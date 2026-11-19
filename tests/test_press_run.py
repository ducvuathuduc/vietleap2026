from __future__ import annotations

import json
import os

import pytest

from tools.press import run


def test_load_targets_has_recipes_and_schemas():
    targets = run.load_targets()
    assert len(targets) >= 8
    ids = {t["source_id"] for t in targets}
    assert {"tcbs_banking_q3_2026", "nhadautu_fdi_10m_2026", "caa_dtc_10m_2026"} <= ids
    for target in targets:
        assert target["url"].startswith("https://")
        assert target["method"] in {"pdf", "tinyfish", "tinyfetch", "scrape", "rss"}
        if target["method"] == "tinyfish":
            assert target["goal"].strip()
            assert isinstance(target["output_schema"], dict)


def test_load_env_does_not_override_or_print(tmp_path, monkeypatch, capsys):
    env_file = tmp_path / ".env.local"
    env_file.write_text("TINYFISH_API_KEY=abc123\nTINYFISH_MAX_USD=80\n# comment\n", encoding="utf-8")
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    run.load_env(env_file)
    assert os.environ["TINYFISH_API_KEY"] == "abc123"
    monkeypatch.setenv("TINYFISH_MAX_USD", "5")
    run.load_env(env_file)
    assert os.environ["TINYFISH_MAX_USD"] == "5"
    assert "abc123" not in capsys.readouterr().out


def test_extract_target_rejects_unknown_method():
    with pytest.raises(ValueError):
        run.extract_target({"source_id": "x", "url": "https://x", "method": "ftp"}, {})


def test_main_reports_new_ledger_spend_excluding_cache_hits(tmp_path, monkeypatch):
    target = {"source_id": "s", "url": "https://example.com", "method": "tinyfish"}
    monkeypatch.setattr(run, "load_env", lambda: None)
    monkeypatch.setattr(run, "load_targets", lambda: [target])
    monkeypatch.setattr(run, "extract_target", lambda *_: ([], {"status": "ok", "cost_usd": 0.048}))
    monkeypatch.setattr(run, "spend_total", lambda: 0.672)
    monkeypatch.setattr(run, "PRESS_LONG", tmp_path / "press_long.csv")
    monkeypatch.setattr(run, "SOURCES_META", tmp_path / "sources_meta.csv")
    monkeypatch.setattr(run, "SUMMARY", tmp_path / "summary.json")

    run.main()

    assert json.loads(run.SUMMARY.read_text(encoding="utf-8"))["run_tinyfish_spend_usd"] == 0


def test_mof_target_replays_reviewed_appendix_without_landed_transcript(tmp_path, monkeypatch):
    from hashlib import sha256
    from tools.press import output

    target = next(t for t in run.load_targets() if t["source_id"] == "bcp_mof_dtc_2026_10")
    cached_pdf = b"cached official report"
    (tmp_path / f"{target['source_id']}.pdf").write_bytes(cached_pdf)
    monkeypatch.setattr(run, "RAW_DIR", tmp_path)
    monkeypatch.setattr(output, "RAW_DIR", tmp_path)
    monkeypatch.setattr(output, "RAW_MANIFEST", tmp_path / "manifest.jsonl")
    monkeypatch.setattr(run, "robots_status", lambda *_: ("allow", True))
    target["sha256"] = sha256(cached_pdf).hexdigest()

    rows, info = run.extract_target(target, {"robots": {}})

    assert info["status"] == "ok"
    assert len(rows) == 133
    assert (tmp_path / f"{target['source_id']}_appendix_ia.tsv").is_file()
