"""RMANVID1 capture parsing and QCL-082 receiver evidence shaping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, BinaryIO

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
from tools.hostessctl.connectivity_media_receiver_common import (
    DEFAULT_MAX_RMANVID1_METADATA_BYTES,
    DEFAULT_MAX_RMANVID1_PACKET_BYTES,
    LIVE_CAPTURE_KINDS,
    MEDIA_CODEC_FLAG_CODEC_CONFIG,
    MEDIA_CODEC_FLAG_KEY_FRAME,
    RECEIVER_CAPTURE_ENDPOINT_SOURCE,
    RECEIVER_CAPTURE_SIDECAR_SCHEMA,
    RECEIVER_CAPTURE_STATS_SCHEMA,
    RMANVID1_CODEC_H264,
    RMANVID1_PACKET_HEADER_BYTES,
    RMANVID1_SCHEMA_VERSION,
    RMANVID1_STREAM_HEADER_BYTES,
    arrival_gap_ms_p95,
    check_passed,
    drain_payload,
    int_or_none,
    u32_be,
    u64_be,
)
from tools.hostessctl.connectivity_media_receiver_lease import media_receiver_quest_lease_summary
from tools.hostessctl.connectivity_media_receiver_product import (
    media_product_listener_firewall_summary,
    media_product_topology_summary,
)


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
    quest_lease: dict[str, Any] | None = None,
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
        "lease": object_value(quest_lease),
    }

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
    quest_lease = media_receiver_quest_lease_summary(sidecar)
    quest_lease_ok = not live_capture or quest_lease["valid"]
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
        and quest_lease_ok
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
        quest_lease=quest_lease,
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
        quest_lease,
        live_capture,
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
            "protocol.media_receiver_quest_lease",
            "pass" if quest_lease_ok else "blocked",
            (
                "live receiver capture carries an accepted Agent Board quest lease"
                if quest_lease_ok and live_capture
                else (
                    "fixture receiver capture does not require a Quest lease"
                    if not live_capture
                    else "live receiver capture is missing accepted Agent Board quest lease evidence"
                )
            ),
            observed=quest_lease,
            issue_codes=list(quest_lease.get("issue_codes") or []) if live_capture else [],
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
            "media_receiver_quest_lease_valid": quest_lease_ok,
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
            "quest_lease": quest_lease,
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
    quest_lease: dict[str, Any],
    live_capture: bool,
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
    if live_capture and not quest_lease.get("valid"):
        for issue_code in quest_lease.get("issue_codes", []) or []:
            issues.append(
                issue_row(
                    str(issue_code),
                    "error",
                    "live QCL-082 receiver capture is missing accepted Agent Board quest lease evidence",
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

__all__ = [
    "receiver_capture_sidecar",
    "parse_rmanvid1_capture",
    "parse_rmanvid1_stream",
    "qcl082_media_stream_receiver_capture_body",
    "receiver_capture_issues",
]
