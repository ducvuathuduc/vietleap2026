"""CONTRACT D geography (M1): OSM bank points joined to the 34 provinces -> gold JSON.

CLI: ``python -m vlkit.ratewatch.geo [--fetch] [--root DIR] [--osm-json PATH]``
"""
from .banks_match import alias_map, match_bank, normalise_name
from .build import ATTRIBUTION, BOUNDARY_REF, build_geo, load_population, write_gold
from .overpass import collect_overpass, latest_overpass
from .pip import point_in_multipolygon, point_in_ring
from .provinces import assign_province, load_provinces

__all__ = [
    "ATTRIBUTION", "BOUNDARY_REF",
    "alias_map", "assign_province", "build_geo", "collect_overpass", "latest_overpass",
    "load_population", "load_provinces", "match_bank", "normalise_name",
    "point_in_multipolygon", "point_in_ring", "write_gold",
]
