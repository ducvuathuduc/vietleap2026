"""Polite HTTP, bronze landing and silver output for the extra NPL sources.

Same lake rules as the FiinQuant ingest (D1): every response lands in bronze with a meta sidecar
(url, params, fetched_at, sha256, run_id), silver tables carry a meta sheet, watermarks per table and
one run log per run. Robots.txt is honoured, requests are spaced per host and retried with backoff.
"""

from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.robotparser import RobotFileParser

import httpx
import pandas as pd

from .files import atomic, now, write_parquet

USER_AGENT = "VietLeapInsightKit/1.0 (NPL research; +https://github.com/vietleap)"
DELAY = 2.0
ATTEMPTS = 3
TIMEOUT = 40.0


class FetchError(RuntimeError):
    """A fetch failed after its retries; the message is safe for the run log."""


class Fetcher:
    """Robots-aware, per-host throttled GET with bounded retries.

    Every injectable dependency (client, sleep, clock) is a parameter so tests never touch the network.
    """

    def __init__(self, lake=None, run_id="extra-test", client=None, sleep=time.sleep, clock=time.monotonic,
                 delay=DELAY, attempts=ATTEMPTS, timeout=TIMEOUT):
        self.lake = Path(lake) if lake is not None else None
        self.run_id = run_id
        self.client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=timeout,
                                             follow_redirects=True)
        self.sleep = sleep
        self.clock = clock
        self.delay = delay
        self.attempts = attempts
        self.last = {}
        self.robots = {}
        self.calls = []

    def allowed(self, url):
        parts = httpx.URL(url)
        origin = f"{parts.scheme}://{parts.host}"
        if parts.port:
            origin += f":{parts.port}"
        if origin not in self.robots:
            response = self._get(origin + "/robots.txt", check_robots=False)
            parser = RobotFileParser()
            if response.status_code in (404, 410):
                parser.allow_all = True
            else:
                response.raise_for_status()
                parser.parse(response.text.splitlines())
            self.robots[origin] = parser
        return self.robots[origin].can_fetch(USER_AGENT, url)

    def _get(self, url, check_robots=True):
        host = httpx.URL(url).host
        for attempt in range(self.attempts):
            wait = max(0.0, self.last.get(host, 0.0) + self.delay - self.clock())
            self.sleep(wait)
            self.last[host] = self.clock()
            try:
                response = self.client.get(url)
            except httpx.HTTPError:
                if attempt + 1 == self.attempts:
                    raise FetchError(f"GET {url}: transport error after {self.attempts} attempts") from None
            else:
                if response.status_code not in {429, 500, 502, 503, 504}:
                    return response
                if attempt + 1 == self.attempts:
                    raise FetchError(f"GET {url}: HTTP {response.status_code} after {self.attempts} attempts")
            self.sleep(2 ** attempt)
        raise FetchError(f"GET {url}: retries exhausted")

    def get(self, url, params=None, timeout=None):
        if timeout:
            self.client.timeout = timeout
        if not self.allowed(url):
            raise FetchError(f"robots.txt disallows {url}")
        response = self._get(url)
        response.raise_for_status()
        self.calls.append({"url": url, "status": response.status_code, "bytes": len(response.content),
                           "fetched_at": now().isoformat(timespec="seconds")})
        return response


def digest(content):
    return sha256(content).hexdigest()


def land(lake, run_id, source, ref, content, suffix, meta=None):
    """Write one response to bronze/<source>/<run_id>/<sha16>.<suffix> plus its JSON sidecar."""
    content = content if isinstance(content, bytes) else content.encode("utf-8")
    folder = Path(lake) / "bronze" / source / run_id
    stem = digest(f"{source}:{ref}".encode())[:16]
    body, sidecar = folder / f"{stem}.{suffix}", folder / f"{stem}.meta.json"
    atomic(body, content)
    record = {"source": source, "ref": ref, "run_id": run_id, "bytes": len(content),
              "sha256": digest(content), "fetched_at": now().isoformat(timespec="seconds"), **(meta or {})}
    atomic(sidecar, json.dumps(record, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    return record


def write_silver(lake, name, frame, meta=None):
    """Write the silver table (parquet by default, csv for the flat registers) plus a <name>.meta.json."""
    path = Path(lake) / "silver" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".csv":
        scratch = path.with_suffix(".csv.tmp")
        frame.to_csv(scratch, index=False)
        scratch.replace(path)
    else:
        write_parquet(path, frame)
        path = path.with_suffix(".parquet") if path.suffix != ".parquet" else path
    record = {"table": name, "rows": len(frame), "columns": list(frame.columns),
              "sha256": digest(path.read_bytes()), "written_at": now().isoformat(timespec="seconds"),
              **(meta or {})}
    atomic(path.with_name(path.name.split(".")[0] + ".meta.json"),
           json.dumps(record, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    return record


def read_silver(lake, name):
    path = Path(lake) / "silver" / name
    if not path.exists():
        return None
    return pd.read_csv(path) if path.suffix == ".csv" else pd.read_parquet(path)
