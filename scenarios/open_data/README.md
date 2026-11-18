# Open-data API recipes (Mentor Gap #5)

Bộ công thức nguồn mở (`kind: api`) sẵn dùng cho ngày thi theo checklist mentor:

1. **`sources.un_sdg.yaml`** — UN SDG API (`areaCode=704` cho Việt Nam, hỗ trợ phân trang `paging: page` và `watermark_col: timePeriodStart`).
2. **`sources.fx_open_er.yaml`** — Tỷ giá quy đổi miễn phí `open.er-api.com` (`USD` và `VND`, giới hạn tần suất `rate_per_sec: 1`, không cần API key).
3. **`sources.open_meteo.yaml`** — Dữ liệu thời tiết lịch sử Open-Meteo Archive (`Hà Nội` và `TP. Hồ Chí Minh`, hỗ trợ `watermark_col` + `watermark_param: start_date`).

## Cách chạy

```bash
python de.py run scenarios/open_data/sources.un_sdg.yaml --serve --mode incremental
python de.py run scenarios/open_data/sources.fx_open_er.yaml --serve
python de.py run scenarios/open_data/sources.open_meteo.yaml --serve --mode incremental
```

> Lưu ý vận hành: API bên ngoài có thể giới hạn tốc độ hoặc quá thời gian chờ tuỳ mạng địa điểm thi; mọi phản hồi thành công được lưu cache tại `data/cache/` để chạy lại không tốn quota.
