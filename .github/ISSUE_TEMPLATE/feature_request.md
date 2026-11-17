---
name: Feature request
about: Đề xuất tính năng — sẽ thành một spec trong specs/ theo quy trình Spec Kit
title: "feat: "
labels: enhancement
---

## Vấn đề / người dùng
<!-- Ai cần gì, vì sao? Ví dụ: "Là storyteller, tôi muốn … để …" -->

## Đề xuất
<!-- Hành vi mong muốn; tiêu chí chấp nhận dạng Given/When/Then nếu có -->

## Phương án đã cân nhắc
<!-- Thư viện mã nguồn mở có sẵn (ghi giấy phép), lựa chọn bị loại và lý do -->

## Đối chiếu constitution
- [ ] Mọi số vẫn đến từ engine/DuckDB (không bịa số)
- [ ] Không biến liên đới thành nhân quả
- [ ] Chỉ dùng thành phần giấy phép OSI / dữ liệu mở
- [ ] Không nới lỏng kiểm soát bảo mật (SQL chỉ đọc, SSRF/path guard, giới hạn upload, CSP, rate limit)
- [ ] Có đường offline khi không có khoá LLM

## Liên quan
<!-- spec / task / issue liên quan, ví dụ specs/009-one-click-export -->
