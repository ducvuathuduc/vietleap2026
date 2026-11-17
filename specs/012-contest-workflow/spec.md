# Contest workflow and offline preparation

**Priority** P1 · **Depends on** 004

A team member supplies a pack or recipe and a brief. `make contest PACK=<pack> BRIEF=<file>` runs locally using checked-in inputs or the prepared cache, saves the brief and bronze/silver/gold models, analyses the selected target, and prints paths to a static dashboard, a data dictionary (CSV and Markdown), an EDA report (Markdown), and the deck and pitch in both languages by default.

- The data dictionary describes each gold column using its DuckDB type, actual missingness, source or derivation, a sample, and descriptions and units when documented. The API and Exports menu offer links to generated reports.
- EDA uses the engine's quality checks, profile, findings and limitations. Missing values stay visible. Markdown is the default.
- `de.py snapshot` prepares sources before an offline run. Missing cache files produce an actionable error. The daily and manual collection workflow downloads public sources and attaches cache files as artifacts. It uses repository permissions only.
- `de.py sync --to s3` is an opt-in mirror of gold Parquet using the four `KIT_S3_*` environment variables. DuckDB + local Parquet remain the primary store.
- The provincial and WDI packs use verified offline data for rehearsal. Contest inputs can be supplied through a recipe or an explicit local file. A pack template provides an owner, a decision question and the KPIs to monitor.

## Acceptance

Run an offline recipe against a transport that refuses every request. Inspect the brief target, Kimball star, returned paths, both deck and pitch languages, dictionary values and EDA statistics. Verify downloads, traversal rejection, CSV escaping, and S3 behavior with a mock. Skip the live S3 test when one of the variables is missing.
