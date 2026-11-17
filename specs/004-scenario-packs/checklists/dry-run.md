# Dry-run checklist — one row per pack (fill with values copied from the run; never estimate)

Run on the contest laptop (2 CPU / 7 GB). Before each run: `source tools/env.sh && export NO_PROXY=localhost,127.0.0.1`. Do not run `npm run build` at the same time.

| Step | Command | Expected output | Go / no-go |
|---|---|---|---|
| 1 Brief | `make brief F=<brief.md> D=<data>` | `brief.json` with pack id + target column | pack id matches the table below |
| 2 Pipeline | `python de.py run <sources.yaml> --primary <src> --serve` (or `de.py file`) | `out/<ds>/pipeline.json`, `quality.json`, `lineage.json`, `conformed.json` when keys are shared | no step `status: failed` |
| 3 Quality | open **Chất lượng** | score before → after per table | after ≥ before |
| 4 Join coverage | **Pipeline** → "Độ phủ ghép nối" | match % per source × key | ≥ 90% or explained |
| 5 Insights | **Insight** | ≥ 3 insights with p < 0.05 and a decision link | ≥ 3 |
| 6 Deck | `out/<ds>/deck.pptx`, `pitch.md` | `deck_overflow()` = `[]` | no overflow |
| 7 AI offline | **Hỏi AI** on 3 elements without key | engine text, no error | 3/3 |

## Results · 17/11/2026 · recipe commit `ed2bd08`

Pipeline time is the sum of the stage times in `pipeline.json`. The significance count includes only reported p-values below 0.05. Overflow is the output of `deck_overflow()` for the EN and VI decks.

| Pack and run | Data | Pipeline s | Quality before → after | Join match | Insights / p < 0.05 | Overflow EN / VI | Result |
|---|---|---:|---|---|---:|---|---|
| public_finance_province `0fc411ef` | Official 2024–2025 earmarked transfer estimates. See [sources and terms](../../../scenarios/public_finance/README.md). | 6.01 | 85.9 → 98.0 | Single source. 126 raw rows → 68 province-year rows. | 7 / 2 | 0 / 0 | Practice only. Transfers cover one budget component. The full autonomy check needs provincial revenue and expenditure and a third significant insight. |
| listed_firms_market `6cf63d41` | `vn_firms_2021.xlsx` (practice only) | 19.46 | Q1 87.9 → 98.0, Q2 87.5 → 97.6, Q3 87.4 → 97.4, Q4 87.4 → 97.6 | Stacked 3,962 rows on the same schema. | 10 / 6 | 0 / 0 | Data check passed. ROE model excluded 15 financial-sector rows. |
| development_indicators / wdi_asean `65c1e379` | WDI practice CSV, CC BY 4.0 with indicator exceptions | 9.29 | Tax 85.0 → 95.0, GDP/capita 90.0 → 99.7 | 100% on each key join (250 country-year rows). | 12 / 6 | 0 / 0 | Offline GDP/capita check passed. Live WDI timed out. Viet Nam tax observations in the practice data are missing. |
| energy_ev_data_economy `0222f1fb` | Pinned OWID release + Ember (terms in [licenses](../../../docs/licenses.md)) | 9.15 | OWID 97.3 → 97.3, Ember 88.8 → 100.0 | 91.5% (257 / 281). | 12 / 7 | 0 / 0 | Data check passed from local downloads. Supplemental WDI sources need a successful fetch. |

All four runs produced both deck and pitch languages. Browser AI checks and visual slide render review remain pending.
