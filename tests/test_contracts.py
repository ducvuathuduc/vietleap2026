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


def test_openapi_in_sync_with_app():
    from api.main import app
    committed = json.loads((C / "openapi.json").read_text(encoding="utf-8"))
    live = app.openapi()
    assert set(committed["paths"]) == set(live["paths"]), "run: python tools/export_openapi.py"
    for p, ops in live["paths"].items():
        assert set(ops) == set(committed["paths"][p]), f"{p}: methods changed — run tools/export_openapi.py"
