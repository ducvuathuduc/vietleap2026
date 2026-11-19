import assert from "node:assert/strict"
import { test } from "node:test"

import {
  LAB_NAV,
  NAV,
  filterCommands,
  filterLabCommands,
  hrefForIndicatorSector,
  legacyRedirects,
  sectorBySlug,
  titleForPath,
  whatIfLink,
} from "./nav.ts"

test("judge navigation is the six public pages", () => {
  assert.deepEqual(
    NAV.map((page) => [page.title, page.url]),
    [
      ["Tổng quan", "/"],
      ["Chỉ số & ASEAN", "/asean"],
      ["Ngành", "/nganh/tai-chinh-cong"],
      ["Tỉnh thành", "/tinh"],
      ["Phân tích & Khuyến nghị", "/khuyen-nghi"],
      ["Dữ liệu & Phương pháp", "/phuong-phap"],
    ],
  )
})

test("Ngành lists the five public sector slugs", () => {
  const nganh = NAV.find((page) => page.title === "Ngành")
  assert.deepEqual(
    nganh?.children?.map((item) => [item.title, item.url, item.id]),
    [
      ["Tài chính công", "/nganh/tai-chinh-cong", "public_finance"],
      ["FDI", "/nganh/fdi", "fdi"],
      ["Ngân hàng", "/nganh/ngan-hang", "banking"],
      ["Thị trường vốn", "/nganh/thi-truong-von", "capital_market"],
      ["Bất động sản", "/nganh/bat-dong-san", "real_estate"],
    ],
  )
})

test("unknown sector slug is rejected", () => {
  assert.equal(sectorBySlug("ngan_hang"), null)
  assert.equal(sectorBySlug("khong-co"), null)
  assert.equal(sectorBySlug("ngan-hang")?.id, "banking")
  assert.equal(sectorBySlug("tai-chinh-cong")?.id, "public_finance")
})

test("judge command search stays on public pages", () => {
  assert.equal(filterCommands("thi truong von")[0]?.url, "/nganh/thi-truong-von")
  assert.equal(filterCommands("khuyen nghi")[0]?.url, "/khuyen-nghi")
  const urls = filterCommands("").map((item) => item.url)
  assert.ok(urls.length >= NAV.length)
  assert.ok(urls.every((url) => !url.startsWith("/lab") && url !== "/sql" && url !== "/analyst"))
})

test("header title follows the longest public match", () => {
  assert.equal(titleForPath("/"), "Tổng quan")
  assert.equal(titleForPath("/nganh/bat-dong-san"), "Bất động sản")
  assert.equal(titleForPath("/nganh/tai-chinh-cong"), "Tài chính công")
  assert.equal(titleForPath("/tinh/HN"), "Tỉnh thành")
  assert.equal(titleForPath("/lab/sql"), "VietLeap Insight")
})

test("lab commands keep internal pages under /lab", () => {
  assert.equal(filterLabCommands("chat luong")[0]?.url, "/lab/quality")
  assert.equal(filterLabCommands("what-if")[0]?.url, "/lab/drivers")
  assert.ok(LAB_NAV.every((page) => page.url === "/lab" || page.url.startsWith("/lab/")))
  assert.equal(titleForPath("/lab/quality", LAB_NAV), "Chất lượng dữ liệu")
})

test("indicator names route to the public page for that sector", () => {
  assert.equal(hrefForIndicatorSector("banking"), "/nganh/ngan-hang")
  assert.equal(hrefForIndicatorSector("public_finance"), "/nganh/tai-chinh-cong")
  assert.equal(hrefForIndicatorSector("province"), "/tinh")
  assert.equal(hrefForIndicatorSector("asean"), "/asean")
  assert.equal(hrefForIndicatorSector("macro"), "/asean")
  assert.equal(hrefForIndicatorSector("khac"), "/")
})

test("legacy tool urls enter the lab only when the lab is enabled", () => {
  assert.equal(legacyRedirects(true).find((item) => item.source === "/sql")?.destination, "/lab/sql")
  assert.equal(legacyRedirects(true).find((item) => item.source === "/whatif")?.destination, "/lab/whatif")
  assert.equal(legacyRedirects(false).find((item) => item.source === "/analyst")?.destination, "/")
  assert.equal(legacyRedirects(false).some((item) => item.destination.includes("/lab")), false)
  assert.equal(legacyRedirects(true).every((item) => item.permanent), true)
})

test("what-if shortcut stays on the lab drivers page and bounds the percentage", () => {
  assert.equal(whatIfLink("what-if GDP/người +50%"), "/lab/drivers?feature=GDP%2Fng%C6%B0%E1%BB%9Di&pct=30")
  assert.equal(whatIfLink("what-if GDP/người -80%"), "/lab/drivers?feature=GDP%2Fng%C6%B0%E1%BB%9Di&pct=-30")
  assert.equal(whatIfLink("what-if"), null)
})
