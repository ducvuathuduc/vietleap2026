-- KPI row for the Overview page. ASEAN-10 peer set, 2000-2024.
-- All values computed live from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') / silver panel.
select
  (select count(*) from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet')
    where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM')) as records,
  (select median(gdp_per_capita_usd) from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet')
    where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM')) as median_gdp_pc,
  (select median(gdp_per_capita_usd) from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') where iso3 = 'SGP')
    / (select median(gdp_per_capita_usd) from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') where iso3 = 'MMR') as gap_sgp_mmr,
  (select (count(country) + count(iso3) + count(year) + count(gdp_per_capita_usd)
      + count(gdp_growth_pct) + count(revenue_pct_gdp) + count(tax_revenue_pct_gdp)
      + count(expense_pct_gdp) + count(net_lending_pct_gdp) + count(central_gov_debt_pct_gdp)
      + count(population) + count(urban_pop_pct) + count(inflation_pct)
      + count(fdi_inflow_pct_gdp) + count(education_spend_pct_gdp)) * 1.0 / (count(*) * 15)
    from read_parquet('../data/lake/silver/wdi_fiscal__wdi_asia_fiscal_panel.parquet')) as completeness
