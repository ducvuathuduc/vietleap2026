"""Tests for the optional TinyFish agent connector (kind: tinyfish) and the free TinyFetch helper.

Every HTTP call is served by httpx.MockTransport — no network, no spend, no API key required.
"""
from __future__ import annotations

import json

import pytest

httpx = pytest.importorskip("httpx")

SCHEMA = {
    "type": "object",
    "properties": {"title": {"type": "string"}, "total_registered_fdi_usd_bn": {"type": "number"}},
    "required": ["title", "total_registered_fdi_usd_bn"],
}
RESULT = {"title": "Vốn FDI đăng ký cao nhất 17 năm", "total_registered_fdi_usd_bn": 54.85}


@pytest.fixture()
def tf(monkeypatch, tmp_path):
    """tinyfish module with no-op sleeps and a throw-away cache dir."""
    from vlkit.de import tinyfish

    monkeypatch.setenv("TINYFISH_API_KEY", "tf-test-key")
    monkeypatch.delenv("TINYFISH_MAX_USD", raising=False)
    monkeypatch.setattr(tinyfish, "SLEEP", lambda _seconds: None)
    monkeypatch.setattr(tinyfish, "CACHE_DIR", tmp_path / "cache")
    return tinyfish


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _run_json(status="COMPLETED", steps=3, result=RESULT, run_id="run-1"):
    return {"run_id": run_id, "status": status, "num_of_steps": steps, "result": result, "error": None}


# --------------------------------------------------------------------- 1 missing key
def test_missing_api_key_skips_gracefully(tf, monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY")
    out = tf.run_goal("https://example.com/a", "Read the page")
    assert out.status == "skipped"
    assert out.records == []
    assert out.run_id is None
    assert "TINYFISH_API_KEY" in out.message


# --------------------------------------------------------------------- 2 mock
def test_mock_run_writes_artifact_without_key(tf, monkeypatch, tmp_path):
    monkeypatch.delenv("TINYFISH_API_KEY")
    out_file = tmp_path / "mock.json"
    out = tf.run_goal("https://example.com/a", "Read the page", mock=True, out_json=out_file)
    assert out.status == "mock"
    assert out.run_id.startswith("mock-tinyfish-")
    assert out.steps == 3
    assert out.cost_usd == pytest.approx(0.048)          # 3 steps x 0.016
    assert len(out.records) == 1 and "title" in out.records[0]
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved["status"] == "mock"
    assert saved["endpoint"] == "https://agent.tinyfish.ai/v1/automation/run-async"
    assert saved["request"]["api_key"] == "***"           # never the secret
    assert len(saved["records"]) == len(out.records)


# --------------------------------------------------------------------- 3 async + poll
def test_async_run_polls_until_completed(tf):
    seen, polls = [], {"n": 0}

    def handler(req):
        seen.append((req.method, req.url.path))
        assert req.headers["x-api-key"] == "tf-test-key"
        if req.url.path == "/v1/automation/run-async":
            body = json.loads(req.content)
            assert body["url"] == "https://example.com/a"
            assert body["goal"] == "Read the page"
            assert body["output_schema"] == SCHEMA
            assert body["agent_config"]["max_duration_seconds"] == 180
            return httpx.Response(200, json={"run_id": "run-1"})
        if req.url.path == "/v1/runs/run-1":
            polls["n"] += 1
            if polls["n"] == 1:
                return httpx.Response(200, json=_run_json("RUNNING", steps=1, result=None))
            return httpx.Response(200, json=_run_json())
        return httpx.Response(404)

    out = tf.run_goal("https://example.com/a", "Read the page", output_schema=SCHEMA, client=_client(handler))
    assert out.status == "ok"
    assert seen == [("POST", "/v1/automation/run-async"),
                    ("GET", "/v1/runs/run-1"),
                    ("GET", "/v1/runs/run-1")]
    assert out.steps == 3
    assert out.cost_usd == pytest.approx(0.048)
    assert out.records == [RESULT]
    assert tf.spend_total() == pytest.approx(0.048)


# --------------------------------------------------------------------- 4 retry policy
def test_retries_429_with_retry_after(tf, monkeypatch):
    calls, sleeps = [], []
    monkeypatch.setattr(tf, "SLEEP", sleeps.append)

    def handler(req):
        calls.append(req.url.path)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "0"},
                                  json={"error": {"code": "RATE_LIMIT_EXCEEDED"}})
        if req.url.path == "/v1/automation/run-async":
            return httpx.Response(200, json={"run_id": "run-2"})
        return httpx.Response(200, json=_run_json(run_id="run-2"))

    out = tf.run_goal("https://example.com/a", "Read", output_schema=SCHEMA, client=_client(handler))
    assert out.status == "ok"
    assert calls.count("/v1/automation/run-async") == 2
    assert sleeps[0] == 0.0                                # Retry-After honoured


@pytest.mark.parametrize("code", [402, 401])
def test_no_retry_on_payment_or_auth_errors(tf, code):
    calls = []

    def handler(req):
        calls.append(req.url.path)
        body = {"error": {"code": "INSUFFICIENT_CREDITS" if code == 402 else "INVALID_API_KEY"}}
        return httpx.Response(code, json=body)

    with pytest.raises(tf.TinyFishError) as err:
        tf.run_goal("https://example.com/a", "Read", client=_client(handler))
    assert len(calls) == 1                                 # no retry
    assert str(code) in str(err.value)


# --------------------------------------------------------------------- 5 deadline + cancel
def test_deadline_cancels_run_and_keeps_steps(tf):
    seen = []

    def handler(req):
        seen.append((req.method, req.url.path))
        if req.url.path == "/v1/automation/run-async":
            return httpx.Response(200, json={"run_id": "run-3"})
        if req.url.path == "/v1/runs/run-3/cancel":
            return httpx.Response(200, json={"run_id": "run-3", "status": "CANCELLING"})
        return httpx.Response(200, json=_run_json("CANCELLED", steps=2, result=None, run_id="run-3"))

    out = tf.run_goal("https://example.com/a", "Read", deadline_s=0, client=_client(handler))
    assert out.status == "cancelled"
    assert out.steps == 2
    assert seen == [("POST", "/v1/automation/run-async"),
                    ("POST", "/v1/runs/run-3/cancel"),
                    ("GET", "/v1/runs/run-3")]
    assert out.records == []


# --------------------------------------------------------------------- 6 schema validation
def test_schema_mismatch_is_invalid_without_records(tf):
    def handler(req):
        if req.url.path == "/v1/automation/run-async":
            return httpx.Response(200, json={"run_id": "run-5"})
        return httpx.Response(200, json=_run_json(result={"title": "chỉ có title"}, run_id="run-5"))

    out = tf.run_goal("https://example.com/a", "Read", output_schema=SCHEMA, client=_client(handler))
    assert out.status == "invalid"
    assert out.records == []
    assert "total_registered_fdi_usd_bn" in out.message

    def empty(req):
        if req.url.path == "/v1/automation/run-async":
            return httpx.Response(200, json={"run_id": "run-6"})
        return httpx.Response(200, json=_run_json(result=None, run_id="run-6"))

    blank = tf.run_goal("https://example.com/b", "Read", output_schema=SCHEMA, client=_client(empty))
    assert blank.status == "invalid" and blank.records == []


def test_cost_uses_the_rate_from_the_response_when_reported(tf):
    def handler(req):
        if req.url.path == "/v1/automation/run-async":
            return httpx.Response(200, json={"run_id": "run-8"})
        body = _run_json(run_id="run-8")
        body["rates"] = {"meters": [{"label": "TinyFish Agent", "unit_amount": "0.02", "currency": "USD", "per": "step"}]}
        return httpx.Response(200, json=body)

    out = tf.run_goal("https://example.com/a", "Read", output_schema=SCHEMA, client=_client(handler))
    assert out.cost_usd == pytest.approx(0.06)      # 3 steps x 0.02 reported by the API, not the 0.016 default


# --------------------------------------------------------------------- 7 cache
def test_cache_prevents_second_http_call_and_expires(tf):
    calls = []

    def handler(req):
        calls.append(req.url.path)
        if req.url.path == "/v1/automation/run-async":
            return httpx.Response(200, json={"run_id": "run-4"})
        return httpx.Response(200, json=_run_json(run_id="run-4"))

    first = tf.run_goal("https://example.com/a", "Read", output_schema=SCHEMA, client=_client(handler))
    assert first.status == "ok"
    used = len(calls)
    second = tf.run_goal("https://example.com/a", "Read", output_schema=SCHEMA, client=_client(handler))
    assert len(calls) == used                              # served from disk cache
    assert second.status == "ok" and second.records == [RESULT]
    assert second.steps == 3 and second.cost_usd == pytest.approx(0.048)
    assert "cache" in second.message
    assert tf.spend_total() == pytest.approx(0.048)        # not paid twice

    tf.run_goal("https://example.com/a", "Read", output_schema=SCHEMA, cache_ttl_h=0, client=_client(handler))
    assert len(calls) > used                               # ttl 0 -> expired -> fetched again


# --------------------------------------------------------------------- 8 netguard
def test_guard_source_blocks_private_url_and_inline_key(monkeypatch):
    from vlkit.de import netguard
    from vlkit.de.netguard import SourceRejected, guard_source
    from vlkit.de.sources import Source

    monkeypatch.delenv("KIT_ALLOW_PRIVATE_NET", raising=False)
    with pytest.raises(SourceRejected):
        guard_source(Source("bad", "tinyfish", "http://127.0.0.1/secret", {"goal": "g"}))

    monkeypatch.setattr(netguard.socket, "getaddrinfo", lambda h, p, **k: [(2, 1, 6, "", ("93.184.216.34", p))])
    with pytest.raises(SourceRejected):
        guard_source(Source("bad", "tinyfish", "https://ok.example/a", {"goal": "g", "api_key": "leaked"}))
    ok = Source("good", "tinyfish", "https://ok.example/a", {"goal": "g"})
    guard_source(ok)
    assert ok.options["_net_guard"] is True


# --------------------------------------------------------------------- budget guard
def test_budget_guard_refuses_before_any_http(tf, monkeypatch, tmp_path):
    def forbidden(req):
        raise AssertionError("no HTTP request may be made when the budget is exhausted")

    spend = tmp_path / "cache" / "_spend.jsonl"
    spend.parent.mkdir(parents=True)
    spend.write_text(json.dumps({"ts": "2026-11-19T00:00:00+07:00", "source": "s1", "cost_usd": 0.03}) + "\n",
                     encoding="utf-8")
    monkeypatch.setenv("TINYFISH_MAX_USD", "0.02")
    out = tf.run_goal("https://example.com/a", "Read", source="s2", client=_client(forbidden))
    assert out.status == "skipped" and "TINYFISH_MAX_USD" in out.message

    monkeypatch.delenv("TINYFISH_MAX_USD")
    out = tf.run_goal("https://example.com/a", "Read", source="s1", max_usd=0.02, client=_client(forbidden))
    assert out.status == "skipped" and "max_usd" in out.message


def test_budget_guard_allows_a_source_under_its_cap(tf):
    def handler(req):
        if req.url.path == "/v1/automation/run-async":
            return httpx.Response(200, json={"run_id": "run-7"})
        return httpx.Response(200, json=_run_json(run_id="run-7"))

    out = tf.run_goal("https://example.com/a", "Read", output_schema=SCHEMA, source="s9", max_usd=0.3,
                      client=_client(handler))
    assert out.status == "ok"


# --------------------------------------------------------------------- evidence check
def test_evidence_check_matches_vietnamese_numbers(tf):
    text = ("Tổng vốn FDI đăng ký đạt 54,85 tỷ USD; vốn thực hiện 24,08 tỷ USD. "
            "Thu NSNN 2.438,9 nghìn tỷ đồng, CPI tăng 5,09%.")
    checks = tf.evidence_check({"total": 54.85, "disbursed": "24,08", "budget": 2438.9, "cpi": 5.09,
                                "wrong": 30.73, "title": "Vốn FDI đăng ký cao nhất 17 năm"}, text)
    assert checks["total"] is True
    assert checks["disbursed"] is True
    assert checks["budget"] is True
    assert checks["cpi"] is True
    assert checks["wrong"] is False
    assert checks["title"] is None                       # not a number -> not evidence-checked
    assert tf.row_evidence({"a": 54.85, "b": 30.73}, text) is False
    assert tf.row_evidence({"a": 54.85, "b": "abc"}, text) is True
    assert tf.row_evidence({"a": "abc"}, text) is None


# --------------------------------------------------------------------- TinyFetch
def test_fetch_text_returns_markdown_by_url(tf, monkeypatch):
    seen = {}

    def handler(req):
        assert str(req.url) == "https://api.fetch.tinyfish.ai"
        assert req.headers["x-api-key"] == "tf-test-key"
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={
            "results": [{"url": "https://example.com/a", "final_url": "https://example.com/a",
                         "text": "FDI 54,85 tỷ USD"}],
            "errors": []})

    got = tf.fetch_text(["https://example.com/a"], client=_client(handler))
    assert got == {"https://example.com/a": "FDI 54,85 tỷ USD"}
    assert seen == {"urls": ["https://example.com/a"], "format": "markdown"}

    monkeypatch.delenv("TINYFISH_API_KEY")
    assert tf.fetch_text(["https://example.com/a"]) == {}


# --------------------------------------------------------------------- connector
def test_connector_registered_and_mock_frame(tf, monkeypatch, tmp_path):
    from vlkit.de import connectors
    from vlkit.de.sources import Source

    monkeypatch.setattr(connectors, "BRONZE", tmp_path)
    monkeypatch.delenv("TINYFISH_API_KEY")
    assert "tinyfish" in connectors.CONNECTORS
    src = Source("savills_reports", "tinyfish", "https://www.savills.com.vn/insight-and-opinion/",
                 {"goal": "Return the 5 latest reports", "output_schema": SCHEMA, "mock": True})
    res = connectors.ingest(src)
    df = res.frames["savills_reports"]
    assert len(df) == 1
    for col in ("_run_id", "_fetched_at", "_status", "_num_steps", "_cost_usd", "_evidence_ok"):
        assert col in df.columns
    assert df["_status"][0] == "mock"
    assert (tmp_path / "tinyfish_savills_reports.json").is_file()
    assert res.provenance["status"] == "mock"


# --------------------------------------------------------------------- connector evidence
def test_connector_evidence_uses_tinyfetch_then_page_get(tf, monkeypatch, tmp_path):
    from vlkit.de import connectors
    from vlkit.de.sources import Source

    monkeypatch.setattr(connectors, "BRONZE", tmp_path)
    html = "<html><body><p>Tổng vốn FDI đăng ký đạt 54,85 tỷ USD</p></body></html>"
    seen = []

    def handler(req):
        seen.append((req.method, req.url.host))
        if req.url.host == "agent.tinyfish.ai":
            if req.url.path.endswith("run-async"):
                return httpx.Response(200, json={"run_id": "run-9"})
            return httpx.Response(200, json=_run_json(run_id="run-9"))
        if req.url.host == "api.fetch.tinyfish.ai":
            req_json = json.loads(req.content)
            if req_json["urls"] == ["https://example.com/b"]:      # TinyFetch is blocked for this origin
                return httpx.Response(200, json={"results": [], "errors": [
                    {"url": "https://example.com/b", "error": "bot_blocked"}]})
            return httpx.Response(200, json={"results": [
                {"url": "https://example.com/a", "text": "FDI 54,85 tỷ USD"}], "errors": []})
        return httpx.Response(200, text=html)

    monkeypatch.setitem(connectors.CONNECTORS, "tinyfish",
                        lambda s: connectors.ingest_tinyfish(s, client=_client(handler)))
    for uri in ("https://example.com/a", "https://example.com/b"):
        res = connectors.ingest(Source(f"src_{uri[-1]}", "tinyfish", uri, {"goal": "g", "output_schema": SCHEMA}))
        df = res.frames[f"src_{uri[-1]}"]
        assert res.provenance["status"] == "ok"
        assert len(df) == 1
        assert bool(df["_evidence_ok"][0]) is True, uri
    assert ("GET", "example.com") in seen                    # TinyFetch was blocked -> plain GET fallback


# --------------------------------------------------------------------- options validation
def test_source_option_validation():
    from vlkit.de.sources import Source

    with pytest.raises(ValueError, match="goal"):
        Source("s", "tinyfish", "https://example.com/a", {})
    with pytest.raises(ValueError, match="mode"):
        Source("s", "tinyfish", "https://example.com/a", {"goal": "g", "mode": "sync"})
    with pytest.raises(ValueError, match="64"):
        Source("s", "tinyfish", "https://example.com/a", {"goal": "g", "output_schema": {"description": "x" * 70000}})
    deep = current = {}
    for _ in range(12):
        current["nested"] = {}
        current = current["nested"]
    with pytest.raises(ValueError, match="depth"):
        Source("s", "tinyfish", "https://example.com/a", {"goal": "g", "output_schema": deep})
    ok = Source("s", "tinyfish", "https://example.com/a",
                {"goal": "g", "output_schema": SCHEMA, "mode": "async", "max_usd": 0.2})
    assert ok.options["max_usd"] == 0.2
