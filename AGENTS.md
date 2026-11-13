# AGENTS.md — hướng dẫn cho Codex / coding agent

Đọc `docs/MASTER_PLAN.md` trước. Làm task theo thứ tự T1 → T12, mỗi task một commit.

## Cấu trúc
- `engine/vlkit/` — Python engine (pandas). Entry: `run.py`. Import: `sys.path` thêm `engine/` (xem `tests/conftest.py`, `tools/env.sh`).
- `api/` — FastAPI (`uvicorn api.main:app --port 8000`), route trong `api/routes/`, job nền `api/jobs.py`.
- `web/` — Next.js 16 + shadcn/ui block `dashboard-01` (style base-nova). **Đọc `web/AGENTS.md`**: Next 16 có breaking changes, tra `web/node_modules/next/dist/docs/` trước khi viết.
- `scenarios/`, `slides/`, `docs/`, `tests/`, `tools/`.

## Quy tắc bắt buộc
1. Máy yếu (2 CPU, 7 GB RAM): không chạy song song `npm run build` với engine/pytest nặng.
2. UI: chỉ dùng component shadcn chính thức (`npx shadcn@latest add ...`). Không tự đổi theme, màu, font, spacing của dashboard-01.
3. Chỉ dùng thư viện open-source. Thêm dependency Python vào `requirements.txt`, JS qua `npm i`.
4. Không bịa số liệu. Mọi số trong UI/deck/AI phải đến từ engine/DuckDB.
5. Text hiển thị: tiếng Việt có dấu (có thể kèm EN). Thời gian: Asia/Saigon.
6. Scraping: tôn trọng robots.txt, có delay, không vượt captcha/đăng nhập.
7. Không commit: `node_modules/`, `.venv/`, `.tools/`, `out/`, `data/raw/`, `data/warehouse.duckdb`, `data/lake/`, `data/cache/`, file > 20 MB, file `.env`.

## Lệnh kiểm tra
```bash
source tools/env.sh            # hoặc: python -m venv .venv && pip install -r requirements.txt
pytest -q tests
python run.py --help
cd web && npm run lint && npm run build
```
Task xong khi tiêu chí "Xong khi" trong MASTER_PLAN đạt và các lệnh trên pass.
