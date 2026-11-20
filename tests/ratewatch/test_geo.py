"""CONTRACT D geography (M1): ray-casting point-in-polygon, OSM bank matching, gold builder on a tiny fixture."""
import json
from pathlib import Path

import pytest

from vlkit.ratewatch.geo import (
    assign_province,
    build_geo,
    collect_overpass,
    latest_overpass,
    load_provinces,
    match_bank,
    normalise_name,
    point_in_multipolygon,
    point_in_ring,
    write_gold,
)
from vlkit.ratewatch.geo.banks_match import alias_map
from vlkit.ratewatch.ingest.bronze import BronzeStore

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ratewatch" / "geo"


@pytest.fixture(scope="module")
def provinces():
    return load_provinces(FIXTURES / "mini.geojson")


@pytest.fixture(scope="module")
def aliases():
    from vlkit.ratewatch.ingest.banks import load_banks

    return alias_map(load_banks(FIXTURES / "mini_banks.yaml"))


def test_point_in_ring_square():
    ring = [[1.0, 10.0], [2.0, 10.0], [2.0, 11.0], [1.0, 11.0], [1.0, 10.0]]
    assert point_in_ring(1.5, 10.5, ring)
    assert point_in_ring(1.0, 10.0, ring)  # vertex counts as inside
    assert not point_in_ring(2.5, 10.5, ring)
    assert not point_in_ring(1.5, 9.5, ring)


def test_point_in_multipolygon_respects_holes():
    square_with_hole = [
        [[1.0, 10.0], [2.0, 10.0], [2.0, 11.0], [1.0, 11.0], [1.0, 10.0]],
        [[1.4, 10.4], [1.6, 10.4], [1.6, 10.6], [1.4, 10.6], [1.4, 10.4]],
    ]
    second_square = [[[2.0, 10.0], [3.0, 10.0], [3.0, 11.0], [2.0, 11.0], [2.0, 10.0]]]
    assert point_in_multipolygon(1.2, 10.2, [square_with_hole])
    assert not point_in_multipolygon(1.5, 10.5, [square_with_hole])  # inside the hole
    assert point_in_multipolygon(2.5, 10.5, [square_with_hole, second_square])


def test_assign_province(provinces):
    assert assign_province(1.2, 10.2, provinces) == "VN00"
    assert assign_province(2.5, 10.5, provinces) == "VN01"
    assert assign_province(1.5, 10.5, provinces) is None  # the hole
    assert assign_province(5.0, 5.0, provinces) is None  # far outside


def test_normalise_name_strips_generic_words_and_d_with_stroke():
    assert normalise_name("Ngân hàng TMCP Ngoại thương Việt Nam") == "ngoai thuong viet nam"
    assert normalise_name("Đồng Nai") == "dong nai"
    assert normalise_name("Vietcombank (Vietnam)") == "vietcombank vietnam"


def test_match_bank(aliases):
    assert match_bank({"brand": "Vietcombank"}, aliases) == "VCB"
    assert match_bank({"name": "Ngân hàng TMCP Ngoại thương Việt Nam"}, aliases) == "VCB"
    assert match_bank({"brand": "Techcombank", "operator": "Techcombank"}, aliases) == "TCB"
    assert match_bank({"brand": "VPBank"}, aliases) == "VPB"  # OSM spelling, not in banks.yaml
    assert match_bank({"name": "Ngân hàng TMCP Đầu tư và Phát triển"}, aliases) == "BIDV"  # name minus "Việt Nam"
    assert match_bank({"name": "Ngân hàng Việt Nam"}, aliases) is None  # too generic to reverse-match
    assert match_bank({"brand": "Ngân hàng Ruột"}, aliases) is None
    assert match_bank({}, aliases) is None
    assert match_bank(None, aliases) is None


def test_build_geo_provinces_fixture(tmp_path):
    osm_json = tmp_path / "overpass.json"
    osm_json.write_text((FIXTURES / "mini_overpass.json").read_text(encoding="utf-8"), encoding="utf-8")
    gold, summary = build_geo(
        geojson_path=FIXTURES / "mini.geojson",
        banks_path=FIXTURES / "mini_banks.yaml",
        population_path=FIXTURES / "mini_population.csv",
        osm_json=osm_json,
    )

    assert [p["pcode"] for p in gold["provinces"]] == ["VN00", "VN01"]
    a, b = gold["provinces"]
    assert a["branches_total"] == 2 and a["branches_by_bank"] == {"VCB": 1}
    assert b["branches_total"] == 2 and b["branches_by_bank"] == {"VCB": 1, "TCB": 1}
    assert a["population"] == 100000 and a["population_period"] == "2024"
    assert a["deposits_bn"] is None and a["credit_bn"] is None and a["best_counter_12m"] is None
    assert "OSM" in a["branch_source"]
    assert "© OpenStreetMap contributors (ODbL)" in gold["attribution"]
    assert gold["boundary"] == "web/public/geo/vn-34.geo.json"

    assert summary["elements_total"] == 5
    assert summary["elements_in_province"] == 4
    assert summary["elements_matched"] == 3
    assert summary["unmatched_in_province"] == 1
    assert summary["unmatched_share"] == pytest.approx(0.25)
    assert summary["banks_matched"] == 2  # distinct codes seen
    assert summary["provinces_covered"] == 2


def test_write_gold_roundtrip(tmp_path):
    gold, _ = build_geo(
        geojson_path=FIXTURES / "mini.geojson",
        banks_path=FIXTURES / "mini_banks.yaml",
        population_path=FIXTURES / "mini_population.csv",
        osm_json=FIXTURES / "mini_overpass.json",
    )
    out = tmp_path / "gold" / "geo_provinces.json"
    write_gold(out, gold)
    assert json.loads(out.read_text(encoding="utf-8")) == gold


def test_latest_overpass_and_collect_reuses_cache(tmp_path):
    assert latest_overpass(tmp_path) is None

    store = BronzeStore(tmp_path / "bronze", run_id="rw-test")
    payload = (FIXTURES / "mini_overpass.json").read_bytes()
    store.save("osm", "overpass_vn_bank.osm.json", payload, url="https://overpass-api.de/api/interpreter",
               licence="ODbL", method="overpass")

    found = latest_overpass(tmp_path)
    assert found is not None and found.name == "overpass_vn_bank.osm.json"

    def boom(**_kwargs):
        raise AssertionError("network fetch must not run when the cache exists")

    assert collect_overpass(tmp_path, fetcher=boom) == found
