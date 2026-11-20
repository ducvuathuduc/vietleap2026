# C-FTSE Red-team candidate C with real FiinQuant calls: "the FTSE upgrade arrived as retail leverage"
Repo (read/run only): C:\Users\dieut\Desktop\Money\vietleap
Research and critique, not product code. Do NOT edit the repo.

## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (rubric, judges, owner rules, FiinQuant notes).
- Read ..\R-DOMAINS\DOMAINS.md (search "FTSE"; survivor S1 and red-team A) and ..\R-SUPPLY\SUPPLY.md section 1 (FiinQuant map).
  R-DOMAINS ran without the repo AGENTS.md and marks many facts [inferred]: verify every date and number you rely on.
- Claimed facts to verify first: FTSE Russell announced Vietnam's upgrade to Secondary Emerging in Oct 2025, effective 21/9/2026;
  record margin lending (claimed 457.5 trillion VND); repo already holds margin data (check docs/DATA_SOURCES.md, tools/press/).
- Working idea (attack it): an investor enters a ticker or VN30 and sees who bought and sold around the announcement and effective
  dates (foreign vs domestic, matched vs put-through), funded by what (margin), at what valuation; the policy side says which
  remaining MSCI criteria matter.

## Answer these (write CRIT-FTSE.md in this folder)
1. Verify the event dates and the margin numbers from primary sources (FTSE Russell notices, SSC/UBCKNN, broker financial statements),
   URL + access date.
2. Real FiinQuant calls (login from the repo .env.local without printing secrets; FiinQuantX in the repo .venv): daily foreign
   buy/sell/net for VN30 members and VNINDEX across Sep 2025 - Nov 2026, how far back daily foreign flows go, VN30 vs non-VN30
   split feasibility, index PE/PB around both dates. Save at most 20 rows per call under samples\. Report what the data actually
   shows around the two dates (numbers, not adjectives).
3. Method critique: is a two-event study with VN30 vs non-VN30 difference-in-differences valid here? Confounders (Fed, FX, margin
   rules, index rebalancing dates), pre-trends, how to state uncertainty.
4. Uniqueness: who already published this analysis (brokers SSI/VNDirect/VCSC research, FiinGroup, press)? Name + URL.
   With every team holding the same FiinQuant account, what would still be new in ours?
5. Verdict GO / GO-WITH-CHANGES / KILL, the research question, the headline the data supports today, and what we show if null.

## Rules
- Cite URL + access date; mark [verified]/[inferred]. Never invent numbers. FiinQuant raw data stays in this folder (<= 20 rows/sample).
- No repo edits, no git writes, do not kill processes you did not start, no npm build, never print secrets.
- Timebox: 30 minutes. Write CRIT-FTSE.md and REPORT.md (max 20 lines, verdict first) in THIS folder.
