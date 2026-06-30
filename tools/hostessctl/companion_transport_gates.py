"""Read-only transport gate reports derived from companion projections."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.companion_report_projection import (
    HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA,
)
from tools.hostessctl.companion_transport_gate_actions import (
    operator_next_actions_for_gate,
    operator_next_actions_summary,
    validate_next_actions_for_gate,
)


HOSTESS_COMPANION_TRANSPORT_GATE_REPORT_SCHEMA = (
    "rusty.hostess.companion.transport_gate_report.v1"
)
HOSTESS_COMPANION_TRANSPORT_GATE_VALIDATION_SCHEMA = (
    "rusty.hostess.companion.transport_gate_report.validation.v1"
)
TRANSPORT_COVERAGE_ROW_ID = "transport_coverage.summary"
PROTOCOL_MATRIX_SUMMARY_ROW_ID = "protocol_matrix.summary"


def run_companion_transport_gates(
    args: argparse.Namespace,
    *,
    clock_func: Callable[[], datetime] | None = None,
) -> int:
    report = build_companion_transport_gate_report(
        args,
        clock_func=clock_func or utc_now,
    )
    validation = validate_companion_transport_gate_report(report)

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
    if getattr(args, "fail_on_pending", False) and report["summary"]["remaining_gate_count"]:
        return 2
    if (
        getattr(args, "fail_on_incomplete", False)
        and not report["summary"]["all_wpf_transport_and_protocol_gates_clear"]
    ):
        return 2
    return 0


def build_companion_transport_gate_report(
    args: argparse.Namespace,
    *,
    clock_func: Callable[[], datetime],
) -> dict[str, Any]:
    generated_at = clock_func()
    projection_path = Path(args.projection)
    projection = read_json(projection_path)
    issues: list[dict[str, Any]] = []

    coverage_row = transport_coverage_row(projection)
    if not projection:
        issues.append(issue("hostess.issue.transport_gates.projection_unreadable", "error"))
    elif projection.get("$schema") != HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA:
        issues.append(issue("hostess.issue.transport_gates.unsupported_projection_schema", "error"))
    if not coverage_row:
        issues.append(issue("hostess.issue.transport_gates.coverage_row_missing", "error"))

    details = object_value(coverage_row.get("details")) if coverage_row else {}
    data_protocols = protocol_matrix_data_protocol_summary(projection)
    term_gates = object_value(details.get("term_gates"))
    remaining_live_gates = [
        normalize_remaining_gate(gate)
        for gate in list_objects(details.get("remaining_live_gates"))
    ]
    remaining_gate_ids = [
        str(gate.get("gate_id") or "")
        for gate in remaining_live_gates
        if str(gate.get("gate_id") or "")
    ]
    report_id = str(getattr(args, "report_id", None) or "").strip()
    if not report_id:
        report_id = f"transport-gates-{generated_at.strftime('%Y%m%d-%H%M%S')}"
    all_required_data_protocols_promoted = bool(
        data_protocols.get("all_required_data_protocols_promoted")
    )
    all_transport_gates_clear = not remaining_gate_ids and not any_error(issues)
    completion_blockers = []
    if not all_required_data_protocols_promoted:
        completion_blockers.append("protocol_matrix.required_data_protocols")
    completion_blockers.extend(remaining_gate_ids)

    return {
        "$schema": HOSTESS_COMPANION_TRANSPORT_GATE_REPORT_SCHEMA,
        "schema_version": 1,
        "report_id": report_id,
        "generated_at_utc": generated_at.isoformat().replace("+00:00", "Z"),
        "status": (
            "fail"
            if any_error(issues)
            else ("warn" if completion_blockers else "pass")
        ),
        "authority": {
            "ui_role": "requester_and_inspector",
            "projection_only": True,
            "source_artifact": "rusty.hostess.companion.report_projection.v1",
            "acceptance_owner": "source_projection",
            "requires_data_protocol_matrix": True,
            "policy": (
                "This report summarizes transport gates already emitted by "
                "companion-report projection and the data-protocol completion "
                "state already emitted by the protocol matrix. It does not run "
                "probes, change firewall/device state, parse media, or promote "
                "protocols."
            ),
        },
        "source_projection": {
            "path": str(projection_path),
            "schema": projection.get("$schema") or projection.get("schema"),
            "projection_id": projection.get("projection_id"),
            "status": projection.get("status") if projection else "unreadable",
            "sha256": sha256_file(projection_path),
        },
        "summary": {
            "all_transport_gates_clear": all_transport_gates_clear,
            "all_required_data_protocols_promoted": all_required_data_protocols_promoted,
            "all_wpf_transport_and_protocol_gates_clear": (
                all_transport_gates_clear and all_required_data_protocols_promoted
            ),
            "completion_blockers": completion_blockers,
            "remaining_gate_count": len(remaining_gate_ids),
            "remaining_gate_ids": remaining_gate_ids,
            "term_gate_count": len(term_gates),
            "term_gate_ids": sorted(term_gates.keys()),
        },
        "data_protocols": data_protocols,
        "operator_next_actions": operator_next_actions_summary(remaining_live_gates),
        "term_gates": term_gates,
        "remaining_live_gates": remaining_live_gates,
        "issues": issues,
    }


def validate_companion_transport_gate_report(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if report.get("$schema") != HOSTESS_COMPANION_TRANSPORT_GATE_REPORT_SCHEMA:
        errors.append("unsupported companion transport gate report schema")
    if object_value(report.get("authority")).get("projection_only") is not True:
        errors.append("transport gate report must set projection_only=true")
    source = object_value(report.get("source_projection"))
    if source.get("schema") != HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA:
        errors.append("source_projection must be a companion report projection")
    if not str(source.get("path") or "").strip():
        errors.append("source_projection missing path")
    summary = object_value(report.get("summary"))
    data_protocols = object_value(report.get("data_protocols"))
    remaining = list_value(report.get("remaining_live_gates"))
    operator_next_actions = object_value(report.get("operator_next_actions"))
    if int_value(summary.get("remaining_gate_count")) != len(remaining):
        errors.append("remaining_gate_count does not match remaining_live_gates")
    if bool(summary.get("all_required_data_protocols_promoted")) != bool(
        data_protocols.get("all_required_data_protocols_promoted")
    ):
        errors.append(
            "summary all_required_data_protocols_promoted does not match data_protocols"
        )
    if bool(summary.get("all_wpf_transport_and_protocol_gates_clear")) and remaining:
        errors.append(
            "all_wpf_transport_and_protocol_gates_clear cannot be true with remaining gates"
        )
    if bool(summary.get("all_wpf_transport_and_protocol_gates_clear")) and not bool(
        data_protocols.get("all_required_data_protocols_promoted")
    ):
        errors.append(
            "all_wpf_transport_and_protocol_gates_clear cannot be true without promoted data protocols"
        )
    if not data_protocols.get("protocol_matrix_present"):
        warnings.append("protocol matrix summary is missing")
    elif not data_protocols.get("all_required_data_protocols_promoted"):
        warnings.append("required data protocols are not all promoted")
    for gate in remaining:
        gate_id = str(object_value(gate).get("gate_id") or "")
        if not gate_id:
            errors.append("remaining gate missing gate_id")
        status = str(object_value(gate).get("status") or "")
        if status in {"pending_live_evidence", "not_in_current_scope"}:
            warnings.append(f"transport gate remains pending: {gate_id}")
            next_actions = list_objects(object_value(gate).get("next_actions"))
            errors.extend(validate_next_actions_for_gate(gate_id, next_actions))
    errors.extend(validate_operator_next_actions_summary(operator_next_actions, remaining))
    for report_issue in list_objects(report.get("issues")):
        if report_issue.get("severity") == "error":
            errors.append(str(report_issue.get("issue_code") or "transport gate issue"))
    return {
        "$schema": HOSTESS_COMPANION_TRANSPORT_GATE_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "report_id": report.get("report_id"),
        "source_projection": source.get("path"),
        "remaining_gate_count": len(remaining),
        "all_required_data_protocols_promoted": bool(
            data_protocols.get("all_required_data_protocols_promoted")
        ),
        "all_wpf_transport_and_protocol_gates_clear": bool(
            summary.get("all_wpf_transport_and_protocol_gates_clear")
        ),
        "errors": errors,
        "warnings": warnings,
    }


def validate_operator_next_actions_summary(
    operator_next_actions: dict[str, Any],
    remaining_live_gates: list[Any],
) -> list[str]:
    errors: list[str] = []
    if not operator_next_actions:
        return ["operator_next_actions summary missing"]
    if operator_next_actions.get("shell") != "powershell":
        errors.append("operator_next_actions shell must be powershell")
    gates = list_objects(operator_next_actions.get("gates"))
    if int_value(operator_next_actions.get("gate_count")) != len(gates):
        errors.append("operator_next_actions gate_count does not match gates")

    expected = remaining_gate_action_ids(remaining_live_gates)
    reported: dict[str, set[str]] = {}
    for gate in gates:
        gate_id = str(gate.get("gate_id") or "")
        if not gate_id:
            errors.append("operator_next_actions gate missing gate_id")
            continue
        if gate_id in reported:
            errors.append(f"duplicate operator_next_actions gate: {gate_id}")
        reported[gate_id] = {
            str(action_id)
            for action_id in list_value(gate.get("next_action_ids"))
            if str(action_id)
        }

    if set(reported.keys()) != set(expected.keys()):
        errors.append(
            "operator_next_actions gates do not match remaining_live_gates next_actions"
        )
    for gate_id in sorted(set(reported.keys()) & set(expected.keys())):
        if reported[gate_id] != expected[gate_id]:
            errors.append(
                f"operator_next_actions action ids do not match remaining_live_gates: {gate_id}"
            )
    return errors


def remaining_gate_action_ids(remaining_live_gates: list[Any]) -> dict[str, set[str]]:
    gate_actions: dict[str, set[str]] = {}
    for gate in list_objects(remaining_live_gates):
        gate_id = str(gate.get("gate_id") or "")
        next_actions = list_objects(object_value(gate).get("next_actions"))
        action_ids = {
            str(action.get("action_id") or "")
            for action in next_actions
            if str(action.get("action_id") or "")
        }
        if gate_id and action_ids:
            gate_actions[gate_id] = action_ids
    return gate_actions


def transport_coverage_row(projection: dict[str, Any]) -> dict[str, Any]:
    for row in list_objects(projection.get("rows")):
        if row.get("row_id") == TRANSPORT_COVERAGE_ROW_ID:
            return row
    return {}


def protocol_matrix_data_protocol_summary(projection: dict[str, Any]) -> dict[str, Any]:
    summary_row = protocol_matrix_summary_row(projection)
    details = object_value(summary_row.get("details"))
    present = bool(summary_row)
    return {
        "protocol_matrix_present": present,
        "row_id": str(summary_row.get("row_id") or ""),
        "status": str(summary_row.get("status") or ("missing" if not present else "unknown")),
        "source_artifact": str(summary_row.get("source_artifact") or ""),
        "source_path": str(summary_row.get("source_path") or ""),
        "all_required_data_protocols_promoted": (
            details.get("all_required_data_protocols_promoted") is True
        ),
        "required_promoted_count": int_value(details.get("required_promoted_count")),
        "promoted_count": int_value(details.get("promoted_count")),
        "required_count": int_value(details.get("required_count")),
        "candidate_count": int_value(details.get("candidate_count")),
        "missing_gate_count": int_value(details.get("missing_gate_count")),
        "issue_count": int_value(summary_row.get("issue_count")),
        "issue_codes": list_value(summary_row.get("issue_codes")),
    }


def protocol_matrix_summary_row(projection: dict[str, Any]) -> dict[str, Any]:
    for row in list_objects(projection.get("rows")):
        if row.get("row_id") == PROTOCOL_MATRIX_SUMMARY_ROW_ID:
            return row
    return {}


def normalize_remaining_gate(gate: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "gate_id": str(gate.get("gate_id") or ""),
        "status": str(gate.get("status") or "unknown"),
        "evidence": str(gate.get("evidence") or ""),
    }
    next_actions = operator_next_actions_for_gate(normalized["gate_id"])
    if next_actions:
        normalized["next_actions"] = next_actions
    return normalized


def any_error(issues: list[dict[str, Any]]) -> bool:
    return any(issue_row.get("severity") == "error" for issue_row in issues)


def issue(issue_code: str, severity: str) -> dict[str, Any]:
    return {
        "issue_code": issue_code,
        "severity": severity,
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def list_objects(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def int_value(value: Any) -> int:
    return value if isinstance(value, int) else 0


def utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "HOSTESS_COMPANION_TRANSPORT_GATE_REPORT_SCHEMA",
    "HOSTESS_COMPANION_TRANSPORT_GATE_VALIDATION_SCHEMA",
    "build_companion_transport_gate_report",
    "run_companion_transport_gates",
    "validate_companion_transport_gate_report",
]
