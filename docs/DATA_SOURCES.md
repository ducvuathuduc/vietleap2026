# Danh mục nguồn của bộ theo dõi tài chính Việt Nam

Đối chiếu ngày 20/11/2026 với bản công bố 19/11/2026 lúc 23:55 (giờ Việt Nam). Số dòng dưới đây lấy từ `monitor.json`. Dòng quan sát chuẩn hóa, dòng báo cáo và mục tin có cơ sở đếm riêng. Điều khoản và trạng thái robots là ghi nhận tại lần lấy. Xem [điều kiện sử dụng](licenses.md).

Phân loại mentor gồm A cơ sở dữ liệu, B API, C tệp, D trang web, E nguồn bổ sung. TinyFish thuộc D. DuckDB dùng để lưu trữ. SQLite ở bộ minh họa là ví dụ cho A.

## Nguồn có dữ liệu trong bản công bố

| Nhà xuất bản và nguồn | Cách thu thập | Kỳ có dữ liệu và lịch cập nhật | Số dòng | Robots và điều khoản ghi nhận | Giới hạn |
| --- | --- | --- | ---: | --- | --- |
| [FiinGroup](https://docs.fiinquant.vn/) · Dữ liệu giao dịch và định giá FiinQuant | B · SDK | 21/11/2016–19/11/2026 tùy tập. Theo phiên hoặc quý, chạy CLI để cập nhật. | 1.968.368 | Thu thập qua SDK được cấp quyền. Điều khoản FiinGroup. Sản phẩm phái sinh cần ghi nguồn. | Số tổng hợp có ghi nguồn cần xác nhận quyền công bố. Giữ nội bộ bản thô, mẫu và Parquet. Danh mục mã hiện hành có thể bỏ sót mã đã rời sàn. |
| [World Bank](https://databank.worldbank.org/source/world-development-indicators) · Chỉ số phát triển thế giới | B · API, CSV lưu sẵn | 2000–2024 tùy nước, chỉ tiêu. Job WDI lúc 07:15 giờ Việt Nam hằng ngày, bộ theo dõi đọc CSV đã đặt sẵn. | 3.000 | API World Bank, phiên bản panel đã lưu. World Development Indicators, CC BY 4.0 trừ ngoại lệ của chỉ tiêu. | Một số chỉ tiêu tài khóa thiếu số Việt Nam. Năm và độ phủ thay đổi theo chỉ tiêu. |
| [Cục Thống kê](https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/) · Báo cáo tình hình kinh tế – xã hội hằng tháng | D · HTML tĩnh | Tháng 01/2024–10/2026. Theo công bố tháng, đọc lại hai kỳ cuối. | 948 | Robot được phép theo hồ sơ thu thập NSO. Công bố thống kê chính thức. Trích dẫn cơ quan và kỳ công bố. | Phân biệt tháng, lũy kế, cùng kỳ và % dự toán. Số tạm tính có thể được sửa. |
| [Ngân hàng Nhà nước Việt Nam](https://sbv.gov.vn/du-no-tin-dung-doi-voi-nen-kt-dttktt) · Dư nợ tín dụng theo ngành kinh tế | D · bảng HTML | Tháng 10/2025 và 08/2026. Theo công bố tín dụng, dùng --refresh để lấy lại. | 36 | Robot được phép theo hồ sơ thu thập SBV. Công bố thống kê chính thức. Trích dẫn Ngân hàng Nhà nước và cơ sở so sánh. | 18 dòng nguồn thành 36 dòng chuẩn hóa. Giữ nguyên cơ sở so sánh cuối năm trước. |
| [Bộ Tài chính / Báo Điện tử Chính phủ](https://bcp.cdnchinhphu.vn/334894974524682240/2026/11/3/908-261103-181630-1-17937095250521778197996.pdf) · Báo cáo 908/BC-BTC, Phụ lục Ia, giải ngân đầu tư công đến 31/10/2026 | C · PDF quét | Tháng 10/2026. Thay bản khi có phụ lục mới. | 133 | Robots trả 404 lúc lấy. Báo cáo công khai của Bộ Tài chính; trích dẫn Phụ lục Ia, trang PDF 35–36. | Phụ lục Ia có 34 tỉnh, thành phố và 33 cơ quan trung ương. Một ô số tiền là dấu gạch. |
| [Cổng thông tin đầu tư công](https://caa.gov.vn/hoat-dong-nganh/10-thang-giai-ngan-von-dau-tu-cong-cua-ca-nuoc-dat-741-ke-hoach-20261105113658123.htm) · 10 tháng giải ngân vốn đầu tư công cả nước đạt 74,1% kế hoạch | D · TinyFish | 10 tháng 2026. Theo bài công bố. | 22 | HTTP 200, nội dung robots chưa xác định. Cổng thông tin đầu tư công; trích dẫn số liệu, ghi nguồn. | Tỷ lệ và điểm phân nhóm có phạm vi công bố riêng. |
| [Nhà Đầu Tư](https://nhadautu.vn/von-fdi-dang-ky-cao-nhat-17-nam-d108659.html) · Vốn FDI đăng ký 10 tháng/2026 cao nhất 17 năm | D · TinyFish | 10 tháng 2026. Theo bài công bố. | 22 | Cho phép đường dẫn đã kiểm. Báo Nhà Đầu Tư; trích dẫn số liệu, ghi nguồn. | Chỉ có một nhóm tỉnh và đối tác. Năm dòng tỷ trọng thiếu bằng chứng trực tiếp. |
| [Realtique (tổng hợp CBRE)](https://www.realtique.net/vi/tin-tuc-vi/cap-nhat-thi-truong-vi/45638/gia-can-ho-tphcm-quy-3-2026/) · Giá căn hộ TP.HCM quý 3/2026 | D · TinyFish và bảng đối chiếu | Quý III/2026. Theo báo cáo quý có thể tiếp cận. | 34 | Cho phép đường dẫn đã kiểm. Realtique tổng hợp CBRE; dùng cho nghiên cứu, ghi nguồn. | Rổ TP.HCM mở rộng sang Bình Dương và Bà Rịa–Vũng Tàu. Dùng số tổng hợp cho nghiên cứu có trích dẫn Realtique và CBRE. |
| [TCBS Research](https://www.tcbs.com.vn/wp-content/uploads/2026/11/20261116_Banking_Sector_Earnings_Update_Q3_2026.pdf) · Cập nhật KQKD ngành ngân hàng Q3/2026 (TCBS) | C · bảng PDF | Quý III/2026. Theo báo cáo quý có thể tiếp cận. | 359 | Cho phép đường dẫn đã kiểm. TCBS Research, báo cáo công khai; dùng cho nghiên cứu cá nhân, ghi nguồn tcbs.com.vn. | Bảng trích có 26 ngân hàng. Nợ nhóm 2 lấy được ở cấp ngành. Dùng cho nghiên cứu có trích dẫn. |
| [The Investor](https://theinvestor.vn/credit-growth-slows-slips-in-first-half-of-october-d20264.html) · Tăng trưởng tín dụng chậm lại nửa đầu tháng 10/2026 | D · TinyFish | Tháng 10/2026. Theo bài công bố. | 3 | Cho phép đường dẫn đã kiểm. Báo điện tử The Investor; trích dẫn số liệu, ghi nguồn. | Ba quan sát của kỳ hiện có, chưa đủ dựng chuỗi tiền gửi. |
| [VnEconomy](https://vneconomy.vn/du-no-margin-giam-toc-trong-quy-3-dat-ky-luc-4575-nghin-ty-dong.htm) · Dư nợ margin giảm tốc trong quý 3, đạt kỷ lục 457,5 nghìn tỷ đồng | D · TinyFish | Quý III/2026. Theo bài công bố quý. | 6 | Cho phép đường dẫn đã kiểm. VnEconomy (FiinTrade); trích dẫn số liệu, ghi nguồn. | Thiếu mức dư nợ quý II/2026 cùng phạm vi để đánh giá BR-CM3. |
| [VnEconomy](https://vneconomy.vn/khoi-ngoai-ban-rong-gan-1-ty-usd-trong-thang-10.htm) · Khối ngoại bán ròng gần 1 tỷ USD trong tháng 10 (đối chiếu) | D · TinyFish | Tháng 10/2026. Khi có bài đối chiếu mới. | 2 | Cho phép đường dẫn đã kiểm. VnEconomy; dòng đối chiếu, nguồn chính là FiinQuant. | Hai quan sát dùng đối chiếu. Chuỗi giao dịch lấy từ FiinQuant. |
| [Quốc hội Việt Nam](https://vanban.chinhphu.vn/?docid=211922&pageid=27160) · Dự toán bổ sung có mục tiêu từ ngân sách trung ương | C · phụ lục nghị quyết | Năm 2024–2025. Khi Quốc hội công bố dự toán mới. | 504 | Tệp chụp phụ lục nghị quyết. Phụ lục số liệu của Nghị quyết 105/2023/QH15 và 160/2024/QH15. | Khoản bổ sung có mục tiêu theo dự toán. Cần quy đổi địa giới trước khi so sánh. |
| [VnExpress](https://vnexpress.net/rss/kinh-doanh.rss) · Tin kinh doanh · VnExpress | E · RSS | Tuần 47/2026. Cập nhật khi chạy phần báo chí. | 60 | Chưa lưu kết quả kiểm robots riêng cho feed. RSS công khai, chỉ dùng tiêu đề và tóm tắt. | Chỉ dùng đếm tin và tìm từ khóa. |
| [CafeF](https://cafef.vn/thi-truong-chung-khoan.rss) · Tin kinh doanh · CafeF | E · RSS | Tuần 47/2026. Cập nhật khi chạy phần báo chí. | 50 | Chưa lưu kết quả kiểm robots riêng cho feed. RSS công khai, chỉ dùng tiêu đề và tóm tắt. | Chỉ dùng đếm tin và tìm từ khóa. |
## Phạm vi FiinQuant lần lấy 19/11/2026

| Tập | Kỳ quan sát đã lưu | Số dòng hoạt động |
| --- | --- | ---: |
| Danh mục | 19/11/2026 | 1.547 |
| Giá và giao dịch | 21/11/2016–18/11/2026 tùy mã | 1.830.896 |
| Khối ngoại | 19/11/2021–19/11/2026 | 53.049 |
| Định giá | 19/11/2021–18/11/2026 | 81.525 |
| Tỷ số ngân hàng | Quý I/2021–quý III/2026 | 614 |
| Độ rộng nguồn | 19/11/2026 | 24 |
| Tỷ trọng VN30 | 19/11/2026 | 30 |
| Dòng tiền nhóm nhà đầu tư | 22/10/2026–18/11/2026 | 683 |

Đối chiếu các số dòng với bảng bronze trong bản công bố và phạm vi kỳ với hồ sơ lần lấy. Số dòng độ rộng Gold gồm kết quả dựng lại theo phiên từ dữ liệu giá. [Hướng dẫn FiinQuant](../tools/fiinquant/README.md)

## Nguồn tham chiếu và nguồn chưa có chỉ tiêu

- Savills thuộc D. TinyFetch lưu danh mục và trang báo cáo quý III/2026. Robots cho phép ở lần lấy. Bảng phân khúc đầy đủ yêu cầu đăng ký nên chưa có dòng chỉ tiêu. Kiểm tra lại theo báo cáo quý. [Danh mục](https://www.savills.com.vn/insight-and-opinion/) · [Báo cáo quý](https://www.savills.com.vn/research_articles/226576/239329-0)
- Cổng Bộ Tài chính thuộc D. Lần thử TinyFish dừng sau 240 giây, không có dòng chỉ tiêu. Nội dung robots chưa xác định. Theo dõi các công bố mới qua phụ lục chính thức. [Cổng Bộ Tài chính](https://www.mof.gov.vn/)
- HDX COD-AB thuộc C. Ranh giới dùng để hiển thị 34 tỉnh, thành phố, không tính vào số dòng chỉ tiêu. Cập nhật khi nguồn hoặc địa giới thay đổi. Quyền dùng và cách tải tệp ghi tại hồ sơ tài sản. [HDX COD-AB](https://data.humdata.org/dataset/cod-ab-vnm) · [Giấy phép bản đồ](../web/public/geo/LICENSE.md)
- SQLite minh họa thuộc A. Tệp cục bộ chỉ dùng để minh họa truy vấn chỉ đọc. Robots không áp dụng cho tệp cục bộ. Không có lịch lấy hoặc số dòng trong bản công bố. [Recipe minh họa](../scenarios/demo/sources.yaml)

## Kiểm tra khi cập nhật

Giữ HTML, PDF, phần trích và mã băm ở vùng nội bộ. Trình lấy báo chí ghi `sources_meta.csv` và `run_summary.json`, giữ cờ ở dòng thiếu bằng chứng. Bản chụp có 581 dòng báo chí cho các kỳ nêu trên. Đối chiếu cùng chỉ tiêu, kỳ, địa bàn, kiểu đo và đơn vị. Bản EDA có 861 mục chỉ có một nguồn. [Cách trích xuất báo chí](../tools/press/run.py) · [Job WDI](../.github/workflows/collect_data.yml)
