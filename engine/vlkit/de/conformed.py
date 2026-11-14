"""Conformed dimensions + integrated facts across several silver tables (Kimball "bus matrix").

When ≥2 silver tables share a business key — province (tỉnh), year (năm), date, ticker (mã CK), country
(ISO3) or any key declared under ``keys:`` in sources.yaml — we build ONE shared dimension per key and
point every source at it:

    gold.<ds>__cdim_geo        geo_key (surrogate) · province · province_2025 (63→34, NQ 202/2025/QH15) ·
                               province_2025_key · region (6 vùng GSO)
    gold.<ds>__cdim_date       date_key (YYYYMMDD) · date · year · quarter · month · month_key · weekday
    gold.<ds>__cdim_year       year_key · year
    gold.<ds>__cdim_<key>      <key>_key (surrogate) · <key> (normalised upper/trim) · n_sources
    gold.<ds>__cfact_<src>     every silver row + the conformed foreign keys (+ _source_table)
    gold.obt_integrated_<ds>   primary rows (sheets with the same schema stacked) LEFT JOIN every other
                               source on the shared conformed keys — only when that source is unique at
                               the join grain (or the YAML says how to aggregate it), so a join never
                               multiplies rows

Join coverage (matched / unmatched rows per source, unmatched samples, pairwise key overlap) goes to
meta.join_coverage, pipeline.json["conformed"], conformed.json and lineage.json.

Per-source YAML options (``conform:`` next to ``options:``):

    conform: {where: "iso3 = 'VNM'", agg: mean, geo_level: "2025"}

``where`` filters the source before it is joined (SQL predicate on its columns, read-only), ``agg``
(mean|sum|min|max|first) aggregates a source that has several rows per join key, ``geo_level: 2025`` says
its province names are post-merger (34) units so the join happens on province_2025.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..vn import ascii_key, normalize_province, to_new_province
from .warehouse import Warehouse, ident

RES = Path(__file__).resolve().parents[1] / "resources"

# YAML key name → builtin key type (anything else becomes a generic dim_<key>)
KEY_ALIASES = {
    "province": "geo", "tinh": "geo", "tinh thanh": "geo", "tinh tp": "geo", "geo": "geo", "provinces": "geo",
    "year": "year", "nam": "year",
    "date": "date", "ngay": "date",
    "ticker": "ticker", "ma ck": "ticker", "ma_ck": "ticker", "symbol": "ticker", "ma cp": "ticker",
    "country": "country", "iso3": "country", "quoc gia": "country",
}
TICKER_NAMES = {"ma ck", "ma cp", "ma chung khoan", "ma co phieu", "ticker", "symbol", "stock code", "ma"}
COUNTRY_NAMES = {"iso3", "iso3 code", "countryiso3code", "country code", "country iso3", "ma quoc gia", "iso"}
YEAR_TOKENS = {"year", "nam", "date", "ky", "period", "time"}
AGGS = {"mean": "avg", "avg": "avg", "sum": "sum", "min": "min", "max": "max", "first": "any_value"}
_FORBIDDEN = re.compile(r";|--|/\*|\b(insert|update|delete|drop|alter|create|copy|attach|install|load|pragma|call|set|"
                        r"export|import)\b|read_\w+\s*\(", re.I)
MAX_TABLES = 12
MAX_JOIN_COLS = 40


@lru_cache(maxsize=1)
def new_province_names() -> frozenset[str]:
    with open(RES / "province_63_to_34.csv", encoding="utf-8") as f:
        return frozenset(r["new_province"] for r in csv.DictReader(f))


def _slug(c: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", ascii_key(c)).strip("_")[:40] or "col"


@dataclass
class TableKeys:
    table: str                                   # silver.<name>
    short: str                                   # name without the "<ds>__" prefix
    cols: dict[str, str] = field(default_factory=dict)      # key type → column
    derived_year: bool = False                   # year comes from the date column
    geo_level: str = "63"                        # "63" | "2025"
    geo_raw: bool = False                        # geo column holds raw spellings (needs meta.geo_alias)
    rows: int = 0
    signature: tuple = ()                        # non-meta column set (same schema → stacked)
    conform: dict = field(default_factory=dict)

    @property
    def types(self) -> set[str]:
        t = set(self.cols)
        if self.derived_year or "year" in self.cols:
            t.add("year")
        return t


# ---------------------------------------------------------------------------------------------- detection
def _match_spec(df: pd.DataFrame, names: list[str]) -> str | None:
    want = {ascii_key(str(n)) for n in names} | {_slug(str(n)) for n in names}
    for c in df.columns:
        if c.startswith("_"):
            continue
        if ascii_key(c) in want or _slug(c) in want:
            return c
    return None


def _is_year_col(s: pd.Series) -> bool:
    if not pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s):
        return False
    v = s.dropna()
    return len(v) > 0 and bool(v.between(1900, 2100).all()) and bool((v % 1 == 0).all())


def _code_share(s: pd.Series, pattern: str) -> float:
    v = s.dropna().astype(str).str.strip()
    return float(v.str.fullmatch(pattern).mean()) if len(v) else 0.0


def detect_keys(df: pd.DataFrame, roles: dict, spec: dict | None = None) -> dict[str, str]:
    """Key type → column for one silver table. ``spec`` = sources.yaml ``keys:`` ({key: [column names]})."""
    spec = spec or {}
    cols = [c for c in df.columns if not c.startswith("_") and not c.endswith("__imputed")]
    found: dict[str, str] = {}
    # 1. declared keys win
    for key, names in spec.items():
        names = names if isinstance(names, (list, tuple)) else [names]
        c = _match_spec(df, list(names))
        if not c:
            continue
        typ = KEY_ALIASES.get(ascii_key(str(key)), _slug(str(key)))
        if typ == "geo" and f"{c}__province" in df.columns:
            c = f"{c}__province"
        found.setdefault(typ, c)
    # 2. auto-detection
    if "geo" not in found:
        prov = [c for c in cols if c.endswith("__province")]
        if prov:
            found["geo"] = max(prov, key=lambda c: df[c].notna().mean())
    if "date" not in found:
        dt = [c for c in cols if pd.api.types.is_datetime64_any_dtype(df[c])]
        if dt:
            found["date"] = max(dt, key=lambda c: df[c].notna().mean())
    if "year" not in found:
        yr = [c for c in cols if (roles.get(c) == "time" or set(ascii_key(c).split()) & YEAR_TOKENS) and _is_year_col(df[c])]
        if yr:
            found["year"] = max(yr, key=lambda c: df[c].notna().mean())
    if "ticker" not in found:
        tk = [c for c in cols if ascii_key(c) in TICKER_NAMES and _code_share(df[c], r"[A-Z0-9]{3,5}") >= 0.9]
        if tk:
            found["ticker"] = tk[0]
    if "country" not in found:
        cc = [c for c in cols if ascii_key(c) in COUNTRY_NAMES and _code_share(df[c], r"[A-Z]{3}") >= 0.9]
        if cc:
            found["country"] = cc[0]
    return found


def _geo_level(df: pd.DataFrame, col: str, conform: dict) -> str:
    if str(conform.get("geo_level", "")).strip() in ("2025", "34"):
        return "2025"
    if str(conform.get("geo_level", "")).strip() == "63":
        return "63"
    vals = set(df[col].dropna().astype(str))
    # a list of ~all 34 post-merger units (e.g. the current Wikipedia table) is at the 2025 grain: every value
    # maps to a different post-merger unit (old spellings such as "Thừa Thiên Huế" → "Huế" included)
    new = {to_new_province(v) or v for v in vals}
    return "2025" if 30 <= len(vals) <= 34 and len(new) == len(vals) and new <= new_province_names() else "63"


def _valid_where(w: str | None) -> str | None:
    if not w:
        return None
    if _FORBIDDEN.search(w):
        raise PermissionError(f"conform.where must be a plain read-only predicate: {w!r}")
    return w


# ---------------------------------------------------------------------------------------------- build
def build_conformed(wh: Warehouse, ds: str, silver: list[str], roles_of: dict[str, dict], primary: str,
                    keys_spec: dict | None = None, conform_of: dict[str, dict] | None = None,
                    frames: dict[str, pd.DataFrame] | None = None) -> dict | None:
    """Build conformed dims + integrated facts. Returns None when fewer than two tables share a key.

    ``conform_of`` maps silver table → the source's ``conform:`` options; ``frames`` lets the caller pass
    silver DataFrames it already holds (otherwise they are read from the warehouse).
    """
    if len(silver) < 2:
        return None
    conform_of = conform_of or {}
    tks: list[TableKeys] = []
    for t in silver[:MAX_TABLES]:
        df = frames[t] if frames and t in frames else wh.read(t)
        cols = detect_keys(df, roles_of.get(t, {}), keys_spec)
        conf = conform_of.get(t, {}) or {}
        tk = TableKeys(table=t, short=t.split(".", 1)[1].removeprefix(f"{ds}__"), cols=cols, rows=len(df), conform=conf,
                       signature=tuple(sorted(c for c in df.columns if not c.startswith("_"))))
        if "date" in cols and "year" not in cols:
            tk.derived_year = True
        if "geo" in cols:
            tk.geo_raw = not cols["geo"].endswith("__province")
            if tk.geo_raw:
                _register_geo_alias(wh, df[cols["geo"]])
            tk.geo_level = _geo_level(df, cols["geo"], conf) if not tk.geo_raw else "63"
        tks.append(tk)

    counts: dict[str, int] = {}
    for tk in tks:
        for typ in tk.types:
            counts[typ] = counts.get(typ, 0) + 1
    shared = sorted(t for t, n in counts.items() if n >= 2)
    if not shared:
        return None
    if "date" in shared and "year" not in shared:
        shared.append("year")
    _ensure_province_ref(wh)

    T = lambda n: n if n == f"obt_integrated_{ds}" else f"{ds}__{n}"  # noqa: E731
    g = lambda n: f"gold.{ident(T(n))}"  # noqa: E731
    S = lambda tk: f"silver.{ident(tk.table.split('.', 1)[1])}"  # noqa: E731
    sql: list[str] = []
    dims: dict[str, str] = {}

    def geo_expr(tk: TableKeys, alias: str = "s") -> str:
        c = f"{alias}.{ident(tk.cols['geo'])}"
        if tk.geo_raw:
            return f"coalesce((SELECT a.province FROM meta.geo_alias a WHERE a.raw = CAST({c} AS VARCHAR)), CAST({c} AS VARCHAR))"
        return f"CAST({c} AS VARCHAR)"

    def year_expr(tk: TableKeys, alias: str = "s") -> str | None:
        if "year" in tk.cols:
            return f"CAST({alias}.{ident(tk.cols['year'])} AS INTEGER)"
        if tk.derived_year:
            return f"CAST(year({alias}.{ident(tk.cols['date'])}) AS INTEGER)"
        return None

    def norm_expr(tk: TableKeys, typ: str, alias: str = "s") -> str:
        return f"nullif(upper(trim(CAST({alias}.{ident(tk.cols[typ])} AS VARCHAR))), '')"

    # ---- dim_geo
    if "geo" in shared:
        parts = [f"SELECT {geo_expr(tk)} AS province FROM {S(tk)} s" for tk in tks if "geo" in tk.cols]
        sql.append(f"""CREATE OR REPLACE TABLE {g('cdim_geo')} AS
WITH v AS (SELECT DISTINCT province FROM ({' UNION ALL '.join(parts)}) u WHERE province IS NOT NULL)
SELECT row_number() OVER (ORDER BY v.province) AS geo_key, v.province,
       coalesce(r.province_2025, v.province) AS province_2025,
       dense_rank() OVER (ORDER BY coalesce(r.province_2025, v.province)) AS province_2025_key,
       r.region, r.province IS NOT NULL AS in_reference
FROM v LEFT JOIN meta.province_ref r USING (province)""")
        dims["geo"] = f"gold.{T('cdim_geo')}"
    # ---- dim_date (calendar) / dim_year
    if "date" in shared:
        parts = [f"SELECT CAST({ident(tk.cols['date'])} AS DATE) d FROM {S(tk)}" for tk in tks if "date" in tk.cols]
        u = " UNION ALL ".join(parts)
        sql.append(f"""CREATE OR REPLACE TABLE {g('cdim_date')} AS
WITH u AS ({u}), b AS (SELECT min(d) lo, max(d) hi FROM u WHERE d IS NOT NULL),
cal AS (SELECT CAST(r.d AS DATE) AS d FROM b, range(b.lo, b.hi + INTERVAL 1 DAY, INTERVAL 1 DAY) r(d)
        WHERE date_diff('day', b.lo, b.hi) <= 20000
        UNION SELECT DISTINCT d FROM u WHERE d IS NOT NULL)
SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key, d AS date, year(d) AS year, quarter(d) AS quarter,
       month(d) AS month, CAST(strftime(d, '%Y%m') AS INTEGER) AS month_key, isodow(d) AS weekday, isodow(d) >= 6 AS is_weekend
FROM cal ORDER BY 1""")
        dims["date"] = f"gold.{T('cdim_date')}"
    if "year" in shared:
        parts = [f"SELECT {year_expr(tk)} y FROM {S(tk)} s" for tk in tks if year_expr(tk)]
        sql.append(f"""CREATE OR REPLACE TABLE {g('cdim_year')} AS
SELECT DISTINCT y AS year_key, y AS year, (y // 10) * 10 AS decade FROM ({' UNION ALL '.join(parts)}) u
WHERE y IS NOT NULL ORDER BY 1""")
        dims["year"] = f"gold.{T('cdim_year')}"
    # ---- generic dims (ticker, country, YAML keys)
    for typ in [t for t in shared if t not in ("geo", "date", "year")]:
        parts = [f"SELECT {norm_expr(tk, typ)} AS v, '{tk.short}' AS src FROM {S(tk)} s" for tk in tks if typ in tk.cols]
        sql.append(f"""CREATE OR REPLACE TABLE {g('cdim_' + typ)} AS
SELECT row_number() OVER (ORDER BY v) AS {typ}_key, v AS {ident(typ)}, count(DISTINCT src) AS n_sources
FROM ({' UNION ALL '.join(parts)}) u WHERE v IS NOT NULL GROUP BY v""")
        dims[typ] = f"gold.{T('cdim_' + typ)}"

    # ---- conformed facts: every silver row + surrogate keys
    facts: dict[str, str] = {}
    for tk in tks:
        sel, joins = [], []
        if "geo" in shared and "geo" in tk.cols:
            sel += ["dg.geo_key", "dg.province_2025_key"]
            joins.append(f"LEFT JOIN {g('cdim_geo')} dg ON dg.province = {geo_expr(tk)}")
        if "date" in shared and "date" in tk.cols:
            sel.append(f"CAST(strftime(CAST(s.{ident(tk.cols['date'])} AS DATE), '%Y%m%d') AS INTEGER) AS date_key")
        if "year" in shared and year_expr(tk):
            sel.append(f"{year_expr(tk)} AS year_key")
        for typ in [t for t in shared if t not in ("geo", "date", "year") and t in tk.cols]:
            sel.append(f"d_{typ}.{typ}_key")
            joins.append(f"LEFT JOIN {g('cdim_' + typ)} d_{typ} ON d_{typ}.{ident(typ)} = {norm_expr(tk, typ)}")
        if not sel:
            continue
        name = f"cfact_{_slug(tk.short)}"
        star = "s.* EXCLUDE (_row_hash)" if _has_col(wh, tk.table, "_row_hash") else "s.*"
        sql.append(f"""CREATE OR REPLACE TABLE {g(name)} AS
SELECT row_number() OVER () AS fact_id, {', '.join(sel)}, {star}, '{tk.short}' AS _source_table
FROM {S(tk)} s {' '.join(joins)}""")
        facts[tk.table] = f"gold.{T(name)}"

    for q in sql:
        wh.con.execute(q)

    # ---- integration: stack same-schema tables, then join the others on shared keys
    pk = next((tk for tk in tks if tk.table == primary), tks[0])
    if pk.table not in facts:   # the primary shares no key with anything: dims/facts only, nothing to integrate
        pk = max((tk for tk in tks if tk.table in facts), key=lambda t: t.rows)
    base_group = [tk for tk in tks if tk.signature == pk.signature and tk.table in facts]
    if pk not in base_group:
        base_group = [pk]
    others = [tk for tk in tks if tk not in base_group and tk.table in facts]
    groups: list[list[TableKeys]] = []
    for tk in others:
        for gr in groups:
            if gr[0].signature == tk.signature:
                gr.append(tk)
                break
        else:
            groups.append([tk])

    def union(group: list[TableKeys]) -> str:
        return " UNION ALL BY NAME ".join(f"SELECT * FROM {_q(facts[tk.table])}" for tk in group)

    joins_diag, join_sql, extra_sel = [], [], []
    base_types = set.intersection(*[_fk_types(tk, shared) for tk in base_group]) if base_group else set()
    for i, gr in enumerate(groups):
        name = "+".join(tk.short for tk in gr)
        gtypes = set.intersection(*[_fk_types(tk, shared) for tk in gr])
        common = base_types & gtypes
        if "date" in common:
            common.discard("year")
        geo_on = None
        if "geo" in common:
            geo_on = "province_2025_key" if any(t.geo_level == "2025" for t in gr + base_group) else "geo_key"
        on_cols = [("date_key" if t == "date" else "year_key" if t == "year" else geo_on if t == "geo" else f"{t}_key")
                   for t in sorted(common)]
        d = {"source": name, "tables": [tk.table for tk in gr], "keys": sorted(common), "join_on": on_cols,
             "rows": sum(tk.rows for tk in gr)}
        if not on_cols:
            joins_diag.append({**d, "status": "no_shared_key", "matched_rows": 0, "match_pct": 0.0})
            continue
        conf = gr[0].conform
        where = _valid_where(conf.get("where"))
        src_sql = f"SELECT * FROM ({union(gr)}) x" + (f" WHERE {where}" if where else "")
        n_rows, n_keys = wh.con.execute(
            f"SELECT count(*), count(DISTINCT ({', '.join(on_cols)})) FROM ({src_sql}) z WHERE {' AND '.join(f'{c} IS NOT NULL' for c in on_cols)}").fetchone()
        attrs = [c["name"] for c in wh.columns(facts[gr[0].table]) if not c["name"].startswith("_") and c["name"] != "fact_id"
                 and not c["name"].endswith("_key") and c["name"] not in {tk.cols.get(t) for tk in gr for t in tk.cols}
                 and not c["name"].endswith(("__province", "__province_2025"))][:MAX_JOIN_COLS]
        agg = AGGS.get(str(conf.get("agg", "")).lower())
        if n_rows > n_keys and not agg:
            joins_diag.append({**d, "status": "grain_mismatch", "rows_filtered": int(n_rows), "distinct_keys": int(n_keys),
                               "rows_per_key": round(n_rows / max(n_keys, 1), 2), "matched_rows": 0, "match_pct": 0.0,
                               "hint": "nguồn có nhiều dòng trên mỗi khoá — thêm conform.where hoặc conform.agg trong sources.yaml"})
            continue
        alias = f"j{i}"
        pre = _slug(gr[0].short)
        num = _numeric_cols(wh, facts[gr[0].table], attrs)
        if n_rows > n_keys:   # aggregate to the join grain
            attrs = [a for a in attrs if a in num]
            inner = f"SELECT {', '.join(on_cols)}, " + ", ".join(f"{agg}({ident(a)}) AS {ident(a)}" for a in attrs) + \
                    f" FROM ({src_sql}) z GROUP BY {', '.join(on_cols)}" if attrs else f"SELECT DISTINCT {', '.join(on_cols)} FROM ({src_sql}) z"
        else:
            inner = f"SELECT {', '.join(on_cols + [ident(a) for a in attrs])} FROM ({src_sql}) z WHERE {' AND '.join(f'{c} IS NOT NULL' for c in on_cols)}"
        join_sql.append(f"LEFT JOIN ({inner}) {alias} ON " + " AND ".join(f"b.{c} = {alias}.{c}" for c in on_cols))
        extra_sel += [f"{alias}.{ident(a)} AS {ident(pre + '__' + _slug(a))}" for a in attrs]
        extra_sel.append(f"{alias}.{on_cols[0]} IS NOT NULL AS {ident('_match_' + pre)}")
        joins_diag.append({**d, "status": "joined", "aggregated": agg if n_rows > n_keys else None, "where": where,
                           "columns_added": len(attrs), "distinct_keys": int(n_keys), "_alias": alias, "_flag": f"_match_{pre}"})

    obt = T(f"obt_integrated_{ds}")
    base_sql = union(base_group)
    geo_cols = ""
    if "geo" in shared and all("geo" in tk.cols for tk in base_group):
        geo_cols = ", dg.province AS _geo_province, dg.province_2025 AS _geo_province_2025, dg.region AS _geo_region"
    obt_sql = (f"CREATE OR REPLACE TABLE gold.{ident(obt)} AS SELECT b.*{geo_cols}"
               + (", " + ", ".join(extra_sel) if extra_sel else "")
               + f" FROM ({base_sql}) b "
               + (f"LEFT JOIN {g('cdim_geo')} dg ON dg.geo_key = b.geo_key " if geo_cols else "")
               + " ".join(join_sql))
    wh.con.execute(obt_sql)
    sql.append(obt_sql)
    total = wh.con.execute(f"SELECT count(*) FROM gold.{ident(obt)}").fetchone()[0]
    base_rows = sum(tk.rows for tk in base_group)

    # ---- join coverage
    for d in joins_diag:
        if d["status"] != "joined":
            continue
        flag, on_cols = d.pop("_flag"), d["join_on"]
        d.pop("_alias", None)
        m = wh.con.execute(f"SELECT count(*) FILTER (WHERE {ident(flag)}), count(*) FROM gold.{ident(obt)}").fetchone()
        d["matched_rows"], d["unmatched_rows"] = int(m[0]), int(m[1] - m[0])
        d["match_pct"] = round(100 * m[0] / max(m[1], 1), 1)
        label = _label_expr(on_cols, "geo" in d["keys"])
        d["unmatched_samples"] = [str(r[0]) for r in wh.con.execute(
            f"SELECT {label} AS k, count(*) n FROM gold.{ident(obt)} b WHERE NOT {ident(flag)} AND k IS NOT NULL "
            f"GROUP BY 1 ORDER BY n DESC LIMIT 5").fetchall()]
        used = wh.con.execute(f"SELECT count(DISTINCT ({', '.join('b.' + c for c in on_cols)})) FROM gold.{ident(obt)} b "
                              f"WHERE {ident(flag)}").fetchone()[0]
        d["source_keys_used"] = int(used)

    sources_cov = []
    for tk in tks:
        if tk.table not in facts:
            continue
        f = _q(facts[tk.table])
        row = {"table": tk.table, "source": tk.short, "rows": tk.rows, "keys": {}, "geo_level": tk.geo_level if "geo" in tk.cols else None}
        for typ in sorted(_fk_types(tk, shared)):
            col = "date_key" if typ == "date" else "year_key" if typ == "year" else "geo_key" if typ == "geo" else f"{typ}_key"
            src_col = tk.cols.get(typ) or (tk.cols.get("date") if typ == "year" else None)
            null_src = wh.con.execute(f"SELECT count(*) FROM {S(tk)} WHERE {ident(src_col)} IS NULL").fetchone()[0] if src_col else 0
            matched = wh.con.execute(f"SELECT count(*) FROM {f} WHERE {col} IS NOT NULL").fetchone()[0]
            info = {"column": src_col, "matched_rows": int(matched), "null_key_rows": int(null_src),
                    "unmatched_rows": int(tk.rows - matched - null_src),
                    "match_pct": round(100 * matched / max(tk.rows, 1), 1)}
            if typ == "geo":
                bad = wh.con.execute(f"SELECT count(*) FROM {f} x JOIN {g('cdim_geo')} d USING (geo_key) WHERE NOT d.in_reference").fetchone()[0]
                info["outside_reference_rows"] = int(bad)
            row["keys"][typ] = info
        sources_cov.append(row)

    overlap = []
    for typ in shared:
        have = [tk for tk in tks if tk.table in facts and typ in _fk_types(tk, shared)]
        col = "date_key" if typ == "date" else "year_key" if typ == "year" else "geo_key" if typ == "geo" else f"{typ}_key"
        for a_i, a in enumerate(have):
            for b in have[a_i + 1:]:
                na, nb, both = wh.con.execute(
                    f"WITH a AS (SELECT DISTINCT {col} k FROM {_q(facts[a.table])} WHERE {col} IS NOT NULL), "
                    f"b AS (SELECT DISTINCT {col} k FROM {_q(facts[b.table])} WHERE {col} IS NOT NULL) "
                    f"SELECT (SELECT count(*) FROM a), (SELECT count(*) FROM b), (SELECT count(*) FROM a JOIN b USING (k))").fetchone()
                overlap.append({"key": typ, "a": a.short, "b": b.short, "a_keys": int(na), "b_keys": int(nb), "shared_keys": int(both),
                                "jaccard": round(both / max(na + nb - both, 1), 3)})

    diag = {"shared_keys": shared, "dims": dims, "facts": facts, "integrated": f"gold.{obt}",
            "integrated_rows": int(total), "base": [tk.table for tk in base_group], "base_rows": int(base_rows),
            "row_explosion": bool(total != base_rows), "joins": joins_diag, "sources": sources_cov, "overlap": overlap,
            "detected": {tk.table: {**tk.cols, **({"year": f"year({tk.cols['date']})"} if tk.derived_year else {})} for tk in tks}}
    _save_coverage(wh, ds, diag)
    tables = list(dims.values()) + list(facts.values()) + [f"gold.{obt}"]
    return {"sql": sql, "tables": tables, "diagnostics": diag}


# ---------------------------------------------------------------------------------------------- helpers
def _q(fq: str) -> str:
    layer, name = fq.split(".", 1)
    return f"{layer}.{ident(name)}"


def _has_col(wh: Warehouse, fq: str, col: str) -> bool:
    return any(c["name"] == col for c in wh.columns(fq))


def _numeric_cols(wh: Warehouse, fq: str, cols: list[str]) -> set[str]:
    num = ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "FLOAT", "DOUBLE", "DECIMAL", "REAL", "UBIGINT", "UINTEGER")
    return {c["name"] for c in wh.columns(fq) if c["name"] in cols and c["type"].split("(")[0].upper() in num}


def _fk_types(tk: TableKeys, shared: list[str]) -> set[str]:
    return {t for t in tk.types if t in shared}


def _label_expr(on_cols: list[str], has_geo: bool) -> str:
    parts = []
    for c in on_cols:
        if c in ("geo_key", "province_2025_key") and has_geo:
            parts.append("coalesce(b._geo_province, CAST(b.geo_key AS VARCHAR))" if c == "geo_key"
                         else "coalesce(b._geo_province_2025, CAST(b.province_2025_key AS VARCHAR))")
        else:
            parts.append(f"CAST(b.{c} AS VARCHAR)")
    return " || ' · ' || ".join(f"coalesce({p}, '∅')" for p in parts) if parts else "''"


def _register_geo_alias(wh: Warehouse, s: pd.Series):
    wh.con.execute("CREATE TABLE IF NOT EXISTS meta.geo_alias(raw TEXT PRIMARY KEY, province TEXT)")
    vals = [str(v) for v in s.dropna().astype(str).unique()]
    rows = [(v, normalize_province(v)) for v in vals]
    rows = [(r, p) for r, p in rows if p]
    if rows:
        wh.con.executemany("INSERT OR REPLACE INTO meta.geo_alias VALUES (?, ?)", rows)


def _ensure_province_ref(wh: Warehouse):
    from .modeling import _ensure_ref_tables
    _ensure_ref_tables(wh)


def _save_coverage(wh: Warehouse, ds: str, diag: dict):
    from .sources import now_iso
    wh.con.execute("""CREATE TABLE IF NOT EXISTS meta.join_coverage(dataset TEXT, created_at TEXT, source TEXT,
                      kind TEXT, keys TEXT, rows BIGINT, matched_rows BIGINT, unmatched_rows BIGINT, match_pct DOUBLE,
                      status TEXT, detail JSON)""")
    wh.con.execute("DELETE FROM meta.join_coverage WHERE dataset = ?", [ds])
    ts = now_iso()
    for s in diag["sources"]:
        for typ, k in s["keys"].items():
            wh.con.execute("INSERT INTO meta.join_coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           [ds, ts, s["source"], "dimension", typ, s["rows"], k["matched_rows"], k["unmatched_rows"],
                            k["match_pct"], "ok" if k["unmatched_rows"] == 0 else "partial", json.dumps(k, ensure_ascii=False)])
    for j in diag["joins"]:
        wh.con.execute("INSERT INTO meta.join_coverage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       [ds, ts, j["source"], "integration", ",".join(j["keys"]), diag["integrated_rows"], j.get("matched_rows", 0),
                        j.get("unmatched_rows", diag["integrated_rows"] - j.get("matched_rows", 0)), j.get("match_pct", 0.0),
                        j["status"], json.dumps(j, ensure_ascii=False, default=str)])
