"""FastAPI app exposing the VietLeap Insight engine.

Run:  uvicorn api.main:app --port 8000      (from the kit folder, after `source tools/env.sh`)
"""
from __future__ import annotations

import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "engine"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from .routes import agent, analysis, brief, datasets, pipeline  # noqa: E402
from .settings import get_settings  # noqa: E402

app = FastAPI(title="VietLeap Insight API", version="1.0.0",
              description="Upload a dataset → profile → ranked insights → drivers → what-if → exports, plus a tool-using AI analyst.")
app.add_middleware(CORSMiddleware, allow_origins=list(get_settings().cors_origins), allow_methods=["*"], allow_headers=["*"])
app.include_router(datasets.router)
app.include_router(analysis.router)
app.include_router(agent.router)
app.include_router(pipeline.router)
app.include_router(brief.router)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})


@app.get("/api/health")
def health():
    return {"status": "ok", "datasets": len(list(get_settings().out_dir.glob("*/results.json")))}
