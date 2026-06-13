"""Shared Projected Motion Breath evidence support helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from tools.check_live_capture_evidence import sha256_file


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
