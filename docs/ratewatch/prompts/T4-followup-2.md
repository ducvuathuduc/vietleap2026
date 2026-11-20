# T4 follow-up 2 from Kiro review of home-desktop.png and map-mobile.png (fix all; TDD for view-model changes)
Layout "/" at >= 1024 px: the chart must be visible on the first screen (1280x800) together with the headline and the key numbers.
1. Row 1: headline (finding, max 2 lines, larger and semibold) + one meta line under it: "Biểu OCB online · ngày 06/11/2026 · đọc lúc
   14:36 20/11/2026 · Đã kiểm 2 nguồn · nguồn ↗" (values from the snapshot, link to sheet_url).
2. Row 2: four key-number cards, numbers large (about 40 px, tabular figures) with the count-up:
   (a) "Lãi của bạn" 6,00%/năm, sub "OCB online · 6 tháng · = 15.000.000 đ trên 500.000.000 đ" (VND from calc at the horizon);
   (b) "Trần kỳ dưới 6 tháng" 4,75%/năm, sub "QĐ 2411/QĐ-NHNN · kỳ 6 tháng của bạn cao hơn 1,25 điểm %";
   (c) "Hòa vốn khi tái tục" 6,41%/năm, sub "phép tính, không phải dự báo";
   (d) "Được bảo hiểm" e.g. "350.000.000 đ / 500.000.000 đ" with a thin bar, sub "TT 05/2026 · phần vượt: 150.000.000 đ".
   The current card "Trần và phương án đã kiểm khác 4,75% · HDBank 5,00%" is ambiguous: remove it.
3. Row 3: two columns. Left (2/3): the main chart card. Right (1/3): "Kế hoạch của bạn" card holding the controls (amount, horizon,
   online, bank) and the top 3 plans (value at horizon in đ, insured share bar, rows used with grade badge). Move all controls out of
   the page top into this card. Persona buttons sit above the controls in that card.
4. Amount input: format while typing (VI 500.000.000 đ, EN 500,000,000 VND), quick chips +100 tr / +500 tr / +1 tỷ, validation text.
   Horizon: slider in months 1-36 with tick labels 1, 3, 6, 9, 12, 18, 24, 36; the date field becomes optional ("hoặc chọn ngày").
5. Bank select label: "OCB · Ngân hàng TMCP Phương Đông" (no "OCB (OCB)"). Compare chips: only banks that have rows for the
   chosen channel; others disabled with a tooltip "chưa đọc được biểu".
6. Main chart (Recharts, components/ui/chart.tsx): x = term months as categories, one line per bank, dots; a shaded band over 1-5
   months labelled "Vùng trần 4,75%"; a reference line at 4.75% labelled "Trần 4,75% · QĐ 2411"; a vertical marker at the chosen horizon;
   tooltip shows rate, grade badge, sheet date and source domain. Title is a finding computed from data, e.g. "OCB trả 6,00% từ kỳ
   6 tháng; kỳ 1–5 tháng bị giới hạn ở 4,75%". Remove the caption "1 đường, trần 4,75%/năm. Biểu OCB ... Nguồn: https://..." (it reads
   like debug text); sources go in the meta line and the footer.
7. Row 4: detail table bank x term as a compact heat table (cell shade by rate within theme tokens, no new colours), grade badge per
   cell, sticky first column, sort by the chosen term; contested cells show both values.
8. /ban-do: the headline must be a finding computed from data, not a count of empty fields and never the boundary attribution.
   Use real data now: read data/lake/ratewatch/gold/geo_provinces.json (written by M1: 2,477 OSM bank points, 34/34 provinces, 33 banks
   matched; deposits are null) into web/seed/ratewatch/snapshot.fixture.json "geo" (keep a "_fixture_note" naming that file).
   Example headline form: "<Tỉnh A> có <n> điểm giao dịch ngân hàng trên OpenStreetMap, <Tỉnh B> có <m>; ở <k> tỉnh không có chi nhánh
   của ngân hàng trả lãi online cao nhất". Choropleth with a 5-step legend (quantiles, labelled), per-100k toggle using population
   from engine/vlkit/ratewatch/geo/population_2024.csv (label its basis), province click -> side panel (banks present, counts, best
   verified counter and online 12-month rates among them). Footer lines: boundary attribution exactly as CONTRACT D, and
   "© OpenStreetMap contributors (ODbL)". On mobile the map is visible without scrolling past the controls.
9. Header: brand text "RateWatch" with the Vietnamese subtitle in smaller text; VI | EN as a segmented control.
Acceptance: npm run lint, npm test exit 0; dev server port 3107 screenshots at 1280x800 and 390x844 for / and /ban-do saved in THIS folder
(home-1280.png, home-390.png, map-1280.png, map-390.png); no console errors. Stop only your own server.