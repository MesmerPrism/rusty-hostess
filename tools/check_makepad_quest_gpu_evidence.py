"""Validate Hostess Makepad Quest live-hand GPU proof summaries.

The checker is intentionally narrow: it validates the compact summary produced
for the live-input-equivalent hand GPU proof run and rejects stale-heavy debug
runs as performance evidence. Raw device artifacts stay outside the repo.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MAX_HOSTESS_STALE = 30.0
DEFAULT_MAX_HOSTESS_STALE_AVG = 3.0
DEFAULT_MAX_HOSTESS_STALE_NONZERO_RATIO = 0.85
DEFAULT_MAX_HOSTESS_STALE_NONZERO_COUNT = 90.0
DEFAULT_MIN_APP_FRAME_RATE_HZ = 85.0
DEFAULT_MIN_XR_EFFECTIVE_FRAME_RATE_HZ = 89.0

REQUIRED_MARKERS = {
    "proof_schedule": "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_SCHEDULE",
    "gpu_skinning_probe": "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE",
    "gpu_skinning_mesh_residency": "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_MESH_RESIDENCY",
    "gpu_mesh_sdf_probe": "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE",
}
PROOF_SUMMARY_SCHEMA = "rusty.hostess.quest_live_hand_small_profile_summary.v1"
CANONICAL_PROOF_SUMMARY_NAME = "live-hand-small-profile-summary.json"


@dataclass(frozen=True)
class EvidenceThresholds:
    max_hostess_stale: float = DEFAULT_MAX_HOSTESS_STALE
    max_hostess_stale_avg: float = DEFAULT_MAX_HOSTESS_STALE_AVG
    max_hostess_stale_nonzero_ratio: float = DEFAULT_MAX_HOSTESS_STALE_NONZERO_RATIO
    max_hostess_stale_nonzero_count: float = DEFAULT_MAX_HOSTESS_STALE_NONZERO_COUNT
    min_app_frame_rate_hz: float = DEFAULT_MIN_APP_FRAME_RATE_HZ
    min_xr_effective_frame_rate_hz: float = DEFAULT_MIN_XR_EFFECTIVE_FRAME_RATE_HZ
    require_mesh_sdf_program_reuse: bool = False
    require_mesh_sdf_source_buffer_reuse: bool = False
    require_mesh_sdf_derived_buffer_reuse: bool = False
    require_mesh_sdf_min_sample_count: int = 0


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
    preferred = input_path / CANONICAL_PROOF_SUMMARY_NAME
    if preferred.is_file():
        return preferred
    candidates = [
        candidate
        for candidate in sorted(input_path.glob("*summary*.json"))
        if candidate.is_file() and summary_file_has_schema(candidate, PROOF_SUMMARY_SCHEMA)
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(
            f"no Hostess GPU proof summary JSON found under {input_path}; "
            f"expected {CANONICAL_PROOF_SUMMARY_NAME} or schema {PROOF_SUMMARY_SCHEMA}"
        )
    names = ", ".join(candidate.name for candidate in candidates)
    raise FileExistsError(f"multiple Hostess GPU proof summaries under {input_path}: {names}")


def summary_file_has_schema(path: Path, schema: str) -> bool:
    try:
        value = load_summary(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return str(value.get("schema", "")) == schema


def validate_summary(
    summary: dict[str, Any], thresholds: EvidenceThresholds = EvidenceThresholds()
) -> EvidenceCheckResult:
    issues: list[str] = []
    schema = str(summary.get("schema", ""))
    if schema != PROOF_SUMMARY_SCHEMA:
        issues.append(f"unexpected schema: {schema or 'missing'}")

    markers = object_value(summary, "markers")
    for key, marker_name in REQUIRED_MARKERS.items():
        if numeric(markers.get(key)) < 1:
            issues.append(f"missing required marker count for {marker_name}")

    cadence = object_value(summary, "cadence")
    app_rate_avg = nested_numeric(cadence, "app_frame_rate_hz", "avg")
    xr_update_avg = nested_numeric(cadence, "xr_update_rate_hz", "avg")
    xr_effective_avg = nested_numeric(cadence, "xr_effective_frame_rate_hz", "avg")
    xr_effective_min = nested_numeric(cadence, "xr_effective_frame_rate_hz", "min")
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
    if xr_effective_min < thresholds.min_xr_effective_frame_rate_hz:
        issues.append(
            "xr_effective_frame_rate_hz.min "
            f"{xr_effective_min:.3f} < {thresholds.min_xr_effective_frame_rate_hz:.3f}"
        )
    if repaint_gpu_avg <= 0.0:
        issues.append("xr_repaint_gpu_ms.avg missing or nonpositive")
    if update_dispatch_avg <= 0.0:
        issues.append("xr_update_dispatch_ms.avg missing or nonpositive")

    hostess_vrapi = object_value(summary, "vrapi_hostess_process")
    stale_90_plus = numeric(hostess_vrapi.get("stale_90_plus_count"))
    stale_30_plus = numeric(hostess_vrapi.get("stale_30_plus_count"))
    stale_nonzero_count = numeric(hostess_vrapi.get("stale_nonzero_count"))
    stale_count = nested_numeric(hostess_vrapi, "stale", "count")
    stale_max = nested_numeric(hostess_vrapi, "stale", "max")
    stale_avg = nested_numeric(hostess_vrapi, "stale", "avg")
    stale_nonzero_ratio = (
        stale_nonzero_count / stale_count if stale_count > 0.0 else 0.0
    )
    if stale_90_plus != 0:
        issues.append(f"Hostess VrApi stale_90_plus_count is {stale_90_plus:g}")
    if stale_30_plus != 0:
        issues.append(f"Hostess VrApi stale_30_plus_count is {stale_30_plus:g}")
    if stale_max > thresholds.max_hostess_stale:
        issues.append(
            f"Hostess VrApi stale.max {stale_max:.3f} > "
            f"{thresholds.max_hostess_stale:.3f}"
        )
    if stale_avg > thresholds.max_hostess_stale_avg:
        issues.append(
            f"Hostess VrApi stale.avg {stale_avg:.3f} > "
            f"{thresholds.max_hostess_stale_avg:.3f}"
        )
    if stale_nonzero_count > thresholds.max_hostess_stale_nonzero_count:
        issues.append(
            "Hostess VrApi stale_nonzero_count "
            f"{stale_nonzero_count:g} > {thresholds.max_hostess_stale_nonzero_count:g}"
        )
    if stale_nonzero_ratio > thresholds.max_hostess_stale_nonzero_ratio:
        issues.append(
            "Hostess VrApi stale_nonzero_ratio "
            f"{stale_nonzero_ratio:.3f} > "
            f"{thresholds.max_hostess_stale_nonzero_ratio:.3f}"
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
        marker_lines = lines_containing(proof_lines, marker_name)
        if not marker_lines:
            continue
        for marker_line in marker_lines:
            if "readbackMatched=true" not in marker_line:
                issues.append(f"{marker_name} did not report readbackMatched=true")
            if "queueWaitIdlePerformed=false" not in marker_line:
                issues.append(f"{marker_name} did not report queueWaitIdlePerformed=false")
            if "recordedInputEquivalent=true" not in marker_line:
                issues.append(f"{marker_name} did not report recordedInputEquivalent=true")
    mesh_sdf_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE"
    )
    if not any("denseSdfConstructedOnGpu=true" in line for line in mesh_sdf_lines):
        issues.append("mesh-SDF proof did not report denseSdfConstructedOnGpu=true")
    if not any("fullSourceMeshConsumedByGpu=true" in line for line in mesh_sdf_lines):
        issues.append("mesh-SDF proof did not report fullSourceMeshConsumedByGpu=true")
    mesh_sdf_program_reuse_count = count_lines_containing(
        mesh_sdf_lines, "programReused=true"
    )
    mesh_sdf_program_setup_count = sum(
        1
        for line in mesh_sdf_lines
        if "programReused=false" in line
        or "shaderCompiledThisSubmit=true" in line
        or "pipelineCreatedThisSubmit=true" in line
    )
    mesh_sdf_shader_compile_count = count_lines_containing(
        mesh_sdf_lines, "shaderCompiledThisSubmit=true"
    )
    mesh_sdf_pipeline_create_count = count_lines_containing(
        mesh_sdf_lines, "pipelineCreatedThisSubmit=true"
    )
    mesh_sdf_derived_resident_count = count_lines_containing(
        mesh_sdf_lines, "derivedBuffersResident=true"
    )
    mesh_sdf_derived_reuse_count = count_lines_containing(
        mesh_sdf_lines, "derivedBuffersReused=true"
    )
    mesh_sdf_source_resident_count = count_lines_containing(
        mesh_sdf_lines, "sourceMeshBuffersResident=true"
    )
    mesh_sdf_source_reuse_count = count_lines_containing(
        mesh_sdf_lines, "sourceMeshBuffersReused=true"
    )
    mesh_sdf_sample_counts = marker_int_fields(mesh_sdf_lines, "sampleCount")
    mesh_sdf_max_sample_count = max(mesh_sdf_sample_counts, default=0)
    mesh_sdf_min_sample_count = min(mesh_sdf_sample_counts, default=0)
    if thresholds.require_mesh_sdf_program_reuse and mesh_sdf_program_reuse_count < 1:
        issues.append("mesh-SDF proof did not include programReused=true")
    if (
        thresholds.require_mesh_sdf_source_buffer_reuse
        and mesh_sdf_source_reuse_count < 1
    ):
        issues.append("mesh-SDF proof did not include sourceMeshBuffersReused=true")
    if (
        thresholds.require_mesh_sdf_derived_buffer_reuse
        and mesh_sdf_derived_reuse_count < 1
    ):
        issues.append("mesh-SDF proof did not include derivedBuffersReused=true")
    if (
        thresholds.require_mesh_sdf_min_sample_count > 0
        and mesh_sdf_max_sample_count < thresholds.require_mesh_sdf_min_sample_count
    ):
        issues.append(
            "mesh-SDF proof max sampleCount "
            f"{mesh_sdf_max_sample_count} < {thresholds.require_mesh_sdf_min_sample_count}"
        )

    compact = {
        "schema": schema,
        "evidence_root": summary.get("evidence_root"),
        "app_frame_rate_hz_avg": app_rate_avg,
        "xr_update_rate_hz_avg": xr_update_avg,
        "xr_effective_frame_rate_hz_avg": xr_effective_avg,
        "xr_effective_frame_rate_hz_min": xr_effective_min,
        "hostess_stale_max": stale_max,
        "hostess_stale_avg": stale_avg,
        "hostess_stale_nonzero_count": stale_nonzero_count,
        "hostess_stale_nonzero_ratio": stale_nonzero_ratio,
        "hostess_stale_30_plus_count": stale_30_plus,
        "hostess_stale_90_plus_count": stale_90_plus,
        "mesh_sdf_proof_line_count": len(mesh_sdf_lines),
        "mesh_sdf_program_setup_count": mesh_sdf_program_setup_count,
        "mesh_sdf_program_reuse_count": mesh_sdf_program_reuse_count,
        "mesh_sdf_shader_compile_count": mesh_sdf_shader_compile_count,
        "mesh_sdf_pipeline_create_count": mesh_sdf_pipeline_create_count,
        "mesh_sdf_source_buffer_resident_count": mesh_sdf_source_resident_count,
        "mesh_sdf_source_buffer_reuse_count": mesh_sdf_source_reuse_count,
        "mesh_sdf_derived_buffer_resident_count": mesh_sdf_derived_resident_count,
        "mesh_sdf_derived_buffer_reuse_count": mesh_sdf_derived_reuse_count,
        "mesh_sdf_min_sample_count": mesh_sdf_min_sample_count,
        "mesh_sdf_max_sample_count": mesh_sdf_max_sample_count,
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


def lines_containing(lines: list[Any], token: str) -> list[str]:
    return [str(line) for line in lines if token in str(line)]


def count_lines_containing(lines: list[str], token: str) -> int:
    return sum(1 for line in lines if token in line)


def marker_int_fields(lines: list[str], field_name: str) -> list[int]:
    pattern = re.compile(rf"\b{re.escape(field_name)}=(\d+)\b")
    values: list[int] = []
    for line in lines:
        values.extend(int(match.group(1)) for match in pattern.finditer(line))
    return values


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
        "--max-hostess-stale-avg",
        type=float,
        default=DEFAULT_MAX_HOSTESS_STALE_AVG,
        help="Maximum allowed average Hostess-process VrApi Stale value.",
    )
    parser.add_argument(
        "--max-hostess-stale-nonzero-ratio",
        type=float,
        default=DEFAULT_MAX_HOSTESS_STALE_NONZERO_RATIO,
        help="Maximum allowed fraction of Hostess-process VrApi samples with Stale > 0.",
    )
    parser.add_argument(
        "--max-hostess-stale-nonzero-count",
        type=float,
        default=DEFAULT_MAX_HOSTESS_STALE_NONZERO_COUNT,
        help="Maximum allowed Hostess-process VrApi sample count with Stale > 0.",
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
    parser.add_argument(
        "--require-mesh-sdf-program-reuse",
        action="store_true",
        help="Require at least one mesh-SDF proof line with programReused=true.",
    )
    parser.add_argument(
        "--require-mesh-sdf-derived-buffer-reuse",
        action="store_true",
        help="Require at least one mesh-SDF proof line with derivedBuffersReused=true.",
    )
    parser.add_argument(
        "--require-mesh-sdf-source-buffer-reuse",
        action="store_true",
        help="Require at least one mesh-SDF proof line with sourceMeshBuffersReused=true.",
    )
    parser.add_argument(
        "--require-mesh-sdf-min-sample-count",
        type=int,
        default=0,
        help="Require at least one mesh-SDF proof line with sampleCount at or above this value.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    summary_path = resolve_summary_path(args.input)
    thresholds = EvidenceThresholds(
        max_hostess_stale=args.max_hostess_stale,
        max_hostess_stale_avg=args.max_hostess_stale_avg,
        max_hostess_stale_nonzero_ratio=args.max_hostess_stale_nonzero_ratio,
        max_hostess_stale_nonzero_count=args.max_hostess_stale_nonzero_count,
        min_app_frame_rate_hz=args.min_app_frame_rate_hz,
        min_xr_effective_frame_rate_hz=args.min_xr_effective_frame_rate_hz,
        require_mesh_sdf_program_reuse=args.require_mesh_sdf_program_reuse,
        require_mesh_sdf_source_buffer_reuse=args.require_mesh_sdf_source_buffer_reuse,
        require_mesh_sdf_derived_buffer_reuse=args.require_mesh_sdf_derived_buffer_reuse,
        require_mesh_sdf_min_sample_count=args.require_mesh_sdf_min_sample_count,
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
