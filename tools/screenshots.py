"""Capture the local dashboard with a selected practice dataset."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROUTES = dict(zip(
    ("/", "/brief", "/sources", "/pipeline", "/quality", "/model", "/sql", "/profile", "/insights", "/drivers",
     "/segments", "/decision", "/analyst", "/report"),
    (f"{index:02d}-{name}.png" for index, name in enumerate(("tong-quan", "de-bai", "nguon", "pipeline", "chat-luong",
      "mo-hinh", "sql", "ho-so", "insights", "drivers", "phan-khuc", "quyet-dinh", "analyst", "xuat-bao-cao"), 1)),
))
DATASET = re.compile(r"[a-z0-9_-]{1,80}")


def open_route(page, base: str, route: str, dataset: str) -> None:
    response = page.goto(f"{base.rstrip('/')}{route}?dataset={dataset}", wait_until="networkidle")
    if response is None or not response.ok:
        raise RuntimeError(f"{route}: page did not load")
    page.locator("[data-slot=skeleton]").first.wait_for(state="hidden")
    page.get_by_role("combobox", name="Dataset", exact=True).get_by_text(dataset, exact=True).wait_for()
    if page.get_by_text("Không kết nối được API", exact=True).count() or page.get_by_text("Dataset này chưa có kết quả pipeline", exact=True).count():
        raise RuntimeError(f"{route}: missing dashboard data")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="wdi_asean")
    parser.add_argument("--base", default="http://127.0.0.1:3000")
    parser.add_argument("--out", type=Path, default=Path("out/screenshots"))
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps(ROUTES))
        return
    if not DATASET.fullmatch(args.dataset):
        parser.error("invalid dataset ID")

    from playwright.sync_api import sync_playwright

    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")
        context.add_init_script(f"localStorage.setItem('theme', '{'dark' if args.dark else 'light'}')")
        page = context.new_page()
        shots = {}
        routes = {route: ROUTES[route] for route in ("/", "/pipeline", "/insights")} if args.dark else ROUTES
        for route, name in routes.items():
            filename = f"dark-{name}" if args.dark else name
            open_route(page, args.base, route, args.dataset)
            page.screenshot(path=args.out / filename, animations="disabled")
            if (args.out / filename).stat().st_size >= 600_000:
                raise RuntimeError(f"{route}: {filename} exceeds 600 kB")
            shots[route] = filename
        browser.close()
    sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    date = datetime.now(ZoneInfo("Asia/Saigon")).date()
    index = ["# Ảnh dashboard", "", f"Dataset `{args.dataset}` · commit `{sha}` · {date}", ""]
    index += [f"- [{route}]({name})" for route, name in shots.items()]
    (args.out / ("DARK.md" if args.dark else "README.md")).write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
