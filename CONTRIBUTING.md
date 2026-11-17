# Đóng góp cho VietLeap Insight Kit

Cảm ơn bạn đã muốn đóng góp. Dự án theo [constitution](.specify/memory/constitution.md) gồm 8 nguyên tắc bắt buộc — quan trọng nhất:
**không bịa số** (mọi con số đến từ engine/DuckDB), **không kết luận nhân quả từ dữ liệu quan sát**, **chỉ dùng thành phần mã nguồn mở**,
**giữ nguyên mọi kiểm soát bảo mật**. Thay đổi vi phạm nguyên tắc NON-NEGOTIABLE sẽ bị từ chối.

## 1. Cài môi trường
Cần Python 3.11+ (CI: 3.12), Node.js 20+ (CI: 22), `make`, Git.

```bash
git clone https://github.com/ducvuathuduc/vietleap2026.git && cd vietleap2026
make setup                 # .venv, requirements.txt, npm install trong web/, Chromium headless
source tools/env.sh        # đưa .venv + engine/ vào PATH/PYTHONPATH
export NO_PROXY=localhost,127.0.0.1
```

Đọc trước khi viết code: [`AGENTS.md`](AGENTS.md), [`web/AGENTS.md`](web/AGENTS.md) (Next.js 16 có breaking changes — tra `web/node_modules/next/dist/docs/`),
[`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) §0.

## 2. Kiểm tra — chạy **tuần tự**, không song song
Máy mục tiêu chỉ có 2 CPU / 7 GB RAM: đừng chạy build web cùng lúc với pytest hay engine.

```bash
make test-py                 # pytest -q tests
make test-web                # cd web && npm test && npm run lint
cd web && npm run build      # khi có thay đổi trong web/
python tools/export_openapi.py   # khi đổi API — CI báo lỗi nếu openapi.json lệch
```

Viết test **trước** (pytest cho Python, `node --test` cho web), xem test đỏ, rồi mới sửa code. Không tắt hay bỏ qua test.

## 3. Quy ước code
- Hàm nhỏ, tên rõ, có type hint (Python) / TypeScript strict; theo mẫu sẵn có; không để code chết, TODO hay trùng lặp.
- Chữ hiển thị: tiếng Việt có dấu (có thể kèm EN); chuỗi cố định của deck/pitch nằm trong `engine/vlkit/i18n.py` (đủ hai ngôn ngữ, cùng con số).
- UI: chỉ component shadcn chính thức (`npx shadcn@latest add …`), không đổi theme/màu/font/spacing của `dashboard-01`.
- Dependency mới phải là giấy phép OSI; ghi vào `requirements.txt` hoặc `web/package.json` **và** [`docs/licenses.md`](docs/licenses.md).
- Đổi hợp đồng API → cập nhật `specs/<feature>/contracts/`, chạy lại `python tools/export_openapi.py`, thêm test.
- Không commit: `node_modules/`, `.venv/`, `.tools/`, `out/`, `data/raw/`, `data/warehouse.duckdb`, `data/lake/`, `data/cache/`, `.env*`, file > 20 MB.
  Kiểm `git status` trước mỗi commit.

## 4. Commit — Conventional Commits
`<type>(<scope>): <tóm tắt>` với `type` ∈ `feat`, `fix`, `docs`, `test`, `refactor`, `ci`, `chore`. Scope thường là số feature (`003`) hoặc khối (`de`, `web`, `security`). Ví dụ:

```
feat(003): T306–T308 --lang vi|en|both
fix(security): reject private-network URLs in ingest sources
docs(003): tick T301–T312 with commit hashes
```

Một nhóm task = một commit; ghi mã task (`T301`…) trong tiêu đề khi có.

## 5. Quy trình Spec Kit
Mỗi tính năng là một thư mục `specs/NNN-ten/` ([chỉ mục](specs/README.md)):
1. `spec.md` — user story P1–P3 (Given/When/Then), FR/NFR, tiêu chí thành công, edge case; điểm chưa rõ đánh dấu `[NEEDS CLARIFICATION]`.
2. `plan.md` — bối cảnh kỹ thuật, **Constitution Check**, file sẽ sửa, thư viện tái sử dụng + giấy phép, bảo mật (OWASP Top 10 / OWASP LLM Top 10).
3. `tasks.md` — task đánh số, test trước, tiêu chí xong.
4. `contracts/` — khi đổi API/tool.

Khi xong: tick task kèm hash commit, cập nhật trạng thái trong `specs/README.md`, `docs/MASTER_PLAN.md` §0 và mục "Progress" của `docs/ROADMAP.md`.

## 6. Pull request
Dùng [mẫu PR](.github/pull_request_template.md). CI (`ci.yml`) và Security (`security.yml`) phải xanh. Mô tả rõ: task/spec liên quan, test đã chạy (số pass/skip),
ảnh chụp khi đổi giao diện, rủi ro bảo mật.

## 7. Báo lỗi & lỗ hổng
Lỗi thường: mở issue theo [mẫu bug](.github/ISSUE_TEMPLATE/bug_report.md). **Lỗ hổng bảo mật: không mở issue công khai** — làm theo [`SECURITY.md`](SECURITY.md).
Hành xử trong cộng đồng: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
