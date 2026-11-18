"""EDA judge notes: row-flow line, method notes (cleaning/serving), and the
independent World Bank cross-check rendered by write_eda."""
import pandas as pd


def _results(**overrides):
    base = {
        "meta": {"name": "demo", "target": "gdp_per_capita_usd"},
        "profile": {
            "rows": 250, "columns": 3, "missing_overall_pct": 0.0,
            "outlier_rows_pct": 0.0, "column_profiles": [], "issues": [],
        },
        "timeseries": {"points": []},
        "insights": [],
        "caveats_vi": [],
    }
    base.update(overrides)
    return base


def test_eda_renders_row_flow_method_notes_and_match(tmp_path):
    from vlkit.de.exports import write_eda

    results = _results(
        quality_summary={"bronze_rows": 2540, "silver_rows": 2500, "duplicate_rows": 40,
                         "score_before": 87.0, "score_after": 93.5},
        validation={"indicator": "NY.GDP.PCAP.CD", "country": "VNM", "year": 2024,
                    "warehouse_value": 4716.66, "live_value": 4716.66, "diff_pct": 0.0,
                    "status": "match", "checked_at": "2026-11-18 12:00:00",
                    "source": "api.worldbank.org"},
    )
    write_eda(results, tmp_path)
    text = (tmp_path / "eda.md").read_text(encoding="utf-8")
    assert "Bronze 2.540 dòng → Silver 2.500 dòng" in text
    assert "40 dòng trùng hoàn toàn" in text
    assert "87,0 → 93,5" in text
    assert "--impute interpolate" in text and "keep='last'" in text
    assert "dashboard đọc OBT" in text and "star schema" in text
    assert "4.716,66 USD" in text and "+0,0%" in text and "api.worldbank.org" in text


def test_eda_omits_sections_without_data(tmp_path):
    from vlkit.de.exports import write_eda

    write_eda(_results(), tmp_path)
    text = (tmp_path / "eda.md").read_text(encoding="utf-8")
    assert "Dòng dữ liệu" not in text
    assert "Kiểm chứng độc lập" not in text
    assert "Ghi chú phương pháp" in text  # method notes are always rendered


def test_validate_headline_skips_non_wdi_frames():
    from vlkit.pipeline import _validate_headline

    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert _validate_headline(df) is None


def test_validate_headline_matches_live_value(monkeypatch):
    from vlkit.de import connectors
    from vlkit.pipeline import _validate_headline

    class FakeResult:
        frames = {"wb_check": pd.DataFrame({"value": [4716.6599379632]})}

    monkeypatch.setattr(connectors, "ingest", lambda *a, **k: FakeResult())
    df = pd.DataFrame({
        "iso3": ["VNM", "SGP"], "year": [2024, 2024],
        "gdp_per_capita_usd": [4716.6599379632, 94897.0],
    })
    out = _validate_headline(df)
    assert out["status"] == "match"
    assert out["warehouse_value"] == 4716.66 and out["live_value"] == 4716.66
    assert out["diff_pct"] == 0.0


def test_validate_headline_never_raises_on_api_failure(monkeypatch):
    from vlkit.de import connectors
    from vlkit.pipeline import _validate_headline

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(connectors, "ingest", boom)
    df = pd.DataFrame({
        "iso3": ["VNM"], "year": [2024], "gdp_per_capita_usd": [4716.66],
    })
    out = _validate_headline(df)
    assert out["status"] == "unverified"
    assert "network down" in out["reason"]
