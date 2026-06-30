from __future__ import annotations

from tools.connectivity_probe_tests.helpers import *


class HostessCtlConnectivityProbeWebSocketDataProtocolTests(unittest.TestCase):
    def test_qcl083_fixture_validates_osc_loopback_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-083", fixture_profile="qcl-083-osc-loopback-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-083")
        self.assertEqual(report["transport"]["family"], "osc")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "protocol.osc_message_shape")["status"], "pass")
        self.assertEqual(check(report, "protocol.osc_payload_exchange")["status"], "pass")
        self.assertEqual(report["measurements"]["osc_messages_received"], 16)
        self.assertEqual(validation["status"], "pass")

    def test_qcl083_damaged_fixture_reports_malformed_packet(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-083", fixture_profile="qcl-083-osc-malformed-packet"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "protocol.osc_message_shape")["status"], "fail")
        self.assertEqual(check(report, "protocol.osc_payload_exchange")["status"], "fail")
        self.assertEqual(validation["status"], "pass")

    def test_qcl084_fixture_validates_zeromq_loopback_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-084", fixture_profile="qcl-084-zeromq-loopback-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-084")
        self.assertEqual(report["transport"]["family"], "zeromq")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "protocol.zeromq_dependency")["status"], "pass")
        self.assertEqual(check(report, "protocol.zeromq_payload_exchange")["status"], "pass")
        self.assertEqual(report["measurements"]["zeromq_messages_received"], 5)
        self.assertEqual(validation["status"], "pass")

    def test_qcl084_damaged_fixture_reports_dependency_missing(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-084", fixture_profile="qcl-084-zeromq-dependency-missing"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "protocol.zeromq_dependency")["status"], "blocked")
        self.assertEqual(check(report, "protocol.zeromq_payload_exchange")["status"], "blocked")
        self.assertEqual(validation["status"], "pass")

    def test_qcl079_fixture_validates_websocket_loopback_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-079", fixture_profile="qcl-079-websocket-loopback-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-079")
        self.assertEqual(report["transport"]["family"], "websocket")
        self.assertEqual(report["transport"]["protocol_role"], "generic_websocket_protocol_fit")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "protocol.websocket_handshake")["status"], "pass")
        self.assertEqual(check(report, "protocol.websocket_payload_exchange")["status"], "pass")
        self.assertEqual(check(report, "protocol.websocket_not_command_authority")["status"], "pass")
        self.assertEqual(report["measurements"]["websocket_messages_received"], 16)
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl079_damaged_fixture_reports_handshake_blocked(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-079", fixture_profile="qcl-079-websocket-handshake-blocked"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "protocol.websocket_handshake")["status"], "blocked")
        self.assertEqual(check(report, "protocol.websocket_payload_exchange")["status"], "fail")
        self.assertEqual(validation["status"], "pass")

    def test_live_websocket_report_runs_bounded_host_loopback_echo(self) -> None:
        report = live_websocket_report(
            probe_args(
                mode="live",
                probe_id="QCL-079",
                websocket_bind_host="127.0.0.1",
                websocket_port=0,
                websocket_message_count=3,
                websocket_payload_bytes=48,
                websocket_timeout_seconds=1.0,
            ),
            clock_func=fixed_datetime,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-079")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["endpoint_source"], "host-loopback")
        self.assertEqual(check(report, "protocol.websocket_handshake")["status"], "pass")
        self.assertEqual(check(report, "protocol.websocket_payload_exchange")["status"], "pass")
        self.assertEqual(report["measurements"]["websocket_messages_requested"], 3)
        self.assertEqual(report["measurements"]["websocket_messages_received"], 3)
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl079_accepts_manifold_stream_websocket_route_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            descriptor, evidence = write_websocket_route_files(root)

            report = live_websocket_report(
                probe_args(
                    mode="live",
                    probe_id="QCL-079",
                    websocket_source="broker-owned-websocket",
                    websocket_route_descriptor=str(descriptor),
                    websocket_route_evidence=str(evidence),
                    websocket_message_count=8,
                    websocket_payload_bytes=128,
                ),
                clock_func=fixed_datetime,
            )
            validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-079")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["endpoint_source"], "broker-owned-websocket")
        self.assertEqual(report["websocket_bridge_route"]["route_id"], "bridge_route.stream.websocket.ordered")
        self.assertEqual(check(report, "protocol.websocket_handshake")["status"], "pass")
        self.assertEqual(check(report, "protocol.websocket_payload_exchange")["status"], "pass")
        self.assertEqual(check(report, "protocol.websocket_not_command_authority")["status"], "pass")
        self.assertEqual(report["measurements"]["websocket_messages_requested"], 8)
        self.assertEqual(report["measurements"]["websocket_messages_received"], 8)
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl079_rejects_manifold_command_websocket_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            descriptor, evidence = write_websocket_route_files(root, command_route=True)

            report = live_websocket_report(
                probe_args(
                    mode="live",
                    probe_id="QCL-079",
                    websocket_source="broker-owned-websocket",
                    websocket_route_descriptor=str(descriptor),
                    websocket_route_evidence=str(evidence),
                ),
                clock_func=fixed_datetime,
            )
            validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "protocol.websocket_not_command_authority")["status"], "fail")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertIn(
            "hostess.issue.connectivity_probe.websocket_command_route_not_generic",
            [issue["issue_code"] for issue in report["issues"]],
        )
        self.assertEqual(validation["status"], "pass")
