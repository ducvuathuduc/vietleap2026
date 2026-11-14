# VietLeap Insight Kit — Spec index

The specification follows **GitHub Spec Kit** (Spec-Driven Development, [github/spec-kit](https://github.com/github/spec-kit), MIT).
Start here, in this order:

| # | Document | What it answers |
|---|---|---|
| 1 | [`.specify/memory/constitution.md`](../.specify/memory/constitution.md) | Non-negotiable principles (real numbers only, tested insights, no causal claims, OSS UI as-is, security, offline, tests + push per feature) |
| 2 | [`specs/001-vietleap-insight-kit/spec.md`](../specs/001-vietleap-insight-kit/spec.md) | User stories P1–P3, acceptance scenarios, FR/NFR, success criteria, edge cases, open questions |
| 3 | [`specs/001-vietleap-insight-kit/tasks.md`](../specs/001-vietleap-insight-kit/tasks.md) | **Real status**: done (with commit) / pending, dependencies, priorities — pick the next unchecked task |
| 4 | [`specs/001-vietleap-insight-kit/plan.md`](../specs/001-vietleap-insight-kit/plan.md) | Technical context, constitution check, architecture (mermaid), every module, API table, CLI, env vars |
| 5 | [`specs/001-vietleap-insight-kit/data-model.md`](../specs/001-vietleap-insight-kit/data-model.md) | Medallion layers, OBT/Star/Snowflake/Data Vault/Conformed, entities, output files |
| 6 | [`specs/001-vietleap-insight-kit/contracts/`](../specs/001-vietleap-insight-kit/contracts/) | `openapi.json` (generated: `python tools/export_openapi.py`), JSON Schemas `pipeline`, `lineage`, `conformed`, `brief`, `story` — checked by `tests/test_contracts.py` |
| 7 | [`specs/001-vietleap-insight-kit/research.md`](../specs/001-vietleap-insight-kit/research.md) | Technology decisions, rationale, alternatives |
| 8 | [`specs/001-vietleap-insight-kit/quickstart.md`](../specs/001-vietleap-insight-kit/quickstart.md) | Contest-day command runbook |
| 9 | [`docs/SRS.md`](SRS.md) | IEEE 830-style SRS + traceability matrix FR → code → tests |
| 10 | [`SECURITY.md`](../SECURITY.md), [`docs/security/threat-model.md`](security/threat-model.md) | STRIDE threat model, controls status |
| 11 | [`docs/CONTEST_ANALYSIS.md`](CONTEST_ANALYSIS.md) | Contest facts, judges, likely themes, scoring strategy |
| — | [`docs/MASTER_PLAN.md`](MASTER_PLAN.md) §0, [`docs/PLAYBOOK.md`](PLAYBOOK.md), [`docs/CONTEXT.md`](CONTEXT.md), [`AGENTS.md`](../AGENTS.md) | Status log, team runbook, context, agent rules |

**Workflow for a new change** (Spec Kit): update `spec.md` (story/FR) → `plan.md` if architecture changes → add a task in `tasks.md` →
implement + tests → `pytest -q tests`, `cd web && npm test && npm run lint && npm run build` (sequentially) → commit → push →
tick the task with its commit hash.
