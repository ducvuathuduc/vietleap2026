"""Publication quality gates for RateWatch gold."""
from datetime import timedelta
import re
from urllib.parse import urlsplit

from .warehouse import TZ

ALLOWED_READERS = {"bank_html", "bank_pdf", "tinyfish", "aggregator"}
GRADE_TOLERANCE = 0.005
DEFAULT_DRIFT = 0.30


def valid_url(value):
    if not isinstance(value, str) or any(char.isspace() for char in value):
        return False
    url = urlsplit(value)
    return url.scheme in {"https", "http"} and bool(url.hostname) and url.username is None


def _reconcile_tolerance(series, total, parts):
    # SBV publishes whole-billion credit balances in some months. Up to six
    # sector balances and the total can each be rounded by half a billion.
    if series == "sbv_credit" and total.is_integer() and parts.is_integer():
        return 3.5
    return 0.05


def evaluate(con, now):
    def query(sql):
        return con.execute(sql).fetchall()

    def result(key, name, detail, problems=False, severity="fail"):
        return dict(id=key, name=name, detail=detail, status=severity if problems else "pass")

    rows = query("""select bank_code, term_months, channel, tier, rate_pct, sheet_date,
                           reader, source_url, raw_sha256
                    from gold.fact_posted_rate""")
    bad = sum(
        term < 0 or channel not in {"counter", "online"} or reader not in ALLOWED_READERS
        or not valid_url(url) or not re.fullmatch(r"[a-fA-F0-9]{64}", digest)
        for _, term, channel, _, _, _, reader, url, digest in rows
    )
    bounds = sum(not (0 < rate < 15) for _, _, _, _, rate, *_ in rows)
    limits = dict(query("select parameter, value from gold.fact_policy_param where parameter in ('ceiling', 'demand_ceiling')"))
    violations = [
        f"{bank}/{term}/{channel}/{tier}={rate}%"
        for bank, term, channel, tier, rate, *_ in rows
        if 0 <= term < 6 and rate > limits["demand_ceiling" if term == 0 else "ceiling"]
    ]
    groups = query("""
        select bank_code, term_months, channel, tier, edition, count(distinct reader),
               min(rate_pct), max(rate_pct), min(grade), max(grade)
        from gold.v_rate_edition group by all
        order by bank_code, term_months, channel, tier, edition
    """)
    grade_errors = 0
    for *_, readers, low, high, grade, last_grade in groups:
        expected = "single" if readers == 1 else "verified" if high - low <= GRADE_TOLERANCE + 1e-10 else "contested"
        grade_errors += grade != expected or last_grade != expected
    latest = query("""
        select bank_code, term_months, channel, tier, timezone('Asia/Ho_Chi_Minh', max(observed_at))
        from gold.v_curve_today group by all order by bank_code, term_months, channel, tier
    """)
    stale = [f"{bank}/{term}/{channel}/{tier}" for bank, term, channel, tier, at in latest
             if not timedelta(0) <= now - at.replace(tzinfo=TZ) <= timedelta(days=30)]
    disagreements = query("""
        select a.bank_code, a.term_months, a.channel, a.tier, a.edition,
               a.rate_pct, b.rate_pct, b.reader
        from gold.v_curve_today a join gold.v_curve_today b using (bank_code, term_months, channel, tier, edition)
        where a.reader = 'aggregator' and b.reader in ('bank_html', 'bank_pdf', 'tinyfish')
          and abs(a.rate_pct-b.rate_pct) > 0.0050000001
        order by 1, 2, 3, 4, 5, 8
    """)
    reconciliation = query("""
        select series, date::varchar, total_bn::double, parts_bn::double from gold.fact_money_market_day
        where total_bn is not null and parts_bn is not null
        union all
        select series, month::varchar, total_bn::double, parts_bn::double from gold.fact_macro_month
        where total_bn is not null and parts_bn is not null order by 1, 2, 3, 4
    """)
    inconsistent = [(series, period, total, parts) for series, period, total, parts in reconciliation
                    if abs(total - parts) > _reconcile_tolerance(series, total, parts)]
    calibration = query("""
        select rate_pct, grade from gold.v_rate_edition
        where bank_code = 'STB' and term_months = 6 and channel = 'counter'
          and sheet_date = date '2026-10-20' and reader = 'bank_pdf'
          and tier = 'duoi_500tr'
    """)
    verified_cell = bool(calibration) and all(rate == 5.70 for rate, _ in calibration)
    calibration_detail = ", ".join(f"{rate:g}%" for rate, _ in calibration)
    sizes = query("""
        select run_id, count(*) as rows from gold.fact_posted_rate
        group by run_id order by run_id desc limit 2
    """)
    drift = len(sizes) == 2 and abs(sizes[0][1] - sizes[1][1]) / sizes[1][1] > DEFAULT_DRIFT
    return [
        result("schema", "Lược đồ silver", f"{bad} dòng sai lược đồ", bad or not rows),
        result("bounds", "Miền lãi suất", f"{bounds} dòng ngoài (0%, 15%)", bounds),
        result("ceiling", "Trần kỳ hạn dưới 6 tháng", "; ".join(violations) or "Trong giới hạn", violations, "warn"),
        result("grade", "Đối chiếu nguồn", f"{grade_errors} nhóm sai quy tắc phân hạng", grade_errors),
        result("freshness", "Độ mới ≤ 30 ngày", "; ".join(stale) or "Quan sát còn hiệu lực", stale),
        result("disagreement", "Chênh lệch bảng so sánh và ngân hàng",
               "; ".join(f"{bank}/{term}/{channel}/{tier}/{edition}: {agg:g}% và {bank_rate:g}% ({reader})"
                         for bank, term, channel, tier, edition, agg, bank_rate, reader in disagreements)
               or "Không có chênh lệch vượt 0,005 điểm %", disagreements, "warn"),
        result("sbv_reconcile", "Đối soát tổng NHNN",
               str(inconsistent) if inconsistent else f"{len(reconciliation)} phép đối soát khả dụng", inconsistent),
        result("calibration", "Ô kiểm chuẩn Sacombank",
               f"20/10/2026 · tại quầy · dưới 500 triệu · 6 tháng · chuẩn 5,70% · đọc {calibration_detail}",
               not verified_cell)
        if calibration else result("calibration", "Ô kiểm chuẩn Sacombank",
                                    "Phiên chạy thiếu bảng kiểm chuẩn 20/10/2026", True, "warn"),
        result("row_drift", "Biến động số dòng giữa hai lần đọc",
               " · ".join(f"{run}: {count}" for run, count in sizes) if len(sizes) == 2 else "Chưa có lần chạy trước",
               drift),
    ]
