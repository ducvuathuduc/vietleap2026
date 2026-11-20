# RateWatch VN — data contracts shared by T1-T5 (owner: Kiro). Change only through Kiro.

Product (final, 20/11/2026 14:00): one reader — a household with a VND amount and a date the money is needed — decides the term,
the bank/channel, and how much to keep at each bank under the 350-million insured cap. Every number shows its sheet date, read time,
source URL and reader grade. Policy panel and bank profile support the pitch and Q&A. No forecast; break-even is a calculation.

## A. Silver: posted rates (T1 writes, T2 reads)  — Parquet + CSV, one row per reader observation
| column | type | notes |
|---|---|---|
| run_id | str | `rw-YYYYMMDDTHHMM` Asia/Saigon |
| bank_code | str | upper-case short code from scenarios/ratewatch/banks.yaml (e.g. VCB, BIDV, CTG, AGRIBANK, TCB, MBB, ACB, VPB, STB, HDB, OCB) |
| term_months | int | 0 = demand (không kỳ hạn) |
| channel | str | counter or online |
| tier | str | "" if none, else as printed (e.g. "duoi_500tr") |
| rate_pct | float | percent per year, e.g. 4.75 |
| interest_basis | str | at_maturity unless the sheet says otherwise |
| sheet_date | date or null | effective date printed on the sheet |
| observed_at | timestamp +07:00 | read time |
| reader | str | bank_html, bank_pdf, aggregator, tinyfish |
| source_url | str | exact page or PDF |
| raw_sha256 | str | hash of the bronze object the row came from |
Bronze: one object per HTTP/agent response under data/lake/ratewatch/bronze/<source>/<run_id>/... (gitignored) + meta JSON
{url, fetched_at, status, sha256, run_id, robots_allowed, licence, method, usd_cost}. Run log JSON: records, errors, seconds, usd.
Idempotent: re-running a run_id overwrites the same objects; silver upsert key (run_id, bank_code, term_months, channel, tier, reader).

## B. Gold grade rule (T2)
Per (bank, term, channel, tier, sheet_date or run): verified = >= 2 independent readers (different reader kinds) agree within 0.005 pp;
contested = readers differ; single = one reader. Headline/KPI/decision numbers use verified rows first, single rows only when labelled.
Contested rows never feed calculations; they appear in the table with both values.

## C. Snapshot JSON (T2 writes web/seed/ratewatch/snapshot.json and S3; T4/T5 read). JSON Schema owned by T2 at
engine/vlkit/ratewatch/schema/snapshot.schema.json. Shape:
```
{ "meta": { "snapshot_id", "generated_at", "run_ids": [], "coverage": {"banks_total","banks_read","rows","verified","single","contested"},
            "quality": [{"id","name","status":"pass|warn|fail","detail"}],
            "sources": [{"id","publisher","url","licence","method"}] },
  "policy": { "ceiling": {"pct":4.75,"terms":"1 to <6 months","legal_ref","valid_from"},
              "cap": {"vnd":350000000,"legal_ref","valid_from"},
              "premium": {"pct":0.15,"legal_ref"},
              "insured_coverage": {"depositors_pct":93.68,"value_pct":19.06,"basis","source"} },
  "banks": [ { "code","name_vi","name_en","ticker","ownership","listed","sheet_url","sheet_date","read_at",
               "rates": [ {"term_months","channel","tier","rate_pct","grade","readers":[{"reader","value","source_url","observed_at"}]} ],
               "profile": { "quarter", "metrics": {"npl_pct","npl_change_pp","npl_amount_growth_pct","coverage_pct","ldr_pct","roa_pct",
                            "nim_pct","loan_growth_pct","deposit_growth_pct"}, "percentiles": {}, "flags": [{"id","text","rule_ref"}],
                            "market": {"pb","vol60_pct","drawdown_pct","foreign_net_20d_bn"}, "source":"FiinQuant (aggregates)" } | null } ],
  "market": { "ceiling_stats": {"quotes_1_5m","at_ceiling","above","jump_5_6_pp_median","n_banks","grade_basis"},
              "interbank": [{"date","tenor","rate_pct"}], "omo": [{"date","volume_bn","rate_pct","tenor_days"}],
              "central_fx": [{"date","vnd_per_usd"}] },
  "macro": { "cpi_yoy": [{"month","pct"}], "sbv_monthly": [{"month","household_deposits_bn","credit_growth_ytd_pct","deposit_growth_ytd_pct"}] },
  "changes": [{"bank","term_months","channel","from_pct","to_pct","observed_at"}] }
```
FiinQuant appears only as aggregates/percentiles with attribution "Nguồn: FiinQuant (FiinGroup)"; never raw rows.

## D. Geography (added 14:15; M1 writes engine/vlkit/ratewatch/geo/**, T2 copies it into the snapshot, T4 renders)
Snapshot key "geo": { "provinces": [ { "pcode" (HDX COD-AB adm1_pcode, 34 units), "name_vi", "name_en",
  "branches_total", "branches_by_bank": {"VCB": n, ...}, "branch_source", "population", "population_period",
  "deposits_bn" | null, "credit_bn" | null, "deposit_period" | null, "deposit_source" | null,
  "best_counter_12m": {"bank","rate_pct","grade"} | null } ], "boundary": "web/public/geo/vn-34.geo.json",
  "attribution": "Ranh giới: GSO/OCHA COD-AB v02 (CC BY-IGO) · Bao gồm Hoàng Sa (Đà Nẵng) & Trường Sa (Khánh Hòa)." }
Never draw a basemap that could omit Hoàng Sa / Trường Sa; use the repo boundary asset only.

## E. Amount tiers (added 15:20 after a live check: OCB's 06/11/2026 online sheet has three tiers, e.g. 6 months 6.00% under 100 million,
6.10% from 100 to 500 million, 6.20% above 500 million; 12 months 6.30 / 6.40 / 6.50)
Silver and gold add `tier_min_vnd` (int, inclusive, 0 if none) and `tier_max_vnd` (int, exclusive, null = no upper bound) next to the
printed `tier` text. A rate applies to an amount only if tier_min_vnd <= amount < tier_max_vnd. Rows without tiers have 0 / null.
Headline, key numbers, plans and the AI must pick the tier that matches the user's amount and show the tier label.
