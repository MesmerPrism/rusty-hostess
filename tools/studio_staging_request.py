"""Schema-only Hostess intake for Studio staging execution requests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUEST_SCHEMA = "rusty.studio.shell_hostess_staging_execution_request.v1"
ACK_SCHEMA = "rusty.studio.shell_hostess_staging_execution_ack.v1"
REJECT_SCHEMA = "rusty.studio.shell_hostess_staging_execution_reject.v1"
INTAKE_SCHEMA = "rusty.hostess.studio_staging_execution_request_intake.v1"
SMOKE_HANDOFF_SCHEMA = "rusty.hostess.studio_staging_smoke_handoff.v1"
SMOKE_HANDOFF_VALIDATION_SCHEMA = "rusty.hostess.studio_staging_smoke_handoff_validation.v1"
SMOKE_DRY_RUN_REQUEST_SCHEMA = "rusty.hostess.studio_staging_smoke_dry_run_request.v1"
SMOKE_DRY_RUN_RECEIPT_SCHEMA = "rusty.hostess.studio_staging_smoke_dry_run_receipt.v1"
SMOKE_DRY_RUN_VALIDATION_SCHEMA = "rusty.hostess.studio_staging_smoke_dry_run_validation.v1"
SMOKE_EXECUTION_PREFLIGHT_SCHEMA = "rusty.hostess.studio_staging_smoke_execution_preflight.v1"
SMOKE_EXECUTION_PREFLIGHT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_smoke_execution_preflight_validation.v1"
)
SMOKE_HOST_SHELL_EXECUTION_SCHEMA = "rusty.hostess.studio_staging_smoke_host_shell_execution.v1"
SMOKE_HOST_SHELL_EXECUTION_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_smoke_host_shell_execution_validation.v1"
)
SMOKE_REVIEW_BUNDLE_SCHEMA = "rusty.hostess.studio_staging_smoke_review_bundle.v1"
SMOKE_REVIEW_BUNDLE_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_smoke_review_bundle_validation.v1"
)
PLATFORM_SMOKE_PLAN_SCHEMA = "rusty.hostess.studio_staging_platform_smoke_plan.v1"
PLATFORM_SMOKE_PLAN_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_plan_validation.v1"
)

READY_STATUS = "ready"
BLOCKED_STATUS = "blocked"
ACCEPTED_STATUS = "accepted"
REJECTED_STATUS = "rejected"
PENDING_STATUS = "pending"
COMPLETED_STATUS = "completed"
REVIEWED_STATUS = "reviewed"
PLANNED_STATUS = "planned"
PASS_STATUS = "pass"
FAIL_STATUS = "fail"

HOSTESS_OWNER = "rusty.hostess"
MANIFOLD_OWNER = "rusty.manifold"
STUDIO_REQUESTER = "rusty.studio"
STUDIO_ROLE = "authoring.export_planning"
REQUEST_POLICY = "not_executed.hostess_request_only"
HOST_SHELL_EXECUTION_POLICY = "hostess.no_device_host_shell_schema_execution_only"
SMOKE_REVIEW_BUNDLE_POLICY = "hostess.no_device_review_bundle_only"
PLATFORM_SMOKE_PLAN_POLICY = "hostess.operator_controlled_platform_smoke_plan_only"

REQUIRED_PROHIBITED_ACTIONS = [
    "stage_generated_shells",
    "install",
    "launch",
    "open_command_session",
    "collect_device_evidence",
    "collect_install_launch_evidence",
]

REQUIRED_EVIDENCE_KINDS = [
    "hostess_staging_request_ack",
    "hostess_file_copy_stage_receipt",
    "hostess_install_launch_evidence_receipt",
    "manifold_command_session_contract_review",
]

SMOKE_HANDOFF_REQUIRED_EVIDENCE_KINDS = REQUIRED_EVIDENCE_KINDS + [
    "hostess_smoke_handoff_checklist",
]

SMOKE_DRY_RUN_REQUIRED_RECEIPT_KINDS = SMOKE_HANDOFF_REQUIRED_EVIDENCE_KINDS + [
    "hostess_smoke_dry_run_receipt",
]

HOSTESS_ACTION_ROUTES = {
    "adapter.hostess.accept_staging_handoff": "hostess.accept.staging_handoff",
    "adapter.hostess.verify_staging_file_plan_checksum": "hostess.verify.staging_file_plan_checksum",
    "adapter.hostess.review_staging_file_requests": "hostess.review.staging_file_requests",
    "adapter.hostess.copy_staging_files": "hostess.stage.files_from_plan",
    "adapter.hostess.collect_install_launch_evidence": "hostess.collect.install_launch_evidence",
}

MANIFOLD_ACTION_ROUTES = {
    "adapter.manifold.review_command_session_contract": "manifold.review.command_session_contract",
}

SMOKE_HANDOFF_STARTED_FLAGS = [
    "execution_performed",
    "build_started",
    "copy_started",
    "stage_started",
    "install_started",
    "launch_started",
    "evidence_collection_started",
    "command_session_started",
]

SMOKE_HANDOFF_ITEM_CONTRACTS = [
    {
        "item_id": "hostess.smoke.validate_studio_request_intake",
        "owner": HOSTESS_OWNER,
        "source_action_id": "adapter.hostess.accept_staging_handoff",
        "route_kind": "hostess.adapter.validate_studio_request",
        "expected_output_kind": "studio_staging_execution_request_intake",
    },
    {
        "item_id": "hostess.smoke.ack_or_reject_request",
        "owner": HOSTESS_OWNER,
        "source_action_id": "adapter.hostess.accept_staging_handoff",
        "route_kind": "hostess.adapter.ack_or_reject_studio_request",
        "expected_output_kind": "hostess_staging_request_ack_or_reject",
    },
    {
        "item_id": "hostess.smoke.plan_stage_copy_receipt",
        "owner": HOSTESS_OWNER,
        "source_action_id": "adapter.hostess.copy_staging_files",
        "route_kind": "hostess.stage.files_from_plan",
        "expected_output_kind": "hostess_file_copy_stage_receipt",
    },
    {
        "item_id": "hostess.smoke.plan_install_launch_receipt",
        "owner": HOSTESS_OWNER,
        "source_action_id": "adapter.hostess.collect_install_launch_evidence",
        "route_kind": "hostess.collect.install_launch_evidence",
        "expected_output_kind": "hostess_install_launch_evidence_receipt",
    },
    {
        "item_id": "hostess.smoke.plan_command_session_review",
        "owner": MANIFOLD_OWNER,
        "source_action_id": "adapter.manifold.review_command_session_contract",
        "route_kind": "manifold.review.command_session_contract",
        "expected_output_kind": "manifold_command_session_contract_review",
    },
]

SMOKE_DRY_RUN_STEP_CONTRACTS = [
    {
        "step_id": "hostess.dry_run.validate_request_intake",
        "owner": HOSTESS_OWNER,
        "source_item_id": "hostess.smoke.validate_studio_request_intake",
        "route_kind": "hostess.adapter.validate_studio_request",
        "expected_receipt_kind": "hostess_smoke_handoff_checklist",
    },
    {
        "step_id": "hostess.dry_run.accept_request_ack",
        "owner": HOSTESS_OWNER,
        "source_item_id": "hostess.smoke.ack_or_reject_request",
        "route_kind": "hostess.adapter.ack_or_reject_studio_request",
        "expected_receipt_kind": "hostess_staging_request_ack",
    },
    {
        "step_id": "hostess.dry_run.plan_stage_copy_receipt",
        "owner": HOSTESS_OWNER,
        "source_item_id": "hostess.smoke.plan_stage_copy_receipt",
        "route_kind": "hostess.stage.files_from_plan",
        "expected_receipt_kind": "hostess_file_copy_stage_receipt",
    },
    {
        "step_id": "hostess.dry_run.plan_install_launch_receipt",
        "owner": HOSTESS_OWNER,
        "source_item_id": "hostess.smoke.plan_install_launch_receipt",
        "route_kind": "hostess.collect.install_launch_evidence",
        "expected_receipt_kind": "hostess_install_launch_evidence_receipt",
    },
    {
        "step_id": "hostess.dry_run.plan_command_session_review",
        "owner": MANIFOLD_OWNER,
        "source_item_id": "hostess.smoke.plan_command_session_review",
        "route_kind": "manifold.review.command_session_contract",
        "expected_receipt_kind": "manifold_command_session_contract_review",
    },
]

SMOKE_PREFLIGHT_CAPABILITY_CONTRACTS = [
    {
        "capability_id": "hostess.preflight.validate_dry_run_request",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.preflight.validate_dry_run_request",
        "evidence_kind": "hostess_smoke_dry_run_request_validation",
    },
    {
        "capability_id": "hostess.preflight.validate_dry_run_receipt",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.preflight.validate_dry_run_receipt",
        "evidence_kind": "hostess_smoke_dry_run_receipt_validation",
    },
    {
        "capability_id": "hostess.preflight.verify_stage_copy_plan",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.stage.files_from_plan",
        "evidence_kind": "hostess_file_copy_stage_receipt",
    },
    {
        "capability_id": "hostess.preflight.verify_install_launch_evidence_plan",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.collect.install_launch_evidence",
        "evidence_kind": "hostess_install_launch_evidence_receipt",
    },
    {
        "capability_id": "hostess.preflight.verify_command_session_review_plan",
        "owner": MANIFOLD_OWNER,
        "route_kind": "manifold.review.command_session_contract",
        "evidence_kind": "manifold_command_session_contract_review",
    },
    {
        "capability_id": "hostess.preflight.no_device_runtime_guard",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.preflight.no_device_runtime_guard",
        "evidence_kind": "hostess_smoke_execution_preflight",
    },
]

PLATFORM_SMOKE_PLAN_ACTION_CONTRACTS = [
    {
        "plan_action_id": "hostess.platform_smoke.review_bundle_gate",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.review_bundle_gate",
        "action_kind": "hostess_operator_review_gate",
        "approval_kind": "operator.reviewed_bundle_acceptance",
        "expected_input_kind": "hostess_smoke_review_bundle",
        "expected_output_kind": "hostess_platform_smoke_plan_gate",
    },
    {
        "plan_action_id": "hostess.platform_smoke.copy_stage_files",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.copy_stage_files",
        "action_kind": "hostess_copy_stage_plan",
        "approval_kind": "operator.copy_stage_approval",
        "expected_input_kind": "hostess_smoke_review_bundle",
        "expected_output_kind": "hostess_copy_stage_receipt",
    },
    {
        "plan_action_id": "hostess.platform_smoke.install_package",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.install_package",
        "action_kind": "hostess_install_plan",
        "approval_kind": "operator.install_approval",
        "expected_input_kind": "hostess_copy_stage_receipt",
        "expected_output_kind": "hostess_install_receipt",
    },
    {
        "plan_action_id": "hostess.platform_smoke.launch_package",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.launch_package",
        "action_kind": "hostess_launch_plan",
        "approval_kind": "operator.launch_approval",
        "expected_input_kind": "hostess_install_receipt",
        "expected_output_kind": "hostess_launch_receipt",
    },
    {
        "plan_action_id": "hostess.platform_smoke.collect_install_launch_evidence",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.collect_install_launch_evidence",
        "action_kind": "hostess_evidence_plan",
        "approval_kind": "operator.evidence_collection_approval",
        "expected_input_kind": "hostess_launch_receipt",
        "expected_output_kind": "hostess_install_launch_evidence_bundle",
    },
    {
        "plan_action_id": "manifold.platform_smoke.review_command_session_contract",
        "owner": MANIFOLD_OWNER,
        "route_kind": "manifold.review.command_session_contract",
        "action_kind": "manifold_command_session_contract_review_plan",
        "approval_kind": "operator.command_session_review_approval",
        "expected_input_kind": "hostess_smoke_review_bundle",
        "expected_output_kind": "manifold_command_session_contract_review",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_intake_report(request: dict[str, Any], source_path: Path | None = None) -> dict[str, Any]:
    checks = request_checks(request)
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    actions = request_actions(request)
    action_ids = [action.get("action_id") for action in actions if isinstance(action.get("action_id"), str)]
    status = ACCEPTED_STATUS if not failed else REJECTED_STATUS
    issue_code = failed[0]["issue_code"] if failed else None

    return {
        "$schema": INTAKE_SCHEMA,
        "request_schema": request.get("$schema"),
        "request_path": str(source_path) if source_path else None,
        "request_id": request.get("request_id"),
        "status": status,
        "issue_code": issue_code,
        "adapter_owner": HOSTESS_OWNER,
        "requester_role": request.get("requester_role"),
        "command_session_authority": request.get("command_session_authority"),
        "install_launch_evidence_authority": request.get("install_launch_evidence_authority"),
        "studio_role": request.get("studio_role"),
        "execution_performed": False,
        "copy_stage_install_launch_evidence_started": False,
        "command_session_started": False,
        "adapter_action_count": len(actions),
        "accepted_action_ids": action_ids if status == ACCEPTED_STATUS else [],
        "rejected_action_ids": action_ids if status == REJECTED_STATUS else [],
        "required_evidence_kinds": REQUIRED_EVIDENCE_KINDS,
        "next_required_action": (
            "emit_hostess_ack_fixture"
            if status == ACCEPTED_STATUS
            else "repair_studio_staging_execution_request"
        ),
        "checks": checks,
    }


def build_ack_fixture(request: dict[str, Any]) -> dict[str, Any]:
    report = build_intake_report(request)
    if report["status"] != ACCEPTED_STATUS:
        raise ValueError(f"cannot accept rejected staging request: {report['issue_code']}")
    action_ids = expected_action_ids(request)
    return {
        "$schema": ACK_SCHEMA,
        "request_id": request.get("request_id"),
        "accepted_by": HOSTESS_OWNER,
        "ack_status": ACCEPTED_STATUS,
        "execution_in_studio": False,
        "command_session_authority": request.get("command_session_authority"),
        "install_launch_evidence_authority": request.get("install_launch_evidence_authority"),
        "required_action_ids": action_ids,
        "accepted_action_ids": action_ids,
        "required_evidence_kinds": REQUIRED_EVIDENCE_KINDS,
        "issue_code": None,
    }


def build_reject_fixture(
    request: dict[str, Any],
    reason_code: str | None = None,
) -> dict[str, Any]:
    action_ids = expected_action_ids(request)
    report = build_intake_report(request)
    issue_code = reason_code or report.get("issue_code") or "hostess.issue.staging_request_rejected"
    return {
        "$schema": REJECT_SCHEMA,
        "request_id": request.get("request_id"),
        "rejected_by": HOSTESS_OWNER,
        "reject_status": REJECTED_STATUS,
        "execution_in_studio": False,
        "request_action_ids": action_ids,
        "rejected_action_ids": action_ids,
        "reason_code": issue_code,
        "next_required_action": "repair_studio_staging_execution_request",
        "issue_code": issue_code,
    }


def build_smoke_handoff_checklist(
    request: dict[str, Any],
    intake_report: dict[str, Any] | None = None,
    ack: dict[str, Any] | None = None,
    target_profile: str = "hostess.t.schema_smoke",
) -> dict[str, Any]:
    intake = intake_report or build_intake_report(request)
    items = smoke_handoff_items(request, intake)
    checks = smoke_handoff_checks(request, intake, ack, items)
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    request_id = request.get("request_id")
    handoff_id = (
        f"hostess.smoke_handoff.{request_id}"
        if isinstance(request_id, str) and request_id
        else "hostess.smoke_handoff.unknown"
    )
    action_ids = expected_action_ids(request)
    ack_action_ids = ack.get("accepted_action_ids", []) if isinstance(ack, dict) else []

    return {
        "$schema": SMOKE_HANDOFF_SCHEMA,
        "handoff_id": handoff_id,
        "request_id": request_id,
        "request_schema": request.get("$schema"),
        "intake_schema": intake.get("$schema"),
        "target_profile": target_profile,
        "status": READY_STATUS if not failed else BLOCKED_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "smoke_scope": "schema_only_request_ack_evidence_checklist",
        "adapter_owner": HOSTESS_OWNER,
        "requester_role": request.get("requester_role"),
        "command_session_authority": request.get("command_session_authority"),
        "install_launch_evidence_authority": request.get("install_launch_evidence_authority"),
        "studio_role": request.get("studio_role"),
        "execution_performed": False,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "request_action_ids": action_ids,
        "accepted_action_ids": ack_action_ids,
        "required_evidence_kinds": SMOKE_HANDOFF_REQUIRED_EVIDENCE_KINDS,
        "checklist_items": items,
        "checks": checks,
    }


def validate_smoke_handoff_checklist(checklist: dict[str, Any]) -> dict[str, Any]:
    items = checklist.get("checklist_items", [])
    if not isinstance(items, list):
        items = []
    item_dicts = [item for item in items if isinstance(item, dict)]
    embedded_checks = checklist.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_smoke_handoff.schema",
            checklist.get("$schema") == SMOKE_HANDOFF_SCHEMA,
            "smoke handoff schema is supported",
            "smoke handoff schema is unsupported",
            "hostess.issue.smoke_handoff_schema",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.status",
            checklist.get("status") in {READY_STATUS, BLOCKED_STATUS},
            "smoke handoff status is supported",
            "smoke handoff status is unsupported",
            "hostess.issue.smoke_handoff_status",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.no_runtime_started",
            all(checklist.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS),
            "smoke handoff has not started runtime work",
            "smoke handoff indicates runtime work started",
            "hostess.issue.smoke_handoff_runtime_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.evidence_kinds",
            set(checklist.get("required_evidence_kinds", []))
            == set(SMOKE_HANDOFF_REQUIRED_EVIDENCE_KINDS),
            "smoke handoff declares required evidence kinds",
            "smoke handoff evidence kinds drifted",
            "hostess.issue.smoke_handoff_evidence_kinds",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.item_contracts",
            smoke_handoff_items_match_contracts(item_dicts),
            "smoke handoff items match owner and route contracts",
            "smoke handoff items drifted from owner or route contracts",
            "hostess.issue.smoke_handoff_item_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.no_item_execution",
            all(item.get("execution_started") is False for item in item_dicts),
            "smoke handoff items have not started runtime work",
            "smoke handoff item indicates runtime work started",
            "hostess.issue.smoke_handoff_item_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.ready_consistency",
            checklist.get("status") != READY_STATUS
            or (
                all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(item.get("status") == READY_STATUS for item in item_dicts)
            ),
            "ready smoke handoff has passing checks and ready items",
            "ready smoke handoff has failed checks or blocked items",
            "hostess.issue.smoke_handoff_ready_inconsistent",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": SMOKE_HANDOFF_VALIDATION_SCHEMA,
        "handoff_id": checklist.get("handoff_id"),
        "request_id": checklist.get("request_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "checks": checks,
    }


def smoke_handoff_items(
    request: dict[str, Any],
    intake_report: dict[str, Any],
) -> list[dict[str, Any]]:
    actions = {action.get("action_id"): action for action in request_actions(request)}
    intake_accepted = intake_report.get("status") == ACCEPTED_STATUS
    items = []
    for contract in SMOKE_HANDOFF_ITEM_CONTRACTS:
        source_action = actions.get(contract["source_action_id"])
        issue_code = None
        if not isinstance(source_action, dict):
            issue_code = "hostess.issue.smoke_handoff_source_action_missing"
        elif not intake_accepted:
            issue_code = intake_report.get("issue_code") or "hostess.issue.staging_request_rejected"
        items.append(
            {
                "item_id": contract["item_id"],
                "owner": contract["owner"],
                "status": READY_STATUS if issue_code is None else BLOCKED_STATUS,
                "issue_code": issue_code,
                "source_action_id": contract["source_action_id"],
                "source_route_kind": source_action.get("route_kind") if isinstance(source_action, dict) else None,
                "route_kind": contract["route_kind"],
                "expected_input_path": source_action.get("expected_input_path")
                if isinstance(source_action, dict)
                else None,
                "expected_output_kind": contract["expected_output_kind"],
                "execution_started": False,
            }
        )
    return items


def smoke_handoff_checks(
    request: dict[str, Any],
    intake_report: dict[str, Any],
    ack: dict[str, Any] | None,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ack_report = validate_ack_fixture(request, ack) if isinstance(ack, dict) else None
    return [
        check(
            "hostess.check.studio_staging_smoke_handoff.request_schema",
            request.get("$schema") == REQUEST_SCHEMA,
            "Studio request schema is supported",
            "Studio request schema is unsupported",
            "hostess.issue.staging_request_schema",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.intake_status",
            intake_report.get("$schema") == INTAKE_SCHEMA
            and intake_report.get("status") == ACCEPTED_STATUS,
            "Hostess intake accepted the Studio request",
            "Hostess intake did not accept the Studio request",
            intake_report.get("issue_code") or "hostess.issue.staging_request_rejected",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.ack",
            ack_report is not None and ack_report.get("status") == PASS_STATUS,
            "Hostess ack fixture validates",
            "Hostess ack fixture is missing or invalid",
            (ack_report or {}).get("issue_code") or "hostess.issue.smoke_handoff_ack_missing",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.authority",
            request.get("adapter_owner") == HOSTESS_OWNER
            and request.get("requester_role") == STUDIO_REQUESTER
            and request.get("command_session_authority") == MANIFOLD_OWNER
            and request.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and request.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.items_ready",
            all(item.get("status") == READY_STATUS for item in items),
            "smoke handoff items are ready",
            "smoke handoff items are blocked",
            first_item_issue_code(items) or "hostess.issue.smoke_handoff_items_blocked",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.no_item_execution",
            all(item.get("execution_started") is False for item in items),
            "smoke handoff items have not started runtime work",
            "smoke handoff item indicates runtime work started",
            "hostess.issue.smoke_handoff_item_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_handoff.item_contracts",
            smoke_handoff_items_match_contracts(items),
            "smoke handoff items match owner and route contracts",
            "smoke handoff items drifted from owner or route contracts",
            "hostess.issue.smoke_handoff_item_contract_drift",
        ),
    ]


def smoke_handoff_items_match_contracts(items: list[dict[str, Any]]) -> bool:
    by_id = {item.get("item_id"): item for item in items}
    for contract in SMOKE_HANDOFF_ITEM_CONTRACTS:
        item = by_id.get(contract["item_id"])
        if not isinstance(item, dict):
            return False
        if item.get("owner") != contract["owner"]:
            return False
        if item.get("source_action_id") != contract["source_action_id"]:
            return False
        if item.get("route_kind") != contract["route_kind"]:
            return False
        if item.get("expected_output_kind") != contract["expected_output_kind"]:
            return False
    return True


def first_item_issue_code(items: list[dict[str, Any]]) -> str | None:
    for item in items:
        issue_code = item.get("issue_code")
        if isinstance(issue_code, str) and issue_code:
            return issue_code
    return None


def build_smoke_dry_run_request(
    smoke_handoff: dict[str, Any],
    target_profile: str | None = None,
) -> dict[str, Any]:
    handoff_validation = validate_smoke_handoff_checklist(smoke_handoff)
    steps = smoke_dry_run_steps(smoke_handoff, handoff_validation)
    checks = smoke_dry_run_request_checks(smoke_handoff, handoff_validation, steps)
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    handoff_id = smoke_handoff.get("handoff_id")
    dry_run_request_id = (
        f"hostess.smoke_dry_run_request.{handoff_id}"
        if isinstance(handoff_id, str) and handoff_id
        else "hostess.smoke_dry_run_request.unknown"
    )

    return {
        "$schema": SMOKE_DRY_RUN_REQUEST_SCHEMA,
        "dry_run_request_id": dry_run_request_id,
        "smoke_handoff_id": handoff_id,
        "source_request_id": smoke_handoff.get("request_id"),
        "source_smoke_schema": smoke_handoff.get("$schema"),
        "target_profile": target_profile or smoke_handoff.get("target_profile"),
        "status": READY_STATUS if not failed else BLOCKED_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_policy": "not_executed.hostess_dry_run_request_only",
        "adapter_owner": HOSTESS_OWNER,
        "requester_role": smoke_handoff.get("requester_role"),
        "command_session_authority": smoke_handoff.get("command_session_authority"),
        "install_launch_evidence_authority": smoke_handoff.get("install_launch_evidence_authority"),
        "studio_role": smoke_handoff.get("studio_role"),
        "execution_performed": False,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "required_receipt_kinds": SMOKE_DRY_RUN_REQUIRED_RECEIPT_KINDS,
        "dry_run_steps": steps,
        "checks": checks,
    }


def build_smoke_dry_run_receipt(dry_run_request: dict[str, Any]) -> dict[str, Any]:
    validation = validate_smoke_dry_run_request(dry_run_request)
    request_ready = (
        dry_run_request.get("status") == READY_STATUS and validation.get("status") == PASS_STATUS
    )
    steps = smoke_dry_run_request_steps(dry_run_request)
    receipt_items = [
        {
            "step_id": step.get("step_id"),
            "owner": step.get("owner"),
            "route_kind": step.get("route_kind"),
            "receipt_kind": step.get("expected_receipt_kind"),
            "receipt_status": ACCEPTED_STATUS if request_ready else REJECTED_STATUS,
            "execution_performed": False,
            "issue_code": None if request_ready else step.get("issue_code") or validation.get("issue_code"),
        }
        for step in steps
    ]
    dry_run_request_id = dry_run_request.get("dry_run_request_id")
    receipt_id = (
        f"hostess.smoke_dry_run_receipt.{dry_run_request_id}"
        if isinstance(dry_run_request_id, str) and dry_run_request_id
        else "hostess.smoke_dry_run_receipt.unknown"
    )

    return {
        "$schema": SMOKE_DRY_RUN_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "dry_run_request_id": dry_run_request_id,
        "smoke_handoff_id": dry_run_request.get("smoke_handoff_id"),
        "source_request_id": dry_run_request.get("source_request_id"),
        "target_profile": dry_run_request.get("target_profile"),
        "status": ACCEPTED_STATUS if request_ready else REJECTED_STATUS,
        "issue_code": None if request_ready else validation.get("issue_code"),
        "execution_policy": "not_executed.hostess_dry_run_receipt_only",
        "adapter_owner": HOSTESS_OWNER,
        "command_session_authority": dry_run_request.get("command_session_authority"),
        "install_launch_evidence_authority": dry_run_request.get("install_launch_evidence_authority"),
        "execution_performed": False,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "requested_step_count": len(steps),
        "accepted_step_count": len(steps) if request_ready else 0,
        "rejected_step_count": 0 if request_ready else len(steps),
        "required_receipt_kinds": dry_run_request.get("required_receipt_kinds", []),
        "receipt_items": receipt_items,
        "checks": validation.get("checks", []),
    }


def validate_smoke_dry_run_request(dry_run_request: dict[str, Any]) -> dict[str, Any]:
    steps = smoke_dry_run_request_steps(dry_run_request)
    embedded_checks = dry_run_request.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_smoke_dry_run_request.schema",
            dry_run_request.get("$schema") == SMOKE_DRY_RUN_REQUEST_SCHEMA,
            "dry-run request schema is supported",
            "dry-run request schema is unsupported",
            "hostess.issue.smoke_dry_run_request_schema",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_request.status",
            dry_run_request.get("status") in {READY_STATUS, BLOCKED_STATUS},
            "dry-run request status is supported",
            "dry-run request status is unsupported",
            "hostess.issue.smoke_dry_run_request_status",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_request.no_runtime_started",
            all(dry_run_request.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS),
            "dry-run request has not started runtime work",
            "dry-run request indicates runtime work started",
            "hostess.issue.smoke_dry_run_runtime_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_request.authority",
            dry_run_request.get("adapter_owner") == HOSTESS_OWNER
            and dry_run_request.get("requester_role") == STUDIO_REQUESTER
            and dry_run_request.get("command_session_authority") == MANIFOLD_OWNER
            and dry_run_request.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and dry_run_request.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_request.receipt_kinds",
            set(dry_run_request.get("required_receipt_kinds", []))
            == set(SMOKE_DRY_RUN_REQUIRED_RECEIPT_KINDS),
            "dry-run request declares required receipt kinds",
            "dry-run request receipt kinds drifted",
            "hostess.issue.smoke_dry_run_receipt_kinds",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_request.step_contracts",
            smoke_dry_run_steps_match_contracts(steps),
            "dry-run steps match owner and route contracts",
            "dry-run steps drifted from owner or route contracts",
            "hostess.issue.smoke_dry_run_step_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_request.no_step_execution",
            all(step.get("execution_started") is False for step in steps),
            "dry-run steps have not started runtime work",
            "dry-run step indicates runtime work started",
            "hostess.issue.smoke_dry_run_step_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_request.ready_consistency",
            dry_run_request.get("status") != READY_STATUS
            or (
                all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(step.get("status") == READY_STATUS for step in steps)
            ),
            "ready dry-run request has passing checks and ready steps",
            "ready dry-run request has failed checks or blocked steps",
            "hostess.issue.smoke_dry_run_ready_inconsistent",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": SMOKE_DRY_RUN_VALIDATION_SCHEMA,
        "fixture_kind": "dry_run_request",
        "dry_run_request_id": dry_run_request.get("dry_run_request_id"),
        "smoke_handoff_id": dry_run_request.get("smoke_handoff_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "checks": checks,
    }


def validate_smoke_dry_run_receipt(
    dry_run_request: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    request_validation = validate_smoke_dry_run_request(dry_run_request)
    request_ready = (
        dry_run_request.get("status") == READY_STATUS and request_validation.get("status") == PASS_STATUS
    )
    receipt_items = receipt.get("receipt_items", [])
    if not isinstance(receipt_items, list):
        receipt_items = []
    receipt_item_dicts = [item for item in receipt_items if isinstance(item, dict)]
    expected_status = ACCEPTED_STATUS if request_ready else REJECTED_STATUS
    checks = [
        check(
            "hostess.check.studio_staging_smoke_dry_run_receipt.schema",
            receipt.get("$schema") == SMOKE_DRY_RUN_RECEIPT_SCHEMA,
            "dry-run receipt schema is supported",
            "dry-run receipt schema is unsupported",
            "hostess.issue.smoke_dry_run_receipt_schema",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_receipt.request_id",
            receipt.get("dry_run_request_id") == dry_run_request.get("dry_run_request_id"),
            "dry-run receipt request id matches",
            "dry-run receipt request id differs",
            "hostess.issue.smoke_dry_run_receipt_request_mismatch",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_receipt.status",
            receipt.get("status") == expected_status,
            "dry-run receipt status matches request readiness",
            "dry-run receipt status differs from request readiness",
            "hostess.issue.smoke_dry_run_receipt_status",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_receipt.no_runtime_started",
            all(receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS),
            "dry-run receipt has not started runtime work",
            "dry-run receipt indicates runtime work started",
            "hostess.issue.smoke_dry_run_runtime_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_receipt.items",
            receipt_items_match_dry_run_steps(dry_run_request, receipt_item_dicts),
            "dry-run receipt items match request steps",
            "dry-run receipt items drifted from request steps",
            "hostess.issue.smoke_dry_run_receipt_item_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run_receipt.no_item_execution",
            all(item.get("execution_performed") is False for item in receipt_item_dicts),
            "dry-run receipt items did not execute runtime work",
            "dry-run receipt item indicates runtime execution",
            "hostess.issue.smoke_dry_run_receipt_item_executed",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": SMOKE_DRY_RUN_VALIDATION_SCHEMA,
        "fixture_kind": "dry_run_receipt",
        "dry_run_request_id": dry_run_request.get("dry_run_request_id"),
        "receipt_id": receipt.get("receipt_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "checks": checks,
    }


def smoke_dry_run_steps(
    smoke_handoff: dict[str, Any],
    handoff_validation: dict[str, Any],
) -> list[dict[str, Any]]:
    source_items = {
        item.get("item_id"): item
        for item in smoke_handoff.get("checklist_items", [])
        if isinstance(item, dict)
    }
    handoff_ready = (
        smoke_handoff.get("status") == READY_STATUS and handoff_validation.get("status") == PASS_STATUS
    )
    steps = []
    for contract in SMOKE_DRY_RUN_STEP_CONTRACTS:
        source_item = source_items.get(contract["source_item_id"])
        issue_code = None
        if not isinstance(source_item, dict):
            issue_code = "hostess.issue.smoke_dry_run_source_item_missing"
        elif not handoff_ready:
            issue_code = (
                smoke_handoff.get("issue_code")
                or handoff_validation.get("issue_code")
                or "hostess.issue.smoke_handoff_not_ready"
            )
        elif source_item.get("status") != READY_STATUS:
            issue_code = source_item.get("issue_code") or "hostess.issue.smoke_handoff_item_blocked"
        steps.append(
            {
                "step_id": contract["step_id"],
                "owner": contract["owner"],
                "status": READY_STATUS if issue_code is None else BLOCKED_STATUS,
                "issue_code": issue_code,
                "source_item_id": contract["source_item_id"],
                "source_route_kind": source_item.get("route_kind") if isinstance(source_item, dict) else None,
                "route_kind": contract["route_kind"],
                "expected_receipt_kind": contract["expected_receipt_kind"],
                "receipt_required": True,
                "execution_started": False,
            }
        )
    return steps


def smoke_dry_run_request_checks(
    smoke_handoff: dict[str, Any],
    handoff_validation: dict[str, Any],
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_smoke_dry_run.handoff_schema",
            smoke_handoff.get("$schema") == SMOKE_HANDOFF_SCHEMA,
            "smoke handoff schema is supported",
            "smoke handoff schema is unsupported",
            "hostess.issue.smoke_handoff_schema",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run.handoff_ready",
            smoke_handoff.get("status") == READY_STATUS
            and handoff_validation.get("status") == PASS_STATUS,
            "smoke handoff is ready and validates",
            "smoke handoff is blocked or invalid",
            smoke_handoff.get("issue_code")
            or handoff_validation.get("issue_code")
            or "hostess.issue.smoke_handoff_not_ready",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run.authority",
            smoke_handoff.get("adapter_owner") == HOSTESS_OWNER
            and smoke_handoff.get("requester_role") == STUDIO_REQUESTER
            and smoke_handoff.get("command_session_authority") == MANIFOLD_OWNER
            and smoke_handoff.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and smoke_handoff.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run.steps_ready",
            all(step.get("status") == READY_STATUS for step in steps),
            "dry-run steps are ready",
            "dry-run steps are blocked",
            first_step_issue_code(steps) or "hostess.issue.smoke_dry_run_steps_blocked",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run.no_step_execution",
            all(step.get("execution_started") is False for step in steps),
            "dry-run steps have not started runtime work",
            "dry-run step indicates runtime work started",
            "hostess.issue.smoke_dry_run_step_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_dry_run.step_contracts",
            smoke_dry_run_steps_match_contracts(steps),
            "dry-run steps match owner and route contracts",
            "dry-run steps drifted from owner or route contracts",
            "hostess.issue.smoke_dry_run_step_contract_drift",
        ),
    ]


def smoke_dry_run_request_steps(dry_run_request: dict[str, Any]) -> list[dict[str, Any]]:
    steps = dry_run_request.get("dry_run_steps", [])
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def smoke_dry_run_steps_match_contracts(steps: list[dict[str, Any]]) -> bool:
    by_id = {step.get("step_id"): step for step in steps}
    for contract in SMOKE_DRY_RUN_STEP_CONTRACTS:
        step = by_id.get(contract["step_id"])
        if not isinstance(step, dict):
            return False
        if step.get("owner") != contract["owner"]:
            return False
        if step.get("source_item_id") != contract["source_item_id"]:
            return False
        if step.get("route_kind") != contract["route_kind"]:
            return False
        if step.get("expected_receipt_kind") != contract["expected_receipt_kind"]:
            return False
        if step.get("receipt_required") is not True:
            return False
    return True


def receipt_items_match_dry_run_steps(
    dry_run_request: dict[str, Any],
    receipt_items: list[dict[str, Any]],
) -> bool:
    steps = smoke_dry_run_request_steps(dry_run_request)
    by_id = {item.get("step_id"): item for item in receipt_items}
    if len(receipt_items) != len(steps):
        return False
    for step in steps:
        item = by_id.get(step.get("step_id"))
        if not isinstance(item, dict):
            return False
        if item.get("owner") != step.get("owner"):
            return False
        if item.get("route_kind") != step.get("route_kind"):
            return False
        if item.get("receipt_kind") != step.get("expected_receipt_kind"):
            return False
    return True


def first_step_issue_code(steps: list[dict[str, Any]]) -> str | None:
    for step in steps:
        issue_code = step.get("issue_code")
        if isinstance(issue_code, str) and issue_code:
            return issue_code
    return None


def build_smoke_execution_preflight(
    dry_run_request: dict[str, Any],
    dry_run_receipt: dict[str, Any],
    target_profile: str | None = None,
    host_shell_kind: str = "hostess.t.no_device_preflight",
) -> dict[str, Any]:
    request_validation = validate_smoke_dry_run_request(dry_run_request)
    receipt_validation = validate_smoke_dry_run_receipt(dry_run_request, dry_run_receipt)
    capabilities = smoke_preflight_capabilities(
        dry_run_request,
        dry_run_receipt,
        request_validation,
        receipt_validation,
    )
    checks = smoke_preflight_checks(
        dry_run_request,
        dry_run_receipt,
        request_validation,
        receipt_validation,
        capabilities,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    dry_run_request_id = dry_run_request.get("dry_run_request_id")
    preflight_id = (
        f"hostess.smoke_execution_preflight.{dry_run_request_id}"
        if isinstance(dry_run_request_id, str) and dry_run_request_id
        else "hostess.smoke_execution_preflight.unknown"
    )

    return {
        "$schema": SMOKE_EXECUTION_PREFLIGHT_SCHEMA,
        "preflight_id": preflight_id,
        "dry_run_request_id": dry_run_request_id,
        "dry_run_receipt_id": dry_run_receipt.get("receipt_id"),
        "smoke_handoff_id": dry_run_request.get("smoke_handoff_id"),
        "source_request_id": dry_run_request.get("source_request_id"),
        "target_profile": target_profile or dry_run_request.get("target_profile"),
        "status": READY_STATUS if not failed else BLOCKED_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_policy": "not_executed.hostess_execution_preflight_only",
        "adapter_owner": HOSTESS_OWNER,
        "requester_role": dry_run_request.get("requester_role"),
        "command_session_authority": dry_run_request.get("command_session_authority"),
        "install_launch_evidence_authority": dry_run_request.get("install_launch_evidence_authority"),
        "studio_role": dry_run_request.get("studio_role"),
        "host_shell_owner": HOSTESS_OWNER,
        "host_shell_kind": host_shell_kind,
        "device_required": False,
        "platform_execution_allowed": False,
        "next_required_action": "hostess_t_or_host_shell_start_platform_smoke_outside_studio",
        "execution_performed": False,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "requested_step_count": dry_run_receipt.get("requested_step_count"),
        "accepted_step_count": dry_run_receipt.get("accepted_step_count"),
        "rejected_step_count": dry_run_receipt.get("rejected_step_count"),
        "required_receipt_kinds": dry_run_request.get("required_receipt_kinds", []),
        "preflight_capabilities": capabilities,
        "checks": checks,
    }


def validate_smoke_execution_preflight(preflight: dict[str, Any]) -> dict[str, Any]:
    capabilities = preflight_capabilities(preflight)
    embedded_checks = preflight.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.schema",
            preflight.get("$schema") == SMOKE_EXECUTION_PREFLIGHT_SCHEMA,
            "smoke execution preflight schema is supported",
            "smoke execution preflight schema is unsupported",
            "hostess.issue.smoke_execution_preflight_schema",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.status",
            preflight.get("status") in {READY_STATUS, BLOCKED_STATUS},
            "smoke execution preflight status is supported",
            "smoke execution preflight status is unsupported",
            "hostess.issue.smoke_execution_preflight_status",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.execution_policy",
            preflight.get("execution_policy") == "not_executed.hostess_execution_preflight_only",
            "smoke execution preflight is schema-only",
            "smoke execution preflight execution policy drifted",
            "hostess.issue.smoke_execution_preflight_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.no_runtime_started",
            all(preflight.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS),
            "smoke execution preflight has not started runtime work",
            "smoke execution preflight indicates runtime work started",
            "hostess.issue.smoke_execution_preflight_runtime_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.no_device",
            preflight.get("device_required") is False
            and preflight.get("platform_execution_allowed") is False,
            "smoke execution preflight is no-device and does not allow platform execution",
            "smoke execution preflight allows device or platform execution",
            "hostess.issue.smoke_execution_preflight_device_gate",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.authority",
            preflight.get("adapter_owner") == HOSTESS_OWNER
            and preflight.get("requester_role") == STUDIO_REQUESTER
            and preflight.get("command_session_authority") == MANIFOLD_OWNER
            and preflight.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and preflight.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.receipt_kinds",
            set(preflight.get("required_receipt_kinds", []))
            == set(SMOKE_DRY_RUN_REQUIRED_RECEIPT_KINDS),
            "smoke execution preflight preserves dry-run receipt kinds",
            "smoke execution preflight receipt kinds drifted",
            "hostess.issue.smoke_execution_preflight_receipt_kinds",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.capability_contracts",
            smoke_preflight_capabilities_match_contracts(capabilities),
            "smoke execution preflight capabilities match owner and route contracts",
            "smoke execution preflight capabilities drifted",
            "hostess.issue.smoke_execution_preflight_capability_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.capabilities_ready",
            preflight.get("status") != READY_STATUS
            or all(capability.get("status") == READY_STATUS for capability in capabilities),
            "ready smoke execution preflight capabilities are ready",
            "ready smoke execution preflight capabilities are blocked",
            first_capability_issue_code(capabilities)
            or "hostess.issue.smoke_execution_preflight_capability_blocked",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.ready_consistency",
            preflight.get("status") != READY_STATUS
            or (
                all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(capability.get("status") == READY_STATUS for capability in capabilities)
            ),
            "ready smoke execution preflight has passing checks and ready capabilities",
            "ready smoke execution preflight has failed checks or blocked capabilities",
            "hostess.issue.smoke_execution_preflight_ready_inconsistent",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": SMOKE_EXECUTION_PREFLIGHT_VALIDATION_SCHEMA,
        "preflight_id": preflight.get("preflight_id"),
        "dry_run_request_id": preflight.get("dry_run_request_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "checks": checks,
    }


def smoke_preflight_capabilities(
    dry_run_request: dict[str, Any],
    dry_run_receipt: dict[str, Any],
    request_validation: dict[str, Any],
    receipt_validation: dict[str, Any],
) -> list[dict[str, Any]]:
    route_kinds = {
        step.get("route_kind")
        for step in smoke_dry_run_request_steps(dry_run_request)
        if isinstance(step.get("route_kind"), str)
    }
    receipt_kinds = {
        item.get("receipt_kind")
        for item in dry_run_receipt.get("receipt_items", [])
        if isinstance(item, dict) and isinstance(item.get("receipt_kind"), str)
    }
    request_ready = (
        dry_run_request.get("status") == READY_STATUS and request_validation.get("status") == PASS_STATUS
    )
    receipt_accepted = (
        dry_run_receipt.get("status") == ACCEPTED_STATUS and receipt_validation.get("status") == PASS_STATUS
    )
    capabilities = []
    for contract in SMOKE_PREFLIGHT_CAPABILITY_CONTRACTS:
        issue_code = None
        if contract["capability_id"] == "hostess.preflight.validate_dry_run_request" and not request_ready:
            issue_code = request_validation.get("issue_code") or "hostess.issue.smoke_dry_run_request_not_ready"
        elif contract["capability_id"] == "hostess.preflight.validate_dry_run_receipt" and not receipt_accepted:
            issue_code = receipt_validation.get("issue_code") or "hostess.issue.smoke_dry_run_receipt_not_accepted"
        elif contract["route_kind"] not in {
            "hostess.preflight.validate_dry_run_request",
            "hostess.preflight.validate_dry_run_receipt",
            "hostess.preflight.no_device_runtime_guard",
        } and contract["route_kind"] not in route_kinds:
            issue_code = "hostess.issue.smoke_execution_preflight_route_missing"
        elif contract["evidence_kind"] not in {
            "hostess_smoke_dry_run_request_validation",
            "hostess_smoke_dry_run_receipt_validation",
            "hostess_smoke_execution_preflight",
        } and contract["evidence_kind"] not in receipt_kinds:
            issue_code = "hostess.issue.smoke_execution_preflight_evidence_missing"
        capabilities.append(
            {
                "capability_id": contract["capability_id"],
                "owner": contract["owner"],
                "status": READY_STATUS if issue_code is None else BLOCKED_STATUS,
                "issue_code": issue_code,
                "route_kind": contract["route_kind"],
                "evidence_kind": contract["evidence_kind"],
                "device_required": False,
                "execution_started": False,
            }
        )
    return capabilities


def smoke_preflight_checks(
    dry_run_request: dict[str, Any],
    dry_run_receipt: dict[str, Any],
    request_validation: dict[str, Any],
    receipt_validation: dict[str, Any],
    capabilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.dry_run_request",
            dry_run_request.get("$schema") == SMOKE_DRY_RUN_REQUEST_SCHEMA
            and dry_run_request.get("status") == READY_STATUS
            and request_validation.get("status") == PASS_STATUS,
            "dry-run request is ready and validates",
            "dry-run request is blocked or invalid",
            dry_run_request.get("issue_code")
            or request_validation.get("issue_code")
            or "hostess.issue.smoke_dry_run_request_not_ready",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.dry_run_receipt",
            dry_run_receipt.get("$schema") == SMOKE_DRY_RUN_RECEIPT_SCHEMA
            and dry_run_receipt.get("status") == ACCEPTED_STATUS
            and receipt_validation.get("status") == PASS_STATUS,
            "dry-run receipt is accepted and validates",
            "dry-run receipt is rejected or invalid",
            dry_run_receipt.get("issue_code")
            or receipt_validation.get("issue_code")
            or "hostess.issue.smoke_dry_run_receipt_not_accepted",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.authority",
            dry_run_request.get("adapter_owner") == HOSTESS_OWNER
            and dry_run_request.get("requester_role") == STUDIO_REQUESTER
            and dry_run_request.get("command_session_authority") == MANIFOLD_OWNER
            and dry_run_request.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and dry_run_request.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.no_runtime_started",
            all(dry_run_request.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and all(dry_run_receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS),
            "preflight inputs have not started runtime work",
            "preflight inputs indicate runtime work started",
            "hostess.issue.smoke_execution_preflight_runtime_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.capabilities_ready",
            all(capability.get("status") == READY_STATUS for capability in capabilities),
            "preflight capabilities are ready",
            "preflight capabilities are blocked",
            first_capability_issue_code(capabilities)
            or "hostess.issue.smoke_execution_preflight_capability_blocked",
        ),
        check(
            "hostess.check.studio_staging_smoke_execution_preflight.capability_contracts",
            smoke_preflight_capabilities_match_contracts(capabilities),
            "preflight capabilities match owner and route contracts",
            "preflight capabilities drifted from owner or route contracts",
            "hostess.issue.smoke_execution_preflight_capability_drift",
        ),
    ]


def preflight_capabilities(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    capabilities = preflight.get("preflight_capabilities", [])
    if not isinstance(capabilities, list):
        return []
    return [capability for capability in capabilities if isinstance(capability, dict)]


def smoke_preflight_capabilities_match_contracts(capabilities: list[dict[str, Any]]) -> bool:
    by_id = {capability.get("capability_id"): capability for capability in capabilities}
    for contract in SMOKE_PREFLIGHT_CAPABILITY_CONTRACTS:
        capability = by_id.get(contract["capability_id"])
        if not isinstance(capability, dict):
            return False
        if capability.get("owner") != contract["owner"]:
            return False
        if capability.get("route_kind") != contract["route_kind"]:
            return False
        if capability.get("evidence_kind") != contract["evidence_kind"]:
            return False
        if capability.get("device_required") is not False:
            return False
        if capability.get("execution_started") is not False:
            return False
    return True


def first_capability_issue_code(capabilities: list[dict[str, Any]]) -> str | None:
    for capability in capabilities:
        issue_code = capability.get("issue_code")
        if isinstance(issue_code, str) and issue_code:
            return issue_code
    return None


def build_smoke_host_shell_execution(preflight: dict[str, Any]) -> dict[str, Any]:
    preflight_validation = validate_smoke_execution_preflight(preflight)
    capabilities = preflight_capabilities(preflight)
    evidence_records = smoke_host_shell_evidence_records(
        preflight,
        preflight_validation,
        capabilities,
    )
    checks = smoke_host_shell_execution_checks(
        preflight,
        preflight_validation,
        capabilities,
        evidence_records,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    preflight_id = preflight.get("preflight_id")
    execution_id = (
        f"hostess.smoke_host_shell_execution.{preflight_id}"
        if isinstance(preflight_id, str) and preflight_id
        else "hostess.smoke_host_shell_execution.unknown"
    )

    accepted_records = [
        record for record in evidence_records if record.get("evidence_status") == ACCEPTED_STATUS
    ]
    rejected_records = [
        record for record in evidence_records if record.get("evidence_status") == REJECTED_STATUS
    ]

    return {
        "$schema": SMOKE_HOST_SHELL_EXECUTION_SCHEMA,
        "execution_id": execution_id,
        "preflight_id": preflight_id,
        "dry_run_request_id": preflight.get("dry_run_request_id"),
        "dry_run_receipt_id": preflight.get("dry_run_receipt_id"),
        "smoke_handoff_id": preflight.get("smoke_handoff_id"),
        "source_request_id": preflight.get("source_request_id"),
        "target_profile": preflight.get("target_profile"),
        "status": COMPLETED_STATUS if not failed else BLOCKED_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_policy": HOST_SHELL_EXECUTION_POLICY,
        "executor_owner": HOSTESS_OWNER,
        "adapter_owner": preflight.get("adapter_owner"),
        "requester_role": preflight.get("requester_role"),
        "command_session_authority": preflight.get("command_session_authority"),
        "install_launch_evidence_authority": preflight.get("install_launch_evidence_authority"),
        "studio_role": preflight.get("studio_role"),
        "host_shell_owner": preflight.get("host_shell_owner"),
        "host_shell_kind": preflight.get("host_shell_kind"),
        "device_required": False,
        "platform_execution_allowed": False,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "host_shell_harness_performed": True,
        "schema_checks_performed": True,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "preflight_status": preflight.get("status"),
        "preflight_validation_status": preflight_validation.get("status"),
        "preflight_issue_code": preflight.get("issue_code") or preflight_validation.get("issue_code"),
        "preflight_capabilities": capabilities,
        "evidence_record_count": len(evidence_records),
        "accepted_evidence_record_count": len(accepted_records),
        "rejected_evidence_record_count": len(rejected_records),
        "evidence_records": evidence_records,
        "checks": checks,
        "next_required_action": (
            "hostess_t_operator_review_before_platform_smoke_outside_studio"
            if not failed
            else "repair_hostess_smoke_execution_preflight"
        ),
    }


def validate_smoke_host_shell_execution(execution: dict[str, Any]) -> dict[str, Any]:
    capabilities = preflight_capabilities(execution)
    records = smoke_host_shell_execution_evidence_records(execution)
    embedded_checks = execution.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    accepted_records = [
        record for record in records if record.get("evidence_status") == ACCEPTED_STATUS
    ]
    rejected_records = [
        record for record in records if record.get("evidence_status") == REJECTED_STATUS
    ]
    checks = [
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.schema",
            execution.get("$schema") == SMOKE_HOST_SHELL_EXECUTION_SCHEMA,
            "smoke host-shell execution schema is supported",
            "smoke host-shell execution schema is unsupported",
            "hostess.issue.smoke_host_shell_execution_schema",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.status",
            execution.get("status") in {COMPLETED_STATUS, BLOCKED_STATUS},
            "smoke host-shell execution status is supported",
            "smoke host-shell execution status is unsupported",
            "hostess.issue.smoke_host_shell_execution_status",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.execution_policy",
            execution.get("execution_policy") == HOST_SHELL_EXECUTION_POLICY,
            "smoke host-shell execution is no-device schema execution only",
            "smoke host-shell execution policy drifted",
            "hostess.issue.smoke_host_shell_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.no_runtime_started",
            all(execution.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and execution.get("runtime_execution_performed") is False
            and execution.get("platform_execution_performed") is False,
            "smoke host-shell execution did not start runtime or platform work",
            "smoke host-shell execution indicates runtime or platform work started",
            "hostess.issue.smoke_host_shell_execution_runtime_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.no_device",
            execution.get("device_required") is False
            and execution.get("platform_execution_allowed") is False,
            "smoke host-shell execution is no-device",
            "smoke host-shell execution allows device or platform execution",
            "hostess.issue.smoke_host_shell_execution_device_gate",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.authority",
            execution.get("executor_owner") == HOSTESS_OWNER
            and execution.get("adapter_owner") == HOSTESS_OWNER
            and execution.get("requester_role") == STUDIO_REQUESTER
            and execution.get("command_session_authority") == MANIFOLD_OWNER
            and execution.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and execution.get("studio_role") == STUDIO_ROLE
            and execution.get("host_shell_owner") == HOSTESS_OWNER,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.harness",
            execution.get("host_shell_harness_performed") is True
            and execution.get("schema_checks_performed") is True,
            "Hostess host-shell harness performed schema checks",
            "Hostess host-shell harness did not record schema checks",
            "hostess.issue.smoke_host_shell_harness_not_performed",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.evidence_counts",
            execution.get("evidence_record_count") == len(records)
            and execution.get("accepted_evidence_record_count") == len(accepted_records)
            and execution.get("rejected_evidence_record_count") == len(rejected_records),
            "smoke host-shell evidence counts match records",
            "smoke host-shell evidence counts drifted",
            "hostess.issue.smoke_host_shell_evidence_count_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.evidence_contracts",
            smoke_host_shell_evidence_records_match_capabilities(capabilities, records),
            "smoke host-shell evidence records match capability contracts",
            "smoke host-shell evidence records drifted",
            "hostess.issue.smoke_host_shell_evidence_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.completed_consistency",
            execution.get("status") != COMPLETED_STATUS
            or (
                execution.get("preflight_status") == READY_STATUS
                and execution.get("preflight_validation_status") == PASS_STATUS
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(record.get("evidence_status") == ACCEPTED_STATUS for record in records)
            ),
            "completed smoke host-shell execution has passing checks and accepted evidence",
            "completed smoke host-shell execution has failed checks or rejected evidence",
            "hostess.issue.smoke_host_shell_completed_inconsistent",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": SMOKE_HOST_SHELL_EXECUTION_VALIDATION_SCHEMA,
        "execution_id": execution.get("execution_id"),
        "preflight_id": execution.get("preflight_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def smoke_host_shell_evidence_records(
    preflight: dict[str, Any],
    preflight_validation: dict[str, Any],
    capabilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    preflight_ready = (
        preflight.get("status") == READY_STATUS
        and preflight_validation.get("status") == PASS_STATUS
        and all(capability.get("status") == READY_STATUS for capability in capabilities)
    )
    records = []
    for capability in capabilities:
        capability_id = capability.get("capability_id")
        issue_code = None
        if not preflight_ready:
            issue_code = (
                capability.get("issue_code")
                or preflight.get("issue_code")
                or preflight_validation.get("issue_code")
                or "hostess.issue.smoke_execution_preflight_not_ready"
            )
        records.append(
            {
                "evidence_id": (
                    f"hostess.smoke_host_shell_evidence.{capability_id}"
                    if isinstance(capability_id, str) and capability_id
                    else "hostess.smoke_host_shell_evidence.unknown"
                ),
                "owner": capability.get("owner"),
                "source_capability_id": capability_id,
                "route_kind": capability.get("route_kind"),
                "evidence_kind": capability.get("evidence_kind"),
                "evidence_status": ACCEPTED_STATUS if issue_code is None else REJECTED_STATUS,
                "issue_code": issue_code,
                "device_required": False,
                "schema_check_performed": True,
                "platform_execution_performed": False,
                "runtime_execution_performed": False,
                "command_session_started": False,
            }
        )
    return records


def smoke_host_shell_execution_checks(
    preflight: dict[str, Any],
    preflight_validation: dict[str, Any],
    capabilities: list[dict[str, Any]],
    evidence_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.preflight",
            preflight.get("$schema") == SMOKE_EXECUTION_PREFLIGHT_SCHEMA
            and preflight.get("status") == READY_STATUS
            and preflight_validation.get("status") == PASS_STATUS,
            "smoke execution preflight is ready and validates",
            "smoke execution preflight is blocked or invalid",
            preflight.get("issue_code")
            or preflight_validation.get("issue_code")
            or "hostess.issue.smoke_execution_preflight_not_ready",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.authority",
            preflight.get("adapter_owner") == HOSTESS_OWNER
            and preflight.get("requester_role") == STUDIO_REQUESTER
            and preflight.get("command_session_authority") == MANIFOLD_OWNER
            and preflight.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and preflight.get("studio_role") == STUDIO_ROLE
            and preflight.get("host_shell_owner") == HOSTESS_OWNER,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.no_device",
            preflight.get("device_required") is False
            and preflight.get("platform_execution_allowed") is False,
            "preflight is no-device and does not allow platform execution",
            "preflight allows device or platform execution",
            "hostess.issue.smoke_host_shell_execution_device_gate",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.no_runtime_started",
            all(preflight.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS),
            "preflight has not started runtime work",
            "preflight indicates runtime work started",
            "hostess.issue.smoke_host_shell_execution_runtime_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.capability_contracts",
            smoke_preflight_capabilities_match_contracts(capabilities),
            "preflight capabilities match owner and route contracts",
            "preflight capabilities drifted",
            "hostess.issue.smoke_execution_preflight_capability_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.evidence_contracts",
            smoke_host_shell_evidence_records_match_capabilities(capabilities, evidence_records),
            "host-shell evidence records match capability contracts",
            "host-shell evidence records drifted",
            "hostess.issue.smoke_host_shell_evidence_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_host_shell_execution.evidence_accepted",
            all(record.get("evidence_status") == ACCEPTED_STATUS for record in evidence_records),
            "host-shell evidence records are accepted",
            "host-shell evidence records are rejected",
            first_evidence_issue_code(evidence_records)
            or "hostess.issue.smoke_host_shell_evidence_rejected",
        ),
    ]


def smoke_host_shell_execution_evidence_records(execution: dict[str, Any]) -> list[dict[str, Any]]:
    records = execution.get("evidence_records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def smoke_host_shell_evidence_records_match_capabilities(
    capabilities: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> bool:
    by_id = {record.get("source_capability_id"): record for record in records}
    if len(records) != len(capabilities):
        return False
    for capability in capabilities:
        capability_id = capability.get("capability_id")
        record = by_id.get(capability_id)
        if not isinstance(record, dict):
            return False
        if record.get("owner") != capability.get("owner"):
            return False
        if record.get("route_kind") != capability.get("route_kind"):
            return False
        if record.get("evidence_kind") != capability.get("evidence_kind"):
            return False
        if record.get("device_required") is not False:
            return False
        if record.get("schema_check_performed") is not True:
            return False
        if record.get("platform_execution_performed") is not False:
            return False
        if record.get("runtime_execution_performed") is not False:
            return False
        if record.get("command_session_started") is not False:
            return False
    return True


def first_evidence_issue_code(records: list[dict[str, Any]]) -> str | None:
    for record in records:
        issue_code = record.get("issue_code")
        if isinstance(issue_code, str) and issue_code:
            return issue_code
    return None


def build_smoke_review_bundle(execution: dict[str, Any]) -> dict[str, Any]:
    execution_validation = validate_smoke_host_shell_execution(execution)
    source_records = smoke_host_shell_execution_evidence_records(execution)
    bundle_records = smoke_review_bundle_records(
        execution,
        execution_validation,
        source_records,
    )
    checks = smoke_review_bundle_checks(
        execution,
        execution_validation,
        source_records,
        bundle_records,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    execution_id = execution.get("execution_id")
    bundle_id = (
        f"hostess.smoke_review_bundle.{execution_id}"
        if isinstance(execution_id, str) and execution_id
        else "hostess.smoke_review_bundle.unknown"
    )
    reviewed_records = [
        record for record in bundle_records if record.get("review_status") == REVIEWED_STATUS
    ]
    blocked_records = [
        record for record in bundle_records if record.get("review_status") == BLOCKED_STATUS
    ]

    return {
        "$schema": SMOKE_REVIEW_BUNDLE_SCHEMA,
        "bundle_id": bundle_id,
        "source_execution_id": execution_id,
        "preflight_id": execution.get("preflight_id"),
        "dry_run_request_id": execution.get("dry_run_request_id"),
        "dry_run_receipt_id": execution.get("dry_run_receipt_id"),
        "smoke_handoff_id": execution.get("smoke_handoff_id"),
        "source_request_id": execution.get("source_request_id"),
        "target_profile": execution.get("target_profile"),
        "status": REVIEWED_STATUS if not failed else BLOCKED_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_policy": SMOKE_REVIEW_BUNDLE_POLICY,
        "bundle_owner": HOSTESS_OWNER,
        "reviewer_owner": HOSTESS_OWNER,
        "executor_owner": execution.get("executor_owner"),
        "adapter_owner": execution.get("adapter_owner"),
        "requester_role": execution.get("requester_role"),
        "command_session_authority": execution.get("command_session_authority"),
        "install_launch_evidence_authority": execution.get("install_launch_evidence_authority"),
        "studio_role": execution.get("studio_role"),
        "host_shell_owner": execution.get("host_shell_owner"),
        "host_shell_kind": execution.get("host_shell_kind"),
        "device_required": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "operator_review_required_before_platform_smoke": True,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "review_bundle_written": True,
        "host_shell_harness_performed": execution.get("host_shell_harness_performed") is True,
        "schema_checks_performed": execution.get("schema_checks_performed") is True,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "source_execution_status": execution.get("status"),
        "source_execution_validation_status": execution_validation.get("status"),
        "source_execution_issue_code": execution.get("issue_code") or execution_validation.get("issue_code"),
        "source_evidence_record_count": len(source_records),
        "bundle_record_count": len(bundle_records),
        "reviewed_record_count": len(reviewed_records),
        "blocked_record_count": len(blocked_records),
        "source_evidence_records": source_records,
        "bundle_records": bundle_records,
        "checks": checks,
        "next_required_action": (
            "operator_review_platform_smoke_plan_outside_studio"
            if not failed
            else "repair_hostess_no_device_smoke_harness"
        ),
    }


def validate_smoke_review_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    source_records = smoke_review_bundle_source_records(bundle)
    bundle_records = smoke_review_bundle_record_dicts(bundle)
    embedded_checks = bundle.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    reviewed_records = [
        record for record in bundle_records if record.get("review_status") == REVIEWED_STATUS
    ]
    blocked_records = [
        record for record in bundle_records if record.get("review_status") == BLOCKED_STATUS
    ]
    checks = [
        check(
            "hostess.check.studio_staging_smoke_review_bundle.schema",
            bundle.get("$schema") == SMOKE_REVIEW_BUNDLE_SCHEMA,
            "smoke review bundle schema is supported",
            "smoke review bundle schema is unsupported",
            "hostess.issue.smoke_review_bundle_schema",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.status",
            bundle.get("status") in {REVIEWED_STATUS, BLOCKED_STATUS},
            "smoke review bundle status is supported",
            "smoke review bundle status is unsupported",
            "hostess.issue.smoke_review_bundle_status",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.execution_policy",
            bundle.get("execution_policy") == SMOKE_REVIEW_BUNDLE_POLICY,
            "smoke review bundle is no-device review-only",
            "smoke review bundle execution policy drifted",
            "hostess.issue.smoke_review_bundle_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.no_runtime_started",
            all(bundle.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and bundle.get("runtime_execution_performed") is False
            and bundle.get("platform_execution_performed") is False,
            "smoke review bundle did not start runtime or platform work",
            "smoke review bundle indicates runtime or platform work started",
            "hostess.issue.smoke_review_bundle_runtime_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.no_device",
            bundle.get("device_required") is False
            and bundle.get("platform_execution_allowed") is False
            and bundle.get("studio_execution_allowed") is False,
            "smoke review bundle keeps device and Studio execution disabled",
            "smoke review bundle allows device, platform, or Studio execution",
            "hostess.issue.smoke_review_bundle_device_gate",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.authority",
            bundle.get("bundle_owner") == HOSTESS_OWNER
            and bundle.get("reviewer_owner") == HOSTESS_OWNER
            and bundle.get("executor_owner") == HOSTESS_OWNER
            and bundle.get("adapter_owner") == HOSTESS_OWNER
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
            "hostess.check.studio_staging_smoke_review_bundle.source_execution",
            bundle.get("status") != REVIEWED_STATUS
            or (
                bundle.get("source_execution_status") == COMPLETED_STATUS
                and bundle.get("source_execution_validation_status") == PASS_STATUS
            ),
            "reviewed source host-shell execution completed and validates",
            "source host-shell execution is blocked or invalid",
            bundle.get("source_execution_issue_code")
            or "hostess.issue.smoke_host_shell_execution_not_completed",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.counts",
            bundle.get("source_evidence_record_count") == len(source_records)
            and bundle.get("bundle_record_count") == len(bundle_records)
            and bundle.get("reviewed_record_count") == len(reviewed_records)
            and bundle.get("blocked_record_count") == len(blocked_records),
            "smoke review bundle counts match records",
            "smoke review bundle counts drifted",
            "hostess.issue.smoke_review_bundle_count_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.records",
            smoke_review_bundle_records_match_source(source_records, bundle_records),
            "smoke review bundle records match source evidence records",
            "smoke review bundle records drifted from source evidence",
            "hostess.issue.smoke_review_bundle_record_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.reviewed_consistency",
            bundle.get("status") != REVIEWED_STATUS
            or (
                all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(record.get("review_status") == REVIEWED_STATUS for record in bundle_records)
                and all(record.get("included_in_bundle") is True for record in bundle_records)
            ),
            "reviewed smoke bundle has passing checks and reviewed included records",
            "reviewed smoke bundle has failed checks or unreviewed records",
            "hostess.issue.smoke_review_bundle_reviewed_inconsistent",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": SMOKE_REVIEW_BUNDLE_VALIDATION_SCHEMA,
        "bundle_id": bundle.get("bundle_id"),
        "source_execution_id": bundle.get("source_execution_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def smoke_review_bundle_records(
    execution: dict[str, Any],
    execution_validation: dict[str, Any],
    source_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    execution_ready = (
        execution.get("status") == COMPLETED_STATUS
        and execution_validation.get("status") == PASS_STATUS
        and all(record.get("evidence_status") == ACCEPTED_STATUS for record in source_records)
    )
    records = []
    for source in source_records:
        source_evidence_id = source.get("evidence_id")
        issue_code = None
        if not execution_ready:
            issue_code = (
                source.get("issue_code")
                or execution.get("issue_code")
                or execution_validation.get("issue_code")
                or "hostess.issue.smoke_host_shell_execution_not_completed"
            )
        records.append(
            {
                "bundle_record_id": (
                    f"hostess.smoke_review_bundle_record.{source_evidence_id}"
                    if isinstance(source_evidence_id, str) and source_evidence_id
                    else "hostess.smoke_review_bundle_record.unknown"
                ),
                "source_evidence_id": source_evidence_id,
                "owner": source.get("owner"),
                "source_capability_id": source.get("source_capability_id"),
                "route_kind": source.get("route_kind"),
                "evidence_kind": source.get("evidence_kind"),
                "source_evidence_status": source.get("evidence_status"),
                "review_status": REVIEWED_STATUS if issue_code is None else BLOCKED_STATUS,
                "issue_code": issue_code,
                "included_in_bundle": issue_code is None,
                "device_required": False,
                "schema_check_performed": True,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "command_session_started": False,
            }
        )
    return records


def smoke_review_bundle_checks(
    execution: dict[str, Any],
    execution_validation: dict[str, Any],
    source_records: list[dict[str, Any]],
    bundle_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_smoke_review_bundle.source_execution",
            execution.get("$schema") == SMOKE_HOST_SHELL_EXECUTION_SCHEMA
            and execution.get("status") == COMPLETED_STATUS
            and execution_validation.get("status") == PASS_STATUS,
            "source host-shell execution completed and validates",
            "source host-shell execution is blocked or invalid",
            execution.get("issue_code")
            or execution_validation.get("issue_code")
            or "hostess.issue.smoke_host_shell_execution_not_completed",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.authority",
            execution.get("executor_owner") == HOSTESS_OWNER
            and execution.get("adapter_owner") == HOSTESS_OWNER
            and execution.get("requester_role") == STUDIO_REQUESTER
            and execution.get("command_session_authority") == MANIFOLD_OWNER
            and execution.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and execution.get("studio_role") == STUDIO_ROLE
            and execution.get("host_shell_owner") == HOSTESS_OWNER,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.no_runtime_started",
            all(execution.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and execution.get("runtime_execution_performed") is False
            and execution.get("platform_execution_performed") is False,
            "source host-shell execution did not start runtime or platform work",
            "source host-shell execution indicates runtime or platform work started",
            "hostess.issue.smoke_review_bundle_runtime_started",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.records",
            smoke_review_bundle_records_match_source(source_records, bundle_records),
            "bundle records match source evidence records",
            "bundle records drifted from source evidence records",
            "hostess.issue.smoke_review_bundle_record_drift",
        ),
        check(
            "hostess.check.studio_staging_smoke_review_bundle.records_reviewed",
            all(record.get("review_status") == REVIEWED_STATUS for record in bundle_records),
            "bundle records are reviewed",
            "bundle records are blocked",
            first_bundle_record_issue_code(bundle_records)
            or "hostess.issue.smoke_review_bundle_records_blocked",
        ),
    ]


def smoke_review_bundle_source_records(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    records = bundle.get("source_evidence_records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def smoke_review_bundle_record_dicts(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    records = bundle.get("bundle_records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def smoke_review_bundle_records_match_source(
    source_records: list[dict[str, Any]],
    bundle_records: list[dict[str, Any]],
) -> bool:
    by_id = {record.get("source_evidence_id"): record for record in bundle_records}
    if len(bundle_records) != len(source_records):
        return False
    for source in source_records:
        source_evidence_id = source.get("evidence_id")
        record = by_id.get(source_evidence_id)
        if not isinstance(record, dict):
            return False
        if record.get("owner") != source.get("owner"):
            return False
        if record.get("source_capability_id") != source.get("source_capability_id"):
            return False
        if record.get("route_kind") != source.get("route_kind"):
            return False
        if record.get("evidence_kind") != source.get("evidence_kind"):
            return False
        if record.get("source_evidence_status") != source.get("evidence_status"):
            return False
        if record.get("device_required") is not False:
            return False
        if record.get("schema_check_performed") is not True:
            return False
        if record.get("runtime_execution_performed") is not False:
            return False
        if record.get("platform_execution_performed") is not False:
            return False
        if record.get("command_session_started") is not False:
            return False
    return True


def first_bundle_record_issue_code(records: list[dict[str, Any]]) -> str | None:
    for record in records:
        issue_code = record.get("issue_code")
        if isinstance(issue_code, str) and issue_code:
            return issue_code
    return None


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


def validate_ack_fixture(request: dict[str, Any], ack: dict[str, Any]) -> dict[str, Any]:
    checks = [
        check(
            "hostess.check.studio_staging_ack.schema",
            ack.get("$schema") == ACK_SCHEMA,
            "ack schema is supported",
            "ack schema is unsupported",
            "hostess.issue.staging_ack_schema",
        ),
        check(
            "hostess.check.studio_staging_ack.request_id",
            ack.get("request_id") == request.get("request_id"),
            "ack request id matches request",
            "ack request id differs from request",
            "hostess.issue.staging_ack_request_mismatch",
        ),
        check(
            "hostess.check.studio_staging_ack.owner",
            ack.get("accepted_by") == HOSTESS_OWNER,
            "ack is owned by Hostess",
            "ack owner is not Hostess",
            "hostess.issue.staging_ack_owner",
        ),
        check(
            "hostess.check.studio_staging_ack.status",
            ack.get("ack_status") == ACCEPTED_STATUS,
            "ack status is accepted",
            "ack status is not accepted",
            "hostess.issue.staging_ack_status",
        ),
        check(
            "hostess.check.studio_staging_ack.no_studio_execution",
            ack.get("execution_in_studio") is False,
            "ack confirms Studio did not execute runtime actions",
            "ack allows Studio runtime execution",
            "hostess.issue.studio_execution_not_allowed",
        ),
        check(
            "hostess.check.studio_staging_ack.authority",
            ack.get("command_session_authority") == MANIFOLD_OWNER
            and ack.get("install_launch_evidence_authority") == HOSTESS_OWNER,
            "ack preserves Manifold and Hostess authority",
            "ack authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_ack.actions",
            ack.get("required_action_ids") == expected_action_ids(request)
            and ack.get("accepted_action_ids") == expected_action_ids(request),
            "ack accepts exactly the requested adapter actions",
            "ack action ids differ from request actions",
            "hostess.issue.staging_ack_action_mismatch",
        ),
        check(
            "hostess.check.studio_staging_ack.evidence_kinds",
            set(ack.get("required_evidence_kinds", [])) == set(REQUIRED_EVIDENCE_KINDS),
            "ack declares required evidence kinds",
            "ack evidence kinds differ from Hostess contract",
            "hostess.issue.staging_ack_evidence_kinds",
        ),
    ]
    return fixture_validation_report("ack", request, checks)


def validate_reject_fixture(request: dict[str, Any], reject: dict[str, Any]) -> dict[str, Any]:
    checks = [
        check(
            "hostess.check.studio_staging_reject.schema",
            reject.get("$schema") == REJECT_SCHEMA,
            "reject schema is supported",
            "reject schema is unsupported",
            "hostess.issue.staging_reject_schema",
        ),
        check(
            "hostess.check.studio_staging_reject.request_id",
            reject.get("request_id") == request.get("request_id"),
            "reject request id matches request",
            "reject request id differs from request",
            "hostess.issue.staging_reject_request_mismatch",
        ),
        check(
            "hostess.check.studio_staging_reject.owner",
            reject.get("rejected_by") == HOSTESS_OWNER,
            "reject is owned by Hostess",
            "reject owner is not Hostess",
            "hostess.issue.staging_reject_owner",
        ),
        check(
            "hostess.check.studio_staging_reject.status",
            reject.get("reject_status") == REJECTED_STATUS,
            "reject status is rejected",
            "reject status is not rejected",
            "hostess.issue.staging_reject_status",
        ),
        check(
            "hostess.check.studio_staging_reject.no_studio_execution",
            reject.get("execution_in_studio") is False,
            "reject confirms Studio did not execute runtime actions",
            "reject allows Studio runtime execution",
            "hostess.issue.studio_execution_not_allowed",
        ),
        check(
            "hostess.check.studio_staging_reject.actions",
            reject.get("request_action_ids") == expected_action_ids(request)
            and reject.get("rejected_action_ids") == expected_action_ids(request),
            "reject names exactly the requested adapter actions",
            "reject action ids differ from request actions",
            "hostess.issue.staging_reject_action_mismatch",
        ),
        check(
            "hostess.check.studio_staging_reject.reason",
            isinstance(reject.get("reason_code"), str) and bool(reject.get("reason_code")),
            "reject carries a reason code",
            "reject is missing a reason code",
            "hostess.issue.staging_reject_reason_missing",
        ),
    ]
    return fixture_validation_report("reject", request, checks)


def request_checks(request: dict[str, Any]) -> list[dict[str, Any]]:
    actions = request_actions(request)
    action_ids = expected_action_ids(request)
    ready_actions = [action for action in actions if action.get("status") == READY_STATUS]
    blocked_actions = [action for action in actions if action.get("status") == "blocked"]
    template_ack = request.get("ack_template", {})
    template_reject = request.get("reject_template", {})

    checks = [
        check(
            "hostess.check.studio_staging_request.schema",
            request.get("$schema") == REQUEST_SCHEMA,
            "Studio request schema is supported",
            "Studio request schema is unsupported",
            "hostess.issue.staging_request_schema",
        ),
        check(
            "hostess.check.studio_staging_request.status",
            request.get("status") == READY_STATUS and request.get("issue_code") is None,
            "Studio request is ready",
            "Studio request is not ready",
            request.get("issue_code") or "hostess.issue.staging_request_not_ready",
        ),
        check(
            "hostess.check.studio_staging_request.execution_policy",
            request.get("execution_policy") == REQUEST_POLICY,
            "request remains Hostess-request-only",
            "request execution policy changed",
            "hostess.issue.staging_request_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_request.authority",
            request.get("adapter_owner") == HOSTESS_OWNER
            and request.get("requester_role") == STUDIO_REQUESTER
            and request.get("command_session_authority") == MANIFOLD_OWNER
            and request.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and request.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_request.prohibited_studio_actions",
            all(action in request.get("prohibited_studio_actions", []) for action in REQUIRED_PROHIBITED_ACTIONS),
            "request preserves prohibited Studio runtime actions",
            "request is missing prohibited Studio runtime actions",
            "hostess.issue.prohibited_studio_actions_missing",
        ),
        check(
            "hostess.check.studio_staging_request.action_counts",
            request.get("adapter_action_count") == len(actions)
            and request.get("ready_adapter_action_count") == len(ready_actions)
            and request.get("blocked_adapter_action_count") == len(blocked_actions),
            "adapter action counts match actions",
            "adapter action counts do not match actions",
            "hostess.issue.staging_request_action_count_mismatch",
        ),
        check(
            "hostess.check.studio_staging_request.action_contracts",
            actions_match_contracts(actions),
            "adapter actions match Hostess and Manifold request contracts",
            "adapter action owner, route, ack, status, or execution fields drifted",
            "hostess.issue.adapter_action_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_request.ack_template",
            isinstance(template_ack, dict)
            and template_ack.get("$schema") == ACK_SCHEMA
            and template_ack.get("request_id") == request.get("request_id")
            and template_ack.get("accepted_by") == HOSTESS_OWNER
            and template_ack.get("ack_status") == PENDING_STATUS
            and template_ack.get("execution_in_studio") is False
            and template_ack.get("required_action_ids") == action_ids
            and template_ack.get("accepted_action_ids") == []
            and set(template_ack.get("required_evidence_kinds", [])) == set(REQUIRED_EVIDENCE_KINDS),
            "ack template is pending, Hostess-owned, and action complete",
            "ack template drifted from Hostess contract",
            "hostess.issue.staging_ack_template_drift",
        ),
        check(
            "hostess.check.studio_staging_request.reject_template",
            isinstance(template_reject, dict)
            and template_reject.get("$schema") == REJECT_SCHEMA
            and template_reject.get("request_id") == request.get("request_id")
            and template_reject.get("rejected_by") == HOSTESS_OWNER
            and template_reject.get("reject_status") == PENDING_STATUS
            and template_reject.get("execution_in_studio") is False
            and template_reject.get("request_action_ids") == action_ids
            and template_reject.get("rejected_action_ids") == []
            and template_reject.get("next_required_action")
            == "hostess_ack_or_reject_request_outside_studio",
            "reject template is pending, Hostess-owned, and action complete",
            "reject template drifted from Hostess contract",
            "hostess.issue.staging_reject_template_drift",
        ),
    ]
    return checks


def actions_match_contracts(actions: list[dict[str, Any]]) -> bool:
    if not actions:
        return False
    for action in actions:
        action_id = action.get("action_id")
        owner = action.get("owner")
        route = action.get("route_kind")
        expected_route = HOSTESS_ACTION_ROUTES.get(action_id) or MANIFOLD_ACTION_ROUTES.get(action_id)
        expected_owner = MANIFOLD_OWNER if action_id in MANIFOLD_ACTION_ROUTES else HOSTESS_OWNER
        if action_id not in HOSTESS_ACTION_ROUTES and action_id not in MANIFOLD_ACTION_ROUTES:
            return False
        if owner != expected_owner or action.get("responsible_authority") != owner:
            return False
        if route != expected_route:
            return False
        if action.get("status") != READY_STATUS:
            return False
        if action.get("ack_required") is not True:
            return False
        if action.get("execution_in_studio") is not False:
            return False
    return True


def request_actions(request: dict[str, Any]) -> list[dict[str, Any]]:
    actions = request.get("actions", [])
    if not isinstance(actions, list):
        return []
    return [action for action in actions if isinstance(action, dict)]


def expected_action_ids(request: dict[str, Any]) -> list[str]:
    return [
        action["action_id"]
        for action in request_actions(request)
        if isinstance(action.get("action_id"), str)
    ]


def fixture_validation_report(
    fixture_kind: str,
    request: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": "rusty.hostess.studio_staging_execution_fixture_validation.v1",
        "fixture_kind": fixture_kind,
        "request_id": request.get("request_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "checks": checks,
    }


def check(
    check_id: str,
    condition: bool,
    pass_evidence: str,
    fail_evidence: str,
    issue_code: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": PASS_STATUS if condition else FAIL_STATUS,
        "evidence": pass_evidence if condition else fail_evidence,
        "issue_code": None if condition else issue_code,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="studio-staging-request",
        description="Validate Studio staging execution requests without executing Hostess runtime actions.",
    )
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--report-out", type=Path)
    parser.add_argument("--ack-out", type=Path)
    parser.add_argument("--reject-out", type=Path)
    parser.add_argument("--smoke-handoff-in", type=Path)
    parser.add_argument("--smoke-handoff-out", type=Path)
    parser.add_argument("--smoke-dry-run-request-in", type=Path)
    parser.add_argument("--smoke-dry-run-request-out", type=Path)
    parser.add_argument("--smoke-dry-run-receipt-in", type=Path)
    parser.add_argument("--smoke-dry-run-receipt-out", type=Path)
    parser.add_argument("--smoke-preflight-in", type=Path)
    parser.add_argument("--smoke-preflight-out", type=Path)
    parser.add_argument("--smoke-host-shell-execution-in", type=Path)
    parser.add_argument("--smoke-host-shell-execution-out", type=Path)
    parser.add_argument("--smoke-review-bundle-in", type=Path)
    parser.add_argument("--smoke-review-bundle-out", type=Path)
    parser.add_argument("--platform-smoke-plan-out", type=Path)
    parser.add_argument("--target-profile", default="hostess.t.schema_smoke")
    parser.add_argument("--target-platform", default="hostess.platform_smoke.operator_controlled")
    parser.add_argument("--validate-ack", type=Path)
    parser.add_argument("--validate-reject", type=Path)
    parser.add_argument("--validate-smoke-handoff", type=Path)
    parser.add_argument("--validate-smoke-dry-run-request", type=Path)
    parser.add_argument("--validate-smoke-dry-run-receipt", type=Path)
    parser.add_argument("--validate-smoke-preflight", type=Path)
    parser.add_argument("--validate-smoke-host-shell-execution", type=Path)
    parser.add_argument("--validate-smoke-review-bundle", type=Path)
    parser.add_argument("--validate-platform-smoke-plan", type=Path)
    args = parser.parse_args()

    request = load_json(args.request)
    report = build_intake_report(request, args.request)
    ack_fixture = build_ack_fixture(request) if report["status"] == ACCEPTED_STATUS else None
    smoke_handoff = load_json(args.smoke_handoff_in) if args.smoke_handoff_in else None
    dry_run_request = load_json(args.smoke_dry_run_request_in) if args.smoke_dry_run_request_in else None
    dry_run_receipt = load_json(args.smoke_dry_run_receipt_in) if args.smoke_dry_run_receipt_in else None
    smoke_preflight = load_json(args.smoke_preflight_in) if args.smoke_preflight_in else None
    host_shell_execution = (
        load_json(args.smoke_host_shell_execution_in) if args.smoke_host_shell_execution_in else None
    )
    smoke_review_bundle = load_json(args.smoke_review_bundle_in) if args.smoke_review_bundle_in else None
    if args.report_out:
        write_json(args.report_out, report)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    if args.ack_out and ack_fixture is not None:
        write_json(args.ack_out, ack_fixture)
    if args.reject_out:
        write_json(args.reject_out, build_reject_fixture(request))
    if args.smoke_handoff_out:
        if smoke_handoff is None:
            smoke_handoff = build_smoke_handoff_checklist(
                request,
                report,
                ack_fixture,
                target_profile=args.target_profile,
            )
        write_json(
            args.smoke_handoff_out,
            smoke_handoff,
        )
    if (
        args.smoke_dry_run_request_out
        or args.smoke_dry_run_receipt_out
        or args.smoke_preflight_out
        or args.smoke_host_shell_execution_out
        or args.smoke_review_bundle_out
        or args.platform_smoke_plan_out
    ):
        if smoke_handoff is None:
            smoke_handoff = build_smoke_handoff_checklist(
                request,
                report,
                ack_fixture,
                target_profile=args.target_profile,
            )
        if dry_run_request is None:
            dry_run_request = build_smoke_dry_run_request(
                smoke_handoff,
                target_profile=args.target_profile,
            )
        if args.smoke_dry_run_request_out:
            write_json(args.smoke_dry_run_request_out, dry_run_request)
        if args.smoke_dry_run_receipt_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            write_json(args.smoke_dry_run_receipt_out, dry_run_receipt)
        if args.smoke_preflight_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            write_json(
                args.smoke_preflight_out,
                smoke_preflight,
            )
        if args.smoke_host_shell_execution_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            write_json(
                args.smoke_host_shell_execution_out,
                host_shell_execution,
            )
        if args.smoke_review_bundle_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            write_json(
                args.smoke_review_bundle_out,
                smoke_review_bundle,
            )
        if args.platform_smoke_plan_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            write_json(
                args.platform_smoke_plan_out,
                build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                ),
            )
    if args.validate_ack:
        ack_report = validate_ack_fixture(request, load_json(args.validate_ack))
        write_json(args.validate_ack.with_suffix(args.validate_ack.suffix + ".validation.json"), ack_report)
    if args.validate_reject:
        reject_report = validate_reject_fixture(request, load_json(args.validate_reject))
        write_json(
            args.validate_reject.with_suffix(args.validate_reject.suffix + ".validation.json"),
            reject_report,
        )
    if args.validate_smoke_handoff:
        smoke_report = validate_smoke_handoff_checklist(load_json(args.validate_smoke_handoff))
        write_json(
            args.validate_smoke_handoff.with_suffix(args.validate_smoke_handoff.suffix + ".validation.json"),
            smoke_report,
        )
    if args.validate_smoke_dry_run_request:
        request_report = validate_smoke_dry_run_request(load_json(args.validate_smoke_dry_run_request))
        write_json(
            args.validate_smoke_dry_run_request.with_suffix(
                args.validate_smoke_dry_run_request.suffix + ".validation.json"
            ),
            request_report,
        )
    if args.validate_smoke_dry_run_receipt:
        if dry_run_request is None:
            if args.validate_smoke_dry_run_request:
                dry_run_request = load_json(args.validate_smoke_dry_run_request)
            else:
                if smoke_handoff is None:
                    smoke_handoff = build_smoke_handoff_checklist(
                        request,
                        report,
                        ack_fixture,
                        target_profile=args.target_profile,
                    )
                dry_run_request = build_smoke_dry_run_request(
                    smoke_handoff,
                    target_profile=args.target_profile,
                )
        receipt_report = validate_smoke_dry_run_receipt(
            dry_run_request,
            load_json(args.validate_smoke_dry_run_receipt),
        )
        write_json(
            args.validate_smoke_dry_run_receipt.with_suffix(
                args.validate_smoke_dry_run_receipt.suffix + ".validation.json"
            ),
            receipt_report,
        )
    if args.validate_smoke_preflight:
        preflight_report = validate_smoke_execution_preflight(load_json(args.validate_smoke_preflight))
        write_json(
            args.validate_smoke_preflight.with_suffix(
                args.validate_smoke_preflight.suffix + ".validation.json"
            ),
            preflight_report,
        )
    if args.validate_smoke_host_shell_execution:
        execution_report = validate_smoke_host_shell_execution(load_json(args.validate_smoke_host_shell_execution))
        write_json(
            args.validate_smoke_host_shell_execution.with_suffix(
                args.validate_smoke_host_shell_execution.suffix + ".validation.json"
            ),
            execution_report,
        )
    if args.validate_smoke_review_bundle:
        bundle_report = validate_smoke_review_bundle(load_json(args.validate_smoke_review_bundle))
        write_json(
            args.validate_smoke_review_bundle.with_suffix(
                args.validate_smoke_review_bundle.suffix + ".validation.json"
            ),
            bundle_report,
        )
    if args.validate_platform_smoke_plan:
        plan_report = validate_platform_smoke_plan(load_json(args.validate_platform_smoke_plan))
        write_json(
            args.validate_platform_smoke_plan.with_suffix(
                args.validate_platform_smoke_plan.suffix + ".validation.json"
            ),
            plan_report,
        )
    return 0 if report["status"] == ACCEPTED_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
