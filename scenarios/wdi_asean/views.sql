CREATE OR REPLACE VIEW gold.v_vnm_vs_asean_gap AS
WITH observations AS (
    SELECT year_key AS year, iso3, indicators.indicator, indicators.value
    FROM gold.obt_integrated_wdi_asean
    CROSS JOIN LATERAL (VALUES
        ('GC.TAX.TOTL.GD.ZS', tax_revenue_pct_gdp),
        ('NY.GDP.PCAP.CD', gdp_per_capita_usd),
        ('NY.GDP.MKTP.KD.ZG', gdp_growth_pct),
        ('GC.REV.XGRT.GD.ZS', revenue_pct_gdp),
        ('GC.XPN.TOTL.GD.ZS', expense_pct_gdp),
        ('GC.NLD.TOTL.GD.ZS', net_lending_pct_gdp),
        ('GC.DOD.TOTL.GD.ZS', central_gov_debt_pct_gdp),
        ('SP.POP.TOTL', population),
        ('SP.URB.TOTL.IN.ZS', urban_pop_pct),
        ('FP.CPI.TOTL.ZG', inflation_pct),
        ('BX.KLT.DINV.WD.GD.ZS', fdi_inflow_pct_gdp),
        ('SE.XPD.TOTL.GD.ZS', education_spend_pct_gdp)
    ) AS indicators(indicator, value)
), comparison AS (
    SELECT indicator, year,
           max(value) FILTER (WHERE iso3 = 'VNM') AS vnm_value,
           median(value) FILTER (WHERE iso3 != 'VNM') AS asean_median,
           count(value) FILTER (WHERE iso3 != 'VNM') AS n_countries
    FROM observations
    GROUP BY indicator, year
)
SELECT indicator, year, vnm_value, asean_median, vnm_value - asean_median AS gap, n_countries
FROM comparison;
