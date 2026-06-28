"""Manifold bridge-route evidence emission helpers for hostessctl."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HOSTESS_BRIDGE_ROUTE_INPUT_SCHEMA = "rusty.hostess.bridge_route_evidence_input.v1"
HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA = "rusty.hostess.bridge_route_evidence.validation.v1"
MANIFOLD_BRIDGE_ROUTE_DESCRIPTOR_SCHEMA = "rusty.manifold.bridge.route_descriptor.v1"
MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA = "rusty.manifold.bridge.route_evidence.v1"

VALID_STATUSES = {"pass", "warn", "fail"}
VALID_SEVERITIES = {"info", "warning", "error"}
VALID_STAGES = {
    "sent",
    "transport_ok",
    "authority_accepted",
    "runtime_accepted",
    "applied",
    "observed",
    "rejected",
    "stale",
    "artifact_captured",
}

DEFAULT_REQUIRED_STAGES: dict[str, tuple[str, ...]] = {
    "bridge_route.command.websocket.applied": (
        "sent",
        "transport_ok",
        "authority_accepted",
        "runtime_accepted",
        "applied",
    ),
    "bridge_route.device.adb.transport_only": ("sent", "transport_ok"),
    "bridge_route.marker.lsl.timestamped": ("sent", "observed"),
    "bridge_route.telemetry.udp.best_effort": ("sent",),
    "bridge_route.media.h264.data_plane": ("sent", "transport_ok", "observed"),
}


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON file did not contain an object: {path}")
    return value


def normalize_bridge_route_evidence(source: dict[str, Any]) -> dict[str, Any]:
    """Convert a Hostess input receipt into Manifold bridge-route evidence."""

    schema = source.get("$schema")
    if schema not in {
        HOSTESS_BRIDGE_ROUTE_INPUT_SCHEMA,
        MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
    }:
        raise ValueError(f"unsupported bridge route evidence input schema: {schema!r}")

    stage_rows = source.get("stage_reports")
    if stage_rows is None:
        stage_rows = source.get("stage_observations")
    if stage_rows is None:
        stage_rows = source.get("stages", [])
    if not isinstance(stage_rows, list):
        raise ValueError("bridge route stage observations must be a list")

    stage_reports = [normalize_stage_report(row) for row in stage_rows]
    started_at_ms = optional_int(source.get("started_at_ms"))
    ended_at_ms = optional_int(source.get("ended_at_ms"))
    observed_values = [
        report["observed_at_ms"]
        for report in stage_reports
        if report.get("observed_at_ms") is not None
    ]
    if started_at_ms is None:
        started_at_ms = min(observed_values) if observed_values else 0
    if ended_at_ms is None:
        ended_at_ms = max(observed_values) if observed_values else started_at_ms

    return {
        "$schema": MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
        "evidence_id": str(source.get("evidence_id") or ""),
        "route_id": str(source.get("route_id") or ""),
        "status": normalize_status(str(source.get("status") or "pass")),
        "started_at_ms": started_at_ms,
        "ended_at_ms": ended_at_ms,
        "stage_reports": stage_reports,
        "artifact_refs": string_list(source.get("artifact_refs", []), "artifact_refs"),
        "issues": [normalize_issue(issue) for issue in source.get("issues", [])],
    }


def normalize_stage_report(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("bridge route stage observation must be an object")
    stage = str(row.get("stage") or "")
    if stage not in VALID_STAGES:
        raise ValueError(f"unsupported bridge route evidence stage: {stage!r}")
    evidence_refs = row.get("evidence_refs")
    if evidence_refs is None:
        evidence_refs = row.get("evidence", [])
    return {
        "stage": stage,
        "status": normalize_status(str(row.get("status") or "pass")),
        "observed_at_ms": optional_int(row.get("observed_at_ms")),
        "evidence_refs": string_list(evidence_refs, "evidence_refs"),
        "issue_codes": string_list(row.get("issue_codes", []), "issue_codes"),
    }


def normalize_issue(issue: Any) -> dict[str, Any]:
    if isinstance(issue, str):
        return {
            "issue_code": issue,
            "severity": "error",
            "message": issue,
        }
    if not isinstance(issue, dict):
        raise ValueError("bridge route issue must be a string or object")
    issue_code = str(issue.get("issue_code") or issue.get("code") or "")
    severity = str(issue.get("severity") or "error")
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"unsupported bridge route issue severity: {severity!r}")
    return {
        "issue_code": issue_code,
        "severity": severity,
        "message": str(issue.get("message") or issue_code),
    }


def validate_bridge_route_evidence(
    evidence: dict[str, Any],
    *,
    required_stages: list[str] | tuple[str, ...] | None = None,
    route_descriptor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    route_id = str(evidence.get("route_id") or "")
    descriptor_required_stages: list[str] | None = None
    descriptor_checks = []
    if route_descriptor is not None:
        descriptor_required_stages = string_list(
            route_descriptor.get("required_evidence_stages", []),
            "required_evidence_stages",
        )
        descriptor_checks = [
            bridge_scorecard_check(
                "hostess.check.bridge_route.descriptor_schema",
                route_descriptor.get("$schema") == MANIFOLD_BRIDGE_ROUTE_DESCRIPTOR_SCHEMA,
                "bridge route descriptor schema is supported",
                "hostess.issue.bridge_route.descriptor_schema",
            ),
            bridge_scorecard_check(
                "hostess.check.bridge_route.descriptor_route",
                str(route_descriptor.get("route_id") or "") == route_id,
                "bridge route descriptor matches the emitted evidence route",
                "hostess.issue.bridge_route.descriptor_route_mismatch",
            ),
        ]

    expected_stages = resolve_required_stages(
        route_id,
        explicit=required_stages,
        descriptor=descriptor_required_stages,
    )
    stage_reports = [
        row
        for row in evidence.get("stage_reports", [])
        if isinstance(row, dict)
    ]
    failed_stage_count = sum(1 for row in stage_reports if row.get("status") == "fail")
    issue_count = len([issue for issue in evidence.get("issues", []) if isinstance(issue, dict)])
    status = evidence.get("status")
    status_consistent = (
        (status == "pass" and failed_stage_count == 0 and issue_count == 0)
        or (status == "warn" and failed_stage_count == 0)
        or (status == "fail" and (failed_stage_count > 0 or issue_count > 0))
    )
    missing_required = [
        stage
        for stage in expected_stages
        if not stage_passed(stage_reports, stage)
    ]

    checks = [
        bridge_scorecard_check(
            "hostess.check.bridge_route.schema",
            evidence.get("$schema") == MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
            "bridge route evidence schema is supported",
            "hostess.issue.bridge_route.unsupported_schema",
        ),
        bridge_scorecard_check(
            "hostess.check.bridge_route.identity",
            bool(route_id) and bool(evidence.get("evidence_id")),
            "bridge route evidence has stable route and evidence ids",
            "hostess.issue.bridge_route.missing_identity",
        ),
        bridge_scorecard_check(
            "hostess.check.bridge_route.status",
            status in VALID_STATUSES and status_consistent,
            "bridge route status matches stage failures and issues",
            "hostess.issue.bridge_route.status_mismatch",
        ),
        bridge_scorecard_check(
            "hostess.check.bridge_route.time_bounds",
            isinstance(evidence.get("started_at_ms"), int)
            and isinstance(evidence.get("ended_at_ms"), int)
            and evidence.get("started_at_ms") > 0
            and evidence.get("ended_at_ms") >= evidence.get("started_at_ms"),
            "bridge route evidence has monotonic millisecond bounds",
            "hostess.issue.bridge_route.time_bounds",
        ),
        bridge_scorecard_check(
            "hostess.check.bridge_route.stage_shape",
            bool(stage_reports)
            and all(
                row.get("stage") in VALID_STAGES and row.get("status") in VALID_STATUSES
                for row in stage_reports
            ),
            "bridge route stage reports use supported stage and status names",
            "hostess.issue.bridge_route.stage_shape",
        ),
        bridge_scorecard_check(
            "hostess.check.bridge_route.required_stage_policy",
            bool(expected_stages),
            "bridge route validation used descriptor, explicit, or known required stages",
            "hostess.issue.bridge_route.required_stage_policy_missing",
        ),
        bridge_scorecard_check(
            "hostess.check.bridge_route.required_stages",
            bool(expected_stages) and not missing_required,
            "bridge route evidence satisfies all required stages",
            "hostess.issue.bridge_route.missing_required_evidence",
        ),
    ]
    checks.extend(descriptor_checks)
    errors = [check["evidence"] for check in checks if check["status"] != "pass"]
    if missing_required:
        errors.append(f"missing required bridge route stages: {', '.join(missing_required)}")
    return {
        "$schema": HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "route_id": route_id,
        "evidence_id": evidence.get("evidence_id"),
        "evidence_status": status,
        "required_evidence_stages": list(expected_stages),
        "passed_evidence_stages": [
            str(row.get("stage"))
            for row in stage_reports
            if row.get("status") != "fail"
        ],
        "missing_required_evidence_stages": missing_required,
        "checks": checks,
        "errors": errors,
    }


def resolve_required_stages(
    route_id: str,
    *,
    explicit: list[str] | tuple[str, ...] | None = None,
    descriptor: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    if explicit:
        return tuple(validate_stage_name(stage) for stage in explicit)
    if descriptor:
        return tuple(validate_stage_name(stage) for stage in descriptor)
    return DEFAULT_REQUIRED_STAGES.get(route_id, ())


def run_emit_bridge_route_evidence(args: argparse.Namespace) -> int:
    source = load_json_object(Path(args.input))
    evidence = normalize_bridge_route_evidence(source)
    descriptor = load_json_object(Path(args.route_descriptor)) if args.route_descriptor else None
    source_required_stages = string_list(
        source.get("required_evidence_stages", []),
        "required_evidence_stages",
    )
    validation = validate_bridge_route_evidence(
        evidence,
        required_stages=list(args.required_stage or []) or source_required_stages or None,
        route_descriptor=descriptor,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    validation_out = (
        Path(args.validation_out)
        if args.validation_out
        else out.with_name(f"{out.stem}.validation-report.json")
    )
    validation_out.parent.mkdir(parents=True, exist_ok=True)
    validation_out.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if validation["status"] == "pass" else 2


def stage_passed(stage_reports: list[dict[str, Any]], stage: str) -> bool:
    return any(
        row.get("stage") == stage and row.get("status") != "fail"
        for row in stage_reports
    )


def validate_stage_name(stage: str) -> str:
    value = str(stage)
    if value not in VALID_STAGES:
        raise ValueError(f"unsupported bridge route evidence stage: {value!r}")
    return value


def normalize_status(status: str) -> str:
    value = status.strip().lower()
    if value not in VALID_STATUSES:
        raise ValueError(f"unsupported bridge route status: {status!r}")
    return value


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean value cannot be used as an integer")
    return int(value)


def string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a string list")
    return [str(item) for item in value]


def bridge_scorecard_check(
    check_id: str,
    passed: bool,
    evidence: str,
    issue_code: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
        "issue_codes": [] if passed else [issue_code],
    }


__all__ = [
    "DEFAULT_REQUIRED_STAGES",
    "HOSTESS_BRIDGE_ROUTE_INPUT_SCHEMA",
    "HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA",
    "MANIFOLD_BRIDGE_ROUTE_DESCRIPTOR_SCHEMA",
    "MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA",
    "normalize_bridge_route_evidence",
    "run_emit_bridge_route_evidence",
    "validate_bridge_route_evidence",
]
