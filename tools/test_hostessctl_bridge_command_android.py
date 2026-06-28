from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.hostessctl.bridge_command_android_routes import (
    BRIDGE_COMMAND_ANDROID_EXECUTION_SCHEMA,
    BRIDGE_COMMAND_RUNTIME_RECEIPT_SCHEMA,
    execute_bridge_command_android_request,
    run_bridge_command_android,
)
from tools.hostessctl.bridge_route_evidence import (
    HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA,
    MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
)
from tools.hostessctl.cli_parser import build_hostessctl_parser


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_COMMAND_FIXTURES = REPO_ROOT / "fixtures" / "bridge-command"


class HostessCtlBridgeCommandAndroidTests(unittest.TestCase):
    def test_android_hotload_command_produces_applied_bridge_evidence(self) -> None:
        request = read_json(BRIDGE_COMMAND_FIXTURES / "hostess-android-hotload-command-request.json")
        fake = FakeAndroidRoute(receipt_for_request(request, applied=True))

        execution = execute_bridge_command_android_request(
            request,
            args=bridge_command_android_args("request.json", "evidence.json"),
            run_func=fake.run,
            run_captured_func=fake.run_captured,
            write_app_file_func=fake.write_app_file,
            read_app_file_func=fake.read_app_file,
            wait_app_file_func=fake.wait_app_file,
            clock_ms_func=FakeClock(
                [
                    1765010000000,
                    1765010000005,
                    1765010000010,
                    1765010000015,
                    1765010000020,
                ]
            ),
            logcat_out=None,
        )

        self.assertEqual(execution["$schema"], BRIDGE_COMMAND_ANDROID_EXECUTION_SCHEMA)
        self.assertEqual(execution["status"], "pass")
        self.assertEqual(execution["runtime_receipt"]["$schema"], BRIDGE_COMMAND_RUNTIME_RECEIPT_SCHEMA)
        self.assertEqual(execution["bridge_route_evidence"]["$schema"], MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA)
        self.assertEqual(execution["bridge_route_evidence"]["status"], "pass")
        self.assertIn("applied", {row["stage"] for row in execution["stage_observations"]})
        self.assertTrue(
            any("am" in command and "start" in command for command in fake.commands)
        )
        self.assertIn("files/hostess-t/settings/bridge-command-request.json", fake.written)

    def test_run_android_hotload_command_writes_evidence_execution_and_validation(self) -> None:
        source_path = BRIDGE_COMMAND_FIXTURES / "hostess-android-hotload-command-request.json"
        request = read_json(source_path)
        fake = FakeAndroidRoute(receipt_for_request(request, applied=True))

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "android-bridge-command.json"
            status = run_bridge_command_android(
                bridge_command_android_args(source_path, out),
                run_func=fake.run,
                run_captured_func=fake.run_captured,
                write_app_file_func=fake.write_app_file,
                read_app_file_func=fake.read_app_file,
                wait_app_file_func=fake.wait_app_file,
                clock_ms_func=FakeClock(
                    [
                        1765011000000,
                        1765011000005,
                        1765011000010,
                        1765011000015,
                        1765011000020,
                    ]
                ),
            )

            self.assertEqual(status, 0)
            evidence = read_json(out)
            execution = read_json(out.with_name("android-bridge-command.android-execution.json"))
            validation = read_json(out.with_name("android-bridge-command.validation-report.json"))

        self.assertEqual(evidence["$schema"], MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA)
        self.assertEqual(execution["$schema"], BRIDGE_COMMAND_ANDROID_EXECUTION_SCHEMA)
        self.assertEqual(validation["$schema"], HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA)
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["missing_required_evidence_stages"], [])

    def test_android_authorized_command_requires_broker_and_runtime_evidence(self) -> None:
        request = read_json(BRIDGE_COMMAND_FIXTURES / "hostess-android-authorized-command-request.json")
        fake_android = FakeAndroidRoute(receipt_for_request(request, applied=True))
        fake_broker = FakeBrokerClient([command_ack(request["request_id"], request["command"])])

        execution = execute_bridge_command_android_request(
            request,
            args=bridge_command_android_args(
                "request.json",
                "evidence.json",
                broker_authority=True,
            ),
            run_func=fake_android.run,
            run_captured_func=fake_android.run_captured,
            write_app_file_func=fake_android.write_app_file,
            read_app_file_func=fake_android.read_app_file,
            wait_app_file_func=fake_android.wait_app_file,
            broker_client_factory=lambda *args, **kwargs: fake_broker,
            clock_ms_func=FakeClock(
                [
                    1765013000000,
                    1765013000005,
                    1765013000010,
                    1765013000015,
                    1765013000020,
                    1765013000025,
                    1765013000030,
                ]
            ),
            logcat_out=None,
        )

        stages = {row["stage"] for row in execution["stage_observations"]}
        self.assertEqual(execution["status"], "pass")
        self.assertTrue({"sent", "transport_ok", "authority_accepted", "runtime_accepted", "applied"} <= stages)
        self.assertTrue(execution["broker_authority"]["enabled"])
        self.assertEqual(fake_broker.sent[0]["client_id"], "hostessctl.bridge_command.android_authorized")
        staged = json.loads(fake_android.written["files/hostess-t/settings/bridge-command-request.json"])
        self.assertEqual(staged["params"]["source"], "manifold-authorized-app-private-json")
        self.assertTrue(staged["params"]["broker_authority_accepted"])

    def test_android_authorized_command_can_prepare_broker_adb_forward(self) -> None:
        request = read_json(BRIDGE_COMMAND_FIXTURES / "hostess-android-authorized-command-request.json")
        fake_android = FakeAndroidRoute(receipt_for_request(request, applied=True))
        fake_broker = FakeBrokerClient([command_ack(request["request_id"], request["command"])])

        execution = execute_bridge_command_android_request(
            request,
            args=bridge_command_android_args(
                "request.json",
                "evidence.json",
                broker_authority=True,
                adb_forward_broker=True,
            ),
            run_func=fake_android.run,
            run_captured_func=fake_android.run_captured,
            write_app_file_func=fake_android.write_app_file,
            read_app_file_func=fake_android.read_app_file,
            wait_app_file_func=fake_android.wait_app_file,
            broker_client_factory=lambda *args, **kwargs: fake_broker,
            clock_ms_func=FakeClock(
                [
                    1765013500000,
                    1765013500005,
                    1765013500010,
                    1765013500015,
                    1765013500020,
                    1765013500025,
                    1765013500030,
                ]
            ),
            logcat_out=None,
        )

        self.assertEqual(execution["status"], "pass")
        self.assertTrue(execution["broker_authority"]["adb_forward"])
        self.assertEqual(execution["broker_authority"]["port"], 28765)
        self.assertEqual(execution["broker_authority"]["target_port"], 18765)
        self.assertIn(
            ["adb.exe", "-s", "serial-1", "forward", "tcp:28765", "tcp:18765"],
            fake_android.commands,
        )
        self.assertTrue(
            any(action["action"] == "adb-forward-broker" for action in execution["actions"])
        )

    def test_android_authority_rejection_blocks_runtime_staging(self) -> None:
        request = read_json(BRIDGE_COMMAND_FIXTURES / "hostess-android-authorized-command-request.json")
        fake_android = FakeAndroidRoute(receipt_for_request(request, applied=True))
        fake_broker = FakeBrokerClient(
            [command_ack(request["request_id"], request["command"], accepted=False)]
        )

        execution = execute_bridge_command_android_request(
            request,
            args=bridge_command_android_args(
                "request.json",
                "evidence.json",
                broker_authority=True,
            ),
            run_func=fake_android.run,
            run_captured_func=fake_android.run_captured,
            write_app_file_func=fake_android.write_app_file,
            read_app_file_func=fake_android.read_app_file,
            wait_app_file_func=fake_android.wait_app_file,
            broker_client_factory=lambda *args, **kwargs: fake_broker,
            clock_ms_func=FakeClock(
                [
                    1765014000000,
                    1765014000005,
                    1765014000010,
                    1765014000015,
                    1765014000020,
                ]
            ),
            logcat_out=None,
        )

        self.assertEqual(execution["status"], "fail")
        self.assertEqual(fake_android.written, {})
        self.assertTrue(
            any(issue["issue_code"] == "hostess.issue.bridge_command.authority_rejected"
                for issue in execution["issues"])
        )

    def test_android_hotload_missing_applied_fails_validation(self) -> None:
        source_path = BRIDGE_COMMAND_FIXTURES / "hostess-android-hotload-command-request.json"
        request = read_json(source_path)
        fake = FakeAndroidRoute(receipt_for_request(request, applied=False))

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "android-bridge-command.json"
            status = run_bridge_command_android(
                bridge_command_android_args(source_path, out),
                run_func=fake.run,
                run_captured_func=fake.run_captured,
                write_app_file_func=fake.write_app_file,
                read_app_file_func=fake.read_app_file,
                wait_app_file_func=fake.wait_app_file,
                clock_ms_func=FakeClock(
                    [
                        1765012000000,
                        1765012000005,
                        1765012000010,
                        1765012000015,
                        1765012000020,
                    ]
                ),
            )

            self.assertEqual(status, 2)
            validation = read_json(out.with_name("android-bridge-command.validation-report.json"))

        self.assertEqual(validation["missing_required_evidence_stages"], ["applied"])

    def test_android_runtime_timeout_still_writes_execution_evidence(self) -> None:
        source_path = BRIDGE_COMMAND_FIXTURES / "hostess-android-hotload-command-request.json"
        request = read_json(source_path)
        fake = FakeAndroidRoute(receipt_for_request(request, applied=True))

        def timeout_wait(*args, **kwargs) -> None:
            raise SystemExit("timed out waiting for app file: test.makepad:receipt.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "android-timeout-command.json"
            status = run_bridge_command_android(
                bridge_command_android_args(source_path, out),
                run_func=fake.run,
                run_captured_func=fake.run_captured,
                write_app_file_func=fake.write_app_file,
                read_app_file_func=fake.read_app_file,
                wait_app_file_func=timeout_wait,
                clock_ms_func=FakeClock(
                    [
                        1765015000000,
                        1765015000005,
                        1765015000010,
                        1765015000015,
                        1765015000020,
                    ]
                ),
            )

            execution = read_json(out.with_name("android-timeout-command.android-execution.json"))
            validation = read_json(out.with_name("android-timeout-command.validation-report.json"))

        self.assertEqual(status, 2)
        self.assertEqual(execution["status"], "fail")
        self.assertTrue(
            any(
                issue["issue_code"] == "hostess.issue.bridge_command.android_execution_failed"
                for issue in execution["issues"]
            )
        )
        self.assertEqual(validation["status"], "fail")
        self.assertIn("runtime_accepted", validation["missing_required_evidence_stages"])

    def test_parser_accepts_run_bridge_command_android(self) -> None:
        args = build_parser().parse_args(
            [
                "run-bridge-command-android",
                "--input",
                "request.json",
                "--out",
                "evidence.json",
                "--adb",
                "adb.exe",
                "--serial",
                "serial-1",
                "--broker-authority",
                "--broker-port",
                "28765",
                "--broker-local-port",
                "38765",
                "--adb-forward-broker",
                "--wait-seconds",
                "0.5",
                "--no-launch",
            ]
        )

        self.assertEqual(args.command, "run-bridge-command-android")
        self.assertEqual(args.input, "request.json")
        self.assertEqual(args.out, "evidence.json")
        self.assertEqual(args.adb, "adb.exe")
        self.assertEqual(args.serial, "serial-1")
        self.assertTrue(args.broker_authority)
        self.assertEqual(args.broker_port, 28765)
        self.assertEqual(args.broker_local_port, 38765)
        self.assertTrue(args.adb_forward_broker)
        self.assertEqual(args.wait_seconds, 0.5)
        self.assertTrue(args.no_launch)


def bridge_command_android_args(
    source_path: Path | str,
    out: Path | str,
    *,
    broker_authority: bool = False,
    adb_forward_broker: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        input=str(source_path),
        out=str(out),
        execution_out=None,
        validation_out=None,
        logcat_out=None,
        route_descriptor=None,
        route_id=None,
        required_stage=[],
        broker_authority=broker_authority,
        broker_host="127.0.0.1",
        broker_port=18765,
        broker_local_port=28765,
        broker_path="/manifold/v1/events",
        connect_timeout_seconds=1.0,
        authority_wait_seconds=0.5,
        adb_forward_broker=adb_forward_broker,
        adb="adb.exe",
        serial="serial-1",
        makepad_package="test.makepad",
        makepad_activity="test.makepad/.MakepadAppXr",
        remote_dir="files/hostess-t/settings",
        wait_seconds=0.5,
        no_launch=False,
    )


def receipt_for_request(request: dict[str, object], *, applied: bool) -> dict[str, object]:
    stages: list[dict[str, object]] = [
        {
            "stage": "runtime_accepted",
            "status": "pass",
            "evidence_refs": ["evidence.quest.runtime_receipt"],
        }
    ]
    if applied:
        stages.append(
            {
                "stage": "applied",
                "status": "pass",
                "evidence_refs": ["evidence.quest.effective_state_marker"],
            }
        )
    return {
        "$schema": BRIDGE_COMMAND_RUNTIME_RECEIPT_SCHEMA,
        "status": "applied" if applied else "runtime_accepted",
        "request_id": request["request_id"],
        "command": request["command"],
        "runtime_accepted": True,
        "applied": applied,
        "probe_token": request["params"]["probe_token"],  # type: ignore[index]
        "stage_receipts": stages,
    }


class FakeAndroidRoute:
    def __init__(self, receipt: dict[str, object]) -> None:
        self.receipt = receipt
        self.commands: list[list[str]] = []
        self.written: dict[str, bytes] = {}

    def run(self, command: list[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    def run_captured(
        self, command: list[str], *, allow_failure: bool = False
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        request_id = str(self.receipt.get("request_id") or "")
        return subprocess.CompletedProcess(command, 0, stdout=f"HostessMakepad {request_id}\n", stderr="")

    def write_app_file(
        self,
        args: argparse.Namespace,
        package: str,
        relative_path: str,
        payload: bytes,
    ) -> None:
        self.written[relative_path] = payload

    def read_app_file(self, args: argparse.Namespace, package: str, relative_path: str) -> bytes:
        return json.dumps(self.receipt).encode("utf-8")

    def wait_app_file(
        self,
        args: argparse.Namespace,
        package: str,
        relative_path: str,
        timeout_seconds: float,
        *,
        run,
    ) -> None:
        return None


def command_ack(request_id: str, command: str, *, accepted: bool = True) -> dict[str, object]:
    return {
        "type": "command_ack",
        "request_id": request_id,
        "command": command,
        "accepted": accepted,
        "authority": "rusty.manifold",
    }


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
