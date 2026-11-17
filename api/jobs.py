"""In-process job runner for dataset analysis (uploads take 10–120 s)."""
from __future__ import annotations

import threading
import time
import traceback
import uuid
import json
import os
import subprocess
import sys
from pathlib import Path

from vlkit import pipeline
from vlkit.de.sources import now_iso

from .settings import get_settings

_jobs: dict[str, dict] = {}
_lock = threading.Lock()
_sem = threading.Semaphore(1)  # one analysis at a time: predictable memory on laptops
_exports: dict[str, dict] = {}
_active_exports: dict[str, str] = {}


def submit(path: Path, name: str, **opts) -> dict:
    job = {"id": uuid.uuid4().hex[:12], "status": "queued", "dataset_id": None, "error": None, "started": time.time(), "finished": None}
    with _lock:
        _jobs[job["id"]] = job

    def work():
        with _sem:
            job["status"] = "running"
            try:
                s = get_settings()
                job["status"] = "pipeline"   # Ingestion → bronze → silver → gold (OBT/Star/Snowflake/Data Vault)
                try:
                    from vlkit.de.flow import run_file
                    from .routes.pipeline import _wh_lock
                    with _wh_lock:
                        run_file(path, dataset=name, out_root=s.out_dir)
                except Exception:  # the insight engine still runs if modelling fails on an odd file
                    traceback.print_exc()
                job["status"] = "running"
                res = pipeline.run(path, out_root=s.out_dir, name=name, reports=s.reports_on_upload, **opts)
                job["dataset_id"] = res["meta"]["name"]
                job["status"] = "done"
            except Exception as e:
                job["status"], job["error"] = "error", f"{type(e).__name__}: {e}"
                traceback.print_exc()
            finally:
                job["finished"] = time.time()

    threading.Thread(target=work, daemon=True).start()
    return job


def get(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def _run_export_process(out: Path, lang: str, dashboard: bool, web_url: str) -> dict:
    from vlkit.export import partial_export

    engine = Path(__file__).resolve().parent.parent / "engine"
    env = {**os.environ, "PYTHONPATH": str(engine), "PYTHONUTF8": "1"}
    command = [sys.executable, "-m", "vlkit.export", str(out), lang, "yes" if dashboard else "no", web_url]
    try:
        process = subprocess.run(command, env=env, capture_output=True, encoding="utf-8", check=True, timeout=180)
    except subprocess.TimeoutExpired:
        return partial_export(out, lang)
    except subprocess.CalledProcessError:
        raise RuntimeError("Không dựng được báo cáo từ dữ liệu đã lưu.") from None
    return json.loads(process.stdout.splitlines()[-1])


def submit_export(out: Path, lang: str, dashboard: bool, web_url: str) -> str:
    with _lock:
        key = str(out.resolve())
        if key in _active_exports:
            return _active_exports[key]
        job_id = uuid.uuid4().hex[:12]
        job = {"id": job_id, "dataset": out.name, "status": "queued", "progress": 0, "step": None,
               "warnings": [], "error": None, "files": {}, "started_at": now_iso(), "finished_at": None}
        _exports[job_id] = job
        _active_exports[key] = job_id

    def work():
        from .routes.pipeline import _wh_lock

        try:
            with _sem, _wh_lock:
                with _lock:
                    job.update(status="running", progress=0.15, step="rebuild")
                result = _run_export_process(out, lang, dashboard, web_url)
            with _lock:
                job.update(result, status="done_with_warnings" if result["warnings"] else "done",
                           progress=1, step="bundle", finished_at=now_iso())
        except Exception:
            with _lock:
                job.update(status="error", error="Xuất báo cáo thất bại. Kiểm tra dữ liệu đã phân tích rồi thử lại.", finished_at=now_iso())
        finally:
            with _lock:
                del _active_exports[key]

    threading.Thread(target=work, daemon=True).start()
    return job_id


def get_export(job_id: str) -> dict | None:
    with _lock:
        job = _exports.get(job_id)
        return dict(job) if job else None
