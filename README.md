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
| `make demo` | Chạy lần lượt các dataset trong `data/practice/` qua toàn bộ pipeline → `out/<tên>/` (insight, deck.pptx, executive_summary, dashboard.html) |
| `make api` | FastAPI `http://localhost:8000` (tài liệu: `/docs`) — terminal 1 |
| `make web` | Build + chạy dashboard `http://localhost:3000` — terminal 2 (cần `make api`) |
| `make web-dev` | Dashboard chế độ dev (hot reload, tốn RAM hơn) |
| `make demo-online` | Demo nhiều nguồn: CSV + SQLite + World Bank API + Wikipedia + RSS → một warehouse |
| `make brief F=scenarios/briefs/bds_gia_m2.md D=data/practice/synthetic_messy_bds.csv` | Đề bài → `brief.json` (câu hỏi, biến mục tiêu, phân khúc, loại quyết định) |
| `make test` | pytest + unit test web + eslint (đừng chạy song song với `make web` trên máy yếu) |

CLI trực tiếp: `python de.py file <file> --serve` · `python de.py run <sources.yaml> --primary <ds> --serve` · `python de.py tables` · `python de.py sql "SELECT ..."`.

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

## 5. Cấu trúc

```
engine/vlkit/      engine Python: de/ (connectors, warehouse DuckDB, quality, modeling, flow), insights, stats, brief, report
api/               FastAPI (routes/, jobs nền)
web/               Next.js 16 + shadcn/ui dashboard-01 + Vercel AI SDK + driver.js
scenarios/         packs/ (7 miền đề), briefs/ (11 đề mẫu), demo/ (nguồn nhiều loại), cv_counting/
docs/  slides/  tests/  tools/
```

Toàn bộ open-source (Apache-2.0, xem `LICENSE`). Dữ liệu sinh ra (`out/`, `data/warehouse.duckdb`, `data/lake/`, `data/raw/`) không được commit.
