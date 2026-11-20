import pandas as pd

from vlkit.npl.ingest.flatten import CORE, flatten_ratios, snake
from vlkit.npl.ingest.silver import merge


PAYLOAD = [{
    "ticker": "BID",
    "year": 2026,
    "quarter": 3,
    "ratios": {
        "AssetQualityComponent": {
            "ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans": 0.0185,
            "LoanLossReservesToNPLs": 0.73,
        },
        "ProfitabilityComponent": {"NIM": 0.02},
        "ValuationRatios": {"PriceToBook": 1.18},
    },
    "NetInterestIncome": 17056049000000.0,
}]


def test_snake_case_splits_camel_case():
    assert snake("ProblemLoansAndLeases") == "problem_loans_and_leases"
    assert snake("LDRPercentage") == "ldr_percentage"


def test_flatten_nested_ratios_keeps_core_aliases():
    frame, field_map = flatten_ratios(PAYLOAD)
    assert frame.loc[0, "period"] == "2026Q3"
    assert frame.loc[0, "ticker"] == "BID"
    assert frame.loc[0, "npl"] == 0.0185
    assert frame.loc[0, "coverage"] == 0.73
    assert frame.loc[0, "nim"] == 0.02
    assert set(CORE) <= set(frame.columns)
    assert pd.isna(frame.loc[0, "roa"])


def test_field_map_names_every_vendor_leaf():
    frame, field_map = flatten_ratios(PAYLOAD)
    aliases = field_map.dropna(subset=["alias"])
    vendor = dict(zip(aliases["alias"], aliases["vendor_name"]))
    assert vendor["npl"] == "ratios.AssetQualityComponent.ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans"
    assert vendor["nim"] == "ratios.ProfitabilityComponent.NIM"
    leaves = {c for c in frame.columns if c not in ("ticker", "period", "year", "quarter", *CORE)}
    assert set(field_map["column"]) == leaves


def test_flatten_annual_rows_have_year_period():
    frame, _ = flatten_ratios([{"ticker": "VCB", "year": 2025, "ratios": {"ProfitabilityComponent": {"NIM": 0.03}}}])
    assert frame.loc[0, "period"] == "2025"
    assert pd.isna(frame.loc[0, "quarter"])


def test_merge_is_idempotent_and_keeps_latest():
    keys = ["ticker", "period"]
    first = pd.DataFrame({"ticker": ["BID", "VCB"], "period": ["2026Q3", "2026Q3"], "npl": [0.01, 0.02]})
    again = merge(first, first.copy(), keys)
    assert len(again) == 2
    revision = pd.DataFrame({"ticker": ["BID"], "period": ["2026Q3"], "npl": [0.03]})
    assert merge(first, revision, keys).set_index("ticker").loc["BID", "npl"] == 0.03
