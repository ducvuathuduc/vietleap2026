# Tài chính công cấp tỉnh

Từ [Cổng công khai ngân sách Bộ Tài chính](https://ckns.mof.gov.vn/SitePages/khaithacdulieu.aspx), chọn **Dự toán** hoặc **Quyết toán**, năm và đơn vị. Ưu tiên tải Excel. Chuẩn hóa đầu vào thành `data/raw/provincial_budget.csv` theo `column_aliases` trong [pack ngân sách](../packs/public_finance_province.yaml). Ghi URL, thời điểm tải, đơn vị và điều khoản sử dụng nguồn trong bản sao recipe trước khi dùng dữ liệu mới. Dân số/GRDP, nếu có, lấy từ [số liệu NSO](https://www.gso.gov.vn/so-lieu-thong-ke/) và ghép ở đúng mức tỉnh × năm trước khi chạy.

Đầu vào cần `province`, `year` và tối thiểu một chỉ tiêu cộng gộp có tên trong `conform.province_rollup.sum`. Dùng cùng đơn vị cho tử và mẫu. Mỗi năm dùng một phạm vi địa giới và một loại số liệu (dự toán hoặc quyết toán) để tránh tính trùng. Bronze giữ bảng gốc. Silver cộng các chỉ tiêu được khai báo theo tỉnh mới × năm, rồi tính tỷ lệ từ các tổng. Nhật ký ghi công thức, cột nguồn thiếu và ví dụ địa danh không ánh xạ được. Các ô thiếu và mẫu số bằng 0 cho kết quả trống. Chỉ tiêu phi cộng gộp cần giữ ở bảng gốc hoặc khai báo tử/mẫu.

```bash
python de.py run scenarios/public_finance/sources.yaml --primary budget --serve --target budget_autonomy_ratio
```

Chỉ chọn `budget_autonomy_ratio` khi có đủ `budget_revenue` và `budget_expenditure`. Điều chỉnh `--target` nếu tệp cung cấp chỉ tiêu khác. Địa giới 2025 là điểm gãy chuỗi. Khi so sánh trước và sau sáp nhập, kiểm tra định nghĩa nguồn thu và chi cùng cơ sở ghi nhận.

## Chạy thử offline với dữ liệu thật

```bash
python de.py run scenarios/public_finance/sources.practice.yaml --serve --target earmarked_capex_share_ratio
```

Snapshot chép Phụ lục VII của Nghị quyết 105/2023/QH15 (trang PDF 18) và 160/2024/QH15 (trang PDF 19), tải ngày 17/11/2026. Đơn vị triệu đồng. Các tổng theo năm và từng cột đã đối chiếu với bảng công bố. Ô để trống trong phụ lục được giữ trống. Hai bảng dự toán dùng địa giới cũ. Chỉ tiêu là **bổ sung có mục tiêu từ NSTW**, với thành phần vốn đầu tư, vốn sự nghiệp và chương trình mục tiêu quốc gia. Bảng này dùng để luyện gộp địa giới và phân tích cơ cấu bổ sung có mục tiêu. Phân tích tự chủ và thực hiện dự toán cần bộ số liệu thu/chi riêng. Checksum nằm trong `data/snapshots/SHA256SUMS`. [NQ 105/2023/QH15](https://vanban.chinhphu.vn/?docid=209069&pageid=27160) · [NQ 160/2024/QH15](https://vanban.chinhphu.vn/?docid=211922&pageid=27160)
