"""Strict type checking for every job. Each job's script is called build.py,
so mypy can't take them all in one run (it would see one module named
`build` defined several times); this checks them one at a time."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
JOBS = sorted(ROOT.glob("jobs/*/build.py"))


@pytest.mark.parametrize("build", JOBS, ids=[p.parent.name for p in JOBS])
def test_job_type_checks(build: Path) -> None:
    res = subprocess.run([sys.executable, "-m", "mypy", str(build)], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
