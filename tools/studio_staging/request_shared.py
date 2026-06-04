"""Shared schemas, constants, and helpers for Studio staging request intake."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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

__all__ = [
    name
    for name in globals()
    if name.isupper()
    or name
    in {
        "load_json",
        "request_relative_path",
        "write_json",
        "check",
        "operator_release_readiness_bundle_unstarted",
    }
    or name.startswith("pmb_shell_handoff_")
]
