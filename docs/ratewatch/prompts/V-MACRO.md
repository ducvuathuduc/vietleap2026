# V-MACRO Real-time and history data for a rate outlook, plus crowding of the forward-rate idea
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
## Do (write MACRO.md)
1. SBV interbank rates (overnight to 12 months, daily): find the official page or file on sbv.gov.vn that publishes them, how far back,
   format; same for open-market operations (OMO) results and the SBV central exchange rate. Real calls, sample rows.
2. SBV monthly statistics: average deposit/lending rates, deposits and credit growth, LDR: history depth via the stats pages or press
   archive; save a sample series (at least 12 months) if obtainable.
3. Market signals already reachable: FiinQuant daily bank-stock index or bank P/B, Vietcombank FX history, BTMC gold. Which can feed a
   daily "rate pressure" indicator? Propose 3 indicators with formulas and show one computed from real rows.
4. Crowding: Vietnamese tools or reports that already show deposit yield curves, implied forward rates, rate outlooks for savers, or
   bank risk next to rates (check taichinh.com, webgia, timo, simplize, Infina, Finhay, broker bank reports). Name + URL + what they show.
5. Verdict: can we show a defensible short-horizon outlook (state the method: market-implied forwards, a nowcast regression, or none)?
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. Negative claims need the
  exact URL and response. Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets.
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.
- Timebox: 30 minutes. Write the named findings file and REPORT.md (max 15 lines) in THIS folder.