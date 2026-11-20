# C-NOTCH Red-team and deepen candidate B: "the 1 billion VND cliff for household businesses"
Repo (read only): C:\Users\dieut\Desktop\Money\vietleap
Research and critique, not coding. Do NOT edit the repo.

## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (challenge, rubric, judges, owner rules).
- Read ..\R-DEMAND\DEMAND.md sections A1-A3 and B1 (your own earlier work): Decree 141/2026 moved the VAT/PIT/e-invoice threshold
  to 1 billion VND/year from 01/01/2026; compulsory social insurance for owners above 1 billion; MOF revenue bands.
- Working idea (to be attacked, not defended): one screen where a shop owner enters revenue and sector and sees every legal duty that
  switches on at 1 billion, plus the national picture. The policy side asks whether stacking duties on one threshold creates a
  "notch" (a revenue range where earning more leaves the owner with less after tax, insurance and compliance), which public-finance
  theory predicts causes bunching below the threshold.

## Answer these (write CRIT-NOTCH.md in this folder)
1. Read the primary legal texts (Law 109/2025/QH15 on PIT, the VAT law as amended, Decree 141/2026, Decree 68/2026, Decree 254/2026,
   the social-insurance rule for household owners) and state exactly, with article numbers: is PIT/VAT for a household above the
   threshold charged on TOTAL revenue or only on revenue ABOVE the threshold? Rates by sector group. Which option (revenue-ratio vs
   profit x 15/17/20%) applies in which band. When SI becomes compulsory and its minimum. This decides whether a true notch exists.
2. Compute, from those official parameters only, the net income just below and just above 1 billion for 3-4 sector groups
   (retail goods, food service, services, transport), and the size of any dominated revenue range. Show the formula.
3. Data beyond parameters: any public distribution of household-business revenue (tax authority bands, NSO economic census 2026
   preliminary tables, NSO PXWeb household-business tables by province/sector, VHLSS), with URL, HTTP status and sample row.
   Can we show bunching, or only the theoretical notch? Say plainly.
4. Strongest objections from Sacha Dray (World Bank, tax compliance), Dr. Doan Vu Nguyen (public finance) and a shop owner:
   "it is just a calculator", "no microdata", "MISA already does this", "the law already uses an excess-only base". Fatal or
   answerable, and how.
5. Verdict: GO / GO-WITH-CHANGES / KILL, with the one research question, the headline we expect, and what we show if no notch exists.

## Rules
- Cite URL + access date for every fact; mark [verified]/[inferred]. Never invent numbers or rates.
- Respect robots.txt, add delays, no captcha/login bypass, never print secrets. TinyFetch allowed (see CONTEST.md).
- No repo edits, no git writes, do not kill processes you did not start, no npm build.
- Timebox: 40 minutes. Write CRIT-NOTCH.md and REPORT.md (max 20 lines, verdict first) in THIS folder.
