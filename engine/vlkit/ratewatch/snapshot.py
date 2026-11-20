"""Build and validate the public RateWatch snapshot before replacing published artifacts."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
import os
import re
import subprocess

import duckdb
from jsonschema import Draft202012Validator, FormatChecker

from .quality import evaluate, valid_url
from .sources import atomic, encode
from .warehouse import MARKET_FIELDS, METRICS, TZ

SCHEMA = Path(__file__).with_name("schema") / "snapshot.schema.json"
GRADE_ORDER = {"verified": 0, "single": 1, "contested": 2}


def _read(con, sql):
    cursor = con.execute(sql)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _iso(value):
    if value is None:
        return None
    return (value.replace(tzinfo=TZ) if value.tzinfo is None else value.astimezone(TZ)).isoformat(timespec="seconds")


def _rate_groups(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in ("bank_code", "term_months", "channel", "tier", "edition"))].append(row)
    for (bank, term, channel, tier, _), readers in groups.items():
        lead = min(readers, key=lambda row: (row["reader"] == "aggregator",
                                            row["reader"] == "tinyfish", row["reader"]))
        yield bank, {
            "term_months": term, "channel": channel, "tier": tier, "grade": lead["grade"],
            "rate_pct": lead["rate_pct"],
            "readers": [
                {"reader": row["reader"], "value": row["rate_pct"], "source_url": row["source_url"],
                 "observed_at": _iso(row["observed_at"])}
                for row in readers
            ],
        }, lead


def _ceiling_stats(groups, ceiling):
    usable = [(bank, rate) for bank, rate, _ in groups if rate["grade"] != "contested"]
    short = [(bank, rate) for bank, rate in usable if 1 <= rate["term_months"] < 6]
    basis = "verified" if any(rate["grade"] == "verified" for _, rate in short) else "single"
    selected = [(bank, rate) for bank, rate in short if rate["grade"] == basis]
    term_pairs = defaultdict(dict)
    for bank, rate in usable:
        if rate["term_months"] in {5, 6}:
            term_pairs[bank, rate["channel"], rate["tier"]][rate["term_months"]] = rate
    jumps = [
        pair[6]["rate_pct"] - pair[5]["rate_pct"]
        for pair in term_pairs.values()
        if len(pair) == 2 and all(rate["grade"] == basis for rate in pair.values())
    ]
    return dict(quotes_1_5m=len(selected), at_ceiling=sum(rate["rate_pct"] == ceiling for _, rate in selected),
                above=sum(rate["rate_pct"] > ceiling for _, rate in selected),
                jump_5_6_pp_median=round(median(jumps), 6) if jumps else None,
                n_banks=len({bank for bank, _ in selected}), grade_basis=basis)


def _policy(con):
    entries = _read(con, "select * from gold.fact_policy_param")
    groups = defaultdict(dict)
    for row in entries:
        groups[row["parameter"]][row["metric"]] = row
    ceiling = groups["ceiling"]["pct"]
    cap = groups["cap"]["vnd"]
    premium = groups["premium"]["pct"]
    coverage = groups["insured_coverage"]
    depositors = coverage["depositors_pct"]
    return {
        "ceiling": dict(pct=ceiling["value"], terms=ceiling["basis"], legal_ref=ceiling["legal_ref"],
                        valid_from=ceiling["valid_from"]),
        "cap": dict(vnd=int(cap["value"]), legal_ref=cap["legal_ref"], valid_from=cap["valid_from"]),
        "premium": dict(pct=premium["value"], legal_ref=premium["legal_ref"]),
        "insured_coverage": dict(depositors_pct=depositors["value"], value_pct=coverage["value_pct"]["value"],
                                 basis=depositors["basis"], source=depositors["source_url"]),
    }


def _profiles(con):
    peers = defaultdict(list)
    for row in _read(con, "select * from gold.fact_bank_quarter"):
        for metric in METRICS:
            if row[metric] is not None:
                peers[row["quarter"], metric].append(row[metric])
    result = {}
    for row in _read(con, "select * from gold.v_bank_profile"):
        if row["quarter"] is None and row["market_date"] is None:
            continue
        percentiles = {}
        for metric in METRICS:
            cohort = peers[row["quarter"], metric]
            value = row[metric]
            if value is not None and len(cohort) > 1:
                percentile = 100 * (sum(peer < value for peer in cohort) + (cohort.count(value) - 1) / 2) / (len(cohort) - 1)
                percentiles[metric] = round(percentile, 4)
        flags = []
        if row["denominator_flag"]:
            flags.append(dict(id="npl_denominator", text="Tỷ lệ nợ xấu giảm nhưng số tiền nợ xấu ước tính tăng",
                              rule_ref="npl_amount_growth_pct"))
        result[row["code"]] = dict(
            quarter=row["quarter"], metrics={key: row[key] for key in METRICS}, percentiles=percentiles,
            flags=flags, market={key: row[key] for key in MARKET_FIELDS}, source="FiinQuant (aggregates)",
        )
    return result


def _changes(con):
    rows = _read(con, """select * replace (timezone('Asia/Ho_Chi_Minh', observed_at) as observed_at)
                         from gold.v_rate_edition
                         order by bank_code, term_months, channel, tier, edition, reader""")
    history = defaultdict(list)
    for bank, rate, lead in _rate_groups(rows):
        if rate["grade"] != "contested":
            history[bank, rate["term_months"], rate["channel"], rate["tier"]].append((rate, lead))
    changes = []
    for (bank, term, channel, _), entries in sorted(history.items()):
        entries.sort(key=lambda pair: pair[1]["observed_at"])
        for (old, _), (new, lead) in zip(entries, entries[1:]):
            if old["rate_pct"] != new["rate_pct"]:
                changes.append(dict(bank=bank, term_months=term, channel=channel, from_pct=old["rate_pct"],
                                    to_pct=new["rate_pct"], observed_at=_iso(lead["observed_at"])))
    return sorted(changes, key=lambda row: row["observed_at"], reverse=True)


def _source_status(con, now, source_log):
    observations = {
        row["series"]: row for row in _read(con, """
            select series, max(date::varchar) as period, max(observed_at::varchar) as observed_at
            from gold.fact_money_market_day group by series
            union all
            select series, max(month::varchar), max(observed_at::varchar) from gold.fact_macro_month group by series
            union all
            select 'fiin_quarter', max(quarter::varchar), max(observed_at::varchar) from gold.fact_bank_quarter
            union all
            select 'fiin_market', max(date::varchar), max(observed_at::varchar) from gold.fact_bank_market_day
        """)
    }
    log = source_log or {}
    errors = {}
    for series, reason in log.get("errors", {}).items():
        if series in {"cpi", "cpi_index"}:
            errors["cpi"] = reason
        elif series == "fiin":
            errors["fiin_quarter"] = errors["fiin_market"] = reason
        else:
            errors["fiin_market" if series.startswith("fiin_raw_") else series] = reason
    statuses = {}
    for series in ("interbank", "omo", "central_fx", "sbv_credit", "sbv_deposit", "cpi", "fiin_quarter", "fiin_market"):
        row = observations.get(series, {})
        observed = log.get("observed_at", {}).get(series) or row.get("observed_at")
        reason = errors.get(series)
        status = "ok"
        if reason:
            status = "error"
        elif not observed:
            status, reason = "missing", "Chưa có dữ liệu trong kho"
        elif now - datetime.fromisoformat(observed) > timedelta(days=30):
            status, reason = "stale", "Lần đọc gần nhất đã quá 30 ngày"
        statuses[series] = dict(status=status, latest_period=row.get("period"), observed_at=observed, detail=reason)
    return statuses


def build_snapshot(con, now, *, source_log=None, geo=None):
    quality = evaluate(con, now)
    failed = [item for item in quality if item["status"] == "fail"]
    if failed:
        raise ValueError("Kiểm tra thất bại: " + ", ".join(f'{item["id"]}: {item["detail"]}' for item in failed))
    source_status = _source_status(con, now, source_log)
    optional_warnings = [f'{series}: {status["detail"]}' for series, status in source_status.items() if status["detail"]]
    quality.append(dict(id="optional_sources", name="Tình trạng nguồn bổ sung",
                        status="warn" if optional_warnings else "pass",
                        detail=" · ".join(optional_warnings) or "Các nguồn bổ sung đã được đọc"))
    rows = _read(con, """select * replace (timezone('Asia/Ho_Chi_Minh', observed_at) as observed_at)
                         from gold.v_curve_today
                         order by bank_code, term_months, channel, tier, reader""")
    groups = list(_rate_groups(rows))
    grades = Counter(rate["grade"] for _, rate, _ in groups)
    by_bank = defaultdict(list)
    for bank, rate, lead in groups:
        by_bank[bank].append((rate, lead))
    profiles = _profiles(con)
    banks = []
    for bank in _read(con, "select * exclude (rate_page) from gold.dim_bank order by code"):
        code = bank["code"]
        pair = max(by_bank[code], key=lambda item: (-GRADE_ORDER[item[0]["grade"]], item[1]["observed_at"]), default=None)
        sheet = pair[1] if pair else None
        banks.append({**bank, "sheet_url": sheet["source_url"] if sheet else None,
                      "sheet_date": str(sheet["sheet_date"]) if sheet and sheet["sheet_date"] else None,
                      "read_at": _iso(max((lead["observed_at"] for _, lead in by_bank[code]), default=None)),
                      "rates": [rate for rate, _ in by_bank[code]], "profile": profiles.get(code)})
    policy = _policy(con)
    run_ids = [row[0] for row in con.execute("select distinct run_id from gold.fact_posted_rate order by 1").fetchall()]
    coverage = dict(banks_total=len(banks), banks_read=sum(bool(bank["rates"]) for bank in banks), rows=len(groups),
                    **{grade: grades[grade] for grade in GRADE_ORDER})
    market = {"ceiling_stats": _ceiling_stats(groups, policy["ceiling"]["pct"])}
    for key, fields in {
        "interbank": "date, tenor, rate_pct",
        "omo": "date, volume_bn, rate_pct, tenor_days",
        "central_fx": "date, vnd_per_usd",
    }.items():
        market[key] = _read(con, f"select {fields} from gold.fact_money_market_day where series = '{key}' order by all")
    macro = {
        "cpi_yoy": _read(con, "select month, pct from gold.fact_macro_month where series = 'cpi' order by month"),
        "sbv_monthly": _read(con, """
            select month, max(household_deposits_bn) as household_deposits_bn,
                max(credit_growth_ytd_pct) as credit_growth_ytd_pct,
                max(deposit_growth_ytd_pct) as deposit_growth_ytd_pct
            from gold.fact_macro_month where series in ('sbv_credit', 'sbv_deposit') group by month order by month
        """),
    }
    digest = sha256(encode([run_ids, banks, market, macro, policy, source_status, geo])).hexdigest()[:12]
    return dict(meta=dict(snapshot_id=f"{run_ids[-1]}-{digest}", generated_at=_iso(now), run_ids=run_ids,
                          coverage=coverage, quality=quality, source_status=source_status,
                          sources=_read(con, "select distinct * from gold.dim_source order by id")),
                policy=policy, banks=banks, market=market, macro=macro, changes=_changes(con),
                **({"geo": geo} if geo is not None else {}))


def validate_snapshot(payload):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
    sources = payload["meta"]["sources"]
    urls = {source["url"] for source in sources}
    if len({source["id"] for source in sources}) != len(sources) or not all(valid_url(url) for url in urls):
        raise ValueError("Danh mục nguồn có định danh trùng hoặc URL không hợp lệ")
    citations = {payload["policy"]["insured_coverage"]["source"]}
    for bank in payload["banks"]:
        if bank["sheet_url"]:
            citations.add(bank["sheet_url"])
        if bank["profile"] and not any(source["publisher"] == "Nguồn: FiinQuant (FiinGroup)" for source in sources):
            raise ValueError("Thiếu nguồn FiinQuant cho hồ sơ ngân hàng")
        citations.update(reader["source_url"] for rate in bank["rates"] for reader in rate["readers"])
    if missing := citations - urls:
        raise ValueError("Thiếu nguồn trích dẫn: " + ", ".join(sorted(missing)))


def _write_reports(stage, payload):
    coverage = payload["meta"]["coverage"]
    labels = {"verified": "Đã xác minh", "single": "Một nguồn", "contested": "Mâu thuẫn"}
    counts = "\n".join(f"- {label}: {coverage[grade]}" for grade, label in labels.items())
    summary = "\n".join(f'- {item["name"]} ({item["status"]}) — {item["detail"]}'
                        for item in payload["meta"]["quality"])
    (stage / "eda.md").write_text(
        f'# Khảo sát lãi suất\n\nNgân hàng đã đọc: {coverage["banks_read"]}/{coverage["banks_total"]}.\n\n'
        f"{counts}\n\n![Phân hạng báo giá](eda.svg)\n\n## Chất lượng\n\n{summary}\n", encoding="utf-8",
    )
    maximum = max(coverage["rows"], 1)
    bars = []
    for index, (grade, label) in enumerate(labels.items()):
        y = 32 + index * 30
        count = coverage[grade]
        bars.append(f'<text x="4" y="{y + 14}">{label}</text>'
                    f'<rect x="110" y="{y}" width="{200 * count / maximum:.2f}" height="19" fill="#28568c"/>'
                    f'<text x="320" y="{y + 14}">{count}</text>')
    (stage / "eda.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 370 126" font-family="sans-serif" font-size="13">'
        '<title>Phân hạng báo giá</title>' + "".join(bars) + '</svg>\n', encoding="utf-8",
    )
    (stage / "data_dictionary.md").write_text("""# Từ điển dữ liệu RateWatch

| Bảng | Hạt dữ liệu và đơn vị |
|---|---|
| dim_bank | Mã ngân hàng, tên, mã chứng khoán, sở hữu, trạng thái niêm yết |
| dim_term | Kỳ hạn tháng. 0 là không kỳ hạn, 1–5 thuộc trần kỳ hạn, từ 6 tháng ngoài trần |
| dim_channel | Tại quầy hoặc trực tuyến |
| dim_date | Ngày lịch Việt Nam và thành phần năm, tháng, ngày |
| dim_source | Mã nguồn, đơn vị công bố, URL, quyền sử dụng và phương pháp đọc |
| fact_posted_rate | Mỗi quan sát một dòng theo phiên, ngân hàng, kỳ hạn, kênh, bậc tiền và loại nguồn. rate_pct là %/năm. sheet_date là ngày áp dụng in trên biểu. observed_at là thời điểm đọc UTC+07:00 |
| fact_bank_quarter | Chỉ số ngân hàng/quý từ FiinQuant. NPL, bao phủ, LDR, ROA, NIM và tăng trưởng đều tính theo % |
| fact_bank_market_day | Ngân hàng/phiên. P/B theo lần. Biến động 60 phiên của lợi suất log được quy năm với 252 phiên. Drawdown theo % từ đỉnh trong cửa sổ một năm. Dòng vốn ngoại cộng 20 phiên theo tỷ VND |
| fact_money_market_day | Ngày giao dịch, kỳ hạn liên ngân hàng, phiên OMO hoặc tỷ giá trung tâm. Lãi suất %/năm, khối lượng tỷ VND, tỷ giá VND/USD |
| fact_macro_month | Tháng tham chiếu. CPI tháng so cùng kỳ, tín dụng và tiền gửi tăng từ cuối năm trước. Tiền gửi tính theo tỷ VND. Phương pháp phân loại tiền gửi đổi từ 10/2025 |
| fact_policy_param | Tham số, đơn vị, văn bản, ngày hiệu lực và căn cứ |
| v_curve_today | Báo giá hiện hành gồm mọi nguồn đọc gần nhất của từng biểu |
| v_bank_profile | Danh mục ngân hàng ghép với quý và phiên thị trường gần nhất |

**Biến động nợ xấu.** Với tăng trưởng dư nợ so cùng quý năm trước, `npl_change_pp` là
`npl_t - npl_{t-4}` theo điểm phần trăm. `npl_amount_growth_pct` là
`100 × ((1 + g_loans / 100) × npl_t / npl_{t-4} - 1)`. Đây là ước tính dùng tăng trưởng dư nợ
bình quân của FiinQuant làm đại diện cho tăng trưởng dư nợ gộp. Kỳ gốc bằng 0 hoặc thiếu đầu vào cho kết quả rỗng.
`coverage_change_pp` là thay đổi bao phủ cùng kỳ theo điểm phần trăm. Cờ bật khi tỷ lệ giảm và số tiền ước tính tăng.

**Đối chiếu báo giá.** Hai loại nguồn trở lên đồng ý trong 0,005 điểm phần trăm được gắn verified.
Mâu thuẫn giữ mọi giá đọc. Một loại nguồn được gắn single. Bản công bố loại nhóm contested khỏi thống kê.

**Nguồn bổ sung.** `meta.source_status` ghi kỳ dữ liệu mới nhất, lần đọc thành công gần nhất và lý do
cảnh báo nếu lần nạp gặp lỗi, dữ liệu vắng mặt hoặc lần đọc đã quá 30 ngày.
""", encoding="utf-8")


def publish(db, destination, out, *, now=None, source_log=None, geo=None):
    now = now or datetime.now(TZ)
    out = Path(out)
    destination = Path(destination)
    with duckdb.connect(str(db), read_only=True) as con:
        payload = build_snapshot(con, now, source_log=source_log, geo=geo)
        validate_snapshot(payload)
        encoded = encode(payload)
        out.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".ratewatch-", dir=out) as folder:
            stage = Path(folder)
            _write_reports(stage, payload)
            con.sql("""
                select r.* exclude (raw_sha256, edition, observed_at),
                    strftime(timezone('Asia/Ho_Chi_Minh', r.observed_at), '%Y-%m-%dT%H:%M:%S') || '+07:00' as observed_at
                from gold.fact_posted_rate r join gold.dim_source s on r.source_url = s.url
                where s.licence = 'Nguồn công khai'
                order by r.bank_code, r.term_months, r.channel, r.tier, r.observed_at, r.reader
            """).write_csv(str(stage / "rates.csv"))
            if s3 := os.getenv("RATEWATCH_S3_URI"):
                if not re.fullmatch(r"s3://[^/]+/[^/].*", s3):
                    raise ValueError("RATEWATCH_S3_URI phải trỏ tới một khóa S3")
                snapshot = stage / "snapshot.json"
                snapshot.write_bytes(encoded)
                subprocess.run(["aws", "s3", "cp", str(snapshot), s3, "--content-type", "application/json",
                                "--only-show-errors"], check=True)
            for name in ("eda.md", "eda.svg", "data_dictionary.md"):
                atomic(out / name, (stage / name).read_bytes())
            atomic(out / "archive" / f'{payload["meta"]["snapshot_id"]}.csv', (stage / "rates.csv").read_bytes())
            atomic(destination, encoded)
    return payload
