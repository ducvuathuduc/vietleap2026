"""Dataset lifecycle: list, upload (async analysis job), summary, profile, rows, exports."""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from vlkit.de.exports import DICTIONARY_CSV, DICTIONARY_MD, EDA_MD
from vlkit.vn import slug

from .. import jobs
from ..schemas import DatasetSummary, Job, RowsResponse
from ..settings import get_settings
from ..store import NotFound, Store, get_store

router = APIRouter(prefix="/api", tags=["datasets"])
ALLOWED = {".csv", ".tsv", ".txt", ".xlsx", ".xls", ".xlsm", ".json", ".parquet"}
MAX_BYTES = 200 * 1024 * 1024
DATA_EXPORTS = {"dictionary_csv": (DICTIONARY_CSV, "text/csv"), "dictionary_md": (DICTIONARY_MD, "text/markdown"),
                "eda_md": (EDA_MD, "text/markdown"), "bundle": ("export/bundle.zip", "application/zip"),
                "dashboard_pdf": ("export/dashboard.pdf", "application/pdf")}
EXPORTS = {"deck": ("deck.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
           "dashboard": ("dashboard.html", "text/html"), "summary_pdf": ("executive_summary.pdf", "application/pdf"),
           "summary_md": ("executive_summary.md", "text/markdown"), "results": ("results.json", "application/json"),
           "clean_csv": ("clean_sample.csv", "text/csv"),
           # feature 003 — names fixed per language (vlkit.report DECK_FILES / PITCH_FILES)
           "deck_vi": ("deck.vi.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
           "pitch_md": ("pitch.md", "text/markdown"), "pitch_en": ("pitch.en.md", "text/markdown"), **DATA_EXPORTS}


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lang: Literal["vi", "en", "both"] = "both"
    dashboard_pdf: bool = True


class ExportStart(BaseModel):
    job_id: str


class ExportJob(BaseModel):
    id: str
    dataset: str
    status: Literal["queued", "running", "done", "done_with_warnings", "error"]
    progress: float = Field(ge=0, le=1)
    step: str | None
    warnings: list[str]
    error: str | None
    files: dict[str, str]
    started_at: str
    finished_at: str | None


def ds_or_404(store: Store, ds_id: str):
    try:
        return store.get(ds_id)
    except NotFound:
        raise HTTPException(404, f"dataset '{ds_id}' not found")


def _available_export(dataset: Path, filename: str) -> bool:
    path = dataset / filename
    try:
        if not path.is_file() or not path.resolve().is_relative_to(dataset.resolve()):
            return False
        return (PurePosixPath(filename).parts[0] != "export"
                or path.stat().st_mtime_ns >= (dataset / "results.json").stat().st_mtime_ns)
    except FileNotFoundError:
        return False


@router.get("/datasets", response_model=list[DatasetSummary])
def list_datasets(store: Store = Depends(get_store)):
    return store.list()


@router.post("/datasets", response_model=Job, status_code=202)
async def upload(file: UploadFile = File(...), target: str | None = Form(None), time: str | None = Form(None),
                 geo: str | None = Form(None), domain: str = Form("auto"), name: str | None = Form(None),
                 lang: Literal["vi", "en", "both"] = Form("both", description="deck/pitch language(s)")):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(415, f"unsupported file type '{ext}'; allowed: {sorted(ALLOWED)}")
    if domain not in ("auto", "property", "public_finance", "firm", "generic"):
        raise HTTPException(422, "domain must be auto|property|public_finance|firm|generic")
    s = get_settings()
    s.upload_dir.mkdir(parents=True, exist_ok=True)
    ds_name = slug(name or Path(file.filename).stem)[:60] or "dataset"
    dest = s.upload_dir / f"{ds_name}{ext}"
    tmp = dest.with_suffix(dest.suffix + ".part")
    size = 0
    with tmp.open("wb") as fh:                      # stream in 1 MB chunks: never hold > 1 MB in RAM, stop at the cap
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > MAX_BYTES:
                fh.close()
                tmp.unlink(missing_ok=True)
                raise HTTPException(413, "file larger than 200 MB")
            fh.write(chunk)
    if size == 0:
        tmp.unlink(missing_ok=True)
        raise HTTPException(422, "empty file")
    tmp.replace(dest)
    return jobs.submit(dest, ds_name, target=target or None, time_col=time or None, geo_col=geo or None, domain=domain, lang=lang)


@router.get("/jobs/{job_id}", response_model=Job)
def job_status(job_id: str):
    j = jobs.get(job_id)
    if not j:
        raise HTTPException(404, "job not found")
    return j


@router.get("/datasets/{ds_id}")
def summary(ds_id: str, store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    r = ds.results
    files = {**r.get("files", {}), **{key: filename for key, (filename, _) in DATA_EXPORTS.items() if _available_export(ds.path, filename)}}
    return {"meta": r["meta"], "kpis": r["kpis"], "caveats": r["caveats"], "timings": r.get("timings"), "files": files,
            "recommendations": r["recommendations"], "has_brief": (ds.path / "brief.json").is_file()}


@router.get("/datasets/{ds_id}/profile")
def profile(ds_id: str, store: Store = Depends(get_store)):
    r = ds_or_404(store, ds_id).results
    return {"profile": r["profile"], "cleaning_log": r["cleaning_log"], "caveats": r["caveats"], "correlations": r.get("correlations")}


def _jsonable(v):
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    if isinstance(v, (pd.Timestamp,)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


@router.get("/datasets/{ds_id}/rows", response_model=RowsResponse)
def rows(ds_id: str, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=500), sort: str | None = None,
         desc: bool = False, q: str | None = None, filter_col: str | None = None, filter_val: str | None = None,
         store: Store = Depends(get_store)):
    ds = ds_or_404(store, ds_id)
    df = ds.df
    roles = ds.results["meta"]["roles"]
    cols = [c for c in df.columns if not c.startswith("_") or c in ("_outlier_any", "_segment")]
    if filter_col and filter_val is not None:
        if filter_col not in df:
            raise HTTPException(422, f"unknown column {filter_col}")
        df = df[df[filter_col].astype(str) == filter_val]
    if q:
        text_cols = [c for c in cols if roles.get(c) in ("text", "geo", "category", "id")]
        mask = pd.Series(False, index=df.index)
        for c in text_cols:
            mask |= df[c].astype(str).str.contains(re.escape(q), case=False, na=False)
        df = df[mask]
    if sort:
        if sort not in df:
            raise HTTPException(422, f"unknown sort column {sort}")
        df = df.sort_values(sort, ascending=not desc, na_position="last")
    total = len(df)
    part = df.iloc[(page - 1) * page_size: page * page_size][cols]
    out = [{c: _jsonable(v) for c, v in rec.items()} for rec in part.to_dict("records")]
    return {"columns": [{"name": c, "role": roles.get(c, "flag" if c.startswith("_") else "?")} for c in cols], "rows": out,
            "total": total, "page": page, "page_size": page_size}


@router.get("/datasets/{ds_id}/files/{kind}")
def export(ds_id: str, kind: str, store: Store = Depends(get_store)):
    if kind not in EXPORTS:
        raise HTTPException(404, f"unknown export '{kind}'; one of {list(EXPORTS)}")
    try:
        d = store.dir(ds_id)
    except NotFound:
        raise HTTPException(404, f"dataset '{ds_id}' not found")
    fname, mime = EXPORTS[kind]
    p = d / fname
    if not p.resolve().is_relative_to(store.out_dir.resolve()) or not _available_export(d, fname):
        raise HTTPException(404, f"{fname} was not generated for this dataset (run with reports enabled)")
    return FileResponse(p, media_type=mime, filename=f"{ds_id}_{p.name}")


@router.post("/datasets/{ds_id}/export", status_code=202, response_model=ExportStart)
def start_export(ds_id: str, body: ExportRequest, store: Store = Depends(get_store)):
    try:
        path = store.dir(ds_id)
    except NotFound:
        raise HTTPException(404, "Không tìm thấy dataset")
    if not path.resolve().is_relative_to(store.out_dir.resolve()):
        raise HTTPException(404, "Không tìm thấy dataset")
    return {"job_id": jobs.submit_export(path, body.lang, body.dashboard_pdf, get_settings().web_url)}


@router.get("/export/{job_id}", response_model=ExportJob)
def export_status(job_id: str):
    job = jobs.get_export(job_id)
    if job is None:
        raise HTTPException(404, "Không tìm thấy lượt xuất báo cáo")
    return job


@router.get("/datasets/{ds_id}/charts/{name}")
def chart_png(ds_id: str, name: str, store: Store = Depends(get_store)):
    if not re.fullmatch(r"[A-Za-z0-9_\-]+\.png", name):
        raise HTTPException(400, "bad chart name")
    try:
        p = store.dir(ds_id) / "charts" / name
    except NotFound:
        raise HTTPException(404, "dataset not found")
    if not p.exists():
        raise HTTPException(404, "chart not found")
    return FileResponse(p, media_type="image/png")
