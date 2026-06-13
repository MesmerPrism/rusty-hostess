"""Platform smoke plan and approval receipt helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.smoke_workflow import *  # smoke review bundle helpers

def build_platform_smoke_plan(
    bundle: dict[str, Any],
    target_platform: str = "hostess.platform_smoke.operator_controlled",
) -> dict[str, Any]:
    bundle_validation = validate_smoke_review_bundle(bundle)
    bundle_records = smoke_review_bundle_record_dicts(bundle)
    actions = platform_smoke_plan_actions(bundle, bundle_validation, bundle_records)
    approvals = platform_smoke_plan_approvals(actions)
    checks = platform_smoke_plan_checks(bundle, bundle_validation, bundle_records, actions)
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    bundle_id = bundle.get("bundle_id")
    plan_id = (
        f"hostess.platform_smoke_plan.{bundle_id}"
        if isinstance(bundle_id, str) and bundle_id
        else "hostess.platform_smoke_plan.unknown"
    )
    planned_actions = [action for action in actions if action.get("status") == PLANNED_STATUS]
    blocked_actions = [action for action in actions if action.get("status") == BLOCKED_STATUS]

    return {
        "$schema": PLATFORM_SMOKE_PLAN_SCHEMA,
        "plan_id": plan_id,
        "source_bundle_id": bundle_id,
        "source_execution_id": bundle.get("source_execution_id"),
        "preflight_id": bundle.get("preflight_id"),
        "dry_run_request_id": bundle.get("dry_run_request_id"),
        "dry_run_receipt_id": bundle.get("dry_run_receipt_id"),
        "smoke_handoff_id": bundle.get("smoke_handoff_id"),
        "source_request_id": bundle.get("source_request_id"),
        "target_profile": bundle.get("target_profile"),
        "target_platform": target_platform,
        "status": PLANNED_STATUS if not failed else BLOCKED_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_policy": PLATFORM_SMOKE_PLAN_POLICY,
        "plan_owner": HOSTESS_OWNER,
        "platform_owner": HOSTESS_OWNER,
        "bundle_owner": bundle.get("bundle_owner"),
        "reviewer_owner": bundle.get("reviewer_owner"),
        "requester_role": bundle.get("requester_role"),
        "command_session_authority": bundle.get("command_session_authority"),
        "install_launch_evidence_authority": bundle.get("install_launch_evidence_authority"),
        "studio_role": bundle.get("studio_role"),
        "host_shell_owner": bundle.get("host_shell_owner"),
        "device_required": False,
        "target_device_required_for_future_execution": True,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "operator_approval_required_before_execution": True,
        "operator_approved": False,
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
        "source_bundle_status": bundle.get("status"),
        "source_bundle_validation_status": bundle_validation.get("status"),
        "source_bundle_issue_code": bundle.get("issue_code") or bundle_validation.get("issue_code"),
        "source_bundle_record_count": len(bundle_records),
        "planned_action_count": len(actions),
        "ready_planned_action_count": len(planned_actions),
        "blocked_planned_action_count": len(blocked_actions),
        "required_approval_count": len(approvals),
        "operator_approved_count": 0,
        "source_bundle_records": bundle_records,
        "required_approvals": approvals,
        "planned_actions": actions,
        "checks": checks,
        "next_required_action": (
            "operator_approve_platform_smoke_plan_outside_studio"
            if not failed
            else "repair_hostess_smoke_review_bundle"
        ),
    }


def validate_platform_smoke_plan(plan: dict[str, Any]) -> dict[str, Any]:
    actions = platform_smoke_plan_action_dicts(plan)
    approvals = plan.get("required_approvals", [])
    if not isinstance(approvals, list):
        approvals = []
    approval_dicts = [approval for approval in approvals if isinstance(approval, dict)]
    source_records = plan.get("source_bundle_records", [])
    if not isinstance(source_records, list):
        source_records = []
    source_record_dicts = [record for record in source_records if isinstance(record, dict)]
    embedded_checks = plan.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    planned_actions = [action for action in actions if action.get("status") == PLANNED_STATUS]
    blocked_actions = [action for action in actions if action.get("status") == BLOCKED_STATUS]
    approved = [approval for approval in approval_dicts if approval.get("operator_approved") is True]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_plan.schema",
            plan.get("$schema") == PLATFORM_SMOKE_PLAN_SCHEMA,
            "platform smoke plan schema is supported",
            "platform smoke plan schema is unsupported",
            "hostess.issue.platform_smoke_plan_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.status",
            plan.get("status") in {PLANNED_STATUS, BLOCKED_STATUS},
            "platform smoke plan status is supported",
            "platform smoke plan status is unsupported",
            "hostess.issue.platform_smoke_plan_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.execution_policy",
            plan.get("execution_policy") == PLATFORM_SMOKE_PLAN_POLICY,
            "platform smoke plan is operator-controlled and plan-only",
            "platform smoke plan execution policy drifted",
            "hostess.issue.platform_smoke_plan_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.no_execution_started",
            all(plan.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and plan.get("runtime_execution_performed") is False
            and plan.get("platform_execution_performed") is False,
            "platform smoke plan has not started runtime or platform work",
            "platform smoke plan indicates runtime or platform work started",
            "hostess.issue.platform_smoke_plan_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.no_schema_path_execution",
            plan.get("device_required") is False
            and plan.get("schema_path_execution_allowed") is False
            and plan.get("platform_execution_allowed") is False
            and plan.get("studio_execution_allowed") is False,
            "platform smoke plan keeps schema path and Studio execution disabled",
            "platform smoke plan allows schema path, platform, or Studio execution",
            "hostess.issue.platform_smoke_plan_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.authority",
            plan.get("plan_owner") == HOSTESS_OWNER
            and plan.get("platform_owner") == HOSTESS_OWNER
            and plan.get("bundle_owner") == HOSTESS_OWNER
            and plan.get("reviewer_owner") == HOSTESS_OWNER
            and plan.get("requester_role") == STUDIO_REQUESTER
            and plan.get("command_session_authority") == MANIFOLD_OWNER
            and plan.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and plan.get("studio_role") == STUDIO_ROLE
            and plan.get("host_shell_owner") == HOSTESS_OWNER,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.source_bundle",
            plan.get("status") != PLANNED_STATUS
            or (
                plan.get("source_bundle_status") == REVIEWED_STATUS
                and plan.get("source_bundle_validation_status") == PASS_STATUS
            ),
            "planned source review bundle is reviewed and validates",
            "source review bundle is blocked or invalid",
            plan.get("source_bundle_issue_code") or "hostess.issue.smoke_review_bundle_not_reviewed",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.action_contracts",
            platform_smoke_plan_actions_match_contracts(actions),
            "platform smoke plan actions match Hostess and Manifold contracts",
            "platform smoke plan actions drifted",
            "hostess.issue.platform_smoke_plan_action_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.action_execution",
            all(platform_smoke_action_unstarted(action) for action in actions),
            "platform smoke plan actions have not started execution",
            "platform smoke plan action indicates execution started",
            "hostess.issue.platform_smoke_plan_action_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.approvals",
            platform_smoke_plan_approvals_match_actions(actions, approval_dicts),
            "platform smoke plan approvals match planned actions and are not approved yet",
            "platform smoke plan approvals drifted or were pre-approved",
            "hostess.issue.platform_smoke_plan_approval_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.counts",
            plan.get("source_bundle_record_count") == len(source_record_dicts)
            and plan.get("planned_action_count") == len(actions)
            and plan.get("ready_planned_action_count") == len(planned_actions)
            and plan.get("blocked_planned_action_count") == len(blocked_actions)
            and plan.get("required_approval_count") == len(approval_dicts)
            and plan.get("operator_approved_count") == len(approved),
            "platform smoke plan counts match actions and approvals",
            "platform smoke plan counts drifted",
            "hostess.issue.platform_smoke_plan_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.planned_consistency",
            plan.get("status") != PLANNED_STATUS
            or (
                all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(action.get("status") == PLANNED_STATUS for action in actions)
                and all(approval.get("operator_approved") is False for approval in approval_dicts)
            ),
            "planned platform smoke plan has passing checks, planned actions, and pending approvals",
            "planned platform smoke plan has failed checks, blocked actions, or approved actions",
            "hostess.issue.platform_smoke_plan_planned_inconsistent",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_PLAN_VALIDATION_SCHEMA,
        "plan_id": plan.get("plan_id"),
        "source_bundle_id": plan.get("source_bundle_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def platform_smoke_plan_actions(
    bundle: dict[str, Any],
    bundle_validation: dict[str, Any],
    bundle_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bundle_ready = (
        bundle.get("status") == REVIEWED_STATUS
        and bundle_validation.get("status") == PASS_STATUS
        and all(record.get("review_status") == REVIEWED_STATUS for record in bundle_records)
    )
    actions = []
    for contract in PLATFORM_SMOKE_PLAN_ACTION_CONTRACTS:
        issue_code = None
        if not bundle_ready:
            issue_code = (
                bundle.get("issue_code")
                or bundle_validation.get("issue_code")
                or first_bundle_record_issue_code(bundle_records)
                or "hostess.issue.smoke_review_bundle_not_reviewed"
            )
        actions.append(
            {
                "plan_action_id": contract["plan_action_id"],
                "owner": contract["owner"],
                "status": PLANNED_STATUS if issue_code is None else BLOCKED_STATUS,
                "issue_code": issue_code,
                "route_kind": contract["route_kind"],
                "action_kind": contract["action_kind"],
                "approval_kind": contract["approval_kind"],
                "expected_input_kind": contract["expected_input_kind"],
                "expected_output_kind": contract["expected_output_kind"],
                "approval_required": True,
                "operator_approved": False,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return actions


def platform_smoke_plan_checks(
    bundle: dict[str, Any],
    bundle_validation: dict[str, Any],
    bundle_records: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_plan.source_bundle",
            bundle.get("$schema") == SMOKE_REVIEW_BUNDLE_SCHEMA
            and bundle.get("status") == REVIEWED_STATUS
            and bundle_validation.get("status") == PASS_STATUS,
            "smoke review bundle is reviewed and validates",
            "smoke review bundle is blocked or invalid",
            bundle.get("issue_code")
            or bundle_validation.get("issue_code")
            or "hostess.issue.smoke_review_bundle_not_reviewed",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.authority",
            bundle.get("bundle_owner") == HOSTESS_OWNER
            and bundle.get("reviewer_owner") == HOSTESS_OWNER
            and bundle.get("requester_role") == STUDIO_REQUESTER
            and bundle.get("command_session_authority") == MANIFOLD_OWNER
            and bundle.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and bundle.get("studio_role") == STUDIO_ROLE
            and bundle.get("host_shell_owner") == HOSTESS_OWNER,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.no_runtime_started",
            all(bundle.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and bundle.get("runtime_execution_performed") is False
            and bundle.get("platform_execution_performed") is False,
            "smoke review bundle did not start runtime or platform work",
            "smoke review bundle indicates runtime or platform work started",
            "hostess.issue.platform_smoke_plan_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.bundle_records",
            all(record.get("review_status") == REVIEWED_STATUS for record in bundle_records),
            "source bundle records are reviewed",
            "source bundle records are blocked",
            first_bundle_record_issue_code(bundle_records)
            or "hostess.issue.smoke_review_bundle_records_blocked",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.action_contracts",
            platform_smoke_plan_actions_match_contracts(actions),
            "platform smoke plan actions match Hostess and Manifold contracts",
            "platform smoke plan actions drifted",
            "hostess.issue.platform_smoke_plan_action_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.no_action_execution",
            all(platform_smoke_action_unstarted(action) for action in actions),
            "platform smoke plan actions have not started execution",
            "platform smoke plan action indicates execution started",
            "hostess.issue.platform_smoke_plan_action_started",
        ),
    ]


def platform_smoke_plan_action_dicts(plan: dict[str, Any]) -> list[dict[str, Any]]:
    actions = plan.get("planned_actions", [])
    if not isinstance(actions, list):
        return []
    return [action for action in actions if isinstance(action, dict)]


def platform_smoke_plan_actions_match_contracts(actions: list[dict[str, Any]]) -> bool:
    by_id = {action.get("plan_action_id"): action for action in actions}
    if len(actions) != len(PLATFORM_SMOKE_PLAN_ACTION_CONTRACTS):
        return False
    for contract in PLATFORM_SMOKE_PLAN_ACTION_CONTRACTS:
        action = by_id.get(contract["plan_action_id"])
        if not isinstance(action, dict):
            return False
        for key in (
            "owner",
            "route_kind",
            "action_kind",
            "approval_kind",
            "expected_input_kind",
            "expected_output_kind",
        ):
            if action.get(key) != contract[key]:
                return False
        if action.get("approval_required") is not True:
            return False
    return True


def platform_smoke_action_unstarted(action: dict[str, Any]) -> bool:
    return (
        action.get("execution_started") is False
        and action.get("runtime_execution_performed") is False
        and action.get("platform_execution_performed") is False
        and action.get("studio_execution_allowed") is False
        and action.get("command_session_started") is False
    )


def platform_smoke_plan_approvals(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    approvals = []
    for action in actions:
        action_id = action.get("plan_action_id")
        approvals.append(
            {
                "approval_id": (
                    f"hostess.platform_smoke_approval.{action_id}"
                    if isinstance(action_id, str) and action_id
                    else "hostess.platform_smoke_approval.unknown"
                ),
                "source_plan_action_id": action_id,
                "owner": HOSTESS_OWNER,
                "approval_kind": action.get("approval_kind"),
                "approval_required": True,
                "operator_approved": False,
                "execution_allowed_after_approval": True,
                "execution_started": False,
            }
        )
    return approvals


def platform_smoke_plan_approvals_match_actions(
    actions: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
) -> bool:
    by_id = {approval.get("source_plan_action_id"): approval for approval in approvals}
    if len(approvals) != len(actions):
        return False
    for action in actions:
        approval = by_id.get(action.get("plan_action_id"))
        if not isinstance(approval, dict):
            return False
        if approval.get("owner") != HOSTESS_OWNER:
            return False
        if approval.get("approval_kind") != action.get("approval_kind"):
            return False
        if approval.get("approval_required") is not True:
            return False
        if approval.get("operator_approved") is not False:
            return False
        if approval.get("execution_started") is not False:
            return False
    return True


def build_platform_smoke_approval_receipt(
    plan: dict[str, Any],
    decision: str = APPROVED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    plan_validation = validate_platform_smoke_plan(plan)
    actions = platform_smoke_plan_action_dicts(plan)
    decision_supported = decision in {APPROVED_STATUS, REJECTED_STATUS}
    plan_ready = (
        plan.get("status") == PLANNED_STATUS
        and plan_validation.get("status") == PASS_STATUS
        and all(action.get("status") == PLANNED_STATUS for action in actions)
    )
    status = APPROVED_STATUS if decision == APPROVED_STATUS and plan_ready else REJECTED_STATUS
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or plan.get("issue_code")
            or plan_validation.get("issue_code")
            or "hostess.issue.platform_smoke_approval_rejected"
        )
    receipts = platform_smoke_action_approval_receipts(plan, actions, status, issue_code)
    approved_receipts = [
        receipt for receipt in receipts if receipt.get("approval_status") == APPROVED_STATUS
    ]
    rejected_receipts = [
        receipt for receipt in receipts if receipt.get("approval_status") == REJECTED_STATUS
    ]
    checks = platform_smoke_approval_receipt_checks(
        plan,
        plan_validation,
        actions,
        receipts,
        status,
        decision_supported,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == APPROVED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        receipts = platform_smoke_action_approval_receipts(plan, actions, status, issue_code)
        approved_receipts = []
        rejected_receipts = receipts

    plan_id = plan.get("plan_id")
    receipt_id = (
        f"hostess.platform_smoke_approval_receipt.{plan_id}"
        if isinstance(plan_id, str) and plan_id
        else "hostess.platform_smoke_approval_receipt.unknown"
    )

    return {
        "$schema": PLATFORM_SMOKE_APPROVAL_RECEIPT_SCHEMA,
        "approval_receipt_id": receipt_id,
        "source_plan_id": plan_id,
        "source_bundle_id": plan.get("source_bundle_id"),
        "source_execution_id": plan.get("source_execution_id"),
        "source_request_id": plan.get("source_request_id"),
        "target_profile": plan.get("target_profile"),
        "target_platform": plan.get("target_platform"),
        "status": status,
        "approval_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_APPROVAL_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "approval_owner": HOSTESS_OWNER,
        "plan_owner": plan.get("plan_owner"),
        "platform_owner": plan.get("platform_owner"),
        "requester_role": plan.get("requester_role"),
        "command_session_authority": plan.get("command_session_authority"),
        "install_launch_evidence_authority": plan.get("install_launch_evidence_authority"),
        "studio_role": plan.get("studio_role"),
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "operator_approved": status == APPROVED_STATUS,
        "future_execution_authorized": status == APPROVED_STATUS,
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
        "source_plan_status": plan.get("status"),
        "source_plan_validation_status": plan_validation.get("status"),
        "source_plan_issue_code": plan.get("issue_code") or plan_validation.get("issue_code"),
        "source_planned_action_count": len(actions),
        "approval_receipt_count": len(receipts),
        "approved_action_count": len(approved_receipts),
        "rejected_action_count": len(rejected_receipts),
        "source_planned_actions": actions,
        "action_approval_receipts": receipts,
        "checks": checks,
        "next_required_action": (
            "hostess_operator_start_platform_smoke_outside_studio"
            if status == APPROVED_STATUS
            else "repair_or_reject_platform_smoke_plan"
        ),
    }


def validate_platform_smoke_approval_receipt(
    plan: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    plan_validation = validate_platform_smoke_plan(plan)
    actions = platform_smoke_plan_action_dicts(plan)
    receipts = platform_smoke_action_approval_receipt_dicts(receipt)
    approved_receipts = [
        item for item in receipts if item.get("approval_status") == APPROVED_STATUS
    ]
    rejected_receipts = [
        item for item in receipts if item.get("approval_status") == REJECTED_STATUS
    ]
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.schema",
            receipt.get("$schema") == PLATFORM_SMOKE_APPROVAL_RECEIPT_SCHEMA,
            "platform smoke approval receipt schema is supported",
            "platform smoke approval receipt schema is unsupported",
            "hostess.issue.platform_smoke_approval_receipt_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.plan_id",
            receipt.get("source_plan_id") == plan.get("plan_id"),
            "platform smoke approval receipt plan id matches",
            "platform smoke approval receipt plan id differs",
            "hostess.issue.platform_smoke_approval_receipt_plan_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.status",
            receipt.get("status") in {APPROVED_STATUS, REJECTED_STATUS},
            "platform smoke approval receipt status is supported",
            "platform smoke approval receipt status is unsupported",
            "hostess.issue.platform_smoke_approval_receipt_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.execution_policy",
            receipt.get("execution_policy") == PLATFORM_SMOKE_APPROVAL_RECEIPT_POLICY,
            "platform smoke approval receipt is decision-only",
            "platform smoke approval receipt execution policy drifted",
            "hostess.issue.platform_smoke_approval_receipt_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.no_execution_started",
            all(receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and receipt.get("runtime_execution_performed") is False
            and receipt.get("platform_execution_performed") is False,
            "platform smoke approval receipt has not started runtime or platform work",
            "platform smoke approval receipt indicates runtime or platform work started",
            "hostess.issue.platform_smoke_approval_receipt_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.execution_gate",
            receipt.get("schema_path_execution_allowed") is False
            and receipt.get("platform_execution_allowed") is False
            and receipt.get("studio_execution_allowed") is False,
            "platform smoke approval receipt keeps schema path and Studio execution disabled",
            "platform smoke approval receipt allows schema path, platform, or Studio execution",
            "hostess.issue.platform_smoke_approval_receipt_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("approval_owner") == HOSTESS_OWNER
            and receipt.get("plan_owner") == HOSTESS_OWNER
            and receipt.get("platform_owner") == HOSTESS_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.source_plan",
            receipt.get("status") != APPROVED_STATUS
            or (
                plan.get("status") == PLANNED_STATUS
                and plan_validation.get("status") == PASS_STATUS
            ),
            "approved source platform smoke plan is planned and validates",
            "approved source platform smoke plan is blocked or invalid",
            plan.get("issue_code")
            or plan_validation.get("issue_code")
            or "hostess.issue.platform_smoke_plan_not_planned",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.action_receipts",
            platform_smoke_action_approval_receipts_match_actions(
                actions,
                receipts,
                receipt.get("status"),
            ),
            "platform smoke approval action receipts match planned actions",
            "platform smoke approval action receipts drifted",
            "hostess.issue.platform_smoke_approval_receipt_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.counts",
            receipt.get("source_planned_action_count") == len(actions)
            and receipt.get("approval_receipt_count") == len(receipts)
            and receipt.get("approved_action_count") == len(approved_receipts)
            and receipt.get("rejected_action_count") == len(rejected_receipts),
            "platform smoke approval receipt counts match actions",
            "platform smoke approval receipt counts drifted",
            "hostess.issue.platform_smoke_approval_receipt_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.decision_consistency",
            receipt.get("status") != APPROVED_STATUS
            or (
                receipt.get("operator_approved") is True
                and receipt.get("future_execution_authorized") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(item.get("approval_status") == APPROVED_STATUS for item in receipts)
            ),
            "approved platform smoke receipt carries approved action receipts",
            "approved platform smoke receipt is inconsistent",
            "hostess.issue.platform_smoke_approval_receipt_approved_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.rejection_reason",
            receipt.get("status") != REJECTED_STATUS
            or isinstance(receipt.get("issue_code"), str),
            "rejected platform smoke receipt carries a reason code",
            "rejected platform smoke receipt is missing a reason code",
            "hostess.issue.platform_smoke_approval_receipt_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_APPROVAL_RECEIPT_VALIDATION_SCHEMA,
        "approval_receipt_id": receipt.get("approval_receipt_id"),
        "source_plan_id": receipt.get("source_plan_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def platform_smoke_action_approval_receipts(
    plan: dict[str, Any],
    actions: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    receipts = []
    for action in actions:
        action_id = action.get("plan_action_id")
        receipts.append(
            {
                "action_approval_receipt_id": (
                    f"hostess.platform_smoke_action_approval_receipt.{action_id}"
                    if isinstance(action_id, str) and action_id
                    else "hostess.platform_smoke_action_approval_receipt.unknown"
                ),
                "source_plan_id": plan.get("plan_id"),
                "source_plan_action_id": action_id,
                "owner": action.get("owner"),
                "route_kind": action.get("route_kind"),
                "action_kind": action.get("action_kind"),
                "approval_kind": action.get("approval_kind"),
                "expected_input_kind": action.get("expected_input_kind"),
                "expected_output_kind": action.get("expected_output_kind"),
                "approval_status": status,
                "issue_code": None if status == APPROVED_STATUS else issue_code,
                "operator_approved": status == APPROVED_STATUS,
                "future_execution_authorized": status == APPROVED_STATUS,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return receipts


def platform_smoke_approval_receipt_checks(
    plan: dict[str, Any],
    plan_validation: dict[str, Any],
    actions: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.source_plan",
            plan.get("$schema") == PLATFORM_SMOKE_PLAN_SCHEMA
            and plan.get("status") == PLANNED_STATUS
            and plan_validation.get("status") == PASS_STATUS,
            "platform smoke plan is planned and validates",
            "platform smoke plan is blocked or invalid",
            plan.get("issue_code")
            or plan_validation.get("issue_code")
            or "hostess.issue.platform_smoke_plan_not_planned",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.decision",
            decision_supported,
            "platform smoke approval decision is supported",
            "platform smoke approval decision is unsupported",
            "hostess.issue.platform_smoke_approval_receipt_decision",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.action_contracts",
            platform_smoke_plan_actions_match_contracts(actions),
            "platform smoke approval source actions match contracts",
            "platform smoke approval source actions drifted",
            "hostess.issue.platform_smoke_plan_action_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.action_receipts",
            platform_smoke_action_approval_receipts_match_actions(actions, receipts, status),
            "platform smoke approval receipts match source actions",
            "platform smoke approval receipts drifted",
            "hostess.issue.platform_smoke_approval_receipt_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.no_action_execution",
            all(platform_smoke_approval_receipt_unstarted(receipt) for receipt in receipts),
            "platform smoke approval receipts have not started execution",
            "platform smoke approval receipt indicates execution started",
            "hostess.issue.platform_smoke_approval_receipt_action_started",
        ),
    ]


def platform_smoke_action_approval_receipt_dicts(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    receipts = receipt.get("action_approval_receipts", [])
    if not isinstance(receipts, list):
        return []
    return [item for item in receipts if isinstance(item, dict)]


def platform_smoke_action_approval_receipts_match_actions(
    actions: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {APPROVED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {receipt.get("source_plan_action_id"): receipt for receipt in receipts}
    if len(receipts) != len(actions):
        return False
    for action in actions:
        receipt = by_id.get(action.get("plan_action_id"))
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
            if receipt.get(key) != action.get(key):
                return False
        if receipt.get("approval_status") != status:
            return False
        if receipt.get("operator_approved") != (status == APPROVED_STATUS):
            return False
        if receipt.get("future_execution_authorized") != (status == APPROVED_STATUS):
            return False
        if not platform_smoke_approval_receipt_unstarted(receipt):
            return False
    return True


def platform_smoke_approval_receipt_unstarted(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("execution_started") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("command_session_started") is False
    )
