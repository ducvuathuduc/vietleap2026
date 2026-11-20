import assert from "node:assert/strict"
import { registerHooks } from "node:module"
import { test } from "node:test"
import { NextRequest } from "next/server.js"

const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    return nextResolve(specifier === "next/server" ? "next/server.js" : specifier, context)
  },
})
const { proxy } = await import("./proxy.ts").finally(() => hooks.deregister())

function checkRoutes(paths: string[], status: number) {
  for (const path of paths) {
    const response = proxy(new NextRequest(`http://localhost${path}`))
    assert.equal(response.status, status, path)
  }
}

const legacy = ["/lab/analyst", "/print?dataset=demo", "/ban-do", "/chinh-sach", "/lai-suat/ngan-hang/TCB", "/tai-lieu/lai-suat", "/api/chat", "/api/datasets/demo", "/api/warehouse/tables"]

test("production hides legacy pages and APIs by default and leaves NPL and health reachable", () => {
  const original = process.env
  process.env = { ...original, NODE_ENV: "production", ENABLE_LAB: "0" }
  try {
    checkRoutes(legacy, 404)
    checkRoutes(["/api/retired", "/api/retired/chat", "/api/npl/missing"], 404)
    checkRoutes(["/", "/giai-ma", "/du-lieu/csv", "/api/health", "/api/npl/chat"], 200)
  } finally {
    process.env = original
  }
})

test("legacy routes remain available with ENABLE_LAB=1 or outside production", () => {
  const original = process.env
  try {
    process.env = { ...original, NODE_ENV: "production", ENABLE_LAB: "1" }
    checkRoutes(legacy, 200)
    process.env = { ...original, NODE_ENV: "development", ENABLE_LAB: "0" }
    checkRoutes(legacy, 200)
  } finally {
    process.env = original
  }
})
