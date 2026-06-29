"""Quest connectivity topology probe reports for hostessctl."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.runtime import run_captured as default_run_captured
from tools.hostessctl.connectivity_bluetooth import (
    qcl051_ble_gatt_payload_checks,
    qcl050_rfcomm_payload_checks,
    live_bluetooth_status,
    bluetooth_protocol_check,
    bluetooth_bytes_exchanged,
    bluetooth_measurements,
    bluetooth_transport_for_probe,
    collect_quest_bluetooth_status,
    collect_windows_bluetooth_status,
    qcl051_payload_sessions,
    qcl051_session_android,
    qcl051_session_cleanup_pass,
    qcl051_session_protocol_pass,
    qcl051_session_windows,
    quest_bluetooth_adapter_status,
    quest_bluetooth_adapter_summary,
    run_qcl050_android_rfcomm_probe,
    run_qcl051_android_ble_gatt_probe,
    topology_for_bluetooth_probe,
    windows_bluetooth_adapter_status,
    windows_bluetooth_adapter_summary,
    windows_bluetooth_service_status,
    windows_bluetooth_service_summary,
)
from tools.hostessctl.connectivity_udp import (
    DEFAULT_QCL080_UDP_PORT,
    DEFAULT_UDP_MARKER,
    device_to_host_udp_freshness,
    latest_qcl080_app_marker,
    qcl080_app_owned_marker_observed,
    qcl080_makepad_runtime_properties,
    runtime_qcl080_udp_sender_check_from_result,
    udp_endpoint_source,
)
from tools.hostessctl.connectivity_media import qcl082_fixture_body
from tools.hostessctl.connectivity_topology import (
    DEFAULT_TOPOLOGY_FIXTURE_PROFILES,
    TOPOLOGY_PROBE_IDS,
    TOPOLOGY_REQUIRED_PASS_CHECKS,
    is_topology_fixture_profile,
    topology_fixture_body,
)
from tools.hostessctl.platform_defaults import (
    ANDROID_PACKAGE,
    ANDROID_QCL083_OSC_ACTION,
    ANDROID_REMOTE_QCL083_OSC_EVIDENCE,
)
from tools.hostessctl.connectivity_data_protocols import (
    zeromq_checks_from_probe,
    osc_checks_from_probe,
    lsl_checks_from_probe,
    build_osc_message,
    lsl_discovery_sample_continuity,
    lsl_manifold_broker_probe,
    lsl_quest_runtime_preflight,
    osc_loopback_probe,
    parse_osc_message,
    parse_probe_json_stdout,
    resolve_manifold_root,
    zeromq_loopback_probe,
)
from tools.hostessctl.connectivity_probe_common import (
    issue_row,
    check_status,
    check_skipped,
    check_row,
    check_passed,
    empty_measurements,
    wait_for_json_file,
    strip_powershell_clixml_noise,
    sanitize_filename,
    redact_command_for_report,
    read_json_file,
    read_android_json_with_retry,
    powershell_executable,
    collect_android_activity_launch_precondition,
    adb_command,
    completed_observed,
    dedupe_issue_codes,
    float_value,
    int_value,
    list_value,
    median,
    object_value,
    parse_json_string,
    percentile,
    round_float,
    shell_word,
    trim_text,
)


CONNECTIVITY_PROBE_SCHEMA = "rusty.quest.connectivity_topology_probe.v1"
CONNECTIVITY_PROBE_VALIDATION_SCHEMA = "rusty.hostess.connectivity_topology_probe.validation.v1"
CONNECTIVITY_FIREWALL_RULE_SCHEMA = "rusty.quest.connectivity_windows_firewall_rule.v1"
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
DEFAULT_TCP_MARKER = "rusty-qcl-tcp-echo"
DEFAULT_QCL010_TCP_ECHO_PORT = 18766
DEFAULT_QCL083_OSC_PORT = 18783
DEFAULT_QCL084_ZEROMQ_PORT = 18784
DEFAULT_WPF_FIREWALL_PROGRAM = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "hostess-companion-wpf"
    / "bin"
    / "Debug"
    / "net9.0-windows"
    / "HostessCompanion.Wpf.exe"
)


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
    elif getattr(args, "probe_id", "QCL-010") in {"QCL-050", "QCL-051"}:
        report = live_bluetooth_report(
            args,
            run_captured_func=run_captured,
            run_timeout_func=run_timeout_func or default_run_captured_timeout,
            clock_func=clock,
        )
    elif getattr(args, "probe_id", "QCL-010") == "QCL-080":
        report = live_udp_freshness_report(
            args,
            run_captured_func=run_captured,
            run_timeout_func=run_timeout_func or default_run_captured_timeout,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
        )
    elif getattr(args, "probe_id", "QCL-010") == "QCL-081":
        report = live_lsl_report(
            args,
            run_captured_func=run_captured,
            run_timeout_func=run_timeout_func or default_run_captured_timeout,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
        )
    elif getattr(args, "probe_id", "QCL-010") == "QCL-083":
        report = live_osc_report(
            args,
            run_captured_func=run_captured,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
        )
    elif getattr(args, "probe_id", "QCL-010") == "QCL-084":
        report = live_zeromq_report(
            args,
            run_captured_func=run_captured,
            clock_func=clock,
            host_ipv4_func=host_ipv4_func,
        )
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


def run_windows_firewall_rule(
    args: argparse.Namespace,
    *,
    run_captured_func: Any | None = None,
    clock_func: Any | None = None,
) -> int:
    """Plan, apply, verify, or remove a scoped Windows Firewall listener rule."""

    run_captured = run_captured_func or default_run_captured
    clock = clock_func or utc_now
    report = windows_firewall_rule_report(args, observed_at=clock())
    action = str(report.get("action") or "plan")

    if action in {"apply", "remove"}:
        if report["status"] == "blocked":
            result_key = "apply_result" if action == "apply" else "remove_result"
            report[result_key] = {
                "attempted": False,
                "returncode": None,
                "stdout": "",
                "stderr": "firewall rule plan was blocked",
            }
        else:
            result = run_captured(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    report["powershell"]["script"],
                ],
                allow_failure=True,
            )
            action_result = {
                "attempted": True,
                **completed_observed(result),
            }
            report["action_result"] = action_result
            if action == "apply":
                report["apply_result"] = action_result
            else:
                report["remove_result"] = action_result
            report["status"] = "pass" if result.returncode == 0 else "fail"

    if action in {"apply", "verify", "remove"} and report["status"] != "blocked":
        verification = verify_windows_firewall_rule_report(report, run_captured)
        report["verification"] = verification
        if action == "verify":
            report["status"] = verification["status"]
        elif action == "apply" and report["status"] == "pass":
            report["status"] = "pass" if verification["product_rule_verified"] is True else "warn"
        elif action == "remove" and report["status"] == "pass":
            report["status"] = "warn" if verification["product_rule_verified"] is True else "pass"

    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    out = str(getattr(args, "out", "") or "").strip()
    if out:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")

    if getattr(args, "fail_on_error", False) and report["status"] not in {"pass", "planned"}:
        return 2
    return 0


def windows_firewall_rule_report(args: argparse.Namespace, *, observed_at: datetime) -> dict[str, Any]:
    port = int(getattr(args, "port", DEFAULT_QCL010_TCP_ECHO_PORT) or DEFAULT_QCL010_TCP_ECHO_PORT)
    protocol = normalize_firewall_protocol(str(getattr(args, "protocol", "") or "TCP"))
    program = normalize_firewall_program_path(
        str(getattr(args, "program", "") or default_firewall_program(protocol)).strip()
    )
    profiles = normalize_firewall_profiles(str(getattr(args, "profile", "") or "Public"))
    remote_address = str(getattr(args, "remote_address", "") or "LocalSubnet").strip()
    rule_name = str(getattr(args, "rule_name", "") or "").strip()
    if not rule_name:
        rule_name = default_firewall_rule_name(port, protocol)
    action = firewall_rule_action(args)

    issues: list[dict[str, Any]] = []
    status = "planned"
    if not program:
        status = "blocked"
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.firewall_rule_program_missing",
                "error",
                "firewall rule plan requires a program path",
            )
        )
    if port <= 0 or port > 65535:
        status = "blocked"
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.firewall_rule_port_invalid",
                "error",
                "firewall rule plan requires a TCP port from 1 to 65535",
            )
        )
    if program and diagnostic_python_program_path(program):
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.firewall_rule_program_diagnostic",
                "warning",
                "diagnostic Python listener rules are not product Hostess/WPF listener rules",
            )
        )

    if action == "remove":
        script = build_windows_firewall_rule_remove_script(rule_name=rule_name)
    elif action == "verify":
        script = build_windows_firewall_rule_verify_script(rule_name=rule_name)
    else:
        script = build_windows_firewall_rule_script(
            rule_name=rule_name,
            program=program,
            port=port,
            protocol=protocol,
            profiles=profiles,
            remote_address=remote_address,
        )
    probe_id = "QCL-010" if protocol == "TCP" else "QCL-080"
    connectivity_probe_args = [
        "connectivity-probe",
        "run",
        "--mode",
        "live",
        "--probe-id",
        probe_id,
    ]
    if protocol == "TCP":
        connectivity_probe_args.extend(["--tcp-echo-port", str(port)])
    else:
        connectivity_probe_args.extend(
            [
                "--udp-port",
                str(port),
                "--udp-listener-helper",
                program,
                "--udp-sender-source",
                "makepad-runtime",
            ]
        )

    return {
        "schema": CONNECTIVITY_FIREWALL_RULE_SCHEMA,
        "schema_version": 1,
        "observed_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "status": status,
        "action": action,
        "rule": {
            "name": rule_name,
            "direction": "Inbound",
            "action": "Allow",
            "enabled": True,
            "program": program,
            "protocol": protocol,
            "local_port": port,
            "profiles": profiles,
            "remote_address": remote_address,
            "replace_same_display_name": True,
            "scope_note": (
                "Allows only the selected program, selected protocol/port, "
                "profile set, and remote address scope."
            ),
        },
        "probe_usage": {
            "probe_id": probe_id,
            "connectivity_probe_args": connectivity_probe_args,
        },
        "powershell": {
            "requires_admin": True,
            "script": script,
            "command": (
                "powershell -NoProfile -ExecutionPolicy Bypass -Command "
                + ps_string_literal(script)
            ),
        },
        "issues": issues,
    }


def firewall_rule_action(args: argparse.Namespace) -> str:
    action = str(getattr(args, "action", "") or "").strip().lower()
    if action in {"plan", "apply", "verify", "remove"}:
        return action
    if getattr(args, "remove", False):
        return "remove"
    if getattr(args, "verify", False):
        return "verify"
    if getattr(args, "apply", False):
        return "apply"
    return "plan"


def default_firewall_program(protocol: str) -> str:
    return str(DEFAULT_WPF_FIREWALL_PROGRAM)


def default_firewall_rule_name(port: int, protocol: str) -> str:
    return (
        f"Rusty Hostess WPF QCL-010 TCP Echo {port}"
        if normalize_firewall_protocol(protocol) == "TCP"
        else f"Rusty Hostess WPF QCL-080 UDP Freshness {port}"
    )


def normalize_firewall_program_path(program: str) -> str:
    if not program:
        return ""
    candidate = Path(program)
    if candidate.is_absolute():
        return str(candidate)
    try:
        return str(candidate.resolve(strict=False))
    except OSError:
        return program


def normalize_firewall_profiles(raw_profiles: str) -> list[str]:
    allowed = {"Domain", "Private", "Public", "Any"}
    profiles: list[str] = []
    for part in raw_profiles.replace(";", ",").split(","):
        candidate = part.strip()
        if not candidate:
            continue
        normalized = candidate[:1].upper() + candidate[1:].lower()
        if normalized == "All":
            normalized = "Any"
        if normalized in allowed and normalized not in profiles:
            profiles.append(normalized)
    return profiles or ["Public"]


def normalize_firewall_protocol(raw_protocol: str) -> str:
    protocol = raw_protocol.strip().upper()
    if protocol not in {"TCP", "UDP"}:
        return "TCP"
    return protocol


def build_windows_firewall_rule_script(
    *,
    rule_name: str,
    program: str,
    port: int,
    protocol: str,
    profiles: list[str],
    remote_address: str,
) -> str:
    profile_text = ",".join(profiles)
    protocol_text = normalize_firewall_protocol(protocol)
    return " ".join(
        [
            "$ErrorActionPreference = 'Stop';",
            f"$ruleName = {ps_string_literal(rule_name)};",
            f"$program = {ps_string_literal(program)};",
            f"$port = {port};",
            f"$protocol = {ps_string_literal(protocol_text)};",
            f"$profile = {ps_string_literal(profile_text)};",
            f"$remoteAddress = {ps_string_literal(remote_address)};",
            "Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule;",
            "New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Enabled True -Program $program -Protocol $protocol -LocalPort $port -Profile $profile -RemoteAddress $remoteAddress | Out-Null;",
            "Get-NetFirewallRule -DisplayName $ruleName | Select-Object DisplayName,Enabled,Direction,Action,Profile | ConvertTo-Json -Compress;",
        ]
    )


def build_windows_firewall_rule_remove_script(*, rule_name: str) -> str:
    return " ".join(
        [
            "$ErrorActionPreference = 'Stop';",
            f"$ruleName = {ps_string_literal(rule_name)};",
            "$rules = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue;",
            "if ($rules) { $rules | Remove-NetFirewallRule; }",
            "[pscustomobject]@{DisplayName=$ruleName;Removed=($null -ne $rules)} | ConvertTo-Json -Compress;",
        ]
    )


def build_windows_firewall_rule_verify_script(*, rule_name: str) -> str:
    return " ".join(
        [
            "$ErrorActionPreference = 'Stop';",
            f"$ruleName = {ps_string_literal(rule_name)};",
            "Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | "
            "Select-Object DisplayName,Enabled,Direction,Action,Profile | ConvertTo-Json -Compress;",
        ]
    )


def verify_windows_firewall_rule_report(
    report: dict[str, Any],
    run_captured_func: Any,
) -> dict[str, Any]:
    rule = object_value(report.get("rule"))
    listener = {
        "program": str(rule.get("program") or ""),
        "protocol": str(rule.get("protocol") or "UDP"),
        "port": int(rule.get("local_port") or 0),
        "bind_host": "0.0.0.0",
        "rule_name": str(rule.get("name") or ""),
        "remote_address": str(rule.get("remote_address") or "LocalSubnet"),
    }
    network_profile = collect_windows_network_profile(run_captured_func, listener=listener)
    listener_firewall = object_value(network_profile.get("listener_firewall"))
    product_rule_verified = listener_firewall.get("product_rule_verified") is True
    allowed_on_active_profile = listener_firewall.get("allowed_on_active_profile") is True
    issue_codes: list[str] = []
    if not allowed_on_active_profile:
        issue_codes.append(
            "hostess.issue.connectivity_probe.no_udp_listener_firewall_allow_rule"
            if normalize_firewall_protocol(str(rule.get("protocol") or "UDP")) == "UDP"
            else "hostess.issue.connectivity_probe.no_tcp_listener_firewall_allow_rule"
        )
    if allowed_on_active_profile and not product_rule_verified:
        issue_codes.append(
            "hostess.issue.connectivity_probe.product_firewall_rule_not_verified"
        )
    return {
        "status": "pass" if product_rule_verified else "warn" if allowed_on_active_profile else "fail",
        "product_rule_verified": product_rule_verified,
        "allowed_on_active_profile": allowed_on_active_profile,
        "network_profile": network_profile,
        "listener_firewall": listener_firewall,
        "issue_codes": issue_codes,
    }


def live_same_wifi_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    run_timeout_func: Any,
    clock_func: Any,
    host_ipv4_func: Any | None = None,
    tcp_echo_func: Any | None = None,
) -> dict[str, Any]:
    selected_probe_id = str(getattr(args, "probe_id", "QCL-010") or "QCL-010")
    if selected_probe_id not in {"QCL-010", "QCL-011"}:
        raise SystemExit("live connectivity-probe currently supports --probe-id QCL-010 or QCL-011")
    if not getattr(args, "adb", None) or not getattr(args, "serial", None):
        raise SystemExit("connectivity-probe live mode requires --adb and --serial")

    observed_at = clock_func()
    ensure_probe_run_id(args, observed_at, selected_probe_id)
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

    mobile_hotspot: dict[str, Any] = {}
    if selected_probe_id == "QCL-011":
        mobile_hotspot = collect_windows_mobile_hotspot(run_captured_func)
        hotspot_status, hotspot_issue_codes = windows_mobile_hotspot_status(mobile_hotspot)
        checks.append(
            check_row(
                "host.windows_mobile_hotspot",
                hotspot_status,
                windows_mobile_hotspot_summary(mobile_hotspot),
                observed=mobile_hotspot,
                issue_codes=hotspot_issue_codes,
            )
        )
        for issue_code in hotspot_issue_codes:
            append_issue_once(
                issues,
                issue_code,
                "error" if hotspot_status in {"blocked", "fail"} else "warning",
                "Windows Mobile Hotspot is not in the expected operational state for QCL-011",
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

    listener = tcp_echo_listener_from_result(args, tcp_result)
    network_profile = collect_windows_network_profile(run_captured_func, listener=listener)
    network_status, network_issue_codes = windows_network_profile_status(network_profile)
    checks.append(
        check_row(
            "host.windows_network_firewall_profile",
            network_status if network_profile else "skipped",
            network_profile_summary(network_profile) if network_profile else "Windows network/firewall profile not available",
            observed=network_profile,
            issue_codes=network_issue_codes,
        )
    )
    for issue_code in network_issue_codes:
        append_issue_once(
            issues,
            issue_code,
            "warning",
            "active Windows network/firewall profile can block Quest-to-PC LAN listeners",
        )

    listener_firewall = object_value(network_profile.get("listener_firewall"))
    listener_status, listener_issue_codes = windows_firewall_listener_status(listener_firewall, tcp_result)
    checks.append(
        check_row(
            "host.windows_firewall_listener",
            listener_status,
            windows_firewall_listener_summary(listener_firewall),
            observed=listener_firewall,
            issue_codes=listener_issue_codes,
        )
    )
    for issue_code in listener_issue_codes:
        append_issue_once(
            issues,
            issue_code,
            "error" if listener_status == "fail" else "warning",
            "no Windows Firewall allow rule covers the Hostess TCP echo listener for the active profile",
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

    status = (
        live_qcl011_status(checks, host_ip, device.get("wifi_ipv4"))
        if selected_probe_id == "QCL-011"
        else live_qcl010_status(checks, host_ip, device.get("wifi_ipv4"))
    )
    if status == "warn":
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.partial_protocol_coverage",
                "warning",
                f"{selected_probe_id} topology was probed with ICMP/TCP only; WebSocket, UDP, and LSL probes remain separate",
            )
        )
    if status in {"fail", "blocked"}:
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.pc_hotspot_reachability_not_proven"
                if selected_probe_id == "QCL-011"
                else "hostess.issue.connectivity_probe.same_wifi_reachability_not_proven",
                "error",
                f"{selected_probe_id} reachability was not proven by the available checks",
            )
        )

    report = base_report(args, observed_at=observed_at)
    topology = topology_for_probe(selected_probe_id)
    transport_route = "pc_hotspot_lan_probe" if selected_probe_id == "QCL-011" else "same_wifi_lan_probe"
    toolchain_profile = (
        "hostessctl.connectivity_probe.qcl011"
        if selected_probe_id == "QCL-011"
        else "hostessctl.connectivity_probe"
    )
    report.update(
        {
            "status": status,
            "classification": "baseline_candidate",
            "topology": topology,
            "transport": {
                "family": "icmp_tcp",
                "route": transport_route,
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
                "firewall_listener": listener_firewall,
                "mobile_hotspot": mobile_hotspot,
                "adb_provider": str(getattr(args, "adb", "")),
                "toolchain_profile": toolchain_profile,
            },
            "checks": checks,
            "measurements": measurements_from_checks(tcp_result),
            "issues": issues,
            "promotion": {
                "allowed": False,
                "target": "quest.device_link topology descriptor",
                "reason": f"initial {selected_probe_id} probe; WebSocket, UDP, LSL, and firewall classification remain separate",
            },
        }
    )
    return report


def live_udp_freshness_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    run_timeout_func: Any,
    clock_func: Any,
    host_ipv4_func: Any | None = None,
    udp_freshness_func: Any | None = None,
) -> dict[str, Any]:
    if getattr(args, "probe_id", "QCL-080") != "QCL-080":
        raise SystemExit("live UDP freshness currently supports --probe-id QCL-080")
    if not getattr(args, "adb", None) or not getattr(args, "serial", None):
        raise SystemExit("connectivity-probe live QCL-080 mode requires --adb and --serial")

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
                "no host IPv4 address was available for the UDP freshness probe",
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

    udp_result: dict[str, Any] | None = None
    if host_ip and not getattr(args, "skip_udp_freshness", False):
        udp_runner = udp_freshness_func or device_to_host_udp_freshness
        udp_result = udp_runner(args, host_ip, run_timeout_func)
        checks.append(udp_result)
        runtime_udp_sender = runtime_qcl080_udp_sender_check_from_result(udp_result)
        if runtime_udp_sender is not None:
            checks.append(runtime_udp_sender)
    else:
        checks.append(check_row("protocol.udp_freshness", "skipped", "UDP freshness skipped or missing host IP"))

    listener = udp_listener_from_result(args, udp_result)
    network_profile = collect_windows_network_profile(run_captured_func, listener=listener)
    network_status, network_issue_codes = windows_network_profile_status(network_profile)
    checks.append(
        check_row(
            "host.windows_network_firewall_profile",
            network_status if network_profile else "skipped",
            network_profile_summary(network_profile) if network_profile else "Windows network/firewall profile not available",
            observed=network_profile,
            issue_codes=network_issue_codes,
        )
    )
    for issue_code in network_issue_codes:
        append_issue_once(
            issues,
            issue_code,
            "warning",
            "active Windows network/firewall profile can block Quest-to-PC LAN listeners",
        )

    listener_firewall = object_value(network_profile.get("listener_firewall"))
    listener_status, listener_issue_codes = windows_firewall_listener_status(listener_firewall, udp_result)
    checks.append(
        check_row(
            "host.windows_firewall_listener",
            listener_status,
            windows_firewall_listener_summary(listener_firewall),
            observed=listener_firewall,
            issue_codes=listener_issue_codes,
        )
    )
    for issue_code in listener_issue_codes:
        append_issue_once(
            issues,
            issue_code,
            "error" if listener_status == "fail" else "warning",
            "no Windows Firewall allow rule covers the Hostess UDP freshness listener for the active profile",
        )

    status = live_qcl080_status(checks, host_ip, device.get("wifi_ipv4"))
    if status in {"fail", "blocked"}:
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.udp_freshness_not_proven",
            "error",
            "UDP freshness was not proven by the available checks",
        )
    if check_status(checks, "protocol.udp_freshness") == "warn":
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.udp_freshness_degraded",
            "warning",
            "UDP packets arrived, but loss or jitter exceeded the configured pass threshold",
        )

    report = base_report(args, observed_at=observed_at)
    endpoint_source = udp_endpoint_source(udp_result)
    app_owned_sender = endpoint_source == "app_owned_runtime_udp_sender"
    runtime_sender_status = check_status(checks, "runtime.qcl080_udp_sender")
    promotion_allowed = (
        check_status(checks, "protocol.udp_freshness") in {"pass", "warn"}
        and (not app_owned_sender or runtime_sender_status == "pass")
    )
    report.update(
        {
            "status": status,
            "classification": "protocol_fit_candidate",
            "topology": topology_for_args(args, "QCL-080"),
            "transport": {
                "family": "udp",
                "route": "qcl080_udp_freshness",
                "local_endpoint": f"{host_ip or 'unknown'}:{listener.get('port', 'unknown')}",
                "remote_endpoint": str(device.get("wifi_ipv4") or "unknown"),
                "protocol_role": "freshness_probe",
                "payload_class": (
                    "low_rate_app_owned_diagnostic_datagram"
                    if app_owned_sender
                    else "low_rate_diagnostic_datagram"
                ),
                "endpoint_source": endpoint_source,
            },
            "device": device,
            "host": {
                "os": "windows",
                "selected_ipv4": host_ip,
                "ipv4_candidates": host_candidates,
                "firewall_profile": network_profile_summary(network_profile) if network_profile else "not_checked",
                "firewall_listener": listener_firewall,
                "adb_provider": str(getattr(args, "adb", "")),
                "toolchain_profile": "hostessctl.connectivity_probe.qcl080",
            },
            "checks": checks,
            "measurements": measurements_from_udp_check(udp_result),
            "issues": issues,
            "promotion": {
                "allowed": promotion_allowed,
                "target": "quest.device_link UDP stream capability descriptor",
                "reason": (
                    "QCL-080 proves app-owned Makepad runtime UDP datagrams over Wi-Fi"
                    if promotion_allowed and app_owned_sender
                    else "QCL-080 proves diagnostic UDP datagrams over Wi-Fi; app-owned runtime sender remains separate evidence"
                ),
            },
        }
    )
    return report


def live_lsl_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    run_timeout_func: Any,
    clock_func: Any,
    host_ipv4_func: Any | None = None,
    lsl_probe_func: Any | None = None,
) -> dict[str, Any]:
    if getattr(args, "probe_id", "QCL-081") != "QCL-081":
        raise SystemExit("live LSL currently supports --probe-id QCL-081")

    observed_at = clock_func()
    ensure_probe_run_id(args, observed_at, "QCL-081")
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    device: dict[str, Any] = {
        "serial_redacted": True,
        "foreground_package": "not_checked",
        "adb_state": "not_provided",
        "wifi_interface": str(getattr(args, "wifi_interface", "wlan0") or "wlan0"),
        "wifi_ipv4": "",
        "wifi_prefix_length": None,
    }
    host_candidates: list[dict[str, Any]] = []
    host_ip = str(getattr(args, "host_ip", "") or "").strip()

    if getattr(args, "adb", None) and getattr(args, "serial", None):
        device = collect_device_identity(args, run_captured_func, checks, issues)
        host_candidates = (
            host_ipv4_func()
            if host_ipv4_func is not None
            else collect_host_ipv4_candidates(run_captured_func)
        )
        host_ip = host_ip or choose_host_ip(
            host_candidates,
            device.get("wifi_ipv4"),
            device.get("wifi_prefix_length"),
        )
        checks.append(
            check_row(
                "host.ipv4_candidate",
                "pass" if host_ip else "blocked",
                f"selected={host_ip or 'none'}",
                observed={"selected_ip": host_ip, "candidates": host_candidates},
                issue_codes=[] if host_ip else ["hostess.issue.connectivity_probe.host_ip_missing"],
            )
        )
        checks.append(same_subnet_check(host_ip, device.get("wifi_ipv4"), device.get("wifi_prefix_length")))
    else:
        checks.append(
            check_row(
                "device.adb_state",
                "skipped",
                "ADB serial not provided; QCL-081 will not prove Quest topology",
            )
        )

    source = str(getattr(args, "lsl_source", "host-loopback") or "host-loopback")
    if source == "quest-runtime" and lsl_probe_func is None:
        lsl_result = lsl_quest_runtime_preflight(args, run_captured_func)
    elif source == "manifold-lsl-broker" and lsl_probe_func is None:
        lsl_result = lsl_manifold_broker_probe(args, run_captured_func)
    else:
        lsl_probe = lsl_probe_func or lsl_discovery_sample_continuity
        lsl_result = lsl_probe(args)
    checks.extend(lsl_checks_from_probe(lsl_result))
    for issue_code in lsl_result.get("issue_codes", []):
        append_issue_once(
            issues,
            str(issue_code),
            "error" if lsl_result.get("status") in {"fail", "blocked"} else "warning",
            "LSL discovery or sample continuity did not satisfy the requested probe",
        )

    status = live_qcl081_status(checks, source=source, device_ip=device.get("wifi_ipv4"))
    if status == "warn" and source == "host-loopback":
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.lsl_host_loopback_not_quest_topology",
            "warning",
            "host-local LSL loopback proves the Python/LSL stack, not Quest-to-PC Wi-Fi discovery",
        )
    if status in {"fail", "blocked"}:
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.lsl_continuity_not_proven",
            "error",
            "LSL discovery and sample continuity were not proven",
        )

    lsl_route_evidence = object_value(lsl_result.get("bridge_route_evidence"))
    lsl_broker_owned = (
        source == "manifold-lsl-broker"
        and str(lsl_result.get("evidence_tier") or "") == "broker_owned"
        and str(lsl_result.get("authority_owner") or "") == "rusty.manifold.transport"
        and str(lsl_route_evidence.get("status") or "") == "pass"
    )
    promotion_allowed = status == "pass" and (
        source == "quest-runtime" or lsl_broker_owned
    )

    report = base_report(args, observed_at=observed_at)
    report.update(
        {
            "status": status,
            "classification": "protocol_fit_candidate",
            "topology": {
                "owner": "external_wifi" if device.get("wifi_ipv4") else "host_local",
                "network_provider": "router_or_existing_wifi" if device.get("wifi_ipv4") else "loopback",
                "endpoint_direction": "lsl_multicast_discovery_plus_tcp_samples",
                "requires_existing_wifi": bool(device.get("wifi_ipv4")),
                "requires_adb": bool(getattr(args, "adb", None) and getattr(args, "serial", None)),
                "requires_pairing": False,
                "requires_termux": False,
                "experimental": source != "host-loopback",
            },
            "transport": {
                "family": "lsl",
                "route": "qcl081_lsl_discovery_sample_continuity",
                "local_endpoint": host_ip or "host-loopback",
                "remote_endpoint": str(device.get("wifi_ipv4") or source),
                "protocol_role": "study_stream_probe",
                "payload_class": "lsl_float32_samples",
                "endpoint_source": source,
            },
            "device": device,
            "host": {
                "os": "windows",
                "selected_ipv4": host_ip,
                "ipv4_candidates": host_candidates,
                "adb_provider": str(getattr(args, "adb", "")),
                "toolchain_profile": "hostessctl.connectivity_probe.qcl081",
            },
            "checks": checks,
            "measurements": measurements_from_lsl_probe(lsl_result),
            "issues": issues,
            "promotion": {
                "allowed": promotion_allowed,
                "target": "quest.device_link LSL stream capability descriptor",
                "reason": (
                    "QCL-081 proves Quest-runtime LSL discovery and sample continuity"
                    if promotion_allowed and source == "quest-runtime"
                    else "QCL-081 proves Manifold-owned LSL producer/sample continuity"
                    if promotion_allowed and source == "manifold-lsl-broker"
                    else "QCL-081 host loopback is a dependency/protocol check; Quest-owned LSL producer remains separate evidence"
                    if source == "host-loopback"
                    else "QCL-081 did not prove a Quest-owned LSL producer; Quest-side liblsl/pylsl runtime remains the blocking dependency"
                ),
            },
        }
    )
    report["lsl_payload_probe"] = lsl_result
    return report


def live_osc_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    clock_func: Any,
    host_ipv4_func: Any | None = None,
    osc_probe_func: Any | None = None,
) -> dict[str, Any]:
    if getattr(args, "probe_id", "QCL-083") != "QCL-083":
        raise SystemExit("live OSC currently supports --probe-id QCL-083")

    observed_at = clock_func()
    ensure_probe_run_id(args, observed_at, "QCL-083")
    checks, issues, device, host_candidates, host_ip = protocol_topology_checks(
        args,
        run_captured_func=run_captured_func,
        host_ipv4_func=host_ipv4_func,
    )
    source = str(getattr(args, "osc_source", "host-loopback") or "host-loopback")
    if source == "quest-runtime" and osc_probe_func is None:
        osc_result = run_qcl083_android_osc_probe(
            args,
            run_captured_func,
            device=device,
        )
    else:
        osc_probe = osc_probe_func or osc_loopback_probe
        osc_result = osc_probe(args)
    checks.extend(osc_checks_from_probe(osc_result))
    for issue_code in osc_result.get("issue_codes", []):
        append_issue_once(
            issues,
            str(issue_code),
            "error" if osc_result.get("status") in {"fail", "blocked"} else "warning",
            "OSC message exchange did not satisfy the requested probe",
        )

    status = live_qcl083_status(checks, source=source, device_ip=device.get("wifi_ipv4"))
    if status == "warn" and source == "host-loopback":
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.osc_host_loopback_not_quest_topology",
            "warning",
            "host-local OSC loopback proves packet parsing and UDP loopback only, not Quest-to-PC topology",
        )
    if status in {"fail", "blocked"}:
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.osc_exchange_not_proven",
            "error",
            "OSC packet exchange was not proven",
        )

    promotion_allowed = status == "pass" and source != "host-loopback"
    report = base_report(args, observed_at=observed_at)
    report.update(
        {
            "status": status,
            "classification": "protocol_fit_candidate",
            "topology": protocol_topology_for_report(
                device=device,
                source=source,
                host_ip=host_ip,
                endpoint_direction="osc_udp_control_telemetry",
            ),
            "transport": {
                "family": "osc",
                "route": "qcl083_osc_udp_payload_exchange",
                "local_endpoint": host_ip or "host-loopback",
                "remote_endpoint": str(device.get("wifi_ipv4") or source),
                "protocol_role": "low_rate_control_telemetry_probe",
                "payload_class": "osc_bounded_messages",
                "endpoint_source": source,
            },
            "device": device,
            "host": {
                "os": "windows",
                "selected_ipv4": host_ip,
                "ipv4_candidates": host_candidates,
                "adb_provider": str(getattr(args, "adb", "")),
                "toolchain_profile": "hostessctl.connectivity_probe.qcl083",
            },
            "checks": checks,
            "measurements": measurements_from_osc_probe(osc_result),
            "issues": issues,
            "promotion": {
                "allowed": promotion_allowed,
                "target": "quest.device_link OSC control/telemetry capability descriptor",
                "reason": (
                    "QCL-083 proves Quest/runtime-owned OSC payload exchange"
                    if promotion_allowed
                    else "QCL-083 host loopback is a dependency/protocol check; Quest-owned OSC sender/receiver remains separate evidence"
                ),
            },
        }
    )
    report["osc_payload_probe"] = osc_result
    return report


def live_zeromq_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    clock_func: Any,
    host_ipv4_func: Any | None = None,
    zeromq_probe_func: Any | None = None,
) -> dict[str, Any]:
    if getattr(args, "probe_id", "QCL-084") != "QCL-084":
        raise SystemExit("live ZeroMQ currently supports --probe-id QCL-084")

    observed_at = clock_func()
    ensure_probe_run_id(args, observed_at, "QCL-084")
    checks, issues, device, host_candidates, host_ip = protocol_topology_checks(
        args,
        run_captured_func=run_captured_func,
        host_ipv4_func=host_ipv4_func,
    )
    source = str(getattr(args, "zeromq_source", "host-loopback") or "host-loopback")
    if source == "quest-runtime" and zeromq_probe_func is None:
        zeromq_result = run_qcl084_android_zeromq_probe(
            args,
            run_captured_func,
            device=device,
        )
    else:
        zeromq_probe = zeromq_probe_func or zeromq_loopback_probe
        zeromq_result = zeromq_probe(args)
    checks.extend(zeromq_checks_from_probe(zeromq_result))
    for issue_code in zeromq_result.get("issue_codes", []):
        append_issue_once(
            issues,
            str(issue_code),
            "error" if zeromq_result.get("status") in {"fail", "blocked"} else "warning",
            "ZeroMQ exchange did not satisfy the requested probe",
        )

    status = live_qcl084_status(checks, source=source, device_ip=device.get("wifi_ipv4"))
    if status == "warn" and source in {"host-loopback", "manifold-zmq-loopback", "rusty-xr-zmq-loopback"}:
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.zeromq_host_loopback_not_quest_topology",
            "warning",
            "host-local ZeroMQ loopback proves the adapter dependency only, not Quest-to-PC topology or a Quest-owned runtime route",
        )
    if status in {"fail", "blocked"}:
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.zeromq_exchange_not_proven",
            "error",
            "ZeroMQ message exchange was not proven",
        )

    promotion_allowed = status == "pass" and source in {"native-rust-broker", "quest-runtime"}
    report = base_report(args, observed_at=observed_at)
    report.update(
        {
            "status": status,
            "classification": "protocol_fit_candidate",
            "topology": protocol_topology_for_report(
                device=device,
                source=source,
                host_ip=host_ip,
                endpoint_direction="zeromq_socket_exchange",
            ),
            "transport": {
                "family": "zeromq",
                "route": "qcl084_zeromq_socket_exchange",
                "local_endpoint": host_ip or "host-loopback",
                "remote_endpoint": str(device.get("wifi_ipv4") or source),
                "protocol_role": "native_rust_transport_probe",
                "payload_class": "bounded_zeromq_messages",
                "endpoint_source": source,
            },
            "device": device,
            "host": {
                "os": "windows",
                "selected_ipv4": host_ip,
                "ipv4_candidates": host_candidates,
                "adb_provider": str(getattr(args, "adb", "")),
                "toolchain_profile": "hostessctl.connectivity_probe.qcl084",
            },
            "checks": checks,
            "measurements": measurements_from_zeromq_probe(zeromq_result),
            "issues": issues,
            "promotion": {
                "allowed": promotion_allowed,
                "target": "quest.device_link ZeroMQ/native Rust transport capability descriptor",
                "reason": (
                    "QCL-084 proves native Rust broker/runtime ZeroMQ exchange"
                    if promotion_allowed
                    else "QCL-084 does not yet prove native Rust broker/runtime ZeroMQ; Manifold adapter dependency or Quest-owned route remains separate evidence"
                ),
            },
        }
    )
    report["zeromq_payload_probe"] = zeromq_result
    return report





def protocol_topology_checks(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    host_ipv4_func: Any | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    device: dict[str, Any] = {
        "serial_redacted": True,
        "foreground_package": "not_checked",
        "adb_state": "not_provided",
        "wifi_interface": str(getattr(args, "wifi_interface", "wlan0") or "wlan0"),
        "wifi_ipv4": "",
        "wifi_prefix_length": None,
    }
    host_candidates: list[dict[str, Any]] = []
    host_ip = str(getattr(args, "host_ip", "") or "").strip()
    if getattr(args, "adb", None) and getattr(args, "serial", None):
        device = collect_device_identity(args, run_captured_func, checks, issues)
        host_candidates = (
            host_ipv4_func()
            if host_ipv4_func is not None
            else collect_host_ipv4_candidates(run_captured_func)
        )
        host_ip = host_ip or choose_host_ip(
            host_candidates,
            device.get("wifi_ipv4"),
            device.get("wifi_prefix_length"),
        )
        checks.append(
            check_row(
                "host.ipv4_candidate",
                "pass" if host_ip else "blocked",
                f"selected={host_ip or 'none'}",
                observed={"selected_ip": host_ip, "candidates": host_candidates},
                issue_codes=[] if host_ip else ["hostess.issue.connectivity_probe.host_ip_missing"],
            )
        )
        checks.append(same_subnet_check(host_ip, device.get("wifi_ipv4"), device.get("wifi_prefix_length")))
    else:
        checks.append(
            check_row(
                "device.adb_state",
                "skipped",
                "ADB serial not provided; protocol probe will not prove Quest topology",
            )
        )
    return checks, issues, device, host_candidates, host_ip


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


def live_bluetooth_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    run_timeout_func: Any | None = None,
    clock_func: Any,
) -> dict[str, Any]:
    selected_probe_id = str(getattr(args, "probe_id", "QCL-050") or "QCL-050")
    if selected_probe_id not in {"QCL-050", "QCL-051"}:
        raise SystemExit("live Bluetooth readiness currently supports --probe-id QCL-050 or QCL-051")
    if not getattr(args, "adb", None) or not getattr(args, "serial", None):
        raise SystemExit("connectivity-probe live Bluetooth mode requires --adb and --serial")

    observed_at = clock_func()
    ensure_probe_run_id(args, observed_at, selected_probe_id)
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    host_bluetooth = collect_windows_bluetooth_status(run_captured_func)
    host_adapter_status, host_adapter_issue_codes = windows_bluetooth_adapter_status(host_bluetooth)
    checks.append(
        check_row(
            "host.bluetooth_adapter",
            host_adapter_status,
            windows_bluetooth_adapter_summary(host_bluetooth),
            observed=host_bluetooth,
            issue_codes=host_adapter_issue_codes,
        )
    )
    host_service_status, host_service_issue_codes = windows_bluetooth_service_status(host_bluetooth)
    checks.append(
        check_row(
            "host.bluetooth_service",
            host_service_status,
            windows_bluetooth_service_summary(host_bluetooth),
            observed=host_bluetooth,
            issue_codes=host_service_issue_codes,
        )
    )
    for issue_code in host_adapter_issue_codes + host_service_issue_codes:
        append_issue_once(
            issues,
            issue_code,
            "error",
            "Windows Bluetooth adapter or service is not ready for the Bluetooth probe",
        )

    device_bluetooth = collect_quest_bluetooth_status(args, run_captured_func)
    device_status, device_issue_codes = quest_bluetooth_adapter_status(device_bluetooth)
    checks.append(
        check_row(
            "device.bluetooth_adapter",
            device_status,
            quest_bluetooth_adapter_summary(device_bluetooth),
            observed=device_bluetooth,
            issue_codes=device_issue_codes,
        )
    )
    for issue_code in device_issue_codes:
        append_issue_once(
            issues,
            issue_code,
            "error",
            "Quest Bluetooth adapter is not ready for the Bluetooth probe",
        )

    payload_result: dict[str, Any] | None = None
    bluetooth_payload_source = str(getattr(args, "bluetooth_payload_source", "passive") or "passive")
    if bluetooth_payload_source == "android-ble-gatt":
        if selected_probe_id != "QCL-051":
            raise SystemExit("--bluetooth-payload-source android-ble-gatt currently supports --probe-id QCL-051")
        payload_result = run_qcl051_android_ble_gatt_probe(args, run_captured_func, run_timeout_func)
        checks.extend(qcl051_ble_gatt_payload_checks(payload_result))
    elif bluetooth_payload_source == "android-rfcomm":
        if selected_probe_id != "QCL-050":
            raise SystemExit("--bluetooth-payload-source android-rfcomm currently supports --probe-id QCL-050")
        payload_result = run_qcl050_android_rfcomm_probe(args, run_captured_func, run_timeout_func)
        checks.extend(qcl050_rfcomm_payload_checks(payload_result))
    else:
        checks.append(
            check_row(
                "bluetooth.pairing_bond_state",
                "skipped",
                "manual pairing/bond rehearsal has not been run in this passive readiness probe",
                issue_codes=["hostess.issue.connectivity_probe.bluetooth_pairing_not_tested"],
            )
        )
        checks.append(bluetooth_protocol_check(selected_probe_id, status="skipped"))
        checks.append(
            check_row(
                "protocol.bluetooth_payload_exchange",
                "skipped",
                "no RFCOMM socket or BLE/GATT characteristic payload exchange has been attempted yet",
                issue_codes=["hostess.issue.connectivity_probe.bluetooth_payload_not_tested"],
            )
        )

    for check in checks:
        for issue_code in check.get("issue_codes", []) or []:
            if issue_code.startswith("hostess.issue.connectivity_probe.ble_gatt") or issue_code.startswith(
                "hostess.issue.connectivity_probe.rfcomm"
            ):
                append_issue_once(
                    issues,
                    issue_code,
                    "error" if check.get("status") in {"fail", "blocked"} else "warning",
                    str(check.get("evidence") or issue_code),
                )

    status = live_bluetooth_status(checks)
    if status == "warn":
        issue_code = (
            "hostess.issue.connectivity_probe.bluetooth_reconnect_not_tested"
            if payload_result and payload_result.get("status") == "pass"
            else "hostess.issue.connectivity_probe.bluetooth_passive_readiness_only"
        )
        append_issue_once(
            issues,
            issue_code,
            "warning",
            (
                f"{selected_probe_id} proved BLE/GATT payload exchange, but reconnect/manual pairing rehearsal remains separate"
                if payload_result and payload_result.get("status") == "pass" and selected_probe_id == "QCL-051"
                else f"{selected_probe_id} proved RFCOMM payload exchange, but reconnect rehearsal remains separate"
                if payload_result and payload_result.get("status") == "pass"
                else f"{selected_probe_id} proved passive adapter readiness only; pairing and payload exchange remain separate"
            ),
        )
    if status in {"fail", "blocked"}:
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.bluetooth_readiness_not_proven",
            "error",
            f"{selected_probe_id} Bluetooth readiness was not proven by the available checks",
        )

    promotion_allowed = (
        selected_probe_id == "QCL-051"
        and status == "pass"
        and bool(payload_result)
        and payload_result.get("status") == "pass"
    )
    promotion_reason = (
        "BLE/GATT app-owned payload exchange, cleanup, and reconnect passed"
        if promotion_allowed
        else (
            "BLE/GATT payload exchange proved, but reconnect and manual pairing/prompt behavior remain unproven"
            if payload_result and payload_result.get("status") == "pass" and selected_probe_id == "QCL-051"
            else "RFCOMM payload exchange proved, but reconnect rehearsal remains unproven"
            if payload_result and payload_result.get("status") == "pass"
            else "passive Bluetooth readiness only; pairing, service discovery, payload exchange, reconnect, and cleanup remain unproven"
        )
    )

    report = base_report(args, observed_at=observed_at)
    report.update(
        {
            "status": status,
            "classification": "discovery_control_candidate",
            "topology": topology_for_bluetooth_probe(selected_probe_id),
            "transport": bluetooth_transport_for_probe(selected_probe_id),
            "device": {
                "serial_redacted": False,
                "serial": str(getattr(args, "serial", "")),
                "model": device_bluetooth.get("name") or "unknown",
                "bluetooth": device_bluetooth,
                "adb_provider": str(getattr(args, "adb", "")),
            },
            "host": {
                "os": "windows",
                "bluetooth": host_bluetooth,
                "toolchain_profile": f"hostessctl.connectivity_probe.{selected_probe_id.lower()}",
            },
            "checks": checks,
            "measurements": bluetooth_measurements(payload_result),
            "issues": issues,
            "promotion": {
                "allowed": promotion_allowed,
                "target": "quest.device_link bluetooth discovery/control descriptor",
                "reason": promotion_reason,
            },
        }
    )
    if payload_result is not None:
        report["bluetooth_payload_probe"] = payload_result
    return report


def fixture_report(args: argparse.Namespace, *, observed_at: datetime) -> dict[str, Any]:
    profile = str(getattr(args, "fixture_profile", "") or "")
    probe_id = str(getattr(args, "probe_id", "") or "QCL-010")
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


def collect_windows_mobile_hotspot(run_captured_func: Any) -> dict[str, Any]:
    command = [
        powershell_executable(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "try { "
            "[Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType = WindowsRuntime] | Out-Null; "
            "[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking.NetworkOperators, ContentType = WindowsRuntime] | Out-Null; "
            "$profile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile(); "
            "if ($null -eq $profile) { "
            "  [pscustomobject]@{ available=$false; state='NoInternetProfile'; source_profile=''; client_count=0; max_client_count=0; ssid=''; passphrase_set=$false } | ConvertTo-Json -Compress; exit 0 "
            "} "
            "$manager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($profile); "
            "$config = $manager.GetCurrentAccessPointConfiguration(); "
            "[pscustomobject]@{ "
            "  available=$true; "
            "  source_profile=$profile.ProfileName; "
            "  state=$manager.TetheringOperationalState.ToString(); "
            "  client_count=$manager.ClientCount; "
            "  max_client_count=$manager.MaxClientCount; "
            "  ssid=$config.Ssid; "
            "  passphrase_set=(-not [string]::IsNullOrWhiteSpace($config.Passphrase)); "
            "  band=$config.Band.ToString() "
            "} | ConvertTo-Json -Compress "
            "} catch { "
            "  [pscustomobject]@{ available=$false; state='Error'; error=$_.Exception.Message; error_type=$_.Exception.GetType().FullName } | ConvertTo-Json -Compress "
            "}"
        ),
    ]
    result = run_captured_func(command, allow_failure=True)
    if result.returncode != 0:
        return {
            "available": False,
            "state": "CommandFailed",
            "error": result.stderr.strip(),
            "returncode": result.returncode,
        }
    stdout = strip_powershell_clixml_noise(result.stdout)
    try:
        parsed = json.loads(stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"available": False, "state": "ParseError", "raw_stdout": stdout}
    return parsed if isinstance(parsed, dict) else {"available": False, "state": "UnexpectedShape"}
















def run_qcl083_android_osc_probe(
    args: argparse.Namespace,
    run_captured_func: Any,
    *,
    device: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = str(getattr(args, "run_id", "") or "qcl083-android-osc")
    package_name = str(getattr(args, "hostess_android_package", "") or ANDROID_PACKAGE)
    message_count = max(1, int(getattr(args, "osc_message_count", 16) or 16))
    timeout_seconds = max(3.0, float(getattr(args, "osc_timeout_seconds", 5.0) or 5.0))
    osc_port = int(getattr(args, "osc_port", 0) or 0) or DEFAULT_QCL083_OSC_PORT
    osc_address = str(getattr(args, "osc_address", "/rusty/qcl083") or "/rusty/qcl083")
    device_ip = str((device or {}).get("wifi_ipv4") or "").strip()
    remote_path = qcl083_remote_evidence_path(package_name)

    if not getattr(args, "adb", None) or not getattr(args, "serial", None):
        return {
            "status": "blocked",
            "source": "quest-runtime",
            "endpoint_source": "app_owned_android_osc_server",
            "address": osc_address,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "loss_percent": 100.0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.osc_android_adb_missing"],
            "notes": "QCL-083 Quest runtime OSC probe requires --adb and --serial",
        }
    if not device_ip:
        return {
            "status": "blocked",
            "source": "quest-runtime",
            "endpoint_source": "app_owned_android_osc_server",
            "address": osc_address,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "loss_percent": 100.0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.device_wifi_ip_missing"],
            "notes": "QCL-083 Quest runtime OSC probe requires a Quest Wi-Fi IPv4 address",
        }

    launch_precondition = collect_android_activity_launch_precondition(args, run_captured_func)
    if launch_precondition.get("blocked"):
        return {
            "status": "blocked",
            "source": "quest-runtime",
            "endpoint_source": "app_owned_android_osc_server",
            "address": osc_address,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "loss_percent": 100.0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.osc_runtime_not_launchable"],
            "android": {
                "launch_precondition": launch_precondition,
                "remote_evidence": remote_path,
                "evidence": {},
                "evidence_available": False,
            },
            "notes": "QCL-083 Android OSC activity was blocked by the current foreground/runtime state",
        }

    run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "rm", "-f", remote_path],
        allow_failure=True,
    )
    run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "am", "force-stop", package_name],
        allow_failure=True,
    )
    android_start = run_captured_func(
        [
            str(getattr(args, "adb")),
            "-s",
            str(getattr(args, "serial")),
            "shell",
            "am",
            "start",
            "-a",
            ANDROID_QCL083_OSC_ACTION,
            "-n",
            f"{package_name}/.MainActivity",
            "--es",
            "run_id",
            run_id,
            "--ei",
            "message_count",
            str(message_count),
            "--el",
            "timeout_ms",
            str(int(timeout_seconds * 1000)),
            "--ei",
            "listen_port",
            str(osc_port),
            "--es",
            "osc_address",
            osc_address,
        ],
        allow_failure=True,
    )
    time.sleep(0.75)
    host_probe = osc_quest_runtime_payload_probe(
        args,
        device_ip=device_ip,
        port=osc_port,
        address=osc_address,
        message_count=message_count,
        timeout_seconds=timeout_seconds,
        run_id=run_id,
    )
    android_report = read_android_json_with_retry(
        args,
        remote_path,
        run_captured_func,
        timeout_seconds=timeout_seconds + 2.0,
    )

    host_status = str(host_probe.get("status") or "")
    android_status = str(android_report.get("status") or "")
    if host_status == "blocked" or android_status == "blocked":
        status = "blocked"
    elif host_status == "pass" and android_status == "pass":
        status = "pass"
    elif host_probe.get("messages_acknowledged", 0) or android_report.get("messages_received", 0):
        status = "warn"
    else:
        status = "fail"

    issue_codes: list[str] = []
    for source_report in [host_probe, android_report]:
        for issue_code in source_report.get("issue_codes", []) or []:
            if issue_code not in issue_codes:
                issue_codes.append(str(issue_code))
    if not android_report:
        issue_codes.append("hostess.issue.connectivity_probe.osc_android_evidence_missing")
        if status == "pass":
            status = "warn"

    result = dict(host_probe)
    result.update(
        {
            "status": status,
            "source": "quest-runtime",
            "endpoint_source": "app_owned_android_osc_server",
            "address": osc_address,
            "device_endpoint": f"{device_ip}:{osc_port}",
            "issue_codes": issue_codes,
            "android": {
                "start": completed_observed(android_start),
                "remote_evidence": remote_path,
                "evidence": android_report,
                "evidence_available": bool(android_report),
            },
            "windows": {
                "evidence": host_probe,
                "evidence_available": bool(host_probe),
            },
            "notes": "Quest app-owned OSC UDP server with host timestamped round-trip probe",
        }
    )
    return result


def osc_quest_runtime_payload_probe(
    args: argparse.Namespace,
    *,
    device_ip: str,
    port: int,
    address: str,
    message_count: int,
    timeout_seconds: float,
    run_id: str,
) -> dict[str, Any]:
    max_loss_percent = max(0.0, float(getattr(args, "osc_max_loss_percent", 0.0) or 0.0))
    received_sequences: list[int] = []
    acknowledged_sequences: list[int] = []
    rtts: list[float] = []
    quest_processing: list[float] = []
    clock_offsets: list[float] = []
    measurements: list[dict[str, Any]] = []
    issue_codes: list[str] = []

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
            client_socket.bind(("", 0))
            client_socket.settimeout(min(1.0, timeout_seconds))
            for sequence in range(message_count):
                host_send_ns = time.monotonic_ns()
                marker = json.dumps(
                    {
                        "run_id": run_id,
                        "sequence": sequence,
                        "host_send_monotonic_ns": host_send_ns,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
                client_socket.sendto(build_osc_message(address, sequence, marker), (device_ip, port))
                try:
                    ack, _addr = client_socket.recvfrom(8192)
                except socket.timeout:
                    continue
                host_receive_ns = time.monotonic_ns()
                parsed_ack = parse_osc_message(ack)
                if parsed_ack.get("address") != "/rusty/qcl083/ack":
                    issue_codes.append("hostess.issue.connectivity_probe.osc_ack_address_mismatch")
                    continue
                if int(parsed_ack.get("sequence", -1)) != sequence:
                    issue_codes.append("hostess.issue.connectivity_probe.osc_ack_sequence_mismatch")
                    continue
                ack_marker = parse_json_string(str(parsed_ack.get("marker") or "{}"))
                quest_received_ns = int_value(ack_marker.get("quest_received_elapsed_ns"))
                quest_send_ns = int_value(ack_marker.get("quest_send_elapsed_ns"))
                rtt_ms = (host_receive_ns - host_send_ns) / 1_000_000.0
                processing_ms = None
                clock_offset_ms = None
                one_way_estimate_ms = None
                if quest_received_ns is not None and quest_send_ns is not None:
                    processing_ms = max(0.0, (quest_send_ns - quest_received_ns) / 1_000_000.0)
                    clock_offset_ms = (
                        (quest_received_ns - host_send_ns) + (quest_send_ns - host_receive_ns)
                    ) / 2_000_000.0
                    one_way_estimate_ms = max(0.0, (rtt_ms - processing_ms) / 2.0)
                    quest_processing.append(processing_ms)
                    clock_offsets.append(clock_offset_ms)
                received_sequences.append(sequence)
                acknowledged_sequences.append(sequence)
                rtts.append(rtt_ms)
                measurements.append(
                    {
                        "sequence": sequence,
                        "round_trip_ms": round(rtt_ms, 3),
                        "quest_processing_ms": round(processing_ms, 3) if processing_ms is not None else None,
                        "estimated_one_way_ms": (
                            round(one_way_estimate_ms, 3) if one_way_estimate_ms is not None else None
                        ),
                        "clock_offset_estimate_ms": (
                            round(clock_offset_ms, 3) if clock_offset_ms is not None else None
                        ),
                    }
                )
                time.sleep(0.005)
    except OSError as exc:
        return {
            "status": "blocked",
            "source": "quest-runtime",
            "address": address,
            "messages_requested": message_count,
            "messages_received": len(received_sequences),
            "messages_acknowledged": len(acknowledged_sequences),
            "loss_percent": 100.0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.osc_client_socket_failed"],
            "notes": str(exc),
        }

    acknowledged_count = len(acknowledged_sequences)
    loss_percent = round(((message_count - acknowledged_count) / message_count) * 100.0, 2)
    monotonic = acknowledged_sequences == list(range(acknowledged_count))
    if acknowledged_count == message_count and monotonic and loss_percent <= max_loss_percent:
        status = "pass"
    elif acknowledged_count > 0:
        status = "warn"
        issue_codes.append("hostess.issue.connectivity_probe.osc_exchange_degraded")
    else:
        status = "fail"
        issue_codes.append("hostess.issue.connectivity_probe.osc_exchange_failed")

    median_offset = median(clock_offsets)
    offset_jitter = [abs(value - median_offset) for value in clock_offsets] if median_offset is not None else []
    return {
        "status": status,
        "source": "quest-runtime",
        "address": address,
        "messages_requested": message_count,
        "messages_received": len(received_sequences),
        "messages_acknowledged": acknowledged_count,
        "loss_percent": loss_percent,
        "round_trip_ms_p95": round_float(percentile(rtts, 95)),
        "round_trip_ms_max": round_float(max(rtts) if rtts else None),
        "quest_processing_ms_p95": round_float(percentile(quest_processing, 95)),
        "estimated_one_way_ms_p95": round_float(percentile(
            [
                max(0.0, (measurement["round_trip_ms"] - (measurement["quest_processing_ms"] or 0.0)) / 2.0)
                for measurement in measurements
            ],
            95,
        )),
        "clock_offset_estimate_ms_median": round_float(median_offset),
        "clock_offset_jitter_ms_p95": round_float(percentile(offset_jitter, 95)),
        "monotonic_sequences": monotonic,
        "received_sequences": received_sequences[:50],
        "acknowledged_sequences": acknowledged_sequences[:50],
        "timing_samples": measurements[:50],
        "issue_codes": dedupe_issue_codes(issue_codes),
        "notes": "host-to-Quest OSC UDP payload exchange with NTP-style monotonic clock offset estimate",
    }


def run_qcl084_android_zeromq_probe(
    args: argparse.Namespace,
    run_captured_func: Any,
    *,
    device: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = str(getattr(args, "run_id", "") or "qcl084-android-zeromq")
    message_count = max(1, int(getattr(args, "zeromq_message_count", 16) or 16))
    timeout_seconds = max(3.0, float(getattr(args, "zeromq_timeout_seconds", 5.0) or 5.0))
    port = int(getattr(args, "zeromq_port", 0) or 0) or DEFAULT_QCL084_ZEROMQ_PORT
    device_ip = str((device or {}).get("wifi_ipv4") or "").strip()
    pattern = str(getattr(args, "zeromq_pattern", "req-rep") or "req-rep")
    if pattern != "req-rep":
        return zeromq_blocked_result(
            source="quest-runtime",
            pattern=pattern,
            message_count=message_count,
            issue_code="hostess.issue.connectivity_probe.zeromq_pattern_not_implemented",
            notes="QCL-084 Quest runtime probe currently supports REQ/REP for latency measurement",
        )
    if not getattr(args, "adb", None) or not getattr(args, "serial", None):
        return zeromq_blocked_result(
            source="quest-runtime",
            pattern=pattern,
            message_count=message_count,
            issue_code="hostess.issue.connectivity_probe.zeromq_android_adb_missing",
            notes="QCL-084 Quest runtime ZeroMQ probe requires --adb and --serial",
        )
    if not device_ip:
        return zeromq_blocked_result(
            source="quest-runtime",
            pattern=pattern,
            message_count=message_count,
            issue_code="hostess.issue.connectivity_probe.device_wifi_ip_missing",
            notes="QCL-084 Quest runtime ZeroMQ probe requires a Quest Wi-Fi IPv4 address",
        )

    host_binary = resolve_qcl084_probe_binary(args, target="android")
    client_binary = resolve_qcl084_probe_binary(args, target="windows")
    if host_binary is None or not host_binary.exists():
        return zeromq_blocked_result(
            source="quest-runtime",
            pattern=pattern,
            message_count=message_count,
            issue_code="hostess.issue.connectivity_probe.zeromq_android_binary_missing",
            notes="Android qcl084_req_rep_probe binary was not found; build rusty-manifold-zmq for aarch64-linux-android",
        )
    if client_binary is None or not client_binary.exists():
        return zeromq_blocked_result(
            source="quest-runtime",
            pattern=pattern,
            message_count=message_count,
            issue_code="hostess.issue.connectivity_probe.zeromq_client_binary_missing",
            notes="Windows qcl084_req_rep_probe binary was not found; build rusty-manifold-zmq example on the host",
        )

    device_binary = str(
        getattr(args, "zeromq_android_binary_device_path", "")
        or "/data/local/tmp/rusty-qcl084-req-rep-probe"
    )
    safe_run = sanitize_filename(run_id)
    remote_server_json = f"/data/local/tmp/{safe_run}.qcl084-server.json"
    remote_server_err = f"/data/local/tmp/{safe_run}.qcl084-server.err"
    endpoint_bind = f"tcp://0.0.0.0:{port}"
    endpoint_connect = f"tcp://{device_ip}:{port}"

    push = run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "push", str(host_binary), device_binary],
        allow_failure=True,
    )
    chmod = run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "chmod", "755", device_binary],
        allow_failure=True,
    )
    run_captured_func(
        [
            str(getattr(args, "adb")),
            "-s",
            str(getattr(args, "serial")),
            "shell",
            "rm",
            "-f",
            remote_server_json,
            remote_server_err,
        ],
        allow_failure=True,
    )
    launch_command = (
        f"nohup {shell_quote(device_binary)} server "
        f"--endpoint {shell_quote(endpoint_bind)} "
        f"--run-id {shell_quote(run_id)} "
        f"--message-count {message_count} "
        f"--timeout-ms {int(timeout_seconds * 1000)} "
        f"> {shell_quote(remote_server_json)} 2> {shell_quote(remote_server_err)} &"
    )
    server_start = run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", launch_command],
        allow_failure=True,
    )
    time.sleep(1.0)

    client_command = [
        str(client_binary),
        "client",
        "--endpoint",
        endpoint_connect,
        "--run-id",
        run_id,
        "--message-count",
        str(message_count),
        "--timeout-ms",
        str(int(timeout_seconds * 1000)),
        "--connect-settle-ms",
        "500",
    ]
    try:
        client_run = subprocess.run(
            client_command,
            cwd=str(client_binary.parent),
            text=True,
            capture_output=True,
            timeout=timeout_seconds + 10.0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        client_report = {}
        client_observed = {
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": True,
        }
    else:
        client_report = parse_probe_json_stdout(client_run.stdout)
        client_observed = completed_observed(client_run)

    server_report = read_android_json_with_retry(
        args,
        remote_server_json,
        run_captured_func,
        timeout_seconds=timeout_seconds + 2.0,
    )
    server_err = run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "cat", remote_server_err],
        allow_failure=True,
    )

    client_status = str(client_report.get("status") or "")
    server_status = str(server_report.get("status") or "")
    if push.returncode != 0 or chmod.returncode != 0:
        status = "blocked"
    elif client_status == "pass" and server_status == "pass":
        status = "pass"
    elif client_report.get("messages_acknowledged", 0) or server_report.get("messages_acknowledged", 0):
        status = "warn"
    else:
        status = "fail"

    issue_codes: list[str] = []
    for report in [client_report, server_report]:
        for issue_code in report.get("issue_codes", []) or []:
            if issue_code not in issue_codes:
                issue_codes.append(str(issue_code))
    if push.returncode != 0:
        issue_codes.append("hostess.issue.connectivity_probe.zeromq_android_binary_push_failed")
    if chmod.returncode != 0:
        issue_codes.append("hostess.issue.connectivity_probe.zeromq_android_binary_chmod_failed")
    if not client_report:
        issue_codes.append("hostess.issue.connectivity_probe.zeromq_client_report_missing")
    if not server_report:
        issue_codes.append("hostess.issue.connectivity_probe.zeromq_server_report_missing")

    return {
        "status": status,
        "source": "quest-runtime",
        "pattern": pattern,
        "endpoint": endpoint_connect,
        "device_endpoint": endpoint_bind,
        "messages_requested": message_count,
        "messages_received": client_report.get("messages_received", 0),
        "messages_acknowledged": client_report.get("messages_acknowledged", 0),
        "loss_percent": client_report.get("loss_percent", 100.0),
        "round_trip_ms_p95": client_report.get("round_trip_ms_p95"),
        "round_trip_ms_max": client_report.get("round_trip_ms_max"),
        "server_processing_ms_p95": client_report.get("server_processing_ms_p95"),
        "estimated_one_way_ms_p95": client_report.get("estimated_one_way_ms_p95"),
        "clock_offset_estimate_ms_median": client_report.get("clock_offset_estimate_ms_median"),
        "clock_offset_jitter_ms_p95": client_report.get("clock_offset_jitter_ms_p95"),
        "received_sequences": client_report.get("received_sequences", []),
        "acknowledged_sequences": client_report.get("acknowledged_sequences", []),
        "timing_samples": client_report.get("timing_samples", []),
        "issue_codes": dedupe_issue_codes(issue_codes),
        "notes": "Quest native Rust ZeroMQ REQ/REP server with Windows native Rust client",
        "android": {
            "push": completed_observed(push),
            "chmod": completed_observed(chmod),
            "start": completed_observed(server_start),
            "device_binary": device_binary,
            "server_stdout_path": remote_server_json,
            "server_stderr_path": remote_server_err,
            "server_stderr": trim_text(server_err.stdout, limit=800),
            "evidence": server_report,
            "evidence_available": bool(server_report),
        },
        "windows": {
            "client_command": redact_command_for_report(client_command),
            "run": client_observed,
            "evidence": client_report,
            "evidence_available": bool(client_report),
        },
    }


def zeromq_blocked_result(
    *,
    source: str,
    pattern: str,
    message_count: int,
    issue_code: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "source": source,
        "pattern": pattern,
        "messages_requested": message_count,
        "messages_received": 0,
        "messages_acknowledged": 0,
        "round_trip_ms_p95": None,
        "issue_codes": [issue_code],
        "notes": notes,
    }


def resolve_qcl084_probe_binary(args: argparse.Namespace, *, target: str) -> Path | None:
    if target == "android":
        explicit = str(getattr(args, "zeromq_android_binary_host_path", "") or "").strip()
        if explicit:
            return Path(explicit)
        root = resolve_manifold_root(args)
        if root is None:
            return None
        return root / "target" / "aarch64-linux-android" / "release" / "examples" / "qcl084_req_rep_probe"
    root = resolve_manifold_root(args)
    if root is None:
        return None
    candidates = [
        root / "target" / "debug" / "examples" / "qcl084_req_rep_probe.exe",
        root / "target" / "release" / "examples" / "qcl084_req_rep_probe.exe",
        root / "target" / "debug" / "examples" / "qcl084_req_rep_probe",
        root / "target" / "release" / "examples" / "qcl084_req_rep_probe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]




def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"












def qcl083_remote_evidence_path(package_name: str) -> str:
    if package_name == ANDROID_PACKAGE:
        return ANDROID_REMOTE_QCL083_OSC_EVIDENCE
    return f"/sdcard/Android/data/{package_name}/files/hostess-t/evidence/qcl083-osc/latest.json"
































def collect_windows_network_profile(run_captured_func: Any, *, listener: dict[str, Any] | None = None) -> dict[str, Any]:
    listener = listener or {}
    listener_program = normalize_firewall_program_path(str(listener.get("program") or ""))
    listener_port = int(listener.get("port") or 0)
    listener_bind_host = str(listener.get("bind_host") or "")
    listener_protocol = normalize_firewall_protocol(str(listener.get("protocol") or "TCP"))
    listener_rule_name = str(listener.get("rule_name") or default_firewall_rule_name(listener_port, listener_protocol))
    listener_remote_address = str(listener.get("remote_address") or "LocalSubnet")
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"$listenerProgram = {ps_string_literal(listener_program)}; "
            f"$listenerPort = {listener_port}; "
            f"$listenerBindHost = {ps_string_literal(listener_bind_host)}; "
            f"$listenerProtocol = {ps_string_literal(listener_protocol)}; "
            f"$listenerRuleName = {ps_string_literal(listener_rule_name)}; "
            f"$listenerRemoteAddress = {ps_string_literal(listener_remote_address)}; "
            "$listenerProtocolNumber = if ($listenerProtocol -eq 'UDP') { 17 } else { 6 }; "
            "function Convert-Profiles($mask) { "
            "  if ($mask -eq 2147483647) { return @('Domain','Private','Public') } "
            "  $names = @(); "
            "  if (($mask -band 1) -ne 0) { $names += 'Domain' } "
            "  if (($mask -band 2) -ne 0) { $names += 'Private' } "
            "  if (($mask -band 4) -ne 0) { $names += 'Public' } "
            "  if ($names.Count -eq 0) { $names += 'All' } "
            "  return $names "
            "} "
            "function Test-PortMatch($ports, $port) { "
            "  if ($port -le 0) { return $false } "
            "  $text = [string]$ports; "
            "  if ([string]::IsNullOrWhiteSpace($text) -or $text -eq '*' -or $text -eq 'Any') { return $true } "
            "  foreach ($part in $text -split ',') { "
            "    $part = $part.Trim(); "
            "    if ($part -eq [string]$port) { return $true } "
            "    if ($part -match '^(\\d+)-(\\d+)$') { "
            "      $left = [int]$Matches[1]; $right = [int]$Matches[2]; "
            "      if ($port -ge $left -and $port -le $right) { return $true } "
            "    } "
            "  } "
            "  return $false "
            "} "
            "function Test-RemoteAddressMatch($remoteAddresses, $expectedRemoteAddress) { "
            "  $expected = [string]$expectedRemoteAddress; "
            "  if ([string]::IsNullOrWhiteSpace($expected)) { return $true } "
            "  $text = [string]$remoteAddresses; "
            "  if ([string]::IsNullOrWhiteSpace($text)) { return $false } "
            "  foreach ($part in $text -split ',') { "
            "    $candidate = $part.Trim(); "
            "    if ($candidate.Equals($expected, [System.StringComparison]::OrdinalIgnoreCase)) { return $true } "
            "  } "
            "  return $false "
            "} "
            "$connections = Get-NetConnectionProfile | "
            "Select-Object InterfaceAlias,"
            "Name,InterfaceIndex,"
            "@{Name='NetworkCategory';Expression={$_.NetworkCategory.ToString()}},"
            "@{Name='IPv4Connectivity';Expression={$_.IPv4Connectivity.ToString()}},"
            "@{Name='IPv6Connectivity';Expression={$_.IPv6Connectivity.ToString()}}; "
            "$firewall = Get-NetFirewallProfile | "
            "Select-Object Name,Enabled,"
            "@{Name='DefaultInboundAction';Expression={$_.DefaultInboundAction.ToString()}},"
            "@{Name='DefaultOutboundAction';Expression={$_.DefaultOutboundAction.ToString()}},"
            "@{Name='AllowInboundRules';Expression={$_.AllowInboundRules.ToString()}},"
            "NotifyOnListen,LogFileName,LogBlocked,LogAllowed; "
            "$listenerFirewall = $null; "
            "if ($listenerPort -gt 0) { "
            "  $activeProfiles = @($connections | ForEach-Object { $_.NetworkCategory } | "
            "    Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique); "
            "  $matches = @(); "
            "  try { "
            "    $policy = New-Object -ComObject HNetCfg.FwPolicy2; "
            "    foreach ($rule in $policy.Rules) { "
            "      try { "
            "        if (-not $rule.Enabled -or $rule.Direction -ne 1 -or $rule.Action -ne 1) { continue } "
            "        $app = [string]$rule.ApplicationName; "
            "        $programMatches = (-not [string]::IsNullOrWhiteSpace($app)) -and "
            "          $app.Equals($listenerProgram, [System.StringComparison]::OrdinalIgnoreCase); "
            "        $displayName = [string]$rule.Name; "
            "        $nameMatches = [string]::IsNullOrWhiteSpace($listenerRuleName) -or "
            "          $displayName.Equals($listenerRuleName, [System.StringComparison]::OrdinalIgnoreCase); "
            "        $ports = [string]$rule.LocalPorts; "
            "        $portScoped = (-not [string]::IsNullOrWhiteSpace($ports)) -and $ports -ne '*' -and $ports -ne 'Any'; "
            "        $portOnlyMatches = ([string]::IsNullOrWhiteSpace($app) -or $app -eq '*') -and $portScoped; "
            "        if (-not ($programMatches -or $portOnlyMatches)) { continue } "
            "        if (-not (($rule.Protocol -eq $listenerProtocolNumber) -or ($rule.Protocol -eq 256))) { continue } "
            "        if (-not (Test-PortMatch $ports $listenerPort)) { continue } "
            "        $remoteAddresses = [string]$rule.RemoteAddresses; "
            "        $remoteAddressMatches = Test-RemoteAddressMatch $remoteAddresses $listenerRemoteAddress; "
            "        $profiles = @(Convert-Profiles $rule.Profiles); "
            "        $profilesApply = $false; "
            "        foreach ($profile in $activeProfiles) { "
            "          if ($profiles -contains $profile -or $profiles -contains 'All') { $profilesApply = $true } "
            "        } "
            "        $productScopeMatches = $programMatches -and $nameMatches -and $remoteAddressMatches -and $profilesApply; "
            "        $matches += [pscustomobject]@{ "
            "          name=$displayName; profiles=$profiles; profile_mask=$rule.Profiles; "
            "          protocol=$rule.Protocol; local_ports=$ports; remote_addresses=$remoteAddresses; "
            "          application_name=$app; profiles_apply_to_active=$profilesApply; "
            "          program_matches=$programMatches; name_matches=$nameMatches; "
            "          remote_address_matches=$remoteAddressMatches; product_scope_matches=$productScopeMatches "
            "        }; "
            "      } catch {} "
            "    } "
            "    $productMatches = @($matches | Where-Object { $_.product_scope_matches }); "
            "    $listenerFirewall = [pscustomobject]@{ "
            "      program=$listenerProgram; protocol=$listenerProtocol; port=$listenerPort; bind_host=$listenerBindHost; "
            "      expected_rule_name=$listenerRuleName; expected_remote_address=$listenerRemoteAddress; "
            "      active_profiles=$activeProfiles; matching_rule_count=$matches.Count; "
            "      product_matching_rule_count=$productMatches.Count; product_rule_verified=($productMatches.Count -gt 0); "
            "      matching_rules=@($matches | Select-Object -First 20); "
            "      allowed_on_active_profile=[bool](@($matches | Where-Object { $_.profiles_apply_to_active }).Count -gt 0); "
            "      probe='windows_firewall_com_policy' "
            "    }; "
            "  } catch { "
            "    $listenerFirewall = [pscustomobject]@{ "
            "      program=$listenerProgram; protocol=$listenerProtocol; port=$listenerPort; bind_host=$listenerBindHost; "
            "      expected_rule_name=$listenerRuleName; expected_remote_address=$listenerRemoteAddress; "
            "      active_profiles=$activeProfiles; matching_rule_count=0; matching_rules=@(); "
            "      product_matching_rule_count=0; product_rule_verified=$false; "
            "      allowed_on_active_profile=$false; probe='windows_firewall_com_policy'; error=$_.Exception.Message "
            "    }; "
            "  } "
            "} "
            "[pscustomobject]@{connections=$connections; firewall=$firewall; listener_firewall=$listenerFirewall} | ConvertTo-Json -Compress -Depth 7"
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


def windows_mobile_hotspot_status(hotspot: dict[str, Any]) -> tuple[str, list[str]]:
    if not hotspot:
        return "blocked", ["hostess.issue.connectivity_probe.pc_hotspot_state_unavailable"]
    if hotspot.get("available") is not True:
        return "blocked", ["hostess.issue.connectivity_probe.pc_hotspot_unavailable"]
    state = str(hotspot.get("state") or "").strip().lower()
    if state == "on":
        return "pass", []
    if state == "off":
        return "blocked", ["hostess.issue.connectivity_probe.pc_hotspot_off"]
    return "warn", ["hostess.issue.connectivity_probe.pc_hotspot_state_unexpected"]


def windows_mobile_hotspot_summary(hotspot: dict[str, Any]) -> str:
    if not hotspot:
        return "Windows Mobile Hotspot state not available"
    state = str(hotspot.get("state") or "unknown")
    ssid = str(hotspot.get("ssid") or "")
    source = str(hotspot.get("source_profile") or "")
    clients = hotspot.get("client_count")
    max_clients = hotspot.get("max_client_count")
    if hotspot.get("available") is not True:
        error = str(hotspot.get("error") or "")
        return f"Mobile Hotspot unavailable: state={state} {error}".strip()
    return (
        f"Mobile Hotspot {state}; ssid={ssid or 'unknown'}; "
        f"source={source or 'unknown'}; clients={clients}/{max_clients}"
    )














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


def windows_network_profile_status(profile: dict[str, Any]) -> tuple[str, list[str]]:
    if not profile:
        return "skipped", []
    active_profiles = active_windows_network_categories(profile)
    issue_codes: list[str] = []
    if "Public" in active_profiles:
        issue_codes.append("hostess.issue.connectivity_probe.windows_network_profile_public")
    return ("warn" if issue_codes else "pass"), issue_codes


def active_windows_network_categories(profile: dict[str, Any]) -> list[str]:
    connections = profile.get("connections")
    if isinstance(connections, dict):
        rows = [connections]
    elif isinstance(connections, list):
        rows = [row for row in connections if isinstance(row, dict)]
    else:
        rows = []
    categories: list[str] = []
    for row in rows:
        category = str(row.get("NetworkCategory") or "").strip()
        if category and category not in categories:
            categories.append(category)
    return categories


def windows_firewall_listener_status(
    listener_firewall: dict[str, Any],
    probe_result: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    if not listener_firewall or not listener_firewall.get("port"):
        return "skipped", []
    if listener_firewall.get("allowed_on_active_profile") is True:
        return "pass", []
    protocol = normalize_firewall_protocol(str(listener_firewall.get("protocol") or "TCP"))
    issue_codes = [
        "hostess.issue.connectivity_probe.no_udp_listener_firewall_allow_rule"
        if protocol == "UDP"
        else "hostess.issue.connectivity_probe.no_tcp_listener_firewall_allow_rule"
    ]
    probe_status = str((probe_result or {}).get("status") or "")
    if probe_status == "fail":
        return "fail", issue_codes
    return "warn", issue_codes


def windows_firewall_listener_summary(listener_firewall: dict[str, Any]) -> str:
    if not listener_firewall or not listener_firewall.get("port"):
        return "Windows listener firewall coverage not available"
    program = str(listener_firewall.get("program") or "unknown")
    protocol = normalize_firewall_protocol(str(listener_firewall.get("protocol") or "TCP"))
    port = listener_firewall.get("port")
    profiles = listener_firewall.get("active_profiles")
    profile_text = ",".join(str(profile) for profile in profiles) if isinstance(profiles, list) else "unknown"
    allowed = listener_firewall.get("allowed_on_active_profile")
    match_count = listener_firewall.get("matching_rule_count", 0)
    allowed_text = "allowed" if allowed is True else "no active-profile allow rule"
    return f"{program} {protocol}/{port} on {profile_text}: {allowed_text} ({match_count} matching rule(s))"


def append_issue_once(
    issues: list[dict[str, Any]],
    issue_code: str,
    severity: str,
    message: str,
) -> None:
    if any(issue.get("issue_code") == issue_code for issue in issues):
        return
    issues.append(issue_row(issue_code, severity, message))


def ps_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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
        f"printf %s {shell_word(marker)} | "
        f"(toybox nc -w {int(timeout)} {host_ip} {port} || nc -w {int(timeout)} {host_ip} {port})"
    )
    result = run_timeout_func(
        adb_command(args, "shell", command_text),
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


def diagnostic_python_program_path(program: Any) -> bool:
    value = str(program or "").replace("\\", "/").lower()
    return value.endswith("/python.exe") or value.endswith("/python") or value.endswith("python.exe")


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










def topology_for_probe(probe_id: str) -> dict[str, Any]:
    if probe_id == "QCL-011":
        return {
            "owner": "pc_hotspot",
            "network_provider": "windows_mobile_hotspot",
            "endpoint_direction": "quest_to_host_lan",
            "requires_existing_wifi": False,
            "requires_adb": True,
            "requires_pairing": True,
            "requires_termux": False,
            "experimental": False,
        }
    return {
        "owner": "external_wifi",
        "network_provider": "router_or_existing_wifi",
        "endpoint_direction": "quest_to_host_lan",
        "requires_existing_wifi": True,
        "requires_adb": True,
        "requires_pairing": False,
        "requires_termux": False,
        "experimental": False,
    }


def topology_for_args(args: argparse.Namespace, probe_id: str) -> dict[str, Any]:
    topology = topology_for_probe(probe_id)
    owner = str(getattr(args, "topology_owner", "") or "").strip()
    provider = str(getattr(args, "network_provider", "") or "").strip()
    if owner:
        topology.update(topology_defaults_for_owner(owner))
        topology["owner"] = owner
    if provider:
        topology["network_provider"] = provider
    return topology


def topology_defaults_for_owner(owner: str) -> dict[str, Any]:
    defaults: dict[str, dict[str, Any]] = {
        "external_wifi": {
            "network_provider": "router_or_existing_wifi",
            "requires_existing_wifi": True,
            "requires_pairing": False,
            "experimental": False,
        },
        "pc_hotspot": {
            "network_provider": "windows_mobile_hotspot",
            "requires_existing_wifi": False,
            "requires_pairing": True,
            "experimental": False,
        },
        "phone_hotspot": {
            "network_provider": "phone_hotspot",
            "requires_existing_wifi": False,
            "requires_pairing": True,
            "experimental": False,
        },
        "travel_router": {
            "network_provider": "travel_router",
            "requires_existing_wifi": False,
            "requires_pairing": True,
            "experimental": False,
        },
        "local_only_hotspot": {
            "network_provider": "android_local_only_hotspot",
            "requires_existing_wifi": False,
            "requires_pairing": True,
            "experimental": True,
        },
        "wifi_direct": {
            "network_provider": "wifi_direct",
            "requires_existing_wifi": False,
            "requires_pairing": True,
            "experimental": True,
        },
    }
    return {
        "endpoint_direction": "quest_to_host_lan",
        "requires_adb": True,
        "requires_termux": False,
        **defaults.get(owner, {}),
    }


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




def base_report(args: argparse.Namespace, *, observed_at: datetime, probe_id: str | None = None) -> dict[str, Any]:
    selected_probe_id = probe_id or str(getattr(args, "probe_id", "") or "QCL-010")
    ensure_probe_run_id(args, observed_at, selected_probe_id)
    run_id = str(getattr(args, "run_id", "") or "").strip()
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


def ensure_probe_run_id(args: argparse.Namespace, observed_at: datetime, probe_id: str) -> str:
    run_id = str(getattr(args, "run_id", "") or "").strip()
    if run_id:
        return run_id
    stamp = observed_at.strftime("%Y%m%d-%H%M%S")
    run_id = f"{stamp}-{probe_id.lower()}"
    setattr(args, "run_id", run_id)
    return run_id














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








def utc_now() -> datetime:
    return datetime.now(UTC)
