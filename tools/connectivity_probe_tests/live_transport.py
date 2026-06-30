from __future__ import annotations

from tools.connectivity_probe_tests.helpers import *


class HostessCtlConnectivityProbeLiveTransportTests(unittest.TestCase):
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

    def test_live_wifi_direct_topology_preflight_blocks_until_peer_lifecycle_exists(self) -> None:
        report = live_direct_wifi_topology_report(
            probe_args(mode="live", probe_id="QCL-041", host_ip="192.0.2.10"),
            run_captured_func=FakeRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
        )
        validation = validate_connectivity_probe_report(report)

        self.assertEqual(report["probe_id"], "QCL-041")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["topology"]["owner"], "wifi_direct")
        self.assertEqual(report["transport"]["route"], "wifi_direct_live_preflight")
        self.assertEqual(check(report, "wifi_direct.feature")["status"], "pass")
        self.assertEqual(check(report, "windows.wifi_direct_api")["status"], "pass")
        self.assertEqual(check(report, "wifi_direct.peer_discovery")["status"], "blocked")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.wifi_direct_live_topology_not_promoted"
                for issue in report["issues"]
            )
        )

    def test_run_connectivity_probe_routes_qcl040_live_to_wifi_direct_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "qcl040-live.json"
            status = run_connectivity_probe(
                probe_args(mode="live", probe_id="QCL-040", out=str(out)),
                run_captured_func=FakeRunner(),
                clock_func=fixed_datetime,
                host_ipv4_func=lambda: [{"ip": "192.0.2.10", "prefix_length": 24, "interface": "fixture"}],
            )
            report = json.loads(out.read_text(encoding="utf-8"))

        check_names = [row["name"] for row in report["checks"]]
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["transport"]["family"], "wifi_direct")
        self.assertIn("wifi_direct.peer_discovery", check_names)
        self.assertNotIn("device_to_host.tcp_echo", check_names)

    def test_wifi_direct_lifecycle_report_promotes_complete_qcl041_topology(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "qcl041-lifecycle.json"
            out = root / "qcl041-live-topology.json"
            lifecycle_path.write_text(
                json.dumps(wifi_direct_lifecycle_artifact(probe_id="QCL-041")),
                encoding="utf-8",
            )
            status = run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(out),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            report = json.loads(out.read_text(encoding="utf-8"))
            validation = validate_connectivity_probe_report(report)

        self.assertEqual(status, 0)
        self.assertEqual(report["probe_id"], "QCL-041")
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(report["transport"]["route"], "wifi_direct_lifecycle_artifact")
        self.assertEqual(check(report, "wifi_direct.lifecycle_source")["status"], "pass")
        self.assertEqual(check(report, "wifi_direct.quest_lease")["status"], "pass")
        self.assertEqual(check(report, "topology.socket_exchange")["status"], "pass")
        self.assertEqual(check(report, "wifi_direct.cleanup")["status"], "pass")
        self.assertEqual(report["measurements"]["cleanup_completed"], True)
        self.assertEqual(validation["status"], "pass")

    def test_wifi_direct_lifecycle_report_promotes_complete_qcl040_topology(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "qcl040-lifecycle.json"
            out = root / "qcl040-live-topology.json"
            lifecycle_path.write_text(
                json.dumps(wifi_direct_lifecycle_artifact(probe_id="QCL-040")),
                encoding="utf-8",
            )
            status = run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-040",
                    out=str(out),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            report = json.loads(out.read_text(encoding="utf-8"))
            validation = validate_connectivity_probe_report(report)

        self.assertEqual(status, 0)
        self.assertEqual(report["probe_id"], "QCL-040")
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["promotion"]["allowed"])
        self.assertEqual(report["topology"]["peer_class"], "android_phone")
        self.assertEqual(report["host"]["os"], "android_phone_peer")
        self.assertEqual(report["transport"]["route"], "wifi_direct_lifecycle_artifact")
        self.assertEqual(check(report, "wifi_direct.lifecycle_source")["status"], "pass")
        self.assertEqual(check(report, "wifi_direct.quest_lease")["status"], "pass")
        self.assertEqual(check(report, "topology.socket_exchange")["status"], "pass")
        self.assertEqual(check(report, "wifi_direct.cleanup")["status"], "pass")
        self.assertEqual(validation["status"], "pass")

    def test_wifi_direct_lifecycle_report_blocks_without_quest_lease_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "qcl041-lifecycle.json"
            out = root / "qcl041-live-topology.json"
            artifact = wifi_direct_lifecycle_artifact(probe_id="QCL-041")
            artifact.pop("lease")
            lifecycle_path.write_text(json.dumps(artifact), encoding="utf-8")

            status = run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(out),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            report = json.loads(out.read_text(encoding="utf-8"))
            validation = validate_connectivity_probe_report(report)

        lease_check = check(report, "wifi_direct.quest_lease")
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(lease_check["status"], "blocked")
        self.assertIn(
            "hostess.issue.connectivity_probe.wifi_direct_quest_lease_missing",
            lease_check["issue_codes"],
        )
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.wifi_direct_live_topology_not_promoted"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_wifi_direct_lifecycle_report_blocks_when_cleanup_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "qcl041-lifecycle.json"
            out = root / "qcl041-live-topology.json"
            lifecycle_path.write_text(
                json.dumps(wifi_direct_lifecycle_artifact(probe_id="QCL-041", cleanup=False)),
                encoding="utf-8",
            )
            status = run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(out),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            report = json.loads(out.read_text(encoding="utf-8"))
            validation = validate_connectivity_probe_report(report)

        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(check(report, "wifi_direct.cleanup")["status"], "blocked")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.wifi_direct_live_topology_not_promoted"
                for issue in report["issues"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_wifi_direct_lifecycle_report_blocks_when_group_roles_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "qcl041-lifecycle.json"
            out = root / "qcl041-live-topology.json"
            artifact = wifi_direct_lifecycle_artifact(probe_id="QCL-041")
            artifact["lifecycle"]["group_formation"].pop("local_role")
            lifecycle_path.write_text(json.dumps(artifact), encoding="utf-8")

            status = run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(out),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            report = json.loads(out.read_text(encoding="utf-8"))
            validation = validate_connectivity_probe_report(report)

        group_check = check(report, "wifi_direct.group_formation")
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(group_check["status"], "blocked")
        self.assertIn(
            "hostess.issue.connectivity_probe.wifi_direct_group_roles_missing",
            group_check["issue_codes"],
        )
        self.assertEqual(validation["status"], "pass")

    def test_wifi_direct_lifecycle_report_blocks_when_socket_counters_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "qcl041-lifecycle.json"
            out = root / "qcl041-live-topology.json"
            artifact = wifi_direct_lifecycle_artifact(probe_id="QCL-041")
            artifact["lifecycle"]["socket_exchange"].pop("messages_received")
            lifecycle_path.write_text(json.dumps(artifact), encoding="utf-8")

            status = run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(out),
                    wifi_direct_lifecycle_report=str(lifecycle_path),
                ),
                clock_func=fixed_datetime,
            )
            report = json.loads(out.read_text(encoding="utf-8"))
            validation = validate_connectivity_probe_report(report)

        socket_check = check(report, "topology.socket_exchange")
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(socket_check["status"], "blocked")
        self.assertIn(
            "hostess.issue.connectivity_probe.wifi_direct_socket_exchange_counters_missing",
            socket_check["issue_codes"],
        )
        self.assertEqual(validation["status"], "pass")

    def test_wifi_direct_lifecycle_template_is_non_promoting_source_contract(self) -> None:
        artifact = wifi_direct_lifecycle_template_artifact(
            probe_id="QCL-041",
            observed_at=fixed_datetime(),
        )

        self.assertEqual(artifact["$schema"], WIFI_DIRECT_LIFECYCLE_SCHEMA)
        self.assertEqual(artifact["probe_id"], "QCL-041")
        self.assertEqual(artifact["peer_class"], "windows")
        self.assertEqual(artifact["evidence_tier"], "template")
        self.assertFalse(artifact["live_evidence"])
        self.assertTrue(artifact["contract"]["non_promoting_template"])
        self.assertEqual(artifact["lease"]["manager"], "Agent Board")
        self.assertEqual(artifact["lease"]["resource"], "quest:<quest-serial>")
        self.assertFalse(artifact["lease"]["reserved_before_live_steps"])
        self.assertFalse(artifact["lease"]["released_after_live_steps"])
        self.assertEqual(artifact["lifecycle"]["peer_discovery"]["peer_count"], 0)
        self.assertIsNone(artifact["lifecycle"]["group_formation"]["local_role"])
        self.assertIsNone(artifact["lifecycle"]["group_formation"]["peer_role"])
        self.assertEqual(artifact["lifecycle"]["socket_exchange"]["protocol"], "tcp")
        self.assertEqual(artifact["lifecycle"]["socket_exchange"]["payload_class"], "bounded_tcp_probe")

    def test_wifi_direct_lifecycle_template_route_normalizes_to_blocked_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            template_path = root / "qcl041-lifecycle-template.json"
            topology_path = root / "qcl041-live-topology.json"

            template_status = run_wifi_direct_lifecycle_template(
                argparse.Namespace(probe_id="QCL-041", out=str(template_path)),
                clock_func=fixed_datetime,
            )
            normalize_status = run_connectivity_probe(
                probe_args(
                    mode="fixture",
                    probe_id="QCL-041",
                    out=str(topology_path),
                    wifi_direct_lifecycle_report=str(template_path),
                ),
                clock_func=fixed_datetime,
            )
            report = json.loads(topology_path.read_text(encoding="utf-8"))
            validation = validate_connectivity_probe_report(report)

        source_check = check(report, "wifi_direct.lifecycle_source")
        self.assertEqual(template_status, 0)
        self.assertEqual(normalize_status, 0)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["promotion"]["allowed"])
        self.assertEqual(source_check["status"], "blocked")
        self.assertIn(
            "hostess.issue.connectivity_probe.wifi_direct_lifecycle_not_live",
            source_check["issue_codes"],
        )
        self.assertEqual(validation["status"], "pass")

    def test_wifi_direct_lifecycle_plan_lists_required_chain(self) -> None:
        report = wifi_direct_lifecycle_plan(
            argparse.Namespace(
                probe_id="QCL-041",
                plan_id="",
                adb=r"S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe",
                serial="<quest-serial>",
                preflight_report_out="",
                template_out="",
                lifecycle_report="",
                topology_report_out="",
                out="unused.json",
                fail_on_error=False,
            ),
            observed_at=fixed_datetime(),
        )

        actions = {command["action_id"]: command for command in report["commands"]}
        collect = actions["collect_qcl041_wifi_direct_lifecycle_source"]
        normalize = actions["normalize_qcl041_wifi_direct_lifecycle_report"]
        self.assertEqual(report["schema"], WIFI_DIRECT_LIFECYCLE_PLAN_SCHEMA)
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["probe_id"], "QCL-041")
        self.assertFalse(report["readiness"]["ready_for_topology_promotion"])
        self.assertFalse(report["policy"]["mutates_wifi_direct_state"])
        self.assertIn("reserve_quest_lease_for_wifi_direct_lifecycle", actions)
        self.assertIn("run_qcl041_live_wifi_direct_preflight", actions)
        self.assertIn("write_qcl041_wifi_direct_lifecycle_template", actions)
        self.assertFalse(collect["available_now"])
        self.assertTrue(collect["requires_quest_lease"])
        self.assertTrue(normalize["clears_gate_when_accepted"])
        self.assertIn("adb-server:lifecycle only for disruptive", report["policy"]["adb_server_lifecycle_policy"])
        self.assertTrue(
            any(
                issue["issue_code"]
                == "hostess.issue.connectivity_probe.wifi_direct_lifecycle_source_missing"
                for issue in report["issues"]
            )
        )

    def test_wifi_direct_lifecycle_plan_is_ready_when_live_source_artifact_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "qcl041-lifecycle.json"
            lifecycle_path.write_text(
                json.dumps(wifi_direct_lifecycle_artifact(probe_id="QCL-041")),
                encoding="utf-8",
            )
            report = wifi_direct_lifecycle_plan(
                argparse.Namespace(
                    probe_id="QCL-041",
                    plan_id="",
                    adb=r"S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe",
                    serial="<quest-serial>",
                    preflight_report_out="",
                    template_out="",
                    lifecycle_report=str(lifecycle_path),
                    topology_report_out="",
                    out="unused.json",
                    fail_on_error=False,
                ),
                observed_at=fixed_datetime(),
            )

        dependency = report["dependencies"][0]
        self.assertTrue(dependency["ready"])
        self.assertTrue(report["readiness"]["ready_for_normalization"])
        self.assertTrue(report["readiness"]["ready_for_topology_promotion"])
        self.assertEqual(report["issues"], [])
        self.assertEqual(dependency["summary"]["topology_status"], "pass")
        self.assertTrue(dependency["summary"]["promotion_allowed"])
        self.assertIn("Normalize the supplied live lifecycle artifact", report["next_step"])

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

    def test_live_udp_freshness_report_generates_run_id_before_makepad_sender_setup(self) -> None:
        report = live_udp_freshness_report(
            probe_args(
                mode="live",
                probe_id="QCL-080",
                host_ip="127.0.0.1",
                udp_sender_source="makepad-runtime",
                udp_bind_host="127.0.0.1",
                udp_port=0,
                udp_packet_count=4,
                udp_interval_ms=1.0,
                udp_timeout_seconds=1.0,
                udp_max_loss_percent=0.0,
            ),
            run_captured_func=FakeRunner(protocol="UDP", listener_port=DEFAULT_QCL080_UDP_PORT),
            run_timeout_func=MakepadRuntimeUdpCommandRunner(),
            clock_func=fixed_datetime,
            host_ipv4_func=lambda: [{"ip": "127.0.0.1", "prefix_length": 8, "interface": "loopback"}],
        )
        runtime_sender = check(report, "runtime.qcl080_udp_sender")
        runtime_marker = runtime_sender["observed"]
        udp_observed = check(report, "protocol.udp_freshness")["observed"]

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["run_id"])
        self.assertTrue(str(report["run_id"]).endswith("-qcl-080"))
        self.assertEqual(runtime_marker["fields"]["runId"], report["run_id"])
        self.assertEqual(
            udp_observed["runtime_properties"]["debug.rustyquest.makepad.qcl080.udp.run.id"],
            report["run_id"],
        )

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
        topology_source = (
            REPO_ROOT / "tools" / "hostessctl" / "connectivity_topology.py"
        ).read_text(encoding="utf-8")
        topology_live_source = (
            REPO_ROOT / "tools" / "hostessctl" / "connectivity_topology_live.py"
        ).read_text(encoding="utf-8")
        common_source = (
            REPO_ROOT / "tools" / "hostessctl" / "connectivity_probe_common.py"
        ).read_text(encoding="utf-8")
        lan_source = (REPO_ROOT / "tools" / "hostessctl" / "connectivity_lan.py").read_text(
            encoding="utf-8"
        )
        udp_source = (REPO_ROOT / "tools" / "hostessctl" / "connectivity_udp.py").read_text(
            encoding="utf-8"
        )
        websocket_source = (
            REPO_ROOT / "tools" / "hostessctl" / "connectivity_websocket.py"
        ).read_text(encoding="utf-8")

        self.assertIn("from tools.hostessctl.connectivity_bluetooth import", probe_source)
        self.assertIn("from tools.hostessctl.connectivity_data_protocols import", probe_source)
        self.assertIn("from tools.hostessctl.connectivity_probe_common import", probe_source)
        self.assertIn("from tools.hostessctl.connectivity_topology import", probe_source)
        self.assertIn("from tools.hostessctl.connectivity_topology_live import", probe_source)
        self.assertIn("from tools.hostessctl.connectivity_udp import", probe_source)
        self.assertIn("from tools.hostessctl.connectivity_websocket import", probe_source)
        facade_defs = re.findall(r"^def ([A-Za-z_][A-Za-z0-9_]*)\(", probe_source, re.MULTILINE)
        self.assertEqual(facade_defs, ["run_connectivity_probe", "utc_now"])
        self.assertNotIn("def live_udp_freshness_report", probe_source)
        self.assertNotIn("def live_lsl_report", probe_source)
        self.assertNotIn("def live_osc_report", probe_source)
        self.assertNotIn("def live_zeromq_report", probe_source)
        self.assertNotIn("def live_bluetooth_report", probe_source)
        self.assertNotIn("def live_websocket_report", probe_source)
        self.assertNotIn("def live_same_wifi_report", probe_source)
        self.assertNotIn("def live_direct_wifi_topology_report", probe_source)
        self.assertNotIn("def device_to_host_udp_freshness", probe_source)
        self.assertNotIn("def collect_device_identity", probe_source)
        self.assertNotIn("def qcl020_wifi_adb_body", probe_source)
        self.assertNotIn("def lsl_discovery_sample_continuity", probe_source)
        self.assertNotIn("def osc_loopback_probe", probe_source)
        self.assertNotIn("def run_qcl050_android_rfcomm_probe", probe_source)
        self.assertNotIn("def zeromq_loopback_probe", probe_source)
        self.assertIn("def run_qcl050_android_rfcomm_probe", bluetooth_source)
        self.assertIn("def live_bluetooth_report", bluetooth_source)
        self.assertIn("def qcl020_wifi_adb_body", topology_source)
        self.assertIn("def live_direct_wifi_topology_report", topology_live_source)
        self.assertIn("def live_lsl_report", protocol_source)
        self.assertIn("def live_osc_report", protocol_source)
        self.assertIn("def live_zeromq_report", protocol_source)
        self.assertIn("def lsl_discovery_sample_continuity", protocol_source)
        self.assertIn("def osc_loopback_probe", protocol_source)
        self.assertIn("def zeromq_loopback_probe", protocol_source)
        self.assertIn("def check_row", common_source)
        self.assertIn("def live_same_wifi_report", lan_source)
        self.assertIn("def collect_device_identity", lan_source)
        self.assertIn("def live_udp_freshness_report", udp_source)
        self.assertIn("def device_to_host_udp_freshness", udp_source)
        self.assertIn("def live_websocket_report", websocket_source)
        self.assertIn("def websocket_loopback_probe", websocket_source)

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
