# REPORT — D-UNLOCK
Status: **DONE** (all three sources tested with real calls; one negative result proven, not assumed). 12:25 +07.

Acceptance commands (run fresh at 12:20–12:24, this folder):
| command | exit |
|---|---|
| `python gold_csv.py` (writes+sanity-checks samples/gold_history_sample.csv) | 0 |
| `python px_csv.py` (pxweb_tables.csv 44 rows, pxweb_sample.json 5,198 B) | 0 |
| `python build_deposits.py` (deposit_rates_today.csv 89 rows, tinyfish_runs.csv 10 runs) | 0 |
| `python -m py_compile build_deposits.py px_csv.py gold_csv.py px_tables.py verify_html.py tf_deposits.py tf_collect.py` | 0 |
| `git -C <repo> status --short` | 0, **no output** (repo untouched) |

Deliverables: UNLOCK.md (findings+evidence), samples/{gold_history_sample.csv, deposit_rates_today.csv, pxweb_tables.csv,
pxweb_sample.json, pxweb_post_attempts.json, tinyfish_runs.csv} (all < 22 KB), http/ raw evidence, scripts in this folder.

Headline results
1. Gold: BTMC `/ProductHome/getGoldDate?date=DD/MM/YYYY` (JSON, robots allows) → **2017-05-02 … 2026-11-20**, SJC bar + ring gold.
   Unit trap: values are thousand VND per **chỉ** → ×10,000 = VND/lượng (verified against the intraday JSON API ×1,000 and world parity +22.7 %).
   Full daily backfill = 3,490 requests ≈ 2.9 h.
2. Deposit rates: TinyFish 10/12 banks COMPLETED, **$1.95** of $6, 89 rows; only **36/89 confirmed** by TinyFetch/raw HTML
   (the bank pages are client-rendered, so `COMPLETED` ≠ proof; 53 rows `agent_only_unconfirmed`, Agribank/MB/Techcombank/VPBank 0/10).
   SBV: policy-rate menu only, no historical bank-level table. TPBank/VIB untested at the 45-min deadline.
3. NSO PXWeb: metadata works (127 tables, **44 with a 70/71-value province dimension, years 1995→2025**) but the **POST query route
   does not exist** on this deployment (9 attempts → 404 or JSON table list); CPI/`Chỉ số giá` (V11.01+) exists only in the WebForms
   frontend, so cells need a viewstate scraper (2–4 h). Nothing invented: no cells claimed without a 200 payload.

Not done / risks for Kiro: 2 banks unrun (budget/time), no second independent reader for 53 deposit rows, PXWeb cells not extracted,
gold history before 2017-05-02 assumed absent (probed 2014/2015/2016 only at 15/06 and 15/12).
