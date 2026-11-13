"""Source specification and provenance records.

A sources.yaml looks like:

    dataset: housing            # name of the analytical dataset (gold tables are named after it)
    sources:
      - name: listings
        kind: file              # file | api | sql | scrape | social | cv
        uri: data/raw/listings.xlsx
      - name: gdp_vn
        kind: api
        uri: https://api.worldbank.org/v2/country/VN/indicator/NY.GDP.PCAP.CD
        options: {params: {format: json, per_page: 100}, records_path: "1", paging: worldbank}
      - name: provinces
        kind: scrape
        uri: https://vi.wikipedia.org/wiki/Tỉnh_thành_Việt_Nam
        options: {table_index: 0}
    keys:                       # optional business keys used by Data Vault / conformed dims
      province: [tinh, province]
      year: [nam, year]
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

TZ = ZoneInfo("Asia/Saigon")
KINDS = ("file", "api", "sql", "scrape", "social", "cv")


@dataclass
class Source:
    name: str
    kind: str
    uri: str
    options: dict = field(default_factory=dict)
    license_note: str = ""

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"source '{self.name}': kind must be one of {KINDS}, got {self.kind!r}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IngestResult:
    source: Source
    frames: dict[str, pd.DataFrame]          # one source can yield several tables (Excel sheets, HTML tables)
    provenance: dict


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def df_fingerprint(df: pd.DataFrame) -> str:
    h = hashlib.sha256()
    h.update(",".join(map(str, df.columns)).encode())
    h.update(pd.util.hash_pandas_object(df.astype(str), index=False).values.tobytes())
    return h.hexdigest()[:16]


def make_provenance(src: Source, frames: dict[str, pd.DataFrame], **extra) -> dict:
    return {
        "source": src.name, "kind": src.kind, "uri": src.uri, "options": src.options,
        "fetched_at": now_iso(), "license_note": src.license_note,
        "tables": {k: {"rows": int(len(v)), "cols": int(v.shape[1]), "fingerprint": df_fingerprint(v)} for k, v in frames.items()},
        **extra,
    }


def load_sources(path: str | Path) -> tuple[str, list[Source], dict]:
    """Returns (dataset_name, sources, keys)."""
    path = Path(path)
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    base = path.parent
    out = []
    for s in spec.get("sources", []):
        uri = s["uri"]
        if s["kind"] in ("file", "cv") and not Path(uri).is_absolute() and (base / uri).exists():
            uri = str((base / uri).resolve())   # paths in sources.yaml are relative to the yaml file
        out.append(Source(name=s["name"], kind=s["kind"], uri=uri, options=s.get("options", {}) or {},
                          license_note=s.get("license", "")))
    return spec.get("dataset", path.stem), out, spec.get("keys", {}) or {}
