# I-PROV Data-first concept round: a product that stands out on real observed data
Repo (read/run only): C:\Users\dieut\Desktop\Money\vietleap
Research with real calls, not product code. Do NOT edit the repo.

YOUR ANCHOR: NSO PXWeb province tables 1995-2025 and the 2026 census by 34 provinces (labour, wages/income, prices/CPI, enterprises, household establishments, investment), with the 63->34 concordance. Think of decisions workers, families or local governments make (where to work or live, wages vs cost of living, regional minimum wage zones, local business conditions).

## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (challenge, rubric, judges, mentors, owner rules) and
  C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\DECISION.md (what was already killed and why: gold-premium trackers, FTSE flows,
  macro monitor, tariff, EVN cut, PIT calculator; the 1-billion household-tax cliff is on hold because it rests on law parameters and
  four published bins, with no observed household-level data).
- The owner's bar: the product must stand out on REAL OBSERVED DATA and the insight it produces, not on law parameters or a
  calculator. Ordinary people must be able to use it for a better financial/economic decision, and it must answer a policy question.
- Verified data already unlocked today (reuse, do not re-discover): BTMC gold daily SJC bar + ring 2017-05-02 -> today
  (..\D-UNLOCK\UNLOCK.md); FiinQuant daily prices/foreign flows back to 2011, PE/PB, ratios 2021+, taxCode -> province
  (..\R-SUPPLY\SUPPLY.md §1, ..\C-FTSE\CRIT-FTSE.md §2); Vietcombank FX XML back to 2020; deposit rates for 10 banks today via
  TinyFish (36 rows confirmed); NSO PXWeb: 44 province tables 1995-2025, GET metadata + POST cells work for V05.53/V05.54
  (..\C-NOTCH2\NOTCH2.md); NSO 2026 census by 34 provinces x 5 sectors; Open-Meteo flood/air, NASA POWER, Global Solar Atlas,
  WorldPop, Climate TRACE, HDX 34-province codes (..\R-SUPPLY\SUPPLY.md §3); repo has the 63->34 province concordance.

## Do (write IDEAS.md in this folder)
1. Propose 2 product concepts anchored on the data named in YOUR ANCHOR below (you may join other sources). For each:
   the user and the decision; the policy question; the research question in one sentence; the exact datasets and join keys.
2. Prove the data with real calls today: pull real rows (enough to compute one first real number that tests the insight), save
   small samples under samples\ (<1 MB; FiinQuant <= 20 raw rows per call, aggregates are fine). Show the computation.
3. Crowding check: search for existing Vietnamese tools, broker/press reports, and academic papers doing the same thing (name + URL).
   If it is already done, say so and drop or change the concept.
4. Score each concept 1-5: observed-data strength, insight (non-obvious, decision-changing), uniqueness vs other teams and tools,
   judge/mentor fit (name the person), demo wow, buildable by 21/11 13:00. Pick your best one and give its main risk.

## Rules
- Real calls only; cite URL + access time; mark [verified]/[inferred]. Never invent numbers.
- Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets. FiinQuant raw stays in this folder.
- TinyFish agent runs allowed up to USD 3 for this task (log run ids and cost). TinyFetch is free.
- No repo edits, no git writes, do not kill processes you did not start, no npm build. Do not install into the repo .venv.
- Timebox: 30 minutes. Write IDEAS.md and REPORT.md (max 15 lines: best concept, first real number, crowding verdict) in THIS folder.