"""Shared fixtures. Puts engine/ and the kit root on sys.path so `from vlkit import ...` works without tools/env.sh."""
import os
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "engine"))
sys.path.insert(0, str(KIT))  # `import api` for FastAPI TestClient tests
os.environ.setdefault("RATE_LIMIT_PER_MIN", "0")  # the suite hammers POST routes; rate limiting is tested on its own app


@pytest.fixture(scope="session")
def kit_root() -> Path:
    return KIT


# CI fix (16/11): every test passes, but on GitHub runners the interpreter sometimes aborts on exit with
# "terminate called without an active exception" (exit 134) while native threads (DuckDB 2.x /
# kaleido-choreographer) are torn down. After pytest has printed its summary we hard-exit with
# pytest's real status so a teardown crash can't turn a green run red. Opt out: VLKIT_NO_HARD_EXIT=1.
_EXIT_STATUS = {"code": None}


def pytest_sessionfinish(session, exitstatus):
    _EXIT_STATUS["code"] = int(exitstatus)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    if _EXIT_STATUS["code"] is None or os.environ.get("VLKIT_NO_HARD_EXIT"):
        return
    if not (os.environ.get("CI") or os.environ.get("VLKIT_HARD_EXIT")):
        return
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_EXIT_STATUS["code"])
