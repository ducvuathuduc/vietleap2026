# Tasks: 004 Scenario packs & dry runs

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

## Phase A — Engine support
- [x] T401 `2cf9d34` Test-first per-column aggregation and ratio recomputation across a provincial merger.
- [x] T402 `2cf9d34` Implement per-column `agg` and `ratios`, preserving string `agg`.
- [x] T403 `2cf9d34` Test `gold.v_*` views, blocked SQL and rejection by `IngestIn`.
- [x] T404 `2cf9d34` Execute validated `post_sql` views in one transaction on the writer connection.
- [x] T405 `2cf9d34` Commit engine support and tests.

## Phase B — Recipes & packs
- [x] T406 `ed2bd08` WDI API recipe, offline panel, gold gap view and DuckDB test.
- [x] T407 `ed2bd08` Provincial budget recipe, aliases and additive rollup to new boundaries.
- [x] T408 `ed2bd08` Listed firms aliases, multi-sheet OBT and financial-sector exclusion from ROE drivers.
- [x] T409 `ed2bd08` Energy/EV pack, sample brief and OWID/Ember recipes with supplemental WDI indicators.
- [x] T410 `ed2bd08` Commit and publish pack recipes.

## Phase C — Dry runs (17/11–18/11)
- [x] T411 `ed2bd08` Collect and reconcile the official earmarked transfer estimates for 2024 and 2025. Record source URLs and checksum.
- [x] T412 `ed2bd08` Run four packs. Record run IDs, measured criteria and outstanding checks in the [checklist](checklists/dry-run.md).
- [x] T413 `ed2bd08` Publish the dry-run checklist and progress alongside the recipe commit.

## Dependencies
T401→T402; T403→T404→T406; T407/T408/T409 parallel after T402; T411→T412.
