from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import studio_staging_request as adapter


class StudioStagingRequestTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
