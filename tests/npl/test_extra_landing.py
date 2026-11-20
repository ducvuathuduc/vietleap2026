import json

import pytest

from vlkit.npl.ingest.extra_landing import FetchError, Fetcher, land, read_silver, write_silver, digest


class Response:
    def __init__(self, status=200, content=b"ok", url="https://example.test/page"):
        self.status_code = status
        self.content = content
        self.text = content.decode()
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class Client:
    """Serves robots.txt plus a scripted list of responses per URL."""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        if url.endswith("/robots.txt"):
            return Response(200, self.pages.get("robots", b"User-agent: *\nAllow: /\n"))
        value = self.pages[url]
        if isinstance(value, list):
            value = value.pop(0) if len(value) > 1 else value[0]
        return Response(*value) if isinstance(value, tuple) else Response(200, value)


def fetcher(pages, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return Fetcher(client=Client(pages), sleep=sleeps.append, clock=lambda: 0.0)


def test_robots_disallow_blocks_the_request():
    pages = {"robots": b"User-agent: *\nDisallow: /private/\n", "https://example.test/private/x": b"secret"}
    ingest = fetcher(pages)
    with pytest.raises(FetchError) as excinfo:
        ingest.get("https://example.test/private/x")
    assert "robots.txt disallows" in str(excinfo.value)
    assert ingest.calls == []


def test_transient_500_is_retried_then_succeeds():
    pages = {"https://example.test/a": [(500, b"boom", "https://example.test/a"), (200, b"fine", "https://example.test/a")]}
    sleeps = []
    ingest = fetcher(pages, sleeps)
    assert ingest.get("https://example.test/a").content == b"fine"
    assert sleeps[:1] == [2.0]          # first request waits for the per-host delay
    assert 1 in sleeps                  # one backoff pause before the retry


def test_requests_to_one_host_are_spaced():
    sleeps, now = [], {"t": 0.0}
    ingest = Fetcher(client=Client({"https://example.test/a": b"1", "https://example.test/b": b"2"}),
                     sleep=sleeps.append, clock=lambda: now["t"])
    ingest.get("https://example.test/a")
    now["t"] = 0.5
    ingest.get("https://example.test/b")
    assert sleeps[-1] == pytest.approx(1.5)


def test_land_writes_body_sidecar_and_sha256(tmp_path):
    meta = land(tmp_path, "extra-test", "wdi", "FB.AST.NPER.ZS", b'{"ok":1}', "json", {"url": "u"})
    body = tmp_path / "bronze/wdi/extra-test"
    files = sorted(path.name for path in body.iterdir())
    assert len(files) == 2
    sidecar = json.loads((body / [name for name in files if name.endswith(".meta.json")][0]).read_text())
    assert sidecar["sha256"] == digest(b'{"ok":1}') == meta["sha256"]
    assert sidecar["source"] == "wdi" and sidecar["url"] == "u"


def test_write_silver_records_rows_and_round_trips(tmp_path):
    import pandas as pd

    record = write_silver(tmp_path, "legal_register.csv", pd.DataFrame({"ref": ["11/2021/TT-NHNN"]}))
    assert record["rows"] == 1 and record["columns"] == ["ref"]
    assert read_silver(tmp_path, "legal_register.csv").loc[0, "ref"] == "11/2021/TT-NHNN"
    assert (tmp_path / "silver/legal_register.meta.json").exists()
