"""Tests for optional Reducto PDF/scan document parsing connector."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


def test_reducto_missing_api_key_skips_gracefully(monkeypatch, tmp_path):
    from vlkit.de.reducto import parse_document

    monkeypatch.delenv("REDUCTO_API_KEY", raising=False)
    sample = tmp_path / "report.pdf"
    sample.write_bytes(b"%PDF-1.4\n%fake\n")

    out = parse_document(sample, mock=False)
    assert out.status == "skipped"
    assert out.records == []
    assert out.job_id is None
    assert "REDUCTO_API_KEY" in out.message


def test_reducto_mock_produces_structured_json_and_records(monkeypatch, tmp_path):
    from vlkit.de.reducto import parse_document

    monkeypatch.delenv("REDUCTO_API_KEY", raising=False)
    out_file = tmp_path / "reducto_mock.json"
    out = parse_document("data/raw/sample_budget.pdf", mock=True, out_json=out_file)
    assert out.status == "mock"
    assert out.job_id == "mock-reducto-sample_budget_pdf"
    assert len(out.records) >= 2
    assert any(r["block_type"] == "Table" for r in out.records)
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved["status"] == "mock"
    assert saved["endpoint"] == "https://platform.reducto.ai/parse"
    assert len(saved["records"]) == len(out.records)


def test_reducto_live_upload_and_parse_with_mocked_httpx(monkeypatch, tmp_path):
    httpx = pytest.importorskip("httpx")
    from vlkit.de.reducto import parse_document

    monkeypatch.setenv("REDUCTO_API_KEY", "test-reducto-secret-123")
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\nhello")
    seen: list[tuple[str, str]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append((req.method, str(req.url)))
        assert req.headers.get("authorization") == "Bearer test-reducto-secret-123"
        if req.url.path == "/upload":
            return httpx.Response(200, json={"file_id": "reducto://uploaded-file-1"})
        if req.url.path == "/parse":
            body = json.loads(req.content.decode("utf-8"))
            assert body["input"] == "reducto://uploaded-file-1"
            return httpx.Response(200, json={
                "job_id": "job-live-1",
                "result": {"chunks": [{"blocks": [{"type": "Title", "content": "Báo cáo", "bbox": {"page": 1}}]}]},
            })
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    out_file = tmp_path / "live.json"
    out = parse_document(pdf, out_json=out_file, client=client)
    assert out.status == "ok"
    assert out.job_id == "job-live-1"
    assert len(out.records) == 1
    assert out.records[0]["content"] == "Báo cáo"
    assert seen == [
        ("POST", "https://platform.reducto.ai/upload"),
        ("POST", "https://platform.reducto.ai/parse"),
    ]


def test_reducto_netguard_blocks_private_urls(monkeypatch):
    from vlkit.de.netguard import SourceRejected, guard_source
    from vlkit.de.sources import Source

    src = Source("bad", "reducto", "http://127.0.0.1/secret.pdf")
    with pytest.raises(SourceRejected):
        guard_source(src)

    ok_src = Source("good", "reducto", "data/practice/synthetic_messy_bds.csv")
    guard_source(ok_src)
    assert ok_src.options["_net_guard"] is True


def test_de_cli_reducto_missing_key_exits_zero(monkeypatch, tmp_path):
    monkeypatch.delenv("REDUCTO_API_KEY", raising=False)
    kit = Path(__file__).resolve().parents[1]
    if str(kit) not in sys.path:
        sys.path.insert(0, str(kit))
    import de

    # No key + no --mock must skip gracefully with zero exit (no SystemExit non-zero)
    de.main(["reducto", str(kit / "data" / "practice" / "synthetic_messy_bds.csv")])
    out_file = tmp_path / "cli_mock.json"
    de.main(["reducto", "demo.pdf", "--mock", "--out", str(out_file)])
    assert out_file.is_file()
