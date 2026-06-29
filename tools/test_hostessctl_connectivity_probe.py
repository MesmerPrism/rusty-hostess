from __future__ import annotations

import argparse
import json
import socket
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.connectivity_probe import (
    CONNECTIVITY_FIREWALL_RULE_SCHEMA,
    CONNECTIVITY_PROBE_SCHEMA,
    DEFAULT_QCL080_UDP_PORT,
    device_to_host_tcp_echo,
    device_to_host_udp_freshness,
    fixture_report,
    latest_qcl080_app_marker,
    live_bluetooth_report,
    live_lsl_report,
    live_osc_report,
    live_same_wifi_report,
    live_udp_freshness_report,
    live_zeromq_report,
    qcl080_makepad_runtime_properties,
    run_connectivity_probe,
    strip_powershell_clixml_noise,
    udp_listener_from_result,
    validate_connectivity_probe_report,
    windows_firewall_rule_report,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class HostessCtlConnectivityProbeTests(unittest.TestCase):
    def test_qcl000_fixture_validates_command_feedback_baseline(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-000", fixture_profile="qcl-000-usb-adb-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["schema"], CONNECTIVITY_PROBE_SCHEMA)
        self.assertEqual(report["probe_id"], "QCL-000")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["command_stages"]["applied"], "pass")
        self.assertEqual(validation["status"], "pass")

    def test_qcl010_fixture_validates_same_wifi_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-010", fixture_profile="qcl-010-router-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-010")
        self.assertEqual(report["topology"]["owner"], "external_wifi")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "host.windows_network_firewall_profile")["status"], "pass")
        self.assertEqual(check(report, "host.windows_firewall_listener")["status"], "pass")
        self.assertEqual(validation["status"], "pass")
        self.assertIn("WebSocket echo", " ".join(validation["warnings"]))

    def test_qcl010_damaged_fixture_reports_public_profile_and_listener_rule_gap(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-010", fixture_profile="qcl-010-router-firewall-blocked"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "host.windows_network_firewall_profile")["status"], "warn")
        self.assertEqual(check(report, "host.windows_firewall_listener")["status"], "fail")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.windows_network_profile_public"
                for issue in report["issues"]
            )
        )
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.no_tcp_listener_firewall_allow_rule"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl011_fixture_validates_pc_hotspot_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-011", fixture_profile="qcl-011-pc-hotspot-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-011")
        self.assertEqual(report["topology"]["owner"], "pc_hotspot")
        self.assertEqual(report["topology"]["network_provider"], "windows_mobile_hotspot")
        self.assertEqual(check(report, "host.windows_mobile_hotspot")["status"], "pass")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(validation["status"], "pass")

    def test_qcl011_damaged_fixture_reports_hotspot_off(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-011", fixture_profile="qcl-011-pc-hotspot-off"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "host.windows_mobile_hotspot")["status"], "blocked")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.pc_hotspot_off"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_windows_hotspot_collector_strips_trailing_clixml_noise(self) -> None:
        clean = strip_powershell_clixml_noise('{"state":"On"}\n#< CLIXML\n<Objs Version="1.1.0.1"></Objs>')

        self.assertEqual(clean, '{"state":"On"}')

    def test_qcl050_fixture_validates_rfcomm_control_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-050", fixture_profile="qcl-050-rfcomm-control-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-050")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["family"], "bluetooth_rfcomm")
        self.assertEqual(check(report, "protocol.rfcomm_control")["status"], "pass")
        self.assertEqual(check(report, "protocol.bluetooth_payload_exchange")["status"], "pass")
        self.assertEqual(validation["status"], "pass")

    def test_qcl050_damaged_fixture_reports_pairing_refused(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-050", fixture_profile="qcl-050-rfcomm-pairing-refused"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "bluetooth.pairing_bond_state")["status"], "blocked")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.bluetooth_pairing_refused"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl051_fixture_validates_ble_gatt_status_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-051", fixture_profile="qcl-051-ble-gatt-status-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-051")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["family"], "ble_gatt")
        self.assertEqual(check(report, "protocol.ble_gatt_status")["status"], "pass")
        self.assertEqual(check(report, "protocol.bluetooth_payload_exchange")["status"], "pass")
        self.assertEqual(validation["status"], "pass")

    def test_qcl051_damaged_fixture_reports_permission_denied(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-051", fixture_profile="qcl-051-ble-permission-denied"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "bluetooth.permission_state")["status"], "blocked")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.bluetooth_permission_denied"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl080_fixture_validates_udp_freshness_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-080", fixture_profile="qcl-080-udp-freshness-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-080")
        self.assertEqual(report["transport"]["family"], "udp")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "protocol.udp_freshness")["status"], "pass")
        self.assertEqual(report["measurements"]["udp_packets_sent"], 12)
        self.assertEqual(report["measurements"]["udp_packets_received"], 12)
        self.assertEqual(report["measurements"]["udp_loss_percent"], 0.0)
        self.assertEqual(validation["status"], "pass")

    def test_qcl080_app_owned_fixture_requires_runtime_sender_marker(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-080", fixture_profile="qcl-080-app-owned-udp-freshness-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["endpoint_source"], "app_owned_runtime_udp_sender")
        self.assertEqual(check(report, "protocol.udp_freshness")["status"], "pass")
        self.assertEqual(check(report, "runtime.qcl080_udp_sender")["status"], "pass")
        self.assertEqual(validation["status"], "pass")

    def test_qcl080_damaged_fixture_reports_udp_firewall_gap(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-080", fixture_profile="qcl-080-udp-firewall-blocked"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "protocol.udp_freshness")["status"], "fail")
        self.assertEqual(check(report, "host.windows_firewall_listener")["status"], "fail")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.no_udp_listener_firewall_allow_rule"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl081_fixture_validates_lsl_loopback_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-081", fixture_profile="qcl-081-lsl-loopback-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-081")
        self.assertEqual(report["transport"]["family"], "lsl")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "protocol.lsl_discovery")["status"], "pass")
        self.assertEqual(check(report, "protocol.lsl_sample_continuity")["status"], "pass")
        self.assertEqual(report["measurements"]["lsl_samples_received"], 16)
        self.assertEqual(validation["status"], "pass")

    def test_qcl081_damaged_fixture_reports_discovery_blocked(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-081", fixture_profile="qcl-081-lsl-discovery-blocked"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "protocol.lsl_discovery")["status"], "fail")
        self.assertEqual(check(report, "protocol.lsl_sample_continuity")["status"], "blocked")
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_fixture_validates_media_binary_plane_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-082", fixture_profile="qcl-082-media-binary-plane-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-082")
        self.assertEqual(report["transport"]["family"], "tcp_binary")
        self.assertEqual(report["transport"]["packet_magic"], "RMANVID1")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "protocol.media_binary_transport")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_backpressure_policy")["status"], "pass")
        self.assertEqual(check(report, "protocol.media_high_rate_json_guard")["status"], "pass")
        self.assertEqual(report["measurements"]["media_frames_received"], 24)
        self.assertEqual(validation["status"], "pass")

    def test_qcl082_damaged_fixture_rejects_high_rate_json_media(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-082", fixture_profile="qcl-082-media-high-rate-json-misuse"),
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

    def test_live_same_wifi_report_uses_adb_for_observation_and_tcp_for_data_path(self) -> None:
        report = live_same_wifi_report(
            probe_args(mode="live", host_ip="192.0.2.10"),
            run_captured_func=FakeRunner(),
            run_timeout_func=FakeTimeoutRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            tcp_echo_func=fake_tcp_echo_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-010")
        self.assertTrue(str(report["run_id"]).endswith("-qcl-010"))
        self.assertEqual(report["status"], "warn")
        self.assertEqual(report["device"]["wifi_ipv4"], "192.0.2.42")
        self.assertEqual(report["host"]["selected_ipv4"], "192.0.2.10")
        self.assertEqual(check(report, "topology.same_subnet")["status"], "pass")
        self.assertEqual(check(report, "device_to_host.tcp_echo")["status"], "pass")
        self.assertEqual(check(report, "host.windows_firewall_listener")["status"], "pass")
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.partial_protocol_coverage"
                for issue in report["issues"]
            )
        )

    def test_live_pc_hotspot_report_requires_hotspot_state_and_data_path(self) -> None:
        report = live_same_wifi_report(
            probe_args(mode="live", probe_id="QCL-011", host_ip="192.0.2.10"),
            run_captured_func=FakeRunner(),
            run_timeout_func=FakeTimeoutRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "Local Area Connection* 12"}],
            tcp_echo_func=fake_tcp_echo_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-011")
        self.assertTrue(str(report["run_id"]).endswith("-qcl-011"))
        self.assertEqual(report["topology"]["owner"], "pc_hotspot")
        self.assertEqual(report["transport"]["route"], "pc_hotspot_lan_probe")
        self.assertEqual(check(report, "host.windows_mobile_hotspot")["status"], "pass")
        self.assertEqual(check(report, "device_to_host.tcp_echo")["status"], "pass")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(validation["status"], "pass")

    def test_live_same_wifi_report_does_not_pass_on_one_way_host_ping(self) -> None:
        report = live_same_wifi_report(
            probe_args(mode="live", host_ip="192.0.2.10"),
            run_captured_func=FakeRunner(),
            run_timeout_func=OneWayPingTimeoutRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            tcp_echo_func=fake_tcp_echo_fail,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(check(report, "host_to_device.icmp_ping")["status"], "pass")
        self.assertEqual(check(report, "device_to_host.icmp_ping")["status"], "fail")
        self.assertEqual(check(report, "device_to_host.tcp_echo")["status"], "fail")
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.same_wifi_reachability_not_proven"
                for issue in report["issues"]
            )
        )

    def test_live_udp_freshness_report_uses_same_wifi_context_and_udp_metrics(self) -> None:
        report = live_udp_freshness_report(
            probe_args(mode="live", probe_id="QCL-080", host_ip="192.0.2.10"),
            run_captured_func=FakeRunner(protocol="UDP", listener_port=DEFAULT_QCL080_UDP_PORT),
            run_timeout_func=FakeTimeoutRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            udp_freshness_func=fake_udp_freshness_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-080")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["endpoint_source"], "adb_shell_udp_generator")
        self.assertEqual(check(report, "protocol.udp_freshness")["status"], "pass")
        self.assertEqual(check(report, "host.windows_firewall_listener")["status"], "pass")
        self.assertEqual(report["measurements"]["udp_packets_received"], 12)
        self.assertEqual(validation["status"], "pass")

    def test_live_udp_freshness_report_can_label_pc_hotspot_topology(self) -> None:
        report = live_udp_freshness_report(
            probe_args(
                mode="live",
                probe_id="QCL-080",
                host_ip="192.0.2.10",
                topology_owner="pc_hotspot",
                network_provider="windows_mobile_hotspot",
            ),
            run_captured_func=FakeRunner(protocol="UDP", listener_port=DEFAULT_QCL080_UDP_PORT),
            run_timeout_func=FakeTimeoutRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            udp_freshness_func=fake_udp_freshness_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["topology"]["owner"], "pc_hotspot")
        self.assertEqual(report["topology"]["network_provider"], "windows_mobile_hotspot")
        self.assertFalse(report["topology"]["requires_existing_wifi"])
        self.assertEqual(validation["status"], "pass")

    def test_live_udp_freshness_report_promotes_app_owned_runtime_sender(self) -> None:
        report = live_udp_freshness_report(
            probe_args(mode="live", probe_id="QCL-080", host_ip="192.0.2.10", run_id="qcl080-app"),
            run_captured_func=FakeRunner(protocol="UDP", listener_port=DEFAULT_QCL080_UDP_PORT),
            run_timeout_func=FakeTimeoutRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            udp_freshness_func=fake_udp_freshness_app_owned_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["endpoint_source"], "app_owned_runtime_udp_sender")
        self.assertEqual(check(report, "runtime.qcl080_udp_sender")["status"], "pass")
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_device_to_host_tcp_echo_uses_single_adb_shell_pipeline(self) -> None:
        runner = TcpEchoCommandRunner()
        result = device_to_host_tcp_echo(
            probe_args(
                tcp_echo_bind_host="127.0.0.1",
                tcp_echo_port=0,
                tcp_timeout_seconds=1.0,
            ),
            "127.0.0.1",
            runner,
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(runner.command[3], "shell")
        self.assertNotIn("sh -c", " ".join(runner.command))
        self.assertIn("printf %s rusty-qcl-tcp-echo", runner.command[-1])

    def test_device_to_host_udp_freshness_uses_sequenced_adb_shell_datagrams(self) -> None:
        runner = UdpFreshnessCommandRunner()
        result = device_to_host_udp_freshness(
            probe_args(
                udp_bind_host="127.0.0.1",
                udp_port=0,
                udp_packet_count=4,
                udp_interval_ms=1.0,
                udp_timeout_seconds=1.0,
                udp_max_loss_percent=0.0,
            ),
            "127.0.0.1",
            runner,
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(runner.command[3], "shell")
        self.assertIn("toybox nc -u", runner.command[-1])
        self.assertEqual(result["observed"]["packets_received"], 4)
        self.assertEqual(result["observed"]["loss_percent"], 0.0)

    def test_device_to_host_udp_freshness_can_use_makepad_runtime_sender(self) -> None:
        runner = MakepadRuntimeUdpCommandRunner()
        result = device_to_host_udp_freshness(
            probe_args(
                run_id="qcl080-runtime-test",
                udp_sender_source="makepad-runtime",
                udp_bind_host="127.0.0.1",
                udp_port=0,
                udp_packet_count=4,
                udp_interval_ms=1.0,
                udp_timeout_seconds=1.0,
                udp_max_loss_percent=0.0,
            ),
            "127.0.0.1",
            runner,
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["observed"]["generator"], "app_owned_runtime_udp_sender")
        self.assertEqual(result["observed"]["packets_received"], 4)
        self.assertTrue(result["observed"]["runtime_marker"]["matched"])
        self.assertEqual(
            result["observed"]["runtime_properties"]["debug.rustyquest.makepad.qcl080.udp.host"],
            "127.0.0.1",
        )
        self.assertIn("am start", " ".join(" ".join(command) for command in runner.commands))

    def test_qcl080_makepad_runtime_properties_match_makepad_runtime_keys(self) -> None:
        properties = qcl080_makepad_runtime_properties(
            host_ip="192.0.2.10",
            port=18767,
            marker="rusty-qcl-udp",
            packet_count=24,
            interval_ms=20.0,
            run_id="run-1",
        )

        self.assertEqual(properties["debug.rustyquest.makepad.qcl080.udp.enabled"], "true")
        self.assertEqual(properties["debug.rustyquest.makepad.qcl080.udp.packet.count"], "24")
        self.assertEqual(properties["debug.rustyquest.makepad.qcl080.udp.interval.ms"], "20")
        self.assertEqual(properties["debug.rustyquest.makepad.qcl080.udp.run.id"], "run-1")

    def test_qcl080_app_marker_parser_filters_stale_run_ids(self) -> None:
        text = "\n".join(
            [
                "06-28 HostessMakepad: RUSTY_HOSTESS_MAKEPAD_QCL080_UDP_SENDER schema=rusty.hostess.makepad.qcl080_udp_sender.v1 status=sent marker=rusty-qcl-udp runId=old packetsRequested=4 packetsSent=4 senderSource=makepad-runtime socketOwner=app-owned",
                "06-28 HostessMakepad: RUSTY_HOSTESS_MAKEPAD_QCL080_UDP_SENDER schema=rusty.hostess.makepad.qcl080_udp_sender.v1 status=sent marker=rusty-qcl-udp runId=current packetsRequested=4 packetsSent=4 senderSource=makepad-runtime socketOwner=app-owned",
            ]
        )

        parsed = latest_qcl080_app_marker(text, marker="rusty-qcl-udp", run_id="current")

        self.assertTrue(parsed["matched"])
        self.assertEqual(parsed["fields"]["runId"], "current")

    def test_connectivity_probe_keeps_protocol_helpers_split(self) -> None:
        probe_source = (REPO_ROOT / "tools" / "hostessctl" / "connectivity_probe.py").read_text(
            encoding="utf-8"
        )
        bluetooth_source = (
            REPO_ROOT / "tools" / "hostessctl" / "connectivity_bluetooth.py"
        ).read_text(encoding="utf-8")
        protocol_source = (
            REPO_ROOT / "tools" / "hostessctl" / "connectivity_data_protocols.py"
        ).read_text(encoding="utf-8")
        common_source = (
            REPO_ROOT / "tools" / "hostessctl" / "connectivity_probe_common.py"
        ).read_text(encoding="utf-8")
        udp_source = (REPO_ROOT / "tools" / "hostessctl" / "connectivity_udp.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("from tools.hostessctl.connectivity_bluetooth import", probe_source)
        self.assertIn("from tools.hostessctl.connectivity_data_protocols import", probe_source)
        self.assertIn("from tools.hostessctl.connectivity_probe_common import", probe_source)
        self.assertIn("from tools.hostessctl.connectivity_udp import", probe_source)
        self.assertNotIn("def device_to_host_udp_freshness", probe_source)
        self.assertNotIn("def lsl_discovery_sample_continuity", probe_source)
        self.assertNotIn("def osc_loopback_probe", probe_source)
        self.assertNotIn("def run_qcl050_android_rfcomm_probe", probe_source)
        self.assertNotIn("def zeromq_loopback_probe", probe_source)
        self.assertIn("def run_qcl050_android_rfcomm_probe", bluetooth_source)
        self.assertIn("def lsl_discovery_sample_continuity", protocol_source)
        self.assertIn("def osc_loopback_probe", protocol_source)
        self.assertIn("def zeromq_loopback_probe", protocol_source)
        self.assertIn("def check_row", common_source)
        self.assertIn("def device_to_host_udp_freshness", udp_source)

    def test_live_lsl_report_classifies_host_loopback_as_warning(self) -> None:
        report = live_lsl_report(
            probe_args(mode="live", probe_id="QCL-081", host_ip="192.0.2.10"),
            run_captured_func=FakeRunner(),
            run_timeout_func=FakeTimeoutRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            lsl_probe_func=fake_lsl_loopback_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-081")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(check(report, "protocol.lsl_discovery")["status"], "pass")
        self.assertEqual(check(report, "protocol.lsl_sample_continuity")["status"], "pass")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_lsl_report_promotes_manifold_lsl_broker_evidence(self) -> None:
        report = live_lsl_report(
            probe_args(
                mode="live",
                probe_id="QCL-081",
                host_ip="",
                lsl_source="manifold-lsl-broker",
            ),
            run_captured_func=FakeRunner(),
            run_timeout_func=FakeTimeoutRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [],
            lsl_probe_func=fake_manifold_lsl_broker_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-081")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["endpoint_source"], "manifold-lsl-broker")
        self.assertEqual(check(report, "protocol.lsl_discovery")["status"], "pass")
        self.assertEqual(check(report, "protocol.lsl_sample_continuity")["status"], "pass")
        self.assertEqual(report["lsl_payload_probe"]["evidence_tier"], "broker_owned")
        self.assertEqual(report["lsl_payload_probe"]["authority_owner"], "rusty.manifold.transport")
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_lsl_report_does_not_promote_external_source(self) -> None:
        report = live_lsl_report(
            probe_args(
                mode="live",
                probe_id="QCL-081",
                adb="adb.exe",
                serial="serial-1",
                host_ip="192.0.2.10",
                lsl_source="external",
            ),
            run_captured_func=FakeRunner(),
            run_timeout_func=FakeTimeoutRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            lsl_probe_func=fake_external_lsl_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["endpoint_source"], "external")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_osc_report_classifies_host_loopback_as_warning(self) -> None:
        report = live_osc_report(
            probe_args(mode="live", probe_id="QCL-083", host_ip="192.0.2.10"),
            run_captured_func=FakeRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            osc_probe_func=fake_osc_loopback_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-083")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(check(report, "protocol.osc_message_shape")["status"], "pass")
        self.assertEqual(check(report, "protocol.osc_payload_exchange")["status"], "pass")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_zeromq_report_classifies_host_loopback_as_warning(self) -> None:
        report = live_zeromq_report(
            probe_args(mode="live", probe_id="QCL-084", host_ip="192.0.2.10"),
            run_captured_func=FakeRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            zeromq_probe_func=fake_zeromq_loopback_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-084")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(check(report, "protocol.zeromq_dependency")["status"], "pass")
        self.assertEqual(check(report, "protocol.zeromq_payload_exchange")["status"], "pass")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_zeromq_report_blocks_when_dependency_missing(self) -> None:
        report = live_zeromq_report(
            probe_args(mode="live", probe_id="QCL-084", host_ip="192.0.2.10"),
            run_captured_func=FakeRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            zeromq_probe_func=fake_zeromq_dependency_missing,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "protocol.zeromq_dependency")["status"], "blocked")
        self.assertEqual(check(report, "protocol.zeromq_payload_exchange")["status"], "blocked")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_zeromq_report_promotes_native_rust_broker_evidence(self) -> None:
        report = live_zeromq_report(
            probe_args(
                mode="live",
                probe_id="QCL-084",
                host_ip="",
                zeromq_source="native-rust-broker",
                zeromq_pattern="pub-sub",
            ),
            run_captured_func=FakeRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [],
            zeromq_probe_func=fake_native_rust_broker_zeromq_pass,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-084")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"]["endpoint_source"], "native-rust-broker")
        self.assertEqual(check(report, "protocol.zeromq_dependency")["status"], "pass")
        self.assertEqual(check(report, "protocol.zeromq_payload_exchange")["status"], "pass")
        self.assertEqual(report["zeromq_payload_probe"]["evidence_tier"], "broker_owned")
        self.assertEqual(report["zeromq_payload_probe"]["authority_owner"], "rusty.manifold.transport")
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_bluetooth_report_classifies_passive_readiness_as_warning(self) -> None:
        report = live_bluetooth_report(
            probe_args(mode="live", probe_id="QCL-050"),
            run_captured_func=FakeRunner(),
            clock_func=fixed_datetime,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-050")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(check(report, "host.bluetooth_adapter")["status"], "pass")
        self.assertEqual(check(report, "host.bluetooth_service")["status"], "pass")
        self.assertEqual(check(report, "device.bluetooth_adapter")["status"], "pass")
        self.assertEqual(check(report, "protocol.rfcomm_control")["status"], "skipped")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_bluetooth_report_runs_android_rfcomm_payload_probe(self) -> None:
        report = live_bluetooth_report(
            probe_args(
                mode="live",
                probe_id="QCL-050",
                run_id="qcl050-unit-rfcomm",
                bluetooth_payload_source="android-rfcomm",
                bluetooth_helper="fixture-qcl050-helper.exe",
                bluetooth_message_count=3,
                bluetooth_timeout_seconds=3.0,
            ),
            run_captured_func=FakeRunner(),
            clock_func=fixed_datetime,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-050")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(check(report, "bluetooth.permission_state")["status"], "pass")
        self.assertEqual(check(report, "bluetooth.pairing_bond_state")["status"], "pass")
        self.assertEqual(check(report, "protocol.rfcomm_control")["status"], "pass")
        self.assertEqual(check(report, "protocol.bluetooth_payload_exchange")["status"], "pass")
        self.assertEqual(check(report, "bluetooth.cleanup_state")["status"], "pass")
        self.assertEqual(check(report, "bluetooth.reconnect_cleanup")["status"], "skipped")
        self.assertEqual(report["bluetooth_payload_probe"]["status"], "pass")
        self.assertGreater(report["measurements"]["bluetooth_bytes_exchanged"], 0)
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_bluetooth_report_runs_android_ble_gatt_payload_probe(self) -> None:
        report = live_bluetooth_report(
            probe_args(
                mode="live",
                probe_id="QCL-051",
                run_id="qcl051-unit-ble-gatt",
                bluetooth_payload_source="android-ble-gatt",
                bluetooth_helper="fixture-qcl051-helper.exe",
                bluetooth_message_count=3,
                bluetooth_timeout_seconds=3.0,
            ),
            run_captured_func=FakeRunner(),
            clock_func=fixed_datetime,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-051")
        self.assertEqual(report["status"], "warn")
        self.assertEqual(check(report, "bluetooth.permission_state")["status"], "pass")
        self.assertEqual(check(report, "bluetooth.pairing_bond_state")["status"], "pass")
        self.assertEqual(check(report, "protocol.ble_gatt_status")["status"], "pass")
        self.assertEqual(check(report, "protocol.bluetooth_payload_exchange")["status"], "pass")
        self.assertEqual(check(report, "bluetooth.cleanup_state")["status"], "pass")
        self.assertEqual(check(report, "bluetooth.reconnect_cleanup")["status"], "skipped")
        self.assertEqual(report["bluetooth_payload_probe"]["status"], "pass")
        self.assertGreater(report["measurements"]["bluetooth_bytes_exchanged"], 0)
        self.assertEqual(report["measurements"]["bluetooth_rtt_ms_p95"], 15.0)
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_bluetooth_report_runs_android_ble_gatt_reconnect_probe(self) -> None:
        report = live_bluetooth_report(
            probe_args(
                mode="live",
                probe_id="QCL-051",
                run_id="qcl051-unit-ble-gatt",
                bluetooth_payload_source="android-ble-gatt",
                bluetooth_helper="fixture-qcl051-helper.exe",
                bluetooth_message_count=3,
                bluetooth_reconnect_count=1,
                bluetooth_timeout_seconds=3.0,
            ),
            run_captured_func=FakeRunner(),
            clock_func=fixed_datetime,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-051")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(check(report, "bluetooth.permission_state")["status"], "pass")
        self.assertEqual(check(report, "bluetooth.pairing_bond_state")["status"], "pass")
        self.assertEqual(check(report, "protocol.ble_gatt_status")["status"], "pass")
        self.assertEqual(check(report, "protocol.bluetooth_payload_exchange")["status"], "pass")
        self.assertEqual(check(report, "bluetooth.cleanup_state")["status"], "pass")
        self.assertEqual(check(report, "bluetooth.reconnect_cleanup")["status"], "pass")
        self.assertEqual(report["bluetooth_payload_probe"]["status"], "pass")
        self.assertEqual(report["bluetooth_payload_probe"]["session_count"], 2)
        self.assertEqual(report["bluetooth_payload_probe"]["reconnect_attempts_completed"], 1)
        self.assertEqual(report["measurements"]["reconnect_attempts"], 1)
        self.assertGreater(report["measurements"]["bluetooth_bytes_exchanged"], 0)
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_live_bluetooth_report_blocks_when_quest_activity_launch_is_locked(self) -> None:
        report = live_bluetooth_report(
            probe_args(
                mode="live",
                probe_id="QCL-051",
                run_id="qcl051-unit-locked",
                bluetooth_payload_source="android-ble-gatt",
            ),
            run_captured_func=FakeRunner(quest_activity_locked=True),
            clock_func=fixed_datetime,
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "bluetooth.activity_launch_state")["status"], "blocked")
        self.assertEqual(check(report, "protocol.ble_gatt_status")["status"], "blocked")
        self.assertEqual(report["bluetooth_payload_probe"]["status"], "blocked")
        self.assertEqual(validation["status"], "pass")

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
        self.assertEqual(args.osc_source, "host-loopback")
        self.assertEqual(args.osc_message_count, 6)
        self.assertEqual(args.zeromq_source, "host-loopback")
        self.assertEqual(args.zeromq_manifold_root, "S:/Work/repos/active/rusty-manifold")
        self.assertEqual(args.zeromq_message_count, 7)
        self.assertEqual(args.bluetooth_payload_source, "android-ble-gatt")
        self.assertEqual(args.bluetooth_message_count, 5)
        self.assertEqual(args.bluetooth_timeout_seconds, 7.0)
        self.assertEqual(args.hostess_android_package, "io.example.hostess")

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
                "--out",
                "target/qcl082.json",
            ]
        )

        self.assertEqual(args.probe_id, "QCL-082")
        self.assertEqual(args.fixture_profile, "qcl-082-media-binary-plane-pass")

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


def fake_tcp_echo_pass(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    return {
        "name": "device_to_host.tcp_echo",
        "status": "pass",
        "evidence": "rusty-qcl-tcp-echo",
        "observed": {"host_ip": host_ip, "port": 49152, "elapsed_ms": 8},
        "notes": "",
        "issue_codes": [],
    }


def fake_tcp_echo_fail(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    return {
        "name": "device_to_host.tcp_echo",
        "status": "fail",
        "evidence": "timed out",
        "observed": {"host_ip": host_ip, "port": 49152, "elapsed_ms": 6000},
        "notes": "",
        "issue_codes": ["hostess.issue.connectivity_probe.tcp_echo_failed"],
    }


def fake_udp_freshness_pass(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    return {
        "name": "protocol.udp_freshness",
        "status": "pass",
        "evidence": "12/12 packets, loss=0.0%, p95_gap=50ms",
        "observed": {
            "host_ip": host_ip,
            "port": DEFAULT_QCL080_UDP_PORT,
            "marker": "rusty-qcl-udp",
            "packets_requested": 12,
            "packets_received": 12,
            "datagrams_received": 12,
            "unique_sequences": list(range(12)),
            "duplicates": 0,
            "loss_percent": 0.0,
            "elapsed_ms": 700,
            "interarrival_ms_p95": 50,
            "generator": "adb_shell_udp_generator",
        },
        "notes": "fixture UDP pass",
        "issue_codes": [],
    }


def fake_udp_freshness_app_owned_pass(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    return {
        "name": "protocol.udp_freshness",
        "status": "pass",
        "evidence": "12/12 packets, loss=0.0%, p95_gap=50ms",
        "observed": {
            "host_ip": host_ip,
            "port": DEFAULT_QCL080_UDP_PORT,
            "marker": "rusty-qcl-udp",
            "packets_requested": 12,
            "packets_received": 12,
            "datagrams_received": 12,
            "unique_sequences": list(range(12)),
            "duplicates": 0,
            "loss_percent": 0.0,
            "elapsed_ms": 700,
            "interarrival_ms_p95": 50,
            "generator": "app_owned_runtime_udp_sender",
            "runtime_marker": {
                "line": "RUSTY_HOSTESS_MAKEPAD_QCL080_UDP_SENDER schema=rusty.hostess.makepad.qcl080_udp_sender.v1 status=sent marker=rusty-qcl-udp packetsRequested=12 packetsSent=12 runId=qcl080-app senderSource=makepad-runtime socketOwner=app-owned",
                "fields": {
                    "schema": "rusty.hostess.makepad.qcl080_udp_sender.v1",
                    "status": "sent",
                    "marker": "rusty-qcl-udp",
                    "packetsRequested": "12",
                    "packetsSent": "12",
                    "runId": "qcl080-app",
                    "senderSource": "makepad-runtime",
                    "socketOwner": "app-owned",
                },
                "matched": True,
            },
        },
        "notes": "fixture app-owned UDP pass",
        "issue_codes": [],
    }


def fake_lsl_loopback_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "host-loopback",
        "stream_name": "RustyQCL081",
        "stream_type": "Markers",
        "samples_requested": 16,
        "samples_received": 16,
        "loss_percent": 0.0,
        "discovery_ms": 42,
        "monotonic_sequences": True,
        "received_sequences": list(range(16)),
        "issue_codes": [],
        "notes": "host-local LSL loopback",
    }


def fake_manifold_lsl_broker_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
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
        "notes": "Manifold-owned LSL route evidence",
    }


def fake_external_lsl_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "external",
        "stream_name": "RustyQCL081",
        "stream_type": "Markers",
        "samples_requested": 16,
        "samples_received": 16,
        "loss_percent": 0.0,
        "discovery_ms": 42,
        "monotonic_sequences": True,
        "received_sequences": list(range(16)),
        "issue_codes": [],
        "notes": "External LSL stream without Quest-runtime or broker-owned authority",
    }


def fake_osc_loopback_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "host-loopback",
        "address": "/rusty/qcl083",
        "messages_requested": 16,
        "messages_received": 16,
        "messages_acknowledged": 16,
        "loss_percent": 0.0,
        "round_trip_ms_p95": 8,
        "monotonic_sequences": True,
        "received_sequences": list(range(16)),
        "issue_codes": [],
        "notes": "host-local OSC loopback",
    }


def fake_zeromq_loopback_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "host-loopback",
        "pattern": "req-rep",
        "messages_requested": 16,
        "messages_received": 16,
        "messages_acknowledged": 16,
        "round_trip_ms_p95": 5,
        "received_sequences": list(range(16)),
        "issue_codes": [],
        "notes": "host-local ZeroMQ loopback",
    }


def fake_native_rust_broker_zeromq_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "native-rust-broker",
        "pattern": "pub-sub",
        "messages_requested": 16,
        "messages_received": 16,
        "messages_acknowledged": 16,
        "round_trip_ms_p95": None,
        "received_sequences": list(range(16)),
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
        "notes": "native Rust Manifold-owned ZeroMQ route evidence",
    }


def fake_zeromq_dependency_missing(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "blocked",
        "source": "host-loopback",
        "pattern": "req-rep",
        "messages_requested": 16,
        "messages_received": 0,
        "messages_acknowledged": 0,
        "round_trip_ms_p95": None,
        "received_sequences": [],
        "issue_codes": ["hostess.issue.connectivity_probe.pyzmq_unavailable"],
        "notes": "pyzmq unavailable",
    }


class FakeRunner:
    def __init__(
        self,
        *,
        protocol: str = "TCP",
        listener_port: int = 49152,
        quest_activity_locked: bool = False,
    ) -> None:
        self.protocol = protocol
        self.listener_port = listener_port
        self.quest_activity_locked = quest_activity_locked

    def __call__(
        self,
        command: list[str],
        *,
        allow_failure: bool = False,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        text = " ".join(command)
        if "get-state" in text:
            return subprocess.CompletedProcess(command, 0, "device\n", "")
        if "ro.product.model" in text:
            return subprocess.CompletedProcess(command, 0, "Quest 3S\n", "")
        if "ro.build.version.sdk" in text:
            return subprocess.CompletedProcess(command, 0, "35\n", "")
        if "ro.build.version.incremental" in text:
            return subprocess.CompletedProcess(command, 0, "2.5.fixture\n", "")
        if "ip -o -4 addr show wlan0" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                "21: wlan0 inet 192.0.2.42/24 brd 192.0.2.255 scope global wlan0\n",
                "",
            )
        if "NetworkOperatorTetheringManager" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "available": True,
                        "state": "On",
                        "source_profile": "fixture-upstream",
                        "client_count": 1,
                        "max_client_count": 8,
                        "ssid": "RustyHostess-QCL011",
                        "passphrase_set": True,
                        "band": "Auto",
                    }
                ),
                "",
            )
        if "Get-PnpDevice -Class Bluetooth" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "available": True,
                        "adapter_status": "OK",
                        "adapter_name": "fixture Bluetooth Adapter",
                        "bthserv_status": "Running",
                        "user_service_running": True,
                        "service_count": 2,
                        "address_redacted": True,
                    }
                ),
                "",
            )
        if "dumpsys bluetooth_manager" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                "\n".join(
                    [
                        "Bluetooth Status",
                        "  enabled: true",
                        "  state: ON",
                        "  address: 12:34:56:78:9A:BC",
                        "  name: Quest fixture",
                        "AdapterProperties",
                        "  Name: Quest fixture",
                        "  Address: 12:34:56:78:9A:BC",
                        "  ConnectionState: STATE_DISCONNECTED",
                        "  State: ON",
                        "  Bonded devices:",
                        "    XX:XX:XX:XX:A5:A5 last_active_time=0",
                    ]
                ),
                "",
            )
        if "cmd bluetooth_manager" in text:
            return subprocess.CompletedProcess(
                command,
                1,
                "Bluetooth Manager Commands:\n  enable\n  disable\n  wait-for-state:<STATE>\n",
                "",
            )
        if "dumpsys activity activities" in text:
            if self.quest_activity_locked:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    "topResumedActivity=ActivityRecord{fixture com.oculus.os.vrlockscreen/.SensorLockActivity}\n",
                    "",
                )
            return subprocess.CompletedProcess(
                command,
                0,
                "topResumedActivity=ActivityRecord{fixture io.github.mesmerprism.rustyhostess.t/.MainActivity}\n",
                "",
            )
        if " shell pm grant " in text and "android.permission.BLUETOOTH_" in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell rm -f " in text and "qcl050-rfcomm/latest.json" in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell rm -f " in text and "qcl051-ble-gatt/latest.json" in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell am force-stop " in text and "io.github.mesmerprism.rustyhostess.t" in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell am start " in text and "RUN_QCL050_RFCOMM" in text:
            return subprocess.CompletedProcess(command, 0, "Starting: Intent\n", "")
        if " shell am start " in text and "RUN_QCL051_BLE_GATT" in text:
            return subprocess.CompletedProcess(command, 0, "Starting: Intent\n", "")
        if "fixture-qcl050-helper.exe" in text:
            helper_out = Path(command[command.index("--out") + 1])
            run_id = command[command.index("--run-id") + 1]
            helper_out.parent.mkdir(parents=True, exist_ok=True)
            helper_out.write_text(json.dumps(qcl050_windows_helper_report(run_id=run_id)) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")
        if "fixture-qcl051-helper.exe" in text:
            helper_out = Path(command[command.index("--out") + 1])
            run_id = command[command.index("--run-id") + 1]
            helper_out.parent.mkdir(parents=True, exist_ok=True)
            helper_out.write_text(json.dumps(qcl051_windows_helper_report(run_id=run_id)) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell cat " in text and "qcl050-rfcomm/latest.json" in text:
            return subprocess.CompletedProcess(command, 0, json.dumps(qcl050_android_probe_report()) + "\n", "")
        if " shell cat " in text and "qcl051-ble-gatt/latest.json" in text:
            return subprocess.CompletedProcess(command, 0, json.dumps(qcl051_android_probe_report()) + "\n", "")
        if "Get-NetConnectionProfile" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                firewall_profile_json(protocol=self.protocol, listener_port=self.listener_port),
                "",
            )
        return subprocess.CompletedProcess(command, 1, "", f"unexpected command: {text}")


class FakeTimeoutRunner:
    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        text = " ".join(command)
        if "ping" in text:
            return subprocess.CompletedProcess(command, 0, "2 packets transmitted, 2 received, 0% packet loss\n", "")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected timeout command: {text}")


class OneWayPingTimeoutRunner:
    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        text = " ".join(command)
        if text.startswith("ping "):
            return subprocess.CompletedProcess(command, 0, "Packets: Sent = 2, Received = 2, Lost = 0 (0% loss),\n", "")
        if " shell ping " in text:
            return subprocess.CompletedProcess(command, 1, "2 packets transmitted, 0 received, 100% packet loss\n", "")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected timeout command: {text}")


class TcpEchoCommandRunner:
    def __init__(self) -> None:
        self.command: list[str] = []

    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        self.command = command
        command_text = command[-1]
        parts = command_text.split()
        host_index = parts.index("127.0.0.1")
        port = int(parts[host_index + 1])
        with socket.create_connection(("127.0.0.1", port), timeout=timeout_seconds) as client:
            client.sendall(b"rusty-qcl-tcp-echo")
        return subprocess.CompletedProcess(command, 0, "", "")


class UdpFreshnessCommandRunner:
    def __init__(self) -> None:
        self.command: list[str] = []

    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        self.command = command
        command_text = command[-1]
        parts = command_text.split()
        host_index = parts.index("127.0.0.1")
        port = int(parts[host_index + 1])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.settimeout(timeout_seconds)
            for sequence in range(4):
                client.sendto(f"rusty-qcl-udp|{sequence:04d}\n".encode("utf-8"), ("127.0.0.1", port))
        return subprocess.CompletedProcess(command, 0, "", "")


class MakepadRuntimeUdpCommandRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.properties: dict[str, str] = {}

    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        text = " ".join(command)
        if " shell setprop " in text:
            key = command[-2]
            value = command[-1]
            self.properties[key] = value
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell am force-stop " in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell am start " in text:
            self.send_configured_packets(timeout_seconds)
            return subprocess.CompletedProcess(command, 0, "Starting: Intent\n", "")
        if " shell logcat " in text:
            return subprocess.CompletedProcess(command, 0, self.logcat_text(), "")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected command: {text}")

    def send_configured_packets(self, timeout_seconds: float) -> None:
        host = self.properties["debug.rustyquest.makepad.qcl080.udp.host"]
        port = int(self.properties["debug.rustyquest.makepad.qcl080.udp.port"])
        marker = self.properties["debug.rustyquest.makepad.qcl080.udp.marker"]
        count = int(self.properties["debug.rustyquest.makepad.qcl080.udp.packet.count"])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.settimeout(timeout_seconds)
            for sequence in range(count):
                client.sendto(f"{marker}|{sequence:04d}\n".encode("utf-8"), (host, port))

    def logcat_text(self) -> str:
        marker = self.properties["debug.rustyquest.makepad.qcl080.udp.marker"]
        run_id = self.properties["debug.rustyquest.makepad.qcl080.udp.run.id"]
        count = self.properties["debug.rustyquest.makepad.qcl080.udp.packet.count"]
        host = self.properties["debug.rustyquest.makepad.qcl080.udp.host"]
        port = self.properties["debug.rustyquest.makepad.qcl080.udp.port"]
        return (
            "06-28 13:00:00.000 I/HostessMakepad: "
            "RUSTY_HOSTESS_MAKEPAD_QCL080_UDP_SENDER "
            "schema=rusty.hostess.makepad.qcl080_udp_sender.v1 "
            f"phase=startup status=sent enabled=true host={host} port={port} "
            f"marker={marker} packetsRequested={count} packetsSent={count} "
            f"intervalMs=1 elapsedMs=4 runId={run_id} issue=none "
            "senderSource=makepad-runtime socketOwner=app-owned "
            "highRateJsonPayload=false settingsControlPayload=false\n"
        )


def check(report: dict[str, Any], name: str) -> dict[str, Any]:
    for row in report["checks"]:
        if row["name"] == name:
            return row
    raise AssertionError(f"missing check {name}")


def probe_args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "command": "connectivity-probe",
        "connectivity_probe_command": "run",
        "out": "target/connectivity-probe/report.json",
        "validation_out": None,
        "probe_id": "QCL-010",
        "run_id": "",
        "mode": "fixture",
        "fixture_profile": "",
        "adb": "adb.exe",
        "serial": "serial-1",
        "wifi_interface": "wlan0",
        "host_ip": "",
        "topology_owner": "",
        "network_provider": "",
        "skip_host_ping": False,
        "skip_device_ping": False,
        "skip_tcp_echo": False,
        "tcp_echo_bind_host": "0.0.0.0",
        "tcp_echo_port": 0,
        "tcp_echo_marker": "rusty-qcl-tcp-echo",
        "tcp_timeout_seconds": 1.0,
        "skip_udp_freshness": False,
        "udp_bind_host": "0.0.0.0",
        "udp_port": 0,
        "udp_marker": "rusty-qcl-udp",
        "udp_packet_count": 12,
        "udp_interval_ms": 50.0,
        "udp_timeout_seconds": 1.0,
        "udp_max_loss_percent": 10.0,
        "udp_max_jitter_ms": 250.0,
        "udp_listener_helper": "",
        "udp_sender_source": "auto",
        "udp_sender_host_path": "",
        "udp_sender_device_path": "/data/local/tmp/rusty-qcl080-udp-sender",
        "makepad_package": "io.github.mesmerprism.rustyhostess.makepad",
        "makepad_activity": "io.github.mesmerprism.rustyhostess.makepad/.MakepadAppXr",
        "skip_makepad_force_stop": False,
        "makepad_launch_timeout_seconds": 10.0,
        "lsl_source": "host-loopback",
        "lsl_stream_name": "RustyQCL081",
        "lsl_stream_type": "Markers",
        "lsl_sample_count": 16,
        "lsl_timeout_seconds": 1.0,
        "lsl_manifold_root": "",
        "osc_source": "host-loopback",
        "osc_address": "/rusty/qcl083",
        "osc_port": 0,
        "osc_message_count": 16,
        "osc_timeout_seconds": 1.0,
        "osc_max_loss_percent": 0.0,
        "zeromq_source": "host-loopback",
        "zeromq_pattern": "req-rep",
        "zeromq_message_count": 16,
        "zeromq_timeout_seconds": 1.0,
        "zeromq_manifold_root": "",
        "zeromq_rusty_xr_root": "",
        "zeromq_goofi_bridge_root": "",
        "zeromq_cargo_timeout_seconds": 120.0,
        "ping_count": 2,
        "ping_timeout_seconds": 1.0,
        "fail_on_error": False,
        "bluetooth_payload_source": "passive",
        "bluetooth_helper": "",
        "bluetooth_message_count": 3,
        "bluetooth_reconnect_count": 0,
        "bluetooth_timeout_seconds": 20.0,
        "hostess_android_package": "io.github.mesmerprism.rustyhostess.t",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def qcl050_windows_helper_report(*, run_id: str = "qcl050-unit-rfcomm") -> dict[str, Any]:
    return {
        "schema": "rusty.hostess.windows.qcl050_rfcomm_client.v1",
        "schema_version": 1,
        "run_id": run_id,
        "status": "pass",
        "role": "windows_rfcomm_client",
        "messages_requested": 3,
        "messages_completed": 3,
        "bytes_written": 99,
        "bytes_read": 183,
        "selected_device": {
            "id_redacted": True,
            "name": "Quest",
            "is_paired": True,
            "can_pair": False,
        },
        "measurements": {
            "round_trip_ms_p95": 22.0,
            "round_trip_ms_max": 22.0,
        },
        "messages": [
            {"sequence": 1, "payload_bytes": 33, "status_bytes": 61, "round_trip_ms": 18.0},
            {"sequence": 2, "payload_bytes": 33, "status_bytes": 61, "round_trip_ms": 20.0},
            {"sequence": 3, "payload_bytes": 33, "status_bytes": 61, "round_trip_ms": 22.0},
        ],
        "issues": [],
        "errors": [],
    }


def qcl050_android_probe_report() -> dict[str, Any]:
    return {
        "schema": "rusty.hostess.android.qcl050_rfcomm_probe.v1",
        "schema_version": 1,
        "run_id": "qcl050-unit-rfcomm",
        "status": "pass",
        "role": "quest_rfcomm_server",
        "authority": "app_owned_runtime_rfcomm_server",
        "messages_expected": 3,
        "messages_received": 3,
        "bytes_received": 99,
        "bytes_written": 183,
        "client_addresses_redacted": True,
        "permissions": {
            "bluetooth_connect": True,
            "address_redacted": True,
        },
        "rfcomm_server": {
            "server_socket_opened": True,
            "server_socket_closed": True,
            "client_socket_accepted": True,
            "client_socket_closed": True,
        },
        "payloads": [
            {"sequence": 1, "byte_count": 33, "redacted": False},
            {"sequence": 2, "byte_count": 33, "redacted": False},
            {"sequence": 3, "byte_count": 33, "redacted": False},
        ],
        "errors": [],
        "issue_codes": [],
    }


def qcl051_windows_helper_report(*, run_id: str = "qcl051-unit-ble-gatt") -> dict[str, Any]:
    return {
        "schema": "rusty.hostess.windows.qcl051_ble_gatt_client.v1",
        "schema_version": 1,
        "run_id": run_id,
        "status": "pass",
        "role": "windows_ble_gatt_client",
        "messages_requested": 3,
        "messages_completed": 3,
        "bytes_written": 96,
        "bytes_read": 180,
        "selected_device": {
            "address_redacted": True,
            "local_name": "",
            "is_paired": False,
            "can_pair": True,
        },
        "measurements": {
            "round_trip_ms_p95": 15.0,
            "round_trip_ms_max": 15.0,
        },
        "messages": [
            {"sequence": 1, "payload_bytes": 32, "status_bytes": 60, "round_trip_ms": 10.0},
            {"sequence": 2, "payload_bytes": 32, "status_bytes": 60, "round_trip_ms": 12.0},
            {"sequence": 3, "payload_bytes": 32, "status_bytes": 60, "round_trip_ms": 15.0},
        ],
        "issues": [],
        "errors": [],
    }


def qcl051_android_probe_report() -> dict[str, Any]:
    return {
        "schema": "rusty.hostess.android.qcl051_ble_gatt_probe.v1",
        "schema_version": 1,
        "run_id": "qcl051-unit-ble-gatt",
        "status": "pass",
        "role": "quest_ble_gatt_server",
        "authority": "app_owned_runtime_ble_gatt_server",
        "messages_expected": 3,
        "messages_received": 3,
        "read_requests": 3,
        "bytes_received": 96,
        "bytes_read": 180,
        "client_addresses_redacted": True,
        "permissions": {
            "bluetooth_connect": True,
            "bluetooth_advertise": True,
            "address_redacted": True,
        },
        "advertising": {
            "started": True,
            "stopped": True,
        },
        "gatt_server": {
            "opened": True,
            "closed": True,
            "service_added": True,
            "service_add_status": 0,
        },
        "payloads": [
            {"sequence": 1, "byte_count": 32, "redacted": False},
            {"sequence": 2, "byte_count": 32, "redacted": False},
            {"sequence": 3, "byte_count": 32, "redacted": False},
        ],
        "errors": [],
        "issue_codes": [],
    }


def fixed_datetime() -> datetime:
    return datetime(2026, 6, 28, 13, 0, 0, tzinfo=UTC)


def firewall_profile_json(
    *,
    active_category: str = "Private",
    allowed: bool = True,
    protocol: str = "TCP",
    listener_port: int = 49152,
) -> str:
    protocol_number = 17 if protocol == "UDP" else 6
    return json.dumps(
        {
            "connections": [
                {
                    "Name": "fixture-wifi",
                    "InterfaceAlias": "Wi-Fi",
                    "InterfaceIndex": 16,
                    "NetworkCategory": active_category,
                    "IPv4Connectivity": "Internet",
                    "IPv6Connectivity": "Internet",
                }
            ],
            "firewall": [
                {
                    "Name": name,
                    "Enabled": True,
                    "DefaultInboundAction": "NotConfigured",
                    "DefaultOutboundAction": "NotConfigured",
                    "AllowInboundRules": "NotConfigured",
                    "NotifyOnListen": True,
                    "LogFileName": "%systemroot%\\system32\\LogFiles\\Firewall\\pfirewall.log",
                    "LogBlocked": False,
                    "LogAllowed": False,
                }
                for name in ["Domain", "Private", "Public"]
            ],
            "listener_firewall": {
                "program": "python.exe",
                "protocol": protocol,
                "port": listener_port,
                "bind_host": "0.0.0.0",
                "expected_rule_name": (
                    f"Rusty Hostess WPF QCL-080 UDP Freshness {listener_port}"
                    if protocol == "UDP"
                    else f"Rusty Hostess WPF QCL-010 TCP Echo {listener_port}"
                ),
                "expected_remote_address": "LocalSubnet",
                "active_profiles": [active_category],
                "matching_rule_count": 1 if allowed else 0,
                "product_matching_rule_count": 0,
                "product_rule_verified": False,
                "matching_rules": [
                    {
                        "name": "Rusty Hostess connectivity probe fixture",
                        "profiles": [active_category],
                        "profile_mask": 2 if active_category == "Private" else 4,
                        "protocol": protocol_number,
                        "local_ports": str(listener_port),
                        "remote_addresses": "LocalSubnet",
                        "application_name": "python.exe",
                        "profiles_apply_to_active": True,
                        "program_matches": True,
                        "name_matches": False,
                        "remote_address_matches": True,
                        "product_scope_matches": False,
                    }
                ]
                if allowed
                else [],
                "allowed_on_active_profile": allowed,
                "probe": "windows_firewall_com_policy",
            },
        }
    )


if __name__ == "__main__":
    unittest.main()
