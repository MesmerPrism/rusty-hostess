"""Hostess staged payload manifest receipt helpers."""

from __future__ import annotations

from typing import Any
from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.staging_handoff_file_copy import *

def build_hostess_staged_payload_manifest_receipt(
    staging_file_copy_receipt: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    source_ready = hostess_staging_file_copy_receipt_source_ready(
        staging_file_copy_receipt
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    status = (
        REVIEWED_STATUS
        if decision == ACCEPTED_STATUS and decision_supported and source_ready
        else REJECTED_STATUS
    )
    issue_code = None
    if status != REVIEWED_STATUS:
        issue_code = (
            reason_code
            or staging_file_copy_receipt.get("issue_code")
            or (
                "hostess.issue.hostess_staged_payload_manifest_receipt_decision"
                if not decision_supported
                else "hostess.issue.hostess_staging_file_copy_source_not_ready"
            )
        )
    payload_rows = hostess_staged_payload_manifest_rows(
        staging_file_copy_receipt,
        status,
        issue_code,
    )
    checks = hostess_staged_payload_manifest_receipt_checks(
        staging_file_copy_receipt,
        payload_rows,
        status,
        decision_supported,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == REVIEWED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        payload_rows = hostess_staged_payload_manifest_rows(
            staging_file_copy_receipt,
            status,
            issue_code,
        )
    reviewed_rows = [
        row
        for row in payload_rows
        if row.get("payload_review_status") == REVIEWED_STATUS
    ]
    rejected_rows = [
        row
        for row in payload_rows
        if row.get("payload_review_status") == REJECTED_STATUS
    ]
    descriptor_rows = [
        row
        for row in reviewed_rows
        if row.get("artifact_kind") == SHELL_DESCRIPTOR_ARTIFACT_KIND
    ]
    downstream_shell_rows = hostess_downstream_shell_payload_rows(reviewed_rows)
    target_descriptor_rows = hostess_target_downstream_shell_payload_rows(
        reviewed_rows
    )
    target_manifold_handoff_rows = [
        row
        for row in target_descriptor_rows
        if row.get("artifact_kind") == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    ]
    receipt_id = (
        f"hostess.staged_payload_manifest_receipt.{staging_file_copy_receipt.get('receipt_id')}"
        if isinstance(staging_file_copy_receipt.get("receipt_id"), str)
        and staging_file_copy_receipt.get("receipt_id")
        else "hostess.staged_payload_manifest_receipt.unknown"
    )
    reviewed = status == REVIEWED_STATUS
    pmb_review_required = (
        staging_file_copy_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        staging_file_copy_receipt.get("pmb_shell_handoff_review_ready") is True
    )
    return {
        "$schema": HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_staging_file_copy_receipt_id": staging_file_copy_receipt.get(
            "receipt_id"
        ),
        "source_staging_file_copy_receipt_schema": staging_file_copy_receipt.get(
            "$schema"
        ),
        "source_staging_file_copy_receipt_status": staging_file_copy_receipt.get(
            "status"
        ),
        "source_file_copy_completed": (
            staging_file_copy_receipt.get("file_copy_completed") is True
        ),
        "source_staging_payloads_copied": (
            staging_file_copy_receipt.get("staging_payloads_copied") is True
        ),
        "manifest_id": staging_file_copy_receipt.get("manifest_id"),
        "project_id": staging_file_copy_receipt.get("project_id"),
        "project_revision": staging_file_copy_receipt.get("project_revision"),
        "selected_candidate_id": staging_file_copy_receipt.get(
            "selected_candidate_id"
        ),
        "checksum_algorithm": staging_file_copy_receipt.get("checksum_algorithm"),
        "plan_checksum": staging_file_copy_receipt.get("plan_checksum"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "payload_manifest_owner": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "downstream_shell_consumer_role": "downstream.shell.consume_staged_descriptors",
        "staging_root": staging_file_copy_receipt.get("staging_root"),
        "payload_manifest_reviewed": reviewed,
        "staged_payloads_available": reviewed,
        "downstream_shell_selection_ready": reviewed and bool(target_descriptor_rows),
        "makepad_shell_selection_ready": reviewed and bool(target_descriptor_rows),
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
        **pmb_shell_handoff_review_summary_from_source(staging_file_copy_receipt),
        "payload_count": len(payload_rows),
        "reviewed_payload_count": len(reviewed_rows),
        "rejected_payload_count": len(rejected_rows),
        "descriptor_payload_count": len(descriptor_rows),
        "downstream_shell_payload_count": len(downstream_shell_rows),
        "target_descriptor_payload_count": len(target_descriptor_rows),
        "target_manifold_shell_handoff_payload_count": len(
            target_manifold_handoff_rows
        ),
        "shared_payload_count": sum(
            1 for row in reviewed_rows if row.get("target_kind") is None
        ),
        "payload_rows": payload_rows,
        "checks": checks,
        "next_required_action": (
            "downstream_shell_select_staged_descriptor_without_legacy_reference"
            if reviewed
            else "repair_or_decline_hostess_staged_payload_manifest"
        ),
    }

def validate_hostess_staged_payload_manifest_receipt(
    staging_file_copy_receipt: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    payload_rows = hostess_staged_payload_manifest_row_dicts(receipt)
    reviewed_rows = [
        row
        for row in payload_rows
        if row.get("payload_review_status") == REVIEWED_STATUS
    ]
    rejected_rows = [
        row
        for row in payload_rows
        if row.get("payload_review_status") == REJECTED_STATUS
    ]
    descriptor_rows = [
        row
        for row in reviewed_rows
        if row.get("artifact_kind") == SHELL_DESCRIPTOR_ARTIFACT_KIND
    ]
    downstream_shell_rows = hostess_downstream_shell_payload_rows(reviewed_rows)
    target_descriptor_rows = hostess_target_downstream_shell_payload_rows(
        reviewed_rows
    )
    target_manifold_handoff_rows = [
        row
        for row in target_descriptor_rows
        if row.get("artifact_kind") == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    ]
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
        staging_file_copy_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_summary_matches_copy = (
        pmb_shell_handoff_review_summary_from_source(receipt)
        == pmb_shell_handoff_review_summary_from_source(
            staging_file_copy_receipt
        )
    )
    checks = [
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.schema",
            receipt.get("$schema")
            == HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA,
            "Hostess staged payload manifest receipt schema is supported",
            "Hostess staged payload manifest receipt schema is unsupported",
            "hostess.issue.hostess_staged_payload_manifest_receipt_schema",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.status",
            status in {REVIEWED_STATUS, REJECTED_STATUS}
            and (
                (status == REVIEWED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess staged payload manifest receipt status is consistent",
            "Hostess staged payload manifest receipt status is inconsistent",
            "hostess.issue.hostess_staged_payload_manifest_receipt_status",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.execution_policy",
            receipt.get("execution_policy")
            == HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_POLICY,
            "Hostess staged payload manifest receipt is schema-only review",
            "Hostess staged payload manifest receipt execution policy drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_execution_policy",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.sources",
            receipt.get("source_staging_file_copy_receipt_id")
            == staging_file_copy_receipt.get("receipt_id")
            and receipt.get("source_staging_file_copy_receipt_schema")
            == HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA
            and receipt.get("manifest_id") == staging_file_copy_receipt.get("manifest_id")
            and receipt.get("project_id") == staging_file_copy_receipt.get("project_id")
            and receipt.get("project_revision")
            == staging_file_copy_receipt.get("project_revision"),
            "Hostess staged payload manifest sources match inputs",
            "Hostess staged payload manifest sources drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_source_mismatch",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.source_readiness",
            (
                status == REVIEWED_STATUS
                and hostess_staging_file_copy_receipt_source_ready(
                    staging_file_copy_receipt
                )
            )
            or status == REJECTED_STATUS,
            "Hostess staged payload manifest source is ready or rejected consistently",
            "Hostess staged payload manifest source does not match receipt status",
            "hostess.issue.hostess_staging_file_copy_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != REVIEWED_STATUS
            or (
                receipt.get("pmb_shell_handoff_review_required") is True
                and receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_copy
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            ),
            "reviewed Hostess staged payload manifest preserves the PMB shell handoff gate",
            "reviewed Hostess staged payload manifest dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staged_payload_manifest_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("payload_manifest_owner") == HOSTESS_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "Hostess staged payload manifest authority fields drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_authority",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.no_runtime_started",
            hostess_staged_payload_manifest_receipt_no_runtime_started(receipt),
            "Hostess staged payload manifest did not copy, install, launch, execute, or start command sessions",
            "Hostess staged payload manifest indicates copy, install, launch, runtime execution, or command sessions",
            "hostess.issue.hostess_staged_payload_manifest_receipt_runtime_started",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.payload_rows",
            hostess_staged_payload_rows_match_copy_receipt(
                staging_file_copy_receipt,
                payload_rows,
                status,
            ),
            "Hostess staged payload manifest rows match copied payload evidence",
            "Hostess staged payload manifest rows drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_payload_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.downstream_selection",
            (
                status == REVIEWED_STATUS
                and receipt.get("downstream_shell_selection_ready") is True
                and receipt.get("makepad_shell_selection_ready") is True
                and len(target_descriptor_rows) > 0
                and all(
                    row.get("downstream_shell_descriptor_ready") is True
                    for row in target_descriptor_rows
                )
                and receipt.get("legacy_reference_dependency_used") is False
            )
            or status == REJECTED_STATUS,
            "Hostess staged payload manifest exposes downstream shell descriptors without legacy reference dependency",
            "Hostess staged payload manifest is not ready for downstream shell descriptor selection",
            "hostess.issue.hostess_staged_payload_manifest_receipt_downstream_selection",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.counts",
            receipt.get("payload_count") == len(payload_rows)
            and receipt.get("reviewed_payload_count") == len(reviewed_rows)
            and receipt.get("rejected_payload_count") == len(rejected_rows)
            and receipt.get("descriptor_payload_count") == len(descriptor_rows)
            and receipt.get("downstream_shell_payload_count")
            == len(downstream_shell_rows)
            and receipt.get("target_descriptor_payload_count")
            == len(target_descriptor_rows)
            and receipt.get("target_manifold_shell_handoff_payload_count")
            == len(target_manifold_handoff_rows)
            and receipt.get("shared_payload_count")
            == sum(1 for row in reviewed_rows if row.get("target_kind") is None),
            "Hostess staged payload manifest counts match nested records",
            "Hostess staged payload manifest counts drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_count_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.embedded_checks",
            (
                status == REVIEWED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess staged payload manifest embedded checks match receipt status",
            "Hostess staged payload manifest embedded checks do not match receipt status",
            "hostess.issue.hostess_staged_payload_manifest_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_VALIDATION_SCHEMA,
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

def downstream_shell_artifact_priority(artifact_kind: Any) -> int:
    try:
        return DOWNSTREAM_SHELL_SELECTION_ARTIFACT_KINDS.index(artifact_kind)
    except ValueError:
        return len(DOWNSTREAM_SHELL_SELECTION_ARTIFACT_KINDS)

def is_downstream_shell_selection_artifact_kind(artifact_kind: Any) -> bool:
    return artifact_kind in DOWNSTREAM_SHELL_SELECTION_ARTIFACT_KINDS

def hostess_downstream_shell_payload_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("payload_review_status") == REVIEWED_STATUS
        and is_downstream_shell_selection_artifact_kind(row.get("artifact_kind"))
    ]

def hostess_target_downstream_shell_payload_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        row
        for row in hostess_downstream_shell_payload_rows(rows)
        if row.get("target_kind") is not None
        and isinstance(row.get("graph_id"), str)
        and isinstance(row.get("consumer_id"), str)
    ]

def hostess_staged_payload_manifest_receipt_checks(
    staging_file_copy_receipt: dict[str, Any],
    payload_rows: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = (
        staging_file_copy_receipt.get("pmb_shell_handoff_review_required") is True
    )
    target_descriptor_rows = hostess_target_downstream_shell_payload_rows(
        payload_rows
    )
    return [
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.copy_source",
            hostess_staging_file_copy_receipt_source_ready(
                staging_file_copy_receipt
            ),
            "Hostess staging file-copy receipt is completed and ready for payload review",
            "Hostess staging file-copy receipt is missing, rejected, or drifted",
            staging_file_copy_receipt.get("issue_code")
            or "hostess.issue.hostess_staging_file_copy_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != REVIEWED_STATUS
            or (
                staging_file_copy_receipt.get("pmb_shell_handoff_review_ready")
                is True
                and pmb_shell_handoff_readiness_result_summary_valid(
                    staging_file_copy_receipt
                )
            ),
            "reviewed Hostess staged payload manifest preserves the PMB shell handoff gate",
            "reviewed Hostess staged payload manifest dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staged_payload_manifest_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.decision",
            decision_supported,
            "Hostess staged payload manifest receipt decision is supported",
            "Hostess staged payload manifest receipt decision is unsupported",
            "hostess.issue.hostess_staged_payload_manifest_receipt_decision",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.payload_rows",
            hostess_staged_payload_rows_match_copy_receipt(
                staging_file_copy_receipt,
                payload_rows,
                status,
            ),
            "Hostess staged payload manifest rows match copied payload evidence",
            "Hostess staged payload manifest rows drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_payload_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.downstream_selection",
            status != REVIEWED_STATUS
            or (
                bool(target_descriptor_rows)
                and all(
                    row.get("downstream_shell_descriptor_ready") is True
                    for row in target_descriptor_rows
                )
            ),
            "Hostess staged payload manifest exposes target descriptors for downstream shell selection",
            "Hostess staged payload manifest has no target descriptor payload ready for downstream shell selection",
            "hostess.issue.hostess_staged_payload_manifest_receipt_downstream_selection",
        ),
    ]

def hostess_staged_payload_manifest_rows(
    staging_file_copy_receipt: dict[str, Any],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    payload_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    rows = []
    for copy_row in hostess_staging_file_copy_row_dicts(staging_file_copy_receipt):
        artifact_kind = copy_row.get("artifact_kind")
        target_kind = copy_row.get("target_kind")
        graph_id = copy_row.get("graph_id")
        consumer_id = copy_row.get("consumer_id")
        payload_path = copy_row.get("resolved_destination_path")
        payload_exists = (
            isinstance(payload_path, str) and Path(payload_path).exists()
        )
        descriptor_ready = (
            payload_status == REVIEWED_STATUS
            and is_downstream_shell_selection_artifact_kind(artifact_kind)
            and target_kind is not None
            and isinstance(graph_id, str)
            and bool(graph_id)
            and isinstance(consumer_id, str)
            and bool(consumer_id)
            and payload_exists
            and copy_row.get("destination_under_staging_root") is True
            and not has_legacy_route_or_path(copy_row)
        )
        rows.append(
            {
                "payload_row_id": (
                    f"hostess.staged_payload.{copy_row.get('copy_row_id')}"
                    if isinstance(copy_row.get("copy_row_id"), str)
                    and copy_row.get("copy_row_id")
                    else "hostess.staged_payload.unknown"
                ),
                "source_staging_file_copy_receipt_id": (
                    staging_file_copy_receipt.get("receipt_id")
                ),
                "source_copy_row_id": copy_row.get("copy_row_id"),
                "source_staging_file_row_id": copy_row.get(
                    "source_staging_file_row_id"
                ),
                "source_request_id": copy_row.get("source_request_id"),
                "source_file_index": copy_row.get("source_file_index"),
                "artifact_kind": artifact_kind,
                "payload_path": payload_path,
                "payload_exists": payload_exists,
                "payload_kind": copy_row.get("source_kind"),
                "payload_under_staging_root": copy_row.get(
                    "destination_under_staging_root"
                ),
                "target_kind": target_kind,
                "graph_id": graph_id,
                "consumer_id": consumer_id,
                "route_hints": copy_row.get("route_hints"),
                "source_action_ids": copy_row.get("source_action_ids"),
                "source_route_kinds": copy_row.get("source_route_kinds"),
                "payload_review_status": payload_status,
                "issue_code": None if payload_status == REVIEWED_STATUS else issue_code,
                "downstream_shell_descriptor_ready": descriptor_ready,
                "manifold_shell_handoff_candidate": (
                    descriptor_ready
                    and artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
                ),
                "makepad_shell_selection_candidate": descriptor_ready,
                "downstream_shell_artifact_priority": (
                    downstream_shell_artifact_priority(artifact_kind)
                    if descriptor_ready
                    else None
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
        )
    return rows

def hostess_staged_payload_manifest_row_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = receipt.get("payload_rows", [])
    if not isinstance(rows, list):
        return []
    return [entry for entry in rows if isinstance(entry, dict)]

def hostess_staged_payload_rows_match_copy_receipt(
    staging_file_copy_receipt: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {REVIEWED_STATUS, REJECTED_STATUS}:
        return False
    source_rows = hostess_staging_file_copy_row_dicts(staging_file_copy_receipt)
    if len(rows) != len(source_rows):
        return False
    expected_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    by_id = {row.get("source_copy_row_id"): row for row in rows}
    for source_row in source_rows:
        row = by_id.get(source_row.get("copy_row_id"))
        if not isinstance(row, dict):
            return False
        for key, source_key in (
            ("source_staging_file_row_id", "source_staging_file_row_id"),
            ("source_request_id", "source_request_id"),
            ("source_file_index", "source_file_index"),
            ("artifact_kind", "artifact_kind"),
            ("payload_path", "resolved_destination_path"),
            ("payload_kind", "source_kind"),
            ("payload_under_staging_root", "destination_under_staging_root"),
            ("target_kind", "target_kind"),
            ("graph_id", "graph_id"),
            ("consumer_id", "consumer_id"),
            ("route_hints", "route_hints"),
            ("source_action_ids", "source_action_ids"),
            ("source_route_kinds", "source_route_kinds"),
        ):
            if row.get(key) != source_row.get(source_key):
                return False
        if row.get("payload_review_status") != expected_status:
            return False
        if expected_status == REVIEWED_STATUS:
            if row.get("issue_code") is not None:
                return False
            if row.get("payload_exists") is not True:
                return False
            if has_legacy_route_or_path(row):
                return False
            if not hostess_staged_payload_row_no_runtime_started(row):
                return False
        else:
            if not isinstance(row.get("issue_code"), str):
                return False
            if not hostess_staged_payload_row_no_runtime_started(row):
                return False
    return True

def hostess_staged_payload_manifest_receipt_no_runtime_started(
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

def hostess_staged_payload_row_no_runtime_started(row: dict[str, Any]) -> bool:
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
