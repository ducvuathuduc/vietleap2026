"""Tests for the FiinQuant connector — mock mode only (no credentials, no wheel)."""
import pandas as pd

from tools.fiinquant import fetch_fiinquant as fq

TICKERS = ["VNINDEX", "VN30", "HPG", "VCB"]


def test_mock_frame_shape():
    df = fq.build_mock_frame(TICKERS, "2026-01-01")
    assert set(TICKERS) <= set(df["ticker"])
    assert list(df.columns) == ["ticker", "timestamp", "open", "high", "low", "close",
                                "volume", "value", "bu", "sd", "fb", "fs", "fn"]
    assert (df["high"] >= df["low"]).all() and (df["close"] > 0).all()


def test_mock_run_writes_readable_bronze(tmp_path):
    out = tmp_path / "fiinquant"
    assert fq.main(["--mock", "--from-date", "2026-01-01", "--tickers", *TICKERS,
                    "--out", str(out)]) == 0
    pq = out / "fiinquant__trading_daily.parquet"
    sidecar = out / "fiinquant__trading_daily.run.json"
    assert pq.exists() and sidecar.exists()
    df = pd.read_parquet(pq)
    assert len(df) > 0 and set(TICKERS) <= set(df["ticker"])
    assert df["_mock"].all() and df["_row_hash"].notna().all()
    assert df["_row_hash"].is_unique  # de-duplicated on ticker+timestamp


def test_mock_run_idempotent(tmp_path):
    out = tmp_path / "fiinquant"
    fq.main(["--mock", "--from-date", "2026-01-01", "--tickers", *TICKERS, "--out", str(out)])
    first = pd.read_parquet(out / "fiinquant__trading_daily.parquet")
    fq.main(["--mock", "--from-date", "2026-01-01", "--tickers", *TICKERS, "--out", str(out)])
    second = pd.read_parquet(out / "fiinquant__trading_daily.parquet")
    assert len(first) == len(second)
    assert set(first["_row_hash"]) == set(second["_row_hash"])


def test_real_mode_without_credentials_fails_cleanly(tmp_path, monkeypatch):
    monkeypatch.delenv("FIINQUANT_USERNAME", raising=False)
    monkeypatch.delenv("FIINQUANT_PASSWORD", raising=False)
    assert fq.main(["--from-date", "2026-01-01", "--out", str(tmp_path)]) == 1
    assert not list(tmp_path.glob("*.parquet"))
