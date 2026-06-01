from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.hostessctl import hostessctl


class HostessCtlRecordValuesTests(unittest.TestCase):
    def test_plan_only_marks_single_supported_value_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "recording" / "polar-acc-plan.json"

            status = hostessctl.run_manifold_value_recording(
                record_args(
                    root,
                    out,
                    target="desktop",
                    values=["polar.acc"],
                    plan_only=True,
                )
            )

            self.assertEqual(status, 0)
            evidence = read_json(out)
            validation = read_json(out.with_name("polar-acc-plan.validation-report.json"))
            host_run = read_json(out.with_name("polar-acc-plan.host-run-evidence.json"))
            self.assertEqual(evidence["$schema"], "rusty.hostess.manifold_value_recording.evidence.v1")
            self.assertEqual(evidence["status"], "ready")
            self.assertEqual(evidence["request"]["requested_value_ids"], ["stream.polar_h10.acc"])
            self.assertFalse(evidence["recording"]["recording_performed"])
            self.assertTrue(evidence["recording"]["general_recorder"])
            self.assertFalse(evidence["recording"]["polar_specific"])
            self.assertEqual(evidence["provider_plans"][0]["recording_route"], "hostessctl.run-live")
            self.assertEqual(validation["status"], "pass")
            self.assertEqual(host_run["status"], "ready")

    def test_controller_and_polar_plan_is_blocked_without_claiming_controller_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "recording" / "controller-polar-plan.json"

            status = hostessctl.run_manifold_value_recording(
                record_args(
                    root,
                    out,
                    target="quest",
                    values=["stream.polar_h10.acc", "stream.motion.object_pose"],
                    plan_only=True,
                    allow_blocked=True,
                )
            )

            self.assertEqual(status, 0)
            evidence = read_json(out)
            host_run = read_json(out.with_name("controller-polar-plan.host-run-evidence.json"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertIn(
                "live OpenXR/controller pose provider",
                " ".join(evidence["blocked_reasons"]),
            )
            self.assertIn(
                "simultaneous multi-value recording",
                " ".join(evidence["blocked_reasons"]),
            )
            self.assertFalse(evidence["recording"]["controller_input_used"])
            self.assertFalse(evidence["recording"]["physical_controller_input_used"])
            self.assertTrue(evidence["recording"]["manual_controller_trial_required"])
            self.assertEqual(host_run["status"], "blocked")
            self.assertEqual(
                host_run["result_fields"]["requested_value_ids"],
                ["stream.polar_h10.acc", "stream.motion.object_pose"],
            )

    def test_single_supported_value_executes_existing_live_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "recording" / "polar-acc-recording.json"
            seen_live_args: list[argparse.Namespace] = []

            def fake_run_live_capture(args: argparse.Namespace) -> int:
                seen_live_args.append(args)
                live_out = Path(args.out)
                live_out.parent.mkdir(parents=True, exist_ok=True)
                live_out.write_text(
                    json.dumps(
                        {
                            "status": "pass",
                            "streams": [
                                {
                                    "stream_id": "stream.polar_h10.acc",
                                    "status": "pass",
                                    "sample_count": 3,
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                live_out.with_name(f"{live_out.stem}.validation-report.json").write_text(
                    json.dumps({"status": "pass"}),
                    encoding="utf-8",
                )
                return 0

            with patch.object(hostessctl, "run_live_capture", side_effect=fake_run_live_capture):
                status = hostessctl.run_manifold_value_recording(
                    record_args(root, out, target="desktop", values=["stream.polar_h10.acc"])
                )

            self.assertEqual(status, 0)
            self.assertEqual(len(seen_live_args), 1)
            self.assertEqual(seen_live_args[0].stream, "acc")
            self.assertEqual(seen_live_args[0].duration_seconds, 120.0)
            evidence = read_json(out)
            self.assertEqual(evidence["status"], "pass")
            self.assertTrue(evidence["recording"]["recording_performed"])
            self.assertEqual(evidence["captured_streams"][0]["stream_id"], "stream.polar_h10.acc")
            self.assertTrue(evidence["capture_artifacts"][0]["exists"])


def record_args(
    root: Path,
    out: Path,
    *,
    target: str,
    values: list[str],
    plan_only: bool = False,
    allow_blocked: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        target=target,
        value=values,
        out=str(out),
        packages_root=str(root / "packages"),
        duration_seconds=120.0,
        device_address=None,
        adb=None,
        serial=None,
        acc_rate=200,
        runtime_core="python-smoke",
        telemetry_page="raw",
        plan_only=plan_only,
        allow_blocked=allow_blocked,
    )


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
