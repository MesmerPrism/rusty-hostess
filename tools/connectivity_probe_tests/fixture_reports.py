from __future__ import annotations

from tools.connectivity_probe_tests.helpers import *


class HostessCtlConnectivityProbeFixtureTests(unittest.TestCase):
    def test_connectivity_probe_reexports_firewall_report_helper(self) -> None:
        self.assertIs(facade_windows_firewall_rule_report, windows_firewall_rule_report)

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

    def test_qcl020_fixture_validates_wifi_adb_session_pass(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-020", fixture_profile="qcl-020-wifi-adb-session-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-020")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["classification"], "developer_only")
        self.assertEqual(report["transport"]["family"], "adb_wifi")
        self.assertEqual(check(report, "companion_session.wifi_serial")["status"], "pass")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl020_damaged_fixture_reports_wifi_adb_reconnect_loss(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-020", fixture_profile="qcl-020-wifi-adb-reconnect-lost"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "adb_wifi.reconnect")["status"], "blocked")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.wifi_adb_reconnect_lost"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl030_fixture_validates_local_only_hotspot_started(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-030", fixture_profile="qcl-030-local-only-hotspot-started"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-030")
        self.assertEqual(report["topology"]["owner"], "local_only_hotspot")
        self.assertEqual(check(report, "android.local_only_hotspot.started")["status"], "pass")
        self.assertEqual(check(report, "topology.socket_exchange")["status"], "pass")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")

    def test_qcl030_damaged_fixture_reports_local_only_hotspot_failure(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-030", fixture_profile="qcl-030-local-only-hotspot-failed"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "android.local_only_hotspot.started")["status"], "blocked")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.local_only_hotspot_start_failed"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl040_fixture_validates_wifi_direct_phone_peer(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-040", fixture_profile="qcl-040-wifi-direct-phone-peer-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-040")
        self.assertEqual(report["topology"]["owner"], "wifi_direct")
        self.assertEqual(report["topology"]["peer_class"], "android_phone")
        self.assertEqual(check(report, "wifi_direct.group_formation")["status"], "pass")
        self.assertEqual(validation["status"], "pass")

    def test_qcl040_damaged_fixture_reports_wifi_direct_permission_denied(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-040", fixture_profile="qcl-040-wifi-direct-permission-denied"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "wifi_direct.permission_state")["status"], "blocked")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.wifi_direct_permission_denied"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl041_fixture_validates_wifi_direct_windows_peer(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-041", fixture_profile="qcl-041-wifi-direct-windows-peer-pass"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-041")
        self.assertEqual(report["topology"]["peer_class"], "windows")
        self.assertEqual(check(report, "windows.wifi_direct_api")["status"], "pass")
        self.assertEqual(check(report, "topology.socket_exchange")["status"], "pass")
        self.assertEqual(validation["status"], "pass")

    def test_qcl041_damaged_fixture_reports_windows_driver_block(self) -> None:
        report = fixture_report(
            probe_args(probe_id="QCL-041", fixture_profile="qcl-041-wifi-direct-windows-driver-blocked"),
            observed_at=fixed_datetime(),
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(check(report, "windows.wifi_direct_api")["status"], "blocked")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.wifi_direct_windows_driver_unavailable"
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
