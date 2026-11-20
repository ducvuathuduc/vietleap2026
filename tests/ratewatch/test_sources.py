import json
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from vlkit.ratewatch.sources import ingest_sources, parse_cpi, parse_interbank, parse_omo, parse_fx
from vlkit.ratewatch.sources.fiin import fiin_provider, market_daily, quarterly
from vlkit.ratewatch.sources.macro import NSO, cpi_provider, parse_monthly

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/ratewatch/t2"


def test_source_parsers_preserve_period_and_local_number_format():
    assert parse_cpi(b"<p>K\xe1\xbb\xb3 tham chi\xe1\xba\xbfu: 10/2026</p><p>CPI t\xc4\x83ng 0,20% so v\xe1\xbb\x9bi th\xc3\xa1ng tr\xc6\xb0\xe1\xbb\x9bc; t\xc4\x83ng 5,09% so v\xe1\xbb\x9bi c\xc3\xb9ng k\xe1\xbb\xb3 n\xc4\x83m tr\xc6\xb0\xe1\xbb\x9bc.</p>") == [{"month": "2026-10", "pct": 5.09}]
    interbank = "<h3>17/11/2026</h3><table><tr><td>Qua đêm</td><td>4,90</td><td>848.580</td></tr></table>"
    assert parse_interbank(interbank.encode())[0]["volume_bn"] == 848580
    omo = "<h3>19/11/2026</h3><table><tr><td>Mua kỳ hạn</td><td>14</td><td>3</td><td>3</td><td>2.244,48</td><td>4,50</td></tr></table>"
    assert parse_omo(omo.encode())[0]["volume_bn"] == 2244.48
    assert parse_fx("<p>Tỷ giá trung tâm 20/11/2026 25.659 VND/USD</p>".encode())[0]["vnd_per_usd"] == 25659


def test_sbv_omo_date_precedes_scroll_wrapper():
    rows = parse_omo((FIXTURE / "omo_sbv.html").read_bytes())
    assert [(row["date"], row["tenor_days"], row["volume_bn"]) for row in rows] == [
        ("2026-11-19", 7, 224.57), ("2026-11-19", 14, 2244.48),
        ("2026-11-19", 35, 134.69), ("2026-11-19", 91, 109.46),
    ]
    assert rows[0]["parts_bn"] == pytest.approx(rows[0]["total_bn"])


def test_nso_archive_links_use_the_release_url_and_monthly_yoy(tmp_path):
    release = (
        "https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/11/"
        "chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-muoi-va-muoi-thang-nam-2026/"
    )
    saved = {
        NSO: (FIXTURE / "cpi_nso_index.html").read_bytes(),
        release: ("<p>Chỉ số giá tiêu dùng (CPI) tháng Mười tăng 0,20% so với tháng trước; "
                  "tăng 4,41% so với tháng 12/2025 và tăng 5,09% so với cùng kỳ năm trước. "
                  "Bình quân mười tháng năm 2026, CPI tăng 4,57% so với cùng kỳ năm trước.</p>"
                  "<span>Kỳ tham chiếu: 10/2026</span>").encode(),
    }
    log = ingest_sources(tmp_path, "rw-20261120T1436", [cpi_provider(saved.__getitem__, "2026-10")])
    assert log["errors"] == {}
    rows = json.loads((tmp_path / "silver/nonrate/cpi.json").read_text(encoding="utf-8"))
    assert [(row["month"], row["pct"], row["source_url"]) for row in rows] == [("2026-10", 5.09, release)]


def test_nso_reference_period_may_include_month_label():
    archive = (FIXTURE / "cpi_nso_index.html").read_bytes()
    discovered = [url for series, url, _, _ in cpi_provider(lambda url: archive if url == NSO else b"")()
                  if series == "cpi"]
    assert any(url.endswith("thang-nam-va-5-thang-dau-nam-2026/") for url in discovered)
    assert parse_cpi(("<p>Chỉ số giá tiêu dùng tháng Năm giảm 1% so với cùng kỳ năm trước.</p>"
                      "<span>Kỳ tham chiếu: Tháng 5/2026</span>").encode()) == [{"month": "2026-05", "pct": -1}]


def test_ingest_lands_bronze_and_retains_older_watermarks(tmp_path):
    def provider():
        yield "test_cpi", "https://example.org/cpi", b"source html", [
            {"month": "2026-09", "pct": 5.08}, {"month": "2026-10", "pct": 5.09},
        ]

    first = ingest_sources(tmp_path, "rw-20261120T1200", [provider])
    again = ingest_sources(tmp_path, "rw-20261120T1200", [provider])
    assert first["records"] == {"test_cpi": 2}
    assert again["new_records"] == {"test_cpi": 0}
    assert len(list((tmp_path / "bronze/test_cpi/rw-20261120T1200").glob("*.meta.json"))) == 1
    rows = json.loads((tmp_path / "silver/nonrate/test_cpi.json").read_text(encoding="utf-8"))
    assert [row["month"] for row in rows] == ["2026-09", "2026-10"]


def test_sbv_interbank_reference_uses_its_own_date():
    body = """<p>Ngày áp dụng: 18/11/2026</p><table>
    <tr><td>Qua đêm</td><td>4,47</td><td>863.715,0</td></tr>
    <tr><td>6 Tháng</td><td>6,87 (*)</td><td>405,0 (*)</td></tr>
    <tr><td>Ghi chú:</td><td>(*) Tham chiếu doanh số và lãi suất ngày 17/11/2026</td></tr>
    </table>"""
    assert [row["date"] for row in parse_interbank(body.encode())] == ["2026-11-18", "2026-11-17"]


def test_sbv_liferay_monthly_fields_and_published_status():
    fields = dict(Date62813077={"content": "2026-08-31"}, soDuTongCong="20.489.434",
                  tocDoTangGiamTongCong="10,19")
    newer_unpublished = dict(status=1, id=99, title="Tháng 8 năm 2026", fields={**fields, "soDuTongCong": "1"})
    published = dict(status=0, id=42, title="Tháng 8 năm 2026", fields=fields)
    rows = parse_monthly(json.dumps({"articles": [newer_unpublished, published]}).encode(), "sbv_credit")
    assert len(rows) == 1
    assert rows[0]["month"] == "2026-08"
    assert rows[0]["credit_bn"] == 20489434
    assert rows[0]["credit_growth_ytd_pct"] == 10.19


def test_fiin_provider_fields_yield_derived_values_without_vendor_columns():
    raw = [{
        "ticker": "BID", "year": 2026, "quarter": 3,
        "ratios": {"AssetQualityComponent": {
            "ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans": 0.019,
            "LoanLossReservesToNPLs": 1.18,
        }, "GrowthComponent": {"AverageLoansGrowthPercentageYoY": 0.2}},
    }]
    row = quarterly(json.dumps(raw).encode())[0]
    assert row["bank"] == "BIDV"
    assert row["npl_pct"] == pytest.approx(1.9)
    assert row["coverage_pct"] == pytest.approx(118)
    assert row["loan_growth_pct"] == pytest.approx(20)
    assert row["roa_pct"] is None
    date_keys = [
        {"ticker": "BID", "timestamp": str(date(2026, 8, 1) + timedelta(days=day))} for day in range(61)
    ]
    close = pd.DataFrame(date_keys).assign(close=[100.0] * 60 + [90.0])
    rows = market_daily(close, pd.DataFrame(date_keys).assign(pb=1.5), pd.DataFrame(date_keys).assign(fn=1e9))
    assert rows[-1]["bank"] == "BIDV"
    assert rows[-1]["drawdown_pct"] == pytest.approx(-10)
    assert rows[-1]["foreign_net_20d_bn"] == 20
    assert rows[-1]["vol60_pct"] == pytest.approx(21.59248033)
    assert "close" not in rows[-1] and "fn" not in rows[-1]


def test_fiin_market_failure_does_not_mark_quarter_as_failed(tmp_path, monkeypatch):
    def market_unavailable(**options):
        raise TimeoutError("Vendor response")

    raw = [{"ticker": "VCB", "year": 2026, "quarter": 3, "ratios": {
        "AssetQualityComponent": {"ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans": 0.019},
    }}]
    fundamental = SimpleNamespace(get_ratios=lambda **options: raw)
    client = SimpleNamespace(FundamentalAnalysis=lambda: fundamental, Fetch_Trading_Data=market_unavailable)
    sdk = SimpleNamespace(FiinSession=lambda **options: SimpleNamespace(login=lambda: client))
    monkeypatch.setitem(sys.modules, "FiinQuantX", sdk)
    monkeypatch.setattr("vlkit.ratewatch.sources.fiin.dotenv_values",
                        lambda path: {"FIINQUANT_USERNAME": "test", "FIINQUANT_PASSWORD": "test"})
    provider = fiin_provider(tmp_path / ".env.local", ["VCB"], date(2026, 11, 20))
    log = ingest_sources(tmp_path, "rw-20261120T1436", [provider])
    assert log["records"] == {"fiin_quarter": 1}
    assert log["errors"] == {"fiin_market": "TimeoutError"}
