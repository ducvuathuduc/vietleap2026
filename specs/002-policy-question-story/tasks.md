# Tasks: 002 Policy-question-first story & deck

**Input**: [spec.md](spec.md), [plan.md](plan.md), [contracts/](contracts/) · **Legend**: `[P]` parallel-safe (different files) · `→` depends on · test-first: write the test, see it fail, then implement.
**Done for every task**: `pytest -q tests` then `cd web && npm test && npm run lint && npm run build` (sequential, 2-CPU machine), commit as `thanhdicode`, `git push origin main`, tick here with the hash.

## Phase A — Engine (deck + pitch)
- [x] T201 (`bdcb571`) Test-first: `tests/test_deck.py::test_slide2_decision_question` — build deck for `data/practice/wdi_asia_fiscal_panel.csv` with a `brief.json` parsed from `scenarios/briefs/wdi_tax_revenue.md`; assert slide 2 title "Decision question", body contains `questions[0]`, cards WHO DECIDES / SUCCESS KPI; second case without brief asserts tag "(no brief — generic question)". **Done when** test fails for the right reason.
- [x] T202 (`bdcb571`) `engine/vlkit/report.py`: `load_brief()`, `_decision_frame()`, slide 2, `build_all` wiring → T201. **Done when** T201 passes and `deck_overflow()==[]` on 3 practice datasets.
- [x] T203 (`bdcb571`) [P] Test-first: `tests/test_deck.py::test_insight_slide_evidence_decision_limitation` (3 cards in order; weak insight kicker "Weak evidence"; linked insights first) + extend `test_numbers_come_from_flow` to slide 2 and insight slides.
- [x] T204 (`bdcb571`) `report.py` insight slide layout + ordering + Limitations order with real counts + speaker notes (FR-203/207/208) → T203.
- [x] T205 (`bdcb571`) `report.py pitch_md()` §0 "Câu hỏi quyết định" + `slides/pitch.md` template; test `test_pitch_md_marp_storyline` asserts §0 first → T202.
- [x] T206 (`bdcb571`) Commit + push "feat(story): T201–T205 policy-question-first deck & pitch" ; tick boxes.

## Phase B — API + web story
- [x] T207 (`76c9e37`) [P] Test-first `tests/test_brief.py::test_get_brief_endpoint` (200 after `POST /api/brief {dataset}`; 404 otherwise; `../` id rejected).
- [x] T208 (`76c9e37`) `api/routes/brief.py` `GET /datasets/{ds}/brief`; `python tools/export_openapi.py` → T207.
- [x] T209 (`76c9e37`) [P] Test-first `web/src/lib/analyst/story.test.ts`: `offlineStory(..., brief)` returns `question` (verbatim) + `limits` (≤3 from caveats); `storyPrompt()` never contains brief text; `mergeDraft` keeps `question`.
- [x] T210 (`76c9e37`) `web/src/lib/analyst/story.ts`, `web/src/app/api/story/route.ts`, `web/src/lib/api/{types,client}.ts`; update `contracts/story.schema.json` (additive) → T208, T209.
- [x] T211 (`76c9e37`) `web/src/app/(dashboard)/page.tsx` "Câu hỏi quyết định" Card (`data-tour="brief-question"`); `web/src/components/insight-inspector.tsx` question first / limits last step → T210. Manual check in headless Chromium: 0 console errors. *(16/11: done with and without brief.json — story step 0 = question, last = Hạn chế; the only console errors are the pre-existing 404 prefetch of the sidebar "More" link `/report`, a page that does not exist yet — not caused by 002, see MASTER_PLAN §0.)*
- [x] T212 (`76c9e37`) Commit + push "feat(story): T207–T211 brief endpoint + story question/limits"; tick boxes; update `specs/README.md` status.

## Dependencies
T201→T202→T205; T203→T204; T207→T208→T210→T211; T209→T210. Phase A and Phase B can run in parallel by two people (engine vs web).
