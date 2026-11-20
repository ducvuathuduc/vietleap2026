# T1 follow-up 1 from Kiro (do after your current live run)
1. Sacombank PDF: the counter series received the online 6-month rate (6.30%; counter is 5.70% on the same sheet, SHA 3b2e6b5f...).
   Scope the PDF parser to the right table section per channel; add a regression test with a trimmed fixture of that page.
2. Amount tiers (CONTRACT.md section E): parse every tier on every sheet into tier_min_vnd / tier_max_vnd. OCB online 06/11/2026
   (https://webocb-api.ocb.com.vn/Resources/Files/20261106091027_3-06.11.2026-bang-lai-suat-tien-gui-khcnvn-web-vnd.pdf) must yield
   6 m: 6.00 / 6.10 / 6.20 and 12 m: 6.30 / 6.40 / 6.50 for <100 tr, 100-500 tr, >500 tr. Add a test for it and for one bank without tiers.
3. Rerun the live ingest and report coverage (banks, rows, tiers found, verified share).