# Tasks: 005 Ctrl+K command palette

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

- [ ] T501 `cd web && npx shadcn@latest add command` (verify base-nova registry provides it; record cmdk MIT in `docs/licenses.md`). Done when build passes with the generated file untouched.
- [ ] T502 Test-first `web/src/lib/nav.test.ts`: every `NAV` url unique; `filterCommands("chat luong")[0].url === "/quality"`; `filterCommands("what-if")` includes `/drivers`.
- [ ] T503 `web/src/lib/nav.ts` (move NAV out of `app-sidebar.tsx`, add keywords VI/EN) → T502.
- [ ] T504 `web/src/components/command-menu.tsx` + mount in `web/src/app/(dashboard)/layout.tsx`; header hint button in `site-header.tsx`; inspect/tour teardown on open → T501, T503.
- [ ] T505 [P] `web/src/app/(dashboard)/analyst/page.tsx` `?q=` pre-fill (Suspense per Next 16 docs).
- [ ] T506 [P] `web/src/lib/tour-steps.ts` step for ⌘K; `tour-steps` test updated.
- [ ] T507 Headless Chromium smoke (Ctrl+K → type → Enter; Esc; 0 console/CSP errors); screenshot `docs/screenshots/command-palette.png`.
- [ ] T508 Commit + push "feat(web): T501–T507 Ctrl+K command palette (shadcn Command/cmdk)"; tick; update `specs/README.md`.

## Dependencies
T501, T502 first (parallel) → T503 → T504 → T507 → T508; T505, T506 any time after T503.
