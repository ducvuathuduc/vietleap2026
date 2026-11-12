# VietLeap Hackathon 2026 — Insight Kit (WIP)

Toolkit for **VietLeap Hackathon: From Data to Decision** (UEH, 19–21/11/2026): drop in the organisers' dataset → profile, ranked insights, drivers & what-if, dashboard, AI analyst, pitch deck.

Status: work in progress. `engine/` (Python analysis engine) and `run.py` run end-to-end; `api/` (FastAPI) and `web/` (Next.js + shadcn/ui) are being finished.

```bash
bash tools/setup_env.sh && source tools/env.sh
python run.py data/practice/<file>.csv --name demo
```
