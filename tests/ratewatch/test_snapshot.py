import json
from datetime import datetime
from pathlib import Path

import pytest

from vlkit.ratewatch.snapshot import publish, validate_snapshot
from vlkit.ratewatch.warehouse import transform

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/ratewatch/t2"


def test_publish_validates_and_preserves_previous_file_on_gate_failure(tmp_path):
    db = tmp_path / "ratewatch.duckdb"
    destination = tmp_path / "seed/snapshot.json"
    output = tmp_path / "public"
    transform(db, [FIXTURE / "rates.csv"], FIXTURE / "banks.yaml", list((FIXTURE / "nonrate").glob("*.json")))
    publish(db, destination, output, now=datetime.fromisoformat("2026-11-20T13:00:00+07:00"))
    original = destination.read_bytes()
    payload = json.loads(original)
    validate_snapshot(payload)
    assert payload["banks"][0]["rates"][0]["grade"] == "contested"
    assert len(payload["banks"][0]["rates"][0]["readers"]) == 2
    assert payload["market"]["ceiling_stats"]["quotes_1_5m"] == 0
    assert payload["market"]["central_fx"] == [{"date": "2026-11-20", "vnd_per_usd": 25659}]
    assert payload["macro"]["cpi_yoy"] == [{"month": "2026-10", "pct": 5.09}]
    assert payload["macro"]["sbv_monthly"][0]["credit_growth_ytd_pct"] == 10.19
    assert list((output / "archive").glob("*.csv"))
    assert (output / "eda.svg").is_file()
    with pytest.raises(ValueError, match="freshness"):
        publish(db, destination, output, now=datetime.fromisoformat("2027-01-01T13:00:00+07:00"))
    assert destination.read_bytes() == original
