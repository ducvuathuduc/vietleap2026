"""Presenter copy and number formatting for the monitor pitch."""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from .copy import localize_periods, period_vi


SECTORS = {
    "public_finance": ("Tài chính công", "Public finance"),
    "fdi": ("Đầu tư trực tiếp nước ngoài", "Foreign direct investment"),
    "banking": ("Ngân hàng", "Banking"),
    "capital_market": ("Thị trường vốn", "Capital markets"),
    "real_estate": ("Bất động sản", "Real estate"),
}
NAMES_EN = {
    "nsnn_thu_pct_plan": "Budget revenue", "nsnn_chi_pct_plan": "Budget spending",
    "budget_time_pace": "Calendar benchmark", "dtc_giai_ngan_pct_plan": "Public investment disbursement",
    "fdi_thuc_hien_ytd": "Realized FDI", "fdi_dang_ky_ytd": "Registered FDI",
    "fdi_dang_ky_yoy": "Registered FDI growth", "fdi_thuc_hien_yoy": "Realized FDI growth",
    "bank_npl": "Reported non-performing loans", "bank_sector_pb": "Bank sector price-to-book",
    "credit_ytd": "Credit growth", "deposit_ytd": "Deposit growth",
    "market_liquidity_20d": "Average trading value per session", "foreign_net_20d": "Foreign net flows",
    "vnindex_drawdown": "VN-Index drawdown", "re_absorption": "Housing absorption",
    "re_new_supply": "New housing supply", "mortgage_rate": "Benchmark mortgage rate",
}
UNITS_EN = {"điểm %": "percentage points", "điểm phần trăm": "percentage points", "lần": "times",
            "tỷ đồng": "billion VND", "nghìn tỷ đồng": "trillion VND", "tỷ USD": "billion USD", "căn": "units"}
CARD_EN = {
    "BR-PF1": "Budget revenue exceeds spending by {n} of plan",
    "BR-PF2": "Public investment is {n} below the calendar benchmark",
    "BR-FDI1": "Realized FDI is {n} of registered capital",
    "BR-FDI2": "The leading provinces account for {n} of observed registrations",
    "BR-BK1": "Credit growth exceeds deposit growth by {n}",
    "BR-BK3": "Bank sector price-to-book is {n}",
    "BR-CM1": "Average trading value is {n} per session",
    "BR-CM2": "Foreign investors are net sellers of {n}",
    "BR-CM4": "The VN-Index is {n} below its recent peak",
    "BR-RE1": "Housing absorption in Ho Chi Minh City reaches {n}",
}


def number(value, places, lang):
    text = f"{value:,.{places}f}".replace("-", "−")
    return text.translate(str.maketrans(",.", ".,")) if lang == "vi" else text


def measure(value, unit, lang):
    places = 2 if unit == "lần" else 1 if unit in {"%", "điểm %", "điểm phần trăm"} or value % 1 else 0
    label = UNITS_EN.get(unit, unit) if lang == "en" else unit.replace("điểm phần trăm", "điểm %")
    return number(value, places, lang) + ("%" if label == "%" else f" {label}" if label else "")


def period(value, lang, *, short=False):
    pieces = value.split("-")
    if short and len(pieces) == 2:
        year, part = pieces
        return f"{part}/{year}" if part.startswith("Q") else f"{'T' if lang == 'vi' else ''}{int(part)}/{year}"
    if lang == "vi":
        return period_vi(value)
    if len(pieces) == 3:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    if len(pieces) == 2:
        year, part = pieces
        return f"{part} {year}" if part.startswith("Q") else datetime.fromisoformat(value + "-01").strftime("%B %Y")
    return value


def day(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(ZoneInfo("Asia/Saigon"))
    return parsed.strftime("%d/%m/%Y")


def tidy(text):
    return localize_periods(text).replace("điểm phần trăm", "điểm %").replace("đòn bẩy", "dư nợ ký quỹ")


def indicator_name(indicator, lang):
    if lang == "vi":
        return indicator["name_vi"]
    return indicator.get("name_en") or NAMES_EN.get(indicator["id"], indicator["name_vi"])


def card_en(card, indicators):
    rule = card["rule_id"]
    value = abs(card["value"]) if rule in {"BR-PF2", "BR-CM2", "BR-CM4"} else card["value"]
    n = measure(value, card["unit"], "en")
    indicator = indicators.get(card.get("indicator_id"))
    template = CARD_EN.get(rule, f"{indicator_name(indicator, 'en')} is {{n}}" if indicator else "Recorded value is {n}")
    if rule == "BR-BK2":
        ticker = re.search(r"của ([A-Z][A-Z0-9]+) đạt", card["sentence_vi"])
        template = f"{ticker[1] if ticker else 'The flagged bank'} reports a non-performing loan ratio of {{n}}"
    return f"{template.format(n=n)} · {period(card['period'], 'en')}"


SECTOR_NOTES = {
    "public_finance": (
        "Đọc thu và chi theo tỷ lệ dự toán của từng khoản. Mốc tiến độ chỉ chia đều theo thời gian trong năm. "
        "Hãy dùng khoảng cách này để chọn hồ sơ cần rà soát và dùng phụ lục địa phương để tìm tỷ lệ theo từng tỉnh.",
        "Read revenue and spending against their respective annual plans. The calendar line is an even pace reference. "
        "Use the gap to select payment files for review, then use the provincial appendix to see each area's disbursement rate.",
    ),
    "fdi": (
        "Vốn đăng ký và vốn thực hiện là hai dòng công bố lũy kế. Tỷ lệ giữa hai dòng không đo tỷ lệ hoàn thành "
        "của cùng một lứa dự án. Đối chiếu từng dự án và xem phạm vi tỉnh có số liệu trước khi đọc mức tập trung.",
        "Registered and realized investment are two cumulative series. Their ratio does not measure completion within a matched "
        "cohort of projects. Reconcile projects individually, and check which locations are covered before interpreting geographic concentration.",
    ),
    "banking": (
        "Đối chiếu tăng trưởng tín dụng với tiền gửi cùng kỳ, sau đó đọc nợ xấu và dự phòng theo từng ngân hàng. "
        "Hai tỷ lệ rủi ro giúp nhận diện hồ sơ cần kiểm tra thêm. Mức định giá trên thị trường là một phép đo riêng.",
        "Compare credit and deposit growth for the same period, then look at reported non-performing loans and coverage by bank. "
        "Those risk measures help select files for review. The sector's market valuation is a separate measure and should be read on its own.",
    ),
    "capital_market": (
        "Đường biểu diễn dùng các cửa sổ giao dịch cùng độ dài. So sánh mức thanh khoản gần đây với các cửa sổ trước đó, "
        "rồi tra dòng vốn ngoại và khoảng cách tới đỉnh của chỉ số. Các chỉ tiêu này phản ánh diễn biến quan sát được.",
        "The chart compares trading windows of equal length. Read recent turnover against earlier windows, then look up foreign flows "
        "and the index's distance from its peak. Each statistic describes activity in the observed sessions and uses the same market source.",
    ),
    "real_estate": (
        "Đọc căn bán được và căn mở bán trong cùng phạm vi công bố của TP.HCM. Lãi vay là số tham chiếu từ các ngân hàng. "
        "Kiểm tra ranh giới và rổ dự án trước khi dùng chỉ tiêu này để so sánh các kỳ.",
        "Read sales and new launches within the same reported Ho Chi Minh City coverage. The mortgage rate is a bank benchmark. "
        "Check the geographic boundary and the projects included before making comparisons across quarters or drawing conclusions about affordability.",
    ),
}


ACTION_EN = {
    "br_pf1": "Review the payment schedule and identify spending below plan",
    "br_pf2": "Review slow projects and count files awaiting acceptance",
    "br_fdi1": "Reconcile registered and realized capital by project and log missing milestones",
    "br_bk1": "Compare credit and deposit maturities and measure the growth gap",
    "br_bk2": "Review loans above the risk threshold and measure reserve coverage",
}
AGENCY_EN = {
    "Bộ Tài chính": "Ministry of Finance", "Bộ Tài chính và Ủy ban nhân dân cấp tỉnh": "Finance Ministry and provincial authorities",
    "Cục Đầu tư nước ngoài, Bộ Tài chính": "Foreign Investment Agency, Ministry of Finance",
    "Ngân hàng Nhà nước Việt Nam": "State Bank of Vietnam",
}
IMPLICATION_EN = {
    "br_pf1": "At the current pace, spending remains {gap} below the calendar benchmark.",
    "br_pf2": "At the current pace, disbursement remains {gap} below the benchmark.",
    "br_fdi1": "At current rates, registration growth remains {gap} higher than realized growth.",
    "br_bk1": "At current rates, the gap remains {gap} above the watch threshold.",
    "br_bk2": "At the reported ratio, reserve coverage remains {gap} below the stock of non-performing loans.",
}


def recommendation_parts(rec, lang, cards, indicators):
    evidence = rec["evidence"][0]
    if lang == "vi":
        return tuple(map(tidy, (evidence["fact_vi"], rec["so_what_vi"], rec["action_vi"],
                                f"{rec['agency_vi']} · {rec['horizon_vi']}")))
    card = cards.get(evidence["rule_id"])
    deadline = re.search(r"\b\d{2}/\d{2}/\d{4}\b", rec["action_vi"])
    horizon = re.fullmatch(r"quý ([IV]+)/([0-9]+)", rec["horizon_vi"])
    english_horizon = f"Q{('I', 'II', 'III', 'IV').index(horizon[1]) + 1} {horizon[2]}" if horizon else rec["horizon_vi"]
    action = ACTION_EN.get(rec["id"], tidy(rec["action_vi"]))
    if deadline and deadline[0] not in action:
        action += f" by {deadline[0]}."
    implication = tidy(rec["so_what_vi"])
    gap = re.search(r"\b(\d+(?:,\d+)?) điểm %", implication)
    if gap and rec["id"] in IMPLICATION_EN:
        implication = IMPLICATION_EN[rec["id"]].format(gap=f"{gap[1].replace(',', '.')} percentage points")
    return (card_en(card, indicators) if card else tidy(evidence["fact_vi"]),
            implication, action,
            f"{AGENCY_EN.get(rec['agency_vi'], rec['agency_vi'])} · {english_horizon}")
