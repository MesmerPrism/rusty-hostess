"""Frontend-neutral bridge command execution routes for hostessctl."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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


BRIDGE_COMMAND_REQUEST_SCHEMA = "rusty.hostess.bridge_command.request.v1"
BRIDGE_COMMAND_EXECUTION_SCHEMA = "rusty.hostess.bridge_command.execution_evidence.v1"
DEFAULT_COMMAND_ROUTE_ID = "bridge_route.command.websocket.applied"
DEFAULT_REQUIRED_STAGES = [
    "sent",
    "transport_ok",
    "authority_accepted",
    "runtime_accepted",
    "applied",
]
DEFAULT_RUNTIME_RECEIPT_STREAM = "stream.hostess.makepad.bridge_command.receipt"
CLIENT_ID = "hostessctl.bridge_command"
RUNTIME_RECEIPT_TYPES = {
    "runtime_receipt",
    "command_receipt",
    "command_runtime_receipt",
    "bridge_route_receipt",
}


def run_emit_bridge_command_request(args: argparse.Namespace) -> int:
    params = bridge_command_request_params(args)
    request = bridge_command_request_artifact(
        bridge_command=str(args.bridge_command),
        request_id=str(getattr(args, "request_id", "") or ""),
        evidence_id=str(getattr(args, "evidence_id", "") or ""),
        route_id=str(getattr(args, "route_id", "") or DEFAULT_COMMAND_ROUTE_ID),
        required_stages=getattr(args, "required_stage", None) or None,
        params=params,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    load_bridge_command_request(out)
    return 0


def bridge_command_request_artifact(
    *,
    bridge_command: str,
    request_id: str = "",
    evidence_id: str = "",
    route_id: str = DEFAULT_COMMAND_ROUTE_ID,
    required_stages: list[str] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    command = bridge_command.strip()
    if not command:
        raise ValueError("bridge command request command is required")
    slug = bridge_command_slug(command)
    return {
        "$schema": BRIDGE_COMMAND_REQUEST_SCHEMA,
        "request_id": request_id or f"request.hostess.bridge_command.{slug}",
        "evidence_id": evidence_id or f"evidence.hostess.bridge_command.{slug}",
        "route_id": route_id or DEFAULT_COMMAND_ROUTE_ID,
        "command": command,
        "params": params or {},
        "required_evidence_stages": required_stages or list(DEFAULT_REQUIRED_STAGES),
    }


def bridge_command_request_params(args: argparse.Namespace) -> dict[str, Any]:
    params_json = str(getattr(args, "params_json", "") or "")
    params_json_file = str(getattr(args, "params_json_file", "") or "")
    if params_json and params_json_file:
        raise ValueError("--params-json and --params-json-file are mutually exclusive")
    if params_json_file:
        value = load_json_object(Path(params_json_file))
    elif params_json:
        value = json.loads(params_json)
        if not isinstance(value, dict):
            raise ValueError("--params-json must decode to a JSON object")
    else:
        value = {}
    return value


def bridge_command_slug(command: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", command.strip())
    slug = slug.replace(".", "_").replace("-", "_").strip("_")
    return slug or "request"


def run_bridge_command(
    args: argparse.Namespace,
    *,
    broker_client_factory: Any | None = None,
    clock_ms_func: Any | None = None,
) -> int:
    request = load_bridge_command_request(Path(args.input))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    execution_out = (
        Path(args.execution_out)
        if getattr(args, "execution_out", None)
        else out.with_name(f"{out.stem}.command-execution.json")
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
    execution = execute_bridge_command_request(
        request,
        broker_host=str(args.broker_host),
        broker_port=int(args.broker_port),
        broker_path=str(args.broker_path),
        connect_timeout_seconds=float(args.connect_timeout_seconds),
        wait_seconds=float(args.wait_seconds),
        runtime_receipt_stream=(
            None
            if getattr(args, "no_runtime_receipt_subscribe", False)
            else str(getattr(args, "runtime_receipt_stream", None) or DEFAULT_RUNTIME_RECEIPT_STREAM)
        ),
        broker_client_factory=broker_client_factory or BrokerWebSocketClient,
        clock_ms_func=clock_ms_func,
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


def execute_bridge_command_request(
    request: dict[str, Any],
    *,
    broker_host: str,
    broker_port: int,
    broker_path: str,
    connect_timeout_seconds: float,
    wait_seconds: float,
    broker_client_factory: Any,
    runtime_receipt_stream: str | None = DEFAULT_RUNTIME_RECEIPT_STREAM,
    clock_ms_func: Any | None = None,
) -> dict[str, Any]:
    clock = clock_ms_func or epoch_ms
    started_at_ms = int(clock())
    route_id = str(request.get("route_id") or DEFAULT_COMMAND_ROUTE_ID)
    request_id = str(request.get("request_id") or "")
    command = str(request.get("command") or "")
    params = request.get("params") if isinstance(request.get("params"), dict) else {}
    evidence_id = str(
        request.get("evidence_id")
        or f"evidence.hostess.bridge_command.{command.replace('-', '_').replace('.', '_')}"
    )
    required_stages = string_list(
        request.get("required_evidence_stages") or DEFAULT_REQUIRED_STAGES,
        "required_evidence_stages",
    )
    broker_messages: list[dict[str, Any]] = []
    stage_observations: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    command_envelope = broker_command_message(
        command,
        params=params,
        request_id=request_id,
        client_id=CLIENT_ID,
    )
    runtime_receipt_subscription_envelope = (
        broker_command_message(
            "subscribe",
            params={"stream": runtime_receipt_stream, "receiver": CLIENT_ID},
            request_id=f"{request_id}.runtime_receipt_subscribe",
            client_id=CLIENT_ID,
        )
        if runtime_receipt_stream
        else None
    )
    client = None
    try:
        client = broker_client_factory(
            broker_host,
            broker_port,
            path=broker_path,
            timeout=connect_timeout_seconds,
        )
        if runtime_receipt_subscription_envelope is not None:
            client.send_json(runtime_receipt_subscription_envelope)
        client.send_json(command_envelope)
        add_stage(
            stage_observations,
            "sent",
            "pass",
            int(clock()),
            ["evidence.hostess.bridge_command.command_envelope"],
        )
        wait_for_command_receipts(
            client,
            request_id=request_id,
            command=command,
            required_stages=required_stages,
            wait_seconds=wait_seconds,
            clock_ms_func=clock,
            broker_messages=broker_messages,
            stage_observations=stage_observations,
            issues=issues,
        )
    except Exception as exc:
        issues.append(
            {
                "issue_code": "hostess.issue.bridge_command.execution_failed",
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

    passed_stages = {
        str(stage.get("stage"))
        for stage in stage_observations
        if stage.get("status") != "fail"
    }
    missing = [stage for stage in required_stages if stage not in passed_stages]
    if missing and not any(
        issue.get("issue_code") == "hostess.issue.bridge_command.missing_required_stage"
        for issue in issues
    ):
        issues.append(
            {
                "issue_code": "hostess.issue.bridge_command.missing_required_stage",
                "severity": "error",
                "message": f"missing bridge command stages: {', '.join(missing)}",
            }
        )
    status = "fail" if issues or any(stage.get("status") == "fail" for stage in stage_observations) else "pass"
    ended_at_ms = int(clock())
    bridge_input = {
        "$schema": HOSTESS_BRIDGE_ROUTE_INPUT_SCHEMA,
        "evidence_id": evidence_id,
        "route_id": route_id,
        "status": status,
        "started_at_ms": started_at_ms,
        "ended_at_ms": max(started_at_ms, ended_at_ms),
        "required_evidence_stages": required_stages,
        "stage_observations": stage_observations,
        "artifact_refs": [
            "artifact.hostess.bridge_command.command_execution",
            "artifact.hostess.bridge_command.validation_report",
        ],
        "issues": issues,
    }
    bridge_evidence = normalize_bridge_route_evidence(bridge_input)
    return {
        "$schema": BRIDGE_COMMAND_EXECUTION_SCHEMA,
        "status": status,
        "started_at_ms": started_at_ms,
        "ended_at_ms": max(started_at_ms, ended_at_ms),
        "route_id": route_id,
        "request_id": request_id,
        "command": command,
        "required_evidence_stages": required_stages,
        "broker": {
            "host": broker_host,
            "port": broker_port,
            "path": broker_path,
            "client_id": CLIENT_ID,
            "runtime_receipt_stream": runtime_receipt_stream,
            "runtime_receipt_subscribed": runtime_receipt_subscription_envelope is not None,
        },
        "command_envelope": command_envelope,
        "runtime_receipt_subscription_envelope": runtime_receipt_subscription_envelope,
        "broker_messages": broker_messages,
        "stage_observations": stage_observations,
        "issues": issues,
        "bridge_route_evidence_schema": MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
        "bridge_route_evidence": bridge_evidence,
    }


def wait_for_command_receipts(
    client: Any,
    *,
    request_id: str,
    command: str,
    required_stages: list[str],
    wait_seconds: float,
    clock_ms_func: Any,
    broker_messages: list[dict[str, Any]],
    stage_observations: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while time.monotonic() <= deadline:
        remaining = max(0.01, min(0.25, deadline - time.monotonic()))
        message = client.recv_json(timeout=remaining)
        if message is None:
            if time.monotonic() >= deadline:
                break
            continue
        if not isinstance(message, dict):
            continue
        if not command_message_matches(message, request_id=request_id, command=command):
            continue
        broker_messages.append(message)
        observed_at_ms = int(clock_ms_func())
        if is_authority_ack(message, request_id=request_id, command=command):
            record_authority_ack(
                message,
                observed_at_ms=observed_at_ms,
                stage_observations=stage_observations,
                issues=issues,
            )
        for stage in stage_observations_from_receipt(message):
            add_stage(
                stage_observations,
                stage["stage"],
                stage["status"],
                observed_at_ms,
                stage["evidence_refs"],
                stage["issue_codes"],
            )
            if stage["status"] == "fail":
                issues.append(
                    {
                        "issue_code": stage["issue_codes"][0]
                        if stage["issue_codes"]
                        else "hostess.issue.bridge_command.stage_failed",
                        "severity": "error",
                        "message": f"bridge command stage {stage['stage']} failed",
                    }
                )
        passed_stages = {
            str(stage.get("stage"))
            for stage in stage_observations
            if stage.get("status") != "fail"
        }
        if all(stage in passed_stages for stage in required_stages):
            return


def record_authority_ack(
    message: dict[str, Any],
    *,
    observed_at_ms: int,
    stage_observations: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
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
    else:
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
                "message": "broker command authority rejected the request",
            }
        )


def stage_observations_from_receipt(message: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    receipt = runtime_receipt_body(message)
    receipts = receipt.get("stage_receipts")
    if isinstance(receipts, list):
        for item in receipts:
            if not isinstance(item, dict):
                continue
            stage = str(item.get("stage") or "")
            if not stage:
                continue
            rows.append(stage_row_from_message(item, stage))
    stage = receipt.get("bridge_route_stage") or receipt.get("stage")
    if isinstance(stage, str) and stage in {
        "runtime_accepted",
        "applied",
        "observed",
        "rejected",
        "stale",
    }:
        rows.append(stage_row_from_message(receipt, stage))
    for field, stage_name in (
        ("runtime_accepted", "runtime_accepted"),
        ("applied", "applied"),
        ("observed", "observed"),
        ("rejected", "rejected"),
        ("stale", "stale"),
    ):
        if receipt.get(field) is True:
            rows.append(stage_row_from_message(receipt, stage_name))
    return dedupe_stage_rows(rows)


def stage_row_from_message(message: dict[str, Any], stage: str) -> dict[str, Any]:
    status = normalize_stage_status(message.get("status"))
    if stage in {"rejected", "stale"} and status == "pass":
        status = "fail"
    if message.get("accepted") is False:
        status = "fail"
    issue_codes = string_list(message.get("issue_codes", []), "issue_codes")
    if status == "fail" and not issue_codes:
        issue_codes = [f"hostess.issue.bridge_command.{stage}"]
    refs = string_list(
        message.get("evidence_refs")
        or message.get("evidence_ref")
        or f"evidence.hostess.bridge_command.{stage}",
        "evidence_refs",
    )
    return {
        "stage": stage,
        "status": status,
        "evidence_refs": refs,
        "issue_codes": issue_codes,
    }


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


def is_authority_ack(message: dict[str, Any], *, request_id: str, command: str) -> bool:
    message_type = str(message.get("type") or "")
    payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
    if message_type == "stream_event":
        return False
    if message_type in RUNTIME_RECEIPT_TYPES:
        return False
    if message.get("bridge_route_stage") or message.get("stage"):
        return False
    if payload.get("bridge_route_stage") or payload.get("stage"):
        return False
    if any(payload.get(field) is True for field in ("runtime_accepted", "applied", "observed", "rejected", "stale")):
        return False
    return command_message_matches(message, request_id=request_id, command=command)


def runtime_receipt_body(message: dict[str, Any]) -> dict[str, Any]:
    if message.get("type") == "stream_event" and isinstance(message.get("payload"), dict):
        return message["payload"]
    return message


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


def dedupe_stage_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result = []
    for row in rows:
        key = (str(row.get("stage")), str(row.get("status")))
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def load_bridge_command_request(path: Path) -> dict[str, Any]:
    request = load_json_object(path)
    if request.get("$schema") != BRIDGE_COMMAND_REQUEST_SCHEMA:
        raise ValueError(f"unsupported bridge command request schema: {request.get('$schema')!r}")
    if not request.get("request_id"):
        raise ValueError("bridge command request is missing request_id")
    if not request.get("command"):
        raise ValueError("bridge command request is missing command")
    params = request.get("params")
    if params is not None and not isinstance(params, dict):
        raise ValueError("bridge command request params must be an object")
    return request


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
    if status in {"fail", "failed", "error", "rejected", "timeout"}:
        return "fail"
    return "pass"


def epoch_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def default_broker_path() -> str:
    return MANIFOLD_BROKER_EVENTS_PATH


__all__ = [
    "BRIDGE_COMMAND_EXECUTION_SCHEMA",
    "BRIDGE_COMMAND_REQUEST_SCHEMA",
    "DEFAULT_COMMAND_ROUTE_ID",
    "DEFAULT_RUNTIME_RECEIPT_STREAM",
    "bridge_command_request_artifact",
    "execute_bridge_command_request",
    "run_emit_bridge_command_request",
    "run_bridge_command",
]
