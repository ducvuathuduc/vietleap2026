import numpy as np
import pandas as pd
import pytest

from vlkit.npl.decompose import decompose_screening


def _stock(bank, period, groups, loans=None, writeoff=None):
    rows = []
    for field, value in zip(
        ["group_1_current", "group_2_watch", "group_3_substandard", "group_4_doubtful", "group_5_loss"],
        groups,
    ):
        rows.append(dict(bank=bank, period=period, field=field, flow_basis="point", value_vnd_bn=value))
    rows.append(dict(bank=bank, period=period, field="loans_customer", flow_basis="point",
                     value_vnd_bn=sum(groups) if loans is None else loans))
    if writeoff is not None:
        rows.append(dict(bank=bank, period=period, field="provision_used_writeoff", flow_basis="quarterly",
                         value_vnd_bn=writeoff))
    return rows


def test_denominator_plus_numerator_equals_the_change():
    frame = pd.DataFrame([
        *_stock("AAA", "2025Q3", [80, 10, 5, 3, 2], writeoff=1),
        *_stock("AAA", "2025Q4", [90, 8, 4, 2, 1], writeoff=1.05),
        *_stock("BBB", "2025Q3", [50, 5, 2, 2, 1]),
        *_stock("BBB", "2025Q4", [40, 6, 3, 3, 3], writeoff=-2),
    ])
    result = decompose_screening(frame)
    assert result["rows"]
    for row in result["rows"]:
        assert row["denominator_pp"] + row["numerator_pp"] == pytest.approx(row["d_npl_pp"])
        growth = row["loan_growth_qoq_pct"] / 100
        previous = row["npl_pct"] - row["d_npl_pp"]
        assert row["denominator_pp"] == pytest.approx(-previous * growth / (1 + growth))
    q4 = next(item for item in result["by_quarter"] if item["quarter"] == "Q4")
    assert q4["n"] == 2
    assert q4["share_falling_pct"] == pytest.approx(50)
    aaa = next(row for row in result["rows"] if row["bank_code"] == "AAA")
    assert aaa["writeoff_pct_loans"] == pytest.approx(1.05 / 105 * 100)
    assert aaa["g2_pct"] == pytest.approx(8 / 105 * 100)


def test_a_repeated_quarter_is_quarantined_and_a_small_real_change_is_kept():
    copied = [100, 10, 4, 3, 2]
    changed = [100, 10, 4, 3, 2]
    moved = [110, 9, 5, 3, 2]
    frame = pd.DataFrame([
        *_stock("TCB", "2025Q3", copied),
        *_stock("TCB", "2025Q4", copied),
        *_stock("CTG", "2025Q3", changed),
        *_stock("CTG", "2025Q4", moved),
    ])
    result = decompose_screening(frame)
    assert result["q4_2025_check"]["quarantine"] == ["TCB"]
    assert "CTG" not in result["q4_2025_check"]["quarantine"]
    assert all(row["bank_code"] != "TCB" for row in result["rows"])
    assert any(row["bank_code"] == "CTG" and row["period"] == "2025Q4" for row in result["rows"])
    assert result["q4_2025_check"]["artefact"] is True
