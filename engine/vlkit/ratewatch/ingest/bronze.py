"""Bronze lake + meta JSON, and the read-only replay used by ``--offline`` and the tests (CONTRACT A).

Layout: ``<root>/<source>/<run_id>/<name>`` with ``<name>.meta.json`` next to it holding
``{url, fetched_at, status, sha256, run_id, robots_allowed, licence, method, usd_cost}``.
Re-running a run_id writes the same paths again, so a retried run never leaves two copies of one sheet.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .contract import TZ


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


@dataclass
class BronzeObject:
    source: str
    name: str
    path: Path
    meta: dict

    @property
    def content(self) -> bytes:
        return self.path.read_bytes()

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", "replace")


class BronzeStore:
    """Write path of the lake (one folder per source and run)."""

    def __init__(self, root: str | Path, run_id: str):
        self.root = Path(root)
        self.run_id = run_id

    def folder(self, source: str) -> Path:
        return self.root / source / self.run_id

    def save(self, source: str, name: str, data: bytes, *, url: str, status: int = 200,
             robots_allowed: bool = True, licence: str = "public page, reference use",
             method: str = "", usd_cost: float = 0.0) -> dict:
        folder = self.folder(source)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(data)
        meta = {
            "url": url, "fetched_at": now_iso(), "status": int(status), "sha256": sha256(data),
            "run_id": self.run_id, "robots_allowed": bool(robots_allowed), "licence": licence,
            "method": method or source, "usd_cost": round(float(usd_cost), 4),
        }
        (folder / f"{name}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
        return meta

    def load(self, source: str, name: str) -> BronzeObject | None:
        path = self.folder(source) / name
        meta_path = path.with_name(f"{name}.meta.json")
        if not path.is_file() or not meta_path.is_file():
            return None
        return BronzeObject(source, name, path, json.loads(meta_path.read_text(encoding="utf-8")))

    def previous_sha(self, source: str, name: str) -> str | None:
        """sha256 of the same object in the most recent *earlier* run, for the incremental skip."""
        source_root = self.root / source
        if not source_root.is_dir():
            return None
        for folder in sorted((p for p in source_root.iterdir() if p.is_dir()), reverse=True):
            if folder.name == self.run_id:
                continue
            meta_path = folder / f"{name}.meta.json"
            if meta_path.is_file():
                try:
                    return json.loads(meta_path.read_text(encoding="utf-8")).get("sha256")
                except json.JSONDecodeError:
                    return None
        return None


class BronzeReplay:
    """Read-only view of an existing bronze tree: the ``--offline`` path, no network, no spend."""

    def __init__(self, root: str | Path, source: str | None = None):
        self.root = Path(root)
        self.source = source

    def objects(self) -> list[BronzeObject]:
        out = []
        if not self.root.is_dir():
            return out
        folders = [self.root / self.source] if self.source else sorted(
            p for p in self.root.iterdir() if p.is_dir())
        for source_root in folders:
            if not source_root.is_dir():
                continue
            found: dict[str, BronzeObject] = {}
            for run_dir in sorted((p for p in source_root.iterdir() if p.is_dir()), reverse=True):
                for meta_path in sorted(run_dir.glob("*.meta.json")):
                    name = meta_path.name[: -len(".meta.json")]
                    content_path = run_dir / name
                    if name in found or not content_path.is_file():
                        continue
                    try:
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        continue
                    found[name] = BronzeObject(source_root.name, name, content_path, meta)
            for name in sorted(found):
                out.append(found[name])
        return out
