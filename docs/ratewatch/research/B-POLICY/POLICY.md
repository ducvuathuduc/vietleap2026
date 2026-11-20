# POLICY — Vietnam banking 2025–2026: which question is live

Read on 20/11/2026, 12:16–12:21 Asia/Saigon. Every URL below was fetched in this session (log: `http/fetch_log.txt`). **[verified]** means the sentence is in the response body or in the text layer / scan of that file. **[inferred]** means a conclusion drawn from those texts, not a number printed in them. No FiinQuant call was made here; bank-ratio availability is the same-day result in `../R-SUPPLY/SUPPLY.md` §1.

**Verdict.** The question a household can act on, with observed data, that is not already a rate table or a FiinRatings sector note, is the deposit-insurance cliff: since 13/7/2026 the cap is 350 million VND per person per institution, and the State Bank's own assessment of that cap fully covers 93.68% of insured depositors but only 19.06% of insured deposit value. Credit-growth quotas are still the live macro tool (a pilot removal was ordered, not enacted). They lose as a product because a household cannot see a bank's remaining quota.

---

## 1. Twelve live issues

### 1. Credit-growth quotas — pilot ordered, quota still described as in force

- **Instrument.** [verified] Công điện 128/CĐ-TTg dated 6/8/2025, signed by the Prime Minister. The Government Portal article (https://baochinhphu.vn/thu-tuong-yeu-cau-nhnn-khan-truong-thi-diem-bo-room-tin-dung-102250807092619905.htm, HTTP 200, 12:17:31) says the State Bank must urgently build a roadmap and **pilot the removal of administrative credit-growth targets for implementation from 2026**, limited to banks that meet safety and credit-quality tests, with the State Bank still supervising so the system and the inflation target hold. That is an order to design a pilot, not a notice that the quota has been abolished.
- **Still operating in 2026.** [verified] FiinRatings, *Ngành Ngân hàng Việt Nam: Tổng kết năm 2025 và Triển vọng năm 2026* (Hà Nội, tháng 04/2026, 22 pages; https://fiinratings.vn/Data/2026/Report/FiinRatings_Tam-diem-nganh-Ngan-hang-2026.pdf, HTTP 200, 2,114,570 bytes, 12:17:53). Text layer: credit growth "đạt đỉnh khoảng 19%" in 2025 and is forecast to slow in 2026 because credit/GDP is "ở mức cao vượt 140%" and because of "các quy định mới từ Ngân hàng Nhà nước, bao gồm thiết lập hạn mức tăng trưởng tín dụng theo quý chặt chẽ hơn và giới hạn cho vay bất động sản." These are FiinRatings' figures, not a State Bank spreadsheet opened here.
- **Not used.** A Vietnambiz chronology names Công văn 11686/NHNN-CSTT, Chỉ thị 01/CT-NHNN and other 2026 dispatches. Those documents were not opened. Do not cite their numbers.
- **Who.** Borrowers who meet a bank that has used its quota, and every bank. No official count of refused household applications was found.
- **Household decision.** Whether to apply now or wait, and whether a social-housing or industrial-park loan is treated inside the quota. That split is not in a public per-bank file.
- **Policy question.** Has the 2026 pilot actually replaced the quota for any named bank, and did the real-estate sub-limit change who gets a mortgage?
- **Data.** The Công điện URL above. No public per-bank remaining-quota series was found. FiinQuant `get_ratios` has loan-growth fields from 2021 (R-SUPPLY §1) but not the quota.

### 2. Deposit-rate ceiling — 4.75% on terms under 6 months

- **Instrument.** [verified] Quyết định 2411/QĐ-NHNN, signed 1/11/2024 by Phó Thống đốc Phạm Quang Dũng, effective 20/11/2024, under Thông tư 48/2024/TT-NHNN of 30/9/2024. The State Bank HTML page is only a title plus a scanned attachment (https://sbv.gov.vn/vi/w/sbv618464, HTTP 200, 12:17:23; PDF https://sbv.gov.vn/documents/d/sbv_portal/587507, HTTP 200, 653,990 bytes, 12:20:33, two JPEG pages, no text layer). The scan reads:
  - demand deposits and terms under 1 month: **0.5%/year**;
  - terms from 1 month to under 6 months: **4.75%/year**;
  - people's credit funds and microfinance institutions, same band: **5.25%/year**;
  - replaces Quyết định 1124/QĐ-NHNN of 16/6/2023.
  - Terms of 6 months and longer are outside this decision.
- **Contradiction discarded.** A commercial page (goctaisan.com, seen in search) states a ceiling of six percent for the 1-to-under-6-month band while citing Quyết định 2411. The scan does not. That figure is not used.
- **No later decision found.** Legal roundups retrieved this session (luatvietnam.vn, luatquanghuy.vn, both still listing 2411 in pages dated as 2026 updates) did not name a replacing decision. [inferred] 2411 is still the ceiling, because the scan is the latest instrument those pages and the State Bank library entry point to. A hidden 2026 decision was not ruled out by an exhaustive gazette search.
- **Consistency check, not a compliance audit.** [verified by count] `../D-UNLOCK/samples/deposit_rates_today.csv` has 89 data rows and 10 banks. 36 rows are TinyFish-confirmed (33 `tinyfetch:rate+term`, 3 `tinyfetch:rate_only`); 53 are `agent_only_unconfirmed`. Zero rows with `term_months` < 6 have `rate_pct` > 4.75. Confirmed banks: ACB, HDBank, Sacombank, VietinBank, plus one VCB row and one BIDV rate-only row. Agribank, MB, Techcombank and VPBank rows in that file are unconfirmed.
- **Who.** Every VND depositor in a term under 6 months. No official count of accounts in that band was found.
- **Household decision.** Roll a sub-6-month deposit at or under the ceiling, or lock 6 months or longer where the bank sets the rate.
- **Policy question.** Does the ceiling push savers into uncapped longer terms, and is that the rate race the State Bank has been trying to cool?
- **Data.** The PDF above. Live bank tables: the 36 confirmed rows. State Bank statistical site `dttktt.sbv.gov.vn` was unreachable in R-SUPPLY this morning; it was not re-probed here.

### 3. Deposit insurance — cap is now 350 million; most of the money is still above it

- **Cap.** [verified] https://www.div.gov.vn/tu-ngay-13-7-2026-han-muc-chi-tra-tien-bao-hiem-cua-bao-hiem-tien-gui-viet-nam-la-350-trieu-dong (HTTP 200, 12:17:13). Thông tư 05/2026/TT-NHNN: from **13/7/2026** the maximum payout is **350 million VND** of insured deposits (principal and interest) of one person at one insured institution. The previous cap, Quyết định 32/2021/QĐ-TTg of 20/10/2021, was 125 million. DIV states the increase is 225 million, which is +180%.
- **Law.** [verified] https://www.div.gov.vn/luat-bao-hiem-tien-gui-nam-2025-bao-ve-nguoi-gui-tien-toan-dien-chu-dong-va-linh-hoat-hon (HTTP 200, 12:17:20). Luật Bảo hiểm tiền gửi 2025: the Governor sets the cap each period and, in a special case, may pay above the cap up to all insured deposits. The payout deadline falls from 60 days (2012 law) to **45 days**.
- **Premium.** [verified] https://www.div.gov.vn/quyen-va-nghia-vu-cua-to-chuc-tham-gia-bao-hiem-tien-gui-theo-luat-bao-hiem-tien-gui-nam-2025 (HTTP 200, 12:17:18), describing Thông tư 04/2026/TT-NHNN. Premium is **0.15%/year** of the average insured balance; people's credit funds pay **0.1%/year from the Q4 2026** collection quarter. The household does not pay this. The premium is flat, not risk-based, in that circular.
- **Stock and coverage.** [verified] https://www.div.gov.vn/se-co-thong-tu-moi-ve-han-muc-chi-tra-tien-bao-hiem (HTTP 200, 12:17:15). DIV, citing the State Bank, at **31/12/2025**: insured balances **10.02 million billion VND** (up almost 3.4 million billion, +51.4%, versus end-2021); **138.69 million** insured depositors (up 55.58 million, +66.87%, versus 2021). After dropping balances under 50,000 VND, a 125 million cap fully covered **87.61%** of insured depositors, below the IADI-style 92–95% goal in the deposit-insurance strategy. The State Bank's assessment of the **350 million option** (this page is the pre-issuance write-up, not a recount after 13/7/2026): depositors fully covered **93.68%** system-wide and **80.15%** at people's credit funds; **value** fully covered **19.06%** system-wide and **37.57%** at people's credit funds; cap / GDP per capita **2.8 times** (the page's global comparison: 98% of people, 47% of value, 3.3 times GDP per capita).
- **Do not read 138.69 million as unique people.** [verified] World Bank population, Vietnam, 2025 = **101,598,527** (https://api.worldbank.org/v2/country/VNM/indicator/SP.POP.TOTL?format=json&mrnev=1, HTTP 200, 12:18:24, `lastupdated` 2026-11-11). [inferred] DIV's "người gửi tiền" counts a person once per institution, because 138.69 million exceeds the 2025 population.
- **Who.** Every insured depositor. The household that is above 350 million at one bank is in the 6.32% of depositors, and in the 80.94% of value, that the State Bank's assessment left partly uninsured. Those two percentages are the assessment of the option, dated on the pre-circular page, not a measurement taken after July 2026.
- **Household decision.** If the balance at one bank exceeds 350 million, split the excess, or keep it and accept that only 350 million is insured.
- **Policy question.** Is a flat 350 million cap the right design when it covers about 94% of depositors and about 19% of value, and while the premium stays a flat 0.15%?
- **Data.** The four DIV URLs. Per-bank risk: FiinQuant NPL, LDR, NIM from 2021 (R-SUPPLY §1; not re-called). Per-bank rate: the 36 confirmed rows.

### 4. Lending-rate transparency and the post-teaser mortgage reset

- **Instrument.** [verified] Văn bản hợp nhất 06/VBHN-NHNN 2026, consolidating Thông tư 39/2016/TT-NHNN as amended, including by Thông tư 52/2025/TT-NHNN of 25/12/2025. Retrieved this session from https://thuvienphapluat.vn/van-ban/Tien-te-Ngan-hang/Van-ban-hop-nhat-06-VBHN-NHNN-2026-Thong-tu-hoat-dong-cho-vay-cua-to-chuc-tin-dung-doi-voi-khach-hang-692624.aspx (robots.txt of that host is `Allow: /`, fetched 12:20:35). Điều 13: the rate is agreed, except a State Bank ceiling on short-term VND loans to five priority uses (agriculture, exports, SMEs, supporting industry, high technology) when the borrower is judged financially transparent. For an adjustable rate the contract must state the factors and the adjustment date; if those factors produce several rates, the bank applies the **lowest**. Overdue principal is capped at **150%** of the in-term rate at the rollover into overdue. Late interest on unpaid interest is capped at **10%/year**. Before signing, the bank must disclose the rate, the adjustment rule, overdue and late rates, the interest method, and fees.
- **Separate ceiling, still cited as in force by 2026 roundups, PDF not opened.** Quyết định 1125/QĐ-NHNN effective 19/6/2023: short-term VND lending ceiling **4.0%/year** (5.0% for people's credit funds and microfinance) for those priority uses. Source is the luatvietnam and luatquanghuy compilations, not the decision PDF.
- **What is not a rule.** There is no statutory "teaser then reset" formula. The teaser is a commercial fixed rate for the first months; the legal duty is to write the later formula down. No open table of those formulas was found. Vietcombank's utility URL https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich returned HTTP 200 at 12:20:47 with HTML title "Promotion", so a calculator was not confirmed there.
- **Who.** Mortgage borrowers. No official count of teaser contracts was found.
- **Household decision.** Sign only if the post-teaser formula is on the page, and compute the đồng increase in the monthly payment when the teaser ends.
- **Policy question.** Does the disclosure duty in Điều 13 change the loan a household accepts, or do advertised teaser rates still hide the reset?
- **Data.** The consolidated circular. Not a rate panel. A honest product here is a calculator the user fills in, not a scraped "true mortgage rate".

### 5. Bad-debt powers and mandatory transfer of weak banks

- **Law.** [verified] https://congbao.chinhphu.vn/van-ban/luat-so-96-2025-qh15-45584.htm (HTTP 200, 12:17:40). Luật 96/2025/QH15, adopted 27/6/2025, in force **15/10/2025**, amends the Law on Credit Institutions. The amending text retrieved this session from https://thuvienphapluat.vn/van-ban/Tien-te-Ngan-hang/Luat-Cac-to-chuc-tin-dung-sua-doi-2025-so-96-2025-QH15-648594.aspx adds Điều 198a: a bank or a debt-trading firm may seize collateral of a bad loan if (i) a Civil Code 299 enforcement event has occurred, (ii) the security contract agrees to seizure, (iii) the security is effective against third parties, (iv) the asset is not in a pending court dispute, emergency measure, or enforcement seizure, and (v) the asset meets conditions the Government sets. The same page amends special State Bank lending to a troubled institution to **0%/year**. The 2411 scan's preamble cites the Law on Credit Institutions dated 18/01/2024; the number of that base law was not printed on the two pages read.
- **Transfers.** [verified] https://sbv.gov.vn/vi/w/sbv622822 (HTTP 200, 12:17:26). On **17/01/2025** the State Bank announced the mandatory transfer of **GPBank to VPBank** and **DongA Bank to HDBank**. The page says depositors' lawful rights at those two banks continue. Press snippets in this session's search also name OceanBank → MB and CB → Vietcombank and a 9/10/2025 review meeting. Those articles were not saved. Only the two transfers on the State Bank page are treated as confirmed.
- **Who.** Depositors and borrowers of GPBank and DongA Bank, and any household that signed a security contract with a seizure clause. No headcount in the State Bank release.
- **Household decision.** Leave a deposit at the transferred bank, or move the uninsured slice; as a borrower, read whether the mortgage allows seizure without a court case.
- **Policy question.** After the transfer, is a đồng at GPBank or DongA Bank as safe as a đồng at VPBank or HDBank, once the 350 million cap is applied?
- **Data.** The State Bank release. Problem-loan ratios only if FiinQuant lists the transferred banks (not checked in this task).

### 6. Basel-style capital and the LDR constraint

- **Capital.** [verified] https://congbao.chinhphu.vn/van-ban/thong-tu-so-14-2025-tt-nhnn-45654.htm (HTTP 200, 12:17:35). Thông tư 14/2025/TT-NHNN, issued 30/6/2025, effective **15/9/2025**, "quy định tỷ lệ an toàn vốn đối với ngân hàng thương mại, chi nhánh ngân hàng nước ngoài." The Công báo page is the catalogue card. The ratios below are from the full text reproduced at https://luatvietnam.vn/tai-chinh/thong-tu-14-2025-tt-nhnn-cua-ngan-hang-nha-nuoc-viet-nam-quy-dinh-ty-le-an-toan-von-doi-voi-ngan-hang-thuong-mai-chi-nhanh-ngan-hang-nuoc-ngoai-405700-d1.html, retrieved this session: minimum core tier-1 **4.5%**, tier-1 **6%**, total capital **8%**; a capital-conservation buffer phased 0.625% / 1.25% / 1.875% / **2.5%**, so the total-capital ratio including the buffer reaches **10.5%** from year four; year one is the year a bank adopts the standardised or internal-ratings approach, otherwise **2030**; a countercyclical buffer of **0–2.5%** only when the Governor switches it on; from **1/1/2030** every bank that has not opted in must use this circular's standardised approach. Cash dividends are allowed only while the ratios hold. The State Bank's own magazine states the same circular adds buffers, including one for systemically important banks (https://thoibaonganhang.vn/chuan-hoa-ty-le-an-toan-von-theo-thong-le-quoc-te-tang-suc-de-khang-he-thong-ngan-hang-167440.html, search retrieval). [inferred] A household cannot see regulatory capital; FiinQuant's NPL/LDR/NIM are not this ratio.
- **LDR.** [verified as reproduced] https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/thong-tu-08-cho-phep-tinh-20-tien-gui-co-ky-han-cua-kho-bac-nha-nuoc-vao-mau-so-ldr-tu-1552026-diem-269431.html, retrieved this session. Thông tư 08/2026/TT-NHNN of 15/5/2026, effective that day, amends Thông tư 22/2019 so that **20%** of the Treasury's term deposits enter the LDR denominator (80% stay out); Treasury demand deposits stay out; the LDR cap remains **85%**.
- **Not verified.** Vietnambiz claims Thông tư 25/2026/TT-NHNN raised the cap on short-term funding used for medium- and long-term loans from 30% to 40%, effective 1/7/2026. That circular was not opened. Do not use 40%.
- **Who.** Banks, and depositors who are choosing a bank on "is it well capitalised".
- **Household decision.** Do not treat a published NPL as a Basel ratio. The decision that uses capital is the uninsured excess in issue 3, and only with that caveat.
- **Policy question.** Does the buffer path to 10.5% by the 2030 cohort, plus an 85% LDR, replace the credit quota as the binding constraint?
- **Data.** The two circulars. FiinQuant does not replace the regulatory return.

### 7. Consumer-finance pricing — a frame that is filed, not a statutory cap

- **Instrument.** [verified] Thông tư 18/2019/TT-NHNN amends Thông tư 43/2016/TT-NHNN. Text retrieved this session: https://thuvienphapluat.vn/van-ban/Tien-te-Ngan-hang/Thong-tu-18-2019-TT-NHNN-sua-doi-Thong-tu-43-2016-TT-NHNN-cho-vay-tieu-dung-409941.aspx. A finance company must issue one frame for the whole system, with the **highest and lowest** consumer-loan rate per product, and file it within 10 working days with the Banking Supervision Agency and the local State Bank branch. Điều 9 points the rate itself back to the general lending rules. **No numeric ceiling is in that article.**
- **Who.** Borrowers at finance companies (app loans, salary loans). No official count of those contracts was found.
- **Household decision.** Compare the all-in rate on the actual balance, including fees, with the advertised rate. The frame the company filed is not a public table that this session found.
- **Policy question.** Would publishing the filed frames, or setting a cap, change whether a household takes the loan?
- **Data.** The circular. A negative: no State Bank open file of those frames was retrieved. Do not invent a typical APR.

### 8. Biometrics and fraud — the gate is already on

- **Instrument.** [verified] https://sbv.gov.vn/vi/w/sbv619010 (HTTP 200, 12:17:28), State Bank article "Cập nhật thông tin giấy tờ tùy thân và dữ liệu sinh trắc học". Thông tư 18/2024/TT-NHNN: from **1/1/2025** a cardholder must have matched identity and biometrics before electronic card transactions; from **1/7/2025** an expired identity document stops the card. Thông tư 40/2024/TT-NHNN: from **1/10/2024** an e-wallet opened online requires biometric authentication. The same article points to Thông tư 17/2024/TT-NHNN (catalogue card: https://congbao.chinhphu.vn/van-ban/thong-tu-so-17-2024-tt-nhnn-42189.htm, HTTP 200, 12:17:43, issued 28/6/2024) for matching the account holder's biometrics to the chip ID card or VNeID. The State Bank page states the electronic cash-withdrawal and payment gate applies to **individual** accounts from 1/1/2025 and to **organisations** from 1/7/2025, and that the match is once, not on every transfer. Non-financial queries are not blocked.
- **Fraud.** Official pages warn about impersonation of banks, CIC and the police, and about fake links after a CIC security incident. No nationwide victim count or đồng loss was in the pages opened. None is stated here.
- **Who.** Every payment-account holder who wants to move money electronically. The 86.97% account figure in issue 9 is the closest official reach number, and it is for end-2024, before the 2025 gate.
- **Household decision.** Complete the biometric match, and do not give an OTP to a caller.
- **Policy question.** What share of accounts is still blocked for missing biometrics, and did the gate reduce impersonation losses? Neither number was published on the pages opened.
- **Data.** The State Bank article. Not a loss series.

### 9. Cashless payments — 2025 targets beaten; 2026 targets are a new list

- **Scheme.** [verified] https://vanban.chinhphu.vn/?docid=204364&pageid=27160 (HTTP 200, 12:17:48). Quyết định 1813/QĐ-TTg of 28/10/2021, Prime Minister, the cashless-payment scheme for **2021–2025**.
- **Result, as printed by the State Bank's review.** [verified] https://tapchinganhang.gov.vn/hoat-dong-thanh-toan-khong-dung-tien-mat-vuot-nhieu-muc-tieu-de-ra-16975.html (HTTP 200, 12:17:45; the page is dated 02/02/2026 in the article header seen via search). Citing the State Bank: by end-2024, **86.97%** of people aged 15 and over had a bank account (above the 1813 target); cashless share of e-commerce **66.8%**; cashless value in **2025** equalled **28.17 times GDP**, against a target of 25 times. The underlying State Bank table was not downloaded. The same article records Nghị định 52/2024/NĐ-CP (15/5/2024) on cashless payment, Nghị định 94/2025/NĐ-CP (issue 12), and Nghị định 368/2025/NĐ-CP of 31/12/2025 on mobile-money services.
- **2026 targets.** [verified as a legal publisher's account] https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/107195/yeu-cau-gia-tri-thanh-toan-khong-dung-tien-mat-phai-gap-30-lan-gdp-trong-nam-2026 (HTTP 200, 12:20:38). It says Thông báo **114/TB-VPCP of 11/3/2026** records the 24/2/2026 meeting of the National Financial Inclusion Steering Committee and sets, among other targets: **95%** of the population aged 15+ with a transaction account; cashless value **30 times GDP**; at least **30%** of adults saving; at least **300,000** SMEs with a loan outstanding; agriculture/rural credit "đạt từ 25%" (the sentence on that page stops there); at least **75%** of adults with a credit history; insurance revenue about **3.3–3.5% of GDP**. The Thông báo PDF itself was not opened.
- **Who.** Anyone who already has an account (the large majority, on the 86.97% figure) and the remaining unbanked.
- **Household decision.** Weak as a new choice in November 2026: the account decision is largely made. The live household piece of "cashless" is the gold-payment rule in issue 11 and the biometric gate in issue 8.
- **Policy question.** Which single lever moves the account rate from 86.97% toward 95%, and is 30 times GDP a household outcome or a payments-volume outcome?
- **Data.** The review article and the Thông báo summary. Not a household-level file.

### 10. Green credit — a taxonomy exists; a loan-rate series does not

- **Instrument.** [verified] Công báo PDF of Quyết định **21/2025/QĐ-TTg**, Hà Nội, 4/7/2025, 36 pages (https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2025/7/45465/57497-1-2025933-93421-2025-qd-ttg.pdf, HTTP 200, 742,578 bytes, 12:17:50). Điều 1: environmental criteria and confirmation so a project on the green list can receive state support for **green credit and green bonds**. Điều 10: effective **22/8/2025**. Điều 9 khoản 3: the State Bank guides credit institutions. Banks are encouraged to use the list for their own green loans.
- **Risk rule, older.** Thông tư 17/2022/TT-NHNN, effective 1/6/2023, requires environmental-risk management in credit. The consolidation https://thuvienphapluat.vn/van-ban/Tien-te-Ngan-hang/Van-ban-hop-nhat-100-2026-VBHN-TT-NHNN-Thong-tu-huong-dan-quan-ly-rui-ro-moi-truong-hoat-dong-cap-tin-dung-726214.aspx (retrieved this session) says Thông tư 35/2026/TT-NHNN of 1/7/2026 amends it, on the evidence of that page mostly to rename State Bank units.
- **Who.** A household or firm that is the sponsor of a project seeking a green loan. Not a mass saver. No official count of confirmed green projects was opened (the decision tells the agriculture-and-environment ministry to publish the list on its portal; that portal was not fetched).
- **Household decision.** Only if the household is borrowing for a project on the list: ask whether the loan is priced as green, and do not accept a "green" label that has no confirmation under Quyết định 21.
- **Policy question.** Does the taxonomy change the rate or the availability of a household loan, or only the label?
- **Data.** The decision PDF. No green-credit stock or green-mortgage rate was retrieved. Judge fit is real (Dr. Phạm Thái Bình, sustainable finance; mentors on ESG) and the household use is narrow.

### 11. Banks and gold bars — production is no longer a one-firm activity; cash stops at 20 million

- **Instrument.** [verified] https://xaydungchinhsach.chinhphu.vn/noi-dung-co-ban-cua-nghi-dinh-so-232-2025-nd-cp-ve-quan-ly-hoat-dong-kinh-doanh-vang-11925082910094638.htm (HTTP 200, gzip, decoded, 12:17:33). Nghị định **232/2025/NĐ-CP** of 26/8/2025 amends Nghị định 24/2012/NĐ-CP and takes effect **10/10/2025**. A gold bar may carry the mark of an enterprise **or a commercial bank** licensed by the State Bank. Điều 11a lets a commercial bank that already holds a gold-bar trading licence be considered for a **production** licence. Purchases and sales of gold worth **from 20 million VND per customer per day** must be paid through payment accounts of the customer and of the gold firm at a commercial bank. Gold derivatives of banks follow Điều 112 of the Law on Credit Institutions.
- **Who.** Anyone buying a bar. A 1-lượng bar is far above 20 million (R-SUPPLY recorded a BTMC SJC quote on 20/11/2026; not re-fetched). The licence list of which banks may mint bars was **not** opened. Do not name a minting bank.
- **Household decision.** Pay any purchase at or above 20 million through a bank account; do not treat a bar as a deposit substitute (it is not inside the 350 million insurance cap).
- **Policy question.** Did ending the single-producer structure, plus the cashless threshold, narrow the domestic premium? That question is already crowded (see §2 and `../C-GOLD`).
- **Data.** The decree page. Price feeds exist (R-SUPPLY §2). The licensed-producer list does not, in this session.

### 12. Fintech sandbox and digital assets — a legal frame, not yet a household product

- **Banking sandbox.** [verified] https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-94-2025-nd-cp-44816.htm (HTTP 200, 12:17:38). Nghị định **94/2025/NĐ-CP**, issued 29/4/2025, effective **1/7/2025**, "quy định về Cơ chế thử nghiệm có kiểm soát trong lĩnh vực ngân hàng." The Công báo page fetched is the catalogue card; the list of eligible activities was not read from the decree PDF.
- **Digital assets.** [verified] Consolidated text https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Van-ban-hop-nhat-20-VBHN-VPQH-2026-Luat-Cong-nghiep-cong-nghe-so-695337.aspx, retrieved this session. Luật Công nghiệp công nghệ số **71/2025/QH15** of 14/6/2025 is effective **1/1/2026** (articles 11, 28 and 29 from 1/7/2025). Điều 46–48 define a digital asset, split virtual assets and crypto-assets (both excluding securities, digital forms of fiat, and other financial assets), and leave licensing conditions for crypto-asset services to the Government.
- **Local trials.** Search snippets name Đà Nẵng controlled trials (Basal Pay, MIMO / Dragon Lab). Those articles were not saved. They are not treated as confirmed.
- **Who.** A household that already holds crypto and wants a legal đồng off-ramp. Most households are outside that set. No official user count was found.
- **Household decision.** Do not use an unlicensed converter. There is no nationwide licensed rail confirmed in the pages opened.
- **Policy question.** Which sandbox activity, if any, is open to a resident by 21/11/2026, and what loss does a household bear if the trial fails?
- **Data.** The two legal URLs. Not a price or volume series.

---

## 2. What is already crowded

Checked this session, with robots read first where a site was scraped for content.

| What a household already has | What this session saw | Implication |
|---|---|---|
| Cross-bank deposit-rate tables | https://webgia.com/lai-suat/ HTTP 200, 12:17:55, title "Lãi suất ngân hàng tháng 11/2026…". The HTML contains **89** copies of "xem tại webgia" and **707** of "webgia.com". Same decoy R-SUPPLY found: a script does not get the rates. https://laisuattietkiem.vn/ HTTP 200, 12:17:57, title "So sánh lãi suất tiết kiệm hôm nay \| Tại quầy và online" (robots allow reference use). | A rate-comparison dashboard is what these sites are. Other teams will rebuild it. |
| A bank's own online deposit | https://timo.vn/ HTTP 200, 12:20:41, title "Timo Digital Bank by BVBank… Gửi tiết kiệm online". | One bank selling its own rate, not a market. |
| Free finance calculators | https://tools.finhay.com.vn/ HTTP 200, 12:20:44, title "Công Cụ Tài Chính Miễn Phí — Finhay". | The calculator category is occupied. Contents of each tool were not clicked. |
| thebank.vn | robots.txt and homepage: curl HTTP **000**, 0 bytes, 25s timeout, 12:17:06 and 12:18:20. | Unreachable from this machine today. Not evidence the site is down for a browser. |
| Mortgage calculators on bank sites | Vietcombank utility URL returned title "Promotion" (issue 4). No post-teaser formula table was found. | The teaser-reset question is less crowded than the rate table, and also less supplied with data. |
| Bank-health rankings | The FiinRatings April 2026 spotlight already prints sector NPL "khoảng 1,9%" for 2025, NIM **2.9%** at end-2025 versus **3.5%** at end-2024, and a median issuer rating still at **[A-]** (7 upgrades, no downgrades in 2025). Every hackathon team has FiinQuant; R-SUPPLY §1 showed `get_ratios` returning VCB 2024 NPL 0.96%, LDR 80.8%, NIM 2.86%. Mentor Đinh Xuân Phan Anh is from FiinGroup. | A "safest bank" leaderboard from NPL is what the data vendor already published, and what other teams can assemble in an hour. |
| Gold premium, FTSE flows, macro dashboards | Already killed in `../DECISION.md` on crowding grounds. This session did not reopen them. | Do not make the banking pivot a gold screen or another macro monitor. |

**What other teams in this hackathon will most likely build.** A deposit-rate leaderboard (the pages above, plus the bank PDFs TinyFish can read), a FiinQuant NPL ranking of listed banks, or a reuse of a macro dashboard. All three fail the owner's "not another dashboard" test. The insurance cliff does not: none of the rate sites joins a household's own balance to the 350 million cap and to a bank's problem loans.

---

## 3. Top 5, scored, and the one to build

Scores are judgment **[inferred]**, 1–5, equal weights. Facts under them are the verified items in §1. "Fit" names the person whose published role the question actually uses.

| Rank | Sum | Data | Household | Policy | Unique | Fit | Wow | Build by 21/11 13:00 | One-sentence research question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 33 | 4 | 5 | 5 | 4 | Ms Nguyễn Ngọc Phương Trang (bank operations), Dr Nguyễn Tri Dung (why people do not split), Dr Nguyễn Văn Phúc (banking), Đinh Xuân Phan Anh (the ratios) | 5 | 5 | Given the 350 million VND cap per person per bank since 13/7/2026, and the State Bank's assessment that this fully covers 93.68% of insured depositors but only 19.06% of insured value, should a household with a balance above the cap split, and which bank's observed problem-loan ratio and confirmed deposit rate makes the uninsured excess least costly? |
| 2 | 28 | 5 | 5 | 4 | 2 | Dr Nguyễn Tri Dung (term choice), Ms Nguyễn Ngọc Phương Trang | 3 | 5 | With the statutory ceiling at 4.75%/year for VND terms from 1 month to under 6 months, does locking 6 months or longer earn more, after an early-withdrawal penalty, than rolling short deposits at the ceiling? |
| 3 | 27 | 3 | 4 | 5 | 4 | Ms Nguyễn Ngọc Phương Trang, Dr Nguyễn Văn Phúc | 4 | 3 | After the 17/1/2025 mandatory transfer of GPBank to VPBank and DongA Bank to HDBank, is a deposit at the transferred bank as protected as one at the receiving bank once the 350 million cap and published problem loans are both applied? |
| 4 | 26 | 2 | 5 | 4 | 4 | Dr Nguyễn Tri Dung, Ms Nguyễn Ngọc Phương Trang | 4 | 2 | When a mortgage teaser ends, by how many đồng does the monthly payment rise under the adjustment formula Điều 13 requires the contract to state, and which banks publish that formula before the household signs? |
| 5 | 23 | 3 | 2 | 5 | 3 | Dr Phạm Thái Bình (sustainable finance), Dr Sacha Dray (the macro frame), Karan Vishwanath (ESG) | 2 | 3 | Does Quyết định 21/2025/QĐ-TTg change the rate or the availability of a loan for a project on the green list, or does the absence of a public green-loan rate series mean the taxonomy is not yet a household decision? |

Just outside: consumer-finance APR (22, no public frame), the credit quota itself (high policy, a household cannot see the remaining room), the sandbox (high uniqueness, almost no household user), Basel buffers (the household cannot see regulatory capital).

**Build rank 1, and fold rank 3 into it.** One screen. The household types a balance and a bank. The screen shows the insured slice (min(balance, 350,000,000)), the uninsured slice, the State Bank's 19.06% value-coverage figure with its date and its limit (it is the pre-July assessment, not a recount), and the confirmed deposit rate plus the latest FiinQuant NPL/LDR/NIM if that bank is in the feed. A second line lists the transferred banks from the 17/1/2025 State Bank release and does not pretend their ratios were fetched. Rank 2 is a crowded rate table with a ceiling annotation; it is a good footnote, not the product. Rank 4 needs formulas that are not in a dataset. Rank 5 fits Dr Phạm Thái Bình and does not fit a household who is not sponsoring a project.

**Demo sentence, with the numbers that are allowed.** "At 31/12/2025 the insured system held 10.02 million billion VND across 138.69 million depositor records. The State Bank judged that a 350 million cap, which has been in force since 13/7/2026, would fully insure 93.68% of those depositors and 19.06% of that value. Anything you hold above 350 million at one bank is outside that promise."

**Do not show** the 53 unconfirmed rate rows, the discarded commercial ceiling, an unverified medium-term funding cap, a victim count for fraud, a named gold-minting bank, or a per-bank credit quota.

---

## Sources touched (access Asia/Saigon, 20/11/2026)

| Time | HTTP | Bytes | URL |
|---|---|---|---|
| 12:17:13 | 200 | 69,238 | https://www.div.gov.vn/tu-ngay-13-7-2026-han-muc-chi-tra-tien-bao-hiem-cua-bao-hiem-tien-gui-viet-nam-la-350-trieu-dong |
| 12:17:15 | 200 | 84,000 | https://www.div.gov.vn/se-co-thong-tu-moi-ve-han-muc-chi-tra-tien-bao-hiem |
| 12:17:18 | 200 | 81,935 | https://www.div.gov.vn/quyen-va-nghia-vu-cua-to-chuc-tham-gia-bao-hiem-tien-gui-theo-luat-bao-hiem-tien-gui-nam-2025 |
| 12:17:20 | 200 | 83,353 | https://www.div.gov.vn/luat-bao-hiem-tien-gui-nam-2025-bao-ve-nguoi-gui-tien-toan-dien-chu-dong-va-linh-hoat-hon |
| 12:17:23 | 200 | 513,662 | https://sbv.gov.vn/vi/w/sbv618464 |
| 12:20:33 | 200 | 653,990 | https://sbv.gov.vn/documents/d/sbv_portal/587507 |
| 12:17:26 | 200 | 534,024 | https://sbv.gov.vn/vi/w/sbv622822 |
| 12:17:28 | 200 | 547,510 | https://sbv.gov.vn/vi/w/sbv619010 |
| 12:17:31 | 200 | 63,705 | https://baochinhphu.vn/thu-tuong-yeu-cau-nhnn-khan-truong-thi-diem-bo-room-tin-dung-102250807092619905.htm |
| 12:17:33 | 200 | 79,748 | https://xaydungchinhsach.chinhphu.vn/noi-dung-co-ban-cua-nghi-dinh-so-232-2025-nd-cp-ve-quan-ly-hoat-dong-kinh-doanh-vang-11925082910094638.htm |
| 12:17:35–43 | 200 | — | Công báo cards for Thông tư 14/2025, Nghị định 94/2025, Luật 96/2025, Thông tư 17/2024 |
| 12:17:45 | 200 | 154,877 | https://tapchinganhang.gov.vn/hoat-dong-thanh-toan-khong-dung-tien-mat-vuot-nhieu-muc-tieu-de-ra-16975.html |
| 12:17:48 | 200 | 82,957 | https://vanban.chinhphu.vn/?docid=204364&pageid=27160 |
| 12:17:50 | 200 | 742,578 | Quyết định 21/2025/QĐ-TTg PDF (Công báo CDN) |
| 12:17:53 | 200 | 2,114,570 | FiinRatings banking spotlight PDF |
| 12:17:55 | 200 | 143,839 | https://webgia.com/lai-suat/ |
| 12:17:57 | 200 | 95,923 | https://laisuattietkiem.vn/ |
| 12:18:20 | 000 | 0 | https://thebank.vn/ |
| 12:18:24 | 200 | 279 | World Bank population API |
| 12:20:38 | 200 | 160,347 | Thông báo 114 summary on thuvienphapluat.vn |
| 12:20:41 | 200 | 214,300 | https://timo.vn/ |
| 12:20:44 | 200 | 17,668 | https://tools.finhay.com.vn/ |

Robots: sbv.gov.vn `Disallow` empty; baochinhphu, xaydungchinhsach, congbao, fiinratings, webgia, thuvienphapluat allow `/`; tapchinganhang allows the article path used; laisuattietkiem allows reference use. div.gov.vn/robots.txt returned an HTML shell, not a disallow list. Delay between requests was 2 seconds. No login, no captcha bypass. FiinQuant was not called.
