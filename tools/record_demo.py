"""Record the local dashboard without narration using the contest storyboard."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

from screenshots import DATASET, open_route

STORYBOARD = Path(__file__).resolve().parents[1] / "docs/DEMO_SCRIPT.md"


def perform(page, action: str) -> None:
    if action == "story":
        page.locator('[data-tour="story-button"]').click()
        page.locator(".driver-popover").wait_for()
        for _ in range(3):
            time.sleep(4)
            page.locator(".driver-popover-next-btn").click()
    elif action == "inspect":
        page.locator('[data-tour="inspect-toggle"]').click()
        page.locator('[data-insight-target^="kpi:"]').first.click()
        page.get_by_role("dialog").wait_for()
    elif action == "export":
        page.get_by_role("button", name="Xuất báo cáo", exact=True).click()
        page.get_by_role("dialog").wait_for()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="wdi_asean")
    parser.add_argument("--base", default="http://127.0.0.1:3000")
    parser.add_argument("--out", type=Path, default=Path("out/demo/demo.webm"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    plan = yaml.safe_load(STORYBOARD.read_text(encoding="utf-8").split("---", 2)[1])
    if args.dry_run:
        print(json.dumps(plan))
        return
    if not DATASET.fullmatch(args.dataset):
        parser.error("invalid dataset ID")

    from playwright.sync_api import sync_playwright

    args.out.parent.mkdir(parents=True, exist_ok=True)
    size = {"width": 1280, "height": 720}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=size, record_video_size=size, record_video_dir=args.out.parent,
                                      locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")
        page = context.new_page()
        video = page.video
        start = time.monotonic()
        for step in plan["steps"]:
            time.sleep(max(0, start + step["at"] - time.monotonic()))
            open_route(page, args.base, step["route"], args.dataset)
            perform(page, step["action"])
        time.sleep(max(0, start + plan["duration"] - time.monotonic()))
        context.close()
        if video is None:
            raise RuntimeError("Playwright did not create a recording")
        video.path().replace(args.out)
        browser.close()
    print(args.out.resolve())


if __name__ == "__main__":
    main()
