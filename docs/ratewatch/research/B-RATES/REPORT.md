# REPORT B-RATES — DONE (with a stated coverage gap)
RATES.md, samples\rates_panel_today.csv, samples\rates_gap_by_term.csv, samples\rates_history_sample.csv written in this folder.

Acceptance commands (run 13:12–13:14 Asia/Saigon 20/11/2026):
- `python build_panel.py` -> **exit 0**; panel rows=289, cols=13, banks=22 blocks (21 banks + VCB Neo), channels=[counter,online], terms=[1,3,6,9,12,18,24,36]; grades verified=21, agent_only=268.
- `python history.py` (urllib) -> exit 0 but 0 snapshots: Wayback refuses urllib TLS (`SSLCertVerificationError: Basic Constraints of CA cert not marked critical`); re-run through curl -> 3 banks x 4 dates, CDX `[]` (HTTP 200) for 2 banks and 429 for 1; saved as 13 rows in rates_history_sample.csv.
- `probe.py` -> exit 0; 35 bank URLs + 4 aggregators in http\probe.csv (7/34 bank pages server-rendered; MB/SHB 403; 11 banks 404; 4 TLS errors).

Delivered: today's counter+online VND panel (8 terms) with per-row bank source URL and grade; gap stats by term (median +0.10 pp at 1 m up to +0.70 pp at 9 m; max +1.85 pp BIDV 6/9 m; 12 m online min 5.20 ACB / median 6.25 / max 7.00); history verdict with exact URLs and responses.
Not done: 12 banks missing (HDBank, SeABank, SCB, NCB, KienlongBank, Saigonbank, PGBank, BVBank/VietABank, BaoVietBank, GPBank, OceanBank, CBBank) — client-rendered/404, would need ~12-18 min of TinyFish (≈USD 2.4); no TinyFish run spent (USD 0.00).
Risks Kiro must check: 268/289 rows rest on one aggregator reader (only 21 numbers cross-seen on bank pages); the 2nd-reader test proves presence, not cell position. Sacombank 1 m counter 0.50 % and VIB 12 m online 7.00 % are implausible — excluded from headline numbers. `effective_date` = aggregator stamp, not each bank's own effective date.
