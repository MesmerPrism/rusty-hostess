from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools.hostessctl import hostessctl
from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.companion_catalog import (
    HOSTESS_COMPANION_CATALOG_SCHEMA,
    HOSTESS_COMPANION_CATALOG_VALIDATION_SCHEMA,
    build_companion_catalog_report,
    validate_companion_catalog_report,
)


class HostessCtlCompanionCatalogTests(unittest.TestCase):
    def test_catalog_loads_frontend_descriptors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_catalog_fixture_set(Path(tmpdir))
            args = catalog_args(
                out=str(Path(tmpdir) / "catalog.json"),
                hostess_descriptor=str(paths["module"]),
                gui_descriptors_root=str(paths["root"]),
            )

            report = build_companion_catalog_report(args, clock_ms_func=FixedClock())
            validation = validate_companion_catalog_report(report)

        self.assertEqual(report["$schema"], HOSTESS_COMPANION_CATALOG_SCHEMA)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["module_count"], 1)
        self.assertEqual(validation["workspace_count"], 1)
        self.assertEqual(validation["transport_count"], 1)

    def test_dispatch_command_writes_catalog_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_catalog_fixture_set(Path(tmpdir))
            out = Path(tmpdir) / "catalog.json"
            status = hostessctl.dispatch_command(
                catalog_args(
                    out=str(out),
                    hostess_descriptor=str(paths["module"]),
                    gui_descriptors_root=str(paths["root"]),
                    fail_on_error=True,
                )
            )
            report = read_json(out)
            validation = read_json(out.with_name("catalog.validation-report.json"))

        self.assertEqual(status, 0)
        self.assertEqual(report["$schema"], HOSTESS_COMPANION_CATALOG_SCHEMA)
        self.assertEqual(validation["$schema"], HOSTESS_COMPANION_CATALOG_VALIDATION_SCHEMA)
        self.assertEqual(validation["status"], "pass")

    def test_authority_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            descriptor_root = root / "descriptors"
            descriptor_root.mkdir()
            module_path = root / "module.json"
            write_json(module_path, minimal_module(authority_role="authority"))
            write_json(descriptor_root / "transport.json", minimal_transport())

            report = build_companion_catalog_report(
                catalog_args(
                    out=str(root / "catalog.json"),
                    hostess_descriptor=str(module_path),
                    gui_descriptors_root=str(descriptor_root),
                ),
                clock_ms_func=FixedClock(),
            )
            validation = validate_companion_catalog_report(report)

        self.assertEqual(validation["status"], "fail")
        self.assertTrue(any("may not claim authority" in error for error in validation["errors"]))

    def test_workspace_unknown_module_is_report_issue_and_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            descriptor_root = root / "descriptors"
            descriptor_root.mkdir()
            module_path = root / "module.json"
            workspace = minimal_workspace()
            workspace["workspace_id"] = "workspace.broken.unknown_module"
            workspace["modules"] = [
                {
                    "module_id": "companion.unknown.module",
                    "required": True,
                    "prominent": True,
                }
            ]
            write_json(module_path, minimal_module())
            write_json(descriptor_root / "transport.json", minimal_transport())
            write_json(descriptor_root / "workspace.json", workspace)

            report = build_companion_catalog_report(
                catalog_args(
                    out=str(root / "catalog.json"),
                    hostess_descriptor=str(module_path),
                    gui_descriptors_root=str(descriptor_root),
                ),
                clock_ms_func=FixedClock(),
            )
            validation = validate_companion_catalog_report(report)

        self.assertEqual(report["status"], "fail")
        issue = next(
            issue
            for issue in report["issues"]
            if issue["code"] == "hostess.issue.companion_catalog.workspace_unknown_module"
        )
        self.assertEqual(issue["workspace_id"], "workspace.broken.unknown_module")
        self.assertEqual(issue["module_id"], "companion.unknown.module")
        self.assertEqual(validation["status"], "fail")
        self.assertTrue(
            any("references unknown module companion.unknown.module" in error for error in validation["errors"])
        )

    def test_fail_on_error_still_blocks_invalid_catalog_in_validation_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            descriptor_root = root / "descriptors"
            descriptor_root.mkdir()
            module_path = root / "module.json"
            workspace = minimal_workspace()
            workspace["modules"] = [
                {
                    "module_id": "companion.unknown.module",
                    "required": True,
                    "prominent": True,
                }
            ]
            write_json(module_path, minimal_module())
            write_json(descriptor_root / "transport.json", minimal_transport())
            write_json(descriptor_root / "workspace.json", workspace)
            status = hostessctl.dispatch_command(
                catalog_args(
                    out=str(root / "catalog.json"),
                    hostess_descriptor=str(module_path),
                    gui_descriptors_root=str(descriptor_root),
                    fail_on_error=True,
                )
            )

        self.assertEqual(status, 2)

    def test_parser_accepts_companion_catalog_command(self) -> None:
        args = build_parser().parse_args(
            [
                "companion-catalog",
                "--out",
                "catalog.json",
                "--frontend",
                "makepad",
                "--gui-descriptors-root",
                "descriptors",
                "--fail-on-error",
            ]
        )

        self.assertEqual(args.command, "companion-catalog")
        self.assertEqual(args.frontend, "makepad")
        self.assertEqual(args.gui_descriptors_root, "descriptors")
        self.assertTrue(args.fail_on_error)


class FixedClock:
    def __call__(self) -> int:
        return 1782320000000


def write_catalog_fixture_set(root: Path) -> dict[str, Path]:
    descriptor_root = root / "descriptors"
    descriptor_root.mkdir()
    module_path = root / "module.json"
    write_json(module_path, minimal_module())
    write_json(descriptor_root / "transport.json", minimal_transport())
    write_json(descriptor_root / "workspace.json", minimal_workspace())
    return {
        "root": descriptor_root,
        "module": module_path,
    }


def minimal_module(*, authority_role: str = "inspector") -> dict[str, object]:
    return {
        "schema": "rusty.gui.companion.module_descriptor.v1",
        "module_id": "companion.readiness.preconditions",
        "title": "Readiness",
        "family": "readiness_preconditions",
        "owner_lane": "hostess",
        "authority_role": authority_role,
        "supported_frontends": ["wpf", "makepad", "cli"],
        "required_tools": [],
        "required_device_states": [],
        "required_transports": [
            {
                "id": "transport.adb_usb",
                "family": "adb",
                "required": True,
            }
        ],
        "readable_reports": [],
        "command_requests": [],
        "evidence_artifacts": [
            {
                "id": "evidence.hostess.readiness",
                "schema": "rusty.hostess.companion.readiness_report.v1",
                "owner_lane": "hostess",
                "redaction_required": False,
            }
        ],
        "remediation_actions": [],
        "action_policy": {
            "auto_run_checks": True,
            "state_changes_require_confirmation": True,
            "destructive_actions_allowed": False,
        },
        "sensitivity": ["public_safe"],
    }


def minimal_transport() -> dict[str, object]:
    return {
        "schema": "rusty.gui.companion.transport_capability.v1",
        "transport_id": "transport.adb_usb",
        "title": "ADB USB",
        "family": "adb",
        "plane": "setup",
        "delivery": "ordered_reliable",
        "payload_rate": "file_artifact",
        "authority_role": "adapter",
        "route_ids": ["bridge_route.device.adb.transport_only"],
        "required_evidence_stages": ["sent", "transport_ok"],
        "supported_frontends": ["wpf", "cli"],
        "strengths": ["serial-scoped validation"],
        "costs": ["transport success is not runtime proof"],
        "suitable_for": ["setup"],
        "not_suitable_for": ["frame streaming"],
        "sensitivity": ["public_safe"],
    }


def minimal_workspace() -> dict[str, object]:
    return {
        "schema": "rusty.gui.companion.workspace_descriptor.v1",
        "workspace_id": "workspace.hostess_makepad.validation",
        "title": "Hostess Makepad Validation",
        "supported_frontends": ["wpf", "makepad", "cli"],
        "modules": [
            {
                "module_id": "companion.readiness.preconditions",
                "required": True,
                "prominent": True,
            }
        ],
        "sensitivity": ["public_safe"],
    }


def catalog_args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "command": "companion-catalog",
        "out": "catalog.json",
        "validation_out": None,
        "frontend": "wpf",
        "hostess_descriptor": None,
        "gui_descriptors_root": None,
        "fail_on_error": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


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


if __name__ == "__main__":
    unittest.main()
