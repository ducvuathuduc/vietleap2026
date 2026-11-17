# Tasks: 005 Ctrl+K command palette

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

- [x] T501 `80bd00d` Official shadcn command/input-group installed via CLI, generated components unchanged. cmdk MIT recorded.
- [x] T502 `80bd00d` RED→GREEN matching, URL uniqueness, what-if encoding/bounds tests.
- [x] T503 `80bd00d` Shared NAV used by sidebar and command menu.
- [x] T504 `80bd00d` Palette mount, header button, interaction cleanup, and keyboard listener.
- [x] T505 `80bd00d` Analyst question prefill in a Suspense boundary, without automatic sending.
- [x] T506 `80bd00d` Command button tour step.
- [x] T507 `80bd00d` Chromium verified inspect cleanup, accent-free filtering, Enter navigation, analyst prefill and Escape. No console/page errors. [Screenshot](../../docs/screenshots/command-palette.png)
- [x] T508 `80bd00d` Publish feature and docs.

Bundle gzip increase relative to the previous build remains unmeasured.

## Dependencies
T501, T502 first (parallel) → T503 → T504 → T507 → T508; T505, T506 any time after T503.
