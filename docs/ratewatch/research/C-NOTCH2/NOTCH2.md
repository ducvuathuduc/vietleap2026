# C-NOTCH2 — Dữ liệu nào làm dày bằng chứng quanh vách 1 tỷ đồng

Ngày truy cập mọi nguồn dưới đây: 20/11/2026. [verified] = trang hoặc PDF được mở trong phiên này. [inferred] = bước không in trong nguồn. Không có con số nào dưới đây được bịa để lấp chỗ trống. Độ rộng khoảng doanh thu bị thua thiệt theo ngành nằm ở `../C-NOTCH/CRIT-NOTCH.md` và không tính lại ở đây.

Kết luận ngắn: có thể chỉ ra vách thuế bằng điều luật, có thể vẽ bản đồ cơ sở cá thể và một bảng theo dõi tuân thủ. Không thể đếm hộ nằm trong khoảng bị thua thiệt của từng ngành, và không thể ra một con số chi ngân sách cho việc chuyển GTGT sang chỉ tính phần vượt 1 tỷ. Bốn bin của cơ quan thuế quá rộng và không có doanh thu bình quân trong bin. gpinter và lognormal gắn vào các bin đó cho ra một đầu ra trông chính xác và không đứng được.

## 1. Phân phối theo nhóm — gpinter và lognormal đều thiếu đầu vào

gpinter (Blanchet–Fournier–Piketty) nội suy đường cong Pareto tổng quát bên trong từng khoảng. Đầu vào của một khoảng là ngưỡng, số người, và doanh thu bình quân (hoặc tổng doanh thu). Không có bình quân thì hệ số Pareto trong khoảng không xác định. Một lognormal hai tham số có thể khớp vào vài mốc phần trăm lũy kế, rồi mật độ ngay trên 1 tỷ vẫn trượt tự do trong một bin rộng 2 tỷ đồng. Khoảng bị thua thiệt trong CRIT-NOTCH chỉ dài khoảng 8–54 triệu đồng phía trên 1 tỷ, tức một lát mỏng ở mép trái của bin 1–3 tỷ. Không tính số hộ trong lát đó.

Mọi số đã công bố mà có thể đưa vào một phép nội suy, và vì sao từng số vẫn không đủ:

| Số | Nguồn, câu chữ, ngày | Dùng được vào việc gì |
| --- | --- | --- |
| Năm 2025: 2,7 triệu hộ, cá nhân kinh doanh doanh thu dưới 1 tỷ đồng/năm, hơn 96% số hộ đang nộp thuế. Từ 1 đến 3 tỷ: 2,84%. Trên 3 đến 10 tỷ: 0,73%. Trên 10 tỷ: khoảng 0,14%. | Tuổi Trẻ, 21/08/2026, lời bà Lan tại hội thảo, “theo số liệu cơ quan thuế”. [verified] https://tuoitre.vn/khi-nang-nguong-len-10-ti-dong-hon-99-ho-kinh-doanh-tinh-thue-theo-doanh-thu-100260821142425173.htm | Bốn phần trăm. Không có số hộ đúng của mẫu số, không có doanh thu bình quân, không tách ngành. “Hơn 96%” và “khoảng 0,14%” là số đã làm tròn. |
| “số hộ, cá nhân có doanh thu dưới 01 tỷ đồng là khoảng 2.556.042”. Giảm thu ngân sách khoảng 16.650 tỷ đồng so với năm 2025 (khoán, ngưỡng 100 triệu) và khoảng 4.850 tỷ đồng so với chính sách ngưỡng 500 triệu. | Cổng Chính phủ, bài 29/04/2026, “số liệu tính toán của cơ quan thuế”. [verified] https://baochinhphu.vn/chinh-thuc-nang-nguong-chiu-thue-voi-ho-kinh-doanh-len-01-ty-dong-nam-ap-dung-tu-1-1-2026-102260429185517215.htm | Một đầu mút dưới 1 tỷ, kèm chữ “khoảng”. Không có số hộ phía trên 1 tỷ và không có doanh thu. 4.850 và 16.650 là tiền thuế ước tính, không phải doanh thu trong bin. |
| Đến tháng 10/2025 có hơn 2,54 triệu hộ kinh doanh thường xuyên. Nếu ngưỡng miễn là 500 triệu thì khoảng 2,3 triệu hộ không phải nộp, khoảng 90%. | Cổng Chính phủ, bài 05/12/2025, công văn 18491/BTC-CST. [verified] https://xaydungchinhsach.chinhphu.vn/bo-tai-chinh-de-xuat-nang-nguong-doanh-thu-mien-thue-voi-ho-kinh-doanh-119251129123622906.htm | Một kịch bản ngưỡng 500 triệu. Không phải phân phối quanh 1 tỷ. |
| 7 tháng đầu năm 2025, hộ ổn định trên tổng 2,35 triệu: từ 200 triệu trở xuống khoảng 1,5 triệu hộ (65,7%), thuế phải nộp 2.410 tỷ đồng; trên 200 triệu đến 3 tỷ khoảng 791 nghìn (33,6%), 7.886 tỷ đồng; trên 3 tỷ đến 50 tỷ khoảng 12 nghìn (0,6%), 1.032 tỷ đồng; trên 50 tỷ 1.464 hộ (0,1%), 288 tỷ đồng. | Phần “số liệu 7 tháng đầu năm 2025” trong văn bản phương án được trang luật đăng kèm Quyết định 3389/QĐ-BTC năm 2025. [verified trên trang đó; PDF ký của quyết định chưa mở] https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Quyet-dinh-3389-QD-BTC-2025-phuong-phap-quan-ly-thue-ho-kinh-doanh-khi-xoa-bo-thue-khoan-676042.aspx | Có số hộ làm tròn và có tổng thuế, không có doanh thu. Bin “trên 200 triệu đến 3 tỷ” chứa cả phần dưới 1 tỷ và toàn bộ khoảng bị thua thiệt. Thuế ở đây là tổng thuế phải nộp, không tách GTGT. |
| Khảo sát VCCI: 36,3% hộ ghi nhận doanh thu dưới 500 triệu trong năm 2025; 51,4% từ 500 triệu đến dưới 3 tỷ; 12,3% từ 3 tỷ trở lên. Bán lẻ 90,1%. | VCCI, bài 19/05/2026, “theo kết quả khảo sát”. Trang không in cỡ mẫu. [verified] https://vcci.com.vn/news/suc-khoe-ho-kinh-doanh-suy-giam-phan-lon-chi-lai-mong-hoac-hoa-von | Đây là cơ cấu của nhóm được hỏi, không phải sổ thuế. 36,3% dưới 500 triệu không sống cùng “hơn 96% dưới 1 tỷ” của cơ quan thuế. Bỏ khỏi mọi phép nội suy dân số. |

Tổng điều tra không cứu được phép nội suy. Báo cáo sơ bộ in số cơ sở và lao động. Doanh thu thuần 45,3 triệu tỷ đồng năm 2025 trong báo cáo là doanh thu của doanh nghiệp (Biểu 09, trang 73). Không có biểu doanh thu của cơ sở cá thể. Trang 18 của cùng PDF nói nhiều chủ cơ sở ngại khai doanh thu, chi phí vì thời điểm điều tra trùng lúc cơ quan thuế xác định lại mức thu. [verified] PDF HTTP 200, 2.871.841 byte, khi gọi đúng href NFD trên trang công bố: https://www.nso.gov.vn/wp-content/uploads/2026/06/BC-CO%CC%82NG-BO%CC%82%CC%81-SO%CC%9B-BO%CC%A3%CC%82_Final.pdf . Cùng đường dẫn viết ở dạng NFC trả 404. Trang công bố, HTTP 200: https://www.nso.gov.vn/bai-top/2026/06/ket-qua-so-bo-tong-dieu-tra-kinh-te-nam-2026/

Đánh giá: một ước lượng “bao nhiêu hộ nằm trong khoảng bị thua thiệt của bán lẻ / ăn uống / dịch vụ” từ các số trên là quá mong manh để in. Sản phẩm dừng ở bốn bin và câu “bin 1–3 tỷ nuốt toàn bộ khoảng bị thua thiệt; chưa có doanh thu bình quân”.

## 2. Địa lý — có số cơ sở cá thể theo tỉnh và theo ngành, không có doanh thu

Hai lớp số, hai bản đồ hành chính khác nhau.

### Báo cáo sơ bộ Tổng điều tra kinh tế 2026 (số năm 2025, địa giới sau sắp xếp)

PDF 135 trang, HTTP 200, 2.871.841 byte. Mục lục đặt các biểu cá thể như sau:

- Biểu 10, trang 74. Số lượng cơ sở sản xuất kinh doanh cá thể phi nông, lâm nghiệp và thủy sản phân theo tình trạng đăng ký kinh doanh và theo địa phương. Đơn vị: cơ sở.
- Biểu 11, trang 78. Số lượng và lao động, phân theo ngành và theo địa phương.
- Biểu 12, trang 80. Số lượng cơ sở phân theo ngành kinh tế và theo địa phương.
- Biểu 13, trang 82. Lao động phân theo ngành và theo địa phương.

Ba dòng đầu của Biểu 10, trang 74. PDF ngăn cách hàng nghìn bằng dấu cách; dưới đây viết bằng dấu chấm. Cộng năm cột “chia ra” ra đúng cột tổng [inferred, phép cộng các số đã in]:

| Địa phương | Tổng số | Đã có giấy chứng nhận đăng ký kinh doanh | Chưa có giấy | Đã đăng ký, chưa được cấp giấy | Không phải đăng ký |
| --- | --- | --- | --- | --- | --- |
| Cả nước | 5.254.952 | 1.224.525 | 3.359.897 | 207.582 | 462.948 |
| Đồng bằng sông Hồng | 1.291.489 | 237.316 | 911.720 | 55.924 | 86.529 |
| Hà Nội | 365.427 | 85.287 | 226.346 | 16.552 | 37.242 |

Biểu 12, trang 80, cùng cách viết. Cột: tổng số, công nghiệp, xây dựng, vận tải kho bãi, thương mại, dịch vụ.

| Địa phương | Tổng số | Công nghiệp | Xây dựng | Vận tải, kho bãi | Thương mại | Dịch vụ |
| --- | --- | --- | --- | --- | --- | --- |
| Cả nước | 5.254.952 | 687.566 | 61.426 | 197.919 | 2.212.601 | 2.095.440 |
| Hà Nội | 365.427 | 67.951 | 5.724 | 11.472 | 153.661 | 126.619 |

Thương mại + vận tải + dịch vụ = 4.505.960 cơ sở, bằng 85,75% của 5.254.952. Công nghiệp + xây dựng = 748.992. Trang 48 viết “85,7%… 4,5 triệu” và “14,3% với 749,0 nghìn”. [verified câu chữ; phần trăm là phép chia từ biểu]

Đây là cơ sở cá thể phi nông nghiệp, không phải hộ đang nộp thuế. 5.254.952 không được cộng vào 2,7 triệu hay 2.556.042. Năm ngành của biểu không trùng bốn nhóm thuế suất GTGT: “dịch vụ” của tổng điều tra gộp ăn uống với dịch vụ chuyên môn, nên không gán suất 3% hay 5% lên cột đó.

### PXWeb — chuỗi 2015–2024, địa giới 63 tỉnh cũ

robots.txt cho phép `User-agent: *`. Metadata HTTP 200 ngày 20/11/2026:

- `V05.54.px` — Số cơ sở kinh tế cá thể phi nông nghiệp phân theo địa phương. Biến: Tỉnh/thành phố (70 mã, gồm cả nước và 6 vùng) và Năm 2015–2024. https://pxweb.nso.gov.vn/api/v1/vi/Doanh%20nghiệp/V05.54.px
- `V05.53.px` — cùng chỉ tiêu phân theo ngành kinh tế (20 ngành, năm 2015–2024). https://pxweb.nso.gov.vn/api/v1/vi/Doanh%20nghiệp/V05.53.px

POST JSON tới đúng URL metadata, `Content-Type: application/json`, HTTP 200, trả ô số. Ba dòng năm 2024 của V05.54 (mã năm `9` = 2024):

| Mã | Địa phương | Số cơ sở, 2024 |
| --- | --- | --- |
| 0 | Cả nước | 5.166.574 |
| 2 | Hà Nội | 356.918 |
| 55 | TP. Hồ Chí Minh | 430.571 |

Bốn dòng ngành, V05.53, năm 2024, cùng cả nước 5.166.574: công nghiệp và xây dựng 883.485; bán buôn, bán lẻ và sửa chữa ô tô, mô tô 2.349.196; vận tải, kho bãi 252.161; dịch vụ lưu trú và ăn uống 858.405. Bốn ngành này không cộng thành tổng, vì bảng còn các ngành khác.

Hà Nội 356.918 (2024, bản đồ cũ) và Hà Nội 365.427 (tổng điều tra 2025, bản đồ mới) không phải một chuỗi tăng. TP. Hồ Chí Minh 430.571 năm 2024 là địa giới trước khi nhập Bình Dương và Bà Rịa–Vũng Tàu; biểu 2025 ghi TP. Hồ Chí Minh 661.850 cơ sở. Sản phẩm để hai lớp cạnh nhau, có nhãn năm và nhãn bản đồ.

## 3. Người bán trên sàn — Nghị định 117 khấu trừ từng giao dịch, hoàn chỉ khi cả năm nằm dưới ngưỡng

Văn bản gốc: Công báo số 769+770, ngày 23/6/2025, PDF HTTP 200, 25 trang. https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2025/6/45045/56698-1-2025769-770117-2025-nd-cp.pdf — trang thư mục HTTP 200: https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-117-2025-nd-cp-45045.htm . Ban hành 09/06/2025, hiệu lực 01/07/2025, ký Hồ Đức Phớc. [verified]

Điều áp vào câu hỏi:

- Điều 2 khoản 1 và Điều 3 khoản 1: người khấu trừ, nộp thay là nhà quản lý sàn và nhà quản lý nền tảng số có chức năng thanh toán, kể cả giao hàng thu tiền hộ, cộng tổ chức chi trả thu nhập nội dung số thay nhà cung cấp nước ngoài.
- Điều 4: khấu trừ GTGT và TNCN trên từng giao dịch phát sinh doanh thu. Điều không viết ngưỡng 1 tỷ.
- Điều 5 khoản 1: khấu trừ ngay khi giao dịch thành công và được chấp nhận thanh toán.
- Điều 5 khoản 2: thuế = tỷ lệ % × doanh thu của giao dịch đó. GTGT: hàng hóa 1%, dịch vụ 5%, vận tải và dịch vụ gắn với hàng hóa 3%. TNCN người cư trú: 0,5%, 2%, 1,5%. Người không cư trú: 1%, 5%, 2%. Không tách được loại giao dịch thì lấy tỷ lệ cao nhất. Doanh thu giao dịch là số tiền người bán được hưởng mà nền tảng thu hộ.
- Điều 6: kê khai theo tháng; giao dịch hủy hoặc trả hàng được bù trừ.
- Điều 8: hộ, cá nhân trên nền tảng không có chức năng thanh toán tự kê khai, nộp thuế.
- Điều 10 khoản 1: đã bị khấu trừ cả năm mà doanh thu năm của toàn bộ hoạt động kinh doanh thuộc đối tượng không chịu GTGT và TNCN thì làm thủ tục hoàn số nộp thừa, sau khi nền tảng đã kê khai và nộp xong thuế khấu trừ của năm đó.
- Điều 10 khoản 3 và 4: hồ sơ là Mẫu 03/CNKD-TMĐT; nơi nhận là cơ quan thuế nơi cư trú.
- Điều 11 khoản 4: phần đã được khấu trừ và nộp thay thì không khai, nộp GTGT và TNCN lần thứ hai.
- Điều 12 khoản 4: Cục Thuế hướng dẫn đối chiếu để hoàn thuế tự động. Đó là nhiệm vụ của cơ quan, không phải câu “đã hoàn tự động”.
- Điều 13: hiệu lực 01/07/2025; văn bản được viện dẫn mà sửa đổi thì thực hiện theo văn bản sửa đổi.

Năm 2026, “không chịu GTGT, TNCN” là mức doanh thu Chính phủ đặt, tức từ 1 tỷ trở xuống theo Nghị định 68/2026 đã được Nghị định 141/2026 sửa (đã đọc ở CRIT-NOTCH). [inferred ở chỗ nối Điều 10 với ngưỡng 2026; Điều 10 không in chữ “1 tỷ”]

Hệ quả cho người bán năm 2026:

- Doanh thu cả năm của mọi hoạt động từ 1 tỷ trở xuống vẫn bị khấu trừ trên từng đơn đã thanh toán. Đường hoàn là hồ sơ 03/CNKD-TMĐT sau khi sàn quyết toán năm, không phải miễn ngay lúc trừ tiền.
- Doanh thu cả năm trên 1 tỷ thì Điều 10 không mở cửa hoàn khoản đã trừ trên phần doanh thu dưới 1 tỷ. Điều 11 khoản 4 chặn khai lại. GTGT bị trừ trên toàn bộ doanh thu sàn khớp với vách GTGT (thuế trên tổng doanh thu một khi đã vượt ngưỡng). TNCN bị trừ 0,5%/2%/1,5% trên toàn bộ doanh thu từng giao dịch. Luật TNCN hiện hành, ở phương pháp tỷ lệ, tính trên phần vượt ngưỡng (CRIT-NOTCH, Điều 7 khoản 3). Hai câu chữ đó chưa được một điều khoản nối lại trong Nghị định 117. Ghi khoảng trống, không kết luận thay cơ quan thuế.

Số người bán, mỗi số một quần thể:

| Số | Quần thể | Nguồn |
| --- | --- | --- |
| 2022: 85.438 hộ/cá nhân đã đăng ký, kê khai, nộp thuế TMĐT; 28.890 tổ chức; 42 nhà cung cấp nước ngoài. Doanh thu thị trường khoảng 16,4 tỷ USD. | Người nộp thuế đã vào sổ | Cục Thuế, bài 04/02/2026. [verified] https://gdt.gov.vn/wps/portal/?1dmy=&page=6_CQKCVKV008UPD0IMM7VUID00T7&urile=wcm%3Apath%3A%2Fgdt%2Bcontent%2Fsa_gdt%2Fsa_news%2Fsa_news_tax%2F2026%2Fthang%2B2%2F1f9a48f8-b0bc-451b-9f80-2c4d6a0aea96 |
| 2023: 88.147 hộ/cá nhân; 35.537 tổ chức; 75 nhà cung cấp nước ngoài. Khoảng 20,5 tỷ USD. | Cùng sổ | Cùng bài |
| 2024: 96.623 hộ/cá nhân; 45.959 tổ chức; 103 nhà cung cấp nước ngoài. Khoảng 25 tỷ USD. | Cùng sổ | Cùng bài |
| 2025: 1.277.000 hộ/cá nhân; 95.000 tổ chức; 202 nhà cung cấp nước ngoài. Khoảng 32 tỷ USD, tăng khoảng 28%. Thuế TMĐT gần 208,8 nghìn tỷ đồng, tăng 66,5% so với 2024. Trong đó hộ/cá nhân gần 4,63 nghìn tỷ đồng; 68 sàn kê khai thay gần 2,7 nghìn tỷ đồng; hơn 95 nghìn tổ chức 186,4 nghìn tỷ đồng; 202 nhà cung cấp nước ngoài 13,9 nghìn tỷ đồng. | Cùng sổ. Bước nhảy 96.623 lên 1.277.000 rơi vào năm Nghị định 117 có hiệu lực (01/07/2025). Đó là độ phủ đăng ký, chưa phải độ tăng của số shop. | Cùng bài |
| Hết tháng 10 (phiên chất vấn 12/11/2026): thu thuế TMĐT 241.000 tỷ đồng, tăng 42% so với cùng thời điểm. Doanh số TMĐT hết 2025 khoảng 37 tỷ USD. Cơ quan thuế đang quản lý hơn 140.000 doanh nghiệp và hơn 1 triệu hộ, cá nhân trên mạng. | Lời Bộ trưởng Bộ Tài chính Ngô Văn Tuấn. 37 tỷ USD và “hơn 1 triệu hộ” không trùng 32 tỷ USD và 1.277.000 hộ của bài Cục Thuế ngày 04/02/2026. Giữ cả hai, không lấy trung bình. | CafeF, HTTP 200. [verified] https://cafef.vn/co-quan-thue-dang-quan-ly-hon-1-trieu-ho-ca-nhan-kinh-doanh-tren-mang-18826111613522139.chn |
| Năm 2025: 601.780 shop có phát sinh đơn trên Shopee, TikTok Shop, Lazada và Tiki, giảm 7,43% so với năm trước. Doanh số bốn sàn 429,7 nghìn tỷ đồng, tăng 34,75%. | Shop có đơn, gồm cả doanh nghiệp và gian hàng mall. Không phải hộ cá nhân, không phải mã số thuế. | Metric, bài 28/01/2026. [verified] https://metric.vn/blog/cong-bo-bao-cao-thuong-mai-dien-tu-viet-nam-2025 |

Báo cáo sơ bộ tổng điều tra nói phạm vi có thêm cơ sở cá thể kinh doanh trực tuyến. Các Biểu 10–13 không có cột “trực tuyến”. Chưa có số cơ sở online trong bản sơ bộ này.

## 4. Chuỗi tuân thủ — đủ mốc để lập bảng, chưa đủ để nối một đường

Mỗi dòng là một thông cáo. Mẫu số và kiểu đếm đổi giữa các dòng.

Hóa đơn khởi tạo từ máy tính tiền, Cục Thuế qua Tạp chí Tài chính Doanh nghiệp, bài 29/12/2025. [verified] https://taichinhdoanhnghiep.net.vn/hon-203-ty-hoa-don-dien-tu-da-duoc-xu-ly-d63773.html

- Năm 2023: hơn 40,3 nghìn cơ sở, 104,8 triệu hóa đơn.
- Năm 2024: 52,7 nghìn cơ sở, hơn 1,26 tỷ hóa đơn.
- Năm 2025: hơn 252,7 nghìn cơ sở, hơn 3,4 tỷ hóa đơn.
- Lũy kế từ khi triển khai đến hết năm 2025: 345.744 cơ sở, 4,8 tỷ hóa đơn, trong đó hộ kinh doanh 178.388.

Ba mức theo năm cộng lại xấp xỉ tồn kho 345.744 trong cùng một bài, nên ba mức đó đọc được như lượng đăng ký trong năm của mọi loại cơ sở, và 178.388 là tồn kho hộ. [inferred ở chỗ gọi là “lượng trong năm”; bài không in hai chữ “phát sinh trong năm”]

Các mốc sau, tồn kho hộ:

- 30/04/2026: hơn 303.000 hộ, “tăng 50% so với cuối năm 2025”. Bộ Tài chính, qua TCDN 01/06/2026. [verified] https://taichinhdoanhnghiep.net.vn/hon-248-trieu-ho-kinh-doanh-su-dung-etax-mobile-d67155.html . Bản tiếng Anh của cùng cụm số viết “up 25 per cent”. [verified] https://vietnamnews.vn/economy/1782654/over-2-48-million-household-businesses-use-etax-mobile.html
- Cuối tháng 6/2026: 315.260 hộ, tăng 56% so với 31/12/2025. Báo Đấu thầu, 06/07/2026, dẫn Cục Thuế. [verified] https://baodauthau.vn/86-ho-ca-nhan-kinh-doanh-su-dung-etax-mobile-post202160.html
- “Trong 7 tháng”, bài Cổng Chính phủ 11/08/2026: 527.604 cơ sở, trong đó 205.769 doanh nghiệp và 321.835 hộ, “tăng 40% so với cuối năm 2025”. [verified] https://baochinhphu.vn/chuyen-doi-so-tiep-tuc-la-diem-sang-cua-nganh-thue-10226081815382699.htm

Lấy 178.388 làm mẫu số thì 315.260 là +76,7% và 321.835 là +80,4%, không phải +56% hay +40%. Lấy 345.744 làm mẫu số thì 527.604 là +52,6%, không phải +40%. “Hơn 303.000” trên 178.388 là hơn +70%, không phải +50% và không phải +25%. [inferred, chỉ là phép chia các số đã in] Sản phẩm in từng mốc kèm câu của từng thông cáo. Không vẽ một đường tăng trưởng từ các phần trăm đó.

eTax Mobile, số hộ:

| Mốc | Số hộ dùng | Mẫu số in kèm | Nguồn |
| --- | --- | --- | --- |
| Cuối 2025 | hơn 1,04 triệu | trên 91,5% số hộ thuộc diện nộp thuế | Bộ Tài chính, TCDN 01/06/2026, URL ở trên |
| 19/04/2026 | 2.390.420 | 3.082.983 hộ đang hoạt động, 78%. 2.390.420 / 3.082.983 = 77,5%, bài làm tròn 78%. | VTV, 29/04/2026, dẫn Cục Thuế. [verified] https://vtv.vn/hon-9-trieu-nguoi-chua-dung-etax-mobile-100260429092410373.htm |
| 02/05/2026 | 2.484.144 | 3.074.068 hộ đang hoạt động theo đăng ký thuế, khoảng 81%. Phép chia ra 80,8%. | Tạp chí Kinh tế Tài chính, bài 01/06/2026. [verified] https://thuehaiquan.tapchikinhtetaichinh.vn/ty-le-ho-kinh-doanh-ke-khai-thue-dien-tu-dat-986-157673.html |
| “đến nay” trong bài 06/07/2026 | 2,72 triệu | 86% số đang hoạt động | Báo Đấu thầu, URL ở trên |
| “hiện có” trong bài 14/11/2026 | hơn 3 triệu | 91,2% số hộ đang hoạt động theo địa điểm kinh doanh. Bài không in ngày chốt số. | Thời báo Tài chính, dẫn Cục Thuế. [verified] https://thoibaotaichinhvietnam.vn/nguoi-nop-thue-ngay-cang-chu-dong-trong-moi-truong-so-206892-206892.html |

Cùng bài 14/11/2026: eTax Mobile trên 16 triệu lượt tải; hơn 24,9 triệu giao dịch nộp qua ngân hàng; khoảng 45.000 tỷ đồng nộp thành công. Bài 11/08/2026 chốt tại 20/07/2026: hơn 16 triệu lượt sử dụng, gần 25 triệu giao dịch, 45.018 tỷ đồng. “Lượt” không phải “số hộ”.

Bài VTV 29/04/2026 còn một quần thể khác: hơn 13,3 triệu người nộp thuế là hộ, cá nhân kinh doanh và cá nhân có nghĩa vụ, khoảng 4,2 triệu người cài eTax Mobile (32%). Không nhập số này vào cột “hộ kinh doanh”.

Thuế đã kê khai của hộ, cá nhân (không phải số thu ngân sách):

- Đến 05/05/2026: 552.388 tờ khai 01/CNKD, 41.688 tờ khai 01/BĐS, 2.021.539 thông báo tài khoản. Bài 01/06/2026 không in số thuế của mốc này.
- Cuối tháng 6/2026: 647.983 tờ khai, 586.857 đúng hạn (98,1%), nộp điện tử 99,54%, thuế đã kê khai 5.859 tỷ đồng. Báo Đấu thầu.
- Bài 14/11/2026: 1,69 triệu tờ khai, 99,6% điện tử, 98,2% đúng hạn, thuế kê khai 9.767,8 tỷ đồng. Không in ngày chốt.

Thu ngân sách từ hộ, cá nhân kinh doanh:

- Năm 2024: 25.953 tỷ đồng, bằng 120% năm 2023. VnExpress 30/03/2025, dẫn Cục Thuế. [verified] https://vnexpress.net/ho-ca-nhan-kinh-doanh-nop-thue-gan-26-000-ty-dong-nam-ngoai-4867721.html . Bài còn viết “khoảng 5,2 triệu hộ” và “hơn 24% GDP”; hai số đó không có bảng kèm, dùng thận trọng.
- 7 tháng 2025, trong văn bản phương án ở mục 1: tổng thuế phải nộp của bốn bin là 2.410 + 7.886 + 1.032 + 288 = 11.616 tỷ đồng. Đó là thuế phải nộp của hộ ổn định, không phải số thu ngân sách cả nước đã công bố cho 7 tháng. [inferred ở phép cộng]
- VCCI 19/05/2026 viết “theo số liệu của Bộ Tài chính” thu hộ kinh doanh năm 2025 khoảng 32.840 tỷ đồng. Trang Bộ không được mở trong phiên này. Chưa đưa 32.840 lên sản phẩm.

Đủ điểm cho một bảng mốc có chú thích. Chưa đủ cho một chuỗi tháng hoặc quý liền mạch của cùng một chỉ tiêu.

## 5. Chi phí cải cách — công thức thì rõ, 4.850 và 16.650 trả lời câu khác

Với hộ trên 1 tỷ đang chịu GTGT theo tỷ lệ trên doanh thu, GTGT hiện tại = v × R. Nếu chỉ tính trên phần vượt 1 tỷ thì GTGT = v × (R − 1.000.000.000). Chênh mỗi hộ = v × 1.000.000.000. Chênh không phụ thuộc R. [inferred từ công thức Luật GTGT Điều 12 khoản 2, đã đọc ở CRIT-NOTCH; điều luật không in sẵn phép trừ này]

Chi ngân sách của việc chuyển sang căn cứ “phần vượt” là

Σ theo ngành (số hộ ngành đó có doanh thu trên 1 tỷ) × (tỷ lệ GTGT của ngành) × 1.000.000.000

Tỷ lệ v là số thật: 1%, 5%, 3%, 2% theo Luật GTGT; đến 31/12/2026 thì 0,8%, 4%, 2,4% với giao dịch được giảm 20% tỷ lệ theo Nghị định 174/2025. Số hộ theo ngành phía trên 1 tỷ không có trong bất kỳ bảng nào đã mở.

4.850 tỷ đồng và 16.650 tỷ đồng, bài Cổng Chính phủ 29/04/2026, là mức giảm thu ước tính khi nâng ngưỡng miễn lên 1 tỷ: 4.850 so với chính sách ngưỡng 500 triệu, 16.650 so với năm 2025 còn khoán và ngưỡng 100 triệu. Cả hai đều là tiền của nhóm dưới 1 tỷ, đều có chữ “khoảng”, và bài không tách GTGT khỏi TNCN. Cùng bài, miễn thuế thu nhập doanh nghiệp cho doanh nghiệp doanh thu không quá 1 tỷ là khoảng 2.164 tỷ đồng trên khoảng 235.800 doanh nghiệp — quần thể doanh nghiệp, để ngoài công thức hộ.

Bảng 7 tháng 2025 có thuế của nhóm trên 3 tỷ (1.032 tỷ và 288 tỷ) nhưng không tách GTGT và không có doanh thu, nên không thế vào công thức. Bin 200 triệu–3 tỷ thì nằm đè lên ngưỡng.

Sản phẩm có thể in công thức với ô N để trống, và in 4.850 / 16.650 ở một câu riêng: đó là chi phí của ngưỡng miễn đã ban hành, do cơ quan thuế ước tính.

## 6. Sản phẩm được phép hiện số nào

Hiện được, mỗi số kèm nguồn và quần thể:

- Độ rộng khoảng bị thua thiệt theo ngành, tính từ suất luật, như CRIT-NOTCH. Đó là cơ chế, không phải số hộ đã quan sát.
- Bốn bin 2025 của cơ quan thuế. Bin 1–3 tỷ dài 2 tỷ đồng và chứa toàn bộ khoảng bị thua thiệt đã tính trong CRIT-NOTCH (dài nhất khoảng 54 triệu đồng với dịch vụ, suất luật, chưa cộng bảo hiểm). Chú thích: chưa đo tụm dưới ngưỡng.
- Bản đồ 5.254.952 cơ sở cá thể năm 2025 theo tỉnh và năm ngành, từ Biểu 10 và Biểu 12. Nhãn: cơ sở phi nông nghiệp, không phải người nộp thuế, không có doanh thu.
- Ba ô PXWeb 2024 (cả nước 5.166.574, Hà Nội 356.918, TP. Hồ Chí Minh 430.571) và bốn ô ngành, nhãn bản đồ 63 tỉnh. API trả được chuỗi 2015–2024 nếu sản phẩm gọi tiếp.
- Bảng mốc eTax Mobile và hóa đơn máy tính tiền ở mục 4, mỗi mốc một chú thích mẫu số. Không nối các phần trăm tăng của thông cáo.
- Chuỗi người nộp thuế TMĐT 2022–2025 của Cục Thuế, với câu bước nhảy 2025 là năm khấu trừ tại sàn bắt đầu. 601.780 shop của Metric đứng ở một khung khác.
- Cơ chế sàn: bị trừ trên từng đơn kể cả khi cả năm dưới 1 tỷ; hoàn bằng mẫu 03 sau khi sàn nộp xong năm; phía trên 1 tỷ thì Điều 10 không hoàn phần đã trừ trên doanh thu dưới ngưỡng, và TNCN trên sàn chưa được viết thành “chỉ phần vượt”.
- Công thức chi phí “GTGT trên phần vượt”, ô số hộ để trống. 4.850 và 16.650 đứng ở câu về ngưỡng miễn đã chọn.

Phải để là giới hạn, không điền số:

- Số hộ trong khoảng bị thua thiệt của từng ngành, và mọi câu “có bao nhiêu người đang ngồi sát vách”.
- Bằng chứng tụm doanh thu ngay dưới 1 tỷ.
- Một con số duy nhất cho chi ngân sách của việc đổi GTGT sang phần vượt.
- Một đường thời gian duy nhất của tuân thủ hoặc của thu hộ từ 2024 đến 2026.
- Gộp 5,25 triệu cơ sở, 2,7 triệu hộ dưới 1 tỷ, 2,48 triệu người dùng eTax, 1,277 triệu hộ TMĐT và 601.780 shop thành một “quy mô thị trường”.
