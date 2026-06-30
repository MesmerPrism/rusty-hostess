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
from tools.hostessctl.companion_transport_gates import (
    HOSTESS_COMPANION_TRANSPORT_GATE_REPORT_SCHEMA,
    build_companion_transport_gate_report,
    run_companion_transport_gates,
    validate_companion_transport_gate_report,
)
from tools.hostessctl.connectivity_probe import (
    CONNECTIVITY_PROBE_SCHEMA,
    fixture_report,
    live_websocket_report,
)
from tools.hostessctl.connectivity_firewall import CONNECTIVITY_FIREWALL_RULE_SCHEMA
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

    def test_projection_warns_for_failed_source_evidence(self) -> None:
        report = build_companion_report_projection(
            argparse.Namespace(
                out="target/companion-report/damaged-source-projection.json",
                validation_out=None,
                projection_id="projection.failed-source",
                frontend="wpf",
                device_link=[],
                connectivity_probe=[
                    str(
                        REPO_ROOT
                        / "fixtures"
                        / "damaged"
                        / "connectivity-probe-media-high-rate-json-misuse.json"
                    )
                ],
                protocol_matrix=[],
                include_protocol_matrix_inputs=False,
                suite_run=[],
                fail_on_error=True,
            ),
            clock_func=fixed_clock,
        )
        validation = validate_companion_report_projection(report)

        self.assertEqual(validation["status"], "pass")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(report["summary"]["source_status_counts"]["fail"], 1)
        failed_check = find_row(report, "connectivity_probe.check.QCL-082.protocol.media_binary_transport")
        self.assertEqual(failed_check["status"], "fail")
        self.assertIn(
            "hostess.issue.connectivity_probe.media_high_rate_json_payload",
            failed_check["issue_codes"],
        )

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

    def test_cli_writes_transport_gate_report_from_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            matrix_path = root / "matrix.json"
            projection_path = root / "projection.json"
            gate_out = root / "transport-gates.json"
            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(matrix_path),
                    validation_out=None,
                    matrix_id="projection-transport-gates",
                    input=[
                        str(REPO_ROOT / "fixtures" / "companion" / "device-link-pass.json"),
                        str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-010-router-pass.json"),
                        str(
                            REPO_ROOT
                            / "fixtures"
                            / "connectivity-probe"
                            / "qcl-040-wifi-direct-phone-peer-pass.json"
                        ),
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
            projection = build_companion_report_projection(
                argparse.Namespace(
                    out=str(projection_path),
                    validation_out=None,
                    projection_id="projection.transport-gates",
                    frontend="wpf",
                    device_link=[],
                    connectivity_probe=[],
                    protocol_matrix=[str(matrix_path)],
                    suite_run=[],
                    include_protocol_matrix_inputs=True,
                    fail_on_error=True,
                ),
                clock_func=fixed_clock,
            )
            projection_path.write_text(json.dumps(projection), encoding="utf-8")
            args = build_parser().parse_args(
                [
                    "companion-report",
                    "transport-gates",
                    "--projection",
                    str(projection_path),
                    "--out",
                    str(gate_out),
                    "--report-id",
                    "transport-gates.fixture",
                    "--fail-on-error",
                ]
            )

            status = run_companion_transport_gates(args, clock_func=fixed_clock)
            gate_report = read_json(gate_out)
            validation = read_json(gate_out.with_name("transport-gates.validation-report.json"))

        self.assertEqual(status, 0)
        self.assertEqual(args.companion_report_command, "transport-gates")
        self.assertEqual(gate_report["$schema"], HOSTESS_COMPANION_TRANSPORT_GATE_REPORT_SCHEMA)
        self.assertEqual(gate_report["report_id"], "transport-gates.fixture")
        self.assertEqual(gate_report["status"], "warn")
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(gate_report["authority"]["projection_only"])
        self.assertIn(
            "transport.direct_wifi_live_topology",
            gate_report["summary"]["remaining_gate_ids"],
        )
        self.assertIn("tcp", gate_report["summary"]["term_gate_ids"])
        self.assertEqual(
            gate_report["operator_next_actions"]["shell"],
            "powershell",
        )
        self.assertGreaterEqual(
            gate_report["operator_next_actions"]["gate_count"],
            3,
        )
        direct_wifi_gate = next(
            gate
            for gate in gate_report["remaining_live_gates"]
            if gate["gate_id"] == "transport.direct_wifi_live_topology"
        )
        self.assertTrue(
            any(action["requires_quest_lease"] for action in direct_wifi_gate["next_actions"])
        )
        self.assertTrue(
            any(
                "adb.exe" in action.get("command", {}).get("command", "")
                and "--serial '<quest-serial>'" in action.get("command", {}).get("command", "")
                for action in direct_wifi_gate["next_actions"]
            )
        )
        firewall_gate = next(
            gate
            for gate in gate_report["remaining_live_gates"]
            if gate["gate_id"] == "transport.product_tcp_media_listener_firewall"
        )
        self.assertTrue(
            any(action["requires_elevation"] for action in firewall_gate["next_actions"])
        )
        self.assertTrue(
            any(
                action.get("command", {}).get("shell") == "powershell"
                and "--rule-profile qcl-082-rmanvid1-media"
                in action.get("command", {}).get("command", "")
                for action in firewall_gate["next_actions"]
            )
        )

    def test_transport_gate_report_can_fail_on_pending_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            projection_path = root / "projection.json"
            projection_path.write_text(
                json.dumps(
                    {
                        "$schema": HOSTESS_COMPANION_REPORT_PROJECTION_SCHEMA,
                        "projection_id": "projection.pending-gates",
                        "status": "warn",
                        "rows": [
                            {
                                "row_id": "transport_coverage.summary",
                                "kind": "transport_coverage_summary",
                                "details": {
                                    "term_gates": {
                                        "tcp": {
                                            "included": True,
                                            "scope": "qcl010_qcl011_echo_and_qcl082_tcp_binary_media",
                                        }
                                    },
                                    "remaining_live_gates": [
                                        {
                                            "gate_id": "transport.product_tcp_media_listener_firewall",
                                            "status": "pending_live_evidence",
                                            "evidence": "verified product listener firewall report required",
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            args = build_parser().parse_args(
                [
                    "companion-report",
                    "transport-gates",
                    "--projection",
                    str(projection_path),
                    "--out",
                    str(root / "transport-gates.json"),
                    "--fail-on-pending",
                ]
            )

            status = run_companion_transport_gates(args, clock_func=fixed_clock)

        self.assertEqual(status, 2)

    def test_transport_gate_report_validates_projection_authority(self) -> None:
        report = build_companion_transport_gate_report(
            argparse.Namespace(
                projection="missing-projection.json",
                out="target/companion-report/transport-gates.json",
                validation_out=None,
                report_id="transport-gates.missing",
                fail_on_error=True,
                fail_on_pending=False,
            ),
            clock_func=fixed_clock,
        )
        validation = validate_companion_transport_gate_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(validation["status"], "fail")
        self.assertIn(
            "hostess.issue.transport_gates.projection_unreadable",
            [issue["issue_code"] for issue in report["issues"]],
        )

    def test_projection_can_include_protocol_matrix_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            device_path = root / "device-link.json"
            qcl050_path = root / "qcl050.json"
            matrix_path = root / "matrix.json"
            device_path.write_text(
                (
                    REPO_ROOT
                    / "fixtures"
                    / "companion"
                    / "device-link-pass.json"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            qcl050_path.write_text(
                (
                    REPO_ROOT
                    / "fixtures"
                    / "connectivity-probe"
                    / "qcl-050-rfcomm-control-pass.json"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(matrix_path),
                    validation_out=None,
                    matrix_id="projection-inputs",
                    input=[str(device_path), str(qcl050_path)],
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

            args = build_parser().parse_args(
                [
                    "companion-report",
                    "projection",
                    "--frontend",
                    "wpf",
                    "--projection-id",
                    "projection.matrix-inputs",
                    "--protocol-matrix",
                    str(matrix_path),
                    "--include-protocol-matrix-inputs",
                    "--out",
                    str(root / "projection.json"),
                    "--fail-on-error",
                ]
            )
            report = build_companion_report_projection(
                args,
                clock_func=fixed_clock,
            )
            validation = validate_companion_report_projection(report)

        source_roles = [source["role"] for source in report["source_artifacts"]]
        self.assertTrue(args.include_protocol_matrix_inputs)
        self.assertEqual(validation["status"], "pass")
        self.assertIn("device_link_report", source_roles)
        self.assertIn("connectivity_probe_report", source_roles)
        self.assertIn("protocol_evidence_matrix", source_roles)
        self.assertTrue(
            any(row["row_id"] == "connectivity_probe.transport.QCL-050" for row in report["rows"])
        )

    def test_projection_summarizes_transport_coverage_from_included_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            matrix_path = root / "matrix.json"
            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(matrix_path),
                    validation_out=None,
                    matrix_id="projection-transport-coverage",
                    input=[
                        str(REPO_ROOT / "fixtures" / "companion" / "device-link-pass.json"),
                        str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-010-router-pass.json"),
                        str(
                            REPO_ROOT
                            / "fixtures"
                            / "connectivity-probe"
                            / "qcl-040-wifi-direct-phone-peer-pass.json"
                        ),
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
                    projection_id="projection.transport-coverage",
                    frontend="wpf",
                    device_link=[],
                    connectivity_probe=[],
                    protocol_matrix=[str(matrix_path)],
                    suite_run=[],
                    include_protocol_matrix_inputs=True,
                    fail_on_error=True,
                ),
                clock_func=fixed_clock,
            )
            validation = validate_companion_report_projection(report)

        self.assertEqual(validation["status"], "pass")
        self.assertTrue(
            any(
                row["row_id"] == "connectivity_probe.check.QCL-010.device_to_host.tcp_echo"
                for row in report["rows"]
            )
        )
        self.assertTrue(
            any(row["row_id"] == "connectivity_probe.topology.QCL-040" for row in report["rows"])
        )
        coverage = find_row(report, "transport_coverage.summary")
        self.assertEqual(coverage["kind"], "transport_coverage_summary")
        self.assertIn("websocket=", coverage["notes"])
        self.assertIn("tcp=", coverage["notes"])
        self.assertIn("wifi_direct=", coverage["notes"])
        self.assertTrue(coverage["details"]["explicit_terms"]["websocket"])
        self.assertTrue(coverage["details"]["explicit_terms"]["tcp"])
        self.assertTrue(coverage["details"]["explicit_terms"]["wifi_direct"])
        term_gates = coverage["details"]["term_gates"]
        self.assertEqual(
            term_gates["websocket"]["scope"],
            "manifold_command_session_receipts",
        )
        self.assertEqual(
            term_gates["tcp"]["scope"],
            "qcl010_qcl011_echo_and_qcl082_tcp_binary_media",
        )
        self.assertEqual(
            term_gates["wifi_direct"]["scope"],
            "qcl040_qcl041_topology_evidence",
        )
        remaining_gate_ids = {
            gate["gate_id"]
            for gate in coverage["details"]["remaining_live_gates"]
        }
        self.assertIn("transport.general_websocket_capability", remaining_gate_ids)
        self.assertIn("transport.direct_wifi_live_topology", remaining_gate_ids)
        self.assertIn("transport.product_tcp_media_over_direct_wifi", remaining_gate_ids)
        self.assertIn("transport.product_tcp_media_listener_firewall", remaining_gate_ids)

    def test_projection_tracks_qcl079_generic_websocket_as_pending_live_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcl079_path = root / "qcl079-websocket-loopback.json"
            qcl079_path.write_text(
                json.dumps(
                    fixture_report(
                        argparse.Namespace(
                            probe_id="QCL-079",
                            fixture_profile="qcl-079-websocket-loopback-pass",
                            run_id="fixture-qcl079-websocket",
                        ),
                        observed_at=datetime(2026, 6, 30, 0, 0, tzinfo=UTC),
                    )
                ),
                encoding="utf-8",
            )
            matrix_path = root / "matrix.json"
            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(matrix_path),
                    validation_out=None,
                    matrix_id="projection-qcl079-websocket",
                    input=[
                        str(REPO_ROOT / "fixtures" / "companion" / "device-link-pass.json"),
                        str(qcl079_path),
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
                    projection_id="projection.qcl079-websocket",
                    frontend="wpf",
                    device_link=[],
                    connectivity_probe=[],
                    protocol_matrix=[str(matrix_path)],
                    suite_run=[],
                    include_protocol_matrix_inputs=True,
                    fail_on_error=True,
                ),
                clock_func=fixed_clock,
            )
            validation = validate_companion_report_projection(report)

        self.assertEqual(validation["status"], "pass")
        coverage = find_row(report, "transport_coverage.summary")
        websocket_gate = coverage["details"]["term_gates"]["websocket"]
        self.assertEqual(
            websocket_gate["scope"],
            "manifold_command_session_receipts_and_qcl079_generic_protocol_fit",
        )
        self.assertIn("QCL-079", websocket_gate["probe_ids"])
        gate = next(
            row
            for row in coverage["details"]["remaining_live_gates"]
            if row["gate_id"] == "transport.general_websocket_capability"
        )
        self.assertEqual(gate["status"], "pending_live_evidence")
        self.assertIn("QCL-079 generic WebSocket", gate["evidence"])

    def test_projection_clears_qcl079_gate_with_broker_owned_websocket_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            descriptor, evidence = write_websocket_route_files(root)
            qcl079_path = root / "qcl079-websocket-broker.json"
            qcl079_path.write_text(
                json.dumps(
                    live_websocket_report(
                        argparse.Namespace(
                            probe_id="QCL-079",
                            mode="live",
                            run_id="qcl079-manifold-websocket",
                            websocket_source="broker-owned-websocket",
                            websocket_route_descriptor=str(descriptor),
                            websocket_route_evidence=str(evidence),
                            websocket_message_count=8,
                            websocket_payload_bytes=128,
                            websocket_bind_host="127.0.0.1",
                            websocket_port=0,
                            websocket_path="/qcl079",
                            websocket_timeout_seconds=1.0,
                        ),
                        clock_func=lambda: datetime(2026, 6, 30, 0, 0, tzinfo=UTC),
                    )
                ),
                encoding="utf-8",
            )
            matrix_path = root / "matrix.json"
            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(matrix_path),
                    validation_out=None,
                    matrix_id="projection-qcl079-websocket-broker",
                    input=[
                        str(REPO_ROOT / "fixtures" / "companion" / "device-link-pass.json"),
                        str(qcl079_path),
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
                    projection_id="projection.qcl079-websocket-broker",
                    frontend="wpf",
                    device_link=[],
                    connectivity_probe=[],
                    protocol_matrix=[str(matrix_path)],
                    suite_run=[],
                    include_protocol_matrix_inputs=True,
                    fail_on_error=True,
                ),
                clock_func=fixed_clock,
            )
            validation = validate_companion_report_projection(report)

        self.assertEqual(validation["status"], "pass")
        coverage = find_row(report, "transport_coverage.summary")
        websocket_gate = coverage["details"]["term_gates"]["websocket"]
        self.assertEqual(
            websocket_gate["scope"],
            "manifold_command_session_receipts_and_qcl079_generic_protocol_fit",
        )
        remaining_gate_ids = {
            row["gate_id"] for row in coverage["details"]["remaining_live_gates"]
        }
        self.assertNotIn("transport.general_websocket_capability", remaining_gate_ids)

    def test_projection_clears_product_tcp_media_direct_wifi_gate_only_with_combined_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcl082_path = root / "qcl082-product-direct-wifi.json"
            qcl082_path.write_text(json.dumps(qcl082_product_direct_wifi_report()), encoding="utf-8")
            report = build_companion_report_projection(
                argparse.Namespace(
                    out=str(root / "projection.json"),
                    validation_out=None,
                    projection_id="projection.product-direct-wifi",
                    frontend="wpf",
                    device_link=[],
                    connectivity_probe=[
                        str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-040-wifi-direct-phone-peer-pass.json"),
                        str(qcl082_path),
                    ],
                    protocol_matrix=[],
                    suite_run=[],
                    include_protocol_matrix_inputs=False,
                    fail_on_error=True,
                ),
                clock_func=fixed_clock,
            )
            validation = validate_companion_report_projection(report)

        self.assertEqual(validation["status"], "pass")
        product_row = find_row(
            report,
            "connectivity_probe.check.QCL-082.protocol.media_product_topology_gate",
        )
        self.assertEqual(product_row["status"], "pass")
        coverage = find_row(report, "transport_coverage.summary")
        remaining_gate_ids = {
            gate["gate_id"]
            for gate in coverage["details"]["remaining_live_gates"]
        }
        self.assertNotIn("transport.product_tcp_media_over_direct_wifi", remaining_gate_ids)
        self.assertIn("transport.product_tcp_media_listener_firewall", remaining_gate_ids)

    def test_projection_clears_product_tcp_media_listener_firewall_gate_with_verified_product_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcl082_path = root / "qcl082-product-firewall.json"
            qcl082_path.write_text(json.dumps(qcl082_product_tcp_firewall_report()), encoding="utf-8")
            report = build_companion_report_projection(
                argparse.Namespace(
                    out=str(root / "projection.json"),
                    validation_out=None,
                    projection_id="projection.product-tcp-firewall",
                    frontend="wpf",
                    device_link=[],
                    connectivity_probe=[str(qcl082_path)],
                    protocol_matrix=[],
                    suite_run=[],
                    include_protocol_matrix_inputs=False,
                    fail_on_error=True,
                ),
                clock_func=fixed_clock,
            )
            validation = validate_companion_report_projection(report)

        self.assertEqual(validation["status"], "pass")
        firewall_row = find_row(
            report,
            "connectivity_probe.check.QCL-082.protocol.media_product_listener_firewall_gate",
        )
        self.assertEqual(firewall_row["status"], "pass")
        coverage = find_row(report, "transport_coverage.summary")
        remaining_gate_ids = {
            gate["gate_id"]
            for gate in coverage["details"]["remaining_live_gates"]
        }
        self.assertNotIn("transport.product_tcp_media_listener_firewall", remaining_gate_ids)

    def test_projection_clears_listener_firewall_gate_from_standalone_firewall_verify_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            firewall_path = root / "qcl082-product-firewall-verify.json"
            firewall_path.write_text(
                json.dumps(qcl082_product_tcp_firewall_verify_report()),
                encoding="utf-8",
            )
            report = build_companion_report_projection(
                argparse.Namespace(
                    out=str(root / "projection.json"),
                    validation_out=None,
                    projection_id="projection.product-firewall-verify",
                    frontend="wpf",
                    device_link=[],
                    connectivity_probe=[
                        str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-040-wifi-direct-phone-peer-pass.json"),
                    ],
                    firewall_rule=[str(firewall_path)],
                    protocol_matrix=[],
                    suite_run=[],
                    include_protocol_matrix_inputs=False,
                    fail_on_error=True,
                ),
                clock_func=fixed_clock,
            )
            validation = validate_companion_report_projection(report)

        self.assertEqual(validation["status"], "pass")
        self.assertEqual(report["source_artifacts"][1]["role"], "firewall_rule_report")
        firewall_row = find_row(report, "firewall_rule.qcl-082-rmanvid1-media.verify")
        self.assertEqual(firewall_row["status"], "pass")
        self.assertEqual(firewall_row["authority_owner"], "tools.hostessctl.connectivity_firewall")
        self.assertEqual(
            firewall_row["details"]["product_gate"],
            "product_tcp_media_listener_firewall_verified",
        )
        self.assertTrue(firewall_row["details"]["product_gate_proven"])
        coverage = find_row(report, "transport_coverage.summary")
        remaining_gate_ids = {
            gate["gate_id"]
            for gate in coverage["details"]["remaining_live_gates"]
        }
        self.assertNotIn("transport.product_tcp_media_listener_firewall", remaining_gate_ids)
        self.assertIn("transport.direct_wifi_live_topology", remaining_gate_ids)
        self.assertIn("transport.product_tcp_media_over_direct_wifi", remaining_gate_ids)


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


def qcl082_product_direct_wifi_report() -> dict[str, Any]:
    return {
        "schema": CONNECTIVITY_PROBE_SCHEMA,
        "probe_id": "QCL-082",
        "run_id": "qcl082-product-direct-wifi",
        "observed_at_utc": "2026-06-29T00:00:00Z",
        "status": "pass",
        "classification": "protocol_fit_receiver_counters",
        "topology": {
            "owner": "hostess_receiver_canary",
            "network_provider": "declared_by_receiver_capture",
            "endpoint_direction": "quest_to_host_binary_media",
            "experimental": True,
        },
        "transport": {
            "family": "tcp_binary",
            "route": "hostess_rmanvid1_receiver_capture",
            "protocol_role": "binary_media_plane_receiver_counters",
            "payload_class": "h264_annex_b_binary_frames",
        },
        "checks": [
            {
                "name": "protocol.media_product_topology_gate",
                "status": "pass",
                "evidence": "RMANVID1 TCP receiver capture is paired with promoted direct-Wi-Fi topology evidence",
                "observed": {
                    "product_gate": "product_tcp_media_over_direct_wifi",
                    "product_gate_proven": True,
                    "topology_owner": "wifi_direct",
                    "topology_network_provider": "wifi_direct",
                    "topology_endpoint_direction": "peer_to_peer_group",
                    "topology_transport_family": "wifi_direct",
                    "topology_promotion_allowed": True,
                    "media_promotion_allowed": True,
                },
                "issue_codes": [],
            }
        ],
        "measurements": {
            "media_product_topology_ready": True,
        },
        "promotion": {
            "allowed": True,
            "target": "quest.device_link binary media stream capability descriptor",
            "reason": "unit fixture promoted product TCP media over direct-Wi-Fi",
        },
        "issues": [],
    }


def qcl082_product_tcp_firewall_report() -> dict[str, Any]:
    return {
        "schema": CONNECTIVITY_PROBE_SCHEMA,
        "probe_id": "QCL-082",
        "run_id": "qcl082-product-firewall",
        "observed_at_utc": "2026-06-29T00:00:00Z",
        "status": "pass",
        "classification": "protocol_fit_receiver_counters",
        "topology": {
            "owner": "hostess_receiver_canary",
            "network_provider": "declared_by_receiver_capture",
            "endpoint_direction": "quest_to_host_binary_media",
            "experimental": True,
        },
        "transport": {
            "family": "tcp_binary",
            "route": "hostess_rmanvid1_receiver_capture",
            "protocol_role": "binary_media_plane_receiver_counters",
            "payload_class": "h264_annex_b_binary_frames",
        },
        "checks": [
            {
                "name": "protocol.media_product_listener_firewall_gate",
                "status": "pass",
                "evidence": "RMANVID1 TCP receiver capture is paired with a verified product Hostess/WPF listener firewall rule",
                "observed": {
                    "product_gate": "product_tcp_media_listener_firewall_verified",
                    "product_gate_proven": True,
                    "listener_program": "S:\\Work\\repos\\active\\rusty-hostess\\apps\\hostess-companion-wpf\\bin\\Debug\\net9.0-windows\\HostessCompanion.Wpf.exe",
                    "listener_protocol": "TCP",
                    "listener_port": 9079,
                    "product_rule_verified": True,
                    "allowed_on_active_profile": True,
                },
                "issue_codes": [],
            }
        ],
        "measurements": {
            "media_product_listener_firewall_verified": True,
        },
        "promotion": {
            "allowed": True,
            "target": "quest.device_link binary media stream capability descriptor",
            "reason": "unit fixture promoted product TCP media listener firewall",
        },
        "issues": [],
    }


def qcl082_product_tcp_firewall_verify_report() -> dict[str, Any]:
    program = (
        "S:\\Work\\repos\\active\\rusty-hostess\\apps\\hostess-companion-wpf\\bin\\"
        "Debug\\net9.0-windows\\HostessCompanion.Wpf.exe"
    )
    return {
        "schema": CONNECTIVITY_FIREWALL_RULE_SCHEMA,
        "observed_at_utc": "2026-06-29T00:00:00Z",
        "status": "pass",
        "action": "verify",
        "rule_profile": "qcl-082-rmanvid1-media",
        "probe_usage": {
            "probe_id": "QCL-082",
            "family": "media",
        },
        "rule": {
            "name": "Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079",
            "program": program,
            "protocol": "TCP",
            "local_port": 9079,
            "profiles": ["Public"],
            "remote_address": "LocalSubnet",
        },
        "verification": {
            "product_rule_verified": True,
            "allowed_on_active_profile": True,
            "issue_codes": [],
            "listener_firewall": {
                "program": program,
                "protocol": "TCP",
                "port": 9079,
                "product_rule_verified": True,
                "allowed_on_active_profile": True,
            },
        },
        "issues": [],
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


def write_websocket_route_files(root: Path) -> tuple[Path, Path]:
    descriptor = {
        "$schema": "rusty.manifold.bridge.route_descriptor.v1",
        "route_id": "bridge_route.stream.websocket.ordered",
        "route_kind": "stream_bridge",
        "plane": "data",
        "transport_family": "web_socket",
        "delivery": "ordered",
        "payload_class": "stream_packet",
        "rate_class": "periodic",
        "authority_role": "adapter",
        "required_evidence_stages": ["sent", "transport_ok", "observed"],
        "required_conditions": [
            {
                "condition_id": "condition.host.websocket_firewall_inbound",
                "scope": "security",
                "kind": "host_firewall_inbound_allowed",
                "required_state": "allowed",
                "check_ref": "check.host.firewall.websocket_inbound",
                "issue_codes": ["issue.host.firewall_blocked"],
            }
        ],
        "timing": {
            "rtt_strategy": "transport_echo",
            "clock_domain": "clock.host_monotonic",
            "min_round_trips": 8,
            "timeout_ms": 5000,
            "warmup_ms": 250,
            "reported_metrics": ["rtt_ms", "jitter_ms"],
        },
    }
    evidence = {
        "$schema": "rusty.manifold.bridge.route_evidence.v1",
        "evidence_id": "evidence.bridge_route.stream.websocket.ordered.loopback",
        "route_id": "bridge_route.stream.websocket.ordered",
        "status": "pass",
        "started_at_ms": 1765000003000,
        "ended_at_ms": 1765000003280,
        "stage_reports": [
            {"stage": "sent", "status": "pass", "evidence_refs": ["evidence.websocket.stream.producer.sent"], "issue_codes": []},
            {
                "stage": "transport_ok",
                "status": "pass",
                "evidence_refs": [
                    "evidence.websocket.http_upgrade.accepted",
                    "evidence.websocket.sec_websocket_accept.valid",
                ],
                "issue_codes": [],
            },
            {"stage": "observed", "status": "pass", "evidence_refs": ["evidence.websocket.stream.consumer.received"], "issue_codes": []},
        ],
        "artifact_refs": ["artifact.websocket.stream.loopback.report"],
        "issues": [],
    }
    descriptor_path = root / "websocket-route.json"
    evidence_path = root / "websocket-evidence.json"
    descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    return descriptor_path, evidence_path


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
