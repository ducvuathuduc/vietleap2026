"""Data-engineering endpoints: sources → ingest job → warehouse tables → read-only SQL → quality / lineage / models."""
from __future__ import annotations

import json
import threading
import time
import traceback
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from vlkit.de.flow import run_flow, slugify
from vlkit.de.sources import KINDS, Source
from vlkit.de.warehouse import Warehouse

from ..settings import get_settings

router = APIRouter(prefix="/api", tags=["pipeline"])
_wh_lock = threading.Lock()          # DuckDB: one writer; reads share the same connection under the lock
_jobs: dict[str, dict] = {}


class SourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9_]+$")
    kind: str = Field(description=f"one of {KINDS}")
    uri: str = Field(min_length=1, max_length=2000)
    options: dict = {}
    license_note: str = Field("", max_length=500)

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}")
        return v

    @field_validator("uri")
    @classmethod
    def _uri(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("uri must not be blank")
        return v.strip()


class IngestIn(BaseModel):
    dataset: str = Field(min_length=1, max_length=60)
    sources: list[SourceIn] = Field(min_length=1, max_length=20)
    primary: str | None = None
    impute: Literal["median"] | None = None
    serve: bool = True

    @model_validator(mode="after")
    def _consistent(self):
        if not self.dataset.strip():
            raise ValueError("dataset name must not be blank")
        names = [s.name for s in self.sources]
        if len(set(names)) != len(names):
            raise ValueError("source names must be unique")
        if self.primary is not None and self.primary not in names:
            raise ValueError(f"primary '{self.primary}' is not one of the source names {names}")
        return self


class SqlIn(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    limit: int = Field(500, ge=1, le=5000)


def _out(ds: str) -> Path:
    return get_settings().out_dir / slugify(ds)


def _json(ds: str, name: str):
    p = _out(ds) / name
    if not p.exists():
        raise HTTPException(404, f"{name} not found for dataset '{ds}' — run the pipeline first")
    return json.loads(p.read_text(encoding="utf-8"))


@router.get("/sources/kinds")
def source_kinds():
    return {"kinds": list(KINDS), "examples": {
        "file": {"uri": "data/raw/file.xlsx"},
        "api": {"uri": "https://api.worldbank.org/v2/country/VN/indicator/NY.GDP.PCAP.CD",
                "options": {"params": {"format": "json", "per_page": 100}, "records_path": "1", "paging": "worldbank"}},
        "sql": {"uri": "sqlite:///path/to.db", "options": {"query": "SELECT * FROM t"}},
        "scrape": {"uri": "https://vi.wikipedia.org/wiki/Tỉnh_thành_Việt_Nam", "options": {"table_index": "largest"}},
        "social": {"uri": "https://vnexpress.net/rss/kinh-doanh.rss"},
        "cv": {"uri": "scenarios/cv_counting/sample_counts.csv"}}}


@router.post("/ingest", status_code=202)
def ingest(body: IngestIn):
    sources = [Source(**s.model_dump()) for s in body.sources]
    job = {"id": uuid.uuid4().hex[:12], "status": "queued", "dataset": slugify(body.dataset), "error": None,
           "started": time.time(), "finished": None, "summary": None}
    _jobs[job["id"]] = job

    def work():
        with _wh_lock:
            job["status"] = "running"
            wh = Warehouse()
            try:
                s = run_flow(body.dataset, sources, out_root=get_settings().out_dir, wh=wh, impute=body.impute,
                             primary=body.primary, serve=body.serve)
                job["summary"] = {k: s[k] for k in ("dataset", "run_id", "timings", "steps", "gold", "quality")}
                job["status"] = "done"
            except Exception as e:
                job["status"], job["error"] = "error", f"{type(e).__name__}: {e}"
                traceback.print_exc()
            finally:
                wh.close()
                job["finished"] = time.time()

    threading.Thread(target=work, daemon=True).start()
    return job


@router.get("/ingest/{job_id}")
def ingest_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "job not found")
    return _jobs[job_id]


@router.get("/warehouse/tables")
def tables():
    with _wh_lock:
        wh = Warehouse()
        try:
            return wh.tables()
        finally:
            wh.close()


@router.get("/warehouse/tables/{fq}/columns")
def columns(fq: str):
    with _wh_lock:
        wh = Warehouse()
        try:
            return wh.columns(fq)
        finally:
            wh.close()


@router.post("/sql")
def sql(body: SqlIn):
    with _wh_lock:
        wh = Warehouse()
        try:
            df = wh.sql(body.query, limit=body.limit)
        except PermissionError as e:
            raise HTTPException(403, str(e))
        except Exception as e:
            raise HTTPException(400, f"{type(e).__name__}: {e}")
        finally:
            wh.close()
    return {"columns": list(map(str, df.columns)), "rows": json.loads(df.to_json(orient="values", date_format="iso")),
            "row_count": len(df)}


@router.get("/datasets/{ds}/pipeline")
def pipeline_summary(ds: str):
    return _json(ds, "pipeline.json")


@router.get("/datasets/{ds}/quality")
def quality(ds: str):
    return _json(ds, "quality.json")


@router.get("/datasets/{ds}/lineage")
def lineage(ds: str):
    g = _json(ds, "lineage.json")
    mmd = _out(ds) / "lineage.mmd"
    g["mermaid"] = mmd.read_text(encoding="utf-8") if mmd.exists() else None
    return g


@router.get("/datasets/{ds}/models")
def models(ds: str):
    p = _json(ds, "pipeline.json")
    d = _out(ds) / "models"
    sql = {f.stem: f.read_text(encoding="utf-8") for f in d.glob("*.sql")} if d.exists() else {}
    return {"models": p["models"], "sql": sql, "rationale": p["rationale"], "recommended": p["recommended"],
            "column_plan": p["column_plan"]}


@router.get("/datasets/{ds}/provenance")
def provenance(ds: str):
    return _json(ds, "provenance.json")
