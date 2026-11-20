# REPORT — B-HOUSE
Status: DONE
Acceptance commands (all run live this session, 12:11–12:45 +07):
- curl sbv.gov.vn robots + 4 stat pages: HTTP 200 x4 (exit 0) — credit by sector, deposits (dân cư 11.434.266 tỷ +10,63% YTD, 8/2026), individual accounts Q2/2026, LDR.
- curl dttktt.sbv.gov.vn: exit 28 timeout — negative claim verified (rate portal down); SBV avg rates 9/2026 verified via Dan trí fetch (lending 8,4–10,9%/năm).
- TinyFetch (free, 3 batches, 21 URLs): DIV limit 125M (QĐ 32/2021/QĐ-TTg, eff 12/12/2021) + 87%→91% fully-insured + premium 0,15%/năm (TT 04/2026/TT-NHNN, eff 01/5/2026) [snippet-verified x2]; WGC country XLSX quarterly from 2010; VSDC monthly account posts through 10/2026 (+252,4k new).
- Negative claims with evidence: bank base-rate pages (VCB/BIDV/MB/ACB/Agribank) are JS shells or 404; VPBank/Sacombank not returned; prepayment fees not fetched (timebox).
Files: HOUSE.md (findings, all rows cited URL+time+status), samples/ (4 SBV HTML + 2 TinyFetch outputs).
Not done: DIV above-limit deposit share (not published on fetched pages); prepayment-fee schedules; TinyFish agent runs (0/4 USD used).
Risks: premium rate rests on two search snippets, not full circular text; SBV monthly history needs article-archive scraping (not built here).
