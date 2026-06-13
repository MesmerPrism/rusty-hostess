"""Projected Motion Breath validation handoff, replay receipt, and operator release tests."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import studio_staging_request as adapter
from tools.studio_staging.test_fixtures import *  # test fixture factories


class StudioStagingPmbReleaseTests(unittest.TestCase):
    def test_builds_projected_motion_breath_validation_handoff_without_execution(self) -> None:
        package_evidence = ready_pmb_package_evidence_intake()
        authoring_review = ready_pmb_authoring_review()

        handoff = adapter.build_projected_motion_breath_validation_handoff(
            authoring_review,
            package_evidence,
            Path("fixtures/projected-motion-breath/authoring-review.json"),
            Path("fixtures/projected-motion-breath/package-evidence-intake.json"),
        )

        self.assertEqual(handoff["$schema"], adapter.PMB_VALIDATION_HANDOFF_SCHEMA)
        self.assertEqual(handoff["status"], "ready")
        self.assertIsNone(handoff["issue_code"])
        self.assertEqual(handoff["handoff_owner"], "rusty.hostess")
        self.assertEqual(handoff["authoring_owner"], "rusty.studio")
        self.assertEqual(handoff["runtime_authority"], "rusty.manifold")
        self.assertEqual(handoff["platform_validation_authority"], "rusty.hostess")
        self.assertEqual(handoff["target_package_id"], adapter.PMB_TARGET_PACKAGE_ID)
        self.assertEqual(handoff["target_module_id"], adapter.PMB_TARGET_MODULE_ID)
        self.assertEqual(handoff["proposed_command_id"], adapter.PMB_PROPOSED_COMMAND_ID)
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(handoff[flag], flag)
        self.assertFalse(handoff["schema_path_execution_allowed"])
        self.assertFalse(handoff["platform_execution_allowed"])
        self.assertFalse(handoff["studio_execution_allowed"])
        self.assertFalse(handoff["runtime_execution_performed"])
        self.assertFalse(handoff["platform_execution_performed"])
        self.assertEqual(handoff["package_ready_required_check_count"], 3)
        self.assertEqual(handoff["package_blocked_required_check_count"], 0)
        self.assertEqual(
            set(handoff["required_package_checks"]),
            set(adapter.PMB_REQUIRED_PACKAGE_CHECKS),
        )
        self.assertEqual(
            [slot["slot_id"] for slot in handoff["validation_slots"]],
            [contract["slot_id"] for contract in adapter.PMB_VALIDATION_SLOT_CONTRACTS],
        )
        self.assertTrue(
            all(slot["status"] == "ready" for slot in handoff["validation_slots"])
        )
        self.assertTrue(
            all(slot["execution_started"] is False for slot in handoff["validation_slots"])
        )

        validation = adapter.validate_projected_motion_breath_validation_handoff(handoff)
        self.assertEqual(validation["$schema"], adapter.PMB_VALIDATION_HANDOFF_VALIDATION_SCHEMA)
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_projected_motion_breath_validation_handoff_blocks_unready_authoring(self) -> None:
        package_evidence = ready_pmb_package_evidence_intake()
        authoring_review = ready_pmb_authoring_review()
        authoring_review["status"] = "blocked"
        authoring_review["issue_code"] = "studio.issue.package_evidence_required_check_missing"
        authoring_review["package_ready_required_check_count"] = 2
        authoring_review["package_blocked_required_check_count"] = 1

        handoff = adapter.build_projected_motion_breath_validation_handoff(
            authoring_review,
            package_evidence,
        )

        self.assertEqual(handoff["status"], "blocked")
        self.assertEqual(
            handoff["issue_code"],
            "studio.issue.package_evidence_required_check_missing",
        )
        self.assertEqual(handoff["ready_validation_slot_count"], 0)
        self.assertEqual(
            handoff["blocked_validation_slot_count"],
            len(adapter.PMB_VALIDATION_SLOT_CONTRACTS),
        )
        self.assertTrue(
            all(slot["status"] == "blocked" for slot in handoff["validation_slots"])
        )
        self.assertEqual(
            adapter.validate_projected_motion_breath_validation_handoff(handoff)["status"],
            "pass",
        )

    def test_projected_motion_breath_validation_handoff_accepts_source_adapter_selection(
        self,
    ) -> None:
        source_selection = ready_pmb_source_adapter_selection_review()

        handoff = adapter.build_projected_motion_breath_validation_handoff(
            ready_pmb_authoring_review(),
            ready_pmb_package_evidence_intake(),
            Path("fixtures/projected-motion-breath/authoring-review.json"),
            Path("fixtures/projected-motion-breath/package-evidence-intake.json"),
            source_selection,
            Path("fixtures/projected-motion-breath/source-adapter-selection.json"),
        )

        self.assertEqual(handoff["status"], "ready")
        self.assertTrue(handoff["source_adapter_selection_present"])
        self.assertEqual(
            handoff["source_adapter_selection_schema"],
            adapter.STUDIO_PMB_SOURCE_ADAPTER_SELECTION_REVIEW_SCHEMA,
        )
        self.assertEqual(
            handoff["selected_adapter_id"],
            "adapter.projected_motion_breath.external_patch_stream_bridge_shape",
        )
        self.assertEqual(handoff["selected_input_kind"], "vector3")
        self.assertEqual(handoff["selected_output_stream_id"], "stream.motion.vector3")
        self.assertEqual(
            handoff["validation_slot_count"],
            len(adapter.PMB_VALIDATION_SLOT_CONTRACTS) + 1,
        )
        self.assertIn(
            "hostess.pmb.review_source_adapter_selection",
            {slot["slot_id"] for slot in handoff["validation_slots"]},
        )
        self.assertTrue(
            all(slot["execution_started"] is False for slot in handoff["validation_slots"])
        )

        validation = adapter.validate_projected_motion_breath_validation_handoff(handoff)
        self.assertEqual(validation["status"], "pass")

    def test_projected_motion_breath_validation_handoff_blocks_bad_source_adapter_selection(
        self,
    ) -> None:
        source_selection = ready_pmb_source_adapter_selection_review()
        source_selection["selected_output_stream_id"] = "stream.motion.object_pose"

        handoff = adapter.build_projected_motion_breath_validation_handoff(
            ready_pmb_authoring_review(),
            ready_pmb_package_evidence_intake(),
            source_adapter_selection_review=source_selection,
        )

        self.assertEqual(handoff["status"], "blocked")
        self.assertEqual(
            handoff["issue_code"],
            "hostess.issue.projected_motion_breath_source_adapter_selection_stream",
        )
        self.assertEqual(
            handoff["blocked_validation_slot_count"],
            len(adapter.PMB_VALIDATION_SLOT_CONTRACTS) + 1,
        )
        self.assertEqual(
            adapter.validate_projected_motion_breath_validation_handoff(handoff)["status"],
            "pass",
        )

    def test_projected_motion_breath_validation_handoff_validation_rejects_execution_or_slot_drift(
        self,
    ) -> None:
        handoff = adapter.build_projected_motion_breath_validation_handoff(
            ready_pmb_authoring_review(),
            ready_pmb_package_evidence_intake(),
        )

        started = copy.deepcopy(handoff)
        started["launch_started"] = True
        started_report = adapter.validate_projected_motion_breath_validation_handoff(started)
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.projected_motion_breath_validation_handoff_execution_started",
        )

        slot_drift = copy.deepcopy(handoff)
        slot_drift["validation_slots"][0]["route_kind"] = "hostess.pmb.drifted_route"
        slot_report = adapter.validate_projected_motion_breath_validation_handoff(slot_drift)
        self.assertEqual(slot_report["status"], "fail")
        self.assertEqual(
            slot_report["issue_code"],
            "hostess.issue.projected_motion_breath_validation_handoff_slot_drift",
        )

    def test_builds_projected_motion_breath_replay_validation_receipt_without_execution(
        self,
    ) -> None:
        receipt = adapter.build_projected_motion_breath_replay_validation_receipt(
            ready_pmb_validation_handoff()
        )

        self.assertEqual(receipt["$schema"], adapter.PMB_REPLAY_VALIDATION_RECEIPT_SCHEMA)
        self.assertEqual(receipt["status"], "validated")
        self.assertIsNone(receipt["issue_code"])
        self.assertEqual(receipt["receipt_owner"], "rusty.hostess")
        self.assertEqual(receipt["runtime_authority"], "rusty.manifold")
        self.assertEqual(receipt["platform_validation_authority"], "rusty.hostess")
        self.assertEqual(receipt["target_package_id"], adapter.PMB_TARGET_PACKAGE_ID)
        self.assertEqual(receipt["target_module_id"], adapter.PMB_TARGET_MODULE_ID)
        self.assertEqual(receipt["proposed_command_id"], adapter.PMB_PROPOSED_COMMAND_ID)
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(receipt[flag], flag)
        self.assertFalse(receipt["replay_execution_started"])
        self.assertFalse(receipt["fixture_payloads_copied"])
        self.assertFalse(receipt["processor_runtime_started"])
        self.assertEqual(
            receipt["replay_descriptor_count"],
            len(adapter.PMB_REPLAY_DESCRIPTOR_CONTRACTS),
        )
        self.assertEqual(
            receipt["validated_replay_descriptor_count"],
            len(adapter.PMB_REPLAY_DESCRIPTOR_CONTRACTS),
        )
        self.assertEqual(receipt["rejected_replay_descriptor_count"], 0)
        self.assertTrue(
            all(
                descriptor["descriptor_status"] == "validated"
                for descriptor in receipt["replay_descriptors"]
            )
        )
        self.assertTrue(
            all(
                descriptor["fixture_payload_copied"] is False
                for descriptor in receipt["replay_descriptors"]
            )
        )

        validation = adapter.validate_projected_motion_breath_replay_validation_receipt(
            receipt
        )
        self.assertEqual(
            validation["$schema"],
            adapter.PMB_REPLAY_VALIDATION_RECEIPT_VALIDATION_SCHEMA,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_projected_motion_breath_replay_validation_receipt_rejects_blocked_handoff(
        self,
    ) -> None:
        authoring_review = ready_pmb_authoring_review()
        authoring_review["status"] = "blocked"
        authoring_review["issue_code"] = "studio.issue.package_evidence_required_check_missing"
        authoring_review["package_ready_required_check_count"] = 2
        authoring_review["package_blocked_required_check_count"] = 1
        handoff = adapter.build_projected_motion_breath_validation_handoff(
            authoring_review,
            ready_pmb_package_evidence_intake(),
        )

        receipt = adapter.build_projected_motion_breath_replay_validation_receipt(handoff)

        self.assertEqual(receipt["status"], "rejected")
        self.assertEqual(
            receipt["issue_code"],
            "studio.issue.package_evidence_required_check_missing",
        )
        self.assertEqual(receipt["validated_replay_descriptor_count"], 0)
        self.assertEqual(
            receipt["rejected_replay_descriptor_count"],
            len(adapter.PMB_REPLAY_DESCRIPTOR_CONTRACTS),
        )
        self.assertTrue(
            all(
                descriptor["descriptor_status"] == "rejected"
                for descriptor in receipt["replay_descriptors"]
            )
        )
        self.assertEqual(
            adapter.validate_projected_motion_breath_replay_validation_receipt(receipt)[
                "status"
            ],
            "pass",
        )

    def test_projected_motion_breath_replay_validation_receipt_validation_rejects_execution_or_descriptor_drift(
        self,
    ) -> None:
        receipt = adapter.build_projected_motion_breath_replay_validation_receipt(
            ready_pmb_validation_handoff()
        )

        started = copy.deepcopy(receipt)
        started["replay_execution_started"] = True
        started_report = adapter.validate_projected_motion_breath_replay_validation_receipt(
            started
        )
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.projected_motion_breath_replay_validation_receipt_execution_started",
        )

        descriptor_drift = copy.deepcopy(receipt)
        descriptor_drift["replay_descriptors"][0]["case_id"] = "case.projected_motion_breath.drift"
        descriptor_report = (
            adapter.validate_projected_motion_breath_replay_validation_receipt(
                descriptor_drift
            )
        )
        self.assertEqual(descriptor_report["status"], "fail")
        self.assertEqual(
            descriptor_report["issue_code"],
            "hostess.issue.projected_motion_breath_replay_validation_receipt_descriptor_drift",
        )

    def test_builds_operator_release_readiness_bundle_without_execution(self) -> None:
        evidence_review, replay_receipt = ready_operator_release_inputs()

        bundle = adapter.build_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
        )

        self.assertEqual(bundle["$schema"], adapter.OPERATOR_RELEASE_READINESS_BUNDLE_SCHEMA)
        self.assertEqual(bundle["status"], "ready")
        self.assertIsNone(bundle["issue_code"])
        self.assertEqual(
            bundle["execution_policy"],
            adapter.OPERATOR_RELEASE_READINESS_BUNDLE_POLICY,
        )
        self.assertEqual(bundle["bundle_owner"], "rusty.hostess")
        self.assertEqual(bundle["runtime_authority"], "rusty.manifold")
        self.assertEqual(bundle["command_session_authority"], "rusty.manifold")
        self.assertEqual(bundle["studio_role"], "authoring.export_planning")
        self.assertTrue(bundle["operator_release_ready"])
        self.assertFalse(bundle["operator_started"])
        self.assertFalse(bundle["host_shell_started"])
        self.assertFalse(bundle["schema_path_execution_allowed"])
        self.assertFalse(bundle["platform_execution_allowed"])
        self.assertFalse(bundle["studio_execution_allowed"])
        self.assertFalse(bundle["execution_performed"])
        self.assertFalse(bundle["runtime_execution_performed"])
        self.assertFalse(bundle["platform_execution_performed"])
        self.assertFalse(bundle["apk_build_started"])
        self.assertFalse(bundle["replay_execution_started"])
        self.assertFalse(bundle["schema_artifact_payloads_copied"])
        self.assertFalse(bundle["release_payloads_copied"])
        self.assertEqual(
            bundle["ready_schema_artifact_count"],
            len(adapter.OPERATOR_RELEASE_ARTIFACT_CONTRACTS),
        )
        self.assertEqual(
            bundle["ready_host_shell_readiness_target_count"],
            len(adapter.OPERATOR_RELEASE_HOST_SHELL_TARGET_CONTRACTS),
        )
        self.assertEqual(
            {row["source_role"] for row in bundle["schema_artifacts"]},
            {
                "platform_smoke_evidence_review",
                "projected_motion_breath_replay_validation_receipt",
            },
        )
        self.assertTrue(
            all(
                row["artifact_status"] == "ready"
                and row["schema_artifact_payload_copied"] is False
                and row["release_payload_copied"] is False
                and row["platform_execution_performed"] is False
                for row in bundle["schema_artifacts"]
            )
        )
        self.assertEqual(
            {target["host_shell_kind"] for target in bundle["host_shell_readiness_targets"]},
            {"hostess.t", "dedicated_quest_host_shell"},
        )
        self.assertTrue(
            all(
                target["target_status"] == "ready"
                and target["host_shell_started"] is False
                and target["operator_started"] is False
                and target["platform_execution_performed"] is False
                for target in bundle["host_shell_readiness_targets"]
            )
        )

        validation = adapter.validate_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
            bundle,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["platform_execution_performed"])

    def test_operator_release_readiness_bundle_preserves_pmb_shell_handoff_gate(
        self,
    ) -> None:
        evidence_review, replay_receipt = ready_pmb_operator_release_inputs()

        bundle = adapter.build_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
        )

        self.assertEqual(bundle["status"], "ready")
        self.assertTrue(bundle["operator_release_ready"])
        self.assertTrue(bundle["pmb_shell_handoff_review_required"])
        self.assertTrue(bundle["pmb_shell_handoff_review_ready"])
        self.assertEqual(
            bundle["source_pmb_shell_handoff_review_schema"],
            evidence_review["source_pmb_shell_handoff_review_schema"],
        )
        self.assertEqual(bundle["source_pmb_runtime_authority"], "rusty.manifold")
        self.assertEqual(bundle["source_pmb_authoring_authority"], "rusty.studio")
        self.assertEqual(
            bundle["source_pmb_platform_validation_authority"],
            "rusty.hostess",
        )
        self.assertFalse(bundle["source_pmb_runtime_execution_performed"])
        self.assertFalse(bundle["source_pmb_platform_execution_performed"])

        platform_artifact = next(
            row
            for row in bundle["schema_artifacts"]
            if row["source_role"] == "platform_smoke_evidence_review"
        )
        self.assertEqual(platform_artifact["artifact_status"], adapter.READY_STATUS)
        self.assertTrue(platform_artifact["pmb_shell_handoff_review_required"])
        self.assertTrue(platform_artifact["pmb_shell_handoff_review_ready"])
        self.assertEqual(
            platform_artifact["source_pmb_shell_handoff_review_schema"],
            evidence_review["source_pmb_shell_handoff_review_schema"],
        )
        self.assertTrue(
            adapter.pmb_shell_handoff_readiness_result_summary_valid(platform_artifact)
        )

        validation = adapter.validate_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
            bundle,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(validation["pmb_shell_handoff_review_required"])
        self.assertTrue(validation["pmb_shell_handoff_review_ready"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_operator_release_readiness_bundle_blocks_unready_replay_receipt(
        self,
    ) -> None:
        evidence_review, replay_receipt = ready_operator_release_inputs()
        replay_receipt["replay_execution_started"] = True

        bundle = adapter.build_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
        )

        self.assertEqual(bundle["status"], "blocked")
        self.assertEqual(bundle["scorecard_status"], "fail")
        self.assertFalse(bundle["operator_release_ready"])
        self.assertEqual(bundle["blocked_schema_artifact_count"], 1)
        self.assertEqual(
            bundle["issue_code"],
            "hostess.issue.projected_motion_breath_replay_validation_receipt_execution_started",
        )
        self.assertEqual(
            adapter.validate_operator_release_readiness_bundle(
                evidence_review,
                replay_receipt,
                bundle,
            )["status"],
            "pass",
        )

    def test_operator_release_readiness_bundle_validation_rejects_execution_or_artifact_drift(
        self,
    ) -> None:
        evidence_review, replay_receipt = ready_operator_release_inputs()
        bundle = adapter.build_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
        )

        started = copy.deepcopy(bundle)
        started["install_started"] = True
        started_report = adapter.validate_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
            started,
        )
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.operator_release_readiness_bundle_execution_started",
        )

        artifact_drift = copy.deepcopy(bundle)
        artifact_drift["schema_artifacts"][0]["owner"] = "rusty.studio"
        artifact_report = adapter.validate_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
            artifact_drift,
        )
        self.assertEqual(artifact_report["status"], "fail")
        self.assertEqual(
            artifact_report["issue_code"],
            "hostess.issue.operator_release_readiness_bundle_artifact_drift",
        )

        host_shell_drift = copy.deepcopy(bundle)
        host_shell_drift["host_shell_readiness_targets"][0]["host_shell_started"] = True
        host_shell_report = adapter.validate_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
            host_shell_drift,
        )
        self.assertEqual(host_shell_report["status"], "fail")
        self.assertEqual(
            host_shell_report["issue_code"],
            "hostess.issue.operator_release_readiness_bundle_host_shell_drift",
        )

    def test_operator_release_readiness_bundle_validation_rejects_pmb_gate_drift(
        self,
    ) -> None:
        evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
        bundle = adapter.build_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
        )

        pmb_drift = copy.deepcopy(bundle)
        pmb_drift["pmb_shell_handoff_review_ready"] = False
        pmb_report = adapter.validate_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
            pmb_drift,
        )
        self.assertEqual(pmb_report["status"], "fail")
        self.assertEqual(
            pmb_report["issue_code"],
            "hostess.issue.operator_release_readiness_bundle_pmb_shell_handoff_review_drift",
        )


if __name__ == "__main__":
    unittest.main()
