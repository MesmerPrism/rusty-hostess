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

READY_STATUS = "ready"
BLOCKED_STATUS = "blocked"
ACCEPTED_STATUS = "accepted"
REJECTED_STATUS = "rejected"
PENDING_STATUS = "pending"
PASS_STATUS = "pass"
FAIL_STATUS = "fail"

HOSTESS_OWNER = "rusty.hostess"
MANIFOLD_OWNER = "rusty.manifold"
STUDIO_REQUESTER = "rusty.studio"
STUDIO_ROLE = "authoring.export_planning"
REQUEST_POLICY = "not_executed.hostess_request_only"

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
    parser.add_argument("--smoke-dry-run-receipt-out", type=Path)
    parser.add_argument("--target-profile", default="hostess.t.schema_smoke")
    parser.add_argument("--validate-ack", type=Path)
    parser.add_argument("--validate-reject", type=Path)
    parser.add_argument("--validate-smoke-handoff", type=Path)
    parser.add_argument("--validate-smoke-dry-run-request", type=Path)
    parser.add_argument("--validate-smoke-dry-run-receipt", type=Path)
    args = parser.parse_args()

    request = load_json(args.request)
    report = build_intake_report(request, args.request)
    ack_fixture = build_ack_fixture(request) if report["status"] == ACCEPTED_STATUS else None
    smoke_handoff = load_json(args.smoke_handoff_in) if args.smoke_handoff_in else None
    dry_run_request = load_json(args.smoke_dry_run_request_in) if args.smoke_dry_run_request_in else None
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
    if args.smoke_dry_run_request_out or args.smoke_dry_run_receipt_out:
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
            write_json(args.smoke_dry_run_receipt_out, build_smoke_dry_run_receipt(dry_run_request))
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
    return 0 if report["status"] == ACCEPTED_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
