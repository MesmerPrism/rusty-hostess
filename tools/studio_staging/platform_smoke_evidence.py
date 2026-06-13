"""Platform smoke evidence attachment and review helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.smoke_workflow import *  # smoke review bundle helpers
from tools.studio_staging.platform_smoke_execution_report import *  # prior platform-smoke phase helpers

def build_platform_smoke_evidence_attachment_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    report_validation = validate_platform_smoke_execution_report(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
        execution_report,
    )
    action_reports = platform_smoke_execution_report_action_report_dicts(execution_report)
    readiness_results = platform_smoke_execution_report_readiness_result_dicts(
        execution_report
    )
    evidence_placeholders = platform_smoke_execution_report_evidence_placeholder_dicts(
        execution_report
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    report_ready = (
        execution_report.get("status") == COMPLETED_STATUS
        and report_validation.get("status") == PASS_STATUS
        and all(
            report.get("reported_status") == COMPLETED_STATUS
            and platform_smoke_execution_report_action_report_schema_unstarted(report)
            for report in action_reports
        )
        and all(
            result.get("result_status") == COMPLETED_STATUS
            and platform_smoke_execution_report_readiness_result_schema_unstarted(result)
            for result in readiness_results
        )
        and all(
            placeholder.get("evidence_status") == PENDING_STATUS
            and placeholder.get("collected") is False
            and placeholder.get("attached") is False
            and placeholder.get("collection_started") is False
            and platform_smoke_execution_report_evidence_placeholder_unstarted(placeholder)
            for placeholder in evidence_placeholders
        )
    )
    status = (
        VALIDATED_STATUS
        if decision == ACCEPTED_STATUS and report_ready
        else REJECTED_STATUS
    )
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or execution_report.get("issue_code")
            or report_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_attachment_rejected"
        )
    evidence_attachments = platform_smoke_evidence_attachments(
        execution_report,
        evidence_placeholders,
        status,
        issue_code,
    )
    readiness_attachments = platform_smoke_readiness_evidence_attachments(
        execution_report,
        readiness_results,
        status,
        issue_code,
    )
    validated_attachments = [
        item
        for item in evidence_attachments
        if item.get("attachment_status") == VALIDATED_STATUS
    ]
    rejected_attachments = [
        item
        for item in evidence_attachments
        if item.get("attachment_status") == REJECTED_STATUS
    ]
    validated_readiness = [
        item
        for item in readiness_attachments
        if item.get("attachment_status") == VALIDATED_STATUS
    ]
    rejected_readiness = [
        item
        for item in readiness_attachments
        if item.get("attachment_status") == REJECTED_STATUS
    ]
    checks = platform_smoke_evidence_attachment_receipt_checks(
        execution_report,
        report_validation,
        action_reports,
        readiness_results,
        evidence_placeholders,
        evidence_attachments,
        readiness_attachments,
        status,
        decision_supported,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == VALIDATED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        evidence_attachments = platform_smoke_evidence_attachments(
            execution_report,
            evidence_placeholders,
            status,
            issue_code,
        )
        readiness_attachments = platform_smoke_readiness_evidence_attachments(
            execution_report,
            readiness_results,
            status,
            issue_code,
        )
        validated_attachments = []
        rejected_attachments = evidence_attachments
        validated_readiness = []
        rejected_readiness = readiness_attachments

    report_id = execution_report.get("execution_report_id")
    receipt_id = (
        f"hostess.platform_smoke_evidence_attachment_receipt.{report_id}"
        if isinstance(report_id, str) and report_id
        else "hostess.platform_smoke_evidence_attachment_receipt.unknown"
    )
    pmb_review_required = execution_report.get("pmb_shell_handoff_review_required") is True
    pmb_review_ready = execution_report.get("pmb_shell_handoff_review_ready") is True

    return {
        "$schema": PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_SCHEMA,
        "evidence_attachment_receipt_id": receipt_id,
        "source_execution_report_id": report_id,
        "source_operator_start_preflight_receipt_id": execution_report.get(
            "source_operator_start_preflight_receipt_id"
        ),
        "source_operator_start_gate_id": execution_report.get("source_operator_start_gate_id"),
        "source_execution_receipt_id": execution_report.get("source_execution_receipt_id"),
        "source_execution_request_id": execution_report.get("source_execution_request_id"),
        "source_approval_receipt_id": execution_report.get("source_approval_receipt_id"),
        "source_plan_id": execution_report.get("source_plan_id"),
        "source_bundle_id": execution_report.get("source_bundle_id"),
        "source_execution_id": execution_report.get("source_execution_id"),
        "source_request_id": execution_report.get("source_request_id"),
        "target_profile": execution_report.get("target_profile"),
        "target_platform": execution_report.get("target_platform"),
        "host_shell_kind": execution_report.get("host_shell_kind"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "evidence_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": execution_report.get("host_shell_owner"),
        "platform_owner": execution_report.get("platform_owner"),
        "requester_role": execution_report.get("requester_role"),
        "command_session_authority": execution_report.get("command_session_authority"),
        "install_launch_evidence_authority": execution_report.get(
            "install_launch_evidence_authority"
        ),
        "studio_role": execution_report.get("studio_role"),
        "device_required": False,
        "external_evidence_required": True,
        "external_evidence_descriptors_supplied": status == VALIDATED_STATUS,
        "external_evidence_descriptors_attached": status == VALIDATED_STATUS,
        "all_placeholders_bound": status == VALIDATED_STATUS,
        "real_platform_execution_evidence_attached": False,
        "evidence_payloads_copied": False,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(execution_report),
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
        "source_execution_report_status": execution_report.get("status"),
        "source_execution_report_validation_status": report_validation.get("status"),
        "source_execution_report_issue_code": (
            execution_report.get("issue_code") or report_validation.get("issue_code")
        ),
        "source_action_report_count": len(action_reports),
        "source_readiness_result_count": len(readiness_results),
        "source_evidence_placeholder_count": len(evidence_placeholders),
        "evidence_attachment_count": len(evidence_attachments),
        "validated_evidence_attachment_count": len(validated_attachments),
        "rejected_evidence_attachment_count": len(rejected_attachments),
        "readiness_evidence_attachment_count": len(readiness_attachments),
        "validated_readiness_evidence_attachment_count": len(validated_readiness),
        "rejected_readiness_evidence_attachment_count": len(rejected_readiness),
        "source_action_reports": action_reports,
        "source_readiness_results": readiness_results,
        "source_evidence_placeholders": evidence_placeholders,
        "evidence_attachments": evidence_attachments,
        "readiness_evidence_attachments": readiness_attachments,
        "checks": checks,
        "next_required_action": (
            "hostess_review_attached_platform_smoke_evidence_outside_studio"
            if status == VALIDATED_STATUS
            else "repair_or_decline_platform_smoke_evidence_attachment"
        ),
    }


def validate_platform_smoke_evidence_attachment_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
    attachment_receipt: dict[str, Any],
) -> dict[str, Any]:
    report_validation = validate_platform_smoke_execution_report(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
        execution_report,
    )
    action_reports = platform_smoke_execution_report_action_report_dicts(execution_report)
    readiness_results = platform_smoke_execution_report_readiness_result_dicts(
        execution_report
    )
    evidence_placeholders = platform_smoke_execution_report_evidence_placeholder_dicts(
        execution_report
    )
    evidence_attachments = platform_smoke_evidence_attachment_dicts(attachment_receipt)
    readiness_attachments = platform_smoke_readiness_evidence_attachment_dicts(
        attachment_receipt
    )
    pmb_review_required = execution_report.get("pmb_shell_handoff_review_required") is True
    pmb_attachment = next(
        (
            item
            for item in readiness_attachments
            if item.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    pmb_summary_matches_report = (
        pmb_shell_handoff_review_summary_from_source(attachment_receipt)
        == pmb_shell_handoff_review_summary_from_source(execution_report)
    )
    validated_attachments = [
        item
        for item in evidence_attachments
        if item.get("attachment_status") == VALIDATED_STATUS
    ]
    rejected_attachments = [
        item
        for item in evidence_attachments
        if item.get("attachment_status") == REJECTED_STATUS
    ]
    validated_readiness = [
        item
        for item in readiness_attachments
        if item.get("attachment_status") == VALIDATED_STATUS
    ]
    rejected_readiness = [
        item
        for item in readiness_attachments
        if item.get("attachment_status") == REJECTED_STATUS
    ]
    embedded_checks = attachment_receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.schema",
            attachment_receipt.get("$schema") == PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_SCHEMA,
            "platform smoke evidence attachment receipt schema is supported",
            "platform smoke evidence attachment receipt schema is unsupported",
            "hostess.issue.platform_smoke_evidence_attachment_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.report_id",
            attachment_receipt.get("source_execution_report_id")
            == execution_report.get("execution_report_id"),
            "platform smoke evidence attachment report id matches",
            "platform smoke evidence attachment report id differs",
            "hostess.issue.platform_smoke_evidence_attachment_report_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.status",
            attachment_receipt.get("status") in {VALIDATED_STATUS, REJECTED_STATUS},
            "platform smoke evidence attachment status is supported",
            "platform smoke evidence attachment status is unsupported",
            "hostess.issue.platform_smoke_evidence_attachment_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.execution_policy",
            attachment_receipt.get("execution_policy")
            == PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_POLICY,
            "platform smoke evidence attachment is descriptor-only",
            "platform smoke evidence attachment execution policy drifted",
            "hostess.issue.platform_smoke_evidence_attachment_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.no_execution_started",
            all(attachment_receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and attachment_receipt.get("runtime_execution_performed") is False
            and attachment_receipt.get("platform_execution_performed") is False
            and attachment_receipt.get("schema_path_execution_allowed") is False
            and attachment_receipt.get("platform_execution_allowed") is False
            and attachment_receipt.get("studio_execution_allowed") is False
            and attachment_receipt.get("device_required") is False
            and attachment_receipt.get("evidence_payloads_copied") is False
            and attachment_receipt.get("real_platform_execution_evidence_attached") is False,
            "platform smoke evidence attachment has not started Studio, schema path, runtime, platform, or collection work",
            "platform smoke evidence attachment indicates execution, collection, or payload copying",
            "hostess.issue.platform_smoke_evidence_attachment_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.authority",
            attachment_receipt.get("receipt_owner") == HOSTESS_OWNER
            and attachment_receipt.get("evidence_owner") == HOSTESS_OWNER
            and attachment_receipt.get("operator_start_owner") == HOSTESS_OWNER
            and attachment_receipt.get("host_shell_owner") == HOSTESS_OWNER
            and attachment_receipt.get("platform_owner") == HOSTESS_OWNER
            and attachment_receipt.get("requester_role") == STUDIO_REQUESTER
            and attachment_receipt.get("command_session_authority") == MANIFOLD_OWNER
            and attachment_receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and attachment_receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.source_report",
            attachment_receipt.get("status") != VALIDATED_STATUS
            or (
                execution_report.get("status") == COMPLETED_STATUS
                and report_validation.get("status") == PASS_STATUS
            ),
            "source platform smoke execution report is completed and validates",
            "source platform smoke execution report is rejected or invalid",
            execution_report.get("issue_code")
            or report_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_attachment_report_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.placeholders",
            all(
                placeholder.get("evidence_status") == PENDING_STATUS
                and placeholder.get("collected") is False
                and placeholder.get("attached") is False
                and placeholder.get("collection_started") is False
                and platform_smoke_execution_report_evidence_placeholder_unstarted(placeholder)
                for placeholder in evidence_placeholders
            ),
            "source evidence placeholders are pending and uncollected",
            "source evidence placeholders already claim collection or attachment",
            "hostess.issue.platform_smoke_evidence_attachment_placeholder_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.attachments",
            platform_smoke_evidence_attachments_match_placeholders(
                evidence_placeholders,
                evidence_attachments,
                attachment_receipt.get("status"),
            ),
            "platform smoke evidence attachments match pending placeholders",
            "platform smoke evidence attachments drifted",
            "hostess.issue.platform_smoke_evidence_attachment_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.readiness",
            platform_smoke_readiness_evidence_attachments_match_results(
                readiness_results,
                readiness_attachments,
                attachment_receipt.get("status"),
            ),
            "platform smoke readiness evidence attachments match readiness results",
            "platform smoke readiness evidence attachments drifted",
            "hostess.issue.platform_smoke_evidence_attachment_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.pmb_shell_handoff_review",
            not pmb_review_required
            or attachment_receipt.get("status") != VALIDATED_STATUS
            or (
                attachment_receipt.get("pmb_shell_handoff_review_required") is True
                and attachment_receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_report
                and isinstance(pmb_attachment, dict)
                and pmb_attachment.get("attachment_status") == VALIDATED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_attachment)
            ),
            "validated platform smoke evidence attachment preserves the PMB shell handoff gate",
            "validated platform smoke evidence attachment dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_evidence_attachment_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.counts",
            attachment_receipt.get("source_action_report_count") == len(action_reports)
            and attachment_receipt.get("source_readiness_result_count") == len(readiness_results)
            and attachment_receipt.get("source_evidence_placeholder_count")
            == len(evidence_placeholders)
            and attachment_receipt.get("evidence_attachment_count") == len(evidence_attachments)
            and attachment_receipt.get("validated_evidence_attachment_count")
            == len(validated_attachments)
            and attachment_receipt.get("rejected_evidence_attachment_count")
            == len(rejected_attachments)
            and attachment_receipt.get("readiness_evidence_attachment_count")
            == len(readiness_attachments)
            and attachment_receipt.get("validated_readiness_evidence_attachment_count")
            == len(validated_readiness)
            and attachment_receipt.get("rejected_readiness_evidence_attachment_count")
            == len(rejected_readiness),
            "platform smoke evidence attachment counts match nested records",
            "platform smoke evidence attachment counts drifted",
            "hostess.issue.platform_smoke_evidence_attachment_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.validated_consistency",
            attachment_receipt.get("status") != VALIDATED_STATUS
            or (
                attachment_receipt.get("external_evidence_descriptors_supplied") is True
                and attachment_receipt.get("external_evidence_descriptors_attached") is True
                and attachment_receipt.get("all_placeholders_bound") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(
                    item.get("attachment_status") == VALIDATED_STATUS
                    for item in evidence_attachments
                )
                and all(
                    item.get("attachment_status") == VALIDATED_STATUS
                    for item in readiness_attachments
                )
            ),
            "validated platform smoke evidence attachment binds all descriptors without collecting payloads",
            "validated platform smoke evidence attachment is inconsistent",
            "hostess.issue.platform_smoke_evidence_attachment_validated_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.rejection_reason",
            attachment_receipt.get("status") != REJECTED_STATUS
            or isinstance(attachment_receipt.get("issue_code"), str),
            "rejected platform smoke evidence attachment carries a reason code",
            "rejected platform smoke evidence attachment is missing a reason code",
            "hostess.issue.platform_smoke_evidence_attachment_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_VALIDATION_SCHEMA,
        "evidence_attachment_receipt_id": attachment_receipt.get(
            "evidence_attachment_receipt_id"
        ),
        "source_execution_report_id": attachment_receipt.get("source_execution_report_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "real_platform_execution_evidence_attached": False,
        "pmb_shell_handoff_review_required": attachment_receipt.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": attachment_receipt.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def platform_smoke_evidence_attachment_receipt_checks(
    execution_report: dict[str, Any],
    report_validation: dict[str, Any],
    action_reports: list[dict[str, Any]],
    readiness_results: list[dict[str, Any]],
    evidence_placeholders: list[dict[str, Any]],
    evidence_attachments: list[dict[str, Any]],
    readiness_attachments: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = execution_report.get("pmb_shell_handoff_review_required") is True
    pmb_attachment = next(
        (
            item
            for item in readiness_attachments
            if item.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.source_report",
            execution_report.get("$schema") == PLATFORM_SMOKE_EXECUTION_REPORT_SCHEMA
            and execution_report.get("status") == COMPLETED_STATUS
            and report_validation.get("status") == PASS_STATUS,
            "platform smoke execution report is completed and validates",
            "platform smoke execution report is rejected or invalid",
            execution_report.get("issue_code")
            or report_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_attachment_report_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.decision",
            decision_supported,
            "platform smoke evidence attachment decision is supported",
            "platform smoke evidence attachment decision is unsupported",
            "hostess.issue.platform_smoke_evidence_attachment_decision",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.action_reports",
            all(
                report.get("reported_status") == COMPLETED_STATUS
                and platform_smoke_execution_report_action_report_schema_unstarted(report)
                for report in action_reports
            ),
            "platform smoke action reports are completed and descriptor-only",
            "platform smoke action reports are rejected, drifted, or started",
            "hostess.issue.platform_smoke_evidence_attachment_action_report_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.readiness_results",
            all(
                result.get("result_status") == COMPLETED_STATUS
                and platform_smoke_execution_report_readiness_result_schema_unstarted(result)
                for result in readiness_results
            ),
            "platform smoke readiness results are completed and descriptor-only",
            "platform smoke readiness results are rejected, drifted, or started",
            "hostess.issue.platform_smoke_evidence_attachment_readiness_result_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.placeholders",
            all(
                placeholder.get("evidence_status") == PENDING_STATUS
                and placeholder.get("collected") is False
                and placeholder.get("attached") is False
                and placeholder.get("collection_started") is False
                and platform_smoke_execution_report_evidence_placeholder_unstarted(placeholder)
                for placeholder in evidence_placeholders
            ),
            "platform smoke evidence placeholders are pending and uncollected",
            "platform smoke evidence placeholders drifted or already attached",
            "hostess.issue.platform_smoke_evidence_attachment_placeholder_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.attachments",
            platform_smoke_evidence_attachments_match_placeholders(
                evidence_placeholders,
                evidence_attachments,
                status,
            ),
            "platform smoke evidence attachments match source placeholders",
            "platform smoke evidence attachments drifted",
            "hostess.issue.platform_smoke_evidence_attachment_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.readiness",
            platform_smoke_readiness_evidence_attachments_match_results(
                readiness_results,
                readiness_attachments,
                status,
            ),
            "platform smoke readiness evidence attachments match source readiness results",
            "platform smoke readiness evidence attachments drifted",
            "hostess.issue.platform_smoke_evidence_attachment_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.pmb_shell_handoff_review",
            not pmb_review_required
            or status != VALIDATED_STATUS
            or (
                isinstance(pmb_attachment, dict)
                and pmb_attachment.get("attachment_status") == VALIDATED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_attachment)
            ),
            "validated platform smoke evidence attachment preserves the PMB shell handoff gate",
            "validated platform smoke evidence attachment dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_evidence_attachment_pmb_shell_handoff_review_drift",
        ),
    ]


def platform_smoke_evidence_attachments(
    execution_report: dict[str, Any],
    evidence_placeholders: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    attachment_status = VALIDATED_STATUS if status == VALIDATED_STATUS else REJECTED_STATUS
    attachments = []
    for placeholder in evidence_placeholders:
        source_plan_action_id = placeholder.get("source_plan_action_id")
        attachments.append(
            {
                "evidence_attachment_id": (
                    f"hostess.platform_smoke_evidence_attachment.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_evidence_attachment.unknown"
                ),
                "source_execution_report_id": execution_report.get("execution_report_id"),
                "source_evidence_placeholder_id": placeholder.get("evidence_placeholder_id"),
                "source_action_report_id": placeholder.get("source_action_report_id"),
                "source_plan_id": placeholder.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": placeholder.get("owner"),
                "route_kind": placeholder.get("route_kind"),
                "required_evidence_kind": placeholder.get("required_evidence_kind"),
                "external_evidence_kind": placeholder.get("required_evidence_kind"),
                "external_evidence_descriptor_id": (
                    f"external.hostess.platform_smoke_evidence_descriptor.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "external.hostess.platform_smoke_evidence_descriptor.unknown"
                ),
                "attachment_status": attachment_status,
                "issue_code": None if attachment_status == VALIDATED_STATUS else issue_code,
                "external_evidence_descriptor_supplied": attachment_status == VALIDATED_STATUS,
                "evidence_descriptor_attached": attachment_status == VALIDATED_STATUS,
                "placeholder_evidence_status": placeholder.get("evidence_status"),
                "requires_external_attachment": True,
                "evidence_payload_copied": False,
                "collection_started": False,
                "studio_execution_allowed": False,
                "schema_path_execution_allowed": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "real_platform_execution_evidence_attached": False,
                "command_session_started": False,
            }
        )
    return attachments


def platform_smoke_readiness_evidence_attachments(
    execution_report: dict[str, Any],
    readiness_results: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    attachment_status = VALIDATED_STATUS if status == VALIDATED_STATUS else REJECTED_STATUS
    attachments = []
    for result in readiness_results:
        source_result_id = result.get("readiness_result_id")
        attachment = {
            "readiness_evidence_attachment_id": (
                f"hostess.platform_smoke_readiness_evidence_attachment.{source_result_id}"
                if isinstance(source_result_id, str) and source_result_id
                else "hostess.platform_smoke_readiness_evidence_attachment.unknown"
            ),
            "source_execution_report_id": execution_report.get("execution_report_id"),
            "source_readiness_result_id": source_result_id,
            "source_readiness_input_id": result.get("source_readiness_input_id"),
            "owner": result.get("owner"),
            "input_kind": result.get("input_kind"),
            "expected_source_kind": result.get("expected_source_kind"),
            "validation_kind": result.get("validation_kind"),
            "external_readiness_descriptor_id": (
                f"external.hostess.platform_smoke_readiness_descriptor.{source_result_id}"
                if isinstance(source_result_id, str) and source_result_id
                else "external.hostess.platform_smoke_readiness_descriptor.unknown"
            ),
            "attachment_status": attachment_status,
            "issue_code": None if attachment_status == VALIDATED_STATUS else issue_code,
            "external_readiness_descriptor_supplied": attachment_status == VALIDATED_STATUS,
            "readiness_descriptor_attached": attachment_status == VALIDATED_STATUS,
            "validated_for_attachment": True,
            "validated_for_execution": False,
            "studio_execution_allowed": False,
            "schema_path_execution_allowed": False,
            "execution_started": False,
            "runtime_execution_performed": False,
            "platform_execution_performed": False,
            "command_session_started": False,
        }
        if result.get("source_readiness_input_id") == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID:
            attachment.update(pmb_shell_handoff_review_summary_from_source(result))
        attachments.append(attachment)
    return attachments


def platform_smoke_evidence_attachment_dicts(
    attachment_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    attachments = attachment_receipt.get("evidence_attachments", [])
    if not isinstance(attachments, list):
        return []
    return [item for item in attachments if isinstance(item, dict)]


def platform_smoke_readiness_evidence_attachment_dicts(
    attachment_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    attachments = attachment_receipt.get("readiness_evidence_attachments", [])
    if not isinstance(attachments, list):
        return []
    return [item for item in attachments if isinstance(item, dict)]


def platform_smoke_evidence_attachments_match_placeholders(
    evidence_placeholders: list[dict[str, Any]],
    evidence_attachments: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {VALIDATED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        attachment.get("source_evidence_placeholder_id"): attachment
        for attachment in evidence_attachments
    }
    if len(evidence_attachments) != len(evidence_placeholders):
        return False
    for placeholder in evidence_placeholders:
        attachment = by_id.get(placeholder.get("evidence_placeholder_id"))
        if not isinstance(attachment, dict):
            return False
        for key in ("owner", "route_kind", "source_plan_id", "source_plan_action_id"):
            if attachment.get(key) != placeholder.get(key):
                return False
        if attachment.get("source_action_report_id") != placeholder.get("source_action_report_id"):
            return False
        if attachment.get("required_evidence_kind") != placeholder.get("required_evidence_kind"):
            return False
        if attachment.get("external_evidence_kind") != placeholder.get("required_evidence_kind"):
            return False
        if attachment.get("placeholder_evidence_status") != PENDING_STATUS:
            return False
        if attachment.get("attachment_status") != status:
            return False
        if attachment.get("external_evidence_descriptor_supplied") != (status == VALIDATED_STATUS):
            return False
        if attachment.get("evidence_descriptor_attached") != (status == VALIDATED_STATUS):
            return False
        if attachment.get("requires_external_attachment") is not True:
            return False
        if not platform_smoke_evidence_attachment_unstarted(attachment):
            return False
    return True


def platform_smoke_readiness_evidence_attachments_match_results(
    readiness_results: list[dict[str, Any]],
    readiness_attachments: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {VALIDATED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        attachment.get("source_readiness_result_id"): attachment
        for attachment in readiness_attachments
    }
    if len(readiness_attachments) != len(readiness_results):
        return False
    for result in readiness_results:
        attachment = by_id.get(result.get("readiness_result_id"))
        if not isinstance(attachment, dict):
            return False
        for key in ("owner", "input_kind", "expected_source_kind", "validation_kind"):
            if attachment.get(key) != result.get(key):
                return False
        if attachment.get("source_readiness_input_id") != result.get("source_readiness_input_id"):
            return False
        if attachment.get("attachment_status") != status:
            return False
        if (
            status == VALIDATED_STATUS
            and result.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
            and (
                not pmb_shell_handoff_readiness_result_summary_valid(result)
                or not pmb_shell_handoff_readiness_result_summary_valid(attachment)
            )
        ):
            return False
        if attachment.get("external_readiness_descriptor_supplied") != (status == VALIDATED_STATUS):
            return False
        if attachment.get("readiness_descriptor_attached") != (status == VALIDATED_STATUS):
            return False
        if attachment.get("validated_for_attachment") is not True:
            return False
        if attachment.get("validated_for_execution") is not False:
            return False
        if not platform_smoke_readiness_evidence_attachment_unstarted(attachment):
            return False
    return True


def platform_smoke_evidence_attachment_unstarted(
    attachment: dict[str, Any],
) -> bool:
    return (
        attachment.get("evidence_payload_copied") is False
        and attachment.get("collection_started") is False
        and attachment.get("studio_execution_allowed") is False
        and attachment.get("schema_path_execution_allowed") is False
        and attachment.get("runtime_execution_performed") is False
        and attachment.get("platform_execution_performed") is False
        and attachment.get("real_platform_execution_evidence_attached") is False
        and attachment.get("command_session_started") is False
    )


def platform_smoke_readiness_evidence_attachment_unstarted(
    attachment: dict[str, Any],
) -> bool:
    return (
        attachment.get("studio_execution_allowed") is False
        and attachment.get("schema_path_execution_allowed") is False
        and attachment.get("execution_started") is False
        and attachment.get("runtime_execution_performed") is False
        and attachment.get("platform_execution_performed") is False
        and attachment.get("command_session_started") is False
    )


def build_platform_smoke_evidence_review(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
    attachment_receipt: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    attachment_validation = validate_platform_smoke_evidence_attachment_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
        execution_report,
        attachment_receipt,
    )
    evidence_attachments = platform_smoke_evidence_attachment_dicts(attachment_receipt)
    readiness_attachments = platform_smoke_readiness_evidence_attachment_dicts(
        attachment_receipt
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    source_validated = (
        attachment_receipt.get("status") == VALIDATED_STATUS
        and attachment_validation.get("status") == PASS_STATUS
        and attachment_receipt.get("external_evidence_descriptors_attached") is True
        and attachment_receipt.get("all_placeholders_bound") is True
        and all(
            attachment.get("attachment_status") == VALIDATED_STATUS
            and attachment.get("evidence_descriptor_attached") is True
            and platform_smoke_evidence_attachment_unstarted(attachment)
            for attachment in evidence_attachments
        )
        and all(
            attachment.get("attachment_status") == VALIDATED_STATUS
            and attachment.get("readiness_descriptor_attached") is True
            and platform_smoke_readiness_evidence_attachment_unstarted(attachment)
            for attachment in readiness_attachments
        )
    )
    status = (
        REVIEWED_STATUS
        if decision == ACCEPTED_STATUS and decision_supported and source_validated
        else REJECTED_STATUS
    )
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or attachment_receipt.get("issue_code")
            or attachment_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_review_rejected"
        )
    evidence_review_rows = platform_smoke_evidence_review_attachment_rows(
        attachment_receipt,
        evidence_attachments,
        status,
        issue_code,
    )
    readiness_review_rows = platform_smoke_evidence_review_readiness_rows(
        attachment_receipt,
        readiness_attachments,
        status,
        issue_code,
    )
    reviewed_evidence_rows = [
        row for row in evidence_review_rows if row.get("review_status") == REVIEWED_STATUS
    ]
    rejected_evidence_rows = [
        row for row in evidence_review_rows if row.get("review_status") == REJECTED_STATUS
    ]
    reviewed_readiness_rows = [
        row for row in readiness_review_rows if row.get("review_status") == REVIEWED_STATUS
    ]
    rejected_readiness_rows = [
        row for row in readiness_review_rows if row.get("review_status") == REJECTED_STATUS
    ]
    missing_attachment_count = sum(
        1 for row in evidence_review_rows if row.get("missing_attachment") is True
    ) + sum(1 for row in readiness_review_rows if row.get("missing_attachment") is True)
    rejected_attachment_count = len(rejected_evidence_rows) + len(rejected_readiness_rows)
    checks = platform_smoke_evidence_review_checks(
        attachment_receipt,
        attachment_validation,
        evidence_attachments,
        readiness_attachments,
        evidence_review_rows,
        readiness_review_rows,
        status,
        decision_supported,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == REVIEWED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        evidence_review_rows = platform_smoke_evidence_review_attachment_rows(
            attachment_receipt,
            evidence_attachments,
            status,
            issue_code,
        )
        readiness_review_rows = platform_smoke_evidence_review_readiness_rows(
            attachment_receipt,
            readiness_attachments,
            status,
            issue_code,
        )
        reviewed_evidence_rows = []
        rejected_evidence_rows = evidence_review_rows
        reviewed_readiness_rows = []
        rejected_readiness_rows = readiness_review_rows
        missing_attachment_count = sum(
            1 for row in evidence_review_rows if row.get("missing_attachment") is True
        ) + sum(1 for row in readiness_review_rows if row.get("missing_attachment") is True)
        rejected_attachment_count = len(rejected_evidence_rows) + len(
            rejected_readiness_rows
        )

    attachment_receipt_id = attachment_receipt.get("evidence_attachment_receipt_id")
    review_id = (
        f"hostess.platform_smoke_evidence_review.{attachment_receipt_id}"
        if isinstance(attachment_receipt_id, str) and attachment_receipt_id
        else "hostess.platform_smoke_evidence_review.unknown"
    )
    pmb_review_required = attachment_receipt.get("pmb_shell_handoff_review_required") is True
    pmb_review_ready = attachment_receipt.get("pmb_shell_handoff_review_ready") is True
    return {
        "$schema": PLATFORM_SMOKE_EVIDENCE_REVIEW_SCHEMA,
        "evidence_review_id": review_id,
        "source_evidence_attachment_receipt_id": attachment_receipt_id,
        "source_execution_report_id": attachment_receipt.get("source_execution_report_id"),
        "source_operator_start_preflight_receipt_id": attachment_receipt.get(
            "source_operator_start_preflight_receipt_id"
        ),
        "source_operator_start_gate_id": attachment_receipt.get("source_operator_start_gate_id"),
        "source_execution_receipt_id": attachment_receipt.get("source_execution_receipt_id"),
        "source_execution_request_id": attachment_receipt.get("source_execution_request_id"),
        "source_approval_receipt_id": attachment_receipt.get("source_approval_receipt_id"),
        "source_plan_id": attachment_receipt.get("source_plan_id"),
        "source_bundle_id": attachment_receipt.get("source_bundle_id"),
        "target_profile": attachment_receipt.get("target_profile"),
        "target_platform": attachment_receipt.get("target_platform"),
        "host_shell_kind": attachment_receipt.get("host_shell_kind"),
        "status": status,
        "review_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EVIDENCE_REVIEW_POLICY,
        "review_owner": HOSTESS_OWNER,
        "evidence_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": attachment_receipt.get("host_shell_owner"),
        "platform_owner": attachment_receipt.get("platform_owner"),
        "requester_role": attachment_receipt.get("requester_role"),
        "command_session_authority": attachment_receipt.get("command_session_authority"),
        "install_launch_evidence_authority": attachment_receipt.get(
            "install_launch_evidence_authority"
        ),
        "studio_role": attachment_receipt.get("studio_role"),
        "device_required": False,
        "operator_review_ready": status == REVIEWED_STATUS,
        "scorecard_status": PASS_STATUS if status == REVIEWED_STATUS else FAIL_STATUS,
        "external_evidence_required": True,
        "external_evidence_descriptors_attached": attachment_receipt.get(
            "external_evidence_descriptors_attached"
        )
        is True,
        "all_placeholders_bound": attachment_receipt.get("all_placeholders_bound") is True,
        "real_platform_execution_evidence_attached": False,
        "evidence_payloads_copied": False,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(attachment_receipt),
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
        "source_evidence_attachment_receipt_status": attachment_receipt.get("status"),
        "source_evidence_attachment_validation_status": attachment_validation.get("status"),
        "source_evidence_attachment_issue_code": (
            attachment_receipt.get("issue_code") or attachment_validation.get("issue_code")
        ),
        "source_evidence_attachment_count": len(evidence_attachments),
        "source_readiness_evidence_attachment_count": len(readiness_attachments),
        "evidence_review_row_count": len(evidence_review_rows),
        "reviewed_evidence_attachment_count": len(reviewed_evidence_rows),
        "rejected_evidence_attachment_count": len(rejected_evidence_rows),
        "readiness_review_row_count": len(readiness_review_rows),
        "reviewed_readiness_evidence_attachment_count": len(reviewed_readiness_rows),
        "rejected_readiness_evidence_attachment_count": len(rejected_readiness_rows),
        "missing_attachment_count": missing_attachment_count,
        "rejected_attachment_count": rejected_attachment_count,
        "source_evidence_attachments": evidence_attachments,
        "source_readiness_evidence_attachments": readiness_attachments,
        "evidence_review_rows": evidence_review_rows,
        "readiness_review_rows": readiness_review_rows,
        "checks": checks,
        "next_required_action": (
            "hostess_prepare_operator_release_bundle_outside_studio"
            if status == REVIEWED_STATUS
            else "repair_or_decline_platform_smoke_evidence_review"
        ),
    }


def validate_platform_smoke_evidence_review(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
    attachment_receipt: dict[str, Any],
    evidence_review: dict[str, Any],
) -> dict[str, Any]:
    attachment_validation = validate_platform_smoke_evidence_attachment_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
        execution_report,
        attachment_receipt,
    )
    evidence_attachments = platform_smoke_evidence_attachment_dicts(attachment_receipt)
    readiness_attachments = platform_smoke_readiness_evidence_attachment_dicts(
        attachment_receipt
    )
    evidence_review_rows = platform_smoke_evidence_review_row_dicts(evidence_review)
    readiness_review_rows = platform_smoke_evidence_review_readiness_row_dicts(
        evidence_review
    )
    pmb_review_required = attachment_receipt.get("pmb_shell_handoff_review_required") is True
    pmb_review_row = next(
        (
            row
            for row in readiness_review_rows
            if row.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    pmb_summary_matches_attachment = (
        pmb_shell_handoff_review_summary_from_source(evidence_review)
        == pmb_shell_handoff_review_summary_from_source(attachment_receipt)
    )
    reviewed_evidence_rows = [
        row for row in evidence_review_rows if row.get("review_status") == REVIEWED_STATUS
    ]
    rejected_evidence_rows = [
        row for row in evidence_review_rows if row.get("review_status") == REJECTED_STATUS
    ]
    reviewed_readiness_rows = [
        row for row in readiness_review_rows if row.get("review_status") == REVIEWED_STATUS
    ]
    rejected_readiness_rows = [
        row for row in readiness_review_rows if row.get("review_status") == REJECTED_STATUS
    ]
    missing_attachment_count = sum(
        1 for row in evidence_review_rows if row.get("missing_attachment") is True
    ) + sum(1 for row in readiness_review_rows if row.get("missing_attachment") is True)
    rejected_attachment_count = len(rejected_evidence_rows) + len(rejected_readiness_rows)
    embedded_checks = evidence_review.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.schema",
            evidence_review.get("$schema") == PLATFORM_SMOKE_EVIDENCE_REVIEW_SCHEMA,
            "platform smoke evidence review schema is supported",
            "platform smoke evidence review schema is unsupported",
            "hostess.issue.platform_smoke_evidence_review_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.attachment_receipt_id",
            evidence_review.get("source_evidence_attachment_receipt_id")
            == attachment_receipt.get("evidence_attachment_receipt_id"),
            "platform smoke evidence review source attachment receipt id matches",
            "platform smoke evidence review source attachment receipt id differs",
            "hostess.issue.platform_smoke_evidence_review_attachment_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.status",
            evidence_review.get("status") in {REVIEWED_STATUS, REJECTED_STATUS},
            "platform smoke evidence review status is supported",
            "platform smoke evidence review status is unsupported",
            "hostess.issue.platform_smoke_evidence_review_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.execution_policy",
            evidence_review.get("execution_policy") == PLATFORM_SMOKE_EVIDENCE_REVIEW_POLICY,
            "platform smoke evidence review is scorecard-only",
            "platform smoke evidence review execution policy drifted",
            "hostess.issue.platform_smoke_evidence_review_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.no_execution_started",
            all(evidence_review.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and evidence_review.get("runtime_execution_performed") is False
            and evidence_review.get("platform_execution_performed") is False
            and evidence_review.get("schema_path_execution_allowed") is False
            and evidence_review.get("platform_execution_allowed") is False
            and evidence_review.get("studio_execution_allowed") is False
            and evidence_review.get("device_required") is False
            and evidence_review.get("evidence_payloads_copied") is False
            and evidence_review.get("real_platform_execution_evidence_attached") is False,
            "platform smoke evidence review has not started Studio, schema path, runtime, platform, collection, or payload work",
            "platform smoke evidence review indicates execution, collection, or payload copying",
            "hostess.issue.platform_smoke_evidence_review_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.authority",
            evidence_review.get("review_owner") == HOSTESS_OWNER
            and evidence_review.get("evidence_owner") == HOSTESS_OWNER
            and evidence_review.get("operator_start_owner") == HOSTESS_OWNER
            and evidence_review.get("host_shell_owner") == HOSTESS_OWNER
            and evidence_review.get("platform_owner") == HOSTESS_OWNER
            and evidence_review.get("requester_role") == STUDIO_REQUESTER
            and evidence_review.get("command_session_authority") == MANIFOLD_OWNER
            and evidence_review.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and evidence_review.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.source_attachment",
            evidence_review.get("status") != REVIEWED_STATUS
            or (
                attachment_receipt.get("status") == VALIDATED_STATUS
                and attachment_validation.get("status") == PASS_STATUS
                and attachment_receipt.get("external_evidence_descriptors_attached") is True
                and attachment_receipt.get("all_placeholders_bound") is True
            ),
            "source platform smoke evidence attachment is validated",
            "source platform smoke evidence attachment is rejected, invalid, or incomplete",
            attachment_receipt.get("issue_code")
            or attachment_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_review_source_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.attachments",
            platform_smoke_evidence_review_rows_match_attachments(
                evidence_attachments,
                evidence_review_rows,
                evidence_review.get("status"),
            ),
            "platform smoke evidence review rows match source evidence attachments",
            "platform smoke evidence review rows drifted from source evidence attachments",
            "hostess.issue.platform_smoke_evidence_review_attachment_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.readiness",
            platform_smoke_evidence_review_readiness_rows_match_attachments(
                readiness_attachments,
                readiness_review_rows,
                evidence_review.get("status"),
            ),
            "platform smoke readiness review rows match source readiness attachments",
            "platform smoke readiness review rows drifted from source readiness attachments",
            "hostess.issue.platform_smoke_evidence_review_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.pmb_shell_handoff_review",
            not pmb_review_required
            or evidence_review.get("status") != REVIEWED_STATUS
            or (
                evidence_review.get("pmb_shell_handoff_review_required") is True
                and evidence_review.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_attachment
                and isinstance(pmb_review_row, dict)
                and pmb_review_row.get("review_status") == REVIEWED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_review_row)
            ),
            "reviewed platform smoke evidence preserves the PMB shell handoff gate",
            "reviewed platform smoke evidence dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_evidence_review_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.counts",
            evidence_review.get("source_evidence_attachment_count") == len(evidence_attachments)
            and evidence_review.get("source_readiness_evidence_attachment_count")
            == len(readiness_attachments)
            and evidence_review.get("evidence_review_row_count") == len(evidence_review_rows)
            and evidence_review.get("reviewed_evidence_attachment_count")
            == len(reviewed_evidence_rows)
            and evidence_review.get("rejected_evidence_attachment_count")
            == len(rejected_evidence_rows)
            and evidence_review.get("readiness_review_row_count") == len(readiness_review_rows)
            and evidence_review.get("reviewed_readiness_evidence_attachment_count")
            == len(reviewed_readiness_rows)
            and evidence_review.get("rejected_readiness_evidence_attachment_count")
            == len(rejected_readiness_rows)
            and evidence_review.get("missing_attachment_count") == missing_attachment_count
            and evidence_review.get("rejected_attachment_count") == rejected_attachment_count,
            "platform smoke evidence review counts match nested records",
            "platform smoke evidence review counts drifted",
            "hostess.issue.platform_smoke_evidence_review_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.scorecard",
            (
                evidence_review.get("status") == REVIEWED_STATUS
                and evidence_review.get("scorecard_status") == PASS_STATUS
                and evidence_review.get("operator_review_ready") is True
                and evidence_review.get("missing_attachment_count") == 0
                and evidence_review.get("rejected_attachment_count") == 0
            )
            or (
                evidence_review.get("status") == REJECTED_STATUS
                and evidence_review.get("scorecard_status") == FAIL_STATUS
                and evidence_review.get("operator_review_ready") is False
            ),
            "platform smoke evidence review scorecard matches review status",
            "platform smoke evidence review scorecard drifted",
            "hostess.issue.platform_smoke_evidence_review_scorecard_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.embedded_checks",
            all(check.get("status") == PASS_STATUS for check in embedded_check_dicts),
            "embedded platform smoke evidence review checks passed",
            "embedded platform smoke evidence review checks contain failures",
            "hostess.issue.platform_smoke_evidence_review_embedded_check_failed",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.rejection_reason",
            evidence_review.get("status") != REJECTED_STATUS
            or isinstance(evidence_review.get("issue_code"), str),
            "rejected platform smoke evidence review carries a reason code",
            "rejected platform smoke evidence review is missing a reason code",
            "hostess.issue.platform_smoke_evidence_review_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EVIDENCE_REVIEW_VALIDATION_SCHEMA,
        "evidence_review_id": evidence_review.get("evidence_review_id"),
        "source_evidence_attachment_receipt_id": evidence_review.get(
            "source_evidence_attachment_receipt_id"
        ),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "real_platform_execution_evidence_attached": False,
        "pmb_shell_handoff_review_required": evidence_review.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": evidence_review.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def platform_smoke_evidence_review_checks(
    attachment_receipt: dict[str, Any],
    attachment_validation: dict[str, Any],
    evidence_attachments: list[dict[str, Any]],
    readiness_attachments: list[dict[str, Any]],
    evidence_review_rows: list[dict[str, Any]],
    readiness_review_rows: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = attachment_receipt.get("pmb_shell_handoff_review_required") is True
    pmb_review_row = next(
        (
            row
            for row in readiness_review_rows
            if row.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.source_attachment",
            attachment_receipt.get("$schema") == PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_SCHEMA
            and attachment_receipt.get("status") == VALIDATED_STATUS
            and attachment_validation.get("status") == PASS_STATUS,
            "platform smoke evidence attachment receipt is validated",
            "platform smoke evidence attachment receipt is rejected or invalid",
            attachment_receipt.get("issue_code")
            or attachment_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_review_source_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.decision",
            decision_supported,
            "platform smoke evidence review decision is supported",
            "platform smoke evidence review decision is unsupported",
            "hostess.issue.platform_smoke_evidence_review_decision",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.source_descriptors",
            attachment_receipt.get("external_evidence_descriptors_attached") is True
            and attachment_receipt.get("all_placeholders_bound") is True
            and all(
                attachment.get("attachment_status") == VALIDATED_STATUS
                and attachment.get("evidence_descriptor_attached") is True
                and platform_smoke_evidence_attachment_unstarted(attachment)
                for attachment in evidence_attachments
            )
            and all(
                attachment.get("attachment_status") == VALIDATED_STATUS
                and attachment.get("readiness_descriptor_attached") is True
                and platform_smoke_readiness_evidence_attachment_unstarted(attachment)
                for attachment in readiness_attachments
            ),
            "platform smoke evidence descriptors are attached and unexecuted",
            "platform smoke evidence descriptors are missing, rejected, or started",
            "hostess.issue.platform_smoke_evidence_review_descriptor_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.attachments",
            platform_smoke_evidence_review_rows_match_attachments(
                evidence_attachments,
                evidence_review_rows,
                status,
            ),
            "platform smoke evidence review rows match source evidence attachments",
            "platform smoke evidence review rows drifted",
            "hostess.issue.platform_smoke_evidence_review_attachment_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.readiness",
            platform_smoke_evidence_review_readiness_rows_match_attachments(
                readiness_attachments,
                readiness_review_rows,
                status,
            ),
            "platform smoke readiness review rows match source readiness attachments",
            "platform smoke readiness review rows drifted",
            "hostess.issue.platform_smoke_evidence_review_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.pmb_shell_handoff_review",
            not pmb_review_required
            or status != REVIEWED_STATUS
            or (
                isinstance(pmb_review_row, dict)
                and pmb_review_row.get("review_status") == REVIEWED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_review_row)
            ),
            "reviewed platform smoke evidence preserves the PMB shell handoff gate",
            "reviewed platform smoke evidence dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_evidence_review_pmb_shell_handoff_review_drift",
        ),
    ]


def platform_smoke_evidence_review_attachment_rows(
    attachment_receipt: dict[str, Any],
    evidence_attachments: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    review_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    rows = []
    for attachment in evidence_attachments:
        source_attachment_id = attachment.get("evidence_attachment_id")
        descriptor_attached = attachment.get("evidence_descriptor_attached") is True
        rows.append(
            {
                "evidence_review_row_id": (
                    f"hostess.platform_smoke_evidence_review_row.{source_attachment_id}"
                    if isinstance(source_attachment_id, str) and source_attachment_id
                    else "hostess.platform_smoke_evidence_review_row.unknown"
                ),
                "source_evidence_attachment_receipt_id": attachment_receipt.get(
                    "evidence_attachment_receipt_id"
                ),
                "source_evidence_attachment_id": source_attachment_id,
                "source_evidence_placeholder_id": attachment.get(
                    "source_evidence_placeholder_id"
                ),
                "source_action_report_id": attachment.get("source_action_report_id"),
                "source_plan_id": attachment.get("source_plan_id"),
                "source_plan_action_id": attachment.get("source_plan_action_id"),
                "owner": attachment.get("owner"),
                "route_kind": attachment.get("route_kind"),
                "required_evidence_kind": attachment.get("required_evidence_kind"),
                "external_evidence_kind": attachment.get("external_evidence_kind"),
                "external_evidence_descriptor_id": attachment.get(
                    "external_evidence_descriptor_id"
                ),
                "source_attachment_status": attachment.get("attachment_status"),
                "review_status": review_status,
                "issue_code": None if review_status == REVIEWED_STATUS else issue_code,
                "external_evidence_descriptor_supplied": attachment.get(
                    "external_evidence_descriptor_supplied"
                ),
                "evidence_descriptor_attached": descriptor_attached,
                "missing_attachment": not descriptor_attached,
                "rejected_attachment": review_status == REJECTED_STATUS,
                "evidence_payload_copied": False,
                "collection_started": False,
                "studio_execution_allowed": False,
                "schema_path_execution_allowed": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "real_platform_execution_evidence_attached": False,
                "command_session_started": False,
            }
        )
    return rows


def platform_smoke_evidence_review_readiness_rows(
    attachment_receipt: dict[str, Any],
    readiness_attachments: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    review_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    rows = []
    for attachment in readiness_attachments:
        source_attachment_id = attachment.get("readiness_evidence_attachment_id")
        descriptor_attached = attachment.get("readiness_descriptor_attached") is True
        row = {
            "readiness_review_row_id": (
                f"hostess.platform_smoke_readiness_review_row.{source_attachment_id}"
                if isinstance(source_attachment_id, str) and source_attachment_id
                else "hostess.platform_smoke_readiness_review_row.unknown"
            ),
            "source_evidence_attachment_receipt_id": attachment_receipt.get(
                "evidence_attachment_receipt_id"
            ),
            "source_readiness_evidence_attachment_id": source_attachment_id,
            "source_readiness_result_id": attachment.get("source_readiness_result_id"),
            "source_readiness_input_id": attachment.get("source_readiness_input_id"),
            "owner": attachment.get("owner"),
            "input_kind": attachment.get("input_kind"),
            "expected_source_kind": attachment.get("expected_source_kind"),
            "validation_kind": attachment.get("validation_kind"),
            "external_readiness_descriptor_id": attachment.get(
                "external_readiness_descriptor_id"
            ),
            "source_attachment_status": attachment.get("attachment_status"),
            "review_status": review_status,
            "issue_code": None if review_status == REVIEWED_STATUS else issue_code,
            "external_readiness_descriptor_supplied": attachment.get(
                "external_readiness_descriptor_supplied"
            ),
            "readiness_descriptor_attached": descriptor_attached,
            "missing_attachment": not descriptor_attached,
            "rejected_attachment": review_status == REJECTED_STATUS,
            "validated_for_attachment": attachment.get("validated_for_attachment"),
            "validated_for_execution": False,
            "studio_execution_allowed": False,
            "schema_path_execution_allowed": False,
            "execution_started": False,
            "runtime_execution_performed": False,
            "platform_execution_performed": False,
            "command_session_started": False,
        }
        if attachment.get("source_readiness_input_id") == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID:
            row.update(pmb_shell_handoff_review_summary_from_source(attachment))
        rows.append(row)
    return rows


def platform_smoke_evidence_review_row_dicts(
    evidence_review: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = evidence_review.get("evidence_review_rows", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def platform_smoke_evidence_review_readiness_row_dicts(
    evidence_review: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = evidence_review.get("readiness_review_rows", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def platform_smoke_evidence_review_rows_match_attachments(
    evidence_attachments: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {REVIEWED_STATUS, REJECTED_STATUS}:
        return False
    expected_review_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    by_id = {
        row.get("source_evidence_attachment_id"): row
        for row in review_rows
    }
    if len(review_rows) != len(evidence_attachments):
        return False
    for attachment in evidence_attachments:
        row = by_id.get(attachment.get("evidence_attachment_id"))
        if not isinstance(row, dict):
            return False
        for key in (
            "source_evidence_placeholder_id",
            "source_action_report_id",
            "source_plan_id",
            "source_plan_action_id",
            "owner",
            "route_kind",
            "required_evidence_kind",
            "external_evidence_kind",
            "external_evidence_descriptor_id",
            "external_evidence_descriptor_supplied",
            "evidence_descriptor_attached",
        ):
            if row.get(key) != attachment.get(key):
                return False
        if row.get("source_attachment_status") != attachment.get("attachment_status"):
            return False
        if row.get("review_status") != expected_review_status:
            return False
        if row.get("missing_attachment") != (
            attachment.get("evidence_descriptor_attached") is not True
        ):
            return False
        if row.get("rejected_attachment") != (expected_review_status == REJECTED_STATUS):
            return False
        if not platform_smoke_evidence_review_row_unstarted(row):
            return False
    return True


def platform_smoke_evidence_review_readiness_rows_match_attachments(
    readiness_attachments: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {REVIEWED_STATUS, REJECTED_STATUS}:
        return False
    expected_review_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    by_id = {
        row.get("source_readiness_evidence_attachment_id"): row
        for row in review_rows
    }
    if len(review_rows) != len(readiness_attachments):
        return False
    for attachment in readiness_attachments:
        row = by_id.get(attachment.get("readiness_evidence_attachment_id"))
        if not isinstance(row, dict):
            return False
        for key in (
            "source_readiness_result_id",
            "source_readiness_input_id",
            "owner",
            "input_kind",
            "expected_source_kind",
            "validation_kind",
            "external_readiness_descriptor_id",
            "external_readiness_descriptor_supplied",
            "readiness_descriptor_attached",
            "validated_for_attachment",
        ):
            if row.get(key) != attachment.get(key):
                return False
        if row.get("source_attachment_status") != attachment.get("attachment_status"):
            return False
        if row.get("review_status") != expected_review_status:
            return False
        if (
            status == REVIEWED_STATUS
            and attachment.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
            and (
                not pmb_shell_handoff_readiness_result_summary_valid(attachment)
                or not pmb_shell_handoff_readiness_result_summary_valid(row)
            )
        ):
            return False
        if row.get("missing_attachment") != (
            attachment.get("readiness_descriptor_attached") is not True
        ):
            return False
        if row.get("rejected_attachment") != (expected_review_status == REJECTED_STATUS):
            return False
        if row.get("validated_for_execution") is not False:
            return False
        if not platform_smoke_evidence_review_readiness_row_unstarted(row):
            return False
    return True


def platform_smoke_evidence_review_row_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("evidence_payload_copied") is False
        and row.get("collection_started") is False
        and row.get("studio_execution_allowed") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("real_platform_execution_evidence_attached") is False
        and row.get("command_session_started") is False
    )


def platform_smoke_evidence_review_readiness_row_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("studio_execution_allowed") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("command_session_started") is False
    )
