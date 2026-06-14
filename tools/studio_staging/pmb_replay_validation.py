"""Projected-motion breath replay validation receipts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.pmb_validation_handoff import *  # validation handoff helpers

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
