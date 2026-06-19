import unittest

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.makepad_pmb_setup import makepad_breath_scale_runtime_properties
from tools.hostessctl.native_breathing_room_setup import (
    build_native_breathing_room_setup_receipt,
)
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
        args = self.build_parser().parse_args(
            [
                "native-breathing-room",
                "setup",
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
        self.assertFalse(any(key.startswith("debug.rustyquest.makepad.") for key in setprops))

    def test_native_breathing_room_state_value_setup_subscribes_processed_stream(self) -> None:
        args = self.build_parser().parse_args(
            [
                "native-breathing-room",
                "setup",
                "--mode",
                "pmb-state-value",
                "--breath-selected-source",
                "polar",
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


if __name__ == "__main__":
    unittest.main()
