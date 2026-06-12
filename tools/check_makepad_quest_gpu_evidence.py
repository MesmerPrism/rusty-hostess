"""Validate Hostess Makepad Quest live-hand GPU proof summaries.

The checker is intentionally narrow: it validates the compact summary produced
for the live-input-equivalent hand GPU proof run and rejects stale-heavy debug
runs as performance evidence. Raw device artifacts stay outside the repo.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MAX_HOSTESS_STALE = 30.0
DEFAULT_MIN_APP_FRAME_RATE_HZ = 85.0
DEFAULT_MIN_XR_EFFECTIVE_FRAME_RATE_HZ = 89.0

REQUIRED_MARKERS = {
    "proof_schedule": "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_SCHEDULE",
    "gpu_skinning_probe": "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE",
    "gpu_skinning_mesh_residency": "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_MESH_RESIDENCY",
    "gpu_mesh_sdf_probe": "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE",
}


@dataclass(frozen=True)
class EvidenceThresholds:
    max_hostess_stale: float = DEFAULT_MAX_HOSTESS_STALE
    min_app_frame_rate_hz: float = DEFAULT_MIN_APP_FRAME_RATE_HZ
    min_xr_effective_frame_rate_hz: float = DEFAULT_MIN_XR_EFFECTIVE_FRAME_RATE_HZ


@dataclass(frozen=True)
class EvidenceCheckResult:
    ok: bool
    issues: list[str]
    summary: dict[str, Any]


def load_summary(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return value


def resolve_summary_path(input_path: Path) -> Path:
    if input_path.is_file():
        return input_path
    if not input_path.is_dir():
        raise FileNotFoundError(f"summary path does not exist: {input_path}")
    preferred = input_path / "live-hand-small-profile-summary.json"
    if preferred.is_file():
        return preferred
    candidates = sorted(input_path.glob("*summary.json"))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(f"no *summary.json file found under {input_path}")
    names = ", ".join(candidate.name for candidate in candidates)
    raise FileExistsError(f"multiple summary candidates under {input_path}: {names}")


def validate_summary(
    summary: dict[str, Any], thresholds: EvidenceThresholds = EvidenceThresholds()
) -> EvidenceCheckResult:
    issues: list[str] = []
    schema = str(summary.get("schema", ""))
    if schema != "rusty.hostess.quest_live_hand_small_profile_summary.v1":
        issues.append(f"unexpected schema: {schema or 'missing'}")

    markers = object_value(summary, "markers")
    for key, marker_name in REQUIRED_MARKERS.items():
        if numeric(markers.get(key)) < 1:
            issues.append(f"missing required marker count for {marker_name}")

    cadence = object_value(summary, "cadence")
    app_rate_avg = nested_numeric(cadence, "app_frame_rate_hz", "avg")
    xr_update_avg = nested_numeric(cadence, "xr_update_rate_hz", "avg")
    xr_effective_avg = nested_numeric(cadence, "xr_effective_frame_rate_hz", "avg")
    repaint_gpu_avg = nested_numeric(cadence, "xr_repaint_gpu_ms", "avg")
    update_dispatch_avg = nested_numeric(cadence, "xr_update_dispatch_ms", "avg")

    if app_rate_avg < thresholds.min_app_frame_rate_hz:
        issues.append(
            "app_frame_rate_hz.avg "
            f"{app_rate_avg:.3f} < {thresholds.min_app_frame_rate_hz:.3f}"
        )
    if xr_update_avg < thresholds.min_app_frame_rate_hz:
        issues.append(
            "xr_update_rate_hz.avg "
            f"{xr_update_avg:.3f} < {thresholds.min_app_frame_rate_hz:.3f}"
        )
    if xr_effective_avg < thresholds.min_xr_effective_frame_rate_hz:
        issues.append(
            "xr_effective_frame_rate_hz.avg "
            f"{xr_effective_avg:.3f} < {thresholds.min_xr_effective_frame_rate_hz:.3f}"
        )
    if repaint_gpu_avg <= 0.0:
        issues.append("xr_repaint_gpu_ms.avg missing or nonpositive")
    if update_dispatch_avg <= 0.0:
        issues.append("xr_update_dispatch_ms.avg missing or nonpositive")

    hostess_vrapi = object_value(summary, "vrapi_hostess_process")
    stale_90_plus = numeric(hostess_vrapi.get("stale_90_plus_count"))
    stale_30_plus = numeric(hostess_vrapi.get("stale_30_plus_count"))
    stale_max = nested_numeric(hostess_vrapi, "stale", "max")
    if stale_90_plus != 0:
        issues.append(f"Hostess VrApi stale_90_plus_count is {stale_90_plus:g}")
    if stale_30_plus != 0:
        issues.append(f"Hostess VrApi stale_30_plus_count is {stale_30_plus:g}")
    if stale_max > thresholds.max_hostess_stale:
        issues.append(
            f"Hostess VrApi stale.max {stale_max:.3f} > "
            f"{thresholds.max_hostess_stale:.3f}"
        )

    proof_lines = summary.get("proof_lines", [])
    if not isinstance(proof_lines, list):
        issues.append("proof_lines is not a list")
        proof_lines = []
    proof_text = "\n".join(str(line) for line in proof_lines)
    for marker_name in REQUIRED_MARKERS.values():
        if marker_name not in proof_text:
            issues.append(f"proof line missing {marker_name}")
    for marker_name in (
        "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE",
        "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_MESH_RESIDENCY",
        "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE",
    ):
        marker_line = first_line_containing(proof_lines, marker_name)
        if "readbackMatched=true" not in marker_line:
            issues.append(f"{marker_name} did not report readbackMatched=true")
        if "queueWaitIdlePerformed=false" not in marker_line:
            issues.append(f"{marker_name} did not report queueWaitIdlePerformed=false")
        if "recordedInputEquivalent=true" not in marker_line:
            issues.append(f"{marker_name} did not report recordedInputEquivalent=true")
    mesh_sdf_line = first_line_containing(proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE")
    if "denseSdfConstructedOnGpu=true" not in mesh_sdf_line:
        issues.append("mesh-SDF proof did not report denseSdfConstructedOnGpu=true")
    if "fullSourceMeshConsumedByGpu=true" not in mesh_sdf_line:
        issues.append("mesh-SDF proof did not report fullSourceMeshConsumedByGpu=true")

    compact = {
        "schema": schema,
        "evidence_root": summary.get("evidence_root"),
        "app_frame_rate_hz_avg": app_rate_avg,
        "xr_update_rate_hz_avg": xr_update_avg,
        "xr_effective_frame_rate_hz_avg": xr_effective_avg,
        "hostess_stale_max": stale_max,
        "hostess_stale_30_plus_count": stale_30_plus,
        "hostess_stale_90_plus_count": stale_90_plus,
        "required_marker_counts": {
            key: int(numeric(markers.get(key))) for key in REQUIRED_MARKERS
        },
    }
    return EvidenceCheckResult(ok=not issues, issues=issues, summary=compact)


def object_value(value: dict[str, Any], key: str) -> dict[str, Any]:
    child = value.get(key, {})
    return child if isinstance(child, dict) else {}


def nested_numeric(value: dict[str, Any], child_key: str, leaf_key: str) -> float:
    child = value.get(child_key, {})
    if not isinstance(child, dict):
        return 0.0
    return numeric(child.get(leaf_key))


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


def first_line_containing(lines: list[Any], token: str) -> str:
    for line in lines:
        text = str(line)
        if token in text:
            return text
    return ""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a Hostess Makepad Quest live-hand GPU proof summary and "
            "reject stale-heavy runs as performance evidence."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a summary JSON file or an evidence root containing one.",
    )
    parser.add_argument(
        "--max-hostess-stale",
        type=float,
        default=DEFAULT_MAX_HOSTESS_STALE,
        help="Maximum allowed Hostess-process VrApi Stale value.",
    )
    parser.add_argument(
        "--min-app-frame-rate-hz",
        type=float,
        default=DEFAULT_MIN_APP_FRAME_RATE_HZ,
        help="Minimum allowed average app and XR update rate.",
    )
    parser.add_argument(
        "--min-xr-effective-frame-rate-hz",
        type=float,
        default=DEFAULT_MIN_XR_EFFECTIVE_FRAME_RATE_HZ,
        help="Minimum allowed average XR effective frame rate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    summary_path = resolve_summary_path(args.input)
    thresholds = EvidenceThresholds(
        max_hostess_stale=args.max_hostess_stale,
        min_app_frame_rate_hz=args.min_app_frame_rate_hz,
        min_xr_effective_frame_rate_hz=args.min_xr_effective_frame_rate_hz,
    )
    result = validate_summary(load_summary(summary_path), thresholds)
    payload = {
        "schema": "rusty.hostess.makepad.quest_gpu_evidence_check.v1",
        "summary_path": str(summary_path),
        "status": "ok" if result.ok else "failed",
        "issues": result.issues,
        "summary": result.summary,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
