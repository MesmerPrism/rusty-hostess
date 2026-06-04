"""Schema-only Hostess smoke workflow receipts and validations."""

from __future__ import annotations

from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.request_intake import *  # request intake helpers

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

__all__ = [
    "build_smoke_handoff_checklist",
    "validate_smoke_handoff_checklist",
    "smoke_handoff_items",
    "smoke_handoff_checks",
    "smoke_handoff_items_match_contracts",
    "first_item_issue_code",
    "build_smoke_dry_run_request",
    "build_smoke_dry_run_receipt",
    "validate_smoke_dry_run_request",
    "validate_smoke_dry_run_receipt",
    "smoke_dry_run_steps",
    "smoke_dry_run_request_checks",
    "smoke_dry_run_request_steps",
    "smoke_dry_run_steps_match_contracts",
    "receipt_items_match_dry_run_steps",
    "first_step_issue_code",
    "build_smoke_execution_preflight",
    "validate_smoke_execution_preflight",
    "smoke_preflight_capabilities",
    "smoke_preflight_checks",
    "preflight_capabilities",
    "smoke_preflight_capabilities_match_contracts",
    "first_capability_issue_code",
    "build_smoke_host_shell_execution",
    "validate_smoke_host_shell_execution",
    "smoke_host_shell_evidence_records",
    "smoke_host_shell_execution_checks",
    "smoke_host_shell_execution_evidence_records",
    "smoke_host_shell_evidence_records_match_capabilities",
    "first_evidence_issue_code",
    "build_smoke_review_bundle",
    "validate_smoke_review_bundle",
    "smoke_review_bundle_records",
    "smoke_review_bundle_checks",
    "smoke_review_bundle_source_records",
    "smoke_review_bundle_record_dicts",
    "smoke_review_bundle_records_match_source",
    "first_bundle_record_issue_code",
]
