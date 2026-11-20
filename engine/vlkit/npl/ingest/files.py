"""Atomic local writes and timestamps for the NPL lake."""

from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def now():
    return datetime.now(TZ)


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


def write_parquet(path, frame):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_suffix(".parquet.tmp")
    frame.to_parquet(scratch, index=False)
    scratch.replace(path)
