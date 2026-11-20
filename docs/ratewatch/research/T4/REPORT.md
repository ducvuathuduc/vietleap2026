status: DONE

Acceptance
- cd web; npm run lint → exit 0
- cd web; npm test → exit 0 (247 pass). Did not run npm run build.
- Dev server npm run dev -- -p 3107, PID 20680, stopped with taskkill /PID 20680 /T /F.
- Screenshots in this folder: home-1280.png, home-390.png, map-1280.png, map-390.png. Console errors: none on those four loads.
- At 1280x800 the chart top is 352px, the headline top is 79px, and 6,00%/năm top is 195px (viewport 800). Mobile scrollWidth equals innerWidth on / and /ban-do. Map svg is above the controls at 390x844.

Tests that failed first
- decide.test.ts: model.figures missing. view.test.ts: bankMenuLabel missing, then formatVnd missing in screenCopy. Both pass after the view-model.
- tools.test.ts expected empty Cần Thơ branches; updated to the gold count (VN92 143, STB 11, deposits null).

What changed
- Four KPI cards, chart-on-first-screen layout, plan card with controls, category chart with the 1–5 band, heat table, RateWatch header, gold geo in the fixture, map headline/quantiles/per-100k/footer.

Not done / risk
- No commit. calc.ts, next.config, package.json, and theme files were not edited. Insured card wraps at 1280. Map shot is after an An Giang click.
