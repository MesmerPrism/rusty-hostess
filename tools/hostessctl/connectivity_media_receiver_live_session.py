"""QCL-082 product media live-session orchestration."""

from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path
from typing import Any

from tools.hostessctl import bridge_command_live_android_routes
from tools.hostessctl.bridge_command_routes import (
    bridge_command_request_artifact,
    bridge_command_request_params,
)
from tools.hostessctl.connectivity_media_receiver_capture import capture_rmanvid1_receiver_stream
from tools.hostessctl.connectivity_media_receiver_common import (
    DEFAULT_MAX_RMANVID1_CAPTURE_BYTES,
    DEFAULT_MAX_RMANVID1_CAPTURE_PACKETS,
    DEFAULT_MAX_RMANVID1_METADATA_BYTES,
    DEFAULT_MAX_RMANVID1_PACKET_BYTES,
    DEFAULT_PREVIEW_WINDOW_TITLE,
    DEFAULT_QCL082_START_SOURCE_COMMAND,
    DEFAULT_QCL082_START_SOURCE_EVIDENCE_ID,
    DEFAULT_QCL082_START_SOURCE_REQUEST_ID,
    DEFAULT_QCL082_START_SOURCE_ROUTE_ID,
    DEFAULT_QCL082_START_SOURCE_STAGES,
    DEFAULT_RMANVID1_RECEIVER_QUEUE_CAPACITY,
    RECEIVER_LIVE_SESSION_SCHEMA,
    receiver_result_follow_on_args,
)
from tools.hostessctl.connectivity_media_receiver_lease import (
    adb_server_lifecycle_policy,
    quest_lease_summary_from_args,
)
from tools.hostessctl.connectivity_media_receiver_preflight import (
    blocked_receiver_capture_result,
    media_live_dependency_preflight_from_args,
)


def run_qcl082_product_media_live_session(
    args: Any,
    *,
    run_captured_func: Any | None = None,
    broker_client_factory: Any | None = None,
    socket_probe_func: Any | None = None,
    sleep_func: Any | None = None,
    live_android_runner: Any | None = None,
) -> int:
    """Arm the RMANVID1 receiver while the Quest start_source command runs."""

    quest_lease = quest_lease_summary_from_args(args)
    if not quest_lease["valid"]:
        live_session = {
            "schema": RECEIVER_LIVE_SESSION_SCHEMA,
            "bridge_command": str(getattr(args, "bridge_command", "") or DEFAULT_QCL082_START_SOURCE_COMMAND),
            "request_path": str(getattr(args, "start_source_request_out", "") or ""),
            "bridge_evidence_path": str(getattr(args, "bridge_evidence_out", "") or ""),
            "execution_path": str(getattr(args, "execution_out", "") or ""),
            "validation_path": str(getattr(args, "validation_out", "") or ""),
            "logcat_path": str(getattr(args, "logcat_out", "") or ""),
            "receiver_armed_before_command": False,
            "receiver_local_endpoint": "",
            "live_command_returncode": None,
            "live_command_finished": False,
            "live_command_error": "blocked before live steps because quest lease evidence is missing",
            "requires_quest_lease": True,
            "requires_adb_server_lifecycle_lease": False,
            "quest_lease": quest_lease,
            "adb_server_lifecycle_policy": adb_server_lifecycle_policy(),
        }
        result = blocked_receiver_capture_result(
            args,
            capture_kind=str(getattr(args, "capture_kind", "live_broker_stream") or "live_broker_stream"),
            quest_lease=quest_lease,
            live_session=live_session,
        )
        out = Path(getattr(args, "out"))
        result["follow_on_qcl082_args"] = receiver_result_follow_on_args(str(out))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if getattr(args, "fail_on_error", False):
            return 2
        return 0

    dependency_preflight = media_live_dependency_preflight_from_args(args)
    if not dependency_preflight["ready"]:
        live_session = {
            "schema": RECEIVER_LIVE_SESSION_SCHEMA,
            "bridge_command": str(getattr(args, "bridge_command", "") or DEFAULT_QCL082_START_SOURCE_COMMAND),
            "request_path": str(getattr(args, "start_source_request_out", "") or ""),
            "bridge_evidence_path": str(getattr(args, "bridge_evidence_out", "") or ""),
            "execution_path": str(getattr(args, "execution_out", "") or ""),
            "validation_path": str(getattr(args, "validation_out", "") or ""),
            "logcat_path": str(getattr(args, "logcat_out", "") or ""),
            "receiver_armed_before_command": False,
            "receiver_local_endpoint": "",
            "live_command_returncode": None,
            "live_command_finished": False,
            "live_command_error": "blocked before live steps because product media dependencies are missing",
            "requires_quest_lease": True,
            "requires_adb_server_lifecycle_lease": False,
            "quest_lease": quest_lease,
            "dependency_preflight": dependency_preflight,
            "adb_server_lifecycle_policy": adb_server_lifecycle_policy(),
        }
        result = blocked_receiver_capture_result(
            args,
            capture_kind=str(getattr(args, "capture_kind", "live_broker_stream") or "live_broker_stream"),
            quest_lease=quest_lease,
            close_reason="blocked_missing_product_media_dependencies",
            extra_issue_codes=list(dependency_preflight.get("issue_codes") or []),
            dependency_preflight=dependency_preflight,
            live_session=live_session,
        )
        out = Path(getattr(args, "out"))
        result["follow_on_qcl082_args"] = receiver_result_follow_on_args(str(out))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if getattr(args, "fail_on_error", False):
            return 2
        return 0

    request = bridge_command_request_artifact(
        bridge_command=str(
            getattr(args, "bridge_command", "") or DEFAULT_QCL082_START_SOURCE_COMMAND
        ),
        request_id=str(
            getattr(args, "request_id", "") or DEFAULT_QCL082_START_SOURCE_REQUEST_ID
        ),
        evidence_id=str(
            getattr(args, "evidence_id", "") or DEFAULT_QCL082_START_SOURCE_EVIDENCE_ID
        ),
        route_id=str(getattr(args, "route_id", "") or DEFAULT_QCL082_START_SOURCE_ROUTE_ID),
        required_stages=(
            getattr(args, "required_stage", None) or list(DEFAULT_QCL082_START_SOURCE_STAGES)
        ),
        params=bridge_command_request_params(args),
    )
    request_out = Path(getattr(args, "start_source_request_out"))
    request_out.parent.mkdir(parents=True, exist_ok=True)
    request_out.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    bridge_args = qcl082_live_session_bridge_args(args, request_out)
    runner = live_android_runner or bridge_command_live_android_routes.run_bridge_command_live_android
    live_state: dict[str, Any] = {
        "thread_started": False,
        "returncode": None,
        "error": "",
        "receiver_local_endpoint": "",
    }
    live_thread: threading.Thread | None = None

    def run_live_command() -> None:
        try:
            live_state["returncode"] = runner(
                bridge_args,
                run_captured_func=run_captured_func,
                broker_client_factory=broker_client_factory,
                socket_probe_func=socket_probe_func,
                sleep_func=sleep_func,
            )
        except Exception as exc:  # pragma: no cover - defensive CLI boundary
            live_state["returncode"] = 2
            live_state["error"] = str(exc)

    def on_listening(local_endpoint: str) -> None:
        nonlocal live_thread
        live_state["receiver_local_endpoint"] = local_endpoint
        live_thread = threading.Thread(
            target=run_live_command,
            name="qcl082-product-media-live-command",
            daemon=True,
        )
        live_state["thread_started"] = True
        live_thread.start()

    result = capture_rmanvid1_receiver_stream(
        bind_host=str(getattr(args, "bind_host", "0.0.0.0") or "0.0.0.0"),
        bind_port=int(getattr(args, "port", 0) or 0),
        capture_path=Path(getattr(args, "capture_out")),
        sidecar_path=Path(getattr(args, "sidecar_out")),
        timeout_seconds=float(getattr(args, "timeout_seconds", 10.0) or 10.0),
        max_capture_bytes=int(
            getattr(args, "max_bytes", DEFAULT_MAX_RMANVID1_CAPTURE_BYTES)
            or DEFAULT_MAX_RMANVID1_CAPTURE_BYTES
        ),
        max_packets=int(
            getattr(args, "max_packets", DEFAULT_MAX_RMANVID1_CAPTURE_PACKETS)
            or DEFAULT_MAX_RMANVID1_CAPTURE_PACKETS
        ),
        max_packet_bytes=int(
            getattr(args, "max_packet_bytes", DEFAULT_MAX_RMANVID1_PACKET_BYTES)
            or DEFAULT_MAX_RMANVID1_PACKET_BYTES
        ),
        max_metadata_bytes=int(
            getattr(args, "max_metadata_bytes", DEFAULT_MAX_RMANVID1_METADATA_BYTES)
            or DEFAULT_MAX_RMANVID1_METADATA_BYTES
        ),
        queue_capacity_packets=int(
            getattr(args, "queue_capacity_packets", DEFAULT_RMANVID1_RECEIVER_QUEUE_CAPACITY)
            or DEFAULT_RMANVID1_RECEIVER_QUEUE_CAPACITY
        ),
        capture_kind=str(getattr(args, "capture_kind", "live_broker_stream") or "live_broker_stream"),
        source_endpoint_source=str(getattr(args, "source_endpoint_source", "") or ""),
        source_remote_endpoint=str(getattr(args, "source_remote_endpoint", "") or ""),
        command_id=str(getattr(args, "bridge_command", "") or DEFAULT_QCL082_START_SOURCE_COMMAND),
        session_id=str(getattr(args, "session_id", "") or ""),
        runtime_status_path=str(getattr(args, "execution_out", "") or ""),
        topology_report_path=str(getattr(args, "topology_report", "") or ""),
        firewall_report_path=str(getattr(args, "firewall_report", "") or ""),
        quest_lease=quest_lease,
        listening_callback=on_listening,
        preview_ffplay=str(getattr(args, "preview_ffplay", "") or ""),
        preview_window_title=str(
            getattr(args, "preview_window_title", "") or DEFAULT_PREVIEW_WINDOW_TITLE
        ),
    )

    live_thread_timeout = max(0.0, float(getattr(args, "live_command_join_timeout_seconds", 30.0) or 30.0))
    if live_thread is not None:
        live_thread.join(timeout=live_thread_timeout)
    live_thread_alive = bool(live_thread and live_thread.is_alive())
    live_returncode = live_state.get("returncode")
    issue_codes = list(result.get("issue_codes") or [])
    if not live_state["thread_started"]:
        issue_codes.append("hostess.issue.connectivity_probe.qcl082_live_session_command_not_started")
    if live_thread_alive:
        issue_codes.append("hostess.issue.connectivity_probe.qcl082_live_session_command_timeout")
    if live_returncode not in {0, None}:
        issue_codes.append("hostess.issue.connectivity_probe.qcl082_live_session_command_failed")
    if live_returncode is None:
        issue_codes.append("hostess.issue.connectivity_probe.qcl082_live_session_command_missing_result")
    result["issue_codes"] = sorted(set(str(code) for code in issue_codes if str(code)))
    live_command_passed = live_state["thread_started"] and not live_thread_alive and live_returncode == 0
    result["status"] = "pass" if result.get("status") == "pass" and live_command_passed else "fail"
    result["live_session"] = {
        "schema": RECEIVER_LIVE_SESSION_SCHEMA,
        "bridge_command": str(getattr(args, "bridge_command", "") or DEFAULT_QCL082_START_SOURCE_COMMAND),
        "request_path": str(request_out),
        "bridge_evidence_path": str(getattr(args, "bridge_evidence_out", "") or ""),
        "execution_path": str(getattr(args, "execution_out", "") or ""),
        "validation_path": str(getattr(args, "validation_out", "") or ""),
        "logcat_path": str(getattr(args, "logcat_out", "") or ""),
        "receiver_armed_before_command": live_state["thread_started"],
        "receiver_local_endpoint": str(live_state["receiver_local_endpoint"] or ""),
        "live_command_returncode": live_returncode,
        "live_command_finished": bool(live_state["thread_started"] and not live_thread_alive),
        "live_command_error": str(live_state["error"] or ""),
        "requires_quest_lease": True,
        "requires_adb_server_lifecycle_lease": False,
        "quest_lease": quest_lease,
        "adb_server_lifecycle_policy": adb_server_lifecycle_policy(),
    }

    out = Path(getattr(args, "out"))
    result["follow_on_qcl082_args"] = receiver_result_follow_on_args(str(out))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if getattr(args, "fail_on_error", False) and result.get("status") != "pass":
        return 2
    return 0

def qcl082_live_session_bridge_args(args: Any, request_out: Path) -> argparse.Namespace:
    return argparse.Namespace(
        input=str(request_out),
        out=str(getattr(args, "bridge_evidence_out", "") or ""),
        execution_out=str(getattr(args, "execution_out", "") or ""),
        validation_out=str(getattr(args, "validation_out", "") or ""),
        logcat_out=str(getattr(args, "logcat_out", "") or ""),
        route_descriptor=str(getattr(args, "route_descriptor", "") or ""),
        adb=str(getattr(args, "adb", "") or ""),
        serial=str(getattr(args, "serial", "") or ""),
        broker_package=str(getattr(args, "broker_package", "") or ""),
        broker_activity=str(getattr(args, "broker_activity", "") or ""),
        broker_host=str(getattr(args, "broker_host", "127.0.0.1") or "127.0.0.1"),
        broker_port=int(getattr(args, "broker_port", 8765) or 8765),
        broker_local_port=int(getattr(args, "broker_local_port", 18765) or 18765),
        broker_path=str(getattr(args, "broker_path", "/manifold/v1/events") or "/manifold/v1/events"),
        connect_timeout_seconds=float(getattr(args, "connect_timeout_seconds", 5.0) or 5.0),
        wait_seconds=float(getattr(args, "wait_seconds", 15.0) or 15.0),
        runtime_receipt_stream=str(
            getattr(args, "runtime_receipt_stream", "stream.hostess.makepad.bridge_command.receipt")
            or "stream.hostess.makepad.bridge_command.receipt"
        ),
        no_runtime_receipt_subscribe=bool(getattr(args, "no_runtime_receipt_subscribe", False)),
        makepad_package=str(getattr(args, "makepad_package", "") or ""),
        makepad_activity=str(getattr(args, "makepad_activity", "") or ""),
        broker_process_wait_seconds=float(getattr(args, "broker_process_wait_seconds", 8.0) or 8.0),
        makepad_process_wait_seconds=float(getattr(args, "makepad_process_wait_seconds", 8.0) or 8.0),
        socket_wait_seconds=float(getattr(args, "socket_wait_seconds", 8.0) or 8.0),
        launch_settle_seconds=float(getattr(args, "launch_settle_seconds", 8.0) or 8.0),
        runtime_subscriber_retry_count=int(getattr(args, "runtime_subscriber_retry_count", 1) or 1),
        runtime_subscriber_retry_wait_seconds=float(
            getattr(args, "runtime_subscriber_retry_wait_seconds", 5.0) or 5.0
        ),
        no_launch_broker=bool(getattr(args, "no_launch_broker", False)),
        no_launch_makepad=bool(getattr(args, "no_launch_makepad", False)),
        no_wait_broker_process=bool(getattr(args, "no_wait_broker_process", False)),
        no_wait_makepad_process=bool(getattr(args, "no_wait_makepad_process", False)),
        no_adb_forward_broker=bool(getattr(args, "no_adb_forward_broker", False)),
    )

__all__ = [
    "run_qcl082_product_media_live_session",
    "qcl082_live_session_bridge_args",
]
