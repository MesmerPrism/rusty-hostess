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


class StudioStagingRequestTests(unittest.TestCase):
    def test_direct_script_help_invocation_keeps_extracted_module_imports_working(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "tools" / "studio_staging_request.py"

        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--hostess-makepad-shell-contract-receipt-out", result.stdout)

    def test_accepts_ready_studio_request_and_builds_ack_reject_fixtures(self) -> None:
        request = valid_request()

        report = adapter.build_intake_report(request)
        self.assertEqual(report["$schema"], adapter.INTAKE_SCHEMA)
        self.assertEqual(report["status"], "accepted")
        self.assertIsNone(report["issue_code"])
        self.assertFalse(report["execution_performed"])
        self.assertFalse(report["copy_stage_install_launch_evidence_started"])
        self.assertFalse(report["command_session_started"])
        self.assertEqual(report["accepted_action_ids"], expected_action_ids())
        self.assertTrue(all(check["status"] == "pass" for check in report["checks"]))

        ack = adapter.build_ack_fixture(request)
        self.assertEqual(ack["$schema"], adapter.ACK_SCHEMA)
        self.assertEqual(ack["ack_status"], "accepted")
        self.assertEqual(ack["accepted_by"], "rusty.hostess")
        self.assertFalse(ack["execution_in_studio"])
        self.assertEqual(ack["accepted_action_ids"], expected_action_ids())
        self.assertEqual(
            adapter.validate_ack_fixture(request, ack)["status"],
            "pass",
        )

        reject = adapter.build_reject_fixture(request, "hostess.issue.operator_rejected_request")
        self.assertEqual(reject["$schema"], adapter.REJECT_SCHEMA)
        self.assertEqual(reject["reject_status"], "rejected")
        self.assertEqual(reject["rejected_by"], "rusty.hostess")
        self.assertFalse(reject["execution_in_studio"])
        self.assertEqual(reject["rejected_action_ids"], expected_action_ids())
        self.assertEqual(
            adapter.validate_reject_fixture(request, reject)["status"],
            "pass",
        )

    def test_rejects_action_owner_route_or_execution_drift(self) -> None:
        request = valid_request()
        copy_action = request["actions"][3]
        copy_action["owner"] = "rusty.studio"
        copy_action["responsible_authority"] = "rusty.studio"
        copy_action["route_kind"] = "studio.stage.files"
        copy_action["execution_in_studio"] = True

        report = adapter.build_intake_report(request)

        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["issue_code"], "hostess.issue.adapter_action_contract_drift")
        self.assertEqual(report["accepted_action_ids"], [])
        self.assertEqual(report["rejected_action_ids"], expected_action_ids())
        self.assertTrue(
            any(
                check["check_id"] == "hostess.check.studio_staging_request.action_contracts"
                and check["status"] == "fail"
                for check in report["checks"]
            )
        )

    def test_rejects_missing_prohibited_studio_runtime_action(self) -> None:
        request = valid_request()
        request["prohibited_studio_actions"].remove("launch")

        report = adapter.build_intake_report(request)

        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["issue_code"], "hostess.issue.prohibited_studio_actions_missing")
        self.assertTrue(
            any(
                check["check_id"]
                == "hostess.check.studio_staging_request.prohibited_studio_actions"
                and check["status"] == "fail"
                for check in report["checks"]
            )
        )

    def test_ack_validation_rejects_silent_action_drift(self) -> None:
        request = valid_request()
        ack = adapter.build_ack_fixture(request)
        ack["accepted_action_ids"] = ack["accepted_action_ids"][:-1]

        report = adapter.validate_ack_fixture(request, ack)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["issue_code"], "hostess.issue.staging_ack_action_mismatch")
        self.assertFalse(report["execution_performed"])

    def test_ack_builder_does_not_accept_rejected_request(self) -> None:
        request = valid_request()
        request["actions"][0]["execution_in_studio"] = True

        with self.assertRaises(ValueError):
            adapter.build_ack_fixture(request)

    def test_builds_ready_smoke_handoff_checklist_without_runtime_execution(self) -> None:
        request = valid_request()
        intake = adapter.build_intake_report(request)
        ack = adapter.build_ack_fixture(request)

        handoff = adapter.build_smoke_handoff_checklist(
            request,
            intake,
            ack,
            target_profile="hostess.t.desktop.schema_smoke",
        )

        self.assertEqual(handoff["$schema"], adapter.SMOKE_HANDOFF_SCHEMA)
        self.assertEqual(handoff["status"], "ready")
        self.assertIsNone(handoff["issue_code"])
        self.assertEqual(handoff["adapter_owner"], "rusty.hostess")
        self.assertEqual(handoff["requester_role"], "rusty.studio")
        self.assertEqual(handoff["command_session_authority"], "rusty.manifold")
        self.assertEqual(handoff["install_launch_evidence_authority"], "rusty.hostess")
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(handoff[flag], flag)
        self.assertEqual(handoff["request_action_ids"], expected_action_ids())
        self.assertEqual(handoff["accepted_action_ids"], expected_action_ids())
        self.assertEqual(
            set(handoff["required_evidence_kinds"]),
            set(adapter.SMOKE_HANDOFF_REQUIRED_EVIDENCE_KINDS),
        )
        self.assertEqual(
            [item["item_id"] for item in handoff["checklist_items"]],
            [contract["item_id"] for contract in adapter.SMOKE_HANDOFF_ITEM_CONTRACTS],
        )
        self.assertTrue(
            all(item["execution_started"] is False for item in handoff["checklist_items"])
        )
        self.assertTrue(all(check["status"] == "pass" for check in handoff["checks"]))

        validation = adapter.validate_smoke_handoff_checklist(handoff)
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["execution_performed"])

    def test_smoke_handoff_blocks_rejected_studio_request(self) -> None:
        request = valid_request()
        request["actions"][3]["route_kind"] = "hostess.stage.files_from_drifted_plan"
        intake = adapter.build_intake_report(request)

        handoff = adapter.build_smoke_handoff_checklist(request, intake, None)

        self.assertEqual(handoff["status"], "blocked")
        self.assertEqual(handoff["issue_code"], "hostess.issue.adapter_action_contract_drift")
        self.assertEqual(handoff["accepted_action_ids"], [])
        self.assertTrue(
            any(
                check["check_id"] == "hostess.check.studio_staging_smoke_handoff.intake_status"
                and check["status"] == "fail"
                for check in handoff["checks"]
            )
        )
        self.assertTrue(any(item["status"] == "blocked" for item in handoff["checklist_items"]))
        self.assertEqual(
            adapter.validate_smoke_handoff_checklist(handoff)["status"],
            "pass",
        )

    def test_smoke_handoff_validation_rejects_runtime_start_or_evidence_drift(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )

        started = copy.deepcopy(handoff)
        started["launch_started"] = True
        started_report = adapter.validate_smoke_handoff_checklist(started)
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.smoke_handoff_runtime_started",
        )

        evidence_drift = copy.deepcopy(handoff)
        evidence_drift["required_evidence_kinds"] = evidence_drift["required_evidence_kinds"][:-1]
        evidence_report = adapter.validate_smoke_handoff_checklist(evidence_drift)
        self.assertEqual(evidence_report["status"], "fail")
        self.assertEqual(
            evidence_report["issue_code"],
            "hostess.issue.smoke_handoff_evidence_kinds",
        )

    def test_builds_smoke_dry_run_request_and_receipt_without_runtime_execution(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
            target_profile="hostess.t.desktop.schema_smoke",
        )

        dry_run = adapter.build_smoke_dry_run_request(handoff)
        self.assertEqual(dry_run["$schema"], adapter.SMOKE_DRY_RUN_REQUEST_SCHEMA)
        self.assertEqual(dry_run["status"], "ready")
        self.assertEqual(dry_run["execution_policy"], "not_executed.hostess_dry_run_request_only")
        self.assertEqual(dry_run["adapter_owner"], "rusty.hostess")
        self.assertEqual(dry_run["requester_role"], "rusty.studio")
        self.assertEqual(dry_run["command_session_authority"], "rusty.manifold")
        self.assertEqual(dry_run["install_launch_evidence_authority"], "rusty.hostess")
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(dry_run[flag], flag)
        self.assertEqual(
            set(dry_run["required_receipt_kinds"]),
            set(adapter.SMOKE_DRY_RUN_REQUIRED_RECEIPT_KINDS),
        )
        self.assertEqual(
            [step["step_id"] for step in dry_run["dry_run_steps"]],
            [contract["step_id"] for contract in adapter.SMOKE_DRY_RUN_STEP_CONTRACTS],
        )
        self.assertTrue(all(step["execution_started"] is False for step in dry_run["dry_run_steps"]))
        self.assertEqual(adapter.validate_smoke_dry_run_request(dry_run)["status"], "pass")

        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        self.assertEqual(receipt["$schema"], adapter.SMOKE_DRY_RUN_RECEIPT_SCHEMA)
        self.assertEqual(receipt["status"], "accepted")
        self.assertEqual(receipt["dry_run_request_id"], dry_run["dry_run_request_id"])
        self.assertFalse(receipt["execution_performed"])
        self.assertFalse(receipt["build_started"])
        self.assertFalse(receipt["launch_started"])
        self.assertEqual(receipt["accepted_step_count"], len(dry_run["dry_run_steps"]))
        self.assertEqual(receipt["rejected_step_count"], 0)
        self.assertTrue(
            all(item["execution_performed"] is False for item in receipt["receipt_items"])
        )
        self.assertEqual(
            adapter.validate_smoke_dry_run_receipt(dry_run, receipt)["status"],
            "pass",
        )

    def test_smoke_dry_run_request_blocks_invalid_handoff(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        handoff["status"] = "ready"
        handoff["build_started"] = True

        dry_run = adapter.build_smoke_dry_run_request(handoff)
        self.assertEqual(dry_run["status"], "blocked")
        self.assertEqual(dry_run["issue_code"], "hostess.issue.smoke_handoff_runtime_started")
        self.assertTrue(any(step["status"] == "blocked" for step in dry_run["dry_run_steps"]))

        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        self.assertEqual(receipt["status"], "rejected")
        self.assertEqual(receipt["accepted_step_count"], 0)
        self.assertEqual(receipt["rejected_step_count"], len(dry_run["dry_run_steps"]))
        self.assertEqual(
            adapter.validate_smoke_dry_run_receipt(dry_run, receipt)["status"],
            "pass",
        )

    def test_smoke_dry_run_validation_rejects_runtime_or_step_drift(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)

        started = copy.deepcopy(dry_run)
        started["install_started"] = True
        started_report = adapter.validate_smoke_dry_run_request(started)
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.smoke_dry_run_runtime_started",
        )

        step_drift = copy.deepcopy(dry_run)
        step_drift["dry_run_steps"][0]["owner"] = "rusty.studio"
        step_report = adapter.validate_smoke_dry_run_request(step_drift)
        self.assertEqual(step_report["status"], "fail")
        self.assertEqual(
            step_report["issue_code"],
            "hostess.issue.smoke_dry_run_step_contract_drift",
        )

        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        receipt_drift = copy.deepcopy(receipt)
        receipt_drift["receipt_items"][0]["execution_performed"] = True
        receipt_report = adapter.validate_smoke_dry_run_receipt(dry_run, receipt_drift)
        self.assertEqual(receipt_report["status"], "fail")
        self.assertEqual(
            receipt_report["issue_code"],
            "hostess.issue.smoke_dry_run_receipt_item_executed",
        )

    def test_builds_smoke_execution_preflight_without_runtime_execution(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
            target_profile="hostess.t.desktop.schema_smoke",
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)
        receipt = adapter.build_smoke_dry_run_receipt(dry_run)

        preflight = adapter.build_smoke_execution_preflight(
            dry_run,
            receipt,
            target_profile="hostess.t.desktop.no_device_preflight",
        )

        self.assertEqual(preflight["$schema"], adapter.SMOKE_EXECUTION_PREFLIGHT_SCHEMA)
        self.assertEqual(preflight["status"], "ready")
        self.assertIsNone(preflight["issue_code"])
        self.assertEqual(preflight["execution_policy"], "not_executed.hostess_execution_preflight_only")
        self.assertEqual(preflight["adapter_owner"], "rusty.hostess")
        self.assertEqual(preflight["requester_role"], "rusty.studio")
        self.assertEqual(preflight["command_session_authority"], "rusty.manifold")
        self.assertEqual(preflight["install_launch_evidence_authority"], "rusty.hostess")
        self.assertEqual(preflight["host_shell_owner"], "rusty.hostess")
        self.assertEqual(preflight["host_shell_kind"], "hostess.t.no_device_preflight")
        self.assertFalse(preflight["device_required"])
        self.assertFalse(preflight["platform_execution_allowed"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(preflight[flag], flag)
        self.assertEqual(
            set(preflight["required_receipt_kinds"]),
            set(adapter.SMOKE_DRY_RUN_REQUIRED_RECEIPT_KINDS),
        )
        self.assertEqual(
            [capability["capability_id"] for capability in preflight["preflight_capabilities"]],
            [
                contract["capability_id"]
                for contract in adapter.SMOKE_PREFLIGHT_CAPABILITY_CONTRACTS
            ],
        )
        self.assertTrue(
            all(
                capability["status"] == "ready"
                and capability["execution_started"] is False
                and capability["device_required"] is False
                for capability in preflight["preflight_capabilities"]
            )
        )
        self.assertTrue(all(check["status"] == "pass" for check in preflight["checks"]))

        validation = adapter.validate_smoke_execution_preflight(preflight)
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["execution_performed"])

    def test_smoke_execution_preflight_blocks_rejected_receipt(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)
        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        receipt["status"] = "rejected"

        preflight = adapter.build_smoke_execution_preflight(dry_run, receipt)

        self.assertEqual(preflight["status"], "blocked")
        self.assertEqual(
            preflight["issue_code"],
            "hostess.issue.smoke_dry_run_receipt_status",
        )
        self.assertTrue(
            any(
                capability["status"] == "blocked"
                for capability in preflight["preflight_capabilities"]
            )
        )
        self.assertEqual(
            adapter.validate_smoke_execution_preflight(preflight)["status"],
            "pass",
        )

    def test_smoke_execution_preflight_validation_rejects_runtime_or_capability_drift(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)
        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        preflight = adapter.build_smoke_execution_preflight(dry_run, receipt)

        started = copy.deepcopy(preflight)
        started["launch_started"] = True
        started_report = adapter.validate_smoke_execution_preflight(started)
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.smoke_execution_preflight_runtime_started",
        )

        capability_drift = copy.deepcopy(preflight)
        capability_drift["preflight_capabilities"][0]["owner"] = "rusty.studio"
        capability_report = adapter.validate_smoke_execution_preflight(capability_drift)
        self.assertEqual(capability_report["status"], "fail")
        self.assertEqual(
            capability_report["issue_code"],
            "hostess.issue.smoke_execution_preflight_capability_drift",
        )

    def test_builds_smoke_host_shell_execution_without_platform_runtime(self) -> None:
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

        self.assertEqual(execution["$schema"], adapter.SMOKE_HOST_SHELL_EXECUTION_SCHEMA)
        self.assertEqual(execution["status"], "completed")
        self.assertIsNone(execution["issue_code"])
        self.assertEqual(execution["execution_policy"], adapter.HOST_SHELL_EXECUTION_POLICY)
        self.assertEqual(execution["executor_owner"], "rusty.hostess")
        self.assertEqual(execution["adapter_owner"], "rusty.hostess")
        self.assertEqual(execution["command_session_authority"], "rusty.manifold")
        self.assertEqual(execution["install_launch_evidence_authority"], "rusty.hostess")
        self.assertFalse(execution["execution_performed"])
        self.assertFalse(execution["runtime_execution_performed"])
        self.assertFalse(execution["platform_execution_performed"])
        self.assertTrue(execution["host_shell_harness_performed"])
        self.assertTrue(execution["schema_checks_performed"])
        self.assertFalse(execution["device_required"])
        self.assertFalse(execution["platform_execution_allowed"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(execution[flag], flag)
        self.assertEqual(
            execution["evidence_record_count"],
            len(preflight["preflight_capabilities"]),
        )
        self.assertEqual(
            execution["accepted_evidence_record_count"],
            len(preflight["preflight_capabilities"]),
        )
        self.assertEqual(execution["rejected_evidence_record_count"], 0)
        self.assertTrue(
            all(
                record["evidence_status"] == "accepted"
                and record["schema_check_performed"] is True
                and record["platform_execution_performed"] is False
                and record["runtime_execution_performed"] is False
                for record in execution["evidence_records"]
            )
        )

        validation = adapter.validate_smoke_host_shell_execution(execution)
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_smoke_host_shell_execution_blocks_invalid_preflight(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)
        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        preflight = adapter.build_smoke_execution_preflight(dry_run, receipt)
        preflight["platform_execution_allowed"] = True

        execution = adapter.build_smoke_host_shell_execution(preflight)

        self.assertEqual(execution["status"], "blocked")
        self.assertEqual(
            execution["issue_code"],
            "hostess.issue.smoke_execution_preflight_device_gate",
        )
        self.assertGreater(execution["rejected_evidence_record_count"], 0)
        self.assertEqual(
            adapter.validate_smoke_host_shell_execution(execution)["status"],
            "pass",
        )

    def test_smoke_host_shell_execution_validation_rejects_runtime_or_evidence_drift(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)
        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        preflight = adapter.build_smoke_execution_preflight(dry_run, receipt)
        execution = adapter.build_smoke_host_shell_execution(preflight)

        started = copy.deepcopy(execution)
        started["install_started"] = True
        started_report = adapter.validate_smoke_host_shell_execution(started)
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.smoke_host_shell_execution_runtime_started",
        )

        evidence_drift = copy.deepcopy(execution)
        evidence_drift["evidence_records"][0]["owner"] = "rusty.studio"
        evidence_report = adapter.validate_smoke_host_shell_execution(evidence_drift)
        self.assertEqual(evidence_report["status"], "fail")
        self.assertEqual(
            evidence_report["issue_code"],
            "hostess.issue.smoke_host_shell_evidence_contract_drift",
        )

    def test_builds_smoke_review_bundle_from_host_shell_execution(self) -> None:
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

        self.assertEqual(bundle["$schema"], adapter.SMOKE_REVIEW_BUNDLE_SCHEMA)
        self.assertEqual(bundle["status"], "reviewed")
        self.assertIsNone(bundle["issue_code"])
        self.assertEqual(bundle["execution_policy"], adapter.SMOKE_REVIEW_BUNDLE_POLICY)
        self.assertEqual(bundle["bundle_owner"], "rusty.hostess")
        self.assertEqual(bundle["reviewer_owner"], "rusty.hostess")
        self.assertEqual(bundle["source_execution_status"], "completed")
        self.assertEqual(bundle["source_execution_validation_status"], "pass")
        self.assertFalse(bundle["execution_performed"])
        self.assertFalse(bundle["runtime_execution_performed"])
        self.assertFalse(bundle["platform_execution_performed"])
        self.assertTrue(bundle["review_bundle_written"])
        self.assertFalse(bundle["device_required"])
        self.assertFalse(bundle["platform_execution_allowed"])
        self.assertFalse(bundle["studio_execution_allowed"])
        self.assertTrue(bundle["operator_review_required_before_platform_smoke"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(bundle[flag], flag)
        self.assertEqual(bundle["source_evidence_record_count"], len(execution["evidence_records"]))
        self.assertEqual(bundle["bundle_record_count"], len(execution["evidence_records"]))
        self.assertEqual(bundle["reviewed_record_count"], len(execution["evidence_records"]))
        self.assertEqual(bundle["blocked_record_count"], 0)
        self.assertTrue(
            all(
                record["review_status"] == "reviewed"
                and record["included_in_bundle"] is True
                and record["runtime_execution_performed"] is False
                and record["platform_execution_performed"] is False
                for record in bundle["bundle_records"]
            )
        )

        validation = adapter.validate_smoke_review_bundle(bundle)
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_smoke_review_bundle_blocks_invalid_host_shell_execution(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)
        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        preflight = adapter.build_smoke_execution_preflight(dry_run, receipt)
        execution = adapter.build_smoke_host_shell_execution(preflight)
        execution["platform_execution_performed"] = True

        bundle = adapter.build_smoke_review_bundle(execution)

        self.assertEqual(bundle["status"], "blocked")
        self.assertEqual(
            bundle["issue_code"],
            "hostess.issue.smoke_host_shell_execution_runtime_started",
        )
        self.assertGreater(bundle["blocked_record_count"], 0)
        self.assertEqual(
            adapter.validate_smoke_review_bundle(bundle)["status"],
            "pass",
        )

    def test_smoke_review_bundle_validation_rejects_runtime_or_record_drift(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)
        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        preflight = adapter.build_smoke_execution_preflight(dry_run, receipt)
        execution = adapter.build_smoke_host_shell_execution(preflight)
        bundle = adapter.build_smoke_review_bundle(execution)

        started = copy.deepcopy(bundle)
        started["launch_started"] = True
        started_report = adapter.validate_smoke_review_bundle(started)
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.smoke_review_bundle_runtime_started",
        )

        record_drift = copy.deepcopy(bundle)
        record_drift["bundle_records"][0]["included_in_bundle"] = False
        record_report = adapter.validate_smoke_review_bundle(record_drift)
        self.assertEqual(record_report["status"], "fail")
        self.assertEqual(
            record_report["issue_code"],
            "hostess.issue.smoke_review_bundle_reviewed_inconsistent",
        )

    def test_builds_operator_controlled_platform_smoke_plan_without_execution(self) -> None:
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

        plan = adapter.build_platform_smoke_plan(
            bundle,
            target_platform="hostess.quest.operator_controlled_smoke_plan",
        )

        self.assertEqual(plan["$schema"], adapter.PLATFORM_SMOKE_PLAN_SCHEMA)
        self.assertEqual(plan["status"], "planned")
        self.assertIsNone(plan["issue_code"])
        self.assertEqual(plan["execution_policy"], adapter.PLATFORM_SMOKE_PLAN_POLICY)
        self.assertEqual(plan["plan_owner"], "rusty.hostess")
        self.assertEqual(plan["platform_owner"], "rusty.hostess")
        self.assertEqual(plan["command_session_authority"], "rusty.manifold")
        self.assertEqual(plan["install_launch_evidence_authority"], "rusty.hostess")
        self.assertFalse(plan["device_required"])
        self.assertTrue(plan["target_device_required_for_future_execution"])
        self.assertFalse(plan["schema_path_execution_allowed"])
        self.assertFalse(plan["platform_execution_allowed"])
        self.assertFalse(plan["studio_execution_allowed"])
        self.assertTrue(plan["operator_approval_required_before_execution"])
        self.assertFalse(plan["operator_approved"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(plan[flag], flag)
        self.assertEqual(
            [action["plan_action_id"] for action in plan["planned_actions"]],
            [
                contract["plan_action_id"]
                for contract in adapter.PLATFORM_SMOKE_PLAN_ACTION_CONTRACTS
            ],
        )
        self.assertEqual(plan["planned_action_count"], len(plan["planned_actions"]))
        self.assertEqual(plan["ready_planned_action_count"], len(plan["planned_actions"]))
        self.assertEqual(plan["blocked_planned_action_count"], 0)
        self.assertEqual(plan["required_approval_count"], len(plan["planned_actions"]))
        self.assertEqual(plan["operator_approved_count"], 0)
        self.assertTrue(
            all(
                action["status"] == "planned"
                and action["approval_required"] is True
                and action["operator_approved"] is False
                and action["execution_started"] is False
                and action["platform_execution_performed"] is False
                and action["studio_execution_allowed"] is False
                for action in plan["planned_actions"]
            )
        )

        validation = adapter.validate_platform_smoke_plan(plan)
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_platform_smoke_plan_blocks_invalid_review_bundle(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)
        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        preflight = adapter.build_smoke_execution_preflight(dry_run, receipt)
        execution = adapter.build_smoke_host_shell_execution(preflight)
        bundle = adapter.build_smoke_review_bundle(execution)
        bundle["status"] = "blocked"
        bundle["issue_code"] = "hostess.issue.operator_rejected_smoke_bundle"

        plan = adapter.build_platform_smoke_plan(bundle)

        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(
            plan["issue_code"],
            "hostess.issue.operator_rejected_smoke_bundle",
        )
        self.assertGreater(plan["blocked_planned_action_count"], 0)
        self.assertEqual(adapter.validate_platform_smoke_plan(plan)["status"], "pass")

    def test_platform_smoke_plan_validation_rejects_execution_or_approval_drift(self) -> None:
        request = valid_request()
        handoff = adapter.build_smoke_handoff_checklist(
            request,
            adapter.build_intake_report(request),
            adapter.build_ack_fixture(request),
        )
        dry_run = adapter.build_smoke_dry_run_request(handoff)
        receipt = adapter.build_smoke_dry_run_receipt(dry_run)
        preflight = adapter.build_smoke_execution_preflight(dry_run, receipt)
        execution = adapter.build_smoke_host_shell_execution(preflight)
        bundle = adapter.build_smoke_review_bundle(execution)
        plan = adapter.build_platform_smoke_plan(bundle)

        started = copy.deepcopy(plan)
        started["planned_actions"][0]["execution_started"] = True
        started_report = adapter.validate_platform_smoke_plan(started)
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.platform_smoke_plan_action_started",
        )

        approved = copy.deepcopy(plan)
        approved["required_approvals"][0]["operator_approved"] = True
        approved_report = adapter.validate_platform_smoke_plan(approved)
        self.assertEqual(approved_report["status"], "fail")
        self.assertEqual(
            approved_report["issue_code"],
            "hostess.issue.platform_smoke_plan_approval_drift",
        )

    def test_builds_platform_smoke_approval_receipt_without_execution(self) -> None:
        plan = ready_platform_smoke_plan()

        receipt = adapter.build_platform_smoke_approval_receipt(plan)

        self.assertEqual(receipt["$schema"], adapter.PLATFORM_SMOKE_APPROVAL_RECEIPT_SCHEMA)
        self.assertEqual(receipt["status"], adapter.APPROVED_STATUS)
        self.assertEqual(receipt["approval_decision"], adapter.APPROVED_STATUS)
        self.assertIsNone(receipt["issue_code"])
        self.assertEqual(
            receipt["execution_policy"],
            adapter.PLATFORM_SMOKE_APPROVAL_RECEIPT_POLICY,
        )
        self.assertTrue(receipt["operator_approved"])
        self.assertTrue(receipt["future_execution_authorized"])
        self.assertFalse(receipt["schema_path_execution_allowed"])
        self.assertFalse(receipt["platform_execution_allowed"])
        self.assertFalse(receipt["studio_execution_allowed"])
        self.assertFalse(receipt["runtime_execution_performed"])
        self.assertFalse(receipt["platform_execution_performed"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(receipt[flag], flag)
        self.assertEqual(receipt["source_planned_action_count"], len(plan["planned_actions"]))
        self.assertEqual(receipt["approval_receipt_count"], len(plan["planned_actions"]))
        self.assertEqual(receipt["approved_action_count"], len(plan["planned_actions"]))
        self.assertEqual(receipt["rejected_action_count"], 0)
        self.assertTrue(
            all(
                item["approval_status"] == adapter.APPROVED_STATUS
                and item["operator_approved"] is True
                and item["future_execution_authorized"] is True
                and item["execution_started"] is False
                and item["runtime_execution_performed"] is False
                and item["platform_execution_performed"] is False
                and item["studio_execution_allowed"] is False
                for item in receipt["action_approval_receipts"]
            )
        )
        validation = adapter.validate_platform_smoke_approval_receipt(plan, receipt)
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_builds_platform_smoke_rejection_receipt_without_execution(self) -> None:
        plan = ready_platform_smoke_plan()

        receipt = adapter.build_platform_smoke_approval_receipt(
            plan,
            decision=adapter.REJECTED_STATUS,
            reason_code="hostess.issue.operator_declined_platform_smoke",
        )

        self.assertEqual(receipt["status"], adapter.REJECTED_STATUS)
        self.assertEqual(receipt["approval_decision"], adapter.REJECTED_STATUS)
        self.assertEqual(
            receipt["issue_code"],
            "hostess.issue.operator_declined_platform_smoke",
        )
        self.assertFalse(receipt["operator_approved"])
        self.assertFalse(receipt["future_execution_authorized"])
        self.assertFalse(receipt["runtime_execution_performed"])
        self.assertFalse(receipt["platform_execution_performed"])
        self.assertEqual(receipt["approved_action_count"], 0)
        self.assertEqual(receipt["rejected_action_count"], len(plan["planned_actions"]))
        self.assertTrue(
            all(
                item["approval_status"] == adapter.REJECTED_STATUS
                and item["operator_approved"] is False
                and item["future_execution_authorized"] is False
                and item["execution_started"] is False
                and item["runtime_execution_performed"] is False
                and item["platform_execution_performed"] is False
                and item["studio_execution_allowed"] is False
                for item in receipt["action_approval_receipts"]
            )
        )
        self.assertEqual(
            adapter.validate_platform_smoke_approval_receipt(plan, receipt)["status"],
            "pass",
        )

    def test_platform_smoke_approval_validation_rejects_execution_or_action_drift(self) -> None:
        plan = ready_platform_smoke_plan()
        receipt = adapter.build_platform_smoke_approval_receipt(plan)

        started = copy.deepcopy(receipt)
        started["install_started"] = True
        started_report = adapter.validate_platform_smoke_approval_receipt(plan, started)
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.platform_smoke_approval_receipt_execution_started",
        )

        route_drift = copy.deepcopy(receipt)
        route_drift["action_approval_receipts"][0]["route_kind"] = (
            "hostess.platform_smoke.drifted_route"
        )
        route_report = adapter.validate_platform_smoke_approval_receipt(plan, route_drift)
        self.assertEqual(route_report["status"], "fail")
        self.assertEqual(
            route_report["issue_code"],
            "hostess.issue.platform_smoke_approval_receipt_action_drift",
        )

    def test_builds_platform_smoke_execution_request_and_receipt_without_execution(self) -> None:
        plan = ready_platform_smoke_plan()
        approval = adapter.build_platform_smoke_approval_receipt(plan)

        execution_request = adapter.build_platform_smoke_execution_request(plan, approval)

        self.assertEqual(
            execution_request["$schema"],
            adapter.PLATFORM_SMOKE_EXECUTION_REQUEST_SCHEMA,
        )
        self.assertEqual(execution_request["status"], adapter.READY_STATUS)
        self.assertIsNone(execution_request["issue_code"])
        self.assertEqual(
            execution_request["execution_policy"],
            adapter.PLATFORM_SMOKE_EXECUTION_REQUEST_POLICY,
        )
        self.assertEqual(execution_request["request_owner"], "rusty.hostess")
        self.assertEqual(execution_request["execution_owner"], "rusty.hostess")
        self.assertEqual(execution_request["command_session_authority"], "rusty.manifold")
        self.assertEqual(execution_request["install_launch_evidence_authority"], "rusty.hostess")
        self.assertFalse(execution_request["device_required"])
        self.assertTrue(execution_request["target_device_required_for_future_execution"])
        self.assertFalse(execution_request["schema_path_execution_allowed"])
        self.assertFalse(execution_request["platform_execution_allowed"])
        self.assertFalse(execution_request["studio_execution_allowed"])
        self.assertTrue(execution_request["operator_approved"])
        self.assertTrue(execution_request["future_execution_authorized"])
        self.assertTrue(execution_request["operator_controlled_execution_required"])
        self.assertTrue(execution_request["hostess_shell_execution_required"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(execution_request[flag], flag)
        self.assertFalse(execution_request["runtime_execution_performed"])
        self.assertFalse(execution_request["platform_execution_performed"])
        self.assertEqual(
            execution_request["execution_action_request_count"],
            len(approval["action_approval_receipts"]),
        )
        self.assertEqual(
            execution_request["pending_execution_action_count"],
            len(approval["action_approval_receipts"]),
        )
        self.assertEqual(execution_request["rejected_execution_action_count"], 0)
        self.assertTrue(
            all(
                action["execution_request_status"] == adapter.PENDING_STATUS
                and action["execution_requested"] is True
                and action["execution_started"] is False
                and action["runtime_execution_performed"] is False
                and action["platform_execution_performed"] is False
                and action["studio_execution_allowed"] is False
                for action in execution_request["execution_action_requests"]
            )
        )
        request_validation = adapter.validate_platform_smoke_execution_request(
            plan,
            approval,
            execution_request,
        )
        self.assertEqual(request_validation["status"], "pass")
        self.assertFalse(request_validation["runtime_execution_performed"])
        self.assertFalse(request_validation["platform_execution_performed"])

        execution_receipt = adapter.build_platform_smoke_execution_receipt(
            plan,
            approval,
            execution_request,
        )

        self.assertEqual(
            execution_receipt["$schema"],
            adapter.PLATFORM_SMOKE_EXECUTION_RECEIPT_SCHEMA,
        )
        self.assertEqual(execution_receipt["status"], adapter.PENDING_STATUS)
        self.assertEqual(
            execution_receipt["execution_policy"],
            adapter.PLATFORM_SMOKE_EXECUTION_RECEIPT_POLICY,
        )
        self.assertTrue(execution_receipt["execution_acknowledged"])
        self.assertTrue(execution_receipt["schema_checks_performed"])
        self.assertFalse(execution_receipt["device_required"])
        self.assertFalse(execution_receipt["schema_path_execution_allowed"])
        self.assertFalse(execution_receipt["platform_execution_allowed"])
        self.assertFalse(execution_receipt["studio_execution_allowed"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(execution_receipt[flag], flag)
        self.assertFalse(execution_receipt["runtime_execution_performed"])
        self.assertFalse(execution_receipt["platform_execution_performed"])
        self.assertEqual(
            execution_receipt["pending_execution_action_count"],
            len(execution_request["execution_action_requests"]),
        )
        self.assertEqual(execution_receipt["rejected_execution_action_count"], 0)
        self.assertTrue(
            all(
                receipt["execution_receipt_status"] == adapter.PENDING_STATUS
                and receipt["execution_acknowledged"] is True
                and receipt["execution_started"] is False
                and receipt["runtime_execution_performed"] is False
                and receipt["platform_execution_performed"] is False
                and receipt["studio_execution_allowed"] is False
                for receipt in execution_receipt["execution_action_receipts"]
            )
        )
        receipt_validation = adapter.validate_platform_smoke_execution_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
        )
        self.assertEqual(receipt_validation["status"], "pass")
        self.assertFalse(receipt_validation["runtime_execution_performed"])
        self.assertFalse(receipt_validation["platform_execution_performed"])

    def test_platform_smoke_execution_request_blocks_rejected_approval(self) -> None:
        plan = ready_platform_smoke_plan()
        approval = adapter.build_platform_smoke_approval_receipt(
            plan,
            decision=adapter.REJECTED_STATUS,
            reason_code="hostess.issue.operator_declined_platform_smoke",
        )

        execution_request = adapter.build_platform_smoke_execution_request(plan, approval)

        self.assertEqual(execution_request["status"], adapter.REJECTED_STATUS)
        self.assertEqual(
            execution_request["issue_code"],
            "hostess.issue.operator_declined_platform_smoke",
        )
        self.assertFalse(execution_request["operator_approved"])
        self.assertFalse(execution_request["future_execution_authorized"])
        self.assertFalse(execution_request["hostess_shell_execution_required"])
        self.assertEqual(execution_request["pending_execution_action_count"], 0)
        self.assertEqual(
            execution_request["rejected_execution_action_count"],
            len(approval["action_approval_receipts"]),
        )
        self.assertEqual(
            adapter.validate_platform_smoke_execution_request(
                plan,
                approval,
                execution_request,
            )["status"],
            "pass",
        )

        execution_receipt = adapter.build_platform_smoke_execution_receipt(
            plan,
            approval,
            execution_request,
        )
        self.assertEqual(execution_receipt["status"], adapter.REJECTED_STATUS)
        self.assertFalse(execution_receipt["execution_acknowledged"])
        self.assertFalse(execution_receipt["platform_execution_performed"])
        self.assertEqual(
            adapter.validate_platform_smoke_execution_receipt(
                plan,
                approval,
                execution_request,
                execution_receipt,
            )["status"],
            "pass",
        )

    def test_platform_smoke_execution_validations_reject_action_or_runtime_drift(self) -> None:
        plan = ready_platform_smoke_plan()
        approval = adapter.build_platform_smoke_approval_receipt(plan)
        execution_request = adapter.build_platform_smoke_execution_request(plan, approval)

        route_drift = copy.deepcopy(execution_request)
        route_drift["execution_action_requests"][0]["owner"] = "rusty.studio"
        route_drift["execution_action_requests"][0]["route_kind"] = (
            "studio.platform_smoke.copy_stage_files"
        )
        route_drift["execution_action_requests"][0]["expected_input_kind"] = (
            "studio_owned_input"
        )
        route_report = adapter.validate_platform_smoke_execution_request(
            plan,
            approval,
            route_drift,
        )
        self.assertEqual(route_report["status"], "fail")
        self.assertEqual(
            route_report["issue_code"],
            "hostess.issue.platform_smoke_execution_request_action_drift",
        )

        started = copy.deepcopy(execution_request)
        started["copy_started"] = True
        started_report = adapter.validate_platform_smoke_execution_request(
            plan,
            approval,
            started,
        )
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.platform_smoke_execution_request_execution_started",
        )

        execution_receipt = adapter.build_platform_smoke_execution_receipt(
            plan,
            approval,
            execution_request,
        )
        receipt_drift = copy.deepcopy(execution_receipt)
        receipt_drift["execution_action_receipts"][0]["platform_execution_performed"] = True
        receipt_report = adapter.validate_platform_smoke_execution_receipt(
            plan,
            approval,
            execution_request,
            receipt_drift,
        )
        self.assertEqual(receipt_report["status"], "fail")
        self.assertEqual(
            receipt_report["issue_code"],
            "hostess.issue.platform_smoke_execution_receipt_action_drift",
        )

    def test_builds_platform_smoke_operator_start_gate_without_execution(self) -> None:
        plan, approval, execution_request, execution_receipt = ready_platform_smoke_execution_chain()

        gate = adapter.build_platform_smoke_operator_start_gate(
            plan,
            approval,
            execution_request,
            execution_receipt,
            host_shell_kind="hostess.t.quest_host_shell.schema_gate",
        )

        self.assertEqual(gate["$schema"], adapter.PLATFORM_SMOKE_OPERATOR_START_GATE_SCHEMA)
        self.assertEqual(gate["status"], adapter.READY_STATUS)
        self.assertIsNone(gate["issue_code"])
        self.assertEqual(gate["execution_policy"], adapter.PLATFORM_SMOKE_OPERATOR_START_GATE_POLICY)
        self.assertEqual(gate["gate_owner"], "rusty.hostess")
        self.assertEqual(gate["operator_start_owner"], "rusty.hostess")
        self.assertEqual(gate["host_shell_owner"], "rusty.hostess")
        self.assertEqual(gate["command_session_authority"], "rusty.manifold")
        self.assertEqual(gate["install_launch_evidence_authority"], "rusty.hostess")
        self.assertFalse(gate["device_required"])
        self.assertTrue(gate["target_device_required_for_future_execution"])
        self.assertTrue(gate["operator_approval_required"])
        self.assertTrue(gate["operator_start_required"])
        self.assertFalse(gate["operator_started"])
        self.assertFalse(gate["operator_start_acknowledged"])
        self.assertFalse(gate["host_shell_started"])
        self.assertFalse(gate["schema_path_execution_allowed"])
        self.assertFalse(gate["platform_execution_allowed"])
        self.assertFalse(gate["studio_execution_allowed"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(gate[flag], flag)
        self.assertFalse(gate["runtime_execution_performed"])
        self.assertFalse(gate["platform_execution_performed"])
        self.assertEqual(
            gate["operator_start_action_gate_count"],
            len(execution_receipt["execution_action_receipts"]),
        )
        self.assertEqual(
            gate["pending_operator_start_action_count"],
            len(execution_receipt["execution_action_receipts"]),
        )
        self.assertEqual(gate["rejected_operator_start_action_count"], 0)
        self.assertEqual(
            gate["operator_start_request_template"]["$schema"],
            adapter.OPERATOR_START_REQUEST_TEMPLATE_SCHEMA,
        )
        self.assertEqual(
            gate["operator_start_ack_template"]["$schema"],
            adapter.OPERATOR_START_ACK_TEMPLATE_SCHEMA,
        )
        self.assertEqual(
            gate["operator_start_reject_template"]["$schema"],
            adapter.OPERATOR_START_REJECT_TEMPLATE_SCHEMA,
        )
        self.assertEqual(
            len(gate["expected_evidence_receipt_templates"]),
            len(gate["operator_start_action_gates"]),
        )
        self.assertTrue(
            all(
                action["operator_start_gate_status"] == adapter.PENDING_STATUS
                and action["operator_start_required"] is True
                and action["operator_started"] is False
                and action["execution_started"] is False
                and action["runtime_execution_performed"] is False
                and action["platform_execution_performed"] is False
                and action["studio_execution_allowed"] is False
                for action in gate["operator_start_action_gates"]
            )
        )
        self.assertTrue(
            all(
                template["$schema"] == adapter.PLATFORM_SMOKE_EVIDENCE_RECEIPT_TEMPLATE_SCHEMA
                and template["evidence_receipt_status"] == adapter.PENDING_STATUS
                and template["operator_started"] is False
                and template["execution_started"] is False
                and template["platform_execution_performed"] is False
                for template in gate["expected_evidence_receipt_templates"]
            )
        )

        validation = adapter.validate_platform_smoke_operator_start_gate(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_platform_smoke_operator_start_gate_blocks_rejected_execution_receipt(self) -> None:
        plan = ready_platform_smoke_plan()
        approval = adapter.build_platform_smoke_approval_receipt(
            plan,
            decision=adapter.REJECTED_STATUS,
            reason_code="hostess.issue.operator_declined_platform_smoke",
        )
        execution_request = adapter.build_platform_smoke_execution_request(plan, approval)
        execution_receipt = adapter.build_platform_smoke_execution_receipt(
            plan,
            approval,
            execution_request,
        )

        gate = adapter.build_platform_smoke_operator_start_gate(
            plan,
            approval,
            execution_request,
            execution_receipt,
        )

        self.assertEqual(gate["status"], adapter.REJECTED_STATUS)
        self.assertEqual(
            gate["issue_code"],
            "hostess.issue.operator_declined_platform_smoke",
        )
        self.assertFalse(gate["operator_start_required"])
        self.assertFalse(gate["host_shell_execution_required"])
        self.assertEqual(gate["pending_operator_start_action_count"], 0)
        self.assertEqual(
            gate["rejected_operator_start_action_count"],
            len(execution_receipt["execution_action_receipts"]),
        )
        self.assertEqual(
            adapter.validate_platform_smoke_operator_start_gate(
                plan,
                approval,
                execution_request,
                execution_receipt,
                gate,
            )["status"],
            "pass",
        )

    def test_platform_smoke_operator_start_gate_validation_rejects_start_or_template_drift(self) -> None:
        plan, approval, execution_request, execution_receipt = ready_platform_smoke_execution_chain()
        gate = adapter.build_platform_smoke_operator_start_gate(
            plan,
            approval,
            execution_request,
            execution_receipt,
        )

        started = copy.deepcopy(gate)
        started["operator_started"] = True
        started_report = adapter.validate_platform_smoke_operator_start_gate(
            plan,
            approval,
            execution_request,
            execution_receipt,
            started,
        )
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.platform_smoke_operator_start_gate_execution_started",
        )

        action_drift = copy.deepcopy(gate)
        action_drift["operator_start_action_gates"][0]["route_kind"] = (
            "studio.platform_smoke.start_copy"
        )
        action_drift["operator_start_action_gates"][0]["owner"] = "rusty.studio"
        action_report = adapter.validate_platform_smoke_operator_start_gate(
            plan,
            approval,
            execution_request,
            execution_receipt,
            action_drift,
        )
        self.assertEqual(action_report["status"], "fail")
        self.assertEqual(
            action_report["issue_code"],
            "hostess.issue.platform_smoke_operator_start_gate_action_drift",
        )

        template_drift = copy.deepcopy(gate)
        template_drift["operator_start_ack_template"]["accepted_action_gate_ids"] = [
            gate["operator_start_action_gates"][0]["action_gate_id"]
        ]
        template_report = adapter.validate_platform_smoke_operator_start_gate(
            plan,
            approval,
            execution_request,
            execution_receipt,
            template_drift,
        )
        self.assertEqual(template_report["status"], "fail")
        self.assertEqual(
            template_report["issue_code"],
            "hostess.issue.platform_smoke_operator_start_gate_template_drift",
        )

    def test_builds_platform_smoke_operator_start_preflight_receipt_without_execution(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
        ) = ready_platform_smoke_operator_start_chain()

        receipt = adapter.build_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
        )

        self.assertEqual(
            receipt["$schema"],
            adapter.PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_SCHEMA,
        )
        self.assertEqual(receipt["status"], adapter.APPROVED_STATUS)
        self.assertEqual(receipt["preflight_decision"], adapter.APPROVED_STATUS)
        self.assertIsNone(receipt["issue_code"])
        self.assertEqual(
            receipt["execution_policy"],
            adapter.PLATFORM_SMOKE_OPERATOR_START_PREFLIGHT_RECEIPT_POLICY,
        )
        self.assertEqual(receipt["receipt_owner"], "rusty.hostess")
        self.assertEqual(receipt["preflight_owner"], "rusty.hostess")
        self.assertEqual(receipt["operator_start_owner"], "rusty.hostess")
        self.assertEqual(receipt["host_shell_owner"], "rusty.hostess")
        self.assertEqual(receipt["command_session_authority"], "rusty.manifold")
        self.assertEqual(receipt["install_launch_evidence_authority"], "rusty.hostess")
        self.assertFalse(receipt["device_required"])
        self.assertTrue(receipt["target_device_required_for_future_execution"])
        self.assertTrue(receipt["operator_approved"])
        self.assertTrue(receipt["operator_start_preflight_approved"])
        self.assertTrue(receipt["operator_start_required"])
        self.assertTrue(receipt["host_shell_execution_required"])
        self.assertFalse(receipt["operator_started"])
        self.assertFalse(receipt["host_shell_started"])
        self.assertFalse(receipt["schema_path_execution_allowed"])
        self.assertFalse(receipt["platform_execution_allowed"])
        self.assertFalse(receipt["studio_execution_allowed"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(receipt[flag], flag)
        self.assertFalse(receipt["runtime_execution_performed"])
        self.assertFalse(receipt["platform_execution_performed"])
        self.assertEqual(
            receipt["readiness_input_count"],
            len(adapter.OPERATOR_START_READINESS_INPUT_CONTRACTS),
        )
        self.assertEqual(
            receipt["approved_readiness_input_count"],
            len(adapter.OPERATOR_START_READINESS_INPUT_CONTRACTS),
        )
        self.assertEqual(receipt["rejected_readiness_input_count"], 0)
        self.assertTrue(
            any(
                item["readiness_input_id"] == "hostess.operator_start.toolchain_readiness"
                for item in receipt["readiness_inputs"]
            )
        )
        self.assertTrue(
            any(
                item["readiness_input_id"] == "hostess.operator_start.device_readiness"
                for item in receipt["readiness_inputs"]
            )
        )
        self.assertEqual(
            receipt["operator_start_action_decision_receipt_count"],
            len(gate["operator_start_action_gates"]),
        )
        self.assertEqual(
            receipt["approved_operator_start_action_count"],
            len(gate["operator_start_action_gates"]),
        )
        self.assertEqual(receipt["rejected_operator_start_action_count"], 0)
        self.assertTrue(
            all(
                action["decision_status"] == adapter.APPROVED_STATUS
                and action["operator_started"] is False
                and action["execution_started"] is False
                and action["runtime_execution_performed"] is False
                and action["platform_execution_performed"] is False
                and action["studio_execution_allowed"] is False
                for action in receipt["operator_start_action_decision_receipts"]
            )
        )
        self.assertTrue(
            all(
                item["readiness_status"] == adapter.APPROVED_STATUS
                and item["operator_supplied"] is False
                and item["validated_for_execution"] is False
                and item["operator_started"] is False
                and item["execution_started"] is False
                for item in receipt["readiness_inputs"]
            )
        )

        validation = adapter.validate_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            receipt,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_operator_start_preflight_accepts_required_pmb_shell_handoff_review(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
        ) = ready_platform_smoke_operator_start_chain()

        receipt = adapter.build_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            pmb_shell_handoff_review=ready_pmb_shell_handoff_review(),
            require_pmb_shell_handoff_review=True,
        )

        self.assertEqual(receipt["status"], adapter.APPROVED_STATUS)
        self.assertTrue(receipt["pmb_shell_handoff_review_required"])
        self.assertTrue(receipt["pmb_shell_handoff_review_ready"])
        self.assertIsNone(receipt["source_pmb_shell_handoff_review_issue_code"])
        self.assertEqual(
            receipt["readiness_input_count"],
            len(adapter.OPERATOR_START_READINESS_INPUT_CONTRACTS) + 1,
        )
        self.assertEqual(
            receipt["approved_readiness_input_count"],
            len(adapter.OPERATOR_START_READINESS_INPUT_CONTRACTS) + 1,
        )
        pmb_input = next(
            item
            for item in receipt["readiness_inputs"]
            if item["readiness_input_id"]
            == adapter.PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        )
        self.assertEqual(pmb_input["owner"], "rusty.studio")
        self.assertEqual(pmb_input["readiness_status"], adapter.APPROVED_STATUS)
        self.assertEqual(
            pmb_input["source_pmb_shell_handoff_review_schema"],
            adapter.STUDIO_PMB_SHELL_HANDOFF_REVIEW_SCHEMA,
        )
        self.assertEqual(pmb_input["source_pmb_runtime_authority"], "rusty.manifold")
        self.assertEqual(pmb_input["source_pmb_authoring_authority"], "rusty.studio")
        self.assertEqual(
            pmb_input["source_pmb_platform_validation_authority"],
            "rusty.hostess",
        )
        self.assertFalse(pmb_input["source_pmb_downstream_shell_runtime_used"])
        self.assertFalse(pmb_input["source_pmb_legacy_app_dependency_used"])
        self.assertTrue(adapter.pmb_shell_handoff_readiness_input_summary_valid(pmb_input))

        validation = adapter.validate_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            receipt,
            require_pmb_shell_handoff_review=True,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_operator_start_preflight_rejects_missing_or_blocked_required_pmb_review(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
        ) = ready_platform_smoke_operator_start_chain()

        missing = adapter.build_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            require_pmb_shell_handoff_review=True,
        )
        self.assertEqual(missing["status"], adapter.REJECTED_STATUS)
        self.assertEqual(
            missing["issue_code"],
            "hostess.issue.pmb_shell_handoff_review_missing",
        )
        self.assertFalse(missing["operator_start_required"])
        self.assertFalse(missing["operator_started"])
        self.assertFalse(missing["host_shell_started"])
        pmb_missing_input = next(
            item
            for item in missing["readiness_inputs"]
            if item["readiness_input_id"]
            == adapter.PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        )
        self.assertEqual(pmb_missing_input["readiness_status"], adapter.REJECTED_STATUS)
        self.assertEqual(
            pmb_missing_input["issue_code"],
            "hostess.issue.pmb_shell_handoff_review_missing",
        )
        self.assertEqual(
            adapter.validate_platform_smoke_operator_start_preflight_receipt(
                plan,
                approval,
                execution_request,
                execution_receipt,
                gate,
                missing,
                require_pmb_shell_handoff_review=True,
            )["status"],
            "pass",
        )

        blocked_review = ready_pmb_shell_handoff_review()
        blocked_review["status"] = "blocked"
        blocked_review["issue_code"] = (
            "studio.issue.projected_motion_breath_shell_handoff_required_bindings"
        )
        blocked = adapter.build_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            pmb_shell_handoff_review=blocked_review,
        )
        self.assertEqual(blocked["status"], adapter.REJECTED_STATUS)
        self.assertEqual(
            blocked["issue_code"],
            "studio.issue.projected_motion_breath_shell_handoff_required_bindings",
        )
        self.assertFalse(blocked["operator_start_required"])
        self.assertFalse(blocked["platform_execution_performed"])

    def test_platform_smoke_operator_start_preflight_rejection_receipt_without_execution(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
        ) = ready_platform_smoke_operator_start_chain()

        receipt = adapter.build_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            decision=adapter.REJECTED_STATUS,
            reason_code="hostess.issue.operator_declined_operator_start_preflight",
        )

        self.assertEqual(receipt["status"], adapter.REJECTED_STATUS)
        self.assertEqual(receipt["preflight_decision"], adapter.REJECTED_STATUS)
        self.assertEqual(
            receipt["issue_code"],
            "hostess.issue.operator_declined_operator_start_preflight",
        )
        self.assertFalse(receipt["operator_approved"])
        self.assertFalse(receipt["operator_start_preflight_approved"])
        self.assertFalse(receipt["operator_start_required"])
        self.assertFalse(receipt["host_shell_execution_required"])
        self.assertFalse(receipt["operator_started"])
        self.assertFalse(receipt["host_shell_started"])
        self.assertFalse(receipt["execution_performed"])
        self.assertFalse(receipt["platform_execution_performed"])
        self.assertEqual(receipt["approved_readiness_input_count"], 0)
        self.assertEqual(
            receipt["rejected_readiness_input_count"],
            len(adapter.OPERATOR_START_READINESS_INPUT_CONTRACTS),
        )
        self.assertEqual(receipt["approved_operator_start_action_count"], 0)
        self.assertEqual(
            receipt["rejected_operator_start_action_count"],
            len(gate["operator_start_action_gates"]),
        )
        self.assertTrue(
            all(
                item["readiness_status"] == adapter.REJECTED_STATUS
                and item["issue_code"]
                == "hostess.issue.operator_declined_operator_start_preflight"
                and item["operator_started"] is False
                for item in receipt["readiness_inputs"]
            )
        )
        self.assertTrue(
            all(
                action["decision_status"] == adapter.REJECTED_STATUS
                and action["issue_code"]
                == "hostess.issue.operator_declined_operator_start_preflight"
                and action["operator_started"] is False
                for action in receipt["operator_start_action_decision_receipts"]
            )
        )
        self.assertEqual(
            adapter.validate_platform_smoke_operator_start_preflight_receipt(
                plan,
                approval,
                execution_request,
                execution_receipt,
                gate,
                receipt,
            )["status"],
            "pass",
        )

    def test_platform_smoke_operator_start_preflight_validation_rejects_start_or_contract_drift(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
        ) = ready_platform_smoke_operator_start_chain()
        receipt = adapter.build_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
        )

        started = copy.deepcopy(receipt)
        started["operator_started"] = True
        started_report = adapter.validate_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            started,
        )
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.platform_smoke_operator_start_preflight_execution_started",
        )

        readiness_drift = copy.deepcopy(receipt)
        readiness_drift["readiness_inputs"][0]["owner"] = "rusty.studio"
        readiness_drift["readiness_inputs"][0]["input_kind"] = "studio_owned_input"
        readiness_report = adapter.validate_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            readiness_drift,
        )
        self.assertEqual(readiness_report["status"], "fail")
        self.assertEqual(
            readiness_report["issue_code"],
            "hostess.issue.platform_smoke_operator_start_preflight_readiness_drift",
        )

        action_drift = copy.deepcopy(receipt)
        action_drift["operator_start_action_decision_receipts"][0]["owner"] = "rusty.studio"
        action_drift["operator_start_action_decision_receipts"][0]["route_kind"] = (
            "studio.platform_smoke.operator_start"
        )
        action_report = adapter.validate_platform_smoke_operator_start_preflight_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            action_drift,
        )
        self.assertEqual(action_report["status"], "fail")
        self.assertEqual(
            action_report["issue_code"],
            "hostess.issue.platform_smoke_operator_start_preflight_action_drift",
        )

    def test_builds_platform_smoke_execution_report_without_studio_or_schema_execution(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
        ) = ready_platform_smoke_operator_start_preflight_chain()

        report = adapter.build_platform_smoke_execution_report(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
        )

        self.assertEqual(report["$schema"], adapter.PLATFORM_SMOKE_EXECUTION_REPORT_SCHEMA)
        self.assertEqual(report["status"], adapter.COMPLETED_STATUS)
        self.assertIsNone(report["issue_code"])
        self.assertEqual(
            report["execution_policy"],
            adapter.PLATFORM_SMOKE_EXECUTION_REPORT_POLICY,
        )
        self.assertEqual(report["report_owner"], "rusty.hostess")
        self.assertEqual(report["operator_start_owner"], "rusty.hostess")
        self.assertEqual(report["host_shell_owner"], "rusty.hostess")
        self.assertEqual(report["command_session_authority"], "rusty.manifold")
        self.assertEqual(report["install_launch_evidence_authority"], "rusty.hostess")
        self.assertTrue(report["operator_start_preflight_approved"])
        self.assertTrue(report["operator_started_outside_studio"])
        self.assertTrue(report["operator_start_acknowledged"])
        self.assertTrue(report["host_shell_started_outside_studio"])
        self.assertTrue(report["host_shell_reported"])
        self.assertTrue(report["requires_external_evidence"])
        self.assertFalse(report["device_required"])
        self.assertFalse(report["schema_path_execution_allowed"])
        self.assertFalse(report["platform_execution_allowed"])
        self.assertFalse(report["studio_execution_allowed"])
        self.assertFalse(report["real_platform_execution_evidence_attached"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(report[flag], flag)
        self.assertFalse(report["runtime_execution_performed"])
        self.assertFalse(report["platform_execution_performed"])
        self.assertEqual(
            report["action_report_count"],
            len(preflight["operator_start_action_decision_receipts"]),
        )
        self.assertEqual(
            report["completed_action_report_count"],
            len(preflight["operator_start_action_decision_receipts"]),
        )
        self.assertEqual(report["rejected_action_report_count"], 0)
        self.assertEqual(
            report["readiness_result_count"],
            len(preflight["readiness_inputs"]),
        )
        self.assertEqual(
            report["completed_readiness_result_count"],
            len(preflight["readiness_inputs"]),
        )
        self.assertEqual(
            report["evidence_placeholder_count"],
            len(report["action_reports"]),
        )
        self.assertTrue(
            all(
                action["reported_status"] == adapter.COMPLETED_STATUS
                and action["operator_started_outside_studio"] is True
                and action["host_shell_reported"] is True
                and action["requires_external_evidence"] is True
                and action["studio_execution_allowed"] is False
                and action["schema_path_execution_allowed"] is False
                and action["execution_started"] is False
                and action["runtime_execution_performed"] is False
                and action["platform_execution_performed"] is False
                and action["real_platform_execution_evidence_attached"] is False
                for action in report["action_reports"]
            )
        )
        self.assertTrue(
            all(
                item["result_status"] == adapter.COMPLETED_STATUS
                and item["operator_supplied"] is True
                and item["validated_for_report"] is True
                and item["validated_for_execution"] is False
                and item["schema_path_execution_allowed"] is False
                and item["execution_started"] is False
                for item in report["readiness_results"]
            )
        )
        self.assertTrue(
            all(
                placeholder["evidence_status"] == adapter.PENDING_STATUS
                and placeholder["collected"] is False
                and placeholder["attached"] is False
                and placeholder["collection_started"] is False
                and placeholder["requires_external_attachment"] is True
                and placeholder["schema_path_execution_allowed"] is False
                and placeholder["runtime_execution_performed"] is False
                and placeholder["platform_execution_performed"] is False
                for placeholder in report["evidence_placeholders"]
            )
        )

        validation = adapter.validate_platform_smoke_execution_report(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            report,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])
        self.assertFalse(validation["real_platform_execution_evidence_attached"])

    def test_platform_smoke_execution_report_preserves_pmb_shell_handoff_gate(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
        ) = ready_platform_smoke_operator_start_chain()
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

        self.assertEqual(report["status"], adapter.COMPLETED_STATUS)
        self.assertTrue(report["pmb_shell_handoff_review_required"])
        self.assertTrue(report["pmb_shell_handoff_review_ready"])
        self.assertEqual(
            report["source_pmb_shell_handoff_review_schema"],
            adapter.STUDIO_PMB_SHELL_HANDOFF_REVIEW_SCHEMA,
        )
        self.assertEqual(
            report["source_pmb_shell_handoff_review_status"],
            adapter.READY_STATUS,
        )
        self.assertIsNone(report["source_pmb_shell_handoff_review_issue_code"])
        self.assertEqual(
            report["source_pmb_shell_handoff_id"],
            "shell_handoff.projected_motion_breath.loopback",
        )
        self.assertEqual(report["source_pmb_runtime_authority"], "rusty.manifold")
        self.assertEqual(report["source_pmb_authoring_authority"], "rusty.studio")
        self.assertEqual(
            report["source_pmb_platform_validation_authority"],
            "rusty.hostess",
        )
        self.assertFalse(report["source_pmb_downstream_shell_runtime_used"])
        self.assertFalse(report["source_pmb_legacy_app_dependency_used"])

        pmb_result = next(
            item
            for item in report["readiness_results"]
            if item["source_readiness_input_id"]
            == adapter.PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        )
        self.assertEqual(pmb_result["result_status"], adapter.COMPLETED_STATUS)
        self.assertEqual(
            pmb_result["source_pmb_shell_handoff_review_schema"],
            adapter.STUDIO_PMB_SHELL_HANDOFF_REVIEW_SCHEMA,
        )
        self.assertEqual(
            pmb_result["source_pmb_shell_handoff_review_status"],
            adapter.READY_STATUS,
        )
        self.assertTrue(adapter.pmb_shell_handoff_readiness_result_summary_valid(pmb_result))

        validation = adapter.validate_platform_smoke_execution_report(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            report,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(validation["pmb_shell_handoff_review_required"])
        self.assertTrue(validation["pmb_shell_handoff_review_ready"])
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])

    def test_platform_smoke_execution_report_rejection_without_execution(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
        ) = ready_platform_smoke_operator_start_preflight_chain()

        report = adapter.build_platform_smoke_execution_report(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            outcome=adapter.REJECTED_STATUS,
            reason_code="hostess.issue.operator_declined_platform_smoke_execution_report",
        )

        self.assertEqual(report["status"], adapter.REJECTED_STATUS)
        self.assertEqual(
            report["issue_code"],
            "hostess.issue.operator_declined_platform_smoke_execution_report",
        )
        self.assertFalse(report["operator_start_preflight_approved"])
        self.assertFalse(report["operator_started_outside_studio"])
        self.assertFalse(report["operator_start_acknowledged"])
        self.assertFalse(report["host_shell_started_outside_studio"])
        self.assertFalse(report["host_shell_reported"])
        self.assertFalse(report["execution_performed"])
        self.assertFalse(report["runtime_execution_performed"])
        self.assertFalse(report["platform_execution_performed"])
        self.assertFalse(report["real_platform_execution_evidence_attached"])
        self.assertEqual(report["completed_action_report_count"], 0)
        self.assertEqual(
            report["rejected_action_report_count"],
            len(preflight["operator_start_action_decision_receipts"]),
        )
        self.assertEqual(report["completed_readiness_result_count"], 0)
        self.assertEqual(
            report["rejected_readiness_result_count"],
            len(preflight["readiness_inputs"]),
        )
        self.assertTrue(
            all(
                action["reported_status"] == adapter.REJECTED_STATUS
                and action["issue_code"]
                == "hostess.issue.operator_declined_platform_smoke_execution_report"
                and action["operator_started_outside_studio"] is False
                and action["execution_started"] is False
                for action in report["action_reports"]
            )
        )
        self.assertTrue(
            all(
                placeholder["evidence_status"] == adapter.PENDING_STATUS
                and placeholder["collected"] is False
                and placeholder["attached"] is False
                for placeholder in report["evidence_placeholders"]
            )
        )
        self.assertEqual(
            adapter.validate_platform_smoke_execution_report(
                plan,
                approval,
                execution_request,
                execution_receipt,
                gate,
                preflight,
                report,
            )["status"],
            "pass",
        )

    def test_platform_smoke_execution_report_validation_rejects_execution_or_contract_drift(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
        ) = ready_platform_smoke_operator_start_preflight_chain()
        report = adapter.build_platform_smoke_execution_report(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
        )

        started = copy.deepcopy(report)
        started["schema_path_execution_allowed"] = True
        started_report = adapter.validate_platform_smoke_execution_report(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            started,
        )
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.platform_smoke_execution_report_execution_started",
        )

        action_drift = copy.deepcopy(report)
        action_drift["action_reports"][0]["owner"] = "rusty.studio"
        action_drift["action_reports"][0]["route_kind"] = "studio.platform_smoke.launch"
        action_drift["action_reports"][0]["expected_input_kind"] = "studio_owned_input"
        action_report = adapter.validate_platform_smoke_execution_report(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            action_drift,
        )
        self.assertEqual(action_report["status"], "fail")
        self.assertEqual(
            action_report["issue_code"],
            "hostess.issue.platform_smoke_execution_report_action_drift",
        )

        readiness_drift = copy.deepcopy(report)
        readiness_drift["readiness_results"][0]["owner"] = "rusty.studio"
        readiness_drift["readiness_results"][0]["input_kind"] = "studio_owned_input"
        readiness_report = adapter.validate_platform_smoke_execution_report(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            readiness_drift,
        )
        self.assertEqual(readiness_report["status"], "fail")
        self.assertEqual(
            readiness_report["issue_code"],
            "hostess.issue.platform_smoke_execution_report_readiness_drift",
        )

        (
            pmb_plan,
            pmb_approval,
            pmb_execution_request,
            pmb_execution_receipt,
            pmb_gate,
        ) = ready_platform_smoke_operator_start_chain()
        pmb_preflight = adapter.build_platform_smoke_operator_start_preflight_receipt(
            pmb_plan,
            pmb_approval,
            pmb_execution_request,
            pmb_execution_receipt,
            pmb_gate,
            pmb_shell_handoff_review=ready_pmb_shell_handoff_review(),
            require_pmb_shell_handoff_review=True,
        )
        pmb_report = adapter.build_platform_smoke_execution_report(
            pmb_plan,
            pmb_approval,
            pmb_execution_request,
            pmb_execution_receipt,
            pmb_gate,
            pmb_preflight,
        )
        pmb_drift = copy.deepcopy(pmb_report)
        pmb_drift["pmb_shell_handoff_review_ready"] = False
        pmb_drift["readiness_results"] = [
            item
            for item in pmb_drift["readiness_results"]
            if item["source_readiness_input_id"]
            != adapter.PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        ]
        pmb_report_validation = adapter.validate_platform_smoke_execution_report(
            pmb_plan,
            pmb_approval,
            pmb_execution_request,
            pmb_execution_receipt,
            pmb_gate,
            pmb_preflight,
            pmb_drift,
        )
        self.assertEqual(pmb_report_validation["status"], "fail")
        self.assertEqual(
            pmb_report_validation["issue_code"],
            "hostess.issue.platform_smoke_execution_report_pmb_shell_handoff_review_drift",
        )

        evidence_drift = copy.deepcopy(report)
        evidence_drift["evidence_placeholders"][0]["collected"] = True
        evidence_drift["evidence_placeholders"][0]["required_evidence_kind"] = (
            "studio_collected_evidence"
        )
        evidence_report = adapter.validate_platform_smoke_execution_report(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            evidence_drift,
        )
        self.assertEqual(evidence_report["status"], "fail")
        self.assertEqual(
            evidence_report["issue_code"],
            "hostess.issue.platform_smoke_execution_report_evidence_drift",
        )

    def test_builds_platform_smoke_evidence_attachment_without_collection_or_execution(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
        ) = ready_platform_smoke_execution_report_chain()

        receipt = adapter.build_platform_smoke_evidence_attachment_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
        )

        self.assertEqual(
            receipt["$schema"],
            adapter.PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_SCHEMA,
        )
        self.assertEqual(receipt["status"], adapter.VALIDATED_STATUS)
        self.assertIsNone(receipt["issue_code"])
        self.assertEqual(
            receipt["execution_policy"],
            adapter.PLATFORM_SMOKE_EVIDENCE_ATTACHMENT_RECEIPT_POLICY,
        )
        self.assertEqual(receipt["receipt_owner"], "rusty.hostess")
        self.assertEqual(receipt["evidence_owner"], "rusty.hostess")
        self.assertEqual(receipt["command_session_authority"], "rusty.manifold")
        self.assertEqual(receipt["install_launch_evidence_authority"], "rusty.hostess")
        self.assertTrue(receipt["external_evidence_required"])
        self.assertTrue(receipt["external_evidence_descriptors_supplied"])
        self.assertTrue(receipt["external_evidence_descriptors_attached"])
        self.assertTrue(receipt["all_placeholders_bound"])
        self.assertFalse(receipt["device_required"])
        self.assertFalse(receipt["evidence_payloads_copied"])
        self.assertFalse(receipt["real_platform_execution_evidence_attached"])
        self.assertFalse(receipt["schema_path_execution_allowed"])
        self.assertFalse(receipt["platform_execution_allowed"])
        self.assertFalse(receipt["studio_execution_allowed"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(receipt[flag], flag)
        self.assertFalse(receipt["runtime_execution_performed"])
        self.assertFalse(receipt["platform_execution_performed"])
        self.assertEqual(
            receipt["evidence_attachment_count"],
            len(execution_report["evidence_placeholders"]),
        )
        self.assertEqual(
            receipt["validated_evidence_attachment_count"],
            len(execution_report["evidence_placeholders"]),
        )
        self.assertEqual(receipt["rejected_evidence_attachment_count"], 0)
        self.assertEqual(
            receipt["readiness_evidence_attachment_count"],
            len(execution_report["readiness_results"]),
        )
        self.assertTrue(
            all(
                attachment["attachment_status"] == adapter.VALIDATED_STATUS
                and attachment["external_evidence_descriptor_supplied"] is True
                and attachment["evidence_descriptor_attached"] is True
                and attachment["evidence_payload_copied"] is False
                and attachment["collection_started"] is False
                and attachment["studio_execution_allowed"] is False
                and attachment["schema_path_execution_allowed"] is False
                and attachment["runtime_execution_performed"] is False
                and attachment["platform_execution_performed"] is False
                and attachment["real_platform_execution_evidence_attached"] is False
                for attachment in receipt["evidence_attachments"]
            )
        )
        self.assertTrue(
            all(
                attachment["attachment_status"] == adapter.VALIDATED_STATUS
                and attachment["external_readiness_descriptor_supplied"] is True
                and attachment["readiness_descriptor_attached"] is True
                and attachment["validated_for_attachment"] is True
                and attachment["validated_for_execution"] is False
                and attachment["execution_started"] is False
                for attachment in receipt["readiness_evidence_attachments"]
            )
        )

        validation = adapter.validate_platform_smoke_evidence_attachment_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            receipt,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])
        self.assertFalse(validation["real_platform_execution_evidence_attached"])

    def test_platform_smoke_evidence_attachment_preserves_pmb_shell_handoff_gate(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        ) = ready_pmb_platform_smoke_evidence_attachment_chain()

        self.assertTrue(attachment["pmb_shell_handoff_review_required"])
        self.assertTrue(attachment["pmb_shell_handoff_review_ready"])
        self.assertEqual(
            attachment["source_pmb_shell_handoff_review_schema"],
            execution_report["source_pmb_shell_handoff_review_schema"],
        )
        self.assertEqual(attachment["source_pmb_runtime_authority"], "rusty.manifold")
        self.assertEqual(attachment["source_pmb_authoring_authority"], "rusty.studio")
        self.assertEqual(
            attachment["source_pmb_platform_validation_authority"],
            "rusty.hostess",
        )
        self.assertFalse(attachment["source_pmb_runtime_execution_performed"])
        self.assertFalse(attachment["source_pmb_platform_execution_performed"])

        pmb_attachment = next(
            item
            for item in attachment["readiness_evidence_attachments"]
            if item["source_readiness_input_id"]
            == adapter.PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        )
        self.assertEqual(pmb_attachment["attachment_status"], adapter.VALIDATED_STATUS)
        self.assertEqual(
            pmb_attachment["source_pmb_shell_handoff_review_schema"],
            execution_report["source_pmb_shell_handoff_review_schema"],
        )
        self.assertTrue(
            adapter.pmb_shell_handoff_readiness_result_summary_valid(pmb_attachment)
        )

        validation = adapter.validate_platform_smoke_evidence_attachment_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(validation["pmb_shell_handoff_review_required"])
        self.assertTrue(validation["pmb_shell_handoff_review_ready"])

    def test_platform_smoke_evidence_attachment_rejection_without_collection(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
        ) = ready_platform_smoke_execution_report_chain()

        receipt = adapter.build_platform_smoke_evidence_attachment_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            decision=adapter.REJECTED_STATUS,
            reason_code="hostess.issue.operator_declined_platform_smoke_evidence_attachment",
        )

        self.assertEqual(receipt["status"], adapter.REJECTED_STATUS)
        self.assertEqual(
            receipt["issue_code"],
            "hostess.issue.operator_declined_platform_smoke_evidence_attachment",
        )
        self.assertFalse(receipt["external_evidence_descriptors_supplied"])
        self.assertFalse(receipt["external_evidence_descriptors_attached"])
        self.assertFalse(receipt["all_placeholders_bound"])
        self.assertFalse(receipt["evidence_payloads_copied"])
        self.assertFalse(receipt["real_platform_execution_evidence_attached"])
        self.assertEqual(receipt["validated_evidence_attachment_count"], 0)
        self.assertEqual(
            receipt["rejected_evidence_attachment_count"],
            len(execution_report["evidence_placeholders"]),
        )
        self.assertTrue(
            all(
                attachment["attachment_status"] == adapter.REJECTED_STATUS
                and attachment["issue_code"]
                == "hostess.issue.operator_declined_platform_smoke_evidence_attachment"
                and attachment["external_evidence_descriptor_supplied"] is False
                and attachment["evidence_payload_copied"] is False
                and attachment["collection_started"] is False
                for attachment in receipt["evidence_attachments"]
            )
        )
        self.assertEqual(
            adapter.validate_platform_smoke_evidence_attachment_receipt(
                plan,
                approval,
                execution_request,
                execution_receipt,
                gate,
                preflight,
                execution_report,
                receipt,
            )["status"],
            "pass",
        )

    def test_platform_smoke_evidence_attachment_validation_rejects_collection_or_descriptor_drift(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
        ) = ready_platform_smoke_execution_report_chain()
        receipt = adapter.build_platform_smoke_evidence_attachment_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
        )

        started = copy.deepcopy(receipt)
        started["evidence_collection_started"] = True
        started_report = adapter.validate_platform_smoke_evidence_attachment_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            started,
        )
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.platform_smoke_evidence_attachment_execution_started",
        )

        attachment_drift = copy.deepcopy(receipt)
        attachment_drift["evidence_attachments"][0]["owner"] = "rusty.studio"
        attachment_drift["evidence_attachments"][0]["required_evidence_kind"] = (
            "studio_owned_evidence"
        )
        attachment_report = adapter.validate_platform_smoke_evidence_attachment_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment_drift,
        )
        self.assertEqual(attachment_report["status"], "fail")
        self.assertEqual(
            attachment_report["issue_code"],
            "hostess.issue.platform_smoke_evidence_attachment_drift",
        )

        readiness_drift = copy.deepcopy(receipt)
        readiness_drift["readiness_evidence_attachments"][0]["owner"] = "rusty.studio"
        readiness_drift["readiness_evidence_attachments"][0]["input_kind"] = (
            "studio_owned_readiness"
        )
        readiness_report = adapter.validate_platform_smoke_evidence_attachment_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            readiness_drift,
        )
        self.assertEqual(readiness_report["status"], "fail")
        self.assertEqual(
            readiness_report["issue_code"],
            "hostess.issue.platform_smoke_evidence_attachment_readiness_drift",
        )

    def test_platform_smoke_evidence_attachment_validation_rejects_pmb_gate_drift(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        ) = ready_pmb_platform_smoke_evidence_attachment_chain()

        pmb_drift = copy.deepcopy(attachment)
        pmb_drift["pmb_shell_handoff_review_ready"] = False
        pmb_report = adapter.validate_platform_smoke_evidence_attachment_receipt(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            pmb_drift,
        )
        self.assertEqual(pmb_report["status"], "fail")
        self.assertEqual(
            pmb_report["issue_code"],
            "hostess.issue.platform_smoke_evidence_attachment_pmb_shell_handoff_review_drift",
        )

    def test_builds_platform_smoke_evidence_review_scorecard_without_collection_or_execution(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        ) = ready_platform_smoke_evidence_attachment_chain()

        review = adapter.build_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        )

        self.assertEqual(review["$schema"], adapter.PLATFORM_SMOKE_EVIDENCE_REVIEW_SCHEMA)
        self.assertEqual(review["status"], adapter.REVIEWED_STATUS)
        self.assertEqual(review["scorecard_status"], "pass")
        self.assertTrue(review["operator_review_ready"])
        self.assertIsNone(review["issue_code"])
        self.assertEqual(review["execution_policy"], adapter.PLATFORM_SMOKE_EVIDENCE_REVIEW_POLICY)
        self.assertEqual(review["review_owner"], "rusty.hostess")
        self.assertEqual(review["command_session_authority"], "rusty.manifold")
        self.assertEqual(review["install_launch_evidence_authority"], "rusty.hostess")
        self.assertFalse(review["device_required"])
        self.assertFalse(review["evidence_payloads_copied"])
        self.assertFalse(review["real_platform_execution_evidence_attached"])
        self.assertFalse(review["schema_path_execution_allowed"])
        self.assertFalse(review["platform_execution_allowed"])
        self.assertFalse(review["studio_execution_allowed"])
        for flag in adapter.SMOKE_HANDOFF_STARTED_FLAGS:
            self.assertFalse(review[flag], flag)
        self.assertFalse(review["runtime_execution_performed"])
        self.assertFalse(review["platform_execution_performed"])
        self.assertEqual(review["missing_attachment_count"], 0)
        self.assertEqual(review["rejected_attachment_count"], 0)
        self.assertEqual(
            review["reviewed_evidence_attachment_count"],
            len(attachment["evidence_attachments"]),
        )
        self.assertEqual(
            review["reviewed_readiness_evidence_attachment_count"],
            len(attachment["readiness_evidence_attachments"]),
        )
        self.assertTrue(
            all(
                row["review_status"] == adapter.REVIEWED_STATUS
                and row["evidence_payload_copied"] is False
                and row["collection_started"] is False
                and row["platform_execution_performed"] is False
                for row in review["evidence_review_rows"]
            )
        )
        self.assertTrue(
            all(
                row["review_status"] == adapter.REVIEWED_STATUS
                and row["execution_started"] is False
                and row["validated_for_execution"] is False
                and row["platform_execution_performed"] is False
                for row in review["readiness_review_rows"]
            )
        )

        validation = adapter.validate_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
            review,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertFalse(validation["runtime_execution_performed"])
        self.assertFalse(validation["platform_execution_performed"])
        self.assertFalse(validation["real_platform_execution_evidence_attached"])

    def test_platform_smoke_evidence_review_preserves_pmb_shell_handoff_gate(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        ) = ready_pmb_platform_smoke_evidence_attachment_chain()
        review = adapter.build_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        )

        self.assertTrue(review["pmb_shell_handoff_review_required"])
        self.assertTrue(review["pmb_shell_handoff_review_ready"])
        self.assertEqual(
            review["source_pmb_shell_handoff_review_schema"],
            attachment["source_pmb_shell_handoff_review_schema"],
        )
        self.assertEqual(review["source_pmb_runtime_authority"], "rusty.manifold")
        self.assertFalse(review["source_pmb_runtime_execution_performed"])
        self.assertFalse(review["source_pmb_platform_execution_performed"])

        pmb_row = next(
            row
            for row in review["readiness_review_rows"]
            if row["source_readiness_input_id"]
            == adapter.PMB_SHELL_HANDOFF_REVIEW_READINESS_INPUT_ID
        )
        self.assertEqual(pmb_row["review_status"], adapter.REVIEWED_STATUS)
        self.assertEqual(
            pmb_row["source_pmb_shell_handoff_review_schema"],
            attachment["source_pmb_shell_handoff_review_schema"],
        )
        self.assertTrue(adapter.pmb_shell_handoff_readiness_result_summary_valid(pmb_row))

        validation = adapter.validate_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
            review,
        )
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(validation["pmb_shell_handoff_review_required"])
        self.assertTrue(validation["pmb_shell_handoff_review_ready"])

    def test_platform_smoke_evidence_review_rejection_without_execution(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        ) = ready_platform_smoke_evidence_attachment_chain()

        review = adapter.build_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
            decision=adapter.REJECTED_STATUS,
            reason_code="hostess.issue.operator_declined_platform_smoke_evidence_review",
        )

        self.assertEqual(review["status"], adapter.REJECTED_STATUS)
        self.assertEqual(review["scorecard_status"], "fail")
        self.assertFalse(review["operator_review_ready"])
        self.assertEqual(
            review["issue_code"],
            "hostess.issue.operator_declined_platform_smoke_evidence_review",
        )
        self.assertFalse(review["evidence_payloads_copied"])
        self.assertFalse(review["evidence_collection_started"])
        self.assertFalse(review["platform_execution_performed"])
        self.assertEqual(
            review["rejected_attachment_count"],
            len(attachment["evidence_attachments"])
            + len(attachment["readiness_evidence_attachments"]),
        )
        self.assertEqual(review["missing_attachment_count"], 0)
        self.assertTrue(
            all(
                row["review_status"] == adapter.REJECTED_STATUS
                and row["issue_code"]
                == "hostess.issue.operator_declined_platform_smoke_evidence_review"
                and row["collection_started"] is False
                for row in review["evidence_review_rows"]
            )
        )
        self.assertEqual(
            adapter.validate_platform_smoke_evidence_review(
                plan,
                approval,
                execution_request,
                execution_receipt,
                gate,
                preflight,
                execution_report,
                attachment,
                review,
            )["status"],
            "pass",
        )

    def test_platform_smoke_evidence_review_validation_rejects_attachment_or_scorecard_drift(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        ) = ready_platform_smoke_evidence_attachment_chain()
        review = adapter.build_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        )

        started = copy.deepcopy(review)
        started["evidence_collection_started"] = True
        started_report = adapter.validate_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
            started,
        )
        self.assertEqual(started_report["status"], "fail")
        self.assertEqual(
            started_report["issue_code"],
            "hostess.issue.platform_smoke_evidence_review_execution_started",
        )

        attachment_drift = copy.deepcopy(review)
        attachment_drift["evidence_review_rows"][0]["owner"] = "rusty.studio"
        attachment_drift["evidence_review_rows"][0]["required_evidence_kind"] = (
            "studio_reviewed_evidence"
        )
        attachment_report = adapter.validate_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
            attachment_drift,
        )
        self.assertEqual(attachment_report["status"], "fail")
        self.assertEqual(
            attachment_report["issue_code"],
            "hostess.issue.platform_smoke_evidence_review_attachment_drift",
        )

        readiness_drift = copy.deepcopy(review)
        readiness_drift["readiness_review_rows"][0]["owner"] = "rusty.studio"
        readiness_drift["readiness_review_rows"][0]["input_kind"] = (
            "studio_reviewed_readiness"
        )
        readiness_report = adapter.validate_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
            readiness_drift,
        )
        self.assertEqual(readiness_report["status"], "fail")
        self.assertEqual(
            readiness_report["issue_code"],
            "hostess.issue.platform_smoke_evidence_review_readiness_drift",
        )

        scorecard_drift = copy.deepcopy(review)
        scorecard_drift["scorecard_status"] = "fail"
        scorecard_report = adapter.validate_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
            scorecard_drift,
        )
        self.assertEqual(scorecard_report["status"], "fail")
        self.assertEqual(
            scorecard_report["issue_code"],
            "hostess.issue.platform_smoke_evidence_review_scorecard_drift",
        )

    def test_platform_smoke_evidence_review_validation_rejects_pmb_gate_drift(self) -> None:
        (
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        ) = ready_pmb_platform_smoke_evidence_attachment_chain()
        review = adapter.build_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
        )

        pmb_drift = copy.deepcopy(review)
        pmb_drift["pmb_shell_handoff_review_ready"] = False
        pmb_report = adapter.validate_platform_smoke_evidence_review(
            plan,
            approval,
            execution_request,
            execution_receipt,
            gate,
            preflight,
            execution_report,
            attachment,
            pmb_drift,
        )
        self.assertEqual(pmb_report["status"], "fail")
        self.assertEqual(
            pmb_report["issue_code"],
            "hostess.issue.platform_smoke_evidence_review_pmb_shell_handoff_review_drift",
        )

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

from tools.studio_staging.test_fixtures import *  # test fixture factories
