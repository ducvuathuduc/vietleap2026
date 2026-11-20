# B-RATES — the deposit-rate panel: 21 banks × 8 terms × 2 channels today, plus what history is actually reachable

Built 20/11/2026 12:24–13:10 Asia/Saigon from this folder. No repo file touched, no git write, no process killed.
Files: `samples\rates_panel_today.csv` (289 rate rows), `samples\rates_gap_by_term.csv`, `samples\rates_history_sample.csv`,
raw pages in `http\pages\`, probe log in `http\probe.csv`, scripts `probe.py`, `build_panel.py`, `history.py`.

## 1. Today's panel — 21 banks, individual VND, counter + online, 8 terms

**Mechanism (what worked, in order of cost).** Raw HTML first: one GET per candidate URL (urllib, robots.txt read per host,
≥2.2 s spacing). Result in `http\probe.csv` (35 bank URLs + 4 aggregators): only **7 of 34** bank rate pages deliver numbers
server-side — BIDV `200`/334 KB/**106** `d.d%` matches, Agribank `200`/89 KB/**94**, VietBank `200`/**391**, LPBank `200`/474 KB/**76**,
TPBank `200`/**67**, MSB `200`/167 KB + **4 rate PDFs** + 77 JSON keys, NamABank `200`/34 KB + 1 PDF. Everything else was
client-rendered or absent: ACB `200` 0 %, OCB `200` 0 %, KienlongBank `200` 0 %, VIB `200`/1.9 KB shell, SCB `200`/3 KB shell,
VietABank `200`/3.2 KB shell, PGBank `200`/1.9 KB; MB **403**, SHB **403**; HDBank, SeABank, Techcombank (2 paths), VPBank,
Sacombank, NCB (`404`, 13 B), ABBank, BaoVietBank, GPBank, CBBank all **404**; VCB, BacABank, Saigonbank, OceanBank TLS
`URLError`; PVcomBank timeout. So the bank-by-bank HTML route alone cannot reach 25 banks.

**The panel backbone** is `https://laisuattietkiem.vn/` — fetched once, `HTTP 200`, 92 KB, **440** rate cells, fully server-rendered:
22 bank blocks × {Tại quầy, Online} × {1,3,6,9,12,18,24,36} months, each block carrying a `Nguồn` link to the bank's own rate
page, page stamp **"Cập nhật lúc: 09:51:13 ngày 20/11/2026"**. It is an aggregator, not a bank, so its `source_url` column keeps
the bank page it scraped and every row is graded:

| grade | rows | meaning |
|---|---|---|
| `verified: aggregator + bank page number seen` | **21** | the same figure also appears in that bank's own HTML downloaded today (BIDV, Agribank, TPBank, LPBank, MSB, VietBank, NamABank pages, `http\pages\*.html`) |
| `agent_only: aggregator is the only reader` | **268** | one reader only — do not publish without a second reader |

That second reader is weak by construction: it proves the number exists on the bank page, not that it sits in the right
channel/term cell. A TinyFish re-read per bank (D-UNLOCK: 150–275 s/run, 2 concurrent, USD 0.13–0.29) would fix it.

**Coverage: 21 distinct banks** of the ~30 commercial banks — Agribank, BIDV, Vietcombank, Vietinbank, ACB, ABBank, Bắc Á,
Eximbank, LPBank, MB, MSB, Nam A, OCB, Sacombank, SHB, Techcombank, TPBank, VIB, Vietbank, VPBank, PVcomBank, plus the digital
brand **VCB Neo** kept as its own row (22 blocks). **Not covered (a gap, stated plainly):** HDBank, SeABank, SCB, NCB,
KienlongBank, Saigonbank, PGBank, BVBank/VietABank, BaoVietBank, GPBank, OceanBank, CBBank — all client-rendered or 404 today
(`http\probe.csv`). Closing them with TinyFish is ≈12–18 min wall clock and ≈USD 2.4 (measured runs), which did not fit the
40-minute box; **no TinyFish run was spent in this task (USD 0.00)**.

**Effective date.** Only the aggregator's update stamp (2026-11-20 09:51) is machine-readable; per-bank "ngày hiệu lực" was not
extracted (`bank_page_date_seen` column holds a date only where a date string existed on the page — not a rate-table date).
Do not present `effective_date` as the bank's own effective date.

## 2. History 2021–2026 — tested, and the honest answer is "not at these URLs"

Tested 3 banks × 4 dates (2021, 2022, 2024, 2025), `samples\rates_history_sample.csv`, raw in `http\hist\`:

| bank | CDX query | result |
|---|---|---|
| BIDV | `https://web.archive.org/cdx/search/cdx?url=bidv.com.vn%2Fvn%2Flai-suat*&output=json&filter=statuscode:200&collapse=digest&from=2021&to=2026&limit=400` | **HTTP 200, `[]` — zero snapshots**. Same for the plain-exact form (HTTP 200, `[]`) and for `archive.org/wayback/available?url=bidv.com.vn/vn/lai-suat&timestamp=20230601` → `{"archived_snapshots":{}}` |
| Sacombank | same form on `sacombank.com.vn/ca-nhan/lai-suat.html` | **HTTP 429** (nginx, 162 B) on the first attempt, `[]` (HTTP 200) on the exact-path form |
| Techcombank | same form on `techcombank.com/thong-tin/lai-suat` | **HTTP 200, `[]` — zero snapshots** |

The API itself is alive and deep — `?url=techcombank.com&matchType=domain&limit=4` returned **HTTP 200** with rows back to
**2002-06-02** — so the failure is specific to the current rate-page paths: Wayback never captured them (they are JS-driven and
often the crawl landed on `404`). Additional blockers met today: every 3rd–4th CDX call answers **429 Too Many Requests**
(three times, `http/cdx_filter_resp*` not written because curl failed mid-loop; the 429 body is 162 B), and Python `urllib`
cannot talk to `web.archive.org` at all on this machine — `SSLCertVerificationError: Basic Constraints of CA cert not marked
critical` — so all Wayback work must go through `curl`.

**Verdict / effort for a real backfill.** A bank-level 2021–2026 rate series is **not obtainable from Wayback at today's page
URLs**. Two routes remain, both untested here for lack of time: (a) archived *PDF* rate sheets (banks publish dated PDFs; if the
PDF URL pattern was crawled, CDX by URL prefix would find them) — needs ~1 query + 1 fetch per bank-month; (b) monthly press
tables (VnExpress/CafeF/Vietstock "lãi suất ngân hàng ngày …" articles) — one article per month yields all banks but only the
headline term(s). Order-of-magnitude: 30 banks × 60 months = 1,800 fetches at 3–10 s (Wayback throttling included) = **2–5 h**,
plus parsing per source; a press-table route is **60 articles**, ~1–2 h, shallower. **CafeF's live page was checked and
rejected**: `https://cafef.vn/du-lieu/lai-suat-ngan-hang.chn` (200, 243 KB) embeds a bank × term table, but its per-bank sheet
images are dated 2023 (`…/ImageInterestRates/HDB22022023142340.PNG`) and its BIDV row (2.1 / 2.4 / 3 / 3 / 5.4 …) contradicts
today's BIDV board, i.e. it is a stale snapshot — using it would have manufactured history.

## 3. First real numbers from today's panel

All arithmetic on `samples\rates_panel_today.csv` → `samples\rates_gap_by_term.csv`. Counter vs online at the same bank and term:

| term | banks with both channels | banks with online > counter | median gap | largest gap |
|---|---|---|---|---|
| 1 m | 15 | 12 | **+0.10 pp** | +2.65 BIDV |
| 3 m | 16 | 11 | +0.12 pp | +0.65 TPBank |
| 6 m | 16 | 15 | **+0.65 pp** | **+1.85 BIDV** |
| 9 m | 15 | 14 | **+0.70 pp** | **+1.85 BIDV** |
| 12 m | 15 | 14 | +0.30 pp | **+1.40 Sacombank and BIDV** |
| 18 m | 14 | 14 | +0.35 pp | +1.30 Sacombank |
| 24 m | 14 | 12 | +0.30 pp | +1.30 BIDV |
| 36 m | 14 | 12 | +0.35 pp | +1.30 BIDV |

- **The gap is real and one-sided at every term**: 12 of 15 banks at 1 m, 14 of 15 at 12 m, 14 of 14 at 18 m pay more online.
  It is *small* at 1–3 months (0.10–0.12 pp) and jumps at 6–9 months (0.65–0.70 pp) — the online premium is bought with term.
- **Largest gaps** are not at the biggest banks only: BIDV +1.85 pp (6 m and 9 m), Sacombank +1.40 pp (12 m), BIDV +1.40 pp
  (12 m), Sacombank +1.30 pp (18 m). Sacombank's 12 m 7.00 vs 5.60 is the one gap already confirmed by the bank's own PDF in
  D-UNLOCK §2 — today's aggregator reproduces it exactly.
- **12-month online spread: min 5.20 (ACB), median 6.25, max 7.00 (VIB, VCB Neo, Sacombank); n=17.** Top of the table:
  VIB 7.00, VCB Neo 7.00, Sacombank 7.00, BIDV 6.80, LPBank 6.70. 12-month **counter**: min 4.50 (Eximbank), median 5.75,
  max 6.90 (VPBank), n=20 — i.e. the whole counter market sits ~0.5 pp below the online median.
- **Longest is not best**: 36 m online median **6.00** is *below* 12 m (6.25) and 24 m (6.06); LPBank online drops 6.70 (12 m) →
  5.60 (36 m) and Sacombank counter 6.40 at 24/36 m is below its own 12 m online 7.00. Chasing the longest term loses money at those banks.

**Two cells are visibly wrong and must not be quoted** (they are in the CSV, graded agent_only): Sacombank 1 m counter
**0.50 %** (a demand-deposit rate, not 1 m — its own 3 m counter is 4.75) and VIB 12 m online **7.00 %**, which breaks the row's
monotonicity (5.80 at 9 m → 7.00 → 5.90 at 18 m). With both dropped, the 1 m median gap stays +0.10 pp and 12 m online median
falls to **6.10** (max still 7.00, Sacombank). This is exactly the error class a second reader per bank catches.

## 4. Rules compliance
robots.txt read per host before crawling; ≥2.2 s between requests to the same host; no captcha/login bypass; no secret printed;
TinyFish budget untouched (USD 0.00 of 6.00, no run ids); no repo edits; no dependency installed; nothing written outside this
folder. Negative claims above each carry the exact URL and the response received (HTTP code and body size).
