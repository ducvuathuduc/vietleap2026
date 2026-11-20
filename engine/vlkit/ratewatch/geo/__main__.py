"""CLI: build gold/geo_provinces.json from the cached Overpass response (fetch only with --fetch)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .build import build_geo, write_gold
from .overpass import collect_overpass, latest_overpass

KIT = Path(__file__).resolve().parents[4]
DEFAULT_ROOT = KIT / "data" / "lake" / "ratewatch"
DEFAULT_GEOJSON = KIT / "web" / "public" / "geo" / "vn-34.geo.json"
DEFAULT_BANKS = KIT / "scenarios" / "ratewatch" / "banks.yaml"
DEFAULT_POPULATION = Path(__file__).resolve().parent / "population_2024.csv"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="ratewatch lake root")
    parser.add_argument("--geojson", default=str(DEFAULT_GEOJSON))
    parser.add_argument("--banks", default=str(DEFAULT_BANKS))
    parser.add_argument("--population", default=str(DEFAULT_POPULATION))
    parser.add_argument("--osm-json", default=None, help="cached Overpass response (default: newest under <root>/bronze/osm)")
    parser.add_argument("--fetch", action="store_true", help="call Overpass once when no cache exists")
    args = parser.parse_args(argv)

    osm_json = Path(args.osm_json) if args.osm_json else latest_overpass(args.root)
    if osm_json is None:
        if not args.fetch:
            print("no cached Overpass response under", Path(args.root) / "bronze" / "osm",
                  "- re-run with --fetch", file=sys.stderr)
            return 2
        osm_json = collect_overpass(args.root)

    gold, summary = build_geo(
        geojson_path=args.geojson,
        banks_path=args.banks,
        population_path=args.population,
        osm_json=osm_json,
    )
    out = write_gold(Path(args.root) / "gold" / "geo_provinces.json", gold)
    print(json.dumps({"written": str(out), **summary}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
