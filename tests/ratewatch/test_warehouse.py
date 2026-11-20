from pathlib import Path

import duckdb

from vlkit.ratewatch.warehouse import transform

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/ratewatch/t2"


def test_transform_idempotent_and_retains_contested_values(tmp_path):
    db = tmp_path / "ratewatch.duckdb"
    results = []
    for _ in range(2):
        transform(db, [FIXTURE / "rates.csv"], FIXTURE / "banks.yaml", [])
        with duckdb.connect(str(db)) as con:
            results.append(con.execute("""
                select term_months, grade, rate_pct from gold.fact_posted_rate
                order by term_months, rate_pct
            """).fetchall())
            assert con.execute("select count(distinct term_months) from gold.v_curve_today").fetchone() == (2,)
            assert con.execute("select count(*) from gold.v_curve_today").fetchone() == (4,)
    assert results[0] == results[1] == [
        (5, "contested", 4.5), (5, "contested", 4.6),
        (6, "verified", 5.7), (6, "verified", 5.7),
    ]
