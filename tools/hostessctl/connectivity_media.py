"""QCL-082 binary media-plane fixture and contract report helpers."""

from __future__ import annotations

from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    check_row,
    empty_measurements,
    issue_row,
    list_value,
    object_value,
)


DEFAULT_QCL082_MEDIA_PORT = 18782
DEFAULT_QCL082_PACKET_MAGIC = "RMANVID1"
MEDIA_STREAM_SESSION_SCHEMA = "rusty.quest.media_stream_session.v1"
MEDIA_STREAM_RUNTIME_STATUS_SCHEMA = "rusty.quest.media_stream.android_runtime_status.v1"
MEDIA_STREAM_COMMAND_PREFIX = "command.media_stream."
MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE = "rusty-quest-manifold-broker-media-stream-runtime"


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


def qcl082_media_stream_session_body(
    plan: dict[str, Any],
    *,
    plan_path: str = "",
) -> dict[str, Any]:
    """Build QCL-082 evidence from a Rusty Quest media-stream session plan."""

    source = first_object(plan.get("sources"))
    lane = first_object(plan.get("lanes"))
    media = object_value(lane.get("media"))
    transport_plan = object_value(lane.get("transport"))
    queue = object_value(lane.get("queue"))
    observability = object_value(plan.get("observability"))
    required_markers = string_set(observability.get("required_markers"))
    required_counters = string_set(observability.get("required_counters"))

    schema_ok = plan.get("schema") == MEDIA_STREAM_SESSION_SCHEMA
    binary_plane = media.get("high_rate_payload_plane") == "binary-media"
    codec_ok = media.get("codec") == "h264"
    transport_ok = transport_plan.get("transport_kind") in {"lan_tcp", "tcp_binary"}
    packet_magic = DEFAULT_QCL082_PACKET_MAGIC
    framing_ok = (
        media.get("stream_framing") == "diagnostic-h264-packet-stream"
        and int_or_none(media.get("max_packet_bytes")) is not None
    )
    timestamp_ok = bool(media.get("timestamp_domain")) and {
        "capture_to_encode_ms",
        "encode_to_receive_ms",
    }.issubset(required_counters)
    backpressure_ok = (
        int_or_none(queue.get("max_buffered_packets")) is not None
        and int_or_none(queue.get("max_buffered_bytes")) is not None
        and bool(queue.get("drop_policy"))
        and queue.get("slow_peer_close") is True
    )
    shell_route = source.get("source_kind") == "shell_display_mirror_mediacodec_surface"
    shell_lab_gate = (
        not shell_route
        or (
            source.get("deployment_classification") == "lab_developer_only"
            and source.get("capture_authority") == "adb_shell_hidden_api_developer_only"
            and source.get("developer_shell_required") is True
        )
    )
    source_classification_ok = bool(source.get("source_family")) and bool(source.get("source_kind"))
    required_observability_ok = {
        "media_packets",
        "codec_config_packets",
        "keyframes",
        "queue_drops",
        "close_reason",
    }.issubset(required_counters) and bool(required_markers)
    failed = not all(
        [
            schema_ok,
            binary_plane,
            codec_ok,
            transport_ok,
            framing_ok,
            timestamp_ok,
            backpressure_ok,
            shell_lab_gate,
            source_classification_ok,
            required_observability_ok,
        ]
    )

    issue_codes: list[str] = []
    issues: list[dict[str, Any]] = []
    if not schema_ok:
        issue_codes.append("hostess.issue.connectivity_probe.media_stream_session_schema_unsupported")
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.media_stream_session_schema_unsupported",
                "error",
                "media-stream session plan schema is unsupported",
            )
        )
    if not binary_plane:
        issue_codes.append("hostess.issue.connectivity_probe.media_high_rate_json_payload")
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.media_high_rate_json_payload",
                "error",
                "media-stream session plan attempts high-rate media outside the binary media plane",
            )
        )
    if not shell_lab_gate:
        issue_codes.append("hostess.issue.connectivity_probe.shell_display_route_not_lab_only")
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.shell_display_route_not_lab_only",
                "error",
                "shell hidden-display media source must stay lab_developer_only with shell authority",
            )
        )

    checks = [
        check_row(
            "protocol.media_stream_session_contract",
            "fail" if not schema_ok else "pass",
            (
                "Rusty Quest media-stream session schema accepted"
                if schema_ok
                else "unsupported media-stream session schema"
            ),
            observed={
                "schema": plan.get("schema"),
                "session_id": plan.get("session_id"),
                "source_family": source.get("source_family"),
                "source_kind": source.get("source_kind"),
                "plan_path": plan_path,
            },
        ),
        check_row(
            "protocol.media_binary_transport",
            "pass" if binary_plane and codec_ok and transport_ok else "fail",
            (
                "media-stream plan declares H.264 over a binary TCP media plane"
                if binary_plane and codec_ok and transport_ok
                else "media-stream plan does not declare a valid binary H.264 TCP media plane"
            ),
            observed={
                "transport_kind": "tcp_binary",
                "source_transport_kind": transport_plan.get("transport_kind"),
                "packet_magic": packet_magic,
                "codec": media.get("codec"),
                "payload_plane": media.get("high_rate_payload_plane"),
                "command_plane_payload": not binary_plane,
            },
            issue_codes=issue_codes if not binary_plane else [],
        ),
        check_row(
            "protocol.media_packet_boundaries",
            "pass" if framing_ok else "blocked",
            (
                "media-stream plan declares bounded diagnostic H.264 packet framing"
                if framing_ok
                else "media-stream plan does not declare bounded packet framing"
            ),
            observed={
                "header_magic": packet_magic,
                "stream_framing": media.get("stream_framing"),
                "max_packet_bytes": media.get("max_packet_bytes"),
                "sequence_monotonic": framing_ok,
                "payload_length_bounded": framing_ok,
                "keyframe_flag_present": "keyframes" in required_counters,
            },
        ),
        check_row(
            "protocol.media_timestamp_policy",
            "pass" if timestamp_ok else "blocked",
            (
                "media-stream plan declares capture/receive timing counters"
                if timestamp_ok
                else "media-stream plan is missing capture/receive timing policy"
            ),
            observed={
                "capture_timestamp": media.get("timestamp_domain"),
                "receiver_arrival_timestamp": "encode_to_receive_ms",
                "clock_alignment": "media-stream required counters",
                "timestamped_frame_count": 0,
            },
        ),
        check_row(
            "protocol.media_backpressure_policy",
            "pass" if backpressure_ok else "blocked",
            (
                "media-stream plan declares bounded queue, drop, and slow-peer close policy"
                if backpressure_ok
                else "media-stream plan is missing bounded queue/drop/close policy"
            ),
            observed={
                "receiver_queue_capacity_frames": queue.get("max_buffered_packets"),
                "receiver_queue_capacity_bytes": queue.get("max_buffered_bytes"),
                "drop_policy": queue.get("drop_policy"),
                "close_policy": "close_after_sustained_overrun" if queue.get("slow_peer_close") is True else "not_declared",
                "max_queue_depth_observed": 0,
                "backpressure_signal": "required queue_drops counter" if "queue_drops" in required_counters else "not_declared",
            },
        ),
        check_row(
            "protocol.media_high_rate_json_guard",
            "pass" if binary_plane else "fail",
            (
                "media-stream plan keeps high-rate payloads on the binary media plane"
                if binary_plane
                else "high-rate media payloads must not be carried by JSON command/report streams"
            ),
            observed={
                "json_allowed_for": ["control_receipts", "descriptors", "validation_reports"],
                "json_allowed_for_media_payload": False,
                "observed_payload_plane": media.get("high_rate_payload_plane"),
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_high_rate_json_payload"]
                if not binary_plane
                else []
            ),
        ),
        check_row(
            "protocol.media_source_classification",
            "pass" if source_classification_ok else "blocked",
            (
                "media-stream plan declares source family, kind, route, and capture authority"
                if source_classification_ok
                else "media-stream plan is missing source classification"
            ),
            observed={
                "source_family": source.get("source_family"),
                "source_kind": source.get("source_kind"),
                "capture_route": source.get("capture_route"),
                "capture_authority": source.get("capture_authority"),
                "deployment_classification": source.get("deployment_classification"),
                "track_role": source.get("track_role"),
            },
        ),
        check_row(
            "protocol.media_shell_lab_gate",
            "pass" if shell_lab_gate else "fail",
            (
                "shell hidden-display source is lab-only or not requested"
                if shell_lab_gate
                else "shell hidden-display source is not correctly gated as lab-only"
            ),
            observed={
                "shell_route": shell_route,
                "deployment_classification": source.get("deployment_classification"),
                "developer_shell_required": source.get("developer_shell_required"),
                "capture_authority": source.get("capture_authority"),
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.shell_display_route_not_lab_only"]
                if not shell_lab_gate
                else []
            ),
        ),
        check_row(
            "protocol.media_observability_policy",
            "pass" if required_observability_ok else "blocked",
            (
                "media-stream plan declares required markers and counters for runtime promotion"
                if required_observability_ok
                else "media-stream plan is missing required runtime observability markers or counters"
            ),
            observed={
                "required_markers": sorted(required_markers),
                "required_counters": sorted(required_counters),
            },
        ),
    ]

    local_endpoint, remote_endpoint = qcl082_media_stream_endpoints(plan)
    return {
        "status": "fail" if failed else "pass",
        "classification": "protocol_fit_source_contract",
        "topology": {
            "owner": str(plan.get("topology_id") or "quest_display_to_pc"),
            "network_provider": "declared_by_media_stream_session",
            "endpoint_direction": "quest_to_host_binary_media",
            "requires_existing_wifi": True,
            "requires_adb": False,
            "requires_pairing": object_value(plan.get("security")).get("explicit_pairing_required") is True,
            "requires_termux": False,
            "experimental": True,
        },
        "transport": {
            "family": "tcp_binary",
            "route": "rusty_quest_media_stream_session_plan",
            "local_endpoint": local_endpoint,
            "remote_endpoint": remote_endpoint,
            "protocol_role": "binary_media_plane_source_contract",
            "payload_class": "h264_annex_b_binary_frames",
            "endpoint_source": "rusty-quest-media-stream-session-plan",
            "packet_magic": packet_magic,
        },
        "device": {
            "serial_redacted": True,
            "model": "source_contract",
            "foreground_package": "not_checked",
            "adb_state": "not_applicable",
        },
        "host": {
            "os": "windows",
            "toolchain_profile": "hostessctl.connectivity_probe.qcl082.media_stream_session_plan.fixture",
        },
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "media_frames_requested": 0,
            "media_frames_received": 0,
            "media_bytes_received": 0,
            "media_keyframes_received": 0,
            "media_dropped_frames": 0 if not failed else None,
            "media_receiver_queue_depth_max": 0 if not failed else None,
            "media_decode_error_count": 0 if not failed else 1,
            "media_backpressure_events": 0 if not failed else None,
            "media_frame_timestamp_gap_ms_p95": None,
        },
        "issues": issues,
        "promotion": {
            "allowed": False,
            "target": "quest.device_link binary media stream capability descriptor",
            "reason": (
                "Rusty Quest media-stream session plan is source-contract evidence; "
                "Quest-runtime or broker-owned binary counters remain required"
            ),
        },
        "media_stream_session_plan": {
            "schema": plan.get("schema"),
            "session_id": plan.get("session_id"),
            "topology_id": plan.get("topology_id"),
            "privacy_tier": plan.get("privacy_tier"),
            "source": {
                "source_id": source.get("source_id"),
                "source_family": source.get("source_family"),
                "source_kind": source.get("source_kind"),
                "capture_route": source.get("capture_route"),
                "capture_authority": source.get("capture_authority"),
                "deployment_classification": source.get("deployment_classification"),
                "developer_shell_required": source.get("developer_shell_required"),
                "consent_required": source.get("consent_required"),
                "track_role": source.get("track_role"),
            },
            "lane": {
                "lane_id": lane.get("lane_id"),
                "track_id": media.get("track_id"),
                "track_role": media.get("track_role"),
                "width": media.get("width"),
                "height": media.get("height"),
                "frame_rate_hz": media.get("frame_rate_hz"),
                "bitrate_bps": media.get("bitrate_bps"),
                "max_packet_bytes": media.get("max_packet_bytes"),
                "high_rate_payload_plane": media.get("high_rate_payload_plane"),
            },
            "artifact_path": plan_path,
        },
    }


def qcl082_media_stream_endpoints(plan: dict[str, Any]) -> tuple[str, str]:
    receiver_port = ""
    source_port = ""
    for endpoint in list_value(plan.get("runtime_endpoints")):
        row = object_value(endpoint)
        adapter = str(row.get("adapter_kind") or "")
        if adapter == "windows_hostess":
            for port in list_value(row.get("transport_receive_ports")):
                port_row = object_value(port)
                receiver_port = str(port_row.get("port") or "")
                if receiver_port:
                    break
        if adapter == "quest_manifold_broker_android":
            for binding in list_value(row.get("source_bindings")):
                binding_row = object_value(binding)
                source_port = str(binding_row.get("source_port") or "")
                if source_port:
                    break
    local = f"0.0.0.0:{receiver_port}" if receiver_port else "declared_by_plan"
    remote = f"127.0.0.1:{source_port}" if source_port else "declared_by_plan"
    return local, remote


def qcl082_media_stream_runtime_status_body(
    artifact: dict[str, Any],
    *,
    artifact_path: str = "",
) -> dict[str, Any]:
    """Build QCL-082 evidence from a Rusty Quest media-stream runtime status artifact."""

    runtime_result, runtime_status, command_ack = media_stream_runtime_sections(artifact)
    command_id = str(
        command_ack.get("command")
        or command_ack.get("command_id")
        or runtime_result.get("command_id")
        or ""
    )
    session_id = str(
        runtime_status.get("session_id")
        or runtime_result.get("session_id")
        or artifact.get("session_id")
        or ""
    )
    runtime_schema = str(runtime_status.get("schema") or runtime_result.get("schema") or "")
    runtime_family = str(runtime_status.get("runtime_family") or runtime_result.get("runtime_family") or "")
    high_rate_json = bool(
        artifact.get("high_rate_json_payload")
        or runtime_result.get("high_rate_json_payload")
        or runtime_status.get("high_rate_json_payload")
    )
    media_payload_plane = str(
        runtime_status.get("media_payload_plane")
        or runtime_result.get("media_payload_plane")
        or "binary-media"
    )
    command_ack_present = bool(command_ack)
    command_ack_ok = (
        not command_ack_present
        or (
            command_ack.get("schema") == "rusty.manifold.command.ack.v1"
            and command_ack.get("accepted") is True
            and str(command_ack.get("authority") or "") == "rusty.manifold"
            and command_id.startswith(MEDIA_STREAM_COMMAND_PREFIX)
        )
    )
    runtime_schema_ok = runtime_schema == MEDIA_STREAM_RUNTIME_STATUS_SCHEMA
    runtime_family_ok = runtime_family == "media_stream"
    binary_plane_ok = media_payload_plane == "binary-media" and not high_rate_json
    runtime_state_ok = "active_count" in runtime_status and "lanes" in runtime_status
    source_runtime = media_stream_source_runtime(runtime_result, runtime_status)
    source_summary = media_stream_source_summary(source_runtime)
    source_classification_ok = bool(source_summary.get("source_kind") or source_summary.get("display_frame_source"))
    source_gate_ok = media_stream_source_gate_ok(source_summary)
    counter_summary = media_stream_counter_summary(source_runtime)
    binary_counters_present = counter_summary["packet_count"] is not None
    core_failed = not all(
        [
            command_ack_ok,
            runtime_schema_ok,
            runtime_family_ok,
            binary_plane_ok,
            source_gate_ok,
        ]
    )
    status = "fail" if core_failed else ("warn" if not binary_counters_present else "pass")

    issues: list[dict[str, Any]] = []
    if not command_ack_ok:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.media_stream_command_ack_invalid",
                "error",
                "media-stream runtime status was not backed by an accepted Manifold command ACK",
            )
        )
    if not runtime_schema_ok:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.media_stream_runtime_schema_unsupported",
                "error",
                "media-stream runtime status schema is unsupported",
            )
        )
    if high_rate_json or media_payload_plane != "binary-media":
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.media_high_rate_json_payload",
                "error",
                "media-stream runtime status attempted or reported high-rate media outside the binary media plane",
            )
        )
    if not source_gate_ok:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.shell_display_route_not_lab_only",
                "error",
                "shell hidden-display runtime source must remain lab-only with shell authority",
            )
        )
    if not binary_counters_present and status != "fail":
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.media_binary_counters_missing",
                "warning",
                "media-stream runtime status did not yet include binary receiver packet/drop/queue counters",
            )
        )

    checks = [
        check_row(
            "protocol.media_stream_runtime_status",
            "pass" if runtime_schema_ok and runtime_family_ok else "fail",
            (
                "Rusty Quest media-stream runtime status schema accepted"
                if runtime_schema_ok and runtime_family_ok
                else "runtime status is not a Rusty Quest media-stream status artifact"
            ),
            observed={
                "schema": runtime_schema,
                "runtime_family": runtime_family,
                "session_id": session_id,
                "artifact_path": artifact_path,
            },
        ),
        check_row(
            "protocol.media_stream_command_ack",
            "pass" if command_ack_ok else "fail",
            (
                "Manifold command ACK accepted a media-stream command"
                if command_ack_present and command_ack_ok
                else (
                    "raw runtime status artifact supplied without command ACK"
                    if not command_ack_present
                    else "media-stream command ACK was not accepted by Manifold"
                )
            ),
            observed={
                "command_ack_present": command_ack_present,
                "command_id": command_id,
                "accepted": command_ack.get("accepted") if command_ack_present else None,
                "authority": command_ack.get("authority") if command_ack_present else None,
            },
        ),
        check_row(
            "protocol.media_runtime_state",
            "pass" if runtime_state_ok else "blocked",
            (
                "runtime status reports active, matched, lifecycle, and lane state"
                if runtime_state_ok
                else "runtime status does not include receiver/source/transport lane state"
            ),
            observed={
                "active_count": runtime_status.get("active_count"),
                "matched_count": runtime_status.get("matched_count"),
                "created_count": runtime_status.get("created_count"),
                "stopped_count": runtime_status.get("stopped_count"),
                "failed_count": runtime_status.get("failed_count"),
                "lane_count": len(list_value(runtime_status.get("lanes"))),
            },
        ),
        check_row(
            "protocol.media_binary_transport",
            "pass" if binary_plane_ok else "fail",
            (
                "runtime status keeps media payloads on the binary media plane"
                if binary_plane_ok
                else "runtime status reports high-rate JSON media or a non-binary media plane"
            ),
            observed={
                "transport_kind": "tcp_binary",
                "packet_magic": DEFAULT_QCL082_PACKET_MAGIC,
                "codec": "h264_annex_b",
                "payload_plane": media_payload_plane,
                "command_plane_payload": high_rate_json,
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_high_rate_json_payload"]
                if not binary_plane_ok
                else []
            ),
        ),
        check_row(
            "protocol.media_source_classification",
            "pass" if source_classification_ok else "blocked",
            (
                "runtime status reports selected media source or display adapter gate"
                if source_classification_ok
                else "runtime status does not expose selected source kind"
            ),
            observed=source_summary,
        ),
        check_row(
            "protocol.media_shell_lab_gate",
            "pass" if source_gate_ok else "fail",
            (
                "shell hidden-display source is lab-only or not requested"
                if source_gate_ok
                else "shell hidden-display source is not correctly gated as lab-only"
            ),
            observed=source_summary,
            issue_codes=(
                ["hostess.issue.connectivity_probe.shell_display_route_not_lab_only"]
                if not source_gate_ok
                else []
            ),
        ),
        check_row(
            "protocol.media_high_rate_json_guard",
            "pass" if not high_rate_json else "fail",
            (
                "runtime status reports high_rate_json_payload=false"
                if not high_rate_json
                else "runtime status reports high-rate media on JSON command/report streams"
            ),
            observed={
                "json_allowed_for": ["control_receipts", "descriptors", "validation_reports"],
                "json_allowed_for_media_payload": False,
                "observed_payload_plane": media_payload_plane,
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_high_rate_json_payload"]
                if high_rate_json
                else []
            ),
        ),
        check_row(
            "protocol.media_binary_runtime_counters",
            "pass" if binary_counters_present else "blocked",
            (
                "runtime status includes binary packet counters"
                if binary_counters_present
                else "runtime status is command/source state only; binary receiver counters remain required"
            ),
            observed=counter_summary,
            issue_codes=(
                ["hostess.issue.connectivity_probe.media_binary_counters_missing"]
                if not binary_counters_present
                else []
            ),
        ),
    ]

    local_endpoint = media_stream_runtime_local_endpoint(runtime_status, runtime_result)
    remote_endpoint = media_stream_runtime_remote_endpoint(runtime_result, source_runtime)
    return {
        "status": status,
        "classification": "protocol_fit_broker_runtime_status",
        "topology": {
            "owner": "quest_broker_media_stream_runtime",
            "network_provider": "declared_by_broker_runtime",
            "endpoint_direction": "quest_to_host_binary_media",
            "requires_existing_wifi": True,
            "requires_adb": False,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": True,
        },
        "transport": {
            "family": "tcp_binary",
            "route": "rusty_quest_media_stream_runtime_status",
            "local_endpoint": local_endpoint,
            "remote_endpoint": remote_endpoint,
            "protocol_role": "binary_media_plane_broker_runtime_status",
            "payload_class": "h264_annex_b_binary_frames",
            "endpoint_source": MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE,
            "packet_magic": DEFAULT_QCL082_PACKET_MAGIC,
        },
        "device": {
            "serial_redacted": True,
            "model": "broker_runtime_status",
            "foreground_package": "not_checked",
            "adb_state": "not_applicable",
        },
        "host": {
            "os": "windows",
            "toolchain_profile": "hostessctl.connectivity_probe.qcl082.media_stream_runtime_status.fixture",
        },
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "media_frames_requested": None,
            "media_frames_received": counter_summary["video_packet_count"],
            "media_bytes_received": counter_summary["bytes_written"],
            "media_keyframes_received": None,
            "media_dropped_frames": None,
            "media_receiver_queue_depth_max": None,
            "media_decode_error_count": 0 if not core_failed else 1,
            "media_backpressure_events": None,
            "media_frame_timestamp_gap_ms_p95": None,
        },
        "issues": issues,
        "promotion": {
            "allowed": False,
            "target": "quest.device_link binary media stream capability descriptor",
            "reason": (
                "Rusty Quest broker media-stream runtime status is command/source-state "
                "evidence; live binary receiver counters with queue/drop/backpressure "
                "remain required"
            ),
        },
        "media_stream_runtime_status": {
            "schema": runtime_schema,
            "command_id": command_id,
            "session_id": session_id,
            "runtime_family": runtime_family,
            "compatibility_runtime": runtime_status.get("compatibility_runtime")
            or runtime_result.get("compatibility_runtime"),
            "status": runtime_result.get("status") or runtime_status.get("status"),
            "source": source_summary,
            "counters": counter_summary,
            "artifact_path": artifact_path,
        },
    }


def media_stream_runtime_sections(
    artifact: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if object_value(artifact.get("media_stream_runtime")):
        runtime_result = object_value(artifact.get("media_stream_runtime"))
        runtime_status = object_value(runtime_result.get("runtime_status")) or runtime_result
        return runtime_result, runtime_status, artifact
    runtime_result = artifact
    runtime_status = object_value(artifact.get("runtime_status")) or artifact
    return runtime_result, runtime_status, {}


def media_stream_source_runtime(
    runtime_result: dict[str, Any],
    runtime_status: dict[str, Any],
) -> dict[str, Any]:
    source_runtime = object_value(runtime_result.get("sender_source_runtime"))
    if source_runtime:
        return source_runtime
    return object_value(runtime_status.get("sender_source_runtime"))


def media_stream_source_summary(source_runtime: dict[str, Any]) -> dict[str, Any]:
    source = first_object(source_runtime.get("sources"))
    if not source and object_value(source_runtime.get("sender_source_runtime")):
        source = object_value(source_runtime.get("sender_source_runtime"))
    row = source or source_runtime
    return {
        "schema": row.get("schema"),
        "source_kind": row.get("source_kind"),
        "display_frame_source": row.get("display_frame_source"),
        "source_family": row.get("source_family"),
        "capture_authority": row.get("capture_authority"),
        "adapter_surface_only": row.get("adapter_surface_only"),
        "lab_only": row.get("lab_only"),
        "production_allowed": row.get("production_allowed"),
        "source_available": row.get("source_available"),
        "runtime_started": row.get("runtime_started"),
        "state": row.get("state") or row.get("status"),
        "reason": row.get("reason"),
        "connected_output_count": row.get("connected_output_count"),
        "source_count": source_runtime.get("source_count"),
    }


def media_stream_source_gate_ok(source_summary: dict[str, Any]) -> bool:
    source_kind = str(source_summary.get("source_kind") or source_summary.get("display_frame_source") or "")
    if source_kind != "shell_display_mirror_mediacodec_surface":
        return True
    return (
        source_summary.get("lab_only") is True
        and source_summary.get("production_allowed") is False
        and source_summary.get("capture_authority") == "shell_hidden_display_adapter"
    )


def media_stream_counter_summary(source_runtime: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for source in list_value(source_runtime.get("sources")):
        rows.extend(list_value(object_value(source).get("source_lanes")))
    rows.extend(list_value(source_runtime.get("source_lanes")))
    packet_count = sum_optional_int(rows, "packet_count")
    video_packet_count = sum_optional_int(rows, "video_packet_count")
    codec_config_packet_count = sum_optional_int(rows, "codec_config_packet_count")
    bytes_written = sum_optional_int(rows, "bytes_written")
    header_bytes = sum_optional_int(rows, "header_bytes")
    return {
        "lane_count": len(rows),
        "packet_count": packet_count,
        "video_packet_count": video_packet_count,
        "codec_config_packet_count": codec_config_packet_count,
        "bytes_written": bytes_written,
        "header_bytes": header_bytes,
        "high_rate_json_payload": any(object_value(row).get("high_rate_json_payload") is True for row in rows),
    }


def sum_optional_int(rows: list[Any], key: str) -> int | None:
    total = 0
    seen = False
    for row in rows:
        value = int_or_none(object_value(row).get(key))
        if value is not None:
            total += value
            seen = True
    return total if seen else None


def media_stream_runtime_local_endpoint(
    runtime_status: dict[str, Any],
    runtime_result: dict[str, Any],
) -> str:
    for lane in list_value(runtime_status.get("lanes")) + list_value(runtime_result.get("started_lanes")):
        row = object_value(lane)
        port = row.get("transport_port") or row.get("port")
        host = row.get("transport_bind_host") or row.get("bind_host") or "0.0.0.0"
        if port:
            return f"{host}:{port}"
    return "declared_by_broker_runtime"


def media_stream_runtime_remote_endpoint(
    runtime_result: dict[str, Any],
    source_runtime: dict[str, Any],
) -> str:
    for source in list_value(source_runtime.get("sources")) + [source_runtime]:
        row = object_value(source)
        for lane in list_value(row.get("source_lanes")):
            lane_row = object_value(lane)
            if lane_row.get("port"):
                return f"{row.get('host') or '127.0.0.1'}:{lane_row.get('port')}"
    for lane in list_value(runtime_result.get("started_lanes")):
        row = object_value(lane)
        if row.get("source_port"):
            return f"{row.get('source_host') or '127.0.0.1'}:{row.get('source_port')}"
    return "declared_by_broker_runtime"


def first_object(value: Any) -> dict[str, Any]:
    rows = list_value(value)
    return object_value(rows[0]) if rows else {}


def string_set(value: Any) -> set[str]:
    return {str(item) for item in value if str(item)} if isinstance(value, list) else set()


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "DEFAULT_QCL082_MEDIA_PORT",
    "DEFAULT_QCL082_PACKET_MAGIC",
    "MEDIA_STREAM_SESSION_SCHEMA",
    "MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE",
    "MEDIA_STREAM_RUNTIME_STATUS_SCHEMA",
    "qcl082_fixture_body",
    "qcl082_media_stream_session_body",
    "qcl082_media_stream_runtime_status_body",
]
