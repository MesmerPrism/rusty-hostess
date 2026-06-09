from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.studio_staging.manifold_handoff_intake import (
    ACCEPTED_STATUS,
    FAIL_STATUS,
    HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_SCHEMA,
    HOSTESS_OWNER,
    MANIFOLD_OWNER,
    MANIFOLD_SHELL_HANDOFF_SCHEMA,
    PASS_STATUS,
    REJECTED_STATUS,
    REVIEWED_STATUS,
    STUDIO_REQUESTER,
    STUDIO_ROLE,
    _check,
)

HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA = (
    "rusty.hostess.makepad_shell_contract_receipt.v1"
)
HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.makepad_shell_contract_receipt_validation.v1"
)
HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_POLICY = (
    "hostess.makepad_shell_contract_schema_only"
)
HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_SCHEMA = (
    "rusty.hostess.makepad_shell_launch_handoff_receipt.v1"
)
HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.makepad_shell_launch_handoff_receipt_validation.v1"
)
HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_POLICY = (
    "hostess.makepad_shell_launch_handoff_schema_only"
)
READY_STATUS = "ready"


def hostess_makepad_shell_contract_source_ready(
    intake_receipt: dict[str, Any],
) -> bool:
    return (
        intake_receipt.get("$schema")
        == HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_SCHEMA
        and intake_receipt.get("status") == REVIEWED_STATUS
        and intake_receipt.get("issue_code") is None
        and intake_receipt.get("selected_handoff_schema") == MANIFOLD_SHELL_HANDOFF_SCHEMA
        and isinstance(intake_receipt.get("selected_handoff_id"), str)
        and isinstance(intake_receipt.get("selected_shell_app_id"), str)
        and intake_receipt.get("manifold_review_status") == PASS_STATUS
        and intake_receipt.get("manifold_shell_handoff_selected") is True
        and intake_receipt.get("makepad_shell_descriptor_selected") is False
        and intake_receipt.get("manifold_shell_handoff_reviewed") is True
        and intake_receipt.get("manifold_shell_handoff_review_ready") is True
        and intake_receipt.get("legacy_reference_dependency_used") is False
        and hostess_makepad_shell_contract_intake_no_runtime_started(intake_receipt)
    )


def build_hostess_makepad_shell_contract_receipt(
    intake_receipt: dict[str, Any],
    source_intake_receipt_path: Path | None = None,
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    source_ready = hostess_makepad_shell_contract_source_ready(intake_receipt)
    accepted = decision == ACCEPTED_STATUS and decision_supported and source_ready
    status = ACCEPTED_STATUS if accepted else REJECTED_STATUS
    issue_code = None
    if status != ACCEPTED_STATUS:
        issue_code = (
            reason_code
            or intake_receipt.get("issue_code")
            or (
                "hostess.issue.hostess_makepad_shell_contract_decision"
                if not decision_supported
                else "hostess.issue.hostess_makepad_shell_contract_source_not_ready"
            )
        )
    checks = hostess_makepad_shell_contract_receipt_checks(
        intake_receipt,
        status,
        decision_supported,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == ACCEPTED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        accepted = False
    receipt_id = (
        "hostess.makepad_shell_contract_receipt."
        f"{intake_receipt.get('receipt_id')}"
        if isinstance(intake_receipt.get("receipt_id"), str)
        and intake_receipt.get("receipt_id")
        else "hostess.makepad_shell_contract_receipt.unknown"
    )
    reviewed_stream_ids = intake_receipt.get("reviewed_stream_ids", [])
    reviewed_command_ids = intake_receipt.get("reviewed_command_ids", [])
    reviewed_transport_ids = intake_receipt.get("reviewed_transport_ids", [])
    reviewed_endpoint_ids = intake_receipt.get("reviewed_endpoint_ids", [])
    return {
        "$schema": HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_manifold_shell_handoff_review_intake_receipt_id": (
            intake_receipt.get("receipt_id")
        ),
        "source_manifold_shell_handoff_review_intake_receipt_schema": (
            intake_receipt.get("$schema")
        ),
        "source_manifold_shell_handoff_review_intake_receipt_status": (
            intake_receipt.get("status")
        ),
        "source_manifold_shell_handoff_review_intake_receipt_path": (
            str(source_intake_receipt_path)
            if source_intake_receipt_path is not None
            else None
        ),
        "source_selected_payload_path": intake_receipt.get(
            "source_selected_payload_path"
        ),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "handoff_intake_owner": HOSTESS_OWNER,
        "shell_contract_authority": MANIFOLD_OWNER,
        "handoff_review_authority": MANIFOLD_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "makepad_role": "downstream_shell.contract_consumer",
        "makepad_contract_input_accepted": accepted,
        "makepad_shell_contract_ready": accepted,
        "makepad_shell_descriptor_selected": (
            intake_receipt.get("makepad_shell_descriptor_selected") is True
        ),
        "descriptor_fallback_used": (
            intake_receipt.get("makepad_shell_descriptor_selected") is True
        ),
        "manifold_shell_handoff_selected": (
            intake_receipt.get("manifold_shell_handoff_selected") is True
        ),
        "manifold_shell_handoff_review_ready": (
            intake_receipt.get("manifold_shell_handoff_review_ready") is True
        ),
        "selected_handoff_schema": intake_receipt.get("selected_handoff_schema"),
        "selected_handoff_id": intake_receipt.get("selected_handoff_id"),
        "selected_handoff_revision": intake_receipt.get(
            "selected_handoff_revision"
        ),
        "selected_target_host_profile": intake_receipt.get(
            "selected_target_host_profile"
        ),
        "selected_shell_app_id": intake_receipt.get("selected_shell_app_id"),
        "selected_validation_slot_id": intake_receipt.get(
            "selected_validation_slot_id"
        ),
        "manifold_review_schema": intake_receipt.get("manifold_review_schema"),
        "manifold_review_id": intake_receipt.get("manifold_review_id"),
        "manifold_review_handoff_id": intake_receipt.get(
            "manifold_review_handoff_id"
        ),
        "manifold_review_status": intake_receipt.get("manifold_review_status"),
        "reviewed_stream_ids": (
            reviewed_stream_ids if isinstance(reviewed_stream_ids, list) else []
        ),
        "reviewed_command_ids": (
            reviewed_command_ids if isinstance(reviewed_command_ids, list) else []
        ),
        "reviewed_transport_ids": (
            reviewed_transport_ids if isinstance(reviewed_transport_ids, list) else []
        ),
        "reviewed_endpoint_ids": (
            reviewed_endpoint_ids if isinstance(reviewed_endpoint_ids, list) else []
        ),
        "reviewed_stream_count": (
            len(reviewed_stream_ids) if isinstance(reviewed_stream_ids, list) else 0
        ),
        "reviewed_command_count": (
            len(reviewed_command_ids) if isinstance(reviewed_command_ids, list) else 0
        ),
        "reviewed_transport_count": (
            len(reviewed_transport_ids)
            if isinstance(reviewed_transport_ids, list)
            else 0
        ),
        "reviewed_endpoint_count": (
            len(reviewed_endpoint_ids)
            if isinstance(reviewed_endpoint_ids, list)
            else 0
        ),
        "legacy_reference_dependency_used": False,
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
        "makepad_runtime_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "schema_artifact_payloads_copied": False,
        "release_payloads_copied": False,
        "staging_payloads_copied": False,
        "file_copy_performed": False,
        "pmb_shell_handoff_review_required": (
            intake_receipt.get("pmb_shell_handoff_review_required") is True
        ),
        "pmb_shell_handoff_review_ready": (
            intake_receipt.get("pmb_shell_handoff_review_ready") is True
        ),
        "checks": checks,
        "next_required_action": (
            "makepad_read_reviewed_manifold_shell_contract_without_launch"
            if accepted
            else "repair_or_decline_makepad_shell_contract_input"
        ),
    }


def validate_hostess_makepad_shell_contract_receipt(
    intake_receipt: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    status = receipt.get("status")
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [
        entry for entry in embedded_checks if isinstance(entry, dict)
    ]
    embedded_failed = [
        entry for entry in embedded_check_dicts if entry.get("status") == FAIL_STATUS
    ]
    source_ready = hostess_makepad_shell_contract_source_ready(intake_receipt)
    checks = [
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.schema",
            receipt.get("$schema") == HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA,
            "Hostess Makepad shell contract receipt schema is supported",
            "Hostess Makepad shell contract receipt schema is unsupported",
            "hostess.issue.hostess_makepad_shell_contract_receipt_schema",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.status",
            status in {ACCEPTED_STATUS, REJECTED_STATUS}
            and (
                (status == ACCEPTED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess Makepad shell contract receipt status is consistent",
            "Hostess Makepad shell contract receipt status is inconsistent",
            "hostess.issue.hostess_makepad_shell_contract_receipt_status",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.sources",
            receipt.get("source_manifold_shell_handoff_review_intake_receipt_id")
            == intake_receipt.get("receipt_id")
            and receipt.get(
                "source_manifold_shell_handoff_review_intake_receipt_schema"
            )
            == HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_SCHEMA
            and receipt.get("source_selected_payload_path")
            == intake_receipt.get("source_selected_payload_path"),
            "Hostess Makepad shell contract sources match intake",
            "Hostess Makepad shell contract sources drifted",
            "hostess.issue.hostess_makepad_shell_contract_source_mismatch",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.source_readiness",
            (status == ACCEPTED_STATUS and source_ready) or status == REJECTED_STATUS,
            "Reviewed Manifold shell handoff intake is ready for Makepad consumption",
            "Reviewed Manifold shell handoff intake is not ready for Makepad consumption",
            "hostess.issue.hostess_makepad_shell_contract_source_not_ready",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("handoff_intake_owner") == HOSTESS_OWNER
            and receipt.get("shell_contract_authority") == MANIFOLD_OWNER
            and receipt.get("handoff_review_authority") == MANIFOLD_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess records Makepad contract intake while Manifold owns shell contract authority",
            "Hostess Makepad shell contract authority fields drifted",
            "hostess.issue.hostess_makepad_shell_contract_authority",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.contract_linkage",
            (
                status == ACCEPTED_STATUS
                and receipt.get("makepad_contract_input_accepted") is True
                and receipt.get("makepad_shell_contract_ready") is True
                and receipt.get("descriptor_fallback_used") is False
                and receipt.get("manifold_shell_handoff_selected") is True
                and receipt.get("manifold_shell_handoff_review_ready") is True
                and receipt.get("selected_handoff_schema")
                == MANIFOLD_SHELL_HANDOFF_SCHEMA
                and receipt.get("selected_handoff_id")
                == intake_receipt.get("selected_handoff_id")
                and receipt.get("selected_shell_app_id")
                == intake_receipt.get("selected_shell_app_id")
                and receipt.get("manifold_review_handoff_id")
                == intake_receipt.get("selected_handoff_id")
                and receipt.get("manifold_review_status") == PASS_STATUS
                and receipt.get("reviewed_stream_ids")
                == intake_receipt.get("reviewed_stream_ids")
                and receipt.get("reviewed_command_ids")
                == intake_receipt.get("reviewed_command_ids")
                and receipt.get("reviewed_transport_ids")
                == intake_receipt.get("reviewed_transport_ids")
                and receipt.get("reviewed_endpoint_ids")
                == intake_receipt.get("reviewed_endpoint_ids")
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("makepad_contract_input_accepted") is False
                and receipt.get("makepad_shell_contract_ready") is False
            ),
            "Makepad shell contract receipt links to the reviewed Manifold handoff",
            "Makepad shell contract receipt linkage drifted",
            "hostess.issue.hostess_makepad_shell_contract_linkage_drift",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.no_runtime_started",
            hostess_makepad_shell_contract_receipt_no_runtime_started(receipt),
            "Hostess Makepad shell contract receipt did not start runtime, platform, launch, or command-session work",
            "Hostess Makepad shell contract receipt indicates runtime, platform, launch, or command-session work",
            "hostess.issue.hostess_makepad_shell_contract_runtime_started",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.counts",
            receipt.get("reviewed_stream_count")
            == len(receipt.get("reviewed_stream_ids", []))
            and receipt.get("reviewed_command_count")
            == len(receipt.get("reviewed_command_ids", []))
            and receipt.get("reviewed_transport_count")
            == len(receipt.get("reviewed_transport_ids", []))
            and receipt.get("reviewed_endpoint_count")
            == len(receipt.get("reviewed_endpoint_ids", [])),
            "Hostess Makepad shell contract counts match nested ids",
            "Hostess Makepad shell contract counts drifted",
            "hostess.issue.hostess_makepad_shell_contract_count_drift",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.embedded_checks",
            (
                status == ACCEPTED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess Makepad shell contract embedded checks match receipt status",
            "Hostess Makepad shell contract embedded checks do not match receipt status",
            "hostess.issue.hostess_makepad_shell_contract_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "launch_started": False,
        "command_session_started": False,
        "makepad_shell_contract_ready": receipt.get(
            "makepad_shell_contract_ready"
        )
        is True,
        "descriptor_fallback_used": receipt.get("descriptor_fallback_used") is True,
        "checks": checks,
    }


def hostess_makepad_shell_launch_handoff_source_ready(
    contract_receipt: dict[str, Any],
) -> bool:
    return (
        contract_receipt.get("$schema")
        == HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA
        and contract_receipt.get("status") == ACCEPTED_STATUS
        and contract_receipt.get("issue_code") is None
        and contract_receipt.get("makepad_contract_input_accepted") is True
        and contract_receipt.get("makepad_shell_contract_ready") is True
        and contract_receipt.get("descriptor_fallback_used") is False
        and contract_receipt.get("manifold_shell_handoff_selected") is True
        and contract_receipt.get("manifold_shell_handoff_review_ready") is True
        and contract_receipt.get("legacy_reference_dependency_used") is False
        and hostess_makepad_shell_contract_receipt_no_runtime_started(
            contract_receipt
        )
    )


def build_hostess_makepad_shell_launch_handoff_receipt(
    contract_receipt: dict[str, Any],
    source_contract_receipt_path: Path | None = None,
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    source_ready = hostess_makepad_shell_launch_handoff_source_ready(
        contract_receipt
    )
    ready = decision == ACCEPTED_STATUS and decision_supported and source_ready
    status = READY_STATUS if ready else REJECTED_STATUS
    issue_code = None
    if status != READY_STATUS:
        issue_code = (
            reason_code
            or contract_receipt.get("issue_code")
            or (
                "hostess.issue.hostess_makepad_shell_launch_handoff_decision"
                if not decision_supported
                else "hostess.issue.hostess_makepad_shell_launch_handoff_source_not_ready"
            )
        )
    checks = hostess_makepad_shell_launch_handoff_receipt_checks(
        contract_receipt,
        status,
        decision_supported,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == READY_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        ready = False
    receipt_id = (
        "hostess.makepad_shell_launch_handoff_receipt."
        f"{contract_receipt.get('receipt_id')}"
        if isinstance(contract_receipt.get("receipt_id"), str)
        and contract_receipt.get("receipt_id")
        else "hostess.makepad_shell_launch_handoff_receipt.unknown"
    )
    reviewed_stream_ids = contract_receipt.get("reviewed_stream_ids", [])
    reviewed_command_ids = contract_receipt.get("reviewed_command_ids", [])
    reviewed_transport_ids = contract_receipt.get("reviewed_transport_ids", [])
    reviewed_endpoint_ids = contract_receipt.get("reviewed_endpoint_ids", [])
    source_path = (
        str(source_contract_receipt_path)
        if source_contract_receipt_path is not None
        else None
    )
    return {
        "$schema": HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_makepad_shell_contract_receipt_id": (
            contract_receipt.get("receipt_id")
        ),
        "source_makepad_shell_contract_receipt_schema": (
            contract_receipt.get("$schema")
        ),
        "source_makepad_shell_contract_receipt_status": (
            contract_receipt.get("status")
        ),
        "source_makepad_shell_contract_receipt_path": source_path,
        "source_manifold_shell_handoff_review_intake_receipt_id": (
            contract_receipt.get(
                "source_manifold_shell_handoff_review_intake_receipt_id"
            )
        ),
        "source_manifold_shell_handoff_review_intake_receipt_path": (
            contract_receipt.get(
                "source_manifold_shell_handoff_review_intake_receipt_path"
            )
        ),
        "source_selected_payload_path": contract_receipt.get(
            "source_selected_payload_path"
        ),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "launch_owner": HOSTESS_OWNER,
        "contract_receipt_owner": contract_receipt.get("receipt_owner"),
        "shell_contract_authority": MANIFOLD_OWNER,
        "handoff_review_authority": MANIFOLD_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "install_launch_evidence_authority": HOSTESS_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "makepad_role": "downstream_shell.launch_candidate",
        "makepad_contract_reader_required": ready,
        "makepad_contract_reader_ready": ready,
        "makepad_contract_reader_input_path": source_path,
        "makepad_launch_handoff_ready": ready,
        "makepad_launch_request_ready": ready,
        "makepad_launch_route_kind": "hostess.makepad.launch_from_contract",
        "expected_reader_contract_schema": (
            HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA
        ),
        "descriptor_fallback_allowed": False,
        "descriptor_fallback_used": (
            contract_receipt.get("descriptor_fallback_used") is True
        ),
        "legacy_reference_dependency_allowed": False,
        "legacy_reference_dependency_used": False,
        "manifold_shell_handoff_selected": (
            contract_receipt.get("manifold_shell_handoff_selected") is True
        ),
        "manifold_shell_handoff_review_ready": (
            contract_receipt.get("manifold_shell_handoff_review_ready") is True
        ),
        "selected_handoff_schema": contract_receipt.get("selected_handoff_schema"),
        "selected_handoff_id": contract_receipt.get("selected_handoff_id"),
        "selected_handoff_revision": contract_receipt.get(
            "selected_handoff_revision"
        ),
        "selected_target_host_profile": contract_receipt.get(
            "selected_target_host_profile"
        ),
        "selected_shell_app_id": contract_receipt.get("selected_shell_app_id"),
        "selected_validation_slot_id": contract_receipt.get(
            "selected_validation_slot_id"
        ),
        "manifold_review_schema": contract_receipt.get("manifold_review_schema"),
        "manifold_review_id": contract_receipt.get("manifold_review_id"),
        "manifold_review_handoff_id": contract_receipt.get(
            "manifold_review_handoff_id"
        ),
        "manifold_review_status": contract_receipt.get("manifold_review_status"),
        "reviewed_stream_ids": (
            reviewed_stream_ids if isinstance(reviewed_stream_ids, list) else []
        ),
        "reviewed_command_ids": (
            reviewed_command_ids if isinstance(reviewed_command_ids, list) else []
        ),
        "reviewed_transport_ids": (
            reviewed_transport_ids if isinstance(reviewed_transport_ids, list) else []
        ),
        "reviewed_endpoint_ids": (
            reviewed_endpoint_ids if isinstance(reviewed_endpoint_ids, list) else []
        ),
        "reviewed_stream_count": (
            len(reviewed_stream_ids) if isinstance(reviewed_stream_ids, list) else 0
        ),
        "reviewed_command_count": (
            len(reviewed_command_ids) if isinstance(reviewed_command_ids, list) else 0
        ),
        "reviewed_transport_count": (
            len(reviewed_transport_ids)
            if isinstance(reviewed_transport_ids, list)
            else 0
        ),
        "reviewed_endpoint_count": (
            len(reviewed_endpoint_ids)
            if isinstance(reviewed_endpoint_ids, list)
            else 0
        ),
        "pmb_shell_handoff_review_required": (
            contract_receipt.get("pmb_shell_handoff_review_required") is True
        ),
        "pmb_shell_handoff_review_ready": (
            contract_receipt.get("pmb_shell_handoff_review_ready") is True
        ),
        "device_required": False,
        "target_device_required_for_future_execution": False,
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
        "makepad_runtime_started": False,
        "makepad_contract_read_started": False,
        "evidence_collection_started": False,
        "command_session_started": False,
        "schema_artifact_payloads_copied": False,
        "release_payloads_copied": False,
        "staging_payloads_copied": False,
        "file_copy_performed": False,
        "checks": checks,
        "next_required_action": (
            "hostess_launch_makepad_from_contract_after_operator_approval"
            if ready
            else "repair_or_decline_makepad_launch_handoff_input"
        ),
    }


def validate_hostess_makepad_shell_launch_handoff_receipt(
    contract_receipt: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    status = receipt.get("status")
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [
        entry for entry in embedded_checks if isinstance(entry, dict)
    ]
    embedded_failed = [
        entry for entry in embedded_check_dicts if entry.get("status") == FAIL_STATUS
    ]
    source_ready = hostess_makepad_shell_launch_handoff_source_ready(
        contract_receipt
    )
    checks = [
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.schema",
            receipt.get("$schema")
            == HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_SCHEMA,
            "Hostess Makepad shell launch handoff receipt schema is supported",
            "Hostess Makepad shell launch handoff receipt schema is unsupported",
            "hostess.issue.hostess_makepad_shell_launch_handoff_receipt_schema",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.status",
            status in {READY_STATUS, REJECTED_STATUS}
            and (
                (status == READY_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess Makepad shell launch handoff status is consistent",
            "Hostess Makepad shell launch handoff status is inconsistent",
            "hostess.issue.hostess_makepad_shell_launch_handoff_status",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.sources",
            receipt.get("source_makepad_shell_contract_receipt_id")
            == contract_receipt.get("receipt_id")
            and receipt.get("source_makepad_shell_contract_receipt_schema")
            == HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA
            and receipt.get("source_selected_payload_path")
            == contract_receipt.get("source_selected_payload_path"),
            "Hostess Makepad launch handoff sources match the contract receipt",
            "Hostess Makepad launch handoff sources drifted",
            "hostess.issue.hostess_makepad_shell_launch_handoff_source_mismatch",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.source_readiness",
            (status == READY_STATUS and source_ready) or status == REJECTED_STATUS,
            "Accepted Makepad shell contract is ready for launch handoff",
            "Accepted Makepad shell contract is not ready for launch handoff",
            "hostess.issue.hostess_makepad_shell_launch_handoff_source_not_ready",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("launch_owner") == HOSTESS_OWNER
            and receipt.get("shell_contract_authority") == MANIFOLD_OWNER
            and receipt.get("handoff_review_authority") == MANIFOLD_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess owns launch handoff while Manifold owns shell contract/session authority",
            "Hostess Makepad launch handoff authority fields drifted",
            "hostess.issue.hostess_makepad_shell_launch_handoff_authority",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.reader_linkage",
            (
                status == READY_STATUS
                and receipt.get("makepad_contract_reader_required") is True
                and receipt.get("makepad_contract_reader_ready") is True
                and receipt.get("makepad_launch_handoff_ready") is True
                and receipt.get("makepad_launch_request_ready") is True
                and receipt.get("expected_reader_contract_schema")
                == HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA
                and receipt.get("descriptor_fallback_allowed") is False
                and receipt.get("descriptor_fallback_used") is False
                and receipt.get("legacy_reference_dependency_allowed") is False
                and receipt.get("legacy_reference_dependency_used") is False
                and receipt.get("selected_handoff_id")
                == contract_receipt.get("selected_handoff_id")
                and receipt.get("selected_shell_app_id")
                == contract_receipt.get("selected_shell_app_id")
                and receipt.get("manifold_review_handoff_id")
                == contract_receipt.get("selected_handoff_id")
                and receipt.get("manifold_review_status") == PASS_STATUS
                and receipt.get("reviewed_stream_ids")
                == contract_receipt.get("reviewed_stream_ids")
                and receipt.get("reviewed_command_ids")
                == contract_receipt.get("reviewed_command_ids")
                and receipt.get("reviewed_transport_ids")
                == contract_receipt.get("reviewed_transport_ids")
                and receipt.get("reviewed_endpoint_ids")
                == contract_receipt.get("reviewed_endpoint_ids")
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("makepad_contract_reader_required") is False
                and receipt.get("makepad_launch_handoff_ready") is False
                and receipt.get("makepad_launch_request_ready") is False
            ),
            "Makepad launch handoff links to the accepted Hostess contract receipt",
            "Makepad launch handoff linkage drifted",
            "hostess.issue.hostess_makepad_shell_launch_handoff_linkage_drift",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.no_runtime_started",
            hostess_makepad_shell_launch_handoff_receipt_no_runtime_started(
                receipt
            ),
            "Hostess Makepad launch handoff did not start runtime, platform, launch, or command-session work",
            "Hostess Makepad launch handoff indicates runtime, platform, launch, or command-session work",
            "hostess.issue.hostess_makepad_shell_launch_handoff_runtime_started",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.counts",
            receipt.get("reviewed_stream_count")
            == len(receipt.get("reviewed_stream_ids", []))
            and receipt.get("reviewed_command_count")
            == len(receipt.get("reviewed_command_ids", []))
            and receipt.get("reviewed_transport_count")
            == len(receipt.get("reviewed_transport_ids", []))
            and receipt.get("reviewed_endpoint_count")
            == len(receipt.get("reviewed_endpoint_ids", [])),
            "Hostess Makepad launch handoff counts match nested ids",
            "Hostess Makepad launch handoff counts drifted",
            "hostess.issue.hostess_makepad_shell_launch_handoff_count_drift",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.embedded_checks",
            (
                status == READY_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess Makepad launch handoff embedded checks match receipt status",
            "Hostess Makepad launch handoff embedded checks do not match receipt status",
            "hostess.issue.hostess_makepad_shell_launch_handoff_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_VALIDATION_SCHEMA,
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "launch_started": False,
        "command_session_started": False,
        "makepad_contract_reader_ready": receipt.get(
            "makepad_contract_reader_ready"
        )
        is True,
        "makepad_launch_handoff_ready": receipt.get(
            "makepad_launch_handoff_ready"
        )
        is True,
        "descriptor_fallback_used": receipt.get("descriptor_fallback_used") is True,
        "legacy_reference_dependency_used": (
            receipt.get("legacy_reference_dependency_used") is True
        ),
        "checks": checks,
    }


def hostess_makepad_shell_launch_handoff_receipt_checks(
    contract_receipt: dict[str, Any],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    source_ready = hostess_makepad_shell_launch_handoff_source_ready(
        contract_receipt
    )
    return [
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.contract_source",
            status != READY_STATUS
            or (
                contract_receipt.get("$schema")
                == HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA
                and contract_receipt.get("status") == ACCEPTED_STATUS
                and contract_receipt.get("makepad_shell_contract_ready") is True
            ),
            "Hostess Makepad shell contract is accepted and ready",
            "Hostess Makepad shell contract is not accepted and ready",
            "hostess.issue.hostess_makepad_shell_launch_handoff_contract_source",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.clean_source",
            status != READY_STATUS
            or (
                contract_receipt.get("descriptor_fallback_used") is False
                and contract_receipt.get("legacy_reference_dependency_used")
                is False
                and contract_receipt.get("manifold_shell_handoff_selected") is True
            ),
            "Makepad launch handoff source is the reviewed Manifold handoff contract",
            "Makepad launch handoff source uses descriptor fallback or legacy dependency",
            "hostess.issue.hostess_makepad_shell_launch_handoff_source",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.source_ready",
            status != READY_STATUS or source_ready,
            "Makepad launch handoff source is ready",
            "Makepad launch handoff source is not ready",
            "hostess.issue.hostess_makepad_shell_launch_handoff_source_not_ready",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_launch_handoff_receipt.decision",
            decision_supported,
            "Hostess Makepad launch handoff decision is supported",
            "Hostess Makepad launch handoff decision is unsupported",
            "hostess.issue.hostess_makepad_shell_launch_handoff_decision",
        ),
    ]


def hostess_makepad_shell_contract_receipt_checks(
    intake_receipt: dict[str, Any],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    source_ready = hostess_makepad_shell_contract_source_ready(intake_receipt)
    return [
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.intake_source",
            status != ACCEPTED_STATUS
            or (
                intake_receipt.get("$schema")
                == HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_SCHEMA
                and intake_receipt.get("status") == REVIEWED_STATUS
                and intake_receipt.get("manifold_shell_handoff_review_ready") is True
            ),
            "Hostess Manifold shell handoff review intake is reviewed and ready",
            "Hostess Manifold shell handoff review intake is not reviewed and ready",
            "hostess.issue.hostess_makepad_shell_contract_intake_source",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.contract_source",
            status != ACCEPTED_STATUS
            or (
                intake_receipt.get("selected_handoff_schema")
                == MANIFOLD_SHELL_HANDOFF_SCHEMA
                and intake_receipt.get("makepad_shell_descriptor_selected") is False
                and intake_receipt.get("legacy_reference_dependency_used") is False
            ),
            "Makepad contract source is the reviewed Manifold shell handoff",
            "Makepad contract source is not the reviewed Manifold shell handoff",
            "hostess.issue.hostess_makepad_shell_contract_source",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.source_ready",
            status != ACCEPTED_STATUS or source_ready,
            "Makepad shell contract source is ready",
            "Makepad shell contract source is not ready",
            "hostess.issue.hostess_makepad_shell_contract_source_not_ready",
        ),
        _check(
            "hostess.check.hostess_makepad_shell_contract_receipt.decision",
            decision_supported,
            "Hostess Makepad shell contract decision is supported",
            "Hostess Makepad shell contract decision is unsupported",
            "hostess.issue.hostess_makepad_shell_contract_decision",
        ),
    ]


def hostess_makepad_shell_contract_intake_no_runtime_started(
    intake_receipt: dict[str, Any],
) -> bool:
    return (
        intake_receipt.get("legacy_reference_dependency_used") is False
        and intake_receipt.get("downstream_shell_runtime_started") is False
        and intake_receipt.get("device_required") is False
        and intake_receipt.get("schema_path_execution_allowed") is False
        and intake_receipt.get("platform_execution_allowed") is False
        and intake_receipt.get("studio_execution_allowed") is False
        and intake_receipt.get("execution_performed") is False
        and intake_receipt.get("runtime_execution_performed") is False
        and intake_receipt.get("platform_execution_performed") is False
        and intake_receipt.get("build_started") is False
        and intake_receipt.get("copy_started") is False
        and intake_receipt.get("stage_started") is False
        and intake_receipt.get("install_started") is False
        and intake_receipt.get("launch_started") is False
        and intake_receipt.get("evidence_collection_started") is False
        and intake_receipt.get("command_session_started") is False
    )


def hostess_makepad_shell_contract_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("legacy_reference_dependency_used") is False
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
        and receipt.get("makepad_runtime_started") is False
        and receipt.get("evidence_collection_started") is False
        and receipt.get("command_session_started") is False
        and receipt.get("schema_artifact_payloads_copied") is False
        and receipt.get("release_payloads_copied") is False
        and receipt.get("staging_payloads_copied") is False
        and receipt.get("file_copy_performed") is False
    )


def hostess_makepad_shell_launch_handoff_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("legacy_reference_dependency_used") is False
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
        and receipt.get("makepad_runtime_started") is False
        and receipt.get("makepad_contract_read_started") is False
        and receipt.get("evidence_collection_started") is False
        and receipt.get("command_session_started") is False
        and receipt.get("schema_artifact_payloads_copied") is False
        and receipt.get("release_payloads_copied") is False
        and receipt.get("staging_payloads_copied") is False
        and receipt.get("file_copy_performed") is False
    )
