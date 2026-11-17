# Chuyển dịch năng lượng và xe điện

Chuẩn bị mạng một lần để tải bản OWID cố định và bản Ember hiện hành vào `data/cache/`. Sau khi có hai tệp, chạy recipe chính offline.

```bash
mkdir -p data/cache
curl -fL 'https://catalog.ourworldindata.org/garden/energy/2026-09-10/owid_energy/owid_energy.parquet' -o data/cache/owid_energy.parquet
curl -fL 'https://files.ember-energy.org/public-downloads/generation/outputs/release_generation_yearly_global.csv' -o data/cache/ember_yearly.csv
python de.py run scenarios/energy/sources.yaml --serve --target renewables_electricity_share_pct
```

Khi có mạng hoặc cache API, `python de.py run scenarios/energy/sources.wdi.yaml` bổ sung bảng về tiếp cận điện, tiêu thụ năng lượng tái tạo và điện/người. Bộ chính dùng tỷ trọng điện tái tạo, cường độ phát thải điện và tỷ trọng dầu. Phân tích triển khai trạm sạc cần thêm số liệu xe điện và công suất lưới theo địa phương. [OWID Energy](https://catalog.ourworldindata.org/energy/owid_energy/) · [Ember Yearly Electricity](https://ember-energy.org/data/yearly-electricity-data/)
