from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.hostessctl import hostessctl


class HostessCtlProjectedMotionReplayTests(unittest.TestCase):
    def test_run_pmb_replay_writes_desktop_execution_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            out = root / "evidence" / "pmb-desktop-replay.json"
            core_report = ready_pmb_core_report()
            completed = subprocess.CompletedProcess(
                args=["cargo", "run"],
                returncode=0,
                stdout=f"ignored cargo line\n{json.dumps(core_report)}\n",
                stderr="",
            )

            with patch.object(hostessctl, "run_captured", return_value=completed):
                status = hostessctl.run_pmb_replay_capture(
                    argparse.Namespace(
                        target="desktop",
                        out=str(out),
                        packages_root=str(packages_root),
                        cargo="cargo",
                    )
                )

            self.assertEqual(status, 0)
            evidence = json.loads(out.read_text(encoding="utf-8"))
            validation = json.loads(
                out.with_name("pmb-desktop-replay.validation-report.json").read_text(
                    encoding="utf-8"
                )
            )
            host_run = json.loads(
                out.with_name("pmb-desktop-replay.host-run-evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                evidence["$schema"],
                "rusty.hostess.projected_motion_breath.desktop_replay_execution_evidence.v1",
            )
            self.assertEqual(evidence["status"], "pass")
            self.assertTrue(evidence["execution"]["execution_performed"])
            self.assertTrue(evidence["execution"]["runtime_execution_performed"])
            self.assertFalse(evidence["execution"]["platform_execution_performed"])
            self.assertFalse(evidence["execution"]["quest_execution_performed"])
            self.assertFalse(evidence["execution"]["apk_build_performed"])
            self.assertEqual(
                evidence["core_report_summary"]["checked_adapter_normalization_cases"],
                3,
            )
            self.assertEqual(validation["status"], "pass")
            self.assertEqual(host_run["status"], "pass")
            self.assertEqual(host_run["package_ids"], ["package.projected_motion_breath"])
            self.assertTrue(out.with_name("pmb-desktop-replay.stdout.txt").exists())
            self.assertTrue(out.with_name("pmb-desktop-replay.stderr.txt").exists())
            self.assertTrue(
                out.with_name("pmb-desktop-replay.core-validation-report.json").exists()
            )

    def test_run_pmb_replay_blocks_when_fixture_counts_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            out = root / "evidence" / "pmb-desktop-replay.json"
            core_report = ready_pmb_core_report()
            core_report["checked_adapter_normalization_cases"] = 0
            completed = subprocess.CompletedProcess(
                args=["cargo", "run"],
                returncode=0,
                stdout=json.dumps(core_report),
                stderr="",
            )

            with patch.object(hostessctl, "run_captured", return_value=completed):
                status = hostessctl.run_pmb_replay_capture(
                    argparse.Namespace(
                        target="desktop",
                        out=str(out),
                        packages_root=str(packages_root),
                        cargo="cargo",
                    )
                )

            self.assertEqual(status, 2)
            validation = json.loads(
                out.with_name("pmb-desktop-replay.validation-report.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(validation["status"], "fail")
            self.assertTrue(
                any(
                    check["check_id"] == "hostess.check.pmb_desktop_replay.core_counts"
                    and check["status"] == "fail"
                    for check in validation["checks"]
                )
            )
            self.assertFalse(out.with_name("pmb-desktop-replay.host-run-evidence.json").exists())

    def test_run_pmb_live_route_self_test_writes_non_live_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            out = root / "evidence" / "pmb-live-route-self-test.json"
            route_report = ready_pmb_live_route_report()
            completed = subprocess.CompletedProcess(
                args=["cargo", "run"],
                returncode=0,
                stdout=f"{json.dumps(route_report)}\n",
                stderr="",
            )

            with patch.object(hostessctl, "run_captured", return_value=completed):
                status = hostessctl.run_pmb_live_route_self_test(
                    argparse.Namespace(
                        out=str(out),
                        packages_root=str(packages_root),
                        cargo="cargo",
                    )
                )

            self.assertEqual(status, 0)
            evidence = json.loads(out.read_text(encoding="utf-8"))
            validation = json.loads(
                out.with_name("pmb-live-route-self-test.validation-report.json").read_text(
                    encoding="utf-8"
                )
            )
            host_run = json.loads(
                out.with_name("pmb-live-route-self-test.host-run-evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                evidence["$schema"],
                "rusty.hostess.projected_motion_breath.live_broker_route_self_test_evidence.v1",
            )
            self.assertEqual(evidence["status"], "pass")
            self.assertTrue(evidence["execution"]["plan_only"])
            self.assertFalse(evidence["execution"]["broker_transport_used"])
            self.assertFalse(evidence["execution"]["live_sensor_used"])
            self.assertFalse(evidence["execution"]["quest_execution_performed"])
            self.assertEqual(
                set(evidence["route_report_summary"]["input_stream_ids"]),
                {"bio:polar_acc", "stream.motion.object_pose"},
            )
            self.assertEqual(
                evidence["route_report_summary"]["makepad_subscription"]["stream"],
                "stream.breath.feedback_state",
            )
            self.assertEqual(evidence["route_report_summary"]["receipt_count"], 2)
            self.assertEqual(validation["status"], "pass")
            self.assertEqual(host_run["status"], "pass")
            self.assertFalse(host_run["result_fields"]["live_sensor_used"])

    def test_run_pmb_shell_handoff_writes_package_only_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            out = root / "evidence" / "pmb-shell-handoff.json"

            status = hostessctl.run_pmb_shell_handoff(
                argparse.Namespace(
                    out=str(out),
                    packages_root=str(packages_root),
                    handoff=None,
                )
            )

            self.assertEqual(status, 0)
            evidence = json.loads(out.read_text(encoding="utf-8"))
            validation = json.loads(
                out.with_name("pmb-shell-handoff.validation-report.json").read_text(
                    encoding="utf-8"
                )
            )
            host_run = json.loads(
                out.with_name("pmb-shell-handoff.host-run-evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                evidence["$schema"],
                "rusty.hostess.projected_motion_breath.shell_handoff_validation_evidence.v1",
            )
            self.assertEqual(evidence["status"], "pass")
            self.assertFalse(evidence["execution"]["runtime_execution_performed"])
            self.assertFalse(evidence["execution"]["broker_transport_used"])
            self.assertFalse(evidence["execution"]["downstream_shell_runtime_used"])
            self.assertFalse(evidence["execution"]["legacy_app_dependency_used"])
            self.assertFalse(evidence["execution"]["legacy_rusty_xr_repo_used"])
            binding_pairs = {
                (binding["stream_id"], binding["direction"])
                for binding in evidence["shell_handoff"]["binding_pairs"]
            }
            self.assertEqual(
                binding_pairs,
                {
                    ("stream.motion.object_pose", "publish"),
                    ("stream.breath.feedback_state", "subscribe"),
                    ("stream.breath.feedback_receipt", "publish"),
                },
            )
            self.assertIn(
                "stream.breath.feedback_receipt",
                evidence["package_contract"]["exported_stream_ids"],
            )
            self.assertIn(
                "stream.breath.feedback_receipt",
                evidence["package_contract"]["feedback_sink_provides_streams"],
            )
            self.assertEqual(validation["status"], "pass")
            self.assertEqual(host_run["status"], "pass")
            self.assertEqual(
                host_run["validation_slot_id"],
                "host_run.slot.projected_motion_breath.shell_handoff",
            )
            self.assertFalse(host_run["result_fields"]["legacy_app_dependency_used"])

    def test_pmb_shell_handoff_rejects_missing_feedback_receipt_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            package_root = packages_root / "packages" / "projected-motion-breath"
            handoff_path = package_root / "fixtures" / "valid" / "shell-handoff-loopback.json"
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            handoff["stream_bindings"] = [
                binding
                for binding in handoff["stream_bindings"]
                if binding["stream_id"] != "stream.breath.feedback_receipt"
            ]
            damaged_handoff_path = root / "damaged-shell-handoff.json"
            write_json(damaged_handoff_path, handoff)
            out = root / "evidence" / "pmb-shell-handoff.json"

            status = hostessctl.run_pmb_shell_handoff(
                argparse.Namespace(
                    out=str(out),
                    packages_root=str(packages_root),
                    handoff=str(damaged_handoff_path),
                )
            )

            self.assertEqual(status, 2)
            validation = json.loads(
                out.with_name("pmb-shell-handoff.validation-report.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(validation["status"], "fail")
            self.assertTrue(
                any(
                    check["check_id"] == "hostess.check.pmb_shell_handoff.required_bindings"
                    and check["status"] == "fail"
                    for check in validation["checks"]
                )
            )
            self.assertFalse(out.with_name("pmb-shell-handoff.host-run-evidence.json").exists())

    def test_pmb_live_route_self_test_rejects_missing_receipts(self) -> None:
        evidence = {
            "$schema": "rusty.hostess.projected_motion_breath.live_broker_route_self_test_evidence.v1",
            "status": "pass",
            "execution": {
                "execution_performed": True,
                "runtime_execution_performed": True,
                "processor_core_executed": True,
                "plan_only": True,
                "platform_execution_performed": False,
                "device_required": False,
                "android_execution_performed": False,
                "quest_execution_performed": False,
                "apk_build_performed": False,
                "openxr_runtime_used": False,
                "adb_used": False,
                "broker_transport_used": False,
                "live_sensor_used": False,
            },
            "route_report_summary": {
                "input_stream_ids": ["bio:polar_acc", "stream.motion.object_pose"],
                "output_stream_ids": ["stream.breath.volume", "stream.breath.feedback_state"],
                "source_route_count": 2,
                "feedback_sample_count": 2,
                "receipt_count": 0,
                "makepad_subscription": {
                    "command": "subscribe",
                    "stream": "stream.breath.feedback_state",
                },
            },
            "scorecard": {"status": "pass"},
        }

        validation = hostessctl.validate_pmb_live_route_self_test_evidence(evidence)

        self.assertEqual(validation["status"], "fail")
        self.assertTrue(
            any(
                check["check_id"] == "hostess.check.pmb_live_route.feedback_ack"
                and check["status"] == "fail"
                for check in validation["checks"]
            )
        )

    def test_run_pmb_replay_requires_projected_motion_package_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pmb-desktop-replay.json"

            with self.assertRaises(SystemExit):
                hostessctl.run_pmb_replay_capture(
                    argparse.Namespace(
                        target="desktop",
                        out=str(out),
                        packages_root=str(Path(tmp) / "missing-packages"),
                        cargo="cargo",
                    )
                )

    def test_validate_android_pmb_replay_writes_host_run_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            package_root = packages_root / "packages" / "projected-motion-breath"
            package = hostessctl.projected_motion_package_snapshot(package_root)
            evidence = ready_pmb_android_evidence(package, target="quest", host_profile="headset")
            out = root / "evidence" / "pmb-quest-replay.json"
            out.parent.mkdir(parents=True)
            out.write_text(json.dumps(evidence), encoding="utf-8")
            validation_path = out.with_name("pmb-quest-replay.validation-report.json")

            validation = hostessctl.validate_pmb_android_replay_execution_evidence(
                evidence,
                package_root=package_root,
                target="quest",
                host_profile="headset",
            )
            validation_path.write_text(json.dumps(validation), encoding="utf-8")
            hostessctl.write_pmb_android_host_run_evidence(
                out,
                validation_path,
                evidence,
                "quest",
                "headset",
            )

            self.assertEqual(validation["status"], "pass")
            host_run = json.loads(
                out.with_name("pmb-quest-replay.host-run-evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(host_run["status"], "pass")
            self.assertEqual(host_run["host_profile"], "host.headset")
            self.assertEqual(host_run["app_id"], "app.rusty_hostess_t.quest")
            self.assertEqual(host_run["package_ids"], ["package.projected_motion_breath"])

    def test_validate_android_pmb_replay_rejects_package_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            package_root = packages_root / "packages" / "projected-motion-breath"
            package = hostessctl.projected_motion_package_snapshot(package_root)
            package["package_manifest_sha256"] = "mismatch"
            evidence = ready_pmb_android_evidence(package, target="quest", host_profile="headset")

            validation = hostessctl.validate_pmb_android_replay_execution_evidence(
                evidence,
                package_root=package_root,
                target="quest",
                host_profile="headset",
            )

            self.assertEqual(validation["status"], "fail")
            self.assertTrue(
                any(
                    check["check_id"] == "hostess.check.pmb_android_replay.package_manifest_hash"
                    and check["status"] == "fail"
                    for check in validation["checks"]
                )
            )

    def test_validate_pmb_controller_preflight_writes_host_run_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            package_root = packages_root / "packages" / "projected-motion-breath"
            package = hostessctl.projected_motion_package_snapshot(package_root)
            evidence = ready_pmb_controller_preflight_evidence(
                package,
                target="quest",
                host_profile="headset",
            )
            out = root / "evidence" / "pmb-quest-controller-preflight.json"
            out.parent.mkdir(parents=True)
            out.write_text(json.dumps(evidence), encoding="utf-8")
            validation_path = out.with_name("pmb-quest-controller-preflight.validation-report.json")

            validation = hostessctl.validate_pmb_controller_preflight_evidence(
                evidence,
                package_root=package_root,
                target="quest",
                host_profile="headset",
            )
            validation_path.write_text(json.dumps(validation), encoding="utf-8")
            hostessctl.write_pmb_controller_preflight_host_run_evidence(
                out,
                validation_path,
                evidence,
                "quest",
                "headset",
            )

            self.assertEqual(validation["status"], "pass")
            host_run = json.loads(
                out.with_name("pmb-quest-controller-preflight.host-run-evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(host_run["status"], "pass")
            self.assertEqual(host_run["validation_slot_id"], "host_run.slot.projected_motion_breath.quest_controller_preflight")

    def test_validate_pmb_quest_simulated_live_writes_host_run_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            package_root = packages_root / "packages" / "projected-motion-breath"
            package = hostessctl.projected_motion_package_snapshot(package_root)
            evidence = ready_pmb_quest_simulated_live_evidence(package)
            out = root / "evidence" / "pmb-quest-simulated-live.json"
            out.parent.mkdir(parents=True)
            out.write_text(json.dumps(evidence), encoding="utf-8")
            validation_path = out.with_name("pmb-quest-simulated-live.validation-report.json")

            validation = hostessctl.validate_pmb_quest_simulated_live_evidence(
                evidence,
                package_root=package_root,
                target="quest",
                host_profile="headset",
            )
            validation_path.write_text(json.dumps(validation), encoding="utf-8")
            hostessctl.write_pmb_quest_simulated_live_host_run_evidence(
                out,
                validation_path,
                evidence,
                "quest",
                "headset",
            )

            self.assertEqual(validation["status"], "pass")
            host_run = json.loads(
                out.with_name("pmb-quest-simulated-live.host-run-evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(host_run["status"], "pass")
            self.assertEqual(
                host_run["validation_slot_id"],
                "host_run.slot.projected_motion_breath.quest_simulated_live",
            )
            self.assertTrue(host_run["result_fields"]["pmd_computed_on_quest"])
            self.assertFalse(host_run["result_fields"]["pmd_computed_on_pc"])
            self.assertEqual(host_run["host_profile"], "host.headset")
            self.assertEqual(host_run["app_id"], "app.rusty_hostess_t.quest")
            self.assertFalse(host_run["result_fields"]["controller_input_used"])
            self.assertFalse(host_run["result_fields"]["physical_controller_input_used"])
            self.assertTrue(host_run["result_fields"]["manual_controller_trial_required"])

    def test_validate_pmb_quest_physical_live_writes_host_run_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            package_root = packages_root / "packages" / "projected-motion-breath"
            package = hostessctl.projected_motion_package_snapshot(package_root)
            evidence = ready_pmb_quest_physical_live_evidence(package)
            out = root / "evidence" / "pmb-quest-physical-live.json"
            out.parent.mkdir(parents=True)
            out.write_text(json.dumps(evidence), encoding="utf-8")
            validation_path = out.with_name("pmb-quest-physical-live.validation-report.json")

            validation = hostessctl.validate_pmb_quest_physical_live_evidence(
                evidence,
                package_root=package_root,
                target="quest",
                host_profile="headset",
            )
            validation_path.write_text(json.dumps(validation), encoding="utf-8")
            hostessctl.write_pmb_quest_physical_live_host_run_evidence(
                out,
                validation_path,
                evidence,
                "quest",
                "headset",
            )

            self.assertEqual(validation["status"], "pass")
            host_run = json.loads(
                out.with_name("pmb-quest-physical-live.host-run-evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(host_run["status"], "pass")
            self.assertEqual(
                host_run["validation_slot_id"],
                "host_run.slot.projected_motion_breath.quest_physical_live",
            )
            self.assertTrue(host_run["result_fields"]["pmd_computed_on_quest"])
            self.assertFalse(host_run["result_fields"]["pmd_computed_on_pc"])
            self.assertTrue(host_run["result_fields"]["physical_polar_ble_used"])
            self.assertTrue(host_run["result_fields"]["physical_controller_input_used"])
            self.assertFalse(host_run["result_fields"]["simulated_polar_provider_used"])
            self.assertFalse(host_run["result_fields"]["simulated_controller_provider_used"])

    def test_pmb_quest_physical_live_defaults_to_background_service(self) -> None:
        args = argparse.Namespace(
            adb="adb",
            serial="quest-serial",
            broker_port=8765,
            duration_seconds=25.0,
            acc_rate=200,
            scan_timeout_seconds=30.0,
            controller_wait_seconds=10.0,
            feedback_publish_limit=12,
            receipt_listen_seconds=6.0,
            device_address="00:11:22:33:44:55",
            foreground_hostess=False,
        )

        command = hostessctl.pmb_physical_live_start_command(args, "headset")

        self.assertIn("start-foreground-service", command)
        self.assertNotIn("start", command[0:6])
        self.assertIn(hostessctl.ANDROID_PMB_PHYSICAL_LIVE_BACKGROUND_ACTION, command)
        self.assertIn(hostessctl.ANDROID_PMB_PHYSICAL_LIVE_SERVICE, command)
        self.assertNotIn(f"{hostessctl.ANDROID_PACKAGE}/.MainActivity", command)

    def test_pmb_quest_physical_live_foreground_override_uses_activity(self) -> None:
        args = argparse.Namespace(
            adb="adb",
            serial="quest-serial",
            broker_port=8765,
            duration_seconds=25.0,
            acc_rate=200,
            scan_timeout_seconds=30.0,
            controller_wait_seconds=10.0,
            feedback_publish_limit=12,
            receipt_listen_seconds=6.0,
            device_address="00:11:22:33:44:55",
            foreground_hostess=True,
        )

        command = hostessctl.pmb_physical_live_start_command(args, "headset")

        self.assertIn("start", command)
        self.assertNotIn("start-foreground-service", command)
        self.assertIn(hostessctl.ANDROID_PMB_PHYSICAL_LIVE_ACTION, command)
        self.assertIn(f"{hostessctl.ANDROID_PACKAGE}/.MainActivity", command)

    def test_configure_makepad_physical_pmb_provider_applies_visual_profile(self) -> None:
        commands: list[list[str]] = []

        def fake_run(
            command: list[str],
            *,
            allow_failure: bool = False,
            cwd: Path | None = None,
        ) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            return subprocess.CompletedProcess(command, 0)

        args = argparse.Namespace(
            adb="adb",
            serial="quest-serial",
            broker_port=8765,
            makepad_pose_controller="right",
            makepad_pose_kind="grip",
            makepad_pose_sample_hz=20.0,
            makepad_package=hostessctl.MAKEPAD_ANDROID_PACKAGE,
            makepad_activity=hostessctl.MAKEPAD_ANDROID_XR_ACTIVITY,
            makepad_settle_seconds=0.0,
        )

        with patch.object(hostessctl, "run", side_effect=fake_run):
            hostessctl.configure_makepad_physical_pmb_provider(args)

        setprops = {
            command[-2]: command[-1]
            for command in commands
            if len(command) >= 7 and command[-4:-2] == ["shell", "setprop"]
        }
        self.assertEqual(
            setprops["debug.rusty.processing.layer"],
            "peripheral-stretch",
        )
        self.assertEqual(
            setprops["debug.rustyxr.processing.layer"],
            "peripheral-stretch",
        )
        self.assertEqual(
            setprops["debug.rusty.projection.border.policy"],
            "passthrough-underlay",
        )
        self.assertEqual(
            setprops["debug.rustyxr.camera.source.sampling.mode"],
            "target-local-raster",
        )
        self.assertEqual(
            setprops["debug.rustyxr.projection.border.policy"],
            "passthrough-underlay",
        )
        self.assertEqual(
            setprops["debug.rustyxr.projection.border.opacity"],
            "0.0",
        )
        self.assertEqual(
            setprops["debug.rustyxr.makepad.projection.border.policy"],
            "passthrough-underlay",
        )
        self.assertEqual(
            setprops["debug.rustyxr.makepad.projection.border.opacity"],
            "0.0",
        )
        self.assertEqual(
            setprops["debug.rusty.makepad.projection.target.joystick.controls"],
            "offset-scale",
        )
        self.assertEqual(
            setprops["debug.rustyxr.makepad.projection.target.joystick.controls"],
            "offset-scale",
        )

    def test_configure_makepad_controller_pose_provider_applies_visual_profile(self) -> None:
        actions: list[tuple[str, list[str]]] = []

        def fake_run_adb(
            label: str,
            command: list[str],
            *,
            allow_failure: bool = False,
        ) -> subprocess.CompletedProcess[str]:
            actions.append((label, command))
            return subprocess.CompletedProcess(command, 0)

        args = argparse.Namespace(
            adb="adb",
            serial="quest-serial",
            broker_port=8765,
            makepad_pose_controller="right",
            makepad_pose_kind="grip",
            makepad_pose_sample_hz=20.0,
            makepad_provider_package=hostessctl.MAKEPAD_ANDROID_PACKAGE,
            makepad_provider_activity=hostessctl.MAKEPAD_ANDROID_XR_ACTIVITY,
        )

        hostessctl.configure_makepad_controller_pose_provider(args, fake_run_adb)

        setprops = {
            command[-2]: command[-1]
            for _label, command in actions
            if len(command) >= 7 and command[-4:-2] == ["shell", "setprop"]
        }
        self.assertEqual(
            setprops["debug.rusty.processing.layer"],
            "peripheral-stretch",
        )
        self.assertEqual(
            setprops["debug.rustyxr.processing.layer"],
            "peripheral-stretch",
        )
        self.assertEqual(
            setprops["debug.rusty.projection.border.policy"],
            "passthrough-underlay",
        )
        self.assertEqual(
            setprops["debug.rustyxr.camera.source.sampling.mode"],
            "target-local-raster",
        )
        self.assertEqual(
            setprops["debug.rustyxr.projection.border.policy"],
            "passthrough-underlay",
        )
        self.assertEqual(
            setprops["debug.rustyxr.projection.border.opacity"],
            "0.0",
        )
        self.assertEqual(
            setprops["debug.rustyxr.makepad.projection.border.policy"],
            "passthrough-underlay",
        )
        self.assertEqual(
            setprops["debug.rustyxr.makepad.projection.border.opacity"],
            "0.0",
        )
        self.assertEqual(
            setprops["debug.rusty.makepad.projection.target.joystick.controls"],
            "offset-scale",
        )
        self.assertEqual(
            setprops["debug.rustyxr.makepad.projection.target.joystick.controls"],
            "offset-scale",
        )

    def test_validate_pmb_quest_physical_live_rejects_pc_or_simulated_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            package_root = packages_root / "packages" / "projected-motion-breath"
            package = hostessctl.projected_motion_package_snapshot(package_root)
            evidence = ready_pmb_quest_physical_live_evidence(package)
            evidence["execution"]["pmd_computed_on_quest"] = False
            evidence["execution"]["pmd_computed_on_pc"] = True
            evidence["execution"]["simulated_polar_provider_used"] = True

            validation = hostessctl.validate_pmb_quest_physical_live_evidence(
                evidence,
                package_root=package_root,
                target="quest",
                host_profile="headset",
            )

            self.assertEqual(validation["status"], "fail")
            failed_checks = {
                check["check_id"]
                for check in validation["checks"]
                if check["status"] == "fail"
            }
            self.assertIn("hostess.check.pmb_quest_physical_live.quest_authority", failed_checks)
            self.assertIn("hostess.check.pmb_quest_physical_live.not_simulated", failed_checks)

    def test_validate_pmb_controller_preflight_rejects_live_controller_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages_root = root / "rusty-manifold-packages"
            write_projected_motion_package_tree(packages_root)
            package_root = packages_root / "packages" / "projected-motion-breath"
            package = hostessctl.projected_motion_package_snapshot(package_root)
            evidence = ready_pmb_controller_preflight_evidence(
                package,
                target="quest",
                host_profile="headset",
            )
            evidence["execution"]["controller_input_used"] = True

            validation = hostessctl.validate_pmb_controller_preflight_evidence(
                evidence,
                package_root=package_root,
                target="quest",
                host_profile="headset",
            )

            self.assertEqual(validation["status"], "fail")
            self.assertTrue(
                any(
                    check["check_id"] == "hostess.check.pmb_controller_preflight.non_human_gate"
                    and check["status"] == "fail"
                    for check in validation["checks"]
                )
            )


def ready_pmb_core_report() -> dict[str, object]:
    return {
        "schema": "rusty.manifold.projected_motion_breath.core_validation_report.v1",
        "package_root": "packages/projected-motion-breath",
        "status": "pass",
        "checked_profiles": 1,
        "checked_command_payloads": 5,
        "checked_damaged_command_payloads": 6,
        "checked_source_bindings": 4,
        "checked_damaged_source_bindings": 2,
        "checked_adapter_normalization_cases": 3,
        "checked_damaged_adapter_normalization_cases": 2,
        "checked_cases": 2,
        "checked_damaged_cases": 2,
        "issues": [],
    }


def ready_pmb_controller_preflight_report() -> dict[str, object]:
    return {
        "schema": "rusty.manifold.projected_motion_breath.controller_preflight_report.v1",
        "package_root": "packages/projected-motion-breath",
        "status": "pass",
        "preflight_id": "preflight.projected_motion_breath.headset_controller_pose.non_human",
        "provider_id": "provider.headset.controller_pose.preflight",
        "provider_kind": "headset_controller_pose",
        "binding_id": "binding.projected_motion_breath.headset_controller_pose.preflight",
        "selected_adapter_id": "adapter.projected_motion_breath.xr_controller_pose_shape",
        "selected_source_kind": "xr_controller_pose",
        "source_payload_kind": "object_pose",
        "input_stream_id": "stream.motion.object_pose",
        "output_stream_id": "stream.motion.object_pose",
        "source_id": "source.headset.controller.right.preflight",
        "frame_id": "frame.headset.stage",
        "sample_count": 3,
        "normalized_sample_count": 3,
        "estimate_count": 3,
        "processor_core_executed": True,
        "runtime_execution_performed": True,
        "provider_boundary_exercised": True,
        "controller_provider_route_ready": True,
        "headset_controller_shape_used": True,
        "physical_controller_input_used": False,
        "controller_input_used": False,
        "manual_controller_trial_required": True,
        "estimates": [
            {
                "sample_index": 0,
                "phase": "pause",
                "volume01": 0.5,
                "tracking01": 0.98,
                "quality": "stable",
            },
            {
                "sample_index": 1,
                "phase": "inhale",
                "volume01": 0.833,
                "tracking01": 0.98,
                "quality": "stable",
            },
            {
                "sample_index": 2,
                "phase": "exhale",
                "volume01": 0.333,
                "tracking01": 0.98,
                "quality": "stable",
            },
        ],
        "issues": [],
    }


def ready_pmb_live_route_report() -> dict[str, object]:
    return {
        "schema": "rusty.manifold.projected_motion_breath.live_route_report.v1",
        "package_root": "packages/projected-motion-breath",
        "status": "pass",
        "route_id": "route.projected_motion_breath.live_stream.polar_acc_controller_pose.self_test",
        "input_stream_ids": ["bio:polar_acc", "stream.motion.object_pose"],
        "normalized_stream_ids": ["stream.motion.vector3", "stream.motion.object_pose"],
        "output_stream_ids": ["stream.breath.volume", "stream.breath.feedback_state"],
        "processor_core_executed": True,
        "runtime_execution_performed": True,
        "external_transport_used": False,
        "live_sensor_used": False,
        "headset_execution_performed": False,
        "plan_only": True,
        "source_routes": [
            {"source_stream_id": "bio:polar_acc"},
            {"source_stream_id": "stream.motion.object_pose"},
        ],
        "breath_samples": [
            {"sequence_id": 1, "volume01": 0.5, "phase": "pause"},
            {"sequence_id": 2, "volume01": 0.75, "phase": "inhale"},
        ],
        "feedback_samples": [
            {"sequence_id": 1, "stream_id": "stream.breath.feedback_state"},
            {"sequence_id": 2, "stream_id": "stream.breath.feedback_state"},
        ],
        "receiver_subscription": {
            "command": "subscribe",
            "stream": "stream.breath.feedback_state",
            "receiver_id": "app.downstream_camera_shell.breath_feedback",
        },
        "receiver_receipts": [
            {
                "command": "breath_feedback.received",
                "schema": "rusty.manifold.breath.feedback_receipt.v1",
                "received_stream": "stream.breath.feedback_state",
                "received_sequence_id": 1,
                "receiver_id": "app.downstream_camera_shell.breath_feedback",
                "acknowledged": True,
            },
            {
                "command": "breath_feedback.received",
                "schema": "rusty.manifold.breath.feedback_receipt.v1",
                "received_stream": "stream.breath.feedback_state",
                "received_sequence_id": 2,
                "receiver_id": "app.downstream_camera_shell.breath_feedback",
                "acknowledged": True,
            },
        ],
        "issues": [],
    }


def ready_pmb_android_evidence(
    package: dict[str, object],
    *,
    target: str,
    host_profile: str,
) -> dict[str, object]:
    core_report = ready_pmb_core_report()
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_replay_execution_evidence.v1",
        "status": "pass",
        "target": target,
        "host_profile": host_profile,
        "started_at_utc": "2026-06-01T00:00:00+00:00",
        "ended_at_utc": "2026-06-01T00:00:01+00:00",
        "duration_ms": 1000,
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.quest" if target == "quest" else "app.rusty_hostess_t.android",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "execution": {
            "mode": "projected_motion_breath_android_synthetic_replay",
            "runtime_path": "rust.projected_motion_breath_core.v1",
            "core_report_artifact": "latest.core-validation-report.json",
            "processor_core_executed": True,
            "execution_performed": True,
            "runtime_execution_performed": True,
            "desktop_execution_performed": False,
            "platform_execution_performed": True,
            "android_execution_performed": True,
            "quest_execution_performed": target == "quest",
            "device_required": True,
            "apk_build_performed": False,
            "openxr_runtime_used": False,
            "live_sensor_used": False,
            "controller_input_used": False,
            "synthetic_replay": True,
            "app_private_evidence": True,
        },
        "core_report_summary": core_report,
        "commands": [
            {
                "command": "run_projected_motion_breath_core_validate_goldens_android",
                "status": "acknowledged",
                "runtime_path": "rust.projected_motion_breath_core.v1",
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.android_replay",
            "target_id": "hostess.projected_motion_breath.android_replay",
            "target_revision": 1,
            "status": "pass",
            "checks": [],
            "issues": [],
        },
    }


def ready_pmb_controller_preflight_evidence(
    package: dict[str, object],
    *,
    target: str,
    host_profile: str,
) -> dict[str, object]:
    report = ready_pmb_controller_preflight_report()
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_controller_preflight_evidence.v1",
        "status": "pass",
        "target": target,
        "host_profile": host_profile,
        "started_at_utc": "2026-06-01T00:00:00+00:00",
        "ended_at_utc": "2026-06-01T00:00:01+00:00",
        "duration_ms": 1000,
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.quest" if target == "quest" else "app.rusty_hostess_t.android",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "execution": {
            "mode": "projected_motion_breath_android_controller_preflight",
            "runtime_path": "rust.projected_motion_breath_core.v1",
            "controller_preflight_report_artifact": "latest.controller-preflight-report.json",
            "pmb_controller_path_preflight_passed": True,
            "processor_core_executed": True,
            "controller_provider_route_ready": True,
            "provider_boundary_exercised": True,
            "controller_shape_used": True,
            "quest_controller_shape_used": True,
            "execution_performed": True,
            "runtime_execution_performed": True,
            "desktop_execution_performed": False,
            "platform_execution_performed": True,
            "android_execution_performed": True,
            "quest_execution_performed": target == "quest",
            "device_required": True,
            "apk_build_performed": False,
            "openxr_runtime_used": False,
            "live_sensor_used": False,
            "physical_controller_input_used": False,
            "controller_input_used": False,
            "human_controller_trial_performed": False,
            "manual_controller_trial_required": True,
            "synthetic_replay": True,
            "preflight_fixture_packaged": True,
            "app_private_evidence": True,
        },
        "controller_preflight_report_summary": report,
        "commands": [
            {
                "command": "run_projected_motion_breath_controller_preflight_android",
                "status": "acknowledged",
                "runtime_path": "rust.projected_motion_breath_core.v1",
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.controller_preflight",
            "target_id": "hostess.projected_motion_breath.controller_preflight",
            "target_revision": 1,
            "status": "pass",
            "checks": [],
            "issues": [],
        },
    }


def ready_pmb_quest_simulated_live_evidence(package: dict[str, object]) -> dict[str, object]:
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_simulated_live_execution_evidence.v1",
        "status": "pass",
        "target": "quest",
        "host_profile": "headset",
        "started_at_utc": "2026-06-01T00:00:00+00:00",
        "ended_at_utc": "2026-06-01T00:00:01+00:00",
        "duration_ms": 1000,
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.quest",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "execution": {
            "mode": "projected_motion_breath_android_quest_simulated_live",
            "runtime_path": "rust.projected_motion_breath_core.v1",
            "route_report_artifact": "latest.live-route-report.json",
            "broker_publish_report_artifact": "latest.broker-publish-report.json",
            "processor_core_executed": True,
            "runtime_execution_performed": True,
            "desktop_execution_performed": False,
            "pc_processor_core_executed": False,
            "platform_execution_performed": True,
            "android_execution_performed": True,
            "quest_execution_performed": True,
            "device_required": True,
            "apk_build_performed": False,
            "openxr_runtime_used": False,
            "live_sensor_used": False,
            "physical_polar_ble_used": False,
            "simulated_polar_provider_used": True,
            "polar_transport_authority": "quest_app_simulated_polar_provider",
            "physical_controller_input_used": False,
            "controller_input_used": False,
            "simulated_controller_provider_used": True,
            "controller_transport_authority": "quest_app_simulated_controller_provider",
            "manual_polar_trial_required": True,
            "manual_controller_trial_required": True,
            "synthetic_live_route": True,
            "pmd_computed_on_quest": True,
            "pmd_computed_on_pc": False,
            "processor_authority": "quest_hostess_android_app",
            "broker_transport_used": True,
            "feedback_published_to_broker": True,
            "makepad_feedback_receipt_count": 6,
            "app_private_evidence": True,
        },
        "route_report_summary": {
            "schema": "rusty.manifold.projected_motion_breath.live_route_report.v1",
            "status": "pass",
            "route_id": "route.projected_motion_breath.live_stream.polar_acc_controller_pose.self_test",
            "input_stream_ids": ["bio:polar_acc", "stream.motion.object_pose"],
            "normalized_stream_ids": ["stream.motion.vector3", "stream.motion.object_pose"],
            "output_stream_ids": ["stream.breath.volume", "stream.breath.feedback_state"],
            "source_route_count": 2,
            "breath_sample_count": 6,
            "feedback_sample_count": 6,
            "processor_core_executed": True,
            "runtime_execution_performed": True,
            "plan_only_fixture": True,
            "source_routes": [
                {"source_stream_id": "bio:polar_acc"},
                {"source_stream_id": "stream.motion.object_pose"},
            ],
        },
        "broker_publish_summary": {
            "schema": "rusty.hostess.projected_motion_breath.quest_broker_publish_report.v1",
            "status": "pass",
            "broker_transport_used": True,
            "broker_connected": True,
            "breath_published_count": 6,
            "feedback_published_count": 6,
            "feedback_receipt_count": 6,
            "receipt_stream_id": "stream.breath.feedback_receipt",
        },
        "commands": [],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.android_simulated_live",
            "target_id": "hostess.projected_motion_breath.android_simulated_live",
            "target_revision": 1,
            "status": "pass",
            "checks": [],
            "issues": [],
        },
    }


def ready_pmb_quest_physical_live_evidence(package: dict[str, object]) -> dict[str, object]:
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_physical_live_execution_evidence.v1",
        "status": "pass",
        "target": "quest",
        "host_profile": "headset",
        "started_at_utc": "2026-06-01T00:00:00+00:00",
        "ended_at_utc": "2026-06-01T00:00:02+00:00",
        "duration_ms": 2000,
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.quest",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "execution": {
            "mode": "projected_motion_breath_android_quest_physical_live",
            "runtime_path": "rust.projected_motion_breath_core.v1",
            "input_capture_report_artifact": "latest.input-capture-report.json",
            "events_jsonl_artifact": "latest.transport-events.jsonl",
            "route_report_artifact": "latest.live-route-report.json",
            "broker_publish_report_artifact": "latest.broker-publish-report.json",
            "processor_core_executed": True,
            "runtime_execution_performed": True,
            "desktop_execution_performed": False,
            "pc_processor_core_executed": False,
            "platform_execution_performed": True,
            "android_execution_performed": True,
            "quest_execution_performed": True,
            "device_required": True,
            "apk_build_performed": False,
            "openxr_runtime_used": True,
            "live_sensor_used": True,
            "physical_polar_ble_used": True,
            "simulated_polar_provider_used": False,
            "polar_transport_authority": "quest_broker_polar_pmd_provider",
            "physical_controller_input_used": True,
            "controller_input_used": True,
            "simulated_controller_provider_used": False,
            "controller_transport_authority": "quest_makepad_xr_controller_pose_provider",
            "manual_polar_trial_required": False,
            "manual_controller_trial_required": False,
            "synthetic_live_route": False,
            "pmd_computed_on_quest": True,
            "pmd_computed_on_pc": False,
            "processor_authority": "quest_hostess_android_app",
            "broker_transport_used": True,
            "feedback_published_to_broker": True,
            "makepad_feedback_receipt_count": 6,
            "app_private_evidence": True,
        },
        "input_capture_summary": {
            "schema": "rusty.hostess.projected_motion_breath.quest_physical_input_capture_report.v1",
            "status": "pass",
            "broker_connected": True,
            "polar_start_status": "pass",
            "polar_stop_status": "pass",
            "polar_event_count": 12,
            "object_pose_event_count": 20,
            "active_tracked_connected_object_pose_count": 18,
            "physical_polar_ble_used": True,
            "physical_controller_input_used": True,
        },
        "route_report_summary": {
            "schema": "rusty.manifold.projected_motion_breath.live_route_report.v1",
            "status": "pass",
            "route_id": "route.projected_motion_breath.live_stream.polar_acc_controller_pose.self_test",
            "input_stream_ids": ["bio:polar_acc", "stream.motion.object_pose"],
            "normalized_stream_ids": ["stream.motion.vector3", "stream.motion.object_pose"],
            "output_stream_ids": ["stream.breath.volume", "stream.breath.feedback_state"],
            "source_route_count": 2,
            "breath_sample_count": 6,
            "feedback_sample_count": 6,
            "processor_core_executed": True,
            "runtime_execution_performed": True,
            "plan_only_fixture": False,
            "external_transport_used": True,
            "live_sensor_used": True,
            "source_routes": [
                {"source_stream_id": "bio:polar_acc"},
                {"source_stream_id": "stream.motion.object_pose"},
            ],
        },
        "broker_publish_summary": {
            "schema": "rusty.hostess.projected_motion_breath.quest_broker_publish_report.v1",
            "status": "pass",
            "broker_transport_used": True,
            "broker_connected": True,
            "breath_published_count": 6,
            "feedback_published_count": 6,
            "feedback_receipt_count": 6,
            "receipt_stream_id": "stream.breath.feedback_receipt",
        },
        "commands": [],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.android_physical_live",
            "target_id": "hostess.projected_motion_breath.android_physical_live",
            "target_revision": 1,
            "status": "pass",
            "checks": [],
            "issues": [],
        },
    }


def write_projected_motion_package_tree(packages_root: Path) -> None:
    package_root = packages_root / "packages" / "projected-motion-breath"
    write_json(
        package_root / "manifests" / "package.manifold.json",
        {
            "$schema": "rusty.manifold.package.manifest.v1",
            "package_id": "package.projected_motion_breath",
            "exports": {
                "modules": [
                    "module.motion.object_pose_provider",
                    "module.breath.projected_motion",
                    "module.breath.feedback_sink",
                ],
                "streams": [
                    "stream.motion.object_pose",
                    "stream.breath.volume",
                    "stream.breath.feedback_state",
                    "stream.breath.feedback_receipt",
                ],
                "commands": [
                    "command.breath.set_profile",
                    "command.breath.status",
                ],
            },
        },
    )
    for filename, stream_id in [
        ("object-pose.json", "stream.motion.object_pose"),
        ("breath-volume.json", "stream.breath.volume"),
        ("feedback-state.json", "stream.breath.feedback_state"),
        ("feedback-receipt.json", "stream.breath.feedback_receipt"),
    ]:
        write_json(
            package_root / "manifests" / "streams" / filename,
            {"$schema": "rusty.manifold.stream.manifest.v1", "stream_id": stream_id},
        )
    for filename, module_id, provides_streams in [
        (
            "object-pose-provider.json",
            "module.motion.object_pose_provider",
            ["stream.motion.object_pose"],
        ),
        (
            "projected-motion-breath.json",
            "module.breath.projected_motion",
            ["stream.breath.volume"],
        ),
        (
            "feedback-sink.json",
            "module.breath.feedback_sink",
            ["stream.breath.feedback_state", "stream.breath.feedback_receipt"],
        ),
    ]:
        write_json(
            package_root / "manifests" / "modules" / filename,
            {
                "$schema": "rusty.manifold.module.manifest.v1",
                "module_id": module_id,
                "provides_streams": provides_streams,
            },
        )
    for filename, command_id in [
        ("breath-set-profile.json", "command.breath.set_profile"),
        ("breath-status.json", "command.breath.status"),
    ]:
        write_json(
            package_root / "manifests" / "commands" / filename,
            {"$schema": "rusty.manifold.command.descriptor.v1", "command_id": command_id},
        )
    write_json(
        package_root / "fixtures" / "valid" / "shell-handoff-loopback.json",
        {
            "$schema": "rusty.manifold.shell.handoff.v1",
            "handoff_id": "shell_handoff.projected_motion_breath.loopback",
            "handoff_revision": 1,
            "target_host_profile": "host.headset",
            "shell_app_id": "app.downstream_shell",
            "validation_slot_id": "host_run.slot.projected_motion_breath.live_route_loopback",
            "stream_bindings": [
                {
                    "stream_id": "stream.motion.object_pose",
                    "direction": "publish",
                    "role": "shell.stream.controller_pose_provider",
                    "required": True,
                },
                {
                    "stream_id": "stream.breath.feedback_state",
                    "direction": "subscribe",
                    "role": "shell.stream.breath_feedback_receiver",
                    "required": True,
                },
                {
                    "stream_id": "stream.breath.feedback_receipt",
                    "direction": "publish",
                    "role": "shell.stream.breath_feedback_receipt",
                    "required": True,
                },
            ],
            "command_ids": ["command.breath.status"],
            "transport_offers": [
                {
                    "transport_id": "transport.shell_loopback",
                    "transport": "http",
                    "endpoint_id": "endpoint.shell_loopback",
                }
            ],
            "expected_scorecard_id": "scorecard.projected_motion_breath.shell_handoff_loopback",
        },
    )


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
