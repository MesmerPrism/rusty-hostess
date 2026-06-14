"""Projected-motion breath validation handoff receipts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers

def build_projected_motion_breath_validation_handoff(
    authoring_review: dict[str, Any],
    package_evidence_intake: dict[str, Any] | None = None,
    authoring_review_path: Path | None = None,
    package_evidence_intake_path: Path | None = None,
    source_adapter_selection_review: dict[str, Any] | None = None,
    source_adapter_selection_review_path: Path | None = None,
) -> dict[str, Any]:
    required_package_checks = pmb_required_package_checks(authoring_review)
    source_adapter_selection_present = isinstance(source_adapter_selection_review, dict)
    source_adapter_selection_schema = (
        source_adapter_selection_review.get("$schema")
        if source_adapter_selection_present
        else None
    )
    source_adapter_selection_status = (
        source_adapter_selection_review.get("status")
        if source_adapter_selection_present
        else None
    )
    selected_adapter_id = (
        source_adapter_selection_review.get("selected_adapter_id")
        if source_adapter_selection_present
        else None
    )
    selected_source_kind = (
        source_adapter_selection_review.get("selected_source_kind")
        if source_adapter_selection_present
        else None
    )
    selected_input_kind = (
        source_adapter_selection_review.get("selected_input_kind")
        if source_adapter_selection_present
        else None
    )
    selected_output_stream_id = (
        source_adapter_selection_review.get("selected_output_stream_id")
        if source_adapter_selection_present
        else None
    )
    source_package_evidence_schema = (
        package_evidence_intake.get("$schema")
        if isinstance(package_evidence_intake, dict)
        else authoring_review.get("source_intake_schema")
    )
    source_package_evidence_status = (
        package_evidence_intake.get("status")
        if isinstance(package_evidence_intake, dict)
        else authoring_review.get("package_evidence_status")
    )
    source_package_evidence_path = (
        str(package_evidence_intake_path)
        if package_evidence_intake_path is not None
        else authoring_review.get("source_intake_path")
    )
    package_required_check_count = int_or_zero(
        authoring_review.get("package_required_check_count")
    )
    package_ready_required_check_count = int_or_zero(
        authoring_review.get("package_ready_required_check_count")
    )
    package_blocked_required_check_count = int_or_zero(
        authoring_review.get("package_blocked_required_check_count")
    )
    checks = [
        check(
            "hostess.check.projected_motion_breath_validation_handoff.authoring_schema",
            authoring_review.get("$schema") == STUDIO_PMB_AUTHORING_REVIEW_SCHEMA,
            "projected-motion breath authoring review schema is supported",
            "projected-motion breath authoring review schema is unsupported",
            "hostess.issue.projected_motion_breath_authoring_review_schema",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.authoring_status",
            authoring_review.get("status") == READY_STATUS,
            "projected-motion breath authoring review is ready",
            "projected-motion breath authoring review is blocked or rejected",
            authoring_review.get("issue_code")
            or "hostess.issue.projected_motion_breath_authoring_review_not_ready",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.package_schema",
            source_package_evidence_schema == STUDIO_PACKAGE_EVIDENCE_INTAKE_SCHEMA,
            "source package evidence intake schema is supported",
            "source package evidence intake schema is unsupported",
            "hostess.issue.projected_motion_breath_package_evidence_schema",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.package_status",
            source_package_evidence_status == READY_STATUS,
            "source package evidence intake is ready",
            "source package evidence intake is blocked or rejected",
            (
                package_evidence_intake.get("issue_code")
                if isinstance(package_evidence_intake, dict)
                else None
            )
            or "hostess.issue.projected_motion_breath_package_evidence_not_ready",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.required_checks",
            pmb_required_package_checks_ready(
                required_package_checks,
                package_required_check_count,
                package_ready_required_check_count,
                package_blocked_required_check_count,
            ),
            "all projected-motion breath package checks are ready",
            "projected-motion breath required package checks are missing or blocked",
            "hostess.issue.projected_motion_breath_required_package_checks",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.package_evidence_entries",
            pmb_package_evidence_intake_matches_required_checks(
                package_evidence_intake,
                required_package_checks,
            ),
            "package evidence intake entries match projected-motion breath requirements",
            "package evidence intake entries do not match projected-motion breath requirements",
            "hostess.issue.projected_motion_breath_package_evidence_entries",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.target_contract",
            authoring_review.get("target_package_id") == PMB_TARGET_PACKAGE_ID
            and authoring_review.get("target_module_id") == PMB_TARGET_MODULE_ID
            and authoring_review.get("proposed_command_id") == PMB_PROPOSED_COMMAND_ID,
            "projected-motion breath target package, module, and command are supported",
            "projected-motion breath target package, module, or command drifted",
            "hostess.issue.projected_motion_breath_target_contract",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.authority_boundary",
            pmb_source_authority_preserved(authoring_review, package_evidence_intake),
            "Studio, Manifold, and Hostess authorities are preserved",
            "Studio, Manifold, or Hostess authority fields drifted",
            "hostess.issue.projected_motion_breath_authority_mismatch",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.source_no_execution",
            pmb_sources_did_not_execute(
                authoring_review,
                package_evidence_intake,
                source_adapter_selection_review,
            ),
            "source Studio artifacts did not execute runtime or platform work",
            "source Studio artifacts indicate runtime or platform execution",
            "hostess.issue.projected_motion_breath_source_execution_started",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.source_adapter_selection_schema",
            (not source_adapter_selection_present)
            or source_adapter_selection_schema
            == STUDIO_PMB_SOURCE_ADAPTER_SELECTION_REVIEW_SCHEMA,
            "source adapter selection schema is supported or absent",
            "source adapter selection schema is unsupported",
            "hostess.issue.projected_motion_breath_source_adapter_selection_schema",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.source_adapter_selection_status",
            (not source_adapter_selection_present)
            or source_adapter_selection_status == READY_STATUS,
            "source adapter selection is ready or absent",
            "source adapter selection is blocked or rejected",
            (
                source_adapter_selection_review.get("issue_code")
                if source_adapter_selection_present
                else None
            )
            or "hostess.issue.projected_motion_breath_source_adapter_selection_not_ready",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.source_adapter_selection_target_contract",
            pmb_source_adapter_selection_targets_authoring(
                authoring_review,
                source_adapter_selection_review,
            ),
            "source adapter selection targets the same projected-motion breath profile",
            "source adapter selection target package, module, or profile drifted",
            "hostess.issue.projected_motion_breath_source_adapter_selection_target",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.source_adapter_selection_stream_binding",
            pmb_source_adapter_selection_stream_binding_supported(
                source_adapter_selection_review
            ),
            "source adapter selection maps to a supported PMB processor input stream",
            "source adapter selection stream binding is unsupported",
            "hostess.issue.projected_motion_breath_source_adapter_selection_stream",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff.source_adapter_selection_authority",
            (not source_adapter_selection_present)
            or pmb_authority_fields_match(source_adapter_selection_review),
            "source adapter selection preserves Studio, Manifold, and Hostess authority fields",
            "source adapter selection authority fields drifted",
            "hostess.issue.projected_motion_breath_source_adapter_selection_authority",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    status = READY_STATUS if not failed else BLOCKED_STATUS
    issue_code = failed[0]["issue_code"] if failed else None
    slots = pmb_validation_slots(
        status,
        issue_code,
        source_adapter_selection_present,
    )
    ready_slots = [slot for slot in slots if slot.get("status") == READY_STATUS]
    blocked_slots = [slot for slot in slots if slot.get("status") == BLOCKED_STATUS]
    profile_id = authoring_review.get("profile_id")
    handoff_id = (
        f"hostess.projected_motion_breath_validation_handoff.{profile_id}"
        if isinstance(profile_id, str) and profile_id
        else "hostess.projected_motion_breath_validation_handoff.unknown"
    )
    return {
        "$schema": PMB_VALIDATION_HANDOFF_SCHEMA,
        "handoff_id": handoff_id,
        "source_authoring_review_schema": authoring_review.get("$schema"),
        "source_authoring_review_path": (
            str(authoring_review_path) if authoring_review_path is not None else None
        ),
        "source_package_evidence_schema": source_package_evidence_schema,
        "source_package_evidence_path": source_package_evidence_path,
        "source_adapter_selection_present": source_adapter_selection_present,
        "source_adapter_selection_schema": source_adapter_selection_schema,
        "source_adapter_selection_path": (
            str(source_adapter_selection_review_path)
            if source_adapter_selection_review_path is not None
            else None
        ),
        "source_adapter_selection_status": source_adapter_selection_status,
        "status": status,
        "issue_code": issue_code,
        "execution_policy": PMB_VALIDATION_HANDOFF_POLICY,
        "handoff_owner": HOSTESS_OWNER,
        "authoring_owner": STUDIO_REQUESTER,
        "runtime_authority": MANIFOLD_OWNER,
        "platform_validation_authority": HOSTESS_OWNER,
        "studio_role": STUDIO_ROLE,
        "target_package_id": PMB_TARGET_PACKAGE_ID,
        "target_module_id": authoring_review.get("target_module_id"),
        "profile_id": profile_id,
        "proposed_command_id": authoring_review.get("proposed_command_id"),
        "validation_scope": "schema_only_pmb_synthetic_replay_handoff",
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "execution_performed": False,
        "build_started": False,
        "copy_started": False,
        "stage_started": False,
        "install_started": False,
        "launch_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "source_authoring_review_status": authoring_review.get("status"),
        "source_package_evidence_status": source_package_evidence_status,
        "selected_adapter_id": selected_adapter_id,
        "selected_source_kind": selected_source_kind,
        "selected_input_kind": selected_input_kind,
        "selected_output_stream_id": selected_output_stream_id,
        "package_required_check_count": package_required_check_count,
        "package_ready_required_check_count": package_ready_required_check_count,
        "package_blocked_required_check_count": package_blocked_required_check_count,
        "required_package_checks": required_package_checks,
        "validation_slot_count": len(slots),
        "ready_validation_slot_count": len(ready_slots),
        "blocked_validation_slot_count": len(blocked_slots),
        "validation_slots": slots,
        "checks": checks,
        "next_required_action": (
            "prepare_pmb_replay_validation_fixture_review"
            if status == READY_STATUS
            else "repair_pmb_authoring_review_or_package_evidence"
        ),
    }


def validate_projected_motion_breath_validation_handoff(
    handoff: dict[str, Any],
) -> dict[str, Any]:
    slots = pmb_validation_slot_dicts(handoff)
    source_adapter_selection_present = (
        handoff.get("source_adapter_selection_present") is True
    )
    ready_slots = [slot for slot in slots if slot.get("status") == READY_STATUS]
    blocked_slots = [slot for slot in slots if slot.get("status") == BLOCKED_STATUS]
    embedded_checks = pmb_embedded_check_dicts(handoff)
    embedded_failed = [
        entry for entry in embedded_checks if entry.get("status") == FAIL_STATUS
    ]
    status = handoff.get("status")
    checks = [
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.schema",
            handoff.get("$schema") == PMB_VALIDATION_HANDOFF_SCHEMA,
            "projected-motion breath validation handoff schema is supported",
            "projected-motion breath validation handoff schema is unsupported",
            "hostess.issue.projected_motion_breath_validation_handoff_schema",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.status",
            status in {READY_STATUS, BLOCKED_STATUS}
            and (
                (status == READY_STATUS and handoff.get("issue_code") is None)
                or (status == BLOCKED_STATUS and isinstance(handoff.get("issue_code"), str))
            ),
            "projected-motion breath validation handoff status is consistent",
            "projected-motion breath validation handoff status is inconsistent",
            "hostess.issue.projected_motion_breath_validation_handoff_status",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.execution_policy",
            handoff.get("execution_policy") == PMB_VALIDATION_HANDOFF_POLICY,
            "projected-motion breath validation handoff is review-only",
            "projected-motion breath validation handoff execution policy drifted",
            "hostess.issue.projected_motion_breath_validation_handoff_execution_policy",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.authority",
            handoff.get("handoff_owner") == HOSTESS_OWNER
            and handoff.get("authoring_owner") == STUDIO_REQUESTER
            and handoff.get("runtime_authority") == MANIFOLD_OWNER
            and handoff.get("platform_validation_authority") == HOSTESS_OWNER
            and handoff.get("studio_role") == STUDIO_ROLE,
            "Hostess, Studio, and Manifold authority fields are separated",
            "Hostess, Studio, or Manifold authority fields drifted",
            "hostess.issue.projected_motion_breath_validation_handoff_authority",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.target_contract",
            handoff.get("target_package_id") == PMB_TARGET_PACKAGE_ID
            and handoff.get("target_module_id") == PMB_TARGET_MODULE_ID
            and handoff.get("proposed_command_id") == PMB_PROPOSED_COMMAND_ID,
            "projected-motion breath target contract is supported",
            "projected-motion breath target contract drifted",
            "hostess.issue.projected_motion_breath_validation_handoff_target_contract",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.source_schemas",
            handoff.get("source_authoring_review_schema")
            == STUDIO_PMB_AUTHORING_REVIEW_SCHEMA
            and handoff.get("source_package_evidence_schema")
            == STUDIO_PACKAGE_EVIDENCE_INTAKE_SCHEMA
            and (
                not source_adapter_selection_present
                or handoff.get("source_adapter_selection_schema")
                == STUDIO_PMB_SOURCE_ADAPTER_SELECTION_REVIEW_SCHEMA
            ),
            "source Studio schemas are supported",
            "source Studio schemas are unsupported",
            "hostess.issue.projected_motion_breath_validation_handoff_source_schema",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.source_statuses",
            (
                status == READY_STATUS
                and handoff.get("source_authoring_review_status") == READY_STATUS
                and handoff.get("source_package_evidence_status") == READY_STATUS
                and (
                    not source_adapter_selection_present
                    or handoff.get("source_adapter_selection_status") == READY_STATUS
                )
            )
            or status == BLOCKED_STATUS,
            "source Studio statuses match handoff readiness",
            "source Studio statuses do not match handoff readiness",
            "hostess.issue.projected_motion_breath_validation_handoff_source_status",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.required_checks",
            (
                status == READY_STATUS
                and pmb_required_package_checks_ready(
                    pmb_required_package_checks(handoff),
                    int_or_zero(handoff.get("package_required_check_count")),
                    int_or_zero(handoff.get("package_ready_required_check_count")),
                    int_or_zero(handoff.get("package_blocked_required_check_count")),
                )
            )
            or (
                status == BLOCKED_STATUS
                and set(PMB_REQUIRED_PACKAGE_CHECKS).issubset(
                    set(pmb_required_package_checks(handoff))
                )
            ),
            "projected-motion breath package checks match handoff status",
            "projected-motion breath package checks are inconsistent with handoff status",
            "hostess.issue.projected_motion_breath_validation_handoff_required_checks",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.source_adapter_selection",
            status == BLOCKED_STATUS
            or pmb_source_adapter_selection_handoff_fields_match(
                handoff,
                source_adapter_selection_present,
            ),
            "source adapter selection handoff fields are consistent",
            "source adapter selection handoff fields are inconsistent",
            "hostess.issue.projected_motion_breath_validation_handoff_source_adapter_selection",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.no_execution_started",
            pmb_validation_handoff_unstarted(handoff),
            "projected-motion breath validation handoff has not started execution",
            "projected-motion breath validation handoff indicates execution",
            "hostess.issue.projected_motion_breath_validation_handoff_execution_started",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.slots",
            pmb_validation_slots_match_contracts(
                slots,
                status,
                source_adapter_selection_present,
            ),
            "projected-motion breath validation slots match the Hostess handoff contract",
            "projected-motion breath validation slots drifted from the Hostess handoff contract",
            "hostess.issue.projected_motion_breath_validation_handoff_slot_drift",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.slot_counts",
            handoff.get("validation_slot_count") == len(slots)
            and handoff.get("ready_validation_slot_count") == len(ready_slots)
            and handoff.get("blocked_validation_slot_count") == len(blocked_slots),
            "projected-motion breath validation slot counts match slots",
            "projected-motion breath validation slot counts do not match slots",
            "hostess.issue.projected_motion_breath_validation_handoff_slot_counts",
        ),
        check(
            "hostess.check.projected_motion_breath_validation_handoff_validation.embedded_checks",
            (
                status == READY_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_checks)
            )
            or (
                status == BLOCKED_STATUS
                and bool(embedded_failed)
                and handoff.get("issue_code") == embedded_failed[0].get("issue_code")
            ),
            "embedded handoff checks match handoff status",
            "embedded handoff checks do not match handoff status",
            "hostess.issue.projected_motion_breath_validation_handoff_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": PMB_VALIDATION_HANDOFF_VALIDATION_SCHEMA,
        "handoff_id": handoff.get("handoff_id"),
        "source_handoff_schema": handoff.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def pmb_required_package_checks(source: dict[str, Any]) -> list[str]:
    checks = source.get("required_package_checks", [])
    if not isinstance(checks, list):
        return []
    return [entry for entry in checks if isinstance(entry, str)]


def int_or_zero(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def pmb_required_package_checks_ready(
    required_package_checks: list[str],
    required_check_count: int,
    ready_required_check_count: int,
    blocked_required_check_count: int,
) -> bool:
    return (
        set(PMB_REQUIRED_PACKAGE_CHECKS).issubset(set(required_package_checks))
        and required_check_count >= len(PMB_REQUIRED_PACKAGE_CHECKS)
        and ready_required_check_count >= len(PMB_REQUIRED_PACKAGE_CHECKS)
        and blocked_required_check_count == 0
    )


def pmb_package_evidence_intake_matches_required_checks(
    package_evidence_intake: dict[str, Any] | None,
    required_package_checks: list[str],
) -> bool:
    if package_evidence_intake is None:
        return True
    if package_evidence_intake.get("$schema") != STUDIO_PACKAGE_EVIDENCE_INTAKE_SCHEMA:
        return False
    if package_evidence_intake.get("target_package_id") != PMB_TARGET_PACKAGE_ID:
        return False
    if package_evidence_intake.get("status") != READY_STATUS:
        return False
    if not pmb_required_package_checks_ready(
        required_package_checks,
        int_or_zero(package_evidence_intake.get("required_check_count")),
        int_or_zero(package_evidence_intake.get("ready_required_check_count")),
        int_or_zero(package_evidence_intake.get("blocked_required_check_count")),
    ):
        return False
    entries = package_evidence_intake.get("entries", [])
    if not isinstance(entries, list):
        return False
    ready_required_entry_ids = {
        entry.get("check_id")
        for entry in entries
        if isinstance(entry, dict)
        and entry.get("required_for_studio") is True
        and entry.get("decision") == READY_STATUS
    }
    return set(PMB_REQUIRED_PACKAGE_CHECKS).issubset(ready_required_entry_ids)


def pmb_source_authority_preserved(
    authoring_review: dict[str, Any],
    package_evidence_intake: dict[str, Any] | None,
) -> bool:
    if not pmb_authority_fields_match(authoring_review):
        return False
    return (
        package_evidence_intake is None
        or pmb_authority_fields_match(package_evidence_intake)
    )


def pmb_authority_fields_match(source: dict[str, Any]) -> bool:
    return (
        source.get("runtime_authority") == MANIFOLD_OWNER
        and source.get("authoring_authority") == STUDIO_REQUESTER
        and source.get("platform_validation_authority") == HOSTESS_OWNER
    )


def pmb_source_adapter_selection_targets_authoring(
    authoring_review: dict[str, Any],
    source_adapter_selection_review: dict[str, Any] | None,
) -> bool:
    if source_adapter_selection_review is None:
        return True
    return (
        source_adapter_selection_review.get("target_package_id") == PMB_TARGET_PACKAGE_ID
        and source_adapter_selection_review.get("target_module_id")
        == PMB_TARGET_MODULE_ID
        and source_adapter_selection_review.get("profile_id")
        == authoring_review.get("profile_id")
    )


def pmb_source_adapter_selection_stream_binding_supported(
    source_adapter_selection_review: dict[str, Any] | None,
) -> bool:
    if source_adapter_selection_review is None:
        return True
    input_kind = source_adapter_selection_review.get("selected_input_kind")
    return (
        isinstance(input_kind, str)
        and source_adapter_selection_review.get("selected_output_stream_id")
        == PMB_SOURCE_ADAPTER_STREAM_BINDINGS.get(input_kind)
    )


def pmb_source_adapter_selection_handoff_fields_match(
    handoff: dict[str, Any],
    source_adapter_selection_present: bool,
) -> bool:
    if not source_adapter_selection_present:
        return (
            handoff.get("source_adapter_selection_schema") is None
            and handoff.get("source_adapter_selection_status") is None
            and handoff.get("selected_adapter_id") is None
            and handoff.get("selected_source_kind") is None
            and handoff.get("selected_input_kind") is None
            and handoff.get("selected_output_stream_id") is None
        )
    input_kind = handoff.get("selected_input_kind")
    base_fields_match = (
        handoff.get("source_adapter_selection_schema")
        == STUDIO_PMB_SOURCE_ADAPTER_SELECTION_REVIEW_SCHEMA
        and handoff.get("source_adapter_selection_status") == READY_STATUS
        and isinstance(handoff.get("selected_adapter_id"), str)
        and isinstance(handoff.get("selected_source_kind"), str)
        and isinstance(input_kind, str)
        and isinstance(handoff.get("selected_output_stream_id"), str)
    )
    if not base_fields_match:
        return False
    if handoff.get("status") == BLOCKED_STATUS:
        return isinstance(handoff.get("issue_code"), str)
    return (
        handoff.get("selected_output_stream_id")
        == PMB_SOURCE_ADAPTER_STREAM_BINDINGS.get(input_kind)
    )


def pmb_sources_did_not_execute(
    authoring_review: dict[str, Any],
    package_evidence_intake: dict[str, Any] | None,
    source_adapter_selection_review: dict[str, Any] | None = None,
) -> bool:
    authoring_clean = (
        authoring_review.get("runtime_execution_performed") is False
        and authoring_review.get("platform_execution_performed") is False
        and authoring_review.get("execution_policy") == "not_executed.proposal_only"
    )
    if not authoring_clean:
        return False
    source_adapter_selection_clean = (
        source_adapter_selection_review is None
        or (
            source_adapter_selection_review.get("runtime_execution_performed") is False
            and source_adapter_selection_review.get("platform_execution_performed") is False
            and source_adapter_selection_review.get("execution_policy")
            == "not_executed.proposal_only"
        )
    )
    if not source_adapter_selection_clean:
        return False
    if package_evidence_intake is None:
        return True
    return (
        package_evidence_intake.get("runtime_execution_performed") is False
        and package_evidence_intake.get("platform_execution_performed") is False
        and package_evidence_intake.get("execution_policy") == "not_executed.review_only"
    )


def pmb_validation_slots(
    status: str,
    issue_code: str | None,
    source_adapter_selection_present: bool = False,
) -> list[dict[str, Any]]:
    slot_status = READY_STATUS if status == READY_STATUS else BLOCKED_STATUS
    contracts = pmb_validation_slot_contracts(source_adapter_selection_present)
    return [
        {
            "slot_id": contract["slot_id"],
            "owner": contract["owner"],
            "route_kind": contract["route_kind"],
            "expected_input_kind": contract["expected_input_kind"],
            "validation_kind": contract["validation_kind"],
            "status": slot_status,
            "issue_code": None if slot_status == READY_STATUS else issue_code,
            "device_required": False,
            "schema_path_execution_allowed": False,
            "platform_execution_allowed": False,
            "studio_execution_allowed": False,
            "execution_started": False,
            "runtime_execution_performed": False,
            "platform_execution_performed": False,
            "build_started": False,
            "install_started": False,
            "launch_started": False,
            "evidence_collection_started": False,
            "command_session_started": False,
        }
        for contract in contracts
    ]


def pmb_validation_slot_contracts(
    source_adapter_selection_present: bool,
) -> list[dict[str, str]]:
    contracts = list(PMB_VALIDATION_SLOT_CONTRACTS)
    if source_adapter_selection_present:
        contracts.append(PMB_SOURCE_ADAPTER_SELECTION_SLOT_CONTRACT)
    return contracts


def pmb_validation_slot_dicts(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    slots = handoff.get("validation_slots", [])
    if not isinstance(slots, list):
        return []
    return [slot for slot in slots if isinstance(slot, dict)]


def pmb_embedded_check_dicts(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    checks = handoff.get("checks", [])
    if not isinstance(checks, list):
        return []
    return [entry for entry in checks if isinstance(entry, dict)]


def pmb_validation_slots_match_contracts(
    slots: list[dict[str, Any]],
    handoff_status: Any,
    source_adapter_selection_present: bool = False,
) -> bool:
    if handoff_status not in {READY_STATUS, BLOCKED_STATUS}:
        return False
    expected_slot_status = READY_STATUS if handoff_status == READY_STATUS else BLOCKED_STATUS
    contracts = pmb_validation_slot_contracts(source_adapter_selection_present)
    if len(slots) != len(contracts):
        return False
    by_id = {slot.get("slot_id"): slot for slot in slots}
    for contract in contracts:
        slot = by_id.get(contract["slot_id"])
        if not isinstance(slot, dict):
            return False
        for key in ("owner", "route_kind", "expected_input_kind", "validation_kind"):
            if slot.get(key) != contract[key]:
                return False
        if slot.get("status") != expected_slot_status:
            return False
        if expected_slot_status == READY_STATUS and slot.get("issue_code") is not None:
            return False
        if expected_slot_status == BLOCKED_STATUS and not isinstance(
            slot.get("issue_code"),
            str,
        ):
            return False
        if not pmb_validation_slot_unstarted(slot):
            return False
    return True


def pmb_validation_slot_unstarted(slot: dict[str, Any]) -> bool:
    return (
        slot.get("device_required") is False
        and slot.get("schema_path_execution_allowed") is False
        and slot.get("platform_execution_allowed") is False
        and slot.get("studio_execution_allowed") is False
        and slot.get("execution_started") is False
        and slot.get("runtime_execution_performed") is False
        and slot.get("platform_execution_performed") is False
        and slot.get("build_started") is False
        and slot.get("install_started") is False
        and slot.get("launch_started") is False
        and slot.get("evidence_collection_started") is False
        and slot.get("command_session_started") is False
    )


def pmb_validation_handoff_unstarted(handoff: dict[str, Any]) -> bool:
    return (
        all(handoff.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
        and handoff.get("device_required") is False
        and handoff.get("schema_path_execution_allowed") is False
        and handoff.get("platform_execution_allowed") is False
        and handoff.get("studio_execution_allowed") is False
        and handoff.get("runtime_execution_performed") is False
        and handoff.get("platform_execution_performed") is False
    )
