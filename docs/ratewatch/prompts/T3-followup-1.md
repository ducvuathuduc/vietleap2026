# T3 follow-up 1 from Kiro review (fix in both analytics.py and calc.ts, same fixture cases; TDD)
1. analytics.py plan(), ladder_6_renewal: the second leg uses the 6-month rate for (horizon - 6) months. Wrong when horizon != 12
   (e.g. horizon 9 -> the second leg is a 3-month deposit, capped at 4.75%). Fix: the second leg uses the same bank's posted row for
   term == horizon - 6 (same channel); if none exists, do not emit the ladder. Label the plan field "second_leg_assumption":
   "same posted rate as today" so the UI can say it is a calculation, not a forecast.
2. analytics.py plan() split and single plans compare options of different terms by growth over the term, not over the horizon.
   Fix: compare and report value at the horizon: for term <= horizon, P*(1 + r*term/12)*(1 + d*(H-term)/12) with d = the bank's demand
   rate if given else 0, and report "idle_months" = H - term. Rank plans by value at the horizon. Keep early-withdrawal logic.
3. Add fixture cases for: horizon 9 ladder (uses the 3-month row), horizon 5 with a 3-month option (idle 2 months), and a case where the
   ranking changes because of idle months. Same cases must pass in Python and TypeScript.
Rerun: pytest tests/ratewatch/test_analytics.py, node --test src/lib/ratewatch/calc.test.ts, npx eslint src/lib/ratewatch. Update REPORT.md.
