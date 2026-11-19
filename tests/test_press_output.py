from __future__ import annotations

import csv
import json

from tools.press import output


def test_contract_row_validates_measure_and_method():
    row = output.contract_row(indicator_id="x", source_id="s", source_url="u", method="pdf",
                              period="2026-Q3", measure_type="level", value=1.5, unit="%", geo="VNM")
    assert row["value"] == "1.5"
    assert row["evidence_ok"] == ""
    try:
        output.contract_row(indicator_id="x", source_id="s", source_url="u", method="pdf", measure_type="bogus")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("measure_type must be validated")


def test_dedupe_keeps_first_and_sorts():
    rows = [
        output.contract_row(indicator_id="b", source_id="s", source_url="u", method="pdf", period="2026-Q3",
                            measure_type="level", value=2, geo="VNM"),
        output.contract_row(indicator_id="a", source_id="s", source_url="u", method="pdf", period="2026-Q3",
                            measure_type="level", value=1, geo="VNM"),
        output.contract_row(indicator_id="a", source_id="s", source_url="u", method="pdf", period="2026-Q3",
                            measure_type="level", value=9, geo="VNM"),
    ]
    out = output.dedupe(rows)
    assert [r["indicator_id"] for r in out] == ["a", "b"]
    assert out[0]["value"] == "1"


def test_write_long_csv_and_meta(tmp_path):
    rows = [output.contract_row(indicator_id="x", source_id="s", source_url="u", method="pdf", period="2026-Q3",
                                measure_type="level", value=1, unit="%", geo="VNM")]
    path = tmp_path / "press_long.csv"
    assert output.write_long_csv(path, rows) == 1
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == output.LONG_COLUMNS
        assert next(reader)["indicator_id"] == "x"
    meta_path = tmp_path / "sources_meta.csv"
    assert output.write_sources_meta_csv(meta_path, [dict(zip(output.META_COLUMNS, ["s", "p", "t", "u", "pdf", "l", "allow", "now"]))]) == 1
    assert meta_path.read_text(encoding="utf-8").splitlines()[1].startswith("s,p,t,u")


def test_save_raw_writes_sha256(tmp_path, monkeypatch):
    monkeypatch.setattr(output, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(output, "RAW_MANIFEST", tmp_path / "raw_manifest.jsonl")
    p = output.save_raw("demo", b"hello", "txt")
    assert p.read_bytes() == b"hello"
    rec = json.loads((tmp_path / "raw_manifest.jsonl").read_text(encoding="utf-8"))
    assert rec["sha256"] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
