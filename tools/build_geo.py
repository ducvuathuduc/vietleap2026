#!/usr/bin/env python3
"""Build verified 34-province Viet Nam boundary asset from HDX OCHA/GSO COD-AB v02 (CC BY-IGO).

Verifies sovereignty & merger gates (feature 008 T801–T802):
  1. Exactly 34 post-NQ 202/2025/QH15 provinces in vnm_admin1.geojson.
  2. Da Nang city includes Hoang Sa (Paracel) archipelago polygons (>111E, ~15-17N).
  3. Khanh Hoa includes Truong Sa (Spratly) archipelago polygons (>111E, ~6.9-12N).
  4. Simplified GeoJSON <= 500 KB for offline fast loading under web/public/geo/.

Usage:
  python tools/build_geo.py [--input path/to/vnm_admin_boundaries.geojson.zip]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVINCE_CSV = ROOT / "engine" / "vlkit" / "resources" / "province_63_to_34.csv"

HDX_GEOJSON_ZIP_URL = (
    "https://data.humdata.org/dataset/3cb544a9-9d04-4f54-94e2-93230efd8ceb/"
    "resource/048a6012-a8c2-4fa9-be87-cb6c01e9afbf/download/vnm_admin_boundaries.geojson.zip"
)
MAX_BYTES = 500 * 1024
OUT_GEO = ROOT / "web" / "public" / "geo" / "vn-34.geo.json"
OUT_LICENSE = ROOT / "web" / "public" / "geo" / "LICENSE.md"


def _fold(s: str) -> str:
    n = unicodedata.normalize("NFD", s).replace("đ", "d").replace("Đ", "D")
    n = "".join(ch for ch in n if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", n.lower()).strip()


def _load_province_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    with PROVINCE_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            old_p, new_p = row["old_province"].strip(), row["new_province"].strip()
            idx[_fold(old_p)] = new_p
            idx[_fold(new_p)] = new_p
    idx["hue"] = "Huế"
    idx["thua thien hue"] = "Huế"
    idx["ho chi minh city"] = "Hồ Chí Minh"
    idx["ha noi capital"] = "Hà Nội"
    return idx


PROVINCE_INDEX = _load_province_index()


def _rdp(pts: list[list[float]], eps: float) -> list[list[float]]:
    if len(pts) <= 4:
        return pts
    closed = pts[0] == pts[-1]
    work = pts[:-1] if closed else pts
    if len(work) <= 3:
        return pts

    def perp_dist(p: list[float], a: list[float], b: list[float]) -> float:
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == 0 and dy == 0:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))

    def rec(arr: list[list[float]]) -> list[list[float]]:
        if len(arr) <= 2:
            return arr
        dmax, idx = 0.0, 0
        for i in range(1, len(arr) - 1):
            d = perp_dist(arr[i], arr[0], arr[-1])
            if d > dmax:
                dmax, idx = d, i
        if dmax > eps:
            return rec(arr[: idx + 1])[:-1] + rec(arr[idx:])
        return [arr[0], arr[-1]]

    mid = len(work) // 2
    res = rec(work[: mid + 1])[:-1] + rec(work[mid:] + [work[0]])
    if len(res) < 4:
        return pts[:4] if len(pts) >= 4 else pts
    return res


def _canonical_name(props: dict) -> str:
    for cand in (props.get("adm1_name1"), props.get("adm1_name")):
        if not cand:
            continue
        k = _fold(str(cand))
        k = re.sub(r"^(?:tinh|thanh pho|tp|city of|province of|thu do)\s+", "", k)
        k = re.sub(r"\s+(?:province|city|capital)$", "", k).strip()
        if k in PROVINCE_INDEX:
            return PROVINCE_INDEX[k]
    raise ValueError(f"Unmapped HDX province feature: {props!r}")


def build(zip_path: Path, out_geo: Path = OUT_GEO, out_license: Path = OUT_LICENSE) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        raw = json.loads(zf.read("vnm_admin1.geojson"))

    features = raw.get("features") or []
    if len(features) != 34:
        raise ValueError(f"Expected 34 Admin1 features in vnm_admin1.geojson, got {len(features)}")

    out_features = []
    seen_provinces = set()
    hoang_sa_count = 0
    truong_sa_count = 0

    for feat in features:
        props = feat["properties"]
        province = _canonical_name(props)
        seen_provinces.add(province)
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        new_polys = []

        for poly in polys:
            outer = poly[0]
            xs = [pt[0] for pt in outer]
            ys = [pt[1] for pt in outer]
            area_approx = (max(xs) - min(xs)) * (max(ys) - min(ys))
            is_offshore = max(xs) > 110.0
            if not is_offshore and area_approx < 0.0002 and len(polys) > 3:
                continue
            eps = 0.002 if is_offshore else 0.008
            ring = [[round(pt[0], 3), round(pt[1], 3)] for pt in _rdp(outer, eps)]
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            if len(ring) >= 4:
                new_polys.append([ring])
                if province == "Đà Nẵng" and max(pt[0] for pt in ring) >= 111.0 and min(pt[1] for pt in ring) >= 15.0:
                    hoang_sa_count += 1
                if province == "Khánh Hòa" and max(pt[0] for pt in ring) >= 111.0 and max(pt[1] for pt in ring) <= 12.5:
                    truong_sa_count += 1

        if not new_polys:
            outer = max(polys, key=lambda pl: len(pl[0]))[0]
            ring = [[round(pt[0], 3), round(pt[1], 3)] for pt in _rdp(outer, 0.008)]
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            new_polys = [[ring]]

        out_features.append({
            "type": "Feature",
            "properties": {
                "pcode": props["adm1_pcode"],
                "name": province,
                "name_en": props["adm1_name"],
            },
            "geometry": {"type": "MultiPolygon", "coordinates": new_polys},
        })

    if len(seen_provinces) != 34:
        raise ValueError(f"Expected 34 unique canonical provinces, got {len(seen_provinces)}")
    if hoang_sa_count == 0 or truong_sa_count == 0:
        raise ValueError(
            f"Sovereignty check failed: Hoang Sa polygons={hoang_sa_count}, Truong Sa polygons={truong_sa_count}"
        )

    payload = json.dumps({"type": "FeatureCollection", "features": out_features}, separators=(",", ":"), ensure_ascii=False)
    size_bytes = len(payload.encode("utf-8"))
    if size_bytes > MAX_BYTES:
        raise ValueError(f"Simplified GeoJSON exceeds {MAX_BYTES} bytes: {size_bytes}")

    out_geo.parent.mkdir(parents=True, exist_ok=True)
    out_geo.write_text(payload, encoding="utf-8")
    out_license.write_text(
        "# Viet Nam 34-Province Boundary Asset (vn-34.geo.json)\n\n"
        "- **Source**: HDX \"Viet Nam – Subnational Administrative Boundaries\" (COD-AB v02), General Statistics Office of Viet Nam (GSO) / OCHA\n"
        "- **Dataset URL**: https://data.humdata.org/dataset/cod-ab-vnm\n"
        "- **Boundary date**: 2025-07-01 (reviewed 2025-09-25, 34 post-NQ 202/2025/QH15 units)\n"
        "- **Licence**: Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO)\n"
        "- **Attribution**: `Ranh giới: GSO/OCHA COD-AB v02 (CC BY-IGO) · Bao gồm Hoàng Sa (Đà Nẵng) & Trường Sa (Khánh Hòa).`\n"
        f"- **Verified islands**: {hoang_sa_count} Hoàng Sa polygons (Đà Nẵng), {truong_sa_count} Trường Sa polygons (Khánh Hòa); size {size_bytes:,} bytes.\n",
        encoding="utf-8",
    )
    return {"features": len(out_features), "bytes": size_bytes, "hoang_sa": hoang_sa_count, "truong_sa": truong_sa_count}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, help="Local path to vnm_admin_boundaries.geojson.zip")
    args = ap.parse_args(argv)
    zip_path = args.input or (ROOT / "data" / "raw" / "vnm_admin_boundaries.geojson.zip")
    if not zip_path.exists():
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading HDX COD-AB v02 to {zip_path}...")
        urllib.request.urlretrieve(HDX_GEOJSON_ZIP_URL, zip_path)
    stats = build(zip_path)
    print(f"Wrote {OUT_GEO} ({stats['bytes']:,} bytes, {stats['features']} provinces, "
          f"Hoang Sa={stats['hoang_sa']}, Truong Sa={stats['truong_sa']})")


if __name__ == "__main__":
    main()
