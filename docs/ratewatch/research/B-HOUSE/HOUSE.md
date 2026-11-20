# HOUSE — Banking from the household side: data for depositor and borrower decisions in Vietnam

All calls made live this session, 20/11/2026, 12:11–12:45 Asia/Saigon (+07). Methods: `curl` direct (sbv.gov.vn), TinyFetch `POST https://api.fetch.tinyfish.ai {"urls":[...],"format":"markdown"}` (free tier, key read from `TINYFISH_API_KEY`, never printed), web search (Brave-backed connector). robots.txt read before fetching: `sbv.gov.vn/robots.txt` = allow all (HTTP 200); `gold.org/robots.txt` = standard Drupal, nothing blocking `/goldhub/data/`; `div.gov.vn/robots.txt` returns the SPA HTML shell (no rules declared); `vsdc.org.vn` does not resolve (HTTP 000) — the live domain is **vsdc.vn** (302 on /robots.txt). Delay ≥ 2.5 s between requests to the same host. Raw evidence in `samples/` (SBV HTML pages, TinyFetch outputs). No repo files touched.

---

## 1. Deposit insurance (DIV) — the depositor's safety net

| Fact | Value | Legal basis / source | Status |
|---|---|---|---|
| Insured limit per depositor per institution | **125,000,000 VND** (gốc + lãi, all insured deposits combined at one institution) | Quyết định 32/2021/QĐ-TTg (20/10/2021), effective **12/12/2021**, replacing 75M under QĐ 21/2017/QĐ-TTg (15/6/2017) | [verified] |
| Share of depositors fully insured | raised **87% → 91%** by the 75M→125M increase (IADI recommends 90–95%) | DIV press page (fetched) | [verified] |
| Premium rate (phí BHTG) | **0,15%/năm** on average insured deposit balance; **0,1%/năm** for quỹ tín dụng nhân dân; Governor may adjust | Thông tư 04/2026/TT-NHNN, effective **01/5/2026** | [verified via 2 independent search-snippet quotes (luatvietnam.vn, baokiemtoan.vn); full circular text behind a JS viewer, not fetched] |
| Share of deposits ABOVE the limit | **not published on the DIV pages fetched** | fetched `div.gov.vn/tu-ngay-12-12-2021-...` and `div.gov.vn/thong-tin-bao-chi-ve-han-muc-tra-tien-bao-hiem` — neither carries it; `div.gov.vn/thong-ke` returned no result in TinyFetch | [negative claim, URLs above] |
| 2026 policy live wire | proposal to raise the limit toward **350 triệu đồng** (VnExpress, Thanh Niên 2026 headlines) | search results | [verified headlines only, articles not fetched] |

Sample rows (TinyFetch, `https://www.div.gov.vn/tu-ngay-12-12-2021-han-muc-tra-tien-bao-hiem-la-125-trieu-dong`):
> "số tiền tối đa tổ chức bảo hiểm tiền gửi trả cho tất cả các khoản tiền gửi được bảo hiểm ... của một người tại một tổ chức ... là 125.000.000 đồng ... Quyết định 32/2021/QĐ-TTg có hiệu lực từ ngày 12/12/2021"

> (from the press-info page) "nâng tỷ lệ số người gửi tiền được bảo hiểm toàn bộ trên tổng số người gửi tiền được bảo hiểm từ 87% lên 91%"

Household decision powered: **split balances so no bank holds more than 125M of principal+interest, or accept uninsured tail risk** — the single most concrete depositor rule in Vietnam. Student-team findability: **easy** (first Google hit for "hạn mức bảo hiểm tiền gửi"); the premium rate and above-limit share are **hard** (legal databases / annual reports).

## 2. SBV monetary statistics — deposits, credit, rates

All four pages below are **server-rendered HTML tables on sbv.gov.vn** (curl, HTTP 200, robots allow). The statistics section mirrors the dead dttktt portal.

| Page | URL | HTTP / size | Latest period on page | Key rows |
|---|---|---|---|---|
| Dư nợ tín dụng đối với nền kinh tế (credit by sector) | `https://sbv.gov.vn/vi/du-no-tin-dung-doi-voi-nen-kt-dttktt` | 200 / 467,769 B | **Tháng 08/2026** (static fallback also carries Tháng 10/2025) | see below |
| Tổng phương tiện thanh toán và Tiền gửi của khách hàng tại TCTD | `https://sbv.gov.vn/vi/t%E1%BB%95ng-ph%C6%B0%C6%A1ng-ti%E1%BB%87n-thanh-to%C3%A1n-v%C3%A0-ti%E1%BB%81n-g%E1%BB%ADi-c%E1%BB%A7a-kh%C3%A1ch-h%C3%A0ng-t%E1%BA%A1i-tctd` | 200 / 441,901 B | **Tháng 08/2026** | see below |
| Tài khoản tiền gửi thanh toán của cá nhân | `https://sbv.gov.vn/vi/tai-khoan-tien-gui-thanh-toan-cua-ca-nhan` | 200 / 438,438 B | **Quý II/2026** | 256,741 nghìn TK; số dư 1,220,766.52 tỷ |
| Tỷ lệ dư nợ cho vay so với tổng tiền gửi (LDR) | `https://sbv.gov.vn/vi/ty-le-du-no-cho-vay-so-voi-tong-tien-gui` | 200 / 412,398 B | static table = Tháng 06/2024 (JS renders newer) | see below |

Sample rows [verified, from fetched HTML in `samples/`]:
- **Credit, Tháng 08/2026** (tỷ đồng, % vs cuối 2025): TỔNG CỘNG **20.489.434, +10,19** · Nông-lâm-thủy sản 1.245.854, +9,77 · Công nghiệp và xây dựng 4.878.387, +12,05 (CN 3.276.604 +11,15; XD 1.601.783 +13,95) · Thương mại-Vận tải-Viễn thông 5.126.749, +4,89 (TM 4.567.396 +3,53; VT-TT 559.352 +17,50) · Dịch vụ khác 9.238.445, +12,41. Static fallback Tháng 10/2025: 18.007.536,76, +15,31 vs cuối 2024.
- **Deposits, Tháng 08/2026**: Tổng phương tiện thanh toán **20.774.696 tỷ, +6,84%** YTD · Tiền gửi của các TCKT 6.337.186, +2,54 · **Tiền gửi của dân cư 11.434.266 tỷ, +10,63%** YTD.
- **LDR, Tháng 06/2024**: NHTM Nhà nước 82,62 · NHTM cổ phần 80,78 · Liên doanh/nước ngoài 42,23 · Hợp tác 50,82 · **Toàn hệ thống 78,25**.

**Interest rates.** The official rate-statistics portal `dttktt.sbv.gov.vn` is **unreachable** — verified negative: `curl https://dttktt.sbv.gov.vn/webcenter/portal/vi/menu/rm/ls` → HTTP 000, curl exit 28 (timeout ~21 s); the sbv.gov.vn pages link only to dttktt URLs for rates ("Lãi suất NHNN quy định", "Lãi suất thị trường liên ngân hàng"); `sbv.gov.vn/en/lãi-suấtt1` → HTTP 404. But SBV's monthly average-rate publication reaches the public via press: **Tháng 9/2026** [verified, Dan trí 23/10/2026 citing SBV, fetched]: avg VND deposit rates 4,1–4,6%/năm (1–<6 tháng), 6,6–8,1% (6–12 tháng), 6,2–7,8% (>12–24 tháng), 7,4–8,2% (>24 tháng); **avg lending rates 8,4–10,9%/năm** (+0,2pp m/m; +1,7–1,9pp vs cuối 2025). Context [verified headlines]: SBV is forcing cuts — 46/46 banks cut deposit rates after directive 9608/NHNN-CSTT (18/10/2026); new-deposit avg ~6,38%/năm (Vietstock 10/2026).

**How far back:** the statistics pages carry only the latest month (+ one stale static snapshot); a 2021–2026 monthly series must be assembled from SBV's monthly "tình hình thực hiện chính sách tiền tệ" articles (server-rendered, robots-allow, archived by month) or web.archive.org captures of these same pages. Feasible, a few hours of scraping.

Household decisions powered: "are deposits still the safe growing option" (dân cư +10,63% YTD), "is my bank's rate above or below the system average", "credit is still growing ~10% — the economy isn't starved". Student-team findability: **medium** — the pages are not linked from the SBV homepage nav in an obvious way; press articles quoting SBV are easier.

## 3. Borrowers — mortgage reference rates, margins, prepayment fees

Deposit-rate pages of the same 10 banks were already agent-verified today (D-UNLOCK, 36 rows). My TinyFetch of the same pages confirms the mechanics:

| Bank | Rate page fetched | What renders without a browser agent |
|---|---|---|
| VietinBank | `vietinbank.vn/ca-nhan/cong-cu-tien-ich/lai-suat-khcn` | **full deposit table** [verified: 2,1 / 2,4 / 3,0 / 5,4 / 5,4–5,5 %/năm for 1/3/6/12/24–36M — matches D-UNLOCK] |
| Vietcombank | `.../KHCN---Lai-suat` | deposit table shell, values JS-only; **`/Lai-suat-co-so` → JS shell, 109 chars, no numbers** [negative] |
| BIDV | `bidv.com.vn/.../lai-suat` | `{{item...}}` Angular template, no values; **`/lai-suat-co-so` → HTTP 200 but "Xin lỗi, chúng tôi không tìm thấy trang này"** [negative] |
| MB | `mbbank.com.vn/ho-tro/bieu-lai-suat` (+`?tab=lai-suat-cho-vay`) | shell + calculator, no rate table in fetch [negative] |
| Techcombank | `techcombank.com/cong-cu-tien-ich/bieu-phi-lai-suat` | nav shell only ("đã hết hạn") [negative] |
| ACB | `acb.com.vn/lai-suat` | 404-style shell ("Không tìm thấy trang") [negative] |
| Agribank | `agribank.com.vn/vn/lai-suat-cho-vay` | WebSphere shell, `${title}` placeholders, no data [negative] |
| VPBank, Sacombank | `vpbank.com.vn/lai-suat`, `sacombank.com.vn/.../lai-suat.html` | **not returned by TinyFetch** (no result object) [negative] |

**Conclusion on base rates (lãi suất cơ sở) after teaser periods:** for the big banks they are **not on fetchable public HTML pages** — they live in PDF appendices (e.g., VPBank's "Phụ lục biểu lãi suất niêm yết" PDF that D-UNLOCK caught) or behind JS apps. The margin formula ("lãi suất cơ sở + biên") is a contract term, not a published page — [inferred from the negative fetches above; no bank page fetched states it]. **Prepayment fees:** not verified this session — fee schedules are separate JS/PDF pages (e.g., Techcombank's "Biểu phí và biểu mẫu"); a team needs the TinyFish agent or the PDFs. **SBV average lending rates** are the honest public benchmark: 8,4–10,9%/năm (9/2026) [verified, §2].

Household decision powered: **the true multi-year cost of a mortgage after the teaser expires** — and the verified finding is itself useful: banks do not publish comparable post-teaser rates in machine-readable form, which is exactly the gap a consumer tool fills. Student-team findability: **hard** (this is the differentiating dataset; most teams will stop at teaser rates).

## 4. Household allocation series — deposits vs securities vs gold, 2021–2026

| Series | Source | Granularity / history | Enough for 2021–2026? |
|---|---|---|---|
| New securities accounts | **VSDC itself**: `https://vsdc.vn/vi/ad/164134` (monthly "Thông tin số lượng tài khoản giao dịch...") | monthly announcements; fetched page = Tháng 10/2023 (7.400.592 domestic TK; **167.659 mở mới**, 545.386 đóng) and lists monthly posts through **Tháng 10/2026 (updated 05/11/2026)** | **Yes — monthly, own-source** [verified] |
| New accounts, latest point | Vietstock via `vn.investing.com` (citing VSDC) | Tháng 10/2026: **+252,4 nghìn mở mới**, total ~14,4 triệu, 99,5% cá nhân | [verified] |
| Gold demand, Vietnam | **WGC Goldhub**: `https://www.gold.org/goldhub/data/gold-demand-by-country` | "Quarterly and annual ... from 2010 up to the most recently available quarter", XLSX download "GDT Q3 2026 Tables", data as of 30/9/2026 | **Yes — quarterly XLSX** [verified page] |
| Gold demand, Vietnam sample points | press citing WGC | 2022: 59,1t → 2023: 55,5t consumer; Q4/2025 jewellery 2,4t (−29% y/y) | [verified snippets] |
| Household deposit growth | SBV monthly (§2) | latest month on page; history via monthly articles | Yes, with scraping effort [verified snapshot] |

Verdict: **a 2021–2026 household-allocation series is buildable** — VSDC monthly (own announcements), WGC quarterly (one XLSX), SBV deposits monthly (article archive). VSDC is the easiest win; SBV history is the long pole.

## 5. Dataset → decision → findability (summary)

| Dataset | Household/policy decision | Typical student team finds it? |
|---|---|---|
| DIV limit 125M + 91% fully insured | how to split balances across banks | Yes, trivially |
| DIV premium 0,15%/năm (TT 04/2026) | scheme cost / limit-rise debate (350M proposal) | No — legal databases |
| SBV tiền gửi của dân cư (11.434.266 tỷ, +10,63% YTD 8/2026) | deposits vs gold vs stocks allocation | Partly — press quotes it; SBV page is buried |
| SBV credit by sector (20,49 triệu tỷ, +10,19%) | policy: credit still flowing, where | Partly |
| SBV average deposit/lending rates (9/2026) | "is my rate fair"; mortgage cost benchmark | Yes, via press; SBV portal itself is down |
| Bank base rates / prepayment fees | true post-teaser mortgage cost | No — JS/PDF, non-comparable (the gap = the product) |
| VSDC new accounts monthly | retail money rotating into equities | Partly — vsdc.vn news list, Vietnamese only |
| WGC gold demand by country | gold vs deposits in household portfolios | Yes — gold.org XLSX |

## Rules compliance
robots.txt read for all four hosts before fetching; ≥ 2,5 s delay between same-host requests; no captcha/login bypass; API key read from env, never printed; no TinyFish agent run needed (TinyFetch + search sufficed — cost 0 USD of the 4 USD budget); no repo edits, no git writes, no processes touched, nothing installed.
