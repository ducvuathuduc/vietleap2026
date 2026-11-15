# Security policy

## Supported versions
Only `main` is maintained (contest tool, VietLeap Hackathon 2026).

## Reporting a vulnerability
Open a private security advisory on GitHub (Security → Advisories → Report a vulnerability) or contact the maintainer
(GitHub `@thanhdicode`). Please do not open a public issue for an unpatched vulnerability. Expect an answer within 72 hours
during the contest window (15–21/11/2026).

## Security model in one paragraph
The kit is a **local, single-team tool**: FastAPI binds to `127.0.0.1`, there is no login. Everything a browser, an uploaded file,
a scraped page or an LLM can send is treated as untrusted: SQL is read-only, connectors refuse private-network targets and local
paths outside allowed directories when called through the API, uploads are size/type-limited, AI tools are read-only and their
output is data (not instructions), secrets come only from environment variables / `.env*` files that are never committed.
Full STRIDE analysis and per-control status: [`docs/security/threat-model.md`](docs/security/threat-model.md).

## Controls (status verified against code; ✅ done · ⚠ partial · ❌ gap)
| Control | Status | Where |
|---|---|---|
| Read-only SQL: single statement, allowlist, DDL/DML denylist, row limit | ✅ | `engine/vlkit/de/warehouse.py Warehouse.sql`, `api/routes/pipeline.py SqlIn` |
| SQL cannot read local files (external access off + file/env function denylist), 20 s statement timeout | ✅ | `Warehouse.readonly()`, `Warehouse.sql`, `tests/test_security.py` |
| SSRF: block private/loopback/link-local/metadata IPs for API-submitted URLs, incl. redirects and DNS answers; `auth_env` limited to `KIT_TOKEN_*`; `render_js` refused via API | ✅ | `engine/vlkit/de/netguard.py`, connectors httpx event hooks, `tests/test_security.py` |
| Local path allowlist (symlinks resolved) for API-submitted file/cv/sqlite sources; network DB hosts checked; cv option allowlist; zip-bomb limit 2 GB | ✅ | `netguard.check_path`, `connectors.ingest_file` |
| Upload limits (type allowlist, 200 MB streamed in 1 MB chunks, empty-file reject, request-body cap) | ✅ | `api/routes/datasets.py`, `api/security.py` |
| Path traversal (ids, filenames, export kinds, chart names) | ✅ | `api/store.py`, `api/routes/datasets.py` |
| CORS origin allowlist (no `*`), methods GET/POST, headers Content-Type/Accept, no credentials | ✅ | `api/main.py`, `CORS_ORIGINS` |
| Security headers (CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, COOP; no X-Powered-By) | ✅ | `api/security.py`, `web/next.config.ts` |
| Rate limiting: 60/min/IP on SQL, ingest, upload, agent, brief, what-if; 20/min on `/api/chat`, `/api/story` | ✅ | `api/security.py` (`RATE_LIMIT_PER_MIN`), `web/src/lib/rate-limit.ts` (`CHAT_RATE_LIMIT_PER_MIN`) |
| Prompt-injection: read-only tools, number verification, "tool output is data" rule | ✅ | `web/src/lib/analyst/*`, `api/agent/verify.py` |
| Secrets via env only; `.env*` ignored (root + web); gitleaks in CI | ⚠ CI part → T067 | `.gitignore`, `web/.gitignore` |
| Dependency audit (pip-audit, npm audit) | ❌ → T067 | CI |
| Run log, lineage, provenance (audit trail) | ✅ | `meta.runs`, `meta.lineage`, `provenance.json` |
| Licence compliance | ✅ | `docs/licenses.md` |

## Operating guidance
- Keep `make api` bound to `127.0.0.1`; if you must share the dashboard on a LAN, expose only the Next.js port and set `CORS_ORIGINS`.
- Put LLM keys only in `web/.env.local` (git-ignored); prefer offline mode for datasets with personal data.
- Remove direct identifiers before ingesting; `make clean-out` after the contest.
