"""Checks for rebuilding reports, bundle contents and the export job."""
import hashlib
import json
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pandas as pd
import pytest


@pytest.fixture
def export_dataset(tmp_path):
    from vlkit import pipeline

    data = tmp_path / "measures.csv"
    pd.DataFrame({"measure": [i * 1.25 for i in range(48)], "group": ["A"] * 24 + ["B"] * 24}).to_csv(data, index=False)
    pipeline.run(data, out_root=tmp_path, name="demo", target="measure", reports=False)
    out = tmp_path / "demo"
    (out / "pipeline.json").write_text(json.dumps({"run_id": "fixture-run"}), encoding="utf-8")
    (out / "provenance.json").write_text(json.dumps([{"source": "measures", "license_note": "Synthetic fixture"}]), encoding="utf-8")
    return out


def test_bundle_keeps_language_scope_and_hashes_without_chromium(export_dataset, monkeypatch):
    from vlkit import export, report

    monkeypatch.setattr(report, "html_to_pdf", lambda *args: None)
    monkeypatch.setattr(export, "dashboard_pdf", lambda *args: (None, "Thiếu Chromium — chạy make setup"))
    (export_dataset / ".env").write_text("UNRELATED=fixture", encoding="utf-8")
    result = export.build_export(export_dataset, lang="en", dashboard=True)
    assert result["files"] == {"bundle": "export/bundle.zip"}
    assert any("Chromium" in warning for warning in result["warnings"])
    with zipfile.ZipFile(export_dataset / result["files"]["bundle"]) as archive:
        names = set(archive.namelist())
        assert {"deck.pptx", "pitch.en.md", "dashboard.html", "eda.md", "provenance.json", "README.txt"} <= names
        assert not names & {".env", "deck.vi.pptx", "pitch.md", "dashboard.pdf", "executive_summary.pdf"}
        readme = archive.read("README.txt").decode("utf-8")
        assert "fixture-run" in readme and "Synthetic fixture" in readme and "Chromium" in readme
        assert all(hashlib.sha256(archive.read(name)).hexdigest() in readme for name in names - {"README.txt"})


def test_dashboard_prints_ready_web_page(tmp_path):
    from playwright.sync_api import sync_playwright
    from vlkit.export import dashboard_pdf

    with sync_playwright() as playwright:
        try:
            playwright.chromium.launch(timeout=5000).close()
        except Exception:
            pytest.skip("Playwright Chromium absent")
    paths = []

    class ReadyPage(BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'<main data-print-ready="demo">VietLeap KPI</main>')

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), ReadyPage) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            pdf, warning = dashboard_pdf(f"http://127.0.0.1:{server.server_port}", "demo", tmp_path)
        finally:
            server.shutdown()
            thread.join()
    assert "/print?dataset=demo" in paths and not warning
    assert pdf is not None and pdf.read_bytes().startswith(b"%PDF-")


def test_export_job_is_idempotent_and_downloadable(export_dataset, monkeypatch):
    from fastapi.testclient import TestClient
    from api import jobs
    from api.main import app
    from api.store import Store, get_store

    started, release = threading.Event(), threading.Event()

    def export_once(out, lang, dashboard, web_url):
        started.set()
        assert release.wait(5)
        (out / "export").mkdir()
        with zipfile.ZipFile(out / "export/bundle.zip", "w") as archive:
            archive.writestr("README.txt", "VietLeap test")
        return {"warnings": ["Chromium absent"], "files": {"bundle": "export/bundle.zip"}}

    monkeypatch.setattr(jobs, "_run_export_process", export_once)
    app.dependency_overrides[get_store] = lambda: Store(export_dataset.parent)
    try:
        with TestClient(app) as client:
            response = client.post("/api/datasets/demo/export", json={"lang": "both", "dashboard_pdf": True})
            assert response.status_code == 202
            job_id = response.json()["job_id"]
            assert started.wait(5)
            assert client.post("/api/datasets/demo/export", json={}).json()["job_id"] == job_id
            assert client.get(f"/api/export/{job_id}").json()["status"] == "running"
            release.set()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                job = client.get(f"/api/export/{job_id}").json()
                if job["status"] in {"done_with_warnings", "error"}:
                    break
                time.sleep(0.02)
            assert job["status"] == "done_with_warnings"
            assert client.get("/api/datasets/demo/files/bundle").content.startswith(b"PK")
            assert client.get("/api/export/no-such-job").status_code == 404
    finally:
        release.set()
        del app.dependency_overrides[get_store]


def test_reanalysis_hides_previous_bundle_and_dashboard_pdf(export_dataset):
    import os
    from fastapi.testclient import TestClient
    from api.main import app
    from api.store import Store, get_store

    directory = export_dataset / "export"
    directory.mkdir()
    for name in ("bundle.zip", "dashboard.pdf"):
        (directory / name).write_bytes(b"old artifact")
    app.dependency_overrides[get_store] = lambda: Store(export_dataset.parent)
    try:
        with TestClient(app) as client:
            assert client.get("/api/datasets/demo/files/bundle").status_code == 200
            results = export_dataset / "results.json"
            later = max((directory / name).stat().st_mtime_ns for name in ("bundle.zip", "dashboard.pdf")) + 10**9
            os.utime(results, ns=(later, later))
            summary = client.get("/api/datasets/demo").json()
            assert "bundle" not in summary["files"] and "dashboard_pdf" not in summary["files"]
            for kind in ("bundle", "dashboard_pdf"):
                assert client.get(f"/api/datasets/demo/files/{kind}").status_code == 404
    finally:
        del app.dependency_overrides[get_store]


def test_rebuild_ignores_whatif_from_a_previous_analysis(export_dataset, monkeypatch):
    from vlkit import report

    current = export_dataset / "results.json"
    results = json.loads(current.read_text(encoding="utf-8"))
    results["drivers"] = None
    current.write_text(json.dumps(results), encoding="utf-8")
    stale = export_dataset / "whatif.json"
    stale.write_text(json.dumps({"target": "removed_metric"}), encoding="utf-8")

    def check_whatif(results, frame, whatif, *args, **kwargs):
        assert results["drivers"] is None
        assert whatif is None
        return {}

    monkeypatch.setattr(report, "build_all", check_whatif)
    report.rebuild_reports(export_dataset)
