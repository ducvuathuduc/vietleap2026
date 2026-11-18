"""Tests for Feature 008: 34-province aggregation endpoint `/geo`."""
import json

import pandas as pd


def test_api_geo_equals_pandas_and_validates_inputs(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("KIT_OUT_DIR", str(tmp_path / "out"))
    from api.main import app

    out_ds = tmp_path / "out" / "prov"
    out_ds.mkdir(parents=True)
    df = pd.DataFrame({
        "province": ["Hà Nội", "TP. Hồ Chí Minh", "Bình Dương", "Đà Nẵng", "Hà Nội", "Thừa Thiên Huế"],
        "_province_2025": ["Hà Nội", "Hồ Chí Minh", "Hồ Chí Minh", "Đà Nẵng", "Hà Nội", "Huế"],
        "_region": ["Đồng bằng sông Hồng", "Đông Nam Bộ", "Đông Nam Bộ", "Bắc Trung Bộ và Duyên hải miền Trung", "Đồng bằng sông Hồng", "Bắc Trung Bộ và Duyên hải miền Trung"],
        "transfers": [100.0, 200.0, 150.0, 80.0, 120.0, 60.0],
        "rate_pct": [10.0, 20.0, 12.0, 8.0, 11.0, 9.0],
    })
    df.to_parquet(out_ds / "clean.parquet", index=False)
    (out_ds / "results.json").write_text(json.dumps({
        "meta": {
            "id": "prov", "name": "Prov", "domain": "public_finance", "rows": 6,
            "target": "transfers", "source_file": "prov.csv", "geo_col": "province",
            "roles": {"province": "geo", "transfers": "numeric", "rate_pct": "numeric"},
        },
        "insights": [], "recommendations": [], "caveats": [], "kpis": [],
    }), encoding="utf-8")

    c = TestClient(app)
    r = c.get("/api/datasets/prov/geo?metric=transfers&agg=median")
    assert r.status_code == 200
    body = r.json()
    assert body["level"] == "province_2025"
    assert len(body["rows"]) <= 34
    by_p = {x["province"]: x for x in body["rows"]}
    assert by_p["Hà Nội"]["value"] == 110.0
    assert by_p["Hồ Chí Minh"]["value"] == 175.0
    assert by_p["Huế"]["value"] == 60.0

    # Ratio column rejects sum
    assert c.get("/api/datasets/prov/geo?metric=rate_pct&agg=sum").status_code == 422
    # Invalid metric
    assert c.get("/api/datasets/prov/geo?metric=missing").status_code == 422

    # Dataset without VN province column returns 422
    out_wdi = tmp_path / "out" / "wdi"
    out_wdi.mkdir(parents=True)
    pd.DataFrame({"country": ["Vietnam", "Thailand"], "gdp": [1.0, 2.0]}).to_parquet(out_wdi / "clean.parquet", index=False)
    (out_wdi / "results.json").write_text(json.dumps({
        "meta": {"id": "wdi", "name": "WDI", "domain": "public_finance", "rows": 2, "target": "gdp", "source_file": "wdi.csv",
                 "roles": {"country": "geo", "gdp": "numeric"}},
        "insights": [], "recommendations": [], "caveats": [], "kpis": [],
    }), encoding="utf-8")
    assert c.get("/api/datasets/wdi/geo").status_code == 422
