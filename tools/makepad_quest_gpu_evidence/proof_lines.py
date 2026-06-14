"""Proof-line parsing helpers for Makepad Quest GPU evidence checks."""

from __future__ import annotations

import re
from typing import Any


def numeric(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def line_has_marker(line: str, marker: str) -> bool:
    pattern = re.compile(rf"(^|:\s+){re.escape(marker)}\b")
    return bool(pattern.search(line))


def lines_containing(lines: list[Any], token: str) -> list[str]:
    return [str(line) for line in lines if line_has_marker(str(line), token)]


def count_lines_containing(lines: list[str], token: str) -> int:
    return sum(1 for line in lines if token in line)


def marker_int_fields(lines: list[str], field_name: str) -> list[int]:
    pattern = re.compile(rf"\b{re.escape(field_name)}=(\d+)\b")
    values: list[int] = []
    for line in lines:
        values.extend(int(match.group(1)) for match in pattern.finditer(line))
    return values
