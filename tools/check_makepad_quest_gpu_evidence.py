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
EXPANDED_FORCE_ORACLE_SAMPLE_COUNT = 16

CORE_REQUIRED_MARKERS = {
    "proof_schedule": "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_SCHEDULE",
    "gpu_skinning_probe": "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE",
    "gpu_skinning_mesh_residency": "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_MESH_RESIDENCY",
    "gpu_mesh_sdf_probe": "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE",
    "gpu_field_construction": "RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION",
    "gpu_field_sampling_probe": "RUSTY_QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE",
}
OPTIONAL_STAGE_MARKERS = {
    "gpu_field_force_sampling_probe": "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE",
    "gpu_field_particle_force_probe": "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE",
    "gpu_force_freshness": "RUSTY_HOSTESS_MAKEPAD_GPU_FORCE_FRESHNESS",
    "gpu_force_authority_candidate": "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_CANDIDATE",
    "gpu_force_authority_gate": "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_GATE",
    "gpu_force_authority_residency": "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY",
}
OPTIONAL_MARKERS = {
    "gpu_proof_epoch": "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_EPOCH",
}
REQUIRED_MARKERS = {**CORE_REQUIRED_MARKERS, **OPTIONAL_STAGE_MARKERS}
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
    require_gpu_proof_epoch: bool = False
    require_gpu_field_force_sampling: bool = False
    require_gpu_field_particle_force: bool = False
    require_gpu_force_freshness: bool = False
    require_gpu_force_authority_candidate: bool = False
    require_gpu_force_authority_gate: bool = False
    require_gpu_force_authority_residency: bool = False
    require_gpu_force_profile_enabled: bool = False
    require_gpu_force_steady_state_fallback: bool = False
    require_gpu_force_fresh_expanded_oracle_fallback: bool = False
    require_gpu_force_expanded_oracle_provider_ab_fallback: bool = False
    min_field_particle_force_sample_count: int = 0
    min_force_residency_observed_proofs: int = 0
    min_force_residency_reused_proofs: int = 0


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
    required_markers = dict(CORE_REQUIRED_MARKERS)
    if thresholds.require_gpu_field_force_sampling:
        required_markers["gpu_field_force_sampling_probe"] = OPTIONAL_STAGE_MARKERS[
            "gpu_field_force_sampling_probe"
        ]
    if thresholds.require_gpu_field_particle_force:
        required_markers["gpu_field_particle_force_probe"] = OPTIONAL_STAGE_MARKERS[
            "gpu_field_particle_force_probe"
        ]
    if thresholds.require_gpu_force_freshness:
        required_markers["gpu_force_freshness"] = OPTIONAL_STAGE_MARKERS[
            "gpu_force_freshness"
        ]
    if thresholds.require_gpu_force_authority_candidate:
        required_markers["gpu_force_authority_candidate"] = OPTIONAL_STAGE_MARKERS[
            "gpu_force_authority_candidate"
        ]
    if thresholds.require_gpu_force_authority_gate:
        required_markers["gpu_force_authority_gate"] = OPTIONAL_STAGE_MARKERS[
            "gpu_force_authority_gate"
        ]
    if thresholds.require_gpu_force_authority_residency:
        required_markers["gpu_force_authority_residency"] = OPTIONAL_STAGE_MARKERS[
            "gpu_force_authority_residency"
        ]
    for key, marker_name in required_markers.items():
        if numeric(markers.get(key)) < 1:
            issues.append(f"missing required marker count for {marker_name}")
    if thresholds.require_gpu_proof_epoch:
        for key, marker_name in OPTIONAL_MARKERS.items():
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
    for marker_name in required_markers.values():
        if marker_name not in proof_text:
            issues.append(f"proof line missing {marker_name}")
    if thresholds.require_gpu_proof_epoch:
        for marker_name in OPTIONAL_MARKERS.values():
            if marker_name not in proof_text:
                issues.append(f"proof line missing {marker_name}")
    gpu_proof_epoch_lines = lines_containing(
        proof_lines, OPTIONAL_MARKERS["gpu_proof_epoch"]
    )
    gpu_proof_epoch_reset_count = count_lines_containing(
        gpu_proof_epoch_lines, "proofCountersReset=true"
    )
    gpu_proof_epoch_no_runtime_reload_count = count_lines_containing(
        gpu_proof_epoch_lines, "runtimeSettingsReloaded=false"
    )
    gpu_proof_epoch_no_replay_rebuild_count = count_lines_containing(
        gpu_proof_epoch_lines, "replayRuntimeRebuilt=false"
    )
    gpu_proof_epoch_no_worker_restart_count = count_lines_containing(
        gpu_proof_epoch_lines, "matterWorkerRestarted=false"
    )
    gpu_proof_epoch_low_rate_count = count_lines_containing(
        gpu_proof_epoch_lines, "highRateJsonPayload=false"
    )
    if thresholds.require_gpu_proof_epoch and not gpu_proof_epoch_lines:
        issues.append("GPU proof epoch marker was required but not present")
    if thresholds.require_gpu_proof_epoch and gpu_proof_epoch_lines:
        if gpu_proof_epoch_reset_count != len(gpu_proof_epoch_lines):
            issues.append("GPU proof epoch did not report proofCountersReset=true")
        if gpu_proof_epoch_no_runtime_reload_count != len(gpu_proof_epoch_lines):
            issues.append("GPU proof epoch did not keep runtimeSettingsReloaded=false")
        if gpu_proof_epoch_no_replay_rebuild_count != len(gpu_proof_epoch_lines):
            issues.append("GPU proof epoch did not keep replayRuntimeRebuilt=false")
        if gpu_proof_epoch_no_worker_restart_count != len(gpu_proof_epoch_lines):
            issues.append("GPU proof epoch did not keep matterWorkerRestarted=false")
        if gpu_proof_epoch_low_rate_count != len(gpu_proof_epoch_lines):
            issues.append("GPU proof epoch did not keep highRateJsonPayload=false")
    for marker_name in (
        "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE",
        "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_MESH_RESIDENCY",
        "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE",
        "RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION",
        "RUSTY_QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE",
        "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE",
        "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE",
        "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_CANDIDATE",
        "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_GATE",
        "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY",
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
    field_construction_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION"
    )
    field_construction_ready_count = count_lines_containing(
        field_construction_lines, "runtimeFieldBoundaryReady=true"
    )
    field_construction_force_authority_false_count = count_lines_containing(
        field_construction_lines, "forceAuthorityReady=false"
    )
    field_construction_runtime_authority_false_count = count_lines_containing(
        field_construction_lines, "runtimeForceAuthority=false"
    )
    field_construction_gpu_not_ready_count = count_lines_containing(
        field_construction_lines, "gpuComputeReady=false"
    )
    field_construction_low_rate_count = count_lines_containing(
        field_construction_lines, "highRateJsonPayload=false"
    )
    if field_construction_ready_count != len(field_construction_lines):
        issues.append("GPU field construction receipt did not keep runtimeFieldBoundaryReady=true")
    if field_construction_force_authority_false_count != len(field_construction_lines):
        issues.append("GPU field construction receipt did not keep forceAuthorityReady=false")
    if field_construction_runtime_authority_false_count != len(field_construction_lines):
        issues.append("GPU field construction receipt did not keep runtimeForceAuthority=false")
    if not any("fieldKind=dense-sdf" in line for line in field_construction_lines):
        issues.append("GPU field construction receipt did not report fieldKind=dense-sdf")
    if field_construction_gpu_not_ready_count != len(field_construction_lines):
        issues.append("GPU field construction receipt did not keep gpuComputeReady=false")
    if field_construction_low_rate_count != len(field_construction_lines):
        issues.append("GPU field construction receipt did not keep highRateJsonPayload=false")
    field_sampling_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE"
    )
    field_sampling_ready_count = count_lines_containing(
        field_sampling_lines, "runtimeSamplingBoundaryReady=true"
    )
    field_sampling_field_ready_count = count_lines_containing(
        field_sampling_lines, "runtimeFieldBoundaryReady=true"
    )
    field_sampling_resident_count = count_lines_containing(
        field_sampling_lines, "residentFieldBufferSampled=true"
    )
    field_sampling_generation_match_count = count_lines_containing(
        field_sampling_lines, "sourceFieldGenerationMatched=true"
    )
    field_sampling_kernel_count = count_lines_containing(
        field_sampling_lines, "fieldSamplingKernel=true"
    )
    field_sampling_force_authority_false_count = count_lines_containing(
        field_sampling_lines, "forceAuthorityReady=false"
    )
    field_sampling_runtime_authority_false_count = count_lines_containing(
        field_sampling_lines, "runtimeForceAuthority=false"
    )
    field_sampling_gpu_not_ready_count = count_lines_containing(
        field_sampling_lines, "gpuComputeReady=false"
    )
    field_sampling_low_rate_count = count_lines_containing(
        field_sampling_lines, "highRateJsonPayload=false"
    )
    if field_sampling_ready_count != len(field_sampling_lines):
        issues.append("GPU field sampling probe did not keep runtimeSamplingBoundaryReady=true")
    if field_sampling_field_ready_count != len(field_sampling_lines):
        issues.append("GPU field sampling probe did not keep runtimeFieldBoundaryReady=true")
    if field_sampling_resident_count != len(field_sampling_lines):
        issues.append("GPU field sampling probe did not report residentFieldBufferSampled=true")
    if field_sampling_generation_match_count != len(field_sampling_lines):
        issues.append("GPU field sampling probe did not match sourceFieldGeneration")
    if field_sampling_kernel_count != len(field_sampling_lines):
        issues.append("GPU field sampling probe did not report fieldSamplingKernel=true")
    if field_sampling_force_authority_false_count != len(field_sampling_lines):
        issues.append("GPU field sampling probe did not keep forceAuthorityReady=false")
    if field_sampling_runtime_authority_false_count != len(field_sampling_lines):
        issues.append("GPU field sampling probe did not keep runtimeForceAuthority=false")
    if not any("fieldKind=dense-sdf" in line for line in field_sampling_lines):
        issues.append("GPU field sampling probe did not report fieldKind=dense-sdf")
    if field_sampling_gpu_not_ready_count != len(field_sampling_lines):
        issues.append("GPU field sampling probe did not keep gpuComputeReady=false")
    if field_sampling_low_rate_count != len(field_sampling_lines):
        issues.append("GPU field sampling probe did not keep highRateJsonPayload=false")
    field_force_sampling_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE"
    )
    field_force_sampling_ready_count = count_lines_containing(
        field_force_sampling_lines, "runtimeForceSamplingBoundaryReady=true"
    )
    field_force_sampling_field_ready_count = count_lines_containing(
        field_force_sampling_lines, "runtimeFieldBoundaryReady=true"
    )
    field_force_sampling_resident_count = count_lines_containing(
        field_force_sampling_lines, "residentFieldBufferSampled=true"
    )
    field_force_sampling_generation_match_count = count_lines_containing(
        field_force_sampling_lines, "sourceFieldGenerationMatched=true"
    )
    field_force_sampling_kernel_count = count_lines_containing(
        field_force_sampling_lines, "fieldForceSamplingKernel=true"
    )
    field_force_sampling_particle_kernel_false_count = count_lines_containing(
        field_force_sampling_lines, "fieldParticleKernel=false"
    )
    field_force_sampling_runtime_particle_false_count = count_lines_containing(
        field_force_sampling_lines, "runtimeParticleIntegration=false"
    )
    field_force_sampling_force_authority_false_count = count_lines_containing(
        field_force_sampling_lines, "forceAuthorityReady=false"
    )
    field_force_sampling_runtime_authority_false_count = count_lines_containing(
        field_force_sampling_lines, "runtimeForceAuthority=false"
    )
    field_force_sampling_gpu_not_ready_count = count_lines_containing(
        field_force_sampling_lines, "gpuComputeReady=false"
    )
    field_force_sampling_low_rate_count = count_lines_containing(
        field_force_sampling_lines, "highRateJsonPayload=false"
    )
    if field_force_sampling_lines:
        if field_force_sampling_ready_count != len(field_force_sampling_lines):
            issues.append(
                "GPU field force sampling probe did not keep "
                "runtimeForceSamplingBoundaryReady=true"
            )
        if field_force_sampling_field_ready_count != len(field_force_sampling_lines):
            issues.append(
                "GPU field force sampling probe did not keep "
                "runtimeFieldBoundaryReady=true"
            )
        if field_force_sampling_resident_count != len(field_force_sampling_lines):
            issues.append(
                "GPU field force sampling probe did not report "
                "residentFieldBufferSampled=true"
            )
        if field_force_sampling_generation_match_count != len(field_force_sampling_lines):
            issues.append("GPU field force sampling probe did not match sourceFieldGeneration")
        if field_force_sampling_kernel_count != len(field_force_sampling_lines):
            issues.append(
                "GPU field force sampling probe did not report "
                "fieldForceSamplingKernel=true"
            )
        if field_force_sampling_particle_kernel_false_count != len(
            field_force_sampling_lines
        ):
            issues.append("GPU field force sampling probe did not keep fieldParticleKernel=false")
        if field_force_sampling_runtime_particle_false_count != len(
            field_force_sampling_lines
        ):
            issues.append(
                "GPU field force sampling probe did not keep "
                "runtimeParticleIntegration=false"
            )
        if field_force_sampling_force_authority_false_count != len(
            field_force_sampling_lines
        ):
            issues.append("GPU field force sampling probe did not keep forceAuthorityReady=false")
        if field_force_sampling_runtime_authority_false_count != len(
            field_force_sampling_lines
        ):
            issues.append("GPU field force sampling probe did not keep runtimeForceAuthority=false")
        if not any("fieldKind=dense-sdf" in line for line in field_force_sampling_lines):
            issues.append("GPU field force sampling probe did not report fieldKind=dense-sdf")
        if field_force_sampling_gpu_not_ready_count != len(field_force_sampling_lines):
            issues.append("GPU field force sampling probe did not keep gpuComputeReady=false")
        if field_force_sampling_low_rate_count != len(field_force_sampling_lines):
            issues.append(
                "GPU field force sampling probe did not keep highRateJsonPayload=false"
            )
    field_particle_force_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE"
    )
    field_particle_force_ready_count = count_lines_containing(
        field_particle_force_lines, "runtimeParticleForceComparisonReady=true"
    )
    field_particle_force_field_ready_count = count_lines_containing(
        field_particle_force_lines, "runtimeFieldBoundaryReady=true"
    )
    field_particle_force_resident_count = count_lines_containing(
        field_particle_force_lines, "residentFieldBufferSampled=true"
    )
    field_particle_force_generation_match_count = count_lines_containing(
        field_particle_force_lines, "sourceFieldGenerationMatched=true"
    )
    field_particle_force_kernel_count = count_lines_containing(
        field_particle_force_lines, "fieldParticleKernel=true"
    )
    field_particle_force_force_kernel_count = count_lines_containing(
        field_particle_force_lines, "fieldForceSamplingKernel=true"
    )
    field_particle_force_sample_source_count = count_lines_containing(
        field_particle_force_lines, "particleSampleSource=matter-particle-snapshot"
    )
    field_particle_force_matter_equation_count = count_lines_containing(
        field_particle_force_lines, "matterParticleForceEquation=true"
    )
    field_particle_force_runtime_particle_false_count = count_lines_containing(
        field_particle_force_lines, "runtimeParticleIntegration=false"
    )
    field_particle_force_force_authority_false_count = count_lines_containing(
        field_particle_force_lines, "forceAuthorityReady=false"
    )
    field_particle_force_runtime_authority_false_count = count_lines_containing(
        field_particle_force_lines, "runtimeForceAuthority=false"
    )
    field_particle_force_gpu_not_ready_count = count_lines_containing(
        field_particle_force_lines, "gpuComputeReady=false"
    )
    field_particle_force_low_rate_count = count_lines_containing(
        field_particle_force_lines, "highRateJsonPayload=false"
    )
    field_particle_force_sample_counts = marker_int_fields(
        field_particle_force_lines, "sampleCount"
    )
    field_particle_force_requested_sample_counts = marker_int_fields(
        field_particle_force_lines, "requestedParticleSampleCount"
    )
    field_particle_force_sampled_particle_counts = marker_int_fields(
        field_particle_force_lines, "sampledParticleCount"
    )
    field_particle_force_max_sample_count = max(
        field_particle_force_sample_counts, default=0
    )
    field_particle_force_max_requested_sample_count = max(
        field_particle_force_requested_sample_counts, default=0
    )
    field_particle_force_max_sampled_particle_count = max(
        field_particle_force_sampled_particle_counts, default=0
    )
    if field_particle_force_lines:
        if field_particle_force_ready_count != len(field_particle_force_lines):
            issues.append(
                "GPU field particle-force probe did not keep "
                "runtimeParticleForceComparisonReady=true"
            )
        if field_particle_force_field_ready_count != len(field_particle_force_lines):
            issues.append(
                "GPU field particle-force probe did not keep runtimeFieldBoundaryReady=true"
            )
        if field_particle_force_resident_count != len(field_particle_force_lines):
            issues.append(
                "GPU field particle-force probe did not report "
                "residentFieldBufferSampled=true"
            )
        if field_particle_force_generation_match_count != len(field_particle_force_lines):
            issues.append("GPU field particle-force probe did not match sourceFieldGeneration")
        if field_particle_force_kernel_count != len(field_particle_force_lines):
            issues.append("GPU field particle-force probe did not report fieldParticleKernel=true")
        if field_particle_force_force_kernel_count != len(field_particle_force_lines):
            issues.append(
                "GPU field particle-force probe did not report fieldForceSamplingKernel=true"
            )
        if field_particle_force_sample_source_count != len(field_particle_force_lines):
            issues.append(
                "GPU field particle-force probe did not report Matter particle snapshot source"
            )
        if field_particle_force_matter_equation_count != len(field_particle_force_lines):
            issues.append("GPU field particle-force probe did not report Matter force equation")
        if field_particle_force_runtime_particle_false_count != len(
            field_particle_force_lines
        ):
            issues.append(
                "GPU field particle-force probe did not keep runtimeParticleIntegration=false"
            )
        if field_particle_force_force_authority_false_count != len(
            field_particle_force_lines
        ):
            issues.append("GPU field particle-force probe did not keep forceAuthorityReady=false")
        if field_particle_force_runtime_authority_false_count != len(
            field_particle_force_lines
        ):
            issues.append("GPU field particle-force probe did not keep runtimeForceAuthority=false")
        if not any("fieldKind=dense-sdf" in line for line in field_particle_force_lines):
            issues.append("GPU field particle-force probe did not report fieldKind=dense-sdf")
        if field_particle_force_gpu_not_ready_count != len(field_particle_force_lines):
            issues.append("GPU field particle-force probe did not keep gpuComputeReady=false")
        if field_particle_force_low_rate_count != len(field_particle_force_lines):
            issues.append(
                "GPU field particle-force probe did not keep highRateJsonPayload=false"
            )
    if (
        thresholds.min_field_particle_force_sample_count > 0
        and field_particle_force_max_sample_count
        < thresholds.min_field_particle_force_sample_count
    ):
        issues.append(
            "GPU field particle-force proof max sampleCount "
            f"{field_particle_force_max_sample_count} < "
            f"{thresholds.min_field_particle_force_sample_count}"
        )
    force_candidate_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_CANDIDATE"
    )
    force_candidate_ready_count = count_lines_containing(
        force_candidate_lines, "forceAuthorityCandidateReady=true"
    )
    force_candidate_gpu_ready_count = count_lines_containing(
        force_candidate_lines, "gpuComputeCandidateReady=true"
    )
    force_candidate_single_authority_count = count_lines_containing(
        force_candidate_lines, "singleActiveForceAuthorityPreserved=true"
    )
    force_candidate_not_selected_count = count_lines_containing(
        force_candidate_lines, "candidateSelected=false"
    )
    force_candidate_not_promoted_count = count_lines_containing(
        force_candidate_lines, "candidatePromoted=false"
    )
    force_candidate_active_unchanged_count = count_lines_containing(
        force_candidate_lines, "activeForceAuthorityChanged=false"
    )
    force_candidate_force_authority_false_count = count_lines_containing(
        force_candidate_lines, "forceAuthorityReady=false"
    )
    force_candidate_runtime_authority_false_count = count_lines_containing(
        force_candidate_lines, "runtimeForceAuthority=false"
    )
    force_candidate_runtime_particle_false_count = count_lines_containing(
        force_candidate_lines, "runtimeParticleIntegration=false"
    )
    force_candidate_gpu_not_ready_count = count_lines_containing(
        force_candidate_lines, "gpuComputeReady=false"
    )
    force_candidate_low_rate_count = count_lines_containing(
        force_candidate_lines, "highRateJsonPayload=false"
    )
    force_candidate_settings_payload_false_count = count_lines_containing(
        force_candidate_lines, "settingsControlPayload=false"
    )
    if force_candidate_lines:
        if force_candidate_ready_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not keep forceAuthorityCandidateReady=true"
            )
        if force_candidate_gpu_ready_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not keep gpuComputeCandidateReady=true"
            )
        if force_candidate_single_authority_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not preserve single active authority"
            )
        if force_candidate_not_selected_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate was selected")
        if force_candidate_not_promoted_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate was promoted")
        if force_candidate_active_unchanged_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate changed active force authority")
        if force_candidate_force_authority_false_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate did not keep forceAuthorityReady=false")
        if force_candidate_runtime_authority_false_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate did not keep runtimeForceAuthority=false")
        if force_candidate_runtime_particle_false_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not keep runtimeParticleIntegration=false"
            )
        if force_candidate_gpu_not_ready_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate did not keep gpuComputeReady=false")
        if force_candidate_low_rate_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate did not keep highRateJsonPayload=false")
        if force_candidate_settings_payload_false_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not keep settingsControlPayload=false"
            )
    force_gate_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_GATE"
    )
    force_gate_candidate_ready_count = count_lines_containing(
        force_gate_lines, "forceAuthorityCandidateReady=true"
    )
    force_gate_gpu_candidate_ready_count = count_lines_containing(
        force_gate_lines, "gpuComputeCandidateReady=true"
    )
    force_gate_single_authority_count = count_lines_containing(
        force_gate_lines, "singleActiveForceAuthorityPreserved=true"
    )
    force_gate_slot_count = count_lines_containing(
        force_gate_lines, "forceAuthoritySlotCount=1"
    )
    force_gate_active_count = count_lines_containing(
        force_gate_lines, "activeForceAuthorityCount=1"
    )
    force_gate_profile_required_count = count_lines_containing(
        force_gate_lines, "profileGate=explicit-profile-required"
    )
    force_gate_profile_declared_count = count_lines_containing(
        force_gate_lines, "profileGateSatisfied="
    )
    force_gate_profile_satisfied_count = count_lines_containing(
        force_gate_lines, "profileGateSatisfied=true"
    )
    force_gate_profile_unsatisfied_count = count_lines_containing(
        force_gate_lines, "profileGateSatisfied=false"
    )
    force_gate_selection_blocked_count = count_lines_containing(
        force_gate_lines, "runtimeSelectionPermitted=false"
    )
    force_gate_profile_known_count = count_lines_containing(
        force_gate_lines, "gpuForceAuthorityProfileKnown=true"
    )
    force_gate_profile_state_declared_count = count_lines_containing(
        force_gate_lines, "gpuForceAuthorityProfileEnabled="
    )
    force_gate_profile_enabled_count = count_lines_containing(
        force_gate_lines, "gpuForceAuthorityProfileEnabled=true"
    )
    force_gate_profile_disabled_count = count_lines_containing(
        force_gate_lines, "gpuForceAuthorityProfileEnabled=false"
    )
    force_gate_active_kind_count = count_lines_containing(
        force_gate_lines, "activeForceAuthorityKind=matter-cpu"
    )
    force_gate_candidate_eligible_count = count_lines_containing(
        force_gate_lines, "candidateEligible=true"
    )
    force_gate_not_selected_count = count_lines_containing(
        force_gate_lines, "candidateSelected=false"
    )
    force_gate_not_promoted_count = count_lines_containing(
        force_gate_lines, "candidatePromoted=false"
    )
    force_gate_active_unchanged_count = count_lines_containing(
        force_gate_lines, "activeForceAuthorityChanged=false"
    )
    force_gate_fallback_ready_count = count_lines_containing(
        force_gate_lines, "matterCpuFallbackReady=true"
    )
    force_gate_rollback_policy_count = count_lines_containing(
        force_gate_lines,
        "rollbackPolicy=matter-cpu-oracle-on-gpu-freshness-or-cadence-failure",
    )
    force_gate_force_authority_false_count = count_lines_containing(
        force_gate_lines, "forceAuthorityReady=false"
    )
    force_gate_runtime_authority_false_count = count_lines_containing(
        force_gate_lines, "runtimeForceAuthority=false"
    )
    force_gate_runtime_particle_false_count = count_lines_containing(
        force_gate_lines, "runtimeParticleIntegration=false"
    )
    force_gate_gpu_not_ready_count = count_lines_containing(
        force_gate_lines, "gpuComputeReady=false"
    )
    force_gate_low_rate_count = count_lines_containing(
        force_gate_lines, "highRateJsonPayload=false"
    )
    force_gate_settings_payload_false_count = count_lines_containing(
        force_gate_lines, "settingsControlPayload=false"
    )
    if force_gate_lines:
        if force_gate_candidate_ready_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not keep forceAuthorityCandidateReady=true"
            )
        if force_gate_gpu_candidate_ready_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not keep gpuComputeCandidateReady=true"
            )
        if force_gate_single_authority_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not preserve single authority")
        if force_gate_slot_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not report forceAuthoritySlotCount=1")
        if force_gate_active_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not report activeForceAuthorityCount=1")
        if force_gate_profile_required_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not require explicit profile selection"
            )
        if force_gate_profile_declared_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not declare profileGateSatisfied")
        if force_gate_selection_blocked_count != len(force_gate_lines):
            issues.append("GPU force authority gate permitted runtime selection")
        if force_gate_profile_known_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not report profile knowledge")
        if force_gate_profile_state_declared_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not declare gpuForceAuthorityProfileEnabled"
            )
        if force_gate_active_kind_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep Matter CPU active kind")
        if force_gate_candidate_eligible_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep candidateEligible=true")
        if force_gate_not_selected_count != len(force_gate_lines):
            issues.append("GPU force authority gate selected the candidate")
        if force_gate_not_promoted_count != len(force_gate_lines):
            issues.append("GPU force authority gate promoted the candidate")
        if force_gate_active_unchanged_count != len(force_gate_lines):
            issues.append("GPU force authority gate changed active force authority")
        if force_gate_fallback_ready_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep Matter CPU fallback ready")
        if force_gate_rollback_policy_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not report Matter CPU rollback policy")
        if force_gate_force_authority_false_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep forceAuthorityReady=false")
        if force_gate_runtime_authority_false_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep runtimeForceAuthority=false")
        if force_gate_runtime_particle_false_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not keep runtimeParticleIntegration=false"
            )
        if force_gate_gpu_not_ready_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep gpuComputeReady=false")
        if force_gate_low_rate_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep highRateJsonPayload=false")
        if force_gate_settings_payload_false_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not keep settingsControlPayload=false"
            )
    force_freshness_lines = lines_containing(
        proof_lines, "RUSTY_HOSTESS_MAKEPAD_GPU_FORCE_FRESHNESS"
    )
    force_freshness_ready_count = count_lines_containing(
        force_freshness_lines, "freshnessReady=true"
    )
    force_freshness_not_ready_count = count_lines_containing(
        force_freshness_lines, "freshnessReady=false"
    )
    force_freshness_source_match_count = count_lines_containing(
        force_freshness_lines, "sourceIdMatched=true"
    )
    force_freshness_candidate_not_future_count = count_lines_containing(
        force_freshness_lines, "candidateNotFuture=true"
    )
    force_freshness_cadence_ready_count = count_lines_containing(
        force_freshness_lines, "cadenceReady=true"
    )
    force_freshness_runtime_authority_false_count = count_lines_containing(
        force_freshness_lines, "runtimeForceAuthority=false"
    )
    force_freshness_gpu_not_ready_count = count_lines_containing(
        force_freshness_lines, "gpuComputeReady=false"
    )
    force_freshness_low_rate_count = count_lines_containing(
        force_freshness_lines, "highRateJsonPayload=false"
    )
    force_freshness_settings_payload_false_count = count_lines_containing(
        force_freshness_lines, "settingsControlPayload=false"
    )
    force_freshness_lag_values = marker_int_fields(force_freshness_lines, "sourceFrameLag")
    force_freshness_max_lag_values = marker_int_fields(
        force_freshness_lines, "maxSourceFrameLag"
    )
    force_freshness_max_lag_observed = max(force_freshness_lag_values, default=0)
    force_freshness_max_lag_allowed = max(force_freshness_max_lag_values, default=0)
    if force_freshness_lines:
        if force_freshness_runtime_authority_false_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep runtimeForceAuthority=false")
        if force_freshness_gpu_not_ready_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep gpuComputeReady=false")
        if force_freshness_low_rate_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep highRateJsonPayload=false")
        if force_freshness_settings_payload_false_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep settingsControlPayload=false")
        if force_freshness_source_match_count + count_lines_containing(
            force_freshness_lines, "sourceIdMatched=false"
        ) != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not declare sourceIdMatched")
        if force_freshness_candidate_not_future_count + count_lines_containing(
            force_freshness_lines, "candidateNotFuture=false"
        ) != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not declare candidateNotFuture")
        if not force_freshness_max_lag_values:
            issues.append("GPU force freshness evidence did not declare maxSourceFrameLag")
    force_residency_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY"
    )
    force_residency_candidate_ready_count = count_lines_containing(
        force_residency_lines, "forceAuthorityCandidateReady=true"
    )
    force_residency_gpu_candidate_ready_count = count_lines_containing(
        force_residency_lines, "gpuComputeCandidateReady=true"
    )
    force_residency_single_authority_count = count_lines_containing(
        force_residency_lines, "singleActiveForceAuthorityPreserved=true"
    )
    force_residency_slot_count = count_lines_containing(
        force_residency_lines, "forceAuthoritySlotCount=1"
    )
    force_residency_active_count = count_lines_containing(
        force_residency_lines, "activeForceAuthorityCount=1"
    )
    force_residency_profile_required_count = count_lines_containing(
        force_residency_lines, "profileGate=explicit-profile-required"
    )
    force_residency_profile_declared_count = count_lines_containing(
        force_residency_lines, "profileGateSatisfied="
    )
    force_residency_selection_blocked_count = count_lines_containing(
        force_residency_lines, "runtimeSelectionPermitted=false"
    )
    force_residency_active_kind_count = count_lines_containing(
        force_residency_lines, "activeForceAuthorityKind=matter-cpu"
    )
    force_residency_active_source_count = count_lines_containing(
        force_residency_lines, "activeForceAuthoritySource=matter-runtime-profile"
    )
    force_residency_oracle_authority_count = count_lines_containing(
        force_residency_lines, "matterCpuOracleForceAuthority="
    )
    force_residency_active_preserved_count = count_lines_containing(
        force_residency_lines, "activeForceAuthorityPreserved=matter-cpu-runtime"
    )
    force_residency_not_selected_count = count_lines_containing(
        force_residency_lines, "candidateSelected=false"
    )
    force_residency_not_promoted_count = count_lines_containing(
        force_residency_lines, "candidatePromoted=false"
    )
    force_residency_tracker_source_count = count_lines_containing(
        force_residency_lines,
        "residencyTrackerSource=quest-makepad-gpu-force-authority-residency-tracker",
    )
    force_residency_reused_proofs_declared_count = count_lines_containing(
        force_residency_lines, "reusedResidentProofs="
    )
    force_residency_continuity_declared_count = count_lines_containing(
        force_residency_lines, "residencyContinuityReady="
    )
    force_residency_continuity_not_broken_count = count_lines_containing(
        force_residency_lines, "residencyContinuityBroken=false"
    )
    force_residency_continuity_breaks_declared_count = count_lines_containing(
        force_residency_lines, "residencyContinuityBreakCount="
    )
    force_residency_source_generation_declared_count = count_lines_containing(
        force_residency_lines, "sourceMeshBufferGeneration="
    )
    force_residency_source_generation_matched_count = count_lines_containing(
        force_residency_lines, "sourceMeshBufferGenerationMatched=true"
    )
    force_residency_derived_generation_declared_count = count_lines_containing(
        force_residency_lines, "derivedBufferGeneration="
    )
    force_residency_derived_generation_matched_count = count_lines_containing(
        force_residency_lines, "derivedBufferGenerationMatched=true"
    )
    force_residency_queue_monotonic_count = count_lines_containing(
        force_residency_lines, "queueSubmitSerialMonotonic=true"
    )
    force_residency_fence_monotonic_count = count_lines_containing(
        force_residency_lines, "fenceSerialMonotonic=true"
    )
    force_residency_fallback_ready_count = count_lines_containing(
        force_residency_lines, "matterCpuFallbackReady=true"
    )
    force_residency_fallback_authority_count = count_lines_containing(
        force_residency_lines, "fallbackForceAuthority="
    )
    force_residency_fallback_reason_count = count_lines_containing(
        force_residency_lines, "fallbackReason="
    )
    force_residency_rollback_policy_count = count_lines_containing(
        force_residency_lines,
        "rollbackPolicy=matter-cpu-oracle-on-gpu-freshness-or-cadence-failure",
    )
    force_residency_source_resident_count = count_lines_containing(
        force_residency_lines, "sourceMeshBuffersResident=true"
    )
    force_residency_source_reuse_declared_count = count_lines_containing(
        force_residency_lines, "sourceMeshBuffersReused="
    )
    force_residency_source_reuse_count = count_lines_containing(
        force_residency_lines, "sourceMeshBuffersReused=true"
    )
    force_residency_derived_resident_count = count_lines_containing(
        force_residency_lines, "derivedBuffersResident=true"
    )
    force_residency_derived_reuse_declared_count = count_lines_containing(
        force_residency_lines, "derivedBuffersReused="
    )
    force_residency_derived_reuse_count = count_lines_containing(
        force_residency_lines, "derivedBuffersReused=true"
    )
    force_residency_bounded_only_count = count_lines_containing(
        force_residency_lines, "boundedProofOnly=true"
    )
    force_residency_bounded_declared_count = count_lines_containing(
        force_residency_lines, "boundedProofOnly="
    )
    force_residency_steady_state_declared_count = count_lines_containing(
        force_residency_lines, "steadyStateResidencyReady="
    )
    force_residency_steady_state_false_count = count_lines_containing(
        force_residency_lines, "steadyStateResidencyReady=false"
    )
    force_residency_steady_state_true_count = count_lines_containing(
        force_residency_lines, "steadyStateResidencyReady=true"
    )
    force_residency_freshness_declared_count = count_lines_containing(
        force_residency_lines, "freshnessReady="
    )
    force_residency_freshness_false_count = count_lines_containing(
        force_residency_lines, "freshnessReady=false"
    )
    force_residency_freshness_true_count = count_lines_containing(
        force_residency_lines, "freshnessReady=true"
    )
    force_residency_cadence_declared_count = count_lines_containing(
        force_residency_lines, "cadenceReady="
    )
    force_residency_cadence_false_count = count_lines_containing(
        force_residency_lines, "cadenceReady=false"
    )
    force_residency_cadence_true_count = count_lines_containing(
        force_residency_lines, "cadenceReady=true"
    )
    force_residency_expanded_oracle_declared_count = count_lines_containing(
        force_residency_lines, "expandedOracleComparisonReady="
    )
    force_residency_expanded_oracle_false_count = count_lines_containing(
        force_residency_lines, "expandedOracleComparisonReady=false"
    )
    force_residency_expanded_oracle_true_count = count_lines_containing(
        force_residency_lines, "expandedOracleComparisonReady=true"
    )
    force_residency_provider_ab_declared_count = count_lines_containing(
        force_residency_lines, "liveRecordedProviderAbReady="
    )
    force_residency_provider_ab_false_count = count_lines_containing(
        force_residency_lines, "liveRecordedProviderAbReady=false"
    )
    force_residency_provider_ab_true_count = count_lines_containing(
        force_residency_lines, "liveRecordedProviderAbReady=true"
    )
    force_residency_force_authority_false_count = count_lines_containing(
        force_residency_lines, "forceAuthorityReady=false"
    )
    force_residency_runtime_authority_false_count = count_lines_containing(
        force_residency_lines, "runtimeForceAuthority=false"
    )
    force_residency_runtime_particle_false_count = count_lines_containing(
        force_residency_lines, "runtimeParticleIntegration=false"
    )
    force_residency_gpu_not_ready_count = count_lines_containing(
        force_residency_lines, "gpuComputeReady=false"
    )
    force_residency_low_rate_count = count_lines_containing(
        force_residency_lines, "highRateJsonPayload=false"
    )
    force_residency_settings_payload_false_count = count_lines_containing(
        force_residency_lines, "settingsControlPayload=false"
    )
    force_residency_observed_proof_values = marker_int_fields(
        force_residency_lines, "observedResidentProofs"
    )
    force_residency_reused_proof_values = marker_int_fields(
        force_residency_lines, "reusedResidentProofs"
    )
    force_residency_required_proof_values = marker_int_fields(
        force_residency_lines, "requiredResidentProofs"
    )
    force_residency_max_observed_proofs = max(
        force_residency_observed_proof_values, default=0
    )
    force_residency_max_reused_proofs = max(
        force_residency_reused_proof_values, default=0
    )
    force_residency_max_required_proofs = max(
        force_residency_required_proof_values, default=0
    )
    force_residency_freshness_fallback_count = count_lines_containing(
        force_residency_lines, "fallbackReason=gpu-freshness-not-proven"
    )
    force_residency_expanded_oracle_fallback_count = count_lines_containing(
        force_residency_lines,
        "fallbackReason=gpu-expanded-oracle-comparison-not-proven",
    )
    force_residency_provider_ab_fallback_count = count_lines_containing(
        force_residency_lines,
        "fallbackReason=gpu-live-recorded-provider-ab-not-proven",
    )
    if force_residency_lines:
        if force_residency_candidate_ready_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not keep forceAuthorityCandidateReady=true"
            )
        if force_residency_gpu_candidate_ready_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not keep gpuComputeCandidateReady=true"
            )
        if force_residency_single_authority_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not preserve single authority")
        if force_residency_slot_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report forceAuthoritySlotCount=1"
            )
        if force_residency_active_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report activeForceAuthorityCount=1"
            )
        if force_residency_profile_required_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not require explicit profile selection"
            )
        if force_residency_profile_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare profileGateSatisfied")
        if force_residency_selection_blocked_count != len(force_residency_lines):
            issues.append("GPU force authority residency permitted runtime selection")
        if force_residency_active_kind_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep Matter CPU active kind")
        if force_residency_active_source_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare the active authority source"
            )
        if force_residency_oracle_authority_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare the Matter CPU oracle authority"
            )
        if force_residency_active_preserved_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not preserve Matter CPU as active authority"
            )
        if force_residency_not_selected_count != len(force_residency_lines):
            issues.append("GPU force authority residency selected the candidate")
        if force_residency_not_promoted_count != len(force_residency_lines):
            issues.append("GPU force authority residency promoted the candidate")
        if force_residency_tracker_source_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report the residency tracker source"
            )
        if force_residency_reused_proofs_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare reusedResidentProofs")
        if force_residency_continuity_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare residency continuity readiness"
            )
        if force_residency_continuity_not_broken_count != len(force_residency_lines):
            issues.append("GPU force authority residency reported a continuity break")
        if force_residency_continuity_breaks_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare continuity break count"
            )
        if force_residency_source_generation_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare source mesh buffer generation"
            )
        if force_residency_source_generation_matched_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not match source mesh buffer generation"
            )
        if force_residency_derived_generation_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare derived buffer generation"
            )
        if force_residency_derived_generation_matched_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not match derived buffer generation"
            )
        if force_residency_queue_monotonic_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep submit serials monotonic")
        if force_residency_fence_monotonic_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep fence serials monotonic")
        if force_residency_fallback_ready_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep Matter CPU fallback ready")
        if force_residency_fallback_authority_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare fallback authority")
        if force_residency_fallback_reason_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare fallback reason")
        if force_residency_rollback_policy_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not report Matter CPU rollback policy")
        if force_residency_source_resident_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report resident source mesh buffers"
            )
        if force_residency_source_reuse_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare source buffer reuse")
        if force_residency_derived_resident_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report resident derived buffers"
            )
        if force_residency_derived_reuse_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare derived buffer reuse")
        if force_residency_bounded_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare boundedProofOnly")
        if force_residency_steady_state_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare steady-state readiness"
            )
        if force_residency_freshness_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare freshness readiness")
        if force_residency_cadence_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare cadence readiness")
        if force_residency_expanded_oracle_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare expanded oracle comparison readiness"
            )
        if force_residency_provider_ab_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare live/recorded A/B readiness"
            )
        if force_residency_force_authority_false_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep forceAuthorityReady=false")
        if force_residency_runtime_authority_false_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep runtimeForceAuthority=false")
        if force_residency_runtime_particle_false_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not keep runtimeParticleIntegration=false"
            )
        if force_residency_gpu_not_ready_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep gpuComputeReady=false")
        if force_residency_low_rate_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep highRateJsonPayload=false")
        if force_residency_settings_payload_false_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not keep settingsControlPayload=false"
            )
    if thresholds.require_gpu_force_profile_enabled:
        if not force_gate_lines:
            issues.append("GPU force profile was required but no force-authority gate was present")
        elif force_gate_profile_satisfied_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not satisfy the explicit GPU profile gate"
            )
        if not force_residency_lines:
            issues.append(
                "GPU force profile was required but no force-authority residency marker was present"
            )
        elif (
            force_residency_profile_declared_count != len(force_residency_lines)
            or count_lines_containing(force_residency_lines, "profileGateSatisfied=true")
            != len(force_residency_lines)
            or count_lines_containing(
                force_residency_lines, "gpuForceAuthorityProfileEnabled=true"
            )
            != len(force_residency_lines)
        ):
            issues.append(
                "GPU force authority residency did not satisfy the explicit GPU profile gate"
            )
    if thresholds.min_force_residency_observed_proofs > 0:
        if force_residency_max_observed_proofs < thresholds.min_force_residency_observed_proofs:
            issues.append(
                "GPU force authority residency observedResidentProofs max "
                f"{force_residency_max_observed_proofs} < "
                f"{thresholds.min_force_residency_observed_proofs}"
            )
    if thresholds.min_force_residency_reused_proofs > 0:
        if force_residency_max_reused_proofs < thresholds.min_force_residency_reused_proofs:
            issues.append(
                "GPU force authority residency reusedResidentProofs max "
                f"{force_residency_max_reused_proofs} < "
                f"{thresholds.min_force_residency_reused_proofs}"
            )
    if thresholds.require_gpu_force_steady_state_fallback:
        if not force_residency_lines:
            issues.append(
                "steady-state GPU force fallback was required but no residency marker was present"
            )
        if force_residency_steady_state_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach steadyStateResidencyReady=true"
            )
        if force_residency_cadence_true_count < 1:
            issues.append("GPU force authority residency did not reach cadenceReady=true")
        if force_residency_freshness_true_count != 0:
            issues.append("GPU force authority residency claimed freshnessReady=true too early")
        if force_residency_expanded_oracle_true_count != 0:
            issues.append(
                "GPU force authority residency claimed expandedOracleComparisonReady=true too early"
            )
        if force_residency_provider_ab_true_count != 0:
            issues.append(
                "GPU force authority residency claimed liveRecordedProviderAbReady=true too early"
            )
        if force_residency_freshness_fallback_count < 1:
            issues.append(
                "GPU force authority residency did not fall back for gpu-freshness-not-proven"
            )
        if force_residency_selection_blocked_count != len(force_residency_lines):
            issues.append("GPU force authority steady-state fallback permitted runtime selection")
        if force_residency_active_kind_count != len(force_residency_lines):
            issues.append("GPU force authority steady-state fallback did not keep Matter CPU active")
    if thresholds.require_gpu_force_freshness:
        if not force_freshness_lines:
            issues.append("GPU force freshness was required but no freshness marker was present")
        if force_freshness_ready_count < 1:
            issues.append("GPU force freshness evidence did not reach freshnessReady=true")
        if force_freshness_not_ready_count != 0:
            issues.append("GPU force freshness evidence still contained freshnessReady=false")
        if force_freshness_source_match_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep sourceIdMatched=true")
        if force_freshness_candidate_not_future_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep candidateNotFuture=true")
        if force_freshness_cadence_ready_count < 1:
            issues.append("GPU force freshness evidence did not show cadenceReady=true")
        if len(force_freshness_lag_values) != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not declare numeric sourceFrameLag")
        if len(force_freshness_max_lag_values) != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not declare maxSourceFrameLag")
        if (
            force_freshness_lag_values
            and force_freshness_max_lag_values
            and force_freshness_max_lag_observed > force_freshness_max_lag_allowed
        ):
            issues.append(
                "GPU force freshness sourceFrameLag max "
                f"{force_freshness_max_lag_observed} > allowed "
                f"{force_freshness_max_lag_allowed}"
            )
        if force_residency_freshness_true_count < 1:
            issues.append("GPU force authority residency did not consume freshnessReady=true")
    if thresholds.require_gpu_force_fresh_expanded_oracle_fallback:
        if not force_residency_lines:
            issues.append(
                "fresh GPU force fallback was required but no residency marker was present"
            )
        if force_residency_steady_state_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach steadyStateResidencyReady=true"
            )
        if force_residency_freshness_true_count < 1:
            issues.append("GPU force authority residency did not reach freshnessReady=true")
        if force_residency_cadence_true_count < 1:
            issues.append("GPU force authority residency did not reach cadenceReady=true")
        if force_residency_expanded_oracle_true_count != 0:
            issues.append(
                "GPU force authority residency claimed expandedOracleComparisonReady=true too early"
            )
        if force_residency_provider_ab_true_count != 0:
            issues.append(
                "GPU force authority residency claimed liveRecordedProviderAbReady=true too early"
            )
        if force_residency_expanded_oracle_fallback_count < 1:
            issues.append(
                "GPU force authority residency did not fall back for "
                "gpu-expanded-oracle-comparison-not-proven"
            )
        if force_residency_selection_blocked_count != len(force_residency_lines):
            issues.append("GPU force authority fresh fallback permitted runtime selection")
        if force_residency_active_kind_count != len(force_residency_lines):
            issues.append("GPU force authority fresh fallback did not keep Matter CPU active")
    if thresholds.require_gpu_force_expanded_oracle_provider_ab_fallback:
        if not field_particle_force_lines:
            issues.append(
                "expanded GPU force oracle fallback was required but no particle-force "
                "proof marker was present"
            )
        if field_particle_force_max_sample_count < EXPANDED_FORCE_ORACLE_SAMPLE_COUNT:
            issues.append(
                "GPU field particle-force proof max sampleCount "
                f"{field_particle_force_max_sample_count} < "
                f"{EXPANDED_FORCE_ORACLE_SAMPLE_COUNT}"
            )
        if not force_residency_lines:
            issues.append(
                "expanded GPU force oracle fallback was required but no residency marker was present"
            )
        if force_residency_steady_state_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach steadyStateResidencyReady=true"
            )
        if force_residency_freshness_true_count < 1:
            issues.append("GPU force authority residency did not reach freshnessReady=true")
        if force_residency_cadence_true_count < 1:
            issues.append("GPU force authority residency did not reach cadenceReady=true")
        if force_residency_expanded_oracle_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach expandedOracleComparisonReady=true"
            )
        if force_residency_provider_ab_true_count != 0:
            issues.append(
                "GPU force authority residency claimed liveRecordedProviderAbReady=true too early"
            )
        if force_residency_provider_ab_fallback_count < 1:
            issues.append(
                "GPU force authority residency did not fall back for "
                "gpu-live-recorded-provider-ab-not-proven"
            )
        if force_residency_selection_blocked_count != len(force_residency_lines):
            issues.append("GPU force expanded oracle fallback permitted runtime selection")
        if force_residency_active_kind_count != len(force_residency_lines):
            issues.append(
                "GPU force expanded oracle fallback did not keep Matter CPU active"
            )
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
        "gpu_proof_epoch_line_count": len(gpu_proof_epoch_lines),
        "gpu_proof_epoch_reset_count": gpu_proof_epoch_reset_count,
        "gpu_proof_epoch_no_runtime_reload_count": (
            gpu_proof_epoch_no_runtime_reload_count
        ),
        "gpu_proof_epoch_no_replay_rebuild_count": (
            gpu_proof_epoch_no_replay_rebuild_count
        ),
        "gpu_proof_epoch_no_worker_restart_count": (
            gpu_proof_epoch_no_worker_restart_count
        ),
        "gpu_proof_epoch_low_rate_count": gpu_proof_epoch_low_rate_count,
        "field_construction_line_count": len(field_construction_lines),
        "field_construction_ready_count": field_construction_ready_count,
        "field_construction_force_authority_false_count": (
            field_construction_force_authority_false_count
        ),
        "field_construction_runtime_authority_false_count": (
            field_construction_runtime_authority_false_count
        ),
        "field_construction_gpu_not_ready_count": field_construction_gpu_not_ready_count,
        "field_construction_low_rate_count": field_construction_low_rate_count,
        "field_sampling_line_count": len(field_sampling_lines),
        "field_sampling_ready_count": field_sampling_ready_count,
        "field_sampling_field_ready_count": field_sampling_field_ready_count,
        "field_sampling_resident_count": field_sampling_resident_count,
        "field_sampling_generation_match_count": field_sampling_generation_match_count,
        "field_sampling_kernel_count": field_sampling_kernel_count,
        "field_sampling_force_authority_false_count": field_sampling_force_authority_false_count,
        "field_sampling_runtime_authority_false_count": field_sampling_runtime_authority_false_count,
        "field_sampling_gpu_not_ready_count": field_sampling_gpu_not_ready_count,
        "field_sampling_low_rate_count": field_sampling_low_rate_count,
        "field_force_sampling_line_count": len(field_force_sampling_lines),
        "field_force_sampling_ready_count": field_force_sampling_ready_count,
        "field_force_sampling_field_ready_count": field_force_sampling_field_ready_count,
        "field_force_sampling_resident_count": field_force_sampling_resident_count,
        "field_force_sampling_generation_match_count": (
            field_force_sampling_generation_match_count
        ),
        "field_force_sampling_kernel_count": field_force_sampling_kernel_count,
        "field_force_sampling_particle_kernel_false_count": (
            field_force_sampling_particle_kernel_false_count
        ),
        "field_force_sampling_runtime_particle_false_count": (
            field_force_sampling_runtime_particle_false_count
        ),
        "field_force_sampling_force_authority_false_count": (
            field_force_sampling_force_authority_false_count
        ),
        "field_force_sampling_runtime_authority_false_count": (
            field_force_sampling_runtime_authority_false_count
        ),
        "field_force_sampling_gpu_not_ready_count": field_force_sampling_gpu_not_ready_count,
        "field_force_sampling_low_rate_count": field_force_sampling_low_rate_count,
        "field_particle_force_line_count": len(field_particle_force_lines),
        "field_particle_force_ready_count": field_particle_force_ready_count,
        "field_particle_force_field_ready_count": field_particle_force_field_ready_count,
        "field_particle_force_resident_count": field_particle_force_resident_count,
        "field_particle_force_generation_match_count": (
            field_particle_force_generation_match_count
        ),
        "field_particle_force_kernel_count": field_particle_force_kernel_count,
        "field_particle_force_force_kernel_count": field_particle_force_force_kernel_count,
        "field_particle_force_sample_source_count": field_particle_force_sample_source_count,
        "field_particle_force_matter_equation_count": field_particle_force_matter_equation_count,
        "field_particle_force_runtime_particle_false_count": (
            field_particle_force_runtime_particle_false_count
        ),
        "field_particle_force_force_authority_false_count": (
            field_particle_force_force_authority_false_count
        ),
        "field_particle_force_runtime_authority_false_count": (
            field_particle_force_runtime_authority_false_count
        ),
        "field_particle_force_gpu_not_ready_count": field_particle_force_gpu_not_ready_count,
        "field_particle_force_low_rate_count": field_particle_force_low_rate_count,
        "field_particle_force_max_sample_count": field_particle_force_max_sample_count,
        "field_particle_force_max_requested_sample_count": (
            field_particle_force_max_requested_sample_count
        ),
        "field_particle_force_max_sampled_particle_count": (
            field_particle_force_max_sampled_particle_count
        ),
        "force_candidate_line_count": len(force_candidate_lines),
        "force_candidate_ready_count": force_candidate_ready_count,
        "force_candidate_gpu_ready_count": force_candidate_gpu_ready_count,
        "force_candidate_single_authority_count": force_candidate_single_authority_count,
        "force_candidate_not_selected_count": force_candidate_not_selected_count,
        "force_candidate_not_promoted_count": force_candidate_not_promoted_count,
        "force_candidate_active_unchanged_count": force_candidate_active_unchanged_count,
        "force_candidate_force_authority_false_count": (
            force_candidate_force_authority_false_count
        ),
        "force_candidate_runtime_authority_false_count": (
            force_candidate_runtime_authority_false_count
        ),
        "force_candidate_runtime_particle_false_count": (
            force_candidate_runtime_particle_false_count
        ),
        "force_candidate_gpu_not_ready_count": force_candidate_gpu_not_ready_count,
        "force_candidate_low_rate_count": force_candidate_low_rate_count,
        "force_candidate_settings_payload_false_count": (
            force_candidate_settings_payload_false_count
        ),
        "force_gate_line_count": len(force_gate_lines),
        "force_gate_candidate_ready_count": force_gate_candidate_ready_count,
        "force_gate_gpu_candidate_ready_count": force_gate_gpu_candidate_ready_count,
        "force_gate_single_authority_count": force_gate_single_authority_count,
        "force_gate_slot_count": force_gate_slot_count,
        "force_gate_active_count": force_gate_active_count,
        "force_gate_profile_required_count": force_gate_profile_required_count,
        "force_gate_profile_declared_count": force_gate_profile_declared_count,
        "force_gate_profile_satisfied_count": force_gate_profile_satisfied_count,
        "force_gate_profile_unsatisfied_count": force_gate_profile_unsatisfied_count,
        "force_gate_selection_blocked_count": force_gate_selection_blocked_count,
        "force_gate_profile_known_count": force_gate_profile_known_count,
        "force_gate_profile_state_declared_count": force_gate_profile_state_declared_count,
        "force_gate_profile_enabled_count": force_gate_profile_enabled_count,
        "force_gate_profile_disabled_count": force_gate_profile_disabled_count,
        "force_gate_active_kind_count": force_gate_active_kind_count,
        "force_gate_candidate_eligible_count": force_gate_candidate_eligible_count,
        "force_gate_not_selected_count": force_gate_not_selected_count,
        "force_gate_not_promoted_count": force_gate_not_promoted_count,
        "force_gate_active_unchanged_count": force_gate_active_unchanged_count,
        "force_gate_fallback_ready_count": force_gate_fallback_ready_count,
        "force_gate_rollback_policy_count": force_gate_rollback_policy_count,
        "force_gate_force_authority_false_count": force_gate_force_authority_false_count,
        "force_gate_runtime_authority_false_count": (
            force_gate_runtime_authority_false_count
        ),
        "force_gate_runtime_particle_false_count": force_gate_runtime_particle_false_count,
        "force_gate_gpu_not_ready_count": force_gate_gpu_not_ready_count,
        "force_gate_low_rate_count": force_gate_low_rate_count,
        "force_gate_settings_payload_false_count": (
            force_gate_settings_payload_false_count
        ),
        "force_freshness_line_count": len(force_freshness_lines),
        "force_freshness_ready_count": force_freshness_ready_count,
        "force_freshness_not_ready_count": force_freshness_not_ready_count,
        "force_freshness_source_match_count": force_freshness_source_match_count,
        "force_freshness_candidate_not_future_count": (
            force_freshness_candidate_not_future_count
        ),
        "force_freshness_cadence_ready_count": force_freshness_cadence_ready_count,
        "force_freshness_runtime_authority_false_count": (
            force_freshness_runtime_authority_false_count
        ),
        "force_freshness_gpu_not_ready_count": force_freshness_gpu_not_ready_count,
        "force_freshness_low_rate_count": force_freshness_low_rate_count,
        "force_freshness_settings_payload_false_count": (
            force_freshness_settings_payload_false_count
        ),
        "force_freshness_max_lag_observed": force_freshness_max_lag_observed,
        "force_freshness_max_lag_allowed": force_freshness_max_lag_allowed,
        "force_residency_line_count": len(force_residency_lines),
        "force_residency_candidate_ready_count": force_residency_candidate_ready_count,
        "force_residency_gpu_candidate_ready_count": (
            force_residency_gpu_candidate_ready_count
        ),
        "force_residency_single_authority_count": force_residency_single_authority_count,
        "force_residency_slot_count": force_residency_slot_count,
        "force_residency_active_count": force_residency_active_count,
        "force_residency_profile_required_count": force_residency_profile_required_count,
        "force_residency_profile_declared_count": force_residency_profile_declared_count,
        "force_residency_selection_blocked_count": force_residency_selection_blocked_count,
        "force_residency_active_kind_count": force_residency_active_kind_count,
        "force_residency_active_source_count": force_residency_active_source_count,
        "force_residency_oracle_authority_count": force_residency_oracle_authority_count,
        "force_residency_active_preserved_count": force_residency_active_preserved_count,
        "force_residency_not_selected_count": force_residency_not_selected_count,
        "force_residency_not_promoted_count": force_residency_not_promoted_count,
        "force_residency_fallback_ready_count": force_residency_fallback_ready_count,
        "force_residency_fallback_authority_count": force_residency_fallback_authority_count,
        "force_residency_fallback_reason_count": force_residency_fallback_reason_count,
        "force_residency_rollback_policy_count": force_residency_rollback_policy_count,
        "force_residency_source_resident_count": force_residency_source_resident_count,
        "force_residency_source_reuse_declared_count": (
            force_residency_source_reuse_declared_count
        ),
        "force_residency_source_reuse_count": force_residency_source_reuse_count,
        "force_residency_derived_resident_count": force_residency_derived_resident_count,
        "force_residency_derived_reuse_declared_count": (
            force_residency_derived_reuse_declared_count
        ),
        "force_residency_derived_reuse_count": force_residency_derived_reuse_count,
        "force_residency_bounded_only_count": force_residency_bounded_only_count,
        "force_residency_bounded_declared_count": (
            force_residency_bounded_declared_count
        ),
        "force_residency_steady_state_declared_count": (
            force_residency_steady_state_declared_count
        ),
        "force_residency_steady_state_false_count": (
            force_residency_steady_state_false_count
        ),
        "force_residency_steady_state_true_count": force_residency_steady_state_true_count,
        "force_residency_freshness_declared_count": (
            force_residency_freshness_declared_count
        ),
        "force_residency_freshness_false_count": force_residency_freshness_false_count,
        "force_residency_freshness_true_count": force_residency_freshness_true_count,
        "force_residency_cadence_declared_count": force_residency_cadence_declared_count,
        "force_residency_cadence_false_count": force_residency_cadence_false_count,
        "force_residency_cadence_true_count": force_residency_cadence_true_count,
        "force_residency_expanded_oracle_declared_count": (
            force_residency_expanded_oracle_declared_count
        ),
        "force_residency_expanded_oracle_false_count": (
            force_residency_expanded_oracle_false_count
        ),
        "force_residency_expanded_oracle_true_count": (
            force_residency_expanded_oracle_true_count
        ),
        "force_residency_provider_ab_declared_count": (
            force_residency_provider_ab_declared_count
        ),
        "force_residency_provider_ab_false_count": force_residency_provider_ab_false_count,
        "force_residency_provider_ab_true_count": force_residency_provider_ab_true_count,
        "force_residency_force_authority_false_count": (
            force_residency_force_authority_false_count
        ),
        "force_residency_runtime_authority_false_count": (
            force_residency_runtime_authority_false_count
        ),
        "force_residency_runtime_particle_false_count": (
            force_residency_runtime_particle_false_count
        ),
        "force_residency_gpu_not_ready_count": force_residency_gpu_not_ready_count,
        "force_residency_low_rate_count": force_residency_low_rate_count,
        "force_residency_settings_payload_false_count": (
            force_residency_settings_payload_false_count
        ),
        "force_residency_max_observed_proofs": force_residency_max_observed_proofs,
        "force_residency_max_reused_proofs": force_residency_max_reused_proofs,
        "force_residency_max_required_proofs": force_residency_max_required_proofs,
        "force_residency_freshness_fallback_count": (
            force_residency_freshness_fallback_count
        ),
        "force_residency_expanded_oracle_fallback_count": (
            force_residency_expanded_oracle_fallback_count
        ),
        "force_residency_provider_ab_fallback_count": (
            force_residency_provider_ab_fallback_count
        ),
        "required_marker_counts": {
            key: int(numeric(markers.get(key))) for key in required_markers
        },
        "stage_marker_counts": {
            key: int(numeric(markers.get(key))) for key in OPTIONAL_STAGE_MARKERS
        },
        "optional_marker_counts": {
            key: int(numeric(markers.get(key))) for key in OPTIONAL_MARKERS
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
    return [str(line) for line in lines if line_has_marker(str(line), token)]


def line_has_marker(line: str, marker: str) -> bool:
    pattern = re.compile(rf"(^|:\s+){re.escape(marker)}\b")
    return bool(pattern.search(line))


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
    parser.add_argument(
        "--require-gpu-proof-epoch",
        action="store_true",
        help=(
            "Require a Hostess GPU proof epoch marker proving proof counter reset "
            "without runtime/settings replay rebuild."
        ),
    )
    parser.add_argument(
        "--require-gpu-field-force-sampling",
        action="store_true",
        help=(
            "Require the optional GPU dense-SDF force-sampling proof marker. "
            "Use this only for the force-sampling stage, not the mesh-SDF "
            "construction stage."
        ),
    )
    parser.add_argument(
        "--require-gpu-field-particle-force",
        action="store_true",
        help=(
            "Require the optional GPU particle-force comparison proof marker. "
            "Use this only for the particle-force stage, not the mesh-SDF "
            "construction stage."
        ),
    )
    parser.add_argument(
        "--require-gpu-force-freshness",
        action="store_true",
        help=(
            "Require Hostess GPU force freshness evidence proving a completed "
            "GPU force proof matches a recently adopted Matter source frame."
        ),
    )
    parser.add_argument(
        "--require-gpu-force-authority-candidate",
        action="store_true",
        help=(
            "Require the optional non-authoritative GPU force-authority candidate "
            "marker. Use this only after the bounded particle-force stage proves "
            "candidate readiness without promotion."
        ),
    )
    parser.add_argument(
        "--require-gpu-force-authority-gate",
        action="store_true",
        help=(
            "Require the optional GPU force-authority profile gate marker proving "
            "the candidate stayed blocked behind explicit profile selection."
        ),
    )
    parser.add_argument(
        "--require-gpu-force-authority-residency",
        action="store_true",
        help=(
            "Require the optional GPU force-authority residency-health marker proving "
            "runtime selection stayed blocked until steady-state residency, freshness, "
            "cadence, expanded oracle comparison, and live/recorded provider A/B evidence exist."
        ),
    )
    parser.add_argument(
        "--require-gpu-force-profile-enabled",
        action="store_true",
        help=(
            "Require force-authority gate and residency markers to show the explicit "
            "gpu-dense-sdf-field-particle-force profile gate was requested."
        ),
    )
    parser.add_argument(
        "--require-gpu-force-steady-state-fallback",
        action="store_true",
        help=(
            "Require the residency marker to reach steady-state/cadence readiness "
            "while still falling back to the Matter CPU oracle because freshness, "
            "expanded oracle comparison, and live/recorded A/B are not proven."
        ),
    )
    parser.add_argument(
        "--require-gpu-force-fresh-expanded-oracle-fallback",
        action="store_true",
        help=(
            "Require steady-state, cadence, and freshness readiness while still "
            "falling back to Matter CPU because expanded oracle comparison and "
            "live/recorded A/B are not proven."
        ),
    )
    parser.add_argument(
        "--require-gpu-force-expanded-oracle-provider-ab-fallback",
        action="store_true",
        help=(
            "Require steady-state, cadence, freshness, and expanded 16-sample "
            "CPU-oracle comparison readiness while still falling back to Matter CPU "
            "because live/recorded provider A/B is not proven."
        ),
    )
    parser.add_argument(
        "--min-field-particle-force-sample-count",
        type=int,
        default=0,
        help="Require GPU field particle-force proof max sampleCount to be at least this value.",
    )
    parser.add_argument(
        "--min-force-residency-observed-proofs",
        type=int,
        default=0,
        help="Require the residency marker's max observedResidentProofs to be at least this value.",
    )
    parser.add_argument(
        "--min-force-residency-reused-proofs",
        type=int,
        default=0,
        help="Require the residency marker's max reusedResidentProofs to be at least this value.",
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
        require_gpu_proof_epoch=args.require_gpu_proof_epoch,
        require_gpu_field_force_sampling=args.require_gpu_field_force_sampling,
        require_gpu_field_particle_force=args.require_gpu_field_particle_force,
        require_gpu_force_freshness=args.require_gpu_force_freshness,
        require_gpu_force_authority_candidate=args.require_gpu_force_authority_candidate,
        require_gpu_force_authority_gate=args.require_gpu_force_authority_gate,
        require_gpu_force_authority_residency=args.require_gpu_force_authority_residency,
        require_gpu_force_profile_enabled=args.require_gpu_force_profile_enabled,
        require_gpu_force_steady_state_fallback=args.require_gpu_force_steady_state_fallback,
        require_gpu_force_fresh_expanded_oracle_fallback=(
            args.require_gpu_force_fresh_expanded_oracle_fallback
        ),
        require_gpu_force_expanded_oracle_provider_ab_fallback=(
            args.require_gpu_force_expanded_oracle_provider_ab_fallback
        ),
        min_field_particle_force_sample_count=args.min_field_particle_force_sample_count,
        min_force_residency_observed_proofs=args.min_force_residency_observed_proofs,
        min_force_residency_reused_proofs=args.min_force_residency_reused_proofs,
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
