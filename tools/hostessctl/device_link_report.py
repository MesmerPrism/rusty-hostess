"""Quest device-link report adapter for Hostess session evidence."""

from __future__ import annotations

import argparse
from typing import Any

from tools.hostessctl.bridge_command_routes import DEFAULT_RUNTIME_RECEIPT_STREAM
from tools.hostessctl.platform_defaults import (
    BROKER_LOCAL_FORWARD_PORT,
    BROKER_PORT,
)


QUEST_DEVICE_LINK_SCHEMA = "rusty.quest.device_link.v1"
QUEST_DEVICE_LINK_VALIDATION_SCHEMA = "rusty.quest.device_link.validation.v1"
REQUEST_STREAM_ID = "stream.hostess.makepad.bridge_command"
VALID_STATUS = {"pass", "warn", "fail", "skipped"}


def build_device_link_report(
    args: argparse.Namespace,
    *,
    readiness_report: dict[str, Any],
    live_execution: dict[str, Any] | None,
    fallback_execution: dict[str, Any] | None,
    observed_at_ms: int,
) -> dict[str, Any]:
    """Build a Quest-owned device-link report from Hostess evidence."""

    executions = [row for row in [live_execution, fallback_execution] if isinstance(row, dict)]
    issues = execution_issues(executions)
    report = {
        "schema": QUEST_DEVICE_LINK_SCHEMA,
        "link_id": f"device_link.hostess.{safe_id(getattr(args, 'session_id', None) or observed_at_ms)}",
        "observed_at_ms": int(observed_at_ms),
        "status": report_status(readiness_report, live_execution, fallback_execution, issues),
        "device_identity": device_identity(args, readiness_report),
        "host_tools": host_tools(readiness_report),
        "tunnels": tunnels(args, live_execution),
        "broker_endpoints": broker_endpoints(args, live_execution),
        "runtime_subscribers": runtime_subscribers(args, live_execution),
        "command_results": command_results(live_execution, fallback_execution),
        "stream_capabilities": default_stream_capabilities(),
        "issues": issues,
    }
    return report


def validate_device_link_report(report: dict[str, Any]) -> dict[str, Any]:
    """Validate the Hostess-emitted subset of the Quest device-link schema."""

    errors: list[str] = []
    if report.get("schema") != QUEST_DEVICE_LINK_SCHEMA:
        errors.append("unsupported device-link schema")
    if str(report.get("link_id") or "").strip() == "":
        errors.append("link_id must not be empty")
    if report.get("status") not in VALID_STATUS:
        errors.append("status must be pass, warn, fail, or skipped")
    identity = object_value(report.get("device_identity"))
    if str(identity.get("serial") or "").strip() == "":
        errors.append("device_identity.serial must not be empty")
    if report.get("status") == "pass" and identity.get("adb_state") != "device":
        errors.append("pass device-link reports require adb_state=device")
    for command in list_value(report.get("command_results")):
        validate_command_result(object_value(command), errors)
    for capability in list_value(report.get("stream_capabilities")):
        validate_stream_capability(object_value(capability), errors)
    return {
        "$schema": QUEST_DEVICE_LINK_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "report_status": report.get("status"),
        "command_result_count": len(list_value(report.get("command_results"))),
        "stream_capability_count": len(list_value(report.get("stream_capabilities"))),
        "errors": errors,
    }


def device_identity(args: argparse.Namespace, readiness_report: dict[str, Any]) -> dict[str, Any]:
    serial = str(getattr(args, "serial", None) or readiness_report.get("scope", {}).get("serial") or "")
    model_check = readiness_check(readiness_report, "check.device.model")
    state_check = readiness_check(readiness_report, "check.device.adb_state")
    return {
        "serial": serial,
        "transport_kind": "adb_wifi" if ":" in serial else "adb_usb",
        "adb_state": evidence_text(state_check) or "unknown",
        "model": evidence_text(model_check) or "unknown",
    }


def host_tools(readiness_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for check_id, kind in [
        ("check.tool.adb", "adb"),
        ("check.host.python", "python"),
    ]:
        check = readiness_check(readiness_report, check_id)
        if not check:
            continue
        observed = object_value(check.get("observed"))
        rows.append(
            {
                "tool_id": check_id.replace("check.", "tool."),
                "kind": kind,
                "status": str(check.get("status") or "fail"),
                "required": bool(check.get("required", False)),
                "path": observed.get("resolved") or observed.get("executable") or "",
                "version": evidence_text(check),
            }
        )
    return rows


def tunnels(args: argparse.Namespace, live_execution: dict[str, Any] | None) -> list[dict[str, Any]]:
    broker_stream = object_value((live_execution or {}).get("broker_stream"))
    if not uses_adb_forward(args, live_execution):
        return []
    local_port = int(
        broker_stream.get("local_forward_port")
        or getattr(args, "broker_local_port", None)
        or BROKER_LOCAL_FORWARD_PORT
    )
    device_port = int(
        broker_stream.get("target_port") or getattr(args, "broker_port", None) or BROKER_PORT
    )
    return [
        {
            "tunnel_id": "tunnel.adb_forward.manifold_broker",
            "transport_kind": "adb_forward",
            "status": action_status(live_execution, "check-broker-adb-forward", "pass"),
            "required": True,
            "host": str(broker_stream.get("host") or getattr(args, "broker_host", "127.0.0.1")),
            "local_port": local_port,
            "device_host": "127.0.0.1",
            "device_port": device_port,
            "path": str(broker_stream.get("path") or "/manifold/v1/events"),
        }
    ]


def broker_endpoints(
    args: argparse.Namespace,
    live_execution: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    broker_stream = object_value((live_execution or {}).get("broker_stream"))
    local_port = int(
        broker_stream.get("port")
        or getattr(args, "broker_local_port", None)
        or BROKER_LOCAL_FORWARD_PORT
    )
    endpoint = {
        "endpoint_id": "broker.manifold.quest_forwarded",
        "status": action_status(live_execution, "wait-broker-forwarded-socket", "pass"),
        "protocol": "websocket",
        "authority": "rusty.manifold.command",
        "host": str(broker_stream.get("host") or getattr(args, "broker_host", "127.0.0.1")),
        "port": local_port,
        "path": str(broker_stream.get("path") or "/manifold/v1/events"),
        "command_envelope_schema": "rusty.manifold.command.envelope.v1",
        "high_rate_payload_allowed": False,
    }
    if uses_adb_forward(args, live_execution):
        endpoint["routed_through_tunnel_id"] = "tunnel.adb_forward.manifold_broker"
    return [endpoint]


def runtime_subscribers(
    args: argparse.Namespace,
    live_execution: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    delivered = runtime_dispatch_delivered_count(live_execution)
    return [
        {
            "subscriber_id": "runtime.hostess_makepad.bridge_command",
            "runtime_app_id": str(getattr(args, "makepad_package", None) or "app.hostess.makepad"),
            "request_stream_id": REQUEST_STREAM_ID,
            "receipt_stream_id": str(
                getattr(args, "runtime_receipt_stream", None) or DEFAULT_RUNTIME_RECEIPT_STREAM
            ),
            "status": "connected" if delivered > 0 else "missing",
            "receipt_required": True,
            "last_dispatch_delivered_count": delivered,
        }
    ]


def command_results(
    live_execution: dict[str, Any] | None,
    fallback_execution: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(live_execution, dict):
        rows.append(command_result(live_execution, "manifold_websocket"))
    if isinstance(fallback_execution, dict):
        rows.append(command_result(fallback_execution, "app_private_json"))
    return rows


def command_result(execution: dict[str, Any], transport_kind: str) -> dict[str, Any]:
    evidence = object_value(execution.get("bridge_route_evidence"))
    stages = list_value(evidence.get("stage_reports") or execution.get("stage_observations"))
    return {
        "result_id": f"command_result.{safe_id(execution.get('request_id') or transport_kind)}",
        "route_id": str(execution.get("route_id") or evidence.get("route_id") or ""),
        "request_id": str(execution.get("request_id") or ""),
        "command": str(execution.get("command") or ""),
        "transport_kind": transport_kind,
        "status": str(execution.get("status") or evidence.get("status") or "fail"),
        "required_stages": string_list(execution.get("required_evidence_stages")),
        "observed_stages": [
            {
                "stage": str(stage.get("stage") or ""),
                "status": str(stage.get("status") or "fail"),
                "evidence_refs": string_list(stage.get("evidence_refs")),
                "issue_codes": string_list(stage.get("issue_codes")),
            }
            for stage in stages
            if isinstance(stage, dict)
        ],
        "runtime_receipt_stream": runtime_receipt_stream(execution),
        "runtime_dispatch_delivered_count": runtime_dispatch_delivered_count(execution),
        "applied": stage_passed(stages, "applied"),
    }


def default_stream_capabilities() -> list[dict[str, Any]]:
    return [
        {
            "capability_id": "capability.command.hostess_makepad_bridge",
            "stream_id": REQUEST_STREAM_ID,
            "semantic_family": "command",
            "transport_kind": "manifold_websocket",
            "payload_plane": "json_event",
            "rate_class": "control",
            "reliability": "ordered_ack_required",
            "direction": "host_to_quest_runtime",
            "clock_policy": "host_request_runtime_receipt",
            "queue_policy": "bounded_command_queue",
            "max_rate_hz": 5,
            "high_rate_json_payload": False,
            "recommended_for": ["operator commands", "runtime receipt probes"],
            "not_for": ["camera frames", "biosignal sample streams"],
        },
        {
            "capability_id": "capability.biosignal.lsl_clocked_samples",
            "stream_id": "stream.polar_h10.ecg",
            "semantic_family": "biosignal",
            "transport_kind": "lsl",
            "payload_plane": "lsl_sample",
            "rate_class": "sample_clocked",
            "reliability": "sample_clocked_best_effort",
            "direction": "sensor_to_host_or_runtime",
            "clock_policy": "source_clock_lsl_time_correction",
            "queue_policy": "bounded_recent_samples",
            "max_rate_hz": 130,
            "high_rate_json_payload": False,
            "recommended_for": ["clocked biosignal samples"],
            "not_for": ["command authority"],
        },
        {
            "capability_id": "capability.telemetry.pose_udp",
            "stream_id": "stream.motion.object_pose",
            "semantic_family": "pose",
            "transport_kind": "udp",
            "payload_plane": "udp_datagram",
            "rate_class": "low_rate",
            "reliability": "latest_value_loss_tolerant",
            "direction": "runtime_to_broker_or_host",
            "clock_policy": "runtime_timestamp",
            "queue_policy": "drop_oldest_latest_value",
            "max_rate_hz": 90,
            "high_rate_json_payload": False,
            "recommended_for": ["low-latency pose telemetry"],
            "not_for": ["applied command feedback"],
        },
        {
            "capability_id": "capability.media.h264_tcp_binary",
            "stream_id": "stream.remote_camera.h264.left",
            "semantic_family": "media",
            "transport_kind": "tcp_binary",
            "payload_plane": "binary_media",
            "rate_class": "high_rate",
            "reliability": "ordered_bytes_backpressure_bounded",
            "direction": "quest_to_peer_or_host",
            "clock_policy": "media_frame_timestamp",
            "queue_policy": "drop_or_close_slow_peer",
            "max_rate_hz": 90,
            "high_rate_json_payload": False,
            "recommended_for": ["H.264 camera frames"],
            "not_for": ["operator command acknowledgement"],
        },
    ]


def validate_command_result(command: dict[str, Any], errors: list[str]) -> None:
    stages = list_value(command.get("observed_stages"))
    passed = {str(stage.get("stage") or "") for stage in stages if stage.get("status") == "pass"}
    if command.get("applied") is True and "runtime_accepted" not in passed:
        errors.append(
            f"command result {command.get('result_id')} cannot be applied without runtime_accepted"
        )
    if command.get("applied") is True and "applied" not in passed:
        errors.append(f"command result {command.get('result_id')} lacks applied stage evidence")
    if (
        command.get("transport_kind") == "manifold_websocket"
        and command.get("applied") is True
        and int(command.get("runtime_dispatch_delivered_count") or 0) == 0
    ):
        errors.append(
            f"command result {command.get('result_id')} requires runtime dispatch delivery"
        )


def validate_stream_capability(capability: dict[str, Any], errors: list[str]) -> None:
    if capability.get("rate_class") in {"sample_clocked", "high_rate"} and capability.get(
        "high_rate_json_payload"
    ):
        errors.append(
            f"stream capability {capability.get('capability_id')} must not carry high-rate JSON"
        )
    if capability.get("rate_class") == "high_rate" and capability.get("payload_plane") == "json_event":
        errors.append(
            f"stream capability {capability.get('capability_id')} needs a non-JSON payload plane"
        )


def report_status(
    readiness_report: dict[str, Any],
    live_execution: dict[str, Any] | None,
    fallback_execution: dict[str, Any] | None,
    issues: list[dict[str, Any]],
) -> str:
    if isinstance(fallback_execution, dict) and fallback_execution.get("status") == "pass":
        return "warn"
    if any(issue.get("severity") == "error" for issue in issues):
        return "fail"
    if isinstance(live_execution, dict) and live_execution.get("status") == "pass":
        return "pass" if readiness_report.get("status") == "pass" else "warn"
    if live_execution is None and fallback_execution is None:
        return "warn"
    return "fail"


def execution_issues(executions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for execution in executions:
        for issue in list_value(execution.get("issues")):
            if not isinstance(issue, dict):
                continue
            issues.append(
                {
                    "issue_code": str(issue.get("issue_code") or issue.get("code") or ""),
                    "severity": str(issue.get("severity") or "warning"),
                    "message": str(issue.get("message") or issue.get("issue_code") or ""),
                }
            )
    return issues


def readiness_check(report: dict[str, Any], check_id: str) -> dict[str, Any] | None:
    for check in list_value(report.get("checks")):
        if isinstance(check, dict) and check.get("check_id") == check_id:
            return check
    return None


def action_status(
    execution: dict[str, Any] | None,
    action_name: str,
    default: str,
) -> str:
    for action in list_value((execution or {}).get("setup_actions")):
        if isinstance(action, dict) and action.get("action") == action_name:
            return str(action.get("status") or default)
    return default if isinstance(execution, dict) and execution.get("status") == "pass" else "fail"


def uses_adb_forward(args: argparse.Namespace, live_execution: dict[str, Any] | None) -> bool:
    broker_stream = object_value((live_execution or {}).get("broker_stream"))
    if "adb_forward" in broker_stream:
        return bool(broker_stream.get("adb_forward"))
    return not bool(getattr(args, "no_adb_forward_broker", False))


def runtime_dispatch_delivered_count(execution: dict[str, Any] | None) -> int:
    if not isinstance(execution, dict):
        return 0
    for message in broker_messages(execution):
        if "runtime_dispatch_delivered_count" not in message:
            continue
        try:
            return int(message.get("runtime_dispatch_delivered_count") or 0)
        except (TypeError, ValueError):
            return 0
    if stage_passed(
        list_value(object_value(execution.get("bridge_route_evidence")).get("stage_reports")),
        "runtime_accepted",
    ):
        return 1
    return 0


def runtime_receipt_stream(execution: dict[str, Any]) -> str:
    broker = object_value(execution.get("broker_stream") or execution.get("broker"))
    return str(broker.get("runtime_receipt_stream") or DEFAULT_RUNTIME_RECEIPT_STREAM)


def broker_messages(execution: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(row for row in list_value(execution.get("broker_messages")) if isinstance(row, dict))
    nested = object_value(execution.get("command_execution"))
    rows.extend(row for row in list_value(nested.get("broker_messages")) if isinstance(row, dict))
    return rows


def stage_passed(stages: list[Any], stage_id: str) -> bool:
    return any(
        isinstance(stage, dict)
        and stage.get("stage") == stage_id
        and stage.get("status") == "pass"
        for stage in stages
    )


def evidence_text(check: dict[str, Any] | None) -> str:
    return str((check or {}).get("evidence") or "").strip()


def string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_id(value: Any) -> str:
    text = str(value or "session")
    chars = [char if char.isalnum() or char in {".", "_", "-"} else "-" for char in text]
    token = "".join(chars).strip("._-")
    while ".." in token:
        token = token.replace("..", ".")
    return token or "session"


__all__ = [
    "QUEST_DEVICE_LINK_SCHEMA",
    "QUEST_DEVICE_LINK_VALIDATION_SCHEMA",
    "build_device_link_report",
    "validate_device_link_report",
]
