"""Bank PDF reader: term lines of the bank's own rate sheet, column pinned by banks.yaml."""
from datetime import date
from pathlib import Path

from vlkit.ratewatch.ingest.readers.bank_pdf import is_household_sheet, parse_pdf_text

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ratewatch" / "pdf"
RUN = "rw-20261120T1400"
SEEN = "2026-11-20T14:00:00+07:00"


def text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def parse(name, **kw):
    params = {"bank_code": "STB", "channel": "counter", "tier": "", "rate_column": 0, "run_id": RUN,
              "observed_at": SEEN, "source_url": "https://example.test/sheet.pdf", "raw_sha256": "pdf-sha"}
    params.update(kw)
    return parse_pdf_text(text(name), **params)


def test_sacombank_first_column_is_counter_under_500tr():
    rows = parse("Sacombank_20261020.txt", bank_code="STB", tier="duoi_500tr", rate_column=0)
    rates = {r["term_months"]: r["rate_pct"] for r in rows}
    assert rates[1] == 4.5
    assert rates[5] == 4.5
    assert rates[6] == 5.7
    assert rates[12] == 5.4
    assert max(rates) == 12  # fixture trimmed at 12 months
    assert 0 not in rates  # "Dưới 1 tháng" is not a demand row
    assert {r["sheet_date"] for r in rows} == {date(2026, 10, 20)}
    assert all(r["reader"] == "bank_pdf" and r["tier"] == "duoi_500tr" for r in rows)
    assert all(r["interest_basis"] == "at_maturity" for r in rows)


def test_ocb_online_column_is_pinned_not_guessed():
    rows = parse("OCB_20261106.txt", bank_code="OCB", channel="online", tier="duoi_100tr", rate_column=5)
    rates = {r["term_months"]: r["rate_pct"] for r in rows}
    assert rates[1] == 4.75
    assert rates[6] == 6.0
    assert rates[12] == 6.3
    assert {r["sheet_date"] for r in rows} == {date(2026, 11, 6)}
    assert all(r["channel"] == "online" for r in rows)


def test_vietbank_end_of_term_column():
    rows = parse("VietBank_20261019.txt", bank_code="VBB", rate_column=0)
    rates = {r["term_months"]: r["rate_pct"] for r in rows}
    assert rates[1] == 4.5
    assert rates[6] == 5.3
    assert rates[12] == 5.5
    assert {r["sheet_date"] for r in rows} == {date(2026, 10, 19)}


def test_missing_column_does_not_shift_to_another_row_value():
    rows = parse("OCB_20261106.txt", bank_code="OCB", channel="online", rate_column=9)
    assert rows == []


def test_corporate_sheet_is_refused():
    corporate = "LÃI SUẤT TIỀN GỬI DÀNH CHO KHÁCH HÀNG DOANH NGHIỆP\n1 tháng 3,00%\n6 tháng 4,00%\n"
    assert is_household_sheet(corporate) is False
    assert parse_pdf_text(corporate, bank_code="BIDV", channel="counter", rate_column=0, run_id=RUN,
                          observed_at=SEEN, source_url="https://example.test/corp.pdf",
                          raw_sha256="x") == []


def test_scan_without_text_returns_no_rows():
    rows = parse_pdf_text("MSB scan OCR garbage 12 3", bank_code="MSB", channel="counter",
                          rate_column=0, run_id=RUN, observed_at=SEEN,
                          source_url="https://example.test/scan.pdf", raw_sha256="x")
    assert rows == []
