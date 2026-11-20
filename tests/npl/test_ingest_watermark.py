from vlkit.npl.ingest.watermark import load, quarter_periods, save, year_periods


def test_watermark_roundtrip(tmp_path):
    path = tmp_path / "state" / "watermarks.json"
    assert load(path) == {}
    save(path, {"bank_quarter": "2026Q3"})
    assert load(path) == {"bank_quarter": "2026Q3"}


def test_quarters_resume_at_watermark_and_refetch_it():
    assert quarter_periods("2021Q1", "2026Q3", None)[0] == "2021Q1"
    assert quarter_periods("2021Q1", "2026Q3", "2026Q2") == ["2026Q2", "2026Q3"]
    assert quarter_periods("2021Q1", "2026Q3", "2024Q4")[-1] == "2026Q3"
    assert "2025Q1" in quarter_periods("2021Q1", "2026Q3", "2024Q4")


def test_years_resume_at_watermark():
    assert year_periods(2021, 2026, None) == [2021, 2022, 2023, 2024, 2025, 2026]
    assert year_periods(2021, 2026, "2025") == [2025, 2026]
