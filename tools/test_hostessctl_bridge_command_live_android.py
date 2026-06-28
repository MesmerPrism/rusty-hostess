from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.hostessctl.bridge_command_live_android_routes import (
    BRIDGE_COMMAND_LIVE_ANDROID_EXECUTION_SCHEMA,
    execute_bridge_command_live_android_request,
    run_bridge_command_live_android,
)
from tools.hostessctl.bridge_command_routes import DEFAULT_RUNTIME_RECEIPT_STREAM
from tools.hostessctl.bridge_route_evidence import (
    HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA,
    MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
)
from tools.hostessctl.cli_parser import build_hostessctl_parser


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_COMMAND_FIXTURES = REPO_ROOT / "fixtures" / "bridge-command"


class HostessCtlBridgeCommandLiveAndroidTests(unittest.TestCase):
    def test_live_android_orchestration_runs_broker_stream_command(self) -> None:
        request = read_json(BRIDGE_COMMAND_FIXTURES / "hostess-broker-stream-command-request.json")
        fake_android = FakeLiveAndroidRoute()
        fake_broker = FakeBrokerClient(
            [
                command_ack(request["request_id"], request["command"]),
                runtime_receipt_stream_event(
                    request["request_id"],
                    "runtime_accepted",
                    "evidence.quest.runtime_receipt",
                ),
                runtime_receipt_stream_event(
                    request["request_id"],
                    "applied",
                    "evidence.quest.effective_state_marker",
                ),
            ]
        )

        execution = execute_bridge_command_live_android_request(
            request,
            args=live_android_args("request.json", "evidence.json"),
            run_captured_func=fake_android.run_captured,
            broker_client_factory=lambda *args, **kwargs: fake_broker,
            clock_ms_func=FakeClock(
                [
                    1765020000000,
                    1765020000005,
                    1765020000010,
                    1765020000020,
                    1765020000030,
                    1765020000040,
                ]
            ),
            socket_probe_func=lambda host, port, timeout: True,
            sleep_func=lambda seconds: None,
        )

        self.assertEqual(execution["$schema"], BRIDGE_COMMAND_LIVE_ANDROID_EXECUTION_SCHEMA)
        self.assertEqual(execution["status"], "pass")
        self.assertEqual(execution["bridge_route_evidence"]["$schema"], MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA)
        self.assertEqual(execution["command_execution"]["status"], "pass")
        stages = {row["stage"] for row in execution["stage_observations"]}
        self.assertTrue({"sent", "transport_ok", "authority_accepted", "runtime_accepted", "applied"} <= stages)
        actions = {row["action"] for row in execution["setup_actions"]}
        self.assertTrue(
            {
                "launch-manifold-broker",
                "wait-manifold-broker-process",
                "adb-forward-broker",
                "check-broker-adb-forward",
                "wait-broker-forwarded-socket",
                "launch-hostess-makepad",
                "wait-hostess-makepad-process",
            }
            <= actions
        )
        self.assertIn(
            ["adb.exe", "-s", "serial-1", "forward", "tcp:28765", "tcp:18765"],
            fake_android.commands,
        )
        self.assertEqual(fake_broker.sent[0]["command"], "subscribe")
        self.assertEqual(fake_broker.sent[0]["params"]["stream"], DEFAULT_RUNTIME_RECEIPT_STREAM)
        self.assertEqual(fake_broker.sent[1]["command"], "hostess.makepad.bridge_probe.set_marker")

    def test_live_android_socket_failure_still_writes_execution_and_validation(self) -> None:
        source_path = BRIDGE_COMMAND_FIXTURES / "hostess-broker-stream-command-request.json"
        fake_android = FakeLiveAndroidRoute()

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "live-android-command.json"
            status = run_bridge_command_live_android(
                live_android_args(source_path, out, socket_wait_seconds=0.0),
                run_captured_func=fake_android.run_captured,
                broker_client_factory=lambda *args, **kwargs: FakeBrokerClient([]),
                clock_ms_func=FakeClock([1765021000000, 1765021000005, 1765021000010]),
                socket_probe_func=lambda host, port, timeout: False,
                sleep_func=lambda seconds: None,
            )

            execution = read_json(out.with_name("live-android-command.live-android-execution.json"))
            validation = read_json(out.with_name("live-android-command.validation-report.json"))

        self.assertEqual(status, 2)
        self.assertEqual(execution["status"], "fail")
        self.assertEqual(validation["$schema"], HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA)
        self.assertEqual(validation["status"], "fail")
        self.assertIn("transport_ok", validation["missing_required_evidence_stages"])
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.bridge_command.live_android.broker_socket_closed"
                for issue in execution["issues"]
            )
        )

    def test_parser_accepts_run_bridge_command_live_android(self) -> None:
        args = build_parser().parse_args(
            [
                "run-bridge-command-live-android",
                "--input",
                "request.json",
                "--out",
                "evidence.json",
                "--adb",
                "adb.exe",
                "--serial",
                "serial-1",
                "--broker-port",
                "18765",
                "--broker-local-port",
                "28765",
                "--wait-seconds",
                "0.5",
                "--launch-settle-seconds",
                "0",
            ]
        )

        self.assertEqual(args.command, "run-bridge-command-live-android")
        self.assertEqual(args.input, "request.json")
        self.assertEqual(args.out, "evidence.json")
        self.assertEqual(args.adb, "adb.exe")
        self.assertEqual(args.serial, "serial-1")
        self.assertEqual(args.broker_port, 18765)
        self.assertEqual(args.broker_local_port, 28765)
        self.assertEqual(args.wait_seconds, 0.5)
        self.assertEqual(args.launch_settle_seconds, 0)
        self.assertFalse(args.no_adb_forward_broker)


def live_android_args(
    source_path: Path | str,
    out: Path | str,
    *,
    socket_wait_seconds: float = 0.5,
) -> argparse.Namespace:
    return argparse.Namespace(
        input=str(source_path),
        out=str(out),
        execution_out=None,
        validation_out=None,
        route_descriptor=None,
        adb="adb.exe",
        serial="serial-1",
        broker_package="test.broker",
        broker_activity="test.broker/.BrokerStartActivity",
        broker_host="127.0.0.1",
        broker_port=18765,
        broker_local_port=28765,
        broker_path="/manifold/v1/events",
        connect_timeout_seconds=1.0,
        wait_seconds=0.5,
        runtime_receipt_stream=DEFAULT_RUNTIME_RECEIPT_STREAM,
        no_runtime_receipt_subscribe=False,
        makepad_package="test.makepad",
        makepad_activity="test.makepad/.MakepadAppXr",
        broker_process_wait_seconds=0.5,
        makepad_process_wait_seconds=0.5,
        socket_wait_seconds=socket_wait_seconds,
        launch_settle_seconds=0.0,
        no_launch_broker=False,
        no_launch_makepad=False,
        no_wait_broker_process=False,
        no_wait_makepad_process=False,
        no_adb_forward_broker=False,
    )


def command_ack(request_id: str, command: str) -> dict[str, object]:
    return {
        "type": "command_ack",
        "request_id": request_id,
        "command": command,
        "accepted": True,
        "authority": "rusty.manifold",
    }


def runtime_receipt(request_id: str, stage: str, evidence_ref: str) -> dict[str, object]:
    return {
        "type": "command_receipt",
        "request_id": request_id,
        "bridge_route_stage": stage,
        "status": "pass",
        "evidence_ref": evidence_ref,
    }


def runtime_receipt_stream_event(request_id: str, stage: str, evidence_ref: str) -> dict[str, object]:
    return {
        "type": "stream_event",
        "stream": DEFAULT_RUNTIME_RECEIPT_STREAM,
        "payload": runtime_receipt(request_id, stage, evidence_ref),
    }


class FakeLiveAndroidRoute:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run_captured(
        self, command: list[str], *, allow_failure: bool = False
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[-3:] == ["shell", "pidof", "test.broker"]:
            return subprocess.CompletedProcess(command, 0, stdout="123\n", stderr="")
        if command[-3:] == ["shell", "pidof", "test.makepad"]:
            return subprocess.CompletedProcess(command, 0, stdout="456\n", stderr="")
        if command[-2:] == ["forward", "--list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="serial-1 tcp:28765 tcp:18765\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


class FakeBrokerClient:
    def __init__(self, messages: list[dict[str, object]]) -> None:
        self.messages = list(messages)
        self.sent: list[dict[str, object]] = []
        self.closed = False

    def send_json(self, payload: dict[str, object]) -> None:
        self.sent.append(payload)

    def recv_json(self, *, timeout: float) -> dict[str, object] | None:
        if not self.messages:
            return None
        return self.messages.pop(0)

    def close(self) -> None:
        self.closed = True


class FakeClock:
    def __init__(self, values: list[int]) -> None:
        self.values = list(values)
        self.last = values[-1]

    def __call__(self) -> int:
        if not self.values:
            return self.last
        self.last = self.values.pop(0)
        return self.last


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
