"""Host-run evidence writers for Hostess PMB and live-capture routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.hostessctl.pmb_support import (
    host_app_for,
    iso_to_epoch_ms,
    module_segment,
    pmb_scorecard_check,
    scorecard_check,
    stream_segment,
)


def write_pmb_host_run_evidence(raw_evidence_path: Path, validation_report_path: Path, raw: dict[str, Any]) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_desktop_replay_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB desktop replay evidence and validation report passed",
        ),
        pmb_scorecard_check(
            "validation.check.package_manifest_hash",
            bool(raw.get("package", {}).get("package_manifest_sha256")),
            "PMB package manifest hash was recorded",
        ),
        pmb_scorecard_check(
            "validation.check.processor_core_execution",
            raw.get("execution", {}).get("processor_core_executed") is True,
            "PMB processor core executed through Hostess",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.desktop_replay.{started_ms}",
        "bundle_id": "host_run.bundle.projected_motion_breath.desktop_replay",
        "validation_slot_id": "host_run.slot.projected_motion_breath.desktop_replay",
        "host_profile": "host.desktop",
        "app_id": "app.rusty_hostess_t.desktop",
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.breath.projected_motion",
            "module.breath.dynamics",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_desktop_replay_evidence",
            "artifact.projected_motion_breath_core_validation_report",
            "artifact.projected_motion_breath_desktop_replay_validation_report",
            "artifact.host_run_evidence",
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.projected_motion_breath.desktop_replay",
            "target_id": f"host_run.run.projected_motion_breath.desktop_replay.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_live_route_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    summary = raw.get("route_report_summary", {})
    execution = raw.get("execution", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_live_route_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB live broker route self-test evidence and validation report passed",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_processor_core",
            execution.get("processor_core_executed") is True
            and execution.get("runtime_execution_performed") is True,
            "PMB processor core executed through Hostess",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_non_live_gate",
            execution.get("plan_only") is True
            and execution.get("broker_transport_used") is False
            and execution.get("live_sensor_used") is False
            and execution.get("quest_execution_performed") is False,
            "PMB route self-test did not use live broker/device resources",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_feedback_ack",
            int(summary.get("receipt_count", 0)) == int(summary.get("feedback_sample_count", -1))
            and int(summary.get("receipt_count", 0)) > 0,
            "PMB route self-test included one Makepad receipt plan per feedback sample",
            "validation.pmb_live_route_self_test_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.live_broker_route_self_test.{started_ms}",
        "bundle_id": "host_run.bundle.projected_motion_breath.live_broker_route_self_test",
        "validation_slot_id": "host_run.slot.projected_motion_breath.live_broker_route_self_test",
        "host_profile": "host.desktop",
        "app_id": "app.rusty_hostess_t.desktop",
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.breath.projected_motion",
            "module.breath.feedback_sink",
            "module.hostess.manifold_value_recorder",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_live_broker_route_self_test_evidence",
            "artifact.projected_motion_breath_live_broker_route_report",
            "artifact.projected_motion_breath_live_broker_route_self_test_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "input_stream_ids": summary.get("input_stream_ids", []),
            "normalized_stream_ids": summary.get("normalized_stream_ids", []),
            "output_stream_ids": summary.get("output_stream_ids", []),
            "source_route_count": summary.get("source_route_count"),
            "breath_sample_count": summary.get("breath_sample_count"),
            "feedback_sample_count": summary.get("feedback_sample_count"),
            "receipt_count": summary.get("receipt_count"),
            "plan_only": execution.get("plan_only"),
            "broker_transport_used": execution.get("broker_transport_used"),
            "live_sensor_used": execution.get("live_sensor_used"),
            "quest_execution_performed": execution.get("quest_execution_performed"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.projected_motion_breath.live_broker_route_self_test",
            "target_id": f"host_run.run.projected_motion_breath.live_broker_route_self_test.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_shell_handoff_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    shell_handoff = raw.get("shell_handoff", {})
    package_contract = raw.get("package_contract", {})
    execution = raw.get("execution", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB shell handoff evidence and validation report passed",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff_receipt_export",
            "stream.breath.feedback_receipt" in package_contract.get("exported_stream_ids", [])
            and "stream.breath.feedback_receipt" in package_contract.get("feedback_sink_provides_streams", []),
            "PMB package exports feedback receipts and the feedback sink provides them",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff_clean_boundary",
            execution.get("runtime_execution_performed") is False
            and execution.get("legacy_app_dependency_used") is False
            and execution.get("legacy_reference_repo_used") is False
            and execution.get("downstream_shell_runtime_used") is False,
            "PMB shell handoff host-run evidence records a package-only validation boundary",
            "validation.pmb_shell_handoff_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.shell_handoff.{started_ms}",
        "bundle_id": "host_run.bundle.projected_motion_breath.shell_handoff",
        "validation_slot_id": "host_run.slot.projected_motion_breath.shell_handoff",
        "host_profile": "host.desktop",
        "app_id": "app.rusty_hostess_t.desktop",
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.motion.object_pose_provider",
            "module.breath.projected_motion",
            "module.breath.feedback_sink",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_shell_handoff_evidence",
            "artifact.projected_motion_breath_shell_handoff_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "handoff_id": shell_handoff.get("handoff_id"),
            "target_host_profile": shell_handoff.get("target_host_profile"),
            "shell_app_id": shell_handoff.get("shell_app_id"),
            "stream_bindings": shell_handoff.get("binding_pairs", []),
            "command_ids": shell_handoff.get("command_ids", []),
            "transport_ids": [
                offer.get("transport_id")
                for offer in shell_handoff.get("transport_offers", [])
                if isinstance(offer, dict)
            ],
            "runtime_execution_performed": execution.get("runtime_execution_performed"),
            "broker_transport_used": execution.get("broker_transport_used"),
            "legacy_app_dependency_used": execution.get("legacy_app_dependency_used"),
            "legacy_reference_repo_used": execution.get("legacy_reference_repo_used"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.projected_motion_breath.shell_handoff",
            "target_id": f"host_run.run.projected_motion_breath.shell_handoff.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_android_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
    target: str,
    host_profile: str,
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_android_replay_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB Android replay evidence and validation report passed",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "validation.check.package_manifest_hash",
            bool(raw.get("package", {}).get("package_manifest_sha256")),
            "PMB package manifest hash was recorded",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "validation.check.processor_core_execution",
            raw.get("execution", {}).get("processor_core_executed") is True
            and raw.get("execution", {}).get("android_execution_performed") is True,
            "PMB processor core executed through Hostess Android app",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "validation.check.synthetic_quest_replay",
            target != "quest" or raw.get("execution", {}).get("quest_execution_performed") is True,
            "PMB synthetic replay executed on Quest target" if target == "quest" else "PMB synthetic replay executed on mobile target",
            "validation.pmb_android_replay_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.{target}_synthetic_replay.{started_ms}",
        "bundle_id": f"host_run.bundle.projected_motion_breath.{target}_synthetic_replay",
        "validation_slot_id": f"host_run.slot.projected_motion_breath.{target}_synthetic_replay",
        "host_profile": f"host.{host_profile}",
        "app_id": host_app_for(host_profile),
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.breath.projected_motion",
            "module.breath.dynamics",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_android_replay_evidence",
            "artifact.projected_motion_breath_core_validation_report",
            "artifact.projected_motion_breath_android_replay_validation_report",
            "artifact.host_run_evidence",
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": f"scorecard.host_run.projected_motion_breath.{target}_synthetic_replay",
            "target_id": f"host_run.run.projected_motion_breath.{target}_synthetic_replay.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_controller_preflight_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
    target: str,
    host_profile: str,
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    execution = raw.get("execution", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_controller_preflight_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB controller preflight evidence and validation report passed",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "validation.check.processor_core_execution",
            execution.get("processor_core_executed") is True
            and execution.get("runtime_execution_performed") is True
            and execution.get("android_execution_performed") is True,
            "PMB processor core executed through Hostess Android controller preflight",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "validation.check.controller_provider_route_ready",
            execution.get("controller_provider_route_ready") is True
            and execution.get("provider_boundary_exercised") is True
            and execution.get("pmb_controller_path_preflight_passed") is True,
            "controller provider route is ready at the PMB provider boundary",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "validation.check.non_human_gate",
            execution.get("controller_input_used") is False
            and execution.get("physical_controller_input_used") is False
            and execution.get("manual_controller_trial_required") is True
            and execution.get("human_controller_trial_performed") is False,
            "physical controller input was not used and the manual human controller trial remains pending",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "validation.check.quest_target",
            target != "quest" or execution.get("quest_execution_performed") is True,
            "PMB controller preflight executed on Quest target" if target == "quest" else "PMB controller preflight executed on mobile target",
            "validation.pmb_controller_preflight_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.{target}_controller_preflight.{started_ms}",
        "bundle_id": f"host_run.bundle.projected_motion_breath.{target}_controller_preflight",
        "validation_slot_id": f"host_run.slot.projected_motion_breath.{target}_controller_preflight",
        "host_profile": f"host.{host_profile}",
        "app_id": host_app_for(host_profile),
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.motion.object_pose_provider",
            "module.breath.projected_motion",
            "module.breath.dynamics",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_controller_preflight_evidence",
            "artifact.projected_motion_breath_controller_preflight_report",
            "artifact.projected_motion_breath_controller_preflight_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "pmb_controller_path_preflight_passed": execution.get("pmb_controller_path_preflight_passed"),
            "quest_execution_performed": execution.get("quest_execution_performed"),
            "processor_core_executed": execution.get("processor_core_executed"),
            "controller_provider_route_ready": execution.get("controller_provider_route_ready"),
            "physical_controller_input_used": execution.get("physical_controller_input_used"),
            "controller_input_used": execution.get("controller_input_used"),
            "manual_controller_trial_required": execution.get("manual_controller_trial_required"),
            "human_controller_trial_performed": execution.get("human_controller_trial_performed"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": f"scorecard.host_run.projected_motion_breath.{target}_controller_preflight",
            "target_id": f"host_run.run.projected_motion_breath.{target}_controller_preflight.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_quest_simulated_live_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
    target: str,
    host_profile: str,
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    execution = raw.get("execution", {})
    route = raw.get("route_report_summary", {})
    broker = raw.get("broker_publish_summary", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_quest_simulated_live_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB Quest simulated live evidence and validation report passed",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.quest_processor_authority",
            execution.get("pmd_computed_on_quest") is True
            and execution.get("pmd_computed_on_pc") is False
            and execution.get("processor_authority") == "quest_hostess_android_app",
            "PMD processing authority stayed on the Quest Android app",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.simulated_polar_controller_sources",
            {"bio:polar_acc", "stream.motion.object_pose"}.issubset(set(route.get("input_stream_ids", [])))
            and int(route.get("source_route_count", 0)) >= 2,
            "simulated Polar ACC and controller object-pose routes ran in the PMB processor",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.makepad_feedback_receipts",
            int(broker.get("feedback_published_count", 0)) > 0
            and int(broker.get("selected_breath_published_count", 0)) > 0
            and int(broker.get("feedback_receipt_count", 0)) == int(broker.get("selected_breath_published_count", -1)),
            "Makepad acknowledged every Quest-published selected breath sample",
            "validation.pmb_quest_simulated_live_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.{target}_simulated_live.{started_ms}",
        "bundle_id": f"host_run.bundle.projected_motion_breath.{target}_simulated_live",
        "validation_slot_id": f"host_run.slot.projected_motion_breath.{target}_simulated_live",
        "host_profile": f"host.{host_profile}",
        "app_id": host_app_for(host_profile),
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.motion.object_pose_provider",
            "module.breath.projected_motion",
            "module.breath.feedback_sink",
            "app.makepad_camera_shell.breath_feedback",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_quest_simulated_live_evidence",
            "artifact.projected_motion_breath_live_route_report",
            "artifact.projected_motion_breath_broker_publish_report",
            "artifact.projected_motion_breath_quest_simulated_live_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "pmd_computed_on_quest": execution.get("pmd_computed_on_quest"),
            "pmd_computed_on_pc": execution.get("pmd_computed_on_pc"),
            "processor_authority": execution.get("processor_authority"),
            "simulated_polar_provider_used": execution.get("simulated_polar_provider_used"),
            "simulated_controller_provider_used": execution.get("simulated_controller_provider_used"),
            "physical_polar_ble_used": execution.get("physical_polar_ble_used"),
            "physical_controller_input_used": execution.get("physical_controller_input_used"),
            "controller_input_used": execution.get("controller_input_used"),
            "manual_controller_trial_required": execution.get("manual_controller_trial_required"),
            "input_stream_ids": route.get("input_stream_ids", []),
            "selected_breath_published_count": broker.get("selected_breath_published_count"),
            "selected_source_effective": broker.get("selected_source_effective"),
            "feedback_published_count": broker.get("feedback_published_count"),
            "feedback_receipt_count": broker.get("feedback_receipt_count"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": f"scorecard.host_run.projected_motion_breath.{target}_simulated_live",
            "target_id": f"host_run.run.projected_motion_breath.{target}_simulated_live.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_quest_physical_live_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
    target: str,
    host_profile: str,
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    execution = raw.get("execution", {})
    capture = raw.get("input_capture_summary", {})
    route = raw.get("route_report_summary", {})
    broker = raw.get("broker_publish_summary", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_quest_physical_live_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB Quest physical live evidence and validation report passed",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.physical_polar_controller_inputs",
            execution.get("physical_polar_ble_used") is True
            and execution.get("physical_controller_input_used") is True
            and int(capture.get("polar_event_count", 0)) > 0
            and int(capture.get("active_tracked_connected_object_pose_count", 0)) > 0,
            "physical Polar ACC and active/tracked/connected controller pose events were captured on Quest",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.quest_processor_authority",
            execution.get("pmd_computed_on_quest") is True
            and execution.get("pmd_computed_on_pc") is False
            and execution.get("processor_authority") == "quest_hostess_android_app",
            "PMD processing authority stayed on the Quest Android app",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.real_transport_route",
            route.get("external_transport_used") is True
            and route.get("live_sensor_used") is True
            and route.get("plan_only_fixture") is False
            and {"bio:polar_acc", "stream.motion.object_pose"}.issubset(set(route.get("input_stream_ids", []))),
            "PMB route consumed real broker transport events",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.makepad_feedback_receipts",
            broker.get("publish_mode") == "event_driven_live_processor"
            and broker.get("live_publish_during_capture") is True
            and broker.get("incremental_processor_used") is True
            and broker.get("snapshot_replay_used") is False
            and int(broker.get("first_selected_publish_elapsed_ms", -1)) >= 0
            and int(broker.get("feedback_published_count", 0)) > 0
            and int(broker.get("selected_breath_published_count", 0)) > 0
            and int(broker.get("feedback_receipt_count", 0)) == int(broker.get("selected_breath_published_count", -1)),
            "Makepad acknowledged every Quest-published live selected breath sample",
            "validation.pmb_quest_physical_live_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.{target}_physical_live.{started_ms}",
        "bundle_id": f"host_run.bundle.projected_motion_breath.{target}_physical_live",
        "validation_slot_id": f"host_run.slot.projected_motion_breath.{target}_physical_live",
        "host_profile": f"host.{host_profile}",
        "app_id": host_app_for(host_profile),
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "provider.polar_h10.ble",
            "module.motion.object_pose_provider",
            "module.breath.projected_motion",
            "module.breath.feedback_sink",
            "app.makepad_camera_shell.breath_feedback",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_quest_physical_live_evidence",
            "artifact.projected_motion_breath_physical_input_capture_report",
            "artifact.projected_motion_breath_transport_events_jsonl",
            "artifact.projected_motion_breath_live_route_report",
            "artifact.projected_motion_breath_broker_publish_report",
            "artifact.projected_motion_breath_quest_physical_live_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "pmd_computed_on_quest": execution.get("pmd_computed_on_quest"),
            "pmd_computed_on_pc": execution.get("pmd_computed_on_pc"),
            "processor_authority": execution.get("processor_authority"),
            "physical_polar_ble_used": execution.get("physical_polar_ble_used"),
            "physical_controller_input_used": execution.get("physical_controller_input_used"),
            "simulated_polar_provider_used": execution.get("simulated_polar_provider_used"),
            "simulated_controller_provider_used": execution.get("simulated_controller_provider_used"),
            "input_stream_ids": route.get("input_stream_ids", []),
            "polar_event_count": capture.get("polar_event_count"),
            "object_pose_event_count": capture.get("object_pose_event_count"),
            "active_tracked_connected_object_pose_count": capture.get("active_tracked_connected_object_pose_count"),
            "selected_breath_published_count": broker.get("selected_breath_published_count"),
            "selected_source_effective": broker.get("selected_source_effective"),
            "publish_mode": broker.get("publish_mode"),
            "live_publish_during_capture": broker.get("live_publish_during_capture"),
            "incremental_processor_used": broker.get("incremental_processor_used"),
            "snapshot_replay_used": broker.get("snapshot_replay_used"),
            "first_selected_publish_elapsed_ms": broker.get("first_selected_publish_elapsed_ms"),
            "last_selected_publish_elapsed_ms": broker.get("last_selected_publish_elapsed_ms"),
            "feedback_published_count": broker.get("feedback_published_count"),
            "feedback_receipt_count": broker.get("feedback_receipt_count"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": f"scorecard.host_run.projected_motion_breath.{target}_physical_live",
            "target_id": f"host_run.run.projected_motion_breath.{target}_physical_live.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_contract_evidence(raw_evidence_path: Path, validation_report_path: Path, host_profile: str) -> None:
    raw = json.loads(raw_evidence_path.read_text(encoding="utf-8"))
    report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    stream_ids = [stream.get("stream_id") for stream in raw.get("streams", []) if stream.get("stream_id")]
    module_ids = [stream.get("module_id") for stream in raw.get("streams", []) if stream.get("module_id")]
    run_segment = module_segment(module_ids) if module_ids else stream_segment(stream_ids)
    checks = [
        scorecard_check(
            "validation.check.live_capture_status",
            report.get("status") == "pass" and raw.get("status") == "pass",
            "live capture evidence and validation report passed",
        ),
        scorecard_check(
            "validation.check.package_manifest_hash",
            bool(raw.get("package", {}).get("package_manifest_sha256")),
            "package manifest hash matched the supplied package root",
        ),
        scorecard_check(
            "validation.check.stream_samples",
            any(stream.get("status") == "pass" for stream in raw.get("streams", [])),
            "expected stream produced decoded samples or HR/RR events",
        ),
    ]
    status = "fail" if report.get("status") != "pass" or raw.get("status") != "pass" else "pass"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.live_capture.{host_profile}.{run_segment}.{started_ms}",
        "bundle_id": "host_run.bundle.polar_h10.live_smoke",
        "validation_slot_id": "host_run.slot.live_smoke",
        "host_profile": f"host.{host_profile}",
        "app_id": str(raw.get("software", {}).get("host_app", host_app_for(host_profile))),
        "package_ids": [str(raw.get("package", {}).get("package_id", "package.polar_h10"))],
        "module_ids": module_ids,
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.live_capture_evidence",
            "artifact.live_capture_validation_report",
            "artifact.host_run_evidence",
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.live_capture",
            "target_id": f"host_run.run.live_capture.{host_profile}.{run_segment}.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [
                {
                    "code": "validation.live_capture_failed",
                    "severity": "error",
                    "message": "; ".join(report.get("errors", [])),
                    "related_id": f"host.{host_profile}",
                }
            ]
            if report.get("errors")
            else [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")
