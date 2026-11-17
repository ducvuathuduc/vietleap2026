# Tasks: 004 Scenario packs & dry runs

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Engine support
- [x] T401 `2cf9d34` Test-first per-column aggregation and ratio recomputation across a provincial merger.
- [x] T402 `2cf9d34` Implement per-column `agg` and `ratios`, preserving string `agg`.
- [x] T403 `2cf9d34` Test `gold.v_*` views, blocked SQL and rejection by `IngestIn`.
- [x] T404 `2cf9d34` Execute validated `post_sql` views in one transaction on the writer connection.
- [x] T405 `2cf9d34` Commit engine support and tests.

## Phase B — Recipes & packs
- [ ] T406 [P] `scenarios/wdi_asean/{sources.yaml,views.sql,README.md}`; offline test using `data/practice/wdi_asia_fiscal_panel.csv` filtered to ASEAN (`tests/test_conformed.py::test_wdi_asean_gap_view_offline`) → T404.
- [ ] T407 [P] `scenarios/public_finance/{sources.yaml,README.md}` + `column_aliases` in `public_finance_province.yaml`.
- [ ] T408 [P] `listed_firms_market.yaml` aliases + `domains.apply_firm` `sector_exclude_for_roe` + test in `tests/test_pipeline_smoke.py` (banks excluded from ROE drivers).
- [ ] T409 [P] `energy_ev_data_economy.yaml`, `scenarios/briefs/nang_luong_xe_dien.md`, `scenarios/energy/sources.yaml` (verify URLs + licences, record in `docs/licenses.md`); `tests/test_brief.py` expects the pack.
- [ ] T410 Commit + push "feat(packs): T406–T409 WDI ASEAN recipe, public finance + energy/EV packs, firm aliases".

## Phase C — Dry runs (17/11–18/11)
- [ ] T411 RQ: collect one real provincial budget table (MOF công khai ngân sách or GSO) — record URL, date, licence in `scenarios/public_finance/README.md` [NEEDS CLARIFICATION: which table is downloadable without login].
- [ ] T412 Run all 4 dry runs on the contest laptop; fill `checklists/dry-run.md` with numbers copied from outputs; open issues for any failure → T406–T411.
- [ ] T413 Commit + push "docs(packs): T411–T412 dry-run results"; update `specs/README.md`, `docs/ROADMAP.md`.

## Dependencies
T401→T402; T403→T404→T406; T407/T408/T409 parallel after T402; T411→T412.
