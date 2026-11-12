"""Dataset store: every analysed dataset lives in <out_dir>/<id>/ (results.json, clean.parquet, whatif.json, reports)."""
from __future__ import annotations

import json
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .settings import get_settings

_ID = re.compile(r"^[a-z0-9_\-]{1,80}$")


class NotFound(Exception):
    pass


@dataclass
class Dataset:
    id: str
    path: Path
    results: dict
    df: pd.DataFrame
    whatif: dict | None
    mtime: float


class Store:
    def __init__(self, out_dir: Path | None = None, capacity: int = 4):
        self.out_dir = Path(out_dir or get_settings().out_dir)
        self._cache: OrderedDict[str, Dataset] = OrderedDict()
        self._lock = threading.Lock()
        self.capacity = capacity

    def list(self) -> list[dict]:
        items = []
        for p in sorted(self.out_dir.glob("*/results.json"), key=lambda x: -x.stat().st_mtime):
            try:
                meta = json.loads(p.read_text(encoding="utf-8"))["meta"]
            except Exception:
                continue
            items.append({"id": p.parent.name, "name": meta.get("name", p.parent.name), "domain": meta["domain"], "rows": meta["rows"],
                          "target": meta["target"], "source_file": meta["source_file"], "created": meta.get("created")})
        return items

    def dir(self, ds_id: str) -> Path:
        if not _ID.match(ds_id):
            raise NotFound(ds_id)
        d = self.out_dir / ds_id
        if not (d / "results.json").exists():
            raise NotFound(ds_id)
        return d

    def get(self, ds_id: str) -> Dataset:
        d = self.dir(ds_id)
        mtime = (d / "results.json").stat().st_mtime
        with self._lock:
            hit = self._cache.get(ds_id)
            if hit and hit.mtime == mtime:
                self._cache.move_to_end(ds_id)
                return hit
        results = json.loads((d / "results.json").read_text(encoding="utf-8"))
        df = pd.read_parquet(d / "clean.parquet")
        wi = json.loads((d / "whatif.json").read_text(encoding="utf-8")) if (d / "whatif.json").exists() else None
        ds = Dataset(ds_id, d, results, df, wi, mtime)
        with self._lock:
            self._cache[ds_id] = ds
            while len(self._cache) > self.capacity:
                self._cache.popitem(last=False)
        return ds


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store
