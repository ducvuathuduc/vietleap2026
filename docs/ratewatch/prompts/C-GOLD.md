# C-GOLD Red-team and deepen candidate A: "the hidden gold premium Vietnamese households pay"
Repo (read only): C:\Users\dieut\Desktop\Money\vietleap
Research and critique, not coding. Do NOT edit the repo.

## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md (challenge, rubric, judges, owner rules).
- Read ..\R-SUPPLY\SUPPLY.md section 5.1 and ..\R-DEMAND\DEMAND.md section C1 (gold rules: Decree 232/2025 ended the state
  bar-minting monopoly from 10/10/2025; Decree 390/2026 non-cash for >= 5 million VND/day from 16/10/2026).
- Live today: BTMC JSON gives SJC sell 13,420,000 VND/chỉ-equivalent board (check the unit: lượng vs chỉ), world GC=F 3,528.4 USD/oz,
  USDVND 25,705 -> premium about +22.7%. Another worker (pi) owns scraping the BTMC daily history and bank deposit rates; you do not.
- Working idea (to be attacked, not defended): a product a household opens before buying gold. It shows today's premium over world
  parity, the instant loss from the bid-ask spread, where today's premium sits in its own history, and how much of a past SJC gain
  came from world gold vs the dong vs the premium. The policy side estimates what the premium costs households per year and tests
  whether the 2025-2026 rules moved it.

## Answer these (write CRIT-GOLD.md in this folder)
1. Data for the history, verified with real calls today: world gold daily (LBMA/Yahoo/other, how many years, licence), USDVND daily
   (SBV central rate and/or Vietcombank, how many years), Vietnam gold demand volumes (World Gold Council Gold Demand Trends:
   bars/coins and jewellery tonnes by quarter for Vietnam; access route and terms), SBV gold-bar auction dates and volumes 2024,
   import/licensing events. For each: URL, HTTP status, sample row, history depth.
2. Method: the exact decomposition of an SJC return into world-gold, FX and premium parts (formula, units: 1 lượng = 37.5 g); an
   event-study or before/after design for Decree 232 (10/10/2025), the 2024 SBV auctions, and Decree 390 (16/10/2026) with world
   price as a control; how to estimate the annual household premium cost (premium x demand volume) with an honest uncertainty band.
3. Strongest objections a World Bank economist (Sacha Dray), a Shinhan securities-services director and a behavioural economist
   (Nguyen Tri Dung) would raise: e.g. premium includes VAT/import costs/legit margins, SJC vs ring gold, demand volume units,
   confounders, "people already know gold is expensive". Fatal or answerable, and how.
4. Existing tools and press that already show the premium (name + URL). What exactly would be new in ours?
5. Verdict: GO / GO-WITH-CHANGES / KILL, with the one research question, the headline we expect, and what we show if the
   hypothesis fails.

## Rules
- Cite URL + access date for every fact; mark [verified]/[inferred]. Never invent numbers.
- Respect robots.txt, add delays, no captcha/login bypass, never print secrets. TinyFetch allowed (see CONTEST.md).
- No repo edits, no git writes, do not kill processes you did not start, no npm build.
- Timebox: 40 minutes. Write CRIT-GOLD.md and REPORT.md (max 20 lines, verdict first) in THIS folder.
