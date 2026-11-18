# VietLeap Insight — Evidence dashboard

Judge-facing dashboard for VietLeap 2026, built with [Evidence](https://evidence.dev)
(v40.1.8, MIT). Only the analysis backend is custom — the shell is Evidence.

- **Data:** reads the gold/silver Parquet lake (`../data/lake/`) through an
  in-memory DuckDB source (`sources/warehouse/`). The warehouse file
  (`data/warehouse.duckdb`) is written by DuckDB 2.0, which Evidence's bundled
  DuckDB 1.4 cannot open — Parquet is the interchange format.
- **Pages:** `pages/index.md` — Overview (business question → KPIs → chart →
  insights → decision). Vietnamese labels, English identifiers.
- **Run:** `npm install` once, then `npm run sources` (re-run queries) and
  `npm run build` (static site in `build/`). Serve locally to preview.
- **New data (20/11):** replace the Parquet files in `data/lake/`, re-run
  `npm run sources && npm run build` — no code changes needed.
