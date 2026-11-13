# Đề mẫu (briefs)

Dán nội dung một file vào trang **Đề bài** trên dashboard, hoặc chạy:

```bash
python de.py brief scenarios/briefs/bds_gia_m2.md --data data/practice/synthetic_messy_bds.csv
```

| File | Dataset luyện tập | Mục tiêu kỳ vọng | Pack |
|---|---|---|---|
| bds_gia_m2.md | synthetic_messy_bds.csv | price_per_m2 | data_economy_property |
| bds_gia_thue.md | synthetic_messy_bds.csv | Giá thuê/tháng | data_economy_property |
| firms_roe.md | vn_firms_2021.xlsx | roe_pct | listed_firms_market |
| wdi_tax_revenue.md | wdi_asia_fiscal_panel.csv | tax_revenue_pct_gdp | development_indicators |
| wdi_no_cong.md | wdi_asia_fiscal_panel.csv | central_gov_debt_pct_gdp | development_indicators |
| ngan_sach_tinh.md | (tự thu thập) | — | public_finance_province |
| chinh_sach_luong.md | (tự thu thập) | — | economic_policy |
| du_lieu_mo_bds.md | (scraping + API) | — | data_economy_property |
| chi_so_phat_trien.md | WDI API | — | development_indicators |
| tac_dong_xa_hoi.md | (tự thu thập) | — | social_impact |
| dem_xe_giao_thong.md | video → CV | — | cv_observation |

Các bảng kỳ vọng ở trên được kiểm thử trong `tests/test_brief.py`.
