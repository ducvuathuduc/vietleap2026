"""Build a shareable, checksummed export from the latest stored analysis."""
from __future__ import annotations

import argparse
import html
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .de.exports import DICTIONARY_CSV, DICTIONARY_MD, EDA_MD
from .de.snapshots import file_sha256
from .de.sources import now_iso
from .i18n import langs_for
from .report import DECK_FILES, PITCH_FILES, rebuild_reports

CHROMIUM_WARNING = "Thiếu Chromium — chạy make setup"
FIXED_FILES = ("dashboard.html", "dashboard.pdf", "executive_summary.pdf", "executive_summary.md",
               "provenance.json", DICTIONARY_CSV, DICTIONARY_MD, EDA_MD)
SUPPORT_FILES = (DICTIONARY_CSV, DICTIONARY_MD, EDA_MD)


def dashboard_pdf(web_url: str, dataset: str, out: Path) -> tuple[Path | None, str | None]:
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        return None, CHROMIUM_WARNING

    path = out / "dashboard.pdf"
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(timeout=15000)
        except Error:
            return None, CHROMIUM_WARNING
        try:
            page = browser.new_page(color_scheme="light", viewport={"width": 1400, "height": 1000})
            page.set_default_timeout(15000)
            origin = urlsplit(web_url)

            def route_request(route):
                requested = urlsplit(route.request.url)
                if requested.scheme in ("data", "file") or (requested.scheme, requested.netloc) == (origin.scheme, origin.netloc):
                    route.continue_()
                else:
                    route.abort()

            page.route("**/*", route_request)
            warning = None
            try:
                if origin.scheme not in ("http", "https") or not origin.netloc:
                    raise ValueError("invalid WEB_URL")
                url = f"{web_url.rstrip('/')}/print?{urlencode({'dataset': dataset})}"
                response = page.goto(url, wait_until="domcontentloaded", timeout=7000)
                if response is None or not response.ok:
                    raise ValueError("print route unavailable")
                page.wait_for_selector(f"[data-print-ready='{dataset}']")
            except (Error, ValueError):
                page.goto((out / "dashboard.html").resolve().as_uri(), wait_until="load", timeout=15000)
                warning = "Đã in dashboard HTML tĩnh do trang in trực tiếp không khả dụng."
            label = html.escape(f"{dataset} · {now_iso()}")
            page.pdf(path=str(path), format="A4", landscape=True, print_background=True, display_header_footer=True,
                     header_template=f'<div style="font-size:9px;padding:0 12mm">{label}</div>', footer_template="<span></span>",
                     margin={"top": "14mm", "bottom": "10mm", "left": "10mm", "right": "10mm"})
            return path, warning
        except Error:
            return None, "Không in được dashboard PDF. Dashboard HTML có trong gói."
        finally:
            browser.close()


def _run_id(out: Path) -> str:
    path = out / "pipeline.json"
    return str(json.loads(path.read_text(encoding="utf-8")).get("run_id") or "—") if path.is_file() else "—"


def bundle(source: Path, destination: Path, dataset: str, lang: str, warnings: list[str]) -> None:
    languages = langs_for(lang)
    filenames = [name for language in languages for name in (DECK_FILES[language], PITCH_FILES[language])]
    filenames += list(FIXED_FILES)
    paths = [source / name for name in filenames if (source / name).is_file() and (source / name).resolve().is_relative_to(source.resolve())]
    lines = [f"VietLeap · {dataset}", f"Run ID: {_run_id(source)}", f"Xuất lúc: {now_iso()}", "", "Tệp và SHA-256:"]
    lines.extend(f"{file_sha256(path)}  {path.name}" for path in paths)
    provenance = source / "provenance.json"
    if provenance in paths:
        lines += ["", "Nguồn và giấy phép:"]
        for row in json.loads(provenance.read_text(encoding="utf-8")):
            lines.append(f"- {row.get('source', '—')} · {row.get('license_note') or '—'}")
    lines += ["", *(f"- {warning}" for warning in warnings)]
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.name)
        archive.writestr("README.txt", "\n".join(lines) + "\n")


def build_export(out: Path, lang: str = "both", dashboard: bool = True, web_url: str = "http://127.0.0.1:3000") -> dict:
    saved = out / "results.json"
    revision = saved.stat().st_mtime_ns
    destination = out / "export"
    destination.mkdir(exist_ok=True)
    warnings = []
    outputs = {"bundle": "export/bundle.zip"}
    with tempfile.TemporaryDirectory(prefix=".build-", dir=destination) as directory:
        stage = Path(directory)
        files = rebuild_reports(out, lang, destination=stage)
        if not (out / "clean.parquet").is_file():
            warnings.append("Dashboard được dựng từ tệp mẫu clean_sample.csv.")
        if not files.get("summary_pdf"):
            warnings.append(CHROMIUM_WARNING)
        for name in SUPPORT_FILES:
            if (out / name).is_file():
                shutil.copyfile(out / name, stage / name)
        pdf = None
        if dashboard:
            pdf, warning = dashboard_pdf(web_url, out.name, stage)
            if warning and warning not in warnings:
                warnings.append(warning)
        if saved.stat().st_mtime_ns != revision:
            warnings.append("Dataset thay đổi trong lúc xuất. Tạo lại báo cáo để đồng bộ phiên bản.")
        bundle(stage, stage / "bundle.zip", out.name, lang, warnings)
        if (stage / "bundle.zip").stat().st_size > 50_000_000:
            warnings.append("Gói ZIP lớn hơn 50 MB.")
            bundle(stage, stage / "bundle.zip", out.name, lang, warnings)
        if pdf:
            pdf.replace(destination / "dashboard.pdf")
            outputs["dashboard_pdf"] = "export/dashboard.pdf"
        else:
            (destination / "dashboard.pdf").unlink(missing_ok=True)
        (stage / "bundle.zip").replace(destination / "bundle.zip")
    return {"files": outputs, "warnings": warnings}


def partial_export(out: Path, lang: str) -> dict:
    destination = out / "export"
    destination.mkdir(exist_ok=True)
    warnings = ["Hết thời gian xuất. Gói chứa các báo cáo đã có của dataset."]
    with tempfile.TemporaryDirectory(prefix=".partial-", dir=destination) as directory:
        path = Path(directory) / "bundle.zip"
        bundle(out, path, out.name, lang, warnings)
        path.replace(destination / "bundle.zip")
    (destination / "dashboard.pdf").unlink(missing_ok=True)
    return {"files": {"bundle": "export/bundle.zip"}, "warnings": warnings}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("lang", choices=("en", "vi", "both"))
    parser.add_argument("dashboard", choices=("yes", "no"))
    parser.add_argument("web_url")
    args = parser.parse_args()
    print(json.dumps(build_export(args.out, args.lang, args.dashboard == "yes", args.web_url), ensure_ascii=True))


if __name__ == "__main__":
    main()
