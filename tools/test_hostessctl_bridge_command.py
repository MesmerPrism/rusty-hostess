from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools.hostessctl.bridge_command_routes import (
    BRIDGE_COMMAND_EXECUTION_SCHEMA,
    DEFAULT_RUNTIME_RECEIPT_STREAM,
    execute_bridge_command_request,
    run_bridge_command,
)
from tools.hostessctl.bridge_route_evidence import (
    HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA,
    MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
)
from tools.hostessctl.cli_parser import build_hostessctl_parser


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_COMMAND_FIXTURES = REPO_ROOT / "fixtures" / "bridge-command"
DAMAGED_FIXTURES = REPO_ROOT / "fixtures" / "damaged"


class HostessCtlBridgeCommandTests(unittest.TestCase):
    def test_fake_websocket_command_produces_applied_bridge_evidence(self) -> None:
        request = read_json(BRIDGE_COMMAND_FIXTURES / "hostess-websocket-command-request.json")
        expected = read_json(BRIDGE_COMMAND_FIXTURES / "hostess-websocket-command-applied-evidence.json")
        fake = FakeBrokerClient(
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

        execution = execute_bridge_command_request(
            request,
            broker_host="127.0.0.1",
            broker_port=18765,
            broker_path="/manifold/v1/events",
            connect_timeout_seconds=1.0,
            wait_seconds=1.0,
            broker_client_factory=lambda *args, **kwargs: fake,
            clock_ms_func=FakeClock(
                [
                    1765004000000,
                    1765004000005,
                    1765004000010,
                    1765004000020,
                    1765004000030,
                    1765004000035,
                ]
            ),
        )

        self.assertEqual(execution["$schema"], BRIDGE_COMMAND_EXECUTION_SCHEMA)
        self.assertEqual(execution["status"], "pass")
        self.assertEqual(execution["bridge_route_evidence"], expected)
        self.assertEqual(fake.sent[0]["command"], "subscribe")
        self.assertEqual(fake.sent[0]["params"]["stream"], DEFAULT_RUNTIME_RECEIPT_STREAM)
        self.assertEqual(fake.sent[1]["client_id"], "hostessctl.bridge_command")
        self.assertEqual(fake.sent[1]["schema"], "rusty.manifold.command.envelope.v1")
        self.assertEqual(fake.sent[1]["command"], "quest.projection_target.set_scale")
        self.assertTrue(fake.closed)

    def test_run_bridge_command_writes_evidence_execution_and_validation(self) -> None:
        source_path = BRIDGE_COMMAND_FIXTURES / "hostess-websocket-command-request.json"
        request = read_json(source_path)
        fake = FakeBrokerClient(
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

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "bridge-command.json"
            status = run_bridge_command(
                bridge_command_args(source_path, out),
                broker_client_factory=lambda *args, **kwargs: fake,
                clock_ms_func=FakeClock(
                    [
                        1765004000000,
                        1765004000005,
                        1765004000010,
                        1765004000020,
                        1765004000030,
                        1765004000035,
                    ]
                ),
            )

            self.assertEqual(status, 0)
            evidence = read_json(out)
            execution = read_json(out.with_name("bridge-command.command-execution.json"))
            validation = read_json(out.with_name("bridge-command.validation-report.json"))

        self.assertEqual(evidence["$schema"], MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA)
        self.assertEqual(execution["$schema"], BRIDGE_COMMAND_EXECUTION_SCHEMA)
        self.assertEqual(validation["$schema"], HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA)
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["missing_required_evidence_stages"], [])

    def test_missing_runtime_and_applied_receipts_fail_validation(self) -> None:
        source_path = DAMAGED_FIXTURES / "hostess-bridge-command-missing-applied-request.json"
        request = read_json(source_path)
        fake = FakeBrokerClient([command_ack(request["request_id"], request["command"])])

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "damaged-bridge-command.json"
            status = run_bridge_command(
                bridge_command_args(source_path, out, wait_seconds=0.01),
                broker_client_factory=lambda *args, **kwargs: fake,
                clock_ms_func=FakeClock(
                    [
                        1765005000000,
                        1765005000005,
                        1765005000010,
                        1765005000020,
                    ]
                ),
            )

            self.assertEqual(status, 2)
            evidence = read_json(out)
            validation = read_json(out.with_name("damaged-bridge-command.validation-report.json"))

        self.assertEqual(evidence["status"], "fail")
        self.assertEqual(
            validation["missing_required_evidence_stages"],
            ["runtime_accepted", "applied"],
        )
        self.assertTrue(evidence["issues"])

    def test_parser_accepts_run_bridge_command(self) -> None:
        args = build_parser().parse_args(
            [
                "run-bridge-command",
                "--input",
                "request.json",
                "--out",
                "evidence.json",
                "--broker-host",
                "127.0.0.1",
                "--broker-port",
                "28765",
                "--wait-seconds",
                "0.5",
            ]
        )

        self.assertEqual(args.command, "run-bridge-command")
        self.assertEqual(args.input, "request.json")
        self.assertEqual(args.out, "evidence.json")
        self.assertEqual(args.broker_port, 28765)
        self.assertEqual(args.wait_seconds, 0.5)
        self.assertEqual(args.runtime_receipt_stream, DEFAULT_RUNTIME_RECEIPT_STREAM)
        self.assertFalse(args.no_runtime_receipt_subscribe)


def bridge_command_args(source_path: Path, out: Path, *, wait_seconds: float = 1.0) -> argparse.Namespace:
    return argparse.Namespace(
        input=str(source_path),
        out=str(out),
        execution_out=None,
        validation_out=None,
        route_descriptor=None,
        broker_host="127.0.0.1",
        broker_port=18765,
        broker_path="/manifold/v1/events",
        connect_timeout_seconds=1.0,
        wait_seconds=wait_seconds,
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
