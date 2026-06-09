from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.hostessctl import hostessctl


class HostessCtlMakepadContractTests(unittest.TestCase):
    def test_plan_only_stages_clean_makepad_shell_contract_launch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "makepad-shell-contract-receipt.json"
            launch_path = root / "makepad-shell-launch-handoff.json"
            out = root / "launch" / "makepad-shell-launch.json"
            write_json(contract_path, accepted_contract_receipt())
            write_json(launch_path, ready_launch_handoff(contract_path))

            status = hostessctl.launch_makepad_shell_contract(
                launch_args(launch_path, out, plan_only=True)
            )

            self.assertEqual(status, 0)
            evidence = read_json(out)
            validation = read_json(out.with_name("makepad-shell-launch.validation-report.json"))
            host_run = read_json(out.with_name("makepad-shell-launch.host-run-evidence.json"))
            device_launch = read_json(
                out.with_name("makepad-shell-launch.device-launch-handoff.json")
            )
            self.assertEqual(
                evidence["$schema"],
                "rusty.hostess.makepad_shell_contract_launch_evidence.v1",
            )
            self.assertEqual(evidence["status"], "ready")
            self.assertTrue(evidence["device_required"])
            self.assertFalse(evidence["adb_execution_performed"])
            self.assertFalse(evidence["push_performed"])
            self.assertFalse(evidence["launch_started"])
            self.assertFalse(evidence["permission_pregrant_performed"])
            self.assertEqual(evidence["permission_grant_records"], [])
            self.assertFalse(evidence["visual_profile_setprops_performed"])
            self.assertEqual(evidence["visual_profile_processing_layer"], "peripheral-stretch")
            self.assertEqual(
                evidence["visual_profile_source_sampling_mode"],
                "target-local-raster",
            )
            self.assertEqual(
                evidence["visual_profile_projection_border_policy"],
                "passthrough-underlay",
            )
            self.assertEqual(
                evidence["visual_profile_makepad_projection_border_policy"],
                "passthrough-underlay",
            )
            self.assertFalse(evidence["runtime_observation_poll_performed"])
            self.assertEqual(evidence["runtime_observation_pull_count"], 0)
            self.assertFalse(evidence["makepad_runtime_capability_receipt_pulled"])
            self.assertTrue(evidence["final_clean_makepad_app_requires_xr"])
            self.assertTrue(evidence["makepad_controller_pose_required"])
            self.assertTrue(evidence["makepad_camera_hwb_projection_required"])
            self.assertTrue(evidence["makepad_custom_camera_projection_required"])
            self.assertEqual(
                evidence["makepad_activity"],
                f"{hostessctl.MAKEPAD_ANDROID_PACKAGE}/.MakepadAppXr",
            )
            self.assertFalse(evidence["old_makepad_provider_route_changed"])
            self.assertFalse(evidence["record_values_provider_route_changed"])
            self.assertEqual(validation["status"], "pass")
            self.assertEqual(host_run["status"], "ready")
            self.assertTrue(
                Path(evidence["local_device_makepad_shell_contract_receipt_path"]).is_file()
            )
            self.assertEqual(
                device_launch["makepad_contract_reader_input_path"],
                evidence["device_makepad_shell_contract_receipt_path"],
            )
            self.assertEqual(
                device_launch["source_makepad_shell_contract_receipt_path"],
                evidence["device_makepad_shell_contract_receipt_path"],
            )
            self.assertEqual(
                device_launch["host_local_makepad_shell_contract_receipt_path"],
                str(contract_path),
            )
            self.assertEqual(
                evidence["device_makepad_shell_runtime_capability_receipt_relative_path"],
                "files/hostess-t/shell/makepad-shell-runtime-capability-receipt.json",
            )
            self.assertFalse(evidence["descriptor_fallback_used"])
            self.assertFalse(evidence["legacy_reference_dependency_used"])

    def test_plan_only_rejects_descriptor_fallback_launch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "makepad-shell-contract-receipt.json"
            launch_path = root / "makepad-shell-launch-handoff.json"
            out = root / "launch" / "makepad-shell-launch.json"
            contract = accepted_contract_receipt()
            write_json(contract_path, contract)
            launch = ready_launch_handoff(contract_path)
            launch["descriptor_fallback_used"] = True
            write_json(launch_path, launch)

            status = hostessctl.launch_makepad_shell_contract(
                launch_args(launch_path, out, plan_only=True)
            )

            self.assertEqual(status, 2)
            evidence = read_json(out)
            validation = read_json(out.with_name("makepad-shell-launch.validation-report.json"))
            self.assertEqual(evidence["status"], "rejected")
            self.assertEqual(
                evidence["issue_code"],
                "hostess.issue.makepad_shell_contract_launch_legacy_or_fallback",
            )
            self.assertTrue(evidence["descriptor_fallback_used"])
            self.assertFalse(evidence["legacy_reference_dependency_used"])
            self.assertFalse(evidence["adb_execution_performed"])
            self.assertEqual(validation["status"], "fail")

    def test_actual_launch_uses_app_private_run_as_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "makepad-shell-contract-receipt.json"
            launch_path = root / "makepad-shell-launch-handoff.json"
            out = root / "launch" / "makepad-shell-launch.json"
            write_json(contract_path, accepted_contract_receipt())
            write_json(launch_path, ready_launch_handoff(contract_path))
            seen_commands: list[list[str]] = []
            written_files: dict[str, dict[str, object]] = {}

            def fake_run(
                command: list[str],
                *,
                allow_failure: bool = False,
                cwd: Path | None = None,
            ) -> subprocess.CompletedProcess[str]:
                seen_commands.append(command)
                return subprocess.CompletedProcess(command, 0)

            def fake_write_run_as_file(
                args: argparse.Namespace,
                package: str,
                relative_path: str,
                payload: bytes,
            ) -> None:
                self.assertEqual(package, hostessctl.MAKEPAD_ANDROID_PACKAGE)
                written_files[relative_path] = json.loads(payload.decode("utf-8"))

            def fake_wait_run_as_file(
                args: argparse.Namespace,
                package: str,
                relative_path: str,
                timeout_seconds: float,
            ) -> None:
                self.assertIn(
                    relative_path,
                    {
                        "files/hostess-t/shell/makepad-shell-contract-read-receipt.json",
                        "files/hostess-t/shell/makepad-shell-runtime-capability-receipt.json",
                    },
                )

            def fake_pull_run_as_file(
                args: argparse.Namespace,
                package: str,
                relative_path: str,
                output_path: Path,
            ) -> None:
                if relative_path == "files/hostess-t/shell/makepad-shell-contract-read-receipt.json":
                    write_json(
                        output_path,
                        {
                            "$schema": "rusty.hostess.makepad_shell_contract_read_receipt.v1",
                            "status": "read",
                            "issue_code": None,
                        },
                    )
                    return
                self.assertEqual(
                    relative_path,
                    "files/hostess-t/shell/makepad-shell-runtime-capability-receipt.json",
                )
                write_json(
                    output_path,
                    {
                        "$schema": (
                            "rusty.hostess.makepad_shell_runtime_capability_receipt.v1"
                        ),
                        "status": "incomplete",
                        "issue_code": (
                            "hostess.issue.makepad_shell_runtime_capability_xr_controller_hwb_missing"
                        ),
                        "final_clean_makepad_app_requires_xr": True,
                        "xr_session_required": True,
                        "controller_pose_required": True,
                        "camera_hardware_buffer_projection_required": True,
                        "custom_camera_projection_required": True,
                        "breath_feedback_required": True,
                        "broker_transport_required": True,
                        "implemented_capabilities": [
                            "shell_contract_reader",
                            "app_private_contract_receipt_writer",
                            "host_telemetry_snapshot_viewer",
                            "render_export_writer",
                            "makepad_xr_root",
                        ],
                        "missing_capabilities": [
                            "xr_session",
                            "xr_controller_pose_provider",
                            "custom_camera_projection_from_hwb",
                        ],
                        "makepad_xr_root_registered": True,
                        "xr_update_observed": False,
                        "xr_update_count": 0,
                        "in_xr_mode_observed": False,
                        "controller_pose_provider_observed": False,
                        "left_controller_active": False,
                        "right_controller_active": False,
                    },
                )

            with (
                patch.object(hostessctl, "run", side_effect=fake_run),
                patch.object(
                    hostessctl,
                    "write_android_run_as_file",
                    side_effect=fake_write_run_as_file,
                ),
                patch.object(
                    hostessctl,
                    "wait_for_android_run_as_file",
                    side_effect=fake_wait_run_as_file,
                ),
                patch.object(
                    hostessctl,
                    "pull_android_run_as_file",
                    side_effect=fake_pull_run_as_file,
                ),
            ):
                status = hostessctl.launch_makepad_shell_contract(
                    launch_args(launch_path, out, plan_only=False)
                )

            self.assertEqual(status, 0)
            evidence = read_json(out)
            self.assertEqual(evidence["status"], "completed")
            self.assertTrue(evidence["adb_execution_performed"])
            self.assertTrue(evidence["app_private_write_performed"])
            self.assertFalse(evidence["push_performed"])
            self.assertTrue(evidence["permission_pregrant_performed"])
            self.assertIn("android.permission.CAMERA", evidence["permission_grants_attempted"])
            self.assertIn("horizonos.permission.HEADSET_CAMERA", evidence["permission_grants_attempted"])
            self.assertTrue(evidence["visual_profile_setprops_performed"])
            self.assertEqual(evidence["visual_profile_processing_layer"], "peripheral-stretch")
            self.assertEqual(
                evidence["visual_profile_source_sampling_mode"],
                "target-local-raster",
            )
            self.assertEqual(
                evidence["visual_profile_projection_border_policy"],
                "passthrough-underlay",
            )
            self.assertEqual(
                evidence["visual_profile_makepad_projection_border_policy"],
                "passthrough-underlay",
            )
            self.assertFalse(evidence["runtime_observation_poll_performed"])
            self.assertEqual(evidence["runtime_observation_pull_count"], 1)
            self.assertEqual(
                evidence["makepad_activity"],
                f"{hostessctl.MAKEPAD_ANDROID_PACKAGE}/.MakepadAppXr",
            )
            self.assertTrue(evidence["makepad_runtime_capability_receipt_pulled"])
            self.assertEqual(evidence["makepad_runtime_capability_receipt_status"], "incomplete")
            self.assertIn("makepad_xr_root", evidence["makepad_runtime_implemented_capabilities"])
            self.assertIn("xr_session", evidence["makepad_runtime_missing_capabilities"])
            self.assertTrue(evidence["makepad_xr_root_registered"])
            self.assertFalse(evidence["makepad_xr_update_observed"])
            self.assertEqual(evidence["makepad_xr_update_count"], 0)
            self.assertFalse(evidence["makepad_controller_pose_provider_observed"])
            self.assertTrue(evidence["makepad_controller_pose_required"])
            self.assertTrue(evidence["makepad_camera_hwb_projection_required"])
            self.assertEqual(
                evidence["next_required_action"],
                "implement_clean_makepad_xr_controller_hwb_runtime",
            )
            self.assertEqual(evidence["device_makepad_shell_staging_mode"], "run_as_app_private")
            self.assertFalse(any("push" in command for command in seen_commands))
            self.assertTrue(
                any(
                    len(command) >= 6
                    and command[-4:-2] == ["pm", "grant"]
                    and command[-2] == hostessctl.MAKEPAD_ANDROID_PACKAGE
                    for command in seen_commands
                )
            )
            setprops = {
                command[-2]: command[-1]
                for command in seen_commands
                if len(command) >= 7 and command[-4:-2] == ["shell", "setprop"]
            }
            self.assertEqual(
                setprops["debug.rusty.processing.layer"],
                "peripheral-stretch",
            )
            self.assertEqual(
                setprops["debug.rusty.camera.source.sampling.mode"],
                "target-local-raster",
            )
            self.assertEqual(
                setprops["debug.rusty.projection.border.policy"],
                "passthrough-underlay",
            )
            self.assertEqual(
                setprops["debug.rusty.projection.border.opacity"],
                "0.0",
            )
            self.assertEqual(
                setprops["debug.rusty.makepad.projection.border.policy"],
                "passthrough-underlay",
            )
            self.assertEqual(
                setprops["debug.rusty.makepad.projection.border.opacity"],
                "0.0",
            )
            self.assertFalse(any(key.startswith("debug.rustyxr.") for key in setprops))
            self.assertIn(
                "files/hostess-t/shell/makepad-shell-contract-receipt.json",
                written_files,
            )
            staged_launch = written_files[
                "files/hostess-t/shell/makepad-shell-launch-handoff.json"
            ]
            self.assertEqual(
                staged_launch["makepad_contract_reader_input_path"],
                evidence["device_makepad_shell_contract_receipt_path"],
            )
            self.assertTrue(
                str(staged_launch["makepad_contract_reader_input_path"]).startswith(
                    f"/data/user/0/{hostessctl.MAKEPAD_ANDROID_PACKAGE}/"
                )
            )
            self.assertTrue(
                any(command[-2:] == ["am", "start"] or "am" in command for command in seen_commands)
            )


def launch_args(launch_handoff: Path, out: Path, *, plan_only: bool) -> argparse.Namespace:
    return argparse.Namespace(
        target="quest",
        launch_handoff=str(launch_handoff),
        out=str(out),
        adb=None if plan_only else "adb",
        serial=None if plan_only else "quest-serial",
        makepad_package=hostessctl.MAKEPAD_ANDROID_PACKAGE,
        makepad_activity=None,
        remote_dir=None,
        wait_seconds=20.0,
        runtime_observation_seconds=0.0,
        runtime_observation_poll_ms=750.0,
        skip_pregrant_permissions=False,
        plan_only=plan_only,
    )


def accepted_contract_receipt() -> dict[str, object]:
    return {
        "$schema": "rusty.hostess.makepad_shell_contract_receipt.v1",
        "receipt_id": "hostess.makepad_shell_contract_receipt.test",
        "status": "accepted",
        "issue_code": None,
        "makepad_contract_input_accepted": True,
        "makepad_shell_contract_ready": True,
        "descriptor_fallback_used": False,
        "legacy_reference_dependency_used": False,
        "manifold_shell_handoff_selected": True,
        "manifold_shell_handoff_review_ready": True,
        "selected_handoff_id": "manifold.shell_handoff.test",
        "selected_shell_app_id": "app.hostess_t_makepad",
    }


def ready_launch_handoff(contract_path: Path) -> dict[str, object]:
    return {
        "$schema": "rusty.hostess.makepad_shell_launch_handoff_receipt.v1",
        "receipt_id": "hostess.makepad_shell_launch_handoff_receipt.test",
        "status": "ready",
        "issue_code": None,
        "makepad_contract_reader_required": True,
        "makepad_contract_reader_ready": True,
        "makepad_contract_reader_input_path": str(contract_path),
        "makepad_launch_handoff_ready": True,
        "makepad_launch_request_ready": True,
        "expected_reader_contract_schema": "rusty.hostess.makepad_shell_contract_receipt.v1",
        "descriptor_fallback_used": False,
        "legacy_reference_dependency_used": False,
        "selected_handoff_id": "manifold.shell_handoff.test",
        "selected_shell_app_id": "app.hostess_t_makepad",
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
