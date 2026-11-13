"""In-process job runner for dataset analysis (uploads take 10–120 s)."""
from __future__ import annotations

import threading
import time
import traceback
import uuid
from pathlib import Path

from vlkit import pipeline

from .settings import get_settings

_jobs: dict[str, dict] = {}
_lock = threading.Lock()
_sem = threading.Semaphore(1)  # one analysis at a time: predictable memory on laptops


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
