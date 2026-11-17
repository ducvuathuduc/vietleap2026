import csv
import json
import os
from unittest.mock import MagicMock

import pandas as pd
import pytest


def test_gold_dictionary_and_eda_downloads(tmp_path):
    from fastapi.testclient import TestClient

    from api.main import app
    from api.store import Store, get_store
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    from vlkit.de.warehouse import Warehouse

    path = tmp_path / "measures.csv"
    pd.DataFrame({"measure": [10.5, 20.5, None, 40.5], "group": ["=danger|<tag>", None, "Z", None]}).to_csv(path, index=False)
    source = Source("input", "file", str(path), {"column_metadata": {"measure": {"unit": "kg", "description": "Measured mass"}}})
    root = tmp_path / "out"
    wh = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    try:
        run_flow("sample", [source], out_root=root, wh=wh, serve=True, serve_kwargs={"target": "measure", "reports": False})
    finally:
        wh.close()

    output = root / "sample"
    with (output / "data_dictionary.csv").open(encoding="utf-8-sig", newline="") as handle:
        columns = {row["column"]: row for row in csv.DictReader(handle) if row["gold_table"] == "gold.obt_sample"}
    assert columns["measure"]["type"] == "DOUBLE"
    assert columns["measure"]["unit"] == "kg" and columns["measure"]["description"] == "Measured mass"
    assert float(columns["measure"]["missing_pct"]) == 25
    assert "measures.csv" in columns["measure"]["source"]
    assert columns["group"]["sample"] == "'=danger|<tag>"
    assert "&lt;tag&gt;" in (output / "data_dictionary.md").read_text(encoding="utf-8")
    assert "measure" in (output / "eda.md").read_text(encoding="utf-8")

    app.dependency_overrides[get_store] = lambda: Store(root)
    try:
        with TestClient(app) as client:
            files = client.get("/api/datasets/sample").json()["files"]
            for kind in ("dictionary_csv", "dictionary_md", "eda_md"):
                assert files[kind]
                response = client.get(f"/api/datasets/sample/files/{kind}")
                assert response.status_code == 200
                assert response.headers["content-disposition"].startswith("attachment")
            assert client.get("/api/datasets/sample/files/unknown").status_code == 404
    finally:
        del app.dependency_overrides[get_store]


def test_contest_replays_snapshot_and_exports_both_languages(tmp_path, monkeypatch):
    import httpx

    from vlkit.de import connectors, snapshots
    from vlkit.de.contest import run_contest
    from vlkit.de.sources import load_recipe
    from vlkit.de.warehouse import Warehouse

    cache = tmp_path / "cache"
    monkeypatch.setattr(connectors, "CACHE", cache)
    monkeypatch.setattr(snapshots, "CACHE", cache)
    recipe_file = tmp_path / "sources.yaml"
    recipe_file.write_text("dataset: replay\nsources:\n  - {name: metrics, kind: api, uri: 'https://example.test/metrics', license: synthetic test}\n", encoding="utf-8")
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("Which groups have high `measure_value`?", encoding="utf-8")
    rows = [{"measure_value": n * 1.5, "group": "Alpha" if n % 2 else "Beta"} for n in range(1, 61)]
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=rows))) as client:
        monkeypatch.setitem(connectors.CONNECTORS, "api", lambda source: connectors.ingest_api(source, client))
        manifests = snapshots.prepare_snapshot(load_recipe(recipe_file))
    assert len(manifests) == 1

    def reject_network(*args, **kwargs):
        pytest.fail("the offline run tried a network request")

    monkeypatch.setattr(httpx.Client, "send", reject_network)
    monkeypatch.setitem(connectors.CONNECTORS, "api", reject_network)
    wh = Warehouse(tmp_path / "contest.duckdb", lake=tmp_path / "lake")
    try:
        paths = run_contest(str(recipe_file), brief_file, out_root=tmp_path / "out", wh=wh)
        assert {"brief.json", "results.json", "data_dictionary.csv", "data_dictionary.md", "eda.md", "dashboard.html",
                "deck.pptx", "deck.vi.pptx", "pitch.md", "pitch.en.md"} <= {path.name for path in paths}
        results = json.loads((tmp_path / "out/replay/results.json").read_text(encoding="utf-8"))
        assert results["meta"]["target"] == "measure_value"
        assert len(wh.read("gold.fact_replay")) == 60
    finally:
        wh.close()


S3_VARS = ("KIT_S3_ENDPOINT", "KIT_S3_BUCKET", "KIT_S3_ACCESS_KEY_ID", "KIT_S3_SECRET_ACCESS_KEY")


def test_sync_mirrors_only_gold_and_redacts_errors(tmp_path, monkeypatch):
    import duckdb
    from vlkit.de.mirror import sync_gold

    for name, value in zip(S3_VARS, ("https://r2.example.test", "example", "access", "secret-for-test")):
        monkeypatch.setenv(name, value)
    for layer in ("bronze", "gold"):
        directory = tmp_path / layer
        directory.mkdir()
        pd.DataFrame({"n": [2]}).to_parquet(directory / "fact.parquet", index=False)
    session = MagicMock()
    monkeypatch.setattr(duckdb, "connect", lambda **kwargs: session)
    assert sync_gold(tmp_path) == ["s3://example/gold/fact.parquet"]
    copy = session.execute.call_args_list[-1]
    assert copy.args[-1] == [str(tmp_path / "gold/fact.parquet"), "s3://example/gold/fact.parquet"]
    session.execute.side_effect = RuntimeError("secret-for-test")
    with pytest.raises(RuntimeError, match="httpfs") as exc:
        sync_gold(tmp_path)
    assert "secret-for-test" not in str(exc.value)


@pytest.mark.skipif(not all(os.getenv(key) for key in S3_VARS), reason="S3 test environment variables absent")
def test_s3_live_mirror(tmp_path):
    from uuid import uuid4
    from vlkit.de.mirror import sync_gold

    gold = tmp_path / "gold"
    gold.mkdir()
    filename = f"vietleap_smoke_{uuid4().hex}.parquet"
    pd.DataFrame({"n": [2]}).to_parquet(gold / filename, index=False)
    assert sync_gold(tmp_path) == [f"s3://{os.environ['KIT_S3_BUCKET']}/gold/{filename}"]
