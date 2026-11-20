"""RateWatch analytics tests.

Every case lives in tests/fixtures/ratewatch/analytics_cases.json and is run
against engine/vlkit/ratewatch/analytics.py here and against the TypeScript
port web/src/lib/ratewatch/calc.ts in web/src/lib/ratewatch/calc.test.ts.
The two hand-checked break-even values are from X-JUDGE/JUDGE.md section 0.
"""

import json
import math
from pathlib import Path

import pytest

from vlkit.ratewatch.analytics import (
    break_even_renewal,
    ceiling_stats,
    early_withdrawal,
    insured_split,
    interest,
    plan,
    real_rate,
)

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "ratewatch" / "analytics_cases.json").read_text(encoding="utf-8")
)
TOL = CASES["tolerances"]


def test_interest():
    for case in CASES["interest"]:
        if case.get("expect_error"):
            with pytest.raises(ValueError):
                interest(
                    case["P"],
                    case["rate_pct"],
                    months=case.get("months"),
                    days=case.get("days"),
                    basis=case.get("basis", "at_maturity"),
                )
            continue
        got = interest(
            case["P"],
            case["rate_pct"],
            months=case.get("months"),
            days=case.get("days"),
            basis=case.get("basis", "at_maturity"),
        )
        assert abs(got - case["expected"]) <= TOL["vnd"], case["name"]


def test_break_even_renewal_hand_checks():
    for case in CASES["break_even"]:
        if case.get("expect_error"):
            with pytest.raises(ValueError):
                break_even_renewal(case["r_long"], case["long_m"], case["r_short"], case["short_m"])
            continue
        f = break_even_renewal(case["r_long"], case["long_m"], case["r_short"], case["short_m"])
        assert round(f, 4) == case["expected_4dp"], case["name"]
        assert abs(f - case["expected_4dp"]) <= TOL["pct"], case["name"]


def test_early_withdrawal():
    for case in CASES["early_withdrawal"]:
        got = early_withdrawal(case["P"], case["posted_rate"], case["demand_rate"], case["held_months"])
        assert abs(got["interest_vnd"] - case["expected_interest_vnd"]) <= TOL["vnd"], case["name"]
        assert abs(got["if_posted_vnd"] - case["expected_if_posted_vnd"]) <= TOL["vnd"], case["name"]
        assert abs(got["forgone_vnd"] - case["expected_forgone_vnd"]) <= TOL["vnd"], case["name"]
        assert got["forgone_vnd"] == got["if_posted_vnd"] - got["interest_vnd"], case["name"]


def test_real_rate_fisher():
    for case in CASES["real_rate"]:
        got = real_rate(case["nominal_pct"], case["cpi_yoy_pct"])
        assert round(got, 4) == case["expected_4dp"], case["name"]
        assert abs(got - case["expected_4dp"]) <= TOL["pct"], case["name"]


def test_insured_split():
    for case in CASES["insured_split"]:
        got = insured_split(case["amount"], case["cap"], case["options"])
        exp = case["expected"]
        assert len(got["allocations"]) == exp["n_allocations"], case["name"]
        assert [a["bank_code"] for a in got["allocations"]] == exp["banks"], case["name"]
        assert abs(got["remainder_vnd"] - exp["remainder_vnd"]) <= TOL["vnd"], case["name"]
        assert got["fully_insured"] is exp["fully_insured"], case["name"]
        assert abs(got["insured_share"] - exp["insured_share_4dp"]) <= TOL["share"], case["name"]
        if "interest_vnd" in exp:
            assert abs(sum(a["interest_vnd"] for a in got["allocations"]) - exp["interest_vnd"]) <= TOL["vnd"], case["name"]
        for alloc in got["allocations"]:
            assert alloc["total_vnd"] <= case["cap"] + 1e-6, case["name"]
            assert abs(alloc["total_vnd"] - (alloc["amount"] + alloc["interest_vnd"])) <= 1e-9, case["name"]
        if exp.get("total_at_cap"):
            total = got["allocations"][0]["total_vnd"]
            assert case["cap"] - TOL["vnd"] <= total <= case["cap"] + 1e-6, case["name"]


def _assert_plans(plans, expected, name):
    assert len(plans) == len(expected), name
    for got, exp in zip(plans, expected):
        assert got["kind"] == exp["kind"], (name, got["kind"])
        assert [a["bank_code"] for a in got["amounts"]] == exp["banks"], name
        assert [r["term_months"] for r in got["rows"]] == exp["terms"], name
        assert abs(got["interest_vnd"] - exp["interest_vnd"]) <= TOL["vnd"], name
        assert abs(got["value_at_horizon"] - exp["value_at_horizon"]) <= TOL["vnd"], name
        assert got["idle_months"] == exp["idle_months"], name
        assert abs(got["insured_share"] - exp["insured_share_4dp"]) <= TOL["share"], name
        if "second_leg_assumption" in exp:
            assert got["second_leg_assumption"] == exp["second_leg_assumption"], name
        if "early_withdrawal" in exp:
            assert got["early_withdrawal"] is exp["early_withdrawal"], name
        else:
            assert got["early_withdrawal"] is False, name
    interests = [p["value_at_horizon"] for p in plans]
    assert interests == sorted(interests, reverse=True), name


def test_plan():
    for case in CASES["plan"]:
        got = plan(
            case["amount"],
            case["horizon_months"],
            case["online_ok"],
            case["options"],
            cap=case["cap"],
            demand_rates=case["demand_rates"],
            allow_single=case["allow_single"],
        )
        _assert_plans(got, case["expected"], case["name"])
        for p in got:  # every row used is one of the input rows, unchanged
            for row in p["rows"]:
                assert row in case["options"], case["name"]


def test_plan_split_greedy_matches_brute_force_small():
    case = CASES["plan_brute_force"]
    got = plan(
        case["amount"],
        case["horizon_months"],
        case["online_ok"],
        case["options"],
        cap=case["cap"],
        demand_rates=case["demand_rates"],
        allow_single=False,
    )
    splits = [p for p in got if p["kind"] == "split"]
    assert len(splits) == 1
    split = splits[0]
    for alloc in split["amounts"]:
        row = next(r for r in case["options"] if r["bank_code"] == alloc["bank_code"])
        g = 1 + (row["rate_pct"] / 100) * (row["term_months"] / 12)
        assert alloc["amount"] + alloc["amount"] * (g - 1) <= case["cap"] + 1e-6

    banks = []
    for row in case["options"]:
        g = 1 + (row["rate_pct"] / 100) * (row["term_months"] / 12)
        d = case["demand_rates"].get(row["bank_code"], 0.0)
        if row["term_months"] <= case["horizon_months"]:
            g_h = g * (1 + (d / 100) * ((case["horizon_months"] - row["term_months"]) / 12))
        else:
            g_h = 1 + (d / 100) * (case["horizon_months"] / 12)
        banks.append((row["bank_code"], g, g_h, case["cap"] / g))
    unit = case["amount"] / case["grid_steps"]
    best = 0.0

    def rec(i, remaining, total):
        nonlocal best
        if i == len(banks):
            best = max(best, total)
            return
        _, g, g_h, room = banks[i]
        top = min(remaining, room)
        for u in range(int(top / unit + 1e-9) + 1):
            alloc = u * unit
            rec(i + 1, remaining - alloc, total + alloc * (g_h - 1))

    rec(0, case["amount"], 0.0)
    assert best > 0
    assert split["interest_vnd"] >= best - TOL["vnd"]


def test_ceiling_stats():
    for case in CASES["ceiling_stats"]:
        got = ceiling_stats(case["rows"], case["ceiling_pct"])
        exp = case["expected"]
        assert got["quotes_1_5m"] == exp["quotes_1_5m"], case["name"]
        assert got["at_ceiling"] == exp["at_ceiling"], case["name"]
        assert got["above"] == exp["above"], case["name"]
        assert got["n_banks"] == exp["n_banks"], case["name"]
        assert got["n_banks_graded"] == exp["n_banks_graded"], case["name"]
        assert [j["bank_code"] for j in got["jumps"]] == [j["bank_code"] for j in exp["jumps"]], case["name"]
        for got_j, exp_j in zip(got["jumps"], exp["jumps"]):
            assert abs(got_j["jump_pp"] - exp_j["jump_pp"]) <= TOL["pp"], case["name"]
            assert got_j["graded"] is exp_j["graded"], case["name"]
        if exp["jump_5_6_pp_median"] is None:
            assert got["jump_5_6_pp_median"] is None, case["name"]
        else:
            assert math.isclose(got["jump_5_6_pp_median"], exp["jump_5_6_pp_median"], abs_tol=TOL["pp"]), case["name"]
