#!/usr/bin/env bash
cd "$(dirname "$0")/.." && source tools/env.sh
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
