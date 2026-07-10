"""Product topology and listener-firewall gates for QCL-082 media receiver evidence."""

from __future__ import annotations

from typing import Any

from tools.hostessctl.connectivity_firewall import diagnostic_python_program_path
from tools.hostessctl.connectivity_media import MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE
from tools.hostessctl.connectivity_probe_common import object_value
from tools.hostessctl.connectivity_media_receiver_common import (
    LIVE_CAPTURE_KINDS,
    PRODUCT_TCP_MEDIA_DIRECT_WIFI_GATE,
    PRODUCT_TCP_MEDIA_LISTENER_FIREWALL_GATE,
    int_or_none,
    normalize_topology_token,
)
from tools.hostessctl.connectivity_media_receiver_lease import (
    quest_serial_from_resource,
    topology_device_serial,
)
from tools.hostessctl.connectivity_topology_lifecycle import WIFI_DIRECT_LIFECYCLE_SCHEMA


QCL082_DEPENDENT_MEDIA_RELAY_STATUSES = {"pass", "pass_with_peer_close"}


def media_product_topology_summary(
    topology_report: dict[str, Any] | None,
    *,
    topology_report_path: str,
    media_promotion_allowed: bool,
    media_transport_ok: bool,
    runtime_ok: bool,
    capture_kind: str,
    quest_lease: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = object_value(topology_report)
    topology = object_value(report.get("topology"))
    transport = object_value(report.get("transport"))
    promotion = object_value(report.get("promotion"))
    lease = object_value(quest_lease)
    owner = str(topology.get("owner") or "")
    network_provider = str(topology.get("network_provider") or "")
    endpoint_direction = str(topology.get("endpoint_direction") or "")
    transport_family = str(transport.get("family") or "")
    route = str(transport.get("route") or "")
    topology_status = str(report.get("status") or "")
    topology_probe_id = str(report.get("probe_id") or "")
    topology_promotion_allowed = promotion.get("allowed") is True
    dependent_relay = qcl082_dependent_media_relay_topology_summary(report)
    dependent_relay_allowed = dependent_relay["allowed"]
    product_topology_allowed = topology_promotion_allowed or dependent_relay_allowed
    product_topology_status_ok = topology_status == "pass" or dependent_relay_allowed
    device_serial = topology_device_serial(report)
    receiver_quest_serial = str(lease.get("quest_serial") or quest_serial_from_resource(str(lease.get("resource") or "")))
    direct_wifi = any(
        "wifi_direct" in normalize_topology_token(value)
        for value in [owner, network_provider, endpoint_direction, transport_family, route]
    )
    report_present = bool(report)
    requires_serial_binding = bool(
        report_present
        and direct_wifi
        and product_topology_allowed
        and capture_kind in LIVE_CAPTURE_KINDS
    )
    serial_binding_ok = bool(
        not requires_serial_binding
        or (device_serial and receiver_quest_serial and device_serial == receiver_quest_serial)
    )
    ready = (
        report_present
        and direct_wifi
        and product_topology_status_ok
        and product_topology_allowed
        and media_promotion_allowed
        and serial_binding_ok
    )
    if not report_present:
        check_status_value = "skipped"
        evidence = "product TCP media over direct-Wi-Fi topology report was not supplied"
        issue_codes: list[str] = []
    elif ready:
        check_status_value = "pass"
        evidence = (
            "RMANVID1 TCP receiver capture is paired with same-run QCL-082 Wi-Fi Direct media relay evidence"
            if dependent_relay_allowed and not topology_promotion_allowed
            else "RMANVID1 TCP receiver capture is paired with promoted direct-Wi-Fi topology evidence"
        )
        issue_codes = []
    elif (
        direct_wifi
        and product_topology_allowed
        and media_promotion_allowed
        and requires_serial_binding
        and not device_serial
    ):
        check_status_value = "blocked"
        evidence = "direct-Wi-Fi topology is promoted but does not expose device.serial for product media lease binding"
        issue_codes = [
            "hostess.issue.connectivity_probe.media_direct_wifi_topology_device_serial_missing"
        ]
    elif (
        direct_wifi
        and product_topology_allowed
        and media_promotion_allowed
        and requires_serial_binding
        and not receiver_quest_serial
    ):
        check_status_value = "blocked"
        evidence = "live receiver capture lease does not expose a Quest serial for product media topology binding"
        issue_codes = [
            "hostess.issue.connectivity_probe.media_receiver_quest_lease_serial_missing"
        ]
    elif (
        direct_wifi
        and product_topology_allowed
        and media_promotion_allowed
        and requires_serial_binding
    ):
        check_status_value = "blocked"
        evidence = "live receiver capture Quest lease serial does not match promoted direct-Wi-Fi topology device.serial"
        issue_codes = [
            "hostess.issue.connectivity_probe.media_direct_wifi_topology_lease_serial_mismatch"
        ]
    elif direct_wifi and not product_topology_allowed:
        check_status_value = "warn"
        evidence = "direct-Wi-Fi topology is present but neither promoted nor backed by same-run QCL-082 relay evidence"
        issue_codes = [
            "hostess.issue.connectivity_probe.media_direct_wifi_topology_not_promoted",
            *dependent_relay["issue_codes"],
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
        "topology_product_acceptance_source": (
            "promoted_topology"
            if topology_promotion_allowed
            else ("dependent_media_relay_lifecycle" if dependent_relay_allowed else "")
        ),
        "topology_product_status_ok": product_topology_status_ok,
        "direct_wifi_topology": direct_wifi,
        "requires_serial_binding": requires_serial_binding,
        "topology_device_serial": device_serial,
        "media_receiver_quest_serial": receiver_quest_serial,
        "topology_lease_serial_matches": serial_binding_ok,
        "media_transport_ok": media_transport_ok,
        "media_runtime_ok": runtime_ok,
        "media_promotion_allowed": media_promotion_allowed,
        "receiver_capture_kind": capture_kind,
        "dependent_media_relay_topology_allowed": dependent_relay_allowed,
        "dependent_media_relay": dependent_relay,
    }


def qcl082_dependent_media_relay_topology_summary(report: dict[str, Any]) -> dict[str, Any]:
    diagnostics = object_value(report.get("diagnostics"))
    relay = object_value(diagnostics.get("qcl082_relay"))
    lifecycle = object_value(report.get("lifecycle"))
    schema = str(report.get("$schema") or report.get("schema") or "")
    probe_id = str(report.get("probe_id") or "")
    run_id = str(report.get("run_id") or "")
    capture_kind = str(report.get("capture_kind") or "")
    relay_status = str(relay.get("status") or "")
    bytes_copied = int_or_none(relay.get("bytes_copied")) or 0
    source_owner = str(relay.get("source_owner") or "")
    source_owner_token = normalize_topology_token(source_owner)
    lifecycle_phase_statuses = {
        "feature": str(object_value(lifecycle.get("feature")).get("status") or ""),
        "windows_wifi_direct_api": str(
            object_value(lifecycle.get("windows_wifi_direct_api")).get("status") or ""
        ),
        "permission_state": str(object_value(lifecycle.get("permission_state")).get("status") or ""),
        "peer_discovery": str(object_value(lifecycle.get("peer_discovery")).get("status") or ""),
        "group_formation": str(object_value(lifecycle.get("group_formation")).get("status") or ""),
        "cleanup": str(object_value(lifecycle.get("cleanup")).get("status") or ""),
    }
    lifecycle_ready = all(status == "pass" for status in lifecycle_phase_statuses.values())
    socket_network_bound = bool(
        relay.get("receiver_socket_created_from_wifi_direct_network") is True
        and relay.get("receiver_socket_bound_to_wifi_direct_network") is True
    )
    source_owner_ok = bool(
        source_owner == MEDIA_STREAM_RUNTIME_ENDPOINT_SOURCE
        or "media_stream_runtime" in source_owner_token
    )
    relay_candidate = bool(schema == WIFI_DIRECT_LIFECYCLE_SCHEMA or relay)
    checks = {
        "schema_ok": schema == WIFI_DIRECT_LIFECYCLE_SCHEMA,
        "probe_ok": probe_id == "QCL-041",
        "live_evidence": report.get("live_evidence") is True
        and capture_kind == "live_wifi_direct_lifecycle",
        "run_id_present": bool(run_id),
        "relay_enabled": relay.get("enabled") is True,
        "relay_status_ok": relay_status in QCL082_DEPENDENT_MEDIA_RELAY_STATUSES,
        "relay_bytes_copied": bytes_copied > 0,
        "receiver_connected": relay.get("receiver_connected") is True,
        "receiver_socket_network_bound": socket_network_bound,
        "source_owner_ok": source_owner_ok,
        "lifecycle_ready_without_diagnostic_socket": lifecycle_ready,
    }
    issue_codes: list[str] = []
    issue_requirements = [
        ("schema_ok", "media_dependent_relay_lifecycle_schema_invalid"),
        ("probe_ok", "media_dependent_relay_lifecycle_probe_mismatch"),
        ("live_evidence", "media_dependent_relay_lifecycle_not_live"),
        ("run_id_present", "media_dependent_relay_run_id_missing"),
        ("relay_enabled", "media_dependent_relay_not_enabled"),
        ("relay_status_ok", "media_dependent_relay_not_passed"),
        ("relay_bytes_copied", "media_dependent_relay_bytes_missing"),
        ("receiver_connected", "media_dependent_relay_receiver_not_connected"),
        ("receiver_socket_network_bound", "media_dependent_relay_receiver_not_wifi_direct_bound"),
        ("source_owner_ok", "media_dependent_relay_source_not_media_runtime"),
        ("lifecycle_ready_without_diagnostic_socket", "media_dependent_relay_lifecycle_incomplete"),
    ]
    if report and relay_candidate:
        issue_codes.extend(
            f"hostess.issue.connectivity_probe.{suffix}"
            for check, suffix in issue_requirements
            if not checks[check]
        )
    return {
        "allowed": bool(report and relay_candidate and not issue_codes),
        "schema": schema,
        "probe_id": probe_id,
        "run_id": run_id,
        "capture_kind": capture_kind,
        "relay_status": relay_status,
        "bytes_copied": bytes_copied,
        "source_owner": source_owner,
        "receiver_connected": relay.get("receiver_connected") is True,
        "receiver_socket_created_from_wifi_direct_network": relay.get(
            "receiver_socket_created_from_wifi_direct_network"
        )
        is True,
        "receiver_socket_bound_to_wifi_direct_network": relay.get(
            "receiver_socket_bound_to_wifi_direct_network"
        )
        is True,
        "receiver_connected_local_address": str(relay.get("receiver_connected_local_address") or ""),
        "lifecycle_phase_statuses": lifecycle_phase_statuses,
        "relay_candidate": relay_candidate,
        "checks": checks,
        "issue_codes": issue_codes,
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

__all__ = [
    "media_product_topology_summary",
    "qcl082_dependent_media_relay_topology_summary",
    "media_product_listener_firewall_summary",
]
