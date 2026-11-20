"""Profile silver/bank_quarter.parquet and summarise quality for the NPL panel."""

from pathlib import Path

import pandas as pd

from .flatten import CORE, KEY


def _core_columns(frame, field_map):
    if field_map is None:
        return {alias: alias for alias in CORE if alias in frame}
    return {alias: rows.iloc[0] for alias in CORE
            if not (rows := field_map.loc[field_map["alias"] == alias, "column"]).empty
            and rows.iloc[0] in frame}


def _gaps(frame):
    lines = []
    for ticker, group in frame.groupby("ticker"):
        quarters = sorted(group["period"].dropna())
        indexes = [int(p[:4]) * 4 + int(p[-1]) - 1 for p in quarters if "Q" in p]
        missing = indexes[-1] - indexes[0] + 1 - len(set(indexes)) if indexes else 0
        lines.append((ticker, len(quarters), quarters[0] if quarters else "", quarters[-1] if quarters else "", missing))
    return pd.DataFrame(lines, columns=["ticker", "quarters", "first", "last", "missing_quarters"])


def _outliers(frame, columns):
    rows = []
    for alias, column in columns.items():
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        if len(values) < 4 or values.std() == 0:
            rows.append((alias, len(values), 0, 0, "n/a"))
            continue
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        outside = ((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum()
        z = ((values - values.mean()) / values.std()).abs()
        rows.append((alias, len(values), int(outside), int((z > 3).sum()),
                     f"{values.min():.4g}..{values.max():.4g}"))
    return pd.DataFrame(rows, columns=["core_field", "n", "iqr_outliers", "z_gt_3", "range"])


def _correlations(frame, columns):
    table = frame[[*columns.values()]].apply(pd.to_numeric, errors="coerce")
    table.columns = list(columns)
    corr = table.corr()
    pairs = [(a, b, corr.loc[a, b]) for i, a in enumerate(corr.columns) for b in corr.columns[i + 1:]]
    pairs = [pair for pair in pairs if pd.notna(pair[2])]
    return sorted(pairs, key=lambda pair: abs(pair[2]), reverse=True)


def build(lake, out):
    lake, out = Path(lake), Path(out)
    frame = pd.read_parquet(lake / "silver/bank_quarter.parquet")
    map_path = lake / "silver/field_map_ratios.csv"
    field_map = pd.read_csv(map_path) if map_path.exists() else None
    core = _core_columns(frame, field_map)
    out.mkdir(parents=True, exist_ok=True)

    from ydata_profiling import ProfileReport

    ProfileReport(frame, title="NPL bank-quarter silver", minimal=True).to_file(
        out / "bank_quarter_profile.html")

    gaps = _gaps(frame)
    duplicates = int(frame.duplicated(KEY).sum())
    missing = frame.isna().mean().sort_values(ascending=False)
    outliers = _outliers(frame, core)
    correlations = _correlations(frame, core)
    lines = [
        "# NPL bank_quarter — EDA summary", "",
        f"- Shape: {len(frame)} rows x {len(frame.columns)} columns",
        f"- Banks: {frame['ticker'].nunique()}; periods {frame['period'].min()}..{frame['period'].max()}",
        f"- Duplicates on (ticker, period): {duplicates}",
        f"- Core fields resolved: {', '.join(f'{a}->{c}' for a, c in core.items()) or 'none'}",
        "", "## Missing share per field", "",
        *[f"- {name}: {share:.1%}" for name, share in missing.items()],
        "", "## Quarter gaps per ticker", "",
        *[f"- {row.ticker}: {row.quarters} quarters {row.first}..{row.last}, "
          f"{row.missing_quarters} missing inside range" for row in gaps.itertuples()],
        "", "## Outliers on core fields", "",
        *[f"- {row.core_field}: n={row.n}, IQR outliers={row.iqr_outliers}, "
          f"|z|>3={row.z_gt_3}, range={row.range}" for row in outliers.itertuples()],
        "", "## Top correlations among core ratios", "",
        *[f"- {a} vs {b}: {value:.3f}" for a, b, value in correlations[:10]],
        "", "Ratios are vendor fractions (0.01 = 1%).",
    ]
    (out / "bank_quarter_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)
