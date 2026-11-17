"""Contracts in specs/001-vietleap-insight-kit/contracts/ match what the code really produces."""
import json
from pathlib import Path

import pandas as pd
import pytest

jsonschema = pytest.importorskip("jsonschema")
from referencing import Registry, Resource  # noqa: E402  (ships with jsonschema ≥ 4.18)

C = Path(__file__).resolve().parents[1] / "specs" / "001-vietleap-insight-kit" / "contracts"


def _validator(name: str):
    schemas = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in C.glob("*.schema.json")}
    reg = Registry().with_resources([(k, Resource.from_contents(v)) for k, v in schemas.items()])
    return jsonschema.Draft202012Validator(schemas[f"{name}.schema.json"], registry=reg)


def _check(name: str, doc):
    errors = sorted(_validator(name).iter_errors(doc), key=lambda e: list(e.path))
    assert not errors, f"{name}: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])


@pytest.fixture()
def run(tmp_path):
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    from vlkit.de.warehouse import Warehouse
    a = tmp_path / "listings.csv"
    pd.DataFrame({"tinh": ["Hà Nội", "Đà Nẵng", "Cần Thơ", "Hà Nội"] * 5, "nam": [2023, 2023, 2024, 2024] * 5,
                  "gia": [float(i) for i in range(20)]}).to_csv(a, index=False)
    b = tmp_path / "budget.csv"
    pd.DataFrame({"tinh": ["Hà Nội", "Đà Nẵng", "Cần Thơ"], "chi_ngan_sach": [10.0, 5.0, 3.0]}).to_csv(b, index=False)
    wh = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    try:
        s = run_flow("contract", [Source("listings", "file", str(a)), Source("budget", "file", str(b))],
                     out_root=tmp_path / "out", wh=wh, primary="listings", mode="incremental")
    finally:
        wh.close()
    return tmp_path / "out" / "contract", s


def test_pipeline_lineage_conformed_contracts(run):
    out, s = run
    _check("pipeline", json.loads((out / "pipeline.json").read_text(encoding="utf-8")))
    _check("lineage", json.loads((out / "lineage.json").read_text(encoding="utf-8")))
    assert (out / "conformed.json").exists(), "two sources sharing province should build conformed dims"
    _check("conformed", json.loads((out / "conformed.json").read_text(encoding="utf-8")))


def test_brief_contract():
    from vlkit.brief import parse_brief
    b = parse_brief("Đề bài: phân tích giá nhà theo tỉnh giai đoạn 2020–2024. Yếu tố nào liên quan đến giá/m2?",
                    columns=["tinh", "nam", "gia", "dien_tich"])
    b["dataset"] = None
    _check("brief", b)


def test_story_contract_shape():
    story = {"mode": "offline", "model": None, "headline": "x", "closing": "y",
             "steps": [{"id": "i1", "rank": 1, "title": "t", "narration": "n", "stats": "s", "action": None, "source": "engine"}]}
    _check("story", story)
    with pytest.raises(AssertionError):
        _check("story", {**story, "mode": "magic"})
    # feature 002: additive question / limits
    framed = {**story, "question": {"text": "Tỉnh nào nên ưu tiên?", "who": "UBND tỉnh", "what": None, "kpi": "Thu/người", "source": "brief"},
              "limits": ["c1", "c2", "c3"]}
    _check("story", framed)
    _check("story", {**story, "question": None, "limits": []})
    for bad in ({**framed, "limits": ["1", "2", "3", "4"]}, {**framed, "question": {"text": "q", "source": "llm"}},
                {**framed, "question": {"text": "x" * 2001, "source": "brief"}}):
        with pytest.raises(AssertionError):
            _check("story", bad)


def test_openapi_in_sync_with_app():
    from api.main import app
    committed = json.loads((C / "openapi.json").read_text(encoding="utf-8"))
    live = app.openapi()
    assert set(committed["paths"]) == set(live["paths"]), "run: python tools/export_openapi.py"
    for p, ops in live["paths"].items():
        assert set(ops) == set(committed["paths"][p]), f"{p}: methods changed — run tools/export_openapi.py"


# ----------------------------------------------------------------------------- feature 003: report language

LANG_CONTRACT = Path(__file__).resolve().parents[1] / "specs" / "003-bilingual-deck" / "contracts" / "lang.openapi.yaml"


@pytest.fixture()
def lang_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("KIT_OUT_DIR", str(tmp_path / "out"))
    d = tmp_path / "out" / "ds"
    d.mkdir(parents=True)
    (d / "results.json").write_text(json.dumps({"files": {"deck_vi": "deck.vi.pptx", "pitch_en": "pitch.en.md"}}), encoding="utf-8")
    (d / "deck.vi.pptx").write_bytes(b"PK\x03\x04 vi deck")
    (d / "pitch.en.md").write_text("# pitch", encoding="utf-8")
    from api.main import app
    from api.store import Store, get_store
    app.dependency_overrides[get_store] = lambda: Store(tmp_path / "out")  # the app-wide store is a process singleton
    yield TestClient(app)
    app.dependency_overrides.pop(get_store, None)


def test_export_kinds_match_lang_contract():
    import yaml

    from api.routes.datasets import EXPORTS
    from vlkit import report
    doc = yaml.safe_load(LANG_CONTRACT.read_text(encoding="utf-8"))
    assert set(doc["components"]["schemas"]["ExportKind"]["enum"]) == set(EXPORTS)
    assert doc["components"]["schemas"]["ReportLang"]["enum"] == ["vi", "en", "both"]
    for lang in ("en", "vi"):  # export kind → the file the report writes for that language
        assert EXPORTS[report.DECK_KEYS[lang]][0] == report.DECK_FILES[lang]
        assert EXPORTS[report.PITCH_KEYS[lang]][0] == report.PITCH_FILES[lang]


def test_language_exports_served_and_guarded(lang_client):
    c = lang_client
    r = c.get("/api/datasets/ds/files/deck_vi")
    assert r.status_code == 200 and "presentationml" in r.headers["content-type"]
    r = c.get("/api/datasets/ds/files/pitch_en")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/markdown")
    assert c.get("/api/datasets/ds/files/deck").status_code == 404        # not generated in this language
    assert c.get("/api/datasets/ds/files/pitch_fr").status_code == 404     # allowlist only
    assert c.get("/api/datasets/ds/files/..%2Fresults").status_code == 404
    assert c.get("/api/datasets/..%2F..%2Fetc/files/deck_vi").status_code == 404


def test_lang_is_validated_at_the_edge(lang_client, tmp_path, monkeypatch):
    monkeypatch.setenv("KIT_UPLOAD_DIR", str(tmp_path / "up"))
    c = lang_client
    r = c.post("/api/datasets", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")}, data={"lang": "fr"})
    assert r.status_code == 422 and not list((tmp_path / "up").glob("*"))
    assert any("lang" in e["loc"] for e in r.json()["detail"])
    body = {"dataset": "d", "sources": [{"name": "s", "kind": "file", "uri": "data/practice/x.csv"}], "lang": "de"}
    r = c.post("/api/ingest", json=body)
    assert r.status_code == 422 and any("lang" in e["loc"] for e in r.json()["detail"])  # rejected before any job starts
