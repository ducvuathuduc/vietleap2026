# Implementation Plan: 34-province choropleth

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 5 h · **Owner role**: DE (RQ verifies boundary licence + sovereignty)

## Technical context
- Engine/data: `engine/vlkit/resources/province_63_to_34.csv`, `province_region.csv`; `clean.parquet` columns `_province_2025`, `_region`; `api/routes/analysis.py` (router `/api/datasets/{ds_id}`), `engine/vlkit/tools.py` (`Context`, `run_groupby`).
- Web: `web/src/app/(dashboard)/segments/page.tsx`, `web/src/app/(dashboard)/page.tsx`, `web/src/lib/insight-target.ts`, `web/src/lib/analyst/explain.ts`, `web/src/components/ui/{card,select,table,tooltip}.tsx` (installed), `web/next.config.ts` (CSP).
- Libraries (npm registry checked 2026-11-16): `d3-geo` 3.1.2 (ISC), `topojson-client` 3.1.0 (ISC), `react-simple-maps` 5.0.5 (MIT, peer React 16–19), `mapshaper` 0.8.0 (MPL-2.0, dev/tool only).

## Constitution check
| Principle | Compliance |
|---|---|
| I | values from `/geo` (pandas groupby on engine-clean data); missing = grey, not 0 |
| II | map card links to the segment test (Kruskal–Wallis by province from `/segments`) when available |
| III | tooltip/explanation wording: "cao hơn trung vị toàn quốc", no causal wording |
| IV | no shadcn map exists → minimal SVG component inside a shadcn `Card`; colours = chart CSS variables; no new theme |
| V | ISC/MIT/MPL libs; boundary data CC BY-IGO with attribution recorded in `docs/licenses.md` + `web/public/geo/LICENSE.md` |
| VI | static asset, no third-party tiles (CSP unchanged); `/geo` params validated (metric must be a numeric column of the dataset; agg enum) |
| VII | fully offline |
| VIII | tests for name mapping + endpoint first |

## Design
1. **Data build (one-off, committed output)** `tools/build_geo.py`: download HDX GeoJSON zip (or alternative chosen in T801) to `data/raw/` (git-ignored), run `npx mapshaper -i … -filter-fields <pcode>,<name> -simplify 2% keep-shapes -o format=topojson web/public/geo/vn-34.topo.json`; print feature count (must be 34) and size.
2. **API** `GET /geo`: `df.groupby("_province_2025")[metric].agg(agg)`, `size()`, region from `_region` mode; `national` = same agg on all rows; `unmatched` = rows with null `_province_2025` count + sample names from the raw province column.
3. **Web** `province-map.tsx`: load topojson via `fetch("/geo/vn-34.topo.json")` once (module cache), `feature()` → `geoPath(geoMercator().fitSize([w,h], fc))`; quantile breaks computed on returned values only; `<path>` per feature with `insightTarget`; shadcn `Tooltip` for hover; legend; attribution; "Tải PNG" via `XMLSerializer` + canvas `toBlob` (no external lib).
4. `geo-names.ts`: `ALIASES` + `matchProvince(name)`; test against the 34 names in `province_63_to_34.csv` (copied into a fixture at build time).

## Files to touch
`tools/build_geo.py` (new), `web/public/geo/vn-34.topo.json` (new, ≤ 500 KB), `web/public/geo/LICENSE.md` (new), `docs/licenses.md`, `web/package.json` (+d3-geo, topojson-client, @types), `web/src/components/province-map.tsx` (new), `web/src/lib/geo-names.ts` (+ `.test.ts`, new), `web/src/lib/api/{client,types}.ts`, `web/src/app/(dashboard)/segments/page.tsx`, `web/src/app/(dashboard)/page.tsx`, `web/src/lib/analyst/explain.ts` (+test), `api/routes/analysis.py`, `engine/vlkit/tools.py` (`run_geo` helper), `tests/test_geo.py` (new), `specs/001-vietleap-insight-kit/contracts/openapi.json`.

## Security considerations
- **A06 Vulnerable components / supply chain**: three small ISC/MIT packages; `npm audit` in CI; mapshaper only as a dev tool via `npx` (not shipped).
- **A05 Misconfiguration (CSP)**: same-origin asset; no `unsafe-eval`; PNG export uses blob URLs (already allowed `img-src blob:`).
- **A03**: `metric` validated against numeric columns (no arbitrary expression); `agg` enum.
- **Legal/data**: CC BY-IGO attribution displayed; sovereignty check (Hoàng Sa/Trường Sa) is a release gate (T801).
