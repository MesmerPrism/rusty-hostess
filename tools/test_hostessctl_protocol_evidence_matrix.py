from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.device_link_report import build_stream_capability_descriptor_from_connectivity_probe
from tools.hostessctl.protocol_evidence_matrix import (
    PROTOCOL_EVIDENCE_MATRIX_SCHEMA,
    build_protocol_evidence_matrix,
    run_protocol_evidence_matrix,
    validate_protocol_evidence_matrix,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class HostessCtlProtocolEvidenceMatrixTests(unittest.TestCase):
    def test_fixture_loopbacks_remain_candidates_with_missing_promotion_gates(self) -> None:
        report = build_protocol_evidence_matrix(
            argparse.Namespace(
                out="unused.json",
                validation_out=None,
                matrix_id="fixture-matrix",
                input=[
                    str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-080-app-owned-udp-freshness-pass.json"),
                    str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-081-lsl-loopback-pass.json"),
                    str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-083-osc-loopback-pass.json"),
                    str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-084-zeromq-loopback-pass.json"),
                ],
                suite_run=[],
                fail_on_error=True,
            )
        )
        validation = validate_protocol_evidence_matrix(report)

        self.assertEqual(report["$schema"], PROTOCOL_EVIDENCE_MATRIX_SCHEMA)
        self.assertEqual(report["status"], "warn")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(row(report, "QCL-080")["status"], "candidate")
        self.assertEqual(row(report, "QCL-081")["evidence_tier"], "fixture")
        self.assertEqual(row(report, "QCL-083")["status"], "candidate")
        self.assertEqual(row(report, "QCL-084")["status"], "candidate")
        self.assertIn("gate.qcl084.quest_runtime_or_broker_owned", row(report, "QCL-084")["missing_gates"])
        self.assertFalse(report["summary"]["all_required_data_protocols_promoted"])

    def test_promoted_udp_descriptor_satisfies_qcl080_without_promoting_other_protocols(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcl080_path = root / "qcl080-live.json"
            descriptor_path = root / "qcl080.stream-capability.json"
            report = promoted_qcl080_report()
            qcl080_path.write_text(json.dumps(report), encoding="utf-8")
            descriptor_path.write_text(
                json.dumps(
                    build_stream_capability_descriptor_from_connectivity_probe(
                        report,
                        source_path=qcl080_path,
                    )
                ),
                encoding="utf-8",
            )

            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="qcl080-promoted",
                    input=[str(qcl080_path), str(descriptor_path)],
                    suite_run=[],
                    fail_on_error=True,
                )
            )

        qcl080 = row(matrix, "QCL-080")
        self.assertEqual(qcl080["status"], "usable")
        self.assertEqual(qcl080["promotion_state"], "promoted")
        self.assertEqual(qcl080["evidence_tier"], "quest_runtime")
        self.assertTrue(qcl080["promotion_allowed"])
        self.assertEqual(qcl080["missing_gates"], [])
        self.assertIn("QCL-081", matrix["summary"]["pending_required_probe_ids"])

    def test_native_rust_broker_zero_mq_promotes_qcl084(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcl084_path = root / "qcl084-native-rust-broker.json"
            qcl084_path.write_text(json.dumps(promoted_qcl084_report()), encoding="utf-8")

            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="qcl084-promoted",
                    input=[str(qcl084_path)],
                    suite_run=[],
                    fail_on_error=True,
                )
            )

        qcl084 = row(matrix, "QCL-084")
        self.assertEqual(qcl084["status"], "usable")
        self.assertEqual(qcl084["promotion_state"], "promoted")
        self.assertEqual(qcl084["evidence_tier"], "broker_owned")
        self.assertTrue(qcl084["promotion_allowed"])
        self.assertEqual(qcl084["missing_gates"], [])
        self.assertIn("QCL-081", matrix["summary"]["pending_required_probe_ids"])

    def test_device_link_report_promotes_command_baseline(self) -> None:
        matrix = build_protocol_evidence_matrix(
            argparse.Namespace(
                out="unused.json",
                validation_out=None,
                matrix_id="device-link-command",
                input=[str(REPO_ROOT / "tests" / "HostessCompanion.Wpf.Tests" / "Fixtures" / "device-link-pass.json")],
                suite_run=[],
                fail_on_error=True,
            )
        )

        command = row(matrix, "QCL-000")
        self.assertEqual(command["status"], "usable")
        self.assertEqual(command["evidence_tier"], "quest_runtime")
        self.assertEqual(command["missing_gates"], [])

    def test_cli_loads_suite_run_artifacts_and_writes_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "qcl084.json"
            suite = root / "suite.json"
            out = root / "matrix.json"
            source.write_text(
                (REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-084-zeromq-loopback-pass.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            suite.write_text(
                json.dumps(
                    {
                        "$schema": "rusty.quest.device_link.install_environment_suite_run.v1",
                        "status": "warn",
                        "artifacts": [
                            {
                                "role": "connectivity_probe_report",
                                "probe_id": "QCL-084",
                                "path": str(source),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            status = run_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(out),
                    validation_out=None,
                    matrix_id="suite-loaded",
                    input=[],
                    suite_run=[str(suite)],
                    fail_on_error=True,
                )
            )
            report = read_json(out)
            validation = read_json(out.with_name("matrix.validation-report.json"))

        self.assertEqual(status, 0)
        self.assertEqual(report["matrix_id"], "suite-loaded")
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(any(item["role"] == "suite_run" for item in report["inputs"]))
        self.assertEqual(row(report, "QCL-084")["source"]["artifact_path"], str(source))

    def test_parser_accepts_protocol_matrix_route(self) -> None:
        args = build_parser().parse_args(
            [
                "connectivity-probe",
                "protocol-matrix",
                "--suite-run",
                "target/connectivity-suite.json",
                "--input",
                "target/qcl080.stream-capability.json",
                "--out",
                "target/protocol-matrix.json",
                "--matrix-id",
                "local-matrix",
                "--fail-on-error",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "protocol-matrix")
        self.assertEqual(args.suite_run, ["target/connectivity-suite.json"])
        self.assertEqual(args.input, ["target/qcl080.stream-capability.json"])
        self.assertEqual(args.matrix_id, "local-matrix")
        self.assertTrue(args.fail_on_error)


def promoted_qcl080_report() -> dict[str, Any]:
    report = read_json(
        REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-080-app-owned-udp-freshness-pass.json"
    )
    report["run_id"] = "qcl080-live-promoted"
    report["status"] = "pass"
    report["promotion"]["allowed"] = True
    report["promotion"]["reason"] = "QCL-080 proves app-owned runtime UDP datagrams"
    report["host"]["adb_provider"] = "S:/Work/tools/Android/windows-sdk/platform-tools/adb.exe"
    report["host"]["toolchain_profile"] = "hostessctl.connectivity_probe.live"
    listener = report["host"]["firewall_listener"]
    listener["program"] = "C:\\Program Files\\Rusty Hostess\\HostessCompanion.Wpf.exe"
    listener["expected_rule_name"] = "Rusty Hostess WPF QCL-080 UDP Freshness 18767"
    listener["expected_remote_address"] = "LocalSubnet"
    listener["product_matching_rule_count"] = 1
    listener["product_rule_verified"] = True
    listener["matching_rules"][0].update(
        {
            "name": "Rusty Hostess WPF QCL-080 UDP Freshness 18767",
            "application_name": "C:\\Program Files\\Rusty Hostess\\HostessCompanion.Wpf.exe",
            "remote_addresses": "LocalSubnet",
            "program_matches": True,
            "name_matches": True,
            "remote_address_matches": True,
            "product_scope_matches": True,
        }
    )
    return report


def promoted_qcl084_report() -> dict[str, Any]:
    report = read_json(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-084-zeromq-loopback-pass.json")
    report["run_id"] = "qcl084-native-rust-broker-promoted"
    report["status"] = "pass"
    report["transport"]["endpoint_source"] = "native-rust-broker"
    report["transport"]["local_endpoint"] = "native-rust-broker"
    report["transport"]["remote_endpoint"] = "native-rust-broker"
    report["host"]["adb_provider"] = ""
    report["host"]["toolchain_profile"] = "hostessctl.connectivity_probe.qcl084"
    report["measurements"]["zeromq_messages_requested"] = 16
    report["measurements"]["zeromq_messages_received"] = 16
    report["promotion"]["allowed"] = True
    report["promotion"]["reason"] = "QCL-084 proves native Rust broker-owned ZeroMQ route evidence"
    report["zeromq_payload_probe"] = {
        "status": "pass",
        "source": "native-rust-broker",
        "pattern": "pub-sub",
        "messages_requested": 16,
        "messages_received": 16,
        "messages_acknowledged": 16,
        "dropped_count": 0,
        "decode_error_count": 0,
        "evidence_tier": "broker_owned",
        "authority_owner": "rusty.manifold.transport",
        "bridge_route_evidence": {
            "$schema": "rusty.manifold.bridge.route_evidence.v1",
            "route_id": "bridge_route.stream.zeromq.pub_sub",
            "status": "pass",
            "stage_reports": [
                {"stage": "sent", "status": "pass", "issue_codes": []},
                {"stage": "transport_ok", "status": "pass", "issue_codes": []},
                {"stage": "observed", "status": "pass", "issue_codes": []},
            ],
            "issues": [],
        },
        "issue_codes": [],
    }
    return report


def row(report: dict[str, Any], probe_id: str) -> dict[str, Any]:
    for candidate in report["rows"]:
        if candidate["probe_id"] == probe_id:
            return candidate
    raise AssertionError(f"missing {probe_id} row")


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
