"""Land source responses, metadata and incremental non-rate silver."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import monotonic

from ..warehouse import TZ
from .macro import parse_cpi, parse_fx, parse_interbank, parse_omo

KEYS = {
    "interbank": ("date", "tenor"),
    "omo": ("date", "operation", "tenor_days", "rate_pct", "auction"),
    "central_fx": ("date",),
    "fiin_quarter": ("bank", "quarter"),
    "fiin_market": ("bank", "date"),
    "policy": ("parameter", "metric"),
}


class SourceFailure(RuntimeError):
    """A provider error with its source and a message safe for the run log."""

    def __init__(self, source, detail):
        super().__init__(detail)
        self.source = source


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")


def atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, prefix=".", delete=False) as stream:
        scratch = Path(stream.name)
    try:
        scratch.write_bytes(content)
        scratch.replace(path)
    finally:
        scratch.unlink(missing_ok=True)


def ingest_sources(lake, run_id, providers):
    started = monotonic()
    lake = Path(lake)
    log = {"run_id": run_id, "records": {}, "new_records": {}, "errors": {}, "watermarks": {},
           "observed_at": {}, "usd": 0}
    for provider in providers:
        name = provider.__name__
        try:
            for series, url, raw, extract in provider():
                name = series
                at = datetime.now(TZ).isoformat(timespec="seconds")
                digest = sha256(raw).hexdigest()
                obj = lake / "bronze" / series / run_id / sha256(url.encode()).hexdigest()[:20]
                sdk = series.startswith("fiin_")
                licence = "FiinQuant (dữ liệu tổng hợp theo giấy phép)" if sdk else "Nguồn công khai"
                method = "SDK FiinQuant" if sdk else "HTTP"
                publisher = "Nguồn: FiinQuant (FiinGroup)" if sdk else ("Cục Thống kê" if series in {"cpi", "cpi_index"} else "NHNN")
                atomic(obj.with_suffix(".bin"), raw)
                atomic(obj.with_suffix(".meta.json"), encode(dict(
                    url=url, fetched_at=at, status=200, sha256=digest, run_id=run_id,
                    robots_allowed=None if sdk else True, licence=licence, method=method, usd_cost=0,
                )))
                rows = extract(raw) if callable(extract) else extract
                if series == "cpi_index" or series.startswith("fiin_raw_"):
                    continue
                if not rows:
                    raise ValueError("Không tìm thấy quan sát trong nguồn")
                path = lake / "silver" / "nonrate" / f"{series}.json"
                old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
                keys = KEYS.get(series, ("month",))

                def row_key(row):
                    return tuple(row[column] for column in keys)

                merged = {row_key(row): row for row in old}
                new = 0
                for row in rows:
                    keyed = row_key(row)
                    previous = merged.get(keyed)
                    if previous is not None and all(previous.get(field) == value for field, value in row.items()):
                        continue
                    new += previous is None
                    merged[keyed] = {
                        "source_id": url, "source_url": url, "publisher": publisher, "licence": licence,
                        "method": method, **row, "observed_at": at, "raw_sha256": digest, "run_id": run_id,
                    }
                atomic(path, encode([merged[key] for key in sorted(merged)]))
                log["records"][series] = len(merged)
                log["observed_at"][series] = at
                log["new_records"][series] = log["new_records"].get(series, 0) + new
                period = next((period for period in ("date", "month", "quarter") if period in keys), None)
                if period:
                    log["watermarks"][series] = max(row[period] for row in merged.values())
        except SourceFailure as exc:
            log["errors"][exc.source] = str(exc)
        except Exception as exc:
            # SDK exceptions can contain request data.
            log["errors"][name] = type(exc).__name__ if name.startswith("fiin") else f"{type(exc).__name__}: {exc}"
    log["seconds"] = round(monotonic() - started, 3)
    atomic(lake / "run_log" / f"{run_id}-nonrate.json", encode(log))
    return log
