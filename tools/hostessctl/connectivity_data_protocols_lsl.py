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
from tools.hostessctl.connectivity_data_protocols_common import protocol_topology_checks

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

    lsl_route_evidence = object_value(lsl_result.get("bridge_route_evidence"))
    lsl_runtime_topology = object_value(lsl_result.get("topology"))
    lsl_runtime_wifi_direct = (
        source == "quest-runtime"
        and str(lsl_runtime_topology.get("network_provider") or "") == "wifi_direct"
    )
    lsl_broker_owned = (
        source == "manifold-lsl-broker"
        and str(lsl_result.get("evidence_tier") or "") == "broker_owned"
        and str(lsl_result.get("authority_owner") or "") == "rusty.manifold.transport"
        and str(lsl_route_evidence.get("status") or "") == "pass"
    )
    effective_device_ip = device.get("wifi_ipv4")
    if lsl_runtime_wifi_direct and not effective_device_ip:
        effective_device_ip = str(
            lsl_result.get("device_endpoint")
            or lsl_runtime_topology.get("remote_endpoint")
            or ""
        ).strip()

    status = live_qcl081_status(checks, source=source, device_ip=effective_device_ip)
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

    promotion_allowed = status == "pass" and (
        source == "quest-runtime" or lsl_broker_owned
    )

    report = base_report(args, observed_at=observed_at)
    report.update(
        {
            "status": status,
            "classification": "protocol_fit_candidate",
            "topology": {
                "owner": (
                    str(lsl_runtime_topology.get("owner") or "wifi_direct")
                    if lsl_runtime_wifi_direct
                    else "external_wifi" if device.get("wifi_ipv4") else "host_local"
                ),
                "network_provider": (
                    "wifi_direct"
                    if lsl_runtime_wifi_direct
                    else "router_or_existing_wifi" if device.get("wifi_ipv4") else "loopback"
                ),
                "endpoint_direction": str(
                    lsl_runtime_topology.get("endpoint_direction")
                    or "lsl_multicast_discovery_plus_tcp_samples"
                ),
                "requires_existing_wifi": False if lsl_runtime_wifi_direct else bool(device.get("wifi_ipv4")),
                "requires_adb": bool(getattr(args, "adb", None) and getattr(args, "serial", None)),
                "requires_pairing": False,
                "requires_termux": False,
                "experimental": source != "host-loopback",
            },
            "transport": {
                "family": "lsl",
                "route": "qcl081_lsl_discovery_sample_continuity",
                "local_endpoint": str(
                    lsl_result.get("host_endpoint")
                    or lsl_runtime_topology.get("local_endpoint")
                    or host_ip
                    or "host-loopback"
                ),
                "remote_endpoint": str(
                    lsl_result.get("device_endpoint")
                    or lsl_runtime_topology.get("remote_endpoint")
                    or lsl_result.get("source_id")
                    or device.get("wifi_ipv4")
                    or source
                ),
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
    report_path = str(getattr(args, "lsl_quest_runtime_report", "") or "").strip()
    if report_path:
        return lsl_quest_runtime_report_from_file(
            Path(report_path),
            stream_name=stream_name,
            stream_type=stream_type,
            sample_count=sample_count,
        )
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

def lsl_quest_runtime_report_from_file(
    report_path: Path,
    *,
    stream_name: str,
    stream_type: str,
    sample_count: int,
) -> dict[str, Any]:
    if not report_path.is_file():
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
            "issue_codes": ["hostess.issue.connectivity_probe.lsl_quest_runtime_report_missing"],
            "notes": f"QCL-081 Quest-runtime receiver report not found: {report_path}",
        }
    try:
        parsed = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
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
            "issue_codes": ["hostess.issue.connectivity_probe.lsl_quest_runtime_report_invalid_json"],
            "notes": f"QCL-081 Quest-runtime receiver report is not valid JSON: {exc}",
        }
    if not isinstance(parsed, dict):
        parsed = {}

    status = str(parsed.get("status") or "blocked")
    issue_codes = [str(code) for code in parsed.get("issue_codes", []) or []]
    if str(parsed.get("source") or "") != "quest-runtime":
        issue_codes.append("hostess.issue.connectivity_probe.lsl_quest_runtime_report_wrong_source")
        if status == "pass":
            status = "blocked"
    if str(object_value(parsed.get("topology")).get("network_provider") or "") != "wifi_direct":
        issue_codes.append("hostess.issue.connectivity_probe.lsl_quest_runtime_not_wifi_direct")
        if status == "pass":
            status = "warn"

    samples_requested = int_value(parsed.get("samples_requested"))
    samples_received = int_value(parsed.get("samples_received"))
    result = dict(parsed)
    result.update(
        {
            "status": status,
            "source": "quest-runtime",
            "stream_name": str(parsed.get("stream_name") or stream_name),
            "stream_type": str(parsed.get("stream_type") or stream_type),
            "samples_requested": samples_requested if samples_requested is not None else sample_count,
            "samples_received": samples_received if samples_received is not None else 0,
            "loss_percent": float_value(parsed.get("loss_percent"), default=100.0),
            "discovery_ms": int_value(parsed.get("discovery_ms")),
            "monotonic_sequences": bool(parsed.get("monotonic_sequences")),
            "received_sequences": parsed.get("received_sequences", []),
            "issue_codes": dedupe_issue_codes(issue_codes),
            "notes": str(parsed.get("notes") or "Quest-runtime QCL-081 LSL receiver report was ingested."),
            "receiver_report_path": str(report_path),
        }
    )
    return result

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

