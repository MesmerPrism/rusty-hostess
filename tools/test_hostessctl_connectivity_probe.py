from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.connectivity_probe import (
    CONNECTIVITY_PROBE_SCHEMA,
    fixture_report,
    live_same_wifi_report,
    run_connectivity_probe,
    validate_connectivity_probe_report,
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
        self.assertEqual(validation["status"], "pass")
        self.assertIn("WebSocket echo", " ".join(validation["warnings"]))

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
        self.assertEqual(report["status"], "warn")
        self.assertEqual(report["device"]["wifi_ipv4"], "192.0.2.42")
        self.assertEqual(report["host"]["selected_ipv4"], "192.0.2.10")
        self.assertEqual(check(report, "topology.same_subnet")["status"], "pass")
        self.assertEqual(check(report, "device_to_host.tcp_echo")["status"], "pass")
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.connectivity_probe.partial_protocol_coverage"
                for issue in report["issues"]
            )
        )

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
            REPO_ROOT / "fixtures" / "damaged" / "connectivity-probe-router-firewall-blocked.json",
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
                "QCL-010",
                "--out",
                "target/qcl010.json",
                "--adb",
                "adb.exe",
                "--serial",
                "serial-1",
                "--host-ip",
                "192.0.2.10",
                "--skip-tcp-echo",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "run")
        self.assertEqual(args.mode, "live")
        self.assertEqual(args.probe_id, "QCL-010")
        self.assertEqual(args.host_ip, "192.0.2.10")
        self.assertTrue(args.skip_tcp_echo)


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


class FakeRunner:
    def __call__(
        self,
        command: list[str],
        *,
        allow_failure: bool = False,
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
        "skip_host_ping": False,
        "skip_device_ping": False,
        "skip_tcp_echo": False,
        "tcp_echo_bind_host": "0.0.0.0",
        "tcp_echo_port": 0,
        "tcp_echo_marker": "rusty-qcl-tcp-echo",
        "tcp_timeout_seconds": 1.0,
        "ping_count": 2,
        "ping_timeout_seconds": 1.0,
        "fail_on_error": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def fixed_datetime() -> datetime:
    return datetime(2026, 6, 28, 13, 0, 0, tzinfo=UTC)


if __name__ == "__main__":
    unittest.main()
