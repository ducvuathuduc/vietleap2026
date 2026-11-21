import pandas as pd
import pytest

from vlkit.npl.scorecard import build_scorecard, summarize


def _panel(banks, periods, npl):
    rows = []
    for bank in banks:
        for period in periods:
            rows.append({"bank_code": bank, "period": period, "basis": "consolidated",
                         "npl_pct": npl[(bank, period)], "coverage_pct": 100.0,
                         "ldr_pct": 80.0, "nim_pct": 3.0, "loan_growth_yoy_pct": 10.0})
    return pd.DataFrame(rows)


def _stock(bank, period, **fields):
    rows = []
    for field, value in fields.items():
        flow = field in {"provision_used_writeoff", "provision_expense"}
        rows.append({"bank": bank, "period": period, "field": field, "value_vnd_bn": value,
                     "basis": "fiinquant_screening", "flow_basis": "quarterly" if flow else "point"})
    return rows


def test_screening_stocks_become_the_eight_asset_quality_ratios():
    panel = _panel(["VCB"], ["2025Q1", "2025Q2"], {("VCB", "2025Q1"): 5.0, ("VCB", "2025Q2"): 4.0})
    screening = pd.DataFrame(
        _stock("VCB", "2025Q1", loans_customer=100, group_2_watch=4, group_3_substandard=2,
               group_4_doubtful=1, group_5_loss=2, provision_total=10,
               provision_used_writeoff=1, provision_expense=1)
        + _stock("VCB", "2025Q2", loans_customer=110, group_2_watch=5, group_3_substandard=2,
                 group_4_doubtful=1, group_5_loss=1, provision_total=8,
                 provision_used_writeoff=2, provision_expense=3)
    )
    valuation = pd.DataFrame({"ticker": ["VCB", "VCB"], "date": ["2025-06-28", "2025-06-30"], "pb": [1.1, 1.2]})
    card = build_scorecard(panel, screening, valuation, None)
    row = next(item for item in card["rows"] if item["period"] == "2025Q2")
    values = row["values"]
    assert values["npl"] == pytest.approx(4 / 110)
    assert values["group2"] == pytest.approx(5 / 110)
    assert values["broad"] == pytest.approx(9 / 110)
    assert values["severity"] == pytest.approx(1 / 4)
    assert values["coverage"] == pytest.approx(8 / 4)
    assert values["provisions_to_loans"] == pytest.approx(8 / 110)
    assert values["writeoff_proxy"] == pytest.approx(2 / 100)
    assert values["credit_cost"] == pytest.approx(3 / ((100 + 110) / 2))
    assert values["pb"] == pytest.approx(1.2)
    assert row["composite"] is None and row["composite_status"] == "Thiếu dữ liệu"
    catalog = {item["id"]: item for item in card["indicators"]}
    assert catalog["npl"]["direction"] == "higher_worse"
    assert catalog["coverage"]["direction"] == "higher_better"
    assert catalog["pb"]["scored"] is False
    assert catalog["writeoff_proxy"]["unit"] == "ratio"


def test_npl_rank_can_look_better_than_the_asset_quality_composite():
    banks = [f"B{i}" for i in range(6)]
    rows = []
    for index, bank in enumerate(banks):
        weak = index == 0
        rows.append({
            "bank_code": bank, "period": "2025Q3",
            "npl": 3.0 if weak else 2.0 + index, "group2": 0.02, "broad": 0.05, "severity": 0.2,
            "coverage": 1.5, "provisions_to_loans": 0.04, "writeoff_proxy": 0.01, "credit_cost": 0.01,
            "nim": 0.03, "ldr": 0.8, "loan_growth_qoq": 0.02, "pb": 1.0, "d_npl": 0.1,
        })
        rows.append({
            "bank_code": bank, "period": "2025Q4",
            "npl": 1.0 if weak else 2.0 + index,
            "group2": 0.10 if weak else 0.01,
            "broad": 0.12 if weak else 0.03,
            "severity": 0.9 if weak else 0.2,
            "coverage": 0.2 if weak else 2.0,
            "provisions_to_loans": 0.01 if weak else 0.05,
            "writeoff_proxy": 0.05 if weak else 0.01,
            "credit_cost": 0.04 if weak else 0.01,
            "nim": 0.03, "ldr": 0.8, "loan_growth_qoq": 0.02, "pb": 1.0,
            "d_npl": -1.0 if weak else 0.2,
        })
    card = summarize(pd.DataFrame(rows))
    gap = next(item for item in card["rank_gaps"]["2025Q4"] if item["bank_code"] == "B0")
    assert gap["direction"] == "npl_looks_better"
    assert gap["places"] >= 5
    assert {"group2", "coverage"} <= set(gap["drivers"])
    quarter = next(item for item in card["by_quarter"] if item["period"] == "2025Q4")
    assert quarter["n"] == 6 and quarter["spearman"] is not None
    assert card["disagreement"]["n_fell"] == 1
    assert card["disagreement"]["share"] == pytest.approx(1.0)
    assert card["sensitivity"]["pca_spearman"] is not None
    assert "npl" in card["sensitivity"]["leave_one_out"]
    assert card["reading_vi"] and card["what_this_does_not_show_vi"]
