"""T8: brief parser picks the right target for the practice datasets and the right scenario pack for every sample brief."""
import pytest

from vlkit.brief import load_packs, parse_brief, split_sentences

BDS = ['Mã tin', 'Ngày đăng', 'Tỉnh/TP', 'Loại BĐS', 'Diện tích', 'Giá bán', 'Giá thuê/tháng', 'Thu nhập hộ/tháng', 'Ghi chú', 'Pháp lý']
FIRMS = ['Mã CK', 'Kỳ báo cáo', 'Doanh thu thuần', 'Giá vốn hàng bán', 'Lợi nhuận gộp', 'Chi phí bán hàng', 'Chi phí quản lý DN',
         'Chi phí lãi vay', 'Lợi nhuận sau thuế', 'Tổng cộng tài sản', 'Nợ phải trả', 'Vốn chủ sở hữu', 'Hàng tồn kho',
         'Tiền và tương đương tiền', 'Ngành', 'Sàn']
WDI = ['country', 'iso3', 'year', 'gdp_per_capita_usd', 'gdp_growth_pct', 'revenue_pct_gdp', 'tax_revenue_pct_gdp', 'expense_pct_gdp',
       'net_lending_pct_gdp', 'central_gov_debt_pct_gdp', 'population', 'urban_pop_pct', 'inflation_pct', 'fdi_inflow_pct_gdp',
       'education_spend_pct_gdp']

PRACTICE = [
    ("bds_gia_m2.md", BDS, "price_per_m2", "data_economy_property"),
    ("bds_gia_thue.md", BDS, "Giá thuê/tháng", "data_economy_property"),
    ("firms_roe.md", FIRMS, "roe_pct", "listed_firms_market"),
    ("wdi_tax_revenue.md", WDI, "tax_revenue_pct_gdp", "development_indicators"),
    ("wdi_no_cong.md", WDI, "central_gov_debt_pct_gdp", None),
]
PACK_BRIEFS = {
    "ngan_sach_tinh.md": "public_finance_province",
    "chinh_sach_luong.md": "economic_policy",
    "du_lieu_mo_bds.md": "data_economy_property",
    "chi_so_phat_trien.md": "development_indicators",
    "tac_dong_xa_hoi.md": "social_impact",
    "dem_xe_giao_thong.md": "cv_observation",
    "firms_roe.md": "listed_firms_market",
}


def _read(kit_root, name):
    return (kit_root / "scenarios" / "briefs" / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name,cols,target,pack", PRACTICE)
def test_practice_brief_target(kit_root, name, cols, target, pack):
    b = parse_brief(_read(kit_root, name), columns=cols)
    assert b["target"]["column"] == target, b["target"]
    assert b["run_config"]["target"] == target
    if pack:
        assert b["pack"]["id"] == pack, b["pack_scores"]
    assert b["questions"], "questions extracted"
    assert b["plan"][0].startswith("Biến mục tiêu")


@pytest.mark.parametrize("name,pack", PACK_BRIEFS.items())
def test_pack_detection(kit_root, name, pack):
    b = parse_brief(_read(kit_root, name))
    assert b["pack"]["id"] == pack, b["pack_scores"]
    assert b["pack"]["recipe"] and b["pack"]["decision_template"]["kpi"]


def test_language_units_years_and_segments(kit_root):
    b = parse_brief(_read(kit_root, "bds_gia_m2.md"), columns=BDS)
    assert b["language"] == "vi"
    assert "province" in b["units"]
    assert "Loại BĐS" in b["segments"]
    assert {"dashboard", "data_pipeline", "recommendation"} <= set(b["deliverables"])
    f = parse_brief(_read(kit_root, "firms_roe.md"), columns=FIRMS)
    assert {"Sàn", "Ngành"} <= set(f["segments"]) and "district" not in f["units"]
    e = parse_brief(_read(kit_root, "wdi_tax_revenue.md"), columns=WDI)
    assert e["language"] == "en" and e["time"]["range"] == [2010, 2024]


def test_no_columns_still_returns_concept():
    b = parse_brief("Hãy phân tích ROE của các doanh nghiệp niêm yết theo ngành?")
    assert b["target"]["concept"] == "roe" and b["target"]["column"] == "roe_pct"


def test_unknown_target_warns_and_empty_rejected():
    b = parse_brief("Hãy phân tích dữ liệu này.", columns=["a", "b"])
    assert b["target"] is None and b["warnings"]
    with pytest.raises(ValueError):
        parse_brief("   ")


def test_packs_are_complete(kit_root):
    packs = load_packs()
    assert len(packs) >= 7
    for p in packs:
        for key in ("id", "title", "sponsor", "domain", "keywords", "expected_columns", "kpis", "recipe", "decision_template", "deck_storyline"):
            assert p.get(key), (p.get("id"), key)
        assert {"who", "what", "where", "kpi", "caveat"} <= set(p["decision_template"])


def test_split_sentences_handles_markdown_lists():
    s = split_sentences("# Tiêu đề\n- Ý một.\n- Ý hai? Câu ba.")
    assert "Ý hai?" in s and "Tiêu đề" in s


def test_brief_api(tmp_path, monkeypatch, kit_root):
    import json
    from fastapi.testclient import TestClient
    out = tmp_path / "out"
    (out / "bds").mkdir(parents=True)
    (out / "bds" / "results.json").write_text(json.dumps({"meta": {"roles": {c: "x" for c in BDS + ["price_per_m2"]}}}), encoding="utf-8")
    monkeypatch.setenv("KIT_OUT_DIR", str(out))
    from api.main import app
    c = TestClient(app)
    r = c.post("/api/brief", json={"text": _read(kit_root, "bds_gia_m2.md"), "dataset": "bds"})
    assert r.status_code == 200 and r.json()["target"]["column"] == "price_per_m2"
    assert (out / "bds" / "brief.json").exists()
    assert c.post("/api/brief", json={"text": "short"}).status_code == 422
    assert c.post("/api/brief", json={"text": "Hãy phân tích dữ liệu", "dataset": "nope"}).status_code == 404
    assert c.post("/api/brief", json={"text": "Hãy phân tích dữ liệu", "dataset": "../etc"}).status_code == 422
    assert len(c.get("/api/brief/packs").json()) >= 7
    names = {x["name"] for x in c.get("/api/brief/samples").json()}
    assert {"bds_gia_m2", "ngan_sach_tinh"} <= names and "README" not in names
