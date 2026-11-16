# Implementation Plan: Policy-question-first story & deck

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 5 h (1 dev) · **Owner role**: DE implements, PO reviews wording

## Summary
Feed the already-produced `brief.json` into the three story surfaces (PPTX deck, Marp `pitch.md`, web "Câu chuyện") so each
opens with *who decides what*, then evidence → decision → limitation. No new dependencies; pure re-ordering and re-labelling
of engine output plus one read endpoint.

## Technical context
- Python 3.12, python-pptx (MIT) — `engine/vlkit/report.py` (`build_deck`, `pitch_md`, `build_all`, `fit_text`, `deck_overflow`).
- FastAPI — new `GET /api/datasets/{ds}/brief` in `api/routes/brief.py` (router prefix `/api`, reuses `get_settings().out_dir`, `slug`).
- Web: `web/src/lib/analyst/story.ts` (`offlineStory`, `mergeDraft`, `storyPrompt`), `web/src/app/api/story/route.ts`,
  `web/src/components/insight-inspector.tsx` (story playback with driver.js), `web/src/lib/api/types.ts` (`Brief` type exists for the Đề bài page — reuse).
- Contracts: `specs/001-vietleap-insight-kit/contracts/story.schema.json`, `brief.schema.json`, `openapi.json` (regenerate with `python tools/export_openapi.py`).
- Tests: `tests/test_deck.py`, `tests/test_brief.py`, `tests/test_contracts.py`, `web/src/lib/analyst/story.test.ts`.

## Constitution check
| Principle | How this feature complies | Gate |
|---|---|---|
| I Real numbers only | Brief text is quoted (prefixed "Đề bài:"/"Brief:"), never treated as computed numbers; every computed number still comes from `results.json`/`pipeline.json`; test extends `test_numbers_come_from_flow` | ✅ |
| II Stat-tested | Evidence card shows test, p, effect, n; weak insights labelled and excluded from headline evidence (FR-207) | ✅ |
| III No causal claims | Limitation card on every insight slide; causal caveat first on Limitations slide | ✅ |
| IV OSS UI as-is | Web change reuses existing Sheet/Card/driver.js popovers; no new styling | ✅ |
| V OSS only | no new deps | ✅ |
| VI Security | brief is untrusted text: rendered as text only, excluded from LLM system prompt, length-capped (≤ 2 000 chars per field); new endpoint is read-only, path from `slug()` | ✅ |
| VII Offline-first | entirely deterministic; LLM only rewrites insight narration as today | ✅ |
| VIII Tests before push | T201/T203/T206 are test-first | ✅ |

## Design
1. `report.py`
   - `load_brief(out: Path) -> dict | None` — reads `brief.json`, validates required keys (`questions`, `title`), caps strings; mismatch of `brief.target.column` vs `res.meta.target` → returns brief + `stale=True`.
   - `_decision_frame(res, brief) -> dict` — `{question, who, what, where, kpi, caveat, source: "brief"|"generic"}`; blanks → `"____"`.
   - `build_deck(res, out, pngs, de, brief=None)`: slide 2 = "Decision question" (question body + WHO DECIDES + SUCCESS KPI cards + footnote when stale/generic); insight slides = 3 cards EVIDENCE / FOR THE DECISION / LIMITATION; order insights linked-first; Limitations slide = causal caveat first, then coverage caveats with real counts (quality `missing_cells`, conformed `unmatched_rows` when present).
   - `pitch_md(res, de, brief=None)`: new section "## 0 · Câu hỏi quyết định".
   - `build_all` passes `load_brief(out)`; speaker notes via `slide.notes_slide.notes_text_frame.text`.
2. API `GET /api/datasets/{ds}/brief` → 200 JSON or 404.
3. Web
   - `story.ts`: `offlineStory(insights, recs, name, n, brief?)` adds `question` and `limits`; `mergeDraft` keeps both untouched; `storyPrompt` gets only insight data (brief excluded).
   - `story/route.ts`: fetch brief with `backend()` (404 → null), pass through.
   - `insight-inspector.tsx`: if `story.question`, first driver.js step on `[data-tour="brief-question"]` (new Tổng quan card; popover-only step when the card is not on the current page); last step lists `limits`.

## Files to touch (verified to exist 2026-11-16)
| Path | Change |
|---|---|
| `engine/vlkit/report.py` | `load_brief`, `_decision_frame`, slide 2, insight slide layout, limitations order, notes, `pitch_md` §0 |
| `api/routes/brief.py` | `GET /datasets/{ds}/brief` |
| `web/src/lib/analyst/story.ts`, `story.test.ts` | `question`, `limits`, brief excluded from prompt |
| `web/src/app/api/story/route.ts` | fetch brief |
| `web/src/components/insight-inspector.tsx` | first/last story steps |
| `web/src/app/(dashboard)/page.tsx` | `data-tour="brief-question"` on the brief summary card (only if a card exists; otherwise popover step) |
| `web/src/lib/api/types.ts`, `client.ts` | `Story.question/limits`, `api.brief(id)` |
| `specs/001-vietleap-insight-kit/contracts/story.schema.json`, `openapi.json` | additive fields / new path |
| `tests/test_deck.py`, `tests/test_brief.py`, `tests/test_contracts.py` | new tests |
| `slides/pitch.md` | template mirrors new §0 |

## Open-source reuse
python-pptx (MIT) notes API; driver.js (MIT) existing; no additions.

## Security considerations (OWASP Top 10 2021 / OWASP LLM Top 10 2025)
- **A03 Injection / LLM01 Prompt injection**: brief text is user-supplied; never concatenated into the system prompt; when the LLM sees story context the brief is excluded (story narration only rewrites insight steps). Unit test asserts `storyPrompt()` output does not contain the brief question.
- **A01 Broken access control / path traversal**: `ds` passes through `slug()`; file name fixed (`brief.json`).
- **A04 Insecure design / LLM09 Misinformation**: number guard unchanged; question rendered as quoted brief text.
- **A05 Misconfiguration**: endpoint inherits SecurityMiddleware (headers, rate limit not needed for GET).
- **XSS**: React escapes text; PPTX/Markdown output: Markdown special chars in brief escaped in `pitch.md` (no raw HTML pass-through to Marp).

## Risks
- Deck overflow with long Vietnamese questions → `fit_text` + notes fallback (NFR-202 test).
- Teams forget to parse the brief before export → slide 2 shows "(no brief — generic question)" tag, Export page (feature 009) warns.
