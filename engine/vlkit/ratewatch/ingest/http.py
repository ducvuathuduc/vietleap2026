"""Polite HTTP for the rate readers: robots.txt first, >=2 s per host, retries with exponential backoff.

Reuses the project conventions already proven in ``vlkit.de.connectors`` (identifiable UA, robots.txt respected,
no captcha/login bypass) without pulling the whole connector in: a rate sheet is one small GET per host.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit

import httpx

UA = "VietLeapInsightKit/1.0 (ratewatch; contact: vietleap2026 participant)"
TIMEOUT = 45.0
MIN_INTERVAL_S = 2.0
ATTEMPTS = 3
BASE_DELAY_S = 1.0
RETRY_STATUS = {429, 500, 502, 503, 504}
ROBOTS: dict[str, RobotFileParser | None] = {}
_LAST: dict[str, float] = {}


class FetchError(RuntimeError):
    """A fetch that failed (retryable) or was refused (permanent, see :class:`PermanentFetchError`)."""


class PermanentFetchError(FetchError):
    """4xx other than 429: retrying would only hammer the host."""


@dataclass
class Response:
    url: str
    status: int
    content: bytes
    content_type: str = ""

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", "replace")


def retry_call(fn, *, attempts: int = ATTEMPTS, base_delay: float = BASE_DELAY_S, sleep=time.sleep):
    """Call ``fn`` up to ``attempts`` times, sleeping ``base_delay * 2**n`` between attempts."""
    last: Exception | None = None
    for attempt in range(int(attempts)):
        try:
            return fn()
        except PermanentFetchError:
            raise
        except FetchError as exc:
            last = exc
            if attempt == int(attempts) - 1:
                break
            sleep(base_delay * (2 ** attempt))
    raise last if last else FetchError("fetch failed")


def _read_robots(host: str, timeout: float = 20.0):
    """RobotFileParser for a host, ``False`` when robots.txt forbids everyone, ``None`` when unreadable."""
    try:
        response = httpx.get(f"https://{host}/robots.txt", timeout=timeout, follow_redirects=True,
                             headers={"User-Agent": UA})
    except httpx.HTTPError:
        return None
    if response.status_code in (401, 403):
        return False
    if response.status_code >= 400:
        return None
    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser


def robots_allowed(url: str, *, user_agent: str = UA, cache: dict | None = None) -> bool:
    """robots.txt for the host, read once. 401/403 forbids the host; an unreadable file means no rules found."""
    host = urlsplit(url).netloc
    cache = ROBOTS if cache is None else cache
    if host not in cache:
        cache[host] = _read_robots(host)
    parser = cache[host]
    if parser is None:
        return True
    if parser is False:
        return False
    try:
        return parser.can_fetch(user_agent, url)
    except Exception:              # noqa: BLE001
        return True


class HttpClient:
    """Minimal GET client: robots.txt checked by the caller, one request per URL with backoff."""

    def __init__(self, *, timeout: float = TIMEOUT, sleep=time.sleep, min_interval: float = MIN_INTERVAL_S,
                 client: httpx.Client | None = None):
        self.timeout = timeout
        self._sleep = sleep
        self.min_interval = min_interval
        self._client = client

    def _polite(self, url: str) -> None:
        host = urlsplit(url).netloc
        wait = self.min_interval - (time.monotonic() - _LAST.get(host, 0.0))
        if wait > 0:
            self._sleep(wait)
        _LAST[host] = time.monotonic()

    def get(self, url: str, *, timeout: float | None = None) -> Response:
        self._polite(url)
        client = self._client or httpx.Client(timeout=timeout or self.timeout, follow_redirects=True,
                                              headers={"User-Agent": UA, "Accept-Language": "vi,en"})
        try:
            def once() -> Response:
                try:
                    response = client.get(url)
                except httpx.HTTPError as exc:
                    raise FetchError(f"GET {url} failed: {exc!r}") from exc
                if response.status_code in RETRY_STATUS:
                    raise FetchError(f"GET {url} -> HTTP {response.status_code}")
                if response.status_code >= 400:
                    raise PermanentFetchError(f"GET {url} -> HTTP {response.status_code}")
                return Response(url=str(response.url), status=response.status_code, content=response.content,
                                content_type=response.headers.get("content-type", ""))

            return retry_call(once, attempts=ATTEMPTS, base_delay=BASE_DELAY_S, sleep=self._sleep)
        finally:
            if self._client is None:
                client.close()
