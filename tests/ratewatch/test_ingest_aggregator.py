"""Aggregator reader: laisuattietkiem.vn server-rendered table -> silver rows."""
from datetime import date
from pathlib import Path

from vlkit.ratewatch.ingest.banks import load_banks
from vlkit.ratewatch.ingest.readers.aggregator import parse_aggregator_html

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ratewatch"
AGG_URL = "https://laisuattietkiem.vn/"
RUN = "rw-20261120T1400"
SEEN = "2026-11-20T14:00:00+07:00"


def fixture_html() -> str:
    return (FIXTURES / "aggregator_20261120.html").read_text(encoding="utf-8")


def parse(html: str, banks=None):
    return parse_aggregator_html(html, url=AGG_URL, run_id=RUN, observed_at=SEEN, raw_sha256="agg-sha",
                                 banks=banks or load_banks())


def test_reads_counter_and_online_cells_with_page_stamp():
    rows = parse(fixture_html())
    rates = {(r["bank_code"], r["channel"], r["term_months"]): r["rate_pct"] for r in rows}
    assert rates[("AGB", "counter", 1)] == 2.6
    assert rates[("AGB", "counter", 3)] == 2.9
    assert rates[("AGB", "counter", 6)] == 3.5
    assert ("AGB", "counter", 36) not in rates
    assert rates[("OCB", "counter", 6)] == 5.9
    assert rates[("OCB", "online", 12)] == 6.3
    assert all(r["sheet_date"] == date(2026, 11, 20) for r in rows)
    assert all(r["reader"] == "aggregator" and r["source_url"] == AGG_URL for r in rows)
    assert all(r["run_id"] == RUN and r["raw_sha256"] == "agg-sha" for r in rows)
    assert all(r["observed_at"] == SEEN and r["tier"] == "" for r in rows)


def test_dash_cells_and_previous_values_are_not_rates():
    rows = parse(fixture_html())
    agribank = [r for r in rows if r["bank_code"] == "AGB"]
    assert {r["channel"] for r in agribank} == {"counter"}
    assert 4.0 not in [r["rate_pct"] for r in agribank]  # "Trước đó: 4%" is history, not today's rate


def test_unknown_bank_name_is_skipped_without_inventing_a_code():
    html = fixture_html().replace(">OCB<", ">Ngân hàng Không Có Trong Danh Sách<")
    rows = parse(html)
    assert all(r["bank_code"] != "OCB" for r in rows)
    assert {r["bank_code"] for r in rows} == {"AGB", "CTG"}


def test_terms_come_from_the_table_header():
    html = fixture_html().replace("<th>36 tháng</th>", "")
    rows = parse(html)
    assert 36 not in {r["term_months"] for r in rows}
