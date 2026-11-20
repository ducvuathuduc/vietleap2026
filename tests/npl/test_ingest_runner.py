from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from vlkit.npl.ingest import runner


RECORDS = {
    "bank_quarter": [{"ticker": "BID", "year": 2026, "quarter": 3,
                      "ratios": {"ProfitabilityComponent": {"NIM": 0.02},
                                 "AssetQualityComponent": {
                                     "ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans": 0.018}}}],
    "bank_annual": [{"ticker": "BID", "year": 2025,
                     "ratios": {"ProfitabilityComponent": {"NIM": 0.03}}}],
}


class FakeCollector:
    def __init__(self):
        self.client = object()
        self.policy = SimpleNamespace(calls=0)

    def call(self, dataset, params, operation, doc_url="", want_raw=False):
        self.policy.calls += 1
        if want_raw:
            records = RECORDS[dataset]
            frame = pd.json_normalize(records)
            return frame, records
        if dataset == "price_daily":
            return pd.DataFrame({"ticker": ["BID"], "timestamp": ["2026-11-19"],
                                 "open": [1.0], "close": [1.0]})
        if dataset == "valuation_daily":
            return pd.DataFrame({"ticker": ["BID"], "timestamp": ["2026-11-19"], "pe": [7.0], "pb": [1.2]})
        return pd.DataFrame({"ticker": ["BID"], "timestamp": ["2026-11-19"],
                             "foreignNetValueTotal": [1.0], "foreignTotalRoom": [2.0]})


def test_run_lands_every_silver_table_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "vendor_banks", lambda ingest: {"BID"})
    ingest = FakeCollector()
    first = runner.run(lake=tmp_path, ingest=ingest,
                       datasets=("bank_quarter", "bank_annual", "price_daily",
                                 "valuation_daily", "foreign_daily", "report_calendar"))
    assert not first["errors"]
    assert first["banks"] == 24
    assert "BID" in first["tickers"]
    quarter = pd.read_parquet(tmp_path / "silver/bank_quarter.parquet")
    assert quarter.loc[0, "period"] == "2026Q3"
    assert quarter.loc[0, "npl"] == 0.018
    assert len(pd.read_parquet(tmp_path / "silver/price_daily.parquet")) == 1
    assert len(pd.read_parquet(tmp_path / "silver/foreign_daily.parquet")) == 1
    assert (tmp_path / "silver/report_calendar.csv").exists()
    assert (tmp_path / "state/watermarks.json").exists()
    assert any((tmp_path / "run_log").glob("*.json"))
    second = runner.run(lake=tmp_path, ingest=ingest, datasets=("bank_quarter",))
    assert not second["errors"]
    assert len(pd.read_parquet(tmp_path / "silver/bank_quarter.parquet")) == len(quarter)
    assert second["datasets"]["bank_quarter"]["new_records"] == 1


def test_silver_ignores_empty_vendor_response(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "vendor_banks", lambda ingest: {"BID"})
    ingest = FakeCollector()
    runner.run(lake=tmp_path, ingest=ingest, datasets=("price_daily",))
    assert (tmp_path / "silver/price_daily.parquet").exists()
