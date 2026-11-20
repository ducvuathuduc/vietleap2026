"""Normalise vendor frames into the NPL silver contracts."""

import pandas as pd

from .flatten import snake

PRICE_COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume", "value",
                 "bu", "sd", "fb", "fs", "fn"]
VALUATION_COLUMNS = ["ticker", "date", "pe", "pb"]
FOREIGN_VALUE_COLUMNS = [
    "foreign_buy_volume_total", "foreign_sell_volume_total", "foreign_buy_value_total",
    "foreign_sell_value_total", "foreign_net_volume_total", "foreign_net_value_total",
    "foreign_buy_volume_matched", "foreign_sell_volume_matched", "foreign_buy_value_matched",
    "foreign_sell_value_matched", "foreign_buy_volume_deal", "foreign_sell_volume_deal",
    "foreign_buy_value_deal", "foreign_sell_value_deal", "foreign_current_room",
    "foreign_total_room", "percent_foreign_total_room", "foreign_owned", "percent_foreign_owned",
]
FOREIGN_COLUMNS = ["ticker", "date", *FOREIGN_VALUE_COLUMNS]
KEYS = {
    "bank_quarter": ["ticker", "period"],
    "bank_annual": ["ticker", "period"],
    "price_daily": ["ticker", "date"],
    "valuation_daily": ["ticker", "date"],
    "foreign_daily": ["ticker", "date"],
}


def merge(existing, new, keys):
    """Union rows by key; the new run wins so revised vendor values replace older ones."""
    frames = [frame for frame in (existing, new) if frame is not None and not frame.empty]
    if not frames:
        return pd.DataFrame(columns=keys)
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.drop_duplicates(subset=keys, keep="last")
    return merged.sort_values(keys, ignore_index=True)


def _dated(frame):
    result = frame.copy()
    result.columns = [snake(str(column)) for column in result.columns]
    if "timestamp" in result:
        result["date"] = pd.to_datetime(result["timestamp"], format="mixed").dt.strftime("%Y-%m-%d")
        result = result.drop(columns="timestamp")
    if "date" in result:
        result["date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")
    result["ticker"] = result["ticker"].astype(str).str.upper()
    return result


def normalise_prices(frame):
    if frame.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    result = _dated(frame)
    for column in PRICE_COLUMNS[2:]:
        result[column] = pd.to_numeric(result.get(column), errors="coerce")
    result = result[[c for c in PRICE_COLUMNS if c in result]].dropna(subset=["date"])
    return result.drop_duplicates(KEYS["price_daily"], keep="last").sort_values(KEYS["price_daily"], ignore_index=True)


def normalise_valuation(frame):
    if frame.empty:
        return pd.DataFrame(columns=VALUATION_COLUMNS)
    result = _dated(frame)
    result = result[[c for c in VALUATION_COLUMNS if c in result]]
    return result.dropna(subset=["date"]).drop_duplicates(KEYS["valuation_daily"], keep="last") \
        .sort_values(KEYS["valuation_daily"], ignore_index=True)


def normalise_foreign(frame):
    if frame.empty:
        return pd.DataFrame(columns=FOREIGN_COLUMNS)
    result = _dated(frame)
    result = result[[c for c in FOREIGN_COLUMNS if c in result]]
    for column in FOREIGN_VALUE_COLUMNS:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    return result.dropna(subset=["date"]).drop_duplicates(KEYS["foreign_daily"], keep="last") \
        .sort_values(KEYS["foreign_daily"], ignore_index=True)
