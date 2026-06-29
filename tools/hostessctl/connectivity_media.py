"""QCL-082 binary media-plane fixture report helpers."""

from __future__ import annotations

from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    check_row,
    empty_measurements,
    issue_row,
)


DEFAULT_QCL082_MEDIA_PORT = 18782
DEFAULT_QCL082_PACKET_MAGIC = "RMANVID1"


def qcl082_fixture_body(*, status: str, high_rate_json_misuse: bool = False) -> dict[str, Any]:
    """Build a source-validatable QCL-082 media/binary report body."""

    failed = status != "pass" or high_rate_json_misuse
    checks = [
        check_row(
            "protocol.media_binary_transport",
            "fail" if failed else "pass",
            (
                "media payload attempted through JSON command stream"
                if failed
                else "TCP binary media plane declared with RMANVID1 packet magic"
            ),
            observed={
                "transport_kind": "tcp_binary",
                "packet_magic": DEFAULT_QCL082_PACKET_MAGIC,
                "codec": "h264_annex_b",
                "payload_plane": "json_event" if high_rate_json_misuse else "binary_media",
                "command_plane_payload": high_rate_json_misuse,
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_high_rate_json_payload"]
                if high_rate_json_misuse
                else []
            ),
        ),
        check_row(
            "protocol.media_packet_boundaries",
            "blocked" if failed else "pass",
            (
                "packet boundaries not valid for JSON-carried media"
                if failed
                else "packet header carries magic, sequence, timestamp, flags, and payload length"
            ),
            observed={
                "header_magic": DEFAULT_QCL082_PACKET_MAGIC,
                "sequence_monotonic": not failed,
                "payload_length_bounded": not failed,
                "keyframe_flag_present": not failed,
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_packet_boundaries_not_proven"]
                if failed
                else []
            ),
        ),
        check_row(
            "protocol.media_timestamp_policy",
            "blocked" if failed else "pass",
            (
                "timestamp policy not proven"
                if failed
                else "capture timestamp and receiver arrival timestamp are recorded per frame"
            ),
            observed={
                "capture_timestamp": "monotonic_ns",
                "receiver_arrival_timestamp": "monotonic_ns",
                "clock_alignment": "parallel_lsl_reference_or_media_ack_channel",
                "timestamped_frame_count": 0 if failed else 24,
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_timestamp_policy_not_proven"]
                if failed
                else []
            ),
        ),
        check_row(
            "protocol.media_backpressure_policy",
            "blocked" if failed else "pass",
            (
                "queue/drop/close policy absent"
                if failed
                else "bounded receiver queue, newest-frame drop, and close-on-overrun policy declared"
            ),
            observed={
                "receiver_queue_capacity_frames": None if failed else 4,
                "drop_policy": "not_declared" if failed else "drop_oldest_non_keyframe",
                "close_policy": "not_declared" if failed else "close_after_sustained_overrun",
                "max_queue_depth_observed": None if failed else 2,
                "backpressure_signal": "not_declared" if failed else "receiver_queue_depth",
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_backpressure_policy_missing"]
                if failed
                else []
            ),
        ),
        check_row(
            "protocol.media_high_rate_json_guard",
            "fail" if high_rate_json_misuse else "pass",
            (
                "high-rate media payloads must not be carried by JSON command/report streams"
                if high_rate_json_misuse
                else "JSON is limited to control receipts and small descriptors"
            ),
            observed={
                "json_allowed_for": ["control_receipts", "descriptors", "validation_reports"],
                "json_allowed_for_media_payload": False,
                "observed_payload_plane": "json_event" if high_rate_json_misuse else "binary_media",
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_high_rate_json_payload"]
                if high_rate_json_misuse
                else []
            ),
        ),
    ]
    return {
        "status": "fail" if failed else "pass",
        "classification": "protocol_fit_candidate",
        "topology": {
            "owner": "host_local",
            "network_provider": "loopback",
            "endpoint_direction": "quest_to_host_binary_media",
            "requires_existing_wifi": False,
            "requires_adb": False,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": True,
        },
        "transport": {
            "family": "tcp_binary",
            "route": "qcl082_h264_tcp_binary_media_plane",
            "local_endpoint": f"127.0.0.1:{DEFAULT_QCL082_MEDIA_PORT}",
            "remote_endpoint": "127.0.0.1",
            "protocol_role": "binary_media_plane_probe",
            "payload_class": "h264_annex_b_binary_frames",
            "endpoint_source": "media-binary-fixture",
            "packet_magic": DEFAULT_QCL082_PACKET_MAGIC,
        },
        "device": {
            "serial_redacted": True,
            "model": "fixture",
            "foreground_package": "not_checked",
            "adb_state": "not_applicable",
        },
        "host": {
            "os": "windows",
            "toolchain_profile": "hostessctl.connectivity_probe.qcl082.fixture",
        },
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "media_frames_requested": 24,
            "media_frames_received": 0 if failed else 24,
            "media_bytes_received": 0 if failed else 1048576,
            "media_keyframes_received": 0 if failed else 2,
            "media_dropped_frames": None if failed else 0,
            "media_receiver_queue_depth_max": None if failed else 2,
            "media_decode_error_count": 1 if high_rate_json_misuse else 0,
            "media_backpressure_events": None if failed else 0,
            "media_frame_timestamp_gap_ms_p95": None if failed else 34,
        },
        "issues": (
            [
                issue_row(
                    "hostess.issue.connectivity_probe.media_high_rate_json_payload",
                    "error",
                    "fixture rejects high-rate media payloads on JSON command/report streams",
                )
            ]
            if high_rate_json_misuse
            else []
        ),
        "promotion": {
            "allowed": False,
            "target": "quest.device_link binary media stream capability descriptor",
            "reason": (
                "fixture declares QCL-082 media-plane constraints; live Quest-runtime "
                "or broker-owned binary evidence remains required"
            ),
        },
    }


__all__ = [
    "DEFAULT_QCL082_MEDIA_PORT",
    "DEFAULT_QCL082_PACKET_MAGIC",
    "qcl082_fixture_body",
]
