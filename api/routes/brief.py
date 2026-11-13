"""Problem statement → analysis plan (T8). Rule-based, offline; see engine/vlkit/brief.py."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from vlkit.brief import load_packs, parse_brief
from vlkit.vn import slug

from ..settings import get_settings

router = APIRouter(prefix="/api", tags=["brief"])
BRIEFS = Path(__file__).resolve().parents[2] / "scenarios" / "briefs"


class BriefIn(BaseModel):
    text: str = Field(min_length=10, max_length=20_000)
    dataset: str | None = Field(None, max_length=80, pattern=r"^[\w.-]+$")


def _dataset_columns(ds: str) -> list[str]:
    p = get_settings().out_dir / ds / "results.json"
    if not p.exists():
        raise HTTPException(404, f"dataset '{ds}' not found — run the pipeline first")
    meta = json.loads(p.read_text(encoding="utf-8"))["meta"]
    return list(meta.get("roles", {}))          # includes engine-derived metrics (price_per_m2, roe_pct …)


@router.post("/brief")
def brief(body: BriefIn):
    columns = _dataset_columns(body.dataset) if body.dataset else None
    try:
        b = parse_brief(body.text, columns=columns)
    except ValueError as e:
        raise HTTPException(422, str(e))
    b["dataset"] = body.dataset
    if body.dataset:                               # persist next to the dataset's other outputs
        (get_settings().out_dir / slug(body.dataset) / "brief.json").write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
    return b


@router.get("/brief/packs")
def packs():
    return [{k: p[k] for k in ("id", "title", "sponsor", "domain", "kpis", "decision_template")} for p in load_packs()]


@router.get("/brief/samples")
def samples():
    return [{"name": p.stem, "text": re.sub(r"<!--.*?-->\s*", "", p.read_text(encoding="utf-8"), flags=re.S)} for p in sorted(BRIEFS.glob("*.md")) if p.name != "README.md"]
