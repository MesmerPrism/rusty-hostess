"""Platform smoke operator-start gate and preflight helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.smoke_workflow import *  # smoke review bundle helpers
from tools.studio_staging.platform_smoke_execution import *  # prior platform-smoke phase helpers

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
