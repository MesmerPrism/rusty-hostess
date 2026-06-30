"""Frontend-neutral companion report projection helpers for hostessctl."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_firewall import CONNECTIVITY_FIREWALL_RULE_SCHEMA
from tools.hostessctl.connectivity_suite import CONNECTIVITY_SUITE_RUN_SCHEMA
from tools.hostessctl.connectivity_probe import CONNECTIVITY_PROBE_SCHEMA
from tools.hostessctl.device_link_report import QUEST_DEVICE_LINK_SCHEMA
from tools.hostessctl.protocol_evidence_matrix import PROTOCOL_EVIDENCE_MATRIX_SCHEMA
from tools.hostessctl.companion_report_transport_coverage import (
    project_transport_coverage_rows,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA = (
    "rusty.hostess.companion.report_projection.v1"
)
HOSTESS_COMPANION_REPORT_PROJECTION_VALIDATION_SCHEMA = (
    "rusty.hostess.companion.report_projection.validation.v1"
)


def run_companion_report_projection(
    args: argparse.Namespace,
    *,
    clock_func: Callable[[], datetime] | None = None,
) -> int:
    """Write a companion report projection and validation sidecar."""

    report = build_companion_report_projection(
        args,
        clock_func=clock_func or utc_now,
    )
    validation = validate_companion_report_projection(report)

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


def build_companion_report_projection(
    args: argparse.Namespace,
    *,
    clock_func: Callable[[], datetime],
) -> dict[str, Any]:
    generated_at = clock_func()
    frontend = str(getattr(args, "frontend", None) or "cli")
    projection_id = str(getattr(args, "projection_id", None) or "").strip()
    if not projection_id:
        projection_id = f"companion-report-{generated_at.strftime('%Y%m%d-%H%M%S')}"

    issues: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for role, path in selected_source_paths(args):
        source_id = f"source.{role}.{len(sources) + 1}"
        source, payload = load_source_artifact(source_id, role, path, issues)
        sources.append(source)
        if not payload:
            continue
        projected_role = source["role"]
        if projected_role == "device_link_report":
            rows.extend(project_device_link_rows(payload, source))
        elif projected_role == "connectivity_probe_report":
            rows.extend(project_connectivity_probe_rows(payload, source))
        elif projected_role == "firewall_rule_report":
            rows.extend(project_firewall_rule_rows(payload, source))
        elif projected_role == "protocol_evidence_matrix":
            rows.extend(project_protocol_matrix_rows(payload, source))
        elif projected_role == "connectivity_suite_run":
            rows.extend(project_connectivity_suite_rows(payload, source))

    rows.extend(project_transport_coverage_rows(rows, sources))
    summary = projection_summary(rows, sources, issues)
    return {
        "$schema": HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA,
        "schema_version": 1,
        "projection_id": projection_id,
        "frontend": frontend,
        "generated_at_utc": generated_at.isoformat().replace("+00:00", "Z"),
        "status": projection_status(sources, issues),
        "authority": {
            "ui_role": "requester_and_inspector",
            "projection_only": True,
            "acceptance_owner": "source_artifacts",
            "command_authority": "rusty.manifold.command",
            "device_link_authority": "rusty.quest.device_link",
            "protocol_promotion_authority": "rusty.quest.device_link.protocol_evidence_matrix",
            "policy": (
                "This report only projects Hostess, Quest, and Manifold evidence "
                "into frontend rows. It does not run probes, select latest "
                "artifacts, change firewall/device state, or promote protocols."
            ),
        },
        "summary": summary,
        "source_artifacts": sources,
        "rows": rows,
        "issues": issues,
    }


def selected_source_paths(args: argparse.Namespace) -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    seen: set[tuple[str, str]] = set()

    def append_source(role: str, path: Path) -> None:
        key = (role, source_path_key(path))
        if key not in seen:
            seen.add(key)
            paths.append((role, path))

    for raw in argument_values(getattr(args, "device_link", None)):
        append_source("device_link_report", Path(raw))
    for raw in argument_values(getattr(args, "connectivity_probe", None)):
        append_source("connectivity_probe_report", Path(raw))
    for raw in argument_values(getattr(args, "firewall_rule", None)):
        append_source("firewall_rule_report", Path(raw))
    protocol_matrix_paths = [
        Path(raw)
        for raw in argument_values(getattr(args, "protocol_matrix", None))
    ]
    if getattr(args, "include_protocol_matrix_inputs", False):
        for matrix_path in protocol_matrix_paths:
            for role, path in protocol_matrix_input_source_paths(matrix_path):
                append_source(role, path)
    for path in protocol_matrix_paths:
        append_source("protocol_evidence_matrix", path)
    for raw in argument_values(getattr(args, "suite_run", None)):
        append_source("connectivity_suite_run", Path(raw))
    return paths


def protocol_matrix_input_source_paths(matrix_path: Path) -> list[tuple[str, Path]]:
    matrix = read_json(matrix_path)
    if not matrix:
        return []

    paths: list[tuple[str, Path]] = []
    for matrix_input in list_objects(matrix.get("inputs")):
        role = str(matrix_input.get("role") or "")
        raw_path = str(matrix_input.get("path") or "").strip()
        if not raw_path:
            continue
        if role == "device_link_report":
            paths.append(("device_link_report", resolve_matrix_source_path(matrix_path, raw_path)))
        elif role == "connectivity_probe_report":
            paths.append(("connectivity_probe_report", resolve_matrix_source_path(matrix_path, raw_path)))

    for matrix_row in list_objects(matrix.get("rows")):
        source = object_value(matrix_row.get("source"))
        if str(source.get("schema") or "") != CONNECTIVITY_PROBE_SCHEMA:
            continue
        raw_path = str(source.get("artifact_path") or "").strip()
        if raw_path:
            paths.append(("connectivity_probe_report", resolve_matrix_source_path(matrix_path, raw_path)))
    return paths


def resolve_matrix_source_path(matrix_path: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if path.exists():
        return path
    repo_path = REPO_ROOT / path
    if repo_path.exists():
        return repo_path
    matrix_relative_path = matrix_path.parent / path
    if matrix_relative_path.exists():
        return matrix_relative_path
    return path


def source_path_key(path: Path) -> str:
    return str(path.resolve()).casefold()


def load_source_artifact(
    source_id: str,
    requested_role: str,
    path: Path,
    issues: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = read_json(path)
    schema = str(payload.get("$schema") or payload.get("schema") or "")
    actual_role = classify_source_payload(payload)
    source = {
        "source_id": source_id,
        "requested_role": requested_role,
        "role": actual_role if actual_role != "unknown" else requested_role,
        "path": str(path),
        "schema": schema,
        "status": payload.get("status") if payload else "unreadable",
        "sha256": sha256_file(path),
        "summary": source_summary(actual_role, payload),
    }
    if not payload:
        issues.append(
            issue(
                "hostess.issue.companion_report_projection.source_unreadable",
                "error",
                f"could not read source artifact {path}",
                source_id=source_id,
            )
        )
        return source, {}
    if actual_role == "unknown":
        issues.append(
            issue(
                "hostess.issue.companion_report_projection.source_schema_unsupported",
                "error",
                f"unsupported source artifact schema {schema or '<missing>'}",
                source_id=source_id,
            )
        )
        return source, {}
    if actual_role != requested_role:
        issues.append(
            issue(
                "hostess.issue.companion_report_projection.source_role_mismatch",
                "warning",
                (
                    f"source role {actual_role} does not match requested "
                    f"role {requested_role}"
                ),
                source_id=source_id,
            )
        )
    return source, payload


def project_device_link_rows(
    report: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    device_identity = object_value(report.get("device_identity"))
    rows.append(
        row(
            "device_link.identity",
            "device",
            "device_identity",
            "Quest identity",
            "pass" if device_identity.get("adb_state") == "device" else report_status(report),
            source,
            authority_owner="rusty.quest.device_link",
            evidence=(
                f"{device_identity.get('model', '')} / "
                f"{device_identity.get('transport_kind', '')} / "
                f"{device_identity.get('adb_state', '')}"
            ).strip(" /"),
            details=device_identity,
        )
    )
    for tool in list_objects(report.get("host_tools")):
        rows.append(
            row(
                f"device_link.tool.{safe_token(tool.get('tool_id') or tool.get('kind'))}",
                "host_tool",
                "host_tool",
                f"Host tool: {tool.get('kind') or 'unknown'}",
                str(tool.get("status") or "unknown"),
                source,
                authority_owner="rusty.hostess.companion_readiness",
                evidence=str(tool.get("path") or tool.get("kind") or ""),
                required=bool(tool.get("required")),
                details=tool,
            )
        )
    for tunnel in list_objects(report.get("tunnels")):
        rows.append(
            row(
                f"device_link.tunnel.{safe_token(tunnel.get('tunnel_id') or tunnel.get('transport_kind'))}",
                "transport",
                "tunnel",
                f"Tunnel: {tunnel.get('transport_kind') or 'unknown'}",
                str(tunnel.get("status") or "unknown"),
                source,
                authority_owner="rusty.quest.device_link",
                evidence=(
                    f"{tunnel.get('host', '')}:{tunnel.get('local_port', '')} -> "
                    f"{tunnel.get('device_host', '')}:{tunnel.get('device_port', '')}"
                    f"{tunnel.get('path', '')}"
                ),
                required=bool(tunnel.get("required")),
                details=tunnel,
            )
        )
    for endpoint in list_objects(report.get("broker_endpoints")):
        rows.append(
            row(
                f"device_link.broker.{safe_token(endpoint.get('endpoint_id') or endpoint.get('protocol'))}",
                "transport",
                "broker_endpoint",
                f"Broker endpoint: {endpoint.get('protocol') or 'unknown'}",
                str(endpoint.get("status") or "unknown"),
                source,
                authority_owner=str(endpoint.get("authority") or "rusty.manifold.command"),
                evidence=(
                    f"{endpoint.get('protocol', '')}://"
                    f"{endpoint.get('host', '')}:{endpoint.get('port', '')}"
                    f"{endpoint.get('path', '')}"
                ),
                details=endpoint,
            )
        )
    for subscriber in list_objects(report.get("runtime_subscribers")):
        status = "pass" if subscriber.get("status") == "connected" else str(
            subscriber.get("status") or "unknown"
        )
        rows.append(
            row(
                f"device_link.runtime_subscriber.{safe_token(subscriber.get('subscriber_id') or subscriber.get('runtime_app_id'))}",
                "runtime",
                "runtime_subscriber",
                "Runtime subscriber",
                status,
                source,
                authority_owner="rusty.quest.device_link",
                evidence=(
                    f"{subscriber.get('runtime_app_id', '')}: "
                    f"{subscriber.get('request_stream_id', '')} -> "
                    f"{subscriber.get('receipt_stream_id', '')}, "
                    f"delivered={subscriber.get('last_dispatch_delivered_count', '')}"
                ),
                metrics={
                    "last_dispatch_delivered_count": subscriber.get(
                        "last_dispatch_delivered_count"
                    )
                },
                details=subscriber,
            )
        )
    for result in list_objects(report.get("command_results")):
        rows.append(
            row(
                f"device_link.command_result.{safe_token(result.get('result_id') or result.get('request_id'))}",
                "command",
                "command_result",
                f"Command result: {result.get('command') or 'unknown'}",
                str(result.get("status") or "unknown"),
                source,
                authority_owner="rusty.manifold.command",
                evidence=(
                    f"{result.get('route_id', '')} / "
                    f"{result.get('transport_kind', '')} / "
                    f"applied={result.get('applied')} / "
                    f"delivered={result.get('runtime_dispatch_delivered_count', '')}"
                ),
                metrics={
                    "applied": result.get("applied"),
                    "runtime_dispatch_delivered_count": result.get(
                        "runtime_dispatch_delivered_count"
                    ),
                },
                details=result,
            )
        )
    for capability in list_objects(report.get("stream_capabilities")):
        rows.append(
            row(
                f"device_link.stream_capability.{safe_token(capability.get('capability_id') or capability.get('stream_id'))}",
                "transport",
                "stream_capability",
                str(capability.get("stream_id") or capability.get("capability_id") or "stream"),
                str(capability.get("status") or "pass"),
                source,
                authority_owner=stream_authority_owner(capability),
                evidence=(
                    f"{capability.get('transport_kind', '')} / "
                    f"{capability.get('semantic_family', '')} / "
                    f"{capability.get('rate_class', '')}"
                ).strip(" /"),
                metrics={"max_rate_hz": capability.get("max_rate_hz")},
                details=capability,
            )
        )
    for report_issue in list_objects(report.get("issues")):
        code = str(report_issue.get("issue_code") or "device_link.issue")
        rows.append(
            row(
                f"device_link.issue.{safe_token(code)}",
                "issue",
                "source_issue",
                code,
                status_from_severity(str(report_issue.get("severity") or "")),
                source,
                authority_owner="rusty.quest.device_link",
                evidence=str(report_issue.get("message") or ""),
                issue_codes=[code],
                details=report_issue,
            )
        )
    return rows


def project_protocol_matrix_rows(
    matrix: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        row(
            "protocol_matrix.summary",
            "protocol",
            "protocol_matrix_summary",
            "Protocol evidence matrix",
            report_status(matrix),
            source,
            authority_owner="rusty.quest.device_link.protocol_evidence_matrix",
            evidence=(
                f"{matrix.get('matrix_id') or ''}: "
                f"{len(list_objects(matrix.get('rows')))} protocol capability rows"
            ),
            details=object_value(matrix.get("summary")),
        )
    ]
    for protocol in list_objects(matrix.get("rows")):
        missing_gates = string_list(protocol.get("missing_gates"))
        rows.append(
            row(
                f"protocol_matrix.row.{safe_token(protocol.get('probe_id'))}.{safe_token(protocol.get('capability_id'))}",
                "protocol",
                "protocol_capability",
                f"{protocol.get('probe_id') or 'QCL'} {protocol.get('transport_kind') or 'protocol'}",
                str(protocol.get("status") or "unknown"),
                source,
                authority_owner=str(protocol.get("authority_owner") or "rusty.quest.device_link"),
                evidence_tier=str(protocol.get("evidence_tier") or ""),
                evidence=(
                    f"{protocol.get('capability_id', '')}: "
                    f"tier={protocol.get('evidence_tier', '')}, "
                    f"promotion={protocol.get('promotion_state', '')}, "
                    f"allowed={protocol.get('promotion_allowed')}"
                ),
                notes=(
                    str(protocol.get("promotion_gate") or "")
                    if not missing_gates
                    else f"{protocol.get('promotion_gate') or ''} Missing: {', '.join(missing_gates)}"
                ),
                issue_count=len(missing_gates),
                issue_codes=protocol_issue_codes(protocol),
                metrics=object_value(protocol.get("measurements")),
                details=protocol,
            )
        )
        for gate in list_objects(protocol.get("gate_results")):
            gate_id = str(gate.get("gate_id") or "gate")
            rows.append(
                row(
                    f"protocol_matrix.gate.{safe_token(gate_id)}",
                    "protocol_gate",
                    "protocol_gate",
                    gate_id,
                    status_for_protocol_gate(str(gate.get("status") or "")),
                    source,
                    authority_owner=str(protocol.get("authority_owner") or "rusty.quest.device_link"),
                    evidence_tier=str(protocol.get("evidence_tier") or ""),
                    evidence=str(gate.get("evidence") or ""),
                    notes=str(protocol.get("capability_id") or ""),
                    issue_codes=[] if gate.get("status") == "satisfied" else [gate_id],
                    details=gate,
                )
            )
    for matrix_issue in list_objects(matrix.get("issues")):
        code = str(matrix_issue.get("issue_code") or "protocol_matrix.issue")
        rows.append(
            row(
                f"protocol_matrix.issue.{safe_token(code)}",
                "issue",
                "source_issue",
                code,
                status_from_severity(str(matrix_issue.get("severity") or "")),
                source,
                authority_owner="rusty.quest.device_link.protocol_evidence_matrix",
                evidence=str(matrix_issue.get("message") or ""),
                issue_codes=[code],
                details=matrix_issue,
            )
        )
    return rows


def project_connectivity_probe_rows(
    report: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    probe_id = str(report.get("probe_id") or "QCL")
    rows: list[dict[str, Any]] = [
        row(
            f"connectivity_probe.summary.{safe_token(probe_id)}",
            "connectivity",
            "connectivity_probe_summary",
            f"{probe_id} connectivity probe",
            report_status(report),
            source,
            authority_owner="rusty.hostess.connectivity_probe",
            evidence=(
                f"{report.get('classification') or 'unknown'} / "
                f"{report.get('run_id') or ''}"
            ).strip(" /"),
            metrics=object_value(report.get("measurements")),
            details={
                "probe_id": probe_id,
                "run_id": report.get("run_id"),
                "observed_at_utc": report.get("observed_at_utc"),
                "classification": report.get("classification"),
            },
        )
    ]

    topology = object_value(report.get("topology"))
    if topology:
        rows.append(
            row(
                f"connectivity_probe.topology.{safe_token(probe_id)}",
                "connectivity_topology",
                "topology",
                f"{probe_id} topology",
                "candidate" if topology.get("experimental") else "pass",
                source,
                authority_owner="rusty.hostess.connectivity_probe",
                evidence=(
                    f"{topology.get('owner') or 'unknown'} / "
                    f"{topology.get('network_provider') or 'unknown'} / "
                    f"{topology.get('endpoint_direction') or 'unknown'}"
                ),
                notes=topology_notes(topology),
                issue_codes=(
                    ["hostess.issue.connectivity_probe.experimental_topology"]
                    if topology.get("experimental")
                    else []
                ),
                details=topology,
            )
        )

    transport = object_value(report.get("transport"))
    if transport:
        rows.append(
            row(
                f"connectivity_probe.transport.{safe_token(probe_id)}",
                "transport",
                "connectivity_transport",
                f"{probe_id} transport",
                "candidate" if transport.get("product_data_plane") is False else "pass",
                source,
                authority_owner="rusty.hostess.connectivity_probe",
                evidence=(
                    f"{transport.get('family') or 'unknown'} / "
                    f"{transport.get('protocol_role') or 'unknown'} / "
                    f"{transport.get('payload_class') or 'unknown'}"
                ),
                notes=str(transport.get("route") or ""),
                details=transport,
            )
        )

    for check in list_objects(report.get("checks")):
        check_name = str(check.get("name") or "check")
        rows.append(
            row(
                f"connectivity_probe.check.{safe_token(probe_id)}.{safe_token(check_name)}",
                "connectivity_check",
                "connectivity_probe_check",
                check_name,
                str(check.get("status") or "unknown"),
                source,
                authority_owner="rusty.hostess.connectivity_probe",
                evidence=str(check.get("evidence") or ""),
                notes=str(check.get("notes") or ""),
                issue_codes=string_list(check.get("issue_codes")),
                details=check,
            )
        )

    promotion = object_value(report.get("promotion"))
    if promotion:
        allowed = promotion.get("allowed") is True
        rows.append(
            row(
                f"connectivity_probe.promotion.{safe_token(probe_id)}",
                "promotion",
                "connectivity_promotion_gate",
                f"{probe_id} promotion gate",
                "pass" if allowed else "candidate",
                source,
                authority_owner="rusty.quest.device_link.protocol_evidence_matrix",
                evidence=(
                    f"allowed={allowed}; target={promotion.get('target') or ''}"
                ),
                notes=str(promotion.get("reason") or ""),
                issue_codes=[] if allowed else [f"gate.{probe_id.lower()}.promotion_allowed"],
                details=promotion,
            )
        )

    for probe_issue in list_objects(report.get("issues")):
        code = str(probe_issue.get("issue_code") or "connectivity_probe.issue")
        rows.append(
            row(
                f"connectivity_probe.issue.{safe_token(probe_id)}.{safe_token(code)}",
                "issue",
                "source_issue",
                code,
                status_from_severity(str(probe_issue.get("severity") or "")),
                source,
                authority_owner="rusty.hostess.connectivity_probe",
                evidence=str(probe_issue.get("message") or ""),
                issue_codes=[code],
                details=probe_issue,
            )
        )
    return rows


def project_connectivity_suite_rows(
    report: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        row(
            "connectivity_suite.summary",
            "suite",
            "suite_summary",
            "Connectivity suite",
            report_status(report),
            source,
            authority_owner="rusty.hostess.connectivity_probe",
            evidence=(
                f"{report.get('suite_id') or ''} / {report.get('mode') or ''}: "
                f"{len(list_objects(report.get('slot_results')))} slots"
            ),
            notes=str(report.get("suite_descriptor_path") or ""),
            details=object_value(report.get("summary")),
        ),
        row(
            "connectivity_suite.environment_snapshot",
            "suite",
            "environment_snapshot",
            "Suite environment snapshot",
            "pass",
            source,
            authority_owner="rusty.hostess.connectivity_probe",
            evidence=(
                "host tools, network adapters, firewall profiles, hotspot, "
                "Bluetooth, and device snapshot captured"
            ),
            details=object_value(report.get("environment_snapshot")),
        ),
    ]
    for group in list_objects(report.get("grouped_results")):
        rows.append(
            row(
                f"connectivity_suite.group.{safe_token(group.get('group_id') or group.get('phase'))}",
                "suite_group",
                "suite_group",
                str(group.get("group_id") or group.get("phase") or "group"),
                str(group.get("status") or "unknown"),
                source,
                authority_owner="rusty.hostess.connectivity_probe",
                evidence=(
                    f"{group.get('phase', '')}: {group.get('pass_count', 0)} pass, "
                    f"{group.get('warn_count', 0)} warn, {group.get('fail_count', 0)} fail "
                    f"across {group.get('slot_count', 0)} slots"
                ),
                details=group,
            )
        )
    for slot in list_objects(report.get("slot_results")):
        slot_issues = [
            str(item.get("issue_code") or "")
            for item in list_objects(slot.get("issues"))
            if str(item.get("issue_code") or "")
        ]
        rows.append(
            row(
                f"connectivity_suite.slot.{safe_token(slot.get('slot_id') or slot.get('probe_id'))}",
                "suite_slot",
                "suite_slot",
                str(slot.get("slot_id") or slot.get("probe_id") or "slot"),
                str(slot.get("status") or "unknown"),
                source,
                authority_owner="rusty.hostess.connectivity_probe",
                evidence=(
                    f"{slot.get('probe_id', '')} {slot.get('phase', '')}: "
                    f"report={slot.get('report_status')}, "
                    f"validation={slot.get('validation_status')}"
                ),
                notes=slot_notes(slot),
                issue_count=len(slot_issues),
                issue_codes=slot_issues,
                metrics=object_value(slot.get("metrics")),
                details=slot,
            )
        )
    return rows


def project_firewall_rule_rows(
    report: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    rule = object_value(report.get("rule"))
    verification = object_value(report.get("verification"))
    listener = object_value(verification.get("listener_firewall"))
    rule_profile = str(report.get("rule_profile") or "")
    probe_usage = object_value(report.get("probe_usage"))
    probe_id = str(probe_usage.get("probe_id") or "host")
    product_gate_proven = firewall_product_listener_gate_proven(report)
    details = {
        "probe_id": probe_id,
        "action": report.get("action"),
        "rule_profile": rule_profile,
        "family": str(rule.get("protocol") or listener.get("protocol") or "").lower(),
        "protocol": str(rule.get("protocol") or listener.get("protocol") or ""),
        "route": "windows_firewall_rule",
        "program": rule.get("program") or listener.get("program"),
        "name": rule.get("name"),
        "local_port": rule.get("local_port") or listener.get("port"),
        "remote_address": rule.get("remote_address"),
        "product_rule_verified": verification.get("product_rule_verified") is True,
        "allowed_on_active_profile": verification.get("allowed_on_active_profile") is True,
        "product_gate": "product_tcp_media_listener_firewall_verified",
        "product_gate_proven": product_gate_proven,
    }
    rows = [
        row(
            f"firewall_rule.{safe_token(rule_profile or probe_id)}.{safe_token(report.get('action'))}",
            "firewall",
            "firewall_rule",
            f"Firewall rule: {rule_profile or probe_id}",
            "pass" if product_gate_proven else report_status(report),
            source,
            authority_owner="tools.hostessctl.connectivity_firewall",
            evidence=(
                f"{rule.get('name') or ''}: "
                f"{rule.get('program') or ''}, "
                f"{rule.get('protocol') or listener.get('protocol') or ''} "
                f"{rule.get('local_port') or listener.get('port') or ''}"
            ).strip(" ,"),
            notes=str(rule.get("scope_note") or ""),
            issue_codes=string_list(verification.get("issue_codes")),
            details=details,
        )
    ]
    for report_issue in list_objects(report.get("issues")):
        code = str(report_issue.get("issue_code") or "firewall_rule.issue")
        rows.append(
            row(
                f"firewall_rule.issue.{safe_token(rule_profile or probe_id)}.{safe_token(code)}",
                "issue",
                "source_issue",
                code,
                status_from_severity(str(report_issue.get("severity") or "")),
                source,
                authority_owner="tools.hostessctl.connectivity_firewall",
                evidence=str(report_issue.get("message") or ""),
                issue_codes=[code],
                details=report_issue,
            )
        )
    return rows


def row(
    row_id: str,
    section: str,
    kind: str,
    label: str,
    status: str,
    source: dict[str, Any],
    *,
    authority_owner: str,
    evidence_tier: str = "",
    evidence: str = "",
    notes: str = "",
    required: bool = False,
    issue_count: int = 0,
    issue_codes: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    codes = issue_codes or []
    return {
        "row_id": row_id,
        "section": section,
        "kind": kind,
        "label": label,
        "status": status or "unknown",
        "authority_owner": authority_owner,
        "evidence_tier": evidence_tier,
        "source_artifact": source.get("source_id"),
        "source_path": source.get("path"),
        "source_schema": source.get("schema"),
        "required": required,
        "evidence": evidence,
        "notes": notes,
        "issue_count": max(issue_count, len(codes)),
        "issue_codes": codes,
        "metrics": metrics or {},
        "details": details or {},
    }


def validate_companion_report_projection(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if report.get("$schema") != HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA:
        errors.append("unsupported companion report projection schema")
    authority = object_value(report.get("authority"))
    if authority.get("projection_only") is not True:
        errors.append("projection authority must set projection_only=true")
    sources = list_objects(report.get("source_artifacts"))
    rows = list_objects(report.get("rows"))
    if not sources:
        errors.append("source_artifacts must not be empty")
    if not rows:
        errors.append("rows must not be empty")
    source_ids = {str(source.get("source_id") or "") for source in sources}
    for source in sources:
        source_id = str(source.get("source_id") or "")
        if not source_id:
            errors.append("source artifact missing source_id")
        if not str(source.get("path") or "").strip():
            errors.append(f"source {source_id or '<unknown>'} missing path")
        if not str(source.get("schema") or "").strip():
            warnings.append(f"source {source_id or '<unknown>'} missing schema")
    for projection_row in rows:
        row_id = str(projection_row.get("row_id") or "")
        if not row_id:
            errors.append("projection row missing row_id")
        if not str(projection_row.get("section") or "").strip():
            errors.append(f"row {row_id or '<unknown>'} missing section")
        if not str(projection_row.get("status") or "").strip():
            errors.append(f"row {row_id or '<unknown>'} missing status")
        source_id = str(projection_row.get("source_artifact") or "")
        if source_id not in source_ids:
            errors.append(f"row {row_id or '<unknown>'} references unknown source {source_id}")
    for projection_issue in list_objects(report.get("issues")):
        if projection_issue.get("severity") == "error":
            errors.append(str(projection_issue.get("message") or "projection issue"))
    return {
        "$schema": HOSTESS_COMPANION_REPORT_PROJECTION_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "projection_id": report.get("projection_id"),
        "report_status": report.get("status"),
        "source_count": len(sources),
        "row_count": len(rows),
        "errors": errors,
        "warnings": warnings,
    }


def projection_summary(
    rows: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    section_counts: dict[str, int] = {}
    row_status_counts: dict[str, int] = {}
    source_status_counts: dict[str, int] = {}
    for projection_row in rows:
        section = str(projection_row.get("section") or "unknown")
        status = str(projection_row.get("status") or "unknown")
        section_counts[section] = section_counts.get(section, 0) + 1
        row_status_counts[status] = row_status_counts.get(status, 0) + 1
    for source in sources:
        status = str(source.get("status") or "unknown")
        source_status_counts[status] = source_status_counts.get(status, 0) + 1
    return {
        "source_count": len(sources),
        "row_count": len(rows),
        "issue_count": len(issues),
        "section_counts": dict(sorted(section_counts.items())),
        "row_status_counts": dict(sorted(row_status_counts.items())),
        "source_status_counts": dict(sorted(source_status_counts.items())),
    }


def projection_status(
    sources: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> str:
    if any(issue_row.get("severity") == "error" for issue_row in issues):
        return "fail"
    statuses = {str(source.get("status") or "") for source in sources}
    if "unreadable" in statuses:
        return "fail"
    if statuses - {"pass", "usable", "usable_with_warnings"}:
        return "warn"
    return "pass" if sources else "warn"


def classify_source_payload(payload: dict[str, Any]) -> str:
    schema = str(payload.get("$schema") or payload.get("schema") or "")
    if schema == QUEST_DEVICE_LINK_SCHEMA:
        return "device_link_report"
    if schema == CONNECTIVITY_PROBE_SCHEMA:
        return "connectivity_probe_report"
    if schema == CONNECTIVITY_FIREWALL_RULE_SCHEMA:
        return "firewall_rule_report"
    if schema == PROTOCOL_EVIDENCE_MATRIX_SCHEMA:
        return "protocol_evidence_matrix"
    if schema == CONNECTIVITY_SUITE_RUN_SCHEMA:
        return "connectivity_suite_run"
    return "unknown"


def source_summary(role: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    if role == "device_link_report":
        return {
            "link_id": payload.get("link_id"),
            "status": payload.get("status"),
            "command_result_count": len(list_objects(payload.get("command_results"))),
            "runtime_subscriber_count": len(list_objects(payload.get("runtime_subscribers"))),
            "stream_capability_count": len(list_objects(payload.get("stream_capabilities"))),
        }
    if role == "protocol_evidence_matrix":
        summary = object_value(payload.get("summary"))
        return {
            "matrix_id": payload.get("matrix_id"),
            "status": payload.get("status"),
            "row_count": summary.get("row_count")
            or len(list_objects(payload.get("rows"))),
            "all_required_data_protocols_promoted": summary.get(
                "all_required_data_protocols_promoted"
            ),
        }
    if role == "connectivity_probe_report":
        topology = object_value(payload.get("topology"))
        transport = object_value(payload.get("transport"))
        promotion = object_value(payload.get("promotion"))
        return {
            "probe_id": payload.get("probe_id"),
            "status": payload.get("status"),
            "classification": payload.get("classification"),
            "topology_owner": topology.get("owner"),
            "network_provider": topology.get("network_provider"),
            "transport_family": transport.get("family"),
            "promotion_allowed": promotion.get("allowed"),
            "check_count": len(list_objects(payload.get("checks"))),
            "issue_count": len(list_objects(payload.get("issues"))),
        }
    if role == "firewall_rule_report":
        rule = object_value(payload.get("rule"))
        verification = object_value(payload.get("verification"))
        probe_usage = object_value(payload.get("probe_usage"))
        return {
            "probe_id": probe_usage.get("probe_id"),
            "status": payload.get("status"),
            "action": payload.get("action"),
            "rule_profile": payload.get("rule_profile"),
            "rule_name": rule.get("name"),
            "protocol": rule.get("protocol"),
            "local_port": rule.get("local_port"),
            "product_rule_verified": verification.get("product_rule_verified"),
        }
    if role == "connectivity_suite_run":
        summary = object_value(payload.get("summary"))
        return {
            "suite_run_id": payload.get("suite_run_id"),
            "suite_id": payload.get("suite_id"),
            "status": payload.get("status"),
            "slot_count": summary.get("slot_count")
            or len(list_objects(payload.get("slot_results"))),
        }
    return {"status": payload.get("status")}


def protocol_issue_codes(protocol: dict[str, Any]) -> list[str]:
    missing_gates = string_list(protocol.get("missing_gates"))
    if not missing_gates:
        return []
    codes = list(missing_gates)
    if protocol.get("required_for_fold_in") is True:
        codes.append("hostess.issue.protocol_evidence_matrix.required_protocol_not_promoted")
    return codes


def slot_notes(slot: dict[str, Any]) -> str:
    descriptor_path = str(slot.get("descriptor_path") or "")
    if descriptor_path:
        return (
            f"{slot.get('report_path') or ''}; descriptor={descriptor_path} "
            f"({slot.get('descriptor_status') or ''})"
        )
    return str(slot.get("report_path") or "")


def topology_notes(topology: dict[str, Any]) -> str:
    flags = []
    if topology.get("requires_existing_wifi") is True:
        flags.append("requires existing Wi-Fi")
    if topology.get("requires_adb") is True:
        flags.append("requires ADB")
    if topology.get("requires_pairing") is True:
        flags.append("requires pairing")
    if topology.get("requires_termux") is True:
        flags.append("requires Termux")
    if topology.get("experimental") is True:
        flags.append("experimental")
    return ", ".join(flags)


def report_status(report: dict[str, Any]) -> str:
    return str(report.get("status") or "unknown")


def stream_authority_owner(capability: dict[str, Any]) -> str:
    if capability.get("semantic_family") == "command":
        return "rusty.manifold.command"
    return "rusty.quest.device_link"


def status_from_severity(severity: str) -> str:
    return "fail" if severity == "error" else "warn"


def status_for_protocol_gate(status: str) -> str:
    if status == "satisfied":
        return "pass"
    if status == "blocked":
        return "blocked"
    if status == "missing":
        return "warn"
    return status or "unknown"


def firewall_product_listener_gate_proven(report: dict[str, Any]) -> bool:
    rule = object_value(report.get("rule"))
    verification = object_value(report.get("verification"))
    listener = object_value(verification.get("listener_firewall"))
    protocol = str(rule.get("protocol") or listener.get("protocol") or "").upper()
    local_port = int_value(rule.get("local_port") or listener.get("port"))
    program = str(rule.get("program") or listener.get("program") or "")
    return (
        str(report.get("status") or "") == "pass"
        and str(report.get("action") or "") == "verify"
        and str(report.get("rule_profile") or "") == "qcl-082-rmanvid1-media"
        and verification.get("product_rule_verified") is True
        and verification.get("allowed_on_active_profile") is True
        and protocol == "TCP"
        and local_port == 9079
        and "HostessCompanion.Wpf" in program
    )


def int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def issue(
    issue_code: str,
    severity: str,
    message: str,
    *,
    source_id: str = "",
) -> dict[str, Any]:
    return {
        "issue_code": issue_code,
        "severity": severity,
        "message": message,
        "source_artifact": source_id,
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


def safe_token(value: Any) -> str:
    text = str(value or "unknown")
    chars = [
        char if char.isalnum() or char in {".", "_", "-"} else "-"
        for char in text
    ]
    token = "".join(chars).strip("._-")
    while "--" in token:
        token = token.replace("--", "-")
    return token or "unknown"


def list_objects(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def argument_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA",
    "HOSTESS_COMPANION_REPORT_PROJECTION_VALIDATION_SCHEMA",
    "build_companion_report_projection",
    "run_companion_report_projection",
    "validate_companion_report_projection",
]
