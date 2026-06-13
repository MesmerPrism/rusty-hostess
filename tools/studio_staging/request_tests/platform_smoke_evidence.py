"""Studio platform-smoke execution report, evidence attachment, and evidence review tests."""

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


class StudioStagingPlatformSmokeEvidenceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
