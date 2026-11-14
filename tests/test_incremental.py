"""Incremental bronze load by _row_hash: replace | append | incremental, counts in meta.runs, schema change → rebuild."""
import json

import pandas as pd
import pytest


@pytest.fixture()
def wh(tmp_path):
    from vlkit.de.warehouse import Warehouse
    w = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    yield w
    w.close()


def _csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


BASE = [{"tinh": "Hà Nội", "nam": 2023, "gia": 10.0}, {"tinh": "Đà Nẵng", "nam": 2023, "gia": 7.0},
        {"tinh": "Cần Thơ", "nam": 2024, "gia": 5.0}]


def _run(wh, tmp_path, f, mode):
    from vlkit.de.flow import run_file
    return run_file(f, dataset="inc", out_root=tmp_path / "out", wh=wh, mode=mode)


def test_incremental_skips_existing_rows(wh, tmp_path):
    f = _csv(tmp_path / "inc.csv", BASE)
    s1 = _run(wh, tmp_path, f, "incremental")
    assert s1["load"]["mode"] == "incremental" and s1["load"]["inserted"] == 3 and s1["load"]["skipped"] == 0
    s2 = _run(wh, tmp_path, f, "incremental")                         # same file again → nothing new
    assert s2["load"]["inserted"] == 0 and s2["load"]["skipped"] == 3
    _csv(f, BASE + [{"tinh": "Huế", "nam": 2024, "gia": 6.0}])        # one new row appended upstream
    s3 = _run(wh, tmp_path, f, "incremental")
    assert s3["load"]["inserted"] == 1 and s3["load"]["skipped"] == 3
    assert wh.sql("SELECT count(*) n FROM bronze.inc__inc")["n"][0] == 4
    assert wh.sql("SELECT count(DISTINCT _row_hash) n FROM bronze.inc__inc")["n"][0] == 4
    assert s3["quality"]["silver.inc__inc"]["rows"] == 4               # silver rebuilt from full bronze
    assert s3["load"]["silver"]["silver.inc__inc"]["new_bronze_rows"] == 1
    # counts recorded in meta.runs
    det = [json.loads(d) for (d,) in wh.con.execute(
        "SELECT detail FROM meta.runs WHERE run_id=? AND step='ingest:inc'", [s3["run_id"]]).fetchall()]
    assert det and det[0]["inserted"] == 1 and det[0]["skipped"] == 3 and det[0]["mode"] == "incremental"
    # parquet lake mirrors the accumulated bronze table
    assert len(pd.read_parquet(wh.lake / "bronze" / "inc__inc.parquet")) == 4
    # pipeline.json exposes the load block
    pj = json.loads((tmp_path / "out" / "inc" / "pipeline.json").read_text(encoding="utf-8"))
    assert pj["load"]["inserted"] == 1


def test_append_and_replace(wh, tmp_path):
    f = _csv(tmp_path / "inc.csv", BASE)
    _run(wh, tmp_path, f, "replace")
    s = _run(wh, tmp_path, f, "append")
    assert s["load"]["inserted"] == 3 and wh.sql("SELECT count(*) n FROM bronze.inc__inc")["n"][0] == 6
    assert s["quality"]["silver.inc__inc"]["rows"] == 3                # duplicates removed in silver
    s = _run(wh, tmp_path, f, "replace")
    assert s["load"]["mode"] == "replace" and wh.sql("SELECT count(*) n FROM bronze.inc__inc")["n"][0] == 3


def test_schema_change_triggers_full_rebuild(wh, tmp_path):
    f = _csv(tmp_path / "inc.csv", BASE)
    _run(wh, tmp_path, f, "incremental")
    _csv(f, [{**r, "dien_tich": 50} for r in BASE])                   # new column
    s = _run(wh, tmp_path, f, "incremental")
    t = s["load"]["tables"]["bronze.inc__inc"]
    assert t["rebuilt"] and "schema" in t["reason"] and t["inserted"] == 3
    cols = [c["name"] for c in wh.columns("bronze.inc__inc")]
    assert "dien_tich" in cols and wh.sql("SELECT count(*) n FROM bronze.inc__inc")["n"][0] == 3


def test_row_hash_ignores_meta_columns():
    from vlkit.de.warehouse import row_hash
    a = pd.DataFrame(BASE)
    b = a.assign(_src="x", _ingested_at="2026-01-01")
    assert list(row_hash(a)) == list(row_hash(b))


def test_bad_mode_rejected(wh, tmp_path):
    from vlkit.de.flow import run_file
    with pytest.raises(ValueError):
        run_file(_csv(tmp_path / "x.csv", BASE), out_root=tmp_path / "out", wh=wh, mode="upsert")


def test_api_and_cli_accept_mode(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("KIT_OUT_DIR", str(tmp_path / "out"))
    from api.main import app
    c = TestClient(app)
    src = {"name": "a", "kind": "file", "uri": "x.csv"}
    assert c.post("/api/ingest", json={"dataset": "d", "sources": [src], "mode": "upsert"}).status_code == 422
    from api.routes.pipeline import IngestIn
    assert IngestIn(dataset="d", sources=[src]).mode == "replace"
    assert IngestIn(dataset="d", sources=[src], mode="incremental").mode == "incremental"
    import de
    with pytest.raises(SystemExit):
        de.main(["file", "x.csv", "--mode", "upsert"])
