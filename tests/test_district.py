"""District-level geo: normalisation (Quận/Huyện/Q./TP. prefixes, accent-insensitive key), silver columns,
star dim_geo at district grain, snowflake district → province → province_2025 → region, conformed dim_geo mixing
district- and province-grain sources. Synthetic fixtures (tests only)."""
import pandas as pd
import pytest


@pytest.mark.parametrize("raw,display,key", [
    ("Quận 1", "Quận 1", "quan 1"), ("Q.1", "Quận 1", "quan 1"), ("Q1", "Quận 1", "quan 1"), ("quan 01", "Quận 1", "quan 1"),
    ("Huyện Củ Chi", "Củ Chi", "cu chi"), ("H. Củ Chi", "Củ Chi", "cu chi"), ("Cu Chi", "Cu Chi", "cu chi"),
    ("TP. Thủ Đức", "Thủ Đức", "thu duc"), ("Thành phố Thủ Đức", "Thủ Đức", "thu duc"), ("Q. Bình Thạnh", "Bình Thạnh", "binh thanh"),
    ("Hai Bà Trưng", "Hai Bà Trưng", "hai ba trung"), ("Xuân Lộc", "Xuân Lộc", "xuan loc"), ("Phường 5", "Phường 5", "phuong 5"),
    ("Thị xã Sơn Tây", "Sơn Tây", "son tay"), (7, "Quận 7", "quan 7"),
])
def test_normalize_district(raw, display, key):
    from vlkit.vn import normalize_district
    assert normalize_district(raw) == (display, key)


def test_canonical_display_and_column_detection():
    from vlkit.vn import canonical_districts, is_district_column, normalize_district
    assert normalize_district(None) is None and normalize_district("  ") is None
    disp, key = canonical_districts(pd.Series(["Cu Chi", "Huyện Củ Chi", "Q1", None, "Cu Chi"]))
    assert list(disp[:3]) == ["Củ Chi", "Củ Chi", "Quận 1"] and pd.isna(key[3]) and pd.isna(disp[3])
    assert is_district_column("Quận/Huyện") == "district" and is_district_column("District") == "district"
    assert is_district_column("Phường/Xã") == "ward" and is_district_column("Giá") is None
    assert is_district_column("Khu vực", pd.Series(["Quận 1", "Q.3", "Huyện Nhà Bè", "Quận 7"])) == "district"
    assert is_district_column("Tỉnh/TP", pd.Series(["Hà Nội", "Đà Nẵng"])) is None


@pytest.fixture()
def wh(tmp_path):
    from vlkit.de.warehouse import Warehouse
    w = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    yield w
    w.close()


def _listings(n=40):
    d = ["Quận 1", "Q.1", "Q1", "Huyện Củ Chi", "Cu Chi", "TP. Thủ Đức", "Quận Hoàn Kiếm", "Hoàn Kiếm"]
    p = ["TP HCM", "TP HCM", "Hồ Chí Minh", "TP HCM", "HCM", "TP.HCM", "Hà Nội", "Ha Noi"]
    return pd.DataFrame({"ma": [f"L{i:03d}" for i in range(n)], "quan huyen": [d[i % 8] for i in range(n)],
                         "tinh": [p[i % 8] for i in range(n)], "gia": [10.0 + i for i in range(n)],
                         "loai": ["a", "b"] * (n // 2)})


def test_silver_star_snowflake_district(wh, tmp_path):
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    f = tmp_path / "l.csv"
    _listings().to_csv(f, index=False)
    s = run_flow("dist", [Source("listings", "file", str(f))], out_root=tmp_path / "out", wh=wh)
    sv = wh.sql('SELECT DISTINCT "quan huyen__district" d, "quan huyen__district_key" k FROM silver.dist__listings ORDER BY k')
    assert list(sv.k) == ["cu chi", "hoan kiem", "quan 1", "thu duc"]
    assert list(sv.d) == ["Củ Chi", "Hoàn Kiếm", "Quận 1", "Thủ Đức"]
    assert s["column_plan"]["district"] == "quan huyen__district"
    g = wh.sql("SELECT * FROM gold.dist__dim_geo ORDER BY geo_key")
    assert len(g) == 4 and g.geo_key.is_unique
    assert set(zip(g.district, g.province)) == {("Củ Chi", "Hồ Chí Minh"), ("Quận 1", "Hồ Chí Minh"),
                                                ("Thủ Đức", "Hồ Chí Minh"), ("Hoàn Kiếm", "Hà Nội")}
    assert set(g.region) == {"Đông Nam Bộ", "Đồng bằng sông Hồng"}
    # every fact row resolves to its district row
    orphans = wh.sql("SELECT count(*) n FROM gold.fact_dist f LEFT JOIN gold.dist__dim_geo g USING (geo_key) WHERE g.geo_key IS NULL")
    assert orphans["n"][0] == 0
    # snowflake: district → province → province_2025 → region
    assert "gold.dist__sf_dim_district" in s["models"]["snowflake"]["tables"]
    chain = wh.sql("""SELECT d.district, p.province, p25.province_2025, r.region FROM gold.dist__sf_dim_district d
                      JOIN gold.dist__sf_dim_province p USING (province_key)
                      JOIN gold.dist__sf_dim_province_2025 p25 USING (province_2025_key)
                      JOIN gold.dist__sf_dim_region r USING (region_key) ORDER BY 1""")
    assert len(chain) == 4 and chain.iloc[0].tolist() == ["Củ Chi", "Hồ Chí Minh", "Hồ Chí Minh", "Đông Nam Bộ"]
    assert "SF_DIM_PROVINCE ||--o{ SF_DIM_DISTRICT" in s["models"]["snowflake"]["erd"]
    assert any("district" in t for t in s["models"]["data_vault"]["tables"])


def test_conformed_geo_mixes_district_and_province_sources(wh, tmp_path):
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    f1, f2, f3 = tmp_path / "l.csv", tmp_path / "d.csv", tmp_path / "p.csv"
    _listings().to_csv(f1, index=False)
    # district stats for HCM only, no province column → conform.province
    pd.DataFrame({"Quận": ["Quan 1", "Củ Chi", "Thu Duc", "Quận 3"], "dan so": [1, 2, 3, 4]}).to_csv(f2, index=False)
    pd.DataFrame({"tinh": ["Hồ Chí Minh", "Hà Nội"], "grdp": [100.0, 90.0]}).to_csv(f3, index=False)
    srcs = [Source("listings", "file", str(f1)), Source("dstats", "file", str(f2), conform={"province": "TP HCM"}),
            Source("pstats", "file", str(f3))]
    s = run_flow("mixgeo", srcs, out_root=tmp_path / "out", wh=wh, primary="listings")
    c = s["conformed"]
    g = wh.sql("SELECT * FROM gold.mixgeo__cdim_geo")
    assert g.geo_key.is_unique
    assert set(g[g.geo_level == "province"].province) == {"Hồ Chí Minh", "Hà Nội"}
    assert set(g[g.geo_level == "district"].district_norm) == {"quan 1", "cu chi", "thu duc", "hoan kiem", "quan 3"}
    hk = g[g.district_norm == "hoan kiem"].iloc[0]
    assert hk.province == "Hà Nội" and hk.province_key == g[(g.geo_level == "province") & (g.province == "Hà Nội")].iloc[0].province_key
    joins = {j["source"]: j for j in c["joins"]}
    assert joins["dstats"]["join_on"] == ["geo_key"]            # district ⨝ district
    assert joins["pstats"]["join_on"] == ["province_key"]       # district rows roll up to their province
    assert joins["pstats"]["match_pct"] == 100.0
    # Hoàn Kiếm (Hà Nội) has no district stats → unmatched, reported with its name
    assert joins["dstats"]["unmatched_rows"] == 10 and "Hoàn Kiếm, Hà Nội" in joins["dstats"]["unmatched_samples"]
    v = wh.sql('SELECT DISTINCT _geo_district, dstats__dan_so, pstats__grdp FROM gold.obt_integrated_mixgeo ORDER BY 1')
    assert v[v._geo_district == "Quận 1"].iloc[0].tolist()[1:] == [1, 100.0]
    cov = {x["source"]: x for x in c["sources"]}
    assert cov["dstats"]["geo_level"] == "district" and cov["listings"]["keys"]["geo"]["match_pct"] == 100.0
