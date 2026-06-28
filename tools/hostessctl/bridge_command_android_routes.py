"""Quest/Android app-private bridge command receipt route."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.android_files import (
    read_android_run_as_file,
    wait_for_android_run_as_file,
    write_android_run_as_file,
)
from tools.hostessctl.bridge_command_routes import (
    BRIDGE_COMMAND_REQUEST_SCHEMA,
    load_bridge_command_request,
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
    broker_ack_accepted,
    broker_command_message,
)
from tools.hostessctl.platform_defaults import (
    MAKEPAD_ANDROID_PACKAGE,
    MAKEPAD_ANDROID_XR_ACTIVITY,
)


BRIDGE_COMMAND_ANDROID_EXECUTION_SCHEMA = (
    "rusty.hostess.bridge_command.android_execution_evidence.v1"
)
BRIDGE_COMMAND_RUNTIME_RECEIPT_SCHEMA = (
    "rusty.hostess.makepad.bridge_command_runtime_receipt.v1"
)
DEFAULT_ANDROID_ROUTE_ID = "bridge_route.command.android_app_private.applied"
DEFAULT_AUTHORIZED_ANDROID_ROUTE_ID = (
    "bridge_route.command.android_broker_authorized_app_private.applied"
)
DEFAULT_ANDROID_REQUIRED_STAGES = [
    "sent",
    "transport_ok",
    "runtime_accepted",
    "applied",
]
DEFAULT_AUTHORIZED_ANDROID_REQUIRED_STAGES = [
    "sent",
    "transport_ok",
    "authority_accepted",
    "runtime_accepted",
    "applied",
]
DEFAULT_REMOTE_DIR = "files/hostess-t/settings"
DEFAULT_REQUEST_FILE = "bridge-command-request.json"
DEFAULT_RECEIPT_FILE = "bridge-command-receipt.json"
ANDROID_AUTHORITY_CLIENT_ID = "hostessctl.bridge_command.android_authorized"


def run_bridge_command_android(
    args: argparse.Namespace,
    *,
    run_func: Any | None = None,
    run_captured_func: Any | None = None,
    write_app_file_func: Any | None = None,
    read_app_file_func: Any | None = None,
    wait_app_file_func: Any | None = None,
    broker_client_factory: Any | None = None,
    clock_ms_func: Any | None = None,
) -> int:
    request = load_bridge_command_request(Path(args.input))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    execution_out = (
        Path(args.execution_out)
        if getattr(args, "execution_out", None)
        else out.with_name(f"{out.stem}.android-execution.json")
    )
    validation_out = (
        Path(args.validation_out)
        if getattr(args, "validation_out", None)
        else out.with_name(f"{out.stem}.validation-report.json")
    )
    logcat_out = (
        Path(args.logcat_out)
        if getattr(args, "logcat_out", None)
        else out.with_name(f"{out.stem}.logcat.txt")
    )
    route_descriptor = (
        load_json_object(Path(args.route_descriptor))
        if getattr(args, "route_descriptor", None)
        else None
    )
    execution = execute_bridge_command_android_request(
        request,
        args=args,
        run_func=run_func or default_run,
        run_captured_func=run_captured_func or default_run_captured,
        write_app_file_func=write_app_file_func or write_android_run_as_file,
        read_app_file_func=read_app_file_func or read_android_run_as_file,
        wait_app_file_func=wait_app_file_func or wait_for_android_run_as_file,
        broker_client_factory=broker_client_factory or BrokerWebSocketClient,
        clock_ms_func=clock_ms_func,
        logcat_out=logcat_out,
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
    return 0 if validation["status"] == "pass" else 2


def execute_bridge_command_android_request(
    request: dict[str, Any],
    *,
    args: argparse.Namespace,
    run_func: Any,
    run_captured_func: Any,
    write_app_file_func: Any,
    read_app_file_func: Any,
    wait_app_file_func: Any,
    broker_client_factory: Any | None = None,
    clock_ms_func: Any | None = None,
    logcat_out: Path | None = None,
) -> dict[str, Any]:
    clock = clock_ms_func or epoch_ms
    started_at_ms = int(clock())
    broker_authority = bool(getattr(args, "broker_authority", False))
    package = str(getattr(args, "makepad_package", None) or MAKEPAD_ANDROID_PACKAGE)
    activity = str(getattr(args, "makepad_activity", None) or MAKEPAD_ANDROID_XR_ACTIVITY)
    remote_dir = normalize_relative_dir(
        str(getattr(args, "remote_dir", None) or DEFAULT_REMOTE_DIR)
    )
    request_relative = f"{remote_dir}/{DEFAULT_REQUEST_FILE}"
    receipt_relative = f"{remote_dir}/{DEFAULT_RECEIPT_FILE}"
    selected_route_id = getattr(args, "route_id", None)
    route_id = str(
        selected_route_id
        or (
            DEFAULT_AUTHORIZED_ANDROID_ROUTE_ID
            if broker_authority
            else DEFAULT_ANDROID_ROUTE_ID
        )
    )
    required_stages = string_list(
        getattr(args, "required_stage", None)
        or (
            DEFAULT_AUTHORIZED_ANDROID_REQUIRED_STAGES
            if broker_authority
            else DEFAULT_ANDROID_REQUIRED_STAGES
        ),
        "required_stage",
    )
    stage_observations: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    broker_messages: list[dict[str, Any]] = []
    command_envelope: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None

    try:
        if broker_authority:
            if getattr(args, "adb_forward_broker", False):
                actions.append(
                    adb_forward_broker(
                        args,
                        run_func=run_func,
                    )
                )
            authority = execute_broker_authority_review(
                request,
                args=args,
                broker_client_factory=broker_client_factory or BrokerWebSocketClient,
                clock_ms_func=clock,
            )
            command_envelope = authority["command_envelope"]
            broker_messages = authority["broker_messages"]
            actions.extend(authority["actions"])
            stage_observations.extend(authority["stage_observations"])
            issues.extend(authority["issues"])
        if not issues:
            run_func(
                [
                    args.adb,
                    "-s",
                    args.serial,
                    "shell",
                    "run-as",
                    package,
                    "mkdir",
                    "-p",
                    remote_dir,
                ]
            )
            run_func(
                [
                    args.adb,
                    "-s",
                    args.serial,
                    "shell",
                    "run-as",
                    package,
                    "rm",
                    "-f",
                    receipt_relative,
                ],
                allow_failure=True,
            )
            staged_request = request_for_runtime_delivery(request, broker_authority=broker_authority)
            write_app_file_func(
                args,
                package,
                request_relative,
                json.dumps(staged_request, indent=2, sort_keys=True).encode("utf-8") + b"\n",
            )
            observed_at_ms = int(clock())
            if not broker_authority:
                add_stage(
                    stage_observations,
                    "sent",
                    "pass",
                    observed_at_ms,
                    ["evidence.hostess.bridge_command.android_request"],
                )
                add_stage(
                    stage_observations,
                    "transport_ok",
                    "pass",
                    observed_at_ms,
                    ["evidence.hostess.android.run_as_app_private_write"],
                )
            actions.append(
                {
                    "action": "stage-app-private-command-request",
                    "status": "pass",
                    "package": package,
                    "relative_path": request_relative,
                    "broker_authority_required": broker_authority,
                }
            )
            if not getattr(args, "no_launch", False):
                run_func([args.adb, "-s", args.serial, "shell", "am", "start", "-W", "-n", activity])
                actions.append(
                    {
                        "action": "launch-makepad-xr-activity",
                        "status": "pass",
                        "activity": activity,
                    }
                )
            wait_app_file_func(
                args,
                package,
                receipt_relative,
                float(getattr(args, "wait_seconds", 20.0)),
                run=run_func,
            )
            receipt_payload = read_app_file_func(args, package, receipt_relative)
            receipt = json.loads(receipt_payload.decode("utf-8"))
            actions.append(
                {
                    "action": "pull-app-private-command-receipt",
                    "status": "pass",
                    "package": package,
                    "relative_path": receipt_relative,
                }
            )
            stage_observations.extend(stage_observations_from_runtime_receipt(receipt, int(clock())))
    except SystemExit as exc:
        issues.append(
            {
                "issue_code": "hostess.issue.bridge_command.android_execution_failed",
                "severity": "error",
                "message": system_exit_message(exc),
            }
        )
    except Exception as exc:
        issues.append(
            {
                "issue_code": "hostess.issue.bridge_command.android_execution_failed",
                "severity": "error",
                "message": str(exc),
            }
        )

    logcat_artifact = collect_logcat(
        args,
        run_captured_func=run_captured_func,
        logcat_out=logcat_out,
        request_id=str(request.get("request_id") or ""),
    )
    if logcat_artifact:
        actions.append(logcat_artifact)

    passed_stages = {
        str(stage.get("stage"))
        for stage in stage_observations
        if stage.get("status") != "fail"
    }
    missing = [stage for stage in required_stages if stage not in passed_stages]
    if missing:
        issues.append(
            {
                "issue_code": "hostess.issue.bridge_command.missing_required_stage",
                "severity": "error",
                "message": f"missing Android bridge command stages: {', '.join(missing)}",
            }
        )
    status = "fail" if issues or any(stage.get("status") == "fail" for stage in stage_observations) else "pass"
    ended_at_ms = int(clock())
    bridge_input = {
        "$schema": HOSTESS_BRIDGE_ROUTE_INPUT_SCHEMA,
        "evidence_id": str(
            request.get("evidence_id")
            or f"evidence.hostess.bridge_command.android.{request.get('command', 'unknown')}"
        ),
        "route_id": route_id,
        "status": status,
        "started_at_ms": started_at_ms,
        "ended_at_ms": max(started_at_ms, ended_at_ms),
        "required_evidence_stages": required_stages,
        "stage_observations": stage_observations,
        "artifact_refs": [
            "artifact.hostess.bridge_command.android_execution",
            "artifact.hostess.bridge_command.android_runtime_receipt",
        ],
        "issues": issues,
    }
    bridge_evidence = normalize_bridge_route_evidence(bridge_input)
    return {
        "$schema": BRIDGE_COMMAND_ANDROID_EXECUTION_SCHEMA,
        "status": status,
        "started_at_ms": started_at_ms,
        "ended_at_ms": max(started_at_ms, ended_at_ms),
        "route_id": route_id,
        "original_request_route_id": request.get("route_id"),
        "request_schema": BRIDGE_COMMAND_REQUEST_SCHEMA,
        "runtime_receipt_schema": BRIDGE_COMMAND_RUNTIME_RECEIPT_SCHEMA,
        "request_id": request.get("request_id"),
        "command": request.get("command"),
        "required_evidence_stages": required_stages,
        "android": {
            "adb": args.adb,
            "serial": args.serial,
            "package": package,
            "activity": activity,
            "remote_request": request_relative,
            "remote_receipt": receipt_relative,
            "transport": "android-app-private-json",
        },
        "broker_authority": {
            "enabled": broker_authority,
            "host": broker_authority_host(args),
            "port": broker_authority_connect_port(args),
            "target_port": broker_authority_target_port(args),
            "adb_forward": bool(getattr(args, "adb_forward_broker", False)),
            "local_port": broker_authority_connect_port(args),
            "path": str(getattr(args, "broker_path", None) or MANIFOLD_BROKER_EVENTS_PATH),
            "client_id": ANDROID_AUTHORITY_CLIENT_ID,
            "command_envelope": command_envelope,
            "broker_messages": broker_messages,
        },
        "actions": actions,
        "runtime_receipt": receipt,
        "stage_observations": stage_observations,
        "issues": issues,
        "bridge_route_evidence_schema": MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
        "bridge_route_evidence": bridge_evidence,
    }


def execute_broker_authority_review(
    request: dict[str, Any],
    *,
    args: argparse.Namespace,
    broker_client_factory: Any,
    clock_ms_func: Any,
) -> dict[str, Any]:
    stage_observations: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    broker_messages: list[dict[str, Any]] = []
    command = str(request.get("command") or "")
    request_id = str(request.get("request_id") or "")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}
    command_envelope = broker_command_message(
        command,
        params=params,
        request_id=request_id,
        client_id=ANDROID_AUTHORITY_CLIENT_ID,
    )
    client = None
    try:
        client = broker_client_factory(
            broker_authority_host(args),
            broker_authority_connect_port(args),
            path=str(getattr(args, "broker_path", None) or MANIFOLD_BROKER_EVENTS_PATH),
            timeout=float(getattr(args, "connect_timeout_seconds", 5.0)),
        )
        client.send_json(command_envelope)
        add_stage(
            stage_observations,
            "sent",
            "pass",
            int(clock_ms_func()),
            ["evidence.hostess.bridge_command.broker_command_envelope"],
        )
        actions.append(
            {
                "action": "request-broker-command-authority",
                "status": "sent",
                "request_id": request_id,
                "command": command,
            }
        )
        accepted = wait_for_broker_authority_ack(
            client,
            request_id=request_id,
            command=command,
            wait_seconds=float(getattr(args, "authority_wait_seconds", None) or getattr(args, "wait_seconds", 5.0)),
            clock_ms_func=clock_ms_func,
            stage_observations=stage_observations,
            broker_messages=broker_messages,
            issues=issues,
        )
        actions.append(
            {
                "action": "broker-command-authority",
                "status": "pass" if accepted else "fail",
                "request_id": request_id,
                "command": command,
            }
        )
    except Exception as exc:
        issues.append(
            {
                "issue_code": "hostess.issue.bridge_command.broker_authority_failed",
                "severity": "error",
                "message": str(exc),
            }
        )
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
    return {
        "status": "pass" if not issues else "fail",
        "command_envelope": command_envelope,
        "broker_messages": broker_messages,
        "stage_observations": stage_observations,
        "issues": issues,
        "actions": actions,
    }


def adb_forward_broker(args: argparse.Namespace, *, run_func: Any) -> dict[str, Any]:
    local_port = broker_authority_connect_port(args)
    remote_port = broker_authority_target_port(args)
    run_func(
        [
            args.adb,
            "-s",
            args.serial,
            "forward",
            f"tcp:{local_port}",
            f"tcp:{remote_port}",
        ]
    )
    return {
        "action": "adb-forward-broker",
        "status": "pass",
        "serial": args.serial,
        "local_port": local_port,
        "remote_port": remote_port,
    }


def broker_authority_host(args: argparse.Namespace) -> str:
    return str(getattr(args, "broker_host", None) or "127.0.0.1")


def broker_authority_connect_port(args: argparse.Namespace) -> int:
    if getattr(args, "adb_forward_broker", False):
        return int(getattr(args, "broker_local_port", None) or getattr(args, "broker_port", None) or 8765)
    return int(getattr(args, "broker_port", None) or 8765)


def broker_authority_target_port(args: argparse.Namespace) -> int:
    return int(getattr(args, "broker_port", None) or 8765)


def wait_for_broker_authority_ack(
    client: Any,
    *,
    request_id: str,
    command: str,
    wait_seconds: float,
    clock_ms_func: Any,
    stage_observations: list[dict[str, Any]],
    broker_messages: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> bool:
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while time.monotonic() <= deadline:
        remaining = max(0.01, min(0.25, deadline - time.monotonic()))
        message = client.recv_json(timeout=remaining)
        if message is None:
            if time.monotonic() >= deadline:
                break
            continue
        if not isinstance(message, dict) or not command_message_matches(
            message,
            request_id=request_id,
            command=command,
        ):
            continue
        broker_messages.append(message)
        observed_at_ms = int(clock_ms_func())
        if broker_ack_accepted(message):
            add_stage(
                stage_observations,
                "transport_ok",
                "pass",
                observed_at_ms,
                ["evidence.hostess.bridge_command.broker_ack"],
            )
            add_stage(
                stage_observations,
                "authority_accepted",
                "pass",
                observed_at_ms,
                ["evidence.manifold.command_ack"],
            )
            return True
        add_stage(
            stage_observations,
            "rejected",
            "fail",
            observed_at_ms,
            ["evidence.manifold.command_ack"],
            ["hostess.issue.bridge_command.authority_rejected"],
        )
        issues.append(
            {
                "issue_code": "hostess.issue.bridge_command.authority_rejected",
                "severity": "error",
                "message": "broker command authority rejected the Android runtime request",
            }
        )
        return False
    issues.append(
        {
            "issue_code": "hostess.issue.bridge_command.broker_authority_timeout",
            "severity": "error",
            "message": "timed out waiting for broker command authority acceptance",
        }
    )
    return False


def command_message_matches(message: dict[str, Any], *, request_id: str, command: str) -> bool:
    payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
    return (
        bool(request_id)
        and (
            message.get("request_id") == request_id
            or payload.get("request_id") == request_id
        )
    ) or (
        bool(command)
        and (
            message.get("command") == command
            or payload.get("command") == command
        )
    )


def request_for_runtime_delivery(
    request: dict[str, Any],
    *,
    broker_authority: bool,
) -> dict[str, Any]:
    if not broker_authority:
        return request
    staged = dict(request)
    params = dict(staged.get("params") if isinstance(staged.get("params"), dict) else {})
    params["source"] = "manifold-authorized-app-private-json"
    params["broker_authority_accepted"] = True
    staged["params"] = params
    return staged


def stage_observations_from_runtime_receipt(
    receipt: dict[str, Any],
    observed_at_ms: int,
) -> list[dict[str, Any]]:
    if receipt.get("$schema") != BRIDGE_COMMAND_RUNTIME_RECEIPT_SCHEMA:
        return [
            {
                "stage": "rejected",
                "status": "fail",
                "observed_at_ms": observed_at_ms,
                "evidence_refs": ["evidence.quest.runtime_receipt"],
                "issue_codes": ["hostess.issue.bridge_command.runtime_receipt_schema"],
            }
        ]
    rows: list[dict[str, Any]] = []
    receipts = receipt.get("stage_receipts")
    if isinstance(receipts, list):
        for item in receipts:
            if not isinstance(item, dict):
                continue
            stage = str(item.get("stage") or "")
            if not stage:
                continue
            rows.append(
                {
                    "stage": stage,
                    "status": normalize_stage_status(item.get("status")),
                    "observed_at_ms": observed_at_ms,
                    "evidence_refs": string_list(
                        item.get("evidence_refs") or item.get("evidence_ref") or [],
                        "evidence_refs",
                    ),
                    "issue_codes": string_list(item.get("issue_codes") or [], "issue_codes"),
                }
            )
    if receipt.get("runtime_accepted") is True and not any(
        row.get("stage") == "runtime_accepted" for row in rows
    ):
        rows.append(
            {
                "stage": "runtime_accepted",
                "status": "pass",
                "observed_at_ms": observed_at_ms,
                "evidence_refs": ["evidence.quest.runtime_receipt"],
                "issue_codes": [],
            }
        )
    if receipt.get("applied") is True and not any(row.get("stage") == "applied" for row in rows):
        rows.append(
            {
                "stage": "applied",
                "status": "pass",
                "observed_at_ms": observed_at_ms,
                "evidence_refs": ["evidence.quest.effective_state_marker"],
                "issue_codes": [],
            }
        )
    return rows


def collect_logcat(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    logcat_out: Path | None,
    request_id: str,
) -> dict[str, Any] | None:
    if logcat_out is None:
        return None
    result = run_captured_func(
        [args.adb, "-s", args.serial, "logcat", "-d", "-v", "time", "-s", "HostessMakepad:I"],
        allow_failure=True,
    )
    text = result.stdout or ""
    logcat_out.parent.mkdir(parents=True, exist_ok=True)
    logcat_out.write_text(text, encoding="utf-8")
    matched = request_id in text if request_id else False
    return {
        "action": "capture-hostess-makepad-logcat",
        "status": "pass" if result.returncode == 0 else "warn",
        "artifact": str(logcat_out),
        "returncode": result.returncode,
        "request_id_seen": matched,
    }


def normalize_relative_dir(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    if not normalized or normalized.startswith("/") or ".." in normalized.split("/"):
        raise ValueError(f"invalid app-private relative dir: {value!r}")
    return normalized


def add_stage(
    stage_observations: list[dict[str, Any]],
    stage: str,
    status: str,
    observed_at_ms: int,
    evidence_refs: list[str],
    issue_codes: list[str] | None = None,
) -> None:
    stage_observations.append(
        {
            "stage": stage,
            "status": status,
            "observed_at_ms": observed_at_ms,
            "evidence_refs": evidence_refs,
            "issue_codes": issue_codes or [],
        }
    )


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON file did not contain an object: {path}")
    return value


def string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a string list")
    return [str(item) for item in value]


def normalize_stage_status(value: Any) -> str:
    status = str(value or "pass").strip().lower()
    if status in {"pass", "passed", "ok", "success", "accepted", "applied"}:
        return "pass"
    if status in {"warn", "warning", "stale"}:
        return "warn"
    return "fail"


def epoch_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def default_run(command: list[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True)
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result


def default_run_captured(
    command: list[str], *, allow_failure: bool = False
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result


def system_exit_message(exc: SystemExit) -> str:
    if exc.code is None:
        return "system exit"
    return str(exc.code)


__all__ = [
    "BRIDGE_COMMAND_ANDROID_EXECUTION_SCHEMA",
    "BRIDGE_COMMAND_RUNTIME_RECEIPT_SCHEMA",
    "DEFAULT_ANDROID_ROUTE_ID",
    "execute_bridge_command_android_request",
    "run_bridge_command_android",
]
