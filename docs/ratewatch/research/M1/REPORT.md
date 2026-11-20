DONE M1

Acceptance (run fresh, exit codes read):
- pytest -q tests/ratewatch/test_geo.py -> 8 passed, exit 0 (PowerShell form from the brief)
- python -m vlkit.ratewatch.geo (builder on live cached Overpass data) -> exit 0, wrote data/lake/ratewatch/gold/geo_provinces.json (21.9 KB)

Live-run numbers (Overpass 20/11/2026 14:10 +07, HTTP 200, 46.6 s, cached bronze/osm/rw-20261120T1410):
- 2,477 OSM amenity=bank elements (1,854 nodes / 620 ways / 3 relations); 2,473 fall inside a province -> 34/34 provinces covered
- banks matched: 1,917 elements -> 33 of 34 banks.yaml codes seen (VCBNEO has no branches); unmatched share 22.5% (556: 166 no name/brand/operator tag; rest are VBSP, VDB, HSBC, Shinhan, VRB, DongA, LienVietPostBank, VietABank/Vikki, Western Union, SBV offices - not in banks.yaml, left unmatched rather than guessed)
- tag completeness: name 92.4%, brand 53.8%, operator 7.9%
- deposits/credit by province: NO systematic official table for all 34; only scattered NHNN regional-branch press figures (e.g. Đồng Nai 452,000 tỷ end-06/2025, NHNN Khu vực 2 via CafeF 22/07/2025) -> deposits_bn/credit_bn stay null in the JSON (CONTRACT D fields reserved)
- population: Nghị quyết 202/2025/QH15 (2024, registered-population basis, sums 113.6M > GSO de-facto ~101.3M - flagged) in engine/vlkit/ratewatch/geo/population_2024.csv; PXWeb DNS-dead from this machine, no 2026 census exists

Files: engine/vlkit/ratewatch/geo/{__init__,__main__,pip,provinces,banks_match,overpass,build}.py + population_2024.csv; tests/ratewatch/test_geo.py; tests/fixtures/ratewatch/geo/{mini.geojson,mini_overpass.json,mini_banks.yaml,mini_population.csv}. Research: M1.md in this folder. ODbL attribution in the gold output. Not done: TinyFish budget unspent (no machine-readable official branch counts found to justify it); no commit (per rules).
