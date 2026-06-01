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
            self.assertEqual(host_run["host_profile"], "host.headset")
            self.assertEqual(host_run["app_id"], "app.rusty_hostess_t.quest")
            self.assertFalse(host_run["result_fields"]["controller_input_used"])
            self.assertFalse(host_run["result_fields"]["physical_controller_input_used"])
            self.assertTrue(host_run["result_fields"]["manual_controller_trial_required"])

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


def write_projected_motion_package_tree(packages_root: Path) -> None:
    package_root = packages_root / "packages" / "projected-motion-breath"
    write_json(
        package_root / "manifests" / "package.manifold.json",
        {"$schema": "rusty.manifold.package.manifest.v1", "package_id": "package.projected_motion_breath"},
    )
    for subdir, filename in [
        ("streams", "breath-volume.json"),
        ("modules", "projected-motion-breath.json"),
        ("commands", "breath-set-profile.json"),
    ]:
        write_json(
            package_root / "manifests" / subdir / filename,
            {"id": filename.removesuffix(".json")},
        )


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
