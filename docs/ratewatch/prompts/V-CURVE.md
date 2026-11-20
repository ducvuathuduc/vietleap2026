# V-CURVE Verify the deposit curve from bank pages directly, the ceiling kink, and implied forwards
Repo (read/run only): C:\Users\dieut\Desktop\Money\vietleap
## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (rubric, judges, owner rules). Area is fixed: banking/finance in Vietnam,
  household deposits. Prior findings (read only what you need): ..\B-RATES\RATES.md (21-bank panel, 268/289 rows from one aggregator),
  ..\B-POLICY\POLICY.md (deposit-insurance cap 350 million from Thông tư 05/2026 in force 13/7/2026; ceiling 4.75% for 1 to <6 months
  under QĐ 2411/QĐ-NHNN), ..\B-HOUSE\HOUSE.md (DIV page still shows 125 million; SBV stats pages; household deposits 11,434,266 tỷ 8/2026),
  ..\B-BANKDATA\BANKDATA.md (FiinQuant 28 banks, ratios 614/644 quarters).
- Working product idea (test it, do not defend it): a deposit decision tool for households that reads every bank's posted curve daily,
  shows where the 4.75% short-term ceiling bends the curve, derives the market-implied future rate from the curve (forward rates) to
  answer "lock 12 months now or 6 months twice", checks the insured cap per bank, and shows each bank's risk profile.
## Do (write CURVE.md)
1. Read posted individual VND deposit rates DIRECTLY from bank pages/PDFs (not aggregators) for as many of the ~30 commercial banks as
   possible, terms 1,2,3,4,5,6,9,12,18,24,36 months, counter and online. Use TinyFish (run-async + poll; budget USD 8, 2 concurrent,
   log run id/steps/cost) for client-rendered pages and TinyFetch/PDF text for the rest. Two readers per number; grade verified/agent_only.
   Save samples\curve_today.csv (bank, channel, term_months, rate_pct, page_effective_date, source_url, grade, read_at).
2. Ceiling: for terms 1-5 months, how many banks post exactly 4.75% (or 4.75 minus small steps) vs below; size of the jump between
   5 and 6 months per bank. Table + counts.
3. Implied forwards: for each bank with verified 6 and 12 months (and 12 and 24), the implied 6-month rate 6 months ahead
   f = ((1 + r12)^(1) / (1 + r6)^(0.5))^(1/0.5) - 1 using simple-interest conventions the bank page states (say which). Report median.
4. A rerunnable collector design: which banks need TinyFish vs plain fetch, steps and cost per daily run, failure modes.
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. Negative claims need the
  exact URL and response. Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets.
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.
- Timebox: 40 minutes. Write the named findings file and REPORT.md (max 15 lines) in THIS folder.