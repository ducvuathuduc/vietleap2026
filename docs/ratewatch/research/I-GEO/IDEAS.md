# I-GEO — Data-first concept round (fine-geography open data × money decisions)

All real calls made 20/11/2026, 12:00–12:35 Asia/Saigon, from this folder. Raw evidence in `http\`, small samples in
`samples\` (100 KB total). [verified] = fetched this session and the number is read/computed from the fetched rows.
[inferred] = interpretation or mapping step. No repo files touched. TinyFish agent runs: 0 (USD 0.00); TinyFetch free calls: 2.

---

## Concept 1 — "Hoàn vốn điện mặt trời theo địa chỉ và bậc điện" (rooftop PV payback by address × tariff tier)

- **User & decision.** A household (or shop owner) deciding whether to install a 3–5 kWp grid-tied rooftop PV system,
  and how many years it takes to pay back **at their address and their consumption tier**.
- **Policy question.** The 1/11/2026 reform (Quyết định 2892/QĐ-BCT: average retail price −2 %, household ladder cut
  from 6 to 5 tiers) changed the value of a self-consumed kWh overnight — does the new tariff still make rooftop
  self-consumption pay back, and how unevenly across addresses and tiers?
- **Research question (one sentence).** How many years does 1 kWp of self-consumed rooftop PV take to pay back at each
  province's satellite-derived yield and each tier of the 1/11/2026 ladder, and how large is the address × tier spread?
- **Datasets & join keys.** Global Solar Atlas API (`api.globalsolaratlas.info/data/lta?loc=lat,lon` → `PVOUT_csi`
  kWh/kWp, updated 2026-04-01) keyed by province centroid from HDX COD-AB (`adm1_pcode`, verified in R-SUPPLY §3 today);
  EVN household ladder from QĐ 2892/QĐ-BCT (tier → đ/kWh); system cost band from vendor quotes (đ/kWp); optional WorldPop
  households per province.

### Proof with real calls [verified]
| Row (fetched) | Value | Source + access time |
|---|---|---|
| PVOUT Hà Nội (21.028, 105.854) | **1.089,96** kWh/kWp/yr | `http\gsa_hanoi.json`, ~12:01 |
| PVOUT Đà Nẵng (16.054, 108.202) | **1.400,76** | `http\gsa_danang.json`, ~12:01 |
| PVOUT TP.HCM (10.75, 106.67) | **1.459,34** (matches R-SUPPLY §3.6 exactly) | `http\gsa_hcmc.json`, ~12:01 |
| Ladder 1/11/2026 (QĐ 2892/QĐ-BCT, pre-VAT) | bậc 1 **1.901** · 2 **2.289** · 3 **2.894** · 4 **3.456** · 5 **3.844** đ/kWh; bình quân **2.159,9037** (−2 % từ 2.204,0655) | fetched page `http\vietnamsolar_tariff.html` ~12:03, cross-checked: its 300 kWh = 708.400 đ example matches baomoi.vn independently |
| System cost, grid-tied residential | **10–18 triệu đ/kWp** [verified as vendor quotes: datuniversal.com 10–15tr; vtsolar.vn 12–18tr] | search results ~12:25 |

**Computation shown** (avoided cost = PVOUT × price; payback = cost ÷ avoided cost), full table in the run log:
- TP.HCM @ bậc 5: 1.459,34 × 3.844 = **5,61 m đ/kWp/yr → payback 1,8–3,2 y** (10–18tr cost).
- TP.HCM @ bình quân: 1.459,34 × 2.159,9 = 3,15 m → 3,2–5,7 y.
- Hà Nội @ bậc 1: 1.089,96 × 1.901 = **2,07 m đ/kWp/yr → payback 4,8–8,7 y**.
- Spread: the same roof and money pays back **~2,7× faster** for a tier-5 household in HCMC than a tier-1 household in
  Hanoi (yield gap HCMC/HN = 1,339; tier5/tier1 price ratio = 2,022). Sample: `samples\gsa_pvout_3cities.csv`,
  `samples\evn_tariff_5tier_from_20261101.csv`.

### Crowding check [verified — searched 12:15–12:30]
- **dienhathe.com** "Công cụ tính toán năng lượng mặt trời… thời gian hoàn vốn, tỷ lệ tự dùng" —
  https://www.dienhathe.com/cong-cu-tinh-toan-nang-luong-mat-troi-tai-viet-nam/
- **posotec.vn** solar sizing tool, FAQ states payback "3–5 năm" — https://posotec.vn/
- **vietnamsolar.vn** tariff + bill calculator and vendor payback claim "hoàn vốn khoảng 3,3 năm" —
  https://vietnamsolar.vn/cong-cu-tinh-gia-dien-sinh-hoat/ , https://vietnamsolar.vn/lap-dat-dien-mat-troi/
- Global Solar Atlas site itself shows PVOUT per point; PVWatts (NREL) is the generic global calculator.
**Verdict: crowded.** Vendor lead-gen calculators already do payback; our only edge (official-decision tier math +
reform comparison) is thin. Score uniqueness 2/5 — keep only as a fallback.

---

## Concept 2 — "Cửa hàng của bạn ngập mấy lần trong 30 năm?" (observed flood history × business siting & insurance)

- **User & decision.** A household business / small firm choosing **where to rent a shop or warehouse**, and whether to
  pay for flood cover; an insurer or provincial planner deciding where household-business flood insurance should be
  sold first.
- **Policy question.** Which provinces concentrate household businesses where 30 years of observed daily river
  discharge shows the most extreme flood days — and should flood insurance for household businesses (penetration ≈ 0
  for this segment) be promoted or subsidized there?
- **Research question (one sentence).** At which province river-cells does the 1997–2026 daily discharge record show
  the most days above the long-run 95th percentile, and how many individual non-farm establishments sit in those provinces?
- **Datasets & join keys.** Open-Meteo flood API (`flood-api.open-meteo.com/v1/flood?latitude=…&longitude=…&daily=river_discharge`,
  GloFAS reanalysis, CC-BY 4.0) at a river cell per province; **HDX COD-AB** `adm1_pcode` (34 units, valid_on 2025-09-25,
  verified R-SUPPLY §3) as the province spine → centroid/river-cell lat-lon; **NSO PXWeb V05.54** (province × year,
  individual non-farm establishments 2015–2024, 63-province map → repo 63→34 concordance) + NSO census 2026 Biểu 10/12
  (34-province map); optional WorldPop 100 m (residents per cell), FiinQuant `taxCode` 2-digit prefix (listed firms per province).

### Proof with real calls [verified]
| Row (fetched) | Value | Source + access time |
|---|---|---|
| Huế cell (16.4637, 107.5909), 1997-01-01→2026-11-19 | 10.915 valid days; median 0,7 · p95 **6,8** · p99 17,1 · max **48,4 m³/s on 2009-09-29 (Ketsana)** | `http\flood_hue_1984_2026.json`, ~12:03 |
| Huế, Oct–Nov 2020 | **26 days above the 30-year p95**, peak 28,8 = **41× median** (the historic central-Vietnam floods) | computed from same file |
| Hà Nội cell (21.028, 105.854) | max **71,6 m³/s on 2024-09-08 (Yagi)**; 2024 = worst year (40 days > p95) | `http\flood_hanoi_1984_2026.json`, ~12:03 |
| NSO PXWeb V05.54 POST (json-stat v1) | 700 cells; **Thừa Thiên - Huế 2024 = 79.105 cơ sở cá thể**; Cả nước 5.166.574 | `http\pxweb_v0554_cells_v1_raw.json`, ~12:07 |
| Cross-check vs C-NOTCH2 §2 | Hà Nội 356.918 · TP.HCM 430.571 (2024) — **exact match** | same file |

The series reproduces known events (Ketsana 29/9/2009; Yagi 8/9/2024; Oct–Nov 2020) — the insight is testable, not
decorative. First real number: *"Tại ô sông Huế, tháng 10–11/2020 có 26 ngày vượt p95 của 30 năm quan sát; tỉnh có
79.105 cơ sở cá thể phi nông nghiệp (2024)."* Samples: `samples\flood_daily_hue_2019_2026.csv` (2.880 rows),
`samples\flood_stats_summary.json`, `samples\pxweb_v0554_establishments_sample.csv`.
Note: 1984–1996 is null at these cells (GloFAS era), so the honest baseline is **1997–2026, 30 years**.

### Crowding check [verified — searched 12:30]
- **ThinkHazard!** (World Bank/GFDRR) — province/district hazard *classes* only, no time series, no economic join —
  https://thinkhazard.org/en/report/264-vietnam/FL
- **thoatnuochanoi.vn/ungngap/** (Hanoi drainage dept ponding points), **UDI Maps** (HN/HCMC urban ponding),
  **hviiet.github.io/flood-map** (community flood map + routing) — urban, real-time incident maps, no 30-year history,
  no business counts — https://thoatnuochanoi.vn/ungngap/ , https://hviiet.github.io/flood-map/
- **Academic**: microbusiness flood-loss / business-interruption models for HCMC and Can Tho (Bayesian networks,
  ResearchGate) — proves the question matters; no product serves it.
**Verdict: not done** as a siting/insurance decision tool on observed discharge history; adjacent tools are either
class maps (ThinkHazard) or urban ponding points. Keep.

---

## Scoring (1–5)

| Criterion | C1 Solar payback | C2 Flood siting/insurance |
|---|---|---|
| Observed-data strength | 4 (satellite LTA + official decision; cost = vendor quotes) | 5 (10.915 days/point, validates against named events) |
| Insight (non-obvious, decision-changing) | 3 (spread is real but intuitive) | 4 (nobody shows a shop owner their cell's 30-year exceedance history next to establishment counts) |
| Uniqueness vs other teams & tools | 2 (vendor calculators everywhere) | 4 (ThinkHazard/ponding maps are coarse or real-time; academic only) |
| Judge/mentor fit | 4 — Nguyễn Tiến Việt (LSE, clean energy/twin transition); Đặng Hoàng Nhất Tam (UEH, energy econ) | 5 — Sacha Dray (World Bank); Nguyễn Tiến Việt's own workshop case study is *flood risk + property data*; Nadia Doytch (energy & environment) |
| Demo wow | 3 (map + slider; calculators are common) | 4 (type an address → 30-year discharge chart with Ketsana/Yagi/2020 highlighted + "79.105 cơ sở" exposure count) |
| Buildable by 21/11 13:00 | 5 (two GETs, client-side) | 4 (needs scripted per-province river-cell selection, 2–3 h) |
| **Total** | **21/30** | **26/30** |

**Best: Concept 2.** **Main risk:** GloFAS cell discharge (~5–11 km grid, modeled reanalysis) is not water depth at
the shop's door — the product must sell *relative exposure + verified history* (never "your street floods X cm"),
and the 1984–1996 nulls must be disclosed. Mitigation already demonstrated: event validation (Ketsana, Yagi, 2020)
and honest labelling; secondary risk: centroid-off-river cells need manual per-province picks.

---

## Rules compliance
- robots.txt read before each host (~12:00): `evn.com.vn` `Allow: /`; `api.globalsolaratlas.info` serves no robots.txt
  (JSON 404); `pxweb.nso.gov.vn` no Disallow (verified in D-UNLOCK §3.1); **`flood-api.open-meteo.com` declares
  `Disallow: /`** — a crawler directive on the provider's own documented, CC-BY 4.0 data API that the brief lists as
  pre-unlocked anchor data; I made 2 single-point API calls (no crawling) and flag the quirk here.
- Delays ≥ 2,2 s between calls to the same host; no captcha/login bypass; no secrets printed (TinyFish key read from
  env, used in headers only). TinyFish agent runs: **0 (USD 0.00)**; TinyFetch free: 2 calls (thuvienphapluat
  `bot_blocked`; luatvietnam OK 5,8 KB, `http\tinyfetch_luatvietnam_2892.json`).
- No repo edits, no git writes, no installs, no processes touched.
