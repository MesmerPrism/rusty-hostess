"""Focused helpers split from connectivity_data_protocols.py."""

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
from tools.hostessctl.connectivity_data_protocols_common import parse_probe_json_stdout, protocol_topology_checks

DEFAULT_QCL083_OSC_PORT = 18783

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

def qcl083_remote_evidence_path(package_name: str) -> str:
    if package_name == ANDROID_PACKAGE:
        return ANDROID_REMOTE_QCL083_OSC_EVIDENCE
    return f"/sdcard/Android/data/{package_name}/files/hostess-t/evidence/qcl083-osc/latest.json"

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

