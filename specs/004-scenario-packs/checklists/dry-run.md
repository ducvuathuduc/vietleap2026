# Dry-run checklist — one row per pack (fill with values copied from the run; never estimate)

Run on the contest laptop (2 CPU / 7 GB). Before each run: `source tools/env.sh && export NO_PROXY=localhost,127.0.0.1`. Do not run `npm run build` at the same time.

| Step | Command | Expected output | Go / no-go |
|---|---|---|---|
| 1 Brief | `make brief F=<brief.md> D=<data>` | `brief.json` with pack id + target column | pack id matches the table below |
| 2 Pipeline | `python de.py run <sources.yaml> --primary <src> --serve` (or `de.py file`) | `out/<ds>/pipeline.json`, `quality.json`, `lineage.json`, `conformed.json` when ≥ 2 sources | no step `status: error` |
| 3 Quality | open **Chất lượng** | score before → after per table | after ≥ before |
| 4 Join coverage | **Pipeline** → "Độ phủ ghép nối" | match % per source × key | ≥ 90% or explained |
| 5 Insights | **Insight** | ≥ 3 insights with p < 0.05 and a decision link | ≥ 3 |
| 6 Deck | `out/<ds>/deck.pptx`, `pitch.md` | `deck_overflow()` = `[]` | no overflow |
| 7 AI offline | **Hỏi AI** on 3 elements without key | engine text, no error | 3/3 |

## Results (fill in; date + commit hash)
| Pack | Data (source, licence) | Date | Commit | Pipeline s | Quality before→after | Join match % | #insights / #p<0.05 | Overflow | Go? | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| public_finance_province | [NEEDS CLARIFICATION: table to collect, T411] | | | | | | | | | |
| listed_firms_market | `data/practice/vn_firms_2021.xlsx` (practice only, see docs/licenses.md) | | | | | | | | | |
| development_indicators / wdi_asean | WDI API, CC BY 4.0 (fallback practice CSV) | | | | | | | | | |
| energy_ev_data_economy | OWID/Ember/WDI, CC BY 4.0 | | | | | | | | | |
