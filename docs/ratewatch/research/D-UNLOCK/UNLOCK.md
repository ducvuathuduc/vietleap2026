# D-UNLOCK — three "hard" sources opened (or proven shut) with real calls
All calls made 20/11/2026 10:52–12:20 Asia/Saigon from this folder. Read-only on the repo; nothing written outside
`C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\D-UNLOCK`. Samples in `samples\`, raw evidence in `http\`, scripts in this folder.

## 1. Gold history — BTMC daily SJC bar + ring gold, 2017-05-02 → today (WORKS, deep enough)

| # | Fact | Evidence |
|---|------|----------|
| 1 | robots.txt allows it | `GET https://btmc.vn/robots.txt` **200**, `Allow: /`; only `/Content/ /Scripts/ /Areas/ /bin/ /Data/ /admin /casino /bet …` disallowed. Checked 10:53 |
| 2 | Date picker → real JSON endpoint | `GET https://btmc.vn/gia-vang-theo-ngay.html` **200, 147,392 B** → JS calls `GET /ProductHome/getGoldDate?date=DD/MM/YYYY` → **200**, `{"Data":{"sjcmua":"<b>12880</b>","sjcban":"<b>13420</b>","btmcvangnhanmua":…,"btmcvangnhanban":…,"trangsuc…","vangnguyenlieu…"}}` (14 fields) |
| 3 | Depth | 94 single-date probes, 2.2 s apart, 10:56–11:15. **Earliest date with data = 2017-05-02** (2017-04-20, 2017-03-20, 2017-01-02, 2016-06-15, 2015-06-15 all return `Data` with empty values). **Latest = 2026-11-20** → 3,490 calendar days, ~9.5 years |
| 4 | Gaps | 25 of 94 probe dates empty: 9 weekend, 16 weekday = all pre-2017-05-02 dates + Tết (2018-02-15, 2021-02-15) + 2017-01-02. **Weekends are mostly published** (17 of 26 weekend probes had data), so the real series is "days the shop published", not "business days". 21/21 days 2026-10-01→10-21 had data |
| 5 | Unit (the trap) | History values are 5-digit thousand-VND numbers. Same moment: history `sjcban 13420` vs intraday `GET /api/BTMCAPI/getpricebtmc?key=…` **200** → `"VÀNG MIẾNG SJC": 12,920,000 / 13,420,000` = **×1,000 → VND per CHỈ**, so **×10,000 = VND per lượng**. Anchors: 2024-06-15 sell 7698 → **76.98 m VND/lượng** (matches reported SJC mid-June 2024); today 134.2 m vs world parity 109.35 m (GC=F 3,528.4 × 1.20565 oz × 25,705) = **+22.7 % premium**. If the unit were 1,000 VND/lượng the bar would cost 13.4 m, i.e. 8× *below* world — impossible |
| 6 | Sample rows (real) | 2017-05-02 SJC 36.66 / 36.72 m; 2019-06-15 37.42 / 37.53 m; 2024-06-15 75.50 / 76.98 m; 2025-11-15 149.0 / 151.0 m; 2026-02-15 178.0 / 181.0 m; **2026-11-20 SJC 128.80 / 134.20 m, ring gold 128.80 / 133.80 m** (VND/lượng) |
| 7 | Full daily backfill | 3,490 requests (1/date). Measured 0.75 s mean latency + 2.2 s deliberate delay → **≈2.9 h single-threaded, ~50 MB raw JSON**; ~2.1 h if only Mon–Sat |
| 8 | Files | `samples\gold_history_sample.csv` — 138 rows = 69 dates × {SJC bar, BTMC ring gold 999.9}, columns `date,product,buy,sell,source_url,http,checked_at` (buy/sell in VND per lượng) |

Other SJC-history sources were **not needed** (BTMC is 9.5 y deep) and are **[untested]** here; SUPPLY.md already records
sjc.com.vn 403 WAF and webgia decoy cells.

## 2. Deposit rates today — 10 banks via TinyFish, only 36/89 numbers independently confirmable

Runs: `POST https://agent.tinyfish.ai/v1/automation/run-async` (X-API-Key from env, 2 concurrent, `max_duration_seconds 170`),
poll `GET /v1/runs/{id}` every 8 s. Log: `samples\tinyfish_runs.csv` (run id, steps, cost, seconds, source URL).

| Bank | Run id | Steps | USD | Rows | Independently verified |
|---|---|---|---|---|---|
| VCB | 0dbefdbb-b273-45d7-8d90-9c8986e72dfe | 13 | 0.208 | 5 | 1 |
| BIDV | 7e56a9e5-21b5-40b1-bdfa-9a1d0617bf1d | 8 | 0.128 | 10 | 1 |
| Agribank | dc13f0ee-4230-4951-b7c3-3af2447deda5 | 11 | 0.176 | 10 | 0 |
| VietinBank | b123371b-ade4-4b26-a382-2767fd337b16 | 23 | 0.368 | 5 | 5 |
| Techcombank | 9b62689b-5b95-47a2-ad8b-344da888a482 | 9 | 0.144 | 10 | 0 |
| MB | 3e1585a3-b542-49d3-b88a-8aae61d277a7 | 18 | 0.288 | 10 | 0 |
| ACB | 03d86668-33da-49de-95e2-b7602e5d9fc9 | 11 | 0.176 | 10 | 10 |
| VPBank | f3662d64-0292-4b04-8f2f-9bafd726d0c8 | 10 | 0.160 | 10 | 0 |
| HDBank | 9839a98a-be39-4ad8-99ff-35faf336df6a | 9 | 0.144 | 10 | 10 |
| Sacombank | 2ba12391-8043-4e13-8712-76e608867b60 | 9 | 0.144 | 10 | 10 |
| TPBank / VIB | — | — | — | — | **[untested — 45-min box hit before the queue reached them]** |

**Total spend 1.95 USD of the 6 USD budget**; 12 banks asked, 10 completed (`COMPLETED`), 2 never launched.
One returned row (`ACB` 24 tháng online = 0 %, quote `N/A`) was dropped as a non-rate; 89 rows remain.
The checks the brief demanded, and what they returned:
- `POST https://api.fetch.tinyfish.ai {"urls":[page],"format":"markdown"}` (free) on every source URL → **200, no errors**, but
  the text is the page chrome only: VCB 109 chars, Agribank 1,585 chars with **no rate table** (numbers like `4.32, 5.32` are
  unrelated). Verdict: TinyFetch alone cannot confirm these pages.
- Raw HTML (urllib, 1 GET/bank, 2.2 s apart) → **200** for 9 of 10 URLs (VietinBank `/lai-suat` **404**; the AI had used
  `/ca-nhan/cong-cu-tien-ich/lai-suat-khcn`), 149–369 KB, but **0 `\d.\d%` matches** on 8 of them: the tables are client-rendered.
- Net result `verified_by` in the CSV: `tinyfetch:rate+term` 33, `tinyfetch:rate_only` 3, **`agent_only_unconfirmed` 53**.
  ACB (9/9), HDBank (10/10), Sacombank (10/10) and VietinBank (5/5) are confirmed against the page text; Agribank, MB,
  Techcombank, VPBank have **0/10** confirmed — **do not publish those four without a second reader**. `effective_date` is unreliable (Agribank came back `2025-07-14`, a stale page footer) — use it only if it
  also appears in the verified page text.
- Cross-bank plausibility of the unverified set: 12 m online 4.5–7.5 %, 12 m counter 3.0–5.4 % — consistent order of magnitude,
  but that is a sanity band, not verification.
- SBV: `https://www.sbv.gov.vn/` **200 (423 KB)**, `/vi/lai-suat` **404**, `/webcenter/portal/vi/menu/trangchu/ls` **200 (423 KB,
  8 "lãi suất" menu hits: "Lãi suất NHNN quy định", "Lãi suất thị trường liên ngân hàng", no numbers, 0 PDF links in HTML)**.
  **No official page lists historical bank-level rates** — SBV publishes policy/ceiling decisions as documents, so history must
  be built from press/decision PDFs [untested for depth].
- File: `samples\deposit_rates_today.csv` — 89 rows, `bank,channel,term_months,rate_pct,effective_date,source_url,verified_by,quote`.

## 3. NSO PXWeb — metadata works, **the POST query route does not exist**; CPI is not in the API

| # | Fact | Evidence |
|---|------|----------|
| 1 | robots | `GET https://pxweb.nso.gov.vn/robots.txt` **200**, no `Disallow` |
| 2 | DB list | `GET https://pxweb.nso.gov.vn/api/v1/vi` **200** → 8 dbids, but only **3 exist**: `Công nghiệp` (9 tables), `Doanh nghiệp` (56), `Dân số và lao động` (62). `Đầu tư`, `Education`, `Enterprise`, `Giáo dục`, `Industry` → **404** |
| 3 | Table metadata | `GET /api/v1/vi/Doanh nghiệp/V05.02.px` **200** → `Tỉnh/thành phố` (70 values, text: CẢ NƯỚC, 6 regions, 63 provinces) × `Năm` (9 values 2016–2024) |
| 4 | POST query | **Not implemented.** `POST` the brief's `{"query":[{"code":…,"selection":{"filter":"all","values":["*"]}}],"response":{"format":"json-stat2"}}` to `/V05.02.px` → **404** (ASP.NET error page); to `/V05.02.px/query`, `/V05.02`, `/V05.02.px/data`, `/api/v1/vi/Doanh nghiệp`, `/V05.02.px?outputformat=json-stat2`, `/pxweb/api/v1/…`, `/api/v2/vi/…` → **200 but the JSON table list** (POST is routed to the db-level handler, body ignored). Port `:4` from robots sitemap → **connection timeout**. 9 attempts logged in `samples\pxweb_post_attempts.json` |
| 5 | What the cells need | the classic WebForms frontend (`/pxweb/vi/{db}/{table}.px`, `__VIEWSTATE` + `__EVENTTARGET` postback). Cell extraction there is **[untested]** |
| 6 | CPI / prices / credit | not in the API at all: the frontend index lists ~15 databases (`Chỉ số giá`, `Đầu tư và xây dựng`, `Tài khoản quốc gia`, `Thương mại`, `Xuất nhập khẩu`, `Du lịch` …); `GET /pxweb/vi/Chỉ số giá/Chỉ số giá/?tablelist=true` **200 (55 KB)** lists **V11.01–V11.28+ CPI tables**. All of these are **404 on the API**. No credit/credit-growth table anywhere |
| 7 | Province tables found | **44** tables carry a real `Tỉnh/thành phố` variable (70 or 71 values incl. CẢ NƯỚC + regions), years 1995–2025 (`V02.03-07` population 1995→Sơ bộ 2025; `V05.08` enterprise capital 2010→2024; `V07.02` IIP 2012→Sơ bộ 2025). 21 in `Doanh nghiệp`, 22 in `Dân số và lao động`, 1 in `Công nghiệp` |
| 8 | Files | `samples\pxweb_tables.csv` (44 rows: db, table_id, title, topic, province_variable, province_values, first_year, last_year, n_periods, api_url); `samples\pxweb_sample.json` (real 200 metadata payload for V05.02 + the 9 POST attempts showing 404/no-cells) |

Decision impact: the "which province is adding firms / losing jobs" story is **buildable today from metadata + a WebForms cell
scraper** (2–4 h), and CPI-by-province exists but only behind the same scraper.

## Rules compliance
robots.txt read before crawling btmc.vn / pxweb.nso.gov.vn; every crawler waited ≥ 2.2 s per site (94 gold + ~75 PXWeb + 14 SBV/bank
requests); no captcha/login bypass; the API key was read from `TINYFISH_API_KEY` and never printed; no repo file touched, no
package installed; no process killed (all workers were mine and exited on their own deadline).
