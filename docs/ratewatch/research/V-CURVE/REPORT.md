# REPORT — V-CURVE
Status **DONE**. Findings `V-CURVE\CURVE.md`; data `V-CURVE\samples\curve_today.csv` (110 rows, 8 banks, 11 terms);
evidence `http\`; no repo file edited, no git write, no process killed, nothing installed.

Acceptance commands, run fresh (exit codes from this session):
- `build_curve.py` → **0** (`rows 110 banks 8`; `==4.75 19 / below 26 / above 0`; `median f6 simple 5.553 n 9`, `f12 5.362 n 9`)
- `probe_html.py` (34 bank URLs, robots.txt per host, ≥2.2 s) → **0**, `http/probe_html.csv`
- `fetch_all.py` (TinyFetch, 22 bank URLs) → **0**, 8 banks with a table or PDF link
- `get_pdf.py` (6 bank PDFs, pdfplumber) → **0**, 5 usable texts (MSB PDF is a scan)
- TinyFish: `71c715fe-…` MSB COMPLETED 13 steps, `50cd817e-…` Sacombank COMPLETED 6 steps, ≈USD 0.30 of 8 spent

Grades: 22 verified (Sacombank counter PDF+agent, OCB online table+PDF), 88 agent_only. Ceiling: 19/45 quotes at
exactly 4.75 for 1–5 m, 0 above, median 5→6 m jump +1.15 pp. Forwards (simple interest): median 6m-in-6m **5.55 %**,
12m-in-12m **5.36 %** (brief formula 5.70 % / 5.70 %).

Not done: 23 banks returned no household VND rate (403/404/TLS/client-render/no PDF/robots) — BIDV, Agribank,
Vietcombank, LPBank, Techcombank, VIB, VPBank, SHB, HDBank, SeABank, NCB, KienlongBank, TPBank, PGBank, Saigonbank,
PVcomBank, BaoVietBank, CBBank, BVBank, GPBank, OceanBank, ABBank, BacABank. No history, no OCR.

Risks: OCB counter **contested** (page 5.90/6.20 vs its own PDF 5.73/5.83 at 6/12 m); MSB agent read the online tab
although asked counter; ACB column mapping sparse (4.00 flat 1–6 m, single reader); VietinBank's 7.68 % forward is a
2.10 %-floor artefact — do not quote.
