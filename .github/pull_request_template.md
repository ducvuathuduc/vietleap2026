## Tóm tắt
<!-- Thay đổi gì, vì sao. Tiêu đề PR theo Conventional Commits: feat(003): …, fix(security): … -->

## Spec / task
- Spec: `specs/NNN-…/` · Task: T…
- [ ] `tasks.md` đã tick kèm hash; `specs/README.md`, `docs/MASTER_PLAN.md` §0, `docs/ROADMAP.md` (Progress) đã cập nhật nếu cần

## Kiểm tra (chạy tuần tự)
- [ ] `make test-py` — pass / skip / fail: …
- [ ] `make test-web` (node tests + eslint)
- [ ] `cd web && npm run build` (nếu sửa `web/`)
- [ ] `python tools/export_openapi.py` không làm `openapi.json` lệch (nếu sửa API) và `contracts/` đã cập nhật

## Constitution & bảo mật
- [ ] Không có số bịa — mọi số từ engine/DuckDB
- [ ] Không có câu khẳng định nhân quả từ dữ liệu quan sát
- [ ] Dependency mới có giấy phép OSI, ghi trong `docs/licenses.md`
- [ ] Kiểm soát bảo mật giữ nguyên (SQL chỉ đọc, SSRF/path guard, upload, CSP, rate limit, quy tắc prompt injection)
- [ ] Không commit `.env*`, `out/`, `data/raw/`, `data/warehouse.duckdb`, `data/lake/`, `data/cache/`, `node_modules/`, file > 20 MB

## Ảnh chụp (nếu đổi giao diện)
