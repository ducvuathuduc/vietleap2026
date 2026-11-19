import assert from "node:assert/strict"
import path from "node:path"
import { test } from "node:test"

import fixture from "../../../lib/monitor/__fixtures__/synthetic.monitor.json" with { type: "json" }
import type { Monitor } from "../../../lib/monitor/types.ts"
import { askPage, methodPage, publishedFile, resolvePublishedFile } from "./method-view.ts"

const monitor = fixture as Monitor

function published(): Monitor {
  const next = structuredClone(monitor) as Monitor
  next.files = {
    dictionary_md: "data_dictionary.md",
    dictionary_csv: "data_dictionary.csv",
    eda: "eda.md",
    erd: "erd.mmd",
    monitor: "monitor.json",
    v_fdi: "csv/v_fdi.csv",
  }
  next.model = {
    erd_mermaid: "erDiagram\n  GOLD_FACT {\n    VARCHAR id PK\n  }",
    tables: [
      { name: "bronze.vm_nso", layer: "bronze", rows: 12, grain_vi: "Chỉ tiêu và tháng" },
      { name: "gold.fact_indicator", layer: "gold", rows: 1200, grain_vi: "Một quan sát theo chỉ tiêu và kỳ" },
    ],
  }
  next.quality = [
    {
      source_id: "nso",
      rows: 9,
      score_before: 80,
      score_after: 95.5,
      flags: { outlier: 2, missing: 1, not_a_known_flag: 4 },
    },
  ]
  next.reconciliation = [
    {
      indicator_id: "credit_ytd",
      period: "2026-10",
      values: { nso: 12.5, secret_source: 13 },
      diff_pct: 1.25,
      tolerance_pct: 1,
      verdict: "mismatch",
      note_vi: "Lệch giữa hai công bố.",
    },
  ]
  next.sources[0].robots = "Robot được phép."
  next.sources[0].next_release = "2026-12-01"
  return next
}

test("method page headline counts sources and indicators and dates the latest update", () => {
  const page = methodPage(published())
  assert.equal(page.level, "detail")
  assert.equal(page.headline, "1 nguồn, 1 chỉ số, cập nhật gần nhất 19/11/2026")
})

test("method page names the collection method in Vietnamese and links the six mentor steps", () => {
  const page = methodPage(published())
  assert.equal(page.sources[0]?.method, "Thu thập trang")
  assert.equal(page.sources[0]?.publisher, "NSO")
  assert.equal(page.sources[0]?.robots, "Robot được phép.")
  assert.equal(page.sources[0]?.fetched, "14:05 19/11/2026")
  assert.equal(page.sources[0]?.cutoff, "10/2026")
  assert.equal(page.sources[0]?.nextRelease, "01/12/2026")
  assert.deepEqual(
    page.steps.map((step) => step.title),
    ["Chọn domain", "Thu thập", "EDA", "Làm sạch & mô hình", "Dashboard", "Quyết định"],
  )
  assert.equal(page.steps[0]?.href, "/phuong-phap/tep/dictionary_md")
  assert.equal(page.steps[2]?.href, "/phuong-phap/tep/eda")
  assert.equal(page.steps[3]?.href, "/phuong-phap/tep/erd")
  assert.equal(page.steps[5]?.href, "/phuong-phap/tep/monitor")
})

test("method page keeps technical table names off the description and translates quality flags", () => {
  const page = methodPage(published())
  assert.equal(page.tables.length, 1)
  assert.equal(page.tables[0]?.description, "Một quan sát theo chỉ tiêu và kỳ")
  assert.equal(page.tables[0]?.technicalName, "gold.fact_indicator")
  assert.equal(page.tables[0]?.rows, "1.200")
  assert.equal(page.erdHref, "/phuong-phap/tep/erd")
  assert.equal(page.quality[0]?.before, "80")
  assert.equal(page.quality[0]?.after, "95,5")
  assert.equal(page.quality[0]?.flags, "Giá trị ngoại lai: 2; Thiếu: 1; Cờ khác: 4")
  assert.equal(page.quality[0]?.flags.includes("outlier"), false)
  assert.equal(page.reconciliation[0]?.name, "Tăng tín dụng")
  assert.equal(page.reconciliation[0]?.verdict, "Lệch")
  assert.equal(page.reconciliation[0]?.values, "NSO: 12,5")
  assert.equal(page.reconciliation[0]?.diff, "1,25%")
  assert.equal(page.glossary.some((term) => term.term === "yoy"), true)
  assert.equal(page.glossary.some((term) => term.term === "lũy kế"), true)
  assert.equal(page.downloads.some((item) => item.href === "/phuong-phap/tep/v_fdi" && item.label === "Vốn đầu tư nước ngoài"), true)
})

test("method page hides internal codes in sources, reconciliation and model tables", () => {
  const next = published()
  next.sources.push({
    id: "bcp_mof_dtc_2026_10",
    publisher: "BCP_MOF_DTC_2026_10",
    title_vi: "Báo cáo ngành và công bố chuyên đề",
    url: "https://bcp.cdnchinhphu.vn/report",
    method: "file",
    license: "Nguồn công bố",
    fetched_at: "2026-11-19T07:05:00.000Z",
    data_cutoff: "2026-10",
  })
  next.province.rows.push({
    code: "ha_noi",
    name: "Hà Nội",
    region: "Thử",
    metrics: { credit_ytd: null },
    group: null,
  })
  next.reconciliation.push({
    indicator_id: "dtc_province_disbursed",
    period: "2026-10",
    values: { bcp_mof_dtc_2026_10: 60.99 },
    diff_pct: 0,
    tolerance_pct: 1,
    verdict: "single_source",
    note_vi: "ha_noi · pct_plan · %",
  })
  next.reconciliation.push({
    indicator_id: "dtc_disbursed",
    period: "2026-10",
    values: { bcp_mof_dtc_2026_10: 708.5 },
    diff_pct: 0,
    tolerance_pct: 1,
    verdict: "single_source",
    note_vi: "Toàn quốc · level · ty_vnd",
  })
  const page = methodPage(next)
  const visible = JSON.stringify({
    sources: page.sources,
    reconciliation: page.reconciliation,
    tables: page.tables.map((table) => ({ description: table.description, detail: table.detail })),
    quality: page.quality,
  })
  assert.equal(page.sources.some((source) => source.publisher.includes("bcp.cdnchinhphu.vn")), true)
  assert.equal(page.reconciliation.some((row) => row.name.includes("Hà Nội") && row.values.includes("60,99%")), true)
  assert.equal(page.reconciliation.some((row) => row.values.includes("tỷ đồng")), true)
  assert.equal(page.tables[0]?.detail ?? null, null)
  assert.equal(/\b[a-z][a-z0-9]*_[a-z0-9_]+\b/.test(visible), false)
  assert.equal(visible.includes("BCP_MOF"), false)
  assert.equal(visible.includes("pct_plan"), false)
  assert.equal(visible.includes("ty_vnd"), false)
})

test("method page omits a mentor link when the artefact file is absent", () => {
  const next = published()
  delete next.files?.eda
  const page = methodPage(next)
  assert.equal(page.steps[2]?.href, null)
})

test("ask page suggests four questions from indicator names and hides the input when chat is off", () => {
  const off = askPage(published(), false)
  assert.equal(off.label, "Hỏi đáp về số liệu")
  assert.equal(off.input, false)
  assert.equal(off.note, "Hỏi đáp về số liệu đang tắt. Trang này không nhận câu hỏi.")
  assert.equal(off.questions.length, 4)
  assert.equal(off.questions.every((question) => question.includes("Tăng tín dụng")), true)

  const on = askPage(published(), true)
  assert.equal(on.input, false)
  assert.match(on.note, /chưa đọc/)
})

test("published file resolver stays inside the monitor directory", () => {
  const root = path.resolve("C:\\data\\vn_monitor")
  assert.equal(resolvePublishedFile(root, "csv/v_fdi.csv"), path.resolve(root, "csv/v_fdi.csv"))
  assert.equal(resolvePublishedFile(root, "../secrets.env"), null)
  assert.equal(resolvePublishedFile(root, "..\\secrets.env"), null)
  assert.equal(resolvePublishedFile(root, "..\\..\\x"), null)
  assert.equal(resolvePublishedFile(root, "/etc/passwd"), null)
  assert.equal(resolvePublishedFile(root, "csv\\v_fdi.csv"), null)
  assert.equal(resolvePublishedFile(root, "C:csv/v_fdi.csv"), null)
  assert.equal(resolvePublishedFile(root, ""), null)
})

test("published downloads allow only a listed file inside the monitor directory", () => {
  const root = path.resolve("C:\\data\\vn_monitor")
  const inherited = Object.create({ inherited: "secret.txt" }) as Record<string, string>
  inherited.eda = "eda.md"
  inherited.secret = "../secrets.env"
  inherited.abs = "C:\\Windows\\system.ini"
  assert.equal(publishedFile(inherited, "eda", root), path.resolve(root, "eda.md"))
  assert.equal(publishedFile(inherited, "secret", root), null)
  assert.equal(publishedFile(inherited, "abs", root), null)
  assert.equal(publishedFile(inherited, "inherited", root), null)
  assert.equal(publishedFile(inherited, "../eda", root), null)
  assert.equal(publishedFile(inherited, "missing", root), null)
  assert.equal(publishedFile(undefined, "eda", root), null)
})
