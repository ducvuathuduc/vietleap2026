// Run: npm test
import assert from "node:assert/strict"
import { test } from "node:test"

import {
  createScenarioRequester,
  defaultTopDrivers,
  formatUnitMode,
  hasZeroCrossing,
  isZeroVector,
  loadLocalScenarios,
  removeLocalScenario,
  saveLocalScenario,
  scenariosKey,
} from "./whatif.ts"

test("defaultTopDrivers orders whatif_features by permutation importance and caps at 5", () => {
  const drivers = {
    target: "price_per_m2",
    drivers: {
      n: 100,
      features: ["a", "b", "c", "d", "e", "f", "g"],
      leakage_excluded: [],
      log_target: false,
      cv_r2: { ridge_mean: 0.6, ridge_std: 0.05, gb_mean: 0.7, gb_std: 0.04 },
      importance: [
        { feature: "d", importance: 0.4, std: 0.01 },
        { feature: "b", importance: 0.3, std: 0.01 },
        { feature: "f", importance: 0.2, std: 0.01 },
        { feature: "a", importance: 0.15, std: 0.01 },
        { feature: "e", importance: 0.1, std: 0.01 },
        { feature: "c", importance: 0.05, std: 0.01 },
      ],
      coefficients: [],
      note: "",
    },
    whatif_features: [
      { name: "a", mean: 10, sd: 2, median: 10 },
      { name: "b", mean: 20, sd: 3, median: 20 },
      { name: "c", mean: 30, sd: 4, median: 30 },
      { name: "d", mean: 40, sd: 5, median: 40 },
      { name: "e", mean: 50, sd: 6, median: 50 },
      { name: "f", mean: 60, sd: 7, median: 60 },
      { name: "g", mean: 70, sd: 8, median: 70 },
    ],
  }
  assert.deepEqual(
    defaultTopDrivers(drivers).map((x) => x.name),
    ["d", "b", "f", "a", "e"]
  )
})

test("hasZeroCrossing and isZeroVector behave deterministically", () => {
  assert.equal(isZeroVector([]), true)
  assert.equal(isZeroVector([{ feature: "a", pct_change: 0 }, { feature: "b", pct_change: 0 }]), true)
  assert.equal(isZeroVector([{ feature: "a", pct_change: 0 }, { feature: "b", pct_change: 5 }]), false)

  assert.equal(hasZeroCrossing([-2.1, 4.3]), true)
  assert.equal(hasZeroCrossing([4.3, -2.1]), true)
  assert.equal(hasZeroCrossing([1.2, 5.4]), false)
  assert.equal(hasZeroCrossing([-5.4, -1.2]), false)
  assert.equal(hasZeroCrossing([0, 0]), false)
  assert.equal(hasZeroCrossing([null, 2]), false)
})

test("formatUnitMode detects zero-sd, negative/near-zero mean, and normal features", () => {
  assert.equal(formatUnitMode({ name: "const", mean: 5, sd: 0 }).disabled, true)
  assert.equal(formatUnitMode({ name: "net_lending", mean: -2.4, sd: 3.1 }).mode, "sd_step")
  assert.equal(formatUnitMode({ name: "near_zero", mean: 0.05, sd: 2.0 }).mode, "sd_step")
  assert.equal(formatUnitMode({ name: "gdp", mean: 4200, sd: 1500 }).mode, "pct_mean")
})

test("localStorage helpers store max 4 scenarios per dataset and recover from corrupt JSON", () => {
  const mem = new Map<string, string>()
  const storage = {
    getItem: (k: string) => mem.get(k) ?? null,
    setItem: (k: string, v: string) => { mem.set(k, v) },
  }
  mem.set(scenariosKey("bds"), "{broken json")
  assert.deepEqual(loadLocalScenarios("bds", storage), [])

  const mk = (name: string) => ({
    name,
    request: { changes: [{ feature: "a", pct_change: 10 }] },
    result: {
      changes: [{ feature: "a", pct_change: 10 }],
      target: "price",
      target_change_pct: 5,
      ci90_pct: [2, 8] as [number, number],
      target_change_abs: 1,
      baseline_target_mean: 20,
      range_warnings: [],
      interpretation: "",
    },
  })
  saveLocalScenario("bds", mk("s1"), storage)
  saveLocalScenario("bds", mk("s2"), storage)
  saveLocalScenario("bds", mk("s3"), storage)
  saveLocalScenario("bds", mk("s4"), storage)
  const capped = saveLocalScenario("bds", mk("s5"), storage)
  assert.equal(capped.length, 4)
  assert.equal(capped[0].name, "s5")
  const afterRemove = removeLocalScenario("bds", "s4", storage)
  assert.equal(afterRemove.length, 3)
  assert.ok(!afterRemove.some((x) => x.name === "s4"))
})

test("createScenarioRequester debounces rapid moves, aborts prior request, and respects throttle", async () => {
  const calls: { changes: { feature: string; pct_change: number }[]; aborted: boolean }[] = []
  let resolveLast: ((v: string) => void) | null = null

  const requester = createScenarioRequester(
    (changes, signal) => {
      const rec = { changes, aborted: false }
      calls.push(rec)
      signal.addEventListener("abort", () => { rec.aborted = true })
      return new Promise<string>((resolve, reject) => {
        resolveLast = resolve
        signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")))
      })
    },
    { debounceMs: 25, minIntervalMs: 60 }
  )

  // Burst of 3 calls inside debounce window → only the 3rd triggers
  void requester.trigger([{ feature: "a", pct_change: 5 }]).catch(() => undefined)
  void requester.trigger([{ feature: "a", pct_change: 10 }]).catch(() => undefined)
  const p1 = requester.trigger([{ feature: "a", pct_change: 15 }])

  await new Promise((r) => setTimeout(r, 40))
  assert.equal(calls.length, 1)
  assert.equal(calls[0].changes[0].pct_change, 15)

  // Trigger a second wave while first is still in flight → aborts first request
  const p2 = requester.trigger([{ feature: "a", pct_change: 20 }])
  await new Promise((r) => setTimeout(r, 80))
  assert.equal(calls.length, 2)
  assert.equal(calls[0].aborted, true)
  assert.equal(calls[1].changes[0].pct_change, 20)

  resolveLast?.("done")
  const [res1, res2] = await Promise.all([p1, p2])
  assert.equal(res1, null)
  assert.equal(res2, "done")
  requester.cancel()
})
