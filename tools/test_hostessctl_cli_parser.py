import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.makepad_pmb_setup import makepad_breath_scale_runtime_properties
from tools.hostessctl.native_breathing_room_setup import (
    NATIVE_BREATHING_ROOM_PROFILE_ID,
    NATIVE_BREATHING_ROOM_PARAMETERIZED_PROPERTIES,
    default_native_breathing_room_profile_path,
    build_native_breathing_room_setup_receipt,
)
from tools.hostessctl.pmb_native_receipts import PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER
from tools.hostessctl.pmb_support import PMB_STREAM_CONTRACT_AUTHORITY
from tools.hostessctl.pmb_android_routes import pmb_physical_live_start_command
from tools.hostessctl.pmb_support import (
    PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS,
    PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS,
)


class HostessCtlCliParserTests(unittest.TestCase):
    def build_parser(self):
        return build_hostessctl_parser(
            broker_package="test.broker",
            broker_port=18765,
            broker_local_forward_port=28765,
            makepad_android_package="test.makepad",
            makepad_android_xr_activity="test.makepad/.Xr",
            makepad_provider_package="test.provider",
            makepad_provider_activity="test.provider/.Provider",
        )

    def write_native_breathing_room_profile(self, path: Path) -> dict[str, str]:
        properties = {
            "debug.rustyquest.native_renderer.render.mode": "custom-stereo-projection",
            "debug.rustyquest.native_renderer.camera.output": "guide-public",
            "debug.rustyquest.native_renderer.guide.blur.enabled": "false",
            "debug.rustyquest.native_renderer.guide.resolution": "camera-native",
            "debug.rustyquest.native_renderer.hand_mesh.input.source": "disabled",
            "debug.rustyquest.native_renderer.environment_depth.mode": "disabled",
            "debug.rustyquest.native_renderer.environment_depth.high_rate_json_payload": "false",
            "debug.rustyquest.native_renderer.stimulus_volume.enabled": "false",
            "debug.rustyquest.native_renderer.private_layer.enabled": "false",
            "debug.rustyquest.native_renderer.projection.target.controls": "true",
            "debug.rustyquest.native_renderer.projection.target.scale": "1.0",
            "debug.rustyquest.native_renderer.projection.target.tuned.max.scale": "1.25",
            "debug.rustyquest.native_renderer.projection.target.min.scale": "0.05",
            "debug.rustyquest.native_renderer.projection.target.max.scale": "5.0",
            "debug.rustyquest.native_renderer.projection.target.offset.x.uv": "0.0",
            "debug.rustyquest.native_renderer.projection.target.offset.y.uv": "0.0",
            "debug.rustyquest.native_renderer.projection.target.joystick.controls": "true",
            "debug.rustyquest.native_renderer.projection.target.joystick.scale.rate_per_second": "0.45",
            "debug.rustyquest.native_renderer.projection.target.breath.bridge.mode": "manifold-state",
            "debug.rustyquest.native_renderer.projection.target.breath.state.stream": "stream.breath.state",
            "debug.rustyquest.native_renderer.projection.target.breath.value.stream": "stream.breath.state.value",
            "debug.rustyquest.native_renderer.projection.target.breath.inhale.seconds.min_to_max": "4.0",
            "debug.rustyquest.native_renderer.projection.target.breath.exhale.seconds.max_to_min": "4.0",
            "debug.rustyquest.native_renderer.projection.target.breath.synthetic.period.seconds": "6.0",
            "debug.rustyquest.native_renderer.projection.target.breath.high_rate_json_payload": "false",
            "debug.rustyquest.native_renderer.manifold.broker.host": "127.0.0.1",
            "debug.rustyquest.native_renderer.manifold.broker.port": "8765",
            "debug.rustyquest.native_renderer.manifold.broker.path": "/manifold/v1/events",
        }
        profile = {
            "schema": "rusty.quest.runtime_profile.v1",
            "profile_id": NATIVE_BREATHING_ROOM_PROFILE_ID,
            "target_platform": "quest",
            "owned_android_properties": list(properties.keys()),
            "set_properties": [
                {
                    "name": name,
                    "value": value,
                    "source_setting_id": name.removeprefix("debug.rustyquest."),
                }
                for name, value in properties.items()
            ],
        }
        path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        return properties

    def test_record_values_uses_injected_platform_defaults(self) -> None:
        args = self.build_parser().parse_args(
            [
                "record-values",
                "--target",
                "quest",
                "--value",
                "stream.motion.object_pose",
                "--out",
                "recording.json",
                "--packages-root",
                "packages",
                "--duration-seconds",
                "1",
            ]
        )

        self.assertEqual(args.command, "record-values")
        self.assertEqual(args.broker_package, "test.broker")
        self.assertEqual(args.broker_port, 18765)
        self.assertEqual(args.broker_local_port, 28765)
        self.assertEqual(args.makepad_provider_package, "test.provider")
        self.assertEqual(args.makepad_provider_activity, "test.provider/.Provider")

    def test_makepad_shell_contract_uses_injected_makepad_default(self) -> None:
        args = self.build_parser().parse_args(
            [
                "launch-makepad-shell-contract",
                "--target",
                "quest",
                "--launch-handoff",
                "handoff.json",
                "--out",
                "evidence.json",
            ]
        )

        self.assertEqual(args.command, "launch-makepad-shell-contract")
        self.assertEqual(args.makepad_package, "test.makepad")

    def test_questionnaire_open_block_cli_route(self) -> None:
        args = self.build_parser().parse_args(
            [
                "questionnaire-open-block",
                "--endpoint",
                "http://127.0.0.1:8787",
                "--block",
                "2",
                "--session-id",
                "session-1",
                "--participant-ref",
                "P001",
                "--language-code",
                "de",
            ]
        )

        self.assertEqual(args.command, "questionnaire-open-block")
        self.assertEqual(args.block, "2")
        self.assertEqual(args.session_id, "session-1")
        self.assertEqual(args.participant_ref, "P001")

    def test_pmb_physical_live_defaults_to_low_latency_breath_scale_profile(self) -> None:
        args = self.build_parser().parse_args(
            [
                "run-pmb-quest-physical-live",
                "--out",
                "evidence.json",
                "--packages-root",
                "packages",
                "--adb",
                "adb",
                "--serial",
                "serial",
            ]
        )

        self.assertEqual(args.makepad_pose_sample_hz, 72.0)
        self.assertEqual(args.makepad_breath_smoothing_alpha, 0.75)
        self.assertEqual(args.makepad_breath_smoothing_seconds, 0.03)
        self.assertEqual(
            args.pmb_controller_state_short_window_seconds,
            PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS,
        )
        self.assertEqual(
            args.pmb_controller_state_long_window_seconds,
            PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS,
        )
        self.assertEqual(args.app_receipt_policy, "makepad-feedback-receipt")

    def test_makepad_breath_smoothing_override_reaches_android_property(self) -> None:
        args = self.build_parser().parse_args(
            [
                "run-pmb-quest-physical-live",
                "--out",
                "evidence.json",
                "--packages-root",
                "packages",
                "--adb",
                "adb",
                "--serial",
                "serial",
                "--makepad-breath-scale-mode",
                "state-value",
                "--makepad-breath-smoothing-alpha",
                "0.9",
            ]
        )

        props = makepad_breath_scale_runtime_properties(args)

        self.assertEqual(
            props["debug.rustyquest.makepad.projection.target.breath.stream"],
            "stream.breath.state.value",
        )
        self.assertEqual(
            props["debug.rustyquest.makepad.projection.target.breath.smoothing.alpha"],
            "0.9",
        )

    def test_makepad_state_ramp_uses_raw_state_stream_and_spring_properties(self) -> None:
        args = self.build_parser().parse_args(
            [
                "run-pmb-quest-physical-live",
                "--out",
                "evidence.json",
                "--packages-root",
                "packages",
                "--adb",
                "adb",
                "--serial",
                "serial",
                "--makepad-breath-scale-mode",
                "state-ramp",
                "--makepad-breath-smoothing-seconds",
                "0.05",
                "--makepad-breath-state-inhale-threshold01",
                "0.8",
                "--makepad-breath-state-exhale-threshold01",
                "0.2",
            ]
        )

        props = makepad_breath_scale_runtime_properties(args)

        self.assertEqual(
            props["debug.rustyquest.makepad.projection.target.breath.stream"],
            "stream.breath.state",
        )
        self.assertEqual(
            props["debug.rustyquest.makepad.projection.target.breath.scale.mode"],
            "state-ramp",
        )
        self.assertEqual(
            props["debug.rustyquest.makepad.projection.target.breath.smoothing.seconds"],
            "0.05",
        )
        self.assertEqual(
            props["debug.rustyquest.makepad.projection.target.breath.state.inhale.threshold01"],
            "0.8",
        )
        self.assertEqual(
            props["debug.rustyquest.makepad.projection.target.breath.state.exhale.threshold01"],
            "0.2",
        )

    def test_pmb_controller_state_tuning_reaches_android_intent(self) -> None:
        args = self.build_parser().parse_args(
            [
                "run-pmb-quest-physical-live",
                "--out",
                "evidence.json",
                "--packages-root",
                "packages",
                "--adb",
                "adb",
                "--serial",
                "serial",
                "--pmb-controller-state-mode",
                "fixed-controller-orientation",
                "--pmb-controller-state-short-window-seconds",
                "2.5",
                "--pmb-controller-state-long-window-seconds",
                "12.0",
            ]
        )

        command = pmb_physical_live_start_command(args, "headset")

        self.assertEqual(
            command[command.index("pmb_controller_state_mode") + 1],
            "fixed-controller-orientation",
        )
        self.assertEqual(command[command.index("pmb_controller_state_short_window_s") + 1], "2.5")
        self.assertEqual(command[command.index("pmb_controller_state_long_window_s") + 1], "12.0")

    def test_native_breathing_room_setup_defaults_to_controller_without_polar(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "native-breathing-room.profile.json"
            profile_properties = self.write_native_breathing_room_profile(profile_path)
            args = self.build_parser().parse_args(
                [
                    "native-breathing-room",
                    "setup",
                    "--runtime-profile",
                    str(profile_path),
                    "--out",
                    "native-breathing-room.json",
                ]
            )

            receipt = build_native_breathing_room_setup_receipt(args)
        setprops = {item["name"]: item["value"] for item in receipt["set_properties"]}

        self.assertEqual(args.command, "native-breathing-room")
        self.assertEqual(args.native_breathing_room_command, "setup")
        self.assertEqual(receipt["mode"], "pmb-controller-state")
        self.assertFalse(receipt["polar_required"])
        self.assertFalse(receipt["controller_pmb_mode_polar_required"])
        self.assertEqual(receipt["pmb"]["breath_selected_source"], "controller")
        self.assertEqual(
            setprops["debug.rustyquest.native_renderer.projection.target.breath.bridge.mode"],
            "manifold-state",
        )
        self.assertEqual(
            setprops["debug.rustyquest.native_renderer.camera.output"],
            profile_properties["debug.rustyquest.native_renderer.camera.output"],
        )
        self.assertEqual(setprops["debug.rustyquest.native_renderer.hand_mesh.input.source"], "disabled")
        self.assertEqual(receipt["runtime_profile_property_count"], len(profile_properties))
        self.assertEqual(receipt["pmb_stream_contract_authority"], PMB_STREAM_CONTRACT_AUTHORITY)
        self.assertEqual(
            receipt["native_app_receipt_policy_streams"]["app_receipt_policy"],
            PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER,
        )
        self.assertEqual(
            receipt["native_app_receipt_policy_streams"]["state_stream"],
            "stream.breath.state",
        )
        self.assertEqual(
            receipt["native_app_receipt_policy_streams"]["state_value_stream"],
            "stream.breath.state.value",
        )
        self.assertFalse(any(key.startswith("debug.rustyquest.makepad.") for key in setprops))

    def test_native_breathing_room_state_value_setup_subscribes_processed_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "native-breathing-room.profile.json"
            self.write_native_breathing_room_profile(profile_path)
            args = self.build_parser().parse_args(
                [
                    "native-breathing-room",
                    "setup",
                    "--mode",
                    "pmb-state-value",
                    "--breath-selected-source",
                    "polar",
                    "--runtime-profile",
                    str(profile_path),
                    "--out",
                    "native-breathing-room.json",
                ]
            )

            receipt = build_native_breathing_room_setup_receipt(args)
        setprops = {item["name"]: item["value"] for item in receipt["set_properties"]}

        self.assertEqual(
            setprops["debug.rustyquest.native_renderer.projection.target.breath.bridge.mode"],
            "manifold-state-value",
        )
        self.assertEqual(
            receipt["pmb"]["subscriptions"][0]["params"]["stream"],
            "stream.breath.state.value",
        )

    def test_native_breathing_room_rejects_custom_stream_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "native-breathing-room.profile.json"
            self.write_native_breathing_room_profile(profile_path)
            args = self.build_parser().parse_args(
                [
                    "native-breathing-room",
                    "setup",
                    "--runtime-profile",
                    str(profile_path),
                    "--state-stream",
                    "stream.breath.custom_state",
                    "--out",
                    "native-breathing-room.json",
                ]
            )

            with self.assertRaisesRegex(ValueError, "canonical PMB stream contract"):
                build_native_breathing_room_setup_receipt(args)

    def test_native_breathing_room_setup_matches_canonical_rusty_quest_profile(self) -> None:
        profile_path = default_native_breathing_room_profile_path()
        if not profile_path.exists():
            self.skipTest("Rusty Quest sibling repo is not available")
        args = self.build_parser().parse_args(
            [
                "native-breathing-room",
                "setup",
                "--out",
                "native-breathing-room.json",
            ]
        )

        receipt = build_native_breathing_room_setup_receipt(args)
        setprop_names = {item["name"] for item in receipt["set_properties"]}
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        canonical_names = {item["name"] for item in profile["set_properties"]}
        canonical_values = {item["name"]: str(item["value"]) for item in profile["set_properties"]}
        setprops = {item["name"]: item["value"] for item in receipt["set_properties"]}
        parameterized = set(NATIVE_BREATHING_ROOM_PARAMETERIZED_PROPERTIES)

        self.assertEqual(setprop_names, canonical_names)
        self.assertGreaterEqual(receipt["runtime_profile_property_count"], 55)
        self.assertEqual(
            receipt["runtime_profile_sha256"],
            hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(receipt["runtime_profile_authority"], "rusty-quest-runtime-profile")
        self.assertEqual(
            set(receipt["runtime_profile_parameterized_properties"]),
            parameterized,
        )
        self.assertEqual(
            {
                name: value
                for name, value in setprops.items()
                if name not in parameterized
            },
            {
                name: value
                for name, value in canonical_values.items()
                if name not in parameterized
            },
        )
        self.assertIn("debug.rustyquest.native_renderer.camera.output", setprop_names)
        self.assertIn("debug.rustyquest.native_renderer.guide.resolution", setprop_names)
        self.assertIn("debug.rustyquest.native_renderer.environment_depth.mode", setprop_names)
        self.assertIn("debug.rustyquest.native_renderer.private_layer.enabled", setprop_names)
        self.assertIn("debug.rustyquest.native_renderer.stimulus_volume.enabled", setprop_names)


if __name__ == "__main__":
    unittest.main()
