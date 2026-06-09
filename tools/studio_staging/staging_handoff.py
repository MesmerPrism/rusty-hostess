"""Hostess staging handoff, file-plan, and payload selection receipts."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers

def build_hostess_staging_handoff_acceptance_receipt(
    operator_release_readiness_bundle: dict[str, Any],
    staging_handoff: dict[str, Any],
    acceptance_manifest: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    release_ready = operator_release_readiness_bundle_source_ready(
        operator_release_readiness_bundle
    )
    handoff_ready = studio_hostess_staging_handoff_source_ready(staging_handoff)
    acceptance_ready = studio_hostess_staging_acceptance_manifest_source_ready(
        acceptance_manifest,
        staging_handoff,
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    status = (
        ACCEPTED_STATUS
        if decision == ACCEPTED_STATUS
        and decision_supported
        and release_ready
        and handoff_ready
        and acceptance_ready
        else REJECTED_STATUS
    )
    issue_code = None
    if status != ACCEPTED_STATUS:
        issue_code = (
            reason_code
            or operator_release_readiness_bundle.get("issue_code")
            or staging_handoff.get("issue_code")
            or acceptance_manifest.get("issue_code")
            or (
                "hostess.issue.hostess_staging_handoff_acceptance_receipt_decision"
                if not decision_supported
                else "hostess.issue.hostess_staging_handoff_source_not_ready"
            )
        )
    request_rows = hostess_staging_handoff_acceptance_request_rows(
        staging_handoff,
        status,
        issue_code,
    )
    instruction_rows = hostess_staging_handoff_acceptance_instruction_rows(
        staging_handoff,
        status,
        issue_code,
    )
    accepted_requests = [
        row for row in request_rows if row.get("acceptance_status") == ACCEPTED_STATUS
    ]
    rejected_requests = [
        row for row in request_rows if row.get("acceptance_status") == REJECTED_STATUS
    ]
    accepted_instructions = [
        row
        for row in instruction_rows
        if row.get("acceptance_status") == ACCEPTED_STATUS
    ]
    rejected_instructions = [
        row
        for row in instruction_rows
        if row.get("acceptance_status") == REJECTED_STATUS
    ]
    checks = hostess_staging_handoff_acceptance_receipt_checks(
        operator_release_readiness_bundle,
        staging_handoff,
        acceptance_manifest,
        request_rows,
        instruction_rows,
        status,
        decision_supported,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == ACCEPTED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        request_rows = hostess_staging_handoff_acceptance_request_rows(
            staging_handoff,
            status,
            issue_code,
        )
        instruction_rows = hostess_staging_handoff_acceptance_instruction_rows(
            staging_handoff,
            status,
            issue_code,
        )
        accepted_requests = []
        rejected_requests = request_rows
        accepted_instructions = []
        rejected_instructions = instruction_rows
    bundle_id = operator_release_readiness_bundle.get("bundle_id")
    envelope_id = staging_handoff.get("envelope_id")
    acceptance_id = acceptance_manifest.get("acceptance_id")
    receipt_id = (
        f"hostess.staging_handoff_acceptance_receipt.{bundle_id}.{envelope_id}.{acceptance_id}"
        if isinstance(bundle_id, str)
        and bundle_id
        and isinstance(envelope_id, str)
        and envelope_id
        and isinstance(acceptance_id, str)
        and acceptance_id
        else "hostess.staging_handoff_acceptance_receipt.unknown"
    )
    pmb_review_required = (
        operator_release_readiness_bundle.get("pmb_shell_handoff_review_required")
        is True
    )
    pmb_review_ready = (
        operator_release_readiness_bundle.get("pmb_shell_handoff_review_ready") is True
    )
    return {
        "$schema": HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_operator_release_readiness_bundle_id": bundle_id,
        "source_operator_release_readiness_bundle_schema": (
            operator_release_readiness_bundle.get("$schema")
        ),
        "source_operator_release_readiness_bundle_status": (
            operator_release_readiness_bundle.get("status")
        ),
        "source_operator_release_scorecard_status": (
            operator_release_readiness_bundle.get("scorecard_status")
        ),
        "source_staging_handoff_envelope_id": envelope_id,
        "source_staging_handoff_schema": staging_handoff.get("$schema"),
        "source_staging_handoff_status": staging_handoff.get("status"),
        "source_acceptance_id": acceptance_id,
        "source_acceptance_schema": acceptance_manifest.get("$schema"),
        "source_acceptance_status": acceptance_manifest.get("status"),
        "manifest_id": staging_handoff.get("manifest_id"),
        "project_id": staging_handoff.get("project_id"),
        "project_revision": staging_handoff.get("project_revision"),
        "selected_candidate_id": staging_handoff.get("selected_candidate_id"),
        "checksum_algorithm": acceptance_manifest.get("checksum_algorithm"),
        "plan_checksum": acceptance_manifest.get("plan_checksum"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "handoff_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "operator_release_ready": (
            operator_release_readiness_bundle.get("operator_release_ready") is True
        ),
        "staging_handoff_accepted": status == ACCEPTED_STATUS,
        "stage_generated_shells_request_accepted": status == ACCEPTED_STATUS,
        "stage_generated_shells_started": False,
        "device_required": False,
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
        "schema_artifact_payloads_copied": False,
        "release_payloads_copied": False,
        "staging_payloads_copied": False,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(operator_release_readiness_bundle),
        "request_count": len(request_rows),
        "accepted_request_count": len(accepted_requests),
        "rejected_request_count": len(rejected_requests),
        "target_request_count": sum(
            1 for row in request_rows if row.get("target_kind") is not None
        ),
        "shared_request_count": sum(
            1 for row in request_rows if row.get("target_kind") is None
        ),
        "instruction_count": len(instruction_rows),
        "accepted_instruction_count": len(accepted_instructions),
        "rejected_instruction_count": len(rejected_instructions),
        "accepted_requests": request_rows,
        "accepted_instructions": instruction_rows,
        "checks": checks,
        "next_required_action": (
            "hostess_stage_generated_shell_files_outside_studio"
            if status == ACCEPTED_STATUS
            else "repair_or_decline_hostess_staging_handoff_acceptance"
        ),
    }


def validate_hostess_staging_handoff_acceptance_receipt(
    operator_release_readiness_bundle: dict[str, Any],
    staging_handoff: dict[str, Any],
    acceptance_manifest: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    request_rows = hostess_staging_handoff_acceptance_request_dicts(receipt)
    instruction_rows = hostess_staging_handoff_acceptance_instruction_dicts(receipt)
    accepted_requests = [
        row for row in request_rows if row.get("acceptance_status") == ACCEPTED_STATUS
    ]
    rejected_requests = [
        row for row in request_rows if row.get("acceptance_status") == REJECTED_STATUS
    ]
    accepted_instructions = [
        row
        for row in instruction_rows
        if row.get("acceptance_status") == ACCEPTED_STATUS
    ]
    rejected_instructions = [
        row
        for row in instruction_rows
        if row.get("acceptance_status") == REJECTED_STATUS
    ]
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [
        entry for entry in embedded_checks if isinstance(entry, dict)
    ]
    embedded_failed = [
        entry for entry in embedded_check_dicts if entry.get("status") == FAIL_STATUS
    ]
    status = receipt.get("status")
    pmb_review_required = (
        operator_release_readiness_bundle.get("pmb_shell_handoff_review_required")
        is True
    )
    pmb_summary_matches_release = (
        pmb_shell_handoff_review_summary_from_source(receipt)
        == pmb_shell_handoff_review_summary_from_source(
            operator_release_readiness_bundle
        )
    )
    checks = [
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.schema",
            receipt.get("$schema") == HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_SCHEMA,
            "Hostess staging handoff acceptance receipt schema is supported",
            "Hostess staging handoff acceptance receipt schema is unsupported",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_schema",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.status",
            status in {ACCEPTED_STATUS, REJECTED_STATUS}
            and (
                (status == ACCEPTED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess staging handoff acceptance receipt status is consistent",
            "Hostess staging handoff acceptance receipt status is inconsistent",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_status",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.execution_policy",
            receipt.get("execution_policy")
            == HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_POLICY,
            "Hostess staging handoff acceptance receipt is schema-only",
            "Hostess staging handoff acceptance receipt execution policy drifted",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_execution_policy",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.sources",
            receipt.get("source_operator_release_readiness_bundle_id")
            == operator_release_readiness_bundle.get("bundle_id")
            and receipt.get("source_operator_release_readiness_bundle_schema")
            == OPERATOR_RELEASE_READINESS_BUNDLE_SCHEMA
            and receipt.get("source_staging_handoff_envelope_id")
            == staging_handoff.get("envelope_id")
            and receipt.get("source_staging_handoff_schema")
            == STUDIO_HOSTESS_STAGING_HANDOFF_SCHEMA
            and receipt.get("source_acceptance_id")
            == acceptance_manifest.get("acceptance_id")
            and receipt.get("source_acceptance_schema")
            == STUDIO_HOSTESS_STAGING_ACCEPTANCE_MANIFEST_SCHEMA,
            "Hostess staging handoff acceptance sources match inputs",
            "Hostess staging handoff acceptance sources drifted",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_source_mismatch",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.source_readiness",
            (
                status == ACCEPTED_STATUS
                and operator_release_readiness_bundle_source_ready(
                    operator_release_readiness_bundle
                )
                and studio_hostess_staging_handoff_source_ready(staging_handoff)
                and studio_hostess_staging_acceptance_manifest_source_ready(
                    acceptance_manifest,
                    staging_handoff,
                )
            )
            or status == REJECTED_STATUS,
            "Hostess staging handoff acceptance sources are ready or rejected consistently",
            "Hostess staging handoff acceptance sources do not match receipt status",
            "hostess.issue.hostess_staging_handoff_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != ACCEPTED_STATUS
            or (
                receipt.get("pmb_shell_handoff_review_required") is True
                and receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_release
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            ),
            "accepted Hostess staging handoff preserves the PMB shell handoff gate",
            "accepted Hostess staging handoff dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("handoff_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "Hostess staging handoff acceptance authority fields drifted",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_authority",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.no_execution_started",
            hostess_staging_handoff_acceptance_receipt_unstarted(receipt),
            "Hostess staging handoff acceptance has not started staging, execution, launch, or payload copying",
            "Hostess staging handoff acceptance indicates staging, execution, launch, or payload copying",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_execution_started",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.requests",
            hostess_staging_handoff_acceptance_requests_match_source(
                staging_handoff,
                request_rows,
                status,
            ),
            "Hostess staging handoff accepted request rows match the source envelope",
            "Hostess staging handoff accepted request rows drifted",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_request_drift",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.instructions",
            hostess_staging_handoff_acceptance_instructions_match_source(
                staging_handoff,
                instruction_rows,
                status,
            ),
            "Hostess staging handoff accepted instruction rows match the source envelope",
            "Hostess staging handoff accepted instruction rows drifted",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_instruction_drift",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.counts",
            receipt.get("request_count") == len(request_rows)
            and receipt.get("accepted_request_count") == len(accepted_requests)
            and receipt.get("rejected_request_count") == len(rejected_requests)
            and receipt.get("target_request_count")
            == sum(1 for row in request_rows if row.get("target_kind") is not None)
            and receipt.get("shared_request_count")
            == sum(1 for row in request_rows if row.get("target_kind") is None)
            and receipt.get("instruction_count") == len(instruction_rows)
            and receipt.get("accepted_instruction_count") == len(accepted_instructions)
            and receipt.get("rejected_instruction_count") == len(rejected_instructions),
            "Hostess staging handoff acceptance counts match nested records",
            "Hostess staging handoff acceptance counts drifted",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_count_drift",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.scorecard",
            (
                status == ACCEPTED_STATUS
                and receipt.get("staging_handoff_accepted") is True
                and receipt.get("stage_generated_shells_request_accepted") is True
                and receipt.get("accepted_request_count")
                == staging_handoff.get("request_count")
                and receipt.get("accepted_instruction_count")
                == staging_handoff.get("instruction_count")
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("staging_handoff_accepted") is False
                and receipt.get("stage_generated_shells_request_accepted") is False
            ),
            "Hostess staging handoff acceptance scorecard matches receipt status",
            "Hostess staging handoff acceptance scorecard drifted",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_scorecard",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.embedded_checks",
            (
                status == ACCEPTED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess staging handoff acceptance embedded checks match receipt status",
            "Hostess staging handoff acceptance embedded checks do not match receipt status",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "pmb_shell_handoff_review_required": receipt.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": receipt.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def hostess_staging_handoff_acceptance_receipt_checks(
    operator_release_readiness_bundle: dict[str, Any],
    staging_handoff: dict[str, Any],
    acceptance_manifest: dict[str, Any],
    request_rows: list[dict[str, Any]],
    instruction_rows: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = (
        operator_release_readiness_bundle.get("pmb_shell_handoff_review_required")
        is True
    )
    return [
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.operator_release_source",
            operator_release_readiness_bundle_source_ready(
                operator_release_readiness_bundle
            ),
            "operator release readiness bundle is ready",
            "operator release readiness bundle is missing, blocked, or drifted",
            operator_release_readiness_bundle.get("issue_code")
            or "hostess.issue.hostess_staging_handoff_operator_release_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.handoff_source",
            studio_hostess_staging_handoff_source_ready(staging_handoff),
            "Studio Hostess staging handoff envelope is ready",
            "Studio Hostess staging handoff envelope is missing, blocked, or drifted",
            staging_handoff.get("issue_code")
            or "hostess.issue.hostess_staging_handoff_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.acceptance_source",
            studio_hostess_staging_acceptance_manifest_source_ready(
                acceptance_manifest,
                staging_handoff,
            ),
            "Studio Hostess staging acceptance manifest is ready",
            "Studio Hostess staging acceptance manifest is missing, blocked, or drifted",
            acceptance_manifest.get("issue_code")
            or "hostess.issue.hostess_staging_acceptance_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != ACCEPTED_STATUS
            or (
                operator_release_readiness_bundle.get(
                    "pmb_shell_handoff_review_ready"
                )
                is True
                and pmb_shell_handoff_readiness_result_summary_valid(
                    operator_release_readiness_bundle
                )
            ),
            "accepted Hostess staging handoff preserves the PMB shell handoff gate",
            "accepted Hostess staging handoff dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.decision",
            decision_supported,
            "Hostess staging handoff acceptance decision is supported",
            "Hostess staging handoff acceptance decision is unsupported",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_decision",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.requests",
            hostess_staging_handoff_acceptance_requests_match_source(
                staging_handoff,
                request_rows,
                status,
            ),
            "Hostess staging handoff accepted request rows match source envelope",
            "Hostess staging handoff accepted request rows drifted",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_request_drift",
        ),
        check(
            "hostess.check.hostess_staging_handoff_acceptance_receipt.instructions",
            hostess_staging_handoff_acceptance_instructions_match_source(
                staging_handoff,
                instruction_rows,
                status,
            ),
            "Hostess staging handoff accepted instruction rows match source envelope",
            "Hostess staging handoff accepted instruction rows drifted",
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_instruction_drift",
        ),
    ]


def hostess_staging_handoff_acceptance_request_rows(
    staging_handoff: dict[str, Any],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    acceptance_status = ACCEPTED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    rows = []
    for request in studio_hostess_staging_handoff_request_dicts(staging_handoff):
        request_id = request.get("request_id")
        rows.append(
            {
                "accepted_request_row_id": (
                    f"hostess.staging_handoff_accepted_request.{request_id}"
                    if isinstance(request_id, str) and request_id
                    else "hostess.staging_handoff_accepted_request.unknown"
                ),
                "source_staging_handoff_envelope_id": staging_handoff.get(
                    "envelope_id"
                ),
                "source_request_id": request_id,
                "request_kind": request.get("request_kind"),
                "owner": request.get("owner"),
                "source_status": request.get("status"),
                "target_key": request.get("target_key"),
                "target_kind": request.get("target_kind"),
                "graph_id": request.get("graph_id"),
                "consumer_id": request.get("consumer_id"),
                "destination_root": request.get("destination_root"),
                "planned_file_count": request.get("planned_file_count"),
                "route_kinds": request.get("route_kinds"),
                "action_ids": request.get("action_ids"),
                "acceptance_status": acceptance_status,
                "issue_code": None if acceptance_status == ACCEPTED_STATUS else issue_code,
                "stage_generated_shells_requested": True,
                "stage_generated_shells_started": False,
                "schema_artifact_payload_copied": False,
                "staging_payload_copied": False,
                "release_payload_copied": False,
                "device_required": False,
                "schema_path_execution_allowed": False,
                "platform_execution_allowed": False,
                "studio_execution_allowed": False,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "build_started": False,
                "copy_started": False,
                "stage_started": False,
                "install_started": False,
                "launch_started": False,
                "evidence_collection_started": False,
                "command_session_started": False,
            }
        )
    return rows


def hostess_staging_handoff_acceptance_instruction_rows(
    staging_handoff: dict[str, Any],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    acceptance_status = ACCEPTED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    rows = []
    for instruction in studio_hostess_staging_handoff_instruction_dicts(staging_handoff):
        instruction_id = instruction.get("instruction_id")
        rows.append(
            {
                "accepted_instruction_row_id": (
                    f"hostess.staging_handoff_accepted_instruction.{instruction_id}"
                    if isinstance(instruction_id, str) and instruction_id
                    else "hostess.staging_handoff_accepted_instruction.unknown"
                ),
                "source_staging_handoff_envelope_id": staging_handoff.get(
                    "envelope_id"
                ),
                "source_instruction_id": instruction_id,
                "owner": instruction.get("owner"),
                "source_status": instruction.get("status"),
                "instruction_kind": instruction.get("instruction_kind"),
                "route_kind": instruction.get("route_kind"),
                "source": instruction.get("source"),
                "expected_input_path": instruction.get("expected_input_path"),
                "next_required_action": instruction.get("next_required_action"),
                "prohibited_in_studio": instruction.get("prohibited_in_studio"),
                "acceptance_status": acceptance_status,
                "issue_code": None if acceptance_status == ACCEPTED_STATUS else issue_code,
                "stage_generated_shells_started": False,
                "schema_artifact_payload_copied": False,
                "staging_payload_copied": False,
                "release_payload_copied": False,
                "device_required": False,
                "schema_path_execution_allowed": False,
                "platform_execution_allowed": False,
                "studio_execution_allowed": False,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "build_started": False,
                "copy_started": False,
                "stage_started": False,
                "install_started": False,
                "launch_started": False,
                "evidence_collection_started": False,
                "command_session_started": False,
            }
        )
    return rows


def hostess_staging_handoff_acceptance_request_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = receipt.get("accepted_requests", [])
    if not isinstance(requests, list):
        return []
    return [entry for entry in requests if isinstance(entry, dict)]


def hostess_staging_handoff_acceptance_instruction_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    instructions = receipt.get("accepted_instructions", [])
    if not isinstance(instructions, list):
        return []
    return [entry for entry in instructions if isinstance(entry, dict)]


def studio_hostess_staging_handoff_request_dicts(
    staging_handoff: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = staging_handoff.get("request_summaries", [])
    if not isinstance(requests, list):
        return []
    return [entry for entry in requests if isinstance(entry, dict)]


def studio_hostess_staging_handoff_instruction_dicts(
    staging_handoff: dict[str, Any],
) -> list[dict[str, Any]]:
    instructions = staging_handoff.get("owner_instructions", [])
    if not isinstance(instructions, list):
        return []
    return [entry for entry in instructions if isinstance(entry, dict)]


def operator_release_readiness_bundle_source_ready(bundle: dict[str, Any]) -> bool:
    checks = bundle.get("checks", [])
    if not isinstance(checks, list):
        return False
    embedded_checks = [entry for entry in checks if isinstance(entry, dict)]
    return (
        bundle.get("$schema") == OPERATOR_RELEASE_READINESS_BUNDLE_SCHEMA
        and bundle.get("status") == READY_STATUS
        and bundle.get("issue_code") is None
        and bundle.get("scorecard_status") == PASS_STATUS
        and bundle.get("operator_release_ready") is True
        and all(entry.get("status") == PASS_STATUS for entry in embedded_checks)
        and operator_release_readiness_bundle_unstarted(bundle)
    )


def studio_hostess_staging_handoff_source_ready(
    staging_handoff: dict[str, Any],
) -> bool:
    checks = staging_handoff.get("checks", [])
    if not isinstance(checks, list):
        return False
    embedded_checks = [entry for entry in checks if isinstance(entry, dict)]
    requests = studio_hostess_staging_handoff_request_dicts(staging_handoff)
    instructions = studio_hostess_staging_handoff_instruction_dicts(staging_handoff)
    return (
        staging_handoff.get("$schema") == STUDIO_HOSTESS_STAGING_HANDOFF_SCHEMA
        and staging_handoff.get("status") == READY_STATUS
        and staging_handoff.get("issue_code") is None
        and staging_handoff.get("execution_policy") == "not_executed.handoff_only"
        and staging_handoff.get("handoff_owner") == HOSTESS_OWNER
        and staging_handoff.get("staging_owner") == HOSTESS_OWNER
        and staging_handoff.get("command_session_authority") == MANIFOLD_OWNER
        and staging_handoff.get("install_launch_evidence_authority") == HOSTESS_OWNER
        and staging_handoff.get("studio_role") == STUDIO_ROLE
        and staging_handoff.get("request_count") == len(requests)
        and staging_handoff.get("ready_request_count") == len(requests)
        and staging_handoff.get("blocked_request_count") == 0
        and staging_handoff.get("instruction_count") == len(instructions)
        and staging_handoff.get("ready_instruction_count") == len(instructions)
        and staging_handoff.get("blocked_instruction_count") == 0
        and all(action in staging_handoff.get("prohibited_actions", []) for action in REQUIRED_PROHIBITED_ACTIONS)
        and all(entry.get("status") == PASS_STATUS for entry in embedded_checks)
        and all(request.get("status") == READY_STATUS for request in requests)
        and all(instruction.get("status") == READY_STATUS for instruction in instructions)
    )


def studio_hostess_staging_acceptance_manifest_source_ready(
    acceptance_manifest: dict[str, Any],
    staging_handoff: dict[str, Any],
) -> bool:
    provenance = staging_handoff.get("provenance", {})
    if not isinstance(provenance, dict):
        provenance = {}
    return (
        acceptance_manifest.get("$schema")
        == STUDIO_HOSTESS_STAGING_ACCEPTANCE_MANIFEST_SCHEMA
        and acceptance_manifest.get("status") == READY_STATUS
        and acceptance_manifest.get("issue_code") is None
        and acceptance_manifest.get("execution_policy")
        == "not_executed.acceptance_check_only"
        and acceptance_manifest.get("checklist_owner") == HOSTESS_OWNER
        and acceptance_manifest.get("handoff_owner") == HOSTESS_OWNER
        and acceptance_manifest.get("staging_owner") == HOSTESS_OWNER
        and acceptance_manifest.get("command_session_authority") == MANIFOLD_OWNER
        and acceptance_manifest.get("install_launch_evidence_authority") == HOSTESS_OWNER
        and acceptance_manifest.get("studio_role") == STUDIO_ROLE
        and acceptance_manifest.get("envelope_id") == staging_handoff.get("envelope_id")
        and acceptance_manifest.get("manifest_id") == staging_handoff.get("manifest_id")
        and acceptance_manifest.get("project_id") == staging_handoff.get("project_id")
        and acceptance_manifest.get("project_revision")
        == staging_handoff.get("project_revision")
        and acceptance_manifest.get("request_count") == staging_handoff.get("request_count")
        and acceptance_manifest.get("ready_request_count")
        == staging_handoff.get("ready_request_count")
        and acceptance_manifest.get("blocked_request_count")
        == staging_handoff.get("blocked_request_count")
        and acceptance_manifest.get("instruction_count")
        == staging_handoff.get("instruction_count")
        and acceptance_manifest.get("ready_instruction_count")
        == staging_handoff.get("ready_instruction_count")
        and acceptance_manifest.get("blocked_instruction_count")
        == staging_handoff.get("blocked_instruction_count")
        and acceptance_manifest.get("checksum_algorithm")
        == provenance.get("checksum_algorithm")
        and acceptance_manifest.get("plan_checksum") == provenance.get("plan_checksum")
        and all(action in acceptance_manifest.get("prohibited_actions", []) for action in REQUIRED_PROHIBITED_ACTIONS)
    )


def hostess_staging_handoff_acceptance_requests_match_source(
    staging_handoff: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {ACCEPTED_STATUS, REJECTED_STATUS}:
        return False
    source_requests = studio_hostess_staging_handoff_request_dicts(staging_handoff)
    if len(rows) != len(source_requests):
        return False
    expected_status = ACCEPTED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    by_id = {row.get("source_request_id"): row for row in rows}
    for request in source_requests:
        row = by_id.get(request.get("request_id"))
        if not isinstance(row, dict):
            return False
        for key in (
            "request_kind",
            "owner",
            "target_key",
            "target_kind",
            "graph_id",
            "consumer_id",
            "destination_root",
            "planned_file_count",
            "route_kinds",
            "action_ids",
        ):
            if row.get(key) != request.get(key):
                return False
        if row.get("source_status") != request.get("status"):
            return False
        if row.get("acceptance_status") != expected_status:
            return False
        if expected_status == ACCEPTED_STATUS and row.get("issue_code") is not None:
            return False
        if expected_status != ACCEPTED_STATUS and not isinstance(row.get("issue_code"), str):
            return False
        if row.get("stage_generated_shells_requested") is not True:
            return False
        if not hostess_staging_handoff_acceptance_request_unstarted(row):
            return False
    return True


def hostess_staging_handoff_acceptance_instructions_match_source(
    staging_handoff: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {ACCEPTED_STATUS, REJECTED_STATUS}:
        return False
    source_instructions = studio_hostess_staging_handoff_instruction_dicts(
        staging_handoff
    )
    if len(rows) != len(source_instructions):
        return False
    expected_status = ACCEPTED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    by_id = {row.get("source_instruction_id"): row for row in rows}
    for instruction in source_instructions:
        row = by_id.get(instruction.get("instruction_id"))
        if not isinstance(row, dict):
            return False
        for key in (
            "owner",
            "instruction_kind",
            "route_kind",
            "source",
            "expected_input_path",
            "next_required_action",
            "prohibited_in_studio",
        ):
            if row.get(key) != instruction.get(key):
                return False
        if row.get("source_status") != instruction.get("status"):
            return False
        if row.get("acceptance_status") != expected_status:
            return False
        if expected_status == ACCEPTED_STATUS and row.get("issue_code") is not None:
            return False
        if expected_status != ACCEPTED_STATUS and not isinstance(row.get("issue_code"), str):
            return False
        if not hostess_staging_handoff_acceptance_instruction_unstarted(row):
            return False
    return True


def hostess_staging_handoff_acceptance_receipt_unstarted(receipt: dict[str, Any]) -> bool:
    return (
        all(receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
        and receipt.get("stage_generated_shells_started") is False
        and receipt.get("device_required") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("schema_artifact_payloads_copied") is False
        and receipt.get("release_payloads_copied") is False
        and receipt.get("staging_payloads_copied") is False
    )


def hostess_staging_handoff_acceptance_request_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("stage_generated_shells_started") is False
        and row.get("schema_artifact_payload_copied") is False
        and row.get("staging_payload_copied") is False
        and row.get("release_payload_copied") is False
        and row.get("device_required") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("platform_execution_allowed") is False
        and row.get("studio_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("build_started") is False
        and row.get("copy_started") is False
        and row.get("stage_started") is False
        and row.get("install_started") is False
        and row.get("launch_started") is False
        and row.get("evidence_collection_started") is False
        and row.get("command_session_started") is False
    )


def hostess_staging_handoff_acceptance_instruction_unstarted(
    row: dict[str, Any],
) -> bool:
    return (
        row.get("stage_generated_shells_started") is False
        and row.get("schema_artifact_payload_copied") is False
        and row.get("staging_payload_copied") is False
        and row.get("release_payload_copied") is False
        and row.get("device_required") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("platform_execution_allowed") is False
        and row.get("studio_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("build_started") is False
        and row.get("copy_started") is False
        and row.get("stage_started") is False
        and row.get("install_started") is False
        and row.get("launch_started") is False
        and row.get("evidence_collection_started") is False
        and row.get("command_session_started") is False
    )


def build_hostess_staging_file_plan_receipt(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    staging_root: str = "hostess-staging",
    source_file_plan_path: Path | None = None,
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    acceptance_ready = hostess_staging_handoff_acceptance_receipt_source_ready(
        handoff_acceptance_receipt
    )
    file_plan_ready = studio_hostess_staging_file_plan_source_ready(
        staging_file_plan,
        handoff_acceptance_receipt,
    )
    staging_root_ready = hostess_staging_root_ready(staging_root)
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    status = (
        ACCEPTED_STATUS
        if decision == ACCEPTED_STATUS
        and decision_supported
        and acceptance_ready
        and file_plan_ready
        and staging_root_ready
        else REJECTED_STATUS
    )
    issue_code = None
    if status != ACCEPTED_STATUS:
        issue_code = (
            reason_code
            or handoff_acceptance_receipt.get("issue_code")
            or staging_file_plan.get("issue_code")
            or (
                "hostess.issue.hostess_staging_file_plan_receipt_decision"
                if not decision_supported
                else "hostess.issue.hostess_staging_file_plan_source_not_ready"
            )
        )
    request_rows = hostess_staging_file_plan_request_rows(
        handoff_acceptance_receipt,
        staging_file_plan,
        staging_root,
        status,
        issue_code,
    )
    file_rows = hostess_staging_file_plan_file_rows(
        staging_file_plan,
        staging_root,
        status,
        issue_code,
    )
    checks = hostess_staging_file_plan_receipt_checks(
        handoff_acceptance_receipt,
        staging_file_plan,
        request_rows,
        file_rows,
        staging_root,
        status,
        decision_supported,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == ACCEPTED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        request_rows = hostess_staging_file_plan_request_rows(
            handoff_acceptance_receipt,
            staging_file_plan,
            staging_root,
            status,
            issue_code,
        )
        file_rows = hostess_staging_file_plan_file_rows(
            staging_file_plan,
            staging_root,
            status,
            issue_code,
        )
    accepted_requests = [
        row
        for row in request_rows
        if row.get("staging_request_status") == PLANNED_STATUS
    ]
    rejected_requests = [
        row
        for row in request_rows
        if row.get("staging_request_status") == REJECTED_STATUS
    ]
    accepted_files = [
        row for row in file_rows if row.get("file_copy_plan_status") == PLANNED_STATUS
    ]
    rejected_files = [
        row
        for row in file_rows
        if row.get("file_copy_plan_status") == REJECTED_STATUS
    ]
    source_receipt_id = handoff_acceptance_receipt.get("receipt_id")
    manifest_id = staging_file_plan.get("manifest_id")
    receipt_id = (
        f"hostess.staging_file_plan_receipt.{source_receipt_id}.{manifest_id}"
        if isinstance(source_receipt_id, str)
        and source_receipt_id
        and isinstance(manifest_id, str)
        and manifest_id
        else "hostess.staging_file_plan_receipt.unknown"
    )
    pmb_review_required = (
        handoff_acceptance_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        handoff_acceptance_receipt.get("pmb_shell_handoff_review_ready") is True
    )
    return {
        "$schema": HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_handoff_acceptance_receipt_id": source_receipt_id,
        "source_handoff_acceptance_receipt_schema": (
            handoff_acceptance_receipt.get("$schema")
        ),
        "source_handoff_acceptance_receipt_status": (
            handoff_acceptance_receipt.get("status")
        ),
        "source_staging_handoff_envelope_id": (
            handoff_acceptance_receipt.get("source_staging_handoff_envelope_id")
        ),
        "source_file_plan_schema": staging_file_plan.get("$schema"),
        "source_file_plan_status": staging_file_plan.get("status"),
        "source_file_plan_path": (
            str(source_file_plan_path) if source_file_plan_path else None
        ),
        "manifest_id": staging_file_plan.get("manifest_id"),
        "project_id": staging_file_plan.get("project_id"),
        "project_revision": staging_file_plan.get("project_revision"),
        "selected_candidate_id": staging_file_plan.get("selected_candidate_id"),
        "checksum_algorithm": handoff_acceptance_receipt.get("checksum_algorithm"),
        "plan_checksum": handoff_acceptance_receipt.get("plan_checksum"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_STAGING_FILE_PLAN_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "file_copy_plan_owner": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "staging_root": staging_root,
        "staging_file_plan_reviewed": status == ACCEPTED_STATUS,
        "copy_plan_ready": status == ACCEPTED_STATUS,
        "stage_generated_shells_request_accepted": (
            handoff_acceptance_receipt.get(
                "stage_generated_shells_request_accepted"
            )
            is True
        ),
        "stage_generated_shells_started": False,
        "device_required": False,
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
        "schema_artifact_payloads_copied": False,
        "release_payloads_copied": False,
        "staging_payloads_copied": False,
        "file_copy_performed": False,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(handoff_acceptance_receipt),
        "request_count": len(request_rows),
        "accepted_request_count": len(accepted_requests),
        "rejected_request_count": len(rejected_requests),
        "file_count": len(file_rows),
        "accepted_file_count": len(accepted_files),
        "rejected_file_count": len(rejected_files),
        "target_request_count": sum(
            1 for row in request_rows if row.get("target_kind") is not None
        ),
        "shared_request_count": sum(
            1 for row in request_rows if row.get("target_kind") is None
        ),
        "staging_requests": request_rows,
        "staging_files": file_rows,
        "checks": checks,
        "next_required_action": (
            "hostess_copy_staging_files_from_reviewed_plan"
            if status == ACCEPTED_STATUS
            else "repair_or_decline_hostess_staging_file_plan"
        ),
    }


def validate_hostess_staging_file_plan_receipt(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    request_rows = hostess_staging_file_plan_request_dicts(receipt)
    file_rows = hostess_staging_file_plan_file_dicts(receipt)
    accepted_requests = [
        row
        for row in request_rows
        if row.get("staging_request_status") == PLANNED_STATUS
    ]
    rejected_requests = [
        row
        for row in request_rows
        if row.get("staging_request_status") == REJECTED_STATUS
    ]
    accepted_files = [
        row for row in file_rows if row.get("file_copy_plan_status") == PLANNED_STATUS
    ]
    rejected_files = [
        row
        for row in file_rows
        if row.get("file_copy_plan_status") == REJECTED_STATUS
    ]
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [
        entry for entry in embedded_checks if isinstance(entry, dict)
    ]
    embedded_failed = [
        entry for entry in embedded_check_dicts if entry.get("status") == FAIL_STATUS
    ]
    status = receipt.get("status")
    staging_root = receipt.get("staging_root")
    pmb_review_required = (
        handoff_acceptance_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_summary_matches_acceptance = (
        pmb_shell_handoff_review_summary_from_source(receipt)
        == pmb_shell_handoff_review_summary_from_source(
            handoff_acceptance_receipt
        )
    )
    checks = [
        check(
            "hostess.check.hostess_staging_file_plan_receipt.schema",
            receipt.get("$schema") == HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA,
            "Hostess staging file plan receipt schema is supported",
            "Hostess staging file plan receipt schema is unsupported",
            "hostess.issue.hostess_staging_file_plan_receipt_schema",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.status",
            status in {ACCEPTED_STATUS, REJECTED_STATUS}
            and (
                (status == ACCEPTED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess staging file plan receipt status is consistent",
            "Hostess staging file plan receipt status is inconsistent",
            "hostess.issue.hostess_staging_file_plan_receipt_status",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.execution_policy",
            receipt.get("execution_policy") == HOSTESS_STAGING_FILE_PLAN_RECEIPT_POLICY,
            "Hostess staging file plan receipt is schema-only",
            "Hostess staging file plan receipt execution policy drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_execution_policy",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.sources",
            receipt.get("source_handoff_acceptance_receipt_id")
            == handoff_acceptance_receipt.get("receipt_id")
            and receipt.get("source_handoff_acceptance_receipt_schema")
            == HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_SCHEMA
            and receipt.get("source_file_plan_schema")
            == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
            and receipt.get("manifest_id") == staging_file_plan.get("manifest_id")
            and receipt.get("project_id") == staging_file_plan.get("project_id")
            and receipt.get("project_revision")
            == staging_file_plan.get("project_revision")
            and receipt.get("selected_candidate_id")
            == staging_file_plan.get("selected_candidate_id"),
            "Hostess staging file plan sources match inputs",
            "Hostess staging file plan sources drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_source_mismatch",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.source_readiness",
            (
                status == ACCEPTED_STATUS
                and hostess_staging_handoff_acceptance_receipt_source_ready(
                    handoff_acceptance_receipt
                )
                and studio_hostess_staging_file_plan_source_ready(
                    staging_file_plan,
                    handoff_acceptance_receipt,
                )
                and hostess_staging_root_ready(staging_root)
            )
            or status == REJECTED_STATUS,
            "Hostess staging file plan sources are ready or rejected consistently",
            "Hostess staging file plan sources do not match receipt status",
            "hostess.issue.hostess_staging_file_plan_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != ACCEPTED_STATUS
            or (
                receipt.get("pmb_shell_handoff_review_required") is True
                and receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_acceptance
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            ),
            "accepted Hostess staging file plan preserves the PMB shell handoff gate",
            "accepted Hostess staging file plan dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_file_plan_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("file_copy_plan_owner") == HOSTESS_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "Hostess staging file plan receipt authority fields drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_authority",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.no_execution_started",
            hostess_staging_file_plan_receipt_unstarted(receipt),
            "Hostess staging file plan receipt has not started copying, execution, launch, or command sessions",
            "Hostess staging file plan receipt indicates copying, execution, launch, or command sessions",
            "hostess.issue.hostess_staging_file_plan_receipt_execution_started",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.requests",
            hostess_staging_file_plan_requests_match_sources(
                handoff_acceptance_receipt,
                staging_file_plan,
                request_rows,
                status,
            ),
            "Hostess staging file plan request rows match accepted handoff and source plan",
            "Hostess staging file plan request rows drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_request_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.files",
            hostess_staging_file_plan_files_match_source(
                staging_file_plan,
                file_rows,
                staging_root,
                status,
            ),
            "Hostess staging file rows match the source file plan",
            "Hostess staging file rows drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_file_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.destination_guards",
            hostess_staging_file_plan_rows_have_clean_destinations(
                request_rows,
                file_rows,
                staging_root,
            ),
            "Hostess staging destinations stay under the reviewed staging root and avoid legacy routes",
            "Hostess staging destinations or routes drifted toward unsafe or legacy paths",
            "hostess.issue.hostess_staging_file_plan_receipt_destination_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.counts",
            receipt.get("request_count") == len(request_rows)
            and receipt.get("accepted_request_count") == len(accepted_requests)
            and receipt.get("rejected_request_count") == len(rejected_requests)
            and receipt.get("file_count") == len(file_rows)
            and receipt.get("accepted_file_count") == len(accepted_files)
            and receipt.get("rejected_file_count") == len(rejected_files)
            and receipt.get("target_request_count")
            == sum(1 for row in request_rows if row.get("target_kind") is not None)
            and receipt.get("shared_request_count")
            == sum(1 for row in request_rows if row.get("target_kind") is None),
            "Hostess staging file plan receipt counts match nested records",
            "Hostess staging file plan receipt counts drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_count_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.scorecard",
            (
                status == ACCEPTED_STATUS
                and receipt.get("staging_file_plan_reviewed") is True
                and receipt.get("copy_plan_ready") is True
                and receipt.get("accepted_request_count")
                == staging_file_plan.get("request_count")
                and receipt.get("accepted_file_count")
                == staging_file_plan.get("planned_file_count")
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("staging_file_plan_reviewed") is False
                and receipt.get("copy_plan_ready") is False
            ),
            "Hostess staging file plan receipt scorecard matches receipt status",
            "Hostess staging file plan receipt scorecard drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_scorecard",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.embedded_checks",
            (
                status == ACCEPTED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess staging file plan receipt embedded checks match receipt status",
            "Hostess staging file plan receipt embedded checks do not match receipt status",
            "hostess.issue.hostess_staging_file_plan_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_STAGING_FILE_PLAN_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "copy_started": False,
        "staging_payloads_copied": False,
        "pmb_shell_handoff_review_required": receipt.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": receipt.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def build_hostess_staging_file_copy_receipt(
    staging_file_plan_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    source_ready = hostess_staging_file_plan_receipt_source_ready(
        staging_file_plan_receipt
    )
    preflight_checks = hostess_staging_file_copy_preflight_checks(
        staging_file_plan_receipt,
        staging_file_plan,
        decision_supported,
    )
    failed = [entry for entry in preflight_checks if entry["status"] == FAIL_STATUS]
    status = REJECTED_STATUS
    issue_code = (
        reason_code
        or staging_file_plan_receipt.get("issue_code")
        or (
            failed[0]["issue_code"]
            if failed
            else "hostess.issue.hostess_staging_file_copy_receipt_decision"
            if not decision_supported
            else None
        )
    )
    copy_rows = hostess_staging_file_copy_rejected_rows(
        staging_file_plan_receipt,
        issue_code,
    )
    copy_errors: list[str] = []
    if (
        decision == ACCEPTED_STATUS
        and decision_supported
        and source_ready
        and not failed
    ):
        copy_rows, copy_errors = perform_hostess_staging_file_copies(
            staging_file_plan_receipt
        )
        if copy_errors:
            issue_code = copy_errors[0]
        else:
            status = COMPLETED_STATUS
            issue_code = None
    copied_rows = [
        row for row in copy_rows if row.get("copy_status") == COMPLETED_STATUS
    ]
    rejected_rows = [
        row for row in copy_rows if row.get("copy_status") == REJECTED_STATUS
    ]
    receipt_id = (
        f"hostess.staging_file_copy_receipt.{staging_file_plan_receipt.get('receipt_id')}"
        if isinstance(staging_file_plan_receipt.get("receipt_id"), str)
        and staging_file_plan_receipt.get("receipt_id")
        else "hostess.staging_file_copy_receipt.unknown"
    )
    completed = status == COMPLETED_STATUS
    pmb_review_required = (
        staging_file_plan_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        staging_file_plan_receipt.get("pmb_shell_handoff_review_ready") is True
    )
    checks = hostess_staging_file_copy_receipt_checks(
        staging_file_plan_receipt,
        staging_file_plan,
        copy_rows,
        status,
        decision_supported,
        preflight_checks,
    )
    return {
        "$schema": HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_staging_file_plan_receipt_id": staging_file_plan_receipt.get(
            "receipt_id"
        ),
        "source_staging_file_plan_receipt_schema": staging_file_plan_receipt.get(
            "$schema"
        ),
        "source_staging_file_plan_receipt_status": staging_file_plan_receipt.get(
            "status"
        ),
        "source_file_plan_schema": staging_file_plan.get("$schema"),
        "source_file_plan_status": staging_file_plan.get("status"),
        "source_file_plan_path": staging_file_plan_receipt.get(
            "source_file_plan_path"
        ),
        "manifest_id": staging_file_plan_receipt.get("manifest_id"),
        "project_id": staging_file_plan_receipt.get("project_id"),
        "project_revision": staging_file_plan_receipt.get("project_revision"),
        "selected_candidate_id": staging_file_plan_receipt.get(
            "selected_candidate_id"
        ),
        "checksum_algorithm": staging_file_plan_receipt.get("checksum_algorithm"),
        "plan_checksum": staging_file_plan_receipt.get("plan_checksum"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_STAGING_FILE_COPY_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "file_copy_owner": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "staging_root": staging_file_plan_receipt.get("staging_root"),
        "copy_plan_ready": staging_file_plan_receipt.get("copy_plan_ready") is True,
        "file_copy_completed": completed,
        "stage_generated_shells_started": completed,
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "build_started": False,
        "copy_started": completed,
        "stage_started": completed,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "schema_artifact_payloads_copied": completed,
        "release_payloads_copied": False,
        "staging_payloads_copied": completed,
        "file_copy_performed": completed,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(staging_file_plan_receipt),
        "file_count": len(copy_rows),
        "copied_file_count": len(copied_rows),
        "rejected_file_count": len(rejected_rows),
        "copied_directory_count": sum(
            1 for row in copied_rows if row.get("source_kind") == "directory"
        ),
        "copied_regular_file_count": sum(
            1 for row in copied_rows if row.get("source_kind") == "file"
        ),
        "copy_rows": copy_rows,
        "checks": checks,
        "next_required_action": (
            "hostess_review_copied_staging_payloads_before_install_or_launch"
            if completed
            else "repair_or_decline_hostess_staging_file_copy"
        ),
    }


def validate_hostess_staging_file_copy_receipt(
    staging_file_plan_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    copy_rows = hostess_staging_file_copy_row_dicts(receipt)
    copied_rows = [
        row for row in copy_rows if row.get("copy_status") == COMPLETED_STATUS
    ]
    rejected_rows = [
        row for row in copy_rows if row.get("copy_status") == REJECTED_STATUS
    ]
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [
        entry for entry in embedded_checks if isinstance(entry, dict)
    ]
    embedded_failed = [
        entry for entry in embedded_check_dicts if entry.get("status") == FAIL_STATUS
    ]
    status = receipt.get("status")
    pmb_review_required = (
        staging_file_plan_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_summary_matches_plan = (
        pmb_shell_handoff_review_summary_from_source(receipt)
        == pmb_shell_handoff_review_summary_from_source(
            staging_file_plan_receipt
        )
    )
    checks = [
        check(
            "hostess.check.hostess_staging_file_copy_receipt.schema",
            receipt.get("$schema") == HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA,
            "Hostess staging file copy receipt schema is supported",
            "Hostess staging file copy receipt schema is unsupported",
            "hostess.issue.hostess_staging_file_copy_receipt_schema",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.status",
            status in {COMPLETED_STATUS, REJECTED_STATUS}
            and (
                (status == COMPLETED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess staging file copy receipt status is consistent",
            "Hostess staging file copy receipt status is inconsistent",
            "hostess.issue.hostess_staging_file_copy_receipt_status",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.execution_policy",
            receipt.get("execution_policy") == HOSTESS_STAGING_FILE_COPY_RECEIPT_POLICY,
            "Hostess staging file copy receipt uses filesystem-only staging policy",
            "Hostess staging file copy receipt execution policy drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_execution_policy",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.sources",
            receipt.get("source_staging_file_plan_receipt_id")
            == staging_file_plan_receipt.get("receipt_id")
            and receipt.get("source_staging_file_plan_receipt_schema")
            == HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA
            and receipt.get("source_file_plan_schema")
            == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
            and receipt.get("manifest_id") == staging_file_plan_receipt.get("manifest_id")
            and receipt.get("project_id") == staging_file_plan_receipt.get("project_id")
            and receipt.get("project_revision")
            == staging_file_plan_receipt.get("project_revision"),
            "Hostess staging file copy sources match inputs",
            "Hostess staging file copy sources drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_source_mismatch",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.source_readiness",
            (
                status == COMPLETED_STATUS
                and hostess_staging_file_plan_receipt_source_ready(
                    staging_file_plan_receipt
                )
                and staging_file_plan.get("$schema")
                == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
            )
            or status == REJECTED_STATUS,
            "Hostess staging file copy sources are ready or rejected consistently",
            "Hostess staging file copy sources do not match receipt status",
            "hostess.issue.hostess_staging_file_copy_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != COMPLETED_STATUS
            or (
                receipt.get("pmb_shell_handoff_review_required") is True
                and receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_plan
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            ),
            "completed Hostess staging file copy preserves the PMB shell handoff gate",
            "completed Hostess staging file copy dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_file_copy_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("file_copy_owner") == HOSTESS_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "Hostess staging file copy authority fields drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_authority",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.no_runtime_started",
            hostess_staging_file_copy_receipt_no_runtime_started(receipt),
            "Hostess staging file copy did not install, launch, run platform code, or start command sessions",
            "Hostess staging file copy indicates install, launch, platform/runtime execution, or command sessions",
            "hostess.issue.hostess_staging_file_copy_receipt_runtime_started",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.copy_state",
            (
                status == COMPLETED_STATUS
                and receipt.get("file_copy_completed") is True
                and receipt.get("copy_started") is True
                and receipt.get("stage_started") is True
                and receipt.get("stage_generated_shells_started") is True
                and receipt.get("schema_artifact_payloads_copied") is True
                and receipt.get("staging_payloads_copied") is True
                and receipt.get("file_copy_performed") is True
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("file_copy_completed") is False
                and receipt.get("copy_started") is False
                and receipt.get("staging_payloads_copied") is False
                and receipt.get("file_copy_performed") is False
            ),
            "Hostess staging file copy state matches receipt status",
            "Hostess staging file copy state drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_copy_state",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.rows",
            hostess_staging_file_copy_rows_match_plan_receipt(
                staging_file_plan_receipt,
                copy_rows,
                status,
            ),
            "Hostess staging file copy rows match the accepted file-plan receipt",
            "Hostess staging file copy rows drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_row_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.destinations_exist",
            status != COMPLETED_STATUS
            or hostess_staging_file_copy_destinations_exist(copy_rows),
            "Hostess staging file copy destinations exist on disk",
            "Hostess staging file copy destinations are missing on disk",
            "hostess.issue.hostess_staging_file_copy_receipt_destination_missing",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.counts",
            receipt.get("file_count") == len(copy_rows)
            and receipt.get("copied_file_count") == len(copied_rows)
            and receipt.get("rejected_file_count") == len(rejected_rows)
            and receipt.get("copied_directory_count")
            == sum(1 for row in copied_rows if row.get("source_kind") == "directory")
            and receipt.get("copied_regular_file_count")
            == sum(1 for row in copied_rows if row.get("source_kind") == "file"),
            "Hostess staging file copy counts match nested records",
            "Hostess staging file copy counts drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_count_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.embedded_checks",
            (
                status == COMPLETED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess staging file copy embedded checks match receipt status",
            "Hostess staging file copy embedded checks do not match receipt status",
            "hostess.issue.hostess_staging_file_copy_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_STAGING_FILE_COPY_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "copy_started": receipt.get("copy_started") is True,
        "staging_payloads_copied": receipt.get("staging_payloads_copied") is True,
        "pmb_shell_handoff_review_required": receipt.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": receipt.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def build_hostess_staged_payload_manifest_receipt(
    staging_file_copy_receipt: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    source_ready = hostess_staging_file_copy_receipt_source_ready(
        staging_file_copy_receipt
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    status = (
        REVIEWED_STATUS
        if decision == ACCEPTED_STATUS and decision_supported and source_ready
        else REJECTED_STATUS
    )
    issue_code = None
    if status != REVIEWED_STATUS:
        issue_code = (
            reason_code
            or staging_file_copy_receipt.get("issue_code")
            or (
                "hostess.issue.hostess_staged_payload_manifest_receipt_decision"
                if not decision_supported
                else "hostess.issue.hostess_staging_file_copy_source_not_ready"
            )
        )
    payload_rows = hostess_staged_payload_manifest_rows(
        staging_file_copy_receipt,
        status,
        issue_code,
    )
    checks = hostess_staged_payload_manifest_receipt_checks(
        staging_file_copy_receipt,
        payload_rows,
        status,
        decision_supported,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == REVIEWED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        payload_rows = hostess_staged_payload_manifest_rows(
            staging_file_copy_receipt,
            status,
            issue_code,
        )
    reviewed_rows = [
        row
        for row in payload_rows
        if row.get("payload_review_status") == REVIEWED_STATUS
    ]
    rejected_rows = [
        row
        for row in payload_rows
        if row.get("payload_review_status") == REJECTED_STATUS
    ]
    descriptor_rows = [
        row
        for row in reviewed_rows
        if row.get("artifact_kind") == SHELL_DESCRIPTOR_ARTIFACT_KIND
    ]
    downstream_shell_rows = hostess_downstream_shell_payload_rows(reviewed_rows)
    target_descriptor_rows = hostess_target_downstream_shell_payload_rows(
        reviewed_rows
    )
    target_manifold_handoff_rows = [
        row
        for row in target_descriptor_rows
        if row.get("artifact_kind") == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    ]
    receipt_id = (
        f"hostess.staged_payload_manifest_receipt.{staging_file_copy_receipt.get('receipt_id')}"
        if isinstance(staging_file_copy_receipt.get("receipt_id"), str)
        and staging_file_copy_receipt.get("receipt_id")
        else "hostess.staged_payload_manifest_receipt.unknown"
    )
    reviewed = status == REVIEWED_STATUS
    pmb_review_required = (
        staging_file_copy_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        staging_file_copy_receipt.get("pmb_shell_handoff_review_ready") is True
    )
    return {
        "$schema": HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_staging_file_copy_receipt_id": staging_file_copy_receipt.get(
            "receipt_id"
        ),
        "source_staging_file_copy_receipt_schema": staging_file_copy_receipt.get(
            "$schema"
        ),
        "source_staging_file_copy_receipt_status": staging_file_copy_receipt.get(
            "status"
        ),
        "source_file_copy_completed": (
            staging_file_copy_receipt.get("file_copy_completed") is True
        ),
        "source_staging_payloads_copied": (
            staging_file_copy_receipt.get("staging_payloads_copied") is True
        ),
        "manifest_id": staging_file_copy_receipt.get("manifest_id"),
        "project_id": staging_file_copy_receipt.get("project_id"),
        "project_revision": staging_file_copy_receipt.get("project_revision"),
        "selected_candidate_id": staging_file_copy_receipt.get(
            "selected_candidate_id"
        ),
        "checksum_algorithm": staging_file_copy_receipt.get("checksum_algorithm"),
        "plan_checksum": staging_file_copy_receipt.get("plan_checksum"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "payload_manifest_owner": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "downstream_shell_consumer_role": "downstream.shell.consume_staged_descriptors",
        "staging_root": staging_file_copy_receipt.get("staging_root"),
        "payload_manifest_reviewed": reviewed,
        "staged_payloads_available": reviewed,
        "downstream_shell_selection_ready": reviewed and bool(target_descriptor_rows),
        "makepad_shell_selection_ready": reviewed and bool(target_descriptor_rows),
        "legacy_reference_dependency_used": False,
        "downstream_shell_runtime_started": False,
        "device_required": False,
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
        "schema_artifact_payloads_copied": False,
        "release_payloads_copied": False,
        "staging_payloads_copied": False,
        "file_copy_performed": False,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(staging_file_copy_receipt),
        "payload_count": len(payload_rows),
        "reviewed_payload_count": len(reviewed_rows),
        "rejected_payload_count": len(rejected_rows),
        "descriptor_payload_count": len(descriptor_rows),
        "downstream_shell_payload_count": len(downstream_shell_rows),
        "target_descriptor_payload_count": len(target_descriptor_rows),
        "target_manifold_shell_handoff_payload_count": len(
            target_manifold_handoff_rows
        ),
        "shared_payload_count": sum(
            1 for row in reviewed_rows if row.get("target_kind") is None
        ),
        "payload_rows": payload_rows,
        "checks": checks,
        "next_required_action": (
            "downstream_shell_select_staged_descriptor_without_legacy_reference"
            if reviewed
            else "repair_or_decline_hostess_staged_payload_manifest"
        ),
    }


def validate_hostess_staged_payload_manifest_receipt(
    staging_file_copy_receipt: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    payload_rows = hostess_staged_payload_manifest_row_dicts(receipt)
    reviewed_rows = [
        row
        for row in payload_rows
        if row.get("payload_review_status") == REVIEWED_STATUS
    ]
    rejected_rows = [
        row
        for row in payload_rows
        if row.get("payload_review_status") == REJECTED_STATUS
    ]
    descriptor_rows = [
        row
        for row in reviewed_rows
        if row.get("artifact_kind") == SHELL_DESCRIPTOR_ARTIFACT_KIND
    ]
    downstream_shell_rows = hostess_downstream_shell_payload_rows(reviewed_rows)
    target_descriptor_rows = hostess_target_downstream_shell_payload_rows(
        reviewed_rows
    )
    target_manifold_handoff_rows = [
        row
        for row in target_descriptor_rows
        if row.get("artifact_kind") == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    ]
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [
        entry for entry in embedded_checks if isinstance(entry, dict)
    ]
    embedded_failed = [
        entry for entry in embedded_check_dicts if entry.get("status") == FAIL_STATUS
    ]
    status = receipt.get("status")
    pmb_review_required = (
        staging_file_copy_receipt.get("pmb_shell_handoff_review_required") is True
    )
    pmb_summary_matches_copy = (
        pmb_shell_handoff_review_summary_from_source(receipt)
        == pmb_shell_handoff_review_summary_from_source(
            staging_file_copy_receipt
        )
    )
    checks = [
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.schema",
            receipt.get("$schema")
            == HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA,
            "Hostess staged payload manifest receipt schema is supported",
            "Hostess staged payload manifest receipt schema is unsupported",
            "hostess.issue.hostess_staged_payload_manifest_receipt_schema",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.status",
            status in {REVIEWED_STATUS, REJECTED_STATUS}
            and (
                (status == REVIEWED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess staged payload manifest receipt status is consistent",
            "Hostess staged payload manifest receipt status is inconsistent",
            "hostess.issue.hostess_staged_payload_manifest_receipt_status",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.execution_policy",
            receipt.get("execution_policy")
            == HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_POLICY,
            "Hostess staged payload manifest receipt is schema-only review",
            "Hostess staged payload manifest receipt execution policy drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_execution_policy",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.sources",
            receipt.get("source_staging_file_copy_receipt_id")
            == staging_file_copy_receipt.get("receipt_id")
            and receipt.get("source_staging_file_copy_receipt_schema")
            == HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA
            and receipt.get("manifest_id") == staging_file_copy_receipt.get("manifest_id")
            and receipt.get("project_id") == staging_file_copy_receipt.get("project_id")
            and receipt.get("project_revision")
            == staging_file_copy_receipt.get("project_revision"),
            "Hostess staged payload manifest sources match inputs",
            "Hostess staged payload manifest sources drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_source_mismatch",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.source_readiness",
            (
                status == REVIEWED_STATUS
                and hostess_staging_file_copy_receipt_source_ready(
                    staging_file_copy_receipt
                )
            )
            or status == REJECTED_STATUS,
            "Hostess staged payload manifest source is ready or rejected consistently",
            "Hostess staged payload manifest source does not match receipt status",
            "hostess.issue.hostess_staging_file_copy_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != REVIEWED_STATUS
            or (
                receipt.get("pmb_shell_handoff_review_required") is True
                and receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_copy
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            ),
            "reviewed Hostess staged payload manifest preserves the PMB shell handoff gate",
            "reviewed Hostess staged payload manifest dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staged_payload_manifest_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("payload_manifest_owner") == HOSTESS_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "Hostess staged payload manifest authority fields drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_authority",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.no_runtime_started",
            hostess_staged_payload_manifest_receipt_no_runtime_started(receipt),
            "Hostess staged payload manifest did not copy, install, launch, execute, or start command sessions",
            "Hostess staged payload manifest indicates copy, install, launch, runtime execution, or command sessions",
            "hostess.issue.hostess_staged_payload_manifest_receipt_runtime_started",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.payload_rows",
            hostess_staged_payload_rows_match_copy_receipt(
                staging_file_copy_receipt,
                payload_rows,
                status,
            ),
            "Hostess staged payload manifest rows match copied payload evidence",
            "Hostess staged payload manifest rows drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_payload_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.downstream_selection",
            (
                status == REVIEWED_STATUS
                and receipt.get("downstream_shell_selection_ready") is True
                and receipt.get("makepad_shell_selection_ready") is True
                and len(target_descriptor_rows) > 0
                and all(
                    row.get("downstream_shell_descriptor_ready") is True
                    for row in target_descriptor_rows
                )
                and receipt.get("legacy_reference_dependency_used") is False
            )
            or status == REJECTED_STATUS,
            "Hostess staged payload manifest exposes downstream shell descriptors without legacy reference dependency",
            "Hostess staged payload manifest is not ready for downstream shell descriptor selection",
            "hostess.issue.hostess_staged_payload_manifest_receipt_downstream_selection",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.counts",
            receipt.get("payload_count") == len(payload_rows)
            and receipt.get("reviewed_payload_count") == len(reviewed_rows)
            and receipt.get("rejected_payload_count") == len(rejected_rows)
            and receipt.get("descriptor_payload_count") == len(descriptor_rows)
            and receipt.get("downstream_shell_payload_count")
            == len(downstream_shell_rows)
            and receipt.get("target_descriptor_payload_count")
            == len(target_descriptor_rows)
            and receipt.get("target_manifold_shell_handoff_payload_count")
            == len(target_manifold_handoff_rows)
            and receipt.get("shared_payload_count")
            == sum(1 for row in reviewed_rows if row.get("target_kind") is None),
            "Hostess staged payload manifest counts match nested records",
            "Hostess staged payload manifest counts drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_count_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.embedded_checks",
            (
                status == REVIEWED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess staged payload manifest embedded checks match receipt status",
            "Hostess staged payload manifest embedded checks do not match receipt status",
            "hostess.issue.hostess_staged_payload_manifest_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "copy_started": False,
        "staging_payloads_copied": False,
        "downstream_shell_selection_ready": receipt.get(
            "downstream_shell_selection_ready"
        )
        is True,
        "makepad_shell_selection_ready": receipt.get(
            "makepad_shell_selection_ready"
        )
        is True,
        "pmb_shell_handoff_review_required": receipt.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": receipt.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def downstream_shell_artifact_priority(artifact_kind: Any) -> int:
    try:
        return DOWNSTREAM_SHELL_SELECTION_ARTIFACT_KINDS.index(artifact_kind)
    except ValueError:
        return len(DOWNSTREAM_SHELL_SELECTION_ARTIFACT_KINDS)


def is_downstream_shell_selection_artifact_kind(artifact_kind: Any) -> bool:
    return artifact_kind in DOWNSTREAM_SHELL_SELECTION_ARTIFACT_KINDS


def hostess_downstream_shell_payload_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("payload_review_status") == REVIEWED_STATUS
        and is_downstream_shell_selection_artifact_kind(row.get("artifact_kind"))
    ]


def hostess_target_downstream_shell_payload_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        row
        for row in hostess_downstream_shell_payload_rows(rows)
        if row.get("target_kind") is not None
        and isinstance(row.get("graph_id"), str)
        and isinstance(row.get("consumer_id"), str)
    ]


def build_hostess_downstream_shell_selection_receipt(
    staged_payload_manifest_receipt: dict[str, Any],
    target_kind: str | None = None,
    graph_id: str | None = None,
    consumer_id: str | None = None,
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    source_ready = hostess_staged_payload_manifest_receipt_source_ready(
        staged_payload_manifest_receipt
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    candidate_rows = hostess_downstream_shell_selection_candidate_rows(
        staged_payload_manifest_receipt
    )
    matching_rows = hostess_downstream_shell_selection_candidate_rows(
        staged_payload_manifest_receipt,
        target_kind=target_kind,
        graph_id=graph_id,
        consumer_id=consumer_id,
    )
    selected_source_row = (
        matching_rows[0]
        if decision == ACCEPTED_STATUS
        and decision_supported
        and source_ready
        and matching_rows
        else None
    )
    status = SELECTED_STATUS if selected_source_row is not None else REJECTED_STATUS
    issue_code = None
    if status != SELECTED_STATUS:
        issue_code = (
            reason_code
            or staged_payload_manifest_receipt.get("issue_code")
            or (
                "hostess.issue.hostess_downstream_shell_selection_receipt_decision"
                if not decision_supported
                else "hostess.issue.hostess_staged_payload_manifest_source_not_ready"
                if not source_ready
                else "hostess.issue.hostess_downstream_shell_selection_no_candidate"
            )
        )
    selection_rows = (
        [
            hostess_downstream_shell_selection_row(
                staged_payload_manifest_receipt,
                selected_source_row,
            )
        ]
        if selected_source_row is not None
        else []
    )
    selected_row = selection_rows[0] if selection_rows else None
    checks = hostess_downstream_shell_selection_receipt_checks(
        staged_payload_manifest_receipt,
        selection_rows,
        status,
        decision_supported,
        target_kind=target_kind,
        graph_id=graph_id,
        consumer_id=consumer_id,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == SELECTED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        selection_rows = []
        selected_row = None
    receipt_id = (
        "hostess.downstream_shell_selection_receipt."
        f"{staged_payload_manifest_receipt.get('receipt_id')}"
        if isinstance(staged_payload_manifest_receipt.get("receipt_id"), str)
        and staged_payload_manifest_receipt.get("receipt_id")
        else "hostess.downstream_shell_selection_receipt.unknown"
    )
    selected = status == SELECTED_STATUS
    selected_artifact_kind = (
        selected_row.get("selected_artifact_kind") if selected_row else None
    )
    manifold_handoff_selected = (
        selected_artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    )
    makepad_descriptor_selected = (
        selected_artifact_kind == SHELL_DESCRIPTOR_ARTIFACT_KIND
    )
    pmb_review_required = (
        staged_payload_manifest_receipt.get("pmb_shell_handoff_review_required")
        is True
    )
    pmb_review_ready = (
        staged_payload_manifest_receipt.get("pmb_shell_handoff_review_ready") is True
    )
    return {
        "$schema": HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_staged_payload_manifest_receipt_id": (
            staged_payload_manifest_receipt.get("receipt_id")
        ),
        "source_staged_payload_manifest_receipt_schema": (
            staged_payload_manifest_receipt.get("$schema")
        ),
        "source_staged_payload_manifest_receipt_status": (
            staged_payload_manifest_receipt.get("status")
        ),
        "source_payload_manifest_reviewed": (
            staged_payload_manifest_receipt.get("payload_manifest_reviewed") is True
        ),
        "source_staged_payloads_available": (
            staged_payload_manifest_receipt.get("staged_payloads_available") is True
        ),
        "manifest_id": staged_payload_manifest_receipt.get("manifest_id"),
        "project_id": staged_payload_manifest_receipt.get("project_id"),
        "project_revision": staged_payload_manifest_receipt.get(
            "project_revision"
        ),
        "selected_candidate_id": staged_payload_manifest_receipt.get(
            "selected_candidate_id"
        ),
        "checksum_algorithm": staged_payload_manifest_receipt.get(
            "checksum_algorithm"
        ),
        "plan_checksum": staged_payload_manifest_receipt.get("plan_checksum"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "selection_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "payload_manifest_owner": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "downstream_shell_consumer_role": "downstream.shell.consume_staged_descriptor",
        "requested_target_kind": target_kind,
        "requested_graph_id": graph_id,
        "requested_consumer_id": consumer_id,
        "staging_root": staged_payload_manifest_receipt.get("staging_root"),
        "downstream_shell_selection_ready": selected,
        "downstream_shell_descriptor_selected": selected,
        "makepad_shell_selection_ready": selected,
        "manifold_shell_handoff_selected": manifold_handoff_selected,
        "makepad_shell_descriptor_selected": makepad_descriptor_selected,
        "selected_payload_row_id": (
            selected_row.get("source_payload_row_id") if selected_row else None
        ),
        "selected_payload_path": (
            selected_row.get("selected_payload_path") if selected_row else None
        ),
        "selected_artifact_kind": (
            selected_row.get("selected_artifact_kind") if selected_row else None
        ),
        "selected_target_kind": (
            selected_row.get("target_kind") if selected_row else None
        ),
        "selected_graph_id": selected_row.get("graph_id") if selected_row else None,
        "selected_consumer_id": (
            selected_row.get("consumer_id") if selected_row else None
        ),
        "legacy_reference_dependency_used": False,
        "downstream_shell_runtime_started": False,
        "device_required": False,
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
        "schema_artifact_payloads_copied": False,
        "release_payloads_copied": False,
        "staging_payloads_copied": False,
        "file_copy_performed": False,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(
            staged_payload_manifest_receipt
        ),
        "candidate_count": len(candidate_rows),
        "matching_candidate_count": len(matching_rows),
        "selected_candidate_count": 1 if selected else 0,
        "selection_rows": selection_rows,
        "checks": checks,
        "next_required_action": (
            "manifold_review_selected_shell_handoff_without_launch"
            if manifold_handoff_selected
            else "makepad_consume_selected_staged_descriptor_without_launch"
            if makepad_descriptor_selected
            else "repair_or_decline_downstream_shell_selection"
        ),
    }


def validate_hostess_downstream_shell_selection_receipt(
    staged_payload_manifest_receipt: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    selection_rows = hostess_downstream_shell_selection_row_dicts(receipt)
    selected_rows = [
        row
        for row in selection_rows
        if row.get("selection_status") == SELECTED_STATUS
    ]
    matching_rows = hostess_downstream_shell_selection_candidate_rows(
        staged_payload_manifest_receipt,
        target_kind=receipt.get("requested_target_kind"),
        graph_id=receipt.get("requested_graph_id"),
        consumer_id=receipt.get("requested_consumer_id"),
    )
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [
        entry for entry in embedded_checks if isinstance(entry, dict)
    ]
    embedded_failed = [
        entry for entry in embedded_check_dicts if entry.get("status") == FAIL_STATUS
    ]
    status = receipt.get("status")
    pmb_review_required = (
        staged_payload_manifest_receipt.get("pmb_shell_handoff_review_required")
        is True
    )
    pmb_summary_matches_manifest = (
        pmb_shell_handoff_review_summary_from_source(receipt)
        == pmb_shell_handoff_review_summary_from_source(
            staged_payload_manifest_receipt
        )
    )
    selected_row = selected_rows[0] if len(selected_rows) == 1 else None
    selected_artifact_kind = receipt.get("selected_artifact_kind")
    manifold_handoff_selected = (
        selected_artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    )
    makepad_descriptor_selected = (
        selected_artifact_kind == SHELL_DESCRIPTOR_ARTIFACT_KIND
    )
    checks = [
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.schema",
            receipt.get("$schema")
            == HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA,
            "Hostess downstream shell selection receipt schema is supported",
            "Hostess downstream shell selection receipt schema is unsupported",
            "hostess.issue.hostess_downstream_shell_selection_receipt_schema",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.status",
            status in {SELECTED_STATUS, REJECTED_STATUS}
            and (
                (status == SELECTED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess downstream shell selection receipt status is consistent",
            "Hostess downstream shell selection receipt status is inconsistent",
            "hostess.issue.hostess_downstream_shell_selection_receipt_status",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.execution_policy",
            receipt.get("execution_policy")
            == HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_POLICY,
            "Hostess downstream shell selection is schema-only",
            "Hostess downstream shell selection execution policy drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_execution_policy",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.sources",
            receipt.get("source_staged_payload_manifest_receipt_id")
            == staged_payload_manifest_receipt.get("receipt_id")
            and receipt.get("source_staged_payload_manifest_receipt_schema")
            == HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA
            and receipt.get("manifest_id")
            == staged_payload_manifest_receipt.get("manifest_id")
            and receipt.get("project_id")
            == staged_payload_manifest_receipt.get("project_id")
            and receipt.get("project_revision")
            == staged_payload_manifest_receipt.get("project_revision"),
            "Hostess downstream shell selection source manifest matches input",
            "Hostess downstream shell selection source manifest drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_source_mismatch",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.source_readiness",
            (
                status == SELECTED_STATUS
                and hostess_staged_payload_manifest_receipt_source_ready(
                    staged_payload_manifest_receipt
                )
            )
            or status == REJECTED_STATUS,
            "Hostess downstream shell selection source is ready or rejected consistently",
            "Hostess downstream shell selection source is not ready",
            "hostess.issue.hostess_staged_payload_manifest_source_not_ready",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != SELECTED_STATUS
            or (
                receipt.get("pmb_shell_handoff_review_required") is True
                and receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_manifest
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            ),
            "selected downstream shell descriptor preserves the PMB shell handoff gate",
            "selected downstream shell descriptor dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_downstream_shell_selection_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("selection_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("payload_manifest_owner") == HOSTESS_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess owns selection while Manifold remains command/session authority",
            "Hostess downstream shell selection authority fields drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_authority",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.no_runtime_started",
            hostess_downstream_shell_selection_receipt_no_runtime_started(receipt),
            "Hostess downstream shell selection did not copy, install, launch, execute, or start command sessions",
            "Hostess downstream shell selection indicates copy, install, launch, runtime execution, or command sessions",
            "hostess.issue.hostess_downstream_shell_selection_receipt_runtime_started",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.selection_rows",
            hostess_downstream_shell_selection_rows_match_manifest(
                staged_payload_manifest_receipt,
                selection_rows,
                status,
            ),
            "Hostess downstream shell selection rows match reviewed manifest descriptors",
            "Hostess downstream shell selection rows drifted from the reviewed manifest",
            "hostess.issue.hostess_downstream_shell_selection_receipt_selection_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.selected_descriptor",
            (
                status == SELECTED_STATUS
                and selected_row is not None
                and receipt.get("downstream_shell_selection_ready") is True
                and receipt.get("downstream_shell_descriptor_selected") is True
                and receipt.get("makepad_shell_selection_ready") is True
                and receipt.get("manifold_shell_handoff_selected")
                is manifold_handoff_selected
                and receipt.get("makepad_shell_descriptor_selected")
                is makepad_descriptor_selected
                and receipt.get("selected_payload_row_id")
                == selected_row.get("source_payload_row_id")
                and receipt.get("selected_payload_path")
                == selected_row.get("selected_payload_path")
                and is_downstream_shell_selection_artifact_kind(
                    selected_artifact_kind
                )
                and receipt.get("selected_target_kind")
                == selected_row.get("target_kind")
                and receipt.get("selected_graph_id") == selected_row.get("graph_id")
                and receipt.get("selected_consumer_id")
                == selected_row.get("consumer_id")
                and bool(matching_rows)
                and selected_row.get("source_payload_row_id")
                == matching_rows[0].get("payload_row_id")
                and receipt.get("legacy_reference_dependency_used") is False
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("downstream_shell_selection_ready") is False
                and receipt.get("downstream_shell_descriptor_selected") is False
                and receipt.get("makepad_shell_selection_ready") is False
                and receipt.get("manifold_shell_handoff_selected") is False
                and receipt.get("makepad_shell_descriptor_selected") is False
                and receipt.get("selected_payload_row_id") is None
                and receipt.get("selected_payload_path") is None
            ),
            "Hostess downstream shell descriptor selection is consistent",
            "Hostess downstream shell descriptor selection drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_descriptor_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.counts",
            receipt.get("candidate_count")
            == len(
                hostess_downstream_shell_selection_candidate_rows(
                    staged_payload_manifest_receipt
                )
            )
            and receipt.get("matching_candidate_count") == len(matching_rows)
            and receipt.get("selected_candidate_count")
            == (1 if status == SELECTED_STATUS else 0)
            and len(selected_rows) == (1 if status == SELECTED_STATUS else 0),
            "Hostess downstream shell selection counts match nested records",
            "Hostess downstream shell selection counts drifted",
            "hostess.issue.hostess_downstream_shell_selection_receipt_count_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.embedded_checks",
            (
                status == SELECTED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess downstream shell selection embedded checks match receipt status",
            "Hostess downstream shell selection embedded checks do not match receipt status",
            "hostess.issue.hostess_downstream_shell_selection_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "copy_started": False,
        "staging_payloads_copied": False,
        "downstream_shell_selection_ready": receipt.get(
            "downstream_shell_selection_ready"
        )
        is True,
        "makepad_shell_selection_ready": receipt.get(
            "makepad_shell_selection_ready"
        )
        is True,
        "manifold_shell_handoff_selected": receipt.get(
            "manifold_shell_handoff_selected"
        )
        is True,
        "makepad_shell_descriptor_selected": receipt.get(
            "makepad_shell_descriptor_selected"
        )
        is True,
        "pmb_shell_handoff_review_required": receipt.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": receipt.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def hostess_downstream_shell_selection_receipt_checks(
    staged_payload_manifest_receipt: dict[str, Any],
    selection_rows: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
    target_kind: str | None = None,
    graph_id: str | None = None,
    consumer_id: str | None = None,
) -> list[dict[str, Any]]:
    matching_rows = hostess_downstream_shell_selection_candidate_rows(
        staged_payload_manifest_receipt,
        target_kind=target_kind,
        graph_id=graph_id,
        consumer_id=consumer_id,
    )
    pmb_review_required = (
        staged_payload_manifest_receipt.get("pmb_shell_handoff_review_required")
        is True
    )
    return [
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.manifest_source",
            hostess_staged_payload_manifest_receipt_source_ready(
                staged_payload_manifest_receipt
            ),
            "Hostess staged payload manifest is reviewed and ready for downstream selection",
            "Hostess staged payload manifest is missing, rejected, or drifted",
            staged_payload_manifest_receipt.get("issue_code")
            or "hostess.issue.hostess_staged_payload_manifest_source_not_ready",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != SELECTED_STATUS
            or (
                staged_payload_manifest_receipt.get(
                    "pmb_shell_handoff_review_ready"
                )
                is True
                and pmb_shell_handoff_readiness_result_summary_valid(
                    staged_payload_manifest_receipt
                )
            ),
            "selected downstream shell descriptor preserves the PMB shell handoff gate",
            "selected downstream shell descriptor dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_downstream_shell_selection_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.decision",
            decision_supported,
            "Hostess downstream shell selection receipt decision is supported",
            "Hostess downstream shell selection receipt decision is unsupported",
            "hostess.issue.hostess_downstream_shell_selection_receipt_decision",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.candidate",
            status != SELECTED_STATUS or bool(matching_rows),
            "Hostess downstream shell selection has a matching descriptor candidate",
            "Hostess downstream shell selection has no matching descriptor candidate",
            "hostess.issue.hostess_downstream_shell_selection_no_candidate",
        ),
        check(
            "hostess.check.hostess_downstream_shell_selection_receipt.rows",
            hostess_downstream_shell_selection_rows_match_manifest(
                staged_payload_manifest_receipt,
                selection_rows,
                status,
            ),
            "Hostess downstream shell selection rows match reviewed manifest descriptors",
            "Hostess downstream shell selection rows drifted from reviewed manifest descriptors",
            "hostess.issue.hostess_downstream_shell_selection_receipt_selection_drift",
        ),
    ]


def hostess_downstream_shell_selection_row(
    staged_payload_manifest_receipt: dict[str, Any],
    source_row: dict[str, Any],
) -> dict[str, Any]:
    payload_row_id = source_row.get("payload_row_id")
    selected_artifact_kind = source_row.get("artifact_kind")
    manifold_handoff_selected = (
        selected_artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    )
    makepad_descriptor_selected = (
        selected_artifact_kind == SHELL_DESCRIPTOR_ARTIFACT_KIND
    )
    return {
        "selection_row_id": (
            f"hostess.downstream_shell_selection.{payload_row_id}"
            if isinstance(payload_row_id, str) and payload_row_id
            else "hostess.downstream_shell_selection.unknown"
        ),
        "source_staged_payload_manifest_receipt_id": (
            staged_payload_manifest_receipt.get("receipt_id")
        ),
        "source_payload_row_id": payload_row_id,
        "source_copy_row_id": source_row.get("source_copy_row_id"),
        "source_staging_file_row_id": source_row.get(
            "source_staging_file_row_id"
        ),
        "source_request_id": source_row.get("source_request_id"),
        "source_file_index": source_row.get("source_file_index"),
        "selected_artifact_kind": selected_artifact_kind,
        "selected_payload_path": source_row.get("payload_path"),
        "payload_kind": source_row.get("payload_kind"),
        "payload_exists": source_row.get("payload_exists") is True,
        "payload_under_staging_root": (
            source_row.get("payload_under_staging_root") is True
        ),
        "target_kind": source_row.get("target_kind"),
        "graph_id": source_row.get("graph_id"),
        "consumer_id": source_row.get("consumer_id"),
        "route_hints": source_row.get("route_hints"),
        "source_action_ids": source_row.get("source_action_ids"),
        "source_route_kinds": source_row.get("source_route_kinds"),
        "selection_status": SELECTED_STATUS,
        "issue_code": None,
        "downstream_shell_descriptor_ready": True,
        "manifold_shell_handoff_candidate": (
            source_row.get("manifold_shell_handoff_candidate") is True
        ),
        "manifold_shell_handoff_selected": manifold_handoff_selected,
        "makepad_shell_selection_candidate": True,
        "makepad_shell_descriptor_selected": makepad_descriptor_selected,
        "downstream_shell_artifact_priority": downstream_shell_artifact_priority(
            selected_artifact_kind
        ),
        "legacy_reference_dependency_used": False,
        "downstream_shell_runtime_started": False,
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_started": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
    }


def hostess_downstream_shell_selection_candidate_rows(
    staged_payload_manifest_receipt: dict[str, Any],
    target_kind: str | None = None,
    graph_id: str | None = None,
    consumer_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for row in hostess_staged_payload_manifest_row_dicts(
        staged_payload_manifest_receipt
    ):
        payload_path = row.get("payload_path")
        if not (
            row.get("payload_review_status") == REVIEWED_STATUS
            and is_downstream_shell_selection_artifact_kind(
                row.get("artifact_kind")
            )
            and row.get("downstream_shell_descriptor_ready") is True
            and row.get("makepad_shell_selection_candidate") is True
            and row.get("payload_exists") is True
            and row.get("payload_under_staging_root") is True
            and isinstance(row.get("target_kind"), str)
            and bool(row.get("target_kind"))
            and isinstance(row.get("graph_id"), str)
            and bool(row.get("graph_id"))
            and isinstance(row.get("consumer_id"), str)
            and bool(row.get("consumer_id"))
            and isinstance(payload_path, str)
            and Path(payload_path).exists()
            and not has_legacy_route_or_path(row)
            and hostess_staged_payload_row_no_runtime_started(row)
        ):
            continue
        if target_kind is not None and row.get("target_kind") != target_kind:
            continue
        if graph_id is not None and row.get("graph_id") != graph_id:
            continue
        if consumer_id is not None and row.get("consumer_id") != consumer_id:
            continue
        rows.append(row)
    rows.sort(
        key=lambda row: (
            downstream_shell_artifact_priority(row.get("artifact_kind")),
            str(row.get("target_kind") or ""),
            str(row.get("graph_id") or ""),
            str(row.get("consumer_id") or ""),
            str(row.get("payload_row_id") or ""),
        )
    )
    return rows


def hostess_downstream_shell_selection_row_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = receipt.get("selection_rows", [])
    if not isinstance(rows, list):
        return []
    return [entry for entry in rows if isinstance(entry, dict)]


def hostess_staged_payload_manifest_receipt_source_ready(
    receipt: dict[str, Any],
) -> bool:
    target_descriptor_rows = hostess_downstream_shell_selection_candidate_rows(
        receipt
    )
    return (
        receipt.get("$schema") == HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA
        and receipt.get("status") == REVIEWED_STATUS
        and receipt.get("issue_code") is None
        and receipt.get("receipt_owner") == HOSTESS_OWNER
        and receipt.get("staging_owner") == HOSTESS_OWNER
        and receipt.get("payload_manifest_owner") == HOSTESS_OWNER
        and receipt.get("command_session_authority") == MANIFOLD_OWNER
        and receipt.get("payload_manifest_reviewed") is True
        and receipt.get("staged_payloads_available") is True
        and receipt.get("downstream_shell_selection_ready") is True
        and receipt.get("makepad_shell_selection_ready") is True
        and receipt.get("target_descriptor_payload_count")
        == len(target_descriptor_rows)
        and len(target_descriptor_rows) > 0
        and hostess_staged_payload_manifest_receipt_no_runtime_started(receipt)
        and (
            receipt.get("pmb_shell_handoff_review_required") is not True
            or (
                receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            )
        )
    )


def hostess_downstream_shell_selection_rows_match_manifest(
    staged_payload_manifest_receipt: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {SELECTED_STATUS, REJECTED_STATUS}:
        return False
    if status == REJECTED_STATUS:
        return rows == []
    if len(rows) != 1:
        return False
    row = rows[0]
    by_id = {
        source_row.get("payload_row_id"): source_row
        for source_row in hostess_downstream_shell_selection_candidate_rows(
            staged_payload_manifest_receipt
        )
    }
    source_row = by_id.get(row.get("source_payload_row_id"))
    if not isinstance(source_row, dict):
        return False
    for key, source_key in (
        ("source_copy_row_id", "source_copy_row_id"),
        ("source_staging_file_row_id", "source_staging_file_row_id"),
        ("source_request_id", "source_request_id"),
        ("source_file_index", "source_file_index"),
        ("selected_artifact_kind", "artifact_kind"),
        ("selected_payload_path", "payload_path"),
        ("payload_kind", "payload_kind"),
        ("target_kind", "target_kind"),
        ("graph_id", "graph_id"),
        ("consumer_id", "consumer_id"),
        ("route_hints", "route_hints"),
        ("source_action_ids", "source_action_ids"),
        ("source_route_kinds", "source_route_kinds"),
    ):
        if row.get(key) != source_row.get(source_key):
            return False
    payload_path = row.get("selected_payload_path")
    selected_artifact_kind = row.get("selected_artifact_kind")
    manifold_handoff_selected = (
        selected_artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
    )
    makepad_descriptor_selected = (
        selected_artifact_kind == SHELL_DESCRIPTOR_ARTIFACT_KIND
    )
    return (
        row.get("source_staged_payload_manifest_receipt_id")
        == staged_payload_manifest_receipt.get("receipt_id")
        and row.get("selection_status") == SELECTED_STATUS
        and row.get("issue_code") is None
        and row.get("payload_exists") is True
        and row.get("payload_under_staging_root") is True
        and isinstance(payload_path, str)
        and Path(payload_path).exists()
        and is_downstream_shell_selection_artifact_kind(selected_artifact_kind)
        and row.get("downstream_shell_descriptor_ready") is True
        and row.get("manifold_shell_handoff_candidate")
        is (source_row.get("manifold_shell_handoff_candidate") is True)
        and row.get("manifold_shell_handoff_selected")
        is manifold_handoff_selected
        and row.get("makepad_shell_selection_candidate") is True
        and row.get("makepad_shell_descriptor_selected")
        is makepad_descriptor_selected
        and row.get("downstream_shell_artifact_priority")
        == downstream_shell_artifact_priority(selected_artifact_kind)
        and not has_legacy_route_or_path(row)
        and hostess_downstream_shell_selection_row_no_runtime_started(row)
    )


def hostess_downstream_shell_selection_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("legacy_reference_dependency_used") is False
        and receipt.get("downstream_shell_runtime_started") is False
        and receipt.get("device_required") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("execution_performed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("build_started") is False
        and receipt.get("copy_started") is False
        and receipt.get("stage_started") is False
        and receipt.get("install_started") is False
        and receipt.get("launch_started") is False
        and receipt.get("evidence_collection_started") is False
        and receipt.get("command_session_started") is False
        and receipt.get("schema_artifact_payloads_copied") is False
        and receipt.get("release_payloads_copied") is False
        and receipt.get("staging_payloads_copied") is False
        and receipt.get("file_copy_performed") is False
    )


def hostess_downstream_shell_selection_row_no_runtime_started(
    row: dict[str, Any],
) -> bool:
    return (
        row.get("legacy_reference_dependency_used") is False
        and row.get("downstream_shell_runtime_started") is False
        and row.get("device_required") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("platform_execution_allowed") is False
        and row.get("studio_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("build_started") is False
        and row.get("copy_started") is False
        and row.get("stage_started") is False
        and row.get("install_started") is False
        and row.get("launch_started") is False
        and row.get("evidence_collection_started") is False
        and row.get("command_session_started") is False
    )


def hostess_staged_payload_manifest_receipt_checks(
    staging_file_copy_receipt: dict[str, Any],
    payload_rows: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = (
        staging_file_copy_receipt.get("pmb_shell_handoff_review_required") is True
    )
    target_descriptor_rows = hostess_target_downstream_shell_payload_rows(
        payload_rows
    )
    return [
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.copy_source",
            hostess_staging_file_copy_receipt_source_ready(
                staging_file_copy_receipt
            ),
            "Hostess staging file-copy receipt is completed and ready for payload review",
            "Hostess staging file-copy receipt is missing, rejected, or drifted",
            staging_file_copy_receipt.get("issue_code")
            or "hostess.issue.hostess_staging_file_copy_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != REVIEWED_STATUS
            or (
                staging_file_copy_receipt.get("pmb_shell_handoff_review_ready")
                is True
                and pmb_shell_handoff_readiness_result_summary_valid(
                    staging_file_copy_receipt
                )
            ),
            "reviewed Hostess staged payload manifest preserves the PMB shell handoff gate",
            "reviewed Hostess staged payload manifest dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staged_payload_manifest_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.decision",
            decision_supported,
            "Hostess staged payload manifest receipt decision is supported",
            "Hostess staged payload manifest receipt decision is unsupported",
            "hostess.issue.hostess_staged_payload_manifest_receipt_decision",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.payload_rows",
            hostess_staged_payload_rows_match_copy_receipt(
                staging_file_copy_receipt,
                payload_rows,
                status,
            ),
            "Hostess staged payload manifest rows match copied payload evidence",
            "Hostess staged payload manifest rows drifted",
            "hostess.issue.hostess_staged_payload_manifest_receipt_payload_drift",
        ),
        check(
            "hostess.check.hostess_staged_payload_manifest_receipt.downstream_selection",
            status != REVIEWED_STATUS
            or (
                bool(target_descriptor_rows)
                and all(
                    row.get("downstream_shell_descriptor_ready") is True
                    for row in target_descriptor_rows
                )
            ),
            "Hostess staged payload manifest exposes target descriptors for downstream shell selection",
            "Hostess staged payload manifest has no target descriptor payload ready for downstream shell selection",
            "hostess.issue.hostess_staged_payload_manifest_receipt_downstream_selection",
        ),
    ]


def hostess_staged_payload_manifest_rows(
    staging_file_copy_receipt: dict[str, Any],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    payload_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    rows = []
    for copy_row in hostess_staging_file_copy_row_dicts(staging_file_copy_receipt):
        artifact_kind = copy_row.get("artifact_kind")
        target_kind = copy_row.get("target_kind")
        graph_id = copy_row.get("graph_id")
        consumer_id = copy_row.get("consumer_id")
        payload_path = copy_row.get("resolved_destination_path")
        payload_exists = (
            isinstance(payload_path, str) and Path(payload_path).exists()
        )
        descriptor_ready = (
            payload_status == REVIEWED_STATUS
            and is_downstream_shell_selection_artifact_kind(artifact_kind)
            and target_kind is not None
            and isinstance(graph_id, str)
            and bool(graph_id)
            and isinstance(consumer_id, str)
            and bool(consumer_id)
            and payload_exists
            and copy_row.get("destination_under_staging_root") is True
            and not has_legacy_route_or_path(copy_row)
        )
        rows.append(
            {
                "payload_row_id": (
                    f"hostess.staged_payload.{copy_row.get('copy_row_id')}"
                    if isinstance(copy_row.get("copy_row_id"), str)
                    and copy_row.get("copy_row_id")
                    else "hostess.staged_payload.unknown"
                ),
                "source_staging_file_copy_receipt_id": (
                    staging_file_copy_receipt.get("receipt_id")
                ),
                "source_copy_row_id": copy_row.get("copy_row_id"),
                "source_staging_file_row_id": copy_row.get(
                    "source_staging_file_row_id"
                ),
                "source_request_id": copy_row.get("source_request_id"),
                "source_file_index": copy_row.get("source_file_index"),
                "artifact_kind": artifact_kind,
                "payload_path": payload_path,
                "payload_exists": payload_exists,
                "payload_kind": copy_row.get("source_kind"),
                "payload_under_staging_root": copy_row.get(
                    "destination_under_staging_root"
                ),
                "target_kind": target_kind,
                "graph_id": graph_id,
                "consumer_id": consumer_id,
                "route_hints": copy_row.get("route_hints"),
                "source_action_ids": copy_row.get("source_action_ids"),
                "source_route_kinds": copy_row.get("source_route_kinds"),
                "payload_review_status": payload_status,
                "issue_code": None if payload_status == REVIEWED_STATUS else issue_code,
                "downstream_shell_descriptor_ready": descriptor_ready,
                "manifold_shell_handoff_candidate": (
                    descriptor_ready
                    and artifact_kind == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
                ),
                "makepad_shell_selection_candidate": descriptor_ready,
                "downstream_shell_artifact_priority": (
                    downstream_shell_artifact_priority(artifact_kind)
                    if descriptor_ready
                    else None
                ),
                "legacy_reference_dependency_used": False,
                "downstream_shell_runtime_started": False,
                "device_required": False,
                "schema_path_execution_allowed": False,
                "platform_execution_allowed": False,
                "studio_execution_allowed": False,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "build_started": False,
                "copy_started": False,
                "stage_started": False,
                "install_started": False,
                "launch_started": False,
                "evidence_collection_started": False,
                "command_session_started": False,
            }
        )
    return rows


def hostess_staged_payload_manifest_row_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = receipt.get("payload_rows", [])
    if not isinstance(rows, list):
        return []
    return [entry for entry in rows if isinstance(entry, dict)]


def hostess_staging_file_copy_receipt_source_ready(receipt: dict[str, Any]) -> bool:
    rows = hostess_staging_file_copy_row_dicts(receipt)
    return (
        receipt.get("$schema") == HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA
        and receipt.get("status") == COMPLETED_STATUS
        and receipt.get("issue_code") is None
        and receipt.get("receipt_owner") == HOSTESS_OWNER
        and receipt.get("staging_owner") == HOSTESS_OWNER
        and receipt.get("file_copy_owner") == HOSTESS_OWNER
        and receipt.get("command_session_authority") == MANIFOLD_OWNER
        and receipt.get("file_copy_completed") is True
        and receipt.get("staging_payloads_copied") is True
        and hostess_staging_file_copy_receipt_no_runtime_started(receipt)
        and hostess_staging_file_copy_rows_match_plan_receipt(
            receipt_from_copy_rows(receipt),
            rows,
            COMPLETED_STATUS,
        )
        and hostess_staging_file_copy_destinations_exist(rows)
        and (
            receipt.get("pmb_shell_handoff_review_required") is not True
            or (
                receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            )
        )
    )


def receipt_from_copy_rows(copy_receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "staging_files": [
            {
                "staging_file_row_id": row.get("source_staging_file_row_id"),
                "source_request_id": row.get("source_request_id"),
                "source_file_index": row.get("source_file_index"),
                "artifact_kind": row.get("artifact_kind"),
                "source_path": row.get("source_path"),
                "destination_path": row.get("destination_path"),
                "destination_root": row.get("destination_root"),
                "destination_absolute_path": row.get("destination_absolute_path"),
                "target_kind": row.get("target_kind"),
                "graph_id": row.get("graph_id"),
                "consumer_id": row.get("consumer_id"),
                "route_hints": row.get("route_hints"),
                "source_action_ids": row.get("source_action_ids"),
                "source_route_kinds": row.get("source_route_kinds"),
            }
            for row in hostess_staging_file_copy_row_dicts(copy_receipt)
        ]
    }


def hostess_staged_payload_rows_match_copy_receipt(
    staging_file_copy_receipt: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {REVIEWED_STATUS, REJECTED_STATUS}:
        return False
    source_rows = hostess_staging_file_copy_row_dicts(staging_file_copy_receipt)
    if len(rows) != len(source_rows):
        return False
    expected_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    by_id = {row.get("source_copy_row_id"): row for row in rows}
    for source_row in source_rows:
        row = by_id.get(source_row.get("copy_row_id"))
        if not isinstance(row, dict):
            return False
        for key, source_key in (
            ("source_staging_file_row_id", "source_staging_file_row_id"),
            ("source_request_id", "source_request_id"),
            ("source_file_index", "source_file_index"),
            ("artifact_kind", "artifact_kind"),
            ("payload_path", "resolved_destination_path"),
            ("payload_kind", "source_kind"),
            ("payload_under_staging_root", "destination_under_staging_root"),
            ("target_kind", "target_kind"),
            ("graph_id", "graph_id"),
            ("consumer_id", "consumer_id"),
            ("route_hints", "route_hints"),
            ("source_action_ids", "source_action_ids"),
            ("source_route_kinds", "source_route_kinds"),
        ):
            if row.get(key) != source_row.get(source_key):
                return False
        if row.get("payload_review_status") != expected_status:
            return False
        if expected_status == REVIEWED_STATUS:
            if row.get("issue_code") is not None:
                return False
            if row.get("payload_exists") is not True:
                return False
            if has_legacy_route_or_path(row):
                return False
            if not hostess_staged_payload_row_no_runtime_started(row):
                return False
        else:
            if not isinstance(row.get("issue_code"), str):
                return False
            if not hostess_staged_payload_row_no_runtime_started(row):
                return False
    return True


def hostess_staged_payload_manifest_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("legacy_reference_dependency_used") is False
        and receipt.get("downstream_shell_runtime_started") is False
        and receipt.get("device_required") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("execution_performed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("build_started") is False
        and receipt.get("copy_started") is False
        and receipt.get("stage_started") is False
        and receipt.get("install_started") is False
        and receipt.get("launch_started") is False
        and receipt.get("evidence_collection_started") is False
        and receipt.get("command_session_started") is False
        and receipt.get("schema_artifact_payloads_copied") is False
        and receipt.get("release_payloads_copied") is False
        and receipt.get("staging_payloads_copied") is False
        and receipt.get("file_copy_performed") is False
    )


def hostess_staged_payload_row_no_runtime_started(row: dict[str, Any]) -> bool:
    return (
        row.get("legacy_reference_dependency_used") is False
        and row.get("downstream_shell_runtime_started") is False
        and row.get("device_required") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("platform_execution_allowed") is False
        and row.get("studio_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("build_started") is False
        and row.get("copy_started") is False
        and row.get("stage_started") is False
        and row.get("install_started") is False
        and row.get("launch_started") is False
        and row.get("evidence_collection_started") is False
        and row.get("command_session_started") is False
    )


def hostess_staging_file_copy_preflight_checks(
    staging_file_plan_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    decision_supported: bool,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.hostess_staging_file_copy_receipt.file_plan_receipt_source",
            hostess_staging_file_plan_receipt_source_ready(
                staging_file_plan_receipt
            ),
            "Hostess staging file-plan receipt is accepted and ready for copy",
            "Hostess staging file-plan receipt is missing, rejected, or drifted",
            staging_file_plan_receipt.get("issue_code")
            or "hostess.issue.hostess_staging_file_plan_receipt_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.file_plan_source",
            staging_file_plan.get("$schema") == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
            and staging_file_plan.get("status") == READY_STATUS,
            "Studio Hostess staging file plan is available for copy evidence",
            "Studio Hostess staging file plan is unavailable or not ready",
            staging_file_plan.get("issue_code")
            or "hostess.issue.hostess_staging_file_copy_file_plan_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.sources_available",
            hostess_staging_file_copy_sources_available(staging_file_plan_receipt),
            "All Hostess staging file copy sources exist",
            "One or more Hostess staging file copy sources are missing",
            "hostess.issue.hostess_staging_file_copy_source_missing",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.destination_guards",
            hostess_staging_file_copy_destinations_are_safe(staging_file_plan_receipt),
            "All Hostess staging file copy destinations resolve under the staging root",
            "One or more Hostess staging file copy destinations escape the staging root",
            "hostess.issue.hostess_staging_file_copy_destination_unsafe",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.decision",
            decision_supported,
            "Hostess staging file copy receipt decision is supported",
            "Hostess staging file copy receipt decision is unsupported",
            "hostess.issue.hostess_staging_file_copy_receipt_decision",
        ),
    ]


def hostess_staging_file_copy_receipt_checks(
    staging_file_plan_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    copy_rows: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
    preflight_checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pmb_review_required = (
        staging_file_plan_receipt.get("pmb_shell_handoff_review_required") is True
    )
    return preflight_checks + [
        check(
            "hostess.check.hostess_staging_file_copy_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != COMPLETED_STATUS
            or (
                staging_file_plan_receipt.get("pmb_shell_handoff_review_ready")
                is True
                and pmb_shell_handoff_readiness_result_summary_valid(
                    staging_file_plan_receipt
                )
            ),
            "completed Hostess staging file copy preserves the PMB shell handoff gate",
            "completed Hostess staging file copy dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_file_copy_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.rows",
            hostess_staging_file_copy_rows_match_plan_receipt(
                staging_file_plan_receipt,
                copy_rows,
                status,
            ),
            "Hostess staging file copy rows match source receipt",
            "Hostess staging file copy rows drifted",
            "hostess.issue.hostess_staging_file_copy_receipt_row_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.no_runtime_started",
            all(
                hostess_staging_file_copy_row_no_runtime_started(row)
                for row in copy_rows
            ),
            "Hostess staging file copy rows did not start runtime, install, launch, or command sessions",
            "Hostess staging file copy rows indicate runtime, install, launch, or command sessions",
            "hostess.issue.hostess_staging_file_copy_receipt_runtime_started",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.decision",
            decision_supported,
            "Hostess staging file copy receipt decision is supported",
            "Hostess staging file copy receipt decision is unsupported",
            "hostess.issue.hostess_staging_file_copy_receipt_decision",
        ),
        check(
            "hostess.check.hostess_staging_file_copy_receipt.file_plan_source",
            staging_file_plan.get("$schema") == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA,
            "Studio Hostess staging file plan schema is available",
            "Studio Hostess staging file plan schema is unavailable",
            "hostess.issue.hostess_staging_file_copy_file_plan_not_ready",
        ),
    ]


def perform_hostess_staging_file_copies(
    staging_file_plan_receipt: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    errors = []
    for source_row in hostess_staging_file_plan_file_dicts(staging_file_plan_receipt):
        row = hostess_staging_file_copy_row_from_plan_row(
            staging_file_plan_receipt,
            source_row,
            COMPLETED_STATUS,
            None,
        )
        source_path = Path(row["resolved_source_path"])
        destination_path = Path(row["resolved_destination_path"])
        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if source_path.is_dir():
                shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
            else:
                shutil.copy2(source_path, destination_path)
            row["destination_exists_after_copy"] = destination_path.exists()
            row["copied_entry_count"] = copied_entry_count(destination_path)
        except Exception as exc:  # pragma: no cover - exact OS errors vary.
            issue = "hostess.issue.hostess_staging_file_copy_copy_failed"
            errors.append(issue)
            row["copy_status"] = REJECTED_STATUS
            row["issue_code"] = issue
            row["destination_exists_after_copy"] = destination_path.exists()
            row["copy_error"] = str(exc)
            row["schema_artifact_payload_copied"] = False
            row["staging_payload_copied"] = False
            row["file_copy_performed"] = False
            row["copy_started"] = False
            row["stage_started"] = False
        rows.append(row)
    return rows, errors


def hostess_staging_file_copy_rejected_rows(
    staging_file_plan_receipt: dict[str, Any],
    issue_code: str | None,
) -> list[dict[str, Any]]:
    return [
        hostess_staging_file_copy_row_from_plan_row(
            staging_file_plan_receipt,
            source_row,
            REJECTED_STATUS,
            issue_code or "hostess.issue.hostess_staging_file_copy_rejected",
        )
        for source_row in hostess_staging_file_plan_file_dicts(
            staging_file_plan_receipt
        )
    ]


def hostess_staging_file_copy_row_from_plan_row(
    staging_file_plan_receipt: dict[str, Any],
    source_row: dict[str, Any],
    copy_status: str,
    issue_code: str | None,
) -> dict[str, Any]:
    source_path = resolve_hostess_staging_copy_source_path(
        staging_file_plan_receipt,
        source_row,
    )
    destination_path = resolve_hostess_staging_copy_destination_path(
        staging_file_plan_receipt,
        source_row,
    )
    source_kind = (
        "directory"
        if source_path.is_dir()
        else "file"
        if source_path.is_file()
        else "missing"
    )
    completed = copy_status == COMPLETED_STATUS
    return {
        "copy_row_id": f"hostess.staging_file_copy.{source_row.get('staging_file_row_id')}",
        "source_staging_file_plan_receipt_id": staging_file_plan_receipt.get(
            "receipt_id"
        ),
        "source_staging_file_row_id": source_row.get("staging_file_row_id"),
        "source_request_id": source_row.get("source_request_id"),
        "source_file_index": source_row.get("source_file_index"),
        "artifact_kind": source_row.get("artifact_kind"),
        "source_path": source_row.get("source_path"),
        "resolved_source_path": str(source_path),
        "source_exists": source_path.exists(),
        "source_kind": source_kind,
        "destination_path": source_row.get("destination_path"),
        "destination_root": source_row.get("destination_root"),
        "destination_absolute_path": source_row.get("destination_absolute_path"),
        "resolved_destination_path": str(destination_path),
        "destination_under_staging_root": path_is_under_root(
            destination_path,
            staging_file_plan_receipt.get("staging_root"),
        ),
        "destination_exists_after_copy": destination_path.exists()
        if completed
        else False,
        "target_kind": source_row.get("target_kind"),
        "graph_id": source_row.get("graph_id"),
        "consumer_id": source_row.get("consumer_id"),
        "route_hints": source_row.get("route_hints"),
        "source_action_ids": source_row.get("source_action_ids"),
        "source_route_kinds": source_row.get("source_route_kinds"),
        "copy_status": copy_status,
        "issue_code": None if completed else issue_code,
        "copied_entry_count": copied_entry_count(destination_path)
        if completed and destination_path.exists()
        else 0,
        "schema_artifact_payload_copied": completed,
        "staging_payload_copied": completed,
        "release_payload_copied": False,
        "file_copy_performed": completed,
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "execution_started": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "build_started": False,
        "copy_started": completed,
        "stage_started": completed,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
    }


def hostess_staging_file_copy_row_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = receipt.get("copy_rows", [])
    if not isinstance(rows, list):
        return []
    return [entry for entry in rows if isinstance(entry, dict)]


def hostess_staging_file_plan_receipt_source_ready(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("$schema") == HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA
        and receipt.get("status") == ACCEPTED_STATUS
        and receipt.get("issue_code") is None
        and receipt.get("receipt_owner") == HOSTESS_OWNER
        and receipt.get("staging_owner") == HOSTESS_OWNER
        and receipt.get("file_copy_plan_owner") == HOSTESS_OWNER
        and receipt.get("command_session_authority") == MANIFOLD_OWNER
        and receipt.get("copy_plan_ready") is True
        and receipt.get("staging_file_plan_reviewed") is True
        and hostess_staging_file_plan_receipt_unstarted(receipt)
        and (
            receipt.get("pmb_shell_handoff_review_required") is not True
            or (
                receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            )
        )
    )


def hostess_staging_file_copy_sources_available(
    staging_file_plan_receipt: dict[str, Any],
) -> bool:
    rows = hostess_staging_file_plan_file_dicts(staging_file_plan_receipt)
    return bool(rows) and all(
        resolve_hostess_staging_copy_source_path(
            staging_file_plan_receipt,
            row,
        ).exists()
        for row in rows
    )


def hostess_staging_file_copy_destinations_are_safe(
    staging_file_plan_receipt: dict[str, Any],
) -> bool:
    rows = hostess_staging_file_plan_file_dicts(staging_file_plan_receipt)
    return bool(rows) and all(
        path_is_under_root(
            resolve_hostess_staging_copy_destination_path(
                staging_file_plan_receipt,
                row,
            ),
            staging_file_plan_receipt.get("staging_root"),
        )
        for row in rows
    )


def hostess_staging_file_copy_rows_match_plan_receipt(
    staging_file_plan_receipt: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {COMPLETED_STATUS, REJECTED_STATUS}:
        return False
    source_rows = hostess_staging_file_plan_file_dicts(staging_file_plan_receipt)
    if len(rows) != len(source_rows):
        return False
    expected_status = COMPLETED_STATUS if status == COMPLETED_STATUS else REJECTED_STATUS
    by_id = {row.get("source_staging_file_row_id"): row for row in rows}
    for source_row in source_rows:
        row = by_id.get(source_row.get("staging_file_row_id"))
        if not isinstance(row, dict):
            return False
        for key in (
            "source_request_id",
            "source_file_index",
            "artifact_kind",
            "source_path",
            "destination_path",
            "destination_root",
            "destination_absolute_path",
            "target_kind",
            "graph_id",
            "consumer_id",
            "route_hints",
            "source_action_ids",
            "source_route_kinds",
        ):
            if row.get(key) != source_row.get(key):
                return False
        if row.get("copy_status") != expected_status:
            return False
        if expected_status == COMPLETED_STATUS:
            if row.get("issue_code") is not None:
                return False
            if row.get("source_exists") is not True:
                return False
            if row.get("source_kind") not in {"file", "directory"}:
                return False
            if row.get("destination_under_staging_root") is not True:
                return False
            if row.get("destination_exists_after_copy") is not True:
                return False
            if not hostess_staging_file_copy_row_completed(row):
                return False
        else:
            if not isinstance(row.get("issue_code"), str):
                return False
            if not hostess_staging_file_copy_row_rejected(row):
                return False
    return True


def hostess_staging_file_copy_destinations_exist(
    rows: list[dict[str, Any]],
) -> bool:
    return bool(rows) and all(
        isinstance(row.get("resolved_destination_path"), str)
        and Path(row["resolved_destination_path"]).exists()
        for row in rows
    )


def resolve_hostess_staging_copy_source_path(
    staging_file_plan_receipt: dict[str, Any],
    source_row: dict[str, Any],
) -> Path:
    raw_path = source_row.get("source_path")
    path = Path(raw_path) if isinstance(raw_path, str) else Path()
    if path.is_absolute():
        return path
    source_file_plan_path = staging_file_plan_receipt.get("source_file_plan_path")
    if isinstance(source_file_plan_path, str) and source_file_plan_path:
        return Path(source_file_plan_path).parent / path
    return path


def resolve_hostess_staging_copy_destination_path(
    staging_file_plan_receipt: dict[str, Any],
    source_row: dict[str, Any],
) -> Path:
    staging_root = staging_file_plan_receipt.get("staging_root")
    destination_path = source_row.get("destination_path")
    if not isinstance(staging_root, str) or not isinstance(destination_path, str):
        return Path()
    return Path(staging_root).joinpath(*destination_path.replace("\\", "/").split("/"))


def path_is_under_root(path: Path, root: Any) -> bool:
    if not isinstance(root, str) or not root:
        return False
    try:
        resolved_path = path.resolve()
        resolved_root = Path(root).resolve()
        resolved_path.relative_to(resolved_root)
        return True
    except (OSError, ValueError):
        return False


def copied_entry_count(path: Path) -> int:
    if path.is_file():
        return 1
    if not path.is_dir():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def hostess_staging_file_copy_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("device_required") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("execution_performed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("build_started") is False
        and receipt.get("install_started") is False
        and receipt.get("launch_started") is False
        and receipt.get("evidence_collection_started") is False
        and receipt.get("command_session_started") is False
        and receipt.get("release_payloads_copied") is False
    )


def hostess_staging_file_copy_row_no_runtime_started(row: dict[str, Any]) -> bool:
    return (
        row.get("device_required") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("platform_execution_allowed") is False
        and row.get("studio_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("build_started") is False
        and row.get("install_started") is False
        and row.get("launch_started") is False
        and row.get("evidence_collection_started") is False
        and row.get("command_session_started") is False
        and row.get("release_payload_copied") is False
    )


def hostess_staging_file_copy_row_completed(row: dict[str, Any]) -> bool:
    return (
        row.get("schema_artifact_payload_copied") is True
        and row.get("staging_payload_copied") is True
        and row.get("release_payload_copied") is False
        and row.get("file_copy_performed") is True
        and row.get("copy_started") is True
        and row.get("stage_started") is True
        and hostess_staging_file_copy_row_no_runtime_started(row)
    )


def hostess_staging_file_copy_row_rejected(row: dict[str, Any]) -> bool:
    return (
        row.get("schema_artifact_payload_copied") is False
        and row.get("staging_payload_copied") is False
        and row.get("release_payload_copied") is False
        and row.get("file_copy_performed") is False
        and row.get("copy_started") is False
        and row.get("stage_started") is False
        and hostess_staging_file_copy_row_no_runtime_started(row)
    )


def hostess_staging_file_plan_receipt_checks(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    request_rows: list[dict[str, Any]],
    file_rows: list[dict[str, Any]],
    staging_root: str,
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = (
        handoff_acceptance_receipt.get("pmb_shell_handoff_review_required") is True
    )
    return [
        check(
            "hostess.check.hostess_staging_file_plan_receipt.acceptance_source",
            hostess_staging_handoff_acceptance_receipt_source_ready(
                handoff_acceptance_receipt
            ),
            "Hostess staging handoff acceptance receipt is accepted",
            "Hostess staging handoff acceptance receipt is missing, rejected, or drifted",
            handoff_acceptance_receipt.get("issue_code")
            or "hostess.issue.hostess_staging_handoff_acceptance_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.file_plan_source",
            studio_hostess_staging_file_plan_source_ready(
                staging_file_plan,
                handoff_acceptance_receipt,
            ),
            "Studio Hostess staging file plan is ready",
            "Studio Hostess staging file plan is missing, blocked, or drifted",
            staging_file_plan.get("issue_code")
            or "hostess.issue.hostess_staging_file_plan_source_not_ready",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.staging_root",
            hostess_staging_root_ready(staging_root),
            "Hostess staging root is explicit",
            "Hostess staging root is missing",
            "hostess.issue.hostess_staging_file_plan_staging_root",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.pmb_shell_handoff_review",
            not pmb_review_required
            or status != ACCEPTED_STATUS
            or (
                handoff_acceptance_receipt.get("pmb_shell_handoff_review_ready")
                is True
                and pmb_shell_handoff_readiness_result_summary_valid(
                    handoff_acceptance_receipt
                )
            ),
            "accepted Hostess staging file plan preserves the PMB shell handoff gate",
            "accepted Hostess staging file plan dropped or drifted the PMB shell handoff gate",
            "hostess.issue.hostess_staging_file_plan_receipt_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.decision",
            decision_supported,
            "Hostess staging file plan receipt decision is supported",
            "Hostess staging file plan receipt decision is unsupported",
            "hostess.issue.hostess_staging_file_plan_receipt_decision",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.requests",
            hostess_staging_file_plan_requests_match_sources(
                handoff_acceptance_receipt,
                staging_file_plan,
                request_rows,
                status,
            ),
            "Hostess staging file plan request rows match sources",
            "Hostess staging file plan request rows drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_request_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.files",
            hostess_staging_file_plan_files_match_source(
                staging_file_plan,
                file_rows,
                staging_root,
                status,
            ),
            "Hostess staging file rows match source plan",
            "Hostess staging file rows drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_file_drift",
        ),
        check(
            "hostess.check.hostess_staging_file_plan_receipt.destination_guards",
            hostess_staging_file_plan_rows_have_clean_destinations(
                request_rows,
                file_rows,
                staging_root,
            ),
            "Hostess staging destinations stay in the staging root and avoid legacy routes",
            "Hostess staging destinations or routes drifted",
            "hostess.issue.hostess_staging_file_plan_receipt_destination_drift",
        ),
    ]


def hostess_staging_file_plan_request_rows(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    staging_root: str,
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    request_status = PLANNED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    accepted_by_id = {
        row.get("source_request_id"): row
        for row in hostess_staging_handoff_acceptance_request_dicts(
            handoff_acceptance_receipt
        )
    }
    rows = []
    for request in studio_hostess_staging_file_plan_request_dicts(staging_file_plan):
        request_id = request.get("request_id")
        accepted = accepted_by_id.get(request_id, {})
        planned_files = studio_hostess_staging_file_plan_planned_file_dicts(request)
        rows.append(
            {
                "staging_request_row_id": (
                    f"hostess.staging_file_plan_request.{request_id}"
                    if isinstance(request_id, str) and request_id
                    else "hostess.staging_file_plan_request.unknown"
                ),
                "source_handoff_acceptance_receipt_id": (
                    handoff_acceptance_receipt.get("receipt_id")
                ),
                "source_accepted_request_row_id": accepted.get(
                    "accepted_request_row_id"
                ),
                "source_request_id": request_id,
                "request_kind": request.get("request_kind"),
                "owner": request.get("owner"),
                "source_status": request.get("status"),
                "acceptance_status": accepted.get("acceptance_status"),
                "target_key": request.get("target_key"),
                "target_kind": request.get("target_kind"),
                "graph_id": request.get("graph_id"),
                "consumer_id": request.get("consumer_id"),
                "destination_root": request.get("destination_root"),
                "staging_root": staging_root,
                "planned_file_count": request.get("planned_file_count"),
                "source_plan_file_count": len(planned_files),
                "route_kinds": request.get("route_kinds"),
                "action_ids": request.get("action_ids"),
                "staging_request_status": request_status,
                "issue_code": None if request_status == PLANNED_STATUS else issue_code,
                "copy_plan_ready": request_status == PLANNED_STATUS,
                "stage_generated_shells_requested": True,
                "stage_generated_shells_started": False,
                "schema_artifact_payload_copied": False,
                "staging_payload_copied": False,
                "release_payload_copied": False,
                "file_copy_performed": False,
                "device_required": False,
                "schema_path_execution_allowed": False,
                "platform_execution_allowed": False,
                "studio_execution_allowed": False,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "build_started": False,
                "copy_started": False,
                "stage_started": False,
                "install_started": False,
                "launch_started": False,
                "evidence_collection_started": False,
                "command_session_started": False,
            }
        )
    return rows


def hostess_staging_file_plan_file_rows(
    staging_file_plan: dict[str, Any],
    staging_root: str,
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    file_status = PLANNED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    rows = []
    for request in studio_hostess_staging_file_plan_request_dicts(staging_file_plan):
        request_id = request.get("request_id")
        destination_root = request.get("destination_root")
        for index, planned_file in enumerate(
            studio_hostess_staging_file_plan_planned_file_dicts(request)
        ):
            artifact_kind = planned_file.get("artifact_kind")
            destination_path = planned_file.get("destination_path")
            row_id = (
                f"hostess.staging_file_plan_file.{request_id}.{index}.{artifact_kind}"
                if isinstance(request_id, str)
                and request_id
                and isinstance(artifact_kind, str)
                and artifact_kind
                else f"hostess.staging_file_plan_file.unknown.{index}"
            )
            destination_valid = hostess_staging_destination_path_valid(
                destination_path,
                destination_root,
            )
            rows.append(
                {
                    "staging_file_row_id": row_id,
                    "source_request_id": request_id,
                    "source_file_index": index,
                    "artifact_kind": artifact_kind,
                    "source_path": planned_file.get("source_path"),
                    "destination_path": destination_path,
                    "destination_root": destination_root,
                    "destination_under_request_root": destination_valid,
                    "staging_root": staging_root,
                    "destination_absolute_path": staging_destination_absolute_path(
                        staging_root,
                        destination_path,
                    ),
                    "target_kind": planned_file.get("target_kind"),
                    "graph_id": planned_file.get("graph_id"),
                    "consumer_id": planned_file.get("consumer_id"),
                    "route_hints": planned_file.get("route_hints"),
                    "source_action_ids": planned_file.get("source_action_ids"),
                    "source_route_kinds": planned_file.get("source_route_kinds"),
                    "source_path_reviewed": isinstance(
                        planned_file.get("source_path"), str
                    )
                    and bool(planned_file.get("source_path")),
                    "destination_path_reviewed": destination_valid,
                    "file_copy_plan_status": file_status,
                    "issue_code": None if file_status == PLANNED_STATUS else issue_code,
                    "copy_plan_ready": file_status == PLANNED_STATUS,
                    "schema_artifact_payload_copied": False,
                    "staging_payload_copied": False,
                    "release_payload_copied": False,
                    "file_copy_performed": False,
                    "device_required": False,
                    "schema_path_execution_allowed": False,
                    "platform_execution_allowed": False,
                    "studio_execution_allowed": False,
                    "execution_started": False,
                    "runtime_execution_performed": False,
                    "platform_execution_performed": False,
                    "build_started": False,
                    "copy_started": False,
                    "stage_started": False,
                    "install_started": False,
                    "launch_started": False,
                    "evidence_collection_started": False,
                    "command_session_started": False,
                }
            )
    return rows


def hostess_staging_file_plan_request_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = receipt.get("staging_requests", [])
    if not isinstance(requests, list):
        return []
    return [entry for entry in requests if isinstance(entry, dict)]


def hostess_staging_file_plan_file_dicts(
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    files = receipt.get("staging_files", [])
    if not isinstance(files, list):
        return []
    return [entry for entry in files if isinstance(entry, dict)]


def studio_hostess_staging_file_plan_request_dicts(
    staging_file_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = staging_file_plan.get("requests", [])
    if not isinstance(requests, list):
        return []
    return [entry for entry in requests if isinstance(entry, dict)]


def studio_hostess_staging_file_plan_planned_file_dicts(
    request: dict[str, Any],
) -> list[dict[str, Any]]:
    files = request.get("planned_files", [])
    if not isinstance(files, list):
        return []
    return [entry for entry in files if isinstance(entry, dict)]


def hostess_staging_handoff_acceptance_receipt_source_ready(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("$schema") == HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_SCHEMA
        and receipt.get("status") == ACCEPTED_STATUS
        and receipt.get("issue_code") is None
        and receipt.get("receipt_owner") == HOSTESS_OWNER
        and receipt.get("staging_owner") == HOSTESS_OWNER
        and receipt.get("command_session_authority") == MANIFOLD_OWNER
        and receipt.get("requester_role") == STUDIO_REQUESTER
        and receipt.get("studio_role") == STUDIO_ROLE
        and receipt.get("staging_handoff_accepted") is True
        and receipt.get("stage_generated_shells_request_accepted") is True
        and hostess_staging_handoff_acceptance_receipt_unstarted(receipt)
        and (
            receipt.get("pmb_shell_handoff_review_required") is not True
            or (
                receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_shell_handoff_readiness_result_summary_valid(receipt)
            )
        )
    )


def studio_hostess_staging_file_plan_source_ready(
    staging_file_plan: dict[str, Any],
    handoff_acceptance_receipt: dict[str, Any],
) -> bool:
    requests = studio_hostess_staging_file_plan_request_dicts(staging_file_plan)
    planned_file_count = sum(
        len(studio_hostess_staging_file_plan_planned_file_dicts(request))
        for request in requests
    )
    return (
        staging_file_plan.get("$schema") == STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA
        and staging_file_plan.get("status") == READY_STATUS
        and staging_file_plan.get("issue_code") is None
        and staging_file_plan.get("execution_policy") == "not_executed.dry_run_only"
        and staging_file_plan.get("staging_owner") == HOSTESS_OWNER
        and staging_file_plan.get("command_session_authority") == MANIFOLD_OWNER
        and staging_file_plan.get("install_launch_evidence_authority")
        == HOSTESS_OWNER
        and staging_file_plan.get("studio_role") == STUDIO_ROLE
        and staging_file_plan.get("manifest_id")
        == handoff_acceptance_receipt.get("manifest_id")
        and staging_file_plan.get("project_id")
        == handoff_acceptance_receipt.get("project_id")
        and staging_file_plan.get("project_revision")
        == handoff_acceptance_receipt.get("project_revision")
        and staging_file_plan.get("selected_candidate_id")
        == handoff_acceptance_receipt.get("selected_candidate_id")
        and staging_file_plan.get("request_count") == len(requests)
        and staging_file_plan.get("ready_request_count") == len(requests)
        and staging_file_plan.get("blocked_request_count") == 0
        and staging_file_plan.get("planned_file_count") == planned_file_count
        and all(
            action in staging_file_plan.get("prohibited_actions", [])
            for action in REQUIRED_PROHIBITED_ACTIONS
        )
        and all(
            studio_hostess_staging_file_plan_request_ready(request)
            for request in requests
        )
    )


def studio_hostess_staging_file_plan_request_ready(
    request: dict[str, Any],
) -> bool:
    files = studio_hostess_staging_file_plan_planned_file_dicts(request)
    destination_root = request.get("destination_root")
    return (
        request.get("owner") == HOSTESS_OWNER
        and request.get("status") == READY_STATUS
        and request.get("issue_code") is None
        and request.get("planned_file_count") == len(files)
        and "hostess.stage.generated_shells" in request.get("route_kinds", [])
        and not has_legacy_route_or_path(request)
        and all(
            studio_hostess_staging_file_plan_file_ready(file, destination_root)
            for file in files
        )
    )


def studio_hostess_staging_file_plan_file_ready(
    planned_file: dict[str, Any],
    destination_root: Any,
) -> bool:
    return (
        isinstance(planned_file.get("artifact_kind"), str)
        and bool(planned_file.get("artifact_kind"))
        and isinstance(planned_file.get("source_path"), str)
        and bool(planned_file.get("source_path"))
        and hostess_staging_destination_path_valid(
            planned_file.get("destination_path"),
            destination_root,
        )
        and any(
            route in planned_file.get("source_route_kinds", [])
            for route in (
                "hostess.stage.generated_shells",
                "hostess.review.release_candidate",
            )
        )
        and not has_legacy_route_or_path(planned_file)
    )


def hostess_staging_file_plan_requests_match_sources(
    handoff_acceptance_receipt: dict[str, Any],
    staging_file_plan: dict[str, Any],
    rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {ACCEPTED_STATUS, REJECTED_STATUS}:
        return False
    source_requests = studio_hostess_staging_file_plan_request_dicts(
        staging_file_plan
    )
    accepted_by_id = {
        row.get("source_request_id"): row
        for row in hostess_staging_handoff_acceptance_request_dicts(
            handoff_acceptance_receipt
        )
    }
    if len(rows) != len(source_requests):
        return False
    expected_status = PLANNED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    by_id = {row.get("source_request_id"): row for row in rows}
    for request in source_requests:
        request_id = request.get("request_id")
        row = by_id.get(request_id)
        accepted = accepted_by_id.get(request_id)
        if not isinstance(row, dict) or not isinstance(accepted, dict):
            return False
        for key in (
            "request_kind",
            "owner",
            "target_key",
            "target_kind",
            "graph_id",
            "consumer_id",
            "destination_root",
            "planned_file_count",
            "route_kinds",
            "action_ids",
        ):
            if row.get(key) != request.get(key):
                return False
        if row.get("source_status") != request.get("status"):
            return False
        if row.get("acceptance_status") != accepted.get("acceptance_status"):
            return False
        if row.get("source_plan_file_count") != len(
            studio_hostess_staging_file_plan_planned_file_dicts(request)
        ):
            return False
        if row.get("staging_request_status") != expected_status:
            return False
        if expected_status == PLANNED_STATUS and row.get("issue_code") is not None:
            return False
        if expected_status != PLANNED_STATUS and not isinstance(row.get("issue_code"), str):
            return False
        if row.get("copy_plan_ready") != (expected_status == PLANNED_STATUS):
            return False
        if not hostess_staging_file_plan_request_unstarted(row):
            return False
    return True


def hostess_staging_file_plan_files_match_source(
    staging_file_plan: dict[str, Any],
    rows: list[dict[str, Any]],
    staging_root: Any,
    status: Any,
) -> bool:
    if status not in {ACCEPTED_STATUS, REJECTED_STATUS}:
        return False
    expected_status = PLANNED_STATUS if status == ACCEPTED_STATUS else REJECTED_STATUS
    expected_rows = []
    for request in studio_hostess_staging_file_plan_request_dicts(staging_file_plan):
        for index, planned_file in enumerate(
            studio_hostess_staging_file_plan_planned_file_dicts(request)
        ):
            expected_rows.append((request, index, planned_file))
    if len(rows) != len(expected_rows):
        return False
    by_key = {
        (row.get("source_request_id"), row.get("source_file_index")): row
        for row in rows
    }
    for request, index, planned_file in expected_rows:
        row = by_key.get((request.get("request_id"), index))
        if not isinstance(row, dict):
            return False
        for key in (
            "artifact_kind",
            "source_path",
            "destination_path",
            "target_kind",
            "graph_id",
            "consumer_id",
            "route_hints",
            "source_action_ids",
            "source_route_kinds",
        ):
            if row.get(key) != planned_file.get(key):
                return False
        destination_path = planned_file.get("destination_path")
        if row.get("destination_root") != request.get("destination_root"):
            return False
        if row.get("staging_root") != staging_root:
            return False
        if row.get("destination_absolute_path") != staging_destination_absolute_path(
            staging_root,
            destination_path,
        ):
            return False
        if row.get("destination_under_request_root") is not True:
            return False
        if row.get("destination_path_reviewed") is not True:
            return False
        if row.get("source_path_reviewed") is not True:
            return False
        if row.get("file_copy_plan_status") != expected_status:
            return False
        if expected_status == PLANNED_STATUS and row.get("issue_code") is not None:
            return False
        if expected_status != PLANNED_STATUS and not isinstance(row.get("issue_code"), str):
            return False
        if row.get("copy_plan_ready") != (expected_status == PLANNED_STATUS):
            return False
        if not hostess_staging_file_plan_file_unstarted(row):
            return False
    return True


def hostess_staging_file_plan_rows_have_clean_destinations(
    request_rows: list[dict[str, Any]],
    file_rows: list[dict[str, Any]],
    staging_root: Any,
) -> bool:
    if not hostess_staging_root_ready(staging_root):
        return False
    for row in request_rows:
        if has_legacy_route_or_path(row):
            return False
        destination_root = row.get("destination_root")
        if not isinstance(destination_root, str) or not destination_root:
            return False
    for row in file_rows:
        if has_legacy_route_or_path(row):
            return False
        if row.get("staging_root") != staging_root:
            return False
        if row.get("destination_under_request_root") is not True:
            return False
        if not hostess_staging_destination_path_valid(
            row.get("destination_path"),
            row.get("destination_root"),
        ):
            return False
        if row.get("destination_absolute_path") != staging_destination_absolute_path(
            staging_root,
            row.get("destination_path"),
        ):
            return False
    return True


def hostess_staging_root_ready(staging_root: Any) -> bool:
    return isinstance(staging_root, str) and bool(staging_root.strip())


def hostess_staging_destination_path_valid(
    destination_path: Any,
    destination_root: Any,
) -> bool:
    if not isinstance(destination_path, str) or not destination_path:
        return False
    if not isinstance(destination_root, str) or not destination_root:
        return False
    normalized = destination_path.replace("\\", "/")
    root = destination_root.replace("\\", "/").rstrip("/")
    if normalized.startswith("/") or ":" in normalized:
        return False
    if any(part in {"", ".", ".."} for part in normalized.split("/")):
        return False
    return normalized == root or normalized.startswith(root + "/")


def staging_destination_absolute_path(
    staging_root: Any,
    destination_path: Any,
) -> str | None:
    if not isinstance(staging_root, str) or not isinstance(destination_path, str):
        return None
    relative_parts = destination_path.replace("\\", "/").split("/")
    return str(Path(staging_root).joinpath(*relative_parts))


def has_legacy_route_or_path(item: dict[str, Any]) -> bool:
    legacy_tokens = ("legacy.rusty_xr", "legacy/rusty-xr", "Rusty-XR")
    for value in item.values():
        values = value if isinstance(value, list) else [value]
        for entry in values:
            if isinstance(entry, str) and any(token in entry for token in legacy_tokens):
                return True
    return False


def hostess_staging_file_plan_receipt_unstarted(receipt: dict[str, Any]) -> bool:
    return (
        all(receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
        and receipt.get("stage_generated_shells_started") is False
        and receipt.get("device_required") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("schema_artifact_payloads_copied") is False
        and receipt.get("release_payloads_copied") is False
        and receipt.get("staging_payloads_copied") is False
        and receipt.get("file_copy_performed") is False
    )


def hostess_staging_file_plan_request_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("stage_generated_shells_started") is False
        and row.get("schema_artifact_payload_copied") is False
        and row.get("staging_payload_copied") is False
        and row.get("release_payload_copied") is False
        and row.get("file_copy_performed") is False
        and row.get("device_required") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("platform_execution_allowed") is False
        and row.get("studio_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("build_started") is False
        and row.get("copy_started") is False
        and row.get("stage_started") is False
        and row.get("install_started") is False
        and row.get("launch_started") is False
        and row.get("evidence_collection_started") is False
        and row.get("command_session_started") is False
    )


def hostess_staging_file_plan_file_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("schema_artifact_payload_copied") is False
        and row.get("staging_payload_copied") is False
        and row.get("release_payload_copied") is False
        and row.get("file_copy_performed") is False
        and row.get("device_required") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("platform_execution_allowed") is False
        and row.get("studio_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("build_started") is False
        and row.get("copy_started") is False
        and row.get("stage_started") is False
        and row.get("install_started") is False
        and row.get("launch_started") is False
        and row.get("evidence_collection_started") is False
        and row.get("command_session_started") is False
    )

__all__ = [
    "build_hostess_staging_handoff_acceptance_receipt",
    "validate_hostess_staging_handoff_acceptance_receipt",
    "hostess_staging_handoff_acceptance_receipt_checks",
    "hostess_staging_handoff_acceptance_request_rows",
    "hostess_staging_handoff_acceptance_instruction_rows",
    "hostess_staging_handoff_acceptance_request_dicts",
    "hostess_staging_handoff_acceptance_instruction_dicts",
    "studio_hostess_staging_handoff_request_dicts",
    "studio_hostess_staging_handoff_instruction_dicts",
    "operator_release_readiness_bundle_source_ready",
    "studio_hostess_staging_handoff_source_ready",
    "studio_hostess_staging_acceptance_manifest_source_ready",
    "hostess_staging_handoff_acceptance_requests_match_source",
    "hostess_staging_handoff_acceptance_instructions_match_source",
    "hostess_staging_handoff_acceptance_receipt_unstarted",
    "hostess_staging_handoff_acceptance_request_unstarted",
    "hostess_staging_handoff_acceptance_instruction_unstarted",
    "build_hostess_staging_file_plan_receipt",
    "validate_hostess_staging_file_plan_receipt",
    "build_hostess_staging_file_copy_receipt",
    "validate_hostess_staging_file_copy_receipt",
    "build_hostess_staged_payload_manifest_receipt",
    "validate_hostess_staged_payload_manifest_receipt",
    "downstream_shell_artifact_priority",
    "is_downstream_shell_selection_artifact_kind",
    "hostess_downstream_shell_payload_rows",
    "hostess_target_downstream_shell_payload_rows",
    "build_hostess_downstream_shell_selection_receipt",
    "validate_hostess_downstream_shell_selection_receipt",
    "hostess_downstream_shell_selection_receipt_checks",
    "hostess_downstream_shell_selection_row",
    "hostess_downstream_shell_selection_candidate_rows",
    "hostess_downstream_shell_selection_row_dicts",
    "hostess_staged_payload_manifest_receipt_source_ready",
    "hostess_downstream_shell_selection_rows_match_manifest",
    "hostess_downstream_shell_selection_receipt_no_runtime_started",
    "hostess_downstream_shell_selection_row_no_runtime_started",
    "hostess_staged_payload_manifest_receipt_checks",
    "hostess_staged_payload_manifest_rows",
    "hostess_staged_payload_manifest_row_dicts",
    "hostess_staging_file_copy_receipt_source_ready",
    "receipt_from_copy_rows",
    "hostess_staged_payload_rows_match_copy_receipt",
    "hostess_staged_payload_manifest_receipt_no_runtime_started",
    "hostess_staged_payload_row_no_runtime_started",
    "hostess_staging_file_copy_preflight_checks",
    "hostess_staging_file_copy_receipt_checks",
    "perform_hostess_staging_file_copies",
    "hostess_staging_file_copy_rejected_rows",
    "hostess_staging_file_copy_row_from_plan_row",
    "hostess_staging_file_copy_row_dicts",
    "hostess_staging_file_plan_receipt_source_ready",
    "hostess_staging_file_copy_sources_available",
    "hostess_staging_file_copy_destinations_are_safe",
    "hostess_staging_file_copy_rows_match_plan_receipt",
    "hostess_staging_file_copy_destinations_exist",
    "resolve_hostess_staging_copy_source_path",
    "resolve_hostess_staging_copy_destination_path",
    "path_is_under_root",
    "copied_entry_count",
    "hostess_staging_file_copy_receipt_no_runtime_started",
    "hostess_staging_file_copy_row_no_runtime_started",
    "hostess_staging_file_copy_row_completed",
    "hostess_staging_file_copy_row_rejected",
    "hostess_staging_file_plan_receipt_checks",
    "hostess_staging_file_plan_request_rows",
    "hostess_staging_file_plan_file_rows",
    "hostess_staging_file_plan_request_dicts",
    "hostess_staging_file_plan_file_dicts",
    "studio_hostess_staging_file_plan_request_dicts",
    "studio_hostess_staging_file_plan_planned_file_dicts",
    "hostess_staging_handoff_acceptance_receipt_source_ready",
    "studio_hostess_staging_file_plan_source_ready",
    "studio_hostess_staging_file_plan_request_ready",
    "studio_hostess_staging_file_plan_file_ready",
    "hostess_staging_file_plan_requests_match_sources",
    "hostess_staging_file_plan_files_match_source",
    "hostess_staging_file_plan_rows_have_clean_destinations",
    "hostess_staging_root_ready",
    "hostess_staging_destination_path_valid",
    "staging_destination_absolute_path",
    "has_legacy_route_or_path",
    "hostess_staging_file_plan_receipt_unstarted",
    "hostess_staging_file_plan_request_unstarted",
    "hostess_staging_file_plan_file_unstarted",
]
