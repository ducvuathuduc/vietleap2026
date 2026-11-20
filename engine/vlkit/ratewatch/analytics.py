"""RateWatch analytics: the formulas behind every decision number.

Simple interest only, on posted rows. No Nelson-Siegel, no point forecast and
no cross-bank regression enters the decision path; the break-even renewal rate
is a calculation on today's posted rates, not a posted rate and not a forecast.

Conventions shared with the TypeScript port web/src/lib/ratewatch/calc.ts,
which must keep identical behaviour (same fixture, same results):
- rates are percent per year (e.g. 6.30 means 6.30%/year);
- money is VND; interest at maturity is simple: P * r * months/12 for a term in
  months, P * r * days/365 for a day count (actual/365);
- the insured cap covers principal + interest per person per institution
  (350,000,000 VND, Thong tu 05/2026/TT-NHNN Dieu 3);
- the short-term ceiling is 4.75%/year for 1 to <6 months (Quyet dinh 2411).

Arithmetic order matters: both ports evaluate the same expressions in the same
order so float results are bitwise identical.
"""

from __future__ import annotations

from typing import Any, Sequence

INSURED_CAP_VND = 350_000_000  # Thong tu 05/2026/TT-NHNN Dieu 3
CEILING_PCT = 4.75  # Quyet dinh 2411/QD-NHNN, terms from 1 to under 6 months
GRADED = ("verified", "single")  # grades that feed decision medians


def interest(
    P: float,
    rate_pct: float,
    months: float | None = None,
    days: float | None = None,
    basis: str = "at_maturity",
) -> float:
    """Simple interest at maturity in VND.

    Exactly one of months/days must be given: months -> P * r * months/12,
    days -> P * r * days/365 (actual/365). basis is the sheet's interest
    convention; only "at_maturity" is supported.
    """
    if basis != "at_maturity":
        raise ValueError(f"unsupported interest basis: {basis!r}")
    if (months is None) == (days is None):
        raise ValueError("provide exactly one of months or days")
    if P < 0:
        raise ValueError("P must be >= 0")
    if months is not None:
        if months < 0:
            raise ValueError("months must be >= 0")
        return P * (rate_pct / 100) * (months / 12)
    if days < 0:
        raise ValueError("days must be >= 0")
    return P * (rate_pct / 100) * (days / 365)


def break_even_renewal(r_long: float, long_m: float, r_short: float, short_m: float) -> float:
    """Solve f in (1 + r_long*long_m/12) = (1 + r_short*short_m/12) * (1 + f*(long_m-short_m)/12).

    Percent in, percent out. f is the second-leg simple rate at which placing
    short and renewing ties the long lock; a calculation on posted rates.
    """
    if long_m <= short_m:
        raise ValueError("long_m must exceed short_m")
    grow_long = 1 + (r_long / 100) * (long_m / 12)
    grow_short = 1 + (r_short / 100) * (short_m / 12)
    if grow_short <= 0:
        raise ValueError("short leg growth factor must be positive")
    f = (grow_long / grow_short - 1) * (12 / (long_m - short_m))
    return f * 100


def early_withdrawal(P: float, posted_rate: float, demand_rate: float, held_months: float) -> dict[str, float]:
    """Outcome of pulling a term deposit at held_months when the term is longer.

    The bank pays the demand (non-term) rate on the whole held period and the
    posted rate is forfeited. Returns interest_vnd (what the bank pays),
    if_posted_vnd (what the same principal over the same horizon would earn at
    the posted rate) and forgone_vnd (the difference).
    """
    if held_months < 0:
        raise ValueError("held_months must be >= 0")
    interest_vnd = P * (demand_rate / 100) * (held_months / 12)
    if_posted_vnd = P * (posted_rate / 100) * (held_months / 12)
    return {
        "interest_vnd": interest_vnd,
        "if_posted_vnd": if_posted_vnd,
        "forgone_vnd": if_posted_vnd - interest_vnd,
    }


def real_rate(nominal_pct: float, cpi_yoy_pct: float) -> float:
    """Fisher: (1 + nominal)/(1 + inflation) - 1. Percent in, percent out."""
    return ((1 + nominal_pct / 100) / (1 + cpi_yoy_pct / 100) - 1) * 100


def _growth_factor(rate_pct: float, term_months: float) -> float:
    return 1 + (rate_pct / 100) * (term_months / 12)


def insured_split(
    amount: float,
    cap: float = INSURED_CAP_VND,
    options: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Greedy per-bank amounts so principal + interest at maturity stays <= cap.

    options: [{bank_code, term_months, rate_pct}], tried in order; a bank's
    room is cap / (1 + r*m/12) minus what it already holds. Returns allocations
    (each with amount, interest_vnd, total_vnd), the unplaced remainder_vnd —
    the uninsured excess flag — and insured_share, the fraction of principal
    placed within the cap.
    """
    if amount < 0:
        raise ValueError("amount must be >= 0")
    allocations: list[dict[str, Any]] = []
    remaining = amount
    used: dict[str, float] = {}
    for opt in options or []:
        bank = opt["bank_code"]
        factor = _growth_factor(opt["rate_pct"], opt["term_months"])
        room = cap / factor - used.get(bank, 0.0)
        alloc = min(remaining, max(room, 0.0))
        if alloc <= 0:
            continue
        interest_vnd = alloc * (opt["rate_pct"] / 100) * (opt["term_months"] / 12)
        allocations.append(
            {
                "bank_code": bank,
                "amount": alloc,
                "interest_vnd": interest_vnd,
                "total_vnd": alloc + interest_vnd,
            }
        )
        used[bank] = used.get(bank, 0.0) + alloc
        remaining -= alloc
    allocated = amount - remaining
    return {
        "allocations": allocations,
        "allocated_vnd": allocated,
        "remainder_vnd": remaining,
        "fully_insured": remaining <= 0,
        "insured_share": allocated / amount if amount > 0 else 1.0,
    }


def _eligible_rows(options: Sequence[dict[str, Any]], online_ok: bool, allow_single: bool) -> list[dict[str, Any]]:
    """Posted rows that may feed a plan: verified rows always, single rows only
    when allow_single, contested rows never; online rows only when online_ok."""
    eligible = []
    for row in options:
        if not online_ok and row["channel"] == "online":
            continue
        grade = row.get("grade", "")
        if grade == "verified" or (allow_single and grade == "single"):
            eligible.append(row)
    return eligible


def _sorted_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic order: best rate first, then shorter term, counter before
    online, then bank/tier; stable, so equal keys keep the caller's order."""
    return sorted(
        rows,
        key=lambda r: (
            -r["rate_pct"],
            r["term_months"],
            r.get("channel", ""),
            r["bank_code"],
            r.get("tier", ""),
        ),
    )


def _insured_share(amount: float, growth: float, cap: float) -> float:
    if amount <= 0:
        return 1.0
    return min(1.0, (cap / growth) / amount)


def plan(
    amount: float,
    horizon_months: float,
    online_ok: bool,
    options: Sequence[dict[str, Any]],
    cap: float = INSURED_CAP_VND,
    demand_rates: dict[str, float] | None = None,
    allow_single: bool = False,
) -> list[dict[str, Any]]:
    """Ranked plans for a household amount and horizon.

    Every plan is compared and reported by its value at the horizon: a term at
    or before the horizon grows at the posted rate, then the idle months earn
    the bank's demand rate (0 when none is given); a term beyond the horizon is
    withdrawn early at the demand rate (the shortest such term per bank
    dominates). Emits every eligible single-term placement, one 6-month +
    renewal ladder (the second leg renews at the same bank's posted row for the
    remaining months, same channel — a calculation on today's posted rates, not
    a forecast; with no such row the ladder is not emitted), and one greedy
    split across banks under the insured cap (per-bank best option by horizon
    value, banks filled best horizon value first; emitted when it uses >= 2
    banks). Plans rank by value at the horizon; comparing terms is the
    break-even card's job.

    rows carry bank_code, term_months, channel, tier, rate_pct, grade,
    source_url, sheet_date and appear in the plan unchanged.
    """
    demands = demand_rates or {}
    eligible = _sorted_rows(_eligible_rows(options, online_ok, allow_single))
    plans: list[dict[str, Any]] = []

    def horizon_factor(bank: str, rate_pct: float, term: float) -> float:
        d = demands.get(bank, 0.0)
        return _growth_factor(rate_pct, term) * _growth_factor(d, horizon_months - term)

    # per bank: shortest term beyond the horizon (early withdrawal forfeits the
    # posted rate, so the shortest term dominates)
    shortest_beyond: dict[str, dict[str, Any]] = {}
    for row in eligible:
        bank = row["bank_code"]
        if row["term_months"] > horizon_months:
            cur = shortest_beyond.get(bank)
            if cur is None or row["term_months"] < cur["term_months"]:
                shortest_beyond[bank] = row

    for row in eligible:
        bank = row["bank_code"]
        term = row["term_months"]
        if term <= horizon_months:
            factor_h = horizon_factor(bank, row["rate_pct"], term)
            value = amount * factor_h
            idle = horizon_months - term
            early = False
            maturity_growth = _growth_factor(row["rate_pct"], term)
        else:
            if shortest_beyond[bank] is not row or bank not in demands:
                continue
            factor_h = _growth_factor(demands[bank], horizon_months)
            value = amount * factor_h
            idle = 0
            early = True
            maturity_growth = factor_h
        plans.append(
            {
                "kind": "single",
                "early_withdrawal": early,
                "interest_vnd": value - amount,
                "value_at_horizon": value,
                "idle_months": idle,
                "insured_share": _insured_share(amount, maturity_growth, cap),
                "rows": [row],
                "amounts": [{"bank_code": bank, "amount": amount}],
            }
        )

    six = [row for row in eligible if row["term_months"] == 6]
    if horizon_months > 6 and six:
        row6 = six[0]  # eligible is rate-sorted, so this is the best 6-month row
        rest = horizon_months - 6
        # the second leg renews at the same bank's posted row for the remaining
        # months (same channel); with no such row the ladder is not emitted
        row2 = next(
            (
                r
                for r in eligible
                if r["bank_code"] == row6["bank_code"]
                and r["term_months"] == rest
                and r.get("channel", "") == row6.get("channel", "")
            ),
            None,
        )
        if row2 is not None:
            r6 = row6["rate_pct"]
            r2 = row2["rate_pct"]
            leg1 = amount * (r6 / 100) * (6 / 12)
            leg2 = (amount + leg1) * (r2 / 100) * (rest / 12)
            growth = _growth_factor(r6, 6) * _growth_factor(r2, rest)
            plans.append(
                {
                    "kind": "ladder_6_renewal",
                    "early_withdrawal": False,
                    "interest_vnd": leg1 + leg2,
                    "value_at_horizon": amount + leg1 + leg2,
                    "idle_months": 0,
                    "second_leg_assumption": "same posted rate as today",
                    "insured_share": _insured_share(amount, growth, cap),
                    "rows": [row6, row2],
                    "amounts": [{"bank_code": row6["bank_code"], "amount": amount}],
                }
            )

    # split: per bank the eligible option with the best value at the horizon
    # (term <= horizon at maturity, then idle months at the demand rate; beyond
    # it, early withdrawal at the demand rate), then greedy fill best horizon
    # value first under the cap
    best: dict[str, dict[str, Any]] = {}
    for row in eligible:
        bank = row["bank_code"]
        term = row["term_months"]
        if term <= horizon_months:
            pseudo = {"bank_code": bank, "term_months": term, "rate_pct": row["rate_pct"]}
        elif bank in demands:
            pseudo = {"bank_code": bank, "term_months": horizon_months, "rate_pct": demands[bank]}
        else:
            continue
        factor_h = horizon_factor(bank, pseudo["rate_pct"], pseudo["term_months"])
        if bank not in best or factor_h > best[bank]["factor_h"]:
            best[bank] = {"row": row, "pseudo": pseudo, "factor_h": factor_h}
    ordered = sorted(best.values(), key=lambda b: -b["factor_h"])
    split = insured_split(amount, cap, [b["pseudo"] for b in ordered])
    if len(split["allocations"]) >= 2:
        rows_by_bank = {b["row"]["bank_code"]: b["row"] for b in ordered}
        factor_h_by_bank = {b["row"]["bank_code"]: b["factor_h"] for b in ordered}
        interest_h = sum(a["amount"] * (factor_h_by_bank[a["bank_code"]] - 1) for a in split["allocations"])
        plans.append(
            {
                "kind": "split",
                "early_withdrawal": False,
                "interest_vnd": interest_h,
                "value_at_horizon": amount + interest_h,
                "idle_months": None,
                "insured_share": split["insured_share"],
                "rows": [rows_by_bank[a["bank_code"]] for a in split["allocations"]],
                "amounts": [{"bank_code": a["bank_code"], "amount": a["amount"]} for a in split["allocations"]],
            }
        )

    plans.sort(
        key=lambda p: (
            -p["value_at_horizon"],
            p["kind"],
            p["rows"][0]["bank_code"],
            p["rows"][0]["term_months"],
        )
    )
    return plans


def _median(values: Sequence[float]) -> float:
    xs = sorted(values)
    n = len(xs)
    if n == 0:
        raise ValueError("median of empty sequence")
    if n % 2 == 1:
        return xs[n // 2]
    return (xs[n // 2 - 1] + xs[n // 2]) / 2


def ceiling_stats(rows: Sequence[dict[str, Any]], ceiling_pct: float = CEILING_PCT) -> dict[str, Any]:
    """Ceiling picture for the 1 to <6 month band.

    quotes_1_5m / at_ceiling / above count every posted row in the band.
    Per-bank 5->6 month jumps come from each bank's median rate at 5 and 6
    months; jump_5_6_pp_median is the median over graded banks only (both legs
    verified or single). grade_basis names the grades behind that median.
    """
    short = [r for r in rows if 1 <= r["term_months"] < 6]
    at_ceiling = sum(1 for r in short if abs(r["rate_pct"] - ceiling_pct) <= 1e-9)
    above = sum(1 for r in short if r["rate_pct"] > ceiling_pct + 1e-9)

    cells: dict[tuple[str, int], dict[str, Any]] = {}
    for r in rows:
        if r["term_months"] not in (5, 6):
            continue
        key = (r["bank_code"], r["term_months"])
        cell = cells.setdefault(key, {"rates": [], "graded": True})
        cell["rates"].append(r["rate_pct"])
        if r.get("grade", "") not in GRADED:
            cell["graded"] = False

    jumps = []
    for bank in sorted({bank for bank, _ in cells}):
        c5 = cells.get((bank, 5))
        c6 = cells.get((bank, 6))
        if not c5 or not c6:
            continue
        jumps.append(
            {
                "bank_code": bank,
                "jump_pp": _median(c6["rates"]) - _median(c5["rates"]),
                "graded": c5["graded"] and c6["graded"],
            }
        )
    graded_jumps = [j["jump_pp"] for j in jumps if j["graded"]]
    return {
        "quotes_1_5m": len(short),
        "at_ceiling": at_ceiling,
        "above": above,
        "jumps": jumps,
        "jump_5_6_pp_median": _median(graded_jumps) if graded_jumps else None,
        "n_banks": len(jumps),
        "n_banks_graded": len(graded_jumps),
        "grade_basis": "verified+single",
    }
