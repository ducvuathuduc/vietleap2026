import pytest

from vlkit.ratewatch.warehouse import bank_quarters


def test_npl_amount_and_coverage_compare_same_quarter_previous_year():
    rows = bank_quarters([
        dict(bank="STB", quarter="2025Q3", npl_pct=2, coverage_pct=90),
        dict(bank="STB", quarter="2026Q2", npl_pct=1.9, coverage_pct=92),
        dict(bank="STB", quarter="2026Q3", npl_pct=1.8, coverage_pct=95, loan_growth_pct=20),
    ])
    assert rows[1]["npl_amount_growth_pct"] is None
    assert rows[2]["npl_change_pp"] == pytest.approx(-0.2)
    assert rows[2]["npl_amount_growth_pct"] == pytest.approx(8)
    assert rows[2]["coverage_change_pp"] == 5
    assert rows[2]["denominator_flag"] is True
