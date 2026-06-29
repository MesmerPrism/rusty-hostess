"""Validation helpers for Quest connectivity probe reports."""

from __future__ import annotations

from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    CONNECTIVITY_PROBE_SCHEMA,
    check_passed,
    check_skipped,
    list_value,
    object_value,
)
from tools.hostessctl.connectivity_topology import (
    TOPOLOGY_PROBE_IDS,
    TOPOLOGY_REQUIRED_PASS_CHECKS,
)


CONNECTIVITY_PROBE_VALIDATION_SCHEMA = "rusty.hostess.connectivity_topology_probe.validation.v1"
VALID_STATUSES = {"planned", "pass", "warn", "fail", "blocked", "skipped"}
VALID_PROBE_IDS = {
    "QCL-000",
    "QCL-010",
    "QCL-011",
    "QCL-020",
    "QCL-030",
    "QCL-040",
    "QCL-041",
    "QCL-050",
    "QCL-051",
    "QCL-080",
    "QCL-081",
    "QCL-082",
    "QCL-083",
    "QCL-084",
}


def validate_connectivity_probe_report(report: dict[str, Any]) -> dict[str, Any]:
    """Validate the shared QCL connectivity report shape."""

    errors: list[str] = []
    warnings: list[str] = []
    if report.get("schema") != CONNECTIVITY_PROBE_SCHEMA:
        errors.append("unsupported connectivity probe schema")
    if report.get("probe_id") not in VALID_PROBE_IDS:
        errors.append("probe_id must be one of the supported QCL IDs")
    if report.get("status") not in VALID_STATUSES:
        errors.append("status must be planned, pass, warn, fail, blocked, or skipped")
    if not str(report.get("run_id") or "").strip():
        errors.append("run_id must not be empty")
    if not isinstance(report.get("topology"), dict):
        errors.append("topology must be an object")
    if not isinstance(report.get("transport"), dict):
        errors.append("transport must be an object")

    checks = list_value(report.get("checks"))
    if not checks:
        errors.append("checks must not be empty")
    for check in checks:
        if check.get("status") not in VALID_STATUSES:
            errors.append(f"check {check.get('name', '<unnamed>')} has invalid status")
        if not str(check.get("name") or "").strip():
            errors.append("checks require names")

    if report.get("probe_id") in {"QCL-010", "QCL-011"} and report.get("status") == "pass":
        probe_id = str(report.get("probe_id"))
        if not check_passed(report, "device.wifi_ipv4"):
            errors.append(f"{probe_id} pass requires device.wifi_ipv4")
        if not check_passed(report, "host.ipv4_candidate"):
            errors.append(f"{probe_id} pass requires host.ipv4_candidate")
        if probe_id == "QCL-011" and not check_passed(report, "host.windows_mobile_hotspot"):
            errors.append("QCL-011 pass requires host.windows_mobile_hotspot")
        if not (
            check_passed(report, "device_to_host.tcp_echo")
            or check_passed(report, "device_to_host.icmp_ping")
            or check_passed(report, "host_to_device.icmp_ping")
        ):
            errors.append(f"{probe_id} pass requires at least one direct LAN reachability check")
        if check_skipped(report, "protocol.websocket_echo"):
            warnings.append(f"{probe_id} report does not yet include WebSocket echo coverage")
        if check_skipped(report, "protocol.udp_freshness"):
            warnings.append(f"{probe_id} report does not yet include UDP freshness coverage")
        if check_skipped(report, "protocol.lsl_discovery"):
            warnings.append(f"{probe_id} report does not yet include LSL discovery coverage")

    if report.get("probe_id") in TOPOLOGY_PROBE_IDS and report.get("status") == "pass":
        probe_id = str(report.get("probe_id"))
        for required_check in TOPOLOGY_REQUIRED_PASS_CHECKS.get(probe_id, []):
            if not check_passed(report, required_check):
                errors.append(f"{probe_id} pass requires {required_check}")

    if report.get("probe_id") == "QCL-080" and report.get("status") == "pass":
        if not check_passed(report, "device.wifi_ipv4"):
            errors.append("QCL-080 pass requires device.wifi_ipv4")
        if not check_passed(report, "host.ipv4_candidate"):
            errors.append("QCL-080 pass requires host.ipv4_candidate")
        if not check_passed(report, "topology.same_subnet"):
            errors.append("QCL-080 pass requires topology.same_subnet")
        if not check_passed(report, "protocol.udp_freshness"):
            errors.append("QCL-080 pass requires protocol.udp_freshness")
        measurements = object_value(report.get("measurements"))
        if measurements.get("udp_packets_sent") is None:
            errors.append("QCL-080 pass requires udp_packets_sent measurement")
        if measurements.get("udp_packets_received") is None:
            errors.append("QCL-080 pass requires udp_packets_received measurement")
        if measurements.get("udp_loss_percent") is None:
            errors.append("QCL-080 pass requires udp_loss_percent measurement")
        if measurements.get("jitter_ms_p95") is None:
            warnings.append("QCL-080 report does not include jitter_ms_p95")

    if report.get("probe_id") == "QCL-081" and report.get("status") == "pass":
        if not check_passed(report, "protocol.lsl_discovery"):
            errors.append("QCL-081 pass requires protocol.lsl_discovery")
        if not check_passed(report, "protocol.lsl_sample_continuity"):
            errors.append("QCL-081 pass requires protocol.lsl_sample_continuity")
        measurements = object_value(report.get("measurements"))
        if measurements.get("lsl_discovery_ms") is None:
            errors.append("QCL-081 pass requires lsl_discovery_ms measurement")
        if measurements.get("lsl_samples_received") is None:
            errors.append("QCL-081 pass requires lsl_samples_received measurement")

    if report.get("probe_id") == "QCL-082" and report.get("status") == "pass":
        for required_check in [
            "protocol.media_binary_transport",
            "protocol.media_packet_boundaries",
            "protocol.media_timestamp_policy",
            "protocol.media_backpressure_policy",
            "protocol.media_high_rate_json_guard",
        ]:
            if not check_passed(report, required_check):
                errors.append(f"QCL-082 pass requires {required_check}")
        measurements = object_value(report.get("measurements"))
        for required_measurement in [
            "media_frames_received",
            "media_bytes_received",
            "media_dropped_frames",
            "media_receiver_queue_depth_max",
        ]:
            if measurements.get(required_measurement) is None:
                errors.append(f"QCL-082 pass requires {required_measurement} measurement")

    if report.get("probe_id") == "QCL-083" and report.get("status") == "pass":
        if not check_passed(report, "protocol.osc_message_shape"):
            errors.append("QCL-083 pass requires protocol.osc_message_shape")
        if not check_passed(report, "protocol.osc_payload_exchange"):
            errors.append("QCL-083 pass requires protocol.osc_payload_exchange")
        measurements = object_value(report.get("measurements"))
        if measurements.get("osc_messages_requested") is None:
            errors.append("QCL-083 pass requires osc_messages_requested measurement")
        if measurements.get("osc_messages_received") is None:
            errors.append("QCL-083 pass requires osc_messages_received measurement")
        if measurements.get("osc_loss_percent") is None:
            errors.append("QCL-083 pass requires osc_loss_percent measurement")

    if report.get("probe_id") == "QCL-084" and report.get("status") == "pass":
        if not check_passed(report, "protocol.zeromq_dependency"):
            errors.append("QCL-084 pass requires protocol.zeromq_dependency")
        if not check_passed(report, "protocol.zeromq_payload_exchange"):
            errors.append("QCL-084 pass requires protocol.zeromq_payload_exchange")
        measurements = object_value(report.get("measurements"))
        if measurements.get("zeromq_messages_requested") is None:
            errors.append("QCL-084 pass requires zeromq_messages_requested measurement")
        if measurements.get("zeromq_messages_received") is None:
            errors.append("QCL-084 pass requires zeromq_messages_received measurement")

    if report.get("probe_id") in {"QCL-050", "QCL-051"} and report.get("status") == "pass":
        probe_id = str(report.get("probe_id"))
        protocol_check = "protocol.rfcomm_control" if probe_id == "QCL-050" else "protocol.ble_gatt_status"
        for required_check in [
            "host.bluetooth_adapter",
            "host.bluetooth_service",
            "device.bluetooth_adapter",
            "bluetooth.pairing_bond_state",
            "bluetooth.permission_state",
            protocol_check,
            "protocol.bluetooth_payload_exchange",
        ]:
            if not check_passed(report, required_check):
                errors.append(f"{probe_id} pass requires {required_check}")
        measurements = object_value(report.get("measurements"))
        if measurements.get("bluetooth_bytes_exchanged") is None:
            errors.append(f"{probe_id} pass requires bluetooth_bytes_exchanged measurement")
        if measurements.get("bluetooth_rtt_ms_p95") is None:
            errors.append(f"{probe_id} pass requires bluetooth_rtt_ms_p95 measurement")

    return {
        "$schema": CONNECTIVITY_PROBE_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "report_status": report.get("status"),
        "probe_id": report.get("probe_id"),
        "check_count": len(checks),
        "errors": errors,
        "warnings": warnings,
    }
