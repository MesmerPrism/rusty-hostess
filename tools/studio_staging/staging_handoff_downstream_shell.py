"""Hostess downstream shell selection receipt helpers."""

from __future__ import annotations

from typing import Any
from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.staging_handoff_payload_manifest import *

def build_hostess_downstream_shell_selection_receipt(
    staged_payload_manifest_receipt: dict[str, Any],
    target_kind: str | None = None,
    graph_id: str | None = None,
    consumer_id: str | None = None,
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    source_ready = hostess_staged_payload_manifest_receipt_source_ready(
        staged_payload_manifest_receipt
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    candidate_rows = hostess_downstream_shell_selection_candidate_rows(
        staged_payload_manifest_receipt
    )
    matching_rows = hostess_downstream_shell_selection_candidate_rows(
        staged_payload_manifest_receipt,
        target_kind=target_kind,
        graph_id=graph_id,
        consumer_id=consumer_id,
    )
    selected_source_row = (
        matching_rows[0]
        if decision == ACCEPTED_STATUS
        and decision_supported
        and source_ready
        and matching_rows
        else None
    )
    status = SELECTED_STATUS if selected_source_row is not None else REJECTED_STATUS
    issue_code = None
    if status != SELECTED_STATUS:
        issue_code = (
            reason_code
            or staged_payload_manifest_receipt.get("issue_code")
            or (
                "hostess.issue.hostess_downstream_shell_selection_receipt_decision"
                if not decision_supported
                else "hostess.issue.hostess_staged_payload_manifest_source_not_ready"
                if not source_ready
                else "hostess.issue.hostess_downstream_shell_selection_no_candidate"
            )
        )
    selection_rows = (
        [
            hostess_downstream_shell_selection_row(
                staged_payload_manifest_receipt,
                selected_source_row,
            )
        ]
        if selected_source_row is not None
        else []
    )
    selected_row = selection_rows[0] if selection_rows else None
    checks = hostess_downstream_shell_selection_receipt_checks(
        staged_payload_manifest_receipt,
        selection_rows,
        status,
        decision_supported,
        target_kind=target_kind,
        graph_id=graph_id,
        consumer_id=consumer_id,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == SELECTED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        selection_rows = []
        selected_row = None
    receipt_id = (
        "hostess.downstream_shell_selection_receipt."
        f"{staged_payload_manifest_receipt.get('receipt_id')}"
        if isinstance(staged_payload_manifest_receipt.get("receipt_id"), str)
        and staged_payload_manifest_receipt.get("receipt_id")
        else "hostess.downstream_shell_selection_receipt.unknown"
    )
    selected = status == SELECTED_STATUS
    selected_artifact_kind = (
        selected_row.get("selected_artifact_kind") if selected_row else None
    )
    manifold_handoff_selected = (
        selected_artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    )
    makepad_descriptor_selected = (
        selected_artifact_kind == SHELL_DESCRIPTOR_ARTIFACT_KIND
    )
    pmb_review_required = (
        staged_payload_manifest_receipt.get("pmb_shell_handoff_review_required")
        is True
    )
    pmb_review_ready = (
        staged_payload_manifest_receipt.get("pmb_shell_handoff_review_ready") is True
    )
    return {
        "$schema": HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_staged_payload_manifest_receipt_id": (
            staged_payload_manifest_receipt.get("receipt_id")
        ),
        "source_staged_payload_manifest_receipt_schema": (
            staged_payload_manifest_receipt.get("$schema")
        ),
        "source_staged_payload_manifest_receipt_status": (
            staged_payload_manifest_receipt.get("status")
        ),
        "source_payload_manifest_reviewed": (
            staged_payload_manifest_receipt.get("payload_manifest_reviewed") is True
        ),
        "source_staged_payloads_available": (
            staged_payload_manifest_receipt.get("staged_payloads_available") is True
        ),
        "manifest_id": staged_payload_manifest_receipt.get("manifest_id"),
        "project_id": staged_payload_manifest_receipt.get("project_id"),
        "project_revision": staged_payload_manifest_receipt.get(
            "project_revision"
        ),
        "selected_candidate_id": staged_payload_manifest_receipt.get(
            "selected_candidate_id"
        ),
        "checksum_algorithm": staged_payload_manifest_receipt.get(
            "checksum_algorithm"
        ),
        "plan_checksum": staged_payload_manifest_receipt.get("plan_checksum"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "selection_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "payload_manifest_owner": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "downstream_shell_consumer_role": "downstream.shell.consume_staged_descriptor",
        "requested_target_kind": target_kind,
        "requested_graph_id": graph_id,
        "requested_consumer_id": consumer_id,
        "staging_root": staged_payload_manifest_receipt.get("staging_root"),
        "downstream_shell_selection_ready": selected,
        "downstream_shell_descriptor_selected": selected,
        "makepad_shell_selection_ready": selected,
        "manifold_shell_handoff_selected": manifold_handoff_selected,
        "makepad_shell_descriptor_selected": makepad_descriptor_selected,
        "selected_payload_row_id": (
            selected_row.get("source_payload_row_id") if selected_row else None
        ),
        "selected_payload_path": (
            selected_row.get("selected_payload_path") if selected_row else None
        ),
        "selected_artifact_kind": (
            selected_row.get("selected_artifact_kind") if selected_row else None
        ),
        "selected_target_kind": (
            selected_row.get("target_kind") if selected_row else None
        ),
        "selected_graph_id": selected_row.get("graph_id") if selected_row else None,
        "selected_consumer_id": (
            selected_row.get("consumer_id") if selected_row else None
        ),
        "legacy_reference_dependency_used": False,
        "downstream_shell_runtime_started": False,
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "schema_artifact_payloads_copied": False,
        "release_payloads_copied": False,
        "staging_payloads_copied": False,
        "file_copy_performed": False,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(
            staged_payload_manifest_receipt
        ),
        "candidate_count": len(candidate_rows),
        "matching_candidate_count": len(matching_rows),
        "selected_candidate_count": 1 if selected else 0,
        "selection_rows": selection_rows,
        "checks": checks,
        "next_required_action": (
            "manifold_review_selected_shell_handoff_without_launch"
            if manifold_handoff_selected
            else "makepad_consume_selected_staged_descriptor_without_launch"
            if makepad_descriptor_selected
            else "repair_or_decline_downstream_shell_selection"
        ),
    }

def validate_hostess_downstream_shell_selection_receipt(
    staged_payload_manifest_receipt: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    selection_rows = hostess_downstream_shell_selection_row_dicts(receipt)
    selected_rows = [
        row
        for row in selection_rows
        if row.get("selection_status") == SELECTED_STATUS
    ]
    matching_rows = hostess_downstream_shell_selection_candidate_rows(
        staged_payload_manifest_receipt,
        target_kind=receipt.get("requested_target_kind"),
        graph_id=receipt.get("requested_graph_id"),
        consumer_id=receipt.get("requested_consumer_id"),
    )
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [
        entry for entry in embedded_checks if isinstance(entry, dict)
    ]
    embedded_failed = [
        entry for entry in embedded_check_dicts if entry.get("status") == FAIL_STATUS
    ]
    status = receipt.get("status")
    pmb_review_required = (
        staged_payload_manifest_receipt.get("pmb_shell_handoff_review_required")
        is True
    )
    pmb_summary_matches_manifest = (
        pmb_shell_handoff_review_summary_from_source(receipt)
        == pmb_shell_handoff_review_summary_from_source(
            staged_payload_manifest_receipt
        )
    )
    selected_row = selected_rows[0] if len(selected_rows) == 1 else None
    selected_artifact_kind = receipt.get("selected_artifact_kind")
    manifold_handoff_selected = (
        selected_artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    )
    makepad_descriptor_selected = (
        selected_artifact_kind == SHELL_DESCRIPTOR_ARTIFACT_KIND
    )
    checks = [
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.schema",
            receipt.get("$schema")
            == HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA,
            "Hostess downstream shell selection receipt schema is supported",
            "Hostess downstream shell selection receipt schema is unsupported",
            "hostess.issue.hostess_downstream_shell_selection_receipt_schema",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.status",
            status in {SELECTED_STATUS, REJECTED_STATUS}
            and (
                (status == SELECTED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess downstream shell selection receipt status is consistent",
            "Hostess downstream shell selection receipt status is inconsistent",
            "hostess.issue.hostess_downstream_shell_selection_receipt_status",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.execution_policy",
            receipt.get("execution_policy")
            == HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_POLICY,
            "Hostess downstream shell selection is schema-only",
            "Hostess downstream shell selection execution policy drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_execution_policy",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.sources",
            receipt.get("source_staged_payload_manifest_receipt_id")
            == staged_payload_manifest_receipt.get("receipt_id")
            and receipt.get("source_staged_payload_manifest_receipt_schema")
            == HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA
            and receipt.get("manifest_id")
            == staged_payload_manifest_receipt.get("manifest_id")
            and receipt.get("project_id")
            == staged_payload_manifest_receipt.get("project_id")
            and receipt.get("project_revision")
            == staged_payload_manifest_receipt.get("project_revision"),
            "Hostess downstream shell selection source manifest matches input",
            "Hostess downstream shell selection source manifest drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_source_mismatch",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.source_readiness",
            (
                status == SELECTED_STATUS
                and hostess_staged_payload_manifest_receipt_source_ready(
                    staged_payload_manifest_receipt
                )
            )
            or status == REJECTED_STATUS,
            "Hostess downstream shell selection source is ready or rejected consistently",
            "Hostess downstream shell selection source is not ready",
            "hostess.issue.hostess_staged_payload_manifest_source_not_ready",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != SELECTED_STATUS
            or (
                receipt.get("pmb_shell_handoff_review_required") is True
                and receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_manifest
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            ),
            "selected downstream shell descriptor preserves the PMB shell handoff gate",
            "selected downstream shell descriptor dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_downstream_shell_selection_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("selection_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("payload_manifest_owner") == HOSTESS_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess owns selection while Manifold remains command/session authority",
            "Hostess downstream shell selection authority fields drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_authority",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.no_runtime_started",
            hostess_downstream_shell_selection_receipt_no_runtime_started(receipt),
            "Hostess downstream shell selection did not copy, install, launch, execute, or start command sessions",
            "Hostess downstream shell selection indicates copy, install, launch, runtime execution, or command sessions",
            "hostess.issue.hostess_downstream_shell_selection_receipt_runtime_started",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.selection_rows",
            hostess_downstream_shell_selection_rows_match_manifest(
                staged_payload_manifest_receipt,
                selection_rows,
                status,
            ),
            "Hostess downstream shell selection rows match reviewed manifest descriptors",
            "Hostess downstream shell selection rows drifted from the reviewed manifest",
            "hostess.issue.hostess_downstream_shell_selection_receipt_selection_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.selected_descriptor",
            (
                status == SELECTED_STATUS
                and selected_row is not None
                and receipt.get("downstream_shell_selection_ready") is True
                and receipt.get("downstream_shell_descriptor_selected") is True
                and receipt.get("makepad_shell_selection_ready") is True
                and receipt.get("manifold_shell_handoff_selected")
                is manifold_handoff_selected
                and receipt.get("makepad_shell_descriptor_selected")
                is makepad_descriptor_selected
                and receipt.get("selected_payload_row_id")
                == selected_row.get("source_payload_row_id")
                and receipt.get("selected_payload_path")
                == selected_row.get("selected_payload_path")
                and is_downstream_shell_selection_artifact_kind(
                    selected_artifact_kind
                )
                and receipt.get("selected_target_kind")
                == selected_row.get("target_kind")
                and receipt.get("selected_graph_id") == selected_row.get("graph_id")
                and receipt.get("selected_consumer_id")
                == selected_row.get("consumer_id")
                and bool(matching_rows)
                and selected_row.get("source_payload_row_id")
                == matching_rows[0].get("payload_row_id")
                and receipt.get("legacy_reference_dependency_used") is False
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("downstream_shell_selection_ready") is False
                and receipt.get("downstream_shell_descriptor_selected") is False
                and receipt.get("makepad_shell_selection_ready") is False
                and receipt.get("manifold_shell_handoff_selected") is False
                and receipt.get("makepad_shell_descriptor_selected") is False
                and receipt.get("selected_payload_row_id") is None
                and receipt.get("selected_payload_path") is None
            ),
            "Hostess downstream shell descriptor selection is consistent",
            "Hostess downstream shell descriptor selection drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_descriptor_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.counts",
            receipt.get("candidate_count")
            == len(
                hostess_downstream_shell_selection_candidate_rows(
                    staged_payload_manifest_receipt
                )
            )
            and receipt.get("matching_candidate_count") == len(matching_rows)
            and receipt.get("selected_candidate_count")
            == (1 if status == SELECTED_STATUS else 0)
            and len(selected_rows) == (1 if status == SELECTED_STATUS else 0),
            "Hostess downstream shell selection counts match nested records",
            "Hostess downstream shell selection counts drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_count_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.embedded_checks",
            (
                status == SELECTED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess downstream shell selection embedded checks match receipt status",
            "Hostess downstream shell selection embedded checks do not match receipt status",
            "hostess.issue.hostess_downstream_shell_selection_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "copy_started": False,
        "staging_payloads_copied": False,
        "downstream_shell_selection_ready": receipt.get(
            "downstream_shell_selection_ready"
        )
        is True,
        "makepad_shell_selection_ready": receipt.get(
            "makepad_shell_selection_ready"
        )
        is True,
        "manifold_shell_handoff_selected": receipt.get(
            "manifold_shell_handoff_selected"
        )
        is True,
        "makepad_shell_descriptor_selected": receipt.get(
            "makepad_shell_descriptor_selected"
        )
        is True,
        "pmb_shell_handoff_review_required": receipt.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": receipt.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }

def hostess_downstream_shell_selection_receipt_checks(
    staged_payload_manifest_receipt: dict[str, Any],
    selection_rows: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
    target_kind: str | None = None,
    graph_id: str | None = None,
    consumer_id: str | None = None,
) -> list[dict[str, Any]]:
    matching_rows = hostess_downstream_shell_selection_candidate_rows(
        staged_payload_manifest_receipt,
        target_kind=target_kind,
        graph_id=graph_id,
        consumer_id=consumer_id,
    )
    pmb_review_required = (
        staged_payload_manifest_receipt.get("pmb_shell_handoff_review_required")
        is True
    )
    return [
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.manifest_source",
            hostess_staged_payload_manifest_receipt_source_ready(
                staged_payload_manifest_receipt
            ),
            "Hostess staged payload manifest is reviewed and ready for downstream selection",
            "Hostess staged payload manifest is missing, rejected, or drifted",
            staged_payload_manifest_receipt.get("issue_code")
            or "hostess.issue.hostess_staged_payload_manifest_source_not_ready",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != SELECTED_STATUS
            or (
                staged_payload_manifest_receipt.get(
                    "pmb_shell_handoff_review_ready"
                )
                is True
                and pmb_shell_handoff_readiness_result_summary_valid(
                    staged_payload_manifest_receipt
                )
            ),
            "selected downstream shell descriptor preserves the PMB shell handoff gate",
            "selected downstream shell descriptor dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_downstream_shell_selection_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.decision",
            decision_supported,
            "Hostess downstream shell selection receipt decision is supported",
            "Hostess downstream shell selection receipt decision is unsupported",
            "hostess.issue.hostess_downstream_shell_selection_receipt_decision",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.candidate",
            status != SELECTED_STATUS or bool(matching_rows),
            "Hostess downstream shell selection has a matching descriptor candidate",
            "Hostess downstream shell selection has no matching descriptor candidate",
            "hostess.issue.hostess_downstream_shell_selection_no_candidate",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.rows",
            hostess_downstream_shell_selection_rows_match_manifest(
                staged_payload_manifest_receipt,
                selection_rows,
                status,
            ),
            "Hostess downstream shell selection rows match reviewed manifest descriptors",
            "Hostess downstream shell selection rows drifted from reviewed manifest descriptors",
            "hostess.issue.hostess_downstream_shell_selection_receipt_selection_drift",
        ),
    ]

def hostess_downstream_shell_selection_row(
    staged_payload_manifest_receipt: dict[str, Any],
    source_row: dict[str, Any],
) -> dict[str, Any]:
    payload_row_id = source_row.get("payload_row_id")
    selected_artifact_kind = source_row.get("artifact_kind")
    manifold_handoff_selected = (
        selected_artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    )
    makepad_descriptor_selected = (
        selected_artifact_kind == SHELL_DESCRIPTOR_ARTIFACT_KIND
    )
    return {
        "selection_row_id": (
            f"hostess.downstream_shell_selection.{payload_row_id}"
            if isinstance(payload_row_id, str) and payload_row_id
            else "hostess.downstream_shell_selection.unknown"
        ),
        "source_staged_payload_manifest_receipt_id": (
            staged_payload_manifest_receipt.get("receipt_id")
        ),
        "source_payload_row_id": payload_row_id,
        "source_copy_row_id": source_row.get("source_copy_row_id"),
        "source_staging_file_row_id": source_row.get(
            "source_staging_file_row_id"
        ),
        "source_request_id": source_row.get("source_request_id"),
        "source_file_index": source_row.get("source_file_index"),
        "selected_artifact_kind": selected_artifact_kind,
        "selected_payload_path": source_row.get("payload_path"),
        "payload_kind": source_row.get("payload_kind"),
        "payload_exists": source_row.get("payload_exists") is True,
        "payload_under_staging_root": (
            source_row.get("payload_under_staging_root") is True
        ),
        "target_kind": source_row.get("target_kind"),
        "graph_id": source_row.get("graph_id"),
        "consumer_id": source_row.get("consumer_id"),
        "route_hints": source_row.get("route_hints"),
        "source_action_ids": source_row.get("source_action_ids"),
        "source_route_kinds": source_row.get("source_route_kinds"),
        "selection_status": SELECTED_STATUS,
        "issue_code": None,
        "downstream_shell_descriptor_ready": True,
        "manifold_shell_handoff_candidate": (
            source_row.get("manifold_shell_handoff_candidate") is True
        ),
        "manifold_shell_handoff_selected": manifold_handoff_selected,
        "makepad_shell_selection_candidate": True,
        "makepad_shell_descriptor_selected": makepad_descriptor_selected,
        "downstream_shell_artifact_priority": downstream_shell_artifact_priority(
            selected_artifact_kind
        ),
        "legacy_reference_dependency_used": False,
        "downstream_shell_runtime_started": False,
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_started": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
    }

def hostess_downstream_shell_selection_candidate_rows(
    staged_payload_manifest_receipt: dict[str, Any],
    target_kind: str | None = None,
    graph_id: str | None = None,
    consumer_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for row in hostess_staged_payload_manifest_row_dicts(
        staged_payload_manifest_receipt
    ):
        payload_path = row.get("payload_path")
        if not (
            row.get("payload_review_status") == REVIEWED_STATUS
            and is_downstream_shell_selection_artifact_kind(
                row.get("artifact_kind")
            )
            and row.get("downstream_shell_descriptor_ready") is True
            and row.get("makepad_shell_selection_candidate") is True
            and row.get("payload_exists") is True
            and row.get("payload_under_staging_root") is True
            and isinstance(row.get("target_kind"), str)
            and bool(row.get("target_kind"))
            and isinstance(row.get("graph_id"), str)
            and bool(row.get("graph_id"))
            and isinstance(row.get("consumer_id"), str)
            and bool(row.get("consumer_id"))
            and isinstance(payload_path, str)
            and Path(payload_path).exists()
            and not has_legacy_route_or_path(row)
            and hostess_staged_payload_row_no_runtime_started(row)
        ):
            continue
        if target_kind is not None and row.get("target_kind") != target_kind:
            continue
        if graph_id is not None and row.get("graph_id") != graph_id:
            continue
        if consumer_id is not None and row.get("consumer_id") != consumer_id:
            continue
        rows.append(row)
    rows.sort(
        key=lambda row: (
            downstream_shell_artifact_priority(row.get("artifact_kind")),
            str(row.get("target_kind") or ""),
            str(row.get("graph_id") or ""),
            str(row.get("consumer_id") or ""),
            str(row.get("payload_row_id") or ""),
        )
    )
    return rows

def hostess_downstream_shell_selection_row_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = receipt.get("selection_rows", [])
    if not isinstance(rows, list):
        return []
    return [entry for entry in rows if isinstance(entry, dict)]

def hostess_staged_payload_manifest_receipt_source_ready(
    receipt: dict[str, Any],
) -> bool:
    target_descriptor_rows = hostess_downstream_shell_selection_candidate_rows(
        receipt
    )
    return (
        receipt.get("$schema") == HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA
        and receipt.get("status") == REVIEWED_STATUS
        and receipt.get("issue_code") is None
        and receipt.get("receipt_owner") == HOSTESS_OWNER
        and receipt.get("staging_owner") == HOSTESS_OWNER
        and receipt.get("payload_manifest_owner") == HOSTESS_OWNER
        and receipt.get("command_session_authority") == MANIFOLD_OWNER
        and receipt.get("payload_manifest_reviewed") is True
        and receipt.get("staged_payloads_available") is True
        and receipt.get("downstream_shell_selection_ready") is True
        and receipt.get("makepad_shell_selection_ready") is True
        and receipt.get("target_descriptor_payload_count")
        == len(target_descriptor_rows)
        and len(target_descriptor_rows) > 0
        and hostess_staged_payload_manifest_receipt_no_runtime_started(receipt)
        and (
            receipt.get("pmb_shell_handoff_review_required") is not True
            or (
                receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            )
        )
    )

def hostess_downstream_shell_selection_rows_match_manifest(
    staged_payload_manifest_receipt: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {SELECTED_STATUS, REJECTED_STATUS}:
        return False
    if status == REJECTED_STATUS:
        return rows == []
    if len(rows) != 1:
        return False
    row = rows[0]
    by_id = {
        source_row.get("payload_row_id"): source_row
        for source_row in hostess_downstream_shell_selection_candidate_rows(
            staged_payload_manifest_receipt
        )
    }
    source_row = by_id.get(row.get("source_payload_row_id"))
    if not isinstance(source_row, dict):
        return False
    for key, source_key in (
        ("source_copy_row_id", "source_copy_row_id"),
        ("source_staging_file_row_id", "source_staging_file_row_id"),
        ("source_request_id", "source_request_id"),
        ("source_file_index", "source_file_index"),
        ("selected_artifact_kind", "artifact_kind"),
        ("selected_payload_path", "payload_path"),
        ("payload_kind", "payload_kind"),
        ("target_kind", "target_kind"),
        ("graph_id", "graph_id"),
        ("consumer_id", "consumer_id"),
        ("route_hints", "route_hints"),
        ("source_action_ids", "source_action_ids"),
        ("source_route_kinds", "source_route_kinds"),
    ):
        if row.get(key) != source_row.get(source_key):
            return False
    payload_path = row.get("selected_payload_path")
    selected_artifact_kind = row.get("selected_artifact_kind")
    manifold_handoff_selected = (
        selected_artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    )
    makepad_descriptor_selected = (
        selected_artifact_kind == SHELL_DESCRIPTOR_ARTIFACT_KIND
    )
    return (
        row.get("source_staged_payload_manifest_receipt_id")
        == staged_payload_manifest_receipt.get("receipt_id")
        and row.get("selection_status") == SELECTED_STATUS
        and row.get("issue_code") is None
        and row.get("payload_exists") is True
        and row.get("payload_under_staging_root") is True
        and isinstance(payload_path, str)
        and Path(payload_path).exists()
        and is_downstream_shell_selection_artifact_kind(selected_artifact_kind)
        and row.get("downstream_shell_descriptor_ready") is True
        and row.get("manifold_shell_handoff_candidate")
        is (source_row.get("manifold_shell_handoff_candidate") is True)
        and row.get("manifold_shell_handoff_selected")
        is manifold_handoff_selected
        and row.get("makepad_shell_selection_candidate") is True
        and row.get("makepad_shell_descriptor_selected")
        is makepad_descriptor_selected
        and row.get("downstream_shell_artifact_priority")
        == downstream_shell_artifact_priority(selected_artifact_kind)
        and not has_legacy_route_or_path(row)
        and hostess_downstream_shell_selection_row_no_runtime_started(row)
    )

def hostess_downstream_shell_selection_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("legacy_reference_dependency_used") is False
        and receipt.get("downstream_shell_runtime_started") is False
        and receipt.get("device_required") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("execution_performed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("build_started") is False
        and receipt.get("copy_started") is False
        and receipt.get("stage_started") is False
        and receipt.get("install_started") is False
        and receipt.get("launch_started") is False
        and receipt.get("evidence_collection_started") is False
        and receipt.get("command_session_started") is False
        and receipt.get("schema_artifact_payloads_copied") is False
        and receipt.get("release_payloads_copied") is False
        and receipt.get("staging_payloads_copied") is False
        and receipt.get("file_copy_performed") is False
    )

def hostess_downstream_shell_selection_row_no_runtime_started(
    row: dict[str, Any],
) -> bool:
    return (
        row.get("legacy_reference_dependency_used") is False
        and row.get("downstream_shell_runtime_started") is False
        and row.get("device_required") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("platform_execution_allowed") is False
        and row.get("studio_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("build_started") is False
        and row.get("copy_started") is False
        and row.get("stage_started") is False
        and row.get("install_started") is False
        and row.get("launch_started") is False
        and row.get("evidence_collection_started") is False
        and row.get("command_session_started") is False
    )
