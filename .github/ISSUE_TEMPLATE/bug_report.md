---
name: Bug report
about: Báo lỗi trong engine, API, dashboard hoặc deck (không dùng cho lỗ hổng bảo mật — xem SECURITY.md)
title: "fix: "
labels: bug
---

## Mô tả lỗi
<!-- Điều gì sai? Một câu. -->

## Cách tái hiện
1. Lệnh / trang: <!-- ví dụ: python de.py file data/practice/synthetic_messy_bds.csv --serve --lang vi -->
2. Dữ liệu: <!-- file practice nào, hoặc mô tả cột; KHÔNG đính kèm dữ liệu cá nhân hay khoá API -->
3. Kết quả thấy:
4. Kết quả mong đợi:

## Môi trường
- Commit (`git rev-parse --short HEAD`):
- OS / CPU / RAM:
- Python (`python --version`) / Node (`node --version`):
- Có khoá LLM hay chạy offline:

## Log
<details><summary>Traceback / console</summary>

```
dán log ở đây (đã che khoá, đường dẫn riêng tư)
```
</details>

## Kiểm tra
- [ ] Đã thử trên `main` mới nhất
- [ ] Không chứa secret, dữ liệu cá nhân
- [ ] Nếu sai số liệu: ghi rõ số trên UI/deck và số đúng từ SQL (`python de.py sql "..."`)
