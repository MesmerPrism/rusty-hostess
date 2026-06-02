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

    def test_controller_and_polar_plan_is_ready_without_claiming_controller_input(self) -> None:
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
                )
            )

            self.assertEqual(status, 0)
            evidence = read_json(out)
            host_run = read_json(out.with_name("controller-polar-plan.host-run-evidence.json"))
            self.assertEqual(evidence["status"], "ready")
            self.assertEqual(evidence["blocked_reasons"], [])
            self.assertEqual(
                {
                    plan["stream_id"]: plan["recording_route"]
                    for plan in evidence["provider_plans"]
                },
                {
                    "stream.polar_h10.acc": "hostessctl.broker-websocket-record",
                    "stream.motion.object_pose": "hostessctl.broker-websocket-record",
                },
            )
            self.assertFalse(evidence["recording"]["controller_input_used"])
            self.assertFalse(evidence["recording"]["physical_controller_input_used"])
            self.assertTrue(evidence["recording"]["manual_controller_trial_required"])
            self.assertTrue(evidence["recording"]["simultaneous_multi_value_recording_supported"])
            self.assertEqual(host_run["status"], "ready")
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

    def test_controller_and_polar_executes_broker_recording_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "recording" / "controller-polar-recording.json"
            seen_broker_args: list[tuple[argparse.Namespace, list[dict[str, object]], Path]] = []

            def fake_record_broker_streams(
                args: argparse.Namespace,
                provider_plans: list[dict[str, object]],
                capture_out: Path,
            ) -> int:
                seen_broker_args.append((args, provider_plans, capture_out))
                capture_out.parent.mkdir(parents=True, exist_ok=True)
                capture_out.write_text(
                    json.dumps(
                        {
                            "$schema": "rusty.hostess.broker_stream_recording.evidence.v1",
                            "status": "pass",
                            "streams": [
                                {
                                    "stream_id": "stream.polar_h10.acc",
                                    "broker_stream_id": "bio:polar_acc",
                                    "status": "pass",
                                    "sample_count": 2,
                                    "event_count": 2,
                                },
                                {
                                    "stream_id": "stream.motion.object_pose",
                                    "broker_stream_id": "stream.motion.object_pose",
                                    "status": "pass",
                                    "sample_count": 2,
                                    "event_count": 2,
                                },
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                capture_out.with_name(f"{capture_out.stem}.validation-report.json").write_text(
                    json.dumps({"status": "pass"}),
                    encoding="utf-8",
                )
                return 0

            with patch.object(
                hostessctl,
                "record_broker_websocket_streams",
                side_effect=fake_record_broker_streams,
            ):
                status = hostessctl.run_manifold_value_recording(
                    record_args(
                        root,
                        out,
                        target="quest",
                        values=["stream.polar_h10.acc", "stream.motion.object_pose"],
                        adb="adb",
                        serial="quest-serial",
                    )
                )

            self.assertEqual(status, 0)
            self.assertEqual(len(seen_broker_args), 1)
            self.assertEqual(
                [plan["recording_route"] for plan in seen_broker_args[0][1]],
                ["hostessctl.broker-websocket-record", "hostessctl.broker-websocket-record"],
            )
            evidence = read_json(out)
            self.assertEqual(evidence["status"], "pass")
            self.assertTrue(evidence["recording"]["recording_performed"])
            self.assertTrue(evidence["recording"]["controller_input_used"])
            self.assertTrue(evidence["recording"]["physical_controller_input_used"])
            self.assertFalse(evidence["recording"]["manual_controller_trial_required"])
            self.assertEqual(
                {
                    stream["stream_id"]: stream["status"]
                    for stream in evidence["captured_streams"]
                },
                {
                    "stream.polar_h10.acc": "pass",
                    "stream.motion.object_pose": "pass",
                },
            )


def record_args(
    root: Path,
    out: Path,
    *,
    target: str,
    values: list[str],
    plan_only: bool = False,
    allow_blocked: bool = False,
    adb: str | None = None,
    serial: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        target=target,
        value=values,
        out=str(out),
        packages_root=str(root / "packages"),
        duration_seconds=120.0,
        device_address=None,
        adb=adb,
        serial=serial,
        acc_rate=200,
        broker_package=hostessctl.BROKER_PACKAGE,
        broker_activity=hostessctl.BROKER_ACTIVITY,
        broker_port=hostessctl.BROKER_PORT,
        broker_local_port=hostessctl.BROKER_LOCAL_FORWARD_PORT,
        makepad_provider_package=hostessctl.MAKEPAD_XR_PROVIDER_PACKAGE,
        makepad_provider_activity=hostessctl.MAKEPAD_XR_PROVIDER_ACTIVITY,
        makepad_pose_controller="right",
        makepad_pose_kind="grip",
        makepad_pose_sample_hz=20.0,
        no_launch_broker=False,
        no_launch_providers=False,
        runtime_core="python-smoke",
        telemetry_page="raw",
        plan_only=plan_only,
        allow_blocked=allow_blocked,
    )


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
