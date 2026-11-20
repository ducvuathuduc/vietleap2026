"""Ray-casting point-in-polygon (even-odd rule), no shapely dependency.

Coordinates are (lon, lat) pairs as in GeoJSON. A polygon is a list of rings
(exterior first, holes after); a multipolygon is a list of polygons.
"""
from __future__ import annotations


def point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_polygon(lon: float, lat: float, rings: list) -> bool:
    """One polygon: rings[0] exterior, the rest holes."""
    if not point_in_ring(lon, lat, rings[0]):
        return False
    return not any(point_in_ring(lon, lat, hole) for hole in rings[1:])


def point_in_multipolygon(lon: float, lat: float, polygons: list) -> bool:
    return any(point_in_polygon(lon, lat, rings) for rings in polygons)


def bbox_of_multipolygon(polygons: list) -> tuple[float, float, float, float]:
    lons = [pt[0] for rings in polygons for ring in rings for pt in ring]
    lats = [pt[1] for rings in polygons for ring in rings for pt in ring]
    return min(lons), min(lats), max(lons), max(lats)
