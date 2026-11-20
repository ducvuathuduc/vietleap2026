# X-TF — can TinyFish read EVERY Vietnamese commercial bank's deposit rates? 24 of 33 banks, 319 rows, 20 % verified

Tested 20/11/2026 13:08–13:52 Asia/Saigon from this folder. Real calls only; every number below is traceable to an artefact
in `http\` (raw pages, PDFs, `http\tf_runs\*.json`, `http\tf\batch*.json`) and `samples\`. No repo file touched, no git
write, nothing installed into the repo `.venv` (used read-only), no process killed except my own runner (pid 25968).
Scripts: `tf_queue.py` (agent runs), `free_readers.py` (HTML+PDF+TinyFetch), `parse_agg.py`, `grade.py`.
Deliverable data: `samples\rates_all_banks.csv` (319 rows), `samples\reader1_agg.csv`, `samples\merge_stats.json`.

## 1. The bank list (33 entities probed, 30 licensed commercial banks + 1 digital brand + 1 duplicate URL)

Authority: State Bank of Vietnam `https://www.sbv.gov.vn/` — **HTTP 200, 423,297 B, accessed 20/11/2026 13:47**.
The licensed-institution list page is **not server-rendered** at the URLs tried (`https://www.sbv.gov.vn/webcenter/portal/vi/menu/trangchu/hethong/htcctd`
→ HTTP 200 but the body is the same 423,029 B homepage shell, zero bank names; `sbv.gov.vn/vi/lai-suat` was **404** in
D-UNLOCK today), so **the membership below is [inferred]** from the standard 2026 tally and is confirmed only where a bank
actually served a rate page. 4 state-owned: Agribank, BIDV, Vietcombank, VietinBank. Joint-stock (26): ACB, ABBank, BacABank,
BaoVietBank, BVBank, CBBank, Eximbank, GPBank, HDBank, KienlongBank, LPBank, MB, MSB, NamABank, NCB, OCB, OceanBank, PGBank,
PVcomBank, Sacombank, Saigonbank, SCB, SeABank, SHB, Techcombank, TPBank, VIB, VietBank, VPBank, Vietcombank's digital brand
VCBNeo (kept as its own row). URL per bank: `banks.tsv` (34 rows, one per URL tried).

## 2. What each method actually delivered (per bank, from `samples\times`/`merge_stats.json`)

| bank | method that worked | rows | terms | channels | verified | contested | agent_only | agent s | USD |
|---|---|---|---|---|---|---|---|---|---|
| HDBank | **TinyFish agent** (this task, run `781cb22a`, 367 s, 12 steps) + D-UNLOCK agent run | 34 | 17 | 2 | 9 | 1 | 24 | 367 | 0.192 |
| SeABank | **TinyFish agent** (run `45c8656d`, 188 s, 22 steps) | 16 | 16 | 1 | 0 | 0 | 16 | 188 | 0.352 |
| Sacombank | aggregator + bank PDF (2 sheets) | 16 | 11 | 2 | 11 | 5 | 0 | 0 | 0 |
| MSB | aggregator + D-UNLOCK agent run + 3 PDFs (scans, unusable) | 17 | 11 | 2 | 0 | 8 | 9 | 0 | 0 |
| VietBank | aggregator + bank PDF | 16 | 8 | 2 | 16 | 0 | 0 | 0 | 0 |
| PVcomBank | aggregator + 3 PDFs | 14 | 8 | 2 | 8 | 6 | 0 | 0 | 0 |
| OCB | aggregator + 2 PDFs | 12 | 8 | 2 | 7 | 5 | 0 | 0 | 0 |
| BIDV | aggregator + 2 PDFs (corporate sheet) | 15 | 8 | 2 | 4 | 9 | 2 | 0 | 0 |
| MB | aggregator + D-UNLOCK agent run (MB page is 403 to plain GET) | 15 | 8 | 2 | 3 | 7 | 5 | 0 | 0 |
| ACB | aggregator + D-UNLOCK agent run | 13 | 8 | 2 | 1 | 7 | 5 | 0 | 0 |
| Techcombank | aggregator + D-UNLOCK agent run | 16 | 8 | 2 | 0 | 10 | 6 | 0 | 0 |
| Agribank | aggregator (bank HTML has no rates) | 12 | 7 | 2 | 5 | 0 | 7 | 0 | 0 |
| ABBank | aggregator + 1 PDF | 16 | 8 | 2 | 0 | 0 | 16 | 0 | 0 |
| LPBank | aggregator | 16 | 8 | 2 | 0 | 0 | 16 | 0 | 0 |
| NamABank | aggregator | 16 | 8 | 2 | 0 | 0 | 16 | 0 | 0 |
| SHB | aggregator (online channel only) | 8 | 8 | 1 | 0 | 0 | 8 | 0 | 0 |
| VCBNeo | aggregator | 9 | 8 | 2 | 0 | 0 | 9 | 0 | 0 |
| VIB | aggregator | 15 | 8 | 2 | 0 | 0 | 15 | 0 | 0 |
| Vietcombank | aggregator | 11 | 8 | 2 | 0 | 0 | 11 | 0 | 0 |
| TPBank | aggregator | 10 | 7 | 2 | 0 | 0 | 10 | 0 | 0 |
| BacABank | aggregator (counter only) | 6 | 6 | 1 | 0 | 0 | 6 | 0 | 0 |
| Eximbank | aggregator + 3 PDFs | 6 | 6 | 1 | 0 | 5 | 1 | 0 | 0 |
| VietinBank | aggregator + D-UNLOCK agent run | 6 | 6 | 1 | 1 | 3 | 2 | 0 | 0 |
| VPBank | aggregator (4 terms only) | 4 | 4 | 1 | 0 | 0 | 4 | 0 | 0 |

**Totals: 24 banks, 319 rows, 23 banks with ≥6 terms, 65 verified (20 %), 66 contested (21 %), 188 agent_only (59 %).**
TinyFish spend in this task: **USD 0.608, 38 steps, 3 COMPLETED runs** (`http/tf_runs/`), of which SCB returned 0 rows.
Prior same-day runs (D-UNLOCK, V-CURVE) reused as a free second reader for MB, ACB, Techcombank, VietinBank, HDBank,
MSB, Sacombank — that is why those banks carry 2 agent reads.

## 3. What failed, with the exact response (negative claims)

| bank | exact evidence (20/11/2026) |
|---|---|
| SCB | agent run `65ca6f64` COMPLETED after **4 steps / 163 s → `rates: []`**; plain GET `https://www.scb.com.vn/lai-suat` in B-RATES: 3 KB shell |
| NCB | `https://www.ncb-bank.vn/robots.txt` → **HTTP 403 Cloudflare** ("Attention Required!"), python robotparser sets disallow_all ⇒ skipped; the agent run `e1002ca6` was still **RUNNING after 25 min** (no result) and was abandoned |
| KienlongBank | plain GET `https://kienlongbank.com/lai-suat-tiet-kiem` → **404**; TinyFetch → 189 chars, no table ("app only available in Vietnam"); agent run `b086a637` **RUNNING after 25 min**, abandoned |
| Saigonbank | plain GET → **403**; TinyFetch → `bot_blocked` |
| GPBank | `robots.txt` → **403 Incapsula** block page ⇒ conservative skip; nothing readable |
| OceanBank | TinyFetch → `proxy_error` |
| CBBank | `https://www.cbbank.vn/lai-suat` → **404** (`page_not_found` from TinyFetch) |
| BVBank | DNS `getaddrinfo failed` — the hostname in `banks.tsv` does not resolve |
| PGBank | plain GET 200 but **1,929 B** shell; TinyFetch 223 chars, 0 rate tokens |
| BaoVietBank | plain GET 200/48,931 B but **0 rate tokens**; TinyFetch 707 chars, 0 rate tokens |
| all 34 pages | **raw HTML is not a rate source**: `\d+[.,]\d+%` counts (ACB 480, TPBank 185, ABBank 147, Agribank 94) are CSS/SVG, not rates — V-CURVE proved this; only PDF text and the aggregator produced numbers |
| TinyFetch markdown | **0 usable tables**: 5 batches, HTTP 200, but `md_banks = []` — term-line parsing found nothing (nav/boilerplate only), matching V-CURVE's 14/22 nav-only result |

## 4. Grading rules used (so the 20 % is not overstated)

`verified` = a second, independent reader covers the same bank+channel+term with the same number (±0.005): aggregator vs
PDF term line, aggregator vs agent run, or two independent agent runs (same kind, different prompt/time — noted as the
weaker case). `pdf`/`tinyfetch` readers are **channel-unknown** (column identity not disambiguated), so they can confirm a
number at a term but not prove which channel it belongs to; those rows are marked `(channel unknown)` in `second_readers`.
`contested` = readers disagree — every one is a real cross-kind disagreement (e.g. Techcombank counter 1 m: aggregator 4.40
vs D-UNLOCK agent 4.15, +0.25 pp systematic, i.e. a different product tier). One systematic caveat: BIDV's only published
PDFs (`http/txt/BIDV_0.txt`, `BIDV_1.txt`) are titled **"LÃI SUẤT TIỀN GỬI DÀNH CHO KHÁCH HÀNG DOANH NGHIỆP"**, so its 9
`contested` rows are household-vs-corporate conflicts, evidence that the sheet is the wrong product, not that the rate is wrong. `agent_only` = single reader, do not publish
without a second read. `effective_date` comes from the PDF header ("Áp dụng … từ ngày 06/11/2026" → OCB 2026-11-06) or the
agent-read page date, else the aggregator stamp **20.11.2026** (`effective_date_source` column says which).

## 5. Daily-run estimate for the full 30-bank set

| step | wall clock | USD | note |
|---|---|---|---|
| aggregator table (1 GET) | 3 s | 0 | 22 banks, 245 rows, 8 terms × 2 channels, server-rendered, refresh stamp on page |
| 34 bank pages + 18 PDFs + 5 TinyFetch batches | ~7 min | 0 | yields PDF text for only 6 banks and **no** TinyFetch table |
| TinyFish agent for the rest | ~4 min/bank measured (188–367 s COMPLETED), 2 concurrent ⇒ **24 min for 12 banks** | **USD 0.20/bank** (0.192–0.352) ⇒ USD 2.4 / 12 banks | **1 in 3 runs hangs** (2 of 5 today never finished, `max_duration_seconds 120` is a soft cap) |
| **one full run** | **≈ 30–35 min** (bounded by the agent queue, not by fetch) | **≈ USD 2.5–3.0** | needs a cancel-on-timeout policy and a re-launch of hung runs |

Stable to plain fetch: **none of the 33** rate pages gives a rate table in raw HTML — only PDFs are (Sacombank, VietBank,
OCB, Eximbank, BIDV, PVcomBank) and they drift in layout and tier structure. Stable to *free* means only the aggregator
(22 banks, 1 request). The product therefore depends on two things: the aggregator for breadth, and one independent
non-aggregator reader per bank for trust — and the cheapest independent reader today is a PDF (6 banks) or an agent run
(USD 0.20, 4 min). **Verdict: full coverage of ~30 banks is possible at ~USD 3/run and ~35 min, but not for the 10 banks
whose sites block or do not publish a rate page** (SCB, NCB, KienlongBank, Saigonbank, GPBank, OceanBank, CBBank, BVBank,
PGBank, BaoVietBank) — those need a different route (branch posters, press tables, licensed data vendor).

## 6. Rules compliance

robots.txt read for every host before the first request (`http/free_probe.csv` records HTTP status per bank page;
`http/robots_*.txt` kept for the three contested ones); ≥2.2 s between requests to the same host; no captcha/login bypass —
NCB and GPBank were **dropped** because their robots.txt answered 403; no secret printed (`TINYFISH_API_KEY` read from env);
no repo edits; no dependency installed. Every rate in `samples\rates_all_banks.csv` carries `grade`, `primary_reader`,
`second_readers`, `effective_date_source`, `access_time` (Asia/Saigon).
