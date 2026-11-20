# RateWatch — Câu hỏi giám khảo có thể xoáy sâu và câu trả lời (bản 20/11/2026 15:00)

Quy ước: mỗi câu có câu trả lời tiếng Việt và một câu tiếng Anh ngắn để nói khi Q&A bằng tiếng Anh.
Số nào có dấu (*) phải kiểm lại trên snapshot cuối trước 13:00 ngày 21/11 (vì pipeline còn chạy thêm).
Nguồn của từng số nằm trong các thư mục nghiên cứu ở C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\.

---

## A. Câu hỏi và người đọc (Dray: "Who decides what?")

**A1. Người đọc của các bạn là ai, họ quyết định gì trên màn hình này?**
Một hộ gia đình có một khoản tiền và một ngày cần dùng lại. Họ quyết định ba việc: kỳ hạn, ngân hàng và kênh (online hay tại quầy), và mỗi ngân hàng để bao nhiêu để nằm trong hạn mức bảo hiểm 350 triệu.
EN: "A household with a sum and a date they need it back. They choose the term, the bank and channel, and how much to keep at each bank under the 350-million cap."

**A2. Vì sao câu hỏi này quan trọng, ai chẳng biết xem bảng lãi suất?**
Bảng lãi suất không cho biết ba điều: trần 4,75% làm gãy đường lãi ở tháng thứ 6; tái tục chỉ có lợi khi lãi lần sau vượt một ngưỡng tính được; và hạn mức 350 triệu chỉ phủ 19,06% giá trị tiền gửi (đánh giá của NHNN). Tiền gửi dân cư là 11.434.266 tỷ đồng (NHNN, 8/2026), và mỗi lần đến hạn là một lần quyết định.
EN: "A rate table does not show the ceiling kink, the renewal break-even, or that the cap covers only 19% of deposit value."

**A3. Câu hỏi có lặp lại không (dashboard phải trả lời câu hỏi lặp lại)?**
Có. Biểu lãi suất thay đổi nhiều lần trong tháng; mỗi khoản gửi đến hạn là một lần quyết định lại. Pipeline đọc biểu hai lần mỗi ngày.

**A4. Mốc so sánh (benchmark) của các bạn là gì?**
Ba mốc: trần 4,75% theo QĐ 2411/QĐ-NHNN; phương án tốt nhất đã kiểm 2 nguồn ở các ngân hàng khác cho cùng kỳ hạn; và lãi thực sau CPI cùng kỳ.

**A5. Nỗi đau có đủ lớn không? Mỗi hộ chỉ thiệt vài triệu.**
Đúng, với từng hộ con số là vài triệu đến vài chục triệu đồng mỗi năm, và chúng tôi không nói quá. Quy mô nằm ở số lần quyết định: hàng chục triệu người gửi, mỗi lần đến hạn. Phía chính sách thì hai công cụ của NHNN (trần lãi suất và hạn mức bảo hiểm) đang có số đo cụ thể lần đầu.
EN: "Small per household, large in aggregate, and it measures two policy levers."

## B. Dữ liệu (Product: "real and well-sourced data")

**B1. Lấy lãi suất ở đâu, có hợp pháp không?**
Từ biểu lãi suất công khai trên trang và file PDF của từng ngân hàng, cộng một trang tổng hợp công khai làm nguồn đọc thứ hai. Chúng tôi đọc robots.txt từng tên miền, giãn cách ≥ 2 giây, không vượt captcha hay đăng nhập. Ngân hàng nào chặn (robots.txt cấm) thì bỏ qua và ghi rõ lý do.

**B2. Bao nhiêu ngân hàng? Có đủ không?**
Lần kiểm trước khi build: 24/33 ngân hàng, 319 dòng (*). 10 ngân hàng nhỏ chưa đọc được; màn hình liệt kê từng ngân hàng thiếu và lý do. Chúng tôi không nói "mọi ngân hàng".
EN: "24 of 33 banks at the last full check; the missing ones are listed with the reason."

**B3. Làm sao biết con số đọc được là đúng?**
Mỗi ô có nhãn: "Đã kiểm 2 nguồn" khi hai cách đọc độc lập khớp nhau (ví dụ PDF và trang tổng hợp), "1 nguồn", hoặc "Mâu thuẫn". Ô mâu thuẫn không đi vào phép tính. Ở lần kiểm trước khi build: 20% dòng đã kiểm 2 nguồn, 21% mâu thuẫn, 59% một nguồn (*). Tiêu đề và các con số chính chỉ dùng dòng đã kiểm 2 nguồn.

**B4. Các bạn có tự tính lại được ba con số không? (Dray: "Recompute three numbers by hand")**
Có, bằng máy tính cầm tay:
1. Hòa vốn OCB online: (1 + 6,30% × 12/12) / (1 + 6,00% × 6/12) − 1, nhân 12/6 → 6,4078%/năm.
2. Hòa vốn Sacombank tại quầy dưới 500 triệu: 12 tháng 5,40%, 6 tháng 5,70% → 4,9587%/năm.
3. Hạn mức 350.000.000 đ bao gồm cả gốc và lãi (TT 05/2026 Điều 3), nên gửi 12 tháng ở 6,30% thì gốc tối đa được bảo hiểm là 350.000.000 / 1,063 ≈ 329.257.000 đ.

**B5. Hai nguồn mâu thuẫn thì làm gì?**
Hiện cả hai giá trị và nhãn "Mâu thuẫn", không tự chọn. Ví dụ OCB tại quầy: trang ghi 5,90%/6,20% còn PDF của chính OCB ghi 5,73%/5,83% cho kỳ 6/12 tháng.

**B6. Lãi niêm yết khác lãi thật người ta được trả (khoản lớn được thương lượng)?**
Đúng, đây là giới hạn. Sản phẩm dùng lãi niêm yết công khai, ghi rõ trên trang phương pháp. Khoản lớn thường được lãi cao hơn niêm yết, nên kết quả của chúng tôi là mức sàn công khai.

**B7. Có lịch sử không, hay chỉ một ngày?**
NHNN không công bố lịch sử lãi suất theo từng ngân hàng, và trang ngân hàng chỉ có biểu hiện hành. Chúng tôi bắt đầu lưu từ 20/11/2026, hai lần mỗi ngày, có ngày hiệu lực và giờ đọc. Đó là lý do chúng tôi không dự báo. Kho lưu này là mục tiêu dài hạn: kho lịch sử lãi suất tiền gửi theo ngân hàng công khai đầu tiên.

**B8. Dữ liệu FiinQuant dùng thế nào, có được phép công khai không?**
FiinQuant cho chỉ số quý của 28 ngân hàng niêm yết từ 2021 (nợ xấu, dự phòng, LDR, ROA, NIM, tăng trưởng) và dữ liệu thị trường (P/B, biến động). Dữ liệu thô giữ nội bộ; trang web chỉ hiện chỉ số tổng hợp và thứ hạng phần trăm, ghi nguồn "FiinQuant (FiinGroup)". Chúng tôi đã hỏi mentor Đinh Xuân Phan Anh về quyền hiển thị (*cập nhật câu trả lời của anh ấy).

**B9. Bản đồ lấy số tiền gửi theo tỉnh ở đâu?**
Không có bảng chính thức tiền gửi theo tỉnh cho đủ 34 tỉnh, nên chúng tôi không vẽ số đó. Bản đồ dùng 2.477 điểm ngân hàng trên OpenStreetMap (ODbL), phủ 34/34 tỉnh, khớp được 33 mã ngân hàng; 22,5% điểm không khớp được mã nên để riêng, không đoán. Ranh giới GSO/OCHA COD-AB v02, có Hoàng Sa (Đà Nẵng) và Trường Sa (Khánh Hòa).

**B10. Dân số để tính trên 100.000 dân lấy ở đâu?**
Theo Nghị quyết 202/2025/QH15 (số dân 2024 theo hộ khẩu). Tổng là 113,6 triệu, cao hơn số thực tế khoảng 101,3 triệu của Cục Thống kê; chúng tôi ghi rõ chênh lệch này trên trang.

## C. Phương pháp (Product: "methods that suit the question")

**C1. Các bạn dùng mô hình gì?**
Không dùng mô hình hộp đen. Các phép tính: lãi đơn khi đáo hạn; lãi hòa vốn khi tái tục; giá trị tại ngày cần tiền (có tính tháng tiền nằm không kỳ hạn và rút trước hạn theo lãi không kỳ hạn); chia tiền theo hạn mức bảo hiểm; lãi thực theo Fisher. Mô hình dữ liệu là star schema theo Kimball. Dray khuyên "the simplest method that answers".

**C2. Sao không dự báo lãi suất?**
Vì chưa có chuỗi lịch sử theo ngân hàng; dự báo từ một ngày dữ liệu là không trung thực. Chúng tôi đưa lãi hòa vốn (phép tính trên biểu hôm nay) và kịch bản ±50 điểm cơ bản, có ghi "phép tính, không phải dự báo".
EN: "With one day of bank-level history, any forecast would be invented. We show a break-even and scenarios instead."

**C3. Lãi hòa vốn có phải là kỳ vọng của thị trường không?**
Không hẳn. Đó là mức lãi kỳ 6 tháng lần sau cần đạt để hai cách gửi bằng nhau. Biểu lãi của ngân hàng còn phản ánh nhu cầu vốn của chính ngân hàng, nên chúng tôi không gọi nó là dự báo.

**C4. Trần 4,75% "bóp méo" như thế nào, có bằng chứng không?**
Trên 8 ngân hàng đọc trực tiếp: 19/45 mức lãi kỳ 1–5 tháng nằm đúng 4,75%, không mức nào vượt. OCB online: 4,75% ở kỳ 5 tháng, 6,00% ở kỳ 6 tháng, chênh 1,25 điểm %. Màn hình chính sách tính lại số này trên mọi dòng đã kiểm (*).

**C5. Lãi cao hơn có đi cùng rủi ro cao hơn không?**
Chúng tôi chỉ trình bày ở dạng thăm dò: tương quan hạng (Spearman) giữa lãi niêm yết và các chỉ số rủi ro trên khoảng 25 ngân hàng niêm yết, ghi rõ n. Cỡ mẫu nhỏ và dữ liệu một ngày nên kết quả không đi vào phần ra quyết định.

**C6. Nợ xấu giảm có nghĩa ngân hàng tốt lên?**
Chưa chắc. Tỷ lệ có thể giảm vì thu hồi được nợ thật, vì xóa nợ bằng dự phòng, vì bán cho VAMC, vì cơ cấu nợ, hoặc vì tín dụng tăng nhanh làm mẫu số phình ra. Chúng tôi tính mức tăng của số tiền nợ xấu = (1 + tăng trưởng tín dụng) × (tỷ lệ kỳ này / tỷ lệ kỳ trước) − 1, và gắn cờ khi tỷ lệ giảm mà số tiền vẫn tăng. FiinQuant không có thuyết minh báo cáo tài chính, nên chưa tách được phần xóa nợ và phần bán cho VAMC.

**C7. Người gửi dưới 350 triệu có cần quan tâm sức khỏe ngân hàng không?**
Ít hơn: khoản trong hạn mức do Bảo hiểm tiền gửi chi trả. Hồ sơ ngân hàng quan trọng với phần vượt hạn mức, nên sản phẩm hiện nó ngay cạnh thẻ "Được bảo hiểm".

**C8. Chia tiền giữa các ngân hàng có tính lãi vào hạn mức không?**
Có. Hạn mức tính cả gốc và lãi, nên số gốc tối đa ở mỗi ngân hàng = 350.000.000 / (1 + lãi × kỳ hạn/12).

## D. Kỹ thuật dữ liệu (mentor Tasco: Ingestion → Storage → Transform → Serving)

**D1. Pipeline có chạy lại được không hay làm tay một lần?**
Chạy lại được theo lịch hai lần mỗi ngày. Mỗi lần chạy có mã run_id, chạy lại cùng run_id không tạo dữ liệu trùng (idempotent). Chỉ lấy phần mới theo watermark; ngân hàng có file biểu không đổi mã băm thì bỏ qua phần đọc. Có retry với backoff, có log số dòng, lỗi, thời gian và chi phí.

**D2. Giữ dữ liệu thô không?**
Có. Mỗi phản hồi HTTP hoặc kết quả TinyFish được lưu nguyên bản (bronze) kèm URL, giờ lấy, mã băm SHA-256, trạng thái robots.txt và giấy phép.

**D3. Mô hình dữ liệu tầng gold?**
Star schema: bảng chiều ngân hàng, kỳ hạn (có nhóm theo trần), kênh, ngày, nguồn; bảng sự kiện lãi niêm yết (lưu cả ngày hiệu lực trên biểu và giờ đọc, tức hai trục thời gian), chỉ số ngân hàng theo quý, thị trường theo ngày, thị trường tiền tệ theo ngày, vĩ mô theo tháng, tham số chính sách kèm điều luật.

**D4. Kiểm chất lượng thế nào? Có ví dụ bắt được lỗi không?**
Cổng chất lượng: kiểu dữ liệu, khoảng hợp lệ, kỳ dưới 6 tháng không vượt trần, quy tắc hai nguồn, độ mới, so phần với tổng, đối chiếu một giá trị biết trước, độ lệch số dòng so với lần trước. Ví dụ thật: cổng đối chiếu đã chặn snapshot vì bộ đọc xếp lãi online 6,30% của Sacombank vào cột tại quầy (đúng là 5,70%).
EN: "Our calibration gate blocked a publish when a parser put Sacombank's online 6.30% into the counter column."

**D5. Vì sao dùng TinyFish?**
Không trang ngân hàng nào có số ngay trong HTML; nhiều trang dựng bằng JavaScript. TinyFish là trình duyệt tự động đọc các trang đó. Kết quả TinyFish chỉ là một nguồn đọc; phải có nguồn thứ hai mới được nhãn "Đã kiểm 2 nguồn". Một lượt đủ khoảng 30 ngân hàng tốn khoảng 2,5–3 USD (*).

**D6. Phát hiện chính sách từ phía kỹ thuật dữ liệu?**
Không ngân hàng nào trong 33 công bố lãi suất ở dạng máy đọc được. Khuyến nghị: NHNN yêu cầu công bố biểu lãi suất theo một định dạng máy đọc được (CSV/JSON có ngày hiệu lực).

## E. AI (Dray: "trace every number", "say where AI helped", "keep private data out of the prompt")

**E1. AI làm gì trong sản phẩm?**
Trợ lý hiểu câu hỏi tiếng Việt/tiếng Anh, chọn công cụ tính toán của chúng tôi (tra lãi, lập kế hoạch, hòa vốn, chia theo hạn mức, hồ sơ ngân hàng, ngân hàng trong tỉnh, điều luật) và giải thích kết quả. Con số do công cụ tính trên snapshot đã kiểm, không do AI nghĩ ra.

**E2. Nếu AI bịa số thì sao?**
Lớp chặn số: mọi con số trong câu trả lời phải khớp kết quả công cụ, nếu không sẽ bị thay bằng "[chưa kiểm chứng]" và câu trả lời bị gắn cờ. Bộ 20 câu kiểm thử chạy tự động; kết quả ghi trên Langfuse (*điền tỷ lệ đạt).

**E3. Model nào, vì sao?**
GPT-6 Luna của OpenAI, gọi qua Langfuse AI Gateway (vùng Nhật), dự phòng Groq gpt-oss-120b. Chọn theo kết quả bộ kiểm thử: gọi đúng công cụ, không có số ngoài công cụ, tiếng Việt, tốc độ và chi phí.

**E4. Dữ liệu người dùng có bị gửi ra nước ngoài không?**
Trợ lý không cần và không hỏi tên, số tài khoản, CCCD hay số điện thoại; bộ lọc che các mẫu đó trước khi gửi model và trước khi ghi trace. Luật Bảo vệ dữ liệu cá nhân 91/2025 Điều 20 điều chỉnh việc chuyển dữ liệu cá nhân ra nước ngoài; chúng tôi không chuyển dữ liệu cá nhân. Không có link trace công khai vì link đó sẽ đăng prompt lên mạng.

**E5. Sao không cho chụp sổ tiết kiệm để AI đọc?**
Cố ý không làm. Ảnh sổ có tên, số tài khoản, số dư (dữ liệu tài chính khách hàng là dữ liệu nhạy cảm theo Nghị định 356/2025 Điều 4). Quyết định chỉ cần bốn trường gõ tay. Đúng nguyên tắc của buổi workshop: "keep private data out of the prompt and off public pages".

**E6. AI đã giúp đội ở đâu?**
Viết code theo brief do đội kiểm, đọc biểu lãi suất (TinyFish), tóm tắt văn bản pháp luật để đội đọc lại bản gốc, và trợ lý trong sản phẩm. Câu hỏi, cách chọn dữ liệu, quy tắc kiểm và khuyến nghị là của đội. Toàn bộ prompt nằm trong tài liệu nộp.

## F. Pháp lý

**F1. Đây có phải tư vấn đầu tư không, có cần giấy phép?**
So sánh tiền gửi không phải tư vấn đầu tư chứng khoán theo Luật Chứng khoán 54/2019 Điều 4 khoản 32. Màn hình ghi "Thông tin tham khảo"; người dùng tự quyết.

**F2. Hạn mức 350 triệu có đúng không, văn bản nào?**
Thông tư 05/2026/TT-NHNN Điều 3, hiệu lực 13/07/2026; QĐ 32/2021/QĐ-TTg (125 triệu) bị bãi bỏ cùng ngày theo Nghị định 280/2026 Điều 36. Phí bảo hiểm 0,15%/năm như nhau, ngân hàng trả (TT 04/2026).

**F3. Trần 4,75% còn hiệu lực không?**
QĐ 2411/QĐ-NHNN hiệu lực 20/11/2024: 0,5% dưới 1 tháng, 4,75% từ 1 đến dưới 6 tháng. Chúng tôi chưa tìm thấy quyết định thay thế, nhưng chưa thể loại trừ hoàn toàn (giới hạn ghi trên trang).

**F4. Bản đồ có đúng chủ quyền không?**
Dùng ranh giới GSO/OCHA COD-AB v02 có Hoàng Sa (Đà Nẵng) và Trường Sa (Khánh Hòa). Không dùng bản đồ nền bên ngoài.

## G. Chính sách và tầm nhìn

**G1. Khuyến nghị cho cơ quan quản lý là gì?**
1. Yêu cầu ngân hàng công bố biểu lãi suất ở dạng máy đọc được, có ngày hiệu lực.
2. Xem xét phí bảo hiểm tiền gửi theo mức rủi ro thay cho mức 0,15% như nhau.
3. Đánh giá lại trần 4,75% với người gửi ngắn hạn: số liệu cho thấy biểu lãi dồn ở trần và nhảy ở tháng thứ 6.

**G2. Sau cuộc thi sản phẩm đi đâu?**
Kho lịch sử lãi suất tiền gửi theo ngày, công khai, giấy phép CC-BY; mở rộng sang lãi vay và lãi thả nổi sau thời gian ưu đãi; API cho các bên nghiên cứu.

**G3. Ai trả chi phí vận hành?**
AWS khoảng 1–2 USD/ngày (ECS Fargate và cân bằng tải), TinyFish khoảng 5–6 USD/ngày cho hai lượt, model AI theo lượt dùng có giới hạn chi tiêu trên Langfuse.

## H. Làm việc nhóm (20 điểm)

**H1. Ai làm gì?** (*điền tên thật*) Dữ liệu và pipeline · phân tích và pháp lý · sản phẩm và UI · thuyết trình · một bạn chuyên "phá số" (tính lại các con số, thử nhập dữ liệu sai).
**H2. Đội có tranh luận gì không?** Đổi hướng ba lần dựa trên dữ liệu: bỏ dashboard vĩ mô (giống đội khác), bỏ hướng thuế hộ kinh doanh (không có dữ liệu quan sát), bỏ chênh lệch giá vàng và FTSE (đã có nhiều công cụ). Bỏ OCR vì lý do dữ liệu cá nhân.
