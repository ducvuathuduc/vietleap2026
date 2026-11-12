"""Fetch a country x year panel of fiscal/macro indicators from the World Bank WDI API.
Usage: python tools/fetch_wdi.py [out.csv]
Source: https://api.worldbank.org/v2 (World Development Indicators)."""
import sys, json, subprocess
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
COUNTRIES = "VNM;THA;IDN;MYS;PHL;KHM;LAO;MMR;SGP;BRN;CHN;KOR;IND;BGD"
IND = {
 "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
 "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
 "GC.REV.XGRT.GD.ZS": "revenue_pct_gdp",
 "GC.TAX.TOTL.GD.ZS": "tax_revenue_pct_gdp",
 "GC.XPN.TOTL.GD.ZS": "expense_pct_gdp",
 "GC.NLD.TOTL.GD.ZS": "net_lending_pct_gdp",
 "GC.DOD.TOTL.GD.ZS": "central_gov_debt_pct_gdp",
 "SP.POP.TOTL": "population",
 "SP.URB.TOTL.IN.ZS": "urban_pop_pct",
 "FP.CPI.TOTL.ZG": "inflation_pct",
 "BX.KLT.DINV.WD.GD.ZS": "fdi_inflow_pct_gdp",
 "SE.XPD.TOTL.GD.ZS": "education_spend_pct_gdp",
}
rows = {}
meta = {}
def get(code):
    url = f"https://api.worldbank.org/v2/country/{COUNTRIES}/indicator/{code}?format=json&date=2000:2024&per_page=2000"
    out = subprocess.run(["curl", "-s", "-m", "60", url], capture_output=True, text=True).stdout
    return code, json.loads(out)
with ThreadPoolExecutor(6) as ex:
    results = list(ex.map(get, IND))
for code, data in results:
    name = IND[code]
    for r in data[1] or []:
        k = (r["country"]["value"], r["countryiso3code"], int(r["date"]))
        rows.setdefault(k, {})[name] = r["value"]
df = pd.DataFrame([{"country": k[0], "iso3": k[1], "year": k[2], **v} for k, v in rows.items()])
df = df.sort_values(["country", "year"])
out = sys.argv[1] if len(sys.argv) > 1 else "data/raw/wdi_asia_fiscal_panel.csv"
df.to_csv(out, index=False)
print(out, df.shape)
