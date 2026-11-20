"""Gold builder: OSM bank points -> data/lake/ratewatch/gold/geo_provinces.json (CONTRACT D)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from vlkit.ratewatch.ingest.banks import load_banks

from .banks_match import alias_map, match_bank
from .overpass import fetched_at_of
from .provinces import assign_province, load_provinces

BOUNDARY_REF = "web/public/geo/vn-34.geo.json"
ATTRIBUTION = ("Ranh giới: GSO/OCHA COD-AB v02 (CC BY-IGO) · Bao gồm Hoàng Sa (Đà Nẵng) & Trường Sa (Khánh Hòa)."
               " · Điểm chi nhánh: © OpenStreetMap contributors (ODbL)")


def load_population(path: str | Path) -> dict[str, dict]:
    """pcode -> {population, period} from the packaged population_2024.csv."""
    population: dict[str, dict] = {}
    with Path(path).open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            population[row["pcode"]] = {"population": int(row["population"]), "period": row["period"]}
    return population


def element_coords(element: dict) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return element["lon"], element["lat"]
    center = element.get("center") or {}
    if "lat" in center and "lon" in center:
        return center["lon"], center["lat"]
    return None


def build_geo(*, geojson_path, banks_path, population_path, osm_json,
              boundary_ref: str = BOUNDARY_REF, attribution: str = ATTRIBUTION) -> tuple[dict, dict]:
    provinces = load_provinces(geojson_path)
    aliases = alias_map(load_banks(banks_path))
    population = load_population(population_path)
    data = json.loads(Path(osm_json).read_text(encoding="utf-8"))

    fetched_at = fetched_at_of(osm_json)
    branch_source = "OSM Overpass amenity=bank (© OpenStreetMap contributors, ODbL)"
    if fetched_at:
        branch_source += f", fetched {fetched_at}"

    counts = {p["pcode"]: {"total": 0, "by_bank": {}} for p in provinces}
    summary = {"elements_total": 0, "elements_placed": 0, "elements_in_province": 0,
               "elements_matched": 0, "unmatched_in_province": 0, "unmatched_share": 0.0,
               "banks_matched": 0, "provinces_covered": 0, "branch_source": branch_source,
               "osm_json": str(osm_json)}
    codes_seen: set[str] = set()

    for element in data.get("elements", []):
        summary["elements_total"] += 1
        coords = element_coords(element)
        if coords is None:
            continue
        summary["elements_placed"] += 1
        pcode = assign_province(coords[0], coords[1], provinces)
        if pcode is None:
            continue
        summary["elements_in_province"] += 1
        counts[pcode]["total"] += 1
        code = match_bank(element.get("tags"), aliases)
        if code:
            codes_seen.add(code)
            summary["elements_matched"] += 1
            by_bank = counts[pcode]["by_bank"]
            by_bank[code] = by_bank.get(code, 0) + 1
        else:
            summary["unmatched_in_province"] += 1

    rows = []
    for province in provinces:
        pcode = province["pcode"]
        pop = population.get(pcode, {})
        row_counts = counts[pcode]
        rows.append({
            "pcode": pcode,
            "name_vi": province["name_vi"],
            "name_en": province["name_en"],
            "branches_total": row_counts["total"],
            "branches_by_bank": dict(sorted(row_counts["by_bank"].items())),
            "branch_source": branch_source,
            "population": pop.get("population"),
            "population_period": pop.get("period"),
            "deposits_bn": None,
            "credit_bn": None,
            "deposit_period": None,
            "deposit_source": None,
            "best_counter_12m": None,
        })

    summary["banks_matched"] = len(codes_seen)
    summary["provinces_covered"] = sum(1 for row in rows if row["branches_total"] > 0)
    if summary["elements_in_province"]:
        summary["unmatched_share"] = round(summary["unmatched_in_province"] / summary["elements_in_province"], 4)

    gold = {"provinces": rows, "boundary": boundary_ref, "attribution": attribution}
    return gold, summary


def write_gold(path: str | Path, gold: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gold, ensure_ascii=False, indent=1), encoding="utf-8")
    return path
