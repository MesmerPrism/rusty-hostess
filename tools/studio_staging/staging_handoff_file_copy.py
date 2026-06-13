"""Hostess staging file-copy receipt helpers."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.staging_handoff_file_plan import *

def build_hostess_staging_file_copy_receipt(
    staging_file_plan_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    source_ready = hostess_staging_file_plan_receipt_source_ready(
        staging_file_plan_receipt
    )
    preflight_checks = hostess_staging_file_copy_preflight_checks(
        staging_file_plan_receipt,
        staging_file_plan,
        decision_supported,
    )
    failed = [entry for entry in preflight_checks if entry["status"] == FAIL_STATUS]
    status = REJECTED_STATUS
    issue_code = (
        reason_code
        or staging_file_plan_receipt.get("issue_code")
        or (
            failed[0]["issue_code"]
            if failed
            else "hostess.issue.hostess_staging_file_copy_receipt_decision"
            if not decision_supported
            else None
        )
    )
    copy_rows = hostess_staging_file_copy_rejected_rows(
        staging_file_plan_receipt,
        issue_code,
    )
    copy_errors: list[str] = []
    if (
        decision == ACCEPTED_STATUS
        and decision_supported
        and source_ready
        and not failed
    ):
        copy_rows, copy_errors = perform_hostess_staging_file_copies(
            staging_file_plan_receipt
        )
        if copy_errors:
            issue_code = copy_errors[0]
        else:
            status = COMPLETED_STATUS
            issue_code = None
    copied_rows = [
        row for row in copy_rows if row.get("copy_status") == COMPLETED_STATUS
    ]
    rejected_rows = [
        row for row in copy_rows if row.get("copy_status") == REJECTED_STATUS
    ]
    receipt_id = (
        f"hostess.staging_file_copy_receipt.{staging_file_plan_receipt.get('receipt_id')}"
        if isinstance(staging_file_plan_receipt.get("receipt_id"), str)
        and staging_file_plan_receipt.get("receipt_id")
        else "hostess.staging_file_copy_receipt.unknown"
    )
    completed = status == COMPLETED_STATUS
    pmb_review_required = (
        staging_file_plan_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        staging_file_plan_receipt.get("pmb_shell_handoff_review_ready") is True
    )
    checks = hostess_staging_file_copy_receipt_checks(
        staging_file_plan_receipt,
        staging_file_plan,
        copy_rows,
        status,
        decision_supported,
        preflight_checks,
    )
    return {
        "$schema": HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_staging_file_plan_receipt_id": staging_file_plan_receipt.get(
            "receipt_id"
        ),
        "source_staging_file_plan_receipt_schema": staging_file_plan_receipt.get(
            "$schema"
        ),
        "source_staging_file_plan_receipt_status": staging_file_plan_receipt.get(
            "status"
        ),
        "source_file_plan_schema": staging_file_plan.get("$schema"),
        "source_file_plan_status": staging_file_plan.get("status"),
        "source_file_plan_path": staging_file_plan_receipt.get(
            "source_file_plan_path"
        ),
        "manifest_id": staging_file_plan_receipt.get("manifest_id"),
        "project_id": staging_file_plan_receipt.get("project_id"),
        "project_revision": staging_file_plan_receipt.get("project_revision"),
        "selected_candidate_id": staging_file_plan_receipt.get(
            "selected_candidate_id"
        ),
        "checksum_algorithm": staging_file_plan_receipt.get("checksum_algorithm"),
        "plan_checksum": staging_file_plan_receipt.get("plan_checksum"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_STAGING_FILE_COPY_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "file_copy_owner": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "staging_root": staging_file_plan_receipt.get("staging_root"),
        "copy_plan_ready": staging_file_plan_receipt.get("copy_plan_ready") is True,
        "file_copy_completed": completed,
        "stage_generated_shells_started": completed,
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "build_started": False,
        "copy_started": completed,
        "stage_started": completed,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "schema_artifact_payloads_copied": completed,
        "release_payloads_copied": False,
        "staging_payloads_copied": completed,
        "file_copy_performed": completed,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(staging_file_plan_receipt),
        "file_count": len(copy_rows),
        "copied_file_count": len(copied_rows),
        "rejected_file_count": len(rejected_rows),
        "copied_directory_count": sum(
            1 for row in copied_rows if row.get("source_kind") == "directory"
        ),
        "copied_regular_file_count": sum(
            1 for row in copied_rows if row.get("source_kind") == "file"
        ),
        "copy_rows": copy_rows,
        "checks": checks,
        "next_required_action": (
            "hostess_review_copied_staging_payloads_before_install_or_launch"
            if completed
            else "repair_or_decline_hostess_staging_file_copy"
        ),
    }

def validate_hostess_staging_file_copy_receipt(
    staging_file_plan_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    copy_rows = hostess_staging_file_copy_row_dicts(receipt)
    copied_rows = [
        row for row in copy_rows if row.get("copy_status") == COMPLETED_STATUS
    ]
    rejected_rows = [
        row for row in copy_rows if row.get("copy_status") == REJECTED_STATUS
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
        staging_file_plan_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_summary_matches_plan = (
        pmb_shell_handoff_review_summary_from_source(receipt)
        == pmb_shell_handoff_review_summary_from_source(
            staging_file_plan_receipt
        )
    )
    checks = [
        check(
            "hostess.check.hostess_staging_file_copy_receipt.schema",
            receipt.get("$schema") == HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA,
            "Hostess staging file copy receipt schema is supported",
            "Hostess staging file copy receipt schema is unsupported",
            "hostess.issue.hostess_staging_file_copy_receipt_schema",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.status",
            status in {COMPLETED_STATUS, REJECTED_STATUS}
            and (
                (status == COMPLETED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess staging file copy receipt status is consistent",
            "Hostess staging file copy receipt status is inconsistent",
            "hostess.issue.hostess_staging_file_copy_receipt_status",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.execution_policy",
            receipt.get("execution_policy") == HOSTESS_STAGING_FILE_COPY_RECEIPT_POLICY,
            "Hostess staging file copy receipt uses filesystem-only staging policy",
            "Hostess staging file copy receipt execution policy drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_execution_policy",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.sources",
            receipt.get("source_staging_file_plan_receipt_id")
            == staging_file_plan_receipt.get("receipt_id")
            and receipt.get("source_staging_file_plan_receipt_schema")
            == HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA
            and receipt.get("source_file_plan_schema")
            == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
            and receipt.get("manifest_id") == staging_file_plan_receipt.get("manifest_id")
            and receipt.get("project_id") == staging_file_plan_receipt.get("project_id")
            and receipt.get("project_revision")
            == staging_file_plan_receipt.get("project_revision"),
            "Hostess staging file copy sources match inputs",
            "Hostess staging file copy sources drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_source_mismatch",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.source_readiness",
            (
                status == COMPLETED_STATUS
                and hostess_staging_file_plan_receipt_source_ready(
                    staging_file_plan_receipt
                )
                and staging_file_plan.get("$schema")
                == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
            )
            or status == REJECTED_STATUS,
            "Hostess staging file copy sources are ready or rejected consistently",
            "Hostess staging file copy sources do not match receipt status",
            "hostess.issue.hostess_staging_file_copy_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != COMPLETED_STATUS
            or (
                receipt.get("pmb_shell_handoff_review_required") is True
                and receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_plan
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            ),
            "completed Hostess staging file copy preserves the PMB shell handoff gate",
            "completed Hostess staging file copy dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_file_copy_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("file_copy_owner") == HOSTESS_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "Hostess staging file copy authority fields drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_authority",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.no_runtime_started",
            hostess_staging_file_copy_receipt_no_runtime_started(receipt),
            "Hostess staging file copy did not install, launch, run platform code, or start command sessions",
            "Hostess staging file copy indicates install, launch, platform/runtime execution, or command sessions",
            "hostess.issue.hostess_staging_file_copy_receipt_runtime_started",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.copy_state",
            (
                status == COMPLETED_STATUS
                and receipt.get("file_copy_completed") is True
                and receipt.get("copy_started") is True
                and receipt.get("stage_started") is True
                and receipt.get("stage_generated_shells_started") is True
                and receipt.get("schema_artifact_payloads_copied") is True
                and receipt.get("staging_payloads_copied") is True
                and receipt.get("file_copy_performed") is True
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("file_copy_completed") is False
                and receipt.get("copy_started") is False
                and receipt.get("staging_payloads_copied") is False
                and receipt.get("file_copy_performed") is False
            ),
            "Hostess staging file copy state matches receipt status",
            "Hostess staging file copy state drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_copy_state",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.rows",
            hostess_staging_file_copy_rows_match_plan_receipt(
                staging_file_plan_receipt,
                copy_rows,
                status,
            ),
            "Hostess staging file copy rows match the accepted file-plan receipt",
            "Hostess staging file copy rows drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_row_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.destinations_exist",
            status != COMPLETED_STATUS
            or hostess_staging_file_copy_destinations_exist(copy_rows),
            "Hostess staging file copy destinations exist on disk",
            "Hostess staging file copy destinations are missing on disk",
            "hostess.issue.hostess_staging_file_copy_receipt_destination_missing",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.counts",
            receipt.get("file_count") == len(copy_rows)
            and receipt.get("copied_file_count") == len(copied_rows)
            and receipt.get("rejected_file_count") == len(rejected_rows)
            and receipt.get("copied_directory_count")
            == sum(1 for row in copied_rows if row.get("source_kind") == "directory")
            and receipt.get("copied_regular_file_count")
            == sum(1 for row in copied_rows if row.get("source_kind") == "file"),
            "Hostess staging file copy counts match nested records",
            "Hostess staging file copy counts drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_count_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.embedded_checks",
            (
                status == COMPLETED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess staging file copy embedded checks match receipt status",
            "Hostess staging file copy embedded checks do not match receipt status",
            "hostess.issue.hostess_staging_file_copy_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_STAGING_FILE_COPY_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "copy_started": receipt.get("copy_started") is True,
        "staging_payloads_copied": receipt.get("staging_payloads_copied") is True,
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

def hostess_staging_file_copy_receipt_source_ready(receipt: dict[str, Any]) -> bool:
    rows = hostess_staging_file_copy_row_dicts(receipt)
    return (
        receipt.get("$schema") == HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA
        and receipt.get("status") == COMPLETED_STATUS
        and receipt.get("issue_code") is None
        and receipt.get("receipt_owner") == HOSTESS_OWNER
        and receipt.get("staging_owner") == HOSTESS_OWNER
        and receipt.get("file_copy_owner") == HOSTESS_OWNER
        and receipt.get("command_session_authority") == MANIFOLD_OWNER
        and receipt.get("file_copy_completed") is True
        and receipt.get("staging_payloads_copied") is True
        and hostess_staging_file_copy_receipt_no_runtime_started(receipt)
        and hostess_staging_file_copy_rows_match_plan_receipt(
            receipt_from_copy_rows(receipt),
            rows,
            COMPLETED_STATUS,
        )
        and hostess_staging_file_copy_destinations_exist(rows)
        and (
            receipt.get("pmb_shell_handoff_review_required") is not True
            or (
                receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            )
        )
    )

def receipt_from_copy_rows(copy_receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "staging_files": [
            {
                "staging_file_row_id": row.get("source_staging_file_row_id"),
                "source_request_id": row.get("source_request_id"),
                "source_file_index": row.get("source_file_index"),
                "artifact_kind": row.get("artifact_kind"),
                "source_path": row.get("source_path"),
                "destination_path": row.get("destination_path"),
                "destination_root": row.get("destination_root"),
                "destination_absolute_path": row.get("destination_absolute_path"),
                "target_kind": row.get("target_kind"),
                "graph_id": row.get("graph_id"),
                "consumer_id": row.get("consumer_id"),
                "route_hints": row.get("route_hints"),
                "source_action_ids": row.get("source_action_ids"),
                "source_route_kinds": row.get("source_route_kinds"),
            }
            for row in hostess_staging_file_copy_row_dicts(copy_receipt)
        ]
    }

def hostess_staging_file_copy_preflight_checks(
    staging_file_plan_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    decision_supported: bool,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.hostess_staging_file_copy_receipt.file_plan_receipt_source",
            hostess_staging_file_plan_receipt_source_ready(
                staging_file_plan_receipt
            ),
            "Hostess staging file-plan receipt is accepted and ready for copy",
            "Hostess staging file-plan receipt is missing, rejected, or drifted",
            staging_file_plan_receipt.get("issue_code")
            or "hostess.issue.hostess_staging_file_plan_receipt_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.file_plan_source",
            staging_file_plan.get("$schema") == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
            and staging_file_plan.get("status") == READY_STATUS,
            "Studio Hostess staging file plan is available for copy evidence",
            "Studio Hostess staging file plan is unavailable or not ready",
            staging_file_plan.get("issue_code")
            or "hostess.issue.hostess_staging_file_copy_file_plan_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.sources_available",
            hostess_staging_file_copy_sources_available(staging_file_plan_receipt),
            "All Hostess staging file copy sources exist",
            "One or more Hostess staging file copy sources are missing",
            "hostess.issue.hostess_staging_file_copy_source_missing",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.destination_guards",
            hostess_staging_file_copy_destinations_are_safe(staging_file_plan_receipt),
            "All Hostess staging file copy destinations resolve under the staging root",
            "One or more Hostess staging file copy destinations escape the staging root",
            "hostess.issue.hostess_staging_file_copy_destination_unsafe",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.decision",
            decision_supported,
            "Hostess staging file copy receipt decision is supported",
            "Hostess staging file copy receipt decision is unsupported",
            "hostess.issue.hostess_staging_file_copy_receipt_decision",
        ),
    ]

def hostess_staging_file_copy_receipt_checks(
    staging_file_plan_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    copy_rows: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
    preflight_checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pmb_review_required = (
        staging_file_plan_receipt.get("pmb_shell_handoff_review_required") is True
    )
    return preflight_checks + [
        check(
            "hostess.check.hostess_staging_file_copy_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != COMPLETED_STATUS
            or (
                staging_file_plan_receipt.get("pmb_shell_handoff_review_ready")
                is True
                and pmb_shell_handoff_readiness_result_summary_valid(
                    staging_file_plan_receipt
                )
            ),
            "completed Hostess staging file copy preserves the PMB shell handoff gate",
            "completed Hostess staging file copy dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_file_copy_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.rows",
            hostess_staging_file_copy_rows_match_plan_receipt(
                staging_file_plan_receipt,
                copy_rows,
                status,
            ),
            "Hostess staging file copy rows match source receipt",
            "Hostess staging file copy rows drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_row_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.no_runtime_started",
            all(
                hostess_staging_file_copy_row_no_runtime_started(row)
                for row in copy_rows
            ),
            "Hostess staging file copy rows did not start runtime, install, launch, or command sessions",
            "Hostess staging file copy rows indicate runtime, install, launch, or command sessions",
            "hostess.issue.hostess_staging_file_copy_receipt_runtime_started",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.decision",
            decision_supported,
            "Hostess staging file copy receipt decision is supported",
            "Hostess staging file copy receipt decision is unsupported",
            "hostess.issue.hostess_staging_file_copy_receipt_decision",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.file_plan_source",
            staging_file_plan.get("$schema") == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA,
            "Studio Hostess staging file plan schema is available",
            "Studio Hostess staging file plan schema is unavailable",
            "hostess.issue.hostess_staging_file_copy_file_plan_not_ready",
        ),
    ]

def perform_hostess_staging_file_copies(
    staging_file_plan_receipt: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    errors = []
    for source_row in hostess_staging_file_plan_file_dicts(staging_file_plan_receipt):
        row = hostess_staging_file_copy_row_from_plan_row(
            staging_file_plan_receipt,
            source_row,
            COMPLETED_STATUS,
            None,
        )
        source_path = Path(row["resolved_source_path"])
        destination_path = Path(row["resolved_destination_path"])
        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if source_path.is_dir():
                shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
            else:
                shutil.copy2(source_path, destination_path)
            row["destination_exists_after_copy"] = destination_path.exists()
            row["copied_entry_count"] = copied_entry_count(destination_path)
        except Exception as exc:  # pragma: no cover - exact OS errors vary.
            issue = "hostess.issue.hostess_staging_file_copy_copy_failed"
            errors.append(issue)
            row["copy_status"] = REJECTED_STATUS
            row["issue_code"] = issue
            row["destination_exists_after_copy"] = destination_path.exists()
            row["copy_error"] = str(exc)
            row["schema_artifact_payload_copied"] = False
            row["staging_payload_copied"] = False
            row["file_copy_performed"] = False
            row["copy_started"] = False
            row["stage_started"] = False
        rows.append(row)
    return rows, errors

def hostess_staging_file_copy_rejected_rows(
    staging_file_plan_receipt: dict[str, Any],
    issue_code: str | None,
) -> list[dict[str, Any]]:
    return [
        hostess_staging_file_copy_row_from_plan_row(
            staging_file_plan_receipt,
            source_row,
            REJECTED_STATUS,
            issue_code or "hostess.issue.hostess_staging_file_copy_rejected",
        )
        for source_row in hostess_staging_file_plan_file_dicts(
            staging_file_plan_receipt
        )
    ]

def hostess_staging_file_copy_row_from_plan_row(
    staging_file_plan_receipt: dict[str, Any],
    source_row: dict[str, Any],
    copy_status: str,
    issue_code: str | None,
) -> dict[str, Any]:
    source_path = resolve_hostess_staging_copy_source_path(
        staging_file_plan_receipt,
        source_row,
    )
    destination_path = resolve_hostess_staging_copy_destination_path(
        staging_file_plan_receipt,
        source_row,
    )
    source_kind = (
        "directory"
        if source_path.is_dir()
        else "file"
        if source_path.is_file()
        else "missing"
    )
    completed = copy_status == COMPLETED_STATUS
    return {
        "copy_row_id": f"hostess.staging_file_copy.{source_row.get('staging_file_row_id')}",
        "source_staging_file_plan_receipt_id": staging_file_plan_receipt.get(
            "receipt_id"
        ),
        "source_staging_file_row_id": source_row.get("staging_file_row_id"),
        "source_request_id": source_row.get("source_request_id"),
        "source_file_index": source_row.get("source_file_index"),
        "artifact_kind": source_row.get("artifact_kind"),
        "source_path": source_row.get("source_path"),
        "resolved_source_path": str(source_path),
        "source_exists": source_path.exists(),
        "source_kind": source_kind,
        "destination_path": source_row.get("destination_path"),
        "destination_root": source_row.get("destination_root"),
        "destination_absolute_path": source_row.get("destination_absolute_path"),
        "resolved_destination_path": str(destination_path),
        "destination_under_staging_root": path_is_under_root(
            destination_path,
            staging_file_plan_receipt.get("staging_root"),
        ),
        "destination_exists_after_copy": destination_path.exists()
        if completed
        else False,
        "target_kind": source_row.get("target_kind"),
        "graph_id": source_row.get("graph_id"),
        "consumer_id": source_row.get("consumer_id"),
        "route_hints": source_row.get("route_hints"),
        "source_action_ids": source_row.get("source_action_ids"),
        "source_route_kinds": source_row.get("source_route_kinds"),
        "copy_status": copy_status,
        "issue_code": None if completed else issue_code,
        "copied_entry_count": copied_entry_count(destination_path)
        if completed and destination_path.exists()
        else 0,
        "schema_artifact_payload_copied": completed,
        "staging_payload_copied": completed,
        "release_payload_copied": False,
        "file_copy_performed": completed,
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_started": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "build_started": False,
        "copy_started": completed,
        "stage_started": completed,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
    }

def hostess_staging_file_copy_row_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = receipt.get("copy_rows", [])
    if not isinstance(rows, list):
        return []
    return [entry for entry in rows if isinstance(entry, dict)]

def hostess_staging_file_plan_receipt_source_ready(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("$schema") == HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA
        and receipt.get("status") == ACCEPTED_STATUS
        and receipt.get("issue_code") is None
        and receipt.get("receipt_owner") == HOSTESS_OWNER
        and receipt.get("staging_owner") == HOSTESS_OWNER
        and receipt.get("file_copy_plan_owner") == HOSTESS_OWNER
        and receipt.get("command_session_authority") == MANIFOLD_OWNER
        and receipt.get("copy_plan_ready") is True
        and receipt.get("staging_file_plan_reviewed") is True
        and hostess_staging_file_plan_receipt_unstarted(receipt)
        and (
            receipt.get("pmb_shell_handoff_review_required") is not True
            or (
                receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            )
        )
    )

def hostess_staging_file_copy_sources_available(
    staging_file_plan_receipt: dict[str, Any],
) -> bool:
    rows = hostess_staging_file_plan_file_dicts(staging_file_plan_receipt)
    return bool(rows) and all(
        resolve_hostess_staging_copy_source_path(
            staging_file_plan_receipt,
            row,
        ).exists()
        for row in rows
    )

def hostess_staging_file_copy_destinations_are_safe(
    staging_file_plan_receipt: dict[str, Any],
) -> bool:
    rows = hostess_staging_file_plan_file_dicts(staging_file_plan_receipt)
    return bool(rows) and all(
        path_is_under_root(
            resolve_hostess_staging_copy_destination_path(
                staging_file_plan_receipt,
                row,
            ),
            staging_file_plan_receipt.get("staging_root"),
        )
        for row in rows
    )

def hostess_staging_file_copy_rows_match_plan_receipt(
    staging_file_plan_receipt: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {COMPLETED_STATUS, REJECTED_STATUS}:
        return False
    source_rows = hostess_staging_file_plan_file_dicts(staging_file_plan_receipt)
    if len(rows) != len(source_rows):
        return False
    expected_status = COMPLETED_STATUS if status == COMPLETED_STATUS else REJECTED_STATUS
    by_id = {row.get("source_staging_file_row_id"): row for row in rows}
    for source_row in source_rows:
        row = by_id.get(source_row.get("staging_file_row_id"))
        if not isinstance(row, dict):
            return False
        for key in (
            "source_request_id",
            "source_file_index",
            "artifact_kind",
            "source_path",
            "destination_path",
            "destination_root",
            "destination_absolute_path",
            "target_kind",
            "graph_id",
            "consumer_id",
            "route_hints",
            "source_action_ids",
            "source_route_kinds",
        ):
            if row.get(key) != source_row.get(key):
                return False
        if row.get("copy_status") != expected_status:
            return False
        if expected_status == COMPLETED_STATUS:
            if row.get("issue_code") is not None:
                return False
            if row.get("source_exists") is not True:
                return False
            if row.get("source_kind") not in {"file", "directory"}:
                return False
            if row.get("destination_under_staging_root") is not True:
                return False
            if row.get("destination_exists_after_copy") is not True:
                return False
            if not hostess_staging_file_copy_row_completed(row):
                return False
        else:
            if not isinstance(row.get("issue_code"), str):
                return False
            if not hostess_staging_file_copy_row_rejected(row):
                return False
    return True

def hostess_staging_file_copy_destinations_exist(
    rows: list[dict[str, Any]],
) -> bool:
    return bool(rows) and all(
        isinstance(row.get("resolved_destination_path"), str)
        and Path(row["resolved_destination_path"]).exists()
        for row in rows
    )

def resolve_hostess_staging_copy_source_path(
    staging_file_plan_receipt: dict[str, Any],
    source_row: dict[str, Any],
) -> Path:
    raw_path = source_row.get("source_path")
    path = Path(raw_path) if isinstance(raw_path, str) else Path()
    if path.is_absolute():
        return path
    source_file_plan_path = staging_file_plan_receipt.get("source_file_plan_path")
    if isinstance(source_file_plan_path, str) and source_file_plan_path:
        return Path(source_file_plan_path).parent / path
    return path

def resolve_hostess_staging_copy_destination_path(
    staging_file_plan_receipt: dict[str, Any],
    source_row: dict[str, Any],
) -> Path:
    staging_root = staging_file_plan_receipt.get("staging_root")
    destination_path = source_row.get("destination_path")
    if not isinstance(staging_root, str) or not isinstance(destination_path, str):
        return Path()
    return Path(staging_root).joinpath(*destination_path.replace("\\", "/").split("/"))

def path_is_under_root(path: Path, root: Any) -> bool:
    if not isinstance(root, str) or not root:
        return False
    try:
        resolved_path = path.resolve()
        resolved_root = Path(root).resolve()
        resolved_path.relative_to(resolved_root)
        return True
    except (OSError, ValueError):
        return False

def copied_entry_count(path: Path) -> int:
    if path.is_file():
        return 1
    if not path.is_dir():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())

def hostess_staging_file_copy_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("device_required") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("execution_performed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("build_started") is False
        and receipt.get("install_started") is False
        and receipt.get("launch_started") is False
        and receipt.get("evidence_collection_started") is False
        and receipt.get("command_session_started") is False
        and receipt.get("release_payloads_copied") is False
    )

def hostess_staging_file_copy_row_no_runtime_started(row: dict[str, Any]) -> bool:
    return (
        row.get("device_required") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("platform_execution_allowed") is False
        and row.get("studio_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("build_started") is False
        and row.get("install_started") is False
        and row.get("launch_started") is False
        and row.get("evidence_collection_started") is False
        and row.get("command_session_started") is False
        and row.get("release_payload_copied") is False
    )

def hostess_staging_file_copy_row_completed(row: dict[str, Any]) -> bool:
    return (
        row.get("schema_artifact_payload_copied") is True
        and row.get("staging_payload_copied") is True
        and row.get("release_payload_copied") is False
        and row.get("file_copy_performed") is True
        and row.get("copy_started") is True
        and row.get("stage_started") is True
        and hostess_staging_file_copy_row_no_runtime_started(row)
    )

def hostess_staging_file_copy_row_rejected(row: dict[str, Any]) -> bool:
    return (
        row.get("schema_artifact_payload_copied") is False
        and row.get("staging_payload_copied") is False
        and row.get("release_payload_copied") is False
        and row.get("file_copy_performed") is False
        and row.get("copy_started") is False
        and row.get("stage_started") is False
        and hostess_staging_file_copy_row_no_runtime_started(row)
    )
