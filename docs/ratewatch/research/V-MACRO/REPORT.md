DONE V-MACRO
- Delivered MACRO.md with all five findings sections and SBV_MONTHLY_SAMPLE.csv with 20 months (2025-01–2026-08).
- Verified official daily interbank, auction and central FX samples. Verified monthly credit/deposit JSON, SBV rate PDF samples and LDR checkpoints.
- Verified Vietcombank FX, live FiinQuant bank-sector P/B and BTMC chart rows. Checked eight competitor entries, including Calc.vn and broker research.
- Acceptance: `.venv/Scripts/python.exe -B -X utf8 "$env:TEMP/vmacro-verify.py"` → exit 0. Verified all monthly values against source JSON and recomputed three indicators plus rollover.
- Repo check: `git diff --exit-code`, `git diff --cached --exit-code`, `git status --short` → all exit 0, no paths. Git emitted a global-ignore read warning.
- No repo changes, dependency installs, model training or build. No tests added to the repo.
- Limits: official deep-history form requests returned 403. Official monthly rates and LDR depth remain partial. The CSV preserves the October 2025 deposits methodology break.
- Product verdict: show a renewal break-even and dated market context. Method for a forward-looking point forecast is none.
