"""Recording evidence and scorecard helpers for hostessctl."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.pmb_evidence import host_app_for, iso_to_epoch_ms

def validate_broker_telemetry_observer_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    capture = evidence.get("capture", {})
    broker_report = evidence.get("broker_report", {})
    streams = [stream for stream in evidence.get("streams", []) if isinstance(stream, dict)]
    polar_stream = next(
        (stream for stream in streams if stream.get("stream_id") == "bio:polar_acc"),
        {},
    )
    checks = [
        recording_scorecard_check(
            "hostess.check.broker_telemetry.schema",
            evidence.get("$schema") == "rusty.hostess.broker_telemetry_observer.evidence.v1",
            "broker telemetry observer evidence schema is supported",
        ),
        recording_scorecard_check(
            "hostess.check.broker_telemetry.observer_boundary",
            capture.get("direct_ble_used") is False
            and evidence.get("direct_ble_used") is False
            and capture.get("hostess_role") == "foreground_telemetry_ui_observer",
            "foreground telemetry UI observes broker streams and does not open direct BLE",
        ),
        recording_scorecard_check(
            "hostess.check.broker_telemetry.broker_transport",
            capture.get("broker_transport_used") is True
            and broker_report.get("broker_connected") is True,
            "broker WebSocket transport was used by the foreground telemetry UI",
        ),
        recording_scorecard_check(
            "hostess.check.broker_telemetry.stream",
            polar_stream.get("status") == "pass"
            and int(polar_stream.get("sample_count") or 0) > 0
            and int(broker_report.get("frame_count") or 0) > 0,
            "bio:polar_acc broker stream produced frames for visualization",
        ),
        recording_scorecard_check(
            "hostess.check.broker_telemetry.status",
            evidence.get("status") == "pass"
            and broker_report.get("status") == "pass"
            and evidence.get("telemetry_ui_visualized") is True,
            "foreground telemetry observer run passed and visualized live telemetry",
        ),
    ]
    errors = [check["evidence"] for check in checks if check["status"] != "pass"]
    return {
        "$schema": "rusty.hostess.broker_telemetry_observer.validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def validate_broker_websocket_stream_recording_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    streams = [stream for stream in evidence.get("streams", []) if isinstance(stream, dict)]
    pmb_requested = evidence.get("pmb_live_processor_requested") is True
    broker_identity_record = evidence.get("transport", {}).get("broker_identity", {})
    checks = [
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.schema",
            evidence.get("$schema") == "rusty.hostess.broker_stream_recording.evidence.v1",
            "broker stream recording evidence schema is supported",
        ),
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.streams",
            bool(streams) and all(stream.get("status") == "pass" for stream in streams),
            "all requested broker streams produced at least one event",
        ),
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.transport",
            evidence.get("broker_websocket_recording") is True
            and evidence.get("transport", {}).get("kind") == "adb-forwarded-broker-websocket",
            "recording used the adb-forwarded broker websocket transport",
        ),
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.broker_identity",
            isinstance(broker_identity_record, dict)
            and broker_identity_record.get("authority") == "rusty.manifold"
            and bool(broker_identity_record.get("package_name")),
            "broker stream recording records the selected Manifold broker identity",
        ),
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.pmb_processor_bridge",
            not pmb_requested
            or (
                evidence.get("pmb_processor_executed") is True
                and evidence.get("pmb_breath_published") is True
                and evidence.get("pmb_selected_breath_published") is True
                and evidence.get("pmb_feedback_published") is True
            ),
            "PMB live processor bridge ran and published aggregate, selected, and feedback output streams when requested",
        ),
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.makepad_breath_feedback_receipt",
            not pmb_requested or int(evidence.get("pmb_feedback_receipt_count") or 0) > 0,
            "Makepad receipt stream acknowledged at least one PMB feedback sample when requested",
        ),
    ]
    errors = [check["evidence"] for check in checks if check["status"] != "pass"]
    return {
        "$schema": "rusty.hostess.broker_stream_recording.validation.v1",
        "status": "pass" if not errors and evidence.get("status") == "pass" else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors + list(evidence.get("errors", [])),
    }


def build_manifold_value_recording_evidence(
    *,
    args: argparse.Namespace,
    requested_values: list[str],
    provider_plans: list[dict[str, Any]],
    route_status: str,
    route_reasons: list[str],
    host_profile: str,
    started_utc: datetime,
    ended_utc: datetime,
    capture_status: int | None,
    capture_evidence_path: Path | None,
    capture_evidence: dict[str, Any] | None,
    broker_identity_record: dict[str, Any],
) -> dict[str, Any]:
    recording_performed = capture_status is not None
    capture_passed = capture_status == 0 and capture_evidence is not None
    if route_status == "blocked":
        status = "blocked"
    elif recording_performed:
        status = "pass" if capture_passed else "fail"
    else:
        status = "ready"
    capture_artifacts = []
    if capture_evidence_path is not None:
        capture_artifacts.append(
            {
                "artifact_id": "artifact.manifold_value_recording.source_capture_evidence",
                "path": str(capture_evidence_path),
                "exists": capture_evidence_path.exists(),
            }
        )
        validation_path = capture_evidence_path.with_name(
            f"{capture_evidence_path.stem}.validation-report.json"
        )
        capture_artifacts.append(
            {
                "artifact_id": "artifact.manifold_value_recording.source_capture_validation",
                "path": str(validation_path),
                "exists": validation_path.exists(),
            }
        )
        if capture_evidence:
            pmb_bridge = capture_evidence.get("pmb_processor_bridge")
            if isinstance(pmb_bridge, dict):
                capture_artifacts.extend(
                    artifact
                    for artifact in pmb_bridge.get("artifacts", [])
                    if isinstance(artifact, dict)
                )
    captured_streams = []
    if capture_evidence:
        captured_streams = [
            {
                "stream_id": stream.get("stream_id"),
                "broker_stream_id": stream.get("broker_stream_id"),
                "status": stream.get("status"),
                "sample_count": stream.get("sample_count"),
                "event_count": stream.get("event_count"),
            }
            for stream in capture_evidence.get("streams", [])
            if isinstance(stream, dict)
        ]
    has_object_pose = any(
        plan.get("stream_id") == "stream.motion.object_pose"
        for plan in provider_plans
    )
    object_pose_captured = any(
        stream.get("stream_id") == "stream.motion.object_pose"
        and stream.get("status") == "pass"
        and int(stream.get("event_count") or stream.get("sample_count") or 0) > 0
        for stream in captured_streams
    )
    all_combined_supported = all(
        bool(plan.get("combined_recording_supported"))
        for plan in provider_plans
    )
    controller_input_used = bool(recording_performed and object_pose_captured)
    selected_identity = dict(broker_identity_record)
    return {
        "$schema": "rusty.hostess.manifold_value_recording.evidence.v1",
        "status": status,
        "target": args.target,
        "host_profile": host_profile,
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "duration_ms": int((ended_utc - started_utc).total_seconds() * 1000),
        "requested_duration_ms": int(args.duration_seconds * 1000),
        "software": {
            "origin": "rusty-hostess",
            "host_app": host_app_for(host_profile),
            "host_app_version": "0.1.0",
        },
        "request": {
            "$schema": "rusty.hostess.manifold_value_recording.request.v1",
            "requested_value_ids": requested_values,
            "duration_seconds": args.duration_seconds,
            "target": args.target,
            "host_profile": host_profile,
            "mode": "live",
            "plan_only": bool(args.plan_only),
            "pmb_live_processor": bool(args.pmb_live_processor),
            "broker_identity": selected_identity,
        },
        "recording": {
            "mode": "manifold_value_recording",
            "route_status": route_status,
            "recording_performed": recording_performed,
            "capture_returncode": capture_status,
            "plan_only": bool(args.plan_only),
            "general_recorder": True,
            "polar_specific": False,
            "controller_specific": False,
            "provider_bound": True,
            "live_sensor_used": recording_performed,
            "physical_controller_input_used": controller_input_used,
            "controller_input_used": controller_input_used,
            "simultaneous_multi_value_recording_supported": all_combined_supported,
            "manual_controller_trial_required": has_object_pose and not controller_input_used,
            "pmb_live_processor_requested": bool(args.pmb_live_processor),
            "pmb_processor_executed": bool(capture_evidence and capture_evidence.get("pmb_processor_executed")),
            "pmb_breath_published": bool(capture_evidence and capture_evidence.get("pmb_breath_published")),
            "pmb_breath_publish_count": int(capture_evidence.get("pmb_breath_publish_count") or 0) if capture_evidence else 0,
            "pmb_feedback_published": bool(capture_evidence and capture_evidence.get("pmb_feedback_published")),
            "pmb_feedback_publish_count": int(capture_evidence.get("pmb_feedback_publish_count") or 0) if capture_evidence else 0,
            "pmb_feedback_receipt_count": int(capture_evidence.get("pmb_feedback_receipt_count") or 0) if capture_evidence else 0,
            "legacy_reference_broker_selected": bool(selected_identity.get("legacy_reference_package")),
            "legacy_reference_broker_used": bool(
                recording_performed and selected_identity.get("legacy_reference_package")
            ),
            "makepad_breath_feedback_subscriber_configured": bool(
                capture_evidence and capture_evidence.get("makepad_breath_feedback_subscriber_configured")
            ),
            "makepad_breath_feedback_subscriber_flags_owner": (
                capture_evidence.get("makepad_breath_feedback_subscriber_flags_owner")
                if capture_evidence
                else None
            ),
        },
        "provider_plans": provider_plans,
        "blocked_reasons": route_reasons,
        "capture_artifacts": capture_artifacts,
        "captured_streams": captured_streams,
        "commands": [
            {
                "command": "record_manifold_values",
                "status": "acknowledged" if status in {"pass", "ready"} else status,
                "requested_value_ids": requested_values,
                "duration_seconds": args.duration_seconds,
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.manifold_value_recording",
            "target_id": "hostess.manifold_value_recording",
            "target_revision": 1,
            "status": "pass" if status in {"pass", "ready"} else status,
            "checks": [],
            "issues": [
                {
                    "code": "recording.manifold_value_recording.blocked",
                    "severity": "warning",
                    "message": reason,
                }
                for reason in route_reasons
            ],
        },
    }


def validate_manifold_value_recording_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    recording = evidence.get("recording", {})
    request = evidence.get("request", {})
    provider_plans = evidence.get("provider_plans", [])
    captured_streams = [
        stream
        for stream in evidence.get("captured_streams", [])
        if isinstance(stream, dict)
    ]
    status = evidence.get("status")
    has_object_pose = any(
        isinstance(plan, dict) and plan.get("stream_id") == "stream.motion.object_pose"
        for plan in provider_plans
    )
    object_pose_captured = any(
        stream.get("stream_id") == "stream.motion.object_pose"
        and stream.get("status") == "pass"
        and int(stream.get("event_count") or stream.get("sample_count") or 0) > 0
        for stream in captured_streams
    )
    recording_performed = recording.get("recording_performed") is True
    pmb_requested = recording.get("pmb_live_processor_requested") is True
    controller_claim_ok = (
        (
            not has_object_pose
            and recording.get("physical_controller_input_used") is False
            and recording.get("controller_input_used") is False
        )
        or (
            has_object_pose
            and not recording_performed
            and recording.get("physical_controller_input_used") is False
            and recording.get("controller_input_used") is False
        )
        or (
            has_object_pose
            and recording_performed
            and object_pose_captured
            and recording.get("physical_controller_input_used") is True
            and recording.get("controller_input_used") is True
        )
        or (
            has_object_pose
            and recording_performed
            and not object_pose_captured
            and recording.get("physical_controller_input_used") is False
            and recording.get("controller_input_used") is False
        )
    )
    requested_streams = [
        str(value)
        for value in request.get("requested_value_ids", [])
    ]
    request_broker_identity = request.get("broker_identity", {})
    captured_pass_streams = {
        str(stream.get("stream_id"))
        for stream in captured_streams
        if stream.get("status") == "pass"
    }
    checks = [
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.schema",
            evidence.get("$schema") == "rusty.hostess.manifold_value_recording.evidence.v1",
            "Manifold value recording evidence schema is supported",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.values",
            bool(request.get("requested_value_ids")) and isinstance(provider_plans, list),
            "recording request includes at least one Manifold value and provider plan",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.duration",
            int(evidence.get("requested_duration_ms", 0)) > 0,
            "recording request duration is positive",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.general_boundary",
            recording.get("general_recorder") is True
            and recording.get("polar_specific") is False
            and recording.get("controller_specific") is False,
            "recording route is general and not Polar- or controller-specific",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.controller_claim",
            controller_claim_ok,
            "controller input claim matches requested provider and execution state",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.status",
            status in {"pass", "ready", "blocked", "fail"},
            f"recording evidence status is {status}",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.broker_identity",
            isinstance(request_broker_identity, dict)
            and request_broker_identity.get("authority") == "rusty.manifold"
            and bool(request_broker_identity.get("package_name")),
            "recording request records a Manifold broker identity",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.pass_requires_capture",
            status != "pass" or recording.get("recording_performed") is True,
            "passing recording evidence includes an executed source capture",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.blocked_is_explicit",
            status != "blocked" or bool(evidence.get("blocked_reasons")),
            "blocked recording evidence lists explicit blocked reasons",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.pass_streams",
            status != "pass" or all(stream_id in captured_pass_streams for stream_id in requested_streams),
            "passing recording evidence includes every requested stream",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.pmb_live_processor_bridge",
            status != "pass"
            or not pmb_requested
            or (
                recording.get("pmb_processor_executed") is True
                and recording.get("pmb_breath_published") is True
                and recording.get("pmb_feedback_published") is True
                and int(recording.get("pmb_feedback_receipt_count") or 0) > 0
                and recording.get("makepad_breath_feedback_subscriber_configured") is True
            ),
            "passing PMB bridge recording ran the processor, published breath streams, and received Makepad feedback ack",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.manifold_value_recording.validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": status,
        "checks": checks,
        "errors": errors,
    }


def write_manifold_value_recording_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    provider_plans = [
        plan for plan in raw.get("provider_plans", [])
        if isinstance(plan, dict)
    ]
    package_ids = sorted(
        {
            str(plan["package_id"])
            for plan in provider_plans
            if plan.get("package_id")
        }
    )
    checks = [
        recording_scorecard_check(
            "validation.check.manifold_value_recording_validation",
            validation_report.get("status") == "pass",
            "Manifold value recording evidence validation passed",
        ),
        recording_scorecard_check(
            "validation.check.manifold_value_recording_boundary",
            raw.get("recording", {}).get("general_recorder") is True
            and raw.get("recording", {}).get("polar_specific") is False
            and raw.get("recording", {}).get("controller_specific") is False,
            "Host-run evidence records the generic recorder boundary",
        ),
    ]
    status = raw.get("status") if validation_report.get("status") == "pass" else "fail"
    requested_values = raw.get("request", {}).get("requested_value_ids", [])
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.manifold_value_recording.{recording_segment(requested_values)}.{started_ms}",
        "bundle_id": "host_run.bundle.manifold_value_recording",
        "validation_slot_id": "host_run.slot.manifold_value_recording",
        "host_profile": f"host.{raw.get('host_profile')}",
        "app_id": host_app_for(str(raw.get("host_profile"))),
        "package_ids": package_ids,
        "module_ids": ["module.hostess.manifold_value_recorder"],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.manifold_value_recording_evidence",
            "artifact.manifold_value_recording_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "requested_value_ids": requested_values,
            "requested_duration_ms": raw.get("requested_duration_ms"),
            "recording_performed": raw.get("recording", {}).get("recording_performed"),
            "route_status": raw.get("recording", {}).get("route_status"),
            "controller_input_used": raw.get("recording", {}).get("controller_input_used"),
            "physical_controller_input_used": raw.get("recording", {}).get("physical_controller_input_used"),
            "manual_controller_trial_required": raw.get("recording", {}).get("manual_controller_trial_required"),
            "pmb_live_processor_requested": raw.get("recording", {}).get("pmb_live_processor_requested"),
            "pmb_processor_executed": raw.get("recording", {}).get("pmb_processor_executed"),
            "pmb_breath_publish_count": raw.get("recording", {}).get("pmb_breath_publish_count"),
            "pmb_feedback_publish_count": raw.get("recording", {}).get("pmb_feedback_publish_count"),
            "pmb_feedback_receipt_count": raw.get("recording", {}).get("pmb_feedback_receipt_count"),
            "broker_identity": raw.get("request", {}).get("broker_identity"),
            "legacy_reference_broker_selected": raw.get("recording", {}).get("legacy_reference_broker_selected"),
            "legacy_reference_broker_used": raw.get("recording", {}).get("legacy_reference_broker_used"),
            "makepad_breath_feedback_subscriber_configured": raw.get("recording", {}).get("makepad_breath_feedback_subscriber_configured"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.manifold_value_recording",
            "target_id": f"host_run.run.manifold_value_recording.{recording_segment(requested_values)}.{started_ms}",
            "target_revision": 1,
            "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
            "checks": checks,
            "issues": raw.get("scorecard", {}).get("issues", []),
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def recording_scorecard_check(check_id: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
        "issue_codes": [] if passed else ["validation.manifold_value_recording_failed"],
    }


def recording_segment(value_ids: list[str]) -> str:
    if not value_ids:
        return "unknown"
    pieces = [value_id.split(".")[-1].replace("-", "_") for value_id in value_ids]
    return "_".join(pieces)[:80]
