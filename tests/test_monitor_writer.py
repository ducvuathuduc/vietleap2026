"""Serving contract, artifact exports, and observation reconciliation."""

import json

import pandas as pd
import pytest
from jsonschema import Draft202012Validator, ValidationError


def observation(period, value, source="nso", geo="", kind="national", **fields):
    return {
        "indicator_id": "total_spending", "period": period, "geo": geo, "geo_type": kind,
        "value": value, "unit": "tỷ đồng", "measure_type": "ytd", "source_id": source, **fields,
    }


@pytest.fixture
def inputs(kit_root, tmp_path):
    def source(source_id, cutoff):
        return {
            "id": source_id, "publisher": source_id.upper(), "title_vi": "Chi ngân sách",
            "url": "https://example.org/budget", "method": "file", "license": "Công khai",
            "fetched_at": "2026-11-19T08:00:00+07:00", "data_cutoff": cutoff,
        }

    catalog = [
        {
            "id": "total_spending_ytd", "base_id": "total_spending", "name_vi": "Chi ngân sách",
            "sector": "public_finance", "unit": "tỷ đồng", "frequency": "monthly",
            "measure_type": "ytd", "source_id": "nso", "definition_vi": "Chi lũy kế trong năm.",
            "note_vi": "Điều cần biết về dự toán.", "higher_is_better": True,
        },
        {
            "id": "unknown", "name_vi": "Chưa có số liệu", "sector": "public_finance",
            "unit": "%", "frequency": "monthly", "measure_type": "yoy", "source_id": "nso",
            "definition_vi": "Mức tăng theo năm.", "note_vi": "Chờ công bố.", "higher_is_better": False,
        },
    ]
    evaluation = {
        "rules": [
            {
                "id": "BR-PF1", "name_vi": "Tiến độ chi", "formula_vi": "Tỷ lệ chi theo dự toán",
                "threshold_vi": "Độ lệch với tiến độ thời gian", "fired": True,
            },
            {
                "id": "BR-PF2", "name_vi": "Tiến độ giải ngân", "formula_vi": "Tỷ lệ giải ngân",
                "threshold_vi": "So với tiến độ thời gian", "fired": False,
            },
        ],
        "results": [
            {
                "id": "BR-PF1", "sector": "public_finance", "status": "fired",
                "chart_id": "budget_execution", "indicator_id": "total_spending_ytd",
                "value": 1234.5, "unit": "tỷ đồng", "period": "2026-09", "direction": "down",
                "sentence_vi": "Chi ngân sách đạt 1.234,5 tỷ đồng.", "agency_vi": "Bộ Tài chính",
                "action_vi": "Đối chiếu tiến độ chi.", "source_id": "nso",
                "so_what_vi": "Tiến độ chi cần được theo dõi.",
            },
            {
                "id": "BR-PF2", "sector": "public_finance", "status": "not evaluated",
                "chart_id": "public_investment", "sentence_vi": "Thiếu số liệu giải ngân.",
            },
        ],
        "asean": {}, "province": {"metric_ids": [], "rows": [], "groups": []},
        "heatmap": {}, "tables": {}, "derived": [],
    }
    observations = pd.DataFrame([
        observation("2026-07", 900),
        observation("2026-08", 1000),
        observation("2026-09", 1234.5),
        observation("2026-09", 1245, "press"),
        observation("2026-09", 50, geo="01", kind="province"),
        observation("2026-10", None),
        observation("2026-10", 200, measure_type="level"),
    ])
    model = {
        "tables": [{"name": "gold.fact_indicator", "layer": "gold", "rows": 6}],
        "quality": [{"source_id": "nso", "rows": 5, "score_before": 90, "score_after": 98, "flags": {}}],
        "profiles": [{
            "table": "silver.nso", "source_id": "nso", "rows": 5, "columns": {"value": "DOUBLE"},
            "missing": {"value": 1}, "duplicates": 1, "time_gap_count": 2, "outliers": 1,
            "correlations": {"value/plan": 0.8}, "date_from": "2026-08", "date_to": "2026-10",
        }],
    }
    return {
        "out": tmp_path / "monitor",
        "schema_path": kit_root / "specs/001-vietleap-insight-kit/contracts/monitor.schema.json",
        "catalog": catalog, "sources": [source("nso", "2026-10"), source("press", "2026-09")],
        "observations": observations, "evaluation": evaluation, "model": model,
        "erd": "erDiagram\n    DIM_INDICATOR ||--o{ FACT_INDICATOR : identifies\n",
        "views": {
            "v_budget_execution": pd.DataFrame({"value": [1234.5]}),
            "v_fdi": lambda path: path.write_text("value\n", encoding="utf-8"),
        },
    }


def test_writer_exports_valid_payload_and_linked_artifacts(inputs):
    from vlkit.monitor.writer import write_monitor

    payload = write_monitor(**inputs)
    out = inputs["out"]
    encoded = json.loads((out / "monitor.json").read_text(encoding="utf-8"))
    schema = json.loads(inputs["schema_path"].read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    validator.validate(encoded)
    assert encoded == payload
    assert payload["meta"]["generated_at"].endswith("+07:00")
    assert payload["meta"]["lead_vi"] == ["Chi ngân sách đạt 1.234,5 tỷ đồng."]
    assert [i["id"] for i in payload["indicators"]] == ["total_spending_ytd"]
    indicator = payload["indicators"][0]
    assert indicator["latest"] == {"period": "2026-10", "value": None}
    assert indicator["sparkline"] == [
        {"period": "2026-07", "value": 900},
        {"period": "2026-08", "value": 1000},
        {"period": "2026-09", "value": 1234.5},
        {"period": "2026-10", "value": None},
    ]
    assert {"period": "2026-09", "value": 50, "geo": "01"} in payload["series"]["total_spending_ytd"]
    assert all(row["period"] != "2026-07" for row in payload["reconciliation"])
    sector = payload["sectors"]["public_finance"]
    assert sector["cards"][0]["source_id"] == "nso"
    assert sector["charts"][0]["indicator_ids"] == ["total_spending_ytd"]
    assert "Thiếu số liệu giải ngân." in sector["watch"]
    evidence = payload["recommendations"][0]["evidence"][0]
    assert evidence["chart_id"] == sector["charts"][0]["id"]
    assert evidence["rule_id"] == sector["cards"][0]["rule_id"]
    assert all((out / path).is_file() for path in payload["files"].values())
    assert (out / "csv/v_budget_execution.csv").read_text(encoding="utf-8") == "value\n1234.5\n"
    assert (out / "csv/v_fdi.csv").read_text(encoding="utf-8") == "value\n"
    assert (out / "erd.mmd").read_text(encoding="utf-8") == inputs["erd"]
    assert (out / "data_dictionary.csv").read_text(encoding="utf-8").count("Chờ công bố.") == 1
    assert "Chi lũy kế trong năm." in (out / "data_dictionary.md").read_text(encoding="utf-8")
    eda = (out / "eda.md").read_text(encoding="utf-8")
    assert "value/plan" in eda and "0,80" in eda and "BR-PF2" in eda
    assert "1.234,5" in eda and "1.245" in eda


@pytest.mark.parametrize(("field", "value", "error"), [
    ("url", "not a URI", "uri"),
    ("fetched_at", "2026-11-19T08:00:00", "date-time"),
    ("data_cutoff", "2026-13", "pattern"),
])
def test_writer_refuses_invalid_contract_without_touching_artifacts(inputs, field, value, error):
    from vlkit.monitor.writer import write_monitor

    inputs["out"].mkdir()
    original = inputs["out"] / "monitor.json"
    original.write_text("existing", encoding="utf-8")
    inputs["sources"][0][field] = value

    with pytest.raises(ValidationError) as raised:
        write_monitor(**inputs)

    assert error in str(raised.value)
    assert original.read_text(encoding="utf-8") == "existing"
    assert list(inputs["out"].iterdir()) == [original]


def test_writer_refuses_card_without_a_registered_source(inputs):
    from vlkit.monitor.writer import write_monitor

    inputs["evaluation"]["results"][0]["source_id"] = "unregistered"

    with pytest.raises(ValidationError, match="unregistered"):
        write_monitor(**inputs)

    assert not inputs["out"].exists()


def test_reconciliation_matches_grain_and_uses_latest_source_revision():
    from vlkit.monitor.writer import reconcile

    rows = pd.DataFrame([
        observation("2026-07", 80, published_date="2026-08-01"),
        observation("2026-07", 100, published_date="2026-08-02"),
        observation("2026-07", 99, "press", published_date="2026-08-03"),
        observation("2026-08", 100),
        observation("2026-08", 95, "press"),
        observation("2026-09", 0),
        observation("2026-09", 0, "press"),
        observation("2026-10", 300),
        observation("2026-10", 9, "press", unit="%"),
        observation("2026-10", 50, "press", measure_type="level"),
        observation("2026-10", 40, "press", geo="01", kind="province"),
        observation("2026-10", 12, "press", is_imputed=True),
        observation("2026-10", 20, "sbv", is_invalid=True),
        observation("2026-10", None, "wdi"),
    ])
    checks = reconcile(rows, {"total_spending": 1.0})

    july, august, september = checks[:3]
    assert july["values"] == {"nso": 100, "press": 99}
    assert july["diff_pct"] == pytest.approx(1)
    assert july["verdict"] == "match"
    assert august["diff_pct"] == pytest.approx(5)
    assert august["verdict"] == "mismatch"
    assert september["diff_pct"] == 0
    assert september["verdict"] == "match"
    october = checks[3:]
    assert len(october) == 4
    assert all(row["verdict"] == "single_source" for row in october)
    assert any("01" in row["note_vi"] for row in october)


def test_rule_charts_include_related_indicators_tables_and_source_notes(inputs):
    from vlkit.monitor.writer import write_monitor

    inputs["catalog"].append({
        **inputs["catalog"][0], "id": "planned_spending", "base_id": "planned_spending",
        "name_vi": "Dự toán chi", "source_id": "press", "note_vi": "Đối chiếu dự toán đã duyệt.",
    })
    inputs["evaluation"]["derived"].append({
        **observation("2026-09", 1400, "press"), "indicator_id": "planned_spending",
    })
    fact = inputs["evaluation"]["results"][0]
    inputs["sources"].append({**inputs["sources"][0], "id": "sbv", "publisher": "SBV"})
    fact["source_ids"] = ["nso", "sbv"]
    inputs["evaluation"]["results"].append({
        **fact, "id": "BR-PF2", "status": "evaluated", "indicator_id": "planned_spending",
        "source_id": "press", "value": 1400, "sentence_vi": "Dự toán chi là 1.400 tỷ đồng.",
    })
    inputs["evaluation"]["tables"]["public_finance"] = [{
        "id": "budget_execution", "title_vi": "Bảng tiến độ chi", "columns": [], "rows": [],
        "source_ids": ["press"],
    }]
    payload = write_monitor(**inputs)
    chart = payload["sectors"]["public_finance"]["charts"][0]

    assert chart["kind"] == "table"
    assert chart["indicator_ids"] == ["total_spending_ytd", "planned_spending"]
    assert chart["source_ids"] == ["nso", "press", "sbv"]
    assert "Đối chiếu dự toán đã duyệt." in chart["note_vi"]
