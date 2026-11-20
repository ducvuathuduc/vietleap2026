"""Decide whether a Last-Modified stamp is a usable quarterly disclosure date."""
import pandas as pd


def assess_last_modified(frame, calendar):
    """Keep a date only when the batch looks like filings, and the date itself falls in the window.

    The window is after the quarter end and on or before the filing deadline plus 10 days.
    A batch stamped on one day, or dated far from the deadline, is not used.
    """
    work = frame.copy()
    if "ticker" not in work.columns and "bank" in work.columns:
        work = work.rename(columns={"bank": "ticker"})
    work["published_at"] = pd.to_datetime(work["published_at"], errors="coerce", utc=True)
    work["published_at"] = work["published_at"].dt.tz_convert("Asia/Ho_Chi_Minh").dt.tz_localize(None).dt.normalize()
    work["quarter_end"] = pd.PeriodIndex(work["period"].astype(str), freq="Q").to_timestamp(how="end").normalize()
    cal = calendar.copy()
    cal["period"] = cal["period"].astype(str)
    deadline_name = "deadline" if "deadline" in cal.columns else "disclosure_deadline"
    cal["deadline"] = pd.to_datetime(cal[deadline_name], errors="coerce").dt.normalize()
    work = work.drop(columns=["deadline"], errors="ignore").merge(cal[["period", "deadline"]], on="period", how="left")
    work["deadline"] = work["deadline"].fillna(work["quarter_end"] + pd.Timedelta(days=30))
    limit = work["deadline"] + pd.Timedelta(days=10)
    dated = work["published_at"].notna()
    in_window = dated & work["published_at"].gt(work["quarter_end"]) & work["published_at"].le(limit)
    lag = (work.loc[dated, "published_at"] - work.loc[dated, "quarter_end"]).dt.days
    share = float(in_window[dated].mean()) if dated.any() else 0.0
    unique = int(work.loc[dated, "published_at"].nunique())
    median = float(lag.median()) if len(lag) else None
    plausible = bool(dated.sum() >= 8 and share >= 0.5 and unique >= 8 and median is not None and 0 < median <= 50)
    work["valid"] = in_window if plausible else False
    work["source"] = "vietstock_last_modified"
    return {
        "plausible": plausible,
        "n": int(dated.sum()),
        "share_in_window": share,
        "n_unique_dates": unique,
        "median_lag_days": median,
        "frame": work,
    }
