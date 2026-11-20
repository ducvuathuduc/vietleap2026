"""World Bank WDI benchmark: bank NPL to gross loans and bank capital to assets for VN and ASEAN peers."""

import json

import pandas as pd

from .extra_landing import FetchError, land, write_silver

API = "https://api.worldbank.org/v2"
INDICATORS = {
    "FB.AST.NPER.ZS": "npl_to_gross_loans_pct",
    "FB.BNK.CAPA.ZS": "capital_to_assets_pct",
}
COUNTRIES = {
    "VNM": "Viet Nam", "THA": "Thailand", "IDN": "Indonesia", "MYS": "Malaysia", "PHL": "Philippines",
    "KHM": "Cambodia", "LAO": "Lao PDR", "MMR": "Myanmar", "SGP": "Singapore", "BRN": "Brunei",
}
COLUMNS = ["iso3", "country", "year", *INDICATORS.values(), "source_lastupdated"]


def url_for(code, economy="VNM"):
    """One country at a time: this is the only query shape the free TinyFetch fallback serves."""
    return f"{API}/country/{economy}/indicator/{code}?format=json&per_page=100"


def parse_wdi(payload, code):
    """WDI JSON -> list of {iso3, country, year, value} (null observations are skipped)."""
    body = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
    if not isinstance(body, list) or len(body) < 2 or not isinstance(body[1], list):
        raise ValueError(f"unexpected WDI payload for {code}")
    header, observations = body[0], body[1]
    rows = []
    for item in observations:
        if item.get("value") is None:
            continue
        rows.append({"iso3": item["countryiso3code"], "country": item["country"]["value"],
                     "year": int(item["date"]), code: float(item["value"])})
    return rows, header.get("lastupdated")


def frame_from(series):
    """Pivot the per-indicator long rows into one wide country x year table."""
    rows = []
    for code, records in series.items():
        for record in records:
            rows.append({"iso3": record["iso3"], "country": record["country"], "year": record["year"],
                         "indicator": code, "value": record.get(code),
                         "lastupdated": record.get("lastupdated")})
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    long = pd.DataFrame(rows)
    by_year = long.pivot_table(index=["iso3", "country", "year"], columns="indicator", values="value",
                               aggfunc="last").reset_index()
    by_year = by_year.rename(columns=INDICATORS)
    for name in INDICATORS.values():
        if name not in by_year:
            by_year[name] = pd.NA
    lastupdated = long.get("lastupdated", pd.Series(dtype=object)).dropna()
    by_year["source_lastupdated"] = lastupdated.max() if not lastupdated.empty else None
    return by_year[COLUMNS].sort_values(["iso3", "year"], ignore_index=True)


def run(lake, fetcher, run_id, tinyfetch=None):
    """Fetch both indicators country by country, land the raw JSON in bronze, write silver/wdi_bank.parquet."""
    series, lastupdated, errors = {}, {}, {}
    direct = True
    for code in INDICATORS:
        for economy in COUNTRIES:
            url = url_for(code, economy)
            try:
                if not direct:
                    raise FetchError("api.worldbank.org unreachable from this network")
                payload = fetcher.get(url, timeout=10).content
            except Exception as exc:  # api.worldbank.org is unreachable from some networks
                direct = False
                if tinyfetch is None:
                    errors[f"{code} {economy}"] = f"{type(exc).__name__}: {exc}"[:120]
                    continue
                try:
                    payload = tinyfetch(url)
                except Exception as fallback_exc:
                    errors[f"{code} {economy}"] = f"tinyfetch: {type(fallback_exc).__name__}"[:120]
                    continue
            try:
                records, stamp = parse_wdi(payload, code)
            except ValueError as exc:
                errors[f"{code} {economy}"] = str(exc)[:120]
                continue
            land(lake, run_id, "wdi", f"{code}-{economy}", payload, "json",
                 {"url": url, "indicator": code, "economy": economy, "records": len(records)})
            series.setdefault(code, []).extend(
                {**record, "lastupdated": stamp} for record in records)
            lastupdated[code] = stamp
    frame = frame_from(series)
    write_silver(lake, "wdi_bank.parquet", frame,
                 {"sources": [url_for(code) for code in INDICATORS], "lastupdated": lastupdated})
    stats = {"rows": len(frame), "indicators": len(series),
             "iso3": int(frame["iso3"].nunique()) if len(frame) else 0,
             "years": [int(frame["year"].min()), int(frame["year"].max())] if len(frame) else None}
    if errors:
        stats["errors"] = errors
    return frame, stats
