from contextlib import nullcontext

import pytest

from vlkit.npl.ingest.fiin import Collector, IngestError
from tools.fiinquant.fetch_fiinquant import AuthError, HttpPolicy


@pytest.fixture(autouse=True)
def stub_vendor_transport(monkeypatch):
    # Each operation below is a fake. The SDK's HTTP transports are never used.
    monkeypatch.setattr(HttpPolicy, "install", lambda self: nullcontext())


def fake_frame():
    import pandas as pd

    return pd.DataFrame({"ticker": ["BID"], "timestamp": ["2026-11-19"], "close": [1.0]})


def collector(tmp_path, sleeps, attempts=3):
    return Collector(credentials=tmp_path / "unused.env", lake=tmp_path / "lake", run_id="npl-test",
                     sleep=sleeps.append, attempts=attempts)


def test_retry_backs_off_then_stops(tmp_path):
    sleeps, calls = [], []
    ingest = collector(tmp_path, sleeps)

    def operation():
        calls.append(1)
        raise ConnectionError("boom")

    with pytest.raises(IngestError):
        ingest.call("price_daily", {"ticker": ["BID"]}, operation)
    assert len(calls) == 3
    assert sleeps == [1, 2]
    assert not (tmp_path / "lake" / "bronze" / "price_daily").exists()


def test_retry_recovers_on_third_attempt(tmp_path):
    sleeps, calls = [], []
    ingest = collector(tmp_path, sleeps)

    def operation():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError("slow")
        return fake_frame()

    frame = ingest.call("price_daily", {"ticker": ["BID"]}, operation)
    assert len(calls) == 3
    assert sleeps == [1, 2]
    assert frame.loc[0, "ticker"] == "BID"
    landed = list((tmp_path / "lake" / "bronze" / "price_daily" / "npl-test").glob("*.parquet"))
    assert len(landed) == 1


def test_authentication_error_is_not_retried(tmp_path):
    sleeps, calls = [], []
    ingest = collector(tmp_path, sleeps)

    def operation():
        calls.append(1)
        raise AuthError("HTTP 403")

    with pytest.raises(AuthError):
        ingest.call("price_daily", {}, operation)
    assert len(calls) == 1
    assert sleeps == []
