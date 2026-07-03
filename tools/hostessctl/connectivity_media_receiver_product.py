"""Product topology and listener-firewall gates for QCL-082 media receiver evidence."""

from __future__ import annotations

from typing import Any

from tools.hostessctl.connectivity_firewall import diagnostic_python_program_path
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
        and topology_promotion_allowed
        and capture_kind in LIVE_CAPTURE_KINDS
    )
    serial_binding_ok = bool(
        not requires_serial_binding
        or (device_serial and receiver_quest_serial and device_serial == receiver_quest_serial)
    )
    ready = (
        report_present
        and direct_wifi
        and topology_status == "pass"
        and topology_promotion_allowed
        and media_promotion_allowed
        and serial_binding_ok
    )
    if not report_present:
        check_status_value = "skipped"
        evidence = "product TCP media over direct-Wi-Fi topology report was not supplied"
        issue_codes: list[str] = []
    elif ready:
        check_status_value = "pass"
        evidence = "RMANVID1 TCP receiver capture is paired with promoted direct-Wi-Fi topology evidence"
        issue_codes = []
    elif (
        direct_wifi
        and topology_promotion_allowed
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
        and topology_promotion_allowed
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
        and topology_promotion_allowed
        and media_promotion_allowed
        and requires_serial_binding
    ):
        check_status_value = "blocked"
        evidence = "live receiver capture Quest lease serial does not match promoted direct-Wi-Fi topology device.serial"
        issue_codes = [
            "hostess.issue.connectivity_probe.media_direct_wifi_topology_lease_serial_mismatch"
        ]
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
        "requires_serial_binding": requires_serial_binding,
        "topology_device_serial": device_serial,
        "media_receiver_quest_serial": receiver_quest_serial,
        "topology_lease_serial_matches": serial_binding_ok,
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

__all__ = [
    "media_product_topology_summary",
    "media_product_listener_firewall_summary",
]
