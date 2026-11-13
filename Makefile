# VietLeap Insight Kit — one-word commands. Run from the repo root. `make help` lists them.
SHELL := /bin/bash
ENV   := source tools/env.sh && export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
PORT  ?= 8000

.PHONY: help setup api web web-dev demo demo-online brief test test-py test-web lint clean-out

help:            ## list commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | expand -t 16

setup:           ## create .venv, install Python + Node deps, headless Chromium (one time, ~5–10 min)
	bash tools/setup_env.sh

api:             ## FastAPI on :8000 (docs at http://localhost:8000/docs)
	$(ENV) && uvicorn api.main:app --host 127.0.0.1 --port $(PORT)

web:             ## production build + start dashboard on :3000 (needs `make api` in another terminal)
	cd web && npm run build && npm run start

web-dev:         ## Next.js dev server on :3000 (hot reload; heavier on RAM)
	cd web && npm run dev

demo:            ## run all practice datasets end-to-end, sequentially → out/<name>/
	bash tools/run_practice.sh

demo-online:     ## multi-source demo: file + SQLite + World Bank API + Wikipedia scrape + RSS → one warehouse
	$(ENV) && python de.py run scenarios/demo/sources.yaml --primary vn_housing --serve

brief:           ## parse a problem statement: make brief F=scenarios/briefs/bds_gia_m2.md D=data/practice/synthetic_messy_bds.csv
	$(ENV) && python de.py brief $(F) $(if $(D),--data $(D),)

test: test-py test-web ## all checks (never run together with a build on weak machines)

test-py:         ## pytest
	$(ENV) && pytest -q tests

test-web:        ## web unit tests + eslint
	cd web && npm test && npm run lint

clean-out:       ## delete generated outputs (out/, warehouse, lake) — keeps data/raw and cache
	rm -rf out data/warehouse.duckdb data/warehouse.duckdb.wal data/lake
