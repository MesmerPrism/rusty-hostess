"""Operator-controlled platform smoke receipts and validations."""

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


def build_platform_smoke_operator_start_gate(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    host_shell_kind: str = "hostess.t_or_dedicated_quest_host_shell",
) -> dict[str, Any]:
    receipt_validation = validate_platform_smoke_execution_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
    )
    action_receipts = platform_smoke_execution_action_receipt_dicts(execution_receipt)
    gate_ready = (
        execution_receipt.get("status") == PENDING_STATUS
        and receipt_validation.get("status") == PASS_STATUS
        and execution_receipt.get("execution_acknowledged") is True
        and execution_receipt.get("operator_approved") is True
        and execution_receipt.get("hostess_shell_execution_required") is True
        and all(
            receipt.get("execution_receipt_status") == PENDING_STATUS
            for receipt in action_receipts
        )
    )
    status = READY_STATUS if gate_ready else REJECTED_STATUS
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            execution_receipt.get("issue_code")
            or receipt_validation.get("issue_code")
            or "hostess.issue.platform_smoke_operator_start_gate_not_ready"
        )
    action_gates = platform_smoke_operator_start_action_gates(
        execution_receipt,
        action_receipts,
        status,
        issue_code,
    )
    pending_gates = [
        gate
        for gate in action_gates
        if gate.get("operator_start_gate_status") == PENDING_STATUS
    ]
    rejected_gates = [
        gate
        for gate in action_gates
        if gate.get("operator_start_gate_status") == REJECTED_STATUS
    ]

    execution_receipt_id = execution_receipt.get("execution_receipt_id")
    gate_id = (
        f"hostess.platform_smoke_operator_start_gate.{execution_receipt_id}"
        if isinstance(execution_receipt_id, str) and execution_receipt_id
        else "hostess.platform_smoke_operator_start_gate.unknown"
    )
    request_template = platform_smoke_operator_start_request_template(
        gate_id,
        execution_receipt,
        action_gates,
        status,
        host_shell_kind,
    )
    ack_template = platform_smoke_operator_start_ack_template(
        gate_id,
        execution_receipt,
        action_gates,
        status,
        host_shell_kind,
    )
    reject_template = platform_smoke_operator_start_reject_template(
        gate_id,
        execution_receipt,
        action_gates,
        status,
    )
    evidence_templates = platform_smoke_expected_evidence_receipt_templates(
        gate_id,
        action_gates,
        status,
    )
    checks = platform_smoke_operator_start_gate_checks(
        execution_receipt,
        receipt_validation,
        action_receipts,
        action_gates,
        request_template,
        ack_template,
        reject_template,
        evidence_templates,
        status,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == READY_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        action_gates = platform_smoke_operator_start_action_gates(
            execution_receipt,
            action_receipts,
            status,
            issue_code,
        )
        pending_gates = []
        rejected_gates = action_gates
        request_template = platform_smoke_operator_start_request_template(
            gate_id,
            execution_receipt,
            action_gates,
            status,
            host_shell_kind,
        )
        ack_template = platform_smoke_operator_start_ack_template(
            gate_id,
            execution_receipt,
            action_gates,
            status,
            host_shell_kind,
        )
        reject_template = platform_smoke_operator_start_reject_template(
            gate_id,
            execution_receipt,
            action_gates,
            status,
        )
        evidence_templates = platform_smoke_expected_evidence_receipt_templates(
            gate_id,
            action_gates,
            status,
        )

    return {
        "$schema": PLATFORM_SMOKE_OPERATOR_START_GATE_SCHEMA,
        "operator_start_gate_id": gate_id,
        "source_execution_receipt_id": execution_receipt_id,
        "source_execution_request_id": execution_receipt.get("source_execution_request_id"),
        "source_approval_receipt_id": execution_receipt.get("source_approval_receipt_id"),
        "source_plan_id": execution_receipt.get("source_plan_id"),
        "source_bundle_id": execution_receipt.get("source_bundle_id"),
        "source_execution_id": execution_receipt.get("source_execution_id"),
        "source_request_id": execution_receipt.get("source_request_id"),
        "target_profile": execution_receipt.get("target_profile"),
        "target_platform": execution_receipt.get("target_platform"),
        "host_shell_kind": host_shell_kind,
        "status": status,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_OPERATOR_START_GATE_POLICY,
        "gate_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": HOSTESS_OWNER,
        "platform_owner": execution_receipt.get("platform_owner"),
        "requester_role": execution_receipt.get("requester_role"),
        "command_session_authority": execution_receipt.get("command_session_authority"),
        "install_launch_evidence_authority": execution_receipt.get("install_launch_evidence_authority"),
        "studio_role": execution_receipt.get("studio_role"),
        "device_required": False,
        "target_device_required_for_future_execution": status == READY_STATUS,
        "operator_approval_required": True,
        "operator_start_required": status == READY_STATUS,
        "operator_started": False,
        "operator_start_acknowledged": False,
        "host_shell_started": False,
        "host_shell_execution_required": status == READY_STATUS,
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
        "source_execution_receipt_status": execution_receipt.get("status"),
        "source_execution_receipt_validation_status": receipt_validation.get("status"),
        "source_execution_receipt_issue_code": (
            execution_receipt.get("issue_code") or receipt_validation.get("issue_code")
        ),
        "source_execution_action_receipt_count": len(action_receipts),
        "operator_start_action_gate_count": len(action_gates),
        "pending_operator_start_action_count": len(pending_gates),
        "rejected_operator_start_action_count": len(rejected_gates),
        "source_execution_action_receipts": action_receipts,
        "operator_start_action_gates": action_gates,
        "operator_start_request_template": request_template,
        "operator_start_ack_template": ack_template,
        "operator_start_reject_template": reject_template,
        "expected_evidence_receipt_templates": evidence_templates,
        "checks": checks,
        "next_required_action": (
            "operator_start_hostess_host_shell_outside_studio"
            if status == READY_STATUS
            else "repair_or_reject_platform_smoke_execution_receipt"
        ),
    }


def validate_platform_smoke_operator_start_gate(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
) -> dict[str, Any]:
    receipt_validation = validate_platform_smoke_execution_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
    )
    action_receipts = platform_smoke_execution_action_receipt_dicts(execution_receipt)
    action_gates = platform_smoke_operator_start_action_gate_dicts(operator_start_gate)
    evidence_templates = platform_smoke_expected_evidence_receipt_template_dicts(
        operator_start_gate
    )
    request_template = operator_start_gate.get("operator_start_request_template")
    ack_template = operator_start_gate.get("operator_start_ack_template")
    reject_template = operator_start_gate.get("operator_start_reject_template")
    if not isinstance(request_template, dict):
        request_template = {}
    if not isinstance(ack_template, dict):
        ack_template = {}
    if not isinstance(reject_template, dict):
        reject_template = {}
    pending_gates = [
        gate
        for gate in action_gates
        if gate.get("operator_start_gate_status") == PENDING_STATUS
    ]
    rejected_gates = [
        gate
        for gate in action_gates
        if gate.get("operator_start_gate_status") == REJECTED_STATUS
    ]
    embedded_checks = operator_start_gate.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.schema",
            operator_start_gate.get("$schema") == PLATFORM_SMOKE_OPERATOR_START_GATE_SCHEMA,
            "platform smoke operator-start gate schema is supported",
            "platform smoke operator-start gate schema is unsupported",
            "hostess.issue.platform_smoke_operator_start_gate_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.receipt_id",
            operator_start_gate.get("source_execution_receipt_id")
            == execution_receipt.get("execution_receipt_id"),
            "platform smoke operator-start gate receipt id matches",
            "platform smoke operator-start gate receipt id differs",
            "hostess.issue.platform_smoke_operator_start_gate_receipt_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.status",
            operator_start_gate.get("status") in {READY_STATUS, REJECTED_STATUS},
            "platform smoke operator-start gate status is supported",
            "platform smoke operator-start gate status is unsupported",
            "hostess.issue.platform_smoke_operator_start_gate_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.execution_policy",
            operator_start_gate.get("execution_policy") == PLATFORM_SMOKE_OPERATOR_START_GATE_POLICY,
            "platform smoke operator-start gate is gate-only",
            "platform smoke operator-start gate execution policy drifted",
            "hostess.issue.platform_smoke_operator_start_gate_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.no_execution_started",
            all(operator_start_gate.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and operator_start_gate.get("runtime_execution_performed") is False
            and operator_start_gate.get("platform_execution_performed") is False
            and operator_start_gate.get("operator_started") is False
            and operator_start_gate.get("operator_start_acknowledged") is False
            and operator_start_gate.get("host_shell_started") is False,
            "platform smoke operator-start gate has not started runtime or platform work",
            "platform smoke operator-start gate indicates runtime, platform, or operator start",
            "hostess.issue.platform_smoke_operator_start_gate_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.execution_gate",
            operator_start_gate.get("schema_path_execution_allowed") is False
            and operator_start_gate.get("platform_execution_allowed") is False
            and operator_start_gate.get("studio_execution_allowed") is False
            and operator_start_gate.get("device_required") is False,
            "platform smoke operator-start gate keeps schema path and Studio execution disabled",
            "platform smoke operator-start gate allows schema path, platform, device, or Studio execution",
            "hostess.issue.platform_smoke_operator_start_gate_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.authority",
            operator_start_gate.get("gate_owner") == HOSTESS_OWNER
            and operator_start_gate.get("operator_start_owner") == HOSTESS_OWNER
            and operator_start_gate.get("host_shell_owner") == HOSTESS_OWNER
            and operator_start_gate.get("platform_owner") == HOSTESS_OWNER
            and operator_start_gate.get("requester_role") == STUDIO_REQUESTER
            and operator_start_gate.get("command_session_authority") == MANIFOLD_OWNER
            and operator_start_gate.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and operator_start_gate.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.source_receipt",
            operator_start_gate.get("status") != READY_STATUS
            or (
                execution_receipt.get("status") == PENDING_STATUS
                and receipt_validation.get("status") == PASS_STATUS
                and execution_receipt.get("execution_acknowledged") is True
            ),
            "source platform smoke execution receipt is pending and validates",
            "source platform smoke execution receipt is rejected or invalid",
            execution_receipt.get("issue_code")
            or receipt_validation.get("issue_code")
            or "hostess.issue.platform_smoke_operator_start_gate_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.action_gates",
            platform_smoke_operator_start_action_gates_match_receipts(
                action_receipts,
                action_gates,
                operator_start_gate.get("status"),
            ),
            "platform smoke operator-start action gates match execution receipts",
            "platform smoke operator-start action gates drifted",
            "hostess.issue.platform_smoke_operator_start_gate_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.templates",
            platform_smoke_operator_start_templates_match_gate(
                operator_start_gate,
                action_gates,
                request_template,
                ack_template,
                reject_template,
                evidence_templates,
            ),
            "platform smoke operator-start request, ack, reject, and evidence templates match the gate",
            "platform smoke operator-start templates drifted",
            "hostess.issue.platform_smoke_operator_start_gate_template_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.counts",
            operator_start_gate.get("source_execution_action_receipt_count") == len(action_receipts)
            and operator_start_gate.get("operator_start_action_gate_count") == len(action_gates)
            and operator_start_gate.get("pending_operator_start_action_count") == len(pending_gates)
            and operator_start_gate.get("rejected_operator_start_action_count") == len(rejected_gates)
            and len(evidence_templates) == len(action_gates),
            "platform smoke operator-start gate counts match action gates and evidence templates",
            "platform smoke operator-start gate counts drifted",
            "hostess.issue.platform_smoke_operator_start_gate_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.ready_consistency",
            operator_start_gate.get("status") != READY_STATUS
            or (
                operator_start_gate.get("operator_start_required") is True
                and operator_start_gate.get("host_shell_execution_required") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(
                    gate.get("operator_start_gate_status") == PENDING_STATUS
                    and gate.get("operator_start_required") is True
                    and gate.get("operator_started") is False
                    for gate in action_gates
                )
            ),
            "ready platform smoke operator-start gate carries pending unstarted action gates",
            "ready platform smoke operator-start gate is inconsistent",
            "hostess.issue.platform_smoke_operator_start_gate_ready_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.rejection_reason",
            operator_start_gate.get("status") != REJECTED_STATUS
            or isinstance(operator_start_gate.get("issue_code"), str),
            "rejected platform smoke operator-start gate carries a reason code",
            "rejected platform smoke operator-start gate is missing a reason code",
            "hostess.issue.platform_smoke_operator_start_gate_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_OPERATOR_START_GATE_VALIDATION_SCHEMA,
        "operator_start_gate_id": operator_start_gate.get("operator_start_gate_id"),
        "source_execution_receipt_id": operator_start_gate.get("source_execution_receipt_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def platform_smoke_operator_start_action_gates(
    execution_receipt: dict[str, Any],
    action_receipts: list[dict[str, Any]],
    gate_status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    action_status = PENDING_STATUS if gate_status == READY_STATUS else REJECTED_STATUS
    gates = []
    for receipt in action_receipts:
        source_receipt_id = receipt.get("action_execution_receipt_id")
        source_plan_action_id = receipt.get("source_plan_action_id")
        gates.append(
            {
                "action_gate_id": (
                    f"hostess.platform_smoke_operator_start_action_gate.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_operator_start_action_gate.unknown"
                ),
                "source_execution_receipt_id": execution_receipt.get("execution_receipt_id"),
                "source_action_execution_receipt_id": source_receipt_id,
                "source_plan_id": receipt.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": receipt.get("owner"),
                "route_kind": receipt.get("route_kind"),
                "action_kind": receipt.get("action_kind"),
                "approval_kind": receipt.get("approval_kind"),
                "expected_input_kind": receipt.get("expected_input_kind"),
                "expected_output_kind": receipt.get("expected_output_kind"),
                "operator_start_gate_status": action_status,
                "issue_code": None if action_status == PENDING_STATUS else issue_code,
                "operator_start_required": action_status == PENDING_STATUS,
                "operator_started": False,
                "operator_start_acknowledged": False,
                "host_shell_execution_required": action_status == PENDING_STATUS,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return gates


def platform_smoke_operator_start_gate_checks(
    execution_receipt: dict[str, Any],
    receipt_validation: dict[str, Any],
    action_receipts: list[dict[str, Any]],
    action_gates: list[dict[str, Any]],
    request_template: dict[str, Any],
    ack_template: dict[str, Any],
    reject_template: dict[str, Any],
    evidence_templates: list[dict[str, Any]],
    gate_status: str,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.source_receipt",
            execution_receipt.get("$schema") == PLATFORM_SMOKE_EXECUTION_RECEIPT_SCHEMA
            and execution_receipt.get("status") == PENDING_STATUS
            and receipt_validation.get("status") == PASS_STATUS,
            "platform smoke execution receipt is pending and validates",
            "platform smoke execution receipt is rejected or invalid",
            execution_receipt.get("issue_code")
            or receipt_validation.get("issue_code")
            or "hostess.issue.platform_smoke_operator_start_gate_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.action_receipts",
            all(
                receipt.get("execution_receipt_status") == PENDING_STATUS
                and platform_smoke_execution_action_receipt_unstarted(receipt)
                for receipt in action_receipts
            ),
            "platform smoke execution action receipts are pending and unstarted",
            "platform smoke execution action receipts are rejected, drifted, or started",
            "hostess.issue.platform_smoke_operator_start_gate_receipt_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.action_gates",
            platform_smoke_operator_start_action_gates_match_receipts(
                action_receipts,
                action_gates,
                gate_status,
            ),
            "platform smoke operator-start action gates match source receipts",
            "platform smoke operator-start action gates drifted",
            "hostess.issue.platform_smoke_operator_start_gate_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.no_action_execution",
            all(platform_smoke_operator_start_action_gate_unstarted(gate) for gate in action_gates),
            "platform smoke operator-start action gates have not started execution",
            "platform smoke operator-start action gate indicates execution started",
            "hostess.issue.platform_smoke_operator_start_gate_action_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_gate.templates",
            platform_smoke_operator_start_templates_core_valid(
                action_gates,
                request_template,
                ack_template,
                reject_template,
                evidence_templates,
                gate_status,
            ),
            "platform smoke operator-start request, ack, reject, and evidence templates are pending and unstarted",
            "platform smoke operator-start templates drifted",
            "hostess.issue.platform_smoke_operator_start_gate_template_drift",
        ),
    ]


def platform_smoke_operator_start_action_gate_dicts(
    operator_start_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    gates = operator_start_gate.get("operator_start_action_gates", [])
    if not isinstance(gates, list):
        return []
    return [item for item in gates if isinstance(item, dict)]


def platform_smoke_operator_start_action_gates_match_receipts(
    action_receipts: list[dict[str, Any]],
    action_gates: list[dict[str, Any]],
    gate_status: Any,
) -> bool:
    if gate_status not in {READY_STATUS, REJECTED_STATUS}:
        return False
    expected_status = PENDING_STATUS if gate_status == READY_STATUS else REJECTED_STATUS
    by_id = {
        gate.get("source_action_execution_receipt_id"): gate
        for gate in action_gates
    }
    if len(action_gates) != len(action_receipts):
        return False
    for receipt in action_receipts:
        gate = by_id.get(receipt.get("action_execution_receipt_id"))
        if not isinstance(gate, dict):
            return False
        for key in (
            "owner",
            "route_kind",
            "action_kind",
            "approval_kind",
            "expected_input_kind",
            "expected_output_kind",
        ):
            if gate.get(key) != receipt.get(key):
                return False
        if gate.get("source_plan_action_id") != receipt.get("source_plan_action_id"):
            return False
        if gate.get("operator_start_gate_status") != expected_status:
            return False
        if gate.get("operator_start_required") != (expected_status == PENDING_STATUS):
            return False
        if gate.get("host_shell_execution_required") != (expected_status == PENDING_STATUS):
            return False
        if not platform_smoke_operator_start_action_gate_unstarted(gate):
            return False
    return True


def platform_smoke_operator_start_action_gate_unstarted(gate: dict[str, Any]) -> bool:
    return (
        gate.get("operator_started") is False
        and gate.get("operator_start_acknowledged") is False
        and gate.get("execution_started") is False
        and gate.get("runtime_execution_performed") is False
        and gate.get("platform_execution_performed") is False
        and gate.get("studio_execution_allowed") is False
        and gate.get("command_session_started") is False
    )


def platform_smoke_operator_start_request_template(
    gate_id: str,
    execution_receipt: dict[str, Any],
    action_gates: list[dict[str, Any]],
    gate_status: str,
    host_shell_kind: str,
) -> dict[str, Any]:
    template_status = PENDING_STATUS if gate_status == READY_STATUS else REJECTED_STATUS
    return {
        "$schema": OPERATOR_START_REQUEST_TEMPLATE_SCHEMA,
        "template_status": template_status,
        "source_operator_start_gate_id": gate_id,
        "source_execution_receipt_id": execution_receipt.get("execution_receipt_id"),
        "request_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": HOSTESS_OWNER,
        "host_shell_kind": host_shell_kind,
        "command_session_authority": execution_receipt.get("command_session_authority"),
        "install_launch_evidence_authority": execution_receipt.get("install_launch_evidence_authority"),
        "operator_start_required": gate_status == READY_STATUS,
        "operator_started": False,
        "operator_start_acknowledged": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "action_gate_ids": [gate.get("action_gate_id") for gate in action_gates],
    }


def platform_smoke_operator_start_ack_template(
    gate_id: str,
    execution_receipt: dict[str, Any],
    action_gates: list[dict[str, Any]],
    gate_status: str,
    host_shell_kind: str,
) -> dict[str, Any]:
    ack_status = PENDING_STATUS if gate_status == READY_STATUS else REJECTED_STATUS
    return {
        "$schema": OPERATOR_START_ACK_TEMPLATE_SCHEMA,
        "ack_status": ack_status,
        "source_operator_start_gate_id": gate_id,
        "source_execution_receipt_id": execution_receipt.get("execution_receipt_id"),
        "ack_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": HOSTESS_OWNER,
        "host_shell_kind": host_shell_kind,
        "operator_started": False,
        "operator_start_acknowledged": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "accepted_action_gate_ids": [],
        "required_action_gate_ids": [gate.get("action_gate_id") for gate in action_gates],
    }


def platform_smoke_operator_start_reject_template(
    gate_id: str,
    execution_receipt: dict[str, Any],
    action_gates: list[dict[str, Any]],
    gate_status: str,
) -> dict[str, Any]:
    reject_status = PENDING_STATUS if gate_status == READY_STATUS else REJECTED_STATUS
    return {
        "$schema": OPERATOR_START_REJECT_TEMPLATE_SCHEMA,
        "reject_status": reject_status,
        "source_operator_start_gate_id": gate_id,
        "source_execution_receipt_id": execution_receipt.get("execution_receipt_id"),
        "reject_owner": HOSTESS_OWNER,
        "operator_started": False,
        "operator_start_acknowledged": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "rejected_action_gate_ids": [],
        "required_action_gate_ids": [gate.get("action_gate_id") for gate in action_gates],
        "next_required_action": "repair_or_decline_platform_smoke_operator_start",
    }


def platform_smoke_expected_evidence_receipt_templates(
    gate_id: str,
    action_gates: list[dict[str, Any]],
    gate_status: str,
) -> list[dict[str, Any]]:
    template_status = PENDING_STATUS if gate_status == READY_STATUS else REJECTED_STATUS
    templates = []
    for gate in action_gates:
        source_plan_action_id = gate.get("source_plan_action_id")
        templates.append(
            {
                "$schema": PLATFORM_SMOKE_EVIDENCE_RECEIPT_TEMPLATE_SCHEMA,
                "evidence_receipt_template_id": (
                    f"hostess.platform_smoke_expected_evidence_receipt.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_expected_evidence_receipt.unknown"
                ),
                "source_operator_start_gate_id": gate_id,
                "source_action_gate_id": gate.get("action_gate_id"),
                "source_action_execution_receipt_id": gate.get(
                    "source_action_execution_receipt_id"
                ),
                "source_plan_id": gate.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": gate.get("owner"),
                "route_kind": gate.get("route_kind"),
                "action_kind": gate.get("action_kind"),
                "expected_input_kind": gate.get("expected_input_kind"),
                "expected_output_kind": gate.get("expected_output_kind"),
                "evidence_receipt_status": template_status,
                "operator_started": False,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return templates


def platform_smoke_expected_evidence_receipt_template_dicts(
    operator_start_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    templates = operator_start_gate.get("expected_evidence_receipt_templates", [])
    if not isinstance(templates, list):
        return []
    return [item for item in templates if isinstance(item, dict)]


def platform_smoke_operator_start_templates_core_valid(
    action_gates: list[dict[str, Any]],
    request_template: dict[str, Any],
    ack_template: dict[str, Any],
    reject_template: dict[str, Any],
    evidence_templates: list[dict[str, Any]],
    gate_status: Any,
) -> bool:
    if gate_status not in {READY_STATUS, REJECTED_STATUS}:
        return False
    expected_status = PENDING_STATUS if gate_status == READY_STATUS else REJECTED_STATUS
    action_gate_ids = [gate.get("action_gate_id") for gate in action_gates]
    if request_template.get("$schema") != OPERATOR_START_REQUEST_TEMPLATE_SCHEMA:
        return False
    if request_template.get("template_status") != expected_status:
        return False
    if request_template.get("action_gate_ids") != action_gate_ids:
        return False
    if ack_template.get("$schema") != OPERATOR_START_ACK_TEMPLATE_SCHEMA:
        return False
    if ack_template.get("ack_status") != expected_status:
        return False
    if ack_template.get("required_action_gate_ids") != action_gate_ids:
        return False
    if ack_template.get("accepted_action_gate_ids") != []:
        return False
    if reject_template.get("$schema") != OPERATOR_START_REJECT_TEMPLATE_SCHEMA:
        return False
    if reject_template.get("reject_status") != expected_status:
        return False
    if reject_template.get("required_action_gate_ids") != action_gate_ids:
        return False
    if reject_template.get("rejected_action_gate_ids") != []:
        return False
    if len(evidence_templates) != len(action_gates):
        return False
    return platform_smoke_operator_start_templates_unstarted(
        request_template,
        ack_template,
        reject_template,
        evidence_templates,
        expected_status,
    )


def platform_smoke_operator_start_templates_match_gate(
    operator_start_gate: dict[str, Any],
    action_gates: list[dict[str, Any]],
    request_template: dict[str, Any],
    ack_template: dict[str, Any],
    reject_template: dict[str, Any],
    evidence_templates: list[dict[str, Any]],
) -> bool:
    if not platform_smoke_operator_start_templates_core_valid(
        action_gates,
        request_template,
        ack_template,
        reject_template,
        evidence_templates,
        operator_start_gate.get("status"),
    ):
        return False
    gate_id = operator_start_gate.get("operator_start_gate_id")
    receipt_id = operator_start_gate.get("source_execution_receipt_id")
    for template in (request_template, ack_template, reject_template):
        if template.get("source_operator_start_gate_id") != gate_id:
            return False
        if template.get("source_execution_receipt_id") != receipt_id:
            return False
    by_gate_id = {
        template.get("source_action_gate_id"): template
        for template in evidence_templates
    }
    for gate in action_gates:
        template = by_gate_id.get(gate.get("action_gate_id"))
        if not isinstance(template, dict):
            return False
        if template.get("source_operator_start_gate_id") != gate_id:
            return False
        for key in (
            "owner",
            "route_kind",
            "action_kind",
            "expected_input_kind",
            "expected_output_kind",
        ):
            if template.get(key) != gate.get(key):
                return False
    return True


def platform_smoke_operator_start_templates_unstarted(
    request_template: dict[str, Any],
    ack_template: dict[str, Any],
    reject_template: dict[str, Any],
    evidence_templates: list[dict[str, Any]],
    expected_status: str,
) -> bool:
    for template in (request_template, ack_template, reject_template):
        if template.get("operator_started") is not False:
            return False
        if template.get("operator_start_acknowledged") is not False:
            return False
        if template.get("schema_path_execution_allowed") is not False:
            return False
        if template.get("platform_execution_allowed") is not False:
            return False
        if template.get("studio_execution_allowed") is not False:
            return False
        if template.get("execution_performed") is not False:
            return False
        if template.get("runtime_execution_performed") is not False:
            return False
        if template.get("platform_execution_performed") is not False:
            return False
    for template in evidence_templates:
        if template.get("$schema") != PLATFORM_SMOKE_EVIDENCE_RECEIPT_TEMPLATE_SCHEMA:
            return False
        if template.get("evidence_receipt_status") != expected_status:
            return False
        if template.get("operator_started") is not False:
            return False
        if template.get("execution_started") is not False:
            return False
        if template.get("runtime_execution_performed") is not False:
            return False
        if template.get("platform_execution_performed") is not False:
            return False
        if template.get("studio_execution_allowed") is not False:
            return False
        if template.get("command_session_started") is not False:
            return False
    return True


def operator_start_readiness_input_contracts(
    pmb_shell_handoff_review_required: bool = False,
) -> list[dict[str, Any]]:
    contracts = list(OPERATOR_START_READINESS_INPUT_CONTRACTS)
    if pmb_shell_handoff_review_required:
        contracts.append(PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_CONTRACT)
    return contracts


def build_platform_smoke_operator_start_preflight_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    decision: str = APPROVED_STATUS,
    reason_code: str | None = None,
    pmb_shell_handoff_review: dict[str, Any] | None = None,
    pmb_shell_handoff_review_path: Path | None = None,
    require_pmb_shell_handoff_review: bool = False,
) -> dict[str, Any]:
    gate_validation = validate_platform_smoke_operator_start_gate(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
    )
    action_gates = platform_smoke_operator_start_action_gate_dicts(operator_start_gate)
    decision_supported = decision in {APPROVED_STATUS, REJECTED_STATUS}
    gate_ready = (
        operator_start_gate.get("status") == READY_STATUS
        and gate_validation.get("status") == PASS_STATUS
        and operator_start_gate.get("operator_start_required") is True
        and operator_start_gate.get("host_shell_execution_required") is True
        and all(
            gate.get("operator_start_gate_status") == PENDING_STATUS
            for gate in action_gates
        )
    )
    pmb_review_required = pmb_shell_handoff_review_is_required(
        pmb_shell_handoff_review,
        require_pmb_shell_handoff_review,
    )
    pmb_review_issue_code = pmb_shell_handoff_review_issue_code(
        pmb_shell_handoff_review,
        pmb_review_required,
    )
    pmb_review_ready = pmb_review_issue_code is None
    status = (
        APPROVED_STATUS
        if decision == APPROVED_STATUS and gate_ready and pmb_review_ready
        else REJECTED_STATUS
    )
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or operator_start_gate.get("issue_code")
            or gate_validation.get("issue_code")
            or pmb_review_issue_code
            or "hostess.issue.platform_smoke_operator_start_preflight_rejected"
        )
    readiness_inputs = platform_smoke_operator_start_readiness_inputs(
        operator_start_gate,
        status,
        issue_code,
        pmb_shell_handoff_review,
        pmb_shell_handoff_review_path,
        pmb_review_required,
    )
    action_receipts = platform_smoke_operator_start_action_decision_receipts(
        operator_start_gate,
        action_gates,
        status,
        issue_code,
    )
    approved_inputs = [
        item for item in readiness_inputs if item.get("readiness_status") == APPROVED_STATUS
    ]
    rejected_inputs = [
        item for item in readiness_inputs if item.get("readiness_status") == REJECTED_STATUS
    ]
    approved_actions = [
        item for item in action_receipts if item.get("decision_status") == APPROVED_STATUS
    ]
    rejected_actions = [
        item for item in action_receipts if item.get("decision_status") == REJECTED_STATUS
    ]
    checks = platform_smoke_operator_start_preflight_receipt_checks(
        operator_start_gate,
        gate_validation,
        action_gates,
        readiness_inputs,
        action_receipts,
        status,
        decision_supported,
        pmb_review_required,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == APPROVED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        readiness_inputs = platform_smoke_operator_start_readiness_inputs(
            operator_start_gate,
            status,
            issue_code,
            pmb_shell_handoff_review,
            pmb_shell_handoff_review_path,
            pmb_review_required,
        )
        action_receipts = platform_smoke_operator_start_action_decision_receipts(
            operator_start_gate,
            action_gates,
            status,
            issue_code,
        )
        approved_inputs = []
        rejected_inputs = readiness_inputs
        approved_actions = []
        rejected_actions = action_receipts

    gate_id = operator_start_gate.get("operator_start_gate_id")
    receipt_id = (
        f"hostess.platform_smoke_operator_start_preflight_receipt.{gate_id}"
        if isinstance(gate_id, str) and gate_id
        else "hostess.platform_smoke_operator_start_preflight_receipt.unknown"
    )

    return {
        "$schema": PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_SCHEMA,
        "operator_start_preflight_receipt_id": receipt_id,
        "source_operator_start_gate_id": gate_id,
        "source_execution_receipt_id": operator_start_gate.get("source_execution_receipt_id"),
        "source_execution_request_id": operator_start_gate.get("source_execution_request_id"),
        "source_approval_receipt_id": operator_start_gate.get("source_approval_receipt_id"),
        "source_plan_id": operator_start_gate.get("source_plan_id"),
        "source_bundle_id": operator_start_gate.get("source_bundle_id"),
        "source_execution_id": operator_start_gate.get("source_execution_id"),
        "source_request_id": operator_start_gate.get("source_request_id"),
        "target_profile": operator_start_gate.get("target_profile"),
        "target_platform": operator_start_gate.get("target_platform"),
        "host_shell_kind": operator_start_gate.get("host_shell_kind"),
        "status": status,
        "preflight_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "preflight_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": operator_start_gate.get("host_shell_owner"),
        "platform_owner": operator_start_gate.get("platform_owner"),
        "requester_role": operator_start_gate.get("requester_role"),
        "command_session_authority": operator_start_gate.get("command_session_authority"),
        "install_launch_evidence_authority": operator_start_gate.get("install_launch_evidence_authority"),
        "studio_role": operator_start_gate.get("studio_role"),
        "device_required": False,
        "target_device_required_for_future_execution": status == APPROVED_STATUS,
        "operator_approved": status == APPROVED_STATUS,
        "operator_start_preflight_approved": status == APPROVED_STATUS,
        "operator_start_required": status == APPROVED_STATUS,
        "operator_started": False,
        "operator_start_acknowledged": False,
        "host_shell_started": False,
        "host_shell_execution_required": status == APPROVED_STATUS,
        "toolchain_readiness_required": True,
        "device_readiness_required": True,
        "evidence_destination_required": True,
        "rollback_plan_required": True,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary(
            pmb_shell_handoff_review,
            pmb_shell_handoff_review_path,
        ),
        "source_pmb_shell_handoff_review_issue_code": pmb_review_issue_code,
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
        "source_operator_start_gate_status": operator_start_gate.get("status"),
        "source_operator_start_gate_validation_status": gate_validation.get("status"),
        "source_operator_start_gate_issue_code": (
            operator_start_gate.get("issue_code") or gate_validation.get("issue_code")
        ),
        "source_operator_start_action_gate_count": len(action_gates),
        "operator_start_action_decision_receipt_count": len(action_receipts),
        "approved_operator_start_action_count": len(approved_actions),
        "rejected_operator_start_action_count": len(rejected_actions),
        "readiness_input_count": len(readiness_inputs),
        "approved_readiness_input_count": len(approved_inputs),
        "rejected_readiness_input_count": len(rejected_inputs),
        "source_operator_start_action_gates": action_gates,
        "operator_start_action_decision_receipts": action_receipts,
        "readiness_inputs": readiness_inputs,
        "checks": checks,
        "next_required_action": (
            "operator_supply_hostess_toolchain_device_readiness_outside_studio"
            if status == APPROVED_STATUS
            else "repair_or_decline_platform_smoke_operator_start_gate"
        ),
    }


def validate_platform_smoke_operator_start_preflight_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    preflight_receipt: dict[str, Any],
    require_pmb_shell_handoff_review: bool = False,
) -> dict[str, Any]:
    gate_validation = validate_platform_smoke_operator_start_gate(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
    )
    action_gates = platform_smoke_operator_start_action_gate_dicts(operator_start_gate)
    action_receipts = platform_smoke_operator_start_action_decision_receipt_dicts(
        preflight_receipt
    )
    readiness_inputs = platform_smoke_operator_start_readiness_input_dicts(preflight_receipt)
    approved_inputs = [
        item for item in readiness_inputs if item.get("readiness_status") == APPROVED_STATUS
    ]
    rejected_inputs = [
        item for item in readiness_inputs if item.get("readiness_status") == REJECTED_STATUS
    ]
    approved_actions = [
        item for item in action_receipts if item.get("decision_status") == APPROVED_STATUS
    ]
    rejected_actions = [
        item for item in action_receipts if item.get("decision_status") == REJECTED_STATUS
    ]
    embedded_checks = preflight_receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    pmb_review_required = (
        preflight_receipt.get("pmb_shell_handoff_review_required") is True
        or require_pmb_shell_handoff_review
    )
    pmb_review_ready = preflight_receipt.get("pmb_shell_handoff_review_ready") is True
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.schema",
            preflight_receipt.get("$schema") == PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_SCHEMA,
            "platform smoke operator-start preflight receipt schema is supported",
            "platform smoke operator-start preflight receipt schema is unsupported",
            "hostess.issue.platform_smoke_operator_start_preflight_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.gate_id",
            preflight_receipt.get("source_operator_start_gate_id")
            == operator_start_gate.get("operator_start_gate_id"),
            "platform smoke operator-start preflight gate id matches",
            "platform smoke operator-start preflight gate id differs",
            "hostess.issue.platform_smoke_operator_start_preflight_gate_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.status",
            preflight_receipt.get("status") in {APPROVED_STATUS, REJECTED_STATUS},
            "platform smoke operator-start preflight status is supported",
            "platform smoke operator-start preflight status is unsupported",
            "hostess.issue.platform_smoke_operator_start_preflight_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.execution_policy",
            preflight_receipt.get("execution_policy")
            == PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_POLICY,
            "platform smoke operator-start preflight is receipt-only",
            "platform smoke operator-start preflight execution policy drifted",
            "hostess.issue.platform_smoke_operator_start_preflight_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.no_execution_started",
            all(preflight_receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and preflight_receipt.get("runtime_execution_performed") is False
            and preflight_receipt.get("platform_execution_performed") is False
            and preflight_receipt.get("operator_started") is False
            and preflight_receipt.get("operator_start_acknowledged") is False
            and preflight_receipt.get("host_shell_started") is False,
            "platform smoke operator-start preflight has not started runtime or platform work",
            "platform smoke operator-start preflight indicates runtime, platform, or operator start",
            "hostess.issue.platform_smoke_operator_start_preflight_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.execution_gate",
            preflight_receipt.get("schema_path_execution_allowed") is False
            and preflight_receipt.get("platform_execution_allowed") is False
            and preflight_receipt.get("studio_execution_allowed") is False
            and preflight_receipt.get("device_required") is False,
            "platform smoke operator-start preflight keeps schema path and Studio execution disabled",
            "platform smoke operator-start preflight allows schema path, platform, device, or Studio execution",
            "hostess.issue.platform_smoke_operator_start_preflight_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.authority",
            preflight_receipt.get("receipt_owner") == HOSTESS_OWNER
            and preflight_receipt.get("preflight_owner") == HOSTESS_OWNER
            and preflight_receipt.get("operator_start_owner") == HOSTESS_OWNER
            and preflight_receipt.get("host_shell_owner") == HOSTESS_OWNER
            and preflight_receipt.get("platform_owner") == HOSTESS_OWNER
            and preflight_receipt.get("requester_role") == STUDIO_REQUESTER
            and preflight_receipt.get("command_session_authority") == MANIFOLD_OWNER
            and preflight_receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and preflight_receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.source_gate",
            preflight_receipt.get("status") != APPROVED_STATUS
            or (
                operator_start_gate.get("status") == READY_STATUS
                and gate_validation.get("status") == PASS_STATUS
            ),
            "source platform smoke operator-start gate is ready and validates",
            "source platform smoke operator-start gate is rejected or invalid",
            operator_start_gate.get("issue_code")
            or gate_validation.get("issue_code")
            or "hostess.issue.platform_smoke_operator_start_gate_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.action_receipts",
            platform_smoke_operator_start_action_decision_receipts_match_gates(
                action_gates,
                action_receipts,
                preflight_receipt.get("status"),
            ),
            "platform smoke operator-start action decision receipts match action gates",
            "platform smoke operator-start action decision receipts drifted",
            "hostess.issue.platform_smoke_operator_start_preflight_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.readiness_inputs",
            platform_smoke_operator_start_readiness_inputs_match_contracts(
                operator_start_gate,
                readiness_inputs,
                preflight_receipt.get("status"),
                pmb_review_required,
            ),
            "platform smoke operator-start readiness inputs match required Hostess/Manifold inputs",
            "platform smoke operator-start readiness inputs drifted",
            "hostess.issue.platform_smoke_operator_start_preflight_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.pmb_shell_handoff_review",
            not pmb_review_required
            or (
                pmb_review_ready
                and any(
                    item.get("readiness_input_id")
                    == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
                    and item.get("readiness_status") == APPROVED_STATUS
                    and pmb_shell_handoff_readiness_input_summary_valid(item)
                    for item in readiness_inputs
                )
            )
            or preflight_receipt.get("status") == REJECTED_STATUS,
            "PMB shell handoff review gate is satisfied or preflight is rejected",
            "PMB shell handoff review gate is required but missing, blocked, or drifted",
            preflight_receipt.get("source_pmb_shell_handoff_review_issue_code")
            or "hostess.issue.pmb_shell_handoff_review_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.counts",
            preflight_receipt.get("source_operator_start_action_gate_count") == len(action_gates)
            and preflight_receipt.get("operator_start_action_decision_receipt_count")
            == len(action_receipts)
            and preflight_receipt.get("approved_operator_start_action_count") == len(approved_actions)
            and preflight_receipt.get("rejected_operator_start_action_count") == len(rejected_actions)
            and preflight_receipt.get("readiness_input_count") == len(readiness_inputs)
            and preflight_receipt.get("approved_readiness_input_count") == len(approved_inputs)
            and preflight_receipt.get("rejected_readiness_input_count") == len(rejected_inputs),
            "platform smoke operator-start preflight counts match action receipts and readiness inputs",
            "platform smoke operator-start preflight counts drifted",
            "hostess.issue.platform_smoke_operator_start_preflight_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.approved_consistency",
            preflight_receipt.get("status") != APPROVED_STATUS
            or (
                preflight_receipt.get("operator_approved") is True
                and preflight_receipt.get("operator_start_preflight_approved") is True
                and preflight_receipt.get("operator_start_required") is True
                and preflight_receipt.get("host_shell_execution_required") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(item.get("decision_status") == APPROVED_STATUS for item in action_receipts)
                and all(item.get("readiness_status") == APPROVED_STATUS for item in readiness_inputs)
                and (not pmb_review_required or pmb_review_ready)
            ),
            "approved platform smoke operator-start preflight carries approved action receipts and required inputs",
            "approved platform smoke operator-start preflight is inconsistent",
            "hostess.issue.platform_smoke_operator_start_preflight_approved_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.rejection_reason",
            preflight_receipt.get("status") != REJECTED_STATUS
            or isinstance(preflight_receipt.get("issue_code"), str),
            "rejected platform smoke operator-start preflight carries a reason code",
            "rejected platform smoke operator-start preflight is missing a reason code",
            "hostess.issue.platform_smoke_operator_start_preflight_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_VALIDATION_SCHEMA,
        "operator_start_preflight_receipt_id": preflight_receipt.get(
            "operator_start_preflight_receipt_id"
        ),
        "source_operator_start_gate_id": preflight_receipt.get("source_operator_start_gate_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def platform_smoke_operator_start_preflight_receipt_checks(
    operator_start_gate: dict[str, Any],
    gate_validation: dict[str, Any],
    action_gates: list[dict[str, Any]],
    readiness_inputs: list[dict[str, Any]],
    action_receipts: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
    pmb_shell_handoff_review_required: bool = False,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.source_gate",
            operator_start_gate.get("$schema") == PLATFORM_SMOKE_OPERATOR_START_GATE_SCHEMA
            and operator_start_gate.get("status") == READY_STATUS
            and gate_validation.get("status") == PASS_STATUS,
            "platform smoke operator-start gate is ready and validates",
            "platform smoke operator-start gate is rejected or invalid",
            operator_start_gate.get("issue_code")
            or gate_validation.get("issue_code")
            or "hostess.issue.platform_smoke_operator_start_gate_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.decision",
            decision_supported,
            "platform smoke operator-start preflight decision is supported",
            "platform smoke operator-start preflight decision is unsupported",
            "hostess.issue.platform_smoke_operator_start_preflight_decision",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.action_receipts",
            platform_smoke_operator_start_action_decision_receipts_match_gates(
                action_gates,
                action_receipts,
                status,
            ),
            "platform smoke operator-start action decision receipts match source gates",
            "platform smoke operator-start action decision receipts drifted",
            "hostess.issue.platform_smoke_operator_start_preflight_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.readiness_inputs",
            platform_smoke_operator_start_readiness_inputs_match_contracts(
                operator_start_gate,
                readiness_inputs,
                status,
                pmb_shell_handoff_review_required,
            ),
            "platform smoke operator-start readiness inputs match required contracts",
            "platform smoke operator-start readiness inputs drifted",
            "hostess.issue.platform_smoke_operator_start_preflight_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.pmb_shell_handoff_review",
            not pmb_shell_handoff_review_required
            or (
                status == APPROVED_STATUS
                and any(
                    item.get("readiness_input_id")
                    == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
                    and item.get("readiness_status") == APPROVED_STATUS
                    and pmb_shell_handoff_readiness_input_summary_valid(item)
                    for item in readiness_inputs
                )
            )
            or status == REJECTED_STATUS,
            "PMB shell handoff review gate is satisfied or preflight is rejected",
            "PMB shell handoff review gate is required but missing, blocked, or drifted",
            "hostess.issue.pmb_shell_handoff_review_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_operator_start_preflight.no_action_execution",
            all(
                platform_smoke_operator_start_action_decision_receipt_unstarted(item)
                for item in action_receipts
            )
            and all(platform_smoke_operator_start_readiness_input_unstarted(item) for item in readiness_inputs),
            "platform smoke operator-start preflight action receipts and inputs have not started execution",
            "platform smoke operator-start preflight action receipt or input indicates execution started",
            "hostess.issue.platform_smoke_operator_start_preflight_action_started",
        ),
    ]


def platform_smoke_operator_start_readiness_inputs(
    operator_start_gate: dict[str, Any],
    status: str,
    issue_code: str | None,
    pmb_shell_handoff_review: dict[str, Any] | None = None,
    pmb_shell_handoff_review_path: Path | None = None,
    require_pmb_shell_handoff_review: bool = False,
) -> list[dict[str, Any]]:
    readiness_status = APPROVED_STATUS if status == APPROVED_STATUS else REJECTED_STATUS
    inputs = []
    pmb_review_required = pmb_shell_handoff_review_is_required(
        pmb_shell_handoff_review,
        require_pmb_shell_handoff_review,
    )
    pmb_review_issue_code = pmb_shell_handoff_review_issue_code(
        pmb_shell_handoff_review,
        pmb_review_required,
    )
    for contract in operator_start_readiness_input_contracts(pmb_review_required):
        input_issue_code = None if readiness_status == APPROVED_STATUS else issue_code
        item = {
            "readiness_input_id": contract["readiness_input_id"],
            "source_operator_start_gate_id": operator_start_gate.get("operator_start_gate_id"),
            "owner": contract["owner"],
            "input_kind": contract["input_kind"],
            "expected_source_kind": contract["expected_source_kind"],
            "validation_kind": contract["validation_kind"],
            "readiness_status": readiness_status,
            "issue_code": input_issue_code,
            "required_before_operator_start": True,
            "operator_supplied": False,
            "validated_for_execution": False,
            "operator_started": False,
            "execution_started": False,
            "runtime_execution_performed": False,
            "platform_execution_performed": False,
            "studio_execution_allowed": False,
            "command_session_started": False,
        }
        if contract["readiness_input_id"] == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID:
            item.update(
                pmb_shell_handoff_review_summary(
                    pmb_shell_handoff_review,
                    pmb_shell_handoff_review_path,
                )
            )
            item["issue_code"] = (
                None
                if readiness_status == APPROVED_STATUS
                else issue_code or pmb_review_issue_code
            )
            item["source_pmb_shell_handoff_review_issue_code"] = pmb_review_issue_code
        inputs.append(item)
    return inputs


def platform_smoke_operator_start_readiness_input_dicts(
    preflight_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    inputs = preflight_receipt.get("readiness_inputs", [])
    if not isinstance(inputs, list):
        return []
    return [item for item in inputs if isinstance(item, dict)]


def platform_smoke_operator_start_readiness_inputs_match_contracts(
    operator_start_gate: dict[str, Any],
    readiness_inputs: list[dict[str, Any]],
    status: Any,
    pmb_shell_handoff_review_required: bool = False,
) -> bool:
    if status not in {APPROVED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {item.get("readiness_input_id"): item for item in readiness_inputs}
    contracts = operator_start_readiness_input_contracts(pmb_shell_handoff_review_required)
    if len(readiness_inputs) != len(contracts):
        return False
    for contract in contracts:
        item = by_id.get(contract["readiness_input_id"])
        if not isinstance(item, dict):
            return False
        for key in ("owner", "input_kind", "expected_source_kind", "validation_kind"):
            if item.get(key) != contract[key]:
                return False
        if item.get("source_operator_start_gate_id") != operator_start_gate.get("operator_start_gate_id"):
            return False
        if item.get("readiness_status") != status:
            return False
        if item.get("required_before_operator_start") is not True:
            return False
        if item.get("operator_supplied") is not False:
            return False
        if item.get("validated_for_execution") is not False:
            return False
        if not platform_smoke_operator_start_readiness_input_unstarted(item):
            return False
        if (
            contract["readiness_input_id"] == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
            and status == APPROVED_STATUS
            and not pmb_shell_handoff_readiness_input_summary_valid(item)
        ):
            return False
    return True


def platform_smoke_operator_start_readiness_input_unstarted(item: dict[str, Any]) -> bool:
    return (
        item.get("operator_started") is False
        and item.get("execution_started") is False
        and item.get("runtime_execution_performed") is False
        and item.get("platform_execution_performed") is False
        and item.get("studio_execution_allowed") is False
        and item.get("command_session_started") is False
    )


def platform_smoke_operator_start_action_decision_receipts(
    operator_start_gate: dict[str, Any],
    action_gates: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    decision_status = APPROVED_STATUS if status == APPROVED_STATUS else REJECTED_STATUS
    receipts = []
    for gate in action_gates:
        source_gate_id = gate.get("action_gate_id")
        source_plan_action_id = gate.get("source_plan_action_id")
        receipts.append(
            {
                "action_decision_receipt_id": (
                    f"hostess.platform_smoke_operator_start_action_decision.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_operator_start_action_decision.unknown"
                ),
                "source_operator_start_gate_id": operator_start_gate.get("operator_start_gate_id"),
                "source_action_gate_id": source_gate_id,
                "source_plan_id": gate.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": gate.get("owner"),
                "route_kind": gate.get("route_kind"),
                "action_kind": gate.get("action_kind"),
                "approval_kind": gate.get("approval_kind"),
                "expected_input_kind": gate.get("expected_input_kind"),
                "expected_output_kind": gate.get("expected_output_kind"),
                "decision_status": decision_status,
                "issue_code": None if decision_status == APPROVED_STATUS else issue_code,
                "operator_approved": decision_status == APPROVED_STATUS,
                "operator_start_required": decision_status == APPROVED_STATUS,
                "operator_started": False,
                "operator_start_acknowledged": False,
                "host_shell_execution_required": decision_status == APPROVED_STATUS,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return receipts


def platform_smoke_operator_start_action_decision_receipt_dicts(
    preflight_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    receipts = preflight_receipt.get("operator_start_action_decision_receipts", [])
    if not isinstance(receipts, list):
        return []
    return [item for item in receipts if isinstance(item, dict)]


def platform_smoke_operator_start_action_decision_receipts_match_gates(
    action_gates: list[dict[str, Any]],
    action_receipts: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {APPROVED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        receipt.get("source_action_gate_id"): receipt
        for receipt in action_receipts
    }
    if len(action_receipts) != len(action_gates):
        return False
    for gate in action_gates:
        receipt = by_id.get(gate.get("action_gate_id"))
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
            if receipt.get(key) != gate.get(key):
                return False
        if receipt.get("source_plan_action_id") != gate.get("source_plan_action_id"):
            return False
        if receipt.get("decision_status") != status:
            return False
        if receipt.get("operator_approved") != (status == APPROVED_STATUS):
            return False
        if receipt.get("operator_start_required") != (status == APPROVED_STATUS):
            return False
        if receipt.get("host_shell_execution_required") != (status == APPROVED_STATUS):
            return False
        if not platform_smoke_operator_start_action_decision_receipt_unstarted(receipt):
            return False
    return True


def platform_smoke_operator_start_action_decision_receipt_unstarted(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("operator_started") is False
        and receipt.get("operator_start_acknowledged") is False
        and receipt.get("execution_started") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("command_session_started") is False
    )


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

__all__ = [
    "build_platform_smoke_plan",
    "validate_platform_smoke_plan",
    "platform_smoke_plan_actions",
    "platform_smoke_plan_checks",
    "platform_smoke_plan_action_dicts",
    "platform_smoke_plan_actions_match_contracts",
    "platform_smoke_action_unstarted",
    "platform_smoke_plan_approvals",
    "platform_smoke_plan_approvals_match_actions",
    "build_platform_smoke_approval_receipt",
    "validate_platform_smoke_approval_receipt",
    "platform_smoke_action_approval_receipts",
    "platform_smoke_approval_receipt_checks",
    "platform_smoke_action_approval_receipt_dicts",
    "platform_smoke_action_approval_receipts_match_actions",
    "platform_smoke_approval_receipt_unstarted",
    "build_platform_smoke_execution_request",
    "validate_platform_smoke_execution_request",
    "build_platform_smoke_execution_receipt",
    "validate_platform_smoke_execution_receipt",
    "platform_smoke_execution_action_requests",
    "platform_smoke_execution_request_checks",
    "platform_smoke_execution_action_request_dicts",
    "platform_smoke_execution_action_requests_match_approvals",
    "platform_smoke_execution_action_request_unstarted",
    "platform_smoke_execution_action_receipts",
    "platform_smoke_execution_receipt_checks",
    "platform_smoke_execution_action_receipt_dicts",
    "platform_smoke_execution_action_receipts_match_requests",
    "platform_smoke_execution_action_receipt_unstarted",
    "build_platform_smoke_operator_start_gate",
    "validate_platform_smoke_operator_start_gate",
    "platform_smoke_operator_start_action_gates",
    "platform_smoke_operator_start_gate_checks",
    "platform_smoke_operator_start_action_gate_dicts",
    "platform_smoke_operator_start_action_gates_match_receipts",
    "platform_smoke_operator_start_action_gate_unstarted",
    "platform_smoke_operator_start_request_template",
    "platform_smoke_operator_start_ack_template",
    "platform_smoke_operator_start_reject_template",
    "platform_smoke_expected_evidence_receipt_templates",
    "platform_smoke_expected_evidence_receipt_template_dicts",
    "platform_smoke_operator_start_templates_core_valid",
    "platform_smoke_operator_start_templates_match_gate",
    "platform_smoke_operator_start_templates_unstarted",
    "operator_start_readiness_input_contracts",
    "build_platform_smoke_operator_start_preflight_receipt",
    "validate_platform_smoke_operator_start_preflight_receipt",
    "platform_smoke_operator_start_preflight_receipt_checks",
    "platform_smoke_operator_start_readiness_inputs",
    "platform_smoke_operator_start_readiness_input_dicts",
    "platform_smoke_operator_start_readiness_inputs_match_contracts",
    "platform_smoke_operator_start_readiness_input_unstarted",
    "platform_smoke_operator_start_action_decision_receipts",
    "platform_smoke_operator_start_action_decision_receipt_dicts",
    "platform_smoke_operator_start_action_decision_receipts_match_gates",
    "platform_smoke_operator_start_action_decision_receipt_unstarted",
    "build_platform_smoke_execution_report",
    "validate_platform_smoke_execution_report",
    "platform_smoke_execution_report_checks",
    "platform_smoke_execution_report_action_reports",
    "platform_smoke_execution_report_readiness_results",
    "platform_smoke_execution_report_evidence_placeholders",
    "platform_smoke_execution_report_action_report_dicts",
    "platform_smoke_execution_report_readiness_result_dicts",
    "platform_smoke_execution_report_evidence_placeholder_dicts",
    "platform_smoke_execution_report_action_reports_match_receipts",
    "platform_smoke_execution_report_readiness_results_match_inputs",
    "platform_smoke_execution_report_evidence_placeholders_match_reports",
    "platform_smoke_execution_report_action_report_schema_unstarted",
    "platform_smoke_execution_report_readiness_result_schema_unstarted",
    "platform_smoke_execution_report_evidence_placeholder_unstarted",
    "build_platform_smoke_evidence_attachment_receipt",
    "validate_platform_smoke_evidence_attachment_receipt",
    "platform_smoke_evidence_attachment_receipt_checks",
    "platform_smoke_evidence_attachments",
    "platform_smoke_readiness_evidence_attachments",
    "platform_smoke_evidence_attachment_dicts",
    "platform_smoke_readiness_evidence_attachment_dicts",
    "platform_smoke_evidence_attachments_match_placeholders",
    "platform_smoke_readiness_evidence_attachments_match_results",
    "platform_smoke_evidence_attachment_unstarted",
    "platform_smoke_readiness_evidence_attachment_unstarted",
    "build_platform_smoke_evidence_review",
    "validate_platform_smoke_evidence_review",
    "platform_smoke_evidence_review_checks",
    "platform_smoke_evidence_review_attachment_rows",
    "platform_smoke_evidence_review_readiness_rows",
    "platform_smoke_evidence_review_row_dicts",
    "platform_smoke_evidence_review_readiness_row_dicts",
    "platform_smoke_evidence_review_rows_match_attachments",
    "platform_smoke_evidence_review_readiness_rows_match_attachments",
    "platform_smoke_evidence_review_row_unstarted",
    "platform_smoke_evidence_review_readiness_row_unstarted",
]
