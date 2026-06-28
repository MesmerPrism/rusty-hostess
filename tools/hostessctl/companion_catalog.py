"""Companion descriptor catalog helpers for hostessctl."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


HOSTESS_COMPANION_CATALOG_SCHEMA = "rusty.hostess.companion.catalog.v1"
HOSTESS_COMPANION_CATALOG_VALIDATION_SCHEMA = (
    "rusty.hostess.companion.catalog_validation.v1"
)
GUI_COMPANION_MODULE_DESCRIPTOR_SCHEMA = "rusty.gui.companion.module_descriptor.v1"
GUI_COMPANION_WORKSPACE_DESCRIPTOR_SCHEMA = "rusty.gui.companion.workspace_descriptor.v1"
GUI_COMPANION_TRANSPORT_CAPABILITY_SCHEMA = "rusty.gui.companion.transport_capability.v1"
SUPPORTED_DESCRIPTOR_SCHEMAS = {
    GUI_COMPANION_MODULE_DESCRIPTOR_SCHEMA,
    GUI_COMPANION_WORKSPACE_DESCRIPTOR_SCHEMA,
    GUI_COMPANION_TRANSPORT_CAPABILITY_SCHEMA,
}


def run_companion_catalog(
    args: argparse.Namespace,
    *,
    clock_ms_func: Callable[[], int] | None = None,
) -> int:
    """Write a companion descriptor catalog and validation sidecar."""

    report = build_companion_catalog_report(
        args,
        clock_ms_func=clock_ms_func or epoch_ms,
    )
    validation = validate_companion_catalog_report(report)
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


def build_companion_catalog_report(
    args: argparse.Namespace,
    *,
    clock_ms_func: Callable[[], int],
) -> dict[str, Any]:
    repo = repo_root()
    generated_at_ms = int(clock_ms_func())
    frontend = str(getattr(args, "frontend", None) or "wpf")
    hostess_descriptor = Path(
        getattr(args, "hostess_descriptor", None)
        or repo / "fixtures" / "companion-readiness" / "readiness-module-descriptor.json"
    )
    gui_descriptors_root = Path(
        getattr(args, "gui_descriptors_root", None) or default_gui_descriptors_root(repo)
    )

    issues: list[dict[str, Any]] = []
    descriptors = load_catalog_descriptors(
        hostess_descriptor=hostess_descriptor,
        gui_descriptors_root=gui_descriptors_root,
        frontend=frontend,
        issues=issues,
    )
    modules = sorted(descriptors["modules"].values(), key=lambda row: row["module_id"])
    workspaces = sorted(descriptors["workspaces"].values(), key=lambda row: row["workspace_id"])
    transports = sorted(descriptors["transports"].values(), key=lambda row: row["transport_id"])
    summary = {
        "modules": len(modules),
        "workspaces": len(workspaces),
        "transports": len(transports),
        "issues": len(issues),
        "warnings": sum(1 for issue in issues if issue.get("severity") == "warning"),
        "errors": sum(1 for issue in issues if issue.get("severity") == "error"),
    }
    status = "fail" if summary["errors"] else ("warn" if summary["warnings"] else "pass")
    return {
        "$schema": HOSTESS_COMPANION_CATALOG_SCHEMA,
        "status": status,
        "generated_at_ms": generated_at_ms,
        "scope": {
            "frontend": frontend,
            "hostess_descriptor": str(hostess_descriptor),
            "gui_descriptors_root": str(gui_descriptors_root),
        },
        "summary": summary,
        "modules": modules,
        "workspaces": workspaces,
        "transports": transports,
        "issues": issues,
    }


def validate_companion_catalog_report(report: dict[str, Any]) -> dict[str, Any]:
    modules = [row for row in report.get("modules", []) if isinstance(row, dict)]
    workspaces = [row for row in report.get("workspaces", []) if isinstance(row, dict)]
    transports = [row for row in report.get("transports", []) if isinstance(row, dict)]
    errors: list[str] = []
    if report.get("$schema") != HOSTESS_COMPANION_CATALOG_SCHEMA:
        errors.append("unsupported companion catalog schema")
    if not modules:
        errors.append("catalog must contain at least one module descriptor")
    if not transports:
        errors.append("catalog must contain at least one transport capability descriptor")

    module_ids = set()
    for row in modules:
        module_id = str(row.get("module_id") or "")
        if not module_id:
            errors.append("module descriptor missing module_id")
        module_ids.add(module_id)
        if row.get("schema") != GUI_COMPANION_MODULE_DESCRIPTOR_SCHEMA:
            errors.append(f"module {module_id or '<unknown>'} has unsupported schema")
        if row.get("authority_role") == "authority":
            errors.append(f"module {module_id or '<unknown>'} may not claim authority")
        if row.get("owner_lane") == "gui" and row.get("command_requests"):
            errors.append(f"module {module_id or '<unknown>'} uses GUI as command authority")

    for row in workspaces:
        workspace_id = str(row.get("workspace_id") or "")
        if row.get("schema") != GUI_COMPANION_WORKSPACE_DESCRIPTOR_SCHEMA:
            errors.append(f"workspace {workspace_id or '<unknown>'} has unsupported schema")
        for selection in row.get("modules", []):
            if isinstance(selection, dict):
                module_id = str(selection.get("module_id") or "")
                if module_id not in module_ids:
                    errors.append(
                        f"workspace {workspace_id or '<unknown>'} references unknown module {module_id}"
                    )

    for row in transports:
        transport_id = str(row.get("transport_id") or "")
        if not transport_id:
            errors.append("transport descriptor missing transport_id")
        if row.get("schema") != GUI_COMPANION_TRANSPORT_CAPABILITY_SCHEMA:
            errors.append(f"transport {transport_id or '<unknown>'} has unsupported schema")
        if row.get("authority_role") == "authority":
            errors.append(f"transport {transport_id or '<unknown>'} may not claim authority")
        for route_id in row.get("route_ids", []):
            if str(route_id).startswith("rusty.gui."):
                errors.append(f"transport {transport_id or '<unknown>'} uses GUI as route authority")
        if row.get("family") == "media_data_plane" and row.get("payload_rate") == "low_rate_json":
            errors.append(
                f"transport {transport_id or '<unknown>'} collapses media data-plane payloads into JSON"
            )

    issue_errors = [
        str(issue.get("message") or "catalog issue")
        for issue in report.get("issues", [])
        if isinstance(issue, dict) and issue.get("severity") == "error"
    ]
    errors.extend(issue_errors)
    return {
        "$schema": HOSTESS_COMPANION_CATALOG_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "catalog_status": report.get("status"),
        "module_count": len(modules),
        "workspace_count": len(workspaces),
        "transport_count": len(transports),
        "errors": errors,
    }


def load_catalog_descriptors(
    *,
    hostess_descriptor: Path,
    gui_descriptors_root: Path,
    frontend: str,
    issues: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    buckets: dict[str, dict[str, dict[str, Any]]] = {
        "modules": {},
        "workspaces": {},
        "transports": {},
    }
    descriptor_paths = []
    if hostess_descriptor.exists():
        descriptor_paths.append(hostess_descriptor)
    else:
        issues.append(
            catalog_issue(
                "warning",
                "hostess.issue.companion_catalog.missing_hostess_descriptor",
                f"Hostess descriptor not found: {hostess_descriptor}",
            )
        )
    if gui_descriptors_root.exists():
        descriptor_paths.extend(sorted(gui_descriptors_root.glob("*.json")))
    else:
        issues.append(
            catalog_issue(
                "warning",
                "hostess.issue.companion_catalog.missing_gui_descriptor_root",
                f"GUI descriptor root not found: {gui_descriptors_root}",
            )
        )

    for path in descriptor_paths:
        try:
            descriptor = load_json_object(path)
        except Exception as exc:
            issues.append(
                catalog_issue(
                    "error",
                    "hostess.issue.companion_catalog.unreadable_descriptor",
                    f"Descriptor unreadable: {path}: {exc}",
                )
            )
            continue
        schema = descriptor.get("schema") or descriptor.get("$schema")
        if schema not in SUPPORTED_DESCRIPTOR_SCHEMAS:
            continue
        if not supports_frontend(descriptor, frontend):
            continue
        row = dict(descriptor)
        row["source_path"] = str(path)
        row["source_paths"] = [str(path)]
        if schema == GUI_COMPANION_MODULE_DESCRIPTOR_SCHEMA:
            merge_descriptor_row(buckets["modules"], "module_id", row, issues)
        elif schema == GUI_COMPANION_WORKSPACE_DESCRIPTOR_SCHEMA:
            merge_descriptor_row(buckets["workspaces"], "workspace_id", row, issues)
        elif schema == GUI_COMPANION_TRANSPORT_CAPABILITY_SCHEMA:
            merge_descriptor_row(buckets["transports"], "transport_id", row, issues)
    return buckets


def merge_descriptor_row(
    bucket: dict[str, dict[str, Any]],
    id_key: str,
    row: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    descriptor_id = str(row.get(id_key) or "")
    if not descriptor_id:
        issues.append(
            catalog_issue(
                "error",
                "hostess.issue.companion_catalog.missing_descriptor_id",
                f"Descriptor missing {id_key}: {row.get('source_path')}",
            )
        )
        return
    existing = bucket.get(descriptor_id)
    if existing is None:
        bucket[descriptor_id] = row
        return
    existing_paths = list(existing.get("source_paths", []))
    existing_paths.extend(row.get("source_paths", []))
    existing["source_paths"] = existing_paths
    comparable_existing = dict(existing)
    comparable_row = dict(row)
    for item in (comparable_existing, comparable_row):
        item.pop("source_path", None)
        item.pop("source_paths", None)
    if comparable_existing != comparable_row:
        issues.append(
            catalog_issue(
                "error",
                "hostess.issue.companion_catalog.conflicting_duplicate",
                f"Descriptor {descriptor_id} has conflicting duplicate definitions",
            )
        )


def supports_frontend(descriptor: dict[str, Any], frontend: str) -> bool:
    frontends = descriptor.get("supported_frontends")
    return not isinstance(frontends, list) or frontend in frontends


def catalog_issue(severity: str, code: str, message: str) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
    }


def default_gui_descriptors_root(repo: Path) -> Path:
    return repo.parent / "rusty-gui" / "fixtures" / "descriptors"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON file did not contain an object: {path}")
    return value


def epoch_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


__all__ = [
    "GUI_COMPANION_MODULE_DESCRIPTOR_SCHEMA",
    "GUI_COMPANION_TRANSPORT_CAPABILITY_SCHEMA",
    "GUI_COMPANION_WORKSPACE_DESCRIPTOR_SCHEMA",
    "HOSTESS_COMPANION_CATALOG_SCHEMA",
    "HOSTESS_COMPANION_CATALOG_VALIDATION_SCHEMA",
    "build_companion_catalog_report",
    "run_companion_catalog",
    "validate_companion_catalog_report",
]
