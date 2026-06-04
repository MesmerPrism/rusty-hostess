from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA = (
    "rusty.hostess.downstream_shell_selection_receipt.v1"
)
HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_SCHEMA = (
    "rusty.hostess.manifold_shell_handoff_review_intake_receipt.v1"
)
HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.manifold_shell_handoff_review_intake_receipt_validation.v1"
)
MANIFOLD_SHELL_HANDOFF_SCHEMA = "rusty.manifold.shell.handoff.v1"
MANIFOLD_SHELL_HANDOFF_REVIEW_RECEIPT_SCHEMA = (
    "rusty.manifold.shell.handoff_review_receipt.v1"
)
HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_POLICY = (
    "hostess.manifold_shell_handoff_review_intake_schema_only"
)
MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND = "manifold_shell_handoff"

ACCEPTED_STATUS = "accepted"
REJECTED_STATUS = "rejected"
REVIEWED_STATUS = "reviewed"
SELECTED_STATUS = "selected"
PASS_STATUS = "pass"
FAIL_STATUS = "fail"

HOSTESS_OWNER = "rusty.hostess"
MANIFOLD_OWNER = "rusty.manifold"
STUDIO_REQUESTER = "rusty.studio"
STUDIO_ROLE = "authoring.export_planning"

PMB_SHELL_HANDOFF_REVIEW_SUMMARY_KEYS = (
    "source_pmb_shell_handoff_review_path",
    "source_pmb_shell_handoff_review_schema",
    "source_pmb_shell_handoff_review_status",
    "source_pmb_shell_handoff_review_issue_code",
    "source_pmb_shell_handoff_id",
    "source_pmb_shell_app_id",
    "source_pmb_runtime_authority",
    "source_pmb_authoring_authority",
    "source_pmb_platform_validation_authority",
    "source_pmb_execution_policy",
    "source_pmb_runtime_execution_performed",
    "source_pmb_platform_execution_performed",
    "source_pmb_broker_transport_used",
    "source_pmb_downstream_shell_runtime_used",
    "source_pmb_legacy_app_dependency_used",
    "source_pmb_required_binding_count",
    "source_pmb_ready_required_binding_count",
    "source_pmb_feedback_receipt_exported",
    "source_pmb_feedback_sink_provides_receipt",
    "source_pmb_command_ids",
    "source_pmb_transport_ids",
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _check(
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


def pmb_shell_handoff_review_summary_from_source(
    source: dict[str, Any],
) -> dict[str, Any]:
    return {key: source.get(key) for key in PMB_SHELL_HANDOFF_REVIEW_SUMMARY_KEYS}


def manifold_shell_handoff_stream_ids(handoff: dict[str, Any]) -> list[Any]:
    bindings = handoff.get("stream_bindings", [])
    if not isinstance(bindings, list):
        return []
    return [
        binding.get("stream_id")
        for binding in bindings
        if isinstance(binding, dict) and isinstance(binding.get("stream_id"), str)
    ]


def manifold_shell_handoff_transport_ids(handoff: dict[str, Any]) -> list[Any]:
    offers = handoff.get("transport_offers", [])
    if not isinstance(offers, list):
        return []
    return [
        offer.get("transport_id")
        for offer in offers
        if isinstance(offer, dict) and isinstance(offer.get("transport_id"), str)
    ]


def manifold_shell_handoff_endpoint_ids(handoff: dict[str, Any]) -> list[Any]:
    offers = handoff.get("transport_offers", [])
    if not isinstance(offers, list):
        return []
    return [
        offer.get("endpoint_id")
        for offer in offers
        if isinstance(offer, dict) and isinstance(offer.get("endpoint_id"), str)
    ]


def selected_manifold_shell_handoff_from_selection(
    downstream_shell_selection_receipt: dict[str, Any],
) -> dict[str, Any]:
    selected_path = downstream_shell_selection_receipt.get("selected_payload_path")
    if not isinstance(selected_path, str) or not selected_path:
        return {}
    path = Path(selected_path)
    if not path.exists():
        return {}
    return _load_json(path)


def manifold_shell_handoff_review_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("launch_started") is False
        and receipt.get("command_session_started") is False
        and receipt.get("legacy_app_dependency_used") is False
    )


def _hostess_downstream_shell_selection_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("legacy_rusty_xr_dependency_used") is False
        and receipt.get("downstream_shell_runtime_started") is False
        and receipt.get("schema_path_execution_allowed") is False
        and receipt.get("platform_execution_allowed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("execution_performed") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("copy_started") is False
        and receipt.get("install_started") is False
        and receipt.get("launch_started") is False
        and receipt.get("evidence_collection_started") is False
        and receipt.get("command_session_started") is False
        and receipt.get("schema_artifact_payloads_copied") is False
        and receipt.get("release_payloads_copied") is False
        and receipt.get("staging_payloads_copied") is False
    )


def hostess_manifold_shell_handoff_review_intake_source_ready(
    downstream_shell_selection_receipt: dict[str, Any],
    selected_handoff: dict[str, Any],
    manifold_review_receipt: dict[str, Any],
) -> bool:
    selected_path = downstream_shell_selection_receipt.get("selected_payload_path")
    return (
        downstream_shell_selection_receipt.get("$schema")
        == HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA
        and downstream_shell_selection_receipt.get("status") == SELECTED_STATUS
        and downstream_shell_selection_receipt.get("issue_code") is None
        and downstream_shell_selection_receipt.get("selected_artifact_kind")
        == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
        and downstream_shell_selection_receipt.get("manifold_shell_handoff_selected")
        is True
        and downstream_shell_selection_receipt.get("makepad_shell_descriptor_selected")
        is False
        and isinstance(selected_path, str)
        and Path(selected_path).exists()
        and selected_handoff.get("$schema") == MANIFOLD_SHELL_HANDOFF_SCHEMA
        and isinstance(selected_handoff.get("handoff_id"), str)
        and isinstance(selected_handoff.get("shell_app_id"), str)
        and manifold_review_receipt.get("$schema")
        == MANIFOLD_SHELL_HANDOFF_REVIEW_RECEIPT_SCHEMA
        and manifold_review_receipt.get("status") == PASS_STATUS
        and manifold_review_receipt.get("handoff_id")
        == selected_handoff.get("handoff_id")
        and manifold_review_receipt.get("handoff_revision")
        == selected_handoff.get("handoff_revision")
        and manifold_review_receipt.get("target_host_profile")
        == selected_handoff.get("target_host_profile")
        and manifold_review_receipt.get("shell_app_id")
        == selected_handoff.get("shell_app_id")
        and manifold_review_receipt.get("validation_slot_id")
        == selected_handoff.get("validation_slot_id")
        and manifold_review_receipt.get("reviewed_stream_ids")
        == manifold_shell_handoff_stream_ids(selected_handoff)
        and manifold_review_receipt.get("reviewed_command_ids")
        == selected_handoff.get("command_ids")
        and manifold_review_receipt.get("reviewed_transport_ids")
        == manifold_shell_handoff_transport_ids(selected_handoff)
        and manifold_review_receipt.get("reviewed_endpoint_ids")
        == manifold_shell_handoff_endpoint_ids(selected_handoff)
        and manifold_shell_handoff_review_receipt_no_runtime_started(
            manifold_review_receipt
        )
        and _hostess_downstream_shell_selection_receipt_no_runtime_started(
            downstream_shell_selection_receipt
        )
    )


def build_hostess_manifold_shell_handoff_review_intake_receipt(
    downstream_shell_selection_receipt: dict[str, Any],
    selected_handoff: dict[str, Any],
    manifold_review_receipt: dict[str, Any],
    manifold_review_receipt_path: Path | None = None,
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    source_ready = hostess_manifold_shell_handoff_review_intake_source_ready(
        downstream_shell_selection_receipt,
        selected_handoff,
        manifold_review_receipt,
    )
    reviewed = decision == ACCEPTED_STATUS and decision_supported and source_ready
    status = REVIEWED_STATUS if reviewed else REJECTED_STATUS
    issue_code = None
    if status != REVIEWED_STATUS:
        issue_code = (
            reason_code
            or downstream_shell_selection_receipt.get("issue_code")
            or (
                "hostess.issue.hostess_manifold_shell_handoff_review_intake_decision"
                if not decision_supported
                else "hostess.issue.hostess_manifold_shell_handoff_review_intake_source_not_ready"
            )
        )
    checks = hostess_manifold_shell_handoff_review_intake_receipt_checks(
        downstream_shell_selection_receipt,
        selected_handoff,
        manifold_review_receipt,
        status,
        decision_supported,
    )
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    if failed and status == REVIEWED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        reviewed = False
    receipt_id = (
        "hostess.manifold_shell_handoff_review_intake_receipt."
        f"{downstream_shell_selection_receipt.get('receipt_id')}"
        if isinstance(downstream_shell_selection_receipt.get("receipt_id"), str)
        and downstream_shell_selection_receipt.get("receipt_id")
        else "hostess.manifold_shell_handoff_review_intake_receipt.unknown"
    )
    reviewed_stream_ids = manifold_review_receipt.get("reviewed_stream_ids", [])
    reviewed_command_ids = manifold_review_receipt.get("reviewed_command_ids", [])
    reviewed_transport_ids = manifold_review_receipt.get("reviewed_transport_ids", [])
    reviewed_endpoint_ids = manifold_review_receipt.get("reviewed_endpoint_ids", [])
    return {
        "$schema": HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "source_downstream_shell_selection_receipt_id": (
            downstream_shell_selection_receipt.get("receipt_id")
        ),
        "source_downstream_shell_selection_receipt_schema": (
            downstream_shell_selection_receipt.get("$schema")
        ),
        "source_downstream_shell_selection_receipt_status": (
            downstream_shell_selection_receipt.get("status")
        ),
        "source_manifold_shell_handoff_review_receipt_path": (
            str(manifold_review_receipt_path)
            if manifold_review_receipt_path is not None
            else None
        ),
        "source_selected_payload_path": (
            downstream_shell_selection_receipt.get("selected_payload_path")
        ),
        "source_selected_artifact_kind": (
            downstream_shell_selection_receipt.get("selected_artifact_kind")
        ),
        "manifest_id": downstream_shell_selection_receipt.get("manifest_id"),
        "project_id": downstream_shell_selection_receipt.get("project_id"),
        "project_revision": downstream_shell_selection_receipt.get(
            "project_revision"
        ),
        "selected_candidate_id": downstream_shell_selection_receipt.get(
            "selected_candidate_id"
        ),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": (
            HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_POLICY
        ),
        "receipt_owner": HOSTESS_OWNER,
        "selection_owner": HOSTESS_OWNER,
        "staging_owner": HOSTESS_OWNER,
        "payload_manifest_owner": HOSTESS_OWNER,
        "handoff_review_authority": MANIFOLD_OWNER,
        "command_session_authority": MANIFOLD_OWNER,
        "requester_role": STUDIO_REQUESTER,
        "studio_role": STUDIO_ROLE,
        "selected_handoff_schema": selected_handoff.get("$schema"),
        "selected_handoff_id": selected_handoff.get("handoff_id"),
        "selected_handoff_revision": selected_handoff.get("handoff_revision"),
        "selected_target_host_profile": selected_handoff.get(
            "target_host_profile"
        ),
        "selected_shell_app_id": selected_handoff.get("shell_app_id"),
        "selected_validation_slot_id": selected_handoff.get("validation_slot_id"),
        "manifold_review_schema": manifold_review_receipt.get("$schema"),
        "manifold_review_id": manifold_review_receipt.get("review_id"),
        "manifold_review_handoff_id": manifold_review_receipt.get("handoff_id"),
        "manifold_review_status": manifold_review_receipt.get("status"),
        "manifold_authority": manifold_review_receipt.get("manifold_authority"),
        "manifold_shell_handoff_selected": (
            downstream_shell_selection_receipt.get("manifold_shell_handoff_selected")
            is True
        ),
        "makepad_shell_descriptor_selected": (
            downstream_shell_selection_receipt.get("makepad_shell_descriptor_selected")
            is True
        ),
        "manifold_shell_handoff_reviewed": reviewed,
        "manifold_shell_handoff_review_ready": reviewed,
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
        "legacy_rusty_xr_dependency_used": False,
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
        "pmb_shell_handoff_review_required": (
            downstream_shell_selection_receipt.get("pmb_shell_handoff_review_required")
            is True
        ),
        "pmb_shell_handoff_review_ready": (
            downstream_shell_selection_receipt.get("pmb_shell_handoff_review_ready")
            is True
        ),
        **pmb_shell_handoff_review_summary_from_source(
            downstream_shell_selection_receipt
        ),
        "checks": checks,
        "next_required_action": (
            "makepad_consume_manifold_reviewed_shell_handoff_without_launch"
            if reviewed
            else "repair_or_decline_manifold_shell_handoff_review_intake"
        ),
    }


def validate_hostess_manifold_shell_handoff_review_intake_receipt(
    downstream_shell_selection_receipt: dict[str, Any],
    selected_handoff: dict[str, Any],
    manifold_review_receipt: dict[str, Any],
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
    source_ready = hostess_manifold_shell_handoff_review_intake_source_ready(
        downstream_shell_selection_receipt,
        selected_handoff,
        manifold_review_receipt,
    )
    checks = [
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.schema",
            receipt.get("$schema")
            == HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_SCHEMA,
            "Hostess Manifold shell handoff review intake receipt schema is supported",
            "Hostess Manifold shell handoff review intake receipt schema is unsupported",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_receipt_schema",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.status",
            status in {REVIEWED_STATUS, REJECTED_STATUS}
            and (
                (status == REVIEWED_STATUS and receipt.get("issue_code") is None)
                or (
                    status == REJECTED_STATUS
                    and isinstance(receipt.get("issue_code"), str)
                )
            ),
            "Hostess Manifold shell handoff review intake receipt status is consistent",
            "Hostess Manifold shell handoff review intake receipt status is inconsistent",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_receipt_status",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.sources",
            receipt.get("source_downstream_shell_selection_receipt_id")
            == downstream_shell_selection_receipt.get("receipt_id")
            and receipt.get("source_downstream_shell_selection_receipt_schema")
            == HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA
            and receipt.get("source_selected_payload_path")
            == downstream_shell_selection_receipt.get("selected_payload_path")
            and receipt.get("source_selected_artifact_kind")
            == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
            and receipt.get("manifest_id")
            == downstream_shell_selection_receipt.get("manifest_id")
            and receipt.get("project_id")
            == downstream_shell_selection_receipt.get("project_id")
            and receipt.get("project_revision")
            == downstream_shell_selection_receipt.get("project_revision"),
            "Hostess Manifold shell handoff review intake sources match selection",
            "Hostess Manifold shell handoff review intake sources drifted",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_source_mismatch",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.source_readiness",
            (status == REVIEWED_STATUS and source_ready) or status == REJECTED_STATUS,
            "Selected Manifold shell handoff and Manifold review receipt are ready",
            "Selected Manifold shell handoff or Manifold review receipt is not ready",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_source_not_ready",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("selection_owner") == HOSTESS_OWNER
            and receipt.get("staging_owner") == HOSTESS_OWNER
            and receipt.get("payload_manifest_owner") == HOSTESS_OWNER
            and receipt.get("handoff_review_authority") == MANIFOLD_OWNER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess records intake while Manifold owns shell handoff review authority",
            "Hostess Manifold shell handoff review intake authority fields drifted",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_authority",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.handoff_review",
            (
                status == REVIEWED_STATUS
                and receipt.get("selected_handoff_schema")
                == MANIFOLD_SHELL_HANDOFF_SCHEMA
                and receipt.get("selected_handoff_id")
                == selected_handoff.get("handoff_id")
                and receipt.get("selected_shell_app_id")
                == selected_handoff.get("shell_app_id")
                and receipt.get("manifold_review_schema")
                == MANIFOLD_SHELL_HANDOFF_REVIEW_RECEIPT_SCHEMA
                and receipt.get("manifold_review_handoff_id")
                == selected_handoff.get("handoff_id")
                and receipt.get("manifold_review_status") == PASS_STATUS
                and receipt.get("manifold_shell_handoff_selected") is True
                and receipt.get("makepad_shell_descriptor_selected") is False
                and receipt.get("manifold_shell_handoff_reviewed") is True
                and receipt.get("manifold_shell_handoff_review_ready") is True
                and receipt.get("reviewed_stream_ids")
                == manifold_shell_handoff_stream_ids(selected_handoff)
                and receipt.get("reviewed_command_ids")
                == selected_handoff.get("command_ids")
                and receipt.get("reviewed_transport_ids")
                == manifold_shell_handoff_transport_ids(selected_handoff)
                and receipt.get("reviewed_endpoint_ids")
                == manifold_shell_handoff_endpoint_ids(selected_handoff)
            )
            or (
                status == REJECTED_STATUS
                and receipt.get("manifold_shell_handoff_reviewed") is False
                and receipt.get("manifold_shell_handoff_review_ready") is False
            ),
            "Hostess intake links the selected handoff to the Manifold review receipt",
            "Hostess intake handoff/review linkage drifted",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_review_drift",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.no_runtime_started",
            hostess_manifold_shell_handoff_review_intake_receipt_no_runtime_started(
                receipt
            ),
            "Hostess Manifold shell handoff review intake did not execute runtime, platform, launch, or command-session work",
            "Hostess Manifold shell handoff review intake indicates runtime, platform, launch, or command-session work",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_runtime_started",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.counts",
            receipt.get("reviewed_stream_count")
            == len(receipt.get("reviewed_stream_ids", []))
            and receipt.get("reviewed_command_count")
            == len(receipt.get("reviewed_command_ids", []))
            and receipt.get("reviewed_transport_count")
            == len(receipt.get("reviewed_transport_ids", []))
            and receipt.get("reviewed_endpoint_count")
            == len(receipt.get("reviewed_endpoint_ids", [])),
            "Hostess Manifold shell handoff review intake counts match nested ids",
            "Hostess Manifold shell handoff review intake counts drifted",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_count_drift",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.embedded_checks",
            (
                status == REVIEWED_STATUS
                and not embedded_failed
                and all(entry.get("status") == PASS_STATUS for entry in embedded_check_dicts)
            )
            or status == REJECTED_STATUS,
            "Hostess Manifold shell handoff review intake embedded checks match receipt status",
            "Hostess Manifold shell handoff review intake embedded checks do not match receipt status",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_checks",
        ),
    ]
    failed = [entry for entry in checks if entry["status"] == FAIL_STATUS]
    return {
        "$schema": (
            HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_VALIDATION_SCHEMA
        ),
        "receipt_id": receipt.get("receipt_id"),
        "source_receipt_schema": receipt.get("$schema"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "copy_started": False,
        "staging_payloads_copied": False,
        "manifold_shell_handoff_selected": receipt.get(
            "manifold_shell_handoff_selected"
        )
        is True,
        "manifold_shell_handoff_review_ready": receipt.get(
            "manifold_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def hostess_manifold_shell_handoff_review_intake_receipt_checks(
    downstream_shell_selection_receipt: dict[str, Any],
    selected_handoff: dict[str, Any],
    manifold_review_receipt: dict[str, Any],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    source_ready = hostess_manifold_shell_handoff_review_intake_source_ready(
        downstream_shell_selection_receipt,
        selected_handoff,
        manifold_review_receipt,
    )
    return [
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.selection_source",
            status != REVIEWED_STATUS
            or (
                downstream_shell_selection_receipt.get("$schema")
                == HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA
                and downstream_shell_selection_receipt.get("status") == SELECTED_STATUS
                and downstream_shell_selection_receipt.get("selected_artifact_kind")
                == MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND
                and downstream_shell_selection_receipt.get(
                    "manifold_shell_handoff_selected"
                )
                is True
            ),
            "Hostess downstream selection chose a Manifold shell handoff artifact",
            "Hostess downstream selection did not choose a Manifold shell handoff artifact",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_selection_source",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.handoff_source",
            status != REVIEWED_STATUS
            or selected_handoff.get("$schema") == MANIFOLD_SHELL_HANDOFF_SCHEMA,
            "Selected payload is a Manifold shell handoff",
            "Selected payload is not a Manifold shell handoff",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_handoff_source",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.manifold_review",
            status != REVIEWED_STATUS
            or (
                manifold_review_receipt.get("$schema")
                == MANIFOLD_SHELL_HANDOFF_REVIEW_RECEIPT_SCHEMA
                and manifold_review_receipt.get("status") == PASS_STATUS
                and manifold_review_receipt.get("handoff_id")
                == selected_handoff.get("handoff_id")
                and manifold_shell_handoff_review_receipt_no_runtime_started(
                    manifold_review_receipt
                )
            ),
            "Manifold shell handoff review receipt passes and matches the selected handoff",
            "Manifold shell handoff review receipt is missing, failing, or mismatched",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_review_source",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.source_ready",
            status != REVIEWED_STATUS or source_ready,
            "Selected shell handoff review intake source is ready",
            "Selected shell handoff review intake source is not ready",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_source_not_ready",
        ),
        _check(
            "hostess.check.hostess_manifold_shell_handoff_review_intake_receipt.decision",
            decision_supported,
            "Hostess Manifold shell handoff review intake decision is supported",
            "Hostess Manifold shell handoff review intake decision is unsupported",
            "hostess.issue.hostess_manifold_shell_handoff_review_intake_decision",
        ),
    ]


def hostess_manifold_shell_handoff_review_intake_receipt_no_runtime_started(
    receipt: dict[str, Any],
) -> bool:
    return (
        receipt.get("legacy_rusty_xr_dependency_used") is False
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
