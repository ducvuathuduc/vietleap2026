# Implementation Plan: Screenshots + demo video script

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 3 h (DE 2 h scripts, ST/PO 1 h storyboard + narration) · **Owner role**: ST (storyboard), DE (scripts)

## Technical context
Python Playwright (Apache-2.0, `requirements.txt`), Chromium headless shell in `.tools/ms-playwright` (`tools/setup_env.sh`, `tools/env.sh`), Makefile, web routes (`web/src/components/app-sidebar.tsx` nav list), selectors from `web/src/lib/tour-steps.ts` (`data-tour=…`), `web/src/components/site-header.tsx` buttons (`data-tour="story-button"`).

## Constitution check
| Principle | Compliance |
|---|---|
| I | screenshots/video show live engine output only; no edited numbers; index records dataset + commit |
| IV | no UI changes |
| V | Playwright Apache-2.0; optional pngquant (GPL-3 tool, not shipped — run only locally, or skip) |
| VI | screenshots only of open/practice data; no secrets on screen; scripts target `--base` given by the operator (local) |
| VII | runs offline against local api/web |
| VIII | script smoke test (`--dry-run` lists routes) in pytest without browser |

## Design
- `tools/screenshots.py`: `with sync_playwright() as p: b = p.chromium.launch(); ctx = b.new_context(viewport={"width":1440,"height":900}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")`; `ctx.add_init_script("localStorage.setItem('<KEY>', '<ds>')")` (key read from `dataset-provider.tsx` constant at T1001); for each route: goto, wait `networkidle` + no `[data-slot=skeleton]`, assert no `[data-error]`/empty-state text, `page.screenshot(full_page=False)`.
- `tools/record_demo.py`: context with `record_video_dir="out/demo"`, `record_video_size={"width":1280,"height":720}`; steps from `docs/DEMO_SCRIPT.md` front matter (YAML list: `t`, `action`, `selector`, `text`) parsed with PyYAML.
- `docs/DEMO_SCRIPT.md` storyboard (90 s): 0–10 s Tổng quan KPIs → 10–35 s "Câu chuyện" 3 steps → 35–55 s Hỏi AI on top chart (offline answer) → 55–70 s Pipeline lineage + join coverage → 70–85 s Quyết định → 85–90 s Xuất báo cáo dialog.

## Files to touch
`tools/screenshots.py` (new), `tools/record_demo.py` (new), `docs/DEMO_SCRIPT.md` (new), `docs/screenshots/*.png` + `README.md` (new), `Makefile`, `README.md`, `tests/test_tools_scripts.py` (new, `--dry-run`).

## Security considerations
- **A05**: scripts never disable CSP or inject scripts beyond `localStorage` init.
- **A02/secret exposure**: check `web/.env.local` values never rendered; screenshot review step in tasks.
- **Privacy**: practice/open datasets only.
