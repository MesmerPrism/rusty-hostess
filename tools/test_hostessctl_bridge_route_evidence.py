from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools.hostessctl import hostessctl
from tools.hostessctl.bridge_route_evidence import (
    HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA,
    MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA,
    normalize_bridge_route_evidence,
    validate_bridge_route_evidence,
)
from tools.hostessctl.cli_parser import build_hostessctl_parser


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "bridge-route"
DAMAGED_ROOT = REPO_ROOT / "fixtures" / "damaged"


class HostessCtlBridgeRouteEvidenceTests(unittest.TestCase):
    def test_command_fixture_normalizes_to_manifold_bridge_route_evidence(self) -> None:
        source = read_json(FIXTURE_ROOT / "hostess-command-websocket-applied-input.json")
        expected = read_json(FIXTURE_ROOT / "hostess-command-websocket-applied-evidence.json")

        evidence = normalize_bridge_route_evidence(source)
        validation = validate_bridge_route_evidence(evidence)

        self.assertEqual(evidence, expected)
        self.assertEqual(evidence["$schema"], MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA)
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["missing_required_evidence_stages"], [])
        self.assertIn("applied", validation["passed_evidence_stages"])

    def test_device_transport_fixture_does_not_require_runtime_applied_receipt(self) -> None:
        source = read_json(FIXTURE_ROOT / "hostess-device-adb-transport-input.json")
        expected = read_json(FIXTURE_ROOT / "hostess-device-adb-transport-evidence.json")

        evidence = normalize_bridge_route_evidence(source)
        validation = validate_bridge_route_evidence(evidence)

        self.assertEqual(evidence, expected)
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["required_evidence_stages"], ["sent", "transport_ok"])
        self.assertNotIn("runtime_accepted", validation["required_evidence_stages"])
        self.assertNotIn("applied", validation["required_evidence_stages"])

    def test_applied_command_rejects_transport_only_evidence(self) -> None:
        source = read_json(DAMAGED_ROOT / "hostess-command-websocket-transport-only-input.json")

        evidence = normalize_bridge_route_evidence(source)
        validation = validate_bridge_route_evidence(
            evidence,
            required_stages=source["required_evidence_stages"],
        )

        self.assertEqual(validation["status"], "fail")
        self.assertEqual(
            validation["missing_required_evidence_stages"],
            ["runtime_accepted", "applied"],
        )
        self.assertTrue(
            any(
                "hostess.issue.bridge_route.missing_required_evidence"
                in check["issue_codes"]
                for check in validation["checks"]
            )
        )

    def test_cli_command_writes_evidence_and_validation_report(self) -> None:
        source_path = FIXTURE_ROOT / "hostess-command-websocket-applied-input.json"
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "bridge-route.json"

            status = hostessctl.emit_bridge_route_evidence(
                argparse.Namespace(
                    input=str(source_path),
                    out=str(out),
                    validation_out=None,
                    route_descriptor=None,
                    required_stage=[],
                )
            )

            self.assertEqual(status, 0)
            evidence = read_json(out)
            validation = read_json(out.with_name("bridge-route.validation-report.json"))
        self.assertEqual(evidence["$schema"], MANIFOLD_BRIDGE_ROUTE_EVIDENCE_SCHEMA)
        self.assertEqual(validation["$schema"], HOSTESS_BRIDGE_ROUTE_VALIDATION_SCHEMA)
        self.assertEqual(validation["status"], "pass")

    def test_cli_command_rejects_damaged_transport_only_input(self) -> None:
        source_path = DAMAGED_ROOT / "hostess-command-websocket-transport-only-input.json"
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "bridge-route.json"

            status = hostessctl.emit_bridge_route_evidence(
                argparse.Namespace(
                    input=str(source_path),
                    out=str(out),
                    validation_out=None,
                    route_descriptor=None,
                    required_stage=[],
                )
            )

            self.assertEqual(status, 2)
            validation = read_json(out.with_name("bridge-route.validation-report.json"))
        self.assertEqual(validation["status"], "fail")
        self.assertEqual(
            validation["missing_required_evidence_stages"],
            ["runtime_accepted", "applied"],
        )

    def test_parser_accepts_bridge_route_evidence_command(self) -> None:
        args = build_parser().parse_args(
            [
                "emit-bridge-route-evidence",
                "--input",
                "input.json",
                "--out",
                "evidence.json",
                "--required-stage",
                "sent",
                "--required-stage",
                "transport_ok",
            ]
        )

        self.assertEqual(args.command, "emit-bridge-route-evidence")
        self.assertEqual(args.input, "input.json")
        self.assertEqual(args.out, "evidence.json")
        self.assertEqual(args.required_stage, ["sent", "transport_ok"])


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
