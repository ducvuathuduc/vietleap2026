# B-HOUSE Banking from the household side: verify the data for depositor and borrower decisions in Vietnam
Repo (read only): C:\Users\dieut\Desktop\Money\vietleap
## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (challenge, rubric, judges, mentors, owner rules) and DECISION.md.
- The owner has fixed the area: FINANCE AND BANKING IN VIETNAM. The product must rest on real observed data, answer a clear
  question for a named user (households must be able to use it), and support a policy decision. Judges include Ms. Nguyen Ngoc
  Phuong Trang (Shinhan Bank), Dr. Sacha Dray (World Bank), Dr. Pham Thai Binh (UEH finance); mentors include Dr. Nguyen Van Phuc
  (econometrics, banking/fintech), Dr. Nguyen Tri Dung (behavioural/financial economics), Dinh Xuan Phan Anh (FiinGroup).
- Already verified today: TinyFish read deposit rates for 10 banks (36 rows confirmed) in ..\D-UNLOCK\samples\deposit_rates_today.csv;
  FiinQuant get_ratios works for banks 2021+ with NPL, LDR, NIM (..\R-SUPPLY\SUPPLY.md §1).
## Do (write HOUSE.md)
1. Deposit insurance: the current insured limit per depositor per institution and its legal basis; DIV (div.gov.vn) statistics on
   insured depositors, insured deposits, premium rates; any published share of deposits above the limit. Real calls, sample rows.
2. SBV monetary statistics: monthly deposits of residents/households and credit (total, by sector), interest-rate statistics
   (average deposit/lending rates), and how far back they go. Exact URLs, HTTP status, sample rows.
3. Borrowers: for 6-10 large banks, the published mortgage reference/base rate used after teaser periods (if public), the margin
   formula, prepayment fees; average lending rates from SBV. Use TinyFetch first, TinyFish only for client-rendered pages; verify
   every number against the page.
4. Household allocation series: VSDC new securities accounts monthly, gold demand (World Gold Council Vietnam), deposits growth;
   enough points for a 2021-2026 time series?
5. For each dataset: what household decision it powers, and whether a typical student team would find it.
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. A negative claim
  ("not available") needs the exact URL/endpoint and response you got.
- Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets. FiinQuant raw data stays in this folder
  (<= 20 raw rows per sample file; computed aggregates are fine). TinyFish agent runs allowed up to USD 4 (log run id, steps, cost).
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.
- Timebox: 35 minutes. Write the named findings file and REPORT.md (max 15 lines) in THIS folder.