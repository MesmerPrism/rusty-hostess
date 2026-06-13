"""Hostess staging file-plan receipt helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.staging_handoff_acceptance import *

def build_hostess_staging_file_plan_receipt(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    staging_root: str = "hostess-staging",
    source_file_plan_path: Path | None = None,
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    acceptance_ready = hostess_staging_handoff_acceptance_receipt_source_ready(
        handoff_acceptance_receipt
    )
    file_plan_ready = studio_hostess_staging_file_plan_source_ready(
        staging_file_plan,
        handoff_acceptance_receipt,
    )
    staging_root_ready = hostess_staging_root_ready(staging_root)
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    status = (
        ACCEPTED_STATUS
        if decision == ACCEPTED_STATUS
        and decision_supported
        and acceptance_ready
        and file_plan_ready
        and staging_root_ready
        else REJECTED_STATUS
    )
    issue_code = None
    if status != ACCEPTED_STATUS:
        issue_code = (
            reason_code
            or handoff_acceptance_receipt.get("issue_code")
            or staging_file_plan.get("issue_code")
            or (
                "hostess.issue.hostess_staging_file_plan_receipt_decision"
                if not decision_supported
                else "hostess.issue.hostess_staging_file_plan_source_not_ready"
            )
        )
    request_rows = hostess_staging_file_plan_request_rows(
        handoff_acceptance_receipt,
        staging_file_plan,
        staging_root,
        status,
        issue_code,
    )
    file_rows = hostess_staging_file_plan_file_rows(
        staging_file_plan,
        staging_root,
        status,
        issue_code,
    )
    checks = hostess_staging_file_plan_receipt_checks(
        handoff_acceptance_receipt,
        staging_file_plan,
        request_rows,
        file_rows,
        staging_root,
        status,
        decision_supported,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == ACCEPTED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        request_rows = hostess_staging_file_plan_request_rows(
            handoff_acceptance_receipt,
            staging_file_plan,
            staging_root,
            status,
            issue_code,
        )
        file_rows = hostess_staging_file_plan_file_rows(
            staging_file_plan,
            staging_root,
            status,
            issue_code,
        )
    accepted_requests = [
        row
        for row in request_rows
        if row.get("staging_request_status") == PLANNED_STATUS
    ]
    rejected_requests = [
        row
        for row in request_rows
        if row.get("staging_request_status") == REJECTED_STATUS
    ]
    accepted_files = [
        row for row in file_rows if row.get("file_copy_plan_status") == PLANNED_STATUS
    ]
    rejected_files = [
        row
        for row in file_rows
        if row.get("file_copy_plan_status") == REJECTED_STATUS
    ]
    source_receipt_id = handoff_acceptance_receipt.get("receipt_id")
    manifest_id = staging_file_plan.get("manifest_id")
    receipt_id = (
        f"hostess.staging_file_plan_receipt.{source_receipt_id}.{manifest_id}"
        if isinstance(source_receipt_id, str)
        and source_receipt_id
        and isinstance(manifest_id, str)
        and manifest_id
        else "hostess.staging_file_plan_receipt.unknown"
    )
    pmb_review_required = (
        handoff_acceptance_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        handoff_acceptance_receipt.get("pmb_shell_handoff_review_ready") is True
    )
    return {
        "$schema": HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_handoff_acceptance_receipt_id": source_receipt_id,
        "source_handoff_acceptance_receipt_schema": (
            handoff_acceptance_receipt.get("$schema")
        ),
        "source_handoff_acceptance_receipt_status": (
            handoff_acceptance_receipt.get("status")
        ),
        "source_staging_handoff_envelope_id": (
            handoff_acceptance_receipt.get("source_staging_handoff_envelope_id")
        ),
        "source_file_plan_schema": staging_file_plan.get("$schema"),
        "source_file_plan_status": staging_file_plan.get("status"),
        "source_file_plan_path": (
            str(source_file_plan_path) if source_file_plan_path else None
        ),
        "manifest_id": staging_file_plan.get("manifest_id"),
        "project_id": staging_file_plan.get("project_id"),
        "project_revision": staging_file_plan.get("project_revision"),
        "selected_candidate_id": staging_file_plan.get("selected_candidate_id"),
        "checksum_algorithm": handoff_acceptance_receipt.get("checksum_algorithm"),
        "plan_checksum": handoff_acceptance_receipt.get("plan_checksum"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_STAGING_FILE_PLAN_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "file_copy_plan_owner": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "staging_root": staging_root,
        "staging_file_plan_reviewed": status == ACCEPTED_STATUS,
        "copy_plan_ready": status == ACCEPTED_STATUS,
        "stage_generated_shells_request_accepted": (
            handoff_acceptance_receipt.get(
                "stage_generated_shells_request_accepted"
            )
            is True
        ),
        "stage_generated_shells_started": False,
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
        **pmb_shell_handoff_review_summary_from_source(handoff_acceptance_receipt),
        "request_count": len(request_rows),
        "accepted_request_count": len(accepted_requests),
        "rejected_request_count": len(rejected_requests),
        "file_count": len(file_rows),
        "accepted_file_count": len(accepted_files),
        "rejected_file_count": len(rejected_files),
        "target_request_count": sum(
            1 for row in request_rows if row.get("target_kind") is not None
        ),
        "shared_request_count": sum(
            1 for row in request_rows if row.get("target_kind") is None
        ),
        "staging_requests": request_rows,
        "staging_files": file_rows,
        "checks": checks,
        "next_required_action": (
            "hostess_copy_staging_files_from_reviewed_plan"
            if status == ACCEPTED_STATUS
            else "repair_or_decline_hostess_staging_file_plan"
        ),
    }

def validate_hostess_staging_file_plan_receipt(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    request_rows = hostess_staging_file_plan_request_dicts(receipt)
    file_rows = hostess_staging_file_plan_file_dicts(receipt)
    accepted_requests = [
        row
        for row in request_rows
        if row.get("staging_request_status") == PLANNED_STATUS
    ]
    rejected_requests = [
        row
        for row in request_rows
        if row.get("staging_request_status") == REJECTED_STATUS
    ]
    accepted_files = [
        row for row in file_rows if row.get("file_copy_plan_status") == PLANNED_STATUS
    ]
    rejected_files = [
        row
        for row in file_rows
        if row.get("file_copy_plan_status") == REJECTED_STATUS
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
    staging_root = receipt.get("staging_root")
    pmb_review_required = (
        handoff_acceptance_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_summary_matches_acceptance = (
        pmb_shell_handoff_review_summary_from_source(receipt)
        == pmb_shell_handoff_review_summary_from_source(
            handoff_acceptance_receipt
        )
    )
    checks = [
        check(
            "hostess.check.hostess_staging_file_plan_receipt.schema",
            receipt.get("$schema") == HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA,
            "Hostess staging file plan receipt schema is supported",
            "Hostess staging file plan receipt schema is unsupported",
            "hostess.issue.hostess_staging_file_plan_receipt_schema",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.status",
            status in {ACCEPTED_STATUS, REJECTED_STATUS}
            and (
                (status == ACCEPTED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess staging file plan receipt status is consistent",
            "Hostess staging file plan receipt status is inconsistent",
            "hostess.issue.hostess_staging_file_plan_receipt_status",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.execution_policy",
            receipt.get("execution_policy") == HOSTESS_STAGING_FILE_PLAN_RECEIPT_POLICY,
            "Hostess staging file plan receipt is schema-only",
            "Hostess staging file plan receipt execution policy drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_execution_policy",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.sources",
            receipt.get("source_handoff_acceptance_receipt_id")
            == handoff_acceptance_receipt.get("receipt_id")
            and receipt.get("source_handoff_acceptance_receipt_schema")
            == HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_SCHEMA
            and receipt.get("source_file_plan_schema")
            == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
            and receipt.get("manifest_id") == staging_file_plan.get("manifest_id")
            and receipt.get("project_id") == staging_file_plan.get("project_id")
            and receipt.get("project_revision")
            == staging_file_plan.get("project_revision")
            and receipt.get("selected_candidate_id")
            == staging_file_plan.get("selected_candidate_id"),
            "Hostess staging file plan sources match inputs",
            "Hostess staging file plan sources drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_source_mismatch",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.source_readiness",
            (
                status == ACCEPTED_STATUS
                and hostess_staging_handoff_acceptance_receipt_source_ready(
                    handoff_acceptance_receipt
                )
                and studio_hostess_staging_file_plan_source_ready(
                    staging_file_plan,
                    handoff_acceptance_receipt,
                )
                and hostess_staging_root_ready(staging_root)
            )
            or status == REJECTED_STATUS,
            "Hostess staging file plan sources are ready or rejected consistently",
            "Hostess staging file plan sources do not match receipt status",
            "hostess.issue.hostess_staging_file_plan_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != ACCEPTED_STATUS
            or (
                receipt.get("pmb_shell_handoff_review_required") is True
                and receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_acceptance
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            ),
            "accepted Hostess staging file plan preserves the PMB shell handoff gate",
            "accepted Hostess staging file plan dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_file_plan_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("file_copy_plan_owner") == HOSTESS_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "Hostess staging file plan receipt authority fields drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_authority",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.no_execution_started",
            hostess_staging_file_plan_receipt_unstarted(receipt),
            "Hostess staging file plan receipt has not started copying, execution, launch, or command sessions",
            "Hostess staging file plan receipt indicates copying, execution, launch, or command sessions",
            "hostess.issue.hostess_staging_file_plan_receipt_execution_started",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.requests",
            hostess_staging_file_plan_requests_match_sources(
                handoff_acceptance_receipt,
                staging_file_plan,
                request_rows,
                status,
            ),
            "Hostess staging file plan request rows match accepted handoff and source plan",
            "Hostess staging file plan request rows drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_request_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.files",
            hostess_staging_file_plan_files_match_source(
                staging_file_plan,
                file_rows,
                staging_root,
                status,
            ),
            "Hostess staging file rows match the source file plan",
            "Hostess staging file rows drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_file_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.destination_guards",
            hostess_staging_file_plan_rows_have_clean_destinations(
                request_rows,
                file_rows,
                staging_root,
            ),
            "Hostess staging destinations stay under the reviewed staging root and avoid legacy routes",
            "Hostess staging destinations or routes drifted toward unsafe or legacy paths",
            "hostess.issue.hostess_staging_file_plan_receipt_destination_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.counts",
            receipt.get("request_count") == len(request_rows)
            and receipt.get("accepted_request_count") == len(accepted_requests)
            and receipt.get("rejected_request_count") == len(rejected_requests)
            and receipt.get("file_count") == len(file_rows)
            and receipt.get("accepted_file_count") == len(accepted_files)
            and receipt.get("rejected_file_count") == len(rejected_files)
            and receipt.get("target_request_count")
            == sum(1 for row in request_rows if row.get("target_kind") is not None)
            and receipt.get("shared_request_count")
            == sum(1 for row in request_rows if row.get("target_kind") is None),
            "Hostess staging file plan receipt counts match nested records",
            "Hostess staging file plan receipt counts drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_count_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.scorecard",
            (
                status == ACCEPTED_STATUS
                and receipt.get("staging_file_plan_reviewed") is True
                and receipt.get("copy_plan_ready") is True
                and receipt.get("accepted_request_count")
                == staging_file_plan.get("request_count")
                and receipt.get("accepted_file_count")
                == staging_file_plan.get("planned_file_count")
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("staging_file_plan_reviewed") is False
                and receipt.get("copy_plan_ready") is False
            ),
            "Hostess staging file plan receipt scorecard matches receipt status",
            "Hostess staging file plan receipt scorecard drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_scorecard",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.embedded_checks",
            (
                status == ACCEPTED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess staging file plan receipt embedded checks match receipt status",
            "Hostess staging file plan receipt embedded checks do not match receipt status",
            "hostess.issue.hostess_staging_file_plan_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_STAGING_FILE_PLAN_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "copy_started": False,
        "staging_payloads_copied": False,
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

def hostess_staging_file_plan_receipt_checks(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    request_rows: list[dict[str, Any]],
    file_rows: list[dict[str, Any]],
    staging_root: str,
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = (
        handoff_acceptance_receipt.get("pmb_shell_handoff_review_required") is True
    )
    return [
        check(
            "hostess.check.hostess_staging_file_plan_receipt.acceptance_source",
            hostess_staging_handoff_acceptance_receipt_source_ready(
                handoff_acceptance_receipt
            ),
            "Hostess staging handoff acceptance receipt is accepted",
            "Hostess staging handoff acceptance receipt is missing, rejected, or drifted",
            handoff_acceptance_receipt.get("issue_code")
            or "hostess.issue.hostess_staging_handoff_acceptance_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.file_plan_source",
            studio_hostess_staging_file_plan_source_ready(
                staging_file_plan,
                handoff_acceptance_receipt,
            ),
            "Studio Hostess staging file plan is ready",
            "Studio Hostess staging file plan is missing, blocked, or drifted",
            staging_file_plan.get("issue_code")
            or "hostess.issue.hostess_staging_file_plan_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.staging_root",
            hostess_staging_root_ready(staging_root),
            "Hostess staging root is explicit",
            "Hostess staging root is missing",
            "hostess.issue.hostess_staging_file_plan_staging_root",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != ACCEPTED_STATUS
            or (
                handoff_acceptance_receipt.get("pmb_shell_handoff_review_ready")
                is True
                and pmb_shell_handoff_readiness_result_summary_valid(
                    handoff_acceptance_receipt
                )
            ),
            "accepted Hostess staging file plan preserves the PMB shell handoff gate",
            "accepted Hostess staging file plan dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_file_plan_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.decision",
            decision_supported,
            "Hostess staging file plan receipt decision is supported",
            "Hostess staging file plan receipt decision is unsupported",
            "hostess.issue.hostess_staging_file_plan_receipt_decision",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.requests",
            hostess_staging_file_plan_requests_match_sources(
                handoff_acceptance_receipt,
                staging_file_plan,
                request_rows,
                status,
            ),
            "Hostess staging file plan request rows match sources",
            "Hostess staging file plan request rows drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_request_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.files",
            hostess_staging_file_plan_files_match_source(
                staging_file_plan,
                file_rows,
                staging_root,
                status,
            ),
            "Hostess staging file rows match source plan",
            "Hostess staging file rows drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_file_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.destination_guards",
            hostess_staging_file_plan_rows_have_clean_destinations(
                request_rows,
                file_rows,
                staging_root,
            ),
            "Hostess staging destinations stay in the staging root and avoid legacy routes",
            "Hostess staging destinations or routes drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_destination_drift",
        ),
    ]

def hostess_staging_file_plan_request_rows(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    staging_root: str,
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    request_status = PLANNED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    accepted_by_id = {
        row.get("source_request_id"): row
        for row in hostess_staging_handoff_acceptance_request_dicts(
            handoff_acceptance_receipt
        )
    }
    rows = []
    for request in studio_hostess_staging_file_plan_request_dicts(staging_file_plan):
        request_id = request.get("request_id")
        accepted = accepted_by_id.get(request_id, {})
        planned_files = studio_hostess_staging_file_plan_planned_file_dicts(request)
        rows.append(
            {
                "staging_request_row_id": (
                    f"hostess.staging_file_plan_request.{request_id}"
                    if isinstance(request_id, str) and request_id
                    else "hostess.staging_file_plan_request.unknown"
                ),
                "source_handoff_acceptance_receipt_id": (
                    handoff_acceptance_receipt.get("receipt_id")
                ),
                "source_accepted_request_row_id": accepted.get(
                    "accepted_request_row_id"
                ),
                "source_request_id": request_id,
                "request_kind": request.get("request_kind"),
                "owner": request.get("owner"),
                "source_status": request.get("status"),
                "acceptance_status": accepted.get("acceptance_status"),
                "target_key": request.get("target_key"),
                "target_kind": request.get("target_kind"),
                "graph_id": request.get("graph_id"),
                "consumer_id": request.get("consumer_id"),
                "destination_root": request.get("destination_root"),
                "staging_root": staging_root,
                "planned_file_count": request.get("planned_file_count"),
                "source_plan_file_count": len(planned_files),
                "route_kinds": request.get("route_kinds"),
                "action_ids": request.get("action_ids"),
                "staging_request_status": request_status,
                "issue_code": None if request_status == PLANNED_STATUS else issue_code,
                "copy_plan_ready": request_status == PLANNED_STATUS,
                "stage_generated_shells_requested": True,
                "stage_generated_shells_started": False,
                "schema_artifact_payload_copied": False,
                "staging_payload_copied": False,
                "release_payload_copied": False,
                "file_copy_performed": False,
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

def hostess_staging_file_plan_file_rows(
    staging_file_plan: dict[str, Any],
    staging_root: str,
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    file_status = PLANNED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    rows = []
    for request in studio_hostess_staging_file_plan_request_dicts(staging_file_plan):
        request_id = request.get("request_id")
        destination_root = request.get("destination_root")
        for index, planned_file in enumerate(
            studio_hostess_staging_file_plan_planned_file_dicts(request)
        ):
            artifact_kind = planned_file.get("artifact_kind")
            destination_path = planned_file.get("destination_path")
            row_id = (
                f"hostess.staging_file_plan_file.{request_id}.{index}.{artifact_kind}"
                if isinstance(request_id, str)
                and request_id
                and isinstance(artifact_kind, str)
                and artifact_kind
                else f"hostess.staging_file_plan_file.unknown.{index}"
            )
            destination_valid = hostess_staging_destination_path_valid(
                destination_path,
                destination_root,
            )
            rows.append(
                {
                    "staging_file_row_id": row_id,
                    "source_request_id": request_id,
                    "source_file_index": index,
                    "artifact_kind": artifact_kind,
                    "source_path": planned_file.get("source_path"),
                    "destination_path": destination_path,
                    "destination_root": destination_root,
                    "destination_under_request_root": destination_valid,
                    "staging_root": staging_root,
                    "destination_absolute_path": staging_destination_absolute_path(
                        staging_root,
                        destination_path,
                    ),
                    "target_kind": planned_file.get("target_kind"),
                    "graph_id": planned_file.get("graph_id"),
                    "consumer_id": planned_file.get("consumer_id"),
                    "route_hints": planned_file.get("route_hints"),
                    "source_action_ids": planned_file.get("source_action_ids"),
                    "source_route_kinds": planned_file.get("source_route_kinds"),
                    "source_path_reviewed": isinstance(
                        planned_file.get("source_path"), str
                    )
                    and bool(planned_file.get("source_path")),
                    "destination_path_reviewed": destination_valid,
                    "file_copy_plan_status": file_status,
                    "issue_code": None if file_status == PLANNED_STATUS else issue_code,
                    "copy_plan_ready": file_status == PLANNED_STATUS,
                    "schema_artifact_payload_copied": False,
                    "staging_payload_copied": False,
                    "release_payload_copied": False,
                    "file_copy_performed": False,
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

def hostess_staging_file_plan_request_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = receipt.get("staging_requests", [])
    if not isinstance(requests, list):
        return []
    return [entry for entry in requests if isinstance(entry, dict)]

def hostess_staging_file_plan_file_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    files = receipt.get("staging_files", [])
    if not isinstance(files, list):
        return []
    return [entry for entry in files if isinstance(entry, dict)]

def studio_hostess_staging_file_plan_request_dicts(
    staging_file_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = staging_file_plan.get("requests", [])
    if not isinstance(requests, list):
        return []
    return [entry for entry in requests if isinstance(entry, dict)]

def studio_hostess_staging_file_plan_planned_file_dicts(
    request: dict[str, Any],
) -> list[dict[str, Any]]:
    files = request.get("planned_files", [])
    if not isinstance(files, list):
        return []
    return [entry for entry in files if isinstance(entry, dict)]

def hostess_staging_handoff_acceptance_receipt_source_ready(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("$schema") == HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_SCHEMA
        and receipt.get("status") == ACCEPTED_STATUS
        and receipt.get("issue_code") is None
        and receipt.get("receipt_owner") == HOSTESS_OWNER
        and receipt.get("staging_owner") == HOSTESS_OWNER
        and receipt.get("command_session_authority") == MANIFOLD_OWNER
        and receipt.get("requester_role") == STUDIO_REQUESTER
        and receipt.get("studio_role") == STUDIO_ROLE
        and receipt.get("staging_handoff_accepted") is True
        and receipt.get("stage_generated_shells_request_accepted") is True
        and hostess_staging_handoff_acceptance_receipt_unstarted(receipt)
        and (
            receipt.get("pmb_shell_handoff_review_required") is not True
            or (
                receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            )
        )
    )

def studio_hostess_staging_file_plan_source_ready(
    staging_file_plan: dict[str, Any],
    handoff_acceptance_receipt: dict[str, Any],
) -> bool:
    requests = studio_hostess_staging_file_plan_request_dicts(staging_file_plan)
    planned_file_count = sum(
        len(studio_hostess_staging_file_plan_planned_file_dicts(request))
        for request in requests
    )
    return (
        staging_file_plan.get("$schema") == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
        and staging_file_plan.get("status") == READY_STATUS
        and staging_file_plan.get("issue_code") is None
        and staging_file_plan.get("execution_policy") == "not_executed.dry_run_only"
        and staging_file_plan.get("staging_owner") == HOSTESS_OWNER
        and staging_file_plan.get("command_session_authority") == MANIFOLD_OWNER
        and staging_file_plan.get("install_launch_evidence_authority")
        == HOSTESS_OWNER
        and staging_file_plan.get("studio_role") == STUDIO_ROLE
        and staging_file_plan.get("manifest_id")
        == handoff_acceptance_receipt.get("manifest_id")
        and staging_file_plan.get("project_id")
        == handoff_acceptance_receipt.get("project_id")
        and staging_file_plan.get("project_revision")
        == handoff_acceptance_receipt.get("project_revision")
        and staging_file_plan.get("selected_candidate_id")
        == handoff_acceptance_receipt.get("selected_candidate_id")
        and staging_file_plan.get("request_count") == len(requests)
        and staging_file_plan.get("ready_request_count") == len(requests)
        and staging_file_plan.get("blocked_request_count") == 0
        and staging_file_plan.get("planned_file_count") == planned_file_count
        and all(
            action in staging_file_plan.get("prohibited_actions", [])
            for action in REQUIRED_PROHIBITED_ACTIONS
        )
        and all(
            studio_hostess_staging_file_plan_request_ready(request)
            for request in requests
        )
    )

def studio_hostess_staging_file_plan_request_ready(
    request: dict[str, Any],
) -> bool:
    files = studio_hostess_staging_file_plan_planned_file_dicts(request)
    destination_root = request.get("destination_root")
    return (
        request.get("owner") == HOSTESS_OWNER
        and request.get("status") == READY_STATUS
        and request.get("issue_code") is None
        and request.get("planned_file_count") == len(files)
        and "hostess.stage.generated_shells" in request.get("route_kinds", [])
        and not has_legacy_route_or_path(request)
        and all(
            studio_hostess_staging_file_plan_file_ready(file, destination_root)
            for file in files
        )
    )

def studio_hostess_staging_file_plan_file_ready(
    planned_file: dict[str, Any],
    destination_root: Any,
) -> bool:
    return (
        isinstance(planned_file.get("artifact_kind"), str)
        and bool(planned_file.get("artifact_kind"))
        and isinstance(planned_file.get("source_path"), str)
        and bool(planned_file.get("source_path"))
        and hostess_staging_destination_path_valid(
            planned_file.get("destination_path"),
            destination_root,
        )
        and any(
            route in planned_file.get("source_route_kinds", [])
            for route in (
                "hostess.stage.generated_shells",
                "hostess.review.release_candidate",
            )
        )
        and not has_legacy_route_or_path(planned_file)
    )

def hostess_staging_file_plan_requests_match_sources(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {ACCEPTED_STATUS, REJECTED_STATUS}:
        return False
    source_requests = studio_hostess_staging_file_plan_request_dicts(
        staging_file_plan
    )
    accepted_by_id = {
        row.get("source_request_id"): row
        for row in hostess_staging_handoff_acceptance_request_dicts(
            handoff_acceptance_receipt
        )
    }
    if len(rows) != len(source_requests):
        return False
    expected_status = PLANNED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    by_id = {row.get("source_request_id"): row for row in rows}
    for request in source_requests:
        request_id = request.get("request_id")
        row = by_id.get(request_id)
        accepted = accepted_by_id.get(request_id)
        if not isinstance(row, dict) or not isinstance(accepted, dict):
            return False
        for key in (
            "request_kind",
            "owner",
            "target_key",
            "target_kind",
            "graph_id",
            "consumer_id",
            "destination_root",
            "planned_file_count",
            "route_kinds",
            "action_ids",
        ):
            if row.get(key) != request.get(key):
                return False
        if row.get("source_status") != request.get("status"):
            return False
        if row.get("acceptance_status") != accepted.get("acceptance_status"):
            return False
        if row.get("source_plan_file_count") != len(
            studio_hostess_staging_file_plan_planned_file_dicts(request)
        ):
            return False
        if row.get("staging_request_status") != expected_status:
            return False
        if expected_status == PLANNED_STATUS and row.get("issue_code") is not None:
            return False
        if expected_status != PLANNED_STATUS and not isinstance(row.get("issue_code"), str):
            return False
        if row.get("copy_plan_ready") != (expected_status == PLANNED_STATUS):
            return False
        if not hostess_staging_file_plan_request_unstarted(row):
            return False
    return True

def hostess_staging_file_plan_files_match_source(
    staging_file_plan: dict[str, Any],
    rows: list[dict[str, Any]],
    staging_root: Any,
    status: Any,
) -> bool:
    if status not in {ACCEPTED_STATUS, REJECTED_STATUS}:
        return False
    expected_status = PLANNED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    expected_rows = []
    for request in studio_hostess_staging_file_plan_request_dicts(staging_file_plan):
        for index, planned_file in enumerate(
            studio_hostess_staging_file_plan_planned_file_dicts(request)
        ):
            expected_rows.append((request, index, planned_file))
    if len(rows) != len(expected_rows):
        return False
    by_key = {
        (row.get("source_request_id"), row.get("source_file_index")): row
        for row in rows
    }
    for request, index, planned_file in expected_rows:
        row = by_key.get((request.get("request_id"), index))
        if not isinstance(row, dict):
            return False
        for key in (
            "artifact_kind",
            "source_path",
            "destination_path",
            "target_kind",
            "graph_id",
            "consumer_id",
            "route_hints",
            "source_action_ids",
            "source_route_kinds",
        ):
            if row.get(key) != planned_file.get(key):
                return False
        destination_path = planned_file.get("destination_path")
        if row.get("destination_root") != request.get("destination_root"):
            return False
        if row.get("staging_root") != staging_root:
            return False
        if row.get("destination_absolute_path") != staging_destination_absolute_path(
            staging_root,
            destination_path,
        ):
            return False
        if row.get("destination_under_request_root") is not True:
            return False
        if row.get("destination_path_reviewed") is not True:
            return False
        if row.get("source_path_reviewed") is not True:
            return False
        if row.get("file_copy_plan_status") != expected_status:
            return False
        if expected_status == PLANNED_STATUS and row.get("issue_code") is not None:
            return False
        if expected_status != PLANNED_STATUS and not isinstance(row.get("issue_code"), str):
            return False
        if row.get("copy_plan_ready") != (expected_status == PLANNED_STATUS):
            return False
        if not hostess_staging_file_plan_file_unstarted(row):
            return False
    return True

def hostess_staging_file_plan_rows_have_clean_destinations(
    request_rows: list[dict[str, Any]],
    file_rows: list[dict[str, Any]],
    staging_root: Any,
) -> bool:
    if not hostess_staging_root_ready(staging_root):
        return False
    for row in request_rows:
        if has_legacy_route_or_path(row):
            return False
        destination_root = row.get("destination_root")
        if not isinstance(destination_root, str) or not destination_root:
            return False
    for row in file_rows:
        if has_legacy_route_or_path(row):
            return False
        if row.get("staging_root") != staging_root:
            return False
        if row.get("destination_under_request_root") is not True:
            return False
        if not hostess_staging_destination_path_valid(
            row.get("destination_path"),
            row.get("destination_root"),
        ):
            return False
        if row.get("destination_absolute_path") != staging_destination_absolute_path(
            staging_root,
            row.get("destination_path"),
        ):
            return False
    return True

def hostess_staging_root_ready(staging_root: Any) -> bool:
    return isinstance(staging_root, str) and bool(staging_root.strip())

def hostess_staging_destination_path_valid(
    destination_path: Any,
    destination_root: Any,
) -> bool:
    if not isinstance(destination_path, str) or not destination_path:
        return False
    if not isinstance(destination_root, str) or not destination_root:
        return False
    normalized = destination_path.replace("\\", "/")
    root = destination_root.replace("\\", "/").rstrip("/")
    if normalized.startswith("/") or ":" in normalized:
        return False
    if any(part in {"", ".", ".."} for part in normalized.split("/")):
        return False
    return normalized == root or normalized.startswith(root + "/")

def staging_destination_absolute_path(
    staging_root: Any,
    destination_path: Any,
) -> str | None:
    if not isinstance(staging_root, str) or not isinstance(destination_path, str):
        return None
    relative_parts = destination_path.replace("\\", "/").split("/")
    return str(Path(staging_root).joinpath(*relative_parts))

def has_legacy_route_or_path(item: dict[str, Any]) -> bool:
    legacy_tokens = ("legacy.rusty_xr", "legacy/rusty-xr", "Rusty-XR")
    for value in item.values():
        values = value if isinstance(value, list) else [value]
        for entry in values:
            if isinstance(entry, str) and any(token in entry for token in legacy_tokens):
                return True
    return False

def hostess_staging_file_plan_receipt_unstarted(receipt: dict[str, Any]) -> bool:
    return (
        all(receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
        and receipt.get("stage_generated_shells_started") is False
        and receipt.get("device_required") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("schema_artifact_payloads_copied") is False
        and receipt.get("release_payloads_copied") is False
        and receipt.get("staging_payloads_copied") is False
        and receipt.get("file_copy_performed") is False
    )

def hostess_staging_file_plan_request_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("stage_generated_shells_started") is False
        and row.get("schema_artifact_payload_copied") is False
        and row.get("staging_payload_copied") is False
        and row.get("release_payload_copied") is False
        and row.get("file_copy_performed") is False
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

def hostess_staging_file_plan_file_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("schema_artifact_payload_copied") is False
        and row.get("staging_payload_copied") is False
        and row.get("release_payload_copied") is False
        and row.get("file_copy_performed") is False
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
