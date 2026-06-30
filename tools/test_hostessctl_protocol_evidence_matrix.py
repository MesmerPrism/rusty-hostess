from __future__ import annotations

import argparse
import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.connectivity_probe import fixture_report, live_websocket_report
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
                    str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-082-media-binary-plane-pass.json"),
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
        self.assertEqual(row(report, "QCL-082")["status"], "candidate")
        self.assertEqual(row(report, "QCL-082")["evidence_tier"], "fixture")
        self.assertNotIn("gate.qcl082.media_binary_probe_defined", row(report, "QCL-082")["missing_gates"])
        self.assertEqual(row(report, "QCL-083")["status"], "candidate")
        self.assertEqual(row(report, "QCL-084")["status"], "candidate")
        self.assertIn("gate.qcl084.quest_runtime_or_broker_owned", row(report, "QCL-084")["missing_gates"])
        self.assertFalse(report["summary"]["all_required_data_protocols_promoted"])

    def test_damaged_qcl082_json_media_fixture_is_rejected(self) -> None:
        report = build_protocol_evidence_matrix(
            argparse.Namespace(
                out="unused.json",
                validation_out=None,
                matrix_id="qcl082-damaged",
                input=[
                    str(REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-media-high-rate-json-misuse.json"),
                ],
                suite_run=[],
                fail_on_error=True,
            )
        )
        validation = validate_protocol_evidence_matrix(report)

        qcl082 = row(report, "QCL-082")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(qcl082["status"], "rejected")
        self.assertEqual(qcl082["promotion_state"], "rejected")
        self.assertIn("gate.qcl082.media_high_rate_json_guard", qcl082["missing_gates"])

    def test_qcl079_generic_websocket_is_optional_candidate(self) -> None:
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

            report = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="qcl079-websocket",
                    input=[str(qcl079_path)],
                    suite_run=[],
                    latest_artifact_dir=[],
                    latest_probe_id=[],
                    latest_device_link_dir=[],
                    latest_stream_capability_dir=[],
                    latest_stream_probe_id=[],
                    fail_on_error=True,
                )
            )
        validation = validate_protocol_evidence_matrix(report)

        qcl079 = row(report, "QCL-079")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(qcl079["status"], "candidate")
        self.assertEqual(qcl079["transport_kind"], "websocket")
        self.assertEqual(qcl079["evidence_tier"], "fixture")
        self.assertEqual(qcl079["promotion_state"], "candidate")
        self.assertFalse(qcl079["required_for_fold_in"])
        self.assertFalse(qcl079["promotion_allowed"])
        self.assertNotIn("QCL-079", report["summary"]["pending_required_probe_ids"])

    def test_qcl079_manifold_websocket_route_promotes_as_broker_owned(self) -> None:
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

            report = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="qcl079-websocket-broker",
                    input=[str(qcl079_path)],
                    suite_run=[],
                    latest_artifact_dir=[],
                    latest_probe_id=[],
                    latest_device_link_dir=[],
                    latest_stream_capability_dir=[],
                    latest_stream_probe_id=[],
                    fail_on_error=True,
                )
            )
        validation = validate_protocol_evidence_matrix(report)

        qcl079 = row(report, "QCL-079")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(qcl079["status"], "usable")
        self.assertEqual(qcl079["transport_kind"], "websocket")
        self.assertEqual(qcl079["evidence_tier"], "broker_owned")
        self.assertEqual(qcl079["promotion_state"], "promoted")
        self.assertFalse(qcl079["required_for_fold_in"])
        self.assertTrue(qcl079["promotion_allowed"])
        self.assertNotIn("QCL-079", report["summary"]["pending_required_probe_ids"])

    def test_qcl082_media_stream_session_plan_remains_candidate_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcl082_path = root / "qcl082-media-stream-session-plan.json"
            qcl082_path.write_text(json.dumps(qcl082_source_contract_report()), encoding="utf-8")

            report = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="qcl082-media-stream-session-plan",
                    input=[str(qcl082_path)],
                    suite_run=[],
                    fail_on_error=True,
                )
            )
        validation = validate_protocol_evidence_matrix(report)

        qcl082 = row(report, "QCL-082")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(qcl082["status"], "candidate")
        self.assertEqual(qcl082["promotion_state"], "candidate")
        self.assertEqual(qcl082["evidence_tier"], "fixture")
        self.assertEqual(qcl082["source"]["endpoint_source"], "rusty-quest-media-stream-session-plan")
        self.assertEqual(qcl082["missing_gates"], ["gate.qcl082.broker_runtime_status"])
        self.assertFalse(qcl082["promotion_allowed"])

    def test_qcl082_media_stream_runtime_status_is_broker_owned_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcl082_path = root / "qcl082-media-stream-runtime-status.json"
            qcl082_path.write_text(json.dumps(qcl082_runtime_status_report()), encoding="utf-8")

            report = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="qcl082-media-stream-runtime-status",
                    input=[str(qcl082_path)],
                    suite_run=[],
                    fail_on_error=True,
                )
            )
        validation = validate_protocol_evidence_matrix(report)

        qcl082 = row(report, "QCL-082")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(qcl082["status"], "candidate")
        self.assertEqual(qcl082["promotion_state"], "candidate")
        self.assertEqual(qcl082["evidence_tier"], "broker_owned")
        self.assertEqual(
            qcl082["source"]["endpoint_source"],
            "rusty-quest-manifold-broker-media-stream-runtime",
        )
        self.assertIn("gate.qcl082.media_measurements_declared", qcl082["missing_gates"])
        self.assertNotIn("gate.qcl082.broker_runtime_status", qcl082["missing_gates"])
        self.assertFalse(qcl082["promotion_allowed"])

    def test_qcl082_receiver_counters_can_promote_broker_owned_live_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcl082_path = root / "qcl082-rmanvid1-receiver-capture.json"
            qcl082_path.write_text(json.dumps(qcl082_receiver_capture_report()), encoding="utf-8")

            report = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="qcl082-rmanvid1-receiver-capture",
                    input=[str(qcl082_path)],
                    suite_run=[],
                    fail_on_error=True,
                )
            )
        validation = validate_protocol_evidence_matrix(report)

        qcl082 = row(report, "QCL-082")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(qcl082["status"], "usable")
        self.assertEqual(qcl082["promotion_state"], "promoted")
        self.assertEqual(qcl082["evidence_tier"], "broker_owned")
        self.assertEqual(qcl082["missing_gates"], [])
        self.assertTrue(qcl082["promotion_allowed"])

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

    def test_manifold_broker_lsl_promotes_qcl081(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qcl081_path = root / "qcl081-manifold-lsl-broker.json"
            qcl081_path.write_text(json.dumps(promoted_qcl081_report()), encoding="utf-8")

            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="qcl081-promoted",
                    input=[str(qcl081_path)],
                    suite_run=[],
                    fail_on_error=True,
                )
            )

        qcl081 = row(matrix, "QCL-081")
        self.assertEqual(qcl081["status"], "usable")
        self.assertEqual(qcl081["promotion_state"], "promoted")
        self.assertEqual(qcl081["evidence_tier"], "broker_owned")
        self.assertTrue(qcl081["promotion_allowed"])
        self.assertEqual(qcl081["missing_gates"], [])
        self.assertIn("QCL-084", matrix["summary"]["pending_required_probe_ids"])

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

    def test_latest_artifact_dir_loads_newest_requested_probe_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            stale_qcl081_path = root / "qcl081-stale.json"
            latest_qcl081_path = root / "qcl081-latest.json"
            qcl084_path = root / "qcl084-latest.json"
            matrix_sidecar_path = root / "qcl081.protocol-matrix.json"

            stale_qcl081 = promoted_qcl081_report()
            stale_qcl081["run_id"] = "qcl081-stale"
            stale_qcl081["promotion"]["allowed"] = False
            stale_qcl081_path.write_text(json.dumps(stale_qcl081), encoding="utf-8")
            latest_qcl081_path.write_text(json.dumps(promoted_qcl081_report()), encoding="utf-8")
            qcl084_path.write_text(json.dumps(promoted_qcl084_report()), encoding="utf-8")
            matrix_sidecar_path.write_text(
                json.dumps({"$schema": PROTOCOL_EVIDENCE_MATRIX_SCHEMA, "probe_id": "QCL-081"}),
                encoding="utf-8",
            )
            os.utime(stale_qcl081_path, (1, 1))
            os.utime(latest_qcl081_path, (2, 2))
            os.utime(qcl084_path, (3, 3))
            os.utime(matrix_sidecar_path, (4, 4))

            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="latest-artifacts",
                    input=[],
                    suite_run=[],
                    latest_artifact_dir=[str(root)],
                    latest_probe_id=["QCL-081", "QCL-084"],
                    fail_on_error=True,
                )
            )

        input_paths = [item["path"] for item in matrix["inputs"]]
        self.assertIn(str(latest_qcl081_path), input_paths)
        self.assertIn(str(qcl084_path), input_paths)
        self.assertNotIn(str(stale_qcl081_path), input_paths)
        self.assertNotIn(str(matrix_sidecar_path), input_paths)
        self.assertEqual(row(matrix, "QCL-081")["source"]["artifact_path"], str(latest_qcl081_path))
        self.assertEqual(row(matrix, "QCL-081")["status"], "usable")
        self.assertEqual(row(matrix, "QCL-084")["status"], "usable")
        self.assertNotIn("QCL-081", matrix["summary"]["pending_required_probe_ids"])
        self.assertNotIn("QCL-084", matrix["summary"]["pending_required_probe_ids"])

    def test_latest_artifact_dir_loads_nested_probe_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested_root = root / "qcl082-live-20260629"
            suite_artifacts_root = root / "wpf-connectivity-suite-smoke-artifacts"
            nested_root.mkdir()
            suite_artifacts_root.mkdir()
            stale_qcl082_path = root / "qcl082-stale.json"
            latest_qcl082_path = nested_root / "qcl082-live-broker-report.json"
            suite_qcl082_path = suite_artifacts_root / "QCL-082-qcl-082-media-binary-plane-pass.json"

            stale_qcl082 = qcl082_receiver_capture_report()
            stale_qcl082["run_id"] = "qcl082-stale"
            stale_qcl082["promotion"]["allowed"] = False
            suite_qcl082 = qcl082_receiver_capture_report()
            suite_qcl082["run_id"] = "qcl082-suite-fixture-copy"
            suite_qcl082["promotion"]["allowed"] = False
            stale_qcl082_path.write_text(json.dumps(stale_qcl082), encoding="utf-8")
            latest_qcl082_path.write_text(json.dumps(qcl082_receiver_capture_report()), encoding="utf-8")
            suite_qcl082_path.write_text(json.dumps(suite_qcl082), encoding="utf-8")
            os.utime(stale_qcl082_path, (1, 1))
            os.utime(latest_qcl082_path, (2, 2))
            os.utime(suite_qcl082_path, (3, 3))

            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="latest-nested-artifacts",
                    input=[],
                    suite_run=[],
                    latest_artifact_dir=[str(root)],
                    latest_probe_id=["QCL-082"],
                    fail_on_error=True,
                )
            )

        input_paths = [item["path"] for item in matrix["inputs"]]
        self.assertIn(str(latest_qcl082_path), input_paths)
        self.assertNotIn(str(stale_qcl082_path), input_paths)
        self.assertNotIn(str(suite_qcl082_path), input_paths)
        self.assertEqual(row(matrix, "QCL-082")["source"]["artifact_path"], str(latest_qcl082_path))
        self.assertEqual(row(matrix, "QCL-082")["status"], "usable")
        self.assertEqual(row(matrix, "QCL-082")["promotion_state"], "promoted")
        self.assertEqual(row(matrix, "QCL-082")["evidence_tier"], "broker_owned")

    def test_latest_artifact_dir_prefers_promoted_qcl082_over_newer_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            promoted_root = root / "qcl082-live-20260629"
            promoted_root.mkdir()
            promoted_qcl082_path = promoted_root / "qcl082-live-broker-report.json"
            source_contract_path = root / "wpf-connectivity-suite.qcl082-media-stream-session-plan.json"

            source_contract = qcl082_source_contract_report()
            source_contract["run_id"] = "qcl082-newer-source-contract"
            promoted_qcl082_path.write_text(
                json.dumps(qcl082_receiver_capture_report()),
                encoding="utf-8",
            )
            source_contract_path.write_text(json.dumps(source_contract), encoding="utf-8")
            os.utime(promoted_qcl082_path, (1, 1))
            os.utime(source_contract_path, (5, 5))

            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="latest-prefers-promoted-qcl082",
                    input=[],
                    suite_run=[],
                    latest_artifact_dir=[str(root)],
                    latest_probe_id=["QCL-082"],
                    fail_on_error=True,
                )
            )

        input_paths = [item["path"] for item in matrix["inputs"]]
        self.assertIn(str(promoted_qcl082_path), input_paths)
        self.assertNotIn(str(source_contract_path), input_paths)
        self.assertEqual(row(matrix, "QCL-082")["source"]["artifact_path"], str(promoted_qcl082_path))
        self.assertEqual(row(matrix, "QCL-082")["status"], "usable")
        self.assertEqual(row(matrix, "QCL-082")["promotion_state"], "promoted")
        self.assertEqual(row(matrix, "QCL-082")["evidence_tier"], "broker_owned")

    def test_latest_consolidated_operator_artifacts_promote_required_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            connectivity_root = root / "connectivity"
            session_root = root / "sessions"
            nested_root = connectivity_root / "live-qcl080-artifacts"
            connectivity_root.mkdir()
            session_root.mkdir()
            nested_root.mkdir()

            stale_device_link_path = session_root / "device-link-stale.json"
            latest_device_link_path = session_root / "device-link-latest.json"
            qcl050_path = connectivity_root / "qcl050-latest.json"
            qcl051_path = connectivity_root / "qcl051-latest.json"
            qcl080_path = connectivity_root / "qcl080-live.json"
            qcl080_descriptor_path = nested_root / "qcl080-live.stream-capability.json"
            stale_qcl080_descriptor_path = connectivity_root / "qcl080-stale.stream-capability.json"
            qcl081_path = connectivity_root / "qcl081-latest.json"
            qcl083_path = connectivity_root / "qcl083-latest.json"
            qcl084_path = connectivity_root / "qcl084-latest.json"

            stale_device_link = read_json(
                REPO_ROOT / "tests" / "HostessCompanion.Wpf.Tests" / "Fixtures" / "device-link-pass.json"
            )
            stale_device_link["status"] = "warn"
            stale_device_link["command_results"][0]["applied"] = False
            stale_device_link_path.write_text(json.dumps(stale_device_link), encoding="utf-8")
            latest_device_link_path.write_text(
                (REPO_ROOT / "tests" / "HostessCompanion.Wpf.Tests" / "Fixtures" / "device-link-pass.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            qcl080 = promoted_qcl080_report()
            qcl080_path.write_text(json.dumps(qcl080), encoding="utf-8")
            qcl080_descriptor_path.write_text(
                json.dumps(
                    build_stream_capability_descriptor_from_connectivity_probe(
                        qcl080,
                        source_path=qcl080_path,
                    )
                ),
                encoding="utf-8",
            )
            stale_qcl080_descriptor = build_stream_capability_descriptor_from_connectivity_probe(
                qcl080,
                source_path=qcl080_path,
            )
            stale_qcl080_descriptor["status"] = "blocked"
            stale_qcl080_descriptor_path.write_text(json.dumps(stale_qcl080_descriptor), encoding="utf-8")

            qcl050_path.write_text(
                json.dumps(
                    read_json(
                        REPO_ROOT
                        / "fixtures"
                        / "connectivity-probe"
                        / "qcl-050-rfcomm-control-pass.json"
                    )
                ),
                encoding="utf-8",
            )
            qcl051_path.write_text(
                json.dumps(
                    read_json(
                        REPO_ROOT
                        / "fixtures"
                        / "connectivity-probe"
                        / "qcl-051-ble-gatt-status-pass.json"
                    )
                ),
                encoding="utf-8",
            )
            qcl081_path.write_text(json.dumps(promoted_qcl081_report()), encoding="utf-8")
            qcl083_path.write_text(json.dumps(promoted_qcl083_report()), encoding="utf-8")
            qcl084_path.write_text(json.dumps(promoted_qcl084_report()), encoding="utf-8")
            os.utime(stale_device_link_path, (1, 1))
            os.utime(latest_device_link_path, (2, 2))
            os.utime(stale_qcl080_descriptor_path, (3, 3))
            os.utime(qcl050_path, (4, 4))
            os.utime(qcl051_path, (5, 5))
            os.utime(qcl080_path, (6, 6))
            os.utime(qcl080_descriptor_path, (7, 7))
            os.utime(qcl081_path, (8, 8))
            os.utime(qcl083_path, (9, 9))
            os.utime(qcl084_path, (10, 10))

            matrix = build_protocol_evidence_matrix(
                argparse.Namespace(
                    out=str(root / "matrix.json"),
                    validation_out=None,
                    matrix_id="consolidated-latest",
                    input=[],
                    suite_run=[],
                    latest_artifact_dir=[str(connectivity_root)],
                    latest_probe_id=[
                        "QCL-050",
                        "QCL-051",
                        "QCL-080",
                        "QCL-081",
                        "QCL-083",
                        "QCL-084",
                    ],
                    latest_device_link_dir=[str(session_root)],
                    latest_stream_capability_dir=[str(connectivity_root)],
                    latest_stream_probe_id=["QCL-080"],
                    fail_on_error=True,
                )
            )

        input_paths = [item["path"] for item in matrix["inputs"]]
        self.assertIn(str(latest_device_link_path), input_paths)
        self.assertNotIn(str(stale_device_link_path), input_paths)
        self.assertIn(str(qcl050_path), input_paths)
        self.assertIn(str(qcl051_path), input_paths)
        self.assertIn(str(qcl080_path), input_paths)
        self.assertIn(str(qcl080_descriptor_path), input_paths)
        self.assertNotIn(str(stale_qcl080_descriptor_path), input_paths)
        self.assertEqual(row(matrix, "QCL-000")["status"], "usable")
        self.assertEqual(row(matrix, "QCL-050")["status"], "candidate")
        self.assertEqual(row(matrix, "QCL-050")["evidence_tier"], "fixture")
        self.assertEqual(row(matrix, "QCL-051")["status"], "candidate")
        self.assertEqual(row(matrix, "QCL-051")["evidence_tier"], "fixture")
        self.assertEqual(row(matrix, "QCL-080")["status"], "usable")
        self.assertEqual(row(matrix, "QCL-080")["descriptor"]["artifact_path"], str(qcl080_descriptor_path))
        self.assertEqual(row(matrix, "QCL-081")["status"], "usable")
        self.assertEqual(row(matrix, "QCL-083")["status"], "usable")
        self.assertEqual(row(matrix, "QCL-084")["status"], "usable")
        self.assertTrue(matrix["summary"]["all_required_data_protocols_promoted"])
        self.assertEqual(matrix["summary"]["pending_required_probe_ids"], [])

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

    def test_qcl000_fixture_keeps_websocket_visible_without_promotion(self) -> None:
        matrix = build_protocol_evidence_matrix(
            argparse.Namespace(
                out="unused.json",
                validation_out=None,
                matrix_id="qcl000-fixture-command",
                input=[str(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-000-usb-adb-pass.json")],
                suite_run=[],
                latest_artifact_dir=[],
                latest_probe_id=[],
                latest_device_link_dir=[],
                latest_stream_capability_dir=[],
                latest_stream_probe_id=[],
                fail_on_error=True,
            )
        )

        command = row(matrix, "QCL-000")
        self.assertEqual(command["status"], "candidate")
        self.assertEqual(command["transport_kind"], "manifold_websocket")
        self.assertEqual(command["evidence_tier"], "fixture")
        self.assertFalse(command["promotion_allowed"])
        self.assertIn("gate.qcl000.quest_runtime", command["missing_gates"])
        self.assertIn("gate.qcl000.promotion_allowed", command["missing_gates"])
        self.assertEqual(command["measurements"]["command_stages"]["applied"], "pass")
        self.assertFalse(matrix["summary"]["all_required_data_protocols_promoted"])

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
                "--latest-artifact-dir",
                "target/connectivity-probe",
                "--latest-probe-id",
                "QCL-081",
                "--latest-probe-id",
                "QCL-084",
                "--latest-device-link-dir",
                "target/companion-session",
                "--latest-stream-capability-dir",
                "target/connectivity-probe",
                "--latest-stream-probe-id",
                "QCL-080",
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
        self.assertEqual(args.latest_artifact_dir, ["target/connectivity-probe"])
        self.assertEqual(args.latest_probe_id, ["QCL-081", "QCL-084"])
        self.assertEqual(args.latest_device_link_dir, ["target/companion-session"])
        self.assertEqual(args.latest_stream_capability_dir, ["target/connectivity-probe"])
        self.assertEqual(args.latest_stream_probe_id, ["QCL-080"])
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


def qcl082_source_contract_report() -> dict[str, Any]:
    report = read_json(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-082-media-binary-plane-pass.json")
    report["run_id"] = "qcl082-media-stream-session-plan"
    report["classification"] = "protocol_fit_source_contract"
    report["transport"]["endpoint_source"] = "rusty-quest-media-stream-session-plan"
    report["host"]["toolchain_profile"] = "hostessctl.connectivity_probe.qcl082.media_stream_session_plan.fixture"
    report["promotion"]["allowed"] = False
    report["promotion"]["reason"] = (
        "Rusty Quest media-stream session plan is source-contract evidence; "
        "Quest-runtime or broker-owned binary counters remain required"
    )
    report["media_stream_session_plan"] = {
        "schema": "rusty.quest.media_stream_session.v1",
        "session_id": "session.media_stream.quest_display_composite_to_pc",
        "source": {
            "source_family": "quest-display-composite-mediaprojection",
            "source_kind": "display_composite_mediaprojection_mediacodec_surface",
            "capture_authority": "android_mediaprojection_consent",
        },
    }
    return report


def qcl082_runtime_status_report() -> dict[str, Any]:
    report = read_json(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-082-media-binary-plane-pass.json")
    report["run_id"] = "qcl082-media-stream-runtime-status"
    report["status"] = "warn"
    report["classification"] = "protocol_fit_broker_runtime_status"
    report["transport"]["endpoint_source"] = "rusty-quest-manifold-broker-media-stream-runtime"
    report["transport"]["route"] = "rusty_quest_media_stream_runtime_status"
    report["host"]["toolchain_profile"] = "hostessctl.connectivity_probe.qcl082.media_stream_runtime_status.fixture"
    report["measurements"]["media_frames_received"] = None
    report["measurements"]["media_bytes_received"] = None
    report["measurements"]["media_dropped_frames"] = None
    report["measurements"]["media_receiver_queue_depth_max"] = None
    report["promotion"]["allowed"] = False
    report["promotion"]["reason"] = (
        "Rusty Quest broker media-stream runtime status is command/source-state "
        "evidence; live binary receiver counters remain required"
    )
    report["checks"].append(
        {
            "name": "protocol.media_stream_runtime_status",
            "status": "pass",
            "summary": "Rusty Quest media-stream runtime status schema accepted",
            "observed": {
                "schema": "rusty.quest.media_stream.android_runtime_status.v1",
                "runtime_family": "media_stream",
                "session_id": "session.media_stream.test",
            },
            "issue_codes": [],
        }
    )
    report["media_stream_runtime_status"] = {
        "schema": "rusty.quest.media_stream.android_runtime_status.v1",
        "command_id": "command.media_stream.start_source",
        "session_id": "session.media_stream.test",
        "runtime_family": "media_stream",
        "status": "sender_source_unavailable",
        "source": {
            "display_frame_source": "display_composite_mediaprojection_mediacodec_surface",
            "capture_authority": "android_mediaprojection_user_consent",
            "adapter_surface_only": True,
            "production_allowed": True,
        },
    }
    return report


def qcl082_receiver_capture_report() -> dict[str, Any]:
    report = read_json(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-082-media-binary-plane-pass.json")
    report["run_id"] = "qcl082-rmanvid1-receiver-capture"
    report["classification"] = "protocol_fit_receiver_counters"
    report["transport"]["endpoint_source"] = "rusty-quest-manifold-broker-media-stream-runtime"
    report["transport"]["route"] = "hostess_rmanvid1_receiver_capture"
    report["transport"]["protocol_role"] = "binary_media_plane_receiver_counters"
    report["host"]["toolchain_profile"] = "hostessctl.connectivity_probe.qcl082.rmanvid1_receiver_capture"
    report["promotion"]["allowed"] = True
    report["promotion"]["reason"] = "RMANVID1 receiver counters are paired with live broker/Quest runtime evidence"
    report["checks"].append(
        {
            "name": "protocol.media_stream_runtime_status",
            "status": "pass",
            "summary": "receiver capture is paired with broker media-stream runtime status",
            "observed": {
                "runtime_status_path": "target/connectivity-probe/qcl082-runtime-status.json",
                "endpoint_source": "rusty-quest-manifold-broker-media-stream-runtime",
                "capture_kind": "live_broker_stream",
            },
            "issue_codes": [],
        }
    )
    report["checks"].append(
        {
            "name": "protocol.media_receiver_counters",
            "status": "pass",
            "summary": "receiver capture reports frame, byte, drop, queue, and close counters",
            "observed": {
                "video_packet_count": 24,
                "payload_bytes": 1048576,
                "dropped_frames": 0,
                "max_queue_depth_observed": 2,
                "backpressure_events": 0,
                "close_reason": "eof_after_test_window",
            },
            "issue_codes": [],
        }
    )
    report["media_stream_receiver_capture"] = {
        "schema": "rusty.hostess.media_stream.rmanvid1_capture_stats.v1",
        "capture_kind": "live_broker_stream",
        "live_capture": True,
        "source": {
            "endpoint_source": "rusty-quest-manifold-broker-media-stream-runtime",
            "runtime_status_observed": True,
        },
    }
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


def promoted_qcl083_report() -> dict[str, Any]:
    report = read_json(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-083-osc-loopback-pass.json")
    report["run_id"] = "qcl083-quest-runtime-promoted"
    report["status"] = "pass"
    report["transport"]["endpoint_source"] = "quest-runtime"
    report["transport"]["local_endpoint"] = "quest-runtime"
    report["transport"]["remote_endpoint"] = "quest-runtime"
    report["host"]["adb_provider"] = "S:/Work/tools/Android/windows-sdk/platform-tools/adb.exe"
    report["host"]["toolchain_profile"] = "hostessctl.connectivity_probe.qcl083"
    report["measurements"]["osc_messages_requested"] = 16
    report["measurements"]["osc_messages_received"] = 16
    report["measurements"]["osc_loss_percent"] = 0.0
    report["promotion"]["allowed"] = True
    report["promotion"]["reason"] = "QCL-083 proves Quest/runtime-owned OSC payload exchange"
    report["osc_payload_probe"] = {
        "status": "pass",
        "source": "quest-runtime",
        "messages_requested": 16,
        "messages_received": 16,
        "messages_acknowledged": 16,
        "loss_percent": 0.0,
        "evidence_tier": "quest_runtime",
        "authority_owner": "rusty.quest.device_link",
        "issue_codes": [],
    }
    return report


def promoted_qcl081_report() -> dict[str, Any]:
    report = read_json(REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-081-lsl-loopback-pass.json")
    report["run_id"] = "qcl081-manifold-lsl-broker-promoted"
    report["status"] = "pass"
    report["transport"]["endpoint_source"] = "manifold-lsl-broker"
    report["transport"]["local_endpoint"] = "manifold-lsl-broker"
    report["transport"]["remote_endpoint"] = "manifold-lsl-broker"
    report["host"]["adb_provider"] = ""
    report["host"]["toolchain_profile"] = "hostessctl.connectivity_probe.qcl081"
    report["promotion"]["allowed"] = True
    report["promotion"]["reason"] = "QCL-081 proves Manifold-owned LSL producer/sample continuity"
    report["lsl_payload_probe"] = {
        "status": "pass",
        "source": "manifold-lsl-broker",
        "stream_name": "RustyQCL081",
        "stream_type": "Markers",
        "source_id": "rusty-manifold-qcl081-fixture",
        "samples_requested": 16,
        "samples_received": 16,
        "loss_percent": 0.0,
        "discovery_ms": 42,
        "monotonic_sequences": True,
        "received_sequences": list(range(16)),
        "evidence_tier": "broker_owned",
        "authority_owner": "rusty.manifold.transport",
        "route_id": "bridge_route.clock.lsl.roundtrip_echo",
        "bridge_route_evidence": {
            "$schema": "rusty.manifold.bridge.route_evidence.v1",
            "route_id": "bridge_route.clock.lsl.roundtrip_echo",
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
