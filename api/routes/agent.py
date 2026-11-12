"""AI Analyst endpoints: Server-Sent Events stream of agent events."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from vlkit import tools as T

from ..agent import runner
from ..schemas import ChatRequest
from ..settings import get_settings
from ..store import Store, get_store
from .datasets import ds_or_404

router = APIRouter(prefix="/api", tags=["agent"])


@router.get("/agent/config")
def agent_config():
    s = get_settings()
    return {"mode": "llm" if s.llm_api_key else "offline", "model": s.llm_model if s.llm_api_key else None,
            "base_url": s.llm_base_url if s.llm_api_key else None, "tools": list(T.TOOLS)}


@router.post("/datasets/{ds_id}/agent")
def chat(ds_id: str, req: ChatRequest, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    ctx = T.Context(ds.df, ds.results, ds.whatif)
    settings = get_settings()
    history = [m.model_dump() for m in req.history]

    def gen():
        try:
            for ev in runner.run(ctx, req.message, history, settings, auto_n=req.top_n if req.auto else None):
                yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:  # never leave the client hanging
            yield f"data: {json.dumps({'type': 'error', 'text': f'{type(e).__name__}: {e}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'text': ''})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
