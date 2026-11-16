# Feature Specification: Policy-question-first story & deck

**Feature Branch**: `002-policy-question-story` (work lands on `main`, one commit per task group — constitution VIII)
**Created**: 2026-11-16 · **Status**: Draft (ready to implement) · **Priority**: P1 for the contest (rubric A + D ≈ 40%, see `docs/CONTEST_ANALYSIS.md` §3.2)
**Input**: "Deck and story must open with the policy question from the brief, then evidence → decision → limitation, for economist judges."
**Supersedes**: `specs/001-vietleap-insight-kit/tasks.md` T080.

## Context (verified in code, 2026-11-16)
- `POST /api/brief` writes `out/<ds>/brief.json` when a dataset is given (`api/routes/brief.py` line ~42); `python de.py brief <file> --out` writes it anywhere.
  `brief.json` has `title`, `questions[]`, `target`, `units`, `segments`, `time`, `decision_types[]`, `deliverables`, `pack{decision_template{who,what,where,kpi,caveat}, kpis, deck_storyline}`, `warnings` (`engine/vlkit/brief.py` `parse_brief`).
- **Nothing downstream reads `brief.json`**: `engine/vlkit/report.py build_deck()` slide 2 is a generic template ("How does {target} vary across {geo}…"), `pitch_md()` opens with "Điều gì quyết định {target}?", and the web story (`web/src/lib/analyst/story.ts offlineStory`, `/api/story`) starts directly with insight #1.
- Deck order today (`build_deck`): title → Problem & question (generic) → Data & method → Data pipeline → Data model → Data quality → Insight 1..k → Recommendations → Impact → Policy recommendation → Limitations & next steps → Data provenance → Team & Q&A.
- Judges are mostly economists / public-finance people (UEH School of Public Finance, AVSE, World Bank, LSE, FiinGroup) → they score *question → evidence → decision → limitation*, not pipeline depth.

## User Scenarios & Testing

### User Story 1 — Deck opens with the decision question (Priority: P1)
As the **policy owner (PO)** pitching to economist judges, I want slide 2 of `deck.pptx` and the first section of `pitch.md` to state *who decides what*, the decision question from the brief, and the success KPI, so the judges know in 40 seconds what decision the evidence serves.

**Independent test**: run the pipeline on `data/practice/wdi_asia_fiscal_panel.csv` (dataset `wdi_fiscal`) with `scenarios/briefs/wdi_tax_revenue.md` parsed into `out/<ds>/brief.json`; open `deck.pptx` slide 2 and `pitch.md` section 1.

**Acceptance scenarios**
1. **Given** `out/<ds>/brief.json` with `questions[0]` and `pack.decision_template`, **When** reports are built, **Then** slide 2 title is "Decision question", its body shows `questions[0]` verbatim, a "WHO DECIDES" card with `decision_template.who`, and a "SUCCESS KPI" card with `decision_template.kpi`.
2. **Given** no `brief.json`, **When** reports are built, **Then** slide 2 falls back to today's generic question and carries the tag "(no brief — generic question)" so the team notices.
3. **Given** a brief whose target was resolved to a real column (`target.column`), **When** reports are built, **Then** every number on slide 2 (rows, columns) comes from `results.json.meta` — none from the brief text.

### User Story 2 — Every insight slide answers "so what for the decision" (Priority: P1)
As an **economist judge**, I want each insight slide to read *evidence → implication for the decision → limitation*, so I can judge whether the evidence actually supports the recommendation.

**Acceptance scenarios**
1. **Given** an insight with a matching recommendation (`rec.from_insight == insight.id`), **When** the slide is built, **Then** it shows three cards in order: EVIDENCE (sentence + test + p + effect + n), FOR THE DECISION (`so_what`), LIMITATION (`insight.caveat` or the strongest generic caveat).
2. **Given** an insight with no recommendation, **Then** FOR THE DECISION shows "No direct decision link — context only" and the insight is ordered after linked insights.
3. **Given** an insight whose `p_value ≥ 0.05` (after the engine's correction), **Then** the slide kicker reads "Weak evidence" and the insight is never used as the evidence of the headline recommendation.

### User Story 3 — Web "Câu chuyện" follows the same arc (Priority: P2)
As a **teammate demoing the dashboard**, I want the "Câu chuyện" story to start with a step that shows the decision question (from the brief) and end with a limitations step, so the live demo tells the same story as the deck.

**Acceptance scenarios**
1. **Given** the dataset has `brief.json`, **When** I click "Câu chuyện", **Then** step 0 highlights the brief card on Tổng quan (or a sheet if absent) with the question and decision maker, steps 1..n are insights (unchanged), the last step is "Hạn chế" listing `results.caveats[0..2]`.
2. **Given** an LLM is configured, **When** the story is generated, **Then** the question/decision-maker step is **not** sent to the LLM for rewriting (it is user/brief text) and the number-verification guard still applies to the insight steps.

### User Story 4 — Limitations slide ranked by decision risk (Priority: P3)
As the **PO**, I want the Limitations slide to list the limitation that most threatens the headline decision first (causal caveat, sample size, missing years/provinces, 63→34 break), so I can pre-empt the judges' first question.

**Acceptance**: **Given** `results.caveats` and `pipeline.json.quality`, **When** the deck is built, **Then** the first bullet is the causal-association caveat (constitution III), followed by data-coverage caveats with their real counts (missing cells / unmatched join rows) copied from engine output.

### Edge cases
- `brief.json` exists but `questions` is empty → use `title`; if both empty → generic question + tag.
- Brief in English (`language == "en"`) and deck in VI (feature 003) → show the question as written, never machine-translated without marking "(dịch máy)".
- Brief text contains numbers (e.g. "2018–2024", "34 tỉnh") → shown verbatim as *quoted brief text*, visually distinguished (italic, "Đề bài:" prefix) so they are not mistaken for engine numbers (constitution I applies to computed numbers).
- Very long question (> 220 chars) → fit with `fit_text()`; if still overflowing, truncate with "…" and keep full text in speaker notes.
- `brief.json` for a different dataset (stale) → compare `brief.target.column` with `results.meta.target`; mismatch → warning in `pipeline.json.steps` and a footnote on slide 2.
- Brief contains prompt-injection-like text ("ignore previous instructions…") → treated as data: only rendered, never placed in an LLM system prompt.

## Requirements

### Functional
- **FR-201**: `engine/vlkit/report.py` MUST load `out/<ds>/brief.json` when present (`load_brief(out) -> dict | None`, validated against `specs/001-vietleap-insight-kit/contracts/brief.schema.json`; invalid → ignored with a warning).
- **FR-202**: Deck slide 2 MUST be "Decision question" built from the brief (question, who, what, where, KPI), with fallback per US1-2.
- **FR-203**: Insight slides MUST follow EVIDENCE → FOR THE DECISION → LIMITATION; insights ordered: linked to a recommendation first, then by engine rank.
- **FR-204**: Recommendation/Policy slide MUST name `who / what / where / KPI` from `decision_template`, with blanks shown as "____" (never invented).
- **FR-205**: `pitch_md()` MUST open with "## 0 · Câu hỏi quyết định" built from the brief, then pipeline (1 slide), 3 insights, decision, impact, limitations — matching `docs/CONTEST_ANALYSIS.md` §4.6 timing.
- **FR-206**: New read endpoint `GET /api/datasets/{ds}/brief` returns `out/<ds>/brief.json` (404 when absent). `/api/story` (server-side) fetches it; `offlineStory()` gains an optional `brief` argument; the `Story` response gains `question: {text, who, what, kpi, source: "brief"} | null` (rendered before step 1, never rewritten by the LLM) and `limits: string[]` (≤ 3, copied from `results.caveats`); `story.schema.json` updated (additive, backward compatible).
- **FR-207**: Weak insights (p ≥ 0.05 or flagged by engine) MUST NOT be the evidence of recommendation #1; the deck labels them "Weak evidence".
- **FR-208**: Speaker notes on slides 2, insight slides and limitations MUST contain the Q&A hint for the most likely judge question (from `docs/CONTEST_ANALYSIS.md` §4.7: causality, data source, 63→34).

### Non-functional
- **NFR-201**: No new runtime dependency (python-pptx already used).
- **NFR-202**: `deck_overflow()` returns `[]` for all practice datasets with and without brief.
- **NFR-203**: Report build time increase ≤ 1 s per dataset.

### Key entities
- **Brief** (`brief.json`, existing schema) · **Story.question** `{text, who, what, kpi, source}` and **Story.limits** `string[]` (additive fields on the existing `story.schema.json`).

## Success criteria
- **SC-201**: For the 3 practice datasets × their sample briefs, slide 2 shows the brief question verbatim (automated test reads slide text).
- **SC-202**: 100% of numbers on slides 2 and insight slides are found in `results.json`/`pipeline.json` (extend `tests/test_deck.py::test_numbers_come_from_flow`).
- **SC-203**: A non-coder teammate can explain the deck's arc (question → evidence → decision → limitation) after one read-through (dry run 18/11, recorded in `docs/ROADMAP.md`).

## Assumptions / open questions
- [NEEDS CLARIFICATION: official pitch length and language — organisers have not published them (CONTEST_ANALYSIS §3.1); timing defaults to 7 minutes.]
- [NEEDS CLARIFICATION: whether the organisers' brief will contain an explicit decision maker; if not, PO fills `who` on the Đề bài page before export.]
- Brief parsing stays rule-based (no LLM) — reuse `parse_brief`.
