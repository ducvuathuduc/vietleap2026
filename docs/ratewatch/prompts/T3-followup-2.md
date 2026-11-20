# T3 follow-up 2 from Kiro (amount tiers, CONTRACT.md section E)
plan(), insured_split() and ceiling_stats() in analytics.py and calc.ts: a row is eligible for an amount only if
tier_min_vnd <= amount < tier_max_vnd (missing bounds = 0 / no upper bound). For a split, each allocation uses the tier of the amount
placed at that bank, not the total. Add fixture cases (OCB 3 tiers: 6.00 / 6.10 / 6.20 at 6 months; amount 50 tr, 300 tr, 800 tr; a
1.2 tỷ split where per-bank amounts fall in different tiers). Same cases in Python and TypeScript.