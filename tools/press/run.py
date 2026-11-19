"""Run all W2-PRESS targets, write data/raw/press/press_long.csv + sources_meta.csv.

Usage: python tools/press/run.py
Idempotent: TinyFish answers are cached in data/cache/tinyfish, page markdown/PDF in data/raw/press/raw.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.robotparser import RobotFileParser

import httpx
import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from engine.vlkit.de.tinyfish import fetch_text, run_goal, spend_total  # noqa: E402
from tools.press import pdf_banking, social_rss, tf_rows  # noqa: E402
from tools.press.output import (KIT, RAW_DIR, PRESS_LONG, SOURCES_META, now_vi, save_raw,  # noqa: E402
                                write_long_csv, write_sources_meta_csv)

TARGETS = Path(__file__).with_name("targets.yaml")
ENV_FILE = KIT / ".env.local"
SUMMARY = KIT / "data" / "raw" / "press" / "run_summary.json"
UA = "vietleap-research/0.1 (press monitor; +https://github.com/vietleap)"
METHODS = {"pdf", "tinyfish", "tinyfetch", "scrape", "rss"}


def load_env(path: Path = ENV_FILE) -> None:
    """Read KEY=VALUE lines from .env.local without overriding the process env and without printing values."""
    if not Path(path).is_file():
        return
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("'\"")


def load_targets(path: Path = TARGETS) -> list[dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    targets = data.get("targets") if isinstance(data, dict) else data
    return [target for target in targets or [] if isinstance(target, dict)]


def robots_status(url: str, cache: dict) -> tuple[str, bool]:
    """(status text, allowed). Unknown robots (403/HTML shell) are allowed but recorded."""
    host = httpx.URL(url).host
    if host in cache:
        return cache[host]
    robots_url = f"https://{host}/robots.txt"
    try:
        response = httpx.get(robots_url, headers={"User-Agent": UA}, timeout=10, follow_redirects=True)
    except httpx.HTTPError as exc:
        cache[host] = (f"unreachable ({type(exc).__name__})", True)
        return cache[host]
    body = response.text or ""
    if response.status_code == 404:
        cache[host] = ("no robots.txt (allow)", True)
    elif response.status_code == 200 and "<html" not in body[:300].lower():
        parser = RobotFileParser()
        parser.parse(body.splitlines())
        allowed = parser.can_fetch(UA, url)
        cache[host] = ("allow" if allowed else "deny", allowed)
    else:
        cache[host] = (f"http {response.status_code} (unknown, allowed)", True)
    return cache[host]


def _download(url: str, path: Path, *, timeout: float = 120.0) -> bytes:
    response = httpx.get(url, headers={"User-Agent": UA}, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    return response.content


def _visible_text(html: str) -> str:
    import re
    from html import unescape

    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "", flags=re.S | re.I)
    return unescape(re.sub(r"<[^>]+>", " ", html))


def _page_text(url: str, name: str) -> str:
    """Cached TinyFetch markdown, plain-GET fallback (some origins block TinyFetch)."""
    path = RAW_DIR / f"{name}_page.md"
    if path.is_file() and path.stat().st_size > 40:
        return path.read_text(encoding="utf-8")
    text = fetch_text([url]).get(url) or ""
    if len(text) <= 40:  # TinyFetch sometimes returns a stub such as "Đã kết nối EMC"
        try:
            response = httpx.get(url, headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
            if response.status_code == 200:
                text = _visible_text(response.text)
        except httpx.HTTPError:
            pass
    if text:
        save_raw(f"{name}_page", text.encode("utf-8"), "md")
    return text


def _reusable_artifact(target: dict, out_json: Path) -> dict | None:
    """A previous non-ok run is replayed instead of paid for again (ok runs hit the TinyFish cache)."""
    if not out_json.is_file():
        return None
    try:
        artifact = json.loads(out_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    body = (artifact.get("request") or {}).get("body") or {}
    if artifact.get("uri") == target["url"] and body.get("goal") == target["goal"].strip():
        return artifact
    return None


def _log_manifest_once(name: str, path: Path, ext: str) -> None:
    """Keep a sha256 line for an existing raw file without rewriting it on every run."""
    data = path.read_bytes()
    from tools.press.output import RAW_MANIFEST

    if RAW_MANIFEST.is_file():
        for line in RAW_MANIFEST.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("name") == name and record.get("sha256") == hashlib.sha256(data).hexdigest():
                return
    save_raw(name, data, ext)


def _tinyfish_target(target: dict, ctx: dict) -> tuple[list[dict], dict]:
    out_json = RAW_DIR / f"{target['source_id']}.json"
    previous = _reusable_artifact(target, out_json)
    if previous is not None and previous.get("status") != "ok":
        return [], {"status": previous.get("status", "unknown"), "message": previous.get("message", "")[:300],
                    "steps": previous.get("num_steps") or 0, "cost_usd": previous.get("cost_usd") or 0.0,
                    "records": len(previous.get("records") or []), "rows": 0, "replayed": True}
    outcome = run_goal(
        target["url"], target["goal"], output_schema=target.get("output_schema"),
        poll_s=5.0, deadline_s=float(target.get("deadline_s", 240.0)),
        browser_profile=target.get("browser_profile"), cache=True,
        cache_ttl_h=float(target.get("cache_ttl_h", 24.0)), max_usd=target.get("max_usd"),
        schema_strict=True, out_json=out_json, source=target["source_id"],
    )
    if out_json.is_file():
        save_raw(target["source_id"], out_json.read_bytes(), "json")
    text = _page_text(target["url"], target["source_id"])
    records = outcome.records or []
    flat = records[0] if len(records) == 1 and isinstance(records[0], dict) else {}
    found_url = str(flat.get("source_page_url") or "")
    if found_url.startswith("https://") and found_url != target["url"]:
        text += "\n" + _page_text(found_url, f"{target['source_id']}_found")
    rows = tf_rows.rows_from_records(records, target, text) if outcome.status == "ok" else []
    if target.get("text_fields") or target.get("segment_table"):
        text_target = dict(target)
        date_field = target.get("published_date_field")
        if date_field and flat:
            text_target["published_date"] = tf_rows.normalize_date(flat.get(date_field)) or ""
        rows += tf_rows.rows_from_text(text, text_target)
    info = {"status": outcome.status, "message": outcome.message[:300], "steps": outcome.steps or 0,
            "cost_usd": outcome.cost_usd, "records": len(records), "rows": len(rows)}
    return rows, info


def extract_target(target: dict, ctx: dict | None = None) -> tuple[list[dict], dict]:
    """Run one recipe entry -> (contract rows, status info). Unknown method raises ValueError."""
    method = target.get("method")
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}")
    ctx = ctx if ctx is not None else {"robots": {}}
    allowed = True
    if target.get("url", "").startswith("https://"):
        status, allowed = robots_status(target["url"], ctx.setdefault("robots", {}))
        if not allowed:
            return [], {"status": f"blocked: robots {status}", "rows": 0, "cost_usd": 0.0}

    if method == "pdf":
        path = RAW_DIR / f"{target['source_id']}.pdf"
        if target.get("extractor") == "mof_appendix_ia":
            transcript = path.with_name(f"{path.stem}_appendix_ia.tsv")
            if not path.is_file():
                content = _download(target["url"], path)
                save_raw(path.stem, content, "pdf")
            with path.open("rb") as pdf:
                sha256 = hashlib.file_digest(pdf, "sha256").hexdigest()
            if sha256 != target["sha256"]:
                raise ValueError("MOF PDF does not match the reviewed appendix transcript")
            reviewed = Path(__file__).with_name(transcript.name).read_bytes()
            if not transcript.is_file() or transcript.read_bytes() != reviewed:
                save_raw(transcript.stem, reviewed, "tsv")
            rows = tf_rows.rows_from_mof_appendix(reviewed.decode("utf-8-sig"), target)
            return rows, {"status": "ok", "rows": len(rows), "cost_usd": 0.0, "pages": [35, 36]}
        if not path.is_file() or path.stat().st_size == 0:
            content = _download(target["url"], path)
            save_raw(target["source_id"], content, "pdf")
        else:
            _log_manifest_once(target["source_id"], path, "pdf")
        rows, info = pdf_banking.extract(path, source_id=target["source_id"], url=target["url"])
        info.update({"status": "ok", "rows": len(rows), "cost_usd": 0.0})
        return rows, info
    if method == "tinyfish":
        return _tinyfish_target(target, ctx)
    if method == "tinyfetch":
        text = _page_text(target["url"], target["source_id"])
        rows: list[dict] = []
        if target.get("extractor") != "list_only" and text:
            rows = tf_rows.rows_from_text(text, target)
        return rows, {"status": "ok" if text else "empty", "rows": len(rows), "cost_usd": 0.0,
                      "bytes": len(text)}
    if method == "scrape":
        content = _download(target["url"], RAW_DIR / f"{target['source_id']}.html")
        save_raw(target["source_id"], content, "html")
        return [], {"status": "ok", "rows": 0, "cost_usd": 0.0, "bytes": len(content)}
    if method == "rss":
        count, feeds = social_rss.run()
        return [], {"status": "ok", "rows": 0, "news_rows": count, "feeds": feeds, "cost_usd": 0.0}
    raise ValueError(f"unknown method {method!r}")  # pragma: no cover


def main() -> int:
    load_env()
    starting_spend = spend_total()
    targets = load_targets()
    ctx: dict = {"robots": {}}
    rows, meta, summary = [], [], []
    for target in targets:
        try:
            target_rows, info = extract_target(target, ctx)
        except Exception as exc:  # one broken source must not lose the others
            target_rows, info = [], {"status": f"error {type(exc).__name__}: {exc}"[:300], "rows": 0}
        rows += target_rows
        summary.append({"source_id": target["source_id"], "method": target["method"],
                        "url": target["url"], **info})
        meta.append({
            "source_id": target["source_id"], "publisher": target.get("publisher", ""),
            "title_vi": target.get("title_vi", ""), "url": target["url"], "method": target["method"],
            "license_note": target.get("license_note", ""),
            "robots_status": ctx["robots"].get(httpx.URL(target["url"]).host, ("not checked", True))[0],
            "fetched_at": now_vi(),
        })
        print(f"{target['source_id']}: {len(target_rows)} rows ({info.get('status')})")

    written = write_long_csv(PRESS_LONG, rows)
    write_sources_meta_csv(SOURCES_META, meta)
    total_spend = spend_total()
    run_spend = round(total_spend - starting_spend, 4)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps({"generated_at": now_vi(), "rows": written,
                                   "run_tinyfish_spend_usd": run_spend, "tinyfish_spend_usd": total_spend,
                                   "sources": summary}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"press_long.csv: {written} rows -> {PRESS_LONG}")
    print(f"sources_meta.csv: {len(meta)} sources -> {SOURCES_META}")
    print(f"TinyFish spend this run: ${run_spend:.4f} (ledger total ${total_spend:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
