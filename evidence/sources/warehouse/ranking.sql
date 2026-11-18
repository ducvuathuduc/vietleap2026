-- ASEAN-10 ranking, latest year (2024).
select
  rank() over (order by gdp_per_capita_usd desc) as hang,
  country as quoc_gia,
  iso3,
  gdp_per_capita_usd,
  gdp_growth_pct,
  urban_pop_pct
from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet')
where year = 2024 and iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM')
order by gdp_per_capita_usd desc
