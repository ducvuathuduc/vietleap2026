# T4 follow-up 1 from Kiro (owner requirements, apply all; keep your current work)
1. Light mode only for the judge site, clean and plain, shadcn dashboard-01 look; no gradients, no emoji, no hype copy.
2. Remove slogan-style copy everywhere. Banned examples: "Từ số liệu đến tiền gửi", "từ insight đến decision", "Data to decision" taglines,
   "thông minh", "đột phá", "toàn diện", "giải pháp". Headings state a finding with a number, a period and a source, nothing else.
   Add these phrases to a small copy check test in web/src/lib/ratewatch/copy.test.ts that scans your page and component strings.
3. First 10 seconds: the three key numbers and the headline counters animate from 0 to their snapshot value (about 1.2 s, ease-out),
   once per load, respecting prefers-reduced-motion; the curve draws in. Nothing else moves.
4. VI default with a clear VI | EN toggle in the header; every label, tooltip and unit has both languages; numbers formatted per locale
   (1.234.567 đ / 4,75% in VI; 1,234,567 VND / 4.75% in EN).
5. Charts must be truly interactive (Recharts via components/ui/chart.tsx): hover tooltips with value, grade, sheet date and source;
   click a bank in the table to load its curve; compare up to 3 banks; a horizon slider that moves a marker on the curve and updates the
   plan card live.
6. A real Vietnam map on the saver screen or a /ban-do page, reusing web/public/geo/vn-34.geo.json and the existing SVG choropleth approach
   in web/src/components/judge/choropleth.tsx (copy into components/ratewatch, do not import from judge). Choropleth by province of the
   metric chosen in a toggle (bank branches total; branches of the selected bank; deposits where published); click a province -> side panel
   with the banks present there and their best verified counter and online rates, so a saver sees which nearby banks pay what. Show the
   boundary attribution line exactly as in CONTRACT.md section D. Build against fixture "geo" data that you mark "_fixture_note"; M1 provides
   the real data later.
7. Easy for anyone: plain Vietnamese labels, short helper text under each control, a "Cách đọc biểu đồ" collapsible under each chart,
   large tap targets, works on a phone.
Rerun your acceptance commands, update REPORT.md.