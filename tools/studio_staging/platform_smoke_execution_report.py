"""Platform smoke execution report helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.smoke_workflow import *  # smoke review bundle helpers
from tools.studio_staging.platform_smoke_operator_start import *  # prior platform-smoke phase helpers

def build_platform_smoke_execution_report(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    outcome: str = COMPLETED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    preflight_validation = validate_platform_smoke_operator_start_preflight_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
    )
    action_receipts = platform_smoke_operator_start_action_decision_receipt_dicts(
        operator_start_preflight
    )
    readiness_inputs = platform_smoke_operator_start_readiness_input_dicts(
        operator_start_preflight
    )
    outcome_supported = outcome in {COMPLETED_STATUS, REJECTED_STATUS}
    preflight_approved = (
        operator_start_preflight.get("status") == APPROVED_STATUS
        and preflight_validation.get("status") == PASS_STATUS
        and operator_start_preflight.get("operator_start_preflight_approved") is True
        and all(
            receipt.get("decision_status") == APPROVED_STATUS
            for receipt in action_receipts
        )
        and all(
            item.get("readiness_status") == APPROVED_STATUS
            for item in readiness_inputs
        )
    )
    status = (
        COMPLETED_STATUS
        if outcome == COMPLETED_STATUS and preflight_approved
        else REJECTED_STATUS
    )
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or operator_start_preflight.get("issue_code")
            or preflight_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_report_rejected"
        )
    action_reports = platform_smoke_execution_report_action_reports(
        operator_start_preflight,
        action_receipts,
        status,
        issue_code,
    )
    readiness_results = platform_smoke_execution_report_readiness_results(
        operator_start_preflight,
        readiness_inputs,
        status,
        issue_code,
    )
    evidence_placeholders = platform_smoke_execution_report_evidence_placeholders(
        action_reports,
        status,
        issue_code,
    )
    completed_actions = [
        item for item in action_reports if item.get("reported_status") == COMPLETED_STATUS
    ]
    rejected_actions = [
        item for item in action_reports if item.get("reported_status") == REJECTED_STATUS
    ]
    completed_readiness = [
        item for item in readiness_results if item.get("result_status") == COMPLETED_STATUS
    ]
    rejected_readiness = [
        item for item in readiness_results if item.get("result_status") == REJECTED_STATUS
    ]
    pending_placeholders = [
        item
        for item in evidence_placeholders
        if item.get("evidence_status") == PENDING_STATUS
    ]
    checks = platform_smoke_execution_report_checks(
        operator_start_preflight,
        preflight_validation,
        action_receipts,
        readiness_inputs,
        action_reports,
        readiness_results,
        evidence_placeholders,
        status,
        outcome_supported,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == COMPLETED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        action_reports = platform_smoke_execution_report_action_reports(
            operator_start_preflight,
            action_receipts,
            status,
            issue_code,
        )
        readiness_results = platform_smoke_execution_report_readiness_results(
            operator_start_preflight,
            readiness_inputs,
            status,
            issue_code,
        )
        evidence_placeholders = platform_smoke_execution_report_evidence_placeholders(
            action_reports,
            status,
            issue_code,
        )
        completed_actions = []
        rejected_actions = action_reports
        completed_readiness = []
        rejected_readiness = readiness_results
        pending_placeholders = evidence_placeholders

    preflight_id = operator_start_preflight.get("operator_start_preflight_receipt_id")
    report_id = (
        f"hostess.platform_smoke_execution_report.{preflight_id}"
        if isinstance(preflight_id, str) and preflight_id
        else "hostess.platform_smoke_execution_report.unknown"
    )
    pmb_review_required = (
        operator_start_preflight.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        operator_start_preflight.get("pmb_shell_handoff_review_ready") is True
    )

    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_REPORT_SCHEMA,
        "execution_report_id": report_id,
        "source_operator_start_preflight_receipt_id": preflight_id,
        "source_operator_start_gate_id": operator_start_preflight.get("source_operator_start_gate_id"),
        "source_execution_receipt_id": operator_start_preflight.get("source_execution_receipt_id"),
        "source_execution_request_id": operator_start_preflight.get("source_execution_request_id"),
        "source_approval_receipt_id": operator_start_preflight.get("source_approval_receipt_id"),
        "source_plan_id": operator_start_preflight.get("source_plan_id"),
        "source_bundle_id": operator_start_preflight.get("source_bundle_id"),
        "source_execution_id": operator_start_preflight.get("source_execution_id"),
        "source_request_id": operator_start_preflight.get("source_request_id"),
        "target_profile": operator_start_preflight.get("target_profile"),
        "target_platform": operator_start_preflight.get("target_platform"),
        "host_shell_kind": operator_start_preflight.get("host_shell_kind"),
        "status": status,
        "reported_outcome": outcome if outcome_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EXECUTION_REPORT_POLICY,
        "report_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": operator_start_preflight.get("host_shell_owner"),
        "platform_owner": operator_start_preflight.get("platform_owner"),
        "requester_role": operator_start_preflight.get("requester_role"),
        "command_session_authority": operator_start_preflight.get("command_session_authority"),
        "install_launch_evidence_authority": operator_start_preflight.get("install_launch_evidence_authority"),
        "studio_role": operator_start_preflight.get("studio_role"),
        "device_required": False,
        "target_device_required_for_external_execution": status == COMPLETED_STATUS,
        "operator_start_preflight_approved": status == COMPLETED_STATUS,
        "operator_started_outside_studio": status == COMPLETED_STATUS,
        "operator_start_acknowledged": status == COMPLETED_STATUS,
        "host_shell_started_outside_studio": status == COMPLETED_STATUS,
        "host_shell_reported": status == COMPLETED_STATUS,
        "real_platform_execution_evidence_attached": False,
        "requires_external_evidence": True,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(operator_start_preflight),
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
        "source_operator_start_preflight_status": operator_start_preflight.get("status"),
        "source_operator_start_preflight_validation_status": preflight_validation.get("status"),
        "source_operator_start_preflight_issue_code": (
            operator_start_preflight.get("issue_code") or preflight_validation.get("issue_code")
        ),
        "source_operator_start_action_decision_receipt_count": len(action_receipts),
        "action_report_count": len(action_reports),
        "completed_action_report_count": len(completed_actions),
        "rejected_action_report_count": len(rejected_actions),
        "readiness_input_count": len(readiness_inputs),
        "readiness_result_count": len(readiness_results),
        "completed_readiness_result_count": len(completed_readiness),
        "rejected_readiness_result_count": len(rejected_readiness),
        "evidence_placeholder_count": len(evidence_placeholders),
        "pending_evidence_placeholder_count": len(pending_placeholders),
        "source_operator_start_action_decision_receipts": action_receipts,
        "source_readiness_inputs": readiness_inputs,
        "action_reports": action_reports,
        "readiness_results": readiness_results,
        "evidence_placeholders": evidence_placeholders,
        "checks": checks,
        "next_required_action": (
            "attach_hostess_platform_smoke_evidence_outside_studio"
            if status == COMPLETED_STATUS
            else "repair_or_decline_platform_smoke_execution_report"
        ),
    }


def validate_platform_smoke_execution_report(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
) -> dict[str, Any]:
    preflight_validation = validate_platform_smoke_operator_start_preflight_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
    )
    action_receipts = platform_smoke_operator_start_action_decision_receipt_dicts(
        operator_start_preflight
    )
    readiness_inputs = platform_smoke_operator_start_readiness_input_dicts(
        operator_start_preflight
    )
    action_reports = platform_smoke_execution_report_action_report_dicts(execution_report)
    readiness_results = platform_smoke_execution_report_readiness_result_dicts(
        execution_report
    )
    evidence_placeholders = platform_smoke_execution_report_evidence_placeholder_dicts(
        execution_report
    )
    completed_actions = [
        item for item in action_reports if item.get("reported_status") == COMPLETED_STATUS
    ]
    rejected_actions = [
        item for item in action_reports if item.get("reported_status") == REJECTED_STATUS
    ]
    completed_readiness = [
        item for item in readiness_results if item.get("result_status") == COMPLETED_STATUS
    ]
    rejected_readiness = [
        item for item in readiness_results if item.get("result_status") == REJECTED_STATUS
    ]
    pending_placeholders = [
        item
        for item in evidence_placeholders
        if item.get("evidence_status") == PENDING_STATUS
    ]
    embedded_checks = execution_report.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    pmb_review_required = (
        operator_start_preflight.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_result = next(
        (
            item
            for item in readiness_results
            if item.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    pmb_review_summary_matches_preflight = (
        pmb_shell_handoff_review_summary_from_source(execution_report)
        == pmb_shell_handoff_review_summary_from_source(operator_start_preflight)
    )
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.schema",
            execution_report.get("$schema") == PLATFORM_SMOKE_EXECUTION_REPORT_SCHEMA,
            "platform smoke execution report schema is supported",
            "platform smoke execution report schema is unsupported",
            "hostess.issue.platform_smoke_execution_report_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.preflight_id",
            execution_report.get("source_operator_start_preflight_receipt_id")
            == operator_start_preflight.get("operator_start_preflight_receipt_id"),
            "platform smoke execution report preflight id matches",
            "platform smoke execution report preflight id differs",
            "hostess.issue.platform_smoke_execution_report_preflight_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.status",
            execution_report.get("status") in {COMPLETED_STATUS, REJECTED_STATUS},
            "platform smoke execution report status is supported",
            "platform smoke execution report status is unsupported",
            "hostess.issue.platform_smoke_execution_report_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.execution_policy",
            execution_report.get("execution_policy") == PLATFORM_SMOKE_EXECUTION_REPORT_POLICY,
            "platform smoke execution report is report-only",
            "platform smoke execution report execution policy drifted",
            "hostess.issue.platform_smoke_execution_report_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.schema_path_boundary",
            all(execution_report.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and execution_report.get("runtime_execution_performed") is False
            and execution_report.get("platform_execution_performed") is False
            and execution_report.get("schema_path_execution_allowed") is False
            and execution_report.get("platform_execution_allowed") is False
            and execution_report.get("studio_execution_allowed") is False
            and execution_report.get("device_required") is False
            and execution_report.get("real_platform_execution_evidence_attached") is False,
            "platform smoke execution report keeps Studio, schema path, runtime, and evidence execution disabled",
            "platform smoke execution report indicates Studio, schema path, runtime, or evidence execution",
            "hostess.issue.platform_smoke_execution_report_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.authority",
            execution_report.get("report_owner") == HOSTESS_OWNER
            and execution_report.get("operator_start_owner") == HOSTESS_OWNER
            and execution_report.get("host_shell_owner") == HOSTESS_OWNER
            and execution_report.get("platform_owner") == HOSTESS_OWNER
            and execution_report.get("requester_role") == STUDIO_REQUESTER
            and execution_report.get("command_session_authority") == MANIFOLD_OWNER
            and execution_report.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and execution_report.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.source_preflight",
            execution_report.get("status") != COMPLETED_STATUS
            or (
                operator_start_preflight.get("status") == APPROVED_STATUS
                and preflight_validation.get("status") == PASS_STATUS
                and operator_start_preflight.get("operator_start_preflight_approved") is True
            ),
            "source operator-start preflight is approved and validates",
            "source operator-start preflight is rejected or invalid",
            operator_start_preflight.get("issue_code")
            or preflight_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_report_preflight_not_approved",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.pmb_shell_handoff_review",
            not pmb_review_required
            or execution_report.get("status") != COMPLETED_STATUS
            or (
                execution_report.get("pmb_shell_handoff_review_required") is True
                and execution_report.get("pmb_shell_handoff_review_ready") is True
                and pmb_review_summary_matches_preflight
                and isinstance(pmb_review_result, dict)
                and pmb_review_result.get("result_status") == COMPLETED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_review_result)
            ),
            "completed platform smoke execution report preserves the PMB shell handoff gate",
            "completed platform smoke execution report dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_execution_report_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.action_reports",
            platform_smoke_execution_report_action_reports_match_receipts(
                action_receipts,
                action_reports,
                execution_report.get("status"),
            ),
            "platform smoke execution action reports match source action decision receipts",
            "platform smoke execution action reports drifted",
            "hostess.issue.platform_smoke_execution_report_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.readiness_results",
            platform_smoke_execution_report_readiness_results_match_inputs(
                readiness_inputs,
                readiness_results,
                execution_report.get("status"),
            ),
            "platform smoke execution readiness results match source readiness inputs",
            "platform smoke execution readiness results drifted",
            "hostess.issue.platform_smoke_execution_report_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.evidence_placeholders",
            platform_smoke_execution_report_evidence_placeholders_match_reports(
                action_reports,
                evidence_placeholders,
            ),
            "platform smoke execution evidence placeholders match action reports and remain pending",
            "platform smoke execution evidence placeholders drifted or include collected evidence",
            "hostess.issue.platform_smoke_execution_report_evidence_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.counts",
            execution_report.get("source_operator_start_action_decision_receipt_count")
            == len(action_receipts)
            and execution_report.get("action_report_count") == len(action_reports)
            and execution_report.get("completed_action_report_count") == len(completed_actions)
            and execution_report.get("rejected_action_report_count") == len(rejected_actions)
            and execution_report.get("readiness_input_count") == len(readiness_inputs)
            and execution_report.get("readiness_result_count") == len(readiness_results)
            and execution_report.get("completed_readiness_result_count") == len(completed_readiness)
            and execution_report.get("rejected_readiness_result_count") == len(rejected_readiness)
            and execution_report.get("evidence_placeholder_count") == len(evidence_placeholders)
            and execution_report.get("pending_evidence_placeholder_count") == len(pending_placeholders),
            "platform smoke execution report counts match nested reports and placeholders",
            "platform smoke execution report counts drifted",
            "hostess.issue.platform_smoke_execution_report_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.completed_consistency",
            execution_report.get("status") != COMPLETED_STATUS
            or (
                execution_report.get("operator_start_preflight_approved") is True
                and execution_report.get("operator_started_outside_studio") is True
                and execution_report.get("operator_start_acknowledged") is True
                and execution_report.get("host_shell_started_outside_studio") is True
                and execution_report.get("host_shell_reported") is True
                and execution_report.get("requires_external_evidence") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(item.get("reported_status") == COMPLETED_STATUS for item in action_reports)
                and all(item.get("result_status") == COMPLETED_STATUS for item in readiness_results)
                and all(
                    item.get("evidence_status") == PENDING_STATUS
                    and item.get("collected") is False
                    and item.get("attached") is False
                    for item in evidence_placeholders
                )
            ),
            "completed platform smoke execution report records operator start while evidence remains external",
            "completed platform smoke execution report is inconsistent",
            "hostess.issue.platform_smoke_execution_report_completed_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.rejection_reason",
            execution_report.get("status") != REJECTED_STATUS
            or isinstance(execution_report.get("issue_code"), str),
            "rejected platform smoke execution report carries a reason code",
            "rejected platform smoke execution report is missing a reason code",
            "hostess.issue.platform_smoke_execution_report_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_REPORT_VALIDATION_SCHEMA,
        "execution_report_id": execution_report.get("execution_report_id"),
        "source_operator_start_preflight_receipt_id": execution_report.get(
            "source_operator_start_preflight_receipt_id"
        ),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "pmb_shell_handoff_review_required": execution_report.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": execution_report.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "real_platform_execution_evidence_attached": False,
        "checks": checks,
    }


def platform_smoke_execution_report_checks(
    operator_start_preflight: dict[str, Any],
    preflight_validation: dict[str, Any],
    action_receipts: list[dict[str, Any]],
    readiness_inputs: list[dict[str, Any]],
    action_reports: list[dict[str, Any]],
    readiness_results: list[dict[str, Any]],
    evidence_placeholders: list[dict[str, Any]],
    status: str,
    outcome_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = (
        operator_start_preflight.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        operator_start_preflight.get("pmb_shell_handoff_review_ready") is True
    )
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.source_preflight",
            operator_start_preflight.get("$schema")
            == PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_SCHEMA
            and operator_start_preflight.get("status") == APPROVED_STATUS
            and preflight_validation.get("status") == PASS_STATUS,
            "platform smoke operator-start preflight is approved and validates",
            "platform smoke operator-start preflight is rejected or invalid",
            operator_start_preflight.get("issue_code")
            or preflight_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_report_preflight_not_approved",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.outcome",
            outcome_supported,
            "platform smoke execution report outcome is supported",
            "platform smoke execution report outcome is unsupported",
            "hostess.issue.platform_smoke_execution_report_outcome",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.action_receipts",
            all(
                receipt.get("decision_status") == APPROVED_STATUS
                and platform_smoke_operator_start_action_decision_receipt_unstarted(receipt)
                for receipt in action_receipts
            ),
            "platform smoke operator-start action decision receipts are approved and unstarted",
            "platform smoke operator-start action decision receipts are rejected, drifted, or started",
            "hostess.issue.platform_smoke_execution_report_preflight_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.readiness_inputs",
            all(
                item.get("readiness_status") == APPROVED_STATUS
                and platform_smoke_operator_start_readiness_input_unstarted(item)
                for item in readiness_inputs
            ),
            "platform smoke operator-start readiness inputs are approved and unstarted",
            "platform smoke operator-start readiness inputs are rejected, drifted, or started",
            "hostess.issue.platform_smoke_execution_report_preflight_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.pmb_shell_handoff_review",
            not pmb_review_required
            or status != COMPLETED_STATUS
            or (
                pmb_review_ready
                and any(
                    result.get("source_readiness_input_id")
                    == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
                    and result.get("result_status") == COMPLETED_STATUS
                    and pmb_shell_handoff_readiness_result_summary_valid(result)
                    for result in readiness_results
                )
            ),
            "completed platform smoke execution report preserves the PMB shell handoff gate",
            "completed platform smoke execution report dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_execution_report_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.action_reports",
            platform_smoke_execution_report_action_reports_match_receipts(
                action_receipts,
                action_reports,
                status,
            ),
            "platform smoke execution action reports match source receipts",
            "platform smoke execution action reports drifted",
            "hostess.issue.platform_smoke_execution_report_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.readiness_results",
            platform_smoke_execution_report_readiness_results_match_inputs(
                readiness_inputs,
                readiness_results,
                status,
            ),
            "platform smoke execution readiness results match source inputs",
            "platform smoke execution readiness results drifted",
            "hostess.issue.platform_smoke_execution_report_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.evidence_placeholders",
            platform_smoke_execution_report_evidence_placeholders_match_reports(
                action_reports,
                evidence_placeholders,
            ),
            "platform smoke execution evidence placeholders match action reports and remain pending",
            "platform smoke execution evidence placeholders drifted or include collected evidence",
            "hostess.issue.platform_smoke_execution_report_evidence_drift",
        ),
    ]


def platform_smoke_execution_report_action_reports(
    operator_start_preflight: dict[str, Any],
    action_receipts: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    reported_status = COMPLETED_STATUS if status == COMPLETED_STATUS else REJECTED_STATUS
    reports = []
    for receipt in action_receipts:
        source_plan_action_id = receipt.get("source_plan_action_id")
        evidence_placeholder_id = (
            f"hostess.platform_smoke_execution_evidence_placeholder.{source_plan_action_id}"
            if isinstance(source_plan_action_id, str) and source_plan_action_id
            else "hostess.platform_smoke_execution_evidence_placeholder.unknown"
        )
        reports.append(
            {
                "action_report_id": (
                    f"hostess.platform_smoke_execution_action_report.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_execution_action_report.unknown"
                ),
                "source_operator_start_preflight_receipt_id": operator_start_preflight.get(
                    "operator_start_preflight_receipt_id"
                ),
                "source_action_decision_receipt_id": receipt.get(
                    "action_decision_receipt_id"
                ),
                "source_action_gate_id": receipt.get("source_action_gate_id"),
                "source_plan_id": receipt.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": receipt.get("owner"),
                "route_kind": receipt.get("route_kind"),
                "action_kind": receipt.get("action_kind"),
                "approval_kind": receipt.get("approval_kind"),
                "expected_input_kind": receipt.get("expected_input_kind"),
                "expected_output_kind": receipt.get("expected_output_kind"),
                "reported_status": reported_status,
                "issue_code": None if reported_status == COMPLETED_STATUS else issue_code,
                "operator_started_outside_studio": reported_status == COMPLETED_STATUS,
                "operator_start_acknowledged": reported_status == COMPLETED_STATUS,
                "host_shell_reported": reported_status == COMPLETED_STATUS,
                "host_shell_started_outside_studio": reported_status == COMPLETED_STATUS,
                "evidence_placeholder_id": evidence_placeholder_id,
                "requires_external_evidence": True,
                "studio_execution_allowed": False,
                "schema_path_execution_allowed": False,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "real_platform_execution_evidence_attached": False,
                "command_session_started": False,
            }
        )
    return reports


def platform_smoke_execution_report_readiness_results(
    operator_start_preflight: dict[str, Any],
    readiness_inputs: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    result_status = COMPLETED_STATUS if status == COMPLETED_STATUS else REJECTED_STATUS
    results = []
    for item in readiness_inputs:
        readiness_input_id = item.get("readiness_input_id")
        result = {
            "readiness_result_id": (
                f"hostess.platform_smoke_execution_readiness_result.{readiness_input_id}"
                if isinstance(readiness_input_id, str) and readiness_input_id
                else "hostess.platform_smoke_execution_readiness_result.unknown"
            ),
            "source_operator_start_preflight_receipt_id": operator_start_preflight.get(
                "operator_start_preflight_receipt_id"
            ),
            "source_readiness_input_id": readiness_input_id,
            "owner": item.get("owner"),
            "input_kind": item.get("input_kind"),
            "expected_source_kind": item.get("expected_source_kind"),
            "validation_kind": item.get("validation_kind"),
            "result_status": result_status,
            "issue_code": None if result_status == COMPLETED_STATUS else issue_code,
            "operator_supplied": result_status == COMPLETED_STATUS,
            "validated_for_report": True,
            "validated_for_execution": False,
            "operator_started_outside_studio": result_status == COMPLETED_STATUS,
            "studio_execution_allowed": False,
            "schema_path_execution_allowed": False,
            "execution_started": False,
            "runtime_execution_performed": False,
            "platform_execution_performed": False,
            "command_session_started": False,
        }
        if readiness_input_id == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID:
            result.update(pmb_shell_handoff_review_summary_from_source(item))
        results.append(result)
    return results


def platform_smoke_execution_report_evidence_placeholders(
    action_reports: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    placeholders = []
    for report in action_reports:
        placeholders.append(
            {
                "evidence_placeholder_id": report.get("evidence_placeholder_id"),
                "source_action_report_id": report.get("action_report_id"),
                "source_plan_id": report.get("source_plan_id"),
                "source_plan_action_id": report.get("source_plan_action_id"),
                "owner": report.get("owner"),
                "route_kind": report.get("route_kind"),
                "required_evidence_kind": report.get("expected_output_kind"),
                "evidence_status": PENDING_STATUS,
                "issue_code": None if status == COMPLETED_STATUS else issue_code,
                "collected": False,
                "attached": False,
                "collection_started": False,
                "requires_external_attachment": True,
                "studio_execution_allowed": False,
                "schema_path_execution_allowed": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "command_session_started": False,
            }
        )
    return placeholders


def platform_smoke_execution_report_action_report_dicts(
    execution_report: dict[str, Any],
) -> list[dict[str, Any]]:
    reports = execution_report.get("action_reports", [])
    if not isinstance(reports, list):
        return []
    return [item for item in reports if isinstance(item, dict)]


def platform_smoke_execution_report_readiness_result_dicts(
    execution_report: dict[str, Any],
) -> list[dict[str, Any]]:
    results = execution_report.get("readiness_results", [])
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


def platform_smoke_execution_report_evidence_placeholder_dicts(
    execution_report: dict[str, Any],
) -> list[dict[str, Any]]:
    placeholders = execution_report.get("evidence_placeholders", [])
    if not isinstance(placeholders, list):
        return []
    return [item for item in placeholders if isinstance(item, dict)]


def platform_smoke_execution_report_action_reports_match_receipts(
    action_receipts: list[dict[str, Any]],
    action_reports: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {COMPLETED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        report.get("source_action_decision_receipt_id"): report
        for report in action_reports
    }
    if len(action_reports) != len(action_receipts):
        return False
    for receipt in action_receipts:
        report = by_id.get(receipt.get("action_decision_receipt_id"))
        if not isinstance(report, dict):
            return False
        for key in (
            "owner",
            "route_kind",
            "action_kind",
            "approval_kind",
            "expected_input_kind",
            "expected_output_kind",
        ):
            if report.get(key) != receipt.get(key):
                return False
        if report.get("source_plan_action_id") != receipt.get("source_plan_action_id"):
            return False
        if report.get("reported_status") != status:
            return False
        if report.get("operator_started_outside_studio") != (status == COMPLETED_STATUS):
            return False
        if report.get("operator_start_acknowledged") != (status == COMPLETED_STATUS):
            return False
        if report.get("host_shell_reported") != (status == COMPLETED_STATUS):
            return False
        if report.get("host_shell_started_outside_studio") != (status == COMPLETED_STATUS):
            return False
        if report.get("requires_external_evidence") is not True:
            return False
        if not platform_smoke_execution_report_action_report_schema_unstarted(report):
            return False
    return True


def platform_smoke_execution_report_readiness_results_match_inputs(
    readiness_inputs: list[dict[str, Any]],
    readiness_results: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {COMPLETED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        result.get("source_readiness_input_id"): result
        for result in readiness_results
    }
    if len(readiness_results) != len(readiness_inputs):
        return False
    for item in readiness_inputs:
        result = by_id.get(item.get("readiness_input_id"))
        if not isinstance(result, dict):
            return False
        for key in ("owner", "input_kind", "expected_source_kind", "validation_kind"):
            if result.get(key) != item.get(key):
                return False
        if result.get("result_status") != status:
            return False
        if result.get("operator_supplied") != (status == COMPLETED_STATUS):
            return False
        if result.get("validated_for_report") is not True:
            return False
        if result.get("validated_for_execution") is not False:
            return False
        if result.get("operator_started_outside_studio") != (status == COMPLETED_STATUS):
            return False
        if not platform_smoke_execution_report_readiness_result_schema_unstarted(result):
            return False
        if item.get("readiness_input_id") == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID:
            if status == COMPLETED_STATUS and not (
                pmb_shell_handoff_readiness_input_summary_valid(item)
                and pmb_shell_handoff_readiness_result_summary_valid(result)
            ):
                return False
    return True


def platform_smoke_execution_report_evidence_placeholders_match_reports(
    action_reports: list[dict[str, Any]],
    evidence_placeholders: list[dict[str, Any]],
) -> bool:
    by_id = {
        placeholder.get("source_action_report_id"): placeholder
        for placeholder in evidence_placeholders
    }
    if len(evidence_placeholders) != len(action_reports):
        return False
    for report in action_reports:
        placeholder = by_id.get(report.get("action_report_id"))
        if not isinstance(placeholder, dict):
            return False
        if placeholder.get("evidence_placeholder_id") != report.get("evidence_placeholder_id"):
            return False
        for key in ("owner", "route_kind", "source_plan_id", "source_plan_action_id"):
            if placeholder.get(key) != report.get(key):
                return False
        if placeholder.get("required_evidence_kind") != report.get("expected_output_kind"):
            return False
        if placeholder.get("evidence_status") != PENDING_STATUS:
            return False
        if placeholder.get("collected") is not False:
            return False
        if placeholder.get("attached") is not False:
            return False
        if placeholder.get("collection_started") is not False:
            return False
        if placeholder.get("requires_external_attachment") is not True:
            return False
        if not platform_smoke_execution_report_evidence_placeholder_unstarted(placeholder):
            return False
    return True


def platform_smoke_execution_report_action_report_schema_unstarted(
    report: dict[str, Any],
) -> bool:
    return (
        report.get("studio_execution_allowed") is False
        and report.get("schema_path_execution_allowed") is False
        and report.get("execution_started") is False
        and report.get("runtime_execution_performed") is False
        and report.get("platform_execution_performed") is False
        and report.get("real_platform_execution_evidence_attached") is False
        and report.get("command_session_started") is False
    )


def platform_smoke_execution_report_readiness_result_schema_unstarted(
    result: dict[str, Any],
) -> bool:
    return (
        result.get("studio_execution_allowed") is False
        and result.get("schema_path_execution_allowed") is False
        and result.get("execution_started") is False
        and result.get("runtime_execution_performed") is False
        and result.get("platform_execution_performed") is False
        and result.get("command_session_started") is False
    )


def platform_smoke_execution_report_evidence_placeholder_unstarted(
    placeholder: dict[str, Any],
) -> bool:
    return (
        placeholder.get("studio_execution_allowed") is False
        and placeholder.get("schema_path_execution_allowed") is False
        and placeholder.get("runtime_execution_performed") is False
        and placeholder.get("platform_execution_performed") is False
        and placeholder.get("command_session_started") is False
    )
