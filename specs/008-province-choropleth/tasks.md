# Tasks: 008 34-province choropleth

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Boundary data (release gate)
- [x] T801 RQ+DE: sovereignty release gate — sourced HDX GSO/OCHA COD-AB v02 (`cod-ab-vnm`, reviewed 2025-09-25, `CC BY-IGO`), verified 34 post-NQ 202/2025/QH15 features including Hoàng Sa (Đà Nẵng, 18 polygons) & Trường Sa (Khánh Hòa, 297 polygons), recorded in `docs/licenses.md` & `web/public/geo/LICENSE.md`.
- [x] T802 `tools/build_geo.py` → `web/public/geo/vn-34.geo.json` (155,262 bytes ≤ 500 KB, all 34 provinces + Hoàng Sa + Trường Sa).
- [x] T803 [P] Test-first `web/src/lib/geo-names.test.ts` (34 canonical names + 63→34 conversion + alias normalisation; `vn.ts` aligned to `"Hồ Chí Minh"` & Huế) → `geo-names.ts`.
- [ ] T804 Commit + push "feat(geo): T801–T803 34-province boundaries (licence recorded) + name mapping".

## Phase B — API
- [x] T805 Test-first `tests/test_geo.py`: `/geo` equals pandas groupby; 422 without province column; invalid metric 422; ratio column rejects `sum` (`py_compile` ok; `pytest` pending Python env).
- [x] T806 `engine/vlkit/tools.py run_geo` + `api/routes/analysis.py GET /geo` (+ TypeScript `computeGeo` & `/api/datasets/[ds_id]/geo` route verified with `synthetic_messy_bds` and `provincial_earmarked_transfers_2024_2025`); `specs/001-vietleap-insight-kit/contracts/openapi.json` synced (live `export_openapi.py` check pending full Python env) → T805.
- [ ] T807 Commit + push "feat(api): T805–T806 /geo province aggregates".

## Phase C — Web
- [x] T808 Implemented interactive 34-province SVG choropleth `web/src/components/province-map.tsx` (with Hoàng Sa & Trường Sa frames, `Hỏi AI` `insightTarget` on every province, quantile legend, and bar-chart toggle/fallback) inside `web/src/components/province-ranking-card.tsx` on `/segments` and `/`.
- [x] T809 [P] `explain.ts` province offline explanation + `explain.test.ts`.
- [x] T810 PNG export (CSS var resolved) + Hoàng Sa (Đà Nẵng) & Trường Sa (Khánh Hòa) + `CC BY-IGO` attribution; headless Chromium smoke on `/segments` → map & table click in `Hỏi AI` mode opens `InsightSheet` with offline rank/gap explanation; 0 console/CSP errors.
- [ ] T811 Commit + push "feat(web): T808–T810 province choropleth → Hỏi AI"; tick; `specs/README.md`.

## Dependencies
T801→T802→T803; T805→T806; (T803, T806)→T808→T810→T811; T809 ∥ T808.
