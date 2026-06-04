"""Fixture factories for Studio staging request tests."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools import studio_staging_request as adapter

def valid_request() -> dict[str, object]:
    actions = [
        action(
            "adapter.hostess.accept_staging_handoff",
            "rusty.hostess",
            "hostess_acceptance_gate",
            "hostess.accept.staging_handoff",
            "hostess.accept_staging_handoff",
            "handoff.json",
            "accept_or_reject_handoff_outside_studio",
        ),
        action(
            "adapter.hostess.verify_staging_file_plan_checksum",
            "rusty.hostess",
            "hostess_checksum_gate",
            "hostess.verify.staging_file_plan_checksum",
            "hostess.verify_staging_file_plan_checksum",
            "file-plan.json",
            "verify_file_plan_checksum_outside_studio",
        ),
        action(
            "adapter.hostess.review_staging_file_requests",
            "rusty.hostess",
            "hostess_file_plan_review_gate",
            "hostess.review.staging_file_requests",
            "hostess.review_staging_file_requests",
            "file-plan.json",
            "review_shared_and_target_requests_outside_studio",
        ),
        action(
            "adapter.hostess.copy_staging_files",
            "rusty.hostess",
            "hostess_file_copy_request",
            "hostess.stage.files_from_plan",
            "hostess.copy_staging_files",
            "file-plan.json",
            "copy_stage_files_outside_studio",
        ),
        action(
            "adapter.manifold.review_command_session_contract",
            "rusty.manifold",
            "manifold_contract_review",
            "manifold.review.command_session_contract",
            "manifold.review_command_session_contract",
            "handoff.json",
            "review_command_session_contract_outside_studio",
        ),
        action(
            "adapter.hostess.collect_install_launch_evidence",
            "rusty.hostess",
            "hostess_evidence_collection_request",
            "hostess.collect.install_launch_evidence",
            "hostess.collect_install_launch_evidence",
            "handoff.json",
            "collect_install_launch_evidence_outside_studio",
        ),
    ]
    action_ids = [entry["action_id"] for entry in actions]
    return {
        "$schema": adapter.REQUEST_SCHEMA,
        "request_id": (
            "studio.hostess_staging_execution_request."
            "studio.project.synthetic_wave.rev1.synthetic-hostess-staging-ready"
        ),
        "status": "ready",
        "issue_code": None,
        "execution_policy": "not_executed.hostess_request_only",
        "adapter_owner": "rusty.hostess",
        "requester_role": "rusty.studio",
        "command_session_authority": "rusty.manifold",
        "install_launch_evidence_authority": "rusty.hostess",
        "studio_role": "authoring.export_planning",
        "adapter_action_count": len(actions),
        "ready_adapter_action_count": len(actions),
        "blocked_adapter_action_count": 0,
        "prohibited_studio_actions": copy.copy(adapter.REQUIRED_PROHIBITED_ACTIONS),
        "actions": actions,
        "ack_template": {
            "$schema": adapter.ACK_SCHEMA,
            "request_id": (
                "studio.hostess_staging_execution_request."
                "studio.project.synthetic_wave.rev1.synthetic-hostess-staging-ready"
            ),
            "accepted_by": "rusty.hostess",
            "ack_status": "pending",
            "execution_in_studio": False,
            "command_session_authority": "rusty.manifold",
            "install_launch_evidence_authority": "rusty.hostess",
            "required_action_ids": action_ids,
            "accepted_action_ids": [],
            "required_evidence_kinds": copy.copy(adapter.REQUIRED_EVIDENCE_KINDS),
            "issue_code": None,
        },
        "reject_template": {
            "$schema": adapter.REJECT_SCHEMA,
            "request_id": (
                "studio.hostess_staging_execution_request."
                "studio.project.synthetic_wave.rev1.synthetic-hostess-staging-ready"
            ),
            "rejected_by": "rusty.hostess",
            "reject_status": "pending",
            "execution_in_studio": False,
            "request_action_ids": action_ids,
            "rejected_action_ids": [],
            "reason_code": None,
            "next_required_action": "hostess_ack_or_reject_request_outside_studio",
            "issue_code": None,
        },
    }


def action(
    action_id: str,
    owner: str,
    action_kind: str,
    route_kind: str,
    source_item_id: str,
    expected_input_path: str,
    next_required_action: str,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "owner": owner,
        "status": "ready",
        "issue_code": None,
        "action_kind": action_kind,
        "route_kind": route_kind,
        "source_item_id": source_item_id,
        "responsible_authority": owner,
        "expected_input_path": expected_input_path,
        "next_required_action": next_required_action,
        "ack_required": True,
        "execution_in_studio": False,
    }


def expected_action_ids() -> list[str]:
    return [entry["action_id"] for entry in valid_request()["actions"]]  # type: ignore[index]


def ready_pmb_package_evidence_intake() -> dict[str, object]:
    entries = [
        {
            "check_id": check_id,
            "source_status": "pass",
            "evidence": "synthetic projected-motion breath package evidence passed",
            "required_for_studio": True,
            "decision": "ready",
            "next_required_action": "review_package_in_studio",
            "issue_code": None,
        }
        for check_id in adapter.PMB_REQUIRED_PACKAGE_CHECKS
    ]
    return {
        "$schema": adapter.STUDIO_PACKAGE_EVIDENCE_INTAKE_SCHEMA,
        "source_report_schema": "rusty.manifold.package.validation_report.v1",
        "source_report_path": "fixtures/projected-motion-breath/package-validation.json",
        "target_package_id": adapter.PMB_TARGET_PACKAGE_ID,
        "status": "ready",
        "issue_code": None,
        "execution_policy": "not_executed.review_only",
        "runtime_authority": "rusty.manifold",
        "authoring_authority": "rusty.studio",
        "platform_validation_authority": "rusty.hostess",
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "source_report_status": "pass",
        "source_check_count": len(entries),
        "target_package_check_count": len(entries),
        "required_check_count": len(entries),
        "ready_required_check_count": len(entries),
        "blocked_required_check_count": 0,
        "observed_check_count": 0,
        "entries": entries,
        "prohibited_actions": [
            "build",
            "install",
            "launch",
            "open_command_session",
            "collect_device_evidence",
            "start_runtime_package",
        ],
        "checks": [],
    }


def ready_pmb_authoring_review() -> dict[str, object]:
    return {
        "$schema": adapter.STUDIO_PMB_AUTHORING_REVIEW_SCHEMA,
        "source_intake_schema": adapter.STUDIO_PACKAGE_EVIDENCE_INTAKE_SCHEMA,
        "source_intake_path": "fixtures/projected-motion-breath/package-evidence-intake.json",
        "source_profile_schema": "rusty.motion_breath_profile.v1",
        "source_profile_path": "fixtures/projected-motion-breath/profile-synthetic.json",
        "target_package_id": adapter.PMB_TARGET_PACKAGE_ID,
        "target_module_id": adapter.PMB_TARGET_MODULE_ID,
        "profile_id": "profile.projected_motion_breath.synthetic_default",
        "status": "ready",
        "issue_code": None,
        "execution_policy": "not_executed.proposal_only",
        "runtime_authority": "rusty.manifold",
        "authoring_authority": "rusty.studio",
        "platform_validation_authority": "rusty.hostess",
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "package_evidence_status": "ready",
        "package_required_check_count": len(adapter.PMB_REQUIRED_PACKAGE_CHECKS),
        "package_ready_required_check_count": len(adapter.PMB_REQUIRED_PACKAGE_CHECKS),
        "package_blocked_required_check_count": 0,
        "input_kinds": ["pose", "vector3"],
        "projection_mode": "controller_relative_axis",
        "fallback_projection_mode": "polar_acc_axis",
        "proposed_command_id": adapter.PMB_PROPOSED_COMMAND_ID,
        "proposed_profile_operation": "propose_profile_for_runtime_owner_review",
        "required_package_checks": copy.copy(adapter.PMB_REQUIRED_PACKAGE_CHECKS),
        "prohibited_actions": [
            "build",
            "install",
            "launch",
            "open_command_session",
            "collect_device_evidence",
            "start_runtime_package",
        ],
        "checks": [],
    }


def ready_pmb_source_adapter_selection_review() -> dict[str, object]:
    return {
        "$schema": adapter.STUDIO_PMB_SOURCE_ADAPTER_SELECTION_REVIEW_SCHEMA,
        "source_authoring_review_schema": adapter.STUDIO_PMB_AUTHORING_REVIEW_SCHEMA,
        "source_authoring_review_path": (
            "fixtures/projected-motion-breath/pmb-authoring-review.json"
        ),
        "source_descriptor_schema": (
            "rusty.manifold.projected_motion_breath.source_adapter_descriptors.v1"
        ),
        "source_descriptor_path": (
            "fixtures/projected-motion-breath/source-adapter-descriptors.json"
        ),
        "target_package_id": adapter.PMB_TARGET_PACKAGE_ID,
        "target_module_id": adapter.PMB_TARGET_MODULE_ID,
        "profile_id": "profile.projected_motion_breath.synthetic_default",
        "selected_adapter_id": (
            "adapter.projected_motion_breath.external_patch_stream_bridge_shape"
        ),
        "selected_source_kind": "external_patch_stream_bridge",
        "selected_input_kind": "vector3",
        "selected_output_stream_id": "stream.motion.vector3",
        "status": "ready",
        "issue_code": None,
        "execution_policy": "not_executed.proposal_only",
        "runtime_authority": "rusty.manifold",
        "authoring_authority": "rusty.studio",
        "platform_validation_authority": "rusty.hostess",
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "source_authoring_review_status": "ready",
        "source_descriptor_count": 5,
        "matching_descriptor_count": 1,
        "proposal_kind": "propose_source_adapter_for_runtime_owner_review",
        "prohibited_actions": [
            "build",
            "install",
            "launch",
            "open_command_session",
            "collect_device_evidence",
            "start_runtime_package",
        ],
        "checks": [],
    }


def ready_pmb_validation_handoff() -> dict[str, object]:
    return adapter.build_projected_motion_breath_validation_handoff(
        ready_pmb_authoring_review(),
        ready_pmb_package_evidence_intake(),
    )


def ready_platform_smoke_plan() -> dict[str, object]:
    request = valid_request()
    handoff = adapter.build_smoke_handoff_checklist(
        request,
        adapter.build_intake_report(request),
        adapter.build_ack_fixture(request),
        target_profile="hostess.t.desktop.schema_smoke",
    )
    dry_run = adapter.build_smoke_dry_run_request(handoff)
    receipt = adapter.build_smoke_dry_run_receipt(dry_run)
    preflight = adapter.build_smoke_execution_preflight(dry_run, receipt)
    execution = adapter.build_smoke_host_shell_execution(preflight)
    bundle = adapter.build_smoke_review_bundle(execution)
    return adapter.build_platform_smoke_plan(
        bundle,
        target_platform="hostess.quest.operator_controlled_smoke_plan",
    )


def ready_pmb_shell_handoff_review() -> dict[str, object]:
    return {
        "$schema": adapter.STUDIO_PMB_SHELL_HANDOFF_REVIEW_SCHEMA,
        "source_evidence_schema": "rusty.hostess.projected_motion_breath.shell_handoff_validation_evidence.v1",
        "source_evidence_path": "target/pmb-shell-handoff.json",
        "target_package_id": "package.projected_motion_breath",
        "handoff_id": "shell_handoff.projected_motion_breath.loopback",
        "target_host_profile": "host.profile.desktop",
        "shell_app_id": "app.makepad_camera_shell",
        "status": "ready",
        "issue_code": None,
        "execution_policy": "not_executed.review_only",
        "runtime_authority": "rusty.manifold",
        "authoring_authority": "rusty.studio",
        "platform_validation_authority": "rusty.hostess",
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "broker_transport_used": False,
        "downstream_shell_runtime_used": False,
        "legacy_app_dependency_used": False,
        "required_binding_count": 3,
        "ready_required_binding_count": 3,
        "stream_bindings": [
            "stream.motion.object_pose:publish",
            "stream.breath.volume.selected:subscribe",
            "stream.breath.feedback_receipt:publish",
        ],
        "command_ids": ["command.breath.status", "command.breath.set_profile"],
        "transport_ids": ["transport.localhost.tcp"],
        "feedback_receipt_exported": True,
        "feedback_sink_provides_receipt": True,
        "proposal_kind": "review_shell_handoff_for_hostess_owner_execution",
        "prohibited_actions": [
            "start_runtime_package",
            "open_broker_transport",
            "launch_downstream_shell",
        ],
        "checks": [],
    }


def dotted_test_id(value: object, fallback: str) -> str:
    text = str(value) if value is not None else fallback
    cleaned = (
        text.strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )
    return cleaned or fallback


def ready_manifold_shell_handoff_for_test(
    target_kind: object = "desktop",
    graph_id: object = "studio.graph.synthetic",
    consumer_id: object = "rusty-studio-desktop-shell",
) -> dict[str, object]:
    target = dotted_test_id(target_kind, "shared")
    graph = dotted_test_id(graph_id, "shared")
    consumer = dotted_test_id(consumer_id, "shared_shell")
    handoff_suffix = f"{target}.{graph}.{consumer}"
    return {
        "$schema": adapter.MANIFOLD_SHELL_HANDOFF_SCHEMA,
        "handoff_id": f"shell_handoff.{handoff_suffix}",
        "handoff_revision": 1,
        "target_host_profile": f"host.profile.{target}",
        "shell_app_id": f"app.{consumer}",
        "validation_slot_id": "hostess.validation_slot.synthetic_smoke",
        "stream_bindings": [
            {
                "stream_id": "stream.synthetic.wave",
                "direction": "subscribe",
                "role": "shell.stream.source_input",
                "required": True,
            },
            {
                "stream_id": "stream.synthetic.rms",
                "direction": "subscribe",
                "role": "shell.stream.derived_feedback",
                "required": True,
            },
        ],
        "command_ids": [
            "command.module.start",
            "command.module.stop",
        ],
        "transport_offers": [
            {
                "transport_id": f"transport.shell_handoff.{handoff_suffix}",
                "transport": "http",
                "endpoint_id": "endpoint.headset_loopback",
            }
        ],
        "expected_scorecard_id": "scorecard.hostess.synthetic_smoke",
    }


def ready_manifold_shell_handoff_review_receipt_for_test(
    handoff: dict[str, object],
) -> dict[str, object]:
    return {
        "$schema": adapter.MANIFOLD_SHELL_HANDOFF_REVIEW_RECEIPT_SCHEMA,
        "review_id": f"manifold.shell_handoff_review.{handoff['handoff_id']}",
        "handoff_id": handoff["handoff_id"],
        "handoff_revision": handoff["handoff_revision"],
        "target_host_profile": handoff["target_host_profile"],
        "shell_app_id": handoff["shell_app_id"],
        "validation_slot_id": handoff["validation_slot_id"],
        "status": adapter.PASS_STATUS,
        "issue_code": None,
        "manifold_authority": "rusty.manifold",
        "reviewed_stream_ids": adapter.manifold_shell_handoff_stream_ids(handoff),
        "reviewed_command_ids": handoff["command_ids"],
        "reviewed_transport_ids": adapter.manifold_shell_handoff_transport_ids(
            handoff
        ),
        "reviewed_endpoint_ids": adapter.manifold_shell_handoff_endpoint_ids(
            handoff
        ),
        "runtime_execution_performed": False,
        "platform_execution_performed": False,
        "launch_started": False,
        "command_session_started": False,
        "legacy_app_dependency_used": False,
        "checks": [
            {
                "check_id": "manifold.check.shell_handoff.synthetic",
                "status": adapter.PASS_STATUS,
                "evidence": "synthetic Manifold shell handoff review passed",
                "issue_code": None,
            }
        ],
    }


def ready_platform_smoke_execution_chain() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    plan = ready_platform_smoke_plan()
    approval = adapter.build_platform_smoke_approval_receipt(plan)
    execution_request = adapter.build_platform_smoke_execution_request(plan, approval)
    execution_receipt = adapter.build_platform_smoke_execution_receipt(
        plan,
        approval,
        execution_request,
    )
    return plan, approval, execution_request, execution_receipt


def ready_platform_smoke_operator_start_chain() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    plan, approval, execution_request, execution_receipt = ready_platform_smoke_execution_chain()
    gate = adapter.build_platform_smoke_operator_start_gate(
        plan,
        approval,
        execution_request,
        execution_receipt,
    )
    return plan, approval, execution_request, execution_receipt, gate


def ready_platform_smoke_operator_start_preflight_chain() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    plan, approval, execution_request, execution_receipt, gate = (
        ready_platform_smoke_operator_start_chain()
    )
    preflight = adapter.build_platform_smoke_operator_start_preflight_receipt(
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
    )
    return plan, approval, execution_request, execution_receipt, gate, preflight


def ready_platform_smoke_execution_report_chain() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    plan, approval, execution_request, execution_receipt, gate, preflight = (
        ready_platform_smoke_operator_start_preflight_chain()
    )
    report = adapter.build_platform_smoke_execution_report(
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
    )
    return plan, approval, execution_request, execution_receipt, gate, preflight, report


def ready_pmb_platform_smoke_evidence_attachment_chain() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    plan, approval, execution_request, execution_receipt, gate = (
        ready_platform_smoke_operator_start_chain()
    )
    preflight = adapter.build_platform_smoke_operator_start_preflight_receipt(
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        pmb_shell_handoff_review=ready_pmb_shell_handoff_review(),
        require_pmb_shell_handoff_review=True,
    )
    report = adapter.build_platform_smoke_execution_report(
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
    )
    attachment = adapter.build_platform_smoke_evidence_attachment_receipt(
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
        report,
    )
    return (
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
        report,
        attachment,
    )


def ready_platform_smoke_evidence_attachment_chain() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    plan, approval, execution_request, execution_receipt, gate, preflight, report = (
        ready_platform_smoke_execution_report_chain()
    )
    attachment = adapter.build_platform_smoke_evidence_attachment_receipt(
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
        report,
    )
    return (
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
        report,
        attachment,
    )


def ready_operator_release_inputs() -> tuple[dict[str, object], dict[str, object]]:
    (
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
        report,
        attachment,
    ) = ready_platform_smoke_evidence_attachment_chain()
    evidence_review = adapter.build_platform_smoke_evidence_review(
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
        report,
        attachment,
    )
    replay_receipt = adapter.build_projected_motion_breath_replay_validation_receipt(
        ready_pmb_validation_handoff()
    )
    return evidence_review, replay_receipt


def ready_pmb_operator_release_inputs() -> tuple[dict[str, object], dict[str, object]]:
    (
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
        report,
        attachment,
    ) = ready_pmb_platform_smoke_evidence_attachment_chain()
    evidence_review = adapter.build_platform_smoke_evidence_review(
        plan,
        approval,
        execution_request,
        execution_receipt,
        gate,
        preflight,
        report,
        attachment,
    )
    replay_receipt = adapter.build_projected_motion_breath_replay_validation_receipt(
        ready_pmb_validation_handoff()
    )
    return evidence_review, replay_receipt


def ready_studio_hostess_staging_file_plan() -> dict[str, object]:
    handoff = ready_studio_hostess_staging_handoff()
    requests = []
    for request in handoff["request_summaries"]:
        destination_root = request["destination_root"]
        target_kind = request["target_kind"]
        graph_id = request["graph_id"]
        consumer_id = request["consumer_id"]
        request_id = request["request_id"]
        request_files = [
            {
                "artifact_kind": "shell_bundle_dir",
                "source_path": f"target/studio-selected-shell/{request_id}/bundle",
                "destination_path": f"{destination_root}/bundle",
                "target_kind": target_kind,
                "graph_id": graph_id,
                "consumer_id": consumer_id,
                "route_hints": ["evidence.filesystem"],
                "source_action_ids": [
                    "hostess.collect_install_launch_evidence",
                    "hostess.stage_generated_shells",
                ],
                "source_route_kinds": [
                    "hostess.collect.install_launch_evidence",
                    "hostess.stage.generated_shells",
                ],
            },
            {
                "artifact_kind": "shell_descriptor",
                "source_path": (
                    f"target/studio-selected-shell/{request_id}/descriptor.json"
                ),
                "destination_path": f"{destination_root}/descriptor/shell.json",
                "target_kind": target_kind,
                "graph_id": graph_id,
                "consumer_id": consumer_id,
                "route_hints": ["manifold.command_session_contract"],
                "source_action_ids": [
                    "hostess.stage_generated_shells",
                    "manifold.review_command_session_contract",
                ],
                "source_route_kinds": [
                    "hostess.stage.generated_shells",
                    "manifold.review.command_session_contract",
                ],
            },
            {
                "artifact_kind": "manifold_shell_handoff",
                "source_path": (
                    f"target/studio-selected-shell/{request_id}/manifold-shell-handoff.json"
                ),
                "destination_path": f"{destination_root}/manifold/shell-handoff.json",
                "target_kind": target_kind,
                "graph_id": graph_id,
                "consumer_id": consumer_id,
                "route_hints": ["manifold.shell_handoff_review"],
                "source_action_ids": [
                    "hostess.stage_generated_shells",
                    "manifold.review_shell_handoff",
                ],
                "source_route_kinds": [
                    "hostess.stage.generated_shells",
                    "manifold.review.shell_handoff",
                ],
            },
            {
                "artifact_kind": "install_launch_evidence_template",
                "source_path": (
                    f"target/studio-selected-shell/{request_id}/evidence-template.json"
                ),
                "destination_path": (
                    f"{destination_root}/evidence/install-launch-template.json"
                ),
                "target_kind": target_kind,
                "graph_id": graph_id,
                "consumer_id": consumer_id,
                "route_hints": ["hostess.install_launch_evidence"],
                "source_action_ids": [
                    "hostess.collect_install_launch_evidence",
                    "hostess.stage_generated_shells",
                ],
                "source_route_kinds": [
                    "hostess.collect.install_launch_evidence",
                    "hostess.stage.generated_shells",
                ],
            },
        ]
        request_view = copy.deepcopy(request)
        request_view["planned_files"] = request_files
        request_view["planned_file_count"] = len(request_files)
        requests.append(request_view)
    return {
        "$schema": adapter.STUDIO_HOSTESS_STAGING_FILE_PLAN_SCHEMA,
        "source_preview_schema": "rusty.studio.shell_hostess_staging_preview_manifest.v1",
        "preview_path": handoff["preview_path"],
        "intake_path": handoff["intake_path"],
        "package_path": handoff["package_path"],
        "handoff_manifest_path": handoff["handoff_manifest_path"],
        "selected_candidate_id": handoff["selected_candidate_id"],
        "manifest_id": handoff["manifest_id"],
        "project_id": handoff["project_id"],
        "project_revision": handoff["project_revision"],
        "status": "ready",
        "issue_code": None,
        "execution_policy": "not_executed.dry_run_only",
        "staging_owner": "rusty.hostess",
        "command_session_authority": "rusty.manifold",
        "install_launch_evidence_authority": "rusty.hostess",
        "studio_role": "authoring.export_planning",
        "preview_group_count": 2,
        "ready_preview_group_count": 2,
        "blocked_preview_group_count": 0,
        "source_artifact_count": sum(
            request["planned_file_count"] for request in requests
        ),
        "planned_file_count": sum(
            request["planned_file_count"] for request in requests
        ),
        "duplicate_artifact_count": 0,
        "request_count": len(requests),
        "ready_request_count": len(requests),
        "blocked_request_count": 0,
        "target_request_count": sum(
            1 for request in requests if request["target_kind"] is not None
        ),
        "shared_request_count": sum(
            1 for request in requests if request["target_kind"] is None
        ),
        "prohibited_actions": [
            "stage_generated_shells",
            "install",
            "launch",
            "open_command_session",
            "collect_device_evidence",
            "collect_install_launch_evidence",
        ],
        "requests": requests,
    }


def materialized_studio_hostess_staging_file_plan(source_root: Path) -> dict[str, object]:
    file_plan = ready_studio_hostess_staging_file_plan()
    for request in file_plan["requests"]:
        safe_request_id = str(request["request_id"]).replace("/", "_").replace("\\", "_")
        for index, planned_file in enumerate(request["planned_files"]):
            artifact_kind = planned_file["artifact_kind"]
            source_path = source_root / safe_request_id / f"{index}-{artifact_kind}"
            if artifact_kind == "shell_bundle_dir":
                source_path.mkdir(parents=True, exist_ok=True)
                (source_path / "bundle-marker.txt").write_text(
                    f"{safe_request_id}:{artifact_kind}\n",
                    encoding="utf-8",
                )
            elif artifact_kind == "manifold_shell_handoff":
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_text(
                    json.dumps(
                        ready_manifold_shell_handoff_for_test(
                            planned_file["target_kind"],
                            planned_file["graph_id"],
                            planned_file["consumer_id"],
                        )
                    ),
                    encoding="utf-8",
                )
            else:
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_text(
                    f"{safe_request_id}:{artifact_kind}\n",
                    encoding="utf-8",
                )
            planned_file["source_path"] = str(source_path)
    return file_plan


def hostess_staged_payload_manifest_for_test(root: Path) -> dict[str, object]:
    evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
    release_bundle = adapter.build_operator_release_readiness_bundle(
        evidence_review,
        replay_receipt,
    )
    acceptance_receipt = adapter.build_hostess_staging_handoff_acceptance_receipt(
        release_bundle,
        ready_studio_hostess_staging_handoff(),
        ready_studio_hostess_staging_acceptance_manifest(),
    )
    file_plan = materialized_studio_hostess_staging_file_plan(root / "source")
    file_plan_receipt = adapter.build_hostess_staging_file_plan_receipt(
        acceptance_receipt,
        file_plan,
        staging_root=str(root / "clean-hostess-staging"),
    )
    copy_receipt = adapter.build_hostess_staging_file_copy_receipt(
        file_plan_receipt,
        file_plan,
    )
    return adapter.build_hostess_staged_payload_manifest_receipt(copy_receipt)


def ready_studio_hostess_staging_handoff() -> dict[str, object]:
    return {
        "$schema": adapter.STUDIO_HOSTESS_STAGING_HANDOFF_SCHEMA,
        "source_file_plan_schema": "rusty.studio.shell_hostess_staging_file_plan.v1",
        "file_plan_path": "target/studio-shell-handoffs/shell-hostess-staging-file-plan.json",
        "preview_path": "target/studio-shell-handoffs/shell-hostess-staging-preview.json",
        "intake_path": "target/studio-shell-handoffs/shell-hostess-owner-intake.json",
        "package_path": "target/studio-shell-handoffs/shell-hostess-handoff-package.json",
        "handoff_manifest_path": "target/studio-shell-handoffs/shell-handoffs.json",
        "selected_candidate_id": "synthetic-ready-candidate",
        "envelope_id": "studio.hostess_staging_handoff.studio.project.synthetic.rev1",
        "manifest_id": "studio.shell_handoffs.studio.project.synthetic",
        "project_id": "studio.project.synthetic",
        "project_revision": 1,
        "status": "ready",
        "issue_code": None,
        "execution_policy": "not_executed.handoff_only",
        "handoff_owner": "rusty.hostess",
        "staging_owner": "rusty.hostess",
        "command_session_authority": "rusty.manifold",
        "install_launch_evidence_authority": "rusty.hostess",
        "studio_role": "authoring.export_planning",
        "planned_file_count": 8,
        "request_count": 2,
        "ready_request_count": 2,
        "blocked_request_count": 0,
        "target_request_count": 1,
        "shared_request_count": 1,
        "instruction_count": 4,
        "ready_instruction_count": 4,
        "blocked_instruction_count": 0,
        "provenance": {
            "checksum_algorithm": "fnv1a64.studio_staging_file_plan.v1",
            "plan_checksum": "synthetic-plan-checksum",
            "source_artifact_kinds": [
                "shell_descriptor",
                "manifold_shell_handoff",
                "shell_template_manifest",
                "shell_handoff_manifest",
            ],
            "source_action_ids": [
                "hostess.stage_generated_shells",
                "manifold.review_command_session_contract",
                "manifold.review_shell_handoff",
                "hostess.collect_install_launch_evidence",
            ],
            "source_route_kinds": [
                "hostess.stage.generated_shells",
                "manifold.review.command_session_contract",
                "manifold.review.shell_handoff",
                "hostess.collect.install_launch_evidence",
            ],
            "target_keys": ["desktop/studio.graph.synthetic", "shared"],
            "destination_roots": [
                "hostess-staging/targets/desktop/studio.graph.synthetic",
                "hostess-staging/shared",
            ],
        },
        "request_summaries": [
            {
                "request_id": "hostess.staging_file_plan.desktop.studio.graph.synthetic",
                "request_kind": "hostess_target_staging_file_plan",
                "owner": "rusty.hostess",
                "status": "ready",
                "target_key": "desktop/studio.graph.synthetic",
                "target_kind": "desktop",
                "graph_id": "studio.graph.synthetic",
                "consumer_id": "rusty-studio-desktop-shell",
                "destination_root": "hostess-staging/targets/desktop/studio.graph.synthetic",
                "planned_file_count": 4,
                "route_kinds": [
                    "hostess.collect.install_launch_evidence",
                    "hostess.stage.generated_shells",
                    "manifold.review.command_session_contract",
                    "manifold.review.shell_handoff",
                ],
                "action_ids": [
                    "hostess.collect_install_launch_evidence",
                    "hostess.stage_generated_shells",
                    "manifold.review_command_session_contract",
                    "manifold.review_shell_handoff",
                ],
            },
            {
                "request_id": "hostess.staging_file_plan.shared",
                "request_kind": "hostess_shared_staging_file_plan",
                "owner": "rusty.hostess",
                "status": "ready",
                "target_key": "shared",
                "target_kind": None,
                "graph_id": None,
                "consumer_id": None,
                "destination_root": "hostess-staging/shared",
                "planned_file_count": 4,
                "route_kinds": [
                    "hostess.collect.install_launch_evidence",
                    "hostess.stage.generated_shells",
                    "manifold.review.command_session_contract",
                    "manifold.review.shell_handoff",
                    "hostess.review.release_candidate",
                ],
                "action_ids": [
                    "hostess.collect_install_launch_evidence",
                    "hostess.stage_generated_shells",
                    "manifold.review_command_session_contract",
                    "manifold.review_shell_handoff",
                    "hostess.review_release_candidate",
                ],
            },
        ],
        "owner_instructions": [
            {
                "instruction_id": "hostess.review_staging_handoff",
                "owner": "rusty.hostess",
                "status": "ready",
                "issue_code": None,
                "instruction_kind": "hostess_handoff_review",
                "route_kind": "hostess.review.staging_handoff",
                "source": "hostess_staging_handoff_envelope",
                "next_required_action": "review_staging_handoff_outside_studio",
                "prohibited_in_studio": True,
                "expected_input_path": "target/studio-shell-handoffs/shell-hostess-staging-file-plan.json",
            },
            {
                "instruction_id": "hostess.copy_staging_files",
                "owner": "rusty.hostess",
                "status": "ready",
                "issue_code": None,
                "instruction_kind": "hostess_file_copy_request",
                "route_kind": "hostess.stage.files_from_plan",
                "source": "hostess_staging_file_plan",
                "next_required_action": "copy_stage_files_outside_studio",
                "prohibited_in_studio": True,
                "expected_input_path": "target/studio-shell-handoffs/shell-hostess-staging-file-plan.json",
            },
            {
                "instruction_id": "manifold.review_command_session_contract",
                "owner": "rusty.manifold",
                "status": "ready",
                "issue_code": None,
                "instruction_kind": "manifold_contract_review",
                "route_kind": "manifold.review.command_session_contract",
                "source": "hostess_staging_file_plan",
                "next_required_action": "review_command_session_contract_outside_studio",
                "prohibited_in_studio": True,
                "expected_input_path": "target/studio-shell-handoffs/shell-hostess-staging-file-plan.json",
            },
            {
                "instruction_id": "manifold.review_shell_handoff",
                "owner": "rusty.manifold",
                "status": "ready",
                "issue_code": None,
                "instruction_kind": "manifold_shell_handoff_review",
                "route_kind": "manifold.review.shell_handoff",
                "source": "hostess_staging_file_plan",
                "next_required_action": "review_shell_handoff_outside_studio",
                "prohibited_in_studio": True,
                "expected_input_path": "target/studio-shell-handoffs/shell-hostess-staging-file-plan.json",
            },
        ],
        "prohibited_actions": [
            "stage_generated_shells",
            "install",
            "launch",
            "open_command_session",
            "collect_device_evidence",
            "collect_install_launch_evidence",
        ],
        "checks": [
            {
                "check_id": "studio.check.shell_hostess_staging_handoff.file_plan_ready",
                "status": "pass",
                "evidence": "source Hostess staging file plan is ready",
                "issue_code": None,
            }
        ],
    }


def ready_studio_hostess_staging_acceptance_manifest() -> dict[str, object]:
    return {
        "$schema": adapter.STUDIO_HOSTESS_STAGING_ACCEPTANCE_MANIFEST_SCHEMA,
        "acceptance_id": "synthetic-hostess-staging-ready",
        "label": "Synthetic Hostess staging ready acceptance",
        "checklist_path": "target/studio-shell-handoffs/shell-hostess-staging-acceptance-checklist.json",
        "checklist_schema": "rusty.studio.shell_hostess_staging_acceptance_checklist.v1",
        "envelope_id": "studio.hostess_staging_handoff.studio.project.synthetic.rev1",
        "manifest_id": "studio.shell_handoffs.studio.project.synthetic",
        "project_id": "studio.project.synthetic",
        "project_revision": 1,
        "status": "ready",
        "issue_code": None,
        "execution_policy": "not_executed.acceptance_check_only",
        "checklist_owner": "rusty.hostess",
        "handoff_owner": "rusty.hostess",
        "staging_owner": "rusty.hostess",
        "command_session_authority": "rusty.manifold",
        "install_launch_evidence_authority": "rusty.hostess",
        "studio_role": "authoring.export_planning",
        "request_count": 2,
        "ready_request_count": 2,
        "blocked_request_count": 0,
        "instruction_count": 4,
        "ready_instruction_count": 4,
        "blocked_instruction_count": 0,
        "checksum_algorithm": "fnv1a64.studio_staging_file_plan.v1",
        "plan_checksum": "synthetic-plan-checksum",
        "ready_item_count": 6,
        "blocked_item_count": 0,
        "rejected_item_count": 0,
        "prohibited_actions": [
            "stage_generated_shells",
            "install",
            "launch",
            "open_command_session",
            "collect_device_evidence",
            "collect_install_launch_evidence",
        ],
    }


if __name__ == "__main__":
    unittest.main()

__all__ = [
    "valid_request",
    "action",
    "expected_action_ids",
    "ready_pmb_package_evidence_intake",
    "ready_pmb_authoring_review",
    "ready_pmb_source_adapter_selection_review",
    "ready_pmb_validation_handoff",
    "ready_platform_smoke_plan",
    "ready_pmb_shell_handoff_review",
    "dotted_test_id",
    "ready_manifold_shell_handoff_for_test",
    "ready_manifold_shell_handoff_review_receipt_for_test",
    "ready_platform_smoke_execution_chain",
    "ready_platform_smoke_operator_start_chain",
    "ready_platform_smoke_operator_start_preflight_chain",
    "ready_platform_smoke_execution_report_chain",
    "ready_pmb_platform_smoke_evidence_attachment_chain",
    "ready_platform_smoke_evidence_attachment_chain",
    "ready_operator_release_inputs",
    "ready_pmb_operator_release_inputs",
    "ready_studio_hostess_staging_file_plan",
    "materialized_studio_hostess_staging_file_plan",
    "hostess_staged_payload_manifest_for_test",
    "ready_studio_hostess_staging_handoff",
    "ready_studio_hostess_staging_acceptance_manifest",
]
