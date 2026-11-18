# VietLeap Insight Kit — one-word commands. Run from the repo root. `make help` lists them.
SHELL := /bin/bash
ENV   := source tools/env.sh && export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
PORT  ?= 8000

.PHONY: help setup api web web-dev demo demo-online brief contest screenshots demo-video test test-py test-web lint clean-out reducto-parse

help:            ## list commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | expand -t 16

setup:           ## create .venv, install Python + Node deps, headless Chromium (one time, ~5–10 min)
	bash tools/setup_env.sh

api:             ## FastAPI on :8000 (docs at http://localhost:8000/docs)
	$(ENV) && uvicorn api.main:app --host 127.0.0.1 --port $(PORT)

web:             ## production build + start dashboard on :3000 (needs `make api` in another terminal)
	cd web && export EXTERNAL_API_URL=http://127.0.0.1:$(PORT) && npm run build && npm run start

web-dev:         ## Next.js dev server on :3000 (hot reload; heavier on RAM)
	cd web && npm run dev

demo:            ## run all practice datasets end-to-end, sequentially → out/<name>/
	bash tools/run_practice.sh

demo-online:     ## multi-source demo: file + SQLite + World Bank API + Wikipedia scrape + RSS → one warehouse
	$(ENV) && python de.py run scenarios/demo/sources.yaml --primary vn_housing --serve

brief:           ## parse a problem statement: make brief F=scenarios/briefs/bds_gia_m2.md D=data/practice/synthetic_messy_bds.csv
	$(ENV) && python de.py brief $(F) $(if $(D),--data $(D),)

export PACK BRIEF CONTEST_LANG
contest:         ## build all contest deliverables: make contest PACK=wdi_asean BRIEF=scenarios/briefs/chi_so_phat_trien.md
	$(ENV) && python de.py contest "$$PACK" "$$BRIEF" --lang "$${CONTEST_LANG:-both}"

DATASET ?= wdi_asean
export DATASET
screenshots:     ## capture the dashboard against a running api and web
	$(ENV) && python tools/screenshots.py --dataset "$$DATASET"

demo-video:      ## record the timed dashboard demo against a running api and web
	$(ENV) && python tools/record_demo.py --dataset "$$DATASET"

test: test-py test-web ## all checks (never run together with a build on weak machines)

test-py:         ## pytest
	$(ENV) && pytest -q tests

test-web:        ## web unit tests + eslint
	cd web && npm test && npm run lint

clean-out:       ## delete generated outputs (out/, warehouse, lake) — keeps data/raw and cache
	rm -rf out data/warehouse.duckdb data/warehouse.duckdb.wal data/lake

reducto-parse:   ## optional PDF/scan parse via Reducto API -> JSON/Bronze (needs REDUCTO_API_KEY or MOCK=1)
	$(ENV) && python de.py reducto "$(FILE)" $(if $(NAME),--name "$(NAME)",) $(if $(MOCK),--mock,) $(if $(OUT),--out "$(OUT)",) --bronze
