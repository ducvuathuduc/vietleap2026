# T2 follow-up 2 (queue after follow-up 1)
1. gold.dim_source is referenced but not created in the gold schema (CONTRACT section 'Design': dim_source with source_id, publisher, url, licence, method, robots_allowed). Create it from bronze meta + the sources registry and join fact_posted_rate.source_url to it (source_id on the fact).
2. Generate the data dictionary (out/ratewatch/data_dictionary.md) with, for every gold table: grain sentence, keys, each column with type/unit/source, and the formula for derived columns (grade rule, npl_amount_growth_pct, edition).
3. Generate an ERD (Mermaid text in out/ratewatch/erd.mmd) of the gold star schema.
Tests for 1-3; rerun pytest -q tests/ratewatch.
