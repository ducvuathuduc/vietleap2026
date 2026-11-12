#!/usr/bin/env bash
# Run the kit on every practice dataset and record wall-clock times.
cd "$(dirname "$0")/.." && source tools/env.sh
run() { local name=$1; shift; local t0=$(date +%s); python run.py "$@" --name "$name" > "out/_logs/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t0 ))" | tee -a out/_logs/times.txt; }
mkdir -p out/_logs; : > out/_logs/times.txt
run synthetic_messy_bds data/practice/synthetic_messy_bds.csv
run hanoi_housing data/practice/hanoi_housing_2020.csv
run asia_fiscal_wdi data/practice/wdi_asia_fiscal_panel.csv --target gdp_per_capita_usd --geo country --time year
run vn_firms_2021 data/practice/vn_firms_2021.xlsx --geo "Ngành"
echo ALL_DONE >> out/_logs/times.txt
