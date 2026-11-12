"""Tool-using insight agent.

Loop (LLM mode): plan → call engine tools → collect outputs → write answer → verify every number against tool outputs
→ one self-correction round if needed → report verification. Without an API key (or if the provider fails) a
deterministic planner calls the same tools and writes the answer from templates, so the demo works offline.

Events (yielded as dicts, sent to the browser as Server-Sent Events):
  status, plan, tool_call, tool_result, chart, table, token, replace, verification, error, done
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Iterator

from vlkit import fmt
from vlkit import tools as T

from ..settings import Settings
from . import verify
from .llm import ChatClient, LLMError

SYSTEM = """You are VietLeap Analyst, a rigorous data analyst for a hackathon team (judges: economists and data scientists).
You analyse ONE dataset through tools. Rules:
1. Plan briefly, then call tools. Never compute statistics yourself; get every number from a tool.
2. NEVER write a number that does not appear in a tool output (rounding is fine). If you lack a number, call a tool.
3. Association ≠ causation: say "is associated with", never "causes/drives/leads to" unless the design is experimental.
4. For each insight give: a one-sentence headline; Evidence (exact numbers, test name, p-value, n); which chart supports it;
   **So what** (why a decision maker should care) and **Now what** (a concrete action).
5. Mention the most important caveat. Be concise. Answer in the user's language (Vietnamese or English).
Dataset context: {context}"""

AUTO_PROMPT = ("Auto-analyse this dataset. Produce a ranked report of the top {n} insights for the judges. Start with "
               "describe_dataset and ranked_insights, then confirm the strongest findings with run_stat_test / fit_drivers / "
               "forecast / what_if as relevant, and finish with 3 recommendations (So what → Now what) and caveats.")


def _ev(type_: str, **kw) -> dict:
    return {"type": type_, "ts": round(time.time(), 3), **kw}


def _slim(out: dict, limit: int = 6000) -> str:
    """Tool output for the model: drop bulky chart arrays, cap size."""
    o = {k: v for k, v in out.items() if k not in ("chart",)}
    s = json.dumps(o, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + "…(truncated)"


def _stream_text(text: str) -> Iterator[dict]:
    for tok in re.findall(r"\S+\s*|\s+", text):
        yield _ev("token", text=tok)


def _tool(ctx: T.Context, name: str, args: dict, outputs: list) -> Iterator[dict]:
    yield _ev("tool_call", name=name, args=args)
    try:
        out = T.call(ctx, name, args)
    except T.ToolError as e:
        out = {"error": str(e)}
    except Exception as e:  # defensive: tools must never kill the stream
        out = {"error": f"{type(e).__name__}: {e}"}
    outputs.append(out)
    yield _ev("tool_result", name=name, ok="error" not in out, summary=_slim(out, 600))
    if out.get("chart"):
        yield _ev("chart", spec=out["chart"], source=name)
    if out.get("table"):
        yield _ev("table", **out["table"], source=name)
    return out


# ----------------------------------------------------------------------------- LLM mode

def run_llm(ctx: T.Context, history: list[dict], question: str, settings: Settings, client: ChatClient | None = None) -> Iterator[dict]:
    client = client or ChatClient(settings.llm_base_url, settings.llm_model, settings.llm_api_key or "", settings.llm_timeout_s)
    context = json.dumps({k: ctx.meta[k] for k in ("domain", "target", "time_col", "geo_col", "rows")}, ensure_ascii=False)
    msgs = [{"role": "system", "content": SYSTEM.format(context=context)}] + history[-8:] + [{"role": "user", "content": question}]
    outputs: list[Any] = []
    specs = T.openai_specs()
    final = ""
    for step in range(settings.agent_max_steps):
        yield _ev("status", text=f"thinking (step {step + 1})")
        turn = None
        for kind, val in client.stream(msgs, specs):
            if kind == "token":
                yield _ev("token", text=val)
            else:
                turn = val
        assert turn is not None
        if turn.tool_calls:
            if turn.content:
                yield _ev("plan", text=turn.content)
            msgs.append({"role": "assistant", "content": turn.content or None,
                         "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments or "{}"}} for c in turn.tool_calls]})
            for c in turn.tool_calls:
                try:
                    args = c.args()
                except LLMError as e:
                    args, out = {}, {"error": str(e)}
                    outputs.append(out)
                    msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(out)})
                    continue
                out = yield from _tool(ctx, c.name, args, outputs)
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": _slim(out)})
            continue
        final = turn.content
        break
    else:
        yield _ev("error", text="step limit reached before a final answer")
    chk = verify.check(final, outputs, question)
    if not chk["ok"]:
        yield _ev("status", text=f"verifying: {len(chk['unverified'])} number(s) not found in tool outputs → revising")
        msgs += [{"role": "assistant", "content": final},
                 {"role": "user", "content": f"These numbers are not present in any tool output: {chk['unverified']}. Rewrite the answer using only numbers returned by tools (call tools if needed). Keep the same structure."}]
        yield _ev("replace")
        final = ""
        for kind, val in client.stream(msgs, None):
            if kind == "token":
                yield _ev("token", text=val)
            else:
                final = val.content
        chk = verify.check(final, outputs, question)
    yield _ev("verification", **chk, mode="llm")
    yield _ev("done", text=final)


# ----------------------------------------------------------------------------- deterministic fallback

KW = {
    "drivers": ["driver", "why", "explain", "factor", "yếu tố", "tại sao", "vì sao", "ảnh hưởng", "giải thích", "importance"],
    "forecast": ["forecast", "predict", "next", "dự báo", "tương lai", "trend", "xu hướng"],
    "whatif": ["what if", "what-if", "nếu", "scenario", "kịch bản", "increase", "decrease", "tăng", "giảm"],
    "corr": ["correl", "tương quan", "relationship", "quan hệ", " vs ", "liên hệ"],
    "compare": ["by ", "across", "compare", "theo", "so sánh", "khác", "differ", "between", "giữa", "segment", "nhóm"],
}


def _mentioned_cols(ctx: T.Context, q: str) -> list[str]:
    from vlkit.vn import ascii_key
    qk = " " + ascii_key(q) + " "
    cols = [c for c in ctx.df.columns if not c.startswith("_")]
    hits = [(qk.find(" " + ascii_key(c) + " "), c) for c in cols if ascii_key(c) and (" " + ascii_key(c) + " ") in qk]
    return [c for _, c in sorted(hits)]


def _insight_md(i: dict, rec: dict | None, k: int, lang: str) -> str:
    title = i["title_vi"] if lang == "vi" else i["title_en"]
    sent = i["sentence_vi"] if lang == "vi" else i["sentence_en"]
    ev = f"{i['test']}" + (f", {fmt.p(i['p_value'])}" if i["p_value"] is not None else "")
    lines = [f"### {k}. {title}", sent, f"*{'Bằng chứng' if lang == 'vi' else 'Evidence'}:* {ev}; {'điểm xếp hạng' if lang == 'vi' else 'rank score'} {i['score']:.2f}."]
    if rec:
        sw, nw = (rec["so_what_vi"], rec["now_what_vi"]) if lang == "vi" else (rec["so_what_en"], rec["now_what_en"])
        lines += [f"**So what:** {sw}", f"**Now what:** {nw}"]
    return "\n".join(lines) + "\n\n"


def run_fallback(ctx: T.Context, question: str, auto_n: int | None = None) -> Iterator[dict]:
    lang = "vi" if re.search(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", question.lower()) else "en"
    outputs: list[Any] = []
    text = ""
    q = question.lower()
    yield _ev("status", text="offline analyst (no LLM key): deterministic planner using the same engine tools")
    if auto_n:
        yield _ev("plan", text="describe dataset → rank insights → confirm top segment gap with a test → drivers → recommendations")
        d = yield from _tool(ctx, "describe_dataset", {}, outputs)
        rk = yield from _tool(ctx, "ranked_insights", {"top_n": auto_n}, outputs)
        gap = next((i for i in rk["insights"] if i["type"] == "segment_gap"), None)
        if gap:
            ev = next(i for i in ctx.results["insights"] if i["id"] == gap["id"])["evidence"]
            yield from _tool(ctx, "run_stat_test", {"x": ev["by"], "y": ev["metric"], "test": "kruskal"}, outputs)
        recs = {r["from_insight"]: r for r in rk["recommendations"]}
        head = (f"## Báo cáo tự động: top {auto_n} phát hiện về {d['default_target']}\n\n" if lang == "vi"
                else f"## Auto-analysis: top {auto_n} insights on {d['default_target']}\n\n")
        head += (f"Dữ liệu: {d['rows']:,} dòng, lĩnh vực {d['domain']}.\n\n" if lang == "vi" else f"Data: {d['rows']:,} rows, domain {d['domain']}.\n\n")
        text = head + "".join(_insight_md(i, recs.get(i["id"]), k + 1, lang) for k, i in enumerate(rk["insights"]))
        for i in rk["insights"][:3]:
            if i.get("chart"):
                yield _ev("chart", spec=i["chart"], source=f"insight {i['id']}")
        text += ("**Lưu ý:** " if lang == "vi" else "**Caveats:** ") + " ".join(d["caveats"][:2])
    else:
        cols = _mentioned_cols(ctx, question)
        target = next((c for c in cols if c in ctx.df and str(ctx.df[c].dtype).startswith(("float", "int"))), ctx.meta["target"])
        cats = [c for c in cols if c != target and c in ctx.meta.get("category_cols", [])] or [c for c in cols if c != target]
        intent = next((k for k in ("whatif", "forecast", "drivers", "corr", "compare") if any(w in q for w in KW[k])), None)
        if intent == "compare" and not cats:
            cats = [ctx.meta.get("geo_col") or (ctx.meta.get("category_cols") or [None])[0]]
        if intent == "whatif":
            m = re.search(r"([-+]?\d+(?:[.,]\d+)?)\s*%", q)
            pct = float(m.group(1).replace(",", ".")) if m else 10.0
            if any(w in q for w in ["giảm", "decrease", "lower", "reduce"]) and pct > 0:
                pct = -pct
            feats = [c for c in cols if c != target] or [None]
            if feats[0] is None:
                dr = yield from _tool(ctx, "fit_drivers", {"target": target}, outputs)
                num = [c["feature"] for c in dr.get("coefficients", []) if "=" not in c["feature"]]
                feats = num[:1] or [None]
            w = yield from _tool(ctx, "what_if", {"feature": feats[0], "pct_change": pct, "target": target}, outputs)
            if "error" in w:
                text = f"Could not run the scenario: {w['error']}"
            else:
                text = (f"Holding other features fixed, changing **{w['feature']}** by {w['pct_change']:+g}% is associated with a "
                        f"**{fmt.pct(w['target_change_pct'])}** change in {w['target']} (bootstrap 90% interval {fmt.pct(w['ci90_pct'][0])} to {fmt.pct(w['ci90_pct'][1])}). "
                        f"Baseline mean {fmt.num(w['baseline_target_mean'], w['target'])}.\n\n**So what:** this sizes the lever before spending on it. "
                        f"**Now what:** pilot the change on a comparable subset and measure. *This is a model-based association, not a causal guarantee.*")
        elif intent == "forecast":
            f = yield from _tool(ctx, "forecast", {"metric": target}, outputs)
            if "error" in f:
                text = f"Forecast not possible: {f['error']}"
            else:
                tr = f.get("trend") or {}
                text = (f"Using a {f['model']} model (chosen by holdout MAE), {f['agg']} {f['metric']} is projected at **{fmt.num(f['forecast'][0], f['metric'])}** next period "
                        f"(80% interval {fmt.num(f['lower80'][0], f['metric'])}–{fmt.num(f['upper80'][0], f['metric'])}).")
                if tr:
                    text += f" Over the history it changed {fmt.pct(tr.get('total_change_pct'))} (Spearman ρ={tr.get('spearman_rho')}, {fmt.p(tr.get('spearman_p'))})."
                text += "\n\n**So what:** plan on the range, not the point. **Now what:** set an alert when actuals leave the 80% band. *Simple extrapolation; shocks are not modelled.*"
        elif intent == "drivers":
            dr = yield from _tool(ctx, "fit_drivers", {"target": target}, outputs)
            if "error" in dr:
                text = f"Driver model failed: {dr['error']}"
            else:
                top = dr["importance"][:3]
                cv = dr["cv_r2"]
                text = (f"A ridge + gradient-boosting model of **{target}** reaches 5-fold CV R² of {cv['gb_mean']} (boosting) and {cv['ridge_mean']} (ridge), n={dr['n']}. "
                        "Strongest associated features by permutation importance: " + "; ".join(f"{t['feature']} ({t['importance']})" for t in top) + ".\n\n"
                        f"**So what:** these variables carry most of the predictive signal. **Now what:** monitor them as KPIs and test the top lever with the what-if tool. *Associations, not causal effects.*")
        elif intent == "corr" and len(cols) >= 2:
            yield from _tool(ctx, "make_chart", {"kind": "scatter", "x": cols[0], "y": cols[1]}, outputs)
            st = yield from _tool(ctx, "run_stat_test", {"x": cols[0], "y": cols[1], "test": "spearman"}, outputs)
            text = (f"**{cols[0]}** and **{cols[1]}**: Spearman ρ={st.get('r')}, {fmt.p(st.get('p'))}, n={st.get('n')}. "
                    "Correlation only; confounders likely.") if "error" not in st else st["error"]
        elif intent == "compare" and cats and cats[0]:
            by = cats[0]
            g = yield from _tool(ctx, "run_groupby", {"by": by, "metric": target, "agg": "median"}, outputs)
            st = yield from _tool(ctx, "run_stat_test", {"x": by, "y": target}, outputs)
            if "error" in g or "error" in st:
                text = g.get("error") or st.get("error")
            else:
                top, bot = st["top"], st["bottom"]
                text = (f"Median **{target}** by **{by}**: highest {top['group']} ({fmt.num(top['median'], target)}, n={top['n']}), lowest {bot['group']} "
                        f"({fmt.num(bot['median'], target)}, n={bot['n']}), ratio {st['top_vs_bottom']['median_ratio']}×. Kruskal–Wallis H={st['kruskal']['H']}, "
                        f"{fmt.p(st['kruskal']['p'])}, ε²={st['kruskal']['epsilon2']}; top vs bottom Mann–Whitney {fmt.p(st['top_vs_bottom']['p'])}, rank-biserial {st['top_vs_bottom']['rank_biserial']}.\n\n"
                        f"**So what:** {by} separates {target} materially. **Now what:** benchmark each {by} against the overall median ({fmt.num(st['overall_median'], target)}) and prioritise the lowest groups.")
        else:
            d = yield from _tool(ctx, "describe_dataset", {}, outputs)
            rk = yield from _tool(ctx, "ranked_insights", {"top_n": 3}, outputs)
            text = (f"The dataset has {d['rows']:,} rows ({d['domain']}); default target **{d['default_target']}**. Top findings:\n\n" +
                    "".join(_insight_md(i, None, k + 1, lang) for k, i in enumerate(rk["insights"])) +
                    "Ask e.g. *“compare {t} by {g}”*, *“what drives {t}?”*, *“what if X increases 10%?”* or *“forecast {t}”*.".format(t=d["default_target"], g=d.get("geo_col") or "a category"))
    yield from _stream_text(text)
    chk = verify.check(text, outputs, question)
    yield _ev("verification", **chk, mode="fallback")
    yield _ev("done", text=text)


def run(ctx: T.Context, question: str, history: list[dict], settings: Settings, auto_n: int | None = None, client: ChatClient | None = None) -> Iterator[dict]:
    q = AUTO_PROMPT.format(n=auto_n) if auto_n else question
    if settings.llm_api_key or client is not None:
        try:
            yield from run_llm(ctx, history, q, settings, client)
            return
        except LLMError as e:
            yield _ev("error", text=f"LLM unavailable ({e}); switching to offline analyst")
    yield from run_fallback(ctx, question or q, auto_n)
