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

    def test_cli_writes_schema_only_report_and_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            report_path = root / "report.json"
            ack_path = root / "ack.json"
            reject_path = root / "reject.json"
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
                ],
            ):
                self.assertEqual(adapter.main(), 0)

            report = json.loads(report_path.read_text(encoding="utf-8"))
            ack = json.loads(ack_path.read_text(encoding="utf-8"))
            reject = json.loads(reject_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "accepted")
            self.assertFalse(report["execution_performed"])
            self.assertEqual(ack["ack_status"], "accepted")
            self.assertEqual(reject["reject_status"], "rejected")


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
