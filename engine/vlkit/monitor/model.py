"""DuckDB silver and gold model for the Vietnam Macro-Financial Monitor."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd

from ..de.sources import now_iso
from ..de.warehouse import Warehouse, ident, row_hash
from ..vn import ascii_key, normalize_province
from .ingest import OBS_COLUMNS


DATASET = "vn_monitor"
RESOURCES = Path(__file__).resolve().parents[1] / "resources"
INDEXES = "'VNINDEX', 'VN30', 'HNXINDEX', 'UPCOMINDEX'"
BAR_FIELDS = ("open", "high", "low", "close", "volume", "value", "bu", "sd", "fb", "fs", "fn")
BANK_FIELDS = {
    "nim": ("ratios.ProfitabilityComponent.NIM", 100),
    "pb": ("ratios.ValuationRatios.PriceToBook", 1),
    "pe": ("ratios.ValuationRatios.PriceToEarning", 1),
    "npl_proxy": ("ratios.AssetQualityComponent.ProblemLoansAndLeasesCalculatedAsPercentageOfGrossLoans", 100),
    "coverage": ("ratios.AssetQualityComponent.LoanLossReservesToNPLs", 100),
    "ldr": ("ratios.LiquidityAndAssetsComponent.LDRPercentage", 100),
    "loan_growth_yoy": ("ratios.GrowthComponent.AverageLoansGrowthPercentageYoY", 100),
    "deposit_growth_yoy": ("ratios.GrowthComponent.AverageDepositGrowthPercentageYoY", 100),
    "interest_income_growth_yoy": ("ratios.GrowthComponent.InterestincomeGrowthPercentageYoY", 100),
    "book_value_per_share": ("ratios.ValuationRatios.BookValuePerShare", 1),
    "eps": ("ratios.ValuationRatios.BasicEPS", 1),
    "net_interest_income": ("ratios.NetInterestIncome", 1),
    "profit_attributable": ("ratios.AttributeToParentCompany", 1),
}
FOREIGN_FIELDS = (
    "foreignBuyVolumeTotal", "foreignSellVolumeTotal", "foreignBuyValueTotal", "foreignSellValueTotal",
    "foreignNetVolumeTotal", "foreignNetValueTotal", "foreignBuyVolumeMatched", "foreignSellVolumeMatched",
    "foreignBuyValueMatched", "foreignSellValueMatched", "foreignBuyVolumeDeal", "foreignSellVolumeDeal",
    "foreignBuyValueDeal", "foreignSellValueDeal", "foreignCurrentRoom", "foreignTotalRoom",
    "percentForeignTotalRoom", "foreignOwned", "percentForeignOwned",
)
INVESTOR_FIELDS = (
    "localIndividualNetMatchVolume", "foreignIndividualNetMatchVolume", "localInstitutionalNetMatchVolume",
    "foreignInstitutionalNetMatchVolume", "localIndividualNetMatchValue", "foreignIndividualNetMatchValue",
    "localInstitutionalNetMatchValue", "foreignInstitutionalNetMatchValue", "proprietaryNetTotalMatchVolume",
    "proprietaryNetTotalMatchValue",
)
WEIGHT_FIELDS = (
    "close", "FreeFloat", "OutstandingShare", "FreeFloatRate", "MarketCapFLimit",
    "TotalCapitalization", "Stock Ratio", "Shares to Buy", "Stock Value to Buy",
)
YTD_LEVELS = (
    "nsnn_thu_ytd", "nsnn_chi_ytd", "dtc_giai_ngan_ytd", "fdi_dang_ky_ytd", "fdi_thuc_hien_ytd",
    "ban_le_ytd", "xuat_khau_ytd", "nhap_khau_ytd", "fdi_cap_moi_ytd", "fdi_dieu_chinh_ytd", "fdi_gop_von_ytd",
)
COUNTRIES = {
    "BRN": "Brunei", "KHM": "Campuchia", "IDN": "Indonesia", "LAO": "Lào", "MYS": "Malaysia",
    "MMR": "Myanmar", "PHL": "Philippines", "SGP": "Singapore", "THA": "Thái Lan",
    "TLS": "Timor-Leste", "VNM": "Việt Nam",
}


def _frame(records, columns):
    return pd.DataFrame(records).reindex(columns=columns).astype("string")


def _flags(expressions):
    labels = ", ".join(f"'{label}'" for label in expressions)
    mask = ", ".join(f"coalesce({predicate}, false)" for predicate in expressions.values())
    return f"list_where([{labels}], [{mask}])"


def _lineage(wh, sources, table, step):
    for source in sources:
        existing = wh.con.execute("""
            SELECT 1 FROM meta.lineage WHERE dataset=? AND from_node=? AND to_node=? AND step=? LIMIT 1
        """, [DATASET, source, table, step]).fetchone()
        if existing is None:
            wh.lineage(DATASET, source, table, step)


def _create(wh, table, query, *sources, view=False):
    kind = "VIEW" if view else "TABLE"
    wh.con.execute(f"CREATE OR REPLACE {kind} {table} AS {query}")
    _lineage(wh, sources, table, "serve" if view else ("clean" if table.startswith("silver.") else "model"))


def _number(expr):
    cast = f"TRY_CAST({expr} AS DOUBLE)"
    return f"CASE WHEN isfinite({cast}) THEN {cast} END"


class _MarketFields:
    """Canonical fields with SQL projections and failed-cast checks for a landing table."""

    def __init__(self, wh, name):
        self.columns = {c["name"] for c in wh.columns(f"bronze.vm_fq_{name}")}
        self.projections = []
        self.errors = []
        self.category_changes = []
        self.units = []

    def raw(self, name):
        return ident(name) if name in self.columns else "NULL"

    def text(self, name):
        return f"nullif(trim(CAST({self.raw(name)} AS VARCHAR)), '')"

    def string(self, alias, name, transform=None, fallback=None):
        value = self.text(name)
        expression = f"coalesce({value}, {fallback})" if fallback else value
        if transform:
            expression = f"{transform}({expression})"
            self.category_changes.append(f"{expression} <> {value}")
        self.projections.append(f"{expression} AS {ident(alias)}")

    def cast(self, alias, name, dtype="DOUBLE", multiplier=1):
        raw = self.text(name)
        value = self.raw(name)
        typed = _number(value) if dtype == "DOUBLE" else f"TRY_CAST({value} AS {dtype})"
        self.errors.append(f"({raw} IS NOT NULL AND ({typed}) IS NULL)")
        if multiplier != 1:
            self.units.append(f"({typed}) IS NOT NULL")
            typed = f"({typed}) * {multiplier}"
        self.projections.append(f"{typed} AS {ident(alias)}")


def _silver_market(wh, name, run_id):
    fields = _MarketFields(wh, name)
    table, raw = f"silver.vm_fq_{name}", f"bronze.vm_fq_{name}"
    date = "snapshot_date" if name in {"roster", "vn30_weights"} else "timestamp"
    keys = ["ticker", "date"]
    required = list(keys)
    validation = {}
    extra = []
    correlated = None
    outlier = None

    fields.string("ticker", "ticker", "upper")
    if name == "roster":
        fields.string("exchange", "exchangeCode", "upper")
        for alias, column in {"name_vi": "organizationName", "name_short_vi": "organizationShortName",
                              "tax_code": "taxCode", "sector_vi": "sector"}.items():
            fields.string(alias, column)
        for level in range(1, 6):
            fields.string(f"icb_l{level}", f"icbNameL{level}", "upper")
        keys.append("exchange")
        required.append("exchange")
        numeric = ()
    elif name == "bars":
        numeric = BAR_FIELDS
        required.extend(("open", "high", "low", "close", "volume", "value"))
        extra.append("'adjusted'::VARCHAR AS price_basis")
        validation.update(
            ohlc_bounds="low > high OR open < low OR close < low OR open > high OR close > high",
            foreign_balance="abs(fb - fs - fn) > greatest(1.0, abs(fb) * 0.00000001, abs(fs) * 0.00000001)",
            negative_trade="volume < 0 OR value < 0 OR fb < 0 OR fs < 0 OR bu < 0 OR sd < 0",
        )
        outlier, correlated = "value", ("volume", "value")
    elif name == "valuation":
        numeric = ("pe", "pb")
        default_scope = f"CASE WHEN upper({fields.text('ticker')}) IN ({INDEXES}) THEN 'index' ELSE 'stock' END"
        fields.string("scope", "scope", "lower", default_scope)
        keys.append("scope")
        validation["invalid_scope"] = "scope NOT IN ('stock', 'sector', 'index')"
        correlated = ("pe", "pb")
    elif name == "foreign":
        numeric = FOREIGN_FIELDS
        validation["foreign_balance"] = """
            abs(foreignBuyValueTotal - foreignSellValueTotal - foreignNetValueTotal) >
            greatest(1.0, abs(foreignBuyValueTotal) * 0.00000001, abs(foreignSellValueTotal) * 0.00000001)
            OR abs(foreignBuyVolumeTotal - foreignSellVolumeTotal - foreignNetVolumeTotal) > 1.0
        """
        correlated = ("foreignBuyValueTotal", "foreignSellValueTotal")
    elif name == "bank_ratios":
        numeric = tuple(BANK_FIELDS)
        for alias, (column, multiplier) in BANK_FIELDS.items():
            fields.cast(alias, column, multiplier=multiplier)
        fields.cast("year", "year", "INTEGER")
        fields.cast("quarter", "quarter", "INTEGER")
        keys = ["ticker", "year", "quarter"]
        required = list(keys)
        extra.extend((
            "CASE WHEN year BETWEEN 1900 AND 2100 AND quarter BETWEEN 1 AND 4 "
            "THEN make_date(year, quarter * 3 - 2, 1) END AS date",
            "CASE WHEN year BETWEEN 1900 AND 2100 AND quarter BETWEEN 1 AND 4 "
            "THEN concat(year, '-Q', quarter) END AS period",
        ))
        validation["invalid_period"] = "date IS NULL AND year IS NOT NULL AND quarter IS NOT NULL"
        correlated = ("nim", "pb")
    elif name == "breadth":
        date = "tradingDate"
        keys = ["index_code", "date", "kind", "ticker"]
        required = ["index_code", "date", "kind"]
        fields.string("index_code", "index_code", "upper", fields.text("comGroupCode"))
        fields.string("kind", "kind", "lower", "'breadth'")
        vendor_fields = {"advancers": "totalStockUpPrice", "decliners": "totalStockDownPrice",
                         "unchanged": "totalStockNoChangePrice", "under_floor": "totalStockUnderFloor",
                         "over_ceiling": "totalStockOverCeiling", "rank": "rank",
                         "contribution": "contribution", "contribution_pct": "contributionPercent"}
        for alias, column in vendor_fields.items():
            fields.cast(alias, column)
        numeric = tuple(vendor_fields)
        validation["negative_count"] = "advancers < 0 OR decliners < 0 OR unchanged < 0"
    else:
        numeric = WEIGHT_FIELDS if name == "vn30_weights" else INVESTOR_FIELDS

    if name not in {"bank_ratios", "breadth"}:
        for column in numeric:
            fields.cast(column, column)
    if name != "bank_ratios":
        fields.cast("date", date, "DATE")
    if name in {"bars", "foreign", "valuation", "investor_flow", "vn30_weights"}:
        fields.cast("quote_timestamp", "timestamp", "TIMESTAMP")
    fields.string("_ingested_at", "_ingested_at")
    fields.string("_row_hash", "_row_hash")
    fields.string("_src", "_src", fallback="'fiinquant'")
    fields.string("run_id", "_run_id", fallback="'" + run_id.replace("'", "''") + "'")

    missing = " OR ".join(f"{ident(col)} IS NULL" for col in required)
    if numeric and name not in {"bars", "breadth"}:
        missing += " OR (" + " AND ".join(f"{ident(col)} IS NULL" for col in numeric) + ")"
    if name == "breadth":
        missing += " OR (kind IN ('breadth', 'summary') AND (advancers IS NULL OR decliners IS NULL OR unchanged IS NULL))"
    flags = {
        "type_error": "is_type_error", "missing": "is_missing", "duplicate": "is_duplicate",
        "category_normalized": "is_category_normalized", "unit_normalized": "is_unit_normalized",
        "outlier": "is_outlier", **validation,
    }
    invalid = " OR ".join(("is_type_error", *[f"({clause})" for clause in validation.values()]))
    if outlier:
        # Price and turnover series can trend. Fences are per ticker and calendar year.
        outlier_sql = f"""stats AS (
            SELECT ticker, year(date) AS year, count({outlier}) AS n,
                   quantile_cont({outlier}, [0.25, 0.75]) AS quartiles
            FROM ranked WHERE NOT is_duplicate GROUP BY 1, 2
        ), scored AS (
            SELECT ranked.*, coalesce(n >= 8 AND
                ({outlier} < quartiles[1] - 1.5 * (quartiles[2] - quartiles[1]) OR
                 {outlier} > quartiles[2] + 1.5 * (quartiles[2] - quartiles[1])), false) AS is_outlier
            FROM ranked LEFT JOIN stats ON ranked.ticker = stats.ticker AND year(ranked.date) = stats.year
        )"""
    else:
        outlier_sql = "scored AS (SELECT *, false AS is_outlier FROM ranked)"
    landed = bool(fields.columns)
    source = raw if landed else "(SELECT 1 WHERE false)"
    partition = ", ".join(map(ident, keys))
    order = "TRY_CAST(_ingested_at AS TIMESTAMPTZ) DESC NULLS LAST"
    if name in {"bars", "foreign", "valuation", "investor_flow", "vn30_weights"}:
        order += ", quote_timestamp DESC NULLS LAST"
    order += ", _row_hash DESC NULLS LAST"
    projection = ", ".join([
        *fields.projections,
        f"coalesce({' OR '.join(fields.errors) or 'false'}, false) AS is_type_error",
        f"coalesce({' OR '.join(fields.category_changes) or 'false'}, false) AS is_category_normalized",
        f"coalesce({' OR '.join(fields.units) or 'false'}, false) AS is_unit_normalized",
    ])
    cleaned = "SELECT typed.*" + (", " + ", ".join(extra) if extra else "") + " FROM typed"
    _create(wh, table, f"""
        WITH typed AS (SELECT {projection} FROM {source}),
        cleaned AS ({cleaned}),
        ranked AS (
            SELECT *, {missing} AS is_missing,
                row_number() OVER (PARTITION BY {partition} ORDER BY {order}) > 1 AS is_duplicate
            FROM cleaned
        ), {outlier_sql}
        SELECT *, false AS is_imputed, coalesce({invalid}, false) AS is_invalid,
            {_flags(flags)} AS dq_flags FROM scored
    """, *([raw] if landed else []))
    return table, landed, tuple(dict.fromkeys((*required, *numeric))), correlated


def _period_date(period):
    return f"""CASE
        WHEN regexp_full_match({period}, '[0-9]{{4}}') THEN TRY_CAST({period} || '-01-01' AS DATE)
        WHEN regexp_full_match({period}, '[0-9]{{4}}-Q[1-4]')
            THEN make_date(CAST(left({period}, 4) AS INTEGER), CAST(right({period}, 1) AS INTEGER) * 3 - 2, 1)
        WHEN regexp_full_match({period}, '[0-9]{{4}}-[0-9]{{2}}') THEN TRY_CAST({period} || '-01' AS DATE)
        WHEN regexp_full_match({period}, '[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}') THEN TRY_CAST({period} AS DATE)
    END"""


def _key_coverage(wh, observations):
    """Conform known old province names and list the peers for the province dimension."""
    boundary = pd.read_csv(RESOURCES / "province_63_to_34.csv")
    regions = pd.read_csv(RESOURCES / "province_region.csv").set_index("province")["region"].to_dict()
    mergers = dict(zip(boundary["old_province"], boundary["new_province"]))
    previous = defaultdict(list)
    for old, new in mergers.items():
        previous[new].append(old)
    slugs = {ascii_key(name).replace(" ", "_"): name for name in previous}
    aliases = {
        name: (code, code) for code, name in slugs.items()
    }
    aliases.update({code: (code, code) for code in slugs})
    province_values = observations.loc[observations["geo_type"].str.lower().eq("province"), "geo"].dropna().unique()
    for raw in province_values:
        old = normalize_province(raw)
        post = mergers.get(old, slugs.get(ascii_key(raw).replace(" ", "_")))
        if post:
            code = ascii_key(post).replace(" ", "_")
            aliases[raw] = (code, ascii_key(old or post).replace(" ", "_"))
    province_map = _frame(
        [{"raw_geo": name, "code": codes[0], "old_code": codes[1]} for name, codes in aliases.items()],
        ["raw_geo", "code", "old_code"],
    )
    ref = [
        {"geo": code, "geo_type": "province", "name_vi": name,
         "region": regions.get(name) or regions.get(previous[name][0]), "previous_provinces": sorted(previous[name])}
        for code, name in slugs.items()
    ] + [
        {"geo": code, "geo_type": "country", "name_vi": name, "region": "Đông Nam Á", "previous_provinces": []}
        for code, name in COUNTRIES.items()
    ] + [{"geo": "", "geo_type": "national", "name_vi": "Việt Nam", "region": "", "previous_provinces": []}]
    wh.con.register("_vm_province_map", province_map)
    wh.con.register("_vm_geo_ref", pd.DataFrame(ref))


def _catalog_tables(wh, catalog, sources):
    wh.con.register("_vm_catalog", _frame(catalog, (
        "id", "name_vi", "name_en", "sector", "unit", "frequency", "measure_type", "definition_vi",
        "note_vi", "source_id", "last_updated", "next_release", "higher_is_better",
    )))
    wh.con.register("_vm_sources", _frame(sources, (
        "id", "publisher", "title_vi", "url", "method", "license", "robots",
        "robots_checked_at", "fetched_at", "next_release",
    )))
    _create(wh, "gold.dim_indicator", """
        SELECT id AS indicator_key, id AS indicator_id, * EXCLUDE(id, higher_is_better), note_vi AS comparability_note_vi,
            TRY_CAST(higher_is_better AS BOOLEAN) AS higher_is_better FROM _vm_catalog
    """)
    _create(wh, "gold.dim_source", "SELECT id AS source_key, id AS source_id, * EXCLUDE(id) FROM _vm_sources")


def _unit_factor(column):
    return f"""CASE lower({column})
        WHEN 'đồng' THEN 1 WHEN 'nghìn đồng' THEN 1000 WHEN 'triệu đồng' THEN 1000000
        WHEN 'tỷ đồng' THEN 1000000000 WHEN 'nghìn tỷ đồng' THEN 1000000000000
        WHEN 'usd' THEN 1 WHEN 'nghìn usd' THEN 1000 WHEN 'triệu usd' THEN 1000000
        WHEN 'tỷ usd' THEN 1000000000
    END"""


def _silver_indicator(wh, observations, run_id):
    observations = _frame(observations, OBS_COLUMNS)
    observations["geo"] = observations["geo"].str.strip()
    observations["run_id"] = observations["run_id"].fillna(run_id)
    observations["_row_hash"] = row_hash(observations.drop(columns="run_id"))
    _key_coverage(wh, observations)
    bronze = wh.write("bronze", "vm_observations", observations, parquet=False)
    inputs = [f"bronze.{name}" for name in ("vm_wdi", "vm_nso", "vm_sbv", "vm_press", "vm_transfers")
              if wh.exists("bronze", name)]
    _lineage(wh, inputs, bronze, "normalize")
    flags = {
        "type_error": "is_type_error", "missing": "is_missing", "duplicate": "is_duplicate",
        "category_normalized": "is_category_normalized", "unit_normalized": "is_unit_normalized",
        "imputed": "is_imputed", "outlier": "is_outlier", "unit_mismatch": "unit_mismatch",
        "measure_mismatch": "measure_mismatch", "share_range": "share_range",
        "ytd_decrease": "ytd_decrease", "parts_balance": "parts_balance",
        "unverified_evidence": "unverified_evidence",
    }
    _create(wh, "silver.vm_observations", f"""
        WITH typed AS (
            SELECT lower(nullif(trim(indicator_id), '')) AS indicator_id,
                nullif(trim(period), '') AS period, trim(coalesce(geo, '')) AS raw_geo,
                coalesce(lower(nullif(trim(geo_type), '')), 'national') AS geo_type,
                lower(nullif(trim(source_id), '')) AS source_id, nullif(trim(unit), '') AS raw_unit,
                CASE lower(trim(measure_type)) WHEN 'month' THEN 'level' WHEN 'avg_ytd' THEN 'ytd'
                    ELSE lower(nullif(trim(measure_type), '')) END AS measure_type,
                {_number('value')} AS raw_value, nullif(trim(value), '') AS raw_value_text,
                TRY_CAST(published_date AS DATE) AS published_date, source_url, evidence, parser_version, run_id, _row_hash,
                coalesce(NOT TRY_CAST(evidence_ok AS BOOLEAN), false) AS unverified_evidence
            FROM {bronze}
        ), tagged AS (
            SELECT typed.*, {_period_date('period')} AS date,
                CASE geo_type
                    WHEN 'national' THEN ''
                    WHEN 'province' THEN coalesce(p.code, raw_geo)
                    WHEN 'ministry' THEN raw_geo
                    ELSE upper(raw_geo)
                END AS geo,
                CASE WHEN geo_type = 'province' AND typed.source_id = 'transfers'
                    THEN coalesce(p.old_code, raw_geo) END AS constituent,
                coalesce(c.unit, raw_unit) AS unit, c.measure_type AS expected_measure,
                c.indicator_id IS NOT NULL AND c.measure_type IS DISTINCT FROM typed.measure_type AS measure_mismatch,
                CASE
                    WHEN lower(raw_unit) = lower(coalesce(c.unit, raw_unit)) THEN 1.0
                    WHEN ends_with(lower(raw_unit), 'đồng') AND ends_with(lower(c.unit), 'đồng')
                      OR ends_with(lower(raw_unit), 'usd') AND ends_with(lower(c.unit), 'usd')
                    THEN {_unit_factor('raw_unit')} / {_unit_factor('c.unit')}
                END AS factor
            FROM typed LEFT JOIN _vm_province_map p USING (raw_geo)
            LEFT JOIN gold.dim_indicator c USING (indicator_id)
        ), ranked AS (
            SELECT *, geo <> raw_geo AS is_category_normalized, coalesce(factor <> 1, false) AS is_unit_normalized,
                raw_unit IS NOT NULL AND factor IS NULL AS unit_mismatch,
                (period IS NOT NULL AND date IS NULL) OR (raw_value_text IS NOT NULL AND raw_value IS NULL) AS is_type_error,
                indicator_id IS NULL OR date IS NULL OR source_id IS NULL OR raw_unit IS NULL OR raw_value IS NULL
                    OR (geo_type <> 'national' AND geo = '') OR measure_type IS NULL AS is_missing,
                raw_value * factor AS actual,
                row_number() OVER (
                    PARTITION BY indicator_id, period, geo, geo_type, constituent, measure_type, unit, source_id
                    ORDER BY unverified_evidence, (factor IS NOT NULL) DESC, published_date DESC NULLS LAST, _row_hash DESC
                ) > 1 AS is_duplicate,
                CASE WHEN measure_type = 'ytd' THEN year(date) END AS ytd_year
            FROM tagged
        ), work AS (
            SELECT *, last_value(CASE WHEN actual IS NOT NULL AND NOT unverified_evidence THEN date END IGNORE NULLS) OVER prior AS previous_date,
                last_value(CASE WHEN NOT unverified_evidence THEN actual END IGNORE NULLS) OVER prior AS previous_value,
                first_value(CASE WHEN actual IS NOT NULL AND NOT unverified_evidence THEN date END IGNORE NULLS) OVER future AS next_date,
                first_value(CASE WHEN NOT unverified_evidence THEN actual END IGNORE NULLS) OVER future AS next_value
            FROM ranked WHERE NOT is_duplicate
            WINDOW series AS (PARTITION BY indicator_id, source_id, geo_type, geo, constituent, measure_type, unit, ytd_year
                              ORDER BY date NULLS LAST, period),
                prior AS (series ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
                future AS (series ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING)
        ), estimated AS (
            SELECT * EXCLUDE (previous_date, previous_value, next_date, next_value),
                coalesce(actual,
                    CASE WHEN raw_value_text IS NULL AND factor IS NOT NULL AND next_date > date AND date > previous_date
                        THEN previous_value + (next_value - previous_value) * (date - previous_date) / (next_date - previous_date)
                    END) AS value,
                indicator_id IN {YTD_LEVELS} AND measure_type = 'ytd' AND actual < previous_value AS ytd_decrease
            FROM work
            UNION ALL BY NAME
            SELECT *, actual AS value, false AS ytd_decrease FROM ranked WHERE is_duplicate
        ), stats AS (
            SELECT indicator_id, source_id, geo_type, geo, constituent, measure_type, unit,
                count(actual) AS n, quantile_cont(actual, [0.25, 0.75]) AS quartiles
            FROM estimated WHERE NOT is_duplicate AND NOT unverified_evidence GROUP BY ALL
        ), parts AS (
            SELECT source_id, geo_type, geo, period, unit, sum(actual) AS total_parts
            FROM estimated
            WHERE indicator_id IN ('fdi_cap_moi_ytd', 'fdi_dieu_chinh_ytd', 'fdi_gop_von_ytd')
                AND measure_type = 'ytd' AND NOT is_duplicate AND NOT unverified_evidence AND actual IS NOT NULL
            GROUP BY ALL HAVING count(DISTINCT indicator_id) = 3
        ), checked AS (
            SELECT e.*,
                actual IS NULL AND value IS NOT NULL AS is_imputed,
                coalesce(n >= 8 AND
                    (actual < quartiles[1] - 1.5 * (quartiles[2] - quartiles[1]) OR
                     actual > quartiles[2] + 1.5 * (quartiles[2] - quartiles[1])), false) AS is_outlier,
                e.measure_type = 'share' AND e.unit = '%' AND (value < 0 OR value > 100) AS share_range,
                e.indicator_id = 'fdi_dang_ky_ytd' AND e.measure_type = 'ytd'
                    AND abs(actual - total_parts) > greatest(abs(actual) * 0.01, 0.01) AS parts_balance
            FROM estimated e LEFT JOIN stats s ON e.indicator_id = s.indicator_id AND e.source_id = s.source_id
                AND e.geo_type = s.geo_type AND e.geo = s.geo AND e.constituent IS NOT DISTINCT FROM s.constituent
                AND e.measure_type = s.measure_type AND e.unit = s.unit
            LEFT JOIN parts p ON e.source_id = p.source_id AND e.geo_type = p.geo_type AND e.geo = p.geo
                AND e.period = p.period AND e.unit = p.unit
        )
        SELECT * EXCLUDE(raw_value_text, expected_measure, factor, actual, ytd_year),
            coalesce(is_type_error OR unit_mismatch OR measure_mismatch OR share_range OR ytd_decrease
                OR parts_balance OR unverified_evidence, false) AS is_invalid,
            {_flags(flags)} AS dq_flags
        FROM checked
    """, bronze, "gold.dim_indicator")


def _indicator_star(wh):
    silver = "silver.vm_observations"
    _create(wh, "gold.dim_geo", f"""
        WITH base AS (
            SELECT geo, geo_type, name_vi, region, previous_provinces::VARCHAR[] AS previous_provinces
            FROM _vm_geo_ref
            UNION ALL
            SELECT DISTINCT s.geo, s.geo_type, s.geo AS name_vi, '' AS region, []::VARCHAR[]
            FROM {silver} s WHERE s.geo <> '' AND NOT EXISTS (
                SELECT 1 FROM _vm_geo_ref r WHERE r.geo = s.geo AND r.geo_type = s.geo_type
            )
        )
        SELECT geo_type || ':' || geo AS geo_key, geo AS code, * FROM base
    """, silver)
    _create(wh, "gold.fact_indicator", f"""
        WITH current_rows AS (
            SELECT * FROM {silver}
            WHERE NOT is_duplicate AND date IS NOT NULL AND indicator_id IS NOT NULL AND source_id IS NOT NULL
                AND (geo_type = 'national' OR geo <> '') AND unit IS NOT NULL AND measure_type IS NOT NULL
        ), consolidated AS (
            SELECT indicator_id, period, date, geo, geo_type, unit, measure_type, source_id,
                CASE WHEN count(value) = count(*) THEN sum(value) END AS value,
                arg_max(source_url, published_date) AS source_url, max(published_date) AS published_date,
                NULL::VARCHAR AS evidence, any_value(parser_version) AS parser_version, any_value(run_id) AS run_id,
                bool_or(is_invalid) AS is_invalid, bool_or(is_imputed) AS is_imputed,
                bool_or(is_outlier) AS is_outlier, list_sort(list_distinct(flatten(list(dq_flags)))) AS dq_flags,
                count(*) AS constituent_count
            FROM current_rows
            WHERE constituent IS NOT NULL
            GROUP BY ALL
        ), fact AS (
            SELECT indicator_id, period, date, geo, geo_type, unit, measure_type, source_id, value,
                source_url, published_date, evidence, parser_version, run_id, is_invalid, is_imputed,
                is_outlier, dq_flags, 1::BIGINT AS constituent_count
            FROM current_rows WHERE constituent IS NULL
            UNION ALL SELECT * FROM consolidated
        )
        SELECT *, indicator_id AS indicator_key, period AS period_key, geo_type || ':' || geo AS geo_key,
            source_id AS source_key, strftime(date, '%Y%m%d')::INTEGER AS date_key FROM fact
    """, silver, "gold.dim_geo", "gold.dim_indicator", "gold.dim_source")
    wh.con.execute("""
        UPDATE gold.dim_indicator AS d SET last_updated = dates.last_updated
        FROM (SELECT indicator_id, max(published_date)::VARCHAR AS last_updated
              FROM gold.fact_indicator GROUP BY indicator_id) dates
        WHERE d.indicator_id = dates.indicator_id AND d.last_updated IS NULL
    """)


def _market_star(wh):
    _create(wh, "gold.dim_security", f"""
        WITH tickers AS (
            SELECT ticker FROM silver.vm_fq_bars
            UNION SELECT ticker FROM silver.vm_fq_roster
            UNION SELECT ticker FROM silver.vm_fq_bank_ratios
            UNION SELECT ticker FROM silver.vm_fq_valuation
        ), bank_tickers AS (
            SELECT DISTINCT ticker FROM silver.vm_fq_bank_ratios WHERE ticker IS NOT NULL
            UNION SELECT geo FROM gold.fact_indicator WHERE geo_type IN ('ticker', 'bank') AND indicator_id IN (
                SELECT indicator_id FROM gold.dim_indicator WHERE sector = 'banking'
            )
        ), roster AS (
            SELECT ticker, name_vi, sector_vi, exchange, icb_l1, icb_l2, icb_l3, icb_l4, icb_l5
            FROM silver.vm_fq_roster WHERE NOT is_duplicate AND NOT is_invalid AND exchange IS NOT NULL
            QUALIFY row_number() OVER (PARTITION BY ticker ORDER BY date DESC NULLS LAST,
                TRY_CAST(_ingested_at AS TIMESTAMPTZ) DESC NULLS LAST, _row_hash DESC NULLS LAST) = 1
        )
        SELECT t.ticker AS security_key, t.ticker, coalesce(r.name_vi, t.ticker) AS name_vi,
            coalesce(r.exchange, CASE t.ticker WHEN 'VNINDEX' THEN 'HOSE' WHEN 'VN30' THEN 'HOSE'
                WHEN 'HNXINDEX' THEN 'HNX' WHEN 'UPCOMINDEX' THEN 'UPCOM' END) AS exchange,
            r.* EXCLUDE(ticker, name_vi, exchange),
            b.ticker IS NOT NULL OR coalesce(r.icb_l2 = 'BANKS_L2', false) AS is_bank,
            t.ticker IN ({INDEXES}) AS is_index
        FROM (SELECT * FROM tickers UNION SELECT * FROM bank_tickers) t
        LEFT JOIN roster r USING (ticker) LEFT JOIN bank_tickers b USING (ticker)
        WHERE t.ticker IS NOT NULL
    """, "silver.vm_fq_roster", "silver.vm_fq_bars", "silver.vm_fq_bank_ratios",
         "silver.vm_fq_valuation", "gold.fact_indicator")
    _create(wh, "gold.dim_bank", """
        SELECT ticker AS bank_key, ticker, name_vi,
            CASE WHEN ticker IN ('BID', 'CTG', 'VCB') THEN 'SOCB' ELSE 'private' END AS "group"
        FROM gold.dim_security WHERE is_bank
    """, "gold.dim_security")
    _create(wh, "gold.fact_security_daily", """
        SELECT s.ticker, s.date, strftime(s.date, '%Y%m%d')::INTEGER AS date_key, d.security_key,
            s.open, s.high, s.low, s.close, s.volume, s.value, s.bu, s.sd, s.fb, s.fs, s.fn,
            d.exchange, d.icb_l2, d.is_index, CASE WHEN d.is_index THEN 'index' ELSE 'stock' END AS scope,
            price_basis, 'fiinquant' AS source_id, 'fiinquant' AS source_key,
            run_id, dq_flags, is_invalid, is_outlier, is_imputed
        FROM silver.vm_fq_bars s JOIN gold.dim_security d USING (ticker)
        WHERE NOT s.is_duplicate AND s.date IS NOT NULL
    """, "silver.vm_fq_bars", "gold.dim_security")
    _create(wh, "gold.fact_valuation_daily", """
        SELECT ticker, date, strftime(date, '%Y%m%d')::INTEGER AS date_key, ticker AS security_key,
            scope, pe, pb, 'fiinquant' AS source_id, 'fiinquant' AS source_key,
            run_id, dq_flags, is_invalid, is_outlier
        FROM silver.vm_fq_valuation
        WHERE NOT is_duplicate AND ticker IS NOT NULL AND date IS NOT NULL
    """, "silver.vm_fq_valuation", "gold.dim_security")
    _create(wh, "gold.fact_bank_ratio_quarter", """
        SELECT ticker, ticker AS bank_key, period, period AS period_key, date, year, quarter,
            nim, pb, pe, npl_proxy, coverage, ldr, loan_growth_yoy, deposit_growth_yoy, interest_income_growth_yoy,
            book_value_per_share, eps, net_interest_income, profit_attributable,
            'fiinquant' AS source_id, 'fiinquant' AS source_key, run_id, dq_flags, is_invalid, is_outlier
        FROM silver.vm_fq_bank_ratios
        WHERE NOT is_duplicate AND ticker IS NOT NULL AND date IS NOT NULL
    """, "silver.vm_fq_bank_ratios", "gold.dim_bank")
    _create(wh, "gold.fact_market_breadth_daily", """
        WITH trade_dates AS (
            SELECT DISTINCT date FROM gold.fact_security_daily WHERE ticker = 'VNINDEX'
            UNION
            SELECT DISTINCT date FROM gold.fact_security_daily WHERE exchange = 'HOSE' AND NOT is_index
                AND NOT EXISTS (SELECT 1 FROM gold.fact_security_daily WHERE ticker = 'VNINDEX')
        ), previous_session AS (
            SELECT date, lag(date) OVER (ORDER BY date) AS previous_date FROM trade_dates
        ), turnover AS (
            SELECT date, ticker, close, run_id, lag(date) OVER series AS prior_quote_date,
                lag(close) OVER series AS prior_quote_close
            FROM gold.fact_security_daily
            WHERE exchange = 'HOSE' AND NOT is_index AND close > 0 AND volume > 0
                AND NOT list_has(dq_flags, 'ohlc_bounds') AND NOT list_has(dq_flags, 'type_error')
            WINDOW series AS (PARTITION BY ticker ORDER BY date)
        ), derived AS (
            SELECT date, count_if(close > prior_quote_close) AS advancers,
                count_if(close < prior_quote_close) AS decliners, count_if(close = prior_quote_close) AS unchanged,
                count(*) AS compared, max(run_id) AS bars_run_id
            FROM turnover JOIN previous_session USING (date)
            WHERE prior_quote_date = previous_date GROUP BY date
        ), vendor AS (
            SELECT date, advancers::BIGINT AS vendor_advancers, decliners::BIGINT AS vendor_decliners,
                unchanged::BIGINT AS vendor_unchanged, _ingested_at AS vendor_as_of, run_id AS vendor_run_id
            FROM silver.vm_fq_breadth
            WHERE index_code = 'VNINDEX' AND kind IN ('breadth', 'summary')
                AND NOT is_duplicate AND NOT is_invalid AND NOT is_missing
        )
        SELECT date, strftime(date, '%Y%m%d')::INTEGER AS date_key,
            'fiinquant' AS source_id, 'fiinquant' AS source_key,
            derived.* EXCLUDE(date), vendor.* EXCLUDE(date),
            'Đếm mã HOSE có giao dịch ở hai phiên liên tiếp theo chênh lệch giá đóng cửa điều chỉnh. '
            'Mã và sàn lấy từ ảnh chụp danh mục gần nhất. '
            'Ảnh chụp VN-Index của FiinQuant có thời điểm và phạm vi quan sát riêng.' AS method_vi
        FROM derived FULL JOIN vendor USING (date)
    """, "gold.fact_security_daily", "silver.vm_fq_breadth")


def _calendar(wh):
    _create(wh, "gold.dim_date", """
        WITH bounds AS (
            SELECT min(date) AS first_date, max(date) AS last_date FROM (
                SELECT min(date) AS date FROM gold.fact_security_daily
                UNION ALL SELECT max(date) FROM gold.fact_security_daily
                UNION ALL SELECT date FROM gold.fact_valuation_daily
                UNION ALL SELECT date FROM gold.fact_market_breadth_daily
                UNION ALL SELECT date FROM gold.fact_indicator
                UNION ALL SELECT date FROM gold.fact_bank_ratio_quarter
            )
        ), dates AS (
            SELECT calendar_date::DATE AS date FROM bounds,
                unnest(generate_series(first_date, last_date, INTERVAL 1 DAY)) dates(calendar_date)
        ), traded AS (
            SELECT DISTINCT date FROM gold.fact_security_daily WHERE ticker IN ('VNINDEX', 'HNXINDEX', 'UPCOMINDEX')
            UNION
            SELECT DISTINCT date FROM gold.fact_security_daily WHERE NOT EXISTS (
                SELECT 1 FROM gold.fact_security_daily WHERE ticker IN ('VNINDEX', 'HNXINDEX', 'UPCOMINDEX')
            )
        )
        SELECT strftime(d.date, '%Y%m%d')::INTEGER AS date_key, d.date, day(d.date) AS day,
            month(d.date) AS month, quarter(d.date) AS quarter, year(d.date) AS year,
            t.date IS NOT NULL AS is_trading_day
        FROM dates d LEFT JOIN traded t USING (date)
    """, "gold.fact_security_daily", "gold.fact_valuation_daily", "gold.fact_market_breadth_daily",
         "gold.fact_indicator", "gold.fact_bank_ratio_quarter")
    _create(wh, "gold.dim_period", """
        WITH periods AS (
            SELECT DISTINCT strftime(date, '%Y-%m') AS period FROM gold.dim_date
            UNION SELECT DISTINCT year::VARCHAR || '-Q' || quarter FROM gold.dim_date
            UNION SELECT DISTINCT year::VARCHAR FROM gold.dim_date
            UNION SELECT DISTINCT period FROM gold.fact_indicator
            UNION SELECT DISTINCT period FROM gold.fact_bank_ratio_quarter
        )
        SELECT period AS period_key, period, """ + _period_date("period") + """ AS start_date,
            CASE WHEN len(period) = 4 THEN 'year' WHEN contains(period, '-Q') THEN 'quarter'
                WHEN len(period) = 7 THEN 'month' ELSE 'day' END AS frequency,
            year(start_date) AS year, quarter(start_date) AS quarter, month(start_date) AS month
        FROM periods
    """, "gold.dim_date", "gold.fact_indicator", "gold.fact_bank_ratio_quarter")


def _serving_views(wh):
    queries = {
        "v_budget_execution": ("""
            SELECT f.* FROM gold.fact_indicator f JOIN gold.dim_indicator d USING (indicator_id)
            WHERE d.sector = 'public_finance' AND f.geo_type = 'national' AND NOT starts_with(f.indicator_id, 'dtc_')
        """, ("gold.fact_indicator", "gold.dim_indicator")),
        "v_public_investment": ("""
            SELECT * FROM gold.fact_indicator WHERE starts_with(indicator_id, 'dtc_')
        """, ("gold.fact_indicator",)),
        "v_fdi": ("""
            SELECT f.* FROM gold.fact_indicator f JOIN gold.dim_indicator d USING (indicator_id) WHERE d.sector = 'fdi'
        """, ("gold.fact_indicator", "gold.dim_indicator")),
        "v_bank_health_quarter": ("""
            WITH reported AS (
                SELECT geo AS ticker, f.period, f.indicator_id, f.value, f.source_id
                FROM gold.fact_indicator f LEFT JOIN gold.dim_indicator d USING (indicator_id)
                WHERE f.geo_type IN ('bank', 'ticker') AND regexp_full_match(f.period, '[0-9]{4}-Q[1-4]')
                    AND f.indicator_id IN ('bank_npl', 'bank_group2', 'bank_coverage')
                    AND f.measure_type = 'ratio' AND f.unit = '%'
                    AND NOT f.is_invalid AND NOT f.is_imputed AND f.value IS NOT NULL
                QUALIFY row_number() OVER (PARTITION BY geo, f.period, f.indicator_id
                    ORDER BY (f.source_id = d.source_id) DESC NULLS LAST,
                        f.published_date DESC NULLS LAST, f.source_id) = 1
            ), reports AS (
                SELECT ticker, period,
                    max(value) FILTER (WHERE indicator_id = 'bank_npl') AS bank_npl,
                    max(source_id) FILTER (WHERE indicator_id = 'bank_npl') AS npl_source_id,
                    max(value) FILTER (WHERE indicator_id = 'bank_group2') AS bank_group2,
                    max(source_id) FILTER (WHERE indicator_id = 'bank_group2') AS group2_source_id,
                    max(value) FILTER (WHERE indicator_id = 'bank_coverage') AS bank_coverage,
                    max(source_id) FILTER (WHERE indicator_id = 'bank_coverage') AS coverage_source_id
                FROM reported GROUP BY ticker, period
            )
            SELECT ticker, period, ticker AS bank_key, period AS period_key,
                f.* EXCLUDE(ticker, period, bank_key, period_key), b.name_vi, b."group",
                r.* EXCLUDE(ticker, period)
            FROM gold.fact_bank_ratio_quarter f FULL JOIN reports r USING (ticker, period)
            LEFT JOIN gold.dim_bank b USING (ticker)
        """, ("gold.fact_bank_ratio_quarter", "gold.dim_bank", "gold.fact_indicator", "gold.dim_indicator")),
        "v_capital_market_daily": ("""
            WITH market AS (
                SELECT date, max(close) FILTER (WHERE ticker = 'VNINDEX' AND NOT is_invalid) AS vnindex_close,
                    sum(value) FILTER (WHERE NOT is_index AND NOT is_invalid) AS trading_value_vnd,
                    sum(fn) FILTER (WHERE NOT is_index AND NOT is_invalid) AS foreign_net_vnd
                FROM gold.fact_security_daily GROUP BY date
            )
            SELECT date, market.* EXCLUDE(date), b.* EXCLUDE(date)
            FROM market FULL JOIN gold.fact_market_breadth_daily b USING (date)
        """, ("gold.fact_security_daily", "gold.fact_market_breadth_daily")),
        "v_real_estate": ("""
            SELECT f.* FROM gold.fact_indicator f JOIN gold.dim_indicator d USING (indicator_id)
            WHERE d.sector = 'real_estate'
        """, ("gold.fact_indicator", "gold.dim_indicator")),
        "v_asean_rank": ("""
            SELECT f.*, g.name_vi, rank() OVER (PARTITION BY indicator_id, period, f.source_id
                ORDER BY CASE WHEN coalesce(d.higher_is_better, true) THEN f.value ELSE -f.value END DESC) AS rank
            FROM gold.fact_indicator f JOIN gold.dim_indicator d USING (indicator_id)
            JOIN gold.dim_geo g USING (geo_key)
            WHERE d.sector = 'asean' AND f.geo_type = 'country' AND f.value IS NOT NULL
                AND NOT f.is_imputed AND NOT f.is_invalid
        """, ("gold.fact_indicator", "gold.dim_indicator", "gold.dim_geo")),
        "v_province_scorecard": ("""
            SELECT f.*, g.code, g.name_vi, g.region FROM gold.fact_indicator f
            JOIN gold.dim_geo g USING (geo_key) WHERE f.geo_type = 'province'
        """, ("gold.fact_indicator", "gold.dim_geo")),
    }
    for name, (query, parents) in queries.items():
        _create(wh, f"gold.{name}", query, *parents, view=True)
    return [f"gold.{name}" for name in queries]


def _profile(wh, table, source_id, fields, correlated=None):
    indicator = table == "silver.vm_observations"
    where = "WHERE source_id = ?" if indicator else ""
    params = [source_id] if indicator else []
    queries = [
        "count(*)", "min(date)::VARCHAR", "max(date)::VARCHAR", "count_if(is_duplicate)",
        "count_if(is_outlier)", "count_if(len(dq_flags) = 0)", "count_if(NOT is_duplicate)",
        "count_if(NOT is_duplicate AND NOT is_invalid AND (NOT is_missing OR is_imputed))",
    ] + [f"count(*) FILTER (WHERE {ident(col)} IS NULL)" for col in fields]
    if correlated:
        x, y = map(ident, correlated)
        queries.append(f"corr({x}, {y}) FILTER (WHERE NOT is_duplicate AND NOT is_invalid)")
    rows, first, last, dup, outliers, raw_good, current, clean_good, *stats = wh.con.execute(
        f"SELECT {', '.join(queries)} FROM {table} {where}", params,
    ).fetchone()
    flags = dict(wh.con.execute(f"""
        SELECT flag, count(*) FROM (SELECT unnest(dq_flags) AS flag FROM {table} {where})
        GROUP BY flag ORDER BY flag
    """, params).fetchall())

    gaps = 0
    if indicator:
        gaps = wh.con.execute(f"""
            WITH series AS (
                SELECT len(period) AS precision, contains(period, '-Q') AS is_quarter,
                    min(date) AS first_date, max(date) AS last_date, count(DISTINCT date) AS dates
                FROM {table} {where} AND date IS NOT NULL
                GROUP BY indicator_id, geo_type, geo, constituent, measure_type, unit, precision, is_quarter
            )
            SELECT coalesce(sum(CASE
                WHEN precision = 4 THEN date_diff('year', first_date, last_date) + 1 - dates
                WHEN is_quarter THEN date_diff('quarter', first_date, last_date) + 1 - dates
                WHEN precision = 7 THEN date_diff('month', first_date, last_date) + 1 - dates
                ELSE 0 END), 0) FROM series
        """, params).fetchone()[0]
    elif table.endswith("bank_ratios"):
        gaps = wh.con.execute(f"""
            SELECT coalesce(sum(gaps), 0) FROM (
                SELECT date_diff('quarter', min(date), max(date)) + 1 - count(DISTINCT date) AS gaps
                FROM {table} WHERE date IS NOT NULL GROUP BY ticker
            )
        """).fetchone()[0]
    elif table.endswith(("bars", "foreign", "valuation", "investor_flow")):
        grouping = "ticker, scope" if table.endswith("valuation") else "ticker"
        gaps = wh.con.execute(f"""
            WITH calendar AS (
                SELECT date, row_number() OVER (ORDER BY date) AS session
                FROM gold.dim_date WHERE is_trading_day
            )
            SELECT coalesce(sum(gaps), 0) FROM (
                SELECT max(session) - min(session) + 1 - count(DISTINCT session) AS gaps
                FROM {table} JOIN calendar USING (date) GROUP BY {grouping}
            )
        """).fetchone()[0]

    correlation = stats[-1] if correlated else None
    correlations = {
        " / ".join(correlated): float(correlation) if pd.notna(correlation) and abs(correlation) != float("inf") else None,
    } if correlated else {}
    if indicator:
        matched = wh.con.execute(f"""
            SELECT a.indicator_id || ' / ' || b.indicator_id, corr(a.value, b.value)
            FROM {table} a JOIN {table} b USING (source_id, geo_type, geo, period)
            WHERE a.source_id = ? AND geo_type = 'national'
                AND (a.indicator_id, b.indicator_id) IN (('nsnn_thu_ytd', 'nsnn_chi_ytd'), ('cpi_yoy', 'iip_yoy'))
                AND NOT (a.is_invalid OR b.is_invalid OR a.is_duplicate OR b.is_duplicate OR a.is_imputed OR b.is_imputed)
            GROUP BY a.indicator_id, b.indicator_id HAVING count(*) >= 3
        """, params).fetchall()
        correlations = {label: float(coef) if pd.notna(coef) else None for label, coef in matched}

    profile = {
        "table": table, "source_id": source_id, "rows": rows, "date_from": first, "date_to": last,
        "columns": {c["name"]: c["type"] for c in wh.columns(table)},
        "missing": dict(zip(fields, stats[:len(fields)])), "duplicates": dup or 0,
        "time_gap_count": gaps, "outliers": outliers or 0, "correlations": correlations,
    }
    return profile, (raw_good or 0, current or 0, clean_good or 0, flags)


def _profiles(wh, landed):
    profiles, quality = [], {}
    inputs = [(table, "fiinquant", fields, corr) for table, present, fields, corr in landed if present]
    inputs += [("silver.vm_observations", source, ("period", "date", "value", "unit", "measure_type"), None)
               for (source,) in wh.con.execute("""
                   SELECT DISTINCT source_id FROM silver.vm_observations WHERE source_id IS NOT NULL ORDER BY source_id
               """).fetchall()]
    for table, source, fields, corr in inputs:
        profile, (raw_good, current, clean_good, flags) = _profile(wh, table, source, fields, corr)
        profiles.append(profile)
        counts = quality.setdefault(source, {"rows": 0, "raw_good": 0, "current": 0, "clean_good": 0,
                                            "flags": defaultdict(int)})
        counts["rows"] += profile["rows"]
        counts["raw_good"] += raw_good
        counts["current"] += current
        counts["clean_good"] += clean_good
        for flag, count in flags.items():
            counts["flags"][flag] += count
        wh.save_quality(DATASET, table, profile | {"flags": flags})
    return profiles, [
        {"source_id": source, "rows": count["rows"], "flags": dict(count["flags"]),
         "score_before": round(100 * count["raw_good"] / max(1, count["rows"]), 2),
         "score_after": round(100 * count["clean_good"] / max(1, count["current"]), 2)}
        for source, count in sorted(quality.items())
    ]


GRAINS = {
    "dim_date": "Một ngày lịch",
    "dim_period": "Một kỳ báo cáo",
    "dim_geo": "Một đơn vị địa lý hoặc chủ thể",
    "dim_indicator": "Một chỉ tiêu trong danh mục",
    "dim_source": "Một nguồn trong danh mục",
    "dim_security": "Một mã chứng khoán, ngành hoặc chỉ số",
    "dim_bank": "Một ngân hàng",
    "fact_indicator": "Một quan sát theo chỉ tiêu, kỳ, phạm vi, nguồn và cách đo",
    "fact_security_daily": "Một mã chứng khoán hoặc chỉ số mỗi ngày",
    "fact_valuation_daily": "Một mã cổ phiếu, ngành hoặc chỉ số mỗi ngày",
    "fact_bank_ratio_quarter": "Một ngân hàng mỗi quý",
    "fact_market_breadth_daily": "Một phiên giao dịch HOSE hoặc ngày có ảnh chụp",
}


def build_model(wh: Warehouse, observations: pd.DataFrame, catalog: list[dict], sources: list[dict],
                run_id: str) -> dict:
    """Rebuild silver and gold from the current landed data, preserving record provenance in silver."""
    con = wh.con
    started = now_iso()
    con.execute("BEGIN TRANSACTION")
    try:
        _catalog_tables(wh, catalog, sources)
        _silver_indicator(wh, observations, run_id)
        landed = [_silver_market(wh, name, run_id) for name in (
            "roster", "bars", "foreign", "valuation", "bank_ratios", "breadth", "vn30_weights", "investor_flow",
        )]
        _indicator_star(wh)
        _market_star(wh)
        _calendar(wh)
        views = _serving_views(wh)
        profiles, quality = _profiles(wh, landed)
        con.execute("COMMIT")
    except Exception as exc:
        con.execute("ROLLBACK")
        wh.log_run(run_id, DATASET, "model", "error", started, {"error_type": type(exc).__name__})
        raise
    finally:
        for name in ("_vm_catalog", "_vm_sources", "_vm_province_map", "_vm_geo_ref"):
            con.unregister(name)

    silver = ["silver.vm_observations", *[table for table, present, _, _ in landed if present]]
    gold = [f"gold.{name}" for name in GRAINS]
    bronze = [f"bronze.{name}" for name in ("vm_wdi", "vm_nso", "vm_sbv", "vm_press", "vm_transfers")
              if wh.exists("bronze", name)]
    bronze += [item.replace("silver.", "bronze.", 1) for item in silver]
    tables = []
    for table in (*bronze, *silver, *gold):
        layer, name = table.split(".")
        rows = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        tables.append({"name": table, "layer": layer, "rows": rows,
                       "grain_vi": GRAINS.get(name, "Một dòng từ nguồn dữ liệu")})
        if layer in {"silver", "gold"}:
            path = wh.lake / layer / f"{name}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            con.execute(f"COPY {table} TO ? (FORMAT PARQUET)", [path.as_posix()])
    for layer in ("silver", "gold"):
        wh.log_run(run_id, DATASET, layer, "ok", started,
                   {"rows": sum(table["rows"] for table in tables if table["layer"] == layer)})
    return {"tables": tables, "quality": quality, "profiles": profiles, "views": views}
