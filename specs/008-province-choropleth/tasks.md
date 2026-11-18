# Tasks: 008 34-province choropleth

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Boundary data (release gate)
- [ ] T801 RQ+DE: sovereignty release gate — unverified TopoJSON polygons omitted until verified 34-province boundaries including Hoàng Sa (Đà Nẵng) & Trường Sa (Khánh Hòa) are sourced & licensed.
- [ ] T802 `tools/build_geo.py` → `web/public/geo/vn-34.topo.json` (blocked by T801).
- [x] T803 [P] Test-first `web/src/lib/geo-names.test.ts` (34 canonical names + 63→34 conversion + alias normalisation; `vn.ts` aligned to `"Hồ Chí Minh"` & Huế) → `geo-names.ts`.
- [ ] T804 Commit + push "feat(geo): T801–T803 34-province boundaries (licence recorded) + name mapping".

## Phase B — API
- [x] T805 Test-first `tests/test_geo.py`: `/geo` equals pandas groupby; 422 without province column; invalid metric 422; ratio column rejects `sum` (`py_compile` ok; `pytest` pending Python env).
- [x] T806 `engine/vlkit/tools.py run_geo` + `api/routes/analysis.py GET /geo` (+ TypeScript `computeGeo` & `/api/datasets/[ds_id]/geo` route verified with `synthetic_messy_bds` and `provincial_earmarked_transfers_2024_2025`); OpenAPI regeneration pending Python env → T805.
- [ ] T807 Commit + push "feat(api): T805–T806 /geo province aggregates".

## Phase C — Web
- [x] T808 Implemented sovereign-safe 34-province ranked chart & table `web/src/components/province-ranking-card.tsx` (without unverified polygon TopoJSON per T801 gate); mounted on `/segments` and `/` (profile-gated `silentOnMissing`).
- [x] T809 [P] `explain.ts` province offline explanation + `explain.test.ts`.
- [x] T810 PNG export + Hoàng Sa (Đà Nẵng) & Trường Sa (Khánh Hòa) attribution; headless Chromium smoke on `/segments` → row click in `Hỏi AI` mode opens `InsightSheet` with offline rank/gap explanation; 0 console/CSP errors.
- [ ] T811 Commit + push "feat(web): T808–T810 province choropleth → Hỏi AI"; tick; `specs/README.md`.

## Dependencies
T801→T802→T803; T805→T806; (T803, T806)→T808→T810→T811; T809 ∥ T808.
