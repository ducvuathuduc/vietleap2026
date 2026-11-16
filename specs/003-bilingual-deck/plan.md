# Implementation Plan: Bilingual deck & pitch

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 4 h · **Owner role**: DE (code) + ST/PO (review every VI/EN string)

## Technical context
- `engine/vlkit/report.py` (`build_deck`, `pitch_md`, `summary_md`, `build_all`, `PITCH_TIMING`), `engine/vlkit/fmt.py` (`num`, `pct` with `lang`; `p` without),
  `engine/vlkit/profile.py caveats()`, `engine/vlkit/domains.py CAVEATS`, `engine/vlkit/pipeline.py` (builds `results`, calls `report.build_all`).
- CLIs `run.py`, `de.py`; API `api/routes/datasets.py` (`EXPORTS`, upload form), `api/routes/pipeline.py` (`IngestIn`), `api/jobs.py` (passes options to `pipeline.run` / `run_file`).
- Web `web/src/components/app-sidebar.tsx` (`documents` list with `file("deck")` …), `web/src/components/nav-documents.tsx`, `web/src/lib/api/client.ts fileUrl` kinds, `web/src/components/ui/toggle-group.tsx` (installed).

## Constitution check
| Principle | Compliance |
|---|---|
| I Real numbers | Same engine values in both languages; only formatting differs; SC-302 test parses and compares |
| II/III | Test names, p, effect and the causal caveat are in both string tables (VI: "liên đới, không phải nhân quả") |
| IV OSS UI | shadcn ToggleGroup as installed; no styling |
| V OSS | no new deps (no MT library) |
| VI Security | `lang` validated as `Literal["vi","en","both"]` (pydantic) / `z.enum` (web); export kinds stay an allowlist (path traversal unchanged) |
| VII Offline | fully offline |
| VIII | test-first tasks below |

## Design
- `engine/vlkit/i18n.py`: `STRINGS = {"en": {...}, "vi": {...}}`, `t(lang, key, **kw)`; keys for every header/kicker/card title, `PITCH_TIMING` labels, judge-question hints, fallback phrases. A unit test asserts both dicts have identical key sets.
- `report.py`: `build_deck(..., lang="en")` picks `title_{lang}`, `sentence_{lang}`, `so_what_{lang}`…, `caveats` vs `caveats_vi`; `pitch_md(..., lang="vi")`; `build_all(..., lang="both")` writes the file matrix of FR-303 and returns `files` incl. `deck_vi`, `pitch_en`.
- Caveats: change `domains.CAVEATS` values and `profile.caveats()` messages to `{"en": str, "vi": str}` pairs; `pipeline.py` emits `caveats` (EN, unchanged consumers) + `caveats_vi`.
- API: `EXPORTS` += `deck_vi` (`deck.vi.pptx`), `pitch_md` (`pitch.md`, `text/markdown`), `pitch_en` (`pitch.en.md`); upload form field `lang`, `IngestIn.lang` default `"both"`.
- Web: `fileUrl` kind union extended; sidebar Exports gets ToggleGroup EN/VI (state in `localStorage` key `vlk.lang`), links switch; disabled when `results.json.files` lacks the variant (read through `api.dataset(id)` summary which already returns `files` — verify in T308).

## Files to touch
| Path | Change |
|---|---|
| `engine/vlkit/i18n.py` (new) | string tables |
| `engine/vlkit/report.py` | lang plumbing, file matrix |
| `engine/vlkit/fmt.py` | `p(pv, lang)` |
| `engine/vlkit/domains.py`, `engine/vlkit/profile.py`, `engine/vlkit/pipeline.py` | bilingual caveats, `caveats_vi` |
| `run.py`, `de.py`, `api/routes/datasets.py`, `api/routes/pipeline.py`, `api/jobs.py` | `--lang` / `lang` |
| `web/src/lib/api/client.ts`, `types.ts`, `web/src/components/app-sidebar.tsx`, `nav-documents.tsx` | toggle + links |
| `tests/test_deck.py`, `tests/test_i18n.py` (new), `tests/test_contracts.py` | tests |
| `specs/001-vietleap-insight-kit/contracts/openapi.json` | regenerate |

## Open-source reuse
python-pptx (MIT), shadcn ToggleGroup (MIT, installed). Rejected: `googletrans`/MT APIs (network, licence/ToS, non-deterministic → violates I/VII).

## Security considerations
- **A01/A05**: new export kinds via allowlist dict only; filenames fixed.
- **A03**: `lang` is an enum, never interpolated into paths except via the fixed mapping.
- **LLM09 Misinformation**: no machine translation of numbers or claims; reviewed static strings only.
