# WDI Việt Nam và nhóm ASEAN giai đoạn 2000–2024

```bash
python de.py run scenarios/wdi_asean/sources.yaml --primary tax_revenue --serve --target gdp_per_capita_usd
python de.py run scenarios/wdi_asean/sources.offline.yaml --serve --target gdp_per_capita_usd
python de.py sql "SELECT * FROM gold.v_vnm_vs_asean_gap WHERE indicator = 'NY.GDP.PCAP.CD' ORDER BY year DESC"
```

Chế độ online đọc từng chỉ số từ WDI và lưu cache theo URL/tham số. Chế độ offline dùng panel practice đã có trong Git. Cả hai đều dựng OBT ở mức quốc gia × năm và dùng chung `views.sql`. Đối chiếu trung vị giữa các nước có giá trị cùng năm. `n_countries` đếm số nước có quan sát trong nhóm so sánh, ngoài Việt Nam. `gap` để trống nếu Việt Nam hoặc nhóm so sánh thiếu số liệu.

Nhóm so sánh là thành viên ASEAN trong panel đến 2024. Timor-Leste gia nhập 26/10/2025, sau kỳ quan sát. Snapshot hiện có không đủ dữ liệu thu thuế/GDP để tính khoảng cách cho Việt Nam. GDP/người dùng USD hiện hành nên chịu ảnh hưởng của giá và tỷ giá. [ASEAN](https://asean.org/forging-a-new-era-timor-leste-admitted-into-asean/) · [Điều khoản dữ liệu World Bank](https://data.worldbank.org/summary-terms-of-use)
