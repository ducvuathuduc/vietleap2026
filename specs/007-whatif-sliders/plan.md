# Implementation Plan: What-if sliders page

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 4 h · **Owner role**: DE (AN validates units/wording)

## Technical context
Engine `engine/vlkit/models.py` (`fit_drivers`, `what_if`), tools `engine/vlkit/tools.py` (`T.what_if`, `T.Context`), API `api/routes/analysis.py` (prefix `/api/datasets/{ds_id}`; `whatif`, `whatif_curve`, `drivers`), schemas `api/schemas.py` (`WhatIfRequest`), store `api/store.py` (`ds.whatif`, `out_dir`), report `engine/vlkit/report.py` (Impact slide).
Web: `web/src/app/(dashboard)/drivers/page.tsx` (existing slider), `web/src/components/ui/slider.tsx` (installed), `insight-chart.tsx`, `web/src/lib/api/{client,types}.ts`, `web/src/lib/nav.ts` (from 005) or `app-sidebar.tsx`, `web/src/lib/tour-steps.ts`.

## Constitution check
| Principle | Compliance |
|---|---|
| I | all displayed numbers returned by the API; saved scenarios store API output |
| II | CI90 from bootstrap on every result; "uncertain direction" badge when CI crosses 0 |
| III | caveat on card + deck; wording "liên đới theo mô hình" |
| IV | installed shadcn components only; new page follows dashboard-01 layout (`PageShell`) |
| VI | pydantic bounds (1–5 changes, ±30 %), dataset id via store (no path input), scenarios file name fixed, ≤ 4 entries, rate limit applies to new POSTs (add paths to `api/security.py` limited set) |
| VII | no LLM involved |
| VIII | test-first engine function + API |

## Design
```
what_if_multi(model, changes):
  wi = model["whatif"]; dz_j = mean_j * pct_j / 100 / sd_j
  point = Σ beta_j * dz_j ; draws_i = Σ_j boot_j[i] * dz_j   # same i → joint distribution
  log target: pct = (exp(point)-1)*100, CI = pct of (exp(draws)-1)*100
  else: pct = point / base * 100, CI = draws / base * 100
  range_warnings: features whose mean*(1+pct) leaves [min, max] (store min/max in fit_drivers if absent)
```
`fit_drivers` must persist `min`/`max` per numeric feature (additive change to `whatif.json`; older files → warnings skipped).

## Files to touch
`engine/vlkit/models.py`, `engine/vlkit/tools.py`, `engine/vlkit/report.py` (Impact slide reads `scenarios.json`), `api/schemas.py` (`WhatIfChange`, `WhatIfScenarioRequest`, `SavedScenario`), `api/routes/analysis.py` (3 routes), `api/security.py` (rate-limited paths), `tests/test_whatif_multi.py` (new), `tests/test_contracts.py`,
`web/src/app/(dashboard)/whatif/page.tsx` (new), `web/src/lib/whatif.ts` (+ `.test.ts`, debounce/abort + localStorage helpers), `web/src/lib/api/{client,types}.ts`, `web/src/app/(dashboard)/drivers/page.tsx` (VI strings), nav + tour files, `specs/001-vietleap-insight-kit/contracts/openapi.json` (regenerate).

## Open-source reuse
numpy (BSD), FastAPI/pydantic (MIT), shadcn Slider (MIT, installed). Considered: DoWhy (MIT) for causal what-if — rejected: needs a causal graph the team cannot defend in 27 h; would invite causal claims (constitution III).

## Security considerations
- **A04 Insecure design / LLM09**: bounded inputs prevent absurd extrapolation; caveat mandatory.
- **A01**: scenarios file path derived from validated dataset id; no user path.
- **A05/DoS**: debounce + client throttle; server rate limit; O(200×5) compute.
- **A03/XSS**: scenario names ≤ 60 chars, rendered as text; stored JSON escaped by `json.dumps`.
