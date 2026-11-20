"""Bronze -> silver rate ingestion (CONTRACT A). CLI: ``python -m vlkit.ratewatch.ingest``."""
from .banks import load_banks
from .runner import RunResult, make_run_id, run_ingest

__all__ = ["RunResult", "load_banks", "make_run_id", "run_ingest"]
