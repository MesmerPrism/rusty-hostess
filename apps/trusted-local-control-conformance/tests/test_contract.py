from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import _app_path  # noqa: F401 - repo-root unittest discovery bootstrap

from trusted_local_control_conformance.conformance import exercise_fixture
from trusted_local_control_conformance.contract import (
    COMMANDS,
    build_descriptor,
    validate_descriptor,
    validate_quest_registry,
    validate_web_assets,
)


APP_ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_descriptor_is_closed_and_disabled(self) -> None:
        descriptor = build_descriptor()

        self.assertEqual(validate_descriptor(descriptor), [])
        self.assertFalse(descriptor["default_enabled"])
        self.assertEqual(descriptor["commands"], list(COMMANDS))
        self.assertFalse(descriptor["transport"]["confidentiality"])
        self.assertEqual(descriptor["transport"]["test_bind_host"], "127.0.0.1")
        self.assertEqual(descriptor["transport"]["test_bind_port"], 0)

    def test_descriptor_damage_is_rejected(self) -> None:
        descriptor = build_descriptor()
        descriptor["commands"].append("execute")
        descriptor["transport"]["cors"] = True
        descriptor["default_enabled"] = True

        issues = validate_descriptor(descriptor)

        self.assertIn("descriptor.closed_command_registry", issues)
        self.assertIn("descriptor.transport.cors", issues)
        self.assertIn("descriptor.default_enabled", issues)

    def test_packaged_fixture_assets_have_no_external_or_dynamic_code(self) -> None:
        self.assertEqual(validate_web_assets(APP_ROOT / "web"), [])

    def test_quest_registry_exact_command_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            quest_root = Path(temporary)
            registry_path = (
                quest_root
                / "apps"
                / "spatial-video-control-example-android"
                / "contracts"
                / "trusted_local_http_v1.commands.registry.json"
            )
            registry_path.parent.mkdir(parents=True)
            commands = []
            for command in COMMANDS:
                payload = {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["video_id"] if command == "select_video" else [],
                }
                if command == "select_video":
                    payload["properties"] = {"video_id": {"type": "string"}}
                commands.append(
                    {
                        "id": command,
                        "kind": (
                            "effect"
                            if command in {"select_video", "play", "pause"}
                            else "query"
                        ),
                        "payload": payload,
                    }
                )
            registry_path.write_text(
                json.dumps(
                    {
                        "schema": "rusty.quest.trusted_local_http.command_registry.v1",
                        "protocol": "trusted_local_http_v1",
                        "payload_max_bytes": 4096,
                        "request_id_pattern": "^[a-z0-9][a-z0-9-]{15,63}$",
                        "commands": commands,
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(validate_quest_registry(quest_root), [])

            commands[-1]["id"] = "execute"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema": "rusty.quest.trusted_local_http.command_registry.v1",
                        "protocol": "trusted_local_http_v1",
                        "payload_max_bytes": 4096,
                        "request_id_pattern": "^[a-z0-9][a-z0-9-]{15,63}$",
                        "commands": commands,
                    }
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "quest_registry.commands.closed_order",
                validate_quest_registry(quest_root),
            )

    def test_offline_fixture_exercises_all_required_gates(self) -> None:
        checks = exercise_fixture()

        self.assertGreaterEqual(len(checks), 17)
        self.assertTrue(all(checks.values()), checks)


if __name__ == "__main__":
    unittest.main()
