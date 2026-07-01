from __future__ import annotations

from tools.connectivity_probe_tests.helpers import *


class HostessCtlConnectivityProbeFacadeParserFirewallTests(unittest.TestCase):
    def test_run_connectivity_probe_writes_report_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "qcl010.json"
            status = run_connectivity_probe(
                probe_args(out=str(out), probe_id="QCL-010", fixture_profile="qcl-010-router-pass"),
                clock_func=fixed_datetime,
            )
            report = json.loads(out.read_text(encoding="utf-8"))
            validation = json.loads(out.with_name("qcl010.validation-report.json").read_text(encoding="utf-8"))

        self.assertEqual(status, 0)
        self.assertEqual(report["probe_id"], "QCL-010")
        self.assertEqual(validation["status"], "pass")

    def test_committed_fixture_reports_validate(self) -> None:
        fixture_paths = [
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-000-usb-adb-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-010-router-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-011-pc-hotspot-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-050-rfcomm-control-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-051-ble-gatt-status-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-080-udp-freshness-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-080-app-owned-udp-freshness-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-081-lsl-loopback-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-082-media-binary-plane-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-083-osc-loopback-pass.json",
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-084-zeromq-loopback-pass.json",
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-router-firewall-blocked.json",
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-pc-hotspot-off.json",
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-rfcomm-pairing-refused.json",
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-ble-permission-denied.json",
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-udp-firewall-blocked.json",
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-lsl-discovery-blocked.json",
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-media-high-rate-json-misuse.json",
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-osc-malformed-packet.json",
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-zeromq-dependency-missing.json",
        ]
        for fixture_path in fixture_paths:
            with self.subTest(fixture=fixture_path.name):
                report = json.loads(fixture_path.read_text(encoding="utf-8"))
                validation = validate_connectivity_probe_report(report)

                self.assertEqual(validation["status"], "pass")

    def test_parser_accepts_connectivity_probe_run(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "run",
                "--mode",
                "live",
                "--probe-id",
                "QCL-080",
                "--out",
                "target/qcl080.json",
                "--adb",
                "adb.exe",
                "--serial",
                "serial-1",
                "--host-ip",
                "192.0.2.10",
                "--topology-owner",
                "pc_hotspot",
                "--network-provider",
                "windows_mobile_hotspot",
                "--udp-port",
                "18767",
                "--udp-packet-count",
                "4",
                "--udp-sender-source",
                "makepad-runtime",
                "--lsl-source",
                "manifold-lsl-broker",
                "--lsl-manifold-root",
                "S:/Work/repos/active/rusty-manifold",
                "--lsl-sample-count",
                "8",
                "--lsl-quest-runtime-report",
                "target/qcl081-wifi-direct-lsl-receiver.json",
                "--osc-source",
                "host-loopback",
                "--osc-message-count",
                "6",
                "--zeromq-source",
                "host-loopback",
                "--zeromq-manifold-root",
                "S:/Work/repos/active/rusty-manifold",
                "--zeromq-message-count",
                "7",
                "--websocket-source",
                "broker-owned-websocket",
                "--websocket-route-descriptor",
                "S:/Work/repos/active/rusty-manifold/fixtures/bridge-route/stream-websocket-ordered-route.json",
                "--websocket-route-evidence",
                "S:/Work/repos/active/rusty-manifold/fixtures/bridge-route/stream-websocket-ordered-evidence.json",
                "--websocket-message-count",
                "9",
                "--websocket-payload-bytes",
                "128",
                "--bluetooth-payload-source",
                "android-ble-gatt",
                "--bluetooth-message-count",
                "5",
                "--bluetooth-timeout-seconds",
                "7",
                "--hostess-android-package",
                "io.example.hostess",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "run")
        self.assertEqual(args.mode, "live")
        self.assertEqual(args.probe_id, "QCL-080")
        self.assertEqual(args.host_ip, "192.0.2.10")
        self.assertEqual(args.topology_owner, "pc_hotspot")
        self.assertEqual(args.network_provider, "windows_mobile_hotspot")
        self.assertEqual(args.udp_port, 18767)
        self.assertEqual(args.udp_packet_count, 4)
        self.assertEqual(args.udp_sender_source, "makepad-runtime")
        self.assertEqual(args.udp_listener_helper, "")
        self.assertEqual(args.lsl_source, "manifold-lsl-broker")
        self.assertEqual(args.lsl_manifold_root, "S:/Work/repos/active/rusty-manifold")
        self.assertEqual(args.lsl_sample_count, 8)
        self.assertEqual(args.lsl_quest_runtime_report, "target/qcl081-wifi-direct-lsl-receiver.json")
        self.assertEqual(args.osc_source, "host-loopback")
        self.assertEqual(args.osc_message_count, 6)
        self.assertEqual(args.zeromq_source, "host-loopback")
        self.assertEqual(args.zeromq_manifold_root, "S:/Work/repos/active/rusty-manifold")
        self.assertEqual(args.zeromq_message_count, 7)
        self.assertEqual(args.websocket_source, "broker-owned-websocket")
        self.assertEqual(
            args.websocket_route_descriptor,
            "S:/Work/repos/active/rusty-manifold/fixtures/bridge-route/stream-websocket-ordered-route.json",
        )
        self.assertEqual(
            args.websocket_route_evidence,
            "S:/Work/repos/active/rusty-manifold/fixtures/bridge-route/stream-websocket-ordered-evidence.json",
        )
        self.assertEqual(args.websocket_message_count, 9)
        self.assertEqual(args.websocket_payload_bytes, 128)
        self.assertEqual(args.bluetooth_payload_source, "android-ble-gatt")
        self.assertEqual(args.bluetooth_message_count, 5)
        self.assertEqual(args.bluetooth_timeout_seconds, 7.0)
        self.assertEqual(args.hostess_android_package, "io.example.hostess")

    def test_parser_accepts_wifi_direct_lifecycle_report_input(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "run",
                "--mode",
                "fixture",
                "--probe-id",
                "QCL-041",
                "--wifi-direct-lifecycle-report",
                "target\\connectivity-probe\\qcl041-lifecycle.json",
                "--out",
                "target\\connectivity-probe\\qcl041-live-topology.json",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "run")
        self.assertEqual(args.probe_id, "QCL-041")
        self.assertEqual(
            args.wifi_direct_lifecycle_report,
            "target\\connectivity-probe\\qcl041-lifecycle.json",
        )

    def test_parser_accepts_wifi_direct_lifecycle_template_route(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "wifi-direct-lifecycle-template",
                "--probe-id",
                "QCL-040",
                "--out",
                "target\\connectivity-probe\\qcl040-wifi-direct-lifecycle-template.json",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "wifi-direct-lifecycle-template")
        self.assertEqual(args.probe_id, "QCL-040")
        self.assertEqual(
            args.out,
            "target\\connectivity-probe\\qcl040-wifi-direct-lifecycle-template.json",
        )

    def test_parser_accepts_wifi_direct_lifecycle_plan_route(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "wifi-direct-lifecycle-plan",
                "--probe-id",
                "QCL-041",
                "--out",
                "target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-plan.json",
                "--adb",
                "S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                "--serial",
                "<quest-serial>",
                "--lifecycle-report",
                "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle-source.json",
                "--fail-on-error",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "wifi-direct-lifecycle-plan")
        self.assertEqual(args.probe_id, "QCL-041")
        self.assertEqual(
            args.out,
            "target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-plan.json",
        )
        self.assertEqual(args.serial, "<quest-serial>")
        self.assertEqual(
            args.lifecycle_report,
            "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle-source.json",
        )
        self.assertTrue(args.fail_on_error)

    def test_parser_accepts_pc_hotspot_probe(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "run",
                "--mode",
                "fixture",
                "--probe-id",
                "QCL-011",
                "--fixture-profile",
                "qcl-011-pc-hotspot-pass",
                "--out",
                "target/qcl011.json",
            ]
        )

        self.assertEqual(args.probe_id, "QCL-011")
        self.assertEqual(args.fixture_profile, "qcl-011-pc-hotspot-pass")

    def test_parser_accepts_experimental_topology_probe(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "run",
                "--mode",
                "fixture",
                "--probe-id",
                "QCL-030",
                "--fixture-profile",
                "qcl-030-local-only-hotspot-started",
                "--out",
                "target/qcl030.json",
            ]
        )

        self.assertEqual(args.probe_id, "QCL-030")
        self.assertEqual(args.fixture_profile, "qcl-030-local-only-hotspot-started")

    def test_parser_accepts_qcl082_media_binary_probe(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "run",
                "--mode",
                "fixture",
                "--probe-id",
                "QCL-082",
                "--fixture-profile",
                "qcl-082-media-binary-plane-pass",
                "--media-stream-session-plan",
                "S:\\Work\\repos\\active\\rusty-quest\\fixtures\\media-stream-sessions\\display-composite-mediaprojection-h264.plan.json",
                "--media-stream-runtime-status",
                "target\\connectivity-probe\\media-stream-runtime-status.json",
                "--media-stream-rmanvid1-capture",
                "target\\connectivity-probe\\media-stream.rmanvid1",
                "--media-stream-receiver-sidecar",
                "target\\connectivity-probe\\media-stream-receiver-sidecar.json",
                "--media-stream-receiver-result",
                "target\\connectivity-probe\\media-stream-receiver-result.json",
                "--media-stream-topology-report",
                "target\\connectivity-probe\\qcl040-topology.json",
                "--media-stream-firewall-report",
                "target\\connectivity-probe\\qcl082-tcp-firewall-verify.json",
                "--out",
                "target/qcl082.json",
            ]
        )

        self.assertEqual(args.probe_id, "QCL-082")
        self.assertEqual(args.fixture_profile, "qcl-082-media-binary-plane-pass")
        self.assertEqual(
            args.media_stream_session_plan,
            "S:\\Work\\repos\\active\\rusty-quest\\fixtures\\media-stream-sessions\\display-composite-mediaprojection-h264.plan.json",
        )
        self.assertEqual(
            args.media_stream_runtime_status,
            "target\\connectivity-probe\\media-stream-runtime-status.json",
        )
        self.assertEqual(
            args.media_stream_rmanvid1_capture,
            "target\\connectivity-probe\\media-stream.rmanvid1",
        )
        self.assertEqual(
            args.media_stream_receiver_sidecar,
            "target\\connectivity-probe\\media-stream-receiver-sidecar.json",
        )
        self.assertEqual(
            args.media_stream_receiver_result,
            "target\\connectivity-probe\\media-stream-receiver-result.json",
        )
        self.assertEqual(
            args.media_stream_topology_report,
            "target\\connectivity-probe\\qcl040-topology.json",
        )
        self.assertEqual(
            args.media_stream_firewall_report,
            "target\\connectivity-probe\\qcl082-tcp-firewall-verify.json",
        )

    def test_parser_accepts_qcl079_websocket_probe(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "run",
                "--mode",
                "live",
                "--probe-id",
                "QCL-079",
                "--websocket-source",
                "host-loopback",
                "--websocket-bind-host",
                "127.0.0.1",
                "--websocket-port",
                "18785",
                "--websocket-path",
                "/qcl079",
                "--websocket-message-count",
                "4",
                "--websocket-payload-bytes",
                "64",
                "--websocket-timeout-seconds",
                "2.5",
                "--websocket-route-descriptor",
                "S:/Work/repos/active/rusty-manifold/fixtures/bridge-route/stream-websocket-ordered-route.json",
                "--websocket-route-evidence",
                "S:/Work/repos/active/rusty-manifold/fixtures/bridge-route/stream-websocket-ordered-evidence.json",
                "--out",
                "target/qcl079.json",
            ]
        )

        self.assertEqual(args.probe_id, "QCL-079")
        self.assertEqual(args.websocket_source, "host-loopback")
        self.assertEqual(args.websocket_bind_host, "127.0.0.1")
        self.assertEqual(args.websocket_port, 18785)
        self.assertEqual(args.websocket_path, "/qcl079")
        self.assertEqual(args.websocket_message_count, 4)
        self.assertEqual(args.websocket_payload_bytes, 64)
        self.assertEqual(args.websocket_timeout_seconds, 2.5)
        self.assertEqual(
            args.websocket_route_descriptor,
            "S:/Work/repos/active/rusty-manifold/fixtures/bridge-route/stream-websocket-ordered-route.json",
        )
        self.assertEqual(
            args.websocket_route_evidence,
            "S:/Work/repos/active/rusty-manifold/fixtures/bridge-route/stream-websocket-ordered-evidence.json",
        )

    def test_parser_accepts_rmanvid1_receiver_capture_command(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "rmanvid1-receiver-capture",
                "--bind-host",
                "0.0.0.0",
                "--port",
                "9079",
                "--capture-out",
                "target\\connectivity-probe\\media-stream.rmanvid1",
                "--sidecar-out",
                "target\\connectivity-probe\\media-stream-receiver-sidecar.json",
                "--runtime-status",
                "target\\connectivity-probe\\media-stream-runtime-status.json",
                "--topology-report",
                "target\\connectivity-probe\\qcl040-topology.json",
                "--firewall-report",
                "target\\connectivity-probe\\qcl082-tcp-firewall-verify.json",
                "--capture-kind",
                "live_broker_stream",
                "--quest-lease-id",
                "unit-test-quest-lease",
                "--quest-lease-resource",
                "quest:3487C10H3M017Q",
                "--quest-lease-reserved-before-live-steps",
                "--max-packets",
                "8",
                "--max-bytes",
                "1048576",
                "--out",
                "target\\connectivity-probe\\media-stream-receiver-result.json",
                "--fail-on-error",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "rmanvid1-receiver-capture")
        self.assertEqual(args.bind_host, "0.0.0.0")
        self.assertEqual(args.port, 9079)
        self.assertEqual(args.capture_kind, "live_broker_stream")
        self.assertEqual(args.quest_lease_id, "unit-test-quest-lease")
        self.assertEqual(args.quest_lease_resource, "quest:3487C10H3M017Q")
        self.assertTrue(args.quest_lease_reserved_before_live_steps)
        self.assertEqual(args.topology_report, "target\\connectivity-probe\\qcl040-topology.json")
        self.assertEqual(args.firewall_report, "target\\connectivity-probe\\qcl082-tcp-firewall-verify.json")
        self.assertEqual(args.max_packets, 8)
        self.assertEqual(args.max_bytes, 1048576)
        self.assertTrue(args.fail_on_error)

    def test_parser_accepts_qcl082_product_media_live_session_command(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "qcl082-product-media-live-session",
                "--out",
                "target\\connectivity-probe\\media-stream-receiver-result.json",
                "--bridge-command",
                "command.media_stream.start_source",
                "--start-source-request-out",
                "target\\connectivity-probe\\media-stream-start-source.request.json",
                "--bridge-evidence-out",
                "target\\connectivity-probe\\media-stream-start-source.bridge-evidence.json",
                "--execution-out",
                "target\\connectivity-probe\\media-stream-start-source.live-android-execution.json",
                "--validation-out",
                "target\\connectivity-probe\\media-stream-start-source.validation-report.json",
                "--logcat-out",
                "target\\connectivity-probe\\media-stream-start-source.logcat.txt",
                "--capture-out",
                "target\\connectivity-probe\\media-stream.rmanvid1",
                "--sidecar-out",
                "target\\connectivity-probe\\media-stream-receiver-sidecar.json",
                "--topology-report",
                "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
                "--firewall-report",
                "target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                "--adb",
                "S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                "--serial",
                "3487C10H3M017Q",
                "--port",
                "9079",
                "--capture-kind",
                "live_broker_stream",
                "--quest-lease-id",
                "unit-test-quest-lease",
                "--quest-lease-resource",
                "quest:3487C10H3M017Q",
                "--quest-lease-reserved-before-live-steps",
                "--fail-on-error",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "qcl082-product-media-live-session")
        self.assertEqual(args.bridge_command, "command.media_stream.start_source")
        self.assertEqual(args.port, 9079)
        self.assertEqual(args.capture_kind, "live_broker_stream")
        self.assertEqual(args.serial, "3487C10H3M017Q")
        self.assertEqual(args.quest_lease_id, "unit-test-quest-lease")
        self.assertEqual(args.quest_lease_resource, "quest:3487C10H3M017Q")
        self.assertTrue(args.quest_lease_reserved_before_live_steps)
        self.assertEqual(
            args.topology_report,
            "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
        )
        self.assertTrue(args.fail_on_error)

    def test_parser_accepts_qcl082_product_media_plan_command(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "qcl082-product-media-plan",
                "--out",
                "target\\connectivity-probe\\qcl082-product-media-direct-wifi-plan.json",
                "--promoted-topology-report",
                "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
                "--firewall-report",
                "target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                "--adb",
                "S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                "--serial",
                "3487C10H3M017Q",
                "--capture-kind",
                "live_broker_stream",
                "--quest-lease-id",
                "unit-test-quest-lease",
                "--quest-lease-resource",
                "quest:3487C10H3M017Q",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "qcl082-product-media-plan")
        self.assertEqual(
            args.out,
            "target\\connectivity-probe\\qcl082-product-media-direct-wifi-plan.json",
        )
        self.assertEqual(
            args.promoted_topology_report,
            "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
        )
        self.assertEqual(
            args.firewall_report,
            "target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
        )
        self.assertEqual(args.serial, "3487C10H3M017Q")
        self.assertEqual(args.capture_kind, "live_broker_stream")
        self.assertEqual(args.quest_lease_id, "unit-test-quest-lease")
        self.assertEqual(args.quest_lease_resource, "quest:3487C10H3M017Q")

    def test_parser_accepts_direct_wifi_product_media_plan_command(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "direct-wifi-product-media-plan",
                "--out",
                "target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json",
                "--qcl040-preflight-report",
                "target\\connectivity-probe\\qcl040-live-wifi-direct-preflight.json",
                "--qcl041-preflight-report",
                "target\\connectivity-probe\\qcl041-live-wifi-direct-preflight.json",
                "--qcl040-topology-report",
                "target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json",
                "--qcl041-topology-report",
                "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
                "--promoted-topology-report",
                "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
                "--firewall-report",
                "target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                "--qcl082-report",
                "target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
                "--protocol-matrix-out",
                "target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.protocol-matrix.json",
                "--projection-out",
                "target\\companion-report\\wpf-live-projection.json",
                "--transport-gates-out",
                "target\\companion-report\\wpf-live-transport-gates.json",
                "--adb",
                "S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe",
                "--serial",
                "3487C10H3M017Q",
                "--capture-kind",
                "live_broker_stream",
                "--quest-lease-id",
                "unit-test-quest-lease",
                "--quest-lease-resource",
                "quest:3487C10H3M017Q",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "direct-wifi-product-media-plan")
        self.assertEqual(
            args.out,
            "target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json",
        )
        self.assertEqual(
            args.qcl040_preflight_report,
            "target\\connectivity-probe\\qcl040-live-wifi-direct-preflight.json",
        )
        self.assertEqual(
            args.qcl041_preflight_report,
            "target\\connectivity-probe\\qcl041-live-wifi-direct-preflight.json",
        )
        self.assertEqual(
            args.qcl041_topology_report,
            "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
        )
        self.assertEqual(
            args.qcl082_report,
            "target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
        )
        self.assertEqual(args.serial, "3487C10H3M017Q")
        self.assertEqual(args.capture_kind, "live_broker_stream")
        self.assertEqual(args.quest_lease_id, "unit-test-quest-lease")
        self.assertEqual(args.quest_lease_resource, "quest:3487C10H3M017Q")

    def test_parser_accepts_bluetooth_probe(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "run",
                "--mode",
                "fixture",
                "--probe-id",
                "QCL-051",
                "--fixture-profile",
                "qcl-051-ble-gatt-status-pass",
                "--bluetooth-reconnect-count",
                "1",
                "--out",
                "target/qcl051.json",
            ]
        )

        self.assertEqual(args.probe_id, "QCL-051")
        self.assertEqual(args.fixture_profile, "qcl-051-ble-gatt-status-pass")
        self.assertEqual(args.bluetooth_reconnect_count, 1)

    def test_parser_accepts_wpf_udp_listener_helper(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "run",
                "--mode",
                "live",
                "--probe-id",
                "QCL-080",
                "--out",
                "target/qcl080.json",
                "--adb",
                "adb.exe",
                "--serial",
                "serial-1",
                "--udp-listener-helper",
                "apps/hostess-companion-wpf/bin/Debug/net9.0-windows/HostessCompanion.Wpf.exe",
                "--udp-sender-source",
                "makepad-runtime",
            ]
        )

        self.assertEqual(
            args.udp_listener_helper,
            "apps/hostess-companion-wpf/bin/Debug/net9.0-windows/HostessCompanion.Wpf.exe",
        )
        self.assertEqual(args.udp_sender_source, "makepad-runtime")

    def test_udp_listener_firewall_uses_observed_listener_program(self) -> None:
        listener = udp_listener_from_result(
            probe_args(udp_bind_host="0.0.0.0"),
            {
                "observed": {
                    "port": 18767,
                    "listener_program": "C:\\Tools\\HostessCompanion.Wpf.exe",
                }
            },
        )

        self.assertEqual(listener["program"], "C:\\Tools\\HostessCompanion.Wpf.exe")
        self.assertEqual(listener["protocol"], "UDP")
        self.assertEqual(listener["port"], 18767)

    def test_parser_accepts_windows_firewall_rule_plan(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "windows-firewall-rule",
                "--program",
                "C:\\Tools\\HostessCompanion.exe",
                "--protocol",
                "UDP",
                "--port",
                "18767",
                "--profile",
                "Public",
                "--remote-address",
                "LocalSubnet",
                "--action",
                "verify",
                "--out",
                "target/firewall.json",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "windows-firewall-rule")
        self.assertEqual(args.protocol, "UDP")
        self.assertEqual(args.port, 18767)
        self.assertEqual(args.remote_address, "LocalSubnet")
        self.assertEqual(args.action, "verify")

    def test_parser_accepts_qcl082_windows_firewall_rule_profile(self) -> None:
        args = build_hostessctl_parser(
            broker_package="broker",
            broker_port=8765,
            broker_local_forward_port=18765,
            makepad_android_package="makepad",
            makepad_android_xr_activity="makepad/.Xr",
            makepad_provider_package="makepad",
            makepad_provider_activity="makepad/.Xr",
        ).parse_args(
            [
                "connectivity-probe",
                "windows-firewall-rule",
                "--rule-profile",
                "qcl-082-rmanvid1-media",
                "--action",
                "verify",
                "--handoff-script-out",
                "target/qcl082-firewall-admin.ps1",
                "--handoff-verify-out",
                "target/qcl082-firewall-verify.json",
                "--out",
                "target/qcl082-firewall.json",
            ]
        )

        self.assertEqual(args.connectivity_probe_command, "windows-firewall-rule")
        self.assertEqual(args.rule_profile, "qcl-082-rmanvid1-media")
        self.assertIsNone(args.protocol)
        self.assertIsNone(args.port)
        self.assertEqual(args.handoff_script_out, "target/qcl082-firewall-admin.ps1")
        self.assertEqual(args.handoff_verify_out, "target/qcl082-firewall-verify.json")

    def test_windows_firewall_rule_plan_scopes_program_port_profile_and_subnet(self) -> None:
        report = windows_firewall_rule_report(
            probe_args(
                connectivity_probe_command="windows-firewall-rule",
                program="C:\\Tools\\HostessCompanion.exe",
                protocol="UDP",
                port=18767,
                profile="Public",
                remote_address="LocalSubnet",
                rule_name="Rusty Hostess WPF QCL-080 UDP Freshness 18767",
                action="plan",
                apply=False,
            ),
            observed_at=fixed_datetime(),
        )

        self.assertEqual(report["schema"], CONNECTIVITY_FIREWALL_RULE_SCHEMA)
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["rule"]["program"], "C:\\Tools\\HostessCompanion.exe")
        self.assertEqual(report["rule"]["protocol"], "UDP")
        self.assertEqual(report["rule"]["local_port"], 18767)
        self.assertEqual(report["rule"]["profiles"], ["Public"])
        self.assertEqual(report["rule"]["remote_address"], "LocalSubnet")
        self.assertEqual(report["probe_usage"]["probe_id"], "QCL-080")
        self.assertIn("selected protocol/port", report["rule"]["scope_note"])
        self.assertIn("--udp-port", report["probe_usage"]["connectivity_probe_args"])
        self.assertIn("--udp-listener-helper", report["probe_usage"]["connectivity_probe_args"])
        self.assertIn(
            "C:\\Tools\\HostessCompanion.exe",
            report["probe_usage"]["connectivity_probe_args"],
        )
        self.assertIn("makepad-runtime", report["probe_usage"]["connectivity_probe_args"])
        self.assertIn("New-NetFirewallRule", report["powershell"]["script"])
        self.assertIn("-Protocol $protocol", report["powershell"]["script"])
        self.assertFalse(report["powershell"]["requires_admin"])

    def test_windows_firewall_rule_defaults_to_wpf_product_listener(self) -> None:
        report = windows_firewall_rule_report(
            probe_args(
                connectivity_probe_command="windows-firewall-rule",
                protocol="UDP",
                port=18767,
                profile="Public",
                remote_address="LocalSubnet",
                rule_name="",
                action="verify",
                apply=False,
            ),
            observed_at=fixed_datetime(),
        )

        self.assertEqual(report["action"], "verify")
        self.assertEqual(report["rule"]["name"], "Rusty Hostess WPF QCL-080 UDP Freshness 18767")
        self.assertTrue(report["rule"]["program"].endswith("HostessCompanion.Wpf.exe"))
        self.assertIn("Get-NetFirewallRule", report["powershell"]["script"])
        self.assertNotIn("New-NetFirewallRule", report["powershell"]["script"])
        self.assertFalse(report["powershell"]["requires_admin"])

    def test_windows_firewall_rule_apply_blocks_before_mutation_when_not_elevated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "qcl082-apply.json"
            commands: list[list[str]] = []

            def fake_run(
                command: list[str],
                *,
                allow_failure: bool = False,
                cwd: Path | None = None,
            ) -> subprocess.CompletedProcess[str]:
                commands.append(command)
                text = " ".join(command)
                if "Get-NetConnectionProfile" in text:
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        firewall_profile_json(protocol="TCP", listener_port=9079),
                        "",
                    )
                return subprocess.CompletedProcess(command, 0, "{}", "")

            status = run_windows_firewall_rule(
                probe_args(
                    connectivity_probe_command="windows-firewall-rule",
                    rule_profile="qcl-082-rmanvid1-media",
                    action="apply",
                    out=str(out),
                    fail_on_error=True,
                ),
                run_captured_func=fake_run,
                clock_func=fixed_datetime,
                elevation_func=lambda: {
                    "current_process_is_elevated": False,
                    "user": "fixture",
                    "source": "unit",
                },
            )
            report = json.loads(out.read_text(encoding="utf-8"))

        joined_commands = [" ".join(command) for command in commands]
        self.assertEqual(status, 2)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["powershell"]["requires_admin"])
        self.assertTrue(report["elevation"]["blocked_before_mutation"])
        self.assertFalse(report["action_result"]["attempted"])
        self.assertIn("requires an elevated PowerShell", report["action_result"]["stderr"])
        self.assertIn(
            "hostess.issue.connectivity_probe.firewall_rule_requires_elevation",
            [issue["issue_code"] for issue in report["issues"]],
        )
        self.assertIn("verification", report)
        self.assertFalse(any("New-NetFirewallRule" in command for command in joined_commands))
        self.assertTrue(any("Get-NetConnectionProfile" in command for command in joined_commands))

    def test_windows_firewall_rule_apply_writes_elevated_handoff_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "qcl082-apply.json"
            script_out = root / "qcl082-admin-apply.ps1"
            verify_out = root / "qcl082-verify.json"
            commands: list[list[str]] = []

            def fake_run(
                command: list[str],
                *,
                allow_failure: bool = False,
                cwd: Path | None = None,
            ) -> subprocess.CompletedProcess[str]:
                commands.append(command)
                text = " ".join(command)
                if "Get-NetConnectionProfile" in text:
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        firewall_profile_json(protocol="TCP", listener_port=9079),
                        "",
                    )
                return subprocess.CompletedProcess(command, 0, "{}", "")

            status = run_windows_firewall_rule(
                probe_args(
                    connectivity_probe_command="windows-firewall-rule",
                    rule_profile="qcl-082-rmanvid1-media",
                    action="apply",
                    out=str(out),
                    handoff_script_out=str(script_out),
                    handoff_verify_out=str(verify_out),
                    fail_on_error=True,
                ),
                run_captured_func=fake_run,
                clock_func=fixed_datetime,
                elevation_func=lambda: {
                    "current_process_is_elevated": False,
                    "user": "fixture",
                    "source": "unit",
                },
            )
            report = json.loads(out.read_text(encoding="utf-8"))
            script = script_out.read_text(encoding="utf-8")

        self.assertEqual(status, 2)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["action_result"]["attempted"])
        self.assertEqual(report["admin_handoff"]["handoff_action"], "apply")
        self.assertEqual(report["admin_handoff"]["script_out"], str(script_out))
        self.assertEqual(report["admin_handoff"]["verify_report_out"], str(verify_out))
        self.assertEqual(report["elevation"]["handoff"]["script_out"], str(script_out))
        self.assertEqual(len(report["admin_handoff"]["script_sha256"]), 64)
        self.assertIn("#Requires -RunAsAdministrator", script)
        self.assertIn("Set-Location -LiteralPath", script)
        self.assertIn("tools/hostessctl/hostessctl.py", script)
        self.assertIn("--action' 'apply", script)
        self.assertIn("--action' 'verify", script)
        self.assertIn("--rule-profile' 'qcl-082-rmanvid1-media", script)
        self.assertIn(str(verify_out).replace("\\", "/").replace("'", "''"), script)
        self.assertNotIn("New-NetFirewallRule", script)
        self.assertTrue(any("Get-NetConnectionProfile" in " ".join(command) for command in commands))

    def test_windows_firewall_rule_tcp_default_uses_wpf_product_name(self) -> None:
        report = windows_firewall_rule_report(
            probe_args(
                connectivity_probe_command="windows-firewall-rule",
                protocol="TCP",
                port=18766,
                profile="Private",
                remote_address="LocalSubnet",
                rule_name="",
                action="plan",
                apply=False,
            ),
            observed_at=fixed_datetime(),
        )

        self.assertEqual(report["rule"]["name"], "Rusty Hostess WPF QCL-010 TCP Echo 18766")
        self.assertEqual(report["probe_usage"]["probe_id"], "QCL-010")
        self.assertIn("--tcp-echo-port", report["probe_usage"]["connectivity_probe_args"])
        self.assertNotIn("--udp-listener-helper", report["probe_usage"]["connectivity_probe_args"])

    def test_windows_firewall_rule_qcl082_profile_uses_media_listener_contract(self) -> None:
        report = windows_firewall_rule_report(
            probe_args(
                connectivity_probe_command="windows-firewall-rule",
                program="C:\\Tools\\HostessCompanion.Wpf.exe",
                rule_profile="qcl-082-rmanvid1-media",
                protocol=None,
                port=None,
                profile="Public",
                remote_address="LocalSubnet",
                rule_name="",
                action="verify",
                out="target\\connectivity-probe\\qcl082-tcp-firewall-verify.json",
                apply=False,
            ),
            observed_at=fixed_datetime(),
        )

        self.assertEqual(report["rule_profile"], "qcl-082-rmanvid1-media")
        self.assertEqual(report["rule"]["name"], "Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079")
        self.assertEqual(report["rule"]["protocol"], "TCP")
        self.assertEqual(report["rule"]["local_port"], 9079)
        self.assertEqual(report["probe_usage"]["probe_id"], "QCL-082")
        self.assertIn("--media-stream-firewall-report", report["probe_usage"]["connectivity_probe_args"])
        self.assertIn(
            "target\\connectivity-probe\\qcl082-tcp-firewall-verify.json",
            report["probe_usage"]["connectivity_probe_args"],
        )
        self.assertNotIn("--tcp-echo-port", report["probe_usage"]["connectivity_probe_args"])

    def test_windows_firewall_rule_qcl082_profile_allows_explicit_port_override(self) -> None:
        report = windows_firewall_rule_report(
            probe_args(
                connectivity_probe_command="windows-firewall-rule",
                program="C:\\Tools\\HostessCompanion.Wpf.exe",
                rule_profile="qcl-082-rmanvid1-media",
                protocol=None,
                port=19082,
                profile="Public",
                remote_address="LocalSubnet",
                rule_name="",
                action="plan",
                apply=False,
            ),
            observed_at=fixed_datetime(),
        )

        self.assertEqual(report["rule"]["name"], "Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 19082")
        self.assertEqual(report["rule"]["local_port"], 19082)
        self.assertEqual(report["probe_usage"]["probe_id"], "QCL-082")
