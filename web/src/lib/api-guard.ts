// Hosted-build gate. Judge pages read monitor.json on the server and call none of these.
// ENABLE_LAB must be "1" for sql, ingest, sources, warehouse, jobs, export, dataset upload,
// brief POST, and story. Chat is separate: ENABLE_CHAT=1. /api/health and dataset reads stay open.

const LAB_ROOTS = ["/api/sql", "/api/ingest", "/api/sources", "/api/warehouse", "/api/jobs", "/api/export", "/api/story"]

function under(path: string, root: string): boolean {
  return path === root || path.startsWith(`${root}/`)
}

function allow(flag: "ENABLE_LAB" | "ENABLE_CHAT"): Response | null {
  if (process.env[flag] === "1") return null
  return Response.json({ detail: "Not found" }, { status: 404 })
}

/** 404 when this request is an internal tool whose flag is not exactly "1"; otherwise null. */
export function guardApi(req: Request): Response | null {
  const path = new URL(req.url).pathname.replace(/\/+$/, "") || "/"
  const method = req.method.toUpperCase()

  if (under(path, "/api/chat")) return allow("ENABLE_CHAT")
  if (LAB_ROOTS.some((root) => under(path, root))) return allow("ENABLE_LAB")
  if (path === "/api/datasets" && method === "POST") return allow("ENABLE_LAB")
  if (path === "/api/brief" && method === "POST") return allow("ENABLE_LAB")
  if (method === "POST" && /^\/api\/datasets\/[^/]+\/export$/.test(path)) return allow("ENABLE_LAB")
  return null
}
