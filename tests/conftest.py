"""Shared fixtures. Puts engine/ and the kit root on sys.path so `from vlkit import ...` works without tools/env.sh."""
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "engine"))
sys.path.insert(0, str(KIT))  # `import api` for FastAPI TestClient tests


@pytest.fixture(scope="session")
def kit_root() -> Path:
    return KIT
