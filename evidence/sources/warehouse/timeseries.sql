-- Viet Nam vs ASEAN median GDP per capita, 2001-2024 (long format for LineChart series).
select cast(year as integer) as year, 'Việt Nam' as nhom, max(case when iso3 = 'VNM' then gdp_per_capita_usd end) as gdp_pc
from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet')
where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM') and year >= 2001
group by year
union all
select cast(year as integer) as year, 'Trung vị ASEAN' as nhom, median(gdp_per_capita_usd) as gdp_pc
from read_parquet('../data/lake/gold/obt_wdi_fiscal.parquet')
where iso3 in ('BRN','IDN','KHM','LAO','MMR','MYS','PHL','SGP','THA','VNM') and year >= 2001
group by year
order by year, nhom
