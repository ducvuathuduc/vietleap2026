"""Decision layer: turn the top insights into 3–5 'So what → Now what' recommendations with an expected-impact estimate."""
from __future__ import annotations

from . import fmt

AUDIENCE = {
    "property": ("buyers, developers and housing policymakers", "người mua, chủ đầu tư và cơ quan quản lý nhà ở"),
    "public_finance": ("provincial finance departments and policymakers", "Sở Tài chính và nhà hoạch định chính sách"),
    "firm": ("investors and company management", "nhà đầu tư và ban điều hành doanh nghiệp"),
    "generic": ("decision makers", "người ra quyết định"),
}


def recommend(insights: list[dict], domain: str, target: str, drivers: dict | None, max_recs: int = 5) -> list[dict]:
    aud_en, aud_vi = AUDIENCE.get(domain, AUDIENCE["generic"])
    recs = []
    for ins in insights:
        t, ev = ins["type"], ins["evidence"]
        rec = None
        if t == "segment_gap":
            top, bot, by = ev["top"], ev["bottom"], ev["by"]
            gap = (ev["overall_median"] / bot["median"] - 1) * 100 if bot["median"] else None
            rec = {
                "so_what_en": f"{target} is {ev['top_vs_bottom']['median_ratio']}× higher in {top['group']} than in {bot['group']} — {by} is a primary lens for {aud_en}.",
                "now_what_en": f"Prioritise/price by {by}: benchmark each {by} against the overall median and target the lowest-ranked groups (e.g. {bot['group']}) with a focused programme; validate with the {by}-level table.",
                "so_what_vi": f"{target} ở {top['group']} cao gấp {ev['top_vs_bottom']['median_ratio']} lần {bot['group']} — {by} là lăng kính chính cho {aud_vi}.",
                "now_what_vi": f"Phân bổ ưu tiên theo {by}: so sánh từng nhóm với trung vị chung, tập trung chương trình hỗ trợ/định giá cho nhóm thấp nhất (vd. {bot['group']}).",
                "impact_en": f"Closing the gap of the lowest group to the overall median ≈ {fmt.pct(gap)} for that group." if gap is not None else "Impact depends on group size.",
                "impact_vi": f"Kéo nhóm thấp nhất về trung vị chung ≈ {fmt.pct(gap, 'vi')} cho nhóm đó." if gap is not None else "Tác động phụ thuộc quy mô nhóm.",
            }
        elif t in ("trend", "forecast"):
            fc = ev if t == "forecast" else None
            rec = {
                "so_what_en": f"{target} follows a measurable trajectory ({ins['sentence_en'].split(';')[0]}).",
                "now_what_en": "Plan budgets/prices on the forecast range rather than the last value; set an early-warning threshold at the 80% band and review quarterly.",
                "so_what_vi": f"{target} có quỹ đạo rõ ràng theo thời gian.",
                "now_what_vi": "Lập kế hoạch theo khoảng dự báo thay vì giá trị kỳ gần nhất; đặt ngưỡng cảnh báo sớm tại biên 80% và rà soát hàng quý.",
                "impact_en": (f"Next-period range {fmt.num(fc['lower80'][0], target)}–{fmt.num(fc['upper80'][0], target)}." if fc else "Reduces planning error vs naive extrapolation."),
                "impact_vi": (f"Khoảng kỳ tới {fmt.num(fc['lower80'][0], target, 'vi')}–{fmt.num(fc['upper80'][0], target, 'vi')}." if fc else "Giảm sai số kế hoạch."),
            }
        elif t == "what_if":
            rec = {
                "so_what_en": f"{ev['feature']} is the most stable lever associated with {target}.",
                "now_what_en": f"Treat {ev['feature']} as a planning lever/benchmark: size scenarios with the what-if calculator before committing resources, then validate on comparable cases or a pilot.",
                "so_what_vi": f"{ev['feature']} là đòn bẩy ổn định nhất gắn với {target}.",
                "now_what_vi": f"Xem {ev['feature']} là đòn bẩy/chuẩn so sánh: ước lượng kịch bản bằng công cụ what-if trước khi phân bổ nguồn lực, rồi kiểm chứng bằng trường hợp tương tự hoặc thí điểm.",
                "impact_en": f"+10% {ev['feature']} ↔ {fmt.pct(ev['target_change_pct'])} {target} (90% CI {fmt.pct(ev['ci90_pct'][0])} to {fmt.pct(ev['ci90_pct'][1])}); association, test with a pilot.",
                "impact_vi": f"+10% {ev['feature']} ↔ {fmt.pct(ev['target_change_pct'], 'vi')} {target} (KTC 90% {fmt.pct(ev['ci90_pct'][0], 'vi')} đến {fmt.pct(ev['ci90_pct'][1], 'vi')}).",
            }
        elif t == "concentration":
            rec = {
                "so_what_en": f"Activity is concentrated: top 20% hold {ev['top20_share'] * 100:.0f}% (Gini {ev['gini']:.2f}).",
                "now_what_en": "Treat the top units as a separate tier (dedicated monitoring/resources) and design a different, lighter-touch approach for the long tail.",
                "so_what_vi": f"Mức tập trung cao: 20% đứng đầu chiếm {ev['top20_share'] * 100:.0f}%.",
                "now_what_vi": "Tách nhóm dẫn đầu thành tầng riêng (giám sát/nguồn lực riêng), thiết kế cách tiếp cận gọn nhẹ cho phần đuôi dài.",
                "impact_en": "Focusing on the top quintile covers the majority of the total with a fraction of the effort.",
                "impact_vi": "Tập trung vào nhóm 20% đầu bao phủ phần lớn tổng giá trị với ít nguồn lực.",
            }
        elif t == "drivers":
            top = [i["feature"] for i in ev["importance"][:3]]
            rec = {
                "so_what_en": f"{', '.join(top)} carry most of the predictive signal for {target} (CV R² {ins['value']:.2f}).",
                "now_what_en": f"Use these variables as the KPI set to monitor {target}; collect better data on them first.",
                "so_what_vi": f"{', '.join(top)} mang phần lớn tín hiệu dự báo {target}.",
                "now_what_vi": f"Dùng các biến này làm bộ KPI theo dõi {target}; ưu tiên cải thiện chất lượng dữ liệu của chúng.",
                "impact_en": "Better targeting of monitoring; not a causal guarantee.",
                "impact_vi": "Giám sát đúng trọng tâm; không phải bảo đảm nhân quả.",
            }
        elif t == "segmentation":
            rec = {
                "so_what_en": f"The data splits into {ev['k']} distinct profiles; one-size-fits-all policies will miss them.",
                "now_what_en": "Tailor the offer/policy per segment; start with the largest segment and the one with the most extreme profile.",
                "so_what_vi": f"Dữ liệu chia thành {ev['k']} nhóm hồ sơ khác biệt; chính sách đồng loạt sẽ bỏ sót.",
                "now_what_vi": "Thiết kế giải pháp theo từng phân khúc; bắt đầu với nhóm lớn nhất và nhóm có hồ sơ khác biệt nhất.",
                "impact_en": f"Largest segment = {ev['profiles'][0]['share'] * 100:.0f}% of records.",
                "impact_vi": f"Nhóm lớn nhất = {ev['profiles'][0]['share'] * 100:.0f}% số bản ghi.",
            }
        if rec:
            rec.update({"from_insight": ins["id"], "type": t, "confidence": "high" if ins["p_value"] is not None and ins["p_value"] < 0.01 else "medium"})
            if not any(r["type"] == t for r in recs):
                recs.append(rec)
        if len(recs) >= max_recs:
            break
    return recs
