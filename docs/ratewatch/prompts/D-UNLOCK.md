# D-UNLOCK Unlock three data sources other teams cannot get easily, with real rows
Repo (read/run only): C:\Users\dieut\Desktop\Money\vietleap
Data research with real calls, not product code. Do NOT edit the repo.

## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md and your own ..\R-SUPPLY\SUPPLY.md (sections 2 and 5).
- These three sources decide which product we build. Get real rows, measure depth, and save small samples.

## Do
1. Gold history (BTMC): from https://btmc.vn/gia-vang-theo-ngay.html (date picker) and the BTMC JSON API, find how far back daily
   SJC bar and ring-gold buy/sell prices go. Fetch a sample of dates across years (e.g. one date per quarter back to the earliest
   available) with >= 2 s delay, check robots.txt first. Confirm the unit (VND per lượng or per chỉ). If BTMC is shallow, test other
   public sources of SJC history (robots allowing). Save samples\gold_history_sample.csv (date, product, buy, sell, source_url).
   Report: earliest date, gaps, requests needed and minutes for a full daily backfill.
2. Bank deposit rates today with TinyFish: run the TinyFish agent (run-async + poll GET /v1/runs/{id}, header X-API-Key from the
   TINYFISH_API_KEY env var, never print it) on the official deposit-rate pages of up to 12 large banks (VCB, BIDV, Agribank,
   VietinBank, Techcombank, MB, ACB, VPBank, Sacombank, HDBank, TPBank, VIB). Ask for 1, 3, 6, 12, 24-month online and counter VND
   rates for individuals with the page's effective date. Check every returned number against the page (TinyFetch the same URL);
   COMPLETED alone is not proof. Budget USD 6 total, max 2 concurrent runs, log run id, steps and cost per run.
   Save samples\deposit_rates_today.csv (bank, channel, term_months, rate_pct, effective_date, source_url, verified_by).
   Also check the SBV page for policy/ceiling deposit rates (sbv.gov.vn) and whether any official page lists historical
   bank-level rates.
3. NSO PXWeb: make https://pxweb.nso.gov.vn/api/v1/vi return cell data (PXWeb API v1: GET the table to read its variables, then POST a
   JSON query {"query":[...],"response":{"format":"json-stat2"}} to the same table URL). List every table that has a province
   dimension and is about prices/CPI, enterprises, household businesses, investment, labour/income, or credit, with years covered.
   Save one real query result as samples\pxweb_sample.json and the table list as samples\pxweb_tables.csv.

## Rules
- Evidence per item: URL, HTTP status, sample rows, date/time checked (Asia/Saigon). Mark anything not tested [untested].
- Respect robots.txt, delays >= 2 s per site, no captcha/login bypass, never print secrets.
- Do not install packages into the repo .venv (use pip --target <this folder>\pylib if needed). Do not kill processes you did not start.
- Save outputs only in THIS folder (samples\ files < 1 MB). Nothing in the repo.
- Timebox: 45 minutes. Write UNLOCK.md (findings + evidence) and REPORT.md (max 20 lines) in THIS folder.
