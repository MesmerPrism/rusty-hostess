"""Summarize raw Hostess Makepad Quest GPU proof evidence.

The raw evidence root is owned by Hostess: logcat, device-state snapshots, and
metadata stay outside the repo. This tool turns that evidence into the compact
summary consumed by ``check_makepad_quest_gpu_evidence.py`` and also writes
small readiness/strict-scan sidecars when a headset run never reaches XR proof
markers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from check_makepad_quest_gpu_evidence import OPTIONAL_MARKERS, REQUIRED_MARKERS
except ImportError:  # pragma: no cover - direct script fallback
    REQUIRED_MARKERS = {
        "proof_schedule": "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_SCHEDULE",
        "gpu_skinning_probe": "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE",
        "gpu_skinning_mesh_residency": "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_MESH_RESIDENCY",
        "gpu_mesh_sdf_probe": "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE",
        "gpu_field_construction": "RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION",
        "gpu_field_sampling_probe": "RUSTY_QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE",
        "gpu_field_force_sampling_probe": (
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE"
        ),
        "gpu_field_particle_force_probe": (
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE"
        ),
        "gpu_force_freshness": "RUSTY_HOSTESS_MAKEPAD_GPU_FORCE_FRESHNESS",
        "gpu_force_authority_candidate": (
            "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_CANDIDATE"
        ),
        "gpu_force_authority_gate": (
            "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_GATE"
        ),
        "gpu_force_authority_residency": (
            "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY"
        ),
    }
    OPTIONAL_MARKERS = {
        "gpu_proof_epoch": "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_EPOCH",
    }


SUMMARY_SCHEMA = "rusty.hostess.quest_live_hand_small_profile_summary.v1"
STRICT_SCAN_SCHEMA = "rusty.hostess.quest_log_strict_scan.v1"
MESH_SDF_CHECK_SCHEMA = "rusty.hostess.makepad.mesh_sdf_source_buffer_reuse_check.v1"
READINESS_SCHEMA = "rusty.hostess.quest_gpu_evidence_readiness_summary.v1"

HOSTESS_TAG = "HostessMakepad"
CADENCE_MARKER = "RUSTY_MAKEPAD_CADENCE"
SOURCE_SELECTION_MARKER = "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_SOURCE_SELECTION"
RECORDED_WORKER_MARKER = "RUSTY_HOSTESS_MAKEPAD_RECORDED_HAND_SURFACE_WORKER_SOURCE"
LIVE_SOURCE_MARKER = "RUSTY_HOSTESS_MAKEPAD_LIVE_HAND_SURFACE_SOURCE"
LIVE_WORKER_MARKER = "RUSTY_HOSTESS_MAKEPAD_LIVE_HAND_SURFACE_WORKER_SOURCE"
GPU_RESIDENCY_MARKER = "RUSTY_QUEST_MAKEPAD_GPU_RESIDENCY"
GPU_MESH_SDF_MARKER = "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE"
GPU_FIELD_CONSTRUCTION_MARKER = "RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION"
GPU_FIELD_SAMPLING_MARKER = "RUSTY_QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE"
GPU_FIELD_FORCE_SAMPLING_MARKER = "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE"
GPU_FIELD_PARTICLE_FORCE_MARKER = "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE"
GPU_FORCE_FRESHNESS_MARKER = "RUSTY_HOSTESS_MAKEPAD_GPU_FORCE_FRESHNESS"
GPU_FORCE_AUTHORITY_CANDIDATE_MARKER = "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_CANDIDATE"
GPU_FORCE_AUTHORITY_GATE_MARKER = "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_GATE"
GPU_FORCE_AUTHORITY_RESIDENCY_MARKER = "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY"
GPU_PROOF_EPOCH_MARKER = "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_EPOCH"
PROOF_MARKERS = {**REQUIRED_MARKERS, **OPTIONAL_MARKERS}

LOGCAT_RE = re.compile(
    r"^(?P<date>\d\d-\d\d)\s+"
    r"(?P<time>\d\d:\d\d:\d\d\.\d{3})\s+"
    r"(?P<pid>\d+)\s+"
    r"(?P<tid>\d+)\s+"
    r"(?P<level>[A-Z])\s+"
    r"(?P<tag>[^:]+?)\s*:\s*"
    r"(?P<message>.*)$"
)
LOGCAT_COMPACT_RE = re.compile(
    r"^(?P<date>\d\d-\d\d)\s+"
    r"(?P<time>\d\d:\d\d:\d\d\.\d{3})\s+"
    r"(?P<level>[A-Z])/"
    r"(?P<tag>[^(:]+?)\s*"
    r"\(\s*(?P<pid>\d+)\):\s*"
    r"(?P<message>.*)$"
)
FIELD_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")
STALE_RE = re.compile(r"\bStale=(?P<stale>-?\d+(?:\.\d+)?)\b")


@dataclass(frozen=True)
class LogEntry:
    line: str
    pid: int | None
    tid: int | None
    level: str
    tag: str
    message: str


def parse_log_entry(line: str) -> LogEntry:
    match = LOGCAT_RE.match(line)
    if not match:
        compact_match = LOGCAT_COMPACT_RE.match(line)
        if compact_match:
            return LogEntry(
                line=line,
                pid=int(compact_match.group("pid")),
                tid=None,
                level=compact_match.group("level"),
                tag=compact_match.group("tag").strip(),
                message=compact_match.group("message"),
            )
    if not match:
        return LogEntry(line=line, pid=None, tid=None, level="", tag="", message=line)
    return LogEntry(
        line=line,
        pid=int(match.group("pid")),
        tid=int(match.group("tid")),
        level=match.group("level"),
        tag=match.group("tag").strip(),
        message=match.group("message"),
    )


def parse_fields(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2) for match in FIELD_RE.finditer(text)}


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def int_fields(lines: list[str], field_name: str) -> list[int]:
    pattern = re.compile(rf"\b{re.escape(field_name)}=(\d+)\b")
    values: list[int] = []
    for line in lines:
        values.extend(int(match.group(1)) for match in pattern.finditer(line))
    return values


def unique_field_values(lines: list[str], field_name: str) -> list[str]:
    pattern = re.compile(rf"\b{re.escape(field_name)}=([^\s]+)")
    values = {
        match.group(1)
        for line in lines
        for match in pattern.finditer(line)
    }
    return sorted(values)


def stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min": 0.0, "max": 0.0, "avg": 0.0}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
    }


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def select_hostess_pid(entries: list[LogEntry]) -> int | None:
    pids = Counter(
        entry.pid
        for entry in entries
        if entry.pid is not None and entry.tag == HOSTESS_TAG
    )
    if not pids:
        return None
    return pids.most_common(1)[0][0]


def filter_hostess_lines(entries: list[LogEntry], app_pid: int | None) -> list[str]:
    lines: list[str] = []
    for entry in entries:
        if entry.tag != HOSTESS_TAG:
            continue
        if app_pid is not None and entry.pid != app_pid:
            continue
        lines.append(entry.line)
    return lines


def filter_hostess_messages(entries: list[LogEntry], app_pid: int | None) -> list[str]:
    messages: list[str] = []
    for entry in entries:
        if entry.tag != HOSTESS_TAG:
            continue
        if app_pid is not None and entry.pid != app_pid:
            continue
        messages.append(entry.message)
    return messages


def marker_lines(lines: list[str], marker: str) -> list[str]:
    return [line for line in lines if line_has_marker(line, marker)]


def line_has_marker(line: str, marker: str) -> bool:
    pattern = re.compile(rf"(^|:\s+){re.escape(marker)}\b")
    return bool(pattern.search(line))


def cadence_summary(messages: list[str]) -> dict[str, dict[str, float | int]]:
    cadence_fields = {
        "app_frame_rate_hz": "appFrameRateHz",
        "xr_update_rate_hz": "xrUpdateRateHz",
        "xr_effective_frame_rate_hz": "xrEffectiveFrameRateHz",
        "xr_repaint_gpu_ms": "xrRepaintGpuMs",
        "xr_update_dispatch_ms": "xrUpdateDispatchMs",
    }
    values: dict[str, list[float]] = {key: [] for key in cadence_fields}
    for message in messages:
        if CADENCE_MARKER not in message or "phase=sample" not in message:
            continue
        fields = parse_fields(message)
        for output_key, marker_key in cadence_fields.items():
            parsed = number(fields.get(marker_key))
            if parsed is not None:
                values[output_key].append(parsed)
    return {key: stats(field_values) for key, field_values in values.items()}


def recorded_hand_source_summary(lines: list[str], max_sample_lines: int) -> dict[str, Any]:
    source_lines = marker_lines(lines, RECORDED_WORKER_MARKER)
    return {
        "line_count": len(source_lines),
        "ready_line_count": sum("status=ready" in line for line in source_lines),
        "compact_worker_ready_line_count": sum(
            "compactFrameWorkerSubmit=true" in line and "status=ready" in line
            for line in source_lines
        ),
        "gpu_oracle_requested_line_count": sum(
            "gpuOraclePayloadsRequested=true" in line for line in source_lines
        ),
        "sample_lines": source_lines[:max_sample_lines],
    }


def live_hand_source_summary(lines: list[str], max_sample_lines: int) -> dict[str, Any]:
    source_lines = marker_lines(lines, LIVE_SOURCE_MARKER)
    return {
        "line_count": len(source_lines),
        "ready_line_count": sum("status=ready" in line for line in source_lines),
        "error_line_count": sum("status=error" in line for line in source_lines),
        "provider_shape_ready_line_count": sum(
            "providerShape=bind-mesh-plus-compact-joint-frame" in line
            and "status=ready" in line
            for line in source_lines
        ),
        "recorded_equivalent_ready_line_count": sum(
            "recordedInputEquivalent=true" in line and "status=ready" in line
            for line in source_lines
        ),
        "sample_lines": source_lines[:max_sample_lines],
    }


def live_hand_worker_source_summary(
    lines: list[str], max_sample_lines: int
) -> dict[str, Any]:
    source_lines = marker_lines(lines, LIVE_WORKER_MARKER)
    return {
        "line_count": len(source_lines),
        "ready_line_count": sum("status=ready" in line for line in source_lines),
        "waiting_line_count": sum("status=waiting" in line for line in source_lines),
        "compact_worker_ready_line_count": sum(
            "compactFrameWorkerSubmit=true" in line and "status=ready" in line
            for line in source_lines
        ),
        "gpu_oracle_requested_line_count": sum(
            "gpuOraclePayloadsRequested=true" in line for line in source_lines
        ),
        "sample_lines": source_lines[:max_sample_lines],
    }


def vrapi_hostess_summary(
    entries: list[LogEntry], app_pid: int | None, max_sample_lines: int
) -> dict[str, Any]:
    stale_values: list[float] = []
    sample_lines: list[str] = []
    for entry in entries:
        if entry.tag != "VrApi":
            continue
        if app_pid is not None and entry.pid != app_pid:
            continue
        match = STALE_RE.search(entry.message)
        if not match:
            continue
        stale = float(match.group("stale"))
        stale_values.append(stale)
        if len(sample_lines) < max_sample_lines:
            sample_lines.append(entry.line)
    return {
        "pid": app_pid,
        "sample_lines": sample_lines,
        "stale": stats(stale_values),
        "stale_nonzero_count": sum(value > 0 for value in stale_values),
        "stale_30_plus_count": sum(value >= 30 for value in stale_values),
        "stale_90_plus_count": sum(value >= 90 for value in stale_values),
    }


def strict_log_scan(
    lines: list[str], app_pid: int | None = None, package: str | None = None
) -> dict[str, Any]:
    fatal_lines: list[str] = []
    camera_lines: list[str] = []
    for line in lines:
        lower = line.lower()
        if is_marker_telemetry(line):
            continue
        if (
            "fatal exception" in lower
            or "fatal signal" in lower
            or " anr in " in lower
            or "application not responding" in lower
            or "gpu fault" in lower
            or "device lost" in lower
            or "kgsl" in lower
        ):
            fatal_lines.append(line)
        if is_app_camera_permission_failure(line, app_pid, package):
            camera_lines.append(line)
    return {
        "schema": STRICT_SCAN_SCHEMA,
        "status": "ok" if not fatal_lines and not camera_lines else "failed",
        "fatal_anr_gpu_fault_line_count": len(fatal_lines),
        "camera_permission_failure_line_count": len(camera_lines),
        "ignored_marker_telemetry": (
            "kgslFaultsBeforeMarker/kgslFaultsAfterMarker fields are not counted "
            "as KGSL fault log lines"
        ),
        "fatal_anr_gpu_fault_lines": fatal_lines[:25],
        "camera_permission_failure_lines": camera_lines[:25],
    }


def is_marker_telemetry(line: str) -> bool:
    return (
        "HostessMakepad" in line
        and (
            "kgslFaultsBeforeMarker=" in line
            or "kgslFaultsAfterMarker=" in line
        )
    )


def is_app_camera_permission_failure(
    line: str, app_pid: int | None, package: str | None
) -> bool:
    lower = line.lower()
    if "camera" not in lower:
        return False
    if not (
        "permission" in lower
        or "denied" in lower
        or "securityexception" in lower
    ):
        return False
    if app_pid is None and not package:
        return True
    entry = parse_log_entry(line)
    if app_pid is not None and entry.pid == app_pid:
        return True
    if package and package.lower() in lower:
        return True
    if HOSTESS_TAG.lower() in lower:
        return True
    return False


def mesh_sdf_check(
    proof_lines: list[str],
    require_program_reuse: bool,
    require_source_buffer_reuse: bool,
    require_derived_buffer_reuse: bool,
    min_sample_count: int,
) -> dict[str, Any]:
    mesh_lines = marker_lines(proof_lines, GPU_MESH_SDF_MARKER)
    sample_counts = int_fields(mesh_lines, "sampleCount")
    issues: list[str] = []
    source_resident_count = sum("sourceMeshBuffersResident=true" in line for line in mesh_lines)
    source_reused_count = sum("sourceMeshBuffersReused=true" in line for line in mesh_lines)
    derived_resident_count = sum("derivedBuffersResident=true" in line for line in mesh_lines)
    derived_reused_count = sum("derivedBuffersReused=true" in line for line in mesh_lines)
    if require_program_reuse and not any("programReused=true" in line for line in mesh_lines):
        issues.append("mesh-SDF proof did not include programReused=true")
    if require_source_buffer_reuse and source_reused_count < 1:
        issues.append("mesh-SDF proof did not include sourceMeshBuffersReused=true")
    if require_derived_buffer_reuse and derived_reused_count < 1:
        issues.append("mesh-SDF proof did not include derivedBuffersReused=true")
    if min_sample_count > 0 and max(sample_counts, default=0) < min_sample_count:
        issues.append(
            f"mesh-SDF proof max sampleCount {max(sample_counts, default=0)} < {min_sample_count}"
        )
    return {
        "schema": MESH_SDF_CHECK_SCHEMA,
        "status": "ok" if not issues else "failed",
        "issues": issues,
        "mesh_sdf_line_count": len(mesh_lines),
        "source_mesh_buffers_resident_count": source_resident_count,
        "source_mesh_buffers_reused_count": source_reused_count,
        "derived_buffers_resident_count": derived_resident_count,
        "derived_buffers_reused_count": derived_reused_count,
        "source_vertex_buffer_bytes_values": unique_field_values(
            mesh_lines, "sourceVertexBufferBytes"
        ),
        "source_triangle_buffer_bytes_values": unique_field_values(
            mesh_lines, "sourceTriangleBufferBytes"
        ),
        "skinned_position_buffer_bytes_values": unique_field_values(
            mesh_lines, "skinnedPositionBufferBytes"
        ),
        "sdf_distance_buffer_bytes_values": unique_field_values(
            mesh_lines, "sdfDistanceBufferBytes"
        ),
        "mesh_sdf_sample_count_values": sample_counts,
        "mesh_sdf_min_sample_count": min(sample_counts, default=0),
        "mesh_sdf_max_sample_count": max(sample_counts, default=0),
        "mesh_sdf_lines": mesh_lines,
    }


def power_after_summary(evidence_root: Path) -> dict[str, Any]:
    power_text = read_text(evidence_root / "power-after.txt")
    mounted = read_text(evidence_root / "sys-hmt-mounted-after.txt").strip() or None
    wakefulness = regex_value(power_text, r"\bmWakefulness=([A-Za-z]+)")
    proximity = regex_value(power_text, r"\bmProximityPositive=(true|false)")
    return {
        "wakefulness": wakefulness,
        "wakefulness_asleep": wakefulness == "Asleep",
        "proximity_positive": (
            True if proximity == "true" else False if proximity == "false" else None
        ),
        "mounted": mounted,
    }


def regex_value(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def window_after_has_activity(evidence_root: Path, metadata: dict[str, Any]) -> bool:
    window_text = read_text(evidence_root / "window-after.txt")
    package = str(metadata.get("package", "")).strip()
    if package and package in window_text:
        return True
    return "rustyhostess.makepad" in window_text or "MakepadAppXr" in window_text


def readiness_summary(
    evidence_root: Path,
    metadata: dict[str, Any],
    markers: dict[str, int],
    extra_marker_counts: dict[str, int],
    log_text_length: int,
) -> dict[str, Any] | None:
    proof_count = sum(markers.values())
    gpu_count = (
        markers.get("gpu_skinning_probe", 0)
        + markers.get("gpu_skinning_mesh_residency", 0)
        + markers.get("gpu_mesh_sdf_probe", 0)
    )
    if proof_count > 0 or gpu_count > 0:
        return None

    power_after = power_after_summary(evidence_root)
    has_activity = window_after_has_activity(evidence_root, metadata)
    source_or_cadence = (
        extra_marker_counts.get("source_selection", 0) > 0
        or extra_marker_counts.get("cadence_start", 0) > 0
    )
    xr_not_ready = source_or_cadence and (
        power_after.get("wakefulness_asleep") is True
        or power_after.get("proximity_positive") is False
        or power_after.get("mounted") == "0"
    )
    status = "xr_not_ready" if xr_not_ready else "gpu_markers_missing"
    if xr_not_ready:
        classification = (
            "Quest app installed/launched and emitted startup markers, but the "
            "headset was asleep/off-face before XR frame cadence reached recorded "
            "worker-source or GPU proof markers."
        )
        next_action = (
            "Wake or mount the headset, then rerun the same evidence harness; "
            "recorded-hand replay does not require live hands."
        )
    else:
        classification = (
            "GPU proof markers were missing and device state did not classify the "
            "run as an off-face/asleep XR readiness failure."
        )
        next_action = "Inspect logcat and launch readiness before treating this as a GPU failure."
    return {
        "schema": READINESS_SCHEMA,
        "status": status,
        "evidence_root": str(evidence_root),
        "metadata": metadata,
        "marker_counts": {
            **extra_marker_counts,
            **markers,
        },
        "log_text_length": log_text_length,
        "power_after": power_after,
        "window_after_has_activity": has_activity,
        "classification": classification,
        "not_gpu_failure": xr_not_ready,
        "next_action": next_action,
    }


def summarize_evidence(
    evidence_root: Path,
    max_sample_lines: int,
    require_mesh_sdf_program_reuse: bool,
    require_source_buffer_reuse: bool,
    require_derived_buffer_reuse: bool,
    mesh_sdf_min_sample_count: int,
) -> dict[str, Any]:
    log_text = read_text(evidence_root / "logcat.txt")
    log_lines = log_text.splitlines()
    entries = [parse_log_entry(line) for line in log_lines]
    metadata = read_json(evidence_root / "metadata.json")
    app_pid = select_hostess_pid(entries)
    hostess_lines = filter_hostess_lines(entries, app_pid)
    hostess_messages = filter_hostess_messages(entries, app_pid)
    proof_lines = [
        line
        for line in hostess_lines
        if any(line_has_marker(line, marker) for marker in PROOF_MARKERS.values())
    ]
    markers = {
        key: len(marker_lines(proof_lines, marker))
        for key, marker in PROOF_MARKERS.items()
    }
    extra_counts = {
        "source_selection": len(marker_lines(hostess_lines, SOURCE_SELECTION_MARKER)),
        "cadence_start": sum(
            CADENCE_MARKER in line and "phase=start" in line for line in hostess_lines
        ),
        "recorded_worker_source": len(marker_lines(hostess_lines, RECORDED_WORKER_MARKER)),
        "live_source": len(marker_lines(hostess_lines, LIVE_SOURCE_MARKER)),
        "live_worker_source": len(marker_lines(hostess_lines, LIVE_WORKER_MARKER)),
        "gpu_residency": len(marker_lines(hostess_lines, GPU_RESIDENCY_MARKER)),
        "gpu_field_construction": len(
            marker_lines(hostess_lines, GPU_FIELD_CONSTRUCTION_MARKER)
        ),
        "gpu_field_sampling_probe": len(
            marker_lines(hostess_lines, GPU_FIELD_SAMPLING_MARKER)
        ),
        "gpu_field_force_sampling_probe": len(
            marker_lines(hostess_lines, GPU_FIELD_FORCE_SAMPLING_MARKER)
        ),
        "gpu_field_particle_force_probe": len(
            marker_lines(hostess_lines, GPU_FIELD_PARTICLE_FORCE_MARKER)
        ),
        "gpu_force_freshness": len(
            marker_lines(hostess_lines, GPU_FORCE_FRESHNESS_MARKER)
        ),
        "gpu_force_authority_candidate": len(
            marker_lines(hostess_lines, GPU_FORCE_AUTHORITY_CANDIDATE_MARKER)
        ),
        "gpu_force_authority_gate": len(
            marker_lines(hostess_lines, GPU_FORCE_AUTHORITY_GATE_MARKER)
        ),
        "gpu_force_authority_residency": len(
            marker_lines(hostess_lines, GPU_FORCE_AUTHORITY_RESIDENCY_MARKER)
        ),
        "gpu_proof_epoch": len(marker_lines(hostess_lines, GPU_PROOF_EPOCH_MARKER)),
        "sample_count_8": sum("sampleCount=8" in line for line in proof_lines),
    }
    summary = {
        "schema": SUMMARY_SCHEMA,
        "evidence_root": str(evidence_root),
        "app_pid": app_pid,
        "metadata": metadata,
        "markers": markers,
        "cadence": cadence_summary(hostess_messages),
        "recorded_hand_source": recorded_hand_source_summary(
            hostess_lines, max_sample_lines
        ),
        "live_hand_source": live_hand_source_summary(hostess_lines, max_sample_lines),
        "live_hand_worker_source": live_hand_worker_source_summary(
            hostess_lines, max_sample_lines
        ),
        "proof_lines": proof_lines,
        "vrapi_hostess_process": vrapi_hostess_summary(
            entries, app_pid, max_sample_lines
        ),
    }
    strict_scan = strict_log_scan(
        log_lines,
        app_pid=app_pid,
        package=str(metadata.get("package", "")).strip() or None,
    )
    mesh_check = mesh_sdf_check(
        proof_lines,
        require_mesh_sdf_program_reuse,
        require_source_buffer_reuse,
        require_derived_buffer_reuse,
        mesh_sdf_min_sample_count,
    )
    readiness = readiness_summary(
        evidence_root,
        metadata,
        markers,
        extra_counts,
        len(log_text),
    )
    return {
        "summary": summary,
        "strict_scan": strict_scan,
        "mesh_sdf_check": mesh_check,
        "readiness": readiness,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize a Hostess Makepad Quest GPU proof evidence root from raw "
            "logcat and device-state artifacts."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Evidence root containing logcat.txt and optional metadata/device-state files.",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        help="Summary JSON path. Defaults to <input>/live-hand-small-profile-summary.json.",
    )
    parser.add_argument(
        "--strict-scan-out",
        type=Path,
        help="Strict log scan path. Defaults to <input>/strict-log-scan.json.",
    )
    parser.add_argument(
        "--mesh-sdf-check-out",
        type=Path,
        help="Mesh-SDF source-buffer check path. Defaults to <input>/mesh-sdf-source-buffer-reuse-check.json.",
    )
    parser.add_argument(
        "--readiness-out",
        type=Path,
        help="Readiness summary path. Defaults to <input>/readiness-failure-summary.json when classified.",
    )
    parser.add_argument(
        "--require-mesh-sdf-program-reuse",
        action="store_true",
        help="Mark the mesh-SDF sidecar failed unless at least one proof line reused the program.",
    )
    parser.add_argument(
        "--require-source-buffer-reuse",
        action="store_true",
        help="Mark the mesh-SDF sidecar failed unless sourceMeshBuffersReused=true appears.",
    )
    parser.add_argument(
        "--require-derived-buffer-reuse",
        action="store_true",
        help="Mark the mesh-SDF sidecar failed unless derivedBuffersReused=true appears.",
    )
    parser.add_argument(
        "--require-mesh-sdf-min-sample-count",
        type=int,
        default=0,
        help="Mark the mesh-SDF sidecar failed unless a mesh-SDF sampleCount reaches this value.",
    )
    parser.add_argument(
        "--max-sample-lines",
        type=int,
        default=8,
        help="Maximum representative raw lines embedded in summary sidecars.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated payload map without writing sidecar files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    evidence_root = args.input.resolve()
    if not evidence_root.is_dir():
        raise FileNotFoundError(f"evidence root does not exist: {evidence_root}")
    if not (evidence_root / "logcat.txt").is_file():
        raise FileNotFoundError(f"logcat.txt not found under evidence root: {evidence_root}")

    payloads = summarize_evidence(
        evidence_root=evidence_root,
        max_sample_lines=max(0, args.max_sample_lines),
        require_mesh_sdf_program_reuse=args.require_mesh_sdf_program_reuse,
        require_source_buffer_reuse=args.require_source_buffer_reuse,
        require_derived_buffer_reuse=args.require_derived_buffer_reuse,
        mesh_sdf_min_sample_count=max(0, args.require_mesh_sdf_min_sample_count),
    )
    output_paths = {
        "summary": args.summary_out
        or evidence_root / "live-hand-small-profile-summary.json",
        "strict_scan": args.strict_scan_out
        or evidence_root / "strict-log-scan.json",
        "mesh_sdf_check": args.mesh_sdf_check_out
        or evidence_root / "mesh-sdf-source-buffer-reuse-check.json",
        "readiness": args.readiness_out
        or evidence_root / "readiness-failure-summary.json",
    }
    written: dict[str, str] = {}
    if not args.dry_run:
        write_json(output_paths["summary"], payloads["summary"])
        written["summary"] = str(output_paths["summary"])
        write_json(output_paths["strict_scan"], payloads["strict_scan"])
        written["strict_scan"] = str(output_paths["strict_scan"])
        write_json(output_paths["mesh_sdf_check"], payloads["mesh_sdf_check"])
        written["mesh_sdf_check"] = str(output_paths["mesh_sdf_check"])
        if payloads["readiness"] is not None:
            write_json(output_paths["readiness"], payloads["readiness"])
            written["readiness"] = str(output_paths["readiness"])
    result = {
        "schema": "rusty.hostess.makepad.quest_gpu_evidence_summary_run.v1",
        "status": "ok",
        "evidence_root": str(evidence_root),
        "written": written,
        "summary_marker_counts": payloads["summary"]["markers"],
        "strict_scan_status": payloads["strict_scan"]["status"],
        "mesh_sdf_check_status": payloads["mesh_sdf_check"]["status"],
        "readiness_status": (
            payloads["readiness"]["status"] if payloads["readiness"] else "not_needed"
        ),
    }
    if args.dry_run:
        result["payloads"] = payloads
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
