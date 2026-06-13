"""Studio platform-smoke plan, approval, execution request, and operator-start gate tests."""

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


class StudioStagingPlatformSmokeControlTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
