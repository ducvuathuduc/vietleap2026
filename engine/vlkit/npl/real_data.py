"""Normalize D1 Silver data and build the six-table analytical star."""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from .snapshot_metrics import OPTIONAL_SIGNAL_DELTAS


RATIOS = {
    "npl_pct": ("npl", "problem_loans_and_leases_calculated_as_percentage_of_gross_loans",),
    "coverage_pct": ("coverage", "loan_loss_reserves_to_npls", "loan_loss_reserves_to_np_ls", "loan_loss_reserves_to_npl"),
    "ldr_pct": ("ldr", "ldr_percentage"),
    "roa_pct": ("return_on_average_assets", "return_on_assets", "roaa", "roa"),
    "nim_pct": ("net_interest_margin", "net_interest_margin_percentage", "nim"),
    "loan_growth_yoy_pct": ("average_loans_growth_percentage_yo_y", "average_loans_growth_percentage_yoy",
                            "loan_growth_percentage_yoy", "loan_growth_yoy", "loan_growth"),
}
STATE = {"VCB", "BID", "CTG"}
DEADLINE_SOURCE = "https://vbpl.vn/FileData/TW/Lists/VBPQ/Attachments/146048/VanBanGoc_96-2020-TT-BTC.pdf"
OWNERSHIP_SOURCES = (
    "[VCB](https://portal.vietcombank.com.vn/VCBDigital/2023/BCTN/en/executive-board-report/), "
    "[BID](https://bidv.com.vn/wps/wcm/connect/2961231d-3291-4326-89b6-7350d04c496c/BIDV%2BAnnual%2BReport%2B2024.FNL.pdf?MOD=AJPERES), "
    "[CTG](https://investor.vietinbank.vn/vi/w/information-on-shareholders-owning-more-than-1-charter-capital-of-vietinbank)"
)


def _field(frame, names, *, required=False):
    # Nested Silver fields may retain their category prefix.
    by_name = {str(column).lower(): column for column in frame}
    for name in names:
        if name in by_name:
            return by_name[name]
    for name in names:
        matches = [column for key, column in by_name.items() if key.endswith("_" + name)]
        if len(matches) == 1:
            return matches[0]
    if required:
        raise ValueError(f"Thiếu cột bắt buộc {names[0]}")
    return None


def _numeric(frame, column):
    if column is None:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _ticker(series):
    return series.astype("string").str.strip().str.upper()


def _bank_code(series):
    return _ticker(series).replace({"BIDV": "BID"})


def clean_quarters(raw, *, canonical_fractions=False, round_digits=2):
    """Keep valid-key observations, preserving nullable metrics and gap boundaries."""
    log = []

    def record(step, before, after, detail):
        log.append(dict(step=step, before=before, after=after, detail=detail))

    panel = pd.DataFrame(index=raw.index)
    panel["ticker"] = _ticker(raw[_field(raw, ("ticker", "organ_code", "bank_code"), required=True)])
    basis = _field(raw, ("basis", "report_type", "type"))
    panel["basis"] = raw[basis].astype("string").str.strip().str.lower() if basis else "consolidated"
    period = _field(raw, ("period", "period_id"))
    if period:
        panel["period"] = raw[period].astype("string").str.strip().str.upper()
    else:
        year = _numeric(raw, _field(raw, ("year",), required=True)).astype("Int64")
        quarter = _numeric(raw, _field(raw, ("quarter",), required=True)).astype("Int64")
        panel["period"] = year.astype("string") + "Q" + quarter.astype("string")
    sources = {}
    for name, aliases in RATIOS.items():
        columns = [_field(raw, (candidate,)) for candidate in (name, *aliases)]
        columns = [column for column in columns if column is not None]
        column = next((column for column in columns if raw[column].notna().any()), columns[0] if columns else None)
        sources[name] = column
        panel[name] = _numeric(raw, column)
    if sources["npl_pct"] is None:
        raise ValueError("Silver không có trường tỷ lệ nợ xấu")
    signal_fields = [field for field in OPTIONAL_SIGNAL_DELTAS if field in raw]
    for field in signal_fields:
        panel[field] = _numeric(raw, field)
    for field in ("g2_ratio", "writeoff_ratio", "npl_formation"):
        if field in raw:
            panel[field] = _numeric(raw, field)
    valid = (panel["ticker"].str.fullmatch(r"[A-Z0-9]+").fillna(False)
             & panel["period"].str.fullmatch(r"\d{4}Q[1-4]").fillna(False)
             & panel["basis"].isin(["consolidated", "separate"]))
    panel = panel.loc[valid].copy()
    record("Kiểu dữ liệu và lược đồ", len(raw), len(panel),
           f"Loại khóa sai. Ánh xạ trường tỷ lệ: {sources}.")
    missing = panel[list(RATIOS)].isna().sum().to_dict()
    record("Giá trị thiếu", len(panel), len(panel),
           f"Số ô thiếu: {missing}. Giữ nguyên giá trị thiếu, kể cả NPL; mỗi mô hình dùng mẫu hợp lệ riêng.")
    before = len(panel)
    panel["ticker"] = panel["ticker"].replace({"BIDV": "BID"})
    key = ["ticker", "period", "basis"]
    panel = panel.drop_duplicates()
    if panel.duplicated(key).any():
        raise ValueError("Trùng khóa (ticker, period, basis) với giá trị tỷ lệ khác nhau")
    record("Bản ghi trùng", before, len(panel),
           "Chuẩn hóa bí danh BIDV → BID và gộp dòng có cùng khóa và cùng giá trị phân tích.")
    for name, column in sources.items():
        if column is not None and (canonical_fractions or str(column).lower() != name):
            panel[name] *= 100
    invalid_npl = panel["npl_pct"].notna() & ~panel["npl_pct"].between(0, 100, inclusive="left")
    invalid_coverage = panel["coverage_pct"].lt(0)
    precision = "giữ nguyên độ chính xác nguồn"
    if round_digits is not None:
        panel[list(RATIOS)] = panel[list(RATIOS)].round(round_digits)
        precision = f"làm tròn {round_digits} chữ số"
    record("Đơn vị", len(panel), len(panel),
           f"Quy đổi tỷ lệ FiinQuant từ phân số sang %, {precision}; biến động dùng điểm phần trăm.")
    panel["bank_code"] = _bank_code(panel["ticker"])
    panel["ownership"] = np.where(panel["bank_code"].isin(STATE), "state", "private")
    record("Phân nhóm", len(panel), len(panel),
           f"Mã niêm yết → mã ngân hàng → sở hữu. Nhóm nhà nước gồm VCB, BID, CTG. {OWNERSHIP_SOURCES}.")
    outliers = {}
    for name in RATIOS:
        values = panel[name]
        lower, upper = values.quantile([.25, .75])
        iqr = upper - lower
        sd = values.std(ddof=0)
        z_score = (values - values.mean()).abs().div(sd) if sd > 0 else values * 0
        panel[f"{name}_iqr_flag"] = (values < lower - 1.5 * iqr) | (values > upper + 1.5 * iqr)
        panel[f"{name}_z_flag"] = z_score.gt(3)
        outliers[name] = (int(panel[f"{name}_iqr_flag"].sum()), int(panel[f"{name}_z_flag"].sum()))
    record("Ngoại lai", len(panel), len(panel),
           f"Số cờ (IQR 1,5 lần; |z| > 3): {outliers}. Giữ quan sát gắn cờ ngoại lai.")
    bad_npl = invalid_npl | panel["npl_pct"].ge(100)
    bad_coverage = invalid_coverage
    panel.loc[bad_npl, "npl_pct"] = np.nan
    panel.loc[bad_coverage, "coverage_pct"] = np.nan
    panel["year"] = panel["period"].str[:4].astype(int)
    panel["quarter"] = panel["period"].str[-1:].astype(int)
    panel["quarter_id"] = panel["year"] * 4 + panel["quarter"]
    panel = panel.sort_values(["bank_code", "basis", "quarter_id"]).reset_index(drop=True)
    grouped = panel.groupby(["bank_code", "basis"], sort=False)
    gap = grouped["quarter_id"].diff()
    for name in RATIOS:
        panel[f"d_{name}"] = grouped[name].diff().where(gap.eq(1))
    panel[signal_fields] = panel[signal_fields].where(gap.eq(1), axis=0)
    record("Quy tắc nghiệp vụ", len(panel), len(panel),
           f"Chuyển thành thiếu {bad_npl.sum()} giá trị NPL ngoài [0, 100) và {bad_coverage.sum()} "
           f"giá trị bao phủ âm. Phát hiện {gap.gt(1).sum()} khoảng trống. Chỉ tính chênh lệch hai quý liên tiếp.")
    return panel, log


def read_silver(folder):
    """Read the full D1 delivery. DuckDB also supports Parquet without pyarrow."""
    names = ["bank_quarter", "bank_annual", "price_daily", "valuation_daily", "foreign_daily"]
    paths = {name: folder / f"{name}.parquet" for name in names}
    calendar = folder / "report_calendar.csv"
    absent = [path.name for path in [*paths.values(), calendar] if not path.is_file()]
    if absent:
        raise ValueError(f"Thiếu đầu vào Silver: {', '.join(absent)}")
    optional_parquet = ("sbv_system", "wdi_bank", "notes_bank_quarter", "fiin_screening")
    optional_csv = ("field_map_ratios", "disclosure_dates", "case_tcb", "legal_register", "notes_links", "notes_gate")
    paths.update({name: folder / f"{name}.parquet" for name in optional_parquet
                  if (folder / f"{name}.parquet").is_file()})
    with duckdb.connect() as db:
        tables = {name: db.read_parquet(str(path)).df() for name, path in paths.items()}
    for name in optional_csv:
        path = folder / f"{name}.csv"
        if path.is_file():
            tables[name] = pd.read_csv(path)
    tables["report_calendar"] = pd.read_csv(calendar)
    if "notes_bank_quarter" in tables and "notes_links" in tables:
        keys = ["bank", "period", "source_url"]
        links = tables["notes_links"].rename(columns={"url": "source_url", "statement_type": "registered_scope"})
        links = links[[*keys, "registered_scope"]].drop_duplicates().dropna(subset=keys)
        links = links.loc[~links.duplicated(keys, keep=False)]
        notes = tables["notes_bank_quarter"].merge(links, on=keys, how="left", validate="many_to_one")
        notes["statement_type"] = (notes["statement_type"].fillna(notes["registered_scope"])
                                   if "statement_type" in notes else notes["registered_scope"])
        tables["notes_bank_quarter"] = notes.drop(columns="registered_scope")
    return tables


def _dates(series):
    return pd.to_datetime(series, format="mixed", errors="coerce").dt.normalize()


def clean_calendar(raw):
    """Use Article 14(3) 30-day anchor for listed parent companies with consolidated statements."""
    period = _field(raw, ("period", "period_id"))
    quarter = _field(raw, ("quarter",), required=period is None)
    if period is not None:
        periods = raw[period].astype("string").str.strip().str.upper()
    elif raw[quarter].astype("string").str.fullmatch(r"\d{4}Q[1-4]").all():
        periods = raw[quarter].astype("string")
    else:
        year = _numeric(raw, _field(raw, ("year",), required=True)).astype("Int64")
        number = _numeric(raw, quarter).astype("Int64")
        periods = year.astype("string") + "Q" + number.astype("string")
    quarter_end = _field(raw, ("quarter_end", "quarter_end_date", "period_end"))
    deadline = _field(raw, ("deadline", "disclosure_deadline", "deadline_date", "statutory_deadline"), required=True)
    dates = pd.PeriodIndex(periods, freq="Q").to_timestamp(how="end").normalize()
    calendar = pd.DataFrame({
        "period": periods,
        "quarter_end": _dates(raw[quarter_end]) if quarter_end is not None else dates,
        "silver_deadline": _dates(raw[deadline]),
        "deadline": dates + pd.Timedelta(days=30),
    })
    for name in ("source_url", "legal_basis", "source", "rule", "circular", "article"):
        if name in raw:
            calendar[f"silver_{name}"] = raw[name]
    if (calendar["quarter_end"].isna().any() or calendar["silver_deadline"].isna().any()
            or (calendar["quarter_end"].to_numpy() != dates.to_numpy()).any()):
        raise ValueError("Lịch công bố có ngày không hợp lệ")
    calendar = calendar.drop_duplicates()
    if calendar["period"].duplicated().any():
        raise ValueError("Lịch công bố có khóa kỳ trùng")
    if calendar["silver_deadline"].le(calendar["quarter_end"]).any():
        raise ValueError("Hạn công bố phải sau ngày kết thúc quý")
    calendar["deadline_source_url"] = DEADLINE_SOURCE
    return calendar.sort_values("period").reset_index(drop=True)


def _daily_keys(raw):
    ticker = _field(raw, ("ticker", "symbol", "organ_code", "bank_code"), required=True)
    date = _field(raw, ("date", "trading_date", "trading_time", "trade_date", "time", "timestamp"), required=True)
    return pd.DataFrame({"bank_code": _bank_code(raw[ticker]), "date": _dates(raw[date])})


def _daily_unique(frame, metrics):
    keys = ["bank_code", "date"]
    frame = frame.dropna(subset=keys).drop_duplicates()
    if frame.duplicated(keys).any():
        raise ValueError(f"Trùng khóa ngày với giá trị khác nhau: {', '.join(metrics)}")
    return frame


def clean_market(tables, banks):
    price = tables["price_daily"]
    returns = _daily_keys(price)
    returns["close"] = _numeric(price, _field(price, ("adjusted_close", "adj_close", "close", "close_price"), required=True))
    returns = _daily_unique(returns, ["close"]).sort_values(["bank_code", "date"])
    returns = returns.loc[returns["bank_code"].isin([*banks, "VNINDEX"])].copy()
    returns.loc[returns["close"].le(0), "close"] = np.nan
    sessions = returns.loc[returns["bank_code"].eq("VNINDEX") & returns["close"].notna(), "date"]
    if sessions.empty:
        raise ValueError("Không có phiên giao dịch VNINDEX có giá hợp lệ")
    session_id = pd.Series(range(len(sessions)), index=sessions)
    returns["session"] = returns["date"].map(session_id)
    grouped = returns.groupby("bank_code", sort=False)
    returns["return_pct"] = (grouped["close"].pct_change(fill_method=None) * 100).where(grouped["session"].diff().eq(1))
    returns = returns.loc[returns["session"].notna(), ["bank_code", "date", "return_pct"]]
    for table, aliases in (
        ("valuation_daily", {"pe": ("pe", "p_e", "pe_ratio"), "pb": ("pb", "p_b", "pb_ratio")}),
        ("foreign_daily", {
            "foreign_buy_value": ("foreign_buy_value_total", "foreign_buy_value", "buy_value", "foreign_buy_val"),
            "foreign_sell_value": ("foreign_sell_value_total", "foreign_sell_value", "sell_value", "foreign_sell_val"),
            "foreign_net_value": ("foreign_net_value_total", "foreign_net_value", "net_value", "foreign_net_val"),
            "foreign_room": ("foreign_room", "room", "current_room", "foreign_current_room"),
        }),
    ):
        raw = tables[table]
        daily = _daily_keys(raw)
        for metric, fields in aliases.items():
            daily[metric] = _numeric(raw, _field(raw, fields))
        daily = daily.loc[daily["bank_code"].isin([*banks, "VNINDEX"])]
        returns = returns.merge(_daily_unique(daily, aliases), on=["bank_code", "date"], how="left",
                                validate="one_to_one")
    return returns


def write_star(path, panel, market, calendar, events):
    banks = panel[["bank_code", "ticker", "ownership"]].drop_duplicates()
    if market["bank_code"].eq("VNINDEX").any():
        banks = pd.concat([banks, pd.DataFrame([dict(bank_code="VNINDEX", ticker="VNINDEX", ownership="index")])])
    quarters = panel.drop(columns=["ticker", "ownership", "year", "quarter", "quarter_id"])
    periods = panel[["period", "year", "quarter"]].drop_duplicates()
    periods = periods.merge(calendar[["period", "quarter_end"]], on="period", how="outer")
    parsed = pd.PeriodIndex(periods["period"], freq="Q")
    periods["year"], periods["quarter"] = parsed.year, parsed.quarter
    periods["quarter_end"] = parsed.to_timestamp(how="end").normalize()
    event_dates = ["deadline", "event_date", "deadline_event_date", "published_at", "anchor_date"]
    dates = pd.concat([market["date"], calendar["deadline"], *[events[column] for column in event_dates]]
                      ).dropna().drop_duplicates()
    dates = dates.to_frame(name="date")
    dates["year"] = dates["date"].dt.year
    dates["month"] = dates["date"].dt.month
    frames = {
        "dim_bank": (banks, "PRIMARY KEY (bank_code)"),
        "dim_period": (periods, "PRIMARY KEY (period)"),
        "dim_date": (dates, "PRIMARY KEY (date)"),
        "fact_bank_quarter": (quarters, "PRIMARY KEY (bank_code, period, basis), "
                              "FOREIGN KEY (bank_code) REFERENCES dim_bank(bank_code), "
                              "FOREIGN KEY (period) REFERENCES dim_period(period)"),
        "fact_bank_market_day": (market, "PRIMARY KEY (bank_code, date), "
                                 "FOREIGN KEY (bank_code) REFERENCES dim_bank(bank_code), "
                                 "FOREIGN KEY (date) REFERENCES dim_date(date)"),
        "fact_report_event": (events, "PRIMARY KEY (bank_code, period, basis), "
                              "FOREIGN KEY (bank_code, period, basis) REFERENCES fact_bank_quarter(bank_code, period, basis), "
                              "FOREIGN KEY (deadline) REFERENCES dim_date(date), "
                              "FOREIGN KEY (event_date) REFERENCES dim_date(date), "
                              "FOREIGN KEY (deadline_event_date) REFERENCES dim_date(date), "
                              "FOREIGN KEY (published_at) REFERENCES dim_date(date), "
                              "FOREIGN KEY (anchor_date) REFERENCES dim_date(date)"),
    }
    with duckdb.connect(str(Path(path))) as db:
        for name, (frame, constraints) in frames.items():
            db.register("star_frame", frame)
            metadata = db.execute("DESCRIBE SELECT * FROM star_frame").fetchall()
            columns = ", ".join(f'"{column}" {dtype}' for column, dtype, *_ in metadata)
            db.execute(f"CREATE TABLE {name} ({columns}, {constraints})")
            db.execute(f"INSERT INTO {name} SELECT * FROM star_frame")
            db.unregister("star_frame")
