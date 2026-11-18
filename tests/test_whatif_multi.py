"""Tests for Feature 007: multi-driver what-if scenarios + API persistence + deck integration."""
import json

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def linear_model():
    from vlkit.models import fit_drivers
    rng = np.random.default_rng(7)
    n = 120
    x1 = rng.normal(100, 15, n)
    x2 = rng.normal(50, 8, n)
    y = 2.0 * x1 - 1.5 * x2 + rng.normal(0, 5, n) + 300
    df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})
    return fit_drivers(df, "y", ["x1", "x2"], n_boot=60)


def test_whatif_multi_matches_single_and_aligned_bootstrap(linear_model):
    from vlkit.models import what_if, what_if_multi

    s1 = what_if(linear_model, "x1", 10.0)
    m1 = what_if_multi(linear_model, [{"feature": "x1", "pct_change": 10.0}])
    assert abs(m1["target_change_pct"] - s1["target_change_pct"]) < 1e-9
    assert abs(m1["ci90_pct"][0] - s1["ci90_pct"][0]) < 1e-9
    assert abs(m1["ci90_pct"][1] - s1["ci90_pct"][1]) < 1e-9

    m2 = what_if_multi(linear_model, [{"feature": "x1", "pct_change": 10.0}, {"feature": "x2", "pct_change": -10.0}])
    assert len(m2["contributions"]) == 2
    assert m2["ci90_pct"][0] <= m2["target_change_pct"] <= m2["ci90_pct"][1]


def test_whatif_multi_zero_vector_duplicate_and_range_warning(linear_model):
    from vlkit.models import what_if_multi

    zero = what_if_multi(linear_model, [{"feature": "x1", "pct_change": 0.0}])
    assert zero["target_change_pct"] == 0.0
    assert zero["ci90_pct"] == [0.0, 0.0]

    with pytest.raises(ValueError):
        what_if_multi(linear_model, [{"feature": "x1", "pct_change": 5.0}, {"feature": "x1", "pct_change": -5.0}])

    with pytest.raises(ValueError):
        what_if_multi(linear_model, [{"feature": "x1", "pct_change": 35.0}])


def test_whatif_multi_log_target():
    from vlkit.models import fit_drivers, what_if, what_if_multi
    rng = np.random.default_rng(11)
    x1 = rng.normal(50, 5, 100)
    x2 = rng.normal(20, 3, 100)
    y = np.exp(0.05 * x1 + 0.02 * x2 + rng.normal(0, 0.2, 100)) * 10
    df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})
    model = fit_drivers(df, "y", ["x1", "x2"], n_boot=40)
    assert model["log_target"] is True
    s1 = what_if(model, "x1", 5.0)
    m1 = what_if_multi(model, [{"feature": "x1", "pct_change": 5.0}])
    assert abs(m1["target_change_pct"] - s1["target_change_pct"]) < 1e-9


def test_api_whatif_scenario_and_saved_cap(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("KIT_OUT_DIR", str(tmp_path / "out"))
    from api.main import app
    from vlkit.models import fit_drivers

    out_ds = tmp_path / "out" / "demo"
    out_ds.mkdir(parents=True)
    rng = np.random.default_rng(3)
    df = pd.DataFrame({
        "x1": rng.normal(100, 10, 60),
        "x2": rng.normal(40, 5, 60),
        "y": rng.normal(500, 40, 60),
    })
    df.to_parquet(out_ds / "clean.parquet", index=False)
    model = fit_drivers(df, "y", ["x1", "x2"], n_boot=30)
    (out_ds / "whatif.json").write_text(json.dumps(model["whatif"]), encoding="utf-8")
    (out_ds / "results.json").write_text(json.dumps({
        "meta": {"id": "demo", "name": "Demo", "domain": "auto", "rows": 60, "target": "y", "source_file": "demo.csv",
                 "roles": {"x1": "numeric", "x2": "numeric", "y": "numeric"}},
        "drivers": model,
    }), encoding="utf-8")

    c = TestClient(app)
    r = c.post("/api/datasets/demo/whatif/scenario", json={"changes": [{"feature": "x1", "pct_change": 10}]})
    assert r.status_code == 200
    assert c.post("/api/datasets/demo/whatif/scenario", json={"changes": [{"feature": "x1", "pct_change": 50}]}).status_code == 422
    assert c.post("/api/datasets/missing/whatif/scenario", json={"changes": [{"feature": "x1", "pct_change": 10}]}).status_code == 404

    for i in range(4):
        sr = c.post("/api/datasets/demo/whatif/scenarios", json={
            "name": f"Kịch bản {i + 1}",
            "request": {"changes": [{"feature": "x1", "pct_change": 5 + i}]},
        })
        assert sr.status_code == 200
    assert len(c.get("/api/datasets/demo/whatif/scenarios").json()) == 4
    r5 = c.post("/api/datasets/demo/whatif/scenarios", json={
        "name": "Kịch bản 5",
        "request": {"changes": [{"feature": "x1", "pct_change": 15}]},
    })
    assert r5.status_code == 409
