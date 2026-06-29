"""LAN and device transport helpers for Quest connectivity probes."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import subprocess
import threading
import time
from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    DEFAULT_TCP_MARKER,
    adb_command,
    append_issue_once,
    base_report,
    check_row,
    completed_observed,
    ensure_probe_run_id,
    issue_row,
    object_value,
    powershell_executable,
    shell_word,
    strip_powershell_clixml_noise,
)
from tools.hostessctl.connectivity_firewall import (
    collect_windows_network_profile,
    network_profile_summary,
    windows_firewall_listener_status,
    windows_firewall_listener_summary,
    windows_network_profile_status,
)
from tools.hostessctl.connectivity_probe_live_reports import (
    live_qcl010_status,
    live_qcl011_status,
    measurements_from_checks,
    tcp_echo_listener_from_result,
)
from tools.hostessctl.connectivity_topology import (
    topology_for_probe,
    windows_mobile_hotspot_status,
    windows_mobile_hotspot_summary,
)


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
