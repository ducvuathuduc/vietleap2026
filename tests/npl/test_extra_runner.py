import json

import pandas as pd

from vlkit.npl.ingest import extra_runner


class Response:
    def __init__(self, content, status=200, url=""):
        self.content = content if isinstance(content, bytes) else content.encode("utf-8")
        self.status_code = status
        self.text = self.content.decode("utf-8")
        self.url = url

    def raise_for_status(self):
        pass


WDI = [{"page": 1, "total": 1, "lastupdated": "2026-11-11"},
       [{"indicator": {"id": "FB.AST.NPER.ZS"}, "country": {"id": "VN", "value": "Viet Nam"},
         "countryiso3code": "VNM", "date": "2024", "value": 2.5}]]
CREDIT = {"articles": [{"articleId": "1", "status": 0, "title": {"vi_VN": "Tin tháng 1 năm 2025"},
                        "fields": {"soDuTongCong": "100.000", "tocDoTangGiamTongCong": "0,5"},
                        "Date62813077": "2025-01-31"}]}
DEPOSITS = {"articles": [{"articleId": "2", "status": 0, "title": {"vi_VN": "Tin tiền gửi tháng 1 năm 2025"},
                          "fields": {"soDuTienGuiCuaDanCu": "40.000", "soDuTienGuiCuaCacTCKT": "60.000",
                                     "tocDoTangGiamTienGuiCuaDanCu": "1,0"},
                          "Date00760329": "2025-01-28"}]}
FEED_INDEX = """<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>
  <item><title>Công bố thông tin</title><link>https://api.hsx.vn/n/api/v1/feed/cbtt</link></item>
</channel></rss>"""
FEED = """<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>
  <item><title>VCB - Báo cáo tài chính quý III/2024</title><link>https://hsx.vn/vcb</link>
    <pubDate>Thu, 24 Oct 2024 03:00:00 GMT</pubDate></item>
</channel></rss>"""
TCB_PAGE = '<html><body>no statements linked</body></html>'


class FakeFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        payload = b"ok"
        if "worldbank" in url:
            payload = json.dumps(WDI).encode()
        elif "contentStructureId=10034332" in url:
            payload = json.dumps(CREDIT).encode()
        elif "contentStructureId=10038520" in url:
            payload = json.dumps(DEPOSITS).encode()
        elif url.endswith("/News/NewsFeed"):
            payload = FEED_INDEX.encode()
        elif url.endswith("/feed/cbtt"):
            payload = FEED.encode()
        elif "techcombank" in url:
            payload = TCB_PAGE.encode()
        return Response(payload, url=url)


def test_extra_run_writes_every_table_and_a_run_log(tmp_path):
    lake = tmp_path / "lake"
    log = extra_runner.run_extra(lake=lake, fetcher=FakeFetcher(), run_id="extra-test",
                                 banks=extra_runner.BANKS, tinyfetch=lambda url: None)
    assert log["run_id"] == "extra-test"
    assert log["elapsed_s"] >= 0 and log["http_calls"] > 0
    assert set(log["datasets"]) == set(extra_runner.DATASETS)
    wdi = pd.read_parquet(lake / "silver/wdi_bank.parquet")
    assert wdi.loc[0, "iso3"] == "VNM" and wdi.loc[0, "npl_to_gross_loans_pct"] == 2.5
    sbv = pd.read_parquet(lake / "silver/sbv_system.parquet")
    assert sbv.loc[0, "ldr_pct"] == 100.0
    legal = pd.read_csv(lake / "silver/legal_register.csv")
    assert len(legal) == len(extra_runner.extra_legal.REGISTER)
    assert list(legal.columns)[-1] == "http_status"
    disclosure = pd.read_csv(lake / "silver/disclosure_dates.csv")
    assert disclosure.loc[0, "ticker"] == "VCB" and disclosure.loc[0, "period"] == "2024Q3"
    tcb = pd.read_csv(lake / "silver/case_tcb.csv")
    assert list(tcb.columns) == ["quarter", "metric", "value_bn_vnd", "page", "url"]
    assert (lake / "run_log/extra-test.json").exists()
    marks = json.loads((lake / "state/watermarks.json").read_text(encoding="utf-8"))
    assert {"extra_wdi", "extra_sbv", "extra_legal", "extra_disclosure", "extra_tcb"} <= set(marks)
    assert log["datasets"]["tcb"]["rows"] == 0
    assert log["errors"]["tcb"]["2024Q3"] == "no statement PDF linked on the investor page"


def test_extra_run_reports_a_failing_source_without_losing_the_others(tmp_path):
    class Broken(FakeFetcher):
        def get(self, url, params=None, timeout=None):
            from vlkit.npl.ingest.extra_landing import FetchError

            if "worldbank" in url:
                raise FetchError("GET worldbank: transport error after 3 attempts")
            return super().get(url, params=params)

    lake = tmp_path / "lake"
    log = extra_runner.run_extra(lake=lake, fetcher=Broken(), run_id="extra-broken",
                                 banks=extra_runner.BANKS, tinyfetch=lambda url: None)
    assert "wdi" in log["errors"]
    assert pd.read_parquet(lake / "silver/sbv_system.parquet").shape[0] == 1
    assert log["datasets"]["disclosure"]["rows"] == 1
