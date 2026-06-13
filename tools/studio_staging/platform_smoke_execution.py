"""Platform smoke execution request and receipt helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.smoke_workflow import *  # smoke review bundle helpers
from tools.studio_staging.platform_smoke_plan import *  # prior platform-smoke phase helpers

def build_platform_smoke_execution_request(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
) -> dict[str, Any]:
    approval_validation = validate_platform_smoke_approval_receipt(plan, approval_receipt)
    approval_receipts = platform_smoke_action_approval_receipt_dicts(approval_receipt)
    request_ready = (
        approval_receipt.get("status") == APPROVED_STATUS
        and approval_validation.get("status") == PASS_STATUS
        and approval_receipt.get("operator_approved") is True
        and approval_receipt.get("future_execution_authorized") is True
        and all(
            receipt.get("approval_status") == APPROVED_STATUS
            and receipt.get("future_execution_authorized") is True
            for receipt in approval_receipts
        )
    )
    status = READY_STATUS if request_ready else REJECTED_STATUS
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            approval_receipt.get("issue_code")
            or approval_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_request_not_authorized"
        )
    action_requests = platform_smoke_execution_action_requests(
        approval_receipt,
        approval_receipts,
        status,
        issue_code,
    )
    pending_actions = [
        action
        for action in action_requests
        if action.get("execution_request_status") == PENDING_STATUS
    ]
    rejected_actions = [
        action
        for action in action_requests
        if action.get("execution_request_status") == REJECTED_STATUS
    ]
    checks = platform_smoke_execution_request_checks(
        plan,
        approval_receipt,
        approval_validation,
        approval_receipts,
        action_requests,
        status,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == READY_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        action_requests = platform_smoke_execution_action_requests(
            approval_receipt,
            approval_receipts,
            status,
            issue_code,
        )
        pending_actions = []
        rejected_actions = action_requests

    approval_receipt_id = approval_receipt.get("approval_receipt_id")
    request_id = (
        f"hostess.platform_smoke_execution_request.{approval_receipt_id}"
        if isinstance(approval_receipt_id, str) and approval_receipt_id
        else "hostess.platform_smoke_execution_request.unknown"
    )

    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_REQUEST_SCHEMA,
        "execution_request_id": request_id,
        "source_approval_receipt_id": approval_receipt_id,
        "source_plan_id": approval_receipt.get("source_plan_id"),
        "source_bundle_id": approval_receipt.get("source_bundle_id"),
        "source_execution_id": approval_receipt.get("source_execution_id"),
        "source_request_id": approval_receipt.get("source_request_id"),
        "target_profile": approval_receipt.get("target_profile"),
        "target_platform": approval_receipt.get("target_platform"),
        "status": status,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EXECUTION_REQUEST_POLICY,
        "request_owner": HOSTESS_OWNER,
        "execution_owner": HOSTESS_OWNER,
        "approval_owner": approval_receipt.get("approval_owner"),
        "plan_owner": approval_receipt.get("plan_owner"),
        "platform_owner": approval_receipt.get("platform_owner"),
        "requester_role": approval_receipt.get("requester_role"),
        "command_session_authority": approval_receipt.get("command_session_authority"),
        "install_launch_evidence_authority": approval_receipt.get("install_launch_evidence_authority"),
        "studio_role": approval_receipt.get("studio_role"),
        "device_required": False,
        "target_device_required_for_future_execution": status == READY_STATUS,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "operator_approved": status == READY_STATUS,
        "future_execution_authorized": status == READY_STATUS,
        "operator_controlled_execution_required": True,
        "hostess_shell_execution_required": status == READY_STATUS,
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
        "source_approval_status": approval_receipt.get("status"),
        "source_approval_validation_status": approval_validation.get("status"),
        "source_approval_issue_code": (
            approval_receipt.get("issue_code") or approval_validation.get("issue_code")
        ),
        "source_action_approval_receipt_count": len(approval_receipts),
        "execution_action_request_count": len(action_requests),
        "pending_execution_action_count": len(pending_actions),
        "rejected_execution_action_count": len(rejected_actions),
        "source_action_approval_receipts": approval_receipts,
        "execution_action_requests": action_requests,
        "checks": checks,
        "next_required_action": (
            "hostess_t_or_dedicated_host_shell_consume_execution_request_outside_studio"
            if status == READY_STATUS
            else "repair_or_reject_platform_smoke_approval_receipt"
        ),
    }


def validate_platform_smoke_execution_request(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
) -> dict[str, Any]:
    approval_validation = validate_platform_smoke_approval_receipt(plan, approval_receipt)
    approval_receipts = platform_smoke_action_approval_receipt_dicts(approval_receipt)
    action_requests = platform_smoke_execution_action_request_dicts(execution_request)
    pending_actions = [
        action
        for action in action_requests
        if action.get("execution_request_status") == PENDING_STATUS
    ]
    rejected_actions = [
        action
        for action in action_requests
        if action.get("execution_request_status") == REJECTED_STATUS
    ]
    embedded_checks = execution_request.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.schema",
            execution_request.get("$schema") == PLATFORM_SMOKE_EXECUTION_REQUEST_SCHEMA,
            "platform smoke execution request schema is supported",
            "platform smoke execution request schema is unsupported",
            "hostess.issue.platform_smoke_execution_request_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.approval_id",
            execution_request.get("source_approval_receipt_id")
            == approval_receipt.get("approval_receipt_id"),
            "platform smoke execution request approval receipt id matches",
            "platform smoke execution request approval receipt id differs",
            "hostess.issue.platform_smoke_execution_request_approval_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.status",
            execution_request.get("status") in {READY_STATUS, REJECTED_STATUS},
            "platform smoke execution request status is supported",
            "platform smoke execution request status is unsupported",
            "hostess.issue.platform_smoke_execution_request_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.execution_policy",
            execution_request.get("execution_policy") == PLATFORM_SMOKE_EXECUTION_REQUEST_POLICY,
            "platform smoke execution request is request-only",
            "platform smoke execution request execution policy drifted",
            "hostess.issue.platform_smoke_execution_request_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.no_execution_started",
            all(execution_request.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and execution_request.get("runtime_execution_performed") is False
            and execution_request.get("platform_execution_performed") is False,
            "platform smoke execution request has not started runtime or platform work",
            "platform smoke execution request indicates runtime or platform work started",
            "hostess.issue.platform_smoke_execution_request_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.execution_gate",
            execution_request.get("schema_path_execution_allowed") is False
            and execution_request.get("platform_execution_allowed") is False
            and execution_request.get("studio_execution_allowed") is False
            and execution_request.get("device_required") is False,
            "platform smoke execution request keeps schema path and Studio execution disabled",
            "platform smoke execution request allows schema path, platform, device, or Studio execution",
            "hostess.issue.platform_smoke_execution_request_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.authority",
            execution_request.get("request_owner") == HOSTESS_OWNER
            and execution_request.get("execution_owner") == HOSTESS_OWNER
            and execution_request.get("approval_owner") == HOSTESS_OWNER
            and execution_request.get("plan_owner") == HOSTESS_OWNER
            and execution_request.get("platform_owner") == HOSTESS_OWNER
            and execution_request.get("requester_role") == STUDIO_REQUESTER
            and execution_request.get("command_session_authority") == MANIFOLD_OWNER
            and execution_request.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and execution_request.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.source_approval",
            execution_request.get("status") != READY_STATUS
            or (
                approval_receipt.get("status") == APPROVED_STATUS
                and approval_validation.get("status") == PASS_STATUS
                and approval_receipt.get("future_execution_authorized") is True
            ),
            "source approval receipt is approved and validates",
            "source approval receipt is rejected or invalid",
            approval_receipt.get("issue_code")
            or approval_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_request_not_authorized",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.action_requests",
            platform_smoke_execution_action_requests_match_approvals(
                approval_receipts,
                action_requests,
                execution_request.get("status"),
            ),
            "platform smoke execution action requests match approved actions",
            "platform smoke execution action requests drifted",
            "hostess.issue.platform_smoke_execution_request_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.counts",
            execution_request.get("source_action_approval_receipt_count") == len(approval_receipts)
            and execution_request.get("execution_action_request_count") == len(action_requests)
            and execution_request.get("pending_execution_action_count") == len(pending_actions)
            and execution_request.get("rejected_execution_action_count") == len(rejected_actions),
            "platform smoke execution request counts match action requests",
            "platform smoke execution request counts drifted",
            "hostess.issue.platform_smoke_execution_request_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.ready_consistency",
            execution_request.get("status") != READY_STATUS
            or (
                execution_request.get("operator_approved") is True
                and execution_request.get("future_execution_authorized") is True
                and execution_request.get("hostess_shell_execution_required") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(
                    action.get("execution_request_status") == PENDING_STATUS
                    and action.get("execution_requested") is True
                    and action.get("execution_started") is False
                    for action in action_requests
                )
            ),
            "ready platform smoke execution request carries pending action requests",
            "ready platform smoke execution request is inconsistent",
            "hostess.issue.platform_smoke_execution_request_ready_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.rejection_reason",
            execution_request.get("status") != REJECTED_STATUS
            or isinstance(execution_request.get("issue_code"), str),
            "rejected platform smoke execution request carries a reason code",
            "rejected platform smoke execution request is missing a reason code",
            "hostess.issue.platform_smoke_execution_request_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_REQUEST_VALIDATION_SCHEMA,
        "execution_request_id": execution_request.get("execution_request_id"),
        "source_approval_receipt_id": execution_request.get("source_approval_receipt_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def build_platform_smoke_execution_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
) -> dict[str, Any]:
    request_validation = validate_platform_smoke_execution_request(
        plan,
        approval_receipt,
        execution_request,
    )
    action_requests = platform_smoke_execution_action_request_dicts(execution_request)
    status = (
        PENDING_STATUS
        if execution_request.get("status") == READY_STATUS
        and request_validation.get("status") == PASS_STATUS
        else REJECTED_STATUS
    )
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            execution_request.get("issue_code")
            or request_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_receipt_rejected"
        )
    action_receipts = platform_smoke_execution_action_receipts(
        execution_request,
        action_requests,
        status,
        issue_code,
    )
    pending_receipts = [
        receipt
        for receipt in action_receipts
        if receipt.get("execution_receipt_status") == PENDING_STATUS
    ]
    rejected_receipts = [
        receipt
        for receipt in action_receipts
        if receipt.get("execution_receipt_status") == REJECTED_STATUS
    ]
    checks = platform_smoke_execution_receipt_checks(
        execution_request,
        request_validation,
        action_requests,
        action_receipts,
        status,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == PENDING_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        action_receipts = platform_smoke_execution_action_receipts(
            execution_request,
            action_requests,
            status,
            issue_code,
        )
        pending_receipts = []
        rejected_receipts = action_receipts

    execution_request_id = execution_request.get("execution_request_id")
    receipt_id = (
        f"hostess.platform_smoke_execution_receipt.{execution_request_id}"
        if isinstance(execution_request_id, str) and execution_request_id
        else "hostess.platform_smoke_execution_receipt.unknown"
    )

    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_RECEIPT_SCHEMA,
        "execution_receipt_id": receipt_id,
        "source_execution_request_id": execution_request_id,
        "source_approval_receipt_id": execution_request.get("source_approval_receipt_id"),
        "source_plan_id": execution_request.get("source_plan_id"),
        "source_bundle_id": execution_request.get("source_bundle_id"),
        "source_execution_id": execution_request.get("source_execution_id"),
        "source_request_id": execution_request.get("source_request_id"),
        "target_profile": execution_request.get("target_profile"),
        "target_platform": execution_request.get("target_platform"),
        "status": status,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EXECUTION_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "execution_owner": HOSTESS_OWNER,
        "request_owner": execution_request.get("request_owner"),
        "platform_owner": execution_request.get("platform_owner"),
        "requester_role": execution_request.get("requester_role"),
        "command_session_authority": execution_request.get("command_session_authority"),
        "install_launch_evidence_authority": execution_request.get("install_launch_evidence_authority"),
        "studio_role": execution_request.get("studio_role"),
        "device_required": False,
        "target_device_required_for_future_execution": status == PENDING_STATUS,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "operator_approved": status == PENDING_STATUS,
        "execution_acknowledged": status == PENDING_STATUS,
        "operator_controlled_execution_required": True,
        "hostess_shell_execution_required": status == PENDING_STATUS,
        "schema_checks_performed": True,
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
        "source_execution_request_status": execution_request.get("status"),
        "source_execution_request_validation_status": request_validation.get("status"),
        "source_execution_request_issue_code": (
            execution_request.get("issue_code") or request_validation.get("issue_code")
        ),
        "source_execution_action_request_count": len(action_requests),
        "execution_action_receipt_count": len(action_receipts),
        "pending_execution_action_count": len(pending_receipts),
        "rejected_execution_action_count": len(rejected_receipts),
        "source_execution_action_requests": action_requests,
        "execution_action_receipts": action_receipts,
        "checks": checks,
        "next_required_action": (
            "hostess_operator_start_platform_smoke_in_host_shell"
            if status == PENDING_STATUS
            else "repair_or_reject_platform_smoke_execution_request"
        ),
    }


def validate_platform_smoke_execution_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
) -> dict[str, Any]:
    request_validation = validate_platform_smoke_execution_request(
        plan,
        approval_receipt,
        execution_request,
    )
    action_requests = platform_smoke_execution_action_request_dicts(execution_request)
    action_receipts = platform_smoke_execution_action_receipt_dicts(execution_receipt)
    pending_receipts = [
        receipt
        for receipt in action_receipts
        if receipt.get("execution_receipt_status") == PENDING_STATUS
    ]
    rejected_receipts = [
        receipt
        for receipt in action_receipts
        if receipt.get("execution_receipt_status") == REJECTED_STATUS
    ]
    embedded_checks = execution_receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.schema",
            execution_receipt.get("$schema") == PLATFORM_SMOKE_EXECUTION_RECEIPT_SCHEMA,
            "platform smoke execution receipt schema is supported",
            "platform smoke execution receipt schema is unsupported",
            "hostess.issue.platform_smoke_execution_receipt_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.request_id",
            execution_receipt.get("source_execution_request_id")
            == execution_request.get("execution_request_id"),
            "platform smoke execution receipt request id matches",
            "platform smoke execution receipt request id differs",
            "hostess.issue.platform_smoke_execution_receipt_request_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.status",
            execution_receipt.get("status") in {PENDING_STATUS, REJECTED_STATUS},
            "platform smoke execution receipt status is supported",
            "platform smoke execution receipt status is unsupported",
            "hostess.issue.platform_smoke_execution_receipt_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.execution_policy",
            execution_receipt.get("execution_policy") == PLATFORM_SMOKE_EXECUTION_RECEIPT_POLICY,
            "platform smoke execution receipt is receipt-only",
            "platform smoke execution receipt execution policy drifted",
            "hostess.issue.platform_smoke_execution_receipt_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.no_execution_started",
            all(execution_receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and execution_receipt.get("runtime_execution_performed") is False
            and execution_receipt.get("platform_execution_performed") is False,
            "platform smoke execution receipt has not started runtime or platform work",
            "platform smoke execution receipt indicates runtime or platform work started",
            "hostess.issue.platform_smoke_execution_receipt_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.execution_gate",
            execution_receipt.get("schema_path_execution_allowed") is False
            and execution_receipt.get("platform_execution_allowed") is False
            and execution_receipt.get("studio_execution_allowed") is False
            and execution_receipt.get("device_required") is False,
            "platform smoke execution receipt keeps schema path and Studio execution disabled",
            "platform smoke execution receipt allows schema path, platform, device, or Studio execution",
            "hostess.issue.platform_smoke_execution_receipt_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.authority",
            execution_receipt.get("receipt_owner") == HOSTESS_OWNER
            and execution_receipt.get("execution_owner") == HOSTESS_OWNER
            and execution_receipt.get("request_owner") == HOSTESS_OWNER
            and execution_receipt.get("platform_owner") == HOSTESS_OWNER
            and execution_receipt.get("requester_role") == STUDIO_REQUESTER
            and execution_receipt.get("command_session_authority") == MANIFOLD_OWNER
            and execution_receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and execution_receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.source_request",
            execution_receipt.get("status") != PENDING_STATUS
            or (
                execution_request.get("status") == READY_STATUS
                and request_validation.get("status") == PASS_STATUS
            ),
            "source platform smoke execution request is ready and validates",
            "source platform smoke execution request is rejected or invalid",
            execution_request.get("issue_code")
            or request_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_receipt_request_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.action_receipts",
            platform_smoke_execution_action_receipts_match_requests(
                action_requests,
                action_receipts,
                execution_receipt.get("status"),
            ),
            "platform smoke execution action receipts match request actions",
            "platform smoke execution action receipts drifted",
            "hostess.issue.platform_smoke_execution_receipt_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.counts",
            execution_receipt.get("source_execution_action_request_count") == len(action_requests)
            and execution_receipt.get("execution_action_receipt_count") == len(action_receipts)
            and execution_receipt.get("pending_execution_action_count") == len(pending_receipts)
            and execution_receipt.get("rejected_execution_action_count") == len(rejected_receipts),
            "platform smoke execution receipt counts match action receipts",
            "platform smoke execution receipt counts drifted",
            "hostess.issue.platform_smoke_execution_receipt_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.pending_consistency",
            execution_receipt.get("status") != PENDING_STATUS
            or (
                execution_receipt.get("operator_approved") is True
                and execution_receipt.get("execution_acknowledged") is True
                and execution_receipt.get("hostess_shell_execution_required") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(
                    receipt.get("execution_receipt_status") == PENDING_STATUS
                    and receipt.get("execution_acknowledged") is True
                    and receipt.get("execution_started") is False
                    for receipt in action_receipts
                )
            ),
            "pending platform smoke execution receipt carries acknowledged pending action receipts",
            "pending platform smoke execution receipt is inconsistent",
            "hostess.issue.platform_smoke_execution_receipt_pending_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.rejection_reason",
            execution_receipt.get("status") != REJECTED_STATUS
            or isinstance(execution_receipt.get("issue_code"), str),
            "rejected platform smoke execution receipt carries a reason code",
            "rejected platform smoke execution receipt is missing a reason code",
            "hostess.issue.platform_smoke_execution_receipt_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_RECEIPT_VALIDATION_SCHEMA,
        "execution_receipt_id": execution_receipt.get("execution_receipt_id"),
        "source_execution_request_id": execution_receipt.get("source_execution_request_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def platform_smoke_execution_action_requests(
    approval_receipt: dict[str, Any],
    approval_receipts: list[dict[str, Any]],
    request_status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    action_status = PENDING_STATUS if request_status == READY_STATUS else REJECTED_STATUS
    requests = []
    for receipt in approval_receipts:
        source_receipt_id = receipt.get("action_approval_receipt_id")
        source_plan_action_id = receipt.get("source_plan_action_id")
        requests.append(
            {
                "action_request_id": (
                    f"hostess.platform_smoke_execution_action_request.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_execution_action_request.unknown"
                ),
                "source_approval_receipt_id": approval_receipt.get("approval_receipt_id"),
                "source_action_approval_receipt_id": source_receipt_id,
                "source_plan_id": receipt.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": receipt.get("owner"),
                "route_kind": receipt.get("route_kind"),
                "action_kind": receipt.get("action_kind"),
                "approval_kind": receipt.get("approval_kind"),
                "expected_input_kind": receipt.get("expected_input_kind"),
                "expected_output_kind": receipt.get("expected_output_kind"),
                "execution_request_status": action_status,
                "issue_code": None if action_status == PENDING_STATUS else issue_code,
                "operator_approved": action_status == PENDING_STATUS,
                "future_execution_authorized": action_status == PENDING_STATUS,
                "hostess_shell_execution_required": action_status == PENDING_STATUS,
                "execution_requested": action_status == PENDING_STATUS,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return requests


def platform_smoke_execution_request_checks(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    approval_validation: dict[str, Any],
    approval_receipts: list[dict[str, Any]],
    action_requests: list[dict[str, Any]],
    request_status: str,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.source_approval",
            approval_receipt.get("$schema") == PLATFORM_SMOKE_APPROVAL_RECEIPT_SCHEMA
            and approval_receipt.get("source_plan_id") == plan.get("plan_id")
            and approval_receipt.get("status") == APPROVED_STATUS
            and approval_validation.get("status") == PASS_STATUS,
            "platform smoke approval receipt is approved and validates",
            "platform smoke approval receipt is rejected or invalid",
            approval_receipt.get("issue_code")
            or approval_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_request_not_authorized",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.action_approvals",
            platform_smoke_action_approval_receipts_match_actions(
                platform_smoke_plan_action_dicts(plan),
                approval_receipts,
                APPROVED_STATUS,
            ),
            "platform smoke approval actions match planned actions",
            "platform smoke approval actions drifted",
            "hostess.issue.platform_smoke_execution_request_approval_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.action_requests",
            platform_smoke_execution_action_requests_match_approvals(
                approval_receipts,
                action_requests,
                request_status,
            ),
            "platform smoke execution requests match approved actions",
            "platform smoke execution requests drifted",
            "hostess.issue.platform_smoke_execution_request_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.no_action_execution",
            all(platform_smoke_execution_action_request_unstarted(action) for action in action_requests),
            "platform smoke execution action requests have not started execution",
            "platform smoke execution action request indicates execution started",
            "hostess.issue.platform_smoke_execution_request_action_started",
        ),
    ]


def platform_smoke_execution_action_request_dicts(
    execution_request: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = execution_request.get("execution_action_requests", [])
    if not isinstance(requests, list):
        return []
    return [item for item in requests if isinstance(item, dict)]


def platform_smoke_execution_action_requests_match_approvals(
    approval_receipts: list[dict[str, Any]],
    action_requests: list[dict[str, Any]],
    request_status: Any,
) -> bool:
    if request_status not in {READY_STATUS, REJECTED_STATUS}:
        return False
    expected_status = PENDING_STATUS if request_status == READY_STATUS else REJECTED_STATUS
    by_id = {
        request.get("source_action_approval_receipt_id"): request
        for request in action_requests
    }
    if len(action_requests) != len(approval_receipts):
        return False
    for receipt in approval_receipts:
        request = by_id.get(receipt.get("action_approval_receipt_id"))
        if not isinstance(request, dict):
            return False
        for key in (
            "owner",
            "route_kind",
            "action_kind",
            "approval_kind",
            "expected_input_kind",
            "expected_output_kind",
        ):
            if request.get(key) != receipt.get(key):
                return False
        if request.get("source_plan_action_id") != receipt.get("source_plan_action_id"):
            return False
        if request.get("execution_request_status") != expected_status:
            return False
        if request.get("operator_approved") != (expected_status == PENDING_STATUS):
            return False
        if request.get("future_execution_authorized") != (expected_status == PENDING_STATUS):
            return False
        if request.get("execution_requested") != (expected_status == PENDING_STATUS):
            return False
        if request.get("hostess_shell_execution_required") != (expected_status == PENDING_STATUS):
            return False
        if not platform_smoke_execution_action_request_unstarted(request):
            return False
    return True


def platform_smoke_execution_action_request_unstarted(action: dict[str, Any]) -> bool:
    return (
        action.get("execution_started") is False
        and action.get("runtime_execution_performed") is False
        and action.get("platform_execution_performed") is False
        and action.get("studio_execution_allowed") is False
        and action.get("command_session_started") is False
    )


def platform_smoke_execution_action_receipts(
    execution_request: dict[str, Any],
    action_requests: list[dict[str, Any]],
    receipt_status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    receipts = []
    for request in action_requests:
        source_request_id = request.get("action_request_id")
        source_plan_action_id = request.get("source_plan_action_id")
        receipts.append(
            {
                "action_execution_receipt_id": (
                    f"hostess.platform_smoke_execution_action_receipt.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_execution_action_receipt.unknown"
                ),
                "source_execution_request_id": execution_request.get("execution_request_id"),
                "source_action_request_id": source_request_id,
                "source_plan_id": request.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": request.get("owner"),
                "route_kind": request.get("route_kind"),
                "action_kind": request.get("action_kind"),
                "approval_kind": request.get("approval_kind"),
                "expected_input_kind": request.get("expected_input_kind"),
                "expected_output_kind": request.get("expected_output_kind"),
                "execution_receipt_status": receipt_status,
                "issue_code": None if receipt_status == PENDING_STATUS else issue_code,
                "operator_approved": receipt_status == PENDING_STATUS,
                "execution_acknowledged": receipt_status == PENDING_STATUS,
                "hostess_shell_execution_required": receipt_status == PENDING_STATUS,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return receipts


def platform_smoke_execution_receipt_checks(
    execution_request: dict[str, Any],
    request_validation: dict[str, Any],
    action_requests: list[dict[str, Any]],
    action_receipts: list[dict[str, Any]],
    receipt_status: str,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.source_request",
            execution_request.get("$schema") == PLATFORM_SMOKE_EXECUTION_REQUEST_SCHEMA
            and execution_request.get("status") == READY_STATUS
            and request_validation.get("status") == PASS_STATUS,
            "platform smoke execution request is ready and validates",
            "platform smoke execution request is rejected or invalid",
            execution_request.get("issue_code")
            or request_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_receipt_request_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.action_requests",
            all(
                action.get("execution_request_status") == PENDING_STATUS
                and platform_smoke_execution_action_request_unstarted(action)
                for action in action_requests
            ),
            "platform smoke execution action requests are pending and unstarted",
            "platform smoke execution action requests are rejected, drifted, or started",
            "hostess.issue.platform_smoke_execution_receipt_request_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.action_receipts",
            platform_smoke_execution_action_receipts_match_requests(
                action_requests,
                action_receipts,
                receipt_status,
            ),
            "platform smoke execution action receipts match source requests",
            "platform smoke execution action receipts drifted",
            "hostess.issue.platform_smoke_execution_receipt_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.no_action_execution",
            all(platform_smoke_execution_action_receipt_unstarted(receipt) for receipt in action_receipts),
            "platform smoke execution action receipts have not started execution",
            "platform smoke execution action receipt indicates execution started",
            "hostess.issue.platform_smoke_execution_receipt_action_started",
        ),
    ]


def platform_smoke_execution_action_receipt_dicts(
    execution_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    receipts = execution_receipt.get("execution_action_receipts", [])
    if not isinstance(receipts, list):
        return []
    return [item for item in receipts if isinstance(item, dict)]


def platform_smoke_execution_action_receipts_match_requests(
    action_requests: list[dict[str, Any]],
    action_receipts: list[dict[str, Any]],
    receipt_status: Any,
) -> bool:
    if receipt_status not in {PENDING_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        receipt.get("source_action_request_id"): receipt
        for receipt in action_receipts
    }
    if len(action_receipts) != len(action_requests):
        return False
    for request in action_requests:
        receipt = by_id.get(request.get("action_request_id"))
        if not isinstance(receipt, dict):
            return False
        for key in (
            "owner",
            "route_kind",
            "action_kind",
            "approval_kind",
            "expected_input_kind",
            "expected_output_kind",
        ):
            if receipt.get(key) != request.get(key):
                return False
        if receipt.get("source_plan_action_id") != request.get("source_plan_action_id"):
            return False
        if receipt.get("execution_receipt_status") != receipt_status:
            return False
        if receipt.get("operator_approved") != (receipt_status == PENDING_STATUS):
            return False
        if receipt.get("execution_acknowledged") != (receipt_status == PENDING_STATUS):
            return False
        if receipt.get("hostess_shell_execution_required") != (receipt_status == PENDING_STATUS):
            return False
        if not platform_smoke_execution_action_receipt_unstarted(receipt):
            return False
    return True


def platform_smoke_execution_action_receipt_unstarted(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("execution_started") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("command_session_started") is False
    )
