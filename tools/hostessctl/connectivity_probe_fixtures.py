"""Fixture constructors for Quest connectivity probe reports."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_firewall import (
    network_profile_summary,
    windows_firewall_listener_summary,
)
from tools.hostessctl.connectivity_bluetooth import (
    bluetooth_transport_for_probe,
    topology_for_bluetooth_probe,
)
from tools.hostessctl.connectivity_media import (
    qcl082_fixture_body,
    qcl082_media_stream_session_body,
    qcl082_media_stream_runtime_status_body,
)
from tools.hostessctl.connectivity_media_receiver import (
    RECEIVER_CAPTURE_RESULT_SCHEMA,
    parse_rmanvid1_capture,
    qcl082_media_stream_receiver_capture_body,
    receiver_result_follow_on_paths,
)
from tools.hostessctl.connectivity_websocket import qcl079_fixture_body
from tools.hostessctl.connectivity_probe_common import (
    DEFAULT_TCP_MARKER,
    base_report,
    check_row,
    empty_measurements,
    issue_row,
    object_value,
    read_json_file,
)
from tools.hostessctl.connectivity_topology import (
    DEFAULT_TOPOLOGY_FIXTURE_PROFILES,
    is_topology_fixture_profile,
    topology_fixture_body,
    topology_for_probe,
    windows_mobile_hotspot_status,
    windows_mobile_hotspot_summary,
)
from tools.hostessctl.connectivity_udp import (
    DEFAULT_QCL080_UDP_PORT,
    DEFAULT_UDP_MARKER,
    qcl080_app_owned_marker_observed,
    udp_endpoint_source,
)

def fixture_report(args: argparse.Namespace, *, observed_at: datetime) -> dict[str, Any]:
    profile = str(getattr(args, "fixture_profile", "") or "")
    probe_id = str(getattr(args, "probe_id", "") or "QCL-010")
    media_stream_session_plan = str(getattr(args, "media_stream_session_plan", "") or "").strip()
    media_stream_runtime_status = str(getattr(args, "media_stream_runtime_status", "") or "").strip()
    media_stream_rmanvid1_capture = str(getattr(args, "media_stream_rmanvid1_capture", "") or "").strip()
    media_stream_receiver_sidecar = str(getattr(args, "media_stream_receiver_sidecar", "") or "").strip()
    media_stream_receiver_result = str(getattr(args, "media_stream_receiver_result", "") or "").strip()
    media_stream_topology_report = str(getattr(args, "media_stream_topology_report", "") or "").strip()
    media_stream_firewall_report = str(getattr(args, "media_stream_firewall_report", "") or "").strip()
    if probe_id == "QCL-082" and media_stream_receiver_result:
        receiver_result_path = Path(media_stream_receiver_result)
        receiver_result = read_json_file(receiver_result_path)
        if str(receiver_result.get("schema") or "") != RECEIVER_CAPTURE_RESULT_SCHEMA:
            report = base_report(args, observed_at=observed_at, probe_id="QCL-082")
            report.update(
                qcl082_media_receiver_result_error_body(
                    receiver_result,
                    receiver_result_path=str(receiver_result_path),
                )
            )
            return report
        receiver_paths = receiver_result_follow_on_paths(receiver_result)
        if not media_stream_rmanvid1_capture:
            media_stream_rmanvid1_capture = receiver_paths["capture_path"]
        if not media_stream_receiver_sidecar:
            media_stream_receiver_sidecar = receiver_paths["sidecar_path"]
        if not media_stream_runtime_status:
            media_stream_runtime_status = receiver_paths["runtime_status_path"]
        if not media_stream_topology_report:
            media_stream_topology_report = receiver_paths["topology_report_path"]
        if not media_stream_firewall_report:
            media_stream_firewall_report = receiver_paths["firewall_report_path"]
        if not media_stream_rmanvid1_capture:
            report = base_report(args, observed_at=observed_at, probe_id="QCL-082")
            report.update(
                qcl082_media_receiver_result_error_body(
                    receiver_result,
                    receiver_result_path=str(receiver_result_path),
                )
            )
            return report
    if probe_id == "QCL-082" and media_stream_rmanvid1_capture:
        capture_path = Path(media_stream_rmanvid1_capture)
        sidecar_path = Path(media_stream_receiver_sidecar) if media_stream_receiver_sidecar else None
        runtime_path = Path(media_stream_runtime_status) if media_stream_runtime_status else None
        capture_stats = parse_rmanvid1_capture(capture_path)
        sidecar = read_json_file(sidecar_path) if sidecar_path else {}
        if not media_stream_topology_report:
            media_stream_topology_report = str(
                object_value(sidecar.get("source")).get("topology_report_path") or ""
            ).strip()
        if not media_stream_firewall_report:
            media_stream_firewall_report = str(
                object_value(sidecar.get("source")).get("firewall_report_path") or ""
            ).strip()
        topology_path = Path(media_stream_topology_report) if media_stream_topology_report else None
        firewall_path = Path(media_stream_firewall_report) if media_stream_firewall_report else None
        runtime_artifact = read_json_file(runtime_path) if runtime_path else None
        topology_artifact = read_json_file(topology_path) if topology_path else None
        firewall_artifact = read_json_file(firewall_path) if firewall_path else None
        report = base_report(args, observed_at=observed_at, probe_id="QCL-082")
        report.update(
            qcl082_media_stream_receiver_capture_body(
                capture_stats,
                sidecar=sidecar,
                runtime_status=runtime_artifact,
                topology_report=topology_artifact,
                firewall_report=firewall_artifact,
                capture_path=str(capture_path),
                sidecar_path=str(sidecar_path) if sidecar_path else "",
                runtime_status_path=str(runtime_path) if runtime_path else "",
                topology_report_path=str(topology_path) if topology_path else "",
                firewall_report_path=str(firewall_path) if firewall_path else "",
            )
        )
        return report
    if probe_id == "QCL-082" and media_stream_runtime_status:
        artifact_path = Path(media_stream_runtime_status)
        artifact = read_json_file(artifact_path)
        report = base_report(args, observed_at=observed_at, probe_id="QCL-082")
        report.update(
            qcl082_media_stream_runtime_status_body(
                artifact,
                artifact_path=str(artifact_path),
            )
        )
        return report
    if probe_id == "QCL-082" and media_stream_session_plan:
        plan_path = Path(media_stream_session_plan)
        plan = read_json_file(plan_path)
        report = base_report(args, observed_at=observed_at, probe_id="QCL-082")
        report.update(
            qcl082_media_stream_session_body(
                plan,
                plan_path=str(plan_path),
            )
        )
        return report
    if not profile:
        if probe_id == "QCL-000":
            profile = "qcl-000-usb-adb-pass"
        elif probe_id == "QCL-011":
            profile = "qcl-011-pc-hotspot-pass"
        elif probe_id in DEFAULT_TOPOLOGY_FIXTURE_PROFILES:
            profile = DEFAULT_TOPOLOGY_FIXTURE_PROFILES[probe_id]
        elif probe_id == "QCL-050":
            profile = "qcl-050-rfcomm-control-pass"
        elif probe_id == "QCL-051":
            profile = "qcl-051-ble-gatt-status-pass"
        elif probe_id == "QCL-080":
            profile = "qcl-080-udp-freshness-pass"
        elif probe_id == "QCL-081":
            profile = "qcl-081-lsl-loopback-pass"
        elif probe_id == "QCL-082":
            profile = "qcl-082-media-binary-plane-pass"
        elif probe_id == "QCL-083":
            profile = "qcl-083-osc-loopback-pass"
        elif probe_id == "QCL-084":
            profile = "qcl-084-zeromq-loopback-pass"
        elif probe_id == "QCL-079":
            profile = "qcl-079-websocket-loopback-pass"
        else:
            profile = "qcl-010-router-pass"
    if profile == "qcl-000-usb-adb-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-000")
        report.update(qcl000_fixture_body())
        return report
    if profile == "qcl-010-router-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-010")
        report.update(qcl010_fixture_body(status="pass"))
        return report
    if profile == "qcl-010-router-firewall-blocked":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-010")
        report.update(qcl010_fixture_body(status="fail", firewall_blocked=True))
        return report
    if profile == "qcl-011-pc-hotspot-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-011")
        report.update(qcl011_fixture_body(status="pass"))
        return report
    if profile == "qcl-011-pc-hotspot-off":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-011")
        report.update(qcl011_fixture_body(status="blocked", hotspot_off=True))
        return report
    if is_topology_fixture_profile(profile):
        report_probe_id = probe_id
        if profile.startswith("qcl-020-"):
            report_probe_id = "QCL-020"
        elif profile.startswith("qcl-030-"):
            report_probe_id = "QCL-030"
        elif profile.startswith("qcl-040-"):
            report_probe_id = "QCL-040"
        elif profile.startswith("qcl-041-"):
            report_probe_id = "QCL-041"
        report = base_report(args, observed_at=observed_at, probe_id=report_probe_id)
        report.update(topology_fixture_body(probe_id=report_probe_id, profile=profile))
        return report
    if profile == "qcl-050-rfcomm-control-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-050")
        report.update(qcl05x_fixture_body(probe_id="QCL-050", status="pass"))
        return report
    if profile == "qcl-050-rfcomm-pairing-refused":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-050")
        report.update(qcl05x_fixture_body(probe_id="QCL-050", status="blocked", failure="pairing_refused"))
        return report
    if profile == "qcl-051-ble-gatt-status-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-051")
        report.update(qcl05x_fixture_body(probe_id="QCL-051", status="pass"))
        return report
    if profile == "qcl-051-ble-permission-denied":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-051")
        report.update(qcl05x_fixture_body(probe_id="QCL-051", status="blocked", failure="permission_denied"))
        return report
    if profile == "qcl-080-udp-freshness-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-080")
        report.update(qcl080_fixture_body(status="pass"))
        return report
    if profile == "qcl-080-app-owned-udp-freshness-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-080")
        report.update(qcl080_fixture_body(status="pass", app_owned=True))
        return report
    if profile == "qcl-080-udp-firewall-blocked":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-080")
        report.update(qcl080_fixture_body(status="fail", firewall_blocked=True))
        return report
    if profile == "qcl-081-lsl-loopback-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-081")
        report.update(qcl081_fixture_body(status="pass"))
        return report
    if profile == "qcl-081-lsl-discovery-blocked":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-081")
        report.update(qcl081_fixture_body(status="fail", discovery_blocked=True))
        return report
    if profile == "qcl-082-media-binary-plane-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-082")
        report.update(qcl082_fixture_body(status="pass"))
        return report
    if profile == "qcl-082-media-high-rate-json-misuse":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-082")
        report.update(qcl082_fixture_body(status="fail", high_rate_json_misuse=True))
        return report
    if profile == "qcl-083-osc-loopback-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-083")
        report.update(qcl083_fixture_body(status="pass"))
        return report
    if profile == "qcl-083-osc-malformed-packet":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-083")
        report.update(qcl083_fixture_body(status="fail", malformed=True))
        return report
    if profile == "qcl-084-zeromq-loopback-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-084")
        report.update(qcl084_fixture_body(status="pass"))
        return report
    if profile == "qcl-084-zeromq-dependency-missing":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-084")
        report.update(qcl084_fixture_body(status="blocked", dependency_missing=True))
        return report
    if profile == "qcl-079-websocket-loopback-pass":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-079")
        report.update(qcl079_fixture_body(status="pass"))
        return report
    if profile == "qcl-079-websocket-handshake-blocked":
        report = base_report(args, observed_at=observed_at, probe_id="QCL-079")
        report.update(qcl079_fixture_body(status="blocked", handshake_blocked=True))
        return report
    raise SystemExit(f"unsupported connectivity fixture profile: {profile}")


def qcl082_media_receiver_result_error_body(
    receiver_result: dict[str, Any],
    *,
    receiver_result_path: str,
) -> dict[str, Any]:
    result = object_value(receiver_result)
    schema = str(result.get("schema") or "")
    capture_path = str(result.get("capture_path") or "")
    issue_codes: list[str] = []
    if not result:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_result_missing")
    elif schema != RECEIVER_CAPTURE_RESULT_SCHEMA:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_result_schema_mismatch")
    if not capture_path:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_result_missing_capture")
    return {
        "status": "fail",
        "classification": "protocol_fit_receiver_result",
        "topology": {
            "owner": "hostess_receiver_canary",
            "network_provider": "declared_by_receiver_result",
            "endpoint_direction": "quest_to_host_binary_media",
            "requires_existing_wifi": True,
            "requires_adb": False,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": True,
        },
        "transport": {
            "family": "tcp_binary",
            "route": "hostess_rmanvid1_receiver_result",
            "local_endpoint": "declared_by_receiver_result",
            "remote_endpoint": "declared_by_receiver_result",
            "protocol_role": "binary_media_plane_receiver_counters",
        },
        "device": {
            "serial_redacted": True,
            "model": "receiver_result",
            "foreground_package": "not_checked",
            "adb_state": "not_applicable",
        },
        "host": {
            "os": "windows",
            "toolchain_profile": "hostessctl.connectivity_probe.qcl082.receiver_result",
        },
        "checks": [
            check_row(
                "protocol.media_receiver_result",
                "fail",
                "QCL-082 receiver-result artifact is not a valid receiver capture result",
                observed={
                    "receiver_result_path": receiver_result_path,
                    "schema": schema,
                    "expected_schema": RECEIVER_CAPTURE_RESULT_SCHEMA,
                    "capture_path": capture_path,
                    "sidecar_path": result.get("sidecar_path"),
                },
                issue_codes=issue_codes,
            )
        ],
        "measurements": empty_measurements(),
        "issues": [
            issue_row(
                issue_code,
                "error",
                "QCL-082 receiver-result artifact cannot be folded into product media evidence",
            )
            for issue_code in issue_codes
        ],
        "promotion": {
            "allowed": False,
            "target": "quest.device_link binary media stream capability descriptor",
            "reason": "receiver-result artifact is not accepted as the QCL-082 fold-in contract",
        },
        "media_stream_receiver_result": {
            "schema": schema,
            "expected_schema": RECEIVER_CAPTURE_RESULT_SCHEMA,
            "artifact_path": receiver_result_path,
            "capture_path": result.get("capture_path"),
            "sidecar_path": result.get("sidecar_path"),
        },
    }


def qcl000_fixture_body() -> dict[str, Any]:
    return {
        "status": "pass",
        "classification": "baseline",
        "topology": {
            "owner": "usb_adb_forward",
            "network_provider": "usb",
            "endpoint_direction": "host_to_device_forward",
            "requires_existing_wifi": False,
            "requires_adb": True,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": False,
        },
        "transport": {
            "family": "websocket",
            "route": "/manifold/v1/events",
            "local_endpoint": "127.0.0.1:18765",
            "remote_endpoint": "127.0.0.1:8765",
            "protocol_role": "command_feedback",
            "payload_class": "low_rate_control",
        },
        "device": {
            "serial_redacted": True,
            "model": "Quest 3S",
            "android_sdk": "unknown",
            "horizon_os": "unknown",
            "ptc": "unknown",
            "foreground_package": "io.github.mesmerprism.rustyhostess.makepad/.MakepadAppXr",
            "adb_state": "device",
        },
        "host": {
            "os": "windows",
            "firewall_profile": "not_applicable",
            "adb_provider": "fixture",
            "toolchain_profile": "hostessctl.connectivity_probe.fixture",
        },
        "checks": [
            check_row("adb.forward.manifold_broker", "pass", "tcp:18765 -> tcp:8765"),
            check_row("broker.events.websocket", "pass", "/manifold/v1/events reachable"),
            check_row("runtime.subscriber.delivery", "pass", "delivered_count=1"),
            check_row("command.applied", "pass", "sent, transport_ok, authority_accepted, runtime_accepted, applied"),
        ],
        "measurements": empty_measurements(),
        "command_stages": {
            "sent": "pass",
            "transport_ok": "pass",
            "authority_accepted": "pass",
            "runtime_accepted": "pass",
            "applied": "pass",
        },
        "issues": [],
        "promotion": {
            "allowed": True,
            "target": "quest.device_link command feedback baseline",
            "reason": "fixture mirrors the live USB ADB command-feedback proof",
        },
    }


def qcl010_fixture_body(*, status: str, firewall_blocked: bool = False) -> dict[str, Any]:
    network_profile = qcl010_fixture_network_profile(firewall_blocked=firewall_blocked)
    listener_firewall = qcl010_fixture_listener_firewall(firewall_blocked=firewall_blocked)
    checks = [
        check_row("device.wifi_ipv4", "pass", "192.0.2.42/24"),
        check_row("host.ipv4_candidate", "pass", "selected=192.0.2.10"),
        check_row("topology.same_subnet", "pass", "192.0.2.10 is in 192.0.2.0/24"),
        check_row(
            "host_to_device.icmp_ping",
            "fail" if firewall_blocked else "pass",
            "ICMP blocked by fixture firewall profile" if firewall_blocked else "2 packets received",
            issue_codes=["hostess.issue.connectivity_probe.host_to_device_ping_failed"] if firewall_blocked else [],
        ),
        check_row("device_to_host.icmp_ping", "pass", "2 packets received"),
        check_row(
            "device_to_host.tcp_echo",
            "fail" if firewall_blocked else "pass",
            "TCP echo timed out" if firewall_blocked else DEFAULT_TCP_MARKER,
            issue_codes=["hostess.issue.connectivity_probe.tcp_echo_failed"] if firewall_blocked else [],
        ),
        check_row(
            "host.windows_network_firewall_profile",
            "warn" if firewall_blocked else "pass",
            network_profile_summary(network_profile),
            observed=network_profile,
            issue_codes=(
                ["hostess.issue.connectivity_probe.windows_network_profile_public"]
                if firewall_blocked
                else []
            ),
        ),
        check_row(
            "host.windows_firewall_listener",
            "fail" if firewall_blocked else "pass",
            windows_firewall_listener_summary(listener_firewall),
            observed=listener_firewall,
            issue_codes=(
                ["hostess.issue.connectivity_probe.no_tcp_listener_firewall_allow_rule"]
                if firewall_blocked
                else []
            ),
        ),
        check_row("protocol.websocket_echo", "skipped", "not part of the fixture slice"),
        check_row("protocol.udp_freshness", "skipped", "covered by QCL-080"),
        check_row("protocol.lsl_discovery", "skipped", "covered by QCL-081"),
    ]
    return {
        "status": status,
        "classification": "baseline_candidate",
        "topology": {
            "owner": "external_wifi",
            "network_provider": "router_or_existing_wifi",
            "endpoint_direction": "quest_to_host_lan",
            "requires_existing_wifi": True,
            "requires_adb": True,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": False,
        },
        "transport": {
            "family": "icmp_tcp",
            "route": "same_wifi_lan_probe",
            "local_endpoint": "192.0.2.10",
            "remote_endpoint": "192.0.2.42",
            "protocol_role": "topology_probe",
            "payload_class": "low_rate_diagnostic",
        },
        "device": {
            "serial_redacted": True,
            "model": "Quest fixture",
            "android_sdk": "35",
            "horizon_os": "fixture",
            "ptc": "unknown",
            "foreground_package": "unknown",
            "adb_state": "device",
            "wifi_interface": "wlan0",
            "wifi_ipv4": "192.0.2.42",
            "wifi_prefix_length": 24,
        },
        "host": {
            "os": "windows",
            "selected_ipv4": "192.0.2.10",
            "ipv4_candidates": [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture-wifi"}],
            "firewall_profile": network_profile_summary(network_profile),
            "firewall_listener": listener_firewall,
            "adb_provider": "fixture",
            "toolchain_profile": "hostessctl.connectivity_probe.fixture",
        },
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "tcp_connect_ms": None if firewall_blocked else 12,
            "reconnect_attempts": 1,
        },
        "command_stages": {
            "sent": "not_applicable",
            "transport_ok": "not_applicable",
            "authority_accepted": "not_applicable",
            "runtime_accepted": "not_applicable",
            "applied": "not_applicable",
        },
        "issues": (
            [
                issue_row(
                    "hostess.issue.connectivity_probe.same_wifi_reachability_not_proven",
                    "error",
                    "fixture models firewall-blocked same-Wi-Fi reachability",
                ),
                issue_row(
                    "hostess.issue.connectivity_probe.windows_network_profile_public",
                    "warning",
                    "fixture models a Public Windows network profile",
                ),
                issue_row(
                    "hostess.issue.connectivity_probe.no_tcp_listener_firewall_allow_rule",
                    "error",
                    "fixture models a Hostess listener without an active-profile firewall allow rule",
                ),
            ]
            if firewall_blocked
            else []
        ),
        "promotion": {
            "allowed": False,
            "target": "quest.device_link topology descriptor",
            "reason": "fixture-only topology proof",
        },
    }


def qcl011_fixture_body(*, status: str, hotspot_off: bool = False) -> dict[str, Any]:
    body = qcl010_fixture_body(status="fail" if hotspot_off else status)
    hotspot = {
        "available": True,
        "state": "Off" if hotspot_off else "On",
        "source_profile": "fixture-upstream",
        "client_count": 0 if hotspot_off else 1,
        "max_client_count": 8,
        "ssid": "RustyHostess-QCL011",
        "passphrase_set": True,
        "band": "Auto",
    }
    hotspot_status, hotspot_issue_codes = windows_mobile_hotspot_status(hotspot)
    checks = list(body["checks"])
    checks.insert(
        3,
        check_row(
            "host.windows_mobile_hotspot",
            hotspot_status,
            windows_mobile_hotspot_summary(hotspot),
            observed=hotspot,
            issue_codes=hotspot_issue_codes,
        ),
    )
    body.update(
        {
            "status": status,
            "topology": topology_for_probe("QCL-011"),
            "transport": {
                **object_value(body.get("transport")),
                "route": "pc_hotspot_lan_probe",
            },
            "checks": checks,
            "host": {
                **object_value(body.get("host")),
                "mobile_hotspot": hotspot,
                "toolchain_profile": "hostessctl.connectivity_probe.qcl011.fixture",
            },
            "promotion": {
                "allowed": False,
                "target": "quest.device_link topology descriptor",
                "reason": "fixture-only PC hotspot topology proof",
            },
        }
    )
    if hotspot_off:
        body["issues"] = [
            issue_row(
                "hostess.issue.connectivity_probe.pc_hotspot_off",
                "error",
                "fixture models Windows Mobile Hotspot switched off",
            ),
            issue_row(
                "hostess.issue.connectivity_probe.pc_hotspot_reachability_not_proven",
                "error",
                "fixture models no PC-hotspot reachability while hotspot is off",
            ),
        ]
    return body


def qcl05x_fixture_body(*, probe_id: str, status: str, failure: str = "") -> dict[str, Any]:
    is_rfcomm = probe_id == "QCL-050"
    protocol_name = "rfcomm" if is_rfcomm else "ble_gatt"
    transport_family = "bluetooth_rfcomm" if is_rfcomm else "ble_gatt"
    protocol_check_name = "protocol.rfcomm_control" if is_rfcomm else "protocol.ble_gatt_status"
    protocol_evidence = (
        "RFCOMM service discovered; 4/4 bounded messages echoed; RTT p95=42ms"
        if is_rfcomm
        else "BLE GATT service discovered; read/write/notify passed; RTT p95=68ms"
    )
    failed_pairing = failure == "pairing_refused"
    permission_denied = failure == "permission_denied"
    checks = [
        check_row(
            "host.bluetooth_adapter",
            "pass",
            "Windows Bluetooth adapter present",
            observed={
                "available": True,
                "adapter_status": "OK",
                "adapter_name": "fixture Bluetooth Adapter",
                "address_redacted": True,
            },
        ),
        check_row(
            "host.bluetooth_service",
            "pass",
            "bthserv running; BluetoothUserService running",
            observed={"bthserv_status": "Running", "user_service_running": True},
        ),
        check_row(
            "device.bluetooth_adapter",
            "pass",
            "Quest Bluetooth enabled and ON",
            observed={
                "available": True,
                "enabled": True,
                "state": "ON",
                "name": "Quest fixture",
                "address_present": True,
                "address_redacted": True,
                "bonded_device_count": 1,
            },
        ),
        check_row(
            "bluetooth.pairing_bond_state",
            "blocked" if failed_pairing else "pass",
            "operator refused pairing prompt" if failed_pairing else "paired and bonded",
            observed={"manual_prompt_required": True, "bonded": not failed_pairing},
            issue_codes=["hostess.issue.connectivity_probe.bluetooth_pairing_refused"] if failed_pairing else [],
        ),
        check_row(
            "bluetooth.permission_state",
            "blocked" if permission_denied else "pass",
            "Bluetooth permission denied" if permission_denied else "Bluetooth permission granted",
            observed={"permission_granted": not permission_denied},
            issue_codes=["hostess.issue.connectivity_probe.bluetooth_permission_denied"] if permission_denied else [],
        ),
        check_row(
            protocol_check_name,
            "blocked" if (failed_pairing or permission_denied) else "pass",
            "service unavailable because setup was blocked" if (failed_pairing or permission_denied) else protocol_evidence,
            observed=(
                {"service_uuid": "not_reached"}
                if (failed_pairing or permission_denied)
                else {
                    "service_uuid": "fixture-redacted-service-uuid",
                    "message_count": 4 if is_rfcomm else 2,
                    "bytes_exchanged": 128 if is_rfcomm else 32,
                    "rtt_ms_p95": 42 if is_rfcomm else 68,
                }
            ),
            issue_codes=(
                ["hostess.issue.connectivity_probe.bluetooth_service_not_reached"]
                if (failed_pairing or permission_denied)
                else []
            ),
        ),
        check_row(
            "protocol.bluetooth_payload_exchange",
            "blocked" if (failed_pairing or permission_denied) else "pass",
            "payload exchange not reached" if (failed_pairing or permission_denied) else "bounded payload exchange passed",
            observed={"high_rate_payload": False},
            issue_codes=(
                ["hostess.issue.connectivity_probe.bluetooth_payload_not_tested"]
                if (failed_pairing or permission_denied)
                else []
            ),
        ),
        check_row(
            "bluetooth.reconnect_cleanup",
            "skipped" if (failed_pairing or permission_denied) else "pass",
            "cleanup/reconnect not reached" if (failed_pairing or permission_denied) else "disconnect, reconnect, and cleanup passed",
            observed={"socket_closed": not (failed_pairing or permission_denied), "adapter_state_changed": False},
        ),
    ]
    issues: list[dict[str, str]] = []
    if failed_pairing:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.bluetooth_pairing_refused",
                "error",
                "fixture models a refused Bluetooth pairing prompt",
            )
        )
    if permission_denied:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.bluetooth_permission_denied",
                "error",
                "fixture models denied Bluetooth runtime permission",
            )
        )
    return {
        "status": status,
        "classification": "discovery_control_candidate",
        "topology": topology_for_bluetooth_probe(probe_id),
        "transport": {
            **bluetooth_transport_for_probe(probe_id),
            "endpoint_source": f"fixture_{protocol_name}_helper",
        },
        "device": {
            "serial_redacted": True,
            "model": "Quest fixture",
            "bluetooth": {
                "available": True,
                "enabled": True,
                "state": "ON",
                "address_present": True,
                "address_redacted": True,
            },
            "adb_provider": "fixture",
        },
        "host": {
            "os": "windows",
            "bluetooth": {
                "available": True,
                "adapter_status": "OK",
                "adapter_name": "fixture Bluetooth Adapter",
                "bthserv_status": "Running",
                "user_service_running": True,
                "address_redacted": True,
            },
            "toolchain_profile": f"hostessctl.connectivity_probe.{probe_id.lower()}.fixture",
        },
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "bluetooth_bytes_exchanged": 0 if (failed_pairing or permission_denied) else (128 if is_rfcomm else 32),
            "bluetooth_rtt_ms_p95": None if (failed_pairing or permission_denied) else (42 if is_rfcomm else 68),
            "reconnect_attempts": 0 if (failed_pairing or permission_denied) else 1,
        },
        "issues": issues,
        "promotion": {
            "allowed": not (failed_pairing or permission_denied),
            "target": "quest.device_link bluetooth discovery/control descriptor",
            "reason": (
                "fixture models bounded Bluetooth discovery/control payload exchange"
                if not (failed_pairing or permission_denied)
                else "fixture models blocked Bluetooth setup before payload exchange"
            ),
        },
    }


def qcl080_fixture_body(
    *,
    status: str,
    firewall_blocked: bool = False,
    app_owned: bool = False,
) -> dict[str, Any]:
    network_profile = qcl010_fixture_network_profile(firewall_blocked=firewall_blocked)
    listener_firewall = qcl080_fixture_listener_firewall(firewall_blocked=firewall_blocked)
    network_profile["listener_firewall"] = listener_firewall
    udp_status = "fail" if firewall_blocked else "pass"
    endpoint_source = "app_owned_runtime_udp_sender" if app_owned else "adb_shell_udp_generator"
    checks = [
        check_row("device.adb_state", "pass", "device"),
        check_row("device.wifi_ipv4", "pass", "192.0.2.42/24"),
        check_row("host.ipv4_candidate", "pass", "selected=192.0.2.10"),
        check_row("topology.same_subnet", "pass", "192.0.2.10 is in 192.0.2.0/24"),
        check_row(
            "protocol.udp_freshness",
            udp_status,
            "12/12 packets, loss=0.0%, p95_gap=52ms"
            if not firewall_blocked
            else "0/12 packets, loss=100.0%",
            observed={
                "host_ip": "192.0.2.10",
                "port": DEFAULT_QCL080_UDP_PORT,
                "marker": DEFAULT_UDP_MARKER,
                "packets_requested": 12,
                "packets_received": 0 if firewall_blocked else 12,
                "unique_sequences": [] if firewall_blocked else list(range(12)),
                "duplicates": 0,
                "loss_percent": 100.0 if firewall_blocked else 0.0,
                "elapsed_ms": 700 if not firewall_blocked else 5000,
                "interarrival_ms_p95": None if firewall_blocked else 52,
                "generator": endpoint_source,
                "runtime_marker": (
                    qcl080_app_owned_marker_observed(status="sent", packets_sent=12)
                    if app_owned and not firewall_blocked
                    else {}
                ),
            },
            issue_codes=["hostess.issue.connectivity_probe.udp_freshness_failed"] if firewall_blocked else [],
        ),
        *(
            [
                check_row(
                    "runtime.qcl080_udp_sender",
                    "pass",
                    "Makepad runtime marker status=sent packetsSent=12/12",
                    observed=qcl080_app_owned_marker_observed(status="sent", packets_sent=12),
                )
            ]
            if app_owned and not firewall_blocked
            else []
        ),
        check_row(
            "host.windows_network_firewall_profile",
            "warn" if firewall_blocked else "pass",
            network_profile_summary(network_profile),
            observed=network_profile,
            issue_codes=(
                ["hostess.issue.connectivity_probe.windows_network_profile_public"]
                if firewall_blocked
                else []
            ),
        ),
        check_row(
            "host.windows_firewall_listener",
            "fail" if firewall_blocked else "pass",
            windows_firewall_listener_summary(listener_firewall),
            observed=listener_firewall,
            issue_codes=(
                ["hostess.issue.connectivity_probe.no_udp_listener_firewall_allow_rule"]
                if firewall_blocked
                else []
            ),
        ),
    ]
    return {
        "status": status,
        "classification": "protocol_fit_candidate",
        "topology": {
            "owner": "external_wifi",
            "network_provider": "router_or_existing_wifi",
            "endpoint_direction": "quest_to_host_lan",
            "requires_existing_wifi": True,
            "requires_adb": True,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": False,
        },
        "transport": {
            "family": "udp",
            "route": "qcl080_udp_freshness",
            "local_endpoint": f"192.0.2.10:{DEFAULT_QCL080_UDP_PORT}",
            "remote_endpoint": "192.0.2.42",
            "protocol_role": "freshness_probe",
            "payload_class": (
                "low_rate_app_owned_diagnostic_datagram" if app_owned else "low_rate_diagnostic_datagram"
            ),
            "endpoint_source": endpoint_source,
        },
        "device": {
            "serial_redacted": True,
            "model": "Quest 3S",
            "android_sdk": "unknown",
            "horizon_os": "unknown",
            "ptc": "unknown",
            "foreground_package": "not_checked",
            "adb_state": "device",
            "wifi_interface": "wlan0",
            "wifi_ipv4": "192.0.2.42",
            "wifi_prefix_length": 24,
        },
        "host": {
            "os": "windows",
            "selected_ipv4": "192.0.2.10",
            "firewall_profile": network_profile_summary(network_profile),
            "firewall_listener": listener_firewall,
            "adb_provider": "fixture",
            "toolchain_profile": "hostessctl.connectivity_probe.fixture",
        },
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "udp_packets_sent": 12,
            "udp_packets_received": 0 if firewall_blocked else 12,
            "udp_loss_percent": 100.0 if firewall_blocked else 0.0,
            "jitter_ms_p95": None if firewall_blocked else 52,
            "reconnect_attempts": 1,
        },
        "issues": (
            [
                issue_row(
                    "hostess.issue.connectivity_probe.udp_freshness_not_proven",
                    "error",
                    "UDP freshness was not proven by the available checks",
                ),
                issue_row(
                    "hostess.issue.connectivity_probe.windows_network_profile_public",
                    "warning",
                    "active Windows network/firewall profile can block Quest-to-PC LAN listeners",
                ),
                issue_row(
                    "hostess.issue.connectivity_probe.no_udp_listener_firewall_allow_rule",
                    "error",
                    "no Windows Firewall allow rule covers the Hostess UDP freshness listener for the active profile",
                ),
            ]
            if firewall_blocked
            else []
        ),
        "promotion": {
            "allowed": False,
            "target": "quest.device_link UDP stream capability descriptor",
            "reason": (
                "fixture covers app-owned runtime UDP datagrams"
                if app_owned
                else "fixture covers diagnostic UDP datagrams; app-owned runtime sender remains separate evidence"
            ),
        },
    }


def qcl081_fixture_body(*, status: str, discovery_blocked: bool = False) -> dict[str, Any]:
    discovery_status = "fail" if discovery_blocked else "pass"
    continuity_status = "blocked" if discovery_blocked else "pass"
    checks = [
        check_row("device.adb_state", "skipped", "fixture does not require a headset"),
        check_row("host.ipv4_candidate", "pass", "selected=192.0.2.10"),
        check_row("topology.same_subnet", "skipped", "host-loopback fixture"),
        check_row(
            "protocol.lsl_discovery",
            discovery_status,
            "stream RustyQCL081 discovered in 42ms" if not discovery_blocked else "no LSL stream discovered",
            observed={
                "source": "host-loopback",
                "stream_name": "RustyQCL081",
                "stream_type": "Markers",
                "discovery_ms": None if discovery_blocked else 42,
            },
            issue_codes=["hostess.issue.connectivity_probe.lsl_discovery_failed"] if discovery_blocked else [],
        ),
        check_row(
            "protocol.lsl_sample_continuity",
            continuity_status,
            "16/16 samples received, loss=0.0%" if not discovery_blocked else "sample continuity blocked by discovery failure",
            observed={
                "samples_requested": 16,
                "samples_received": 0 if discovery_blocked else 16,
                "loss_percent": 100.0 if discovery_blocked else 0.0,
                "monotonic_sequences": not discovery_blocked,
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.lsl_sample_continuity_blocked"]
                if discovery_blocked
                else []
            ),
        ),
    ]
    return {
        "status": status,
        "classification": "protocol_fit_candidate",
        "topology": {
            "owner": "host_local",
            "network_provider": "loopback",
            "endpoint_direction": "lsl_multicast_discovery_plus_tcp_samples",
            "requires_existing_wifi": False,
            "requires_adb": False,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": False,
        },
        "transport": {
            "family": "lsl",
            "route": "qcl081_lsl_discovery_sample_continuity",
            "local_endpoint": "host-loopback",
            "remote_endpoint": "host-loopback",
            "protocol_role": "study_stream_probe",
            "payload_class": "lsl_float32_samples",
            "endpoint_source": "host-loopback",
        },
        "device": {
            "serial_redacted": True,
            "foreground_package": "not_checked",
            "adb_state": "not_applicable",
        },
        "host": {
            "os": "windows",
            "selected_ipv4": "192.0.2.10",
            "adb_provider": "fixture",
            "toolchain_profile": "hostessctl.connectivity_probe.fixture",
        },
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "lsl_discovery_ms": None if discovery_blocked else 42,
            "lsl_samples_requested": 16,
            "lsl_samples_received": 0 if discovery_blocked else 16,
            "lsl_sample_loss_percent": 100.0 if discovery_blocked else 0.0,
        },
        "issues": (
            [
                issue_row(
                    "hostess.issue.connectivity_probe.lsl_continuity_not_proven",
                    "error",
                    "fixture models blocked LSL discovery/sample continuity",
                )
            ]
            if discovery_blocked
            else []
        ),
        "promotion": {
            "allowed": False,
            "target": "quest.device_link LSL stream capability descriptor",
            "reason": "fixture covers LSL mechanics; Quest-owned LSL producer remains separate evidence",
        },
    }


def qcl083_fixture_body(*, status: str, malformed: bool = False) -> dict[str, Any]:
    failed = status != "pass" or malformed
    checks = [
        check_row(
            "protocol.osc_message_shape",
            "fail" if malformed else "pass",
            "malformed OSC packet rejected" if malformed else "OSC address and int/string payload shape parsed",
            observed={"address": "/rusty/qcl083", "type_tags": "invalid" if malformed else ",is"},
            issue_codes=["hostess.issue.connectivity_probe.osc_packet_malformed"] if malformed else [],
        ),
        check_row(
            "protocol.osc_payload_exchange",
            "fail" if failed else "pass",
            "OSC payload exchange failed" if failed else "16/16 OSC messages acknowledged, loss=0.0%",
            observed={
                "messages_requested": 16,
                "messages_received": 0 if failed else 16,
                "messages_acknowledged": 0 if failed else 16,
                "loss_percent": 100.0 if failed else 0.0,
                "round_trip_ms_p95": None if failed else 8,
                "monotonic_sequences": not failed,
            },
            issue_codes=["hostess.issue.connectivity_probe.osc_exchange_failed"] if failed else [],
        ),
    ]
    return {
        "status": "fail" if failed else "pass",
        "classification": "protocol_fit_candidate",
        "topology": {
            "owner": "host_local",
            "network_provider": "loopback",
            "endpoint_direction": "osc_udp_control_telemetry",
            "requires_existing_wifi": False,
            "requires_adb": False,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": False,
        },
        "transport": {
            "family": "osc",
            "route": "qcl083_osc_udp_payload_exchange",
            "local_endpoint": "host-loopback",
            "remote_endpoint": "host-loopback",
            "protocol_role": "low_rate_control_telemetry_probe",
            "payload_class": "osc_bounded_messages",
            "endpoint_source": "host-loopback",
        },
        "device": {"serial_redacted": True, "model": "fixture", "wifi_ipv4": ""},
        "host": {"os": "windows", "toolchain_profile": "hostessctl.connectivity_probe.qcl083.fixture"},
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "osc_messages_requested": 16,
            "osc_messages_received": 0 if failed else 16,
            "osc_loss_percent": 100.0 if failed else 0.0,
            "osc_rtt_ms_p95": None if failed else 8,
        },
        "issues": (
            [
                issue_row(
                    "hostess.issue.connectivity_probe.osc_exchange_failed",
                    "error",
                    "fixture models malformed or failed OSC payload exchange",
                )
            ]
            if failed
            else []
        ),
        "promotion": {
            "allowed": False,
            "target": "quest.device_link OSC control/telemetry capability descriptor",
            "reason": "fixture covers OSC mechanics; Quest-owned OSC sender/receiver remains separate evidence",
        },
    }


def qcl084_fixture_body(*, status: str, dependency_missing: bool = False) -> dict[str, Any]:
    blocked = status == "blocked" or dependency_missing
    checks = [
        check_row(
            "protocol.zeromq_dependency",
            "blocked" if blocked else "pass",
            "native Rust ZeroMQ adapter unavailable"
            if blocked
            else "pure Rust rusty-manifold-zmq adapter available for PUB/SUB",
            observed={"source": "manifold-zmq-loopback", "pattern": "pub-sub", "bundles_libzmq": False},
            issue_codes=["hostess.issue.connectivity_probe.manifold_zmq_root_missing"] if blocked else [],
        ),
        check_row(
            "protocol.zeromq_payload_exchange",
            "blocked" if blocked else "pass",
            "ZeroMQ payload exchange blocked by dependency/source failure"
            if blocked
            else "5/5 native Rust ZeroMQ PUB/SUB messages received",
            observed={
                "messages_requested": 5,
                "messages_received": 0 if blocked else 5,
                "messages_acknowledged": 0 if blocked else 5,
                "round_trip_ms_p95": None if blocked else 5,
                "dropped_count": 0 if not blocked else None,
                "decode_error_count": 0 if not blocked else None,
            },
            issue_codes=["hostess.issue.connectivity_probe.manifold_zmq_root_missing"] if blocked else [],
        ),
    ]
    return {
        "status": "blocked" if blocked else "pass",
        "classification": "protocol_fit_candidate",
        "topology": {
            "owner": "host_local",
            "network_provider": "loopback",
            "endpoint_direction": "zeromq_socket_exchange",
            "requires_existing_wifi": False,
            "requires_adb": False,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": False,
        },
        "transport": {
            "family": "zeromq",
            "route": "qcl084_zeromq_socket_exchange",
            "local_endpoint": "host-loopback",
            "remote_endpoint": "host-loopback",
            "protocol_role": "native_rust_transport_probe",
            "payload_class": "bounded_zeromq_messages",
            "endpoint_source": "manifold-zmq-loopback",
        },
        "device": {"serial_redacted": True, "model": "fixture", "wifi_ipv4": ""},
        "host": {"os": "windows", "toolchain_profile": "hostessctl.connectivity_probe.qcl084.fixture"},
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "zeromq_messages_requested": 5,
            "zeromq_messages_received": 0 if blocked else 5,
            "zeromq_rtt_ms_p95": None if blocked else 5,
        },
        "issues": (
            [
                issue_row(
                    "hostess.issue.connectivity_probe.manifold_zmq_root_missing",
                    "error",
                    "fixture models missing native Manifold ZeroMQ adapter",
                )
            ]
            if blocked
            else []
        ),
        "promotion": {
            "allowed": False,
            "target": "quest.device_link ZeroMQ/native Rust transport capability descriptor",
            "reason": "fixture covers ZeroMQ mechanics; native Rust broker/runtime route remains separate evidence",
        },
    }


def qcl010_fixture_network_profile(*, firewall_blocked: bool) -> dict[str, Any]:
    active_category = "Public" if firewall_blocked else "Private"
    return {
        "connections": [
            {
                "Name": "fixture-wifi",
                "InterfaceAlias": "Wi-Fi",
                "InterfaceIndex": 16,
                "NetworkCategory": active_category,
                "IPv4Connectivity": "Internet",
                "IPv6Connectivity": "Internet",
            }
        ],
        "firewall": [
            {
                "Name": name,
                "Enabled": True,
                "DefaultInboundAction": "NotConfigured",
                "DefaultOutboundAction": "NotConfigured",
                "AllowInboundRules": "NotConfigured",
                "NotifyOnListen": True,
                "LogFileName": "%systemroot%\\system32\\LogFiles\\Firewall\\pfirewall.log",
                "LogBlocked": False,
                "LogAllowed": False,
            }
            for name in ["Domain", "Private", "Public"]
        ],
        "listener_firewall": qcl010_fixture_listener_firewall(firewall_blocked=firewall_blocked),
    }


def qcl010_fixture_listener_firewall(*, firewall_blocked: bool) -> dict[str, Any]:
    active_profiles = ["Public"] if firewall_blocked else ["Private"]
    rule = {
        "name": "Rusty Hostess connectivity probe fixture",
        "profiles": active_profiles,
        "profile_mask": 2 if not firewall_blocked else 4,
        "protocol": 6,
        "local_ports": "49152",
        "application_name": "python.exe",
        "profiles_apply_to_active": not firewall_blocked,
    }
    return {
        "program": "python.exe",
        "protocol": "TCP",
        "port": 49152,
        "bind_host": "0.0.0.0",
        "active_profiles": active_profiles,
        "matching_rule_count": 0 if firewall_blocked else 1,
        "matching_rules": [] if firewall_blocked else [rule],
        "allowed_on_active_profile": not firewall_blocked,
        "probe": "windows_firewall_com_policy",
    }


def qcl080_fixture_listener_firewall(*, firewall_blocked: bool) -> dict[str, Any]:
    active_profiles = ["Public"] if firewall_blocked else ["Private"]
    rule = {
        "name": "Rusty Hostess QCL-080 UDP Freshness 18767",
        "profiles": active_profiles,
        "profile_mask": 2 if not firewall_blocked else 4,
        "protocol": 17,
        "local_ports": str(DEFAULT_QCL080_UDP_PORT),
        "application_name": "python.exe",
        "profiles_apply_to_active": not firewall_blocked,
    }
    return {
        "program": "python.exe",
        "protocol": "UDP",
        "port": DEFAULT_QCL080_UDP_PORT,
        "bind_host": "0.0.0.0",
        "active_profiles": active_profiles,
        "matching_rule_count": 0 if firewall_blocked else 1,
        "matching_rules": [] if firewall_blocked else [rule],
        "allowed_on_active_profile": not firewall_blocked,
        "probe": "windows_firewall_com_policy",
    }
