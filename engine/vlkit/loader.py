"""Load any tabular file (CSV/TSV/TXT/XLSX/XLS/JSON/Parquet), clean it and guess column roles.

Nothing is deleted silently: every transformation is appended to a cleaning log.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import vn

ENCODINGS = ["utf-8-sig", "utf-8", "utf-16", "cp1258", "cp1252", "latin-1"]

GEO_HINTS = ["tinh", "province", "thanh pho", "city", "quan", "huyen", "district", "phuong", "xa", "ward",
             "region", "vung", "country", "quoc gia", "khu vuc", "dia ban", "location", "area name", "state"]
TIME_HINTS = ["ngay", "date", "time", "thoi gian", "nam", "year", "thang", "month", "quy", "quarter", "ky",
              "period", "posted", "published"]
ID_HINTS = ["id", "ma", "code", "ticker", "symbol", "stt", "index", "unnamed", "url", "link", "iso"]


@dataclass
class CleanResult:
    df: pd.DataFrame
    roles: dict[str, str]
    log: list[str] = field(default_factory=list)
    source: dict = field(default_factory=dict)
    numeric_reports: dict = field(default_factory=dict)
    renamed: dict = field(default_factory=dict)


# ----------------------------------------------------------------------------- reading

def _read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for enc in ENCODINGS:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace"), "latin-1(replace)"


def _sniff_delim(text: str) -> str:
    lines = text.splitlines()
    sample = "\n".join(lines[5:60] if len(lines) > 20 else lines[:50])  # skip possible title rows
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        counts = {d: sample.count(d) for d in [",", ";", "\t", "|"]}
        return max(counts, key=counts.get)


def _find_header_row(df_raw: pd.DataFrame, max_scan: int = 15) -> int:
    """Title rows above the real header are common in VN government Excel files."""
    best, best_score = 0, -1
    ncol = df_raw.shape[1]
    for i in range(min(max_scan, len(df_raw))):
        row = df_raw.iloc[i]
        filled = row.notna().sum()
        strs = sum(isinstance(v, str) and not re.fullmatch(r"[\d.,\s%-]+", v) for v in row)
        score = filled + strs
        if filled >= max(2, 0.5 * ncol) and score > best_score:
            best, best_score = i, score
            if filled == ncol:
                break
    return best


def read_any(path: str | Path, sheet: str | None = None, log: list[str] | None = None) -> pd.DataFrame:
    path = Path(path)
    log = log if log is not None else []
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        xl = pd.ExcelFile(path)
        sheets = [sheet] if sheet else xl.sheet_names
        frames = []
        for sh in sheets:
            raw = pd.read_excel(xl, sheet_name=sh, header=None)
            raw = raw.dropna(how="all").dropna(axis=1, how="all")
            if raw.empty or raw.shape[0] < 2:
                log.append(f"sheet '{sh}': empty, skipped")
                continue
            h = _find_header_row(raw)
            df = raw.iloc[h + 1:].copy()
            df.columns = [str(c) if pd.notna(c) else f"col_{j}" for j, c in enumerate(raw.iloc[h])]
            if h:
                log.append(f"sheet '{sh}': skipped {h} title row(s) above the header")
            frames.append((sh, df.reset_index(drop=True)))
        if not frames:
            raise ValueError("No non-empty sheet found")
        if len(frames) == 1:
            log.append(f"read sheet '{frames[0][0]}' ({len(frames[0][1])} rows)")
            return frames[0][1]
        cols0 = set(frames[0][1].columns)
        same = [f for f in frames if len(set(f[1].columns) & cols0) >= 0.8 * len(cols0)]
        if len(same) == len(frames):
            out = pd.concat([f[1].assign(_sheet=f[0]) for f in frames], ignore_index=True)
            log.append(f"stacked {len(frames)} sheets with the same columns into one table; sheet name kept in '_sheet'")
            return out
        biggest = max(frames, key=lambda f: f[1].size)
        log.append(f"{len(frames)} sheets with different layouts; using the largest '{biggest[0]}'. "
                   f"Others: {[f[0] for f in frames if f is not biggest]} (pass --sheet to choose)")
        return biggest[1]
    if ext == ".parquet":
        return pd.read_parquet(path)
    if ext == ".json":
        try:
            return pd.read_json(path)
        except ValueError:
            return pd.read_json(path, lines=True)
    text, enc = _read_text(path)
    delim = _sniff_delim(text)
    log.append(f"read text file: encoding={enc}, delimiter={delim!r}")
    # parse with the csv module so ragged title rows above the header do not break column detection
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    width = max((len(r) for r in rows[:2000]), default=0)
    rows = [r + [""] * (width - len(r)) if len(r) < width else r[:width] for r in rows if any(x.strip() for x in r)]
    raw = pd.DataFrame(rows, dtype=object).replace({"": np.nan})
    h = _find_header_row(raw)
    if h:
        log.append(f"skipped {h} title row(s) above the header")
    df = raw.iloc[h + 1:].copy()
    df.columns = [str(c) if pd.notna(c) else f"col_{j}" for j, c in enumerate(raw.iloc[h])]
    return df.reset_index(drop=True)


def maybe_transpose(df: pd.DataFrame, force: bool | None, log: list[str]) -> pd.DataFrame:
    """Financial statements often come as items (rows) x entities (columns)."""
    first = df.columns[0]
    looks_wide = df.shape[1] > 3 * df.shape[0] and df[first].astype(str).str.len().mean() > 8
    if force or (force is None and looks_wide):
        t = df.set_index(first).T.reset_index().rename(columns={"index": "entity"})
        t.columns = [str(c) for c in t.columns]
        t = t.loc[:, ~pd.Index(t.columns).duplicated()]
        log.append(f"transposed wide table (items as rows, {df.shape[1]-1} entities as columns) to one row per entity")
        return t
    return df


# ----------------------------------------------------------------------------- cleaning

def _dedupe_names(cols) -> list[str]:
    seen, out = {}, []
    for c in cols:
        c = vn.clean_text(str(c)) or "col"
        if c in seen:
            seen[c] += 1
            c = f"{c}_{seen[c]}"
        else:
            seen[c] = 0
        out.append(c)
    return out


def is_texty(s: pd.Series) -> bool:
    return s.dtype == object or pd.api.types.is_string_dtype(s)


def guess_role(name: str, s: pd.Series, n: int) -> str:
    key = vn.ascii_key(name)
    words = set(key.split())
    nun = s.nunique(dropna=True)
    if pd.api.types.is_datetime64_any_dtype(s):
        return "time"
    if pd.api.types.is_numeric_dtype(s):
        vals = s.dropna()
        if (words & {"year", "nam"}) and len(vals) and vals.between(1900, 2100).all() and (vals % 1 == 0).all():
            return "time"
        if (key in ("", "unnamed 0", "stt", "index", "id") or words & {"id", "stt"}) and nun > 0.9 * len(vals):
            return "id"
        if nun <= 2:
            return "category"
        return "numeric"
    vals = s.dropna().astype(str)
    if vals.empty:
        return "empty"
    avg_len = vals.str.len().mean()
    if any(h == key or key.startswith(h + " ") or key.endswith(" " + h) for h in GEO_HINTS) and avg_len < 40:
        return "geo"
    prov_share = vals.head(500).map(lambda v: vn.normalize_province(v) is not None).mean()
    if prov_share > 0.6 and avg_len < 30:
        return "geo"
    if nun > 0.95 * len(vals) and (words & set(ID_HINTS) or avg_len < 15):
        return "id"
    if nun <= max(30, min(200, 0.05 * n)) and avg_len < 60:
        return "category"
    if avg_len >= 40:
        return "text"
    if nun > 0.5 * len(vals):
        return "id" if avg_len < 15 else "text"
    return "category"


def clean(df: pd.DataFrame, log: list[str] | None = None) -> CleanResult:
    log = log if log is not None else []
    n0 = len(df)
    df = df.copy()
    df.columns = _dedupe_names(df.columns)
    # drop pandas index columns written by to_csv
    for c in list(df.columns):
        if vn.ascii_key(c) in ("", "unnamed 0", "col 0") or re.fullmatch(r"Unnamed: \d+", c):
            s = pd.to_numeric(df[c], errors="coerce")
            if s.notna().mean() > 0.99 and s.dropna().is_monotonic_increasing:
                df = df.drop(columns=c)
                log.append(f"dropped '{c}': it is just a row index")
    df = df.dropna(how="all").dropna(axis=1, how="all")
    for c in df.columns:
        if is_texty(df[c]):
            u = df[c].dropna().unique()
            df[c] = df[c].astype(object).map(dict(zip(u, map(vn.clean_text, u))))
            df[c] = df[c].replace({k: np.nan for k in ["", "NaN", "nan", "None", "null", "NULL", "-", "N/A", "#N/A"]})
    numeric_reports = {}
    for c in list(df.columns):
        s = df[c]
        if not is_texty(s):
            continue
        key = vn.ascii_key(c)
        # dates first when the name suggests time
        if any(h in key.split() or key.startswith(h) for h in TIME_HINTS) or s.dropna().astype(str).head(200).str.match(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}").mean() > 0.8:
            d = vn.parse_dates(s)
            if d is not None:
                df[c] = d
                log.append(f"'{c}': parsed as dates (day-first), {int(d.isna().sum() - s.isna().sum())} unparseable → NaT")
                continue
        parsed, rep = vn.parse_numeric_series(s)
        if parsed is not None:
            df[c] = parsed
            numeric_reports[c] = rep
            msg = f"'{c}': text → number ({rep['ok_ratio']:.0%} parsed, decimal '{rep['decimal']}')"
            if rep["units"]:
                msg += f", VN units scaled to base (VND): {rep['units']}"
            if rep["per"]:
                msg += f", per-unit marker {rep['per']}"
            if rep["failed"]:
                msg += f", {rep['failed']} values unparseable → NaN"
            log.append(msg)
    # duplicates
    before = len(df)
    df = df.drop_duplicates()
    if len(df) < before:
        log.append(f"removed {before - len(df)} exact duplicate rows ({(before - len(df)) / before:.1%})")
    df = df.reset_index(drop=True)
    roles = {c: guess_role(c, df[c], len(df)) for c in df.columns}
    # province normalisation for geo columns
    for c in [c for c, r in roles.items() if r == "geo"]:
        if not is_texty(df[c]):
            continue
        norm = df[c].map(vn.normalize_province)
        share = norm.notna().mean() / max(df[c].notna().mean(), 1e-9)
        if share > 0.6:
            newc, newc34 = f"{c}__province", f"{c}__province_2025"
            df[newc] = norm
            df[newc34] = norm.map(vn.to_new_province)
            roles[newc], roles[newc34] = "geo", "geo"
            roles[c] = "geo_raw"  # keep for display; analyse the normalised column instead
            log.append(f"'{c}': normalised {norm.nunique()} province spellings → '{newc}'; added post-merger (34-unit) "
                       f"column '{newc34}' using Resolution 202/2025/QH15")
        else:
            # strip administrative prefixes for consistent grouping
            df[c] = df[c].map(lambda v: re.sub(r"^(Tỉnh|Thành phố|TP\.?|Quận|Huyện|Thị xã|Phường|Xã)\s+", "", v, flags=re.I).strip() if isinstance(v, str) else v)
    # whole-column constants
    for c in df.columns:
        if df[c].nunique(dropna=True) <= 1 and roles.get(c) != "empty":
            roles[c] = "constant"
    # outlier flags (never delete)
    num = [c for c, r in roles.items() if r == "numeric"]
    flags = pd.DataFrame(index=df.index)
    for c in num:
        x = df[c]
        med = x.median()
        mad = (x - med).abs().median() * 1.4826
        q1, q3 = x.quantile([0.25, 0.75])
        iqr = q3 - q1
        rz = (x - med).abs() / mad if mad and mad > 0 else pd.Series(0, index=x.index)
        f = (rz > 3.5) | (x < q1 - 3 * iqr) | (x > q3 + 3 * iqr)
        flags[c] = f.fillna(False)
    if num:
        df["_outlier_any"] = flags.any(axis=1)
        roles["_outlier_any"] = "flag"
        k = int(df["_outlier_any"].sum())
        log.append(f"flagged {k} rows ({k / max(1, len(df)):.1%}) as outliers on ≥1 numeric column (robust z>3.5 or 3×IQR); kept, not deleted")
    log.append(f"rows: {n0} raw → {len(df)} clean")
    res = CleanResult(df=df, roles=roles, log=log, numeric_reports=numeric_reports)
    res.source["outlier_counts"] = {c: int(flags[c].sum()) for c in flags.columns}
    return res


def load_and_clean(path: str | Path, sheet: str | None = None, transpose: bool | None = None) -> CleanResult:
    log: list[str] = []
    df = read_any(path, sheet=sheet, log=log)
    df = maybe_transpose(df, transpose, log)
    res = clean(df, log)
    res.source.update({"file": str(Path(path).name), "raw_shape": list(df.shape)})
    return res
