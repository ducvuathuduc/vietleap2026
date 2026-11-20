# SUPPLY — what real data we could actually use (checked with live calls, 20/11/2026 ~10:35–11:15 Asia/Saigon)

Scope: supply side only — what exists, is reachable today, at what granularity/history, and what decision it enables.
Every row below was produced by a real call in this session; samples are in `samples\` (FiinQuant ≤20 rows).
Rows marked **[untested]** were not called. No repo files were modified.

Two parallel research workers were used: one for Vietnamese official/market sources (`partial_vn.md`), one for
international APIs (`partial_intl.md`). Their tables are folded in below; my own FiinQuant work is section 1.

---

## 1. FiinQuant (FiinQuantX 0.1.73) capability map — the real ceiling of the paid feed

Login: `FiinSession(FIINQUANT_USERNAME, FIINQUANT_PASSWORD).login()` — **OK in 0.4 s**, credentials read from the repo
`.env.local` (`dotenv_values`), never printed. Token is a JWT for package **FiinQuant.Premium**, validity 16/11/2026 →
30/11/2026, `time_range_limit=0` in the token but the API endpoint itself enforces limits (see "hard limits").

### 1.1 Every public entry point on the session object

| # | Call | Signature (0.1.73) | Live result today | Verdict |
|---|------|--------------------|-------------------|---------|
| 1 | `s.TickerList()` | `(ticker=None, tickers=None)` | `[]` for `"FPT"` and `["FPT","VCB","HPG"]` | **broken** — empty |
| 2 | `s.BasicInfor(t).get()` | `(tickers)` → DataFrame | 1×11 for FPT in 1.2 s; 4×11 for 4 tickers | **works** |
| 3 | `s.Fetch_Trading_Data(...)` | `(realtime, tickers, fields, adjusted, period, by∈{1m,5m,15m,30m,1h,2h,4h,1d}, from_date, to_date, callback, wait_for_full_timeFrame, lasted)` `.get_data()` | 1d: 248 rows / 1 y; 1m: 226 bars for 17/11/2026 (09:15→14:45) | **works** (see limits) |
| 4 | `s.GetDataPoint(...)` | `(ticker, field, by, candle_index, adjusted)` → float | `FPT close 1d idx1` = 45,700.0 in 0.9 s | **works** |
| 5 | `s.PriceStatistics().get_overview` | `(tickers, time_filter, from_date, to_date)` | 9×8 (volume, value, matched vs deal, %Δ, marketCap) | **works** |
| 6 | `s.PriceStatistics().get_foreign` | `(tickers, time_filter, from, to)` | Daily 9×21, Monthly 23×22 (buy/sell/net, matched vs put-through, room) | **works** |
| 7 | `s.PriceStatistics().get_freefloat` | `(tickers, from, to)` | 0×0 for 1 d and 1 month windows | **broken** |
| 8 | `s.PriceStatistics().get_ceilingfloor` | `(tickers, from, to)` | 0×0 | **broken** |
| 9 | `s.PriceStatistics().get_value_by_investor` | `(tickers, from, to)` | `KeyError: 'ticker'` | **broken** |
| 10 | `s.MarketBreadth().get(t)` | `(tickers=None)` | `VNINDEX` → 1 row (60 up / 229 down / 46 flat / 7 floor / 1 ceiling); `HOSE` → 0 rows | **works, today only** |
| 11 | `s.MarketDepth().get_index_valuation` | `(tickers, from_date, to_date)` | 261 daily rows PE/PB for VNINDEX, 2025-11-03→2026-11-19 | **works, best-in-class** |
| 12 | `s.MarketDepth().get_stock_valuation` | `(tickers, from, to)` | 14 rows PE/PB for FPT | **works** |
| 13 | `s.MarketDepth().get_sector_valuation` | `(tickers, level, from, to)` | `["BANKS"], level=2` → 36 rows; a stock ticker → `KeyError 'FPT_L3'` | **works with sector names only** |
| 14 | `s.MoneyFlow().get_contribution` | `(ticker, contribution_day∈{1Day,5Day,10Day,20Day}, type∈{topGainers,topLosers}, top)` | 5 rows 1Day, 10 rows 5Day (MCH #1, contribution 1.99 pts = 0.115 % of index) | **works** |
| 15 | `s.RRG(tickers, benchmark, ...)` | `(tickers, benchmark, by, from_date, to_date, period)` → `.get()/.filter()/.plot()` | 114 rows for FPT+VCB vs VNINDEX with `rs`,`rm`,`phase` | **works, needs explicit dates** |
| 16 | `s.Rebalance().get(Budget, Ticker)` | `(Budget:int, Ticker:str)` | `VN30`, 1 bn VND → 30×11 with FreeFloat, Shares to Buy, Stock Value to Buy; single stock → "FPT is not available" | **works for index baskets only** |
| 17 | `s.StockScreening().get_indicator_configs` | `(names)` | `[]` for `"rsi"`, `["close","rsi"]` | **broken/undocumented** |
| 18 | `s.StockScreening().get(...)` | `(filter, exchanges, screenerDate, sectors)` | `KeyError: 'indicatorName'` then `'NoneType' has no attribute 'get'` | **unusable** |
| 19 | `s.FundamentalAnalysis().get_ratios(...)` | `(tickers, years, quarters, type, fields)` | FPT 2024: 40+ ratios; VCB 2024: NPL 0.96 %, LDR 80.8 %, NIM 2.86 %, P/B 2.01, P/E 11.65; quarterly 2025 Q1–Q3 | **works, 2021+ only** |
| 20 | `s.FiinIndicator()` | 112 indicator functions (`rsi, macd, adx, atr, mfi, obv, stoch, supertrend, bollinger_*`, …) | `rsi(close_series)` raised `ValueError: could not convert string to float: 'FPT'` when fed the raw fetched frame | **works on clean numeric input only** |
| 21 | `s.Pattern()` | 22 functions (`detect_doji, detect_engulfing, detect_head_shoulder, detect_wedge, find_pivot_high/low, heiken_ashi, calculate_support_resistance`, …) | `calculate_support_resistance(df)` → 218×2 (support, resistance) on real FPT daily bars | **works** |
| 22 | `s.BidAsk(tickers, callback)` / `s.Trading_Data_Stream(...)` | streaming callbacks | start/stop exist; not exercised to completion | **[untested]** (streaming) |
| 23 | `s.OrderBook().track_order_book_changes(...)` | streaming cancels/adders | blocked > 150 s inside a 180 s run | **hangs — do not use in a 26 h build** |
| 24 | `s.FiinQuantConnector(broker, user, pwd)` | DNSE brokerage: `login, get_orderbook, place_order, modify_order, get_positions, trading_power…` (24 methods) | not called (would place real orders) | **[untested]** — out of scope |

### 1.2 Granularity, history depth and hard limits (measured, not assumed)

| Thing | Granularity | History actually returned | Limit hit |
|-------|-------------|---------------------------|-----------|
| OHLCV daily | 1d, adjusted or raw | 248 rows for 2025-11-20→2026-11-19; 76 rows for 2026-08-01→2026-11-19 | asking from 2000-01-01 → `Permission error: You can only access data up to 5475 days from the present time` (≈15 y) |
| OHLCV intraday | 1m | 226 bars for one session (09:15…14:45) **only with `lasted=True`**; without it → 0 rows | `by` valid set is exactly `1m,5m,15m,30m,1h,2h,4h,1d` (anything else raises `ValueError`); `1h` over a 1-year window returned 0 rows silently |
| Index / stock valuation | daily PE, PB | 261 rows = ~1 trading year for VNINDEX | call per window |
| Sector valuation | daily PE, PB per sector (level 1–? ) | 36 rows over 2026-10-01→2026-11-19, levels 2–3 | needs ICB sector names, not tickers |
| Foreign flow | daily and monthly, 21 fields incl. room % | 23 monthly rows 2026-01→2026-11 | – |
| Market breadth | 1 row/day, up/down/flat/floor/ceiling counts | today only | no history parameter |
| Money-flow contribution | 1/5/10/20-day windows, top N | current window only | – |
| Financial ratios | annual + quarterly, consolidated/separate, 40–60 fields (bank-specific NPL, LDR, NIM, loan/deposit growth) | **2021 → present** ("Your package FiinQuant.Premium can't access data for year 2015… You can only access from 2021 to present") | 2015 and 2018 requests silently dropped |
| Rebalance / free float | per index, per budget | live snapshot with `FreeFloat`, `FreeFloatRate`, `MarketCapFLimit` | only index tickers (`VN30`), not single stocks |
| Reference data | 1 row/ticker: `taxCode`, `organizationName/ShortName`, `exchangeCode`, `sector`, ICB L1→L5 | current | – |

Cost/throughput: no rate-limit error observed across ~45 calls in 4 minutes (plan advertises 1,500 req/min, 400 k/month).
Every call takes 0.2–5 s. All numbers above come from the saved samples in `samples\fiin\` (`results.json`, `results2.json`,
`results3.json` hold timings and exact errors).

### 1.3 What FiinQuant is good for / decisions it can power

**Working core (use these):** daily OHLCV 15 y for ~1,600 tickers, 1-minute bars for any session, index/sector/stock PE-PB
daily, foreign buy/sell/net with room %, index money-flow contribution, RRG relative strength, index-basket rebalancing with
free float, 40+ fundamental ratios since 2021 with bank-specific fields, 112 technical indicators, 22 chart-pattern detectors,
`taxCode` on every issuer.

**Broken/unusable (do not design around):** `TickerList`, `get_freefloat`, `get_ceilingfloor`, `get_value_by_investor`,
`StockScreening` (both methods), streaming `OrderBook`, `get_financial_statement` (absent in 0.1.73).

Decisions it could power (one line each):
- **"Is the market expensive right now, and about to rotate?"** VNINDEX PE/PB daily + sector PE/PB + RRG phases per ticker →
  a rotation call with a number and a date.
- **"Which 5 stocks actually moved the index this week?"** money-flow contribution 5Day + breadth + foreign net → attribution.
- **"If I have 1 bn VND, which basket do I buy and how many shares?"** `Rebalance().get(1e9,"VN30")` → exact share counts
  that respect free float.
- **"Is the foreign room closing on this name?"** `get_foreign` room % + net value daily.
- **"How levered / how profitable is this issuer relative to its sector?"** `get_ratios` (2021+, incl. NPL/NIM for banks).
- **"Does this bank's NPL ratio contradict its price?"** bank-specific `ProblemLoansAndLeases...`, `LoanLossReservesToNPLs`, NIM.

**Unusual rating: medium.** Every team at the hackathon has the same FiinQuant account (mentor Dinh Xuan Phan Anh is from
FiinGroup), so raw FiinQuant is *not* differentiating; only the odd corners are — `taxCode` joins to the business registry,
index-basket rebalancing with free float, RRG phases, and PE/PB by ICB level, which nobody bothers to wire.

---

## 2. Vietnamese official / market sources — one real call each (20/11/2026, 10:35–11:35 Asia/Saigon)

All statuses below are from my own `curl`/urllib calls today (`vn_probe.json`, samples in `samples\mine\`). "Unusual" =
would a typical 26-hour student team find **and** use it? `hours` = my estimate to get clean rows into a pipeline.

| # | Area | Exact URL | HTTP | Format | Geo granularity | Time granularity / history | Sample record (real, from today's response) | Licence / robots | h | Unusual | Decisions it could power |
|---|------|-----------|------|--------|-----------------|---------------------------|--------------------------------------------|-----------------|---|---------|--------------------------|
| 1 | Tax parameters (VAT/PIT/CIT/household) | `https://www.gdt.gov.vn/wps/portal/Home` · `https://vanban.chinhphu.vn/` | 200 · 200 | HTML (server-rendered menus, legal text) | national | per legal document (amendments) | "Cục Thuế - Bộ Tài chính - Trang chủ" / "Hệ thống văn bản" | public, robots allow browsing; no bulk licence | 4–6 | low | "How much tax does a 1.5 bn VND household business owe after the 2026 threshold change?" |
| 2 | Household-business **counts** | `https://pxweb.nso.gov.vn/api/v1/vi/Doanh nghiệp` (table `V05.02.px`) | 200 | JSON (PXWeb metadata) | **province (70 values)** | annual, 9 years | `{"id":"V05.02.px","text":"Số doanh nghiệp đăng ký thành lập mới phân theo địa phương","updated":"2026-08-21T19:39:45"}` | public statistics, attribution | 3–4 | **high** | "Which province is actually adding firms this year, and is that where the listed companies are?" |
| 3 | Bank deposit / lending rates | `https://webgia.com/lai-suat/` — **decoy cells**; BIDV `/vn/lai-suat` 200 but 0 tables; techcombank 200 / 0 tables; acb 200 / 2 `%`; mbbank **403 Akamai**; CafeF **404**; SBV `vi/lai-suat` **404**, `dttktt.sbv.gov.vn` **000** | 200 but **no usable numbers** | HTML table, 77 rows, cells replaced by "webgia.com" strings | per bank (37) | current only | `["BIDV","web giá","webgiá.com","xem tại webgia.com",…]` | robots `Disallow:` empty; ToS sells access | – | **none today** | **No machine-readable deposit-rate source found** — a rate-vs-PE screen needs another route (SBV decision PDFs, or a paid aggregator). Do not promise it in the pitch |
| 4 | Gold, domestic vs world | `https://btmc.vn/api/BTMCAPI/getpricebtmc?key=...` (JSON) · `https://btmc.vn/gia-vang-theo-ngay.html` (HTML table) · `https://api.gold-api.com/price/XAU` · `https://query1.finance.yahoo.com/v8/finance/chart/GC=F` + `USDVND=X` | 200 · 200 · 200 · 200 | **JSON, 1285 rows** · HTML 1 table/10 rows · JSON tick · JSON 253 daily bars | brand/SJC ring · brand × type · world · world/FX | intraday `20/11/2026 10:05` · daily (datepicker) · spot only, no history · 1 y daily | `"VÀNG MIẾNG SJC": 12,920,000 / 13,420,000`; `{"symbol":"XAU","price":3533.52,"updatedAt":"2026-11-20T03:40:35Z"}`; `GC=F 3528.4 USD/oz`; `USDVND 25,705` | public, no key; quote + attribution; btmc robots disallows `/Content/` only | 1–2 | **high** | "Is the SJC premium 20 %+ — i.e. am I buying at a bubble price versus world gold?" (see §5.1) |
| 5 | FX | `https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx?b=10` | 200 | **XML** | national, per currency | intraday, `11/20/2026 10:34:58 AM` | `USD Buy 25,530 · Transfer 25,560 · Sell 25,940` | public; page says "one request every 5 minutes" | 1 | medium | "Should I convert now or wait — is the bank spread + world rate telling the same story?" |
| 6 | Fuel retail prices | `https://www.petrolimex.com.vn/ndi/gia-xang-dau.html` · `https://webgia.com/gia-xang-dau/` (history) | 200 · 200 | HTML | national, per product (RON95, E5, DO) | per adjustment cycle (~7 days), webgia keeps history | "Petrolimex (PLX) - Tập đoàn Xăng dầu Việt Nam … Giá xăng dầu - Lịch sử giá xăng dầu bán lẻ" | public | 2 | medium | "What does the next fuel adjustment do to my logistics cost per trip?" |
| 7 | Electricity tariff & consumption | `https://www.evn.com.vn/c3/gia-dien/Gia-ban-dien-9-186.aspx` · `https://www.evn.com.vn/` | 200 · 200 | HTML (server-rendered) | national; 6-tier household ladder | per tariff decision (~quarterly) | "Trang thông tin điện tử tổng hợp - Tập đoàn Điện lực Việt Nam" | public | 2–3 | medium | "Does a 400 kWh household cross into tier 4, and what does that add per month?" |
| 8 | Land price tables / property | `https://land24h.net/` (200, project listings) · `https://thuvienphapluat.vn/banan/land-tables` (**403**) | 200 · 403 | HTML, unstructured; official tables are per-province PDF decisions | province → district → road | annual price frameworks | "Dự án bất động sản Hà Nội - Bỏ qua menu B1.20 An Vượng Villas, Dương Nội, Hà Đông…" | public decisions; site blocks bots | 6–8 | **high** but expensive | "Is this land asking price above the official price frame (and therefore the tax base)?" |
| 9 | CPI / prices by item & province | `https://www.nso.gov.vn/` (monthly release) · `https://pxweb.nso.gov.vn/api/v1/vi` · `data.nso.gov.vn` | 200 · **200** · DNS fail | HTML · **JSON (8 databases, 118 tables)** · – | national + province dimensions in PXWeb | monthly (4–6 weeks lag); PXWeb tables carry 9 years | PXWeb: `[{"dbid":"Công nghiệp"},{"dbid":"Đầu tư"},{"dbid":"Doanh nghiệp"},{"dbid":"Dân số và lao động"}]` | public statistics, attribution | 3–5 | **high** | "Where is the cost of living actually rising — CPI item × province — and who is hit?" |
| 10 | VHLSS household survey | `https://microdata.worldbank.org/index.php/catalog?sk=Vietnam` | 200 | HTML catalog; microdata behind registration | province (in the raw files) | 2002→2022 waves | "Data Catalog … Home / Central Data Catalog" (Vietnam surveys listed) | World Bank terms; registration/login required for files | 2 meta / 8 raw | **high** | "What share of households in a province cannot absorb a 20 % income shock?" |
| 11 | Social insurance / pension | `https://baohiemxahoi.gov.vn/` | **ERR** (SSL unsafe legacy renegotiation) | – | – | – | no response | unknown | 4+ | medium | "At what contribution level does the pension replacement rate beat self-saving?" [partially tested] |
| 12 | Agriculture / coffee price | `https://giacaphe.com/gia-ca-phe-noi-dia/` · `mard.gov.vn` | 200 · ERR (timeout) | HTML, daily table | province (growing regions) + world (Robusta London) | daily, `20/11/2026` | "Giá cà phê hôm nay 20/11/2026 cao nhất 74,000 vnđ/kg" | public | 2 | medium | "Sell coffee now or hold — domestic price vs London robusta minus drying cost?" |
| 13 | Customs / trade by product-partner | `https://www.customs.gov.vn/` · UN Comtrade (§3) | 200 (14 KB JS shell "Hải Quan Việt Nam") · 200 | JS app · JSON | province of customs office · HS code × partner | monthly · annual 2023 tested | customs shell returns no tables server-side | public | 4 (site) / 1–2 (Comtrade) | medium | "Which export line and partner caused this month's trade swing?" |
| 14 | Public investment disbursement | `https://www.mof.gov.vn/` · `https://baodautu.vn/` | 200 (2.9 KB SPA shell) · 200 | JS SPA · news HTML | province (in reports) | monthly reports, prose | "Cổng thông tin điện tử Bộ Tài Chính" (no tables in HTML) | public | 6+ | medium | "Which province is behind its disbursement plan, and what does that do to local demand?" |
| 15 | Climate / flood / air quality | `https://air-quality-api.open-meteo.com/v1/air-quality` · `https://flood-api.open-meteo.com/v1/flood` · `api.openaq.org/v3/locations` | 200 · 200 · **401** | JSON · JSON · needs key | any lat/lon (province, district) | hourly PM2.5 2022→now · daily river discharge 1984→now | `{"latitude":10.775,"longitude":1…}` discharge series; AQ hourly `pm2_5` | Open-Meteo CC-BY 4.0, non-commercial free | 1 | medium | "Which warehouse/district is exposed to flood or PM2.5 spikes next week?" |

**What failed and why (VN), cross-checked with the parallel worker (`partial_vn.md`, 69 samples + 23 robots.txt):**
`cafef.vn/lai-suat-ngan-hang.chn` 404; BIDV `InterestRateList.aspx` 342 KB error shell and `/vn/lai-suat` has **0 tables** (client-rendered);
techcombank `/tiet-kiem` 200 / **0 tables**; ACB `/lai-suat` 200 but only two `%` signs on the page; **mbbank 403 Akamai even on robots.txt**;
SBV policy-rate pages `vi/lai-suat` 404 and `dttktt.sbv.gov.vn` unreachable; `webgia.com/lai-suat` **serves decoy cells** (real numbers replaced by
`webgia.com` / `web giá` strings, 77 rows of it) so it is free but unusable without OCR — *this kills the deposit-rate leg of any equity-risk-premium idea*;
`sjc.com.vn` 403 WAF and its `/ajax/price/history/gold`, `/xml/tygiavang.xml` 404 although robots allows them; `thuvienphapluat.vn` land-price section is a
3.7 KB `NOINDEX` stub (403 on my probe) and the real tables are images/`.aspx` docs; `nso.gov.vn` hub pages carry **0 tables / 0 xlsx links at hub level**
(the numbers sit in per-article XLSX attachments); `data.nso.gov.vn` does not resolve; `mard.gov.vn` connect timeout (21 s); `baohiemxahoi.gov.vn` refuses TLS
renegotiation (legacy cipher); `openaq.org` v3 requires a free key (401). GDT article URLs are session-seeded (`/wps/portal/!ut/p/z0/…`, ~280 chars) — no stable crawl path.
**Still open:** whether NSO's PXWeb POST route can be made to return data (metadata 200, query returned the table list instead of cells) — 2–4 h to settle.

---

## 3. International open data with real Vietnam granularity — one real call each

| # | Source | Exact URL | HTTP | Format | Geo granularity | Time / history | Sample record (real) | Licence | h | Unusual | Decisions it could power |
|---|---|-----------|------|--------|-----------------|----------------|----------------------|---------|---|---------|--------------------------|
| 1 | World Bank API v2 | `api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.CD?format=json` | 200 | JSON | **country only** | 1960→2025, 66 points, `lastupdated 2026-11-11` | GDP 2025 = `514,697,215,165.065` USD; PM2.5 2023 = 24.78 µg/m³; pop 2025 = 101,598,527 | CC-BY 4.0 | 1 | low | "Is Vietnam's growth decoupling from its pollution/energy path?" |
| 2 | IMF SDMX 2.1 | `api.imf.org/external/sdmx/2.1/dataflow` · `/data/...WEO` | 200 · 200 | SDMX XML/JSON | country | WEO projections to 2030 | `{"header","dataSets","structure"}` (WEO dataset 14.5 KB) | IMF terms, attribution | 2–3 | low | macro baseline for forecast-vs-outcome checks. DataMapper API is 403 today |
| 3 | UN Comtrade (public preview, no key) | `comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=704&period=2023&cmdCode=27&flowCode=M` | 200 | JSON | HS code × partner | annual, back to 1962 (preview caps rows) | 2023 imports of HS 27 = `25,685,316,504.324` USD, 59 partner rows | UN terms, free w/ attribution | 1–2 | medium | "Which partner supplies our fuel, at what value — and what does a shock there cost?" |
| 4 | NASA POWER | `power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR&community=AG&longitude=105.85&latitude=21.03` | 200 | JSON | **any lat/lon** (0.5° point or regional) | daily, 1981→now | `T2M 2024-01-01 = 20.95 °C`, `PRECTOTCORR = 0.94 mm` | public domain (NASA) | 1 | medium | "Has this district's heat/rain shifted enough to change agri or cooling load?" |
| 5 | Open-Meteo (archive / air / flood) | `archive-api…/v1/archive` · `air-quality-api…` · `flood-api…` | 200 · 200 · 200 | JSON | any lat/lon, hourly or daily | 1940→now (archive) · 2022→now (AQ) · 1984→now (discharge) | daily `river_discharge` m³/s series; hourly `pm2_5` | CC-BY 4.0, free non-commercial | 1 | low–med (everyone uses weather) | "Which province is water-stressed or PM-heavy in the next 7 days?" |
| 6 | Global Solar Atlas API | `api.globalsolaratlas.info/data/lta?loc=10.75,106.67` | 200 | JSON (Solargis 1.7) | point → country | long-term average to 2025, `updated 2026-04-01` | `PVOUT 1459.34 kWh/kWp/yr · GHI 1820.62 · DNI 1239.82 · TEMP 27.06 °C · ELE 5 m` (HCMC) | CC-BY 4.0 (Solargis/World Bank), no raw-layer redistribution | 1–2 | **high** | "What does 1 MW of rooftop PV yield here, and what is that worth at today's EVN tariff?" |
| 7 | WorldPop REST | `worldpop.org/rest/data/pop/wpgp?iso3=VNM` | 200 | JSON catalog + GeoTIFF | **100 m grid**, national file | 21 layers, 2000–2020 | `vnm_ppp_2000.tif`, doi `10.5258/SOTON/WP00645` | CC-BY 4.0 | 3 (raster→province) | **high** | "How many people live inside this flood/discharge zone?" |
| 8 | HDX — COD admin boundaries (**the province spine**) | `data.humdata.org/api/3/action/package_search?q=vietnam` → COD-AB XLSX resource | 200 | JSON API → XLSX/GeoJSON | **34 ADM1 units (post-2025 merger)** + ADM2 + centroids | `valid_on 2025-09-25`, source GSO | `An Giang, VN91, 9986.95 km², Province` (277 VN datasets in the catalog) | CC-BY-IGO | 1 | **high** | the correct 34-province key so nothing joins old 63-province data by name |
| 9 | geoBoundaries | `geoboundaries.org/api/current/gbOpen/VNM/ADM1/` | 200 | JSON meta → SHP/GeoJSON | ADM1 **64 units, year represented 2008**; ADM2 708 units (2020) | static release Dec 2023 | `{"boundaryID":"VNM-ADM1-63759600","boundaryLicense":"Public Domain","admUnitCount":64}` | Public Domain | 1 | medium — **stale, see risk** | easy geometry, but it predates the 2025 merger: names will silently mismatch |
| 10 | Global Data Lab SHDI | `globaldatalab.org/shdi/table/shdi/VNM/?format=json&levels=2&years=2022` | 200 (`levels=3` province rows → **500**) | JSON wrapping an HTML table (v10.2) | **6 regions only, not provinces** | annual, 1990→2022 | `Red River Delta 0.808 · South East 0.775 · Central Highlands 0.720 · Vietnam 0.764` | free for non-commercial use, cite GDL | 1 | **high** | "Which region is falling behind — the 'who is left behind' slide, with no GSO PDF" |
| 10b | Climate TRACE v6 asset emissions | `api.climatetrace.org/v6/assets?countries=VNM&limit=3` | 200 | JSON | **asset level with centroid** | annual, asset capacity + activity | `Duyen Hai Power Generation Complex, coal, 4,378 MW, 22,170,000 t CO2e` | CC-BY 4.0 | 4 | **high** | "Which facility/province carries the emissions and transition risk?" |
| 11 | Our World in Data (CSV) | `ourworldindata.org/grapher/gdp-per-capita-worldbank.csv?country=~VNM` | 200 | CSV | country | →2025, 7,446 rows in the full file | `Vietnam,VNM,2025,…` | CC-BY | 0.5 | low | one-line macro context for a chart |
| 12 | Copernicus CDS / EMS | `cds.climate.copernicus.eu/api` · `emergency.copernicus.eu` | **401** · 404 | – | – | ERA5 hourly since 1940 | needs an account/key | Copernicus licence | 3+ | medium | ERA5 climate — **[needs key, untested data]** |
| 13 | Google Trends | `trends.google.com/trends/api/explore` | **429** | – | province-level possible | 2004→now | blocked without an unofficial lib | ToS restricts | 3+ | medium | search-interest nowcast — **[untested, blocked]** |
| 14 | FAOSTAT · ADB Data Library · ADB KI · Global Wind Atlas | `fenixservices.fao.org/faostat/…` (521) · `faostatservices.fao.org` (**401**) · `data.adb.org/api/3/action/…` (**403 Cloudflare**) · `kidb.adb.org` (200 HTML) · 5 GWA paths (**404/400**) | mostly failed | – | – | – | FAO now needs a subscriber token; ADB DCAT is behind a JS challenge | – | 2 | medium | – **[failed — do not promise these]** |

---

## 4. Rankings at a glance

**Unusual = high (nobody else will have it):** BTMC gold JSON (all brands, bid/ask, intraday) · NSO PXWeb
(`pxweb.nso.gov.vn`, 118 province-level tables) · WorldPop 100 m grid joined to Open-Meteo flood discharge ·
Global Solar Atlas PVOUT per site · GDL subnational HDI · provincial land-price frames (expensive, PDF).
**Medium:** fuel adjustment cycle, EVN tariff ladder, UN Comtrade, NASA POWER, HDX, geoBoundaries, customs/trade, Open-Meteo AQ.
**Unavailable today (do not build on it):** bank deposit-rate tables (every route above is client-rendered, blocked, or decoy-poisoned).
**Low (every team will use these):** World Bank WDI, IMF, OWID, Open-Meteo weather, NSO homepage prose, FiinQuant raw prices.

---

## 5. Top 5 "unusual but real" combinations (join key + evidence on real rows)

### 5.1 SJC premium tracker — domestic gold vs world gold vs the dong
`BTMC JSON` (SJC sell 13,420,000 VND/lượng, 20/11 10:05) × `Yahoo GC=F` (3,528.4 USD/oz, 20/11) × `USDVND=X` (25,705).
1 lượng = 37.5 g = 1.20565 troy oz → world parity = 3,528.4 × 1.20565 × 25,705 = **109.35 m VND**; SJC sell 134.2 m →
**premium +22.7 %** (19.9 % if converted at Vietcombank's 25,940 sell from the same-day VCB XML).
Join key: **calendar date** (all three feeds timestamped today). Decision: "buy gold now, wait, or arbitrage?" — no other team
will have this number, and it is the most-asked money question in Vietnam right now.

### 5.2 Region business formation × listed companies × development
`NSO PXWeb V05.02` (new firms, **70 province values × 9 years**) + `HDX COD-AB` (**34 `adm1_pcode`, valid_on 2025-09-25** — the correct
spine; `geoBoundaries` ADM1 is 64 units from **2008** and will silently mismatch) + `GDL SHDI` (**6 regions only** — join at region
level) + FiinQuant `BasicInfor.taxCode`, whose **first 2 digits are the province code** (VCB/FPT/VIC/DGC `01…` = Hà Nội,
VNM/MSN/PNJ `03…` = TP.HCM, HPG `09…`, GAS `35…`, HAG `59…` — verified in `samples\fiin\taxcodes.csv`).
Join key: **`adm1_pcode` / 2-digit tax-code prefix** (names are unsafe: 63→34 province merger).
Decision: "where is formal-sector firm creation outrunning the listed companies — and which region is falling behind?"

### 5.3 Equity valuation vs the gold premium (the deposit-rate leg is dead, see §2 row 3)
FiinQuant `MarketDepth.get_index_valuation("VNINDEX", 1 y)` → **261 daily PE/PB rows** (PE 14.10, PB 1.946 on 2025-11-03, last row
2026-11-19) × the SJC premium from 5.1 × FiinQuant `get_foreign` monthly net (FPT Nov 2026 **−1.92 tn VND**, room 48.99 %).
Join key: **date / month**. Decision: "when the domestic gold premium is 20 % and equities sit at PE 14, where does household money
actually go?" A 1/PE = 7.1 % earnings yield is only comparable to a term deposit if you can find the deposit rate — which today you
cannot from any free API, so show the gold leg and take the rate from SBV decision documents rather than inventing a number.

### 5.4 Foreign flow vs the dong and the gold premium
FiinQuant `PriceStatistics.get_foreign(…,"Monthly")` (FPT Nov 2026 net **−1.92 tn VND**, foreign room 48.99 %) × `VCB XML`
USD (25,530 / 25,940) × the SJC premium from 5.1. Join key: **month / trading date**.
Decision: "when the dong weakens and the gold premium widens, do foreign investors leave — and how fast?"

### 5.5 Hazard micro-geography of listed names
FiinQuant `BasicInfor` (ticker → taxCode → province, 10/10 resolved) + `Open-Meteo flood` daily `river_discharge` (real cell:
26.99 → 300.30 m³/s, Central Vietnam, 2020-10-01→11) + `Open-Meteo air-quality` `pm2_5` + `WorldPop` 100 m grid at the same lat/lon,
snapped to `HDX COD-AB` **ADM1 pcode**. Join key: **adm1_pcode → centroid lat/lon**. Decision: "which HOSE names sit in the provinces
with the highest flood / PM2.5 exposure next quarter?" — a supply-chain risk screen with no paid data beyond the account we already have.

**Risks for these combos:** 5.2 needs the PXWeb POST query solved (2–4 h) or the same series scraped from the NSO release page;
5.3/5.4 must **not** claim a deposit-rate comparison (no usable free source today); 5.2/5.5 must use `adm1_pcode` from HDX COD-AB,
**never** geoBoundaries names (2008, 64 units) nor GDL "provinces" (it serves 6 regions). FiinQuant terms: keep raw data internal,
publish aggregates with attribution. Both parallel workers' full evidence: `partial_vn.md`, `partial_intl.md`.
