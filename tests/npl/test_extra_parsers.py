import json

import pandas as pd

from vlkit.npl.ingest import extra_disclosure, extra_legal, extra_sbv, extra_tcb, extra_wdi

WDI = [
    {"page": 1, "pages": 1, "per_page": 100, "total": 4, "sourceid": "2", "lastupdated": "2026-11-11"},
    [
        {"indicator": {"id": "FB.AST.NPER.ZS", "value": "Bank nonperforming loans to total gross loans (%)"},
         "country": {"id": "VN", "value": "Viet Nam"}, "countryiso3code": "VNM", "date": "2024",
         "value": 2.5, "unit": "", "obs_status": "", "decimal": 1},
        {"indicator": {"id": "FB.AST.NPER.ZS", "value": "Bank nonperforming loans to total gross loans (%)"},
         "country": {"id": "VN", "value": "Viet Nam"}, "countryiso3code": "VNM", "date": "2023",
         "value": None, "unit": "", "obs_status": "", "decimal": 1},
    ],
]

ARTICLES = {"articles": [{"articleId": "1", "status": 0, "title": {"vi_VN": "Tin tháng 1 năm 2025"},
                          "fields": {"soDuTongCong": "15.701.965", "tocDoTangGiamTongCong": "0,55"},
                          "Date62813077": "2025-01-31T00:00:00+07:00"}]}
DEPOSITS = {"articles": [{"articleId": "2", "status": 0, "title": {"vi_VN": "Tin tiền gửi tháng 1 năm 2025"},
                          "fields": {"soDuTienGuiCuaDanCu": "7.188.027", "tocDoTangGiamTienGuiCuaDanCu": "1,74",
                                     "soDuTienGuiCuaCacTCKT": "7.433.824"},
                          "Date00760329": "2025-01-28T00:00:00+07:00"}]}


def test_wdi_pivots_both_indicators_and_drops_nulls():
    rows, lastupdated = extra_wdi.parse_wdi(json.dumps(WDI), "FB.AST.NPER.ZS")
    assert [row["year"] for row in rows] == [2024] and lastupdated == "2026-11-11"
    frame = extra_wdi.frame_from({"FB.AST.NPER.ZS": rows})
    assert frame.loc[0, "npl_to_gross_loans_pct"] == 2.5
    assert pd.isna(frame.loc[0, "capital_to_assets_pct"])
    assert list(frame.columns) == extra_wdi.COLUMNS


def test_wdi_rejects_a_payload_without_observations():
    try:
        extra_wdi.parse_wdi(json.dumps([{"page": 1}]), "FB.AST.NPER.ZS")
    except ValueError as exc:
        assert "unexpected WDI payload" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("a payload without observations must raise")


def test_sbv_merges_credit_and_deposits_and_derives_ldr():
    credit = extra_sbv.frame_from([{"month": "2025-01", "credit_bn": 15701965.17,
                                    "credit_growth_ytd_pct": 0.55}], [])
    assert credit.loc[0, "deposits_bn"] is pd.NA or pd.isna(credit.loc[0, "deposits_bn"])
    assert pd.isna(credit.loc[0, "ldr_pct"])
    frame = extra_sbv.frame_from([{"month": "2025-01", "credit_bn": 100.0, "credit_growth_ytd_pct": 0.5}],
                                 [{"month": "2025-01", "household_deposits_bn": 40.0,
                                   "organization_deposits_bn": 60.0, "deposit_growth_ytd_pct": 1.0}])
    assert frame.loc[0, "deposits_bn"] == 100.0
    assert frame.loc[0, "ldr_pct"] == 100.0
    assert list(frame.columns) == extra_sbv.COLUMNS


def test_sbv_url_filters_dates_for_credit_only():
    assert "Date62813077" in extra_sbv.url_for("sbv_credit", today="2026-11-21")
    assert "Date62813077" not in extra_sbv.url_for("sbv_deposit")


def test_legal_register_has_the_required_columns_and_sane_windows():
    frame = extra_legal.register(retrieved_at="2026-11-21T10:00:00", status=[200] * len(extra_legal.REGISTER))
    for column in ["ref", "title", "effective_from", "effective_to", "what_changes", "url", "retrieved_at"]:
        assert column in frame.columns
    assert frame["ref"].is_unique and frame["url"].str.startswith("https://congbao.chinhphu.vn/").all()
    dated = frame.dropna(subset=["effective_to"])
    assert date_ok(dated).all()


def date_ok(frame):
    return frame["effective_from"] < frame["effective_to"]


def test_legal_register_covers_the_named_circulars():
    refs = {row["ref"] for row in extra_legal.REGISTER}
    assert {"11/2021/TT-NHNN", "01/2020/TT-NHNN", "14/2021/TT-NHNN",
            "02/2023/TT-NHNN", "06/2024/TT-NHNN", "Luật 32/2024/QH15"} <= refs


def test_disclosure_feed_keeps_only_quarterly_statements_of_listed_banks():
    xml = """<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>
      <item><title>TCB - Báo cáo tài chính quý III/2024</title><link>https://hsx.vn/a</link>
        <pubDate>Thu, 24 Oct 2024 03:00:00 GMT</pubDate></item>
      <item><title>TCB - Nghị quyết HĐQT</title><link>https://hsx.vn/b</link>
        <pubDate>Thu, 24 Oct 2024 03:00:00 GMT</pubDate></item>
      <item><title>ZZZ - Báo cáo tài chính quý IV/2024</title><link>https://hsx.vn/c</link>
        <pubDate>Mon, 20 Jan 2025 03:00:00 GMT</pubDate></item>
    </channel></rss>"""
    frame = extra_disclosure.parse_feed(xml, ["TCB", "VCB"])
    assert frame.to_dict("records") == [{"ticker": "TCB", "period": "2024Q3",
                                        "published_at": "2024-10-24", "url": "https://hsx.vn/a"}]


def test_disclosure_period_reads_roman_and_digit_quarters():
    assert extra_disclosure.period_of("Báo cáo tài chính quý IV/2025", 2025) == "2025Q4"
    assert extra_disclosure.period_of("Báo cáo tài chính quý 2", 2025) == "2025Q2"
    assert extra_disclosure.period_of("Báo cáo tài chính năm 2025", 2025) is None


def test_tcb_case_reads_each_metric_from_its_own_page():
    pages = [
        "Thuyết minh\nCho vay khách hàng 412.345.678\nNợ đủ tiêu chuẩn 400.000.000\nNợ cần chú ý 5.000.000\n"
        "Nợ dưới tiêu chuẩn 4.000.000\nNợ nghi ngờ 2.000.000\nNợ có khả năng mất vốn 1.000.000",
        "Dự phòng rủi ro cho vay khách hàng 6.543.210\nDự phòng đã sử dụng để xử lý rủi ro 1.234.567",
    ]
    frame = extra_tcb.parse_pages(pages, "2024Q4", url="https://techcombank.com/x.pdf")
    values = dict(zip(frame["metric"], frame["value_bn_vnd"]))
    pages_of = dict(zip(frame["metric"], frame["page"]))
    assert values["loans_customer_bn_vnd"] == 412345678
    assert values["npl_group_1_current"] == 400000000
    assert values["npl_group_5_loss"] == 1000000
    assert values["provision_used_writeoff_bn_vnd"] == 1234567
    assert pages_of["provision_balance_bn_vnd"] == 2
    assert (frame["url"] == "https://techcombank.com/x.pdf").all()


def test_tcb_case_leaves_a_missing_metric_missing():
    frame = extra_tcb.parse_pages(["Cho vay khách hàng 1.000"], "2025Q1")
    assert list(frame["metric"]) == ["loans_customer_bn_vnd"]
    assert len(frame) == 1
