"""Validate live-vs-recorded hand provider A/B evidence.

This checker compares one recorded-hand GPU evidence summary with one live
Meta Quest OpenXR hand evidence summary. It proves only that both providers
enter Hostess through the same bind-mesh plus compact joint-frame worker
boundary. It does not promote runtime GPU force authority.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from check_makepad_quest_gpu_evidence import (
        PROOF_SUMMARY_SCHEMA,
        load_summary,
        resolve_summary_path,
    )
except ImportError:  # pragma: no cover - direct script fallback
    from pathlib import Path as _Path

    PROOF_SUMMARY_SCHEMA = "rusty.hostess.quest_live_hand_small_profile_summary.v1"

    def load_summary(path: _Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"{path} did not contain a JSON object")
        return value

    def resolve_summary_path(input_path: _Path) -> _Path:
        if input_path.is_file():
            return input_path
        preferred = input_path / "live-hand-small-profile-summary.json"
        if preferred.is_file():
            return preferred
        raise FileNotFoundError(f"summary not found under {input_path}")


AB_SCHEMA = "rusty.hostess.makepad.live_recorded_provider_ab_check.v1"
PROVIDER_SHAPE = "bind-mesh-plus-compact-joint-frame"
FIELD_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*?)=([^ \t\r\n]+)")


@dataclass(frozen=True)
class ProviderSide:
    summary_path: str
    source_id: str
    vertex_count: int
    triangle_count: int
    worker_ready_count: int
    source_ready_count: int


@dataclass(frozen=True)
class ProviderAbResult:
    ok: bool
    issues: list[str]
    report: dict[str, Any]


def parse_fields(line: str) -> dict[str, str]:
    return {match.group(1): match.group(2) for match in FIELD_RE.finditer(line)}


def object_value(value: Any, key: str) -> dict[str, Any]:
    nested = value.get(key) if isinstance(value, dict) else None
    return nested if isinstance(nested, dict) else {}


def sample_lines(summary: dict[str, Any], key: str) -> list[str]:
    value = object_value(summary, key).get("sample_lines", [])
    if not isinstance(value, list):
        return []
    return [str(line) for line in value]


def int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def first_line_with_tokens(lines: list[str], tokens: tuple[str, ...]) -> str:
    for line in lines:
        if all(token in line for token in tokens):
            return line
    return ""


def side_summary(line: str, summary_path: Path, source_ready_count: int) -> ProviderSide:
    fields = parse_fields(line)
    return ProviderSide(
        summary_path=str(summary_path),
        source_id=fields.get("sourceId", "none"),
        vertex_count=int_value(fields.get("vertexCount")),
        triangle_count=int_value(fields.get("triangleCount")),
        worker_ready_count=1 if line else 0,
        source_ready_count=source_ready_count,
    )


def validate_provider_ab(
    recorded_summary: dict[str, Any],
    live_summary: dict[str, Any],
    recorded_summary_path: Path,
    live_summary_path: Path,
) -> ProviderAbResult:
    issues: list[str] = []
    if recorded_summary.get("schema") != PROOF_SUMMARY_SCHEMA:
        issues.append("recorded summary schema did not match Hostess GPU proof summary")
    if live_summary.get("schema") != PROOF_SUMMARY_SCHEMA:
        issues.append("live summary schema did not match Hostess GPU proof summary")

    recorded_lines = sample_lines(recorded_summary, "recorded_hand_source")
    recorded_worker = first_line_with_tokens(
        recorded_lines,
        (
            "status=ready",
            f"providerShape={PROVIDER_SHAPE}",
            "recordedHandProvider=true",
            "compactFrameWorkerSubmit=true",
            "sourceFrameExpansionThread=matter-worker",
            "recordedInputEquivalent=true",
            "gpuAdapterBoundaryUnchanged=true",
            "highRateJsonPayload=false",
        ),
    )
    if not recorded_worker:
        issues.append("recorded evidence did not prove the recorded worker provider shape")

    live_source_lines = sample_lines(live_summary, "live_hand_source")
    live_source = first_line_with_tokens(
        live_source_lines,
        (
            "status=ready",
            f"providerShape={PROVIDER_SHAPE}",
            "liveOpenXrHandProvider=true",
            "recordedInputEquivalent=true",
            "gpuAdapterBoundaryUnchanged=true",
            "highRateJsonPayload=false",
        ),
    )
    if not live_source:
        issues.append("live evidence did not prove the live provider source shape")

    live_worker_lines = sample_lines(live_summary, "live_hand_worker_source")
    live_worker = first_line_with_tokens(
        live_worker_lines,
        (
            "status=ready",
            f"providerShape={PROVIDER_SHAPE}",
            "liveOpenXrHandProvider=true",
            "compactFrameWorkerSubmit=true",
            "sourceFrameExpansionThread=matter-worker",
            "recordedInputEquivalent=true",
            "gpuAdapterBoundaryUnchanged=true",
            "highRateJsonPayload=false",
        ),
    )
    if not live_worker:
        issues.append("live evidence did not prove the live worker provider shape")

    recorded_side = side_summary(recorded_worker, recorded_summary_path, 0)
    live_source_ready_count = int_value(
        object_value(live_summary, "live_hand_source").get("ready_line_count")
    )
    live_side = side_summary(live_worker, live_summary_path, live_source_ready_count)

    if recorded_side.vertex_count <= 0:
        issues.append("recorded worker did not report a positive vertexCount")
    if recorded_side.triangle_count <= 0:
        issues.append("recorded worker did not report a positive triangleCount")
    if live_side.vertex_count <= 0:
        issues.append("live worker did not report a positive vertexCount")
    if live_side.triangle_count <= 0:
        issues.append("live worker did not report a positive triangleCount")
    if (
        recorded_side.vertex_count > 0
        and live_side.vertex_count > 0
        and recorded_side.vertex_count != live_side.vertex_count
    ):
        issues.append(
            "recorded/live worker vertexCount mismatch: "
            f"{recorded_side.vertex_count} != {live_side.vertex_count}"
        )
    if (
        recorded_side.triangle_count > 0
        and live_side.triangle_count > 0
        and recorded_side.triangle_count != live_side.triangle_count
    ):
        issues.append(
            "recorded/live worker triangleCount mismatch: "
            f"{recorded_side.triangle_count} != {live_side.triangle_count}"
        )

    report = {
        "schema": AB_SCHEMA,
        "status": "ok" if not issues else "failed",
        "issues": issues,
        "recorded": recorded_side.__dict__,
        "live": live_side.__dict__,
        "boundary": {
            "providerShape": PROVIDER_SHAPE,
            "sourceFrameExpansionThread": "matter-worker",
            "recordedInputEquivalent": True,
            "gpuAdapterBoundaryUnchanged": True,
            "highRatePayloadInJson": False,
        },
        "promotion": {
            "liveRecordedProviderAbReadyCandidate": not issues,
            "runtimeSelectionPermitted": False,
            "runtimeForceAuthority": False,
            "gpuComputeReady": False,
            "reason": "provider-ab-evidence-only",
        },
    }
    return ProviderAbResult(ok=not issues, issues=issues, report=report)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare recorded-hand and live OpenXR hand Hostess evidence summaries "
            "for the same provider/worker boundary."
        )
    )
    parser.add_argument("--recorded", required=True, type=Path)
    parser.add_argument("--live", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    recorded_path = resolve_summary_path(args.recorded.resolve())
    live_path = resolve_summary_path(args.live.resolve())
    result = validate_provider_ab(
        load_summary(recorded_path),
        load_summary(live_path),
        recorded_path,
        live_path,
    )
    output = json.dumps(result.report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
