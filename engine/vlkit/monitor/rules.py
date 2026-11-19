"""Deterministic monitor rules over conformed, aggregated gold frames."""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import fmt


@dataclass(frozen=True)
class Rule:
    id: str
    sector: str
    chart_id: str
    name_vi: str
    formula_vi: str
    threshold_vi: str
    agency_vi: str
    so_what_vi: str
    action_vi: str


RULES = [
    Rule("BR-PF1", "public_finance", "budget_execution", "Tiến độ thu, chi ngân sách",
         "Tỷ lệ thu trừ tỷ lệ chi theo dự toán cùng tháng. Mốc tiến độ là tháng chia 12.",
         "Cảnh báo khi chi thấp hơn mốc tiến độ trên 10 điểm phần trăm để nhận diện độ trễ đáng theo dõi.",
         "Bộ Tài chính", "Khoảng cách thu–chi cần được đối chiếu với lịch chi thực tế.",
         "Đối chiếu tiến độ chi với kế hoạch theo quý và lịch thanh toán của từng khoản."),
    Rule("BR-PF2", "public_finance", "public_investment", "Tiến độ giải ngân đầu tư công",
         "Tỷ lệ giải ngân trừ mốc tháng chia 12. So tỷ lệ trung ương, địa phương và từng đơn vị với số toàn quốc.",
         "Đánh dấu giải ngân dưới mốc tiến độ tháng và đơn vị dưới mức cả nước để chọn nơi rà soát.",
         "Bộ Tài chính và UBND cấp tỉnh", "Chênh lệch tiến độ giúp xác định đơn vị cần rà soát hồ sơ dự án.",
         "Đối chiếu kế hoạch vốn và mốc nghiệm thu tại các đơn vị giải ngân thấp."),
    Rule("BR-FDI1", "fdi", "fdi_realisation", "Vốn FDI đăng ký và thực hiện",
         "Vốn thực hiện chia vốn đăng ký lũy kế. So tăng trưởng cùng kỳ của hai dòng vốn.",
         "Cảnh báo khi mức tăng đăng ký hơn thực hiện trên 30 điểm phần trăm để theo dõi sự phân kỳ đáng kể.",
         "Cục Đầu tư nước ngoài, Bộ Tài chính", "Vốn đăng ký và vốn thực hiện đo hai giai đoạn của đầu tư.",
         "Đối chiếu các dự án đăng ký lớn với tiến độ thực hiện và các mốc thủ tục."),
    Rule("BR-FDI2", "fdi", "fdi_concentration", "Mức tập trung vốn FDI đăng ký",
         "Cộng tỷ trọng của ba tỉnh lớn nhất. HHI là tổng bình phương tỷ trọng theo tỉnh hoặc đối tác quan sát được.",
         "Cần ít nhất ba tỉnh để tính tỷ trọng nhóm đầu và ít nhất hai quan sát để mô tả mức tập trung của nhóm.",
         "Cục Đầu tư nước ngoài, Bộ Tài chính", "Mức tập trung bổ sung góc nhìn địa bàn và đối tác cho số vốn toàn quốc.",
         "Theo dõi tỷ trọng các địa bàn và đối tác qua các kỳ có cùng phạm vi thống kê."),
    Rule("BR-BK1", "banking", "credit_deposit", "Chênh lệch tăng trưởng tín dụng và tiền gửi",
         "Tăng trưởng tín dụng trừ tăng trưởng tiền gửi so với cuối năm trước.",
         "Cảnh báo trên 1 điểm phần trăm để theo dõi tín dụng tăng nhanh hơn nguồn tiền gửi.",
         "Ngân hàng Nhà nước", "Chênh lệch tăng trưởng là tín hiệu để kiểm tra nguồn vốn và thanh khoản.",
         "Đối chiếu kỳ hạn nguồn vốn, tín dụng và thanh khoản theo nhóm ngân hàng."),
    Rule("BR-BK2", "banking", "bank_league", "Chất lượng tài sản ngân hàng",
         "Đối chiếu tỷ lệ nợ xấu, nợ nhóm 2 và bao phủ cùng ngân hàng, cùng quý. Chia nhóm theo các phân vị một phần ba.",
         "Cảnh báo nợ xấu trên 3% và bao phủ dưới 100%. Ngưỡng nợ xấu tham chiếu giám sát, bao phủ so với số nợ xấu.",
         "Ngân hàng Nhà nước", "Tỷ lệ nợ xấu và bao phủ cùng kỳ giúp ưu tiên ngân hàng cần theo dõi.",
         "Kiểm tra biến động nợ nhóm 2, nợ xấu và mức dự phòng trong báo cáo tài chính."),
    Rule("BR-BK3", "banking", "bank_valuation", "Định giá và sinh lời ngân hàng",
         "Phân vị P/B ngành so với lịch sử của chính ngành trong năm năm. Đối chiếu ROE cùng ngày khi công bố.",
         "Chỉ tiêu mô tả vị trí định giá trong lịch sử, dùng để đặt P/B và ROE vào cùng bối cảnh.",
         "Ủy ban Chứng khoán Nhà nước", "Vị trí P/B trong lịch sử cung cấp bối cảnh cho khả năng sinh lời.",
         "Đối chiếu biến động định giá với cập nhật lợi nhuận và cấu phần vốn chủ sở hữu."),
    Rule("BR-CM1", "capital_market", "market_liquidity", "Thanh khoản và độ rộng thị trường",
         "Bình quân giá trị giao dịch 20 phiên so với trung vị và phân vị của các bình quân 20 phiên trong năm trước. "
         "Độ rộng là số mã tăng chia tổng số mã tăng, giảm và đứng giá.",
         "Chỉ tiêu mô tả sử dụng các cửa sổ 20 phiên và một năm để giảm ảnh hưởng của phiên riêng lẻ.",
         "Ủy ban Chứng khoán Nhà nước", "Thanh khoản và độ rộng đo quy mô giao dịch và mức lan tỏa qua các mã.",
         "Theo dõi đồng thời độ rộng thị trường và giá trị giao dịch bình quân."),
    Rule("BR-CM2", "capital_market", "market_foreign", "Dòng vốn khối ngoại",
         "Cộng mua ròng trong 20 và 60 phiên, đếm chuỗi phiên cùng dấu và xếp ngành theo mua ròng.",
         "Chỉ tiêu mô tả dùng cửa sổ phiên đầy đủ để so sánh mua bán ròng nhất quán.",
         "Ủy ban Chứng khoán Nhà nước", "Dòng vốn theo ngành cho biết mua bán ròng tập trung ở đâu.",
         "Theo dõi liệu dòng vốn có tiếp tục tập trung ở các ngành bán ròng lớn."),
    Rule("BR-CM3", "capital_market", "market_leverage", "Dư nợ ký quỹ và thanh khoản",
         "So thay đổi theo quý của dư nợ ký quỹ với thay đổi giá trị giao dịch bình quân phiên.",
         "Cảnh báo hai thay đổi trái dấu để xem xét sự phân kỳ giữa dư nợ và hoạt động giao dịch.",
         "Ủy ban Chứng khoán Nhà nước", "Sự phân kỳ là tín hiệu để rà soát chất lượng tài sản bảo đảm.",
         "Đối chiếu dư nợ ký quỹ với thanh khoản theo nhóm cổ phiếu và thời hạn báo cáo."),
    Rule("BR-RE1", "real_estate", "real_estate", "Hấp thụ, nguồn cung và lãi suất vay mua nhà",
         "Đối chiếu tỷ lệ hấp thụ và nguồn cung mới cùng kỳ với lãi suất vay mua nhà và chênh lệch lãi suất so với kỳ trước.",
         "Chỉ tiêu mô tả dùng cùng kỳ và cùng rổ dự án khi đối chiếu cung với lượng hấp thụ.",
         "Bộ Xây dựng và Ngân hàng Nhà nước", "Hấp thụ và lãi suất cung cấp hai góc nhìn về nhu cầu nhà ở.",
         "Đối chiếu tỷ lệ hấp thụ theo phân khúc và điều kiện vay tại cùng thời điểm."),
    Rule("BR-AS1", "asean", "asean_rank", "So sánh với ASEAN",
         "Xếp hạng theo hướng của chỉ tiêu ở năm chung gần nhất và trừ trung vị nhóm khỏi giá trị Việt Nam.",
         "Chỉ tiêu mô tả dùng dữ liệu cùng năm của các nước ASEAN có quan sát.",
         "Bộ Tài chính", "Hạng và khoảng cách với trung vị bổ sung bối cảnh so sánh cùng năm.",
         "Đối chiếu định nghĩa chỉ tiêu, phạm vi số liệu và chính sách của các nước trong nhóm."),
    Rule("BR-PV1", "province", "province_scores", "Phân nhóm tỉnh, thành phố",
         "Chia theo phân vị 20, 40, 60 và 80 của giá trị cấp tỉnh cùng kỳ. Công bố trung vị, khoảng giá trị và số quan sát.",
         "Năm nhóm theo kiểu PCI cho thấy khoảng giá trị thực tế thay vì chỉ trình bày thứ hạng.",
         "Bộ Tài chính và UBND cấp tỉnh", "Các nhóm cho thấy vị trí tương đối theo chỉ tiêu và mức phân tán.",
         "Đối chiếu các tỉnh trong cùng nhóm với quy mô địa phương và thẩm quyền ngân sách."),
    Rule("HM1", "macro", "monthly_heatmap", "Phân vị chỉ tiêu tháng",
         "So từng giá trị với 12 tháng gần nhất của chính chỉ tiêu, tính nửa trọng số cho các giá trị bằng nhau.",
         "Chỉ tô phân vị khi đủ 12 tháng liền nhau để so sánh nhất quán trong năm.",
         "Cục Thống kê", "Phân vị cho biết vị trí của giá trị trong năm gần nhất của cùng chỉ tiêu.",
         "Đối chiếu biến động với chuỗi gốc trước khi diễn giải."),
]

ASEAN_NAMES = {
    "BRN": "Brunei", "KHM": "Campuchia", "IDN": "Indonesia", "LAO": "Lào", "MYS": "Malaysia",
    "MMR": "Myanmar", "PHL": "Philippines", "SGP": "Singapore", "THA": "Thái Lan",
    "TLS": "Timor-Leste", "VNM": "Việt Nam",
}
OBS_COLUMNS = ["indicator_id", "period", "geo", "geo_type", "value", "unit", "measure_type", "source_id"]
MEASURE_SUFFIXES = ("pct_plan", "level", "ytd", "yoy", "mom", "share", "ratio", "index")
MONTH = r"\d{4}-(0[1-9]|1[0-2])"


def _fmt(value: float) -> str:
    return fmt.fixed(value, 1, lang="vi")


def _percentile(value: float, reference: np.ndarray) -> float:
    return float(100 * (np.count_nonzero(reference < value) + np.count_nonzero(reference == value) / 2) / len(reference))


def _numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    frame = frame.reindex(columns=frame.columns.union(columns, sort=False)).copy()
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)
    return frame


def _date_frame(frame: pd.DataFrame, keys: list[str], columns: list[str]) -> pd.DataFrame:
    frame = _numeric(frame.reindex(columns=["date", *keys, *columns]), columns)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    for key in keys:
        frame[key] = frame[key].astype("string")
    return frame.dropna(subset=["date", *keys]).sort_values("date").drop_duplicates(["date", *keys], keep="last")


def _rank_history(series: pd.Series, years: int) -> tuple[pd.Series, pd.Series]:
    """Use prior rows inside each calendar window, allowing a closed market at the boundary."""
    rank = pd.Series(np.nan, index=series.index)
    median = rank.copy()
    series = series.dropna()
    dates = pd.DatetimeIndex(series.index)
    if dates.empty:
        return rank, median
    starts = dates - pd.DateOffset(years=years)
    indexes = dates.searchsorted(starts)
    values = series.to_numpy()
    for i, left in enumerate(indexes):
        if i > left and starts[i] >= dates[0] - pd.Timedelta(days=7):
            history = values[left:i]
            rank.at[dates[i]] = _percentile(values[i], history)
            median.at[dates[i]] = float(np.median(history))
    return rank, median


def _col(key: str, label: str, kind: str = "text", unit: str = "") -> dict:
    return {"key": key, "label_vi": label, "kind": kind, "unit": unit}


def _num(value) -> float | None:
    return float(value) if pd.notna(value) else None


def _sources(*parts) -> list[str]:
    return sorted({source for part in parts for source in part if isinstance(source, str) and source})


class _Analytics:
    """Collect fact outcomes and schema-ready tables without mutating the input frames."""

    def __init__(self, frames: dict[str, pd.DataFrame], catalog: list[dict]):
        self.frames = frames
        self.catalog = {row["id"]: row for row in catalog}
        observations = self.frame("observations")
        for flag in ("is_imputed", "is_invalid"):
            if flag in observations:
                observations = observations.loc[~observations[flag].eq(True).fillna(False)]
        self.observations = _numeric(observations.reindex(columns=OBS_COLUMNS), ["value"])
        self.observations["period"] = self.observations["period"].astype("string")
        self.observations["base"] = self.observations["indicator_id"].map(self._base)
        geo = self.frame("geo").reindex(columns=["geo", "code", "name_vi", "region"])
        self.geo = {
            str(key): row
            for row in geo.to_dict("records") for key in (row["geo"], row["code"]) if pd.notna(key)
        }
        self.market = _date_frame(
            self.frame("market"), [], ["trading_value", "close", "pe", "pb", "advancers", "decliners", "unchanged", "foreign_net"],
        ).set_index("date")
        self.valuation = _date_frame(self.frame("valuation"), ["scope", "ticker"], ["pb", "pe", "roe"])
        self.tables: dict[str, list[dict]] = {}
        self.heatmap: dict[str, list[dict]] = {}
        self.asean: dict[str, dict] = {}
        self.province: dict = {"metric_ids": [], "rows": [], "groups": []}
        self.derived: list[dict] = []

    def _base(self, indicator) -> str | None:
        if not isinstance(indicator, str):
            return None
        meta = self.catalog.get(indicator, {})
        if "base_id" in meta:
            return meta["base_id"]
        for measure in MEASURE_SUFFIXES:
            suffix = f"_{measure}"
            if indicator.endswith(suffix):
                return indicator.removesuffix(suffix)
        return indicator

    def frame(self, key: str) -> pd.DataFrame:
        return self.frames.get(key, pd.DataFrame())

    def facts(self, *indicators: str, measure=None, geography="national") -> pd.DataFrame:
        rows = self.observations
        rows = rows.loc[
            (rows["indicator_id"].isin(indicators) | rows["base"].isin(indicators)) &
            rows["value"].notna() & rows["period"].notna() & rows["source_id"].notna()
        ]
        if measure:
            rows = rows.loc[rows["measure_type"].eq(measure)]
        if geography == "national":
            rows = rows.loc[rows["geo"].eq("VNM") | rows["geo_type"].eq("national")]
        elif geography is not None:
            rows = rows.loc[rows["geo_type"].isin([geography] if isinstance(geography, str) else geography)]
        return rows

    def unique(self, rows: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        primary = rows["indicator_id"].map(lambda indicator: self.catalog.get(indicator, {}).get("source_id"))
        return rows.assign(preferred=rows["source_id"].eq(primary)).sort_values(
            ["preferred", "source_id"], ascending=[False, True],
        ).drop_duplicates(keys)

    def latest(self, rows: pd.DataFrame, pattern=None) -> pd.Series | None:
        if pattern:
            rows = rows.loc[rows["period"].str.fullmatch(pattern)]
        if rows.empty:
            return None
        return self.unique(rows.loc[rows["period"].eq(rows["period"].max())], ["period"]).iloc[0]

    def aligned(self, left: pd.DataFrame, right: pd.DataFrame, *, same_source=True, pattern=MONTH):
        key = ["period", "unit", "source_id"] if same_source else ["period", "unit"]
        left = self.unique(left.loc[left["period"].str.fullmatch(pattern)], key)
        right = self.unique(right, key)
        common = left.merge(right[key], on=key)
        first = self.latest(common)
        if first is None:
            return None
        match = right.loc[(right[key] == first[key]).all(axis=1)].iloc[0]
        return first, match

    def geo_name(self, code: str) -> str:
        name = self.geo.get(code, {}).get("name_vi")
        return str(name) if pd.notna(name) and name else code

    def table(self, sector: str, id: str, title: str, columns: list[dict], rows: list[dict], sources: list[str]):
        if rows and sources:
            self.tables.setdefault(sector, []).append({
                "id": id, "title_vi": title, "columns": columns, "rows": rows, "source_ids": sources,
            })

    def series(self, indicator: str, values: pd.Series, unit: str, measure: str, *, geo="VNM", geo_type="country"):
        self.derived.extend({
            "indicator_id": indicator, "period": day.strftime("%Y-%m-%d"), "geo": geo, "geo_type": geo_type,
            "value": float(value), "unit": unit, "measure_type": measure, "source_id": "fiinquant",
        } for day, value in values.dropna().items())


def _fact(row: pd.Series, value: float, unit: str, sentence: str, *, fired=False, related=(), **extra) -> dict:
    return _number(row["period"], row["source_id"], value, unit, sentence, indicator_id=row["indicator_id"],
                   fired=fired, indicator_ids=list(dict.fromkeys([row["indicator_id"], *related])), **extra)


def _number(period, source: str, value: float, unit: str, sentence: str, *, fired=False, **extra) -> dict:
    if isinstance(period, pd.Timestamp):
        period = period.strftime("%Y-%m-%d")
    return {
        "status": "fired" if fired else "evaluated", "value": float(value), "unit": unit, "period": str(period),
        "source_id": source, "sentence_vi": sentence, "severity": "alert" if fired else "info", **extra,
    }


def _budget(a: _Analytics):
    pair = a.aligned(a.facts("nsnn_thu", measure="pct_plan"), a.facts("nsnn_chi", measure="pct_plan"))
    if pair is None:
        return None
    revenue, spend = pair
    pace = int(spend["period"][-2:]) / 12 * 100
    gap = revenue["value"] - spend["value"]
    sentence = (
        f"Thu vượt chi {_fmt(gap)} điểm phần trăm dự toán" if gap >= 0
        else f"Chi vượt thu {_fmt(-gap)} điểm phần trăm dự toán"
    ) if gap else "Thu và chi đều cùng tỷ lệ so với dự toán"
    return _fact(spend, gap, "điểm %", f"{sentence} kỳ {spend['period']}. Chi đạt {_fmt(spend['value'])}% "
                 f"so với mốc tiến độ {_fmt(pace)}%.", fired=spend["value"] < pace - 10,
                 related=[revenue["indicator_id"]], metrics={"revenue": revenue["value"], "spend": spend["value"], "pace": pace})


def _investment(a: _Analytics):
    rows = a.facts("dtc_giai_ngan", measure="pct_plan", geography=None)
    national = a.latest(rows.loc[rows["geo"].eq("VNM") | rows["geo_type"].eq("national")], MONTH)
    if national is None:
        return None
    period, value = national["period"], national["value"]
    pace = int(period[-2:]) / 12 * 100
    comparable = rows.loc[rows["period"].eq(period) & rows["unit"].eq(national["unit"])]
    geography = comparable["geo"].astype("string").str.lower()
    pair = a.aligned(
        comparable.loc[comparable["geo_type"].eq("central") | geography.eq("central")],
        comparable.loc[comparable["geo_type"].eq("local") | geography.eq("local")],
    )
    details = {"pace": pace, "national_rate": value}
    sources = [national["source_id"]]
    sentence = f"Giải ngân đầu tư công đạt {_fmt(value)}% kế hoạch kỳ {period}, so với mốc tiến độ {_fmt(pace)}%."
    if pair is not None:
        central, local = pair
        sources.append(central["source_id"])
        details["central_local_gap"] = central["value"] - local["value"]
        sentence += f" Chênh lệch trung ương trừ địa phương là {_fmt(details['central_local_gap'])} điểm phần trăm."
    units = comparable.loc[comparable["geo_type"].isin(["province", "ministry"])]
    units = a.unique(units, ["geo", "geo_type"])
    below = units.loc[units["value"].lt(value)].sort_values(["value", "geo"])
    a.table("public_finance", "investment_below_national", "Các đơn vị giải ngân thấp hơn tỷ lệ cả nước", [
        _col("name", "Đơn vị"), _col("kind", "Cấp quản lý"), _col("rate", "Giải ngân", "percent", "%"),
        _col("gap", "Chênh lệch với tỷ lệ cả nước", "number", "điểm %"), _col("period", "Kỳ", "date"),
    ], [{
        "geo": row.geo, "name": a.geo_name(row.geo), "kind": "Bộ, ngành" if row.geo_type == "ministry" else "Tỉnh, thành phố",
        "rate": float(row.value), "gap": float(row.value - value), "period": period,
    } for row in below.itertuples()], _sources([national["source_id"]], below["source_id"]))
    return _fact(national, value - pace, "điểm %", sentence, fired=value < pace, metrics=details,
                 source_ids=_sources(sources))


def _fdi_realisation(a: _Analytics):
    pair = a.aligned(a.facts("fdi_thuc_hien", measure="ytd"), a.facts("fdi_dang_ky", measure="ytd"))
    if pair is None:
        return None
    real, registered = pair
    if registered["value"] <= 0 or real["value"] < 0:
        return None
    ratio = real["value"] / registered["value"] * 100
    period = real["period"]
    real_yoy = a.facts("fdi_thuc_hien", measure="yoy")
    reg_yoy = a.facts("fdi_dang_ky", measure="yoy")
    matches = a.aligned(
        reg_yoy.loc[reg_yoy["period"].eq(period) & reg_yoy["source_id"].eq(real["source_id"])],
        real_yoy.loc[real_yoy["period"].eq(period) & real_yoy["source_id"].eq(real["source_id"])],
    )
    related = [registered["indicator_id"]]
    sentence = f"Vốn FDI thực hiện bằng {_fmt(ratio)}% vốn đăng ký lũy kế kỳ {period}."
    metrics = {"yoy_gap": None}
    if matches is not None:
        reg_growth, real_growth = matches
        related.extend([reg_growth["indicator_id"], real_growth["indicator_id"]])
        metrics.update(registered_yoy=reg_growth["value"], realised_yoy=real_growth["value"],
                       yoy_gap=reg_growth["value"] - real_growth["value"])
        sentence += (f" Thay đổi cùng kỳ của vốn đăng ký là {_fmt(reg_growth['value'])}% và vốn thực hiện "
                     f"là {_fmt(real_growth['value'])}%.")
    return _fact(real, ratio, "%", sentence, fired=metrics["yoy_gap"] is not None and metrics["yoy_gap"] > 30,
                 related=related, metrics=metrics,
                 caveat_vi="Tỷ số vốn thực hiện trên đăng ký là so sánh dòng vốn lũy kế tổng hợp giữa hai giai đoạn.")


def _fdi_concentration(a: _Analytics):
    rows = a.facts("fdi_dang_ky", measure="ytd", geography=None)
    rows = rows.loc[rows["geo"].notna() & rows["value"].ge(0) & rows["geo_type"].isin(["province", "partner"])]
    candidate = a.latest(rows)
    if candidate is None:
        return None
    period = candidate["period"]
    current = rows.loc[rows["period"].eq(period)]
    metrics = {"province_hhi": None, "partner_hhi": None}
    result = None
    sources = []
    for kind, title in [("province", "tỉnh"), ("partner", "đối tác")]:
        subset = current.loc[current["geo_type"].eq(kind)]
        row = a.latest(subset)
        if row is None:
            continue
        subset = subset.loc[subset["source_id"].eq(row["source_id"]) & subset["unit"].eq(row["unit"])]
        subset = a.unique(subset, ["geo"]).sort_values("value", ascending=False)
        total = subset["value"].sum()
        if len(subset) < 2 or total <= 0:
            continue
        sources.append(row["source_id"])
        shares = subset["value"] / total
        hhi = float((shares ** 2).sum())
        metrics[f"{kind}_hhi"] = hhi
        if kind == "province":
            a.table("fdi", "fdi_concentration", "Tỷ trọng vốn FDI theo tỉnh có số liệu", [
                _col("name", "Tỉnh, thành phố"), _col("share", "Tỷ trọng", "percent", "%"),
            ], [{"geo": item.geo, "name": a.geo_name(item.geo), "share": float(100 * share)}
                for item, share in zip(subset.itertuples(), shares)], [row["source_id"]])
            if len(subset) >= 3:
                top = subset["value"].head(3).sum() / total * 100
                result = _fact(row, top, "%", f"Ba tỉnh đứng đầu chiếm {_fmt(top)}% vốn FDI đăng ký của các tỉnh "
                               f"có số liệu kỳ {period}.")
        if result is None:
            result = _fact(row, hhi, "HHI", f"Chỉ số tập trung vốn FDI đăng ký theo {title} là "
                           f"{fmt.fixed(hhi, 3, lang='vi')} trong kỳ {period}.")
    if result is not None:
        result.update(metrics=metrics, source_ids=_sources(sources))
        for kind, title in [("province", "tỉnh"), ("partner", "đối tác")]:
            hhi = metrics[f"{kind}_hhi"]
            if hhi is not None and result["unit"] != "HHI":
                result["sentence_vi"] += f" HHI theo {title} là {fmt.fixed(hhi, 3, lang='vi')}."
    return result


def _credit_deposit(a: _Analytics):
    pair = a.aligned(a.facts("credit_ytd", "sbv_credit_growth", measure="ytd"),
                     a.facts("deposit_ytd", "sbv_deposit_growth", measure="ytd"), same_source=False)
    if pair is None:
        return None
    credit, deposits = pair
    if credit["unit"] != "%":
        return None
    gap = credit["value"] - deposits["value"]
    return _fact(credit, gap, "điểm %", f"Chênh lệch tăng trưởng tín dụng trừ tăng trưởng tiền gửi kỳ "
                 f"{credit['period']} là {_fmt(gap)} điểm phần trăm.", fired=gap > 1, related=[deposits["indicator_id"]],
                 source_ids=_sources([credit["source_id"], deposits["source_id"]]))


def _bank_quality(a: _Analytics):
    metrics = ["nim", "pb", "npl_proxy", "coverage", "ldr"]
    ratios = _numeric(a.frame("bank").reindex(columns=["ticker", "period", *metrics]), metrics)
    ratios["period"] = ratios["period"].astype("string")
    observed = a.facts("bank_npl", "bank_group2", "bank_coverage", measure="ratio", geography=("bank", "ticker"))
    observed = observed.loc[observed["unit"].eq("%")]
    periods = pd.concat([ratios["period"], observed["period"]]).dropna()
    quarters = periods.loc[periods.str.fullmatch(r"\d{4}-Q[1-4]")]
    if quarters.empty:
        return None
    period = quarters.max()
    ratios = ratios.loc[ratios["period"].eq(period)].dropna(subset=["ticker"]).drop_duplicates("ticker").set_index("ticker")
    observed = a.unique(observed.loc[observed["period"].eq(period)], ["geo", "base"])
    by_ticker = {(row.geo, row.base): row for row in observed.itertuples()}
    tickers = sorted(set(ratios.index) | set(observed["geo"].dropna()))
    rows = []
    for ticker in tickers:
        data = ratios.loc[ticker] if ticker in ratios.index else {}
        npl = by_ticker.get((ticker, "bank_npl"))
        group2 = by_ticker.get((ticker, "bank_group2"))
        coverage = by_ticker.get((ticker, "bank_coverage"))
        nim, pb = _num(data.get("nim")), _num(data.get("pb"))
        reported_coverage = coverage.value if coverage else _num(data.get("coverage"))
        comparable = npl is not None and reported_coverage is not None
        rows.append({
            "ticker": ticker, "period": period, "nim": nim, "pb": pb, "ldr": _num(data.get("ldr")),
            "npl_proxy": _num(data.get("npl_proxy")), "npl": _num(npl.value) if npl else None,
            "group2": _num(group2.value) if group2 else None, "coverage": _num(reported_coverage),
            "alert": bool(npl.value > 3 and reported_coverage < 100) if comparable else None,
        })
    for key in ("nim", "pb", "npl"):
        values = pd.Series([row[key] for row in rows], dtype=float).dropna()
        cuts = values.quantile([1 / 3, 2 / 3]).tolist() if len(values) >= 3 else []
        for row in rows:
            row[f"{key}_tier"] = bisect_left(cuts, row[key]) + 1 if cuts and row[key] is not None else None
    rows.sort(key=lambda row: (row["nim"] is None, -(row["nim"] or 0), row["ticker"]))
    sources = _sources([] if ratios.empty else ["fiinquant"], observed["source_id"])
    a.table("banking", "bank_league", "Các tỷ lệ ngân hàng cùng quý và nhóm theo phân vị", [
        _col("ticker", "Mã ngân hàng"), _col("period", "Quý", "date"),
        _col("nim", "Biên lãi ròng", "percent", "%"), _col("pb", "P/B", "number", "lần"),
        _col("ldr", "Dư nợ trên tiền gửi", "percent", "%"), _col("npl_proxy", "Khoản vay có vấn đề theo FiinQuant", "percent", "%"),
        _col("npl", "Nợ xấu công bố", "percent", "%"), _col("group2", "Nợ nhóm 2 công bố", "percent", "%"),
        _col("coverage", "Bao phủ nợ xấu", "percent", "%"), _col("nim_tier", "Nhóm biên lãi ròng", "number"),
        _col("pb_tier", "Nhóm P/B", "number"), _col("npl_tier", "Nhóm nợ xấu", "number"),
    ], rows, sources)
    comparable = [row for row in rows if row["alert"] is not None]
    if not comparable:
        return None
    triggered = [row for row in comparable if row["alert"]]
    representative = max(triggered or comparable, key=lambda row: row["npl"])
    npl = by_ticker[(representative["ticker"], "bank_npl")]
    coverage = by_ticker.get((representative["ticker"], "bank_coverage"))
    return _number(period, npl.source_id, representative["npl"], "%",
                   f"Nợ xấu công bố của {npl.geo} là {_fmt(representative['npl'])}% và bao phủ nợ xấu "
                   f"đạt {_fmt(representative['coverage'])}% trong quý {period}.",
                   fired=bool(triggered), indicator_id=npl.indicator_id,
                   indicator_ids=[npl.indicator_id, *([coverage.indicator_id] if coverage else [])],
                   source_ids=_sources([npl.source_id, coverage.source_id if coverage else "fiinquant"]),
                   metrics={"npl": representative["npl"], "coverage": representative["coverage"], "banks_flagged": len(triggered)})


def _bank_valuation(a: _Analytics):
    sectors = a.valuation.loc[a.valuation["scope"].str.lower().eq("sector")]
    rows = []
    bank = None
    for ticker, group in sectors.groupby("ticker"):
        group = group.set_index("date")
        pb = group["pb"].where(group["pb"].gt(0))
        rank, _ = _rank_history(pb, years=5)
        latest = pb.last_valid_index()
        if latest is None:
            continue
        row = {"ticker": ticker, "period": latest.strftime("%Y-%m-%d"), "pb": _num(pb.loc[latest]),
               "pb_pctile": _num(rank.loc[latest]), "roe": _num(group.at[latest, "roe"])}
        rows.append(row)
        if ticker.upper() == "BANKS_L2":
            a.series("bank_pb_pctile", rank, "%", "ratio")
            bank = row
    a.table("banking", "bank_valuation", "P/B các ngành và phân vị của chính ngành trong năm năm", [
        _col("ticker", "Mã ngành ICB"), _col("period", "Ngày", "date"),
        _col("pb", "P/B", "number", "lần"), _col("pb_pctile", "Phân vị P/B", "percent", "%"),
        _col("roe", "ROE", "percent", "%"),
    ], rows, ["fiinquant"])
    if bank is None or bank["pb_pctile"] is None:
        return None
    sentence = (f"P/B ngành ngân hàng đạt {_fmt(bank['pb'])} lần ngày {bank['period']}, "
                f"ở phân vị {_fmt(bank['pb_pctile'])}% so với năm năm trước.")
    if bank["roe"] is not None:
        sentence += f" ROE cùng ngày là {_fmt(bank['roe'])}%."
    return _number(bank["period"], "fiinquant", bank["pb_pctile"], "%", sentence,
                   indicator_id="bank_pb_pctile", indicator_ids=["bank_pb_pctile"], metrics=bank)


def _liquidity(a: _Analytics):
    traded = a.market["trading_value"].where(a.market["trading_value"].ge(0))
    avg = traded.rolling(20).mean()
    rank, median = _rank_history(avg, years=1)
    changes = a.market[["advancers", "decliners", "unchanged"]]
    total = changes.sum(axis=1, min_count=3)
    breadth = 100 * changes["advancers"] / total.where(total.gt(0))
    a.series("market_liquidity_20d", avg, "tỷ đồng", "level")
    a.series("market_liquidity_pctile", rank, "%", "ratio")
    a.series("market_breadth", breadth, "%", "ratio")
    latest = traded.last_valid_index()
    if latest is None or pd.isna(rank.loc[latest]):
        return None
    value, midpoint, percentile = avg.at[latest], median.at[latest], rank.at[latest]
    sentence = (f"Giá trị giao dịch bình quân 20 phiên trên các mã có dữ liệu đến {latest:%Y-%m-%d} đạt "
                f"{fmt.num(value, lang='vi')} tỷ đồng, ở phân vị {_fmt(percentile)}% so với năm trước. "
                f"Trung vị tham chiếu là {fmt.num(midpoint, lang='vi')} tỷ đồng.")
    details = {"median_1y": float(midpoint), "pctile": float(percentile), "breadth": _num(breadth.loc[latest])}
    if details["breadth"] is not None:
        details.update(advancers=int(changes.at[latest, "advancers"]), decliners=int(changes.at[latest, "decliners"]))
        sentence += f" Phiên cuối trên HOSE có {_fmt(details['breadth'])}% số mã tăng giá."
    return _number(latest, "fiinquant", value, "tỷ đồng", sentence, indicator_id="market_liquidity_20d",
                   indicator_ids=["market_liquidity_20d", "market_liquidity_pctile", "market_breadth"], metrics=details)


def _index_metrics(a: _Analytics):
    close = a.market["close"].where(a.market["close"].gt(0))
    drawdown = 100 * (close / close.cummax() - 1)
    a.series("vnindex_drawdown", drawdown, "%", "ratio")
    vnindex = a.valuation.loc[a.valuation["scope"].str.lower().eq("index") &
                              a.valuation["ticker"].str.upper().eq("VNINDEX")].set_index("date")
    for measure in ("pe", "pb"):
        valuation = vnindex[measure].combine_first(a.market[measure]).sort_index()
        rank, _ = _rank_history(valuation.where(valuation.gt(0)), years=5)
        a.series(f"vnindex_{measure}_pctile", rank, "%", "ratio")


def _foreign_flow(a: _Analytics):
    flow = a.market["foreign_net"]
    flow20, flow60 = flow.rolling(20).sum(), flow.rolling(60).sum()
    a.series("foreign_net_20d", flow20, "tỷ đồng", "level")
    a.series("foreign_net_60d", flow60, "tỷ đồng", "level")
    latest = flow.last_valid_index()
    sector_data = _date_frame(a.frame("foreign"), ["icb_l2"], ["foreign_net"])
    if not sector_data.empty:
        # Each industry window ends on the same market session, with no implicit zero for missing sessions.
        session_dates = flow.index[flow.index <= latest] if latest is not None else pd.DatetimeIndex(
            sector_data["date"].drop_duplicates(),
        )
        rows = []
        for ticker, group in sector_data.groupby("icb_l2"):
            sector = group.set_index("date")["foreign_net"].reindex(session_dates)
            last20 = sector.tail(20).sum(min_count=20)
            last60 = sector.tail(60).sum(min_count=60)
            if pd.notna(last20) or pd.notna(last60):
                rows.append({"icb_l2": ticker, "period": session_dates[-1].strftime("%Y-%m-%d"),
                             "net_20d": _num(last20), "net_60d": _num(last60)})
        rows.sort(key=lambda row: (row["net_20d"] is None, row["net_20d"] or 0, row["icb_l2"]))
        a.table("capital_market", "foreign_sector_flows", "Mua ròng khối ngoại theo ngành, xếp từ bán ròng lớn nhất", [
            _col("icb_l2", "Mã ngành ICB"), _col("period", "Phiên cuối", "date"),
            _col("net_20d", "Mua ròng 20 phiên", "number", "tỷ đồng"),
            _col("net_60d", "Mua ròng 60 phiên", "number", "tỷ đồng"),
        ], rows, ["fiinquant"])
    if latest is None or pd.isna(flow20.loc[latest]):
        return None
    current = flow20.loc[latest]
    sign = np.sign(flow.loc[latest])
    same_sign = np.sign(flow.loc[:latest].to_numpy()[::-1]) == sign
    streak = int(sign * np.count_nonzero(np.logical_and.accumulate(same_sign)))
    net_60d = _num(flow60.loc[latest])
    sentence = ("Khối ngoại cân bằng mua bán trong 20 phiên" if current == 0
                else f"Khối ngoại {'mua' if current > 0 else 'bán'} ròng {fmt.num(abs(current), lang='vi')} tỷ đồng trong 20 phiên")
    sentence += f" đến {latest:%Y-%m-%d}."
    if net_60d == 0:
        sentence += " Mua và bán cân bằng trong 60 phiên."
    elif net_60d is not None:
        sentence += (f" Khối ngoại {'mua' if net_60d > 0 else 'bán'} ròng "
                     f"{fmt.num(abs(net_60d), lang='vi')} tỷ đồng trong 60 phiên.")
    if streak:
        sentence += f" Chuỗi hiện tại có {fmt.count(abs(streak), lang='vi')} phiên {'mua' if streak > 0 else 'bán'} ròng liên tiếp."
    return _number(latest, "fiinquant", current, "tỷ đồng", sentence, indicator_id="foreign_net_20d",
                   indicator_ids=["foreign_net_20d", "foreign_net_60d"], metrics={"net_60d": net_60d, "streak": streak})


def _leverage(a: _Analytics):
    margin = a.facts("margin_debt", measure="level")
    current = a.latest(margin, r"\d{4}-Q[1-4]")
    if current is None:
        return None
    current_quarter = pd.Period(current["period"].replace("-", ""), freq="Q")
    prior_quarter = current_quarter - 1
    prior_period = f"{prior_quarter.year}-Q{prior_quarter.quarter}"
    prior = a.latest(margin.loc[margin["period"].eq(prior_period) & margin["unit"].eq(current["unit"]) &
                                margin["source_id"].eq(current["source_id"])])
    if prior is None or prior["value"] <= 0 or current["value"] < 0:
        return None
    values = a.market["trading_value"]
    quarter_means = []
    for quarter in (prior_quarter, current_quarter):
        start, end = quarter.start_time, quarter.end_time.normalize()
        sessions = values.loc[start:end]
        if (sessions.empty or sessions.isna().any() or sessions.index[0] > start + pd.Timedelta(days=7)
                or sessions.index[-1] < end - pd.Timedelta(days=7)):
            return None
        quarter_means.append(sessions.mean())
    if quarter_means[0] <= 0:
        return None
    growth = 100 * (current["value"] / prior["value"] - 1)
    liquidity = float(100 * (quarter_means[1] / quarter_means[0] - 1))
    return _fact(current, growth, "%",
                 f"Dư nợ ký quỹ thay đổi {_fmt(growth)}% trong quý {current['period']}, trong khi "
                 f"giá trị giao dịch bình quân phiên thay đổi {_fmt(liquidity)}% so với quý trước.",
                 fired=growth * liquidity < 0, related=["market_liquidity_20d"],
                 source_ids=_sources([current["source_id"], "fiinquant"]), metrics={"liquidity_growth": liquidity})


def _real_estate(a: _Analytics):
    scope = ("national", "country", "city")
    supplies = a.facts("re_new_supply", measure="level", geography=scope)
    absorption = a.facts("re_absorption", geography=scope)
    rates = a.facts("mortgage_rate")
    rates = rates.loc[rates["unit"].eq("%")]
    join_keys = ["period", "geo_type", "geo", "source_id"]
    supply = a.unique(supplies, join_keys)
    absorbed = a.unique(absorption, join_keys)
    matched = absorbed.merge(supply[join_keys], on=join_keys)
    matched = matched.loc[matched["period"].isin(rates["period"])]
    first = a.latest(matched, r"\d{4}-(Q[1-4]|\d{2})")
    if first is None:
        return None
    period = first["period"]
    second = supply.loc[(supply[join_keys] == first[join_keys]).all(axis=1)].iloc[0]
    if second["value"] <= 0 or first["value"] < 0:
        return None
    if first["unit"] == "%":
        rate_absorption = first["value"]
    elif first["unit"] == second["unit"]:
        rate_absorption = first["value"] / second["value"] * 100
    else:
        return None
    rate = a.latest(rates.loc[rates["period"].eq(period)])
    previous = _previous_period(period)
    prior_rate = a.latest(rates.loc[rates["period"].eq(previous) & rates["source_id"].eq(rate["source_id"])])
    gap = None if prior_rate is None else _num(rate["value"] - prior_rate["value"])
    place = f" tại {first['geo']}" if first["geo_type"] == "city" else ""
    sentence = f"Tỷ lệ hấp thụ nhà ở{place} kỳ {period} là {_fmt(rate_absorption)}%, với nguồn cung mới {fmt.num(second['value'], lang='vi')} "
    sentence += f"{second['unit']} và lãi suất vay mua nhà {_fmt(rate['value'])}%."
    if gap is not None:
        sentence += f" Lãi suất thay đổi {_fmt(gap)} điểm phần trăm so với kỳ trước."
    return _fact(first, rate_absorption, "%", sentence, related=[second["indicator_id"], rate["indicator_id"]],
                 source_ids=_sources([first["source_id"], rate["source_id"]]),
                 metrics={"new_supply": _num(second["value"]), "mortgage_rate": _num(rate["value"]), "mortgage_gap": gap},
                 caveat_vi="Rổ dự án, phân khúc hoặc khu vực có thể thay đổi giữa kỳ. Chỉ so sánh hấp thụ và nguồn cung trong cùng phạm vi công bố.")


def _previous_period(period: str) -> str:
    if "-Q" in period:
        quarter = pd.Period(period.replace("-", ""), freq="Q") - 1
        return f"{quarter.year}-Q{quarter.quarter}"
    return str(pd.Period(period, freq="M") - 1)


def _asean_rank(a: _Analytics):
    facts = a.observations
    facts = facts.loc[facts["geo"].isin(ASEAN_NAMES) & facts["period"].str.fullmatch(r"\d{4}") &
                      facts["source_id"].eq("wdi") & facts["value"].notna()]
    ranked = {}
    for indicator, rows in facts.groupby("indicator_id"):
        frame = a.unique(rows, ["geo", "period"]).pivot(index="period", columns="geo", values="value").dropna()
        if "VNM" not in frame or len(frame.columns) < 2 or frame.empty:
            continue
        year = frame.index.max()
        values = frame.loc[year]
        higher = a.catalog.get(indicator, {}).get("higher_is_better", True)
        ranks = values.rank(method="min", ascending=not higher).astype(int)
        leader_board = [{"iso3": iso, "name_vi": ASEAN_NAMES[iso], "value": float(values[iso]), "rank": int(ranks[iso])}
                        for iso in ranks.sort_values(kind="stable").index]
        n, median, vn_rank = len(leader_board), float(values.median()), int(ranks["VNM"])
        a.asean[indicator] = {"year": int(year), "rows": leader_board, "vn_rank": vn_rank, "n": n,
                              "median": median, "higher_is_better": bool(higher), "source_id": "wdi"}
        vn = rows.loc[rows["geo"].eq("VNM") & rows["period"].eq(year)].iloc[0]
        gap = float(values["VNM"] - median)
        unit = "điểm %" if vn["unit"].startswith("%") else vn["unit"]
        name = a.catalog.get(indicator, {}).get("name_vi", "Chỉ tiêu")
        ranked[indicator] = _fact(vn, gap, unit, f"{name} của Việt Nam xếp hạng {fmt.count(vn_rank, lang='vi')} "
                                   f"trong {fmt.count(n, lang='vi')} nước ASEAN có số liệu chung năm {year}. "
                                   f"Chênh lệch với trung vị là {_fmt(gap)} {unit}.",
                                   metrics={"rank": vn_rank, "n": n, "median": median})
    result = ranked.get("tax_revenue_pct_gdp") or next(iter(ranked.values()), None)
    if result:
        result["metrics"]["comparisons"] = {
            indicator: {"period": row["period"], "gap": row["value"], "unit": row["unit"],
                        "rank": row["metrics"]["rank"], "sentence_vi": row["sentence_vi"]}
            for indicator, row in ranked.items()
        }
    return result


def _province(a: _Analytics):
    rows = a.facts("earmarked_transfers", geography="province")
    current = a.latest(rows, r"\d{4}")
    if current is None:
        return None
    period, primary = current["period"], current["indicator_id"]
    facts = a.observations.loc[
        a.observations["geo_type"].eq("province") & a.observations["period"].eq(period) &
        a.observations["value"].notna() & a.observations["geo"].notna() & a.observations["source_id"].notna()
    ]
    facts = a.unique(facts, ["indicator_id", "geo"])
    pivot = facts.pivot(index="geo", columns="indicator_id", values="value")
    values = pivot[primary].dropna()
    cuts = [float(values.min()), *values.quantile([0.2, 0.4, 0.6, 0.8]).tolist(), float(values.max())]
    province_geos = a.frame("geo")
    if {"geo", "geo_type"}.issubset(province_geos.columns):
        pivot = pivot.reindex(sorted(set(pivot.index) | set(province_geos.loc[
            province_geos["geo_type"].eq("province"), "geo",
        ].dropna())))
    metrics = [primary, *sorted(set(pivot.columns) - {primary})]
    groups = []
    provinces = []
    counts = [0] * 5
    for geo, row in pivot.iterrows():
        meta = a.geo.get(geo, {})
        group = None
        if pd.notna(row[primary]):
            group = bisect_left(cuts[1:-1], row[primary]) + 1
            counts[group - 1] += 1
        code = meta.get("code")
        region = meta.get("region")
        provinces.append({"code": str(code) if pd.notna(code) else geo, "name": a.geo_name(geo),
                          "region": str(region) if pd.notna(region) else "",
                          "metrics": {indicator: _num(row[indicator]) for indicator in metrics}, "group": group})
    for i, (lower, upper, count) in enumerate(zip(cuts, cuts[1:], counts), 1):
        groups.append({"group": i, "label_vi": f"Nhóm {i}", "min": float(lower), "max": float(upper), "count": count})
    stats = {indicator: {"median": float(values.median()), "min": float(values.min()),
                         "max": float(values.max()), "n": int(values.count())}
             for indicator, values in pivot.items()}
    median = stats[primary]["median"]
    unit = current["unit"]
    sentence = f"Trung vị khoản bổ sung có mục tiêu năm {period} là {fmt.num(median, lang='vi')} {unit} mỗi tỉnh có số liệu."
    a.province = {"metric_ids": metrics, "primary_metric": primary, "rows": provinces, "groups": groups, "stats": stats,
                  "source_ids": _sources(facts["source_id"]), "headline_vi": sentence,
                  "question_vi": "Khoản bổ sung có mục tiêu phân bố thế nào theo tỉnh, thành phố?"}
    return _fact(current, median, unit, sentence, metrics=stats[primary])


def _monthly_heatmap(a: _Analytics):
    best = None
    for indicator, meta in sorted(a.catalog.items()):
        if meta.get("frequency") != "monthly":
            continue
        rows = a.observations.loc[a.observations["indicator_id"].eq(indicator) &
                                  (a.observations["geo"].eq("VNM") | a.observations["geo_type"].eq("national")) &
                                  a.observations["period"].str.fullmatch(MONTH)]
        if meta.get("source_id"):
            rows = rows.loc[rows["source_id"].eq(meta["source_id"])]
        rows = a.unique(rows, ["period"])
        if rows.empty:
            continue
        dates = pd.PeriodIndex(rows["period"], freq="M")
        values = pd.Series(rows["value"].to_numpy(), index=dates).reindex(pd.period_range(dates.min(), dates.max(), freq="M"))
        ranked = values.rolling(12).apply(lambda arr: _percentile(arr[-1], arr), raw=True)
        cells = [{"period": str(period), "value": _num(value), "pctile": _num(rank)}
                 for period, value, rank in zip(values.tail(36).index, values.tail(36), ranked.tail(36))]
        a.heatmap.setdefault(meta["sector"], []).append({"indicator_id": indicator, "cells": cells})
        last = ranked.last_valid_index()
        if last is not None and (best is None or str(last) > best["period"]):
            fact = rows.loc[rows["period"].eq(str(last))].iloc[0]
            name = meta.get("name_vi", "Chỉ tiêu")
            rank = ranked.at[last]
            best = _fact(fact, rank, "%", f"{name} kỳ {last} nằm ở phân vị {_fmt(rank)}% trong 12 tháng gần nhất.")
    return best


def evaluate(frames: dict[str, pd.DataFrame], catalog: list[dict]) -> dict:
    """Return rule metadata, outcomes, views, and derived indicator observations."""
    analytics = _Analytics(frames, catalog)
    handlers = [
        _budget, _investment, _fdi_realisation, _fdi_concentration, _credit_deposit, _bank_quality, _bank_valuation,
        _liquidity, _foreign_flow, _leverage, _real_estate, _asean_rank, _province, _monthly_heatmap,
    ]
    outcomes = []
    rules = []
    for rule, handler in zip(RULES, handlers, strict=True):
        fact = handler(analytics)
        outcome = {"id": rule.id, "sector": rule.sector, "chart_id": rule.chart_id, "agency_vi": rule.agency_vi,
                   "action_vi": rule.action_vi, "so_what_vi": rule.so_what_vi}
        if fact:
            outcome.update(fact)
        else:
            outcome.update(status="not evaluated", sentence_vi=f"{rule.name_vi} chưa đủ dữ liệu cùng kỳ để đánh giá.")
        rules.append({
            "id": rule.id, "name_vi": rule.name_vi, "formula_vi": rule.formula_vi,
            "threshold_vi": rule.threshold_vi, "agency_vi": rule.agency_vi, "fired": outcome["status"] == "fired",
        })
        outcomes.append(outcome)
    _index_metrics(analytics)
    return {"rules": rules, "results": outcomes, "asean": analytics.asean, "province": analytics.province,
            "heatmap": analytics.heatmap, "tables": analytics.tables, "derived": analytics.derived}
