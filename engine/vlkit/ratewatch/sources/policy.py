"""Dated deposit-policy references verified in B-POLICY and V-LAW."""
DIV = "https://www.div.gov.vn/"


def policy_rows():
    ceiling = "https://sbv.gov.vn/vi/w/sbv618464"
    cap = DIV + "tu-ngay-13-7-2026-han-muc-chi-tra-tien-bao-hiem-cua-bao-hiem-tien-gui-viet-nam-la-350-trieu-dong"
    premium = DIV + "quyen-va-nghia-vu-cua-to-chuc-tham-gia-bao-hiem-tien-gui-theo-luat-bao-hiem-tien-gui-nam-2025"
    coverage = DIV + "se-co-thong-tu-moi-ve-han-muc-chi-tra-tien-bao-hiem"
    basis = "Đánh giá phương án 350 triệu đồng của NHNN trên số liệu ngày 31/12/2025"
    entries = [
        ("ceiling", "pct", 4.75, "%/năm", "Quyết định 2411/QĐ-NHNN", "2024-11-20", "1 đến dưới 6 tháng", ceiling),
        ("demand_ceiling", "pct", 0.5, "%/năm", "Quyết định 2411/QĐ-NHNN", "2024-11-20", "Không kỳ hạn và dưới 1 tháng", ceiling),
        ("cap", "vnd", 350_000_000, "VND", "Thông tư 05/2026/TT-NHNN", "2026-07-13", "Gốc và lãi mỗi người tại mỗi tổ chức", cap),
        ("premium", "pct", 0.15, "%/năm", "Thông tư 04/2026/TT-NHNN", None, "Số dư bình quân được bảo hiểm", premium),
        ("insured_coverage", "depositors_pct", 93.68, "%", "Đánh giá của NHNN", None, basis, coverage),
        ("insured_coverage", "value_pct", 19.06, "%", "Đánh giá của NHNN", None, basis, coverage),
    ]
    return [
        dict(parameter=param, metric=metric, value=value, unit=unit, legal_ref=legal, valid_from=start,
             basis=detail, source_url=url, source_id=url, publisher="NHNN" if url == ceiling else "Bảo hiểm tiền gửi Việt Nam",
             licence="Nguồn công khai", method="Văn bản công khai")
        for param, metric, value, unit, legal, start, detail, url in entries
    ]
