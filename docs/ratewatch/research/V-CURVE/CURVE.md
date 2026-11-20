# V-CURVE — the deposit curve read from bank pages themselves: the 4.75 % kink is real, most banks do not sit on it, and the curve implies rising rates

Built 20/11/2026 ~12:00–13:05 Asia/Saigon in this folder (script `build_curve.py`, log `analysis.out`). No repo file
edited, no git write, no dependency installed into the repo `.venv` (used read-only), no process killed.
Files: `samples\curve_today.csv` (110 rate rows, 8 banks), raw evidence `http\pages\*.html` (34 pages tried),
`http\fetch\*.md` (22 bank pages rendered by TinyFetch), `http\pdf\*.pdf|.txt` (7 PDFs), `http\probe_html.csv`,
`http\tf_run_*.json`, `tinyfish_runs.json`.

## 1. What was actually read from a bank, not an aggregator

Method, cheapest first, every number traceable to a saved artefact:

1. **Plain GET of the 34 bank rate URLs** (`probe_html.py`, robots.txt read per host first, ≥2.2 s per host):
   only `http/probe_html.csv` shows what came back. **No rate survived this path**: the raw HTML of BIDV, Agribank,
   LPBank, Eximbank contains the markup but the numbers are injected client-side, and the `%` matches that do exist
   are CSS gradients (`0.85%`, `98.94%` in BIDV's chat widget) and SVG path data. Counting `d.d%` in HTML is a trap —
   that is how B-RATES "found" 106/94 rate cells in BIDV/Agribank; they are styles, not rates.
2. **TinyFetch (free, renders JS) on the 22 URLs the banks' own rate pages are linked from** (`banks.tsv`):
   8 banks gave a readable rate table or a PDF link; 14 gave navigation/boilerplate only.
3. **The bank's own PDF rate sheet** where the page only publishes a file (Sacombank, Eximbank, OCB, VietBank, MSB, BIDV):
   downloaded and text-extracted with pdfplumber → `http/pdf/*.txt`. MSB's PDF is a scan (5 chars of text) — unusable.
4. **TinyFish agent runs, 2 (budget spent ≈ USD 0.30 of 8)**: `71c715fe…` MSB 13 steps COMPLETED,
   `50cd817e…` Sacombank 6 steps COMPLETED (`http/tf_run_*.json`, run ids in `tinyfish_runs.json`).

| bank | channel | terms read | 1m | 3m | 5m | 6m | 9m | 12m | 18m | 24m | 36m | readers | grade |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sacombank | counter, <500 tr | 11 | 4.50 | 4.50 | 4.50 | 5.70 | 5.70 | 5.40 | 5.50 | 6.20 | 6.20 | PDF + TinyFish | **verified** |
| OCB | online | 11 | 4.75 | 4.75 | 4.75 | 6.00 | 6.00 | 6.30 | 6.00 | 6.00 | 6.00 | table + PDF | **verified** |
| OCB | counter | 11 | 4.75 | 4.75 | 4.75 | 5.90 | 5.90 | 6.20 | 5.90 | 5.90 | 5.90 | table (PDF conflicts) | agent_only |
| VCBNeo | counter (max, KHCN) | 11 | 4.65 | 4.75 | 4.75 | 5.90 | 5.90 | 6.30 | 6.30 | 6.30 | 6.30 | table | agent_only |
| MSB | online (agent-read) | 11 | 4.75 | 4.75 | 4.75 | 5.80 | 5.80 | 6.30 | 6.10 | 6.10 | 5.60 | TinyFish | agent_only |
| VietBank | counter | 11 | 4.50 | 4.50 | 4.50 | 5.30 | 5.40 | 5.50 | 5.80 | 5.80 | 5.80 | PDF | agent_only |
| ACB | counter (LCK) | 11 | 4.00 | 4.00 | 4.00 | 4.00 | 4.20 | 4.80 | 4.90 | 4.90 | 4.90 | table | agent_only |
| Eximbank | counter (end of term) | 11 | 3.50 | 3.60 | 3.60 | 4.20 | 4.20 | 4.50 | 5.00 | 5.00 | 5.00 | PDF | agent_only |
| VietinBank | counter | 11 | 2.10 | 2.40 | 2.40 | 3.00 | 3.00 | 5.40 | 5.40 | 5.50 | 5.50 | table | agent_only |
| Sacombank | counter, ≥2 tỷ | 11 | 4.75 | 4.75 | 4.75 | 5.90 | 5.90 | 5.60 | 5.70 | 6.40 | 6.40 | PDF | agent_only |

`page_effective_date` is the date **printed on the sheet**: Sacombank 20/10/2026, OCB 06/11/2026, VCBNeo 19/10/2026,
VietBank 19/10/2026, Eximbank 31/10/2026, MSB none found. VietinBank, ACB, MSB publish no date on the page → left blank,
never guessed. `read_at` is the fetch clock (machine clock, cross-checked against TinyFish's UTC stamps: 05:40Z = 12:40 +07).

**Grade split: 22 rows verified (2 bank-channels), 88 rows agent_only (8 bank-channels).** That ratio is the honest
headline: one direct read per bank is cheap, the *second* independent reader is what costs, exactly as B-RATES found.
The four big-4 banks are the weakest: VietinBank's table is clean but single-read, and **BIDV/Agribank/Vietcombank were
not read at all** — BIDV's only offered PDF is `LÃI SUẤT TIỀN GỬI DÀNH CHO KHÁCH HÀNG DOANH NGHIỆP` (16/12/2025),
i.e. the wrong product (a corporate sheet, not household), its second PDF link 404s as HTML; Agribank and Vietcombank
render their rates client-side and publish no PDF (`n_pdf=0` in `http/probe_html.csv`). Quoting them would mean
inventing numbers, so they are absent.

Banks probed and **not** obtained, with the exact reason: MB 403, SHB 403, Saigonbank 403, HDBank 404,
KienlongBank 404 (its TinyFetch text is "our app is currently only available for users located in Vietnam"),
CBBank 404, TPBank TLS `UNEXPECTED_EOF`, PGBank timeout, robots.txt read failed → skipped for PVcomBank, SeABank, NCB,
BVBank, GPBank, OceanBank (their `/lai-suat` pages never touched).

## 2. The 4.75 % ceiling: half of all short-term quotes sit exactly on it, and nothing sits above

QĐ 2411/QĐ-NHNN caps 1 to <6 months at 4.75 %/year (B-POLICY). Direct reads, terms 1–5 months, counter + online,
45 quotes from 9 bank-channels:

| 1–5 m rate | quotes | bank-channels |
|---|---|---|
| **4.75 %** | **19 (42 %)** | OCB counter, OCB online, VCBNeo (2–5 m), MSB online, Sacombank counter ≥2 tỷ |
| 4.50–4.65 % | 11 | Sacombank <500 tr, VietBank (4.50), VCBNeo 1 m (4.65) |
| 4.00 % | 5 | ACB (all five terms) |
| 3.50–3.60 % | 5 | Eximbank |
| 2.10–2.40 % | 5 | VietinBank (demand-like, the state banks' posted floor) |
| **> 4.75 %** | **0** | — |

**OCB both channels and MSB online post 4.75 % for every single term from 1 to 5 months; VCBNeo joins them from 2 m and
Sacombank's ≥2 tỷ tier is 4.75 flat too (that tier is excluded from the 45 quotes above)** — money left on the table for a household that only wants 1–3 months. **Zero quotes above 4.75 %: the ceiling binds, and
the binding point is exactly where banks that can pay more stop differentiating.** The market splits into two clear
regimes: on-the-cap (4.75 flat) and far below it (ACB 4.00, VietinBank 2.10–2.40, Eximbank 3.50–3.60), with almost
nothing in between — a two-tier short-term market, not a continuum.

**The kink.** Jump from 5 to 6 months (the first term released from the cap):

| bank / channel | 5 m | 6 m | jump |
|---|---|---|---|
| OCB online | 4.75 | 6.00 | **+1.25** |
| Sacombank <500 tr | 4.50 | 5.70 | +1.20 |
| VCBNeo | 4.75 | 5.90 | +1.15 |
| OCB counter | 4.75 | 5.90 | +1.15 |
| Sacombank ≥2 tỷ | 4.75 | 5.90 | +1.15 |
| MSB online | 4.75 | 5.80 | +1.05 |
| VietBank | 4.50 | 5.30 | +0.80 |
| Eximbank | 3.60 | 4.20 | +0.60 |
| VietinBank | 2.40 | 3.00 | +0.60 |
| ACB | 4.00 | 4.00 | 0.00 |

Median jump **+1.15 pp** (mean 0.90) in one month of extra term; the cap itself is 4.75, so on-the-cap banks pay
**1.15–1.25 pp more for a 30-day-longer commitment**. ACB is the exception (flat 4.00 through 6 m — no kink at all),
which is why "the ceiling bends every curve" must be shown per bank, not as a market fact.

## 3. Implied forwards — the curve says the second half of 2027 pays more than the first

Convention: Vietnamese sheets print **simple interest, `P × r × days/365`, interest at end of term** (BIDV's own note:
"lãi được tính trên số ngày thực tế … cơ sở tính lãi là 365 ngày"; VCBNeo prints end-of-term vs monthly payout columns).
So the consistent forward is the simple-interest one, `f = 2[(1+r12)/(1+r6/2) − 1]`; the brief's annual-compounding
formula is reported too for comparison and gives ~+0.15 pp higher answers.

| bank / channel | r6 | r12 | implied 6 m rate, 6 m ahead (simple) | 12 m→24 m forward (simple) |
|---|---|---|---|---|
| VietinBank counter | 3.00 | 5.40 | **7.68 %** | 5.31 % |
| VCBNeo | 5.90 | 6.30 | 6.51 % | 5.93 % |
| OCB online | 6.00 | 6.30 | 6.41 % | 5.36 % |
| OCB counter | 5.90 | 6.20 | 6.31 % | 5.27 % |
| VietBank | 5.30 | 5.50 | 5.55 % | 5.78 % |
| ACB | 4.00 | 4.80 | 5.49 % | 4.77 % |
| Sacombank ≥2 tỷ | 5.90 | 5.60 | 5.15 % | 6.82 % |
| Sacombank <500 tr | 5.70 | 5.40 | 4.96 % | 6.64 % |
| Eximbank | 4.20 | 4.50 | 4.70 % | 5.26 % |
| **median (n=9)** | | | **5.55 %** (brief formula 5.70 %) | **5.36 %** (brief formula 5.70 %) |

Reads for the product: the **median implied 6 m rate 6 months out is 5.55 % vs a median 6 m rate today of 5.70 %** —
for the median bank, rolling 6+6 beats locking 12 m only *if* the second half clears 5.55 %, i.e. the market is
pricing the next six months **above** today's 6 m rate at 7 of 9 banks (6 m sits below r12 almost everywhere).
Sacombank is the opposite and is the one bank where locking 12 m is clearly wrong: its 12 m (5.40) is *below* its own
9 m (5.70), so a 6+6 roll at 5.70 and 4.96 beats 5.40 today. VietinBank's 7.68 % forward is an artefact of the
2.10 → 5.40 step (its 1–11 m rates are demand-like), not a market view: **do not quote VietinBank's forward**.

## 4. A rerunnable collector: 2 paths, ~9 min and ~USD 0.30 per daily run

| path | banks | how | cost/run | failure modes |
|---|---|---|---|---|
| **A. plain fetch + PDF** (do this first) | Sacombank, Eximbank, VietBank, OCB, MSB(PDF is a scan → skip), BIDV(corporate only) | GET page (robots.txt first, 2.2 s), extract `href=*.pdf`, pdfplumber text, regex `(\\d+)\\s*tháng…(\\d[.,]\\d+)` | **free**, ~3 min | PDF layout drift; tier tables (Sacombank 3 money bands, OCB 4) — pick the band explicitly; scans (MSB) need OCR |
| **B. TinyFetch markdown** | VietinBank, ACB, VCBNeo, OCB (summary table) | POST api.fetch.tinyfish.ai, 8 URLs/request, markdown tables parse cleanly | **free**, ~2 min for 22 URLs | nav-only text (14/22 today); markdown flattens merged cells → ACB's column mapping is ambiguous; no rate when the table is a PDF |
| **C. TinyFish agent** (only for C-rendered pages with no PDF) | MB, SHB, HDBank, KienlongBank, SeABank, NCB, TPBank; big-4 if no PDF | run-async + poll, `output_schema` {bank, page_effective_date, channel, rates[{term_months, rate_pct}]}, `browser_profile: lite`, 240 s | **USD 0.016/step**: today 13 steps = **USD 0.21** (MSB), 6 steps = **USD 0.10** (Sacombank); 2 concurrent ⇒ ~2–4 min wall clock | agent reads the *default* channel (MSB came back "Trực tuyến (Online)" although asked for counter) → must read both tabs or pin the tab in the goal; steps and cost only known after the run; USD 8 budget ⇒ ~25–30 bank-runs/day |

**Daily run to cover ~30 banks: ~USD 0.30–0.50 and 8–10 minutes** if path A+B cover 12–15 banks and C covers the rest.
The second reader should be *deliberately different in kind* (PDF vs rendered table vs agent), never two passes of the
same parser: today the only two conflicts found (OCB counter 5.90 vs PDF 5.73 at 6 m; MSB channel mismatch) were
cross-kind disagreements. Validation rule for the collector: a rate that breaks monotonicity without a documented
reason, or that differs between kinds, is published as `contested`, not silently averaged.

## 5. Product implications (test, do not defend)

- The **kink chart is genuinely differentiating**: on-the-cap banks pay +1.15 pp for a 1-month-longer term, and
  4 bank-channels are at 4.75 % for 1–5 m. This is a real, checkable household decision ("wait 30 days, gain 1.15 pp").
- The **"lock 12 or roll 6+6" answer must be per bank, not market-wide**: implied forwards span 4.70–6.51 % (excluding
  VietinBank's artefact), and Sacombank inverts (12 m < 9 m).
- **Coverage is the binding constraint, not method**: 8 of ~30 banks are read here in ~60 minutes, and only 2 have two
  readers. A daily product needs the collector in §4 running on a schedule, plus OCR for scanned sheets.
- **The insured cap (350 m, Thông tư 05/2026) interacts with the tiers we saw**: Sacombank pays 4.75 % only from
  2 tỷ (uninsured), 4.50 % below 500 tr (insured) — i.e. the extra 0.25 pp is bought partly by crossing the insurance
  cap. Worth a computed "insured yield vs uninsured yield" toggle; not done here.
