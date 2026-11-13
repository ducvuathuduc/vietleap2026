"""Data-engineering layer: Ingestion → Storage → Transform → Serving.

    sources.py     Source spec + provenance (YAML: many sources in one file)
    connectors.py  file / api / sql / scrape / social / cv  → IngestResult(df, provenance)
    warehouse.py   DuckDB medallion (bronze / silver / gold / meta) + Parquet lake
    quality.py     missing / duplicate / outlier / type checks, cleaning log, quality score
    modeling.py    OBT, Star schema, Snowflake, Data Vault 2.0 built from silver tables
    lineage.py     lineage graph + Mermaid flow/ERD
    flow.py        orchestrator: run_flow(sources) end to end
"""
from .sources import Source, load_sources  # noqa: F401
