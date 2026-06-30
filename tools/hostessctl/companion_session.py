"""Companion session orchestration report helpers for hostessctl."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl import bridge_command_android_routes
from tools.hostessctl import bridge_command_live_android_routes
from tools.hostessctl import companion_catalog
from tools.hostessctl import companion_readiness
from tools.hostessctl import device_link_report
from tools.hostessctl.bridge_command_routes import DEFAULT_RUNTIME_RECEIPT_STREAM
from tools.hostessctl.bridge_route_evidence import validate_bridge_route_evidence
from tools.hostessctl.broker_transport import BrokerWebSocketClient, MANIFOLD_BROKER_EVENTS_PATH
from tools.hostessctl.companion_session_defaults import (
    DEFAULT_COMPANION_SESSION_AUTHORITY_WAIT_SECONDS,
    DEFAULT_COMPANION_SESSION_LAUNCH_SETTLE_SECONDS,
    DEFAULT_COMPANION_SESSION_PROCESS_WAIT_SECONDS,
    DEFAULT_COMPANION_SESSION_RUNTIME_SUBSCRIBER_RETRY_COUNT,
    DEFAULT_COMPANION_SESSION_RUNTIME_SUBSCRIBER_RETRY_WAIT_SECONDS,
    DEFAULT_COMPANION_SESSION_SOCKET_WAIT_SECONDS,
    DEFAULT_COMPANION_SESSION_WAIT_SECONDS,
)
from tools.hostessctl.platform_defaults import (
    BROKER_LOCAL_FORWARD_PORT,
    BROKER_PORT,
    MAKEPAD_ANDROID_PACKAGE,
    MAKEPAD_ANDROID_XR_ACTIVITY,
    selected_broker_activity,
    selected_broker_package,
)
from tools.hostessctl.runtime import run_captured as default_run_captured


HOSTESS_COMPANION_SESSION_SCHEMA = "rusty.hostess.companion.session.v1"
HOSTESS_COMPANION_SESSION_VALIDATION_SCHEMA = (
    "rusty.hostess.companion.session_validation.v1"
)
HOSTESS_COMPANION_SESSION_HISTORY_SCHEMA = "rusty.hostess.companion.session_history.v1"
VALID_SESSION_STATUSES = {"pass", "warn", "fail", "skipped"}
SESSION_PHASE_IDS = (
    "preflight",
    "device",
    "broker",
    "runtime",
    "broker_stream_probe",
    "app_private_fallback",
    "evidence",
)


def run_companion_session(
    args: argparse.Namespace,
    *,
    run_captured_func: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    clock_ms_func: Callable[[], int] | None = None,
    which_func: Callable[[str], str | None] | None = None,
    broker_probe_func: Callable[[str, int, float], bool] | None = None,
    broker_client_factory: Any | None = None,
    socket_probe_func: Callable[[str, int, float], bool] | None = None,
    sleep_func: Callable[[float], None] | None = None,
    live_execution_func: Callable[..., dict[str, Any]] | None = None,
    fallback_execution_func: Callable[..., dict[str, Any]] | None = None,
) -> int:
    """Write a companion session report and validation sidecar."""

    report = build_companion_session_report(
        args,
        run_captured_func=run_captured_func or default_run_captured,
        clock_ms_func=clock_ms_func or epoch_ms,
        which_func=which_func or shutil.which,
        broker_probe_func=broker_probe_func or companion_readiness.broker_port_open,
        broker_client_factory=broker_client_factory or BrokerWebSocketClient,
        socket_probe_func=socket_probe_func or bridge_command_live_android_routes.broker_port_open,
        sleep_func=sleep_func or time.sleep,
        live_execution_func=live_execution_func,
        fallback_execution_func=fallback_execution_func,
    )
    validation = validate_companion_session_report(report)
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


def run_companion_session_history(
    args: argparse.Namespace,
    *,
    clock_ms_func: Callable[[], int] | None = None,
) -> int:
    """Write a compact index of saved companion session reports."""

    report = build_companion_session_history_report(
        args,
        clock_ms_func=clock_ms_func or epoch_ms,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def build_companion_session_history_report(
    args: argparse.Namespace,
    *,
    clock_ms_func: Callable[[], int],
) -> dict[str, Any]:
    session_dir = Path(
        getattr(args, "session_dir", None)
        or repo_root() / "target" / "companion-session"
    )
    limit = max(0, int(getattr(args, "limit", 25) or 25))
    reports: list[dict[str, Any]] = []
    if session_dir.exists():
        candidates = sorted(
            session_dir.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in candidates:
            summary = companion_session_history_row(path)
            if summary is None:
                continue
            reports.append(summary)
            if limit and len(reports) >= limit:
                break

    return {
        "$schema": HOSTESS_COMPANION_SESSION_HISTORY_SCHEMA,
        "status": "pass",
        "observed_at_ms": int(clock_ms_func()),
        "session_dir": str(session_dir),
        "limit": limit,
        "count": len(reports),
        "sessions": reports,
    }


def companion_session_history_row(path: Path) -> dict[str, Any] | None:
    try:
        report = load_json_object(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if report.get("$schema") != HOSTESS_COMPANION_SESSION_SCHEMA:
        return None
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    try:
        return {
            "session_id": str(report.get("session_id") or path.stem),
            "status": str(report.get("status") or "unknown"),
            "frontend": str(report.get("frontend") or ""),
            "profile": str(report.get("profile") or ""),
            "started_at_ms": int(report.get("started_at_ms") or 0),
            "ended_at_ms": int(report.get("ended_at_ms") or 0),
            "phase_count": int(summary.get("phase_count") or 0),
            "artifact_count": int(summary.get("artifact_count") or 0),
            "issue_count": int(summary.get("issue_count") or 0),
            "report_path": str(path),
            "last_write_time_ms": int(path.stat().st_mtime * 1000),
        }
    except (OSError, TypeError, ValueError):
        return None


def build_companion_session_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Callable[..., subprocess.CompletedProcess[str]],
    clock_ms_func: Callable[[], int],
    which_func: Callable[[str], str | None],
    broker_probe_func: Callable[[str, int, float], bool],
    broker_client_factory: Any,
    socket_probe_func: Callable[[str, int, float], bool],
    sleep_func: Callable[[float], None],
    live_execution_func: Callable[..., dict[str, Any]] | None = None,
    fallback_execution_func: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    started_at_ms = int(clock_ms_func())
    request_token = session_request_token(args, out, started_at_ms)
    artifact_refs: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    readiness_report, readiness_validation = run_readiness_slice(
        args,
        out,
        run_captured_func=run_captured_func,
        clock_ms_func=clock_ms_func,
        which_func=which_func,
        broker_probe_func=broker_probe_func,
        artifact_refs=artifact_refs,
    )
    catalog_report, catalog_validation = run_catalog_slice(
        args,
        out,
        clock_ms_func=clock_ms_func,
        artifact_refs=artifact_refs,
    )

    live_execution: dict[str, Any] | None = None
    live_validation: dict[str, Any] | None = None
    fallback_execution: dict[str, Any] | None = None
    fallback_validation: dict[str, Any] | None = None
    skip_probe = bool(getattr(args, "skip_probe", False))

    if skip_probe:
        issues.append(
            session_issue(
                "hostess.issue.companion_session.probe_skipped",
                "warning",
                "runtime command probe was skipped by request",
            )
        )
    else:
        try:
            live_execution, live_validation = run_live_probe_slice(
                args,
                out,
                broker_client_factory=broker_client_factory,
                clock_ms_func=clock_ms_func,
                socket_probe_func=socket_probe_func,
                sleep_func=sleep_func,
                live_execution_func=live_execution_func,
                artifact_refs=artifact_refs,
                request_token=request_token,
            )
        except Exception as exc:
            live_execution = exception_execution(
                "rusty.hostess.bridge_command.live_android_execution_evidence.v1",
                "bridge_route.command.websocket.applied",
                "hostess.makepad.bridge_probe.set_marker",
                "hostess.issue.companion_session.live_probe_exception",
                str(exc),
                int(clock_ms_func()),
            )
            live_validation = {"status": "fail", "errors": [str(exc)]}
            issues.append(
                session_issue(
                    "hostess.issue.companion_session.live_probe_exception",
                    "error",
                    str(exc),
                )
            )

    live_failed = live_execution is not None and live_execution.get("status") != "pass"
    fallback_enabled = not bool(getattr(args, "no_fallback", False))
    if live_failed and fallback_enabled:
        try:
            fallback_execution, fallback_validation = run_fallback_probe_slice(
                args,
                out,
                clock_ms_func=clock_ms_func,
                fallback_execution_func=fallback_execution_func,
                artifact_refs=artifact_refs,
                request_token=request_token,
            )
        except Exception as exc:
            fallback_execution = exception_execution(
                "rusty.hostess.bridge_command.android_execution_evidence.v1",
                "bridge_route.command.android_app_private.applied",
                "hostess.makepad.bridge_probe.set_marker",
                "hostess.issue.companion_session.fallback_probe_exception",
                str(exc),
                int(clock_ms_func()),
            )
            fallback_validation = {"status": "fail", "errors": [str(exc)]}
            issues.append(
                session_issue(
                    "hostess.issue.companion_session.fallback_probe_exception",
                    "error",
                    str(exc),
                )
            )
    elif live_failed and not fallback_enabled:
        issues.append(
            session_issue(
                "hostess.issue.companion_session.fallback_disabled",
                "error",
                "broker-stream probe failed and app-private fallback was disabled",
            )
        )

    recovered_by_fallback = bool(
        live_failed and fallback_execution is not None and fallback_execution.get("status") == "pass"
    )
    if recovered_by_fallback:
        issues.append(
            session_issue(
                "hostess.issue.companion_session.recovered_by_app_private_fallback",
                "warning",
                "broker-stream probe did not pass; app-private command fallback passed",
            )
        )

    _, device_link_validation = run_device_link_slice(
        args,
        out,
        readiness_report=readiness_report,
        live_execution=live_execution,
        fallback_execution=fallback_execution,
        observed_at_ms=int(clock_ms_func()),
        artifact_refs=artifact_refs,
    )

    phases = [
        readiness_phase("preflight", "Host preflight", readiness_report, {"host", "toolchain", "module_descriptor"}),
        readiness_phase("device", "Quest device", readiness_report, {"device", "runtime"}),
        readiness_phase("broker", "Broker transport", readiness_report, {"network"}),
        runtime_phase(live_execution, recovered_by_fallback=recovered_by_fallback, skipped=skip_probe),
        broker_stream_probe_phase(live_execution, recovered_by_fallback=recovered_by_fallback, skipped=skip_probe),
        fallback_phase(
            fallback_execution,
            live_failed=live_failed,
            fallback_enabled=fallback_enabled,
            skipped=skip_probe,
        ),
        evidence_phase(
            artifact_refs,
            readiness_validation,
            catalog_validation,
            device_link_validation,
            live_validation,
            fallback_validation,
            recovered_by_fallback=recovered_by_fallback,
        ),
    ]
    for phase in phases:
        issues.extend(phase.get("issues", []))

    ended_at_ms = max(started_at_ms, int(clock_ms_func()))
    status = session_status(phases)
    return {
        "$schema": HOSTESS_COMPANION_SESSION_SCHEMA,
        "status": status,
        "started_at_ms": started_at_ms,
        "ended_at_ms": ended_at_ms,
        "session_id": str(getattr(args, "session_id", None) or f"hostess-session-{started_at_ms}"),
        "frontend": str(getattr(args, "frontend", None) or "cli"),
        "profile": str(getattr(args, "profile", None) or "hostess-makepad-quest"),
        "scope": session_scope(args),
        "summary": {
            "phase_count": len(phases),
            "pass": sum(1 for phase in phases if phase.get("status") == "pass"),
            "warn": sum(1 for phase in phases if phase.get("status") == "warn"),
            "fail": sum(1 for phase in phases if phase.get("status") == "fail"),
            "skipped": sum(1 for phase in phases if phase.get("status") == "skipped"),
            "artifact_count": len(artifact_refs),
            "issue_count": len(issues),
        },
        "phases": phases,
        "artifact_refs": artifact_refs,
        "issues": issues,
    }


def run_readiness_slice(
    args: argparse.Namespace,
    out: Path,
    *,
    run_captured_func: Callable[..., subprocess.CompletedProcess[str]],
    clock_ms_func: Callable[[], int],
    which_func: Callable[[str], str | None],
    broker_probe_func: Callable[[str, int, float], bool],
    artifact_refs: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    readiness_out = out.with_name(f"{out.stem}.readiness.json")
    readiness_args = argparse.Namespace(
        command="companion-readiness",
        out=str(readiness_out),
        validation_out=None,
        profile=str(getattr(args, "profile", None) or "hostess-makepad-quest"),
        descriptor=getattr(args, "descriptor", None),
        adb=getattr(args, "adb", None),
        serial=getattr(args, "serial", None),
        android_sdk=getattr(args, "android_sdk", None),
        jdk_home=getattr(args, "jdk_home", None),
        cargo=getattr(args, "cargo", "cargo"),
        cargo_makepad=getattr(args, "cargo_makepad", "cargo-makepad"),
        broker_host=getattr(args, "broker_host", "127.0.0.1"),
        broker_port=getattr(args, "broker_port", BROKER_PORT),
        broker_local_port=getattr(args, "broker_local_port", BROKER_LOCAL_FORWARD_PORT),
        broker_package=getattr(args, "broker_package", None),
        broker_activity=getattr(args, "broker_activity", None),
        check_broker=bool(getattr(args, "check_broker", False)),
        require_broker=bool(getattr(args, "require_broker", False)),
        makepad_package=getattr(args, "makepad_package", MAKEPAD_ANDROID_PACKAGE),
        makepad_activity=getattr(args, "makepad_activity", MAKEPAD_ANDROID_XR_ACTIVITY),
        require_adb=False,
        require_android_sdk=False,
        require_jdk=False,
        require_cargo_makepad=False,
        require_device=False,
        require_makepad_package=False,
        fail_on_blocking=False,
    )
    report = companion_readiness.build_companion_readiness_report(
        readiness_args,
        run_captured_func=run_captured_func,
        clock_ms_func=clock_ms_func,
        which_func=which_func,
        broker_probe_func=broker_probe_func,
    )
    validation = companion_readiness.validate_companion_readiness_report(report)
    write_json(readiness_out, report)
    validation_out = readiness_out.with_name(f"{readiness_out.stem}.validation-report.json")
    write_json(validation_out, validation)
    artifact_refs.extend(
        [
            artifact_ref(
                "artifact.hostess.companion_session.readiness_report",
                readiness_out,
                report.get("$schema"),
                role="readiness_report",
                validation_status=validation.get("status"),
            ),
            artifact_ref(
                "artifact.hostess.companion_session.readiness_validation",
                validation_out,
                validation.get("$schema"),
                role="readiness_validation",
                validation_status=validation.get("status"),
            ),
        ]
    )
    return report, validation


def run_catalog_slice(
    args: argparse.Namespace,
    out: Path,
    *,
    clock_ms_func: Callable[[], int],
    artifact_refs: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    catalog_out = out.with_name(f"{out.stem}.catalog.json")
    catalog_args = argparse.Namespace(
        command="companion-catalog",
        out=str(catalog_out),
        validation_out=None,
        frontend=str(getattr(args, "frontend", None) or "cli"),
        hostess_descriptor=getattr(args, "hostess_descriptor", None),
        gui_descriptors_root=getattr(args, "gui_descriptors_root", None),
        fail_on_error=False,
    )
    report = companion_catalog.build_companion_catalog_report(
        catalog_args,
        clock_ms_func=clock_ms_func,
    )
    validation = companion_catalog.validate_companion_catalog_report(report)
    write_json(catalog_out, report)
    validation_out = catalog_out.with_name(f"{catalog_out.stem}.validation-report.json")
    write_json(validation_out, validation)
    artifact_refs.extend(
        [
            artifact_ref(
                "artifact.hostess.companion_session.catalog_report",
                catalog_out,
                report.get("$schema"),
                role="catalog_report",
                validation_status=validation.get("status"),
            ),
            artifact_ref(
                "artifact.hostess.companion_session.catalog_validation",
                validation_out,
                validation.get("$schema"),
                role="catalog_validation",
                validation_status=validation.get("status"),
            ),
        ]
    )
    return report, validation


def run_device_link_slice(
    args: argparse.Namespace,
    out: Path,
    *,
    readiness_report: dict[str, Any],
    live_execution: dict[str, Any] | None,
    fallback_execution: dict[str, Any] | None,
    observed_at_ms: int,
    artifact_refs: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    device_link_out = out.with_name(f"{out.stem}.device-link.json")
    report = device_link_report.build_device_link_report(
        args,
        readiness_report=readiness_report,
        live_execution=live_execution,
        fallback_execution=fallback_execution,
        observed_at_ms=observed_at_ms,
    )
    validation = device_link_report.validate_device_link_report(report)
    write_json(device_link_out, report)
    validation_out = device_link_out.with_name(f"{device_link_out.stem}.validation-report.json")
    write_json(validation_out, validation)
    artifact_refs.extend(
        [
            artifact_ref(
                "artifact.hostess.companion_session.device_link_report",
                device_link_out,
                report.get("schema"),
                role="device_link_report",
                validation_status=validation.get("status"),
            ),
            artifact_ref(
                "artifact.hostess.companion_session.device_link_validation",
                validation_out,
                validation.get("$schema"),
                role="device_link_validation",
                validation_status=validation.get("status"),
            ),
        ]
    )
    return report, validation


def run_live_probe_slice(
    args: argparse.Namespace,
    out: Path,
    *,
    broker_client_factory: Any,
    clock_ms_func: Callable[[], int],
    socket_probe_func: Callable[[str, int, float], bool],
    sleep_func: Callable[[float], None],
    live_execution_func: Callable[..., dict[str, Any]] | None,
    artifact_refs: list[dict[str, Any]],
    request_token: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence_out = out.with_name(f"{out.stem}.live-broker-stream-evidence.json")
    execution_out = evidence_out.with_name(f"{evidence_out.stem}.live-android-execution.json")
    validation_out = evidence_out.with_name(f"{evidence_out.stem}.validation-report.json")
    logcat_out = evidence_out.with_name(f"{evidence_out.stem}.logcat.txt")
    request_out = out.with_name(f"{out.stem}.live-broker-stream-request.json")
    request_path = materialize_session_request(
        Path(str(getattr(args, "probe_input", None) or default_probe_input())),
        request_out,
        request_token=request_token,
        role="broker_stream_probe",
    )
    request = bridge_command_live_android_routes.load_bridge_command_request(
        request_path,
    )
    live_args = live_android_args(args, evidence_out, execution_out, validation_out, logcat_out)
    live_args.input = str(request_path)
    if live_execution_func is not None:
        execution = live_execution_func(request, args=live_args)
    else:
        execution = bridge_command_live_android_routes.execute_bridge_command_live_android_request(
            request,
            args=live_args,
            run_captured_func=default_run_captured,
            broker_client_factory=broker_client_factory,
            clock_ms_func=clock_ms_func,
            socket_probe_func=socket_probe_func,
            sleep_func=sleep_func,
        )
    bridge_evidence = execution["bridge_route_evidence"]
    validation = validate_bridge_route_evidence(
        bridge_evidence,
        required_stages=execution.get("required_evidence_stages"),
        route_descriptor=None,
    )
    execution["bridge_route_validation"] = validation
    write_json(evidence_out, bridge_evidence)
    write_json(execution_out, execution)
    write_json(validation_out, validation)
    artifact_refs.extend(
        [
            artifact_ref(
                "artifact.hostess.companion_session.live_broker_stream_request",
                request_path,
                request.get("$schema"),
                role="live_broker_stream_request",
                validation_status="generated",
            ),
            artifact_ref(
                "artifact.hostess.companion_session.live_broker_stream_evidence",
                evidence_out,
                bridge_evidence.get("$schema"),
                role="live_broker_stream_evidence",
                validation_status=validation.get("status"),
            ),
            artifact_ref(
                "artifact.hostess.companion_session.live_broker_stream_execution",
                execution_out,
                execution.get("$schema"),
                role="live_broker_stream_execution",
                validation_status=validation.get("status"),
            ),
            artifact_ref(
                "artifact.hostess.companion_session.live_broker_stream_validation",
                validation_out,
                validation.get("$schema"),
                role="live_broker_stream_validation",
                validation_status=validation.get("status"),
            ),
        ]
    )
    if logcat_out.is_file():
        artifact_refs.append(
            artifact_ref(
                "artifact.hostess.companion_session.live_broker_stream_logcat",
                logcat_out,
                "text/plain",
                role="live_broker_stream_logcat",
                validation_status="captured",
            )
        )
    return execution, validation


def run_fallback_probe_slice(
    args: argparse.Namespace,
    out: Path,
    *,
    clock_ms_func: Callable[[], int],
    fallback_execution_func: Callable[..., dict[str, Any]] | None,
    artifact_refs: list[dict[str, Any]],
    request_token: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence_out = out.with_name(f"{out.stem}.app-private-fallback-evidence.json")
    execution_out = evidence_out.with_name(f"{evidence_out.stem}.android-execution.json")
    validation_out = evidence_out.with_name(f"{evidence_out.stem}.validation-report.json")
    logcat_out = evidence_out.with_name(f"{evidence_out.stem}.logcat.txt")
    request_out = out.with_name(f"{out.stem}.app-private-fallback-request.json")
    request_path = materialize_session_request(
        Path(str(getattr(args, "fallback_input", None) or default_fallback_input())),
        request_out,
        request_token=request_token,
        role="app_private_fallback",
    )
    request = bridge_command_android_routes.load_bridge_command_request(
        request_path,
    )
    fallback_args = android_fallback_args(args, evidence_out, execution_out, validation_out, logcat_out)
    fallback_args.input = str(request_path)
    if fallback_execution_func is not None:
        execution = fallback_execution_func(request, args=fallback_args)
    else:
        execution = bridge_command_android_routes.execute_bridge_command_android_request(
            request,
            args=fallback_args,
            run_func=bridge_command_android_routes.default_run,
            run_captured_func=bridge_command_android_routes.default_run_captured,
            write_app_file_func=bridge_command_android_routes.write_android_run_as_file,
            read_app_file_func=bridge_command_android_routes.read_android_run_as_file,
            wait_app_file_func=bridge_command_android_routes.wait_for_android_run_as_file,
            broker_client_factory=BrokerWebSocketClient,
            clock_ms_func=clock_ms_func,
            logcat_out=logcat_out,
        )
    bridge_evidence = execution["bridge_route_evidence"]
    validation = validate_bridge_route_evidence(
        bridge_evidence,
        required_stages=execution.get("required_evidence_stages"),
        route_descriptor=None,
    )
    execution["bridge_route_validation"] = validation
    write_json(evidence_out, bridge_evidence)
    write_json(execution_out, execution)
    write_json(validation_out, validation)
    artifact_refs.extend(
        [
            artifact_ref(
                "artifact.hostess.companion_session.app_private_fallback_request",
                request_path,
                request.get("$schema"),
                role="app_private_fallback_request",
                validation_status="generated",
            ),
            artifact_ref(
                "artifact.hostess.companion_session.app_private_fallback_evidence",
                evidence_out,
                bridge_evidence.get("$schema"),
                role="app_private_fallback_evidence",
                validation_status=validation.get("status"),
            ),
            artifact_ref(
                "artifact.hostess.companion_session.app_private_fallback_execution",
                execution_out,
                execution.get("$schema"),
                role="app_private_fallback_execution",
                validation_status=validation.get("status"),
            ),
            artifact_ref(
                "artifact.hostess.companion_session.app_private_fallback_validation",
                validation_out,
                validation.get("$schema"),
                role="app_private_fallback_validation",
                validation_status=validation.get("status"),
            ),
        ]
    )
    if logcat_out.exists():
        artifact_refs.append(
            artifact_ref(
                "artifact.hostess.companion_session.app_private_fallback_logcat",
                logcat_out,
                "text/plain",
                role="app_private_fallback_logcat",
                validation_status=validation.get("status"),
            )
        )
    return execution, validation


def readiness_phase(
    phase_id: str,
    title: str,
    readiness_report: dict[str, Any],
    groups: set[str],
) -> dict[str, Any]:
    checks = [
        check
        for check in readiness_report.get("checks", [])
        if isinstance(check, dict) and str(check.get("group") or "") in groups
    ]
    actions = [
        session_action(
            str(check.get("check_id") or ""),
            str(check.get("title") or ""),
            str(check.get("status") or "fail"),
            bool(check.get("required", False)),
            str(check.get("evidence") or ""),
            observed=check.get("observed") if isinstance(check.get("observed"), dict) else {},
            issue_codes=string_list(check.get("issue_codes"), "issue_codes"),
        )
        for check in checks
    ]
    return phase(
        phase_id,
        title,
        actions=actions,
        issues=issues_from_actions(actions),
    )


def runtime_phase(
    live_execution: dict[str, Any] | None,
    *,
    recovered_by_fallback: bool,
    skipped: bool,
) -> dict[str, Any]:
    if skipped:
        return skipped_phase("runtime", "Runtime launch", "probe skipped")
    if live_execution is None:
        return skipped_phase("runtime", "Runtime launch", "live broker-stream probe did not run")
    actions = [
        session_action(
            str(row.get("action") or ""),
            humanize_id(str(row.get("action") or "")),
            recovered_status(str(row.get("status") or "fail"), recovered_by_fallback),
            bool(row.get("required", False)),
            action_evidence(row),
            observed=row,
            issue_codes=[],
        )
        for row in live_execution.get("setup_actions", [])
        if isinstance(row, dict)
    ]
    return phase(
        "runtime",
        "Runtime launch",
        actions=actions,
        issues=issues_from_actions(actions) + execution_issues(live_execution, recovered_by_fallback),
    )


def broker_stream_probe_phase(
    live_execution: dict[str, Any] | None,
    *,
    recovered_by_fallback: bool,
    skipped: bool,
) -> dict[str, Any]:
    if skipped:
        return skipped_phase("broker_stream_probe", "Broker-stream probe", "probe skipped")
    if live_execution is None:
        return skipped_phase(
            "broker_stream_probe",
            "Broker-stream probe",
            "live broker-stream probe did not run",
        )
    actions = [
        session_action(
            f"stage.{row.get('stage')}",
            str(row.get("stage") or ""),
            recovered_status(str(row.get("status") or "fail"), recovered_by_fallback),
            True,
            ", ".join(string_list(row.get("evidence_refs"), "evidence_refs")),
            observed=row,
            issue_codes=string_list(row.get("issue_codes"), "issue_codes"),
        )
        for row in live_execution.get("stage_observations", [])
        if isinstance(row, dict)
    ]
    return phase(
        "broker_stream_probe",
        "Broker-stream probe",
        actions=actions,
        issues=execution_issues(live_execution, recovered_by_fallback),
        artifact_refs=["artifact.hostess.companion_session.live_broker_stream_execution"],
    )


def fallback_phase(
    fallback_execution: dict[str, Any] | None,
    *,
    live_failed: bool,
    fallback_enabled: bool,
    skipped: bool,
) -> dict[str, Any]:
    if skipped:
        return skipped_phase("app_private_fallback", "App-private fallback", "probe skipped")
    if not live_failed:
        return skipped_phase(
            "app_private_fallback",
            "App-private fallback",
            "broker-stream probe passed; fallback not needed",
        )
    if not fallback_enabled:
        return phase(
            "app_private_fallback",
            "App-private fallback",
            actions=[
                session_action(
                    "fallback.disabled",
                    "Fallback disabled",
                    "fail",
                    True,
                    "app-private fallback was disabled",
                    issue_codes=["hostess.issue.companion_session.fallback_disabled"],
                )
            ],
            issues=[
                session_issue(
                    "hostess.issue.companion_session.fallback_disabled",
                    "error",
                    "app-private fallback was disabled",
                )
            ],
        )
    if fallback_execution is None:
        return phase(
            "app_private_fallback",
            "App-private fallback",
            actions=[
                session_action(
                    "fallback.not_run",
                    "Fallback not run",
                    "fail",
                    True,
                    "broker-stream probe failed but no fallback execution was recorded",
                    issue_codes=["hostess.issue.companion_session.fallback_missing"],
                )
            ],
            issues=[
                session_issue(
                    "hostess.issue.companion_session.fallback_missing",
                    "error",
                    "broker-stream probe failed but no fallback execution was recorded",
                )
            ],
        )
    actions = [
        session_action(
            f"stage.{row.get('stage')}",
            str(row.get("stage") or ""),
            str(row.get("status") or "fail"),
            True,
            ", ".join(string_list(row.get("evidence_refs"), "evidence_refs")),
            observed=row,
            issue_codes=string_list(row.get("issue_codes"), "issue_codes"),
        )
        for row in fallback_execution.get("stage_observations", [])
        if isinstance(row, dict)
    ]
    return phase(
        "app_private_fallback",
        "App-private fallback",
        actions=actions,
        issues=execution_issues(fallback_execution, recovered=False),
        artifact_refs=["artifact.hostess.companion_session.app_private_fallback_execution"],
    )


def evidence_phase(
    artifact_refs: list[dict[str, Any]],
    readiness_validation: dict[str, Any],
    catalog_validation: dict[str, Any],
    device_link_validation: dict[str, Any],
    live_validation: dict[str, Any] | None,
    fallback_validation: dict[str, Any] | None,
    *,
    recovered_by_fallback: bool,
) -> dict[str, Any]:
    validations = [
        ("readiness", readiness_validation, False),
        ("catalog", catalog_validation, False),
        ("device_link", device_link_validation, False),
        ("live_broker_stream", live_validation, recovered_by_fallback),
        ("app_private_fallback", fallback_validation, False),
    ]
    actions = []
    for name, validation, recoverable in validations:
        if validation is None:
            continue
        validation_status = str(validation.get("status") or "fail")
        actions.append(
            session_action(
                f"validation.{name}",
                f"{humanize_id(name)} validation",
                recovered_status(validation_status, recoverable),
                not recoverable,
                "; ".join(string_list(validation.get("errors"), "errors")) or validation_status,
                observed=validation,
                issue_codes=[] if validation_status == "pass" else [f"hostess.issue.companion_session.{name}_validation"],
            )
        )
    return phase(
        "evidence",
        "Evidence package",
        actions=actions,
        artifact_refs=[str(row.get("artifact_id") or "") for row in artifact_refs],
        issues=issues_from_actions(actions),
    )


def phase(
    phase_id: str,
    title: str,
    *,
    actions: list[dict[str, Any]],
    issues: list[dict[str, Any]] | None = None,
    artifact_refs: list[str] | None = None,
) -> dict[str, Any]:
    clean_issues = issues or []
    status = status_from_actions_and_issues(actions, clean_issues)
    return {
        "phase_id": phase_id,
        "title": title,
        "status": status,
        "required": phase_id not in {"app_private_fallback"},
        "summary": phase_summary(actions, clean_issues),
        "actions": actions,
        "artifact_refs": artifact_refs or [],
        "issues": clean_issues,
    }


def skipped_phase(phase_id: str, title: str, reason: str) -> dict[str, Any]:
    return {
        "phase_id": phase_id,
        "title": title,
        "status": "skipped",
        "required": False,
        "summary": {
            "pass": 0,
            "warn": 0,
            "fail": 0,
            "skipped": 1,
            "action_count": 1,
            "issue_count": 0,
        },
        "actions": [
            session_action(
                f"{phase_id}.skipped",
                "Skipped",
                "skipped",
                False,
                reason,
            )
        ],
        "artifact_refs": [],
        "issues": [],
    }


def session_action(
    action_id: str,
    title: str,
    status: str,
    required: bool,
    evidence: str,
    *,
    observed: Any | None = None,
    issue_codes: list[str] | None = None,
) -> dict[str, Any]:
    normalized = normalize_session_status(status)
    return {
        "action_id": action_id,
        "title": title or action_id,
        "status": normalized,
        "required": required,
        "severity": severity_for_status(normalized, required),
        "evidence": evidence,
        "observed": observed or {},
        "issue_codes": issue_codes or [],
    }


def session_issue(issue_code: str, severity: str, message: str) -> dict[str, Any]:
    return {
        "issue_code": issue_code,
        "severity": severity,
        "message": message,
    }


def issues_from_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for action in actions:
        if action.get("status") not in {"fail", "warn"}:
            continue
        issue_codes = string_list(action.get("issue_codes"), "issue_codes")
        if not issue_codes:
            issue_codes = [f"hostess.issue.companion_session.{action.get('action_id')}"]
        for code in issue_codes:
            issues.append(
                session_issue(
                    code,
                    "error" if action.get("status") == "fail" and action.get("required") else "warning",
                    str(action.get("evidence") or action.get("title") or code),
                )
            )
    return issues


def execution_issues(execution: dict[str, Any], recovered: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue in execution.get("issues", []):
        if not isinstance(issue, dict):
            continue
        severity = str(issue.get("severity") or "error")
        if recovered and severity == "error":
            severity = "warning"
        rows.append(
            session_issue(
                str(issue.get("issue_code") or issue.get("code") or "hostess.issue.companion_session.execution"),
                severity,
                str(issue.get("message") or issue.get("issue_code") or "execution issue"),
            )
        )
    return rows


def artifact_ref(
    artifact_id: str,
    path: Path,
    schema: Any,
    *,
    role: str,
    validation_status: Any,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "role": role,
        "path": str(path),
        "schema": str(schema or ""),
        "validation_status": str(validation_status or ""),
    }


def materialize_session_request(
    template_path: Path,
    out: Path,
    *,
    request_token: str,
    role: str,
) -> Path:
    request = json.loads(template_path.read_text(encoding="utf-8"))
    request["request_id"] = append_identity_token(
        str(request.get("request_id") or f"request.hostess.companion_session.{role}"),
        request_token,
    )
    request["evidence_id"] = append_identity_token(
        str(request.get("evidence_id") or f"evidence.hostess.companion_session.{role}"),
        request_token,
    )
    params = request.get("params")
    if not isinstance(params, dict):
        params = {}
    params = dict(params)
    params["probe_token"] = append_identity_token(
        str(params.get("probe_token") or f"probe.{role}"),
        request_token,
    )
    params["session_request_token"] = request_token
    request["params"] = params
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def session_request_token(args: argparse.Namespace, out: Path, started_at_ms: int) -> str:
    explicit_session_id = str(getattr(args, "session_id", None) or "").strip()
    source = explicit_session_id or f"{out.stem}.{started_at_ms}"
    return safe_identity_token(source)


def append_identity_token(identity: str, token: str) -> str:
    base = safe_identity_token(identity)
    suffix = safe_identity_token(token)
    if base.endswith(f".{suffix}"):
        return base
    return f"{base}.{suffix}"


def safe_identity_token(value: str) -> str:
    chars = [
        char if char.isalnum() or char in {".", "_", "-"} else "-"
        for char in str(value).strip()
    ]
    token = "".join(chars).strip("._-")
    while ".." in token:
        token = token.replace("..", ".")
    return (token or "session")[:120]


def session_scope(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "adb": str(getattr(args, "adb", None) or ""),
        "serial": str(getattr(args, "serial", None) or ""),
        "broker_host": str(getattr(args, "broker_host", None) or "127.0.0.1"),
        "broker_port": int(getattr(args, "broker_port", None) or BROKER_PORT),
        "broker_local_port": int(
            getattr(args, "broker_local_port", None) or BROKER_LOCAL_FORWARD_PORT
        ),
        "broker_package": selected_broker_package(args),
        "broker_activity": selected_broker_activity(args),
        "makepad_package": str(getattr(args, "makepad_package", None) or MAKEPAD_ANDROID_PACKAGE),
        "makepad_activity": str(
            getattr(args, "makepad_activity", None) or MAKEPAD_ANDROID_XR_ACTIVITY
        ),
        "probe_input": str(getattr(args, "probe_input", None) or default_probe_input()),
        "fallback_input": str(getattr(args, "fallback_input", None) or default_fallback_input()),
    }


def live_android_args(
    args: argparse.Namespace,
    evidence_out: Path,
    execution_out: Path,
    validation_out: Path,
    logcat_out: Path,
) -> argparse.Namespace:
    return argparse.Namespace(
        input=str(getattr(args, "probe_input", None) or default_probe_input()),
        out=str(evidence_out),
        execution_out=str(execution_out),
        validation_out=str(validation_out),
        logcat_out=str(logcat_out),
        route_descriptor=None,
        adb=str(getattr(args, "adb", "")),
        serial=str(getattr(args, "serial", "")),
        broker_package=getattr(args, "broker_package", None),
        broker_activity=getattr(args, "broker_activity", None),
        broker_host=str(getattr(args, "broker_host", None) or "127.0.0.1"),
        broker_port=int(getattr(args, "broker_port", None) or BROKER_PORT),
        broker_local_port=int(getattr(args, "broker_local_port", None) or BROKER_LOCAL_FORWARD_PORT),
        broker_path=str(getattr(args, "broker_path", None) or MANIFOLD_BROKER_EVENTS_PATH),
        connect_timeout_seconds=float(getattr(args, "connect_timeout_seconds", 5.0)),
        wait_seconds=float(
            getattr(args, "wait_seconds", DEFAULT_COMPANION_SESSION_WAIT_SECONDS)
        ),
        runtime_receipt_stream=str(
            getattr(args, "runtime_receipt_stream", None) or DEFAULT_RUNTIME_RECEIPT_STREAM
        ),
        no_runtime_receipt_subscribe=bool(getattr(args, "no_runtime_receipt_subscribe", False)),
        makepad_package=str(getattr(args, "makepad_package", None) or MAKEPAD_ANDROID_PACKAGE),
        makepad_activity=str(
            getattr(args, "makepad_activity", None) or MAKEPAD_ANDROID_XR_ACTIVITY
        ),
        broker_process_wait_seconds=float(
            getattr(
                args,
                "broker_process_wait_seconds",
                DEFAULT_COMPANION_SESSION_PROCESS_WAIT_SECONDS,
            )
        ),
        makepad_process_wait_seconds=float(
            getattr(
                args,
                "makepad_process_wait_seconds",
                DEFAULT_COMPANION_SESSION_PROCESS_WAIT_SECONDS,
            )
        ),
        socket_wait_seconds=float(
            getattr(
                args,
                "socket_wait_seconds",
                DEFAULT_COMPANION_SESSION_SOCKET_WAIT_SECONDS,
            )
        ),
        launch_settle_seconds=float(
            getattr(
                args,
                "launch_settle_seconds",
                DEFAULT_COMPANION_SESSION_LAUNCH_SETTLE_SECONDS,
            )
        ),
        runtime_subscriber_retry_count=int(
            getattr(
                args,
                "runtime_subscriber_retry_count",
                DEFAULT_COMPANION_SESSION_RUNTIME_SUBSCRIBER_RETRY_COUNT,
            )
        ),
        runtime_subscriber_retry_wait_seconds=float(
            getattr(
                args,
                "runtime_subscriber_retry_wait_seconds",
                DEFAULT_COMPANION_SESSION_RUNTIME_SUBSCRIBER_RETRY_WAIT_SECONDS,
            )
        ),
        no_launch_broker=bool(getattr(args, "no_launch_broker", False)),
        no_launch_makepad=bool(getattr(args, "no_launch_makepad", False)),
        no_wait_broker_process=bool(getattr(args, "no_wait_broker_process", False)),
        no_wait_makepad_process=bool(getattr(args, "no_wait_makepad_process", False)),
        no_adb_forward_broker=bool(getattr(args, "no_adb_forward_broker", False)),
    )


def android_fallback_args(
    args: argparse.Namespace,
    evidence_out: Path,
    execution_out: Path,
    validation_out: Path,
    logcat_out: Path,
) -> argparse.Namespace:
    return argparse.Namespace(
        input=str(getattr(args, "fallback_input", None) or default_fallback_input()),
        out=str(evidence_out),
        execution_out=str(execution_out),
        validation_out=str(validation_out),
        logcat_out=str(logcat_out),
        route_descriptor=None,
        route_id=None,
        required_stage=[],
        broker_authority=False,
        broker_host=str(getattr(args, "broker_host", None) or "127.0.0.1"),
        broker_port=int(getattr(args, "broker_port", None) or BROKER_PORT),
        broker_local_port=int(getattr(args, "broker_local_port", None) or BROKER_LOCAL_FORWARD_PORT),
        broker_path=str(getattr(args, "broker_path", None) or MANIFOLD_BROKER_EVENTS_PATH),
        connect_timeout_seconds=float(getattr(args, "connect_timeout_seconds", 5.0)),
        authority_wait_seconds=float(
            getattr(
                args,
                "authority_wait_seconds",
                DEFAULT_COMPANION_SESSION_AUTHORITY_WAIT_SECONDS,
            )
        ),
        adb_forward_broker=False,
        adb=str(getattr(args, "adb", "")),
        serial=str(getattr(args, "serial", "")),
        makepad_package=str(getattr(args, "makepad_package", None) or MAKEPAD_ANDROID_PACKAGE),
        makepad_activity=str(
            getattr(args, "makepad_activity", None) or MAKEPAD_ANDROID_XR_ACTIVITY
        ),
        remote_dir=str(
            getattr(args, "fallback_remote_dir", None)
            or bridge_command_android_routes.DEFAULT_REMOTE_DIR
        ),
        wait_seconds=float(
            getattr(args, "fallback_wait_seconds", None)
            or getattr(args, "wait_seconds", DEFAULT_COMPANION_SESSION_WAIT_SECONDS)
        ),
        no_launch=bool(getattr(args, "no_launch_makepad", False)),
    )


def validate_companion_session_report(report: dict[str, Any]) -> dict[str, Any]:
    phases = [row for row in report.get("phases", []) if isinstance(row, dict)]
    artifact_refs = [row for row in report.get("artifact_refs", []) if isinstance(row, dict)]
    errors: list[str] = []
    if report.get("$schema") != HOSTESS_COMPANION_SESSION_SCHEMA:
        errors.append("unsupported companion session schema")
    phase_ids = [str(row.get("phase_id") or "") for row in phases]
    missing = [phase_id for phase_id in SESSION_PHASE_IDS if phase_id not in phase_ids]
    if missing:
        errors.append(f"missing companion session phases: {', '.join(missing)}")
    invalid_phase_status = [
        str(row.get("phase_id") or "<unknown>")
        for row in phases
        if row.get("status") not in VALID_SESSION_STATUSES
    ]
    if invalid_phase_status:
        errors.append(f"phases with unsupported status: {', '.join(invalid_phase_status)}")
    if not artifact_refs:
        errors.append("companion session must reference evidence artifacts")
    invalid_artifacts = [
        str(row.get("artifact_id") or "<unknown>")
        for row in artifact_refs
        if not row.get("artifact_id") or not row.get("path")
    ]
    if invalid_artifacts:
        errors.append(f"artifact refs missing identity or path: {', '.join(invalid_artifacts)}")
    expected = session_status(phases)
    if report.get("status") != expected:
        errors.append(
            f"session status {report.get('status')!r} did not match phase status {expected!r}"
        )
    return {
        "$schema": HOSTESS_COMPANION_SESSION_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "session_status": report.get("status"),
        "phase_count": len(phases),
        "artifact_count": len(artifact_refs),
        "errors": errors,
    }


def session_status(phases: list[dict[str, Any]]) -> str:
    statuses = [str(phase.get("status") or "") for phase in phases]
    if any(status == "fail" for status in statuses):
        return "fail"
    if any(status == "warn" for status in statuses):
        return "warn"
    return "pass"


def status_from_actions(actions: list[dict[str, Any]]) -> str:
    if not actions:
        return "skipped"
    statuses = [str(action.get("status") or "") for action in actions]
    if any(status == "fail" for status in statuses):
        return "fail"
    if any(status == "warn" for status in statuses):
        return "warn"
    if all(status == "skipped" for status in statuses):
        return "skipped"
    return "pass"


def status_from_actions_and_issues(
    actions: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> str:
    status = status_from_actions(actions)
    if status in {"fail", "warn"}:
        return status
    severities = {str(issue.get("severity") or "") for issue in issues}
    if "error" in severities:
        return "fail"
    if "warning" in severities:
        return "warn"
    return status


def phase_summary(actions: list[dict[str, Any]], issues: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "pass": sum(1 for action in actions if action.get("status") == "pass"),
        "warn": sum(1 for action in actions if action.get("status") == "warn"),
        "fail": sum(1 for action in actions if action.get("status") == "fail"),
        "skipped": sum(1 for action in actions if action.get("status") == "skipped"),
        "action_count": len(actions),
        "issue_count": len(issues),
    }


def recovered_status(status: str, recovered: bool) -> str:
    normalized = normalize_session_status(status)
    if recovered and normalized == "fail":
        return "warn"
    return normalized


def normalize_session_status(status: str) -> str:
    value = str(status or "").strip().lower()
    if value in VALID_SESSION_STATUSES:
        return value
    if value in {"ok", "accepted", "applied", "success", "passed"}:
        return "pass"
    return "fail"


def severity_for_status(status: str, required: bool) -> str:
    if status == "fail" and required:
        return "error"
    if status in {"fail", "warn"}:
        return "warning"
    return "info"


def action_evidence(row: dict[str, Any]) -> str:
    if row.get("stdout"):
        return str(row.get("stdout"))
    if row.get("stderr"):
        return str(row.get("stderr"))
    if row.get("pid"):
        return f"pid={row.get('pid')}"
    if row.get("expected"):
        return str(row.get("expected"))
    if row.get("host") and row.get("port"):
        return f"{row.get('host')}:{row.get('port')}"
    return str(row.get("action") or "")


def exception_execution(
    schema: str,
    route_id: str,
    command: str,
    issue_code: str,
    message: str,
    observed_at_ms: int,
) -> dict[str, Any]:
    return {
        "$schema": schema,
        "status": "fail",
        "started_at_ms": observed_at_ms,
        "ended_at_ms": observed_at_ms,
        "route_id": route_id,
        "request_id": "",
        "command": command,
        "required_evidence_stages": ["sent"],
        "setup_actions": [],
        "stage_observations": [
            {
                "stage": "sent",
                "status": "fail",
                "observed_at_ms": observed_at_ms,
                "evidence_refs": [],
                "issue_codes": [issue_code],
            }
        ],
        "issues": [session_issue(issue_code, "error", message)],
        "bridge_route_evidence": {
            "$schema": "rusty.manifold.bridge.route_evidence.v1",
            "evidence_id": f"evidence.hostess.companion_session.exception.{observed_at_ms}",
            "route_id": route_id,
            "status": "fail",
            "started_at_ms": observed_at_ms,
            "ended_at_ms": observed_at_ms,
            "stage_reports": [
                {
                    "stage": "sent",
                    "status": "fail",
                    "observed_at_ms": observed_at_ms,
                    "evidence_refs": [],
                    "issue_codes": [issue_code],
                }
            ],
            "artifact_refs": [],
            "issues": [session_issue(issue_code, "error", message)],
        },
    }


def humanize_id(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().capitalize()


def string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return [str(value)]
    return [str(item) for item in value]


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON file did not contain an object: {path}")
    return value


def default_probe_input() -> Path:
    return repo_root() / "fixtures" / "bridge-command" / "hostess-broker-stream-command-request.json"


def default_fallback_input() -> Path:
    return repo_root() / "fixtures" / "bridge-command" / "hostess-android-hotload-command-request.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def epoch_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


__all__ = [
    "HOSTESS_COMPANION_SESSION_SCHEMA",
    "HOSTESS_COMPANION_SESSION_HISTORY_SCHEMA",
    "HOSTESS_COMPANION_SESSION_VALIDATION_SCHEMA",
    "build_companion_session_history_report",
    "build_companion_session_report",
    "run_companion_session_history",
    "run_companion_session",
    "validate_companion_session_report",
]
