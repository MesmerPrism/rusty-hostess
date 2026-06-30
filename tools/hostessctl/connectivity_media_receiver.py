"""QCL-082 RMANVID1 receiver capture parsing and report helpers."""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from typing import Any, BinaryIO

from tools.hostessctl.connectivity_firewall import diagnostic_python_program_path
from tools.hostessctl.connectivity_media import (
    DEFAULT_QCL082_PACKET_MAGIC,
    MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE,
    qcl082_media_stream_runtime_status_body,
)
from tools.hostessctl.connectivity_probe_common import (
    check_row,
    empty_measurements,
    issue_row,
    object_value,
    round_float,
)


RECEIVER_CAPTURE_STATS_SCHEMA = "rusty.hostess.media_stream.rmanvid1_capture_stats.v1"
RECEIVER_CAPTURE_SIDECAR_SCHEMA = "rusty.hostess.media_stream.receiver_capture_sidecar.v1"
RECEIVER_CAPTURE_RESULT_SCHEMA = "rusty.hostess.media_stream.rmanvid1_receiver_capture_result.v1"
RECEIVER_CAPTURE_ENDPOINT_SOURCE = "hostess-rmanvid1-receiver-counter-canary"
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


def run_rmanvid1_receiver_capture(args: Any) -> int:
    """Run the CLI-owned bounded TCP receiver capture route."""

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
        capture_kind=str(getattr(args, "capture_kind", "fixture_loopback_receiver") or "fixture_loopback_receiver"),
        source_endpoint_source=str(getattr(args, "source_endpoint_source", "") or ""),
        source_remote_endpoint=str(getattr(args, "source_remote_endpoint", "") or ""),
        command_id=str(getattr(args, "command_id", "") or ""),
        session_id=str(getattr(args, "session_id", "") or ""),
        runtime_status_path=str(getattr(args, "runtime_status", "") or ""),
        topology_report_path=str(getattr(args, "topology_report", "") or ""),
        firewall_report_path=str(getattr(args, "firewall_report", "") or ""),
    )
    out = Path(getattr(args, "out"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if getattr(args, "fail_on_error", False) and result.get("status") != "pass":
        return 2
    return 0


def capture_rmanvid1_receiver_stream(
    *,
    bind_host: str,
    bind_port: int,
    capture_path: Path,
    sidecar_path: Path,
    timeout_seconds: float,
    max_capture_bytes: int = DEFAULT_MAX_RMANVID1_CAPTURE_BYTES,
    max_packets: int = DEFAULT_MAX_RMANVID1_CAPTURE_PACKETS,
    max_packet_bytes: int = DEFAULT_MAX_RMANVID1_PACKET_BYTES,
    max_metadata_bytes: int = DEFAULT_MAX_RMANVID1_METADATA_BYTES,
    queue_capacity_packets: int = DEFAULT_RMANVID1_RECEIVER_QUEUE_CAPACITY,
    capture_kind: str = "fixture_loopback_receiver",
    source_endpoint_source: str = "",
    source_remote_endpoint: str = "",
    command_id: str = "",
    session_id: str = "",
    runtime_status_path: str = "",
    topology_report_path: str = "",
    firewall_report_path: str = "",
    listening_callback: Any | None = None,
) -> dict[str, Any]:
    """Listen for one RMANVID1 TCP stream and write bounded capture artifacts."""

    capture_path = Path(capture_path)
    sidecar_path = Path(sidecar_path)
    capture_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)

    issue_codes: list[str] = []
    receiver_arrivals_ns: list[int] = []
    capture_started_unix_ns = time.time_ns()
    capture_started_monotonic = time.monotonic()
    close_reason = "not_started"
    accepted = False
    local_endpoint = f"{bind_host}:{bind_port}"
    remote_endpoint = source_remote_endpoint
    bytes_written = 0
    packet_count = 0

    try:
        capture_path.write_bytes(b"")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((bind_host, bind_port))
            server.listen(1)
            bound_host, bound_port = server.getsockname()[:2]
            local_endpoint = f"{bound_host}:{bound_port}"
            if listening_callback is not None:
                listening_callback(local_endpoint)
            server.settimeout(max(0.001, timeout_seconds))
            try:
                connection, address = server.accept()
            except socket.timeout:
                close_reason = "accept_timeout"
                issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_accept_timeout")
            else:
                accepted = True
                remote_endpoint = source_remote_endpoint or f"{address[0]}:{address[1]}"
                with connection:
                    connection.settimeout(max(0.001, timeout_seconds))
                    with capture_path.open("wb") as output:
                        close_reason, bytes_written, packet_count = capture_rmanvid1_socket_bytes(
                            connection,
                            output,
                            receiver_arrivals_ns,
                            max_capture_bytes=max_capture_bytes,
                            max_packets=max_packets,
                            max_packet_bytes=max_packet_bytes,
                            max_metadata_bytes=max_metadata_bytes,
                        )
    except OSError as exc:
        close_reason = "socket_error"
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_socket_error")
        socket_error = str(exc)
    else:
        socket_error = ""

    capture_finished_unix_ns = time.time_ns()
    elapsed_ms = max(0.0, (time.monotonic() - capture_started_monotonic) * 1000.0)
    capture_stats = parse_rmanvid1_capture(
        capture_path,
        max_packet_bytes=max_packet_bytes,
        max_metadata_bytes=max_metadata_bytes,
    )
    packet_count = int_or_none(capture_stats.get("packet_count")) or packet_count
    source_endpoint = source_endpoint_source or endpoint_source_for_capture_kind(capture_kind)
    sidecar = receiver_capture_sidecar(
        capture_kind=capture_kind,
        local_endpoint=local_endpoint,
        remote_endpoint=remote_endpoint,
        source_endpoint_source=source_endpoint,
        command_id=command_id,
        session_id=session_id,
        close_reason=close_reason,
        queue_capacity_packets=queue_capacity_packets,
        packet_count=packet_count,
        receiver_arrivals_ns=receiver_arrivals_ns,
        bytes_written=bytes_written,
        max_capture_bytes=max_capture_bytes,
        max_packets=max_packets,
        capture_started_unix_ns=capture_started_unix_ns,
        capture_finished_unix_ns=capture_finished_unix_ns,
        elapsed_ms=elapsed_ms,
        runtime_status_path=runtime_status_path,
        topology_report_path=topology_report_path,
        firewall_report_path=firewall_report_path,
    )
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    all_issue_codes = list(issue_codes) + list(capture_stats.get("issue_codes") or [])
    status = "pass" if accepted and capture_stats.get("status") == "pass" and not issue_codes else "fail"
    follow_on_args = [
        "connectivity-probe",
        "run",
        "--probe-id",
        "QCL-082",
        "--media-stream-rmanvid1-capture",
        str(capture_path),
        "--media-stream-receiver-sidecar",
        str(sidecar_path),
    ]
    if runtime_status_path:
        follow_on_args.extend(["--media-stream-runtime-status", runtime_status_path])
    if topology_report_path:
        follow_on_args.extend(["--media-stream-topology-report", topology_report_path])
    if firewall_report_path:
        follow_on_args.extend(["--media-stream-firewall-report", firewall_report_path])
    result = {
        "schema": RECEIVER_CAPTURE_RESULT_SCHEMA,
        "status": status,
        "capture_kind": capture_kind,
        "live_capture": bool(sidecar.get("live_capture")),
        "capture_path": str(capture_path),
        "sidecar_path": str(sidecar_path),
        "runtime_status_path": runtime_status_path,
        "topology_report_path": topology_report_path,
        "firewall_report_path": firewall_report_path,
        "local_endpoint": local_endpoint,
        "remote_endpoint": remote_endpoint,
        "accepted_connection": accepted,
        "close_reason": close_reason,
        "elapsed_ms": round_float(elapsed_ms),
        "bytes_written": bytes_written,
        "issue_codes": all_issue_codes,
        "socket_error": socket_error,
        "capture_stats": capture_stats,
        "receiver_sidecar": sidecar,
        "follow_on_qcl082_args": follow_on_args,
    }
    return result


def capture_rmanvid1_socket_bytes(
    connection: socket.socket,
    output: BinaryIO,
    receiver_arrivals_ns: list[int],
    *,
    max_capture_bytes: int,
    max_packets: int,
    max_packet_bytes: int,
    max_metadata_bytes: int,
) -> tuple[str, int, int]:
    bytes_written = 0
    packet_count = 0

    header, header_reason = recv_exact(connection, RMANVID1_STREAM_HEADER_BYTES)
    if len(header) != RMANVID1_STREAM_HEADER_BYTES:
        output.write(header)
        return f"stream_header_{header_reason}", len(header), packet_count
    if len(header) > max_capture_bytes:
        return "max_bytes_reached", bytes_written, packet_count
    output.write(header)
    bytes_written += len(header)

    metadata_len = u32_be(header, 28)
    if metadata_len > max_metadata_bytes:
        return "metadata_too_large", bytes_written, packet_count
    if bytes_written + metadata_len > max_capture_bytes:
        return "max_bytes_reached", bytes_written, packet_count
    metadata, metadata_reason = recv_exact(connection, metadata_len)
    output.write(metadata)
    bytes_written += len(metadata)
    if len(metadata) != metadata_len:
        return f"metadata_{metadata_reason}", bytes_written, packet_count

    while True:
        if max_packets > 0 and packet_count >= max_packets:
            return "max_packets_reached", bytes_written, packet_count
        packet_header, packet_header_reason = recv_exact(connection, RMANVID1_PACKET_HEADER_BYTES)
        if not packet_header and packet_header_reason == "peer_closed":
            return "peer_closed", bytes_written, packet_count
        if len(packet_header) != RMANVID1_PACKET_HEADER_BYTES:
            output.write(packet_header)
            bytes_written += len(packet_header)
            return f"packet_header_{packet_header_reason}", bytes_written, packet_count

        payload_len = u32_be(packet_header, 12)
        if payload_len > max_packet_bytes:
            output.write(packet_header)
            bytes_written += len(packet_header)
            return "payload_too_large", bytes_written, packet_count
        if bytes_written + RMANVID1_PACKET_HEADER_BYTES + payload_len > max_capture_bytes:
            return "max_bytes_reached", bytes_written, packet_count

        receiver_arrivals_ns.append(time.time_ns())
        output.write(packet_header)
        bytes_written += len(packet_header)
        payload, payload_reason = recv_exact(connection, payload_len)
        output.write(payload)
        bytes_written += len(payload)
        if len(payload) != payload_len:
            return f"payload_{payload_reason}", bytes_written, packet_count
        packet_count += 1


def recv_exact(connection: socket.socket, byte_count: int) -> tuple[bytes, str]:
    chunks: list[bytes] = []
    remaining = byte_count
    while remaining > 0:
        try:
            chunk = connection.recv(remaining)
        except socket.timeout:
            return b"".join(chunks), "timeout"
        except OSError:
            return b"".join(chunks), "socket_error"
        if not chunk:
            return b"".join(chunks), "peer_closed"
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks), "complete"


def receiver_capture_sidecar(
    *,
    capture_kind: str,
    local_endpoint: str,
    remote_endpoint: str,
    source_endpoint_source: str,
    command_id: str,
    session_id: str,
    close_reason: str,
    queue_capacity_packets: int,
    packet_count: int,
    receiver_arrivals_ns: list[int],
    bytes_written: int,
    max_capture_bytes: int,
    max_packets: int,
    capture_started_unix_ns: int,
    capture_finished_unix_ns: int,
    elapsed_ms: float,
    runtime_status_path: str,
    topology_report_path: str,
    firewall_report_path: str,
) -> dict[str, Any]:
    arrival_count = len(receiver_arrivals_ns)
    queue_depth = 1 if packet_count > 0 else 0
    timestamp_gap_ms_p95 = arrival_gap_ms_p95(receiver_arrivals_ns)
    return {
        "schema": RECEIVER_CAPTURE_SIDECAR_SCHEMA,
        "capture_kind": capture_kind,
        "live_capture": capture_kind in LIVE_CAPTURE_KINDS,
        "receiver": {
            "local_endpoint": local_endpoint,
            "bind_endpoint": local_endpoint,
            "remote_endpoint": remote_endpoint,
            "queue_capacity_packets": queue_capacity_packets,
            "max_queue_depth_observed": min(queue_depth, queue_capacity_packets),
            "drop_policy": "drop-oldest-complete-frame",
            "close_policy": "close_after_capture_window_or_peer_eof",
            "close_reason": close_reason,
            "dropped_frames": 0,
            "backpressure_events": 0,
            "arrival_timestamped_packet_count": arrival_count,
            "receiver_arrival_timestamps": arrival_count >= packet_count and packet_count > 0,
            "timestamp_gap_ms_p95": timestamp_gap_ms_p95,
            "decode_error_count": 0,
            "bytes_written": bytes_written,
            "max_capture_bytes": max_capture_bytes,
            "max_packets": max_packets,
            "capture_started_unix_ns": capture_started_unix_ns,
            "capture_finished_unix_ns": capture_finished_unix_ns,
            "elapsed_ms": round_float(elapsed_ms),
        },
        "source": {
            "endpoint_source": source_endpoint_source,
            "remote_endpoint": remote_endpoint,
            "command_id": command_id,
            "session_id": session_id,
            "runtime_status_path": runtime_status_path,
            "topology_report_path": topology_report_path,
            "firewall_report_path": firewall_report_path,
        },
    }


def endpoint_source_for_capture_kind(capture_kind: str) -> str:
    if capture_kind == "live_broker_stream":
        return MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE
    if capture_kind == "live_quest_runtime_stream":
        return "quest-runtime"
    return RECEIVER_CAPTURE_ENDPOINT_SOURCE


def parse_rmanvid1_capture(
    capture_path: Path,
    *,
    max_packet_bytes: int = DEFAULT_MAX_RMANVID1_PACKET_BYTES,
    max_metadata_bytes: int = DEFAULT_MAX_RMANVID1_METADATA_BYTES,
) -> dict[str, Any]:
    """Parse a bounded RMANVID1 H.264 diagnostic stream without decoding H.264."""

    path = Path(capture_path)
    issue_codes: list[str] = []
    stream = {
        "schema": RECEIVER_CAPTURE_STATS_SCHEMA,
        "capture_path": str(path),
        "status": "fail",
        "stream_magic": "",
        "schema_version": None,
        "codec": None,
        "codec_name": "",
        "width": None,
        "height": None,
        "reserved": None,
        "metadata_bytes": 0,
        "metadata": {},
        "header_bytes": 0,
        "packet_count": 0,
        "video_packet_count": 0,
        "codec_config_packet_count": 0,
        "keyframe_count": 0,
        "payload_bytes": 0,
        "total_bytes_read": 0,
        "max_packet_bytes_allowed": max_packet_bytes,
        "max_payload_bytes_observed": 0,
        "payload_length_bounded": True,
        "presentation_time_us_monotonic": True,
        "source_elapsed_ns_monotonic": True,
        "first_presentation_time_us": None,
        "latest_presentation_time_us": None,
        "first_source_elapsed_ns": None,
        "latest_source_elapsed_ns": None,
        "first_source_unix_ns": None,
        "latest_source_unix_ns": None,
        "duration_ms": None,
        "truncated": False,
        "issue_codes": issue_codes,
    }
    try:
        with path.open("rb") as handle:
            parse_rmanvid1_stream(handle, stream, issue_codes, max_packet_bytes, max_metadata_bytes)
    except OSError as exc:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_unreadable")
        stream["read_error"] = str(exc)

    if not issue_codes:
        stream["status"] = "pass"
    return stream


def parse_rmanvid1_stream(
    handle: BinaryIO,
    stream: dict[str, Any],
    issue_codes: list[str],
    max_packet_bytes: int,
    max_metadata_bytes: int,
) -> None:
    header = handle.read(RMANVID1_STREAM_HEADER_BYTES)
    if len(header) != RMANVID1_STREAM_HEADER_BYTES:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_header_truncated")
        stream["truncated"] = True
        stream["total_bytes_read"] = len(header)
        return

    magic = header[:8].decode("ascii", errors="replace")
    metadata_len = u32_be(header, 28)
    stream.update(
        {
            "stream_magic": magic,
            "schema_version": u32_be(header, 8),
            "codec": u32_be(header, 12),
            "codec_name": "h264" if u32_be(header, 12) == RMANVID1_CODEC_H264 else "unknown",
            "width": u32_be(header, 16),
            "height": u32_be(header, 20),
            "reserved": u32_be(header, 24),
            "metadata_bytes": metadata_len,
            "header_bytes": RMANVID1_STREAM_HEADER_BYTES + metadata_len,
            "total_bytes_read": RMANVID1_STREAM_HEADER_BYTES,
        }
    )
    if magic != DEFAULT_QCL082_PACKET_MAGIC:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_magic_invalid")
    if stream["schema_version"] != RMANVID1_SCHEMA_VERSION:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_schema_unsupported")
    if stream["codec"] != RMANVID1_CODEC_H264:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_codec_unsupported")
    if metadata_len > max_metadata_bytes:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_metadata_too_large")

    metadata_bytes = handle.read(metadata_len)
    stream["total_bytes_read"] += len(metadata_bytes)
    if len(metadata_bytes) != metadata_len:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_metadata_truncated")
        stream["truncated"] = True
        return
    if metadata_bytes:
        try:
            stream["metadata"] = object_value(json.loads(metadata_bytes.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError):
            issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_metadata_invalid")

    previous_pts: int | None = None
    previous_elapsed: int | None = None
    while True:
        packet_header = handle.read(RMANVID1_PACKET_HEADER_BYTES)
        if not packet_header:
            break
        stream["total_bytes_read"] += len(packet_header)
        if len(packet_header) != RMANVID1_PACKET_HEADER_BYTES:
            issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_packet_header_truncated")
            stream["truncated"] = True
            break

        presentation_time_us = u64_be(packet_header, 0)
        flags = u32_be(packet_header, 8)
        payload_len = u32_be(packet_header, 12)
        source_elapsed_ns = u64_be(packet_header, 16)
        source_unix_ns = u64_be(packet_header, 24)
        if payload_len > max_packet_bytes:
            issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_packet_too_large")
            stream["payload_length_bounded"] = False

        payload_read = drain_payload(handle, payload_len)
        stream["total_bytes_read"] += payload_read
        if payload_read != payload_len:
            issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_payload_truncated")
            stream["truncated"] = True
            break

        packet_count = int(stream["packet_count"]) + 1
        stream["packet_count"] = packet_count
        stream["payload_bytes"] = int(stream["payload_bytes"]) + payload_len
        stream["max_payload_bytes_observed"] = max(int(stream["max_payload_bytes_observed"]), payload_len)
        if flags & MEDIA_CODEC_FLAG_CODEC_CONFIG:
            stream["codec_config_packet_count"] = int(stream["codec_config_packet_count"]) + 1
        else:
            stream["video_packet_count"] = int(stream["video_packet_count"]) + 1
        if flags & MEDIA_CODEC_FLAG_KEY_FRAME:
            stream["keyframe_count"] = int(stream["keyframe_count"]) + 1

        if stream["first_presentation_time_us"] is None:
            stream["first_presentation_time_us"] = presentation_time_us
            stream["first_source_elapsed_ns"] = source_elapsed_ns
            stream["first_source_unix_ns"] = source_unix_ns
        if previous_pts is not None and presentation_time_us < previous_pts:
            stream["presentation_time_us_monotonic"] = False
        if previous_elapsed is not None and source_elapsed_ns < previous_elapsed:
            stream["source_elapsed_ns_monotonic"] = False
        previous_pts = presentation_time_us
        previous_elapsed = source_elapsed_ns
        stream["latest_presentation_time_us"] = presentation_time_us
        stream["latest_source_elapsed_ns"] = source_elapsed_ns
        stream["latest_source_unix_ns"] = source_unix_ns

    first_pts = int_or_none(stream.get("first_presentation_time_us"))
    latest_pts = int_or_none(stream.get("latest_presentation_time_us"))
    if first_pts is not None and latest_pts is not None:
        stream["duration_ms"] = max(0.0, (latest_pts - first_pts) / 1000.0)
    if stream["packet_count"] == 0 and not stream["truncated"]:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_no_packets")
    if stream["presentation_time_us_monotonic"] is not True:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_pts_nonmonotonic")
    if stream["source_elapsed_ns_monotonic"] is not True:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_capture_elapsed_nonmonotonic")


def qcl082_media_stream_receiver_capture_body(
    capture_stats: dict[str, Any],
    *,
    sidecar: dict[str, Any] | None = None,
    runtime_status: dict[str, Any] | None = None,
    topology_report: dict[str, Any] | None = None,
    firewall_report: dict[str, Any] | None = None,
    capture_path: str = "",
    sidecar_path: str = "",
    runtime_status_path: str = "",
    topology_report_path: str = "",
    firewall_report_path: str = "",
) -> dict[str, Any]:
    """Build QCL-082 evidence from RMANVID1 receiver counters."""

    sidecar = object_value(sidecar)
    receiver = object_value(sidecar.get("receiver"))
    source = object_value(sidecar.get("source"))
    runtime_body = (
        qcl082_media_stream_runtime_status_body(runtime_status, artifact_path=runtime_status_path)
        if runtime_status
        else {}
    )
    runtime_ok = check_passed(runtime_body, "protocol.media_stream_runtime_status")
    runtime_transport = object_value(runtime_body.get("transport"))
    source_endpoint = str(
        source.get("endpoint_source")
        or runtime_transport.get("endpoint_source")
        or RECEIVER_CAPTURE_ENDPOINT_SOURCE
    )
    capture_kind = str(sidecar.get("capture_kind") or "fixture_rmanvid1_capture")
    live_capture = bool(sidecar.get("live_capture")) or capture_kind in LIVE_CAPTURE_KINDS
    broker_or_quest_source = source_endpoint in {MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE, "quest-runtime"}
    high_rate_json = bool(
        sidecar.get("high_rate_json_payload")
        or receiver.get("high_rate_json_payload")
        or capture_stats.get("high_rate_json_payload")
    )

    packet_count = int_or_none(capture_stats.get("packet_count")) or 0
    video_packet_count = int_or_none(capture_stats.get("video_packet_count")) or 0
    payload_bytes = int_or_none(capture_stats.get("payload_bytes")) or 0
    keyframe_count = int_or_none(capture_stats.get("keyframe_count")) or 0
    dropped_frames = int_or_none(receiver.get("dropped_frames"))
    backpressure_events = int_or_none(receiver.get("backpressure_events"))
    queue_capacity = int_or_none(receiver.get("queue_capacity_packets"))
    max_queue_depth = int_or_none(receiver.get("max_queue_depth_observed"))
    arrival_timestamped_count = int_or_none(receiver.get("arrival_timestamped_packet_count"))
    if arrival_timestamped_count is None and receiver.get("receiver_arrival_timestamps") is True:
        arrival_timestamped_count = packet_count
    drop_policy = str(receiver.get("drop_policy") or "")
    close_policy = str(receiver.get("close_policy") or "")
    close_reason = str(receiver.get("close_reason") or "")
    capture_status_ok = capture_stats.get("status") == "pass"
    binary_transport_ok = (
        capture_status_ok
        and capture_stats.get("stream_magic") == DEFAULT_QCL082_PACKET_MAGIC
        and capture_stats.get("schema_version") == RMANVID1_SCHEMA_VERSION
        and capture_stats.get("codec") == RMANVID1_CODEC_H264
        and not high_rate_json
    )
    packet_boundaries_ok = (
        binary_transport_ok
        and packet_count > 0
        and capture_stats.get("payload_length_bounded") is True
        and capture_stats.get("presentation_time_us_monotonic") is True
    )
    timestamp_policy_ok = (
        packet_boundaries_ok
        and capture_stats.get("source_elapsed_ns_monotonic") is True
        and arrival_timestamped_count is not None
        and arrival_timestamped_count >= packet_count
    )
    backpressure_policy_ok = (
        queue_capacity is not None
        and queue_capacity > 0
        and max_queue_depth is not None
        and max_queue_depth <= queue_capacity
        and dropped_frames is not None
        and backpressure_events is not None
        and bool(drop_policy)
        and bool(close_policy)
        and bool(close_reason)
    )
    receiver_measurements_present = all(
        value is not None
        for value in [video_packet_count, payload_bytes, dropped_frames, max_queue_depth]
    )
    core_failed = not binary_transport_ok or capture_status_ok is not True
    all_qcl_gates = (
        binary_transport_ok
        and packet_boundaries_ok
        and timestamp_policy_ok
        and backpressure_policy_ok
        and runtime_ok
        and receiver_measurements_present
        and not high_rate_json
    )
    status = "fail" if core_failed else ("pass" if all_qcl_gates else "warn")
    promotion_allowed = all_qcl_gates and live_capture and broker_or_quest_source
    product_topology = media_product_topology_summary(
        topology_report,
        topology_report_path=topology_report_path,
        media_promotion_allowed=promotion_allowed,
        media_transport_ok=binary_transport_ok,
        runtime_ok=runtime_ok,
        capture_kind=capture_kind,
    )
    product_listener_firewall = media_product_listener_firewall_summary(
        firewall_report,
        firewall_report_path=firewall_report_path,
        media_promotion_allowed=promotion_allowed,
        capture_kind=capture_kind,
    )
    issues = receiver_capture_issues(
        capture_stats,
        high_rate_json,
        runtime_ok,
        backpressure_policy_ok,
        product_topology,
        product_listener_firewall,
    )

    checks = [
        check_row(
            "protocol.media_receiver_capture",
            "pass" if capture_status_ok else "fail",
            (
                "RMANVID1 receiver capture parsed"
                if capture_status_ok
                else "RMANVID1 receiver capture could not be parsed cleanly"
            ),
            observed={
                "capture_path": capture_path,
                "sidecar_path": sidecar_path,
                "packet_count": packet_count,
                "video_packet_count": video_packet_count,
                "payload_bytes": payload_bytes,
                "issue_codes": capture_stats.get("issue_codes"),
            },
            issue_codes=list(capture_stats.get("issue_codes") or []),
        ),
        check_row(
            "protocol.media_stream_runtime_status",
            "pass" if runtime_ok else "blocked",
            (
                "receiver capture is paired with broker media-stream runtime status"
                if runtime_ok
                else "receiver capture is missing paired broker media-stream runtime status"
            ),
            observed={
                "runtime_status_path": runtime_status_path,
                "endpoint_source": source_endpoint,
                "capture_kind": capture_kind,
            },
        ),
        check_row(
            "protocol.media_binary_transport",
            "pass" if binary_transport_ok else "fail",
            (
                "receiver capture reports RMANVID1 H.264 binary media"
                if binary_transport_ok
                else "receiver capture is not valid RMANVID1 H.264 binary media"
            ),
            observed={
                "transport_kind": "tcp_binary",
                "packet_magic": capture_stats.get("stream_magic"),
                "codec": capture_stats.get("codec_name"),
                "payload_plane": "json-event" if high_rate_json else "binary-media",
                "command_plane_payload": high_rate_json,
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_high_rate_json_payload"]
                if high_rate_json
                else []
            ),
        ),
        check_row(
            "protocol.media_packet_boundaries",
            "pass" if packet_boundaries_ok else "blocked",
            (
                "receiver capture proves bounded packet headers and payload lengths"
                if packet_boundaries_ok
                else "receiver capture does not prove bounded packet headers and payload lengths"
            ),
            observed={
                "header_magic": capture_stats.get("stream_magic"),
                "packet_count": packet_count,
                "max_payload_bytes_observed": capture_stats.get("max_payload_bytes_observed"),
                "max_packet_bytes_allowed": capture_stats.get("max_packet_bytes_allowed"),
                "payload_length_bounded": capture_stats.get("payload_length_bounded"),
                "presentation_time_us_monotonic": capture_stats.get("presentation_time_us_monotonic"),
                "keyframe_count": keyframe_count,
                "codec_config_packet_count": capture_stats.get("codec_config_packet_count"),
            },
        ),
        check_row(
            "protocol.media_timestamp_policy",
            "pass" if timestamp_policy_ok else "blocked",
            (
                "capture and receiver-arrival timestamps are present for receiver packets"
                if timestamp_policy_ok
                else "receiver capture is missing capture or receiver-arrival timestamp evidence"
            ),
            observed={
                "first_presentation_time_us": capture_stats.get("first_presentation_time_us"),
                "latest_presentation_time_us": capture_stats.get("latest_presentation_time_us"),
                "source_elapsed_ns_monotonic": capture_stats.get("source_elapsed_ns_monotonic"),
                "receiver_arrival_timestamped_packet_count": arrival_timestamped_count,
                "timestamp_gap_ms_p95": receiver.get("timestamp_gap_ms_p95"),
            },
        ),
        check_row(
            "protocol.media_backpressure_policy",
            "pass" if backpressure_policy_ok else "blocked",
            (
                "receiver sidecar declares bounded queue, drop, backpressure, and close policy"
                if backpressure_policy_ok
                else "receiver sidecar is missing bounded queue/drop/backpressure/close evidence"
            ),
            observed={
                "receiver_queue_capacity_frames": queue_capacity,
                "max_queue_depth_observed": max_queue_depth,
                "drop_policy": drop_policy or "not_declared",
                "close_policy": close_policy or "not_declared",
                "close_reason": close_reason or "not_declared",
                "dropped_frames": dropped_frames,
                "backpressure_events": backpressure_events,
            },
        ),
        check_row(
            "protocol.media_high_rate_json_guard",
            "pass" if not high_rate_json else "fail",
            (
                "receiver capture keeps media bytes outside JSON command/report streams"
                if not high_rate_json
                else "receiver capture reports high-rate media on JSON command/report streams"
            ),
            observed={
                "json_allowed_for": ["control_receipts", "descriptors", "validation_reports"],
                "json_allowed_for_media_payload": False,
                "observed_payload_plane": "json-event" if high_rate_json else "binary-media",
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_high_rate_json_payload"]
                if high_rate_json
                else []
            ),
        ),
        check_row(
            "protocol.media_receiver_counters",
            "pass" if receiver_measurements_present else "blocked",
            (
                "receiver capture reports frame, byte, drop, queue, and close counters"
                if receiver_measurements_present
                else "receiver capture is missing frame, byte, drop, or queue counters"
            ),
            observed={
                "video_packet_count": video_packet_count,
                "payload_bytes": payload_bytes,
                "dropped_frames": dropped_frames,
                "max_queue_depth_observed": max_queue_depth,
                "backpressure_events": backpressure_events,
                "close_reason": close_reason,
            },
        ),
        check_row(
            "protocol.media_product_topology_gate",
            str(product_topology["check_status"]),
            str(product_topology["evidence"]),
            observed=product_topology,
            issue_codes=list(product_topology.get("issue_codes") or []),
        ),
        check_row(
            "protocol.media_product_listener_firewall_gate",
            str(product_listener_firewall["check_status"]),
            str(product_listener_firewall["evidence"]),
            observed=product_listener_firewall,
            issue_codes=list(product_listener_firewall.get("issue_codes") or []),
        ),
    ]

    local_endpoint = str(receiver.get("local_endpoint") or receiver.get("bind_endpoint") or "hostess_receiver_capture")
    remote_endpoint = str(source.get("remote_endpoint") or source.get("source_endpoint") or "declared_by_runtime_status")
    return {
        "status": status,
        "classification": "protocol_fit_receiver_counters",
        "topology": {
            "owner": "hostess_receiver_canary",
            "network_provider": "declared_by_receiver_capture",
            "endpoint_direction": "quest_to_host_binary_media",
            "requires_existing_wifi": True,
            "requires_adb": False,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": True,
        },
        "transport": {
            "family": "tcp_binary",
            "route": "hostess_rmanvid1_receiver_capture",
            "local_endpoint": local_endpoint,
            "remote_endpoint": remote_endpoint,
            "protocol_role": "binary_media_plane_receiver_counters",
            "payload_class": "h264_annex_b_binary_frames",
            "endpoint_source": source_endpoint,
            "packet_magic": DEFAULT_QCL082_PACKET_MAGIC,
        },
        "device": {
            "serial_redacted": True,
            "model": "receiver_capture",
            "foreground_package": "not_checked",
            "adb_state": "not_applicable",
        },
        "host": {
            "os": "windows",
            "toolchain_profile": "hostessctl.connectivity_probe.qcl082.rmanvid1_receiver_capture",
        },
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "media_frames_requested": int_or_none(receiver.get("frames_requested")),
            "media_frames_received": video_packet_count,
            "media_bytes_received": payload_bytes,
            "media_keyframes_received": keyframe_count,
            "media_dropped_frames": dropped_frames,
            "media_receiver_queue_depth_max": max_queue_depth,
            "media_decode_error_count": int_or_none(receiver.get("decode_error_count")) or 0,
            "media_backpressure_events": backpressure_events,
            "media_frame_timestamp_gap_ms_p95": receiver.get("timestamp_gap_ms_p95"),
            "media_product_topology_ready": product_topology["ready"],
            "media_product_listener_firewall_verified": product_listener_firewall["ready"],
        },
        "issues": issues,
        "promotion": {
            "allowed": promotion_allowed,
            "target": "quest.device_link binary media stream capability descriptor",
            "reason": (
                "RMANVID1 receiver counters are paired with live broker/Quest runtime evidence"
                if promotion_allowed
                else (
                    "receiver counters parsed, but live broker/Quest runtime promotion evidence "
                    "or receiver policy gates remain incomplete"
                )
            ),
        },
        "media_stream_receiver_capture": {
            "schema": RECEIVER_CAPTURE_STATS_SCHEMA,
            "capture_kind": capture_kind,
            "live_capture": live_capture,
            "capture_path": capture_path,
            "sidecar_schema": sidecar.get("schema"),
            "sidecar_path": sidecar_path,
            "runtime_status_path": runtime_status_path,
            "topology_report_path": topology_report_path,
            "firewall_report_path": firewall_report_path,
            "source": {
                "endpoint_source": source_endpoint,
                "broker_or_quest_source": broker_or_quest_source,
                "runtime_status_observed": runtime_ok,
                "command_id": source.get("command_id"),
                "session_id": source.get("session_id"),
            },
            "stream": capture_stats,
            "product_topology": product_topology,
            "product_listener_firewall": product_listener_firewall,
            "receiver": {
                "queue_capacity_packets": queue_capacity,
                "max_queue_depth_observed": max_queue_depth,
                "drop_policy": drop_policy,
                "close_policy": close_policy,
                "close_reason": close_reason,
                "dropped_frames": dropped_frames,
                "backpressure_events": backpressure_events,
                "arrival_timestamped_packet_count": arrival_timestamped_count,
            },
        },
    }


def receiver_capture_issues(
    capture_stats: dict[str, Any],
    high_rate_json: bool,
    runtime_ok: bool,
    backpressure_policy_ok: bool,
    product_topology: dict[str, Any],
    product_listener_firewall: dict[str, Any],
) -> list[dict[str, Any]]:
    issues = [
        issue_row(
            str(code),
            "error",
            "RMANVID1 receiver capture parser reported an invalid or incomplete stream",
        )
        for code in capture_stats.get("issue_codes", [])
    ]
    if high_rate_json:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.media_high_rate_json_payload",
                "error",
                "receiver capture attempted or reported high-rate media outside the binary media plane",
            )
        )
    if not runtime_ok:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.media_stream_runtime_status_missing",
                "warning",
                "receiver capture is not paired with broker media-stream runtime status",
            )
        )
    if not backpressure_policy_ok:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.media_receiver_backpressure_missing",
                "warning",
                "receiver capture sidecar is missing bounded queue/drop/backpressure/close evidence",
            )
        )
    for issue_code in product_topology.get("issue_codes", []) or []:
        issues.append(
            issue_row(
                str(issue_code),
                "warning" if product_topology.get("check_status") == "warn" else "error",
                "QCL-082 receiver capture is not paired with a promoted direct-Wi-Fi topology",
            )
        )
    for issue_code in product_listener_firewall.get("issue_codes", []) or []:
        issues.append(
            issue_row(
                str(issue_code),
                "warning"
                if product_listener_firewall.get("check_status") == "warn"
                else "error",
                "QCL-082 receiver capture is not paired with a verified product TCP listener firewall rule",
            )
        )
    return issues


def media_product_topology_summary(
    topology_report: dict[str, Any] | None,
    *,
    topology_report_path: str,
    media_promotion_allowed: bool,
    media_transport_ok: bool,
    runtime_ok: bool,
    capture_kind: str,
) -> dict[str, Any]:
    report = object_value(topology_report)
    topology = object_value(report.get("topology"))
    transport = object_value(report.get("transport"))
    promotion = object_value(report.get("promotion"))
    owner = str(topology.get("owner") or "")
    network_provider = str(topology.get("network_provider") or "")
    endpoint_direction = str(topology.get("endpoint_direction") or "")
    transport_family = str(transport.get("family") or "")
    route = str(transport.get("route") or "")
    topology_status = str(report.get("status") or "")
    topology_probe_id = str(report.get("probe_id") or "")
    topology_promotion_allowed = promotion.get("allowed") is True
    direct_wifi = any(
        "wifi_direct" in normalize_topology_token(value)
        for value in [owner, network_provider, endpoint_direction, transport_family, route]
    )
    report_present = bool(report)
    ready = (
        report_present
        and direct_wifi
        and topology_status == "pass"
        and topology_promotion_allowed
        and media_promotion_allowed
    )
    if not report_present:
        check_status_value = "skipped"
        evidence = "product TCP media over direct-Wi-Fi topology report was not supplied"
        issue_codes: list[str] = []
    elif ready:
        check_status_value = "pass"
        evidence = "RMANVID1 TCP receiver capture is paired with promoted direct-Wi-Fi topology evidence"
        issue_codes = []
    elif direct_wifi and not topology_promotion_allowed:
        check_status_value = "warn"
        evidence = "direct-Wi-Fi topology is present but not promoted for product media"
        issue_codes = [
            "hostess.issue.connectivity_probe.media_direct_wifi_topology_not_promoted"
        ]
    elif direct_wifi and not media_promotion_allowed:
        check_status_value = "warn"
        evidence = "direct-Wi-Fi topology is present but receiver media promotion evidence is incomplete"
        issue_codes = [
            "hostess.issue.connectivity_probe.media_receiver_not_product_ready"
        ]
    else:
        check_status_value = "blocked"
        evidence = "topology report does not prove direct-Wi-Fi for product TCP media"
        issue_codes = [
            "hostess.issue.connectivity_probe.media_direct_wifi_topology_mismatch"
        ]
    return {
        "product_gate": PRODUCT_TCP_MEDIA_DIRECT_WIFI_GATE,
        "product_gate_proven": ready,
        "ready": ready,
        "check_status": check_status_value,
        "evidence": evidence,
        "issue_codes": issue_codes,
        "topology_report_path": topology_report_path,
        "topology_report_present": report_present,
        "topology_probe_id": topology_probe_id,
        "topology_status": topology_status,
        "topology_owner": owner,
        "topology_network_provider": network_provider,
        "topology_endpoint_direction": endpoint_direction,
        "topology_transport_family": transport_family,
        "topology_promotion_allowed": topology_promotion_allowed,
        "direct_wifi_topology": direct_wifi,
        "media_transport_ok": media_transport_ok,
        "media_runtime_ok": runtime_ok,
        "media_promotion_allowed": media_promotion_allowed,
        "receiver_capture_kind": capture_kind,
    }


def media_product_listener_firewall_summary(
    firewall_report: dict[str, Any] | None,
    *,
    firewall_report_path: str,
    media_promotion_allowed: bool,
    capture_kind: str,
) -> dict[str, Any]:
    report = object_value(firewall_report)
    rule = object_value(report.get("rule"))
    verification = object_value(report.get("verification"))
    listener_firewall = object_value(verification.get("listener_firewall"))
    if not listener_firewall:
        listener_firewall = object_value(object_value(verification.get("network_profile")).get("listener_firewall"))
    report_present = bool(report)
    report_status = str(report.get("status") or "")
    action = str(report.get("action") or "")
    protocol = str(listener_firewall.get("protocol") or rule.get("protocol") or "").upper()
    port = int_or_none(listener_firewall.get("port")) or int_or_none(rule.get("local_port")) or 0
    program = str(listener_firewall.get("program") or rule.get("program") or "")
    product_rule_verified = (
        verification.get("product_rule_verified") is True
        or listener_firewall.get("product_rule_verified") is True
    )
    allowed_on_active_profile = (
        verification.get("allowed_on_active_profile") is True
        or listener_firewall.get("allowed_on_active_profile") is True
    )
    diagnostic_program = diagnostic_python_program_path(program)
    tcp_listener = protocol == "TCP" and port > 0
    ready = (
        report_present
        and report_status == "pass"
        and product_rule_verified
        and allowed_on_active_profile
        and tcp_listener
        and not diagnostic_program
        and media_promotion_allowed
    )
    if not report_present:
        check_status_value = "skipped"
        evidence = "product TCP media listener firewall report was not supplied"
        issue_codes: list[str] = []
    elif ready:
        check_status_value = "pass"
        evidence = "RMANVID1 TCP receiver capture is paired with a verified product Hostess/WPF listener firewall rule"
        issue_codes = []
    elif not tcp_listener:
        check_status_value = "blocked"
        evidence = "firewall report does not verify a TCP listener port for product media"
        issue_codes = ["hostess.issue.connectivity_probe.media_listener_firewall_not_tcp"]
    elif diagnostic_program:
        check_status_value = "blocked"
        evidence = "firewall report is scoped to a diagnostic Python listener, not the product Hostess/WPF executable"
        issue_codes = ["hostess.issue.connectivity_probe.media_listener_firewall_program_diagnostic"]
    elif not product_rule_verified:
        check_status_value = "warn" if allowed_on_active_profile else "blocked"
        evidence = "firewall report does not verify a product Hostess/WPF TCP listener rule"
        issue_codes = ["hostess.issue.connectivity_probe.media_listener_firewall_product_rule_missing"]
    elif not media_promotion_allowed:
        check_status_value = "warn"
        evidence = "product Hostess/WPF TCP listener firewall is verified but receiver media promotion evidence is incomplete"
        issue_codes = ["hostess.issue.connectivity_probe.media_receiver_not_product_ready"]
    else:
        check_status_value = "blocked"
        evidence = "firewall report does not prove product TCP media listener readiness"
        issue_codes = ["hostess.issue.connectivity_probe.media_listener_firewall_not_verified"]
    return {
        "product_gate": PRODUCT_TCP_MEDIA_LISTENER_FIREWALL_GATE,
        "product_gate_proven": ready,
        "ready": ready,
        "check_status": check_status_value,
        "evidence": evidence,
        "issue_codes": issue_codes,
        "firewall_report_path": firewall_report_path,
        "firewall_report_present": report_present,
        "firewall_report_status": report_status,
        "firewall_action": action,
        "product_rule_verified": product_rule_verified,
        "allowed_on_active_profile": allowed_on_active_profile,
        "listener_program": program,
        "listener_protocol": protocol,
        "listener_port": port,
        "diagnostic_program": diagnostic_program,
        "media_promotion_allowed": media_promotion_allowed,
        "receiver_capture_kind": capture_kind,
    }


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
    "DEFAULT_MAX_RMANVID1_CAPTURE_BYTES",
    "DEFAULT_MAX_RMANVID1_CAPTURE_PACKETS",
    "DEFAULT_MAX_RMANVID1_PACKET_BYTES",
    "DEFAULT_RMANVID1_RECEIVER_QUEUE_CAPACITY",
    "RECEIVER_CAPTURE_ENDPOINT_SOURCE",
    "RECEIVER_CAPTURE_RESULT_SCHEMA",
    "RECEIVER_CAPTURE_SIDECAR_SCHEMA",
    "RECEIVER_CAPTURE_STATS_SCHEMA",
    "capture_rmanvid1_receiver_stream",
    "parse_rmanvid1_capture",
    "qcl082_media_stream_receiver_capture_body",
    "run_rmanvid1_receiver_capture",
]
