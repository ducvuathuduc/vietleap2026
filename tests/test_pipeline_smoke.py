"""End-to-end smoke test on a tiny synthetic, deliberately messy Vietnamese CSV (no charts/PDF: reports=False)."""
import json

import numpy as np
import pandas as pd
import pytest

from vlkit import pipeline
from vlkit.loader import load_and_clean

PROVS = ["TP.HCM", "Hà Nội", "Đà Nẵng", "Tỉnh Bình Dương", "Hai Phong"]
TYPES = ["Nhà riêng", "Căn hộ chung cư", "Nhà mặt phố"]


def _messy_property_csv(path, n=160, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        prov = PROVS[i % len(PROVS)]
        typ = TYPES[i % len(TYPES)]
        area = float(rng.integers(30, 120))
        ppm2 = (60 if "HCM" in prov or "Nội" in prov else 35) + 25 * (typ == "Nhà mặt phố") + rng.normal(0, 5)
        total = area * ppm2 * 1e6
        price = f"{total / 1e9:.2f}".replace(".", ",") + " tỷ" if total >= 1e9 else f"{total / 1e6:.0f} triệu"
        if i % 37 == 0:
            price = "Thỏa thuận"
        month = 1 + i % 12
        rows.append({"Ngày đăng": f"{1 + i % 28:02d}/{month:02d}/2024", "Tỉnh/Thành phố": prov, "Loại hình nhà ở": typ,
                     "Diện tích": f"{area:.0f} m²", "Số phòng ngủ": f"{1 + i % 4} phòng", "Giá": price})
    rows.append(dict(rows[1]))  # one exact duplicate
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


@pytest.fixture(scope="module")
def csv_path(tmp_path_factory):
    return _messy_property_csv(tmp_path_factory.mktemp("data") / "tiny_bds.csv")


def test_loader_cleans(csv_path):
    cr = load_and_clean(csv_path)
    df, roles = cr.df, cr.roles
    assert len(df) == 160  # duplicate removed
    assert pd.api.types.is_datetime64_any_dtype(df["Ngày đăng"])
    assert pd.api.types.is_numeric_dtype(df["Giá"]) and df["Giá"].max() > 1e9
    assert df["Giá"].isna().sum() == len([i for i in range(160) if i % 37 == 0])
    assert pd.api.types.is_numeric_dtype(df["Diện tích"])
    geo = [c for c, r in roles.items() if r == "geo" and c.endswith("__province")]
    assert geo, roles
    assert set(df[geo[0]].dropna()) == {"Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Bình Dương", "Hải Phòng"}
    assert set(df[geo[0] + "_2025"].dropna()) == {"Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Hải Phòng"}
    assert any("duplicate" in m for m in cr.log)


def test_pipeline_runs(csv_path, tmp_path):
    res = pipeline.run(csv_path, out_root=tmp_path, name="smoke", reports=False, domain="property")
    m = res["meta"]
    assert m["domain"] == "property" and m["rows"] == 160
    assert m["target"] in ("Giá", "price_per_m2")
    assert m["time_col"] == "Ngày đăng"
    assert res["insights"], "expected at least one insight"
    for ins in res["insights"]:
        assert {"rank", "type", "score", "sentence_en"} <= set(ins)
    assert res["recommendations"]
    assert len(res["kpis"]) >= 3
    out = tmp_path / "smoke"
    assert (out / "clean.parquet").exists()
    data = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert data["meta"]["name"] == "smoke"


def test_auto_domain_detects_property(csv_path, tmp_path):
    res = pipeline.run(csv_path, out_root=tmp_path, name="auto", reports=False, target="Giá", geo_col="Tỉnh/Thành phố__province")
    assert res["meta"]["domain"] == "property"
    assert res["meta"]["target"] == "Giá"


def test_public_finance_derived_metrics(tmp_path):
    rows = []
    for y in range(2018, 2025):
        for j, p in enumerate(["Hà Nội", "TP.HCM", "Đà Nẵng", "Cần Thơ", "Lào Cai", "Sơn La"]):
            plan = 1000 + 300 * j + 40 * (y - 2018)
            rows.append({"Năm": y, "Tỉnh": p, "Dự toán thu": plan, "Thực hiện thu": plan * (0.9 + 0.03 * j),
                         "Tổng chi": plan * 1.1, "Dân số": 1e6 + 1e5 * j})
    f = tmp_path / "pf.csv"
    pd.DataFrame(rows).to_csv(f, index=False)
    res = pipeline.run(f, out_root=tmp_path, name="pf", reports=False, domain="public_finance")
    assert "budget_execution_rate_pct" in res["meta"]["domain_metrics"]
    assert res["meta"]["target"] == "budget_execution_rate_pct"
    df = pd.read_parquet(tmp_path / "pf" / "clean.parquet")
    assert df["budget_execution_rate_pct"].between(85, 110).all()


def test_firm_aliases_and_financial_sector_driver_sample():
    from vlkit import domains

    df = pd.DataFrame({"LNST (VND)": [10, 20, 12, 15], "VCSH": [100, 100, 100, 100],
                       "ICB Industry": ["Công nghiệp", "Ngân hàng", "Non-life insurance", "Tài chính"]})
    roles = {"LNST (VND)": "numeric", "VCSH": "numeric", "ICB Industry": "category"}
    info = domains.apply_firm(df, roles, [])
    assert df["roe_pct"].tolist() == [10, 20, 12, 15]
    assert info["ingredients"]["roe_pct"] == ["LNST (VND)", "VCSH"]
    assert df.index[info["roe_driver_sample"]].tolist() == [0]


def test_driver_evaluation_does_not_report_a_hypothesis_p_value():
    from vlkit.insights import driver_insights

    rng = np.random.default_rng(7)
    x = rng.uniform(10, 50, size=160)
    frame = pd.DataFrame({"x": x, "y": x * 3 + rng.normal(scale=18, size=len(x))})
    insights, _ = driver_insights(frame, "y", ["x", "y"], [], {})
    assert {item["type"] for item in insights} == {"drivers", "what_if"}
    assert all(item["p_value"] is None for item in insights)
