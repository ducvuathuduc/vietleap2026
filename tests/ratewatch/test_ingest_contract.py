"""Silver contract (CONTRACT A): unit normalisation, typed rows, dataframe shape."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from vlkit.ratewatch.ingest.contract import (
    SILVER_COLUMNS,
    dedupe_rows,
    normalise_row,
    parse_channel,
    parse_rate,
    parse_term,
    parse_vi_date,
    silver_frame,
)

TZ = ZoneInfo("Asia/Saigon")


def test_parse_rate_accepts_vietnamese_and_english_decimals():
    assert parse_rate("4,75%") == 4.75
    assert parse_rate("4.75 %") == 4.75
    assert parse_rate("5.9") == 5.9
    assert parse_rate("0,5") == 0.5
    assert parse_rate(" 4,50 ") == 4.5


def test_parse_rate_rejects_placeholders_and_prose():
    for value in ("-", "", None, "không có", "0%", "20", "abc"):
        assert parse_rate(value) is None, value


def test_parse_term_months_handles_ranges_and_demand():
    assert parse_term("12 tháng") == 12
    assert parse_term("Từ 1 đến dưới 2 tháng") == 1
    assert parse_term("Từ 1 tháng đến dưới 2 tháng") == 1
    assert parse_term("12 tháng (*)") == 12
    assert parse_term("Không kỳ hạn") == 0
    assert parse_term("KKH") == 0
    assert parse_term("1 tuần") is None
    assert parse_term("Dưới 1 tháng") is None
    assert parse_term("Trên 500 triệu đồng") is None


def test_parse_channel_maps_printed_labels():
    assert parse_channel("Tại quầy") == "counter"
    assert parse_channel("TẠI QUẦY") == "counter"
    assert parse_channel("Online") == "online"
    assert parse_channel("Tiết kiệm Online") == "online"
    assert parse_channel("Trực tuyến") == "online"
    with pytest.raises(ValueError):
        parse_channel("không rõ")


def test_parse_vi_date_reads_printed_effective_dates():
    assert parse_vi_date("Hiệu lực từ 07h30 ngày 20.10.2026") == date(2026, 10, 20)
    assert parse_vi_date("Áp dụng cho KHCN từ ngày 06/11/2026 (ĐVT: %/năm)") == date(2026, 11, 6)
    assert parse_vi_date("(Hiệu lực ngày 19/10/2026)") == date(2026, 10, 19)
    assert parse_vi_date("áp dụng từ ngày 31 tháng 10 năm 2026") == date(2026, 10, 31)
    assert parse_vi_date("không in ngày hiệu lực") is None


def test_normalise_row_casts_units_and_defaults():
    row = normalise_row({
        "run_id": "rw-20261120T1400",
        "bank_code": "vcb",
        "term_months": "6 tháng",
        "channel": "Tại quầy",
        "rate_pct": "4,75%",
        "sheet_date": "20.11.2026",
        "observed_at": "2026-11-20T14:00:00+07:00",
        "reader": "bank_pdf",
        "source_url": "https://example.test/sheet.pdf",
        "raw_sha256": "abc",
    })
    assert row["bank_code"] == "VCB"
    assert row["term_months"] == 6
    assert row["channel"] == "counter"
    assert row["rate_pct"] == 4.75
    assert row["tier"] == ""
    assert row["interest_basis"] == "at_maturity"
    assert row["sheet_date"] == date(2026, 11, 20)


def test_normalise_row_rejects_impossible_rates_and_terms():
    base = {"run_id": "rw-20261120T1400", "bank_code": "VCB", "term_months": 1, "channel": "counter",
            "rate_pct": 4.0, "observed_at": "2026-11-20T14:00:00+07:00", "reader": "aggregator",
            "source_url": "https://example.test/", "raw_sha256": "abc"}
    for bad in ({"rate_pct": 0}, {"rate_pct": 16.0}, {"rate_pct": None},
                {"term_months": -1}, {"term_months": None}, {"channel": "chi nhánh"},
                {"reader": "guess"}):
        with pytest.raises(ValueError):
            normalise_row({**base, **bad})


def test_dedupe_rows_keeps_one_row_per_upsert_key():
    base = {"run_id": "rw-1", "bank_code": "VCB", "term_months": 6, "channel": "online", "tier": "",
            "interest_basis": "at_maturity", "sheet_date": None, "observed_at": "2026-11-20T14:00:00+07:00",
            "reader": "aggregator", "source_url": "https://example.test/", "raw_sha256": "abc"}
    rows = dedupe_rows([{**base, "rate_pct": 4.8}, {**base, "rate_pct": 4.8},
                        {**base, "rate_pct": 4.9}, {**base, "reader": "bank_pdf", "rate_pct": 4.8}])
    assert len(rows) == 2


def test_silver_frame_has_contract_columns_and_types():
    rows = dedupe_rows([normalise_row({
        "run_id": "rw-20261120T1400", "bank_code": "VCB", "term_months": 6, "channel": "online",
        "rate_pct": 4.8, "sheet_date": date(2026, 11, 20), "observed_at": "2026-11-20T14:00:00+07:00",
        "reader": "aggregator", "source_url": "https://example.test/", "raw_sha256": "abc",
    })])
    frame = silver_frame(rows)
    assert list(frame.columns) == SILVER_COLUMNS
    assert frame.term_months.dtype == "int64"
    assert frame.rate_pct.dtype == "float64"
    assert str(frame.sheet_date.dtype).startswith("datetime64")
    assert isinstance(frame.observed_at.iloc[0], pd.Timestamp)
    assert str(frame.observed_at.iloc[0].tzinfo) == "Asia/Saigon"
    assert frame.observed_at.iloc[0].to_pydatetime() == datetime(2026, 11, 20, 14, 0, tzinfo=TZ)
