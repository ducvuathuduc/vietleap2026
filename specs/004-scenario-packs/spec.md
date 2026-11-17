# Feature Specification: Scenario packs & dry runs for the likely contest themes

**Feature Branch**: `004-scenario-packs` (lands on `main`) · **Created**: 2026-11-16 · **Status**: Draft · **Priority**: P1 (themes ranked in `docs/CONTEST_ANALYSIS.md` §2.2: public finance ~30%, listed firms ~20%, WDI benchmark ~15%, energy/EV/data economy ~15%)
**Supersedes**: `specs/001-vietleap-insight-kit/tasks.md` T082, T083.

## Context (verified 2026-11-16)
- 7 packs exist in `scenarios/packs/`: `public_finance_province`, `listed_firms_market`, `development_indicators`, `data_economy_property`, `economic_policy`, `social_impact`, `cv_observation`. **No energy/EV pack, no mobility pack.**
- Practice data in repo: `data/practice/wdi_asia_fiscal_panel.csv` (350 rows = 14 countries × 2000–2024, 15 columns: VNM, 9 other ASEAN members, CHN, KOR, IND, BGD — built by `tools/fetch_wdi.py`), `data/practice/vn_firms_2021.xlsx`, `data/practice/synthetic_messy_bds.csv`. **No provincial budget data is in the repo**; brief `scenarios/briefs/ngan_sach_tinh.md` says "(tự thu thập)".
- World Bank API connector works with `paging: worldbank`, `records_path: "1"` (`scenarios/demo/sources.yaml`). Conformed keys support `country` (iso3) + `year` (`scenarios/conformed/sources.yaml`).
- `tests/test_brief.py` checks that sample briefs select the expected pack/target.

## User Scenarios & Testing

### User Story 1 — Provincial public-finance dry run (Priority: P1)
As the **DE + AN**, I want to run the public-finance pack end-to-end on real provincial data (34-province basis) before 20/11, so on contest day only the organisers' data changes.

**Independent test**: `python de.py run scenarios/public_finance/sources.yaml --primary budget --serve` then `make brief F=scenarios/briefs/ngan_sach_tinh.md D=<budget csv>`; dashboard shows KPIs from the pack (tự chủ ngân sách, phụ thuộc bổ sung, thực hiện dự toán).

**Acceptance**
1. **Given** a provincial budget table (63 old or 34 new provinces, ≥ 2 years), **When** the pipeline runs, **Then** provinces normalise to 34 (`province_63_to_34.csv`), additive measures are summed for merged provinces, ratios are recomputed from numerator/denominator (never averaged), and unmapped names appear in join coverage.
2. **Given** the pack's KPI formulas, **When** columns match, **Then** derived columns exist in silver with a cleaning-log line naming the formula; **When** they do not match, **Then** the brief page warns which expected columns are missing (no invented column).
3. **Given** the dry run, **Then** `checklists/dry-run.md` is filled with timings, quality scores, number of insights with p < 0.05 and any manual fix.

### User Story 2 — Listed firms (FiinGroup-like) dry run (Priority: P1)
As the **AN**, I want the listed-firms pack to run on multi-sheet/multi-period financial statements (ticker × period), so a FiinPro-style export works without code changes.

**Acceptance**: **Given** `data/practice/vn_firms_2021.xlsx`, **When** run via `de.py file … --serve`, **Then** `roe_pct` is derived (`domains.py apply_firm`), the leakage guard excludes NPAT/equity from ROE drivers, the ticker conformed dim exists when a second source (e.g. sector list) shares `ticker`, and the dry-run checklist is filled. **Given** a FiinPro-like export layout [NEEDS CLARIFICATION: exact column names the organisers' FiinGroup extract will use], **Then** the column mapping table in the pack lists the aliases we expect.

### User Story 3 — WDI Vietnam vs ASEAN recipe (Priority: P1)
As the **PO**, I want a ready `sources.yaml` that pulls WDI indicators for Viet Nam and ASEAN peers through the API (cached) and conforms them on country + year, so we can benchmark Viet Nam in < 10 minutes.

**Acceptance**
1. **Given** network, **When** `python de.py run scenarios/wdi_asean/sources.yaml --primary tax_revenue --serve`, **Then** one bronze table per indicator, a `cdim_country`/`cdim_year`, an integrated OBT country × year, join coverage ≥ 95% for rows with values, and provenance with CC BY 4.0.
2. **Given** no network, **Then** the run uses `data/cache/` (second run) or the documented fallback `data/practice/wdi_asia_fiscal_panel.csv` with the same keys.
3. **Given** the integrated table, **Then** the pack's KPI "gap of Viet Nam vs ASEAN median" is computed by SQL in DuckDB (saved view `gold.v_vnm_vs_asean_gap`), not by hand.

### User Story 4 — Energy / EV / data-economy pack (Priority: P2)
As the **PO**, I want a light pack (keywords, expected columns, KPIs, recipe, decision template, deck storyline, sample brief) for energy transition / EV / digital economy (Viet Nguyen-Tien's LSE topic), so a brief on these themes is recognised.

**Acceptance**: **Given** `scenarios/briefs/nang_luong_xe_dien.md`, **When** parsed, **Then** `pack.id == "energy_ev_data_economy"` and the target maps to a real column of the recipe dataset (test in `tests/test_brief.py`).

### User Story 5 — Contest-day dry-run checklist (Priority: P2)
As the **LEAD**, I want one checklist per pack that a non-coder can follow (commands, expected outputs, go/no-go), so CP1 at 12:30 on 20/11 is met.

### Edge cases
- Provincial data mixes 63-province years (≤ 2024) and 34-province years (2025+) → normalise all to 34 and flag "series break 2025" caveat; keep 63-level table for non-additive indicators.
- Ratios (%, per capita) after merging → recomputed from components; if components missing, keep old-province level and say so.
- WDI missing values (fiscal series often missing for MMR, LAO) → reported as missing per country × indicator, never imputed for benchmarks.
- ASEAN membership: Timor-Leste was admitted in October 2025 [NEEDS CLARIFICATION: confirm and decide whether to include TLS in the ASEAN median; WDI fiscal coverage for TLS is sparse].
- World Bank API rate-limit/outage → tenacity retry + cache; fallback CSV.
- Firm data from banks/insurers (different statement structure) → excluded from ROE drivers by sector filter with a caveat.
- Licences: FiinGroup data terms unknown → [NEEDS CLARIFICATION: may the extract be redistributed in the submission?]; vnstock licence must be checked before use (not integrated today).

## Requirements
- **FR-401**: `scenarios/public_finance/sources.yaml` + `README.md` (where to download: MOF "công khai ngân sách", GSO/NSO yearbook tables), column alias list, 63→34 aggregation rules. **Engine gap (verified)**: `conform.agg` in `engine/vlkit/de/conformed.py` is one function for the whole source (`mean|sum|min|max|first`), so it cannot sum additive budget columns while recomputing ratios. Extend it to accept a per-column mapping `agg: {default: sum, columns: {col: mean|sum|…}}` plus `ratios: {name: [numerator, denominator]}` recomputed after aggregation (backward compatible with the string form).
- **FR-402**: `scenarios/wdi_asean/sources.yaml` — WDI API sources per indicator (same 12 indicators as `tools/fetch_wdi.py`), countries = ASEAN (+ optional comparators), keys `country: [countryiso3code, iso3]`, `year: [date, year]` (WB JSON is flattened by `pd.json_normalize(sep="__")` in `connectors.py`, so records expose `countryiso3code`, `date`, `value`, `indicator__id`, `country__value`; each source's `value` column is prefixed with the source name in the integrated OBT); SQL view for VN-vs-ASEAN gap.
- **FR-403**: `scenarios/packs/energy_ev_data_economy.yaml` + `scenarios/briefs/nang_luong_xe_dien.md` + sources recipe (OWID energy CSV CC BY 4.0, Ember yearly electricity CC BY 4.0, WDI `EG.*` indicators) [NEEDS CLARIFICATION: IEA Global EV data licence before adding it as a source].
- **FR-404**: `scenarios/packs/listed_firms_market.yaml` gains `column_aliases` for FiinPro-style headers (VI/EN) and a `sector_exclude_for_roe` list.
- **FR-405**: `specs/004-scenario-packs/checklists/dry-run.md` filled for each pack with real numbers from the run (timings, quality before/after, #insights, #significant, overflow check), dated.
- **FR-406**: `tests/test_brief.py` covers the new sample brief; `tests/test_conformed.py` gets an offline test for the WDI recipe using the practice CSV.

### Non-functional
- **NFR-401**: Each dry run ≤ 5 min on the 2-CPU laptop (pipeline + reports), measured.
- **NFR-402**: All sources record `license:`; `docs/licenses.md` updated.

## Success criteria
- **SC-401**: 3 packs (public finance, listed firms, WDI ASEAN) have a completed dry-run row with go = ✅ by 18/11 evening.
- **SC-402**: New brief selects `energy_ev_data_economy` (test).
- **SC-403**: VN-vs-ASEAN gap view returns one row per indicator × year with no hand-typed numbers.

## Clarifications

- WDI uses the ASEAN peer cohort available through 2024. Timor-Leste joined on 26 October 2025. Missing Viet Nam tax observations in the practice panel remain null. Use GDP per capita to practise benchmarking with observed Viet Nam values. [ASEAN admission notice](https://asean.org/forging-a-new-era-timor-leste-admitted-into-asean/)
- Use the listed-firms practice workbook and common VI/EN header aliases. Verify the actual FiinGroup export and its redistribution terms when available.
- Use the 2026-09-10 OWID release and Ember for the energy recipe. Run the supplemental WDI indicators separately. Defer IEA EV inputs until the source and applicable licence are confirmed.
- Use an additive measure from one boundary vintage and one accounting stage per year for public finance. Record the file provenance and leave missing KPI inputs blank.
