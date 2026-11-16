# Implementation Plan: Ctrl+K command palette

**Spec**: [spec.md](spec.md) · **Date**: 2026-11-16 · **Estimate**: 2.5 h · **Owner role**: DE

## Technical context
Next.js 16.4 App Router (read `web/AGENTS.md` + `web/node_modules/next/dist/docs/` before coding), React 19.3, shadcn base-nova, `@base-ui/react` dialog primitives, lucide icons.
Files: `web/src/app/(dashboard)/layout.tsx` (mount point), `web/src/components/site-header.tsx`, `web/src/components/app-sidebar.tsx`, `web/src/components/insight-inspector.tsx` (hooks), `web/src/components/dataset-provider.tsx`, `web/src/lib/analyst/explain.ts` (`fold`), `web/src/lib/tour-steps.ts`, `web/src/app/(dashboard)/analyst/page.tsx`.

## Constitution check
| Principle | Compliance |
|---|---|
| IV Reuse OSS UI | official shadcn `command` via CLI (cmdk inside); no custom styling |
| V OSS | cmdk 1.1.1 MIT (peer React ^18/^19 — verified on npm registry 2026-11-16) |
| VI Security | free text only URL-encoded into `?q=`; no `dangerouslySetInnerHTML`; CSP unchanged (no new origins) |
| VII Offline | no network on open |
| VIII | unit test for filtering + nav parity before UI |

## Design
- `web/src/lib/nav.ts`: `export const NAV: {title, url, icon, keywords: string[]}[]` (moved from `app-sidebar.tsx`), `export function filterCommands(q, items)` using `fold` (pure, node-testable).
- `web/src/components/command-menu.tsx`: `CommandDialog` with groups; uses `useRouter`, `useDataset`, `useInsightInspector`; global `keydown` listener in `useEffect` with cleanup.
- `site-header.tsx`: hint button opening the dialog (shared state via a tiny context or a custom event `vlk:open-command`).
- `analyst/page.tsx`: read `useSearchParams().get("q")` (wrap in `Suspense` as Next 16 requires for `useSearchParams` in static pages — check docs) to pre-fill.

## Files to touch
`web/package.json` (+cmdk via shadcn CLI), `web/src/components/ui/command.tsx` (generated), `web/src/lib/nav.ts` (new), `web/src/lib/nav.test.ts` (new), `web/src/components/command-menu.tsx` (new), `web/src/app/(dashboard)/layout.tsx`, `web/src/components/app-sidebar.tsx`, `web/src/components/site-header.tsx`, `web/src/app/(dashboard)/analyst/page.tsx`, `web/src/lib/tour-steps.ts`, `docs/licenses.md` (cmdk MIT).

## Open-source reuse
shadcn Command (MIT) + cmdk (MIT). Rejected: kbar (MIT) — not a shadcn component (constitution IV).

## Security considerations
- **A03/XSS**: labels from code; dataset names from API rendered as text by React.
- **A01**: navigation only to internal routes from the `NAV` allowlist or `/analyst?q=` (encoded); export links only via `api.fileUrl` allowlisted kinds.
- **LLM01**: palette never sends text to an LLM; the analyst page requires an explicit Send.
- **Supply chain (A06)**: dependency added through the shadcn CLI; `npm audit --audit-level=high` in CI.
