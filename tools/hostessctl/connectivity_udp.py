"""QCL-080 UDP freshness helpers for Hostess connectivity probes."""

from __future__ import annotations

import argparse
import re
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_firewall import (
    collect_windows_network_profile,
    network_profile_summary,
    windows_firewall_listener_status,
    windows_firewall_listener_summary,
    windows_network_profile_status,
)
from tools.hostessctl.connectivity_lan import (
    choose_host_ip,
    collect_device_identity,
    collect_host_ipv4_candidates,
    same_subnet_check,
)
from tools.hostessctl.connectivity_probe_common import (
    append_issue_once,
    adb_command,
    base_report,
    check_status,
    check_row,
    completed_observed,
    issue_row,
    list_value,
    object_value,
    percentile,
    read_json_file,
    shell_word,
    wait_for_json_file,
)
from tools.hostessctl.connectivity_probe_live_reports import (
    live_qcl080_status,
    measurements_from_udp_check,
    udp_listener_from_result,
)
from tools.hostessctl.connectivity_topology import topology_for_args
from tools.hostessctl.platform_defaults import (
    MAKEPAD_ANDROID_PACKAGE,
    MAKEPAD_ANDROID_XR_ACTIVITY,
)

DEFAULT_UDP_MARKER = "rusty-qcl-udp"

DEFAULT_QCL080_UDP_PORT = 18767

QCL080_APP_MARKER_PREFIX = "RUSTY_HOSTESS_MAKEPAD_QCL080_UDP_SENDER"

QCL080_APP_MARKER_SCHEMA = "rusty.hostess.makepad.qcl080_udp_sender.v1"

QCL080_APP_PROPERTY_PREFIX = "debug.rustyquest.makepad.qcl080.udp"


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


def qcl080_app_owned_marker_observed(
    *,
    status: str,
    packets_sent: int,
    packets_requested: int = 12,
    host: str = "192.0.2.10",
    port: int = DEFAULT_QCL080_UDP_PORT,
    marker: str = DEFAULT_UDP_MARKER,
    run_id: str = "fixture-qcl080-app-owned",
) -> dict[str, Any]:
    fields = {
        "schema": QCL080_APP_MARKER_SCHEMA,
        "phase": "startup",
        "status": status,
        "enabled": "true",
        "host": host,
        "port": str(port),
        "marker": marker,
        "packetsRequested": str(packets_requested),
        "packetsSent": str(packets_sent),
        "intervalMs": "50",
        "elapsedMs": "700",
        "runId": run_id,
        "issue": "none" if status == "sent" else "fixture_issue",
        "senderSource": "makepad-runtime",
        "socketOwner": "app-owned",
        "highRateJsonPayload": "false",
        "settingsControlPayload": "false",
    }
    return {
        "line": QCL080_APP_MARKER_PREFIX
        + " "
        + " ".join(f"{key}={value}" for key, value in fields.items()),
        "fields": fields,
    }

def runtime_qcl080_udp_sender_check_from_result(
    udp_result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    observed = object_value((udp_result or {}).get("observed"))
    if observed.get("generator") != "app_owned_runtime_udp_sender":
        return None
    marker = object_value(observed.get("runtime_marker"))
    fields = object_value(marker.get("fields"))
    if not fields:
        return check_row(
            "runtime.qcl080_udp_sender",
            "fail",
            "Makepad runtime marker was not observed",
            observed=marker,
            issue_codes=["hostess.issue.connectivity_probe.qcl080_runtime_marker_missing"],
        )
    status = str(fields.get("status") or "")
    try:
        packets_requested = int(fields.get("packetsRequested") or 0)
        packets_sent = int(fields.get("packetsSent") or 0)
    except (TypeError, ValueError):
        packets_requested = 0
        packets_sent = 0
    passed = (
        fields.get("schema") == QCL080_APP_MARKER_SCHEMA
        and status == "sent"
        and packets_requested > 0
        and packets_sent >= packets_requested
        and fields.get("senderSource") == "makepad-runtime"
        and fields.get("socketOwner") == "app-owned"
    )
    if passed:
        return check_row(
            "runtime.qcl080_udp_sender",
            "pass",
            f"Makepad runtime marker status=sent packetsSent={packets_sent}/{packets_requested}",
            observed=marker,
        )
    issue_codes = ["hostess.issue.connectivity_probe.qcl080_runtime_marker_rejected"]
    return check_row(
        "runtime.qcl080_udp_sender",
        "warn" if packets_sent > 0 else "fail",
        f"Makepad runtime marker status={status or 'missing'} packetsSent={packets_sent}/{packets_requested}",
        observed=marker,
        issue_codes=issue_codes,
    )

def udp_endpoint_source(udp_result: dict[str, Any] | None) -> str:
    observed = object_value((udp_result or {}).get("observed"))
    return str(observed.get("generator") or "not_available")

def selected_udp_sender_source(args: argparse.Namespace, sender_host_path: str) -> str:
    requested = str(getattr(args, "udp_sender_source", "") or "").strip()
    if requested in {"makepad-runtime", "app-owned", "app_owned_runtime_udp_sender"}:
        return "makepad-runtime"
    if requested in {"adb-pushed-native", "native"}:
        return "adb-pushed-native"
    if requested in {"adb-shell", "shell"}:
        return "adb-shell"
    if sender_host_path:
        return "adb-pushed-native"
    return "adb-shell"

def start_makepad_runtime_udp_sender(
    args: argparse.Namespace,
    *,
    host_ip: str,
    port: int,
    marker: str,
    packet_count: int,
    interval_ms: float,
    run_timeout_func: Any,
) -> dict[str, Any]:
    run_id = str(getattr(args, "run_id", "") or "").strip()
    properties = qcl080_makepad_runtime_properties(
        host_ip=host_ip,
        port=port,
        marker=marker,
        packet_count=packet_count,
        interval_ms=interval_ms,
        run_id=run_id,
    )
    actions: list[dict[str, Any]] = []
    for key, value in properties.items():
        result = run_timeout_func(
            adb_command(args, "shell", "setprop", key, value),
            timeout_seconds=3.0,
        )
        actions.append(
            {
                "action": "set-qcl080-makepad-property",
                "property": key,
                "value": value,
                **completed_observed(result),
            }
        )

    package = str(getattr(args, "makepad_package", None) or MAKEPAD_ANDROID_PACKAGE)
    activity = str(getattr(args, "makepad_activity", None) or MAKEPAD_ANDROID_XR_ACTIVITY)
    if not getattr(args, "skip_makepad_force_stop", False):
        force_stop = run_timeout_func(
            adb_command(args, "shell", "am", "force-stop", package),
            timeout_seconds=5.0,
        )
        actions.append({"action": "force-stop-makepad-package", "package": package, **completed_observed(force_stop)})
    launch = run_timeout_func(
        adb_command(args, "shell", "am", "start", "-n", activity),
        timeout_seconds=float(getattr(args, "makepad_launch_timeout_seconds", 10.0) or 10.0),
    )
    actions.append({"action": "launch-makepad-activity", "activity": activity, **completed_observed(launch)})
    return {
        "properties": properties,
        "actions": actions,
        "package": package,
        "activity": activity,
        "launch": launch,
    }

def collect_makepad_runtime_udp_sender_marker(
    args: argparse.Namespace,
    *,
    marker: str,
    run_timeout_func: Any,
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    run_id = str(getattr(args, "run_id", "") or "").strip()
    logcat = run_timeout_func(
        adb_command(
            args,
            "shell",
            "logcat",
            "-d",
            "-v",
            "time",
            "-s",
            "HostessMakepad:I",
        ),
        timeout_seconds=8.0,
    )
    actions.append({"action": "capture-hostess-makepad-logcat", **completed_observed(logcat)})
    disable = run_timeout_func(
        adb_command(args, "shell", "setprop", f"{QCL080_APP_PROPERTY_PREFIX}.enabled", "false"),
        timeout_seconds=3.0,
    )
    actions.append(
        {
            "action": "disable-qcl080-makepad-property",
            "property": f"{QCL080_APP_PROPERTY_PREFIX}.enabled",
            **completed_observed(disable),
        }
    )
    parsed = latest_qcl080_app_marker(logcat.stdout, marker=marker, run_id=run_id)
    return {"runtime_marker": parsed, "actions": actions}

def qcl080_makepad_runtime_properties(
    *,
    host_ip: str,
    port: int,
    marker: str,
    packet_count: int,
    interval_ms: float,
    run_id: str,
) -> dict[str, str]:
    return {
        f"{QCL080_APP_PROPERTY_PREFIX}.enabled": "true",
        f"{QCL080_APP_PROPERTY_PREFIX}.host": host_ip,
        f"{QCL080_APP_PROPERTY_PREFIX}.port": str(port),
        f"{QCL080_APP_PROPERTY_PREFIX}.marker": marker,
        f"{QCL080_APP_PROPERTY_PREFIX}.packet.count": str(packet_count),
        f"{QCL080_APP_PROPERTY_PREFIX}.interval.ms": str(int(round(interval_ms))),
        f"{QCL080_APP_PROPERTY_PREFIX}.run.id": run_id,
    }

def latest_qcl080_app_marker(text: str, *, marker: str, run_id: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for line in (text or "").splitlines():
        if QCL080_APP_MARKER_PREFIX not in line:
            continue
        parsed = parse_marker_line(line, QCL080_APP_MARKER_PREFIX)
        fields = object_value(parsed.get("fields"))
        if fields.get("marker") != marker:
            continue
        if run_id and fields.get("runId") != run_id:
            continue
        matches.append(parsed)
    if not matches:
        return {
            "line": "",
            "fields": {},
            "expected_marker": marker,
            "expected_run_id": run_id,
            "matched": False,
        }
    latest = matches[-1]
    latest["matched"] = True
    return latest

def parse_marker_line(line: str, prefix: str) -> dict[str, Any]:
    start = line.find(prefix)
    marker_text = line[start:] if start >= 0 else line
    fields: dict[str, str] = {}
    for token in marker_text.split()[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        fields[key] = value
    return {"line": marker_text, "fields": fields}

def device_to_host_udp_freshness(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    marker = str(getattr(args, "udp_marker", DEFAULT_UDP_MARKER) or DEFAULT_UDP_MARKER)
    timeout = float(getattr(args, "udp_timeout_seconds", 5.0))
    bind_host = str(getattr(args, "udp_bind_host", "0.0.0.0") or "0.0.0.0")
    requested_port = int(getattr(args, "udp_port", 0) or 0) or DEFAULT_QCL080_UDP_PORT
    packet_count = max(1, int(getattr(args, "udp_packet_count", 12) or 12))
    interval_ms = max(0.0, float(getattr(args, "udp_interval_ms", 50.0) or 50.0))
    max_loss_percent = max(0.0, float(getattr(args, "udp_max_loss_percent", 10.0) or 10.0))
    max_jitter_ms = max(0.0, float(getattr(args, "udp_max_jitter_ms", 250.0) or 250.0))
    sender_host_path = str(getattr(args, "udp_sender_host_path", "") or "").strip()
    sender_device_path = str(
        getattr(args, "udp_sender_device_path", "/data/local/tmp/rusty-qcl080-udp-sender")
        or "/data/local/tmp/rusty-qcl080-udp-sender"
    ).strip()
    sender_source = selected_udp_sender_source(args, sender_host_path)
    listener_helper = str(getattr(args, "udp_listener_helper", "") or "").strip()
    if listener_helper:
        return device_to_host_udp_freshness_with_listener_helper(
            args,
            host_ip,
            run_timeout_func,
            marker=marker,
            timeout=timeout,
            bind_host=bind_host,
            requested_port=requested_port,
            packet_count=packet_count,
            interval_ms=interval_ms,
            max_loss_percent=max_loss_percent,
            max_jitter_ms=max_jitter_ms,
            sender_host_path=sender_host_path,
            sender_device_path=sender_device_path,
            sender_source=sender_source,
            listener_helper=listener_helper,
        )
    received: dict[str, Any] = {"packets": [], "error": ""}
    ready = threading.Event()

    def server() -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((bind_host, requested_port))
                sock.settimeout(0.2)
                received["port"] = sock.getsockname()[1]
                ready.set()
                deadline = time.monotonic() + timeout + packet_count * 1.2
                while time.monotonic() < deadline:
                    try:
                        data, addr = sock.recvfrom(2048)
                    except TimeoutError:
                        continue
                    except socket.timeout:
                        continue
                    received["packets"].append(
                        {
                            "payload": data.decode("utf-8", "replace").strip(),
                            "peer": f"{addr[0]}:{addr[1]}",
                            "arrival_monotonic": time.monotonic(),
                        }
                    )
                    if len(received["packets"]) >= packet_count:
                        break
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
            "protocol.udp_freshness",
            "blocked",
            f"UDP freshness server did not start: {received.get('error') or 'unknown'}",
            issue_codes=["hostess.issue.connectivity_probe.udp_server_failed"],
        )

    generator = "adb_shell_udp_generator"
    push_result: subprocess.CompletedProcess[str] | None = None
    chmod_result: subprocess.CompletedProcess[str] | None = None
    runtime_sender: dict[str, Any] = {}
    app_actions: list[dict[str, Any]] = []
    if sender_source == "makepad-runtime":
        generator = "app_owned_runtime_udp_sender"
        runtime_sender = start_makepad_runtime_udp_sender(
            args,
            host_ip=host_ip,
            port=port,
            marker=marker,
            packet_count=packet_count,
            interval_ms=interval_ms,
            run_timeout_func=run_timeout_func,
        )
        app_actions = list_value(runtime_sender.get("actions"))
        result = runtime_sender.get("launch") or subprocess.CompletedProcess([], 1, "", "missing launch result")
    elif sender_host_path:
        generator = "adb_pushed_native_udp_sender"
        push_result = run_timeout_func(
            adb_command(args, "push", sender_host_path, sender_device_path),
            timeout_seconds=15.0,
        )
        chmod_result = run_timeout_func(
            adb_command(args, "shell", "chmod", "755", sender_device_path),
            timeout_seconds=5.0,
        )
        result = run_timeout_func(
            adb_command(
                args,
                "shell",
                sender_device_path,
                host_ip,
                str(port),
                marker,
                str(packet_count),
                str(int(round(interval_ms))),
            ),
            timeout_seconds=timeout + packet_count * max(0.02, interval_ms / 1000.0) + 3.0,
        )
    else:
        interval_seconds = f"{interval_ms / 1000.0:.3f}".rstrip("0").rstrip(".")
        payload_format = shell_word(marker + "|%04d\\n")
        command_text = (
            f"i=0; while [ $i -lt {packet_count} ]; do "
            f"printf {payload_format} \"$i\" | "
            f"(toybox nc -u -w 1 -q 1 {host_ip} {port} || nc -u -w 1 -q 1 {host_ip} {port}); "
            "i=$((i+1)); "
            f"sleep {interval_seconds}; "
            "done"
        )
        result = run_timeout_func(
            adb_command(args, "shell", command_text),
            timeout_seconds=timeout + packet_count * (1.2 + max(0.05, interval_ms / 1000.0)) + 3.0,
        )
    thread.join(timeout=timeout + 1.0)
    if sender_source == "makepad-runtime":
        runtime_marker_result = collect_makepad_runtime_udp_sender_marker(
            args,
            marker=marker,
            run_timeout_func=run_timeout_func,
        )
        runtime_sender["runtime_marker"] = object_value(runtime_marker_result.get("runtime_marker"))
        app_actions.extend(list_value(runtime_marker_result.get("actions")))
    elapsed_ms = int((time.monotonic() - started) * 1000)
    packets = list(received.get("packets") or [])
    sequences = udp_sequences_from_packets(packets, marker)
    unique_sequences = sorted(set(sequences))
    received_count = len(unique_sequences)
    duplicate_count = max(0, len(sequences) - received_count)
    loss_count = max(0, packet_count - received_count)
    loss_percent = round((loss_count / packet_count) * 100.0, 2)
    interarrival_ms = udp_interarrival_ms(packets)
    interarrival_ms_p95 = percentile(interarrival_ms, 95)
    loss_ok = loss_percent <= max_loss_percent
    jitter_ok = interarrival_ms_p95 is None or interarrival_ms_p95 <= max_jitter_ms
    if received_count == 0:
        status = "fail"
    elif loss_ok and jitter_ok:
        status = "pass"
    else:
        status = "warn"
    issue_codes: list[str] = []
    if status == "fail":
        issue_codes.append("hostess.issue.connectivity_probe.udp_freshness_failed")
    elif status == "warn":
        issue_codes.append("hostess.issue.connectivity_probe.udp_freshness_degraded")
    evidence = (
        f"{received_count}/{packet_count} packets, loss={loss_percent:.1f}%, "
        f"p95_gap={interarrival_ms_p95 if interarrival_ms_p95 is not None else 'n/a'}ms"
    )
    return check_row(
        "protocol.udp_freshness",
        status,
        evidence,
        observed={
            "host_ip": host_ip,
            "port": port,
            "marker": marker,
            "packets_requested": packet_count,
            "packets_received": received_count,
            "datagrams_received": len(packets),
            "unique_sequences": unique_sequences[:50],
            "duplicates": duplicate_count,
            "loss_percent": loss_percent,
            "elapsed_ms": elapsed_ms,
            "interarrival_ms": interarrival_ms[:50],
            "interarrival_ms_p95": interarrival_ms_p95,
            "generator": generator,
            "sender_host_path": sender_host_path,
            "sender_device_path": sender_device_path if sender_host_path else "",
            "app_actions": app_actions,
            "runtime_marker": object_value(runtime_sender.get("runtime_marker")),
            "runtime_properties": object_value(runtime_sender.get("properties")),
            "adb_push": completed_observed(push_result) if push_result else None,
            "adb_chmod": completed_observed(chmod_result) if chmod_result else None,
            "adb_client": completed_observed(result),
            "server_error": received.get("error", ""),
            "server_peer": packets[0]["peer"] if packets else "",
        },
        notes=(
            "App-owned Makepad runtime UDP sender; Hostess ADB only configured and launched the runtime."
            if sender_source == "makepad-runtime"
            else "Diagnostic UDP generator uses ADB shell netcat; app-owned runtime UDP remains a separate promotion gate."
        ),
        issue_codes=issue_codes,
    )

def device_to_host_udp_freshness_with_listener_helper(
    args: argparse.Namespace,
    host_ip: str,
    run_timeout_func: Any,
    *,
    marker: str,
    timeout: float,
    bind_host: str,
    requested_port: int,
    packet_count: int,
    interval_ms: float,
    max_loss_percent: float,
    max_jitter_ms: float,
    sender_host_path: str,
    sender_device_path: str,
    sender_source: str,
    listener_helper: str,
) -> dict[str, Any]:
    run_token = safe_filename(str(getattr(args, "run_id", "") or f"{int(time.time() * 1000)}"))
    helper_root = Path(tempfile.gettempdir()) / "rusty-hostess-qcl080"
    helper_root.mkdir(parents=True, exist_ok=True)
    ready_path = helper_root / f"{run_token}.listener-ready.json"
    out_path = helper_root / f"{run_token}.listener-result.json"
    for path in [ready_path, out_path]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    helper_command = [
        listener_helper,
        "--qcl080-udp-listener",
        "--bind-host",
        bind_host,
        "--port",
        str(requested_port),
        "--marker",
        marker,
        "--packet-count",
        str(packet_count),
        "--timeout-seconds",
        f"{timeout + packet_count * 1.2:.3f}",
        "--ready-out",
        str(ready_path),
        "--out",
        str(out_path),
    ]
    started = time.monotonic()
    try:
        listener_process = subprocess.Popen(
            helper_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        return check_row(
            "protocol.udp_freshness",
            "blocked",
            f"WPF UDP listener helper did not start: {exc}",
            observed={"listener_helper": listener_helper, "error": str(exc)},
            issue_codes=["hostess.issue.connectivity_probe.udp_listener_helper_failed"],
        )

    ready = wait_for_json_file(ready_path, timeout_seconds=timeout)
    if not ready:
        terminate_process(listener_process)
        return check_row(
            "protocol.udp_freshness",
            "blocked",
            "WPF UDP listener helper did not report readiness",
            observed={
                "listener_helper": listener_helper,
                "ready_path": str(ready_path),
                "result_path": str(out_path),
            },
            issue_codes=["hostess.issue.connectivity_probe.udp_listener_helper_not_ready"],
        )

    port = int(ready.get("port") or requested_port)
    generator = "adb_shell_udp_generator"
    push_result: subprocess.CompletedProcess[str] | None = None
    chmod_result: subprocess.CompletedProcess[str] | None = None
    runtime_sender: dict[str, Any] = {}
    app_actions: list[dict[str, Any]] = []
    if sender_source == "makepad-runtime":
        generator = "app_owned_runtime_udp_sender"
        runtime_sender = start_makepad_runtime_udp_sender(
            args,
            host_ip=host_ip,
            port=port,
            marker=marker,
            packet_count=packet_count,
            interval_ms=interval_ms,
            run_timeout_func=run_timeout_func,
        )
        app_actions = list_value(runtime_sender.get("actions"))
        result = runtime_sender.get("launch") or subprocess.CompletedProcess([], 1, "", "missing launch result")
    elif sender_host_path:
        generator = "adb_pushed_native_udp_sender"
        push_result = run_timeout_func(
            adb_command(args, "push", sender_host_path, sender_device_path),
            timeout_seconds=15.0,
        )
        chmod_result = run_timeout_func(
            adb_command(args, "shell", "chmod", "755", sender_device_path),
            timeout_seconds=5.0,
        )
        result = run_timeout_func(
            adb_command(
                args,
                "shell",
                sender_device_path,
                host_ip,
                str(port),
                marker,
                str(packet_count),
                str(int(round(interval_ms))),
            ),
            timeout_seconds=timeout + packet_count * max(0.02, interval_ms / 1000.0) + 3.0,
        )
    else:
        interval_seconds = f"{interval_ms / 1000.0:.3f}".rstrip("0").rstrip(".")
        payload_format = shell_word(marker + "|%04d\\n")
        command_text = (
            f"i=0; while [ $i -lt {packet_count} ]; do "
            f"printf {payload_format} \"$i\" | "
            f"(toybox nc -u -w 1 -q 1 {host_ip} {port} || nc -u -w 1 -q 1 {host_ip} {port}); "
            "i=$((i+1)); "
            f"sleep {interval_seconds}; "
            "done"
        )
        result = run_timeout_func(
            adb_command(args, "shell", command_text),
            timeout_seconds=timeout + packet_count * (1.2 + max(0.05, interval_ms / 1000.0)) + 3.0,
        )

    helper_stdout = ""
    helper_stderr = ""
    try:
        helper_stdout, helper_stderr = listener_process.communicate(
            timeout=timeout + packet_count * 1.2 + 5.0,
        )
    except subprocess.TimeoutExpired:
        terminate_process(listener_process)
        helper_stdout, helper_stderr = listener_process.communicate(timeout=2.0)

    if sender_source == "makepad-runtime":
        runtime_marker_result = collect_makepad_runtime_udp_sender_marker(
            args,
            marker=marker,
            run_timeout_func=run_timeout_func,
        )
        runtime_sender["runtime_marker"] = object_value(runtime_marker_result.get("runtime_marker"))
        app_actions.extend(list_value(runtime_marker_result.get("actions")))

    listener_report = read_json_file(out_path)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    packets = packets_from_listener_report(listener_report)
    sequences = udp_sequences_from_packets(packets, marker)
    unique_sequences = sorted(set(sequences))
    received_count = len(unique_sequences)
    duplicate_count = max(0, len(sequences) - received_count)
    loss_count = max(0, packet_count - received_count)
    loss_percent = round((loss_count / packet_count) * 100.0, 2)
    interarrival_ms = udp_interarrival_ms(packets)
    interarrival_ms_p95 = percentile(interarrival_ms, 95)
    loss_ok = loss_percent <= max_loss_percent
    jitter_ok = interarrival_ms_p95 is None or interarrival_ms_p95 <= max_jitter_ms
    if received_count == 0:
        status = "fail"
    elif loss_ok and jitter_ok:
        status = "pass"
    else:
        status = "warn"
    issue_codes: list[str] = []
    if status == "fail":
        issue_codes.append("hostess.issue.connectivity_probe.udp_freshness_failed")
    elif status == "warn":
        issue_codes.append("hostess.issue.connectivity_probe.udp_freshness_degraded")
    evidence = (
        f"{received_count}/{packet_count} packets, loss={loss_percent:.1f}%, "
        f"p95_gap={interarrival_ms_p95 if interarrival_ms_p95 is not None else 'n/a'}ms"
    )
    return check_row(
        "protocol.udp_freshness",
        status,
        evidence,
        observed={
            "host_ip": host_ip,
            "port": port,
            "marker": marker,
            "packets_requested": packet_count,
            "packets_received": received_count,
            "datagrams_received": len(packets),
            "unique_sequences": unique_sequences[:50],
            "duplicates": duplicate_count,
            "loss_percent": loss_percent,
            "elapsed_ms": elapsed_ms,
            "interarrival_ms": interarrival_ms[:50],
            "interarrival_ms_p95": interarrival_ms_p95,
            "generator": generator,
            "listener_owner": "hostess_companion_wpf",
            "listener_program": str(listener_report.get("program") or ready.get("program") or listener_helper),
            "listener_helper": listener_helper,
            "listener_ready": ready,
            "listener_report": listener_report,
            "listener_process": {
                "returncode": listener_process.returncode,
                "stdout": helper_stdout,
                "stderr": helper_stderr,
            },
            "sender_host_path": sender_host_path,
            "sender_device_path": sender_device_path if sender_host_path else "",
            "app_actions": app_actions,
            "runtime_marker": object_value(runtime_sender.get("runtime_marker")),
            "runtime_properties": object_value(runtime_sender.get("properties")),
            "adb_push": completed_observed(push_result) if push_result else None,
            "adb_chmod": completed_observed(chmod_result) if chmod_result else None,
            "adb_client": completed_observed(result),
            "server_error": str(listener_report.get("error") or ""),
            "server_peer": packets[0]["peer"] if packets else "",
        },
        notes=(
            "App-owned Makepad runtime UDP sender with WPF-owned host UDP listener."
            if sender_source == "makepad-runtime"
            else "WPF-owned host UDP listener with diagnostic sender; app-owned runtime UDP remains a separate promotion gate."
        ),
        issue_codes=issue_codes,
    )

def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        process.kill()

def packets_from_listener_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for row in list_value(report.get("packets")):
        if not isinstance(row, dict):
            continue
        arrival = float(row.get("arrival_elapsed_ms") or 0.0) / 1000.0
        packets.append(
            {
                "payload": str(row.get("payload") or ""),
                "peer": str(row.get("peer") or ""),
                "arrival_monotonic": arrival,
            }
        )
    return packets

def safe_filename(value: str) -> str:
    chars = [char if char.isalnum() or char in {".", "_", "-"} else "-" for char in value]
    token = "".join(chars).strip("._-")
    return token or "run"

def udp_sequences_from_packets(packets: list[dict[str, Any]], marker: str) -> list[int]:
    sequences: list[int] = []
    prefix = marker + "|"
    for packet in packets:
        payload = str(packet.get("payload") or "")
        if not payload.startswith(prefix):
            continue
        sequence_text = payload[len(prefix):].split("|", 1)[0].strip()
        try:
            sequences.append(int(sequence_text))
        except ValueError:
            continue
    return sequences

def udp_interarrival_ms(packets: list[dict[str, Any]]) -> list[int]:
    arrivals = [
        float(packet["arrival_monotonic"])
        for packet in packets
        if isinstance(packet.get("arrival_monotonic"), (float, int))
    ]
    arrivals.sort()
    return [int(round((right - left) * 1000.0)) for left, right in zip(arrivals, arrivals[1:])]
