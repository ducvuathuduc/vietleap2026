# source tools/env.sh  -> puts the kit venv + local chromium on the path
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -d "$KIT/.venv/Scripts" ] && command -v cygpath >/dev/null; then
  export PATH="$KIT/.venv/Scripts:$PATH"
  export PYTHONPATH="$(cygpath -w "$KIT/engine");$(cygpath -w "$KIT")${PYTHONPATH:+;$PYTHONPATH}"
  export PLAYWRIGHT_BROWSERS_PATH="$(cygpath -w "$KIT/.tools/ms-playwright")"
  HS=$(ls "$KIT"/.tools/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell.exe 2>/dev/null | head -1)
  [ -n "$HS" ] && export BROWSER_PATH="$(cygpath -w "$HS")"
else
  export PATH="$KIT/.venv/bin:$PATH"
  export PYTHONPATH="$KIT/engine:$KIT${PYTHONPATH:+:$PYTHONPATH}"
  export PLAYWRIGHT_BROWSERS_PATH="$KIT/.tools/ms-playwright"
  LIBDIR=$(ls -d "$KIT"/.tools/chromelibs/root/usr/lib/*-linux-gnu 2>/dev/null | head -1)
  [ -n "$LIBDIR" ] && export LD_LIBRARY_PATH="$LIBDIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  HS=$(ls "$PLAYWRIGHT_BROWSERS_PATH"/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell 2>/dev/null | head -1)
  [ -n "$HS" ] && export BROWSER_PATH="$HS"
fi
export PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1
# httpx (every live fetch: connectors.py, reducto.py) parses NO_PROXY with its URL
# parser: the sandbox default contains bracketed IPv6 entries ([::1], ...) which raise
# `httpx.InvalidURL: Invalid port: ':1]'` on ANY request. The Makefile and CI already
# override NO_PROXY to this value; set it here too so direct `python de.py ...` runs
# (which only source this file) get the same fix.
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
# keep BLAS/OpenMP thread pools small: lower peak memory on small laptops/containers
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2} OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-2} MKL_NUM_THREADS=${MKL_NUM_THREADS:-2}
