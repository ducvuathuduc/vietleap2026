-- Spearman rank correlation of each indicator vs GDP per capita (ASEAN-10, pooled 2000-2024).
select 'urban_pop_pct' as indicator, 'Tỉ lệ dân số đô thị (%)' as chi_tieu,
  corr(rx, ry) as spearman_rho, count(*) as n
from (select rank() over (order by gdp_per_capita_usd) as rx, rank() over (order by urban_pop_pct) as ry
      from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM')
      and gdp_per_capita_usd is not null and urban_pop_pct is not null)
union all
select 'central_gov_debt_pct_gdp', 'Nợ chính phủ trung ương (% GDP)',
  corr(rx, ry), count(*)
from (select rank() over (order by gdp_per_capita_usd) as rx, rank() over (order by central_gov_debt_pct_gdp) as ry
      from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM')
      and gdp_per_capita_usd is not null and central_gov_debt_pct_gdp is not null)
union all
select 'revenue_pct_gdp', 'Thu ngân sách (% GDP)',
  corr(rx, ry), count(*)
from (select rank() over (order by gdp_per_capita_usd) as rx, rank() over (order by revenue_pct_gdp) as ry
      from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM')
      and gdp_per_capita_usd is not null and revenue_pct_gdp is not null)
union all
select 'inflation_pct', 'Lạm phát (%)',
  corr(rx, ry), count(*)
from (select rank() over (order by gdp_per_capita_usd) as rx, rank() over (order by inflation_pct) as ry
      from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM')
      and gdp_per_capita_usd is not null and inflation_pct is not null)
union all
select 'fdi_inflow_pct_gdp', 'FDI ròng (% GDP)',
  corr(rx, ry), count(*)
from (select rank() over (order by gdp_per_capita_usd) as rx, rank() over (order by fdi_inflow_pct_gdp) as ry
      from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet') where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM')
      and gdp_per_capita_usd is not null and fdi_inflow_pct_gdp is not null)
order by spearman_rho desc
