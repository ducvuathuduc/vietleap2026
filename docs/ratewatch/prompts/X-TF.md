# X-TF TinyFish full-coverage test: can we read EVERY Vietnamese commercial bank's deposit rates today?
Repo (read/run only): C:\Users\dieut\Desktop\Money\vietleap
## Context
- Read ..\CONTEST.md, your ..\V-CURVE\CURVE.md and ..\B-RATES\RATES.md. Last time only 8 banks were read directly and TinyFish was
  barely used (USD 0.30). The owner says: use TinyFish hard; too little data is not acceptable. This test decides the product.
- TinyFish agent API: POST https://agent.tinyfish.ai/v1/automation/run-async {url, goal}, header X-API-Key = env TINYFISH_API_KEY
  (never print it); poll GET /v1/runs/{id}; 2 concurrent runs; about USD 0.016 per step. TinyFetch POST https://api.fetch.tinyfish.ai is free.
## Do (write XTF.md)
1. Bank list: all ~30 commercial banks licensed in Vietnam (state-owned, joint-stock; cite the SBV list URL). For each find the
   official individual deposit-rate page or PDF (search the bank site; many publish "biểu lãi suất" PDFs).
2. For EVERY bank where plain fetch / TinyFetch / PDF text does not give the table, run the TinyFish agent with one standard goal:
   return JSON rows {term_months, channel: counter|online, rate_pct, effective_date, product_name} for individual VND term deposits,
   interest paid at maturity, terms 1-36 months. Retry once with a refined goal if empty. Budget USD 15 total; log run id, steps, cost.
3. Second reader for each bank: a different method (TinyFetch text, PDF text, or a second TinyFish run with a different goal, e.g.
   "read the PDF linked on this page"). Grade per row: verified (2 readers agree), agent_only, contested (readers differ).
4. Coverage table per bank: method that worked, rows, terms covered, channels covered, grade counts, seconds, USD.
   Save samples\rates_all_banks.csv. Target >= 28 banks with >= 6 terms. Report honestly what failed and why.
5. Daily-run estimate: total steps, USD and minutes for one full run; which banks are stable to plain fetch.
## Timebox: 45 minutes. Write XTF.md and REPORT.md (max 15 lines: banks covered, rows, verified share, USD) in THIS folder.
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. Negative claims need the
  exact URL and response. Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets.
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.