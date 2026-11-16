# Implementation Plan: Scenario packs & dry runs

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 7 h (DE 4 h code/recipes + RQ/AN 3 h data collection & dry runs) · **Owner role**: DE + RQ

## Technical context
- Packs: `scenarios/packs/*.yaml` (fields `id, title, sponsor, domain, keywords, expected_columns, kpis, recipe, decision_template, deck_storyline`), loaded by `engine/vlkit/brief.py`.
- Recipes: `sources.yaml` read by `engine/vlkit/de/sources.py load_sources` (`dataset`, `sources[{name, kind, uri, options, license, conform}]`, `keys`).
- Connectors: `engine/vlkit/de/connectors.py` (api paging `worldbank`, cache in `data/cache/`, `pd.json_normalize(sep="__")`).
- Conformed layer: `engine/vlkit/de/conformed.py` (`conform: {where, agg, geo_level, province}`; province reference `engine/vlkit/resources/province_63_to_34.csv` — 63 rows → 34 new provinces, verified).
- Domain derivations: `engine/vlkit/domains.py` (`apply_public_finance`, `apply_firm` → `roe_pct`, `CAVEATS`).
- Tests: `tests/test_brief.py`, `tests/test_conformed.py`, `tests/test_provinces.py`.

## Constitution check
| Principle | Compliance |
|---|---|
| I Real numbers | dry-run checklist records only values printed by the run (copy from `pipeline.json`/`results.json`); gap view computed in DuckDB |
| II | pack recipes name the test (Kruskal–Wallis, Spearman, bootstrap) already implemented |
| III | decision templates phrase effects as associations; 2025 series-break caveat added |
| V OSS/licences | every source has `license:`; OWID/Ember/WDI CC BY 4.0; FiinGroup/IEA/vnstock flagged NEEDS CLARIFICATION, not integrated until confirmed |
| VI Security | recipes use https public APIs only (SSRF guard applies to API-submitted runs); scraping respects robots.txt; no credentials in yaml (`auth_env` only `KIT_TOKEN_*`) |
| VII Offline | cache + practice CSV fallback; recipes documented with offline mode |
| VIII | tests for brief selection + conformed recipe before push |

## Design
1. **Engine**: `conformed.py` — `agg` accepts `str | {default, columns}`; `ratios: {name: [num, den]}` computed after group-by (`SUM(num)/NULLIF(SUM(den),0)`); diagnostics record which rule applied (`joins[].aggregated` becomes the rule summary). Tests for sum + ratio recompute on merged provinces (e.g. Hà Giang + Tuyên Quang → Tuyên Quang).
2. **Public finance recipe** `scenarios/public_finance/`: `sources.yaml` (file sources: budget CSV/XLSX by province × year; population/GRDP table), `README.md` with download steps and expected headers, `aliases.yaml` optional. Pack `public_finance_province.yaml` gains `column_aliases`.
3. **WDI ASEAN recipe** `scenarios/wdi_asean/sources.yaml`: one `api` source per indicator (12 codes from `tools/fetch_wdi.py`), `uri: https://api.worldbank.org/v2/country/VNM;THA;IDN;MYS;PHL;KHM;LAO;MMR;SGP;BRN/indicator/<code>`, `options: {params: {format: json, per_page: 2000, date: "2000:2024"}, records_path: "1", paging: worldbank}`, `license: World Bank WDI, CC BY 4.0`; `keys: {country: [countryiso3code, iso3], year: [date, year]}`; `views.sql` creating `gold.v_vnm_vs_asean_gap` (VN value, ASEAN median excl. VN, gap, n_countries) — executed by a new optional `post_sql:` list in `sources.yaml` run through the **writer** connection inside `flow.py` (not via `/api/sql`, which stays read-only).
4. **Energy/EV pack** `scenarios/packs/energy_ev_data_economy.yaml` + `scenarios/briefs/nang_luong_xe_dien.md` + `scenarios/energy/sources.yaml` (OWID energy CSV `https://owid-public.owid.io/data/energy/owid-energy-data.csv` [verify URL at T409], Ember yearly data, WDI `EG.ELC.ACCS.ZS`, `EG.FEC.RNEW.ZS`, `EG.USE.ELEC.KH.PC`).
5. **Listed firms**: `column_aliases` (Mã CK/ticker, Sàn/exchange, Ngành ICB, LNST/npat, Vốn chủ sở hữu/equity…), `sector_exclude_for_roe` (Ngân hàng, Bảo hiểm, Chứng khoán) applied in `domains.apply_firm`.
6. **Checklist** `checklists/dry-run.md` (template now, filled during T412).

## Files to touch (verified paths; new ones marked)
`engine/vlkit/de/conformed.py`, `engine/vlkit/de/sources.py` (`post_sql`), `engine/vlkit/de/flow.py` (run `post_sql` after conform), `engine/vlkit/domains.py`,
`scenarios/packs/public_finance_province.yaml`, `scenarios/packs/listed_firms_market.yaml`, `scenarios/packs/energy_ev_data_economy.yaml` (new),
`scenarios/public_finance/{sources.yaml,README.md}` (new), `scenarios/wdi_asean/{sources.yaml,views.sql,README.md}` (new), `scenarios/energy/sources.yaml` (new),
`scenarios/briefs/nang_luong_xe_dien.md` (new), `scenarios/briefs/README.md`, `docs/licenses.md`, `tests/test_conformed.py`, `tests/test_brief.py`.

## Open-source reuse
DuckDB SQL (MIT) for gap view; World Bank API (CC BY 4.0 data); OWID (CC BY 4.0); Ember (CC BY 4.0). Considered: `wbgapi` (MIT) — not needed, the existing api connector already pages/caches.

## Security considerations
- **A10 SSRF**: recipes run from CLI (trusted) — but if submitted through `/api/ingest`, `netguard.guard_source` still validates hosts (public only).
- **A08 Integrity**: `post_sql` only from repo yaml (CLI); `/api/ingest` rejects `post_sql` (pydantic model has no such field) — test.
- **A03 Injection**: `post_sql` statements limited to `CREATE OR REPLACE VIEW gold.*` (regex check) to avoid arbitrary writes.
- **Data/licence (OWASP A06-like supply chain for data)**: licence recorded per source; unclear licences not shipped in submission.
