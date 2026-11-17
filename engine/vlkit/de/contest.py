"""Contest workflow for named packs and trusted local YAML recipes."""
from __future__ import annotations

from pathlib import Path

from ..brief import parse_brief
from ..i18n import DEFAULT_REPORT_LANG
from .exports import DICTIONARY_CSV, DICTIONARY_MD, EDA_MD
from .flow import run_flow
from .snapshots import has_snapshot
from .sources import Recipe, load_recipe
from .warehouse import KIT, Warehouse

PACK_DIRS = {"public_finance_province": "public_finance", "listed_firms_market": "listed_firms",
             "development_indicators": "wdi_asean", "energy_ev_data_economy": "energy", "energy_ev": "energy"}


def pack_recipe(pack: str, *, offline: bool = False) -> Recipe:
    path = Path(pack)
    if path.is_file():
        return load_recipe(path)
    if not pack.isascii() or not pack.replace("_", "").isalnum():
        raise FileNotFoundError(f"Không tìm thấy recipe {pack!r}")
    directory = KIT / "scenarios" / PACK_DIRS.get(pack, pack)
    online = load_recipe(directory / "sources.yaml")
    practice = directory / "sources.practice.yaml"
    if practice.is_file() and not Path(online.sources[0].uri).is_file():
        return load_recipe(practice)
    fallback = directory / "sources.offline.yaml"
    if offline and fallback.is_file() and not all(has_snapshot(source) for source in online.sources):
        return load_recipe(fallback)
    return online


def run_contest(pack: str, brief: Path, *, out_root: Path | None = None, wh: Warehouse | None = None,
                lang: str = DEFAULT_REPORT_LANG, target: str | None = None) -> list[Path]:
    text = brief.read_text(encoding="utf-8-sig")
    parse_brief(text)
    recipe = pack_recipe(pack, offline=True)
    root = Path(out_root or KIT / "out")
    serve_kwargs = {"lang": lang}
    if target:
        serve_kwargs["target"] = target
    summary = run_flow(recipe.dataset, recipe.sources, out_root=root, wh=wh, primary=recipe.primary, serve=True,
                       serve_kwargs=serve_kwargs, keys=recipe.keys, post_sql=recipe.post_sql,
                       analysis_table=recipe.analysis_table, brief_text=text, offline=True)
    out = root / summary["dataset"]
    paths = [out / name for name in ("brief.json", "pipeline.json", "lineage.json", "provenance.json", "quality.json",
                                     "models/star.sql", "results.json", DICTIONARY_CSV, DICTIONARY_MD, EDA_MD)]
    paths += [out / name for name in summary["report_files"].values() if isinstance(name, str) and name != EDA_MD]
    return paths
