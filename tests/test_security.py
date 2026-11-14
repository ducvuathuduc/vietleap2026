"""Security controls (docs/security/threat-model.md): read-only SQL that cannot touch the filesystem, timeouts, …"""
import pandas as pd
import pytest


@pytest.fixture()
def wh(tmp_path):
    from vlkit.de.warehouse import Warehouse
    w = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    w.write("gold", "t", pd.DataFrame({"a": range(10), "b": list("abcdefghij")}))
    w.close()
    ro = Warehouse.readonly(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    yield ro
    ro.close()


@pytest.fixture()
def secret_file(tmp_path):
    p = tmp_path / "secret.csv"
    p.write_text("token\nTOP-SECRET-123\n")
    return p


ATTACKS = [
    "DROP TABLE gold.t", "SELECT 1; DROP TABLE gold.t", "INSERT INTO gold.t VALUES (1,'x')",
    "SELECT * FROM read_csv('{f}')", "SELECT * FROM sniff_csv('{f}')", "SELECT * FROM '{f}'", 'SELECT * FROM "{f}"',
    "SELECT * FROM parquet_scan('{f}')", "SELECT * FROM glob('/etc/*')", "SELECT current_setting('home_directory')",
    "SELECT * FROM query('SELECT 1')", "ATTACH '{f}' AS x", "COPY gold.t TO '{f}'", "SET enable_external_access=true",
    "WITH x AS (SELECT 1) SELECT * FROM x JOIN '{f}' ON true", "SELECT * FROM gold.t, '{f}'",
]


@pytest.mark.parametrize("q", ATTACKS)
def test_sql_attacks_refused(wh, secret_file, q):
    with pytest.raises(PermissionError):
        wh.sql(q.format(f=secret_file))


def test_readonly_connection_is_hardened(wh, secret_file):
    assert wh.hardened
    # even bypassing the regex layer, the engine refuses file access and writes
    import duckdb
    with pytest.raises(duckdb.Error):
        wh.con.execute(f"SELECT * FROM sniff_csv('{secret_file}')").fetchall()
    with pytest.raises(duckdb.Error):
        wh.con.execute("CREATE TABLE gold.x AS SELECT 1").fetchall()


def test_legit_queries_still_work(wh):
    assert wh.sql("SELECT count(*) n FROM gold.t")["n"][0] == 10
    assert len(wh.sql('SELECT * FROM gold."t" WHERE b IN (\'a\', \'b\')')) == 2
    assert wh.sql("SELECT 'dataset' AS s, a FROM gold.t ORDER BY a LIMIT 1")["s"][0] == "dataset"
    assert len(wh.sql("DESCRIBE gold.t")) == 2
    assert len(wh.sql("SELECT * FROM gold.t", limit=3)) == 3


def test_sql_timeout(wh):
    with pytest.raises(TimeoutError):
        wh.sql("SELECT count(*) FROM range(1000000000) a, range(1000) b", timeout_s=0.5)


def test_api_sql_rejects_file_read(tmp_path, monkeypatch, secret_file):
    from fastapi.testclient import TestClient
    from api.main import app
    c = TestClient(app)
    r = c.post("/api/sql", json={"query": f"SELECT * FROM sniff_csv('{secret_file}')"})
    assert r.status_code == 403 and "TOP-SECRET" not in r.text
