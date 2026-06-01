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
PLATFORM_SMOKE_APPROVAL_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_approval_receipt.v1"
)
PLATFORM_SMOKE_APPROVAL_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_approval_receipt_validation.v1"
)
PLATFORM_SMOKE_EXECUTION_REQUEST_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_request.v1"
)
PLATFORM_SMOKE_EXECUTION_REQUEST_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_request_validation.v1"
)
PLATFORM_SMOKE_EXECUTION_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_receipt.v1"
)
PLATFORM_SMOKE_EXECUTION_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_receipt_validation.v1"
)
PLATFORM_SMOKE_OPERATOR_START_GATE_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_operator_start_gate.v1"
)
PLATFORM_SMOKE_OPERATOR_START_GATE_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_operator_start_gate_validation.v1"
)
PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_operator_start_preflight_receipt.v1"
)
PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_operator_start_preflight_receipt_validation.v1"
)
OPERATOR_START_REQUEST_TEMPLATE_SCHEMA = (
    "rusty.hostess.platform_smoke_operator_start_request_template.v1"
)
OPERATOR_START_ACK_TEMPLATE_SCHEMA = (
    "rusty.hostess.platform_smoke_operator_start_ack_template.v1"
)
OPERATOR_START_REJECT_TEMPLATE_SCHEMA = (
    "rusty.hostess.platform_smoke_operator_start_reject_template.v1"
)
PLATFORM_SMOKE_EVIDENCE_RECEIPT_TEMPLATE_SCHEMA = (
    "rusty.hostess.platform_smoke_expected_evidence_receipt_template.v1"
)

READY_STATUS = "ready"
BLOCKED_STATUS = "blocked"
ACCEPTED_STATUS = "accepted"
REJECTED_STATUS = "rejected"
PENDING_STATUS = "pending"
COMPLETED_STATUS = "completed"
REVIEWED_STATUS = "reviewed"
PLANNED_STATUS = "planned"
APPROVED_STATUS = "approved"
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
PLATFORM_SMOKE_APPROVAL_RECEIPT_POLICY = (
    "hostess.operator_controlled_platform_smoke_approval_receipt_only"
)
PLATFORM_SMOKE_EXECUTION_REQUEST_POLICY = (
    "hostess.operator_controlled_platform_smoke_execution_request_only"
)
PLATFORM_SMOKE_EXECUTION_RECEIPT_POLICY = (
    "hostess.operator_controlled_platform_smoke_execution_receipt_only"
)
PLATFORM_SMOKE_OPERATOR_START_GATE_POLICY = (
    "hostess.operator_controlled_platform_smoke_operator_start_gate_only"
)
PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_POLICY = (
    "hostess.operator_controlled_platform_smoke_operator_start_preflight_receipt_only"
)

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

OPERATOR_START_READINESS_INPUT_CONTRACTS = [
    {
        "readiness_input_id": "hostess.operator_start.host_shell_selection",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_host_shell_selection",
        "expected_source_kind": "platform_smoke_operator_start_gate",
        "validation_kind": "host_shell_kind_review",
    },
    {
        "readiness_input_id": "hostess.operator_start.toolchain_readiness",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_toolchain_readiness",
        "expected_source_kind": "operator_supplied_toolchain_manifest",
        "validation_kind": "toolchain_paths_review",
    },
    {
        "readiness_input_id": "hostess.operator_start.device_readiness",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_device_readiness",
        "expected_source_kind": "operator_supplied_device_readiness_manifest",
        "validation_kind": "device_target_review",
    },
    {
        "readiness_input_id": "manifold.operator_start.command_session_review",
        "owner": MANIFOLD_OWNER,
        "input_kind": "manifold_command_session_readiness",
        "expected_source_kind": "manifold_command_session_contract_review",
        "validation_kind": "command_session_authority_review",
    },
    {
        "readiness_input_id": "hostess.operator_start.evidence_destination",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_evidence_destination_readiness",
        "expected_source_kind": "operator_supplied_evidence_destination_manifest",
        "validation_kind": "evidence_write_location_review",
    },
    {
        "readiness_input_id": "hostess.operator_start.rollback_plan",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_platform_smoke_rollback_plan",
        "expected_source_kind": "operator_supplied_rollback_plan",
        "validation_kind": "rollback_or_cleanup_review",
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


def build_platform_smoke_operator_start_preflight_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    decision: str = APPROVED_STATUS,
    reason_code: str | None = None,
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
    status = APPROVED_STATUS if decision == APPROVED_STATUS and gate_ready else REJECTED_STATUS
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or operator_start_gate.get("issue_code")
            or gate_validation.get("issue_code")
            or "hostess.issue.platform_smoke_operator_start_preflight_rejected"
        )
    readiness_inputs = platform_smoke_operator_start_readiness_inputs(
        operator_start_gate,
        status,
        issue_code,
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
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == APPROVED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        readiness_inputs = platform_smoke_operator_start_readiness_inputs(
            operator_start_gate,
            status,
            issue_code,
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
            ),
            "platform smoke operator-start readiness inputs match required Hostess/Manifold inputs",
            "platform smoke operator-start readiness inputs drifted",
            "hostess.issue.platform_smoke_operator_start_preflight_readiness_drift",
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
            ),
            "platform smoke operator-start readiness inputs match required contracts",
            "platform smoke operator-start readiness inputs drifted",
            "hostess.issue.platform_smoke_operator_start_preflight_readiness_drift",
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
) -> list[dict[str, Any]]:
    readiness_status = APPROVED_STATUS if status == APPROVED_STATUS else REJECTED_STATUS
    inputs = []
    for contract in OPERATOR_START_READINESS_INPUT_CONTRACTS:
        inputs.append(
            {
                "readiness_input_id": contract["readiness_input_id"],
                "source_operator_start_gate_id": operator_start_gate.get("operator_start_gate_id"),
                "owner": contract["owner"],
                "input_kind": contract["input_kind"],
                "expected_source_kind": contract["expected_source_kind"],
                "validation_kind": contract["validation_kind"],
                "readiness_status": readiness_status,
                "issue_code": None if readiness_status == APPROVED_STATUS else issue_code,
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
        )
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
) -> bool:
    if status not in {APPROVED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {item.get("readiness_input_id"): item for item in readiness_inputs}
    if len(readiness_inputs) != len(OPERATOR_START_READINESS_INPUT_CONTRACTS):
        return False
    for contract in OPERATOR_START_READINESS_INPUT_CONTRACTS:
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
    parser.add_argument("--platform-smoke-plan-in", type=Path)
    parser.add_argument("--platform-smoke-plan-out", type=Path)
    parser.add_argument("--platform-smoke-approval-in", type=Path)
    parser.add_argument("--platform-smoke-approval-out", type=Path)
    parser.add_argument("--platform-smoke-rejection-out", type=Path)
    parser.add_argument("--platform-smoke-execution-request-in", type=Path)
    parser.add_argument("--platform-smoke-execution-request-out", type=Path)
    parser.add_argument("--platform-smoke-execution-receipt-in", type=Path)
    parser.add_argument("--platform-smoke-execution-receipt-out", type=Path)
    parser.add_argument("--platform-smoke-operator-start-gate-in", type=Path)
    parser.add_argument("--platform-smoke-operator-start-gate-out", type=Path)
    parser.add_argument("--platform-smoke-operator-start-preflight-in", type=Path)
    parser.add_argument("--platform-smoke-operator-start-preflight-out", type=Path)
    parser.add_argument("--platform-smoke-operator-start-preflight-rejection-out", type=Path)
    parser.add_argument("--target-profile", default="hostess.t.schema_smoke")
    parser.add_argument("--target-platform", default="hostess.platform_smoke.operator_controlled")
    parser.add_argument("--host-shell-kind", default="hostess.t_or_dedicated_quest_host_shell")
    parser.add_argument("--validate-ack", type=Path)
    parser.add_argument("--validate-reject", type=Path)
    parser.add_argument("--validate-smoke-handoff", type=Path)
    parser.add_argument("--validate-smoke-dry-run-request", type=Path)
    parser.add_argument("--validate-smoke-dry-run-receipt", type=Path)
    parser.add_argument("--validate-smoke-preflight", type=Path)
    parser.add_argument("--validate-smoke-host-shell-execution", type=Path)
    parser.add_argument("--validate-smoke-review-bundle", type=Path)
    parser.add_argument("--validate-platform-smoke-plan", type=Path)
    parser.add_argument("--validate-platform-smoke-approval", type=Path)
    parser.add_argument("--validate-platform-smoke-execution-request", type=Path)
    parser.add_argument("--validate-platform-smoke-execution-receipt", type=Path)
    parser.add_argument("--validate-platform-smoke-operator-start-gate", type=Path)
    parser.add_argument("--validate-platform-smoke-operator-start-preflight", type=Path)
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
    platform_smoke_plan = load_json(args.platform_smoke_plan_in) if args.platform_smoke_plan_in else None
    platform_smoke_approval = (
        load_json(args.platform_smoke_approval_in) if args.platform_smoke_approval_in else None
    )
    platform_smoke_execution_request = (
        load_json(args.platform_smoke_execution_request_in)
        if args.platform_smoke_execution_request_in
        else None
    )
    platform_smoke_execution_receipt = (
        load_json(args.platform_smoke_execution_receipt_in)
        if args.platform_smoke_execution_receipt_in
        else None
    )
    platform_smoke_operator_start_gate = (
        load_json(args.platform_smoke_operator_start_gate_in)
        if args.platform_smoke_operator_start_gate_in
        else None
    )
    platform_smoke_operator_start_preflight = (
        load_json(args.platform_smoke_operator_start_preflight_in)
        if args.platform_smoke_operator_start_preflight_in
        else None
    )
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
        or args.platform_smoke_approval_out
        or args.platform_smoke_rejection_out
        or args.platform_smoke_execution_request_out
        or args.platform_smoke_execution_receipt_out
        or args.platform_smoke_operator_start_gate_out
        or args.platform_smoke_operator_start_preflight_out
        or args.platform_smoke_operator_start_preflight_rejection_out
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
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            write_json(
                args.platform_smoke_plan_out,
                platform_smoke_plan,
            )
        if args.platform_smoke_approval_out or args.platform_smoke_rejection_out:
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
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if args.platform_smoke_approval_out:
                if platform_smoke_approval is None:
                    platform_smoke_approval = build_platform_smoke_approval_receipt(
                        platform_smoke_plan,
                        decision=APPROVED_STATUS,
                    )
                write_json(
                    args.platform_smoke_approval_out,
                    platform_smoke_approval,
                )
            if args.platform_smoke_rejection_out:
                write_json(
                    args.platform_smoke_rejection_out,
                    build_platform_smoke_approval_receipt(
                        platform_smoke_plan,
                        decision=REJECTED_STATUS,
                        reason_code="hostess.issue.operator_rejected_platform_smoke_plan",
                    ),
                )
        if args.platform_smoke_execution_request_out or args.platform_smoke_execution_receipt_out:
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
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if platform_smoke_approval is None:
                platform_smoke_approval = build_platform_smoke_approval_receipt(
                    platform_smoke_plan,
                    decision=APPROVED_STATUS,
                )
            if platform_smoke_execution_request is None:
                platform_smoke_execution_request = build_platform_smoke_execution_request(
                    platform_smoke_plan,
                    platform_smoke_approval,
                )
            if args.platform_smoke_execution_request_out:
                write_json(
                    args.platform_smoke_execution_request_out,
                    platform_smoke_execution_request,
                )
            if args.platform_smoke_execution_receipt_out:
                if platform_smoke_execution_receipt is None:
                    platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                        platform_smoke_plan,
                        platform_smoke_approval,
                        platform_smoke_execution_request,
                    )
                write_json(
                    args.platform_smoke_execution_receipt_out,
                    platform_smoke_execution_receipt,
                )
        if args.platform_smoke_operator_start_gate_out:
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
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if platform_smoke_approval is None:
                platform_smoke_approval = build_platform_smoke_approval_receipt(
                    platform_smoke_plan,
                    decision=APPROVED_STATUS,
                )
            if platform_smoke_execution_request is None:
                platform_smoke_execution_request = build_platform_smoke_execution_request(
                    platform_smoke_plan,
                    platform_smoke_approval,
                )
            if platform_smoke_execution_receipt is None:
                platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                )
            if platform_smoke_operator_start_gate is None:
                platform_smoke_operator_start_gate = build_platform_smoke_operator_start_gate(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    host_shell_kind=args.host_shell_kind,
                )
            write_json(
                args.platform_smoke_operator_start_gate_out,
                platform_smoke_operator_start_gate,
            )
        if (
            args.platform_smoke_operator_start_preflight_out
            or args.platform_smoke_operator_start_preflight_rejection_out
        ):
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
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if platform_smoke_approval is None:
                platform_smoke_approval = build_platform_smoke_approval_receipt(
                    platform_smoke_plan,
                    decision=APPROVED_STATUS,
                )
            if platform_smoke_execution_request is None:
                platform_smoke_execution_request = build_platform_smoke_execution_request(
                    platform_smoke_plan,
                    platform_smoke_approval,
                )
            if platform_smoke_execution_receipt is None:
                platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                )
            if platform_smoke_operator_start_gate is None:
                platform_smoke_operator_start_gate = build_platform_smoke_operator_start_gate(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    host_shell_kind=args.host_shell_kind,
                )
            if args.platform_smoke_operator_start_preflight_out:
                if platform_smoke_operator_start_preflight is None:
                    platform_smoke_operator_start_preflight = (
                        build_platform_smoke_operator_start_preflight_receipt(
                            platform_smoke_plan,
                            platform_smoke_approval,
                            platform_smoke_execution_request,
                            platform_smoke_execution_receipt,
                            platform_smoke_operator_start_gate,
                            decision=APPROVED_STATUS,
                        )
                    )
                write_json(
                    args.platform_smoke_operator_start_preflight_out,
                    platform_smoke_operator_start_preflight,
                )
            if args.platform_smoke_operator_start_preflight_rejection_out:
                write_json(
                    args.platform_smoke_operator_start_preflight_rejection_out,
                    build_platform_smoke_operator_start_preflight_receipt(
                        platform_smoke_plan,
                        platform_smoke_approval,
                        platform_smoke_execution_request,
                        platform_smoke_execution_receipt,
                        platform_smoke_operator_start_gate,
                        decision=REJECTED_STATUS,
                        reason_code="hostess.issue.operator_rejected_platform_smoke_operator_start_preflight",
                    ),
                )
    if (
        args.validate_platform_smoke_approval
        or args.validate_platform_smoke_execution_request
        or args.validate_platform_smoke_execution_receipt
        or args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
    ) and platform_smoke_plan is None:
        if args.validate_platform_smoke_plan:
            platform_smoke_plan = load_json(args.validate_platform_smoke_plan)
        else:
            if dry_run_request is None:
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
            platform_smoke_plan = build_platform_smoke_plan(
                smoke_review_bundle,
                target_platform=args.target_platform,
            )
    if (
        args.validate_platform_smoke_execution_request
        or args.validate_platform_smoke_execution_receipt
        or args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
    ) and platform_smoke_approval is None:
        if args.validate_platform_smoke_approval:
            platform_smoke_approval = load_json(args.validate_platform_smoke_approval)
        else:
            platform_smoke_approval = build_platform_smoke_approval_receipt(
                platform_smoke_plan,
                decision=APPROVED_STATUS,
            )
    if (
        args.validate_platform_smoke_execution_receipt
        or args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
    ) and platform_smoke_execution_request is None:
        if args.validate_platform_smoke_execution_request:
            platform_smoke_execution_request = load_json(args.validate_platform_smoke_execution_request)
        else:
            platform_smoke_execution_request = build_platform_smoke_execution_request(
                platform_smoke_plan,
                platform_smoke_approval,
            )
    if (
        args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
    ) and platform_smoke_execution_receipt is None:
        if args.validate_platform_smoke_execution_receipt:
            platform_smoke_execution_receipt = load_json(args.validate_platform_smoke_execution_receipt)
        else:
            platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
            )
    if args.validate_platform_smoke_operator_start_preflight and platform_smoke_operator_start_gate is None:
        if args.validate_platform_smoke_operator_start_gate:
            platform_smoke_operator_start_gate = load_json(args.validate_platform_smoke_operator_start_gate)
        else:
            platform_smoke_operator_start_gate = build_platform_smoke_operator_start_gate(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
                platform_smoke_execution_receipt,
                host_shell_kind=args.host_shell_kind,
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
    if args.validate_platform_smoke_approval:
        approval_report = validate_platform_smoke_approval_receipt(
            platform_smoke_plan,
            load_json(args.validate_platform_smoke_approval),
        )
        write_json(
            args.validate_platform_smoke_approval.with_suffix(
                args.validate_platform_smoke_approval.suffix + ".validation.json"
            ),
            approval_report,
        )
    if args.validate_platform_smoke_execution_request:
        execution_request_report = validate_platform_smoke_execution_request(
            platform_smoke_plan,
            platform_smoke_approval,
            load_json(args.validate_platform_smoke_execution_request),
        )
        write_json(
            args.validate_platform_smoke_execution_request.with_suffix(
                args.validate_platform_smoke_execution_request.suffix + ".validation.json"
            ),
            execution_request_report,
        )
    if args.validate_platform_smoke_execution_receipt:
        execution_receipt_report = validate_platform_smoke_execution_receipt(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            load_json(args.validate_platform_smoke_execution_receipt),
        )
        write_json(
            args.validate_platform_smoke_execution_receipt.with_suffix(
                args.validate_platform_smoke_execution_receipt.suffix + ".validation.json"
            ),
            execution_receipt_report,
        )
    if args.validate_platform_smoke_operator_start_gate:
        operator_start_report = validate_platform_smoke_operator_start_gate(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            load_json(args.validate_platform_smoke_operator_start_gate),
        )
        write_json(
            args.validate_platform_smoke_operator_start_gate.with_suffix(
                args.validate_platform_smoke_operator_start_gate.suffix + ".validation.json"
            ),
            operator_start_report,
        )
    if args.validate_platform_smoke_operator_start_preflight:
        operator_start_preflight_report = validate_platform_smoke_operator_start_preflight_receipt(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            platform_smoke_operator_start_gate,
            load_json(args.validate_platform_smoke_operator_start_preflight),
        )
        write_json(
            args.validate_platform_smoke_operator_start_preflight.with_suffix(
                args.validate_platform_smoke_operator_start_preflight.suffix + ".validation.json"
            ),
            operator_start_preflight_report,
        )
    return 0 if report["status"] == ACCEPTED_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
