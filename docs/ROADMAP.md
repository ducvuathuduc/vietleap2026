# ROADMAP 16/11 → 21/11/2026 (Asia/Saigon)

Source of truth for *what*: [`specs/README.md`](../specs/README.md) (features 002–011, estimates, dependencies).
Source of truth for the *contest days*: [`docs/CONTEST_ANALYSIS.md`](CONTEST_ANALYSIS.md) §1.3 (official agenda) and §4.2 (hour-by-hour plan).
Rules: every task group = commit + push (constitution VIII); never run `npm run build` together with pytest (2-CPU laptop); `NO_PROXY=localhost,127.0.0.1`.

## Capacity vs scope (planning numbers, not measurements)
- Remaining spec work ≈ 43.5 h (+2 h optional YOLO). Developer time before the 19/11 12:00 check-in ≈ 29 h (16/11 ≈ 6 h, 17/11 ≈ 10 h, 18/11 ≈ 10 h, 19/11 morning ≈ 3 h).
- **Cut line**: all P1 (002, 003, 004, 009, 011-LLM ≈ 24 h) + 010 (3 h) must land; 007 is the first stretch goal; 005, 006, 008 only if P1 finishes early. Anything not merged by **18/11 22:00 (feature freeze)** is dropped for the contest.

## Progress (16/11 16:40)
- ✅ 002 done & pushed (`bdcb571`, `76c9e37`; CI + Security green) — Tue 17/11 08:00–12:00 slot is freed.
- ⏸ Paused on request before 003 started (no 003 code written). Next on resume: 003 T301.

## Day by day
| Day | Time | Work | Feature / tasks | Owner | Done when |
|---|---|---|---|---|---|
| **Mon 16/11** | morning | Join-coverage UI finished; all remaining specs written and pushed | 001 T043–T045 (`7ecc309`); specs 002–011 | DE | pushed ✅ |
| | afternoon | Policy-question-first deck & pitch (engine) | 002 T201–T206 | DE | ✅ pushed `bdcb571` (CI + Security green) |
| | **19:00** | **Online workshop — Lưu Đức Cảnh (Tasco): luồng dữ liệu & dashboard chuyên nghiệp** — note exact vocabulary (4 stages, OBT/Star/Snowflake/Data Vault choice), ask "ở quy mô hackathon ưu tiên mô hình nào cho dashboard?" | — | LEAD | notes added to `docs/WORKFLOW.md` (commit) |
| | after workshop | Align deck "Data model" wording with the speaker's answer | 002 T204 wording | DE | pushed |
| **Tue 17/11** | 08:00–12:00 | Brief endpoint + story question/limits | 002 T207–T212 | DE | ✅ done early 16/11 `76c9e37` (CI + Security green) |
| | 13:00–17:00 | Bilingual deck/pitch (ST writes VI/EN strings in parallel) | 003 T301–T309 | DE + ST | `--lang both` test green |
| | 17:00–19:00 | Real-key LLM run (Groq) + injection/rate-limit probes | 011 T1101–T1106 | LEAD/DE + AN | `llm-run.md` filled, gitleaks clean |
| | evening | Engine support for packs (per-column agg, ratios, post_sql views) | 004 T401–T405 | DE | pushed |
| | admin | Ask organisers (Zalo): rubric, pitch length & language, submission format/size, provided data, AI policy | — | LEAD | answers recorded in `docs/CONTEST_ANALYSIS.md` §5 |
| **Wed 18/11** | 08:00–12:00 | Recipes & packs: WDI ASEAN, public finance, listed firms aliases, energy/EV | 004 T406–T410 | DE (+ RQ collects provincial table T411) | tests green |
| | 13:00–16:00 | Dry runs of all packs on the contest laptop | 004 T411–T413 | DE + AN | `checklists/dry-run.md` filled with real numbers |
| | 16:00–21:00 | One-click export (engine → API → web) + web export toggle | 009 T901–T911, 003 T310–T312 | DE | bundle opens on another machine |
| | evening | Bilingual deck skeleton for pitch (7 min, §4.6) + Q&A drill in VI/EN | 002/003 outputs | PO + ST | deck v0 from a practice dataset |
| | **22:00** | **Feature freeze** — only fixes after this | — | LEAD | `specs/README.md` statuses updated |
| | stretch | What-if sliders page | 007 T701–T711 | DE | only if P1 done |
| **Thu 19/11** | 07:00–11:00 | Screenshots + 90 s demo video; README images | 010 T1001–T1007 | ST + DE | PNGs pushed, video on Drive |
| | 11:00–12:00 | Contest laptop: `git pull && make setup && make demo`, `make api` + `make web`, export once | — | DE | all green offline |
| | 12:00–15:00 | Check-in KTX UEH Green Living Hub; test wifi; hotspot fallback | — | LEAD | kit runs on venue network |
| | 15:00 / **15:30** | Opening; **workshop Chi-Yu Lee (Konstanz) — object tracking CV** | 011 YOLO optional notes | all | 5-line notes |
| | 18:30–20:30 | Networking: confirm submission format, pitch length/language with organisers | — | LEAD | §5 updated |
| | 21:00 | Sleep early | — | all | — |
| **Fri 20/11** | **09:00–09:30** | **Brief published + random team formation** → assign roles (LEAD, DE, AN, PO, ST, RQ) | — | LEAD | role table |
| | 09:30–10:00 | Paste brief into **Đề bài** → `brief.json`; list provided data | 002 flow | LEAD + PO | brief.json saved for the dataset |
| | 10:00–10:45 | Workshop Viet Nguyen-Tien (LSE) — PO/AN/ST attend; DE runs pipeline #1 on organisers' data | 004 recipe closest to the brief | DE | pipeline green #1 |
| | 11:00–11:30 | **Workshop Sacha Dray (World Bank) — dashboard** (whole team) | — | all | 3 dashboard principles noted |
| | 12:30 | **CP1**: one decision question, data identified, pipeline runs | — | PO | go/no-go |
| | 12:30–16:30 | Extra sources + conformed dims; select 3–5 tested insights; draft recommendation | 004 recipes, 007 if built | DE/AN/PO | **CP2 16:30** |
| | **17:15–17:45** | **Mentor check-in #1** | — | PO | adjustments list |
| | 20:00 | **CP3** scope frozen; then deck v1 via one-click export, story, decision page | 009, 002 | DE/ST/PO | deck v1 |
| | 23:00–24:00 | Full pitch run #1 (timed) | — | PO | notes |
| **Sat 21/11** | 09:00–10:30 | Deck v2 (`--lang` per organisers), screenshots/video on contest data, Q&A drill | 003, 010 T1008 | ST/DE/PO | deck v2 |
| | **10:30–11:00** | **Mentor check-in #2** — real pitch | — | PO | last fixes |
| | 12:00 | **CP4** content locked; final one-click export bundle | 009 | LEAD | bundle + checksums |
| | **12:40** | **Submit (target)** — screenshot confirmation | — | LEAD | receipt |
| | **13:00** | **Submission deadline** (13:00–13:15 per agenda) | — | — | — |
| | **13:15–15:15** | **Pitch + Q&A** | — | PO (+ DE for technical Qs) | — |

## Go/no-go gates before the contest
| Gate | When | Condition | If no-go |
|---|---|---|---|
| G1 | 17/11 20:00 | 002 + 011 LLM row pass | ship deck with generic slide 2 + offline AI only |
| G2 | 18/11 16:00 | ≥ 3 packs dry-run green | drop energy/EV pack; keep recipes as docs |
| G3 | 18/11 22:00 | 009 bundle works offline | fall back to sidebar downloads (deck, summary PDF, dashboard HTML) |
| G4 | 19/11 11:00 | contest laptop runs `make demo` + web offline | use dev laptop + hotspot; video backup |
