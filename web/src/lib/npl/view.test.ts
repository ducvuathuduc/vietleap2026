import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"

import {
  BADGE_LABEL,
  DECODER_DISCLAIMER,
  LARGE_BANKS,
  PAGE_SHELL,
  SERIES_ATTRIBUTION,
  applyPublishFlag,
  bankModel,
  bankRows,
  buildFiinQuantDecoder,
  decoderModel,
  formatNumber,
  marketModel,
  methodModel,
  nextPeriod,
  overviewModel,
  publicCsv,
  sortDataRows,
  type Snapshot,
} from "./view.ts"

function term(coef: number, wild: number | null = 0.01) {
  const low = Number((coef - 0.1).toFixed(1))
  const high = Number((coef + 0.1).toFixed(1))
  return { coef_pp: coef, ci95: [low, high] as [number, number], p: 0.01, p_wild_bootstrap: wild, n: 10, clusters: 3 }
}

function effect(quarter: number, coef: number) {
  return { quarter, ...term(coef) }
}

function mini(options?: { drop?: ReturnType<typeof term> | null; wild?: number | null; publish?: boolean }): Snapshot {
  const wild = options && "wild" in options ? options.wild ?? null : 0.01
  const drop = options && "drop" in options ? options.drop : term(-0.7, wild)
  return {
    _fixture_note: "test",
    meta: {
      snapshot_id: "test",
      generated_at: "2026-11-20T16:00:00+07:00",
      period_start: "2021Q1",
      period_end: "2026Q3",
      n_banks: 4,
      n_bank_quarters: 8,
      publish_bank_series: options?.publish === true,
      sources: [{ id: "fiin_ratios", name: "FiinQuant", method: "api", url: "https://docs.fiinquant.vn/", licence: "FiinGroup", retrieved_at: "2026-11-20T16:00:00+07:00", rows: 8 }],
      quality: [],
      cleaning: [{ step: "Đơn vị", before: 8, after: 8, detail: "Quy đổi sang phần trăm." }],
      schema: [{ table: "fact_bank_quarter", keys: "bank_code, period, basis", grain: "Ngân hàng × quý" }],
      eda: { href: "#eda", summary_vi: "Thiếu được giữ.", summary_en: "Missing cells are kept." },
    },
    headline: { vi: "HEADLINE VI", en: "HEADLINE EN", keys: ["M2.baseline.terms.Q4.coefficient"] },
    kpis: {
      level: { npl_median_pct: 2.22, period: "2026Q3", n_banks: 23 },
      benchmark: term(-0.4, wild),
      trend: {
        down_then_up: [{ year: 2025, share_pct: 70, n: 20 }],
        npl_4q_avg_median_pct: 1.8,
        period: "2025Q4–2026Q3",
      },
    },
    series: {
      median_by_period: [
        { period: "2021Q4", npl_median_pct: 1.5, npl_p25_pct: 1.1, npl_p75_pct: 1.9, coverage_median_pct: 80, n_banks: 4 },
        { period: "2026Q3", npl_median_pct: 2.22, npl_p25_pct: 1.8, npl_p75_pct: 2.6, coverage_median_pct: 62, n_banks: 23 },
      ],
    },
    quarter_effects: [effect(2, -0.1), effect(3, -0.2), effect(4, -0.4)],
    banks: [
      {
        code: "VCB",
        ticker: "VCB",
        name_vi: "VCB",
        name_en: "VCB",
        ownership: "state",
        q4_change_median_pp: -0.3,
        q1_rebound_median_pp: 0.2,
        down_then_up_years: 2,
        years: 2,
        quarter_means: [{ quarter: 2, mean_pp: -0.15 }, { quarter: 3, mean_pp: -0.05 }, { quarter: 4, mean_pp: -0.3 }],
        pairs: [{ year: 2025, q4_pp: -0.3, q1_pp: 0.2, reversed: true }],
        latest: { period: "2026Q3", adjusted_change_pp: 0.05, forecast_next: { period: "2026Q4", npl_pct: 2.1, lo80: 1.5, hi80: 2.7 } },
        signals: [],
        quarters: [{ period: "2026Q3", d_npl_pp: -0.11, adjusted_change_pp: 0.05 }],
        series: [{ period: "2026Q3", npl_pct: 9.99, coverage_pct: 60, ldr_pct: 70, nim_pct: 3, loan_growth_pct: 8 }],
      },
      {
        code: "SSB",
        ticker: "SSB",
        name_vi: "SSB",
        name_en: "SSB",
        ownership: "private",
        q4_change_median_pp: -0.05,
        q1_rebound_median_pp: -0.02,
        down_then_up_years: 1,
        years: 2,
        quarter_means: [{ quarter: 4, mean_pp: -0.05 }],
        pairs: [{ year: 2025, q4_pp: -0.05, q1_pp: -0.02, reversed: false }],
        latest: { period: "2026Q3", adjusted_change_pp: -0.01, forecast_next: null },
        signals: [],
        quarters: [{ period: "2026Q2", d_npl_pp: 0.04, adjusted_change_pp: 0.14 }],
      },
      {
        code: "AAA",
        ticker: "AAA",
        name_vi: "AAA",
        name_en: "AAA",
        ownership: "private",
        q4_change_median_pp: -0.2,
        q1_rebound_median_pp: 0.1,
        down_then_up_years: 0,
        years: 1,
        quarter_means: [],
        pairs: [],
        latest: null,
        signals: [{ id: "S1", period: "2026Q3", text_vi: "Tín hiệu thử", text_en: "Test signal" }],
        quarters: [],
      },
      {
        code: "BBB",
        ticker: "BBB",
        name_vi: "BBB",
        name_en: "BBB",
        ownership: "private",
        q4_change_median_pp: -0.8,
        q1_rebound_median_pp: 0.4,
        down_then_up_years: 0,
        years: 1,
        quarter_means: [],
        pairs: [],
        latest: null,
        signals: [],
        quarters: [],
      },
    ],
    heterogeneity: { pre_period: "2021Q1–2022Q4", high_banks: ["AAA"], q4_high_npl: term(-0.05), q4_state: term(-0.02) },
    linkage: { roa_absent: true, coverage_q4: term(13), nim_q4: null, loan_growth_q4: null, roa_q4: null },
    market: {
      car_by_day: [
        { group: "all", day: 0, n: 5, mean_car_pct: 0.1, ci95: [-0.1, 0.3] },
        { group: "Q4", day: 0, n: 2, mean_car_pct: -0.2, ci95: [-0.4, 0] },
      ],
      regressions: {
        raw: { n: 8, clusters: 3, period: ["2021Q2", "2026Q3"], terms: { d_npl_pct: term(-1.5, null) }, unavailable_reason: null },
      },
      events_with_car: 8,
      eligible_bank_quarters: 10,
      period_start: "2021Q2",
      period_end: "2026Q3",
      reading_vi: "ĐỌC M6",
      reading_en: "M6 READING",
    },
    forecast: {
      backtest: [],
      mae: { model: 0.4, last_value: 0.3, seasonal_naive: 0.9 },
      train_through: "2024Q4",
      test_period: ["2025Q1", "2026Q3"],
      reading_vi: "ĐỌC M7",
      reading_en: "M7 READING",
    },
    robustness: {
      leave_one_bank_out: { min: -0.47, max: -0.39 },
      drop_2021_2022: drop,
      state_vs_private: { state: term(-0.5, wild), private: term(-0.33, wild) },
      state_vs_private_effects: { state: [effect(2, -0.11), effect(3, -0.22), effect(4, -0.5)], private: [effect(2, -0.12), effect(3, -0.13), effect(4, -0.33)] },
      drop_effects: drop ? [effect(2, -0.21), effect(3, -0.31), effect(4, -0.7)] : [],
      median_regression: term(-0.32, null),
      year_fe: term(-0.28, wild),
    },
    method: ["M1", "M2", "M3", "M4", "M5", "M6", "M7"].map((id) => ({
      id,
      name_vi: id,
      name_en: id,
      spec_vi: `SPEC ${id}`,
      spec_en: `SPEC ${id}`,
      n: id === "M2" ? 10 : 4,
      reading_vi: `READING ${id}`,
      reading_en: `READING ${id}`,
      does_not_show_vi: `NOT ${id}`,
      does_not_show_en: `NOT ${id}`,
    })),
    limitations: [{ vi: "Giới hạn", en: "Limit" }],
    legal: [{ ref: "Ghi chú nghiên cứu", text_vi: "Ghi chú nghiên cứu. Không phải khuyến nghị mua hoặc bán một ngân hàng.", text_en: "Research note. Not a recommendation to buy or sell a bank." }],
    ai_use: [{ vi: "Trang này không gọi mô hình ngôn ngữ.", en: "This page does not call a language model." }],
  }
}

test("overview reads the headline and the three key numbers from the snapshot", () => {
  const model = overviewModel(mini(), "vi")
  assert.equal(model.headline, "HEADLINE VI")
  assert.equal(model.level.value, 2.22)
  assert.equal(model.level.period, "2026Q3")
  assert.equal(model.level.nBanks, 23)
  assert.equal(model.benchmark.coef, -0.4)
  assert.deepEqual(model.benchmark.ci, [-0.5, -0.3])
  assert.equal(model.benchmark.n, 10)
  assert.equal(model.benchmark.clusters, 3)
  assert.equal(model.trend.shares[0]?.share, 70)
  assert.equal(model.trend.repeatCount, 1)
  assert.equal(model.series.find((row) => row.period === "2021Q4")?.q4, true)
  assert.equal(model.series.find((row) => row.period === "2026Q3")?.q4, false)
  assert.deepEqual(model.bars.map((bar) => bar.quarter), [2, 3, 4])
  assert.equal(model.bars[2]?.coef, -0.4)
  assert.match(model.decision, /Chưa coi mức giảm NPL quý 4 là cải thiện bền/)
  assert.match(model.decision, /-0,400/)
})

test("Vietnamese figures use a decimal comma and the headline is the plain sentence", () => {
  assert.equal(formatNumber(-0.425606, "vi", 2), "-0,43")
  assert.equal(formatNumber(2.22, "vi", 2), "2,22")
  assert.equal(formatNumber(1234, "vi", 0), "1.234")
  assert.equal(formatNumber(-0.426, "en", 2), "-0.43")
  const snapshot = mini()
  snapshot.meta.n_banks = 27
  snapshot.kpis.benchmark = { ...snapshot.kpis.benchmark, coef_pp: -0.425606, ci95: [-0.576508, -0.274704], n: 576, p_wild_bootstrap: 0.001, clusters: 27 }
  snapshot.kpis.trend.down_then_up = [
    { year: 2021, share_pct: 40.7407, n: 27 },
    { year: 2022, share_pct: 44.4444, n: 27 },
    { year: 2023, share_pct: 70.3704, n: 27 },
    { year: 2024, share_pct: 68, n: 25 },
    { year: 2025, share_pct: 53.8462, n: 26 },
  ]
  const model = overviewModel(snapshot, "vi")
  assert.match(model.plainHeadline, /Quý 4 nào nợ xấu cũng đẹp hơn: trung bình giảm 0,43 điểm % so với quý 1/)
  assert.match(model.plainHeadline, /73\/132 trường hợp \(27 ngân hàng, 2021–2026\)/)
  assert.doesNotMatch(model.plainHeadline, /0\.43|get_ratios|consolidated/)
  assert.match(model.evidenceLine, /-0,58 đến -0,27/)
  assert.match(model.evidenceLine, /n = 576/)
  assert.match(model.evidenceLine, /0,001/)
  assert.equal(model.cards[0]?.title, "Nợ xấu trung vị hiện nay")
  assert.match(model.cards[0]?.figure ?? "", /2,22%/)
  assert.match(model.cards[0]?.help ?? "", /2026Q3, 23 ngân hàng/)
  assert.equal(model.cards[1]?.title, "Quý 4 so với quý 1")
  assert.match(model.cards[1]?.figure ?? "", /-0,43 điểm %/)
  assert.equal(model.cards[2]?.title, "Giảm rồi tăng lại")
  assert.match(model.cards[2]?.help ?? "", /53,8% năm 2025/)
  assert.match(model.cards[2]?.help ?? "", /70,4% năm 2023/)
  assert.equal(model.why.length, 2)
  assert.match(model.why[0] ?? "", /Nợ xấu trung vị quý 2026Q3 là 2,22% trên 23 ngân hàng/)
  assert.match(model.why[1] ?? "", /0,43 điểm %/)
  assert.match(model.why[1] ?? "", /2025/)
  assert.match(model.why[1] ?? "", /70,4% năm 2023/)
  assert.doesNotMatch(model.why.join(" "), / · |S4|M7|snapshot/)
  const englishWhy = overviewModel(snapshot, "en")
  assert.equal(englishWhy.cards[1]?.title, "Q4 versus Q1")
  assert.equal(englishWhy.why.length, 2)
  assert.match(englishWhy.why[0] ?? "", /2\.22%/)
  assert.match(englishWhy.why[1] ?? "", /0\.43/)
  assert.equal(model.q4Mark?.period, "2021Q4")
  assert.match(model.footer.publicLine, /Nguồn: FiinQuant \(FiinGroup\), báo cáo tài chính hợp nhất/)
  assert.match(model.footer.publicLine, /dữ liệu đến 2026Q3/)
  assert.doesNotMatch(model.footer.publicLine, /get_ratios|consolidated/)
  const english = overviewModel(snapshot, "en")
  assert.match(english.plainHeadline, /falls 0\.43 percentage points/)
  assert.match(english.plainHeadline, /73\/132/)
})

test("ownership and the 2021-2022 switch change the coefficient on screen", () => {
  const state = overviewModel(mini(), "en", { ownership: "state", dropEarly: false })
  assert.equal(state.benchmark.coef, -0.5)
  assert.equal(state.bars[2]?.coef, -0.5)
  const dropped = overviewModel(mini(), "en", { ownership: "state", dropEarly: true })
  assert.equal(dropped.benchmark.coef, -0.7)
  assert.equal(dropped.bars[2]?.coef, -0.7)
  const missing = overviewModel(mini({ drop: null }), "vi", { ownership: "all", dropEarly: true })
  assert.equal(missing.dropEnabled, false)
  assert.equal(missing.benchmark.coef, -0.4)
  assert.match(missing.dropReason ?? "", /chưa/)
})

test("a missing wild-bootstrap p-value is said to be absent and is not printed as zero", () => {
  const model = overviewModel(mini({ wild: null }), "vi")
  assert.equal(model.benchmark.wild, null)
  assert.match(model.benchmark.wildText, /chưa có/)
  assert.doesNotMatch(model.benchmark.wildText, /0\.000/)
})

test("bank rows sort by the Q4 median and the ownership filter keeps one group", () => {
  assert.deepEqual(bankRows(mini(), "private").map((row) => row.code), ["BBB", "AAA", "SSB"])
  assert.deepEqual(bankRows(mini(), "state").map((row) => row.code), ["VCB"])
  assert.deepEqual(bankRows(mini(), "all").map((row) => row.code), ["BBB", "VCB", "AAA", "SSB"])
})

test("a bank outside the every-year list is not given that list's sentence", () => {
  const model = bankModel(mini(), "ssb", "vi")
  assert.equal(model?.everyYear, false)
  assert.match(model?.headline ?? "", /không nằm trong danh sách/)
  assert.doesNotMatch(model?.headline ?? "", /đảo chiều ở mọi cặp năm của ngân hàng này/)
})

test("a bank that reversed every pair says so, and raw lines stay hidden until publication is on", () => {
  const hidden = bankModel(mini(), "VCB", "vi")
  assert.equal(hidden?.everyYear, true)
  assert.match(hidden?.headline ?? "", /đảo chiều ở mọi cặp năm của ngân hàng này/)
  assert.equal(hidden?.lines, null)
  assert.equal(hidden?.forecast?.npl, 2.1)
  assert.equal(hidden?.mae.model, 0.4)
  assert.equal(hidden?.mae.lastValue, 0.3)
  assert.equal(hidden?.attribution, null)
  const shown = bankModel(mini({ publish: true }), "VCB", "en")
  assert.equal(shown?.lines?.length, 1)
  assert.equal(shown?.lines?.[0]?.npl, 9.99)
  assert.equal(shown?.lines?.[0]?.coverage, 60)
  assert.equal(shown?.lines?.[0]?.ldr, 70)
  assert.equal(shown?.lines?.[0]?.nim, 3)
  assert.equal(shown?.lines?.[0]?.loanGrowth, 8)
  assert.equal(shown?.attribution, SERIES_ATTRIBUTION)
  assert.equal(SERIES_ATTRIBUTION, "Nguồn: FiinQuant (FiinGroup)")
})

test("NPL_PUBLISH_BANK_SERIES=0 turns publication off and drops the series", () => {
  const open = applyPublishFlag(mini({ publish: true }), undefined)
  assert.equal(open.meta.publish_bank_series, true)
  assert.equal(open.banks[0]?.series?.[0]?.npl_pct, 9.99)
  const closed = applyPublishFlag(mini({ publish: true }), "0")
  assert.equal(closed.meta.publish_bank_series, false)
  assert.equal(closed.banks[0]?.series, undefined)
  assert.equal(bankModel(closed, "VCB", "vi")?.lines, null)
  assert.equal(applyPublishFlag(mini({ publish: true }), "1").meta.publish_bank_series, true)
})

test("public csv keeps derived columns and adds raw columns only when publication is on", () => {
  const hidden = publicCsv(mini())
  assert.match(hidden.split("\n")[0] ?? "", /d_npl_pp,adjusted_change_pp/)
  assert.doesNotMatch(hidden, /npl_pct/)
  assert.doesNotMatch(hidden, /9\.99/)
  const shown = publicCsv(mini({ publish: true }))
  assert.match(shown.split("\n")[0] ?? "", /npl_pct/)
  assert.match(shown, /9\.99/)
})

test("market sentences use the regression coefficient and both CAR groups", () => {
  const model = marketModel(mini(), "en")
  assert.deepEqual(model.groups, ["all", "Q4"])
  assert.equal(model.points[0]?.all, 0.1)
  assert.equal(model.points[0]?.q4, -0.2)
  assert.match(model.rows[0]?.text ?? "", /-1\.500/)
  assert.equal(model.reading, "M6 READING")
})

test("market rows name both effects and do not say snapshot or a model id", () => {
  const snapshot = mini()
  snapshot.market.regressions = {
    reported_or_deadline: {
      n: 567,
      clusters: 27,
      period: ["2021Q2", "2026Q3"],
      terms: {
        expected_d_npl_pct: term(-2.816),
        surprise_d_npl_pct: term(-1.238),
      },
      unavailable_reason: null,
    },
    actual_dates: { n: 0, clusters: 0, period: null, terms: {}, unavailable_reason: "no_observations" },
  }
  const text = marketModel(snapshot, "en").rows.map((row) => row.text).join("\n")
  assert.match(text, /Expected change/)
  assert.match(text, /Surprise/)
  assert.match(text, /-2\.816/)
  assert.match(text, /-1\.238/)
  assert.match(text, /no figure yet/)
  assert.doesNotMatch(text, /snapshot|fixture|\bactual_dates\b|\bM[1-7]\b|\bS[1-4]\b/)
  const vi = marketModel(snapshot, "vi").rows.map((row) => row.text).join("\n")
  assert.match(vi, /Phần dự kiến/)
  assert.match(vi, /Phần bất ngờ/)
  assert.doesNotMatch(vi, /snapshot|bản chụp|fixture|\bactual_dates\b|\bM[1-7]\b|\bS[1-4]\b/)
})

test("missing-figure copy does not say snapshot", () => {
  const dropped = overviewModel(mini({ drop: null }), "en")
  assert.doesNotMatch(dropped.dropReason ?? "", /snapshot/)
  const quiet = overviewModel(mini({ wild: null }), "en")
  assert.doesNotMatch(quiet.evidenceLine, /snapshot/)
  assert.doesNotMatch(quiet.decision, /snapshot/)
})

test("method cards are M1 through M7 and copy the snapshot reading", () => {
  const model = methodModel(mini(), "vi")
  assert.deepEqual(model.models.map((item) => item.id), ["M1", "M2", "M3", "M4", "M5", "M6", "M7"])
  assert.equal(model.models[1]?.reading, "READING M2")
  assert.equal(model.models[1]?.n, 10)
  assert.equal(model.models[1]?.doesNotShow, "NOT M2")
  assert.equal(model.edaHref, "#eda")
})

test("detail rows sort by the chosen column", () => {
  const rows = [
    { bank_code: "B", period: "2021Q1", d_npl_pp: 1, adjusted_change_pp: 0 },
    { bank_code: "A", period: "2021Q2", d_npl_pp: -1, adjusted_change_pp: 2 },
  ]
  assert.deepEqual(sortDataRows(rows, "bank_code", 1).map((row) => row.bank_code), ["A", "B"])
  assert.deepEqual(sortDataRows(rows, "d_npl_pp", -1).map((row) => row.bank_code), ["B", "A"])
})

test("the next quarter rolls from Q4 into the next year", () => {
  assert.equal(nextPeriod("2026Q3"), "2026Q4")
  assert.equal(nextPeriod("2026Q4"), "2027Q1")
})

test("the decoder flags a coverage decline and a usual Q4 move, and never calls missing notes clean", () => {
  const cells = buildFiinQuantDecoder([
    {
      code: "VCB",
      series: [
        { period: "2023Q3", npl_pct: 2, coverage_pct: 100 },
        { period: "2023Q4", npl_pct: 1, coverage_pct: 110 },
        { period: "2024Q3", npl_pct: 1.4, coverage_pct: 100 },
        { period: "2024Q4", npl_pct: 1.2, coverage_pct: 120 },
        { period: "2025Q1", npl_pct: 1.2, coverage_pct: 120 },
        { period: "2025Q2", npl_pct: 1.0, coverage_pct: 90 },
        { period: "2025Q3", npl_pct: 0.9, coverage_pct: 95 },
        { period: "2025Q4", npl_pct: 0.5, coverage_pct: 140 },
        { period: "2026Q1", npl_pct: 0.7, coverage_pct: 130 },
        { period: "2026Q2", npl_pct: 0.7, coverage_pct: 100 },
        { period: "2026Q3", npl_pct: null, coverage_pct: 100 },
      ],
    },
    {
      code: "ABB",
      series: [
        { period: "2025Q1", npl_pct: 2, coverage_pct: 40 },
        { period: "2025Q2", npl_pct: 2.2, coverage_pct: 40 },
      ],
    },
  ], "2026Q3")
  const byPeriod = Object.fromEntries(cells.filter((cell) => cell.bank === "VCB").map((cell) => [cell.period, cell]))
  assert.equal(byPeriod["2025Q2"]?.d_npl_pp, -0.2)
  assert.equal(byPeriod["2025Q2"]?.status, "coverage")
  assert.deepEqual(byPeriod["2025Q2"]?.signals.map((signal) => signal.id), ["S3"])
  assert.equal(byPeriod["2025Q4"]?.d_npl_pp, -0.4)
  assert.equal(byPeriod["2025Q4"]?.status, "seasonal")
  assert.deepEqual(byPeriod["2025Q4"]?.signals.map((signal) => signal.id), ["S4"])
  assert.equal(byPeriod["2025Q3"]?.status, "missing")
  assert.equal(byPeriod["2026Q1"]?.status, "no_fall")
  assert.equal(byPeriod["2026Q3"]?.status, "missing")
  assert.equal(byPeriod["2025Q2"]?.inputs.group2, null)
  assert.equal(byPeriod["2025Q2"]?.inputs.writeoff, null)
  assert.equal(byPeriod["2025Q2"]?.inputs.ratios.coverage.value, 90)
  assert.equal(byPeriod["2025Q2"]?.inputs.ratios.npl_ratio.source, "FiinQuant (FiinGroup)")
  assert.equal(byPeriod["2025Q2"]?.inputs.ratios.npl_ratio.page, null)
  const both = buildFiinQuantDecoder([
    {
      code: "BVB",
      series: [
        { period: "2022Q3", npl_pct: 3, coverage_pct: 50 },
        { period: "2022Q4", npl_pct: 2.5, coverage_pct: 50 },
        { period: "2023Q3", npl_pct: 2.2, coverage_pct: 50 },
        { period: "2023Q4", npl_pct: 2, coverage_pct: 50 },
        { period: "2024Q3", npl_pct: 2, coverage_pct: 50 },
        { period: "2024Q4", npl_pct: 1, coverage_pct: 40 },
        { period: "2025Q3", npl_pct: 1.5, coverage_pct: 40 },
        { period: "2025Q4", npl_pct: 1.2, coverage_pct: 30 },
      ],
    },
  ], "2026Q3")
  const flagged = both.find((cell) => cell.period === "2025Q4")
  assert.deepEqual(flagged?.signals.map((signal) => signal.id), ["S3", "S4"])
  assert.equal(flagged?.status, "coverage")
  const table = decoderModel({ decoder: cells } as Snapshot, "vi")
  assert.deepEqual(table.rows.map((row) => row.bank), ["VCB"])
  assert.deepEqual(table.periods, ["2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"])
  assert.equal(table.rows[0]?.cells[0]?.label, BADGE_LABEL.coverage.vi)
  assert.equal(table.rows[0]?.cells[2]?.label, BADGE_LABEL.seasonal.vi)
  assert.equal(table.rows[0]?.cells[3]?.label, null)
  assert.match(table.rows[0]?.cells[1]?.reading ?? "", /không gọi là cải thiện có cơ sở/)
  assert.equal(table.disclaimer, DECODER_DISCLAIMER.vi)
  assert.equal(DECODER_DISCLAIMER.vi, "Tool chỉ nêu cờ cần xem xét, không kết luận ngân hàng che giấu nợ xấu")
  assert.equal(BADGE_LABEL.clean.vi, "Cải thiện có cơ sở")
  assert.equal(BADGE_LABEL.g2.vi, "Cờ vàng: nhóm 2 tăng")
  assert.equal(BADGE_LABEL.writeoff.vi, "Cờ vàng: xóa nợ tăng")
  assert.equal(BADGE_LABEL.coverage.vi, "Cờ vàng: bao phủ giảm")
  assert.equal(BADGE_LABEL.seasonal.vi, "Nhịp mùa vụ cuối năm")
  assert.equal(BADGE_LABEL.missing.vi, "Thiếu dữ liệu")
  assert.equal(decoderModel({ decoder: cells } as Snapshot, "en").rows[0]?.cells[0]?.label, BADGE_LABEL.coverage.en)
  assert.deepEqual(LARGE_BANKS, ["VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "STB"])
  const all = decoderModel({ decoder: cells } as Snapshot, "vi", "all")
  assert.ok(all.periods.includes("2023Q4"))
  assert.ok(all.periods.length > 6)
  assert.deepEqual(all.rows.map((row) => row.bank), ["VCB", "ABB"])
  assert.equal(table.moreLabel, "Xem tất cả ngân hàng")
  assert.match(table.note, /Dải mùa vụ của chính ngân hàng đó/)
  assert.doesNotMatch(table.note, /S4|M7|snapshot/)
  assert.equal(table.rows[0]?.cells[0]?.badges.join(" "), "Bao phủ giảm")
  assert.equal(table.rows[0]?.cells[0]?.pending, "Chưa có nhóm 2, xóa nợ")
  assert.equal(table.rows[0]?.cells[0]?.largeMove, false)
  assert.match(table.rows[0]?.cells[2]?.badges.join(" ") ?? "", /Trong nhịp mùa vụ/)
  assert.match(table.rows[0]?.cells[2]?.badges.join(" ") ?? "", /Bao phủ không giảm/)
  assert.equal(table.rows[0]?.cells[1]?.badges.includes("Cải thiện có cơ sở"), false)
  assert.equal(table.rows[0]?.cells[1]?.pending, "Chưa có nhóm 2, xóa nợ")
})

test("a published decoder object supplies ratios, flags and the plain reading", () => {
  const publication = {
    rows: [{ bank_code: "VCB", period: "2021Q1", npl_ratio: null, delta_npl_ratio: null, status: "missing_data", signals: [] }],
    focus: [{
      bank_code: "VCB",
      period: "2025Q2",
      npl_ratio: 0.01,
      coverage: 2.1384,
      loan_growth: 0.1406,
      delta_npl_ratio: -0.0003,
      delta_coverage: -0.0227,
      delta_g2_ratio: 0.003,
      status: "missing_data",
      signals: [{ id: "S3", text_vi: "Đệm dự phòng mỏng đi", text_en: "Provision buffer thinner" }],
    }],
    fiinquant_rows: [{ bank_code: "ABB", period: "2025Q4", npl_ratio: 0.02, delta_npl_ratio: -0.001, status: "not_applicable", signals: [] }],
  }
  const preview = decoderModel({ decoder: publication } as unknown as Snapshot, "vi")
  assert.deepEqual(preview.rows.map((row) => row.bank), ["VCB"])
  const cell = preview.rows[0]?.cells.find((item) => item?.period === "2025Q2")
  assert.equal(cell?.dNpl, -0.03)
  assert.equal(cell?.status, "coverage")
  assert.equal(cell?.inputs.ratios.npl_ratio.value, 1)
  assert.match(cell?.reading ?? "", /NPL giảm 0,03 điểm %/)
  assert.match(cell?.reading ?? "", /nợ nhóm 2 tăng 0,30 điểm %/)
  const full = decoderModel({ decoder: publication } as unknown as Snapshot, "vi", "all")
  assert.equal(full.periods[0], "2021Q1")
  assert.equal(full.rows.some((row) => row.bank === "ABB"), true)
})

test("a falling quarter with missing notes still shows the coverage and seasonal checks", () => {
  const publication = {
    rows: [
      {
        bank_code: "VCB",
        period: "2025Q4",
        npl_ratio: 0.01,
        coverage: 1.2,
        delta_npl_ratio: -0.002,
        delta_coverage: 0.01,
        status: "missing",
        signals: [{ id: "S4", text_vi: "Nhịp mùa vụ cuối năm", text_en: "Usual year-end movement" }],
        missing_inputs: ["delta_g2_ratio", "delta_writeoff_ratio"],
      },
      {
        bank_code: "STB",
        period: "2025Q4",
        npl_ratio: 0.07,
        coverage: 0.35,
        delta_npl_ratio: 0.0366,
        delta_coverage: -0.43,
        status: "not_applicable",
        signals: [],
        missing_inputs: [],
      },
      {
        bank_code: "ACB",
        period: "2025Q3",
        npl_ratio: 0.012,
        coverage: 1.1,
        delta_npl_ratio: -0.001,
        delta_coverage: -0.02,
        delta_g2_ratio: 0.004,
        delta_writeoff_ratio: -0.001,
        status: "review",
        signals: [{ id: "S1", text_vi: "Nhóm 2 tăng", text_en: "Group 2 rose" }, { id: "S3", text_vi: "Bao phủ giảm", text_en: "Coverage fell" }],
        missing_inputs: [],
      },
      {
        bank_code: "BID",
        period: "2025Q2",
        npl_ratio: 0.011,
        coverage: 1.4,
        delta_npl_ratio: -0.001,
        delta_coverage: 0.02,
        delta_g2_ratio: -0.001,
        delta_writeoff_ratio: -0.001,
        status: "clean",
        signals: [],
        missing_inputs: [],
      },
    ],
  }
  const model = decoderModel({ decoder: publication } as unknown as Snapshot, "vi")
  const vcb = model.rows.find((row) => row.bank === "VCB")?.cells.find((item) => item?.period === "2025Q4")
  assert.deepEqual(vcb?.badges, ["Bao phủ không giảm", "Trong nhịp mùa vụ"])
  assert.equal(vcb?.pending, "Chưa có nhóm 2, xóa nợ")
  assert.equal(vcb?.badges.includes("Cải thiện có cơ sở"), false)
  assert.equal(vcb?.badges.includes("Thiếu dữ liệu"), false)
  const stb = model.rows.find((row) => row.bank === "STB")?.cells.find((item) => item?.period === "2025Q4")
  assert.equal(stb?.dNplText, "3,66")
  assert.equal(stb?.largeMove, true)
  const acb = model.rows.find((row) => row.bank === "ACB")?.cells.find((item) => item?.period === "2025Q3")
  assert.equal(acb?.pending, null)
  assert.ok(acb?.badges.includes("Nhóm 2 tăng"))
  assert.ok(acb?.badges.includes("Bao phủ giảm"))
  assert.ok(acb?.badges.includes("Xóa nợ không tăng"))
  const bid = model.rows.find((row) => row.bank === "BID")?.cells.find((item) => item?.period === "2025Q2")
  assert.deepEqual(bid?.badges, ["Cải thiện có cơ sở"])
  assert.equal(bid?.pending, null)
  const english = decoderModel({ decoder: publication } as unknown as Snapshot, "en")
  const englishVcb = english.rows.find((row) => row.bank === "VCB")?.cells.find((item) => item?.period === "2025Q4")
  assert.deepEqual(englishVcb?.badges, ["Coverage did not fall", "Inside the year-end range"])
  assert.equal(englishVcb?.pending, "Group 2 and write-offs are not in yet")
})

test("the published snapshot shows group-2 and write-off badges only when those inputs exist", () => {
  const path = join(dirname(fileURLToPath(import.meta.url)), "../../../seed/npl/snapshot.json")
  const snapshot = JSON.parse(readFileSync(path, "utf8")) as Snapshot
  const decoder = snapshot.decoder
  assert.ok(decoder && !Array.isArray(decoder))
  const model = decoderModel(snapshot, "vi", "all")
  const both = "Chưa có nhóm 2, xóa nợ"
  let sawGroup2 = 0
  let sawWriteoff = 0
  for (const row of decoder.rows ?? []) {
    if (row.delta_npl_ratio == null || row.delta_npl_ratio >= 0) continue
    const cell = model.rows.find((item) => item.bank === row.bank_code)?.cells.find((item) => item?.period === row.period)
    assert.ok(cell, `${row.bank_code} ${row.period}`)
    const g2Known = row.delta_g2_ratio != null || (row.signals ?? []).some((signal) => signal.id === "S1")
    const writeoffKnown = row.delta_writeoff_ratio != null || (row.signals ?? []).some((signal) => signal.id === "S2")
    const text = cell.badges.join(" ")
    if (cell.status === "clean") {
      assert.deepEqual(cell.badges, ["Cải thiện có cơ sở"])
      assert.equal(cell.pending, null)
      continue
    }
    if (g2Known) {
      sawGroup2 += 1
      assert.match(text, row.delta_g2_ratio != null && row.delta_g2_ratio <= 0 && !(row.signals ?? []).some((signal) => signal.id === "S1") ? /Nhóm 2 không tăng/ : /Nhóm 2 tăng/)
    } else {
      assert.equal(text.includes("Nhóm 2"), false)
    }
    if (writeoffKnown) {
      sawWriteoff += 1
      assert.match(text, row.delta_writeoff_ratio != null && row.delta_writeoff_ratio <= 0 && !(row.signals ?? []).some((signal) => signal.id === "S2") ? /Xóa nợ không tăng/ : /Xóa nợ tăng/)
    } else {
      assert.equal(text.includes("Xóa nợ"), false)
    }
    if (g2Known && writeoffKnown) assert.equal(cell.pending, null)
    else if (!g2Known && !writeoffKnown) assert.equal(cell.pending, both)
    else assert.notEqual(cell.pending, both)
  }
  const ctg = model.rows.find((row) => row.bank === "CTG")?.cells.find((item) => item?.period === "2026Q1")
  assert.ok(ctg?.badges.includes("Nhóm 2 tăng"))
  assert.notEqual(ctg?.pending, both)
  assert.ok(sawGroup2 > 0)
  assert.equal(sawWriteoff, (decoder.rows ?? []).filter((row) => row.delta_npl_ratio != null && row.delta_npl_ratio < 0 && (row.delta_writeoff_ratio != null || (row.signals ?? []).some((signal) => signal.id === "S2"))).length)
})

test("the page shell clips horizontal overflow", () => {
  assert.match(PAGE_SHELL, /overflow-x-hidden/)
  const layout = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../app/(npl)/layout.tsx"), "utf8")
  assert.match(layout, /overflow-x-hidden/)
  const table = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../components/npl/data-table.tsx"), "utf8")
  assert.match(table, /overflow-x-auto/)
  const overview = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../app/(npl)/page.tsx"), "utf8")
  assert.match(overview, /Tỷ lệ nợ xấu giảm chưa chứng minh tín dụng tốt hơn/)
  assert.match(overview, /Vì sao cần kiểm tra/)
  assert.match(overview, /DecoderTable/)
  assert.match(overview, /Glossary/)
  assert.match(overview, /Cách đọc/)
  assert.doesNotMatch(overview, /→/)
  assert.doesNotMatch(overview, / · /)
  assert.doesNotMatch(overview, /Kiểm tra độ vững/)
  assert.match(overview, /KeyNumbers/)
  assert.match(overview, /model\.why/)
  assert.doesNotMatch(overview, /cards\.map/)
  assert.doesNotMatch(overview, /footer\.legal/)
  assert.match(overview, /hideSource/)
  const charts = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../components/npl/charts.tsx"), "utf8")
  assert.match(charts, /strokeWidth=\{2\.5\}/)
  assert.match(charts, /stroke="var\(--foreground\)"/)
  assert.match(charts, /animationDuration=\{800\}/)
  assert.match(charts, /fill="var\(--color-band\)"/)
  assert.match(charts, /bg-foreground/)
  assert.match(charts, /% dư nợ/)
  assert.match(charts, /25–75% ngân hàng/)
  assert.match(charts, /Quý 4/)
  assert.match(charts, /25%/)
  assert.match(charts, /75%/)
  const decoder = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../components/npl/decoder-table.tsx"), "utf8")
  assert.match(decoder, /"Ngân hàng"/)
  assert.match(decoder, /chưa công bố/)
  assert.match(decoder, /biến động lớn/)
  assert.doesNotMatch(decoder, /"Mã"/)
  const banks = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../app/(npl)/ngan-hang/page.tsx"), "utf8")
  assert.match(banks, /"Ngân hàng"/)
  assert.doesNotMatch(banks, /"Mã"/)
  assert.match(banks, /HowToRead/)
  assert.match(banks, /Cách đọc/)
  const data = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../components/npl/data-table.tsx"), "utf8")
  assert.doesNotMatch(data, /vi: "Mã"/)
  const bar = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../components/npl/site-bar.tsx"), "utf8")
  assert.match(bar, /Sau tỷ lệ nợ xấu/)
  assert.match(bar, /Behind the NPL Ratio/)
  assert.doesNotMatch(bar, / · /)
  assert.match(bar, /md:hidden/)
  assert.match(bar, /hidden md:flex/)
  assert.match(bar, /flex-nowrap/)
  assert.match(bar, /NplAskDock/)
  assert.match(bar, /href="#content"/)
  const bankPage = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../app/(npl)/ngan-hang/[code]/page.tsx"), "utf8")
  assert.doesNotMatch(bankPage, /[Bb]ản chụp|snapshot|fixture/)
  assert.match(charts, /HowToRead/)
  assert.ok((charts.match(/<HowToRead/g) ?? []).length >= 3)
  const method = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../app/(npl)/phuong-phap/page.tsx"), "utf8")
  assert.match(method, /Kiểm tra độ vững/)
  assert.match(method, /QuarterChart/)
  assert.doesNotMatch(method, /→/)
  assert.doesNotMatch(method, /get_ratios/)
})
