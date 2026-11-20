# VietLeap | Behind the NPL Ratio

VietLeap helps bank analysts, researchers and readers of Vietnamese listed-bank financial statements interpret changes in credit quality. It asks whether a lower reported non-performing loan (NPL) ratio, especially at year-end, reflects a lasting improvement. The decoder checks Group 2 loans, write-offs, provision coverage and seasonal patterns alongside the headline ratio. The bilingual site includes bank comparisons, a market event study, methodology, a CSV export and a read-only assistant grounded in the published data.

[Open the live application](https://vi-661c03b5a07045aeaf57703e47c826e3.ecs.ap-southeast-1.on.aws)

## Data and pipeline

FiinQuant supplies bank financial ratios, market prices, valuations and foreign trading data. Bank financial-statement notes supply additional loan and provision figures where available. Bank and exchange disclosures give report dates. State Bank of Vietnam releases, Vietnamese legal texts and World Bank World Development Indicators provide regulatory and regional context. The app shows source references and coverage in its methodology and data pages. Missing observations remain missing.

The Python engine lands source records and provenance in Bronze. Silver normalises tickers, dates and reporting scope into Parquet and CSV tables. Gold stores the analysis panel in DuckDB and produces model results. The snapshot builder packages the results and quality checks in a schema-validated JSON file for the Next.js app.

Gold links bank, quarter and date dimensions to quarterly bank ratios, daily market observations and disclosure events. Quarterly facts use bank ticker, quarter and reporting scope as their key. Market facts use ticker and trading date. Disclosure events retain the observed reporting date, a deadline-based fallback and the associated trading session. Statement notes carry their source URL, page and verification grade.

## Run locally

Use Node.js 22 and run these commands from the repository root.

```sh
cd web
npm ci
npm run dev
```

Open http://localhost:3000. With no cloud settings, the app reads the bundled NPL snapshot. To read a published S3 snapshot, set `NPL_SNAPSHOT_S3_URI` to its `s3://bucket/key` URI and give the process AWS read access. The assistant runs in offline mode when no provider is configured. It also supports OpenAI, Groq and the Langfuse AI Gateway.

Use Python 3.12 for the engine. From the repository root, install the dependencies and run the retained Python tests.

```sh
python -m pip install -r requirements.txt
python -m pytest -q tests
```

## Chạy lại từ đầu

The PowerShell commands below use the interpreter in `.venv`, with the engine requirements and the bundled FiinQuant SDK installed. Put authorised FiinQuant credentials in your ignored `.env.local`. Run from the repository root. This run fixes the data cutoff and uses a separate lake. The providers can revise historical records.

```powershell
$env:PYTHONPATH='engine;.'
$env:PYTHONIOENCODING='utf-8'
$env:OPENBLAS_NUM_THREADS='2'
$env:OMP_NUM_THREADS='2'
.venv/Scripts/python.exe -m vlkit.npl.ingest --all --as-of 2026-11-20 --credentials .env.local --lake out/npl-rebuild/lake
.venv/Scripts/python.exe -m vlkit.npl.ingest --screening --as-of 2026-11-20 --credentials .env.local --lake out/npl-rebuild/lake
.venv/Scripts/python.exe -m vlkit.npl.ingest --extra --as-of 2026-11-20 --lake out/npl-rebuild/lake
.venv/Scripts/python.exe -m vlkit.npl.pipeline --real out/npl-rebuild/lake/silver --out out/npl-rebuild/analysis
.venv/Scripts/python.exe -m vlkit.npl.snapshot --results out/npl-rebuild/analysis/results.json --gold out/npl-rebuild/analysis/gold.duckdb --silver out/npl-rebuild/lake/silver --out out/npl-rebuild/snapshot.json

$env:PATH = "$(Join-Path (Get-Location) '.venv/Scripts');$env:PATH"
$env:PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=out/npl-rebuild/pytest'
pytest -q tests
Set-Location web
npm.cmd test
npm.cmd run dev -- --port 3017 --hostname 127.0.0.1
```

Bronze and Silver land in `out/npl-rebuild/lake`. Gold, `results.json`, and the analytical exports land in `out/npl-rebuild/analysis`. The rebuilt snapshot lands in `out/npl-rebuild/snapshot.json`. The local web server is at http://127.0.0.1:3017 and reads the repository's published seed with S3 unconfigured.

To regenerate that bundled seed from the audited release lake, run from the repository root with the same environment settings.

```powershell
.venv/Scripts/python.exe -m vlkit.npl.pipeline --real data/lake/npl/silver --out out/b17
.venv/Scripts/python.exe -m vlkit.npl.snapshot --results out/b17/results.json --gold out/b17/gold.duckdb --silver data/lake/npl/silver --out web/seed/npl/snapshot.json
```

The reviewer tests, bank-cluster bootstrap and market-model inference use `BOOTSTRAP_SEED = 20261120`. Random non-event dates use `PLACEBO_SEED = 20261120`, and the Q2/Q3 placebo uses `BOOTSTRAP_SEED + 11`.

## AWS deployment

Deploy the base CloudFormation stack for the private S3 lake, ECR repositories, ECS cluster and task roles. The app stack uses the base stack outputs, application secret and VPC subnets to run an ECS Express web service and schedule the Fargate pipeline with EventBridge Scheduler. The pipeline publishes the snapshot to `snapshots/npl/snapshot.json` after its quality checks pass. The web task reads that object from S3, and ECS uses `/api/health` for liveness.

GitHub Actions assumes the deploy role via OIDC, builds the web and pipeline images, pushes them to ECR in `ap-southeast-1` and can roll the Express service when its ARN is configured. AWS Secrets Manager supplies credentials to the tasks.

[Base stack](infra/aws/vietleap-base.yaml) · [App stack](infra/aws/vietleap-app.yaml) · [OIDC deploy role](infra/aws/github-oidc.yaml) · [Deploy workflow](.github/workflows/deploy.yml)

## Licence

The project code is licensed under Apache-2.0. Source data and third-party components are subject to their own terms. Confirm publication rights before redistributing source inputs or derived data.

[Apache-2.0 licence](LICENSE) · [Data and third-party terms](docs/licenses.md)
