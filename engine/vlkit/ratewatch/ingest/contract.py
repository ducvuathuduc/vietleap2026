"""Silver contract for RateWatch (CONTRACT A in ~/.kiro/herdr-tasks/vietleap-4/CONTRACT.md).

One row per reader observation of a posted term-deposit rate. Every reader returns raw dicts, they all go
through :func:`normalise_row` (unit normalisation + validation) and :func:`silver_frame` (typed frame), so a
reader can never smuggle a text rate, a percent sign or a wrong channel into the lake.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from ...vn import ascii_key

TZ = ZoneInfo("Asia/Saigon")
SILVER_COLUMNS = ["run_id", "bank_code", "term_months", "channel", "tier", "rate_pct", "interest_basis",
                  "sheet_date", "observed_at", "reader", "source_url", "raw_sha256"]
READERS = ("aggregator", "bank_pdf", "bank_html", "tinyfish")
CHANNELS = ("counter", "online")
MAX_RATE_PCT = 15.0
MAX_TERM_MONTHS = 60
DEMAND_KEYS = {"kkh", "khong ky han", "khong ki han", "khong co ky han", "tien gui khong ky han"}

_RATE_RE = re.compile(r"^\d{1,2}(?:[.,]\d{1,2})?$")
_TERM_RE = re.compile(r"^(?:tu\s+)?(\d{1,2})\b[^\n]{0,40}\bthang\b")
_DATE_RE = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](20\d\d)")
_DATE_LONG_RE = re.compile(r"ngay\s+(\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+(20\d\d)")


def parse_rate(value) -> float | None:
    """``4,75%`` / ``4.75 %`` -> 4.75; ``-`` / ``0%`` / ``20`` -> None (not a posted deposit rate)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace("%", "").replace(" ", "").replace("\u00a0", "")
        if not _RATE_RE.match(text):
            return None
        number = float(text.replace(",", "."))
    return number if 0 < number <= MAX_RATE_PCT else None


def parse_term(value) -> int | None:
    """``12 tháng`` / ``Từ 1 đến dưới 2 tháng`` -> months; ``Không kỳ hạn`` -> 0; weeks/tiers -> None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        term = int(value)
        return term if 0 <= term <= MAX_TERM_MONTHS else None
    key = ascii_key(value)
    if not key:
        return None
    if key in DEMAND_KEYS:
        return 0
    if "tuan" in key.split():          # weekly products are not term deposits in months
        return None
    match = _TERM_RE.match(key)
    if not match:
        return None
    term = int(match.group(1))
    return term if 0 <= term <= MAX_TERM_MONTHS else None


def parse_channel(value) -> str:
    key = ascii_key(value)
    if "online" in key or "truc tuyen" in key or "internet" in key:
        return "online"
    if "quay" in key or "counter" in key or "tai quay" in key:
        return "counter"
    raise ValueError(f"không nhận ra kênh giao dịch: {value!r}")


def parse_vi_date(text) -> date | None:
    """The effective date printed on a sheet (``ngày 20.10.2026``, ``từ ngày 31 tháng 10 năm 2026``)."""
    if text is None:
        return None
    if isinstance(text, datetime):
        return text.date()
    if isinstance(text, date):
        return text
    raw = str(text)
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", raw.strip())
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    for match in _DATE_RE.finditer(raw):
        day, month, year = (int(part) for part in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            continue
    for match in _DATE_LONG_RE.finditer(ascii_key(raw)):      # "ngày 31 tháng 10 năm 2026"
        day, month, year = (int(part) for part in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return None


def normalise_row(row: dict) -> dict:
    """Cast, validate and normalise one reader row. Raises ``ValueError`` on an impossible observation."""
    missing = [key for key in ("run_id", "bank_code", "term_months", "channel", "rate_pct", "observed_at",
                               "reader", "source_url", "raw_sha256") if row.get(key) in (None, "")]
    if missing:
        raise ValueError(f"silver row thiếu trường: {', '.join(missing)}")
    reader = str(row["reader"]).strip()
    if reader not in READERS:
        raise ValueError(f"reader không hợp lệ: {reader!r}")
    term = parse_term(row["term_months"])
    if term is None:
        raise ValueError(f"kỳ hạn không hợp lệ: {row['term_months']!r}")
    rate = parse_rate(row["rate_pct"])
    if rate is None:
        raise ValueError(f"lãi suất không hợp lệ: {row['rate_pct']!r}")
    observed = row["observed_at"]
    if not isinstance(observed, str):
        observed = observed.isoformat()
    sheet = row.get("sheet_date")
    if isinstance(sheet, str):
        sheet = parse_vi_date(sheet)
    elif isinstance(sheet, datetime):
        sheet = sheet.date()
    return {
        "run_id": str(row["run_id"]),
        "bank_code": str(row["bank_code"]).strip().upper(),
        "term_months": term,
        "channel": parse_channel(row["channel"]),
        "tier": str(row.get("tier") or ""),
        "rate_pct": round(rate, 4),
        "interest_basis": str(row.get("interest_basis") or "at_maturity"),
        "sheet_date": sheet,
        "observed_at": observed,
        "reader": reader,
        "source_url": str(row["source_url"]),
        "raw_sha256": str(row["raw_sha256"]),
    }


def dedupe_rows(rows) -> list[dict]:
    """Upsert key of CONTRACT A: (run_id, bank_code, term_months, channel, tier, reader) — last read wins."""
    ordered: dict[tuple, dict] = {}
    for row in rows:
        key = (row["run_id"], row["bank_code"], row["term_months"], row["channel"], row["tier"], row["reader"])
        ordered[key] = row
    return list(ordered.values())


def silver_frame(rows) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows), columns=SILVER_COLUMNS)
    if frame.empty:
        frame = frame.astype({"term_months": "int64", "rate_pct": "float64"})
        frame["sheet_date"] = pd.to_datetime(frame["sheet_date"])
        frame["observed_at"] = pd.to_datetime(frame["observed_at"], utc=True).dt.tz_convert(TZ)
        return frame[SILVER_COLUMNS]
    frame["term_months"] = frame["term_months"].astype("int64")
    frame["rate_pct"] = frame["rate_pct"].astype("float64")
    frame["sheet_date"] = pd.to_datetime(frame["sheet_date"])
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], utc=True).dt.tz_convert(TZ)
    return frame[SILVER_COLUMNS].reset_index(drop=True)


def rows_from_frame(frame: pd.DataFrame) -> list[dict]:
    """Back to plain dicts (reused rows of an unchanged sheet keep their original reader/url/hash)."""
    rows = []
    for record in frame.to_dict("records"):
        sheet = record.get("sheet_date")
        observed = record.get("observed_at")
        rows.append({
            **record,
            "sheet_date": None if sheet is None or pd.isna(sheet) else pd.Timestamp(sheet).date(),
            "observed_at": pd.Timestamp(observed).isoformat(),
        })
    return rows


def write_silver(frame: pd.DataFrame, out: str | Path, run_id: str) -> dict[str, Path]:
    """Write both formats under ``<out>/silver/<run_id>/`` (re-running a run_id overwrites them)."""
    folder = Path(out) / "silver" / run_id
    folder.mkdir(parents=True, exist_ok=True)
    parquet = folder / "rates.parquet"
    csv_path = folder / "rates.csv"
    frame.to_parquet(parquet, index=False)
    export = frame.copy()
    export["sheet_date"] = frame.sheet_date.dt.strftime("%Y-%m-%d")
    export["observed_at"] = frame.observed_at.map(lambda ts: ts.isoformat())
    export.to_csv(csv_path, index=False, encoding="utf-8")
    return {"parquet": parquet, "csv": csv_path}
