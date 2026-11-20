# BA brief v1 — "Lãi Suất Hôm Nay" (working name) — 20/11/2026 12:40
Status: concept for owner approval; numbers marked (*) are being re-verified in V-CURVE / V-LAW / V-MACRO / V-TECH.

## Problem and evidence
- Household deposits 11,434,266 billion VND, +10.63% YTD (SBV stats, 8/2026, B-HOUSE). Largest household financial asset.
- Same product, different price: 12-month online rates 5.20% (ACB) to 7.00% (*), median 6.25% (B-RATES, 21 banks).
  Online vs counter gap up to 1.85 pp (BIDV 6/9 m) (*); Sacombank PDF 1.40 pp (I-SAVE).
- Regulation shapes the curve: 4.75% ceiling for 1 to <6 months (QĐ 2411/QĐ-NHNN, 20/11/2024) (*); deposit-insurance cap
  350 million per depositor per institution from 13/7/2026 (Thông tư 05/2026) (*) — SBV's own assessment: covers 93.68% of insured
  depositors but only 19.06% of insured value (B-POLICY).
- Honest pain test: comparing rates is already served (webgia, timo, simplize, taichinh.com). The unserved part is the DECISION:
  which term given a horizon (break-even rate), how to split across banks under the cap, what risk sits behind a higher rate,
  and what the rules cost savers. Pain per household is millions of VND per year, not life-changing; the pitch must not overclaim.

## Research question
"Where, for how long, and how much should a Vietnamese household deposit today, and how much do the 4.75% short-term ceiling and the
350-million insurance cap change that choice?"

## Users and jobs
- Judges acting as a saver (primary demo user), real households (secondary), SBV/DIV policy staff (policy page).
- J1 Plan: amount + horizon (+ current bank/channel) -> split, terms, VND interest, insured share, versus staying at the counter.
- J2 Break-even: "lock 12 months or 6 months twice": implied forward / break-even rate from each bank's curve.
- J3 Safety: insured vs uninsured amount per bank; bank risk profile (NPL, coverage, LDR, capital, P/B) from FiinQuant aggregates.
- J4 Policy: ceiling kink across banks; cap adequacy (insured value share); do higher rates come with higher risk (market discipline).

## Product form
Public HTTPS web app on AWS (responsive, installable PWA), no login, VI default + EN, one-click demo personas. AI planner panel
built into every page. Optional stretch: MCP endpoint exposing the same tools.

## Wow moments (pitch order)
1. Live national deposit yield curve: every bank, today, with the kink at 6 months from the ceiling, updated daily (rate-move ticker).
2. Ask the planner in Vietnamese: "1,2 tỷ, cần dùng sau 9 tháng, đang gửi BIDV tại quầy" -> plan with VND numbers, each linked to the
   bank page and read time; "Xem dấu vết" opens the Langfuse trace (tool calls, inputs, sources).
3. Break-even card: "6 months twice beats 12 months only if the 6-month rate in 6 months is >= X%".
4. Policy: insured vs uninsured value; what a different cap would cover; ceiling kink cost.

## Models and formulas (no black box)
- Break-even forward: (1 + r12) = (1 + r6/2) * (1 + f/2) under the bank's stated simple-interest convention -> f.
- Nelson-Siegel fit of the system curve (level, slope, curvature) per day; factors stored daily for trend.
- Split optimiser: maximise interest s.t. per-bank amount <= insured cap, term <= horizon, bank passes risk filter; greedy + ladder.
- Real return = nominal - CPI YoY (NSO); rate-pressure indicators (interbank, credit-deposit growth gap, LDR) if V-MACRO finds data.
- Market discipline: cross-bank regression of posted rate on risk indicators with size/state controls; small n stated.

## Data and pipeline
TinyFish/TinyFetch daily on ~30 bank pages (two readers, grades) -> S3 bronze -> DuckDB silver/gold star schema
(dim_bank, dim_term, dim_channel, dim_date, dim_source; fact_posted_rate bitemporal, fact_bank_quarter, fact_bank_market_day,
fact_macro_month) -> quality gates -> versioned snapshot JSON (schema + citation checks) -> app. FiinQuant raw stays private.

## Platform
Next.js 16 + shadcn (repo stack) in Docker -> ECR -> ECS Express Mode (ap-southeast-1); EventBridge Scheduler -> ECS task pipeline;
S3 snapshots; Secrets Manager; CloudWatch; AI SDK v7 + Bedrock (task role) with Groq fallback; Langfuse Cloud traces via OTel.

## Legal
Show citations for ceiling, insurance cap, data sources; "reference information, not investment advice" (wording per V-LAW);
no personal data needed for the planner; mask amounts in traces if required; FiinQuant aggregates only, attribution, confirm with FiinGroup.
