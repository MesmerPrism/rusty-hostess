"""Schema-only Hostess intake for Studio staging execution requests."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.studio_staging.manifold_handoff_intake import (
    build_hostess_manifold_shell_handoff_review_intake_receipt,
    hostess_manifold_shell_handoff_review_intake_receipt_checks,
    hostess_manifold_shell_handoff_review_intake_receipt_no_runtime_started,
    hostess_manifold_shell_handoff_review_intake_source_ready,
    manifold_shell_handoff_endpoint_ids,
    manifold_shell_handoff_review_receipt_no_runtime_started,
    manifold_shell_handoff_stream_ids,
    manifold_shell_handoff_transport_ids,
    selected_manifold_shell_handoff_from_selection,
    validate_hostess_manifold_shell_handoff_review_intake_receipt,
)
from tools.studio_staging.makepad_shell_contract import (
    HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_SCHEMA,
    HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_VALIDATION_SCHEMA,
    HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA,
    HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_VALIDATION_SCHEMA,
    build_hostess_makepad_shell_launch_handoff_receipt,
    build_hostess_makepad_shell_contract_receipt,
    hostess_makepad_shell_launch_handoff_receipt_no_runtime_started,
    hostess_makepad_shell_launch_handoff_source_ready,
    hostess_makepad_shell_contract_intake_no_runtime_started,
    hostess_makepad_shell_contract_receipt_checks,
    hostess_makepad_shell_contract_receipt_no_runtime_started,
    hostess_makepad_shell_contract_source_ready,
    validate_hostess_makepad_shell_launch_handoff_receipt,
    validate_hostess_makepad_shell_contract_receipt,
)


REQUEST_SCHEMA = "rusty.studio.shell_hostess_staging_execution_request.v1"
ACK_SCHEMA = "rusty.studio.shell_hostess_staging_execution_ack.v1"
REJECT_SCHEMA = "rusty.studio.shell_hostess_staging_execution_reject.v1"
INTAKE_SCHEMA = "rusty.hostess.studio_staging_execution_request_intake.v1"
SMOKE_HANDOFF_SCHEMA = "rusty.hostess.studio_staging_smoke_handoff.v1"
SMOKE_HANDOFF_VALIDATION_SCHEMA = "rusty.hostess.studio_staging_smoke_handoff_validation.v1"
SMOKE_DRY_RUN_REQUEST_SCHEMA = "rusty.hostess.studio_staging_smoke_dry_run_request.v1"
SMOKE_DRY_RUN_RECEIPT_SCHEMA = "rusty.hostess.studio_staging_smoke_dry_run_receipt.v1"
SMOKE_DRY_RUN_VALIDATION_SCHEMA = "rusty.hostess.studio_staging_smoke_dry_run_validation.v1"
SMOKE_EXECUTION_PREFLIGHT_SCHEMA = "rusty.hostess.studio_staging_smoke_execution_preflight.v1"
SMOKE_EXECUTION_PREFLIGHT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_smoke_execution_preflight_validation.v1"
)
SMOKE_HOST_SHELL_EXECUTION_SCHEMA = "rusty.hostess.studio_staging_smoke_host_shell_execution.v1"
SMOKE_HOST_SHELL_EXECUTION_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_smoke_host_shell_execution_validation.v1"
)
SMOKE_REVIEW_BUNDLE_SCHEMA = "rusty.hostess.studio_staging_smoke_review_bundle.v1"
SMOKE_REVIEW_BUNDLE_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_smoke_review_bundle_validation.v1"
)
PLATFORM_SMOKE_PLAN_SCHEMA = "rusty.hostess.studio_staging_platform_smoke_plan.v1"
PLATFORM_SMOKE_PLAN_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_plan_validation.v1"
)
PLATFORM_SMOKE_APPROVAL_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_approval_receipt.v1"
)
PLATFORM_SMOKE_APPROVAL_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_approval_receipt_validation.v1"
)
PLATFORM_SMOKE_EXECUTION_REQUEST_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_request.v1"
)
PLATFORM_SMOKE_EXECUTION_REQUEST_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_request_validation.v1"
)
PLATFORM_SMOKE_EXECUTION_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_receipt.v1"
)
PLATFORM_SMOKE_EXECUTION_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_receipt_validation.v1"
)
PLATFORM_SMOKE_OPERATOR_START_GATE_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_operator_start_gate.v1"
)
PLATFORM_SMOKE_OPERATOR_START_GATE_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_operator_start_gate_validation.v1"
)
PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_operator_start_preflight_receipt.v1"
)
PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_operator_start_preflight_receipt_validation.v1"
)
PLATFORM_SMOKE_EXECUTION_REPORT_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_report.v1"
)
PLATFORM_SMOKE_EXECUTION_REPORT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_execution_report_validation.v1"
)
PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_evidence_attachment_receipt.v1"
)
PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_evidence_attachment_receipt_validation.v1"
)
PLATFORM_SMOKE_EVIDENCE_REVIEW_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_evidence_review.v1"
)
PLATFORM_SMOKE_EVIDENCE_REVIEW_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_platform_smoke_evidence_review_validation.v1"
)
STUDIO_PMB_AUTHORING_REVIEW_SCHEMA = (
    "rusty.studio.projected_motion_breath_authoring_review.v1"
)
STUDIO_PMB_SOURCE_ADAPTER_SELECTION_REVIEW_SCHEMA = (
    "rusty.studio.projected_motion_breath_source_adapter_selection_review.v1"
)
STUDIO_PMB_SHELL_HANDOFF_REVIEW_SCHEMA = (
    "rusty.studio.projected_motion_breath_shell_handoff_review.v1"
)
STUDIO_PACKAGE_EVIDENCE_INTAKE_SCHEMA = "rusty.studio.package_evidence_intake_report.v1"
PMB_VALIDATION_HANDOFF_SCHEMA = "rusty.hostess.projected_motion_breath_validation_handoff.v1"
PMB_VALIDATION_HANDOFF_VALIDATION_SCHEMA = (
    "rusty.hostess.projected_motion_breath_validation_handoff_validation.v1"
)
PMB_REPLAY_VALIDATION_RECEIPT_SCHEMA = (
    "rusty.hostess.projected_motion_breath_replay_validation_receipt.v1"
)
PMB_REPLAY_VALIDATION_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.projected_motion_breath_replay_validation_receipt_validation.v1"
)
OPERATOR_RELEASE_READINESS_BUNDLE_SCHEMA = (
    "rusty.hostess.studio_staging_operator_release_readiness_bundle.v1"
)
OPERATOR_RELEASE_READINESS_BUNDLE_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_operator_release_readiness_bundle_validation.v1"
)
STUDIO_HOSTESS_STAGING_HANDOFF_SCHEMA = (
    "rusty.studio.shell_hostess_staging_handoff_envelope.v1"
)
STUDIO_HOSTESS_STAGING_ACCEPTANCE_MANIFEST_SCHEMA = (
    "rusty.studio.shell_hostess_staging_acceptance_manifest.v1"
)
STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA = (
    "rusty.studio.shell_hostess_staging_file_plan.v1"
)
HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_handoff_acceptance_receipt.v1"
)
HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_handoff_acceptance_receipt_validation.v1"
)
HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_file_plan_receipt.v1"
)
HOSTESS_STAGING_FILE_PLAN_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_file_plan_receipt_validation.v1"
)
HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staging_file_copy_receipt.v1"
)
HOSTESS_STAGING_FILE_COPY_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staging_file_copy_receipt_validation.v1"
)
HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA = (
    "rusty.hostess.studio_staged_payload_manifest_receipt.v1"
)
HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.studio_staged_payload_manifest_receipt_validation.v1"
)
HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA = (
    "rusty.hostess.downstream_shell_selection_receipt.v1"
)
HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_VALIDATION_SCHEMA = (
    "rusty.hostess.downstream_shell_selection_receipt_validation.v1"
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
OPERATOR_START_REQUEST_TEMPLATE_SCHEMA = (
    "rusty.hostess.platform_smoke_operator_start_request_template.v1"
)
OPERATOR_START_ACK_TEMPLATE_SCHEMA = (
    "rusty.hostess.platform_smoke_operator_start_ack_template.v1"
)
OPERATOR_START_REJECT_TEMPLATE_SCHEMA = (
    "rusty.hostess.platform_smoke_operator_start_reject_template.v1"
)
PLATFORM_SMOKE_EVIDENCE_RECEIPT_TEMPLATE_SCHEMA = (
    "rusty.hostess.platform_smoke_expected_evidence_receipt_template.v1"
)

READY_STATUS = "ready"
BLOCKED_STATUS = "blocked"
ACCEPTED_STATUS = "accepted"
REJECTED_STATUS = "rejected"
PENDING_STATUS = "pending"
COMPLETED_STATUS = "completed"
VALIDATED_STATUS = "validated"
REVIEWED_STATUS = "reviewed"
SELECTED_STATUS = "selected"
PLANNED_STATUS = "planned"
APPROVED_STATUS = "approved"
PASS_STATUS = "pass"
FAIL_STATUS = "fail"

HOSTESS_OWNER = "rusty.hostess"
MANIFOLD_OWNER = "rusty.manifold"
STUDIO_REQUESTER = "rusty.studio"
STUDIO_ROLE = "authoring.export_planning"
REQUEST_POLICY = "not_executed.hostess_request_only"
HOST_SHELL_EXECUTION_POLICY = "hostess.no_device_host_shell_schema_execution_only"
SMOKE_REVIEW_BUNDLE_POLICY = "hostess.no_device_review_bundle_only"
PLATFORM_SMOKE_PLAN_POLICY = "hostess.operator_controlled_platform_smoke_plan_only"
PLATFORM_SMOKE_APPROVAL_RECEIPT_POLICY = (
    "hostess.operator_controlled_platform_smoke_approval_receipt_only"
)
PLATFORM_SMOKE_EXECUTION_REQUEST_POLICY = (
    "hostess.operator_controlled_platform_smoke_execution_request_only"
)
PLATFORM_SMOKE_EXECUTION_RECEIPT_POLICY = (
    "hostess.operator_controlled_platform_smoke_execution_receipt_only"
)
PLATFORM_SMOKE_OPERATOR_START_GATE_POLICY = (
    "hostess.operator_controlled_platform_smoke_operator_start_gate_only"
)
PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_POLICY = (
    "hostess.operator_controlled_platform_smoke_operator_start_preflight_receipt_only"
)
PLATFORM_SMOKE_EXECUTION_REPORT_POLICY = (
    "hostess.operator_started_platform_smoke_execution_report_only"
)
PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_POLICY = (
    "hostess.external_platform_smoke_evidence_attachment_receipt_only"
)
PLATFORM_SMOKE_EVIDENCE_REVIEW_POLICY = (
    "hostess.platform_smoke_evidence_review_scorecard_only"
)
PMB_VALIDATION_HANDOFF_POLICY = "hostess.projected_motion_breath_validation_handoff_review_only"
PMB_REPLAY_VALIDATION_RECEIPT_POLICY = (
    "hostess.projected_motion_breath_replay_validation_receipt_review_only"
)
OPERATOR_RELEASE_READINESS_BUNDLE_POLICY = (
    "hostess.operator_release_readiness_bundle_schema_only"
)
HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_POLICY = (
    "hostess.staging_handoff_acceptance_schema_only"
)
HOSTESS_STAGING_FILE_PLAN_RECEIPT_POLICY = (
    "hostess.staging_file_plan_receipt_schema_only"
)
HOSTESS_STAGING_FILE_COPY_RECEIPT_POLICY = (
    "hostess.staging_file_copy_receipt_filesystem_only"
)
HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_POLICY = (
    "hostess.staged_payload_manifest_review_schema_only"
)
HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_POLICY = (
    "hostess.downstream_shell_selection_schema_only"
)
HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_POLICY = (
    "hostess.manifold_shell_handoff_review_intake_schema_only"
)
SHELL_DESCRIPTOR_ARTIFACT_KIND = "shell_descriptor"
MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND = "manifold_shell_handoff"
DOWNSTREAM_SHELL_SELECTION_ARTIFACT_KINDS = (
    MANIFOLD_SHELL_HANDOFF_ARTIFACT_KIND,
    SHELL_DESCRIPTOR_ARTIFACT_KIND,
)
PMB_TARGET_PACKAGE_ID = "package.projected_motion_breath"
PMB_TARGET_MODULE_ID = "module.breath.projected_motion"
PMB_PROPOSED_COMMAND_ID = "command.breath.set_profile"
PMB_REQUIRED_PACKAGE_CHECKS = [
    "validation.package.package.projected_motion_breath.projected_motion_contract",
    "validation.package.package.projected_motion_breath.projected_motion_profile_commands",
    "validation.package.package.projected_motion_breath.projected_motion_goldens",
]
PMB_SOURCE_ADAPTER_STREAM_BINDINGS = {
    "pose": "stream.motion.object_pose",
    "vector3": "stream.motion.vector3",
}
PMB_VALIDATION_SLOT_CONTRACTS = [
    {
        "slot_id": "hostess.pmb.review_authoring_profile_intent",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.pmb.review_authoring_profile_intent",
        "expected_input_kind": STUDIO_PMB_AUTHORING_REVIEW_SCHEMA,
        "validation_kind": "schema_only_authoring_intent_review",
    },
    {
        "slot_id": "hostess.pmb.review_package_evidence",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.pmb.review_package_evidence",
        "expected_input_kind": STUDIO_PACKAGE_EVIDENCE_INTAKE_SCHEMA,
        "validation_kind": "schema_only_package_evidence_review",
    },
    {
        "slot_id": "manifold.pmb.review_set_profile_command_contract",
        "owner": MANIFOLD_OWNER,
        "route_kind": "manifold.review.command.breath.set_profile",
        "expected_input_kind": PMB_PROPOSED_COMMAND_ID,
        "validation_kind": "schema_only_manifold_command_contract_review",
    },
    {
        "slot_id": "hostess.pmb.prepare_replay_validation_plan",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.pmb.prepare_replay_validation_plan",
        "expected_input_kind": "synthetic_or_replay_fixture",
        "validation_kind": "schema_only_synthetic_replay_plan",
    },
]
PMB_SOURCE_ADAPTER_SELECTION_SLOT_CONTRACT = {
    "slot_id": "hostess.pmb.review_source_adapter_selection",
    "owner": HOSTESS_OWNER,
    "route_kind": "hostess.pmb.review_source_adapter_selection",
    "expected_input_kind": STUDIO_PMB_SOURCE_ADAPTER_SELECTION_REVIEW_SCHEMA,
    "validation_kind": "schema_only_source_adapter_selection_review",
}
PMB_REPLAY_DESCRIPTOR_CONTRACTS = [
    {
        "descriptor_id": "pmb.replay.golden.pose_projection",
        "owner": HOSTESS_OWNER,
        "fixture_kind": "projected_motion_breath_golden_case",
        "case_id": "case.projected_motion_breath.pose_projection",
        "expected_processor_status": PASS_STATUS,
        "validation_kind": "pure_processor_golden_replay",
    },
    {
        "descriptor_id": "pmb.replay.golden.vector_projection",
        "owner": HOSTESS_OWNER,
        "fixture_kind": "projected_motion_breath_golden_case",
        "case_id": "case.projected_motion_breath.vector_projection",
        "expected_processor_status": PASS_STATUS,
        "validation_kind": "pure_processor_golden_replay",
    },
    {
        "descriptor_id": "pmb.replay.damaged.flat_calibration",
        "owner": HOSTESS_OWNER,
        "fixture_kind": "projected_motion_breath_damaged_case",
        "case_id": "case.projected_motion_breath.flat_calibration_rejected",
        "expected_processor_status": FAIL_STATUS,
        "validation_kind": "pure_processor_damaged_replay",
    },
    {
        "descriptor_id": "pmb.replay.damaged.stale_source",
        "owner": HOSTESS_OWNER,
        "fixture_kind": "projected_motion_breath_damaged_case",
        "case_id": "case.projected_motion_breath.stale_source_rejected",
        "expected_processor_status": FAIL_STATUS,
        "validation_kind": "pure_processor_damaged_replay",
    },
]

OPERATOR_RELEASE_ARTIFACT_CONTRACTS = [
    {
        "artifact_id": "hostess.operator_release.platform_smoke_evidence_review",
        "owner": HOSTESS_OWNER,
        "source_role": "platform_smoke_evidence_review",
        "source_schema": PLATFORM_SMOKE_EVIDENCE_REVIEW_SCHEMA,
        "expected_source_status": REVIEWED_STATUS,
        "validation_kind": "platform_smoke_evidence_review_scorecard",
    },
    {
        "artifact_id": "hostess.operator_release.pmb_replay_validation_receipt",
        "owner": HOSTESS_OWNER,
        "source_role": "projected_motion_breath_replay_validation_receipt",
        "source_schema": PMB_REPLAY_VALIDATION_RECEIPT_SCHEMA,
        "expected_source_status": VALIDATED_STATUS,
        "validation_kind": "projected_motion_breath_replay_validation_receipt",
    },
]

OPERATOR_RELEASE_HOST_SHELL_TARGET_CONTRACTS = [
    {
        "host_shell_target_id": "hostess.operator_release.hostess_t",
        "owner": HOSTESS_OWNER,
        "host_shell_kind": "hostess.t",
        "target_kind": "hostess_t_operator_shell",
        "validation_kind": "schema_artifact_bundle_readiness",
    },
    {
        "host_shell_target_id": "hostess.operator_release.dedicated_quest_host_shell",
        "owner": HOSTESS_OWNER,
        "host_shell_kind": "dedicated_quest_host_shell",
        "target_kind": "quest_host_shell_operator_shell",
        "validation_kind": "schema_artifact_bundle_readiness",
    },
]

REQUIRED_PROHIBITED_ACTIONS = [
    "stage_generated_shells",
    "install",
    "launch",
    "open_command_session",
    "collect_device_evidence",
    "collect_install_launch_evidence",
]

REQUIRED_EVIDENCE_KINDS = [
    "hostess_staging_request_ack",
    "hostess_file_copy_stage_receipt",
    "hostess_install_launch_evidence_receipt",
    "manifold_command_session_contract_review",
]

SMOKE_HANDOFF_REQUIRED_EVIDENCE_KINDS = REQUIRED_EVIDENCE_KINDS + [
    "hostess_smoke_handoff_checklist",
]

SMOKE_DRY_RUN_REQUIRED_RECEIPT_KINDS = SMOKE_HANDOFF_REQUIRED_EVIDENCE_KINDS + [
    "hostess_smoke_dry_run_receipt",
]

HOSTESS_ACTION_ROUTES = {
    "adapter.hostess.accept_staging_handoff": "hostess.accept.staging_handoff",
    "adapter.hostess.verify_staging_file_plan_checksum": "hostess.verify.staging_file_plan_checksum",
    "adapter.hostess.review_staging_file_requests": "hostess.review.staging_file_requests",
    "adapter.hostess.copy_staging_files": "hostess.stage.files_from_plan",
    "adapter.hostess.collect_install_launch_evidence": "hostess.collect.install_launch_evidence",
}

MANIFOLD_ACTION_ROUTES = {
    "adapter.manifold.review_command_session_contract": "manifold.review.command_session_contract",
}

SMOKE_HANDOFF_STARTED_FLAGS = [
    "execution_performed",
    "build_started",
    "copy_started",
    "stage_started",
    "install_started",
    "launch_started",
    "evidence_collection_started",
    "command_session_started",
]

SMOKE_HANDOFF_ITEM_CONTRACTS = [
    {
        "item_id": "hostess.smoke.validate_studio_request_intake",
        "owner": HOSTESS_OWNER,
        "source_action_id": "adapter.hostess.accept_staging_handoff",
        "route_kind": "hostess.adapter.validate_studio_request",
        "expected_output_kind": "studio_staging_execution_request_intake",
    },
    {
        "item_id": "hostess.smoke.ack_or_reject_request",
        "owner": HOSTESS_OWNER,
        "source_action_id": "adapter.hostess.accept_staging_handoff",
        "route_kind": "hostess.adapter.ack_or_reject_studio_request",
        "expected_output_kind": "hostess_staging_request_ack_or_reject",
    },
    {
        "item_id": "hostess.smoke.plan_stage_copy_receipt",
        "owner": HOSTESS_OWNER,
        "source_action_id": "adapter.hostess.copy_staging_files",
        "route_kind": "hostess.stage.files_from_plan",
        "expected_output_kind": "hostess_file_copy_stage_receipt",
    },
    {
        "item_id": "hostess.smoke.plan_install_launch_receipt",
        "owner": HOSTESS_OWNER,
        "source_action_id": "adapter.hostess.collect_install_launch_evidence",
        "route_kind": "hostess.collect.install_launch_evidence",
        "expected_output_kind": "hostess_install_launch_evidence_receipt",
    },
    {
        "item_id": "hostess.smoke.plan_command_session_review",
        "owner": MANIFOLD_OWNER,
        "source_action_id": "adapter.manifold.review_command_session_contract",
        "route_kind": "manifold.review.command_session_contract",
        "expected_output_kind": "manifold_command_session_contract_review",
    },
]

SMOKE_DRY_RUN_STEP_CONTRACTS = [
    {
        "step_id": "hostess.dry_run.validate_request_intake",
        "owner": HOSTESS_OWNER,
        "source_item_id": "hostess.smoke.validate_studio_request_intake",
        "route_kind": "hostess.adapter.validate_studio_request",
        "expected_receipt_kind": "hostess_smoke_handoff_checklist",
    },
    {
        "step_id": "hostess.dry_run.accept_request_ack",
        "owner": HOSTESS_OWNER,
        "source_item_id": "hostess.smoke.ack_or_reject_request",
        "route_kind": "hostess.adapter.ack_or_reject_studio_request",
        "expected_receipt_kind": "hostess_staging_request_ack",
    },
    {
        "step_id": "hostess.dry_run.plan_stage_copy_receipt",
        "owner": HOSTESS_OWNER,
        "source_item_id": "hostess.smoke.plan_stage_copy_receipt",
        "route_kind": "hostess.stage.files_from_plan",
        "expected_receipt_kind": "hostess_file_copy_stage_receipt",
    },
    {
        "step_id": "hostess.dry_run.plan_install_launch_receipt",
        "owner": HOSTESS_OWNER,
        "source_item_id": "hostess.smoke.plan_install_launch_receipt",
        "route_kind": "hostess.collect.install_launch_evidence",
        "expected_receipt_kind": "hostess_install_launch_evidence_receipt",
    },
    {
        "step_id": "hostess.dry_run.plan_command_session_review",
        "owner": MANIFOLD_OWNER,
        "source_item_id": "hostess.smoke.plan_command_session_review",
        "route_kind": "manifold.review.command_session_contract",
        "expected_receipt_kind": "manifold_command_session_contract_review",
    },
]

SMOKE_PREFLIGHT_CAPABILITY_CONTRACTS = [
    {
        "capability_id": "hostess.preflight.validate_dry_run_request",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.preflight.validate_dry_run_request",
        "evidence_kind": "hostess_smoke_dry_run_request_validation",
    },
    {
        "capability_id": "hostess.preflight.validate_dry_run_receipt",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.preflight.validate_dry_run_receipt",
        "evidence_kind": "hostess_smoke_dry_run_receipt_validation",
    },
    {
        "capability_id": "hostess.preflight.verify_stage_copy_plan",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.stage.files_from_plan",
        "evidence_kind": "hostess_file_copy_stage_receipt",
    },
    {
        "capability_id": "hostess.preflight.verify_install_launch_evidence_plan",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.collect.install_launch_evidence",
        "evidence_kind": "hostess_install_launch_evidence_receipt",
    },
    {
        "capability_id": "hostess.preflight.verify_command_session_review_plan",
        "owner": MANIFOLD_OWNER,
        "route_kind": "manifold.review.command_session_contract",
        "evidence_kind": "manifold_command_session_contract_review",
    },
    {
        "capability_id": "hostess.preflight.no_device_runtime_guard",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.preflight.no_device_runtime_guard",
        "evidence_kind": "hostess_smoke_execution_preflight",
    },
]

PLATFORM_SMOKE_PLAN_ACTION_CONTRACTS = [
    {
        "plan_action_id": "hostess.platform_smoke.review_bundle_gate",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.review_bundle_gate",
        "action_kind": "hostess_operator_review_gate",
        "approval_kind": "operator.reviewed_bundle_acceptance",
        "expected_input_kind": "hostess_smoke_review_bundle",
        "expected_output_kind": "hostess_platform_smoke_plan_gate",
    },
    {
        "plan_action_id": "hostess.platform_smoke.copy_stage_files",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.copy_stage_files",
        "action_kind": "hostess_copy_stage_plan",
        "approval_kind": "operator.copy_stage_approval",
        "expected_input_kind": "hostess_smoke_review_bundle",
        "expected_output_kind": "hostess_copy_stage_receipt",
    },
    {
        "plan_action_id": "hostess.platform_smoke.install_package",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.install_package",
        "action_kind": "hostess_install_plan",
        "approval_kind": "operator.install_approval",
        "expected_input_kind": "hostess_copy_stage_receipt",
        "expected_output_kind": "hostess_install_receipt",
    },
    {
        "plan_action_id": "hostess.platform_smoke.launch_package",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.launch_package",
        "action_kind": "hostess_launch_plan",
        "approval_kind": "operator.launch_approval",
        "expected_input_kind": "hostess_install_receipt",
        "expected_output_kind": "hostess_launch_receipt",
    },
    {
        "plan_action_id": "hostess.platform_smoke.collect_install_launch_evidence",
        "owner": HOSTESS_OWNER,
        "route_kind": "hostess.platform_smoke.collect_install_launch_evidence",
        "action_kind": "hostess_evidence_plan",
        "approval_kind": "operator.evidence_collection_approval",
        "expected_input_kind": "hostess_launch_receipt",
        "expected_output_kind": "hostess_install_launch_evidence_bundle",
    },
    {
        "plan_action_id": "manifold.platform_smoke.review_command_session_contract",
        "owner": MANIFOLD_OWNER,
        "route_kind": "manifold.review.command_session_contract",
        "action_kind": "manifold_command_session_contract_review_plan",
        "approval_kind": "operator.command_session_review_approval",
        "expected_input_kind": "hostess_smoke_review_bundle",
        "expected_output_kind": "manifold_command_session_contract_review",
    },
]

OPERATOR_START_READINESS_INPUT_CONTRACTS = [
    {
        "readiness_input_id": "hostess.operator_start.host_shell_selection",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_host_shell_selection",
        "expected_source_kind": "platform_smoke_operator_start_gate",
        "validation_kind": "host_shell_kind_review",
    },
    {
        "readiness_input_id": "hostess.operator_start.toolchain_readiness",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_toolchain_readiness",
        "expected_source_kind": "operator_supplied_toolchain_manifest",
        "validation_kind": "toolchain_paths_review",
    },
    {
        "readiness_input_id": "hostess.operator_start.device_readiness",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_device_readiness",
        "expected_source_kind": "operator_supplied_device_readiness_manifest",
        "validation_kind": "device_target_review",
    },
    {
        "readiness_input_id": "manifold.operator_start.command_session_review",
        "owner": MANIFOLD_OWNER,
        "input_kind": "manifold_command_session_readiness",
        "expected_source_kind": "manifold_command_session_contract_review",
        "validation_kind": "command_session_authority_review",
    },
    {
        "readiness_input_id": "hostess.operator_start.evidence_destination",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_evidence_destination_readiness",
        "expected_source_kind": "operator_supplied_evidence_destination_manifest",
        "validation_kind": "evidence_write_location_review",
    },
    {
        "readiness_input_id": "hostess.operator_start.rollback_plan",
        "owner": HOSTESS_OWNER,
        "input_kind": "hostess_platform_smoke_rollback_plan",
        "expected_source_kind": "operator_supplied_rollback_plan",
        "validation_kind": "rollback_or_cleanup_review",
    },
]

PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID = (
    "studio.operator_start.projected_motion_breath_shell_handoff_review"
)
PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_CONTRACT = {
    "readiness_input_id": PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID,
    "owner": STUDIO_REQUESTER,
    "input_kind": "studio_projected_motion_breath_shell_handoff_review",
    "expected_source_kind": "studio_projected_motion_breath_shell_handoff_review_report",
    "validation_kind": "projected_motion_breath_shell_handoff_review_gate",
}
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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return data


def request_relative_path(request_path: Path, raw_path: str | None) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return request_path.parent / path


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_intake_report(request: dict[str, Any], source_path: Path | None = None) -> dict[str, Any]:
    checks = request_checks(request)
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    actions = request_actions(request)
    action_ids = [action.get("action_id") for action in actions if isinstance(action.get("action_id"), str)]
    status = ACCEPTED_STATUS if not failed else REJECTED_STATUS
    issue_code = failed[0]["issue_code"] if failed else None

    return {
        "$schema": INTAKE_SCHEMA,
        "request_schema": request.get("$schema"),
        "request_path": str(source_path) if source_path else None,
        "request_id": request.get("request_id"),
        "status": status,
        "issue_code": issue_code,
        "adapter_owner": HOSTESS_OWNER,
        "requester_role": request.get("requester_role"),
        "command_session_authority": request.get("command_session_authority"),
        "install_launch_evidence_authority": request.get("install_launch_evidence_authority"),
        "studio_role": request.get("studio_role"),
        "execution_performed": False,
        "copy_stage_install_launch_evidence_started": False,
        "command_session_started": False,
        "adapter_action_count": len(actions),
        "accepted_action_ids": action_ids if status == ACCEPTED_STATUS else [],
        "rejected_action_ids": action_ids if status == REJECTED_STATUS else [],
        "required_evidence_kinds": REQUIRED_EVIDENCE_KINDS,
        "next_required_action": (
            "emit_hostess_ack_fixture"
            if status == ACCEPTED_STATUS
            else "repair_studio_staging_execution_request"
        ),
        "checks": checks,
    }


def build_ack_fixture(request: dict[str, Any]) -> dict[str, Any]:
    report = build_intake_report(request)
    if report["status"] != ACCEPTED_STATUS:
        raise ValueError(f"cannot accept rejected staging request: {report['issue_code']}")
    action_ids = expected_action_ids(request)
    return {
        "$schema": ACK_SCHEMA,
        "request_id": request.get("request_id"),
        "accepted_by": HOSTESS_OWNER,
        "ack_status": ACCEPTED_STATUS,
        "execution_in_studio": False,
        "command_session_authority": request.get("command_session_authority"),
        "install_launch_evidence_authority": request.get("install_launch_evidence_authority"),
        "required_action_ids": action_ids,
        "accepted_action_ids": action_ids,
        "required_evidence_kinds": REQUIRED_EVIDENCE_KINDS,
        "issue_code": None,
    }


def build_reject_fixture(
    request: dict[str, Any],
    reason_code: str | None = None,
) -> dict[str, Any]:
    action_ids = expected_action_ids(request)
    report = build_intake_report(request)
    issue_code = reason_code or report.get("issue_code") or "hostess.issue.staging_request_rejected"
    return {
        "$schema": REJECT_SCHEMA,
        "request_id": request.get("request_id"),
        "rejected_by": HOSTESS_OWNER,
        "reject_status": REJECTED_STATUS,
        "execution_in_studio": False,
        "request_action_ids": action_ids,
        "rejected_action_ids": action_ids,
        "reason_code": issue_code,
        "next_required_action": "repair_studio_staging_execution_request",
        "issue_code": issue_code,
    }


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


def build_platform_smoke_plan(
    bundle: dict[str, Any],
    target_platform: str = "hostess.platform_smoke.operator_controlled",
) -> dict[str, Any]:
    bundle_validation = validate_smoke_review_bundle(bundle)
    bundle_records = smoke_review_bundle_record_dicts(bundle)
    actions = platform_smoke_plan_actions(bundle, bundle_validation, bundle_records)
    approvals = platform_smoke_plan_approvals(actions)
    checks = platform_smoke_plan_checks(bundle, bundle_validation, bundle_records, actions)
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    bundle_id = bundle.get("bundle_id")
    plan_id = (
        f"hostess.platform_smoke_plan.{bundle_id}"
        if isinstance(bundle_id, str) and bundle_id
        else "hostess.platform_smoke_plan.unknown"
    )
    planned_actions = [action for action in actions if action.get("status") == PLANNED_STATUS]
    blocked_actions = [action for action in actions if action.get("status") == BLOCKED_STATUS]

    return {
        "$schema": PLATFORM_SMOKE_PLAN_SCHEMA,
        "plan_id": plan_id,
        "source_bundle_id": bundle_id,
        "source_execution_id": bundle.get("source_execution_id"),
        "preflight_id": bundle.get("preflight_id"),
        "dry_run_request_id": bundle.get("dry_run_request_id"),
        "dry_run_receipt_id": bundle.get("dry_run_receipt_id"),
        "smoke_handoff_id": bundle.get("smoke_handoff_id"),
        "source_request_id": bundle.get("source_request_id"),
        "target_profile": bundle.get("target_profile"),
        "target_platform": target_platform,
        "status": PLANNED_STATUS if not failed else BLOCKED_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_policy": PLATFORM_SMOKE_PLAN_POLICY,
        "plan_owner": HOSTESS_OWNER,
        "platform_owner": HOSTESS_OWNER,
        "bundle_owner": bundle.get("bundle_owner"),
        "reviewer_owner": bundle.get("reviewer_owner"),
        "requester_role": bundle.get("requester_role"),
        "command_session_authority": bundle.get("command_session_authority"),
        "install_launch_evidence_authority": bundle.get("install_launch_evidence_authority"),
        "studio_role": bundle.get("studio_role"),
        "host_shell_owner": bundle.get("host_shell_owner"),
        "device_required": False,
        "target_device_required_for_future_execution": True,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "operator_approval_required_before_execution": True,
        "operator_approved": False,
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
        "source_bundle_status": bundle.get("status"),
        "source_bundle_validation_status": bundle_validation.get("status"),
        "source_bundle_issue_code": bundle.get("issue_code") or bundle_validation.get("issue_code"),
        "source_bundle_record_count": len(bundle_records),
        "planned_action_count": len(actions),
        "ready_planned_action_count": len(planned_actions),
        "blocked_planned_action_count": len(blocked_actions),
        "required_approval_count": len(approvals),
        "operator_approved_count": 0,
        "source_bundle_records": bundle_records,
        "required_approvals": approvals,
        "planned_actions": actions,
        "checks": checks,
        "next_required_action": (
            "operator_approve_platform_smoke_plan_outside_studio"
            if not failed
            else "repair_hostess_smoke_review_bundle"
        ),
    }


def validate_platform_smoke_plan(plan: dict[str, Any]) -> dict[str, Any]:
    actions = platform_smoke_plan_action_dicts(plan)
    approvals = plan.get("required_approvals", [])
    if not isinstance(approvals, list):
        approvals = []
    approval_dicts = [approval for approval in approvals if isinstance(approval, dict)]
    source_records = plan.get("source_bundle_records", [])
    if not isinstance(source_records, list):
        source_records = []
    source_record_dicts = [record for record in source_records if isinstance(record, dict)]
    embedded_checks = plan.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    planned_actions = [action for action in actions if action.get("status") == PLANNED_STATUS]
    blocked_actions = [action for action in actions if action.get("status") == BLOCKED_STATUS]
    approved = [approval for approval in approval_dicts if approval.get("operator_approved") is True]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_plan.schema",
            plan.get("$schema") == PLATFORM_SMOKE_PLAN_SCHEMA,
            "platform smoke plan schema is supported",
            "platform smoke plan schema is unsupported",
            "hostess.issue.platform_smoke_plan_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.status",
            plan.get("status") in {PLANNED_STATUS, BLOCKED_STATUS},
            "platform smoke plan status is supported",
            "platform smoke plan status is unsupported",
            "hostess.issue.platform_smoke_plan_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.execution_policy",
            plan.get("execution_policy") == PLATFORM_SMOKE_PLAN_POLICY,
            "platform smoke plan is operator-controlled and plan-only",
            "platform smoke plan execution policy drifted",
            "hostess.issue.platform_smoke_plan_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.no_execution_started",
            all(plan.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and plan.get("runtime_execution_performed") is False
            and plan.get("platform_execution_performed") is False,
            "platform smoke plan has not started runtime or platform work",
            "platform smoke plan indicates runtime or platform work started",
            "hostess.issue.platform_smoke_plan_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.no_schema_path_execution",
            plan.get("device_required") is False
            and plan.get("schema_path_execution_allowed") is False
            and plan.get("platform_execution_allowed") is False
            and plan.get("studio_execution_allowed") is False,
            "platform smoke plan keeps schema path and Studio execution disabled",
            "platform smoke plan allows schema path, platform, or Studio execution",
            "hostess.issue.platform_smoke_plan_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.authority",
            plan.get("plan_owner") == HOSTESS_OWNER
            and plan.get("platform_owner") == HOSTESS_OWNER
            and plan.get("bundle_owner") == HOSTESS_OWNER
            and plan.get("reviewer_owner") == HOSTESS_OWNER
            and plan.get("requester_role") == STUDIO_REQUESTER
            and plan.get("command_session_authority") == MANIFOLD_OWNER
            and plan.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and plan.get("studio_role") == STUDIO_ROLE
            and plan.get("host_shell_owner") == HOSTESS_OWNER,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.source_bundle",
            plan.get("status") != PLANNED_STATUS
            or (
                plan.get("source_bundle_status") == REVIEWED_STATUS
                and plan.get("source_bundle_validation_status") == PASS_STATUS
            ),
            "planned source review bundle is reviewed and validates",
            "source review bundle is blocked or invalid",
            plan.get("source_bundle_issue_code") or "hostess.issue.smoke_review_bundle_not_reviewed",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.action_contracts",
            platform_smoke_plan_actions_match_contracts(actions),
            "platform smoke plan actions match Hostess and Manifold contracts",
            "platform smoke plan actions drifted",
            "hostess.issue.platform_smoke_plan_action_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.action_execution",
            all(platform_smoke_action_unstarted(action) for action in actions),
            "platform smoke plan actions have not started execution",
            "platform smoke plan action indicates execution started",
            "hostess.issue.platform_smoke_plan_action_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.approvals",
            platform_smoke_plan_approvals_match_actions(actions, approval_dicts),
            "platform smoke plan approvals match planned actions and are not approved yet",
            "platform smoke plan approvals drifted or were pre-approved",
            "hostess.issue.platform_smoke_plan_approval_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.counts",
            plan.get("source_bundle_record_count") == len(source_record_dicts)
            and plan.get("planned_action_count") == len(actions)
            and plan.get("ready_planned_action_count") == len(planned_actions)
            and plan.get("blocked_planned_action_count") == len(blocked_actions)
            and plan.get("required_approval_count") == len(approval_dicts)
            and plan.get("operator_approved_count") == len(approved),
            "platform smoke plan counts match actions and approvals",
            "platform smoke plan counts drifted",
            "hostess.issue.platform_smoke_plan_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.planned_consistency",
            plan.get("status") != PLANNED_STATUS
            or (
                all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(action.get("status") == PLANNED_STATUS for action in actions)
                and all(approval.get("operator_approved") is False for approval in approval_dicts)
            ),
            "planned platform smoke plan has passing checks, planned actions, and pending approvals",
            "planned platform smoke plan has failed checks, blocked actions, or approved actions",
            "hostess.issue.platform_smoke_plan_planned_inconsistent",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_PLAN_VALIDATION_SCHEMA,
        "plan_id": plan.get("plan_id"),
        "source_bundle_id": plan.get("source_bundle_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def platform_smoke_plan_actions(
    bundle: dict[str, Any],
    bundle_validation: dict[str, Any],
    bundle_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bundle_ready = (
        bundle.get("status") == REVIEWED_STATUS
        and bundle_validation.get("status") == PASS_STATUS
        and all(record.get("review_status") == REVIEWED_STATUS for record in bundle_records)
    )
    actions = []
    for contract in PLATFORM_SMOKE_PLAN_ACTION_CONTRACTS:
        issue_code = None
        if not bundle_ready:
            issue_code = (
                bundle.get("issue_code")
                or bundle_validation.get("issue_code")
                or first_bundle_record_issue_code(bundle_records)
                or "hostess.issue.smoke_review_bundle_not_reviewed"
            )
        actions.append(
            {
                "plan_action_id": contract["plan_action_id"],
                "owner": contract["owner"],
                "status": PLANNED_STATUS if issue_code is None else BLOCKED_STATUS,
                "issue_code": issue_code,
                "route_kind": contract["route_kind"],
                "action_kind": contract["action_kind"],
                "approval_kind": contract["approval_kind"],
                "expected_input_kind": contract["expected_input_kind"],
                "expected_output_kind": contract["expected_output_kind"],
                "approval_required": True,
                "operator_approved": False,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return actions


def platform_smoke_plan_checks(
    bundle: dict[str, Any],
    bundle_validation: dict[str, Any],
    bundle_records: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_plan.source_bundle",
            bundle.get("$schema") == SMOKE_REVIEW_BUNDLE_SCHEMA
            and bundle.get("status") == REVIEWED_STATUS
            and bundle_validation.get("status") == PASS_STATUS,
            "smoke review bundle is reviewed and validates",
            "smoke review bundle is blocked or invalid",
            bundle.get("issue_code")
            or bundle_validation.get("issue_code")
            or "hostess.issue.smoke_review_bundle_not_reviewed",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.authority",
            bundle.get("bundle_owner") == HOSTESS_OWNER
            and bundle.get("reviewer_owner") == HOSTESS_OWNER
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
            "hostess.check.studio_staging_platform_smoke_plan.no_runtime_started",
            all(bundle.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and bundle.get("runtime_execution_performed") is False
            and bundle.get("platform_execution_performed") is False,
            "smoke review bundle did not start runtime or platform work",
            "smoke review bundle indicates runtime or platform work started",
            "hostess.issue.platform_smoke_plan_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.bundle_records",
            all(record.get("review_status") == REVIEWED_STATUS for record in bundle_records),
            "source bundle records are reviewed",
            "source bundle records are blocked",
            first_bundle_record_issue_code(bundle_records)
            or "hostess.issue.smoke_review_bundle_records_blocked",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.action_contracts",
            platform_smoke_plan_actions_match_contracts(actions),
            "platform smoke plan actions match Hostess and Manifold contracts",
            "platform smoke plan actions drifted",
            "hostess.issue.platform_smoke_plan_action_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_plan.no_action_execution",
            all(platform_smoke_action_unstarted(action) for action in actions),
            "platform smoke plan actions have not started execution",
            "platform smoke plan action indicates execution started",
            "hostess.issue.platform_smoke_plan_action_started",
        ),
    ]


def platform_smoke_plan_action_dicts(plan: dict[str, Any]) -> list[dict[str, Any]]:
    actions = plan.get("planned_actions", [])
    if not isinstance(actions, list):
        return []
    return [action for action in actions if isinstance(action, dict)]


def platform_smoke_plan_actions_match_contracts(actions: list[dict[str, Any]]) -> bool:
    by_id = {action.get("plan_action_id"): action for action in actions}
    if len(actions) != len(PLATFORM_SMOKE_PLAN_ACTION_CONTRACTS):
        return False
    for contract in PLATFORM_SMOKE_PLAN_ACTION_CONTRACTS:
        action = by_id.get(contract["plan_action_id"])
        if not isinstance(action, dict):
            return False
        for key in (
            "owner",
            "route_kind",
            "action_kind",
            "approval_kind",
            "expected_input_kind",
            "expected_output_kind",
        ):
            if action.get(key) != contract[key]:
                return False
        if action.get("approval_required") is not True:
            return False
    return True


def platform_smoke_action_unstarted(action: dict[str, Any]) -> bool:
    return (
        action.get("execution_started") is False
        and action.get("runtime_execution_performed") is False
        and action.get("platform_execution_performed") is False
        and action.get("studio_execution_allowed") is False
        and action.get("command_session_started") is False
    )


def platform_smoke_plan_approvals(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    approvals = []
    for action in actions:
        action_id = action.get("plan_action_id")
        approvals.append(
            {
                "approval_id": (
                    f"hostess.platform_smoke_approval.{action_id}"
                    if isinstance(action_id, str) and action_id
                    else "hostess.platform_smoke_approval.unknown"
                ),
                "source_plan_action_id": action_id,
                "owner": HOSTESS_OWNER,
                "approval_kind": action.get("approval_kind"),
                "approval_required": True,
                "operator_approved": False,
                "execution_allowed_after_approval": True,
                "execution_started": False,
            }
        )
    return approvals


def platform_smoke_plan_approvals_match_actions(
    actions: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
) -> bool:
    by_id = {approval.get("source_plan_action_id"): approval for approval in approvals}
    if len(approvals) != len(actions):
        return False
    for action in actions:
        approval = by_id.get(action.get("plan_action_id"))
        if not isinstance(approval, dict):
            return False
        if approval.get("owner") != HOSTESS_OWNER:
            return False
        if approval.get("approval_kind") != action.get("approval_kind"):
            return False
        if approval.get("approval_required") is not True:
            return False
        if approval.get("operator_approved") is not False:
            return False
        if approval.get("execution_started") is not False:
            return False
    return True


def build_platform_smoke_approval_receipt(
    plan: dict[str, Any],
    decision: str = APPROVED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    plan_validation = validate_platform_smoke_plan(plan)
    actions = platform_smoke_plan_action_dicts(plan)
    decision_supported = decision in {APPROVED_STATUS, REJECTED_STATUS}
    plan_ready = (
        plan.get("status") == PLANNED_STATUS
        and plan_validation.get("status") == PASS_STATUS
        and all(action.get("status") == PLANNED_STATUS for action in actions)
    )
    status = APPROVED_STATUS if decision == APPROVED_STATUS and plan_ready else REJECTED_STATUS
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or plan.get("issue_code")
            or plan_validation.get("issue_code")
            or "hostess.issue.platform_smoke_approval_rejected"
        )
    receipts = platform_smoke_action_approval_receipts(plan, actions, status, issue_code)
    approved_receipts = [
        receipt for receipt in receipts if receipt.get("approval_status") == APPROVED_STATUS
    ]
    rejected_receipts = [
        receipt for receipt in receipts if receipt.get("approval_status") == REJECTED_STATUS
    ]
    checks = platform_smoke_approval_receipt_checks(
        plan,
        plan_validation,
        actions,
        receipts,
        status,
        decision_supported,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == APPROVED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        receipts = platform_smoke_action_approval_receipts(plan, actions, status, issue_code)
        approved_receipts = []
        rejected_receipts = receipts

    plan_id = plan.get("plan_id")
    receipt_id = (
        f"hostess.platform_smoke_approval_receipt.{plan_id}"
        if isinstance(plan_id, str) and plan_id
        else "hostess.platform_smoke_approval_receipt.unknown"
    )

    return {
        "$schema": PLATFORM_SMOKE_APPROVAL_RECEIPT_SCHEMA,
        "approval_receipt_id": receipt_id,
        "source_plan_id": plan_id,
        "source_bundle_id": plan.get("source_bundle_id"),
        "source_execution_id": plan.get("source_execution_id"),
        "source_request_id": plan.get("source_request_id"),
        "target_profile": plan.get("target_profile"),
        "target_platform": plan.get("target_platform"),
        "status": status,
        "approval_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_APPROVAL_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "approval_owner": HOSTESS_OWNER,
        "plan_owner": plan.get("plan_owner"),
        "platform_owner": plan.get("platform_owner"),
        "requester_role": plan.get("requester_role"),
        "command_session_authority": plan.get("command_session_authority"),
        "install_launch_evidence_authority": plan.get("install_launch_evidence_authority"),
        "studio_role": plan.get("studio_role"),
        "device_required": False,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "operator_approved": status == APPROVED_STATUS,
        "future_execution_authorized": status == APPROVED_STATUS,
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
        "source_plan_status": plan.get("status"),
        "source_plan_validation_status": plan_validation.get("status"),
        "source_plan_issue_code": plan.get("issue_code") or plan_validation.get("issue_code"),
        "source_planned_action_count": len(actions),
        "approval_receipt_count": len(receipts),
        "approved_action_count": len(approved_receipts),
        "rejected_action_count": len(rejected_receipts),
        "source_planned_actions": actions,
        "action_approval_receipts": receipts,
        "checks": checks,
        "next_required_action": (
            "hostess_operator_start_platform_smoke_outside_studio"
            if status == APPROVED_STATUS
            else "repair_or_reject_platform_smoke_plan"
        ),
    }


def validate_platform_smoke_approval_receipt(
    plan: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    plan_validation = validate_platform_smoke_plan(plan)
    actions = platform_smoke_plan_action_dicts(plan)
    receipts = platform_smoke_action_approval_receipt_dicts(receipt)
    approved_receipts = [
        item for item in receipts if item.get("approval_status") == APPROVED_STATUS
    ]
    rejected_receipts = [
        item for item in receipts if item.get("approval_status") == REJECTED_STATUS
    ]
    embedded_checks = receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.schema",
            receipt.get("$schema") == PLATFORM_SMOKE_APPROVAL_RECEIPT_SCHEMA,
            "platform smoke approval receipt schema is supported",
            "platform smoke approval receipt schema is unsupported",
            "hostess.issue.platform_smoke_approval_receipt_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.plan_id",
            receipt.get("source_plan_id") == plan.get("plan_id"),
            "platform smoke approval receipt plan id matches",
            "platform smoke approval receipt plan id differs",
            "hostess.issue.platform_smoke_approval_receipt_plan_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.status",
            receipt.get("status") in {APPROVED_STATUS, REJECTED_STATUS},
            "platform smoke approval receipt status is supported",
            "platform smoke approval receipt status is unsupported",
            "hostess.issue.platform_smoke_approval_receipt_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.execution_policy",
            receipt.get("execution_policy") == PLATFORM_SMOKE_APPROVAL_RECEIPT_POLICY,
            "platform smoke approval receipt is decision-only",
            "platform smoke approval receipt execution policy drifted",
            "hostess.issue.platform_smoke_approval_receipt_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.no_execution_started",
            all(receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and receipt.get("runtime_execution_performed") is False
            and receipt.get("platform_execution_performed") is False,
            "platform smoke approval receipt has not started runtime or platform work",
            "platform smoke approval receipt indicates runtime or platform work started",
            "hostess.issue.platform_smoke_approval_receipt_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.execution_gate",
            receipt.get("schema_path_execution_allowed") is False
            and receipt.get("platform_execution_allowed") is False
            and receipt.get("studio_execution_allowed") is False,
            "platform smoke approval receipt keeps schema path and Studio execution disabled",
            "platform smoke approval receipt allows schema path, platform, or Studio execution",
            "hostess.issue.platform_smoke_approval_receipt_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.authority",
            receipt.get("receipt_owner") == HOSTESS_OWNER
            and receipt.get("approval_owner") == HOSTESS_OWNER
            and receipt.get("plan_owner") == HOSTESS_OWNER
            and receipt.get("platform_owner") == HOSTESS_OWNER
            and receipt.get("requester_role") == STUDIO_REQUESTER
            and receipt.get("command_session_authority") == MANIFOLD_OWNER
            and receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.source_plan",
            receipt.get("status") != APPROVED_STATUS
            or (
                plan.get("status") == PLANNED_STATUS
                and plan_validation.get("status") == PASS_STATUS
            ),
            "approved source platform smoke plan is planned and validates",
            "approved source platform smoke plan is blocked or invalid",
            plan.get("issue_code")
            or plan_validation.get("issue_code")
            or "hostess.issue.platform_smoke_plan_not_planned",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.action_receipts",
            platform_smoke_action_approval_receipts_match_actions(
                actions,
                receipts,
                receipt.get("status"),
            ),
            "platform smoke approval action receipts match planned actions",
            "platform smoke approval action receipts drifted",
            "hostess.issue.platform_smoke_approval_receipt_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.counts",
            receipt.get("source_planned_action_count") == len(actions)
            and receipt.get("approval_receipt_count") == len(receipts)
            and receipt.get("approved_action_count") == len(approved_receipts)
            and receipt.get("rejected_action_count") == len(rejected_receipts),
            "platform smoke approval receipt counts match actions",
            "platform smoke approval receipt counts drifted",
            "hostess.issue.platform_smoke_approval_receipt_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.decision_consistency",
            receipt.get("status") != APPROVED_STATUS
            or (
                receipt.get("operator_approved") is True
                and receipt.get("future_execution_authorized") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(item.get("approval_status") == APPROVED_STATUS for item in receipts)
            ),
            "approved platform smoke receipt carries approved action receipts",
            "approved platform smoke receipt is inconsistent",
            "hostess.issue.platform_smoke_approval_receipt_approved_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.rejection_reason",
            receipt.get("status") != REJECTED_STATUS
            or isinstance(receipt.get("issue_code"), str),
            "rejected platform smoke receipt carries a reason code",
            "rejected platform smoke receipt is missing a reason code",
            "hostess.issue.platform_smoke_approval_receipt_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_APPROVAL_RECEIPT_VALIDATION_SCHEMA,
        "approval_receipt_id": receipt.get("approval_receipt_id"),
        "source_plan_id": receipt.get("source_plan_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def platform_smoke_action_approval_receipts(
    plan: dict[str, Any],
    actions: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    receipts = []
    for action in actions:
        action_id = action.get("plan_action_id")
        receipts.append(
            {
                "action_approval_receipt_id": (
                    f"hostess.platform_smoke_action_approval_receipt.{action_id}"
                    if isinstance(action_id, str) and action_id
                    else "hostess.platform_smoke_action_approval_receipt.unknown"
                ),
                "source_plan_id": plan.get("plan_id"),
                "source_plan_action_id": action_id,
                "owner": action.get("owner"),
                "route_kind": action.get("route_kind"),
                "action_kind": action.get("action_kind"),
                "approval_kind": action.get("approval_kind"),
                "expected_input_kind": action.get("expected_input_kind"),
                "expected_output_kind": action.get("expected_output_kind"),
                "approval_status": status,
                "issue_code": None if status == APPROVED_STATUS else issue_code,
                "operator_approved": status == APPROVED_STATUS,
                "future_execution_authorized": status == APPROVED_STATUS,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return receipts


def platform_smoke_approval_receipt_checks(
    plan: dict[str, Any],
    plan_validation: dict[str, Any],
    actions: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.source_plan",
            plan.get("$schema") == PLATFORM_SMOKE_PLAN_SCHEMA
            and plan.get("status") == PLANNED_STATUS
            and plan_validation.get("status") == PASS_STATUS,
            "platform smoke plan is planned and validates",
            "platform smoke plan is blocked or invalid",
            plan.get("issue_code")
            or plan_validation.get("issue_code")
            or "hostess.issue.platform_smoke_plan_not_planned",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.decision",
            decision_supported,
            "platform smoke approval decision is supported",
            "platform smoke approval decision is unsupported",
            "hostess.issue.platform_smoke_approval_receipt_decision",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.action_contracts",
            platform_smoke_plan_actions_match_contracts(actions),
            "platform smoke approval source actions match contracts",
            "platform smoke approval source actions drifted",
            "hostess.issue.platform_smoke_plan_action_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.action_receipts",
            platform_smoke_action_approval_receipts_match_actions(actions, receipts, status),
            "platform smoke approval receipts match source actions",
            "platform smoke approval receipts drifted",
            "hostess.issue.platform_smoke_approval_receipt_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_approval_receipt.no_action_execution",
            all(platform_smoke_approval_receipt_unstarted(receipt) for receipt in receipts),
            "platform smoke approval receipts have not started execution",
            "platform smoke approval receipt indicates execution started",
            "hostess.issue.platform_smoke_approval_receipt_action_started",
        ),
    ]


def platform_smoke_action_approval_receipt_dicts(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    receipts = receipt.get("action_approval_receipts", [])
    if not isinstance(receipts, list):
        return []
    return [item for item in receipts if isinstance(item, dict)]


def platform_smoke_action_approval_receipts_match_actions(
    actions: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {APPROVED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {receipt.get("source_plan_action_id"): receipt for receipt in receipts}
    if len(receipts) != len(actions):
        return False
    for action in actions:
        receipt = by_id.get(action.get("plan_action_id"))
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
            if receipt.get(key) != action.get(key):
                return False
        if receipt.get("approval_status") != status:
            return False
        if receipt.get("operator_approved") != (status == APPROVED_STATUS):
            return False
        if receipt.get("future_execution_authorized") != (status == APPROVED_STATUS):
            return False
        if not platform_smoke_approval_receipt_unstarted(receipt):
            return False
    return True


def platform_smoke_approval_receipt_unstarted(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("execution_started") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("command_session_started") is False
    )


def build_platform_smoke_execution_request(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
) -> dict[str, Any]:
    approval_validation = validate_platform_smoke_approval_receipt(plan, approval_receipt)
    approval_receipts = platform_smoke_action_approval_receipt_dicts(approval_receipt)
    request_ready = (
        approval_receipt.get("status") == APPROVED_STATUS
        and approval_validation.get("status") == PASS_STATUS
        and approval_receipt.get("operator_approved") is True
        and approval_receipt.get("future_execution_authorized") is True
        and all(
            receipt.get("approval_status") == APPROVED_STATUS
            and receipt.get("future_execution_authorized") is True
            for receipt in approval_receipts
        )
    )
    status = READY_STATUS if request_ready else REJECTED_STATUS
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            approval_receipt.get("issue_code")
            or approval_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_request_not_authorized"
        )
    action_requests = platform_smoke_execution_action_requests(
        approval_receipt,
        approval_receipts,
        status,
        issue_code,
    )
    pending_actions = [
        action
        for action in action_requests
        if action.get("execution_request_status") == PENDING_STATUS
    ]
    rejected_actions = [
        action
        for action in action_requests
        if action.get("execution_request_status") == REJECTED_STATUS
    ]
    checks = platform_smoke_execution_request_checks(
        plan,
        approval_receipt,
        approval_validation,
        approval_receipts,
        action_requests,
        status,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == READY_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        action_requests = platform_smoke_execution_action_requests(
            approval_receipt,
            approval_receipts,
            status,
            issue_code,
        )
        pending_actions = []
        rejected_actions = action_requests

    approval_receipt_id = approval_receipt.get("approval_receipt_id")
    request_id = (
        f"hostess.platform_smoke_execution_request.{approval_receipt_id}"
        if isinstance(approval_receipt_id, str) and approval_receipt_id
        else "hostess.platform_smoke_execution_request.unknown"
    )

    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_REQUEST_SCHEMA,
        "execution_request_id": request_id,
        "source_approval_receipt_id": approval_receipt_id,
        "source_plan_id": approval_receipt.get("source_plan_id"),
        "source_bundle_id": approval_receipt.get("source_bundle_id"),
        "source_execution_id": approval_receipt.get("source_execution_id"),
        "source_request_id": approval_receipt.get("source_request_id"),
        "target_profile": approval_receipt.get("target_profile"),
        "target_platform": approval_receipt.get("target_platform"),
        "status": status,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EXECUTION_REQUEST_POLICY,
        "request_owner": HOSTESS_OWNER,
        "execution_owner": HOSTESS_OWNER,
        "approval_owner": approval_receipt.get("approval_owner"),
        "plan_owner": approval_receipt.get("plan_owner"),
        "platform_owner": approval_receipt.get("platform_owner"),
        "requester_role": approval_receipt.get("requester_role"),
        "command_session_authority": approval_receipt.get("command_session_authority"),
        "install_launch_evidence_authority": approval_receipt.get("install_launch_evidence_authority"),
        "studio_role": approval_receipt.get("studio_role"),
        "device_required": False,
        "target_device_required_for_future_execution": status == READY_STATUS,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "operator_approved": status == READY_STATUS,
        "future_execution_authorized": status == READY_STATUS,
        "operator_controlled_execution_required": True,
        "hostess_shell_execution_required": status == READY_STATUS,
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
        "source_approval_status": approval_receipt.get("status"),
        "source_approval_validation_status": approval_validation.get("status"),
        "source_approval_issue_code": (
            approval_receipt.get("issue_code") or approval_validation.get("issue_code")
        ),
        "source_action_approval_receipt_count": len(approval_receipts),
        "execution_action_request_count": len(action_requests),
        "pending_execution_action_count": len(pending_actions),
        "rejected_execution_action_count": len(rejected_actions),
        "source_action_approval_receipts": approval_receipts,
        "execution_action_requests": action_requests,
        "checks": checks,
        "next_required_action": (
            "hostess_t_or_dedicated_host_shell_consume_execution_request_outside_studio"
            if status == READY_STATUS
            else "repair_or_reject_platform_smoke_approval_receipt"
        ),
    }


def validate_platform_smoke_execution_request(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
) -> dict[str, Any]:
    approval_validation = validate_platform_smoke_approval_receipt(plan, approval_receipt)
    approval_receipts = platform_smoke_action_approval_receipt_dicts(approval_receipt)
    action_requests = platform_smoke_execution_action_request_dicts(execution_request)
    pending_actions = [
        action
        for action in action_requests
        if action.get("execution_request_status") == PENDING_STATUS
    ]
    rejected_actions = [
        action
        for action in action_requests
        if action.get("execution_request_status") == REJECTED_STATUS
    ]
    embedded_checks = execution_request.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.schema",
            execution_request.get("$schema") == PLATFORM_SMOKE_EXECUTION_REQUEST_SCHEMA,
            "platform smoke execution request schema is supported",
            "platform smoke execution request schema is unsupported",
            "hostess.issue.platform_smoke_execution_request_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.approval_id",
            execution_request.get("source_approval_receipt_id")
            == approval_receipt.get("approval_receipt_id"),
            "platform smoke execution request approval receipt id matches",
            "platform smoke execution request approval receipt id differs",
            "hostess.issue.platform_smoke_execution_request_approval_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.status",
            execution_request.get("status") in {READY_STATUS, REJECTED_STATUS},
            "platform smoke execution request status is supported",
            "platform smoke execution request status is unsupported",
            "hostess.issue.platform_smoke_execution_request_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.execution_policy",
            execution_request.get("execution_policy") == PLATFORM_SMOKE_EXECUTION_REQUEST_POLICY,
            "platform smoke execution request is request-only",
            "platform smoke execution request execution policy drifted",
            "hostess.issue.platform_smoke_execution_request_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.no_execution_started",
            all(execution_request.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and execution_request.get("runtime_execution_performed") is False
            and execution_request.get("platform_execution_performed") is False,
            "platform smoke execution request has not started runtime or platform work",
            "platform smoke execution request indicates runtime or platform work started",
            "hostess.issue.platform_smoke_execution_request_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.execution_gate",
            execution_request.get("schema_path_execution_allowed") is False
            and execution_request.get("platform_execution_allowed") is False
            and execution_request.get("studio_execution_allowed") is False
            and execution_request.get("device_required") is False,
            "platform smoke execution request keeps schema path and Studio execution disabled",
            "platform smoke execution request allows schema path, platform, device, or Studio execution",
            "hostess.issue.platform_smoke_execution_request_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.authority",
            execution_request.get("request_owner") == HOSTESS_OWNER
            and execution_request.get("execution_owner") == HOSTESS_OWNER
            and execution_request.get("approval_owner") == HOSTESS_OWNER
            and execution_request.get("plan_owner") == HOSTESS_OWNER
            and execution_request.get("platform_owner") == HOSTESS_OWNER
            and execution_request.get("requester_role") == STUDIO_REQUESTER
            and execution_request.get("command_session_authority") == MANIFOLD_OWNER
            and execution_request.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and execution_request.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.source_approval",
            execution_request.get("status") != READY_STATUS
            or (
                approval_receipt.get("status") == APPROVED_STATUS
                and approval_validation.get("status") == PASS_STATUS
                and approval_receipt.get("future_execution_authorized") is True
            ),
            "source approval receipt is approved and validates",
            "source approval receipt is rejected or invalid",
            approval_receipt.get("issue_code")
            or approval_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_request_not_authorized",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.action_requests",
            platform_smoke_execution_action_requests_match_approvals(
                approval_receipts,
                action_requests,
                execution_request.get("status"),
            ),
            "platform smoke execution action requests match approved actions",
            "platform smoke execution action requests drifted",
            "hostess.issue.platform_smoke_execution_request_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.counts",
            execution_request.get("source_action_approval_receipt_count") == len(approval_receipts)
            and execution_request.get("execution_action_request_count") == len(action_requests)
            and execution_request.get("pending_execution_action_count") == len(pending_actions)
            and execution_request.get("rejected_execution_action_count") == len(rejected_actions),
            "platform smoke execution request counts match action requests",
            "platform smoke execution request counts drifted",
            "hostess.issue.platform_smoke_execution_request_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.ready_consistency",
            execution_request.get("status") != READY_STATUS
            or (
                execution_request.get("operator_approved") is True
                and execution_request.get("future_execution_authorized") is True
                and execution_request.get("hostess_shell_execution_required") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(
                    action.get("execution_request_status") == PENDING_STATUS
                    and action.get("execution_requested") is True
                    and action.get("execution_started") is False
                    for action in action_requests
                )
            ),
            "ready platform smoke execution request carries pending action requests",
            "ready platform smoke execution request is inconsistent",
            "hostess.issue.platform_smoke_execution_request_ready_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.rejection_reason",
            execution_request.get("status") != REJECTED_STATUS
            or isinstance(execution_request.get("issue_code"), str),
            "rejected platform smoke execution request carries a reason code",
            "rejected platform smoke execution request is missing a reason code",
            "hostess.issue.platform_smoke_execution_request_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_REQUEST_VALIDATION_SCHEMA,
        "execution_request_id": execution_request.get("execution_request_id"),
        "source_approval_receipt_id": execution_request.get("source_approval_receipt_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def build_platform_smoke_execution_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
) -> dict[str, Any]:
    request_validation = validate_platform_smoke_execution_request(
        plan,
        approval_receipt,
        execution_request,
    )
    action_requests = platform_smoke_execution_action_request_dicts(execution_request)
    status = (
        PENDING_STATUS
        if execution_request.get("status") == READY_STATUS
        and request_validation.get("status") == PASS_STATUS
        else REJECTED_STATUS
    )
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            execution_request.get("issue_code")
            or request_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_receipt_rejected"
        )
    action_receipts = platform_smoke_execution_action_receipts(
        execution_request,
        action_requests,
        status,
        issue_code,
    )
    pending_receipts = [
        receipt
        for receipt in action_receipts
        if receipt.get("execution_receipt_status") == PENDING_STATUS
    ]
    rejected_receipts = [
        receipt
        for receipt in action_receipts
        if receipt.get("execution_receipt_status") == REJECTED_STATUS
    ]
    checks = platform_smoke_execution_receipt_checks(
        execution_request,
        request_validation,
        action_requests,
        action_receipts,
        status,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == PENDING_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        action_receipts = platform_smoke_execution_action_receipts(
            execution_request,
            action_requests,
            status,
            issue_code,
        )
        pending_receipts = []
        rejected_receipts = action_receipts

    execution_request_id = execution_request.get("execution_request_id")
    receipt_id = (
        f"hostess.platform_smoke_execution_receipt.{execution_request_id}"
        if isinstance(execution_request_id, str) and execution_request_id
        else "hostess.platform_smoke_execution_receipt.unknown"
    )

    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_RECEIPT_SCHEMA,
        "execution_receipt_id": receipt_id,
        "source_execution_request_id": execution_request_id,
        "source_approval_receipt_id": execution_request.get("source_approval_receipt_id"),
        "source_plan_id": execution_request.get("source_plan_id"),
        "source_bundle_id": execution_request.get("source_bundle_id"),
        "source_execution_id": execution_request.get("source_execution_id"),
        "source_request_id": execution_request.get("source_request_id"),
        "target_profile": execution_request.get("target_profile"),
        "target_platform": execution_request.get("target_platform"),
        "status": status,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EXECUTION_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "execution_owner": HOSTESS_OWNER,
        "request_owner": execution_request.get("request_owner"),
        "platform_owner": execution_request.get("platform_owner"),
        "requester_role": execution_request.get("requester_role"),
        "command_session_authority": execution_request.get("command_session_authority"),
        "install_launch_evidence_authority": execution_request.get("install_launch_evidence_authority"),
        "studio_role": execution_request.get("studio_role"),
        "device_required": False,
        "target_device_required_for_future_execution": status == PENDING_STATUS,
        "schema_path_execution_allowed": False,
        "platform_execution_allowed": False,
        "studio_execution_allowed": False,
        "operator_approved": status == PENDING_STATUS,
        "execution_acknowledged": status == PENDING_STATUS,
        "operator_controlled_execution_required": True,
        "hostess_shell_execution_required": status == PENDING_STATUS,
        "schema_checks_performed": True,
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
        "source_execution_request_status": execution_request.get("status"),
        "source_execution_request_validation_status": request_validation.get("status"),
        "source_execution_request_issue_code": (
            execution_request.get("issue_code") or request_validation.get("issue_code")
        ),
        "source_execution_action_request_count": len(action_requests),
        "execution_action_receipt_count": len(action_receipts),
        "pending_execution_action_count": len(pending_receipts),
        "rejected_execution_action_count": len(rejected_receipts),
        "source_execution_action_requests": action_requests,
        "execution_action_receipts": action_receipts,
        "checks": checks,
        "next_required_action": (
            "hostess_operator_start_platform_smoke_in_host_shell"
            if status == PENDING_STATUS
            else "repair_or_reject_platform_smoke_execution_request"
        ),
    }


def validate_platform_smoke_execution_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
) -> dict[str, Any]:
    request_validation = validate_platform_smoke_execution_request(
        plan,
        approval_receipt,
        execution_request,
    )
    action_requests = platform_smoke_execution_action_request_dicts(execution_request)
    action_receipts = platform_smoke_execution_action_receipt_dicts(execution_receipt)
    pending_receipts = [
        receipt
        for receipt in action_receipts
        if receipt.get("execution_receipt_status") == PENDING_STATUS
    ]
    rejected_receipts = [
        receipt
        for receipt in action_receipts
        if receipt.get("execution_receipt_status") == REJECTED_STATUS
    ]
    embedded_checks = execution_receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.schema",
            execution_receipt.get("$schema") == PLATFORM_SMOKE_EXECUTION_RECEIPT_SCHEMA,
            "platform smoke execution receipt schema is supported",
            "platform smoke execution receipt schema is unsupported",
            "hostess.issue.platform_smoke_execution_receipt_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.request_id",
            execution_receipt.get("source_execution_request_id")
            == execution_request.get("execution_request_id"),
            "platform smoke execution receipt request id matches",
            "platform smoke execution receipt request id differs",
            "hostess.issue.platform_smoke_execution_receipt_request_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.status",
            execution_receipt.get("status") in {PENDING_STATUS, REJECTED_STATUS},
            "platform smoke execution receipt status is supported",
            "platform smoke execution receipt status is unsupported",
            "hostess.issue.platform_smoke_execution_receipt_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.execution_policy",
            execution_receipt.get("execution_policy") == PLATFORM_SMOKE_EXECUTION_RECEIPT_POLICY,
            "platform smoke execution receipt is receipt-only",
            "platform smoke execution receipt execution policy drifted",
            "hostess.issue.platform_smoke_execution_receipt_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.no_execution_started",
            all(execution_receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and execution_receipt.get("runtime_execution_performed") is False
            and execution_receipt.get("platform_execution_performed") is False,
            "platform smoke execution receipt has not started runtime or platform work",
            "platform smoke execution receipt indicates runtime or platform work started",
            "hostess.issue.platform_smoke_execution_receipt_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.execution_gate",
            execution_receipt.get("schema_path_execution_allowed") is False
            and execution_receipt.get("platform_execution_allowed") is False
            and execution_receipt.get("studio_execution_allowed") is False
            and execution_receipt.get("device_required") is False,
            "platform smoke execution receipt keeps schema path and Studio execution disabled",
            "platform smoke execution receipt allows schema path, platform, device, or Studio execution",
            "hostess.issue.platform_smoke_execution_receipt_execution_gate",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.authority",
            execution_receipt.get("receipt_owner") == HOSTESS_OWNER
            and execution_receipt.get("execution_owner") == HOSTESS_OWNER
            and execution_receipt.get("request_owner") == HOSTESS_OWNER
            and execution_receipt.get("platform_owner") == HOSTESS_OWNER
            and execution_receipt.get("requester_role") == STUDIO_REQUESTER
            and execution_receipt.get("command_session_authority") == MANIFOLD_OWNER
            and execution_receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and execution_receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.source_request",
            execution_receipt.get("status") != PENDING_STATUS
            or (
                execution_request.get("status") == READY_STATUS
                and request_validation.get("status") == PASS_STATUS
            ),
            "source platform smoke execution request is ready and validates",
            "source platform smoke execution request is rejected or invalid",
            execution_request.get("issue_code")
            or request_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_receipt_request_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.action_receipts",
            platform_smoke_execution_action_receipts_match_requests(
                action_requests,
                action_receipts,
                execution_receipt.get("status"),
            ),
            "platform smoke execution action receipts match request actions",
            "platform smoke execution action receipts drifted",
            "hostess.issue.platform_smoke_execution_receipt_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.counts",
            execution_receipt.get("source_execution_action_request_count") == len(action_requests)
            and execution_receipt.get("execution_action_receipt_count") == len(action_receipts)
            and execution_receipt.get("pending_execution_action_count") == len(pending_receipts)
            and execution_receipt.get("rejected_execution_action_count") == len(rejected_receipts),
            "platform smoke execution receipt counts match action receipts",
            "platform smoke execution receipt counts drifted",
            "hostess.issue.platform_smoke_execution_receipt_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.pending_consistency",
            execution_receipt.get("status") != PENDING_STATUS
            or (
                execution_receipt.get("operator_approved") is True
                and execution_receipt.get("execution_acknowledged") is True
                and execution_receipt.get("hostess_shell_execution_required") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(
                    receipt.get("execution_receipt_status") == PENDING_STATUS
                    and receipt.get("execution_acknowledged") is True
                    and receipt.get("execution_started") is False
                    for receipt in action_receipts
                )
            ),
            "pending platform smoke execution receipt carries acknowledged pending action receipts",
            "pending platform smoke execution receipt is inconsistent",
            "hostess.issue.platform_smoke_execution_receipt_pending_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.rejection_reason",
            execution_receipt.get("status") != REJECTED_STATUS
            or isinstance(execution_receipt.get("issue_code"), str),
            "rejected platform smoke execution receipt carries a reason code",
            "rejected platform smoke execution receipt is missing a reason code",
            "hostess.issue.platform_smoke_execution_receipt_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_RECEIPT_VALIDATION_SCHEMA,
        "execution_receipt_id": execution_receipt.get("execution_receipt_id"),
        "source_execution_request_id": execution_receipt.get("source_execution_request_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "checks": checks,
    }


def platform_smoke_execution_action_requests(
    approval_receipt: dict[str, Any],
    approval_receipts: list[dict[str, Any]],
    request_status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    action_status = PENDING_STATUS if request_status == READY_STATUS else REJECTED_STATUS
    requests = []
    for receipt in approval_receipts:
        source_receipt_id = receipt.get("action_approval_receipt_id")
        source_plan_action_id = receipt.get("source_plan_action_id")
        requests.append(
            {
                "action_request_id": (
                    f"hostess.platform_smoke_execution_action_request.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_execution_action_request.unknown"
                ),
                "source_approval_receipt_id": approval_receipt.get("approval_receipt_id"),
                "source_action_approval_receipt_id": source_receipt_id,
                "source_plan_id": receipt.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": receipt.get("owner"),
                "route_kind": receipt.get("route_kind"),
                "action_kind": receipt.get("action_kind"),
                "approval_kind": receipt.get("approval_kind"),
                "expected_input_kind": receipt.get("expected_input_kind"),
                "expected_output_kind": receipt.get("expected_output_kind"),
                "execution_request_status": action_status,
                "issue_code": None if action_status == PENDING_STATUS else issue_code,
                "operator_approved": action_status == PENDING_STATUS,
                "future_execution_authorized": action_status == PENDING_STATUS,
                "hostess_shell_execution_required": action_status == PENDING_STATUS,
                "execution_requested": action_status == PENDING_STATUS,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return requests


def platform_smoke_execution_request_checks(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    approval_validation: dict[str, Any],
    approval_receipts: list[dict[str, Any]],
    action_requests: list[dict[str, Any]],
    request_status: str,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.source_approval",
            approval_receipt.get("$schema") == PLATFORM_SMOKE_APPROVAL_RECEIPT_SCHEMA
            and approval_receipt.get("source_plan_id") == plan.get("plan_id")
            and approval_receipt.get("status") == APPROVED_STATUS
            and approval_validation.get("status") == PASS_STATUS,
            "platform smoke approval receipt is approved and validates",
            "platform smoke approval receipt is rejected or invalid",
            approval_receipt.get("issue_code")
            or approval_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_request_not_authorized",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.action_approvals",
            platform_smoke_action_approval_receipts_match_actions(
                platform_smoke_plan_action_dicts(plan),
                approval_receipts,
                APPROVED_STATUS,
            ),
            "platform smoke approval actions match planned actions",
            "platform smoke approval actions drifted",
            "hostess.issue.platform_smoke_execution_request_approval_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.action_requests",
            platform_smoke_execution_action_requests_match_approvals(
                approval_receipts,
                action_requests,
                request_status,
            ),
            "platform smoke execution requests match approved actions",
            "platform smoke execution requests drifted",
            "hostess.issue.platform_smoke_execution_request_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_request.no_action_execution",
            all(platform_smoke_execution_action_request_unstarted(action) for action in action_requests),
            "platform smoke execution action requests have not started execution",
            "platform smoke execution action request indicates execution started",
            "hostess.issue.platform_smoke_execution_request_action_started",
        ),
    ]


def platform_smoke_execution_action_request_dicts(
    execution_request: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = execution_request.get("execution_action_requests", [])
    if not isinstance(requests, list):
        return []
    return [item for item in requests if isinstance(item, dict)]


def platform_smoke_execution_action_requests_match_approvals(
    approval_receipts: list[dict[str, Any]],
    action_requests: list[dict[str, Any]],
    request_status: Any,
) -> bool:
    if request_status not in {READY_STATUS, REJECTED_STATUS}:
        return False
    expected_status = PENDING_STATUS if request_status == READY_STATUS else REJECTED_STATUS
    by_id = {
        request.get("source_action_approval_receipt_id"): request
        for request in action_requests
    }
    if len(action_requests) != len(approval_receipts):
        return False
    for receipt in approval_receipts:
        request = by_id.get(receipt.get("action_approval_receipt_id"))
        if not isinstance(request, dict):
            return False
        for key in (
            "owner",
            "route_kind",
            "action_kind",
            "approval_kind",
            "expected_input_kind",
            "expected_output_kind",
        ):
            if request.get(key) != receipt.get(key):
                return False
        if request.get("source_plan_action_id") != receipt.get("source_plan_action_id"):
            return False
        if request.get("execution_request_status") != expected_status:
            return False
        if request.get("operator_approved") != (expected_status == PENDING_STATUS):
            return False
        if request.get("future_execution_authorized") != (expected_status == PENDING_STATUS):
            return False
        if request.get("execution_requested") != (expected_status == PENDING_STATUS):
            return False
        if request.get("hostess_shell_execution_required") != (expected_status == PENDING_STATUS):
            return False
        if not platform_smoke_execution_action_request_unstarted(request):
            return False
    return True


def platform_smoke_execution_action_request_unstarted(action: dict[str, Any]) -> bool:
    return (
        action.get("execution_started") is False
        and action.get("runtime_execution_performed") is False
        and action.get("platform_execution_performed") is False
        and action.get("studio_execution_allowed") is False
        and action.get("command_session_started") is False
    )


def platform_smoke_execution_action_receipts(
    execution_request: dict[str, Any],
    action_requests: list[dict[str, Any]],
    receipt_status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    receipts = []
    for request in action_requests:
        source_request_id = request.get("action_request_id")
        source_plan_action_id = request.get("source_plan_action_id")
        receipts.append(
            {
                "action_execution_receipt_id": (
                    f"hostess.platform_smoke_execution_action_receipt.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_execution_action_receipt.unknown"
                ),
                "source_execution_request_id": execution_request.get("execution_request_id"),
                "source_action_request_id": source_request_id,
                "source_plan_id": request.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": request.get("owner"),
                "route_kind": request.get("route_kind"),
                "action_kind": request.get("action_kind"),
                "approval_kind": request.get("approval_kind"),
                "expected_input_kind": request.get("expected_input_kind"),
                "expected_output_kind": request.get("expected_output_kind"),
                "execution_receipt_status": receipt_status,
                "issue_code": None if receipt_status == PENDING_STATUS else issue_code,
                "operator_approved": receipt_status == PENDING_STATUS,
                "execution_acknowledged": receipt_status == PENDING_STATUS,
                "hostess_shell_execution_required": receipt_status == PENDING_STATUS,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "studio_execution_allowed": False,
                "command_session_started": False,
            }
        )
    return receipts


def platform_smoke_execution_receipt_checks(
    execution_request: dict[str, Any],
    request_validation: dict[str, Any],
    action_requests: list[dict[str, Any]],
    action_receipts: list[dict[str, Any]],
    receipt_status: str,
) -> list[dict[str, Any]]:
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.source_request",
            execution_request.get("$schema") == PLATFORM_SMOKE_EXECUTION_REQUEST_SCHEMA
            and execution_request.get("status") == READY_STATUS
            and request_validation.get("status") == PASS_STATUS,
            "platform smoke execution request is ready and validates",
            "platform smoke execution request is rejected or invalid",
            execution_request.get("issue_code")
            or request_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_receipt_request_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.action_requests",
            all(
                action.get("execution_request_status") == PENDING_STATUS
                and platform_smoke_execution_action_request_unstarted(action)
                for action in action_requests
            ),
            "platform smoke execution action requests are pending and unstarted",
            "platform smoke execution action requests are rejected, drifted, or started",
            "hostess.issue.platform_smoke_execution_receipt_request_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.action_receipts",
            platform_smoke_execution_action_receipts_match_requests(
                action_requests,
                action_receipts,
                receipt_status,
            ),
            "platform smoke execution action receipts match source requests",
            "platform smoke execution action receipts drifted",
            "hostess.issue.platform_smoke_execution_receipt_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_receipt.no_action_execution",
            all(platform_smoke_execution_action_receipt_unstarted(receipt) for receipt in action_receipts),
            "platform smoke execution action receipts have not started execution",
            "platform smoke execution action receipt indicates execution started",
            "hostess.issue.platform_smoke_execution_receipt_action_started",
        ),
    ]


def platform_smoke_execution_action_receipt_dicts(
    execution_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    receipts = execution_receipt.get("execution_action_receipts", [])
    if not isinstance(receipts, list):
        return []
    return [item for item in receipts if isinstance(item, dict)]


def platform_smoke_execution_action_receipts_match_requests(
    action_requests: list[dict[str, Any]],
    action_receipts: list[dict[str, Any]],
    receipt_status: Any,
) -> bool:
    if receipt_status not in {PENDING_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        receipt.get("source_action_request_id"): receipt
        for receipt in action_receipts
    }
    if len(action_receipts) != len(action_requests):
        return False
    for request in action_requests:
        receipt = by_id.get(request.get("action_request_id"))
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
            if receipt.get(key) != request.get(key):
                return False
        if receipt.get("source_plan_action_id") != request.get("source_plan_action_id"):
            return False
        if receipt.get("execution_receipt_status") != receipt_status:
            return False
        if receipt.get("operator_approved") != (receipt_status == PENDING_STATUS):
            return False
        if receipt.get("execution_acknowledged") != (receipt_status == PENDING_STATUS):
            return False
        if receipt.get("hostess_shell_execution_required") != (receipt_status == PENDING_STATUS):
            return False
        if not platform_smoke_execution_action_receipt_unstarted(receipt):
            return False
    return True


def platform_smoke_execution_action_receipt_unstarted(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("execution_started") is False
        and receipt.get("runtime_execution_performed") is False
        and receipt.get("platform_execution_performed") is False
        and receipt.get("studio_execution_allowed") is False
        and receipt.get("command_session_started") is False
    )


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


def pmb_shell_handoff_review_is_required(
    pmb_shell_handoff_review: dict[str, Any] | None,
    require_pmb_shell_handoff_review: bool,
) -> bool:
    return require_pmb_shell_handoff_review or pmb_shell_handoff_review is not None


def pmb_shell_handoff_review_issue_code(
    pmb_shell_handoff_review: dict[str, Any] | None,
    required: bool,
) -> str | None:
    if not required:
        return None
    if not isinstance(pmb_shell_handoff_review, dict):
        return "hostess.issue.pmb_shell_handoff_review_missing"
    if pmb_shell_handoff_review.get("$schema") != STUDIO_PMB_SHELL_HANDOFF_REVIEW_SCHEMA:
        return "hostess.issue.pmb_shell_handoff_review_schema"
    if (
        pmb_shell_handoff_review.get("status") != READY_STATUS
        or pmb_shell_handoff_review.get("issue_code") is not None
    ):
        review_issue = pmb_shell_handoff_review.get("issue_code")
        return (
            review_issue
            if isinstance(review_issue, str)
            else "hostess.issue.pmb_shell_handoff_review_not_ready"
        )
    if pmb_shell_handoff_review.get("execution_policy") != "not_executed.review_only":
        return "hostess.issue.pmb_shell_handoff_review_execution_policy"
    if (
        pmb_shell_handoff_review.get("runtime_authority") != MANIFOLD_OWNER
        or pmb_shell_handoff_review.get("authoring_authority") != STUDIO_REQUESTER
        or pmb_shell_handoff_review.get("platform_validation_authority") != HOSTESS_OWNER
    ):
        return "hostess.issue.pmb_shell_handoff_review_authority_mismatch"
    if (
        pmb_shell_handoff_review.get("runtime_execution_performed") is not False
        or pmb_shell_handoff_review.get("platform_execution_performed") is not False
        or pmb_shell_handoff_review.get("broker_transport_used") is not False
        or pmb_shell_handoff_review.get("downstream_shell_runtime_used") is not False
        or pmb_shell_handoff_review.get("legacy_app_dependency_used") is not False
    ):
        return "hostess.issue.pmb_shell_handoff_review_execution_started"
    required_binding_count = pmb_shell_handoff_review.get("required_binding_count")
    ready_binding_count = pmb_shell_handoff_review.get("ready_required_binding_count")
    if (
        not isinstance(required_binding_count, int)
        or required_binding_count <= 0
        or ready_binding_count != required_binding_count
    ):
        return "hostess.issue.pmb_shell_handoff_review_binding_gap"
    if (
        pmb_shell_handoff_review.get("feedback_receipt_exported") is not True
        or pmb_shell_handoff_review.get("feedback_sink_provides_receipt") is not True
    ):
        return "hostess.issue.pmb_shell_handoff_review_feedback_receipt"
    command_ids = pmb_shell_handoff_review.get("command_ids", [])
    transport_ids = pmb_shell_handoff_review.get("transport_ids", [])
    if not isinstance(command_ids, list) or "command.breath.status" not in command_ids:
        return "hostess.issue.pmb_shell_handoff_review_command_missing"
    if not isinstance(transport_ids, list) or not transport_ids:
        return "hostess.issue.pmb_shell_handoff_review_transport_missing"
    return None


def pmb_shell_handoff_review_summary(
    pmb_shell_handoff_review: dict[str, Any] | None,
    source_path: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(pmb_shell_handoff_review, dict):
        return {
            "source_pmb_shell_handoff_review_path": str(source_path) if source_path else None,
            "source_pmb_shell_handoff_review_schema": None,
            "source_pmb_shell_handoff_review_status": None,
            "source_pmb_shell_handoff_review_issue_code": None,
            "source_pmb_shell_handoff_id": None,
            "source_pmb_shell_app_id": None,
        }
    return {
        "source_pmb_shell_handoff_review_path": str(source_path) if source_path else None,
        "source_pmb_shell_handoff_review_schema": pmb_shell_handoff_review.get("$schema"),
        "source_pmb_shell_handoff_review_status": pmb_shell_handoff_review.get("status"),
        "source_pmb_shell_handoff_review_issue_code": pmb_shell_handoff_review.get("issue_code"),
        "source_pmb_shell_handoff_id": pmb_shell_handoff_review.get("handoff_id"),
        "source_pmb_shell_app_id": pmb_shell_handoff_review.get("shell_app_id"),
        "source_pmb_runtime_authority": pmb_shell_handoff_review.get("runtime_authority"),
        "source_pmb_authoring_authority": pmb_shell_handoff_review.get("authoring_authority"),
        "source_pmb_platform_validation_authority": pmb_shell_handoff_review.get(
            "platform_validation_authority"
        ),
        "source_pmb_execution_policy": pmb_shell_handoff_review.get("execution_policy"),
        "source_pmb_runtime_execution_performed": pmb_shell_handoff_review.get(
            "runtime_execution_performed"
        ),
        "source_pmb_platform_execution_performed": pmb_shell_handoff_review.get(
            "platform_execution_performed"
        ),
        "source_pmb_broker_transport_used": pmb_shell_handoff_review.get(
            "broker_transport_used"
        ),
        "source_pmb_downstream_shell_runtime_used": pmb_shell_handoff_review.get(
            "downstream_shell_runtime_used"
        ),
        "source_pmb_legacy_app_dependency_used": pmb_shell_handoff_review.get(
            "legacy_app_dependency_used"
        ),
        "source_pmb_required_binding_count": pmb_shell_handoff_review.get(
            "required_binding_count"
        ),
        "source_pmb_ready_required_binding_count": pmb_shell_handoff_review.get(
            "ready_required_binding_count"
        ),
        "source_pmb_feedback_receipt_exported": pmb_shell_handoff_review.get(
            "feedback_receipt_exported"
        ),
        "source_pmb_feedback_sink_provides_receipt": pmb_shell_handoff_review.get(
            "feedback_sink_provides_receipt"
        ),
        "source_pmb_command_ids": pmb_shell_handoff_review.get("command_ids"),
        "source_pmb_transport_ids": pmb_shell_handoff_review.get("transport_ids"),
    }


def pmb_shell_handoff_readiness_input_summary_valid(item: dict[str, Any]) -> bool:
    if item.get("source_pmb_shell_handoff_review_schema") != STUDIO_PMB_SHELL_HANDOFF_REVIEW_SCHEMA:
        return False
    if item.get("source_pmb_shell_handoff_review_status") != READY_STATUS:
        return False
    if item.get("source_pmb_shell_handoff_review_issue_code") is not None:
        return False
    if (
        item.get("source_pmb_runtime_authority") != MANIFOLD_OWNER
        or item.get("source_pmb_authoring_authority") != STUDIO_REQUESTER
        or item.get("source_pmb_platform_validation_authority") != HOSTESS_OWNER
    ):
        return False
    if (
        item.get("source_pmb_runtime_execution_performed") is not False
        or item.get("source_pmb_platform_execution_performed") is not False
        or item.get("source_pmb_broker_transport_used") is not False
        or item.get("source_pmb_downstream_shell_runtime_used") is not False
        or item.get("source_pmb_legacy_app_dependency_used") is not False
    ):
        return False
    required_count = item.get("source_pmb_required_binding_count")
    ready_count = item.get("source_pmb_ready_required_binding_count")
    if not isinstance(required_count, int) or required_count <= 0 or ready_count != required_count:
        return False
    if (
        item.get("source_pmb_feedback_receipt_exported") is not True
        or item.get("source_pmb_feedback_sink_provides_receipt") is not True
    ):
        return False
    command_ids = item.get("source_pmb_command_ids")
    transport_ids = item.get("source_pmb_transport_ids")
    return (
        isinstance(command_ids, list)
        and "command.breath.status" in command_ids
        and isinstance(transport_ids, list)
        and len(transport_ids) > 0
    )


def pmb_shell_handoff_review_summary_from_source(
    source: dict[str, Any],
) -> dict[str, Any]:
    return {key: source.get(key) for key in PMB_SHELL_HANDOFF_REVIEW_SUMMARY_KEYS}


def pmb_shell_handoff_readiness_result_summary_valid(item: dict[str, Any]) -> bool:
    return pmb_shell_handoff_readiness_input_summary_valid(item)


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


def build_platform_smoke_execution_report(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    outcome: str = COMPLETED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    preflight_validation = validate_platform_smoke_operator_start_preflight_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
    )
    action_receipts = platform_smoke_operator_start_action_decision_receipt_dicts(
        operator_start_preflight
    )
    readiness_inputs = platform_smoke_operator_start_readiness_input_dicts(
        operator_start_preflight
    )
    outcome_supported = outcome in {COMPLETED_STATUS, REJECTED_STATUS}
    preflight_approved = (
        operator_start_preflight.get("status") == APPROVED_STATUS
        and preflight_validation.get("status") == PASS_STATUS
        and operator_start_preflight.get("operator_start_preflight_approved") is True
        and all(
            receipt.get("decision_status") == APPROVED_STATUS
            for receipt in action_receipts
        )
        and all(
            item.get("readiness_status") == APPROVED_STATUS
            for item in readiness_inputs
        )
    )
    status = (
        COMPLETED_STATUS
        if outcome == COMPLETED_STATUS and preflight_approved
        else REJECTED_STATUS
    )
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or operator_start_preflight.get("issue_code")
            or preflight_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_report_rejected"
        )
    action_reports = platform_smoke_execution_report_action_reports(
        operator_start_preflight,
        action_receipts,
        status,
        issue_code,
    )
    readiness_results = platform_smoke_execution_report_readiness_results(
        operator_start_preflight,
        readiness_inputs,
        status,
        issue_code,
    )
    evidence_placeholders = platform_smoke_execution_report_evidence_placeholders(
        action_reports,
        status,
        issue_code,
    )
    completed_actions = [
        item for item in action_reports if item.get("reported_status") == COMPLETED_STATUS
    ]
    rejected_actions = [
        item for item in action_reports if item.get("reported_status") == REJECTED_STATUS
    ]
    completed_readiness = [
        item for item in readiness_results if item.get("result_status") == COMPLETED_STATUS
    ]
    rejected_readiness = [
        item for item in readiness_results if item.get("result_status") == REJECTED_STATUS
    ]
    pending_placeholders = [
        item
        for item in evidence_placeholders
        if item.get("evidence_status") == PENDING_STATUS
    ]
    checks = platform_smoke_execution_report_checks(
        operator_start_preflight,
        preflight_validation,
        action_receipts,
        readiness_inputs,
        action_reports,
        readiness_results,
        evidence_placeholders,
        status,
        outcome_supported,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == COMPLETED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        action_reports = platform_smoke_execution_report_action_reports(
            operator_start_preflight,
            action_receipts,
            status,
            issue_code,
        )
        readiness_results = platform_smoke_execution_report_readiness_results(
            operator_start_preflight,
            readiness_inputs,
            status,
            issue_code,
        )
        evidence_placeholders = platform_smoke_execution_report_evidence_placeholders(
            action_reports,
            status,
            issue_code,
        )
        completed_actions = []
        rejected_actions = action_reports
        completed_readiness = []
        rejected_readiness = readiness_results
        pending_placeholders = evidence_placeholders

    preflight_id = operator_start_preflight.get("operator_start_preflight_receipt_id")
    report_id = (
        f"hostess.platform_smoke_execution_report.{preflight_id}"
        if isinstance(preflight_id, str) and preflight_id
        else "hostess.platform_smoke_execution_report.unknown"
    )
    pmb_review_required = (
        operator_start_preflight.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        operator_start_preflight.get("pmb_shell_handoff_review_ready") is True
    )

    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_REPORT_SCHEMA,
        "execution_report_id": report_id,
        "source_operator_start_preflight_receipt_id": preflight_id,
        "source_operator_start_gate_id": operator_start_preflight.get("source_operator_start_gate_id"),
        "source_execution_receipt_id": operator_start_preflight.get("source_execution_receipt_id"),
        "source_execution_request_id": operator_start_preflight.get("source_execution_request_id"),
        "source_approval_receipt_id": operator_start_preflight.get("source_approval_receipt_id"),
        "source_plan_id": operator_start_preflight.get("source_plan_id"),
        "source_bundle_id": operator_start_preflight.get("source_bundle_id"),
        "source_execution_id": operator_start_preflight.get("source_execution_id"),
        "source_request_id": operator_start_preflight.get("source_request_id"),
        "target_profile": operator_start_preflight.get("target_profile"),
        "target_platform": operator_start_preflight.get("target_platform"),
        "host_shell_kind": operator_start_preflight.get("host_shell_kind"),
        "status": status,
        "reported_outcome": outcome if outcome_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EXECUTION_REPORT_POLICY,
        "report_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": operator_start_preflight.get("host_shell_owner"),
        "platform_owner": operator_start_preflight.get("platform_owner"),
        "requester_role": operator_start_preflight.get("requester_role"),
        "command_session_authority": operator_start_preflight.get("command_session_authority"),
        "install_launch_evidence_authority": operator_start_preflight.get("install_launch_evidence_authority"),
        "studio_role": operator_start_preflight.get("studio_role"),
        "device_required": False,
        "target_device_required_for_external_execution": status == COMPLETED_STATUS,
        "operator_start_preflight_approved": status == COMPLETED_STATUS,
        "operator_started_outside_studio": status == COMPLETED_STATUS,
        "operator_start_acknowledged": status == COMPLETED_STATUS,
        "host_shell_started_outside_studio": status == COMPLETED_STATUS,
        "host_shell_reported": status == COMPLETED_STATUS,
        "real_platform_execution_evidence_attached": False,
        "requires_external_evidence": True,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(operator_start_preflight),
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
        "source_operator_start_preflight_status": operator_start_preflight.get("status"),
        "source_operator_start_preflight_validation_status": preflight_validation.get("status"),
        "source_operator_start_preflight_issue_code": (
            operator_start_preflight.get("issue_code") or preflight_validation.get("issue_code")
        ),
        "source_operator_start_action_decision_receipt_count": len(action_receipts),
        "action_report_count": len(action_reports),
        "completed_action_report_count": len(completed_actions),
        "rejected_action_report_count": len(rejected_actions),
        "readiness_input_count": len(readiness_inputs),
        "readiness_result_count": len(readiness_results),
        "completed_readiness_result_count": len(completed_readiness),
        "rejected_readiness_result_count": len(rejected_readiness),
        "evidence_placeholder_count": len(evidence_placeholders),
        "pending_evidence_placeholder_count": len(pending_placeholders),
        "source_operator_start_action_decision_receipts": action_receipts,
        "source_readiness_inputs": readiness_inputs,
        "action_reports": action_reports,
        "readiness_results": readiness_results,
        "evidence_placeholders": evidence_placeholders,
        "checks": checks,
        "next_required_action": (
            "attach_hostess_platform_smoke_evidence_outside_studio"
            if status == COMPLETED_STATUS
            else "repair_or_decline_platform_smoke_execution_report"
        ),
    }


def validate_platform_smoke_execution_report(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
) -> dict[str, Any]:
    preflight_validation = validate_platform_smoke_operator_start_preflight_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
    )
    action_receipts = platform_smoke_operator_start_action_decision_receipt_dicts(
        operator_start_preflight
    )
    readiness_inputs = platform_smoke_operator_start_readiness_input_dicts(
        operator_start_preflight
    )
    action_reports = platform_smoke_execution_report_action_report_dicts(execution_report)
    readiness_results = platform_smoke_execution_report_readiness_result_dicts(
        execution_report
    )
    evidence_placeholders = platform_smoke_execution_report_evidence_placeholder_dicts(
        execution_report
    )
    completed_actions = [
        item for item in action_reports if item.get("reported_status") == COMPLETED_STATUS
    ]
    rejected_actions = [
        item for item in action_reports if item.get("reported_status") == REJECTED_STATUS
    ]
    completed_readiness = [
        item for item in readiness_results if item.get("result_status") == COMPLETED_STATUS
    ]
    rejected_readiness = [
        item for item in readiness_results if item.get("result_status") == REJECTED_STATUS
    ]
    pending_placeholders = [
        item
        for item in evidence_placeholders
        if item.get("evidence_status") == PENDING_STATUS
    ]
    embedded_checks = execution_report.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    pmb_review_required = (
        operator_start_preflight.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_result = next(
        (
            item
            for item in readiness_results
            if item.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    pmb_review_summary_matches_preflight = (
        pmb_shell_handoff_review_summary_from_source(execution_report)
        == pmb_shell_handoff_review_summary_from_source(operator_start_preflight)
    )
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.schema",
            execution_report.get("$schema") == PLATFORM_SMOKE_EXECUTION_REPORT_SCHEMA,
            "platform smoke execution report schema is supported",
            "platform smoke execution report schema is unsupported",
            "hostess.issue.platform_smoke_execution_report_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.preflight_id",
            execution_report.get("source_operator_start_preflight_receipt_id")
            == operator_start_preflight.get("operator_start_preflight_receipt_id"),
            "platform smoke execution report preflight id matches",
            "platform smoke execution report preflight id differs",
            "hostess.issue.platform_smoke_execution_report_preflight_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.status",
            execution_report.get("status") in {COMPLETED_STATUS, REJECTED_STATUS},
            "platform smoke execution report status is supported",
            "platform smoke execution report status is unsupported",
            "hostess.issue.platform_smoke_execution_report_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.execution_policy",
            execution_report.get("execution_policy") == PLATFORM_SMOKE_EXECUTION_REPORT_POLICY,
            "platform smoke execution report is report-only",
            "platform smoke execution report execution policy drifted",
            "hostess.issue.platform_smoke_execution_report_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.schema_path_boundary",
            all(execution_report.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and execution_report.get("runtime_execution_performed") is False
            and execution_report.get("platform_execution_performed") is False
            and execution_report.get("schema_path_execution_allowed") is False
            and execution_report.get("platform_execution_allowed") is False
            and execution_report.get("studio_execution_allowed") is False
            and execution_report.get("device_required") is False
            and execution_report.get("real_platform_execution_evidence_attached") is False,
            "platform smoke execution report keeps Studio, schema path, runtime, and evidence execution disabled",
            "platform smoke execution report indicates Studio, schema path, runtime, or evidence execution",
            "hostess.issue.platform_smoke_execution_report_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.authority",
            execution_report.get("report_owner") == HOSTESS_OWNER
            and execution_report.get("operator_start_owner") == HOSTESS_OWNER
            and execution_report.get("host_shell_owner") == HOSTESS_OWNER
            and execution_report.get("platform_owner") == HOSTESS_OWNER
            and execution_report.get("requester_role") == STUDIO_REQUESTER
            and execution_report.get("command_session_authority") == MANIFOLD_OWNER
            and execution_report.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and execution_report.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.source_preflight",
            execution_report.get("status") != COMPLETED_STATUS
            or (
                operator_start_preflight.get("status") == APPROVED_STATUS
                and preflight_validation.get("status") == PASS_STATUS
                and operator_start_preflight.get("operator_start_preflight_approved") is True
            ),
            "source operator-start preflight is approved and validates",
            "source operator-start preflight is rejected or invalid",
            operator_start_preflight.get("issue_code")
            or preflight_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_report_preflight_not_approved",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.pmb_shell_handoff_review",
            not pmb_review_required
            or execution_report.get("status") != COMPLETED_STATUS
            or (
                execution_report.get("pmb_shell_handoff_review_required") is True
                and execution_report.get("pmb_shell_handoff_review_ready") is True
                and pmb_review_summary_matches_preflight
                and isinstance(pmb_review_result, dict)
                and pmb_review_result.get("result_status") == COMPLETED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_review_result)
            ),
            "completed platform smoke execution report preserves the PMB shell handoff gate",
            "completed platform smoke execution report dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_execution_report_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.action_reports",
            platform_smoke_execution_report_action_reports_match_receipts(
                action_receipts,
                action_reports,
                execution_report.get("status"),
            ),
            "platform smoke execution action reports match source action decision receipts",
            "platform smoke execution action reports drifted",
            "hostess.issue.platform_smoke_execution_report_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.readiness_results",
            platform_smoke_execution_report_readiness_results_match_inputs(
                readiness_inputs,
                readiness_results,
                execution_report.get("status"),
            ),
            "platform smoke execution readiness results match source readiness inputs",
            "platform smoke execution readiness results drifted",
            "hostess.issue.platform_smoke_execution_report_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.evidence_placeholders",
            platform_smoke_execution_report_evidence_placeholders_match_reports(
                action_reports,
                evidence_placeholders,
            ),
            "platform smoke execution evidence placeholders match action reports and remain pending",
            "platform smoke execution evidence placeholders drifted or include collected evidence",
            "hostess.issue.platform_smoke_execution_report_evidence_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.counts",
            execution_report.get("source_operator_start_action_decision_receipt_count")
            == len(action_receipts)
            and execution_report.get("action_report_count") == len(action_reports)
            and execution_report.get("completed_action_report_count") == len(completed_actions)
            and execution_report.get("rejected_action_report_count") == len(rejected_actions)
            and execution_report.get("readiness_input_count") == len(readiness_inputs)
            and execution_report.get("readiness_result_count") == len(readiness_results)
            and execution_report.get("completed_readiness_result_count") == len(completed_readiness)
            and execution_report.get("rejected_readiness_result_count") == len(rejected_readiness)
            and execution_report.get("evidence_placeholder_count") == len(evidence_placeholders)
            and execution_report.get("pending_evidence_placeholder_count") == len(pending_placeholders),
            "platform smoke execution report counts match nested reports and placeholders",
            "platform smoke execution report counts drifted",
            "hostess.issue.platform_smoke_execution_report_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.completed_consistency",
            execution_report.get("status") != COMPLETED_STATUS
            or (
                execution_report.get("operator_start_preflight_approved") is True
                and execution_report.get("operator_started_outside_studio") is True
                and execution_report.get("operator_start_acknowledged") is True
                and execution_report.get("host_shell_started_outside_studio") is True
                and execution_report.get("host_shell_reported") is True
                and execution_report.get("requires_external_evidence") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(item.get("reported_status") == COMPLETED_STATUS for item in action_reports)
                and all(item.get("result_status") == COMPLETED_STATUS for item in readiness_results)
                and all(
                    item.get("evidence_status") == PENDING_STATUS
                    and item.get("collected") is False
                    and item.get("attached") is False
                    for item in evidence_placeholders
                )
            ),
            "completed platform smoke execution report records operator start while evidence remains external",
            "completed platform smoke execution report is inconsistent",
            "hostess.issue.platform_smoke_execution_report_completed_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.rejection_reason",
            execution_report.get("status") != REJECTED_STATUS
            or isinstance(execution_report.get("issue_code"), str),
            "rejected platform smoke execution report carries a reason code",
            "rejected platform smoke execution report is missing a reason code",
            "hostess.issue.platform_smoke_execution_report_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EXECUTION_REPORT_VALIDATION_SCHEMA,
        "execution_report_id": execution_report.get("execution_report_id"),
        "source_operator_start_preflight_receipt_id": execution_report.get(
            "source_operator_start_preflight_receipt_id"
        ),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "pmb_shell_handoff_review_required": execution_report.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": execution_report.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "real_platform_execution_evidence_attached": False,
        "checks": checks,
    }


def platform_smoke_execution_report_checks(
    operator_start_preflight: dict[str, Any],
    preflight_validation: dict[str, Any],
    action_receipts: list[dict[str, Any]],
    readiness_inputs: list[dict[str, Any]],
    action_reports: list[dict[str, Any]],
    readiness_results: list[dict[str, Any]],
    evidence_placeholders: list[dict[str, Any]],
    status: str,
    outcome_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = (
        operator_start_preflight.get("pmb_shell_handoff_review_required") is True
    )
    pmb_review_ready = (
        operator_start_preflight.get("pmb_shell_handoff_review_ready") is True
    )
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.source_preflight",
            operator_start_preflight.get("$schema")
            == PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_SCHEMA
            and operator_start_preflight.get("status") == APPROVED_STATUS
            and preflight_validation.get("status") == PASS_STATUS,
            "platform smoke operator-start preflight is approved and validates",
            "platform smoke operator-start preflight is rejected or invalid",
            operator_start_preflight.get("issue_code")
            or preflight_validation.get("issue_code")
            or "hostess.issue.platform_smoke_execution_report_preflight_not_approved",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.outcome",
            outcome_supported,
            "platform smoke execution report outcome is supported",
            "platform smoke execution report outcome is unsupported",
            "hostess.issue.platform_smoke_execution_report_outcome",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.action_receipts",
            all(
                receipt.get("decision_status") == APPROVED_STATUS
                and platform_smoke_operator_start_action_decision_receipt_unstarted(receipt)
                for receipt in action_receipts
            ),
            "platform smoke operator-start action decision receipts are approved and unstarted",
            "platform smoke operator-start action decision receipts are rejected, drifted, or started",
            "hostess.issue.platform_smoke_execution_report_preflight_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.readiness_inputs",
            all(
                item.get("readiness_status") == APPROVED_STATUS
                and platform_smoke_operator_start_readiness_input_unstarted(item)
                for item in readiness_inputs
            ),
            "platform smoke operator-start readiness inputs are approved and unstarted",
            "platform smoke operator-start readiness inputs are rejected, drifted, or started",
            "hostess.issue.platform_smoke_execution_report_preflight_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.pmb_shell_handoff_review",
            not pmb_review_required
            or status != COMPLETED_STATUS
            or (
                pmb_review_ready
                and any(
                    result.get("source_readiness_input_id")
                    == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
                    and result.get("result_status") == COMPLETED_STATUS
                    and pmb_shell_handoff_readiness_result_summary_valid(result)
                    for result in readiness_results
                )
            ),
            "completed platform smoke execution report preserves the PMB shell handoff gate",
            "completed platform smoke execution report dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_execution_report_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.action_reports",
            platform_smoke_execution_report_action_reports_match_receipts(
                action_receipts,
                action_reports,
                status,
            ),
            "platform smoke execution action reports match source receipts",
            "platform smoke execution action reports drifted",
            "hostess.issue.platform_smoke_execution_report_action_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.readiness_results",
            platform_smoke_execution_report_readiness_results_match_inputs(
                readiness_inputs,
                readiness_results,
                status,
            ),
            "platform smoke execution readiness results match source inputs",
            "platform smoke execution readiness results drifted",
            "hostess.issue.platform_smoke_execution_report_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_execution_report.evidence_placeholders",
            platform_smoke_execution_report_evidence_placeholders_match_reports(
                action_reports,
                evidence_placeholders,
            ),
            "platform smoke execution evidence placeholders match action reports and remain pending",
            "platform smoke execution evidence placeholders drifted or include collected evidence",
            "hostess.issue.platform_smoke_execution_report_evidence_drift",
        ),
    ]


def platform_smoke_execution_report_action_reports(
    operator_start_preflight: dict[str, Any],
    action_receipts: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    reported_status = COMPLETED_STATUS if status == COMPLETED_STATUS else REJECTED_STATUS
    reports = []
    for receipt in action_receipts:
        source_plan_action_id = receipt.get("source_plan_action_id")
        evidence_placeholder_id = (
            f"hostess.platform_smoke_execution_evidence_placeholder.{source_plan_action_id}"
            if isinstance(source_plan_action_id, str) and source_plan_action_id
            else "hostess.platform_smoke_execution_evidence_placeholder.unknown"
        )
        reports.append(
            {
                "action_report_id": (
                    f"hostess.platform_smoke_execution_action_report.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_execution_action_report.unknown"
                ),
                "source_operator_start_preflight_receipt_id": operator_start_preflight.get(
                    "operator_start_preflight_receipt_id"
                ),
                "source_action_decision_receipt_id": receipt.get(
                    "action_decision_receipt_id"
                ),
                "source_action_gate_id": receipt.get("source_action_gate_id"),
                "source_plan_id": receipt.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": receipt.get("owner"),
                "route_kind": receipt.get("route_kind"),
                "action_kind": receipt.get("action_kind"),
                "approval_kind": receipt.get("approval_kind"),
                "expected_input_kind": receipt.get("expected_input_kind"),
                "expected_output_kind": receipt.get("expected_output_kind"),
                "reported_status": reported_status,
                "issue_code": None if reported_status == COMPLETED_STATUS else issue_code,
                "operator_started_outside_studio": reported_status == COMPLETED_STATUS,
                "operator_start_acknowledged": reported_status == COMPLETED_STATUS,
                "host_shell_reported": reported_status == COMPLETED_STATUS,
                "host_shell_started_outside_studio": reported_status == COMPLETED_STATUS,
                "evidence_placeholder_id": evidence_placeholder_id,
                "requires_external_evidence": True,
                "studio_execution_allowed": False,
                "schema_path_execution_allowed": False,
                "execution_started": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "real_platform_execution_evidence_attached": False,
                "command_session_started": False,
            }
        )
    return reports


def platform_smoke_execution_report_readiness_results(
    operator_start_preflight: dict[str, Any],
    readiness_inputs: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    result_status = COMPLETED_STATUS if status == COMPLETED_STATUS else REJECTED_STATUS
    results = []
    for item in readiness_inputs:
        readiness_input_id = item.get("readiness_input_id")
        result = {
            "readiness_result_id": (
                f"hostess.platform_smoke_execution_readiness_result.{readiness_input_id}"
                if isinstance(readiness_input_id, str) and readiness_input_id
                else "hostess.platform_smoke_execution_readiness_result.unknown"
            ),
            "source_operator_start_preflight_receipt_id": operator_start_preflight.get(
                "operator_start_preflight_receipt_id"
            ),
            "source_readiness_input_id": readiness_input_id,
            "owner": item.get("owner"),
            "input_kind": item.get("input_kind"),
            "expected_source_kind": item.get("expected_source_kind"),
            "validation_kind": item.get("validation_kind"),
            "result_status": result_status,
            "issue_code": None if result_status == COMPLETED_STATUS else issue_code,
            "operator_supplied": result_status == COMPLETED_STATUS,
            "validated_for_report": True,
            "validated_for_execution": False,
            "operator_started_outside_studio": result_status == COMPLETED_STATUS,
            "studio_execution_allowed": False,
            "schema_path_execution_allowed": False,
            "execution_started": False,
            "runtime_execution_performed": False,
            "platform_execution_performed": False,
            "command_session_started": False,
        }
        if readiness_input_id == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID:
            result.update(pmb_shell_handoff_review_summary_from_source(item))
        results.append(result)
    return results


def platform_smoke_execution_report_evidence_placeholders(
    action_reports: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    placeholders = []
    for report in action_reports:
        placeholders.append(
            {
                "evidence_placeholder_id": report.get("evidence_placeholder_id"),
                "source_action_report_id": report.get("action_report_id"),
                "source_plan_id": report.get("source_plan_id"),
                "source_plan_action_id": report.get("source_plan_action_id"),
                "owner": report.get("owner"),
                "route_kind": report.get("route_kind"),
                "required_evidence_kind": report.get("expected_output_kind"),
                "evidence_status": PENDING_STATUS,
                "issue_code": None if status == COMPLETED_STATUS else issue_code,
                "collected": False,
                "attached": False,
                "collection_started": False,
                "requires_external_attachment": True,
                "studio_execution_allowed": False,
                "schema_path_execution_allowed": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "command_session_started": False,
            }
        )
    return placeholders


def platform_smoke_execution_report_action_report_dicts(
    execution_report: dict[str, Any],
) -> list[dict[str, Any]]:
    reports = execution_report.get("action_reports", [])
    if not isinstance(reports, list):
        return []
    return [item for item in reports if isinstance(item, dict)]


def platform_smoke_execution_report_readiness_result_dicts(
    execution_report: dict[str, Any],
) -> list[dict[str, Any]]:
    results = execution_report.get("readiness_results", [])
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


def platform_smoke_execution_report_evidence_placeholder_dicts(
    execution_report: dict[str, Any],
) -> list[dict[str, Any]]:
    placeholders = execution_report.get("evidence_placeholders", [])
    if not isinstance(placeholders, list):
        return []
    return [item for item in placeholders if isinstance(item, dict)]


def platform_smoke_execution_report_action_reports_match_receipts(
    action_receipts: list[dict[str, Any]],
    action_reports: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {COMPLETED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        report.get("source_action_decision_receipt_id"): report
        for report in action_reports
    }
    if len(action_reports) != len(action_receipts):
        return False
    for receipt in action_receipts:
        report = by_id.get(receipt.get("action_decision_receipt_id"))
        if not isinstance(report, dict):
            return False
        for key in (
            "owner",
            "route_kind",
            "action_kind",
            "approval_kind",
            "expected_input_kind",
            "expected_output_kind",
        ):
            if report.get(key) != receipt.get(key):
                return False
        if report.get("source_plan_action_id") != receipt.get("source_plan_action_id"):
            return False
        if report.get("reported_status") != status:
            return False
        if report.get("operator_started_outside_studio") != (status == COMPLETED_STATUS):
            return False
        if report.get("operator_start_acknowledged") != (status == COMPLETED_STATUS):
            return False
        if report.get("host_shell_reported") != (status == COMPLETED_STATUS):
            return False
        if report.get("host_shell_started_outside_studio") != (status == COMPLETED_STATUS):
            return False
        if report.get("requires_external_evidence") is not True:
            return False
        if not platform_smoke_execution_report_action_report_schema_unstarted(report):
            return False
    return True


def platform_smoke_execution_report_readiness_results_match_inputs(
    readiness_inputs: list[dict[str, Any]],
    readiness_results: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {COMPLETED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        result.get("source_readiness_input_id"): result
        for result in readiness_results
    }
    if len(readiness_results) != len(readiness_inputs):
        return False
    for item in readiness_inputs:
        result = by_id.get(item.get("readiness_input_id"))
        if not isinstance(result, dict):
            return False
        for key in ("owner", "input_kind", "expected_source_kind", "validation_kind"):
            if result.get(key) != item.get(key):
                return False
        if result.get("result_status") != status:
            return False
        if result.get("operator_supplied") != (status == COMPLETED_STATUS):
            return False
        if result.get("validated_for_report") is not True:
            return False
        if result.get("validated_for_execution") is not False:
            return False
        if result.get("operator_started_outside_studio") != (status == COMPLETED_STATUS):
            return False
        if not platform_smoke_execution_report_readiness_result_schema_unstarted(result):
            return False
        if item.get("readiness_input_id") == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID:
            if status == COMPLETED_STATUS and not (
                pmb_shell_handoff_readiness_input_summary_valid(item)
                and pmb_shell_handoff_readiness_result_summary_valid(result)
            ):
                return False
    return True


def platform_smoke_execution_report_evidence_placeholders_match_reports(
    action_reports: list[dict[str, Any]],
    evidence_placeholders: list[dict[str, Any]],
) -> bool:
    by_id = {
        placeholder.get("source_action_report_id"): placeholder
        for placeholder in evidence_placeholders
    }
    if len(evidence_placeholders) != len(action_reports):
        return False
    for report in action_reports:
        placeholder = by_id.get(report.get("action_report_id"))
        if not isinstance(placeholder, dict):
            return False
        if placeholder.get("evidence_placeholder_id") != report.get("evidence_placeholder_id"):
            return False
        for key in ("owner", "route_kind", "source_plan_id", "source_plan_action_id"):
            if placeholder.get(key) != report.get(key):
                return False
        if placeholder.get("required_evidence_kind") != report.get("expected_output_kind"):
            return False
        if placeholder.get("evidence_status") != PENDING_STATUS:
            return False
        if placeholder.get("collected") is not False:
            return False
        if placeholder.get("attached") is not False:
            return False
        if placeholder.get("collection_started") is not False:
            return False
        if placeholder.get("requires_external_attachment") is not True:
            return False
        if not platform_smoke_execution_report_evidence_placeholder_unstarted(placeholder):
            return False
    return True


def platform_smoke_execution_report_action_report_schema_unstarted(
    report: dict[str, Any],
) -> bool:
    return (
        report.get("studio_execution_allowed") is False
        and report.get("schema_path_execution_allowed") is False
        and report.get("execution_started") is False
        and report.get("runtime_execution_performed") is False
        and report.get("platform_execution_performed") is False
        and report.get("real_platform_execution_evidence_attached") is False
        and report.get("command_session_started") is False
    )


def platform_smoke_execution_report_readiness_result_schema_unstarted(
    result: dict[str, Any],
) -> bool:
    return (
        result.get("studio_execution_allowed") is False
        and result.get("schema_path_execution_allowed") is False
        and result.get("execution_started") is False
        and result.get("runtime_execution_performed") is False
        and result.get("platform_execution_performed") is False
        and result.get("command_session_started") is False
    )


def platform_smoke_execution_report_evidence_placeholder_unstarted(
    placeholder: dict[str, Any],
) -> bool:
    return (
        placeholder.get("studio_execution_allowed") is False
        and placeholder.get("schema_path_execution_allowed") is False
        and placeholder.get("runtime_execution_performed") is False
        and placeholder.get("platform_execution_performed") is False
        and placeholder.get("command_session_started") is False
    )


def build_platform_smoke_evidence_attachment_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    report_validation = validate_platform_smoke_execution_report(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
        execution_report,
    )
    action_reports = platform_smoke_execution_report_action_report_dicts(execution_report)
    readiness_results = platform_smoke_execution_report_readiness_result_dicts(
        execution_report
    )
    evidence_placeholders = platform_smoke_execution_report_evidence_placeholder_dicts(
        execution_report
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    report_ready = (
        execution_report.get("status") == COMPLETED_STATUS
        and report_validation.get("status") == PASS_STATUS
        and all(
            report.get("reported_status") == COMPLETED_STATUS
            and platform_smoke_execution_report_action_report_schema_unstarted(report)
            for report in action_reports
        )
        and all(
            result.get("result_status") == COMPLETED_STATUS
            and platform_smoke_execution_report_readiness_result_schema_unstarted(result)
            for result in readiness_results
        )
        and all(
            placeholder.get("evidence_status") == PENDING_STATUS
            and placeholder.get("collected") is False
            and placeholder.get("attached") is False
            and placeholder.get("collection_started") is False
            and platform_smoke_execution_report_evidence_placeholder_unstarted(placeholder)
            for placeholder in evidence_placeholders
        )
    )
    status = (
        VALIDATED_STATUS
        if decision == ACCEPTED_STATUS and report_ready
        else REJECTED_STATUS
    )
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or execution_report.get("issue_code")
            or report_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_attachment_rejected"
        )
    evidence_attachments = platform_smoke_evidence_attachments(
        execution_report,
        evidence_placeholders,
        status,
        issue_code,
    )
    readiness_attachments = platform_smoke_readiness_evidence_attachments(
        execution_report,
        readiness_results,
        status,
        issue_code,
    )
    validated_attachments = [
        item
        for item in evidence_attachments
        if item.get("attachment_status") == VALIDATED_STATUS
    ]
    rejected_attachments = [
        item
        for item in evidence_attachments
        if item.get("attachment_status") == REJECTED_STATUS
    ]
    validated_readiness = [
        item
        for item in readiness_attachments
        if item.get("attachment_status") == VALIDATED_STATUS
    ]
    rejected_readiness = [
        item
        for item in readiness_attachments
        if item.get("attachment_status") == REJECTED_STATUS
    ]
    checks = platform_smoke_evidence_attachment_receipt_checks(
        execution_report,
        report_validation,
        action_reports,
        readiness_results,
        evidence_placeholders,
        evidence_attachments,
        readiness_attachments,
        status,
        decision_supported,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == VALIDATED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        evidence_attachments = platform_smoke_evidence_attachments(
            execution_report,
            evidence_placeholders,
            status,
            issue_code,
        )
        readiness_attachments = platform_smoke_readiness_evidence_attachments(
            execution_report,
            readiness_results,
            status,
            issue_code,
        )
        validated_attachments = []
        rejected_attachments = evidence_attachments
        validated_readiness = []
        rejected_readiness = readiness_attachments

    report_id = execution_report.get("execution_report_id")
    receipt_id = (
        f"hostess.platform_smoke_evidence_attachment_receipt.{report_id}"
        if isinstance(report_id, str) and report_id
        else "hostess.platform_smoke_evidence_attachment_receipt.unknown"
    )
    pmb_review_required = execution_report.get("pmb_shell_handoff_review_required") is True
    pmb_review_ready = execution_report.get("pmb_shell_handoff_review_ready") is True

    return {
        "$schema": PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_SCHEMA,
        "evidence_attachment_receipt_id": receipt_id,
        "source_execution_report_id": report_id,
        "source_operator_start_preflight_receipt_id": execution_report.get(
            "source_operator_start_preflight_receipt_id"
        ),
        "source_operator_start_gate_id": execution_report.get("source_operator_start_gate_id"),
        "source_execution_receipt_id": execution_report.get("source_execution_receipt_id"),
        "source_execution_request_id": execution_report.get("source_execution_request_id"),
        "source_approval_receipt_id": execution_report.get("source_approval_receipt_id"),
        "source_plan_id": execution_report.get("source_plan_id"),
        "source_bundle_id": execution_report.get("source_bundle_id"),
        "source_execution_id": execution_report.get("source_execution_id"),
        "source_request_id": execution_report.get("source_request_id"),
        "target_profile": execution_report.get("target_profile"),
        "target_platform": execution_report.get("target_platform"),
        "host_shell_kind": execution_report.get("host_shell_kind"),
        "status": status,
        "receipt_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_POLICY,
        "receipt_owner": HOSTESS_OWNER,
        "evidence_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": execution_report.get("host_shell_owner"),
        "platform_owner": execution_report.get("platform_owner"),
        "requester_role": execution_report.get("requester_role"),
        "command_session_authority": execution_report.get("command_session_authority"),
        "install_launch_evidence_authority": execution_report.get(
            "install_launch_evidence_authority"
        ),
        "studio_role": execution_report.get("studio_role"),
        "device_required": False,
        "external_evidence_required": True,
        "external_evidence_descriptors_supplied": status == VALIDATED_STATUS,
        "external_evidence_descriptors_attached": status == VALIDATED_STATUS,
        "all_placeholders_bound": status == VALIDATED_STATUS,
        "real_platform_execution_evidence_attached": False,
        "evidence_payloads_copied": False,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(execution_report),
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
        "source_execution_report_status": execution_report.get("status"),
        "source_execution_report_validation_status": report_validation.get("status"),
        "source_execution_report_issue_code": (
            execution_report.get("issue_code") or report_validation.get("issue_code")
        ),
        "source_action_report_count": len(action_reports),
        "source_readiness_result_count": len(readiness_results),
        "source_evidence_placeholder_count": len(evidence_placeholders),
        "evidence_attachment_count": len(evidence_attachments),
        "validated_evidence_attachment_count": len(validated_attachments),
        "rejected_evidence_attachment_count": len(rejected_attachments),
        "readiness_evidence_attachment_count": len(readiness_attachments),
        "validated_readiness_evidence_attachment_count": len(validated_readiness),
        "rejected_readiness_evidence_attachment_count": len(rejected_readiness),
        "source_action_reports": action_reports,
        "source_readiness_results": readiness_results,
        "source_evidence_placeholders": evidence_placeholders,
        "evidence_attachments": evidence_attachments,
        "readiness_evidence_attachments": readiness_attachments,
        "checks": checks,
        "next_required_action": (
            "hostess_review_attached_platform_smoke_evidence_outside_studio"
            if status == VALIDATED_STATUS
            else "repair_or_decline_platform_smoke_evidence_attachment"
        ),
    }


def validate_platform_smoke_evidence_attachment_receipt(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
    attachment_receipt: dict[str, Any],
) -> dict[str, Any]:
    report_validation = validate_platform_smoke_execution_report(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
        execution_report,
    )
    action_reports = platform_smoke_execution_report_action_report_dicts(execution_report)
    readiness_results = platform_smoke_execution_report_readiness_result_dicts(
        execution_report
    )
    evidence_placeholders = platform_smoke_execution_report_evidence_placeholder_dicts(
        execution_report
    )
    evidence_attachments = platform_smoke_evidence_attachment_dicts(attachment_receipt)
    readiness_attachments = platform_smoke_readiness_evidence_attachment_dicts(
        attachment_receipt
    )
    pmb_review_required = execution_report.get("pmb_shell_handoff_review_required") is True
    pmb_attachment = next(
        (
            item
            for item in readiness_attachments
            if item.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    pmb_summary_matches_report = (
        pmb_shell_handoff_review_summary_from_source(attachment_receipt)
        == pmb_shell_handoff_review_summary_from_source(execution_report)
    )
    validated_attachments = [
        item
        for item in evidence_attachments
        if item.get("attachment_status") == VALIDATED_STATUS
    ]
    rejected_attachments = [
        item
        for item in evidence_attachments
        if item.get("attachment_status") == REJECTED_STATUS
    ]
    validated_readiness = [
        item
        for item in readiness_attachments
        if item.get("attachment_status") == VALIDATED_STATUS
    ]
    rejected_readiness = [
        item
        for item in readiness_attachments
        if item.get("attachment_status") == REJECTED_STATUS
    ]
    embedded_checks = attachment_receipt.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.schema",
            attachment_receipt.get("$schema") == PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_SCHEMA,
            "platform smoke evidence attachment receipt schema is supported",
            "platform smoke evidence attachment receipt schema is unsupported",
            "hostess.issue.platform_smoke_evidence_attachment_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.report_id",
            attachment_receipt.get("source_execution_report_id")
            == execution_report.get("execution_report_id"),
            "platform smoke evidence attachment report id matches",
            "platform smoke evidence attachment report id differs",
            "hostess.issue.platform_smoke_evidence_attachment_report_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.status",
            attachment_receipt.get("status") in {VALIDATED_STATUS, REJECTED_STATUS},
            "platform smoke evidence attachment status is supported",
            "platform smoke evidence attachment status is unsupported",
            "hostess.issue.platform_smoke_evidence_attachment_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.execution_policy",
            attachment_receipt.get("execution_policy")
            == PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_POLICY,
            "platform smoke evidence attachment is descriptor-only",
            "platform smoke evidence attachment execution policy drifted",
            "hostess.issue.platform_smoke_evidence_attachment_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.no_execution_started",
            all(attachment_receipt.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and attachment_receipt.get("runtime_execution_performed") is False
            and attachment_receipt.get("platform_execution_performed") is False
            and attachment_receipt.get("schema_path_execution_allowed") is False
            and attachment_receipt.get("platform_execution_allowed") is False
            and attachment_receipt.get("studio_execution_allowed") is False
            and attachment_receipt.get("device_required") is False
            and attachment_receipt.get("evidence_payloads_copied") is False
            and attachment_receipt.get("real_platform_execution_evidence_attached") is False,
            "platform smoke evidence attachment has not started Studio, schema path, runtime, platform, or collection work",
            "platform smoke evidence attachment indicates execution, collection, or payload copying",
            "hostess.issue.platform_smoke_evidence_attachment_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.authority",
            attachment_receipt.get("receipt_owner") == HOSTESS_OWNER
            and attachment_receipt.get("evidence_owner") == HOSTESS_OWNER
            and attachment_receipt.get("operator_start_owner") == HOSTESS_OWNER
            and attachment_receipt.get("host_shell_owner") == HOSTESS_OWNER
            and attachment_receipt.get("platform_owner") == HOSTESS_OWNER
            and attachment_receipt.get("requester_role") == STUDIO_REQUESTER
            and attachment_receipt.get("command_session_authority") == MANIFOLD_OWNER
            and attachment_receipt.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and attachment_receipt.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.source_report",
            attachment_receipt.get("status") != VALIDATED_STATUS
            or (
                execution_report.get("status") == COMPLETED_STATUS
                and report_validation.get("status") == PASS_STATUS
            ),
            "source platform smoke execution report is completed and validates",
            "source platform smoke execution report is rejected or invalid",
            execution_report.get("issue_code")
            or report_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_attachment_report_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.placeholders",
            all(
                placeholder.get("evidence_status") == PENDING_STATUS
                and placeholder.get("collected") is False
                and placeholder.get("attached") is False
                and placeholder.get("collection_started") is False
                and platform_smoke_execution_report_evidence_placeholder_unstarted(placeholder)
                for placeholder in evidence_placeholders
            ),
            "source evidence placeholders are pending and uncollected",
            "source evidence placeholders already claim collection or attachment",
            "hostess.issue.platform_smoke_evidence_attachment_placeholder_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.attachments",
            platform_smoke_evidence_attachments_match_placeholders(
                evidence_placeholders,
                evidence_attachments,
                attachment_receipt.get("status"),
            ),
            "platform smoke evidence attachments match pending placeholders",
            "platform smoke evidence attachments drifted",
            "hostess.issue.platform_smoke_evidence_attachment_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.readiness",
            platform_smoke_readiness_evidence_attachments_match_results(
                readiness_results,
                readiness_attachments,
                attachment_receipt.get("status"),
            ),
            "platform smoke readiness evidence attachments match readiness results",
            "platform smoke readiness evidence attachments drifted",
            "hostess.issue.platform_smoke_evidence_attachment_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.pmb_shell_handoff_review",
            not pmb_review_required
            or attachment_receipt.get("status") != VALIDATED_STATUS
            or (
                attachment_receipt.get("pmb_shell_handoff_review_required") is True
                and attachment_receipt.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_report
                and isinstance(pmb_attachment, dict)
                and pmb_attachment.get("attachment_status") == VALIDATED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_attachment)
            ),
            "validated platform smoke evidence attachment preserves the PMB shell handoff gate",
            "validated platform smoke evidence attachment dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_evidence_attachment_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.counts",
            attachment_receipt.get("source_action_report_count") == len(action_reports)
            and attachment_receipt.get("source_readiness_result_count") == len(readiness_results)
            and attachment_receipt.get("source_evidence_placeholder_count")
            == len(evidence_placeholders)
            and attachment_receipt.get("evidence_attachment_count") == len(evidence_attachments)
            and attachment_receipt.get("validated_evidence_attachment_count")
            == len(validated_attachments)
            and attachment_receipt.get("rejected_evidence_attachment_count")
            == len(rejected_attachments)
            and attachment_receipt.get("readiness_evidence_attachment_count")
            == len(readiness_attachments)
            and attachment_receipt.get("validated_readiness_evidence_attachment_count")
            == len(validated_readiness)
            and attachment_receipt.get("rejected_readiness_evidence_attachment_count")
            == len(rejected_readiness),
            "platform smoke evidence attachment counts match nested records",
            "platform smoke evidence attachment counts drifted",
            "hostess.issue.platform_smoke_evidence_attachment_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.validated_consistency",
            attachment_receipt.get("status") != VALIDATED_STATUS
            or (
                attachment_receipt.get("external_evidence_descriptors_supplied") is True
                and attachment_receipt.get("external_evidence_descriptors_attached") is True
                and attachment_receipt.get("all_placeholders_bound") is True
                and all(check.get("status") == PASS_STATUS for check in embedded_check_dicts)
                and all(
                    item.get("attachment_status") == VALIDATED_STATUS
                    for item in evidence_attachments
                )
                and all(
                    item.get("attachment_status") == VALIDATED_STATUS
                    for item in readiness_attachments
                )
            ),
            "validated platform smoke evidence attachment binds all descriptors without collecting payloads",
            "validated platform smoke evidence attachment is inconsistent",
            "hostess.issue.platform_smoke_evidence_attachment_validated_inconsistent",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.rejection_reason",
            attachment_receipt.get("status") != REJECTED_STATUS
            or isinstance(attachment_receipt.get("issue_code"), str),
            "rejected platform smoke evidence attachment carries a reason code",
            "rejected platform smoke evidence attachment is missing a reason code",
            "hostess.issue.platform_smoke_evidence_attachment_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_VALIDATION_SCHEMA,
        "evidence_attachment_receipt_id": attachment_receipt.get(
            "evidence_attachment_receipt_id"
        ),
        "source_execution_report_id": attachment_receipt.get("source_execution_report_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "real_platform_execution_evidence_attached": False,
        "pmb_shell_handoff_review_required": attachment_receipt.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": attachment_receipt.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def platform_smoke_evidence_attachment_receipt_checks(
    execution_report: dict[str, Any],
    report_validation: dict[str, Any],
    action_reports: list[dict[str, Any]],
    readiness_results: list[dict[str, Any]],
    evidence_placeholders: list[dict[str, Any]],
    evidence_attachments: list[dict[str, Any]],
    readiness_attachments: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = execution_report.get("pmb_shell_handoff_review_required") is True
    pmb_attachment = next(
        (
            item
            for item in readiness_attachments
            if item.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.source_report",
            execution_report.get("$schema") == PLATFORM_SMOKE_EXECUTION_REPORT_SCHEMA
            and execution_report.get("status") == COMPLETED_STATUS
            and report_validation.get("status") == PASS_STATUS,
            "platform smoke execution report is completed and validates",
            "platform smoke execution report is rejected or invalid",
            execution_report.get("issue_code")
            or report_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_attachment_report_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.decision",
            decision_supported,
            "platform smoke evidence attachment decision is supported",
            "platform smoke evidence attachment decision is unsupported",
            "hostess.issue.platform_smoke_evidence_attachment_decision",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.action_reports",
            all(
                report.get("reported_status") == COMPLETED_STATUS
                and platform_smoke_execution_report_action_report_schema_unstarted(report)
                for report in action_reports
            ),
            "platform smoke action reports are completed and descriptor-only",
            "platform smoke action reports are rejected, drifted, or started",
            "hostess.issue.platform_smoke_evidence_attachment_action_report_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.readiness_results",
            all(
                result.get("result_status") == COMPLETED_STATUS
                and platform_smoke_execution_report_readiness_result_schema_unstarted(result)
                for result in readiness_results
            ),
            "platform smoke readiness results are completed and descriptor-only",
            "platform smoke readiness results are rejected, drifted, or started",
            "hostess.issue.platform_smoke_evidence_attachment_readiness_result_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.placeholders",
            all(
                placeholder.get("evidence_status") == PENDING_STATUS
                and placeholder.get("collected") is False
                and placeholder.get("attached") is False
                and placeholder.get("collection_started") is False
                and platform_smoke_execution_report_evidence_placeholder_unstarted(placeholder)
                for placeholder in evidence_placeholders
            ),
            "platform smoke evidence placeholders are pending and uncollected",
            "platform smoke evidence placeholders drifted or already attached",
            "hostess.issue.platform_smoke_evidence_attachment_placeholder_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.attachments",
            platform_smoke_evidence_attachments_match_placeholders(
                evidence_placeholders,
                evidence_attachments,
                status,
            ),
            "platform smoke evidence attachments match source placeholders",
            "platform smoke evidence attachments drifted",
            "hostess.issue.platform_smoke_evidence_attachment_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.readiness",
            platform_smoke_readiness_evidence_attachments_match_results(
                readiness_results,
                readiness_attachments,
                status,
            ),
            "platform smoke readiness evidence attachments match source readiness results",
            "platform smoke readiness evidence attachments drifted",
            "hostess.issue.platform_smoke_evidence_attachment_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_attachment.pmb_shell_handoff_review",
            not pmb_review_required
            or status != VALIDATED_STATUS
            or (
                isinstance(pmb_attachment, dict)
                and pmb_attachment.get("attachment_status") == VALIDATED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_attachment)
            ),
            "validated platform smoke evidence attachment preserves the PMB shell handoff gate",
            "validated platform smoke evidence attachment dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_evidence_attachment_pmb_shell_handoff_review_drift",
        ),
    ]


def platform_smoke_evidence_attachments(
    execution_report: dict[str, Any],
    evidence_placeholders: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    attachment_status = VALIDATED_STATUS if status == VALIDATED_STATUS else REJECTED_STATUS
    attachments = []
    for placeholder in evidence_placeholders:
        source_plan_action_id = placeholder.get("source_plan_action_id")
        attachments.append(
            {
                "evidence_attachment_id": (
                    f"hostess.platform_smoke_evidence_attachment.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "hostess.platform_smoke_evidence_attachment.unknown"
                ),
                "source_execution_report_id": execution_report.get("execution_report_id"),
                "source_evidence_placeholder_id": placeholder.get("evidence_placeholder_id"),
                "source_action_report_id": placeholder.get("source_action_report_id"),
                "source_plan_id": placeholder.get("source_plan_id"),
                "source_plan_action_id": source_plan_action_id,
                "owner": placeholder.get("owner"),
                "route_kind": placeholder.get("route_kind"),
                "required_evidence_kind": placeholder.get("required_evidence_kind"),
                "external_evidence_kind": placeholder.get("required_evidence_kind"),
                "external_evidence_descriptor_id": (
                    f"external.hostess.platform_smoke_evidence_descriptor.{source_plan_action_id}"
                    if isinstance(source_plan_action_id, str) and source_plan_action_id
                    else "external.hostess.platform_smoke_evidence_descriptor.unknown"
                ),
                "attachment_status": attachment_status,
                "issue_code": None if attachment_status == VALIDATED_STATUS else issue_code,
                "external_evidence_descriptor_supplied": attachment_status == VALIDATED_STATUS,
                "evidence_descriptor_attached": attachment_status == VALIDATED_STATUS,
                "placeholder_evidence_status": placeholder.get("evidence_status"),
                "requires_external_attachment": True,
                "evidence_payload_copied": False,
                "collection_started": False,
                "studio_execution_allowed": False,
                "schema_path_execution_allowed": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "real_platform_execution_evidence_attached": False,
                "command_session_started": False,
            }
        )
    return attachments


def platform_smoke_readiness_evidence_attachments(
    execution_report: dict[str, Any],
    readiness_results: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    attachment_status = VALIDATED_STATUS if status == VALIDATED_STATUS else REJECTED_STATUS
    attachments = []
    for result in readiness_results:
        source_result_id = result.get("readiness_result_id")
        attachment = {
            "readiness_evidence_attachment_id": (
                f"hostess.platform_smoke_readiness_evidence_attachment.{source_result_id}"
                if isinstance(source_result_id, str) and source_result_id
                else "hostess.platform_smoke_readiness_evidence_attachment.unknown"
            ),
            "source_execution_report_id": execution_report.get("execution_report_id"),
            "source_readiness_result_id": source_result_id,
            "source_readiness_input_id": result.get("source_readiness_input_id"),
            "owner": result.get("owner"),
            "input_kind": result.get("input_kind"),
            "expected_source_kind": result.get("expected_source_kind"),
            "validation_kind": result.get("validation_kind"),
            "external_readiness_descriptor_id": (
                f"external.hostess.platform_smoke_readiness_descriptor.{source_result_id}"
                if isinstance(source_result_id, str) and source_result_id
                else "external.hostess.platform_smoke_readiness_descriptor.unknown"
            ),
            "attachment_status": attachment_status,
            "issue_code": None if attachment_status == VALIDATED_STATUS else issue_code,
            "external_readiness_descriptor_supplied": attachment_status == VALIDATED_STATUS,
            "readiness_descriptor_attached": attachment_status == VALIDATED_STATUS,
            "validated_for_attachment": True,
            "validated_for_execution": False,
            "studio_execution_allowed": False,
            "schema_path_execution_allowed": False,
            "execution_started": False,
            "runtime_execution_performed": False,
            "platform_execution_performed": False,
            "command_session_started": False,
        }
        if result.get("source_readiness_input_id") == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID:
            attachment.update(pmb_shell_handoff_review_summary_from_source(result))
        attachments.append(attachment)
    return attachments


def platform_smoke_evidence_attachment_dicts(
    attachment_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    attachments = attachment_receipt.get("evidence_attachments", [])
    if not isinstance(attachments, list):
        return []
    return [item for item in attachments if isinstance(item, dict)]


def platform_smoke_readiness_evidence_attachment_dicts(
    attachment_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    attachments = attachment_receipt.get("readiness_evidence_attachments", [])
    if not isinstance(attachments, list):
        return []
    return [item for item in attachments if isinstance(item, dict)]


def platform_smoke_evidence_attachments_match_placeholders(
    evidence_placeholders: list[dict[str, Any]],
    evidence_attachments: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {VALIDATED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        attachment.get("source_evidence_placeholder_id"): attachment
        for attachment in evidence_attachments
    }
    if len(evidence_attachments) != len(evidence_placeholders):
        return False
    for placeholder in evidence_placeholders:
        attachment = by_id.get(placeholder.get("evidence_placeholder_id"))
        if not isinstance(attachment, dict):
            return False
        for key in ("owner", "route_kind", "source_plan_id", "source_plan_action_id"):
            if attachment.get(key) != placeholder.get(key):
                return False
        if attachment.get("source_action_report_id") != placeholder.get("source_action_report_id"):
            return False
        if attachment.get("required_evidence_kind") != placeholder.get("required_evidence_kind"):
            return False
        if attachment.get("external_evidence_kind") != placeholder.get("required_evidence_kind"):
            return False
        if attachment.get("placeholder_evidence_status") != PENDING_STATUS:
            return False
        if attachment.get("attachment_status") != status:
            return False
        if attachment.get("external_evidence_descriptor_supplied") != (status == VALIDATED_STATUS):
            return False
        if attachment.get("evidence_descriptor_attached") != (status == VALIDATED_STATUS):
            return False
        if attachment.get("requires_external_attachment") is not True:
            return False
        if not platform_smoke_evidence_attachment_unstarted(attachment):
            return False
    return True


def platform_smoke_readiness_evidence_attachments_match_results(
    readiness_results: list[dict[str, Any]],
    readiness_attachments: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {VALIDATED_STATUS, REJECTED_STATUS}:
        return False
    by_id = {
        attachment.get("source_readiness_result_id"): attachment
        for attachment in readiness_attachments
    }
    if len(readiness_attachments) != len(readiness_results):
        return False
    for result in readiness_results:
        attachment = by_id.get(result.get("readiness_result_id"))
        if not isinstance(attachment, dict):
            return False
        for key in ("owner", "input_kind", "expected_source_kind", "validation_kind"):
            if attachment.get(key) != result.get(key):
                return False
        if attachment.get("source_readiness_input_id") != result.get("source_readiness_input_id"):
            return False
        if attachment.get("attachment_status") != status:
            return False
        if (
            status == VALIDATED_STATUS
            and result.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
            and (
                not pmb_shell_handoff_readiness_result_summary_valid(result)
                or not pmb_shell_handoff_readiness_result_summary_valid(attachment)
            )
        ):
            return False
        if attachment.get("external_readiness_descriptor_supplied") != (status == VALIDATED_STATUS):
            return False
        if attachment.get("readiness_descriptor_attached") != (status == VALIDATED_STATUS):
            return False
        if attachment.get("validated_for_attachment") is not True:
            return False
        if attachment.get("validated_for_execution") is not False:
            return False
        if not platform_smoke_readiness_evidence_attachment_unstarted(attachment):
            return False
    return True


def platform_smoke_evidence_attachment_unstarted(
    attachment: dict[str, Any],
) -> bool:
    return (
        attachment.get("evidence_payload_copied") is False
        and attachment.get("collection_started") is False
        and attachment.get("studio_execution_allowed") is False
        and attachment.get("schema_path_execution_allowed") is False
        and attachment.get("runtime_execution_performed") is False
        and attachment.get("platform_execution_performed") is False
        and attachment.get("real_platform_execution_evidence_attached") is False
        and attachment.get("command_session_started") is False
    )


def platform_smoke_readiness_evidence_attachment_unstarted(
    attachment: dict[str, Any],
) -> bool:
    return (
        attachment.get("studio_execution_allowed") is False
        and attachment.get("schema_path_execution_allowed") is False
        and attachment.get("execution_started") is False
        and attachment.get("runtime_execution_performed") is False
        and attachment.get("platform_execution_performed") is False
        and attachment.get("command_session_started") is False
    )


def build_platform_smoke_evidence_review(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
    attachment_receipt: dict[str, Any],
    decision: str = ACCEPTED_STATUS,
    reason_code: str | None = None,
) -> dict[str, Any]:
    attachment_validation = validate_platform_smoke_evidence_attachment_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
        execution_report,
        attachment_receipt,
    )
    evidence_attachments = platform_smoke_evidence_attachment_dicts(attachment_receipt)
    readiness_attachments = platform_smoke_readiness_evidence_attachment_dicts(
        attachment_receipt
    )
    decision_supported = decision in {ACCEPTED_STATUS, REJECTED_STATUS}
    source_validated = (
        attachment_receipt.get("status") == VALIDATED_STATUS
        and attachment_validation.get("status") == PASS_STATUS
        and attachment_receipt.get("external_evidence_descriptors_attached") is True
        and attachment_receipt.get("all_placeholders_bound") is True
        and all(
            attachment.get("attachment_status") == VALIDATED_STATUS
            and attachment.get("evidence_descriptor_attached") is True
            and platform_smoke_evidence_attachment_unstarted(attachment)
            for attachment in evidence_attachments
        )
        and all(
            attachment.get("attachment_status") == VALIDATED_STATUS
            and attachment.get("readiness_descriptor_attached") is True
            and platform_smoke_readiness_evidence_attachment_unstarted(attachment)
            for attachment in readiness_attachments
        )
    )
    status = (
        REVIEWED_STATUS
        if decision == ACCEPTED_STATUS and decision_supported and source_validated
        else REJECTED_STATUS
    )
    issue_code = None
    if status == REJECTED_STATUS:
        issue_code = (
            reason_code
            or attachment_receipt.get("issue_code")
            or attachment_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_review_rejected"
        )
    evidence_review_rows = platform_smoke_evidence_review_attachment_rows(
        attachment_receipt,
        evidence_attachments,
        status,
        issue_code,
    )
    readiness_review_rows = platform_smoke_evidence_review_readiness_rows(
        attachment_receipt,
        readiness_attachments,
        status,
        issue_code,
    )
    reviewed_evidence_rows = [
        row for row in evidence_review_rows if row.get("review_status") == REVIEWED_STATUS
    ]
    rejected_evidence_rows = [
        row for row in evidence_review_rows if row.get("review_status") == REJECTED_STATUS
    ]
    reviewed_readiness_rows = [
        row for row in readiness_review_rows if row.get("review_status") == REVIEWED_STATUS
    ]
    rejected_readiness_rows = [
        row for row in readiness_review_rows if row.get("review_status") == REJECTED_STATUS
    ]
    missing_attachment_count = sum(
        1 for row in evidence_review_rows if row.get("missing_attachment") is True
    ) + sum(1 for row in readiness_review_rows if row.get("missing_attachment") is True)
    rejected_attachment_count = len(rejected_evidence_rows) + len(rejected_readiness_rows)
    checks = platform_smoke_evidence_review_checks(
        attachment_receipt,
        attachment_validation,
        evidence_attachments,
        readiness_attachments,
        evidence_review_rows,
        readiness_review_rows,
        status,
        decision_supported,
    )
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    if failed and status == REVIEWED_STATUS:
        status = REJECTED_STATUS
        issue_code = failed[0]["issue_code"]
        evidence_review_rows = platform_smoke_evidence_review_attachment_rows(
            attachment_receipt,
            evidence_attachments,
            status,
            issue_code,
        )
        readiness_review_rows = platform_smoke_evidence_review_readiness_rows(
            attachment_receipt,
            readiness_attachments,
            status,
            issue_code,
        )
        reviewed_evidence_rows = []
        rejected_evidence_rows = evidence_review_rows
        reviewed_readiness_rows = []
        rejected_readiness_rows = readiness_review_rows
        missing_attachment_count = sum(
            1 for row in evidence_review_rows if row.get("missing_attachment") is True
        ) + sum(1 for row in readiness_review_rows if row.get("missing_attachment") is True)
        rejected_attachment_count = len(rejected_evidence_rows) + len(
            rejected_readiness_rows
        )

    attachment_receipt_id = attachment_receipt.get("evidence_attachment_receipt_id")
    review_id = (
        f"hostess.platform_smoke_evidence_review.{attachment_receipt_id}"
        if isinstance(attachment_receipt_id, str) and attachment_receipt_id
        else "hostess.platform_smoke_evidence_review.unknown"
    )
    pmb_review_required = attachment_receipt.get("pmb_shell_handoff_review_required") is True
    pmb_review_ready = attachment_receipt.get("pmb_shell_handoff_review_ready") is True
    return {
        "$schema": PLATFORM_SMOKE_EVIDENCE_REVIEW_SCHEMA,
        "evidence_review_id": review_id,
        "source_evidence_attachment_receipt_id": attachment_receipt_id,
        "source_execution_report_id": attachment_receipt.get("source_execution_report_id"),
        "source_operator_start_preflight_receipt_id": attachment_receipt.get(
            "source_operator_start_preflight_receipt_id"
        ),
        "source_operator_start_gate_id": attachment_receipt.get("source_operator_start_gate_id"),
        "source_execution_receipt_id": attachment_receipt.get("source_execution_receipt_id"),
        "source_execution_request_id": attachment_receipt.get("source_execution_request_id"),
        "source_approval_receipt_id": attachment_receipt.get("source_approval_receipt_id"),
        "source_plan_id": attachment_receipt.get("source_plan_id"),
        "source_bundle_id": attachment_receipt.get("source_bundle_id"),
        "target_profile": attachment_receipt.get("target_profile"),
        "target_platform": attachment_receipt.get("target_platform"),
        "host_shell_kind": attachment_receipt.get("host_shell_kind"),
        "status": status,
        "review_decision": decision if decision_supported else REJECTED_STATUS,
        "issue_code": issue_code,
        "execution_policy": PLATFORM_SMOKE_EVIDENCE_REVIEW_POLICY,
        "review_owner": HOSTESS_OWNER,
        "evidence_owner": HOSTESS_OWNER,
        "operator_start_owner": HOSTESS_OWNER,
        "host_shell_owner": attachment_receipt.get("host_shell_owner"),
        "platform_owner": attachment_receipt.get("platform_owner"),
        "requester_role": attachment_receipt.get("requester_role"),
        "command_session_authority": attachment_receipt.get("command_session_authority"),
        "install_launch_evidence_authority": attachment_receipt.get(
            "install_launch_evidence_authority"
        ),
        "studio_role": attachment_receipt.get("studio_role"),
        "device_required": False,
        "operator_review_ready": status == REVIEWED_STATUS,
        "scorecard_status": PASS_STATUS if status == REVIEWED_STATUS else FAIL_STATUS,
        "external_evidence_required": True,
        "external_evidence_descriptors_attached": attachment_receipt.get(
            "external_evidence_descriptors_attached"
        )
        is True,
        "all_placeholders_bound": attachment_receipt.get("all_placeholders_bound") is True,
        "real_platform_execution_evidence_attached": False,
        "evidence_payloads_copied": False,
        "pmb_shell_handoff_review_required": pmb_review_required,
        "pmb_shell_handoff_review_ready": pmb_review_ready,
        **pmb_shell_handoff_review_summary_from_source(attachment_receipt),
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
        "source_evidence_attachment_receipt_status": attachment_receipt.get("status"),
        "source_evidence_attachment_validation_status": attachment_validation.get("status"),
        "source_evidence_attachment_issue_code": (
            attachment_receipt.get("issue_code") or attachment_validation.get("issue_code")
        ),
        "source_evidence_attachment_count": len(evidence_attachments),
        "source_readiness_evidence_attachment_count": len(readiness_attachments),
        "evidence_review_row_count": len(evidence_review_rows),
        "reviewed_evidence_attachment_count": len(reviewed_evidence_rows),
        "rejected_evidence_attachment_count": len(rejected_evidence_rows),
        "readiness_review_row_count": len(readiness_review_rows),
        "reviewed_readiness_evidence_attachment_count": len(reviewed_readiness_rows),
        "rejected_readiness_evidence_attachment_count": len(rejected_readiness_rows),
        "missing_attachment_count": missing_attachment_count,
        "rejected_attachment_count": rejected_attachment_count,
        "source_evidence_attachments": evidence_attachments,
        "source_readiness_evidence_attachments": readiness_attachments,
        "evidence_review_rows": evidence_review_rows,
        "readiness_review_rows": readiness_review_rows,
        "checks": checks,
        "next_required_action": (
            "hostess_prepare_operator_release_bundle_outside_studio"
            if status == REVIEWED_STATUS
            else "repair_or_decline_platform_smoke_evidence_review"
        ),
    }


def validate_platform_smoke_evidence_review(
    plan: dict[str, Any],
    approval_receipt: dict[str, Any],
    execution_request: dict[str, Any],
    execution_receipt: dict[str, Any],
    operator_start_gate: dict[str, Any],
    operator_start_preflight: dict[str, Any],
    execution_report: dict[str, Any],
    attachment_receipt: dict[str, Any],
    evidence_review: dict[str, Any],
) -> dict[str, Any]:
    attachment_validation = validate_platform_smoke_evidence_attachment_receipt(
        plan,
        approval_receipt,
        execution_request,
        execution_receipt,
        operator_start_gate,
        operator_start_preflight,
        execution_report,
        attachment_receipt,
    )
    evidence_attachments = platform_smoke_evidence_attachment_dicts(attachment_receipt)
    readiness_attachments = platform_smoke_readiness_evidence_attachment_dicts(
        attachment_receipt
    )
    evidence_review_rows = platform_smoke_evidence_review_row_dicts(evidence_review)
    readiness_review_rows = platform_smoke_evidence_review_readiness_row_dicts(
        evidence_review
    )
    pmb_review_required = attachment_receipt.get("pmb_shell_handoff_review_required") is True
    pmb_review_row = next(
        (
            row
            for row in readiness_review_rows
            if row.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    pmb_summary_matches_attachment = (
        pmb_shell_handoff_review_summary_from_source(evidence_review)
        == pmb_shell_handoff_review_summary_from_source(attachment_receipt)
    )
    reviewed_evidence_rows = [
        row for row in evidence_review_rows if row.get("review_status") == REVIEWED_STATUS
    ]
    rejected_evidence_rows = [
        row for row in evidence_review_rows if row.get("review_status") == REJECTED_STATUS
    ]
    reviewed_readiness_rows = [
        row for row in readiness_review_rows if row.get("review_status") == REVIEWED_STATUS
    ]
    rejected_readiness_rows = [
        row for row in readiness_review_rows if row.get("review_status") == REJECTED_STATUS
    ]
    missing_attachment_count = sum(
        1 for row in evidence_review_rows if row.get("missing_attachment") is True
    ) + sum(1 for row in readiness_review_rows if row.get("missing_attachment") is True)
    rejected_attachment_count = len(rejected_evidence_rows) + len(rejected_readiness_rows)
    embedded_checks = evidence_review.get("checks", [])
    if not isinstance(embedded_checks, list):
        embedded_checks = []
    embedded_check_dicts = [check for check in embedded_checks if isinstance(check, dict)]
    checks = [
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.schema",
            evidence_review.get("$schema") == PLATFORM_SMOKE_EVIDENCE_REVIEW_SCHEMA,
            "platform smoke evidence review schema is supported",
            "platform smoke evidence review schema is unsupported",
            "hostess.issue.platform_smoke_evidence_review_schema",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.attachment_receipt_id",
            evidence_review.get("source_evidence_attachment_receipt_id")
            == attachment_receipt.get("evidence_attachment_receipt_id"),
            "platform smoke evidence review source attachment receipt id matches",
            "platform smoke evidence review source attachment receipt id differs",
            "hostess.issue.platform_smoke_evidence_review_attachment_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.status",
            evidence_review.get("status") in {REVIEWED_STATUS, REJECTED_STATUS},
            "platform smoke evidence review status is supported",
            "platform smoke evidence review status is unsupported",
            "hostess.issue.platform_smoke_evidence_review_status",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.execution_policy",
            evidence_review.get("execution_policy") == PLATFORM_SMOKE_EVIDENCE_REVIEW_POLICY,
            "platform smoke evidence review is scorecard-only",
            "platform smoke evidence review execution policy drifted",
            "hostess.issue.platform_smoke_evidence_review_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.no_execution_started",
            all(evidence_review.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
            and evidence_review.get("runtime_execution_performed") is False
            and evidence_review.get("platform_execution_performed") is False
            and evidence_review.get("schema_path_execution_allowed") is False
            and evidence_review.get("platform_execution_allowed") is False
            and evidence_review.get("studio_execution_allowed") is False
            and evidence_review.get("device_required") is False
            and evidence_review.get("evidence_payloads_copied") is False
            and evidence_review.get("real_platform_execution_evidence_attached") is False,
            "platform smoke evidence review has not started Studio, schema path, runtime, platform, collection, or payload work",
            "platform smoke evidence review indicates execution, collection, or payload copying",
            "hostess.issue.platform_smoke_evidence_review_execution_started",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.authority",
            evidence_review.get("review_owner") == HOSTESS_OWNER
            and evidence_review.get("evidence_owner") == HOSTESS_OWNER
            and evidence_review.get("operator_start_owner") == HOSTESS_OWNER
            and evidence_review.get("host_shell_owner") == HOSTESS_OWNER
            and evidence_review.get("platform_owner") == HOSTESS_OWNER
            and evidence_review.get("requester_role") == STUDIO_REQUESTER
            and evidence_review.get("command_session_authority") == MANIFOLD_OWNER
            and evidence_review.get("install_launch_evidence_authority") == HOSTESS_OWNER
            and evidence_review.get("studio_role") == STUDIO_ROLE,
            "Hostess, Manifold, and Studio authority fields are separated",
            "authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.source_attachment",
            evidence_review.get("status") != REVIEWED_STATUS
            or (
                attachment_receipt.get("status") == VALIDATED_STATUS
                and attachment_validation.get("status") == PASS_STATUS
                and attachment_receipt.get("external_evidence_descriptors_attached") is True
                and attachment_receipt.get("all_placeholders_bound") is True
            ),
            "source platform smoke evidence attachment is validated",
            "source platform smoke evidence attachment is rejected, invalid, or incomplete",
            attachment_receipt.get("issue_code")
            or attachment_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_review_source_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.attachments",
            platform_smoke_evidence_review_rows_match_attachments(
                evidence_attachments,
                evidence_review_rows,
                evidence_review.get("status"),
            ),
            "platform smoke evidence review rows match source evidence attachments",
            "platform smoke evidence review rows drifted from source evidence attachments",
            "hostess.issue.platform_smoke_evidence_review_attachment_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.readiness",
            platform_smoke_evidence_review_readiness_rows_match_attachments(
                readiness_attachments,
                readiness_review_rows,
                evidence_review.get("status"),
            ),
            "platform smoke readiness review rows match source readiness attachments",
            "platform smoke readiness review rows drifted from source readiness attachments",
            "hostess.issue.platform_smoke_evidence_review_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.pmb_shell_handoff_review",
            not pmb_review_required
            or evidence_review.get("status") != REVIEWED_STATUS
            or (
                evidence_review.get("pmb_shell_handoff_review_required") is True
                and evidence_review.get("pmb_shell_handoff_review_ready") is True
                and pmb_summary_matches_attachment
                and isinstance(pmb_review_row, dict)
                and pmb_review_row.get("review_status") == REVIEWED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_review_row)
            ),
            "reviewed platform smoke evidence preserves the PMB shell handoff gate",
            "reviewed platform smoke evidence dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_evidence_review_pmb_shell_handoff_review_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.counts",
            evidence_review.get("source_evidence_attachment_count") == len(evidence_attachments)
            and evidence_review.get("source_readiness_evidence_attachment_count")
            == len(readiness_attachments)
            and evidence_review.get("evidence_review_row_count") == len(evidence_review_rows)
            and evidence_review.get("reviewed_evidence_attachment_count")
            == len(reviewed_evidence_rows)
            and evidence_review.get("rejected_evidence_attachment_count")
            == len(rejected_evidence_rows)
            and evidence_review.get("readiness_review_row_count") == len(readiness_review_rows)
            and evidence_review.get("reviewed_readiness_evidence_attachment_count")
            == len(reviewed_readiness_rows)
            and evidence_review.get("rejected_readiness_evidence_attachment_count")
            == len(rejected_readiness_rows)
            and evidence_review.get("missing_attachment_count") == missing_attachment_count
            and evidence_review.get("rejected_attachment_count") == rejected_attachment_count,
            "platform smoke evidence review counts match nested records",
            "platform smoke evidence review counts drifted",
            "hostess.issue.platform_smoke_evidence_review_count_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.scorecard",
            (
                evidence_review.get("status") == REVIEWED_STATUS
                and evidence_review.get("scorecard_status") == PASS_STATUS
                and evidence_review.get("operator_review_ready") is True
                and evidence_review.get("missing_attachment_count") == 0
                and evidence_review.get("rejected_attachment_count") == 0
            )
            or (
                evidence_review.get("status") == REJECTED_STATUS
                and evidence_review.get("scorecard_status") == FAIL_STATUS
                and evidence_review.get("operator_review_ready") is False
            ),
            "platform smoke evidence review scorecard matches review status",
            "platform smoke evidence review scorecard drifted",
            "hostess.issue.platform_smoke_evidence_review_scorecard_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.embedded_checks",
            all(check.get("status") == PASS_STATUS for check in embedded_check_dicts),
            "embedded platform smoke evidence review checks passed",
            "embedded platform smoke evidence review checks contain failures",
            "hostess.issue.platform_smoke_evidence_review_embedded_check_failed",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.rejection_reason",
            evidence_review.get("status") != REJECTED_STATUS
            or isinstance(evidence_review.get("issue_code"), str),
            "rejected platform smoke evidence review carries a reason code",
            "rejected platform smoke evidence review is missing a reason code",
            "hostess.issue.platform_smoke_evidence_review_rejection_reason",
        ),
    ]
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": PLATFORM_SMOKE_EVIDENCE_REVIEW_VALIDATION_SCHEMA,
        "evidence_review_id": evidence_review.get("evidence_review_id"),
        "source_evidence_attachment_receipt_id": evidence_review.get(
            "source_evidence_attachment_receipt_id"
        ),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "real_platform_execution_evidence_attached": False,
        "pmb_shell_handoff_review_required": evidence_review.get(
            "pmb_shell_handoff_review_required"
        )
        is True,
        "pmb_shell_handoff_review_ready": evidence_review.get(
            "pmb_shell_handoff_review_ready"
        )
        is True,
        "checks": checks,
    }


def platform_smoke_evidence_review_checks(
    attachment_receipt: dict[str, Any],
    attachment_validation: dict[str, Any],
    evidence_attachments: list[dict[str, Any]],
    readiness_attachments: list[dict[str, Any]],
    evidence_review_rows: list[dict[str, Any]],
    readiness_review_rows: list[dict[str, Any]],
    status: str,
    decision_supported: bool,
) -> list[dict[str, Any]]:
    pmb_review_required = attachment_receipt.get("pmb_shell_handoff_review_required") is True
    pmb_review_row = next(
        (
            row
            for row in readiness_review_rows
            if row.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ),
        None,
    )
    return [
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.source_attachment",
            attachment_receipt.get("$schema") == PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_SCHEMA
            and attachment_receipt.get("status") == VALIDATED_STATUS
            and attachment_validation.get("status") == PASS_STATUS,
            "platform smoke evidence attachment receipt is validated",
            "platform smoke evidence attachment receipt is rejected or invalid",
            attachment_receipt.get("issue_code")
            or attachment_validation.get("issue_code")
            or "hostess.issue.platform_smoke_evidence_review_source_not_ready",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.decision",
            decision_supported,
            "platform smoke evidence review decision is supported",
            "platform smoke evidence review decision is unsupported",
            "hostess.issue.platform_smoke_evidence_review_decision",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.source_descriptors",
            attachment_receipt.get("external_evidence_descriptors_attached") is True
            and attachment_receipt.get("all_placeholders_bound") is True
            and all(
                attachment.get("attachment_status") == VALIDATED_STATUS
                and attachment.get("evidence_descriptor_attached") is True
                and platform_smoke_evidence_attachment_unstarted(attachment)
                for attachment in evidence_attachments
            )
            and all(
                attachment.get("attachment_status") == VALIDATED_STATUS
                and attachment.get("readiness_descriptor_attached") is True
                and platform_smoke_readiness_evidence_attachment_unstarted(attachment)
                for attachment in readiness_attachments
            ),
            "platform smoke evidence descriptors are attached and unexecuted",
            "platform smoke evidence descriptors are missing, rejected, or started",
            "hostess.issue.platform_smoke_evidence_review_descriptor_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.attachments",
            platform_smoke_evidence_review_rows_match_attachments(
                evidence_attachments,
                evidence_review_rows,
                status,
            ),
            "platform smoke evidence review rows match source evidence attachments",
            "platform smoke evidence review rows drifted",
            "hostess.issue.platform_smoke_evidence_review_attachment_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.readiness",
            platform_smoke_evidence_review_readiness_rows_match_attachments(
                readiness_attachments,
                readiness_review_rows,
                status,
            ),
            "platform smoke readiness review rows match source readiness attachments",
            "platform smoke readiness review rows drifted",
            "hostess.issue.platform_smoke_evidence_review_readiness_drift",
        ),
        check(
            "hostess.check.studio_staging_platform_smoke_evidence_review.pmb_shell_handoff_review",
            not pmb_review_required
            or status != REVIEWED_STATUS
            or (
                isinstance(pmb_review_row, dict)
                and pmb_review_row.get("review_status") == REVIEWED_STATUS
                and pmb_shell_handoff_readiness_result_summary_valid(pmb_review_row)
            ),
            "reviewed platform smoke evidence preserves the PMB shell handoff gate",
            "reviewed platform smoke evidence dropped or drifted the PMB shell handoff gate",
            "hostess.issue.platform_smoke_evidence_review_pmb_shell_handoff_review_drift",
        ),
    ]


def platform_smoke_evidence_review_attachment_rows(
    attachment_receipt: dict[str, Any],
    evidence_attachments: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    review_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    rows = []
    for attachment in evidence_attachments:
        source_attachment_id = attachment.get("evidence_attachment_id")
        descriptor_attached = attachment.get("evidence_descriptor_attached") is True
        rows.append(
            {
                "evidence_review_row_id": (
                    f"hostess.platform_smoke_evidence_review_row.{source_attachment_id}"
                    if isinstance(source_attachment_id, str) and source_attachment_id
                    else "hostess.platform_smoke_evidence_review_row.unknown"
                ),
                "source_evidence_attachment_receipt_id": attachment_receipt.get(
                    "evidence_attachment_receipt_id"
                ),
                "source_evidence_attachment_id": source_attachment_id,
                "source_evidence_placeholder_id": attachment.get(
                    "source_evidence_placeholder_id"
                ),
                "source_action_report_id": attachment.get("source_action_report_id"),
                "source_plan_id": attachment.get("source_plan_id"),
                "source_plan_action_id": attachment.get("source_plan_action_id"),
                "owner": attachment.get("owner"),
                "route_kind": attachment.get("route_kind"),
                "required_evidence_kind": attachment.get("required_evidence_kind"),
                "external_evidence_kind": attachment.get("external_evidence_kind"),
                "external_evidence_descriptor_id": attachment.get(
                    "external_evidence_descriptor_id"
                ),
                "source_attachment_status": attachment.get("attachment_status"),
                "review_status": review_status,
                "issue_code": None if review_status == REVIEWED_STATUS else issue_code,
                "external_evidence_descriptor_supplied": attachment.get(
                    "external_evidence_descriptor_supplied"
                ),
                "evidence_descriptor_attached": descriptor_attached,
                "missing_attachment": not descriptor_attached,
                "rejected_attachment": review_status == REJECTED_STATUS,
                "evidence_payload_copied": False,
                "collection_started": False,
                "studio_execution_allowed": False,
                "schema_path_execution_allowed": False,
                "runtime_execution_performed": False,
                "platform_execution_performed": False,
                "real_platform_execution_evidence_attached": False,
                "command_session_started": False,
            }
        )
    return rows


def platform_smoke_evidence_review_readiness_rows(
    attachment_receipt: dict[str, Any],
    readiness_attachments: list[dict[str, Any]],
    status: str,
    issue_code: str | None,
) -> list[dict[str, Any]]:
    review_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    rows = []
    for attachment in readiness_attachments:
        source_attachment_id = attachment.get("readiness_evidence_attachment_id")
        descriptor_attached = attachment.get("readiness_descriptor_attached") is True
        row = {
            "readiness_review_row_id": (
                f"hostess.platform_smoke_readiness_review_row.{source_attachment_id}"
                if isinstance(source_attachment_id, str) and source_attachment_id
                else "hostess.platform_smoke_readiness_review_row.unknown"
            ),
            "source_evidence_attachment_receipt_id": attachment_receipt.get(
                "evidence_attachment_receipt_id"
            ),
            "source_readiness_evidence_attachment_id": source_attachment_id,
            "source_readiness_result_id": attachment.get("source_readiness_result_id"),
            "source_readiness_input_id": attachment.get("source_readiness_input_id"),
            "owner": attachment.get("owner"),
            "input_kind": attachment.get("input_kind"),
            "expected_source_kind": attachment.get("expected_source_kind"),
            "validation_kind": attachment.get("validation_kind"),
            "external_readiness_descriptor_id": attachment.get(
                "external_readiness_descriptor_id"
            ),
            "source_attachment_status": attachment.get("attachment_status"),
            "review_status": review_status,
            "issue_code": None if review_status == REVIEWED_STATUS else issue_code,
            "external_readiness_descriptor_supplied": attachment.get(
                "external_readiness_descriptor_supplied"
            ),
            "readiness_descriptor_attached": descriptor_attached,
            "missing_attachment": not descriptor_attached,
            "rejected_attachment": review_status == REJECTED_STATUS,
            "validated_for_attachment": attachment.get("validated_for_attachment"),
            "validated_for_execution": False,
            "studio_execution_allowed": False,
            "schema_path_execution_allowed": False,
            "execution_started": False,
            "runtime_execution_performed": False,
            "platform_execution_performed": False,
            "command_session_started": False,
        }
        if attachment.get("source_readiness_input_id") == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID:
            row.update(pmb_shell_handoff_review_summary_from_source(attachment))
        rows.append(row)
    return rows


def platform_smoke_evidence_review_row_dicts(
    evidence_review: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = evidence_review.get("evidence_review_rows", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def platform_smoke_evidence_review_readiness_row_dicts(
    evidence_review: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = evidence_review.get("readiness_review_rows", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def platform_smoke_evidence_review_rows_match_attachments(
    evidence_attachments: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {REVIEWED_STATUS, REJECTED_STATUS}:
        return False
    expected_review_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    by_id = {
        row.get("source_evidence_attachment_id"): row
        for row in review_rows
    }
    if len(review_rows) != len(evidence_attachments):
        return False
    for attachment in evidence_attachments:
        row = by_id.get(attachment.get("evidence_attachment_id"))
        if not isinstance(row, dict):
            return False
        for key in (
            "source_evidence_placeholder_id",
            "source_action_report_id",
            "source_plan_id",
            "source_plan_action_id",
            "owner",
            "route_kind",
            "required_evidence_kind",
            "external_evidence_kind",
            "external_evidence_descriptor_id",
            "external_evidence_descriptor_supplied",
            "evidence_descriptor_attached",
        ):
            if row.get(key) != attachment.get(key):
                return False
        if row.get("source_attachment_status") != attachment.get("attachment_status"):
            return False
        if row.get("review_status") != expected_review_status:
            return False
        if row.get("missing_attachment") != (
            attachment.get("evidence_descriptor_attached") is not True
        ):
            return False
        if row.get("rejected_attachment") != (expected_review_status == REJECTED_STATUS):
            return False
        if not platform_smoke_evidence_review_row_unstarted(row):
            return False
    return True


def platform_smoke_evidence_review_readiness_rows_match_attachments(
    readiness_attachments: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    status: Any,
) -> bool:
    if status not in {REVIEWED_STATUS, REJECTED_STATUS}:
        return False
    expected_review_status = REVIEWED_STATUS if status == REVIEWED_STATUS else REJECTED_STATUS
    by_id = {
        row.get("source_readiness_evidence_attachment_id"): row
        for row in review_rows
    }
    if len(review_rows) != len(readiness_attachments):
        return False
    for attachment in readiness_attachments:
        row = by_id.get(attachment.get("readiness_evidence_attachment_id"))
        if not isinstance(row, dict):
            return False
        for key in (
            "source_readiness_result_id",
            "source_readiness_input_id",
            "owner",
            "input_kind",
            "expected_source_kind",
            "validation_kind",
            "external_readiness_descriptor_id",
            "external_readiness_descriptor_supplied",
            "readiness_descriptor_attached",
            "validated_for_attachment",
        ):
            if row.get(key) != attachment.get(key):
                return False
        if row.get("source_attachment_status") != attachment.get("attachment_status"):
            return False
        if row.get("review_status") != expected_review_status:
            return False
        if (
            status == REVIEWED_STATUS
            and attachment.get("source_readiness_input_id")
            == PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
            and (
                not pmb_shell_handoff_readiness_result_summary_valid(attachment)
                or not pmb_shell_handoff_readiness_result_summary_valid(row)
            )
        ):
            return False
        if row.get("missing_attachment") != (
            attachment.get("readiness_descriptor_attached") is not True
        ):
            return False
        if row.get("rejected_attachment") != (expected_review_status == REJECTED_STATUS):
            return False
        if row.get("validated_for_execution") is not False:
            return False
        if not platform_smoke_evidence_review_readiness_row_unstarted(row):
            return False
    return True


def platform_smoke_evidence_review_row_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("evidence_payload_copied") is False
        and row.get("collection_started") is False
        and row.get("studio_execution_allowed") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("real_platform_execution_evidence_attached") is False
        and row.get("command_session_started") is False
    )


def platform_smoke_evidence_review_readiness_row_unstarted(row: dict[str, Any]) -> bool:
    return (
        row.get("studio_execution_allowed") is False
        and row.get("schema_path_execution_allowed") is False
        and row.get("execution_started") is False
        and row.get("runtime_execution_performed") is False
        and row.get("platform_execution_performed") is False
        and row.get("command_session_started") is False
    )


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


def operator_release_readiness_bundle_unstarted(bundle: dict[str, Any]) -> bool:
    return (
        all(bundle.get(flag) is False for flag in SMOKE_HANDOFF_STARTED_FLAGS)
        and bundle.get("operator_started") is False
        and bundle.get("host_shell_started") is False
        and bundle.get("device_required") is False
        and bundle.get("schema_path_execution_allowed") is False
        and bundle.get("platform_execution_allowed") is False
        and bundle.get("studio_execution_allowed") is False
        and bundle.get("runtime_execution_performed") is False
        and bundle.get("platform_execution_performed") is False
        and bundle.get("replay_execution_started") is False
        and bundle.get("apk_build_started") is False
        and bundle.get("schema_artifact_payloads_copied") is False
        and bundle.get("release_payloads_copied") is False
        and bundle.get("evidence_payloads_copied") is False
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
            "downstream_shell_select_staged_descriptor_without_legacy_rusty_xr"
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
                and receipt.get("legacy_rusty_xr_dependency_used") is False
            )
            or status == REJECTED_STATUS,
            "Hostess staged payload manifest exposes downstream shell descriptors without legacy Rusty-XR dependency",
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
                and receipt.get("legacy_rusty_xr_dependency_used") is False
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
        "legacy_rusty_xr_dependency_used": False,
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


def hostess_downstream_shell_selection_row_no_runtime_started(
    row: dict[str, Any],
) -> bool:
    return (
        row.get("legacy_rusty_xr_dependency_used") is False
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
                "legacy_rusty_xr_dependency_used": False,
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


def hostess_staged_payload_row_no_runtime_started(row: dict[str, Any]) -> bool:
    return (
        row.get("legacy_rusty_xr_dependency_used") is False
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


def validate_ack_fixture(request: dict[str, Any], ack: dict[str, Any]) -> dict[str, Any]:
    checks = [
        check(
            "hostess.check.studio_staging_ack.schema",
            ack.get("$schema") == ACK_SCHEMA,
            "ack schema is supported",
            "ack schema is unsupported",
            "hostess.issue.staging_ack_schema",
        ),
        check(
            "hostess.check.studio_staging_ack.request_id",
            ack.get("request_id") == request.get("request_id"),
            "ack request id matches request",
            "ack request id differs from request",
            "hostess.issue.staging_ack_request_mismatch",
        ),
        check(
            "hostess.check.studio_staging_ack.owner",
            ack.get("accepted_by") == HOSTESS_OWNER,
            "ack is owned by Hostess",
            "ack owner is not Hostess",
            "hostess.issue.staging_ack_owner",
        ),
        check(
            "hostess.check.studio_staging_ack.status",
            ack.get("ack_status") == ACCEPTED_STATUS,
            "ack status is accepted",
            "ack status is not accepted",
            "hostess.issue.staging_ack_status",
        ),
        check(
            "hostess.check.studio_staging_ack.no_studio_execution",
            ack.get("execution_in_studio") is False,
            "ack confirms Studio did not execute runtime actions",
            "ack allows Studio runtime execution",
            "hostess.issue.studio_execution_not_allowed",
        ),
        check(
            "hostess.check.studio_staging_ack.authority",
            ack.get("command_session_authority") == MANIFOLD_OWNER
            and ack.get("install_launch_evidence_authority") == HOSTESS_OWNER,
            "ack preserves Manifold and Hostess authority",
            "ack authority fields drifted",
            "hostess.issue.runtime_authority_mismatch",
        ),
        check(
            "hostess.check.studio_staging_ack.actions",
            ack.get("required_action_ids") == expected_action_ids(request)
            and ack.get("accepted_action_ids") == expected_action_ids(request),
            "ack accepts exactly the requested adapter actions",
            "ack action ids differ from request actions",
            "hostess.issue.staging_ack_action_mismatch",
        ),
        check(
            "hostess.check.studio_staging_ack.evidence_kinds",
            set(ack.get("required_evidence_kinds", [])) == set(REQUIRED_EVIDENCE_KINDS),
            "ack declares required evidence kinds",
            "ack evidence kinds differ from Hostess contract",
            "hostess.issue.staging_ack_evidence_kinds",
        ),
    ]
    return fixture_validation_report("ack", request, checks)


def validate_reject_fixture(request: dict[str, Any], reject: dict[str, Any]) -> dict[str, Any]:
    checks = [
        check(
            "hostess.check.studio_staging_reject.schema",
            reject.get("$schema") == REJECT_SCHEMA,
            "reject schema is supported",
            "reject schema is unsupported",
            "hostess.issue.staging_reject_schema",
        ),
        check(
            "hostess.check.studio_staging_reject.request_id",
            reject.get("request_id") == request.get("request_id"),
            "reject request id matches request",
            "reject request id differs from request",
            "hostess.issue.staging_reject_request_mismatch",
        ),
        check(
            "hostess.check.studio_staging_reject.owner",
            reject.get("rejected_by") == HOSTESS_OWNER,
            "reject is owned by Hostess",
            "reject owner is not Hostess",
            "hostess.issue.staging_reject_owner",
        ),
        check(
            "hostess.check.studio_staging_reject.status",
            reject.get("reject_status") == REJECTED_STATUS,
            "reject status is rejected",
            "reject status is not rejected",
            "hostess.issue.staging_reject_status",
        ),
        check(
            "hostess.check.studio_staging_reject.no_studio_execution",
            reject.get("execution_in_studio") is False,
            "reject confirms Studio did not execute runtime actions",
            "reject allows Studio runtime execution",
            "hostess.issue.studio_execution_not_allowed",
        ),
        check(
            "hostess.check.studio_staging_reject.actions",
            reject.get("request_action_ids") == expected_action_ids(request)
            and reject.get("rejected_action_ids") == expected_action_ids(request),
            "reject names exactly the requested adapter actions",
            "reject action ids differ from request actions",
            "hostess.issue.staging_reject_action_mismatch",
        ),
        check(
            "hostess.check.studio_staging_reject.reason",
            isinstance(reject.get("reason_code"), str) and bool(reject.get("reason_code")),
            "reject carries a reason code",
            "reject is missing a reason code",
            "hostess.issue.staging_reject_reason_missing",
        ),
    ]
    return fixture_validation_report("reject", request, checks)


def request_checks(request: dict[str, Any]) -> list[dict[str, Any]]:
    actions = request_actions(request)
    action_ids = expected_action_ids(request)
    ready_actions = [action for action in actions if action.get("status") == READY_STATUS]
    blocked_actions = [action for action in actions if action.get("status") == "blocked"]
    template_ack = request.get("ack_template", {})
    template_reject = request.get("reject_template", {})

    checks = [
        check(
            "hostess.check.studio_staging_request.schema",
            request.get("$schema") == REQUEST_SCHEMA,
            "Studio request schema is supported",
            "Studio request schema is unsupported",
            "hostess.issue.staging_request_schema",
        ),
        check(
            "hostess.check.studio_staging_request.status",
            request.get("status") == READY_STATUS and request.get("issue_code") is None,
            "Studio request is ready",
            "Studio request is not ready",
            request.get("issue_code") or "hostess.issue.staging_request_not_ready",
        ),
        check(
            "hostess.check.studio_staging_request.execution_policy",
            request.get("execution_policy") == REQUEST_POLICY,
            "request remains Hostess-request-only",
            "request execution policy changed",
            "hostess.issue.staging_request_execution_policy",
        ),
        check(
            "hostess.check.studio_staging_request.authority",
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
            "hostess.check.studio_staging_request.prohibited_studio_actions",
            all(action in request.get("prohibited_studio_actions", []) for action in REQUIRED_PROHIBITED_ACTIONS),
            "request preserves prohibited Studio runtime actions",
            "request is missing prohibited Studio runtime actions",
            "hostess.issue.prohibited_studio_actions_missing",
        ),
        check(
            "hostess.check.studio_staging_request.action_counts",
            request.get("adapter_action_count") == len(actions)
            and request.get("ready_adapter_action_count") == len(ready_actions)
            and request.get("blocked_adapter_action_count") == len(blocked_actions),
            "adapter action counts match actions",
            "adapter action counts do not match actions",
            "hostess.issue.staging_request_action_count_mismatch",
        ),
        check(
            "hostess.check.studio_staging_request.action_contracts",
            actions_match_contracts(actions),
            "adapter actions match Hostess and Manifold request contracts",
            "adapter action owner, route, ack, status, or execution fields drifted",
            "hostess.issue.adapter_action_contract_drift",
        ),
        check(
            "hostess.check.studio_staging_request.ack_template",
            isinstance(template_ack, dict)
            and template_ack.get("$schema") == ACK_SCHEMA
            and template_ack.get("request_id") == request.get("request_id")
            and template_ack.get("accepted_by") == HOSTESS_OWNER
            and template_ack.get("ack_status") == PENDING_STATUS
            and template_ack.get("execution_in_studio") is False
            and template_ack.get("required_action_ids") == action_ids
            and template_ack.get("accepted_action_ids") == []
            and set(template_ack.get("required_evidence_kinds", [])) == set(REQUIRED_EVIDENCE_KINDS),
            "ack template is pending, Hostess-owned, and action complete",
            "ack template drifted from Hostess contract",
            "hostess.issue.staging_ack_template_drift",
        ),
        check(
            "hostess.check.studio_staging_request.reject_template",
            isinstance(template_reject, dict)
            and template_reject.get("$schema") == REJECT_SCHEMA
            and template_reject.get("request_id") == request.get("request_id")
            and template_reject.get("rejected_by") == HOSTESS_OWNER
            and template_reject.get("reject_status") == PENDING_STATUS
            and template_reject.get("execution_in_studio") is False
            and template_reject.get("request_action_ids") == action_ids
            and template_reject.get("rejected_action_ids") == []
            and template_reject.get("next_required_action")
            == "hostess_ack_or_reject_request_outside_studio",
            "reject template is pending, Hostess-owned, and action complete",
            "reject template drifted from Hostess contract",
            "hostess.issue.staging_reject_template_drift",
        ),
    ]
    return checks


def actions_match_contracts(actions: list[dict[str, Any]]) -> bool:
    if not actions:
        return False
    for action in actions:
        action_id = action.get("action_id")
        owner = action.get("owner")
        route = action.get("route_kind")
        expected_route = HOSTESS_ACTION_ROUTES.get(action_id) or MANIFOLD_ACTION_ROUTES.get(action_id)
        expected_owner = MANIFOLD_OWNER if action_id in MANIFOLD_ACTION_ROUTES else HOSTESS_OWNER
        if action_id not in HOSTESS_ACTION_ROUTES and action_id not in MANIFOLD_ACTION_ROUTES:
            return False
        if owner != expected_owner or action.get("responsible_authority") != owner:
            return False
        if route != expected_route:
            return False
        if action.get("status") != READY_STATUS:
            return False
        if action.get("ack_required") is not True:
            return False
        if action.get("execution_in_studio") is not False:
            return False
    return True


def request_actions(request: dict[str, Any]) -> list[dict[str, Any]]:
    actions = request.get("actions", [])
    if not isinstance(actions, list):
        return []
    return [action for action in actions if isinstance(action, dict)]


def expected_action_ids(request: dict[str, Any]) -> list[str]:
    return [
        action["action_id"]
        for action in request_actions(request)
        if isinstance(action.get("action_id"), str)
    ]


def fixture_validation_report(
    fixture_kind: str,
    request: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = [check for check in checks if check["status"] == FAIL_STATUS]
    return {
        "$schema": "rusty.hostess.studio_staging_execution_fixture_validation.v1",
        "fixture_kind": fixture_kind,
        "request_id": request.get("request_id"),
        "status": PASS_STATUS if not failed else FAIL_STATUS,
        "issue_code": failed[0]["issue_code"] if failed else None,
        "execution_performed": False,
        "checks": checks,
    }


def check(
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


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="studio-staging-request",
        description="Validate Studio staging execution requests without executing Hostess runtime actions.",
    )
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--report-out", type=Path)
    parser.add_argument("--ack-out", type=Path)
    parser.add_argument("--reject-out", type=Path)
    parser.add_argument("--smoke-handoff-in", type=Path)
    parser.add_argument("--smoke-handoff-out", type=Path)
    parser.add_argument("--smoke-dry-run-request-in", type=Path)
    parser.add_argument("--smoke-dry-run-request-out", type=Path)
    parser.add_argument("--smoke-dry-run-receipt-in", type=Path)
    parser.add_argument("--smoke-dry-run-receipt-out", type=Path)
    parser.add_argument("--smoke-preflight-in", type=Path)
    parser.add_argument("--smoke-preflight-out", type=Path)
    parser.add_argument("--smoke-host-shell-execution-in", type=Path)
    parser.add_argument("--smoke-host-shell-execution-out", type=Path)
    parser.add_argument("--smoke-review-bundle-in", type=Path)
    parser.add_argument("--smoke-review-bundle-out", type=Path)
    parser.add_argument("--platform-smoke-plan-in", type=Path)
    parser.add_argument("--platform-smoke-plan-out", type=Path)
    parser.add_argument("--platform-smoke-approval-in", type=Path)
    parser.add_argument("--platform-smoke-approval-out", type=Path)
    parser.add_argument("--platform-smoke-rejection-out", type=Path)
    parser.add_argument("--platform-smoke-execution-request-in", type=Path)
    parser.add_argument("--platform-smoke-execution-request-out", type=Path)
    parser.add_argument("--platform-smoke-execution-receipt-in", type=Path)
    parser.add_argument("--platform-smoke-execution-receipt-out", type=Path)
    parser.add_argument("--platform-smoke-operator-start-gate-in", type=Path)
    parser.add_argument("--platform-smoke-operator-start-gate-out", type=Path)
    parser.add_argument("--platform-smoke-operator-start-preflight-in", type=Path)
    parser.add_argument("--platform-smoke-operator-start-preflight-out", type=Path)
    parser.add_argument("--platform-smoke-operator-start-preflight-rejection-out", type=Path)
    parser.add_argument("--platform-smoke-execution-report-in", type=Path)
    parser.add_argument("--platform-smoke-execution-report-out", type=Path)
    parser.add_argument("--platform-smoke-execution-report-rejection-out", type=Path)
    parser.add_argument("--platform-smoke-evidence-attachment-in", type=Path)
    parser.add_argument("--platform-smoke-evidence-attachment-out", type=Path)
    parser.add_argument("--platform-smoke-evidence-attachment-rejection-out", type=Path)
    parser.add_argument("--platform-smoke-evidence-review-in", type=Path)
    parser.add_argument("--platform-smoke-evidence-review-out", type=Path)
    parser.add_argument("--platform-smoke-evidence-review-rejection-out", type=Path)
    parser.add_argument("--pmb-authoring-review-in", type=Path)
    parser.add_argument("--pmb-package-evidence-intake-in", type=Path)
    parser.add_argument("--pmb-source-adapter-selection-in", type=Path)
    parser.add_argument("--pmb-shell-handoff-review-in", type=Path)
    parser.add_argument("--require-pmb-shell-handoff-review", action="store_true")
    parser.add_argument("--pmb-validation-handoff-in", type=Path)
    parser.add_argument("--pmb-validation-handoff-out", type=Path)
    parser.add_argument("--pmb-replay-descriptors-in", type=Path)
    parser.add_argument("--pmb-replay-validation-receipt-in", type=Path)
    parser.add_argument("--pmb-replay-validation-receipt-out", type=Path)
    parser.add_argument("--operator-release-readiness-bundle-in", type=Path)
    parser.add_argument("--operator-release-readiness-bundle-out", type=Path)
    parser.add_argument("--operator-release-readiness-bundle-rejection-out", type=Path)
    parser.add_argument("--hostess-staging-file-plan-in", type=Path)
    parser.add_argument("--hostess-staging-handoff-in", type=Path)
    parser.add_argument("--hostess-staging-acceptance-manifest-in", type=Path)
    parser.add_argument("--hostess-staging-handoff-acceptance-receipt-in", type=Path)
    parser.add_argument("--hostess-staging-handoff-acceptance-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-staging-handoff-acceptance-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-staging-file-plan-receipt-in", type=Path)
    parser.add_argument("--hostess-staging-file-plan-receipt-out", type=Path)
    parser.add_argument("--hostess-staging-file-plan-receipt-rejection-out", type=Path)
    parser.add_argument("--hostess-staging-file-copy-receipt-in", type=Path)
    parser.add_argument("--hostess-staging-file-copy-receipt-out", type=Path)
    parser.add_argument("--hostess-staging-file-copy-receipt-rejection-out", type=Path)
    parser.add_argument("--hostess-staged-payload-manifest-receipt-in", type=Path)
    parser.add_argument("--hostess-staged-payload-manifest-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-staged-payload-manifest-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-downstream-shell-selection-receipt-in", type=Path)
    parser.add_argument("--hostess-downstream-shell-selection-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-downstream-shell-selection-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--manifold-shell-handoff-review-receipt-in", type=Path)
    parser.add_argument(
        "--hostess-manifold-shell-handoff-review-intake-receipt-in",
        type=Path,
    )
    parser.add_argument(
        "--hostess-manifold-shell-handoff-review-intake-receipt-out",
        type=Path,
    )
    parser.add_argument(
        "--hostess-manifold-shell-handoff-review-intake-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-makepad-shell-contract-receipt-in", type=Path)
    parser.add_argument("--hostess-makepad-shell-contract-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-makepad-shell-contract-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-makepad-shell-launch-handoff-receipt-in", type=Path)
    parser.add_argument("--hostess-makepad-shell-launch-handoff-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-makepad-shell-launch-handoff-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-downstream-shell-selection-target-kind")
    parser.add_argument("--hostess-downstream-shell-selection-graph-id")
    parser.add_argument("--hostess-downstream-shell-selection-consumer-id")
    parser.add_argument("--hostess-staging-root", default="hostess-staging")
    parser.add_argument("--target-profile", default="hostess.t.schema_smoke")
    parser.add_argument("--target-platform", default="hostess.platform_smoke.operator_controlled")
    parser.add_argument("--host-shell-kind", default="hostess.t_or_dedicated_quest_host_shell")
    parser.add_argument("--validate-ack", type=Path)
    parser.add_argument("--validate-reject", type=Path)
    parser.add_argument("--validate-smoke-handoff", type=Path)
    parser.add_argument("--validate-smoke-dry-run-request", type=Path)
    parser.add_argument("--validate-smoke-dry-run-receipt", type=Path)
    parser.add_argument("--validate-smoke-preflight", type=Path)
    parser.add_argument("--validate-smoke-host-shell-execution", type=Path)
    parser.add_argument("--validate-smoke-review-bundle", type=Path)
    parser.add_argument("--validate-platform-smoke-plan", type=Path)
    parser.add_argument("--validate-platform-smoke-approval", type=Path)
    parser.add_argument("--validate-platform-smoke-execution-request", type=Path)
    parser.add_argument("--validate-platform-smoke-execution-receipt", type=Path)
    parser.add_argument("--validate-platform-smoke-operator-start-gate", type=Path)
    parser.add_argument("--validate-platform-smoke-operator-start-preflight", type=Path)
    parser.add_argument("--validate-platform-smoke-execution-report", type=Path)
    parser.add_argument("--validate-platform-smoke-evidence-attachment", type=Path)
    parser.add_argument("--validate-platform-smoke-evidence-review", type=Path)
    parser.add_argument("--validate-pmb-validation-handoff", type=Path)
    parser.add_argument("--validate-pmb-replay-validation-receipt", type=Path)
    parser.add_argument("--validate-operator-release-readiness-bundle", type=Path)
    parser.add_argument("--validate-hostess-staging-handoff-acceptance-receipt", type=Path)
    parser.add_argument("--validate-hostess-staging-file-plan-receipt", type=Path)
    parser.add_argument("--validate-hostess-staging-file-copy-receipt", type=Path)
    parser.add_argument("--validate-hostess-staged-payload-manifest-receipt", type=Path)
    parser.add_argument("--validate-hostess-downstream-shell-selection-receipt", type=Path)
    parser.add_argument(
        "--validate-hostess-manifold-shell-handoff-review-intake-receipt",
        type=Path,
    )
    parser.add_argument("--validate-hostess-makepad-shell-contract-receipt", type=Path)
    parser.add_argument("--validate-hostess-makepad-shell-launch-handoff-receipt", type=Path)
    args = parser.parse_args()

    request = load_json(args.request)
    report = build_intake_report(request, args.request)
    ack_fixture = build_ack_fixture(request) if report["status"] == ACCEPTED_STATUS else None
    smoke_handoff = load_json(args.smoke_handoff_in) if args.smoke_handoff_in else None
    dry_run_request = load_json(args.smoke_dry_run_request_in) if args.smoke_dry_run_request_in else None
    dry_run_receipt = load_json(args.smoke_dry_run_receipt_in) if args.smoke_dry_run_receipt_in else None
    smoke_preflight = load_json(args.smoke_preflight_in) if args.smoke_preflight_in else None
    host_shell_execution = (
        load_json(args.smoke_host_shell_execution_in) if args.smoke_host_shell_execution_in else None
    )
    smoke_review_bundle = load_json(args.smoke_review_bundle_in) if args.smoke_review_bundle_in else None
    platform_smoke_plan = load_json(args.platform_smoke_plan_in) if args.platform_smoke_plan_in else None
    platform_smoke_approval = (
        load_json(args.platform_smoke_approval_in) if args.platform_smoke_approval_in else None
    )
    platform_smoke_execution_request = (
        load_json(args.platform_smoke_execution_request_in)
        if args.platform_smoke_execution_request_in
        else None
    )
    platform_smoke_execution_receipt = (
        load_json(args.platform_smoke_execution_receipt_in)
        if args.platform_smoke_execution_receipt_in
        else None
    )
    platform_smoke_operator_start_gate = (
        load_json(args.platform_smoke_operator_start_gate_in)
        if args.platform_smoke_operator_start_gate_in
        else None
    )
    platform_smoke_operator_start_preflight = (
        load_json(args.platform_smoke_operator_start_preflight_in)
        if args.platform_smoke_operator_start_preflight_in
        else None
    )
    platform_smoke_execution_report = (
        load_json(args.platform_smoke_execution_report_in)
        if args.platform_smoke_execution_report_in
        else None
    )
    platform_smoke_evidence_attachment = (
        load_json(args.platform_smoke_evidence_attachment_in)
        if args.platform_smoke_evidence_attachment_in
        else None
    )
    platform_smoke_evidence_review = (
        load_json(args.platform_smoke_evidence_review_in)
        if args.platform_smoke_evidence_review_in
        else None
    )
    pmb_authoring_review = (
        load_json(args.pmb_authoring_review_in)
        if args.pmb_authoring_review_in
        else None
    )
    pmb_package_evidence_intake = (
        load_json(args.pmb_package_evidence_intake_in)
        if args.pmb_package_evidence_intake_in
        else None
    )
    pmb_source_adapter_selection = (
        load_json(args.pmb_source_adapter_selection_in)
        if args.pmb_source_adapter_selection_in
        else None
    )
    request_pmb_shell_handoff_review_path = request_relative_path(
        args.request,
        request.get("pmb_shell_handoff_review_path"),
    )
    pmb_shell_handoff_review_path = (
        args.pmb_shell_handoff_review_in
        if args.pmb_shell_handoff_review_in
        else request_pmb_shell_handoff_review_path
    )
    pmb_shell_handoff_review_required = (
        args.require_pmb_shell_handoff_review
        or request.get("pmb_shell_handoff_review_required") is True
    )
    pmb_shell_handoff_review = (
        load_json(pmb_shell_handoff_review_path)
        if pmb_shell_handoff_review_path
        else None
    )
    pmb_validation_handoff = (
        load_json(args.pmb_validation_handoff_in)
        if args.pmb_validation_handoff_in
        else None
    )
    pmb_replay_descriptors = (
        load_json(args.pmb_replay_descriptors_in)
        if args.pmb_replay_descriptors_in
        else None
    )
    pmb_replay_validation_receipt = (
        load_json(args.pmb_replay_validation_receipt_in)
        if args.pmb_replay_validation_receipt_in
        else None
    )
    operator_release_readiness_bundle = (
        load_json(args.operator_release_readiness_bundle_in)
        if args.operator_release_readiness_bundle_in
        else None
    )
    request_staging_handoff_path = request_relative_path(
        args.request,
        request.get("handoff_path"),
    )
    request_staging_file_plan_path = request_relative_path(
        args.request,
        request.get("file_plan_path"),
    )
    request_staging_acceptance_manifest_path = request_relative_path(
        args.request,
        request.get("acceptance_manifest_path"),
    )
    staging_file_plan_path = (
        args.hostess_staging_file_plan_in
        if args.hostess_staging_file_plan_in
        else request_staging_file_plan_path
    )
    staging_handoff_path = (
        args.hostess_staging_handoff_in
        if args.hostess_staging_handoff_in
        else request_staging_handoff_path
    )
    staging_acceptance_manifest_path = (
        args.hostess_staging_acceptance_manifest_in
        if args.hostess_staging_acceptance_manifest_in
        else request_staging_acceptance_manifest_path
    )
    staging_file_plan = (
        load_json(staging_file_plan_path) if staging_file_plan_path else None
    )
    staging_handoff = load_json(staging_handoff_path) if staging_handoff_path else None
    staging_acceptance_manifest = (
        load_json(staging_acceptance_manifest_path)
        if staging_acceptance_manifest_path
        else None
    )
    staging_handoff_acceptance_receipt = (
        load_json(args.hostess_staging_handoff_acceptance_receipt_in)
        if args.hostess_staging_handoff_acceptance_receipt_in
        else None
    )
    staging_file_plan_receipt = (
        load_json(args.hostess_staging_file_plan_receipt_in)
        if args.hostess_staging_file_plan_receipt_in
        else None
    )
    staging_file_copy_receipt = (
        load_json(args.hostess_staging_file_copy_receipt_in)
        if args.hostess_staging_file_copy_receipt_in
        else None
    )
    staged_payload_manifest_receipt = (
        load_json(args.hostess_staged_payload_manifest_receipt_in)
        if args.hostess_staged_payload_manifest_receipt_in
        else None
    )
    downstream_shell_selection_receipt = (
        load_json(args.hostess_downstream_shell_selection_receipt_in)
        if args.hostess_downstream_shell_selection_receipt_in
        else None
    )
    manifold_shell_handoff_review_receipt = (
        load_json(args.manifold_shell_handoff_review_receipt_in)
        if args.manifold_shell_handoff_review_receipt_in
        else None
    )
    manifold_shell_handoff_review_intake_receipt = (
        load_json(args.hostess_manifold_shell_handoff_review_intake_receipt_in)
        if args.hostess_manifold_shell_handoff_review_intake_receipt_in
        else None
    )
    makepad_shell_contract_receipt = (
        load_json(args.hostess_makepad_shell_contract_receipt_in)
        if args.hostess_makepad_shell_contract_receipt_in
        else None
    )
    makepad_shell_launch_handoff_receipt = (
        load_json(args.hostess_makepad_shell_launch_handoff_receipt_in)
        if args.hostess_makepad_shell_launch_handoff_receipt_in
        else None
    )
    if args.report_out:
        write_json(args.report_out, report)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    if args.ack_out and ack_fixture is not None:
        write_json(args.ack_out, ack_fixture)
    if args.reject_out:
        write_json(args.reject_out, build_reject_fixture(request))
    if args.pmb_validation_handoff_out:
        if pmb_validation_handoff is None:
            if pmb_authoring_review is None:
                raise ValueError(
                    "--pmb-authoring-review-in is required when building a PMB validation handoff"
                )
            pmb_validation_handoff = build_projected_motion_breath_validation_handoff(
                pmb_authoring_review,
                pmb_package_evidence_intake,
                args.pmb_authoring_review_in,
                args.pmb_package_evidence_intake_in,
                pmb_source_adapter_selection,
                args.pmb_source_adapter_selection_in,
            )
        write_json(args.pmb_validation_handoff_out, pmb_validation_handoff)
    if args.pmb_replay_validation_receipt_out:
        if pmb_replay_validation_receipt is None:
            if pmb_validation_handoff is None:
                if pmb_authoring_review is None:
                    raise ValueError(
                        "--pmb-validation-handoff-in or --pmb-authoring-review-in "
                        "is required when building a PMB replay validation receipt"
                    )
                pmb_validation_handoff = build_projected_motion_breath_validation_handoff(
                    pmb_authoring_review,
                    pmb_package_evidence_intake,
                    args.pmb_authoring_review_in,
                    args.pmb_package_evidence_intake_in,
                    pmb_source_adapter_selection,
                    args.pmb_source_adapter_selection_in,
                )
            pmb_replay_validation_receipt = (
                build_projected_motion_breath_replay_validation_receipt(
                    pmb_validation_handoff,
                    pmb_replay_descriptors,
                    args.pmb_replay_descriptors_in,
                )
            )
        write_json(args.pmb_replay_validation_receipt_out, pmb_replay_validation_receipt)
    if args.smoke_handoff_out:
        if smoke_handoff is None:
            smoke_handoff = build_smoke_handoff_checklist(
                request,
                report,
                ack_fixture,
                target_profile=args.target_profile,
            )
        write_json(
            args.smoke_handoff_out,
            smoke_handoff,
        )
    if (
        args.smoke_dry_run_request_out
        or args.smoke_dry_run_receipt_out
        or args.smoke_preflight_out
        or args.smoke_host_shell_execution_out
        or args.smoke_review_bundle_out
        or args.platform_smoke_plan_out
        or args.platform_smoke_approval_out
        or args.platform_smoke_rejection_out
        or args.platform_smoke_execution_request_out
        or args.platform_smoke_execution_receipt_out
        or args.platform_smoke_operator_start_gate_out
        or args.platform_smoke_operator_start_preflight_out
        or args.platform_smoke_operator_start_preflight_rejection_out
        or args.platform_smoke_execution_report_out
        or args.platform_smoke_execution_report_rejection_out
        or args.platform_smoke_evidence_attachment_out
        or args.platform_smoke_evidence_attachment_rejection_out
        or args.platform_smoke_evidence_review_out
        or args.platform_smoke_evidence_review_rejection_out
        or args.operator_release_readiness_bundle_out
        or args.operator_release_readiness_bundle_rejection_out
        or args.hostess_staging_handoff_acceptance_receipt_out
        or args.hostess_staging_handoff_acceptance_receipt_rejection_out
        or args.hostess_staging_file_plan_receipt_out
        or args.hostess_staging_file_plan_receipt_rejection_out
        or args.hostess_staging_file_copy_receipt_out
        or args.hostess_staging_file_copy_receipt_rejection_out
        or args.hostess_staged_payload_manifest_receipt_out
        or args.hostess_staged_payload_manifest_receipt_rejection_out
        or args.hostess_staged_payload_manifest_receipt_out
        or args.hostess_staged_payload_manifest_receipt_rejection_out
    ):
        if smoke_handoff is None:
            smoke_handoff = build_smoke_handoff_checklist(
                request,
                report,
                ack_fixture,
                target_profile=args.target_profile,
            )
        if dry_run_request is None:
            dry_run_request = build_smoke_dry_run_request(
                smoke_handoff,
                target_profile=args.target_profile,
            )
        if args.smoke_dry_run_request_out:
            write_json(args.smoke_dry_run_request_out, dry_run_request)
        if args.smoke_dry_run_receipt_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            write_json(args.smoke_dry_run_receipt_out, dry_run_receipt)
        if args.smoke_preflight_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            write_json(
                args.smoke_preflight_out,
                smoke_preflight,
            )
        if args.smoke_host_shell_execution_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            write_json(
                args.smoke_host_shell_execution_out,
                host_shell_execution,
            )
        if args.smoke_review_bundle_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            write_json(
                args.smoke_review_bundle_out,
                smoke_review_bundle,
            )
        if args.platform_smoke_plan_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            write_json(
                args.platform_smoke_plan_out,
                platform_smoke_plan,
            )
        if args.platform_smoke_approval_out or args.platform_smoke_rejection_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if args.platform_smoke_approval_out:
                if platform_smoke_approval is None:
                    platform_smoke_approval = build_platform_smoke_approval_receipt(
                        platform_smoke_plan,
                        decision=APPROVED_STATUS,
                    )
                write_json(
                    args.platform_smoke_approval_out,
                    platform_smoke_approval,
                )
            if args.platform_smoke_rejection_out:
                write_json(
                    args.platform_smoke_rejection_out,
                    build_platform_smoke_approval_receipt(
                        platform_smoke_plan,
                        decision=REJECTED_STATUS,
                        reason_code="hostess.issue.operator_rejected_platform_smoke_plan",
                    ),
                )
        if args.platform_smoke_execution_request_out or args.platform_smoke_execution_receipt_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if platform_smoke_approval is None:
                platform_smoke_approval = build_platform_smoke_approval_receipt(
                    platform_smoke_plan,
                    decision=APPROVED_STATUS,
                )
            if platform_smoke_execution_request is None:
                platform_smoke_execution_request = build_platform_smoke_execution_request(
                    platform_smoke_plan,
                    platform_smoke_approval,
                )
            if args.platform_smoke_execution_request_out:
                write_json(
                    args.platform_smoke_execution_request_out,
                    platform_smoke_execution_request,
                )
            if args.platform_smoke_execution_receipt_out:
                if platform_smoke_execution_receipt is None:
                    platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                        platform_smoke_plan,
                        platform_smoke_approval,
                        platform_smoke_execution_request,
                    )
                write_json(
                    args.platform_smoke_execution_receipt_out,
                    platform_smoke_execution_receipt,
                )
        if args.platform_smoke_operator_start_gate_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if platform_smoke_approval is None:
                platform_smoke_approval = build_platform_smoke_approval_receipt(
                    platform_smoke_plan,
                    decision=APPROVED_STATUS,
                )
            if platform_smoke_execution_request is None:
                platform_smoke_execution_request = build_platform_smoke_execution_request(
                    platform_smoke_plan,
                    platform_smoke_approval,
                )
            if platform_smoke_execution_receipt is None:
                platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                )
            if platform_smoke_operator_start_gate is None:
                platform_smoke_operator_start_gate = build_platform_smoke_operator_start_gate(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    host_shell_kind=args.host_shell_kind,
                )
            write_json(
                args.platform_smoke_operator_start_gate_out,
                platform_smoke_operator_start_gate,
            )
        if (
            args.platform_smoke_operator_start_preflight_out
            or args.platform_smoke_operator_start_preflight_rejection_out
            or args.platform_smoke_execution_report_out
            or args.platform_smoke_execution_report_rejection_out
            or args.platform_smoke_evidence_attachment_out
            or args.platform_smoke_evidence_attachment_rejection_out
            or args.platform_smoke_evidence_review_out
            or args.platform_smoke_evidence_review_rejection_out
            or args.operator_release_readiness_bundle_out
            or args.operator_release_readiness_bundle_rejection_out
        ):
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if platform_smoke_approval is None:
                platform_smoke_approval = build_platform_smoke_approval_receipt(
                    platform_smoke_plan,
                    decision=APPROVED_STATUS,
                )
            if platform_smoke_execution_request is None:
                platform_smoke_execution_request = build_platform_smoke_execution_request(
                    platform_smoke_plan,
                    platform_smoke_approval,
                )
            if platform_smoke_execution_receipt is None:
                platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                )
            if platform_smoke_operator_start_gate is None:
                platform_smoke_operator_start_gate = build_platform_smoke_operator_start_gate(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    host_shell_kind=args.host_shell_kind,
                )
            if args.platform_smoke_operator_start_preflight_out:
                if platform_smoke_operator_start_preflight is None:
                    platform_smoke_operator_start_preflight = (
                        build_platform_smoke_operator_start_preflight_receipt(
                            platform_smoke_plan,
                            platform_smoke_approval,
                            platform_smoke_execution_request,
                            platform_smoke_execution_receipt,
                            platform_smoke_operator_start_gate,
                            decision=APPROVED_STATUS,
                            pmb_shell_handoff_review=pmb_shell_handoff_review,
                            pmb_shell_handoff_review_path=pmb_shell_handoff_review_path,
                            require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
                        )
                    )
                write_json(
                    args.platform_smoke_operator_start_preflight_out,
                    platform_smoke_operator_start_preflight,
                )
            if args.platform_smoke_operator_start_preflight_rejection_out:
                write_json(
                    args.platform_smoke_operator_start_preflight_rejection_out,
                    build_platform_smoke_operator_start_preflight_receipt(
                        platform_smoke_plan,
                        platform_smoke_approval,
                        platform_smoke_execution_request,
                        platform_smoke_execution_receipt,
                        platform_smoke_operator_start_gate,
                        decision=REJECTED_STATUS,
                        reason_code="hostess.issue.operator_rejected_platform_smoke_operator_start_preflight",
                        pmb_shell_handoff_review=pmb_shell_handoff_review,
                        pmb_shell_handoff_review_path=pmb_shell_handoff_review_path,
                        require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
                    ),
                )
            if (
                args.platform_smoke_execution_report_out
                or args.platform_smoke_execution_report_rejection_out
                or args.platform_smoke_evidence_attachment_out
                or args.platform_smoke_evidence_attachment_rejection_out
                or args.platform_smoke_evidence_review_out
                or args.platform_smoke_evidence_review_rejection_out
                or args.operator_release_readiness_bundle_out
                or args.operator_release_readiness_bundle_rejection_out
            ):
                if platform_smoke_operator_start_preflight is None:
                    platform_smoke_operator_start_preflight = (
                        build_platform_smoke_operator_start_preflight_receipt(
                            platform_smoke_plan,
                            platform_smoke_approval,
                            platform_smoke_execution_request,
                            platform_smoke_execution_receipt,
                            platform_smoke_operator_start_gate,
                            decision=APPROVED_STATUS,
                            pmb_shell_handoff_review=pmb_shell_handoff_review,
                            pmb_shell_handoff_review_path=pmb_shell_handoff_review_path,
                            require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
                        )
                    )
                if args.platform_smoke_execution_report_out:
                    if platform_smoke_execution_report is None:
                        platform_smoke_execution_report = (
                            build_platform_smoke_execution_report(
                                platform_smoke_plan,
                                platform_smoke_approval,
                                platform_smoke_execution_request,
                                platform_smoke_execution_receipt,
                                platform_smoke_operator_start_gate,
                                platform_smoke_operator_start_preflight,
                            )
                        )
                    write_json(
                        args.platform_smoke_execution_report_out,
                        platform_smoke_execution_report,
                    )
                if args.platform_smoke_execution_report_rejection_out:
                    write_json(
                        args.platform_smoke_execution_report_rejection_out,
                        build_platform_smoke_execution_report(
                            platform_smoke_plan,
                            platform_smoke_approval,
                            platform_smoke_execution_request,
                            platform_smoke_execution_receipt,
                            platform_smoke_operator_start_gate,
                            platform_smoke_operator_start_preflight,
                            outcome=REJECTED_STATUS,
                            reason_code="hostess.issue.operator_rejected_platform_smoke_execution_report",
                        ),
                    )
                if (
                    args.platform_smoke_evidence_attachment_out
                    or args.platform_smoke_evidence_attachment_rejection_out
                    or args.platform_smoke_evidence_review_out
                    or args.platform_smoke_evidence_review_rejection_out
                    or args.operator_release_readiness_bundle_out
                    or args.operator_release_readiness_bundle_rejection_out
                ):
                    if platform_smoke_execution_report is None:
                        platform_smoke_execution_report = (
                            build_platform_smoke_execution_report(
                                platform_smoke_plan,
                                platform_smoke_approval,
                                platform_smoke_execution_request,
                                platform_smoke_execution_receipt,
                                platform_smoke_operator_start_gate,
                                platform_smoke_operator_start_preflight,
                            )
                        )
                    if args.platform_smoke_evidence_attachment_out:
                        if platform_smoke_evidence_attachment is None:
                            platform_smoke_evidence_attachment = (
                                build_platform_smoke_evidence_attachment_receipt(
                                    platform_smoke_plan,
                                    platform_smoke_approval,
                                    platform_smoke_execution_request,
                                    platform_smoke_execution_receipt,
                                    platform_smoke_operator_start_gate,
                                    platform_smoke_operator_start_preflight,
                                    platform_smoke_execution_report,
                                )
                            )
                        write_json(
                            args.platform_smoke_evidence_attachment_out,
                            platform_smoke_evidence_attachment,
                        )
                    if args.platform_smoke_evidence_attachment_rejection_out:
                        write_json(
                            args.platform_smoke_evidence_attachment_rejection_out,
                            build_platform_smoke_evidence_attachment_receipt(
                                platform_smoke_plan,
                                platform_smoke_approval,
                                platform_smoke_execution_request,
                                platform_smoke_execution_receipt,
                                platform_smoke_operator_start_gate,
                                platform_smoke_operator_start_preflight,
                                platform_smoke_execution_report,
                                decision=REJECTED_STATUS,
                                reason_code="hostess.issue.operator_rejected_platform_smoke_evidence_attachment",
                            ),
                        )
                    if (
                        args.platform_smoke_evidence_review_out
                        or args.platform_smoke_evidence_review_rejection_out
                        or args.operator_release_readiness_bundle_out
                        or args.operator_release_readiness_bundle_rejection_out
                    ):
                        if platform_smoke_evidence_attachment is None:
                            platform_smoke_evidence_attachment = (
                                build_platform_smoke_evidence_attachment_receipt(
                                    platform_smoke_plan,
                                    platform_smoke_approval,
                                    platform_smoke_execution_request,
                                    platform_smoke_execution_receipt,
                                    platform_smoke_operator_start_gate,
                                    platform_smoke_operator_start_preflight,
                                    platform_smoke_execution_report,
                                )
                            )
                        if args.platform_smoke_evidence_review_out:
                            if platform_smoke_evidence_review is None:
                                platform_smoke_evidence_review = (
                                    build_platform_smoke_evidence_review(
                                        platform_smoke_plan,
                                        platform_smoke_approval,
                                        platform_smoke_execution_request,
                                        platform_smoke_execution_receipt,
                                        platform_smoke_operator_start_gate,
                                        platform_smoke_operator_start_preflight,
                                        platform_smoke_execution_report,
                                        platform_smoke_evidence_attachment,
                                    )
                                )
                            write_json(
                                args.platform_smoke_evidence_review_out,
                                platform_smoke_evidence_review,
                            )
                        if args.platform_smoke_evidence_review_rejection_out:
                            write_json(
                                args.platform_smoke_evidence_review_rejection_out,
                                build_platform_smoke_evidence_review(
                                    platform_smoke_plan,
                                    platform_smoke_approval,
                                    platform_smoke_execution_request,
                                    platform_smoke_execution_receipt,
                                    platform_smoke_operator_start_gate,
                                    platform_smoke_operator_start_preflight,
                                    platform_smoke_execution_report,
                                    platform_smoke_evidence_attachment,
                                    decision=REJECTED_STATUS,
                                    reason_code="hostess.issue.operator_rejected_platform_smoke_evidence_review",
                                ),
                            )
                        if (
                            args.operator_release_readiness_bundle_out
                            or args.operator_release_readiness_bundle_rejection_out
                            or args.hostess_staging_handoff_acceptance_receipt_out
                            or args.hostess_staging_handoff_acceptance_receipt_rejection_out
                            or args.hostess_staging_file_plan_receipt_out
                            or args.hostess_staging_file_plan_receipt_rejection_out
                            or args.hostess_staging_file_copy_receipt_out
                            or args.hostess_staging_file_copy_receipt_rejection_out
                            or args.hostess_staged_payload_manifest_receipt_out
                            or args.hostess_staged_payload_manifest_receipt_rejection_out
                        ):
                            if platform_smoke_evidence_review is None:
                                platform_smoke_evidence_review = (
                                    build_platform_smoke_evidence_review(
                                        platform_smoke_plan,
                                        platform_smoke_approval,
                                        platform_smoke_execution_request,
                                        platform_smoke_execution_receipt,
                                        platform_smoke_operator_start_gate,
                                        platform_smoke_operator_start_preflight,
                                        platform_smoke_execution_report,
                                        platform_smoke_evidence_attachment,
                                    )
                                )
                            if pmb_replay_validation_receipt is None:
                                if pmb_validation_handoff is None:
                                    if pmb_authoring_review is None:
                                        raise ValueError(
                                            "--pmb-replay-validation-receipt-in or "
                                            "--pmb-authoring-review-in is required when "
                                            "building an operator release readiness bundle"
                                        )
                                    pmb_validation_handoff = (
                                        build_projected_motion_breath_validation_handoff(
                                            pmb_authoring_review,
                                            pmb_package_evidence_intake,
                                            args.pmb_authoring_review_in,
                                            args.pmb_package_evidence_intake_in,
                                            pmb_source_adapter_selection,
                                            args.pmb_source_adapter_selection_in,
                                        )
                                    )
                                pmb_replay_validation_receipt = (
                                    build_projected_motion_breath_replay_validation_receipt(
                                        pmb_validation_handoff,
                                        pmb_replay_descriptors,
                                        args.pmb_replay_descriptors_in,
                                    )
                                )
                            if args.operator_release_readiness_bundle_out:
                                if operator_release_readiness_bundle is None:
                                    operator_release_readiness_bundle = (
                                        build_operator_release_readiness_bundle(
                                            platform_smoke_evidence_review,
                                            pmb_replay_validation_receipt,
                                        )
                                    )
                                write_json(
                                    args.operator_release_readiness_bundle_out,
                                    operator_release_readiness_bundle,
                                )
                            if args.operator_release_readiness_bundle_rejection_out:
                                write_json(
                                    args.operator_release_readiness_bundle_rejection_out,
                                    build_operator_release_readiness_bundle(
                                        platform_smoke_evidence_review,
                                        pmb_replay_validation_receipt,
                                        decision=REJECTED_STATUS,
                                        reason_code=(
                                            "hostess.issue.operator_rejected_operator_release_readiness_bundle"
                                        ),
                                    ),
                                )
                            if (
                                args.hostess_staging_handoff_acceptance_receipt_out
                                or args.hostess_staging_handoff_acceptance_receipt_rejection_out
                                or args.hostess_staging_file_plan_receipt_out
                                or args.hostess_staging_file_plan_receipt_rejection_out
                                or args.hostess_staging_file_copy_receipt_out
                                or args.hostess_staging_file_copy_receipt_rejection_out
                                or args.hostess_staged_payload_manifest_receipt_out
                                or args.hostess_staged_payload_manifest_receipt_rejection_out
                            ):
                                if operator_release_readiness_bundle is None:
                                    operator_release_readiness_bundle = (
                                        build_operator_release_readiness_bundle(
                                            platform_smoke_evidence_review,
                                            pmb_replay_validation_receipt,
                                        )
                                    )
                                if staging_handoff is None:
                                    raise ValueError(
                                        "--hostess-staging-handoff-in or request handoff_path "
                                        "is required when accepting a Hostess staging handoff"
                                    )
                                if staging_acceptance_manifest is None:
                                    raise ValueError(
                                        "--hostess-staging-acceptance-manifest-in or request "
                                        "acceptance_manifest_path is required when accepting a "
                                        "Hostess staging handoff"
                                    )
                                if args.hostess_staging_handoff_acceptance_receipt_out:
                                    if staging_handoff_acceptance_receipt is None:
                                        staging_handoff_acceptance_receipt = (
                                            build_hostess_staging_handoff_acceptance_receipt(
                                                operator_release_readiness_bundle,
                                                staging_handoff,
                                                staging_acceptance_manifest,
                                            )
                                        )
                                    write_json(
                                        args.hostess_staging_handoff_acceptance_receipt_out,
                                        staging_handoff_acceptance_receipt,
                                    )
                                if (
                                    args.hostess_staging_handoff_acceptance_receipt_rejection_out
                                ):
                                    write_json(
                                        args.hostess_staging_handoff_acceptance_receipt_rejection_out,
                                        build_hostess_staging_handoff_acceptance_receipt(
                                            operator_release_readiness_bundle,
                                            staging_handoff,
                                            staging_acceptance_manifest,
                                            decision=REJECTED_STATUS,
                                            reason_code=(
                                                "hostess.issue.operator_rejected_hostess_staging_handoff_acceptance"
                                            ),
                                        ),
                                    )
                                if (
                                    args.hostess_staging_file_plan_receipt_out
                                    or args.hostess_staging_file_plan_receipt_rejection_out
                                    or args.hostess_staging_file_copy_receipt_out
                                    or args.hostess_staging_file_copy_receipt_rejection_out
                                    or args.hostess_staged_payload_manifest_receipt_out
                                    or args.hostess_staged_payload_manifest_receipt_rejection_out
                                ):
                                    if staging_file_plan is None:
                                        raise ValueError(
                                            "--hostess-staging-file-plan-in or request file_plan_path "
                                            "is required when building a Hostess staging file plan receipt"
                                        )
                                    if staging_handoff_acceptance_receipt is None:
                                        staging_handoff_acceptance_receipt = (
                                            build_hostess_staging_handoff_acceptance_receipt(
                                                operator_release_readiness_bundle,
                                                staging_handoff,
                                                staging_acceptance_manifest,
                                            )
                                        )
                                    if args.hostess_staging_file_plan_receipt_out:
                                        if staging_file_plan_receipt is None:
                                            staging_file_plan_receipt = (
                                                build_hostess_staging_file_plan_receipt(
                                                    staging_handoff_acceptance_receipt,
                                                    staging_file_plan,
                                                    staging_root=args.hostess_staging_root,
                                                    source_file_plan_path=staging_file_plan_path,
                                                )
                                            )
                                        write_json(
                                            args.hostess_staging_file_plan_receipt_out,
                                            staging_file_plan_receipt,
                                        )
                                    if args.hostess_staging_file_plan_receipt_rejection_out:
                                        write_json(
                                            args.hostess_staging_file_plan_receipt_rejection_out,
                                            build_hostess_staging_file_plan_receipt(
                                                staging_handoff_acceptance_receipt,
                                                staging_file_plan,
                                                staging_root=args.hostess_staging_root,
                                                source_file_plan_path=staging_file_plan_path,
                                                decision=REJECTED_STATUS,
                                                reason_code=(
                                                    "hostess.issue.operator_rejected_hostess_staging_file_plan"
                                                ),
                                            ),
                                        )
                                    if (
                                        args.hostess_staging_file_copy_receipt_out
                                        or args.hostess_staging_file_copy_receipt_rejection_out
                                        or args.hostess_staged_payload_manifest_receipt_out
                                        or args.hostess_staged_payload_manifest_receipt_rejection_out
                                    ):
                                        if staging_file_plan_receipt is None:
                                            staging_file_plan_receipt = (
                                                build_hostess_staging_file_plan_receipt(
                                                    staging_handoff_acceptance_receipt,
                                                    staging_file_plan,
                                                    staging_root=args.hostess_staging_root,
                                                    source_file_plan_path=staging_file_plan_path,
                                                )
                                            )
                                        if args.hostess_staging_file_copy_receipt_out:
                                            if staging_file_copy_receipt is None:
                                                staging_file_copy_receipt = (
                                                    build_hostess_staging_file_copy_receipt(
                                                        staging_file_plan_receipt,
                                                        staging_file_plan,
                                                    )
                                                )
                                            write_json(
                                                args.hostess_staging_file_copy_receipt_out,
                                                staging_file_copy_receipt,
                                            )
                                        if args.hostess_staging_file_copy_receipt_rejection_out:
                                            write_json(
                                                args.hostess_staging_file_copy_receipt_rejection_out,
                                                build_hostess_staging_file_copy_receipt(
                                                    staging_file_plan_receipt,
                                                    staging_file_plan,
                                                    decision=REJECTED_STATUS,
                                                    reason_code=(
                                                        "hostess.issue.operator_rejected_hostess_staging_file_copy"
                                                    ),
                                                ),
                                            )
                                        if (
                                            args.hostess_staged_payload_manifest_receipt_out
                                            or args.hostess_staged_payload_manifest_receipt_rejection_out
                                        ):
                                            if staging_file_copy_receipt is None:
                                                staging_file_copy_receipt = (
                                                    build_hostess_staging_file_copy_receipt(
                                                        staging_file_plan_receipt,
                                                        staging_file_plan,
                                                    )
                                                )
                                            if args.hostess_staged_payload_manifest_receipt_out:
                                                if staged_payload_manifest_receipt is None:
                                                    staged_payload_manifest_receipt = (
                                                        build_hostess_staged_payload_manifest_receipt(
                                                            staging_file_copy_receipt,
                                                        )
                                                    )
                                                write_json(
                                                    args.hostess_staged_payload_manifest_receipt_out,
                                                    staged_payload_manifest_receipt,
                                                )
                                            if args.hostess_staged_payload_manifest_receipt_rejection_out:
                                                write_json(
                                                    args.hostess_staged_payload_manifest_receipt_rejection_out,
                                                    build_hostess_staged_payload_manifest_receipt(
                                                        staging_file_copy_receipt,
                                                        decision=REJECTED_STATUS,
                                                        reason_code=(
                                                            "hostess.issue.operator_rejected_hostess_staged_payload_manifest"
                                                        ),
                                                    ),
                                                )
    if (
        args.hostess_staging_handoff_acceptance_receipt_out
        or args.hostess_staging_handoff_acceptance_receipt_rejection_out
        or args.hostess_staging_file_plan_receipt_out
        or args.hostess_staging_file_plan_receipt_rejection_out
        or args.hostess_staging_file_copy_receipt_out
        or args.hostess_staging_file_copy_receipt_rejection_out
        or args.hostess_staged_payload_manifest_receipt_out
        or args.hostess_staged_payload_manifest_receipt_rejection_out
    ):
        if operator_release_readiness_bundle is None:
            if (
                staging_handoff_acceptance_receipt is None
                and staging_file_plan_receipt is None
                and staging_file_copy_receipt is None
            ):
                raise ValueError(
                    "--operator-release-readiness-bundle-in, "
                    "--operator-release-readiness-bundle-out, or "
                    "--hostess-staging-handoff-acceptance-receipt-in is required "
                    "when building Hostess staging receipts"
                )
        if staging_handoff is None:
            if (
                staging_handoff_acceptance_receipt is None
                and staging_file_plan_receipt is None
                and staging_file_copy_receipt is None
            ):
                raise ValueError(
                    "--hostess-staging-handoff-in or request handoff_path is required "
                    "when accepting a Hostess staging handoff"
                )
        if staging_acceptance_manifest is None:
            if (
                staging_handoff_acceptance_receipt is None
                and staging_file_plan_receipt is None
                and staging_file_copy_receipt is None
            ):
                raise ValueError(
                    "--hostess-staging-acceptance-manifest-in or request "
                    "acceptance_manifest_path is required when accepting a Hostess "
                    "staging handoff"
                )
        if args.hostess_staging_handoff_acceptance_receipt_out:
            if staging_handoff_acceptance_receipt is None:
                staging_handoff_acceptance_receipt = (
                    build_hostess_staging_handoff_acceptance_receipt(
                        operator_release_readiness_bundle,
                        staging_handoff,
                        staging_acceptance_manifest,
                    )
                )
            write_json(
                args.hostess_staging_handoff_acceptance_receipt_out,
                staging_handoff_acceptance_receipt,
            )
        if args.hostess_staging_handoff_acceptance_receipt_rejection_out:
            write_json(
                args.hostess_staging_handoff_acceptance_receipt_rejection_out,
                build_hostess_staging_handoff_acceptance_receipt(
                    operator_release_readiness_bundle,
                    staging_handoff,
                    staging_acceptance_manifest,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_staging_handoff_acceptance"
                    ),
                ),
            )
        if (
            args.hostess_staging_file_plan_receipt_out
            or args.hostess_staging_file_plan_receipt_rejection_out
            or args.hostess_staging_file_copy_receipt_out
            or args.hostess_staging_file_copy_receipt_rejection_out
        ):
            if staging_file_plan is None:
                raise ValueError(
                    "--hostess-staging-file-plan-in or request file_plan_path is required "
                    "when building a Hostess staging file plan receipt"
                )
            if (
                staging_handoff_acceptance_receipt is None
                and staging_file_plan_receipt is None
            ):
                if operator_release_readiness_bundle is None:
                    raise ValueError(
                        "--hostess-staging-handoff-acceptance-receipt-in or "
                        "operator release and handoff inputs are required when "
                        "building a Hostess staging file plan receipt"
                    )
                staging_handoff_acceptance_receipt = (
                    build_hostess_staging_handoff_acceptance_receipt(
                        operator_release_readiness_bundle,
                        staging_handoff,
                        staging_acceptance_manifest,
                    )
                )
            if args.hostess_staging_file_plan_receipt_out:
                if staging_file_plan_receipt is None:
                    staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                    )
                write_json(
                    args.hostess_staging_file_plan_receipt_out,
                    staging_file_plan_receipt,
                )
            if args.hostess_staging_file_plan_receipt_rejection_out:
                write_json(
                    args.hostess_staging_file_plan_receipt_rejection_out,
                    build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                        decision=REJECTED_STATUS,
                        reason_code=(
                            "hostess.issue.operator_rejected_hostess_staging_file_plan"
                        ),
                    ),
                )
            if (
                args.hostess_staging_file_copy_receipt_out
                or args.hostess_staging_file_copy_receipt_rejection_out
            ):
                if staging_file_plan_receipt is None:
                    staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                    )
                if args.hostess_staging_file_copy_receipt_out:
                    if staging_file_copy_receipt is None:
                        staging_file_copy_receipt = (
                            build_hostess_staging_file_copy_receipt(
                                staging_file_plan_receipt,
                                staging_file_plan,
                            )
                        )
                    write_json(
                        args.hostess_staging_file_copy_receipt_out,
                        staging_file_copy_receipt,
                    )
                if args.hostess_staging_file_copy_receipt_rejection_out:
                    write_json(
                        args.hostess_staging_file_copy_receipt_rejection_out,
                        build_hostess_staging_file_copy_receipt(
                            staging_file_plan_receipt,
                            staging_file_plan,
                            decision=REJECTED_STATUS,
                            reason_code=(
                                "hostess.issue.operator_rejected_hostess_staging_file_copy"
                            ),
                        ),
                    )
                if (
                    args.hostess_staged_payload_manifest_receipt_out
                    or args.hostess_staged_payload_manifest_receipt_rejection_out
                ):
                    if staging_file_copy_receipt is None:
                        staging_file_copy_receipt = (
                            build_hostess_staging_file_copy_receipt(
                                staging_file_plan_receipt,
                                staging_file_plan,
                            )
                        )
                    if args.hostess_staged_payload_manifest_receipt_out:
                        if staged_payload_manifest_receipt is None:
                            staged_payload_manifest_receipt = (
                                build_hostess_staged_payload_manifest_receipt(
                                    staging_file_copy_receipt,
                                )
                            )
                        write_json(
                            args.hostess_staged_payload_manifest_receipt_out,
                            staged_payload_manifest_receipt,
                        )
                    if args.hostess_staged_payload_manifest_receipt_rejection_out:
                        write_json(
                            args.hostess_staged_payload_manifest_receipt_rejection_out,
                            build_hostess_staged_payload_manifest_receipt(
                                staging_file_copy_receipt,
                                decision=REJECTED_STATUS,
                                reason_code=(
                                    "hostess.issue.operator_rejected_hostess_staged_payload_manifest"
                            ),
                        ),
                    )
        if (
            args.hostess_staged_payload_manifest_receipt_out
            or args.hostess_staged_payload_manifest_receipt_rejection_out
        ):
            if staging_file_copy_receipt is None:
                if staging_file_plan is None:
                    raise ValueError(
                        "--hostess-staging-file-copy-receipt-in or "
                        "--hostess-staging-file-plan-in is required when building "
                        "a Hostess staged payload manifest receipt"
                    )
                if staging_file_plan_receipt is None:
                    staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                    )
                staging_file_copy_receipt = build_hostess_staging_file_copy_receipt(
                    staging_file_plan_receipt,
                    staging_file_plan,
                )
            if args.hostess_staged_payload_manifest_receipt_out:
                if staged_payload_manifest_receipt is None:
                    staged_payload_manifest_receipt = (
                        build_hostess_staged_payload_manifest_receipt(
                            staging_file_copy_receipt,
                        )
                    )
                write_json(
                    args.hostess_staged_payload_manifest_receipt_out,
                    staged_payload_manifest_receipt,
                )
            if args.hostess_staged_payload_manifest_receipt_rejection_out:
                write_json(
                    args.hostess_staged_payload_manifest_receipt_rejection_out,
                    build_hostess_staged_payload_manifest_receipt(
                        staging_file_copy_receipt,
                        decision=REJECTED_STATUS,
                        reason_code=(
                            "hostess.issue.operator_rejected_hostess_staged_payload_manifest"
                        ),
                    ),
                )
    if (
        args.hostess_downstream_shell_selection_receipt_out
        or args.hostess_downstream_shell_selection_receipt_rejection_out
    ):
        if staged_payload_manifest_receipt is None:
            if staging_file_copy_receipt is None:
                if staging_file_plan is None:
                    raise ValueError(
                        "--hostess-staged-payload-manifest-receipt-in, "
                        "--hostess-staging-file-copy-receipt-in, or "
                        "--hostess-staging-file-plan-in is required when building "
                        "a Hostess downstream shell selection receipt"
                    )
                if staging_file_plan_receipt is None:
                    if staging_handoff_acceptance_receipt is None:
                        raise ValueError(
                            "--hostess-staged-payload-manifest-receipt-in, "
                            "--hostess-staging-file-copy-receipt-in, "
                            "--hostess-staging-file-plan-receipt-in, or "
                            "handoff acceptance inputs are required when building "
                            "a Hostess downstream shell selection receipt"
                        )
                    staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                    )
                staging_file_copy_receipt = build_hostess_staging_file_copy_receipt(
                    staging_file_plan_receipt,
                    staging_file_plan,
                )
            staged_payload_manifest_receipt = (
                build_hostess_staged_payload_manifest_receipt(
                    staging_file_copy_receipt,
                )
            )
        if args.hostess_downstream_shell_selection_receipt_out:
            if downstream_shell_selection_receipt is None:
                downstream_shell_selection_receipt = (
                    build_hostess_downstream_shell_selection_receipt(
                        staged_payload_manifest_receipt,
                        target_kind=args.hostess_downstream_shell_selection_target_kind,
                        graph_id=args.hostess_downstream_shell_selection_graph_id,
                        consumer_id=args.hostess_downstream_shell_selection_consumer_id,
                    )
                )
            write_json(
                args.hostess_downstream_shell_selection_receipt_out,
                downstream_shell_selection_receipt,
            )
        if args.hostess_downstream_shell_selection_receipt_rejection_out:
            write_json(
                args.hostess_downstream_shell_selection_receipt_rejection_out,
                build_hostess_downstream_shell_selection_receipt(
                    staged_payload_manifest_receipt,
                    target_kind=args.hostess_downstream_shell_selection_target_kind,
                    graph_id=args.hostess_downstream_shell_selection_graph_id,
                    consumer_id=args.hostess_downstream_shell_selection_consumer_id,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_downstream_shell_selection"
                    ),
                ),
            )
    if (
        args.hostess_manifold_shell_handoff_review_intake_receipt_out
        or args.hostess_manifold_shell_handoff_review_intake_receipt_rejection_out
    ):
        if downstream_shell_selection_receipt is None:
            if staged_payload_manifest_receipt is None:
                if staging_file_copy_receipt is None:
                    raise ValueError(
                        "--hostess-downstream-shell-selection-receipt-in, "
                        "--hostess-staged-payload-manifest-receipt-in, or "
                        "--hostess-staging-file-copy-receipt-in is required when "
                        "building a Hostess Manifold shell handoff review intake receipt"
                    )
                staged_payload_manifest_receipt = (
                    build_hostess_staged_payload_manifest_receipt(
                        staging_file_copy_receipt,
                    )
                )
            downstream_shell_selection_receipt = (
                build_hostess_downstream_shell_selection_receipt(
                    staged_payload_manifest_receipt,
                    target_kind=args.hostess_downstream_shell_selection_target_kind,
                    graph_id=args.hostess_downstream_shell_selection_graph_id,
                    consumer_id=args.hostess_downstream_shell_selection_consumer_id,
                )
            )
        selected_handoff = selected_manifold_shell_handoff_from_selection(
            downstream_shell_selection_receipt
        )
        if args.hostess_manifold_shell_handoff_review_intake_receipt_out:
            if manifold_shell_handoff_review_receipt is None:
                raise ValueError(
                    "--manifold-shell-handoff-review-receipt-in is required when "
                    "building a Hostess Manifold shell handoff review intake receipt"
                )
            manifold_shell_handoff_review_intake_receipt = (
                build_hostess_manifold_shell_handoff_review_intake_receipt(
                    downstream_shell_selection_receipt,
                    selected_handoff,
                    manifold_shell_handoff_review_receipt,
                    args.manifold_shell_handoff_review_receipt_in,
                )
            )
            write_json(
                args.hostess_manifold_shell_handoff_review_intake_receipt_out,
                manifold_shell_handoff_review_intake_receipt,
            )
        if args.hostess_manifold_shell_handoff_review_intake_receipt_rejection_out:
            write_json(
                args.hostess_manifold_shell_handoff_review_intake_receipt_rejection_out,
                build_hostess_manifold_shell_handoff_review_intake_receipt(
                    downstream_shell_selection_receipt,
                    selected_handoff,
                    manifold_shell_handoff_review_receipt or {},
                    args.manifold_shell_handoff_review_receipt_in,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_manifold_shell_handoff_review_intake"
                    ),
                ),
            )
    if (
        args.hostess_makepad_shell_contract_receipt_out
        or args.hostess_makepad_shell_contract_receipt_rejection_out
    ):
        if manifold_shell_handoff_review_intake_receipt is None:
            raise ValueError(
                "--hostess-manifold-shell-handoff-review-intake-receipt-in or "
                "--hostess-manifold-shell-handoff-review-intake-receipt-out is "
                "required when building a Hostess Makepad shell contract receipt"
            )
        if args.hostess_makepad_shell_contract_receipt_out:
            makepad_shell_contract_receipt = (
                build_hostess_makepad_shell_contract_receipt(
                    manifold_shell_handoff_review_intake_receipt,
                    args.hostess_manifold_shell_handoff_review_intake_receipt_in
                    or args.hostess_manifold_shell_handoff_review_intake_receipt_out,
                )
            )
            write_json(
                args.hostess_makepad_shell_contract_receipt_out,
                makepad_shell_contract_receipt,
            )
        if args.hostess_makepad_shell_contract_receipt_rejection_out:
            write_json(
                args.hostess_makepad_shell_contract_receipt_rejection_out,
                build_hostess_makepad_shell_contract_receipt(
                    manifold_shell_handoff_review_intake_receipt,
                    args.hostess_manifold_shell_handoff_review_intake_receipt_in
                    or args.hostess_manifold_shell_handoff_review_intake_receipt_out,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_makepad_shell_contract"
                    ),
                ),
            )
    if (
        args.hostess_makepad_shell_launch_handoff_receipt_out
        or args.hostess_makepad_shell_launch_handoff_receipt_rejection_out
    ):
        if makepad_shell_contract_receipt is None:
            raise ValueError(
                "--hostess-makepad-shell-contract-receipt-in or "
                "--hostess-makepad-shell-contract-receipt-out is required when "
                "building a Hostess Makepad shell launch handoff receipt"
            )
        makepad_shell_contract_receipt_path = (
            args.hostess_makepad_shell_contract_receipt_in
            or args.hostess_makepad_shell_contract_receipt_out
        )
        if args.hostess_makepad_shell_launch_handoff_receipt_out:
            makepad_shell_launch_handoff_receipt = (
                build_hostess_makepad_shell_launch_handoff_receipt(
                    makepad_shell_contract_receipt,
                    makepad_shell_contract_receipt_path,
                )
            )
            write_json(
                args.hostess_makepad_shell_launch_handoff_receipt_out,
                makepad_shell_launch_handoff_receipt,
            )
        if args.hostess_makepad_shell_launch_handoff_receipt_rejection_out:
            write_json(
                args.hostess_makepad_shell_launch_handoff_receipt_rejection_out,
                build_hostess_makepad_shell_launch_handoff_receipt(
                    makepad_shell_contract_receipt,
                    makepad_shell_contract_receipt_path,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_makepad_shell_launch_handoff"
                    ),
                ),
            )
    if (
        args.validate_platform_smoke_approval
        or args.validate_platform_smoke_execution_request
        or args.validate_platform_smoke_execution_receipt
        or args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_plan is None:
        if args.validate_platform_smoke_plan:
            platform_smoke_plan = load_json(args.validate_platform_smoke_plan)
        else:
            if dry_run_request is None:
                if smoke_handoff is None:
                    smoke_handoff = build_smoke_handoff_checklist(
                        request,
                        report,
                        ack_fixture,
                        target_profile=args.target_profile,
                    )
                dry_run_request = build_smoke_dry_run_request(
                    smoke_handoff,
                    target_profile=args.target_profile,
                )
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            platform_smoke_plan = build_platform_smoke_plan(
                smoke_review_bundle,
                target_platform=args.target_platform,
            )
    if (
        args.validate_platform_smoke_execution_request
        or args.validate_platform_smoke_execution_receipt
        or args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_approval is None:
        if args.validate_platform_smoke_approval:
            platform_smoke_approval = load_json(args.validate_platform_smoke_approval)
        else:
            platform_smoke_approval = build_platform_smoke_approval_receipt(
                platform_smoke_plan,
                decision=APPROVED_STATUS,
            )
    if (
        args.validate_platform_smoke_execution_receipt
        or args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_execution_request is None:
        if args.validate_platform_smoke_execution_request:
            platform_smoke_execution_request = load_json(args.validate_platform_smoke_execution_request)
        else:
            platform_smoke_execution_request = build_platform_smoke_execution_request(
                platform_smoke_plan,
                platform_smoke_approval,
            )
    if (
        args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_execution_receipt is None:
        if args.validate_platform_smoke_execution_receipt:
            platform_smoke_execution_receipt = load_json(args.validate_platform_smoke_execution_receipt)
        else:
            platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
            )
    if (
        args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_operator_start_gate is None:
        if args.validate_platform_smoke_operator_start_gate:
            platform_smoke_operator_start_gate = load_json(args.validate_platform_smoke_operator_start_gate)
        else:
            platform_smoke_operator_start_gate = build_platform_smoke_operator_start_gate(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
                platform_smoke_execution_receipt,
                host_shell_kind=args.host_shell_kind,
            )
    if (
        args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_operator_start_preflight is None:
        if args.validate_platform_smoke_operator_start_preflight:
            platform_smoke_operator_start_preflight = load_json(
                args.validate_platform_smoke_operator_start_preflight
            )
        else:
            platform_smoke_operator_start_preflight = (
                build_platform_smoke_operator_start_preflight_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    platform_smoke_operator_start_gate,
                    decision=APPROVED_STATUS,
                    pmb_shell_handoff_review=pmb_shell_handoff_review,
                    pmb_shell_handoff_review_path=pmb_shell_handoff_review_path,
                    require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
                )
            )
    if (
        args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_execution_report is None:
        if args.validate_platform_smoke_execution_report:
            platform_smoke_execution_report = load_json(args.validate_platform_smoke_execution_report)
        else:
            platform_smoke_execution_report = build_platform_smoke_execution_report(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
                platform_smoke_execution_receipt,
                platform_smoke_operator_start_gate,
                platform_smoke_operator_start_preflight,
            )
    if (
        args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_evidence_attachment is None:
        if args.validate_platform_smoke_evidence_attachment:
            platform_smoke_evidence_attachment = load_json(
                args.validate_platform_smoke_evidence_attachment
            )
        else:
            platform_smoke_evidence_attachment = (
                build_platform_smoke_evidence_attachment_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    platform_smoke_operator_start_gate,
                    platform_smoke_operator_start_preflight,
                    platform_smoke_execution_report,
                )
            )
    if args.validate_operator_release_readiness_bundle and platform_smoke_evidence_review is None:
        if args.validate_platform_smoke_evidence_review:
            platform_smoke_evidence_review = load_json(
                args.validate_platform_smoke_evidence_review
            )
        else:
            platform_smoke_evidence_review = build_platform_smoke_evidence_review(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
                platform_smoke_execution_receipt,
                platform_smoke_operator_start_gate,
                platform_smoke_operator_start_preflight,
                platform_smoke_execution_report,
                platform_smoke_evidence_attachment,
            )
    if args.validate_operator_release_readiness_bundle and pmb_replay_validation_receipt is None:
        if args.validate_pmb_replay_validation_receipt:
            pmb_replay_validation_receipt = load_json(
                args.validate_pmb_replay_validation_receipt
            )
        else:
            if pmb_validation_handoff is None:
                if pmb_authoring_review is None:
                    raise ValueError(
                        "--pmb-replay-validation-receipt-in or --pmb-authoring-review-in "
                        "is required when validating an operator release readiness bundle"
                    )
                pmb_validation_handoff = build_projected_motion_breath_validation_handoff(
                    pmb_authoring_review,
                    pmb_package_evidence_intake,
                    args.pmb_authoring_review_in,
                    args.pmb_package_evidence_intake_in,
                    pmb_source_adapter_selection,
                    args.pmb_source_adapter_selection_in,
                )
            pmb_replay_validation_receipt = (
                build_projected_motion_breath_replay_validation_receipt(
                    pmb_validation_handoff,
                    pmb_replay_descriptors,
                    args.pmb_replay_descriptors_in,
                )
            )
    if args.validate_ack:
        ack_report = validate_ack_fixture(request, load_json(args.validate_ack))
        write_json(args.validate_ack.with_suffix(args.validate_ack.suffix + ".validation.json"), ack_report)
    if args.validate_reject:
        reject_report = validate_reject_fixture(request, load_json(args.validate_reject))
        write_json(
            args.validate_reject.with_suffix(args.validate_reject.suffix + ".validation.json"),
            reject_report,
        )
    if args.validate_smoke_handoff:
        smoke_report = validate_smoke_handoff_checklist(load_json(args.validate_smoke_handoff))
        write_json(
            args.validate_smoke_handoff.with_suffix(args.validate_smoke_handoff.suffix + ".validation.json"),
            smoke_report,
        )
    if args.validate_smoke_dry_run_request:
        request_report = validate_smoke_dry_run_request(load_json(args.validate_smoke_dry_run_request))
        write_json(
            args.validate_smoke_dry_run_request.with_suffix(
                args.validate_smoke_dry_run_request.suffix + ".validation.json"
            ),
            request_report,
        )
    if args.validate_smoke_dry_run_receipt:
        if dry_run_request is None:
            if args.validate_smoke_dry_run_request:
                dry_run_request = load_json(args.validate_smoke_dry_run_request)
            else:
                if smoke_handoff is None:
                    smoke_handoff = build_smoke_handoff_checklist(
                        request,
                        report,
                        ack_fixture,
                        target_profile=args.target_profile,
                    )
                dry_run_request = build_smoke_dry_run_request(
                    smoke_handoff,
                    target_profile=args.target_profile,
                )
        receipt_report = validate_smoke_dry_run_receipt(
            dry_run_request,
            load_json(args.validate_smoke_dry_run_receipt),
        )
        write_json(
            args.validate_smoke_dry_run_receipt.with_suffix(
                args.validate_smoke_dry_run_receipt.suffix + ".validation.json"
            ),
            receipt_report,
        )
    if args.validate_smoke_preflight:
        preflight_report = validate_smoke_execution_preflight(load_json(args.validate_smoke_preflight))
        write_json(
            args.validate_smoke_preflight.with_suffix(
                args.validate_smoke_preflight.suffix + ".validation.json"
            ),
            preflight_report,
        )
    if args.validate_smoke_host_shell_execution:
        execution_report = validate_smoke_host_shell_execution(load_json(args.validate_smoke_host_shell_execution))
        write_json(
            args.validate_smoke_host_shell_execution.with_suffix(
                args.validate_smoke_host_shell_execution.suffix + ".validation.json"
            ),
            execution_report,
        )
    if args.validate_smoke_review_bundle:
        bundle_report = validate_smoke_review_bundle(load_json(args.validate_smoke_review_bundle))
        write_json(
            args.validate_smoke_review_bundle.with_suffix(
                args.validate_smoke_review_bundle.suffix + ".validation.json"
            ),
            bundle_report,
        )
    if args.validate_platform_smoke_plan:
        plan_report = validate_platform_smoke_plan(load_json(args.validate_platform_smoke_plan))
        write_json(
            args.validate_platform_smoke_plan.with_suffix(
                args.validate_platform_smoke_plan.suffix + ".validation.json"
            ),
            plan_report,
        )
    if args.validate_platform_smoke_approval:
        approval_report = validate_platform_smoke_approval_receipt(
            platform_smoke_plan,
            load_json(args.validate_platform_smoke_approval),
        )
        write_json(
            args.validate_platform_smoke_approval.with_suffix(
                args.validate_platform_smoke_approval.suffix + ".validation.json"
            ),
            approval_report,
        )
    if args.validate_platform_smoke_execution_request:
        execution_request_report = validate_platform_smoke_execution_request(
            platform_smoke_plan,
            platform_smoke_approval,
            load_json(args.validate_platform_smoke_execution_request),
        )
        write_json(
            args.validate_platform_smoke_execution_request.with_suffix(
                args.validate_platform_smoke_execution_request.suffix + ".validation.json"
            ),
            execution_request_report,
        )
    if args.validate_platform_smoke_execution_receipt:
        execution_receipt_report = validate_platform_smoke_execution_receipt(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            load_json(args.validate_platform_smoke_execution_receipt),
        )
        write_json(
            args.validate_platform_smoke_execution_receipt.with_suffix(
                args.validate_platform_smoke_execution_receipt.suffix + ".validation.json"
            ),
            execution_receipt_report,
        )
    if args.validate_platform_smoke_operator_start_gate:
        operator_start_report = validate_platform_smoke_operator_start_gate(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            load_json(args.validate_platform_smoke_operator_start_gate),
        )
        write_json(
            args.validate_platform_smoke_operator_start_gate.with_suffix(
                args.validate_platform_smoke_operator_start_gate.suffix + ".validation.json"
            ),
            operator_start_report,
        )
    if args.validate_platform_smoke_operator_start_preflight:
        operator_start_preflight_report = validate_platform_smoke_operator_start_preflight_receipt(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            platform_smoke_operator_start_gate,
            load_json(args.validate_platform_smoke_operator_start_preflight),
            require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
        )
        write_json(
            args.validate_platform_smoke_operator_start_preflight.with_suffix(
                args.validate_platform_smoke_operator_start_preflight.suffix + ".validation.json"
            ),
            operator_start_preflight_report,
        )
    if args.validate_platform_smoke_execution_report:
        execution_report_report = validate_platform_smoke_execution_report(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            platform_smoke_operator_start_gate,
            platform_smoke_operator_start_preflight,
            load_json(args.validate_platform_smoke_execution_report),
        )
        write_json(
            args.validate_platform_smoke_execution_report.with_suffix(
                args.validate_platform_smoke_execution_report.suffix + ".validation.json"
            ),
            execution_report_report,
        )
    if args.validate_platform_smoke_evidence_attachment:
        evidence_attachment_report = validate_platform_smoke_evidence_attachment_receipt(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            platform_smoke_operator_start_gate,
            platform_smoke_operator_start_preflight,
            platform_smoke_execution_report,
            load_json(args.validate_platform_smoke_evidence_attachment),
        )
        write_json(
            args.validate_platform_smoke_evidence_attachment.with_suffix(
                args.validate_platform_smoke_evidence_attachment.suffix + ".validation.json"
            ),
            evidence_attachment_report,
        )
    if args.validate_platform_smoke_evidence_review:
        evidence_review_report = validate_platform_smoke_evidence_review(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            platform_smoke_operator_start_gate,
            platform_smoke_operator_start_preflight,
            platform_smoke_execution_report,
            platform_smoke_evidence_attachment,
            load_json(args.validate_platform_smoke_evidence_review),
        )
        write_json(
            args.validate_platform_smoke_evidence_review.with_suffix(
                args.validate_platform_smoke_evidence_review.suffix + ".validation.json"
            ),
            evidence_review_report,
        )
    if args.validate_pmb_validation_handoff:
        pmb_validation_report = validate_projected_motion_breath_validation_handoff(
            load_json(args.validate_pmb_validation_handoff)
        )
        write_json(
            args.validate_pmb_validation_handoff.with_suffix(
                args.validate_pmb_validation_handoff.suffix + ".validation.json"
            ),
            pmb_validation_report,
        )
    if args.validate_pmb_replay_validation_receipt:
        pmb_replay_validation_report = (
            validate_projected_motion_breath_replay_validation_receipt(
                load_json(args.validate_pmb_replay_validation_receipt)
            )
        )
        write_json(
            args.validate_pmb_replay_validation_receipt.with_suffix(
                args.validate_pmb_replay_validation_receipt.suffix + ".validation.json"
            ),
            pmb_replay_validation_report,
        )
    if args.validate_operator_release_readiness_bundle:
        operator_release_report = validate_operator_release_readiness_bundle(
            platform_smoke_evidence_review,
            pmb_replay_validation_receipt,
            load_json(args.validate_operator_release_readiness_bundle),
        )
        write_json(
            args.validate_operator_release_readiness_bundle.with_suffix(
                args.validate_operator_release_readiness_bundle.suffix
                + ".validation.json"
            ),
            operator_release_report,
        )
    if args.validate_hostess_staging_handoff_acceptance_receipt:
        if operator_release_readiness_bundle is None:
            if args.validate_operator_release_readiness_bundle:
                operator_release_readiness_bundle = load_json(
                    args.validate_operator_release_readiness_bundle
                )
            else:
                operator_release_readiness_bundle = build_operator_release_readiness_bundle(
                    platform_smoke_evidence_review,
                    pmb_replay_validation_receipt,
                )
        if staging_handoff is None:
            raise ValueError(
                "--hostess-staging-handoff-in or request handoff_path is required "
                "when validating a Hostess staging handoff acceptance receipt"
            )
        if staging_acceptance_manifest is None:
            raise ValueError(
                "--hostess-staging-acceptance-manifest-in or request "
                "acceptance_manifest_path is required when validating a Hostess "
                "staging handoff acceptance receipt"
            )
        handoff_acceptance_report = validate_hostess_staging_handoff_acceptance_receipt(
            operator_release_readiness_bundle,
            staging_handoff,
            staging_acceptance_manifest,
            load_json(args.validate_hostess_staging_handoff_acceptance_receipt),
        )
        write_json(
            args.validate_hostess_staging_handoff_acceptance_receipt.with_suffix(
                args.validate_hostess_staging_handoff_acceptance_receipt.suffix
                + ".validation.json"
            ),
            handoff_acceptance_report,
        )
    if args.validate_hostess_staging_file_plan_receipt:
        if staging_handoff_acceptance_receipt is None:
            if args.validate_hostess_staging_handoff_acceptance_receipt:
                staging_handoff_acceptance_receipt = load_json(
                    args.validate_hostess_staging_handoff_acceptance_receipt
                )
            else:
                if operator_release_readiness_bundle is None:
                    raise ValueError(
                        "--hostess-staging-handoff-acceptance-receipt-in or "
                        "operator release inputs are required when validating a "
                        "Hostess staging file plan receipt"
                    )
                if staging_handoff is None:
                    raise ValueError(
                        "--hostess-staging-handoff-in or request handoff_path is required "
                        "when validating a Hostess staging file plan receipt"
                    )
                if staging_acceptance_manifest is None:
                    raise ValueError(
                        "--hostess-staging-acceptance-manifest-in or request "
                        "acceptance_manifest_path is required when validating a "
                        "Hostess staging file plan receipt"
                    )
                staging_handoff_acceptance_receipt = (
                    build_hostess_staging_handoff_acceptance_receipt(
                        operator_release_readiness_bundle,
                        staging_handoff,
                        staging_acceptance_manifest,
                    )
                )
        if staging_file_plan is None:
            raise ValueError(
                "--hostess-staging-file-plan-in or request file_plan_path is required "
                "when validating a Hostess staging file plan receipt"
            )
        file_plan_report = validate_hostess_staging_file_plan_receipt(
            staging_handoff_acceptance_receipt,
            staging_file_plan,
            load_json(args.validate_hostess_staging_file_plan_receipt),
        )
        write_json(
            args.validate_hostess_staging_file_plan_receipt.with_suffix(
                args.validate_hostess_staging_file_plan_receipt.suffix
                + ".validation.json"
            ),
            file_plan_report,
        )
    if args.validate_hostess_staging_file_copy_receipt:
        if staging_file_plan_receipt is None:
            if args.validate_hostess_staging_file_plan_receipt:
                staging_file_plan_receipt = load_json(
                    args.validate_hostess_staging_file_plan_receipt
                )
            else:
                if staging_handoff_acceptance_receipt is None:
                    raise ValueError(
                        "--hostess-staging-file-plan-receipt-in, "
                        "--validate-hostess-staging-file-plan-receipt, or "
                        "handoff acceptance inputs are required when validating a "
                        "Hostess staging file copy receipt"
                    )
                if staging_file_plan is None:
                    raise ValueError(
                        "--hostess-staging-file-plan-in or request file_plan_path is required "
                        "when validating a Hostess staging file copy receipt"
                    )
                staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                    staging_handoff_acceptance_receipt,
                    staging_file_plan,
                    staging_root=args.hostess_staging_root,
                    source_file_plan_path=staging_file_plan_path,
                )
        if staging_file_plan is None:
            raise ValueError(
                "--hostess-staging-file-plan-in or request file_plan_path is required "
                "when validating a Hostess staging file copy receipt"
            )
        file_copy_report = validate_hostess_staging_file_copy_receipt(
            staging_file_plan_receipt,
            staging_file_plan,
            load_json(args.validate_hostess_staging_file_copy_receipt),
        )
        write_json(
            args.validate_hostess_staging_file_copy_receipt.with_suffix(
                args.validate_hostess_staging_file_copy_receipt.suffix
                + ".validation.json"
            ),
            file_copy_report,
        )
    if args.validate_hostess_staged_payload_manifest_receipt:
        if staging_file_copy_receipt is None:
            if args.validate_hostess_staging_file_copy_receipt:
                staging_file_copy_receipt = load_json(
                    args.validate_hostess_staging_file_copy_receipt
                )
            else:
                if staging_file_plan_receipt is None:
                    raise ValueError(
                        "--hostess-staging-file-copy-receipt-in, "
                        "--validate-hostess-staging-file-copy-receipt, or "
                        "file-plan receipt inputs are required when validating a "
                        "Hostess staged payload manifest receipt"
                    )
                if staging_file_plan is None:
                    raise ValueError(
                        "--hostess-staging-file-plan-in or request file_plan_path is required "
                        "when validating a Hostess staged payload manifest receipt"
                    )
                staging_file_copy_receipt = build_hostess_staging_file_copy_receipt(
                    staging_file_plan_receipt,
                    staging_file_plan,
                )
        staged_payload_report = validate_hostess_staged_payload_manifest_receipt(
            staging_file_copy_receipt,
            load_json(args.validate_hostess_staged_payload_manifest_receipt),
        )
        write_json(
            args.validate_hostess_staged_payload_manifest_receipt.with_suffix(
                args.validate_hostess_staged_payload_manifest_receipt.suffix
                + ".validation.json"
            ),
            staged_payload_report,
        )
    if args.validate_hostess_downstream_shell_selection_receipt:
        if staged_payload_manifest_receipt is None:
            if args.validate_hostess_staged_payload_manifest_receipt:
                staged_payload_manifest_receipt = load_json(
                    args.validate_hostess_staged_payload_manifest_receipt
                )
            elif staging_file_copy_receipt is not None:
                staged_payload_manifest_receipt = (
                    build_hostess_staged_payload_manifest_receipt(
                        staging_file_copy_receipt,
                    )
                )
            else:
                raise ValueError(
                    "--hostess-staged-payload-manifest-receipt-in, "
                    "--validate-hostess-staged-payload-manifest-receipt, or "
                    "--hostess-staging-file-copy-receipt-in is required when "
                    "validating a Hostess downstream shell selection receipt"
                )
        downstream_shell_selection_report = (
            validate_hostess_downstream_shell_selection_receipt(
                staged_payload_manifest_receipt,
                load_json(args.validate_hostess_downstream_shell_selection_receipt),
            )
        )
        write_json(
            args.validate_hostess_downstream_shell_selection_receipt.with_suffix(
                args.validate_hostess_downstream_shell_selection_receipt.suffix
                + ".validation.json"
            ),
            downstream_shell_selection_report,
        )
    if args.validate_hostess_manifold_shell_handoff_review_intake_receipt:
        intake_receipt = load_json(
            args.validate_hostess_manifold_shell_handoff_review_intake_receipt
        )
        manifold_shell_handoff_review_intake_receipt = intake_receipt
        if downstream_shell_selection_receipt is None:
            if args.validate_hostess_downstream_shell_selection_receipt:
                downstream_shell_selection_receipt = load_json(
                    args.validate_hostess_downstream_shell_selection_receipt
                )
            else:
                raise ValueError(
                    "--hostess-downstream-shell-selection-receipt-in or "
                    "--validate-hostess-downstream-shell-selection-receipt is "
                    "required when validating a Hostess Manifold shell handoff "
                    "review intake receipt"
                )
        selected_handoff = selected_manifold_shell_handoff_from_selection(
            downstream_shell_selection_receipt
        )
        if manifold_shell_handoff_review_receipt is None:
            review_path = intake_receipt.get(
                "source_manifold_shell_handoff_review_receipt_path"
            )
            if isinstance(review_path, str) and review_path:
                manifold_shell_handoff_review_receipt = load_json(Path(review_path))
            else:
                raise ValueError(
                    "--manifold-shell-handoff-review-receipt-in is required when "
                    "validating a Hostess Manifold shell handoff review intake receipt"
                )
        intake_report = validate_hostess_manifold_shell_handoff_review_intake_receipt(
            downstream_shell_selection_receipt,
            selected_handoff,
            manifold_shell_handoff_review_receipt,
            intake_receipt,
        )
        write_json(
            args.validate_hostess_manifold_shell_handoff_review_intake_receipt.with_suffix(
                args.validate_hostess_manifold_shell_handoff_review_intake_receipt.suffix
                + ".validation.json"
            ),
            intake_report,
        )
    if args.validate_hostess_makepad_shell_contract_receipt:
        makepad_shell_contract_receipt = load_json(
            args.validate_hostess_makepad_shell_contract_receipt
        )
        if manifold_shell_handoff_review_intake_receipt is None:
            if args.validate_hostess_manifold_shell_handoff_review_intake_receipt:
                manifold_shell_handoff_review_intake_receipt = load_json(
                    args.validate_hostess_manifold_shell_handoff_review_intake_receipt
                )
            else:
                intake_path = makepad_shell_contract_receipt.get(
                    "source_manifold_shell_handoff_review_intake_receipt_path"
                )
                if isinstance(intake_path, str) and intake_path:
                    manifold_shell_handoff_review_intake_receipt = load_json(
                        Path(intake_path)
                    )
                else:
                    raise ValueError(
                        "--hostess-manifold-shell-handoff-review-intake-receipt-in "
                        "or --validate-hostess-manifold-shell-handoff-review-intake-receipt "
                        "is required when validating a Hostess Makepad shell contract receipt"
                    )
        makepad_shell_contract_report = (
            validate_hostess_makepad_shell_contract_receipt(
                manifold_shell_handoff_review_intake_receipt,
                makepad_shell_contract_receipt,
            )
        )
        write_json(
            args.validate_hostess_makepad_shell_contract_receipt.with_suffix(
                args.validate_hostess_makepad_shell_contract_receipt.suffix
                + ".validation.json"
            ),
            makepad_shell_contract_report,
        )
    if args.validate_hostess_makepad_shell_launch_handoff_receipt:
        makepad_shell_launch_handoff_receipt = load_json(
            args.validate_hostess_makepad_shell_launch_handoff_receipt
        )
        if makepad_shell_contract_receipt is None:
            if args.validate_hostess_makepad_shell_contract_receipt:
                makepad_shell_contract_receipt = load_json(
                    args.validate_hostess_makepad_shell_contract_receipt
                )
            else:
                contract_receipt_path = makepad_shell_launch_handoff_receipt.get(
                    "source_makepad_shell_contract_receipt_path"
                )
                if isinstance(contract_receipt_path, str) and contract_receipt_path:
                    makepad_shell_contract_receipt = load_json(
                        Path(contract_receipt_path)
                    )
                else:
                    raise ValueError(
                        "--hostess-makepad-shell-contract-receipt-in or "
                        "--validate-hostess-makepad-shell-contract-receipt is "
                        "required when validating a Hostess Makepad shell launch "
                        "handoff receipt"
                    )
        makepad_shell_launch_handoff_report = (
            validate_hostess_makepad_shell_launch_handoff_receipt(
                makepad_shell_contract_receipt,
                makepad_shell_launch_handoff_receipt,
            )
        )
        write_json(
            args.validate_hostess_makepad_shell_launch_handoff_receipt.with_suffix(
                args.validate_hostess_makepad_shell_launch_handoff_receipt.suffix
                + ".validation.json"
            ),
            makepad_shell_launch_handoff_report,
        )
    return 0 if report["status"] == ACCEPTED_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
