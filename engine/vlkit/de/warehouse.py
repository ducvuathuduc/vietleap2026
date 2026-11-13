"""Storage: DuckDB medallion warehouse + Parquet lake.

    bronze.<t>   raw as ingested (+ _src, _ingested_at, _row_hash) — never modified
    silver.<t>   typed, VN-parsed, de-duplicated, outliers flagged
    gold.<t>     analytical models: obt_*, fact_*, dim_*, hub_*, lnk_*, sat_*
    meta.*       sources, runs, lineage, quality

Why DuckDB: embedded (no server), columnar, reads CSV/Parquet/Excel directly, standard SQL,
millions of rows on a laptop — right-sized for a 28-hour hackathon. Parquet copies make every layer
portable to Spark/BigQuery/Postgres later.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
import pandas as pd

from .sources import now_iso

KIT = Path(__file__).resolve().parents[3]
LAYERS = ("bronze", "silver", "gold")
_READONLY_OK = re.compile(r"^\s*(with|select|describe|show|summarize|pragma\s+table_info|explain)\b", re.I)
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|copy|attach|detach|install|load|export|import|"
                        r"call|set|checkpoint|vacuum|truncate)\b|read_\w+\s*\(|\bglob\s*\(", re.I)


def ident(s: str) -> str:
    return '"' + str(s).replace('"', '""') + '"'


class Warehouse:
    def __init__(self, path: str | Path | None = None, lake: str | Path | None = None):
        self.path = Path(path or KIT / "data" / "warehouse.duckdb")
        self.lake = Path(lake or KIT / "data" / "lake")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.path))
        self.con.execute("SET threads TO 2")          # small laptops: keep memory down
        self.con.execute("SET preserve_insertion_order = false")
        for s in (*LAYERS, "meta"):
            self.con.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
        self.con.execute("""CREATE TABLE IF NOT EXISTS meta.sources(dataset TEXT, source TEXT, kind TEXT, uri TEXT,
                            fetched_at TEXT, provenance JSON)""")
        self.con.execute("""CREATE TABLE IF NOT EXISTS meta.runs(run_id TEXT, dataset TEXT, step TEXT, status TEXT,
                            started_at TEXT, finished_at TEXT, detail JSON)""")
        self.con.execute("""CREATE TABLE IF NOT EXISTS meta.lineage(dataset TEXT, from_node TEXT, to_node TEXT,
                            step TEXT, created_at TEXT)""")
        self.con.execute("CREATE TABLE IF NOT EXISTS meta.quality(dataset TEXT, tbl TEXT, created_at TEXT, report JSON)")

    # ------------------------------------------------------------------ write
    def write(self, layer: str, name: str, df: pd.DataFrame, parquet: bool = True) -> str:
        assert layer in LAYERS
        fq = f"{layer}.{ident(name)}"
        df = _duck_safe(df)
        self.con.register("_tmp_df", df)
        self.con.execute(f"CREATE OR REPLACE TABLE {fq} AS SELECT * FROM _tmp_df")
        self.con.unregister("_tmp_df")
        if parquet:
            out = self.lake / layer / f"{name}.parquet"
            out.parent.mkdir(parents=True, exist_ok=True)
            self.con.execute(f"COPY {fq} TO '{out.as_posix()}' (FORMAT parquet)")
        return f"{layer}.{name}"

    def write_bronze(self, dataset: str, name: str, df: pd.DataFrame, provenance: dict) -> str:
        df = df.copy()
        df.columns = [str(c) for c in df.columns]
        df["_row_hash"] = pd.util.hash_pandas_object(df.astype(str), index=False).astype("uint64").astype(str)
        df["_src"] = provenance.get("source", name)
        df["_ingested_at"] = provenance.get("fetched_at", now_iso())
        t = self.write("bronze", name, df)
        self.con.execute("INSERT INTO meta.sources VALUES (?,?,?,?,?,?)",
                         [dataset, name, provenance.get("kind"), provenance.get("uri"), provenance.get("fetched_at"),
                          json.dumps(provenance, ensure_ascii=False, default=str)])
        self.lineage(dataset, f"source:{provenance.get('source', name)}", t, "ingest")
        return t

    def lineage(self, dataset: str, src: str, dst: str, step: str):
        self.con.execute("INSERT INTO meta.lineage VALUES (?,?,?,?,?)", [dataset, src, dst, step, now_iso()])

    def log_run(self, run_id, dataset, step, status, started, detail=None):
        self.con.execute("INSERT INTO meta.runs VALUES (?,?,?,?,?,?,?)",
                         [run_id, dataset, step, status, started, now_iso(), json.dumps(detail or {}, default=str)])

    def save_quality(self, dataset: str, tbl: str, report: dict):
        self.con.execute("INSERT INTO meta.quality VALUES (?,?,?,?)",
                         [dataset, tbl, now_iso(), json.dumps(report, ensure_ascii=False, default=str)])

    # ------------------------------------------------------------------ read
    def read(self, fq: str) -> pd.DataFrame:
        layer, name = fq.split(".", 1)
        return self.con.execute(f"SELECT * FROM {layer}.{ident(name)}").df()

    def tables(self) -> list[dict]:
        q = """SELECT schema_name AS layer, table_name AS name, estimated_size AS rows, column_count AS cols
               FROM duckdb_tables() WHERE schema_name IN ('bronze','silver','gold','meta') ORDER BY 1, 2"""
        return self.con.execute(q).df().to_dict("records")

    def columns(self, fq: str) -> list[dict]:
        layer, name = fq.split(".", 1)
        return self.con.execute("SELECT column_name AS name, data_type AS type FROM information_schema.columns "
                                "WHERE table_schema=? AND table_name=? ORDER BY ordinal_position", [layer, name]).df().to_dict("records")

    def sql(self, query: str, limit: int = 1000) -> pd.DataFrame:
        """Read-only SQL for the dashboard SQL explorer and the AI analyst."""
        q = query.strip().rstrip(";")
        if ";" in q or not _READONLY_OK.match(q) or _FORBIDDEN.search(q):
            raise PermissionError("Only a single read-only SELECT/WITH/DESCRIBE/SUMMARIZE query is allowed")
        return self.con.execute(f"SELECT * FROM ({q}) AS _q LIMIT {int(limit)}").df()

    def close(self):
        self.con.close()


def _duck_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Mixed-type object columns break DuckDB type inference → cast them to string."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == object or pd.api.types.is_string_dtype(df[c]):
            # pandas 3 "str" dtype and mixed object columns: NaN must reach DuckDB as NULL, not the text 'NaN'
            df[c] = pd.Series([None if v is None or (isinstance(v, float) and v != v) or v is pd.NA else str(v)
                               for v in df[c].to_numpy(dtype=object)], index=df.index, dtype=object)
    return df
