from __future__ import annotations

from pathlib import Path

from tools.press import pdf_banking, tf_rows

FIXTURES = Path(__file__).parent / "fixtures" / "press"


def test_mof_appendix_rows_preserve_units_printed_amounts_and_page():
    target = {"source_id": "mof", "url": "https://example.com/report.pdf", "period": "2026-10",
              "published_date": "2026-11-03"}
    transcript = "page\tscope\tgeo\tamount\tpct_plan\n36\tprovince\tĐiện Biên\t3.899.253\t78,97%\n"
    rows = tf_rows.rows_from_mof_appendix(transcript, target)
    assert [(r["measure_type"], r["value"], r["unit"], r["evidence"]) for r in rows] == [
        ("level", "3899253", "triệu đồng", "3.899.253"), ("pct_plan", "78.97", "%", "78,97%"),
    ]
    assert all(r["source_url"].endswith("#page=36") and r["evidence_ok"] == "true" for r in rows)

def test_parse_appendix_reads_thirteen_metrics():
    text = (FIXTURES / "tcbs_appendix_snippet.txt").read_text(encoding="utf-8")
    banks = pdf_banking.parse_appendix(text)
    assert [b["ticker"] for b in banks] == ["BID", "CTG", "MBB", "TCB"]
    ctg = next(b for b in banks if b["ticker"] == "CTG")
    assert ctg["total_assets"] == 2952
    assert ctg["credit_ytd"] == 7.4
    assert ctg["npl"] == 1.2
    assert ctg["npl_coverage"] == 160
    assert ctg["casa"] == 22.7


def test_sector_rows_values_and_evidence():
    text = (FIXTURES / "tcbs_page0_summary.txt").read_text(encoding="utf-8")
    rows = pdf_banking.sector_rows(text, source_id="tcbs", url="https://example/pdf",
                                   published_date="2026-11-16", period="2026-Q3")
    by_id = {r["indicator_id"]: r for r in rows}
    assert by_id["bank_sector_npl"]["value"] == "2.11"
    assert by_id["bank_sector_npl_group2"]["value"] == "1.58"
    assert by_id["bank_sector_npl_coverage"]["value"] == "75"
    assert by_id["bank_sector_nim"]["value"] == "3.11"
    assert by_id["bank_sector_cof"]["value"] == "5.27"
    assert by_id["bank_sector_pb"]["value"] == "1.3"
    assert by_id["bank_sector_roe"]["value"] == "17.4"
    assert by_id["bank_sector_credit"]["value"] == "16050"
    assert by_id["bank_sector_credit_ytd"]["value"] == "12.7"
    assert all(r["evidence_ok"] == "true" for r in rows)
    assert all(r["method"] == "pdf" for r in rows)


def test_bank_rows_contract():
    text = (FIXTURES / "tcbs_appendix_snippet.txt").read_text(encoding="utf-8")
    banks = pdf_banking.parse_appendix(text)
    rows = pdf_banking.bank_rows(banks, source_id="tcbs", url="https://example/pdf",
                                 published_date="2026-11-16", period="2026-Q3")
    assert len(rows) == 4 * 13
    ctg_npl = next(r for r in rows if r["geo"] == "CTG" and r["indicator_id"] == "bank_npl")
    assert ctg_npl["value"] == "1.2"
    assert ctg_npl["evidence_ok"] == "true"
    assert ctg_npl["evidence"].startswith("CTG 2,952")
