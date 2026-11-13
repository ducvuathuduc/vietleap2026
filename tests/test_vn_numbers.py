"""Vietnamese number parsing: vlkit.vn.parse_vn_number / parse_numeric_series / detect_decimal."""
import math

import numpy as np
import pandas as pd
import pytest

from vlkit.vn import ascii_key, clean_text, detect_decimal, parse_numeric_series, parse_vn_number, slug


@pytest.mark.parametrize("raw,expected", [
    ("2,5 tỷ", 2.5e9),
    ("3.5 tỷ", 3.5e9),
    ("850 triệu", 8.5e8),
    ("2 tỷ 300 triệu", 2.3e9),
    ("500k", 5e5),
    ("1.234,5", 1234.5),
    ("1.200.000.000", 1.2e9),
    ("46 m²", 46.0),
    ("1e6", 1e6),
    (7, 7.0),
    (3.25, 3.25),
    (np.int64(12), 12.0),
])
def test_parse_values(raw, expected):
    v, _ = parse_vn_number(raw)
    assert v == pytest.approx(expected)


def test_units_reported():
    assert parse_vn_number("2,5 tỷ")[1]["unit"] == "ty"
    assert parse_vn_number("850 triệu")[1]["unit"] == "trieu"
    assert parse_vn_number("500k")[1]["unit"] == "nghin"


def test_per_m2_and_per_month():
    v, info = parse_vn_number("35 tr/m²")
    assert v == pytest.approx(3.5e7) and info["per"] == "m2"
    v, info = parse_vn_number("12.000.000 đ/tháng")
    assert v == pytest.approx(1.2e7) and info["per"] == "month"


def test_percent_flag():
    v, info = parse_vn_number("12,5%")
    assert v == pytest.approx(12.5) and info["pct"] is True


@pytest.mark.parametrize("raw", ["Thỏa thuận", "Liên hệ", "", "-", "N/A", "đang cập nhật", None, float("nan")])
def test_null_words(raw):
    assert parse_vn_number(raw)[0] is None


def test_address_is_not_a_number():
    assert parse_vn_number("Số 12 Nguyễn Trãi")[0] is None


def test_ambiguous_thousands_follow_column_decimal():
    # '1.234' is 1234 in a VN (comma-decimal) column and 1.234 in an English column
    assert parse_vn_number("1.234", ",")[0] == pytest.approx(1234)
    assert parse_vn_number("1.234", ".")[0] == pytest.approx(1.234)
    assert parse_vn_number("1,234", ".")[0] == pytest.approx(1234)


@pytest.mark.known_bug
@pytest.mark.xfail(reason="ENGINE BUG: accounting negatives '(1.200)' parse as +1200 — the regex's trailing \\b drops ')' so the "
                          "paren check in _to_float never fires; with decimal='.' it even returns 1.2", strict=True)
def test_accounting_negative_parentheses():
    assert parse_vn_number("(1.200)")[0] == pytest.approx(-1200)


@pytest.mark.known_bug
@pytest.mark.xfail(reason="ENGINE LIMITATION: colloquial '2 tỷ 5' (= 2.5 tỷ) parses as 2,000,000,005", strict=True)
def test_colloquial_ty_remainder():
    assert parse_vn_number("2 tỷ 5")[0] == pytest.approx(2.5e9)


def test_detect_decimal():
    assert detect_decimal(["1.234,5", "2,5", "10,75"]) == ","
    assert detect_decimal(["1,234.5", "2.5", "10.75"]) == "."


def test_parse_numeric_series_mixed_units():
    s = pd.Series(["2,5 tỷ", "850 triệu", "Thỏa thuận", "1,2 tỷ"])
    out, rep = parse_numeric_series(s)
    assert out is not None
    assert out.tolist()[0] == pytest.approx(2.5e9)
    assert out.tolist()[1] == pytest.approx(8.5e8)
    assert math.isnan(out.tolist()[2])
    assert rep["units"] == {"ty": 2, "trieu": 1}
    assert rep["failed"] == 0 and rep["ok_ratio"] == 1.0


def test_parse_numeric_series_rejects_text_column():
    out, rep = parse_numeric_series(pd.Series(["Quận 1", "Bình Thạnh", "Gò Vấp", "Thủ Đức"]))
    assert out is None


def test_text_helpers():
    assert clean_text("  Hà\u00a0  Nội ") == "Hà Nội"
    assert ascii_key("Giá (tỷ đồng)") == "gia ty dong"
    assert slug("Diện tích m²") == "dien_tich_m2" or slug("Diện tích m²").startswith("dien_tich")
