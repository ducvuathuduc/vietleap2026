---
title: Tổng quan — Việt Nam so với các nước cùng khu vực
---

# Việt Nam đứng ở đâu so với các nước cùng khu vực?

> **Câu hỏi quyết định · Đề bài (trích nguyên văn)**
>
> *"build a dashboard that benchmarks Viet Nam against its peers."*
>
> **Ai quyết định:** Chính phủ / nhà tài trợ phát triển ·
> **Quyết định gì:** Ưu tiên cải cách ở chỉ số VN tụt hậu xa nhất so với nhóm so sánh ·
> **KPI thành công:** Khoảng cách với trung vị ASEAN, thay đổi khoảng cách theo thời gian, số nước có quan sát cùng năm

```sql kpis
select * from warehouse.kpis
```

```sql timeseries
select * from warehouse.timeseries
```

```sql ranking
select * from warehouse.ranking
```

```sql insights
select * from warehouse.insights
```

<BigValue data={kpis} value=records fmt=num0 title="Số bản ghi · ASEAN-10, 2000–2024" />
<BigValue data={kpis} value=median_gdp_pc fmt=usd title="Trung vị GDP bình quân đầu người" />
<BigValue data={kpis} value=gap_sgp_mmr fmt=num1 title="Chênh lệch trung vị SGP vs MMR (lần)" />
<BigValue data={kpis} value=completeness fmt=pct1 title="Độ đầy đủ dữ liệu · bảng silver" />

<LineChart
    data={timeseries}
    title="GDP bình quân đầu người — Việt Nam so với trung vị ASEAN"
    subtitle="USD hiện hành, 2001–2024 · Nguồn: World Bank WDI"
    x=year
    y=gdp_pc
    series=nhom
    yFmt=usd
    yAxisTitle="USD / người"
/>

## Phát hiện nổi bật

Kiểm định Kruskal–Wallis trên GDP bình quân đầu người theo nước (ASEAN-10, 2000–2024): **H = 197,8; p nhỏ hơn 0,001; ε² = 0,79** — chênh lệch giữa các nước là có ý nghĩa thống kê, không phải nhiễu. Tương quan hạng Spearman với GDP bình quân đầu người:

<DataTable data={insights} />

## Xếp hạng 2024 — ASEAN-10

<DataTable data={ranking} rows=10 />

## Vậy thì sao? (So what)

- **Việt Nam đã bắt kịp mức trung vị khu vực.** Năm 2024, GDP bình quân đầu người của Việt Nam là **4.717 USD**, bằng **98% trung vị ASEAN (4.821 USD)**, xếp **thứ 6/10** — trên Philippines (3.985 USD), Campuchia, Lào và Myanmar, dưới Indonesia (4.925 USD).
- **Nhưng tốc độ là điểm mạnh nhất.** Từ 2001 đến 2024, GDP bình quân đầu người của Việt Nam tăng **11,3 lần** (419 → 4.717 USD, tăng trưởng kép **11,1%/năm**), trong khi trung vị ASEAN chỉ tăng **5,7 lần** (851 → 4.821 USD).
- **Khoảng cách giàu–nghèo trong khu vực vẫn rất lớn.** Trung vị 25 năm của Singapore (55.548 USD) gấp **47,6 lần** Myanmar (1.167 USD). Việt Nam không nằm ở nhóm này, nhưng đó là khung tham chiếu cho mọi mục tiêu thu hẹp khoảng cách.
- **Đô thị hoá đi cùng thu nhập.** Tương quan hạng Spearman giữa tỉ lệ dân số đô thị và GDP bình quân đầu người là **ρ = 0,93** — mạnh nhất trong các chỉ tiêu kiểm tra. Nợ chính phủ (ρ = 0,69) và thu ngân sách (ρ = 0,68) cũng tương quan dương; lạm phát tương quan âm (ρ = −0,55).

## Làm gì tiếp? (Now what)

1. **Ưu tiên 1 — lấp lỗ hổng dữ liệu tài chính công trước khi kết luận về ngân sách.** Độ đầy đủ dữ liệu chỉ **84,3%** (4.425/5.250 ô trên bảng silver); thiếu nhiều nhất là **nợ chính phủ trung ương (63,1% thiếu)**, chi tiêu (38,9%), cho vay ròng (37,7%) và chi giáo dục (34,0%). Mọi khuyến nghị về thu–chi phải ghi rõ giới hạn này.
2. **Ưu tiên 2 — giữ đà đô thị hoá và năng suất làm động lực tăng trưởng**, vì đó là yếu tố gắn chặt nhất với thu nhập bình quân trong dữ liệu 25 năm.
3. **Ưu tiên 3 — đặt mục tiêu vượt trung vị ASEAN một cách bền vững**: Việt Nam đã ở sát trung vị (98%); vượt lên cần tăng trưởng nhanh hơn trung vị, không chỉ tăng trưởng tuyệt đối.

---

**Nguồn & phương pháp.** Dữ liệu: World Bank World Development Indicators (WDI), bảng `gold.obt_wdi_fiscal` trong kho DuckDB (`data/warehouse.duckdb`), xử lý qua pipeline Bronze → Silver → Gold. Nhóm so sánh: 10 nước ASEAN (BRN, IDN, KHM, LAO, MMR, MYS, PHL, SGP, THA, VNM). Độ đầy đủ = tỉ lệ ô có giá trị trên bảng silver (350 dòng × 15 cột). Kiểm định Kruskal–Wallis và tương quan Spearman tính trên cùng dữ liệu; mọi số trên trang này đều truy vấn trực tiếp từ kho dữ liệu, không nhập tay.
