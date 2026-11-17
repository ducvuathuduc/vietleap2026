# Phân tích cuộc thi VietLeap Hackathon 2026 — "From Data to Decision"

*Soạn ngày 15/11/2026 (giờ VN). Mọi giờ trong file là giờ Việt Nam (ICT, UTC+7).*
*Ký hiệu: **[XÁC NHẬN]** = đọc trực tiếp từ nguồn chính thức · **[SUY RA]** = suy luận của tôi, chưa có nguồn nói thẳng · **[CHƯA XÁC NHẬN]** = chưa tìm được nguồn nào.*

---

## 0. Tóm tắt nhanh (đọc phần này nếu chỉ có 2 phút)

1. **Bạn đã vào Chung kết** (mail BTC 28/10/2026) và được **mời làm Trưởng nhóm**. **Đội do BTC ghép ngẫu nhiên lúc 09:00 ngày 20/11** ("Challenge Briefing + Team Formation") → bạn sẽ không chọn được đồng đội; phần lớn khả năng là sinh viên **khối Kinh doanh / Khoa học xã hội** (đối tượng tuyển chính thức) → nhiều người không code.
2. **Giám khảo thiên kinh tế học / chính sách công**: UEH Khoa Tài chính công (chủ nhà), AVSE Economic Policy Network, Sacha Dray (World Bank – chính sách tài khoá, thuế), Viet Nguyen-Tien (LSE – kinh tế năng lượng, xe điện, công nghệ số), cùng giảng viên Western Sydney, Coventry, Roehampton và FiinGroup. → Họ sẽ chấm **câu hỏi chính sách + bằng chứng + giới hạn** nặng hơn độ "kỹ thuật" của pipeline.
3. **Giải thưởng chính thức: "tổng hơn 20 triệu VNĐ"**. Con số "giải nhất 25 triệu" **không tìm thấy trong nguồn chính thức nào** → [CHƯA XÁC NHẬN]. Có 2 "competition track": *Data & Analytics* và *Presentation*.
4. **Không tìm thấy tiêu chí chấm chính thức** (web, UEH, Facebook, Gmail đều không có) → tiêu chí ở mục 3 là suy ra. Nên hỏi BTC trên nhóm Zalo trước 19/11.
5. Thời gian thi thật (agenda vietleap2026.com, 17/11): **09:00 20/11 (Challenge Briefing) → 13:00 21/11**; hacking bắt đầu sau workshop Dashboard (10:15). Pitch 13:15–15:15 (120 phút cho mọi đội; độ dài mỗi đội [CHƯA XÁC NHẬN]).
6. Đề có khả năng cao nhất (suy ra): **tài chính công / chính sách kinh tế cấp tỉnh hoặc quốc gia**, kế đến **dữ liệu doanh nghiệp niêm yết (FiinGroup)** và **chỉ số phát triển (World Bank)**. Đề giao thông/CV xếp thấp hơn mức kit đang đầu tư (Chi‑Yu Lee là nhà thần kinh học, Tasco chỉ dạy workshop DE chung).
7. Kit thiếu: **pack "mobility/Tasco"**, kịch bản pitch **tiếng Anh** (giám khảo và diễn giả nước ngoài; ngôn ngữ pitch [CHƯA XÁC NHẬN]), và **gói dữ liệu offline** cho các nguồn mở.

---

## 1. Dữ kiện đã kiểm chứng (kèm nguồn)

### 1.1 Nguồn đã dùng
| # | Nguồn | URL / vị trí |
|---|---|---|
| S1 | Website chính thức | https://vietleap2026.com/ |
| S2 | Bài đăng UEH – Khoa Tài chính công (10/10/2026) | https://spf.ueh.edu.vn/vietleap-hackathon-from-data-to-decision-2026/ |
| S3 | Mail BTC "[VIETLEAP HACKATHON 2026][MAIL THÔNG BÁO KẾT QUẢ]" 28/10/2026 21:56, từ vietleap2026@gmail.com, CC ynhn@ueh.edu.vn, gửi tới dieuthanhvn1006@gmail.com + địa chỉ fpt.edu.vn của bạn; đính kèm "VietLeap Hackathon 2026.pdf" (agenda) | Gmail dieuthanhvn1006@gmail.com |
| S4 | Poster workshop 16/11 (Lưu Đức Cảnh – Tasco) | Ảnh người dùng tải lên: `/workspace/projects/ff097594-b928-4965-8d98-f3f2e267b034/files/uploads/image-a1e217c39b61.webp` |
| S5 | Poster agenda (giống file PDF trong S3) | `/workspace/projects/ff097594-b928-4965-8d98-f3f2e267b034/files/uploads/image-48c084af359e.webp` |
| S6 | Facebook VietLeap – giới thiệu Chi‑Yu Lee (01/11/2026) | https://www.facebook.com/VietIeap/posts/122113357916598408 |
| S7 | Instagram VietLeap – đếm ngược hạn nộp (09/10/2026) | https://www.instagram.com/p/DeTa79Tv2uD |
| S8 | Facebook/Instagram – công bố đối tác FiinGroup | https://www.instagram.com/p/De_6T6HvVOm ; https://www.facebook.com/VietIeap/posts/122113047578598408 |
| S9 | Trang LSE – Viet Nguyen-Tien | https://www.lse.ac.uk/people/viet-nguyen-tien ; https://cep.lse.ac.uk/_new/people/person.asp?id=10783 |
| S10 | Trang cá nhân + World Bank blog – Sacha Dray | https://www.sachadray.com/ ; https://blogs.worldbank.org/en/team/s/sacha-dray |
| S11 | LinkedIn Lưu Đức Cảnh | https://linkedin.com/in/canhld0304 |
| S12 | Tasco – mảng cốt lõi (VETC, Tasco Auto) | https://www.tasco.com.vn/core-business |

### 1.2 Bảng dữ kiện
| Dữ kiện | Trạng thái | Nguồn |
|---|---|---|
| Tên: VietLeap Hackathon: From Data to Decision 2026; 19–21/11/2026, TP.HCM, "2.5 ngày" | [XÁC NHẬN] | S1, S2 |
| Đơn vị tổ chức: Khoa Tài chính công, Trường Kinh tế, Luật & Quản lý nhà nước, UEH. Đồng tổ chức: VietLeap (Vietnam Initiative for Emerging Talents…) và AVSE Global – Economic Policy Network. Tài trợ: Goodenough College / Goodstart Fellow. Đối tác: FiinGroup. Hỗ trợ: Đoàn–Hội khoa TCC, APPLE Club | [XÁC NHẬN] | S1, S2, S3 |
| Poster 16/11 còn có thêm logo "RAF" và APPLE trong mục Partner | [XÁC NHẬN] (logo) – vai trò RAF [CHƯA XÁC NHẬN] | S4 |
| Bối cảnh chính sách: Nghị quyết 57‑NQ/TW (dữ liệu là tư liệu sản xuất chính, kinh tế dữ liệu) | [XÁC NHẬN] | S2 |
| Đối tượng: sinh viên **khối Kinh doanh và Khoa học xã hội** của UEH và các ĐH/CĐ tại VN | [XÁC NHẬN] | S2 |
| Hồ sơ: CV + động lực + **bài kiểm tra kỹ năng**; "sinh viên sẽ được chia đội ở vòng chung kết" | [XÁC NHẬN] | S2 |
| Bài test đầu vào có phần tự thu thập Google Trends & ghi nguồn | [SUY RA] – chỉ có trong `docs/CONTEXT.md` của repo, không có nguồn công khai | repo |
| Hạn nộp hồ sơ: 17/10 (UEH) nhưng Facebook/IG sau đó ghi gia hạn tới **28/10/2026 20:30** | [XÁC NHẬN] (hai mốc khác nhau – có gia hạn) | S2, S8 |
| Kết quả: bạn **vào Chung kết**, được **mời làm Trưởng nhóm** (trả lời Câu 12 form: "Yes, I am willing to take the role") | [XÁC NHẬN] | S3 |
| Xác nhận tham gia: trả lời mail theo cú pháp "TÊN – XÁC NHẬN THAM GIA" **trước 07/11/2026** + điền Google Form https://forms.gle/nW8XHXnRCdVNgSU57 ; nhóm Zalo https://zalo.me/g/jn1k29vh1xuqfdacsr42 | [XÁC NHẬN] | S3 |
| Bạn đã gửi mail xác nhận chưa? | **[CHƯA XÁC NHẬN]** – Hộp thư Đã gửi của dieuthanhvn1006@gmail.com **không có** mail xác nhận nào (có thể đã xác nhận qua form/địa chỉ fpt.edu.vn). Cần tự kiểm tra | Gmail |
| Đồng ý chụp ảnh/ghi hình khi xác nhận | [XÁC NHẬN] | S3 |
| Miễn phí 100%; ăn uống; hỗ trợ đi lại + chỗ ở cho người ngoài TP.HCM; check-in "UEH Green Living Hub" (ký túc xá) | [XÁC NHẬN] | S1, S3 |
| Địa điểm workshop & chung kết: **Cơ sở N của UEH** | [XÁC NHẬN] | S2 |
| Giải thưởng: **"tổng giá trị hơn 20 triệu VNĐ"** + chứng nhận + quà | [XÁC NHẬN] | S1, S2 |
| Giải nhất 25.000.000 VNĐ | **[CHƯA XÁC NHẬN]** – chỉ thấy trong `docs/CONTEXT.md`/brief; không nguồn chính thức nào nêu | — |
| 2 competition track: **Data & Analytics** ("dashboards and data pipelines that turn raw data into actionable insights") và **Presentation** ("turn technical findings into a narrative…") | [XÁC NHẬN] | S1 |
| Có giải riêng cho từng track hay chỉ là hai mặt của một bài? | [CHƯA XÁC NHẬN] | — |
| "48h+ Learn & Build", "15+ Professionals" | [XÁC NHẬN] (số marketing) | S1 |
| Mentor & giám khảo gồm chuyên gia từ **UEH, Western Sydney University, Coventry University, University of Roehampton, FiinGroup** "và các tổ chức khác" | [XÁC NHẬN] | S1 |
| Danh sách tên giám khảo cụ thể | [CHƯA XÁC NHẬN] | — |
| Mentor hỗ trợ "trực tiếp tại chỗ và từ xa" | [XÁC NHẬN] | S2 |
| Tiêu chí chấm điểm chính thức | **[CHƯA XÁC NHẬN]** – không có ở web, UEH, FB, mail | — |
| Độ dài pitch mỗi đội (7 phút?) / số đội | [CHƯA XÁC NHẬN]. Khung pitch 13:15–15:15 = 120 phút | S3, S5 |
| Ngôn ngữ đề / pitch (Việt hay Anh) | [CHƯA XÁC NHẬN]. Mail/website song ngữ; diễn giả & giám khảo có người nước ngoài → [SUY RA] nên sẵn sàng pitch tiếng Anh | S1, S3 |
| Ban tổ chức có cấp dữ liệu (FiinGroup) hay đội tự thu thập? | [CHƯA XÁC NHẬN]. Bài FB: "cơ hội làm việc với các công cụ thực tế" → [SUY RA] có thể có quyền truy cập công cụ/dữ liệu FiinGroup | S8 |
| Lần tổ chức đầu tiên? | [SUY RA] Đây là lần đầu – không thấy kỳ trước. Lưu ý **"VietLeap AI Accelerator"** (NIC/BambuUP, Hà Nội) là chương trình **khác, chỉ trùng tên** | tìm kiếm web |

### 1.3 Lịch chính thức — agenda hiện hành trên vietleap2026.com (đọc 17/11/2026; trang sửa 17/11 ~18:55) [XÁC NHẬN]
Nguồn: https://vietleap2026.com/ (agenda trong site, đọc ngày 17/11/2026). Lịch này **thay thế** agenda PDF trong mail (S3) / poster (S5):
talk LSE chuyển từ 20/11 10:00 sang **19/11 15:30**, workshop Dashboard từ 11:00 sang **09:30**, mentor check‑in #1 từ 17:15 sang **16:00**, trao giải từ 16:00 sang **15:45**.

| Ngày | Giờ | Nội dung |
|---|---|---|
| **16/11 (Thứ Hai)** | 19:00, online | Workshop "Hướng dẫn xây dựng luồng dữ liệu & dashboard chuyên nghiệp" – **Lưu Đức Cảnh, Data Engineer, Tasco** (đã diễn ra; theo agenda PDF S3/S5): 4 giai đoạn Ingestion–Storage–Transform–Serving; nguồn Database/JDBC, Public API, file, Web scraping, Social listening; làm sạch missing/duplicate/outlier; chọn mô hình **OBT / Star / Snowflake / Data Vault** (S4) |
| **19/11** | 09:00–11:30 và 13:30–14:45 | Check‑in UEH Green Living Hub |
| | **14:45–15:30** | Workshop "From observation to data – Object tracking" – **Chi‑Yu Lee, ĐH Konstanz** |
| | **15:30–16:15** | **"Data to Decision" – Viet Nguyen‑Tien, LSE** (tên talk trên site: *Combining Data for Socioeconomic Development*) |
| | 16:15–16:45 | Họp online với mentors |
| | 16:45–17:30 | Ăn tối |
| | 18:30–20:15 | Bus tour (tự chọn) |
| **20/11** | **09:00–09:30** | **Khai mạc + Challenge Briefing + ghép đội** |
| | **09:30–10:15** | **Workshop Dashboard – Sacha Dray, World Bank Việt Nam** |
| | 10:15–11:30 | Hacking |
| | 11:30–13:00 | Ăn trưa |
| | 13:00–16:00 | Hacking |
| | **16:00–16:30** | **Mentor check‑in #1** |
| | 16:30–17:30 | Hacking |
| | 17:30–19:00 | Ăn tối |
| | từ 19:00 | Hacking xuyên đêm |
| **21/11** | 09:00–10:30 | Hacking |
| | **10:30–11:00** | **Mentor check‑in #2** |
| | 11:00–12:00 | Ăn trưa |
| | 12:00–13:00 | Nước rút |
| | **13:00–13:15** | **Hạn nộp bài** |
| | **13:15–15:15** | **Pitch + Q&A** |
| | 15:45–16:45 | Trao giải |
| | 17:00–21:00 | Gala |

Mentor/giám khảo liệt kê trên vietleap2026.com (17/11): Nguyễn Phúc Cảnh (UEH), Nguyễn Tiến Việt (LSE), Nguyễn Văn Phúc (WSU), Đặng Hoàng Nhật Tâm (UEH),
Nguyễn Trí Dũng (Coventry), Karan Vishwanath (Leicester), Lê Minh Phương (VinUni), Lưu Đức Cảnh (Tasco), Đinh Xuân Phan Anh (FiinGroup).
Site **không** đăng rubric, thể lệ, FAQ, chính sách AI/dữ liệu, định dạng nộp, thời lượng pitch hay ngôn ngữ — vẫn [CHƯA XÁC NHẬN].

Ghi chú: 16/11/2026 là **Thứ Hai**.

### 1.4 Hồ sơ diễn giả
| Người | Thực tế | Trạng thái |
|---|---|---|
| **Chi‑Yu Lee** (Konstanz) | Nhà **thần kinh học**, nghiên cứu cách não điều khiển **hành vi tập thể ở động vật**; làm trọn vòng: công cụ → thí nghiệm → thu & phân tích dữ liệu. Đồng thời là **một người tổ chức** (Organizer). Thông điệp: "dũng cảm phản biện đồng thuận khoa học", "đừng ngợp bởi dữ liệu – tìm câu chuyện đằng sau con số" | [XÁC NHẬN] S6 |
| **Viet Nguyen‑Tien** (LSE) | Research Officer, Centre for Economic Performance; kinh tế môi trường, **năng lượng, xe điện (EV), công nghệ số – năng suất**, đổi mới; từng nghiên cứu **mất điện & hiệu quả DN Việt Nam** (dữ liệu World Bank Enterprise Survey), tuổi thọ EV từ 300 triệu bản ghi MOT UK (survival analysis) | [XÁC NHẬN] S9 |
| **Sacha Dray** (World Bank VN) | Economist, Economic Policy Unit for Viet Nam: **vĩ mô, thương mại, tài khoá, thuế, tuân thủ chính sách**; đồng tác giả Viet Nam Taking Stock / Economic Update; Visiting Fellow LSE | [XÁC NHẬN] S10 |
| **Lưu Đức Cảnh** (Tasco) | Data Engineer tại Tasco JSC từ 05/2024, ~7 năm kinh nghiệm DS/DE | [XÁC NHẬN] S11, S4 |
| **Tasco** | Hai mảng lõi: **VETC** (thu phí không dừng, ~75% thị phần ETC, 136 trạm/765 làn) và **Tasco Auto** (phân phối ô tô), cùng bảo hiểm, tài chính | [XÁC NHẬN] S12 |

---

## 2. Tổ chức – đối tác – giám khảo: họ coi trọng gì, và đề có thể ra

### 2.1 Mỗi bên có thể coi trọng gì [SUY RA]
| Bên | Có thể coi trọng | Hệ quả cho đội |
|---|---|---|
| **UEH Khoa Tài chính công** (chủ nhà, viết đề khả năng cao) | Ngân sách, thuế, đầu tư công, phân cấp tỉnh; lập luận chính sách theo NQ 57; ngôn ngữ khuyến nghị chính sách | Khuyến nghị phải có **chủ thể ra quyết định là cơ quan nhà nước** (Bộ TC, UBND tỉnh…) |
| **AVSE Economic Policy Network** | Phân tích dựa trên bằng chứng nối nhà nghiên cứu – nhà hoạch định | Phân biệt **tương quan vs nhân quả**, có slide giới hạn |
| **World Bank (Sacha Dray)** – dạy dashboard | Chỉ số phát triển, so sánh quốc tế/ASEAN, tài khoá, thương mại, năng suất; dashboard **ít mà rõ, có nguồn** | Dashboard 1 trang, mỗi biểu đồ trả lời 1 câu hỏi, ghi nguồn + năm dưới mỗi biểu đồ |
| **LSE (Viet Nguyen‑Tien)** – "Data to Decision / Combining Data for Socioeconomic Development" (19/11 15:30) | Giá trị của dữ liệu, dữ liệu thay thế/dữ liệu lớn hành chính, năng lượng/EV/chuyển đổi xanh, công nghệ số & năng suất | Ghi điểm nếu **kết hợp nguồn dữ liệu phi truyền thống** (Google Trends, scrape, API) với số liệu chính thức |
| **FiinGroup** (đối tác dữ liệu, có thể là giám khảo) | Dữ liệu doanh nghiệp/ngành/thị trường vốn VN, chất lượng & chuẩn hoá dữ liệu | Nếu đề có dữ liệu DN: dùng đúng chỉ số tài chính (ROE, ROA, đòn bẩy), chú ý ngành tài chính tách riêng |
| **Tasco (Lưu Đức Cảnh)** – chỉ dạy workshop online | Quy trình DE chuyên nghiệp 4 giai đoạn; mô hình dữ liệu phù hợp quy mô | Dùng đúng thuật ngữ workshop trong pitch; **không** chọn Data Vault cho hackathon trừ khi giải thích được |
| **Chi‑Yu Lee** (CV, nhà tổ chức) | Từ quan sát → dữ liệu; tư duy khoa học, phản biện, kể chuyện từ dữ liệu | Có phần "chúng tôi đã kiểm tra giả thuyết ngược lại" |
| **Goodstart Fellow** (tài trợ) | Tác động cộng đồng: y tế, giáo dục, môi trường, wellbeing | Câu "ai được lợi, bao nhiêu người" trong khuyến nghị |
| **GV Western Sydney / Coventry / Roehampton** | Chuẩn học thuật quốc tế, pitch tiếng Anh rõ ràng | Chuẩn bị deck song ngữ hoặc tiếng Anh |

### 2.2 Chủ đề đề bài có thể ra – xếp hạng [SUY RA]
Xác suất là ước lượng chủ quan (tổng ≈100%), dựa trên: ai là chủ nhà viết đề, ai cung cấp dữ liệu, nội dung workshop cùng ngày phát đề.

| Hạng | Chủ đề | Xác suất | Lý do | Dữ liệu khả dĩ |
|---|---|---|---|---|
| 1 | **Tài chính công / chính sách kinh tế cấp tỉnh hoặc quốc gia** (thu–chi NSNN, thuế, đầu tư công, FDI, tăng trưởng, việc làm; sáp nhập 63→34 tỉnh) | ~30% | Chủ nhà là Khoa TCC + AVSE policy + Sacha Dray (tài khoá/thuế) dạy ngay sau khi phát đề | Niên giám & số liệu thống kê (gso.gov.vn / nso.gov.vn), Bộ Tài chính – công khai ngân sách (mof.gov.vn), PCI (pcivietnam.vn), PAPI (papi.org.vn), WB Viet Nam Economic Update |
| 2 | **Doanh nghiệp / thị trường vốn** (hiệu quả DN theo ngành, rủi ro tín dụng, tác động chính sách lên DN niêm yết) | ~20% | FiinGroup là đối tác dữ liệu duy nhất; Viet Nguyen‑Tien có nghiên cứu dữ liệu DN VN | Dữ liệu FiinPro/FiinTrade (nếu BTC cấp), BCTC công bố, thư viện vnstock, WB Enterprise Survey VN |
| 3 | **Chỉ số phát triển & so sánh quốc tế** (VN vs ASEAN: năng suất, thu thuế/GDP, nợ công, giáo dục, nghèo) | ~15% | Workshop dashboard của World Bank; dữ liệu mở sạch, dễ làm trong 27 giờ | World Bank WDI API (api.worldbank.org/v2), IMF WEO, Our World in Data, Open Development Mekong (data.opendevelopmentmekong.net) |
| 4 | **Kinh tế dữ liệu / chuyển đổi số / chuyển đổi xanh** (năng lượng, EV, số hoá, thương mại điện tử) | ~15% | Talk LSE "Combining Data for Socioeconomic Development" chiều 19/11; NQ 57 | Google Trends, Ember/IEA, VECOM e‑commerce index, OWID energy, WDI digital, dữ liệu tin đăng (scrape) |
| 5 | **Tác động xã hội** (y tế, giáo dục, ô nhiễm PM2.5, wellbeing) | ~10% | Nhà tài trợ Goodstart ưu tiên tác động cộng đồng | OpenAQ, IQAir, WHO GHO, VHLSS (tóm tắt), dữ liệu Bộ GD&ĐT |
| 6 | **Giao thông / di chuyển / thị giác máy tính** (đếm xe từ camera, ETC, ùn tắc) | ~10% | Workshop CV ngày 19/11 và diễn giả Tasco (VETC). **Nhưng** Chi‑Yu Lee nghiên cứu hành vi động vật, Tasco không phải đơn vị ra đề, và đối tượng là SV kinh tế → khó ra đề CV thuần | Camera giao thông TP.HCM (giaothong.hochiminhcity.gov.vn), video công khai, dữ liệu xe đăng ký/VAMA, OSM |

**Dạng đề dự đoán** [SUY RA]: một **đề mở chung cho mọi đội**, có thể kèm 1–2 bộ dữ liệu BTC cấp + cho phép bổ sung nguồn ngoài; yêu cầu sản phẩm = **dashboard + khuyến nghị quyết định + pitch**. Khả năng là đề kết hợp (ví dụ "dùng dữ liệu để đề xuất chính sách X cho tỉnh/ngành Y").

**Khoảng trống của kit so với xếp hạng:** đã có pack cho hạng 1–5 (`public_finance_province`, `listed_firms_market`, `development_indicators`, `data_economy_property`, `social_impact`, `economic_policy`) và CV (`cv_observation`). **Thiếu pack "mobility/ETC/ô tô"** và **pack năng lượng/EV** (sở trường của Viet Nguyen‑Tien) — nên bổ sung bản nhẹ (KPI + công thức + mẫu khuyến nghị) trước 18/11. Kit hiện nặng về DE; cần cân lại để phần **chính sách & giới hạn** nổi bật hơn.

---

## 3. Tiêu chí chấm & chiến lược ghi điểm

### 3.1 Tiêu chí chính thức
**[CHƯA XÁC NHẬN]** — không tìm thấy. Việc nên làm: hỏi BTC trên nhóm Zalo trước 18/11: (a) rubric và trọng số, (b) thời lượng pitch/Q&A, (c) ngôn ngữ, (d) định dạng nộp (link dashboard? file deck? mã nguồn?), (e) dữ liệu do BTC cấp hay tự thu thập, (f) có được dùng AI/LLM không.

### 3.2 Rubric suy ra (dựa trên mô tả 2 track ở S1, mô tả cuộc thi ở S2 và chuẩn datathon VN cùng loại) [SUY RA]
| Tiêu chí | Trọng số ước lượng | Căn cứ |
|---|---|---|
| A. Định hình vấn đề & câu hỏi quyết định (phù hợp đề, đúng người ra quyết định) | 20% | Tên cuộc thi "Data to Decision" |
| B. Dữ liệu & quy trình (thu thập, làm sạch, mô hình dữ liệu, minh bạch nguồn) | 20% | Track Data & Analytics; workshop Tasco |
| C. Phân tích & insight (đúng phương pháp, có kiểm định, giới hạn) | 20% | Giám khảo kinh tế lượng/học thuật |
| D. Khuyến nghị & tính khả thi/tác động | 20% | AVSE/WB/Goodstart |
| E. Dashboard/trực quan hoá | 10% | Workshop Sacha Dray |
| F. Trình bày & Q&A (Track Presentation) | 10% (+ có thể giải riêng) | Track Presentation |

### 3.3 Ánh xạ tiêu chí → tính năng kit
| Tiêu chí | Tính năng kit dùng | Cách trình bày để ăn điểm | Bẫy cần tránh |
|---|---|---|---|
| A | Trang **Đề bài** → `brief.json` (câu hỏi, biến mục tiêu, loại quyết định); scenario packs | Slide 2: 1 câu hỏi quyết định + người ra quyết định + KPI thành công | Trả lời "đề muốn gì" bằng 10 biểu đồ mô tả |
| B | Pipeline **Ingestion→Storage→Transform→Serving** (DuckDB bronze/silver/gold, connectors CSV/SQL/API/scrape/RSS), **báo cáo chất lượng trước/sau** (missing/duplicate/outlier), lineage/provenance, incremental load, conformed dimensions (63→34 tỉnh) | 1 slide pipeline có **số thật** (số dòng vào/ra, % missing trước/sau, thời gian chạy); bảng nguồn + ngày tải | Nói quá dài về kỹ thuật; giám khảo kinh tế chỉ cần tin rằng số liệu sạch & truy được |
| B (mô hình) | Sinh **OBT / Star / Snowflake / Data Vault** + ERD | Trả lời đúng ngôn ngữ workshop: "**Star schema** cho phân tích (dim tỉnh/năm/ngành), **OBT** để phục vụ dashboard nhanh; Data Vault không cần ở quy mô hackathon – nhưng kit sinh được nếu mở rộng nhiều nguồn" | Khoe cả 4 mô hình mà không nói vì sao chọn |
| C | **Insight có kiểm định thống kê** (p‑value, effect size, cỡ mẫu), Drivers & What‑if, Phân khúc, SQL Explorer | Mỗi insight: con số + kiểm định + "liên đới, không phải nhân quả" + một kiểm tra phản biện (theo tinh thần Chi‑Yu Lee) | Khẳng định nhân quả từ dữ liệu quan sát; p‑hacking khi chạy nhiều kiểm định (nhắc hiệu chỉnh/thận trọng) |
| D | Trang **Quyết định** (mẫu khuyến nghị: hành động, so‑what, tác động, bằng chứng, KPI/chủ thể), What‑if để lượng hoá | "Chúng tôi khuyến nghị **[cơ quan]** làm **[gì]** ở **[đâu/ai]**, kỳ vọng **[KPI ±]**, theo dõi bằng **[chỉ số]**" + chi phí/rủi ro | Khuyến nghị chung chung "cần đẩy mạnh…" |
| E | Dashboard shadcn, **driver.js "Câu chuyện"** (tour qua 5 insight), chế độ **Hỏi AI** | Demo 60–90 giây: bấm "Câu chuyện" → 3 insight → trang Quyết định. Mỗi biểu đồ có nguồn + năm | Demo trực tiếp phụ thuộc mạng → luôn có video/ảnh chụp dự phòng |
| E/F | **AI Analyst** (Groq hoặc offline, chỉ dùng số từ engine – không bịa) | Giới thiệu như "người phân tích hỏi đáp cho cán bộ không biết SQL" → gắn với "kinh tế dữ liệu"/dân chủ hoá dữ liệu | Để AI trả lời live khi giám khảo hỏi mà không kiểm soát |
| F | `deck.pptx` 15 slide tự sinh, `slides/pitch.md` khung 7 phút, executive summary | Người nói tốt nhất (không nhất thiết người code) trình bày; deck tiếng Anh nếu được phép | Đọc slide; vượt giờ |

**Định vị chiến lược:** đa số đội SV kinh tế sẽ có slide đẹp nhưng dữ liệu mỏng; đội nào có pipeline chuẩn sẽ dễ sa vào khoe kỹ thuật. **Lợi thế của bạn = "bằng chứng chặt + một quyết định rõ"**: dùng kit để có độ tin cậy dữ liệu, nhưng thời lượng pitch dành ≥60% cho câu hỏi chính sách, insight và khuyến nghị.

---

## 4. Kế hoạch quản lý dự án

### 4.1 Vai trò (đội 4–5 người ghép ngẫu nhiên)
| Mã | Vai | Ai hợp | Ghi chú |
|---|---|---|---|
| **LEAD** | Trưởng nhóm / giữ giờ / người quyết | **Thành** (được BTC mời) | Kiêm luôn DE vì là người code duy nhất có khả năng → giao phần nói chính cho người khác |
| **DE** | Data engineer (kit, pipeline, dashboard) | Thành | Nếu có thêm người biết code: giao Hỏi AI/SQL cho họ |
| **AN** | Analyst (thống kê/Excel/kinh tế lượng) | SV kinh tế/tài chính giỏi định lượng | Chọn & kiểm chứng insight qua dashboard, SQL Explorer, Hỏi AI |
| **PO** | Policy owner / người pitch chính | SV nói tốt, hiểu chính sách công | Viết câu hỏi quyết định & khuyến nghị; trình bày chính |
| **ST** | Storyteller / designer deck (không code) | SV marketing/truyền thông | Deck, kịch bản, ảnh dự phòng |
| **RQ** | Researcher / QA (người thứ 5) | Bất kỳ | Bối cảnh từ nguồn chính thống; soát mọi con số trên slide khớp dashboard |
Đội 4 người: gộp RQ vào ST.

### 4.2 Timeline theo giờ (19/11–21/11)
| Thời điểm | Việc | Chủ trì | Đầu ra |
|---|---|---|---|
| **19/11** 09:00–11:30 / 13:30–14:45 | Check‑in UEH Green Living Hub; test laptop + wifi; `make api` + `make web` chạy được trên mạng địa điểm | LEAD | Kit chạy tại chỗ |
| 14:45–15:30 | Nghe Chi‑Yu Lee; ghi thuật ngữ, ý "observation → data" | Tất cả | Ghi chú 5 dòng |
| 15:30–16:15 | **Cả đội** nghe talk LSE "Data to Decision" (tìm "góc" kết hợp dữ liệu cho phát triển KT‑XH) | Tất cả | 3 ý dùng được trong pitch |
| 16:15–16:45 | Họp online với mentors: hỏi format nộp bài, độ dài pitch, ngôn ngữ, dữ liệu | LEAD | Trả lời các câu ở 3.1 |
| 21:00–22:30 | Ngủ sớm (đêm 20/11 có thể thức khuya) | Tất cả | — |
| **20/11** 09:00–09:30 | Khai mạc + Challenge Briefing + ghép đội. 10 phút giới thiệu kỹ năng → chốt vai | LEAD | Bảng vai |
| 09:30–10:15 | **Cả đội** nghe workshop Dashboard World Bank (khả năng là người chấm phần dashboard); DE tranh thủ dán đề vào **Đề bài** | Tất cả | 3 nguyên tắc dashboard của diễn giả, brief.json |
| 10:15–11:30 | DE: upload dữ liệu BTC, chạy pipeline lần 1; PO + AN: đọc đề to, liệt kê dữ liệu được cấp, phác câu hỏi quyết định | DE / PO | Pipeline xanh lần 1 |
| 11:30–13:00 | Ăn trưa + **họp chốt hướng**: 1 câu hỏi quyết định, người ra quyết định, 2–3 giả thuyết | PO | **CHECKPOINT 1 (12:30)** |
| 13:00–14:30 | DE: thêm 1–2 nguồn ngoài (WDI/GSO/scrape) + conformed dim; AN: duyệt Insight/Drivers; RQ: bối cảnh + nguồn; ST: khung deck theo 4.4 | Từng người | Gold tables, danh sách insight ứng viên |
| 14:30–15:30 | AN chọn 3–5 insight (kiểm định, cỡ mẫu); DE sửa lỗi dữ liệu, bật What‑if; PO viết bản nháp khuyến nghị | AN / PO | **CHECKPOINT 2 (15:30)** |
| 15:30–16:00 | Chuẩn bị 3 câu hỏi cho mentor + bản pitch 2 phút (ghi câu hỏi chính sách + giả thuyết trước check‑in) | PO | — |
| **16:00–16:30** | **Mentor check‑in #1**: trình bày câu hỏi + 3 insight + khuyến nghị nháp; xin phản hồi về độ phù hợp đề | PO (nói), cả đội ghi | Danh sách điều chỉnh |
| 16:30–20:00 | Xử lý phản hồi mentor; ăn tối 17:30–19:00; khoá dữ liệu nguồn | DE / AN | **CHECKPOINT 3 (20:00) – đóng băng phạm vi** |
| 20:00–23:00 | DE: dashboard + "Câu chuyện" driver.js + Quyết định; ST + PO: deck v1 + kịch bản; RQ: soát số | Từng người | Deck v1, dashboard v1 |
| 23:00–24:00 | Chạy thử pitch toàn phần lần 1 (bấm giờ) | PO | Ghi chú sửa |
| 00:00–06:30 | **Ngủ luân phiên**: ít nhất 5 tiếng cho người pitch; DE ngủ từ 01:00 | LEAD | — |
| **21/11** 07:00–09:00 | Ăn sáng; rà lại khuyến nghị với cái đầu tỉnh táo | Tất cả | — |
| 09:00–10:30 | Hoàn thiện deck v2; xuất `deck.pptx` + ảnh/video dự phòng của dashboard; Q&A drill (mục 4.6) | ST / DE / PO | Deck v2 |
| **10:30–11:00** | **Mentor check‑in #2**: chạy pitch thật trước mentor | PO | Sửa cuối |
| 11:00–12:00 | Ăn trưa + sửa theo mentor; **CHECKPOINT 4 (12:00) – khoá nội dung** | LEAD | — |
| 12:00–12:40 | Chỉ sửa lỗi chính tả/định dạng; chạy pitch 2 lần; kiểm tra file mở được trên máy khác | ST / PO | Bản cuối |
| **12:40** | **Nộp bài (sớm 20 phút so với hạn 13:00)**; chụp màn hình xác nhận | LEAD | Biên nhận |
| 13:15–15:15 | Pitch + Q&A (trao giải 15:45–16:45) | PO (+ DE trả lời câu kỹ thuật) | — |

### 4.3 Checkpoint go/no‑go
| Checkpoint | Điều kiện "GO" | Nếu "NO‑GO" |
|---|---|---|
| **CP1 – 20/11 12:30** | Có 1 câu hỏi quyết định viết được thành 1 câu; biết dữ liệu nào trả lời nó; pipeline lần 1 chạy | Thu hẹp câu hỏi (1 ngành / 1 vùng / 1 chỉ số); bỏ nguồn ngoài, chỉ dùng dữ liệu BTC |
| **CP2 – 20/11 15:30** (trước check‑in #1 16:00) | ≥3 insight có số + kiểm định + liên quan trực tiếp tới quyết định | Đổi sang phân tích mô tả + so sánh nhóm đơn giản (t‑test / so sánh trung vị); bỏ mô hình phức tạp |
| **CP3 – 20/11 20:00** | Mentor xác nhận hướng phù hợp đề; dữ liệu đã khoá | Nếu mentor nói lệch đề: dành tối đa 2 giờ xoay hướng, giữ nguyên pipeline, đổi câu hỏi |
| **CP4 – 21/11 12:00** | Deck hoàn chỉnh, pitch ≤ thời lượng, mọi số đã soát | Cắt slide, không thêm tính năng; nếu dashboard lỗi → dùng ảnh chụp + video |

### 4.4 Sổ rủi ro
| # | Rủi ro | Khả năng | Ảnh hưởng | Giảm thiểu |
|---|---|---|---|---|
| R1 | Đề lệch hẳn các pack chuẩn bị (VD: giao thông, y tế cụ thể) | Trung bình | Cao | Kit dạng "thả dataset bất kỳ"; dùng pack gần nhất làm khung; CP1 thu hẹp phạm vi |
| R2 | Đồng đội không code / không quen nhau, xung đột vai | Cao | Trung bình | Vai ở 4.1 không cần code; mọi việc phân tích làm qua trình duyệt; LEAD chốt quyết định nhanh |
| R3 | Một mình Thành ôm toàn bộ kỹ thuật → kiệt sức, thành nút cổ chai | Cao | Cao | Khoá phạm vi ở CP3; không thêm tính năng sau 20:00; ngủ ≥4 tiếng; giao Hỏi AI/SQL cho AN |
| R4 | Wifi UEH yếu / chặn cổng → API ngoài, Groq lỗi | Trung bình | Cao | Tải sẵn WDI/GSO offline; AI chế độ offline; hotspot 4G dự phòng; chạy local hoàn toàn |
| R5 | Laptop hết pin / hỏng / RAM thấp khi `make web` | Thấp–TB | Cao | Ổ cắm kéo dài, sạc dự phòng; bản build sẵn; ảnh chụp + video demo trên USB/Drive |
| R6 | Pitch tiếng Anh bắt buộc mà đội yếu tiếng Anh | Trung bình | Trung bình | Hỏi BTC trước; chuẩn bị deck song ngữ; người pitch tốt tiếng Anh nhất nói phần chính |
| R7 | Giám khảo hỏi nhân quả / phương pháp mà đội trả lời sai | Cao | Cao | Q&A drill (4.6); slide Limitations; từ khoá "liên đới", "gợi ý", "cần đánh giá tác động" |
| R8 | Số trên slide không khớp dashboard (sửa tay) | Trung bình | Cao | RQ soát chéo; chỉ lấy số từ engine/export; không gõ số tay |
| R9 | Dữ liệu BTC bẩn/lớn bất ngờ (Excel nhiều sheet, mã tỉnh lệch, 63/34 tỉnh) | Cao | Trung bình | Conformed dim tỉnh 63→34 đã có; báo cáo chất lượng → biến điểm yếu thành slide "data quality" |
| R10 | Trễ hạn nộp 13:00 (form lỗi, file lớn) | Thấp | Rất cao | Nộp lúc 12:40; nén file; có link Drive dự phòng |
| R11 | Dùng AI/LLM bị coi là vi phạm (nếu luật cấm) | Thấp | Cao | Hỏi BTC; AI Analyst chỉ là công cụ diễn giải, mọi số từ engine – nói rõ |
| R12 | Không đủ giờ cho slide "Khuyến nghị" (lỗi phổ biến) | Cao | Cao | Viết khuyến nghị nháp ngay 14:30 ngày 20/11; deck dựng ngược từ khuyến nghị |
| R13 | Chưa xác nhận tham gia đúng hạn 07/11 (không thấy mail xác nhận trong Gmail) | Thấp–TB | Rất cao | Kiểm tra ngay: đã điền Form/ở trong nhóm Zalo chưa; nếu chưa, liên hệ vietleap2026@gmail.com |

### 4.5 Checklist trước thi (15–18/11)
**Hành chính**
- [ ] **Ngay hôm nay (15/11):** kiểm tra đã xác nhận tham gia (Form + nhóm Zalo; Gmail của bạn không có mail xác nhận đã gửi). Nếu đã trả lời "Yes, I am willing to take the role" thì chuẩn bị vai Trưởng nhóm.
- [ ] Hỏi BTC trên Zalo: rubric, thời lượng pitch, ngôn ngữ, định dạng nộp, dữ liệu được cấp, chính sách dùng AI, có cần mang laptop riêng không.
- [ ] CCCD, thẻ SV, đồ ở KTX (nếu ở lại), ổ cắm kéo dài, sạc dự phòng, adapter HDMI/USB‑C.

**16/11 (Thứ Hai) 19:00 – workshop Tasco (online)**
- [ ] Tham dự, ghi lại **từ khoá đúng như diễn giả dùng** (4 giai đoạn, cách chọn OBT/Star/Snowflake/Data Vault). Dùng lại y nguyên trong pitch.
- [ ] Hỏi diễn giả 1 câu: "Ở quy mô hackathon, anh ưu tiên mô hình nào để phục vụ dashboard?" → câu trả lời này là "đáp án" giám khảo có thể mong đợi.

**17/11 – kỹ thuật**
- [ ] Trên laptop thi: `git pull && make setup && make demo`, rồi `make api` + `make web`; thử cả 3 dataset practice.
- [ ] Tải và lưu offline: WDI cho VN + ASEAN (≈50 chỉ số chính), số liệu GSO cấp tỉnh (GRDP, thu–chi NSNN, dân số, lao động), PCI, dữ liệu FiinGroup/vnstock mẫu.
- [ ] Thử AI Analyst: có khoá Groq và **khi rút mạng** (offline).
- [ ] (Tuỳ chọn) bổ sung pack nhẹ "mobility/ETC" và "energy/EV" (KPI + mẫu khuyến nghị).

**18/11 – trình bày**
- [ ] Viết khung deck 7 phút song ngữ (4.6) với chỗ trống cho số liệu.
- [ ] Soạn câu trả lời mẫu 10 câu Q&A (4.7) bằng cả tiếng Việt và tiếng Anh.
- [ ] Ghi lại video demo 90 giây của dashboard (dùng dataset practice) để làm mẫu dự phòng.
- [ ] Viết "thẻ vai trò" 1 trang để phát cho đồng đội lúc 09:00 ngày 20/11.

### 4.6 Cấu trúc pitch 7 phút (thời lượng thật [CHƯA XÁC NHẬN] – co giãn theo tỉ lệ)
| Phút | Slide | Nội dung | Người nói |
|---|---|---|---|
| 0:00–0:40 | 1. Hook | 1 con số gây chú ý từ dữ liệu + vì sao quan trọng bây giờ (NQ 57 / bối cảnh đề) | PO |
| 0:40–1:20 | 2. Câu hỏi quyết định | "Ai cần quyết định gì?" + KPI thành công | PO |
| 1:20–2:10 | 3. Dữ liệu & pipeline | Nguồn (cấp + tự thu), 4 giai đoạn, chất lượng trước/sau, mô hình Star/OBT – **1 slide duy nhất** | DE |
| 2:10–4:10 | 4–6. Ba insight | Mỗi insight: biểu đồ + con số + kiểm định + "so what" | AN / PO |
| 4:10–5:00 | 7. Demo dashboard | "Câu chuyện" driver.js → trang Quyết định (hoặc video dự phòng) | DE |
| 5:00–6:10 | 8. Khuyến nghị | 2–3 hành động: ai – làm gì – ở đâu – KPI – lộ trình; what‑if lượng hoá | PO |
| 6:10–6:40 | 9. Giới hạn & bước tiếp | Liên đới ≠ nhân quả, dữ liệu thiếu, cách đánh giá tác động sau này | PO |
| 6:40–7:00 | 10. Kết | Nhắc lại 1 câu khuyến nghị + cảm ơn | PO |
Phụ lục (không trình bày, dùng cho Q&A): ERD, bảng chất lượng, bảng kiểm định đầy đủ, nguồn dữ liệu.

### 4.7 Mười câu giám khảo có thể hỏi + gợi ý trả lời
1. **"Kết quả này là nhân quả hay chỉ tương quan?"** → "Là liên đới từ dữ liệu quan sát. Chúng tôi đã kiểm soát [biến X] và kiểm tra theo nhóm; để khẳng định nhân quả cần thiết kế như difference‑in‑differences khi chính sách được áp dụng theo giai đoạn — đó là bước tiếp theo chúng tôi đề xuất."
2. **"Vì sao chọn mô hình dữ liệu này (Star/OBT)?"** → "Star schema cho phép phân tích theo tỉnh/năm/ngành nhất quán giữa nhiều nguồn; OBT phục vụ dashboard nhanh. Data Vault phù hợp hệ thống lâu dài nhiều nguồn thay đổi — vượt quá nhu cầu 27 giờ, nhưng pipeline của chúng tôi mở rộng sang được."
3. **"Dữ liệu từ đâu, có tin được không?"** → Chỉ bảng nguồn: tổ chức phát hành, ngày tải, phạm vi; nêu % missing/duplicate trước–sau và cách xử lý outlier.
4. **"Xử lý thay đổi địa giới 63→34 tỉnh thế nào?"** → "Chúng tôi dùng bảng ánh xạ tỉnh cũ → tỉnh mới (conformed dimension), cộng gộp chỉ số cộng được, tính lại tỉ lệ từ tử/mẫu; với chỉ số không cộng được thì giữ cấp tỉnh cũ và ghi chú."
5. **"Nếu cơ quan chỉ làm được một việc, đó là gì?"** → Đọc ngay khuyến nghị số 1 kèm KPI và chi phí/độ khó.
6. **"Mẫu nhỏ/nhiều kiểm định thì có bị p‑hacking không?"** → "Chúng tôi báo cỡ mẫu và effect size, không chỉ p‑value; ưu tiên insight vững qua nhiều cách đo; coi kết quả là gợi ý cần kiểm chứng."
7. **"Khuyến nghị có khả thi về ngân sách/thể chế không?"** → Nêu đơn vị chịu trách nhiệm, nguồn lực, rủi ro triển khai, và chỉ số theo dõi 6–12 tháng.
8. **"Dashboard này dành cho ai và họ dùng thế nào?"** → "Cho cán bộ [Sở/Bộ] không biết SQL: xem 3 KPI, lọc theo tỉnh, hỏi AI bằng tiếng Việt; AI chỉ trả lời bằng số đã tính sẵn, không tự bịa."
9. **"Nhóm đã dùng AI ở đâu? Có kiểm chứng không?"** → "AI chỉ diễn giải và trả lời câu hỏi dựa trên bảng gold và kết quả kiểm định; mọi con số trên slide được đối chiếu với SQL."
10. **"Hạn chế lớn nhất của phân tích là gì?"** → Nêu thẳng 1–2 hạn chế thật (thiếu năm/tỉnh, biến bị bỏ sót, dữ liệu tổng hợp ẩn bất bình đẳng trong tỉnh) + cách khắc phục với dữ liệu tốt hơn — đây là điểm cộng với giám khảo học thuật.

---

## 5. Việc còn mở / cần xác minh
- Tiêu chí chấm, thời lượng pitch, ngôn ngữ, định dạng nộp, chính sách dùng AI → hỏi BTC (Zalo / vietleap2026@gmail.com).
- Giải nhất 25 triệu VNĐ → chưa có nguồn; chính thức chỉ là "tổng hơn 20 triệu".
- Có giải riêng cho track Presentation không.
- Tên giám khảo cụ thể; vai trò logo "RAF" trên poster 16/11.
- Bạn đã xác nhận tham gia + nhận vai Trưởng nhóm chưa (không thấy mail đã gửi trong Gmail cá nhân).
