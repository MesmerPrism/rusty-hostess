"""Shared constants and small helpers for QCL-082 RMANVID1 receiver reports."""

from __future__ import annotations

from typing import Any, BinaryIO

from tools.hostessctl.connectivity_media import MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE
from tools.hostessctl.connectivity_probe_common import object_value, round_float


RECEIVER_CAPTURE_STATS_SCHEMA = "rusty.hostess.media_stream.rmanvid1_capture_stats.v1"
RECEIVER_CAPTURE_SIDECAR_SCHEMA = "rusty.hostess.media_stream.receiver_capture_sidecar.v1"
RECEIVER_CAPTURE_RESULT_SCHEMA = "rusty.hostess.media_stream.rmanvid1_receiver_capture_result.v1"
RECEIVER_LIVE_SESSION_SCHEMA = "rusty.hostess.media_stream.rmanvid1_live_session.v1"
RECEIVER_CAPTURE_ENDPOINT_SOURCE = "hostess-rmanvid1-receiver-counter-canary"
AGENT_BOARD_MANAGER = "Agent Board"
QUEST_LEASE_RESOURCE_PREFIX = "quest:"
QUEST_LEASE_PLACEHOLDERS = {
    "",
    "<quest-lease-id>",
    "LEASE_ID_FROM_RESERVE_OUTPUT",
}
QUEST_SERIAL_PLACEHOLDERS = {
    "",
    "<quest-serial>",
    "QUEST_SERIAL_FROM_ADB_DEVICES",
}
DEFAULT_QCL082_START_SOURCE_COMMAND = "command.media_stream.start_source"
DEFAULT_QCL082_START_SOURCE_REQUEST_ID = "request.hostess.qcl082.media_stream.start_source"
DEFAULT_QCL082_START_SOURCE_EVIDENCE_ID = "evidence.hostess.qcl082.media_stream.start_source"
DEFAULT_QCL082_START_SOURCE_ROUTE_ID = "bridge_route.command.websocket.applied"
DEFAULT_QCL082_START_SOURCE_STAGES = ["sent", "transport_ok", "authority_accepted"]
RMANVID1_SCHEMA_VERSION = 1
RMANVID1_CODEC_H264 = 1
RMANVID1_STREAM_HEADER_BYTES = 32
RMANVID1_PACKET_HEADER_BYTES = 32
DEFAULT_MAX_RMANVID1_METADATA_BYTES = 262144
DEFAULT_MAX_RMANVID1_PACKET_BYTES = 4194304
DEFAULT_MAX_RMANVID1_CAPTURE_BYTES = 67108864
DEFAULT_MAX_RMANVID1_CAPTURE_PACKETS = 240
DEFAULT_RMANVID1_RECEIVER_QUEUE_CAPACITY = 48
MEDIA_CODEC_FLAG_KEY_FRAME = 1
MEDIA_CODEC_FLAG_CODEC_CONFIG = 2
LIVE_CAPTURE_KINDS = {"live_broker_stream", "live_quest_runtime_stream"}
PRODUCT_TCP_MEDIA_DIRECT_WIFI_GATE = "product_tcp_media_over_direct_wifi"
PRODUCT_TCP_MEDIA_LISTENER_FIREWALL_GATE = "product_tcp_media_listener_firewall_verified"
DEFAULT_PREVIEW_WINDOW_TITLE = "Rusty QCL-082 Camera2 direct-WiFi preview"


def receiver_result_follow_on_args(result_path: str) -> list[str]:
    return [
        "connectivity-probe",
        "run",
        "--probe-id",
        "QCL-082",
        "--media-stream-receiver-result",
        result_path,
    ]

def receiver_result_follow_on_paths(result: dict[str, Any]) -> dict[str, str]:
    result = object_value(result)
    sidecar = object_value(result.get("receiver_sidecar"))
    source = object_value(sidecar.get("source"))
    live_session = object_value(result.get("live_session"))
    quest_lease = object_value(result.get("quest_lease") or sidecar.get("lease"))

    def first_text(*values: Any) -> str:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""

    return {
        "capture_path": first_text(result.get("capture_path")),
        "sidecar_path": first_text(result.get("sidecar_path")),
        "runtime_status_path": first_text(
            result.get("runtime_status_path"),
            source.get("runtime_status_path"),
            live_session.get("execution_path"),
        ),
        "topology_report_path": first_text(
            result.get("topology_report_path"),
            source.get("topology_report_path"),
        ),
        "firewall_report_path": first_text(
            result.get("firewall_report_path"),
            source.get("firewall_report_path"),
        ),
        "quest_lease_valid": "true" if quest_lease.get("valid") is True else "false",
        "receiver_result_schema": first_text(result.get("schema")),
        "receiver_live_session_schema": first_text(live_session.get("schema")),
        "receiver_armed_before_command": "true"
        if live_session.get("receiver_armed_before_command") is True
        else "false",
    }

def endpoint_source_for_capture_kind(capture_kind: str) -> str:
    if capture_kind == "live_broker_stream":
        return MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE
    if capture_kind == "live_quest_runtime_stream":
        return "quest-runtime"
    return RECEIVER_CAPTURE_ENDPOINT_SOURCE

def normalize_topology_token(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

def check_passed(report_body: dict[str, Any], name: str) -> bool:
    for row in report_body.get("checks", []):
        check = object_value(row)
        if check.get("name") == name:
            return check.get("status") == "pass"
    return False

def drain_payload(handle: BinaryIO, payload_len: int) -> int:
    remaining = payload_len
    total = 0
    while remaining > 0:
        chunk = handle.read(min(remaining, 65536))
        if not chunk:
            break
        total += len(chunk)
        remaining -= len(chunk)
    return total

def u32_be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big", signed=False)

def u64_be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 8], "big", signed=False)

def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def arrival_gap_ms_p95(arrivals_ns: list[int]) -> float | None:
    if len(arrivals_ns) < 2:
        return None
    gaps_ms = [
        max(0.0, (arrivals_ns[index] - arrivals_ns[index - 1]) / 1_000_000.0)
        for index in range(1, len(arrivals_ns))
    ]
    if not gaps_ms:
        return None
    ordered = sorted(gaps_ms)
    selected = ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))]
    return round_float(selected)

__all__ = [
    "RECEIVER_CAPTURE_STATS_SCHEMA",
    "RECEIVER_CAPTURE_SIDECAR_SCHEMA",
    "RECEIVER_CAPTURE_RESULT_SCHEMA",
    "RECEIVER_LIVE_SESSION_SCHEMA",
    "RECEIVER_CAPTURE_ENDPOINT_SOURCE",
    "AGENT_BOARD_MANAGER",
    "QUEST_LEASE_RESOURCE_PREFIX",
    "QUEST_LEASE_PLACEHOLDERS",
    "QUEST_SERIAL_PLACEHOLDERS",
    "DEFAULT_QCL082_START_SOURCE_COMMAND",
    "DEFAULT_QCL082_START_SOURCE_REQUEST_ID",
    "DEFAULT_QCL082_START_SOURCE_EVIDENCE_ID",
    "DEFAULT_QCL082_START_SOURCE_ROUTE_ID",
    "DEFAULT_QCL082_START_SOURCE_STAGES",
    "RMANVID1_SCHEMA_VERSION",
    "RMANVID1_CODEC_H264",
    "RMANVID1_STREAM_HEADER_BYTES",
    "RMANVID1_PACKET_HEADER_BYTES",
    "DEFAULT_MAX_RMANVID1_METADATA_BYTES",
    "DEFAULT_MAX_RMANVID1_PACKET_BYTES",
    "DEFAULT_MAX_RMANVID1_CAPTURE_BYTES",
    "DEFAULT_MAX_RMANVID1_CAPTURE_PACKETS",
    "DEFAULT_RMANVID1_RECEIVER_QUEUE_CAPACITY",
    "MEDIA_CODEC_FLAG_KEY_FRAME",
    "MEDIA_CODEC_FLAG_CODEC_CONFIG",
    "LIVE_CAPTURE_KINDS",
    "PRODUCT_TCP_MEDIA_DIRECT_WIFI_GATE",
    "PRODUCT_TCP_MEDIA_LISTENER_FIREWALL_GATE",
    "DEFAULT_PREVIEW_WINDOW_TITLE",
    "receiver_result_follow_on_args",
    "receiver_result_follow_on_paths",
    "endpoint_source_for_capture_kind",
    "normalize_topology_token",
    "check_passed",
    "drain_payload",
    "u32_be",
    "u64_be",
    "int_or_none",
    "arrival_gap_ms_p95",
]
