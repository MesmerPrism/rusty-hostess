"""Hostess staging handoff acceptance receipt helpers."""

from __future__ import annotations

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
