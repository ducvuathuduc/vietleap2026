# T3 REPORT — analytics engine (Python + TypeScript), follow-up 1

Status: DONE

## Acceptance commands (run fresh, this session)
- `$env:PYTHONPATH='engine'; .\.venv\Scripts\python.exe -m pytest -q tests/ratewatch/test_analytics.py` -> 8 passed, exit 0
- `cd web; node --test src/lib/ratewatch/calc.test.ts` -> 8 pass / 0 fail, exit 0
- `cd web; npx eslint src/lib/ratewatch` -> exit 0
- Regression: decide.test.ts + view.test.ts still 15 pass / 0 fail.

## Fixes (TDD: fixture + assertions first, both suites failed on the new fields, then implemented)
1. Ladder second leg: now renews at the same bank's posted row for term == horizon-6 (same channel); no such row -> no ladder. Field `second_leg_assumption: "same posted rate as today"` added. Horizon 9 fixture proves the 3-month row is used (leg2 = 1,287,500 at 5.0%).
2. Plans compare and report value at the horizon: single term<=H = P*(1+r*term/12)*(1+d*(H-term)/12), d = bank demand rate else 0; `idle_months` = H-term reported (split: null — per-allocation terms differ); interest_vnd is now interest over the horizon (includes idle demand earnings); ranking key is value_at_horizon. Early-withdrawal logic unchanged.
3. New fixture cases: ladder_horizon_9_uses_3m_row, horizon_5_with_3m_option_idle_2, ranking_flips_with_idle_months (OCB 3m @6.0 + 2 idle months @6.0 demand beats STB 5m @5.9 at horizon 5 — by term interest STB won; by horizon value OCB wins). Same cases pass in Python and TypeScript.

## Verification
- Cross-port bitwise identity re-checked: 72 computed doubles (interest_vnd, value_at_horizon, insured_share over all plan cases) are identical IEEE-754 bit patterns in Python and Node.
- One fixture arithmetic slip during TDD (STB 5m insured_share 0.854, not 1.0 — 400M exceeds one bank's insured room); fixed in the fixture, implementation was right.

## Notes for Kiro
- interest_vnd for singles now includes idle-month demand earnings — saver-live.tsx shows this number as "lãi"; T4 may want to surface idle_months and second_leg_assumption.
- Split plan's idle_months is null (per-allocation terms differ); per-allocation detail is in rows[].term_months.
