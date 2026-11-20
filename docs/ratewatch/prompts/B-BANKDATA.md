# B-BANKDATA What bank-level data FiinQuant really gives for every listed Vietnamese bank, and a first test of "do riskier banks pay depositors more?"
Repo (read/run only): C:\Users\dieut\Desktop\Money\vietleap  (FiinQuantX 0.1.73 in the repo .venv; login from .env.local)
## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (challenge, rubric, judges, mentors, owner rules) and DECISION.md.
- The owner has fixed the area: FINANCE AND BANKING IN VIETNAM. The product must rest on real observed data, answer a clear
  question for a named user (households must be able to use it), and support a policy decision. Judges include Ms. Nguyen Ngoc
  Phuong Trang (Shinhan Bank), Dr. Sacha Dray (World Bank), Dr. Pham Thai Binh (UEH finance); mentors include Dr. Nguyen Van Phuc
  (econometrics, banking/fintech), Dr. Nguyen Tri Dung (behavioural/financial economics), Dinh Xuan Phan Anh (FiinGroup).
- Already verified today: TinyFish read deposit rates for 10 banks (36 rows confirmed) in ..\D-UNLOCK\samples\deposit_rates_today.csv;
  FiinQuant get_ratios works for banks 2021+ with NPL, LDR, NIM (..\R-SUPPLY\SUPPLY.md §1).
## Do (write BANKDATA.md)
1. List every listed bank ticker (BasicInfor / ICB Banks) with exchange and ownership type (state-owned vs joint-stock, from a cited source).
2. get_ratios for all banks, quarterly and annual, 2021 -> latest: enumerate EVERY returned field with its non-null coverage
   (banks x periods). Find fields for: cost of funds / interest expense on deposits, yield on earning assets, NIM, NPL and group-2
   loans if any, loan-loss coverage, LDR, CASA, capital or equity/assets, ROA/ROE, cost-income, loan growth, deposit growth, total
   assets. Save a field-coverage table as samples\bank_fields.csv.
3. Market side for banks: daily price and stock P/B, foreign ownership/room. Coverage only.
4. First real numbers: for the latest complete quarter, the cross-bank Spearman correlation between a deposit-price measure
   (cost of funds if it exists; else the 12-month online rate from deposit_rates_today.csv for the banks covered) and NPL, loan-loss
   coverage, LDR, equity/assets. Also a 2021-2026 panel sketch: how many bank-quarters have both. Show the computation and n.
5. Crowding: academic papers on depositor market discipline in Vietnamese banks (Google Scholar/SSRN/journals, URL + year + finding),
   and any Vietnamese consumer tool that ranks banks by safety next to their deposit rates.
6. FiinQuant terms: which of these outputs may be shown publicly as aggregates (quote the terms page).
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. A negative claim
  ("not available") needs the exact URL/endpoint and response you got.
- Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets. FiinQuant raw data stays in this folder
  (<= 20 raw rows per sample file; computed aggregates are fine). TinyFish agent runs allowed up to USD 4 (log run id, steps, cost).
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.
- Timebox: 35 minutes. Write the named findings file and REPORT.md (max 15 lines) in THIS folder.