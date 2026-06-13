"""Shared process helpers for Hostess control routes."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def run(
    command: list[str], *, allow_failure: bool = False, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, cwd=cwd)
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result


def run_captured(
    command: list[str], *, allow_failure: bool = False, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result
