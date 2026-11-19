# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/); the project has no tagged release yet, so everything is under
**Unreleased**, newest first within each section. Commit hashes refer to `main` on https://github.com/ducvuathuduc/vietleap2026.

## [Unreleased]

### VN Macro-Financial Monitor · 2026-11-20

- Added incremental FiinQuant landings, deterministic NSO and SBV extractors, TinyFish with spend controls, and evidence-tagged press and PDF observations.
- Added the `vn_monitor` DuckDB star model, rule results, provenance, a validated publication manifest, and six judge sections with five sector pages. The overview, ASEAN and sector pages publish their main content in server-rendered HTML. Unknown sector routes return 404.
- Added a bilingual 13-slide pitch and Vietnamese executive brief via `de.py monitor --deck`, plus a business-rule register and a source-by-source publication record. Hosting, mobile/A4 checks and confirmation of FiinQuant publication rights remain open.

### Added
- Open-source README (badges, architecture, data-engineering and analysis principles), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
  (Contributor Covenant 2.1), issue and pull-request templates, this changelog; `docs/WORKFLOW.md` §0 maps the mentor's 6-step hackathon scope
  to the kit and lists the gaps (2026-11-17).
- Feature 003 — bilingual deck and pitch: `--lang vi|en|both` for `run.py`, `de.py file|run` and the API; `deck.pptx` (EN) / `deck.vi.pptx`,
  `pitch.md` (VI) / `pitch.en.md`; reviewed EN/VI string table `engine/vlkit/i18n.py`; `caveats_vi`, `caveat_vi`, `issue_vi`;
  export kinds `deck_vi`, `pitch_md`, `pitch_en`; EN/VI export toggle in the dashboard sidebar (`74de518`, `5aa4194`, `4e098e5`).
- Feature 002 — policy-question-first story: slide 2 "Decision question" from `brief.json` (who decides, success KPI), insight slides
  EVIDENCE → FOR THE DECISION → LIMITATION, weak evidence labelled, Limitations slide with real coverage counts, pitch opens with the
  decision question (`bdcb571`); `GET /api/datasets/{ds}/brief`, story question and limits in the web "Câu chuyện" (`76c9e37`).
- Join coverage of conformed dimensions: `GET /api/datasets/{ds}/conformed`, keys in `/models`, coverage card and Conformed tab (`7ecc309`).
- Spec Kit layout: constitution (8 principles), specs 001–011 with plans, tasks and contracts, `specs/README.md` index, `docs/ROADMAP.md`
  (`aef4d05`, `005f6cb`, `fefb26a`, `585a3fd`, `8eb44a3`, `65faeb3`).
- GitHub Actions CI (pytest, OpenAPI drift check, web test/lint/build) and Security (gitleaks, pip-audit, npm audit, CodeQL), Dependabot,
  Dockerfiles and `docker-compose.yml` (`a0a920e`).
- Incremental bronze load by `_row_hash` (`--mode replace|append|incremental`) (`1b3a40d`); district-level geography (`74d2d98`);
  conformed dimensions across sources with province 63 → 34 mapping (`726fe1c`).
- Computer-vision counting scenario (YOLOv8n + ByteTrack → counts CSV; `--events` mode without torch) (`8024f92`).
- Deck slides for data pipeline, data model, data quality, provenance and policy recommendation, with text fitting and an overflow
  check; Marp `pitch.md` (`d3208b3`).
- Web: auto-insight story with number verification (`253f761`); guided tour and "Hỏi AI" explain mode (`b225042`); AI Analyst with
  read-only tools, Groq or any OpenAI-compatible endpoint, offline mode (`953057a`); Pipeline, Sources, Quality, Model, SQL and Decision
  pages on shadcn/ui `dashboard-01` (`0e8be9b`).
- Problem statement → `brief.json`, 7 scenario packs and sample briefs (`2609808`); Makefile commands (`a4483a2`).
- Data-engineering layer: connectors (file, API, SQL, scrape, social, CV) → DuckDB medallion → quality → OBT / Star / Snowflake /
  Data Vault → lineage and provenance (`2e9674c`); initial insight kit (engine, API, web scaffold) (`7e6a9c3`, `1d7c925`).
- Documentation: master plan, SPEC, contest analysis, workflow, playbook, security policy and STRIDE threat model, open-question research
  (`cedbfbb`, `004caef`, `b6e6b6b`, `86f194b`, `a712972`, `2444157`, `e938a12`, `40a8537`).

### Changed
- Contest schedule in the docs and scenario packs updated to the agenda published on vietleap2026.com as of 2026-11-17 (LSE talk 19/11 15:30,
  World Bank dashboard workshop 20/11 09:30, mentor check-in #1 20/11 16:00).
- Engine Vietnamese sentences and recommendations now carry the same numbers as the English ones, with Vietnamese number formatting
  (`p<0,001`, `1.234,5`); deck title wording changed from "What drives X?" to "What is X associated with?" (`5aa4194`).

### Fixed
- CI: hard-exit with pytest's real status after the summary to avoid a teardown abort from native threads (`6f52404`).
- Already-normalised province columns are no longer normalised twice (`757df0c`).

### Security
- HTTP hardening: security headers and CSP, restricted CORS, streamed uploads with size and type limits, rate limits (`0eec8d3`).
- SSRF and local-path guards for sources submitted through the API (`c1a263b`).
- Read-only SQL: DuckDB `read_only`, external access disabled, file/env functions blocked, query timeout (`1147a5d`).
