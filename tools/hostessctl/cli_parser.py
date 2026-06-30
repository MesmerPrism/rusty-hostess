"""Argument parser construction for the Hostess CLI."""

from __future__ import annotations

import argparse

from tools.hostessctl.companion_session_defaults import (
    DEFAULT_COMPANION_SESSION_AUTHORITY_WAIT_SECONDS,
    DEFAULT_COMPANION_SESSION_LAUNCH_SETTLE_SECONDS,
    DEFAULT_COMPANION_SESSION_PROCESS_WAIT_SECONDS,
    DEFAULT_COMPANION_SESSION_RUNTIME_SUBSCRIBER_RETRY_COUNT,
    DEFAULT_COMPANION_SESSION_RUNTIME_SUBSCRIBER_RETRY_WAIT_SECONDS,
    DEFAULT_COMPANION_SESSION_SOCKET_WAIT_SECONDS,
    DEFAULT_COMPANION_SESSION_WAIT_SECONDS,
)
from tools.hostessctl.pmb_support import (
    PMB_CONTROLLER_STATE_EXHALE_THRESHOLD,
    PMB_CONTROLLER_STATE_INHALE_THRESHOLD,
    PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS,
    PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD,
    PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES,
    PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS,
)

DEFAULT_MAKEPAD_POSE_SAMPLE_HZ = 72.0
DEFAULT_MAKEPAD_BREATH_SMOOTHING_ALPHA = 0.75
DEFAULT_MAKEPAD_BREATH_SMOOTHING_SECONDS = 0.03
DEFAULT_MAKEPAD_BREATH_STATE_INHALE_THRESHOLD01 = 0.75
DEFAULT_MAKEPAD_BREATH_STATE_EXHALE_THRESHOLD01 = 0.25
DEFAULT_PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS = PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS
DEFAULT_PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS = PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS
DEFAULT_PMB_CONTROLLER_STATE_INHALE_THRESHOLD = PMB_CONTROLLER_STATE_INHALE_THRESHOLD
DEFAULT_PMB_CONTROLLER_STATE_EXHALE_THRESHOLD = PMB_CONTROLLER_STATE_EXHALE_THRESHOLD
DEFAULT_PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES = PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES
DEFAULT_PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD = PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD


def add_makepad_breath_scale_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--makepad-breath-scale-mode",
        choices=["volume", "state-ramp", "state-value"],
        default="volume",
    )
    parser.add_argument(
        "--makepad-breath-inhale-seconds-min-to-max",
        type=float,
        default=4.0,
    )
    parser.add_argument(
        "--makepad-breath-exhale-seconds-max-to-min",
        type=float,
        default=4.0,
    )
    parser.add_argument(
        "--makepad-breath-smoothing-alpha",
        type=float,
        default=DEFAULT_MAKEPAD_BREATH_SMOOTHING_ALPHA,
    )
    parser.add_argument(
        "--makepad-breath-smoothing-seconds",
        type=float,
        default=DEFAULT_MAKEPAD_BREATH_SMOOTHING_SECONDS,
    )
    parser.add_argument(
        "--makepad-breath-state-inhale-threshold01",
        type=float,
        default=DEFAULT_MAKEPAD_BREATH_STATE_INHALE_THRESHOLD01,
    )
    parser.add_argument(
        "--makepad-breath-state-exhale-threshold01",
        type=float,
        default=DEFAULT_MAKEPAD_BREATH_STATE_EXHALE_THRESHOLD01,
    )


def build_hostessctl_parser(
    *,
    broker_package: str,
    broker_port: int,
    broker_local_forward_port: int,
    makepad_android_package: str,
    makepad_android_xr_activity: str,
    makepad_provider_package: str,
    makepad_provider_activity: str,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hostessctl")
    subcommands = parser.add_subparsers(dest="command", required=True)

    install = subcommands.add_parser("install-android")
    install.add_argument("--adb", required=True)
    install.add_argument("--serial", required=True)
    install.add_argument("--apk", required=True)

    run_live = subcommands.add_parser("run-live")
    run_live.add_argument("--target", choices=["desktop", "phone", "quest"], required=True)
    run_live.add_argument("--stream", choices=["hr_rr", "ecg", "acc", "coherence"])
    run_live.add_argument("--module", action="append", default=[])
    run_live.add_argument("--out", required=True)
    run_live.add_argument("--packages-root", required=True)
    run_live.add_argument("--duration-seconds", type=float, default=12.0)
    run_live.add_argument("--device-address")
    run_live.add_argument("--adb")
    run_live.add_argument("--serial")
    run_live.add_argument("--acc-rate", type=int, default=200)
    run_live.add_argument("--runtime-core", choices=["rust", "python-smoke"], default="rust")
    run_live.add_argument("--rmssd-baseline-ln-rmssd", type=float)
    run_live.add_argument("--rmssd-baseline-mean-ln-rmssd", type=float)
    run_live.add_argument("--rmssd-baseline-sd-ln-rmssd", type=float)
    run_live.add_argument("--rmssd-baseline-window-count", type=int)
    run_live.add_argument("--rmssd-baseline-source", default="explicit_baseline")
    run_live.add_argument("--telemetry-page", choices=["raw", "modules"], default="raw")

    run_replay = subcommands.add_parser("run-replay")
    run_replay.add_argument("--target", choices=["desktop", "phone", "quest"], default="desktop")
    run_replay.add_argument("--module", action="append", required=True)
    run_replay.add_argument("--out", required=True)
    run_replay.add_argument("--packages-root", required=True)
    run_replay.add_argument("--input")
    run_replay.add_argument("--adb")
    run_replay.add_argument("--serial")

    run_pmb_replay = subcommands.add_parser("run-pmb-replay")
    run_pmb_replay.add_argument("--target", choices=["desktop", "phone", "quest"], default="desktop")
    run_pmb_replay.add_argument("--out", required=True)
    run_pmb_replay.add_argument("--packages-root", required=True)
    run_pmb_replay.add_argument("--cargo", default="cargo")
    run_pmb_replay.add_argument("--adb")
    run_pmb_replay.add_argument("--serial")

    run_pmb_controller_preflight_parser = subcommands.add_parser("run-pmb-controller-preflight")
    run_pmb_controller_preflight_parser.add_argument("--target", choices=["phone", "quest"], required=True)
    run_pmb_controller_preflight_parser.add_argument("--out", required=True)
    run_pmb_controller_preflight_parser.add_argument("--packages-root", required=True)
    run_pmb_controller_preflight_parser.add_argument("--adb", required=True)
    run_pmb_controller_preflight_parser.add_argument("--serial", required=True)

    run_pmb_simulated_live_parser = subcommands.add_parser("run-pmb-quest-simulated-live")
    run_pmb_simulated_live_parser.add_argument("--target", choices=["quest"], default="quest")
    run_pmb_simulated_live_parser.add_argument("--out", required=True)
    run_pmb_simulated_live_parser.add_argument("--packages-root", required=True)
    run_pmb_simulated_live_parser.add_argument("--adb", required=True)
    run_pmb_simulated_live_parser.add_argument("--serial", required=True)
    run_pmb_simulated_live_parser.add_argument("--broker-package", default=broker_package)
    run_pmb_simulated_live_parser.add_argument("--broker-activity")
    run_pmb_simulated_live_parser.add_argument("--broker-port", type=int, default=broker_port)
    run_pmb_simulated_live_parser.add_argument("--makepad-package", default=makepad_android_package)
    run_pmb_simulated_live_parser.add_argument("--makepad-activity", default=makepad_android_xr_activity)
    run_pmb_simulated_live_parser.add_argument("--makepad-settle-seconds", type=float, default=8.0)
    run_pmb_simulated_live_parser.add_argument("--feedback-publish-limit", type=int, default=12)
    add_makepad_breath_scale_arguments(run_pmb_simulated_live_parser)
    run_pmb_simulated_live_parser.add_argument(
        "--breath-selected-source",
        choices=["auto", "polar", "controller"],
        default="auto",
    )
    run_pmb_simulated_live_parser.add_argument("--receipt-listen-seconds", type=float, default=6.0)
    run_pmb_simulated_live_parser.add_argument("--no-launch-broker", action="store_true")
    run_pmb_simulated_live_parser.add_argument("--no-launch-makepad", action="store_true")

    run_pmb_physical_live_parser = subcommands.add_parser("run-pmb-quest-physical-live")
    run_pmb_physical_live_parser.add_argument("--target", choices=["quest"], default="quest")
    run_pmb_physical_live_parser.add_argument("--out", required=True)
    run_pmb_physical_live_parser.add_argument("--packages-root", required=True)
    run_pmb_physical_live_parser.add_argument("--adb", required=True)
    run_pmb_physical_live_parser.add_argument("--serial", required=True)
    run_pmb_physical_live_parser.add_argument("--device-address")
    run_pmb_physical_live_parser.add_argument("--duration-seconds", type=float, default=30.0)
    run_pmb_physical_live_parser.add_argument("--acc-rate", type=int, default=200)
    run_pmb_physical_live_parser.add_argument("--scan-timeout-seconds", type=float, default=30.0)
    run_pmb_physical_live_parser.add_argument("--controller-wait-seconds", type=float, default=15.0)
    run_pmb_physical_live_parser.add_argument("--broker-package", default=broker_package)
    run_pmb_physical_live_parser.add_argument("--broker-activity")
    run_pmb_physical_live_parser.add_argument("--broker-port", type=int, default=broker_port)
    run_pmb_physical_live_parser.add_argument("--makepad-package", default=makepad_android_package)
    run_pmb_physical_live_parser.add_argument("--makepad-activity", default=makepad_android_xr_activity)
    run_pmb_physical_live_parser.add_argument("--makepad-settle-seconds", type=float, default=10.0)
    run_pmb_physical_live_parser.add_argument("--makepad-pose-controller", choices=["left", "right"], default="right")
    run_pmb_physical_live_parser.add_argument("--makepad-pose-kind", choices=["grip", "aim"], default="grip")
    run_pmb_physical_live_parser.add_argument(
        "--makepad-pose-sample-hz",
        type=float,
        default=DEFAULT_MAKEPAD_POSE_SAMPLE_HZ,
    )
    run_pmb_physical_live_parser.add_argument(
        "--pmb-controller-state-mode",
        choices=["projected-volume-delta", "fixed-controller-orientation"],
        default="projected-volume-delta",
    )
    run_pmb_physical_live_parser.add_argument(
        "--pmb-controller-state-short-window-seconds",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS,
    )
    run_pmb_physical_live_parser.add_argument(
        "--pmb-controller-state-long-window-seconds",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS,
    )
    run_pmb_physical_live_parser.add_argument(
        "--pmb-controller-state-inhale-threshold",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_INHALE_THRESHOLD,
    )
    run_pmb_physical_live_parser.add_argument(
        "--pmb-controller-state-exhale-threshold",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_EXHALE_THRESHOLD,
    )
    run_pmb_physical_live_parser.add_argument(
        "--pmb-controller-state-rotation-guard-degrees",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES,
    )
    run_pmb_physical_live_parser.add_argument(
        "--pmb-controller-state-moving-average-guard",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD,
    )
    run_pmb_physical_live_parser.add_argument("--feedback-publish-limit", type=int, default=24)
    add_makepad_breath_scale_arguments(run_pmb_physical_live_parser)
    run_pmb_physical_live_parser.add_argument(
        "--breath-selected-source",
        choices=["auto", "polar", "controller"],
        default="auto",
    )
    run_pmb_physical_live_parser.add_argument("--receipt-listen-seconds", type=float, default=6.0)
    run_pmb_physical_live_parser.add_argument(
        "--app-receipt-policy",
        choices=["makepad-feedback-receipt", "native-renderer-projection-target"],
        default="makepad-feedback-receipt",
    )
    run_pmb_physical_live_parser.add_argument("--run-until-stopped", action="store_true")
    run_pmb_physical_live_parser.add_argument("--no-launch-broker", action="store_true")
    run_pmb_physical_live_parser.add_argument("--no-launch-makepad", action="store_true")
    run_pmb_physical_live_parser.add_argument("--foreground-hostess", action="store_true")

    native_breathing_room = subcommands.add_parser("native-breathing-room")
    native_breathing_room_subcommands = native_breathing_room.add_subparsers(
        dest="native_breathing_room_command",
        required=True,
    )
    native_breathing_room_setup = native_breathing_room_subcommands.add_parser("setup")
    native_breathing_room_setup.add_argument("--out", required=True)
    native_breathing_room_setup.add_argument(
        "--mode",
        choices=["pmb-controller-state", "pmb-state", "pmb-state-value", "synthetic"],
        default="pmb-controller-state",
    )
    native_breathing_room_setup.add_argument(
        "--breath-selected-source",
        choices=["auto", "polar", "controller"],
        default="controller",
    )
    native_breathing_room_setup.add_argument("--base-scale", type=float, default=1.0)
    native_breathing_room_setup.add_argument("--runtime-profile")
    native_breathing_room_setup.add_argument("--tuned-max-scale", type=float, default=1.25)
    native_breathing_room_setup.add_argument("--joystick-rate", type=float, default=0.45)
    native_breathing_room_setup.add_argument("--inhale-seconds", type=float, default=4.0)
    native_breathing_room_setup.add_argument("--exhale-seconds", type=float, default=4.0)
    native_breathing_room_setup.add_argument("--synthetic-period-seconds", type=float, default=6.0)
    native_breathing_room_setup.add_argument("--state-stream", default="stream.breath.state")
    native_breathing_room_setup.add_argument("--value-stream", default="stream.breath.state.value")
    native_breathing_room_setup.add_argument("--broker-host", default="127.0.0.1")
    native_breathing_room_setup.add_argument("--broker-port", type=int, default=broker_port)
    native_breathing_room_setup.add_argument("--broker-path", default="/manifold/v1/events")
    native_breathing_room_setup.add_argument(
        "--pmb-controller-state-mode",
        choices=["projected-volume-delta", "fixed-controller-orientation"],
        default="projected-volume-delta",
    )
    native_breathing_room_setup.add_argument(
        "--pmb-controller-state-short-window-seconds",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS,
    )
    native_breathing_room_setup.add_argument(
        "--pmb-controller-state-long-window-seconds",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS,
    )
    native_breathing_room_setup.add_argument(
        "--pmb-controller-state-inhale-threshold",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_INHALE_THRESHOLD,
    )
    native_breathing_room_setup.add_argument(
        "--pmb-controller-state-exhale-threshold",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_EXHALE_THRESHOLD,
    )
    native_breathing_room_setup.add_argument(
        "--pmb-controller-state-rotation-guard-degrees",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES,
    )
    native_breathing_room_setup.add_argument(
        "--pmb-controller-state-moving-average-guard",
        type=float,
        default=DEFAULT_PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD,
    )
    native_breathing_room_setup.add_argument("--execute", action="store_true")
    native_breathing_room_setup.add_argument("--adb")
    native_breathing_room_setup.add_argument("--serial")

    observe_broker_telemetry = subcommands.add_parser("observe-broker-telemetry")
    observe_broker_telemetry.add_argument("--target", choices=["quest"], default="quest")
    observe_broker_telemetry.add_argument("--out", required=True)
    observe_broker_telemetry.add_argument("--adb", required=True)
    observe_broker_telemetry.add_argument("--serial", required=True)
    observe_broker_telemetry.add_argument("--duration-seconds", type=float, default=10.0)
    observe_broker_telemetry.add_argument("--device-address")
    observe_broker_telemetry.add_argument("--acc-rate", type=int, default=200)
    observe_broker_telemetry.add_argument("--scan-timeout-seconds", type=float, default=30.0)
    observe_broker_telemetry.add_argument("--broker-package", default=broker_package)
    observe_broker_telemetry.add_argument("--broker-activity")
    observe_broker_telemetry.add_argument("--broker-port", type=int, default=broker_port)
    observe_broker_telemetry.add_argument("--telemetry-page", choices=["raw", "modules"], default="raw")
    observe_broker_telemetry.add_argument("--no-launch-broker", action="store_true")
    observe_broker_telemetry.add_argument("--no-request-provider-start", action="store_true")
    observe_broker_telemetry.add_argument("--keep-provider-running", action="store_true")
    observe_broker_telemetry.add_argument("--render-out")

    run_pmb_live_route_self_test_parser = subcommands.add_parser("run-pmb-live-route-self-test")
    run_pmb_live_route_self_test_parser.add_argument("--out", required=True)
    run_pmb_live_route_self_test_parser.add_argument("--packages-root", required=True)
    run_pmb_live_route_self_test_parser.add_argument("--cargo", default="cargo")

    run_pmb_shell_handoff_parser = subcommands.add_parser("run-pmb-shell-handoff")
    run_pmb_shell_handoff_parser.add_argument("--out", required=True)
    run_pmb_shell_handoff_parser.add_argument("--packages-root", required=True)
    run_pmb_shell_handoff_parser.add_argument("--handoff")

    record_values = subcommands.add_parser("record-values")
    record_values.add_argument("--target", choices=["desktop", "phone", "quest"], required=True)
    record_values.add_argument("--value", action="append", required=True)
    record_values.add_argument("--out", required=True)
    record_values.add_argument("--packages-root", required=True)
    record_values.add_argument("--duration-seconds", type=float, required=True)
    record_values.add_argument("--device-address")
    record_values.add_argument("--adb")
    record_values.add_argument("--serial")
    record_values.add_argument("--acc-rate", type=int, default=200)
    record_values.add_argument("--broker-package", default=broker_package)
    record_values.add_argument("--broker-activity")
    record_values.add_argument("--broker-port", type=int, default=broker_port)
    record_values.add_argument("--broker-local-port", type=int, default=broker_local_forward_port)
    record_values.add_argument("--makepad-provider-package", default=makepad_provider_package)
    record_values.add_argument("--makepad-provider-activity", default=makepad_provider_activity)
    record_values.add_argument("--makepad-pose-controller", choices=["left", "right"], default="right")
    record_values.add_argument("--makepad-pose-kind", choices=["grip", "aim"], default="grip")
    record_values.add_argument(
        "--makepad-pose-sample-hz",
        type=float,
        default=DEFAULT_MAKEPAD_POSE_SAMPLE_HZ,
    )
    record_values.add_argument("--makepad-pose-ready-timeout-seconds", type=float, default=20.0)
    record_values.add_argument("--cargo", default="cargo")
    record_values.add_argument("--pmb-live-processor", action="store_true")
    record_values.add_argument("--pmb-feedback-publish-limit", type=int, default=24)
    add_makepad_breath_scale_arguments(record_values)
    record_values.add_argument("--pmb-breath-selected-source", choices=["auto", "polar", "controller"], default="auto")
    record_values.add_argument("--pmb-receipt-listen-seconds", type=float, default=3.0)
    record_values.add_argument("--no-launch-broker", action="store_true")
    record_values.add_argument("--no-launch-providers", action="store_true")
    record_values.add_argument("--runtime-core", choices=["rust", "python-smoke"], default="rust")
    record_values.add_argument("--telemetry-page", choices=["raw", "modules"], default="raw")
    record_values.add_argument("--plan-only", action="store_true")
    record_values.add_argument("--allow-blocked", action="store_true")

    bridge_route_evidence = subcommands.add_parser("emit-bridge-route-evidence")
    bridge_route_evidence.add_argument("--input", required=True)
    bridge_route_evidence.add_argument("--out", required=True)
    bridge_route_evidence.add_argument("--validation-out")
    bridge_route_evidence.add_argument("--route-descriptor")
    bridge_route_evidence.add_argument("--required-stage", action="append", default=[])

    bridge_command_request = subcommands.add_parser("emit-bridge-command-request")
    bridge_command_request.add_argument("--bridge-command", required=True)
    bridge_command_request.add_argument("--out", required=True)
    bridge_command_request.add_argument("--request-id")
    bridge_command_request.add_argument("--evidence-id")
    bridge_command_request.add_argument("--route-id", default="bridge_route.command.websocket.applied")
    bridge_command_request.add_argument("--required-stage", action="append", default=[])
    bridge_command_request.add_argument("--params-json")
    bridge_command_request.add_argument("--params-json-file")

    bridge_command = subcommands.add_parser("run-bridge-command")
    bridge_command.add_argument("--input", required=True)
    bridge_command.add_argument("--out", required=True)
    bridge_command.add_argument("--execution-out")
    bridge_command.add_argument("--validation-out")
    bridge_command.add_argument("--route-descriptor")
    bridge_command.add_argument("--broker-host", default="127.0.0.1")
    bridge_command.add_argument("--broker-port", type=int, default=broker_port)
    bridge_command.add_argument("--broker-path", default="/manifold/v1/events")
    bridge_command.add_argument("--connect-timeout-seconds", type=float, default=5.0)
    bridge_command.add_argument("--wait-seconds", type=float, default=5.0)
    bridge_command.add_argument(
        "--runtime-receipt-stream",
        default="stream.hostess.makepad.bridge_command.receipt",
    )
    bridge_command.add_argument("--no-runtime-receipt-subscribe", action="store_true")

    bridge_command_live_android = subcommands.add_parser("run-bridge-command-live-android")
    bridge_command_live_android.add_argument("--input", required=True)
    bridge_command_live_android.add_argument("--out", required=True)
    bridge_command_live_android.add_argument("--execution-out")
    bridge_command_live_android.add_argument("--validation-out")
    bridge_command_live_android.add_argument("--logcat-out")
    bridge_command_live_android.add_argument("--route-descriptor")
    bridge_command_live_android.add_argument("--adb", required=True)
    bridge_command_live_android.add_argument("--serial", required=True)
    bridge_command_live_android.add_argument("--broker-package", default=broker_package)
    bridge_command_live_android.add_argument("--broker-activity")
    bridge_command_live_android.add_argument("--broker-host", default="127.0.0.1")
    bridge_command_live_android.add_argument("--broker-port", type=int, default=broker_port)
    bridge_command_live_android.add_argument("--broker-local-port", type=int, default=broker_local_forward_port)
    bridge_command_live_android.add_argument("--broker-path", default="/manifold/v1/events")
    bridge_command_live_android.add_argument("--connect-timeout-seconds", type=float, default=5.0)
    bridge_command_live_android.add_argument("--wait-seconds", type=float, default=15.0)
    bridge_command_live_android.add_argument(
        "--runtime-receipt-stream",
        default="stream.hostess.makepad.bridge_command.receipt",
    )
    bridge_command_live_android.add_argument("--no-runtime-receipt-subscribe", action="store_true")
    bridge_command_live_android.add_argument("--makepad-package", default=makepad_android_package)
    bridge_command_live_android.add_argument("--makepad-activity", default=makepad_android_xr_activity)
    bridge_command_live_android.add_argument("--broker-process-wait-seconds", type=float, default=8.0)
    bridge_command_live_android.add_argument("--makepad-process-wait-seconds", type=float, default=8.0)
    bridge_command_live_android.add_argument("--socket-wait-seconds", type=float, default=8.0)
    bridge_command_live_android.add_argument("--launch-settle-seconds", type=float, default=8.0)
    bridge_command_live_android.add_argument("--runtime-subscriber-retry-count", type=int, default=1)
    bridge_command_live_android.add_argument(
        "--runtime-subscriber-retry-wait-seconds",
        type=float,
        default=5.0,
    )
    bridge_command_live_android.add_argument("--no-launch-broker", action="store_true")
    bridge_command_live_android.add_argument("--no-launch-makepad", action="store_true")
    bridge_command_live_android.add_argument("--no-wait-broker-process", action="store_true")
    bridge_command_live_android.add_argument("--no-wait-makepad-process", action="store_true")
    bridge_command_live_android.add_argument("--no-adb-forward-broker", action="store_true")

    bridge_command_android = subcommands.add_parser("run-bridge-command-android")
    bridge_command_android.add_argument("--input", required=True)
    bridge_command_android.add_argument("--out", required=True)
    bridge_command_android.add_argument("--execution-out")
    bridge_command_android.add_argument("--validation-out")
    bridge_command_android.add_argument("--logcat-out")
    bridge_command_android.add_argument("--route-descriptor")
    bridge_command_android.add_argument("--route-id")
    bridge_command_android.add_argument("--required-stage", action="append", default=[])
    bridge_command_android.add_argument("--broker-authority", action="store_true")
    bridge_command_android.add_argument("--broker-host", default="127.0.0.1")
    bridge_command_android.add_argument("--broker-port", type=int, default=broker_port)
    bridge_command_android.add_argument("--broker-local-port", type=int, default=broker_local_forward_port)
    bridge_command_android.add_argument("--broker-path", default="/manifold/v1/events")
    bridge_command_android.add_argument("--connect-timeout-seconds", type=float, default=5.0)
    bridge_command_android.add_argument("--authority-wait-seconds", type=float, default=5.0)
    bridge_command_android.add_argument("--adb-forward-broker", action="store_true")
    bridge_command_android.add_argument("--adb", required=True)
    bridge_command_android.add_argument("--serial", required=True)
    bridge_command_android.add_argument("--makepad-package", default=makepad_android_package)
    bridge_command_android.add_argument("--makepad-activity", default=makepad_android_xr_activity)
    bridge_command_android.add_argument("--remote-dir", default="files/hostess-t/settings")
    bridge_command_android.add_argument("--wait-seconds", type=float, default=20.0)
    bridge_command_android.add_argument("--no-launch", action="store_true")

    companion_catalog = subcommands.add_parser("companion-catalog")
    companion_catalog.add_argument("--out", required=True)
    companion_catalog.add_argument("--validation-out")
    companion_catalog.add_argument("--frontend", choices=["wpf", "makepad", "cli"], default="wpf")
    companion_catalog.add_argument("--hostess-descriptor")
    companion_catalog.add_argument("--gui-descriptors-root")
    companion_catalog.add_argument("--fail-on-error", action="store_true")

    companion_readiness = subcommands.add_parser("companion-readiness")
    companion_readiness.add_argument("--out", required=True)
    companion_readiness.add_argument("--validation-out")
    companion_readiness.add_argument(
        "--profile",
        choices=["basic", "hostess-makepad-quest"],
        default="basic",
    )
    companion_readiness.add_argument("--descriptor")
    companion_readiness.add_argument("--adb")
    companion_readiness.add_argument("--serial")
    companion_readiness.add_argument("--android-sdk")
    companion_readiness.add_argument("--jdk-home")
    companion_readiness.add_argument("--cargo", default="cargo")
    companion_readiness.add_argument("--cargo-makepad", default="cargo-makepad")
    companion_readiness.add_argument("--broker-host", default="127.0.0.1")
    companion_readiness.add_argument("--broker-port", type=int, default=broker_port)
    companion_readiness.add_argument("--broker-local-port", type=int, default=broker_local_forward_port)
    companion_readiness.add_argument("--broker-package", default=broker_package)
    companion_readiness.add_argument("--broker-activity")
    companion_readiness.add_argument("--check-broker", action="store_true")
    companion_readiness.add_argument("--require-broker", action="store_true")
    companion_readiness.add_argument("--makepad-package", default=makepad_android_package)
    companion_readiness.add_argument("--makepad-activity", default=makepad_android_xr_activity)
    companion_readiness.add_argument("--require-adb", action="store_true")
    companion_readiness.add_argument("--require-android-sdk", action="store_true")
    companion_readiness.add_argument("--require-jdk", action="store_true")
    companion_readiness.add_argument("--require-cargo-makepad", action="store_true")
    companion_readiness.add_argument("--require-device", action="store_true")
    companion_readiness.add_argument("--require-makepad-package", action="store_true")
    companion_readiness.add_argument("--fail-on-blocking", action="store_true")

    companion_session = subcommands.add_parser("companion-session")
    companion_session_subcommands = companion_session.add_subparsers(
        dest="session_command",
        required=True,
    )
    companion_session_run = companion_session_subcommands.add_parser("run")
    companion_session_run.add_argument("--out", required=True)
    companion_session_run.add_argument("--validation-out")
    companion_session_run.add_argument("--session-id")
    companion_session_run.add_argument(
        "--frontend",
        choices=["wpf", "makepad", "cli"],
        default="cli",
    )
    companion_session_run.add_argument(
        "--profile",
        choices=["basic", "hostess-makepad-quest"],
        default="hostess-makepad-quest",
    )
    companion_session_run.add_argument("--descriptor")
    companion_session_run.add_argument("--hostess-descriptor")
    companion_session_run.add_argument("--gui-descriptors-root")
    companion_session_run.add_argument("--adb")
    companion_session_run.add_argument("--serial")
    companion_session_run.add_argument("--android-sdk")
    companion_session_run.add_argument("--jdk-home")
    companion_session_run.add_argument("--cargo", default="cargo")
    companion_session_run.add_argument("--cargo-makepad", default="cargo-makepad")
    companion_session_run.add_argument("--broker-host", default="127.0.0.1")
    companion_session_run.add_argument("--broker-port", type=int, default=broker_port)
    companion_session_run.add_argument(
        "--broker-local-port",
        type=int,
        default=broker_local_forward_port,
    )
    companion_session_run.add_argument("--broker-package", default=broker_package)
    companion_session_run.add_argument("--broker-activity")
    companion_session_run.add_argument("--broker-path", default="/manifold/v1/events")
    companion_session_run.add_argument("--check-broker", action="store_true")
    companion_session_run.add_argument("--require-broker", action="store_true")
    companion_session_run.add_argument("--makepad-package", default=makepad_android_package)
    companion_session_run.add_argument("--makepad-activity", default=makepad_android_xr_activity)
    companion_session_run.add_argument("--probe-input")
    companion_session_run.add_argument("--fallback-input")
    companion_session_run.add_argument("--fallback-remote-dir", default="files/hostess-t/settings")
    companion_session_run.add_argument("--connect-timeout-seconds", type=float, default=5.0)
    companion_session_run.add_argument(
        "--wait-seconds",
        type=float,
        default=DEFAULT_COMPANION_SESSION_WAIT_SECONDS,
    )
    companion_session_run.add_argument("--fallback-wait-seconds", type=float)
    companion_session_run.add_argument(
        "--authority-wait-seconds",
        type=float,
        default=DEFAULT_COMPANION_SESSION_AUTHORITY_WAIT_SECONDS,
    )
    companion_session_run.add_argument(
        "--runtime-receipt-stream",
        default="stream.hostess.makepad.bridge_command.receipt",
    )
    companion_session_run.add_argument("--no-runtime-receipt-subscribe", action="store_true")
    companion_session_run.add_argument(
        "--broker-process-wait-seconds",
        type=float,
        default=DEFAULT_COMPANION_SESSION_PROCESS_WAIT_SECONDS,
    )
    companion_session_run.add_argument(
        "--makepad-process-wait-seconds",
        type=float,
        default=DEFAULT_COMPANION_SESSION_PROCESS_WAIT_SECONDS,
    )
    companion_session_run.add_argument(
        "--socket-wait-seconds",
        type=float,
        default=DEFAULT_COMPANION_SESSION_SOCKET_WAIT_SECONDS,
    )
    companion_session_run.add_argument(
        "--launch-settle-seconds",
        type=float,
        default=DEFAULT_COMPANION_SESSION_LAUNCH_SETTLE_SECONDS,
    )
    companion_session_run.add_argument(
        "--runtime-subscriber-retry-count",
        type=int,
        default=DEFAULT_COMPANION_SESSION_RUNTIME_SUBSCRIBER_RETRY_COUNT,
    )
    companion_session_run.add_argument(
        "--runtime-subscriber-retry-wait-seconds",
        type=float,
        default=DEFAULT_COMPANION_SESSION_RUNTIME_SUBSCRIBER_RETRY_WAIT_SECONDS,
    )
    companion_session_run.add_argument("--no-launch-broker", action="store_true")
    companion_session_run.add_argument("--no-launch-makepad", action="store_true")
    companion_session_run.add_argument("--no-wait-broker-process", action="store_true")
    companion_session_run.add_argument("--no-wait-makepad-process", action="store_true")
    companion_session_run.add_argument("--no-adb-forward-broker", action="store_true")
    companion_session_run.add_argument("--skip-probe", action="store_true")
    companion_session_run.add_argument("--no-fallback", action="store_true")
    companion_session_run.add_argument("--fail-on-error", action="store_true")
    companion_session_history = companion_session_subcommands.add_parser("history")
    companion_session_history.add_argument("--out", required=True)
    companion_session_history.add_argument("--session-dir")
    companion_session_history.add_argument("--limit", type=int, default=25)

    companion_report = subcommands.add_parser("companion-report")
    companion_report_subcommands = companion_report.add_subparsers(
        dest="companion_report_command",
        required=True,
    )
    companion_report_projection = companion_report_subcommands.add_parser("projection")
    companion_report_projection.add_argument("--out", required=True)
    companion_report_projection.add_argument("--validation-out")
    companion_report_projection.add_argument("--projection-id")
    companion_report_projection.add_argument(
        "--frontend",
        choices=["wpf", "makepad", "cli"],
        default="cli",
    )
    companion_report_projection.add_argument("--device-link", action="append")
    companion_report_projection.add_argument("--connectivity-probe", action="append")
    companion_report_projection.add_argument("--firewall-rule", action="append")
    companion_report_projection.add_argument("--direct-wifi-product-media-plan", action="append")
    companion_report_projection.add_argument("--protocol-matrix", action="append")
    companion_report_projection.add_argument("--include-protocol-matrix-inputs", action="store_true")
    companion_report_projection.add_argument("--suite-run", action="append")
    companion_report_projection.add_argument("--fail-on-error", action="store_true")
    companion_report_transport_gates = companion_report_subcommands.add_parser("transport-gates")
    companion_report_transport_gates.add_argument("--projection", required=True)
    companion_report_transport_gates.add_argument("--out", required=True)
    companion_report_transport_gates.add_argument("--validation-out")
    companion_report_transport_gates.add_argument("--report-id")
    companion_report_transport_gates.add_argument("--fail-on-error", action="store_true")
    companion_report_transport_gates.add_argument("--fail-on-pending", action="store_true")

    connectivity_probe = subcommands.add_parser("connectivity-probe")
    connectivity_probe_subcommands = connectivity_probe.add_subparsers(
        dest="connectivity_probe_command",
        required=True,
    )
    connectivity_probe_run = connectivity_probe_subcommands.add_parser("run")
    connectivity_probe_run.add_argument("--out", required=True)
    connectivity_probe_run.add_argument("--validation-out")
    connectivity_probe_run.add_argument(
        "--probe-id",
        choices=[
            "QCL-000",
            "QCL-010",
            "QCL-011",
            "QCL-020",
            "QCL-030",
            "QCL-040",
            "QCL-041",
            "QCL-050",
            "QCL-051",
            "QCL-080",
            "QCL-081",
            "QCL-082",
            "QCL-083",
            "QCL-084",
            "QCL-079",
        ],
        default="QCL-010",
    )
    connectivity_probe_run.add_argument("--run-id")
    connectivity_probe_run.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    connectivity_probe_run.add_argument(
        "--fixture-profile",
        choices=[
            "qcl-000-usb-adb-pass",
            "qcl-010-router-pass",
            "qcl-010-router-firewall-blocked",
            "qcl-011-pc-hotspot-pass",
            "qcl-011-pc-hotspot-off",
            "qcl-020-wifi-adb-session-pass",
            "qcl-020-wifi-adb-reconnect-lost",
            "qcl-030-local-only-hotspot-started",
            "qcl-030-local-only-hotspot-failed",
            "qcl-040-wifi-direct-phone-peer-pass",
            "qcl-040-wifi-direct-permission-denied",
            "qcl-041-wifi-direct-windows-peer-pass",
            "qcl-041-wifi-direct-windows-driver-blocked",
            "qcl-050-rfcomm-control-pass",
            "qcl-050-rfcomm-pairing-refused",
            "qcl-051-ble-gatt-status-pass",
            "qcl-051-ble-permission-denied",
            "qcl-080-udp-freshness-pass",
            "qcl-080-app-owned-udp-freshness-pass",
            "qcl-080-udp-firewall-blocked",
            "qcl-081-lsl-loopback-pass",
            "qcl-081-lsl-discovery-blocked",
            "qcl-082-media-binary-plane-pass",
            "qcl-082-media-high-rate-json-misuse",
            "qcl-083-osc-loopback-pass",
            "qcl-083-osc-malformed-packet",
            "qcl-084-zeromq-loopback-pass",
            "qcl-084-zeromq-dependency-missing",
            "qcl-079-websocket-loopback-pass",
            "qcl-079-websocket-handshake-blocked",
        ],
    )
    connectivity_probe_run.add_argument("--media-stream-session-plan", default="")
    connectivity_probe_run.add_argument("--media-stream-runtime-status", default="")
    connectivity_probe_run.add_argument("--media-stream-rmanvid1-capture", default="")
    connectivity_probe_run.add_argument("--media-stream-receiver-sidecar", default="")
    connectivity_probe_run.add_argument("--media-stream-receiver-result", default="")
    connectivity_probe_run.add_argument("--media-stream-topology-report", default="")
    connectivity_probe_run.add_argument("--media-stream-firewall-report", default="")
    connectivity_probe_run.add_argument("--wifi-direct-lifecycle-report", default="")
    connectivity_probe_run.add_argument(
        "--websocket-source",
        choices=["host-loopback", "broker-owned-websocket", "quest-runtime", "external"],
        default="host-loopback",
    )
    connectivity_probe_run.add_argument("--websocket-bind-host", default="127.0.0.1")
    connectivity_probe_run.add_argument("--websocket-port", type=int, default=0)
    connectivity_probe_run.add_argument("--websocket-path", default="/qcl079")
    connectivity_probe_run.add_argument("--websocket-message-count", type=int, default=16)
    connectivity_probe_run.add_argument("--websocket-payload-bytes", type=int, default=96)
    connectivity_probe_run.add_argument("--websocket-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run.add_argument("--websocket-route-descriptor", default="")
    connectivity_probe_run.add_argument("--websocket-route-evidence", default="")
    connectivity_probe_receiver_capture = connectivity_probe_subcommands.add_parser(
        "rmanvid1-receiver-capture"
    )
    connectivity_probe_receiver_capture.add_argument("--out", required=True)
    connectivity_probe_receiver_capture.add_argument("--capture-out", required=True)
    connectivity_probe_receiver_capture.add_argument("--sidecar-out", required=True)
    connectivity_probe_receiver_capture.add_argument("--bind-host", default="0.0.0.0")
    connectivity_probe_receiver_capture.add_argument("--port", type=int, default=9079)
    connectivity_probe_receiver_capture.add_argument("--timeout-seconds", type=float, default=10.0)
    connectivity_probe_receiver_capture.add_argument("--max-packets", type=int, default=240)
    connectivity_probe_receiver_capture.add_argument("--max-bytes", type=int, default=67108864)
    connectivity_probe_receiver_capture.add_argument("--max-packet-bytes", type=int, default=4194304)
    connectivity_probe_receiver_capture.add_argument("--max-metadata-bytes", type=int, default=262144)
    connectivity_probe_receiver_capture.add_argument("--queue-capacity-packets", type=int, default=48)
    connectivity_probe_receiver_capture.add_argument(
        "--capture-kind",
        choices=["fixture_loopback_receiver", "live_broker_stream", "live_quest_runtime_stream"],
        default="fixture_loopback_receiver",
    )
    connectivity_probe_receiver_capture.add_argument("--source-endpoint-source", default="")
    connectivity_probe_receiver_capture.add_argument("--source-remote-endpoint", default="")
    connectivity_probe_receiver_capture.add_argument("--command-id", default="command.media_stream.start_source")
    connectivity_probe_receiver_capture.add_argument("--session-id", default="")
    connectivity_probe_receiver_capture.add_argument("--runtime-status", default="")
    connectivity_probe_receiver_capture.add_argument("--topology-report", default="")
    connectivity_probe_receiver_capture.add_argument("--firewall-report", default="")
    connectivity_probe_receiver_capture.add_argument("--fail-on-error", action="store_true")
    connectivity_probe_live_session = connectivity_probe_subcommands.add_parser(
        "qcl082-product-media-live-session"
    )
    connectivity_probe_live_session.add_argument("--out", required=True)
    connectivity_probe_live_session.add_argument("--start-source-request-out", required=True)
    connectivity_probe_live_session.add_argument("--bridge-evidence-out", required=True)
    connectivity_probe_live_session.add_argument("--execution-out", required=True)
    connectivity_probe_live_session.add_argument("--validation-out", required=True)
    connectivity_probe_live_session.add_argument("--logcat-out")
    connectivity_probe_live_session.add_argument("--route-descriptor")
    connectivity_probe_live_session.add_argument(
        "--bridge-command",
        default="command.media_stream.start_source",
    )
    connectivity_probe_live_session.add_argument("--request-id")
    connectivity_probe_live_session.add_argument("--evidence-id")
    connectivity_probe_live_session.add_argument(
        "--route-id",
        default="bridge_route.command.websocket.applied",
    )
    connectivity_probe_live_session.add_argument("--required-stage", action="append", default=[])
    connectivity_probe_live_session.add_argument("--params-json")
    connectivity_probe_live_session.add_argument("--params-json-file")
    connectivity_probe_live_session.add_argument("--capture-out", required=True)
    connectivity_probe_live_session.add_argument("--sidecar-out", required=True)
    connectivity_probe_live_session.add_argument("--bind-host", default="0.0.0.0")
    connectivity_probe_live_session.add_argument("--port", type=int, default=9079)
    connectivity_probe_live_session.add_argument("--timeout-seconds", type=float, default=10.0)
    connectivity_probe_live_session.add_argument("--max-packets", type=int, default=240)
    connectivity_probe_live_session.add_argument("--max-bytes", type=int, default=67108864)
    connectivity_probe_live_session.add_argument("--max-packet-bytes", type=int, default=4194304)
    connectivity_probe_live_session.add_argument("--max-metadata-bytes", type=int, default=262144)
    connectivity_probe_live_session.add_argument("--queue-capacity-packets", type=int, default=48)
    connectivity_probe_live_session.add_argument(
        "--capture-kind",
        choices=["live_broker_stream", "live_quest_runtime_stream"],
        default="live_broker_stream",
    )
    connectivity_probe_live_session.add_argument("--source-endpoint-source", default="")
    connectivity_probe_live_session.add_argument("--source-remote-endpoint", default="")
    connectivity_probe_live_session.add_argument("--session-id", default="")
    connectivity_probe_live_session.add_argument("--topology-report", required=True)
    connectivity_probe_live_session.add_argument("--firewall-report", required=True)
    connectivity_probe_live_session.add_argument("--adb", required=True)
    connectivity_probe_live_session.add_argument("--serial", required=True)
    connectivity_probe_live_session.add_argument("--broker-package", default=broker_package)
    connectivity_probe_live_session.add_argument("--broker-activity")
    connectivity_probe_live_session.add_argument("--broker-host", default="127.0.0.1")
    connectivity_probe_live_session.add_argument("--broker-port", type=int, default=broker_port)
    connectivity_probe_live_session.add_argument("--broker-local-port", type=int, default=broker_local_forward_port)
    connectivity_probe_live_session.add_argument("--broker-path", default="/manifold/v1/events")
    connectivity_probe_live_session.add_argument("--connect-timeout-seconds", type=float, default=5.0)
    connectivity_probe_live_session.add_argument("--wait-seconds", type=float, default=15.0)
    connectivity_probe_live_session.add_argument(
        "--runtime-receipt-stream",
        default="stream.hostess.makepad.bridge_command.receipt",
    )
    connectivity_probe_live_session.add_argument("--no-runtime-receipt-subscribe", action="store_true")
    connectivity_probe_live_session.add_argument("--makepad-package", default=makepad_android_package)
    connectivity_probe_live_session.add_argument("--makepad-activity", default=makepad_android_xr_activity)
    connectivity_probe_live_session.add_argument("--broker-process-wait-seconds", type=float, default=8.0)
    connectivity_probe_live_session.add_argument("--makepad-process-wait-seconds", type=float, default=8.0)
    connectivity_probe_live_session.add_argument("--socket-wait-seconds", type=float, default=8.0)
    connectivity_probe_live_session.add_argument("--launch-settle-seconds", type=float, default=8.0)
    connectivity_probe_live_session.add_argument("--runtime-subscriber-retry-count", type=int, default=1)
    connectivity_probe_live_session.add_argument(
        "--runtime-subscriber-retry-wait-seconds",
        type=float,
        default=5.0,
    )
    connectivity_probe_live_session.add_argument("--live-command-join-timeout-seconds", type=float, default=30.0)
    connectivity_probe_live_session.add_argument("--no-launch-broker", action="store_true")
    connectivity_probe_live_session.add_argument("--no-launch-makepad", action="store_true")
    connectivity_probe_live_session.add_argument("--no-wait-broker-process", action="store_true")
    connectivity_probe_live_session.add_argument("--no-wait-makepad-process", action="store_true")
    connectivity_probe_live_session.add_argument("--no-adb-forward-broker", action="store_true")
    connectivity_probe_live_session.add_argument("--fail-on-error", action="store_true")
    connectivity_probe_product_media_plan = connectivity_probe_subcommands.add_parser(
        "qcl082-product-media-plan"
    )
    connectivity_probe_product_media_plan.add_argument("--out", required=True)
    connectivity_probe_product_media_plan.add_argument("--plan-id", default="")
    connectivity_probe_product_media_plan.add_argument(
        "--adb",
        default=r"S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe",
    )
    connectivity_probe_product_media_plan.add_argument("--serial", default="<quest-serial>")
    connectivity_probe_product_media_plan.add_argument("--program", default="")
    connectivity_probe_product_media_plan.add_argument("--bind-host", default="0.0.0.0")
    connectivity_probe_product_media_plan.add_argument("--port", type=int, default=9079)
    connectivity_probe_product_media_plan.add_argument("--max-packets", type=int, default=240)
    connectivity_probe_product_media_plan.add_argument(
        "--capture-kind",
        choices=["live_broker_stream", "live_quest_runtime_stream"],
        default="live_broker_stream",
    )
    connectivity_probe_product_media_plan.add_argument("--start-source-request-out", default="")
    connectivity_probe_product_media_plan.add_argument("--start-source-bridge-evidence-out", default="")
    connectivity_probe_product_media_plan.add_argument("--start-source-execution-out", default="")
    connectivity_probe_product_media_plan.add_argument("--start-source-validation-out", default="")
    connectivity_probe_product_media_plan.add_argument("--runtime-status-report-out", default="")
    connectivity_probe_product_media_plan.add_argument("--promoted-topology-report", default="")
    connectivity_probe_product_media_plan.add_argument("--firewall-report", default="")
    connectivity_probe_product_media_plan.add_argument("--capture-out", default="")
    connectivity_probe_product_media_plan.add_argument("--sidecar-out", default="")
    connectivity_probe_product_media_plan.add_argument("--receiver-result-out", default="")
    connectivity_probe_product_media_plan.add_argument("--qcl082-report-out", default="")
    connectivity_probe_product_media_plan.add_argument("--protocol-matrix-out", default="")
    connectivity_probe_product_media_plan.add_argument("--fail-on-error", action="store_true")
    connectivity_probe_direct_wifi_product_media_plan = connectivity_probe_subcommands.add_parser(
        "direct-wifi-product-media-plan"
    )
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--out", required=True)
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--plan-id", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument(
        "--adb",
        default=r"S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe",
    )
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--serial", default="<quest-serial>")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--program", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--bind-host", default="0.0.0.0")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--port", type=int, default=9079)
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--max-packets", type=int, default=240)
    connectivity_probe_direct_wifi_product_media_plan.add_argument(
        "--capture-kind",
        choices=["live_broker_stream", "live_quest_runtime_stream"],
        default="live_broker_stream",
    )
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--qcl040-lifecycle-plan-out", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--qcl041-lifecycle-plan-out", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--qcl082-product-plan-out", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--qcl040-lifecycle-report", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--qcl041-lifecycle-report", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--qcl040-topology-report", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--qcl041-topology-report", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--promoted-topology-report", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--firewall-report", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--qcl082-report", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--protocol-matrix-out", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--projection-out", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--transport-gates-out", default="")
    connectivity_probe_direct_wifi_product_media_plan.add_argument("--fail-on-error", action="store_true")
    connectivity_probe_wifi_direct_lifecycle_template = connectivity_probe_subcommands.add_parser(
        "wifi-direct-lifecycle-template"
    )
    connectivity_probe_wifi_direct_lifecycle_template.add_argument("--out", required=True)
    connectivity_probe_wifi_direct_lifecycle_template.add_argument(
        "--probe-id",
        choices=["QCL-040", "QCL-041"],
        required=True,
    )
    connectivity_probe_wifi_direct_lifecycle_plan = connectivity_probe_subcommands.add_parser(
        "wifi-direct-lifecycle-plan"
    )
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument("--out", required=True)
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument(
        "--probe-id",
        choices=["QCL-040", "QCL-041"],
        required=True,
    )
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument("--plan-id", default="")
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument(
        "--adb",
        default=r"S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe",
    )
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument(
        "--serial",
        default="<quest-serial>",
    )
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument(
        "--preflight-report-out",
        default="",
    )
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument("--template-out", default="")
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument("--lifecycle-report", default="")
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument(
        "--topology-report-out",
        default="",
    )
    connectivity_probe_wifi_direct_lifecycle_plan.add_argument(
        "--fail-on-error",
        action="store_true",
    )
    connectivity_probe_run.add_argument("--adb")
    connectivity_probe_run.add_argument("--serial")
    connectivity_probe_run.add_argument("--wifi-interface", default="wlan0")
    connectivity_probe_run.add_argument("--host-ip")
    connectivity_probe_run.add_argument(
        "--topology-owner",
        choices=[
            "external_wifi",
            "pc_hotspot",
            "phone_hotspot",
            "travel_router",
            "local_only_hotspot",
            "wifi_direct",
        ],
        default="",
    )
    connectivity_probe_run.add_argument("--network-provider", default="")
    connectivity_probe_run.add_argument("--skip-host-ping", action="store_true")
    connectivity_probe_run.add_argument("--skip-device-ping", action="store_true")
    connectivity_probe_run.add_argument("--skip-tcp-echo", action="store_true")
    connectivity_probe_run.add_argument("--tcp-echo-bind-host", default="0.0.0.0")
    connectivity_probe_run.add_argument("--tcp-echo-port", type=int, default=0)
    connectivity_probe_run.add_argument("--tcp-echo-marker", default="rusty-qcl-tcp-echo")
    connectivity_probe_run.add_argument("--tcp-timeout-seconds", type=float, default=4.0)
    connectivity_probe_run.add_argument("--skip-udp-freshness", action="store_true")
    connectivity_probe_run.add_argument("--udp-bind-host", default="0.0.0.0")
    connectivity_probe_run.add_argument("--udp-port", type=int, default=0)
    connectivity_probe_run.add_argument("--udp-marker", default="rusty-qcl-udp")
    connectivity_probe_run.add_argument("--udp-packet-count", type=int, default=12)
    connectivity_probe_run.add_argument("--udp-interval-ms", type=float, default=50.0)
    connectivity_probe_run.add_argument("--udp-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run.add_argument("--udp-max-loss-percent", type=float, default=10.0)
    connectivity_probe_run.add_argument("--udp-max-jitter-ms", type=float, default=250.0)
    connectivity_probe_run.add_argument("--udp-listener-helper", default="")
    connectivity_probe_run.add_argument(
        "--udp-sender-source",
        choices=["auto", "adb-shell", "adb-pushed-native", "makepad-runtime"],
        default="auto",
    )
    connectivity_probe_run.add_argument("--udp-sender-host-path")
    connectivity_probe_run.add_argument("--udp-sender-device-path", default="/data/local/tmp/rusty-qcl080-udp-sender")
    connectivity_probe_run.add_argument("--makepad-package", default="io.github.mesmerprism.rustyhostess.makepad")
    connectivity_probe_run.add_argument(
        "--makepad-activity",
        default="io.github.mesmerprism.rustyhostess.makepad/.MakepadAppXr",
    )
    connectivity_probe_run.add_argument("--skip-makepad-force-stop", action="store_true")
    connectivity_probe_run.add_argument("--makepad-launch-timeout-seconds", type=float, default=10.0)
    connectivity_probe_run.add_argument(
        "--lsl-source",
        choices=["host-loopback", "quest-runtime", "manifold-lsl-broker", "external"],
        default="host-loopback",
    )
    connectivity_probe_run.add_argument("--lsl-stream-name", default="RustyQCL081")
    connectivity_probe_run.add_argument("--lsl-stream-type", default="Markers")
    connectivity_probe_run.add_argument("--lsl-sample-count", type=int, default=16)
    connectivity_probe_run.add_argument("--lsl-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run.add_argument("--lsl-manifold-root", default="")
    connectivity_probe_run.add_argument(
        "--osc-source",
        choices=["host-loopback", "quest-runtime", "external"],
        default="host-loopback",
    )
    connectivity_probe_run.add_argument("--osc-address", default="/rusty/qcl083")
    connectivity_probe_run.add_argument("--osc-port", type=int, default=0)
    connectivity_probe_run.add_argument("--osc-message-count", type=int, default=16)
    connectivity_probe_run.add_argument("--osc-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run.add_argument("--osc-max-loss-percent", type=float, default=0.0)
    connectivity_probe_run.add_argument(
        "--zeromq-source",
        choices=[
            "manifold-zmq-loopback",
            "rusty-xr-zmq-loopback",
            "host-loopback",
            "goofi-sidecar",
            "native-rust-broker",
            "quest-runtime",
            "external",
        ],
        default="manifold-zmq-loopback",
    )
    connectivity_probe_run.add_argument(
        "--zeromq-pattern",
        choices=["req-rep", "pub-sub"],
        default="pub-sub",
    )
    connectivity_probe_run.add_argument("--zeromq-message-count", type=int, default=16)
    connectivity_probe_run.add_argument("--zeromq-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run.add_argument("--zeromq-port", type=int, default=18784)
    connectivity_probe_run.add_argument("--zeromq-android-binary-host-path", default="")
    connectivity_probe_run.add_argument(
        "--zeromq-android-binary-device-path",
        default="/data/local/tmp/rusty-qcl084-req-rep-probe",
    )
    connectivity_probe_run.add_argument("--zeromq-manifold-root", default="")
    connectivity_probe_run.add_argument("--zeromq-rusty-xr-root", default="")
    connectivity_probe_run.add_argument("--zeromq-goofi-bridge-root", default="")
    connectivity_probe_run.add_argument("--zeromq-cargo-timeout-seconds", type=float, default=120.0)
    connectivity_probe_run.add_argument(
        "--bluetooth-payload-source",
        choices=["passive", "android-ble-gatt", "android-rfcomm"],
        default="passive",
    )
    connectivity_probe_run.add_argument("--bluetooth-helper", default="")
    connectivity_probe_run.add_argument("--bluetooth-message-count", type=int, default=3)
    connectivity_probe_run.add_argument("--bluetooth-reconnect-count", type=int, default=0)
    connectivity_probe_run.add_argument("--bluetooth-timeout-seconds", type=float, default=20.0)
    connectivity_probe_run.add_argument("--hostess-android-package", default="io.github.mesmerprism.rustyhostess.t")
    connectivity_probe_run.add_argument("--ping-count", type=int, default=2)
    connectivity_probe_run.add_argument("--ping-timeout-seconds", type=float, default=2.0)
    connectivity_probe_run.add_argument("--fail-on-error", action="store_true")
    connectivity_probe_firewall = connectivity_probe_subcommands.add_parser("windows-firewall-rule")
    connectivity_probe_firewall.add_argument("--out")
    connectivity_probe_firewall.add_argument("--program")
    connectivity_probe_firewall.add_argument(
        "--rule-profile",
        choices=["custom", "qcl-010-tcp-echo", "qcl-080-udp-freshness", "qcl-082-rmanvid1-media"],
        default="custom",
    )
    connectivity_probe_firewall.add_argument("--protocol", choices=["TCP", "UDP"], default=None)
    connectivity_probe_firewall.add_argument("--port", type=int, default=None)
    connectivity_probe_firewall.add_argument("--profile", default="Public")
    connectivity_probe_firewall.add_argument("--remote-address", default="LocalSubnet")
    connectivity_probe_firewall.add_argument("--rule-name")
    connectivity_probe_firewall.add_argument(
        "--action",
        choices=["plan", "apply", "verify", "remove"],
        default=None,
    )
    connectivity_probe_firewall.add_argument("--apply", action="store_true")
    connectivity_probe_firewall.add_argument("--verify", action="store_true")
    connectivity_probe_firewall.add_argument("--remove", action="store_true")
    connectivity_probe_firewall.add_argument("--handoff-script-out")
    connectivity_probe_firewall.add_argument("--handoff-verify-out")
    connectivity_probe_firewall.add_argument("--fail-on-error", action="store_true")
    connectivity_probe_stream_capability = connectivity_probe_subcommands.add_parser("stream-capability")
    connectivity_probe_stream_capability.add_argument("--input", required=True)
    connectivity_probe_stream_capability.add_argument("--out", required=True)
    connectivity_probe_stream_capability.add_argument("--validation-out")
    connectivity_probe_stream_capability.add_argument("--fail-on-error", action="store_true")
    connectivity_probe_test_suite = connectivity_probe_subcommands.add_parser("test-suite")
    connectivity_probe_test_suite.add_argument("--out", required=True)
    connectivity_probe_test_suite.add_argument("--validation-out")
    connectivity_probe_test_suite.add_argument("--suite-id", default="")
    connectivity_probe_test_suite.add_argument("--fail-on-error", action="store_true")
    connectivity_probe_protocol_matrix = connectivity_probe_subcommands.add_parser("protocol-matrix")
    connectivity_probe_protocol_matrix.add_argument("--out", required=True)
    connectivity_probe_protocol_matrix.add_argument("--validation-out")
    connectivity_probe_protocol_matrix.add_argument("--matrix-id")
    connectivity_probe_protocol_matrix.add_argument("--input", action="append")
    connectivity_probe_protocol_matrix.add_argument("--suite-run", action="append")
    connectivity_probe_protocol_matrix.add_argument("--latest-artifact-dir", action="append")
    connectivity_probe_protocol_matrix.add_argument("--latest-probe-id", action="append")
    connectivity_probe_protocol_matrix.add_argument("--latest-device-link-dir", action="append")
    connectivity_probe_protocol_matrix.add_argument("--latest-stream-capability-dir", action="append")
    connectivity_probe_protocol_matrix.add_argument("--latest-stream-probe-id", action="append")
    connectivity_probe_protocol_matrix.add_argument("--fail-on-error", action="store_true")
    connectivity_probe_run_suite = connectivity_probe_subcommands.add_parser("run-suite")
    connectivity_probe_run_suite.add_argument("--out", required=True)
    connectivity_probe_run_suite.add_argument("--validation-out")
    connectivity_probe_run_suite.add_argument("--suite-out")
    connectivity_probe_run_suite.add_argument("--artifact-dir")
    connectivity_probe_run_suite.add_argument("--suite-id", default="")
    connectivity_probe_run_suite.add_argument("--run-id")
    connectivity_probe_run_suite.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    connectivity_probe_run_suite.add_argument(
        "--probe-id",
        action="append",
        choices=[
            "QCL-000",
            "QCL-010",
            "QCL-011",
            "QCL-050",
            "QCL-051",
            "QCL-080",
            "QCL-081",
            "QCL-082",
            "QCL-083",
            "QCL-084",
            "QCL-079",
        ],
    )
    connectivity_probe_run_suite.add_argument("--skip-host-snapshot", action="store_true")
    connectivity_probe_run_suite.add_argument("--listener-program", default="")
    connectivity_probe_run_suite.add_argument("--listener-protocol", choices=["TCP", "UDP"], default="UDP")
    connectivity_probe_run_suite.add_argument("--listener-port", type=int, default=18767)
    connectivity_probe_run_suite.add_argument("--listener-bind-host", default="0.0.0.0")
    connectivity_probe_run_suite.add_argument("--listener-rule-name", default="")
    connectivity_probe_run_suite.add_argument("--listener-remote-address", default="LocalSubnet")
    connectivity_probe_run_suite.add_argument("--adb")
    connectivity_probe_run_suite.add_argument("--serial")
    connectivity_probe_run_suite.add_argument("--wifi-interface", default="wlan0")
    connectivity_probe_run_suite.add_argument("--host-ip")
    connectivity_probe_run_suite.add_argument(
        "--topology-owner",
        choices=[
            "external_wifi",
            "pc_hotspot",
            "phone_hotspot",
            "travel_router",
            "local_only_hotspot",
            "wifi_direct",
        ],
        default="",
    )
    connectivity_probe_run_suite.add_argument("--network-provider", default="")
    connectivity_probe_run_suite.add_argument("--tcp-echo-bind-host", default="0.0.0.0")
    connectivity_probe_run_suite.add_argument("--tcp-echo-port", type=int, default=0)
    connectivity_probe_run_suite.add_argument("--tcp-echo-marker", default="rusty-qcl-tcp-echo")
    connectivity_probe_run_suite.add_argument("--tcp-timeout-seconds", type=float, default=4.0)
    connectivity_probe_run_suite.add_argument("--udp-bind-host", default="0.0.0.0")
    connectivity_probe_run_suite.add_argument("--udp-port", type=int, default=0)
    connectivity_probe_run_suite.add_argument("--udp-marker", default="rusty-qcl-udp")
    connectivity_probe_run_suite.add_argument("--udp-packet-count", type=int, default=12)
    connectivity_probe_run_suite.add_argument("--udp-interval-ms", type=float, default=50.0)
    connectivity_probe_run_suite.add_argument("--udp-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run_suite.add_argument("--udp-max-loss-percent", type=float, default=10.0)
    connectivity_probe_run_suite.add_argument("--udp-max-jitter-ms", type=float, default=250.0)
    connectivity_probe_run_suite.add_argument("--udp-listener-helper", default="")
    connectivity_probe_run_suite.add_argument(
        "--udp-sender-source",
        choices=["auto", "adb-shell", "adb-pushed-native", "makepad-runtime"],
        default="auto",
    )
    connectivity_probe_run_suite.add_argument("--udp-sender-host-path")
    connectivity_probe_run_suite.add_argument("--udp-sender-device-path", default="/data/local/tmp/rusty-qcl080-udp-sender")
    connectivity_probe_run_suite.add_argument("--makepad-package", default="io.github.mesmerprism.rustyhostess.makepad")
    connectivity_probe_run_suite.add_argument(
        "--makepad-activity",
        default="io.github.mesmerprism.rustyhostess.makepad/.MakepadAppXr",
    )
    connectivity_probe_run_suite.add_argument("--skip-makepad-force-stop", action="store_true")
    connectivity_probe_run_suite.add_argument("--makepad-launch-timeout-seconds", type=float, default=10.0)
    connectivity_probe_run_suite.add_argument(
        "--lsl-source",
        choices=["host-loopback", "quest-runtime", "manifold-lsl-broker", "external"],
        default="host-loopback",
    )
    connectivity_probe_run_suite.add_argument("--lsl-stream-name", default="RustyQCL081")
    connectivity_probe_run_suite.add_argument("--lsl-stream-type", default="Markers")
    connectivity_probe_run_suite.add_argument("--lsl-sample-count", type=int, default=16)
    connectivity_probe_run_suite.add_argument("--lsl-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run_suite.add_argument("--lsl-manifold-root", default="")
    connectivity_probe_run_suite.add_argument("--osc-source", choices=["host-loopback", "quest-runtime", "external"], default="host-loopback")
    connectivity_probe_run_suite.add_argument("--osc-address", default="/rusty/qcl083")
    connectivity_probe_run_suite.add_argument("--osc-port", type=int, default=0)
    connectivity_probe_run_suite.add_argument("--osc-message-count", type=int, default=16)
    connectivity_probe_run_suite.add_argument("--osc-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run_suite.add_argument("--osc-max-loss-percent", type=float, default=0.0)
    connectivity_probe_run_suite.add_argument(
        "--zeromq-source",
        choices=[
            "manifold-zmq-loopback",
            "rusty-xr-zmq-loopback",
            "host-loopback",
            "goofi-sidecar",
            "native-rust-broker",
            "quest-runtime",
            "external",
        ],
        default="manifold-zmq-loopback",
    )
    connectivity_probe_run_suite.add_argument("--zeromq-pattern", choices=["req-rep", "pub-sub"], default="pub-sub")
    connectivity_probe_run_suite.add_argument("--zeromq-message-count", type=int, default=16)
    connectivity_probe_run_suite.add_argument("--zeromq-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run_suite.add_argument("--zeromq-port", type=int, default=18784)
    connectivity_probe_run_suite.add_argument("--zeromq-android-binary-host-path", default="")
    connectivity_probe_run_suite.add_argument("--zeromq-android-binary-device-path", default="/data/local/tmp/rusty-qcl084-req-rep-probe")
    connectivity_probe_run_suite.add_argument("--zeromq-manifold-root", default="")
    connectivity_probe_run_suite.add_argument("--zeromq-rusty-xr-root", default="")
    connectivity_probe_run_suite.add_argument("--zeromq-goofi-bridge-root", default="")
    connectivity_probe_run_suite.add_argument("--zeromq-cargo-timeout-seconds", type=float, default=120.0)
    connectivity_probe_run_suite.add_argument(
        "--websocket-source",
        choices=["host-loopback", "broker-owned-websocket", "quest-runtime", "external"],
        default="host-loopback",
    )
    connectivity_probe_run_suite.add_argument("--websocket-bind-host", default="127.0.0.1")
    connectivity_probe_run_suite.add_argument("--websocket-port", type=int, default=0)
    connectivity_probe_run_suite.add_argument("--websocket-path", default="/qcl079")
    connectivity_probe_run_suite.add_argument("--websocket-message-count", type=int, default=16)
    connectivity_probe_run_suite.add_argument("--websocket-payload-bytes", type=int, default=96)
    connectivity_probe_run_suite.add_argument("--websocket-timeout-seconds", type=float, default=5.0)
    connectivity_probe_run_suite.add_argument("--websocket-route-descriptor", default="")
    connectivity_probe_run_suite.add_argument("--websocket-route-evidence", default="")
    connectivity_probe_run_suite.add_argument("--bluetooth-payload-source", choices=["passive", "android-ble-gatt", "android-rfcomm"], default="passive")
    connectivity_probe_run_suite.add_argument("--bluetooth-helper", default="")
    connectivity_probe_run_suite.add_argument("--bluetooth-message-count", type=int, default=3)
    connectivity_probe_run_suite.add_argument("--bluetooth-reconnect-count", type=int, default=0)
    connectivity_probe_run_suite.add_argument("--bluetooth-timeout-seconds", type=float, default=20.0)
    connectivity_probe_run_suite.add_argument("--hostess-android-package", default="io.github.mesmerprism.rustyhostess.t")
    connectivity_probe_run_suite.add_argument("--ping-count", type=int, default=2)
    connectivity_probe_run_suite.add_argument("--ping-timeout-seconds", type=float, default=2.0)
    connectivity_probe_run_suite.add_argument("--fail-on-error", action="store_true")

    render = subcommands.add_parser("render-telemetry")
    render.add_argument("--target", choices=["desktop", "phone", "quest"], required=True)
    render.add_argument("--adb")
    render.add_argument("--serial")
    render.add_argument("--out", required=True)
    render.add_argument("--input")
    render.add_argument("--name")
    render.add_argument("--page", choices=["raw", "modules"], default="raw")
    render.add_argument("--source-evidence-path")

    makepad_render = subcommands.add_parser("pull-makepad-render")
    makepad_render.add_argument("--target", choices=["phone", "quest"], required=True)
    makepad_render.add_argument("--adb", required=True)
    makepad_render.add_argument("--serial", required=True)
    makepad_render.add_argument("--out", required=True)
    makepad_render.add_argument("--wait-seconds", type=float, default=45.0)
    makepad_render.add_argument("--min-events", type=int, default=0)
    makepad_render.add_argument("--no-launch", action="store_true")

    makepad_shell_contract = subcommands.add_parser("launch-makepad-shell-contract")
    makepad_shell_contract.add_argument("--target", choices=["phone", "quest"], required=True)
    makepad_shell_contract.add_argument("--launch-handoff", required=True)
    makepad_shell_contract.add_argument("--out", required=True)
    makepad_shell_contract.add_argument("--adb")
    makepad_shell_contract.add_argument("--serial")
    makepad_shell_contract.add_argument("--makepad-package", default=makepad_android_package)
    makepad_shell_contract.add_argument("--makepad-activity")
    makepad_shell_contract.add_argument("--remote-dir")
    makepad_shell_contract.add_argument("--wait-seconds", type=float, default=20.0)
    makepad_shell_contract.add_argument("--runtime-observation-seconds", type=float, default=8.0)
    makepad_shell_contract.add_argument("--runtime-observation-poll-ms", type=float, default=750.0)
    makepad_shell_contract.add_argument("--skip-pregrant-permissions", action="store_true")
    makepad_shell_contract.add_argument("--plan-only", action="store_true")

    questionnaire_status = subcommands.add_parser("questionnaire-status")
    questionnaire_status.add_argument("--endpoint", default="http://127.0.0.1:8787")

    questionnaire_open_block = subcommands.add_parser("questionnaire-open-block")
    questionnaire_open_block.add_argument("--endpoint", default="http://127.0.0.1:8787")
    questionnaire_open_block.add_argument("--block", choices=["1", "2", "3"], required=True)
    questionnaire_open_block.add_argument("--session-id", required=True)
    questionnaire_open_block.add_argument("--participant-ref", required=True)
    questionnaire_open_block.add_argument("--language-code", default="en")
    questionnaire_open_block.add_argument("--command-id", default="hostessctl-open-block")

    questionnaire_dismiss = subcommands.add_parser("questionnaire-dismiss")
    questionnaire_dismiss.add_argument("--endpoint", default="http://127.0.0.1:8787")
    questionnaire_dismiss.add_argument("--session-id", required=True)
    questionnaire_dismiss.add_argument("--command-id", default="hostessctl-dismiss")

    questionnaire_serve = subcommands.add_parser("questionnaire-serve")
    questionnaire_serve.add_argument("--host", default="127.0.0.1")
    questionnaire_serve.add_argument("--port", type=int, default=8787)
    questionnaire_serve.add_argument("--max-requests", type=int)
    questionnaire_serve.add_argument("--device-label", default="local-dev")
    questionnaire_serve.add_argument("--xr-package", default="rusty-morphospace.xr")
    questionnaire_serve.add_argument("--xr-activity", default=".MainActivity")
    questionnaire_serve.add_argument(
        "--panel-package",
        default="io.github.mesmerprism.questquestionnaire",
    )
    questionnaire_serve.add_argument("--panel-activity", default=".QuestionnairePanelActivity")

    snapshot = subcommands.add_parser("snapshot-telemetry")
    snapshot.add_argument("--input", required=True)
    snapshot.add_argument("--out", required=True)
    snapshot.add_argument("--runtime-input")
    snapshot.add_argument("--graph-report")

    return parser
