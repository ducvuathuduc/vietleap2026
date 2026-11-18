#!/usr/bin/env bash
# `make demo`: run every practice dataset through the full kit (DE pipeline → DuckDB bronze/silver/gold → insights,
# deck, dashboard) one at a time (weak laptops: never in parallel). Wall-clock times → out/_logs/times.txt
set -uo pipefail
cd "$(dirname "$0")/.." && source tools/env.sh
mkdir -p out/_logs; : > out/_logs/times.txt
run() {
  local name=$1 file=$2; shift 2
  if [ ! -f "$file" ]; then echo "$name skipped (missing $file)" | tee -a out/_logs/times.txt; return; fi
  local t0=$(date +%s)
  python de.py file "$file" --name "$name" --serve "$@" > "out/_logs/$name.log" 2>&1
  echo "$name exit=$? seconds=$(( $(date +%s) - t0 ))" | tee -a out/_logs/times.txt
}
run bds_practice   data/practice/synthetic_messy_bds.csv
run firms_2021     data/practice/vn_firms_2021.xlsx
run wdi_fiscal     data/practice/wdi_asia_fiscal_panel.csv --target tax_revenue_pct_gdp
run hanoi_housing  data/practice/hanoi_housing_2020.csv
echo ALL_DONE >> out/_logs/times.txt
