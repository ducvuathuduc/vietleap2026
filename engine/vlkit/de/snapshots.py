"""Prepare input data for a strictly local replay."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pandas as pd

from .connectors import CACHE, ingest
from .sources import IngestResult, Recipe, Source
from .warehouse import KIT

MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024


def file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _manifest(source: Source) -> Path:
    descriptor = source.to_dict()
    if source.kind == "file" and source.options.get("origin"):
        descriptor["uri"] = source.options["origin"]
    elif source.kind in ("file", "cv"):
        path = Path(source.uri).resolve()
        if path.is_relative_to(KIT):
            descriptor["uri"] = path.relative_to(KIT).as_posix()
    key = hashlib.sha256(json.dumps(descriptor, sort_keys=True, default=str).encode()).hexdigest()
    return CACHE / "snapshots" / key / "manifest.json"


def _fetch_file(source: Source) -> None:
    origin = source.options["origin"]
    path = Path(source.uri).resolve()
    if not origin.startswith("https://") or not path.is_relative_to(CACHE.resolve()):
        raise ValueError("snapshot downloads require HTTPS and a destination under data/cache")
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.part")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.stream("GET", origin, follow_redirects=True, timeout=30) as response:
            response.raise_for_status()
            total = 0
            with tmp.open("wb") as handle:
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError(f"snapshot exceeds {MAX_DOWNLOAD_BYTES} bytes")
                    handle.write(chunk)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def prepare_snapshot(recipe: Recipe) -> list[Path]:
    manifests = []
    for source in recipe.sources:
        try:
            if source.kind == "file" and source.options.get("origin") and not Path(source.uri).is_file():
                _fetch_file(source)
            result = ingest(source)
        except httpx.HTTPError as error:
            context = str(error.response.status_code) if isinstance(error, httpx.HTTPStatusError) else type(error).__name__
            raise RuntimeError(f"Không tải được nguồn '{source.name}' ({context})") from None
        if not any(not frame.empty for frame in result.frames.values()):
            raise ValueError(f"Nguồn {source.name} không có dữ liệu để lưu cache")
        manifest = _manifest(source)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        files = {}
        for name, frame in result.frames.items():
            tmp = manifest.with_name(f".{uuid4().hex}.parquet")
            try:
                frame.to_parquet(tmp, index=False)
                checksum = file_sha256(tmp)
                filename = f"{checksum}.parquet"
                tmp.replace(manifest.with_name(filename))
                files[name] = {"file": filename, "sha256": checksum}
            finally:
                tmp.unlink(missing_ok=True)
        tmp = manifest.with_name(f".{uuid4().hex}.json")
        try:
            payload = {"provenance": result.provenance, "tables": files}
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            tmp.replace(manifest)
        finally:
            tmp.unlink(missing_ok=True)
        manifests.append(manifest)
    return manifests


def has_snapshot(source: Source) -> bool:
    return _manifest(source).is_file()


def ingest_offline(source: Source) -> IngestResult:
    local = source.kind == "file" or (source.kind == "cv" and Path(source.uri).suffix.lower() == ".csv")
    manifest = _manifest(source)
    if local and Path(source.uri).is_file() and (not source.options.get("origin") or not manifest.is_file()):
        return ingest(source)
    if not manifest.is_file():
        raise FileNotFoundError(f"Thiếu dữ liệu offline cho '{source.name}'. Chạy de.py snapshot với recipe khi có mạng hoặc đặt tệp nguồn vào máy.")
    snapshot = json.loads(manifest.read_text(encoding="utf-8"))
    frames = {}
    for name, entry in snapshot["tables"].items():
        path = (manifest.parent / entry["file"]).resolve()
        if path.parent != manifest.parent.resolve() or not path.is_file() or file_sha256(path) != entry["sha256"]:
            raise ValueError(f"Cache của '{source.name}' thiếu tệp hoặc sai checksum. Chạy lại de.py snapshot.")
        frames[name] = pd.read_parquet(path)
    return IngestResult(source, frames, {**snapshot["provenance"], "offline_snapshot": True})
