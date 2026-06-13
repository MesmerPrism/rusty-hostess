"""Studio staging request CLI fixture-writing tests."""

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


class StudioStagingCliTests(unittest.TestCase):
    def test_cli_writes_operator_release_readiness_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            evidence_review_path = root / "platform-smoke-evidence-review.json"
            replay_receipt_path = root / "pmb-replay-validation-receipt.json"
            release_bundle_path = root / "operator-release-readiness-bundle.json"
            release_rejection_path = (
                root / "operator-release-readiness-bundle-rejection.json"
            )
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
            evidence_review, replay_receipt = ready_operator_release_inputs()
            evidence_review_path.write_text(
                json.dumps(evidence_review),
                encoding="utf-8",
            )
            replay_receipt_path.write_text(
                json.dumps(replay_receipt),
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--platform-smoke-evidence-review-in",
                    str(evidence_review_path),
                    "--pmb-replay-validation-receipt-in",
                    str(replay_receipt_path),
                    "--operator-release-readiness-bundle-out",
                    str(release_bundle_path),
                    "--operator-release-readiness-bundle-rejection-out",
                    str(release_rejection_path),
                    "--validate-operator-release-readiness-bundle",
                    str(release_bundle_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            release_bundle = json.loads(release_bundle_path.read_text(encoding="utf-8"))
            release_validation = json.loads(
                release_bundle_path.with_suffix(
                    release_bundle_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            release_rejection = json.loads(
                release_rejection_path.read_text(encoding="utf-8")
            )
            self.assertEqual(release_bundle["status"], "ready")
            self.assertTrue(release_bundle["operator_release_ready"])
            self.assertFalse(release_bundle["copy_started"])
            self.assertFalse(release_bundle["install_started"])
            self.assertFalse(release_bundle["launch_started"])
            self.assertFalse(release_bundle["apk_build_started"])
            self.assertFalse(release_bundle["evidence_collection_started"])
            self.assertEqual(release_validation["status"], "pass")
            self.assertEqual(release_rejection["status"], "rejected")
            self.assertFalse(release_rejection["operator_release_ready"])
            self.assertFalse(release_rejection["release_payloads_copied"])

    def test_cli_writes_hostess_staging_handoff_acceptance_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            release_bundle_path = root / "operator-release-readiness-bundle.json"
            staging_handoff_path = root / "shell-hostess-staging-handoff.json"
            acceptance_manifest_path = (
                root / "shell-hostess-staging-acceptance-manifest.json"
            )
            receipt_path = root / "hostess-staging-handoff-acceptance-receipt.json"
            rejection_path = (
                root
                / "hostess-staging-handoff-acceptance-receipt-rejection.json"
            )
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
            evidence_review, replay_receipt = ready_pmb_operator_release_inputs()
            release_bundle = adapter.build_operator_release_readiness_bundle(
                evidence_review,
                replay_receipt,
            )
            release_bundle_path.write_text(json.dumps(release_bundle), encoding="utf-8")
            staging_handoff_path.write_text(
                json.dumps(ready_studio_hostess_staging_handoff()),
                encoding="utf-8",
            )
            acceptance_manifest_path.write_text(
                json.dumps(ready_studio_hostess_staging_acceptance_manifest()),
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--operator-release-readiness-bundle-in",
                    str(release_bundle_path),
                    "--hostess-staging-handoff-in",
                    str(staging_handoff_path),
                    "--hostess-staging-acceptance-manifest-in",
                    str(acceptance_manifest_path),
                    "--hostess-staging-handoff-acceptance-receipt-out",
                    str(receipt_path),
                    "--hostess-staging-handoff-acceptance-receipt-rejection-out",
                    str(rejection_path),
                    "--validate-hostess-staging-handoff-acceptance-receipt",
                    str(receipt_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            validation = json.loads(
                receipt_path.with_suffix(
                    receipt_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            rejection = json.loads(rejection_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], adapter.ACCEPTED_STATUS)
            self.assertTrue(receipt["pmb_shell_handoff_review_required"])
            self.assertFalse(receipt["staging_payloads_copied"])
            self.assertEqual(validation["status"], "pass")
            self.assertEqual(rejection["status"], adapter.REJECTED_STATUS)
            self.assertFalse(rejection["staging_handoff_accepted"])

    def test_cli_writes_hostess_staging_file_plan_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            acceptance_receipt_path = (
                root / "hostess-staging-handoff-acceptance-receipt.json"
            )
            file_plan_path = root / "shell-hostess-staging-file-plan.json"
            receipt_path = root / "hostess-staging-file-plan-receipt.json"
            rejection_path = root / "hostess-staging-file-plan-receipt-rejection.json"
            staging_root = root / "clean-hostess-staging"
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
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
            acceptance_receipt_path.write_text(
                json.dumps(acceptance_receipt),
                encoding="utf-8",
            )
            file_plan = ready_studio_hostess_staging_file_plan()
            file_plan_path.write_text(json.dumps(file_plan), encoding="utf-8")

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--hostess-staging-handoff-acceptance-receipt-in",
                    str(acceptance_receipt_path),
                    "--hostess-staging-file-plan-in",
                    str(file_plan_path),
                    "--hostess-staging-root",
                    str(staging_root),
                    "--hostess-staging-file-plan-receipt-out",
                    str(receipt_path),
                    "--hostess-staging-file-plan-receipt-rejection-out",
                    str(rejection_path),
                    "--validate-hostess-staging-file-plan-receipt",
                    str(receipt_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            validation = json.loads(
                receipt_path.with_suffix(
                    receipt_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            rejection = json.loads(rejection_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], adapter.ACCEPTED_STATUS)
            self.assertTrue(receipt["copy_plan_ready"])
            self.assertTrue(receipt["pmb_shell_handoff_review_required"])
            self.assertEqual(
                receipt["accepted_file_count"],
                file_plan["planned_file_count"],
            )
            self.assertFalse(receipt["copy_started"])
            self.assertFalse(receipt["staging_payloads_copied"])
            self.assertFalse(receipt["platform_execution_performed"])
            self.assertEqual(validation["status"], "pass")
            self.assertEqual(rejection["status"], adapter.REJECTED_STATUS)
            self.assertFalse(rejection["copy_plan_ready"])

    def test_cli_writes_hostess_staging_file_copy_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            file_plan_path = root / "shell-hostess-staging-file-plan.json"
            file_plan_receipt_path = root / "hostess-staging-file-plan-receipt.json"
            copy_receipt_path = root / "hostess-staging-file-copy-receipt.json"
            rejection_path = root / "hostess-staging-file-copy-receipt-rejection.json"
            staging_root = root / "clean-hostess-staging"
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
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
                staging_root=str(staging_root),
            )
            file_plan_path.write_text(json.dumps(file_plan), encoding="utf-8")
            file_plan_receipt_path.write_text(
                json.dumps(file_plan_receipt),
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--hostess-staging-file-plan-in",
                    str(file_plan_path),
                    "--hostess-staging-file-plan-receipt-in",
                    str(file_plan_receipt_path),
                    "--hostess-staging-file-copy-receipt-out",
                    str(copy_receipt_path),
                    "--hostess-staging-file-copy-receipt-rejection-out",
                    str(rejection_path),
                    "--validate-hostess-staging-file-copy-receipt",
                    str(copy_receipt_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            copy_receipt = json.loads(copy_receipt_path.read_text(encoding="utf-8"))
            validation = json.loads(
                copy_receipt_path.with_suffix(
                    copy_receipt_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            rejection = json.loads(rejection_path.read_text(encoding="utf-8"))
            self.assertEqual(copy_receipt["status"], adapter.COMPLETED_STATUS)
            self.assertTrue(copy_receipt["file_copy_completed"])
            self.assertEqual(
                copy_receipt["copied_file_count"],
                file_plan["planned_file_count"],
            )
            self.assertTrue(
                all(
                    Path(row["resolved_destination_path"]).exists()
                    for row in copy_receipt["copy_rows"]
                )
            )
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["copy_started"])
            self.assertEqual(rejection["status"], adapter.REJECTED_STATUS)
            self.assertFalse(rejection["file_copy_completed"])

    def test_cli_writes_hostess_staged_payload_manifest_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            file_copy_receipt_path = root / "hostess-staging-file-copy-receipt.json"
            manifest_path = root / "hostess-staged-payload-manifest-receipt.json"
            rejection_path = (
                root / "hostess-staged-payload-manifest-receipt-rejection.json"
            )
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
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
            file_copy_receipt_path.write_text(
                json.dumps(copy_receipt),
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--hostess-staging-file-copy-receipt-in",
                    str(file_copy_receipt_path),
                    "--hostess-staged-payload-manifest-receipt-out",
                    str(manifest_path),
                    "--hostess-staged-payload-manifest-receipt-rejection-out",
                    str(rejection_path),
                    "--validate-hostess-staged-payload-manifest-receipt",
                    str(manifest_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            validation = json.loads(
                manifest_path.with_suffix(
                    manifest_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            rejection = json.loads(rejection_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], adapter.REVIEWED_STATUS)
            self.assertTrue(manifest["makepad_shell_selection_ready"])
            self.assertGreater(manifest["target_descriptor_payload_count"], 0)
            self.assertFalse(manifest["launch_started"])
            self.assertFalse(manifest["runtime_execution_performed"])
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["makepad_shell_selection_ready"])
            self.assertEqual(rejection["status"], adapter.REJECTED_STATUS)
            self.assertFalse(rejection["makepad_shell_selection_ready"])

    def test_cli_writes_hostess_downstream_shell_selection_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            manifest_path = root / "hostess-staged-payload-manifest-receipt.json"
            selection_path = root / "hostess-downstream-shell-selection-receipt.json"
            rejection_path = (
                root / "hostess-downstream-shell-selection-receipt-rejection.json"
            )
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
            manifest = hostess_staged_payload_manifest_for_test(root)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--hostess-staged-payload-manifest-receipt-in",
                    str(manifest_path),
                    "--hostess-downstream-shell-selection-target-kind",
                    "desktop",
                    "--hostess-downstream-shell-selection-receipt-out",
                    str(selection_path),
                    "--hostess-downstream-shell-selection-receipt-rejection-out",
                    str(rejection_path),
                    "--validate-hostess-downstream-shell-selection-receipt",
                    str(selection_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            validation = json.loads(
                selection_path.with_suffix(
                    selection_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            rejection = json.loads(rejection_path.read_text(encoding="utf-8"))
            self.assertEqual(selection["status"], adapter.SELECTED_STATUS)
            self.assertEqual(selection["selected_target_kind"], "desktop")
            self.assertEqual(
                selection["selected_artifact_kind"],
                "manifold_shell_handoff",
            )
            self.assertTrue(selection["manifold_shell_handoff_selected"])
            self.assertFalse(selection["makepad_shell_descriptor_selected"])
            self.assertTrue(Path(selection["selected_payload_path"]).exists())
            self.assertFalse(selection["legacy_reference_dependency_used"])
            self.assertFalse(selection["launch_started"])
            self.assertFalse(selection["runtime_execution_performed"])
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["manifold_shell_handoff_selected"])
            self.assertFalse(validation["makepad_shell_descriptor_selected"])
            self.assertEqual(rejection["status"], adapter.REJECTED_STATUS)
            self.assertFalse(rejection["manifold_shell_handoff_selected"])
            self.assertFalse(rejection["makepad_shell_descriptor_selected"])

    def test_cli_writes_hostess_manifold_shell_handoff_review_intake_receipt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            selection_path = root / "hostess-downstream-shell-selection-receipt.json"
            review_path = root / "manifold-shell-handoff-review-receipt.json"
            intake_path = (
                root / "hostess-manifold-shell-handoff-review-intake-receipt.json"
            )
            rejection_path = (
                root
                / "hostess-manifold-shell-handoff-review-intake-receipt-rejection.json"
            )
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
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
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            review_path.write_text(json.dumps(manifold_review), encoding="utf-8")

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--hostess-downstream-shell-selection-receipt-in",
                    str(selection_path),
                    "--manifold-shell-handoff-review-receipt-in",
                    str(review_path),
                    "--hostess-manifold-shell-handoff-review-intake-receipt-out",
                    str(intake_path),
                    "--hostess-manifold-shell-handoff-review-intake-receipt-rejection-out",
                    str(rejection_path),
                    "--validate-hostess-manifold-shell-handoff-review-intake-receipt",
                    str(intake_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            receipt = json.loads(intake_path.read_text(encoding="utf-8"))
            validation = json.loads(
                intake_path.with_suffix(
                    intake_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            rejection = json.loads(rejection_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], adapter.REVIEWED_STATUS)
            self.assertTrue(receipt["manifold_shell_handoff_selected"])
            self.assertFalse(receipt["makepad_shell_descriptor_selected"])
            self.assertTrue(receipt["manifold_shell_handoff_review_ready"])
            self.assertFalse(receipt["launch_started"])
            self.assertFalse(receipt["runtime_execution_performed"])
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["manifold_shell_handoff_review_ready"])
            self.assertEqual(rejection["status"], adapter.REJECTED_STATUS)
            self.assertFalse(rejection["manifold_shell_handoff_review_ready"])

    def test_cli_writes_hostess_makepad_shell_contract_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            intake_path = (
                root / "hostess-manifold-shell-handoff-review-intake-receipt.json"
            )
            receipt_path = root / "hostess-makepad-shell-contract-receipt.json"
            rejection_path = (
                root / "hostess-makepad-shell-contract-receipt-rejection.json"
            )
            launch_path = (
                root / "hostess-makepad-shell-launch-handoff-receipt.json"
            )
            launch_rejection_path = (
                root
                / "hostess-makepad-shell-launch-handoff-receipt-rejection.json"
            )
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
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
            intake_path.write_text(json.dumps(intake), encoding="utf-8")

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--hostess-manifold-shell-handoff-review-intake-receipt-in",
                    str(intake_path),
                    "--hostess-makepad-shell-contract-receipt-out",
                    str(receipt_path),
                    "--hostess-makepad-shell-contract-receipt-rejection-out",
                    str(rejection_path),
                    "--hostess-makepad-shell-launch-handoff-receipt-out",
                    str(launch_path),
                    "--hostess-makepad-shell-launch-handoff-receipt-rejection-out",
                    str(launch_rejection_path),
                    "--validate-hostess-makepad-shell-contract-receipt",
                    str(receipt_path),
                    "--validate-hostess-makepad-shell-launch-handoff-receipt",
                    str(launch_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            validation = json.loads(
                receipt_path.with_suffix(
                    receipt_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            rejection = json.loads(rejection_path.read_text(encoding="utf-8"))
            launch = json.loads(launch_path.read_text(encoding="utf-8"))
            launch_validation = json.loads(
                launch_path.with_suffix(
                    launch_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            launch_rejection = json.loads(
                launch_rejection_path.read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["status"], adapter.ACCEPTED_STATUS)
            self.assertTrue(receipt["makepad_shell_contract_ready"])
            self.assertFalse(receipt["descriptor_fallback_used"])
            self.assertFalse(receipt["launch_started"])
            self.assertFalse(receipt["makepad_runtime_started"])
            self.assertFalse(receipt["runtime_execution_performed"])
            self.assertEqual(validation["status"], "pass")
            self.assertTrue(validation["makepad_shell_contract_ready"])
            self.assertEqual(rejection["status"], adapter.REJECTED_STATUS)
            self.assertFalse(rejection["makepad_shell_contract_ready"])
            self.assertEqual(launch["status"], "ready")
            self.assertTrue(launch["makepad_contract_reader_ready"])
            self.assertTrue(launch["makepad_launch_handoff_ready"])
            self.assertFalse(launch["launch_started"])
            self.assertFalse(launch["makepad_runtime_started"])
            self.assertFalse(launch["makepad_contract_read_started"])
            self.assertFalse(launch["runtime_execution_performed"])
            self.assertEqual(launch_validation["status"], "pass")
            self.assertTrue(launch_validation["makepad_launch_handoff_ready"])
            self.assertEqual(launch_rejection["status"], adapter.REJECTED_STATUS)
            self.assertFalse(launch_rejection["makepad_launch_handoff_ready"])

    def test_cli_writes_pmb_gated_operator_start_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            pmb_review_path = root / "pmb-shell-handoff-review.json"
            preflight_path = root / "operator-start-preflight.json"
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
            pmb_review_path.write_text(
                json.dumps(ready_pmb_shell_handoff_review()),
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--pmb-shell-handoff-review-in",
                    str(pmb_review_path),
                    "--require-pmb-shell-handoff-review",
                    "--platform-smoke-operator-start-preflight-out",
                    str(preflight_path),
                    "--validate-platform-smoke-operator-start-preflight",
                    str(preflight_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            validation = json.loads(
                preflight_path.with_suffix(
                    preflight_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(preflight["status"], "approved")
            self.assertTrue(preflight["pmb_shell_handoff_review_required"])
            self.assertTrue(preflight["pmb_shell_handoff_review_ready"])
            self.assertEqual(
                preflight["source_pmb_shell_handoff_review_path"],
                str(pmb_review_path),
            )
            self.assertEqual(
                preflight["approved_readiness_input_count"],
                len(adapter.OPERATOR_START_READINESS_INPUT_CONTRACTS) + 1,
            )
            self.assertEqual(validation["status"], "pass")
            self.assertFalse(validation["runtime_execution_performed"])
            self.assertFalse(validation["platform_execution_performed"])

    def test_cli_uses_pmb_review_path_from_studio_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            pmb_review_path = root / "pmb-shell-handoff-review.json"
            preflight_path = root / "operator-start-preflight.json"
            request = valid_request()
            request["pmb_shell_handoff_review_required"] = True
            request["pmb_shell_handoff_review_path"] = pmb_review_path.name
            request["hostess_operator_start_preflight_cli_args"] = [
                "--pmb-shell-handoff-review-in",
                pmb_review_path.name,
                "--require-pmb-shell-handoff-review",
            ]
            request_path.write_text(json.dumps(request), encoding="utf-8")
            pmb_review_path.write_text(
                json.dumps(ready_pmb_shell_handoff_review()),
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--platform-smoke-operator-start-preflight-out",
                    str(preflight_path),
                    "--validate-platform-smoke-operator-start-preflight",
                    str(preflight_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            validation = json.loads(
                preflight_path.with_suffix(
                    preflight_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(preflight["status"], "approved")
            self.assertTrue(preflight["pmb_shell_handoff_review_required"])
            self.assertTrue(preflight["pmb_shell_handoff_review_ready"])
            self.assertEqual(
                preflight["source_pmb_shell_handoff_review_path"],
                str(pmb_review_path),
            )
            pmb_input = next(
                item
                for item in preflight["readiness_inputs"]
                if item["readiness_input_id"]
                == adapter.PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
            )
            self.assertEqual(pmb_input["readiness_status"], adapter.APPROVED_STATUS)
            self.assertEqual(validation["status"], "pass")

    def test_cli_writes_projected_motion_breath_validation_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            package_evidence_path = root / "pmb-package-evidence-intake.json"
            authoring_review_path = root / "pmb-authoring-review.json"
            source_adapter_selection_path = root / "pmb-source-adapter-selection.json"
            handoff_path = root / "pmb-validation-handoff.json"
            replay_receipt_path = root / "pmb-replay-validation-receipt.json"
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")
            package_evidence_path.write_text(
                json.dumps(ready_pmb_package_evidence_intake()),
                encoding="utf-8",
            )
            authoring_review_path.write_text(
                json.dumps(ready_pmb_authoring_review()),
                encoding="utf-8",
            )
            source_adapter_selection_path.write_text(
                json.dumps(ready_pmb_source_adapter_selection_review()),
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--pmb-authoring-review-in",
                    str(authoring_review_path),
                    "--pmb-package-evidence-intake-in",
                    str(package_evidence_path),
                    "--pmb-source-adapter-selection-in",
                    str(source_adapter_selection_path),
                    "--pmb-validation-handoff-out",
                    str(handoff_path),
                    "--validate-pmb-validation-handoff",
                    str(handoff_path),
                    "--pmb-replay-validation-receipt-out",
                    str(replay_receipt_path),
                    "--validate-pmb-replay-validation-receipt",
                    str(replay_receipt_path),
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            validation = json.loads(
                handoff_path.with_suffix(handoff_path.suffix + ".validation.json").read_text(
                    encoding="utf-8"
                )
            )
            replay_receipt = json.loads(replay_receipt_path.read_text(encoding="utf-8"))
            replay_validation = json.loads(
                replay_receipt_path.with_suffix(
                    replay_receipt_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(handoff["status"], "ready")
            self.assertEqual(handoff["handoff_owner"], "rusty.hostess")
            self.assertTrue(handoff["source_adapter_selection_present"])
            self.assertEqual(handoff["selected_input_kind"], "vector3")
            self.assertEqual(handoff["validation_slot_count"], 5)
            self.assertFalse(handoff["platform_execution_performed"])
            self.assertEqual(validation["status"], "pass")
            self.assertEqual(replay_receipt["status"], "validated")
            self.assertEqual(replay_receipt["scorecard_status"], "pass")
            self.assertFalse(replay_receipt["replay_execution_started"])
            self.assertFalse(replay_receipt["fixture_payloads_copied"])
            self.assertEqual(replay_validation["status"], "pass")

    def test_cli_writes_schema_only_report_and_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            ack_path = root / "ack.json"
            reject_path = root / "reject.json"
            smoke_path = root / "smoke-handoff.json"
            dry_run_path = root / "smoke-dry-run-request.json"
            receipt_path = root / "smoke-dry-run-receipt.json"
            preflight_path = root / "smoke-preflight.json"
            execution_path = root / "smoke-host-shell-execution.json"
            bundle_path = root / "smoke-review-bundle.json"
            plan_path = root / "platform-smoke-plan.json"
            approval_path = root / "platform-smoke-approval.json"
            rejection_path = root / "platform-smoke-rejection.json"
            execution_request_path = root / "platform-smoke-execution-request.json"
            execution_receipt_path = root / "platform-smoke-execution-receipt.json"
            operator_start_path = root / "platform-smoke-operator-start-gate.json"
            operator_start_preflight_path = (
                root / "platform-smoke-operator-start-preflight.json"
            )
            operator_start_preflight_rejection_path = (
                root / "platform-smoke-operator-start-preflight-rejection.json"
            )
            execution_report_path = root / "platform-smoke-execution-report.json"
            execution_report_rejection_path = (
                root / "platform-smoke-execution-report-rejection.json"
            )
            evidence_attachment_path = root / "platform-smoke-evidence-attachment.json"
            evidence_attachment_rejection_path = (
                root / "platform-smoke-evidence-attachment-rejection.json"
            )
            evidence_review_path = root / "platform-smoke-evidence-review.json"
            evidence_review_rejection_path = (
                root / "platform-smoke-evidence-review-rejection.json"
            )
            request_path.write_text(json.dumps(valid_request()), encoding="utf-8")

            with patch.object(
                sys,
                "argv",
                [
                    "studio-staging-request",
                    "--request",
                    str(request_path),
                    "--report-out",
                    str(report_path),
                    "--ack-out",
                    str(ack_path),
                    "--reject-out",
                    str(reject_path),
                    "--smoke-handoff-out",
                    str(smoke_path),
                    "--target-profile",
                    "hostess.t.desktop.schema_smoke",
                    "--smoke-dry-run-request-out",
                    str(dry_run_path),
                    "--smoke-dry-run-receipt-out",
                    str(receipt_path),
                    "--smoke-preflight-out",
                    str(preflight_path),
                    "--validate-smoke-preflight",
                    str(preflight_path),
                    "--smoke-host-shell-execution-out",
                    str(execution_path),
                    "--validate-smoke-host-shell-execution",
                    str(execution_path),
                    "--smoke-review-bundle-out",
                    str(bundle_path),
                    "--validate-smoke-review-bundle",
                    str(bundle_path),
                    "--platform-smoke-plan-out",
                    str(plan_path),
                    "--platform-smoke-approval-out",
                    str(approval_path),
                    "--platform-smoke-rejection-out",
                    str(rejection_path),
                    "--target-platform",
                    "hostess.quest.operator_controlled_smoke_plan",
                    "--validate-platform-smoke-plan",
                    str(plan_path),
                    "--validate-platform-smoke-approval",
                    str(approval_path),
                    "--platform-smoke-execution-request-out",
                    str(execution_request_path),
                    "--platform-smoke-execution-receipt-out",
                    str(execution_receipt_path),
                    "--validate-platform-smoke-execution-request",
                    str(execution_request_path),
                    "--validate-platform-smoke-execution-receipt",
                    str(execution_receipt_path),
                    "--platform-smoke-operator-start-gate-out",
                    str(operator_start_path),
                    "--validate-platform-smoke-operator-start-gate",
                    str(operator_start_path),
                    "--platform-smoke-operator-start-preflight-out",
                    str(operator_start_preflight_path),
                    "--platform-smoke-operator-start-preflight-rejection-out",
                    str(operator_start_preflight_rejection_path),
                    "--validate-platform-smoke-operator-start-preflight",
                    str(operator_start_preflight_path),
                    "--platform-smoke-execution-report-out",
                    str(execution_report_path),
                    "--platform-smoke-execution-report-rejection-out",
                    str(execution_report_rejection_path),
                    "--validate-platform-smoke-execution-report",
                    str(execution_report_path),
                    "--platform-smoke-evidence-attachment-out",
                    str(evidence_attachment_path),
                    "--platform-smoke-evidence-attachment-rejection-out",
                    str(evidence_attachment_rejection_path),
                    "--validate-platform-smoke-evidence-attachment",
                    str(evidence_attachment_path),
                    "--platform-smoke-evidence-review-out",
                    str(evidence_review_path),
                    "--platform-smoke-evidence-review-rejection-out",
                    str(evidence_review_rejection_path),
                    "--validate-platform-smoke-evidence-review",
                    str(evidence_review_path),
                    "--host-shell-kind",
                    "hostess.t.quest_host_shell.schema_gate",
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            report = json.loads(report_path.read_text(encoding="utf-8"))
            ack = json.loads(ack_path.read_text(encoding="utf-8"))
            reject = json.loads(reject_path.read_text(encoding="utf-8"))
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            dry_run = json.loads(dry_run_path.read_text(encoding="utf-8"))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            preflight_report = json.loads(
                preflight_path.with_suffix(preflight_path.suffix + ".validation.json").read_text(
                    encoding="utf-8"
                )
            )
            execution = json.loads(execution_path.read_text(encoding="utf-8"))
            execution_report = json.loads(
                execution_path.with_suffix(execution_path.suffix + ".validation.json").read_text(
                    encoding="utf-8"
                )
            )
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle_report = json.loads(
                bundle_path.with_suffix(bundle_path.suffix + ".validation.json").read_text(
                    encoding="utf-8"
                )
            )
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan_report = json.loads(
                plan_path.with_suffix(plan_path.suffix + ".validation.json").read_text(
                    encoding="utf-8"
                )
            )
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
            approval_report = json.loads(
                approval_path.with_suffix(approval_path.suffix + ".validation.json").read_text(
                    encoding="utf-8"
                )
            )
            rejection = json.loads(rejection_path.read_text(encoding="utf-8"))
            platform_request = json.loads(execution_request_path.read_text(encoding="utf-8"))
            platform_request_report = json.loads(
                execution_request_path.with_suffix(
                    execution_request_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            platform_receipt = json.loads(execution_receipt_path.read_text(encoding="utf-8"))
            platform_receipt_report = json.loads(
                execution_receipt_path.with_suffix(
                    execution_receipt_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            operator_start = json.loads(operator_start_path.read_text(encoding="utf-8"))
            operator_start_report = json.loads(
                operator_start_path.with_suffix(operator_start_path.suffix + ".validation.json").read_text(
                    encoding="utf-8"
                )
            )
            operator_start_preflight = json.loads(
                operator_start_preflight_path.read_text(encoding="utf-8")
            )
            operator_start_preflight_rejection = json.loads(
                operator_start_preflight_rejection_path.read_text(encoding="utf-8")
            )
            operator_start_preflight_report = json.loads(
                operator_start_preflight_path.with_suffix(
                    operator_start_preflight_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            platform_execution_report = json.loads(
                execution_report_path.read_text(encoding="utf-8")
            )
            platform_execution_report_rejection = json.loads(
                execution_report_rejection_path.read_text(encoding="utf-8")
            )
            platform_execution_report_validation = json.loads(
                execution_report_path.with_suffix(
                    execution_report_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            evidence_attachment = json.loads(
                evidence_attachment_path.read_text(encoding="utf-8")
            )
            evidence_attachment_rejection = json.loads(
                evidence_attachment_rejection_path.read_text(encoding="utf-8")
            )
            evidence_attachment_validation = json.loads(
                evidence_attachment_path.with_suffix(
                    evidence_attachment_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            evidence_review = json.loads(evidence_review_path.read_text(encoding="utf-8"))
            evidence_review_rejection = json.loads(
                evidence_review_rejection_path.read_text(encoding="utf-8")
            )
            evidence_review_validation = json.loads(
                evidence_review_path.with_suffix(
                    evidence_review_path.suffix + ".validation.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(report["status"], "accepted")
            self.assertFalse(report["execution_performed"])
            self.assertEqual(ack["ack_status"], "accepted")
            self.assertEqual(reject["reject_status"], "rejected")
            self.assertEqual(smoke["status"], "ready")
            self.assertFalse(smoke["build_started"])
            self.assertFalse(smoke["install_started"])
            self.assertEqual(dry_run["status"], "ready")
            self.assertFalse(dry_run["copy_started"])
            self.assertEqual(receipt["status"], "accepted")
            self.assertFalse(receipt["launch_started"])
            self.assertEqual(preflight["status"], "ready")
            self.assertFalse(preflight["platform_execution_allowed"])
            self.assertTrue(
                all(
                    capability["execution_started"] is False
                    for capability in preflight["preflight_capabilities"]
                )
            )
            self.assertEqual(preflight_report["status"], "pass")
            self.assertEqual(execution["status"], "completed")
            self.assertFalse(execution["platform_execution_performed"])
            self.assertTrue(execution["host_shell_harness_performed"])
            self.assertEqual(execution_report["status"], "pass")
            self.assertEqual(bundle["status"], "reviewed")
            self.assertFalse(bundle["platform_execution_performed"])
            self.assertTrue(bundle["review_bundle_written"])
            self.assertEqual(bundle_report["status"], "pass")
            self.assertEqual(plan["status"], "planned")
            self.assertFalse(plan["platform_execution_performed"])
            self.assertFalse(plan["operator_approved"])
            self.assertEqual(plan_report["status"], "pass")
            self.assertEqual(approval["status"], "approved")
            self.assertTrue(approval["operator_approved"])
            self.assertTrue(approval["future_execution_authorized"])
            self.assertFalse(approval["execution_performed"])
            self.assertFalse(approval["platform_execution_performed"])
            self.assertEqual(approval["approved_action_count"], len(plan["planned_actions"]))
            self.assertEqual(approval_report["status"], "pass")
            self.assertEqual(rejection["status"], "rejected")
            self.assertFalse(rejection["operator_approved"])
            self.assertFalse(rejection["future_execution_authorized"])
            self.assertFalse(rejection["execution_performed"])
            self.assertFalse(rejection["platform_execution_performed"])
            self.assertEqual(platform_request["status"], "ready")
            self.assertFalse(platform_request["device_required"])
            self.assertFalse(platform_request["execution_performed"])
            self.assertFalse(platform_request["platform_execution_performed"])
            self.assertFalse(platform_request["schema_path_execution_allowed"])
            self.assertEqual(
                platform_request["pending_execution_action_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(platform_request_report["status"], "pass")
            self.assertEqual(platform_receipt["status"], "pending")
            self.assertTrue(platform_receipt["execution_acknowledged"])
            self.assertTrue(platform_receipt["schema_checks_performed"])
            self.assertFalse(platform_receipt["execution_performed"])
            self.assertFalse(platform_receipt["platform_execution_performed"])
            self.assertFalse(platform_receipt["schema_path_execution_allowed"])
            self.assertEqual(
                platform_receipt["pending_execution_action_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(platform_receipt_report["status"], "pass")
            self.assertEqual(operator_start["status"], "ready")
            self.assertFalse(operator_start["device_required"])
            self.assertFalse(operator_start["operator_started"])
            self.assertFalse(operator_start["host_shell_started"])
            self.assertFalse(operator_start["execution_performed"])
            self.assertFalse(operator_start["platform_execution_performed"])
            self.assertFalse(operator_start["schema_path_execution_allowed"])
            self.assertEqual(
                operator_start["pending_operator_start_action_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(
                operator_start["operator_start_ack_template"]["ack_status"],
                "pending",
            )
            self.assertEqual(
                len(operator_start["expected_evidence_receipt_templates"]),
                len(plan["planned_actions"]),
            )
            self.assertEqual(operator_start_report["status"], "pass")
            self.assertEqual(operator_start_preflight["status"], "approved")
            self.assertTrue(operator_start_preflight["operator_start_preflight_approved"])
            self.assertFalse(operator_start_preflight["device_required"])
            self.assertFalse(operator_start_preflight["operator_started"])
            self.assertFalse(operator_start_preflight["host_shell_started"])
            self.assertFalse(operator_start_preflight["execution_performed"])
            self.assertFalse(operator_start_preflight["platform_execution_performed"])
            self.assertFalse(operator_start_preflight["schema_path_execution_allowed"])
            self.assertEqual(
                operator_start_preflight["approved_readiness_input_count"],
                len(adapter.OPERATOR_START_READINESS_INPUT_CONTRACTS),
            )
            self.assertEqual(
                operator_start_preflight["approved_operator_start_action_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(operator_start_preflight_report["status"], "pass")
            self.assertEqual(operator_start_preflight_rejection["status"], "rejected")
            self.assertFalse(operator_start_preflight_rejection["operator_start_preflight_approved"])
            self.assertFalse(operator_start_preflight_rejection["operator_started"])
            self.assertFalse(operator_start_preflight_rejection["host_shell_started"])
            self.assertFalse(operator_start_preflight_rejection["execution_performed"])
            self.assertFalse(operator_start_preflight_rejection["platform_execution_performed"])
            self.assertEqual(
                operator_start_preflight_rejection["rejected_readiness_input_count"],
                len(adapter.OPERATOR_START_READINESS_INPUT_CONTRACTS),
            )
            self.assertEqual(platform_execution_report["status"], "completed")
            self.assertTrue(platform_execution_report["operator_started_outside_studio"])
            self.assertTrue(platform_execution_report["host_shell_started_outside_studio"])
            self.assertFalse(platform_execution_report["execution_performed"])
            self.assertFalse(platform_execution_report["schema_path_execution_allowed"])
            self.assertFalse(platform_execution_report["platform_execution_performed"])
            self.assertFalse(platform_execution_report["real_platform_execution_evidence_attached"])
            self.assertEqual(
                platform_execution_report["completed_action_report_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(
                platform_execution_report["pending_evidence_placeholder_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(platform_execution_report_validation["status"], "pass")
            self.assertEqual(platform_execution_report_rejection["status"], "rejected")
            self.assertFalse(
                platform_execution_report_rejection["operator_started_outside_studio"]
            )
            self.assertFalse(
                platform_execution_report_rejection["host_shell_started_outside_studio"]
            )
            self.assertFalse(platform_execution_report_rejection["platform_execution_performed"])
            self.assertEqual(
                platform_execution_report_rejection["rejected_action_report_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(evidence_attachment["status"], "validated")
            self.assertTrue(evidence_attachment["external_evidence_descriptors_attached"])
            self.assertTrue(evidence_attachment["all_placeholders_bound"])
            self.assertFalse(evidence_attachment["evidence_payloads_copied"])
            self.assertFalse(evidence_attachment["evidence_collection_started"])
            self.assertFalse(evidence_attachment["platform_execution_performed"])
            self.assertFalse(evidence_attachment["real_platform_execution_evidence_attached"])
            self.assertEqual(
                evidence_attachment["validated_evidence_attachment_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(evidence_attachment_validation["status"], "pass")
            self.assertEqual(evidence_attachment_rejection["status"], "rejected")
            self.assertFalse(
                evidence_attachment_rejection["external_evidence_descriptors_attached"]
            )
            self.assertFalse(evidence_attachment_rejection["evidence_payloads_copied"])
            self.assertEqual(
                evidence_attachment_rejection["rejected_evidence_attachment_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(evidence_review["status"], "reviewed")
            self.assertEqual(evidence_review["scorecard_status"], "pass")
            self.assertTrue(evidence_review["operator_review_ready"])
            self.assertFalse(evidence_review["evidence_payloads_copied"])
            self.assertFalse(evidence_review["evidence_collection_started"])
            self.assertFalse(evidence_review["platform_execution_performed"])
            self.assertFalse(evidence_review["real_platform_execution_evidence_attached"])
            self.assertEqual(evidence_review["missing_attachment_count"], 0)
            self.assertEqual(evidence_review["rejected_attachment_count"], 0)
            self.assertEqual(
                evidence_review["reviewed_evidence_attachment_count"],
                len(plan["planned_actions"]),
            )
            self.assertEqual(evidence_review_validation["status"], "pass")
            self.assertEqual(evidence_review_rejection["status"], "rejected")
            self.assertEqual(evidence_review_rejection["scorecard_status"], "fail")
            self.assertFalse(evidence_review_rejection["operator_review_ready"])
            self.assertFalse(evidence_review_rejection["evidence_payloads_copied"])
            self.assertEqual(
                evidence_review_rejection["rejected_attachment_count"],
                len(evidence_review_rejection["evidence_review_rows"])
                + len(evidence_review_rejection["readiness_review_rows"]),
            )


if __name__ == "__main__":
    unittest.main()
