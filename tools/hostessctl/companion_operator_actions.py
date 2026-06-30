"""CLI-equivalent operator action catalog for companion frontends."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.companion_operator_action_rows import (
    HOSTESS_CTL_SCRIPT,
    operator_actions_for_frontend,
)


HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA = (
    "rusty.hostess.companion.operator_action_catalog.v1"
)
HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_VALIDATION_SCHEMA = (
    "rusty.hostess.companion.operator_action_catalog.validation.v1"
)


def run_companion_operator_actions(
    args: argparse.Namespace,
    *,
    clock_func: Callable[[], datetime] | None = None,
) -> int:
    """Write the frontend operator action catalog and validation sidecar."""

    report = build_companion_operator_action_catalog(
        args,
        clock_func=clock_func or utc_now,
    )
    validation = validate_companion_operator_action_catalog(report)

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


def build_companion_operator_action_catalog(
    args: argparse.Namespace,
    *,
    clock_func: Callable[[], datetime],
) -> dict[str, Any]:
    generated_at = clock_func()
    frontend = str(getattr(args, "frontend", None) or "wpf")
    report_id = str(getattr(args, "report_id", None) or "").strip()
    if not report_id:
        report_id = f"{frontend}-operator-actions-{generated_at.strftime('%Y%m%d-%H%M%S')}"
    actions = operator_actions_for_frontend(frontend)
    issues = operator_catalog_issues(actions, frontend=frontend)
    segments = [
        segment
        for action in actions
        for segment in hostess_cli_segments(str(action.get("cli_route") or ""))
    ]
    return {
        "$schema": HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA,
        "schema_version": 1,
        "report_id": report_id,
        "frontend": frontend,
        "generated_at_utc": generated_at.isoformat().replace("+00:00", "Z"),
        "status": "fail" if any_error(issues) else "pass",
        "authority": {
            "ui_role": "requester_and_inspector",
            "catalog_only": True,
            "acceptance_owner": "advertised_cli_routes",
            "command_authority": "hostessctl_routes_and_source_reports",
            "policy": (
                "This catalog makes WPF-visible operator actions inspectable "
                "from the CLI. It does not execute commands, choose latest "
                "artifacts, change firewall/device state, run probes, reserve "
                "leases, or promote protocols."
            ),
        },
        "summary": {
            "action_count": len(actions),
            "hostess_cli_segment_count": len(segments),
            "requires_elevation_count": sum(
                1 for action in actions if action.get("requires_elevation") is True
            ),
            "requires_quest_lease_count": sum(
                1 for action in actions if action.get("requires_quest_lease") is True
            ),
            "mutates_host_count": sum(
                1 for action in actions if action.get("mutates_host") is True
            ),
            "mutates_device_count": sum(
                1 for action in actions if action.get("mutates_device") is True
            ),
            "all_hostess_cli_segments_name_out": not any(
                issue.get("issue_code")
                == "hostess.issue.operator_action_catalog.cli_segment_missing_out"
                for issue in issues
            ),
            "issue_count": len(issues),
        },
        "actions": actions,
        "issues": issues,
    }


def validate_companion_operator_action_catalog(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if report.get("$schema") != HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA:
        errors.append("unsupported companion operator action catalog schema")
    authority = object_value(report.get("authority"))
    if authority.get("catalog_only") is not True:
        errors.append("operator action catalog must set catalog_only=true")
    actions = list_objects(report.get("actions"))
    if not actions:
        errors.append("actions must not be empty")
    seen: set[str] = set()
    for action_row in actions:
        action_id = str(action_row.get("action_id") or "")
        if not action_id:
            errors.append("action missing action_id")
        elif action_id in seen:
            errors.append(f"duplicate action_id: {action_id}")
        else:
            seen.add(action_id)
        for field in [
            "title",
            "ui_command_property",
            "cli_route",
            "evidence_artifact",
            "authority_owner",
            "test_coverage",
        ]:
            if not str(action_row.get(field) or "").strip():
                errors.append(f"action {action_id or '<unknown>'} missing {field}")
        for bool_field in [
            "requires_elevation",
            "requires_quest_lease",
            "requires_adb_server_lifecycle_lease",
            "mutates_host",
            "mutates_device",
        ]:
            if not isinstance(action_row.get(bool_field), bool):
                errors.append(
                    f"action {action_id or '<unknown>'} missing boolean {bool_field}"
                )
    for catalog_issue in list_objects(report.get("issues")):
        message = str(catalog_issue.get("message") or catalog_issue.get("issue_code") or "")
        if catalog_issue.get("severity") == "error":
            errors.append(message)
        else:
            warnings.append(message)
    return {
        "$schema": HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "report_id": report.get("report_id"),
        "frontend": report.get("frontend"),
        "action_count": len(actions),
        "errors": errors,
        "warnings": warnings,
    }


def operator_catalog_issues(
    actions: list[dict[str, Any]],
    *,
    frontend: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if frontend != "wpf":
        issues.append(
            issue(
                "hostess.issue.operator_action_catalog.unsupported_frontend",
                "error",
                f"unsupported operator action frontend {frontend}",
            )
        )
    for action_row in actions:
        action_id = str(action_row.get("action_id") or "")
        route = str(action_row.get("cli_route") or "")
        if not action_id.startswith(f"{frontend}."):
            issues.append(
                issue(
                    "hostess.issue.operator_action_catalog.action_id_scope",
                    "error",
                    f"action {action_id or '<unknown>'} is not scoped to {frontend}",
                    action_id=action_id,
                )
            )
        if not advertises_hostessctl(route):
            issues.append(
                issue(
                    "hostess.issue.operator_action_catalog.hostessctl_missing",
                    "error",
                    f"action {action_id or '<unknown>'} does not advertise hostessctl",
                    action_id=action_id,
                )
            )
        if re.search(r"[A-Za-z0-9_)-]\|[A-Za-z0-9_(]", route):
            issues.append(
                issue(
                    "hostess.issue.operator_action_catalog.pipe_shorthand",
                    "error",
                    f"action {action_id or '<unknown>'} uses pipe-delimited option shorthand",
                    action_id=action_id,
                )
            )
        for segment in hostess_cli_segments(route):
            if not re.search(r"(^|\s)--out(\s|$)", segment):
                issues.append(
                    issue(
                        "hostess.issue.operator_action_catalog.cli_segment_missing_out",
                        "error",
                        f"action {action_id or '<unknown>'} route segment missing --out: {segment}",
                        action_id=action_id,
                    )
                )
        if action_row.get("requires_quest_lease") is True and "quest" not in route.lower():
            issues.append(
                issue(
                    "hostess.issue.operator_action_catalog.quest_lease_unexplained",
                    "error",
                    f"action {action_id or '<unknown>'} requires a Quest lease but the route has no Quest context",
                    action_id=action_id,
                )
            )
        if action_row.get("requires_elevation") is True and "windows-firewall-rule" not in route:
            issues.append(
                issue(
                    "hostess.issue.operator_action_catalog.elevation_unexplained",
                    "error",
                    f"action {action_id or '<unknown>'} requires elevation outside a Hostess firewall route",
                    action_id=action_id,
                )
            )
        if action_row.get("requires_adb_server_lifecycle_lease") is True:
            issues.append(
                issue(
                    "hostess.issue.operator_action_catalog.adb_lifecycle_over_serial_scoped_action",
                    "error",
                    f"action {action_id or '<unknown>'} should not require adb-server:lifecycle for serial-scoped WPF routes",
                    action_id=action_id,
                )
            )
    return issues


def hostess_cli_segments(cli_route: str) -> list[str]:
    return [
        segment
        for segment in [
            part.strip()
            for part in cli_route.split(";")
            if part.strip()
        ]
        if (
            f"python {HOSTESS_CTL_SCRIPT}" in segment
            or "python $HostessCtl" in segment
        )
    ]


def advertises_hostessctl(cli_route: str) -> bool:
    return (
        f"python {HOSTESS_CTL_SCRIPT}" in cli_route
        or (
            f"$HostessCtl = '{HOSTESS_CTL_SCRIPT}'" in cli_route
            and "python $HostessCtl" in cli_route
        )
    )


def issue(
    issue_code: str,
    severity: str,
    message: str,
    *,
    action_id: str = "",
) -> dict[str, Any]:
    row = {
        "issue_code": issue_code,
        "severity": severity,
        "message": message,
    }
    if action_id:
        row["action_id"] = action_id
    return row


def any_error(issues: list[dict[str, Any]]) -> bool:
    return any(issue_row.get("severity") == "error" for issue_row in issues)


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_objects(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA",
    "HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_VALIDATION_SCHEMA",
    "build_companion_operator_action_catalog",
    "run_companion_operator_actions",
    "validate_companion_operator_action_catalog",
]
