# B-BANKDATA · Vietnamese listed banks and the price of deposits

**Internal research · 20 November 2026 · Asia/Saigon (UTC+07).** FiinQuantX 0.1.73 identified 28 exchange-traded banks and returned 614 of 644 possible consolidated bank-quarters. Using four cross-checked retail quotes, Spearman ρ was **+0.40 for NPL, −0.40 for loan-loss coverage, −0.80 for LDR, and −0.40 for equity/assets**. This compares November deposit offers with 2026 Q3 financials. The sample is too small and the dates too different to establish depositor discipline.

## 1. Bank roster and ownership

[verified] FiinQuant's live calls at 12:12–12:13 returned 28 unique members from ICB Banks (BANKS_L2). Each matched a BasicInfor record and an exchange index member. The SDK called [GetMappingObjects](https://fiinquant.fiintrade.vn/Master/GetMappingObjects), [GetOrganizationsByIcb](https://apigw.fiingroup.vn/FXPJ/MasterData/GetOrganizationsByIcb), [gettickerbygroup](https://fiinquant.fiintrade.vn/master/gettickerbygroup) for VNINDEX, HNXIndex and UpcomIndex, and [GetOrganizationsByGroupCodeAndIcbCode](https://apigw.fiingroup.vn/FXPJ/MasterData/GetOrganizationsByGroupCodeAndIcbCode) (HTTP 200, 29 BasicInfor rows × 11 fields). The extra BasicInfor row was BAOVIETBAN, venue OTC, outside the exchange universe. UPCoM is registered trading and included here. The [LPBank HNX-filed prospectus](https://owa.hnx.vn/ftp/cims/2026/6_W4/000000016502778_signed_EN._TB_chao_ban_TPRCC__BCB_cam_ket_HD_dai_dien_CBTT.pdf) names the 27 other codes. [PVcomBank's trading notice](https://www.pvcombank.com.vn/tin-tuc/tin-pvcombank/pvcombank-dau-moc-upcom-va-buoc-chuyen-sang-giai-doan-tang-toc-moi) confirms PCB entered UPCoM on 12 August 2026 (sources accessed 12:12–12:15).

| Venue | Ownership / legal form | Tickers |
|---|---|---|
| HOSE | Direct state-majority joint-stock banks | BID, CTG, VCB |
| HOSE | Other commercial joint-stock banks | ACB, BVB, EIB, HDB, KLB, LPB, MBB, MSB, NAB, OCB, SHB, SSB, STB, TCB, TPB, VAB, VBB, VIB, VPB |
| HNX | Other commercial joint-stock banks | BAB, NVB |
| UPCoM | Indirect state-majority joint-stock bank through PVN | PCB |
| UPCoM | Joint-stock bank with local Party-affiliated majority group | SGB |
| UPCoM | Other commercial joint-stock banks | ABB, PGB |

[verified] All 28 have joint-stock legal form in the live BasicInfor names. The gazette lists state stakes in BID, CTG and VCB of 76.73%, 64.46% and 74.80%, respectively, and 100% state ownership of PVN. PCB's disclosures show PVN holding 52%. SGB reports 65.26% for the HCMC Party Committee office and three affiliated companies as a group. [inferred] PCB is indirectly state-majority. The SGB majority reflects a separate affiliated group. “Other joint-stock” describes the residual legal-form bucket. MBB's disclosure identifies material state-linked stakes, so that bucket is unsuitable as a private-ownership dummy. Accessed 12:15–12:20. [Government Decision 2054/QĐ-TTg](https://congbaocdn.chinhphu.vn/180507251028987904/2026/11/6/470879-1793932002_v1_1793932231_signed.pdf) · [PCB listing disclosure, tables 5–6](https://owa.hnx.vn/ftp/PORTALNEW/HEADER_IMAGES/20260812/2.%20PVCB_Ban%20CBTT%20cong%20ty%20dai%20chung..pdf) · [PCB Q3 financial statements](https://www.pvcombank.com.vn/static/2026/BCTC/BCTC%20Hop%20nhat%20Q3%20Tieng%20anh.pdf) · [SGB shareholder disclosure](https://www.saigonbank.com.vn/files/File/Quan-He-Co-Dong/Cong-Bo-Thong-Tin/N2026/T01/TTCDSHVDL1PTSGB.pdf) · [MBB ownership disclosure, 30 October](https://webcdn.mbbank.com.vn/public/media/6f92add6-0525-4276-aa33-35926c6dc5c7.pdf)

## 2. Consolidated ratios from 2021 to the latest closed period

[verified] At 12:18:59 and 12:19:08, the SDK queried all 28 codes. Each call logged 27 HTTP 200 responses from [GetFinancialDataRatio](https://apigw.fiingroup.vn/FXPF/Corporate/GetFinancialDataRatio) and 27 from [GetFinancialDataIncomeStatement](https://apigw.fiingroup.vn/FXPF/Corporate/GetFinancialDataIncomeStatement). Quarterly parameters were years 2021–2026 and quarters [1,2,3,4]. Annual parameters were years 2021–2025 with quarters omitted. Both used consolidated and fields omitted, which the vendor documents as all fields. The quarterly feed stopped at Q3. Coverage counts unique ticker-periods, keeps zero as non-null and uses a fixed as-of roster, including banks' financial periods before exchange debut. [Vendor SDK docs](https://docs.fiinquant.vn/ham-va-cong-thuc/3.-phan-tich-co-ban-and-dinh-gia/3.2.-ham-chi-so-bao-cao-tai-chinh) · [Field coverage and latest-period counts](samples/bank_fields.csv)

| Frequency | Possible | Returned and unique | Observed by period |
|---|---:|---:|---|
| Quarterly, 2021 Q1–2026 Q3 | 644 (28 × 23) | 614 (95.34%) | 27 each quarter in 2021–2025, then 27, 24 and 23 in Q1, Q2 and Q3 2026 |
| Annual, FY2021–2025 | 140 (28 × 5) | 134 (95.71%) | 26 in FY2021, then 27 each year |

[verified] All 13 leaf fields follow. The CSV also covers ticker and period keys and the six mapping nodes, including the top-level ratios object.

| Leaf path under ratios | Quarterly non-null / 644 | Annual non-null / 140 |
|---|---:|---:|
| NetInterestIncome | 614 | 134 |
| AttributeToParentCompany | 614 | 134 |
| AssetQualityComponent.ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans (NPL) | 611 | 134 |
| AssetQualityComponent.LoanLossReservesToNPLs | 611 | 134 |
| LiquidityAndAssetsComponent.LDRPercentage | 614 | 134 |
| ProfitabilityComponent.NIM | 614 | 134 |
| GrowthComponent.AverageLoansGrowthPercentageYoY | 614 | 134 |
| GrowthComponent.AverageDepositGrowthPercentageYoY | 614 | 134 |
| GrowthComponent.InterestincomeGrowthPercentageYoY | 614 | 134 |
| ValuationRatios.BookValuePerShare | 614 | 134 |
| ValuationRatios.BasicEPS | 614 | 134 |
| ValuationRatios.PriceToBook | 614 | 134 |
| ValuationRatios.PriceToEarning | 614 | 134 |

[verified] **Requested metrics absent from the observed SDK return.** The two endpoints above yielded 614 × 4 (ticker/year/quarter/ratios) and 134 × 3 (ticker/year/ratios) SDK frames. The all-fields inventory omits cost of funds, deposit interest expense, yield on earning assets, group-2 loans, CASA, regulatory capital, equity/assets or its components, ROA, ROE, CIR and total assets. A VCB Q3 request for ROA, ROE, CASA, CostOfFunds, AverageCostOfFinancing, InterestExpense, InterestExpenseOnDeposits, YieldOnEarningAssets, AverageYieldOnEarningAssets, Group2Loans, CapitalAdequacyRatio, EquityToAssets, TotalEquity, TotalAssets and CostToIncomeRatio at 12:16:43 returned HTTP 200 from both endpoints and an empty 0 × 0 SDK frame. A positive control with ProfitabilityComponent.NIM at 12:20:41 returned one row with NIM. The documented get_financial_statement method was absent from the 0.1.73 runtime (hasattr was False at 12:16). These observations apply to the tested SDK and entitlement. FiinPro X separately documents COF, YOEA and CIR. NIM and net interest income alone cannot identify deposit interest expense. [FiinQuant statement method docs](https://docs.fiinquant.vn/ham-va-cong-thuc/3.-phan-tich-co-ban-and-dinh-gia/3.1.-bao-cao-tai-chinh) · [FiinPro X metric definitions](https://docs.fiinpro.com/english/methodology/calculating-financial-ratios-for-fiinpro-x/banking-ratios)

[verified] **Feed gaps.** PCB had zero annual or quarterly records. An explicit PCB Q3 call at 12:16:41 returned an empty 0 × 0 frame with no ratio or income-statement HTTP request on the observed transport. BAB, BVB, NAB and OCB also returned no Q3 rows in the batch. Individual retries at 12:16:30–12:16:38 made one HTTP 200 request to each of the ratio and income-statement endpoints above and likewise returned 0 × 0. PCB has a public Q3 filing and the external bank table covers the other four. Q3 was the latest elapsed calendar quarter, and Q1 was the latest quarter with all 27 SDK ratio-covered banks. [PCB filing](https://www.pvcombank.com.vn/static/2026/BCTC/BCTC%20Hop%20nhat%20Q3%20Tieng%20anh.pdf) · [External Q3 bank table](https://taichinh.com/ngan-hang)

## 3. Market coverage

[verified] Requested 1 January 2021–19 November 2026 for all 28 banks. Returned data span 4 January 2021–19 November 2026 on 1,465 distinct session dates. Ticker × timestamp keys were unique within each frame. Coverage counts non-null fields, including vendor-supplied zeros.

| SDK call and request time | Returned bank-days | Non-null coverage | Banks |
|---|---:|---|---:|
| Fetch_Trading_Data, unadjusted daily close, 12:18:04 | 39,376 | close 39,376 | 28/28 |
| MarketDepth.get_stock_valuation, 12:18:23 | 39,307 | pb 39,307 | 27/28 |
| PriceStatistics.get_foreign, Daily, 12:18:28 | 39,376 | foreignOwned, foreignCurrentRoom and foreignTotalRoom 39,376 each. percentForeignOwned and percentForeignTotalRoom 39,210 each. | 28/28 per field |

Price and foreign each observed 394 HTTP 200 POSTs to [GetTradingDataByMultiEntities](https://apigw.fiingroup.vn/FXMA/TradingData/GetTradingDataByMultiEntities). Valuation observed 27 HTTP 200 GETs to [GetValuation](https://apigw.fiingroup.vn/FXMA/MarketInDepth/valuation/GetValuation) and returned no PCB record. [Foreign ownership and room field definitions](https://docs.fiinquant.vn/ham-va-cong-thuc/1.-danh-muc-and-thong-tin-co-ban/1.5.-lay-du-lieu-room-ndtnn)


## 4. First test of retail rates and bank risk

[verified] Filtered the D-UNLOCK CSV to 12 months and online. The snapshot has nine such banks and eight listed matches after excluding Agribank. VietinBank has no 12-month online row in this CSV. Mapped HDBank→HDB, Sacombank→STB, VPBank→VPB, BIDV→BID, MB→MBB and Techcombank→TCB. File SHA-256 at 12:19 was 28aa05e96e55d3dfd43435df3158ccf6165c837fa187b3cc3d87fc98989a3494. NPL, loan-loss coverage and LDR use the consolidated FiinQuant Q3 fields in §2. For equity/assets, the 30 September external table returned 27 unique descending equity/assets ranks (HTTP 200, 12:19). Reverse the sign of those ranks so a larger value means more equity/assets, then re-rank within the matching banks. The table attributes the balance-sheet data to issuer filings via VNDirect. [Deposit snapshot](../D-UNLOCK/samples/deposit_rates_today.csv) · [Collection evidence](../D-UNLOCK/UNLOCK.md) · [Equity/assets table](https://taichinh.com/ngan-hang)

| Sample | NPL ρ (n) | Loan-loss coverage ρ (n) | LDR ρ (n) | Equity/assets ρ (n) |
|---|---:|---:|---:|---:|
| [verified] Literal CSV rows with rate + term attestation (ACB, HDB, STB, mixed amount tiers) | +1.000 (3) | −1.000 (3) | −1.000 (3) | −1.000 (3) |
| [verified] ACB and HDB rows, STB's VND 100m tier, VCB quote corroborated independently | +0.400 (4) | −0.400 (4) | −0.800 (4) | −0.400 (4) |
| [inferred] All CSV rows labeled online, as received, for audit sensitivity (ACB, BID, HDB, MBB, STB, TCB, VCB, VPB) | +0.548 (8) | −0.452 (8) | +0.095 (8) | −0.429 (8) |

[verified] **Rate evidence.** ACB's online schedule shows 5.20% for under VND 200m. D-UNLOCK's HDB row is 5.30% for ordinary online savings and the 19 November rate table corroborates the term and channel. The original HDB PDF returned HTTP 502 to the web reader on this pass. STB's official PDF part B.I shows the CSV's 7.00% applies at VND ≥500m, and gives 6.80% for VND 50m to under 500m. The VCB official HTML displayed a calculator with asterisks in the rate field. The consumer comparator independently lists VCB at 5.40% online for 12 months at VND 100m. The exact VPB PDF was inaccessible to the web reader, and the comparator labels the matching 6.70% as counter. BIDV's official page returned unresolved rate templates, MB's page displayed a calculator, and the TCB landing page did not confirm the CSV rate. Checked 12:15–12:18. [ACB](https://acb.com.vn/lai-suat-tien-gui) · [HDB source PDF](https://cdn.hdbank.com.vn/hdbank-file/document/20261910BIEULAISUATTIENGUIKHACHHANGCANHANKHCNWEBSITEF2TD_1792402278333.pdf) · [HDB corroboration](https://vietnambiz.vn/lai-suat-ngan-hang-hom-nay-1911-agribank-vietcombank-vietinbank-va-bidv-duy-tri-on-dinh-20261119956282.htm) · [STB PDF](https://www.sacombank.com.vn/content/dam/sacombank/files/cong-cu/lai-suat/tien-gui/khcn/SACOMBANK_LAISUATNIEMYETTAIQUAY_KHCN_VIE.pdf) · [VCB official page](https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/KHCN---Lai-suat) · [VCB and VPB comparison](https://taichinh.com/lai-suat) · [VPB CSV source](https://www.vpbank.com.vn/-/media/vpbank-latest/tai-lieu-bieu-mau/lai-suat-huy-dong/khcn/2026/2.-20261114-Phu-luc-BLS-niem-yet.pdf) · [BIDV](https://bidv.com.vn/vn/ca-nhan/cong-cu-tien-ich/lai-suat) · [MBB](https://www.mbbank.com.vn/ho-tro/bieu-lai-suat?tab=lai-suat-huy-dong) · [TCB](https://techcombank.com/cong-cu-tien-ich/bieu-phi-lai-suat)

[verified] **Computation.** Join by ticker, one row per bank. For each risk measure, take the Pearson correlation of average ranks on pairwise complete observations. SciPy reproduced every coefficient. [Aggregate output](samples/bank_correlations.csv)

~~~python
from scipy.stats import spearmanr

for metric in ("NPL", "Loan-loss coverage", "LDR", "Equity/assets"):
    pair = joined[["rate_pct", metric]].dropna()
    ranks = pair.rank(method="average")
    n = len(pair)
    rho = ranks.corr().iloc[0, 1]
    assert abs(rho - spearmanr(pair["rate_pct"], pair[metric]).statistic) < 1e-12
~~~

[verified] **2021–2026 panel sketch.** Of 644 bank-quarters, 611 have all three SDK risk ratios and 614 have LDR. Same-quarter price + NPL, price + coverage, price + LDR, and price + equity/assets each have **0 observed pairs** in the inspected inputs. FiinQuant returned zero COF values and the eight listed snapshot quotes' effective dates all fall in 2026 Q4, which has no closed-quarter ratios. The separate Q3-risk/Q4-rate match has 3, 4 or 8 pairs per metric under the respective samples above. A November quote has no historical panel interpretation.

[inferred] **Household and policy decisions.** The LDR sign changes with sample choice. Posted rates also reflect deposit tiers, funding mix and timing. A Vietnamese household choosing an online VND term deposit could compare offers at its actual balance and inspect dated bank metrics and deposit-insurance eligibility. An SBV disclosure pilot could standardize machine-readable rate histories with effective date, amount tier, channel and payout basis, plus public bank metrics with consistent definitions. Those histories would support testing lagged risk against both rates and deposit growth with bank and quarter effects.

## 5. Research and consumer tools

Publisher pages and public tools checked 12:12–12:20 Asia/Saigon.

- [verified] **Nguyễn Chí Đức, Nguyễn Minh Kiều and Hoàng Trọng (2012).** A 2003–2010 panel of 21 Vietnamese commercial banks examined implicit deposit rates and growth. Market discipline was weak and the estimated relationships were unclear. [HCMC Open University journal](https://journalofscience.ou.edu.vn/index.php/econ-vi/article/download/1127/911)
- [verified] **Tu D.Q. Le (2020).** Higher implicit deposit interest rates were associated with more liquidity and default risk, while the regulatory change was associated with lower rates. The rate divides total interest expenses by total deposits and cannot isolate uninsured deposits. [Cogent Economics & Finance article](https://www.econstor.eu/bitstream/10419/245310/1/10.1080-23322039.2020.1757801.pdf)
- [verified] **Asian Journal of Economics and Banking (2021).** A study of 19 Vietnamese listed banks over 2010–2019 found weak depositor discipline and greater sensitivity to macro indicators than bank-specific risk. [Journal abstract](https://old.ajeb.edu.vn/vi/article/hoat-dong-ngan-hang-viet-nam-nguoi-gui-tien-co-phai-la-kenh-giam-sat-hieu-qua)
- [verified] **Giang Phung and Michael Troege (2024).** After the 2008–2011 Vietnamese banking crisis and government prevention of bank failures, depositors remained responsive to rates and responded substantially less to bank risk. [Wiley article](https://onlinelibrary.wiley.com/doi/abs/10.1111/ecot.12409)
- [verified] **Taichinh.com directly overlaps.** Its Vietnamese consumer rate comparison displays NPL, loans/deposits and equity/assets on the same page, with missing values for some banks. Its linked bank table ranks 27 banks on individual indicators including NPL and loss coverage. The calculator filters by deposit amount, term, channel, region and payout method. [Rate comparison with health indicators](https://taichinh.com/lai-suat) · [Bank ranks](https://taichinh.com/ngan-hang) · [Calculator](https://taichinh.com/gui-tiet-kiem)
- [verified] **Adjacent tools.** ORA·tech's comparison returned rate history, source and channel filters, terms and receipt calculations. The FiinRatings results endpoint returned issuer and instrument credit ratings with dated outlooks. [ORA·tech](https://vn.ora-tech.vn/tai-chinh/lai-suat-ngan-hang) · [FiinRatings results](https://fiinratings.vn/vi/ket-qua-xep-hang/ket-qua-xep-hang-tin-nhiem.html)

[inferred] Both the generic research question and the basic household comparison already have close precedents. Standardized history and a reproducible disclosure audit offer a possible distinction. The pages inspected show individual risk indicators or issuer ratings and do not establish an exhaustive market-wide safety leaderboard.

## 6. Public use under the FiinQuant terms

[verified] The official terms page returned HTTP 200 at 12:19:50. It says “Có quyền tạo ra các sản phẩm phái sinh […] phải trích nguồn một cách phù hợp” (permission to create derived products with appropriate attribution). The same terms restrict transferring or disclosing the system and associated information to third parties, providing third-party services using the system, and republishing system information. [FiinQuant official terms](https://fiinquant.vn/Home/Privacy?isShowPolicy=True)

[inferred] Attributed static industry aggregates, coverage percentages, and sample-level correlations with n are the strongest candidates for public display under the derivative-product clause. The public terms give no explicit list of permitted aggregations and do not resolve whether this account authorizes a public interactive product serving FiinQuant-derived bank comparisons. Confirm the judge-facing use with FiinGroup. Keep bank-period histories and identifiable FiinQuant observations internal. For any authorized aggregate, attribute FiinGroup / FiinQuant, the period and the computation. Issuer filings and rate sheets have their own terms for bank-specific detail.

TinyFish spend for this task was USD 0. D-UNLOCK's prior automation IDs, steps and costs are in its [run log](../D-UNLOCK/samples/tinyfish_runs.csv). No raw FiinQuant financial or market rows were written to disk.
