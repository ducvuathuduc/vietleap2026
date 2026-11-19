import assert from "node:assert/strict"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { describe, test } from "node:test"
import { fileURLToPath } from "node:url"

import { MonitorSchemaError, defaultMonitorPaths, loadMonitor, loadPublishedMonitor, resolveMonitorPaths } from "./load.ts"

const fixturePath = fileURLToPath(new URL("./__fixtures__/synthetic.monitor.json", import.meta.url))

describe("monitor file", { concurrency: false }, () => {
  test("missing primary and seed return null", () => {
    const missing = path.join(os.tmpdir(), "vietleap-monitor-missing.json")
    assert.equal(loadMonitor({ primary: missing, seed: path.join(os.tmpdir(), "vietleap-monitor-seed-missing.json") }), null)
  })

  test("wrong schema_version throws and does not fall back to the seed", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vietleap-monitor-"))
    const primary = path.join(dir, "bad.json")
    fs.writeFileSync(primary, JSON.stringify({ schema_version: 2, meta: {} }))
    assert.throws(() => loadMonitor({ primary, seed: fixturePath }), MonitorSchemaError)
  })

  test("a missing primary falls back to the seed fixture", () => {
    const missing = path.join(os.tmpdir(), "vietleap-monitor-no-primary.json")
    const loaded = loadMonitor({ primary: missing, seed: fixturePath })
    assert.equal(loaded?.schema_version, 1)
    assert.equal(loaded?.meta.title_vi, "Tiêu đề tổng quan")
  })

  test("the same file is cached until its mtime changes", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vietleap-monitor-cache-"))
    const primary = path.join(dir, "monitor.json")
    const seed = path.join(dir, "missing.json")
    fs.copyFileSync(fixturePath, primary)
    const first = loadMonitor({ primary, seed })
    const second = loadMonitor({ primary, seed })
    assert.equal(first, second)
    const next = JSON.parse(fs.readFileSync(primary, "utf8")) as { meta: { title_vi: string } }
    next.meta.title_vi = "Bản mới"
    fs.writeFileSync(primary, JSON.stringify(next))
    const later = new Date(Date.now() + 5000)
    fs.utimesSync(primary, later, later)
    const third = loadMonitor({ primary, seed })
    assert.notEqual(third, first)
    assert.equal(third?.meta.title_vi, "Bản mới")
  })

  test("default paths point at the repo output and the web seed", () => {
    const paths = defaultMonitorPaths()
    assert.match(paths.primary, /[\\/]out[\\/]vn_monitor[\\/]monitor\.json$/)
    assert.match(paths.seed, /[\\/]seed[\\/]vn_monitor[\\/]monitor\.json$/)
    assert.equal(resolveMonitorPaths({ MONITOR_PATH: "D:\\custom\\monitor.json" }).primary, "D:\\custom\\monitor.json")
    assert.equal(resolveMonitorPaths({}).primary, paths.primary)
  })

  test("the published loader reads the payload and returns null when nothing is published", async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vietleap-monitor-published-"))
    const previousPath = process.env.MONITOR_PATH
    const previousCwd = process.cwd()
    // A temp cwd also moves the seed fallback, so "nothing published" really means nothing.
    process.chdir(dir)
    process.env.MONITOR_PATH = path.join(dir, "monitor.json")
    try {
      assert.equal(await loadPublishedMonitor(), null)
      fs.copyFileSync(fixturePath, process.env.MONITOR_PATH)
      assert.equal((await loadPublishedMonitor())?.meta.title_vi, "Tiêu đề tổng quan")
    } finally {
      process.chdir(previousCwd)
      if (previousPath === undefined) delete process.env.MONITOR_PATH
      else process.env.MONITOR_PATH = previousPath
    }
  })
})
