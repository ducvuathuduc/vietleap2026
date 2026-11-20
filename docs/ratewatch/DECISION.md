# Decision memo (draft for team approval) — 20/11/2026 11:35

## Evidence base (task folders next to this file)
R-AUDIT (codex), R-DEMAND (cursor), R-SUPPLY (pi), R-DOMAINS (vibe, ran without repo AGENTS.md), C-GOLD (codex), C-NOTCH +
C-NOTCH2 (cursor), C-FTSE (codex), D-UNLOCK (pi).

## Killed as lead product
- Gold premium: GemBack, MacroDashboard, Cá Buồm, ORA·tech, OpenBDS, Giá Vàng Nay, GiaVang.app already show premium/spread/
  break-even; a 2026 paper in Risks already studies the Decree 232 breakpoint (C-GOLD §4).
- FTSE upgrade flows: SSI, VNDIRECT, Vietcap, ACBS, SBBS, TCBS, FiinGroup and press already published it; every team has FiinQuant (C-FTSE §4).
- Public investment x merger / macro monitor: policy-only, looks like the dashboards other teams build (R-AUDIT §4: 59/100 today).
- US tariff rerouting: Census pull is the long pole, exporters only. EVN 2% cut: weak pain. PIT calculator: crowded (R-DEMAND §4-5).

## Recommended: "Ngưỡng 1 tỷ" (The 1-billion cliff)
Research question: does stacking VAT, the e-invoice duty and (conditionally) compulsory social insurance on one 1-billion-VND
threshold make household businesses worse off for growing, for which sectors, by how much, and which reform removes it?
Core insight (C-NOTCH, to re-verify in Phase 0): above 1 billion, VAT applies to TOTAL revenue (VAT law art. 12.2.c, Decree 68 art. 3)
while ratio-method PIT applies to the excess (PIT law art. 7.3.a). One đồng over the line costs a retailer 8 million and a service
household 40 million VND in 2026 (10 / 50 million from 2027). Dominated revenue range: retail ~10.2M, food/transport ~31.4M,
services ~53.8M above the line (zero-cost, tax-only).
Users: shop owners and online sellers (Decree 117 platform withholding, refund only if full-year revenue is non-taxable), accountants,
policymakers. Data: bitemporal legal-parameter registry with article citations; MOF bins 2025; NSO 2026 census by 34 provinces x
5 sectors (Biểu 10 p.74, Biểu 12 p.80); NSO PXWeb V05.53/54 2015-2024 + repo 63->34 concordance; eTax / cash-register e-invoice
adoption; budget figures 4,850 / 16,650 billion. Honest limits: no microdata, so no bunching estimate and no headcount inside the
notch; reform cost only as a bounded range; SI gate awaiting guidance; Decree 117 vs PIT excess-only conflict open.

## Open for the team
1. Approve the domain (AI rules: final decisions are the team's).
2. Team members, disciplines, team name.
3. AWS: run `aws login` (session expired); region (proposed ap-southeast-1), cost of ECS Express Mode (~USD 1-2/day) acceptable?
