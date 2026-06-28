from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.connectivity_suite import (
    CONNECTIVITY_SUITE_RUN_SCHEMA,
    build_connectivity_suite_run_report,
    run_connectivity_suite,
    validate_connectivity_suite_run_report,
)


class HostessCtlConnectivitySuiteTests(unittest.TestCase):
    def test_fixture_suite_runs_all_slots_and_groups_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "suite-run.json"
            report = build_connectivity_suite_run_report(
                suite_args(out),
                run_captured_func=SnapshotRunner(),
                clock_func=lambda: "2026-06-28T00:00:00Z",
            )
            validation = validate_connectivity_suite_run_report(report)

        self.assertEqual(report["$schema"], CONNECTIVITY_SUITE_RUN_SCHEMA)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(len(report["slot_results"]), 9)
        self.assertEqual(
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
            },
            {row["probe_id"] for row in report["slot_results"]},
        )
        self.assertTrue(
            any(row["phase"] == "protocol" for row in report["grouped_results"])
        )
        qcl080 = slot(report, "QCL-080")
        self.assertEqual(qcl080["status"], "pass")
        self.assertTrue(qcl080["descriptor_path"])
        self.assertEqual(qcl080["descriptor_status"], "candidate")
        self.assertEqual(
            report["environment_snapshot"]["network"]["ipv4_candidates"][0]["ip"],
            "192.0.2.10",
        )

    def test_run_connectivity_suite_writes_report_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "suite-run.json"
            status = run_connectivity_suite(
                suite_args(out),
                run_captured_func=SnapshotRunner(),
                clock_func=lambda: "2026-06-28T00:00:00Z",
            )
            report = read_json(out)
            validation = read_json(out.with_name("suite-run.validation-report.json"))

        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["slot_count"], 9)

    def test_public_profile_single_connection_object_keeps_suite_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "suite-run.json"
            report = build_connectivity_suite_run_report(
                suite_args(out),
                run_captured_func=PublicProfileSnapshotRunner(),
                clock_func=lambda: "2026-06-28T00:00:00Z",
            )

        self.assertEqual(report["status"], "warn")
        self.assertEqual(report["summary"]["pass_count"], 9)
        self.assertEqual(
            report["environment_snapshot"]["network"]["windows_profile"]["connections"][
                "NetworkCategory"
            ],
            "Public",
        )

    def test_parser_accepts_connectivity_probe_run_suite(self) -> None:
        args = build_parser().parse_args(
            [
                "connectivity-probe",
                "run-suite",
                "--mode",
                "fixture",
                "--probe-id",
                "QCL-080",
                "--out",
                "target/connectivity-probe/suite-run.json",
                "--suite-id",
                "installer-smoke",
                "--listener-program",
                "HostessCompanion.Wpf.exe",
                "--listener-port",
                "18767",
                "--fail-on-error",
            ]
        )

        self.assertEqual(args.command, "connectivity-probe")
        self.assertEqual(args.connectivity_probe_command, "run-suite")
        self.assertEqual(args.mode, "fixture")
        self.assertEqual(args.probe_id, ["QCL-080"])
        self.assertEqual(args.suite_id, "installer-smoke")
        self.assertEqual(args.listener_program, "HostessCompanion.Wpf.exe")
        self.assertTrue(args.fail_on_error)


class SnapshotRunner:
    def __call__(
        self,
        command: list[str],
        *,
        allow_failure: bool = False,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        text = " ".join(command)
        if "Get-NetIPAddress" in text:
            return completed(
                [
                    {
                        "InterfaceAlias": "Wi-Fi",
                        "IPAddress": "192.0.2.10",
                        "PrefixLength": 24,
                    }
                ]
            )
        if "Get-NetConnectionProfile" in text:
            return completed(
                {
                    "connections": [
                        {
                            "InterfaceAlias": "Wi-Fi",
                            "Name": "Lab",
                            "NetworkCategory": "Private",
                            "IPv4Connectivity": "Internet",
                            "IPv6Connectivity": "NoTraffic",
                        }
                    ],
                    "firewall": [
                        {
                            "Name": "Private",
                            "Enabled": True,
                            "DefaultInboundAction": "Block",
                            "DefaultOutboundAction": "Allow",
                            "AllowInboundRules": "True",
                        }
                    ],
                    "listener_firewall": {
                        "program": "HostessCompanion.Wpf.exe",
                        "protocol": "UDP",
                        "port": 18767,
                        "active_profiles": ["Private"],
                        "matching_rule_count": 1,
                        "allowed_on_active_profile": True,
                    },
                }
            )
        if "NetworkOperatorTetheringManager" in text:
            return completed(
                {
                    "available": True,
                    "state": "Off",
                    "source_profile": "Lab",
                    "client_count": 0,
                    "max_client_count": 8,
                    "ssid": "RustyHostess-QCL011",
                    "passphrase_set": True,
                    "band": "Auto",
                }
            )
        if "Get-PnpDevice -Class Bluetooth" in text:
            return completed(
                {
                    "available": True,
                    "adapter_status": "OK",
                    "adapter_name": "fixture Bluetooth Adapter",
                    "bthserv_status": "Running",
                    "user_service_running": True,
                    "service_count": 2,
                    "address_redacted": True,
                }
            )
        return completed({})


class PublicProfileSnapshotRunner(SnapshotRunner):
    def __call__(
        self,
        command: list[str],
        *,
        allow_failure: bool = False,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        text = " ".join(command)
        if "Get-NetConnectionProfile" in text:
            return completed(
                {
                    "connections": {
                        "InterfaceAlias": "Wi-Fi",
                        "Name": "Lab",
                        "NetworkCategory": "Public",
                        "IPv4Connectivity": "Internet",
                        "IPv6Connectivity": "Internet",
                    },
                    "firewall": [],
                }
            )
        return super().__call__(command, allow_failure=allow_failure, cwd=cwd)


def completed(value: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(value),
        stderr="",
    )


def suite_args(out: Path) -> argparse.Namespace:
    return argparse.Namespace(
        out=str(out),
        validation_out=None,
        suite_out=None,
        artifact_dir=None,
        suite_id="installer-smoke",
        run_id="suite-fixture",
        mode="fixture",
        probe_id=None,
        skip_host_snapshot=False,
        listener_program="HostessCompanion.Wpf.exe",
        listener_protocol="UDP",
        listener_port=18767,
        listener_bind_host="0.0.0.0",
        fail_on_error=True,
    )


def slot(report: dict[str, Any], probe_id: str) -> dict[str, Any]:
    for row in report["slot_results"]:
        if row["probe_id"] == probe_id:
            return row
    raise AssertionError(f"missing slot for {probe_id}")


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
