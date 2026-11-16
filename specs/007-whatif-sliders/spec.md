# Feature Specification: What-if sliders page (multi-driver scenarios with 90% interval)

**Feature Branch**: `007-whatif-sliders` (lands on `main`) · **Created**: 2026-11-16 · **Status**: Draft · **Priority**: P2 (rubric D "quantified recommendation" — pitch §4.6 slide 8 uses what-if)
**Supersedes**: `specs/001-vietleap-insight-kit/tasks.md` T052.

## Context (verified 2026-11-16)
- Engine `engine/vlkit/models.py`: `fit_drivers` fits a standardised Ridge with **200 bootstrap resamples**; each feature stores `beta`, `boot` (column `j` of the same resample matrix `B` → draws are aligned across features), `mean`, `sd`, `numeric`; `what_if(model, feature, pct_change)` returns `target_change_pct`, `ci90_pct` (5th/95th percentile), `target_change_abs`, `baseline_target_mean`, interpretation "model-based association … not a causal guarantee"; log target handled with `exp`.
- API: `POST /api/datasets/{id}/whatif {feature, pct_change ∈ [-90, 500], target?}`, `GET …/whatif/curve?feature=` (−30…+30 step 5), `GET …/drivers` (`whatif_features`).
- Web: `/drivers` page already has **one** shadcn `Slider` (−30…+30 %) for **one** feature, with English labels ("What-if scenario", "Move the slider…") — violates the Vietnamese-text rule (constitution IV).
- No way to change several drivers at once, compare scenarios, or push a scenario into the deck.

## User Scenarios & Testing

### User Story 1 — Move several drivers, see one predicted change with CI90 (Priority: P1)
As the **PO**, I want a "Kịch bản what-if" page with a slider per top driver (up to 5 numeric drivers ranked by permutation importance) and one result card (Δ% target, 90% interval, absolute change, baseline), so I can quantify a policy package ("+10% FDI, +5% urbanisation").

**Acceptance**
1. **Given** a dataset with `whatif.json`, **When** I open `/whatif`, **Then** I see ≤ 5 sliders (range −30…+30 %, step 1, default 0) labelled with the feature name and its current mean (from `whatif_features`).
2. **When** I move sliders, **Then** after 250 ms debounce `POST /whatif/scenario` returns the joint change: point = Σ βⱼ·Δzⱼ, interval = 5th/95th percentile of Σ Bᵢⱼ·Δzⱼ over the *same* resample i (log target → `exp(·)−1`). The card shows Δ%, CI90, absolute change on the baseline mean, and the caveat "liên đới theo mô hình, không phải nhân quả".
3. **Given** all sliders at 0, **Then** result is 0 with CI [0, 0] and the card says "Chưa thay đổi".
4. **Given** the interval crosses 0, **Then** the card shows a "Không chắc chắn về chiều tác động" badge.

### User Story 2 — Save & compare scenarios (Priority: P2)
**Acceptance**: "Lưu kịch bản" stores `{name, changes, result}` in `localStorage` (per dataset); a table compares up to 4 saved scenarios (Δ%, CI90); "Xoá" removes one. Numbers in the table are the API results, never recomputed client-side.

### User Story 3 — Scenario into the deck & AI (Priority: P3)
**Acceptance**: "Đưa vào deck" posts the scenario to `POST /api/datasets/{id}/whatif/scenarios` (persisted to `out/<ds>/scenarios.json`, max 4); the deck's Impact slide (report.py) lists saved scenarios with CI. The result card is a `data-insight-target` (`whatif`) so "Hỏi AI" explains it offline.

### Edge cases
- Dataset without drivers model (`whatif.json` missing or < 2 numeric features) → empty state "Chưa có mô hình drivers — cần ≥ 2 biến số" with link to `/drivers`.
- Feature with `sd == 0` → slider disabled ("biến không đổi").
- Mean ≈ 0 or negative (e.g. net lending % GDP) → % change of the mean is misleading: show the slider in **absolute units** (Δ = k·sd steps) and label it; [NEEDS CLARIFICATION: confirm with AN which unit judges expect for negative-mean fiscal ratios].
- Correlated drivers moved together → joint bootstrap handles coefficient covariance, but the card warns when two moved drivers have |r| > 0.8 (from `drivers` correlations if available, else omit).
- Extrapolation: sliders limited to ±30 %; if the implied value leaves the observed [min, max] → "ngoài phạm vi dữ liệu" warning.
- Categorical drivers → not sliders (Ridge one-hot); listed as "giữ nguyên".
- Rapid slider moves → debounce + abort previous request (AbortController); rate limit 60/min respected (debounced calls ≈ ≤ 4/s only while dragging; add client throttle 2/s).

## Requirements
- **FR-701**: `engine/vlkit/models.py what_if_multi(model, changes: list[{feature, pct_change}]) -> dict` using aligned bootstrap columns; same output keys as `what_if` + `changes`, `range_warnings`.
- **FR-702**: `POST /api/datasets/{id}/whatif/scenario` (pydantic: 1–5 changes, `pct_change ∈ [-30, 30]`, unique features) → 200 / 422 / 404.
- **FR-703**: `POST|GET /api/datasets/{id}/whatif/scenarios` persist ≤ 4 named scenarios in `out/<ds>/scenarios.json`; `report.py` Impact slide reads it.
- **FR-704**: New page `web/src/app/(dashboard)/whatif/page.tsx` built only from installed shadcn components (Card, Slider, Badge, Table, Button, Empty) + `InsightChart` for a tornado-style hbar of each driver's individual contribution (from per-feature `what_if`, values from API).
- **FR-705**: Sidebar/`NAV` entry "Kịch bản what-if" (`/whatif`), tour steps, command palette item (005).
- **FR-706**: Translate `/drivers` what-if card strings to Vietnamese (keep EN technical terms in parentheses).

### Non-functional
- **NFR-701**: API p95 ≤ 150 ms (200 draws × ≤ 5 features, numpy).
- **NFR-702**: No new dependency.

## Success criteria
- **SC-701**: pytest: `what_if_multi` with one change equals `what_if` (point and CI to 1e-9); two changes equal Σ of aligned draws; log-target case; validation errors.
- **SC-702**: Web unit test for debounce/abort helper; headless smoke: moving 2 sliders updates the card; 0 console/CSP errors.
- **SC-703**: PO can state a quantified package with CI in the pitch dry run (18/11).
