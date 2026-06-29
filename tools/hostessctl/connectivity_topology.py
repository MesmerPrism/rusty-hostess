"""Fixture report helpers for experimental connectivity topology QCL rows."""

from __future__ import annotations

from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    check_row,
    empty_measurements,
    issue_row,
)


TOPOLOGY_PROBE_IDS = {"QCL-020", "QCL-030", "QCL-040", "QCL-041"}

DEFAULT_TOPOLOGY_FIXTURE_PROFILES = {
    "QCL-020": "qcl-020-wifi-adb-session-pass",
    "QCL-030": "qcl-030-local-only-hotspot-started",
    "QCL-040": "qcl-040-wifi-direct-phone-peer-pass",
    "QCL-041": "qcl-041-wifi-direct-windows-peer-pass",
}

TOPOLOGY_FIXTURE_PROFILES = {
    *DEFAULT_TOPOLOGY_FIXTURE_PROFILES.values(),
    "qcl-020-wifi-adb-reconnect-lost",
    "qcl-030-local-only-hotspot-failed",
    "qcl-040-wifi-direct-permission-denied",
    "qcl-041-wifi-direct-windows-driver-blocked",
}

TOPOLOGY_REQUIRED_PASS_CHECKS = {
    "QCL-020": [
        "adb.usb_authorized",
        "adb.tcpip_enabled",
        "adb_wifi.connect",
        "companion_session.wifi_serial",
    ],
    "QCL-030": [
        "android.local_only_hotspot.feature",
        "android.local_only_hotspot.started",
        "pc.local_only_hotspot_join",
        "topology.socket_exchange",
        "android.local_only_hotspot.cleanup",
    ],
    "QCL-040": [
        "wifi_direct.feature",
        "wifi_direct.permission_state",
        "wifi_direct.peer_discovery",
        "wifi_direct.group_formation",
        "topology.socket_exchange",
    ],
    "QCL-041": [
        "wifi_direct.feature",
        "windows.wifi_direct_api",
        "wifi_direct.peer_discovery",
        "wifi_direct.group_formation",
        "topology.socket_exchange",
    ],
}


def default_topology_fixture_profile(probe_id: str) -> str:
    """Return the default fixture profile for a topology-only QCL probe."""

    return DEFAULT_TOPOLOGY_FIXTURE_PROFILES.get(probe_id, "")


def is_topology_fixture_profile(profile: str) -> bool:
    return profile in TOPOLOGY_FIXTURE_PROFILES


def topology_fixture_body(*, probe_id: str, profile: str) -> dict[str, Any]:
    """Build a fake/damaged topology probe report body."""

    if profile == "qcl-020-wifi-adb-session-pass":
        return qcl020_wifi_adb_body(status="pass")
    if profile == "qcl-020-wifi-adb-reconnect-lost":
        return qcl020_wifi_adb_body(status="blocked", reconnect_lost=True)
    if profile == "qcl-030-local-only-hotspot-started":
        return qcl030_local_only_hotspot_body(status="pass")
    if profile == "qcl-030-local-only-hotspot-failed":
        return qcl030_local_only_hotspot_body(status="blocked", start_failed=True)
    if profile == "qcl-040-wifi-direct-phone-peer-pass":
        return qcl040_wifi_direct_body(probe_id="QCL-040", status="pass")
    if profile == "qcl-040-wifi-direct-permission-denied":
        return qcl040_wifi_direct_body(
            probe_id="QCL-040",
            status="blocked",
            permission_denied=True,
        )
    if profile == "qcl-041-wifi-direct-windows-peer-pass":
        return qcl040_wifi_direct_body(probe_id="QCL-041", status="pass")
    if profile == "qcl-041-wifi-direct-windows-driver-blocked":
        return qcl040_wifi_direct_body(
            probe_id="QCL-041",
            status="blocked",
            windows_driver_blocked=True,
        )
    raise ValueError(f"unsupported topology fixture profile for {probe_id}: {profile}")


def qcl020_wifi_adb_body(*, status: str, reconnect_lost: bool = False) -> dict[str, Any]:
    checks = [
        check_row("adb.usb_authorized", "pass", "USB ADB authorization exists before Wi-Fi handoff"),
        check_row("adb.tcpip_enabled", "pass", "adb tcpip mode accepted on port 5555"),
        check_row(
            "adb_wifi.connect",
            "blocked" if reconnect_lost else "pass",
            "Wi-Fi serial lost after sleep" if reconnect_lost else "192.0.2.42:5555 connected",
            issue_codes=(
                ["hostess.issue.connectivity_probe.wifi_adb_reconnect_lost"]
                if reconnect_lost
                else []
            ),
        ),
        check_row(
            "companion_session.wifi_serial",
            "blocked" if reconnect_lost else "pass",
            "companion-session did not complete after reconnect"
            if reconnect_lost
            else "session report completed using Wi-Fi ADB serial",
            issue_codes=(
                ["hostess.issue.connectivity_probe.wifi_adb_session_incomplete"]
                if reconnect_lost
                else []
            ),
        ),
        check_row(
            "adb_wifi.reconnect",
            "blocked" if reconnect_lost else "pass",
            "route lost after sleep/reconnect" if reconnect_lost else "1/1 reconnect rehearsal passed",
            issue_codes=(
                ["hostess.issue.connectivity_probe.wifi_adb_reconnect_lost"]
                if reconnect_lost
                else []
            ),
        ),
    ]
    measurements = empty_measurements()
    measurements.update(
        {
            "adb_wifi_connect_ms": None if reconnect_lost else 420,
            "reconnect_attempts": 1,
            "reconnects_completed": 0 if reconnect_lost else 1,
        }
    )
    return {
        "status": status,
        "classification": "developer_only",
        "topology": {
            "owner": "wifi_adb",
            "network_provider": "router_or_existing_wifi",
            "endpoint_direction": "host_to_device_adb_wifi",
            "requires_existing_wifi": True,
            "requires_adb": True,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": False,
        },
        "transport": {
            "family": "adb_wifi",
            "route": "adb tcpip/connect plus companion-session",
            "protocol_role": "developer_operator_transport",
            "payload_class": "low_rate_control",
            "product_data_plane": False,
        },
        "device": {
            "serial_redacted": True,
            "model": "Quest 3S",
            "adb_wifi_serial": "192.0.2.42:5555" if not reconnect_lost else "",
        },
        "host": {"os": "windows", "toolchain_profile": "hostessctl.connectivity_probe.qcl020"},
        "checks": checks,
        "measurements": measurements,
        "issues": topology_issues(checks),
        "promotion": {
            "allowed": False,
            "target": "developer Wi-Fi ADB workflow note",
            "reason": "Wi-Fi ADB is a developer/operator convenience transport, not a product data plane",
        },
    }


def qcl030_local_only_hotspot_body(*, status: str, start_failed: bool = False) -> dict[str, Any]:
    checks = [
        check_row("android.local_only_hotspot.feature", "pass", "WifiManager.startLocalOnlyHotspot API present"),
        check_row(
            "android.local_only_hotspot.started",
            "blocked" if start_failed else "pass",
            "onFailed(reason=ERROR_GENERIC)" if start_failed else "onStarted callback returned SSID/passphrase",
            observed={"failure_reason": "ERROR_GENERIC"} if start_failed else {"ssid_redacted": True},
            issue_codes=(
                ["hostess.issue.connectivity_probe.local_only_hotspot_start_failed"]
                if start_failed
                else []
            ),
        ),
        check_row(
            "pc.local_only_hotspot_join",
            "skipped" if start_failed else "pass",
            "no SSID to join" if start_failed else "Windows client joined Quest-provided local-only hotspot",
        ),
        check_row(
            "topology.socket_exchange",
            "skipped" if start_failed else "pass",
            "no joined PC peer" if start_failed else "TCP echo and bounded UDP datagrams exchanged",
        ),
        check_row(
            "android.local_only_hotspot.cleanup",
            "pass",
            "reservation closed and restart gate clean",
        ),
    ]
    measurements = empty_measurements()
    measurements.update(
        {
            "tcp_connect_ms": None if start_failed else 68,
            "udp_packets_sent": None if start_failed else 6,
            "udp_packets_received": None if start_failed else 6,
            "udp_loss_percent": None if start_failed else 0.0,
            "reconnect_attempts": 1,
        }
    )
    return {
        "status": status,
        "classification": "experimental",
        "topology": {
            "owner": "local_only_hotspot",
            "network_provider": "android_local_only_hotspot",
            "endpoint_direction": "quest_provides_local_link",
            "requires_existing_wifi": False,
            "requires_adb": True,
            "requires_pairing": True,
            "requires_termux": False,
            "experimental": True,
        },
        "transport": {
            "family": "local_only_hotspot",
            "route": "WifiManager.startLocalOnlyHotspot",
            "protocol_role": "experimental_topology",
            "payload_class": "tcp_udp_probe",
            "product_data_plane": False,
        },
        "device": {"model": "Quest 3S", "hotspot_owner": "quest_app_probe"},
        "host": {"os": "windows", "toolchain_profile": "hostessctl.connectivity_probe.qcl030"},
        "checks": checks,
        "measurements": measurements,
        "issues": topology_issues(checks),
        "promotion": {
            "allowed": False,
            "target": "experimental topology descriptor",
            "reason": "LocalOnlyHotspot remains experimental until repeated live Horizon OS lifecycle evidence exists",
        },
    }


def qcl040_wifi_direct_body(
    *,
    probe_id: str,
    status: str,
    permission_denied: bool = False,
    windows_driver_blocked: bool = False,
) -> dict[str, Any]:
    windows_peer = probe_id == "QCL-041"
    blocked = permission_denied or windows_driver_blocked
    peer = "windows" if windows_peer else "android_phone"
    checks = [
        check_row("wifi_direct.feature", "pass", "FEATURE_WIFI_DIRECT present on Quest probe"),
        check_row(
            "windows.wifi_direct_api" if windows_peer else "android_phone.wifi_direct_peer",
            "blocked" if windows_driver_blocked else "pass",
            "Windows Wi-Fi Direct API/driver unavailable"
            if windows_driver_blocked
            else f"{peer} peer available",
            issue_codes=(
                ["hostess.issue.connectivity_probe.wifi_direct_windows_driver_unavailable"]
                if windows_driver_blocked
                else []
            ),
        ),
        check_row(
            "wifi_direct.permission_state",
            "blocked" if permission_denied else "pass",
            "NEARBY_WIFI_DEVICES permission denied" if permission_denied else "required permissions granted",
            issue_codes=(
                ["hostess.issue.connectivity_probe.wifi_direct_permission_denied"]
                if permission_denied
                else []
            ),
        ),
        check_row(
            "wifi_direct.peer_discovery",
            "blocked" if blocked else "pass",
            "peer discovery not available" if blocked else "peer discovered",
        ),
        check_row(
            "wifi_direct.group_formation",
            "skipped" if blocked else "pass",
            "group formation skipped after precondition block" if blocked else "group owner and client roles recorded",
        ),
        check_row(
            "topology.socket_exchange",
            "skipped" if blocked else "pass",
            "socket exchange skipped after group failure" if blocked else "bounded TCP message exchanged",
        ),
    ]
    measurements = empty_measurements()
    measurements.update(
        {
            "tcp_connect_ms": None if blocked else 91,
            "wifi_direct_peer_count": 0 if blocked else 1,
            "reconnect_attempts": 1,
        }
    )
    return {
        "status": status,
        "classification": "experimental",
        "topology": {
            "owner": "wifi_direct",
            "network_provider": "wifi_direct",
            "endpoint_direction": "peer_to_peer_group",
            "requires_existing_wifi": False,
            "requires_adb": True,
            "requires_pairing": True,
            "requires_termux": False,
            "experimental": True,
            "peer_class": peer,
        },
        "transport": {
            "family": "wifi_direct",
            "route": "WifiP2pManager discovery/group/socket exchange",
            "protocol_role": "experimental_topology",
            "payload_class": "bounded_tcp_probe",
            "product_data_plane": False,
        },
        "device": {"model": "Quest 3S", "wifi_direct_role": "group_owner_or_client"},
        "host": {
            "os": "windows" if windows_peer else "android_phone_peer",
            "toolchain_profile": f"hostessctl.connectivity_probe.{probe_id.lower()}",
        },
        "checks": checks,
        "measurements": measurements,
        "issues": topology_issues(checks),
        "promotion": {
            "allowed": False,
            "target": "experimental topology descriptor",
            "reason": "Wi-Fi Direct remains experimental until repeated live peer and lifecycle evidence exists",
        },
    }


def topology_issues(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen: set[str] = set()
    for check in checks:
        for issue_code in check.get("issue_codes", []) or []:
            if not issue_code or issue_code in seen:
                continue
            seen.add(issue_code)
            issues.append(
                issue_row(
                    issue_code,
                    "warning" if str(check.get("status")) == "warn" else "error",
                    str(check.get("summary") or issue_code),
                )
            )
    return issues
