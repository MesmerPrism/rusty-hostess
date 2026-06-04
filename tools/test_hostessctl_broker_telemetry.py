from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.hostessctl import hostessctl


class HostessCtlBrokerTelemetryTests(unittest.TestCase):
    def test_broker_telemetry_validation_requires_observer_boundary(self) -> None:
        evidence = broker_telemetry_evidence()

        validation = hostessctl.validate_broker_telemetry_observer_evidence(evidence)

        self.assertEqual(validation["status"], "pass")
        evidence["capture"]["direct_ble_used"] = True
        evidence["direct_ble_used"] = True
        validation = hostessctl.validate_broker_telemetry_observer_evidence(evidence)
        self.assertEqual(validation["status"], "fail")

    def test_observe_broker_telemetry_launches_observer_without_force_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "broker-telemetry.json"
            render_out = root / "broker-telemetry-render.png"
            seen_commands: list[list[str]] = []
            render_args: list[argparse.Namespace] = []

            def fake_run(
                command: list[str],
                *,
                allow_failure: bool = False,
                cwd: Path | None = None,
            ) -> subprocess.CompletedProcess[str]:
                seen_commands.append(command)
                if "pull" in command:
                    remote = command[-2]
                    local = Path(command[-1])
                    if remote == hostessctl.ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE:
                        local.write_text(json.dumps(broker_telemetry_evidence()), encoding="utf-8")
                    elif remote == hostessctl.ANDROID_REMOTE_BROKER_TELEMETRY_REPORT:
                        local.write_text(
                            json.dumps(broker_telemetry_evidence()["broker_report"]),
                            encoding="utf-8",
                        )
                return subprocess.CompletedProcess(command, 0)

            def fake_render(args: argparse.Namespace) -> int:
                render_args.append(args)
                return 0

            with patch.object(hostessctl, "run", side_effect=fake_run), patch.object(
                hostessctl,
                "grant_broker_runtime_permissions",
            ), patch.object(hostessctl, "wait_for_android_file"), patch.object(
                hostessctl,
                "render_telemetry",
                side_effect=fake_render,
            ):
                status = hostessctl.observe_broker_telemetry_ui(
                    argparse.Namespace(
                        target="quest",
                        out=str(out),
                        adb="adb",
                        serial="quest",
                        duration_seconds=5.0,
                        device_address="AA:BB",
                        acc_rate=200,
                        scan_timeout_seconds=10.0,
                        broker_package=hostessctl.BROKER_PACKAGE,
                        broker_activity=hostessctl.BROKER_ACTIVITY,
                        broker_port=hostessctl.BROKER_PORT,
                        telemetry_page="raw",
                        no_launch_broker=False,
                        no_request_provider_start=False,
                        keep_provider_running=False,
                        render_out=str(render_out),
                    )
                )

            self.assertEqual(status, 0)
            flat_commands = [" ".join(command) for command in seen_commands]
            self.assertFalse(any("force-stop" in command for command in flat_commands))
            observer_start = next(command for command in seen_commands if hostessctl.ANDROID_BROKER_TELEMETRY_ACTION in command)
            self.assertIn("--ez", observer_start)
            self.assertIn("request_provider_start", observer_start)
            self.assertIn("stop_provider_on_finish", observer_start)
            self.assertEqual(render_args[0].source_evidence_path, "hostess-t/evidence/broker-telemetry/latest.json")
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["direct_ble_used"], False)


def broker_telemetry_evidence() -> dict[str, object]:
    return {
        "$schema": "rusty.hostess.broker_telemetry_observer.evidence.v1",
        "status": "pass",
        "host_profile": "headset",
        "telemetry_ui_visualized": True,
        "direct_ble_used": False,
        "capture": {
            "mode": "broker_acc",
            "hostess_role": "foreground_telemetry_ui_observer",
            "direct_ble_used": False,
            "broker_transport_used": True,
            "broker_transport_authority": "quest_broker_polar_pmd_provider",
        },
        "streams": [
            {
                "stream_id": "bio:polar_acc",
                "status": "pass",
                "frame_count": 2,
                "sample_count": 6,
                "broker_transport_used": True,
                "direct_ble_used": False,
            }
        ],
        "broker_report": {
            "status": "pass",
            "broker_connected": True,
            "frame_count": 2,
            "sample_count": 6,
            "direct_ble_used": False,
            "telemetry_ui_visualized": True,
        },
    }


if __name__ == "__main__":
    unittest.main()
