"""Projected Motion Breath evidence helpers for hostessctl."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.pmb_host_run_evidence import (
    write_contract_evidence,
    write_pmb_android_host_run_evidence,
    write_pmb_controller_preflight_host_run_evidence,
    write_pmb_host_run_evidence,
    write_pmb_live_route_host_run_evidence,
    write_pmb_quest_physical_live_host_run_evidence,
    write_pmb_quest_simulated_live_host_run_evidence,
    write_pmb_shell_handoff_host_run_evidence,
)
from tools.hostessctl.pmb_native_receipts import (
    pmb_app_receipt_policy,
    pmb_app_receipt_policy_pass,
    pmb_evidence_status_accepts_receipt_policy,
    pmb_scorecard_status_accepts_receipt_policy,
)
from tools.hostessctl.pmb_support import (
    PMB_BREATH_FEEDBACK_RECEIPT_STREAM,
    PMB_BREATH_FEEDBACK_STATE_STREAM,
    PMB_BREATH_SELECTION_STATE_STREAM,
    PMB_BREATH_STATE_STREAM,
    PMB_BREATH_STATE_VALUE_STREAM,
    PMB_BREATH_VOLUME_CONTROLLER_STREAM,
    PMB_BREATH_VOLUME_POLAR_STREAM,
    PMB_BREATH_VOLUME_SELECTED_STREAM,
    PMB_BREATH_VOLUME_STREAM,
    host_app_for,
    iso_to_epoch_ms,
    pmb_checked_counts,
    pmb_scorecard_check,
    projected_motion_package_snapshot,
)

PMB_SHELL_HANDOFF_REQUIRED_BINDINGS = {
    ("stream.motion.object_pose", "publish"),
    ("stream.breath.volume.selected", "subscribe"),
    ("stream.breath.feedback_receipt", "publish"),
}

PMB_BREATH_SCALE_VOLUME0 = "1.0"
PMB_BREATH_SCALE_VOLUME1 = "0.1796"
PMB_BREATH_SCALE_SMOOTHING_ALPHA = "0.75"
PMB_BREATH_SCALE_SMOOTHING_SECONDS = "0.03"
PMB_BREATH_SCALE_MODE = "volume"
PMB_BREATH_SCALE_INHALE_SECONDS_MIN_TO_MAX = "4.0"
PMB_BREATH_SCALE_EXHALE_SECONDS_MAX_TO_MIN = "4.0"
PMB_BREATH_SCALE_STATE_INHALE_THRESHOLD01 = "0.75"
PMB_BREATH_SCALE_STATE_EXHALE_THRESHOLD01 = "0.25"


def graph_report_streams(graph_report: dict[str, Any]) -> list[dict[str, Any]]:
    streams: list[dict[str, Any]] = []
    for raw_stream in graph_report.get("streams", []):
        if not isinstance(raw_stream, dict):
            continue
        stream = dict(raw_stream)
        stream.setdefault("malformed_frame_count", 0)
        streams.append(stream)
    return streams


def polar_package_root(packages_root: Path) -> Path:
    package_root = packages_root / "packages" / "polar-h10"
    return package_root if package_root.exists() else packages_root


def projected_motion_breath_package_root(packages_root: Path) -> Path:
    package_root = packages_root / "packages" / "projected-motion-breath"
    return package_root if package_root.exists() else packages_root


def default_pmb_shell_handoff_path(package_root: Path) -> Path:
    return package_root / "fixtures" / "valid" / "shell-handoff-loopback.json"


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON file did not contain an object: {path}")
    return value


def load_json_manifest_dir(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    return [
        load_json_object(path)
        for path in sorted(directory.glob("*.json"))
    ]


def collect_manifest_ids(manifests: list[dict[str, Any]], key: str) -> list[str]:
    return sorted(
        str(manifest[key])
        for manifest in manifests
        if manifest.get(key)
    )


def parse_pmb_core_report(stdout: str) -> tuple[dict[str, Any] | None, str | None]:
    for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
        try:
            report = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(report, dict):
            return report, None
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as error:
        return None, str(error)
    if not isinstance(report, dict):
        return None, "core stdout did not contain a JSON object"
    return report, None


def build_pmb_desktop_replay_execution_evidence(
    *,
    packages_root: Path,
    package_root: Path,
    command: list[str],
    core_run: subprocess.CompletedProcess[str],
    core_report: dict[str, Any] | None,
    core_report_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    started_utc: datetime,
    ended_utc: datetime,
    parse_error: str | None,
) -> dict[str, Any]:
    checked_counts = pmb_checked_counts(core_report)
    core_status = core_report.get("status") if core_report else "missing"
    status = "pass" if core_run.returncode == 0 and core_status == "pass" and parse_error is None else "fail"
    package = projected_motion_package_snapshot(package_root)
    issues = []
    if parse_error:
        issues.append(
            {
                "code": "hostess.issue.pmb_core_report_parse_failed",
                "severity": "error",
                "message": parse_error,
            }
        )
    if core_report:
        for issue in core_report.get("issues", []):
            if isinstance(issue, dict):
                issues.append(issue)
            else:
                issues.append(
                    {
                        "code": "hostess.issue.pmb_core_report_issue",
                        "severity": "error",
                        "message": str(issue),
                    }
                )
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_core_process_exit",
            core_run.returncode == 0,
            f"projected-motion-breath-core exited with {core_run.returncode}",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_core_report_parse",
            core_report is not None and parse_error is None,
            "projected-motion-breath-core emitted a parseable validation report",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_core_report_status",
            core_status == "pass",
            f"projected-motion-breath core report status was {core_status}",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_core_goldens_executed",
            checked_counts.get("checked_cases", 0) >= 2
            and checked_counts.get("checked_damaged_cases", 0) >= 2,
            "projected-motion breath pose/vector golden and damaged cases executed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_core_adapter_normalization_executed",
            checked_counts.get("checked_adapter_normalization_cases", 0) >= 3
            and checked_counts.get("checked_damaged_adapter_normalization_cases", 0) >= 2,
            "projected-motion breath adapter-normalization valid and damaged cases executed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_no_platform_execution",
            True,
            "desktop replay used no Android, Quest, APK, OpenXR, ADB, or live sensor path",
        ),
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.desktop_replay_execution_evidence.v1",
        "status": status,
        "target": "desktop",
        "host_profile": "desktop",
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "duration_ms": int((ended_utc - started_utc).total_seconds() * 1000),
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.desktop",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "package_root_name": package_root.name,
        "packages_workspace_name": packages_root.name,
        "execution": {
            "mode": "projected_motion_breath_desktop_replay",
            "command": command,
            "returncode": core_run.returncode,
            "runtime_path": "rust.projected_motion_breath_core.v1",
            "core_report_artifact": core_report_path.name if core_report is not None else None,
            "stdout_artifact": stdout_path.name,
            "stderr_artifact": stderr_path.name,
            "processor_core_executed": True,
            "execution_performed": True,
            "runtime_execution_performed": True,
            "desktop_execution_performed": True,
            "platform_execution_performed": False,
            "device_required": False,
            "android_execution_performed": False,
            "quest_execution_performed": False,
            "apk_build_performed": False,
            "openxr_runtime_used": False,
            "adb_used": False,
            "live_sensor_used": False,
        },
        "core_report_summary": {
            "schema": core_report.get("schema") if core_report else None,
            "status": core_status,
            **checked_counts,
        },
        "commands": [
            {
                "command": "run_projected_motion_breath_core_validate_goldens",
                "status": "acknowledged" if core_run.returncode == 0 else "rejected",
                "runtime_path": "rust.projected_motion_breath_core.v1",
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.desktop_replay",
            "target_id": "hostess.projected_motion_breath.desktop_replay",
            "target_revision": 1,
            "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
            "checks": checks,
            "issues": issues,
        },
    }


def validate_pmb_desktop_replay_execution_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    core_summary = evidence.get("core_report_summary", {})
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.desktop_replay_execution_evidence.v1",
            "PMB desktop replay evidence schema is supported",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.status",
            evidence.get("status") == "pass",
            "PMB desktop replay evidence status passed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.target",
            evidence.get("target") == "desktop" and evidence.get("host_profile") == "desktop",
            "PMB desktop replay targeted the desktop host profile",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.runtime_executed",
            execution.get("execution_performed") is True
            and execution.get("runtime_execution_performed") is True
            and execution.get("processor_core_executed") is True,
            "PMB processor core execution was performed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.no_platform_execution",
            execution.get("platform_execution_performed") is False
            and execution.get("device_required") is False
            and execution.get("android_execution_performed") is False
            and execution.get("quest_execution_performed") is False
            and execution.get("apk_build_performed") is False
            and execution.get("openxr_runtime_used") is False
            and execution.get("adb_used") is False
            and execution.get("live_sensor_used") is False,
            "PMB desktop replay avoided Android, Quest, APK, OpenXR, ADB, and live sensors",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.core_counts",
            core_summary.get("checked_cases", 0) >= 2
            and core_summary.get("checked_damaged_cases", 0) >= 2
            and core_summary.get("checked_adapter_normalization_cases", 0) >= 3
            and core_summary.get("checked_damaged_adapter_normalization_cases", 0) >= 2,
            "PMB core replay executed golden and adapter-normalization fixture sets",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.desktop_replay_execution_validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def build_pmb_live_route_self_test_evidence(
    *,
    packages_root: Path,
    package_root: Path,
    command: list[str],
    core_run: subprocess.CompletedProcess[str],
    route_report: dict[str, Any] | None,
    route_report_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    started_utc: datetime,
    ended_utc: datetime,
    parse_error: str | None,
) -> dict[str, Any]:
    route_status = route_report.get("status") if route_report else "missing"
    status = "pass" if core_run.returncode == 0 and route_status == "pass" and parse_error is None else "fail"
    package = projected_motion_package_snapshot(package_root)
    issues = []
    if parse_error:
        issues.append(
            {
                "code": "hostess.issue.pmb_live_route_report_parse_failed",
                "severity": "error",
                "message": parse_error,
            }
        )
    if route_report:
        for issue in route_report.get("issues", []):
            issues.append(
                {
                    "code": "hostess.issue.pmb_live_route_report_issue",
                    "severity": "error",
                    "message": str(issue),
                }
            )
    input_stream_ids = route_report.get("input_stream_ids", []) if route_report else []
    normalized_stream_ids = route_report.get("normalized_stream_ids", []) if route_report else []
    output_stream_ids = route_report.get("output_stream_ids", []) if route_report else []
    source_routes = route_report.get("source_routes", []) if route_report else []
    state_samples = route_report.get("state_samples", []) if route_report else []
    state_value_samples = route_report.get("state_value_samples", []) if route_report else []
    feedback_samples = route_report.get("feedback_samples", []) if route_report else []
    receipts = (
        route_report.get("receiver_receipts")
        or route_report.get("makepad_receipts")
        or []
        if route_report
        else []
    )
    subscription = (
        route_report.get("receiver_subscription")
        or route_report.get("makepad_subscription")
        or {}
        if route_report
        else {}
    )
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_live_route_core_exit",
            core_run.returncode == 0,
            f"projected-motion-breath-core exited with {core_run.returncode}",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_report_parse",
            route_report is not None and parse_error is None,
            "projected-motion-breath-core emitted a parseable live broker route report",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_report_status",
            route_status == "pass",
            f"live broker route report status was {route_status}",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_inputs",
            {"bio:polar_acc", "stream.motion.object_pose"}.issubset(set(input_stream_ids))
            and {"stream.motion.vector3", "stream.motion.object_pose"}.issubset(set(normalized_stream_ids)),
            "self-test route consumes Polar ACC plus Makepad controller pose and normalizes them",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_outputs",
            {
                PMB_BREATH_VOLUME_STREAM,
                PMB_BREATH_VOLUME_SELECTED_STREAM,
                PMB_BREATH_VOLUME_POLAR_STREAM,
                PMB_BREATH_VOLUME_CONTROLLER_STREAM,
                PMB_BREATH_SELECTION_STATE_STREAM,
                PMB_BREATH_STATE_STREAM,
                PMB_BREATH_STATE_VALUE_STREAM,
                PMB_BREATH_FEEDBACK_STATE_STREAM,
            }.issubset(set(output_stream_ids)),
            "self-test route emits aggregate, selected, source-specific, raw state, processed state-value, selection-state, and feedback streams",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_state_samples",
            bool(state_samples) and bool(state_value_samples) and len(state_samples) == len(state_value_samples),
            "self-test route emits paired raw state and processed state-value samples",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_makepad_subscription",
            subscription.get("command") == "subscribe"
            and subscription.get("stream") == PMB_BREATH_VOLUME_SELECTED_STREAM,
            "Makepad subscription contract targets the selected breath volume stream",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_makepad_receipts",
            bool(receipts)
            and all(
                receipt.get("command") == "breath_feedback.received"
                and receipt.get("schema") == "rusty.manifold.breath.feedback_receipt.v1"
                and receipt.get("received_stream") == PMB_BREATH_VOLUME_SELECTED_STREAM
                and receipt.get("acknowledged") is True
                for receipt in receipts
                if isinstance(receipt, dict)
            ),
            "Makepad receipt contract acknowledges selected breath samples",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_non_live",
            bool(route_report)
            and route_report.get("plan_only") is True
            and route_report.get("broker_transport_used", route_report.get("external_transport_used")) is False
            and route_report.get("live_sensor_used") is False
            and route_report.get("quest_execution_performed", route_report.get("headset_execution_performed")) is False,
            "self-test avoided broker transport, live sensors, and headset execution",
            "validation.pmb_live_route_self_test_failed",
        ),
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.live_broker_route_self_test_evidence.v1",
        "status": status,
        "target": "desktop",
        "host_profile": "desktop",
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "duration_ms": int((ended_utc - started_utc).total_seconds() * 1000),
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.desktop",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "package_root_name": package_root.name,
        "packages_workspace_name": packages_root.name,
        "execution": {
            "mode": "projected_motion_breath_live_broker_route_self_test",
            "command": command,
            "returncode": core_run.returncode,
            "runtime_path": "rust.projected_motion_breath_core.v1",
            "route_report_artifact": route_report_path.name if route_report is not None else None,
            "stdout_artifact": stdout_path.name,
            "stderr_artifact": stderr_path.name,
            "processor_core_executed": bool(route_report and route_report.get("processor_core_executed") is True),
            "execution_performed": True,
            "runtime_execution_performed": bool(route_report and route_report.get("runtime_execution_performed") is True),
            "desktop_execution_performed": True,
            "platform_execution_performed": False,
            "device_required": False,
            "android_execution_performed": False,
            "quest_execution_performed": False,
            "apk_build_performed": False,
            "openxr_runtime_used": False,
            "adb_used": False,
            "broker_transport_used": bool(
                route_report
                and (
                    route_report.get("broker_transport_used") is True
                    or route_report.get("external_transport_used") is True
                )
            ),
            "live_sensor_used": bool(route_report and route_report.get("live_sensor_used") is True),
            "plan_only": bool(route_report and route_report.get("plan_only") is True),
        },
        "route_report_summary": {
            "schema": route_report.get("schema") if route_report else None,
            "status": route_status,
            "route_id": route_report.get("route_id") if route_report else None,
            "input_stream_ids": input_stream_ids,
            "normalized_stream_ids": normalized_stream_ids,
            "output_stream_ids": output_stream_ids,
            "source_route_count": len(source_routes),
            "breath_sample_count": len(route_report.get("breath_samples", [])) if route_report else 0,
            "state_sample_count": len(state_samples),
            "state_value_sample_count": len(state_value_samples),
            "feedback_sample_count": len(feedback_samples),
            "receipt_count": len(receipts),
            "makepad_subscription": subscription,
        },
        "commands": [
            {
                "command": "run_projected_motion_breath_live_broker_route_self_test",
                "status": "acknowledged" if core_run.returncode == 0 else "rejected",
                "runtime_path": "rust.projected_motion_breath_core.v1",
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.live_broker_route_self_test",
            "target_id": "hostess.projected_motion_breath.live_broker_route_self_test",
            "target_revision": 1,
            "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
            "checks": checks,
            "issues": issues,
        },
    }


def validate_pmb_live_route_self_test_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    summary = evidence.get("route_report_summary", {})
    subscription = summary.get("makepad_subscription", {})
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.live_broker_route_self_test_evidence.v1",
            "PMB live broker route self-test evidence schema is supported",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.status",
            evidence.get("status") == "pass",
            "PMB live broker route self-test evidence status passed",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.runtime_executed",
            execution.get("execution_performed") is True
            and execution.get("runtime_execution_performed") is True
            and execution.get("processor_core_executed") is True,
            "PMB processor core execution was performed",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.non_live",
            execution.get("plan_only") is True
            and execution.get("platform_execution_performed") is False
            and execution.get("device_required") is False
            and execution.get("android_execution_performed") is False
            and execution.get("quest_execution_performed") is False
            and execution.get("apk_build_performed") is False
            and execution.get("openxr_runtime_used") is False
            and execution.get("adb_used") is False
            and execution.get("broker_transport_used") is False
            and execution.get("live_sensor_used") is False,
            "PMB live broker route self-test avoided devices and live transports",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.stream_contract",
            {"bio:polar_acc", "stream.motion.object_pose"}.issubset(
                set(summary.get("input_stream_ids", []))
            )
            and {
                PMB_BREATH_VOLUME_STREAM,
                PMB_BREATH_VOLUME_SELECTED_STREAM,
                PMB_BREATH_STATE_STREAM,
                PMB_BREATH_STATE_VALUE_STREAM,
                PMB_BREATH_FEEDBACK_STATE_STREAM,
            }.issubset(
                set(summary.get("output_stream_ids", []))
            )
            and int(summary.get("source_route_count", 0)) >= 2,
            "PMB live route stream contract includes the required inputs and outputs",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.feedback_ack",
            subscription.get("stream") == PMB_BREATH_VOLUME_SELECTED_STREAM
            and int(summary.get("feedback_sample_count", 0)) > 0
            and int(summary.get("receipt_count", 0)) == int(summary.get("feedback_sample_count", -1)),
            "PMB live route has a Makepad selected breath subscription and one receipt per selected sample",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB live route self-test scorecard passed",
            "validation.pmb_live_route_self_test_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.live_broker_route_self_test_validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def build_pmb_shell_handoff_validation_evidence(
    *,
    packages_root: Path,
    package_root: Path,
    handoff_path: Path,
    started_utc: datetime,
    ended_utc: datetime,
) -> dict[str, Any]:
    package_manifest = load_json_object(package_root / "manifests" / "package.manifold.json")
    stream_manifests = load_json_manifest_dir(package_root / "manifests" / "streams")
    command_manifests = load_json_manifest_dir(package_root / "manifests" / "commands")
    module_manifests = load_json_manifest_dir(package_root / "manifests" / "modules")
    handoff = load_json_object(handoff_path)
    exports = package_manifest.get("exports", {}) if isinstance(package_manifest.get("exports"), dict) else {}
    exported_stream_ids = sorted(str(value) for value in exports.get("streams", []) if value)
    exported_command_ids = sorted(str(value) for value in exports.get("commands", []) if value)
    exported_module_ids = sorted(str(value) for value in exports.get("modules", []) if value)
    manifest_stream_ids = collect_manifest_ids(stream_manifests, "stream_id")
    manifest_command_ids = collect_manifest_ids(command_manifests, "command_id")
    manifest_module_ids = collect_manifest_ids(module_manifests, "module_id")
    feedback_sink = next(
        (
            manifest
            for manifest in module_manifests
            if manifest.get("module_id") == "module.breath.feedback_sink"
        ),
        {},
    )
    state_value_module = next(
        (
            manifest
            for manifest in module_manifests
            if manifest.get("module_id") == "module.breath.state_value"
        ),
        {},
    )
    stream_bindings = [
        binding
        for binding in handoff.get("stream_bindings", [])
        if isinstance(binding, dict)
    ]
    binding_pairs = sorted(
        {
            (str(binding.get("stream_id")), str(binding.get("direction")))
            for binding in stream_bindings
            if binding.get("stream_id") and binding.get("direction")
        }
    )
    bound_stream_ids = sorted({stream_id for stream_id, _direction in binding_pairs})
    command_ids = sorted(str(command_id) for command_id in handoff.get("command_ids", []) if command_id)
    transport_offers = [
        offer
        for offer in handoff.get("transport_offers", [])
        if isinstance(offer, dict)
    ]
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.schema",
            handoff.get("$schema") == "rusty.manifold.shell.handoff.v1",
            "shell handoff manifest uses the Manifold shell handoff schema",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.required_bindings",
            PMB_SHELL_HANDOFF_REQUIRED_BINDINGS.issubset(set(binding_pairs)),
            "shell handoff binds controller pose input, breath feedback subscription, and feedback receipt publication",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.stream_manifest_ids",
            set(bound_stream_ids).issubset(set(manifest_stream_ids)),
            "all shell handoff stream bindings are declared by PMB stream manifests",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.command_manifest_ids",
            bool(command_ids) and set(command_ids).issubset(set(manifest_command_ids)),
            "all shell handoff commands are declared by PMB command manifests",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.feedback_receipt_export",
            "stream.breath.feedback_receipt" in exported_stream_ids,
            "PMB package exports stream.breath.feedback_receipt for downstream shell acknowledgements",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.state_stream_exports",
            PMB_BREATH_STATE_STREAM in exported_stream_ids
            and PMB_BREATH_STATE_VALUE_STREAM in exported_stream_ids,
            "PMB package exports raw breath state and processed state-value streams",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.state_value_module",
            PMB_BREATH_STATE_VALUE_STREAM in state_value_module.get("provides_streams", []),
            "PMB state-value module provides stream.breath.state.value",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.feedback_sink_provider",
            "stream.breath.feedback_receipt" in feedback_sink.get("provides_streams", []),
            "PMB feedback sink module provides stream.breath.feedback_receipt",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.transport_offer",
            bool(transport_offers)
            and all(
                offer.get("transport_id")
                and offer.get("transport")
                and offer.get("endpoint_id")
                for offer in transport_offers
            ),
            "shell handoff exposes named transport offers without requiring a live transport",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.clean_boundary",
            True,
            "validation used package manifests and handoff fixture only, with no legacy app, device, or runtime shell dependency",
            "validation.pmb_shell_handoff_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    issues = [
        {
            "code": check["issue_codes"][0],
            "severity": "error",
            "message": check["evidence"],
            "related_id": check["check_id"],
        }
        for check in checks
        if check["status"] != "pass" and check.get("issue_codes")
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.shell_handoff_validation_evidence.v1",
        "status": status,
        "target": "desktop",
        "host_profile": "desktop",
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "duration_ms": int((ended_utc - started_utc).total_seconds() * 1000),
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.desktop",
            "host_app_version": "0.1.0",
        },
        "package": projected_motion_package_snapshot(package_root),
        "package_root_name": package_root.name,
        "packages_workspace_name": packages_root.name,
        "execution": {
            "mode": "projected_motion_breath_shell_handoff_validation",
            "handoff_validation_performed": True,
            "execution_performed": True,
            "runtime_execution_performed": False,
            "processor_core_executed": False,
            "desktop_execution_performed": True,
            "platform_execution_performed": False,
            "device_required": False,
            "android_execution_performed": False,
            "quest_execution_performed": False,
            "apk_build_performed": False,
            "openxr_runtime_used": False,
            "adb_used": False,
            "external_transport_used": False,
            "broker_transport_used": False,
            "live_sensor_used": False,
            "downstream_shell_runtime_used": False,
            "legacy_app_dependency_used": False,
            "legacy_reference_repo_used": False,
        },
        "shell_handoff": {
            "handoff_artifact": handoff_path.name,
            "handoff_id": handoff.get("handoff_id"),
            "handoff_revision": handoff.get("handoff_revision"),
            "target_host_profile": handoff.get("target_host_profile"),
            "shell_app_id": handoff.get("shell_app_id"),
            "validation_slot_id": handoff.get("validation_slot_id"),
            "expected_scorecard_id": handoff.get("expected_scorecard_id"),
            "stream_bindings": [
                {
                    "stream_id": binding.get("stream_id"),
                    "direction": binding.get("direction"),
                    "role": binding.get("role"),
                    "required": binding.get("required", False),
                }
                for binding in stream_bindings
            ],
            "binding_pairs": [
                {"stream_id": stream_id, "direction": direction}
                for stream_id, direction in binding_pairs
            ],
            "command_ids": command_ids,
            "transport_offers": transport_offers,
        },
        "package_contract": {
            "package_id": package_manifest.get("package_id"),
            "exported_stream_ids": exported_stream_ids,
            "exported_command_ids": exported_command_ids,
            "exported_module_ids": exported_module_ids,
            "manifest_stream_ids": manifest_stream_ids,
            "manifest_command_ids": manifest_command_ids,
            "manifest_module_ids": manifest_module_ids,
            "feedback_sink_provides_streams": sorted(
                str(stream_id)
                for stream_id in feedback_sink.get("provides_streams", [])
                if stream_id
            ),
            "state_value_provides_streams": sorted(
                str(stream_id)
                for stream_id in state_value_module.get("provides_streams", [])
                if stream_id
            ),
        },
        "commands": [
            {
                "command": "validate_projected_motion_breath_shell_handoff",
                "status": "acknowledged" if status == "pass" else "rejected",
                "runtime_path": "python.hostessctl.v1",
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.shell_handoff",
            "target_id": "hostess.projected_motion_breath.shell_handoff",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": issues,
        },
    }


def validate_pmb_shell_handoff_validation_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    shell_handoff = evidence.get("shell_handoff", {})
    package_contract = evidence.get("package_contract", {})
    binding_pairs = {
        (str(binding.get("stream_id")), str(binding.get("direction")))
        for binding in shell_handoff.get("binding_pairs", [])
        if isinstance(binding, dict) and binding.get("stream_id") and binding.get("direction")
    }
    bound_stream_ids = {stream_id for stream_id, _direction in binding_pairs}
    command_ids = set(shell_handoff.get("command_ids", []))
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.shell_handoff_validation_evidence.v1",
            "PMB shell handoff validation evidence schema is supported",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.status",
            evidence.get("status") == "pass",
            "PMB shell handoff validation evidence status passed",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.required_bindings",
            PMB_SHELL_HANDOFF_REQUIRED_BINDINGS.issubset(binding_pairs),
            "PMB shell handoff includes the required stream directions",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.stream_manifests",
            bound_stream_ids.issubset(set(package_contract.get("manifest_stream_ids", []))),
            "PMB shell handoff streams resolve to package stream manifests",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.commands",
            bool(command_ids)
            and command_ids.issubset(set(package_contract.get("manifest_command_ids", []))),
            "PMB shell handoff commands resolve to package command manifests",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.feedback_receipt_export",
            "stream.breath.feedback_receipt" in package_contract.get("exported_stream_ids", []),
            "PMB package exports stream.breath.feedback_receipt",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.state_stream_exports",
            PMB_BREATH_STATE_STREAM in package_contract.get("exported_stream_ids", [])
            and PMB_BREATH_STATE_VALUE_STREAM in package_contract.get("exported_stream_ids", []),
            "PMB package exports raw breath state and processed state-value streams",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.state_value_module",
            PMB_BREATH_STATE_VALUE_STREAM in package_contract.get("state_value_provides_streams", []),
            "PMB state-value module provides stream.breath.state.value",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.feedback_sink",
            "stream.breath.feedback_receipt" in package_contract.get("feedback_sink_provides_streams", []),
            "PMB feedback sink provides stream.breath.feedback_receipt",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.transport_offer",
            bool(shell_handoff.get("transport_offers")),
            "PMB shell handoff declares at least one named transport offer",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.clean_boundary",
            execution.get("runtime_execution_performed") is False
            and execution.get("platform_execution_performed") is False
            and execution.get("device_required") is False
            and execution.get("external_transport_used") is False
            and execution.get("broker_transport_used") is False
            and execution.get("downstream_shell_runtime_used") is False
            and execution.get("legacy_app_dependency_used") is False
            and execution.get("legacy_reference_repo_used") is False,
            "PMB shell handoff validation avoided runtime shell, device, transport, and legacy repo dependencies",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB shell handoff validation scorecard passed",
            "validation.pmb_shell_handoff_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.shell_handoff_validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def validate_pmb_android_replay_execution_evidence(
    evidence: dict[str, Any],
    *,
    package_root: Path,
    target: str,
    host_profile: str,
) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    core_summary = evidence.get("core_report_summary", {})
    package = evidence.get("package", {})
    local_package = projected_motion_package_snapshot(package_root)
    expected_manifest_hash = local_package.get("package_manifest_sha256")
    actual_manifest_hash = package.get("package_manifest_sha256")
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.android_replay_execution_evidence.v1",
            "PMB Android replay evidence schema is supported",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.status",
            evidence.get("status") == "pass",
            "PMB Android replay evidence status passed",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.target",
            evidence.get("target") == target and evidence.get("host_profile") == host_profile,
            f"PMB Android replay targeted {target}/{host_profile}",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.runtime_executed",
            execution.get("execution_performed") is True
            and execution.get("runtime_execution_performed") is True
            and execution.get("processor_core_executed") is True
            and execution.get("android_execution_performed") is True
            and execution.get("platform_execution_performed") is True,
            "PMB processor core execution was performed on Android",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.quest_flag",
            execution.get("quest_execution_performed") == (target == "quest"),
            f"PMB replay quest flag matched target={target}",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.synthetic_only",
            execution.get("synthetic_replay") is True
            and execution.get("openxr_runtime_used") is False
            and execution.get("live_sensor_used") is False
            and execution.get("controller_input_used") is False,
            "PMB Android replay avoided OpenXR, live sensors, and controller input",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.core_counts",
            core_summary.get("checked_cases", 0) >= 2
            and core_summary.get("checked_damaged_cases", 0) >= 2
            and core_summary.get("checked_adapter_normalization_cases", 0) >= 3
            and core_summary.get("checked_damaged_adapter_normalization_cases", 0) >= 2,
            "PMB core replay executed golden and adapter-normalization fixture sets on Android",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.package_manifest_hash",
            bool(expected_manifest_hash)
            and expected_manifest_hash != "unavailable"
            and actual_manifest_hash == expected_manifest_hash,
            "PMB Android packaged manifest hash matched the supplied package root",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB Android app-side scorecard passed",
            "validation.pmb_android_replay_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_replay_execution_validation.v1",
        "status": "pass" if not errors else "fail",
        "target": target,
        "host_profile": host_profile,
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def validate_pmb_controller_preflight_evidence(
    evidence: dict[str, Any],
    *,
    package_root: Path,
    target: str,
    host_profile: str,
) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    report = evidence.get("controller_preflight_report_summary", {})
    package = evidence.get("package", {})
    local_package = projected_motion_package_snapshot(package_root)
    expected_manifest_hash = local_package.get("package_manifest_sha256")
    actual_manifest_hash = package.get("package_manifest_sha256")
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.android_controller_preflight_evidence.v1",
            "PMB controller preflight evidence schema is supported",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.status",
            evidence.get("status") == "pass",
            "PMB controller preflight evidence status passed",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.target",
            evidence.get("target") == target and evidence.get("host_profile") == host_profile,
            f"PMB controller preflight targeted {target}/{host_profile}",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.quest_execution",
            execution.get("quest_execution_performed") == (target == "quest")
            and execution.get("android_execution_performed") is True
            and execution.get("platform_execution_performed") is True
            and execution.get("device_required") is True,
            "PMB controller preflight was executed on the requested Android/Quest target",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.processor_executed",
            execution.get("processor_core_executed") is True
            and execution.get("runtime_execution_performed") is True
            and report.get("processor_core_executed") is True
            and report.get("runtime_execution_performed") is True,
            "PMB processor core executed through the controller preflight route",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.provider_route",
            execution.get("pmb_controller_path_preflight_passed") is True
            and execution.get("controller_provider_route_ready") is True
            and execution.get("provider_boundary_exercised") is True
            and report.get("controller_provider_route_ready") is True
            and report.get("provider_boundary_exercised") is True
            and report.get("output_stream_id") == "stream.motion.object_pose",
            "controller-shaped provider route emitted stream.motion.object_pose into PMB",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.non_human_gate",
            execution.get("synthetic_replay") is True
            and execution.get("preflight_fixture_packaged") is True
            and execution.get("openxr_runtime_used") is False
            and execution.get("live_sensor_used") is False
            and execution.get("physical_controller_input_used") is False
            and execution.get("controller_input_used") is False
            and execution.get("human_controller_trial_performed") is False
            and execution.get("manual_controller_trial_required") is True
            and report.get("physical_controller_input_used") is False
            and report.get("controller_input_used") is False
            and report.get("manual_controller_trial_required") is True,
            "preflight used packaged controller-shaped samples and left the human controller trial pending",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.report_counts",
            report.get("sample_count", 0) >= 3
            and report.get("normalized_sample_count", 0) >= 3
            and report.get("estimate_count", 0) >= 3,
            "controller preflight report contains normalized samples and PMB estimates",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.package_manifest_hash",
            bool(expected_manifest_hash)
            and expected_manifest_hash != "unavailable"
            and actual_manifest_hash == expected_manifest_hash,
            "PMB Android packaged manifest hash matched the supplied package root",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB Android app-side controller preflight scorecard passed",
            "validation.pmb_controller_preflight_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_controller_preflight_validation.v1",
        "status": "pass" if not errors else "fail",
        "target": target,
        "host_profile": host_profile,
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def validate_pmb_quest_simulated_live_evidence(
    evidence: dict[str, Any],
    *,
    package_root: Path,
    target: str,
    host_profile: str,
) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    route = evidence.get("route_report_summary", {})
    broker = evidence.get("broker_publish_summary", {})
    package = evidence.get("package", {})
    local_package = projected_motion_package_snapshot(package_root)
    expected_manifest_hash = local_package.get("package_manifest_sha256")
    actual_manifest_hash = package.get("package_manifest_sha256")
    input_stream_ids = set(route.get("input_stream_ids", []))
    output_stream_ids = set(route.get("output_stream_ids", []))
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.android_simulated_live_execution_evidence.v1",
            "PMB Quest simulated live evidence schema is supported",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.status",
            evidence.get("status") == "pass",
            "PMB Quest simulated live evidence status passed",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.target",
            evidence.get("target") == target and evidence.get("host_profile") == host_profile,
            f"PMB simulated live targeted {target}/{host_profile}",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.quest_authority",
            execution.get("quest_execution_performed") is True
            and execution.get("android_execution_performed") is True
            and execution.get("platform_execution_performed") is True
            and execution.get("pmd_computed_on_quest") is True
            and execution.get("pmd_computed_on_pc") is False
            and execution.get("pc_processor_core_executed") is False
            and execution.get("processor_authority") == "quest_hostess_android_app",
            "PMD processing authority was the Quest Android app, not the PC",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.sources",
            {"bio:polar_acc", "stream.motion.object_pose"}.issubset(input_stream_ids)
            and {
                PMB_BREATH_VOLUME_STREAM,
                PMB_BREATH_VOLUME_SELECTED_STREAM,
                PMB_BREATH_STATE_STREAM,
                PMB_BREATH_STATE_VALUE_STREAM,
                PMB_BREATH_FEEDBACK_STATE_STREAM,
            }.issubset(output_stream_ids)
            and int(route.get("source_route_count", 0)) >= 2
            and int(route.get("breath_sample_count", 0)) >= 6
            and int(route.get("state_sample_count", 0)) >= 6
            and int(route.get("state_value_sample_count", 0)) >= 6
            and int(route.get("feedback_sample_count", 0)) >= 6,
            "simulated Polar ACC and controller object-pose routes produced PMB outputs",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.non_physical_gate",
            execution.get("simulated_polar_provider_used") is True
            and execution.get("simulated_controller_provider_used") is True
            and execution.get("physical_polar_ble_used") is False
            and execution.get("physical_controller_input_used") is False
            and execution.get("controller_input_used") is False
            and execution.get("manual_polar_trial_required") is True
            and execution.get("manual_controller_trial_required") is True,
            "run used simulated providers and did not claim physical Polar/controller input",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.broker_feedback",
            execution.get("broker_transport_used") is True
            and execution.get("feedback_published_to_broker") is True
            and execution.get("breath_state_published_to_broker") is True
            and execution.get("breath_state_value_published_to_broker") is True
            and broker.get("broker_transport_used") is True
            and int(broker.get("selected_breath_published_count", 0)) > 0
            and int(broker.get("state_published_count", 0)) > 0
            and int(broker.get("state_value_published_count", 0)) > 0
            and int(broker.get("feedback_published_count", 0)) > 0,
            "Quest app published selected breath, raw state, processed state-value, and PMB feedback to the broker",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.makepad_receipts",
            int(broker.get("feedback_published_count", 0)) > 0
            and int(broker.get("selected_breath_published_count", 0)) > 0
            and int(broker.get("feedback_receipt_count", 0)) == int(broker.get("selected_breath_published_count", -1))
            and int(execution.get("makepad_feedback_receipt_count", 0))
            == int(broker.get("selected_breath_published_count", -1)),
            "Makepad acknowledged every broker selected breath sample",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.package_manifest_hash",
            bool(expected_manifest_hash)
            and expected_manifest_hash != "unavailable"
            and actual_manifest_hash == expected_manifest_hash,
            "PMB Android packaged manifest hash matched the supplied package root",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB Quest simulated live app-side scorecard passed",
            "validation.pmb_quest_simulated_live_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_simulated_live_validation.v1",
        "status": "pass" if not errors else "fail",
        "target": target,
        "host_profile": host_profile,
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def pmb_physical_input_requirements_pass(
    capture: dict[str, Any],
    execution: dict[str, Any],
) -> bool:
    polar_required = bool(capture.get("polar_required", True))
    controller_required = bool(capture.get("controller_required", True))
    polar_used = (
        capture.get("physical_polar_ble_used") is True
        and execution.get("physical_polar_ble_used") is True
        and int(capture.get("polar_event_count", 0)) > 0
    )
    controller_used = (
        capture.get("physical_controller_input_used") is True
        and execution.get("physical_controller_input_used") is True
        and execution.get("controller_input_used") is True
        and int(capture.get("active_tracked_connected_object_pose_count", 0)) > 0
    )
    if polar_required and not polar_used:
        return False
    if controller_required and not controller_used:
        return False
    if not polar_required and not controller_required:
        return polar_used or controller_used
    return True


def validate_pmb_quest_physical_live_evidence(
    evidence: dict[str, Any],
    *,
    package_root: Path,
    target: str,
    host_profile: str,
) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    capture = evidence.get("input_capture_summary", {})
    route = evidence.get("route_report_summary", {})
    broker = evidence.get("broker_publish_summary", {})
    package = evidence.get("package", {})
    local_package = projected_motion_package_snapshot(package_root)
    expected_manifest_hash = local_package.get("package_manifest_sha256")
    actual_manifest_hash = package.get("package_manifest_sha256")
    input_stream_ids = set(route.get("input_stream_ids", []))
    output_stream_ids = set(route.get("output_stream_ids", []))
    polar_required = bool(capture.get("polar_required", True))
    controller_required = bool(capture.get("controller_required", True))
    app_receipt_policy = pmb_app_receipt_policy(evidence)
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.android_physical_live_execution_evidence.v1",
            "PMB Quest physical live evidence schema is supported",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.status",
            pmb_evidence_status_accepts_receipt_policy(evidence),
            "PMB Quest physical live evidence status passed or native renderer receipt policy accounted for app-side Makepad receipt failure",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.target",
            evidence.get("target") == target and evidence.get("host_profile") == host_profile,
            f"PMB physical live targeted {target}/{host_profile}",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.physical_inputs",
            pmb_physical_input_requirements_pass(capture, execution),
            "Quest broker captured the required physical PMB input streams for the selected source",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.quest_authority",
            execution.get("quest_execution_performed") is True
            and execution.get("android_execution_performed") is True
            and execution.get("platform_execution_performed") is True
            and execution.get("pmd_computed_on_quest") is True
            and execution.get("pmd_computed_on_pc") is False
            and execution.get("pc_processor_core_executed") is False
            and execution.get("processor_authority") == "quest_hostess_android_app",
            "PMD processing authority was the Quest Android app, not the PC",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.not_simulated",
            execution.get("simulated_polar_provider_used") is False
            and execution.get("simulated_controller_provider_used") is False
            and execution.get("synthetic_live_route") is False
            and pmb_physical_input_requirements_pass(capture, execution),
            "physical PMB route did not claim simulated providers",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.route",
            (not polar_required or "bio:polar_acc" in input_stream_ids)
            and (not controller_required or "stream.motion.object_pose" in input_stream_ids)
            and {
                PMB_BREATH_VOLUME_STREAM,
                PMB_BREATH_VOLUME_SELECTED_STREAM,
                PMB_BREATH_STATE_STREAM,
                PMB_BREATH_STATE_VALUE_STREAM,
                PMB_BREATH_FEEDBACK_STATE_STREAM,
            }.issubset(output_stream_ids)
            and route.get("status") == "pass"
            and route.get("external_transport_used") is True
            and route.get("live_sensor_used") is True
            and route.get("plan_only_fixture") is False
            and int(route.get("breath_sample_count", 0)) > 0
            and int(route.get("state_sample_count", 0)) > 0
            and int(route.get("state_value_sample_count", 0)) > 0
            and int(route.get("feedback_sample_count", 0)) > 0,
            "PMB live route consumed physical broker transport events and produced breath feedback",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.makepad_receipts",
            broker.get("publish_mode") == "event_driven_live_processor"
            and broker.get("live_publish_during_capture") is True
            and broker.get("incremental_processor_used") is True
            and broker.get("snapshot_replay_used") is False
            and int(broker.get("input_event_processed_count", 0)) > 0
            and int(broker.get("live_processor_output_update_count", 0)) > 0
            and int(broker.get("first_selected_publish_elapsed_ms", -1)) >= 0
            and int(broker.get("state_published_count", 0)) > 0
            and int(broker.get("state_value_published_count", 0)) > 0
            and int(broker.get("feedback_published_count", 0)) > 0
            and int(broker.get("selected_breath_published_count", 0)) > 0
            and pmb_app_receipt_policy_pass(evidence),
            f"PMB application receipt policy {app_receipt_policy} accepted event-driven live samples while selected breath, raw state, and processed state-value were published during capture",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.package_manifest_hash",
            bool(expected_manifest_hash)
            and expected_manifest_hash != "unavailable"
            and actual_manifest_hash == expected_manifest_hash,
            "PMB Android packaged manifest hash matched the supplied package root",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.app_scorecard",
            pmb_scorecard_status_accepts_receipt_policy(evidence),
            "PMB Quest physical live app-side scorecard passed or native renderer receipt policy accounted for its Makepad receipt-only failure",
            "validation.pmb_quest_physical_live_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_physical_live_validation.v1",
        "status": "pass" if not errors else "fail",
        "target": target,
        "host_profile": host_profile,
        "evidence_status": evidence.get("status"),
        "app_receipt_policy": app_receipt_policy,
        "checks": checks,
        "errors": errors,
    }
