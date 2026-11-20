"""Read and write per-dataset watermarks, and derive what a run still needs."""

import json
from pathlib import Path

from .files import atomic


def load(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save(path, watermarks):
    atomic(Path(path), json.dumps(watermarks, ensure_ascii=False, indent=2).encode("utf-8"))


def quarter_periods(first, latest, watermark):
    """Quarters from the watermark (inclusive, to catch revisions) through `latest`."""
    start = watermark or first
    start_year, start_quarter = int(start[:4]), int(start[-1])
    end_year, end_quarter = int(latest[:4]), int(latest[-1])
    return [
        f"{year}Q{quarter}"
        for year in range(start_year, end_year + 1)
        for quarter in range(1, 5)
        if start_year * 4 + start_quarter - 1 <= year * 4 + quarter - 1 <= end_year * 4 + end_quarter - 1
    ]


def year_periods(first, latest, watermark):
    return list(range(max(first, int(watermark) if watermark else first), latest + 1))


def day_start(first, watermark, overlap_days=10):
    """First calendar date to request: the watermark minus an overlap for late vendor fixes."""
    if not watermark:
        return first
    from datetime import date, timedelta

    return str(max(date.fromisoformat(first), date.fromisoformat(str(watermark)[:10]) - timedelta(days=overlap_days)))
