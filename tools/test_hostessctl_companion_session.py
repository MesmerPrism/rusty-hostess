from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.companion_session import (
    HOSTESS_COMPANION_SESSION_SCHEMA,
    build_companion_session_report,
    run_companion_session,
    validate_companion_session_report,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS_DESCRIPTOR = REPO_ROOT / "fixtures" / "companion-readiness" / "readiness-module-descriptor.json"


class HostessCtlCompanionSessionTests(unittest.TestCase):
    def test_session_run_writes_phase_artifacts_for_live_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tools = fake_toolchain(root)
            descriptors = write_descriptor_root(root)
            out = root / "session.json"
            args = session_args(
                out=str(out),
                gui_descriptors_root=str(descriptors),
                **tools,
            )

            status = run_companion_session(
                args,
                run_captured_func=FakeAdbRunner(),
                clock_ms_func=FixedClock(),
                which_func=lambda name: None,
                broker_probe_func=lambda host, port, timeout: True,
                live_execution_func=fake_live_pass,
                sleep_func=lambda seconds: None,
            )
            report = read_json(out)
            validation = read_json(out.with_name("session.validation-report.json"))

        self.assertEqual(status, 0)
        self.assertEqual(report["$schema"], HOSTESS_COMPANION_SESSION_SCHEMA)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(phase(report, "broker_stream_probe")["status"], "pass")
        self.assertEqual(phase(report, "app_private_fallback")["status"], "skipped")
        self.assertTrue(
            any(
                artifact["role"] == "live_broker_stream_execution"
                for artifact in report["artifact_refs"]
            )
        )

    def test_fallback_recovery_reports_warn_session_without_ui_logic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tools = fake_toolchain(root)
            descriptors = write_descriptor_root(root)
            args = session_args(
                out=str(root / "session.json"),
                gui_descriptors_root=str(descriptors),
                **tools,
            )

            report = build_companion_session_report(
                args,
                run_captured_func=FakeAdbRunner(),
                clock_ms_func=FixedClock(),
                which_func=lambda name: None,
                broker_probe_func=lambda host, port, timeout: True,
                broker_client_factory=lambda *args, **kwargs: None,
                socket_probe_func=lambda host, port, timeout: False,
                sleep_func=lambda seconds: None,
                live_execution_func=fake_live_fail,
                fallback_execution_func=fake_fallback_pass,
            )
            validation = validate_companion_session_report(report)

        self.assertEqual(report["status"], "warn")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(phase(report, "broker_stream_probe")["status"], "warn")
        self.assertEqual(phase(report, "app_private_fallback")["status"], "pass")
        self.assertTrue(
            any(
                issue["issue_code"]
                == "hostess.issue.companion_session.recovered_by_app_private_fallback"
                for issue in report["issues"]
            )
        )

    def test_parser_accepts_companion_session_run_command(self) -> None:
        args = build_parser().parse_args(
            [
                "companion-session",
                "run",
                "--out",
                "session.json",
                "--frontend",
                "wpf",
                "--profile",
                "hostess-makepad-quest",
                "--adb",
                "adb.exe",
                "--serial",
                "serial-1",
                "--check-broker",
                "--broker-local-port",
                "28765",
                "--wait-seconds",
                "0.5",
                "--no-fallback",
            ]
        )

        self.assertEqual(args.command, "companion-session")
        self.assertEqual(args.session_command, "run")
        self.assertEqual(args.frontend, "wpf")
        self.assertEqual(args.profile, "hostess-makepad-quest")
        self.assertEqual(args.adb, "adb.exe")
        self.assertEqual(args.serial, "serial-1")
        self.assertEqual(args.broker_local_port, 28765)
        self.assertEqual(args.wait_seconds, 0.5)
        self.assertTrue(args.check_broker)
        self.assertTrue(args.no_fallback)


def fake_live_pass(request: dict[str, Any], *, args: argparse.Namespace) -> dict[str, Any]:
    return fake_execution(
        request,
        schema="rusty.hostess.bridge_command.live_android_execution_evidence.v1",
        route_id=request["route_id"],
        stages=["sent", "transport_ok", "authority_accepted", "runtime_accepted", "applied"],
        setup_actions=[
            {"action": "launch-manifold-broker", "status": "pass", "required": True},
            {"action": "adb-forward-broker", "status": "pass", "required": True},
            {"action": "launch-hostess-makepad", "status": "pass", "required": False},
        ],
    )


def fake_live_fail(request: dict[str, Any], *, args: argparse.Namespace) -> dict[str, Any]:
    return fake_execution(
        request,
        schema="rusty.hostess.bridge_command.live_android_execution_evidence.v1",
        route_id=request["route_id"],
        stages=["sent"],
        setup_actions=[
            {"action": "launch-manifold-broker", "status": "pass", "required": True},
            {"action": "wait-broker-forwarded-socket", "status": "fail", "required": True},
        ],
        status="fail",
        issue_code="hostess.issue.bridge_command.live_android.broker_socket_closed",
    )


def fake_fallback_pass(request: dict[str, Any], *, args: argparse.Namespace) -> dict[str, Any]:
    return fake_execution(
        request,
        schema="rusty.hostess.bridge_command.android_execution_evidence.v1",
        route_id="bridge_route.command.android_app_private.applied",
        stages=["sent", "transport_ok", "runtime_accepted", "applied"],
    )


def fake_execution(
    request: dict[str, Any],
    *,
    schema: str,
    route_id: str,
    stages: list[str],
    setup_actions: list[dict[str, Any]] | None = None,
    status: str = "pass",
    issue_code: str | None = None,
) -> dict[str, Any]:
    stage_rows = [
        {
            "stage": stage,
            "status": "pass" if status == "pass" else "fail",
            "observed_at_ms": 1782320000000 + index,
            "evidence_refs": [f"evidence.{stage}"],
            "issue_codes": [issue_code] if issue_code and status != "pass" else [],
        }
        for index, stage in enumerate(stages, start=1)
    ]
    issues = (
        [
            {
                "issue_code": issue_code,
                "severity": "error",
                "message": "fake route failure",
            }
        ]
        if issue_code
        else []
    )
    bridge_evidence = {
        "$schema": "rusty.manifold.bridge.route_evidence.v1",
        "evidence_id": request["evidence_id"],
        "route_id": route_id,
        "status": status,
        "started_at_ms": 1782320000000,
        "ended_at_ms": 1782320000010,
        "stage_reports": stage_rows,
        "artifact_refs": ["artifact.fake.execution"],
        "issues": issues,
    }
    return {
        "$schema": schema,
        "status": status,
        "started_at_ms": 1782320000000,
        "ended_at_ms": 1782320000010,
        "route_id": route_id,
        "request_id": request["request_id"],
        "command": request["command"],
        "required_evidence_stages": request["required_evidence_stages"],
        "setup_actions": setup_actions or [],
        "stage_observations": stage_rows,
        "issues": issues,
        "bridge_route_evidence": bridge_evidence,
    }


class FakeAdbRunner:
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
            return subprocess.CompletedProcess(command, 0, "12345\n", "")
        if "forward --list" in text:
            return subprocess.CompletedProcess(command, 0, "serial-1 tcp:28765 tcp:18765\n", "")
        if "run-as" in text and "pwd" in text:
            return subprocess.CompletedProcess(command, 0, "/data/user/0/test\n", "")
        if "resolve-activity" in text:
            return subprocess.CompletedProcess(command, 0, "test.makepad/.Xr\n", "")
        return subprocess.CompletedProcess(command, 1, "", "unexpected command")


class FixedClock:
    def __init__(self) -> None:
        self.value = 1782320000000

    def __call__(self) -> int:
        self.value += 1
        return self.value


def session_args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "command": "companion-session",
        "session_command": "run",
        "out": "session.json",
        "validation_out": None,
        "session_id": None,
        "frontend": "wpf",
        "profile": "hostess-makepad-quest",
        "descriptor": str(READINESS_DESCRIPTOR),
        "hostess_descriptor": str(READINESS_DESCRIPTOR),
        "gui_descriptors_root": None,
        "adb": "adb.exe",
        "serial": "serial-1",
        "android_sdk": "",
        "jdk_home": "",
        "cargo": "cargo",
        "cargo_makepad": "cargo-makepad",
        "broker_host": "127.0.0.1",
        "broker_port": 18765,
        "broker_local_port": 28765,
        "broker_package": "test.broker",
        "broker_activity": "test.broker/.BrokerStartActivity",
        "broker_path": "/manifold/v1/events",
        "check_broker": True,
        "require_broker": False,
        "makepad_package": "test.makepad",
        "makepad_activity": "test.makepad/.Xr",
        "probe_input": str(REPO_ROOT / "fixtures" / "bridge-command" / "hostess-broker-stream-command-request.json"),
        "fallback_input": str(REPO_ROOT / "fixtures" / "bridge-command" / "hostess-android-hotload-command-request.json"),
        "fallback_remote_dir": "files/hostess-t/settings",
        "connect_timeout_seconds": 1.0,
        "wait_seconds": 0.5,
        "fallback_wait_seconds": 0.5,
        "authority_wait_seconds": 0.5,
        "runtime_receipt_stream": "stream.hostess.makepad.bridge_command.receipt",
        "no_runtime_receipt_subscribe": False,
        "broker_process_wait_seconds": 0.5,
        "makepad_process_wait_seconds": 0.5,
        "socket_wait_seconds": 0.5,
        "launch_settle_seconds": 0.0,
        "no_launch_broker": False,
        "no_launch_makepad": False,
        "no_wait_broker_process": False,
        "no_wait_makepad_process": False,
        "no_adb_forward_broker": False,
        "skip_probe": False,
        "no_fallback": False,
        "fail_on_error": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def fake_toolchain(root: Path) -> dict[str, str]:
    tool_root = root / "tools"
    adb = touch(tool_root / "adb.exe")
    cargo = touch(tool_root / "cargo.exe")
    cargo_makepad = touch(tool_root / "cargo-makepad.exe")
    android_sdk = tool_root / "android-sdk"
    android_sdk.mkdir()
    jdk_home = tool_root / "jdk"
    (jdk_home / "bin").mkdir(parents=True)
    touch(jdk_home / "bin" / "java.exe")
    return {
        "adb": str(adb),
        "cargo": str(cargo),
        "cargo_makepad": str(cargo_makepad),
        "android_sdk": str(android_sdk),
        "jdk_home": str(jdk_home),
    }


def write_descriptor_root(root: Path) -> Path:
    descriptor_root = root / "descriptors"
    descriptor_root.mkdir()
    (descriptor_root / "transport-capability-websocket.json").write_text(
        json.dumps(
            {
                "schema": "rusty.gui.companion.transport_capability.v1",
                "transport_id": "transport.manifold_websocket",
                "title": "Manifold WebSocket",
                "family": "websocket",
                "plane": "control",
                "delivery": "ordered_reliable",
                "payload_rate": "low_rate_json",
                "authority_role": "requester",
                "route_ids": ["bridge_route.command.websocket.applied"],
                "required_evidence_stages": [
                    "sent",
                    "transport_ok",
                    "authority_accepted",
                    "runtime_accepted",
                    "applied",
                ],
                "supported_frontends": ["wpf", "makepad", "cli"],
            }
        ),
        encoding="utf-8",
    )
    return descriptor_root


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def phase(report: dict[str, Any], phase_id: str) -> dict[str, Any]:
    return next(row for row in report["phases"] if row["phase_id"] == phase_id)


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
