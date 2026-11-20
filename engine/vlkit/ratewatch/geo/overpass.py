"""Overpass collector: ONE query for amenity=bank in Vietnam, cached to the bronze lake.

Usage policy (operations.osmfoundation.org/policies/overpass/): a single query with a
server-side timeout, an identifiable User-Agent, and the response cached on disk so
re-runs never hit the endpoint again.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

from vlkit.ratewatch.ingest.bronze import BronzeStore
from vlkit.ratewatch.ingest.runner import make_run_id

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NAME = "overpass_vn_bank.osm.json"
LICENCE = "ODbL (© OpenStreetMap contributors)"
UA = "VietLeapInsightKit/1.0 (ratewatch geo; one Overpass read per run; contact: vietleap2026 participant)"
QUERY = """[out:json][timeout:120];
area["ISO3166-1"="VN"][admin_level=2]->.vn;
(
  nwr["amenity"="bank"](area.vn);
);
out center tags;
"""


def latest_overpass(root: str | Path) -> Path | None:
    """Newest cached Overpass response under <root>/bronze/osm/<run_id>/, if any."""
    source_root = Path(root) / "bronze" / "osm"
    if not source_root.is_dir():
        return None
    for folder in sorted((p for p in source_root.iterdir() if p.is_dir()), reverse=True):
        path = folder / NAME
        if path.is_file():
            return path
    return None


def _default_fetcher(query: str, timeout: float) -> bytes:
    response = requests.post(OVERPASS_URL, data={"data": query},
                             headers={"User-Agent": UA}, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"Overpass answered HTTP {response.status_code}")
    return response.content


def collect_overpass(root: str | Path, run_id: str | None = None, timeout: float = 180.0,
                     fetcher=None) -> Path:
    """Cached bronze path of the Overpass response; fetches only when no cache exists."""
    cached = latest_overpass(root)
    if cached is not None:
        return cached
    store = BronzeStore(Path(root) / "bronze", run_id or make_run_id())
    fetch = fetcher or _default_fetcher
    content = fetch(query=QUERY, timeout=timeout)
    store.save("osm", NAME, content, url=OVERPASS_URL, status=200,
               robots_allowed=True, licence=LICENCE, method="overpass")
    return store.folder("osm") / NAME


def fetched_at_of(osm_json: str | Path) -> str:
    meta_path = Path(osm_json).with_name(NAME + ".meta.json")
    if meta_path.is_file():
        return str(json.loads(meta_path.read_text(encoding="utf-8")).get("fetched_at", ""))
    return ""
