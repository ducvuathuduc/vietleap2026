"""Conformed dimensions across sources: shared dim_geo/dim_date/dim_year/dim_<key>, conformed facts, integrated OBT,
join-coverage diagnostics, lineage, ERD. Fixtures are synthetic (tests only)."""
import json
import sqlite3

import pandas as pd
import pytest


@pytest.fixture()
def wh(tmp_path):
    from vlkit.de.warehouse import Warehouse
    w = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    yield w
    w.close()


def _csv(tmp_path, name, df):
    p = tmp_path / f"{name}.csv"
    df.to_csv(p, index=False)
    return str(p)


@pytest.fixture()
def province_sources(tmp_path):
    from vlkit.de.conformed import new_province_names
    from vlkit.de.sources import Source
    provs = ["Hà Nội", "TP HCM", "Bình Dương", "Đà Nẵng", "Ha Noi", "Hà Giang"] * 5
    listings = pd.DataFrame({"ma tin": [f"T{i:03d}" for i in range(len(provs))], "tinh": provs,
                             "ngay dang": [f"{1 + i % 27:02d}/0{1 + i % 9}/202{3 + i % 2}" for i in range(len(provs))],
                             "gia": [1.0 + i for i in range(len(provs))]})
    new34 = sorted(new_province_names())
    units = pd.DataFrame({"tinh thanh": new34, "dan so": [1000 + 10 * i for i in range(len(new34))]})
    years = pd.DataFrame({"nam": [2022, 2023, 2024], "gdp": [10.0, 11.0, 12.0]})
    return [Source("listings", "file", _csv(tmp_path, "listings", listings)),
            Source("units34", "file", _csv(tmp_path, "units34", units)),
            Source("macro", "file", _csv(tmp_path, "macro", years))]


def test_conformed_dims_and_integrated_obt(wh, province_sources, tmp_path):
    from vlkit.de.flow import run_flow
    s = run_flow("conf", province_sources, out_root=tmp_path / "out", wh=wh, primary="listings")
    c = s["conformed"]
    assert c and {"geo", "year"} <= set(c["shared_keys"])
    assert set(c["dims"]) >= {"geo", "year"}
    # conformed dim_geo: one row per normalised province, surrogate key, 63→34 + region
    g = wh.sql("SELECT * FROM gold.conf__cdim_geo")
    assert g["geo_key"].is_unique and g["province"].is_unique
    row = g[g.province == "Bình Dương"].iloc[0]
    assert row.province_2025 == "Hồ Chí Minh" and row.region == "Đông Nam Bộ"
    assert g[g.province == "Hà Giang"].iloc[0].province_2025 == "Tuyên Quang"
    # integrated OBT keeps the primary grain (no row explosion)
    n = wh.sql("SELECT count(*) n FROM gold.obt_integrated_conf")["n"][0]
    assert n == s["quality"]["silver.conf__listings"]["rows"] == c["base_rows"] and not c["row_explosion"]
    joins = {j["source"]: j for j in c["joins"]}
    # 34-unit list is detected as post-merger grain → joined on province_2025_key; Bình Dương picks up HCM's row
    assert joins["units34"]["join_on"] == ["province_2025_key"] and joins["units34"]["status"] == "joined"
    assert joins["units34"]["match_pct"] == 100.0
    bd = wh.sql("SELECT DISTINCT units34__dan_so FROM gold.obt_integrated_conf WHERE _geo_province = 'Bình Dương'")
    hcm = wh.sql("SELECT \"dan so\" FROM silver.conf__units34 WHERE \"tinh thanh__province\" = 'Hồ Chí Minh'")
    assert bd.iloc[0, 0] == hcm.iloc[0, 0]
    # year join: listings from 2023/2024 match the macro table, coverage counted, nothing unmatched
    assert joins["macro"]["join_on"] == ["year_key"] and joins["macro"]["matched_rows"] == n
    # per-source dimension coverage
    cov = {x["source"]: x for x in c["sources"]}
    assert cov["listings"]["keys"]["geo"]["match_pct"] == 100.0
    assert cov["listings"]["keys"]["year"]["column"] == "ngay dang"
    assert cov["units34"]["geo_level"] == "2025"
    # meta.join_coverage, outputs, lineage edges, ERD
    jc = wh.sql("SELECT kind, count(*) n FROM meta.join_coverage WHERE dataset='conf' GROUP BY 1")
    assert set(jc["kind"]) == {"dimension", "integration"}
    out = tmp_path / "out/conf"
    assert json.loads((out / "conformed.json").read_text())["integrated"] == "gold.obt_integrated_conf"
    lin = json.loads((out / "lineage.json").read_text())
    steps = {e["step"] for e in lin["edges"]}
    assert {"conform", "fk", "integrate"} <= steps
    assert lin["join_coverage"]["joins"]
    erd = s["models"]["conformed"]["erd"]
    assert "CDIM_GEO ||--o{ CFACT_LISTINGS" in erd and "CDIM_YEAR ||--o{" in erd
    assert (out / "models/conformed.sql").exists()


def test_grain_mismatch_where_and_agg(wh, tmp_path):
    from vlkit.de.conformed import build_conformed
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    base = pd.DataFrame({"nam": [2020, 2021, 2022, 2023] * 3, "x": range(12), "loai": list("abc") * 4})
    panel = pd.DataFrame({"year": [2020, 2021, 2022, 2023] * 2, "iso3": ["VNM"] * 4 + ["THA"] * 4,
                          "gdp": [1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0]})
    srcs = [Source("base", "file", _csv(tmp_path, "base", base)), Source("panel", "file", _csv(tmp_path, "panel", panel))]
    s = run_flow("g1", srcs, out_root=tmp_path / "out", wh=wh, primary="base")
    j = s["conformed"]["joins"][0]
    assert j["status"] == "grain_mismatch" and j["rows_per_key"] == 2.0 and "conform" in j["hint"]
    # where → one row per year
    srcs[1].conform = {"where": "iso3 = 'VNM'"}
    s = run_flow("g2", srcs, out_root=tmp_path / "out", wh=wh, primary="base")
    j = s["conformed"]["joins"][0]
    assert j["status"] == "joined" and j["match_pct"] == 100.0
    assert sorted(wh.sql("SELECT DISTINCT panel__gdp FROM gold.obt_integrated_g2")["panel__gdp"]) == [1.0, 2.0, 3.0, 4.0]
    # agg → mean across countries, explicitly requested
    srcs[1].conform = {"agg": "mean"}
    s = run_flow("g3", srcs, out_root=tmp_path / "out", wh=wh, primary="base")
    j = s["conformed"]["joins"][0]
    assert j["status"] == "joined" and j["aggregated"] == "avg"
    assert sorted(wh.sql("SELECT DISTINCT panel__gdp FROM gold.obt_integrated_g3")["panel__gdp"]) == [5.5, 11.0, 16.5, 22.0]
    assert wh.sql("SELECT count(*) n FROM gold.obt_integrated_g3")["n"][0] == 12
    # where must be a plain predicate
    with pytest.raises(PermissionError):
        build_conformed(wh, "g3", ["silver.g3__base", "silver.g3__panel"], {}, "silver.g3__base",
                        conform_of={"silver.g3__panel": {"where": "1=1; DROP TABLE gold.obt_g3"}})
    srcs[1].conform = {"where": "1=1; DROP TABLE x"}
    s = run_flow("g4", srcs, out_root=tmp_path / "out", wh=wh, primary="base")
    assert any(x["step"] == "conform" and x["status"] == "failed" for x in s["steps"])
    assert s["models"]["obt"]["tables"]          # single-source models survive a failed integration


def test_same_schema_sheets_are_stacked_and_ticker_dim(wh, tmp_path):
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    p = tmp_path / "firms.xlsx"
    with pd.ExcelWriter(p) as xw:
        for q, n in (("Q1", 5), ("Q2", 4)):
            pd.DataFrame({"Mã CK": ["AAA", "BBB", "CCC", "DDD", "EEE"][:n], "Kỳ báo cáo": [f"01/0{1 if q == 'Q1' else 4}/2021"] * n,
                          "Doanh thu": [100.0 * i for i in range(n)]}).to_excel(xw, sheet_name=q, index=False)
    s = run_flow("firms", [Source("firms", "file", str(p))], out_root=tmp_path / "out", wh=wh)
    c = s["conformed"]
    assert "ticker" in c["shared_keys"] and c["integrated_rows"] == 9 and len(c["base"]) == 2 and not c["joins"]
    t = wh.sql("SELECT * FROM gold.firms__cdim_ticker ORDER BY ticker")
    assert list(t.ticker) == ["AAA", "BBB", "CCC", "DDD", "EEE"] and t.ticker_key.is_unique
    assert dict(zip(t.ticker, t.n_sources))["AAA"] == 2 and dict(zip(t.ticker, t.n_sources))["EEE"] == 1
    ov = [o for o in c["overlap"] if o["key"] == "ticker"][0]
    assert ov["shared_keys"] == 4
    d = wh.sql("SELECT min(date) lo, max(date) hi FROM gold.firms__cdim_date")
    assert str(d.lo[0])[:10] == "2021-01-01" and str(d.hi[0])[:10] == "2021-04-01"


def test_yaml_keys_custom_dim_and_no_shared_key(wh, tmp_path):
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    a = pd.DataFrame({"ma_sp": ["x1", "x2", "x3", "x1"], "ban": [1, 2, 3, 4]})
    b = pd.DataFrame({"product code": ["X1", "x2 ", "x9"], "gia": [10.0, 20.0, 30.0]})
    srcs = [Source("sales", "file", _csv(tmp_path, "sales", a)), Source("prices", "file", _csv(tmp_path, "prices", b))]
    s = run_flow("sku", srcs, out_root=tmp_path / "out", wh=wh, primary="sales",
                 keys={"sku": ["ma_sp", "product code"]})
    c = s["conformed"]
    assert c["shared_keys"] == ["sku"]
    assert sorted(wh.sql("SELECT sku FROM gold.sku__cdim_sku")["sku"]) == ["X1", "X2", "X3", "X9"]
    j = c["joins"][0]
    assert j["matched_rows"] == 3 and j["unmatched_rows"] == 1 and j["unmatched_samples"]
    # no shared key → no conformed layer, nothing breaks
    c2 = pd.DataFrame({"foo": ["a", "b"], "bar": [1, 2]})
    srcs2 = [Source("one", "file", _csv(tmp_path, "one", c2)), Source("two", "file", _csv(tmp_path, "two", c2.rename(columns={"foo": "baz"})))]
    s2 = run_flow("nokey", srcs2, out_root=tmp_path / "out", wh=wh, primary="one")
    assert s2["conformed"] is None and "conformed" not in s2["models"]
    assert not (tmp_path / "out/nokey/conformed.json").exists()


def test_demo_scenario_offline(wh, tmp_path, kit_root):
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import load_sources
    ds, srcs, keys = load_sources(kit_root / "scenarios/conformed/sources.yaml")
    assert srcs[1].conform == {"where": "iso3 = 'VNM'"} and "province" in keys
    s = run_flow(ds, srcs, out_root=tmp_path / "out", wh=wh, primary="vn_housing", keys=keys)
    j = s["conformed"]["joins"][0]
    assert j["source"] == "wdi_panel" and j["status"] == "joined" and j["keys"] == ["year"]
    assert 0 < j["matched_rows"] <= s["conformed"]["integrated_rows"]
    # every matched row carries the real WDI value of its year (Viet Nam)
    chk = wh.sql("""SELECT count(*) n FROM gold.obt_integrated_conformed_vn o JOIN silver.conformed_vn__wdi_panel w
                    ON w.iso3 = 'VNM' AND w.year = o.year_key WHERE o.wdi_panel__gdp_per_capita_usd IS DISTINCT FROM w.gdp_per_capita_usd""")
    assert chk["n"][0] == 0


def test_sqlite_and_file_share_province(wh, tmp_path, kit_root):
    """Two different connector kinds, same province key → one conformed geo dimension."""
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    db = tmp_path / "b.sqlite"
    con = sqlite3.connect(db)
    pd.DataFrame({"tinh": ["Hà Nội", "TP Hồ Chí Minh", "Đà Nẵng", "Cần Thơ", "Hải Phòng", "Bình Dương"],
                  "chi": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]}).to_sql("t", con, index=False)
    con.close()
    srcs = [Source("bds", "file", str(kit_root / "data/practice/synthetic_messy_bds.csv")),
            Source("budget", "sql", f"sqlite:///{db}", {"query": "SELECT * FROM t"})]
    s = run_flow("mix", srcs, out_root=tmp_path / "out", wh=wh, primary="bds")
    j = s["conformed"]["joins"][0]
    assert j["join_on"] == ["geo_key"] and j["match_pct"] == 100.0
    assert s["conformed"]["integrated_rows"] == s["conformed"]["base_rows"]
