"""Quest device-link report adapter for Hostess session evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.bridge_command_routes import DEFAULT_RUNTIME_RECEIPT_STREAM
from tools.hostessctl.platform_defaults import (
    BROKER_LOCAL_FORWARD_PORT,
    BROKER_PORT,
)


QUEST_DEVICE_LINK_SCHEMA = "rusty.quest.device_link.v1"
QUEST_DEVICE_LINK_VALIDATION_SCHEMA = "rusty.quest.device_link.validation.v1"
QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA = "rusty.quest.device_link.stream_capability.v1"
QUEST_DEVICE_LINK_STREAM_CAPABILITY_VALIDATION_SCHEMA = (
    "rusty.quest.device_link.stream_capability.validation.v1"
)
QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_SCHEMA = (
    "rusty.quest.device_link.install_environment_test_suite.v1"
)
QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_VALIDATION_SCHEMA = (
    "rusty.quest.device_link.install_environment_test_suite.validation.v1"
)
REQUEST_STREAM_ID = "stream.hostess.makepad.bridge_command"
VALID_STATUS = {"pass", "warn", "fail", "skipped"}
VALID_STREAM_CAPABILITY_STATUS = {
    "usable",
    "usable_with_warnings",
    "candidate",
    "rejected",
    "blocked",
}
VALID_CONDITION_STATUS = {
    "satisfied",
    "missing",
    "blocked",
    "unknown",
    "candidate",
    "not_applicable",
}


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


def run_stream_capability_descriptor(args: argparse.Namespace) -> int:
    """Promote a connectivity probe report into a Quest device-link capability row."""

    source_path = Path(str(getattr(args, "input", "") or ""))
    report = json.loads(source_path.read_text(encoding="utf-8"))
    descriptor = build_stream_capability_descriptor_from_connectivity_probe(
        report,
        source_path=source_path,
    )
    validation = validate_stream_capability_descriptor(descriptor)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    validation_out = (
        Path(args.validation_out)
        if getattr(args, "validation_out", None)
        else out.with_name(f"{out.stem}.validation-report.json")
    )
    validation_out.parent.mkdir(parents=True, exist_ok=True)
    validation_out.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if getattr(args, "fail_on_error", False) and validation["status"] != "pass":
        return 2
    return 0


def run_install_test_suite_descriptor(args: argparse.Namespace) -> int:
    """Write the downloadable install/environment/protocol test-suite descriptor."""

    descriptor = build_install_test_suite_descriptor(
        suite_id=str(getattr(args, "suite_id", "") or ""),
        observed_at_utc=utc_now(),
    )
    validation = validate_install_test_suite_descriptor(descriptor)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    validation_out = (
        Path(args.validation_out)
        if getattr(args, "validation_out", None)
        else out.with_name(f"{out.stem}.validation-report.json")
    )
    validation_out.parent.mkdir(parents=True, exist_ok=True)
    validation_out.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if getattr(args, "fail_on_error", False) and validation["status"] != "pass":
        return 2
    return 0


def build_stream_capability_descriptor_from_connectivity_probe(
    report: dict[str, Any],
    *,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Build a measured stream-capability descriptor from a QCL probe report."""

    probe_id = str(report.get("probe_id") or "")
    if probe_id == "QCL-080":
        return build_qcl080_stream_capability_descriptor(report, source_path=source_path)
    if probe_id == "QCL-081":
        return build_qcl081_stream_capability_descriptor(report, source_path=source_path)
    if probe_id == "QCL-083":
        return build_qcl083_stream_capability_descriptor(report, source_path=source_path)
    raise SystemExit(f"stream capability descriptor is not implemented for {probe_id or 'unknown probe'}")


def build_qcl080_stream_capability_descriptor(
    report: dict[str, Any],
    *,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Build the measured QCL-080 app-owned UDP freshness descriptor."""

    transport = object_value(report.get("transport"))
    topology = object_value(report.get("topology"))
    host = object_value(report.get("host"))
    device = object_value(report.get("device"))
    measurements = object_value(report.get("measurements"))
    promotion = object_value(report.get("promotion"))
    udp_check = report_check(report, "protocol.udp_freshness")
    runtime_check = report_check(report, "runtime.qcl080_udp_sender")
    runtime_evidence = qcl080_runtime_evidence(runtime_check, udp_check)
    firewall_listener = object_value(host.get("firewall_listener"))
    requirements = stream_capability_requirements(
        report,
        transport=transport,
        runtime_evidence=runtime_evidence,
        firewall_listener=firewall_listener,
    )
    status = stream_capability_status(
        report,
        transport=transport,
        measurements=measurements,
        runtime_evidence=runtime_evidence,
        requirements=requirements,
    )
    interval_ms = float_or_none(runtime_evidence.get("interval_ms"))
    observed_rate_hz = round(1000.0 / interval_ms, 3) if interval_ms and interval_ms > 0 else None

    return {
        "$schema": QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA,
        "schema_version": 1,
        "capability_id": f"capability.qcl080.app_owned_udp.{safe_id(report.get('run_id'))}",
        "bridge_route_id": "bridge_route.quest_device_link.qcl080.app_owned_udp_freshness",
        "stream_id": "stream.quest.device_link.qcl080.udp_freshness",
        "semantic_family": "device_link_diagnostic",
        "transport_kind": "udp",
        "payload_plane": "udp_datagram",
        "rate_class": "low_rate",
        "reliability": "sequenced_best_effort_loss_measured",
        "direction": str(topology.get("endpoint_direction") or "quest_to_host_lan"),
        "clock_policy": "runtime_sequence_host_arrival_timestamps",
        "queue_policy": "receiver_counts_unique_sequences_no_backpressure",
        "max_rate_hz": observed_rate_hz,
        "high_rate_json_payload": False,
        "status": status,
        "required_conditions": qcl080_required_conditions(
            requirements,
            report=report,
            transport=transport,
            runtime_evidence=runtime_evidence,
            firewall_listener=firewall_listener,
        ),
        "timing": timing_profile(
            rtt_strategy="host_arrival_sequence_only",
            clock_alignment="runtime_sequence_with_host_arrival_timestamps",
            metrics=[
                "udp_packets_sent",
                "udp_packets_received",
                "udp_loss_percent",
                "jitter_ms_p95",
                "observed_rate_hz",
            ],
            rtt_supported=False,
            fallback_timing_source="parallel_lsl_reference_or_protocol_ack_required_for_rtt",
        ),
        "test_slots": [
            test_slot(
                "QCL-080",
                "qcl-080-app-owned-udp-freshness-pass",
                "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-080 --udp-sender-source makepad-runtime --udp-port 18767 --out target\\connectivity-probe\\qcl-080-live.json",
                "Quest app-owned UDP freshness and host listener firewall coverage",
                metrics=[
                    "udp_packets_sent",
                    "udp_packets_received",
                    "udp_loss_percent",
                    "jitter_ms_p95",
                ],
            )
        ],
        "source_probe": {
            "schema": report.get("schema"),
            "probe_id": report.get("probe_id"),
            "run_id": report.get("run_id"),
            "observed_at_utc": report.get("observed_at_utc"),
            "status": report.get("status"),
            "classification": report.get("classification"),
            "promotion_allowed": promotion.get("allowed"),
            "promotion_target": promotion.get("target"),
            "promotion_reason": promotion.get("reason"),
            "artifact_path": str(source_path) if source_path else "",
            "artifact_sha256": sha256_file(source_path) if source_path else "",
        },
        "topology_evidence": {
            "owner": topology.get("owner"),
            "network_provider": topology.get("network_provider"),
            "requires_existing_wifi": topology.get("requires_existing_wifi"),
            "requires_adb_for_setup_or_observation": topology.get("requires_adb"),
            "requires_termux": topology.get("requires_termux"),
            "experimental": topology.get("experimental"),
        },
        "transport_evidence": {
            "route": transport.get("route"),
            "protocol_role": transport.get("protocol_role"),
            "endpoint_source": transport.get("endpoint_source"),
            "payload_class": transport.get("payload_class"),
            "local_endpoint": transport.get("local_endpoint"),
            "remote_endpoint": transport.get("remote_endpoint"),
        },
        "runtime_evidence": runtime_evidence,
        "host_listener": {
            "program": firewall_listener.get("program"),
            "protocol": firewall_listener.get("protocol"),
            "bind_host": firewall_listener.get("bind_host"),
            "port": firewall_listener.get("port"),
            "active_profiles": string_list(firewall_listener.get("active_profiles")),
            "allowed_on_active_profile": firewall_listener.get("allowed_on_active_profile"),
            "matching_rule_count": firewall_listener.get("matching_rule_count"),
        },
        "device_identity": {
            "model": device.get("model"),
            "adb_state": device.get("adb_state"),
            "wifi_ipv4": device.get("wifi_ipv4"),
            "wifi_prefix_length": device.get("wifi_prefix_length"),
            "serial_redacted": device.get("serial_redacted", True),
        },
        "measurements": {
            "udp_packets_sent": int_or_none(measurements.get("udp_packets_sent")),
            "udp_packets_received": int_or_none(measurements.get("udp_packets_received")),
            "udp_loss_percent": float_or_none(measurements.get("udp_loss_percent")),
            "jitter_ms_p95": float_or_none(measurements.get("jitter_ms_p95")),
            "reconnect_attempts": int_or_none(measurements.get("reconnect_attempts")),
            "observed_rate_hz": observed_rate_hz,
        },
        "requirements": requirements,
        "warnings": stream_capability_warnings(report, requirements),
        "recommended_for": [
            "Quest app-owned low-rate UDP freshness checks",
            "runtime-to-host telemetry paths where loss is acceptable",
            "operator readiness diagnostics for same-Wi-Fi topology",
        ],
        "not_for": [
            "applied command feedback",
            "high-rate camera or media payloads",
            "production host listener claims until the signed Hostess/WPF firewall rule is proven",
        ],
    }


def build_qcl081_stream_capability_descriptor(
    report: dict[str, Any],
    *,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Build the measured QCL-081 LSL clocked-sample descriptor."""

    transport = object_value(report.get("transport"))
    topology = object_value(report.get("topology"))
    device = object_value(report.get("device"))
    measurements = object_value(report.get("measurements"))
    promotion = object_value(report.get("promotion"))
    runtime_evidence = qcl081_runtime_evidence(report)
    requirements = qcl081_stream_capability_requirements(
        report,
        transport=transport,
        runtime_evidence=runtime_evidence,
        measurements=measurements,
    )
    status = qcl081_stream_capability_status(
        report,
        transport=transport,
        runtime_evidence=runtime_evidence,
        measurements=measurements,
        requirements=requirements,
    )

    return {
        "$schema": QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA,
        "schema_version": 1,
        "capability_id": f"capability.qcl081.lsl_clocked_samples.{safe_id(report.get('run_id'))}",
        "bridge_route_id": "bridge_route.quest_device_link.qcl081.lsl_clocked_samples",
        "stream_id": "stream.protocol_fit.lsl.clocked_samples",
        "semantic_family": "study_stream",
        "transport_kind": "lsl",
        "payload_plane": "lsl_sample",
        "rate_class": "sample_clocked",
        "reliability": "lsl_ordered_stream_with_sample_continuity",
        "direction": str(topology.get("endpoint_direction") or "lsl_multicast_discovery_plus_tcp_samples"),
        "clock_policy": "lsl_time_correction_reference",
        "queue_policy": "bounded_recent_samples_with_sequence_continuity_check",
        "max_rate_hz": 500,
        "high_rate_json_payload": False,
        "status": status,
        "required_conditions": qcl081_required_conditions(
            requirements,
            report=report,
            transport=transport,
            runtime_evidence=runtime_evidence,
        ),
        "timing": timing_profile(
            rtt_strategy="lsl_time_correction_reference",
            clock_alignment="lsl_clock_offset_and_sample_timestamps",
            metrics=[
                "lsl_discovery_ms",
                "lsl_samples_requested",
                "lsl_samples_received",
                "lsl_sample_loss_percent",
            ],
            rtt_supported=True,
            fallback_timing_source="quest_or_broker_owned_lsl_outlet_required",
        ),
        "test_slots": [
            test_slot(
                "QCL-081",
                "qcl-081-lsl-loopback-pass",
                "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-081 --lsl-source quest-runtime --out target\\connectivity-probe\\qcl081-live-quest-runtime.json",
                "LSL discovery, sample continuity, and Quest/broker-owned producer evidence",
                metrics=[
                    "lsl_discovery_ms",
                    "lsl_samples_received",
                    "lsl_sample_loss_percent",
                ],
            )
        ],
        "source_probe": {
            "schema": report.get("schema"),
            "probe_id": report.get("probe_id"),
            "run_id": report.get("run_id"),
            "observed_at_utc": report.get("observed_at_utc"),
            "status": report.get("status"),
            "classification": report.get("classification"),
            "promotion_allowed": promotion.get("allowed"),
            "promotion_target": promotion.get("target"),
            "promotion_reason": promotion.get("reason"),
            "artifact_path": str(source_path) if source_path else "",
            "artifact_sha256": sha256_file(source_path) if source_path else "",
        },
        "topology_evidence": {
            "owner": topology.get("owner"),
            "network_provider": topology.get("network_provider"),
            "requires_existing_wifi": topology.get("requires_existing_wifi"),
            "requires_adb_for_setup_or_observation": topology.get("requires_adb"),
            "requires_termux": topology.get("requires_termux"),
            "experimental": topology.get("experimental"),
        },
        "transport_evidence": {
            "route": transport.get("route"),
            "protocol_role": transport.get("protocol_role"),
            "endpoint_source": transport.get("endpoint_source"),
            "payload_class": transport.get("payload_class"),
            "local_endpoint": transport.get("local_endpoint"),
            "remote_endpoint": transport.get("remote_endpoint"),
        },
        "runtime_evidence": runtime_evidence,
        "device_identity": {
            "model": device.get("model"),
            "adb_state": device.get("adb_state"),
            "wifi_ipv4": device.get("wifi_ipv4"),
            "wifi_prefix_length": device.get("wifi_prefix_length"),
            "serial_redacted": device.get("serial_redacted", True),
        },
        "measurements": {
            "lsl_discovery_ms": float_or_none(measurements.get("lsl_discovery_ms")),
            "lsl_samples_requested": int_or_none(measurements.get("lsl_samples_requested")),
            "lsl_samples_received": int_or_none(measurements.get("lsl_samples_received")),
            "lsl_sample_loss_percent": float_or_none(measurements.get("lsl_sample_loss_percent")),
            "reconnect_attempts": int_or_none(measurements.get("reconnect_attempts")),
        },
        "requirements": requirements,
        "warnings": qcl081_stream_capability_warnings(report, requirements),
        "recommended_for": [
            "clocked study and biosignal sample streams",
            "parallel timing references for UDP, OSC, ZeroMQ, or media routes",
            "operator diagnostics where discovery and sample continuity are explicit",
        ],
        "not_for": [
            "command authority",
            "bulk media payloads",
            "Quest-runtime promotion until a Quest-owned, study-adapter-owned, or broker-owned LSL producer is proven",
        ],
    }


def build_qcl083_stream_capability_descriptor(
    report: dict[str, Any],
    *,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Build the measured QCL-083 OSC runtime round-trip descriptor."""

    transport = object_value(report.get("transport"))
    topology = object_value(report.get("topology"))
    device = object_value(report.get("device"))
    measurements = object_value(report.get("measurements"))
    promotion = object_value(report.get("promotion"))
    runtime_evidence = qcl083_runtime_evidence(report)
    requirements = qcl083_stream_capability_requirements(
        report,
        transport=transport,
        runtime_evidence=runtime_evidence,
        measurements=measurements,
    )
    status = qcl083_stream_capability_status(
        report,
        transport=transport,
        runtime_evidence=runtime_evidence,
        measurements=measurements,
        requirements=requirements,
    )

    return {
        "$schema": QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA,
        "schema_version": 1,
        "capability_id": f"capability.qcl083.osc_round_trip.{safe_id(report.get('run_id'))}",
        "bridge_route_id": "bridge_route.quest_device_link.qcl083.osc_exchange",
        "stream_id": "stream.protocol_fit.osc.round_trip",
        "semantic_family": "control_or_low_rate_telemetry",
        "transport_kind": "osc_udp",
        "payload_plane": "osc_message",
        "rate_class": "control",
        "reliability": "udp_ack_measured",
        "direction": str(topology.get("endpoint_direction") or "host_to_quest_runtime_with_ack"),
        "clock_policy": "host_send_quest_ack_timestamps_with_offset_estimate",
        "queue_policy": "bounded_request_ack_window",
        "max_rate_hz": 60,
        "high_rate_json_payload": False,
        "status": status,
        "required_conditions": qcl083_required_conditions(
            requirements,
            report=report,
            transport=transport,
            runtime_evidence=runtime_evidence,
        ),
        "timing": timing_profile(
            rtt_strategy="native_round_trip_ack",
            clock_alignment="host_send_quest_ack_timestamps_with_offset_estimate",
            metrics=[
                "osc_rtt_ms_p95",
                "osc_quest_processing_ms_p95",
                "osc_estimated_one_way_ms_p95",
                "osc_clock_offset_estimate_ms_median",
                "osc_clock_offset_jitter_ms_p95",
            ],
            rtt_supported=True,
            fallback_timing_source="parallel_lsl_reference",
        ),
        "test_slots": [
            test_slot(
                "QCL-083",
                "qcl-083-osc-loopback-pass",
                "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-083 --osc-source quest-runtime --out target\\connectivity-probe\\qcl083-live-quest-runtime.json",
                "OSC message shape, Quest-runtime payload exchange, and ACK timing metrics",
                metrics=[
                    "osc_messages_received",
                    "osc_loss_percent",
                    "osc_rtt_ms_p95",
                    "osc_estimated_one_way_ms_p95",
                ],
            )
        ],
        "source_probe": {
            "schema": report.get("schema"),
            "probe_id": report.get("probe_id"),
            "run_id": report.get("run_id"),
            "observed_at_utc": report.get("observed_at_utc"),
            "status": report.get("status"),
            "classification": report.get("classification"),
            "promotion_allowed": promotion.get("allowed"),
            "promotion_target": promotion.get("target"),
            "promotion_reason": promotion.get("reason"),
            "artifact_path": str(source_path) if source_path else "",
            "artifact_sha256": sha256_file(source_path) if source_path else "",
        },
        "topology_evidence": {
            "owner": topology.get("owner"),
            "network_provider": topology.get("network_provider"),
            "requires_existing_wifi": topology.get("requires_existing_wifi"),
            "requires_adb_for_setup_or_observation": topology.get("requires_adb"),
            "requires_termux": topology.get("requires_termux"),
            "experimental": topology.get("experimental"),
        },
        "transport_evidence": {
            "route": transport.get("route"),
            "protocol_role": transport.get("protocol_role"),
            "endpoint_source": transport.get("endpoint_source"),
            "payload_class": transport.get("payload_class"),
            "local_endpoint": transport.get("local_endpoint"),
            "remote_endpoint": transport.get("remote_endpoint"),
        },
        "runtime_evidence": runtime_evidence,
        "device_identity": {
            "model": device.get("model"),
            "adb_state": device.get("adb_state"),
            "wifi_ipv4": device.get("wifi_ipv4"),
            "wifi_prefix_length": device.get("wifi_prefix_length"),
            "serial_redacted": device.get("serial_redacted", True),
        },
        "measurements": {
            "osc_messages_requested": int_or_none(measurements.get("osc_messages_requested")),
            "osc_messages_received": int_or_none(measurements.get("osc_messages_received")),
            "osc_loss_percent": float_or_none(measurements.get("osc_loss_percent")),
            "osc_rtt_ms_p95": float_or_none(measurements.get("osc_rtt_ms_p95")),
            "osc_quest_processing_ms_p95": float_or_none(
                measurements.get("osc_quest_processing_ms_p95")
            ),
            "osc_estimated_one_way_ms_p95": float_or_none(
                measurements.get("osc_estimated_one_way_ms_p95")
            ),
            "osc_clock_offset_estimate_ms_median": float_or_none(
                measurements.get("osc_clock_offset_estimate_ms_median")
            ),
            "osc_clock_offset_jitter_ms_p95": float_or_none(
                measurements.get("osc_clock_offset_jitter_ms_p95")
            ),
        },
        "requirements": requirements,
        "warnings": qcl083_stream_capability_warnings(report, requirements),
        "recommended_for": [
            "Quest app-owned low-rate OSC control packets",
            "status messages with native ACK timing",
            "operator readiness diagnostics for same-Wi-Fi Quest runtime routes",
        ],
        "not_for": [
            "bulk media",
            "lossless sample streams without sequence repair",
            "strict command authority without Manifold acceptance",
        ],
    }


def validate_stream_capability_descriptor(descriptor: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if descriptor.get("$schema") != QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA:
        errors.append("unsupported stream capability descriptor schema")
    validate_stream_capability(descriptor, errors)

    status = str(descriptor.get("status") or "")
    if status not in VALID_STREAM_CAPABILITY_STATUS:
        errors.append("status must be usable, usable_with_warnings, candidate, rejected, or blocked")

    measurements = object_value(descriptor.get("measurements"))
    runtime = object_value(descriptor.get("runtime_evidence"))
    transport = object_value(descriptor.get("transport_evidence"))
    source_probe = object_value(descriptor.get("source_probe"))
    if status in {"usable", "usable_with_warnings"}:
        probe_id = str(source_probe.get("probe_id") or "")
        if probe_id == "QCL-080":
            if source_probe.get("promotion_allowed") is not True:
                errors.append("usable QCL-080 capabilities require a promoted QCL-080 source probe")
            if transport.get("endpoint_source") != "app_owned_runtime_udp_sender":
                errors.append("usable QCL-080 capabilities require an app-owned runtime UDP sender")
            if runtime.get("status") != "sent" or runtime.get("socket_owner") != "app-owned":
                errors.append("usable QCL-080 capabilities require sent app-owned runtime evidence")
            packets_sent = int_or_none(runtime.get("packets_sent"))
            if packets_sent is None or packets_sent < 1:
                errors.append("usable QCL-080 capabilities require runtime packets_sent evidence")
            packets_received = int_or_none(measurements.get("udp_packets_received"))
            if packets_received is None or packets_received < 1:
                errors.append("usable QCL-080 capabilities require received UDP packets")
        elif probe_id == "QCL-083":
            if source_probe.get("promotion_allowed") is not True:
                errors.append("usable QCL-083 capabilities require a promoted QCL-083 source probe")
            if transport.get("endpoint_source") != "quest-runtime":
                errors.append("usable QCL-083 capabilities require Quest-runtime endpoint evidence")
            if runtime.get("status") != "pass":
                errors.append("usable QCL-083 capabilities require passing runtime OSC evidence")
            messages_received = int_or_none(measurements.get("osc_messages_received"))
            if messages_received is None or messages_received < 1:
                errors.append("usable QCL-083 capabilities require received OSC ACK evidence")
        elif probe_id == "QCL-081":
            if source_probe.get("promotion_allowed") is not True:
                errors.append("usable QCL-081 capabilities require a promoted QCL-081 source probe")
            if not qcl081_promotable_lsl_owner(transport.get("endpoint_source")):
                errors.append(
                    "usable QCL-081 capabilities require Quest-runtime, study-adapter, or broker-owned LSL evidence"
                )
            if transport.get("endpoint_source") == "manifold-lsl-broker":
                if runtime.get("evidence_tier") != "broker_owned":
                    errors.append("usable QCL-081 Manifold LSL broker capabilities require broker_owned evidence")
                if runtime.get("authority_owner") != "rusty.manifold.transport":
                    errors.append("usable QCL-081 Manifold LSL broker capabilities require Manifold transport authority")
                if runtime.get("bridge_route_evidence_status") != "pass":
                    errors.append("usable QCL-081 Manifold LSL broker capabilities require passing route evidence")
            if runtime.get("status") != "pass":
                errors.append("usable QCL-081 capabilities require passing runtime LSL evidence")
            samples_received = int_or_none(measurements.get("lsl_samples_received"))
            if samples_received is None or samples_received < 1:
                errors.append("usable QCL-081 capabilities require received LSL samples")
        else:
            errors.append("usable stream capabilities require a supported promoted source probe")

    for requirement in list_value(descriptor.get("requirements")):
        if not isinstance(requirement, dict):
            continue
        requirement_status = str(requirement.get("status") or "")
        if requirement_status in {"missing", "blocked", "unknown"}:
            warnings.append(
                f"{requirement.get('requirement_id', 'requirement')} is {requirement_status}"
            )

    return {
        "$schema": QUEST_DEVICE_LINK_STREAM_CAPABILITY_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "descriptor_status": descriptor.get("status"),
        "capability_id": descriptor.get("capability_id"),
        "errors": errors,
        "warnings": warnings,
    }


def build_install_test_suite_descriptor(
    *,
    suite_id: str = "",
    observed_at_utc: str = "",
) -> dict[str, Any]:
    """Describe the full install/environment/protocol test suite."""

    capabilities = default_stream_capabilities()
    return {
        "$schema": QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_SCHEMA,
        "schema_version": 1,
        "suite_id": safe_id(suite_id or "quest-device-link-install-environment"),
        "observed_at_utc": observed_at_utc,
        "scope": {
            "host_os": "windows",
            "device_family": "meta_quest",
            "frontends": ["hostessctl", "wpf", "makepad", "future_frontends"],
            "network_topologies": [
                "usb_adb",
                "router_or_existing_wifi",
                "pc_hotspot",
                "phone_hotspot",
                "travel_router",
                "bluetooth_classic_rfcomm",
                "bluetooth_le_gatt",
            ],
        },
        "authority": {
            "descriptor_owner": "rusty.quest.device_link",
            "execution_owner": "rusty.hostess.connectivity_probe",
            "ui_role": "requester_and_inspector",
            "command_authority": "rusty.manifold.command",
            "note": (
                "Frontends can request tests and render reports; they do not decide "
                "dependency validity, protocol promotion, or command authority."
            ),
        },
        "environment_checks": install_suite_environment_checks(),
        "protocol_capabilities": capabilities,
        "test_slots": install_suite_test_slots(),
        "result_contracts": [
            QUEST_DEVICE_LINK_SCHEMA,
            QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA,
            "rusty.quest.connectivity_topology_probe.v1",
            "rusty.hostess.companion.readiness_report.v1",
            "rusty.hostess.companion.session.v1",
        ],
        "operator_ui_groups": [
            {
                "group_id": "group.install_environment",
                "label": "Install Environment",
                "covers": ["host", "toolchain", "output_directory"],
            },
            {
                "group_id": "group.device_link",
                "label": "Device Link",
                "covers": ["adb", "device_identity", "adb_forward", "broker"],
            },
            {
                "group_id": "group.network_firewall",
                "label": "Network And Firewall",
                "covers": ["network_adapters", "windows_firewall", "listener_rules"],
            },
            {
                "group_id": "group.protocol_latency",
                "label": "Protocols And RTT",
                "covers": [
                    "udp",
                    "lsl",
                    "media_tcp_binary",
                    "osc",
                    "zeromq",
                    "bluetooth_rfcomm",
                    "bluetooth_gatt",
                ],
            },
        ],
        "promotion_policy": {
            "requires_fixture_validation": True,
            "requires_live_target_topology": True,
            "requires_required_conditions": True,
            "requires_timing_strategy": True,
            "requires_rtt_when_supported": True,
            "parallel_lsl_reference": (
                "Use QCL-081 LSL timing in parallel for protocols that have no "
                "native RTT/ACK or need an independent clock-alignment reference."
            ),
        },
    }


def validate_install_test_suite_descriptor(descriptor: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if descriptor.get("$schema") != QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_SCHEMA:
        errors.append("unsupported install test suite schema")
    if str(descriptor.get("suite_id") or "").strip() == "":
        errors.append("suite_id must not be empty")

    environment_checks = list_value(descriptor.get("environment_checks"))
    test_slots = list_value(descriptor.get("test_slots"))
    capabilities = list_value(descriptor.get("protocol_capabilities"))
    if not environment_checks:
        errors.append("environment_checks must not be empty")
    if not test_slots:
        errors.append("test_slots must not be empty")
    if not capabilities:
        errors.append("protocol_capabilities must not be empty")

    required_categories = {"host", "toolchain", "network", "firewall", "device", "protocol", "timing"}
    observed_categories = {
        str(check.get("category") or "")
        for check in environment_checks
        if isinstance(check, dict)
    }
    for category in sorted(required_categories - observed_categories):
        errors.append(f"environment_checks missing category {category}")

    for capability in capabilities:
        validate_stream_capability(object_value(capability), errors)

    required_transports = {
        "manifold_websocket",
        "websocket",
        "udp",
        "lsl",
        "osc_udp",
        "zeromq",
        "bluetooth_rfcomm",
        "bluetooth_gatt",
        "tcp_binary",
    }
    observed_transports = {
        str(capability.get("transport_kind") or "")
        for capability in capabilities
        if isinstance(capability, dict)
    }
    for transport in sorted(required_transports - observed_transports):
        errors.append(f"protocol_capabilities missing transport {transport}")

    required_probe_ids = {
        "QCL-000",
        "QCL-010",
        "QCL-011",
        "QCL-050",
        "QCL-051",
        "QCL-080",
        "QCL-081",
        "QCL-082",
        "QCL-083",
        "QCL-084",
        "QCL-079",
    }
    observed_probe_ids = {
        str(slot.get("probe_id") or "")
        for slot in test_slots
        if isinstance(slot, dict)
    }
    for probe_id in sorted(required_probe_ids - observed_probe_ids):
        errors.append(f"test_slots missing {probe_id}")

    for slot in test_slots:
        row = object_value(slot)
        if not str(row.get("slot_id") or "").strip():
            errors.append("test slot requires slot_id")
        if not str(row.get("live_command") or "").strip():
            warnings.append(f"test slot {row.get('slot_id', '<unknown>')} has no live_command")
        if not list_value(row.get("metrics")):
            warnings.append(f"test slot {row.get('slot_id', '<unknown>')} has no metrics")

    return {
        "$schema": QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "suite_id": descriptor.get("suite_id"),
        "environment_check_count": len(environment_checks),
        "test_slot_count": len(test_slots),
        "protocol_capability_count": len(capabilities),
        "errors": errors,
        "warnings": warnings,
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
        capability_row(
            capability_id="capability.command.hostess_makepad_bridge",
            bridge_route_id="bridge_route.hostess.makepad.manifold_websocket",
            stream_id=REQUEST_STREAM_ID,
            semantic_family="command",
            transport_kind="manifold_websocket",
            payload_plane="json_event",
            rate_class="control",
            reliability="ordered_ack_required",
            direction="host_to_quest_runtime",
            clock_policy="host_request_runtime_receipt",
            queue_policy="bounded_command_queue",
            max_rate_hz=5,
            status="usable",
            conditions=[
                condition(
                    "condition.command.manifold_broker_forward",
                    "network",
                    "unknown",
                    remediation="Run companion-readiness with broker checks; prepare the ADB forward for /manifold/v1/events.",
                    evidence_refs=["check.network.broker_adb_forward", "check.network.broker_forwarded_port"],
                ),
                condition(
                    "condition.command.runtime_subscriber_receipts",
                    "runtime",
                    "unknown",
                    remediation="Run companion-session run and require runtime_accepted/applied receipts.",
                    evidence_refs=["runtime.hostess_makepad.bridge_command"],
                ),
            ],
            timing=timing_profile(
                rtt_strategy="command_stage_receipts",
                clock_alignment="host_request_runtime_receipt_delta",
                metrics=[
                    "sent",
                    "transport_ok",
                    "authority_accepted",
                    "runtime_accepted",
                    "applied",
                ],
                rtt_supported=True,
                fallback_timing_source="app_private_json_receipt",
            ),
            test_slots=[
                test_slot(
                    "QCL-000",
                    "qcl-000-usb-adb-pass",
                    "python tools\\hostessctl\\hostessctl.py companion-session run --out target\\companion-session\\session.json",
                    "Manifold broker command feedback with runtime receipt stages",
                    metrics=["sent", "transport_ok", "authority_accepted", "runtime_accepted", "applied"],
                )
            ],
            recommended_for=["operator commands", "runtime receipt probes"],
            not_for=["camera frames", "biosignal sample streams"],
        ),
        capability_row(
            capability_id="capability.protocol.websocket_generic",
            bridge_route_id="bridge_route.quest_device_link.qcl079.websocket_generic",
            stream_id="stream.protocol_fit.websocket.generic",
            semantic_family="generic_data_protocol",
            transport_kind="websocket",
            payload_plane="bounded_text_or_binary_message",
            rate_class="low_or_mid_rate",
            reliability="ordered_message_ack_measured",
            direction="peer_to_peer_socket_exchange",
            clock_policy="protocol_ack_timestamps",
            queue_policy="bounded_message_exchange_not_command_authority",
            max_rate_hz=120,
            status="candidate",
            conditions=[
                condition(
                    "condition.websocket.http_upgrade",
                    "protocol",
                    "unknown",
                    remediation="Run QCL-079 host-loopback for protocol fit, or broker-owned with Manifold stream route descriptor/evidence for promotion.",
                    evidence_refs=["protocol.websocket_handshake"],
                ),
                condition(
                    "condition.websocket.generic_data_boundary",
                    "authority",
                    "unknown",
                    remediation="Keep generic WebSocket separate from Manifold command acceptance and high-rate media routes; reject command/control WebSocket descriptors.",
                    evidence_refs=[
                        "protocol.websocket_not_command_authority",
                        "protocol.websocket_high_rate_media_guard",
                    ],
                ),
            ],
            timing=timing_profile(
                rtt_strategy="echo_round_trip_ack",
                clock_alignment="host_send_echo_receive_delta",
                metrics=[
                    "websocket_messages_received",
                    "websocket_loss_percent",
                    "websocket_echo_ms",
                ],
                rtt_supported=True,
                fallback_timing_source="parallel_lsl_reference_for_cross_runtime_timing",
            ),
            test_slots=[
                test_slot(
                    "QCL-079",
                    "qcl-079-websocket-loopback-pass",
                    "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-079 --websocket-source host-loopback --out target\\connectivity-probe\\qcl079-live-host-loopback.json",
                    "Generic WebSocket handshake, bounded message exchange, and authority boundary",
                    metrics=[
                        "websocket_messages_received",
                        "websocket_loss_percent",
                        "websocket_echo_ms",
                    ],
                ),
                test_slot(
                    "QCL-079",
                    "qcl-079-manifold-websocket-broker",
                    "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-079 --websocket-source broker-owned-websocket --websocket-route-descriptor S:\\Work\\repos\\active\\rusty-manifold\\fixtures\\bridge-route\\stream-websocket-ordered-route.json --websocket-route-evidence S:\\Work\\repos\\active\\rusty-manifold\\fixtures\\bridge-route\\stream-websocket-ordered-evidence.json --out target\\connectivity-probe\\qcl079-live-manifold-websocket-broker.json --fail-on-error",
                    "Broker-owned generic WebSocket stream bridge evidence, separate from command authority",
                    metrics=[
                        "websocket_messages_received",
                        "websocket_loss_percent",
                        "websocket_echo_ms",
                    ],
                )
            ],
            recommended_for=["generic low/mid-rate message protocols after broker or runtime endpoint evidence"],
            not_for=["Manifold command authority", "high-rate media payloads"],
        ),
        capability_row(
            capability_id="capability.biosignal.lsl_clocked_samples",
            bridge_route_id="bridge_route.quest_device_link.qcl081.lsl_clocked_samples",
            stream_id="stream.protocol_fit.lsl.clocked_samples",
            semantic_family="biosignal_or_clocked_samples",
            transport_kind="lsl",
            payload_plane="lsl_sample",
            rate_class="sample_clocked",
            reliability="sample_clocked_best_effort",
            direction="sensor_runtime_or_host_to_peer",
            clock_policy="source_clock_lsl_time_correction",
            queue_policy="bounded_recent_samples",
            max_rate_hz=500,
            status="candidate",
            conditions=[
                condition(
                    "condition.lsl.library_available",
                    "dependency",
                    "unknown",
                    remediation="Install/provide pylsl or liblsl for the process that owns the stream.",
                    evidence_refs=["protocol.lsl_discovery"],
                ),
                condition(
                    "condition.lsl.multicast_or_known_endpoint_reachable",
                    "network",
                    "unknown",
                    remediation="Run QCL-081 on the target topology; firewall and router multicast behavior must be measured.",
                    evidence_refs=["protocol.lsl_discovery", "protocol.lsl_sample_continuity"],
                ),
            ],
            timing=timing_profile(
                rtt_strategy="lsl_time_correction",
                clock_alignment="lsl_clock_offset_and_sample_timestamps",
                metrics=[
                    "lsl_discovery_ms",
                    "lsl_samples_requested",
                    "lsl_samples_received",
                    "lsl_sample_loss_percent",
                ],
                rtt_supported=True,
                fallback_timing_source="host_loopback_dependency_smoke_then_quest_runtime_probe",
            ),
            test_slots=[
                test_slot(
                    "QCL-081",
                    "qcl-081-lsl-loopback-pass",
                    "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-081 --lsl-source host-loopback --out target\\connectivity-probe\\qcl081-live-host-loopback.json",
                    "LSL discovery and sample continuity",
                    metrics=["lsl_discovery_ms", "lsl_samples_received", "lsl_sample_loss_percent"],
                )
            ],
            recommended_for=["clocked biosignal samples", "parallel timing reference for other streams"],
            not_for=["command authority", "bulk media payloads"],
        ),
        capability_row(
            capability_id="capability.telemetry.pose_udp",
            bridge_route_id="bridge_route.quest_device_link.qcl080.udp_freshness",
            stream_id="stream.motion.object_pose",
            semantic_family="pose_or_low_rate_telemetry",
            transport_kind="udp",
            payload_plane="udp_datagram",
            rate_class="low_rate",
            reliability="latest_value_loss_tolerant",
            direction="runtime_to_broker_or_host",
            clock_policy="runtime_timestamp",
            queue_policy="drop_oldest_latest_value",
            max_rate_hz=90,
            status="candidate",
            conditions=[
                condition(
                    "condition.udp.host_listener_firewall",
                    "firewall",
                    "unknown",
                    remediation="Use a fixed product listener port and a scoped inbound rule for the signed Hostess/WPF executable.",
                    evidence_refs=["host.windows_firewall_listener"],
                ),
                condition(
                    "condition.udp.quest_and_host_same_topology",
                    "network",
                    "unknown",
                    remediation="Run QCL-010/QCL-011 first, then QCL-080 on the same topology.",
                    evidence_refs=["topology.same_subnet", "protocol.udp_freshness"],
                ),
            ],
            timing=timing_profile(
                rtt_strategy="host_arrival_sequence_only",
                clock_alignment="runtime_timestamp_or_parallel_lsl_reference",
                metrics=[
                    "udp_packets_sent",
                    "udp_packets_received",
                    "udp_loss_percent",
                    "jitter_ms_p95",
                ],
                rtt_supported=False,
                fallback_timing_source="parallel_lsl_reference_or_protocol_ack_for_rtt",
            ),
            test_slots=[
                test_slot(
                    "QCL-080",
                    "qcl-080-app-owned-udp-freshness-pass",
                    "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-080 --udp-sender-source makepad-runtime --udp-port 18767 --out target\\connectivity-probe\\qcl080-live.json",
                    "Quest app-owned UDP freshness and loss/jitter counters",
                    metrics=["udp_packets_sent", "udp_packets_received", "udp_loss_percent", "jitter_ms_p95"],
                )
            ],
            recommended_for=["low-latency pose telemetry", "freshness checks"],
            not_for=["applied command feedback", "lossless samples without sequence repair"],
        ),
        capability_row(
            capability_id="capability.control.osc_round_trip",
            bridge_route_id="bridge_route.quest_device_link.qcl083.osc_exchange",
            stream_id="stream.protocol_fit.osc.round_trip",
            semantic_family="control_or_low_rate_telemetry",
            transport_kind="osc_udp",
            payload_plane="osc_message",
            rate_class="control",
            reliability="udp_ack_measured",
            direction="host_to_quest_runtime_with_ack",
            clock_policy="host_send_quest_process_host_ack",
            queue_policy="bounded_request_ack_window",
            max_rate_hz=60,
            status="candidate",
            conditions=[
                condition(
                    "condition.osc.message_shape",
                    "protocol",
                    "unknown",
                    remediation="Run QCL-083 and reject malformed address/typetag/payload combinations.",
                    evidence_refs=["protocol.osc_message_shape"],
                ),
                condition(
                    "condition.osc.quest_runtime_endpoint",
                    "runtime",
                    "unknown",
                    remediation="Use the Hostess Android QCL-083 action or the future Rusty Quest runtime endpoint.",
                    evidence_refs=["protocol.osc_payload_exchange"],
                ),
            ],
            timing=timing_profile(
                rtt_strategy="native_round_trip_ack",
                clock_alignment="host_send_quest_ack_timestamps_with_offset_estimate",
                metrics=[
                    "osc_rtt_ms_p95",
                    "osc_quest_processing_ms_p95",
                    "osc_estimated_one_way_ms_p95",
                    "osc_clock_offset_estimate_ms_median",
                    "osc_clock_offset_jitter_ms_p95",
                ],
                rtt_supported=True,
                fallback_timing_source="parallel_lsl_reference",
            ),
            test_slots=[
                test_slot(
                    "QCL-083",
                    "qcl-083-osc-loopback-pass",
                    "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-083 --osc-source quest-runtime --out target\\connectivity-probe\\qcl083-live-quest-runtime.json",
                    "OSC message shape, payload exchange, and RTT metrics",
                    metrics=["osc_messages_received", "osc_loss_percent", "osc_rtt_ms_p95"],
                )
            ],
            recommended_for=["simple control packets", "status messages with native ACK timing"],
            not_for=["bulk media", "strict command authority without Manifold acceptance"],
        ),
        capability_row(
            capability_id="capability.protocol.zeromq_native_rust",
            bridge_route_id="bridge_route.quest_device_link.qcl084.zeromq_exchange",
            stream_id="stream.protocol_fit.zeromq.native_rust",
            semantic_family="generic_data_protocol",
            transport_kind="zeromq",
            payload_plane="binary_or_json_message",
            rate_class="low_or_mid_rate",
            reliability="pattern_defined_backpressure",
            direction="peer_to_peer_socket_exchange",
            clock_policy="protocol_ack_timestamps",
            queue_policy="bounded_receiver_queue_with_drop_counters",
            max_rate_hz=240,
            status="candidate",
            conditions=[
                condition(
                    "condition.zeromq.adapter_available",
                    "dependency",
                    "unknown",
                    remediation="Build and run the generic rusty-manifold-zmq adapter; Goofi remains only an example source profile.",
                    evidence_refs=["protocol.zeromq_dependency"],
                ),
                condition(
                    "condition.zeromq.pattern_declared",
                    "protocol",
                    "unknown",
                    remediation="Declare REQ/REP, PUB/SUB, or another supported pattern in the route descriptor before running.",
                    evidence_refs=["protocol.zeromq_payload_exchange"],
                ),
            ],
            timing=timing_profile(
                rtt_strategy="native_round_trip_ack_when_req_rep",
                clock_alignment="host_server_ack_timestamps_with_offset_estimate",
                metrics=[
                    "zeromq_rtt_ms_p95",
                    "zeromq_server_processing_ms_p95",
                    "zeromq_estimated_one_way_ms_p95",
                    "zeromq_clock_offset_estimate_ms_median",
                    "zeromq_clock_offset_jitter_ms_p95",
                ],
                rtt_supported=True,
                fallback_timing_source="parallel_lsl_reference_for_pub_sub",
            ),
            test_slots=[
                test_slot(
                    "QCL-084",
                    "qcl-084-zeromq-loopback-pass",
                    "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-084 --zeromq-source manifold-zmq-loopback --zeromq-pattern pub-sub --zeromq-manifold-root S:\\Work\\repos\\active\\rusty-manifold --out target\\connectivity-probe\\qcl084-live-manifold-zmq-loopback.json",
                    "Generic ZeroMQ adapter dependency, message exchange, and timing metrics",
                    metrics=["zeromq_messages_received", "zeromq_rtt_ms_p95"],
                )
            ],
            recommended_for=["native Rust protocol modules", "sidecar adapters", "Goofi-compatible source profiles"],
            not_for=["Goofi-specific object payloads as the generic protocol contract"],
        ),
        capability_row(
            capability_id="capability.bluetooth.rfcomm_control",
            bridge_route_id="bridge_route.quest_device_link.qcl050.bluetooth_rfcomm",
            stream_id="stream.protocol_fit.bluetooth.rfcomm_control",
            semantic_family="short_range_control",
            transport_kind="bluetooth_rfcomm",
            payload_plane="rfcomm_bytes",
            rate_class="control",
            reliability="stream_socket_ordered_bytes",
            direction="windows_client_to_quest_server",
            clock_policy="request_ack_round_trip",
            queue_policy="bounded_socket_exchange",
            max_rate_hz=20,
            status="candidate",
            conditions=[
                condition(
                    "condition.rfcomm.host_adapter_and_service",
                    "device",
                    "unknown",
                    remediation="Run QCL-050 with the Windows RFCOMM helper and verify adapter/service discovery.",
                    evidence_refs=["host.bluetooth_adapter", "host.bluetooth_service"],
                ),
                condition(
                    "condition.rfcomm.quest_pairing_and_permission",
                    "device",
                    "unknown",
                    remediation="Confirm Quest Bluetooth pairing/bond state and runtime permission before payload exchange.",
                    evidence_refs=["bluetooth.pairing_bond_state", "bluetooth.permission_state"],
                ),
            ],
            timing=timing_profile(
                rtt_strategy="native_round_trip_ack",
                clock_alignment="host_request_quest_ack_delta",
                metrics=["bluetooth_bytes_exchanged", "bluetooth_rtt_ms_p95"],
                rtt_supported=True,
                fallback_timing_source="parallel_lsl_reference_if_available",
            ),
            test_slots=[
                test_slot(
                    "QCL-050",
                    "qcl-050-rfcomm-control-pass",
                    "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-050 --bluetooth-payload-source android-rfcomm --out target\\connectivity-probe\\qcl050-live-rfcomm.json",
                    "Bluetooth Classic RFCOMM pairing, socket exchange, cleanup, and RTT",
                    metrics=["bluetooth_bytes_exchanged", "bluetooth_rtt_ms_p95"],
                )
            ],
            recommended_for=["short-range setup/control paths after pairing is proven"],
            not_for=["high-rate telemetry", "unpaired field deployment until service visibility is stable"],
        ),
        capability_row(
            capability_id="capability.bluetooth.ble_gatt_status",
            bridge_route_id="bridge_route.quest_device_link.qcl051.ble_gatt",
            stream_id="stream.protocol_fit.bluetooth.ble_gatt_status",
            semantic_family="short_range_status_or_control",
            transport_kind="bluetooth_gatt",
            payload_plane="gatt_characteristic",
            rate_class="control",
            reliability="characteristic_write_ack_measured",
            direction="windows_central_to_quest_gatt_server",
            clock_policy="write_ack_round_trip",
            queue_policy="bounded_characteristic_payloads",
            max_rate_hz=20,
            status="candidate",
            conditions=[
                condition(
                    "condition.ble.host_adapter_and_service",
                    "device",
                    "unknown",
                    remediation="Run QCL-051 with the Windows BLE/GATT helper and verify adapter/service readiness.",
                    evidence_refs=["host.bluetooth_adapter", "host.bluetooth_service"],
                ),
                condition(
                    "condition.ble.quest_gatt_permission",
                    "device",
                    "unknown",
                    remediation="Launch the app-owned Quest GATT server and verify permission plus status characteristic updates.",
                    evidence_refs=["device.bluetooth_adapter", "bluetooth.permission_state"],
                ),
            ],
            timing=timing_profile(
                rtt_strategy="native_write_ack_round_trip",
                clock_alignment="host_write_quest_status_ack_delta",
                metrics=["bluetooth_bytes_exchanged", "bluetooth_rtt_ms_p95"],
                rtt_supported=True,
                fallback_timing_source="parallel_lsl_reference_if_available",
            ),
            test_slots=[
                test_slot(
                    "QCL-051",
                    "qcl-051-ble-gatt-status-pass",
                    "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-051 --bluetooth-payload-source android-ble-gatt --out target\\connectivity-probe\\qcl051-live-ble-gatt.json",
                    "BLE/GATT control write, status read, cleanup, and RTT",
                    metrics=["bluetooth_bytes_exchanged", "bluetooth_rtt_ms_p95"],
                )
            ],
            recommended_for=["short-range status/control after reconnect evidence"],
            not_for=["high-rate telemetry", "large binary payloads"],
        ),
        capability_row(
            capability_id="capability.media.h264_tcp_binary",
            bridge_route_id="bridge_route.quest_device_link.media.tcp_binary",
            stream_id="stream.remote_camera.h264.left",
            semantic_family="media",
            transport_kind="tcp_binary",
            payload_plane="binary_media",
            rate_class="high_rate",
            reliability="ordered_bytes_backpressure_bounded",
            direction="quest_to_peer_or_host",
            clock_policy="media_frame_timestamp",
            queue_policy="drop_or_close_slow_peer",
            max_rate_hz=90,
            status="candidate",
            conditions=[
                condition(
                    "condition.media.binary_socket_or_codec_path",
                    "dependency",
                    "unknown",
                    remediation="Use a binary/media plane with codec-specific validation; never route frames through JSON command streams.",
                    evidence_refs=["media.binary_transport"],
                ),
                condition(
                    "condition.media.backpressure_policy",
                    "protocol",
                    "unknown",
                    remediation="Declare queue, drop, close, and frame timestamp policy before promotion.",
                    evidence_refs=["media.queue_policy"],
                ),
            ],
            timing=timing_profile(
                rtt_strategy="media_frame_timestamp_and_receiver_arrival",
                clock_alignment="codec_timestamp_with_optional_lsl_reference",
                metrics=["frame_timestamp_delta_ms", "dropped_frames", "throughput_mbps"],
                rtt_supported=False,
                fallback_timing_source="parallel_lsl_reference_or_media_ack_channel",
            ),
            test_slots=[],
            recommended_for=["H.264 camera frames", "binary media planes"],
            not_for=["operator command acknowledgement", "JSON payload transport"],
        ),
    ]


def capability_row(
    *,
    capability_id: str,
    bridge_route_id: str,
    stream_id: str,
    semantic_family: str,
    transport_kind: str,
    payload_plane: str,
    rate_class: str,
    reliability: str,
    direction: str,
    clock_policy: str,
    queue_policy: str,
    max_rate_hz: int | float,
    status: str,
    conditions: list[dict[str, Any]],
    timing: dict[str, Any],
    test_slots: list[dict[str, Any]],
    recommended_for: list[str],
    not_for: list[str],
) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "bridge_route_id": bridge_route_id,
        "stream_id": stream_id,
        "semantic_family": semantic_family,
        "transport_kind": transport_kind,
        "payload_plane": payload_plane,
        "rate_class": rate_class,
        "reliability": reliability,
        "direction": direction,
        "clock_policy": clock_policy,
        "queue_policy": queue_policy,
        "max_rate_hz": max_rate_hz,
        "status": status,
        "required_conditions": conditions,
        "timing": timing,
        "test_slots": test_slots,
        "high_rate_json_payload": False,
        "recommended_for": recommended_for,
        "not_for": not_for,
    }


def condition(
    condition_id: str,
    category: str,
    status: str,
    *,
    required: bool = True,
    remediation: str,
    evidence_refs: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "condition_id": condition_id,
        "category": category,
        "required": required,
        "status": status,
        "evidence_refs": evidence_refs or [],
        "remediation": remediation,
        "notes": notes,
    }


def timing_profile(
    *,
    rtt_strategy: str,
    clock_alignment: str,
    metrics: list[str],
    rtt_supported: bool,
    fallback_timing_source: str,
) -> dict[str, Any]:
    return {
        "rtt_supported": rtt_supported,
        "rtt_strategy": rtt_strategy,
        "clock_alignment": clock_alignment,
        "metrics": metrics,
        "fallback_timing_source": fallback_timing_source,
    }


def test_slot(
    probe_id: str,
    fixture_profile: str,
    live_command: str,
    purpose: str,
    *,
    metrics: list[str],
) -> dict[str, Any]:
    return {
        "probe_id": probe_id,
        "fixture_profile": fixture_profile,
        "purpose": purpose,
        "live_command": live_command,
        "fixture_command": (
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
            f"--mode fixture --probe-id {probe_id} --fixture-profile {fixture_profile} "
            f"--out target\\connectivity-probe\\{fixture_profile}.json --fail-on-error"
        ),
        "metrics": metrics,
    }


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
    if str(capability.get("capability_id") or "").strip() == "":
        errors.append("stream capability capability_id must not be empty")
    if str(capability.get("stream_id") or "").strip() == "":
        errors.append(
            f"stream capability {capability.get('capability_id')} stream_id must not be empty"
        )
    if str(capability.get("transport_kind") or "").strip() == "":
        errors.append(
            f"stream capability {capability.get('capability_id')} transport_kind must not be empty"
        )
    if "status" in capability and capability.get("status") not in VALID_STREAM_CAPABILITY_STATUS:
        errors.append(f"stream capability {capability.get('capability_id')} has invalid status")
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
    conditions = list_value(capability.get("required_conditions"))
    if not conditions:
        errors.append(
            f"stream capability {capability.get('capability_id')} requires required_conditions"
        )
    for condition_row in conditions:
        condition = object_value(condition_row)
        if not str(condition.get("condition_id") or "").strip():
            errors.append(
                f"stream capability {capability.get('capability_id')} has a condition without condition_id"
            )
        if str(condition.get("status") or "") not in VALID_CONDITION_STATUS:
            errors.append(
                f"stream capability {capability.get('capability_id')} has invalid condition status"
            )
    timing = object_value(capability.get("timing"))
    if not timing:
        errors.append(f"stream capability {capability.get('capability_id')} requires timing")
    elif not str(timing.get("rtt_strategy") or "").strip():
        errors.append(
            f"stream capability {capability.get('capability_id')} requires timing.rtt_strategy"
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


def qcl080_runtime_evidence(
    runtime_check: dict[str, Any] | None,
    udp_check: dict[str, Any] | None,
) -> dict[str, Any]:
    observed = object_value((runtime_check or {}).get("observed"))
    fields = object_value(observed.get("fields"))
    if not fields:
        udp_observed = object_value((udp_check or {}).get("observed"))
        marker = object_value(udp_observed.get("runtime_marker"))
        fields = object_value(marker.get("fields"))
        observed = marker
    return {
        "schema": fields.get("schema"),
        "status": fields.get("status"),
        "phase": fields.get("phase"),
        "enabled": fields.get("enabled"),
        "host": fields.get("host"),
        "port": int_or_none(fields.get("port")),
        "marker": fields.get("marker"),
        "run_id": fields.get("runId"),
        "packets_requested": int_or_none(fields.get("packetsRequested")),
        "packets_sent": int_or_none(fields.get("packetsSent")),
        "interval_ms": float_or_none(fields.get("intervalMs")),
        "elapsed_ms": float_or_none(fields.get("elapsedMs")),
        "sender_source": fields.get("senderSource"),
        "socket_owner": fields.get("socketOwner"),
        "high_rate_json_payload": str(fields.get("highRateJsonPayload") or "").lower()
        == "true",
        "settings_control_payload": str(fields.get("settingsControlPayload") or "").lower()
        == "true",
        "issue": fields.get("issue"),
        "marker_line": observed.get("line"),
        "check_status": str((runtime_check or {}).get("status") or ""),
    }


def stream_capability_requirements(
    report: dict[str, Any],
    *,
    transport: dict[str, Any],
    runtime_evidence: dict[str, Any],
    firewall_listener: dict[str, Any],
) -> list[dict[str, Any]]:
    packets_sent = int_or_none(runtime_evidence.get("packets_sent"))
    packets_requested = int_or_none(runtime_evidence.get("packets_requested"))
    runtime_ok = (
        transport.get("endpoint_source") == "app_owned_runtime_udp_sender"
        and runtime_evidence.get("status") == "sent"
        and runtime_evidence.get("sender_source") == "makepad-runtime"
        and runtime_evidence.get("socket_owner") == "app-owned"
        and packets_sent is not None
        and packets_requested is not None
        and packets_sent >= packets_requested
    )
    listener_allowed = firewall_listener.get("allowed_on_active_profile") is True
    product_rule_status = (
        "satisfied"
        if firewall_listener.get("product_rule_verified") is True
        else "missing"
        if diagnostic_python_program(firewall_listener.get("program"))
        else "present_unverified"
    )
    if not firewall_listener:
        product_rule_status = "unknown"
    return [
        {
            "requirement_id": "requirement.quest_device_link.qcl080.app_owned_runtime_sender",
            "status": "satisfied" if runtime_ok else "missing",
            "evidence": runtime_evidence.get("marker_line") or "",
            "required": True,
        },
        {
            "requirement_id": "requirement.quest_device_link.host_udp_listener_firewall",
            "status": "satisfied" if listener_allowed else "blocked",
            "observed_program": firewall_listener.get("program"),
            "observed_protocol": firewall_listener.get("protocol"),
            "observed_port": firewall_listener.get("port"),
            "observed_profiles": string_list(firewall_listener.get("active_profiles")),
            "required": True,
        },
        {
            "requirement_id": "requirement.quest_device_link.product_host_firewall_rule",
            "status": product_rule_status,
            "observed_program": firewall_listener.get("program"),
            "required_program_class": "signed_hostess_wpf_or_hostess_service",
            "required": True,
            "notes": (
                "Development or diagnostic listeners can prove the data path, but product "
                "readiness requires an inbound rule for the signed Hostess/WPF executable "
                "or service."
            ),
        },
        {
            "requirement_id": "requirement.quest_device_link.qcl080_live_promotion",
            "status": "satisfied"
            if object_value(report.get("promotion")).get("allowed") is True
            else "missing",
            "source_status": report.get("status"),
            "required": True,
        },
    ]


def stream_capability_status(
    report: dict[str, Any],
    *,
    transport: dict[str, Any],
    measurements: dict[str, Any],
    runtime_evidence: dict[str, Any],
    requirements: list[dict[str, Any]],
) -> str:
    if report.get("status") in {"fail", "blocked"}:
        return "blocked"
    if report.get("schema") != "rusty.quest.connectivity_topology_probe.v1":
        return "rejected"
    if report.get("probe_id") != "QCL-080" or transport.get("family") != "udp":
        return "rejected"
    if transport.get("endpoint_source") != "app_owned_runtime_udp_sender":
        return "rejected"
    if runtime_evidence.get("status") != "sent" or runtime_evidence.get("socket_owner") != "app-owned":
        return "rejected"
    packets_received = int_or_none(measurements.get("udp_packets_received"))
    if packets_received is None or packets_received < 1:
        return "blocked"
    if object_value(report.get("promotion")).get("allowed") is not True:
        return "candidate"
    warning_statuses = {"missing", "blocked", "unknown"}
    has_requirement_warning = any(
        str(requirement.get("status") or "") in warning_statuses
        for requirement in requirements
        if isinstance(requirement, dict)
    )
    has_report_warning = report.get("status") == "warn" or any(
        object_value(issue).get("severity") == "warning" for issue in list_value(report.get("issues"))
    )
    if has_requirement_warning or has_report_warning:
        return "usable_with_warnings"
    return "usable"


def stream_capability_warnings(
    report: dict[str, Any],
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for issue in list_value(report.get("issues")):
        if not isinstance(issue, dict):
            continue
        warnings.append(
            {
                "issue_code": str(issue.get("issue_code") or ""),
                "severity": str(issue.get("severity") or "warning"),
                "message": str(issue.get("message") or issue.get("issue_code") or ""),
            }
        )
    product_rule = next(
        (
            requirement
            for requirement in requirements
            if isinstance(requirement, dict)
            and requirement.get("requirement_id")
            == "requirement.quest_device_link.product_host_firewall_rule"
        ),
        {},
    )
    if object_value(product_rule).get("status") in {"missing", "unknown"}:
        warnings.append(
            {
                "issue_code": "hostess.issue.device_link.stream_capability.product_firewall_rule_missing",
                "severity": "warning",
                "message": (
                    "QCL-080 used a diagnostic listener; product readiness still needs a "
                    "scoped inbound firewall rule for the signed Hostess/WPF app."
                ),
            }
        )
    return warnings


def qcl080_required_conditions(
    requirements: list[dict[str, Any]],
    *,
    report: dict[str, Any],
    transport: dict[str, Any],
    runtime_evidence: dict[str, Any],
    firewall_listener: dict[str, Any],
) -> list[dict[str, Any]]:
    statuses = {
        requirement_suffix(row): requirement_condition_status(str(row.get("status") or "unknown"))
        for row in requirements
        if isinstance(row, dict)
    }
    return [
        condition(
            "condition.qcl080.app_owned_runtime_sender",
            "runtime",
            statuses.get("app_owned_runtime_sender", "unknown"),
            remediation="Use the Makepad/runtime-owned UDP sender rather than an adb-shell generator.",
            evidence_refs=["runtime.qcl080_udp_sender"],
            notes=str(runtime_evidence.get("marker_line") or ""),
        ),
        condition(
            "condition.qcl080.host_udp_listener_firewall",
            "firewall",
            statuses.get("host_udp_listener_firewall", "unknown"),
            remediation="Bind the fixed Hostess listener port and allow that executable/port on the active Windows profile.",
            evidence_refs=["host.windows_firewall_listener"],
            notes=(
                f"{firewall_listener.get('program') or 'unknown'}:"
                f"{firewall_listener.get('port') or 'unknown'}"
            ),
        ),
        condition(
            "condition.qcl080.product_host_firewall_rule",
            "firewall",
            statuses.get("product_host_firewall_rule", "unknown"),
            remediation="Replace diagnostic Python listener evidence with the signed Hostess/WPF executable firewall rule.",
            evidence_refs=["requirement.quest_device_link.product_host_firewall_rule"],
        ),
        condition(
            "condition.qcl080.live_promotion",
            "protocol",
            statuses.get("qcl080_live_promotion", "unknown"),
            remediation="Run QCL-080 live on the target topology and keep the promotion decision with the artifact.",
            evidence_refs=["promotion.allowed"],
            notes=str(object_value(report.get("promotion")).get("reason") or ""),
        ),
        condition(
            "condition.qcl080.endpoint_source",
            "runtime",
            "satisfied"
            if transport.get("endpoint_source") == "app_owned_runtime_udp_sender"
            else "blocked",
            remediation="Promote only app-owned runtime UDP senders into reusable stream capability descriptors.",
            evidence_refs=["transport.endpoint_source"],
        ),
    ]


def qcl081_runtime_evidence(report: dict[str, Any]) -> dict[str, Any]:
    probe = object_value(report.get("lsl_payload_probe"))
    transport = object_value(report.get("transport"))
    measurements = object_value(report.get("measurements"))
    discovery_check = report_check(report, "protocol.lsl_discovery")
    continuity_check = report_check(report, "protocol.lsl_sample_continuity")
    discovery_observed = object_value((discovery_check or {}).get("observed"))
    continuity_observed = object_value((continuity_check or {}).get("observed"))
    preflight = object_value(probe.get("quest_runtime_preflight"))
    termux_python = object_value(preflight.get("termux_python"))
    pylsl_import = object_value(preflight.get("pylsl_import"))
    bridge_route_evidence = object_value(probe.get("bridge_route_evidence"))
    issue_codes = string_list(probe.get("issue_codes"))
    if not issue_codes:
        issue_codes = string_list((discovery_check or {}).get("issue_codes")) + string_list(
            (continuity_check or {}).get("issue_codes")
        )
    status = str(
        probe.get("status")
        or (
            "pass"
            if object_value(discovery_check).get("status") == "pass"
            and object_value(continuity_check).get("status") == "pass"
            else report.get("status") or "unknown"
        )
    )
    return {
        "status": status,
        "source": probe.get("source") or discovery_observed.get("source") or transport.get("endpoint_source"),
        "stream_name": probe.get("stream_name") or discovery_observed.get("stream_name"),
        "stream_type": probe.get("stream_type") or discovery_observed.get("stream_type"),
        "samples_requested": int_or_none(
            probe.get("samples_requested")
            or continuity_observed.get("samples_requested")
            or measurements.get("lsl_samples_requested")
        ),
        "samples_received": int_or_none(
            probe.get("samples_received")
            or continuity_observed.get("samples_received")
            or measurements.get("lsl_samples_received")
        ),
        "loss_percent": float_or_none(
            probe.get("loss_percent")
            or continuity_observed.get("loss_percent")
            or measurements.get("lsl_sample_loss_percent")
        ),
        "discovery_ms": float_or_none(
            probe.get("discovery_ms")
            or discovery_observed.get("discovery_ms")
            or measurements.get("lsl_discovery_ms")
        ),
        "monotonic_sequences": (
            probe.get("monotonic_sequences")
            if "monotonic_sequences" in probe
            else continuity_observed.get("monotonic_sequences")
        ),
        "received_sequences": list_value(probe.get("received_sequences")),
        "evidence_tier": probe.get("evidence_tier"),
        "authority_owner": probe.get("authority_owner"),
        "route_id": probe.get("route_id"),
        "bridge_route_evidence_status": bridge_route_evidence.get("status"),
        "issue_codes": issue_codes,
        "notes": probe.get("notes") or evidence_text(discovery_check),
        "quest_termux_python_returncode": int_or_none(termux_python.get("returncode")),
        "quest_termux_python_available": termux_python.get("returncode") == 0,
        "quest_pylsl_import_returncode": int_or_none(pylsl_import.get("returncode")),
        "quest_pylsl_import_available": pylsl_import.get("returncode") == 0,
        "high_rate_json_payload": False,
    }


def qcl081_stream_capability_requirements(
    report: dict[str, Any],
    *,
    transport: dict[str, Any],
    runtime_evidence: dict[str, Any],
    measurements: dict[str, Any],
) -> list[dict[str, Any]]:
    discovery_check = report_check(report, "protocol.lsl_discovery")
    continuity_check = report_check(report, "protocol.lsl_sample_continuity")
    discovery_ms = float_or_none(measurements.get("lsl_discovery_ms"))
    samples_requested = int_or_none(measurements.get("lsl_samples_requested"))
    samples_received = int_or_none(measurements.get("lsl_samples_received"))
    loss_percent = float_or_none(measurements.get("lsl_sample_loss_percent"))
    continuity_ok = (
        samples_requested is not None
        and samples_requested > 0
        and samples_received is not None
        and samples_received >= samples_requested
        and (loss_percent is None or loss_percent <= 0.0)
        and runtime_evidence.get("monotonic_sequences") is not False
    )
    owner_source = str(transport.get("endpoint_source") or "")
    broker_authority_ok = (
        owner_source != "manifold-lsl-broker"
        or (
            runtime_evidence.get("evidence_tier") == "broker_owned"
            and runtime_evidence.get("authority_owner") == "rusty.manifold.transport"
            and runtime_evidence.get("bridge_route_evidence_status") == "pass"
        )
    )
    owner_ok = (
        qcl081_promotable_lsl_owner(owner_source)
        and broker_authority_ok
        and runtime_evidence.get("status") == "pass"
        and samples_received is not None
        and samples_received > 0
    )
    discovery_status = str(object_value(discovery_check).get("status") or "")
    continuity_status = str(object_value(continuity_check).get("status") or "")
    blocked_by_runtime = (
        runtime_evidence.get("status") == "blocked"
        or discovery_status == "blocked"
        or continuity_status == "blocked"
    )
    return [
        {
            "requirement_id": "requirement.quest_device_link.qcl081.lsl_discovery",
            "status": "satisfied"
            if discovery_status == "pass" and discovery_ms is not None
            else "blocked"
            if discovery_status == "blocked"
            else "missing",
            "evidence": evidence_text(discovery_check),
            "observed_discovery_ms": discovery_ms,
            "required": True,
        },
        {
            "requirement_id": "requirement.quest_device_link.qcl081.sample_continuity",
            "status": "satisfied"
            if continuity_status == "pass" and continuity_ok
            else "blocked"
            if continuity_status == "blocked"
            else "missing",
            "observed_samples_requested": samples_requested,
            "observed_samples_received": samples_received,
            "observed_loss_percent": loss_percent,
            "required": True,
        },
        {
            "requirement_id": "requirement.quest_device_link.qcl081.quest_or_broker_lsl_producer",
            "status": "satisfied"
            if owner_ok
            else "blocked"
            if blocked_by_runtime and qcl081_promotable_lsl_owner(owner_source)
            else "missing",
            "observed_endpoint_source": owner_source,
            "observed_evidence_tier": runtime_evidence.get("evidence_tier"),
            "observed_authority_owner": runtime_evidence.get("authority_owner"),
            "issue_codes": string_list(runtime_evidence.get("issue_codes")),
            "notes": str(runtime_evidence.get("notes") or ""),
            "required": True,
        },
        {
            "requirement_id": "requirement.quest_device_link.qcl081_live_promotion",
            "status": "satisfied"
            if object_value(report.get("promotion")).get("allowed") is True
            else "blocked"
            if report.get("status") == "blocked"
            else "missing",
            "source_status": report.get("status"),
            "required": True,
        },
    ]


def qcl081_stream_capability_status(
    report: dict[str, Any],
    *,
    transport: dict[str, Any],
    runtime_evidence: dict[str, Any],
    measurements: dict[str, Any],
    requirements: list[dict[str, Any]],
) -> str:
    if report.get("schema") != "rusty.quest.connectivity_topology_probe.v1":
        return "rejected"
    if report.get("probe_id") != "QCL-081" or transport.get("family") != "lsl":
        return "rejected"
    if report.get("status") in {"fail", "blocked"}:
        return "blocked"
    if transport.get("endpoint_source") == "host-loopback":
        return "candidate"
    if not qcl081_promotable_lsl_owner(transport.get("endpoint_source")):
        return "candidate"
    if runtime_evidence.get("status") != "pass":
        return "blocked"
    samples_received = int_or_none(measurements.get("lsl_samples_received"))
    if samples_received is None or samples_received < 1:
        return "blocked"
    if object_value(report.get("promotion")).get("allowed") is not True:
        return "candidate"
    has_requirement_warning = any(
        str(requirement.get("status") or "") in {"missing", "blocked", "unknown"}
        for requirement in requirements
        if isinstance(requirement, dict)
    )
    has_report_warning = report.get("status") == "warn" or any(
        object_value(issue).get("severity") == "warning" for issue in list_value(report.get("issues"))
    )
    if has_requirement_warning or has_report_warning:
        return "usable_with_warnings"
    return "usable"


def qcl081_stream_capability_warnings(
    report: dict[str, Any],
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for issue in list_value(report.get("issues")):
        if not isinstance(issue, dict):
            continue
        warnings.append(
            {
                "issue_code": str(issue.get("issue_code") or ""),
                "severity": str(issue.get("severity") or "warning"),
                "message": str(issue.get("message") or issue.get("issue_code") or ""),
            }
        )
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        if str(requirement.get("status") or "") not in {"missing", "blocked", "unknown"}:
            continue
        warnings.append(
            {
                "issue_code": "hostess.issue.device_link.stream_capability.qcl081_requirement_missing",
                "severity": "warning",
                "message": f"{requirement.get('requirement_id')} is {requirement.get('status')}",
            }
        )
    return warnings


def qcl081_required_conditions(
    requirements: list[dict[str, Any]],
    *,
    report: dict[str, Any],
    transport: dict[str, Any],
    runtime_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    statuses = {
        requirement_suffix(row): requirement_condition_status(str(row.get("status") or "unknown"))
        for row in requirements
        if isinstance(row, dict)
    }
    endpoint_source = transport.get("endpoint_source")
    return [
        condition(
            "condition.qcl081.lsl_discovery",
            "protocol",
            statuses.get("lsl_discovery", "unknown"),
            remediation="Run QCL-081 and require LSL stream discovery on the target topology.",
            evidence_refs=["protocol.lsl_discovery", "lsl_discovery_ms"],
        ),
        condition(
            "condition.qcl081.sample_continuity",
            "protocol",
            statuses.get("sample_continuity", "unknown"),
            remediation="Run QCL-081 with the requested sample count and zero unexpected loss.",
            evidence_refs=["protocol.lsl_sample_continuity", "lsl_samples_received"],
        ),
        condition(
            "condition.qcl081.quest_or_broker_lsl_producer",
            "runtime",
            statuses.get("quest_or_broker_lsl_producer", "unknown"),
            remediation=(
                "Package a Quest-owned/study-adapter LSL outlet or use a broker-owned "
                "LSL producer before promoting this capability."
            ),
            evidence_refs=["lsl_payload_probe", "transport.endpoint_source"],
            notes=str(runtime_evidence.get("notes") or ""),
        ),
        condition(
            "condition.qcl081.live_promotion",
            "protocol",
            statuses.get("qcl081_live_promotion", "unknown"),
            remediation="Run QCL-081 live on the target topology and keep the promotion decision with the artifact.",
            evidence_refs=["promotion.allowed"],
            notes=str(object_value(report.get("promotion")).get("reason") or ""),
        ),
        condition(
            "condition.qcl081.endpoint_source",
            "runtime",
            "satisfied"
            if qcl081_promotable_lsl_owner(endpoint_source)
            else "candidate"
            if endpoint_source in {"host-loopback", "external"}
            else "blocked",
            remediation="Promote only Quest-runtime, study-adapter, or broker-owned LSL producer evidence.",
            evidence_refs=["transport.endpoint_source"],
        ),
    ]


def qcl081_promotable_lsl_owner(source: Any) -> bool:
    return str(source or "") in {
        "quest-runtime",
        "study-adapter",
        "broker-owned",
        "native-rust-broker",
        "manifold-lsl-broker",
    }


def qcl083_runtime_evidence(report: dict[str, Any]) -> dict[str, Any]:
    probe = object_value(report.get("osc_payload_probe"))
    android = object_value(probe.get("android"))
    android_evidence = object_value(android.get("evidence"))
    osc_server = object_value(android_evidence.get("osc_server"))
    return {
        "status": probe.get("status"),
        "source": probe.get("source"),
        "endpoint_source": probe.get("endpoint_source"),
        "address": probe.get("address"),
        "device_endpoint": probe.get("device_endpoint"),
        "messages_requested": int_or_none(probe.get("messages_requested")),
        "messages_acknowledged": int_or_none(probe.get("messages_acknowledged")),
        "loss_percent": float_or_none(probe.get("loss_percent")),
        "round_trip_ms_p95": float_or_none(probe.get("round_trip_ms_p95")),
        "android_status": android_evidence.get("status"),
        "android_authority": android_evidence.get("authority"),
        "android_evidence_available": android.get("evidence_available") is True,
        "android_messages_received": int_or_none(android_evidence.get("messages_received")),
        "android_messages_acknowledged": int_or_none(android_evidence.get("messages_acknowledged")),
        "android_socket_opened": osc_server.get("socket_opened"),
        "android_socket_closed": osc_server.get("socket_closed"),
        "remote_evidence": android.get("remote_evidence"),
        "high_rate_json_payload": False,
    }


def qcl083_stream_capability_requirements(
    report: dict[str, Any],
    *,
    transport: dict[str, Any],
    runtime_evidence: dict[str, Any],
    measurements: dict[str, Any],
) -> list[dict[str, Any]]:
    shape_ok = report_check(report, "protocol.osc_message_shape")
    exchange_ok = report_check(report, "protocol.osc_payload_exchange")
    messages_requested = int_or_none(measurements.get("osc_messages_requested"))
    messages_received = int_or_none(measurements.get("osc_messages_received"))
    loss_percent = float_or_none(measurements.get("osc_loss_percent"))
    message_counts_ok = (
        messages_requested is not None
        and messages_requested > 0
        and messages_received is not None
        and messages_received >= messages_requested
        and (loss_percent is None or loss_percent <= 0.0)
    )
    runtime_ok = (
        transport.get("endpoint_source") == "quest-runtime"
        and runtime_evidence.get("endpoint_source") == "app_owned_android_osc_server"
        and runtime_evidence.get("status") == "pass"
        and runtime_evidence.get("android_status") == "pass"
        and runtime_evidence.get("android_authority") == "app_owned_runtime_osc_udp_server"
        and runtime_evidence.get("android_socket_opened") is True
        and runtime_evidence.get("android_socket_closed") is True
    )
    return [
        {
            "requirement_id": "requirement.quest_device_link.qcl083.message_shape",
            "status": "satisfied" if object_value(shape_ok).get("status") == "pass" else "missing",
            "evidence": evidence_text(shape_ok),
            "required": True,
        },
        {
            "requirement_id": "requirement.quest_device_link.qcl083.payload_exchange",
            "status": "satisfied"
            if object_value(exchange_ok).get("status") == "pass" and message_counts_ok
            else "missing",
            "observed_messages_requested": messages_requested,
            "observed_messages_received": messages_received,
            "observed_loss_percent": loss_percent,
            "required": True,
        },
        {
            "requirement_id": "requirement.quest_device_link.qcl083.quest_runtime_endpoint",
            "status": "satisfied" if runtime_ok else "missing",
            "evidence": str(runtime_evidence.get("remote_evidence") or ""),
            "required": True,
        },
        {
            "requirement_id": "requirement.quest_device_link.qcl083_live_promotion",
            "status": "satisfied"
            if object_value(report.get("promotion")).get("allowed") is True
            else "missing",
            "source_status": report.get("status"),
            "required": True,
        },
    ]


def qcl083_stream_capability_status(
    report: dict[str, Any],
    *,
    transport: dict[str, Any],
    runtime_evidence: dict[str, Any],
    measurements: dict[str, Any],
    requirements: list[dict[str, Any]],
) -> str:
    if report.get("status") in {"fail", "blocked"}:
        return "blocked"
    if report.get("schema") != "rusty.quest.connectivity_topology_probe.v1":
        return "rejected"
    if report.get("probe_id") != "QCL-083" or transport.get("family") != "osc":
        return "rejected"
    if transport.get("endpoint_source") == "host-loopback":
        return "candidate"
    if transport.get("endpoint_source") != "quest-runtime":
        return "rejected"
    if runtime_evidence.get("status") != "pass":
        return "blocked"
    messages_received = int_or_none(measurements.get("osc_messages_received"))
    if messages_received is None or messages_received < 1:
        return "blocked"
    if object_value(report.get("promotion")).get("allowed") is not True:
        return "candidate"
    has_requirement_warning = any(
        str(requirement.get("status") or "") in {"missing", "blocked", "unknown"}
        for requirement in requirements
        if isinstance(requirement, dict)
    )
    has_report_warning = report.get("status") == "warn" or any(
        object_value(issue).get("severity") == "warning" for issue in list_value(report.get("issues"))
    )
    if has_requirement_warning or has_report_warning:
        return "usable_with_warnings"
    return "usable"


def qcl083_stream_capability_warnings(
    report: dict[str, Any],
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for issue in list_value(report.get("issues")):
        if not isinstance(issue, dict):
            continue
        warnings.append(
            {
                "issue_code": str(issue.get("issue_code") or ""),
                "severity": str(issue.get("severity") or "warning"),
                "message": str(issue.get("message") or issue.get("issue_code") or ""),
            }
        )
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        if str(requirement.get("status") or "") not in {"missing", "blocked", "unknown"}:
            continue
        warnings.append(
            {
                "issue_code": "hostess.issue.device_link.stream_capability.qcl083_requirement_missing",
                "severity": "warning",
                "message": f"{requirement.get('requirement_id')} is {requirement.get('status')}",
            }
        )
    return warnings


def qcl083_required_conditions(
    requirements: list[dict[str, Any]],
    *,
    report: dict[str, Any],
    transport: dict[str, Any],
    runtime_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    statuses = {
        requirement_suffix(row): requirement_condition_status(str(row.get("status") or "unknown"))
        for row in requirements
        if isinstance(row, dict)
    }
    return [
        condition(
            "condition.qcl083.message_shape",
            "protocol",
            statuses.get("message_shape", "unknown"),
            remediation="Run QCL-083 and reject malformed OSC address, typetag, or payload combinations.",
            evidence_refs=["protocol.osc_message_shape"],
        ),
        condition(
            "condition.qcl083.payload_exchange",
            "protocol",
            statuses.get("payload_exchange", "unknown"),
            remediation="Run QCL-083 with the required message count and zero unacceptable loss.",
            evidence_refs=["protocol.osc_payload_exchange", "osc_messages_received"],
        ),
        condition(
            "condition.qcl083.quest_runtime_endpoint",
            "runtime",
            statuses.get("quest_runtime_endpoint", "unknown"),
            remediation="Use the Hostess Android QCL-083 action or future Rusty Quest runtime endpoint.",
            evidence_refs=["osc_payload_probe.android.evidence"],
            notes=str(runtime_evidence.get("remote_evidence") or ""),
        ),
        condition(
            "condition.qcl083.live_promotion",
            "protocol",
            statuses.get("qcl083_live_promotion", "unknown"),
            remediation="Run QCL-083 live on the target topology and keep the promotion decision with the artifact.",
            evidence_refs=["promotion.allowed"],
            notes=str(object_value(report.get("promotion")).get("reason") or ""),
        ),
        condition(
            "condition.qcl083.endpoint_source",
            "runtime",
            "satisfied" if transport.get("endpoint_source") == "quest-runtime" else "blocked",
            remediation="Promote only Quest-runtime OSC endpoint evidence into reusable OSC descriptors.",
            evidence_refs=["transport.endpoint_source"],
        ),
    ]


def install_suite_environment_checks() -> list[dict[str, Any]]:
    return [
        environment_check(
            "suite.host.os",
            "host",
            "Windows OS, architecture, and writable output directory",
            "python tools\\hostessctl\\hostessctl.py companion-readiness --out target\\companion-readiness\\readiness.json",
            ["check.host.os", "check.host.python", "check.host.output_directory"],
        ),
        environment_check(
            "suite.toolchain.android",
            "toolchain",
            "ADB, Android SDK/JDK, Cargo, and cargo-makepad when Quest/Makepad routes are in scope",
            "python tools\\hostessctl\\hostessctl.py companion-readiness --profile hostess-makepad-quest --out target\\companion-readiness\\quest-readiness.json",
            ["check.tool.adb", "check.tool.android_sdk", "check.tool.jdk", "check.tool.cargo", "check.tool.cargo_makepad"],
        ),
        environment_check(
            "suite.network.adapters",
            "network",
            "Host IPv4 candidates, Quest Wi-Fi IPv4, same-subnet state, and direct-ish hotspot topology",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-010 --out target\\connectivity-probe\\qcl010-live.json",
            ["host.ipv4_candidate", "device.wifi_ipv4", "topology.same_subnet"],
        ),
        environment_check(
            "suite.firewall.listener_rules",
            "firewall",
            "Windows active network/firewall profile and inbound listener rule coverage",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe windows-firewall-rule --program <HostessCompanion.Wpf.exe> --protocol UDP --port 18767 --out target\\connectivity-probe\\qcl080-firewall-plan.json",
            ["host.windows_network_firewall_profile", "host.windows_firewall_listener"],
        ),
        environment_check(
            "suite.device.identity",
            "device",
            "Quest ADB state, model, app package availability, runtime launchability, Wi-Fi, and Bluetooth adapters",
            "python tools\\hostessctl\\hostessctl.py companion-readiness --require-device --require-makepad-package --out target\\companion-readiness\\device-readiness.json",
            ["check.device.adb_state", "check.device.model", "device.wifi_ipv4", "device.bluetooth_adapter"],
        ),
        environment_check(
            "suite.protocol.dependencies",
            "protocol",
            "Protocol libraries, helpers, and runtime endpoints for WebSocket, LSL, OSC, ZeroMQ, BLE/GATT, and RFCOMM",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe test-suite --out target\\connectivity-probe\\device-link-test-suite.json",
            ["protocol.websocket_handshake", "protocol.lsl_discovery", "protocol.osc_payload_exchange", "protocol.zeromq_dependency", "protocol.ble_gatt_status", "protocol.rfcomm_control"],
        ),
        environment_check(
            "suite.timing.rtt",
            "timing",
            "RTT, one-way estimates, clock offset estimates, jitter, loss, reconnects, and parallel LSL timing references",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-083 --osc-source quest-runtime --out target\\connectivity-probe\\qcl083-live-quest-runtime.json",
            ["osc_rtt_ms_p95", "zeromq_rtt_ms_p95", "bluetooth_rtt_ms_p95", "lsl_discovery_ms"],
        ),
    ]


def install_suite_test_slots() -> list[dict[str, Any]]:
    return [
        suite_slot(
            "suite.qcl000.usb_adb_command_feedback",
            "QCL-000",
            "qcl-000-usb-adb-pass",
            "device_link",
            "USB ADB command-feedback baseline and app-private fallback path",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-000 --fixture-profile qcl-000-usb-adb-pass --out target\\connectivity-probe\\qcl000-fixture.json --fail-on-error",
            metrics=["sent", "transport_ok", "authority_accepted", "runtime_accepted", "applied"],
            rtt_policy="command_stage_receipts",
        ),
        suite_slot(
            "suite.qcl010.same_wifi_tcp",
            "QCL-010",
            "qcl-010-router-pass",
            "network",
            "Router/existing-Wi-Fi host and Quest reachability plus TCP listener firewall posture",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-010 --out target\\connectivity-probe\\qcl010-live.json",
            metrics=["tcp_connect_ms"],
            rtt_policy="tcp_connect_only_not_full_rtt",
        ),
        suite_slot(
            "suite.qcl011.pc_hotspot_tcp",
            "QCL-011",
            "qcl-011-pc-hotspot-pass",
            "network",
            "Windows Mobile Hotspot topology and LAN reachability",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-011 --topology-owner pc_hotspot --network-provider windows_mobile_hotspot --out target\\connectivity-probe\\qcl011-live.json",
            metrics=["tcp_connect_ms"],
            rtt_policy="tcp_connect_only_not_full_rtt",
        ),
        suite_slot(
            "suite.qcl080.udp_freshness",
            "QCL-080",
            "qcl-080-app-owned-udp-freshness-pass",
            "protocol",
            "Quest app-owned UDP freshness, loss, jitter, and listener firewall coverage",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-080 --udp-sender-source makepad-runtime --udp-port 18767 --out target\\connectivity-probe\\qcl080-live.json",
            metrics=["udp_packets_sent", "udp_packets_received", "udp_loss_percent", "jitter_ms_p95"],
            rtt_policy="host_arrival_only_use_lsl_parallel_for_clock_alignment",
        ),
        suite_slot(
            "suite.qcl081.lsl_clocked_samples",
            "QCL-081",
            "qcl-081-lsl-loopback-pass",
            "protocol",
            "LSL discovery, multicast behavior, sample continuity, and clock correction",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-081 --lsl-source host-loopback --out target\\connectivity-probe\\qcl081-live-host-loopback.json",
            metrics=["lsl_discovery_ms", "lsl_samples_received", "lsl_sample_loss_percent"],
            rtt_policy="lsl_time_correction_reference",
        ),
        suite_slot(
            "suite.qcl082.media_tcp_binary",
            "QCL-082",
            "qcl-082-media-binary-plane-pass",
            "protocol",
            "Binary media-plane framing, timestamp, queue, drop, and backpressure guardrails",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-082 --fixture-profile qcl-082-media-binary-plane-pass --out target\\connectivity-probe\\qcl082-media-binary-plane-pass.json --fail-on-error",
            metrics=[
                "media_frames_received",
                "media_bytes_received",
                "media_dropped_frames",
                "media_receiver_queue_depth_max",
            ],
            rtt_policy="media_frame_timestamp_and_receiver_arrival",
        ),
        suite_slot(
            "suite.qcl083.osc_round_trip",
            "QCL-083",
            "qcl-083-osc-loopback-pass",
            "protocol",
            "OSC message shape, payload exchange, RTT, one-way estimate, and clock offset estimate",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-083 --osc-source quest-runtime --out target\\connectivity-probe\\qcl083-live-quest-runtime.json",
            metrics=["osc_messages_received", "osc_loss_percent", "osc_rtt_ms_p95", "osc_clock_offset_estimate_ms_median"],
            rtt_policy="native_round_trip_ack",
        ),
        suite_slot(
            "suite.qcl084.zeromq_native_rust",
            "QCL-084",
            "qcl-084-zeromq-loopback-pass",
            "protocol",
            "Generic ZeroMQ adapter dependency, socket exchange, RTT, and queue/decode counters",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-084 --zeromq-source manifold-zmq-loopback --zeromq-pattern pub-sub --zeromq-manifold-root S:\\Work\\repos\\active\\rusty-manifold --out target\\connectivity-probe\\qcl084-live-manifold-zmq-loopback.json",
            metrics=["zeromq_messages_received", "zeromq_rtt_ms_p95", "zeromq_clock_offset_estimate_ms_median"],
            rtt_policy="req_rep_native_rtt_or_pub_sub_lsl_parallel_reference",
        ),
        suite_slot(
            "suite.qcl079.websocket_generic",
            "QCL-079",
            "qcl-079-websocket-loopback-pass",
            "protocol",
            "Generic WebSocket handshake, bounded payload exchange, and command-authority separation",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-079 --websocket-source host-loopback --out target\\connectivity-probe\\qcl079-live-host-loopback.json",
            metrics=["websocket_messages_received", "websocket_loss_percent", "websocket_echo_ms"],
            rtt_policy="echo_round_trip_ack_candidate_until_broker_or_runtime_endpoint",
        ),
        suite_slot(
            "suite.qcl050.bluetooth_rfcomm",
            "QCL-050",
            "qcl-050-rfcomm-control-pass",
            "protocol",
            "Bluetooth Classic RFCOMM pairing, service discovery, payload exchange, cleanup, and RTT",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-050 --bluetooth-payload-source android-rfcomm --out target\\connectivity-probe\\qcl050-live-rfcomm.json",
            metrics=["bluetooth_bytes_exchanged", "bluetooth_rtt_ms_p95"],
            rtt_policy="native_round_trip_ack",
        ),
        suite_slot(
            "suite.qcl051.bluetooth_gatt",
            "QCL-051",
            "qcl-051-ble-gatt-status-pass",
            "protocol",
            "BLE/GATT control write, status characteristic read, reconnect, cleanup, and RTT",
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-051 --bluetooth-payload-source android-ble-gatt --out target\\connectivity-probe\\qcl051-live-ble-gatt.json",
            metrics=["bluetooth_bytes_exchanged", "bluetooth_rtt_ms_p95"],
            rtt_policy="native_write_ack_round_trip",
        ),
    ]


def environment_check(
    check_id: str,
    category: str,
    purpose: str,
    command: str,
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "category": category,
        "purpose": purpose,
        "command": command,
        "evidence_refs": evidence_refs,
    }


def suite_slot(
    slot_id: str,
    probe_id: str,
    fixture_profile: str,
    phase: str,
    purpose: str,
    live_command: str,
    *,
    metrics: list[str],
    rtt_policy: str,
) -> dict[str, Any]:
    return {
        "slot_id": slot_id,
        "probe_id": probe_id,
        "fixture_profile": fixture_profile,
        "phase": phase,
        "purpose": purpose,
        "fixture_command": (
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
            f"--mode fixture --probe-id {probe_id} --fixture-profile {fixture_profile} "
            f"--out target\\connectivity-probe\\{fixture_profile}.json --fail-on-error"
        ),
        "live_command": live_command,
        "metrics": metrics,
        "rtt_policy": rtt_policy,
        "artifacts": [
            "rusty.quest.connectivity_topology_probe.v1",
            "validation-report.json",
        ],
    }


def requirement_suffix(requirement: dict[str, Any]) -> str:
    return str(requirement.get("requirement_id") or "").split(".")[-1]


def requirement_condition_status(status: str) -> str:
    if status == "satisfied":
        return "satisfied"
    if status in {"missing", "blocked", "unknown"}:
        return status
    if status == "present_unverified":
        return "candidate"
    return "unknown"


def report_check(report: dict[str, Any], name: str) -> dict[str, Any] | None:
    for check in list_value(report.get("checks")):
        if isinstance(check, dict) and check.get("name") == name:
            return check
    return None


def diagnostic_python_program(program: Any) -> bool:
    leaf = str(program or "").replace("\\", "/").rstrip("/").split("/")[-1].lower()
    return leaf in {"python.exe", "python", "python3", "python3.exe"}


def int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sha256_file(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "QUEST_DEVICE_LINK_SCHEMA",
    "QUEST_DEVICE_LINK_VALIDATION_SCHEMA",
    "QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_SCHEMA",
    "QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_VALIDATION_SCHEMA",
    "QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA",
    "QUEST_DEVICE_LINK_STREAM_CAPABILITY_VALIDATION_SCHEMA",
    "build_device_link_report",
    "build_install_test_suite_descriptor",
    "build_stream_capability_descriptor_from_connectivity_probe",
    "run_install_test_suite_descriptor",
    "run_stream_capability_descriptor",
    "validate_device_link_report",
    "validate_install_test_suite_descriptor",
    "validate_stream_capability_descriptor",
]
