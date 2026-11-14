# CV counting — từ quan sát đến dữ liệu

Đếm phương tiện/người đi qua một vạch trong video → `counts.csv` (`timestamp,class,in,out`) → đưa vào pipeline như mọi nguồn khác. Liên quan talk Chi-Yu Lee (Konstanz), 19/11 15:30, *From observation to data* (object tracking).

**Cách hoạt động:** YOLOv8n (ultralytics) nhận diện từng khung → ByteTrack gán ID theo dõi (`supervision.ByteTrack` ở bản supervision cũ; từ supervision 0.31 ByteTrack chuyển sang gói `trackers` — nếu không có thì dùng ByteTrack tích hợp của ultralytics; tên tracker được ghi vào meta) → LineZone đếm lượt qua vạch theo chiều vào/ra → gộp theo khung thời gian (`--every`), điền 0 cho khung không có lượt nào. Chỉ lưu số đếm, không lưu ảnh/khuôn mặt.

## Cài đặt (tuỳ chọn, ~1 GB vì PyTorch)

```bash
source tools/env.sh
pip install ultralytics supervision          # + tuỳ chọn: pip install trackers (ByteTrack của Roboflow)
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"   # tải sẵn trọng số (~6 MB) trước ngày thi
```

Không cài cũng không sao: script báo hướng dẫn thay vì lỗi (mã thoát 2), và chế độ `--events` không cần thư viện nào.

## Chạy

```bash
# video → counts.csv (CPU; --stride 3 = xử lý 1/3 số khung cho nhanh)
python scenarios/cv_counting/count.py --video data/raw/nut_giao.mp4 --out data/raw/counts.csv \
    --line 0,360,1280,360 --classes car,motorcycle,bus,truck,person --every 60s --stride 3 \
    --start 2026-11-20T07:00:00 --license "<giấy phép + link nguồn video>"

# đã có log sự kiện qua vạch (t giây, class, direction in|out) → counts.csv
python scenarios/cv_counting/count.py --events events.csv --out counts.csv --every 15m --duration 3600

# vào pipeline: file đơn…
python de.py file data/raw/counts.csv --name dem_xe --serve
```

…hoặc khai báo trong `sources.yaml` (connector `cv` nhận cả CSV lẫn video; với video sẽ tự gọi `count.py`, các `options` thành tham số dòng lệnh):

```yaml
- name: cam_nut_giao
  kind: cv
  uri: data/raw/nut_giao.mp4
  options: {line: "0,360,1280,360", every: 60s, stride: 3, start: "2026-11-20T07:00:00"}
  license_note: "<giấy phép video>"
```

| Tham số | Mặc định | Ghi chú |
|---|---|---|
| `--line x1,y1,x2,y2` | vạch ngang giữa khung | toạ độ pixel; chiều "in"/"out" theo hướng vạch (đảo 2 điểm để đổi chiều) |
| `--classes` | car,motorcycle,bus,truck,bicycle,person | tên lớp COCO |
| `--every` | 60s | `30s`, `15m`, `1h` |
| `--stride` | 3 | tăng nếu máy chậm; quá lớn sẽ bỏ sót vật thể nhanh |
| `--start` | — | giờ thực của khung đầu; không có thì `timestamp` là thời gian trôi qua `HH:MM:SS` |
| `--model`, `--conf` | yolov8n.pt, 0.3 | |

Đầu ra kèm `counts.csv.meta.json` (video, fps, vạch, model, stride, số lượt, giấy phép) — dùng cho slide Provenance.

## Kiểm tra độ chính xác & giấy phép

- Đếm tay 1–2 phút mẫu và so với `counts.csv` → báo sai số trong slide Limitations (đêm/mưa/che khuất làm giảm độ chính xác).
- Chỉ dùng video bạn có quyền dùng (BTC cung cấp, tự quay nơi công cộng, hoặc nguồn có giấy phép mở ghi rõ trên trang file); ghi giấy phép qua `--license`. Repo không kèm video mẫu.
- Kiểm thử không cần video/torch: `pytest -q tests/test_cv_counting.py` (log sự kiện tổng hợp → counts.csv → connector `cv` → DuckDB). Nếu đã cài `supervision` + `av`, test còn chạy LineZone/tracker thật trên một clip tổng hợp (chỉ thay YOLO bằng bộ dò ngưỡng). Đã kiểm với supervision 0.31.7 + trackers 2.7.0 và nhánh ByteTrack của ultralytics.
