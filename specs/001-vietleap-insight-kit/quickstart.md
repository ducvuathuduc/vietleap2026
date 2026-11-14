# Quickstart — contest-day runbook

Giờ Việt Nam (Asia/Saigon). Kế hoạch theo giờ và vai trò đầy đủ: [`docs/PLAYBOOK.md`](../../docs/PLAYBOOK.md). Trang này là
chuỗi lệnh tối thiểu để đi từ **đề + dữ liệu** đến **dashboard + deck**; mỗi bước có "kiểm tra xong khi".

## 0. Một lần trước ngày thi
```bash
git clone https://github.com/ducvuathuduc/vietleap2026.git && cd vietleap2026
make setup                                  # .venv + requirements + npm install + Chromium (~5–10 phút)
cp web/.env.example web/.env.local          # điền GROQ_API_KEY nếu có; để trống = offline
export NO_PROXY=localhost,127.0.0.1         # máy có proxy
make demo                                   # 3 dataset luyện tập → out/<ds>/
pytest -q tests && (cd web && npm test && npm run lint)
```
Xong khi: `out/bds_practice/deck.pptx` mở được; test pass.

## 1. 20/11 09:00 — nhận đề
```bash
make api          # terminal 1 → http://localhost:8000/docs
make web          # terminal 2 → http://localhost:3000   (đừng build song song với pipeline)
```
Dán đề vào **Đề bài** (`/brief`) hoặc: `python de.py brief de_bai.md --data data/raw/<file> --out out/brief.json`.
Xong khi: `target.column` là cột thật, cả đội đồng ý câu hỏi quyết định.

## 2. Nạp dữ liệu
Một file:
```bash
python de.py file data/raw/<file>.xlsx --name <ds> --serve [--target <col>]
```
Nhiều nguồn (`sources.yaml`, xem `scenarios/demo/sources.yaml`, `scenarios/conformed/sources.yaml`):
```bash
python de.py run data/raw/sources.yaml --primary <src> --serve
python de.py run data/raw/sources.yaml --primary <src> --serve --mode incremental   # nạp lại chỉ dòng mới
```
Hoặc trên web: nút **Upload dataset** / trang **Nguồn**.
Xong khi: in ra `quality … → …`, các model OBT/Star/Snowflake/Data Vault (+ `conformed` nếu ≥2 nguồn chung khoá) và `load … inserted`.

## 3. Kiểm chứng & giải thích
- **Pipeline / Chất lượng / Mô hình**: số cho slide DE (timings, điểm trước/sau, ERD, join coverage).
- **SQL Explorer** hoặc `python de.py sql "SELECT … FROM gold.obt_<ds> …"`: kiểm chứng mọi số trên slide.
- **Insight → Drivers & What-if → Phân khúc → Quyết định**: chọn 3 insight (effect lớn, p nhỏ, liên quan quyết định).
- **Hỏi AI** (bấm thẻ bất kỳ), **Câu chuyện** (top-5), **Hướng dẫn** (tour) cho người không code.

## 4. Xuất & nộp
- Sidebar → Exports: `deck.pptx`, `dashboard.html`, `executive_summary.pdf`; `out/<ds>/pitch.md` (Marp), `slides/pitch.md` (kịch bản 7 phút).
- Chạy lại `--serve` sau khi chốt dữ liệu để deck cập nhật.
- 21/11 11:00 đóng băng code · nộp trước 12:30 (hạn 13:00) · 13:15 pitch.

## 5. Sự cố nhanh
| Sự cố | Xử lý |
|---|---|
| Upload lỗi | `python de.py file <file> --serve` xem log |
| LLM lỗi/hết quota | xoá khoá trong `web/.env.local`, restart web → offline |
| Web build hỏng | `make web-dev` hoặc mở `out/<ds>/dashboard.html` |
| Warehouse hỏng | `make clean-out` rồi chạy lại bước 2 |
