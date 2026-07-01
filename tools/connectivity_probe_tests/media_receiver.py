from __future__ import annotations

from tools.connectivity_probe_tests.helpers import *
from tools.hostessctl.connectivity_direct_wifi_product_media_plan import (
    DIRECT_WIFI_PRODUCT_MEDIA_PLAN_SCHEMA,
    direct_wifi_product_media_plan,
    run_direct_wifi_product_media_plan,
)
from tools.hostessctl.connectivity_media_product_plan import (
    PRODUCT_MEDIA_DIRECT_WIFI_PLAN_SCHEMA,
    qcl082_product_media_direct_wifi_plan,
    run_qcl082_product_media_direct_wifi_plan,
)


class HostessCtlConnectivityProbeMediaReceiverTests(unittest.TestCase):
    def test_direct_wifi_product_media_acceptance_plan_lists_remaining_gate_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "direct-wifi-product-media-acceptance-plan.json"
            status = run_direct_wifi_product_media_plan(
                probe_args(
                    connectivity_probe_command="direct-wifi-product-media-plan",
                    out=str(out),
                    qcl040_topology_report="target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json",
                    qcl041_topology_report="target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
                    firewall_report="target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                    qcl082_report="target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
                    adb="S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                    serial="<quest-serial>",
                ),
                clock_func=fixed_datetime,
            )
            report = json.loads(out.read_text(encoding="utf-8"))

        action_ids = [action["action_id"] for action in report["commands"]]
        command_text = "\n".join(action["command"] for action in report["commands"])

        self.assertEqual(status, 0)
        self.assertEqual(report["schema"], DIRECT_WIFI_PRODUCT_MEDIA_PLAN_SCHEMA)
        self.assertEqual(report["status"], "planned")
        self.assertFalse(report["readiness"]["direct_wifi_topology_ready"])
        self.assertFalse(report["readiness"]["ready_for_qcl082_receiver_capture"])
        self.assertFalse(report["readiness"]["product_tcp_media_over_direct_wifi_ready"])
        self.assertIn("transport.direct_wifi_live_topology", report["product_gates"])
        self.assertIn("transport.product_tcp_media_over_direct_wifi", report["product_gates"])
        self.assertIn("qcl040_normalize_qcl040_wifi_direct_lifecycle_report", action_ids)
        self.assertIn("qcl041_normalize_qcl041_wifi_direct_lifecycle_report", action_ids)
        self.assertIn("qcl082_run_qcl082_product_media_live_session", action_ids)
        self.assertIn("qcl082_capture_rmanvid1_over_promoted_direct_wifi", action_ids)
        self.assertIn("build_protocol_matrix_after_qcl082_product_media", action_ids)
        self.assertIn("wifi-direct-lifecycle-plan", command_text)
        self.assertIn("qcl082-product-media-plan", command_text)
        self.assertIn("qcl082-product-media-live-session", command_text)
        self.assertIn("rmanvid1-receiver-capture", command_text)
        self.assertIn("--quest-lease-id", command_text)
        self.assertIn("--quest-lease-resource", command_text)
        self.assertIn("--quest-lease-reserved-before-live-steps", command_text)
        self.assertIn("protocol-matrix", command_text)
        self.assertIn("companion-report projection", command_text)
        self.assertIn("--firewall-rule", command_text)
        self.assertIn("--direct-wifi-product-media-plan", command_text)
        self.assertIn("companion-report transport-gates", command_text)

    def test_direct_wifi_product_media_acceptance_plan_surfaces_preflight_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            preflight_path = root / "qcl041-live-wifi-direct-preflight.json"
            preflight = live_direct_wifi_topology_report(
                probe_args(mode="live", probe_id="QCL-041", host_ip="192.0.2.10"),
                run_captured_func=FakeRunner(),
                clock_func=fixed_datetime,
                host_ipv4_func=lambda: [
                    {
                        "ip": "192.0.2.10",
                        "prefix_length": 24,
                        "interface": "fixture",
                    }
                ],
            )
            preflight_path.write_text(json.dumps(preflight), encoding="utf-8")

            report = direct_wifi_product_media_plan(
                probe_args(
                    connectivity_probe_command="direct-wifi-product-media-plan",
                    out=str(root / "plan.json"),
                    qcl041_preflight_report=str(preflight_path),
                    firewall_report="target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                    qcl082_report="target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
                ),
                observed_at=fixed_datetime(),
            )

        preflight_check = check(
            {"checks": report["checks"]},
            "direct_wifi_product_media.direct_wifi_preflight_observation",
        )
        self.assertFalse(report["readiness"]["direct_wifi_topology_ready"])
        self.assertTrue(report["readiness"]["direct_wifi_preflight_observed"])
        self.assertTrue(report["readiness"]["direct_wifi_preflight_blocked"])
        self.assertEqual(preflight_check["status"], "blocked")
        self.assertIn(
            "hostess.issue.connectivity_probe.wifi_direct_live_peer_discovery_missing",
            preflight_check["issue_codes"],
        )
        self.assertNotIn(
            "hostess.issue.connectivity_probe.wifi_direct_live_preflight_missing",
            preflight_check["issue_codes"],
        )
        self.assertEqual(
            preflight_check["observed"]["qcl041"]["report_path"],
            str(preflight_path),
        )
        self.assertIn("preflight blockers", report["next_step"])

    def test_direct_wifi_product_media_acceptance_plan_detects_ready_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "qcl041-lifecycle.json"
            topology_path = root / "qcl041-live-wifi-direct-lifecycle.json"
            firewall_path = root / "qcl082-tcp-firewall-verify.json"
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            status_path = root / "media-stream-runtime-status.json"
            qcl082_path = root / "qcl082-rmanvid1-receiver-capture.json"

            lifecycle_path.write_text(
                json.dumps(wifi_direct_lifecycle_artifact(probe_id="QCL-041")),
                encoding="utf-8",
            )
            run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(topology_path),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            firewall_path.write_text(json.dumps(media_stream_firewall_report()), encoding="utf-8")
            capture_path.write_bytes(rmanvid1_capture_bytes())
            sidecar_path.write_text(
                json.dumps(media_stream_receiver_sidecar(capture_kind="live_broker_stream")),
                encoding="utf-8",
            )
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            qcl082_report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_rmanvid1_capture=str(capture_path),
                    media_stream_receiver_sidecar=str(sidecar_path),
                    media_stream_runtime_status=str(status_path),
                    media_stream_topology_report=str(topology_path),
                    media_stream_firewall_report=str(firewall_path),
                ),
                observed_at=fixed_datetime(),
            )
            qcl082_path.write_text(json.dumps(qcl082_report), encoding="utf-8")

            report = direct_wifi_product_media_plan(
                probe_args(
                    connectivity_probe_command="direct-wifi-product-media-plan",
                    out=str(root / "plan.json"),
                    qcl041_topology_report=str(topology_path),
                    firewall_report=str(firewall_path),
                    qcl082_report=str(qcl082_path),
                ),
                observed_at=fixed_datetime(),
            )

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["readiness"]["direct_wifi_topology_ready"])
        self.assertTrue(report["readiness"]["product_listener_firewall_ready"])
        self.assertTrue(report["readiness"]["ready_for_qcl082_receiver_capture"])
        self.assertTrue(report["readiness"]["product_tcp_media_over_direct_wifi_ready"])
        self.assertTrue(report["readiness"]["all_remaining_transport_gates_ready"])
        self.assertEqual(
            report["dependencies"][0]["selected"]["selected_candidate_id"],
            "qcl041_lifecycle_topology",
        )
        self.assertEqual(
            check({"checks": report["checks"]}, "direct_wifi_product_media.qcl082_product_media_dependency")["status"],
            "pass",
        )

    def test_qcl082_product_media_direct_wifi_plan_lists_cli_owned_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "qcl082-product-media-direct-wifi-plan.json"
            status = run_qcl082_product_media_direct_wifi_plan(
                probe_args(
                    connectivity_probe_command="qcl082-product-media-plan",
                    out=str(out),
                    promoted_topology_report="target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
                    firewall_report="target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                    adb="S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                    serial="<quest-serial>",
                ),
                clock_func=fixed_datetime,
            )
            report = json.loads(out.read_text(encoding="utf-8"))

        action_ids = [action["action_id"] for action in report["commands"]]
        command_text = "\n".join(action["command"] for action in report["commands"])

        self.assertEqual(status, 0)
        self.assertEqual(report["schema"], PRODUCT_MEDIA_DIRECT_WIFI_PLAN_SCHEMA)
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["product_gate"], "product_tcp_media_over_direct_wifi")
        self.assertFalse(report["readiness"]["ready_for_receiver_capture"])
        self.assertEqual(report["lease"]["resource"], "quest:<quest-serial>")
        self.assertIn("write_qcl082_media_stream_start_source_request", action_ids)
        self.assertIn("run_qcl082_media_stream_start_source", action_ids)
        self.assertIn("run_qcl082_product_media_live_session", action_ids)
        self.assertIn("capture_rmanvid1_over_promoted_direct_wifi", action_ids)
        self.assertIn("promote_qcl082_rmanvid1_capture", action_ids)
        self.assertIn("emit-bridge-command-request", command_text)
        self.assertIn("run-bridge-command-live-android", command_text)
        self.assertIn("qcl082-product-media-live-session", command_text)
        self.assertIn("rmanvid1-receiver-capture", command_text)
        self.assertIn("--media-stream-receiver-result", command_text)
        self.assertIn("media-stream-receiver-result.json", command_text)
        self.assertIn("--quest-lease-id", command_text)
        self.assertIn("--quest-lease-resource", command_text)
        self.assertIn("--quest-lease-reserved-before-live-steps", command_text)

    def test_qcl082_product_media_direct_wifi_plan_binds_lease_resource_to_serial(self) -> None:
        report = qcl082_product_media_direct_wifi_plan(
            probe_args(
                connectivity_probe_command="qcl082-product-media-plan",
                out="unused.json",
                promoted_topology_report="target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
                firewall_report="target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                adb="S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                serial="3487C10H3M017Q",
            ),
            observed_at=fixed_datetime(),
        )

        command_text = "\n".join(action["command"] for action in report["commands"])
        self.assertEqual(report["lease"]["resource"], "quest:3487C10H3M017Q")
        self.assertTrue(report["policy"]["requires_media_lease_matches_topology_serial"])
        self.assertIn("--serial '3487C10H3M017Q'", command_text)
        self.assertIn("--quest-lease-resource 'quest:3487C10H3M017Q'", command_text)

    def test_qcl082_product_media_direct_wifi_plan_detects_ready_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "qcl041-lifecycle.json"
            topology_path = root / "qcl041-live-wifi-direct-lifecycle.json"
            firewall_path = root / "qcl082-tcp-firewall-verify.json"
            lifecycle_path.write_text(
                json.dumps(wifi_direct_lifecycle_artifact(probe_id="QCL-041")),
                encoding="utf-8",
            )
            run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(topology_path),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            firewall_path.write_text(json.dumps(media_stream_firewall_report()), encoding="utf-8")
            report = qcl082_product_media_direct_wifi_plan(
                probe_args(
                    connectivity_probe_command="qcl082-product-media-plan",
                    out=str(root / "plan.json"),
                    promoted_topology_report=str(topology_path),
                    firewall_report=str(firewall_path),
                ),
                observed_at=fixed_datetime(),
            )

        dependencies = {
            dependency["gate_id"]: dependency
            for dependency in report["dependencies"]
        }
        self.assertTrue(dependencies["transport.direct_wifi_live_topology"]["ready"])
        self.assertTrue(dependencies["transport.product_tcp_media_listener_firewall"]["ready"])
        self.assertTrue(report["readiness"]["ready_for_receiver_capture"])
        self.assertEqual(check({"checks": report["checks"]}, "qcl082.product_media_direct_wifi_dependency")["status"], "pass")
        self.assertEqual(check({"checks": report["checks"]}, "qcl082.product_media_listener_firewall_dependency")["status"], "pass")

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
            topology_report["device"]["serial"] = "TESTQUESTSERIAL"
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

    def test_qcl082_rmanvid1_receiver_capture_blocks_product_gate_when_topology_serial_mismatches_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            status_path = root / "media-stream-runtime-status.json"
            lifecycle_path = root / "qcl041-lifecycle.json"
            topology_path = root / "qcl041-live-wifi-direct-lifecycle.json"
            capture_path.write_bytes(rmanvid1_capture_bytes())
            sidecar_path.write_text(
                json.dumps(media_stream_receiver_sidecar(capture_kind="live_broker_stream")),
                encoding="utf-8",
            )
            status_path.write_text(json.dumps(media_stream_runtime_ack()), encoding="utf-8")
            lifecycle_artifact = wifi_direct_lifecycle_artifact(probe_id="QCL-041")
            lifecycle_artifact["device"]["serial"] = "OTHERQUESTSERIAL"
            lifecycle_artifact["lease"]["resource"] = "quest:OTHERQUESTSERIAL"
            lifecycle_path.write_text(json.dumps(lifecycle_artifact), encoding="utf-8")
            run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(topology_path),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
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
        self.assertEqual(product_gate["status"], "blocked")
        self.assertFalse(product_gate["observed"]["product_gate_proven"])
        self.assertEqual(product_gate["observed"]["topology_device_serial"], "OTHERQUESTSERIAL")
        self.assertEqual(product_gate["observed"]["media_receiver_quest_serial"], "TESTQUESTSERIAL")
        self.assertFalse(product_gate["observed"]["topology_lease_serial_matches"])
        self.assertIn(
            "hostess.issue.connectivity_probe.media_direct_wifi_topology_lease_serial_mismatch",
            product_gate["issue_codes"],
        )
        self.assertFalse(report["media_stream_receiver_capture"]["product_topology"]["ready"])
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

    def test_qcl082_receiver_result_rejects_wrong_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "media-stream.rmanvid1"
            result_path = root / "receiver-result.json"
            capture_path.write_bytes(rmanvid1_capture_bytes())
            result_path.write_text(
                json.dumps(
                    {
                        "schema": "wrong.receiver.result.schema",
                        "status": "pass",
                        "capture_path": str(capture_path),
                    }
                ),
                encoding="utf-8",
            )
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_receiver_result=str(result_path),
                ),
                observed_at=fixed_datetime(),
            )
        validation = validate_connectivity_probe_report(report)
        receiver_result_check = check(report, "protocol.media_receiver_result")

        self.assertEqual(report["status"], "fail")
        self.assertEqual(receiver_result_check["status"], "fail")
        self.assertIn(
            "hostess.issue.connectivity_probe.media_receiver_result_schema_mismatch",
            receiver_result_check["issue_codes"],
        )
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
        self.assertIn("--media-stream-receiver-result", receipt["follow_on_qcl082_args"])
        self.assertIn(str(result_path), receipt["follow_on_qcl082_args"])
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "protocol.media_receiver_capture")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_timestamp_policy")["status"], "pass")

    def test_qcl082_rmanvid1_live_receiver_blocks_without_product_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            capture_path = root / "captured.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            result_path = root / "receiver-result.json"
            status = run_rmanvid1_receiver_capture(
                probe_args(
                    connectivity_probe_command="rmanvid1-receiver-capture",
                    out=str(result_path),
                    capture_out=str(capture_path),
                    sidecar_out=str(sidecar_path),
                    bind_host="127.0.0.1",
                    port=free_tcp_port(),
                    timeout_seconds=0.01,
                    max_packets=4,
                    max_bytes=1048576,
                    max_packet_bytes=4194304,
                    max_metadata_bytes=262144,
                    queue_capacity_packets=48,
                    capture_kind="live_broker_stream",
                    runtime_status=str(root / "runtime-status.json"),
                    topology_report=str(root / "missing-topology.json"),
                    firewall_report=str(root / "missing-firewall.json"),
                    serial="TESTQUESTSERIAL",
                    quest_lease_id="unit-test-quest-lease",
                    quest_lease_resource="quest:TESTQUESTSERIAL",
                    quest_lease_reserved_before_live_steps=True,
                    fail_on_error=True,
                )
            )
            receipt = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual(status, 2)
        self.assertFalse(capture_path.exists())
        self.assertFalse(sidecar_path.exists())
        self.assertFalse(receipt["accepted_connection"])
        self.assertEqual(receipt["close_reason"], "blocked_missing_product_media_dependencies")
        self.assertFalse(receipt["dependency_preflight"]["ready"])
        self.assertIn(
            "hostess.issue.connectivity_probe.media_live_session_topology_report_missing",
            receipt["issue_codes"],
        )
        self.assertIn(
            "hostess.issue.connectivity_probe.media_live_session_firewall_report_missing",
            receipt["issue_codes"],
        )

    def test_qcl082_product_media_live_session_arms_receiver_before_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request_path = root / "media-stream-start-source.request.json"
            bridge_path = root / "media-stream-start-source.bridge-evidence.json"
            execution_path = root / "media-stream-start-source.live-android-execution.json"
            validation_path = root / "media-stream-start-source.validation-report.json"
            logcat_path = root / "media-stream-start-source.logcat.txt"
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            result_path = root / "receiver-result.json"
            lifecycle_path = root / "qcl041-lifecycle.json"
            topology_path = root / "qcl041-live-wifi-direct-lifecycle.json"
            firewall_path = root / "qcl082-tcp-firewall-verify.json"
            lifecycle_path.write_text(
                json.dumps(wifi_direct_lifecycle_artifact(probe_id="QCL-041")),
                encoding="utf-8",
            )
            run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(topology_path),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            firewall_path.write_text(json.dumps(media_stream_firewall_report()), encoding="utf-8")
            port = free_tcp_port()

            def fake_live_android_runner(live_args: argparse.Namespace, **_: object) -> int:
                Path(live_args.out).write_text(
                    json.dumps({"schema": "fake.bridge", "status": "pass"}),
                    encoding="utf-8",
                )
                Path(live_args.execution_out).write_text(
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
                Path(live_args.validation_out).write_text(json.dumps({"status": "pass"}), encoding="utf-8")
                Path(live_args.logcat_out).write_text("fake logcat\n", encoding="utf-8")
                send_rmanvid1_loopback_payload(port, rmanvid1_capture_bytes())
                return 0

            status = run_qcl082_product_media_live_session(
                probe_args(
                    connectivity_probe_command="qcl082-product-media-live-session",
                    out=str(result_path),
                    start_source_request_out=str(request_path),
                    bridge_evidence_out=str(bridge_path),
                    execution_out=str(execution_path),
                    validation_out=str(validation_path),
                    logcat_out=str(logcat_path),
                    capture_out=str(capture_path),
                    sidecar_out=str(sidecar_path),
                    bind_host="127.0.0.1",
                    port=port,
                    timeout_seconds=2.0,
                    max_packets=4,
                    max_bytes=1048576,
                    capture_kind="live_broker_stream",
                    topology_report=str(topology_path),
                    firewall_report=str(firewall_path),
                    adb="S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                    serial="TESTQUESTSERIAL",
                    quest_lease_id="unit-test-quest-lease",
                    quest_lease_resource="quest:TESTQUESTSERIAL",
                    quest_lease_reserved_before_live_steps=True,
                    fail_on_error=True,
                ),
                live_android_runner=fake_live_android_runner,
            )
            receipt = json.loads(result_path.read_text(encoding="utf-8"))
            request = json.loads(request_path.read_text(encoding="utf-8"))
            report = fixture_report(
                probe_args(
                    probe_id="QCL-082",
                    media_stream_receiver_result=str(result_path),
                ),
                observed_at=fixed_datetime(),
            )

        self.assertEqual(status, 0)
        self.assertEqual(request["command"], "command.media_stream.start_source")
        self.assertEqual(receipt["status"], "pass")
        self.assertEqual(
            receipt["live_session"]["schema"],
            "rusty.hostess.media_stream.rmanvid1_live_session.v1",
        )
        self.assertTrue(receipt["live_session"]["receiver_armed_before_command"])
        self.assertEqual(receipt["live_session"]["live_command_returncode"], 0)
        self.assertTrue(receipt["live_session"]["quest_lease"]["valid"])
        self.assertEqual(receipt["capture_stats"]["packet_count"], 4)
        self.assertIn("--media-stream-receiver-result", receipt["follow_on_qcl082_args"])
        self.assertIn(str(result_path), receipt["follow_on_qcl082_args"])
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["media_stream_receiver_capture"]["product_topology"]["ready"])
        self.assertTrue(report["media_stream_receiver_capture"]["product_listener_firewall"]["ready"])
        self.assertTrue(report["media_stream_receiver_capture"]["quest_lease"]["valid"])

    def test_qcl082_product_media_live_session_blocks_when_topology_serial_mismatches_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request_path = root / "media-stream-start-source.request.json"
            bridge_path = root / "media-stream-start-source.bridge-evidence.json"
            execution_path = root / "media-stream-start-source.live-android-execution.json"
            validation_path = root / "media-stream-start-source.validation-report.json"
            logcat_path = root / "media-stream-start-source.logcat.txt"
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            result_path = root / "receiver-result.json"
            lifecycle_path = root / "qcl041-lifecycle.json"
            topology_path = root / "qcl041-live-wifi-direct-lifecycle.json"
            firewall_path = root / "qcl082-tcp-firewall-verify.json"
            lifecycle_artifact = wifi_direct_lifecycle_artifact(probe_id="QCL-041")
            lifecycle_artifact["device"]["serial"] = "OTHERQUESTSERIAL"
            lifecycle_artifact["lease"]["resource"] = "quest:OTHERQUESTSERIAL"
            lifecycle_path.write_text(json.dumps(lifecycle_artifact), encoding="utf-8")
            run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(topology_path),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            firewall_path.write_text(json.dumps(media_stream_firewall_report()), encoding="utf-8")
            runner_called = {"value": False}

            def fake_live_android_runner(*_: object, **__: object) -> int:
                runner_called["value"] = True
                return 0

            status = run_qcl082_product_media_live_session(
                probe_args(
                    connectivity_probe_command="qcl082-product-media-live-session",
                    out=str(result_path),
                    start_source_request_out=str(request_path),
                    bridge_evidence_out=str(bridge_path),
                    execution_out=str(execution_path),
                    validation_out=str(validation_path),
                    logcat_out=str(logcat_path),
                    capture_out=str(capture_path),
                    sidecar_out=str(sidecar_path),
                    bind_host="127.0.0.1",
                    port=free_tcp_port(),
                    timeout_seconds=0.01,
                    capture_kind="live_broker_stream",
                    topology_report=str(topology_path),
                    firewall_report=str(firewall_path),
                    adb="S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                    serial="TESTQUESTSERIAL",
                    quest_lease_id="unit-test-quest-lease",
                    quest_lease_resource="quest:TESTQUESTSERIAL",
                    quest_lease_reserved_before_live_steps=True,
                    fail_on_error=True,
                ),
                live_android_runner=fake_live_android_runner,
            )
            receipt = json.loads(result_path.read_text(encoding="utf-8"))

        topology = receipt["dependency_preflight"]["topology"]
        self.assertEqual(status, 2)
        self.assertFalse(runner_called["value"])
        self.assertFalse(request_path.exists())
        self.assertFalse(capture_path.exists())
        self.assertFalse(sidecar_path.exists())
        self.assertEqual(receipt["close_reason"], "blocked_missing_product_media_dependencies")
        self.assertFalse(receipt["live_session"]["receiver_armed_before_command"])
        self.assertTrue(receipt["live_session"]["quest_lease"]["valid"])
        self.assertFalse(receipt["live_session"]["dependency_preflight"]["ready"])
        self.assertEqual(topology["topology_device_serial"], "OTHERQUESTSERIAL")
        self.assertEqual(topology["media_receiver_quest_serial"], "TESTQUESTSERIAL")
        self.assertFalse(topology["topology_lease_serial_matches"])
        self.assertIn(
            "hostess.issue.connectivity_probe.media_direct_wifi_topology_lease_serial_mismatch",
            receipt["issue_codes"],
        )

    def test_qcl082_product_media_live_session_blocks_without_quest_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request_path = root / "media-stream-start-source.request.json"
            bridge_path = root / "media-stream-start-source.bridge-evidence.json"
            execution_path = root / "media-stream-start-source.live-android-execution.json"
            validation_path = root / "media-stream-start-source.validation-report.json"
            logcat_path = root / "media-stream-start-source.logcat.txt"
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "receiver-sidecar.json"
            result_path = root / "receiver-result.json"
            runner_called = {"value": False}

            def fake_live_android_runner(live_args: argparse.Namespace, **_: object) -> int:
                runner_called["value"] = True
                return 0

            status = run_qcl082_product_media_live_session(
                probe_args(
                    connectivity_probe_command="qcl082-product-media-live-session",
                    out=str(result_path),
                    start_source_request_out=str(request_path),
                    bridge_evidence_out=str(bridge_path),
                    execution_out=str(execution_path),
                    validation_out=str(validation_path),
                    logcat_out=str(logcat_path),
                    capture_out=str(capture_path),
                    sidecar_out=str(sidecar_path),
                    bind_host="127.0.0.1",
                    port=free_tcp_port(),
                    timeout_seconds=0.01,
                    capture_kind="live_broker_stream",
                    topology_report=str(root / "qcl041-live-wifi-direct-lifecycle.json"),
                    firewall_report=str(root / "qcl082-tcp-firewall-verify.json"),
                    adb="S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                    serial="TESTQUESTSERIAL",
                    fail_on_error=True,
                ),
                live_android_runner=fake_live_android_runner,
            )
            receipt = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual(status, 2)
        self.assertFalse(runner_called["value"])
        self.assertFalse(request_path.exists())
        self.assertFalse(receipt["accepted_connection"])
        self.assertEqual(receipt["close_reason"], "blocked_missing_quest_lease")
        self.assertFalse(receipt["live_session"]["receiver_armed_before_command"])
        self.assertFalse(receipt["live_session"]["quest_lease"]["valid"])
        self.assertIn(
            "hostess.issue.connectivity_probe.media_receiver_quest_lease_id_missing",
            receipt["issue_codes"],
        )

    def test_qcl082_product_media_live_session_blocks_without_product_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request_path = root / "media-stream-start-source.request.json"
            bridge_path = root / "media-stream-start-source.bridge-evidence.json"
            execution_path = root / "media-stream-start-source.live-android-execution.json"
            validation_path = root / "media-stream-start-source.validation-report.json"
            logcat_path = root / "media-stream-start-source.logcat.txt"
            capture_path = root / "media-stream.rmanvid1"
            sidecar_path = root / "media-stream-receiver-sidecar.json"
            result_path = root / "receiver-result.json"
            runner_called = {"value": False}

            def fake_live_android_runner(*_: object, **__: object) -> int:
                runner_called["value"] = True
                return 0

            status = run_qcl082_product_media_live_session(
                probe_args(
                    connectivity_probe_command="qcl082-product-media-live-session",
                    out=str(result_path),
                    start_source_request_out=str(request_path),
                    bridge_evidence_out=str(bridge_path),
                    execution_out=str(execution_path),
                    validation_out=str(validation_path),
                    logcat_out=str(logcat_path),
                    capture_out=str(capture_path),
                    sidecar_out=str(sidecar_path),
                    bind_host="127.0.0.1",
                    port=free_tcp_port(),
                    timeout_seconds=0.01,
                    capture_kind="live_broker_stream",
                    topology_report=str(root / "missing-topology.json"),
                    firewall_report=str(root / "missing-firewall.json"),
                    adb="S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                    serial="TESTQUESTSERIAL",
                    quest_lease_id="unit-test-quest-lease",
                    quest_lease_resource="quest:TESTQUESTSERIAL",
                    quest_lease_reserved_before_live_steps=True,
                    fail_on_error=True,
                ),
                live_android_runner=fake_live_android_runner,
            )
            receipt = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual(status, 2)
        self.assertFalse(runner_called["value"])
        self.assertFalse(request_path.exists())
        self.assertFalse(capture_path.exists())
        self.assertFalse(sidecar_path.exists())
        self.assertEqual(receipt["close_reason"], "blocked_missing_product_media_dependencies")
        self.assertFalse(receipt["live_session"]["receiver_armed_before_command"])
        self.assertTrue(receipt["live_session"]["quest_lease"]["valid"])
        self.assertFalse(receipt["live_session"]["dependency_preflight"]["ready"])
        self.assertIn(
            "hostess.issue.connectivity_probe.media_live_session_topology_report_missing",
            receipt["issue_codes"],
        )
        self.assertIn(
            "hostess.issue.connectivity_probe.media_live_session_firewall_report_missing",
            receipt["issue_codes"],
        )
