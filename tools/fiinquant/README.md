# FiinQuantX → vùng dữ liệu gốc

Cài trong môi trường Python của dự án. Wheel FiinQuantX 0.1.73 nằm cạnh README.
Tệp requirements ghi các phiên bản đã có trong môi trường chạy, gồm matplotlib
mà wheel không khai báo và PyArrow để ghi Parquet.

```powershell
python -m pip install -r tools/fiinquant/requirements.txt tools/fiinquant/fiinquantx-0.1.73-py3-none-any.whl
python tools/fiinquant/fetch_fiinquant.py --all --mock
python tools/fiinquant/fetch_fiinquant.py --all
python tools/fiinquant/fetch_fiinquant.py bars --universe banks --since 2021-11-19
python tools/fiinquant/fetch_fiinquant.py foreign --universe VCB,ACB
```

Lệnh thật đọc `FIINQUANT_USERNAME` và `FIINQUANT_PASSWORD` từ biến môi trường.
Chế độ mock dùng ngày cố định 19/11/2026 và hạt giống cố định, ghi dưới
`data/raw/fiinquant/_mock/`. Chọn Python trong `.venv` khi chạy trực tiếp
trên Windows. Lệnh cũ không chỉ định dataset, chẳng hạn `--mock --tickers VCB`,
vẫn tạo tệp bronze theo giao diện trước đây.

| Dataset | Phạm vi mặc định |
| --- | --- |
| `roster` | Ảnh chụp HOSE, HNX, UPCoM với BasicInfor và ICB. Mã–sàn ngoài danh sách TickerList được ghi trong sidecar. |
| `bars` | Cổ phiếu hiện có trên ba sàn từ 19/11/2021. VNINDEX, VN30, HNXIndex và UpcomIndex từ 19/11/2016. Giá điều chỉnh và số liệu giao dịch theo SDK. |
| `foreign` | Ngân hàng và VN30 từ 19/11/2021. Giữ nguyên dấu thời gian trong phiên nếu nguồn trả về. |
| `valuation` | Ngân hàng và VN30, toàn bộ nhóm ICB L2 theo tài liệu, và bốn chỉ số. P/E và P/B từ 19/11/2021, phân biệt bằng `scope`. |
| `bank_ratios` | Ngân hàng BANKS_L2, tỷ số hợp nhất theo quý đã kết thúc. Truy vấn từ năm 2015 và giữ các quý nguồn trả về. |
| `breadth` | Độ rộng của bốn chỉ số và top tăng/giảm đóng góp của VNINDEX. Dòng đóng góp dùng ngày giao dịch từ ảnh chụp độ rộng VNINDEX. |
| `vn30_weights` | Ảnh chụp Rebalance VN30, khóa theo mã và ngày chụp. |
| `investor_flow` | Ngân hàng và VN30 trong 28 ngày lịch gần nhất. |

`--universe` chọn mã cổ phiếu cho các truy vấn có danh sách mã. Danh mục vẫn
kiểm tra theo ba sàn, tỷ số theo BANKS_L2 và tỷ trọng theo VN30. Phạm vi ngành
và chỉ số của `valuation`, cũng như các chỉ số của `breadth`, cố định.
`--since` đặt mốc sớm nhất cho dữ liệu lịch sử. Ngày cuối là ngày chạy theo giờ
Việt Nam. Ngày giao dịch thực tế, mã thiếu và thời gian thực thi xem trong log.
Danh mục hiện tại có thể bỏ sót mã đã hủy niêm yết. Dữ liệu ngày hiện tại có thể
thay đổi sau khi đóng cửa.

Đợt tải ngày 19/11/2026 có giá, định giá và dòng tiền theo nhóm nhà đầu tư
đến 18/11/2026. Dữ liệu khối ngoại và các ảnh chụp có ngày 19/11/2026.
Tỷ số ngân hàng có dữ liệu từ quý I/2021 đến quý III/2026.

## Tệp và giới hạn

- Mỗi lần xuất dữ liệu ghi cặp
  `data/raw/fiinquant/<dataset>/<run_date>_<run_id>.parquet` và `.json`.
  Parquet hiện hành là bản tích lũy, mỗi khóa giữ dòng lấy mới nhất. Cặp trước
  được lưu trong `_history/` để đối chiếu. Đọc cặp hoàn chỉnh mới nhất ở cấp
  dataset, tránh đọc đệ quy vào lịch sử. Sidecar ghi tham số, số dòng, cột,
  SHA-256, giờ tải (+07:00), phiên bản SDK, HTTP và thời gian lấy.
- Chuỗi ngày truy vấn lại từ phiên thứ năm gần nhất đã lưu của từng mã. Nếu có
  dưới năm phiên thì dùng mốc yêu cầu. Tỷ số theo quý dùng năm quý gần nhất
  đã lưu. Ảnh chụp giữ lịch sử theo ngày. Lần tải toàn bộ đầu tiên có thể kéo
  dài vì SDK chia chuỗi ngày của cả thị trường thành nhiều lượt HTTP.
- `_runs.jsonl` ghi một dòng cho mỗi lần gọi CLI mới, gồm thống kê từng
  dataset, lỗi và tổng số HTTP. Phiên đăng nhập dùng chung cho cả lượt.
  Bộ đếm theo dataset tính cả truy vấn danh mục dùng lần đầu trong dataset đó.
- Tối đa 10 lượt HTTP mỗi giây trên các transport REST của SDK. Tạm dừng
  theo `Retry-After` và thử lại với khoảng chờ tăng dần khi mất kết nối,
  gặp HTTP 429 hoặc 5xx. HTTP 401/403 dừng lượt chạy. Giới hạn của gói được
  công bố tại [bảng giá FiinQuant](https://fiinquant.vn/Pricing).
- Tệp Parquet giữ giá trị nguồn và thêm trường nhận diện ảnh chụp/phạm vi
  khi cần. Các khóa ghép theo từng dataset nằm trong `KEYS`. Quy ước mã
  ngành theo danh mục ICB. Với SDK 0.1.73, truy vấn ngành bằng mã có dấu
  gạch dưới như `BASIC_RESOURCES`. Kết quả gồm hậu tố `_L2`. [Danh mục ICB](https://docs.fiinquant.vn/ham-va-cong-thuc/11.-du-lieu-ho-tro/11.2.-danh-sach-nhom-nganh-icb).

## Quyền sử dụng

Điều khoản FiinGroup, mục 2, cho phép tạo sản phẩm phái sinh từ dữ liệu
với trích nguồn phù hợp, đồng thời giới hạn chuyển giao và cung cấp Hệ
thống cho bên thứ ba. Giữ dữ liệu gốc trong vùng truy cập nội bộ. Chỉ đưa
chỉ số tổng hợp có ghi nguồn lên dashboard công khai sau khi xác nhận phạm
vi công bố với FiinGroup cho gói tài khoản đang dùng. Áp dụng cùng quy
trình xác nhận cho các mẫu dữ liệu gốc trong bộ kiểm thử. [Điều khoản sử dụng FiinQuant](https://fiinquant.vn/Home/Privacy?isShowPolicy=True).
