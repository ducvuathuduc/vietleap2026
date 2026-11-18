"""Optional Reducto document-parsing connector (PDF / scan -> structured JSON -> Bronze).

Official Reducto API specification (verified against docs.reducto.ai):
  - Upload local file: POST https://platform.reducto.ai/upload
      Headers: Authorization: Bearer <REDUCTO_API_KEY>
      Body:    multipart/form-data with field ``file``
      Returns: {"file_id": "reducto://..."}
  - Parse document:    POST https://platform.reducto.ai/parse
      Headers: Authorization: Bearer <REDUCTO_API_KEY>, Content-Type: application/json
      Body:    {"input": "<public_url_or_reducto_file_id>"}
      Returns: {"job_id": "...", "result": {"chunks": [...]}}

API key handling:
  Reads ONLY from environment variable ``REDUCTO_API_KEY``. Never hardcode or log secrets.
  When ``REDUCTO_API_KEY`` is absent (and ``mock=False``), logs a skip message and exits cleanly
  so offline setups, ``make setup``, ``make demo``, and tests never fail.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Asia/Saigon")
REDUCTO_UPLOAD_URL = "https://platform.reducto.ai/upload"
REDUCTO_PARSE_URL = "https://platform.reducto.ai/parse"
REDUCTO_ENV_VAR = "REDUCTO_API_KEY"
DEFAULT_TIMEOUT = 120.0


@dataclass
class ReductoOutcome:
    status: str  # "ok" | "mock" | "skipped"
    source: str
    job_id: str | None
    records: list[dict[str, Any]]
    raw: dict[str, Any] | None = None
    output_json: str | None = None
    bronze_table: str | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _slug(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return s[:40] or "document"


def mock_parse_response(source: str) -> dict[str, Any]:
    """Deterministic Reducto-shaped JSON payload for offline dry-run verification (--mock)."""
    name = Path(source).name if not str(source).startswith(("http://", "https://")) else source
    return {
        "job_id": f"mock-reducto-{_slug(name)}",
        "duration": 0.01,
        "pdf_info": {"total_pages": 1, "source": str(name)},
        "result": {
            "type": "full",
            "chunks": [
                {
                    "content": f"# Tài liệu mẫu (Reducto --mock): {name}\nBáo cáo phân bổ ngân sách dự phòng cấp tỉnh.",
                    "embed": f"Báo cáo mẫu từ {name}",
                    "blocks": [
                        {
                            "type": "Title",
                            "content": f"Báo cáo tài chính công ({name})",
                            "bbox": {"left": 0.1, "top": 0.08, "width": 0.8, "height": 0.05, "page": 1},
                        },
                        {
                            "type": "Table",
                            "content": "| Tỉnh/Thành | Năm | Bổ sung có mục tiêu (tỷ đồng) |\n|---|---|---|\n| Hà Nội | 2025 | 1250.5 |\n| Đà Nẵng | 2025 | 410.2 |\n| Khánh Hòa | 2025 | 385.0 |",
                            "bbox": {"left": 0.1, "top": 0.2, "width": 0.8, "height": 0.3, "page": 1},
                        },
                    ],
                }
            ],
        },
    }


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def reducto_to_records(payload: dict[str, Any], source: str) -> list[dict[str, Any]]:
    """Flatten a Reducto /parse response into Bronze-ready tabular records."""
    job_id = str(payload.get("job_id") or "")
    result = payload.get("result") or {}
    chunks = result.get("chunks") or []
    records: list[dict[str, Any]] = []
    for c_idx, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            continue
        blocks = chunk.get("blocks") or []
        if blocks:
            for b_idx, block in enumerate(blocks):
                if not isinstance(block, dict):
                    continue
                bbox = block.get("bbox") or {}
                records.append({
                    "reducto_job_id": job_id,
                    "source_file": str(source),
                    "chunk_index": c_idx,
                    "block_index": b_idx,
                    "page": bbox.get("page") if isinstance(bbox, dict) else None,
                    "block_type": str(block.get("type") or "Text"),
                    "content": _strip_html(str(block.get("content") or "")),
                })
        else:
            records.append({
                "reducto_job_id": job_id,
                "source_file": str(source),
                "chunk_index": c_idx,
                "block_index": 0,
                "page": None,
                "block_type": "Chunk",
                "content": _strip_html(str(chunk.get("content") or chunk.get("embed") or "")),
            })
    if not records and payload:
        records.append({
            "reducto_job_id": job_id,
            "source_file": str(source),
            "chunk_index": 0,
            "block_index": 0,
            "page": None,
            "block_type": "Document",
            "content": json.dumps(result or payload, ensure_ascii=False)[:4000],
        })
    return records


def _is_url(value: str) -> bool:
    u = urlparse(value.strip())
    return u.scheme in ("http", "https") and bool(u.netloc)


def parse_document(
    source: str | Path,
    *,
    mock: bool = False,
    out_json: str | Path | None = None,
    bronze: bool = False,
    dataset: str | None = None,
    mode: str = "replace",
    client=None,
    net_guard: bool = False,
) -> ReductoOutcome:
    """Parse a PDF/image/document via Reducto API into structured JSON and optional DuckDB Bronze.

    Reads ``REDUCTO_API_KEY`` strictly from ``os.environ``. When unset and ``mock=False``,
    returns ``status="skipped"`` cleanly without raising.
    """
    src_str = str(source).strip()
    if not src_str:
        raise ValueError("Reducto source path or URL must not be blank")

    if mock:
        raw = mock_parse_response(src_str)
        status = "mock"
        message = f"[reducto] mock parse complete for {src_str}"
    else:
        api_key = os.environ.get(REDUCTO_ENV_VAR, "").strip()
        if not api_key:
            msg = f"[reducto] skipped: {REDUCTO_ENV_VAR} is not set (set {REDUCTO_ENV_VAR} or pass --mock for dry-run)"
            logger.info(msg)
            return ReductoOutcome(
                status="skipped",
                source=src_str,
                job_id=None,
                records=[],
                raw=None,
                output_json=None,
                bronze_table=None,
                message=msg,
            )

        import httpx

        if net_guard and _is_url(src_str):
            from .netguard import check_url
            check_url(src_str)

        headers = {"Authorization": f"Bearer {api_key}"}
        own_client = client is None
        http = client or httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=False)
        try:
            if _is_url(src_str):
                parse_input = src_str
            else:
                path = Path(src_str)
                if not path.is_file():
                    raise FileNotFoundError(f"Reducto input file not found: {path}")
                with path.open("rb") as fh:
                    up = http.post(
                        REDUCTO_UPLOAD_URL,
                        headers=headers,
                        files={"file": (path.name, fh, "application/octet-stream")},
                    )
                up.raise_for_status()
                up_data = up.json()
                parse_input = up_data.get("file_id") or up_data.get("presigned_url")
                if not parse_input:
                    raise RuntimeError(f"Reducto /upload did not return file_id: {up_data!r}")

            resp = http.post(
                REDUCTO_PARSE_URL,
                headers={**headers, "Content-Type": "application/json"},
                json={"input": parse_input},
            )
            resp.raise_for_status()
            raw = resp.json()
        finally:
            if own_client:
                http.close()
        status = "ok"
        message = f"[reducto] parsed {src_str} (job_id={raw.get('job_id')})"

    records = reducto_to_records(raw, src_str)
    doc_slug = _slug(dataset or Path(src_str).stem)

    written_json: str | None = None
    if out_json is not None or bronze:
        if out_json is not None:
            target_path = Path(out_json)
        else:
            kit_root = Path(__file__).resolve().parents[3]
            target_path = kit_root / "data" / "lake" / "bronze" / f"reducto_{doc_slug}.json"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "status": status,
            "source": src_str,
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "endpoint": REDUCTO_PARSE_URL,
            "job_id": raw.get("job_id"),
            "records": records,
            "raw": raw,
        }
        target_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
        written_json = str(target_path)

    bronze_table: str | None = None
    if bronze and records:
        import pandas as pd
        from .warehouse import Warehouse

        ds_name = _slug(dataset or Path(src_str).stem)
        tname = f"{ds_name}__reducto_{_slug(Path(src_str).stem)}"
        wh = Warehouse()
        try:
            ls = wh.write_bronze(
                ds_name,
                tname,
                pd.DataFrame(records),
                {
                    "source": f"reducto:{Path(src_str).name}",
                    "kind": "reducto",
                    "uri": src_str,
                    "endpoint": REDUCTO_PARSE_URL,
                    "job_id": raw.get("job_id"),
                },
                mode=mode,
            )
            bronze_table = ls["table"]
        finally:
            wh.close()

    return ReductoOutcome(
        status=status,
        source=src_str,
        job_id=raw.get("job_id"),
        records=records,
        raw=raw,
        output_json=written_json,
        bronze_table=bronze_table,
        message=message,
    )
