// Guided tour (driver.js) — per-page steps over elements tagged with data-insight-target / data-tour.

export interface TourStep {
  selector: string
  title: string
  description: string
}

const INSPECT: TourStep = {
  selector: '[data-tour="inspect-toggle"]',
  title: "Hỏi AI về bất kỳ phần tử nào",
  description: "Bật chế độ này, rê chuột lên KPI, biểu đồ, dòng bảng, giai đoạn pipeline… rồi bấm để AI Analyst giải thích bằng số liệu thật từ engine (Esc để thoát).",
}

const PAGES: Record<string, TourStep[]> = {
  "/": [
    { selector: '[data-insight-target^="kpi:"]', title: "Thẻ KPI", description: "Chỉ số chính của dataset (trung vị, quy mô mẫu, xu hướng) do engine tính trên bảng gold." },
    { selector: '[data-insight-target="chart:timeseries"]', title: "Xu hướng theo thời gian", description: "Trung vị chỉ số mục tiêu theo kỳ; chọn khoảng thời gian ở góc phải." },
    { selector: '[data-tour="insights-table"]', title: "Bảng insight xếp hạng", description: "Mỗi dòng là một phát hiện có kiểm định thống kê, effect size và mức ý nghĩa; bấm tiêu đề để xem chi tiết." },
  ],
  "/pipeline": [
    { selector: '[data-insight-target="pipeline-stage:ingestion"]', title: "1 · Ingestion", description: "Thu thập từ DB/JDBC, Public API, file, web scraping, social listening — có provenance cho từng nguồn." },
    { selector: '[data-insight-target="pipeline-stage:storage"]', title: "2 · Storage", description: "DuckDB + Parquet theo medallion bronze/silver/gold, giữ dữ liệu thô để audit." },
    { selector: '[data-insight-target="pipeline-stage:transform"]', title: "3 · Transform", description: "Làm sạch missing/duplicate/outlier và dựng OBT, Star, Snowflake, Data Vault." },
    { selector: '[data-insight-target="pipeline-stage:serving"]', title: "4 · Serving", description: "Bảng gold phục vụ dashboard, SQL Explorer và AI Analyst." },
    { selector: '[data-tour="lineage"]', title: "Lineage", description: "Sơ đồ nguồn → bronze → silver → gold: mọi con số truy được về nguồn." },
  ],
  "/quality": [
    { selector: '[data-insight-target^="quality:"]', title: "Điểm chất lượng", description: "Điểm 0–100 trước và sau làm sạch, tính từ tỉ lệ thiếu, sai định dạng, trùng lặp." },
    { selector: '[data-insight-target="chart:missing"]', title: "% thiếu theo cột", description: "So sánh mức thiếu dữ liệu từng cột trước/sau làm sạch." },
    { selector: '[data-tour="cleaning-log"]', title: "Nhật ký làm sạch", description: "Mọi biến đổi bronze → silver được ghi lại để giám khảo kiểm tra." },
  ],
  "/model": [
    { selector: '[data-tour="model-choice"]', title: "Chọn mô hình", description: "OBT, Star, Snowflake, Data Vault đều được sinh tự động; bảng này nói mô hình nào dùng cho việc gì." },
    { selector: '[data-insight-target^="model:"]', title: "Chi tiết mô hình", description: "Lý do chọn, danh sách bảng gold, ERD và SQL DuckDB đã chạy." },
  ],
  "/brief": [
    { selector: '[aria-label="Đề bài"]', title: "Dán đề bài", description: "Dán nguyên văn đề của BTC; kit trích câu hỏi, biến mục tiêu, đơn vị, loại quyết định và chọn gói kịch bản phù hợp." },
  ],
  "/decision": [
    { selector: '[data-insight-target^="decision:"]', title: "Khuyến nghị", description: "Mỗi khuyến nghị sinh từ một insight đã kiểm định: vấn đề, hành động, tác động ước tính, mức tin cậy." },
  ],
  "/insights": [
    { selector: '[data-insight-target^="insight:"]', title: "Insight", description: "Phát hiện kèm kiểm định, p-value, effect size và lưu ý; xếp hạng theo độ mạnh × ý nghĩa × liên quan." },
  ],
  "/segments": [
    { selector: '[data-insight-target^="segment:"]', title: "Phân khúc", description: "Trung vị chỉ số mục tiêu theo nhóm; kiểm định cho biết khác biệt có thật hay do ngẫu nhiên." },
  ],
  "/drivers": [
    { selector: '[data-insight-target^="driver:"]', title: "Yếu tố tác động", description: "Hệ số chuẩn hoá có khoảng tin cậy bootstrap; “ổn định” nghĩa là khoảng 90% không chứa 0." },
    { selector: '[data-insight-target^="whatif:"]', title: "Kịch bản what-if", description: "Thay đổi một yếu tố và xem chỉ số mục tiêu dịch chuyển bao nhiêu, kèm khoảng 90%." },
  ],
}

/** Steps for a route, keeping only elements present on the page. */
export function tourSteps(pathname: string, exists: (selector: string) => boolean): TourStep[] {
  return [...(PAGES[pathname] ?? []), INSPECT].filter((s) => exists(s.selector))
}
