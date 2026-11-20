GO-WITH-CHANGES
Status DONE C-FTSE
Deliverables CRIT-FTSE.md, probe.py, aggregates.json, samples/calls.json and 39 capped sample CSVs in the task folder.
Live command .venv/Scripts/python.exe -B <task>/probe.py exited 0. Logged 43 calls, including intentional permission-boundary checks.
Artifact verification with .venv/Scripts/python.exe -B via stdin exited 0. Recomputed event and basket tables, checked coverage and reconciliations, and confirmed every raw CSV has at most 20 rows.
Read-only git diff --stat and git diff --cached --stat both exited 0 with no tracked changes. Git warned that the global ignore file was inaccessible.
Published evidence checked against FTSE, HOSE, MSCI, the FiinTrade chart, and TCBS and SSI filings.
Foreign net on VNINDEX was +VND 1,255bn at the rebalance and -VND 664bn at the effective session.
The 78-broker margin worksheet and matching SSC aggregate were unavailable. The FiinTrade chart verifies the rounded series high and the press attributes the more precise figure to FiinTrade.
Residual coverage and historical memberships require reconciliation. The 27-stock check uses the ACBS August list. The live domestic investor breakdown was blank for HPG in the September event window.
No product edits or causal model. The recorded flows and quarter-end debt do not identify who financed each purchase.
