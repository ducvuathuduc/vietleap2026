"""HTTP hardening for the FastAPI app: security headers, request-size cap and a per-client rate limit.

Pure-ASGI/Starlette middleware, no extra dependency. Limits are per client IP, in memory (single-process local tool).
Env: RATE_LIMIT_PER_MIN (default 60 for expensive routes, 0 disables), MAX_BODY_MB (default 200).
"""
from __future__ import annotations

import os
import re
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    # JSON API: nothing may execute or be framed; /docs (Swagger UI from jsdelivr) gets a relaxed policy below
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
}
DOCS_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'; base-uri 'self'")

# expensive or state-changing routes (method, regex)
LIMITED = [("POST", re.compile(r"^/api/sql$")), ("POST", re.compile(r"^/api/ingest$")),
           ("POST", re.compile(r"^/api/datasets$")), ("POST", re.compile(r"^/api/datasets/[^/]+/agent$")),
           ("POST", re.compile(r"^/api/brief$")), ("POST", re.compile(r"^/api/datasets/[^/]+/(?:whatif|export)$"))]


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, per_min: int | None = None, max_body_mb: int | None = None):
        super().__init__(app)
        self.per_min = _int_env("RATE_LIMIT_PER_MIN", 60) if per_min is None else per_min
        self.max_body = (_int_env("MAX_BODY_MB", 200) if max_body_mb is None else max_body_mb) * 1024 * 1024
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def _limited(self, request: Request) -> bool:
        if self.per_min <= 0:
            return False
        if not any(request.method == m and rx.match(request.url.path) for m, rx in LIMITED):
            return False
        key = f"{request.client.host if request.client else '?'}"
        now = time.monotonic()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_min:
                return True
            q.append(now)
        return False

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > self.max_body:
            return self._secure(JSONResponse({"detail": f"request body larger than {self.max_body // 2**20} MB"}, 413), request)
        if self._limited(request):
            r = JSONResponse({"detail": "too many requests — slow down (rate limit)"}, 429, headers={"Retry-After": "60"})
            return self._secure(r, request)
        return self._secure(await call_next(request), request)

    @staticmethod
    def _secure(response, request: Request):
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if request.url.path in ("/docs", "/redoc") or request.url.path.startswith("/docs/"):
            response.headers["Content-Security-Policy"] = DOCS_CSP
        return response
