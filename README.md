# VietLeap Insight Kit — From Data to Decision

Bộ công cụ cho **VietLeap Hackathon 2026** (UEH School of Public Finance × AVSE Economic Policy Network): thả dataset + đề bài → pipeline Data Engineering (Ingestion → Storage → Transform → Serving), insight có kiểm định thống kê, drivers & what-if, khuyến nghị quyết định, dashboard shadcn, AI Analyst "Hỏi AI", deck pitch. Mọi con số đến từ engine/DuckDB — không bịa số.

> Đọc thêm: [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md) (kế hoạch theo giờ hôm thi, chia vai) · [`docs/CONTEXT.md`](docs/CONTEXT.md) (bối cảnh cuộc thi → miền đề có thể ra) · [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md) (kiến trúc, trạng thái).

## 1. Cài đặt (một lần, ~5–10 phút)

Cần: Python ≥ 3.11, Node.js ≥ 20, `make`, Git. Linux/macOS (Windows: dùng WSL2).

```bash
git clone https://github.com/ducvuathuduc/vietleap2026.git && cd vietleap2026
make setup                       # .venv + requirements.txt + npm install + Chromium headless (xuất PNG/PDF)
cp web/.env.example web/.env.local   # rồi điền khoá LLM nếu có (mục 3)
```

Máy có proxy: `export NO_PROXY=localhost,127.0.0.1` (Makefile đã tự đặt cho `api`/`demo`).

## 2. Chạy

| Lệnh | Việc |
|---|---|
| `make demo` | Chạy lần lượt các dataset trong `data/practice/` qua toàn bộ pipeline → `out/<tên>/` (insight, deck.pptx 15 slide gồm pipeline/mô hình/chất lượng/provenance, pitch.md Marp, executive_summary, dashboard.html) |
| `make api` | FastAPI `http://localhost:8000` (tài liệu: `/docs`) — terminal 1 |
| `make web` | Build + chạy dashboard `http://localhost:3000` — terminal 2 (cần `make api`) |
| `make web-dev` | Dashboard chế độ dev (hot reload, tốn RAM hơn) |
| `make demo-online` | Demo nhiều nguồn: CSV + SQLite + World Bank API + Wikipedia + RSS → một warehouse |
| `make brief F=scenarios/briefs/bds_gia_m2.md D=data/practice/synthetic_messy_bds.csv` | Đề bài → `brief.json` (câu hỏi, biến mục tiêu, phân khúc, loại quyết định) |
| `make test` | pytest + unit test web + eslint (đừng chạy song song với `make web` trên máy yếu) |

CLI trực tiếp: `python de.py file <file> --serve` · `python de.py run <sources.yaml> --primary <ds> --serve` · `python de.py tables` · `python de.py sql "SELECT ..."`.

Nạp lại dữ liệu (`de.py file|run`, và trường `mode` của `POST /api/ingest`): `--mode replace` (mặc định, ghi đè bronze) · `--mode append` (thêm mọi dòng) ·
`--mode incremental` (chỉ thêm dòng có `_row_hash` mới; bộ cột đổi → tự dựng lại bảng). Số dòng thêm/bỏ qua nằm trong `pipeline.json` (`load`) và `meta.runs`.

## 3. Biến môi trường AI Analyst (`web/.env.local`)

Không có khoá nào → AI chạy **offline**: trả lời bằng insight/pipeline/quality do engine tính (vẫn dùng được khi demo mất mạng).

```dotenv
API_URL=http://127.0.0.1:8000
# Lựa chọn 1 — Groq (miễn phí, nhanh)
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
# Lựa chọn 2 — bất kỳ endpoint OpenAI-compatible (OpenRouter, Together, Ollama http://localhost:11434/v1, LM Studio…)
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_MODEL=
OPENAI_COMPATIBLE_API_KEY=
```

Groq được ưu tiên nếu cả hai cùng có. Không commit `.env*` có khoá thật.

## 4. Luồng dùng trong 1 phút

**Đề bài** (dán đề → kế hoạch) → **Upload** (nút tải dữ liệu / trang Nguồn) → **Pipeline / Chất lượng / Mô hình** (giải thích cho giám khảo) → **Insight / Drivers & What-if / Phân khúc** → **Hỏi AI** (bật ở thanh trên, bấm vào bất kỳ thẻ/biểu đồ) → **Quyết định** → **Exports → deck.pptx**.

## 5. Bảo mật, CI, Docker

- **Bảo mật** (chi tiết: [`SECURITY.md`](SECURITY.md), [`docs/security/threat-model.md`](docs/security/threat-model.md)): công cụ chạy cục bộ, không đăng nhập — API chỉ bind `127.0.0.1`.
  SQL chỉ đọc (DuckDB `read_only`, tắt truy cập file/mạng, chặn hàm đọc file/env, timeout 20 s); nguồn gửi qua API bị chặn địa chỉ mạng nội bộ (SSRF) và đường dẫn ngoài thư mục cho phép;
  upload giới hạn loại/kích thước; header bảo mật + CSP; CORS không wildcard; rate limit 60/phút (API) và 20/phút (`/api/chat`, `/api/story`); tool AI chỉ đọc, output tool là dữ liệu, không phải lệnh.
  Khoá LLM chỉ để trong `web/.env.local` (đã git-ignore).
- **CI** (GitHub Actions): `.github/workflows/ci.yml` — pytest + kiểm tra `openapi.json` không lệch (`python tools/export_openapi.py`), web `npm ci && npm test && npm run lint && npm run build`;
  `.github/workflows/security.yml` — gitleaks (toàn lịch sử), pip-audit, `npm audit --audit-level=high`, CodeQL (Python + TS), chạy hằng tuần; Dependabot cho pip/npm/actions.
- **Docker** (chưa chạy thử trên máy dev): `docker compose up --build` → dashboard `http://localhost:3000`, API `http://localhost:8000/docs`; cổng chỉ mở trên 127.0.0.1;
  khoá LLM đọc từ `web/.env.local` nếu có.

## 6. Spec & lộ trình

Spec Kit: [`specs/README.md`](specs/README.md) (feature 001 đã xong; 002–011 là phần còn lại, có ước lượng và phụ thuộc) · lịch 16–21/11: [`docs/ROADMAP.md`](docs/ROADMAP.md).

## 7. Cấu trúc

```
engine/vlkit/      engine Python: de/ (connectors, warehouse DuckDB, quality, modeling, flow), insights, stats, brief, report
api/               FastAPI (routes/, jobs nền)
web/               Next.js 16 + shadcn/ui dashboard-01 + Vercel AI SDK + driver.js
scenarios/         packs/ (7 miền đề), briefs/ (11 đề mẫu), demo/ (nguồn nhiều loại), conformed/, cv_counting/
specs/             Spec Kit: 001 (đã xong) + 002–011 (còn lại)
.github/           CI + Security workflows, Dependabot
docs/  slides/  tests/  tools/
```

Toàn bộ open-source (Apache-2.0, xem `LICENSE`). Dữ liệu sinh ra (`out/`, `data/warehouse.duckdb`, `data/lake/`, `data/raw/`) không được commit.
