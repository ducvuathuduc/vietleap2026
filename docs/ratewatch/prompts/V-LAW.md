# V-LAW Primary-text legal check for the deposit decision product
Repo (read only): C:\Users\dieut\Desktop\Money\vietleap
## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (rubric, judges, owner rules). Area is fixed: banking/finance in Vietnam,
  household deposits. Prior findings (read only what you need): ..\B-RATES\RATES.md (21-bank panel, 268/289 rows from one aggregator),
  ..\B-POLICY\POLICY.md (deposit-insurance cap 350 million from Thông tư 05/2026 in force 13/7/2026; ceiling 4.75% for 1 to <6 months
  under QĐ 2411/QĐ-NHNN), ..\B-HOUSE\HOUSE.md (DIV page still shows 125 million; SBV stats pages; household deposits 11,434,266 tỷ 8/2026),
  ..\B-BANKDATA\BANKDATA.md (FiinQuant 28 banks, ratios 614/644 quarters).
- Working product idea (test it, do not defend it): a deposit decision tool for households that reads every bank's posted curve daily,
  shows where the 4.75% short-term ceiling bends the curve, derives the market-implied future rate from the curve (forward rates) to
  answer "lock 12 months now or 6 months twice", checks the insured cap per bank, and shows each bank's risk profile.
## Do (write LAW.md)
1. Deposit insurance: the limit in force today and its legal basis (Thông tư 05/2026 vs QĐ 32/2021/QĐ-TTg; Luật Bảo hiểm tiền gửi
   2024/2025 changes), effective date, what is covered (per depositor per institution; savings and current accounts; exclusions),
   premium rate and whether it is flat or risk-based. Primary text (vbpl.vn, congbao.chinhphu.vn, sbv.gov.vn, div.gov.vn) with articles.
2. Rate ceilings: the text in force today for VND deposits under 6 months (QĐ 2411/QĐ-NHNN of 2024 or later), and any 2025-2026 change.
3. Disclosure: what banks must publish about deposit rates (Law on Credit Institutions 2024, SBV circulars), online vs counter rules.
4. Our product's legal limits: is comparing banks and suggesting a term/split "financial advice" that needs a licence in Vietnam?
   Personal data rules for an AI chat (Decree 13/2023/NĐ-CP and the 2025 Personal Data Protection Law): what we may log, masking,
   consent wording. Sending prompts to a foreign LLM/observability provider (Langfuse Cloud): cross-border transfer obligations.
5. A short list of exact legal citations the product must show on screen.
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. Negative claims need the
  exact URL and response. Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets.
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.
- Timebox: 30 minutes. Write the named findings file and REPORT.md (max 15 lines) in THIS folder.