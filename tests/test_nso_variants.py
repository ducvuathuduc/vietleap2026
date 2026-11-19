"""Regression tests for wording variants found in the real 2024-2026 report runs."""
import pytest

from tools.nso import parse


def run(period, paragraphs, method):
    extractor = parse._Extractor(paragraphs, period, "", "")
    getattr(extractor, method)()
    return {(r["indicator_id"], r["measure_type"]): r["value"] for r in extractor.rows}


@pytest.mark.parametrize(
    "paragraph, period, expected",
    [
        (
            "– Tổng vốn đầu tư nước ngoài đăng ký vào Việt Nam tính đến ngày 20/3/2024 "
            "bao gồm: Vốn đăng ký cấp mới, vốn đăng ký điều chỉnh và giá trị góp vốn, "
            "mua cổ phần của nhà đầu tư nước ngoài đạt gần 6,17 tỷ USD, "
            "tăng 13,4% so với cùng kỳ năm trước.",
            "2024-03",
            {("fdi_dang_ky", "ytd"): 6.17, ("fdi_dang_ky", "yoy"): 13.4},
        ),
        (
            "– Tổng vốn đầu tư nước ngoài đăng ký vào Việt Nam tính đến ngày 20/7/2024 "
            "bao gồm: Vốn đăng ký cấp mới, vốn đăng ký điều chỉnh và giá trị góp vốn, "
            "mua cổ phần của nhà đầu tư nước ngoài đạt hơn 18 tỷ USD, "
            "tăng 10,9% so với cùng kỳ năm trước.",
            "2024-07",
            {("fdi_dang_ky", "ytd"): 18.0, ("fdi_dang_ky", "yoy"): 10.9},
        ),
        (
            "– Tổng vốn đầu tư nước ngoài đăng ký vào Việt Nam trong hai tháng đầu năm 2025 "
            "bao gồm: Vốn đăng ký cấp mới, vốn đăng ký điều chỉnh và giá trị góp vốn, "
            "mua cổ phần của nhà đầu tư nước ngoài đạt gần 6,90 tỷ USD, "
            "tăng 35,5% so với cùng kỳ năm trước.",
            "2025-02",
            {("fdi_dang_ky", "ytd"): 6.9, ("fdi_dang_ky", "yoy"): 35.5},
        ),
    ],
)
def test_fdi_registered_accepts_printed_qualifiers(paragraph, period, expected):
    assert run(period, [paragraph], "fdi") == expected


def test_fdi_realized_without_truc_tiep():
    paragraph = (
        "– Vốn đầu tư nước ngoài thực hiện tại Việt Nam ba tháng đầu năm 2025 "
        "ước đạt 4,96 tỷ USD, tăng 7,2% so với cùng kỳ năm trước."
    )
    assert run("2025-03", [paragraph], "fdi") == {
        ("fdi_thuc_hien", "ytd"): 4.96,
        ("fdi_thuc_hien", "yoy"): 7.2,
    }


def test_trade_month_values_marked_so_bo():
    exports = (
        "– Xuất khẩu hàng hóa: Kim ngạch xuất khẩu hàng hóa tháng 9/2024 sơ bộ "
        "đạt 34,05 tỷ USD, giảm 9,9% so với tháng trước và tăng 10,7% so với cùng kỳ năm trước. "
        "Tính chung chín tháng năm 2024, kim ngạch xuất khẩu hàng hóa sơ bộ "
        "đạt 299,63 tỷ USD, tăng 15,4% so với cùng kỳ năm trước."
    )
    imports = (
        "– Nhập khẩu hàng hóa: Kim ngạch nhập khẩu hàng hóa tháng 9/2024 sơ bộ "
        "đạt 31,76 tỷ USD, giảm 5,9% so với tháng trước và tăng 11,1% so với cùng kỳ năm trước. "
        "Tính chung chín tháng năm 2024, kim ngạch nhập khẩu hàng hóa sơ bộ "
        "đạt 278,84 tỷ USD, tăng 17,3% so với cùng kỳ năm trước."
    )
    assert run("2024-09", [exports], "exports") == {
        ("xuat_khau", "month"): 34.05,
        ("xuat_khau", "ytd"): 299.63,
    }
    assert run("2024-09", [imports], "imports") == {
        ("nhap_khau", "month"): 31.76,
        ("nhap_khau", "ytd"): 278.84,
    }


def test_cpi_yoy_with_cung_ky_nam_truoc():
    paragraph = (
        "– Chỉ số giá tiêu dùng (CPI) tháng Mười Hai tăng 0,19% so với tháng trước. "
        "So với cùng kỳ năm trước, CPI tháng Mười Hai tăng 3,48%. "
        "CPI bình quân quý IV/2025 tăng 3,44% so với quý IV/2024. "
        "Tính chung cả năm 2025, CPI tăng 3,31% so với năm trước, "
        "đạt mục tiêu Quốc hội đề ra."
    )
    assert run("2025-12", [paragraph], "cpi") == {
        ("cpi", "mom"): 0.19,
        ("cpi", "yoy"): 3.48,
        ("cpi", "avg_ytd"): 3.31,
    }


def test_trade_balance_ytd_without_tinh_chung():
    paragraph = (
        "Cán cân thương mại hàng hóa 2 tháng đầu năm 2024 ước tính xuất siêu 4,72 tỷ USD "
        "(cùng kỳ năm trước xuất siêu 3,5 tỷ USD)."
    )
    assert run("2024-02", [paragraph], "trade_balance") == {
        ("can_can_thuong_mai", "ytd"): 4.72,
    }


def test_trade_balance_month_is_the_reported_period_month():
    paragraph = (
        "Cán cân thương mại hàng hóa sơ bộ tháng Ba xuất siêu 2,78 tỷ USD ; "
        "quý I xuất siêu 7,72 tỷ USD; tháng Tư ước tính xuất siêu 0,68 tỷ USD. "
        "Tính chung bốn tháng đầu năm 2024, cán cân thương mại hàng hóa "
        "ước tính xuất siêu 8,4 tỷ USD (cùng kỳ năm trước xuất siêu 7,66 tỷ USD)."
    )
    assert run("2024-04", [paragraph], "trade_balance") == {
        ("can_can_thuong_mai", "month"): 0.68,
        ("can_can_thuong_mai", "ytd"): 8.4,
    }


def test_iip_accepts_nganh_cong_nghiep():
    paragraph = (
        "– Chỉ số sản xuất ngành công nghiệp (IIP) tháng 8/2024 ước tính "
        "tăng 2,0% so với tháng trước và tăng 9,5% so với cùng kỳ năm trước."
    )
    assert run("2024-08", [paragraph], "iip") == {
        ("iip", "mom"): 2.0,
        ("iip", "yoy"): 9.5,
    }


def test_budget_chi_month_without_thang_word():
    paragraph = (
        "Tổng chi ngân sách Nhà nước Bảy ước đạt 164,9 nghìn tỷ đồng. "
        "Lũy kế tổng chi ngân sách Nhà nước bảy tháng năm 2025 ước đạt 1.317,4 nghìn tỷ đồng, "
        "bằng 51,7% dự toán năm và tăng 39,3% so với cùng kỳ năm trước."
    )
    extractor = parse._Extractor([paragraph], "2025-07", "", "")
    extractor.budget("nsnn_chi", r"tổng chi ngân sách")
    assert {(r["indicator_id"], r["measure_type"]): r["value"] for r in extractor.rows} == {
        ("nsnn_chi", "month"): 164.9,
        ("nsnn_chi", "ytd"): 1317.4,
        ("nsnn_chi", "pct_plan"): 51.7,
        ("nsnn_chi", "yoy"): 39.3,
    }


@pytest.mark.parametrize(
    "paragraph, period, expected",
    [
        (
            "– Chỉ số giá tiêu dùng (CPI) tháng 6/2025 tăng 0,48% so với tháng; "
            "tăng 2,02% so với tháng 12/2024; tăng 3,57% so với cùng kỳ năm trước. "
            "CPI bình quân quý II/2025 tăng 3,31% so với quý II/2024. "
            "Bình quân sáu tháng đầu năm 2025, CPI tăng 3,27% so với cùng kỳ năm trước; "
            "lạm phát cơ bản tăng 3,16%.",
            "2025-06",
            {("cpi", "mom"): 0.48, ("cpi", "yoy"): 3.57, ("cpi", "avg_ytd"): 3.27},
        ),
        (
            "– Chỉ số giá tiêu dùng (CPI) tháng 01/2026 tăng nhẹ 0,05% so với tháng trước "
            "và tăng 2,53% so với cùng kỳ năm trước; "
            "lạm phát cơ bản tháng 01/2026 tăng 3,19%.",
            "2026-01",
            {("cpi", "mom"): 0.05, ("cpi", "yoy"): 2.53},
        ),
    ],
)
def test_cpi_mom_wording_variants(paragraph, period, expected):
    assert run(period, [paragraph], "cpi") == expected


def test_trade_balance_month_without_hoa():
    paragraph = (
        "Theo số liệu sơ bộ, cán cân thương mại hàng tháng Một nhập siêu 1,78 tỷ USD "
        "(cùng kỳ năm trước xuất siêu 3,17 tỷ USD)."
    )
    assert run("2026-01", [paragraph], "trade_balance") == {
        ("can_can_thuong_mai", "month"): -1.78,
    }


def test_trade_balance_ytd_ignores_sau_count_thang():
    paragraph = (
        "Tổng kim ngạch xuất, nhập khẩu hàng hóa tháng Chín đạt 117,69 tỷ USD. "
        "Đặc biệt, cán cân thương mại hàng hóa tháng Chín đã xuất siêu trở lại "
        "sau chín tháng liên tiếp nhập siêu, với mức xuất siêu 1,27 tỷ USD. "
        "Tính chung chín tháng năm 2026, tổng kim ngạch xuất, nhập khẩu hàng hóa "
        "đạt 888,02 tỷ USD. Cán cân thương mại hàng hóa chín tháng nhập siêu 19,42 tỷ USD."
    )
    assert run("2026-09", [paragraph], "trade_balance") == {
        ("can_can_thuong_mai", "month"): 1.27,
        ("can_can_thuong_mai", "ytd"): -19.42,
    }


def test_trade_balance_ytd_with_count_word():
    paragraph = (
        "Theo số liệu sơ bộ, cán cân thương mại hàng hóa tháng Chín xuất siêu 1,27 tỷ USD. "
        "Tính chung chín tháng năm 2026, cán cân thương mại hàng hóa nhập siêu 19,42 tỷ USD[7] "
        "(cùng kỳ năm trước xuất siêu 16,87 tỷ USD)."
    )
    assert run("2026-09", [paragraph], "trade_balance") == {
        ("can_can_thuong_mai", "month"): 1.27,
        ("can_can_thuong_mai", "ytd"): -19.42,
    }
