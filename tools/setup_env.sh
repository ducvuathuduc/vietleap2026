#!/usr/bin/env bash
# One-time environment setup. Everything lives inside the kit folder (portable, no root needed).
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KIT"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
# Headless Chromium for PNG/PDF export (kaleido + playwright). On x86_64 laptops kaleido can use system Chrome.
export PLAYWRIGHT_BROWSERS_PATH="$KIT/.tools/ms-playwright"
.venv/bin/python -m playwright install chromium-headless-shell || .venv/bin/python -m playwright install chromium
# Linux containers without root sometimes miss 4 GUI libs; fetch them locally (Debian/Ubuntu arm64/amd64).
if command -v dpkg-deb >/dev/null && [ "$(uname -s)" = Linux ]; then
  bash tools/fetch_chrome_libs.sh || true
fi
(cd web && npm install)
echo "setup done"
