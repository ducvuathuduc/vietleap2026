import numpy as np
import pandas as pd
import pytest

from vlkit.npl.decoder import build_decoder
from vlkit.npl.real_data import clean_quarters, read_silver
from vlkit.npl.real_models import decision_rule
from test_real_pipeline import silver


def test_decoder_signal_gates_ratios_and_incomplete_periods(silver):
    panel, _ = clean_quarters(pd.read_parquet(silver / "bank_quarter.parquet"))
    _, seasonal = decision_rule(panel)
    seasonal.loc[seasonal.period.eq("2025Q4"), ["expected_change_pp", "lo80_pp", "hi80_pp"]] = [-1., -.1, .1]
    amounts = {
        "2024Q4": [100, 4, 11, 22, 1],
        "2025Q1": [100, 5, 10, 20, 1],
        "2025Q2": [100, 6, 9, 9, 3],
        "2025Q3": [100, 5, 8, 16, 1],
        "2025Q4": [100, 4, 7, 14, .5],
        "2026Q1": [100, None, 6, 12, .4],
        "2026Q2": [100, 4, 7, 14, .4],
    }
    vcb = panel.bank_code.eq("VCB")
    for period, values in amounts.items():
        panel.loc[vcb & panel.period.eq(period), "npl_pct"] = values[2]
        panel.loc[vcb & panel.period.eq(period), "coverage_pct"] = abs(values[3]) / values[2] * 100
    for field in ["npl_pct", "coverage_pct"]:
        panel.loc[vcb, f"d_{field}"] = panel.loc[vcb, field].diff()
    fields = ["customer_loans", "group2_loans", "groups345_loans", "provision_closing", "writeoffs"]
    notes = pd.DataFrame([
        dict(bank="VCB", period=period, field=field, value_vnd_bn=value, basis="consolidated",
             grade="verified", page=4, source_url="https://test.com/notes.pdf")
        for period, values in amounts.items() for field, value in zip(fields, values) if value is not None
    ])
    result = build_decoder(panel, seasonal, notes)
    assert result["periods"] == ["2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"]
    assert len(result["focus"]) == 48
    assert len(result["rows"]) == 184
    rows = {row["period"]: row for row in result["focus"] if row["bank_code"] == "VCB"}
    q2 = rows["2025Q2"]
    assert [signal["id"] for signal in q2["signals"]] == ["S1", "S2", "S3"]
    assert q2["status"] == "review"
    assert q2["npl_formation"] == pytest.approx(.02)
    assert q2["broad_problem_ratio"] == pytest.approx(.15)
    assert q2["lagged_coverage"] == pytest.approx(2)
    assert q2["coverage"] == pytest.approx(1)
    assert q2["loans_vnd_bn"] == 100 and q2["writeoff_vnd_bn"] == 3
    assert q2["coverage_source"] == "notes"
    assert rows["2025Q3"]["status"] == "clean"
    assert [signal["id"] for signal in rows["2025Q4"]["signals"]] == ["S4"]
    assert rows["2025Q4"]["status"] == "clean"
    assert rows["2025Q4"]["layers"]["accounting"] == []
    assert rows["2025Q4"]["layers"]["data_quality"] == "đủ"
    assert "S4" in rows["2025Q4"]["layers"]["context"]
    assert rows["2026Q1"]["status_vi"] == "Thiếu dữ liệu"
    assert "delta_g2_ratio" in rows["2026Q1"]["missing_inputs"]
    assert rows["2026Q2"]["status"] == "not_applicable"
    assert result["regression"]["notes"]["full"]["n"] > 0
    assert result["regression"]["notes"]["full"]["clusters"] == 1


def test_vendor_reduced_fit_uses_lagged_coverage_and_preserves_missing_fields(silver):
    panel, _ = clean_quarters(pd.read_parquet(silver / "bank_quarter.parquet"))
    _, seasonal = decision_rule(panel)
    result = build_decoder(panel, seasonal, None)
    fit = result["regression"]["fiinquant"]
    assert fit["n_panel"] == 184 and fit["grid_n"] == 184
    assert fit["full"]["n"] == 0
    assert fit["available"]["n"] == 176
    assert set(fit["available"]["terms"]) == {"loan_growth", "lagged_coverage"}
    assert all(term["ci95"] and term["wild_p"] is not None for term in fit["available"]["terms"].values())
    assert result["regression"]["notes"]["full"]["n"] == 0
    rows = result["rows"]
    assert result["signal_availability"]["S2"]["eligible"] == 0
    assert result["signal_availability"]["S3"]["eligible"] > 0
    assert all(row["writeoff_ratio"] is None and row["broad_problem_ratio"] is None for row in rows)
    assert all(row["status"] != "clean" for row in rows)
    for row in rows:
        source = panel.loc[panel.bank_code.eq(row["bank_code"]) & panel.period.eq(row["period"])].iloc[0]
        assert row["npl_ratio"] == pytest.approx(source.npl_pct / 100)
        assert row["coverage"] == pytest.approx(source.coverage_pct / 100)
        assert row["nim"] == pytest.approx(source.nim_pct / 100)
        assert row["loan_growth"] == pytest.approx(source.loan_growth_yoy_pct / 100)
        if source.d_npl_pct < 0:
            assert row["delta_npl_ratio"] == pytest.approx(source.d_npl_pct / 100)
            assert row["status"] == "missing"


def test_screening_fills_decoder_and_pdf_is_only_a_fallback():
    panel, _ = clean_quarters(pd.DataFrame({"ticker": ["VCB"] * 3,
        "period": ["2025Q1", "2025Q2", "2025Q3"], "npl_pct": [5., 4., 3.], "coverage_pct": [100.] * 3}))
    _, seasonal = decision_rule(panel)
    screening = pd.DataFrame([
        dict(bank="VCB", period=period, field=field, value_vnd_bn=value, basis="fiinquant_screening",
             flow_basis="quarterly" if field == "provision_used_writeoff" else "point",
             statement_type="consolidated", reader="fiinquant_screening", grade="single", page=None,
             source_url="https://test.com/screening")
        for period, group2, used in [("2025Q1", 4., 1.), ("2025Q2", 5., 2.), ("2025Q3", 6., 4.)]
        for field, value in [("loans_customer", 100.), ("group_2_watch", group2), ("provision_used_writeoff", used)]
        if not (period == "2025Q1" and field == "group_2_watch")
    ])
    notes = pd.DataFrame([
        dict(bank="VCB", period=period, field="group_2_watch", value_vnd_bn=value, basis="point",
             statement_type="consolidated", grade="verified", page=2, source_url="https://test.com/filing")
        for period, value in [("2025Q1", 4.), ("2025Q2", 10.), ("2025Q3", 12.)]
    ])
    first, second, third = build_decoder(panel, seasonal, notes, screening)["rows"]
    assert [row["group2_vnd_bn"] for row in [first, second, third]] == [4., 5., 6.]
    assert third["writeoff_ratio"] == pytest.approx(.04)
    assert {"S1", "S2"} <= {signal["id"] for signal in third["signals"]}


def test_decoder_does_not_flag_a_switch_from_reported_writeoffs_to_the_proxy():
    periods = ["2025Q1", "2025Q2", "2025Q3"]
    panel, _ = clean_quarters(pd.DataFrame({"ticker": ["VCB"] * 3, "period": periods,
        "npl_pct": [5., 4., 3.], "coverage_pct": [100.] * 3}))
    _, seasonal = decision_rule(panel)
    pdf = pd.DataFrame([dict(bank="VCB", period=period, field=field, value_vnd_bn=value, basis="consolidated",
                             grade="verified", page=2, source_url="https://test.com/filing")
                        for period in periods for field, value in [("loans_customer", 100.), ("writeoff_period", 2.)]])
    screening = pd.DataFrame([dict(bank="VCB", period="2025Q3", field="provision_used_writeoff", value_vnd_bn=5.,
        basis="fiinquant_screening", flow_basis="quarterly", statement_type="consolidated",
        grade="single", page=None, source_url="https://test.com/screening")])
    latest = build_decoder(panel, seasonal, pdf, screening)["rows"][-1]
    assert latest["writeoff_ratio"] == pytest.approx(.05)
    assert latest["delta_writeoff_ratio"] is None
    assert "S2" not in {signal["id"] for signal in latest["signals"]}


def test_statement_regression_recovers_lagged_coverage_with_eight_banks(silver):
    panel, _ = clean_quarters(pd.read_parquet(silver / "bank_quarter.parquet"))
    _, seasonal = decision_rule(panel)
    rng = np.random.default_rng(70)
    fields = ["customer_loans", "group2_loans", "groups345_loans", "provision_closing", "writeoffs"]
    statements = []
    periods = pd.period_range("2024Q1", "2026Q3", freq="Q")
    for bank_no, bank in enumerate(sorted(panel.bank_code.unique())):
        loans, g2, npl, coverage = 100., .05, .15, 1.5
        for period in periods:
            current_g2 = rng.uniform(.02, .12)
            growth = rng.uniform(-.07, .09)
            writeoff_ratio = rng.uniform(.001, .02)
            writeoffs = writeoff_ratio * loans
            npl += (.18 * writeoff_ratio + .04 * (current_g2 - g2) + .09 * growth
                    - .012 * coverage + .003 * bank_no + rng.normal(0, .0005))
            coverage = rng.uniform(.5, 1.6)
            loans *= 1 + growth
            g2 = current_g2
            values = [loans, g2 * loans, npl * loans, coverage * npl * loans, writeoffs]
            statements.extend(dict(bank=bank, period=str(period), field=field, value_vnd_bn=value,
                                   basis="consolidated", grade="verified", page=4,
                                   source_url="https://test.com/notes.pdf") for field, value in zip(fields, values))
    fit = build_decoder(panel, seasonal, pd.DataFrame(statements))["regression"]["notes"]["full"]
    assert fit["clusters"] == 8 and fit["n"] == 80
    assert fit["terms"]["lagged_coverage"]["coefficient"] == pytest.approx(-.012, abs=.001)
    assert fit["terms"]["lagged_coverage"]["ci95"][1] < 0
    assert 0 < fit["terms"]["lagged_coverage"]["wild_p"] < .05


def test_b5_silver_uses_point_stocks_quarterly_flows_and_filing_scope(silver):
    panel, _ = clean_quarters(pd.read_parquet(silver / "bank_quarter.parquet"))
    _, seasonal = decision_rule(panel)
    fields = ["loans_customer", "group_2_watch", "group_3_substandard", "group_4_doubtful",
              "group_5_loss", "provision_closing", "writeoff_period", "writeoff_period"]
    bases = ["point"] * 6 + ["quarterly", "ytd"]
    periods = ["2025Q1", "2025Q2", "2025Q3"]
    types = ["consolidated", "consolidated", "separate"]
    notes, links = [], []
    for index, (period, scope) in enumerate(zip(periods, types)):
        url = f"https://test.com/statement-{period}.pdf"
        links.append(dict(bank="VCB", period=period, url=url, statement_type=scope))
        values = [100, 6, 6 - index, 2, 2, 20, 2 + index, 99]
        notes.extend(dict(bank="VCB", period=period, field=field, value_vnd_bn=value, basis=basis,
                          grade="verified", page=5, source_url=url)
                     for field, value, basis in zip(fields, values, bases))
    pd.DataFrame(notes).to_parquet(silver / "notes_bank_quarter.parquet")
    pd.DataFrame(links).to_csv(silver / "notes_links.csv", index=False)
    tables = read_silver(silver)
    result = build_decoder(panel, seasonal, tables["notes_bank_quarter"])
    rows = {row["period"]: row for row in result["rows"] if row["bank_code"] == "VCB"}
    assert rows["2025Q2"]["npl_vnd_bn"] == 9
    assert rows["2025Q2"]["writeoff_ratio"] == pytest.approx(.03)
    assert rows["2025Q2"]["npl_formation"] == pytest.approx(.02)
    assert rows["2025Q3"]["npl_vnd_bn"] is None
    assert rows["2025Q3"]["npl_ratio"] is not None


def test_coverage_disagreement_disables_s3_for_both_adjacent_changes():
    raw = pd.DataFrame({
        "ticker": ["ABB"] * 3,
        "period": ["2025Q1", "2025Q2", "2025Q3"],
        "npl_pct": [4, 3, 2],
        "coverage_pct": [120, 110, 100],
    })
    panel, _ = clean_quarters(raw)
    _, seasonal = decision_rule(panel)
    notes = pd.DataFrame([
        dict(bank="ABB", period="2025Q2", field=field, value_vnd_bn=value, basis="consolidated",
             grade="verified", page=4, source_url="https://test.com/notes.pdf")
        for field, value in [("customer_loans", 100), ("group2_loans", 5), ("groups345_loans", 3),
                             ("provision_closing", 9)]
    ])
    result = build_decoder(panel, seasonal, notes)
    assert result == build_decoder(panel, seasonal, pd.concat([notes, notes]))
    first, contested, following = result["rows"]
    assert first["coverage_contested"] is False
    assert contested["coverage_contested"] is True
    assert contested["group2_vnd_bn"] == 5
    assert contested["coverage"] == pytest.approx(1.1)
    assert contested["coverage_source"] == "fiinquant"
    assert following["coverage_contested"] is False
    assert contested["layers"]["data_quality"] == "cách ly"
    for row in [contested, following]:
        assert row["status"] == "missing"
        assert row["delta_coverage"] is None
        assert "delta_coverage" in row["missing_inputs"]
        assert not any(signal["id"] == "S3" for signal in row["signals"])


def test_coverage_change_uses_one_comparable_source():
    raw = pd.DataFrame({"ticker": ["VCB"] * 2, "period": ["2025Q1", "2025Q2"],
                        "npl_pct": [4, 3], "coverage_pct": [120, 120]})
    panel, _ = clean_quarters(raw)
    _, seasonal = decision_rule(panel)
    notes = pd.DataFrame([
        dict(bank="VCB", period="2025Q2", field=field, value_vnd_bn=value, basis="consolidated",
             grade="verified", page=4, source_url="https://test.com/notes.pdf")
        for field, value in [("groups345_loans", 3), ("provision_closing", 3.5998)]
    ])
    _, row = build_decoder(panel, seasonal, notes)["rows"]
    assert row["coverage_source"] == "notes" and row["coverage_contested"] is False
    assert row["delta_coverage"] == 0
    assert row["signals"] == []


def test_coverage_decline_without_a_thinner_provision_ratio_is_not_s3():
    raw = pd.DataFrame({"ticker": ["VCB"] * 3, "period": ["2024Q4", "2025Q1", "2025Q2"],
                        "npl_pct": [5, 4, 3], "coverage_pct": [200, 200, 100]})
    panel, _ = clean_quarters(raw)
    _, seasonal = decision_rule(panel)
    notes = pd.DataFrame([
        dict(bank="VCB", period=period, field=field, value_vnd_bn=value, basis="consolidated",
             grade="verified", page=4, source_url="https://test.com/notes.pdf")
        for period, loans, group2, provision, writeoff in [
            ("2024Q4", 100, 4, 8, 1), ("2025Q1", 100, 4, 8, 1), ("2025Q2", 100, 6, 10, 1),
        ]
        for field, value in [("customer_loans", loans), ("group2_loans", group2),
                             ("provision_closing", provision), ("writeoffs", writeoff)]
    ])
    row = build_decoder(panel, seasonal, notes)["rows"][-1]
    assert row["delta_coverage"] < 0
    assert "S3" not in {signal["id"] for signal in row["signals"]}
    assert row["status"] == "review"
    assert [signal["id"] for signal in row["signals"]] == ["S1"]


def test_a_ytd_provision_flow_does_not_raise_s2():
    periods = ["2025Q1", "2025Q2"]
    panel, _ = clean_quarters(pd.DataFrame({"ticker": ["VCB"] * 2, "period": periods,
        "npl_pct": [5., 4.], "coverage_pct": [100., 100.]}))
    _, seasonal = decision_rule(panel)
    screening = pd.DataFrame([
        dict(bank="VCB", period=period, field=field, value_vnd_bn=value, basis="fiinquant_screening",
             flow_basis="ytd" if field == "provision_used_writeoff" else "point",
             statement_type="consolidated", grade="single", page=None, source_url="https://test.com/screening")
        for period, used in [("2025Q1", 1.), ("2025Q2", 4.)]
        for field, value in [("loans_customer", 100.), ("group_2_watch", 4.), ("provision_used_writeoff", used)]
    ])
    latest = build_decoder(panel, seasonal, None, screening)["rows"][-1]
    assert "S2" not in {signal["id"] for signal in latest["signals"]}


def test_fiinquant_ols_uses_screening_group2_and_quarterly_writeoffs_only():
    banks = ["VCB", "BID", "CTG"]
    periods = ["2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2"]
    paths = {
        "VCB": {"npl": [2.0, 2.4, 2.1, 2.8, 2.2], "coverage": [80, 100, 90, 120, 95],
                "growth": [8, 14, 6, 18, 9], "loans": [100, 108, 104, 130, 121],
                "group2": [4.0, 5.5, 5.0, 7.2, 6.1], "used": [1.0, 1.4, 0.8, 2.1, 1.1]},
        "BID": {"npl": [2.2, 2.0, 2.6, 2.3, 2.9], "coverage": [70, 75, 110, 85, 130],
                "growth": [11, 7, 16, 8, 13], "loans": [140, 150, 148, 170, 160],
                "group2": [6.0, 5.2, 8.1, 7.0, 9.4], "used": [1.2, 0.7, 1.8, 1.0, 2.4]},
        "CTG": {"npl": [3.0, 2.7, 3.2, 2.5, 2.9], "coverage": [90, 88, 140, 100, 110],
                "growth": [9, 15, 8, 12, 6], "loans": [90, 96, 110, 105, 120],
                "group2": [3.5, 4.8, 4.1, 6.0, 5.2], "used": [2.0, 2.2, 2.5, 2.1, 2.8]},
    }
    panel, _ = clean_quarters(pd.DataFrame([
        {"ticker": bank, "period": period, "npl_pct": paths[bank]["npl"][t],
         "coverage_pct": paths[bank]["coverage"][t], "loan_growth_yoy_pct": paths[bank]["growth"][t],
         "nim_pct": 3}
        for bank in banks for t, period in enumerate(periods)
    ]))
    _, seasonal = decision_rule(panel)
    screening, notes = [], []
    for bank in banks:
        for t, period in enumerate(periods):
            loans, group2, used = paths[bank]["loans"][t], paths[bank]["group2"][t], paths[bank]["used"][t]
            for field, value, flow in [
                ("loans_customer", loans, "point"),
                ("group_2_watch", group2, "point"),
                ("provision_used_writeoff", used, "quarterly" if bank != "CTG" else "ytd"),
            ]:
                screening.append(dict(
                    bank=bank, period=period, field=field, value_vnd_bn=value,
                    basis="fiinquant_screening", flow_basis=flow, statement_type="consolidated",
                    grade="single", page=None, source_url="https://test.com/screening"))
            notes.append(dict(
                bank=bank, period=period, field="writeoffs", value_vnd_bn=9, basis="consolidated",
                grade="verified", page=3, source_url="https://test.com/notes.pdf"))
    result = build_decoder(panel, seasonal, pd.DataFrame(notes), pd.DataFrame(screening))
    fit = result["regression"]["fiinquant"]
    assert fit["n_by_field"]["writeoff_ratio"] == 8
    assert fit["n_by_field"]["delta_g2_ratio"] == 12
    assert fit["full"]["n"] == 8 and fit["full"]["clusters"] == 2
    assert set(fit["full"]["terms"]) == {"writeoff_ratio", "delta_g2_ratio", "loan_growth", "lagged_coverage"}
    assert fit["without_writeoff"]["n"] == 12
    assert set(fit["without_writeoff"]["terms"]) == {"delta_g2_ratio", "loan_growth", "lagged_coverage"}
    assert set(fit["available"]["terms"]) == {"loan_growth", "lagged_coverage"}
    assert fit["available"]["n"] == 12
    assert fit["sample_banks"]["full"] == ["BID", "VCB"]
    assert "CTG" in fit["sample_banks"]["without_writeoff"]
    ctg = next(row for row in result["rows"] if row["bank_code"] == "CTG" and row["period"] == "2025Q2")
    assert ctg["writeoff_ratio"] is not None
    for text in (fit["reading_vi"], fit["reading_en"]):
        assert "n=8" in text and "2024Q3" in text and "BID" in text and "CTG" in text
    for term in fit["full"]["terms"].values():
        assert term["wild_p"] is not None and np.isfinite(term["coefficient"])
