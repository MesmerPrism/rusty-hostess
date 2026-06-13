"""Hostess staging handoff, file-plan, file-copy, payload manifest, and downstream shell tests."""

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


class StudioStagingHostessHandoffTests(unittest.TestCase):
    def test_hostess_accepts_staging_handoff_after_release_readiness_without_copying(
        self,
    ) -> None:
        evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
        release_bundle = adapter.build_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
        )
        staging_handoff = ready_studio_hostess_staging_handoff()
        acceptance_manifest = ready_studio_hostess_staging_acceptance_manifest()

        receipt = adapter.build_hostess_staging_handoff_acceptance_receipt(
            release_bundle,
            staging_handoff,
            acceptance_manifest,
        )

        self.assertEqual(
            receipt["$schema"],
            adapter.HOSTESS_STAGING_HANDOFF_ACCEPTANCE_RECEIPT_SCHEMA,
        )
        self.assertEqual(receipt["status"], adapter.ACCEPTED_STATUS)
        self.assertIsNone(receipt["issue_code"])
        self.assertTrue(receipt["staging_handoff_accepted"])
        self.assertTrue(receipt["stage_generated_shells_request_accepted"])
        self.assertFalse(receipt["stage_generated_shells_started"])
        self.assertFalse(receipt["copy_started"])
        self.assertFalse(receipt["stage_started"])
        self.assertFalse(receipt["install_started"])
        self.assertFalse(receipt["launch_started"])
        self.assertFalse(receipt["staging_payloads_copied"])
        self.assertEqual(receipt["receipt_owner"], "rusty.hostess")
        self.assertEqual(receipt["command_session_authority"], "rusty.manifold")
        self.assertEqual(receipt["requester_role"], "rusty.studio")
        self.assertTrue(receipt["pmb_shell_handoff_review_required"])
        self.assertTrue(receipt["pmb_shell_handoff_review_ready"])
        self.assertEqual(
            receipt["source_pmb_shell_handoff_review_schema"],
            release_bundle["source_pmb_shell_handoff_review_schema"],
        )
        self.assertEqual(receipt["request_count"], staging_handoff["request_count"])
        self.assertEqual(receipt["accepted_request_count"], staging_handoff["request_count"])
        self.assertEqual(
            receipt["instruction_count"],
            staging_handoff["instruction_count"],
        )
        self.assertEqual(
            receipt["accepted_instruction_count"],
            staging_handoff["instruction_count"],
        )
        self.assertTrue(
            any(
                row["route_kinds"]
                and "hostess.stage.generated_shells" in row["route_kinds"]
                for row in receipt["accepted_requests"]
            )
        )

        validation = adapter.validate_hostess_staging_handoff_acceptance_receipt(
            release_bundle,
            staging_handoff,
            acceptance_manifest,
            receipt,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(validation["pmb_shell_handoff_review_required"])
        self.assertTrue(validation["pmb_shell_handoff_review_ready"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_hostess_staging_handoff_acceptance_rejects_request_and_pmb_drift(
        self,
    ) -> None:
        evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
        release_bundle = adapter.build_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
        )
        staging_handoff = ready_studio_hostess_staging_handoff()
        acceptance_manifest = ready_studio_hostess_staging_acceptance_manifest()
        receipt = adapter.build_hostess_staging_handoff_acceptance_receipt(
            release_bundle,
            staging_handoff,
            acceptance_manifest,
        )

        request_drift = copy.deepcopy(receipt)
        request_drift["accepted_requests"][0]["route_kinds"] = [
            "legacy.rusty_xr.stage.generated_shells"
        ]
        request_report = adapter.validate_hostess_staging_handoff_acceptance_receipt(
            release_bundle,
            staging_handoff,
            acceptance_manifest,
            request_drift,
        )
        self.assertEqual(request_report["status"], "fail")
        self.assertEqual(
            request_report["issue_code"],
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_request_drift",
        )

        pmb_drift = copy.deepcopy(receipt)
        pmb_drift["pmb_shell_handoff_review_ready"] = False
        pmb_report = adapter.validate_hostess_staging_handoff_acceptance_receipt(
            release_bundle,
            staging_handoff,
            acceptance_manifest,
            pmb_drift,
        )
        self.assertEqual(pmb_report["status"], "fail")
        self.assertEqual(
            pmb_report["issue_code"],
            "hostess.issue.hostess_staging_handoff_acceptance_receipt_pmb_shell_handoff_review_drift",
        )

    def test_hostess_reviews_staging_file_plan_after_handoff_acceptance_without_copying(
        self,
    ) -> None:
        evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
        release_bundle = adapter.build_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
        )
        staging_handoff = ready_studio_hostess_staging_handoff()
        acceptance_manifest = ready_studio_hostess_staging_acceptance_manifest()
        acceptance_receipt = adapter.build_hostess_staging_handoff_acceptance_receipt(
            release_bundle,
            staging_handoff,
            acceptance_manifest,
        )
        file_plan = ready_studio_hostess_staging_file_plan()

        receipt = adapter.build_hostess_staging_file_plan_receipt(
            acceptance_receipt,
            file_plan,
            staging_root="public-test-root/hostess-clean-staging",
        )

        self.assertEqual(
            receipt["$schema"],
            adapter.HOSTESS_STAGING_FILE_PLAN_RECEIPT_SCHEMA,
        )
        self.assertEqual(receipt["status"], adapter.ACCEPTED_STATUS)
        self.assertIsNone(receipt["issue_code"])
        self.assertTrue(receipt["staging_file_plan_reviewed"])
        self.assertTrue(receipt["copy_plan_ready"])
        self.assertFalse(receipt["copy_started"])
        self.assertFalse(receipt["stage_started"])
        self.assertFalse(receipt["install_started"])
        self.assertFalse(receipt["launch_started"])
        self.assertFalse(receipt["staging_payloads_copied"])
        self.assertFalse(receipt["file_copy_performed"])
        self.assertEqual(receipt["receipt_owner"], "rusty.hostess")
        self.assertEqual(receipt["command_session_authority"], "rusty.manifold")
        self.assertEqual(receipt["requester_role"], "rusty.studio")
        self.assertTrue(receipt["pmb_shell_handoff_review_required"])
        self.assertTrue(receipt["pmb_shell_handoff_review_ready"])
        self.assertEqual(receipt["request_count"], file_plan["request_count"])
        self.assertEqual(
            receipt["accepted_request_count"],
            file_plan["request_count"],
        )
        self.assertEqual(receipt["file_count"], file_plan["planned_file_count"])
        self.assertEqual(
            receipt["accepted_file_count"],
            file_plan["planned_file_count"],
        )
        self.assertTrue(
            all(row["destination_under_request_root"] for row in receipt["staging_files"])
        )
        self.assertTrue(
            all(
                str(row["destination_absolute_path"]).replace("\\", "/").startswith(
                    "public-test-root/hostess-clean-staging"
                )
                for row in receipt["staging_files"]
            )
        )

        validation = adapter.validate_hostess_staging_file_plan_receipt(
            acceptance_receipt,
            file_plan,
            receipt,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(validation["pmb_shell_handoff_review_required"])
        self.assertTrue(validation["pmb_shell_handoff_review_ready"])
        self.assertFalse(validation["copy_started"])
        self.assertFalse(validation["staging_payloads_copied"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_hostess_staging_file_plan_receipt_rejects_file_and_pmb_drift(
        self,
    ) -> None:
        evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
        release_bundle = adapter.build_operator_release_readiness_bundle(
            evidence_review,
            replay_receipt,
        )
        staging_handoff = ready_studio_hostess_staging_handoff()
        acceptance_manifest = ready_studio_hostess_staging_acceptance_manifest()
        acceptance_receipt = adapter.build_hostess_staging_handoff_acceptance_receipt(
            release_bundle,
            staging_handoff,
            acceptance_manifest,
        )
        file_plan = ready_studio_hostess_staging_file_plan()
        receipt = adapter.build_hostess_staging_file_plan_receipt(
            acceptance_receipt,
            file_plan,
        )

        file_drift = copy.deepcopy(receipt)
        file_drift["staging_files"][0]["destination_path"] = (
            "legacy/rusty-xr/generated-shell.json"
        )
        file_report = adapter.validate_hostess_staging_file_plan_receipt(
            acceptance_receipt,
            file_plan,
            file_drift,
        )
        self.assertEqual(file_report["status"], "fail")
        self.assertEqual(
            file_report["issue_code"],
            "hostess.issue.hostess_staging_file_plan_receipt_file_drift",
        )

        pmb_drift = copy.deepcopy(receipt)
        pmb_drift["pmb_shell_handoff_review_ready"] = False
        pmb_report = adapter.validate_hostess_staging_file_plan_receipt(
            acceptance_receipt,
            file_plan,
            pmb_drift,
        )
        self.assertEqual(pmb_report["status"], "fail")
        self.assertEqual(
            pmb_report["issue_code"],
            "hostess.issue.hostess_staging_file_plan_receipt_pmb_shell_handoff_review_drift",
        )

    def test_hostess_copies_staging_file_plan_without_launching_runtime(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
            release_bundle = adapter.build_operator_release_readiness_bundle(
                evidence_review,
                replay_receipt,
            )
            staging_handoff = ready_studio_hostess_staging_handoff()
            acceptance_manifest = ready_studio_hostess_staging_acceptance_manifest()
            acceptance_receipt = (
                adapter.build_hostess_staging_handoff_acceptance_receipt(
                    release_bundle,
                    staging_handoff,
                    acceptance_manifest,
                )
            )
            file_plan = materialized_studio_hostess_staging_file_plan(
                root / "source"
            )
            file_plan_receipt = adapter.build_hostess_staging_file_plan_receipt(
                acceptance_receipt,
                file_plan,
                staging_root=str(root / "clean-hostess-staging"),
            )

            copy_receipt = adapter.build_hostess_staging_file_copy_receipt(
                file_plan_receipt,
                file_plan,
            )

            self.assertEqual(
                copy_receipt["$schema"],
                adapter.HOSTESS_STAGING_FILE_COPY_RECEIPT_SCHEMA,
            )
            self.assertEqual(copy_receipt["status"], adapter.COMPLETED_STATUS)
            self.assertIsNone(copy_receipt["issue_code"])
            self.assertTrue(copy_receipt["file_copy_completed"])
            self.assertTrue(copy_receipt["copy_started"])
            self.assertTrue(copy_receipt["stage_started"])
            self.assertTrue(copy_receipt["staging_payloads_copied"])
            self.assertTrue(copy_receipt["schema_artifact_payloads_copied"])
            self.assertFalse(copy_receipt["install_started"])
            self.assertFalse(copy_receipt["launch_started"])
            self.assertFalse(copy_receipt["runtime_execution_performed"])
            self.assertFalse(copy_receipt["platform_execution_performed"])
            self.assertFalse(copy_receipt["command_session_started"])
            self.assertEqual(
                copy_receipt["copied_file_count"],
                file_plan_receipt["accepted_file_count"],
            )
            self.assertTrue(
                all(row["destination_exists_after_copy"] for row in copy_receipt["copy_rows"])
            )
            self.assertTrue(
                all(
                    Path(row["resolved_destination_path"]).exists()
                    for row in copy_receipt["copy_rows"]
                )
            )

            validation = adapter.validate_hostess_staging_file_copy_receipt(
                file_plan_receipt,
                file_plan,
                copy_receipt,
            )
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["copy_started"])
            self.assertTrue(validation["staging_payloads_copied"])
            self.assertFalse(validation["runtime_execution_performed"])
            self.assertFalse(validation["platform_execution_performed"])

    def test_hostess_staging_file_copy_rejects_missing_source_or_unsafe_destination(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
            release_bundle = adapter.build_operator_release_readiness_bundle(
                evidence_review,
                replay_receipt,
            )
            acceptance_receipt = (
                adapter.build_hostess_staging_handoff_acceptance_receipt(
                    release_bundle,
                    ready_studio_hostess_staging_handoff(),
                    ready_studio_hostess_staging_acceptance_manifest(),
                )
            )
            file_plan = materialized_studio_hostess_staging_file_plan(
                root / "source"
            )
            file_plan_receipt = adapter.build_hostess_staging_file_plan_receipt(
                acceptance_receipt,
                file_plan,
                staging_root=str(root / "clean-hostess-staging"),
            )

            missing_source_plan = copy.deepcopy(file_plan)
            missing_source_plan["requests"][0]["planned_files"][0]["source_path"] = str(
                root / "missing-source-dir"
            )
            missing_source_receipt = adapter.build_hostess_staging_file_plan_receipt(
                acceptance_receipt,
                missing_source_plan,
                staging_root=str(root / "missing-source-staging"),
            )
            missing_receipt = adapter.build_hostess_staging_file_copy_receipt(
                missing_source_receipt,
                missing_source_plan,
            )
            self.assertEqual(missing_receipt["status"], adapter.REJECTED_STATUS)
            self.assertEqual(
                missing_receipt["issue_code"],
                "hostess.issue.hostess_staging_file_copy_source_missing",
            )
            self.assertFalse(missing_receipt["copy_started"])
            self.assertFalse(missing_receipt["staging_payloads_copied"])

            unsafe_receipt_source = copy.deepcopy(file_plan_receipt)
            unsafe_receipt_source["staging_files"][0]["destination_path"] = (
                "../outside-staging"
            )
            unsafe_receipt = adapter.build_hostess_staging_file_copy_receipt(
                unsafe_receipt_source,
                file_plan,
            )
            self.assertEqual(unsafe_receipt["status"], adapter.REJECTED_STATUS)
            self.assertEqual(
                unsafe_receipt["issue_code"],
                "hostess.issue.hostess_staging_file_copy_destination_unsafe",
            )
            unsafe_validation = adapter.validate_hostess_staging_file_copy_receipt(
                unsafe_receipt_source,
                file_plan,
                unsafe_receipt,
            )
            self.assertEqual(unsafe_validation["status"], "pass")

    def test_hostess_reviews_staged_payloads_for_downstream_shell_selection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
            release_bundle = adapter.build_operator_release_readiness_bundle(
                evidence_review,
                replay_receipt,
            )
            acceptance_receipt = (
                adapter.build_hostess_staging_handoff_acceptance_receipt(
                    release_bundle,
                    ready_studio_hostess_staging_handoff(),
                    ready_studio_hostess_staging_acceptance_manifest(),
                )
            )
            file_plan = materialized_studio_hostess_staging_file_plan(
                root / "source"
            )
            file_plan_receipt = adapter.build_hostess_staging_file_plan_receipt(
                acceptance_receipt,
                file_plan,
                staging_root=str(root / "clean-hostess-staging"),
            )
            copy_receipt = adapter.build_hostess_staging_file_copy_receipt(
                file_plan_receipt,
                file_plan,
            )

            manifest = adapter.build_hostess_staged_payload_manifest_receipt(
                copy_receipt,
            )

            self.assertEqual(
                manifest["$schema"],
                adapter.HOSTESS_STAGED_PAYLOAD_MANIFEST_RECEIPT_SCHEMA,
            )
            self.assertEqual(manifest["status"], adapter.REVIEWED_STATUS)
            self.assertIsNone(manifest["issue_code"])
            self.assertTrue(manifest["payload_manifest_reviewed"])
            self.assertTrue(manifest["staged_payloads_available"])
            self.assertTrue(manifest["downstream_shell_selection_ready"])
            self.assertTrue(manifest["makepad_shell_selection_ready"])
            self.assertFalse(manifest["legacy_reference_dependency_used"])
            self.assertFalse(manifest["downstream_shell_runtime_started"])
            self.assertFalse(manifest["copy_started"])
            self.assertFalse(manifest["install_started"])
            self.assertFalse(manifest["launch_started"])
            self.assertFalse(manifest["runtime_execution_performed"])
            self.assertFalse(manifest["platform_execution_performed"])
            self.assertFalse(manifest["command_session_started"])
            self.assertEqual(manifest["payload_count"], copy_receipt["file_count"])
            self.assertEqual(
                manifest["reviewed_payload_count"],
                copy_receipt["copied_file_count"],
            )
            self.assertGreater(manifest["target_descriptor_payload_count"], 0)
            self.assertTrue(
                any(
                    row["artifact_kind"] == "shell_descriptor"
                    and row["downstream_shell_descriptor_ready"]
                    and row["makepad_shell_selection_candidate"]
                    for row in manifest["payload_rows"]
                )
            )

            validation = adapter.validate_hostess_staged_payload_manifest_receipt(
                copy_receipt,
                manifest,
            )
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["downstream_shell_selection_ready"])
            self.assertTrue(validation["makepad_shell_selection_ready"])
            self.assertFalse(validation["runtime_execution_performed"])
            self.assertFalse(validation["platform_execution_performed"])

    def test_hostess_staged_payload_manifest_rejects_descriptor_runtime_and_pmb_drift(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
            release_bundle = adapter.build_operator_release_readiness_bundle(
                evidence_review,
                replay_receipt,
            )
            acceptance_receipt = (
                adapter.build_hostess_staging_handoff_acceptance_receipt(
                    release_bundle,
                    ready_studio_hostess_staging_handoff(),
                    ready_studio_hostess_staging_acceptance_manifest(),
                )
            )
            file_plan = materialized_studio_hostess_staging_file_plan(
                root / "source"
            )
            file_plan_receipt = adapter.build_hostess_staging_file_plan_receipt(
                acceptance_receipt,
                file_plan,
                staging_root=str(root / "clean-hostess-staging"),
            )
            copy_receipt = adapter.build_hostess_staging_file_copy_receipt(
                file_plan_receipt,
                file_plan,
            )
            manifest = adapter.build_hostess_staged_payload_manifest_receipt(
                copy_receipt,
            )

            descriptor_drift = copy.deepcopy(manifest)
            descriptor_row = next(
                row
                for row in descriptor_drift["payload_rows"]
                if row["artifact_kind"] == "shell_descriptor"
                and row["target_kind"] is not None
            )
            descriptor_row["downstream_shell_descriptor_ready"] = False
            descriptor_drift["makepad_shell_selection_ready"] = False
            descriptor_report = adapter.validate_hostess_staged_payload_manifest_receipt(
                copy_receipt,
                descriptor_drift,
            )
            self.assertEqual(descriptor_report["status"], "fail")
            self.assertEqual(
                descriptor_report["issue_code"],
                "hostess.issue.hostess_staged_payload_manifest_receipt_downstream_selection",
            )

            runtime_drift = copy.deepcopy(manifest)
            runtime_drift["launch_started"] = True
            runtime_report = adapter.validate_hostess_staged_payload_manifest_receipt(
                copy_receipt,
                runtime_drift,
            )
            self.assertEqual(runtime_report["status"], "fail")
            self.assertEqual(
                runtime_report["issue_code"],
                "hostess.issue.hostess_staged_payload_manifest_receipt_runtime_started",
            )

            pmb_drift = copy.deepcopy(manifest)
            pmb_drift["pmb_shell_handoff_review_ready"] = False
            pmb_report = adapter.validate_hostess_staged_payload_manifest_receipt(
                copy_receipt,
                pmb_drift,
            )
            self.assertEqual(pmb_report["status"], "fail")
            self.assertEqual(
                pmb_report["issue_code"],
                "hostess.issue.hostess_staged_payload_manifest_receipt_pmb_shell_handoff_review_drift",
            )

    def test_hostess_selects_downstream_manifold_shell_handoff_without_launching(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = hostess_staged_payload_manifest_for_test(root)

            selection = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="desktop",
                graph_id="studio.graph.synthetic",
                consumer_id="rusty-studio-desktop-shell",
            )

            self.assertEqual(
                selection["$schema"],
                adapter.HOSTESS_DOWNSTREAM_SHELL_SELECTION_RECEIPT_SCHEMA,
            )
            self.assertEqual(selection["status"], adapter.SELECTED_STATUS)
            self.assertIsNone(selection["issue_code"])
            self.assertTrue(selection["downstream_shell_selection_ready"])
            self.assertTrue(selection["downstream_shell_descriptor_selected"])
            self.assertTrue(selection["makepad_shell_selection_ready"])
            self.assertTrue(selection["manifold_shell_handoff_selected"])
            self.assertFalse(selection["makepad_shell_descriptor_selected"])
            self.assertEqual(
                selection["selected_artifact_kind"],
                "manifold_shell_handoff",
            )
            self.assertEqual(selection["selected_target_kind"], "desktop")
            self.assertEqual(selection["selected_graph_id"], "studio.graph.synthetic")
            self.assertEqual(
                selection["selected_consumer_id"],
                "rusty-studio-desktop-shell",
            )
            self.assertTrue(Path(selection["selected_payload_path"]).exists())
            self.assertFalse(selection["legacy_reference_dependency_used"])
            self.assertFalse(selection["downstream_shell_runtime_started"])
            self.assertFalse(selection["copy_started"])
            self.assertFalse(selection["install_started"])
            self.assertFalse(selection["launch_started"])
            self.assertFalse(selection["runtime_execution_performed"])
            self.assertFalse(selection["platform_execution_performed"])
            self.assertFalse(selection["command_session_started"])
            self.assertEqual(selection["candidate_count"], 2)
            self.assertEqual(selection["matching_candidate_count"], 2)
            self.assertEqual(selection["selected_candidate_count"], 1)

            validation = (
                adapter.validate_hostess_downstream_shell_selection_receipt(
                    manifest,
                    selection,
                )
            )
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["manifold_shell_handoff_selected"])
            self.assertFalse(validation["makepad_shell_descriptor_selected"])
            self.assertFalse(validation["runtime_execution_performed"])
            self.assertFalse(validation["platform_execution_performed"])

    def test_hostess_intakes_manifold_shell_handoff_review_without_launching(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = hostess_staged_payload_manifest_for_test(root)
            selection = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="desktop",
                graph_id="studio.graph.synthetic",
                consumer_id="rusty-studio-desktop-shell",
            )
            selected_handoff = adapter.selected_manifold_shell_handoff_from_selection(
                selection
            )
            manifold_review = ready_manifold_shell_handoff_review_receipt_for_test(
                selected_handoff
            )

            receipt = (
                adapter.build_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    manifold_review,
                    root / "manifold-shell-handoff-review-receipt.json",
                )
            )

            self.assertEqual(
                receipt["$schema"],
                adapter.HOSTESS_MANIFOLD_SHELL_HANDOFF_REVIEW_INTAKE_RECEIPT_SCHEMA,
            )
            self.assertEqual(receipt["status"], adapter.REVIEWED_STATUS)
            self.assertIsNone(receipt["issue_code"])
            self.assertEqual(
                receipt["source_selected_artifact_kind"],
                "manifold_shell_handoff",
            )
            self.assertEqual(
                receipt["selected_handoff_id"],
                selected_handoff["handoff_id"],
            )
            self.assertEqual(
                receipt["manifold_review_id"],
                manifold_review["review_id"],
            )
            self.assertEqual(receipt["manifold_review_status"], adapter.PASS_STATUS)
            self.assertTrue(receipt["manifold_shell_handoff_selected"])
            self.assertFalse(receipt["makepad_shell_descriptor_selected"])
            self.assertTrue(receipt["manifold_shell_handoff_reviewed"])
            self.assertTrue(receipt["manifold_shell_handoff_review_ready"])
            self.assertEqual(receipt["reviewed_stream_count"], 2)
            self.assertEqual(receipt["reviewed_command_count"], 2)
            self.assertEqual(receipt["reviewed_transport_count"], 1)
            self.assertEqual(receipt["reviewed_endpoint_count"], 1)
            self.assertFalse(receipt["legacy_reference_dependency_used"])
            self.assertFalse(receipt["downstream_shell_runtime_started"])
            self.assertFalse(receipt["launch_started"])
            self.assertFalse(receipt["runtime_execution_performed"])
            self.assertFalse(receipt["platform_execution_performed"])
            self.assertFalse(receipt["command_session_started"])
            self.assertEqual(
                receipt["next_required_action"],
                "makepad_consume_manifold_reviewed_shell_handoff_without_launch",
            )

            validation = (
                adapter.validate_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    manifold_review,
                    receipt,
                )
            )
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["manifold_shell_handoff_selected"])
            self.assertTrue(validation["manifold_shell_handoff_review_ready"])
            self.assertFalse(validation["runtime_execution_performed"])
            self.assertFalse(validation["platform_execution_performed"])

    def test_hostess_falls_back_to_downstream_shell_descriptor_without_launching(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = hostess_staged_payload_manifest_for_test(root)
            manifest["payload_rows"] = [
                row
                for row in manifest["payload_rows"]
                if row["artifact_kind"] != "manifold_shell_handoff"
            ]
            reviewed_rows = [
                row
                for row in manifest["payload_rows"]
                if row["payload_review_status"] == adapter.REVIEWED_STATUS
            ]
            manifest["payload_count"] = len(manifest["payload_rows"])
            manifest["reviewed_payload_count"] = len(reviewed_rows)
            manifest["descriptor_payload_count"] = sum(
                1 for row in reviewed_rows if row["artifact_kind"] == "shell_descriptor"
            )
            manifest["downstream_shell_payload_count"] = sum(
                1
                for row in reviewed_rows
                if row["artifact_kind"] == "shell_descriptor"
            )
            manifest["target_descriptor_payload_count"] = sum(
                1
                for row in reviewed_rows
                if row["artifact_kind"] == "shell_descriptor"
                and row["target_kind"] is not None
            )
            manifest["target_manifold_shell_handoff_payload_count"] = 0
            manifest["shared_payload_count"] = sum(
                1 for row in reviewed_rows if row["target_kind"] is None
            )

            selection = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="desktop",
                graph_id="studio.graph.synthetic",
                consumer_id="rusty-studio-desktop-shell",
            )

            self.assertEqual(selection["status"], adapter.SELECTED_STATUS)
            self.assertTrue(selection["downstream_shell_descriptor_selected"])
            self.assertFalse(selection["manifold_shell_handoff_selected"])
            self.assertTrue(selection["makepad_shell_descriptor_selected"])
            self.assertEqual(selection["selected_artifact_kind"], "shell_descriptor")
            self.assertEqual(selection["candidate_count"], 1)
            self.assertEqual(selection["matching_candidate_count"], 1)

            validation = adapter.validate_hostess_downstream_shell_selection_receipt(
                manifest,
                selection,
            )
            self.assertEqual(validation["status"], "pass")
            self.assertFalse(validation["manifold_shell_handoff_selected"])
            self.assertTrue(validation["makepad_shell_descriptor_selected"])

    def test_hostess_downstream_shell_selection_rejects_drift_and_missing_filter(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = hostess_staged_payload_manifest_for_test(root)
            selection = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="desktop",
            )

            legacy_drift = copy.deepcopy(selection)
            legacy_drift["selected_payload_path"] = "legacy/Rusty-XR/shell.json"
            legacy_report = (
                adapter.validate_hostess_downstream_shell_selection_receipt(
                    manifest,
                    legacy_drift,
                )
            )
            self.assertEqual(legacy_report["status"], "fail")
            self.assertEqual(
                legacy_report["issue_code"],
                "hostess.issue.hostess_downstream_shell_selection_receipt_descriptor_drift",
            )

            runtime_drift = copy.deepcopy(selection)
            runtime_drift["launch_started"] = True
            runtime_report = (
                adapter.validate_hostess_downstream_shell_selection_receipt(
                    manifest,
                    runtime_drift,
                )
            )
            self.assertEqual(runtime_report["status"], "fail")
            self.assertEqual(
                runtime_report["issue_code"],
                "hostess.issue.hostess_downstream_shell_selection_receipt_runtime_started",
            )

            pmb_drift = copy.deepcopy(selection)
            pmb_drift["pmb_shell_handoff_review_ready"] = False
            pmb_report = (
                adapter.validate_hostess_downstream_shell_selection_receipt(
                    manifest,
                    pmb_drift,
                )
            )
            self.assertEqual(pmb_report["status"], "fail")
            self.assertEqual(
                pmb_report["issue_code"],
                "hostess.issue.hostess_downstream_shell_selection_receipt_pmb_shell_handoff_review_drift",
            )

            missing = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="quest",
            )
            self.assertEqual(missing["status"], adapter.REJECTED_STATUS)
            self.assertEqual(
                missing["issue_code"],
                "hostess.issue.hostess_downstream_shell_selection_no_candidate",
            )
            self.assertFalse(missing["downstream_shell_selection_ready"])
            self.assertFalse(missing["makepad_shell_descriptor_selected"])
            self.assertEqual(missing["matching_candidate_count"], 0)
            missing_report = (
                adapter.validate_hostess_downstream_shell_selection_receipt(
                    manifest,
                    missing,
                )
            )
            self.assertEqual(missing_report["status"], "pass")

    def test_hostess_manifold_shell_handoff_review_intake_rejects_descriptor_and_drift(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = hostess_staged_payload_manifest_for_test(root)
            selection = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="desktop",
                graph_id="studio.graph.synthetic",
                consumer_id="rusty-studio-desktop-shell",
            )
            selected_handoff = adapter.selected_manifold_shell_handoff_from_selection(
                selection
            )
            manifold_review = ready_manifold_shell_handoff_review_receipt_for_test(
                selected_handoff
            )
            reviewed = (
                adapter.build_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    manifold_review,
                )
            )

            descriptor_selection = copy.deepcopy(selection)
            descriptor_selection["selected_artifact_kind"] = "shell_descriptor"
            descriptor_selection["manifold_shell_handoff_selected"] = False
            descriptor_selection["makepad_shell_descriptor_selected"] = True
            descriptor_receipt = (
                adapter.build_hostess_manifold_shell_handoff_review_intake_receipt(
                    descriptor_selection,
                    selected_handoff,
                    manifold_review,
                )
            )
            self.assertEqual(descriptor_receipt["status"], adapter.REJECTED_STATUS)
            self.assertEqual(
                descriptor_receipt["issue_code"],
                "hostess.issue.hostess_manifold_shell_handoff_review_intake_source_not_ready",
            )
            self.assertFalse(
                descriptor_receipt["manifold_shell_handoff_review_ready"]
            )

            runtime_drift = copy.deepcopy(reviewed)
            runtime_drift["launch_started"] = True
            runtime_report = (
                adapter.validate_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    manifold_review,
                    runtime_drift,
                )
            )
            self.assertEqual(runtime_report["status"], "fail")
            self.assertEqual(
                runtime_report["issue_code"],
                "hostess.issue.hostess_manifold_shell_handoff_review_intake_runtime_started",
            )

            review_drift = copy.deepcopy(manifold_review)
            review_drift["handoff_id"] = "shell_handoff.other"
            drift_receipt = (
                adapter.build_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    review_drift,
                )
            )
            self.assertEqual(drift_receipt["status"], adapter.REJECTED_STATUS)
            self.assertFalse(drift_receipt["manifold_shell_handoff_review_ready"])

            linked_drift = copy.deepcopy(reviewed)
            linked_drift["manifold_review_handoff_id"] = "shell_handoff.other"
            linked_report = (
                adapter.validate_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    manifold_review,
                    linked_drift,
                )
            )
            self.assertEqual(linked_report["status"], "fail")
            self.assertEqual(
                linked_report["issue_code"],
                "hostess.issue.hostess_manifold_shell_handoff_review_intake_review_drift",
            )

    def test_hostess_accepts_makepad_shell_contract_from_reviewed_manifold_handoff(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = hostess_staged_payload_manifest_for_test(root)
            selection = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="desktop",
                graph_id="studio.graph.synthetic",
                consumer_id="rusty-studio-desktop-shell",
            )
            selected_handoff = adapter.selected_manifold_shell_handoff_from_selection(
                selection
            )
            manifold_review = ready_manifold_shell_handoff_review_receipt_for_test(
                selected_handoff
            )
            intake = (
                adapter.build_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    manifold_review,
                )
            )

            receipt = adapter.build_hostess_makepad_shell_contract_receipt(
                intake,
                root / "hostess-manifold-shell-handoff-review-intake-receipt.json",
            )

            self.assertEqual(
                receipt["$schema"],
                adapter.HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA,
            )
            self.assertEqual(receipt["status"], adapter.ACCEPTED_STATUS)
            self.assertIsNone(receipt["issue_code"])
            self.assertTrue(receipt["makepad_contract_input_accepted"])
            self.assertTrue(receipt["makepad_shell_contract_ready"])
            self.assertFalse(receipt["descriptor_fallback_used"])
            self.assertFalse(receipt["makepad_shell_descriptor_selected"])
            self.assertTrue(receipt["manifold_shell_handoff_selected"])
            self.assertTrue(receipt["manifold_shell_handoff_review_ready"])
            self.assertEqual(
                receipt["selected_handoff_id"],
                intake["selected_handoff_id"],
            )
            self.assertEqual(
                receipt["manifold_review_handoff_id"],
                intake["selected_handoff_id"],
            )
            self.assertEqual(receipt["reviewed_stream_count"], 2)
            self.assertEqual(receipt["reviewed_command_count"], 2)
            self.assertEqual(receipt["reviewed_transport_count"], 1)
            self.assertEqual(receipt["reviewed_endpoint_count"], 1)
            self.assertFalse(receipt["legacy_reference_dependency_used"])
            self.assertFalse(receipt["launch_started"])
            self.assertFalse(receipt["makepad_runtime_started"])
            self.assertFalse(receipt["runtime_execution_performed"])
            self.assertFalse(receipt["platform_execution_performed"])
            self.assertFalse(receipt["command_session_started"])
            self.assertEqual(
                receipt["next_required_action"],
                "makepad_read_reviewed_manifold_shell_contract_without_launch",
            )

            validation = adapter.validate_hostess_makepad_shell_contract_receipt(
                intake,
                receipt,
            )
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["makepad_shell_contract_ready"])
            self.assertFalse(validation["descriptor_fallback_used"])
            self.assertFalse(validation["runtime_execution_performed"])
            self.assertFalse(validation["platform_execution_performed"])

    def test_hostess_builds_makepad_shell_launch_handoff_from_contract_without_launch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = hostess_staged_payload_manifest_for_test(root)
            selection = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="desktop",
                graph_id="studio.graph.synthetic",
                consumer_id="rusty-studio-desktop-shell",
            )
            selected_handoff = adapter.selected_manifold_shell_handoff_from_selection(
                selection
            )
            manifold_review = ready_manifold_shell_handoff_review_receipt_for_test(
                selected_handoff
            )
            intake = (
                adapter.build_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    manifold_review,
                )
            )
            contract_path = root / "hostess-makepad-shell-contract-receipt.json"
            contract = adapter.build_hostess_makepad_shell_contract_receipt(
                intake,
                root / "hostess-manifold-shell-handoff-review-intake-receipt.json",
            )

            receipt = adapter.build_hostess_makepad_shell_launch_handoff_receipt(
                contract,
                contract_path,
            )

            self.assertEqual(
                receipt["$schema"],
                adapter.HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_SCHEMA,
            )
            self.assertEqual(receipt["status"], "ready")
            self.assertIsNone(receipt["issue_code"])
            self.assertTrue(receipt["makepad_contract_reader_required"])
            self.assertTrue(receipt["makepad_contract_reader_ready"])
            self.assertTrue(receipt["makepad_launch_handoff_ready"])
            self.assertTrue(receipt["makepad_launch_request_ready"])
            self.assertEqual(
                receipt["makepad_contract_reader_input_path"],
                str(contract_path),
            )
            self.assertEqual(
                receipt["expected_reader_contract_schema"],
                adapter.HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA,
            )
            self.assertFalse(receipt["descriptor_fallback_allowed"])
            self.assertFalse(receipt["descriptor_fallback_used"])
            self.assertFalse(receipt["legacy_reference_dependency_used"])
            self.assertEqual(
                receipt["selected_handoff_id"],
                contract["selected_handoff_id"],
            )
            self.assertEqual(receipt["reviewed_stream_count"], 2)
            self.assertEqual(receipt["reviewed_command_count"], 2)
            self.assertEqual(receipt["reviewed_transport_count"], 1)
            self.assertEqual(receipt["reviewed_endpoint_count"], 1)
            self.assertFalse(receipt["launch_started"])
            self.assertFalse(receipt["makepad_runtime_started"])
            self.assertFalse(receipt["makepad_contract_read_started"])
            self.assertFalse(receipt["runtime_execution_performed"])
            self.assertFalse(receipt["platform_execution_performed"])
            self.assertFalse(receipt["command_session_started"])
            self.assertEqual(
                receipt["next_required_action"],
                "hostess_launch_makepad_from_contract_after_operator_approval",
            )

            validation = (
                adapter.validate_hostess_makepad_shell_launch_handoff_receipt(
                    contract,
                    receipt,
                )
            )
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["makepad_contract_reader_ready"])
            self.assertTrue(validation["makepad_launch_handoff_ready"])
            self.assertFalse(validation["descriptor_fallback_used"])
            self.assertFalse(validation["legacy_reference_dependency_used"])

    def test_hostess_makepad_shell_contract_rejects_descriptor_and_runtime_drift(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = hostess_staged_payload_manifest_for_test(root)
            selection = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="desktop",
                graph_id="studio.graph.synthetic",
                consumer_id="rusty-studio-desktop-shell",
            )
            selected_handoff = adapter.selected_manifold_shell_handoff_from_selection(
                selection
            )
            manifold_review = ready_manifold_shell_handoff_review_receipt_for_test(
                selected_handoff
            )
            intake = (
                adapter.build_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    manifold_review,
                )
            )
            accepted = adapter.build_hostess_makepad_shell_contract_receipt(intake)

            descriptor_intake = copy.deepcopy(intake)
            descriptor_intake["makepad_shell_descriptor_selected"] = True
            descriptor_receipt = adapter.build_hostess_makepad_shell_contract_receipt(
                descriptor_intake
            )
            self.assertEqual(descriptor_receipt["status"], adapter.REJECTED_STATUS)
            self.assertEqual(
                descriptor_receipt["issue_code"],
                "hostess.issue.hostess_makepad_shell_contract_source_not_ready",
            )
            self.assertFalse(descriptor_receipt["makepad_shell_contract_ready"])
            self.assertTrue(descriptor_receipt["descriptor_fallback_used"])

            runtime_drift = copy.deepcopy(accepted)
            runtime_drift["makepad_runtime_started"] = True
            runtime_report = adapter.validate_hostess_makepad_shell_contract_receipt(
                intake,
                runtime_drift,
            )
            self.assertEqual(runtime_report["status"], "fail")
            self.assertEqual(
                runtime_report["issue_code"],
                "hostess.issue.hostess_makepad_shell_contract_runtime_started",
            )

            linkage_drift = copy.deepcopy(accepted)
            linkage_drift["selected_handoff_id"] = "shell_handoff.other"
            linkage_report = adapter.validate_hostess_makepad_shell_contract_receipt(
                intake,
                linkage_drift,
            )
            self.assertEqual(linkage_report["status"], "fail")
            self.assertEqual(
                linkage_report["issue_code"],
                "hostess.issue.hostess_makepad_shell_contract_linkage_drift",
            )

    def test_hostess_makepad_shell_launch_handoff_rejects_descriptor_and_runtime_drift(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = hostess_staged_payload_manifest_for_test(root)
            selection = adapter.build_hostess_downstream_shell_selection_receipt(
                manifest,
                target_kind="desktop",
                graph_id="studio.graph.synthetic",
                consumer_id="rusty-studio-desktop-shell",
            )
            selected_handoff = adapter.selected_manifold_shell_handoff_from_selection(
                selection
            )
            manifold_review = ready_manifold_shell_handoff_review_receipt_for_test(
                selected_handoff
            )
            intake = (
                adapter.build_hostess_manifold_shell_handoff_review_intake_receipt(
                    selection,
                    selected_handoff,
                    manifold_review,
                )
            )
            accepted = adapter.build_hostess_makepad_shell_contract_receipt(intake)
            ready = adapter.build_hostess_makepad_shell_launch_handoff_receipt(
                accepted
            )

            descriptor_contract = copy.deepcopy(accepted)
            descriptor_contract["descriptor_fallback_used"] = True
            descriptor_receipt = (
                adapter.build_hostess_makepad_shell_launch_handoff_receipt(
                    descriptor_contract
                )
            )
            self.assertEqual(descriptor_receipt["status"], adapter.REJECTED_STATUS)
            self.assertEqual(
                descriptor_receipt["issue_code"],
                "hostess.issue.hostess_makepad_shell_launch_handoff_source_not_ready",
            )
            self.assertFalse(descriptor_receipt["makepad_launch_handoff_ready"])
            self.assertTrue(descriptor_receipt["descriptor_fallback_used"])

            runtime_drift = copy.deepcopy(ready)
            runtime_drift["launch_started"] = True
            runtime_report = (
                adapter.validate_hostess_makepad_shell_launch_handoff_receipt(
                    accepted,
                    runtime_drift,
                )
            )
            self.assertEqual(runtime_report["status"], "fail")
            self.assertEqual(
                runtime_report["issue_code"],
                "hostess.issue.hostess_makepad_shell_launch_handoff_runtime_started",
            )

            linkage_drift = copy.deepcopy(ready)
            linkage_drift["selected_handoff_id"] = "shell_handoff.other"
            linkage_report = (
                adapter.validate_hostess_makepad_shell_launch_handoff_receipt(
                    accepted,
                    linkage_drift,
                )
            )
            self.assertEqual(linkage_report["status"], "fail")
            self.assertEqual(
                linkage_report["issue_code"],
                "hostess.issue.hostess_makepad_shell_launch_handoff_linkage_drift",
            )


if __name__ == "__main__":
    unittest.main()
