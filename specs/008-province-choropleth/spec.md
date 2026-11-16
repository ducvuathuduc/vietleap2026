# Feature Specification: Vietnam 34-province choropleth → click → Hỏi AI

**Feature Branch**: `008-province-choropleth` (lands on `main`) · **Created**: 2026-11-16 · **Status**: Draft · **Priority**: P2 (public-finance theme ~30% is provincial; World Bank dashboard workshop; strong visual for economists)
**Supersedes**: `specs/001-vietleap-insight-kit/tasks.md` T053.

## Context (verified 2026-11-16)
- Engine already normalises provinces 63 → 34 (`engine/vlkit/resources/province_63_to_34.csv`: 63 rows → 34 new provinces, NQ 202/2025/QH15) and adds `_province_2025` and `_region` to `clean.parquet` (seen in `out/bds_practice/clean.parquet`).
- `GET /api/datasets/{id}/segments?by=&metric=` returns at most **25** groups (`T.run_groupby(..., 25)`) → cannot feed a 34-province map.
- No map library and no boundary file in the repo; `docs/licenses.md` says "Map GeoJSON (T053) must be recorded here when added".
- Candidate boundary data (checked 2026-11-16): **HDX "Viet Nam – Subnational Administrative Boundaries" (COD-AB v02)** — Admin 1 = 34 provinces, source General Statistics Office of Vietnam, boundaries dated 01/07/2025, reviewed 25/09/2025, licence **CC BY-IGO**, GeoJSON zip 27.1 MB, P-coded (https://data.humdata.org/dataset/cod-ab-vnm). Alternatives: `open-admin-data/vietnam-administrative-divisions` (CC BY 4.0; coordinates/hierarchy — boundary polygons to be checked), `nguyenduy1133/Free-GIS-Data` (34-province GeoJSON incl. Hoàng Sa/Trường Sa; licence to be checked).
- CSP (`web/next.config.ts`): `img-src 'self' data: blob:`, `connect-src 'self'` → the map must be served from `web/public/` (no tile servers).

## User Scenarios & Testing

### User Story 1 — See a metric by province on a map (Priority: P1)
As the **PO**, I want a choropleth of the selected metric (median by default) across the 34 provinces, so judges see regional disparities at a glance.

**Acceptance**
1. **Given** a dataset with a province column, **When** I open the "Bản đồ" card (on `/segments` and `/` when available), **Then** 34 polygons render with a sequential colour scale from the shadcn chart CSS variables (`--chart-1`…`--chart-5`), a legend with quantile breaks, and grey for provinces with no data ("không có dữ liệu", never 0).
2. **Given** I pick another metric/aggregation (median|mean|sum|count) from shadcn `Select`, **Then** values reload from `GET /api/datasets/{id}/geo`.
3. **Given** hovering a province, **Then** a tooltip shows name, value, n (rows), and the region.

### User Story 2 — Click a province → Hỏi AI (Priority: P1)
**Acceptance**: each polygon carries `insightTarget("segment", province, "Tỉnh …", {province, metric, value, n, rank, region})`; in inspect mode a click opens the AI sheet; offline explanation lists the province's rank among 34 and its gap to the national median (numbers from the `/geo` response).

### User Story 3 — Ranking table & map export (Priority: P2)
**Acceptance**: a table under the map (top/bottom 5 with values) and "Tải PNG" (SVG → canvas → PNG, client-side) for the deck; PNG includes the attribution "Ranh giới: GSO/OCHA COD-AB (CC BY-IGO)".

### User Story 4 — District/63-province fallback (Priority: P3)
**Acceptance**: if a dataset has only 63-province names for years < 2025 the map aggregates to 34 using the existing mapping and labels "đã quy đổi về 34 tỉnh"; district-level maps are out of scope.

### Edge cases
- Name mismatches between the boundary file and `province_63_to_34.csv` new names (e.g. "TP. Hồ Chí Minh" vs "Hồ Chí Minh", "Thừa Thiên Huế" → "Huế") → join on a folded key + explicit alias table; unmatched names listed under the map and in tests (must be 0 for the 34).
- Sovereignty: maps of Viet Nam shown publicly must include Hoàng Sa and Trường Sa — [NEEDS CLARIFICATION: verify the chosen boundary file includes both archipelagos (HDX bbox reaches 6.93°N / 117.39°E, suggesting yes); otherwise use an alternative that does]. The map must not be published without them.
- Metric non-additive (ratios) with `sum` aggregation → `sum` disabled for columns flagged as ratio/percent (name contains `pct|%|ty_le|per`).
- n < 5 rows in a province → hatched/greyed with "n nhỏ" note; still shown.
- Very skewed values → quantile scale (5 classes) rather than linear.
- File size: raw GeoJSON 27 MB → simplified TopoJSON committed only if ≤ 500 KB (repo rule: no file > 20 MB; perf).
- Dark mode → colours from CSS variables adapt automatically.

## Requirements
- **FR-801**: `tools/build_geo.py` (or `npx mapshaper` script) downloads the chosen boundary zip, simplifies (e.g. `-simplify 2% keep-shapes`), keeps properties `{pcode, name, name_en}`, writes `web/public/geo/vn-34.topo.json`, and `web/public/geo/LICENSE.md` with source, date, licence, attribution text; `docs/licenses.md` updated.
- **FR-802**: `GET /api/datasets/{id}/geo?metric=&agg=median|mean|sum|count` → `{metric, agg, level: "province_2025", rows:[{province, region, value, n}], national: {value, n}, unmatched: {rows, samples}}` computed in pandas from `ds.df` grouped by `_province_2025`; 422 when the dataset has no province column.
- **FR-803**: `web/src/components/province-map.tsx` renders SVG with `d3-geo` (`geoMercator().fitSize`) + `topojson-client` (`feature`), or `react-simple-maps` 5.x if it keeps the bundle smaller; colours via CSS variables; keyboard focusable paths with `aria-label`.
- **FR-804**: Alias table `web/src/lib/geo-names.ts` (pure, tested) mapping boundary names ↔ engine names via `fold()`.
- **FR-805**: Offline explanation in `explain.ts` for `segment` targets with `province` data (rank, gap to national median).
- **FR-806**: Attribution text always visible on the map card.

### Non-functional
- **NFR-801**: TopoJSON ≤ 500 KB; map first render ≤ 300 ms on the 2-CPU laptop; JS added ≤ 40 kB gzip.
- **NFR-802**: Works offline (static asset).

## Success criteria
- **SC-801**: test: all 34 engine province names resolve to exactly one map feature and vice versa.
- **SC-802**: pytest `/geo` returns 34-or-fewer rows whose values equal a pandas groupby on the clean data.
- **SC-803**: headless smoke: hover/click works; 0 CSP errors; screenshot `docs/screenshots/map.png`.
