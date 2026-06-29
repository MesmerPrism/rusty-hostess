from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.device_link_report import (
    QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_SCHEMA,
    QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA,
    build_install_test_suite_descriptor,
    build_stream_capability_descriptor_from_connectivity_probe,
    run_install_test_suite_descriptor,
    run_stream_capability_descriptor,
    validate_install_test_suite_descriptor,
    validate_stream_capability_descriptor,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class HostessCtlDeviceLinkReportTests(unittest.TestCase):
    def test_qcl080_app_owned_report_promotes_measured_udp_capability_with_caveat(self) -> None:
        report = qcl080_app_owned_fixture()
        report["promotion"]["allowed"] = True
        report["status"] = "warn"
        report["issues"] = [
            {
                "issue_code": "hostess.issue.connectivity_probe.windows_network_profile_public",
                "severity": "warning",
                "message": "active Windows network/firewall profile can block Quest-to-PC LAN listeners",
            }
        ]

        descriptor = build_stream_capability_descriptor_from_connectivity_probe(report)
        validation = validate_stream_capability_descriptor(descriptor)

        self.assertEqual(descriptor["$schema"], QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA)
        self.assertEqual(descriptor["status"], "usable_with_warnings")
        self.assertEqual(descriptor["transport_kind"], "udp")
        self.assertEqual(
            descriptor["transport_evidence"]["endpoint_source"],
            "app_owned_runtime_udp_sender",
        )
        self.assertEqual(descriptor["runtime_evidence"]["sender_source"], "makepad-runtime")
        self.assertEqual(descriptor["runtime_evidence"]["socket_owner"], "app-owned")
        self.assertEqual(descriptor["measurements"]["udp_packets_received"], 12)
        self.assertEqual(descriptor["timing"]["rtt_strategy"], "host_arrival_sequence_only")
        self.assertFalse(descriptor["timing"]["rtt_supported"])
        self.assertTrue(
            any(
                row["condition_id"] == "condition.qcl080.product_host_firewall_rule"
                for row in descriptor["required_conditions"]
            )
        )
        self.assertEqual(descriptor["test_slots"][0]["probe_id"], "QCL-080")
        self.assertEqual(descriptor["source_probe"]["promotion_allowed"], True)
        self.assertEqual(requirement(descriptor, "product_host_firewall_rule")["status"], "missing")
        self.assertTrue(
            any(
                warning["issue_code"]
                == "hostess.issue.device_link.stream_capability.product_firewall_rule_missing"
                for warning in descriptor["warnings"]
            )
        )
        self.assertEqual(validation["status"], "pass")
        self.assertIn("product_host_firewall_rule", " ".join(validation["warnings"]))

    def test_qcl080_fixture_without_live_promotion_stays_candidate(self) -> None:
        descriptor = build_stream_capability_descriptor_from_connectivity_probe(qcl080_app_owned_fixture())
        validation = validate_stream_capability_descriptor(descriptor)

        self.assertEqual(descriptor["status"], "candidate")
        self.assertEqual(requirement(descriptor, "qcl080_live_promotion")["status"], "missing")
        self.assertEqual(validation["status"], "pass")

    def test_qcl080_product_wpf_firewall_rule_satisfies_requirement(self) -> None:
        report = qcl080_app_owned_fixture()
        report["promotion"]["allowed"] = True
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

        descriptor = build_stream_capability_descriptor_from_connectivity_probe(report)
        validation = validate_stream_capability_descriptor(descriptor)

        self.assertEqual(requirement(descriptor, "product_host_firewall_rule")["status"], "satisfied")
        self.assertFalse(
            any(
                warning["issue_code"]
                == "hostess.issue.device_link.stream_capability.product_firewall_rule_missing"
                for warning in descriptor["warnings"]
            )
        )
        self.assertEqual(validation["status"], "pass")

    def test_qcl080_adb_shell_udp_generator_is_not_app_owned_capability(self) -> None:
        report = read_json(
            REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-080-udp-freshness-pass.json"
        )

        descriptor = build_stream_capability_descriptor_from_connectivity_probe(report)
        validation = validate_stream_capability_descriptor(descriptor)

        self.assertEqual(descriptor["status"], "rejected")
        self.assertEqual(
            descriptor["transport_evidence"]["endpoint_source"],
            "adb_shell_udp_generator",
        )
        self.assertEqual(requirement(descriptor, "app_owned_runtime_sender")["status"], "missing")
        self.assertEqual(validation["status"], "pass")

    def test_qcl083_quest_runtime_report_promotes_measured_osc_capability(self) -> None:
        descriptor = build_stream_capability_descriptor_from_connectivity_probe(
            qcl083_quest_runtime_fixture()
        )
        validation = validate_stream_capability_descriptor(descriptor)

        self.assertEqual(descriptor["$schema"], QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA)
        self.assertEqual(descriptor["status"], "usable")
        self.assertEqual(descriptor["transport_kind"], "osc_udp")
        self.assertEqual(descriptor["payload_plane"], "osc_message")
        self.assertEqual(descriptor["timing"]["rtt_strategy"], "native_round_trip_ack")
        self.assertTrue(descriptor["timing"]["rtt_supported"])
        self.assertEqual(
            descriptor["transport_evidence"]["endpoint_source"],
            "quest-runtime",
        )
        self.assertEqual(
            descriptor["runtime_evidence"]["endpoint_source"],
            "app_owned_android_osc_server",
        )
        self.assertEqual(
            descriptor["runtime_evidence"]["android_authority"],
            "app_owned_runtime_osc_udp_server",
        )
        self.assertEqual(descriptor["measurements"]["osc_messages_received"], 16)
        self.assertEqual(descriptor["measurements"]["osc_loss_percent"], 0.0)
        self.assertEqual(requirement(descriptor, "qcl083_live_promotion")["status"], "satisfied")
        self.assertTrue(
            any(
                row["condition_id"] == "condition.qcl083.quest_runtime_endpoint"
                for row in descriptor["required_conditions"]
            )
        )
        self.assertEqual(descriptor["test_slots"][0]["probe_id"], "QCL-083")
        self.assertEqual(validation["status"], "pass")

    def test_stream_capability_cli_writes_descriptor_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "qcl080.json"
            out = root / "qcl080.stream-capability.json"
            source.write_text(json.dumps(qcl080_app_owned_fixture()), encoding="utf-8")

            status = run_stream_capability_descriptor(
                argparse.Namespace(
                    input=str(source),
                    out=str(out),
                    validation_out=None,
                    fail_on_error=True,
                )
            )
            descriptor = read_json(out)
            validation = read_json(out.with_name("qcl080.stream-capability.validation-report.json"))

        self.assertEqual(status, 0)
        self.assertEqual(descriptor["$schema"], QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA)
        self.assertEqual(descriptor["source_probe"]["artifact_path"], str(source))
        self.assertTrue(descriptor["source_probe"]["artifact_sha256"])
        self.assertEqual(validation["status"], "pass")

    def test_stream_capability_cli_writes_qcl083_descriptor_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "qcl083.json"
            out = root / "qcl083.stream-capability.json"
            source.write_text(json.dumps(qcl083_quest_runtime_fixture()), encoding="utf-8")

            status = run_stream_capability_descriptor(
                argparse.Namespace(
                    input=str(source),
                    out=str(out),
                    validation_out=None,
                    fail_on_error=True,
                )
            )
            descriptor = read_json(out)
            validation = read_json(out.with_name("qcl083.stream-capability.validation-report.json"))

        self.assertEqual(status, 0)
        self.assertEqual(descriptor["transport_kind"], "osc_udp")
        self.assertEqual(descriptor["status"], "usable")
        self.assertEqual(descriptor["source_probe"]["artifact_path"], str(source))
        self.assertTrue(descriptor["source_probe"]["artifact_sha256"])
        self.assertEqual(validation["status"], "pass")

    def test_parser_accepts_connectivity_probe_stream_capability(self) -> None:
        args = build_parser().parse_args(
            [
                "connectivity-probe",
                "stream-capability",
                "--input",
                "target/qcl080.json",
                "--out",
                "target/qcl080.stream-capability.json",
                "--fail-on-error",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "stream-capability")
        self.assertEqual(args.input, "target/qcl080.json")
        self.assertEqual(args.out, "target/qcl080.stream-capability.json")
        self.assertTrue(args.fail_on_error)

    def test_install_test_suite_descriptor_covers_environment_and_protocols(self) -> None:
        descriptor = build_install_test_suite_descriptor(
            suite_id="downloadable-suite",
            observed_at_utc="2026-06-28T00:00:00Z",
        )
        validation = validate_install_test_suite_descriptor(descriptor)

        self.assertEqual(descriptor["$schema"], QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_SCHEMA)
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(descriptor["suite_id"], "downloadable-suite")
        self.assertTrue(
            {"host", "toolchain", "network", "firewall", "device", "protocol", "timing"}.issubset(
                {row["category"] for row in descriptor["environment_checks"]}
            )
        )
        self.assertTrue(
            {
                "manifold_websocket",
                "udp",
                "lsl",
                "osc_udp",
                "zeromq",
                "bluetooth_rfcomm",
                "bluetooth_gatt",
                "tcp_binary",
            }.issubset({row["transport_kind"] for row in descriptor["protocol_capabilities"]})
        )
        self.assertTrue(
            {
                "QCL-000",
                "QCL-010",
                "QCL-011",
                "QCL-050",
                "QCL-051",
                "QCL-080",
                "QCL-081",
                "QCL-083",
                "QCL-084",
            }.issubset({row["probe_id"] for row in descriptor["test_slots"]})
        )
        for capability in descriptor["protocol_capabilities"]:
            self.assertTrue(capability["required_conditions"])
            self.assertTrue(capability["timing"]["rtt_strategy"])

    def test_install_test_suite_cli_writes_descriptor_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "device-link-test-suite.json"

            status = run_install_test_suite_descriptor(
                argparse.Namespace(
                    out=str(out),
                    validation_out=None,
                    suite_id="local-downloadable-suite",
                    fail_on_error=True,
                )
            )
            descriptor = read_json(out)
            validation = read_json(out.with_name("device-link-test-suite.validation-report.json"))

        self.assertEqual(status, 0)
        self.assertEqual(descriptor["suite_id"], "local-downloadable-suite")
        self.assertEqual(validation["status"], "pass")

    def test_parser_accepts_connectivity_probe_test_suite(self) -> None:
        args = build_parser().parse_args(
            [
                "connectivity-probe",
                "test-suite",
                "--out",
                "target/device-link-test-suite.json",
                "--suite-id",
                "install-suite",
                "--fail-on-error",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "test-suite")
        self.assertEqual(args.out, "target/device-link-test-suite.json")
        self.assertEqual(args.suite_id, "install-suite")
        self.assertTrue(args.fail_on_error)


def qcl080_app_owned_fixture() -> dict[str, Any]:
    return read_json(
        REPO_ROOT
        / "fixtures"
        / "connectivity-probe"
        / "qcl-080-app-owned-udp-freshness-pass.json"
    )


def qcl083_quest_runtime_fixture() -> dict[str, Any]:
    report = read_json(
        REPO_ROOT / "fixtures" / "connectivity-probe" / "qcl-083-osc-loopback-pass.json"
    )
    report["run_id"] = "qcl083-quest-runtime"
    report["status"] = "pass"
    report["device"] = {
        "adb_state": "device",
        "model": "Quest 3S",
        "serial_redacted": False,
        "wifi_ipv4": "192.168.2.56",
        "wifi_prefix_length": 24,
    }
    report["topology"]["endpoint_direction"] = "host_to_quest_runtime_with_ack"
    report["transport"]["endpoint_source"] = "quest-runtime"
    report["transport"]["local_endpoint"] = "192.168.2.54"
    report["transport"]["remote_endpoint"] = "192.168.2.56"
    report["promotion"] = {
        "allowed": True,
        "target": "quest.device_link OSC control/telemetry capability descriptor",
        "reason": "QCL-083 proves Quest/runtime-owned OSC payload exchange",
    }
    report["measurements"].update(
        {
            "osc_quest_processing_ms_p95": 0.3,
            "osc_estimated_one_way_ms_p95": 7.1,
            "osc_clock_offset_estimate_ms_median": -12.5,
            "osc_clock_offset_jitter_ms_p95": 1.2,
        }
    )
    report["osc_payload_probe"] = {
        "status": "pass",
        "source": "quest-runtime",
        "endpoint_source": "app_owned_android_osc_server",
        "address": "/rusty/qcl083",
        "device_endpoint": "192.168.2.56:18783",
        "messages_requested": 16,
        "messages_acknowledged": 16,
        "loss_percent": 0.0,
        "round_trip_ms_p95": 8,
        "android": {
            "remote_evidence": "/sdcard/Android/data/io.github.mesmerprism.rustyhostess.t/files/hostess-t/evidence/qcl083-osc/latest.json",
            "evidence_available": True,
            "evidence": {
                "status": "pass",
                "authority": "app_owned_runtime_osc_udp_server",
                "messages_received": 16,
                "messages_acknowledged": 16,
                "osc_server": {"socket_opened": True, "socket_closed": True},
            },
        },
    }
    return report


def requirement(descriptor: dict[str, Any], suffix: str) -> dict[str, Any]:
    for row in descriptor["requirements"]:
        if str(row["requirement_id"]).endswith(suffix):
            return row
    raise AssertionError(f"missing requirement ending with {suffix}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    return build_hostessctl_parser(
        broker_package="broker",
        broker_port=8765,
        broker_local_forward_port=18765,
        makepad_android_package="makepad",
        makepad_android_xr_activity="makepad/.Xr",
        makepad_provider_package="makepad",
        makepad_provider_activity="makepad/.Xr",
    )


if __name__ == "__main__":
    unittest.main()
