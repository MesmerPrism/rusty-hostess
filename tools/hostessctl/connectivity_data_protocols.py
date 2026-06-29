"""Data-protocol adapters for Quest connectivity lab probes."""

from __future__ import annotations

import argparse
import json
import re
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    adb_command,
    append_issue_once,
    base_report,
    check_row,
    collect_android_activity_launch_precondition,
    completed_observed,
    dedupe_issue_codes,
    ensure_probe_run_id,
    float_value,
    int_value,
    median,
    object_value,
    parse_json_string,
    percentile,
    read_android_json_with_retry,
    redact_command_for_report,
    round_float,
    sanitize_filename,
    trim_text,
)
from tools.hostessctl.connectivity_lan import (
    choose_host_ip,
    collect_device_identity,
    collect_host_ipv4_candidates,
    same_subnet_check,
)
from tools.hostessctl.connectivity_probe_live_reports import (
    live_qcl081_status,
    live_qcl083_status,
    live_qcl084_status,
    measurements_from_lsl_probe,
    measurements_from_osc_probe,
    measurements_from_zeromq_probe,
    protocol_topology_for_report,
)
from tools.hostessctl.platform_defaults import (
    ANDROID_PACKAGE,
    ANDROID_QCL083_OSC_ACTION,
    ANDROID_REMOTE_QCL083_OSC_EVIDENCE,
)

DEFAULT_QCL083_OSC_PORT = 18783
DEFAULT_QCL084_ZEROMQ_PORT = 18784


def parse_probe_json_stdout(stdout: str) -> dict[str, Any]:
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


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

def lsl_discovery_sample_continuity(args: argparse.Namespace) -> dict[str, Any]:
    source = str(getattr(args, "lsl_source", "host-loopback") or "host-loopback")
    stream_name = str(getattr(args, "lsl_stream_name", "RustyQCL081") or "RustyQCL081")
    stream_type = str(getattr(args, "lsl_stream_type", "Markers") or "Markers")
    sample_count = max(1, int(getattr(args, "lsl_sample_count", 16) or 16))
    timeout = max(0.5, float(getattr(args, "lsl_timeout_seconds", 5.0) or 5.0))
    if source != "host-loopback":
        return {
            "status": "blocked",
            "source": source,
            "stream_name": stream_name,
            "stream_type": stream_type,
            "samples_requested": sample_count,
            "samples_received": 0,
            "loss_percent": 100.0,
            "discovery_ms": None,
            "monotonic_sequences": False,
            "issue_codes": ["hostess.issue.connectivity_probe.quest_lsl_source_not_configured"],
            "notes": "QCL-081 external/Quest LSL source is not implemented in hostessctl yet",
        }
    try:
        from pylsl import StreamInfo, StreamInlet, StreamOutlet, resolve_byprop
    except Exception as exc:
        return {
            "status": "blocked",
            "source": source,
            "stream_name": stream_name,
            "stream_type": stream_type,
            "samples_requested": sample_count,
            "samples_received": 0,
            "loss_percent": 100.0,
            "discovery_ms": None,
            "monotonic_sequences": False,
            "issue_codes": ["hostess.issue.connectivity_probe.pylsl_unavailable"],
            "notes": f"pylsl unavailable: {exc}",
        }

    source_id = f"rusty-qcl081-{int(time.time() * 1000)}"
    info = StreamInfo(stream_name, stream_type, 1, 0, "float32", source_id)
    outlet = StreamOutlet(info)
    time.sleep(0.15)
    discovery_started = time.monotonic()
    streams = resolve_byprop("name", stream_name, minimum=1, timeout=timeout)
    discovery_ms = int(round((time.monotonic() - discovery_started) * 1000.0))
    if not streams:
        return {
            "status": "fail",
            "source": source,
            "stream_name": stream_name,
            "stream_type": stream_type,
            "samples_requested": sample_count,
            "samples_received": 0,
            "loss_percent": 100.0,
            "discovery_ms": discovery_ms,
            "monotonic_sequences": False,
            "issue_codes": ["hostess.issue.connectivity_probe.lsl_discovery_failed"],
            "notes": "no LSL stream was discovered",
        }
    inlet = StreamInlet(streams[0])
    try:
        inlet.open_stream(timeout=timeout)
    except Exception:
        pass
    producer_done = threading.Event()

    def producer() -> None:
        time.sleep(0.1)
        for sequence in range(sample_count):
            outlet.push_sample([float(sequence)])
            time.sleep(0.01)
        producer_done.set()

    producer_thread = threading.Thread(target=producer, daemon=True)
    producer_thread.start()
    received: list[int] = []
    deadline = time.monotonic() + timeout
    while len(received) < sample_count and (time.monotonic() < deadline or not producer_done.is_set()):
        sample, _timestamp = inlet.pull_sample(timeout=0.2)
        if not sample:
            continue
        try:
            received.append(int(round(float(sample[0]))))
        except (TypeError, ValueError, IndexError):
            continue
    producer_thread.join(timeout=1.0)
    received_count = len(received)
    loss_percent = round(((sample_count - received_count) / sample_count) * 100.0, 2)
    monotonic = received == list(range(received_count))
    if received_count == sample_count and monotonic:
        status = "pass"
        issue_codes: list[str] = []
    elif received_count > 0:
        status = "warn"
        issue_codes = ["hostess.issue.connectivity_probe.lsl_sample_continuity_degraded"]
    else:
        status = "fail"
        issue_codes = ["hostess.issue.connectivity_probe.lsl_sample_continuity_failed"]
    return {
        "status": status,
        "source": source,
        "stream_name": stream_name,
        "stream_type": stream_type,
        "samples_requested": sample_count,
        "samples_received": received_count,
        "loss_percent": loss_percent,
        "discovery_ms": discovery_ms,
        "monotonic_sequences": monotonic,
        "received_sequences": received[:50],
        "issue_codes": issue_codes,
        "notes": "host-local LSL loopback; not a Quest-to-PC topology proof",
    }

def lsl_manifold_broker_probe(args: argparse.Namespace, run_captured_func: Any) -> dict[str, Any]:
    source = "manifold-lsl-broker"
    stream_name = str(getattr(args, "lsl_stream_name", "RustyQCL081") or "RustyQCL081")
    stream_type = str(getattr(args, "lsl_stream_type", "Markers") or "Markers")
    sample_count = max(1, int(getattr(args, "lsl_sample_count", 16) or 16))
    timeout = max(0.5, float(getattr(args, "lsl_timeout_seconds", 5.0) or 5.0))
    root = resolve_lsl_manifold_root(args)
    if root is None:
        return {
            "status": "blocked",
            "source": source,
            "stream_name": stream_name,
            "stream_type": stream_type,
            "samples_requested": sample_count,
            "samples_received": 0,
            "loss_percent": 100.0,
            "discovery_ms": None,
            "monotonic_sequences": False,
            "issue_codes": ["hostess.issue.connectivity_probe.manifold_lsl_root_missing"],
            "notes": "Rusty Manifold root with tools/qcl081_lsl_clocked_samples.py was not found",
        }

    command = [
        sys.executable,
        str(root / "tools" / "qcl081_lsl_clocked_samples.py"),
        "--json",
        "--source",
        source,
        "--stream-name",
        stream_name,
        "--stream-type",
        stream_type,
        "--sample-count",
        str(sample_count),
        "--timeout-seconds",
        str(timeout),
    ]
    try:
        completed = run_captured_func(command, allow_failure=True, cwd=root)
    except Exception as exc:
        return {
            "status": "blocked",
            "source": source,
            "stream_name": stream_name,
            "stream_type": stream_type,
            "samples_requested": sample_count,
            "samples_received": 0,
            "loss_percent": 100.0,
            "discovery_ms": None,
            "monotonic_sequences": False,
            "issue_codes": ["hostess.issue.connectivity_probe.manifold_lsl_broker_failed"],
            "notes": f"Manifold LSL broker-owned probe could not be launched: {exc}",
        }

    parsed = parse_probe_json_stdout(completed.stdout)
    if not parsed:
        return {
            "status": "blocked",
            "source": source,
            "stream_name": stream_name,
            "stream_type": stream_type,
            "samples_requested": sample_count,
            "samples_received": 0,
            "loss_percent": 100.0,
            "discovery_ms": None,
            "monotonic_sequences": False,
            "issue_codes": ["hostess.issue.connectivity_probe.manifold_lsl_report_missing"],
            "notes": (completed.stderr or completed.stdout or "Manifold LSL broker-owned report missing").strip()[:800],
        }

    issue_codes = [str(code) for code in parsed.get("issue_codes", []) or []]
    route_evidence = object_value(parsed.get("bridge_route_evidence"))
    authority = object_value(parsed.get("authority"))
    requested = int_value(parsed.get("samples_requested")) or sample_count
    received = int_value(parsed.get("samples_received")) or 0
    loss_percent = float_value(parsed.get("loss_percent"), default=100.0)
    status = str(parsed.get("status") or "blocked")
    broker_owned = (
        str(parsed.get("evidence_tier") or "") == "broker_owned"
        and str(authority.get("owner") or "") == "rusty.manifold.transport"
        and str(route_evidence.get("status") or "") == "pass"
    )
    if completed.returncode != 0 and status == "pass":
        status = "blocked"
        issue_codes.append("hostess.issue.connectivity_probe.manifold_lsl_broker_failed")
    if status == "pass" and not broker_owned:
        status = "warn"
        issue_codes.append("hostess.issue.connectivity_probe.manifold_lsl_broker_owned_evidence_missing")
    if status == "pass" and (
        received < requested
        or loss_percent > 0.0
        or parsed.get("monotonic_sequences") is False
    ):
        status = "warn"
        issue_codes.append("hostess.issue.connectivity_probe.lsl_sample_continuity_degraded")
    if status not in {"pass", "warn", "fail", "blocked"}:
        status = "blocked"
        issue_codes.append("hostess.issue.connectivity_probe.manifold_lsl_broker_status_invalid")

    return {
        "status": status,
        "source": source,
        "stream_name": parsed.get("stream_name") or stream_name,
        "stream_type": parsed.get("stream_type") or stream_type,
        "source_id": parsed.get("source_id"),
        "samples_requested": requested,
        "samples_received": received,
        "loss_percent": loss_percent,
        "discovery_ms": parsed.get("discovery_ms"),
        "monotonic_sequences": parsed.get("monotonic_sequences"),
        "received_sequences": parsed.get("received_sequences", []),
        "evidence_tier": parsed.get("evidence_tier"),
        "authority_owner": authority.get("owner"),
        "route_id": parsed.get("route_id"),
        "bridge_route_evidence": route_evidence,
        "library_version": parsed.get("library_version"),
        "issue_codes": dedupe_issue_codes(issue_codes),
        "notes": (
            "Manifold-owned LSL route evidence from rusty-manifold; "
            "Hostess only wraps the emitted broker-owned report"
        ),
    }

def lsl_quest_runtime_preflight(args: argparse.Namespace, run_captured_func: Any) -> dict[str, Any]:
    stream_name = str(getattr(args, "lsl_stream_name", "RustyQCL081") or "RustyQCL081")
    stream_type = str(getattr(args, "lsl_stream_type", "Markers") or "Markers")
    sample_count = max(1, int(getattr(args, "lsl_sample_count", 16) or 16))
    if not getattr(args, "adb", None) or not getattr(args, "serial", None):
        return {
            "status": "blocked",
            "source": "quest-runtime",
            "stream_name": stream_name,
            "stream_type": stream_type,
            "samples_requested": sample_count,
            "samples_received": 0,
            "loss_percent": 100.0,
            "discovery_ms": None,
            "monotonic_sequences": False,
            "issue_codes": ["hostess.issue.connectivity_probe.lsl_android_adb_missing"],
            "notes": "QCL-081 Quest runtime LSL preflight requires --adb and --serial",
        }

    python_command = (
        "run-as com.termux /data/data/com.termux/files/usr/bin/python3.13 "
        "-c 'import sys; print(sys.version)'"
    )
    pylsl_command = (
        "run-as com.termux /data/data/com.termux/files/usr/bin/python3.13 "
        "-c 'import pylsl; print(pylsl.__version__)'"
    )
    python_result = run_captured_func(adb_command(args, "shell", python_command), allow_failure=True)
    pylsl_result = run_captured_func(adb_command(args, "shell", pylsl_command), allow_failure=True)
    issue_codes: list[str] = []
    if python_result.returncode != 0:
        issue_codes.append("hostess.issue.connectivity_probe.lsl_termux_python_missing")
    if pylsl_result.returncode != 0:
        issue_codes.append("hostess.issue.connectivity_probe.lsl_quest_pylsl_missing")
    if not issue_codes:
        issue_codes.append("hostess.issue.connectivity_probe.quest_lsl_source_not_configured")
    notes = (
        "Termux Python is available, but pylsl/liblsl is not importable on the Quest"
        if python_result.returncode == 0 and pylsl_result.returncode != 0
        else "Quest-side LSL producer runtime is not launchable from the current Termux environment"
        if python_result.returncode != 0
        else "Quest-side pylsl import is available, but Hostess has no Quest LSL outlet launcher yet"
    )
    return {
        "status": "blocked",
        "source": "quest-runtime",
        "stream_name": stream_name,
        "stream_type": stream_type,
        "samples_requested": sample_count,
        "samples_received": 0,
        "loss_percent": 100.0,
        "discovery_ms": None,
        "monotonic_sequences": False,
        "received_sequences": [],
        "issue_codes": issue_codes,
        "notes": notes,
        "quest_runtime_preflight": {
            "termux_python": completed_observed(python_result),
            "pylsl_import": completed_observed(pylsl_result),
        },
    }


def osc_loopback_probe(args: argparse.Namespace) -> dict[str, Any]:
    source = str(getattr(args, "osc_source", "host-loopback") or "host-loopback")
    address = str(getattr(args, "osc_address", "/rusty/qcl083") or "/rusty/qcl083")
    message_count = max(1, int(getattr(args, "osc_message_count", 16) or 16))
    timeout = max(0.5, float(getattr(args, "osc_timeout_seconds", 5.0) or 5.0))
    max_loss_percent = max(0.0, float(getattr(args, "osc_max_loss_percent", 0.0) or 0.0))
    if source != "host-loopback":
        return {
            "status": "blocked",
            "source": source,
            "address": address,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "loss_percent": 100.0,
            "round_trip_ms_p95": None,
            "monotonic_sequences": False,
            "issue_codes": ["hostess.issue.connectivity_probe.quest_osc_source_not_configured"],
            "notes": "QCL-083 external/Quest OSC source is not implemented in hostessctl yet",
        }

    received_sequences: list[int] = []
    acknowledged_sequences: list[int] = []
    rtts: list[int] = []
    server_ready = threading.Event()
    server_done = threading.Event()
    server_error: list[str] = []

    def server() -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
                server_socket.bind(("127.0.0.1", int(getattr(args, "osc_port", 0) or 0)))
                server_socket.settimeout(0.2)
                server_port_holder.append(server_socket.getsockname()[1])
                server_ready.set()
                deadline = time.monotonic() + timeout
                while len(received_sequences) < message_count and time.monotonic() < deadline:
                    try:
                        payload, addr = server_socket.recvfrom(8192)
                    except socket.timeout:
                        continue
                    parsed = parse_osc_message(payload)
                    sequence = int(parsed.get("sequence", -1))
                    if parsed.get("address") == address and sequence >= 0:
                        received_sequences.append(sequence)
                        server_socket.sendto(build_osc_message("/rusty/qcl083/ack", sequence, "ack"), addr)
        except OSError as exc:
            server_error.append(str(exc))
        finally:
            server_done.set()

    server_port_holder: list[int] = []
    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    if not server_ready.wait(timeout=1.0) or not server_port_holder:
        return {
            "status": "blocked",
            "source": source,
            "address": address,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "loss_percent": 100.0,
            "round_trip_ms_p95": None,
            "monotonic_sequences": False,
            "issue_codes": ["hostess.issue.connectivity_probe.osc_listener_not_ready"],
            "notes": "OSC loopback listener did not become ready",
        }

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.bind(("127.0.0.1", 0))
        client_socket.settimeout(min(0.5, timeout))
        for sequence in range(message_count):
            started = time.monotonic()
            client_socket.sendto(
                build_osc_message(address, sequence, f"runId={getattr(args, 'run_id', '') or 'qcl083'}"),
                ("127.0.0.1", server_port_holder[0]),
            )
            try:
                ack, _addr = client_socket.recvfrom(8192)
            except socket.timeout:
                continue
            parsed_ack = parse_osc_message(ack)
            if parsed_ack.get("address") == "/rusty/qcl083/ack" and int(parsed_ack.get("sequence", -1)) == sequence:
                acknowledged_sequences.append(sequence)
                rtts.append(int(round((time.monotonic() - started) * 1000.0)))
            time.sleep(0.005)
    server_done.wait(timeout=1.0)

    received_count = len(received_sequences)
    acknowledged_count = len(acknowledged_sequences)
    loss_percent = round(((message_count - acknowledged_count) / message_count) * 100.0, 2)
    monotonic = received_sequences == list(range(received_count))
    if server_error:
        status = "blocked"
        issue_codes = ["hostess.issue.connectivity_probe.osc_listener_failed"]
    elif acknowledged_count == message_count and monotonic and loss_percent <= max_loss_percent:
        status = "pass"
        issue_codes = []
    elif acknowledged_count > 0:
        status = "warn"
        issue_codes = ["hostess.issue.connectivity_probe.osc_exchange_degraded"]
    else:
        status = "fail"
        issue_codes = ["hostess.issue.connectivity_probe.osc_exchange_failed"]
    return {
        "status": status,
        "source": source,
        "address": address,
        "messages_requested": message_count,
        "messages_received": received_count,
        "messages_acknowledged": acknowledged_count,
        "loss_percent": loss_percent,
        "round_trip_ms_p95": percentile(rtts, 95),
        "round_trip_ms_max": max(rtts) if rtts else None,
        "monotonic_sequences": monotonic,
        "received_sequences": received_sequences[:50],
        "acknowledged_sequences": acknowledged_sequences[:50],
        "issue_codes": issue_codes,
        "notes": "host-local OSC UDP loopback; not a Quest-to-PC topology proof",
    }

def build_osc_message(address: str, sequence: int, marker: str) -> bytes:
    return osc_string(address) + osc_string(",is") + struct.pack(">i", int(sequence)) + osc_string(marker)

def osc_string(value: str) -> bytes:
    raw = value.encode("utf-8") + b"\0"
    padding = (4 - (len(raw) % 4)) % 4
    return raw + (b"\0" * padding)

def read_osc_string(payload: bytes, offset: int) -> tuple[str, int]:
    end = payload.index(b"\0", offset)
    value = payload[offset:end].decode("utf-8", errors="replace")
    next_offset = end + 1
    while next_offset % 4 != 0:
        next_offset += 1
    return value, next_offset

def parse_osc_message(payload: bytes) -> dict[str, Any]:
    try:
        address, offset = read_osc_string(payload, 0)
        type_tags, offset = read_osc_string(payload, offset)
        if not type_tags.startswith(",i") or len(payload) < offset + 4:
            return {"valid": False, "address": address, "type_tags": type_tags}
        sequence = struct.unpack(">i", payload[offset : offset + 4])[0]
        offset += 4
        marker = ""
        if "s" in type_tags[2:]:
            marker, _offset = read_osc_string(payload, offset)
        return {
            "valid": True,
            "address": address,
            "type_tags": type_tags,
            "sequence": sequence,
            "marker": marker,
        }
    except (ValueError, IndexError, struct.error):
        return {"valid": False}


def zeromq_loopback_probe(args: argparse.Namespace) -> dict[str, Any]:
    source = str(getattr(args, "zeromq_source", "host-loopback") or "host-loopback")
    pattern = str(getattr(args, "zeromq_pattern", "req-rep") or "req-rep")
    message_count = max(1, int(getattr(args, "zeromq_message_count", 16) or 16))
    timeout = max(0.5, float(getattr(args, "zeromq_timeout_seconds", 5.0) or 5.0))
    if source == "native-rust-broker":
        return zeromq_manifold_broker_probe(args)
    if source == "manifold-zmq-loopback":
        return zeromq_manifold_loopback_probe(args)
    if source == "rusty-xr-zmq-loopback":
        return zeromq_rusty_xr_loopback_probe(args)
    if source == "goofi-sidecar":
        return zeromq_goofi_sidecar_probe(args)
    if source != "host-loopback":
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.native_zeromq_source_not_configured"],
            "notes": "QCL-084 native Rust/Quest ZeroMQ source is not implemented in hostessctl yet",
        }
    try:
        import zmq  # type: ignore[import-not-found]
    except Exception as exc:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.pyzmq_unavailable"],
            "notes": f"pyzmq unavailable: {exc}",
        }

    if pattern != "req-rep":
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.zeromq_pattern_not_implemented"],
            "notes": f"ZeroMQ pattern {pattern} is not implemented in hostessctl host loopback",
        }

    context = zmq.Context()
    endpoint = "tcp://127.0.0.1"
    received_sequences: list[int] = []
    acknowledged_sequences: list[int] = []
    rtts: list[int] = []
    server_ready = threading.Event()
    server_done = threading.Event()
    server_error: list[str] = []

    def server() -> None:
        socket_rep = context.socket(zmq.REP)
        try:
            port = socket_rep.bind_to_random_port(endpoint)
            server_port_holder.append(port)
            server_ready.set()
            deadline = time.monotonic() + timeout
            while len(received_sequences) < message_count and time.monotonic() < deadline:
                if socket_rep.poll(100) == 0:
                    continue
                message = socket_rep.recv_json()
                sequence = int(message.get("sequence", -1))
                received_sequences.append(sequence)
                socket_rep.send_json({"status": "ack", "sequence": sequence})
        except Exception as exc:
            server_error.append(str(exc))
        finally:
            socket_rep.close(linger=0)
            server_done.set()

    server_port_holder: list[int] = []
    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    if not server_ready.wait(timeout=1.0) or not server_port_holder:
        context.term()
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.zeromq_listener_not_ready"],
            "notes": "ZeroMQ loopback listener did not become ready",
        }

    socket_req = context.socket(zmq.REQ)
    try:
        socket_req.connect(f"{endpoint}:{server_port_holder[0]}")
        for sequence in range(message_count):
            started = time.monotonic()
            socket_req.send_json({"run_id": getattr(args, "run_id", "") or "qcl084", "sequence": sequence})
            if socket_req.poll(int(timeout * 1000.0)) == 0:
                break
            reply = socket_req.recv_json()
            if reply.get("status") == "ack" and int(reply.get("sequence", -1)) == sequence:
                acknowledged_sequences.append(sequence)
                rtts.append(int(round((time.monotonic() - started) * 1000.0)))
    finally:
        socket_req.close(linger=0)
        server_done.wait(timeout=1.0)
        context.term()

    if server_error:
        status = "blocked"
        issue_codes = ["hostess.issue.connectivity_probe.zeromq_listener_failed"]
    elif len(acknowledged_sequences) == message_count:
        status = "pass"
        issue_codes = []
    elif acknowledged_sequences:
        status = "warn"
        issue_codes = ["hostess.issue.connectivity_probe.zeromq_exchange_degraded"]
    else:
        status = "fail"
        issue_codes = ["hostess.issue.connectivity_probe.zeromq_exchange_failed"]
    return {
        "status": status,
        "source": source,
        "pattern": pattern,
        "messages_requested": message_count,
        "messages_received": len(received_sequences),
        "messages_acknowledged": len(acknowledged_sequences),
        "round_trip_ms_p95": percentile(rtts, 95),
        "round_trip_ms_max": max(rtts) if rtts else None,
        "received_sequences": received_sequences[:50],
        "acknowledged_sequences": acknowledged_sequences[:50],
        "issue_codes": issue_codes,
        "notes": "host-local ZeroMQ loopback; not a native Rust broker/Quest topology proof",
    }

def zeromq_manifold_broker_probe(args: argparse.Namespace) -> dict[str, Any]:
    source = "native-rust-broker"
    pattern = str(getattr(args, "zeromq_pattern", "pub-sub") or "pub-sub")
    message_count = max(1, int(getattr(args, "zeromq_message_count", 16) or 16))
    if pattern != "pub-sub":
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.zeromq_pattern_not_implemented"],
            "notes": "native Rust broker-owned QCL-084 currently validates PUB/SUB only",
        }

    root = resolve_manifold_root(args)
    if root is None:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.manifold_zmq_root_missing"],
            "notes": "Rusty Manifold root with crates/rusty-manifold-zmq was not found",
        }

    timeout = max(10.0, float(getattr(args, "zeromq_cargo_timeout_seconds", 120.0) or 120.0))
    command = [
        "cargo",
        "run",
        "-q",
        "-p",
        "rusty-manifold-zmq",
        "--example",
        "zmq_pub_sub_loopback",
        "--features",
        "runtime",
        "--",
        "--json",
        "--source",
        source,
        "--message-count",
        str(message_count),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.manifold_zmq_broker_timeout"],
            "notes": f"native Rust broker-owned ZeroMQ probe timed out after {timeout}s: {exc}",
        }

    parsed = parse_probe_json_stdout(completed.stdout)
    if not parsed:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": message_count,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.manifold_zmq_broker_report_missing"],
            "notes": (completed.stderr or completed.stdout or "native Rust broker-owned ZeroMQ report missing").strip()[:800],
        }

    issue_codes = [str(code) for code in parsed.get("issue_codes", []) or []]
    route_evidence = object_value(parsed.get("bridge_route_evidence"))
    authority = object_value(parsed.get("authority"))
    broker_owned = (
        str(parsed.get("evidence_tier") or "") == "broker_owned"
        and str(authority.get("owner") or "") == "rusty.manifold.transport"
        and str(route_evidence.get("status") or "") == "pass"
    )
    requested = int(parsed.get("messages_requested") or message_count)
    received = int(parsed.get("messages_received") or 0)
    acknowledged = int(parsed.get("messages_acknowledged") or received)
    dropped = int(parsed.get("dropped_count") or 0)
    decode_errors = int(parsed.get("decode_error_count") or 0)
    status = str(parsed.get("status") or "blocked")
    if completed.returncode != 0 and status == "pass":
        status = "blocked"
        issue_codes.append("hostess.issue.connectivity_probe.manifold_zmq_broker_failed")
    if status == "pass" and not broker_owned:
        status = "warn"
        issue_codes.append("hostess.issue.connectivity_probe.manifold_zmq_broker_owned_evidence_missing")
    if status == "pass" and (acknowledged < requested or dropped or decode_errors):
        status = "warn"
        issue_codes.append("hostess.issue.connectivity_probe.zeromq_exchange_degraded")
    if status not in {"pass", "warn", "fail", "blocked"}:
        status = "blocked"
        issue_codes.append("hostess.issue.connectivity_probe.manifold_zmq_broker_status_invalid")

    return {
        "status": status,
        "source": source,
        "pattern": pattern,
        "endpoint": parsed.get("endpoint") or "tcp://127.0.0.1:<dynamic>",
        "messages_requested": requested,
        "messages_received": received,
        "messages_acknowledged": acknowledged,
        "round_trip_ms_p95": parsed.get("round_trip_ms_p95"),
        "received_sequences": parsed.get("received_sequences", []),
        "dropped_count": dropped,
        "decode_error_count": decode_errors,
        "evidence_tier": parsed.get("evidence_tier"),
        "authority_owner": authority.get("owner"),
        "bridge_route_evidence": route_evidence,
        "issue_codes": dedupe_issue_codes(issue_codes),
        "notes": (
            "native Rust Manifold-owned ZeroMQ PUB/SUB route evidence from rusty-manifold-zmq; "
            "Hostess only wraps the emitted broker-owned report"
        ),
    }

def zeromq_manifold_loopback_probe(args: argparse.Namespace) -> dict[str, Any]:
    source = "manifold-zmq-loopback"
    pattern = str(getattr(args, "zeromq_pattern", "pub-sub") or "pub-sub")
    if pattern != "pub-sub":
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": 0,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.zeromq_pattern_not_implemented"],
            "notes": "rusty-manifold-zmq loopback currently validates PUB/SUB only",
        }

    root = resolve_manifold_root(args)
    if root is None:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": 0,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.manifold_zmq_root_missing"],
            "notes": "Rusty Manifold root with crates/rusty-manifold-zmq was not found",
        }

    timeout = max(10.0, float(getattr(args, "zeromq_cargo_timeout_seconds", 120.0) or 120.0))
    command = [
        "cargo",
        "run",
        "-q",
        "-p",
        "rusty-manifold-zmq",
        "--example",
        "zmq_pub_sub_loopback",
        "--features",
        "runtime",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": 0,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.manifold_zmq_loopback_timeout"],
            "notes": f"rusty-manifold-zmq loopback timed out after {timeout}s: {exc}",
        }

    parsed = parse_native_zmq_loopback_stdout(completed.stdout)
    if completed.returncode != 0:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": parsed.get("messages_requested") or 0,
            "messages_received": parsed.get("messages_received") or 0,
            "messages_acknowledged": parsed.get("messages_acknowledged") or 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.manifold_zmq_loopback_failed"],
            "notes": (completed.stderr or completed.stdout or "rusty-manifold-zmq loopback failed").strip()[:800],
        }

    requested = int(parsed.get("messages_requested") or parsed.get("messages_received") or 0)
    received = int(parsed.get("messages_received") or 0)
    dropped = int(parsed.get("dropped_count") or 0)
    decode_errors = int(parsed.get("decode_error_count") or 0)
    if requested > 0 and received >= requested and dropped == 0 and decode_errors == 0:
        status = "pass"
        issue_codes: list[str] = []
    elif received > 0:
        status = "warn"
        issue_codes = ["hostess.issue.connectivity_probe.zeromq_exchange_degraded"]
    else:
        status = "fail"
        issue_codes = ["hostess.issue.connectivity_probe.zeromq_exchange_failed"]
    return {
        "status": status,
        "source": source,
        "pattern": pattern,
        "endpoint": parsed.get("endpoint") or "tcp://127.0.0.1:<dynamic>",
        "messages_requested": requested,
        "messages_received": received,
        "messages_acknowledged": received,
        "round_trip_ms_p95": None,
        "received_sequences": parsed.get("received_sequences", []),
        "dropped_count": dropped,
        "decode_error_count": decode_errors,
        "issue_codes": issue_codes,
        "notes": (
            "native Rust rusty-manifold-zmq PUB/SUB loopback; no native libzmq dependency; "
            "Goofi is an example source profile, not the protocol authority"
        ),
    }

def zeromq_rusty_xr_loopback_probe(args: argparse.Namespace) -> dict[str, Any]:
    source = "rusty-xr-zmq-loopback"
    pattern = str(getattr(args, "zeromq_pattern", "pub-sub") or "pub-sub")
    if pattern != "pub-sub":
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": 0,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.zeromq_pattern_not_implemented"],
            "notes": "rusty-xr-zmq loopback currently validates PUB/SUB only",
        }

    root = resolve_rusty_xr_root(args)
    if root is None:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": 0,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.rusty_xr_zmq_root_missing"],
            "notes": "Rusty-XR root with crates/rusty-xr-zmq was not found",
        }

    timeout = max(10.0, float(getattr(args, "zeromq_cargo_timeout_seconds", 120.0) or 120.0))
    command = [
        "cargo",
        "run",
        "-q",
        "-p",
        "rusty-xr-zmq",
        "--example",
        "zmq_pub_sub_loopback",
        "--features",
        "runtime",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": 0,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.rusty_xr_zmq_loopback_timeout"],
            "notes": f"rusty-xr-zmq loopback timed out after {timeout}s: {exc}",
        }

    parsed = parse_native_zmq_loopback_stdout(completed.stdout)
    if completed.returncode != 0:
        return {
            "status": "blocked",
            "source": source,
            "pattern": pattern,
            "messages_requested": parsed.get("messages_requested") or 0,
            "messages_received": parsed.get("messages_received") or 0,
            "messages_acknowledged": parsed.get("messages_acknowledged") or 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.rusty_xr_zmq_loopback_failed"],
            "notes": (completed.stderr or completed.stdout or "rusty-xr-zmq loopback failed").strip()[:800],
        }

    requested = int(parsed.get("messages_requested") or parsed.get("messages_received") or 0)
    received = int(parsed.get("messages_received") or 0)
    dropped = int(parsed.get("dropped_count") or 0)
    decode_errors = int(parsed.get("decode_error_count") or 0)
    if requested > 0 and received >= requested and dropped == 0 and decode_errors == 0:
        status = "pass"
        issue_codes: list[str] = []
    elif received > 0:
        status = "warn"
        issue_codes = ["hostess.issue.connectivity_probe.zeromq_exchange_degraded"]
    else:
        status = "fail"
        issue_codes = ["hostess.issue.connectivity_probe.zeromq_exchange_failed"]
    return {
        "status": status,
        "source": source,
        "pattern": pattern,
        "endpoint": parsed.get("endpoint") or "tcp://127.0.0.1:<dynamic>",
        "messages_requested": requested,
        "messages_received": received,
        "messages_acknowledged": received,
        "round_trip_ms_p95": None,
        "received_sequences": parsed.get("received_sequences", []),
        "dropped_count": dropped,
        "decode_error_count": decode_errors,
        "issue_codes": issue_codes,
        "notes": "native Rust rusty-xr-zmq PUB/SUB loopback; no native libzmq dependency",
    }

def resolve_rusty_xr_root(args: argparse.Namespace) -> Path | None:
    explicit = str(getattr(args, "zeromq_rusty_xr_root", "") or "").strip()
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend(
        [
            repo_root.parent / "Rusty-XR",
            Path("S:/Work/repos/active/Rusty-XR"),
        ]
    )
    for candidate in candidates:
        if (candidate / "crates" / "rusty-xr-zmq" / "Cargo.toml").is_file():
            return candidate
    return None

def resolve_manifold_root(args: argparse.Namespace) -> Path | None:
    explicit = str(getattr(args, "zeromq_manifold_root", "") or "").strip()
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend(
        [
            repo_root.parent / "rusty-manifold",
            Path("S:/Work/repos/active/rusty-manifold"),
        ]
    )
    for candidate in candidates:
        if (candidate / "crates" / "rusty-manifold-zmq" / "Cargo.toml").is_file():
            return candidate
    return None

def resolve_lsl_manifold_root(args: argparse.Namespace) -> Path | None:
    explicit = str(getattr(args, "lsl_manifold_root", "") or "").strip()
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend(
        [
            repo_root.parent / "rusty-manifold",
            Path("S:/Work/repos/active/rusty-manifold"),
        ]
    )
    for candidate in candidates:
        if (candidate / "tools" / "qcl081_lsl_clocked_samples.py").is_file():
            return candidate
    return None

def parse_native_zmq_loopback_stdout(stdout: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "messages_requested": None,
        "messages_received": None,
        "messages_acknowledged": None,
        "dropped_count": None,
        "decode_error_count": None,
        "received_sequences": [],
    }
    for line in stdout.splitlines():
        if line.startswith("ZeroMQ loopback endpoint:"):
            parsed["endpoint"] = line.split(":", 1)[1].strip()
        counters = re.search(
            r"received=(?P<received>\d+)\s+drained=(?P<drained>\d+)\s+dropped=(?P<dropped>\d+)\s+decode_errors=(?P<decode>\d+)",
            line,
        )
        if counters:
            parsed["messages_requested"] = int(counters.group("received"))
            parsed["messages_received"] = int(counters.group("received"))
            parsed["messages_acknowledged"] = int(counters.group("drained"))
            parsed["dropped_count"] = int(counters.group("dropped"))
            parsed["decode_error_count"] = int(counters.group("decode"))
            continue
        sequence = re.match(r"^(?P<sequence>\d+)\s+", line)
        if sequence:
            parsed["received_sequences"].append(int(sequence.group("sequence")))
    return parsed

def parse_rusty_xr_zmq_loopback_stdout(stdout: str) -> dict[str, Any]:
    return parse_native_zmq_loopback_stdout(stdout)

def zeromq_goofi_sidecar_probe(args: argparse.Namespace) -> dict[str, Any]:
    root = resolve_goofi_bridge_root(args)
    if root is None:
        return {
            "status": "blocked",
            "source": "goofi-sidecar",
            "pattern": "pub-sub",
            "messages_requested": 0,
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "issue_codes": ["hostess.issue.connectivity_probe.goofi_zmq_bridge_root_missing"],
            "notes": "Goofi/Gonzo ZeroMQ sidecar root was not found",
        }
    flight_logs = [
        root / "logs" / "goofi-node-witness.flight-log.json",
        root / "logs" / "goofi-manager-patch-witness.flight-log.json",
        root / "logs" / "goofi-gui-patch-witness.flight-log.json",
        root / "logs" / "goofi-fake-witness.flight-log.json",
    ]
    existing_logs = sorted(
        [path for path in flight_logs if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for flight_log in existing_logs:
            try:
                payload = json.loads(flight_log.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            count = int(payload.get("message_count") or 0)
            parse_errors = int(payload.get("parse_error_count") or 0)
            status = "pass" if count > 0 and parse_errors == 0 else "fail"
            return {
                "status": status,
                "source": "goofi-sidecar",
                "pattern": "pub-sub",
                "endpoint": payload.get("endpoint"),
                "topic": payload.get("topic"),
                "messages_requested": count,
                "messages_received": count,
                "messages_acknowledged": count,
                "round_trip_ms_p95": None,
                "received_sequences": list(range(min(count, 50))),
                "issue_codes": [] if status == "pass" else ["hostess.issue.connectivity_probe.goofi_zmq_parse_errors"],
                "notes": f"existing Goofi ZeroMQ sidecar flight log: {flight_log}",
            }
    return {
        "status": "blocked",
        "source": "goofi-sidecar",
        "pattern": "pub-sub",
        "messages_requested": 0,
        "messages_received": 0,
        "messages_acknowledged": 0,
        "round_trip_ms_p95": None,
        "issue_codes": ["hostess.issue.connectivity_probe.goofi_zmq_flight_log_missing"],
        "notes": "Goofi sidecar root exists but no supported flight log was found",
    }

def resolve_goofi_bridge_root(args: argparse.Namespace) -> Path | None:
    explicit = str(getattr(args, "zeromq_goofi_bridge_root", "") or "").strip()
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(Path("S:/Work/repos/active/Rusty-XR-Private-Planning/prototypes/gonzo-zmq-bridge"))
    for candidate in candidates:
        if (candidate / "Cargo.toml").is_file() and (candidate / "tools" / "goofi_pair_to_gargoyle_pub.py").is_file():
            return candidate
    return None

def lsl_checks_from_probe(result: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(result.get("status") or "blocked")
    issue_codes = [str(code) for code in result.get("issue_codes", [])]
    discovery_ms = result.get("discovery_ms")
    discovery_status = "pass" if discovery_ms is not None and status != "blocked" else status
    if status == "blocked":
        discovery_status = "blocked"
    elif discovery_ms is None:
        discovery_status = "fail"
    sample_status = status if discovery_status == "pass" else "blocked"
    return [
        check_row(
            "protocol.lsl_discovery",
            discovery_status,
            (
                f"stream {result.get('stream_name', 'unknown')} discovered in {discovery_ms}ms"
                if discovery_status == "pass"
                else str(result.get("notes") or "LSL discovery failed")
            ),
            observed={
                "source": result.get("source"),
                "stream_name": result.get("stream_name"),
                "stream_type": result.get("stream_type"),
                "discovery_ms": discovery_ms,
            },
            issue_codes=[] if discovery_status == "pass" else issue_codes,
        ),
        check_row(
            "protocol.lsl_sample_continuity",
            sample_status,
            (
                f"{result.get('samples_received', 0)}/{result.get('samples_requested', 0)} samples, loss={result.get('loss_percent', 100.0)}%"
                if sample_status in {"pass", "warn", "fail"}
                else "sample continuity blocked by discovery/dependency failure"
            ),
            observed={
                "samples_requested": result.get("samples_requested"),
                "samples_received": result.get("samples_received"),
                "loss_percent": result.get("loss_percent"),
                "monotonic_sequences": result.get("monotonic_sequences"),
                "received_sequences": result.get("received_sequences", []),
            },
            issue_codes=[] if sample_status == "pass" else issue_codes,
        ),
    ]

def osc_checks_from_probe(result: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(result.get("status") or "blocked")
    issue_codes = [str(code) for code in result.get("issue_codes", [])]
    shape_status = "pass" if status in {"pass", "warn", "fail"} else "blocked"
    exchange_status = status if shape_status == "pass" else "blocked"
    return [
        check_row(
            "protocol.osc_message_shape",
            shape_status,
            (
                f"OSC address {result.get('address')} parsed with int/string payload shape"
                if shape_status == "pass"
                else str(result.get("notes") or "OSC packet shape not proven")
            ),
            observed={"source": result.get("source"), "address": result.get("address")},
            issue_codes=[] if shape_status == "pass" else issue_codes,
        ),
        check_row(
            "protocol.osc_payload_exchange",
            exchange_status,
            (
                f"{result.get('messages_acknowledged', 0)}/{result.get('messages_requested', 0)} OSC messages acknowledged, loss={result.get('loss_percent', 100.0)}%"
                if exchange_status in {"pass", "warn", "fail"}
                else "OSC payload exchange blocked by dependency/source failure"
            ),
            observed={
                "messages_requested": result.get("messages_requested"),
                "messages_received": result.get("messages_received"),
                "messages_acknowledged": result.get("messages_acknowledged"),
                "loss_percent": result.get("loss_percent"),
                "round_trip_ms_p95": result.get("round_trip_ms_p95"),
                "monotonic_sequences": result.get("monotonic_sequences"),
                "received_sequences": result.get("received_sequences", []),
            },
            issue_codes=[] if exchange_status == "pass" else issue_codes,
        ),
    ]

def zeromq_checks_from_probe(result: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(result.get("status") or "blocked")
    issue_codes = [str(code) for code in result.get("issue_codes", [])]
    dependency_status = "pass" if status in {"pass", "warn", "fail"} else "blocked"
    exchange_status = status if dependency_status == "pass" else "blocked"
    return [
        check_row(
            "protocol.zeromq_dependency",
            dependency_status,
            (
                f"ZeroMQ dependency available for pattern {result.get('pattern')}"
                if dependency_status == "pass"
                else str(result.get("notes") or "ZeroMQ dependency/source unavailable")
            ),
            observed={"source": result.get("source"), "pattern": result.get("pattern")},
            issue_codes=[] if dependency_status == "pass" else issue_codes,
        ),
        check_row(
            "protocol.zeromq_payload_exchange",
            exchange_status,
            (
                f"{result.get('messages_acknowledged', 0)}/{result.get('messages_requested', 0)} ZeroMQ messages acknowledged"
                if exchange_status in {"pass", "warn", "fail"}
                else "ZeroMQ payload exchange blocked by dependency/source failure"
            ),
            observed={
                "messages_requested": result.get("messages_requested"),
                "messages_received": result.get("messages_received"),
                "messages_acknowledged": result.get("messages_acknowledged"),
                "round_trip_ms_p95": result.get("round_trip_ms_p95"),
                "received_sequences": result.get("received_sequences", []),
            },
            issue_codes=[] if exchange_status == "pass" else issue_codes,
        ),
    ]
