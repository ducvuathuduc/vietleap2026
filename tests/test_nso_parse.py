from pathlib import Path

import pytest

from tools.nso import parse

FIX = Path(__file__).parent / "fixtures" / "nso"


def by_key(result):
    return {(r["indicator_id"], r["measure_type"]): r for r in result["rows"]}


def values(result):
    return {k: r["value"] for k, r in by_key(result).items()}


def test_period_from_title():
    cases = {
        "Báo cáo tình hình kinh tế – xã hội tháng Mười và 10 tháng năm 2026": "2026-10",
        "Báo cáo tình hình kinh tế - xã hội tháng 01 năm 2024": "2024-01",
        "Báo cáo tình hình kinh tế - xã hội tháng Mười Một và 11 tháng năm 2025": "2025-11",
        "Báo cáo tình hình kinh tế – xã hội Quý II và sáu tháng đầu năm 2026": "2026-06",
        "Báo cáo tình hình kinh tế - xã hội quý IV và năm 2025": "2025-12",
        "Báo cáo tình hình kinh tế - xã hội quý I năm 2026": "2026-03",
    }
    for title, expected in cases.items():
        assert parse.period_from_title(title) == expected


def test_parse_2026_10():
    result = parse.parse_file(FIX / "nso_2026-10.html", source_url="https://example.test/2026-10")
    rows = by_key(result)

    assert result["period"] == "2026-10"
    assert result["published_date"] == "2026-11-03"
    assert len(result["rows"]) == 31
    assert {r["source_url"] for r in result["rows"]} == {"https://example.test/2026-10"}
    assert {r["parser_version"] for r in result["rows"]} == {parse.PARSER_VERSION}

    assert values(result) == {
        ("nsnn_thu", "month"): 251.5,
        ("nsnn_thu", "ytd"): 2438.9,
        ("nsnn_thu", "pct_plan"): 96.4,
        ("nsnn_thu", "yoy"): 11.0,
        ("nsnn_chi", "month"): 235.0,
        ("nsnn_chi", "ytd"): 2108.7,
        ("nsnn_chi", "pct_plan"): 66.8,
        ("nsnn_chi", "yoy"): 14.8,
        ("dtc_giai_ngan", "month"): 121.6,
        ("dtc_giai_ngan", "ytd"): 783.9,
        ("dtc_giai_ngan", "pct_plan"): 69.0,
        ("dtc_giai_ngan", "yoy"): 19.8,
        ("fdi_dang_ky", "ytd"): 54.85,
        ("fdi_dang_ky", "yoy"): 74.0,
        ("fdi_thuc_hien", "ytd"): 24.08,
        ("fdi_thuc_hien", "yoy"): 13.1,
        ("cpi", "mom"): 0.20,
        ("cpi", "yoy"): 5.09,
        ("cpi", "avg_ytd"): 4.57,
        ("iip", "mom"): 2.3,
        ("iip", "yoy"): 15.0,
        ("ban_le", "month"): 695.5,
        ("ban_le", "ytd"): 6618.9,
        ("ban_le", "mom"): 1.0,
        ("ban_le", "yoy"): 13.5,
        ("xuat_khau", "month"): 64.67,
        ("xuat_khau", "ytd"): 499.24,
        ("nhap_khau", "month"): 57.36,
        ("nhap_khau", "ytd"): 511.31,
        ("can_can_thuong_mai", "month"): 7.31,
        ("can_can_thuong_mai", "ytd"): -12.07,
    }

    assert rows[("nsnn_thu", "month")]["evidence"] == (
        "Tổng thu ngân sách nhà nước tháng Mười ước đạt 251,5 nghìn tỷ đồng."
    )
    assert rows[("nsnn_thu", "ytd")]["evidence"] == (
        "Lũy kế tổng thu ngân sách nhà nước mười tháng năm 2026 ước đạt 2.438,9 nghìn tỷ đồng, "
        "bằng 96,4% dự toán năm và tăng 11,0% so với cùng kỳ năm trước."
    )
    assert rows[("cpi", "avg_ytd")]["evidence"] == (
        "Bình quân mười tháng năm 2026, CPI tăng 4,57% so với cùng kỳ năm trước; "
        "lạm phát cơ bản tăng 4,24%."
    )
    assert rows[("nsnn_thu", "month")]["unit"] == "nghìn tỷ đồng"
    assert rows[("fdi_dang_ky", "ytd")]["unit"] == "tỷ USD"
    assert rows[("can_can_thuong_mai", "ytd")]["unit"] == "tỷ USD"
    assert rows[("cpi", "yoy")]["unit"] == "%"


def test_parse_2025_10():
    result = parse.parse_file(FIX / "nso_2025-10.html")
    assert result["period"] == "2025-10"
    assert result["published_date"] == "2025-11-06"
    assert len(result["rows"]) == 31
    assert values(result) == {
        ("nsnn_thu", "month"): 231.2,
        ("nsnn_thu", "ytd"): 2182.7,
        ("nsnn_thu", "pct_plan"): 111.0,
        ("nsnn_thu", "yoy"): 30.8,
        ("nsnn_chi", "month"): 199.1,
        ("nsnn_chi", "ytd"): 1835.7,
        ("nsnn_chi", "pct_plan"): 71.2,
        ("nsnn_chi", "yoy"): 32.1,
        ("dtc_giai_ngan", "month"): 91.0,
        ("dtc_giai_ngan", "ytd"): 640.2,
        ("dtc_giai_ngan", "pct_plan"): 63.1,
        ("dtc_giai_ngan", "yoy"): 27.8,
        ("fdi_dang_ky", "ytd"): 31.52,
        ("fdi_dang_ky", "yoy"): 15.6,
        ("fdi_thuc_hien", "ytd"): 21.3,
        ("fdi_thuc_hien", "yoy"): 8.8,
        ("cpi", "mom"): 0.20,
        ("cpi", "yoy"): 3.25,
        ("cpi", "avg_ytd"): 3.27,
        ("iip", "mom"): 2.4,
        ("iip", "yoy"): 10.8,
        ("ban_le", "month"): 598.4,
        ("ban_le", "ytd"): 5772.9,
        ("ban_le", "mom"): 0.2,
        ("ban_le", "yoy"): 9.3,
        ("xuat_khau", "month"): 42.05,
        ("xuat_khau", "ytd"): 391.0,
        ("nhap_khau", "month"): 39.45,
        ("nhap_khau", "ytd"): 371.44,
        ("can_can_thuong_mai", "month"): 2.6,
        ("can_can_thuong_mai", "ytd"): 19.56,
    }


def test_parse_2024_01_and_missing_fields_are_omitted():
    result = parse.parse_file(FIX / "nso_2024-01.html")
    rows = by_key(result)

    assert result["period"] == "2024-01"
    assert result["published_date"] == "2024-01-29"
    assert len(result["rows"]) == 23
    assert values(result) == {
        ("nsnn_thu", "month"): 231.0,
        ("nsnn_thu", "pct_plan"): 13.6,
        ("nsnn_thu", "yoy"): -2.8,
        ("nsnn_chi", "month"): 128.9,
        ("nsnn_chi", "pct_plan"): 6.1,
        ("nsnn_chi", "yoy"): -0.2,
        ("dtc_giai_ngan", "month"): 31.1,
        ("dtc_giai_ngan", "pct_plan"): 4.4,
        ("dtc_giai_ngan", "yoy"): 12.5,
        ("fdi_dang_ky", "ytd"): 2.36,
        ("fdi_dang_ky", "yoy"): 40.2,
        ("fdi_thuc_hien", "ytd"): 1.48,
        ("fdi_thuc_hien", "yoy"): 9.6,
        ("cpi", "mom"): 0.31,
        ("cpi", "yoy"): 3.37,
        ("iip", "mom"): -4.4,
        ("iip", "yoy"): 18.3,
        ("ban_le", "month"): 524.1,
        ("ban_le", "mom"): 1.6,
        ("ban_le", "yoy"): 8.1,
        ("xuat_khau", "month"): 33.57,
        ("nhap_khau", "month"): 30.65,
        ("can_can_thuong_mai", "month"): 2.92,
    }

    # A field the report does not publish must produce no row, never a guess.
    for missing in [
        ("nsnn_thu", "ytd"),
        ("nsnn_chi", "ytd"),
        ("dtc_giai_ngan", "ytd"),
        ("cpi", "avg_ytd"),
        ("ban_le", "ytd"),
        ("xuat_khau", "ytd"),
        ("nhap_khau", "ytd"),
        ("can_can_thuong_mai", "ytd"),
    ]:
        assert missing not in rows

    # 2024 pages are partly NFD; evidence must be NFC-normalised.
    assert rows[("cpi", "yoy")]["evidence"] == (
        "So với cùng kỳ năm 2023, CPI tháng Một tăng 3,37%; "
        "lạm phát cơ bản tháng 01/2024 tăng 2,72%."
    )
    assert rows[("nsnn_thu", "month")]["evidence"] == (
        "Tổng thu ngân sách Nhà nước tháng 01/2024 ước đạt gần 231 nghìn tỷ đồng, "
        "bằng 13,6% dự toán năm và giảm 2,8% so với cùng kỳ năm trước."
    )


def test_parse_2024_12_annual_report():
    result = parse.parse_file(FIX / "nso_2024-12.html")
    rows = by_key(result)

    assert result["period"] == "2024-12"
    assert result["published_date"] == "2025-01-06"
    assert len(result["rows"]) == 25
    assert values(result) == {
        ("nsnn_thu", "month"): 206.5,
        ("nsnn_thu", "ytd"): 2037.5,
        ("nsnn_thu", "pct_plan"): 119.8,
        ("nsnn_thu", "yoy"): 16.2,
        ("nsnn_chi", "month"): 283.9,
        ("nsnn_chi", "ytd"): 1830.8,
        ("nsnn_chi", "pct_plan"): 86.4,
        ("nsnn_chi", "yoy"): 5.7,
        ("fdi_dang_ky", "ytd"): 38.23,
        ("fdi_dang_ky", "yoy"): -3.0,
        ("fdi_thuc_hien", "ytd"): 25.35,
        ("fdi_thuc_hien", "yoy"): 9.4,
        ("cpi", "mom"): 0.29,
        ("cpi", "yoy"): 2.94,
        ("cpi", "avg_ytd"): 3.63,
        ("ban_le", "month"): 570.7,
        ("ban_le", "ytd"): 6391.0,
        ("ban_le", "mom"): 1.9,
        ("ban_le", "yoy"): 9.0,
        ("xuat_khau", "month"): 35.53,
        ("xuat_khau", "ytd"): 405.53,
        ("nhap_khau", "month"): 35.01,
        ("nhap_khau", "ytd"): 380.76,
        ("can_can_thuong_mai", "month"): 0.52,
        ("can_can_thuong_mai", "ytd"): 24.77,
    }

    # The annual report publishes only annual IIP and no state-budget investment;
    # those are different measures, so they must not be invented.
    assert ("iip", "yoy") not in rows
    assert ("dtc_giai_ngan", "ytd") not in rows
    assert rows[("fdi_thuc_hien", "ytd")]["evidence"] == (
        "Vốn đầu tư trực tiếp nước ngoài thực hiện tại Việt Nam năm 2024 "
        "ước đạt 25,35 tỷ USD, tăng 9,4% so với năm trước."
    )
    assert rows[("cpi", "yoy")]["evidence"] == (
        "So với tháng 12/2023, CPI tháng Mười Hai tăng 2,94%."
    )
    assert rows[("cpi", "avg_ytd")]["evidence"] == (
        "Tính chung cả năm 2024, CPI tăng 3,63% so với năm trước, "
        "đạt mục tiêu Quốc hội đề ra."
    )


def test_period_required():
    with pytest.raises(ValueError):
        parse.parse_html("<html><body><p>no title</p></body></html>")
