"""Shared Projected Motion Breath evidence support helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from tools.check_live_capture_evidence import sha256_file

PMB_STREAM_CONTRACT_AUTHORITY = "rusty-manifold-packages.projected-motion-breath"
PMB_BREATH_VOLUME_STREAM = "stream.breath.volume"
PMB_BREATH_VOLUME_SELECTED_STREAM = "stream.breath.volume.selected"
PMB_BREATH_VOLUME_POLAR_STREAM = "stream.breath.volume.polar"
PMB_BREATH_VOLUME_CONTROLLER_STREAM = "stream.breath.volume.controller"
PMB_BREATH_SELECTION_STATE_STREAM = "stream.breath.selection_state"
PMB_BREATH_STATE_STREAM = "stream.breath.state"
PMB_BREATH_STATE_VALUE_STREAM = "stream.breath.state.value"
PMB_BREATH_FEEDBACK_STATE_STREAM = "stream.breath.feedback_state"
PMB_BREATH_FEEDBACK_RECEIPT_STREAM = "stream.breath.feedback_receipt"

# PMB fixed-controller state mirrors the legacy Unity 24/180-sample spans
# against the current 72 Hz headset profile, then transports them as seconds.
PMB_CONTROLLER_STATE_SAMPLE_RATE_HZ = 72.0
PMB_CONTROLLER_STATE_SHORT_WINDOW_SAMPLES = 24.0
PMB_CONTROLLER_STATE_LONG_WINDOW_SAMPLES = 180.0
PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS = (
    PMB_CONTROLLER_STATE_SHORT_WINDOW_SAMPLES / PMB_CONTROLLER_STATE_SAMPLE_RATE_HZ
)
PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS = (
    PMB_CONTROLLER_STATE_LONG_WINDOW_SAMPLES / PMB_CONTROLLER_STATE_SAMPLE_RATE_HZ
)
PMB_CONTROLLER_STATE_INHALE_THRESHOLD = 0.001
PMB_CONTROLLER_STATE_EXHALE_THRESHOLD = -0.00057
PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES = 0.5
PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD = 0.025


def projected_motion_package_snapshot(package_root: Path) -> dict[str, Any]:
    manifest = package_root / "manifests" / "package.manifold.json"
    return {
        "package_id": "package.projected_motion_breath",
        "package_manifest_sha256": sha256_file(manifest),
        "stream_manifest_sha256": sha256_manifest_children(package_root / "manifests" / "streams"),
        "module_manifest_sha256": sha256_manifest_children(package_root / "manifests" / "modules"),
        "command_manifest_sha256": sha256_manifest_children(package_root / "manifests" / "commands"),
    }


def sha256_manifest_children(directory: Path) -> dict[str, str]:
    if not directory.exists():
        return {}
    return {
        path.stem: sha256_file(path)
        for path in sorted(directory.glob("*.json"))
    }


def pmb_checked_counts(core_report: dict[str, Any] | None) -> dict[str, int]:
    names = [
        "checked_profiles",
        "checked_command_payloads",
        "checked_damaged_command_payloads",
        "checked_source_bindings",
        "checked_damaged_source_bindings",
        "checked_adapter_normalization_cases",
        "checked_damaged_adapter_normalization_cases",
        "checked_cases",
        "checked_damaged_cases",
    ]
    return {name: int(core_report.get(name, 0)) if core_report else 0 for name in names}


def pmb_scorecard_check(
    check_id: str,
    passed: bool,
    evidence: str,
    issue_code: str = "validation.pmb_desktop_replay_failed",
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
        "issue_codes": [] if passed else [issue_code],
    }


def scorecard_check(check_id: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
        "issue_codes": [] if passed else ["validation.live_capture_failed"],
    }


def stream_segment(stream_ids: list[str]) -> str:
    if not stream_ids:
        return "unknown"
    return stream_ids[0].split(".")[-1].replace("-", "_")


def module_segment(module_ids: list[str]) -> str:
    if not module_ids:
        return "unknown"
    pieces = [module_id.split(".")[-1].replace("-", "_") for module_id in module_ids]
    joined = "_".join(pieces)
    return joined[:80]


def host_app_for(host_profile: str) -> str:
    if host_profile == "desktop":
        return "app.rusty_hostess_t.desktop"
    if host_profile == "headset":
        return "app.rusty_hostess_t.quest"
    return "app.rusty_hostess_t.android"


def iso_to_epoch_ms(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.replace("Z", "+00:00")
    return int(datetime.fromisoformat(normalized).timestamp() * 1000)
