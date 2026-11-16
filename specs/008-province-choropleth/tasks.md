# Tasks: 008 34-province choropleth

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Boundary data (release gate)
- [ ] T801 RQ+DE: choose boundary source (HDX COD-AB v02 CC BY-IGO preferred); verify 34 features, Hoàng Sa + Trường Sa present, licence text, attribution; record in `docs/licenses.md` + `web/public/geo/LICENSE.md`. **Done when** both archipelagos verified visually — otherwise pick an alternative.
- [ ] T802 `tools/build_geo.py` → `web/public/geo/vn-34.topo.json` (≤ 500 KB, 34 features) → T801.
- [ ] T803 [P] Test-first `web/src/lib/geo-names.test.ts` (34 engine names ↔ 34 features, 0 unmatched) → `geo-names.ts` → T802.
- [ ] T804 Commit + push "feat(geo): T801–T803 34-province boundaries (licence recorded) + name mapping".

## Phase B — API
- [ ] T805 Test-first `tests/test_geo.py`: `/geo` equals pandas groupby; 422 without province column; invalid metric 422; ratio column rejects `sum`.
- [ ] T806 `engine/vlkit/tools.py run_geo` + `api/routes/analysis.py GET /geo`; regenerate OpenAPI → T805.
- [ ] T807 Commit + push "feat(api): T805–T806 /geo province aggregates".

## Phase C — Web
- [ ] T808 `npm i d3-geo topojson-client` (+ `@types/d3-geo`, `@types/topojson-client` dev); `web/src/components/province-map.tsx`; mount on `/segments` and `/` → T803, T806.
- [ ] T809 [P] `explain.ts` province offline explanation + test.
- [ ] T810 PNG export + attribution; headless smoke + screenshot `docs/screenshots/map.png`; 0 CSP errors.
- [ ] T811 Commit + push "feat(web): T808–T810 province choropleth → Hỏi AI"; tick; `specs/README.md`.

## Dependencies
T801→T802→T803; T805→T806; (T803, T806)→T808→T810→T811; T809 ∥ T808.
