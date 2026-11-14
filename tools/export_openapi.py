#!/usr/bin/env python3
"""Regenerate specs/001-vietleap-insight-kit/contracts/openapi.json from the FastAPI app (run after changing routes)."""
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(KIT / "engine"), str(KIT)]
from api.main import app  # noqa: E402

OUT = KIT / "specs" / "001-vietleap-insight-kit" / "contracts" / "openapi.json"

if __name__ == "__main__":
    OUT.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(KIT)} ({len(app.openapi()['paths'])} paths)")
