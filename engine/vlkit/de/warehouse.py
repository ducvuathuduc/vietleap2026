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
import threading
from pathlib import Path

import duckdb
import pandas as pd

from .sources import now_iso

KIT = Path(__file__).resolve().parents[3]
LAYERS = ("bronze", "silver", "gold")
_READONLY_OK = re.compile(r"^\s*(with|select|describe|show|summarize|pragma\s+table_info|explain)\b", re.I)
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|copy|attach|detach|install|load|export|import|"
                        r"call|set|reset|checkpoint|vacuum|truncate|use)\b|read_\w+\s*\(|\bglob\s*\(", re.I)
# table functions / replacement scans that touch the filesystem or the process environment in DuckDB, e.g.
# sniff_csv('/etc/x'), parquet_scan(..), FROM 'file.csv', FROM "file.parquet", query('..'), current_setting()
_FN_DENY = ["sniff_csv", r"parquet_\w+", r"\w+_scan", "query_table", "query", "get" + "env", "current_setting",
            "json_execute_serialized_sql", "duckdb_secrets", "which_secret", "load_extension", r"iceberg_\w+", r"delta_\w+"]
_FILE_ACCESS = re.compile(r"\b(" + "|".join(_FN_DENY) + r")\s*\(|"
                          r"\b(from|join)\s*\(?\s*'|,\s*'[^']*\.(csv|tsv|parquet|json|jsonl|xlsx|txt|gz)'|"
                          r"\b(from|join)\s+\"[^\"]*[./\\:][^\"]*\"", re.I)
SQL_TIMEOUT_S = 20.0


LOAD_MODES = ("replace", "append", "incremental")


def row_hash(df: pd.DataFrame) -> pd.Series:
    """Stable per-row hash of the source columns (meta columns starting with '_' excluded) as text."""
    cols = [c for c in df.columns if not str(c).startswith(("_row_hash", "_src", "_ingested_at"))]
    return pd.util.hash_pandas_object(df[cols].astype(str), index=False).astype("uint64").astype(str)


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

    def exists(self, layer: str, name: str) -> bool:
        return bool(self.con.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?",
                                     [layer, name]).fetchall()[0][0])

    def write_bronze(self, dataset: str, name: str, df: pd.DataFrame, provenance: dict, mode: str = "replace") -> dict:
        """Land a source frame in bronze.<name>.

        mode = replace      drop + recreate (default; previous behaviour)
               append       insert every incoming row after the existing ones
               incremental  insert only rows whose _row_hash (hash of the source columns, not of _src/_ingested_at)
                            is not already in the table — re-running the same file inserts 0 rows
        A schema change (different source columns, or types DuckDB cannot cast) falls back to a full rebuild.
        Returns {"table", "mode", "inserted", "skipped", "rebuilt", "rows", "reason"}.
        """
        if mode not in LOAD_MODES:
            raise ValueError(f"mode must be one of {LOAD_MODES}")
        df = df.copy()
        df.columns = [str(c) for c in df.columns]
        df["_row_hash"] = row_hash(df)
        df["_src"] = provenance.get("source", name)
        df["_ingested_at"] = provenance.get("fetched_at", now_iso())
        fq = f"bronze.{ident(name)}"
        stats = {"table": f"bronze.{name}", "mode": mode, "inserted": int(len(df)), "skipped": 0, "rebuilt": False, "reason": None}
        if mode == "replace" or not self.exists("bronze", name):
            if mode != "replace":
                stats["reason"] = "first load"
            self.write("bronze", name, df)
        else:
            old_cols = [c["name"] for c in self.columns(f"bronze.{name}")]
            if old_cols != list(df.columns):
                stats.update(rebuilt=True, reason="schema changed → full rebuild")
                self.write("bronze", name, df)
            else:
                d = _duck_safe(df)
                self.con.register("_tmp_df", d)
                try:
                    if mode == "incremental":
                        new = self.con.execute(f"SELECT count(*) FROM _tmp_df n WHERE n._row_hash NOT IN "
                                               f"(SELECT _row_hash FROM {fq} WHERE _row_hash IS NOT NULL)").fetchall()[0][0]
                        self.con.execute(f"INSERT INTO {fq} BY NAME SELECT * FROM _tmp_df n WHERE n._row_hash NOT IN "
                                         f"(SELECT _row_hash FROM {fq} WHERE _row_hash IS NOT NULL)")
                        stats.update(inserted=int(new), skipped=int(len(df) - new))
                    else:
                        self.con.execute(f"INSERT INTO {fq} BY NAME SELECT * FROM _tmp_df")
                except duckdb.Error as e:          # incompatible types = schema change
                    stats.update(rebuilt=True, inserted=int(len(df)), skipped=0,
                                 reason=f"schema changed ({type(e).__name__}) → full rebuild")
                    self.con.unregister("_tmp_df")
                    self.write("bronze", name, df)
                else:
                    self.con.unregister("_tmp_df")
                    out = self.lake / "bronze" / f"{name}.parquet"
                    out.parent.mkdir(parents=True, exist_ok=True)
                    self.con.execute(f"COPY {fq} TO '{out.as_posix()}' (FORMAT parquet)")
        stats["rows"] = int(self.con.execute(f"SELECT count(*) FROM {fq}").fetchall()[0][0])
        self.con.execute("INSERT INTO meta.sources VALUES (?,?,?,?,?,?)",
                         [dataset, name, provenance.get("kind"), provenance.get("uri"), provenance.get("fetched_at"),
                          json.dumps(provenance, ensure_ascii=False, default=str)])
        self.lineage(dataset, f"source:{provenance.get('source', name)}", stats["table"], "ingest")
        return stats

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

    def sql(self, query: str, limit: int = 1000, timeout_s: float | None = SQL_TIMEOUT_S) -> pd.DataFrame:
        """Read-only SQL for the dashboard SQL explorer and the AI analyst.

        Guard layers: (1) one statement starting with SELECT/WITH/DESCRIBE/SHOW/SUMMARIZE/PRAGMA table_info/EXPLAIN;
        (2) denylist of DDL/DML, of file/env table functions and of string-literal table refs; (3) result wrapped in
        LIMIT; (4) interrupted after timeout_s; (5) Warehouse.readonly() connections additionally run with DuckDB
        enable_external_access=false, so even an unlisted file-reading function is refused by the engine itself.
        """
        q = query.strip().rstrip(";")
        if ";" in q or not _READONLY_OK.match(q) or _FORBIDDEN.search(q):
            raise PermissionError("Only a single read-only SELECT/WITH/DESCRIBE/SUMMARIZE query is allowed")
        if _FILE_ACCESS.search(q):
            raise PermissionError("File, environment and external table functions are not allowed — query warehouse tables only")
        timer = None
        if timeout_s:
            timer = threading.Timer(timeout_s, self.con.interrupt)
            timer.daemon = True
            timer.start()
        try:
            return self.con.execute(f"SELECT * FROM ({q}) AS _q LIMIT {int(limit)}").df()
        except duckdb.InterruptException as e:
            raise TimeoutError(f"query exceeded {timeout_s:g}s and was cancelled") from e
        finally:
            if timer:
                timer.cancel()

    @classmethod
    def readonly(cls, path: str | Path | None = None, lake: str | Path | None = None) -> "Warehouse":
        """Read-only connection with DuckDB external (filesystem/network) access disabled and the config locked.
        Falls back to a normal connection (regex guards still apply) when another connection in this process holds the
        same file with a different configuration."""
        self = cls.__new__(cls)
        self.path = Path(path or KIT / "data" / "warehouse.duckdb")
        self.lake = Path(lake or KIT / "data" / "lake")
        if not self.path.exists():
            cls(self.path, self.lake).close()     # create schemas once
        try:
            self.con = duckdb.connect(str(self.path), read_only=True,
                                      config={"enable_external_access": "false", "lock_configuration": "true", "threads": "2"})
            self.hardened = True
        except duckdb.Error:
            self.con = duckdb.connect(str(self.path))
            self.hardened = False
        return self

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
