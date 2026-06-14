"""Operator release readiness bundle receipts."""

from __future__ import annotations

from typing import Any

from tools.studio_staging.request_shared import *  # shared schema constants and helpers
from tools.studio_staging.pmb_replay_validation import *  # replay validation helpers
from tools.studio_staging.staging_handoff import *  # staging handoff readiness summaries

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
