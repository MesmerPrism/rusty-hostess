"""Pure live-report shaping helpers for connectivity probe routes."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from tools.hostessctl.connectivity_firewall import (
    default_firewall_program,
    default_firewall_rule_name,
)
from tools.hostessctl.connectivity_probe_common import (
    check_status,
    empty_measurements,
    object_value,
)


def protocol_topology_for_report(
    *,
    device: dict[str, Any],
    source: str,
    host_ip: str,
    endpoint_direction: str,
) -> dict[str, Any]:
    owner = "external_wifi" if device.get("wifi_ipv4") else "host_local"
    return {
        "owner": owner,
        "network_provider": "router_or_existing_wifi" if owner == "external_wifi" else "loopback",
        "endpoint_direction": endpoint_direction,
        "requires_existing_wifi": bool(device.get("wifi_ipv4")),
        "requires_adb": bool(device.get("wifi_ipv4")),
        "requires_pairing": False,
        "requires_termux": False,
        "experimental": source != "host-loopback" or not bool(host_ip),
    }


def tcp_echo_listener_from_result(args: argparse.Namespace, tcp_result: dict[str, Any] | None) -> dict[str, Any]:
    if not tcp_result:
        return {}
    observed = object_value(tcp_result.get("observed"))
    try:
        port = int(observed.get("port") or 0)
    except (TypeError, ValueError):
        port = 0
    if port <= 0:
        return {}
    return {
        "program": sys.executable,
        "protocol": "TCP",
        "port": port,
        "bind_host": str(getattr(args, "tcp_echo_bind_host", "0.0.0.0") or "0.0.0.0"),
    }


def udp_listener_from_result(args: argparse.Namespace, udp_result: dict[str, Any] | None) -> dict[str, Any]:
    if not udp_result:
        return {}
    observed = object_value(udp_result.get("observed"))
    try:
        port = int(observed.get("port") or 0)
    except (TypeError, ValueError):
        port = 0
    if port <= 0:
        return {}
    return {
        "program": str(observed.get("listener_program") or default_firewall_program("UDP")),
        "protocol": "UDP",
        "port": port,
        "bind_host": str(getattr(args, "udp_bind_host", "0.0.0.0") or "0.0.0.0"),
        "rule_name": default_firewall_rule_name(port, "UDP"),
        "remote_address": "LocalSubnet",
    }


def live_qcl010_status(checks: list[dict[str, Any]], host_ip: str, device_ip: Any) -> str:
    if not host_ip or not device_ip:
        return "blocked"
    if check_status(checks, "device_to_host.tcp_echo") == "pass":
        return "warn"
    if check_status(checks, "device_to_host.icmp_ping") == "pass":
        return "warn"
    return "fail"


def live_qcl011_status(checks: list[dict[str, Any]], host_ip: str, device_ip: Any) -> str:
    if not host_ip or not device_ip:
        return "blocked"
    if check_status(checks, "host.windows_mobile_hotspot") != "pass":
        return "blocked"
    if check_status(checks, "device_to_host.tcp_echo") == "pass":
        return "warn"
    if check_status(checks, "device_to_host.icmp_ping") == "pass":
        return "warn"
    return "fail"


def live_qcl080_status(checks: list[dict[str, Any]], host_ip: str, device_ip: Any) -> str:
    if not host_ip or not device_ip:
        return "blocked"
    runtime_status = check_status(checks, "runtime.qcl080_udp_sender")
    if runtime_status and runtime_status not in {"pass", "skipped"}:
        return "fail"
    udp_status = check_status(checks, "protocol.udp_freshness")
    if udp_status == "pass":
        if check_status(checks, "host.windows_network_firewall_profile") == "warn":
            return "warn"
        if check_status(checks, "host.windows_firewall_listener") == "warn":
            return "warn"
        return "pass"
    if udp_status == "warn":
        return "warn"
    return "fail"


def live_qcl081_status(checks: list[dict[str, Any]], *, source: str, device_ip: Any) -> str:
    discovery_status = check_status(checks, "protocol.lsl_discovery")
    continuity_status = check_status(checks, "protocol.lsl_sample_continuity")
    if discovery_status == "blocked" or continuity_status == "blocked":
        return "blocked"
    if discovery_status == "fail" or continuity_status == "fail":
        return "fail"
    if continuity_status == "warn":
        return "warn"
    if continuity_status == "pass":
        if source == "manifold-lsl-broker":
            return "pass"
        if source == "host-loopback" or not device_ip:
            return "warn"
        return "pass"
    return "blocked"


def live_qcl083_status(checks: list[dict[str, Any]], *, source: str, device_ip: Any) -> str:
    shape_status = check_status(checks, "protocol.osc_message_shape")
    exchange_status = check_status(checks, "protocol.osc_payload_exchange")
    if shape_status == "blocked" or exchange_status == "blocked":
        return "blocked"
    if shape_status == "fail" or exchange_status == "fail":
        return "fail"
    if exchange_status == "warn":
        return "warn"
    if exchange_status == "pass":
        if source == "host-loopback" or not device_ip:
            return "warn"
        return "pass"
    return "blocked"


def live_qcl084_status(checks: list[dict[str, Any]], *, source: str, device_ip: Any) -> str:
    dependency_status = check_status(checks, "protocol.zeromq_dependency")
    exchange_status = check_status(checks, "protocol.zeromq_payload_exchange")
    if dependency_status == "blocked" or exchange_status == "blocked":
        return "blocked"
    if dependency_status == "fail" or exchange_status == "fail":
        return "fail"
    if exchange_status == "warn":
        return "warn"
    if exchange_status == "pass":
        if source == "native-rust-broker":
            return "pass"
        if source == "quest-runtime" and device_ip:
            return "pass"
        if source not in {"native-rust-broker", "quest-runtime"} or not device_ip:
            return "warn"
    return "blocked"


def measurements_from_checks(tcp_result: dict[str, Any] | None) -> dict[str, Any]:
    measurements = empty_measurements()
    if tcp_result:
        observed = object_value(tcp_result.get("observed"))
        if observed.get("elapsed_ms") is not None:
            measurements["tcp_connect_ms"] = observed.get("elapsed_ms")
    measurements["reconnect_attempts"] = 1
    return measurements


def measurements_from_udp_check(udp_result: dict[str, Any] | None) -> dict[str, Any]:
    measurements = empty_measurements()
    if udp_result:
        observed = object_value(udp_result.get("observed"))
        measurements["udp_packets_sent"] = observed.get("packets_requested")
        measurements["udp_packets_received"] = observed.get("packets_received")
        measurements["udp_loss_percent"] = observed.get("loss_percent")
        measurements["jitter_ms_p95"] = observed.get("interarrival_ms_p95")
    measurements["reconnect_attempts"] = 1
    return measurements


def measurements_from_lsl_probe(lsl_result: dict[str, Any] | None) -> dict[str, Any]:
    measurements = empty_measurements()
    if lsl_result:
        measurements["lsl_discovery_ms"] = lsl_result.get("discovery_ms")
        measurements["lsl_samples_requested"] = lsl_result.get("samples_requested")
        measurements["lsl_samples_received"] = lsl_result.get("samples_received")
        measurements["lsl_sample_loss_percent"] = lsl_result.get("loss_percent")
    measurements["reconnect_attempts"] = 1
    return measurements


def measurements_from_osc_probe(osc_result: dict[str, Any] | None) -> dict[str, Any]:
    measurements = empty_measurements()
    if osc_result:
        measurements["osc_messages_requested"] = osc_result.get("messages_requested")
        measurements["osc_messages_received"] = osc_result.get("messages_acknowledged")
        measurements["osc_loss_percent"] = osc_result.get("loss_percent")
        measurements["osc_rtt_ms_p95"] = osc_result.get("round_trip_ms_p95")
        measurements["osc_quest_processing_ms_p95"] = osc_result.get("quest_processing_ms_p95")
        measurements["osc_estimated_one_way_ms_p95"] = osc_result.get("estimated_one_way_ms_p95")
        measurements["osc_clock_offset_estimate_ms_median"] = osc_result.get("clock_offset_estimate_ms_median")
        measurements["osc_clock_offset_jitter_ms_p95"] = osc_result.get("clock_offset_jitter_ms_p95")
    measurements["reconnect_attempts"] = 1
    return measurements


def measurements_from_zeromq_probe(zeromq_result: dict[str, Any] | None) -> dict[str, Any]:
    measurements = empty_measurements()
    if zeromq_result:
        measurements["zeromq_messages_requested"] = zeromq_result.get("messages_requested")
        measurements["zeromq_messages_received"] = zeromq_result.get("messages_acknowledged")
        measurements["zeromq_rtt_ms_p95"] = zeromq_result.get("round_trip_ms_p95")
        measurements["zeromq_server_processing_ms_p95"] = zeromq_result.get("server_processing_ms_p95")
        measurements["zeromq_estimated_one_way_ms_p95"] = zeromq_result.get("estimated_one_way_ms_p95")
        measurements["zeromq_clock_offset_estimate_ms_median"] = zeromq_result.get("clock_offset_estimate_ms_median")
        measurements["zeromq_clock_offset_jitter_ms_p95"] = zeromq_result.get("clock_offset_jitter_ms_p95")
    measurements["reconnect_attempts"] = 1
    return measurements
