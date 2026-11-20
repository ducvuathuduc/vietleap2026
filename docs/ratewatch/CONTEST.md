# VietLeap Hackathon 2026 "From Data to Decision" — shared context for research tasks

Read this first. Facts below are from the official guidebook (full text: C:\Users\dieut\.kiro\vietleap-final\guidebook.txt,
PDF next to it, source https://vietleap2026.com/guidebook/ -> heyzine flipbook) and the challenge-briefing slides shown on 20/11/2026.
Now: 20/11/2026 ~10:30 Asia/Saigon. Submission deadline: 21/11/2026 13:00. Pitch 13:15-15:15 same day.

## The challenge (briefing slide, 20/11 09:00)
"USE DATA TO IMPROVE POLICY OR ECONOMIC DECISIONS. Build a functioning product that:
- uses real data,
- answers a relevant question from the [text cut off in photo, likely: the team's field / the real world],
- applies tools from the team's discipline(s)."
No fixed dataset or topic was announced in what we have. Domain choice is open.

## What to submit (guidebook p.3 + slide)
- Final product: any format, shared so judges can open and use it.
- Documentation: open, editable file with viewable edit history (e.g. Word / Google Docs): research question, data used and
  limitations, analysis results, record of AI use, who did what.
- Source code: open-source, if code is used.
- AI prompts used.
- Final presentation in English, with a short Vietnamese summary at the end.
- File names: TeamName_Product, TeamName_Documentation, TeamName_Code.
- Data rule: cite the source of all data; licensed/restricted data must follow the provider's terms.
- AI rule: AI/LLM allowed but must be declared; core reasoning and final decisions must be the team's own work.

## Marking (100 points)
- Product 40: clear question that fits the theme; real, well-sourced data; methods that suit the question; a product that works
  and supports a decision; clear, open documentation.
- Presentation 40: clear, persuasive pitch; confident answers to questions.
- Teamwork 20: multidisciplinary approach, every member contributes, coherent final outcome.
Teams were formed by the organisers based on each student's expertise (business / social-science students are the main intake;
our teammates' disciplines are not yet known to us).

## Judges (guidebook p.13)
- Dr. Sacha Dray — Economist, World Bank Vietnam (macro, trade, fiscal policy, tax, tax compliance; ran the Dashboard workshop today).
- Dr. Pham Thai Binh — Vice Dean/Vice Director, Sustainable Finance Institute, UEH (text garbled in PDF).
- Ms. Nguyen Ngoc Phuong Trang — Acting Director, Securities Services, Shinhan Bank Vietnam.
- Dr. Tuan Chu — Associate Program Manager, Undergraduate Business Program, RMIT Vietnam; Economist, EPNet (AVSE Global).
- Dr. Doan Vu Nguyen — Director, Undergraduate programme in International Trade and Customs Management, School of Public Finance, CELG, UEH.

## Mentors (guidebook p.7-11; availability 20-21/11)
Nadia Doytch (CUNY: FDI, energy & environment, financial development) · Nguyen Phuc Canh (UEH: institutions, macro policy impact,
environmental & energy economics) · Nguyen Tien Viet (LSE: clean energy, digital tech, twin transition) · Nguyen Van Phuc (WSU:
econometrics, policy analysis, AI, corporate finance, fintech, CBDC) · Le Minh Phuong (VinUni: growth and income/wealth inequality) ·
Dang Hoang Nhat Tam (UEH: macro, energy economics, uncertainty, fiscal policy uncertainty, shocks) · Nguyen Tri Dung (Coventry: macro,
behavioural economics, financial economics; ex National Assembly Economic Committee) · Karan Vishwanath (Leicester: corporate
governance, ESG, M&A) · Luu Duc Canh (Tasco: data engineering, lakehouse) · Dinh Xuan Phan Anh (FiinGroup: FiinQuant library,
Alpha Radar alert bot, AI agent chatbot for market statistics).
Workshops: Tasco data pipelines (4 stages: ingestion, storage, transform, serving); Chi-Yu Lee computer vision / object tracking;
Nguyen Tien Viet "How can data be transformed into decisions": open data, national land database, property transaction data linked
with other datasets, case studies on transport accessibility, flood risk, education quality.
Partner: FiinGroup (we have a FiinQuant Professional account).

## Owner's goal for this research (anh Thanh, team lead)
- Pick a domain + data + product that is clearly different from what most teams will build ("other teams will also build a
  dashboard like ours"). Needs a "wow" for judges, both in technology and in use case.
- Preferably something anyone can use to make a better financial/economic decision, tied to an urgent, current problem in Vietnam.
- AI (Vercel AI SDK in the Next.js app) is only a quick add-on feature, not the core.
- Must be buildable and demo-able by 21/11 13:00 on a weak laptop (2 CPU, 7 GB RAM).

## Hard rules from the owner
- Never invent numbers. Every number shown must come from a cited real source through our pipeline.
- Judges must not see dev tools (SQL console, pipeline buttons, debug JSON, table names, model badges).
- No "AI-slop" UI or copy: plain, bright, fast; headings state a conclusion with number, period and source.
- FiinQuant terms: keep raw data internal; publish only aggregates with attribution.
- Scraping: respect robots.txt, add delays, never bypass captcha/login.

## Current project (repo C:\Users\dieut\Desktop\Money\vietleap, branch feat/vn-monitor)
"Vietnam Macro-Financial Monitor": Python engine (engine/vlkit, DuckDB star schema, business rules), FastAPI (api/), Next.js 16 +
shadcn dashboard-01 (web/), bilingual deck generator (slides/), docs/ (BUSINESS_RULES, DATA_SOURCES, WORKFLOW, PLAYBOOK, CONTEST_ANALYSIS),
specs/001-012 (spec-kit). Sources already wired: FiinQuant, NSO, SBV, WDI, press reports, TinyFish.

## Keys and tools on this machine (never print or copy secret values)
- FiinQuant: FIINQUANT_USERNAME / FIINQUANT_PASSWORD in the repo's .env.local; vendored wheel FiinQuantX 0.1.73 in the repo's .venv.
- TinyFish: TINYFISH_API_KEY (user env var and .env.local). Agent API https://agent.tinyfish.ai/v1/automation/run|run-async|run-sse,
  header X-API-Key, about $0.016 per step, 2 concurrent runs. TinyFetch POST https://api.fetch.tinyfish.ai is free and reads pages
  that curl gets 403 on.
- LLM keys: GROQ_API_KEY (model openai/gpt-oss-120b works), OPENAI_COMPATIBLE_* in .env.local.
- Exa: no key on this machine yet. Use your own web search tool and TinyFetch.

## Known source behaviour (verified Nov 2026, do not re-discover)
- FiinQuantX 0.1.73 needs aiohttp, matplotlib, signalrcore, requests. get_financial_statement is missing (0.1.73) / HTTP 504 (0.1.71).
  Index tickers: VNINDEX, VN30, HNXIndex, UpcomIndex. get_ratios for banks only ~2021+. Valuation (PE/PB stock/sector/index),
  foreign flows, breadth and realtime stream work. Plan: 400k requests/month, 1,500/min.
- nso.gov.vn monthly reports are server-rendered prose (robots allow). sbv.gov.vn credit-by-sector has HTML tables.
  dttktt.sbv.gov.vn unreachable; mof.gov.vn is a JS SPA TinyFish could not read; gso.gov.vn and fia.mpi.gov.vn do not resolve.
- TinyFish "COMPLETED" does not prove data was extracted; Vietnamese titles can come back garbled.
