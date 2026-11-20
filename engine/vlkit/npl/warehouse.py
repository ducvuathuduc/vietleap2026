"""Build the DuckDB gold star and serving views."""

import duckdb

from .model import AMOUNTS, KEY, SOURCE

KEY_SQL = """
    bank_code VARCHAR REFERENCES gold.dim_bank(bank_code),
    period VARCHAR REFERENCES gold.dim_period(period),
    basis VARCHAR CHECK (basis IN ('consolidated', 'separate'))
"""


def write_gold(path, credit, signals):
    metrics = [name for name in credit if name not in KEY + SOURCE + ["writeoff_basis", "missing_fields"]]
    with duckdb.connect(str(path)) as con:
        con.register("credit", credit)
        con.register("signals", signals)
        con.execute("""
            CREATE SCHEMA gold;
            CREATE TABLE gold.dim_bank (bank_code VARCHAR PRIMARY KEY);
            CREATE TABLE gold.dim_period (
                period VARCHAR PRIMARY KEY, quarter UTINYINT NOT NULL, year USMALLINT NOT NULL,
                is_quarter_end BOOLEAN NOT NULL
            );
            INSERT INTO gold.dim_bank SELECT DISTINCT bank_code FROM credit ORDER BY bank_code;
            INSERT INTO gold.dim_period
                SELECT DISTINCT period, right(period, 1)::UTINYINT, left(period, 4)::USMALLINT, true
                FROM credit ORDER BY period;
        """)
        source = ", ".join(SOURCE)
        source_types = ", ".join(f"{name} VARCHAR" for name in SOURCE)
        has_source = " OR ".join(f"{name} IS NOT NULL" for name in SOURCE)
        same_source = " AND ".join(f"c.{name} IS NOT DISTINCT FROM s.{name}" for name in SOURCE)
        con.execute(f"""
            CREATE TABLE gold.dim_source (source_id BIGINT PRIMARY KEY, {source_types});
            INSERT INTO gold.dim_source
                SELECT row_number() OVER (ORDER BY {source}), {source}
                FROM (SELECT DISTINCT {source} FROM credit WHERE {has_source}) AS sources;
        """)
        metric_types = ", ".join(f"{name} DOUBLE" for name in metrics)
        fact_fields = ", ".join([
            *(f"c.{name}" for name in KEY), "s.source_id",
            *(f"c.{name}" for name in ["writeoff_basis"] + metrics),
        ])
        # Defense in depth for bounded shares. Coverage and flows over opening loans
        # have no universal upper bound, and net formation can have either sign.
        bounded = ", ".join(
            f"CHECK ({name} BETWEEN 0 AND 1)" for name in ("npl_ratio", "g2_ratio", "broad_problem_ratio")
        )
        nonnegative = ", ".join(
            f"CHECK ({name} >= 0)" for name in AMOUNTS + ["coverage", "writeoff_ratio", "writeoff_ratio_annualised"]
        )
        con.execute(f"""
            CREATE TABLE gold.fact_credit_quality (
                {KEY_SQL}, source_id BIGINT REFERENCES gold.dim_source(source_id),
                writeoff_basis VARCHAR CHECK (writeoff_basis IN ('quarter', 'ytd')),
                {metric_types}, missing_fields VARCHAR[] NOT NULL,
                PRIMARY KEY (bank_code, period, basis), {bounded}, {nonnegative}
            );
            INSERT INTO gold.fact_credit_quality
                SELECT {fact_fields}, c.missing_fields::VARCHAR[]
                FROM credit AS c LEFT JOIN gold.dim_source AS s ON {same_source};
        """)
        con.execute(f"""
            CREATE TABLE gold.fact_signal (
                {KEY_SQL}, signal VARCHAR CHECK (signal IN ('S1', 'S2', 'S3', 'S4', 'S5')),
                sentence_vi VARCHAR NOT NULL, sentence_en VARCHAR NOT NULL,
                PRIMARY KEY (bank_code, period, signal),
                FOREIGN KEY (bank_code, period, basis)
                    REFERENCES gold.fact_credit_quality(bank_code, period, basis)
            );
            INSERT INTO gold.fact_signal SELECT * FROM signals;
            CREATE VIEW gold.v_credit_quality AS
                SELECT f.*, p.quarter, p.year, p.is_quarter_end, s.* EXCLUDE (source_id)
                FROM gold.fact_credit_quality f JOIN gold.dim_period p USING (period)
                LEFT JOIN gold.dim_source s USING (source_id);
            CREATE VIEW gold.v_signal AS
                SELECT s.*, c.source_id, c.delta_npl_ratio, c.delta_g2_ratio,
                       c.delta_writeoff_ratio, c.delta_coverage, c.delta_npl_formation
                FROM gold.fact_signal s JOIN gold.fact_credit_quality c USING (bank_code, period, basis);
        """)
