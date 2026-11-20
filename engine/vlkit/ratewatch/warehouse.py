"""RateWatch silver-to-gold transformation."""
from datetime import timedelta, timezone
from pathlib import Path
import json

import duckdb
import pandas as pd
import yaml

TZ = timezone(timedelta(hours=7))
RATE_COLUMNS = """run_id bank_code term_months channel tier rate_pct interest_basis
                  sheet_date observed_at reader source_url raw_sha256""".split()
METRICS = """npl_pct npl_change_pp npl_amount_growth_pct coverage_pct ldr_pct roa_pct nim_pct
             loan_growth_pct deposit_growth_pct""".split()
MARKET_FIELDS = "pb vol60_pct drawdown_pct foreign_net_20d_bn".split()
SOURCE_FIELDS = "source_id source_url observed_at raw_sha256 run_id".split()
MONEY_FIELDS = "date tenor rate_pct volume_bn tenor_days operation vnd_per_usd total_bn parts_bn".split()
MACRO_FIELDS = """month pct credit_bn household_deposits_bn credit_growth_ytd_pct deposit_growth_ytd_pct
                 organization_deposits_bn total_bn parts_bn methodology_break article_id source_date_field""".split()
TABLES = {
    "fact_bank_quarter": ["bank_code", "quarter", *METRICS, "coverage_change_pp", "denominator_flag"],
    "fact_bank_market_day": ["bank_code", "date", *MARKET_FIELDS],
    "fact_money_market_day": ["series", *MONEY_FIELDS],
    "fact_macro_month": ["series", *MACRO_FIELDS],
}


def bank_quarters(rows):
    """Compare the NPL and coverage ratios over the loan-growth window (year-on-year)."""
    index = {(row["bank"], row["quarter"]): row for row in rows}
    if len(index) != len(rows):
        raise ValueError("Trùng dữ liệu ngân hàng/quý")
    result = []
    for (bank, quarter), row in sorted(index.items()):
        previous = index.get((bank, str(pd.Period(quarter, freq="Q") - 4)), {})
        npl, last = row.get("npl_pct"), previous.get("npl_pct")
        growth = row.get("loan_growth_pct")
        coverage, previous_coverage = row.get("coverage_pct"), previous.get("coverage_pct")
        change = None if npl is None or last is None else npl - last
        amount = None if change is None or last <= 0 or growth is None or growth < -100 else (
            100 * ((1 + growth / 100) * npl / last - 1)
        )
        result.append({
            **row, "npl_change_pp": change, "npl_amount_growth_pct": amount,
            "coverage_change_pp": None if coverage is None or previous_coverage is None else coverage - previous_coverage,
            "denominator_flag": amount is not None and change < 0 and amount > 1e-10,
        })
    return result


def _register(con, name, records, columns):
    frame = pd.DataFrame(records, columns=columns)
    con.register("incoming", frame)
    con.execute(f"create or replace table gold.{name} as select * from incoming")
    con.unregister("incoming")


def _bank_register(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig"))
    banks = data["banks"] if isinstance(data, dict) else data
    return [
        {**bank, "ticker": bank.get("ticker") or "", "listed": bool(bank.get("ticker")),
         "rate_page": bank.get("rate_page") or None}
        for bank in banks
    ]


def transform(db, rate_files, banks_path, source_files):
    """Replace the gold star in one transaction, leaving prior gold intact on failure."""
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    banks = _bank_register(banks_path)
    ticker_codes = {bank["ticker"]: bank["code"] for bank in banks if bank["ticker"]}
    rates = [
        pd.read_parquet(path) if Path(path).suffix == ".parquet" else
        pd.read_csv(path, keep_default_na=False, dtype={"tier": str})
        for path in rate_files
    ]
    if not rates or any(sorted(frame.columns) != sorted(RATE_COLUMNS) for frame in rates):
        raise ValueError("Thiếu dữ liệu hoặc sai lược đồ lãi suất silver")
    frame = pd.concat(rates, ignore_index=True)
    frame["tier"] = frame["tier"].fillna("")
    if frame.empty:
        raise ValueError("Dữ liệu lãi suất silver rỗng")
    if any(pd.isna(frame[column]).any() or frame[column].eq("").any()
           for column in set(RATE_COLUMNS) - {"tier", "sheet_date"}):
        raise ValueError("Thiếu trường bắt buộc trong lãi suất silver")
    observed = frame["observed_at"].map(pd.Timestamp)
    if any(value.utcoffset() != timedelta(hours=7) for value in observed):
        raise ValueError("observed_at phải là thời gian Việt Nam (+07:00)")
    frame["observed_at"] = pd.to_datetime(observed, utc=True).dt.tz_convert(TZ)
    frame["sheet_date"] = pd.to_datetime(frame["sheet_date"].replace("", None), errors="raise")
    key = ["run_id", "bank_code", "term_months", "channel", "tier", "reader"]
    frame = frame.drop_duplicates()
    if frame.duplicated(key).any():
        raise ValueError("Trùng khóa lãi suất silver")
    if not set(frame.bank_code) <= {bank["code"] for bank in banks}:
        raise ValueError("Mã ngân hàng ngoài danh mục")

    sources, series_rows = {}, {}
    for path in sorted(map(Path, source_files)):
        if path.stem in series_rows:
            raise ValueError(f"Trùng nguồn silver: {path.stem}")
        series_rows[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        for row in series_rows[path.stem]:
            sources[row["source_id"]] = {key: row[key] for key in ("publisher", "licence", "method")}
            sources[row["source_id"]]["url"] = row["source_url"]
    policy = series_rows.get("policy")
    if policy is None:
        from .sources.policy import policy_rows
        policy = policy_rows()
        for row in policy:
            sources[row["source_id"]] = dict(url=row["source_url"], publisher=row["publisher"],
                                            licence=row["licence"], method=row["method"])
    sources.update({
        row.source_url: {"url": row.source_url, "publisher": "Bảng so sánh" if row.reader == "aggregator" else row.bank_code,
                         "licence": "Nguồn công khai", "method": row.reader}
        for row in frame.itertuples()
    })
    with duckdb.connect(str(db)) as con:
        con.execute("begin")
        con.execute("create schema if not exists gold")
        _register(con, "dim_bank", banks, ["code", "name_vi", "name_en", "ticker", "ownership", "listed", "rate_page"])
        _register(con, "dim_source", [{"id": key, **value} for key, value in sorted(sources.items())],
                  ["id", "publisher", "url", "licence", "method"])
        con.register("posted", frame[RATE_COLUMNS])
        con.execute("""
            create or replace table gold.fact_posted_rate as
            with observations as (
                select * exclude (sheet_date), sheet_date::date as sheet_date,
                    coalesce(sheet_date::date::varchar, run_id) as edition
                from posted
            ), reader_latest as (
                select * from observations qualify row_number() over (
                    partition by bank_code, term_months, channel, tier, edition, reader
                    order by observed_at desc, run_id desc
                ) = 1
            ), grades as (
                select bank_code, term_months, channel, tier, edition,
                    case when count(*) = 1 then 'single'
                         when max(rate_pct::decimal(10,4)) - min(rate_pct::decimal(10,4)) <= 0.005
                         then 'verified' else 'contested' end as grade
                from reader_latest group by all
            )
            select observations.*, grades.grade from observations join grades
                using (bank_code, term_months, channel, tier, edition)
            order by bank_code, term_months, channel, tier, edition, observed_at, reader
        """)
        con.execute("""
            create or replace table gold.dim_term as
            select distinct term_months,
                case when term_months = 0 then 'demand' when term_months < 6 then '1_to_under_6'
                     else '6_plus' end as ceiling_bucket from gold.fact_posted_rate order by term_months;
            create or replace table gold.dim_channel as select * from (values ('counter'), ('online')) as t(channel);
            create or replace view gold.v_rate_edition as
            select * from gold.fact_posted_rate qualify row_number() over (
                partition by bank_code, term_months, channel, tier, edition, reader
                order by observed_at desc, run_id desc
            ) = 1;
            create or replace view gold.v_curve_today as
            with latest as (
                select *, max(observed_at) over (
                    partition by bank_code, term_months, channel, tier, edition
                ) as edition_read_at from gold.v_rate_edition
            )
            select latest.* exclude (edition_read_at), b.name_vi, b.name_en, b.ownership, t.ceiling_bucket
            from latest join gold.dim_bank b on b.code = latest.bank_code
            join gold.dim_term t using (term_months)
            qualify dense_rank() over (
                partition by bank_code, term_months, channel, tier
                order by coalesce(sheet_date, timezone('Asia/Ho_Chi_Minh', edition_read_at)::date) desc,
                    edition_read_at desc, edition desc
            ) = 1
        """)
        quarters = bank_quarters(series_rows.get("fiin_quarter", []))
        market = series_rows.get("fiin_market", [])
        facts = {
            "fact_bank_quarter": [{**row, "bank_code": ticker_codes[row["bank"]]}
                                  for row in quarters if row["bank"] in ticker_codes],
            "fact_bank_market_day": [{**row, "bank_code": ticker_codes[row["bank"]]}
                                     for row in market if row["bank"] in ticker_codes],
            "fact_money_market_day": [{**row, "series": series} for series in ("interbank", "omo", "central_fx")
                                       for row in series_rows.get(series, [])],
            "fact_macro_month": [{**row, "series": series} for series in ("cpi", "sbv_credit", "sbv_deposit")
                                  for row in series_rows.get(series, [])],
        }
        for name, rows in facts.items():
            _register(con, name, rows, [*TABLES[name], *SOURCE_FIELDS])
        _register(con, "fact_policy_param", policy,
                  ["parameter", "metric", "value", "unit", "legal_ref", "valid_from", "basis", *SOURCE_FIELDS])
        con.execute("""
            create or replace table gold.dim_date as
            with dates as (
                select sheet_date as date from gold.fact_posted_rate
                union select timezone('Asia/Ho_Chi_Minh', observed_at)::date from gold.fact_posted_rate
                union select date::date from gold.fact_money_market_day
                union select date::date from gold.fact_bank_market_day
                union select (month::varchar || '-01')::date from gold.fact_macro_month
                union select valid_from::date from gold.fact_policy_param
            )
            select date, year(date) as year, month(date) as month, day(date) as day
            from dates where date is not null order by date;
            create or replace view gold.v_bank_profile as
            with q as (
                select * from gold.fact_bank_quarter qualify row_number() over (
                    partition by bank_code order by quarter desc
                ) = 1
            ), m as (
                select * from gold.fact_bank_market_day qualify row_number() over (
                    partition by bank_code order by date desc
                ) = 1
            )
            select b.*, q.* exclude(bank_code),
                m.date as market_date, m.pb, m.vol60_pct, m.drawdown_pct, m.foreign_net_20d_bn
            from gold.dim_bank b left join q on q.bank_code = b.code
            left join m on m.bank_code = b.code
        """)
        con.execute("commit")
