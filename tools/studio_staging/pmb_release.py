"""Projected-motion breath and operator-release staging receipts."""

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


def build_projected_motion_breath_replay_validation_receipt(
    handoff: dict[str, Any],
    replay_descriptor_source: dict[str, Any] | None = None,
    replay_descriptor_source_path: Path | None = None,
) -> dict[str, Any]:
    handoff_validation = validate_projected_motion_breath_validation_handoff(handoff)
    source_adapter_selection_present = (
        handoff.get("source_adapter_selection_present") is True
    )
    descriptor_source_matches = pmb_replay_descriptor_source_matches_contracts(
        replay_descriptor_source
    )
    checks = [
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt.handoff_schema",
            handoff.get("$schema") == PMB_VALIDATION_HANDOFF_SCHEMA,
            "projected-motion breath validation handoff schema is supported",
            "projected-motion breath validation handoff schema is unsupported",
            "hostess.issue.projected_motion_breath_replay_handoff_schema",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt.handoff_ready",
            handoff.get("status") == READY_STATUS
            and handoff_validation.get("status") == PASS_STATUS,
            "projected-motion breath validation handoff is ready and validated",
            "projected-motion breath validation handoff is blocked or invalid",
            handoff.get("issue_code")
            or handoff_validation.get("issue_code")
            or "hostess.issue.projected_motion_breath_replay_handoff_not_ready",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt.handoff_slots",
            int_or_zero(handoff.get("ready_validation_slot_count"))
            == len(pmb_validation_slot_contracts(source_adapter_selection_present))
            and int_or_zero(handoff.get("blocked_validation_slot_count")) == 0
            and pmb_validation_slots_match_contracts(
                pmb_validation_slot_dicts(handoff),
                READY_STATUS,
                source_adapter_selection_present,
            ),
            "all projected-motion breath handoff validation slots are ready",
            "projected-motion breath handoff validation slots are blocked or drifted",
            "hostess.issue.projected_motion_breath_replay_handoff_slots",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt.target_contract",
            handoff.get("target_package_id") == PMB_TARGET_PACKAGE_ID
            and handoff.get("target_module_id") == PMB_TARGET_MODULE_ID
            and handoff.get("proposed_command_id") == PMB_PROPOSED_COMMAND_ID,
            "projected-motion breath replay receipt target contract is supported",
            "projected-motion breath replay receipt target contract drifted",
            "hostess.issue.projected_motion_breath_replay_target_contract",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt.no_execution_started",
            pmb_validation_handoff_unstarted(handoff),
            "source handoff did not start execution",
            "source handoff indicates execution",
            "hostess.issue.projected_motion_breath_replay_source_execution_started",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt.descriptors",
            descriptor_source_matches,
            "projected-motion breath replay descriptors match expected pure-processor contracts",
            "projected-motion breath replay descriptors are missing or drifted",
            "hostess.issue.projected_motion_breath_replay_descriptor_drift",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    status = VALIDATED_STATUS if not failed else REJECTED_STATUS
    issue_code = failed[0]["issue_code"] if failed else None
    descriptors = pmb_replay_descriptor_rows(
        replay_descriptor_source,
        status,
        issue_code,
    )
    validated_descriptors = [
        entry for entry in descriptors if entry.get("descriptor_status") == VALIDATED_STATUS
    ]
    rejected_descriptors = [
        entry for entry in descriptors if entry.get("descriptor_status") == REJECTED_STATUS
    ]
    return {
        "$schema": PMB_REPLAY_VALIDATION_RECEIPT_SCHEMA,
        "receipt_id": pmb_replay_receipt_id(handoff),
        "source_handoff_id": handoff.get("handoff_id"),
        "source_handoff_schema": handoff.get("$schema"),
        "source_handoff_status": handoff.get("status"),
        "source_handoff_validation_status": handoff_validation.get("status"),
        "source_replay_descriptor_path": (
            str(replay_descriptor_source_path)
            if replay_descriptor_source_path is not None
            else None
        ),
        "status": status,
        "issue_code": issue_code,
        "execution_policy": PMB_REPLAY_VALIDATION_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "handoff_owner": HOSTESS_OWNER,
        "runtime_authority": MANIFOLD_OWNER,
        "platform_validation_authority": HOSTESS_OWNER,
        "studio_role": STUDIO_ROLE,
        "target_package_id": PMB_TARGET_PACKAGE_ID,
        "target_module_id": handoff.get("target_module_id"),
        "profile_id": handoff.get("profile_id"),
        "proposed_command_id": handoff.get("proposed_command_id"),
        "validation_scope": "schema_only_pmb_synthetic_replay_receipt",
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
        "replay_execution_started": False,
        "fixture_payloads_copied": False,
        "processor_runtime_started": False,
        "scorecard_status": PASS_STATUS if status == VALIDATED_STATUS else FAIL_STATUS,
        "replay_descriptor_count": len(descriptors),
        "validated_replay_descriptor_count": len(validated_descriptors),
        "rejected_replay_descriptor_count": len(rejected_descriptors),
        "replay_descriptors": descriptors,
        "checks": checks,
        "next_required_action": (
            "prepare_pmb_replay_scorecard_review"
            if status == VALIDATED_STATUS
            else "repair_pmb_replay_descriptor_or_handoff"
        ),
    }


def validate_projected_motion_breath_replay_validation_receipt(
    receipt: dict[str, Any],
) -> dict[str, Any]:
    descriptors = pmb_replay_descriptor_dicts(receipt)
    validated_descriptors = [
        entry for entry in descriptors if entry.get("descriptor_status") == VALIDATED_STATUS
    ]
    rejected_descriptors = [
        entry for entry in descriptors if entry.get("descriptor_status") == REJECTED_STATUS
    ]
    embedded_checks = pmb_embedded_check_dicts(receipt)
    embedded_failed = [
        entry for entry in embedded_checks if entry.get("status") == FAIL_STATUS
    ]
    status = receipt.get("status")
    checks = [
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.schema",
            receipt.get("$schema") == PMB_REPLAY_VALIDATION_RECEIPT_SCHEMA,
            "projected-motion breath replay validation receipt schema is supported",
            "projected-motion breath replay validation receipt schema is unsupported",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_schema",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.status",
            status in {VALIDATED_STATUS, REJECTED_STATUS}
            and (
                (status == VALIDATED_STATUS and receipt.get("issue_code") is None)
                or (status == REJECTED_STATUS and isinstance(receipt.get("issue_code"), str))
            ),
            "projected-motion breath replay validation receipt status is consistent",
            "projected-motion breath replay validation receipt status is inconsistent",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_status",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.execution_policy",
            receipt.get("execution_policy") == PMB_REPLAY_VALIDATION_RECEIPT_POLICY,
            "projected-motion breath replay validation receipt is review-only",
            "projected-motion breath replay validation receipt execution policy drifted",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_execution_policy",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("handoff_owner") == HOSTESS_OWNER
            and receipt.get("runtime_authority") == MANIFOLD_OWNER
            and receipt.get("platform_validation_authority") == HOSTESS_OWNER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess and Manifold authority fields are separated",
            "Hostess or Manifold authority fields drifted",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_authority",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.target_contract",
            receipt.get("target_package_id") == PMB_TARGET_PACKAGE_ID
            and receipt.get("target_module_id") == PMB_TARGET_MODULE_ID
            and receipt.get("proposed_command_id") == PMB_PROPOSED_COMMAND_ID,
            "projected-motion breath replay target contract is supported",
            "projected-motion breath replay target contract drifted",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_target_contract",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.source_handoff",
            (
                status == VALIDATED_STATUS
                and receipt.get("source_handoff_schema") == PMB_VALIDATION_HANDOFF_SCHEMA
                and receipt.get("source_handoff_status") == READY_STATUS
                and receipt.get("source_handoff_validation_status") == PASS_STATUS
            )
            or status == REJECTED_STATUS,
            "source projected-motion breath handoff matches receipt status",
            "source projected-motion breath handoff does not match receipt status",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_source_handoff",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.no_execution_started",
            pmb_replay_validation_receipt_unstarted(receipt),
            "projected-motion breath replay validation receipt has not started execution",
            "projected-motion breath replay validation receipt indicates execution",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_execution_started",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.descriptors",
            pmb_replay_descriptors_match_contracts(descriptors, status),
            "projected-motion breath replay descriptors match expected contracts",
            "projected-motion breath replay descriptors drifted",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_descriptor_drift",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.counts",
            receipt.get("replay_descriptor_count") == len(descriptors)
            and receipt.get("validated_replay_descriptor_count")
            == len(validated_descriptors)
            and receipt.get("rejected_replay_descriptor_count")
            == len(rejected_descriptors),
            "projected-motion breath replay descriptor counts match descriptors",
            "projected-motion breath replay descriptor counts do not match descriptors",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_counts",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.scorecard",
            (
                status == VALIDATED_STATUS
                and receipt.get("scorecard_status") == PASS_STATUS
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("scorecard_status") == FAIL_STATUS
            ),
            "projected-motion breath replay scorecard status matches receipt status",
            "projected-motion breath replay scorecard status drifted",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_scorecard",
        ),
        check(
            "hostess.check.projected_motion_breath_replay_validation_receipt_validation.embedded_checks",
            (
                status == VALIDATED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_checks)
            )
            or (
                status == REJECTED_STATUS
                and bool(embedded_failed)
                and receipt.get("issue_code") == embedded_failed[0].get("issue_code")
            ),
            "embedded replay receipt checks match receipt status",
            "embedded replay receipt checks do not match receipt status",
            "hostess.issue.projected_motion_breath_replay_validation_receipt_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": PMB_REPLAY_VALIDATION_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def pmb_replay_receipt_id(handoff: dict[str, Any]) -> str:
    profile_id = handoff.get("profile_id")
    return (
        f"hostess.projected_motion_breath_replay_validation_receipt.{profile_id}"
        if isinstance(profile_id, str) and profile_id
        else "hostess.projected_motion_breath_replay_validation_receipt.unknown"
    )


def pmb_replay_descriptor_source_matches_contracts(
    source: dict[str, Any] | None,
) -> bool:
    rows = pmb_replay_descriptor_rows(source, VALIDATED_STATUS, None)
    return pmb_replay_descriptors_match_contracts(rows, VALIDATED_STATUS)


def pmb_replay_descriptor_rows(
    source: dict[str, Any] | None,
    receipt_status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    source_by_id = pmb_replay_source_descriptor_by_id(source)
    rows = []
    for contract in PMB_REPLAY_DESCRIPTOR_CONTRACTS:
        supplied = source is None or contract["descriptor_id"] in source_by_id
        source_descriptor = source_by_id.get(contract["descriptor_id"], {})
        matches_contract = supplied and (
            source is None
            or all(
                source_descriptor.get(key) == contract[key]
                for key in (
                    "owner",
                    "fixture_kind",
                    "case_id",
                    "expected_processor_status",
                    "validation_kind",
                )
            )
        )
        descriptor_status = (
            VALIDATED_STATUS
            if receipt_status == VALIDATED_STATUS and matches_contract
            else REJECTED_STATUS
        )
        rows.append(
            {
                "descriptor_id": contract["descriptor_id"],
                "owner": contract["owner"],
                "fixture_kind": contract["fixture_kind"],
                "case_id": contract["case_id"],
                "expected_processor_status": contract["expected_processor_status"],
                "validation_kind": contract["validation_kind"],
                "descriptor_supplied": supplied,
                "source_descriptor_matches_contract": matches_contract,
                "descriptor_status": descriptor_status,
                "issue_code": None if descriptor_status == VALIDATED_STATUS else issue_code,
                "device_required": False,
                "schema_path_execution_allowed": False,
                "platform_execution_allowed": False,
                "studio_execution_allowed": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "execution_started": False,
                "replay_execution_started": False,
                "fixture_payload_copied": False,
                "processor_runtime_started": False,
                "evidence_collection_started": False,
                "command_session_started": False,
            }
        )
    return rows


def pmb_replay_source_descriptor_by_id(
    source: dict[str, Any] | None,
) -> dict[Any, dict[str, Any]]:
    if source is None:
        return {}
    rows = source.get("replay_descriptors", source.get("descriptors", []))
    if not isinstance(rows, list):
        return {}
    return {
        row.get("descriptor_id"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("descriptor_id"), str)
    }


def pmb_replay_descriptor_dicts(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    descriptors = receipt.get("replay_descriptors", [])
    if not isinstance(descriptors, list):
        return []
    return [entry for entry in descriptors if isinstance(entry, dict)]


def pmb_replay_descriptors_match_contracts(
    descriptors: list[dict[str, Any]],
    receipt_status: Any,
) -> bool:
    if receipt_status not in {VALIDATED_STATUS, REJECTED_STATUS}:
        return False
    expected_descriptor_status = (
        VALIDATED_STATUS if receipt_status == VALIDATED_STATUS else REJECTED_STATUS
    )
    if len(descriptors) != len(PMB_REPLAY_DESCRIPTOR_CONTRACTS):
        return False
    by_id = {entry.get("descriptor_id"): entry for entry in descriptors}
    for contract in PMB_REPLAY_DESCRIPTOR_CONTRACTS:
        descriptor = by_id.get(contract["descriptor_id"])
        if not isinstance(descriptor, dict):
            return False
        for key in (
            "owner",
            "fixture_kind",
            "case_id",
            "expected_processor_status",
            "validation_kind",
        ):
            if descriptor.get(key) != contract[key]:
                return False
        if descriptor.get("descriptor_status") != expected_descriptor_status:
            return False
        if expected_descriptor_status == VALIDATED_STATUS:
            if descriptor.get("issue_code") is not None:
                return False
            if descriptor.get("source_descriptor_matches_contract") is not True:
                return False
        if expected_descriptor_status == REJECTED_STATUS and descriptor.get(
            "descriptor_status"
        ) != REJECTED_STATUS:
            return False
        if not pmb_replay_descriptor_unstarted(descriptor):
            return False
    return True


def pmb_replay_descriptor_unstarted(descriptor: dict[str, Any]) -> bool:
    return (
        descriptor.get("device_required") is False
        and descriptor.get("schema_path_execution_allowed") is False
        and descriptor.get("platform_execution_allowed") is False
        and descriptor.get("studio_execution_allowed") is False
        and descriptor.get("runtime_execution_performed") is False
        and descriptor.get("platform_execution_performed") is False
        and descriptor.get("execution_started") is False
        and descriptor.get("replay_execution_started") is False
        and descriptor.get("fixture_payload_copied") is False
        and descriptor.get("processor_runtime_started") is False
        and descriptor.get("evidence_collection_started") is False
        and descriptor.get("command_session_started") is False
    )


def pmb_replay_validation_receipt_unstarted(receipt: dict[str, Any]) -> bool:
    return (
        all(receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
        and receipt.get("device_required") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("replay_execution_started") is False
        and receipt.get("fixture_payloads_copied") is False
        and receipt.get("processor_runtime_started") is False
    )


def build_operator_release_readiness_bundle(
    platform_smoke_evidence_review: dict[str, Any],
    pmb_replay_validation_receipt: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    pmb_validation = validate_projected_motion_breath_replay_validation_receipt(
        pmb_replay_validation_receipt
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    platform_ready = platform_smoke_evidence_review_source_ready(
        platform_smoke_evidence_review
    )
    pmb_ready = pmb_replay_validation_receipt_source_ready(
        pmb_replay_validation_receipt,
        pmb_validation,
    )
    if decision == REJECTED_STATUS:
        status = REJECTED_STATUS
    elif decision_supported and platform_ready and pmb_ready:
        status = READY_STATUS
    else:
        status = BLOCKED_STATUS
    issue_code = None
    if status != READY_STATUS:
        issue_code = (
            reason_code
            or platform_smoke_evidence_review.get("issue_code")
            or pmb_replay_validation_receipt.get("issue_code")
            or pmb_validation.get("issue_code")
            or (
                "hostess.issue.operator_release_readiness_bundle_decision"
                if not decision_supported
                else "hostess.issue.operator_release_readiness_source_not_ready"
            )
        )
    artifact_rows = operator_release_artifact_rows(
        platform_smoke_evidence_review,
        pmb_replay_validation_receipt,
        pmb_validation,
        status,
        issue_code,
    )
    host_shell_targets = operator_release_host_shell_targets(status, issue_code)
    ready_artifacts = [
        row for row in artifact_rows if row.get("artifact_status") == READY_STATUS
    ]
    blocked_artifacts = [
        row for row in artifact_rows if row.get("artifact_status") == BLOCKED_STATUS
    ]
    rejected_artifacts = [
        row for row in artifact_rows if row.get("artifact_status") == REJECTED_STATUS
    ]
    ready_targets = [
        row for row in host_shell_targets if row.get("target_status") == READY_STATUS
    ]
    blocked_targets = [
        row for row in host_shell_targets if row.get("target_status") == BLOCKED_STATUS
    ]
    rejected_targets = [
        row for row in host_shell_targets if row.get("target_status") == REJECTED_STATUS
    ]
    checks = operator_release_readiness_bundle_checks(
        platform_smoke_evidence_review,
        pmb_replay_validation_receipt,
        pmb_validation,
        artifact_rows,
        host_shell_targets,
        status,
        decision_supported,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == READY_STATUS:
        status = BLOCKED_STATUS
        issue_code = failed[0]["issue_code"]
        artifact_rows = operator_release_artifact_rows(
            platform_smoke_evidence_review,
            pmb_replay_validation_receipt,
            pmb_validation,
            status,
            issue_code,
        )
        host_shell_targets = operator_release_host_shell_targets(status, issue_code)
        ready_artifacts = [
            row for row in artifact_rows if row.get("artifact_status") == READY_STATUS
        ]
        blocked_artifacts = [
            row for row in artifact_rows if row.get("artifact_status") == BLOCKED_STATUS
        ]
        rejected_artifacts = [
            row for row in artifact_rows if row.get("artifact_status") == REJECTED_STATUS
        ]
        ready_targets = [
            row for row in host_shell_targets if row.get("target_status") == READY_STATUS
        ]
        blocked_targets = [
            row for row in host_shell_targets if row.get("target_status") == BLOCKED_STATUS
        ]
        rejected_targets = [
            row for row in host_shell_targets if row.get("target_status") == REJECTED_STATUS
        ]
    platform_review_id = platform_smoke_evidence_review.get("evidence_review_id")
    pmb_receipt_id = pmb_replay_validation_receipt.get("receipt_id")
    bundle_id = (
        f"hostess.operator_release_readiness_bundle.{platform_review_id}.{pmb_receipt_id}"
        if isinstance(platform_review_id, str)
        and platform_review_id
        and isinstance(pmb_receipt_id, str)
        and pmb_receipt_id
        else "hostess.operator_release_readiness_bundle.unknown"
    )
    pmb_review_required = (
        platform_smoke_evidence_review.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        platform_smoke_evidence_review.get("pmb_shell_handoff_review_ready") is True
    )
    return {
        "$schema": OPERATOR_RELEASE_READINESS_BUNDLE_SCHEMA,
        "bundle_id": bundle_id,
        "source_platform_smoke_evidence_review_id": platform_review_id,
        "source_platform_smoke_evidence_review_schema": platform_smoke_evidence_review.get(
            "$schema"
        ),
        "source_platform_smoke_evidence_review_status": platform_smoke_evidence_review.get(
            "status"
        ),
        "source_platform_smoke_evidence_review_scorecard_status": (
            platform_smoke_evidence_review.get("scorecard_status")
        ),
        "source_pmb_replay_validation_receipt_id": pmb_receipt_id,
        "source_pmb_replay_validation_receipt_schema": pmb_replay_validation_receipt.get(
            "$schema"
        ),
        "source_pmb_replay_validation_receipt_status": (
            pmb_replay_validation_receipt.get("status")
        ),
        "source_pmb_replay_validation_status": pmb_validation.get("status"),
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(platform_smoke_evidence_review),
        "target_package_id": pmb_replay_validation_receipt.get("target_package_id"),
        "target_module_id": pmb_replay_validation_receipt.get("target_module_id"),
        "profile_id": pmb_replay_validation_receipt.get("profile_id"),
        "status": status,
        "issue_code": issue_code,
        "execution_policy": OPERATOR_RELEASE_READINESS_BUNDLE_POLICY,
        "bundle_owner": HOSTESS_OWNER,
        "artifact_owner": HOSTESS_OWNER,
        "platform_validation_authority": HOSTESS_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "runtime_authority": MANIFOLD_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "studio_role": STUDIO_ROLE,
        "authoring_owner": STUDIO_REQUESTER,
        "operator_release_ready": status == READY_STATUS,
        "operator_start_required_before_platform_work": True,
        "operator_started": False,
        "host_shell_started": False,
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
        "replay_execution_started": False,
        "apk_build_started": False,
        "schema_artifact_payloads_copied": False,
        "release_payloads_copied": False,
        "evidence_payloads_copied": False,
        "scorecard_status": PASS_STATUS if status == READY_STATUS else FAIL_STATUS,
        "schema_artifact_count": len(artifact_rows),
        "ready_schema_artifact_count": len(ready_artifacts),
        "blocked_schema_artifact_count": len(blocked_artifacts),
        "rejected_schema_artifact_count": len(rejected_artifacts),
        "host_shell_readiness_target_count": len(host_shell_targets),
        "ready_host_shell_readiness_target_count": len(ready_targets),
        "blocked_host_shell_readiness_target_count": len(blocked_targets),
        "rejected_host_shell_readiness_target_count": len(rejected_targets),
        "schema_artifacts": artifact_rows,
        "host_shell_readiness_targets": host_shell_targets,
        "checks": checks,
        "next_required_action": (
            "handoff_schema_bundle_to_hostess_operator_shell_outside_studio"
            if status == READY_STATUS
            else "repair_or_decline_operator_release_readiness_bundle"
        ),
    }


def validate_operator_release_readiness_bundle(
    platform_smoke_evidence_review: dict[str, Any],
    pmb_replay_validation_receipt: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    pmb_validation = validate_projected_motion_breath_replay_validation_receipt(
        pmb_replay_validation_receipt
    )
    artifacts = operator_release_artifact_dicts(bundle)
    host_shell_targets = operator_release_host_shell_target_dicts(bundle)
    ready_artifacts = [
        row for row in artifacts if row.get("artifact_status") == READY_STATUS
    ]
    blocked_artifacts = [
        row for row in artifacts if row.get("artifact_status") == BLOCKED_STATUS
    ]
    rejected_artifacts = [
        row for row in artifacts if row.get("artifact_status") == REJECTED_STATUS
    ]
    ready_targets = [
        row for row in host_shell_targets if row.get("target_status") == READY_STATUS
    ]
    blocked_targets = [
        row for row in host_shell_targets if row.get("target_status") == BLOCKED_STATUS
    ]
    rejected_targets = [
        row for row in host_shell_targets if row.get("target_status") == REJECTED_STATUS
    ]
    embedded_checks = bundle.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [
        entry for entry in embedded_checks if isinstance(entry, dict)
    ]
    embedded_failed = [
        entry for entry in embedded_check_dicts if entry.get("status") == FAIL_STATUS
    ]
    status = bundle.get("status")
    pmb_review_required = (
        platform_smoke_evidence_review.get("pmb_shell_handoff_review_required") is True
    )
    pmb_platform_artifact = next(
        (
            row
            for row in artifacts
            if row.get("source_role") == "platform_smoke_evidence_review"
        ),
        None,
    )
    pmb_summary_matches_review = (
        pmb_shell_handoff_review_summary_from_source(bundle)
        == pmb_shell_handoff_review_summary_from_source(platform_smoke_evidence_review)
    )
    checks = [
        check(
            "hostess.check.operator_release_readiness_bundle.schema",
            bundle.get("$schema") == OPERATOR_RELEASE_READINESS_BUNDLE_SCHEMA,
            "operator release readiness bundle schema is supported",
            "operator release readiness bundle schema is unsupported",
            "hostess.issue.operator_release_readiness_bundle_schema",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.status",
            status in {READY_STATUS, BLOCKED_STATUS, REJECTED_STATUS}
            and (
                (status == READY_STATUS and bundle.get("issue_code") is None)
                or (
                    status in {BLOCKED_STATUS, REJECTED_STATUS}
                    and isinstance(bundle.get("issue_code"), str)
                )
            ),
            "operator release readiness bundle status is consistent",
            "operator release readiness bundle status is inconsistent",
            "hostess.issue.operator_release_readiness_bundle_status",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.execution_policy",
            bundle.get("execution_policy") == OPERATOR_RELEASE_READINESS_BUNDLE_POLICY,
            "operator release readiness bundle is schema-only",
            "operator release readiness bundle execution policy drifted",
            "hostess.issue.operator_release_readiness_bundle_execution_policy",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.sources",
            bundle.get("source_platform_smoke_evidence_review_id")
            == platform_smoke_evidence_review.get("evidence_review_id")
            and bundle.get("source_pmb_replay_validation_receipt_id")
            == pmb_replay_validation_receipt.get("receipt_id")
            and bundle.get("source_platform_smoke_evidence_review_schema")
            == PLATFORM_SMOKE_EVIDENCE_REVIEW_SCHEMA
            and bundle.get("source_pmb_replay_validation_receipt_schema")
            == PMB_REPLAY_VALIDATION_RECEIPT_SCHEMA,
            "operator release readiness bundle source artifacts match inputs",
            "operator release readiness bundle source artifacts drifted",
            "hostess.issue.operator_release_readiness_bundle_source_mismatch",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.source_readiness",
            (
                status == READY_STATUS
                and platform_smoke_evidence_review_source_ready(
                    platform_smoke_evidence_review
                )
                and pmb_replay_validation_receipt_source_ready(
                    pmb_replay_validation_receipt,
                    pmb_validation,
                )
            )
            or status in {BLOCKED_STATUS, REJECTED_STATUS},
            "operator release readiness bundle source artifacts are ready or blocked consistently",
            "operator release readiness bundle source artifacts do not match bundle status",
            "hostess.issue.operator_release_readiness_bundle_source_not_ready",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.pmb_shell_handoff_review",
            not pmb_review_required
            or status != READY_STATUS
            or (
                bundle.get("pmb_shell_handoff_review_required") is True
                and bundle.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_review
                and pmb_shell_handoff_readiness_result_summary_valid(bundle)
                and isinstance(pmb_platform_artifact, dict)
                and pmb_platform_artifact.get("artifact_status") == READY_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(
                    pmb_platform_artifact
                )
            ),
            "ready operator release bundle preserves the PMB shell handoff gate",
            "ready operator release bundle dropped or drifted the PMB shell handoff gate",
            "hostess.issue.operator_release_readiness_bundle_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.authority",
            bundle.get("bundle_owner") == HOSTESS_OWNER
            and bundle.get("artifact_owner") == HOSTESS_OWNER
            and bundle.get("platform_validation_authority") == HOSTESS_OWNER
            and bundle.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and bundle.get("runtime_authority") == MANIFOLD_OWNER
            and bundle.get("command_session_authority") == MANIFOLD_OWNER
            and bundle.get("studio_role") == STUDIO_ROLE
            and bundle.get("authoring_owner") == STUDIO_REQUESTER,
            "Hostess, Manifold, and Studio authority fields are separated",
            "operator release readiness bundle authority fields drifted",
            "hostess.issue.operator_release_readiness_bundle_authority",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.no_execution_started",
            operator_release_readiness_bundle_unstarted(bundle),
            "operator release readiness bundle has not started execution or copied payloads",
            "operator release readiness bundle indicates execution, build, copy, launch, evidence, or replay work",
            "hostess.issue.operator_release_readiness_bundle_execution_started",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.artifacts",
            operator_release_artifacts_match_contracts(
                artifacts,
                platform_smoke_evidence_review,
                pmb_replay_validation_receipt,
                pmb_validation,
                status,
            ),
            "operator release readiness bundle artifact rows match source contracts",
            "operator release readiness bundle artifact rows drifted",
            "hostess.issue.operator_release_readiness_bundle_artifact_drift",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.host_shell_targets",
            operator_release_host_shell_targets_match_contracts(
                host_shell_targets,
                status,
            ),
            "operator release readiness bundle host shell targets match contracts",
            "operator release readiness bundle host shell targets drifted",
            "hostess.issue.operator_release_readiness_bundle_host_shell_drift",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.counts",
            bundle.get("schema_artifact_count") == len(artifacts)
            and bundle.get("ready_schema_artifact_count") == len(ready_artifacts)
            and bundle.get("blocked_schema_artifact_count") == len(blocked_artifacts)
            and bundle.get("rejected_schema_artifact_count") == len(rejected_artifacts)
            and bundle.get("host_shell_readiness_target_count")
            == len(host_shell_targets)
            and bundle.get("ready_host_shell_readiness_target_count")
            == len(ready_targets)
            and bundle.get("blocked_host_shell_readiness_target_count")
            == len(blocked_targets)
            and bundle.get("rejected_host_shell_readiness_target_count")
            == len(rejected_targets),
            "operator release readiness bundle counts match nested records",
            "operator release readiness bundle counts drifted",
            "hostess.issue.operator_release_readiness_bundle_count_drift",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.scorecard",
            (
                status == READY_STATUS
                and bundle.get("scorecard_status") == PASS_STATUS
                and bundle.get("operator_release_ready") is True
                and bundle.get("ready_schema_artifact_count")
                == len(OPERATOR_RELEASE_ARTIFACT_CONTRACTS)
                and bundle.get("ready_host_shell_readiness_target_count")
                == len(OPERATOR_RELEASE_HOST_SHELL_TARGET_CONTRACTS)
            )
            or (
                status in {BLOCKED_STATUS, REJECTED_STATUS}
                and bundle.get("scorecard_status") == FAIL_STATUS
                and bundle.get("operator_release_ready") is False
            ),
            "operator release readiness scorecard matches bundle status",
            "operator release readiness scorecard drifted",
            "hostess.issue.operator_release_readiness_bundle_scorecard",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.embedded_checks",
            (
                status == READY_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status in {BLOCKED_STATUS, REJECTED_STATUS},
            "operator release readiness embedded checks match bundle status",
            "operator release readiness embedded checks do not match bundle status",
            "hostess.issue.operator_release_readiness_bundle_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": OPERATOR_RELEASE_READINESS_BUNDLE_VALIDATION_SCHEMA,
        "bundle_id": bundle.get("bundle_id"),
        "source_bundle_schema": bundle.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "pmb_shell_handoff_review_required": bundle.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": bundle.get("pmb_shell_handoff_review_ready")
        is True,
        "checks": checks,
    }


def operator_release_readiness_bundle_checks(
    platform_smoke_evidence_review: dict[str, Any],
    pmb_replay_validation_receipt: dict[str, Any],
    pmb_validation: dict[str, Any],
    artifact_rows: list[dict[str, Any]],
    host_shell_targets: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = (
        platform_smoke_evidence_review.get("pmb_shell_handoff_review_required") is True
    )
    pmb_platform_artifact = next(
        (
            row
            for row in artifact_rows
            if row.get("source_role") == "platform_smoke_evidence_review"
        ),
        None,
    )
    return [
        check(
            "hostess.check.operator_release_readiness_bundle.platform_smoke_source",
            platform_smoke_evidence_review_source_ready(platform_smoke_evidence_review),
            "platform smoke evidence review is reviewed and ready for operator bundling",
            "platform smoke evidence review is missing, rejected, or drifted",
            platform_smoke_evidence_review.get("issue_code")
            or "hostess.issue.operator_release_platform_smoke_source_not_ready",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.pmb_replay_source",
            pmb_replay_validation_receipt_source_ready(
                pmb_replay_validation_receipt,
                pmb_validation,
            ),
            "projected-motion breath replay receipt is validated and ready for operator bundling",
            "projected-motion breath replay receipt is missing, rejected, or drifted",
            pmb_replay_validation_receipt.get("issue_code")
            or pmb_validation.get("issue_code")
            or "hostess.issue.operator_release_pmb_replay_source_not_ready",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.pmb_shell_handoff_review",
            not pmb_review_required
            or status != READY_STATUS
            or (
                pmb_shell_handoff_readiness_result_summary_valid(
                    platform_smoke_evidence_review
                )
                and isinstance(pmb_platform_artifact, dict)
                and pmb_platform_artifact.get("artifact_status") == READY_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(
                    pmb_platform_artifact
                )
            ),
            "ready operator release bundle preserves the PMB shell handoff gate",
            "ready operator release bundle dropped or drifted the PMB shell handoff gate",
            "hostess.issue.operator_release_readiness_bundle_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.decision",
            decision_supported,
            "operator release readiness bundle decision is supported",
            "operator release readiness bundle decision is unsupported",
            "hostess.issue.operator_release_readiness_bundle_decision",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.artifacts",
            operator_release_artifacts_match_contracts(
                artifact_rows,
                platform_smoke_evidence_review,
                pmb_replay_validation_receipt,
                pmb_validation,
                status,
            ),
            "operator release readiness artifact rows match source contracts",
            "operator release readiness artifact rows drifted",
            "hostess.issue.operator_release_readiness_bundle_artifact_drift",
        ),
        check(
            "hostess.check.operator_release_readiness_bundle.host_shell_targets",
            operator_release_host_shell_targets_match_contracts(
                host_shell_targets,
                status,
            ),
            "operator release readiness host shell targets match contracts",
            "operator release readiness host shell targets drifted",
            "hostess.issue.operator_release_readiness_bundle_host_shell_drift",
        ),
    ]


def operator_release_artifact_rows(
    platform_smoke_evidence_review: dict[str, Any],
    pmb_replay_validation_receipt: dict[str, Any],
    pmb_validation: dict[str, Any],
    bundle_status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    sources = operator_release_source_by_role(
        platform_smoke_evidence_review,
        pmb_replay_validation_receipt,
        pmb_validation,
    )
    rows = []
    for contract in OPERATOR_RELEASE_ARTIFACT_CONTRACTS:
        source = sources[contract["source_role"]]
        source_ready = source["ready"]
        if bundle_status == REJECTED_STATUS:
            artifact_status = REJECTED_STATUS
        elif source_ready:
            artifact_status = READY_STATUS
        else:
            artifact_status = BLOCKED_STATUS
        row = {
            "artifact_row_id": f"{contract['artifact_id']}.row",
            "artifact_id": contract["artifact_id"],
            "owner": contract["owner"],
            "source_role": contract["source_role"],
            "source_artifact_id": source["source_artifact_id"],
            "source_schema": source["source_schema"],
            "expected_source_schema": contract["source_schema"],
            "source_status": source["source_status"],
            "expected_source_status": contract["expected_source_status"],
            "source_validation_status": source["source_validation_status"],
            "source_scorecard_status": source["source_scorecard_status"],
            "validation_kind": contract["validation_kind"],
            "artifact_status": artifact_status,
            "issue_code": None if artifact_status == READY_STATUS else issue_code,
            "selected_for_bundle": artifact_status == READY_STATUS,
            "schema_artifact_selected": artifact_status == READY_STATUS,
            "schema_artifact_payload_copied": False,
            "release_payload_copied": False,
            "operator_started": False,
            "host_shell_started": False,
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
            "replay_execution_started": False,
        }
        if contract["source_role"] == "platform_smoke_evidence_review":
            row["pmb_shell_handoff_review_required"] = (
                platform_smoke_evidence_review.get("pmb_shell_handoff_review_required")
                is True
            )
            row["pmb_shell_handoff_review_ready"] = (
                platform_smoke_evidence_review.get("pmb_shell_handoff_review_ready")
                is True
            )
            row.update(
                pmb_shell_handoff_review_summary_from_source(
                    platform_smoke_evidence_review
                )
            )
        rows.append(row)
    return rows


def operator_release_host_shell_targets(
    bundle_status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    target_status = (
        READY_STATUS
        if bundle_status == READY_STATUS
        else REJECTED_STATUS
        if bundle_status == REJECTED_STATUS
        else BLOCKED_STATUS
    )
    return [
        {
            "host_shell_target_id": contract["host_shell_target_id"],
            "owner": contract["owner"],
            "host_shell_kind": contract["host_shell_kind"],
            "target_kind": contract["target_kind"],
            "validation_kind": contract["validation_kind"],
            "target_status": target_status,
            "issue_code": None if target_status == READY_STATUS else issue_code,
            "operator_start_required_before_platform_work": True,
            "operator_started": False,
            "host_shell_started": False,
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
            "replay_execution_started": False,
            "release_payload_copied": False,
        }
        for contract in OPERATOR_RELEASE_HOST_SHELL_TARGET_CONTRACTS
    ]


def operator_release_artifact_dicts(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = bundle.get("schema_artifacts", [])
    if not isinstance(artifacts, list):
        return []
    return [entry for entry in artifacts if isinstance(entry, dict)]


def operator_release_host_shell_target_dicts(
    bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    targets = bundle.get("host_shell_readiness_targets", [])
    if not isinstance(targets, list):
        return []
    return [entry for entry in targets if isinstance(entry, dict)]


def operator_release_source_by_role(
    platform_smoke_evidence_review: dict[str, Any],
    pmb_replay_validation_receipt: dict[str, Any],
    pmb_validation: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        "platform_smoke_evidence_review": {
            "source_artifact_id": platform_smoke_evidence_review.get("evidence_review_id"),
            "source_schema": platform_smoke_evidence_review.get("$schema"),
            "source_status": platform_smoke_evidence_review.get("status"),
            "source_validation_status": (
                PASS_STATUS
                if platform_smoke_evidence_review_source_ready(
                    platform_smoke_evidence_review
                )
                else FAIL_STATUS
            ),
            "source_scorecard_status": platform_smoke_evidence_review.get(
                "scorecard_status"
            ),
            "ready": platform_smoke_evidence_review_source_ready(
                platform_smoke_evidence_review
            ),
        },
        "projected_motion_breath_replay_validation_receipt": {
            "source_artifact_id": pmb_replay_validation_receipt.get("receipt_id"),
            "source_schema": pmb_replay_validation_receipt.get("$schema"),
            "source_status": pmb_replay_validation_receipt.get("status"),
            "source_validation_status": pmb_validation.get("status"),
            "source_scorecard_status": pmb_replay_validation_receipt.get(
                "scorecard_status"
            ),
            "ready": pmb_replay_validation_receipt_source_ready(
                pmb_replay_validation_receipt,
                pmb_validation,
            ),
        },
    }


def operator_release_artifacts_match_contracts(
    artifacts: list[dict[str, Any]],
    platform_smoke_evidence_review: dict[str, Any],
    pmb_replay_validation_receipt: dict[str, Any],
    pmb_validation: dict[str, Any],
    bundle_status: Any,
) -> bool:
    if bundle_status not in {READY_STATUS, BLOCKED_STATUS, REJECTED_STATUS}:
        return False
    if len(artifacts) != len(OPERATOR_RELEASE_ARTIFACT_CONTRACTS):
        return False
    source_by_role = operator_release_source_by_role(
        platform_smoke_evidence_review,
        pmb_replay_validation_receipt,
        pmb_validation,
    )
    by_id = {entry.get("artifact_id"): entry for entry in artifacts}
    for contract in OPERATOR_RELEASE_ARTIFACT_CONTRACTS:
        row = by_id.get(contract["artifact_id"])
        if not isinstance(row, dict):
            return False
        source = source_by_role[contract["source_role"]]
        source_ready = source["ready"]
        expected_status = (
            REJECTED_STATUS
            if bundle_status == REJECTED_STATUS
            else READY_STATUS
            if source_ready
            else BLOCKED_STATUS
        )
        for key in ("owner", "source_role", "validation_kind"):
            if row.get(key) != contract[key]:
                return False
        if row.get("expected_source_schema") != contract["source_schema"]:
            return False
        if row.get("expected_source_status") != contract["expected_source_status"]:
            return False
        for key in (
            "source_artifact_id",
            "source_schema",
            "source_status",
            "source_validation_status",
            "source_scorecard_status",
        ):
            if row.get(key) != source[key]:
                return False
        if (
            contract["source_role"] == "platform_smoke_evidence_review"
            and bundle_status == READY_STATUS
            and platform_smoke_evidence_review.get("pmb_shell_handoff_review_required")
            is True
        ):
            if row.get("pmb_shell_handoff_review_required") is not True:
                return False
            if row.get("pmb_shell_handoff_review_ready") is not True:
                return False
            if (
                pmb_shell_handoff_review_summary_from_source(row)
                != pmb_shell_handoff_review_summary_from_source(
                    platform_smoke_evidence_review
                )
            ):
                return False
            if not pmb_shell_handoff_readiness_result_summary_valid(row):
                return False
        if row.get("artifact_status") != expected_status:
            return False
        if row.get("selected_for_bundle") != (expected_status == READY_STATUS):
            return False
        if row.get("schema_artifact_selected") != (expected_status == READY_STATUS):
            return False
        if expected_status == READY_STATUS and row.get("issue_code") is not None:
            return False
        if expected_status != READY_STATUS and not isinstance(row.get("issue_code"), str):
            return False
        if not operator_release_artifact_row_unstarted(row):
            return False
    return True


def operator_release_host_shell_targets_match_contracts(
    targets: list[dict[str, Any]],
    bundle_status: Any,
) -> bool:
    if bundle_status not in {READY_STATUS, BLOCKED_STATUS, REJECTED_STATUS}:
        return False
    if len(targets) != len(OPERATOR_RELEASE_HOST_SHELL_TARGET_CONTRACTS):
        return False
    expected_status = (
        READY_STATUS
        if bundle_status == READY_STATUS
        else REJECTED_STATUS
        if bundle_status == REJECTED_STATUS
        else BLOCKED_STATUS
    )
    by_id = {entry.get("host_shell_target_id"): entry for entry in targets}
    for contract in OPERATOR_RELEASE_HOST_SHELL_TARGET_CONTRACTS:
        target = by_id.get(contract["host_shell_target_id"])
        if not isinstance(target, dict):
            return False
        for key in ("owner", "host_shell_kind", "target_kind", "validation_kind"):
            if target.get(key) != contract[key]:
                return False
        if target.get("target_status") != expected_status:
            return False
        if target.get("operator_start_required_before_platform_work") is not True:
            return False
        if expected_status == READY_STATUS and target.get("issue_code") is not None:
            return False
        if expected_status != READY_STATUS and not isinstance(
            target.get("issue_code"),
            str,
        ):
            return False
        if not operator_release_host_shell_target_unstarted(target):
            return False
    return True


def platform_smoke_evidence_review_source_ready(
    evidence_review: dict[str, Any],
) -> bool:
    checks = evidence_review.get("checks", [])
    if not isinstance(checks, list):
        return False
    embedded_checks = [entry for entry in checks if isinstance(entry, dict)]
    return (
        evidence_review.get("$schema") == PLATFORM_SMOKE_EVIDENCE_REVIEW_SCHEMA
        and evidence_review.get("status") == REVIEWED_STATUS
        and evidence_review.get("issue_code") is None
        and evidence_review.get("scorecard_status") == PASS_STATUS
        and evidence_review.get("operator_review_ready") is True
        and evidence_review.get("missing_attachment_count") == 0
        and evidence_review.get("rejected_attachment_count") == 0
        and all(entry.get("status") == PASS_STATUS for entry in embedded_checks)
        and platform_smoke_evidence_review_unstarted(evidence_review)
    )


def pmb_replay_validation_receipt_source_ready(
    receipt: dict[str, Any],
    validation: dict[str, Any],
) -> bool:
    return (
        receipt.get("$schema") == PMB_REPLAY_VALIDATION_RECEIPT_SCHEMA
        and receipt.get("status") == VALIDATED_STATUS
        and receipt.get("issue_code") is None
        and receipt.get("scorecard_status") == PASS_STATUS
        and validation.get("status") == PASS_STATUS
        and pmb_replay_validation_receipt_unstarted(receipt)
    )


def platform_smoke_evidence_review_unstarted(evidence_review: dict[str, Any]) -> bool:
    return (
        all(evidence_review.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
        and evidence_review.get("device_required") is False
        and evidence_review.get("schema_path_execution_allowed") is False
        and evidence_review.get("platform_execution_allowed") is False
        and evidence_review.get("studio_execution_allowed") is False
        and evidence_review.get("runtime_execution_performed") is False
        and evidence_review.get("platform_execution_performed") is False
        and evidence_review.get("evidence_payloads_copied") is False
        and evidence_review.get("real_platform_execution_evidence_attached") is False
    )


def operator_release_artifact_row_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("schema_artifact_payload_copied") is False
        and row.get("release_payload_copied") is False
        and row.get("operator_started") is False
        and row.get("host_shell_started") is False
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
        and row.get("replay_execution_started") is False
    )


def operator_release_host_shell_target_unstarted(target: dict[str, Any]) -> bool:
    return (
        target.get("operator_started") is False
        and target.get("host_shell_started") is False
        and target.get("device_required") is False
        and target.get("schema_path_execution_allowed") is False
        and target.get("platform_execution_allowed") is False
        and target.get("studio_execution_allowed") is False
        and target.get("execution_started") is False
        and target.get("runtime_execution_performed") is False
        and target.get("platform_execution_performed") is False
        and target.get("build_started") is False
        and target.get("copy_started") is False
        and target.get("stage_started") is False
        and target.get("install_started") is False
        and target.get("launch_started") is False
        and target.get("evidence_collection_started") is False
        and target.get("command_session_started") is False
        and target.get("replay_execution_started") is False
        and target.get("release_payload_copied") is False
    )


from tools.studio_staging.staging_handoff import *  # re-exported facade symbols

__all__ = [
    "build_projected_motion_breath_validation_handoff",
    "validate_projected_motion_breath_validation_handoff",
    "pmb_required_package_checks",
    "int_or_zero",
    "pmb_required_package_checks_ready",
    "pmb_package_evidence_intake_matches_required_checks",
    "pmb_source_authority_preserved",
    "pmb_authority_fields_match",
    "pmb_source_adapter_selection_targets_authoring",
    "pmb_source_adapter_selection_stream_binding_supported",
    "pmb_source_adapter_selection_handoff_fields_match",
    "pmb_sources_did_not_execute",
    "pmb_validation_slots",
    "pmb_validation_slot_contracts",
    "pmb_validation_slot_dicts",
    "pmb_embedded_check_dicts",
    "pmb_validation_slots_match_contracts",
    "pmb_validation_slot_unstarted",
    "pmb_validation_handoff_unstarted",
    "build_projected_motion_breath_replay_validation_receipt",
    "validate_projected_motion_breath_replay_validation_receipt",
    "pmb_replay_receipt_id",
    "pmb_replay_descriptor_source_matches_contracts",
    "pmb_replay_descriptor_rows",
    "pmb_replay_source_descriptor_by_id",
    "pmb_replay_descriptor_dicts",
    "pmb_replay_descriptors_match_contracts",
    "pmb_replay_descriptor_unstarted",
    "pmb_replay_validation_receipt_unstarted",
    "build_operator_release_readiness_bundle",
    "validate_operator_release_readiness_bundle",
    "operator_release_readiness_bundle_checks",
    "operator_release_artifact_rows",
    "operator_release_host_shell_targets",
    "operator_release_artifact_dicts",
    "operator_release_host_shell_target_dicts",
    "operator_release_source_by_role",
    "operator_release_artifacts_match_contracts",
    "operator_release_host_shell_targets_match_contracts",
    "platform_smoke_evidence_review_source_ready",
    "pmb_replay_validation_receipt_source_ready",
    "platform_smoke_evidence_review_unstarted",
    "operator_release_artifact_row_unstarted",
    "operator_release_host_shell_target_unstarted",
]
