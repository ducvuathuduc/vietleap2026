-- KPI row for the Overview page. ASEAN-10 peer set, 2000-2024.
-- median_gdp_pc is the 2024-only median (the benchmark year for the
-- "So what" narrative); the pooled 2000-24 median ($2,971) is a different
-- statistic and must not share the same label. gap_sgp_mmr stays the ratio
-- of pooled medians (SGP vs MMR, 2000-24).
-- All values computed live from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') / silver panel.
select
  (select count(*) from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet')
    where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM')) as records,
  (select median(gdp_per_capita_usd) from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet')
    where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM') and year = 2024) as median_gdp_pc,
  (select median(gdp_per_capita_usd) from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') where iso3 = 'SGP')
    / (select median(gdp_per_capita_usd) from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') where iso3 = 'MMR') as gap_sgp_mmr,
  (select (count(country) + count(iso3) + count(year) + count(gdp_per_capita_usd)
      + count(gdp_growth_pct) + count(revenue_pct_gdp) + count(tax_revenue_pct_gdp)
      + count(expense_pct_gdp) + count(net_lending_pct_gdp) + count(central_gov_debt_pct_gdp)
      + count(population) + count(urban_pop_pct) + count(inflation_pct)
      + count(fdi_inflow_pct_gdp) + count(education_spend_pct_gdp)) * 1.0 / (count(*) * 15)
    from read_parquet('../data/lake/silver/wdi_fiscal__wdi_asia_fiscal_panel.parquet')) as completeness
