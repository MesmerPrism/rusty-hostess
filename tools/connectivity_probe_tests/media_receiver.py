from __future__ import annotations

from tools.connectivity_probe_tests.helpers import *


class HostessCtlConnectivityProbeMediaReceiverTests(unittest.TestCase):
    def test_qcl082_media_stream_session_plan_validates_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "display-composite-mediaprojection-h264.plan.json"
            plan_path.write_text(json.dumps(media_stream_session_plan()), encoding="utf-8")
            report = fixture_report(
                probe_args(probe_id="QCL-082", media_stream_session_plan=str(plan_path)),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-082")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["endpoint_source"], "rusty-quest-media-stream-session-plan")
        self.assertEqual(report["transport"]["packet_magic"], "RMANVID1")
        self.assertEqual(check(report, "protocol.media_stream_session_contract")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_binary_transport")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_source_classification")["status"], "pass")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(
            report["media_stream_session_plan"]["source"]["source_kind"],
            "display_composite_mediaprojection_mediacodec_surface",
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_media_stream_session_plan_rejects_high_rate_json_media(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "media-stream-high-rate-json.plan.json"
            plan_path.write_text(
                json.dumps(media_stream_session_plan(high_rate_payload_plane="control-json")),
                encoding="utf-8",
            )
            report = fixture_report(
                probe_args(probe_id="QCL-082", media_stream_session_plan=str(plan_path)),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "protocol.media_binary_transport")["status"], "fail")
        self.assertEqual(check(report, "protocol.media_high_rate_json_guard")["status"], "fail")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.media_high_rate_json_payload"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_media_stream_session_plan_rejects_shell_display_production(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "media-stream-shell-display-production.plan.json"
            plan_path.write_text(
                json.dumps(media_stream_session_plan(shell_display=True, shell_display_production=True)),
                encoding="utf-8",
            )
            report = fixture_report(
                probe_args(probe_id="QCL-082", media_stream_session_plan=str(plan_path)),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "protocol.media_shell_lab_gate")["status"], "fail")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.shell_display_route_not_lab_only"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_media_stream_runtime_status_validates_broker_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status_path = Path(tmpdir) / "media-stream-runtime-status.json"
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            report = fixture_report(
                probe_args(probe_id="QCL-082", media_stream_runtime_status=str(status_path)),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-082")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(
            report["transport"]["endpoint_source"],
            "rusty-quest-manifold-broker-media-stream-runtime",
        )
        self.assertEqual(check(report, "protocol.media_stream_runtime_status")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_stream_command_ack")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_binary_transport")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_binary_runtime_counters")["status"], "blocked")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(
            report["media_stream_runtime_status"]["source"]["display_frame_source"],
            "display_composite_mediaprojection_mediacodec_surface",
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_media_stream_runtime_status_accepts_live_android_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status_path = Path(tmpdir) / "media-stream-start-source.live-android-execution.json"
            status_path.write_text(
                json.dumps(
                    {
                        "$schema": "rusty.hostess.bridge_command.live_android_execution_evidence.v1",
                        "status": "pass",
                        "command": "command.media_stream.start_source",
                        "command_execution": {
                            "$schema": "rusty.hostess.bridge_command.execution_evidence.v1",
                            "status": "pass",
                            "broker_messages": [media_stream_runtime_ack()],
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = fixture_report(
                probe_args(probe_id="QCL-082", media_stream_runtime_status=str(status_path)),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-082")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(check(report, "protocol.media_stream_runtime_status")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_stream_command_ack")["status"], "pass")
        self.assertEqual(
            report["media_stream_runtime_status"]["artifact_path"],
            str(status_path),
        )
        self.assertEqual(
            report["media_stream_runtime_status"]["command_id"],
            "command.media_stream.start_source",
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_media_stream_runtime_status_rejects_high_rate_json_media(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            status_path = Path(tmpdir) / "media-stream-runtime-status.json"
            status_path.write_text(
                json.dumps(media_stream_runtime_ack(high_rate_json_payload=True)),
                encoding="utf-8",
            )
            report = fixture_report(
                probe_args(probe_id="QCL-082", media_stream_runtime_status=str(status_path)),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "protocol.media_binary_transport")["status"], "fail")
        self.assertEqual(check(report, "protocol.media_high_rate_json_guard")["status"], "fail")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.media_high_rate_json_payload"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_rmanvid1_receiver_capture_validates_counters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            status_path = root / "media-stream-runtime-status.json"
            capture_path.write_bytes(rmanvid1_capture_bytes())
            sidecar_path.write_text(json.dumps(media_stream_receiver_sidecar()), encoding="utf-8")
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_rmanvid1_capture=str(capture_path),
                    media_stream_receiver_sidecar=str(sidecar_path),
                    media_stream_runtime_status=str(status_path),
                ),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-082")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(
            report["transport"]["endpoint_source"],
            "rusty-quest-manifold-broker-media-stream-runtime",
        )
        self.assertEqual(check(report, "protocol.media_receiver_capture")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_stream_runtime_status")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_packet_boundaries")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_timestamp_policy")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_backpressure_policy")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_receiver_counters")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_product_topology_gate")["status"], "skipped")
        self.assertEqual(report["measurements"]["media_frames_received"], 3)
        self.assertEqual(report["measurements"]["media_bytes_received"], 41)
        self.assertEqual(report["measurements"]["media_dropped_frames"], 0)
        self.assertEqual(report["measurements"]["media_receiver_queue_depth_max"], 2)
        self.assertFalse(report["measurements"]["media_product_topology_ready"])
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_rmanvid1_receiver_capture_allows_live_broker_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            status_path = root / "media-stream-runtime-status.json"
            capture_path.write_bytes(rmanvid1_capture_bytes())
            sidecar_path.write_text(
                json.dumps(media_stream_receiver_sidecar(capture_kind="live_broker_stream")),
                encoding="utf-8",
            )
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_rmanvid1_capture=str(capture_path),
                    media_stream_receiver_sidecar=str(sidecar_path),
                    media_stream_runtime_status=str(status_path),
                ),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(report["media_stream_receiver_capture"]["capture_kind"], "live_broker_stream")
        self.assertTrue(report["media_stream_receiver_capture"]["source"]["broker_or_quest_source"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_rmanvid1_receiver_capture_warns_until_direct_wifi_topology_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            status_path = root / "media-stream-runtime-status.json"
            topology_path = root / "qcl040-topology.json"
            capture_path.write_bytes(rmanvid1_capture_bytes())
            sidecar_path.write_text(
                json.dumps(media_stream_receiver_sidecar(capture_kind="live_broker_stream")),
                encoding="utf-8",
            )
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            topology_report = fixture_report(
                probe_args(
                    probe_id="QCL-040",
                    fixture_profile="qcl-040-wifi-direct-phone-peer-pass",
                ),
                observed_at=fixed_datetime(),
            )
            topology_path.write_text(json.dumps(topology_report), encoding="utf-8")
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_rmanvid1_capture=str(capture_path),
                    media_stream_receiver_sidecar=str(sidecar_path),
                    media_stream_runtime_status=str(status_path),
                    media_stream_topology_report=str(topology_path),
                ),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)
        product_gate = check(report, "protocol.media_product_topology_gate")

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(product_gate["status"], "warn")
        self.assertFalse(product_gate["observed"]["product_gate_proven"])
        self.assertFalse(report["media_stream_receiver_capture"]["product_topology"]["ready"])
        self.assertIn(
            "hostess.issue.connectivity_probe.media_direct_wifi_topology_not_promoted",
            product_gate["issue_codes"],
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_rmanvid1_receiver_capture_accepts_promoted_direct_wifi_product_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            status_path = root / "media-stream-runtime-status.json"
            topology_path = root / "qcl040-topology.json"
            capture_path.write_bytes(rmanvid1_capture_bytes())
            sidecar_path.write_text(
                json.dumps(media_stream_receiver_sidecar(capture_kind="live_broker_stream")),
                encoding="utf-8",
            )
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            topology_report = fixture_report(
                probe_args(
                    probe_id="QCL-040",
                    fixture_profile="qcl-040-wifi-direct-phone-peer-pass",
                ),
                observed_at=fixed_datetime(),
            )
            topology_report["promotion"]["allowed"] = True
            topology_report["promotion"]["reason"] = "unit test promoted direct-Wi-Fi topology"
            topology_path.write_text(json.dumps(topology_report), encoding="utf-8")
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_rmanvid1_capture=str(capture_path),
                    media_stream_receiver_sidecar=str(sidecar_path),
                    media_stream_runtime_status=str(status_path),
                    media_stream_topology_report=str(topology_path),
                ),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)
        product_gate = check(report, "protocol.media_product_topology_gate")

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(product_gate["status"], "pass")
        self.assertEqual(product_gate["observed"]["product_gate"], "product_tcp_media_over_direct_wifi")
        self.assertTrue(product_gate["observed"]["product_gate_proven"])
        self.assertTrue(report["measurements"]["media_product_topology_ready"])
        self.assertTrue(report["media_stream_receiver_capture"]["product_topology"]["ready"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_rmanvid1_receiver_capture_accepts_verified_product_tcp_firewall(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            status_path = root / "media-stream-runtime-status.json"
            firewall_path = root / "qcl082-tcp-firewall-verify.json"
            capture_path.write_bytes(rmanvid1_capture_bytes())
            sidecar_path.write_text(
                json.dumps(media_stream_receiver_sidecar(capture_kind="live_broker_stream")),
                encoding="utf-8",
            )
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            firewall_report = media_stream_firewall_report()
            self.assertEqual(
                firewall_report["rule"]["name"],
                "Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079",
            )
            self.assertEqual(
                firewall_report["verification"]["listener_firewall"]["expected_rule_name"],
                "Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079",
            )
            firewall_path.write_text(json.dumps(firewall_report), encoding="utf-8")
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_rmanvid1_capture=str(capture_path),
                    media_stream_receiver_sidecar=str(sidecar_path),
                    media_stream_runtime_status=str(status_path),
                    media_stream_firewall_report=str(firewall_path),
                ),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)
        product_gate = check(report, "protocol.media_product_listener_firewall_gate")

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(product_gate["status"], "pass")
        self.assertEqual(product_gate["observed"]["product_gate"], "product_tcp_media_listener_firewall_verified")
        self.assertTrue(product_gate["observed"]["product_gate_proven"])
        self.assertTrue(report["measurements"]["media_product_listener_firewall_verified"])
        self.assertTrue(report["media_stream_receiver_capture"]["product_listener_firewall"]["ready"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_rmanvid1_receiver_capture_rejects_diagnostic_tcp_firewall(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            status_path = root / "media-stream-runtime-status.json"
            firewall_path = root / "qcl082-tcp-firewall-verify.json"
            capture_path.write_bytes(rmanvid1_capture_bytes())
            sidecar_path.write_text(
                json.dumps(media_stream_receiver_sidecar(capture_kind="live_broker_stream")),
                encoding="utf-8",
            )
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            firewall_path.write_text(
                json.dumps(media_stream_firewall_report(program="C:\\Python311\\python.exe")),
                encoding="utf-8",
            )
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_rmanvid1_capture=str(capture_path),
                    media_stream_receiver_sidecar=str(sidecar_path),
                    media_stream_runtime_status=str(status_path),
                    media_stream_firewall_report=str(firewall_path),
                ),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)
        product_gate = check(report, "protocol.media_product_listener_firewall_gate")

        self.assertEqual(report["status"], "pass")
        self.assertEqual(product_gate["status"], "blocked")
        self.assertFalse(product_gate["observed"]["product_gate_proven"])
        self.assertIn(
            "hostess.issue.connectivity_probe.media_listener_firewall_program_diagnostic",
            product_gate["issue_codes"],
        )
        self.assertFalse(report["measurements"]["media_product_listener_firewall_verified"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_rmanvid1_receiver_capture_rejects_invalid_magic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            status_path = root / "media-stream-runtime-status.json"
            capture_path.write_bytes(rmanvid1_capture_bytes(invalid_magic=True))
            sidecar_path.write_text(json.dumps(media_stream_receiver_sidecar()), encoding="utf-8")
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_rmanvid1_capture=str(capture_path),
                    media_stream_receiver_sidecar=str(sidecar_path),
                    media_stream_runtime_status=str(status_path),
                ),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "protocol.media_receiver_capture")["status"], "fail")
        self.assertEqual(check(report, "protocol.media_binary_transport")["status"], "fail")
        self.assertTrue(
            any(
                issue["issue_code"]
                == "hostess.issue.connectivity_probe.media_receiver_capture_magic_invalid"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_rmanvid1_receiver_capture_command_captures_loopback_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "captured.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            result_path = root / "receiver-result.json"
            status_path = root / "runtime-status.json"
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            topology_path = root / "qcl040-topology.json"
            port = free_tcp_port()
            args = probe_args(
                connectivity_probe_command="rmanvid1-receiver-capture",
                out=str(result_path),
                capture_out=str(capture_path),
                sidecar_out=str(sidecar_path),
                bind_host="127.0.0.1",
                port=port,
                timeout_seconds=2.0,
                max_packets=4,
                max_bytes=1048576,
                max_packet_bytes=4194304,
                max_metadata_bytes=262144,
                queue_capacity_packets=48,
                capture_kind="fixture_loopback_receiver",
                source_endpoint_source="",
                source_remote_endpoint="127.0.0.1:8879",
                command_id="command.media_stream.start_source",
                session_id="session.media_stream.test",
                runtime_status=str(status_path),
                topology_report=str(topology_path),
                fail_on_error=True,
            )
            result: dict[str, int | None] = {"code": None}
            thread = threading.Thread(
                target=lambda: result.__setitem__("code", run_rmanvid1_receiver_capture(args)),
                daemon=True,
            )
            thread.start()
            send_rmanvid1_loopback_payload(port, rmanvid1_capture_bytes())
            thread.join(timeout=4.0)

            self.assertFalse(thread.is_alive())
            self.assertEqual(result["code"], 0)
            receipt = json.loads(result_path.read_text(encoding="utf-8"))
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_rmanvid1_capture=str(capture_path),
                    media_stream_receiver_sidecar=str(sidecar_path),
                    media_stream_runtime_status=str(status_path),
                    media_stream_topology_report=str(topology_path),
                ),
                observed_at=fixed_datetime(),
            )

        self.assertEqual(receipt["status"], "pass")
        self.assertEqual(receipt["close_reason"], "max_packets_reached")
        self.assertEqual(receipt["capture_stats"]["packet_count"], 4)
        self.assertEqual(sidecar["receiver"]["arrival_timestamped_packet_count"], 4)
        self.assertEqual(sidecar["receiver"]["max_queue_depth_observed"], 1)
        self.assertEqual(sidecar["source"]["topology_report_path"], str(topology_path))
        self.assertIn("--media-stream-rmanvid1-capture", receipt["follow_on_qcl082_args"])
        self.assertIn("--media-stream-topology-report", receipt["follow_on_qcl082_args"])
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "protocol.media_receiver_capture")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_timestamp_policy")["status"], "pass")
