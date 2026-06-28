"""Live Android broker-stream bridge command orchestration route."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from tools.hostessctl.bridge_command_routes import (
    DEFAULT_REQUIRED_STAGES,
    DEFAULT_RUNTIME_RECEIPT_STREAM,
    add_stage,
    epoch_ms,
    execute_bridge_command_request,
    load_bridge_command_request,
    load_json_object,
    string_list,
)
from tools.hostessctl.bridge_route_evidence import (
    HOSTESS_BRIDGE_ROUTE_INPUT_SCHEMA,
    MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
    normalize_bridge_route_evidence,
    validate_bridge_route_evidence,
)
from tools.hostessctl.broker_transport import (
    MANIFOLD_BROKER_EVENTS_PATH,
    BrokerWebSocketClient,
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


BRIDGE_COMMAND_LIVE_ANDROID_EXECUTION_SCHEMA = (
    "rusty.hostess.bridge_command.live_android_execution_evidence.v1"
)
LIVE_ANDROID_CLIENT_ID = "hostessctl.bridge_command.live_android"


def run_bridge_command_live_android(
    args: argparse.Namespace,
    *,
    run_captured_func: Any | None = None,
    broker_client_factory: Any | None = None,
    clock_ms_func: Any | None = None,
    socket_probe_func: Callable[[str, int, float], bool] | None = None,
    sleep_func: Callable[[float], None] | None = None,
) -> int:
    request = load_bridge_command_request(Path(args.input))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    execution_out = (
        Path(args.execution_out)
        if getattr(args, "execution_out", None)
        else out.with_name(f"{out.stem}.live-android-execution.json")
    )
    validation_out = (
        Path(args.validation_out)
        if getattr(args, "validation_out", None)
        else out.with_name(f"{out.stem}.validation-report.json")
    )
    route_descriptor = (
        load_json_object(Path(args.route_descriptor))
        if getattr(args, "route_descriptor", None)
        else None
    )

    execution = execute_bridge_command_live_android_request(
        request,
        args=args,
        run_captured_func=run_captured_func or default_run_captured,
        broker_client_factory=broker_client_factory or BrokerWebSocketClient,
        clock_ms_func=clock_ms_func,
        socket_probe_func=socket_probe_func or broker_port_open,
        sleep_func=sleep_func or time.sleep,
    )
    bridge_evidence = execution["bridge_route_evidence"]
    validation = validate_bridge_route_evidence(
        bridge_evidence,
        required_stages=execution["required_evidence_stages"],
        route_descriptor=route_descriptor,
    )
    execution["bridge_route_validation"] = validation
    out.write_text(json.dumps(bridge_evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    execution_out.parent.mkdir(parents=True, exist_ok=True)
    execution_out.write_text(json.dumps(execution, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation_out.parent.mkdir(parents=True, exist_ok=True)
    validation_out.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if validation["status"] == "pass" and execution["status"] != "fail" else 2


def execute_bridge_command_live_android_request(
    request: dict[str, Any],
    *,
    args: argparse.Namespace,
    run_captured_func: Any,
    broker_client_factory: Any,
    clock_ms_func: Any | None = None,
    socket_probe_func: Callable[[str, int, float], bool] | None = None,
    sleep_func: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    clock = clock_ms_func or epoch_ms
    socket_probe = socket_probe_func or broker_port_open
    sleep = sleep_func or time.sleep
    started_at_ms = int(clock())
    setup_actions: list[dict[str, Any]] = []
    setup_issues: list[dict[str, Any]] = []

    broker_package = selected_broker_package(args)
    broker_activity = selected_broker_activity(args)
    makepad_package = str(getattr(args, "makepad_package", None) or MAKEPAD_ANDROID_PACKAGE)
    makepad_activity = str(getattr(args, "makepad_activity", None) or MAKEPAD_ANDROID_XR_ACTIVITY)
    broker_host = str(getattr(args, "broker_host", None) or "127.0.0.1")
    broker_port = int(getattr(args, "broker_port", None) or BROKER_PORT)
    broker_local_port = int(getattr(args, "broker_local_port", None) or BROKER_LOCAL_FORWARD_PORT)
    broker_path = str(getattr(args, "broker_path", None) or MANIFOLD_BROKER_EVENTS_PATH)
    use_adb_forward = not bool(getattr(args, "no_adb_forward_broker", False))
    connect_port = broker_local_port if use_adb_forward else broker_port

    if not getattr(args, "no_launch_broker", False):
        run_adb_action(
            setup_actions,
            setup_issues,
            "launch-manifold-broker",
            adb_command(args, "shell", "am", "start", "-n", broker_activity),
            run_captured_func,
            required=True,
        )

    if not getattr(args, "no_wait_broker_process", False):
        wait_for_android_pid(
            setup_actions,
            setup_issues,
            args,
            broker_package,
            "wait-manifold-broker-process",
            float(getattr(args, "broker_process_wait_seconds", 8.0)),
            run_captured_func,
            required=True,
        )

    if use_adb_forward:
        run_adb_action(
            setup_actions,
            setup_issues,
            "remove-existing-broker-adb-forward",
            adb_command(args, "forward", "--remove", f"tcp:{broker_local_port}"),
            run_captured_func,
            required=False,
            issue_on_failure=False,
        )
        run_adb_action(
            setup_actions,
            setup_issues,
            "adb-forward-broker",
            adb_command(args, "forward", f"tcp:{broker_local_port}", f"tcp:{broker_port}"),
            run_captured_func,
            required=True,
        )
        check_adb_forward(
            setup_actions,
            setup_issues,
            args,
            broker_local_port,
            broker_port,
            run_captured_func,
            required=True,
        )

    socket_ready = wait_for_broker_socket(
        setup_actions,
        setup_issues,
        broker_host,
        connect_port,
        float(getattr(args, "socket_wait_seconds", 8.0)),
        socket_probe,
        sleep,
    )

    if not getattr(args, "no_launch_makepad", False):
        run_adb_action(
            setup_actions,
            setup_issues,
            "launch-hostess-makepad",
            adb_command(args, "shell", "am", "start", "-n", makepad_activity),
            run_captured_func,
            required=False,
        )

    if not getattr(args, "no_wait_makepad_process", False):
        wait_for_android_pid(
            setup_actions,
            setup_issues,
            args,
            makepad_package,
            "wait-hostess-makepad-process",
            float(getattr(args, "makepad_process_wait_seconds", 8.0)),
            run_captured_func,
            required=False,
        )

    settle_seconds = max(0.0, float(getattr(args, "launch_settle_seconds", 8.0)))
    if settle_seconds:
        sleep(settle_seconds)
        setup_actions.append(
            {
                "action": "wait-runtime-subscriber-settle",
                "status": "pass",
                "duration_seconds": settle_seconds,
            }
        )

    if socket_ready:
        command_execution = execute_bridge_command_request(
            request,
            broker_host=broker_host,
            broker_port=connect_port,
            broker_path=broker_path,
            connect_timeout_seconds=float(getattr(args, "connect_timeout_seconds", 5.0)),
            wait_seconds=float(getattr(args, "wait_seconds", 15.0)),
            runtime_receipt_stream=(
                None
                if getattr(args, "no_runtime_receipt_subscribe", False)
                else str(getattr(args, "runtime_receipt_stream", None) or DEFAULT_RUNTIME_RECEIPT_STREAM)
            ),
            broker_client_factory=broker_client_factory,
            clock_ms_func=clock,
        )
        bridge_evidence = command_execution["bridge_route_evidence"]
        stage_observations = command_execution["stage_observations"]
        command_issues = command_execution["issues"]
    else:
        command_execution = None
        command_issues = []
        stage_observations = [
            failed_stage(
                "sent",
                int(clock()),
                "hostess.issue.bridge_command.live_android.broker_socket_unavailable",
            )
        ]
        bridge_evidence = failed_bridge_route_evidence(
            request,
            started_at_ms=started_at_ms,
            ended_at_ms=int(clock()),
            stage_observations=stage_observations,
            issues=setup_issues,
        )

    issues = setup_issues + command_issues
    status = execution_status(setup_issues, command_execution)
    ended_at_ms = int(clock())
    return {
        "$schema": BRIDGE_COMMAND_LIVE_ANDROID_EXECUTION_SCHEMA,
        "status": status,
        "started_at_ms": started_at_ms,
        "ended_at_ms": max(started_at_ms, ended_at_ms),
        "route_id": str(request.get("route_id") or ""),
        "request_schema": str(request.get("$schema") or ""),
        "request_id": str(request.get("request_id") or ""),
        "command": str(request.get("command") or ""),
        "required_evidence_stages": string_list(
            request.get("required_evidence_stages") or DEFAULT_REQUIRED_STAGES,
            "required_evidence_stages",
        ),
        "android": {
            "adb": str(getattr(args, "adb", "")),
            "serial": str(getattr(args, "serial", "")),
            "broker_package": broker_package,
            "broker_activity": broker_activity,
            "makepad_package": makepad_package,
            "makepad_activity": makepad_activity,
        },
        "broker_stream": {
            "host": broker_host,
            "port": connect_port,
            "target_port": broker_port,
            "local_forward_port": broker_local_port if use_adb_forward else None,
            "adb_forward": use_adb_forward,
            "path": broker_path,
            "runtime_receipt_stream": (
                None
                if getattr(args, "no_runtime_receipt_subscribe", False)
                else str(getattr(args, "runtime_receipt_stream", None) or DEFAULT_RUNTIME_RECEIPT_STREAM)
            ),
            "client_id": LIVE_ANDROID_CLIENT_ID,
        },
        "setup_actions": setup_actions,
        "command_execution": command_execution,
        "stage_observations": stage_observations,
        "issues": issues,
        "bridge_route_evidence_schema": MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
        "bridge_route_evidence": bridge_evidence,
    }


def execution_status(
    setup_issues: list[dict[str, Any]],
    command_execution: dict[str, Any] | None,
) -> str:
    if any(issue.get("severity") == "error" for issue in setup_issues):
        return "fail"
    command_status = str(command_execution.get("status") if command_execution else "fail")
    if command_status == "fail":
        return "fail"
    if setup_issues or command_status == "warn":
        return "warn"
    return "pass"


def run_adb_action(
    actions: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    action: str,
    command: list[str],
    run_captured_func: Any,
    *,
    required: bool,
    issue_on_failure: bool = True,
) -> bool:
    try:
        result = run_captured_func(command, allow_failure=True)
    except SystemExit as exc:
        result = subprocess.CompletedProcess(command, int(exc.code or 1), "", str(exc))
    except Exception as exc:
        result = subprocess.CompletedProcess(command, 1, "", str(exc))
    passed = result.returncode == 0
    status = "pass" if passed else ("fail" if required else "warn")
    actions.append(
        {
            "action": action,
            "status": status,
            "required": required,
            "command": redact_command(command),
            "returncode": result.returncode,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
        }
    )
    if not passed and issue_on_failure:
        issues.append(
            {
                "issue_code": f"hostess.issue.bridge_command.live_android.{action.replace('-', '_')}_failed",
                "severity": "error" if required else "warning",
                "message": f"{action} failed with exit code {result.returncode}",
            }
        )
    return passed


def wait_for_android_pid(
    actions: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    args: argparse.Namespace,
    package: str,
    action: str,
    timeout_seconds: float,
    run_captured_func: Any,
    *,
    required: bool,
) -> bool:
    command = adb_command(args, "shell", "pidof", package)
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    last_result = subprocess.CompletedProcess(command, 1, "", "")
    while time.monotonic() <= deadline:
        last_result = run_captured_func(command, allow_failure=True)
        if last_result.returncode == 0 and (last_result.stdout or "").strip():
            actions.append(
                {
                    "action": action,
                    "status": "pass",
                    "required": required,
                    "package": package,
                    "pid": (last_result.stdout or "").strip(),
                    "command": redact_command(command),
                }
            )
            return True
        time.sleep(0.25)
    status = "fail" if required else "warn"
    actions.append(
        {
            "action": action,
            "status": status,
            "required": required,
            "package": package,
            "command": redact_command(command),
            "returncode": last_result.returncode,
            "stdout": (last_result.stdout or "").strip(),
            "stderr": (last_result.stderr or "").strip(),
        }
    )
    issues.append(
        {
            "issue_code": f"hostess.issue.bridge_command.live_android.{action.replace('-', '_')}_missing",
            "severity": "error" if required else "warning",
            "message": f"{package} process was not observed within {timeout_seconds:.1f}s",
        }
    )
    return False


def check_adb_forward(
    actions: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    args: argparse.Namespace,
    local_port: int,
    remote_port: int,
    run_captured_func: Any,
    *,
    required: bool,
) -> bool:
    command = adb_command(args, "forward", "--list")
    result = run_captured_func(command, allow_failure=True)
    expected = f"tcp:{local_port} tcp:{remote_port}"
    passed = result.returncode == 0 and expected in (result.stdout or "")
    status = "pass" if passed else ("fail" if required else "warn")
    actions.append(
        {
            "action": "check-broker-adb-forward",
            "status": status,
            "required": required,
            "expected": expected,
            "command": redact_command(command),
            "returncode": result.returncode,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
        }
    )
    if not passed:
        issues.append(
            {
                "issue_code": "hostess.issue.bridge_command.live_android.broker_adb_forward_missing",
                "severity": "error" if required else "warning",
                "message": f"missing ADB forward {expected}",
            }
        )
    return passed


def wait_for_broker_socket(
    actions: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    host: str,
    port: int,
    timeout_seconds: float,
    socket_probe_func: Callable[[str, int, float], bool],
    sleep_func: Callable[[float], None],
) -> bool:
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while time.monotonic() <= deadline:
        if socket_probe_func(host, port, 0.25):
            actions.append(
                {
                    "action": "wait-broker-forwarded-socket",
                    "status": "pass",
                    "required": True,
                    "host": host,
                    "port": port,
                }
            )
            return True
        sleep_func(0.25)
    actions.append(
        {
            "action": "wait-broker-forwarded-socket",
            "status": "fail",
            "required": True,
            "host": host,
            "port": port,
            "timeout_seconds": timeout_seconds,
        }
    )
    issues.append(
        {
            "issue_code": "hostess.issue.bridge_command.live_android.broker_socket_closed",
            "severity": "error",
            "message": f"broker socket {host}:{port} did not open within {timeout_seconds:.1f}s",
        }
    )
    return False


def failed_bridge_route_evidence(
    request: dict[str, Any],
    *,
    started_at_ms: int,
    ended_at_ms: int,
    stage_observations: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    bridge_input = {
        "$schema": HOSTESS_BRIDGE_ROUTE_INPUT_SCHEMA,
        "evidence_id": str(
            request.get("evidence_id")
            or f"evidence.hostess.bridge_command.live_android.{request.get('command', 'unknown')}"
        ),
        "route_id": str(request.get("route_id") or ""),
        "status": "fail",
        "started_at_ms": started_at_ms,
        "ended_at_ms": max(started_at_ms, ended_at_ms),
        "required_evidence_stages": string_list(
            request.get("required_evidence_stages") or DEFAULT_REQUIRED_STAGES,
            "required_evidence_stages",
        ),
        "stage_observations": stage_observations,
        "artifact_refs": [
            "artifact.hostess.bridge_command.live_android_execution",
            "artifact.hostess.bridge_command.validation_report",
        ],
        "issues": issues,
    }
    return normalize_bridge_route_evidence(bridge_input)


def failed_stage(stage: str, observed_at_ms: int, issue_code: str) -> dict[str, Any]:
    row: list[dict[str, Any]] = []
    add_stage(
        row,
        stage,
        "fail",
        observed_at_ms,
        ["evidence.hostess.bridge_command.live_android.setup"],
        [issue_code],
    )
    return row[0]


def adb_command(args: argparse.Namespace, *parts: str) -> list[str]:
    return [str(args.adb), "-s", str(args.serial), *parts]


def broker_port_open(host: str, port: int, timeout_seconds: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def redact_command(command: list[str]) -> list[str]:
    return [str(part) for part in command]


__all__ = [
    "BRIDGE_COMMAND_LIVE_ANDROID_EXECUTION_SCHEMA",
    "execute_bridge_command_live_android_request",
    "run_bridge_command_live_android",
]
