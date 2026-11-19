import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tools.fiinquant import fetch_fiinquant as fq


FIXTURES = Path(__file__).parent / "fixtures" / "fiinquant"


def fixture(name):
    return pd.read_csv(FIXTURES / f"{name}.csv", dtype={"taxCode": str})


@pytest.mark.parametrize(("dataset", "required"), [
    ("roster", "ticker exchangeCode organizationName icbNameL2 snapshot_date"),
    ("bars", "ticker timestamp open high low close volume value bu sd fb fs fn"),
    ("foreign", "ticker timestamp foreignBuyVolumeTotal foreignNetValueTotal foreignCurrentRoom"),
    ("valuation", "ticker timestamp pe pb scope"),
    ("bank_ratios", "ticker year quarter ratios.ProfitabilityComponent.NIM ratios.ValuationRatios.PriceToBook"),
    ("breadth", "ticker tradingDate index_code kind totalStockUpPrice rank contributionPercent"),
    ("vn30_weights", "ticker timestamp snapshot_date FreeFloat OutstandingShare Stock_Ratio"),
    ("investor_flow", "ticker timestamp proprietaryNetTotalMatchValue localIndividualNetMatchVolume"),
])
def test_dataset_contract(dataset, required, tmp_path):
    assert fq.main([dataset, "--mock", "--out", str(tmp_path)]) == 0
    parquet, = (tmp_path / dataset).glob("*.parquet")
    frame = pd.read_parquet(parquet)
    columns = [name.replace("Stock_Ratio", "Stock Ratio") for name in required.split()]
    assert set(columns) <= set(frame.columns)
    assert not frame.empty
    if dataset == "valuation":
        assert set(frame["scope"]) == {"stock", "sector", "index"}
    if dataset == "breadth":
        assert set(frame["kind"]) == {"breadth", "topGainers", "topLosers"}


def test_landing_replaces_duplicate_keys_with_latest_raw_row(tmp_path):
    initial = fixture("bars")
    assert initial.iloc[0]["timestamp"] == "2025-05-20 00:00"
    revision = initial.iloc[[0]].assign(close=123.456789)
    fq.land(tmp_path, "bars", initial, {}, "first", "2026-11-19T10:00:00+07:00", "mock", 0, 1)
    fq.land(tmp_path, "bars", revision, {}, "second", "2026-11-19T11:00:00+07:00", "mock", 0, 1)
    active = pd.concat([pd.read_parquet(p) for p in (tmp_path / "bars").glob("*.parquet")])
    assert len(active) == len(initial)
    assert not active.duplicated(["ticker", "timestamp"]).any()
    updated = active.loc[active["timestamp"] == "2025-05-20 00:00"].iloc[0]
    assert updated["close"] == 123.456789


def test_watermark_rewinds_five_observed_sessions_per_ticker():
    a = pd.DataFrame({"ticker": "A", "timestamp": [
        "2026-11-02", "2026-11-03", "2026-11-05", "2026-11-09",
        "2026-11-10", "2026-11-12", "2026-11-13"]})
    b = pd.DataFrame({"ticker": "B", "timestamp": ["2026-11-16"]})
    starts = fq.starts_by_ticker(pd.concat([a, b]), ["A", "B", "C"], "2021-11-19")
    assert starts == {"A": "2026-11-05", "B": "2021-11-19", "C": "2021-11-19"}


def test_sidecar_and_run_log_describe_written_file(tmp_path):
    assert fq.main(["bars", "--mock", "--universe", "ACB", "--out", str(tmp_path)]) == 0
    parquet, = (tmp_path / "bars").glob("*.parquet")
    meta = json.loads(parquet.with_suffix(".json").read_text(encoding="utf-8"))
    df = pd.read_parquet(parquet)
    assert meta["params"]["universe"] == "ACB"
    assert meta["dataset"] == "bars" and meta["run_id"] in parquet.stem
    assert meta["fetched_at"].endswith("+07:00") and meta["fetched_at"][:10] in parquet.stem
    assert meta["sha256"] == hashlib.sha256(parquet.read_bytes()).hexdigest()
    assert meta["rows"] == len(df) and meta["columns"] == list(df)
    assert meta["http_calls"] == 0 and meta["sdk_version"] == "mock" and meta["duration_s"] >= 0
    record, = [json.loads(line) for line in (tmp_path / "_runs.jsonl").read_text().splitlines()]
    assert record["run_id"] == meta["run_id"] and record["errors"] == [] and record["rows"] == len(df)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds

    async def asleep(self, seconds):
        self.sleep(seconds)


def test_http_rate_limit_shared_between_sync_and_async_requests():
    clock = FakeClock()
    http = fq.HttpPolicy(clock.now, clock.sleep, clock.asleep)
    sent = []

    def request():
        sent.append(clock.now())
        return SimpleNamespace(status=200, headers={})

    async def async_request():
        return request()

    for _ in range(6):
        http.send(request)
        asyncio.run(http.request(async_request))
    assert len(sent) == http.calls == 12
    assert all(sent[i + 10] - sent[i] >= 1 for i in range(2))


@pytest.mark.parametrize("status", [401, 403])
def test_auth_failure_aborts_without_retry(status):
    clock = FakeClock()
    http = fq.HttpPolicy(clock.now, clock.sleep, clock.asleep)
    with pytest.raises(fq.AuthError):
        http.send(lambda: SimpleNamespace(status_code=status, headers={"Retry-After": "10"}))
    assert http.calls == 1 and clock.now() == 0


def test_retry_honors_retry_after_then_uses_exponential_backoff():
    clock = FakeClock()
    http = fq.HttpPolicy(clock.now, clock.sleep, clock.asleep)
    attempts = []

    def send():
        attempts.append(clock.now())
        status = [429, 503, 200][len(attempts) - 1]
        return SimpleNamespace(status_code=status, headers={"Retry-After": "4"} if status == 429 else {})

    assert http.send(send).status_code == 200
    assert attempts == [0, 4, 6]


def test_roster_removes_wrong_venue_and_reports_extras():
    frame = fixture("roster")
    expected = {("ACV", "UPCOM"), ("MISSING", "HNX")}
    report = {}
    result = fq.filter_roster(frame, expected, report)
    assert list(result["ticker"]) == ["ACV"]
    assert result.iloc[0]["exchangeCode"] == "UPCoM"
    assert set(report["dropped_tickers"]) == set(frame["ticker"]) - {"ACV"}
    assert report["missing_tickers"] == ["MISSING"]


def test_breadth_uses_provider_trading_date_for_contributions():
    source = fixture("breadth")
    result = fq.breadth_frame(source, {"topGainers": fixture("contribution")})
    constituent = result.loc[result["kind"] == "topGainers"]
    assert set(constituent["tradingDate"]) == {"2026-11-19 00:00"}
    assert set(constituent["index_code"]) == {"VNINDEX"}
    assert set(constituent["ticker"]) == set(fixture("contribution")["ticker"])


class FixtureClient:
    """The SDK interface backed by the probe responses instead of HTTP."""

    def TickerList(self, *, ticker):
        return {"VNINDEX": ["APG"], "HNXIndex": ["HNX"], "UpcomIndex": ["ACV"],
                "BANKS_L2": ["ACB", "BID"], "VN30": ["ACB", "HPG"]}[ticker]

    def BasicInfor(self, *, tickers):
        assert tickers == ["ACV", "APG", "HNX"]
        return SimpleNamespace(get=lambda: fixture("roster"))

    def Fetch_Trading_Data(self, *, tickers, from_date, to_date, by, realtime, adjusted, fields):
        assert by == "1d" and not realtime and adjusted
        assert fields == ["open", "high", "low", "close", "volume", "value", "bu", "sd", "fb", "fs", "fn"]
        assert from_date == "2021-11-19" and to_date == "2026-11-19"
        return SimpleNamespace(get_data=lambda: fixture("bars").loc[lambda frame: frame.ticker.isin(tickers)])

    def PriceStatistics(self):
        def foreign(*, tickers, from_date, to_date, time_filter):
            assert tickers == ["ACB", "BID", "HPG"]
            assert from_date == "2021-11-19" and to_date == "2026-11-19" and time_filter == "Daily"
            return SimpleNamespace(get_data=lambda: fixture("foreign"))

        def investors(*, tickers, from_date, to_date):
            assert tickers == ["ACB", "BID", "HPG"]
            assert from_date == "2026-10-22" and to_date == "2026-11-19"
            return fixture("investor_flow")

        return SimpleNamespace(get_foreign=foreign, get_value_by_investor=investors)

    def MarketDepth(self):
        def stock(*, tickers, from_date, to_date):
            assert tickers == ["ACB", "BID", "HPG"]
            return fixture("valuation")

        def sector(*, tickers, level, from_date, to_date):
            assert level == 2
            assert len(tickers) == 19
            assert "BANKS" in tickers and "INDUSTRIAL_GOODS_AND_SERVICES" in tickers
            return fixture("valuation_sector")

        def index(*, tickers, from_date, to_date):
            assert set(tickers) == {"VNINDEX", "VN30", "HNXIndex", "UpcomIndex"}
            return fixture("valuation_index")

        return SimpleNamespace(get_stock_valuation=stock, get_sector_valuation=sector, get_index_valuation=index)

    def FundamentalAnalysis(self):
        def ratios(*, tickers, years, quarters, type):
            assert tickers == ["ACB", "BID"] and type == "consolidated"
            if years == [2025]:
                assert quarters == [1, 2, 3, 4]
                return fixture("bank_ratios")
            return []

        return SimpleNamespace(get_ratios=ratios)

    def MarketBreadth(self):
        return SimpleNamespace(get=lambda *, tickers: fixture("breadth"))

    def MoneyFlow(self):
        return SimpleNamespace(get_contribution=lambda **kwargs: fixture("contribution"))

    def Rebalance(self):
        return SimpleNamespace(get=lambda *, Budget, Ticker: fixture("vn30_weights"))


@pytest.mark.parametrize("dataset", [
    "roster", "bars", "foreign", "valuation", "bank_ratios", "breadth", "vn30_weights", "investor_flow",
])
def test_sdk_payload_contract_survives_extraction(dataset):
    # Retain every provider column in each fixture and keep provider values untouched.
    extractor = fq.Extractor(FixtureClient(), "2026-11-19", None, "ACB" if dataset == "bars" else None)
    gaps = {}
    actual = extractor.extract(dataset, pd.DataFrame(), gaps)
    source = fixture(dataset)
    assert not actual.empty
    assert set(source) - ({"index"} if dataset == "breadth" else set()) <= set(actual)
    if dataset == "roster":
        assert actual.iloc[0]["taxCode"] == "0311638525"
        assert set(actual.ticker) == {"ACV", "APG"}
    elif dataset == "bank_ratios":
        assert 2015 in gaps["empty_years"] and 2026 in gaps["empty_years"]
        assert actual.iloc[0]["ratios.ProfitabilityComponent.NIM"] == source.iloc[0]["ratios.ProfitabilityComponent.NIM"]
    elif dataset in {"foreign", "bars", "vn30_weights", "investor_flow"}:
        assert actual.iloc[0]["timestamp"] == source.iloc[0]["timestamp"]


def test_full_roster_snapshot_removes_stale_members_for_same_date(tmp_path):
    initial = fixture("roster").assign(snapshot_date="2026-11-19")
    fq.land(tmp_path, "roster", initial, {}, "first", "2026-11-19T10:00:00+07:00", "mock", 0, 1)
    fq.land(tmp_path, "roster", initial.iloc[[0]], {}, "second", "2026-11-19T11:00:00+07:00", "mock", 0, 1)
    assert list(fq.prior_frame(tmp_path, "roster")["ticker"]) == ["ACV"]


def test_sector_lookup_uses_unsuffixed_icb_codes():
    class SectorClient(FixtureClient):
        def MarketDepth(self):
            methods = super().MarketDepth()

            def sector(*, tickers, level, from_date, to_date):
                assert level == 2
                if "INDUSTRIAL_GOODS_AND_SERVICES" in tickers:
                    return fixture("valuation_sector").assign(ticker="INDUSTRIAL_GOODS_AND_SERVICES_L2")
                return fixture("valuation_sector")

            methods.get_sector_valuation = sector
            return methods

    gaps = {}
    extractor = fq.Extractor(SectorClient(), "2026-11-19", None, None)
    result = extractor.extract("valuation", pd.DataFrame(), gaps)
    assert "INDUSTRIAL_GOODS_AND_SERVICES_L2" in set(result.loc[result.scope == "sector", "ticker"])
    assert "INDUSTRIAL_GOODS_AND_SERVICES" not in gaps["valuation_sector_missing"]
