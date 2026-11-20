import json
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from vlkit.ratewatch.quality import evaluate
from vlkit.ratewatch.warehouse import transform

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/ratewatch/t2"


def test_known_sacombank_sheet_cell_and_disagreement(tmp_path):
    # V-CURVE: Sacombank PDF + bank-page read, 20/10/2026, counter <500m, 6m = 5.70%.
    db = tmp_path / "ratewatch.duckdb"
    transform(db, [FIXTURE / "rates.csv"], FIXTURE / "banks.yaml", [])
    with duckdb.connect(str(db)) as con:
        checks = {gate["id"]: gate for gate in evaluate(con, datetime.fromisoformat("2026-11-20T13:00:00+07:00"))}
        assert checks["calibration"]["status"] == "pass"
        assert "4.5" in checks["disagreement"]["detail"]
        con.execute("update gold.fact_posted_rate set rate_pct = 15 where term_months = 6")
        checks = {gate["id"]: gate for gate in evaluate(con, datetime.fromisoformat("2026-12-25T13:00:00+07:00"))}
    assert checks["bounds"]["status"] == checks["freshness"]["status"] == checks["calibration"]["status"] == "fail"


@pytest.mark.parametrize(("series", "total", "parts", "status"), [
    ("sbv_credit", 19703851, 19703853, "pass"),
    ("sbv_credit", 19703851, 19703855, "fail"),
    ("sbv_credit", 19703851.20, 19703853.20, "fail"),
    ("omo", 2713.20, 2715.20, "fail"),
])
def test_sbv_reconciliation_respects_whole_billion_credit_rounding(tmp_path, series, total, parts, status):
    source = tmp_path / f"{series}.json"
    rows = json.loads((FIXTURE / f"nonrate/{series}.json").read_text(encoding="utf-8"))
    rows[0].update(total_bn=total, parts_bn=parts)
    source.write_text(json.dumps(rows), encoding="utf-8")
    db = tmp_path / "ratewatch.duckdb"
    transform(db, [FIXTURE / "rates.csv"], FIXTURE / "banks.yaml", [source])
    with duckdb.connect(str(db)) as con:
        checks = {gate["id"]: gate for gate in evaluate(con, datetime.fromisoformat("2026-11-20T13:00:00+07:00"))}
    assert checks["sbv_reconcile"]["status"] == status
