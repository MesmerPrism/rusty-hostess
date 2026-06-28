from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.hostessctl import hostessctl
from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.companion_readiness import (
    HOSTESS_COMPANION_READINESS_SCHEMA,
    HOSTESS_COMPANION_READINESS_VALIDATION_SCHEMA,
    build_companion_readiness_report,
    validate_companion_readiness_report,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "companion-readiness"
DAMAGED_ROOT = REPO_ROOT / "fixtures" / "damaged"


class HostessCtlCompanionReadinessTests(unittest.TestCase):
    def test_basic_readiness_report_accepts_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            args = readiness_args(
                out=str(Path(tmpdir) / "readiness.json"),
                descriptor=str(FIXTURE_ROOT / "readiness-module-descriptor.json"),
            )

            report = build_companion_readiness_report(
                args,
                run_captured_func=FakeAdbRunner(),
                clock_ms_func=FixedClock(),
                which_func=lambda name: None,
                broker_probe_func=lambda host, port, timeout: False,
            )
            validation = validate_companion_readiness_report(report)

        self.assertEqual(report["$schema"], HOSTESS_COMPANION_READINESS_SCHEMA)
        self.assertEqual(report["profile"], "basic")
        self.assertEqual(validation["status"], "pass")
        self.assertTrue(
            any(
                check["check_id"] == "check.descriptor.companion_module"
                and check["status"] == "pass"
                for check in report["checks"]
            )
        )

    def test_hostess_makepad_quest_profile_passes_with_fake_tools_and_device(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_root = Path(tmpdir) / "tools"
            adb = touch(tool_root / "adb.exe")
            cargo = touch(tool_root / "cargo.exe")
            cargo_makepad = touch(tool_root / "cargo-makepad.exe")
            android_sdk = tool_root / "android-sdk"
            android_sdk.mkdir()
            jdk_home = tool_root / "jdk"
            (jdk_home / "bin").mkdir(parents=True)
            touch(jdk_home / "bin" / "java.exe")
            args = readiness_args(
                out=str(Path(tmpdir) / "readiness.json"),
                profile="hostess-makepad-quest",
                adb=str(adb),
                serial="TEST_SERIAL",
                android_sdk=str(android_sdk),
                jdk_home=str(jdk_home),
                cargo=str(cargo),
                cargo_makepad=str(cargo_makepad),
                check_broker=True,
            )

            report = build_companion_readiness_report(
                args,
                run_captured_func=FakeAdbRunner(),
                clock_ms_func=FixedClock(),
                which_func=lambda name: None,
                broker_probe_func=lambda host, port, timeout: True,
            )
            validation = validate_companion_readiness_report(report)

        self.assertEqual(report["status"], "pass")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["blocking_failures"], [])
        self.assertTrue(
            any(
                check["check_id"] == "check.runtime.makepad_run_as"
                and check["status"] == "pass"
                for check in report["checks"]
            )
        )
        self.assertTrue(
            any(
                check["check_id"] == "check.runtime.manifold_broker_process"
                and check["status"] == "pass"
                for check in report["checks"]
            )
        )
        self.assertTrue(
            any(
                check["check_id"] == "check.network.broker_adb_forward"
                and check["status"] == "pass"
                for check in report["checks"]
            )
        )
        self.assertTrue(
            any(
                check["check_id"] == "check.network.broker_forwarded_port"
                and check["status"] == "pass"
                for check in report["checks"]
            )
        )
        raw_broker_port = check_with_id(report, "check.network.broker_port")
        self.assertEqual(raw_broker_port["status"], "skipped")
        self.assertEqual(raw_broker_port["observed"]["transport"], "adb-forward")

    def test_required_broker_reports_blocking_runtime_and_forward_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_root = Path(tmpdir) / "tools"
            adb = touch(tool_root / "adb.exe")
            cargo = touch(tool_root / "cargo.exe")
            cargo_makepad = touch(tool_root / "cargo-makepad.exe")
            android_sdk = tool_root / "android-sdk"
            android_sdk.mkdir()
            jdk_home = tool_root / "jdk"
            (jdk_home / "bin").mkdir(parents=True)
            touch(jdk_home / "bin" / "java.exe")
            args = readiness_args(
                out=str(Path(tmpdir) / "readiness.json"),
                profile="hostess-makepad-quest",
                adb=str(adb),
                serial="TEST_SERIAL",
                android_sdk=str(android_sdk),
                jdk_home=str(jdk_home),
                cargo=str(cargo),
                cargo_makepad=str(cargo_makepad),
                check_broker=True,
                require_broker=True,
            )

            report = build_companion_readiness_report(
                args,
                run_captured_func=FakeAdbRunner(broker_running=False, broker_forwarded=False),
                clock_ms_func=FixedClock(),
                which_func=lambda name: None,
                broker_probe_func=lambda host, port, timeout: False,
            )
            validation = validate_companion_readiness_report(report)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(validation["status"], "fail")
        self.assertIn("check.runtime.manifold_broker_process", validation["blocking_failures"])
        self.assertIn("check.network.broker_adb_forward", validation["blocking_failures"])
        self.assertIn("check.network.broker_forwarded_port", validation["blocking_failures"])

    def test_required_adb_missing_can_return_blocking_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "readiness.json"
            status = hostessctl.dispatch_command(
                readiness_args(
                    out=str(out),
                    adb=str(Path(tmpdir) / "missing-adb.exe"),
                    android_sdk=str(Path(tmpdir) / "missing-sdk"),
                    require_adb=True,
                    fail_on_blocking=True,
                ),
            )
            report = read_json(out)
            validation = read_json(out.with_name("readiness.validation-report.json"))

        self.assertEqual(status, 2)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(validation["$schema"], HOSTESS_COMPANION_READINESS_VALIDATION_SCHEMA)
        self.assertIn("check.tool.adb", validation["blocking_failures"])

    def test_damaged_report_without_checks_is_rejected(self) -> None:
        report = read_json(DAMAGED_ROOT / "hostess-companion-readiness-report-missing-checks.json")
        validation = validate_companion_readiness_report(report)

        self.assertEqual(validation["status"], "fail")
        self.assertTrue(any("must contain checks" in error for error in validation["errors"]))

    def test_parser_accepts_companion_readiness_command(self) -> None:
        args = build_parser().parse_args(
            [
                "companion-readiness",
                "--profile",
                "hostess-makepad-quest",
                "--out",
                "readiness.json",
                "--serial",
                "TEST_SERIAL",
                "--broker-local-port",
                "28765",
                "--broker-package",
                "test.broker",
                "--broker-activity",
                "test.broker/.BrokerStartActivity",
                "--require-device",
                "--fail-on-blocking",
            ]
        )

        self.assertEqual(args.command, "companion-readiness")
        self.assertEqual(args.profile, "hostess-makepad-quest")
        self.assertEqual(args.serial, "TEST_SERIAL")
        self.assertEqual(args.broker_local_port, 28765)
        self.assertEqual(args.broker_package, "test.broker")
        self.assertEqual(args.broker_activity, "test.broker/.BrokerStartActivity")
        self.assertTrue(args.require_device)
        self.assertTrue(args.fail_on_blocking)


class FakeAdbRunner:
    def __init__(self, *, broker_running: bool = True, broker_forwarded: bool = True) -> None:
        self.broker_running = broker_running
        self.broker_forwarded = broker_forwarded

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
        if "pm path" in text:
            return subprocess.CompletedProcess(command, 0, "package:/data/app/base.apk\n", "")
        if "pidof" in text:
            if self.broker_running:
                return subprocess.CompletedProcess(command, 0, "12345\n", "")
            return subprocess.CompletedProcess(command, 1, "", "")
        if "forward --list" in text:
            if self.broker_forwarded:
                return subprocess.CompletedProcess(command, 0, "TEST_SERIAL tcp:18765 tcp:8765\n", "")
            return subprocess.CompletedProcess(command, 0, "", "")
        if "run-as" in text and "pwd" in text:
            return subprocess.CompletedProcess(command, 0, "/data/user/0/test\n", "")
        if "resolve-activity" in text:
            return subprocess.CompletedProcess(command, 0, "io.github.test/.MakepadAppXr\n", "")
        return subprocess.CompletedProcess(command, 1, "", "unexpected command")


class FixedClock:
    def __init__(self) -> None:
        self.value = 1782320000000

    def __call__(self) -> int:
        self.value += 1
        return self.value


def readiness_args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "command": "companion-readiness",
        "out": "readiness.json",
        "validation_out": None,
        "profile": "basic",
        "descriptor": None,
        "adb": None,
        "serial": None,
        "android_sdk": None,
        "jdk_home": None,
        "cargo": "cargo",
        "cargo_makepad": "cargo-makepad",
        "broker_host": "127.0.0.1",
        "broker_port": 8765,
        "broker_local_port": 18765,
        "broker_package": "io.github.test.broker",
        "broker_activity": "io.github.test.broker/.BrokerStartActivity",
        "check_broker": False,
        "require_broker": False,
        "makepad_package": "io.github.test.makepad",
        "makepad_activity": "io.github.test.makepad/.MakepadAppXr",
        "require_adb": False,
        "require_android_sdk": False,
        "require_jdk": False,
        "require_cargo_makepad": False,
        "require_device": False,
        "require_makepad_package": False,
        "fail_on_blocking": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def check_with_id(report: dict[str, object], check_id: str) -> dict[str, object]:
    checks = report["checks"]
    assert isinstance(checks, list)
    return next(row for row in checks if row["check_id"] == check_id)


def build_parser():
    return build_hostessctl_parser(
        broker_package="test.broker",
        broker_port=18765,
        broker_local_forward_port=28765,
        makepad_android_package="test.makepad",
        makepad_android_xr_activity="test.makepad/.Xr",
        makepad_provider_package="test.provider",
        makepad_provider_activity="test.provider/.Provider",
    )


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
