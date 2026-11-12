"""Domain packs: detect the dataset's domain from column names and add derived metrics when columns match."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .vn import ascii_key

KEYWORDS = {
    "property": ["gia", "price", "dien tich", "area", "m2", "phong ngu", "bedroom", "phap ly", "so tang", "floors",
                 "loai hinh nha", "nha", "can ho", "apartment", "rent", "thue", "du an", "toilet", "mat tien", "duong"],
    "public_finance": ["ngan sach", "budget", "du toan", "thuc hien", "thu", "chi", "revenue", "expenditure", "expense",
                       "grdp", "gdp", "dan so", "population", "tax", "thue", "fiscal", "debt", "no cong", "bo sung",
                       "transfer", "chi dau tu", "chi thuong xuyen", "lending", "inflation"],
    "firm": ["doanh thu", "loi nhuan", "profit", "tai san", "assets", "von chu", "equity", "no phai tra", "liabilities",
             "ticker", "ma ck", "symbol", "roe", "roa", "eps", "nganh", "sector", "gia von", "cogs", "margin", "npat",
             "net revenue", "gross profit", "san", "exchange"],
}


def _find(cols, *patterns, exclude=()):
    """First column whose ascii key contains all words of any pattern (patterns are alternatives)."""
    for p in patterns:
        words = p.split("&")
        for c in cols:
            k = ascii_key(c)
            if all(w.strip() in k for w in words) and not any(e in k for e in exclude):
                return c
    return None


def detect_domain(columns: list[str]) -> tuple[str, dict]:
    scores = {}
    keys = [ascii_key(c) for c in columns]
    for dom, kws in KEYWORDS.items():
        scores[dom] = sum(any(kw in k for k in keys) for kw in kws) / len(kws)
    best = max(scores, key=scores.get)
    return (best if scores[best] >= 0.12 else "generic"), {k: round(v, 3) for k, v in scores.items()}


def _safe_div(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        out = a / b
    return out.replace([np.inf, -np.inf], np.nan)


def apply_property(df: pd.DataFrame, roles: dict, log: list[str]) -> dict:
    cols = [c for c, r in roles.items() if r == "numeric"]
    ppm2 = _find(cols, "gia&m2", "price per m", "price_per_m", "don gia", "ppm2", "gia/m")
    area = _find(cols, "dien tich", "area", "m2", exclude=("gia", "price"))
    price = _find(cols, "gia", "price", exclude=("m2", "/m", "per m", "don gia", "thue"))
    rent = _find(cols, "gia thue", "rent", "thue/thang")
    income = _find(cols, "thu nhap", "income")
    out = {"metrics": [], "primary_metric": None, "segment_col": None}
    if ppm2 and area and not price:
        df["price_total_vnd"] = df[ppm2] * df[area]
        roles["price_total_vnd"] = "numeric"; price = "price_total_vnd"
        log.append(f"[property] derived price_total_vnd = '{ppm2}' × '{area}'"); out["metrics"].append("price_total_vnd")
    if price and area and not ppm2:
        df["price_per_m2"] = _safe_div(df[price], df[area])
        roles["price_per_m2"] = "numeric"; ppm2 = "price_per_m2"
        log.append(f"[property] derived price_per_m2 = '{price}' / '{area}'"); out["metrics"].append("price_per_m2")
    if price:
        q = df[price].quantile([0.25, 0.5, 0.75])
        df["price_segment"] = pd.cut(df[price], [-np.inf, q[0.25], q[0.5], q[0.75], np.inf],
                                     labels=["Q1 entry", "Q2 mid", "Q3 upper-mid", "Q4 premium"]).astype(str).replace("nan", np.nan)
        roles["price_segment"] = "category"
        log.append(f"[property] price_segment = quartiles of '{price}'"); out["segment_col"] = "price_segment"
    if area:
        df["area_band"] = pd.cut(df[area], [0, 30, 50, 80, 120, np.inf], labels=["<30m²", "30-50m²", "50-80m²", "80-120m²", ">120m²"]).astype(str).replace("nan", np.nan)
        roles["area_band"] = "category"; out["metrics"].append("area_band")
    if rent and price:
        df["gross_rental_yield_pct"] = _safe_div(df[rent] * 12, df[price]) * 100
        roles["gross_rental_yield_pct"] = "numeric"; out["metrics"].append("gross_rental_yield_pct")
        log.append("[property] gross_rental_yield_pct = rent×12 / price")
    if income and price:
        df["price_to_income_years"] = _safe_div(df[price], df[income] * (12 if df[income].median() < 1e9 / 12 else 1))
        roles["price_to_income_years"] = "numeric"; out["metrics"].append("price_to_income_years")
        log.append("[property] price_to_income_years = price / annual income")
    out["primary_metric"] = ppm2 or price
    out.update({"price": price, "area": area, "price_per_m2": ppm2})
    ing = {}
    if ppm2 and price:
        ing[ppm2] = [price]  # area is kept: it is a standard hedonic driver of price/m²
        ing[price] = [ppm2]
    if rent and price:
        ing["gross_rental_yield_pct"] = [rent, price]
    if income and price:
        ing["price_to_income_years"] = [price, income]
    out["ingredients"] = ing
    return out


def apply_public_finance(df: pd.DataFrame, roles: dict, log: list[str]) -> dict:
    cols = [c for c, r in roles.items() if r == "numeric"]
    out = {"metrics": [], "primary_metric": None}
    rev = _find(cols, "tong thu", "thu ngan sach", "revenue")
    exp = _find(cols, "tong chi", "chi ngan sach", "expenditure", "expense")
    plan = _find(cols, "du toan", "budget plan", "estimate", "ke hoach")
    actual = _find(cols, "thuc hien", "actual", "quyet toan")
    pop = _find(cols, "dan so", "population")
    gdp = _find(cols, "grdp", "gdp", exclude=("pct", "growth", "per capita", "binh quan", "tang truong"))
    transfer = _find(cols, "bo sung", "transfer", "tro cap")
    pct_based = rev and exp and ("pct" in ascii_key(rev) or "%" in rev)
    if rev and exp:
        name = "fiscal_balance_pct_gdp" if pct_based else "fiscal_balance"
        df[name] = df[rev] - df[exp]
        roles[name] = "numeric"; out["metrics"].append(name)
        log.append(f"[public finance] {name} = '{rev}' − '{exp}'")
        if not pct_based:
            df["expenditure_to_revenue"] = _safe_div(df[exp], df[rev])
            roles["expenditure_to_revenue"] = "numeric"; out["metrics"].append("expenditure_to_revenue")
    if plan and actual:
        df["budget_execution_rate_pct"] = _safe_div(df[actual], df[plan]) * 100
        roles["budget_execution_rate_pct"] = "numeric"; out["metrics"].append("budget_execution_rate_pct")
        log.append(f"[public finance] budget_execution_rate_pct = '{actual}' / '{plan}'")
    if pop:
        for base in [b for b in (rev, exp, gdp) if b and not pct_based]:
            nm = f"{ascii_key(base).replace(' ', '_')}_per_capita"
            df[nm] = _safe_div(df[base], df[pop]); roles[nm] = "numeric"; out["metrics"].append(nm)
            log.append(f"[public finance] {nm} = '{base}' / '{pop}'")
    if transfer and rev:
        df["transfer_dependency_pct"] = _safe_div(df[transfer], df[rev]) * 100
        roles["transfer_dependency_pct"] = "numeric"; out["metrics"].append("transfer_dependency_pct")
    if gdp and rev and not pct_based:
        df["revenue_to_gdp_pct"] = _safe_div(df[rev], df[gdp]) * 100
        roles["revenue_to_gdp_pct"] = "numeric"; out["metrics"].append("revenue_to_gdp_pct")
    gpc = _find(cols, "gdp per capita", "gdp_per_capita", "grdp binh quan", "per capita")
    out["primary_metric"] = ("budget_execution_rate_pct" if plan and actual else None) or gpc or rev or gdp
    out.update({"revenue": rev, "expenditure": exp, "population": pop, "gdp": gdp})
    return out


def apply_firm(df: pd.DataFrame, roles: dict, log: list[str]) -> dict:
    cols = [c for c, r in roles.items() if r == "numeric"]
    rev = _find(cols, "doanh thu thuan", "net revenue", "net_revenue", "doanh thu", "revenue", "sales")
    cogs = _find(cols, "gia von", "cogs", "cost of goods")
    gp = _find(cols, "loi nhuan gop", "gross profit", "gross_profit")
    npat = _find(cols, "loi nhuan sau thue", "npat", "net income", "net profit", "net_profit", "profit after")
    ta = _find(cols, "tong cong tai san", "tong tai san", "total assets", "total_assets")
    eq = _find(cols, "von chu so huu", "equity", exclude=("no ",))
    liab = _find(cols, "no phai tra", "liabilities", "total debt")
    out = {"metrics": [], "primary_metric": None}

    out["ingredients"] = {}

    def add(name, series, desc, parts=()):
        df[name] = series; roles[name] = "numeric"; out["metrics"].append(name); log.append(f"[firm] {name} = {desc}")
        out["ingredients"][name] = [p for p in parts if p]
    if rev and not gp and cogs:
        add("gross_profit", df[rev] - df[cogs].abs(), f"'{rev}' − '{cogs}'", (rev, cogs)); gp = "gross_profit"
    pos_rev = df[rev].where(df[rev] > 0) if rev else None
    if gp and rev:
        add("gross_margin_pct", _safe_div(df[gp], pos_rev) * 100, f"'{gp}' / '{rev}'", (gp, rev))
    if npat and rev:
        add("net_margin_pct", _safe_div(df[npat], pos_rev) * 100, f"'{npat}' / '{rev}'", (npat, rev))
    if npat and ta:
        add("roa_pct", _safe_div(df[npat], df[ta].where(df[ta] > 0)) * 100, f"'{npat}' / '{ta}' (period, not annualised)", (npat, ta))
    if npat and eq:
        add("roe_pct", _safe_div(df[npat], df[eq].where(df[eq] > 0)) * 100, f"'{npat}' / '{eq}' (period, not annualised)", (npat, eq))
    if liab and eq:
        add("debt_to_equity", _safe_div(df[liab], df[eq].where(df[eq] > 0)), f"'{liab}' / '{eq}'", (liab, eq))
    if liab and ta:
        add("liabilities_to_assets_pct", _safe_div(df[liab], df[ta].where(df[ta] > 0)) * 100, f"'{liab}' / '{ta}'", (liab, ta))
    for c in [m for m in out["metrics"] if m.endswith("_pct")]:
        df[c] = df[c].clip(-500, 500)  # tiny denominators make ratios explode; clip and note
    out["primary_metric"] = "roe_pct" if "roe_pct" in out["metrics"] else ("net_margin_pct" if "net_margin_pct" in out["metrics"] else rev)
    out.update({"revenue": rev, "npat": npat, "total_assets": ta, "equity": eq})
    return out


def apply_domain(domain: str, df: pd.DataFrame, roles: dict, log: list[str]) -> dict:
    fn = {"property": apply_property, "public_finance": apply_public_finance, "firm": apply_firm}.get(domain)
    if fn is None:
        return {"metrics": [], "primary_metric": None}
    return fn(df, roles, log)


CAVEATS = {
    "property": [
        "Listing (asking) prices are not transaction prices; asking prices usually exceed final sale prices.",
        "Listings over-represent sellers who advertise online; the sample is not a random sample of the housing stock.",
        "Duplicate listings of the same property by several brokers may remain after exact-duplicate removal.",
    ],
    "public_finance": [
        "Budget figures mix plan (dự toán) and actual (quyết toán) depending on the year; check definitions before comparing.",
        "Administrative boundaries changed on 1 Jul 2025 (63 → 34 provinces); time series across the merger need re-aggregation.",
        "Per-capita figures depend on the population source (GSO census vs. annual estimates).",
    ],
    "firm": [
        "Ratios from a single quarter are not annualised; compare like periods only.",
        "Banks, insurers and securities firms use different statement templates; their margins are not comparable to non-financial firms.",
        "Accounting values are book values; market-value metrics need price data.",
    ],
    "generic": [],
}
