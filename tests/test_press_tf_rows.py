from __future__ import annotations

import pandas as pd

from engine.vlkit.de.warehouse import Warehouse
from engine.vlkit.monitor.ingest import land_source, normalize_long
from tools.press import tf_rows
from tools.press.run import load_targets


def test_to_number_handles_vn_and_en_formats():
    assert tf_rows.to_number("2.438,9", "vn") == 2438.9
    assert tf_rows.to_number("2,438.9", "en") == 2438.9
    assert tf_rows.to_number("+19,7%", "vn") == 19.7
    assert tf_rows.to_number("-71%", "vn") == -71
    assert tf_rows.to_number("1.809", "vn") == 1809
    assert tf_rows.to_number("n/a", "vn") is None


def test_period_and_date_normalisation():
    assert tf_rows.normalize_period("2026-Q3") == "2026-Q3"
    assert tf_rows.normalize_period("10M/2026") == "2026-10"
    assert tf_rows.normalize_period("tháng 10/2026") == "2026-10"
    assert tf_rows.normalize_period(None, "2026-Q3") == "2026-Q3"
    assert tf_rows.normalize_date("04/11/2026") == "2026-11-04"
    assert tf_rows.normalize_date("2026-11-04") == "2026-11-04"


def test_rows_from_records_maps_fields_lists_and_evidence():
    target = {
        "source_id": "nhadautu", "url": "https://example/fdi", "published_date": "2026-11-04",
        "period": "2026-10", "decimal": "vn", "geo": "VNM",
        "fields": [
            {"field": "registered", "indicator_id": "fdi_registered", "measure_type": "level", "unit": "bn_usd"},
        ],
        "lists": [{
            "list_field": "provinces", "geo_field": "name",
            "fields": [{"field": "amount", "indicator_id": "fdi_province", "measure_type": "level", "unit": "bn_usd"}],
        }],
    }
    records = [{"registered": 54.85, "provinces": [{"name": "TP.HCM", "amount": 20.14}]}]
    text = "Vốn đăng ký 54,85 tỷ USD. TP.HCM 20,14 tỷ USD."
    rows = tf_rows.rows_from_records(records, target, text)
    assert len(rows) == 2
    reg = next(r for r in rows if r["indicator_id"] == "fdi_registered")
    assert reg["value"] == "54.85" and reg["evidence_ok"] == "true"
    hcm = next(r for r in rows if r["indicator_id"] == "fdi_province")
    assert hcm["geo"] == "TP.HCM" and hcm["value"] == "20.14"
    assert "TP.HCM 20,14" in hcm["evidence"]


def test_rows_from_records_flags_missing_evidence():
    target = {"source_id": "s", "url": "u", "period": "2026-Q3", "decimal": "vn",
              "fields": [{"field": "x", "indicator_id": "x", "measure_type": "level", "unit": "%"}]}
    rows = tf_rows.rows_from_records([{"x": 99.9}], target, "không có số này")
    assert rows[0]["evidence_ok"] == "false"


def test_list_rows_inherit_the_article_date():
    target = {
        "source_id": "s", "url": "u", "period": "2026-10", "decimal": "vn",
        "published_date_field": "pub",
        "fields": [{"field": "x", "indicator_id": "x", "measure_type": "level", "unit": "%"}],
        "lists": [{"list_field": "items", "geo_field": "name",
                   "fields": [{"field": "v", "indicator_id": "v", "measure_type": "level", "unit": "%"}]}],
    }
    records = [{"x": 1, "pub": "04/11/2026", "items": [{"name": "A", "v": 2}]}]
    rows = tf_rows.rows_from_records(records, target, "1% và 2%")
    assert [r["published_date"] for r in rows] == ["2026-11-04", "2026-11-04"]


def test_slug_field_keeps_partner_names_distinct():
    target = {"source_id": "s", "url": "u", "period": "2026-10", "decimal": "vn",
              "fields": [], "lists": [{"list_field": "partners", "fields": [
                  {"field": "v", "indicator_id": "fdi_partner", "measure_type": "level", "unit": "bn_usd",
                   "geo": "VNM", "slug_field": "name"}]}]}
    records = [{"partners": [{"name": "Hàn Quốc", "v": 10}, {"name": "Singapore", "v": 13.46}]}]
    rows = tf_rows.rows_from_records(records, target, "Hàn Quốc 10 tỷ USD; Singapore 13,46 tỷ USD")
    assert [r["indicator_id"] for r in rows] == ["fdi_partner_han_quoc", "fdi_partner_singapore"]


def test_rows_from_text_regex_recipe():
    target = {"source_id": "s", "url": "u", "period": "2026-10", "decimal": "vn", "geo": "VNM",
              "text_fields": [{"pattern": r"đạt ([\d.,]+) điểm", "indicator_id": "score",
                               "measure_type": "level", "unit": "points", "geo": "Điện Biên"}]}
    rows = tf_rows.rows_from_text("Điện Biên đứng đầu và đạt 100 điểm.", target)
    assert len(rows) == 1
    assert rows[0]["value"] == "100" and rows[0]["geo"] == "Điện Biên"
    assert rows[0]["evidence_ok"] == "true"


def test_negative_value_matches_a_printed_decrease():
    target = {"source_id": "s", "url": "u", "period": "2026-Q3", "decimal": "vn",
              "fields": [{"field": "x", "indicator_id": "x", "measure_type": "yoy", "unit": "%"}]}
    rows = tf_rows.rows_from_records([{"x": -71}], target, "Số căn bán được giảm 71% so với cùng kỳ.")
    assert rows[0]["evidence_ok"] == "true"
    assert "giảm 71%" in rows[0]["evidence"]


def test_evidence_snippet_includes_amount_beyond_first_400_characters():
    text = "Giới thiệu dự án. " * 30 + "Vốn đăng ký đạt 54,85 tỷ USD."
    assert "54,85" in tf_rows.find_snippet(text, 54.85)


def test_realtique_segment_table_retains_city_and_signed_cell_evidence():
    target = next(t for t in load_targets() if t["source_id"] == "realtique_cbre_hcm_q3_2026")
    text = (
        "| Quý 3/2026 | Căn hộ Hà Nội\\* | Căn hộ TP.HCM\\*\\* | Liền thổ Hà Nội\\* | Liền thổ TP.HCM\\*\\* |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Nguồn cung mới | 6.187 căn (−40%) | **3.267 căn (−50%)** | 1.517 căn (+144%) | 30 căn (−92%) |\n"
    )
    rows = tf_rows.rows_from_text(text, target)
    supply = next(r for r in rows if r["geo"] == "TP.HCM" and r["indicator_id"] == "apartment_new_supply"
                  and r["measure_type"] == "level")
    assert (supply["value"], supply["evidence"], supply["evidence_ok"]) == ("3267", "**3.267 căn (−50%)**", "true")
    assert {(r["geo"], r["value"]) for r in rows if r["indicator_id"] == "landed_home_new_supply"
            and r["measure_type"] == "yoy"} == {("Hà Nội", "144"), ("TP.HCM", "-92")}


def test_monitor_accepts_press_ids_and_legacy_geography():
    raw = pd.DataFrame([
        ("apartment_new_supply", "level", "TP.HCM", "can"),
        ("mortgage_rate", "level", "TP.HCM", "%"),
        ("fdi_province", "level", "Thái Nguyên", "bn_usd"),
        ("fdi_partner", "level", "Singapore", "bn_usd"),
        ("bank_sector_deposits_ytd", "ytd", "VNM", "%"),
        ("bank_npl_coverage", "ratio", "ACB", "%"),
    ], columns=["indicator_id", "measure_type", "geo", "unit"])
    raw["period"] = ["2026-Q3", "2026-Q3", "2026-10", "2026-10", "2026-Q3", "2026-Q3"]
    rows = normalize_long(raw, "press", "run")
    assert list(zip(rows.indicator_id, rows.measure_type, rows.geo_type)) == [
        ("re_new_supply", "level", "city"),
        ("mortgage_rate", "level", "city"),
        ("fdi_dang_ky", "ytd", "province"),
        ("fdi_dang_ky", "ytd", "partner"),
        ("deposit_ytd", "ytd", "national"),
        ("bank_coverage", "ratio", "ticker"),
    ]
    assert rows.iloc[4].period == "2026-09"
    assert rows.iloc[0].unit == "căn"


def test_monitor_preserves_margin_debt_as_a_convertible_currency_unit():
    raw = pd.DataFrame([{"indicator_id": "margin_debt", "measure_type": "level", "geo": "VNM",
                         "unit": "nghin_ty_vnd", "value": "457.5"}])
    row = normalize_long(raw, "press", "run").iloc[0]
    assert (row.unit, row.value) == ("nghìn tỷ đồng", "457.5")


def test_monitor_derives_catalog_absorption_from_verified_matching_counts():
    raw = pd.DataFrame([
        ("apartment_absorption", "TP.HCM", "1809", "can", "1.809 căn", True),
        ("apartment_new_supply", "TP.HCM", "3267", "can", "3.267 căn", True),
        ("mortgage_rate", "TP.HCM", "10.6", "%", "10,6%", True),
        ("apartment_absorption", "Hà Nội", "3920", "can", "3.920 căn", True),
        ("apartment_new_supply", "Hà Nội", "6187", "can", "6.187 căn", True),
    ], columns=["indicator_id", "geo", "value", "unit", "evidence", "evidence_ok"])
    raw = raw.assign(measure_type="level", period="2026-Q3", source_id="realtique_cbre_hcm_q3_2026")

    rows = normalize_long(raw, "press", "run")
    ratio, = rows.loc[rows.indicator_id.eq("re_absorption")].itertuples()
    assert (ratio.geo, ratio.unit, ratio.evidence) == ("TP.HCM", "%", "1.809 căn | 3.267 căn")
    assert abs(ratio.value - 55.37190082644628) < 0.001
    assert rows.loc[rows.indicator_id.eq("apartment_absorption"), "value"].tolist() == ["1809", "3920"]
    rate = rows.loc[rows.indicator_id.eq("mortgage_rate")].iloc[0]
    assert (rate.geo, rate.geo_type) == ("VNM", "national")


def test_revised_press_snapshot_replaces_existing_bronze_rows(tmp_path):
    warehouse = Warehouse(tmp_path / "warehouse.duckdb", tmp_path / "lake")
    path = tmp_path / "press_long.csv"
    provenance = {"source": "press", "kind": "file", "fetched_at": "2026-11-19T16:00:00+07:00"}
    try:
        for value in [1, 2]:
            path.write_text(f"value\n{value}\n", encoding="utf-8")
            land_source(warehouse, "press", path, provenance, "run", frame=pd.read_csv(path))
        assert warehouse.con.execute("SELECT value FROM bronze.press").fetchall() == [(2,)]
    finally:
        warehouse.close()
