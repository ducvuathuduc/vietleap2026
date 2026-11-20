"""Bank HTML reader: a server-rendered <table> with the rate column pinned by banks.yaml."""
from pathlib import Path

from vlkit.ratewatch.ingest.readers.bank_html import find_pdf_links, parse_bank_html

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ratewatch" / "html"
RUN = "rw-20261120T1400"
SEEN = "2026-11-20T14:00:00+07:00"


def parse(name, **kw):
    params = {"bank_code": "OCB", "channel": "online", "tier": "", "rate_column": 3, "run_id": RUN,
              "observed_at": SEEN, "source_url": "https://example.test/lai-suat", "raw_sha256": "html-sha"}
    params.update(kw)
    return parse_bank_html((FIXTURES / name).read_text(encoding="utf-8"), **params)


def test_ocb_table_online_column():
    rows = parse("OCB_20261120.html")
    rates = {r["term_months"]: r["rate_pct"] for r in rows}
    assert rates[1] == 4.75
    assert rates[6] == 6.0
    assert rates[12] == 6.3
    assert rows[0]["sheet_date"] is None
    assert all(r["reader"] == "bank_html" and r["channel"] == "online" for r in rows)
    assert all(r["source_url"] == "https://example.test/lai-suat" for r in rows)


def test_vietinbank_vnd_counter_column():
    rows = parse("VietinBank_20261120.html", bank_code="CTG", channel="counter", rate_column=1)
    rates = {r["term_months"]: r["rate_pct"] for r in rows}
    assert rates[1] == 2.1
    assert rates[6] == 3.0
    assert rates[12] == 5.4
    assert {r["sheet_date"] for r in rows} == {None}  # the page date 17/7/2024 is not a rate-sheet date


def test_css_percentages_are_not_rates():
    page = ('<html><head><style>.bar{width:0.85%}</style></head><body>'
            '<p>4.75% không phải bảng lãi suất</p></body></html>')
    assert parse_bank_html(page, bank_code="ACB", channel="counter", rate_column=1, run_id=RUN,
                           observed_at=SEEN, source_url="https://example.test/", raw_sha256="x") == []


def test_find_pdf_links_scores_rate_sheets_first():
    page = ('<a href="/files/gioi-thieu.pdf">Giới thiệu</a>'
            '<a href="/files/bieu-lai-suat-khcn-2026.pdf">Biểu lãi suất</a>')
    links = find_pdf_links(page, "https://example.test/lai-suat")
    assert links[0] == "https://example.test/files/bieu-lai-suat-khcn-2026.pdf"
    assert len(links) == 2
