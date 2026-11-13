"""Transform step 2: data modelling — all four patterns from the DE workshop, generated as DuckDB SQL.

    OBT        gold.obt_<ds>                     one wide table: fastest for dashboards and ML
    Star       gold.fact_<ds> + gold.dim_*       Kimball star: date, geo, one dim per low-cardinality category
    Snowflake  gold.sf_dim_*                     normalised dims (province → province_2025, province → region;
                                                 date → month → year) sharing the star's fact keys
    Data Vault gold.hub_* / gold.lnk_<ds> / gold.sat_<ds>   DV 2.0: hash keys (md5 of business key),
                                                 load_dts, record_source, hashdiff on the satellite

Every statement is kept (models[...]["sql"]) and written to out/<ds>/models/*.sql so the team can show
the exact transformation in the pitch. Recommendation for a 28-hour hackathon: serve the dashboard from
OBT, present the Star schema as the semantic model; Snowflake/Data Vault are built to show we know the
trade-offs (auditability and change history vs. join cost) — see RATIONALE.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from ..vn import ascii_key
from .warehouse import Warehouse, ident

RES = Path(__file__).resolve().parents[1] / "resources"

RATIONALE = {
    "obt": "Một bảng phẳng: truy vấn dashboard/ML nhanh nhất, dễ cho đồng đội không rành SQL. Nhược: lặp dữ liệu, khó cập nhật.",
    "star": "Chuẩn Kimball: fact chứa số đo, dim chứa ngữ cảnh (thời gian, địa lý, phân loại). Dễ hiểu với người ra quyết định, slice/dice nhanh. Đây là mô hình trình bày chính.",
    "snowflake": "Chuẩn hoá dim (tỉnh → tỉnh sau sáp nhập 2025 → vùng; ngày → tháng → năm): bớt lặp, đúng hệ phân cấp hành chính mới. Đổi lại thêm join.",
    "data_vault": "Hub/Link/Satellite với hash key, load_dts, record_source: truy vết nguồn và lịch sử thay đổi khi ghép nhiều nguồn. Mạnh cho tích hợp dài hạn, nặng cho 28 giờ — dựng để chứng minh khả năng audit.",
}


def _ensure_ref_tables(wh: Warehouse):
    con = wh.con
    if not con.execute("SELECT count(*) FROM duckdb_tables() WHERE schema_name='meta' AND table_name='province_ref'").fetchall()[0][0]:
        merge = {r["old_province"]: r["new_province"] for r in csv.DictReader(open(RES / "province_63_to_34.csv", encoding="utf-8"))}
        region = {r["province"]: r["region"] for r in csv.DictReader(open(RES / "province_region.csv", encoding="utf-8"))}
        ref = pd.DataFrame([{"province": p, "province_2025": merge.get(p, p), "region": region.get(p)} for p in region])
        con.register("_ref", ref)
        con.execute("CREATE TABLE meta.province_ref AS SELECT * FROM _ref")
        con.unregister("_ref")


def _slug(c: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", ascii_key(c)).strip("_")[:40] or "col"


def plan_columns(df: pd.DataFrame, roles: dict) -> dict:
    cols = [c for c in df.columns if not c.startswith("_") and not c.endswith("__imputed")]
    time = [c for c in cols if roles.get(c) == "time"]
    time_col = None
    if time:
        dt = [c for c in time if pd.api.types.is_datetime64_any_dtype(df[c])]
        time_col = max(dt or time, key=lambda c: df[c].notna().mean())
    prov = next((c for c in cols if c.endswith("__province") and not c.endswith("__province_2025")), None)
    geo = [c for c in cols if roles.get(c) in ("geo",) and not c.endswith("__province_2025") and c != prov]
    cats = [c for c in cols if roles.get(c) == "category" and 2 <= df[c].nunique() <= 200]
    if not prov:  # non-province geo (district, country...) becomes a normal dimension
        cats = [c for c in geo if 2 <= df[c].nunique() <= 500] + cats
    measures = [c for c in cols if roles.get(c) == "numeric" and pd.api.types.is_numeric_dtype(df[c])]
    ids = [c for c in cols if roles.get(c) == "id"]
    return {"time": time_col, "time_is_date": bool(time_col and pd.api.types.is_datetime64_any_dtype(df[time_col])),
            "province": prov, "cats": cats[:12], "measures": measures, "ids": ids[:3]}


def build_models(wh: Warehouse, ds: str, silver: str, roles: dict, out_dir: Path | None = None) -> dict:
    _ensure_ref_tables(wh)
    df = wh.read(silver)
    p = plan_columns(df, roles)
    S = f"silver.{ident(silver.split('.', 1)[1])}"
    # every gold table is namespaced by dataset (<ds>__dim_date ...) so several datasets can live side by side
    T = lambda n: n if n.endswith("_" + ds) else f"{ds}__{n}"  # noqa: E731
    g = lambda n: f"gold.{ident(T(n))}"  # noqa: E731
    models: dict[str, dict] = {}

    # ---------------------------------------------------------------- OBT
    sel = ["s.*"]
    joins = ""
    if p["time"]:
        t = ident(p["time"])
        if p["time_is_date"]:
            sel += [f"year({t}) AS _year", f"quarter({t}) AS _quarter", f"month({t}) AS _month"]
        else:
            sel += [f"CAST({t} AS INTEGER) AS _year"]
    if p["province"]:
        sel += ["r.province_2025 AS _province_2025", "r.region AS _region"]
        joins = f" LEFT JOIN meta.province_ref r ON s.{ident(p['province'])} = r.province"
    obt_sql = f"CREATE OR REPLACE TABLE {g('obt_' + ds)} AS SELECT {', '.join(sel)} FROM {S} s{joins}"
    models["obt"] = {"sql": [obt_sql], "tables": [f"gold.obt_{ds}"]}

    # ---------------------------------------------------------------- STAR
    star_sql, star_tables, fk = [], [], []
    if p["time"]:
        t = ident(p["time"])
        if p["time_is_date"]:
            star_sql.append(f"""CREATE OR REPLACE TABLE {g('dim_date')} AS
WITH b AS (SELECT CAST(min({t}) AS DATE) lo, CAST(max({t}) AS DATE) hi FROM {S})
SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key, CAST(d AS DATE) AS date, year(d) AS year,
       quarter(d) AS quarter, month(d) AS month, CAST(strftime(d, '%Y%m') AS INTEGER) AS month_key,
       isodow(d) AS weekday, isodow(d) >= 6 AS is_weekend
FROM b, range(b.lo, b.hi + INTERVAL 1 DAY, INTERVAL 1 DAY) AS r(d)""")
            fk.append(("date_key", f"CAST(strftime(s.{t}, '%Y%m%d') AS INTEGER)", "dim_date"))
        else:
            star_sql.append(f"""CREATE OR REPLACE TABLE {g('dim_date')} AS
SELECT DISTINCT CAST({t} AS INTEGER) AS date_key, CAST({t} AS INTEGER) AS year FROM {S} WHERE {t} IS NOT NULL ORDER BY 1""")
            fk.append(("date_key", f"CAST(s.{t} AS INTEGER)", "dim_date"))
        star_tables.append(f"gold.{T('dim_date')}")
    if p["province"]:
        pc = ident(p["province"])
        star_sql.append(f"""CREATE OR REPLACE TABLE {g('dim_geo')} AS
SELECT row_number() OVER (ORDER BY v.province) AS geo_key, v.province, r.province_2025, r.region
FROM (SELECT DISTINCT {pc} AS province FROM {S} WHERE {pc} IS NOT NULL) v
LEFT JOIN meta.province_ref r USING (province)""")
        fk.append(("geo_key", f"s.{pc}", "dim_geo:province"))
        star_tables.append(f"gold.{T('dim_geo')}")
    for c in p["cats"]:
        sc, ci = _slug(c), ident(c)
        star_sql.append(f"""CREATE OR REPLACE TABLE {g('dim_' + sc)} AS
SELECT row_number() OVER (ORDER BY v) AS {sc}_key, v AS {ident(sc)} FROM (SELECT DISTINCT {ci} AS v FROM {S} WHERE {ci} IS NOT NULL)""")
        fk.append((f"{sc}_key", f"s.{ci}", f"dim_{sc}:{sc}"))
        star_tables.append(f"gold.{T('dim_' + sc)}")
    fsel, fjoin = ["row_number() OVER () AS fact_id"], []
    for i, (key, expr, dim) in enumerate(fk):
        if dim == "dim_date":
            fsel.append(f"{expr} AS {key}")
        else:
            dname, dcol = dim.split(":")
            fsel.append(f"d{i}.{key}")
            fjoin.append(f"LEFT JOIN {g(dname)} d{i} ON {expr} = d{i}.{ident(dcol)}")
    fsel += [f"s.{ident(c)} AS {ident(_slug(c))}" for c in p["ids"]]
    fsel += [f"s.{ident(c)} AS {ident(_slug(c))}" for c in p["measures"]]
    if "_src" in df.columns:
        fsel.append("s._src AS record_source")
    star_sql.append(f"CREATE OR REPLACE TABLE {g('fact_' + ds)} AS SELECT {', '.join(fsel)} FROM {S} s {' '.join(fjoin)}")
    star_tables.insert(0, f"gold.fact_{ds}")
    models["star"] = {"sql": star_sql, "tables": star_tables}

    # ---------------------------------------------------------------- SNOWFLAKE (normalised dims, same fact keys)
    sf_sql, sf_tables = [], []
    if p["province"]:
        sf_sql += [
            f"CREATE OR REPLACE TABLE {g('sf_dim_region')} AS SELECT row_number() OVER (ORDER BY region) AS region_key, region FROM (SELECT DISTINCT region FROM {g('dim_geo')} WHERE region IS NOT NULL)",
            f"CREATE OR REPLACE TABLE {g('sf_dim_province_2025')} AS SELECT row_number() OVER (ORDER BY province_2025) AS province_2025_key, province_2025 FROM (SELECT DISTINCT province_2025 FROM {g('dim_geo')} WHERE province_2025 IS NOT NULL)",
            f"""CREATE OR REPLACE TABLE {g('sf_dim_province')} AS SELECT gk.geo_key AS province_key, gk.province, p25.province_2025_key, rg.region_key
FROM {g('dim_geo')} gk LEFT JOIN {g('sf_dim_province_2025')} p25 USING (province_2025) LEFT JOIN {g('sf_dim_region')} rg USING (region)""",
        ]
        sf_tables += [f"gold.{T(n)}" for n in ("sf_dim_province", "sf_dim_province_2025", "sf_dim_region")]
    if p["time"] and p["time_is_date"]:
        sf_sql += [
            f"CREATE OR REPLACE TABLE {g('sf_dim_year')} AS SELECT DISTINCT year AS year_key FROM {g('dim_date')}",
            f"CREATE OR REPLACE TABLE {g('sf_dim_month')} AS SELECT DISTINCT month_key, year AS year_key, quarter, month FROM {g('dim_date')}",
            f"CREATE OR REPLACE TABLE {g('sf_dim_date')} AS SELECT date_key, date, month_key, weekday, is_weekend FROM {g('dim_date')}",
        ]
        sf_tables += [f"gold.{T(n)}" for n in ("sf_dim_date", "sf_dim_month", "sf_dim_year")]
    models["snowflake"] = {"sql": sf_sql, "tables": [f"gold.fact_{ds}"] + sf_tables}

    # ---------------------------------------------------------------- DATA VAULT 2.0
    rs = "s._src" if "_src" in df.columns else f"'{ds}'"
    bks = list(p["ids"][:1])
    if p["province"]:
        bks.append(p["province"])
    bks += [c for c in sorted(p["cats"], key=lambda c: -df[c].nunique())][: max(0, 3 - len(bks))]
    dv_sql, dv_tables, hk_cols = [], [], []
    norm = lambda e: f"upper(trim(CAST({e} AS VARCHAR)))"  # noqa: E731
    for c in bks:
        sc, ci = _slug(c), ident(c)
        dv_sql.append(f"""CREATE OR REPLACE TABLE {g('hub_' + sc)} AS
SELECT md5({norm('s.' + ci)}) AS hk_{sc}, any_value(s.{ci}) AS {ident(sc)}, current_timestamp AS load_dts, any_value({rs}) AS record_source
FROM {S} s WHERE s.{ci} IS NOT NULL GROUP BY md5({norm('s.' + ci)})""")
        dv_tables.append(f"gold.{T('hub_' + sc)}")
        hk_cols.append((sc, f"md5({norm('s.' + ci)})"))
    if hk_cols:
        concat = " || '||' || ".join(f"coalesce({e}, '')" for _, e in hk_cols)
        lnk_cols = ", ".join(f"{e} AS hk_{sc}" for sc, e in hk_cols)
        attrs = [c for c in df.columns if not c.startswith("_") and c not in bks and not c.endswith("__imputed")]
        hashdiff = " || '|' || ".join(f"coalesce(CAST(s.{ident(c)} AS VARCHAR), '')" for c in attrs) or "''"
        dv_sql.append(f"""CREATE OR REPLACE TABLE {g('lnk_' + ds)} AS
SELECT DISTINCT md5({concat}) AS hk_lnk_{ds}, {lnk_cols}, current_timestamp AS load_dts, {rs} AS record_source FROM {S} s""")
        dv_sql.append(f"""CREATE OR REPLACE TABLE {g('sat_' + ds)} AS
SELECT md5({concat}) AS hk_lnk_{ds}, current_timestamp AS load_dts, md5({hashdiff}) AS hashdiff, {rs} AS record_source,
       {', '.join(f's.{ident(c)} AS {ident(_slug(c))}' for c in attrs) or 'NULL AS empty'}
FROM {S} s""")
        dv_tables += [f"gold.lnk_{ds}", f"gold.sat_{ds}"]
    models["data_vault"] = {"sql": dv_sql, "tables": dv_tables, "business_keys": bks}

    # ---------------------------------------------------------------- execute + export
    for m in models.values():
        for q in m["sql"]:
            wh.con.execute(q)
        for t in m["tables"]:
            wh.lineage(ds, silver, t, "model")
            layer, name = t.split(".", 1)
            out = wh.lake / layer / f"{name}.parquet"
            out.parent.mkdir(parents=True, exist_ok=True)
            wh.con.execute(f"COPY {layer}.{ident(name)} TO '{out.as_posix()}' (FORMAT parquet)")
        m["erd"] = erd(wh, m["tables"], strip=f"{ds}__")
    if out_dir:
        d = Path(out_dir) / "models"
        d.mkdir(parents=True, exist_ok=True)
        for k, m in models.items():
            (d / f"{k}.sql").write_text(";\n\n".join(m["sql"]) + ";\n", encoding="utf-8")
            (d / f"{k}.mmd").write_text(m["erd"], encoding="utf-8")
    return {"plan": p, "models": models, "rationale": RATIONALE, "recommended": {"serving": "obt", "semantic": "star"}}


def erd(wh: Warehouse, tables: list[str], strip: str = "") -> str:
    """Mermaid erDiagram; relationships inferred from shared *_key / hk_* column names."""
    lines, cols_of = ["erDiagram"], {}
    for t in tables:
        cols = wh.columns(t)
        name = t.split(".", 1)[1].removeprefix(strip).upper()
        cols_of[name] = [c["name"] for c in cols]
        lines.append(f"  {name} {{")
        for c in cols[:18]:
            typ = c["type"].split("(")[0].replace(" ", "_")
            tag = " PK" if c is cols[0] and (c["name"].endswith("_key") or c["name"].startswith("hk_") or c["name"] == "fact_id") else ""
            lines.append(f"    {typ} {_slug(c['name']) or 'col'}{tag}")
        if len(cols) > 18:
            lines.append(f"    string more_{len(cols) - 18}_columns")
        lines.append("  }")
    names = list(cols_of)
    for a in names:
        pk = cols_of[a][0] if cols_of[a] else None
        if not pk or not (pk.endswith("_key") or pk.startswith("hk_")):
            continue
        for b in names:
            if b != a and pk in cols_of[b][1:]:
                lines.append(f'  {a} ||--o{{ {b} : "{pk}"')
    return "\n".join(lines)
