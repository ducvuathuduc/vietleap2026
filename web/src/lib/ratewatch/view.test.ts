import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"

import { formatAmountInput, formatPct, formatReadClock, formatVnd, parseAmountInput } from "./format.ts"
import { bandRates, bankMenuLabel, buildHeadline, chartFinding, chartPoints, clampCompare, gradeBadge, keyNumbers, mapHeadline, personaPresets, provinceOffers, quantileSteps, rateForHorizon, screenCopy, sourceIsMachineReadable, tableRows } from "./view.ts"

test("OCB online headline states the sheet date, the ceiling, 6 and 12 month rates, and the renewal break-even", () => {
  const text = buildHeadline({
    lang: "vi",
    bankName: "OCB",
    channel: "online",
    sheetDate: "2026-11-06",
    shortRate: 4.75,
    shortFlat: true,
    rate6: 6,
    rate12: 6.3,
    breakEven: 6.4078,
  })

  assert.equal(
    text,
    "Trên biểu OCB online đề ngày 06/11/2026, kỳ 1–5 tháng đứng ở trần 4,75%/năm, kỳ 6 tháng là 6,00%/năm và kỳ 12 tháng là 6,30%/năm; gửi 6 tháng rồi gửi tiếp chỉ hoà hoặc hơn khoản khoá 12 tháng khi lãi suất kỳ 6 tháng lần sau từ 6,41%/năm trở lên.",
  )
})

test("Sacombank counter headline names the posted short rate when it sits under the ceiling", () => {
  const text = buildHeadline({
    lang: "vi",
    bankName: "Sacombank",
    channel: "counter",
    sheetDate: "2026-10-20",
    shortRate: 4.5,
    shortFlat: true,
    rate6: 5.7,
    rate12: 5.4,
    breakEven: 4.9587,
    ceilingPct: 4.75,
  })
  assert.equal(
    text,
    "Trên biểu Sacombank quầy đề ngày 20/10/2026, kỳ 1–5 tháng là 4,50%/năm, kỳ 6 tháng là 5,70%/năm và kỳ 12 tháng là 5,40%/năm; gửi 6 tháng rồi gửi tiếp chỉ hoà hoặc hơn khoản khoá 12 tháng khi lãi suất kỳ 6 tháng lần sau từ 4,96%/năm trở lên.",
  )
})

test("grade badges are the three reader grades, and a single reader keeps the agent_only word", () => {
  assert.equal(gradeBadge("verified", "", "vi").label, "Đã kiểm 2 nguồn")
  assert.equal(gradeBadge("single", "agent_only: single reader", "vi").label, "1 nguồn")
  assert.match(gradeBadge("single", "agent_only: single reader", "vi").detail, /agent_only/)
  assert.equal(gradeBadge("contested", "two readers disagree", "vi").label, "Mâu thuẫn")
  assert.equal(gradeBadge("verified", "", "en").label, "Checked, 2 sources")
})

test("chart drops contested rows and a bank with no sheet date", () => {
  const points = chartPoints({
    code: "OCB",
    sheet_date: "2026-11-06",
    rates: [
      { term_months: 1, channel: "counter", tier: "", rate_pct: 4.75, grade: "contested", grade_note: "disagree" },
      { term_months: 6, channel: "counter", tier: "", rate_pct: 5.9, grade: "contested", grade_note: "disagree" },
      { term_months: 6, channel: "online", tier: "", rate_pct: 6, grade: "verified", grade_note: "verified" },
      { term_months: 12, channel: "online", tier: "", rate_pct: 6.3, grade: "verified", grade_note: "verified" },
    ],
  }, "online")
  assert.deepEqual(points.map((point) => [point.term, point.rate, point.mark]), [
    [6, 6, true],
    [12, 6.3, true],
  ])
  assert.deepEqual(chartPoints({ code: "ACB", sheet_date: null, rates: points.map(() => ({ term_months: 6, channel: "online", tier: "", rate_pct: 5, grade: "single" as const, grade_note: "agent_only" })) }, "online"), [])
})

test("detail table lists verified, then one source, then contested, with both reader values when they differ", () => {
  const rows = tableRows([{
    code: "OCB",
    name_vi: "OCB",
    sheet_date: "2026-11-06",
    sheet_url: "https://ocb.com.vn/vi/cong-cu/lai-suat",
    rates: [
      { term_months: 1, channel: "counter", tier: "", rate_pct: 4.75, grade: "contested", grade_note: "disagree", readers: [{ value: 4.75 }, { value: 5.9 }] },
      { term_months: 12, channel: "online", tier: "", rate_pct: 6.3, grade: "verified", grade_note: "verified", readers: [{ value: 6.3 }] },
      { term_months: 6, channel: "online", tier: "", rate_pct: 6, grade: "single", grade_note: "agent_only: single reader", readers: [{ value: 6 }] },
    ],
  }], "vi")
  assert.deepEqual(rows.map((row) => row.gradeLabel), ["Đã kiểm 2 nguồn", "1 nguồn", "Mâu thuẫn"])
  assert.equal(rows[2]?.rateText, "4,75% · 5,90%")
  assert.equal(rows[0]?.sheetDate, "06/11/2026")
  assert.equal(rows[0]?.sourceUrl, "https://ocb.com.vn/vi/cong-cu/lai-suat")
  assert.equal(tableRows([{ code: "VTB", name_vi: "VietinBank", sheet_date: null, sheet_url: "", rates: [{ term_months: 12, channel: "counter", tier: "", rate_pct: 5.4, grade: "single", grade_note: "agent_only", readers: [{ value: 5.4 }] }] }], "vi").length, 0)
})

test("persona buttons set amount, horizon, channel and bank", () => {
  const personas = personaPresets("2026-11-20")
  assert.deepEqual(personas.map((item) => item.labelVi), [
    "1,2 tỷ · cần sau 5 tháng",
    "500 triệu · gửi tại quầy",
    "3 tỷ · nghỉ hưu",
  ])
  assert.deepEqual(personas[0], {
    id: "need-5m",
    labelVi: "1,2 tỷ · cần sau 5 tháng",
    labelEn: "1.2 billion · needed in 5 months",
    amount: 1_200_000_000,
    horizonMonths: 5,
    needDate: "2027-04-20",
    onlineOk: true,
    bankCode: "OCB",
    channel: "online",
  })
  assert.equal(personas[1]?.onlineOk, false)
  assert.equal(personas[1]?.channel, "counter")
  assert.equal(personas[1]?.bankCode, "STB")
  assert.equal(personas[1]?.amount, 500_000_000)
  assert.equal(personas[1]?.horizonMonths, 6)
  assert.equal(personas[2]?.amount, 3_000_000_000)
  assert.equal(personas[2]?.horizonMonths, 12)
  assert.equal(personas[2]?.needDate, "2027-11-20")
})

test("compare keeps at most three banks and drops the selected bank", () => {
  assert.deepEqual(clampCompare(["STB", "OCB", "MSB", "EIB", "VBB"], "OCB"), ["STB", "MSB", "EIB"])
})

test("horizon rate uses the longest verified term that matures in time, skipping contested rows", () => {
  const rates = [
    { term_months: 5, channel: "online", tier: "", rate_pct: 4.75, grade: "verified" as const, grade_note: "" },
    { term_months: 6, channel: "online", tier: "", rate_pct: 6, grade: "verified" as const, grade_note: "" },
    { term_months: 9, channel: "online", tier: "", rate_pct: 6, grade: "contested" as const, grade_note: "disagree" },
    { term_months: 12, channel: "online", tier: "", rate_pct: 6.3, grade: "single" as const, grade_note: "agent_only" },
  ]
  assert.deepEqual(rateForHorizon(rates, "online", 5), { term: 5, rate: 4.75, grade: "verified" })
  assert.deepEqual(rateForHorizon(rates, "online", 8), { term: 6, rate: 6, grade: "verified" })
  assert.deepEqual(rateForHorizon(rates, "online", 12), { term: 6, rate: 6, grade: "verified" })
})

test("key numbers are your rate, the ceiling, the best other verified rate, and a labelled break-even", () => {
  const numbers = keyNumbers({
    lang: "vi",
    ceilingPct: 4.75,
    horizonMonths: 6,
    channel: "online",
    focus: "OCB",
    breakEven: 6.4078,
    banks: [
      { code: "OCB", sheet_date: "2026-11-06", rates: [
        { term_months: 6, channel: "online", tier: "", rate_pct: 6, grade: "verified", grade_note: "" },
      ] },
      { code: "STB", sheet_date: "2026-10-20", rates: [
        { term_months: 6, channel: "online", tier: "", rate_pct: 5.4, grade: "verified", grade_note: "" },
        { term_months: 6, channel: "counter", tier: "", rate_pct: 5.7, grade: "verified", grade_note: "" },
      ] },
    ],
  })
  assert.equal(numbers.yourRate, 6)
  assert.equal(numbers.ceilingPct, 4.75)
  assert.equal(numbers.best?.code, "STB")
  assert.equal(numbers.best?.rate, 5.4)
  assert.equal(numbers.breakEven, 6.4078)
  assert.equal(numbers.breakEvenLabel, "phép tính, không phải dự báo")
})

test("a bank HTML page is not a machine-readable rate file", () => {
  assert.equal(sourceIsMachineReadable("https://ocb.com.vn/vi/cong-cu/lai-suat"), false)
  assert.equal(sourceIsMachineReadable("https://example.com/rates.csv"), true)
  assert.equal(sourceIsMachineReadable("https://example.com/rates.json?dl=1"), true)
})

test("english rates use a dot and grouped VND, vietnamese rates keep the comma and đồng sign", () => {
  assert.equal(formatPct(4.75, 2, "en"), "4.75")
  assert.equal(formatPct(4.75), "4,75")
  assert.equal(formatVnd(1234567, "en"), "1,234,567 VND")
  assert.equal(formatVnd(1234567, "vi"), "1.234.567 đ")
  const text = buildHeadline({
    lang: "en",
    bankName: "OCB",
    channel: "online",
    sheetDate: "2026-11-06",
    shortRate: 4.75,
    shortFlat: true,
    rate6: 6,
    rate12: 6.3,
    breakEven: 6.4078,
  })
  assert.match(text, /4\.75%\/year ceiling/)
  assert.match(text, /6\.00%\/year/)
  assert.match(text, /6\.30%\/year/)
  assert.match(text, /6\.41%\/year/)
  assert.doesNotMatch(text, /4,75/)
})

test("a province lists best verified counter and online rates only for banks recorded there", () => {
  const offers = provinceOffers(
    { branches_by_bank: { OCB: 2 }, best_counter_12m: null },
    [{
      code: "OCB",
      name_vi: "OCB",
      sheet_date: "2026-11-06",
      rates: [
        { term_months: 6, channel: "online", tier: "", rate_pct: 6, grade: "verified", grade_note: "" },
        { term_months: 12, channel: "online", tier: "", rate_pct: 6.3, grade: "verified", grade_note: "" },
        { term_months: 18, channel: "online", tier: "", rate_pct: 9, grade: "verified", grade_note: "" },
        { term_months: 6, channel: "counter", tier: "", rate_pct: 5.9, grade: "contested", grade_note: "disagree" },
      ],
    }],
  )
  assert.equal(offers.length, 1)
  assert.equal(offers[0]?.branches, 2)
  assert.deepEqual(offers[0]?.online, { term: 12, rate: 6.3, grade: "verified" })
  assert.equal(offers[0]?.counter, null)
  assert.deepEqual(provinceOffers({ branches_by_bank: {}, best_counter_12m: null }, []), [])
  const aliased = provinceOffers(
    { branches_by_bank: { AGB: 3 }, best_counter_12m: null },
    [{
      code: "AGRIBANK",
      name_vi: "Agribank",
      sheet_date: "2025-07-14",
      rates: [{ term_months: 12, channel: "counter", tier: "", rate_pct: 4.6, grade: "verified", grade_note: "" }],
    }],
  )
  assert.equal(aliased[0]?.code, "AGRIBANK")
  assert.deepEqual(aliased[0]?.counter, { term: 12, rate: 4.6, grade: "verified" })
})

test("the bank menu uses the legal name, and the chart title is the ceiling finding", () => {
  assert.equal(bankMenuLabel("OCB", "vi"), "OCB · Ngân hàng TMCP Phương Đông")
  assert.equal(bankMenuLabel("OCB", "en"), "OCB · Orient Commercial Joint Stock Bank")
  assert.equal(
    chartFinding({ lang: "vi", bankName: "OCB", rate6: 6, shortRate: 4.75, shortFlat: true, ceilingPct: 4.75 }),
    "OCB trả 6,00% từ kỳ 6 tháng; kỳ 1–5 tháng bị giới hạn ở 4,75%",
  )
  assert.equal(
    screenCopy({
      lang: "vi",
      bankName: "OCB",
      channel: "online",
      term: 6,
      rate: 6,
      interestVnd: 15_000_000,
      amount: 500_000_000,
      ceilingRef: "Quyết định 2411/QĐ-NHNN Điều 1",
      gapPp: 1.25,
      capRef: "Thông tư 05/2026/TT-NHNN Điều 3",
      excessVnd: 150_000_000,
    }).yourSub,
    "OCB online · 6 tháng · = 15.000.000 đ trên 500.000.000 đ",
  )
  assert.equal(
    screenCopy({
      lang: "vi", bankName: "OCB", channel: "online", term: 6, rate: 6, interestVnd: 15_000_000, amount: 500_000_000,
      ceilingRef: "Quyết định 2411/QĐ-NHNN Điều 1", gapPp: 1.25, capRef: "Thông tư 05/2026/TT-NHNN Điều 3", excessVnd: 150_000_000,
    }).ceilingSub,
    "QĐ 2411/QĐ-NHNN · kỳ 6 tháng của bạn cao hơn 1,25 điểm %",
  )
  assert.match(formatReadClock("2026-11-20T12:42:00+07:00", "vi"), /^12:42 20\/11\/2026$/)
  assert.equal(formatAmountInput(500_000_000, "vi"), "500.000.000")
  assert.equal(formatAmountInput(500_000_000, "en"), "500,000,000")
  assert.equal(parseAmountInput("500.000.000 đ"), 500_000_000)
})

test("the map headline is the busiest provinces, not the boundary line", () => {
  const text = mapHeadline({
    lang: "vi",
    provinces: [
      { name_vi: "Hồ Chí Minh", name_en: "Ho Chi Minh", branches_total: 10, branches_by_bank: { OCB: 2 } },
      { name_vi: "Hà Nội", name_en: "Ha Noi", branches_total: 4, branches_by_bank: {} },
      { name_vi: "Cần Thơ", name_en: "Can Tho", branches_total: 1, branches_by_bank: {} },
    ],
    bestBankCode: "OCB",
  })
  assert.equal(text, "Hồ Chí Minh có 10 điểm giao dịch ngân hàng trên OpenStreetMap, Hà Nội có 4; ở 2 tỉnh không có chi nhánh của ngân hàng trả lãi online cao nhất.")
  assert.equal(quantileSteps([1, 2, 3, 4, 5]).length, 5)
})

test("fixture geography copies the gold province counts and leaves deposits empty", () => {
  const here = dirname(fileURLToPath(import.meta.url))
  const snapshot = JSON.parse(readFileSync(join(here, "../../../seed/ratewatch/snapshot.fixture.json"), "utf8")) as {
    geo: { attribution: string; population_basis?: string; provinces: { pcode: string; branches_total: number | null; branches_by_bank: Record<string, number>; population: number | null; deposits_bn: number | null }[] }
    _fixture_note: { geo?: string }
  }
  const gold = JSON.parse(readFileSync(join(here, "../../../../data/lake/ratewatch/gold/geo_provinces.json"), "utf8")) as {
    provinces: { pcode: string; branches_total: number; branches_by_bank: Record<string, number>; population: number | null }[]
  }
  const byCode = new Map(gold.provinces.map((item) => [item.pcode, item]))
  assert.equal(snapshot.geo.provinces.length, 34)
  for (const province of snapshot.geo.provinces) {
    const source = byCode.get(province.pcode)
    assert.equal(province.branches_total, source?.branches_total)
    assert.deepEqual(province.branches_by_bank, source?.branches_by_bank)
    assert.equal(province.population, source?.population)
    assert.equal(province.deposits_bn, null)
  }
  assert.equal(snapshot.geo.provinces.find((item) => item.pcode === "VN79")?.branches_total, 795)
  assert.match(snapshot.geo.attribution, /© OpenStreetMap contributors \(ODbL\)/)
  assert.match(snapshot._fixture_note.geo ?? "", /geo_provinces\.json/)
  assert.match(snapshot.geo.population_basis ?? "", /202\/2025\/QH15/)
})

test("the 1–5 month band is flat only when every usable short term prints the same rate", () => {
  const rates = [1, 2, 3, 4, 5].map((term) => ({
    term_months: term, channel: "online", tier: "", rate_pct: 4.75, grade: "verified" as const, grade_note: "",
  })).concat([
    { term_months: 6, channel: "online", tier: "", rate_pct: 6, grade: "verified" as const, grade_note: "" },
    { term_months: 12, channel: "online", tier: "", rate_pct: 6.3, grade: "verified" as const, grade_note: "" },
    { term_months: 6, channel: "counter", tier: "", rate_pct: 5.9, grade: "contested" as const, grade_note: "disagree" },
  ])
  assert.deepEqual(bandRates(rates, "online"), { shortRate: 4.75, shortFlat: true, rate6: 6, rate12: 6.3 })
  assert.deepEqual(bandRates(rates, "counter"), { shortRate: null, shortFlat: false, rate6: null, rate12: null })
})
