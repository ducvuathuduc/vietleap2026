# B-POLICY Vietnam finance and banking 2025-2026: which question is live, who it serves, what data exists, and what is already crowded
Repo (read only): C:\Users\dieut\Desktop\Money\vietleap
## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (challenge, rubric, judges, mentors, owner rules) and DECISION.md.
- The owner has fixed the area: FINANCE AND BANKING IN VIETNAM. The product must rest on real observed data, answer a clear
  question for a named user (households must be able to use it), and support a policy decision. Judges include Ms. Nguyen Ngoc
  Phuong Trang (Shinhan Bank), Dr. Sacha Dray (World Bank), Dr. Pham Thai Binh (UEH finance); mentors include Dr. Nguyen Van Phuc
  (econometrics, banking/fintech), Dr. Nguyen Tri Dung (behavioural/financial economics), Dinh Xuan Phan Anh (FiinGroup).
- Already verified today: TinyFish read deposit rates for 10 banks (36 rows confirmed) in ..\D-UNLOCK\samples\deposit_rates_today.csv;
  FiinQuant get_ratios works for banks 2021+ with NPL, LDR, NIM (..\R-SUPPLY\SUPPLY.md §1).
## Do (write POLICY.md)
1. List at least 12 live banking/finance policy issues in Vietnam with dated primary sources (SBV circulars/decisions, laws, MOF):
   e.g. credit-growth quotas and their removal, deposit-rate caps and SBV guidance, deposit insurance (limit, premium, law changes,
   DIV statistics), lending-rate transparency and mortgage resets after teaser periods, bad-debt law and weak-bank mandatory
   transfers, Basel II/III and capital, consumer-finance caps, digital banking/biometrics and fraud, cashless payments, green credit,
   banks trading gold, crypto/fintech sandbox. For each: who is affected (with an official count if found), the household decision,
   the policy question, and the public data that could answer it (URL).
2. Crowding: what Vietnamese tools already serve depositors and borrowers (rate comparison, mortgage calculators, bank safety
   rankings) and what brokers/FiinGroup/press already publish on bank health. What will other hackathon teams most likely build
   in banking?
3. Rank the top 5 banking questions on: observed-data strength, household usefulness, policy relevance, uniqueness, judge/mentor
   fit (name the person), demo wow, buildable by 21/11 13:00. Give the one-sentence research question for each.
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. A negative claim
  ("not available") needs the exact URL/endpoint and response you got.
- Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets. FiinQuant raw data stays in this folder
  (<= 20 raw rows per sample file; computed aggregates are fine). TinyFish agent runs allowed up to USD 4 (log run id, steps, cost).
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.
- Timebox: 35 minutes. Write the named findings file and REPORT.md (max 15 lines) in THIS folder.