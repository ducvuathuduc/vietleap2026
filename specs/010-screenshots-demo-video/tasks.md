# Tasks: 010 Screenshots + demo video script

**Legend**: `[P]` parallel-safe · `→` depends on · test-first. **Done for every task**: pytest → web test/lint/build (sequential), commit `thanhdicode`, push `origin main`, tick with hash.

- [ ] T1001 Test-first `tests/test_tools_scripts.py`: `tools/screenshots.py --dry-run` prints every nav route with its file name; `record_demo.py --dry-run` parses the storyboard.
- [ ] T1002 `tools/screenshots.py` (+ Makefile `screenshots`) → T1001.
- [ ] T1003 [P] ST/PO: `docs/DEMO_SCRIPT.md` storyboard (time, action, selector, narration VI/EN) aligned with `docs/CONTEST_ANALYSIS.md` §4.6.
- [ ] T1004 `tools/record_demo.py` (+ Makefile `demo-video`) → T1001, T1003.
- [ ] T1005 Real run on `wdi_fiscal` (and `demo_multi`): commit `docs/screenshots/*.png` + index (dataset, commit, date); review for secrets/PII; README §4 images.
- [ ] T1006 Record `out/demo/demo.webm`; PO review; LEAD uploads to Drive (link noted in `docs/ROADMAP.md`, not the file).
- [ ] T1007 Commit + push "docs(demo): T1001–T1006 screenshots + demo video script"; tick; `specs/README.md`.
- [ ] T1008 (21/11 09:00–10:30) Re-run both on the contest dataset; drop PNGs into deck appendix (no commit of contest data).

## Dependencies
T1001→T1002/T1004; T1003→T1004; T1002→T1005; T1004→T1006→T1007. Best after 005/007/008/009 land so screenshots include them; can run earlier and be refreshed.
