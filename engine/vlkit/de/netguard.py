"""Guards for sources submitted through the HTTP API (untrusted callers) — SSRF, local-path and option abuse.

The CLI (`de.py`) is run by the analyst on their own machine and is NOT guarded: a sources.yaml may legitimately
point at a LAN database or a local file anywhere. The API (`POST /api/ingest`) calls :func:`guard_source` first and
marks the source (`options["_net_guard"] = True`) so connectors re-check every request, including redirects.

Controls
  * URLs: http/https only, no credentials in the URL, hostname must resolve only to public unicast addresses
    (blocks localhost, RFC1918, CGNAT, link-local incl. cloud metadata 169.254.169.254, multicast, reserved, IPv6
    ULA/loopback); re-checked on every request/redirect via an httpx event hook.
  * Local paths (file, cv, sqlite): must resolve (symlinks followed) inside the allowed roots — data/, scenarios/,
    the upload dir and the out dir.
  * SQL URLs: sqlite → path rule; network DBs → host rule.
  * Options: ``auth_env`` may only name variables starting with ``KIT_TOKEN_`` (otherwise any secret in the API's
    environment, e.g. an LLM key, could be sent as a Bearer token to an attacker URL); cv options limited to the
    counting knobs (no --out/--video overrides); ``render_js`` refused (headless browser redirects cannot be checked).
Set ``KIT_ALLOW_PRIVATE_NET=1`` to allow private hosts for a trusted LAN demo.
"""
from __future__ import annotations

import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

from .warehouse import KIT

AUTH_ENV_PREFIX = "KIT_TOKEN_"
CV_OPTION_KEYS = {"every", "stride", "line", "classes", "start", "conf", "model"}
NET_KINDS = {"api", "scrape", "social", "tinyfish"}
PATH_KINDS = {"file", "cv"}


class SourceRejected(ValueError):
    pass


def _private_allowed() -> bool:
    return os.environ.get("KIT_ALLOW_PRIVATE_NET", "0") == "1"


def allowed_roots() -> list[Path]:
    roots = [KIT / "data", KIT / "scenarios", Path(os.environ.get("KIT_UPLOAD_DIR", KIT / "data" / "uploads")),
             Path(os.environ.get("KIT_OUT_DIR", KIT / "out"))]
    extra = os.environ.get("KIT_ALLOWED_DIRS", "")
    roots += [Path(p) for p in extra.split(os.pathsep) if p.strip()]
    return [r.resolve() for r in roots]


def is_public_ip(ip: str) -> bool:
    a = ipaddress.ip_address(ip)
    if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped:
        a = a.ipv4_mapped
    return a.is_global and not (a.is_multicast or a.is_reserved or a.is_loopback or a.is_link_local or a.is_private)


def check_host(host: str | None, port: int | None = None) -> None:
    if not host:
        raise SourceRejected("URL has no host")
    if _private_allowed():
        return
    try:                                     # IP literal: decide without DNS
        literal = str(ipaddress.ip_address(host.strip("[]")))
    except ValueError:
        literal = None
    if literal is not None:
        if not is_public_ip(literal):
            raise SourceRejected(f"address {literal} is not public — blocked (SSRF guard)")
        return
    try:
        infos = socket.getaddrinfo(host, port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise SourceRejected(f"cannot resolve host '{host}'") from e
    bad = sorted({i[4][0] for i in infos if not is_public_ip(i[4][0])})
    if bad:
        raise SourceRejected(f"host '{host}' resolves to non-public address {bad[0]} — blocked (SSRF guard)")


def check_url(url: str) -> None:
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        raise SourceRejected(f"only http/https URLs are allowed, got '{u.scheme or url}'")
    if u.username or u.password:
        raise SourceRejected("credentials in URLs are not allowed — use options.auth_env")
    check_host(u.hostname, u.port)


def check_path(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = KIT / p
    rp = p.resolve()
    if not any(rp == r or r in rp.parents for r in allowed_roots()):
        raise SourceRejected(f"path '{path}' is outside the allowed folders (data/, scenarios/, uploads, out) — blocked")
    return rp


def guard_source(src) -> None:
    """Validate a Source from an untrusted caller; mutates src.uri to the resolved path for path kinds."""
    o = src.options or {}
    if src.kind in NET_KINDS:
        if src.kind == "social" and src.uri.startswith("trends:"):
            pass
        else:
            check_url(src.uri)
        for extra in list(o.get("urls") or []) + list(o.get("feeds") or []):
            check_url(str(extra))
        if o.get("render_js"):
            raise SourceRejected("render_js is not allowed through the API (browser redirects cannot be checked)")
        if o.get("auth_env") and not str(o["auth_env"]).startswith(AUTH_ENV_PREFIX):
            raise SourceRejected(f"auth_env must name a variable starting with {AUTH_ENV_PREFIX}")
        if src.kind == "tinyfish" and o.get("api_key"):
            raise SourceRejected("tinyfish reads TINYFISH_API_KEY from the environment; api_key in options is refused")
    elif src.kind in PATH_KINDS:
        src.uri = str(check_path(src.uri))
        if src.kind == "cv":
            bad = set(o) - CV_OPTION_KEYS
            if bad:
                raise SourceRejected(f"cv options not allowed: {sorted(bad)}")
    elif src.kind == "sql":
        u = urlparse(src.uri)
        if u.scheme.startswith("sqlite"):
            db = src.uri.split(":///", 1)[1] if ":///" in src.uri else ""
            if not db or db == ":memory:":
                raise SourceRejected("sqlite URL must point at a database file")
            check_path(db)
        else:
            check_host(u.hostname, u.port)
    elif src.kind == "reducto":
        if src.uri.strip().startswith(("http://", "https://")):
            check_url(src.uri)
        else:
            src.uri = str(check_path(src.uri))
    o["_net_guard"] = True
    src.options = o


def httpx_hooks(src) -> dict:
    """httpx event hooks that re-check every outgoing request (incl. redirects) for guarded sources."""
    if not (src.options or {}).get("_net_guard"):
        return {}

    def _check(request):
        check_url(str(request.url))
    return {"request": [_check]}
