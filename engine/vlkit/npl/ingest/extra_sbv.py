"""SBV system credit and deposit growth by month, plus the system LDR context."""

from urllib.parse import quote

import pandas as pd

from .extra_landing import FetchError, land, write_silver
from .sbv_articles import parse_monthly

SBV = "https://sbv.gov.vn"
CREDIT_ID, DEPOSIT_ID = "10034332", "10038520"
COLUMNS = ["month", "credit_bn", "credit_growth_ytd_pct", "household_deposits_bn",
           "household_deposit_growth_ytd_pct", "organization_deposits_bn", "deposits_bn", "ldr_pct"]


def url_for(series, first_year=2019, today="2026-12-31"):
    url = f"{SBV}/o/article/v1.0/articles?scopeKey=20117&contentStructureId=" \
          f"{CREDIT_ID if series == 'sbv_credit' else DEPOSIT_ID}&pageSize=100"
    if series == "sbv_credit":
        condition = f"status eq 0 and Date62813077 ne '' and Date62813077 ge '{first_year}-01-01' " \
                    f"and Date62813077 le '{today}'"
        url += "&filter=" + quote(condition)
    return url


def frame_from(credit, deposits):
    """Merge the credit and deposit series on month and derive the system loan-to-deposit ratio."""
    by_month = {record["month"]: record for record in credit if record.get("month")}
    deposits_by_month = {record["month"]: record for record in deposits if record.get("month")}
    rows = []
    for month in sorted(set(by_month) | set(deposits_by_month)):
        credit_row, deposit_row = by_month.get(month, {}), deposits_by_month.get(month, {})
        household = deposit_row.get("household_deposits_bn")
        organization = deposit_row.get("organization_deposits_bn")
        total = None
        if household is not None or organization is not None:
            total = sum(value for value in (household, organization) if value is not None)
        credit_bn = credit_row.get("credit_bn")
        rows.append({
            "month": month, "credit_bn": credit_bn,
            "credit_growth_ytd_pct": credit_row.get("credit_growth_ytd_pct"),
            "household_deposits_bn": household,
            "household_deposit_growth_ytd_pct": deposit_row.get("deposit_growth_ytd_pct"),
            "organization_deposits_bn": organization, "deposits_bn": total,
            "ldr_pct": round(credit_bn / total * 100, 2) if credit_bn is not None and total else None,
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def run(lake, fetcher, run_id, today="2026-12-31"):
    series, errors = {}, {}
    for name in ("sbv_credit", "sbv_deposit"):
        url = url_for(name, today=today)
        try:
            response = fetcher.get(url)
        except FetchError as exc:
            errors[name] = str(exc)[:160]
            continue
        land(lake, run_id, "sbv", name, response.content, "json", {"url": url})
        try:
            series[name] = parse_monthly(response.content, name)
        except (ValueError, KeyError) as exc:
            errors[name] = f"parse: {type(exc).__name__}: {exc}"[:160]
    frame = frame_from(series.get("sbv_credit", []), series.get("sbv_deposit", []))
    write_silver(lake, "sbv_system.parquet", frame, {"sources": [url_for(n, today=today) for n in series]})
    stats = {"rows": len(frame), "months": [frame["month"].min(), frame["month"].max()] if len(frame) else None,
             "credit_rows": len(series.get("sbv_credit", [])), "deposit_rows": len(series.get("sbv_deposit", []))}
    if errors:
        stats["errors"] = errors
    return frame, stats
