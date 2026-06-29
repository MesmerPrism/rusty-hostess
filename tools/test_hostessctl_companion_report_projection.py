from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.companion_report_projection import (
    HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA,
    build_companion_report_projection,
    run_companion_report_projection,
    validate_companion_report_projection,
)
from tools.hostessctl.connectivity_suite import CONNECTIVITY_SUITE_RUN_SCHEMA
from tools.hostessctl.protocol_evidence_matrix import build_protocol_evidence_matrix


REPO_ROOT = Path(__file__).resolve().parents[1]


class HostessCtlCompanionReportProjectionTests(unittest.TestCase):
    def test_projection_combines_device_link_suite_and_protocol_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            suite_path = root / "suite-run.json"
            suite_path.write_text(json.dumps(suite_run_fixture()), encoding="utf-8")

            report = build_companion_report_projection(
                argparse.Namespace(
                    out=str(root / "projection.json"),
                    validation_out=None,
                    projection_id="projection.fixture",
                    frontend="wpf",
                    device_link=[str(REPO_ROOT / "fixtures" / "companion" / "device-link-pass.json")],
                    protocol_matrix=[
                        str(REPO_ROOT / "fixtures" / "companion" / "protocol-matrix-promoted.json")
                    ],
                    suite_run=[str(suite_path)],
                    fail_on_error=True,
                ),
                clock_func=fixed_clock,
            )
            validation = validate_companion_report_projection(report)

        self.assertEqual(report["$schema"], HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA)
        self.assertEqual(report["projection_id"], "projection.fixture")
        self.assertEqual(report["frontend"], "wpf")
        self.assertEqual(report["status"], "warn")
        self.assertTrue(report["authority"]["projection_only"])
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(report["summary"]["source_count"], 3)
        self.assertGreater(report["summary"]["section_counts"]["protocol"], 1)
        self.assertGreater(report["summary"]["section_counts"]["transport"], 1)

        command_row = find_row(report, "device_link.command_result.command_result.fixture")
        self.assertEqual(command_row["authority_owner"], "rusty.manifold.command")
        self.assertEqual(command_row["metrics"]["applied"], True)

        qcl081 = protocol_row(report, "QCL-081")
        self.assertEqual(qcl081["status"], "usable")
        self.assertEqual(qcl081["evidence_tier"], "broker_owned")
        self.assertEqual(qcl081["issue_codes"], [])

        suite_slot = find_row(report, "connectivity_suite.slot.slot.qcl-080")
        self.assertEqual(suite_slot["status"], "pass")
        self.assertEqual(suite_slot["metrics"]["udp_packets_received"], 12)

    def test_projection_copies_candidate_protocol_gates_without_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            matrix_path = root / "candidate-matrix.json"
            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(matrix_path),
                    validation_out=None,
                    matrix_id="candidate-matrix",
                    input=[
                        str(
                            REPO_ROOT
                            / "fixtures"
                            / "connectivity-probe"
                            / "qcl-081-lsl-loopback-pass.json"
                        )
                    ],
                    suite_run=[],
                    latest_artifact_dir=[],
                    latest_probe_id=[],
                    latest_device_link_dir=[],
                    latest_stream_capability_dir=[],
                    latest_stream_probe_id=[],
                    fail_on_error=True,
                )
            )
            matrix_path.write_text(json.dumps(matrix), encoding="utf-8")

            report = build_companion_report_projection(
                argparse.Namespace(
                    out=str(root / "projection.json"),
                    validation_out=None,
                    projection_id="projection.candidate",
                    frontend="cli",
                    device_link=[],
                    protocol_matrix=[str(matrix_path)],
                    suite_run=[],
                    fail_on_error=True,
                ),
                clock_func=fixed_clock,
            )
            validation = validate_companion_report_projection(report)

        qcl081 = protocol_row(report, "QCL-081")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(qcl081["status"], "candidate")
        self.assertEqual(qcl081["evidence_tier"], "fixture")
        self.assertIn("gate.qcl081.quest_runtime_or_broker_owned", qcl081["issue_codes"])
        self.assertNotEqual(qcl081["details"]["promotion_state"], "promoted")

    def test_projection_accepts_connectivity_probe_topology_artifact(self) -> None:
        report = build_companion_report_projection(
            argparse.Namespace(
                out="target/companion-report/topology-projection.json",
                validation_out=None,
                projection_id="projection.topology",
                frontend="wpf",
                device_link=[],
                connectivity_probe=[
                    str(
                        REPO_ROOT
                        / "fixtures"
                        / "connectivity-probe"
                        / "qcl-030-local-only-hotspot-started.json"
                    )
                ],
                protocol_matrix=[],
                suite_run=[],
                fail_on_error=True,
            ),
            clock_func=fixed_clock,
        )
        validation = validate_companion_report_projection(report)

        self.assertEqual(validation["status"], "pass")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["source_count"], 1)
        self.assertEqual(report["source_artifacts"][0]["role"], "connectivity_probe_report")
        self.assertEqual(report["source_artifacts"][0]["summary"]["probe_id"], "QCL-030")

        topology = find_row(report, "connectivity_probe.topology.QCL-030")
        self.assertEqual(topology["status"], "candidate")
        self.assertEqual(topology["authority_owner"], "rusty.hostess.connectivity_probe")
        self.assertIn("experimental", topology["issue_codes"][0])
        self.assertEqual(topology["details"]["owner"], "local_only_hotspot")

        check = find_row(report, "connectivity_probe.check.QCL-030.topology.socket_exchange")
        self.assertEqual(check["status"], "pass")
        self.assertIn("bounded UDP", check["evidence"])

        promotion = find_row(report, "connectivity_probe.promotion.QCL-030")
        self.assertEqual(promotion["status"], "candidate")
        self.assertFalse(promotion["details"]["allowed"])
        self.assertIn("gate.qcl-030.promotion_allowed", promotion["issue_codes"])

    def test_cli_writes_projection_and_validation_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "projection.json"
            args = build_parser().parse_args(
                [
                    "companion-report",
                    "projection",
                    "--frontend",
                    "makepad",
                    "--device-link",
                    str(REPO_ROOT / "fixtures" / "companion" / "device-link-pass.json"),
                    "--connectivity-probe",
                    str(
                        REPO_ROOT
                        / "fixtures"
                        / "connectivity-probe"
                        / "qcl-030-local-only-hotspot-started.json"
                    ),
                    "--protocol-matrix",
                    str(REPO_ROOT / "fixtures" / "companion" / "protocol-matrix-promoted.json"),
                    "--out",
                    str(out),
                    "--projection-id",
                    "projection.cli",
                    "--fail-on-error",
                ]
            )

            status = run_companion_report_projection(args, clock_func=fixed_clock)
            report = read_json(out)
            validation = read_json(out.with_name("projection.validation-report.json"))

        self.assertEqual(status, 0)
        self.assertEqual(args.command, "companion-report")
        self.assertEqual(args.companion_report_command, "projection")
        self.assertEqual(args.frontend, "makepad")
        self.assertEqual(report["projection_id"], "projection.cli")
        self.assertEqual(report["frontend"], "makepad")
        self.assertTrue(
            any(source["role"] == "connectivity_probe_report" for source in report["source_artifacts"])
        )
        self.assertEqual(validation["status"], "pass")


def suite_run_fixture() -> dict[str, Any]:
    return {
        "$schema": CONNECTIVITY_SUITE_RUN_SCHEMA,
        "schema_version": 1,
        "suite_run_id": "suite.fixture",
        "suite_id": "installer-smoke",
        "mode": "fixture",
        "observed_at_utc": "2026-06-29T00:00:00Z",
        "status": "warn",
        "suite_descriptor_path": "target/connectivity-probe/device-link-test-suite.json",
        "environment_snapshot": {
            "network": {
                "windows_profile": {
                    "connections": [
                        {
                            "InterfaceAlias": "Wi-Fi",
                            "NetworkCategory": "Public",
                        }
                    ]
                }
            }
        },
        "grouped_results": [
            {
                "group_id": "group.protocol",
                "phase": "protocol",
                "status": "pass",
                "slot_count": 1,
                "pass_count": 1,
                "warn_count": 0,
                "fail_count": 0,
                "slot_ids": ["slot.qcl-080"],
            }
        ],
        "slot_results": [
            {
                "slot_id": "slot.qcl-080",
                "probe_id": "QCL-080",
                "fixture_profile": "qcl-080-app-owned-udp-freshness-pass",
                "phase": "protocol",
                "purpose": "UDP freshness",
                "mode": "fixture",
                "status": "pass",
                "runner_exit_code": 0,
                "runner_error": "",
                "report_status": "pass",
                "validation_status": "pass",
                "report_path": "target/connectivity-probe/qcl-080.json",
                "validation_path": "target/connectivity-probe/qcl-080.validation-report.json",
                "descriptor_path": "target/connectivity-probe/qcl-080.stream-capability.json",
                "descriptor_validation_path": (
                    "target/connectivity-probe/"
                    "qcl-080.stream-capability.validation-report.json"
                ),
                "descriptor_status": "candidate",
                "elapsed_ms": 10.0,
                "metrics": {
                    "udp_packets_received": 12,
                    "udp_loss_percent": 0.0,
                },
                "issues": [],
            }
        ],
        "artifacts": [],
        "summary": {
            "status": "warn",
            "slot_count": 1,
            "group_count": 1,
            "pass_count": 1,
            "warn_count": 0,
            "fail_count": 0,
        },
    }


def fixed_clock() -> datetime:
    return datetime(2026, 6, 29, 0, 0, 0, tzinfo=UTC)


def protocol_row(report: dict[str, Any], probe_id: str) -> dict[str, Any]:
    for projection_row in report["rows"]:
        details = projection_row.get("details", {})
        if isinstance(details, dict) and details.get("probe_id") == probe_id:
            return projection_row
    raise AssertionError(f"missing protocol row {probe_id}")


def find_row(report: dict[str, Any], row_id: str) -> dict[str, Any]:
    for projection_row in report["rows"]:
        if projection_row["row_id"] == row_id:
            return projection_row
    raise AssertionError(f"missing row {row_id}")


def read_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise AssertionError(f"expected object in {path}")
    return parsed


def build_parser():
    return build_hostessctl_parser(
        broker_package="test.broker",
        broker_port=18765,
        broker_local_forward_port=28765,
        makepad_android_package="test.makepad",
        makepad_android_xr_activity="test.makepad/.Xr",
        makepad_provider_package="test.provider",
        makepad_provider_activity="test.provider/.Provider",
    )


if __name__ == "__main__":
    unittest.main()
