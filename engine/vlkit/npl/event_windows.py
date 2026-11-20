"""Market-model CARs on fixed windows, with a deadline clock and a disclosure-date clock.

The estimation window is the 100 sessions [-120, -21]. It does not overlap [-1, +1], [-1, +5]
or the existing [-10, +10] window. A minimum detectable effect is 2.8 bootstrap standard errors,
the usual normal approximation for 80% power at a 5% two-sided test.
"""
import numpy as np
import pandas as pd

from .real_models import BOOTSTRAP_SEED, _fit

ESTIMATION = (-120, -21)
WINDOWS = {"m1_p1": (-1, 1), "m1_p5": (-1, 5), "m10_p10": (-10, 10)}
MDE_FACTOR = 2.8
PLACEBO_SEED = 20261120


def windows_overlap(estimation, event):
    return max(estimation[0], event[0]) <= min(estimation[1], event[1])


def _prepare(market):
    frame = market.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    wide = frame.pivot(index="date", columns="bank_code", values="return_pct").sort_index()
    benchmark = wide.pop("VNINDEX").to_numpy(dtype=float)
    series = {bank: wide[bank].to_numpy(dtype=float) for bank in wide.columns}
    return wide.index, series, benchmark


def _car_at(stock, benchmark, event, estimation, window):
    start, stop = event + estimation[0], event + estimation[1] + 1
    first, last = event + window[0], event + window[1] + 1
    if start < 0 or last > len(stock) or stop <= start or last <= first:
        return None
    train_x, train_y = benchmark[start:stop], stock[start:stop]
    observed = np.isfinite(train_x) & np.isfinite(train_y)
    if int(observed.sum()) < 60:
        return None
    design = np.column_stack([np.ones(int(observed.sum())), train_x[observed]])
    if np.linalg.matrix_rank(design) < 2:
        return None
    alpha, beta = np.linalg.lstsq(design, train_y[observed], rcond=None)[0]
    event_x, event_y = benchmark[first:last], stock[first:last]
    if not (np.isfinite(event_x).all() and np.isfinite(event_y).all()):
        return None
    return float((event_y - alpha - beta * event_x).sum())


def _session(dates, stamp):
    if pd.isna(stamp):
        return None
    index = int(dates.searchsorted(pd.Timestamp(stamp).normalize()))
    if index >= len(dates):
        return None
    return index


def event_cars(market, anchors, estimation=ESTIMATION, window=(-1, 1)):
    if windows_overlap(estimation, window):
        raise ValueError("estimation window overlaps the event window")
    dates, series, benchmark = _prepare(market)
    rows = []
    for record in anchors.itertuples(index=False):
        event = _session(dates, record.event_date)
        if event is None or record.bank_code not in series:
            continue
        car = _car_at(series[record.bank_code], benchmark, event, estimation, window)
        if car is None:
            continue
        rows.append({
            "bank_code": record.bank_code,
            "event_date": pd.Timestamp(dates[event]).normalize(),
            "period": getattr(record, "period", None),
            "quarter": getattr(record, "quarter", None),
            "d_npl_pct": getattr(record, "d_npl_pct", None),
            "surprise_d_npl_pct": getattr(record, "surprise_d_npl_pct", None),
            "car_pct": car,
        })
    return pd.DataFrame(rows, columns=["bank_code", "event_date", "period", "quarter", "d_npl_pct",
                                       "surprise_d_npl_pct", "car_pct"])


def _eligible(dates, stock, benchmark, banned, estimation, window):
    found = []
    start = max(0, -estimation[0])
    stop = len(dates) - max(0, window[1])
    for index in range(start, stop):
        stamp = pd.Timestamp(dates[index]).normalize()
        if stamp in banned:
            continue
        car = _car_at(stock, benchmark, index, estimation, window)
        if car is not None:
            found.append((stamp, car))
    return found


def placebo_dates(market, events, *, draws, seed, estimation=ESTIMATION, window=(-1, 1)):
    """One non-event session per bank per draw. The session is never that bank's event date."""
    dates, series, benchmark = _prepare(market)
    pools = {}
    for bank, group in events.groupby("bank_code", sort=False):
        if bank not in series:
            continue
        banned = set()
        for stamp in group["event_date"]:
            index = _session(dates, stamp)
            if index is not None:
                banned.add(pd.Timestamp(dates[index]).normalize())
            if pd.notna(stamp):
                banned.add(pd.Timestamp(stamp).normalize())
        pool = _eligible(dates, series[bank], benchmark, banned, estimation, window)
        if pool:
            pools[bank] = pool
    rng = np.random.default_rng(seed)
    rows = []
    for draw in range(draws):
        for bank, pool in pools.items():
            stamp, car = pool[int(rng.integers(len(pool)))]
            rows.append({"draw": draw, "bank_code": bank, "event_date": stamp, "car_pct": car})
    return pd.DataFrame(rows, columns=["draw", "bank_code", "event_date", "car_pct"])


def _mean_draws(frame, reps, seed):
    if frame.bank_code.nunique() < 2 or frame.empty:
        return None
    stats = frame.groupby("bank_code", sort=False)["car_pct"].agg(["sum", "size"])
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(stats), size=(reps, len(stats)))
    totals = stats["sum"].to_numpy()[pick].sum(axis=1)
    counts = stats["size"].to_numpy()[pick].sum(axis=1)
    return totals / counts


def _mean_block(frame, reps, seed):
    block = {
        "n": int(len(frame)),
        "clusters": int(frame.bank_code.nunique()) if len(frame) else 0,
        "mean_car_pct": None if frame.empty else float(frame.car_pct.mean()),
        "ci95": None,
        "bootstrap_se": None,
    }
    draws = None if frame.empty else _mean_draws(frame, reps, seed)
    if draws is not None:
        block["ci95"] = [float(value) for value in np.quantile(draws, [.025, .975])]
        block["bootstrap_se"] = float(draws.std(ddof=1))
    if block["bootstrap_se"] is not None:
        block["mde_80"] = MDE_FACTOR * block["bootstrap_se"]
    else:
        block["mde_80"] = None
    return block


def _difference_block(frame, reps, seed):
    rows = []
    for bank, group in frame.groupby("bank_code", sort=False):
        fall = group.loc[group.d_npl_pct.lt(0), "car_pct"]
        rise = group.loc[group.d_npl_pct.gt(0), "car_pct"]
        rows.append((fall.sum(), len(fall), rise.sum(), len(rise)))
    table = np.array(rows, dtype=float) if rows else np.zeros((0, 4))
    fall = frame.loc[frame.d_npl_pct.lt(0), "car_pct"]
    rise = frame.loc[frame.d_npl_pct.gt(0), "car_pct"]
    difference = None
    if len(fall) and len(rise):
        difference = float(fall.mean() - rise.mean())
    se = ci = None
    if len(table) >= 2:
        rng = np.random.default_rng(seed)
        pick = rng.integers(0, len(table), size=(reps, len(table)))
        chosen = table[pick]
        fall_n = chosen[:, :, 1].sum(axis=1)
        rise_n = chosen[:, :, 3].sum(axis=1)
        usable = (fall_n > 0) & (rise_n > 0)
        if int(usable.sum()) >= 20:
            kept = chosen[usable]
            diffs = kept[:, :, 0].sum(axis=1) / fall_n[usable] - kept[:, :, 2].sum(axis=1) / rise_n[usable]
            se = float(diffs.std(ddof=1))
            ci = [float(value) for value in np.quantile(diffs, [.025, .975])]
    return {
        "difference": difference,
        "n_fall": int(len(fall)),
        "n_rise": int(len(rise)),
        "bootstrap_se": se,
        "ci95": ci,
        "mde_80": None if se is None else MDE_FACTOR * se,
    }


def _slope_draws(frame, reps, seed):
    groups = {bank: group for bank, group in frame.groupby("bank_code", sort=False)}
    banks = np.array(list(groups))
    if len(banks) < 2:
        return None
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(banks), size=(reps, len(banks)))
    draws = []
    for choice in pick:
        sample = pd.concat([groups[bank] for bank in banks[choice]], ignore_index=True)
        design = np.column_stack([np.ones(len(sample)), sample["surprise_d_npl_pct"].to_numpy(dtype=float)])
        target = sample["car_pct"].to_numpy(dtype=float)
        if not np.isfinite(design).all() or not np.isfinite(target).all() or np.linalg.matrix_rank(design) < 2:
            continue
        draws.append(float(np.linalg.lstsq(design, target, rcond=None)[0][1]))
    return np.array(draws) if draws else None


def _window_summary(cars, window, reps, seed):
    summary = {
        "event": [int(window[0]), int(window[1])],
        **_mean_block(cars, reps, seed),
        "fall": _mean_block(cars.loc[cars.d_npl_pct.lt(0)] if len(cars) else cars, reps, seed + 1),
        "rise": _mean_block(cars.loc[cars.d_npl_pct.gt(0)] if len(cars) else cars, reps, seed + 2),
        "q4": _mean_block(cars.loc[cars.quarter.eq(4)] if len(cars) else cars, reps, seed + 3),
        "other": _mean_block(cars.loc[cars.quarter.ne(4)] if len(cars) else cars, reps, seed + 4),
        "fall_minus_rise": _difference_block(cars, reps, seed + 5) if len(cars) else _difference_block(cars, reps, seed),
    }
    usable = cars.dropna(subset=["car_pct", "surprise_d_npl_pct"]) if len(cars) else cars
    surprise = {"coefficient": None, "se": None, "p": None, "wild_p": None, "bootstrap_se": None,
                "ci95": None, "mde_80": None, "n": int(len(usable))}
    if len(usable) and usable.bank_code.nunique() >= 2 and usable.surprise_d_npl_pct.nunique() >= 2:
        fit, _ = _fit(usable, "car_pct", ["surprise_d_npl_pct"], bootstrap=True)
        term = fit["terms"].get("surprise_d_npl_pct", {})
        surprise.update(coefficient=term.get("coefficient"), se=term.get("se"), p=term.get("p"),
                        wild_p=term.get("wild_p"), n=fit["n"])
        draws = _slope_draws(usable, reps, seed + 6)
        if draws is not None and len(draws) >= 20:
            surprise["bootstrap_se"] = float(draws.std(ddof=1))
            surprise["ci95"] = [float(value) for value in np.quantile(draws, [.025, .975])]
            surprise["mde_80"] = MDE_FACTOR * surprise["bootstrap_se"]
    summary["surprise"] = surprise
    return summary


def _anchors(events, column):
    if column not in events.columns:
        return pd.DataFrame(columns=["bank_code", "event_date"])
    keep = ["bank_code", "period", "quarter", "d_npl_pct", "surprise_d_npl_pct", column]
    frame = events.loc[events[column].notna(), [name for name in keep if name in events.columns]].copy()
    frame = frame.rename(columns={column: "event_date"})
    frame["event_date"] = pd.to_datetime(frame["event_date"], errors="coerce")
    return frame.dropna(subset=["event_date"])


def _clock(market, anchors, draws, reps):
    if anchors.empty:
        return {"unavailable_reason": "no_valid_disclosure_dates", "windows": {}}
    windows = {name: _window_summary(event_cars(market, anchors, ESTIMATION, span), span, reps, BOOTSTRAP_SEED)
               for name, span in WINDOWS.items()}
    primary = windows["m1_p1"]["mean_car_pct"]
    picked = placebo_dates(market, anchors, draws=draws, seed=PLACEBO_SEED)
    means = picked.groupby("draw")["car_pct"].mean() if len(picked) else pd.Series(dtype=float)
    empirical = None
    if primary is not None and len(means):
        empirical = float(np.mean(np.abs(means.to_numpy()) >= abs(primary)))
    placebo = {
        "draws": int(draws), "seed": PLACEBO_SEED, "n_banks": int(picked.bank_code.nunique()) if len(picked) else 0,
        "mean": None if means.empty else float(means.mean()),
        "p05": None if means.empty else float(means.quantile(.05)),
        "p50": None if means.empty else float(means.quantile(.50)),
        "p95": None if means.empty else float(means.quantile(.95)),
        "empirical_p": empirical,
    }
    q2 = anchors.loc[anchors["quarter"].isin([2, 3])] if "quarter" in anchors else anchors.iloc[0:0]
    q2_cars = event_cars(market, q2, ESTIMATION, (-1, 1)) if len(q2) else pd.DataFrame(columns=event_cars(market, anchors.iloc[0:0]).columns)
    q2_summary = _window_summary(q2_cars, (-1, 1), reps, BOOTSTRAP_SEED + 11) if len(q2_cars) else {"n": 0, "mean_car_pct": None}
    if len(means) and q2_summary.get("mean_car_pct") is not None:
        q2_summary["empirical_p"] = float(np.mean(np.abs(means.to_numpy()) >= abs(q2_summary["mean_car_pct"])))
    return {"n_anchors": int(len(anchors)), "windows": windows, "placebo": placebo, "q2_q3": q2_summary}


def _legacy_power(events, published, reps):
    outcome = "deadline_car_pct" if "deadline_car_pct" in events.columns else "car_pct"
    if published is None or outcome not in events or "surprise_d_npl_pct" not in events:
        return None
    needed = ["bank_code", outcome, "expected_d_npl_pct", "surprise_d_npl_pct"]
    if any(name not in events for name in needed):
        return None
    sample = events.dropna(subset=needed).copy()
    sample["car_pct"] = sample[outcome]
    if sample.bank_code.nunique() < 2:
        return None
    groups = {bank: group for bank, group in sample.groupby("bank_code", sort=False)}
    banks = np.array(list(groups))
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    pick = rng.integers(0, len(banks), size=(reps, len(banks)))
    draws = []
    for choice in pick:
        part = pd.concat([groups[bank] for bank in banks[choice]], ignore_index=True)
        design = np.column_stack([
            np.ones(len(part)),
            part["expected_d_npl_pct"].to_numpy(dtype=float),
            part["surprise_d_npl_pct"].to_numpy(dtype=float),
        ])
        target = part["car_pct"].to_numpy(dtype=float)
        if np.linalg.matrix_rank(design) < 3:
            continue
        draws.append(float(np.linalg.lstsq(design, target, rcond=None)[0][2]))
    se = float(np.std(draws, ddof=1)) if len(draws) >= 20 else None
    coefficient = published.get("coefficient")
    return {
        "coefficient": coefficient, "se": published.get("se"), "p": published.get("p"),
        "wild_p": published.get("wild_p"), "bootstrap_se": se,
        "mde_80": None if se is None else MDE_FACTOR * se,
        "n": int(len(sample)), "clusters": int(sample.bank_code.nunique()),
    }


def _fmt(value, digits=3):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "n/a"
    return f"{value:.{digits}f}"


def _power_sentence(legacy, primary, *, english):
    factor = "2.8"
    if legacy and legacy.get("coefficient") is not None and legacy.get("mde_80") is not None:
        larger = abs(legacy["coefficient"]) >= legacy["mde_80"]
        if english:
            verdict = ("The point estimate is at least the minimum detectable effect, but the wild p does not reject zero, "
                       "so the slope is not established.") if larger else (
                "The estimate is smaller than the minimum detectable effect, so this p does not show there is no effect. "
                "The sample is too small to tell an effect of that size from zero.")
            return (f"On the existing [-10, +10] deadline CAR, the surprise slope is {_fmt(legacy['coefficient'])} "
                    f"(cluster p {_fmt(legacy.get('p'), 4)}, wild p {_fmt(legacy.get('wild_p'), 3)}, "
                    f"bootstrap SE {_fmt(legacy.get('bootstrap_se'))}, MDE { _fmt(legacy.get('mde_80'))} = {factor} x SE). "
                    + verdict)
        verdict = ("Ước lượng đạt mức phát hiện tối thiểu, nhưng p wild không tách khỏi 0, nên chưa kết luận có độ dốc.") if larger else (
            "Ước lượng nhỏ hơn mức phát hiện tối thiểu, nên p này không chứng minh là không có hiệu ứng. "
            "Mẫu chưa đủ để phân biệt hiệu ứng cỡ đó với 0.")
        return (f"Với CAR hạn nộp hiện có trên cửa sổ [-10, +10], hệ số bất ngờ là {_fmt(legacy['coefficient'])} "
                f"(p cụm {_fmt(legacy.get('p'), 4)}, p wild {_fmt(legacy.get('wild_p'), 3)}, "
                f"SE bootstrap {_fmt(legacy.get('bootstrap_se'))}, MDE {_fmt(legacy.get('mde_80'))} = {factor} × SE). "
                + verdict)
    surprise = (primary or {}).get("surprise") or {}
    if english:
        return (f"MDE at 80% power and 5% two-sided is {factor} times the bank-cluster bootstrap SE. "
                f"The [-1, +1] surprise slope is {_fmt(surprise.get('coefficient'))}, "
                f"MDE {_fmt(surprise.get('mde_80'))}.")
    return (f"MDE với lực 80% và kiểm định hai phía 5% bằng {factor} lần sai số chuẩn bootstrap cụm ngân hàng. "
            f"Hệ số bất ngờ trên cửa sổ [-1, +1] là {_fmt(surprise.get('coefficient'))}, "
            f"MDE {_fmt(surprise.get('mde_80'))}.")


def _reading(deadline, actual, legacy, *, english=False):
    window = ((deadline.get("windows") or {}).get("m1_p1") or {})
    placebo = deadline.get("placebo") or {}
    diff = window.get("fall_minus_rise") or {}
    power = _power_sentence(legacy, window, english=english)
    if english:
        gap = "No validated disclosure date is available, so the actual-date clock is not used." if actual.get("unavailable_reason") else (
            f"The actual-date clock has {actual.get('n_anchors', 0)} events.")
        return (f"Estimation uses sessions [-120, -21] and does not overlap the event window. "
                f"[-1, +1] mean CAR is {_fmt(window.get('mean_car_pct'))} (n={window.get('n', 0)}, "
                f"95% bank-bootstrap interval {_fmt((window.get('ci95') or [None, None])[0])} to "
                f"{_fmt((window.get('ci95') or [None, None])[1])}). "
                f"Fall minus rise is {_fmt(diff.get('difference'))}, MDE {_fmt(diff.get('mde_80'))}. "
                f"Random non-event dates ({placebo.get('draws', 0)} draws, seed {PLACEBO_SEED}) give empirical p "
                f"{_fmt(placebo.get('empirical_p'), 3)} against this mean CAR. {gap} {power}")
    gap = "Chưa có ngày công bố đã kiểm tra, nên chưa dùng mốc ngày thực." if actual.get("unavailable_reason") else (
        f"Mốc ngày thực có {actual.get('n_anchors', 0)} sự kiện.")
    return (f"Cửa sổ ước lượng là phiên [-120, -21] và không chồng lên cửa sổ sự kiện. "
            f"CAR trung bình [-1, +1] là {_fmt(window.get('mean_car_pct'))} (n={window.get('n', 0)}, "
            f"khoảng bootstrap ngân hàng 95% {_fmt((window.get('ci95') or [None, None])[0])} đến "
            f"{_fmt((window.get('ci95') or [None, None])[1])}). "
            f"Chênh CAR giảm trừ tăng là {_fmt(diff.get('difference'))}, MDE {_fmt(diff.get('mde_80'))}. "
            f"Ngày giả ngẫu nhiên không trùng ngày sự kiện ({placebo.get('draws', 0)} lần, seed {PLACEBO_SEED}) "
            f"có p thực nghiệm {_fmt(placebo.get('empirical_p'), 3)} so với CAR trung bình này. {gap} {power}")


def window_study(market, events, *, draws=500, reps=999, legacy_surprise=None):
    deadline = _clock(market, _anchors(events, "deadline"), draws, reps)
    actual_anchors = _anchors(events, "published_at")
    actual = _clock(market, actual_anchors, draws, reps) if len(actual_anchors) else {
        "unavailable_reason": "no_valid_disclosure_dates", "windows": {},
    }
    legacy = _legacy_power(events, legacy_surprise, reps)
    limit_en = ("CAR is the sum of market-model residuals in the window. It is not a tradable return and it does not "
                "show that an NPL disclosure caused the price move. A p above 0.05 does not show that the effect is zero "
                "when the estimate is inside the minimum detectable effect.")
    limit_vi = ("CAR là tổng phần dư mô hình thị trường trong cửa sổ. Đó không phải lợi suất có thể giao dịch và không "
                "chứng minh công bố NPL gây ra biến động giá. p trên 0,05 không chứng minh hiệu ứng bằng không khi "
                "ước lượng còn nằm trong mức phát hiện tối thiểu.")
    return {
        "estimation": [ESTIMATION[0], ESTIMATION[1]],
        "clocks": {"deadline": deadline, "actual": actual},
        "legacy_surprise": legacy,
        "reading_vi": _reading(deadline, actual, legacy),
        "reading_en": _reading(deadline, actual, legacy, english=True),
        "what_this_does_not_show_vi": limit_vi,
        "what_this_does_not_show_en": limit_en,
    }
