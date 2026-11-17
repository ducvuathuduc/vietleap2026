# Implementation plan

1. Reuse warehouse lineage, table metadata, existing profile and engine insight output for the two exports. Test the emitted files and FastAPI downloads. The web sidebar follows existing file links and displays the new links when `files` declares them.
2. Reuse source connectors for deterministic preparation. Store checksums with cached inputs. Default named packs to practice files where provided. Give an actionable missing-data error for packs with team-supplied files.
3. Reuse `run_flow` and `pipeline.run`. Parse the brief before ingestion and resolve the analytical target against the actual gold frame before analysis. Export both languages for the contest entry point.
4. Use GitHub Actions with read-only permissions and `upload-artifact`. Use DuckDB `httpfs` with session credentials for the explicit S3 command. Collect no secret values in logs.

## Constitution check

Stats and field samples come from DuckDB and the engine. Gather and serve with existing file/URL guards at API boundaries. Use only built-in libraries, DuckDB, existing dependencies and official shadcn components. Run Python and web checks sequentially.
