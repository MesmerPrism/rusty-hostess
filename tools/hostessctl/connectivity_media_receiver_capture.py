"""Socket capture and preview helpers for QCL-082 RMANVID1 receiver runs."""

from __future__ import annotations

import json
import socket
import time
from collections import deque
from pathlib import Path
from typing import Any, BinaryIO, MutableSequence

from tools.hostessctl.connectivity_probe_common import object_value, round_float
from tools.hostessctl.connectivity_media_receiver_common import (
    DEFAULT_MAX_RMANVID1_CAPTURE_BYTES,
    DEFAULT_MAX_RMANVID1_CAPTURE_PACKETS,
    DEFAULT_MAX_RMANVID1_METADATA_BYTES,
    DEFAULT_MAX_RMANVID1_PACKET_BYTES,
    DEFAULT_PREVIEW_WINDOW_TITLE,
    DEFAULT_RMANVID1_RECEIVER_QUEUE_CAPACITY,
    LIVE_CAPTURE_KINDS,
    RECEIVER_CAPTURE_RESULT_SCHEMA,
    RMANVID1_CODEC_H264,
    RMANVID1_PACKET_HEADER_BYTES,
    RMANVID1_STREAM_HEADER_BYTES,
    endpoint_source_for_capture_kind,
    int_or_none,
    receiver_result_follow_on_args,
    u32_be,
)
from tools.hostessctl.connectivity_media_receiver_lease import quest_lease_summary_from_args
from tools.hostessctl.connectivity_media_receiver_preflight import (
    blocked_receiver_capture_result,
    media_live_dependency_preflight_from_args,
)
from tools.hostessctl.connectivity_media_receiver_rmanvid1 import (
    parse_rmanvid1_capture,
    receiver_capture_sidecar,
)
from tools.hostessctl.h264_preview import (
    LowLatencyH264PreviewSink,
)


MAX_RECEIVER_ARRIVAL_SAMPLES = 4096


def run_rmanvid1_receiver_capture(args: Any) -> int:
    """Run the CLI-owned bounded TCP receiver capture route."""

    capture_kind = str(getattr(args, "capture_kind", "fixture_loopback_receiver") or "fixture_loopback_receiver")
    quest_lease = quest_lease_summary_from_args(args)
    if capture_kind in LIVE_CAPTURE_KINDS and not quest_lease["valid"]:
        result = blocked_receiver_capture_result(
            args,
            capture_kind=capture_kind,
            quest_lease=quest_lease,
        )
        out = Path(getattr(args, "out"))
        result["follow_on_qcl082_args"] = receiver_result_follow_on_args(str(out))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if getattr(args, "fail_on_error", False):
            return 2
        return 0
    if capture_kind in LIVE_CAPTURE_KINDS:
        dependency_preflight = media_live_dependency_preflight_from_args(args)
        if not dependency_preflight["ready"]:
            result = blocked_receiver_capture_result(
                args,
                capture_kind=capture_kind,
                quest_lease=quest_lease,
                close_reason="blocked_missing_product_media_dependencies",
                extra_issue_codes=list(dependency_preflight.get("issue_codes") or []),
                dependency_preflight=dependency_preflight,
            )
            out = Path(getattr(args, "out"))
            result["follow_on_qcl082_args"] = receiver_result_follow_on_args(str(out))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if getattr(args, "fail_on_error", False):
                return 2
            return 0

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
        capture_kind=capture_kind,
        source_endpoint_source=str(getattr(args, "source_endpoint_source", "") or ""),
        source_remote_endpoint=str(getattr(args, "source_remote_endpoint", "") or ""),
        command_id=str(getattr(args, "command_id", "") or ""),
        session_id=str(getattr(args, "session_id", "") or ""),
        runtime_status_path=str(getattr(args, "runtime_status", "") or ""),
        topology_report_path=str(getattr(args, "topology_report", "") or ""),
        firewall_report_path=str(getattr(args, "firewall_report", "") or ""),
        quest_lease=quest_lease,
        preview_ffplay=str(getattr(args, "preview_ffplay", "") or ""),
        preview_window_title=str(
            getattr(args, "preview_window_title", "") or DEFAULT_PREVIEW_WINDOW_TITLE
        ),
    )
    out = Path(getattr(args, "out"))
    result["follow_on_qcl082_args"] = receiver_result_follow_on_args(str(out))
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
    quest_lease: dict[str, Any] | None = None,
    listening_callback: Any | None = None,
    preview_ffplay: str = "",
    preview_window_title: str = DEFAULT_PREVIEW_WINDOW_TITLE,
    continue_after_capture_limit: bool = False,
) -> dict[str, Any]:
    """Listen for one RMANVID1 TCP stream and write bounded capture artifacts."""

    capture_path = Path(capture_path)
    sidecar_path = Path(sidecar_path)
    capture_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)

    issue_codes: list[str] = []
    receiver_arrivals_ns: MutableSequence[int] = deque(maxlen=MAX_RECEIVER_ARRIVAL_SAMPLES)
    capture_started_unix_ns = time.time_ns()
    capture_started_monotonic = time.monotonic()
    close_reason = "not_started"
    accepted = False
    local_endpoint = f"{bind_host}:{bind_port}"
    remote_endpoint = source_remote_endpoint
    bytes_written = 0
    packet_count = 0
    capture_retention_limit_reached = False
    viewer: dict[str, Any] = rmanvid1_preview_viewer(
        ffplay=preview_ffplay,
        window_title=preview_window_title,
        started=False,
        payload_writes=0,
        error="",
    )

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
                        (
                            close_reason,
                            bytes_written,
                            packet_count,
                            capture_retention_limit_reached,
                        ) = capture_rmanvid1_socket_bytes(
                            connection,
                            output,
                            receiver_arrivals_ns,
                            max_capture_bytes=max_capture_bytes,
                            max_packets=max_packets,
                            max_packet_bytes=max_packet_bytes,
                            max_metadata_bytes=max_metadata_bytes,
                            preview_ffplay=preview_ffplay,
                            preview_window_title=preview_window_title,
                            viewer_out=viewer,
                            continue_after_capture_limit=continue_after_capture_limit,
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
    captured_packet_count = int_or_none(capture_stats.get("packet_count")) or 0
    if not capture_retention_limit_reached:
        packet_count = captured_packet_count or packet_count
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
        quest_lease=quest_lease,
        receiver_arrival_count=packet_count,
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
        "stream_packet_count": packet_count,
        "captured_packet_count": captured_packet_count,
        "capture_retention_limit_reached": capture_retention_limit_reached,
        "continued_after_capture_limit": (
            continue_after_capture_limit and capture_retention_limit_reached
        ),
        "issue_codes": all_issue_codes,
        "socket_error": socket_error,
        "capture_stats": capture_stats,
        "receiver_sidecar": sidecar,
        "quest_lease": object_value(quest_lease),
        "viewer": viewer,
        "follow_on_qcl082_args": follow_on_args,
    }
    return result

def capture_rmanvid1_socket_bytes(
    connection: socket.socket,
    output: BinaryIO,
    receiver_arrivals_ns: MutableSequence[int],
    *,
    max_capture_bytes: int,
    max_packets: int,
    max_packet_bytes: int,
    max_metadata_bytes: int,
    preview_ffplay: str = "",
    preview_window_title: str = DEFAULT_PREVIEW_WINDOW_TITLE,
    viewer_out: dict[str, Any] | None = None,
    continue_after_capture_limit: bool = False,
) -> tuple[str, int, int, bool]:
    bytes_written = 0
    packet_count = 0
    capture_retention_limit_reached = False
    preview = Rmanvid1PreviewSink(
        preview_ffplay,
        preview_window_title,
    )

    try:
        header, header_reason = recv_exact(connection, RMANVID1_STREAM_HEADER_BYTES)
        if len(header) != RMANVID1_STREAM_HEADER_BYTES:
            output.write(header)
            return f"stream_header_{header_reason}", len(header), packet_count, False
        if len(header) > max_capture_bytes:
            return "max_bytes_reached", bytes_written, packet_count, True
        output.write(header)
        bytes_written += len(header)

        codec = u32_be(header, 12)
        width = u32_be(header, 16)
        height = u32_be(header, 20)
        metadata_len = u32_be(header, 28)
        if metadata_len > max_metadata_bytes:
            return "metadata_too_large", bytes_written, packet_count, False
        if bytes_written + metadata_len > max_capture_bytes:
            return "max_bytes_reached", bytes_written, packet_count, True
        metadata, metadata_reason = recv_exact(connection, metadata_len)
        output.write(metadata)
        bytes_written += len(metadata)
        if len(metadata) != metadata_len:
            return f"metadata_{metadata_reason}", bytes_written, packet_count, False
        preview.start(codec, width, height)

        while True:
            if max_packets > 0 and packet_count >= max_packets:
                return "max_packets_reached", bytes_written, packet_count, False
            packet_header, packet_header_reason = recv_exact(connection, RMANVID1_PACKET_HEADER_BYTES)
            if not packet_header and packet_header_reason == "peer_closed":
                return (
                    "peer_closed",
                    bytes_written,
                    packet_count,
                    capture_retention_limit_reached,
                )
            if len(packet_header) != RMANVID1_PACKET_HEADER_BYTES:
                if not capture_retention_limit_reached:
                    output.write(packet_header)
                    bytes_written += len(packet_header)
                return (
                    f"packet_header_{packet_header_reason}",
                    bytes_written,
                    packet_count,
                    capture_retention_limit_reached,
                )

            payload_len = u32_be(packet_header, 12)
            packet_flags = u32_be(packet_header, 8)
            if payload_len > max_packet_bytes:
                if not capture_retention_limit_reached:
                    output.write(packet_header)
                    bytes_written += len(packet_header)
                return "payload_too_large", bytes_written, packet_count, capture_retention_limit_reached
            if bytes_written + RMANVID1_PACKET_HEADER_BYTES + payload_len > max_capture_bytes:
                if not continue_after_capture_limit:
                    return "max_bytes_reached", bytes_written, packet_count, True
                capture_retention_limit_reached = True

            payload, payload_reason = recv_exact(connection, payload_len)
            if len(payload) != payload_len:
                return (
                    f"payload_{payload_reason}",
                    bytes_written,
                    packet_count,
                    capture_retention_limit_reached,
                )
            receiver_arrivals_ns.append(time.time_ns())
            preview.write_payload(payload, packet_flags)
            if not capture_retention_limit_reached:
                output.write(packet_header)
                bytes_written += len(packet_header)
                output.write(payload)
                bytes_written += len(payload)
            packet_count += 1
    finally:
        preview.close()
        if viewer_out is not None:
            viewer_out.clear()
            viewer_out.update(preview.to_json())

class Rmanvid1PreviewSink:
    def __init__(self, ffplay: str, window_title: str) -> None:
        self.ffplay = str(ffplay or "").strip()
        self.window_title = str(window_title or DEFAULT_PREVIEW_WINDOW_TITLE).strip()
        self.sink: LowLatencyH264PreviewSink | None = None
        self.lifecycle: dict[str, Any] = {}
        self.started = False
        self.payload_writes = 0
        self.error = ""

    def start(self, codec: int, width: int, height: int) -> None:
        if not self.ffplay or codec != RMANVID1_CODEC_H264:
            return
        self.sink = LowLatencyH264PreviewSink(
            self.ffplay,
            self.window_title,
            width=max(1, int(width)),
            height=max(1, int(height)),
        )
        self.sink.start()
        self.started = self.sink.started
        self.error = self.sink.error

    def write_payload(self, payload: bytes, flags: int = 0) -> None:
        if not self.started or self.sink is None:
            return
        self.sink.write(payload, flags=flags)
        self.payload_writes = self.sink.payload_writes
        self.error = self.sink.error

    def close(self) -> None:
        if self.sink is None:
            return
        self.lifecycle = self.sink.close()
        self.started = bool(self.lifecycle.get("started"))
        self.payload_writes = int(self.lifecycle.get("payload_writes", 0))
        self.error = str(self.lifecycle.get("error", ""))

    def to_json(self) -> dict[str, Any]:
        return rmanvid1_preview_viewer(
            ffplay=self.ffplay,
            window_title=self.window_title,
            started=self.started,
            payload_writes=self.payload_writes,
            error=self.error,
            lifecycle=self.lifecycle,
        )

def rmanvid1_preview_viewer(
    *,
    ffplay: str,
    window_title: str,
    started: bool,
    payload_writes: int,
    error: str,
    lifecycle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail = lifecycle or {}
    backend = str(
        detail.get("backend")
        or "ffplay_external_window"
    )
    return {
        "backend": backend,
        "started": bool(started),
        "connected": bool(detail.get("connected", started if ffplay else False)),
        "payload_writes": int(payload_writes),
        "bytes_written": int(detail.get("bytes_written", 0)),
        "ffplay": str(ffplay or ""),
        "window_title": str(window_title or DEFAULT_PREVIEW_WINDOW_TITLE),
        "ffplay_started": bool(started),
        "ffplay_payload_writes": int(payload_writes),
        "ffplay_bytes_written": int(detail.get("bytes_written", 0)),
        "ffplay_payload_enqueues": int(detail.get("payload_enqueues", 0)),
        "ffplay_bytes_enqueued": int(detail.get("bytes_enqueued", 0)),
        "preview_queue_capacity_packets": int(detail.get("queue_capacity_packets", 0)),
        "preview_queue_max_depth": int(detail.get("queue_max_depth", 0)),
        "preview_queue_dropped_packets": int(detail.get("queue_dropped_packets", 0)),
        "preview_queue_dropped_bytes": int(detail.get("queue_dropped_bytes", 0)),
        "preview_queue_resync_events": int(detail.get("queue_resync_events", 0)),
        "preview_writer_thread_stopped": bool(detail.get("writer_thread_stopped", True)),
        "ffplay_returncode": detail.get("returncode"),
        "ffplay_terminated_after_eof_timeout": bool(
            detail.get("terminated_after_eof_timeout", False)
        ),
        "ffplay_killed_after_eof_timeout": bool(detail.get("killed_after_eof_timeout", False)),
        "ffplay_error": str(error or ""),
        "ffplay_visible_window_seen": bool(detail.get("visible_window_seen", False)),
        "ffplay_visible_window_title": str(detail.get("visible_window_title", "")),
        "first_payload_delay_ms": detail.get("first_payload_delay_ms"),
        "connect_delay_ms": detail.get("connect_delay_ms"),
        "last_payload_elapsed_ms": detail.get("last_payload_elapsed_ms"),
        "first_visible_window_delay_ms": detail.get("first_visible_window_delay_ms"),
        "timing_mode": str(detail.get("timing_mode", "receiver_arrival_wallclock")),
        "sync_master": str(detail.get("sync_master", "external_clock")),
        "drop_policy": str(detail.get("drop_policy", "ffplay_framedrop")),
        "preview_queue_drop_policy": str(
            detail.get("preview_queue_drop_policy", "drop_on_overflow_resync_on_keyframe")
        ),
        "ffplay_stderr": str(detail.get("stderr", "")),
    }

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

__all__ = [
    "run_rmanvid1_receiver_capture",
    "capture_rmanvid1_receiver_stream",
    "capture_rmanvid1_socket_bytes",
    "Rmanvid1PreviewSink",
    "rmanvid1_preview_viewer",
    "recv_exact",
]
