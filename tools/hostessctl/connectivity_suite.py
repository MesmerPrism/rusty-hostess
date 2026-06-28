"""Connectivity test-suite runner and aggregation for hostessctl."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import socket
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl import connectivity_probe
from tools.hostessctl import device_link_report
from tools.hostessctl.runtime import run_captured as default_run_captured


CONNECTIVITY_SUITE_RUN_SCHEMA = "rusty.quest.device_link.install_environment_suite_run.v1"
CONNECTIVITY_SUITE_RUN_VALIDATION_SCHEMA = (
    "rusty.quest.device_link.install_environment_suite_run.validation.v1"
)
VALID_SUITE_STATUSES = {"pass", "warn", "fail", "skipped"}


def run_connectivity_suite(
    args: argparse.Namespace,
    *,
    run_captured_func: Any | None = None,
    clock_func: Any | None = None,
) -> int:
    """Run selected suite slots and write an aggregate report plus validation sidecar."""

    run_captured = run_captured_func or default_run_captured
    clock = clock_func or utc_now
    report = build_connectivity_suite_run_report(
        args,
        run_captured_func=run_captured,
        clock_func=clock,
    )
    validation = validate_connectivity_suite_run_report(report)

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
    if getattr(args, "fail_on_error", False) and report["status"] == "fail":
        return 2
    return 0


def build_connectivity_suite_run_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    clock_func: Any,
) -> dict[str, Any]:
    observed_at = clock_func()
    suite_id = str(getattr(args, "suite_id", "") or "quest-device-link-install-suite")
    suite_run_id = str(getattr(args, "run_id", "") or f"{safe_token(suite_id)}-{run_stamp(observed_at)}")
    mode = str(getattr(args, "mode", "") or "fixture")
    out = Path(args.out)
    artifact_root = Path(
        str(getattr(args, "artifact_dir", "") or "")
        or out.with_name(f"{out.stem}-artifacts")
    )
    artifact_root.mkdir(parents=True, exist_ok=True)

    descriptor = device_link_report.build_install_test_suite_descriptor(
        suite_id=suite_id,
        observed_at_utc=observed_at,
    )
    suite_descriptor_path = Path(
        str(getattr(args, "suite_out", "") or "")
        or artifact_root / "device-link-test-suite.json"
    )
    suite_descriptor_path.parent.mkdir(parents=True, exist_ok=True)
    suite_descriptor_path.write_text(
        json.dumps(descriptor, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    selected_probe_ids = {
        str(value)
        for value in list_value(getattr(args, "probe_id", None))
        if str(value).strip()
    }
    selected_slots = [
        slot
        for slot in list_value(descriptor.get("test_slots"))
        if not selected_probe_ids or str(slot.get("probe_id") or "") in selected_probe_ids
    ]

    environment_snapshot = {}
    if not bool(getattr(args, "skip_host_snapshot", False)):
        environment_snapshot = collect_environment_snapshot(args, run_captured_func)

    slot_results: list[dict[str, Any]] = []
    for slot in selected_slots:
        slot_results.append(
            run_suite_slot(
                args,
                slot,
                suite_run_id=suite_run_id,
                mode=mode,
                artifact_root=artifact_root,
                run_captured_func=run_captured_func,
            )
        )

    grouped_results = group_slot_results(slot_results)
    status = suite_status(slot_results, environment_snapshot)
    return {
        "$schema": CONNECTIVITY_SUITE_RUN_SCHEMA,
        "schema_version": 1,
        "suite_run_id": suite_run_id,
        "suite_id": descriptor.get("suite_id"),
        "mode": mode,
        "observed_at_utc": observed_at,
        "status": status,
        "suite_descriptor_path": str(suite_descriptor_path),
        "suite_descriptor_validation": device_link_report.validate_install_test_suite_descriptor(
            descriptor
        ),
        "environment_snapshot": environment_snapshot,
        "selected_probe_ids": sorted(selected_probe_ids) if selected_probe_ids else ["all"],
        "slot_results": slot_results,
        "grouped_results": grouped_results,
        "artifacts": suite_artifacts(suite_descriptor_path, slot_results),
        "summary": suite_summary(status, slot_results, grouped_results),
    }


def run_suite_slot(
    args: argparse.Namespace,
    slot: dict[str, Any],
    *,
    suite_run_id: str,
    mode: str,
    artifact_root: Path,
    run_captured_func: Any,
) -> dict[str, Any]:
    probe_id = str(slot.get("probe_id") or "")
    fixture_profile = str(slot.get("fixture_profile") or "")
    slot_id = str(slot.get("slot_id") or f"slot.{probe_id.lower()}")
    slot_token = safe_token(f"{probe_id}-{fixture_profile or slot_id}")
    report_path = artifact_root / f"{slot_token}.json"
    validation_path = artifact_root / f"{slot_token}.validation-report.json"
    started = time.perf_counter()
    exit_code = 1
    runner_error = ""
    try:
        exit_code = connectivity_probe.run_connectivity_probe(
            probe_args_for_slot(
                args,
                slot,
                mode=mode,
                report_path=report_path,
                validation_path=validation_path,
                suite_run_id=suite_run_id,
            ),
            run_captured_func=run_captured_func,
        )
    except Exception as exc:  # keep suite aggregation inspectable
        runner_error = f"{type(exc).__name__}: {exc}"

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    report = read_json(report_path)
    validation = read_json(validation_path)
    descriptor_path = ""
    descriptor_validation_path = ""
    descriptor_status = ""
    if not runner_error and probe_id == "QCL-080" and report_path.exists():
        descriptor_path = str(report_path.with_suffix(".stream-capability.json"))
        descriptor_validation_path = str(
            Path(descriptor_path).with_name(
                f"{Path(descriptor_path).stem}.validation-report.json"
            )
        )
        stream_code = device_link_report.run_stream_capability_descriptor(
            argparse.Namespace(
                input=str(report_path),
                out=descriptor_path,
                validation_out=descriptor_validation_path,
                fail_on_error=False,
            )
        )
        if stream_code == 0:
            descriptor_status = str(read_json(Path(descriptor_path)).get("status") or "")
        else:
            descriptor_status = "fail"

    status = slot_status(exit_code, runner_error, report, validation)
    return {
        "slot_id": slot_id,
        "probe_id": probe_id,
        "fixture_profile": fixture_profile,
        "phase": str(slot.get("phase") or "protocol"),
        "purpose": str(slot.get("purpose") or ""),
        "mode": mode,
        "status": status,
        "runner_exit_code": exit_code,
        "runner_error": runner_error,
        "report_status": report.get("status"),
        "validation_status": validation.get("status"),
        "report_path": str(report_path),
        "validation_path": str(validation_path),
        "descriptor_path": descriptor_path,
        "descriptor_validation_path": descriptor_validation_path,
        "descriptor_status": descriptor_status,
        "elapsed_ms": elapsed_ms,
        "metrics": slot_metrics(report),
        "issues": slot_issues(report, validation, runner_error),
    }


def probe_args_for_slot(
    args: argparse.Namespace,
    slot: dict[str, Any],
    *,
    mode: str,
    report_path: Path,
    validation_path: Path,
    suite_run_id: str,
) -> argparse.Namespace:
    probe_id = str(slot.get("probe_id") or "QCL-010")
    fixture_profile = str(slot.get("fixture_profile") or "")
    return argparse.Namespace(
        connectivity_probe_command="run",
        out=str(report_path),
        validation_out=str(validation_path),
        probe_id=probe_id,
        run_id=f"{safe_token(suite_run_id)}-{safe_token(probe_id.lower())}",
        mode=mode,
        fixture_profile=fixture_profile if mode == "fixture" else None,
        adb=getattr(args, "adb", None),
        serial=getattr(args, "serial", None),
        wifi_interface=getattr(args, "wifi_interface", "wlan0"),
        host_ip=getattr(args, "host_ip", None),
        topology_owner=getattr(args, "topology_owner", ""),
        network_provider=getattr(args, "network_provider", ""),
        skip_host_ping=bool(getattr(args, "skip_host_ping", False)),
        skip_device_ping=bool(getattr(args, "skip_device_ping", False)),
        skip_tcp_echo=bool(getattr(args, "skip_tcp_echo", False)),
        tcp_echo_bind_host=getattr(args, "tcp_echo_bind_host", "0.0.0.0"),
        tcp_echo_port=int(getattr(args, "tcp_echo_port", 0) or 0),
        tcp_echo_marker=getattr(args, "tcp_echo_marker", "rusty-qcl-tcp-echo"),
        tcp_timeout_seconds=float(getattr(args, "tcp_timeout_seconds", 4.0) or 4.0),
        skip_udp_freshness=bool(getattr(args, "skip_udp_freshness", False)),
        udp_bind_host=getattr(args, "udp_bind_host", "0.0.0.0"),
        udp_port=int(getattr(args, "udp_port", 0) or 0),
        udp_marker=getattr(args, "udp_marker", "rusty-qcl-udp"),
        udp_packet_count=int(getattr(args, "udp_packet_count", 12) or 12),
        udp_interval_ms=float(getattr(args, "udp_interval_ms", 50.0) or 50.0),
        udp_timeout_seconds=float(getattr(args, "udp_timeout_seconds", 5.0) or 5.0),
        udp_max_loss_percent=float(getattr(args, "udp_max_loss_percent", 10.0) or 10.0),
        udp_max_jitter_ms=float(getattr(args, "udp_max_jitter_ms", 250.0) or 250.0),
        udp_listener_helper=getattr(args, "udp_listener_helper", ""),
        udp_sender_source=getattr(args, "udp_sender_source", "auto"),
        udp_sender_host_path=getattr(args, "udp_sender_host_path", None),
        udp_sender_device_path=getattr(
            args,
            "udp_sender_device_path",
            "/data/local/tmp/rusty-qcl080-udp-sender",
        ),
        makepad_package=getattr(args, "makepad_package", "io.github.mesmerprism.rustyhostess.makepad"),
        makepad_activity=getattr(
            args,
            "makepad_activity",
            "io.github.mesmerprism.rustyhostess.makepad/.MakepadAppXr",
        ),
        skip_makepad_force_stop=bool(getattr(args, "skip_makepad_force_stop", False)),
        makepad_launch_timeout_seconds=float(getattr(args, "makepad_launch_timeout_seconds", 10.0) or 10.0),
        lsl_source=getattr(args, "lsl_source", "host-loopback"),
        lsl_stream_name=getattr(args, "lsl_stream_name", "RustyQCL081"),
        lsl_stream_type=getattr(args, "lsl_stream_type", "Markers"),
        lsl_sample_count=int(getattr(args, "lsl_sample_count", 16) or 16),
        lsl_timeout_seconds=float(getattr(args, "lsl_timeout_seconds", 5.0) or 5.0),
        osc_source=getattr(args, "osc_source", "host-loopback"),
        osc_address=getattr(args, "osc_address", "/rusty/qcl083"),
        osc_port=int(getattr(args, "osc_port", 0) or 0),
        osc_message_count=int(getattr(args, "osc_message_count", 16) or 16),
        osc_timeout_seconds=float(getattr(args, "osc_timeout_seconds", 5.0) or 5.0),
        osc_max_loss_percent=float(getattr(args, "osc_max_loss_percent", 0.0) or 0.0),
        zeromq_source=getattr(args, "zeromq_source", "manifold-zmq-loopback"),
        zeromq_pattern=getattr(args, "zeromq_pattern", "pub-sub"),
        zeromq_message_count=int(getattr(args, "zeromq_message_count", 16) or 16),
        zeromq_timeout_seconds=float(getattr(args, "zeromq_timeout_seconds", 5.0) or 5.0),
        zeromq_port=int(getattr(args, "zeromq_port", 18784) or 18784),
        zeromq_android_binary_host_path=getattr(args, "zeromq_android_binary_host_path", ""),
        zeromq_android_binary_device_path=getattr(
            args,
            "zeromq_android_binary_device_path",
            "/data/local/tmp/rusty-qcl084-req-rep-probe",
        ),
        zeromq_manifold_root=getattr(args, "zeromq_manifold_root", ""),
        zeromq_rusty_xr_root=getattr(args, "zeromq_rusty_xr_root", ""),
        zeromq_goofi_bridge_root=getattr(args, "zeromq_goofi_bridge_root", ""),
        zeromq_cargo_timeout_seconds=float(getattr(args, "zeromq_cargo_timeout_seconds", 120.0) or 120.0),
        bluetooth_payload_source=getattr(args, "bluetooth_payload_source", "passive"),
        bluetooth_helper=getattr(args, "bluetooth_helper", ""),
        bluetooth_message_count=int(getattr(args, "bluetooth_message_count", 3) or 3),
        bluetooth_reconnect_count=int(getattr(args, "bluetooth_reconnect_count", 0) or 0),
        bluetooth_timeout_seconds=float(getattr(args, "bluetooth_timeout_seconds", 20.0) or 20.0),
        hostess_android_package=getattr(args, "hostess_android_package", "io.github.mesmerprism.rustyhostess.t"),
        ping_count=int(getattr(args, "ping_count", 2) or 2),
        ping_timeout_seconds=float(getattr(args, "ping_timeout_seconds", 2.0) or 2.0),
        fail_on_error=False,
    )


def collect_environment_snapshot(args: argparse.Namespace, run_captured_func: Any) -> dict[str, Any]:
    listener = {
        "program": str(getattr(args, "listener_program", "") or ""),
        "protocol": str(getattr(args, "listener_protocol", "") or "UDP"),
        "port": int(getattr(args, "listener_port", 0) or 0),
        "bind_host": str(getattr(args, "listener_bind_host", "") or "0.0.0.0"),
    }
    tools = {
        "python": sys.executable,
        "powershell": shutil.which("powershell") or shutil.which("powershell.exe") or "",
        "adb": str(getattr(args, "adb", "") or shutil.which("adb") or ""),
        "dotnet": shutil.which("dotnet") or "",
        "cargo": shutil.which("cargo") or "",
    }
    network_profile = connectivity_probe.collect_windows_network_profile(
        run_captured_func,
        listener=listener,
    )
    hotspot = connectivity_probe.collect_windows_mobile_hotspot(run_captured_func)
    bluetooth = connectivity_probe.collect_windows_bluetooth_status(run_captured_func)
    return {
        "host": {
            "os": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "hostname": socket.gethostname(),
            "python": sys.version.split()[0],
        },
        "tools": tools,
        "listener": listener,
        "network": {
            "ipv4_candidates": connectivity_probe.collect_host_ipv4_candidates(run_captured_func),
            "windows_profile": network_profile,
            "mobile_hotspot": hotspot,
        },
        "bluetooth": bluetooth,
        "device": {
            "adb_serial_provided": bool(str(getattr(args, "serial", "") or "").strip()),
            "serial_redacted": True,
        },
    }


def validate_connectivity_suite_run_report(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if report.get("$schema") != CONNECTIVITY_SUITE_RUN_SCHEMA:
        errors.append("unsupported connectivity suite run schema")
    if report.get("status") not in VALID_SUITE_STATUSES:
        errors.append("status must be pass, warn, fail, or skipped")
    if not str(report.get("suite_run_id") or "").strip():
        errors.append("suite_run_id must not be empty")
    slot_results = list_value(report.get("slot_results"))
    if not slot_results:
        errors.append("slot_results must not be empty")
    for row in slot_results:
        slot = object_value(row)
        if not str(slot.get("slot_id") or "").strip():
            errors.append("slot result requires slot_id")
        if slot.get("status") not in VALID_SUITE_STATUSES:
            errors.append(f"slot {slot.get('slot_id', '<unknown>')} has invalid status")
        if not str(slot.get("report_path") or "").strip():
            errors.append(f"slot {slot.get('slot_id', '<unknown>')} requires report_path")
        if slot.get("runner_error"):
            warnings.append(f"slot {slot.get('slot_id', '<unknown>')} runner error recorded")
    if not list_value(report.get("grouped_results")):
        errors.append("grouped_results must not be empty")
    descriptor_validation = object_value(report.get("suite_descriptor_validation"))
    if descriptor_validation.get("status") != "pass":
        errors.append("suite descriptor validation must pass")
    return {
        "$schema": CONNECTIVITY_SUITE_RUN_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "suite_run_id": report.get("suite_run_id"),
        "report_status": report.get("status"),
        "slot_count": len(slot_results),
        "errors": errors,
        "warnings": warnings,
    }


def group_slot_results(slot_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in slot_results:
        groups.setdefault(str(row.get("phase") or "protocol"), []).append(row)
    return [
        {
            "group_id": f"group.{safe_token(phase)}",
            "phase": phase,
            "status": suite_status(rows, {}),
            "slot_count": len(rows),
            "pass_count": sum(1 for row in rows if row.get("status") == "pass"),
            "warn_count": sum(1 for row in rows if row.get("status") == "warn"),
            "fail_count": sum(1 for row in rows if row.get("status") == "fail"),
            "slot_ids": [str(row.get("slot_id") or "") for row in rows],
        }
        for phase, rows in sorted(groups.items())
    ]


def suite_status(
    slot_results: list[dict[str, Any]],
    environment_snapshot: dict[str, Any],
) -> str:
    if not slot_results:
        return "skipped"
    statuses = {str(row.get("status") or "") for row in slot_results}
    if "fail" in statuses:
        return "fail"
    if statuses - {"pass"}:
        return "warn"
    network_profile = object_value(
        object_value(object_value(environment_snapshot).get("network")).get("windows_profile")
    )
    raw_connections = network_profile.get("connections")
    connections = (
        raw_connections
        if isinstance(raw_connections, list)
        else [raw_connections]
        if isinstance(raw_connections, dict)
        else []
    )
    active_categories = [
        str(row.get("NetworkCategory") or "")
        for row in connections
        if isinstance(row, dict)
    ]
    if "Public" in active_categories:
        return "warn"
    listener_firewall = object_value(network_profile.get("listener_firewall"))
    if listener_firewall and listener_firewall.get("allowed_on_active_profile") is not True:
        return "warn"
    return "pass"


def suite_summary(
    status: str,
    slot_results: list[dict[str, Any]],
    grouped_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": status,
        "slot_count": len(slot_results),
        "group_count": len(grouped_results),
        "pass_count": sum(1 for row in slot_results if row.get("status") == "pass"),
        "warn_count": sum(1 for row in slot_results if row.get("status") == "warn"),
        "fail_count": sum(1 for row in slot_results if row.get("status") == "fail"),
    }


def suite_artifacts(descriptor_path: Path, slot_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    artifacts = [
        {
            "role": "suite_descriptor",
            "schema": device_link_report.QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_SCHEMA,
            "path": str(descriptor_path),
        }
    ]
    for row in slot_results:
        artifacts.append(
            {
                "role": "connectivity_probe_report",
                "probe_id": row.get("probe_id"),
                "path": row.get("report_path"),
            }
        )
        if row.get("descriptor_path"):
            artifacts.append(
                {
                    "role": "stream_capability_descriptor",
                    "probe_id": row.get("probe_id"),
                    "path": row.get("descriptor_path"),
                }
            )
    return artifacts


def slot_status(
    exit_code: int,
    runner_error: str,
    report: dict[str, Any],
    validation: dict[str, Any],
) -> str:
    if runner_error or exit_code != 0 or validation.get("status") == "fail":
        return "fail"
    report_status = str(report.get("status") or "")
    if report_status == "pass":
        return "pass"
    if report_status in {"warn", "blocked", "planned", "skipped"}:
        return "warn"
    if report_status == "fail":
        return "fail"
    return "warn"


def slot_metrics(report: dict[str, Any]) -> dict[str, Any]:
    measurements = object_value(report.get("measurements"))
    metrics = {
        key: value
        for key, value in measurements.items()
        if value is not None and key != "throughput_mbps"
    }
    command_stages = object_value(report.get("command_stages"))
    if command_stages:
        metrics["command_stages"] = command_stages
    return metrics


def slot_issues(
    report: dict[str, Any],
    validation: dict[str, Any],
    runner_error: str,
) -> list[dict[str, Any]]:
    rows = [row for row in list_value(report.get("issues")) if isinstance(row, dict)]
    for error in list_value(validation.get("errors")):
        rows.append(
            {
                "issue_code": "hostess.issue.connectivity_suite.validation_error",
                "severity": "error",
                "message": str(error),
            }
        )
    if runner_error:
        rows.append(
            {
                "issue_code": "hostess.issue.connectivity_suite.runner_error",
                "severity": "error",
                "message": runner_error,
            }
        )
    return rows


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def safe_token(value: Any) -> str:
    text = str(value or "suite")
    chars = [char if char.isalnum() or char in {".", "_", "-"} else "-" for char in text]
    token = "".join(chars).strip("._-")
    while "--" in token:
        token = token.replace("--", "-")
    return token or "suite"


def run_stamp(observed_at_utc: str) -> str:
    return safe_token(observed_at_utc.replace(":", "").replace("Z", ""))


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = [
    "CONNECTIVITY_SUITE_RUN_SCHEMA",
    "CONNECTIVITY_SUITE_RUN_VALIDATION_SCHEMA",
    "build_connectivity_suite_run_report",
    "run_connectivity_suite",
    "validate_connectivity_suite_run_report",
]
