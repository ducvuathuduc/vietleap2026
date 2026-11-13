"""Data-engineering layer: file + sql sources → bronze/silver/gold (all four models), read-only SQL guard, API."""
import sqlite3

import pandas as pd
import pytest


@pytest.fixture()
def wh(tmp_path):
    from vlkit.de.warehouse import Warehouse
    w = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    yield w
    w.close()


@pytest.fixture()
def sources(tmp_path, kit_root):
    from vlkit.de.sources import Source
    db = tmp_path / "t.sqlite"
    con = sqlite3.connect(db)
    pd.DataFrame({"tinh": ["Hà Nội", "TP HCM", "Đà Nẵng"], "nam": [2023, 2023, 2024], "chi": [1.0, 2.0, 3.0]}).to_sql("t", con, index=False)
    con.close()
    return [Source("bds", "file", str(kit_root / "data/practice/synthetic_messy_bds.csv")),
            Source("budget", "sql", f"sqlite:///{db}", {"query": "SELECT * FROM t"})]


def test_flow_builds_all_models(wh, sources, tmp_path):
    from vlkit.de.flow import run_flow
    s = run_flow("Test DS", sources, out_root=tmp_path / "out", wh=wh, primary="bds")
    assert s["dataset"] == "test_ds"
    assert len(s["bronze"]) == 2 and len(s["silver"]) == 2
    for m in ("obt", "star", "snowflake", "data_vault"):
        assert s["models"][m]["tables"], m
        assert "erDiagram" in s["models"][m]["erd"]
    fact = wh.sql("SELECT count(*) AS n FROM gold.fact_test_ds")["n"][0]
    assert fact == s["quality"]["silver.test_ds__bds"]["rows"]
    # every fact row resolves to a geo dimension row when it has a province
    orphans = wh.sql("SELECT count(*) n FROM gold.fact_test_ds f LEFT JOIN gold.test_ds__dim_geo g USING (geo_key) "
                     "WHERE f.geo_key IS NOT NULL AND g.geo_key IS NULL")["n"][0]
    assert orphans == 0
    q = s["quality"]["silver.test_ds__bds"]
    assert q["score_after"] >= q["score_before"]
    assert (tmp_path / "out/test_ds/models/star.sql").exists()


def test_sql_is_read_only(wh, sources, tmp_path):
    from vlkit.de.flow import run_flow
    run_flow("ro", sources[:1], out_root=tmp_path / "out", wh=wh)
    for bad in ["DROP TABLE gold.obt_ro", "SELECT 1; DROP TABLE gold.obt_ro", "COPY gold.obt_ro TO 'x.csv'",
                "SELECT * FROM read_csv('/etc/passwd')", "CREATE TABLE x AS SELECT 1"]:
        with pytest.raises(PermissionError):
            wh.sql(bad)
    assert len(wh.sql("SELECT * FROM gold.obt_ro", limit=5)) == 5


def test_sql_connector_refuses_writes(tmp_path):
    from vlkit.de.connectors import ingest
    from vlkit.de.sources import Source
    with pytest.raises(PermissionError):
        ingest(Source("x", "sql", f"sqlite:///{tmp_path / 'a.db'}", {"query": "DELETE FROM t"}))


def test_api_connector_paging_and_retry(monkeypatch, tmp_path):
    import httpx
    from vlkit.de import connectors
    from vlkit.de.sources import Source
    monkeypatch.setattr(connectors, "CACHE", tmp_path)
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        page = int(req.url.params.get("page", 1))
        return httpx.Response(200, json=[{"page": page, "pages": 2}, [{"date": str(2020 + page), "value": page}]])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(connectors.time, "sleep", lambda *_: None)
    r = connectors.ingest_api(Source("wb", "api", "https://x.test/api", {"records_path": "1", "paging": "worldbank", "cache": False}), client=client)
    assert len(r.frames["wb"]) == 2 and r.provenance["pages"] == 2


def test_scrape_respects_robots(monkeypatch):
    import httpx
    from vlkit.de import connectors
    from vlkit.de.sources import Source

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        return httpx.Response(200, text="<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table>")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(connectors, "robots_allows", lambda url, c=None: not url.endswith("/private"))
    r = connectors.ingest_scrape(Source("s", "scrape", "https://x.test/private", {"urls": ["https://x.test/private", "https://x.test/ok"], "delay": [0, 0]}), client=client)
    assert r.provenance["robots_disallowed"] == ["https://x.test/private"]
    assert any(len(df) == 1 for df in r.frames.values())


def test_api_routes(tmp_path, monkeypatch, kit_root):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("KIT_OUT_DIR", str(tmp_path / "out"))
    from api.settings import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
    from api.main import app
    c = TestClient(app)
    assert "api" in c.get("/api/sources/kinds").json()["kinds"]
    assert c.post("/api/sql", json={"query": "DROP TABLE x"}).status_code == 403


def test_api_ingest_validation(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("KIT_OUT_DIR", str(tmp_path / "out"))
    from api.main import app
    c = TestClient(app)
    ok_src = {"name": "a", "kind": "file", "uri": "x.csv"}
    bad = [
        {"dataset": "d", "sources": []},                                                    # no sources
        {"dataset": " ", "sources": [ok_src]},                                              # blank dataset
        {"dataset": "d", "sources": [{**ok_src, "kind": "ftp"}]},                           # unknown kind
        {"dataset": "d", "sources": [{**ok_src, "name": "bad name!"}]},                     # invalid name
        {"dataset": "d", "sources": [{**ok_src, "uri": "   "}]},                            # blank uri
        {"dataset": "d", "sources": [ok_src, ok_src]},                                      # duplicate names
        {"dataset": "d", "sources": [ok_src], "primary": "zzz"},                            # unknown primary
        {"dataset": "d", "sources": [ok_src], "impute": "mean"},                            # unsupported impute
    ]
    for body in bad:
        assert c.post("/api/ingest", json=body).status_code == 422, body
    assert c.post("/api/sql", json={"query": "SELECT 1", "limit": 0}).status_code == 422
    assert c.post("/api/sql", json={"query": ""}).status_code == 422
    assert c.get("/api/ingest/nope").status_code == 404
    assert c.get("/api/datasets/does_not_exist/pipeline").status_code == 404


def test_api_ingest_job_and_dataset_endpoints(tmp_path, monkeypatch, kit_root):
    """Runs a real (small) ingest job through the API and reads every per-dataset DE endpoint."""
    import time
    from fastapi.testclient import TestClient
    from vlkit.de.warehouse import Warehouse
    monkeypatch.setenv("KIT_OUT_DIR", str(tmp_path / "out"))
    from api.main import app
    from api.routes import pipeline as routes
    monkeypatch.setattr(routes, "Warehouse", lambda: Warehouse(tmp_path / "wh.duckdb", tmp_path / "lake"))
    c = TestClient(app)
    src = {"name": "firms", "kind": "file", "uri": str(kit_root / "data/practice/wdi_asia_fiscal_panel.csv")}
    r = c.post("/api/ingest", json={"dataset": "api_t", "sources": [src], "serve": False})
    assert r.status_code == 202
    job_id = r.json()["id"]
    for _ in range(240):
        j = c.get(f"/api/ingest/{job_id}").json()
        if j["status"] in ("done", "error"):
            break
        time.sleep(0.5)
    assert j["status"] == "done", j["error"]
    p = c.get("/api/datasets/api_t/pipeline").json()
    assert p["bronze"] and p["silver"] and p["gold"]
    q = c.get("/api/datasets/api_t/quality").json()
    t = next(iter(q.values()))
    assert {"before", "after", "cleaning_log", "score_before", "score_after"} <= set(t)
    lin = c.get("/api/datasets/api_t/lineage").json()
    assert lin["nodes"] and lin["edges"] and lin["mermaid"].startswith("flowchart")
    m = c.get("/api/datasets/api_t/models").json()
    assert set(m["models"]) == {"obt", "star", "snowflake", "data_vault"} and m["sql"]
    assert c.get("/api/datasets/api_t/provenance").json()[0]["source"] == "firms"
