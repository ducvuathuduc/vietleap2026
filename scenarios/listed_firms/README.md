# Doanh nghiệp niêm yết

```bash
python de.py run scenarios/listed_firms/sources.yaml --serve --target roe_pct
```

Recipe practice đọc các sheet cùng cấu trúc trong workbook, ghép theo mã chứng khoán và phân tích OBT đã hợp nhất. Header phổ biến nằm trong [pack doanh nghiệp](../packs/listed_firms_market.yaml). ROE được tính theo kỳ từ lợi nhuận sau thuế và vốn chủ sở hữu dương. Mô hình ROE loại ngân hàng, bảo hiểm và chứng khoán khi có cột ngành phù hợp. Bảng tổng quan giữ các doanh nghiệp tài chính để người dùng xem độ phủ. Kiểm tra lại ánh xạ và điều khoản khi nhận dữ liệu FiinGroup.
