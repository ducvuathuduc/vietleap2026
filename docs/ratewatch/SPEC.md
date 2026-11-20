# RateWatch VN — spec v1 (draft, 20/11/2026 13:20). Owner approval pending the X-* blocker round.
Repo C:\Users\dieut\Desktop\Money\vietleap, base e19f05d, feature branch feat/ratewatch. Specs live here, never in the repo.

## 1. Requirements
R1 Reader and decision (Dray): a household saver with a lump sum asks every week/at each maturity "where, for how long, and how much
   per bank". Policy reader: SBV monetary policy staff and DIV: "do the 4.75% short-term ceiling and the 350-million cap still serve savers?"
R2 Main screen answers level, benchmark, trend, decision, with a one-sentence headline carrying numbers, period and source.
R3 Every number traces to a source row (URL, read time, reader grade) and a formula; three numbers recomputed by hand in the docs.
R4 Data refresh: bank rates twice a day; money market daily; macro monthly; FiinQuant bank data quarterly + market daily.
R5 Planner: amount, horizon, online yes/no, optional current bank and risk filter -> split per bank within the insured cap, term
   ladder, VND interest vs baseline, break-even rate, insured share, scenario +-50/100 bp.
R6 AI assistant: Vietnamese/English questions -> deterministic tools -> answer with live charts in chat; numbers guard; public
   Langfuse trace per answer; no personal data in prompts or traces; works offline with deterministic fallback.
R7 Savings-book photo: on-device OCR, user confirms fields, only numbers + bank name leave the device; image never uploaded.
R8 Policy panel: ceiling kink evidence and cost; insurance cap coverage (SBV figures); rate vs bank risk (FiinQuant percentiles, n stated).
R9 Method page: lineage, data dictionary, EDA, quality-gate results, limitations, AI-use disclosure, legal citations, downloads
   (public sources only; FiinQuant only as aggregates/percentiles with attribution after mentor confirmation).
R10 Production on AWS ap-southeast-1: public HTTPS, no login, no dev/lab routes, no debug logs, security headers, rate-limited AI,
    health check, budget alarm. Backup static snapshot link.
R11 Legal: QĐ 2411/QĐ-NHNN (ceiling), TT 05/2026 Điều 3 (cap 350 million from 13/7/2026; QĐ 32/2021 repealed by NĐ 280/2026),
    TT 04/2026 (premium 0.15% flat), Law 91/2025 Điều 20 (cross-border personal data), Securities Law 54/2019 Điều 4.32 (deposit
    comparison is not securities advice). "Thông tin tham khảo" notice.
R12 Long-term: first public daily archive of bank-level deposit rates in Vietnam (CSV/API, CC-BY), extendable to lending rates.

## 2. Design
### Pipeline (mentor Tasco: ingestion -> storage -> transform -> serving; idempotent, incremental, retry+backoff, logging, keep raw)
- Ingestion: bank registry YAML (bank, url, method fetch|pdf|tinyfish, parser, robots status); readers: TinyFetch/HTML, PDF text,
  TinyFish agent (standard goal, JSON rows); second reader per bank; FiinQuant (bank ratios quarterly, market daily); SBV interbank,
  OMO, central FX (daily), SBV monthly stats; NSO CPI; VCB FX. Every call -> bronze object (raw bytes + meta: url, fetched_at, sha256,
  run_id, robots, licence). Watermarks per source; retries with exponential backoff; run log JSON (records, errors, seconds, USD).
- Storage: S3 (bronze private; silver/gold Parquet); DuckDB as engine; local mirror under data/ (gitignored).
- Transform: silver = typed, unit-normalised, deduplicated rows with reader grades; gold = Kimball star:
  dim_bank, dim_term (ceiling bucket), dim_channel, dim_date, dim_source;
  fact_posted_rate (bank, term, channel, effective_date valid time, observed_at recorded time, rate, grade, source, run) — bitemporal,
  change events derived; fact_bank_quarter; fact_bank_market_day; fact_money_market_day; fact_macro_month; fact_policy_param
  (value, valid_from, valid_to, legal_ref). OBT views: v_curve_today, v_bank_profile, v_plan_options.
- Quality gates (fail the snapshot, never silently pass): schema; 0 < rate < 15; terms < 6 m <= ceiling else flag; two-reader
  agreement; freshness <= 30 days; aggregator vs bank page disagreement flagged; SBV parts vs totals; calibration on known values
  (e.g. Sacombank PDF 12 m counter); row counts vs previous run. EDA report + data dictionary generated each run.
- Serving: versioned snapshot JSON (JSON Schema + citation check) -> web app; public CSV archive.
### Models and formulas
- Interest at maturity: P * r * days/365 (bank convention stated per bank; default actual/365).
- Break-even renewal rate: (1 + r_H*H/12) = (1 + r_a*a/12) * (1 + f*(H-a)/12).
- Real rate (Fisher): (1+r)/(1+pi) - 1, pi = CPI YoY (NSO).
- Ceiling impact: delta = median r(6m) - median r(5m); cost to a saver = P * delta * h/12.
- Nelson-Siegel on the system median curve (tau fixed, OLS), fitted on >= 6 m terms plus a ceiling dummy; betas stored daily.
- Split/ladder optimiser: maximise interest s.t. per-bank amount <= cap, maturity <= horizon (or early-withdrawal at demand rate),
  bank passes the reader's risk filter; greedy on (bank, term) options, verified against brute force on small cases.
- Bank profile: percentile rank per metric among listed banks (no invented weights) + flags vs cited prudential limits.
- Market discipline: Spearman rho and OLS rate_12m ~ risk metrics + state dummy, HC3 SE, bootstrap CI, n stated (exploratory).
- Rate-pressure indicators: interbank ON minus policy rate, credit growth minus deposit growth, system LDR. No point forecast.
### Web (Next.js 16 + shadcn dashboard-01, Recharts), VI default + EN
- / "Thị trường hôm nay": headline; 3 KPI tiles (level, benchmark vs CPI/SBV average, trend); main chart deposit yield curve by bank
  with median band and ceiling annotation; heatmap bank x term with grade badges and source links; rate-change ticker.
- /ke-hoach planner with persona buttons and sliders; /chinh-sach policy panel; /phuong-phap method, data, legal, AI use, downloads.
- AI side panel on every page.
### AI
- AI SDK v7 ToolLoopAgent; provider env switch: Anthropic Claude Sonnet 5 (API key) | Groq gpt-oss-120b; Bedrock later if quota.
- Tools (deterministic, snapshot only): get_curve, get_bank_profile, plan_deposit, break_even, insured_split, get_policy_param,
  explain_metric. Tool results rendered as typed parts by our chart components. Numbers guard before display.
- Langfuse (jp.cloud.langfuse.com) via OTel: session id, snapshot version, source ids; mask PII patterns; public trace link per answer.
- OCR: Tesseract.js "vie" in the browser, regex field extraction, confirm form; nothing but confirmed numbers + bank leaves the device.
### AWS
- ECR (web, pipeline); ECS Express Mode web service 0.5 vCPU/1 GB; S3 data bucket (versioned, private); EventBridge Scheduler ->
  ECS task pipeline 08:45 and 15:45 ICT; Secrets Manager; CloudWatch logs + alarm; AWS Budgets alarm; GitHub Actions with OIDC role
  (least privilege), images built on GitHub runners. Account is root-only today: create scoped roles, never root keys in CI.

## 3. Tasks (owner per file set; disjoint)
T1 rates ingestion (engine/vlkit/ratewatch/ingest/, scenarios/ratewatch/banks.yaml, tests/ratewatch/test_ingest_*.py)
T2 other sources + warehouse + quality + snapshot (engine/vlkit/ratewatch/{sources,warehouse,quality,snapshot}.py, tests)
T3 analytics formulas (engine/vlkit/ratewatch/analytics.py, tests with hand-computed values) + TS port for the planner (web/src/lib/ratewatch/calc.ts)
T4 web pages + charts (web/src/app/(ratewatch)/**, web/src/components/ratewatch/**)
T5 AI planner + Langfuse + OCR (web/src/app/api/ratewatch/**, web/src/lib/ratewatch/agent/**, web/instrumentation.ts)
T6 AWS infra + CI (infra/**, Dockerfile.web, Dockerfile.pipeline, .github/workflows/deploy.yml)
T7 docs (Documentation .docx), EN deck + VI summary, demo script, prompt log (outside repo until owner approves)
T8 e2e QA (Playwright judge flows, mobile, no dev routes, headers, console errors) + cross-model reviews
