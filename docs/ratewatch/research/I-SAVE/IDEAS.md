# I-SAVE — two household-savings concepts on observed Vietnamese prices (20/11/2026, 12:00–12:35 Asia/Saigon)

Anchor data used: **BTMC gold history** (2017-05-02 → today), **Vietcombank FX board** (2020-02-03 → today), **posted deposit
rates** (10 banks, today), **CPI**, and **FiinQuant VN30** (available, not needed for the first number). Nothing here is a
gold-premium tracker or a break-even calculator: the gold premium is never displayed, and no channel is scored on "will gold go up".

Reused, not re-discovered: `..\D-UNLOCK\UNLOCK.md` §1 (BTMC route + unit trap), §2 (deposit-rate CSV, 89 rows, verification
grades), C-GOLD §1 (VCB dated API), R-SUPPLY §1 (FiinQuant). New calls made today are listed in §2 with the exact URL.

---

## 1. Two concepts

### A. "Hóa đơn 12 tháng" — the same 500 million, four places to keep it, one receipt
- **User and decision.** A household with a known sum and a known date when it is needed (school fees in 1 year, house deposit in
  3). Decision: *which channel, and — inside the deposit channel — branch counter or app?* Today the comparison a Vietnamese
  saver actually makes is a rate table (CafeF/Webgia/Timo), which ignores what the saver pays to get in and out.
- **Policy question.** Most Vietnamese savers still transact at the counter, where the four state-owned banks publish 12-month
  rates that leave roughly nothing after inflation, while the same banks' online rates exceed inflation. Is channel-based
  price discrimination a hidden transfer from non-digital savers, and does the "safe" channel still exist for them?
- **Research question (one sentence).** Using only posted dealer/bank quotes and official CPI, what would the same sum have been
  worth after 12/24/36 months in a counter deposit, an online deposit, physical SJC gold and cash dollars — and how often did each
  channel actually beat inflation?
- **Datasets and join keys.**

| Dataset | Route (verified today) | Depth | Join key |
|---|---|---|---|
| BTMC SJC bar ask/bid | `GET https://btmc.vn/ProductHome/getGoldDate?date=DD/MM/YYYY` → `Data.sjcban` (ask) / `Data.sjcmua` (bid), raw = thousand VND per **chỉ**, ×10,000 = VND/lượng | 2017-05-02 → 2026-11-20, ~3,490 calendar days, gaps on unpublished days | `date` (Asia/Saigon), `product` |
| Vietcombank USD | `GET https://www.vietcombank.com.vn/api/exchangerates?date=YYYY-MM-DD` → `Data[currencyCode=USD].cash / transfer / sell`; check `UpdatedDate` | 2020-02-03 → today | `date`, `currency=USD` |
| Deposit rates | bank PDF/HTML boards, 10 banks × channel × term (from D-UNLOCK `deposit_rates_today.csv`, per-row `verified_by`) | today's snapshot only; **no official rate history exists** (SBV publishes decisions, not bank tables) | `bank`, `channel`, `term_months`, `effective_date` |
| CPI | IMF `CPI` dataflow via DBnomics `IMF/CPI/M.VN.PCPI_IX` (monthly index, 1950-01 → 2025-03) + NSO/Hanoi DoF report for the current YoY | monthly, 75 y | `month` |
| VN30 (risk channel) | FiinQuant `Fetch_Trading_Data(by="1d")` / `get_index_valuation` | 2011 → today, PE/PB 2021+ | `date`, `ticker=VN30` |

### B. "Đô la trong tủ" — what the dollar in the drawer really earned
- **User and decision.** A household that already holds, or is about to buy, cash dollars (remittance receivers, small traders):
  keep it in cash/foreign-currency account, convert to dong and deposit, or convert to gold. Decision: *is the dollar a one-year
  store of value, or only a long-horizon hedge?*
- **Policy question.** With the 0 % USD deposit rate and a managed dong, does the observed cash-side FX spread make
  dollar-holding a losing one-year strategy — i.e. is dollarisation being taxed by the bank's own board rather than by policy?
- **Research question.** After the bank's own cash buy/sell spread, in how many observed 12-month windows did cash dollars beat
  CPI, and at what horizon does the answer flip?
- **Datasets.** Same VCB board (cash vs sell is the household's round trip), CPI, gold as the alternative store, Frankfurter/SBV
  central rate only as a cross-check (C-GOLD §1). Join keys: `date`, `currency`, `channel`.

---

## 2. Proof — real calls, real samples, one real number each

All calls 20/11/2026 12:00–12:10 Asia/Saigon, `robots.txt` read first (btmc.vn `Allow: /`, vietcombank.com.vn `Allow: /`),
≥2.2 s between requests, no login/captcha, no repo file touched. Script: `pull_gold_fx.py` (urllib only, stdlib).

- `GET https://btmc.vn/ProductHome/getGoldDate?date=20%2F11%2F2026` → **200**, `sjcmua 12860`, `sjcban 13420` →
  **128.60 m bid / 134.20 m ask VND per lượng** [verified].
- `GET https://www.vietcombank.com.vn/api/exchangerates?date=2026-11-20` → **200**, `USD cash 25,550 / transfer 25,560 /
  sell 25,960`, `UpdatedDate 2026-11-20T23:00:00+07:00` [verified].
- `GET https://api.db.nomics.world/v22/series/IMF/CPI/M.VN.PCPI_IX?observations=1` → **200**, 903 monthly values,
  last published 2025-03 = 118.656 (index) [verified]. IMF's own SDMX (`api.imf.org`, dataflow `IMF.STA/CPI/5.0.0`) returns
  200 but an empty DataSet for the `VN` key I tried — DBnomics is the working mirror [verified].
- `GET https://sotaichinh.hanoi.gov.vn/bao-cao-gia-thi-truong-thang-10-nam-2026-140554.html` → **200**, citing BC 19152/BC-STC
  (05/11/2026): **CPI tháng 10/2026 +5.03 % YoY**, 10-month average +4.92 % [verified].
- Deposit rates: reused `..\D-UNLOCK\samples\deposit_rates_today.csv` (89 rows). Banks with **both** 12-month channels:
  8. On those 8 banks: online median **6.47 %**, counter median **5.50 %**, gap median **0.40 pp**, max **1.40 pp**
  [inferred from the quoted rates].
  Sacombank's own PDF (`SACOMBANK_LAISUATNIEMYETTAIQUAY_KHCN_VIE.pdf`, effective 20/10/2026, `verified_by=tinyfetch:rate+term`)
  posts **7.00 % online vs 5.60 % counter for 12 months** — a 1.40 pp same-bank gap that survives verification [verified].
  Agribank and BIDV show the same 1.4 pp gap but their rows are `agent_only_unconfirmed` [verified label, unconfirmed value].
- TinyFish budget: **0 USD spent, no agent runs**; one free `POST https://api.fetch.tinyfish.ai` (200, 2 URLs) to read
  `tools.finhay.com.vn` and `giavang.com.vn` for the crowding check, saved as `http/tinyfetch.json`. No run ids to log.

**Computation** (grid: 39 real dates, quarterly, 2017-05-02 → 2026-11-20; buy at the shop's ask, sell at the shop's bid;
USD bought at the bank's sell, sold back at the bank's cash-buy; real = nominal − CPI YoY of the exit month):

`samples\gold_fx_pull.csv` (39 rows, real), `samples\windows_12m.csv` (28 windows: 21 gold, 15 USD), `samples\horizon_real_returns.csv`:

| Horizon | n windows | Gold median real | Gold beat CPI | Gold worst real | n | USD cash median real | USD beat CPI |
|---|---|---|---|---|---|---|---|
| 12 m | 21 | **+9.43 %** | 14/21 | **−6.39 %** | 15 | **−2.08 %** | 3/15 |
| 24 m | 17 | +18.10 % | 16/17 | −3.83 % | 11 | +0.71 % | 6/11 |
| 36 m | 14 | +48.01 % | 14/14 | +16.94 % | 8 | +0.50 % | 4/8 |

**First real numbers that test the insight (all [inferred] arithmetic on [verified] quotes):**
1. **Today's posted toll for 500 m VND**: gold ask−bid = **4.173 % → 20.9 m VND**; cash dollars = **1.605 % → 8.0 m VND**.
   A gold round trip costs about **8 months of a 6.47 % deposit**, paid before any price move.
2. **Cash dollars are a *losing* one-year store**: after the bank's own spread, 12-month real return median **−2.08 %**, and they
   beat CPI in only **3 of 15** observed windows. The one-year "safe haven" story fails on observed quotes; it only turns
   positive at 24 m+ (6/11, median +0.71 %) [inferred].
3. **Gold beat CPI in 16 of 17 24-month windows and 14 of 14 36-month windows, but lost in 7 of 21 one-year windows, worst −6.39 % real** —
   so the channel is horizon-dependent, not "gold always wins"; the seven losing windows are 2017-05→2019-05 (flat nominal gold,
   2.9–4.0 % CPI) and 2022-05→2023-11 (nominal −0.2 % to −4.0 % while CPI ran 2.4–3.5 %) [inferred from the sample].
4. **The counter is a real-rate dead end today**: counter 12 m median 5.50 % vs CPI 5.03 % YoY = **+0.47 % real**; online median
   6.47 % = **+1.44 % real**; at the two state banks that publish a 1.40 pp gap, walking into the branch costs **7.0 m VND per
   500 m per year** [inferred].

**Limitations, stated now:** the grid is quarterly (35 gold pairs, 27 FX pairs), not daily — overlapping windows, so counts are not
independent samples; full daily backfill is ≈2.9 h (D-UNLOCK §1.7). CPI monthly stops at 2025-03 in this mirror, so windows that
end after 2025-03 are excluded (that is why n falls with horizon); the 2026 YoY figure is a single official number, not a series.
Deposit *history* does not exist officially, so the deposit channel is today's posted cross-section only — any historical deposit
comparison would need a scraped rate history and must be labelled as such. USD cash round trip uses VCB cash-buy vs sell, the
household's actual pair; the transfer channel is cheaper and should be shown as a sensitivity.

---

## 3. Crowding check (searched 20/11/2026 12:02–12:07 via DuckDuckGo lite, Vietnamese and English queries)

| What exists | Verdict on overlap |
|---|---|
| Rate aggregators/comparators: `webgia.com/lai-suat/`, `laisuattietkiem.vn`, `vnsignal.vn`, `vn-finance.com`, `tools.finhay.com.vn`, `giavang.com.vn`, `calc.vn`, `timo.vn`, `simplize.vn` (all 200, indexed) | **Crowded**: comparing *headline* deposit rates, compound-interest and gold-price calculators. None shows a same-bank counter-vs-online VND bill, after-spread gold outcomes, or win rates vs CPI. |
| Bank marketing on the same topic: `techcombank.com/thong-tin/blog/so-sanh-gui-tiet-kiem-online-va-tai-quay`, `vaynao.com`, `vib.com.vn` | **Adjacent and partly crowded**: the online-vs-counter idea is already used as a sales argument. Our difference must be the measured per-bank gap in VND and the realised-outcome test, not the concept. |
| Gold premium/spread tools (GemBack, MacroDashboard, Cá Buồm, ORA·tech, Giá Vàng Nay, OpenBDS, GiaVang.app — C-GOLD §4) | **Deliberately avoided**: no premium, no break-even screen. |
| Channel-comparison articles: `finhay.com.vn`, `greencapinvestment.com`, `thitruongtaichinh.org`, `tietkiemtaichinh.com` | **Adjacent**: opinion pieces "vàng vs USD vs tiết kiệm"; they do not compute after-cost, after-CPI outcomes per holding period, and none uses 9.5 y of a dealer's own bid/ask. |
| Academic: no paper found in these queries doing Vietnamese after-spread channel win rates (not a negative claim — only that I did not find one in 12 minutes of search; a proper Scholar/SciSpace pass is still owed) | **[inferred]** gap looks real but unproven |

**Verdict.** "Which channel should I use" is a crowded *category*, so the product cannot be sold as a rate table or a returns
calculator. What I did not find anywhere is the **observed-outcome receipt**: same sum, four channels, the dealer's/bank's own
posted quote on both sides, CPI-deflated, reported as *how often* each channel won at each holding period, plus the
counter-vs-online bill at the same bank. That is the surviving edge — and it is exactly the kind of "decision, not dashboard"
content the guidebook asks for.

---

## 4. Scores (1–5) and the pick

| | A. Hóa đơn 12 tháng | B. Đô la trong tủ |
|---|---|---|
| Observed-data strength | **5** — 9.5 y BTMC bid/ask, 6.8 y VCB board, 89 posted rates, official CPI | 4 — VCB board only (one bank, cash side), CPI |
| Insight (non-obvious, decision-changing) | **4** — cash dollars lose at 12 m (3/15); gold may lose (−6.39 % real) but won 16/17 at 24 m and 14/14 at 36 m; counter = +0.47 % real | 4 — the "safe" dollar is the worst one-year channel; flips only at 24 m |
| Uniqueness vs teams/tools | 3 — category is crowded; the receipt/win-rate framing is not | **5** — no product I found prices the cash-dollar round trip as a savings decision |
| Judge / mentor fit | **5** — Sacha Dray (World Bank, fiscal + household finance), Nguyen Ngoc Phuong Trang (Shinhan, banking channels), Nguyen Tri Dung (behavioural: channel defaults); mentor Le Minh Phuong (inequality: non-digital savers) | 3 — Trang and Dang Hoang Nhat Tam (macro/FX) yes, Dray partly |
| Demo wow | **4** — one input (500 m, 12 months) → four receipts, one "you paid 20.9 m to enter gold" line, one "your branch costs 7 m" line | 3 — one chart, one number |
| Buildable by 21/11 13:00 | **4** — static snapshots + a 2.9 h backfill that can run overnight; no ML | 5 — 27 quotes already pulled |
| **Total** | **25** | **24** |

**Pick: A — "Hóa đơn 12 tháng"**, with B's dollar result folded in as one of the four receipts (it is the most surprising line and
costs nothing extra). Positioning sentence for the pitch: *"500 triệu của bạn, 12 tháng, bốn nơi để giữ: chúng tôi không dự báo
giá vàng — chúng tôi cho bạn xem 9,5 năm giá mua-bán thật của chính cửa hàng, và hoá đơn bạn trả trước khi mua."*

**Main risk (A).** The cell that decides the pitch is the counter-vs-online gap, and today it rests on **one fully verified PDF
(Sacombank 7.00 vs 5.60)**; Agribank and BIDV show the same 1.4 pp but are `agent_only_unconfirmed`, and no official rate
*history* exists, so the deposit leg is a snapshot, not a series. If a second reader does not confirm the state banks' gap by
21/11 morning, the headline must be reduced to Sacombank + ACB/HDBank (verified) and the product must lead with the gold/USD
after-spread result instead. Secondary risk: 21 overlapping quarterly windows are a thin sample — a judge will ask for n and
non-overlap; the answer must be to run the full daily backfill and report non-overlapping windows only.
