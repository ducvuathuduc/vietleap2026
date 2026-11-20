"""The 34-province boundary (web/public/geo/vn-34.geo.json, HDX COD-AB adm1_pcode)."""
from __future__ import annotations

import json
from pathlib import Path

from .pip import bbox_of_multipolygon, point_in_multipolygon


def load_provinces(path: str | Path) -> list[dict]:
    geo = json.loads(Path(path).read_text(encoding="utf-8"))
    provinces = []
    for feature in geo["features"]:
        props = feature["properties"]
        geometry = feature["geometry"]
        if geometry["type"] == "Polygon":
            polygons = [geometry["coordinates"]]
        elif geometry["type"] == "MultiPolygon":
            polygons = geometry["coordinates"]
        else:
            continue
        provinces.append({
            "pcode": props["pcode"],
            "name_vi": props.get("name", ""),
            "name_en": props.get("name_en", ""),
            "polygons": polygons,
            "bbox": bbox_of_multipolygon(polygons),
        })
    return provinces


def assign_province(lon: float, lat: float, provinces: list[dict]) -> str | None:
    """pcode of the province containing the point, or None (bbox prefilter, then ray casting)."""
    for province in provinces:
        min_lon, min_lat, max_lon, max_lat = province["bbox"]
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            if point_in_multipolygon(lon, lat, province["polygons"]):
                return province["pcode"]
    return None
