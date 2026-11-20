# R-AUDIT Read-only audit: how strong is our current project as a base for a new, differentiated product by 21/11 13:00
Repo: C:\Users\dieut\Desktop\Money\vietleap      Base: e19f05d (branch feat/vn-monitor)
This is research, not coding. Do NOT edit anything in the repo.

## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md first (challenge, rubric, judges, owner rules, deadline).
- The owner fears our "Vietnam Macro-Financial Monitor" is the same dashboard every other team will build. He may switch domain.
  Other workers are researching domains (demand side) and data (supply side) in parallel. Your job is the technology side.
- Start points: AGENTS.md, web/AGENTS.md, docs/MASTER_PLAN.md, docs/WORKFLOW.md, docs/PLAYBOOK.md, docs/BUSINESS_RULES.md,
  docs/DATA_SOURCES.md, docs/ROADMAP.md, specs/README.md, engine/vlkit/, api/, web/, slides/, tests/, run.py, Makefile, .github/.

## Answer these (write AUDIT.md in this task folder)
1. Architecture map: each layer (engine, api, web, slides/deck, specs, CI), entry points, and the data flow from source to the
   judge pages (file paths). Rough size (files / LOC per layer) and test count.
2. Reusable building blocks for ANY new domain: connectors (FiinQuant, TinyFish, NSO/SBV scrapers, generic HTTP/file), DuckDB
   bronze/silver/gold + star schema, business-rule register, provenance/evidence checks, copy lint, judge-page framework,
   bilingual deck/brief generator, export, Q&A guard, what-if sliders, province map. For each: path, maturity (works / partial /
   stub, with evidence), and hours to reuse for a new domain.
3. AI today: every LLM integration (web Q&A page, api agent, Groq/OpenAI-compatible), whether the Vercel AI SDK (`ai`, `@ai-sdk/*`)
   is installed and used (versions from web/package.json and node_modules), and the fastest place to add one AI add-on feature
   (for example grounded explanation or tool-calling over our own data) with an hours estimate. Check the AI SDK docs in
   node_modules or the official docs for the installed major version before you claim an API.
4. Honest scoring of the CURRENT product against the rubric (Product 40 / Presentation 40 / Teamwork 20) and the submission list
   (documentation with edit history, AI prompts, English deck + Vietnamese summary, open-source licence, product judges can open).
   What would judges find generic or weak? What is genuinely strong and rare among student teams?
5. Pivot cost: if we keep the stack but change the domain/product, what is the critical path and hours for: new sources ->
   pipeline -> 2-3 judge pages -> deck -> docs -> hosting judges can open. List the top 5 technical risks (Next 16 build,
   2-CPU laptop, hosting, FiinQuant terms, data gaps) with the mitigation already in the repo, if any.
6. Hygiene for submission: files in git that must not be public (secrets, raw licensed data, large files, internal notes),
   and anything that would embarrass us on a public repo.

## Rules
- Read-only. No file edits in the repo, no git commands except read-only ones (log, show, diff, ls-files, status).
- You may run `.\.venv\Scripts\python.exe -m pytest -q tests` once. Do NOT run `npm run build` or `npm run dev`.
- Do not kill any process you did not start. Never print secret values from .env files.
- Cite file paths (and line numbers where useful) for every claim. Mark anything you did not verify as [unverified].
- Timebox: 50 minutes. If time runs out, write what you have.
- Write AUDIT.md (max ~250 lines) and REPORT.md (max 20 lines, the key conclusions) in THIS folder. No files in the repo.
