import argparse
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from tools.hostessctl.companion_operator_actions import (
    HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA,
    build_companion_operator_action_catalog,
    operator_catalog_issues,
    run_companion_operator_actions,
    validate_companion_operator_action_catalog,
)
from tools.hostessctl.companion_operator_action_rows import (
    operator_actions_for_frontend as operator_action_rows_for_frontend,
)


class FixedClock:
    def __call__(self) -> datetime:
        return datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


class CompanionOperatorActionCatalogTests(unittest.TestCase):
    def test_wpf_operator_action_catalog_names_cli_routes_and_out_artifacts(self) -> None:
        report = build_companion_operator_action_catalog(
            argparse.Namespace(frontend="wpf", report_id="operator-actions.fixture"),
            clock_func=FixedClock(),
        )
        validation = validate_companion_operator_action_catalog(report)

        self.assertEqual(report["$schema"], HOSTESS_COMPANION_OPERATOR_ACTION_CATALOG_SCHEMA)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(report["frontend"], "wpf")
        self.assertEqual(report["summary"]["action_count"], 12)
        self.assertEqual(report["actions"], operator_action_rows_for_frontend("wpf"))
        self.assertEqual(report["summary"]["requires_elevation_count"], 2)
        self.assertEqual(report["summary"]["requires_quest_lease_count"], 4)
        self.assertEqual(report["summary"]["mutates_host_count"], 5)
        self.assertEqual(report["summary"]["mutates_device_count"], 4)
        self.assertTrue(report["summary"]["all_hostess_cli_segments_name_out"])
        self.assertFalse(report["issues"])
        action_ids = {action["action_id"] for action in report["actions"]}
        self.assertIn("wpf.connectivity.protocol_matrix", action_ids)
        session_action = next(
            action
            for action in report["actions"]
            if action["action_id"] == "wpf.session.run"
        )
        self.assertTrue(session_action["requires_quest_lease"])
        self.assertTrue(session_action["mutates_host"])
        self.assertTrue(session_action["mutates_device"])
        self.assertFalse(session_action["requires_adb_server_lifecycle_lease"])
        self.assertIn("--adb $Adb --serial $QuestSerial", session_action["cli_route"])
        firewall_apply_action = next(
            action
            for action in report["actions"]
            if action["action_id"] == "wpf.connectivity.firewall.apply"
        )
        self.assertTrue(firewall_apply_action["requires_elevation"])
        self.assertTrue(firewall_apply_action["mutates_host"])
        self.assertFalse(firewall_apply_action["requires_quest_lease"])
        protocol_action = next(
            action
            for action in report["actions"]
            if action["action_id"] == "wpf.connectivity.protocol_matrix"
        )
        self.assertTrue(protocol_action["requires_quest_lease"])
        self.assertTrue(protocol_action["mutates_host"])
        self.assertTrue(protocol_action["mutates_device"])
        self.assertIn("companion-report projection", protocol_action["cli_route"])
        self.assertIn("companion-report transport-gates", protocol_action["cli_route"])
        self.assertIn("--fail-on-error", protocol_action["cli_route"])
        self.assertIn("--fail-on-pending", protocol_action["cli_route"])
        self.assertIn("--fail-on-incomplete", protocol_action["cli_route"])
        self.assertIn("--quest-lease-id $QuestLeaseId", protocol_action["cli_route"])
        self.assertIn("QCL-079", protocol_action["cli_route"])

    def test_validation_rejects_advertised_hostess_segment_without_out(self) -> None:
        report = build_companion_operator_action_catalog(
            argparse.Namespace(frontend="wpf", report_id="operator-actions.fixture"),
            clock_func=FixedClock(),
        )
        report["actions"][0]["cli_route"] = (
            "python tools\\hostessctl\\hostessctl.py companion-readiness"
        )
        report["issues"] = operator_catalog_issues(report["actions"], frontend="wpf")

        validation = validate_companion_operator_action_catalog(report)

        self.assertEqual(validation["status"], "fail")
        self.assertTrue(
            any("route segment missing --out" in error for error in validation["errors"])
        )

    def test_validation_rejects_missing_requirement_booleans(self) -> None:
        report = build_companion_operator_action_catalog(
            argparse.Namespace(frontend="wpf", report_id="operator-actions.fixture"),
            clock_func=FixedClock(),
        )
        del report["actions"][0]["requires_quest_lease"]
        report["issues"] = operator_catalog_issues(report["actions"], frontend="wpf")

        validation = validate_companion_operator_action_catalog(report)

        self.assertEqual(validation["status"], "fail")
        self.assertTrue(
            any("missing boolean requires_quest_lease" in error for error in validation["errors"])
        )

    def test_cli_route_writes_operator_action_report_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "operator-actions.json"
            args = argparse.Namespace(
                out=str(out),
                validation_out=None,
                report_id="operator-actions.cli",
                frontend="wpf",
                fail_on_error=True,
            )

            status = run_companion_operator_actions(args, clock_func=FixedClock())

            self.assertEqual(status, 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            validation = json.loads(
                out.with_name("operator-actions.validation-report.json").read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual(report["report_id"], "operator-actions.cli")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(validation["status"], "pass")


if __name__ == "__main__":
    unittest.main()
