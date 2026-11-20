# R-SUPPLY Research with real calls: which real, reachable, unusual datasets about Vietnam could power a differentiated decision product
Repo (read/run only): C:\Users\dieut\Desktop\Money\vietleap
This is data research, not coding. Do NOT edit anything in the repo.

## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md first (challenge, rubric, owner rules, keys, known source behaviour).
- The owner wants data that few teams will use, so the product stands out. Another worker researches demand (people, decisions,
  urgency) in parallel; you focus on supply: what data exists, is reachable today, at what granularity, and what decisions it can
  power. Every dataset you list must be checked with a real call today, not from memory.
- Use pi subagents (scout / researcher) in parallel where it helps.

## Answer these (write SUPPLY.md in this task folder)
1. FiinQuant capability map: introspect FiinQuantX 0.1.73 in the repo .venv (`.\.venv\Scripts\python.exe`), list every public
   function, and make one minimal call per category (login with FIINQUANT_USERNAME / FIINQUANT_PASSWORD from the repo .env.local,
   without printing them). Record what works, history depth, granularity, and row counts. Keep at most 20 sample rows per call.
2. Vietnamese official or market data that is machine-readable or scrapable with robots.txt allowing it. Cover at least: tax
   parameters and household-business data, bank deposit and lending rates by bank, gold prices (domestic vs world), FX, fuel price
   adjustments, electricity tariffs and consumption, land price tables and property data, CPI by item/province, household living
   standards survey, social insurance/pension, agriculture/commodity prices, customs/trade by product or partner, public
   investment, climate/flood/air quality. For each: URL, HTTP status today, format, granularity (geo + time), history, licence or
   terms, effort to ingest (hours).
3. International open data with fine Vietnam coverage (examples to test, not a limit: World Bank/IMF/ADB APIs, UN Comtrade,
   NASA POWER, Open-Meteo, OpenStreetMap Overpass, Global Solar Atlas, WorldPop, HDX, Copernicus, Google Trends). One real call
   each for the ones that matter.
4. For every dataset: one line "decisions it could power" and a rating "unusual: high/medium/low" (would a typical student team
   find and use it in 26 hours?).
5. Your top 5 "unusual but real" dataset combinations (two or more sources joined) that would let a product answer a question
   nobody else can, with the join key and the evidence that the join works on real rows.

## Rules
- Evidence for each row: URL, HTTP status, one sample record, date/time checked (Asia/Saigon). Mark anything not tested [untested].
- Try plain HTTP first, then TinyFetch (free). TinyFish agent runs are allowed up to USD 5 total for this task; log each run and cost.
- Respect robots.txt, add delays, never bypass captcha or login. Never print secrets.
- Do not install packages into the repo .venv; if you need one, `pip install --target <this task folder>\pylib` and add it to PYTHONPATH.
- Save small samples only under <this task folder>\samples\ (each < 1 MB; FiinQuant samples <= 20 rows). Nothing in the repo.
- Do not kill processes you did not start. Do not run npm build.
- Timebox: 60 minutes. If time runs out, write what you have.
- Write SUPPLY.md and REPORT.md (max 20 lines: the top 5 combinations) in THIS folder.
