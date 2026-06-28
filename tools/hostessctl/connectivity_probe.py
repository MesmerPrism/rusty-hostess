"""Quest connectivity topology probe reports for hostessctl."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.runtime import run_captured as default_run_captured


CONNECTIVITY_PROBE_SCHEMA = "rusty.quest.connectivity_topology_probe.v1"
CONNECTIVITY_PROBE_VALIDATION_SCHEMA = "rusty.hostess.connectivity_topology_probe.validation.v1"
VALID_STATUSES = {"planned", "pass", "warn", "fail", "blocked", "skipped"}
VALID_PROBE_IDS = {"QCL-000", "QCL-010"}
DEFAULT_TCP_MARKER = "rusty-qcl-tcp-echo"


def run_connectivity_probe(
    args: argparse.Namespace,
    *,
    run_captured_func: Any | None = None,
    run_timeout_func: Any | None = None,
    clock_func: Any | None = None,
    host_ipv4_func: Any | None = None,
    tcp_echo_func: Any | None = None,
) -> int:
    """Write a connectivity probe report and validation sidecar."""

    run_captured = run_captured_func or default_run_captured
    clock = clock_func or utc_now
    if getattr(args, "mode", "fixture") == "fixture":
        report = fixture_report(args, observed_at=clock())
    else:
        report = live_same_wifi_report(
            args,
            run_captured_func=run_captured,
            run_timeout_func=run_timeout_func or default_run_captured_timeout,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
            tcp_echo_func=tcp_echo_func,
        )

    validation = validate_connectivity_probe_report(report)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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


def live_same_wifi_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    run_timeout_func: Any,
    clock_func: Any,
    host_ipv4_func: Any | None = None,
    tcp_echo_func: Any | None = None,
) -> dict[str, Any]:
    if getattr(args, "probe_id", "QCL-010") != "QCL-010":
        raise SystemExit("live connectivity-probe currently supports --probe-id QCL-010")
    if not getattr(args, "adb", None) or not getattr(args, "serial", None):
        raise SystemExit("connectivity-probe live mode requires --adb and --serial")

    observed_at = clock_func()
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    device = collect_device_identity(args, run_captured_func, checks, issues)
    host_candidates = (
        host_ipv4_func()
        if host_ipv4_func is not None
        else collect_host_ipv4_candidates(run_captured_func)
    )
    host_ip = str(getattr(args, "host_ip", "") or "").strip() or choose_host_ip(
        host_candidates,
        device.get("wifi_ipv4"),
        device.get("wifi_prefix_length"),
    )
    checks.append(
        check_row(
            "host.ipv4_candidate",
            "pass" if host_ip else "blocked",
            f"selected={host_ip or 'none'} candidates={','.join(candidate.get('ip', '') for candidate in host_candidates)}",
            observed={"selected_ip": host_ip, "candidates": host_candidates},
            issue_codes=[] if host_ip else ["hostess.issue.connectivity_probe.host_ip_missing"],
        )
    )
    if not host_ip:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.host_ip_missing",
                "error",
                "no host IPv4 address was available for the same-Wi-Fi probe",
            )
        )

    same_subnet = same_subnet_check(host_ip, device.get("wifi_ipv4"), device.get("wifi_prefix_length"))
    checks.append(same_subnet)
    if same_subnet["status"] == "fail":
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.subnet_mismatch",
                "warning",
                "selected host IPv4 address is not in the Quest Wi-Fi subnet",
            )
        )

    if host_ip and device.get("wifi_ipv4") and not getattr(args, "skip_host_ping", False):
        checks.append(host_to_device_ping(args, str(device["wifi_ipv4"]), run_timeout_func))
    else:
        checks.append(check_row("host_to_device.icmp_ping", "skipped", "host-to-device ping skipped or missing device IP"))

    if host_ip and not getattr(args, "skip_device_ping", False):
        checks.append(device_to_host_ping(args, host_ip, run_timeout_func))
    else:
        checks.append(check_row("device_to_host.icmp_ping", "skipped", "device-to-host ping skipped or missing host IP"))

    tcp_result: dict[str, Any] | None = None
    if host_ip and not getattr(args, "skip_tcp_echo", False):
        tcp_runner = tcp_echo_func or device_to_host_tcp_echo
        tcp_result = tcp_runner(args, host_ip, run_timeout_func)
        checks.append(tcp_result)
    else:
        checks.append(check_row("device_to_host.tcp_echo", "skipped", "TCP echo skipped or missing host IP"))

    network_profile = collect_windows_network_profile(run_captured_func)
    checks.append(
        check_row(
            "host.windows_network_firewall_profile",
            "pass" if network_profile else "skipped",
            network_profile_summary(network_profile) if network_profile else "Windows network/firewall profile not available",
            observed=network_profile,
        )
    )
    checks.append(
        check_row(
            "protocol.websocket_echo",
            "skipped",
            "no Quest app WebSocket echo endpoint is part of this initial same-Wi-Fi probe",
            issue_codes=["hostess.issue.connectivity_probe.websocket_echo_not_implemented"],
        )
    )
    checks.append(check_row("protocol.udp_freshness", "skipped", "UDP freshness is a later QCL-080 protocol-fit probe"))
    checks.append(check_row("protocol.lsl_discovery", "skipped", "LSL discovery is a later QCL-081 study-stream probe"))

    status = live_qcl010_status(checks, host_ip, device.get("wifi_ipv4"))
    if status == "warn":
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.partial_protocol_coverage",
                "warning",
                "same-Wi-Fi topology was probed with ICMP/TCP only; WebSocket, UDP, and LSL probes remain separate",
            )
        )
    if status in {"fail", "blocked"}:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.same_wifi_reachability_not_proven",
                "error",
                "same-Wi-Fi reachability was not proven by the available checks",
            )
        )

    report = base_report(args, observed_at=observed_at)
    report.update(
        {
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
                "local_endpoint": host_ip or "unknown",
                "remote_endpoint": str(device.get("wifi_ipv4") or "unknown"),
                "protocol_role": "topology_probe",
                "payload_class": "low_rate_diagnostic",
            },
            "device": device,
            "host": {
                "os": "windows",
                "selected_ipv4": host_ip,
                "ipv4_candidates": host_candidates,
                "firewall_profile": network_profile_summary(network_profile) if network_profile else "not_checked",
                "adb_provider": str(getattr(args, "adb", "")),
                "toolchain_profile": "hostessctl.connectivity_probe",
            },
            "checks": checks,
            "measurements": measurements_from_checks(tcp_result),
            "issues": issues,
            "promotion": {
                "allowed": False,
                "target": "quest.device_link topology descriptor",
                "reason": "initial same-Wi-Fi probe; WebSocket, UDP, LSL, and firewall classification remain separate",
            },
        }
    )
    return report


def fixture_report(args: argparse.Namespace, *, observed_at: datetime) -> dict[str, Any]:
    profile = str(getattr(args, "fixture_profile", "") or "")
    probe_id = str(getattr(args, "probe_id", "") or "QCL-010")
    if not profile:
        profile = "qcl-000-usb-adb-pass" if probe_id == "QCL-000" else "qcl-010-router-pass"
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
    raise SystemExit(f"unsupported connectivity fixture profile: {profile}")


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
            "firewall_profile": "blocked_fixture" if firewall_blocked else "not_checked",
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
                )
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


def validate_connectivity_probe_report(report: dict[str, Any]) -> dict[str, Any]:
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
    if report.get("probe_id") == "QCL-010" and report.get("status") == "pass":
        if not check_passed(report, "device.wifi_ipv4"):
            errors.append("QCL-010 pass requires device.wifi_ipv4")
        if not check_passed(report, "host.ipv4_candidate"):
            errors.append("QCL-010 pass requires host.ipv4_candidate")
        if not (
            check_passed(report, "device_to_host.tcp_echo")
            or check_passed(report, "device_to_host.icmp_ping")
            or check_passed(report, "host_to_device.icmp_ping")
        ):
            errors.append("QCL-010 pass requires at least one direct LAN reachability check")
        if check_skipped(report, "protocol.websocket_echo"):
            warnings.append("QCL-010 report does not yet include WebSocket echo coverage")
        if check_skipped(report, "protocol.udp_freshness"):
            warnings.append("QCL-010 report does not yet include UDP freshness coverage")
        if check_skipped(report, "protocol.lsl_discovery"):
            warnings.append("QCL-010 report does not yet include LSL discovery coverage")
    return {
        "$schema": CONNECTIVITY_PROBE_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "report_status": report.get("status"),
        "probe_id": report.get("probe_id"),
        "check_count": len(checks),
        "errors": errors,
        "warnings": warnings,
    }


def collect_device_identity(
    args: argparse.Namespace,
    run_captured_func: Any,
    checks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    adb_state = adb_text(args, run_captured_func, "get-state")
    model = adb_text(args, run_captured_func, "shell", "getprop", "ro.product.model")
    android_sdk = adb_text(args, run_captured_func, "shell", "getprop", "ro.build.version.sdk")
    horizon_os = adb_text(args, run_captured_func, "shell", "getprop", "ro.build.version.incremental")
    interface = str(getattr(args, "wifi_interface", "wlan0") or "wlan0")
    ip_result = run_captured_func(
        adb_command(args, "shell", "ip", "-o", "-4", "addr", "show", interface),
        allow_failure=True,
    )
    wifi_ip, prefix_length = parse_ip_addr_output(ip_result.stdout)
    if not wifi_ip:
        fallback = run_captured_func(
            adb_command(args, "shell", "ip", "addr", "show", interface),
            allow_failure=True,
        )
        wifi_ip, prefix_length = parse_ip_addr_output(fallback.stdout)
        ip_result = fallback
    checks.append(
        check_row(
            "device.adb_state",
            "pass" if adb_state == "device" else "blocked",
            adb_state or "unknown",
            observed={"serial": str(getattr(args, "serial", ""))},
            issue_codes=[] if adb_state == "device" else ["hostess.issue.connectivity_probe.adb_not_device"],
        )
    )
    checks.append(
        check_row(
            "device.wifi_ipv4",
            "pass" if wifi_ip else "blocked",
            f"{wifi_ip}/{prefix_length}" if wifi_ip else "no wlan IPv4 detected",
            observed=completed_observed(ip_result),
            issue_codes=[] if wifi_ip else ["hostess.issue.connectivity_probe.device_wifi_ip_missing"],
        )
    )
    if not wifi_ip:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.device_wifi_ip_missing",
                "error",
                f"no IPv4 address was detected on Quest interface {interface}",
            )
        )
    return {
        "serial_redacted": False,
        "serial": str(getattr(args, "serial", "")),
        "model": model or "unknown",
        "android_sdk": android_sdk or "unknown",
        "horizon_os": horizon_os or "unknown",
        "ptc": "unknown",
        "foreground_package": "not_checked",
        "adb_state": adb_state or "unknown",
        "wifi_interface": interface,
        "wifi_ipv4": wifi_ip or "",
        "wifi_prefix_length": prefix_length,
    }


def collect_host_ipv4_candidates(run_captured_func: Any) -> list[dict[str, Any]]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-NetIPAddress -AddressFamily IPv4 | "
            "Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'} | "
            "Select-Object InterfaceAlias,IPAddress,PrefixLength | ConvertTo-Json -Compress"
        ),
    ]
    result = run_captured_func(command, allow_failure=True)
    candidates: list[dict[str, Any]] = []
    try:
        parsed = json.loads(result.stdout.strip() or "[]")
        rows = parsed if isinstance(parsed, list) else [parsed]
        for row in rows:
            if not isinstance(row, dict):
                continue
            ip = str(row.get("IPAddress") or "")
            if is_ipv4(ip):
                candidates.append(
                    {
                        "ip": ip,
                        "prefix_length": int(row.get("PrefixLength") or 24),
                        "interface": str(row.get("InterfaceAlias") or ""),
                    }
                )
    except Exception:
        candidates = []
    return candidates if candidates else socket_host_ipv4_candidates()


def collect_windows_network_profile(run_captured_func: Any) -> dict[str, Any]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$connections = Get-NetConnectionProfile | "
            "Select-Object InterfaceAlias,"
            "@{Name='NetworkCategory';Expression={$_.NetworkCategory.ToString()}},"
            "@{Name='IPv4Connectivity';Expression={$_.IPv4Connectivity.ToString()}}; "
            "$firewall = Get-NetFirewallProfile | "
            "Select-Object Name,Enabled,"
            "@{Name='DefaultInboundAction';Expression={$_.DefaultInboundAction.ToString()}}; "
            "[pscustomobject]@{connections=$connections; firewall=$firewall} | ConvertTo-Json -Compress -Depth 4"
        ),
    ]
    result = run_captured_func(command, allow_failure=True)
    if result.returncode != 0:
        return {}
    try:
        parsed = json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def network_profile_summary(profile: dict[str, Any]) -> str:
    connections = profile.get("connections")
    if isinstance(connections, dict):
        connection_rows = [connections]
    elif isinstance(connections, list):
        connection_rows = [row for row in connections if isinstance(row, dict)]
    else:
        connection_rows = []
    firewall = profile.get("firewall")
    if isinstance(firewall, dict):
        firewall_rows = [firewall]
    elif isinstance(firewall, list):
        firewall_rows = [row for row in firewall if isinstance(row, dict)]
    else:
        firewall_rows = []
    connection_text = ", ".join(
        f"{row.get('InterfaceAlias', 'unknown')}:{row.get('NetworkCategory', 'unknown')}"
        for row in connection_rows
    )
    firewall_text = ", ".join(
        f"{row.get('Name', 'unknown')} enabled={row.get('Enabled', 'unknown')} inbound={row.get('DefaultInboundAction', 'unknown')}"
        for row in firewall_rows
    )
    return "; ".join(part for part in [connection_text, firewall_text] if part) or "not_checked"


def socket_host_ipv4_candidates() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = str(info[4][0])
            if is_ipv4(ip) and not ip.startswith("127.") and not ip.startswith("169.254."):
                candidates.append({"ip": ip, "prefix_length": 24, "interface": "socket"})
    except OSError:
        return []
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate["ip"] in seen:
            continue
        seen.add(candidate["ip"])
        unique.append(candidate)
    return unique


def choose_host_ip(candidates: list[dict[str, Any]], device_ip: Any, prefix_length: Any) -> str:
    if device_ip and prefix_length is not None:
        try:
            network = ipaddress.ip_network(f"{device_ip}/{int(prefix_length)}", strict=False)
            for candidate in candidates:
                ip = ipaddress.ip_address(str(candidate.get("ip", "")))
                if ip in network:
                    return str(ip)
        except ValueError:
            pass
    return str(candidates[0].get("ip", "")) if candidates else ""


def same_subnet_check(host_ip: str, device_ip: Any, prefix_length: Any) -> dict[str, Any]:
    if not host_ip or not device_ip or prefix_length is None:
        return check_row(
            "topology.same_subnet",
            "blocked",
            "host or device IP missing",
            issue_codes=["hostess.issue.connectivity_probe.subnet_inputs_missing"],
        )
    try:
        network = ipaddress.ip_network(f"{device_ip}/{int(prefix_length)}", strict=False)
        in_subnet = ipaddress.ip_address(host_ip) in network
    except ValueError as exc:
        return check_row(
            "topology.same_subnet",
            "blocked",
            str(exc),
            issue_codes=["hostess.issue.connectivity_probe.subnet_parse_failed"],
        )
    return check_row(
        "topology.same_subnet",
        "pass" if in_subnet else "fail",
        f"{host_ip} {'is' if in_subnet else 'is not'} in {network}",
        observed={"host_ip": host_ip, "device_ip": str(device_ip), "network": str(network)},
        issue_codes=[] if in_subnet else ["hostess.issue.connectivity_probe.subnet_mismatch"],
    )


def host_to_device_ping(args: argparse.Namespace, device_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    timeout_ms = int(float(getattr(args, "ping_timeout_seconds", 2.0)) * 1000)
    result = run_timeout_func(
        ["ping", "-n", str(getattr(args, "ping_count", 2)), "-w", str(timeout_ms), device_ip],
        timeout_seconds=float(getattr(args, "ping_timeout_seconds", 2.0)) * 4,
    )
    passed = result.returncode == 0
    return check_row(
        "host_to_device.icmp_ping",
        "pass" if passed else "fail",
        ping_summary(result),
        observed=completed_observed(result),
        issue_codes=[] if passed else ["hostess.issue.connectivity_probe.host_to_device_ping_failed"],
    )


def device_to_host_ping(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    result = run_timeout_func(
        adb_command(
            args,
            "shell",
            "ping",
            "-c",
            str(getattr(args, "ping_count", 2)),
            "-W",
            str(int(float(getattr(args, "ping_timeout_seconds", 2.0)))),
            host_ip,
        ),
        timeout_seconds=float(getattr(args, "ping_timeout_seconds", 2.0)) * 4,
    )
    passed = result.returncode == 0
    return check_row(
        "device_to_host.icmp_ping",
        "pass" if passed else "fail",
        ping_summary(result),
        observed=completed_observed(result),
        issue_codes=[] if passed else ["hostess.issue.connectivity_probe.device_to_host_ping_failed"],
    )


def device_to_host_tcp_echo(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    marker = str(getattr(args, "tcp_echo_marker", DEFAULT_TCP_MARKER) or DEFAULT_TCP_MARKER)
    timeout = float(getattr(args, "tcp_timeout_seconds", 4.0))
    bind_host = str(getattr(args, "tcp_echo_bind_host", "0.0.0.0") or "0.0.0.0")
    requested_port = int(getattr(args, "tcp_echo_port", 0) or 0)
    received: dict[str, Any] = {"data": b"", "error": ""}
    ready = threading.Event()

    def server() -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((bind_host, requested_port))
                sock.listen(1)
                sock.settimeout(timeout)
                received["port"] = sock.getsockname()[1]
                ready.set()
                conn, addr = sock.accept()
                with conn:
                    conn.settimeout(timeout)
                    received["peer"] = f"{addr[0]}:{addr[1]}"
                    received["data"] = conn.recv(256)
        except Exception as exc:
            received["error"] = str(exc)
            ready.set()

    thread = threading.Thread(target=server, daemon=True)
    started = time.monotonic()
    thread.start()
    ready.wait(timeout=timeout)
    port = int(received.get("port") or 0)
    if not port:
        return check_row(
            "device_to_host.tcp_echo",
            "blocked",
            f"TCP echo server did not start: {received.get('error') or 'unknown'}",
            issue_codes=["hostess.issue.connectivity_probe.tcp_echo_server_failed"],
        )

    command_text = (
        f"echo {shell_word(marker)} | "
        f"(toybox nc -w {int(timeout)} {host_ip} {port} || nc -w {int(timeout)} {host_ip} {port})"
    )
    result = run_timeout_func(
        adb_command(args, "shell", "sh", "-c", command_text),
        timeout_seconds=timeout + 2.0,
    )
    thread.join(timeout=timeout + 1.0)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    data = bytes(received.get("data") or b"").decode("utf-8", "replace")
    passed = marker in data
    return check_row(
        "device_to_host.tcp_echo",
        "pass" if passed else "fail",
        data.strip() or received.get("error") or "no TCP echo received",
        observed={
            "host_ip": host_ip,
            "port": port,
            "elapsed_ms": elapsed_ms,
            "adb_client": completed_observed(result),
            "server_peer": received.get("peer", ""),
        },
        issue_codes=[] if passed else ["hostess.issue.connectivity_probe.tcp_echo_failed"],
    )


def live_qcl010_status(checks: list[dict[str, Any]], host_ip: str, device_ip: Any) -> str:
    if not host_ip or not device_ip:
        return "blocked"
    if check_status(checks, "device_to_host.tcp_echo") == "pass":
        return "warn"
    if check_status(checks, "device_to_host.icmp_ping") == "pass":
        return "warn"
    return "fail"


def measurements_from_checks(tcp_result: dict[str, Any] | None) -> dict[str, Any]:
    measurements = empty_measurements()
    if tcp_result:
        observed = object_value(tcp_result.get("observed"))
        if observed.get("elapsed_ms") is not None:
            measurements["tcp_connect_ms"] = observed.get("elapsed_ms")
    measurements["reconnect_attempts"] = 1
    return measurements


def empty_measurements() -> dict[str, Any]:
    return {
        "tcp_connect_ms": None,
        "websocket_echo_ms": None,
        "udp_packets_sent": None,
        "udp_packets_received": None,
        "udp_loss_percent": None,
        "lsl_discovery_ms": None,
        "throughput_mbps": None,
        "jitter_ms_p95": None,
        "reconnect_attempts": None,
    }


def base_report(args: argparse.Namespace, *, observed_at: datetime, probe_id: str | None = None) -> dict[str, Any]:
    selected_probe_id = probe_id or str(getattr(args, "probe_id", "") or "QCL-010")
    run_id = str(getattr(args, "run_id", "") or "").strip()
    if not run_id:
        stamp = observed_at.strftime("%Y%m%d-%H%M%S")
        run_id = f"{stamp}-{selected_probe_id.lower()}"
    return {
        "schema": CONNECTIVITY_PROBE_SCHEMA,
        "schema_version": 1,
        "probe_id": selected_probe_id,
        "run_id": run_id,
        "observed_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "status": "planned",
        "classification": "baseline_candidate",
        "topology": {},
        "transport": {},
        "device": {},
        "host": {},
        "termux_sidecar": {
            "in_scope": False,
            "uid_gate": "not_checked",
            "bind_scope": "not_applicable",
            "authority_role": "none",
        },
        "checks": [],
        "measurements": empty_measurements(),
        "command_stages": {
            "sent": "not_applicable",
            "transport_ok": "not_applicable",
            "authority_accepted": "not_applicable",
            "runtime_accepted": "not_applicable",
            "applied": "not_applicable",
        },
        "issues": [],
        "artifacts": [],
        "promotion": {"allowed": False, "target": "none", "reason": "not evaluated"},
    }


def check_row(
    name: str,
    status: str,
    evidence: str,
    *,
    observed: dict[str, Any] | None = None,
    notes: str = "",
    issue_codes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "evidence": evidence,
        "observed": observed or {},
        "notes": notes,
        "issue_codes": issue_codes or [],
    }


def issue_row(issue_code: str, severity: str, message: str) -> dict[str, str]:
    return {"issue_code": issue_code, "severity": severity, "message": message}


def check_status(checks: list[dict[str, Any]], name: str) -> str:
    for check in checks:
        if check.get("name") == name:
            return str(check.get("status") or "")
    return ""


def check_passed(report: dict[str, Any], name: str) -> bool:
    return check_status(list_value(report.get("checks")), name) == "pass"


def check_skipped(report: dict[str, Any], name: str) -> bool:
    return check_status(list_value(report.get("checks")), name) == "skipped"


def adb_command(args: argparse.Namespace, *parts: str) -> list[str]:
    return [str(getattr(args, "adb", "adb")), "-s", str(getattr(args, "serial", "")), *parts]


def adb_text(args: argparse.Namespace, run_captured_func: Any, *parts: str) -> str:
    result = run_captured_func(adb_command(args, *parts), allow_failure=True)
    return result.stdout.strip()


def parse_ip_addr_output(text: str) -> tuple[str, int | None]:
    match = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+)(?:/(\d+))?", text)
    if not match:
        return "", None
    prefix = int(match.group(2)) if match.group(2) else None
    return match.group(1), prefix


def is_ipv4(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return "." in value
    except ValueError:
        return False


def ping_summary(result: subprocess.CompletedProcess[str]) -> str:
    text = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
    if not text:
        return f"returncode={result.returncode}"
    for line in text.splitlines():
        if "packet loss" in line or "Lost =" in line or "Average =" in line:
            return line.strip()
    return text.splitlines()[-1].strip()


def completed_observed(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {"returncode": result.returncode, "stdout": trim_text(result.stdout), "stderr": trim_text(result.stderr)}


def trim_text(text: str, limit: int = 800) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "...<truncated>"


def default_run_captured_timeout(command: list[str], *, timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return subprocess.CompletedProcess(
            command,
            124,
            stdout,
            stderr + f"\ncommand timed out after {timeout_seconds} seconds",
        )


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def shell_word(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9._:-]+", value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"


def utc_now() -> datetime:
    return datetime.now(UTC)
