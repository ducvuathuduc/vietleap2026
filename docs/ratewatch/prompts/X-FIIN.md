# X-FIIN Use FiinQuant hard for the bank side: risk profile, market view and flows for all 28 listed banks
Repo (read/run only): C:\Users\dieut\Desktop\Money\vietleap (FiinQuantX 0.1.73 in .venv; login from .env.local)
## Context
- Read ..\CONTEST.md and your ..\B-BANKDATA\BANKDATA.md. Product direction: a household deposit decision tool. For each bank the saver
  sees a "bank safety profile" next to its rate. FiinQuant is the only source of comparable bank fundamentals and market data.
## Do (write FIIN.md; scripts and outputs in THIS folder; raw FiinQuant rows <= 20 per sample file, aggregates unlimited)
1. For all 28 banks, latest 8 quarters: NPL, loan-loss coverage, LDR, equity/assets (or capital proxy), ROA, NIM, CASA if present,
   loan growth, deposit growth, total assets. Coverage per field. Output an aggregate table aggregates\bank_quarter_metrics.csv.
2. Market view, daily for the last 12 months: close, P/B, 60-day realised volatility, max drawdown, foreign net flow and room.
   Output aggregates\bank_market_daily_summary.csv (per bank: latest P/B, vol, drawdown, 20d foreign net).
3. Propose a transparent safety profile: per metric the percentile rank among the 28 banks (no weights invented), plus a short list of
   "flags" with thresholds taken from a cited rule (e.g. SBV prudential ratios: LDR cap, NPL 3% target). Cite the circulars.
4. Join check with today's rates: ..\D-UNLOCK\samples\deposit_rates_today.csv and ..\V-CURVE\samples\curve_today.csv on bank code.
   Spearman rate vs each risk metric, n, and a scatter-ready CSV. Say plainly what n allows.
5. Terms: quote the FiinQuant terms on derived/aggregated data and draft a 5-line email (Vietnamese) to mentor Dinh Xuan Phan Anh
   asking (a) which bank fields are recommended, (b) whether percentile ranks and charts derived from FiinQuant may be shown on a public
   judge site with attribution. Save as email_phananh.txt.
## Timebox: 45 minutes. Write FIIN.md and REPORT.md (max 15 lines) in THIS folder.
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. Negative claims need the
  exact URL and response. Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets.
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.