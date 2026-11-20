"""FiinQuant licensed ingestion. Vendor records are retained in bronze only."""
from contextlib import contextmanager
from datetime import timedelta
import json

import numpy as np
import pandas as pd
from dotenv import dotenv_values

from ..warehouse import TZ

BASE = "https://docs.fiinquant.vn/"
RATIO_DOC = BASE + "ham-va-cong-thuc/3.-phan-tich-co-ban-and-dinh-gia/3.2.-ham-chi-so-bao-cao-tai-chinh"
MARKET_DOC = BASE + "fiinquant-en/function-and-formula/historical-data-function"
MARKET_DERIVED = MARKET_DOC + "#ratewatch-rolling-statistics"
FIELDS = {
    "npl_pct": "AssetQualityComponent.ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans",
    "coverage_pct": "AssetQualityComponent.LoanLossReservesToNPLs",
    "ldr_pct": "LiquidityAndAssetsComponent.LDRPercentage",
    "roa_pct": "ProfitabilityComponent.ROA",
    "nim_pct": "ProfitabilityComponent.NIM",
    "loan_growth_pct": "GrowthComponent.AverageLoansGrowthPercentageYoY",
    "deposit_growth_pct": "GrowthComponent.AverageDepositGrowthPercentageYoY",
}


class FiinAuthenticationError(RuntimeError):
    """The SDK did not establish an authenticated session."""


def _records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def quarterly(raw):
    rows = pd.json_normalize(json.loads(raw))
    if rows.empty:
        return []
    result = pd.DataFrame({
        "bank": rows.ticker.replace({"BID": "BIDV"}),
        "quarter": rows.year.astype(str) + "Q" + rows.quarter.astype(str),
    })
    for name, field in FIELDS.items():
        column = "ratios." + field
        result[name] = 100 * pd.to_numeric(rows[column]) if column in rows else None
    return _records(result[result[list(FIELDS)].notna().any(axis=1)].drop_duplicates())


def _daily(frame, fields):
    date = pd.to_datetime(frame["timestamp"], format="mixed")
    if date.dt.tz is not None:
        date = date.dt.tz_convert(TZ)
    daily = frame.assign(date=date.dt.strftime("%Y-%m-%d")).set_index(["ticker", "date"])
    return daily[fields].apply(pd.to_numeric).sort_index()


def market_daily(close, valuation, foreign):
    prices = _daily(close, ["close"])
    valuation = _daily(valuation, ["pb"])
    foreign = _daily(foreign, ["fn"])
    daily = prices.join(valuation).join(foreign)
    results = []
    for ticker, group in daily.groupby(level="ticker"):
        group = group.loc[group.close > 0].copy()
        returns = np.log(group.close).diff()
        group["vol60_pct"] = 100 * np.sqrt(252) * returns.rolling(60).std()
        group["drawdown_pct"] = 100 * (group.close / group.close.cummax() - 1)
        group["foreign_net_20d_bn"] = group.fn.rolling(20).sum() / 1e9
        public = group[["pb", "vol60_pct", "drawdown_pct", "foreign_net_20d_bn"]].reset_index()
        public["bank"] = "BIDV" if ticker == "BID" else ticker
        results.extend(_records(public.drop(columns="ticker")))
    return results


def fiin_provider(credentials, tickers, today):
    def fiin():
        from tools.fiinquant.fetch_fiinquant import AuthError, HttpPolicy, quiet_sdk, frame_of

        class PoliteSdk(HttpPolicy):
            def claim(self):
                with self.lock:
                    if self.auth_status:
                        raise AuthError(f"HTTP {self.auth_status}")
                    now = self.clock()
                    previous = self.recent[-1] if self.recent else 0
                    wait = max(previous + 2, self.pause_until) - now
                    if wait <= 0:
                        self.recent.clear()
                        self.recent.append(now)
                        self.calls += 1
                    return wait

        config = dotenv_values(credentials)
        username, password = config.get("FIINQUANT_USERNAME"), config.get("FIINQUANT_PASSWORD")
        if not username or not password:
            raise ValueError("Thiếu thông tin đăng nhập FiinQuant")
        vendor_tickers = sorted({"BID" if ticker == "BIDV" else ticker for ticker in tickers})
        policy = PoliteSdk()

        @contextmanager
        def sdk_http():
            try:
                with quiet_sdk(), policy.install():
                    yield
            except AuthError:
                raise FiinAuthenticationError from None

        with sdk_http():
            from FiinQuantX import FiinSession

            client = FiinSession(username=username, password=password).login()
            try:
                fundamental = client.FundamentalAnalysis()
            except NameError:
                raise FiinAuthenticationError from None
            raw = fundamental.get_ratios(tickers=vendor_tickers, years=[today.year - 2, today.year - 1, today.year],
                                         quarters=[1, 2, 3, 4], type="consolidated")
        yield "fiin_quarter", RATIO_DOC, frame_of(raw).to_json(orient="records", date_format="iso").encode(), quarterly
        options = dict(tickers=vendor_tickers, from_date=str(today - timedelta(days=366)),
                       to_date=str(today - timedelta(days=1)))
        with sdk_http():
            close = frame_of(client.Fetch_Trading_Data(
                **options, realtime=False, adjusted=True, fields=["close"], by="1d",
            ).get_data())
        yield "fiin_raw_close", MARKET_DOC, close.to_json(orient="records", date_format="iso").encode(), []
        with sdk_http():
            pb = frame_of(client.MarketDepth().get_stock_valuation(**options))
        yield "fiin_raw_valuation", MARKET_DOC, pb.to_json(orient="records", date_format="iso").encode(), []
        with sdk_http():
            flow = frame_of(client.Fetch_Trading_Data(
                **options, realtime=False, adjusted=False, fields=["fn"], by="1d",
            ).get_data())
        yield "fiin_raw_foreign", MARKET_DOC, flow.to_json(orient="records", date_format="iso").encode(), []
        market_inputs = {"close": _records(close), "valuation": _records(pb), "foreign": _records(flow)}
        raw = json.dumps(market_inputs).encode()
        yield "fiin_market", MARKET_DERIVED, raw, lambda _: market_daily(close, pb, flow)

    return fiin
