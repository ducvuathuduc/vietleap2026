import csv
import hashlib
from pathlib import Path

import pytest

from tools.sbv import extract

FIX = Path(__file__).parent / "fixtures" / "sbv"
PAGE = "https://sbv.gov.vn/du-no-tin-dung-doi-voi-nen-kt-dttktt"

EXPECTED = {
    ("2025-10", "Nông nghiệp, lâm nghiệp và thuỷ sản"): (1106909.62, 8.26, "so với cuối năm 2024"),
    ("2025-10", "Công nghiệp và xây dựng"): (4314295.34, 11.35, "so với cuối năm 2024"),
    ("2025-10", "Công nghiệp"): (2968266.73, 10.85, "so với cuối năm 2024"),
    ("2025-10", "Xây dựng"): (1346028.61, 12.47, "so với cuối năm 2024"),
    ("2025-10", "Hoạt động Thương mại, Vận tải và Viễn thông"): (4793564.4, 8.8, "so với cuối năm 2024"),
    ("2025-10", "Thương mại"): (4341914.71, 7.89, "so với cuối năm 2024"),
    ("2025-10", "Vận tải và Viễn thông"): (451649.69, 18.35, "so với cuối năm 2024"),
    ("2025-10", "Các hoạt động dịch vụ khác"): (7792767.4, 23.43, "so với cuối năm 2024"),
    ("2025-10", "TỔNG CỘNG"): (18007536.76, 15.31, "so với cuối năm 2024"),
    ("2026-08", "Nông nghiệp, lâm nghiệp và thủy sản"): (1245854, 9.77, "so với cuối năm trước"),
    ("2026-08", "Công nghiệp và xây dựng"): (4878387, 12.05, "so với cuối năm trước"),
    ("2026-08", "Công nghiệp"): (3276604, 11.15, "so với cuối năm trước"),
    ("2026-08", "Xây dựng"): (1601783, 13.95, "so với cuối năm trước"),
    ("2026-08", "Hoạt động Thương mại,Vận tải và Viễn thông"): (5126749, 4.89, "so với cuối năm trước"),
    ("2026-08", "Thương mại"): (4567396, 3.53, "so với cuối năm trước"),
    ("2026-08", "Vận tải và Viễn thông"): (559352, 17.5, "so với cuối năm trước"),
    ("2026-08", "Các hoạt động dịch vụ khác"): (9238445, 12.41, "so với cuối năm trước"),
    ("2026-08", "TỔNG CỘNG"): (20489434, 10.19, "so với cuối năm trước"),
}


def test_parse_fixture_rows_and_metadata():
    rows = extract.parse_file(FIX / "sbv_credit_2026-08.html", source_url=PAGE)
    assert len(rows) == 18
    found = {(r["period"], r["sector"]): r for r in rows}
    assert set(found) == set(EXPECTED)
    for key, (balance, growth, base) in EXPECTED.items():
        row = found[key]
        assert row["balance_bn_vnd"] == pytest.approx(balance)
        assert row["growth_vs_prev_year_end_pct"] == pytest.approx(growth)
        assert row["comparison_base"] == base
        assert row["source_url"] == PAGE
        assert row["period"] in row["evidence"]
        assert row["sector"] in row["evidence"]


def test_decimal_comma_is_not_read_as_thousands():
    rows = extract.parse_file(FIX / "sbv_credit_2026-08.html")
    found = {(r["period"], r["sector"]): r for r in rows}
    assert found[("2025-10", "Nông nghiệp, lâm nghiệp và thuỷ sản")][
        "growth_vs_prev_year_end_pct"
    ] == pytest.approx(8.26)
    assert found[("2026-08", "TỔNG CỘNG")]["balance_bn_vnd"] == 20489434


def test_write_csv_is_idempotent(tmp_path):
    rows = extract.parse_file(FIX / "sbv_credit_2026-08.html", source_url=PAGE)
    extract.write_csv(rows, tmp_path)
    first = (tmp_path / extract.CSV_NAME).read_bytes()
    extract.write_csv(rows, tmp_path)
    second = (tmp_path / extract.CSV_NAME).read_bytes()
    assert first == second
    with open(tmp_path / extract.CSV_NAME, encoding="utf-8", newline="") as handle:
        parsed = list(csv.DictReader(handle))
    assert len(parsed) == 18
    keys = [(r["period"], r["sector"]) for r in parsed]
    assert len(keys) == len(set(keys))


def test_run_is_idempotent_and_uses_cache(tmp_path):
    fixture = (FIX / "sbv_credit_2026-08.html").read_bytes()
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return fixture

    kwargs = dict(
        out_dir=tmp_path,
        fetch_fn=fake_fetch,
        robots_fn=lambda: True,
        sleep=lambda _s: None,
        delay=0,
    )
    first = extract.run(**kwargs)
    first_bytes = (tmp_path / extract.CSV_NAME).read_bytes()
    second = extract.run(**kwargs)

    assert first["rows"] == 18
    assert second["rows"] == 18
    assert first["fetched"] == ["credit_by_sector"]
    assert second["cached"] == ["credit_by_sector"]
    assert calls == [extract.PAGE_URL]
    assert (tmp_path / "credit_by_sector.html").read_bytes() == fixture
    assert (tmp_path / "credit_by_sector.html.sha256").read_text().strip() == hashlib.sha256(
        fixture
    ).hexdigest()
    assert (tmp_path / extract.CSV_NAME).read_bytes() == first_bytes


def test_run_without_balance_rows_does_not_write_guesses(tmp_path):
    html = "<html><body><table><tr><td>STT</td><td>Chỉ tiêu</td></tr></table></body></html>"
    with pytest.raises(ValueError):
        extract.parse_html(html)
