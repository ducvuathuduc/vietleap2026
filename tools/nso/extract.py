"""Fetch and cache NSO monthly socio-economic reports, then write the long CSV.

Usage: python tools/nso/extract.py [--refresh]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.nso import parse

LISTING_URL = "https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/"
ROBOTS_URL = "https://www.nso.gov.vn/robots.txt"
USER_AGENT = "vietleap-research/0.1 (NSO monthly report extractor; +https://github.com/vietleap)"
START_PERIOD = "2024-01"
DELAY = 2.0
RETRIES = 3
MAX_PAGES = 12

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "raw" / "nso"
LONG_CSV = "nso_monthly_long.csv"
COVERAGE_CSV = "nso_coverage.csv"
WATERMARK = "_watermark.json"
ROBOTS_RECORD = "_robots.json"

_LISTING_RE = re.compile(
    r'<a href="([^"]+)">\s*</p>\s*<section class="item">\s*<h3>(.*?)</h3>(.*?)</section>',
    re.S,
)

_last_request_at = 0.0


class RobotsDenied(RuntimeError):
    pass


class FetchError(RuntimeError):
    pass


def _throttle(delay: float, sleep) -> None:
    global _last_request_at
    if delay > 0:
        wait = delay - (time.monotonic() - _last_request_at)
        if wait > 0:
            sleep(wait)


def fetch_url(
    url: str,
    *,
    user_agent: str = USER_AGENT,
    opener=urllib.request.urlopen,
    retries: int = RETRIES,
    sleep=time.sleep,
    delay: float = DELAY,
    timeout: int = 60,
) -> bytes:
    """GET a URL with throttle, retries and exponential backoff. Returns raw bytes."""
    global _last_request_at
    last_error: Exception | None = None
    for attempt in range(retries):
        _throttle(delay, sleep)
        _last_request_at = time.monotonic()
        request = urllib.request.Request(url, headers={"User-Agent": user_agent})
        try:
            with opener(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # network errors, HTTP errors, timeouts
            last_error = exc
            if attempt + 1 < retries:
                sleep(2**attempt)
    raise FetchError(f"GET {url} failed after {retries} attempts: {last_error}") from last_error


def check_robots(
    robots_url: str = ROBOTS_URL,
    *,
    out_dir: Path | str = OUT_DIR,
    user_agent: str = USER_AGENT,
    opener=urllib.request.urlopen,
    sleep=time.sleep,
    delay: float = DELAY,
) -> bool:
    """Check robots.txt for the listing and article paths; record the result before scraping."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = fetch_url(
        robots_url, user_agent=user_agent, opener=opener, retries=2, sleep=sleep, delay=delay
    )
    robots = urllib.robotparser.RobotFileParser()
    robots.parse(body.decode("utf-8", errors="replace").splitlines())
    allowed = robots.can_fetch(user_agent, LISTING_URL) and robots.can_fetch(
        user_agent, urljoin(LISTING_URL, "/bai-top/")
    )
    crawl_delay = robots.crawl_delay(user_agent)
    record = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "robots_url": robots_url,
        "user_agent": user_agent,
        "allowed": allowed,
        "crawl_delay": crawl_delay,
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    (out_dir / ROBOTS_RECORD).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    if not allowed:
        raise RobotsDenied(f"robots.txt at {robots_url} does not allow {LISTING_URL}")
    return True


def parse_listing(html: str, base_url: str = LISTING_URL) -> list[dict]:
    """Extract (period, url, title) entries from one archive page."""
    entries = []
    seen = set()
    for href, title_html, _rest in _LISTING_RE.findall(html):
        title = parse.clean_text(unescape(re.sub(r"<[^>]+>", "", title_html)))
        try:
            period = parse.period_from_title(title)
        except ValueError:
            continue
        if period in seen:
            continue
        seen.add(period)
        entries.append({"period": period, "url": urljoin(base_url, unescape(href)), "title": title})
    return entries


def discover(*, sleep=time.sleep, delay: float = DELAY, max_pages: int = MAX_PAGES) -> dict[str, dict]:
    """Walk the paginated archive and return period -> {url, title} for 2024-01 onwards."""
    found: dict[str, dict] = {}
    for page in range(1, max_pages + 1):
        url = LISTING_URL if page == 1 else f"{LISTING_URL}?paged={page}"
        body = fetch_url(url, sleep=sleep, delay=delay)
        entries = parse_listing(body.decode("utf-8", errors="replace"), LISTING_URL)
        fresh = [entry for entry in entries if entry["period"] not in found]
        for entry in fresh:
            if entry["period"] >= START_PERIOD:
                found[entry["period"]] = {"url": entry["url"], "title": entry["title"]}
        if not entries or not fresh:
            break
    return dict(sorted(found.items()))


def select_targets(periods: list[str], watermark: str | None, recent: int = 2) -> set[str]:
    """Periods newer than the watermark plus the last `recent` periods (for revisions)."""
    if not periods:
        return set()
    targets = set(sorted(periods)[-recent:])
    if watermark:
        targets.update(period for period in periods if period > watermark)
    else:
        targets.update(periods)
    return targets


def read_watermark(out_dir: Path | str = OUT_DIR) -> str | None:
    path = Path(out_dir) / WATERMARK
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("last_period")
    except (ValueError, OSError):
        return None


def write_watermark(period: str, out_dir: Path | str = OUT_DIR) -> None:
    path = Path(out_dir) / WATERMARK
    path.write_text(
        json.dumps(
            {
                "last_period": period,
                "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _cache_valid(raw: Path, sha: Path) -> bool:
    if not raw.exists():
        return False
    if not sha.exists():
        return True
    return sha.read_text(encoding="utf-8").strip() == hashlib.sha256(raw.read_bytes()).hexdigest()


def _cache_write(raw: Path, sha: Path, body: bytes) -> None:
    raw.write_bytes(body)
    sha.write_text(hashlib.sha256(body).hexdigest() + "\n", encoding="utf-8")


def read_long_csv(out_dir: Path | str = OUT_DIR) -> list[dict]:
    path = Path(out_dir) / LONG_CSV
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_long_csv(rows: list[dict], out_dir: Path | str = OUT_DIR) -> None:
    path = Path(out_dir) / LONG_CSV
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=parse.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def coverage_rows(rows: list[dict], periods: list[str]) -> list[dict]:
    """Coverage matrix in long form: every indicator x period, including empty cells."""
    by_key: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        by_key.setdefault((row["indicator_id"], row["period"]), []).append(row["measure_type"])
    out = []
    for indicator in parse.INDICATOR_ORDER:
        for period in periods:
            measures = by_key.get((indicator, period), [])
            ordered = [m for m in parse.MEASURE_ORDER if m in measures]
            out.append(
                {
                    "indicator_id": indicator,
                    "period": period,
                    "n_measures": len(ordered),
                    "measures": ";".join(ordered),
                }
            )
    return out


def _write_coverage(rows: list[dict], periods: list[str], out_dir: Path) -> None:
    path = out_dir / COVERAGE_CSV
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["indicator_id", "period", "n_measures", "measures"])
        writer.writeheader()
        writer.writerows(coverage_rows(rows, periods))


def _merge(existing: list[dict], new_rows: list[dict], replaced_periods: set[str]) -> list[dict]:
    kept = [row for row in existing if row["period"] not in replaced_periods]
    merged = {}
    for row in kept + new_rows:
        merged[(row["indicator_id"], row["period"], row["measure_type"])] = row
    return sorted(
        merged.values(),
        key=lambda row: (
            row["period"],
            parse.INDICATOR_ORDER.index(row["indicator_id"])
            if row["indicator_id"] in parse.INDICATOR_ORDER
            else 99,
            parse.MEASURE_ORDER.index(row["measure_type"])
            if row["measure_type"] in parse.MEASURE_ORDER
            else 99,
        ),
    )


def run(
    *,
    refresh: bool = False,
    out_dir: Path | str = OUT_DIR,
    discover_fn=None,
    fetch_fn=None,
    robots_fn=None,
    sleep=time.sleep,
    delay: float = DELAY,
) -> dict:
    """Discover, fetch, parse and merge reports. Returns a summary; individual page errors are accumulated."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if robots_fn is None:
        def robots_fn():
            return check_robots(out_dir=out_dir, sleep=sleep, delay=delay)

    robots_fn()
    discovered = discover_fn() if discover_fn is not None else discover(sleep=sleep, delay=delay)
    periods = sorted(discovered)

    watermark = read_watermark(out_dir)
    targets = sorted(select_targets(periods, watermark))

    existing = read_long_csv(out_dir)
    fetched: list[str] = []
    cached: list[str] = []
    parsed_periods: set[str] = set()
    new_rows: list[dict] = []
    errors: list[str] = []

    for period in targets:
        entry = discovered[period]
        raw = out_dir / f"{period}.html"
        sha = out_dir / f"{period}.html.sha256"
        try:
            if not refresh and _cache_valid(raw, sha):
                body = raw.read_bytes()
                cached.append(period)
            else:
                body = (fetch_fn or (lambda url: fetch_url(url, sleep=sleep, delay=delay)))(
                    entry["url"]
                )
                _cache_write(raw, sha, body)
                fetched.append(period)
            result = parse.parse_html(
                body.decode("utf-8", errors="replace"), source_url=entry["url"]
            )
            new_rows.extend(result["rows"])
            parsed_periods.add(period)
        except Exception as exc:
            errors.append(f"{period}: {exc}")

    merged = _merge(existing, new_rows, parsed_periods)
    write_long_csv(merged, out_dir)
    _write_coverage(merged, periods, out_dir)

    if not errors and targets:
        new_watermark = max(targets)
        if watermark is None or new_watermark > watermark:
            write_watermark(new_watermark, out_dir)

    return {
        "periods": periods,
        "targets": targets,
        "fetched": fetched,
        "cached": cached,
        "rows": len(merged),
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-fetch cached report pages")
    args = parser.parse_args(argv)

    summary = run(refresh=args.refresh)
    print(
        f"NSO: {len(summary['periods'])} periods discovered, "
        f"{len(summary['targets'])} targets, {len(summary['fetched'])} fetched, "
        f"{len(summary['cached'])} cached, {summary['rows']} CSV rows"
    )
    for error in summary["errors"]:
        print(f"ERROR {error}", file=sys.stderr)
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
