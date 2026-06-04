"""Small Hostess T command bridge for the first live-capture slot."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.check_live_capture_evidence import package_snapshot, sha256_file  # noqa: E402
from tools.hostessctl import makepad_shell_contract as makepad_shell_contract_launcher  # noqa: E402
from tools.hostessctl.makepad_visual_profile import (  # noqa: E402
    makepad_visual_profile_runtime_properties,
    with_legacy_rustyxr_property_aliases,
)
from tools.telemetry_snapshot import build_snapshot, write_snapshot  # noqa: E402

ANDROID_PACKAGE = "io.github.mesmerprism.rustyhostess.t"
BROKER_PACKAGE = "com.example.rustyxr.broker"
BROKER_ACTIVITY = f"{BROKER_PACKAGE}/.BrokerStartActivity"
BROKER_PORT = 8765
BROKER_LOCAL_FORWARD_PORT = 18765
MANIFOLD_COMMAND_SCHEMA = "rusty.manifold.command.envelope.v1"
LEGACY_RUSTY_XR_BROKER_COMMAND_SCHEMA = "rusty.xr.broker.command.v1"
MANIFOLD_BROKER_EVENTS_PATH = "/manifold/v1/events"
LEGACY_RUSTY_XR_BROKER_EVENTS_PATH = "/rustyxr/v1/events"
MAKEPAD_XR_PROVIDER_PACKAGE = "io.github.mesmerprism.rustyxr.makepad.camera"
MAKEPAD_XR_PROVIDER_ACTIVITY = f"{MAKEPAD_XR_PROVIDER_PACKAGE}/.MakepadApp"
MAKEPAD_ANDROID_PACKAGE = "io.github.mesmerprism.rustyhostess.makepad"
MAKEPAD_ANDROID_ACTIVITY = f"{MAKEPAD_ANDROID_PACKAGE}/.MakepadApp"
MAKEPAD_ANDROID_XR_ACTIVITY = f"{MAKEPAD_ANDROID_PACKAGE}/.MakepadAppXr"
ANDROID_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_CAPTURE"
ANDROID_REPLAY_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_REPLAY"
ANDROID_PMB_REPLAY_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_PMB_REPLAY"
ANDROID_PMB_CONTROLLER_PREFLIGHT_ACTION = (
    "io.github.mesmerprism.rustyhostess.t.RUN_PMB_CONTROLLER_PREFLIGHT"
)
ANDROID_PMB_SIMULATED_LIVE_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_PMB_SIMULATED_LIVE"
ANDROID_PMB_PHYSICAL_LIVE_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_PMB_PHYSICAL_LIVE"
ANDROID_PMB_PHYSICAL_LIVE_BACKGROUND_ACTION = (
    "io.github.mesmerprism.rustyhostess.t.RUN_PMB_PHYSICAL_LIVE_BACKGROUND"
)
ANDROID_BROKER_TELEMETRY_ACTION = "io.github.mesmerprism.rustyhostess.t.OBSERVE_BROKER_TELEMETRY"
ANDROID_PMB_PHYSICAL_LIVE_SERVICE = f"{ANDROID_PACKAGE}/.PmbPhysicalLiveService"
ANDROID_RENDER_ACTION = "io.github.mesmerprism.rustyhostess.t.RENDER_TELEMETRY"
ANDROID_REMOTE_EVIDENCE = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/live-capture/latest.json"
)
ANDROID_REMOTE_RUNTIME_INPUT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/live-capture/latest.runtime-input.json"
)
ANDROID_REMOTE_GRAPH_REPORT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/live-capture/latest.graph-execution-report.json"
)
ANDROID_REMOTE_PMB_EVIDENCE = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-replay/latest.json"
)
ANDROID_REMOTE_PMB_CORE_REPORT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-replay/latest.core-validation-report.json"
)
ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-controller-preflight/latest.json"
)
ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_REPORT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-controller-preflight/latest.controller-preflight-report.json"
)
ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-simulated-live/latest.json"
)
ANDROID_REMOTE_PMB_SIMULATED_LIVE_ROUTE_REPORT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-simulated-live/latest.live-route-report.json"
)
ANDROID_REMOTE_PMB_SIMULATED_LIVE_BROKER_REPORT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-simulated-live/latest.broker-publish-report.json"
)
ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-physical-live/latest.json"
)
ANDROID_REMOTE_PMB_PHYSICAL_LIVE_CAPTURE_REPORT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-physical-live/latest.input-capture-report.json"
)
ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVENTS_JSONL = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-physical-live/latest.transport-events.jsonl"
)
ANDROID_REMOTE_PMB_PHYSICAL_LIVE_ROUTE_REPORT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-physical-live/latest.live-route-report.json"
)
ANDROID_REMOTE_PMB_PHYSICAL_LIVE_BROKER_REPORT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/pmb-physical-live/latest.broker-publish-report.json"
)
ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/broker-telemetry/latest.json"
)
ANDROID_REMOTE_BROKER_TELEMETRY_REPORT = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/broker-telemetry/latest.broker-telemetry-report.json"
)
ANDROID_REMOTE_RENDER_ROOT = f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/render"
MAKEPAD_RENDER_RELATIVE = "files/hostess-t/telemetry/makepad-telemetry-render.png"
MAKEPAD_RENDER_SIDECAR_RELATIVE = f"{MAKEPAD_RENDER_RELATIVE}.json"
MIN_RENDER_WIDTH = 320
MIN_RENDER_HEIGHT = 240
MIN_RENDER_CONTENT_PIXELS = 64

MANIFOLD_VALUE_ALIASES = {
    "polar.hr_rr": "stream.polar_h10.hr_rr",
    "polar.ecg": "stream.polar_h10.ecg",
    "polar.acc": "stream.polar_h10.acc",
    "polar.coherence": "stream.polar_h10.coherence",
    "motion.object_pose": "stream.motion.object_pose",
    "motion.vector3": "stream.motion.vector3",
    "breath.volume": "stream.breath.volume",
    "breath.dynamics": "stream.breath.dynamics",
    "breath.feedback_state": "stream.breath.feedback_state",
}

PMB_SHELL_HANDOFF_REQUIRED_BINDINGS = {
    ("stream.motion.object_pose", "publish"),
    ("stream.breath.feedback_state", "subscribe"),
    ("stream.breath.feedback_receipt", "publish"),
}

MANIFOLD_VALUE_PROVIDERS = {
    "stream.polar_h10.hr_rr": {
        "value_id": "value.polar_h10.hr_rr",
        "stream_id": "stream.polar_h10.hr_rr",
        "provider_id": "provider.polar_h10.ble",
        "provider_kind": "ble_polar_h10",
        "package_id": "package.polar_h10",
        "live_stream_mode": "hr_rr",
        "sample_kind": "heart_rate_rr",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": True,
        "preflight_supported": False,
    },
    "stream.polar_h10.ecg": {
        "value_id": "value.polar_h10.ecg",
        "stream_id": "stream.polar_h10.ecg",
        "provider_id": "provider.polar_h10.ble",
        "provider_kind": "ble_polar_h10",
        "package_id": "package.polar_h10",
        "live_stream_mode": "ecg",
        "sample_kind": "ecg",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": True,
        "preflight_supported": False,
    },
    "stream.polar_h10.acc": {
        "value_id": "value.polar_h10.acc",
        "stream_id": "stream.polar_h10.acc",
        "broker_stream_id": "bio:polar_acc",
        "provider_id": "provider.polar_h10.ble",
        "provider_kind": "ble_polar_h10",
        "package_id": "package.polar_h10",
        "live_stream_mode": "acc",
        "sample_kind": "motion_vector3",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": True,
        "broker_websocket_recording_supported": True,
        "broker_start_command": "polar_pmd.start",
        "broker_stop_command": "polar_pmd.stop",
        "preflight_supported": False,
    },
    "stream.polar_h10.coherence": {
        "value_id": "value.polar_h10.coherence",
        "stream_id": "stream.polar_h10.coherence",
        "provider_id": "provider.polar_h10.ble",
        "provider_kind": "ble_polar_h10",
        "package_id": "package.polar_h10",
        "live_stream_mode": "coherence",
        "sample_kind": "coherence",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": True,
        "preflight_supported": False,
    },
    "stream.motion.object_pose": {
        "value_id": "value.motion.object_pose",
        "stream_id": "stream.motion.object_pose",
        "broker_stream_id": "stream.motion.object_pose",
        "provider_id": "provider.makepad.controller_pose",
        "provider_kind": "xr_object_pose",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "object_pose",
        "supported_targets": ["quest"],
        "single_value_live_route_supported": False,
        "broker_websocket_recording_supported": True,
        "provider_launch": "makepad_xr_controller_pose",
        "preflight_supported": True,
        "preflight_route": "hostessctl.run-pmb-controller-preflight",
    },
    "stream.motion.vector3": {
        "value_id": "value.motion.vector3",
        "stream_id": "stream.motion.vector3",
        "provider_id": "provider.motion.vector3.unbound",
        "provider_kind": "motion_vector3",
        "sample_kind": "motion_vector3",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": False,
        "blocked_reason": "generic motion vector3 providers must bind a concrete source before recording",
    },
    "stream.breath.volume": {
        "value_id": "value.breath.volume",
        "stream_id": "stream.breath.volume",
        "provider_id": "processor.projected_motion_breath",
        "provider_kind": "processor_output",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "breath_volume",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": True,
        "blocked_reason": "processor output recording requires at least one bound PMB input provider",
    },
    "stream.breath.dynamics": {
        "value_id": "value.breath.dynamics",
        "stream_id": "stream.breath.dynamics",
        "provider_id": "processor.projected_motion_breath",
        "provider_kind": "processor_output",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "breath_dynamics",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": True,
        "blocked_reason": "processor output recording requires at least one bound PMB input provider",
    },
    "stream.breath.feedback_state": {
        "value_id": "value.breath.feedback_state",
        "stream_id": "stream.breath.feedback_state",
        "provider_id": "processor.projected_motion_breath.feedback_sink",
        "provider_kind": "processor_output",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "breath_feedback_state",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": True,
        "blocked_reason": "processor feedback recording requires the PMB live broker route self-test and live processor bridge",
    },
}


def main() -> int:
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
    run_pmb_simulated_live_parser.add_argument("--broker-package", default=BROKER_PACKAGE)
    run_pmb_simulated_live_parser.add_argument("--broker-activity", default=BROKER_ACTIVITY)
    run_pmb_simulated_live_parser.add_argument("--broker-port", type=int, default=BROKER_PORT)
    run_pmb_simulated_live_parser.add_argument("--makepad-package", default=MAKEPAD_ANDROID_PACKAGE)
    run_pmb_simulated_live_parser.add_argument("--makepad-activity", default=MAKEPAD_ANDROID_XR_ACTIVITY)
    run_pmb_simulated_live_parser.add_argument("--makepad-settle-seconds", type=float, default=8.0)
    run_pmb_simulated_live_parser.add_argument("--feedback-publish-limit", type=int, default=12)
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
    run_pmb_physical_live_parser.add_argument("--broker-package", default=BROKER_PACKAGE)
    run_pmb_physical_live_parser.add_argument("--broker-activity", default=BROKER_ACTIVITY)
    run_pmb_physical_live_parser.add_argument("--broker-port", type=int, default=BROKER_PORT)
    run_pmb_physical_live_parser.add_argument("--makepad-package", default=MAKEPAD_ANDROID_PACKAGE)
    run_pmb_physical_live_parser.add_argument("--makepad-activity", default=MAKEPAD_ANDROID_XR_ACTIVITY)
    run_pmb_physical_live_parser.add_argument("--makepad-settle-seconds", type=float, default=10.0)
    run_pmb_physical_live_parser.add_argument("--makepad-pose-controller", choices=["left", "right"], default="right")
    run_pmb_physical_live_parser.add_argument("--makepad-pose-kind", choices=["grip", "aim"], default="grip")
    run_pmb_physical_live_parser.add_argument("--makepad-pose-sample-hz", type=float, default=20.0)
    run_pmb_physical_live_parser.add_argument("--feedback-publish-limit", type=int, default=24)
    run_pmb_physical_live_parser.add_argument("--receipt-listen-seconds", type=float, default=6.0)
    run_pmb_physical_live_parser.add_argument("--no-launch-broker", action="store_true")
    run_pmb_physical_live_parser.add_argument("--no-launch-makepad", action="store_true")
    run_pmb_physical_live_parser.add_argument("--foreground-hostess", action="store_true")

    observe_broker_telemetry = subcommands.add_parser("observe-broker-telemetry")
    observe_broker_telemetry.add_argument("--target", choices=["quest"], default="quest")
    observe_broker_telemetry.add_argument("--out", required=True)
    observe_broker_telemetry.add_argument("--adb", required=True)
    observe_broker_telemetry.add_argument("--serial", required=True)
    observe_broker_telemetry.add_argument("--duration-seconds", type=float, default=10.0)
    observe_broker_telemetry.add_argument("--device-address")
    observe_broker_telemetry.add_argument("--acc-rate", type=int, default=200)
    observe_broker_telemetry.add_argument("--scan-timeout-seconds", type=float, default=30.0)
    observe_broker_telemetry.add_argument("--broker-package", default=BROKER_PACKAGE)
    observe_broker_telemetry.add_argument("--broker-activity", default=BROKER_ACTIVITY)
    observe_broker_telemetry.add_argument("--broker-port", type=int, default=BROKER_PORT)
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
    record_values.add_argument("--broker-package", default=BROKER_PACKAGE)
    record_values.add_argument("--broker-activity", default=BROKER_ACTIVITY)
    record_values.add_argument("--broker-port", type=int, default=BROKER_PORT)
    record_values.add_argument("--broker-local-port", type=int, default=BROKER_LOCAL_FORWARD_PORT)
    record_values.add_argument("--makepad-provider-package", default=MAKEPAD_XR_PROVIDER_PACKAGE)
    record_values.add_argument("--makepad-provider-activity", default=MAKEPAD_XR_PROVIDER_ACTIVITY)
    record_values.add_argument("--makepad-pose-controller", choices=["left", "right"], default="right")
    record_values.add_argument("--makepad-pose-kind", choices=["grip", "aim"], default="grip")
    record_values.add_argument("--makepad-pose-sample-hz", type=float, default=20.0)
    record_values.add_argument("--makepad-pose-ready-timeout-seconds", type=float, default=20.0)
    record_values.add_argument("--cargo", default="cargo")
    record_values.add_argument("--pmb-live-processor", action="store_true")
    record_values.add_argument("--pmb-feedback-publish-limit", type=int, default=24)
    record_values.add_argument("--pmb-receipt-listen-seconds", type=float, default=3.0)
    record_values.add_argument("--no-launch-broker", action="store_true")
    record_values.add_argument("--no-launch-providers", action="store_true")
    record_values.add_argument("--runtime-core", choices=["rust", "python-smoke"], default="rust")
    record_values.add_argument("--telemetry-page", choices=["raw", "modules"], default="raw")
    record_values.add_argument("--plan-only", action="store_true")
    record_values.add_argument("--allow-blocked", action="store_true")

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
    makepad_shell_contract.add_argument("--makepad-package", default=MAKEPAD_ANDROID_PACKAGE)
    makepad_shell_contract.add_argument("--makepad-activity")
    makepad_shell_contract.add_argument("--remote-dir")
    makepad_shell_contract.add_argument("--wait-seconds", type=float, default=20.0)
    makepad_shell_contract.add_argument("--runtime-observation-seconds", type=float, default=8.0)
    makepad_shell_contract.add_argument("--runtime-observation-poll-ms", type=float, default=750.0)
    makepad_shell_contract.add_argument("--skip-pregrant-permissions", action="store_true")
    makepad_shell_contract.add_argument("--plan-only", action="store_true")

    snapshot = subcommands.add_parser("snapshot-telemetry")
    snapshot.add_argument("--input", required=True)
    snapshot.add_argument("--out", required=True)
    snapshot.add_argument("--runtime-input")
    snapshot.add_argument("--graph-report")

    args = parser.parse_args()
    if args.command == "install-android":
        return install_android(args)
    if args.command == "run-live":
        return run_live_capture(args)
    if args.command == "run-replay":
        return run_replay_capture(args)
    if args.command == "run-pmb-replay":
        return run_pmb_replay_capture(args)
    if args.command == "run-pmb-controller-preflight":
        return run_pmb_controller_preflight(args)
    if args.command == "run-pmb-quest-simulated-live":
        return run_pmb_quest_simulated_live(args)
    if args.command == "run-pmb-quest-physical-live":
        return run_pmb_quest_physical_live(args)
    if args.command == "observe-broker-telemetry":
        return observe_broker_telemetry_ui(args)
    if args.command == "run-pmb-live-route-self-test":
        return run_pmb_live_route_self_test(args)
    if args.command == "run-pmb-shell-handoff":
        return run_pmb_shell_handoff(args)
    if args.command == "record-values":
        return run_manifold_value_recording(args)
    if args.command == "render-telemetry":
        return render_telemetry(args)
    if args.command == "pull-makepad-render":
        return pull_makepad_render(args)
    if args.command == "launch-makepad-shell-contract":
        return launch_makepad_shell_contract(args)
    if args.command == "snapshot-telemetry":
        return snapshot_telemetry(args)
    return 2


def install_android(args: argparse.Namespace) -> int:
    run([args.adb, "-s", args.serial, "uninstall", ANDROID_PACKAGE], allow_failure=True)
    run([args.adb, "-s", args.serial, "install", args.apk])
    for permission in [
        "android.permission.BLUETOOTH_SCAN",
        "android.permission.BLUETOOTH_CONNECT",
        "android.permission.ACCESS_FINE_LOCATION",
    ]:
        run([args.adb, "-s", args.serial, "shell", "pm", "grant", ANDROID_PACKAGE, permission], allow_failure=True)
    return 0


def run_live_capture(args: argparse.Namespace) -> int:
    if not args.stream and not args.module:
        raise SystemExit("run-live requires --stream or at least one --module")
    if args.stream and args.module:
        raise SystemExit("run-live accepts either --stream or --module selections, not both")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.target == "desktop":
        return run_desktop_capture(args, out)
    return run_android_capture(args, out)


def run_desktop_capture(args: argparse.Namespace, out: Path) -> int:
    command = [
        sys.executable,
        str(REPO_ROOT / "apps" / "hostess-t-desktop" / "capture_polar.py"),
        "--packages-root",
        args.packages_root,
        "--mode",
        args.stream if args.stream else "module",
        "--duration-seconds",
        str(args.duration_seconds),
        "--acc-rate",
        str(args.acc_rate),
        "--runtime-core",
        args.runtime_core,
        "--out",
        str(out),
    ]
    if args.device_address:
        command.extend(["--device-address", args.device_address])
    for module_id in args.module:
        command.extend(["--module", module_id])
    for source_arg, cli_arg in [
        ("rmssd_baseline_ln_rmssd", "--rmssd-baseline-ln-rmssd"),
        ("rmssd_baseline_mean_ln_rmssd", "--rmssd-baseline-mean-ln-rmssd"),
        ("rmssd_baseline_sd_ln_rmssd", "--rmssd-baseline-sd-ln-rmssd"),
        ("rmssd_baseline_window_count", "--rmssd-baseline-window-count"),
    ]:
        value = getattr(args, source_arg)
        if value is not None:
            command.extend([cli_arg, str(value)])
    if args.rmssd_baseline_source:
        command.extend(["--rmssd-baseline-source", args.rmssd_baseline_source])
    capture = run(command, allow_failure=True)
    validation = validate_evidence(args, out, "desktop")
    return validation if validation != 0 else capture.returncode


def run_replay_capture(args: argparse.Namespace) -> int:
    if args.target in {"phone", "quest"}:
        return run_android_replay(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = polar_package_root(packages_root)
    graph_path = package_root / "fixtures" / "valid" / "graph.json"
    input_path = (
        Path(args.input)
        if args.input
        else package_root / "fixtures" / "valid" / "processor-runtime-input-synthetic.json"
    )
    graph_report_path = out.with_name(f"{out.stem}.graph-execution-report.json")
    started_utc = datetime.now(UTC)
    command = [
        "cargo",
        "run",
        "-p",
        "polar-h10-core",
        "--",
        "run-fixture",
        "--graph",
        str(graph_path),
        "--input",
        str(input_path),
        "--select",
        ",".join(args.module),
        "--out",
        str(graph_report_path),
    ]
    graph_run = run(command, allow_failure=True, cwd=packages_root)
    ended_utc = datetime.now(UTC)
    if not graph_report_path.exists():
        return graph_run.returncode if graph_run.returncode != 0 else 2
    graph_report = json.loads(graph_report_path.read_text(encoding="utf-8"))
    streams = graph_report_streams(graph_report)
    package = package_snapshot(packages_root)
    package["package_id"] = "package.polar_h10"
    evidence = {
        "$schema": "rusty.manifold.live_capture_evidence.v1",
        "status": graph_report.get("status", "fail"),
        "host_profile": "desktop",
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.desktop",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "capture": {
            "mode": "module",
            "selected_module_ids": graph_report.get("selected_module_ids", []),
            "dependency_stream_ids": graph_report.get("output_stream_ids", []),
            "runtime_path": graph_report.get("runtime_path"),
            "graph_id": graph_report.get("graph_id"),
            "graph_revision": graph_report.get("graph_revision"),
            "graph_execution_report": graph_report_path.name,
        },
        "commands": [
            {
                "command": "run_graph_fixture",
                "status": "acknowledged" if graph_run.returncode == 0 else "rejected",
                "runtime_path": graph_report.get("runtime_path"),
            }
        ],
        "streams": streams,
        "errors": [issue.get("message") for issue in graph_report.get("issues", [])],
    }
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    validation = validate_evidence(args, out, "desktop")
    return validation if validation != 0 else graph_run.returncode


def run_pmb_replay_capture(args: argparse.Namespace) -> int:
    if args.target in {"phone", "quest"}:
        return run_android_pmb_replay(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    core_report_path = out.with_name(f"{out.stem}.core-validation-report.json")
    stdout_path = out.with_name(f"{out.stem}.stdout.txt")
    stderr_path = out.with_name(f"{out.stem}.stderr.txt")
    started_utc = datetime.now(UTC)
    command = [
        args.cargo,
        "run",
        "--quiet",
        "-p",
        "projected-motion-breath-core",
        "--",
        "validate-goldens",
        "--package-root",
        str(package_root),
    ]
    core_run = run_captured(command, allow_failure=True, cwd=packages_root)
    ended_utc = datetime.now(UTC)
    stdout_path.write_text(core_run.stdout, encoding="utf-8")
    stderr_path.write_text(core_run.stderr, encoding="utf-8")
    core_report, parse_error = parse_pmb_core_report(core_run.stdout)
    if core_report is not None:
        core_report_path.write_text(
            json.dumps(core_report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    evidence = build_pmb_desktop_replay_execution_evidence(
        packages_root=packages_root,
        package_root=package_root,
        command=command,
        core_run=core_run,
        core_report=core_report,
        core_report_path=core_report_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        started_utc=started_utc,
        ended_utc=ended_utc,
        parse_error=parse_error,
    )
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    validation_report = validate_pmb_desktop_replay_execution_evidence(evidence)
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_pmb_host_run_evidence(out, validation_path, evidence)
    return 0 if validation_report["status"] == "pass" else core_run.returncode or 2


def run_pmb_live_route_self_test(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    route_report_path = out.with_name(f"{out.stem}.live-broker-route-report.json")
    stdout_path = out.with_name(f"{out.stem}.stdout.txt")
    stderr_path = out.with_name(f"{out.stem}.stderr.txt")
    started_utc = datetime.now(UTC)
    command = [
        args.cargo,
        "run",
        "--quiet",
        "-p",
        "projected-motion-breath-core",
        "--",
        "live-route-self-test",
        "--package-root",
        str(package_root),
    ]
    core_run = run_captured(command, allow_failure=True, cwd=packages_root)
    ended_utc = datetime.now(UTC)
    stdout_path.write_text(core_run.stdout, encoding="utf-8")
    stderr_path.write_text(core_run.stderr, encoding="utf-8")
    route_report, parse_error = parse_pmb_core_report(core_run.stdout)
    if route_report is not None:
        route_report_path.write_text(
            json.dumps(route_report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    evidence = build_pmb_live_route_self_test_evidence(
        packages_root=packages_root,
        package_root=package_root,
        command=command,
        core_run=core_run,
        route_report=route_report,
        route_report_path=route_report_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        started_utc=started_utc,
        ended_utc=ended_utc,
        parse_error=parse_error,
    )
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    validation_report = validate_pmb_live_route_self_test_evidence(evidence)
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_pmb_live_route_host_run_evidence(out, validation_path, evidence)
    return 0 if validation_report["status"] == "pass" else core_run.returncode or 2


def run_pmb_shell_handoff(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    handoff_path = Path(args.handoff) if getattr(args, "handoff", None) else default_pmb_shell_handoff_path(package_root)
    if not handoff_path.exists():
        raise SystemExit(f"PMB shell handoff manifest not found: {handoff_path}")
    started_utc = datetime.now(UTC)
    evidence = build_pmb_shell_handoff_validation_evidence(
        packages_root=packages_root,
        package_root=package_root,
        handoff_path=handoff_path,
        started_utc=started_utc,
        ended_utc=datetime.now(UTC),
    )
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    validation_report = validate_pmb_shell_handoff_validation_evidence(evidence)
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_pmb_shell_handoff_host_run_evidence(out, validation_path, evidence)
    return 0 if validation_report["status"] == "pass" else 2


def run_android_capture(args: argparse.Namespace, out: Path) -> int:
    if not args.adb or not args.serial:
        raise SystemExit("--adb and --serial are required for phone and quest targets")
    host_profile = "headset" if args.target == "quest" else "mobile"
    run([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    clear_android_live_artifacts(args)
    command = [
        args.adb,
        "-s",
        args.serial,
        "shell",
        "am",
        "start",
        "-a",
        ANDROID_ACTION,
        "-n",
        f"{ANDROID_PACKAGE}/.MainActivity",
        "--es",
        "mode",
        args.stream if args.stream else "module",
        "--es",
        "host_profile",
        host_profile,
        "--el",
        "duration_ms",
        str(int(args.duration_seconds * 1000)),
        "--ei",
        "acc_rate_hz",
        str(args.acc_rate),
        "--es",
        "telemetry_page",
        args.telemetry_page,
    ]
    if args.device_address:
        command.extend(["--es", "device_address", args.device_address])
    if args.module:
        command.extend(["--es", "modules", ",".join(args.module)])
    append_rmssd_baseline_extras(command, args)
    run(command)
    wait_for_android_evidence(args, args.duration_seconds + 90.0)
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_EVIDENCE, str(out)])
    pull_android_runtime_artifacts(args, out)
    return validate_evidence(args, out, "headset" if args.target == "quest" else "mobile")


def run_android_replay(args: argparse.Namespace) -> int:
    if not args.adb or not args.serial:
        raise SystemExit("--adb and --serial are required for phone and quest replay targets")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    host_profile = "headset" if args.target == "quest" else "mobile"
    run([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    clear_android_live_artifacts(args)
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "shell",
            "am",
            "start",
            "-a",
            ANDROID_REPLAY_ACTION,
            "-n",
            f"{ANDROID_PACKAGE}/.MainActivity",
            "--es",
            "host_profile",
            host_profile,
            "--es",
            "modules",
            ",".join(args.module),
        ]
    )
    wait_for_android_evidence(args, 15.0)
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_EVIDENCE, str(out)])
    pull_android_runtime_artifacts(args, out)
    return validate_evidence(args, out, host_profile)


def run_android_pmb_replay(args: argparse.Namespace) -> int:
    if not args.adb or not args.serial:
        raise SystemExit("--adb and --serial are required for phone and quest PMB replay targets")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    host_profile = "headset" if args.target == "quest" else "mobile"
    run([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    clear_android_pmb_artifacts(args)
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "shell",
            "am",
            "start",
            "-a",
            ANDROID_PMB_REPLAY_ACTION,
            "-n",
            f"{ANDROID_PACKAGE}/.MainActivity",
            "--es",
            "host_profile",
            host_profile,
        ]
    )
    wait_for_android_file(args, ANDROID_REMOTE_PMB_EVIDENCE, 30.0)
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_EVIDENCE, str(out)])
    core_report_path = out.with_name(f"{out.stem}.core-validation-report.json")
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_CORE_REPORT, str(core_report_path)])
    evidence = json.loads(out.read_text(encoding="utf-8"))
    validation_report = validate_pmb_android_replay_execution_evidence(
        evidence,
        package_root=package_root,
        target=args.target,
        host_profile=host_profile,
    )
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_pmb_android_host_run_evidence(out, validation_path, evidence, args.target, host_profile)
    return 0 if validation_report["status"] == "pass" else 2


def run_pmb_controller_preflight(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    host_profile = "headset" if args.target == "quest" else "mobile"
    run([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    clear_android_pmb_controller_preflight_artifacts(args)
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "shell",
            "am",
            "start",
            "-a",
            ANDROID_PMB_CONTROLLER_PREFLIGHT_ACTION,
            "-n",
            f"{ANDROID_PACKAGE}/.MainActivity",
            "--es",
            "host_profile",
            host_profile,
        ]
    )
    wait_for_android_file(args, ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE, 30.0)
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE, str(out)])
    report_path = out.with_name(f"{out.stem}.controller-preflight-report.json")
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "pull",
            ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_REPORT,
            str(report_path),
        ]
    )
    evidence = json.loads(out.read_text(encoding="utf-8"))
    validation_report = validate_pmb_controller_preflight_evidence(
        evidence,
        package_root=package_root,
        target=args.target,
        host_profile=host_profile,
    )
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_pmb_controller_preflight_host_run_evidence(
            out,
            validation_path,
            evidence,
            args.target,
            host_profile,
        )
    return 0 if validation_report["status"] == "pass" else 2


def run_pmb_quest_simulated_live(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    host_profile = "headset"
    if not getattr(args, "no_launch_broker", False):
        run([args.adb, "-s", args.serial, "shell", "am", "start", "-n", args.broker_activity])
    if not getattr(args, "no_launch_makepad", False):
        configure_makepad_breath_feedback_receiver(args)
    clear_android_pmb_simulated_live_artifacts(args)
    run([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "shell",
            "am",
            "start",
            "-a",
            ANDROID_PMB_SIMULATED_LIVE_ACTION,
            "-n",
            f"{ANDROID_PACKAGE}/.MainActivity",
            "--es",
            "host_profile",
            host_profile,
            "--es",
            "broker_host",
            "127.0.0.1",
            "--es",
            "broker_port",
            str(args.broker_port),
            "--es",
            "feedback_publish_limit",
            str(args.feedback_publish_limit),
            "--es",
            "receipt_listen_ms",
            str(int(max(0.0, args.receipt_listen_seconds) * 1000.0)),
        ]
    )
    wait_for_android_file(args, ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE, 45.0)
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE, str(out)])
    route_report_path = out.with_name(f"{out.stem}.live-route-report.json")
    broker_report_path = out.with_name(f"{out.stem}.broker-publish-report.json")
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "pull",
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_ROUTE_REPORT,
            str(route_report_path),
        ]
    )
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "pull",
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_BROKER_REPORT,
            str(broker_report_path),
        ]
    )
    evidence = json.loads(out.read_text(encoding="utf-8"))
    validation_report = validate_pmb_quest_simulated_live_evidence(
        evidence,
        package_root=package_root,
        target=args.target,
        host_profile=host_profile,
    )
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_pmb_quest_simulated_live_host_run_evidence(
            out,
            validation_path,
            evidence,
            args.target,
            host_profile,
        )
    return 0 if validation_report["status"] == "pass" else 2


def run_pmb_quest_physical_live(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    if args.duration_seconds <= 0:
        raise SystemExit("--duration-seconds must be greater than zero")
    host_profile = "headset"
    if not getattr(args, "no_launch_broker", False):
        grant_broker_runtime_permissions(args)
        run([args.adb, "-s", args.serial, "shell", "am", "start", "-n", args.broker_activity])
    if not getattr(args, "no_launch_makepad", False):
        configure_makepad_physical_pmb_provider(args)
    clear_android_pmb_physical_live_artifacts(args)
    run([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    command = pmb_physical_live_start_command(args, host_profile)
    run(command)
    wait_seconds = (
        max(0.0, float(args.scan_timeout_seconds))
        + max(0.0, float(args.duration_seconds))
        + max(0.0, float(args.receipt_listen_seconds))
        + 30.0
    )
    wait_for_android_file(args, ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE, wait_seconds)
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE, str(out)])
    capture_report_path = out.with_name(f"{out.stem}.input-capture-report.json")
    events_jsonl_path = out.with_name(f"{out.stem}.transport-events.jsonl")
    route_report_path = out.with_name(f"{out.stem}.live-route-report.json")
    broker_report_path = out.with_name(f"{out.stem}.broker-publish-report.json")
    for remote, local in [
        (ANDROID_REMOTE_PMB_PHYSICAL_LIVE_CAPTURE_REPORT, capture_report_path),
        (ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVENTS_JSONL, events_jsonl_path),
        (ANDROID_REMOTE_PMB_PHYSICAL_LIVE_ROUTE_REPORT, route_report_path),
        (ANDROID_REMOTE_PMB_PHYSICAL_LIVE_BROKER_REPORT, broker_report_path),
    ]:
        run([args.adb, "-s", args.serial, "pull", remote, str(local)])
    evidence = json.loads(out.read_text(encoding="utf-8"))
    validation_report = validate_pmb_quest_physical_live_evidence(
        evidence,
        package_root=package_root,
        target=args.target,
        host_profile=host_profile,
    )
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_pmb_quest_physical_live_host_run_evidence(
            out,
            validation_path,
            evidence,
            args.target,
            host_profile,
        )
    return 0 if validation_report["status"] == "pass" else 2


def pmb_physical_live_start_command(args: argparse.Namespace, host_profile: str) -> list[str]:
    if getattr(args, "foreground_hostess", False):
        command = [
            args.adb,
            "-s",
            args.serial,
            "shell",
            "am",
            "start",
            "-a",
            ANDROID_PMB_PHYSICAL_LIVE_ACTION,
            "-n",
            f"{ANDROID_PACKAGE}/.MainActivity",
        ]
    else:
        command = [
            args.adb,
            "-s",
            args.serial,
            "shell",
            "am",
            "start-foreground-service",
            "-a",
            ANDROID_PMB_PHYSICAL_LIVE_BACKGROUND_ACTION,
            "-n",
            ANDROID_PMB_PHYSICAL_LIVE_SERVICE,
        ]
    command.extend([
        "--es",
        "host_profile",
        host_profile,
        "--es",
        "broker_host",
        "127.0.0.1",
        "--es",
        "broker_port",
        str(args.broker_port),
        "--es",
        "duration_ms",
        str(int(max(0.0, args.duration_seconds) * 1000.0)),
        "--es",
        "acc_rate_hz",
        str(args.acc_rate),
        "--es",
        "scan_timeout_ms",
        str(int(max(0.0, args.scan_timeout_seconds) * 1000.0)),
        "--es",
        "controller_wait_ms",
        str(int(max(0.0, args.controller_wait_seconds) * 1000.0)),
        "--es",
        "feedback_publish_limit",
        str(args.feedback_publish_limit),
        "--es",
        "receipt_listen_ms",
        str(int(max(0.0, args.receipt_listen_seconds) * 1000.0)),
    ])
    if args.device_address:
        command.extend(["--es", "device_address", args.device_address])
    return command


def observe_broker_telemetry_ui(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.duration_seconds <= 0:
        raise SystemExit("--duration-seconds must be greater than zero")
    if not getattr(args, "no_launch_broker", False):
        grant_broker_runtime_permissions(args)
        run([args.adb, "-s", args.serial, "shell", "am", "start", "-n", args.broker_activity])
    clear_android_broker_telemetry_artifacts(args)
    command = [
        args.adb,
        "-s",
        args.serial,
        "shell",
        "am",
        "start",
        "-a",
        ANDROID_BROKER_TELEMETRY_ACTION,
        "-n",
        f"{ANDROID_PACKAGE}/.MainActivity",
        "--es",
        "host_profile",
        "headset",
        "--es",
        "broker_host",
        "127.0.0.1",
        "--es",
        "broker_port",
        str(args.broker_port),
        "--es",
        "duration_ms",
        str(int(max(0.0, args.duration_seconds) * 1000.0)),
        "--es",
        "acc_rate_hz",
        str(args.acc_rate),
        "--es",
        "scan_timeout_ms",
        str(int(max(0.0, args.scan_timeout_seconds) * 1000.0)),
        "--es",
        "telemetry_page",
        args.telemetry_page,
        "--ez",
        "request_provider_start",
        "false" if args.no_request_provider_start else "true",
        "--ez",
        "stop_provider_on_finish",
        "false" if args.keep_provider_running else "true",
    ]
    if args.device_address:
        command.extend(["--es", "device_address", args.device_address])
    run(command)
    wait_seconds = (
        max(0.0, float(args.duration_seconds))
        + (0.0 if args.no_request_provider_start else max(0.0, float(args.scan_timeout_seconds)))
        + 20.0
    )
    wait_for_android_file(args, ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE, wait_seconds)
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE, str(out)])
    report_path = out.with_name(f"{out.stem}.broker-telemetry-report.json")
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_BROKER_TELEMETRY_REPORT, str(report_path)])
    evidence = json.loads(out.read_text(encoding="utf-8"))
    validation_report = validate_broker_telemetry_observer_evidence(evidence)
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if args.render_out:
        render_args = argparse.Namespace(
            target=args.target,
            adb=args.adb,
            serial=args.serial,
            out=args.render_out,
            input=None,
            name=Path(args.render_out).name,
            page=args.telemetry_page,
            source_evidence_path="hostess-t/evidence/broker-telemetry/latest.json",
        )
        render_telemetry(render_args)
    return 0 if validation_report["status"] == "pass" else 2


def validate_broker_telemetry_observer_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    capture = evidence.get("capture", {})
    broker_report = evidence.get("broker_report", {})
    streams = [stream for stream in evidence.get("streams", []) if isinstance(stream, dict)]
    polar_stream = next(
        (stream for stream in streams if stream.get("stream_id") == "bio:polar_acc"),
        {},
    )
    checks = [
        recording_scorecard_check(
            "hostess.check.broker_telemetry.schema",
            evidence.get("$schema") == "rusty.hostess.broker_telemetry_observer.evidence.v1",
            "broker telemetry observer evidence schema is supported",
        ),
        recording_scorecard_check(
            "hostess.check.broker_telemetry.observer_boundary",
            capture.get("direct_ble_used") is False
            and evidence.get("direct_ble_used") is False
            and capture.get("hostess_role") == "foreground_telemetry_ui_observer",
            "foreground telemetry UI observes broker streams and does not open direct BLE",
        ),
        recording_scorecard_check(
            "hostess.check.broker_telemetry.broker_transport",
            capture.get("broker_transport_used") is True
            and broker_report.get("broker_connected") is True,
            "broker WebSocket transport was used by the foreground telemetry UI",
        ),
        recording_scorecard_check(
            "hostess.check.broker_telemetry.stream",
            polar_stream.get("status") == "pass"
            and int(polar_stream.get("sample_count") or 0) > 0
            and int(broker_report.get("frame_count") or 0) > 0,
            "bio:polar_acc broker stream produced frames for visualization",
        ),
        recording_scorecard_check(
            "hostess.check.broker_telemetry.status",
            evidence.get("status") == "pass"
            and broker_report.get("status") == "pass"
            and evidence.get("telemetry_ui_visualized") is True,
            "foreground telemetry observer run passed and visualized live telemetry",
        ),
    ]
    errors = [check["evidence"] for check in checks if check["status"] != "pass"]
    return {
        "$schema": "rusty.hostess.broker_telemetry_observer.validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def run_manifold_value_recording(args: argparse.Namespace) -> int:
    if args.duration_seconds <= 0:
        raise SystemExit("--duration-seconds must be greater than zero")
    if not args.value:
        raise SystemExit("record-values requires at least one --value")
    if args.target in {"phone", "quest"} and not args.plan_only and (not args.adb or not args.serial):
        raise SystemExit("--adb and --serial are required for phone and quest recording targets")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    requested_values = normalize_manifold_recording_values(args.value)
    host_profile = host_profile_for_target(args.target)
    provider_plans = [
        manifold_value_provider_plan(value, target=args.target)
        for value in requested_values
    ]
    route_status, route_reasons = manifold_recording_route_status(
        provider_plans,
        plan_only=args.plan_only,
    )
    if args.pmb_live_processor and not pmb_live_processor_inputs_ready(provider_plans):
        route_status = "blocked"
        route_reasons.append(
            "PMB live processor bridge requires stream.polar_h10.acc and stream.motion.object_pose"
        )
    started_utc = datetime.now(UTC)
    capture_status: int | None = None
    capture_evidence: dict[str, Any] | None = None
    capture_evidence_path: Path | None = None

    if not args.plan_only and route_status == "ready":
        if all(plan.get("recording_route") == "hostessctl.broker-websocket-record" for plan in provider_plans):
            capture_evidence_path = out.with_name(
                f"{out.stem}.{recording_segment(requested_values)}.broker-streams.json"
            )
            capture_status = record_broker_websocket_streams(args, provider_plans, capture_evidence_path)
        else:
            plan = provider_plans[0]
            capture_evidence_path = out.with_name(
                f"{out.stem}.{recording_segment([plan['stream_id']])}.live-capture.json"
            )
            capture_status = run_live_capture(
                single_value_live_capture_args(args, plan, capture_evidence_path)
            )
        if capture_evidence_path.exists():
            capture_evidence = json.loads(capture_evidence_path.read_text(encoding="utf-8"))

    ended_utc = datetime.now(UTC)
    evidence = build_manifold_value_recording_evidence(
        args=args,
        requested_values=requested_values,
        provider_plans=provider_plans,
        route_status=route_status,
        route_reasons=route_reasons,
        host_profile=host_profile,
        started_utc=started_utc,
        ended_utc=ended_utc,
        capture_status=capture_status,
        capture_evidence_path=capture_evidence_path,
        capture_evidence=capture_evidence,
    )
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    validation_report = validate_manifold_value_recording_evidence(evidence)
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_manifold_value_recording_host_run_evidence(out, validation_path, evidence)
    if validation_report["status"] != "pass":
        return 2
    if evidence["status"] == "blocked" and not args.allow_blocked:
        return 2
    if evidence["status"] == "fail":
        return capture_status or 2
    return 0


def normalize_manifold_recording_values(raw_values: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw_value in raw_values:
        value = raw_value.strip()
        if not value:
            raise SystemExit("record-values received an empty --value")
        normalized_value = MANIFOLD_VALUE_ALIASES.get(value, value)
        if normalized_value not in normalized:
            normalized.append(normalized_value)
    return normalized


def host_profile_for_target(target: str) -> str:
    if target == "quest":
        return "headset"
    if target == "phone":
        return "mobile"
    return "desktop"


def manifold_value_provider_plan(value_id: str, *, target: str) -> dict[str, Any]:
    provider = MANIFOLD_VALUE_PROVIDERS.get(value_id)
    if provider is None:
        return {
            "value_id": value_id,
            "stream_id": value_id if value_id.startswith("stream.") else None,
            "provider_id": None,
            "provider_kind": None,
            "sample_kind": None,
            "target": target,
            "status": "unknown",
            "live_supported": False,
            "preflight_supported": False,
            "single_value_live_route_supported": False,
            "combined_recording_supported": False,
            "blocked_reason": "value is not in the Hostess Manifold recording provider registry",
        }

    supported_targets = list(provider.get("supported_targets", []))
    target_supported = target in supported_targets
    single_live = bool(provider.get("single_value_live_route_supported")) and target_supported
    broker_live = bool(provider.get("broker_websocket_recording_supported")) and target == "quest" and target_supported
    status = "ready" if single_live or broker_live else "requires_provider"
    blocked_reason = provider.get("blocked_reason")
    if not target_supported:
        status = "unavailable_on_target"
        blocked_reason = f"value is not available on target {target}"
    recording_route = None
    if broker_live:
        recording_route = "hostessctl.broker-websocket-record"
    elif single_live:
        recording_route = "hostessctl.run-live"
    return {
        "value_id": provider["value_id"],
        "requested_value_id": value_id,
        "stream_id": provider["stream_id"],
        "broker_stream_id": provider.get("broker_stream_id", provider["stream_id"]),
        "provider_id": provider["provider_id"],
        "provider_kind": provider["provider_kind"],
        "package_id": provider.get("package_id"),
        "sample_kind": provider.get("sample_kind"),
        "target": target,
        "supported_targets": supported_targets,
        "status": status,
        "live_supported": single_live,
        "broker_websocket_recording_supported": broker_live,
        "preflight_supported": bool(provider.get("preflight_supported")),
        "single_value_live_route_supported": single_live,
        "combined_recording_supported": broker_live,
        "recording_route": recording_route,
        "live_stream_mode": provider.get("live_stream_mode"),
        "preflight_route": provider.get("preflight_route"),
        "broker_start_command": provider.get("broker_start_command"),
        "broker_stop_command": provider.get("broker_stop_command"),
        "provider_launch": provider.get("provider_launch"),
        "blocked_reason": blocked_reason,
    }


def manifold_recording_route_status(
    provider_plans: list[dict[str, Any]],
    *,
    plan_only: bool,
) -> tuple[str, list[str]]:
    if not provider_plans:
        return "blocked", ["no values were requested"]
    blocked_reasons = [
        str(plan.get("blocked_reason") or f"{plan.get('stream_id') or plan.get('value_id')} is not recordable")
        for plan in provider_plans
        if plan.get("status") != "ready"
    ]
    if len(provider_plans) > 1 and not all(
        plan.get("combined_recording_supported")
        and plan.get("recording_route") == "hostessctl.broker-websocket-record"
        for plan in provider_plans
    ):
        blocked_reasons.append(
            "simultaneous multi-value recording is not implemented for the selected provider set"
        )
    if blocked_reasons:
        return "blocked", blocked_reasons
    if plan_only:
        return "ready", []
    return "ready", []


def pmb_live_processor_inputs_ready(provider_plans: list[dict[str, Any]]) -> bool:
    stream_ids = {str(plan.get("stream_id")) for plan in provider_plans}
    return {
        "stream.polar_h10.acc",
        "stream.motion.object_pose",
    }.issubset(stream_ids)


def single_value_live_capture_args(
    args: argparse.Namespace,
    plan: dict[str, Any],
    out: Path,
) -> argparse.Namespace:
    return argparse.Namespace(
        target=args.target,
        stream=plan["live_stream_mode"],
        module=[],
        out=str(out),
        packages_root=args.packages_root,
        duration_seconds=args.duration_seconds,
        device_address=args.device_address,
        adb=args.adb,
        serial=args.serial,
        acc_rate=args.acc_rate,
        runtime_core=args.runtime_core,
        rmssd_baseline_ln_rmssd=None,
        rmssd_baseline_mean_ln_rmssd=None,
        rmssd_baseline_sd_ln_rmssd=None,
        rmssd_baseline_window_count=None,
        rmssd_baseline_source="explicit_baseline",
        telemetry_page=args.telemetry_page,
    )


class BrokerWebSocketClient:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        path: str = MANIFOLD_BROKER_EVENTS_PATH,
        timeout: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.path = path
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {self.key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self._read_http_response()
        status_line = response.split(b"\r\n", 1)[0]
        if b" 101 " not in status_line:
            raise RuntimeError(f"broker websocket handshake failed: {status_line.decode('ascii', 'replace')}")
        expected_accept = base64.b64encode(
            hashlib.sha1((self.key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        headers = {}
        for line in response.split(b"\r\n")[1:]:
            if b":" not in line:
                continue
            name, value = line.split(b":", 1)
            headers[name.decode("ascii", "ignore").strip().lower()] = value.decode("ascii", "ignore").strip()
        if headers.get("sec-websocket-accept") != expected_accept:
            raise RuntimeError("broker websocket handshake accept header did not match")

    def close(self) -> None:
        try:
            self._send_frame(b"", opcode=0x8)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    def send_json(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        self._send_frame(data, opcode=0x1)

    def recv_json(self, *, timeout: float) -> dict[str, Any] | None:
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(timeout)
        try:
            while True:
                opcode, payload = self._recv_frame()
                if opcode == 0x1:
                    return json.loads(payload.decode("utf-8"))
                if opcode == 0x8:
                    return None
                if opcode == 0x9:
                    self._send_frame(payload, opcode=0xA)
        except socket.timeout:
            return None
        finally:
            self.sock.settimeout(old_timeout)

    def _read_http_response(self) -> bytes:
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > 65536:
                raise RuntimeError("broker websocket handshake response exceeded 64 KiB")
        return bytes(data)

    def _send_frame(self, payload: bytes, *, opcode: int) -> None:
        header = bytearray()
        header.append(0x80 | (opcode & 0x0F))
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length <= 0xFFFF:
            header.append(0x80 | 126)
            header.extend(length.to_bytes(2, "big"))
        else:
            header.append(0x80 | 127)
            header.extend(length.to_bytes(8, "big"))
        mask = os.urandom(4)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def _recv_frame(self) -> tuple[int, bytes]:
        first = self._read_exact(2)
        opcode = first[0] & 0x0F
        masked = bool(first[1] & 0x80)
        length = first[1] & 0x7F
        if length == 126:
            length = int.from_bytes(self._read_exact(2), "big")
        elif length == 127:
            length = int.from_bytes(self._read_exact(8), "big")
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length) if length else b""
        if masked:
            payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        return opcode, payload

    def _read_exact(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise RuntimeError("broker websocket closed while reading")
            data.extend(chunk)
        return bytes(data)


def record_broker_websocket_streams(
    args: argparse.Namespace,
    provider_plans: list[dict[str, Any]],
    out: Path,
) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    started_monotonic = time.monotonic()
    requested_streams = [
        {
            "stream_id": str(plan["stream_id"]),
            "broker_stream_id": str(plan.get("broker_stream_id") or plan["stream_id"]),
            "provider_id": plan.get("provider_id"),
            "provider_kind": plan.get("provider_kind"),
        }
        for plan in provider_plans
    ]
    stream_rows: dict[str, dict[str, Any]] = {
        stream["broker_stream_id"]: {
            **stream,
            "status": "missing",
            "event_count": 0,
            "sample_count": 0,
            "first_event_at_utc": None,
            "last_event_at_utc": None,
        }
        for stream in requested_streams
    }
    provider_actions: list[dict[str, Any]] = []
    broker_acks: list[dict[str, Any]] = []
    errors: list[str] = []
    events_jsonl = out.with_name(f"{out.stem}.events.jsonl")
    ws: BrokerWebSocketClient | None = None
    polar_started = False
    makepad_publish_enabled = False
    makepad_breath_feedback_enabled = False
    pmb_bridge_enabled = bool(getattr(args, "pmb_live_processor", False)) and pmb_live_processor_inputs_ready(provider_plans)
    pmb_bridge: dict[str, Any] = {
        "requested": bool(getattr(args, "pmb_live_processor", False)),
        "enabled": pmb_bridge_enabled,
        "status": "not_requested" if not getattr(args, "pmb_live_processor", False) else "pending",
        "artifacts": [],
    }
    forward_spec = f"tcp:{args.broker_local_port}"

    if pmb_bridge_enabled:
        for broker_stream_id, sample_kind in [
            ("stream.breath.volume", "breath_volume"),
            ("stream.breath.feedback_state", "breath_feedback_state"),
            ("stream.breath.feedback_receipt", "breath_feedback_receipt"),
        ]:
            stream_rows[broker_stream_id] = {
                "stream_id": broker_stream_id,
                "broker_stream_id": broker_stream_id,
                "provider_id": "processor.projected_motion_breath.live_bridge",
                "provider_kind": "processor_bridge_output",
                "sample_kind": sample_kind,
                "status": "missing",
                "event_count": 0,
                "sample_count": 0,
                "first_event_at_utc": None,
                "last_event_at_utc": None,
                "pmb_bridge_stream": True,
            }

    def run_adb(label: str, command: list[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
        result = run_captured(command, allow_failure=True)
        provider_actions.append(
            {
                "action": label,
                "command": redact_command(command),
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "status": "pass" if result.returncode == 0 else "fail",
            }
        )
        if result.returncode != 0 and not allow_failure:
            message = f"{label} failed with exit code {result.returncode}"
            errors.append(message)
            raise RuntimeError(message)
        return result

    def send_broker_command(command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        assert ws is not None
        request_id = f"hostess-record-values-{command.replace('.', '-')}-{len(broker_acks) + 1}"
        message = broker_command_message(command, params=params, request_id=request_id)
        ws.send_json(message)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            reply = ws.recv_json(timeout=0.25)
            if reply is None:
                continue
            if reply.get("type") == "stream_event":
                accept_broker_stream_event(reply, stream_rows, events_jsonl)
                continue
            if reply.get("request_id") == request_id or reply.get("command") == command:
                ok = broker_ack_accepted(reply)
                ack = {
                    "command": command,
                    "request_id": request_id,
                    "status": "pass" if ok else "fail",
                    "reply": reply,
                }
                broker_acks.append(ack)
                if not ok:
                    errors.append(f"broker command {command} failed: {reply}")
                return ack
        ack = {
            "command": command,
            "request_id": request_id,
            "status": "unknown",
            "reply": None,
        }
        broker_acks.append(ack)
        errors.append(f"broker command {command} did not return an acknowledgement")
        return ack

    try:
        run_adb("adb-forward-remove-existing", adb_prefix(args) + ["forward", "--remove", forward_spec], allow_failure=True)
        if not args.no_launch_broker:
            run_adb(
                "launch-broker",
                adb_prefix(args) + ["shell", "am", "start", "-n", args.broker_activity],
                allow_failure=False,
            )
        run_adb(
            "adb-forward-broker-websocket",
            adb_prefix(args) + ["forward", forward_spec, f"tcp:{args.broker_port}"],
            allow_failure=False,
        )
        ws = connect_broker_websocket_with_retry(
            "127.0.0.1",
            int(args.broker_local_port),
            provider_actions,
            errors,
        )
        ws.send_json(
            {
                "type": "hello",
                "client_id": "hostessctl.record_values",
                "app_package": "rusty-hostess",
                "role": "hostess_manifold_value_recorder",
            }
        )
        ws.recv_json(timeout=1.0)
        events_jsonl.write_text("", encoding="utf-8")
        for stream in requested_streams:
            send_broker_command("subscribe", {"stream": stream["broker_stream_id"]})
        if pmb_bridge_enabled:
            send_broker_command("subscribe", {"stream": "stream.breath.volume"})
            send_broker_command("subscribe", {"stream": "stream.breath.feedback_state"})
            send_broker_command("subscribe", {"stream": "stream.breath.feedback_receipt"})
        for plan in provider_plans:
            if plan.get("broker_start_command") == "polar_pmd.start":
                send_broker_command(
                    "polar_pmd.start",
                    {
                        "device_address": args.device_address or "",
                        "scan_timeout_ms": 30000,
                        "pmd_stream": "acc",
                        "acc_sample_rate_hz": args.acc_rate,
                        "high_connection_priority": True,
                    },
                )
                polar_started = True
            if plan.get("provider_launch") == "makepad_xr_controller_pose" and not args.no_launch_providers:
                configure_makepad_controller_pose_provider(
                    args,
                    run_adb,
                    enable_breath_feedback=pmb_bridge_enabled,
                )
                makepad_publish_enabled = True
                makepad_breath_feedback_enabled = pmb_bridge_enabled
                wait_for_makepad_controller_pose_ready(
                    args,
                    ws,
                    provider_actions,
                    errors,
                )
        deadline = time.monotonic() + float(args.duration_seconds)
        with events_jsonl.open("a", encoding="utf-8") as events_file:
            while time.monotonic() < deadline:
                remaining = max(0.05, min(0.5, deadline - time.monotonic()))
                message = ws.recv_json(timeout=remaining)
                if message is None:
                    continue
                if message.get("type") == "stream_event":
                    accept_broker_stream_event(message, stream_rows, events_jsonl, events_file=events_file)
                else:
                    broker_acks.append(
                        {
                            "command": str(message.get("command") or message.get("type") or "broker-message"),
                            "request_id": message.get("request_id"),
                            "status": "observed",
                            "reply": message,
                        }
                    )
        if pmb_bridge_enabled and ws is not None:
            pmb_bridge = run_pmb_live_processor_bridge(args, events_jsonl, out)
            if pmb_bridge.get("status") == "pass":
                publish_result = publish_pmb_feedback_samples(
                    args,
                    pmb_bridge.get("route_report") if isinstance(pmb_bridge.get("route_report"), dict) else {},
                    send_broker_command,
                )
                pmb_bridge["publish"] = publish_result
                if not publish_result.get("published"):
                    errors.append("PMB live processor bridge produced no published feedback samples")
                listen_for_pmb_receipts(args, ws, stream_rows, events_jsonl, broker_acks)
            else:
                errors.append(f"PMB live processor bridge failed: {pmb_bridge.get('error') or pmb_bridge.get('status')}")
    except Exception as ex:
        errors.append(str(ex))
    finally:
        if ws is not None:
            try:
                if polar_started:
                    request_id = "hostess-record-values-polar-pmd-stop"
                    ws.send_json(broker_command_message("polar_pmd.stop", request_id=request_id))
            except Exception as ex:
                errors.append(f"polar_pmd.stop cleanup failed: {ex}")
            ws.close()
        if makepad_publish_enabled:
            for key in [
                "debug.rusty.manifold.pose.publish.enabled",
                "debug.rustyxr.manifold.pose.publish.enabled",
            ]:
                run_adb(
                    f"disable-makepad-pose-publish-{key}",
                    adb_prefix(args) + ["shell", "setprop", key, "false"],
                    allow_failure=True,
                )
        if makepad_breath_feedback_enabled:
            for key in [
                "debug.rusty.manifold.breath.feedback.enabled",
                "debug.rustyxr.manifold.breath.feedback.enabled",
            ]:
                run_adb(
                    f"disable-makepad-breath-feedback-subscriber-{key}",
                    adb_prefix(args) + ["shell", "setprop", key, "false"],
                    allow_failure=True,
                )
        run_adb("adb-forward-remove-broker-websocket", adb_prefix(args) + ["forward", "--remove", forward_spec], allow_failure=True)

    ended = datetime.now(UTC)
    for row in stream_rows.values():
        if int(row["event_count"]) > 0:
            row["status"] = "pass"
            row["sample_count"] = row["event_count"]
    missing = [
        row["stream_id"]
        for row in stream_rows.values()
        if row["status"] != "pass"
    ]
    errors.extend([f"missing stream events for {stream_id}" for stream_id in missing])
    status = "pass" if not missing and not errors else "fail"
    has_object_pose = any(row["stream_id"] == "stream.motion.object_pose" for row in stream_rows.values())
    object_pose_events = any(
        row["stream_id"] == "stream.motion.object_pose" and row["status"] == "pass"
        for row in stream_rows.values()
    )
    pmb_publish = pmb_bridge.get("publish") if isinstance(pmb_bridge.get("publish"), dict) else {}
    pmb_feedback_published = bool(pmb_publish.get("published"))
    pmb_breath_publish_count = int(pmb_publish.get("breath_published_count") or 0)
    pmb_feedback_publish_count = int(pmb_publish.get("feedback_published_count") or 0)
    pmb_receipt_count = int(
        stream_rows.get("stream.breath.feedback_receipt", {}).get("event_count") or 0
    )
    evidence = {
        "$schema": "rusty.hostess.broker_stream_recording.evidence.v1",
        "status": status,
        "target": args.target,
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
        "duration_ms": int((ended - started).total_seconds() * 1000),
        "requested_duration_ms": int(args.duration_seconds * 1000),
        "transport": {
            "kind": "adb-forwarded-broker-websocket",
            "websocket_url": f"ws://127.0.0.1:{args.broker_local_port}{MANIFOLD_BROKER_EVENTS_PATH}",
            "broker_device_port": args.broker_port,
            "host_forward_port": args.broker_local_port,
            "adb_serial": args.serial,
        },
        "provider_actions": provider_actions,
        "broker_acks": broker_acks,
        "streams": list(stream_rows.values()),
        "missing_streams": missing,
        "events_jsonl": str(events_jsonl),
        "errors": errors,
        "quest_execution_performed": args.target == "quest",
        "broker_websocket_recording": True,
        "pmb_live_processor_requested": bool(getattr(args, "pmb_live_processor", False)),
        "pmb_live_processor_enabled": pmb_bridge_enabled,
        "pmb_processor_executed": bool(
            pmb_bridge_enabled
            and pmb_bridge.get("status") == "pass"
            and isinstance(pmb_bridge.get("route_report"), dict)
            and pmb_bridge["route_report"].get("processor_core_executed") is True
        ),
        "pmb_breath_published": pmb_breath_publish_count > 0,
        "pmb_breath_publish_count": pmb_breath_publish_count,
        "pmb_feedback_published": pmb_feedback_published and pmb_feedback_publish_count > 0,
        "pmb_feedback_publish_count": pmb_feedback_publish_count,
        "pmb_feedback_receipt_count": pmb_receipt_count,
        "pmb_processor_bridge": pmb_bridge,
        "makepad_breath_feedback_subscriber_configured": makepad_breath_feedback_enabled,
        "makepad_breath_feedback_subscriber_flags_owner": "hostessctl.record_values",
        "controller_provider_route_ready": has_object_pose and (makepad_publish_enabled or object_pose_events),
        "polar_provider_route_ready": any(plan.get("broker_start_command") == "polar_pmd.start" for plan in provider_plans),
        "controller_input_used": object_pose_events,
        "physical_controller_input_used": object_pose_events,
        "manual_controller_trial_required": has_object_pose and not object_pose_events,
        "elapsed_monotonic_ms": int((time.monotonic() - started_monotonic) * 1000),
    }
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    validation = validate_broker_websocket_stream_recording_evidence(evidence)
    out.with_name(f"{out.stem}.validation-report.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return 0 if status == "pass" else 2


def adb_prefix(args: argparse.Namespace) -> list[str]:
    return [args.adb, "-s", args.serial]


def broker_command_message(
    command: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "type": "command",
        "schema": MANIFOLD_COMMAND_SCHEMA,
        "request_id": request_id or f"hostess-record-values-{command.replace('.', '-')}",
        "command": command,
        "params": params or {},
        "client_id": "hostessctl.record_values",
        "app_package": "rusty-hostess",
    }


def broker_ack_accepted(reply: dict[str, Any]) -> bool:
    if "accepted" in reply:
        return bool(reply.get("accepted"))
    return bool(reply.get("ok", reply.get("success", True)))


def connect_broker_websocket_with_retry(
    host: str,
    port: int,
    provider_actions: list[dict[str, Any]],
    errors: list[str],
) -> BrokerWebSocketClient:
    deadline = time.monotonic() + 15.0
    attempt = 0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        attempt += 1
        try:
            client = BrokerWebSocketClient(host, port, timeout=2.0)
            provider_actions.append(
                {
                    "action": "connect-broker-websocket",
                    "attempt": attempt,
                    "status": "pass",
                    "host": host,
                    "port": port,
                }
            )
            return client
        except OSError as ex:
            last_error = ex
            time.sleep(0.25)
        except RuntimeError as ex:
            last_error = ex
            time.sleep(0.25)
    message = f"broker websocket connection failed: {last_error}"
    errors.append(message)
    raise RuntimeError(message)


def configure_makepad_controller_pose_provider(
    args: argparse.Namespace,
    run_adb: Any,
    *,
    enable_breath_feedback: bool = False,
) -> None:
    setprops = with_legacy_rustyxr_property_aliases({
        **makepad_visual_profile_runtime_properties(),
        "debug.rusty.manifold.pose.publish.enabled": "true",
        "debug.rusty.manifold.pose.stream": "stream.motion.object_pose",
        "debug.rusty.manifold.pose.source": "provider.makepad.controller_pose",
        "debug.rusty.manifold.pose.controller": args.makepad_pose_controller,
        "debug.rusty.manifold.pose.kind": args.makepad_pose_kind,
        "debug.rusty.manifold.pose.sample.hz": str(args.makepad_pose_sample_hz),
        "debug.rusty.manifold.broker.host": "127.0.0.1",
        "debug.rusty.manifold.broker.port": str(args.broker_port),
        "debug.rusty.makepad.projection.target.joystick.controls": "offset-scale",
    })
    if enable_breath_feedback:
        setprops.update(
            with_legacy_rustyxr_property_aliases({
                "debug.rusty.manifold.breath.feedback.enabled": "true",
                "debug.rusty.manifold.breath.feedback.stream": "stream.breath.feedback_state",
                "debug.rusty.manifold.breath.feedback.receiver": "app.makepad_camera_shell.breath_feedback",
                "debug.rusty.manifold.breath.feedback.connect.timeout.ms": "5000",
            })
        )
    else:
        setprops.update(
            with_legacy_rustyxr_property_aliases({
                "debug.rusty.manifold.breath.feedback.enabled": "false"
            })
        )
    for key, value in setprops.items():
        run_adb(
            f"setprop-{key}",
            adb_prefix(args) + ["shell", "setprop", key, value],
            allow_failure=False,
        )
    run_adb(
        "force-stop-makepad-controller-pose-provider",
        adb_prefix(args) + ["shell", "am", "force-stop", args.makepad_provider_package],
        allow_failure=True,
    )
    run_adb(
        "launch-makepad-controller-pose-provider",
        adb_prefix(args) + ["shell", "am", "start", "-n", args.makepad_provider_activity],
        allow_failure=False,
    )


def configure_makepad_breath_feedback_receiver(args: argparse.Namespace) -> None:
    setprops = with_legacy_rustyxr_property_aliases({
        **makepad_visual_profile_runtime_properties(),
        "debug.rusty.manifold.pose.publish.enabled": "false",
        "debug.rusty.manifold.broker.host": "127.0.0.1",
        "debug.rusty.manifold.broker.port": str(args.broker_port),
        "debug.rusty.manifold.breath.feedback.enabled": "true",
        "debug.rusty.manifold.breath.feedback.stream": "stream.breath.feedback_state",
        "debug.rusty.manifold.breath.feedback.receiver": "app.makepad_camera_shell.breath_feedback",
        "debug.rusty.manifold.breath.feedback.connect.timeout.ms": "5000",
        "debug.rusty.makepad.projection.target.joystick.controls": "offset-scale",
    })
    for key, value in setprops.items():
        run([args.adb, "-s", args.serial, "shell", "setprop", key, value])
    for permission in [
        "android.permission.CAMERA",
        "horizonos.permission.HEADSET_CAMERA",
    ]:
        run(
            [args.adb, "-s", args.serial, "shell", "pm", "grant", args.makepad_package, permission],
            allow_failure=True,
        )
    run([args.adb, "-s", args.serial, "shell", "am", "force-stop", args.makepad_package], allow_failure=True)
    run([args.adb, "-s", args.serial, "shell", "am", "start", "-n", args.makepad_activity])
    time.sleep(max(0.0, float(args.makepad_settle_seconds)))


def configure_makepad_physical_pmb_provider(args: argparse.Namespace) -> None:
    setprops = with_legacy_rustyxr_property_aliases({
        **makepad_visual_profile_runtime_properties(),
        "debug.rusty.manifold.pose.publish.enabled": "true",
        "debug.rusty.manifold.pose.stream": "stream.motion.object_pose",
        "debug.rusty.manifold.pose.source": "provider.makepad.controller_pose",
        "debug.rusty.manifold.pose.controller": args.makepad_pose_controller,
        "debug.rusty.manifold.pose.kind": args.makepad_pose_kind,
        "debug.rusty.manifold.pose.sample.hz": str(args.makepad_pose_sample_hz),
        "debug.rusty.manifold.broker.host": "127.0.0.1",
        "debug.rusty.manifold.broker.port": str(args.broker_port),
        "debug.rusty.manifold.breath.feedback.enabled": "true",
        "debug.rusty.manifold.breath.feedback.stream": "stream.breath.feedback_state",
        "debug.rusty.manifold.breath.feedback.receiver": "app.makepad_camera_shell.breath_feedback",
        "debug.rusty.manifold.breath.feedback.connect.timeout.ms": "5000",
        "debug.rusty.makepad.projection.target.joystick.controls": "offset-scale",
    })
    for key, value in setprops.items():
        run([args.adb, "-s", args.serial, "shell", "setprop", key, value])
    for permission in [
        "android.permission.CAMERA",
        "horizonos.permission.HEADSET_CAMERA",
    ]:
        run(
            [args.adb, "-s", args.serial, "shell", "pm", "grant", args.makepad_package, permission],
            allow_failure=True,
        )
    run([args.adb, "-s", args.serial, "shell", "am", "force-stop", args.makepad_package], allow_failure=True)
    run([args.adb, "-s", args.serial, "shell", "am", "start", "-n", args.makepad_activity])
    time.sleep(max(0.0, float(args.makepad_settle_seconds)))


def grant_broker_runtime_permissions(args: argparse.Namespace) -> None:
    for permission in [
        "android.permission.BLUETOOTH_SCAN",
        "android.permission.BLUETOOTH_CONNECT",
    ]:
        run(
            [args.adb, "-s", args.serial, "shell", "pm", "grant", args.broker_package, permission],
            allow_failure=True,
        )


def wait_for_makepad_controller_pose_ready(
    args: argparse.Namespace,
    ws: BrokerWebSocketClient,
    provider_actions: list[dict[str, Any]],
    errors: list[str],
) -> None:
    timeout_seconds = float(getattr(args, "makepad_pose_ready_timeout_seconds", 20.0))
    deadline = time.monotonic() + max(timeout_seconds, 0.1)
    observed = 0
    active = 0
    tracked = 0
    connected = 0
    last_payload: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        message = ws.recv_json(timeout=0.25)
        if message is None:
            continue
        if message.get("type") != "stream_event":
            provider_actions.append(
                {
                    "action": "wait-makepad-controller-pose-ready-observed-broker-message",
                    "status": "observed",
                    "message_type": str(message.get("type") or message.get("command") or "broker-message"),
                    "request_id": message.get("request_id"),
                }
            )
            continue
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        stream = str(message.get("stream") or message.get("stream_id") or payload.get("stream_id") or payload.get("stream") or "")
        if stream != "stream.motion.object_pose":
            continue
        observed += 1
        last_payload = payload
        if payload.get("active") is True:
            active += 1
        if payload.get("tracked") is True:
            tracked += 1
        if payload.get("connected") is True:
            connected += 1
        if (
            payload.get("active") is True
            and payload.get("tracked") is True
            and payload.get("connected") is True
        ):
            provider_actions.append(
                {
                    "action": "wait-makepad-controller-pose-ready",
                    "status": "pass",
                    "timeout_seconds": timeout_seconds,
                    "observed_pose_events": observed,
                    "active_pose_events": active,
                    "tracked_pose_events": tracked,
                    "connected_pose_events": connected,
                    "controller": payload.get("controller"),
                    "pose_kind": payload.get("pose_kind"),
                    "quality01": payload.get("quality01"),
                    "stream": stream,
                }
            )
            return
    message = (
        "Makepad controller pose provider did not produce active/tracked/connected "
        f"stream.motion.object_pose within {timeout_seconds:.1f}s"
    )
    provider_actions.append(
        {
            "action": "wait-makepad-controller-pose-ready",
            "status": "fail",
            "timeout_seconds": timeout_seconds,
            "observed_pose_events": observed,
            "active_pose_events": active,
            "tracked_pose_events": tracked,
            "connected_pose_events": connected,
            "last_active": last_payload.get("active") if last_payload else None,
            "last_tracked": last_payload.get("tracked") if last_payload else None,
            "last_connected": last_payload.get("connected") if last_payload else None,
            "last_quality01": last_payload.get("quality01") if last_payload else None,
        }
    )
    errors.append(message)
    raise RuntimeError(message)


def run_pmb_live_processor_bridge(
    args: argparse.Namespace,
    events_jsonl: Path,
    capture_out: Path,
) -> dict[str, Any]:
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    route_report_path = capture_out.with_name(f"{capture_out.stem}.pmb-live-route-report.json")
    stdout_path = capture_out.with_name(f"{capture_out.stem}.pmb-live-route.stdout.txt")
    stderr_path = capture_out.with_name(f"{capture_out.stem}.pmb-live-route.stderr.txt")
    command = [
        args.cargo,
        "run",
        "--quiet",
        "-p",
        "projected-motion-breath-core",
        "--",
        "live-route-from-events",
        "--package-root",
        str(package_root),
        "--events-jsonl",
        str(events_jsonl),
    ]
    started_utc = datetime.now(UTC)
    if not package_root.exists():
        return {
            "requested": True,
            "enabled": True,
            "status": "fail",
            "error": f"projected-motion-breath package root not found: {package_root}",
            "artifacts": [],
        }
    core_run = run_captured(command, allow_failure=True, cwd=packages_root)
    ended_utc = datetime.now(UTC)
    stdout_path.write_text(core_run.stdout, encoding="utf-8")
    stderr_path.write_text(core_run.stderr, encoding="utf-8")
    route_report, parse_error = parse_pmb_core_report(core_run.stdout)
    if route_report is not None:
        route_report_path.write_text(
            json.dumps(route_report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    status = "pass" if core_run.returncode == 0 and route_report and route_report.get("status") == "pass" else "fail"
    return {
        "requested": True,
        "enabled": True,
        "status": status,
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "duration_ms": int((ended_utc - started_utc).total_seconds() * 1000),
        "command": redact_command(command),
        "core_returncode": core_run.returncode,
        "parse_error": parse_error,
        "route_report": route_report,
        "breath_sample_count": len(route_report.get("breath_samples", [])) if isinstance(route_report, dict) else 0,
        "feedback_sample_count": len(route_report.get("feedback_samples", [])) if isinstance(route_report, dict) else 0,
        "artifacts": [
            {
                "artifact_id": "artifact.pmb_live_processor_route_report",
                "path": str(route_report_path),
                "exists": route_report_path.exists(),
            },
            {
                "artifact_id": "artifact.pmb_live_processor_stdout",
                "path": str(stdout_path),
                "exists": stdout_path.exists(),
            },
            {
                "artifact_id": "artifact.pmb_live_processor_stderr",
                "path": str(stderr_path),
                "exists": stderr_path.exists(),
            },
        ],
    }


def publish_pmb_feedback_samples(
    args: argparse.Namespace,
    route_report: dict[str, Any],
    send_broker_command: Any,
) -> dict[str, Any]:
    limit = max(0, int(getattr(args, "pmb_feedback_publish_limit", 0)))
    breath_samples = select_pmb_output_samples(route_report.get("breath_samples", []), limit)
    feedback_samples = select_pmb_output_samples(route_report.get("feedback_samples", []), limit)
    breath_results = [
        publish_pmb_stream_sample(
            send_broker_command,
            stream_id="stream.breath.volume",
            sequence_id=int(sample.get("sequence_id") or index + 1),
            payload={
                "schema": "rusty.manifold.breath.volume.v1",
                "stream_id": "stream.breath.volume",
                "sequence_id": int(sample.get("sequence_id") or index + 1),
                "source_id": sample.get("source_id"),
                "input_stream_id": sample.get("input_stream_id"),
                "normalized_stream_id": sample.get("normalized_stream_id"),
                "sample_time_unix_ns": sample_time_unix_ns_from_sample(sample),
                "volume01": sample.get("volume01"),
                "phase": sample.get("phase"),
                "quality": sample.get("quality"),
                "tracking01": sample.get("tracking01"),
                "processor_id": "processor.projected_motion_breath.live_bridge",
                "publisher": "hostessctl.record_values",
            },
        )
        for index, sample in enumerate(breath_samples)
    ]
    feedback_results = [
        publish_pmb_stream_sample(
            send_broker_command,
            stream_id="stream.breath.feedback_state",
            sequence_id=int(sample.get("sequence_id") or index + 1),
            payload={
                "schema": "rusty.manifold.breath.feedback_state.v1",
                "stream_id": "stream.breath.feedback_state",
                "sequence_id": int(sample.get("sequence_id") or index + 1),
                "source_breath_sequence_id": sample.get("source_breath_sequence_id"),
                "source_id": sample.get("source_id"),
                "sample_time_unix_ns": sample.get("sample_time_unix_ns"),
                "volume01": sample.get("volume01"),
                "phase": sample.get("phase"),
                "quality": sample.get("quality"),
                "processor_id": "processor.projected_motion_breath.live_bridge",
                "publisher": "hostessctl.record_values",
            },
        )
        for index, sample in enumerate(feedback_samples)
    ]
    return {
        "limit": limit,
        "breath_requested_count": len(route_report.get("breath_samples", [])),
        "feedback_requested_count": len(route_report.get("feedback_samples", [])),
        "breath_published_count": sum(1 for result in breath_results if result.get("status") == "pass"),
        "feedback_published_count": sum(1 for result in feedback_results if result.get("status") == "pass"),
        "published_count": sum(1 for result in breath_results + feedback_results if result.get("status") == "pass"),
        "published": any(result.get("status") == "pass" for result in breath_results + feedback_results),
        "breath_results": breath_results,
        "feedback_results": feedback_results,
    }


def select_pmb_output_samples(raw_samples: Any, limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or not isinstance(raw_samples, list):
        return []
    by_source: dict[str, list[dict[str, Any]]] = {}
    source_order: list[str] = []
    for sample in raw_samples:
        if not isinstance(sample, dict):
            continue
        source_id = str(sample.get("source_id") or "source.unknown")
        if source_id not in by_source:
            by_source[source_id] = []
            source_order.append(source_id)
        by_source[source_id].append(sample)
    selected: list[dict[str, Any]] = []
    cursor = 0
    while len(selected) < limit and source_order:
        progressed = False
        for source_id in source_order:
            source_samples = by_source[source_id]
            if cursor < len(source_samples):
                selected.append(source_samples[cursor])
                progressed = True
                if len(selected) >= limit:
                    break
        if not progressed:
            break
        cursor += 1
    return selected


def publish_pmb_stream_sample(
    send_broker_command: Any,
    *,
    stream_id: str,
    sequence_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    ack = send_broker_command(
        "publish_stream_event",
        {
            "stream": stream_id,
            "sequence_id": sequence_id,
            "payload": payload,
        },
    )
    return {
        "stream_id": stream_id,
        "sequence_id": sequence_id,
        "status": ack.get("status"),
        "request_id": ack.get("request_id"),
    }


def sample_time_unix_ns_from_sample(sample: dict[str, Any]) -> int:
    value = sample.get("sample_time_unix_ns")
    if isinstance(value, (int, float)):
        return int(value)
    sample_time_s = sample.get("sample_time_s")
    if isinstance(sample_time_s, (int, float)):
        return int(max(0.0, float(sample_time_s)) * 1_000_000_000)
    return 0


def listen_for_pmb_receipts(
    args: argparse.Namespace,
    ws: BrokerWebSocketClient,
    stream_rows: dict[str, dict[str, Any]],
    events_jsonl: Path,
    broker_acks: list[dict[str, Any]],
) -> None:
    deadline = time.monotonic() + max(0.0, float(getattr(args, "pmb_receipt_listen_seconds", 0.0)))
    with events_jsonl.open("a", encoding="utf-8") as events_file:
        while time.monotonic() < deadline:
            remaining = max(0.05, min(0.25, deadline - time.monotonic()))
            message = ws.recv_json(timeout=remaining)
            if message is None:
                continue
            if message.get("type") == "stream_event":
                accept_broker_stream_event(message, stream_rows, events_jsonl, events_file=events_file)
            else:
                broker_acks.append(
                    {
                        "command": str(message.get("command") or message.get("type") or "broker-message"),
                        "request_id": message.get("request_id"),
                        "status": "observed",
                        "reply": message,
                    }
                )


def accept_broker_stream_event(
    event: dict[str, Any],
    stream_rows: dict[str, dict[str, Any]],
    events_jsonl: Path,
    *,
    events_file: Any | None = None,
) -> None:
    event = with_transport_event_aliases(event)
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    stream = str(event.get("stream") or event.get("stream_id") or payload.get("stream_id") or "")
    if stream not in stream_rows:
        return
    now = datetime.now(UTC).isoformat()
    row = stream_rows[stream]
    row["event_count"] = int(row["event_count"]) + 1
    row["sample_count"] = int(row["sample_count"]) + 1
    if row["first_event_at_utc"] is None:
        row["first_event_at_utc"] = now
    row["last_event_at_utc"] = now
    line = json.dumps(event, separators=(",", ":"), sort_keys=True)
    if events_file is not None:
        events_file.write(line + "\n")
    else:
        with events_jsonl.open("a", encoding="utf-8") as file:
            file.write(line + "\n")


def with_transport_event_aliases(event: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(event)
    payload = normalized.get("payload")
    if isinstance(payload, dict):
        payload = dict(payload)
        normalized["payload"] = payload
    else:
        payload = {}

    for old_key, new_key in (
        ("broker_time_unix_ns", "transport_time_unix_ns"),
        ("broker_receive_time_unix_ns", "transport_receive_time_unix_ns"),
    ):
        if new_key not in normalized and old_key in normalized:
            normalized[new_key] = normalized[old_key]
        if new_key not in payload and old_key in payload:
            payload[new_key] = payload[old_key]

    return normalized


def validate_broker_websocket_stream_recording_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    streams = [stream for stream in evidence.get("streams", []) if isinstance(stream, dict)]
    pmb_requested = evidence.get("pmb_live_processor_requested") is True
    checks = [
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.schema",
            evidence.get("$schema") == "rusty.hostess.broker_stream_recording.evidence.v1",
            "broker stream recording evidence schema is supported",
        ),
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.streams",
            bool(streams) and all(stream.get("status") == "pass" for stream in streams),
            "all requested broker streams produced at least one event",
        ),
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.transport",
            evidence.get("broker_websocket_recording") is True
            and evidence.get("transport", {}).get("kind") == "adb-forwarded-broker-websocket",
            "recording used the adb-forwarded broker websocket transport",
        ),
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.pmb_processor_bridge",
            not pmb_requested
            or (
                evidence.get("pmb_processor_executed") is True
                and evidence.get("pmb_breath_published") is True
                and evidence.get("pmb_feedback_published") is True
            ),
            "PMB live processor bridge ran and published breath output streams when requested",
        ),
        recording_scorecard_check(
            "hostess.check.broker_stream_recording.makepad_breath_feedback_receipt",
            not pmb_requested or int(evidence.get("pmb_feedback_receipt_count") or 0) > 0,
            "Makepad receipt stream acknowledged at least one PMB feedback sample when requested",
        ),
    ]
    errors = [check["evidence"] for check in checks if check["status"] != "pass"]
    return {
        "$schema": "rusty.hostess.broker_stream_recording.validation.v1",
        "status": "pass" if not errors and evidence.get("status") == "pass" else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors + list(evidence.get("errors", [])),
    }


def redact_command(command: list[str]) -> list[str]:
    redacted = list(command)
    for index, token in enumerate(redacted[:-1]):
        if token in {"--device-address"}:
            redacted[index + 1] = "<redacted>"
    return redacted


def build_manifold_value_recording_evidence(
    *,
    args: argparse.Namespace,
    requested_values: list[str],
    provider_plans: list[dict[str, Any]],
    route_status: str,
    route_reasons: list[str],
    host_profile: str,
    started_utc: datetime,
    ended_utc: datetime,
    capture_status: int | None,
    capture_evidence_path: Path | None,
    capture_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    recording_performed = capture_status is not None
    capture_passed = capture_status == 0 and capture_evidence is not None
    if route_status == "blocked":
        status = "blocked"
    elif recording_performed:
        status = "pass" if capture_passed else "fail"
    else:
        status = "ready"
    capture_artifacts = []
    if capture_evidence_path is not None:
        capture_artifacts.append(
            {
                "artifact_id": "artifact.manifold_value_recording.source_capture_evidence",
                "path": str(capture_evidence_path),
                "exists": capture_evidence_path.exists(),
            }
        )
        validation_path = capture_evidence_path.with_name(
            f"{capture_evidence_path.stem}.validation-report.json"
        )
        capture_artifacts.append(
            {
                "artifact_id": "artifact.manifold_value_recording.source_capture_validation",
                "path": str(validation_path),
                "exists": validation_path.exists(),
            }
        )
        if capture_evidence:
            pmb_bridge = capture_evidence.get("pmb_processor_bridge")
            if isinstance(pmb_bridge, dict):
                capture_artifacts.extend(
                    artifact
                    for artifact in pmb_bridge.get("artifacts", [])
                    if isinstance(artifact, dict)
                )
    captured_streams = []
    if capture_evidence:
        captured_streams = [
            {
                "stream_id": stream.get("stream_id"),
                "broker_stream_id": stream.get("broker_stream_id"),
                "status": stream.get("status"),
                "sample_count": stream.get("sample_count"),
                "event_count": stream.get("event_count"),
            }
            for stream in capture_evidence.get("streams", [])
            if isinstance(stream, dict)
        ]
    has_object_pose = any(
        plan.get("stream_id") == "stream.motion.object_pose"
        for plan in provider_plans
    )
    object_pose_captured = any(
        stream.get("stream_id") == "stream.motion.object_pose"
        and stream.get("status") == "pass"
        and int(stream.get("event_count") or stream.get("sample_count") or 0) > 0
        for stream in captured_streams
    )
    all_combined_supported = all(
        bool(plan.get("combined_recording_supported"))
        for plan in provider_plans
    )
    controller_input_used = bool(recording_performed and object_pose_captured)
    return {
        "$schema": "rusty.hostess.manifold_value_recording.evidence.v1",
        "status": status,
        "target": args.target,
        "host_profile": host_profile,
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "duration_ms": int((ended_utc - started_utc).total_seconds() * 1000),
        "requested_duration_ms": int(args.duration_seconds * 1000),
        "software": {
            "origin": "rusty-hostess",
            "host_app": host_app_for(host_profile),
            "host_app_version": "0.1.0",
        },
        "request": {
            "$schema": "rusty.hostess.manifold_value_recording.request.v1",
            "requested_value_ids": requested_values,
            "duration_seconds": args.duration_seconds,
            "target": args.target,
            "host_profile": host_profile,
            "mode": "live",
            "plan_only": bool(args.plan_only),
            "pmb_live_processor": bool(args.pmb_live_processor),
        },
        "recording": {
            "mode": "manifold_value_recording",
            "route_status": route_status,
            "recording_performed": recording_performed,
            "capture_returncode": capture_status,
            "plan_only": bool(args.plan_only),
            "general_recorder": True,
            "polar_specific": False,
            "controller_specific": False,
            "provider_bound": True,
            "live_sensor_used": recording_performed,
            "physical_controller_input_used": controller_input_used,
            "controller_input_used": controller_input_used,
            "simultaneous_multi_value_recording_supported": all_combined_supported,
            "manual_controller_trial_required": has_object_pose and not controller_input_used,
            "pmb_live_processor_requested": bool(args.pmb_live_processor),
            "pmb_processor_executed": bool(capture_evidence and capture_evidence.get("pmb_processor_executed")),
            "pmb_breath_published": bool(capture_evidence and capture_evidence.get("pmb_breath_published")),
            "pmb_breath_publish_count": int(capture_evidence.get("pmb_breath_publish_count") or 0) if capture_evidence else 0,
            "pmb_feedback_published": bool(capture_evidence and capture_evidence.get("pmb_feedback_published")),
            "pmb_feedback_publish_count": int(capture_evidence.get("pmb_feedback_publish_count") or 0) if capture_evidence else 0,
            "pmb_feedback_receipt_count": int(capture_evidence.get("pmb_feedback_receipt_count") or 0) if capture_evidence else 0,
            "makepad_breath_feedback_subscriber_configured": bool(
                capture_evidence and capture_evidence.get("makepad_breath_feedback_subscriber_configured")
            ),
            "makepad_breath_feedback_subscriber_flags_owner": (
                capture_evidence.get("makepad_breath_feedback_subscriber_flags_owner")
                if capture_evidence
                else None
            ),
        },
        "provider_plans": provider_plans,
        "blocked_reasons": route_reasons,
        "capture_artifacts": capture_artifacts,
        "captured_streams": captured_streams,
        "commands": [
            {
                "command": "record_manifold_values",
                "status": "acknowledged" if status in {"pass", "ready"} else status,
                "requested_value_ids": requested_values,
                "duration_seconds": args.duration_seconds,
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.manifold_value_recording",
            "target_id": "hostess.manifold_value_recording",
            "target_revision": 1,
            "status": "pass" if status in {"pass", "ready"} else status,
            "checks": [],
            "issues": [
                {
                    "code": "recording.manifold_value_recording.blocked",
                    "severity": "warning",
                    "message": reason,
                }
                for reason in route_reasons
            ],
        },
    }


def validate_manifold_value_recording_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    recording = evidence.get("recording", {})
    request = evidence.get("request", {})
    provider_plans = evidence.get("provider_plans", [])
    captured_streams = [
        stream
        for stream in evidence.get("captured_streams", [])
        if isinstance(stream, dict)
    ]
    status = evidence.get("status")
    has_object_pose = any(
        isinstance(plan, dict) and plan.get("stream_id") == "stream.motion.object_pose"
        for plan in provider_plans
    )
    object_pose_captured = any(
        stream.get("stream_id") == "stream.motion.object_pose"
        and stream.get("status") == "pass"
        and int(stream.get("event_count") or stream.get("sample_count") or 0) > 0
        for stream in captured_streams
    )
    recording_performed = recording.get("recording_performed") is True
    pmb_requested = recording.get("pmb_live_processor_requested") is True
    controller_claim_ok = (
        (
            not has_object_pose
            and recording.get("physical_controller_input_used") is False
            and recording.get("controller_input_used") is False
        )
        or (
            has_object_pose
            and not recording_performed
            and recording.get("physical_controller_input_used") is False
            and recording.get("controller_input_used") is False
        )
        or (
            has_object_pose
            and recording_performed
            and object_pose_captured
            and recording.get("physical_controller_input_used") is True
            and recording.get("controller_input_used") is True
        )
        or (
            has_object_pose
            and recording_performed
            and not object_pose_captured
            and recording.get("physical_controller_input_used") is False
            and recording.get("controller_input_used") is False
        )
    )
    requested_streams = [
        str(value)
        for value in request.get("requested_value_ids", [])
    ]
    captured_pass_streams = {
        str(stream.get("stream_id"))
        for stream in captured_streams
        if stream.get("status") == "pass"
    }
    checks = [
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.schema",
            evidence.get("$schema") == "rusty.hostess.manifold_value_recording.evidence.v1",
            "Manifold value recording evidence schema is supported",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.values",
            bool(request.get("requested_value_ids")) and isinstance(provider_plans, list),
            "recording request includes at least one Manifold value and provider plan",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.duration",
            int(evidence.get("requested_duration_ms", 0)) > 0,
            "recording request duration is positive",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.general_boundary",
            recording.get("general_recorder") is True
            and recording.get("polar_specific") is False
            and recording.get("controller_specific") is False,
            "recording route is general and not Polar- or controller-specific",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.controller_claim",
            controller_claim_ok,
            "controller input claim matches requested provider and execution state",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.status",
            status in {"pass", "ready", "blocked", "fail"},
            f"recording evidence status is {status}",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.pass_requires_capture",
            status != "pass" or recording.get("recording_performed") is True,
            "passing recording evidence includes an executed source capture",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.blocked_is_explicit",
            status != "blocked" or bool(evidence.get("blocked_reasons")),
            "blocked recording evidence lists explicit blocked reasons",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.pass_streams",
            status != "pass" or all(stream_id in captured_pass_streams for stream_id in requested_streams),
            "passing recording evidence includes every requested stream",
        ),
        recording_scorecard_check(
            "hostess.check.manifold_value_recording.pmb_live_processor_bridge",
            status != "pass"
            or not pmb_requested
            or (
                recording.get("pmb_processor_executed") is True
                and recording.get("pmb_breath_published") is True
                and recording.get("pmb_feedback_published") is True
                and int(recording.get("pmb_feedback_receipt_count") or 0) > 0
                and recording.get("makepad_breath_feedback_subscriber_configured") is True
            ),
            "passing PMB bridge recording ran the processor, published breath streams, and received Makepad feedback ack",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.manifold_value_recording.validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": status,
        "checks": checks,
        "errors": errors,
    }


def write_manifold_value_recording_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    provider_plans = [
        plan for plan in raw.get("provider_plans", [])
        if isinstance(plan, dict)
    ]
    package_ids = sorted(
        {
            str(plan["package_id"])
            for plan in provider_plans
            if plan.get("package_id")
        }
    )
    checks = [
        recording_scorecard_check(
            "validation.check.manifold_value_recording_validation",
            validation_report.get("status") == "pass",
            "Manifold value recording evidence validation passed",
        ),
        recording_scorecard_check(
            "validation.check.manifold_value_recording_boundary",
            raw.get("recording", {}).get("general_recorder") is True
            and raw.get("recording", {}).get("polar_specific") is False
            and raw.get("recording", {}).get("controller_specific") is False,
            "Host-run evidence records the generic recorder boundary",
        ),
    ]
    status = raw.get("status") if validation_report.get("status") == "pass" else "fail"
    requested_values = raw.get("request", {}).get("requested_value_ids", [])
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.manifold_value_recording.{recording_segment(requested_values)}.{started_ms}",
        "bundle_id": "host_run.bundle.manifold_value_recording",
        "validation_slot_id": "host_run.slot.manifold_value_recording",
        "host_profile": f"host.{raw.get('host_profile')}",
        "app_id": host_app_for(str(raw.get("host_profile"))),
        "package_ids": package_ids,
        "module_ids": ["module.hostess.manifold_value_recorder"],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.manifold_value_recording_evidence",
            "artifact.manifold_value_recording_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "requested_value_ids": requested_values,
            "requested_duration_ms": raw.get("requested_duration_ms"),
            "recording_performed": raw.get("recording", {}).get("recording_performed"),
            "route_status": raw.get("recording", {}).get("route_status"),
            "controller_input_used": raw.get("recording", {}).get("controller_input_used"),
            "physical_controller_input_used": raw.get("recording", {}).get("physical_controller_input_used"),
            "manual_controller_trial_required": raw.get("recording", {}).get("manual_controller_trial_required"),
            "pmb_live_processor_requested": raw.get("recording", {}).get("pmb_live_processor_requested"),
            "pmb_processor_executed": raw.get("recording", {}).get("pmb_processor_executed"),
            "pmb_breath_publish_count": raw.get("recording", {}).get("pmb_breath_publish_count"),
            "pmb_feedback_publish_count": raw.get("recording", {}).get("pmb_feedback_publish_count"),
            "pmb_feedback_receipt_count": raw.get("recording", {}).get("pmb_feedback_receipt_count"),
            "makepad_breath_feedback_subscriber_configured": raw.get("recording", {}).get("makepad_breath_feedback_subscriber_configured"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.manifold_value_recording",
            "target_id": f"host_run.run.manifold_value_recording.{recording_segment(requested_values)}.{started_ms}",
            "target_revision": 1,
            "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
            "checks": checks,
            "issues": raw.get("scorecard", {}).get("issues", []),
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def recording_scorecard_check(check_id: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
        "issue_codes": [] if passed else ["validation.manifold_value_recording_failed"],
    }


def recording_segment(value_ids: list[str]) -> str:
    if not value_ids:
        return "unknown"
    pieces = [value_id.split(".")[-1].replace("-", "_") for value_id in value_ids]
    return "_".join(pieces)[:80]


def render_telemetry(args: argparse.Namespace) -> int:
    if args.target == "desktop":
        return render_desktop_telemetry(args)
    if not args.adb or not args.serial:
        raise SystemExit("--adb and --serial are required for phone and quest render targets")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    name = sanitize_remote_name(args.name or out.name or "latest-render.png")
    if not name.endswith(".png"):
        name = f"{name}.png"
    remote = f"{ANDROID_REMOTE_RENDER_ROOT}/{name}"
    remote_sidecar = f"{remote}.json"
    run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)
    run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote_sidecar], allow_failure=True)
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "shell",
            "am",
            "start",
            "-a",
            ANDROID_RENDER_ACTION,
            "-n",
            f"{ANDROID_PACKAGE}/.MainActivity",
            "--es",
            "render_name",
            name,
            "--es",
            "render_page",
            args.page,
            "--es",
            "render_target",
            args.target,
            "--es",
            "render_source_evidence_path",
            args.source_evidence_path or "hostess-t/evidence/live-capture/latest.json",
        ]
    )
    wait_for_android_file(args, remote_sidecar, 10.0)
    run([args.adb, "-s", args.serial, "pull", remote, str(out)])
    sidecar = render_sidecar_path(out)
    run([args.adb, "-s", args.serial, "pull", remote_sidecar, str(sidecar)])
    validate_render_output(
        out,
        sidecar,
        expected_page=args.page,
        source_evidence_path=args.source_evidence_path or ANDROID_REMOTE_EVIDENCE,
        target=args.target,
    )
    return 0


def pull_makepad_render(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not args.no_launch:
        run(
            [
                args.adb,
                "-s",
                args.serial,
                "shell",
                "run-as",
                MAKEPAD_ANDROID_PACKAGE,
                "rm",
                "-f",
                MAKEPAD_RENDER_RELATIVE,
                MAKEPAD_RENDER_SIDECAR_RELATIVE,
            ],
            allow_failure=True,
        )
        run(
            [
                args.adb,
                "-s",
                args.serial,
                "shell",
                "am",
                "force-stop",
                MAKEPAD_ANDROID_PACKAGE,
            ],
            allow_failure=True,
        )
        run(
            [
                args.adb,
                "-s",
                args.serial,
                "shell",
                "am",
                "start",
                "-n",
                MAKEPAD_ANDROID_ACTIVITY,
            ]
        )
    wait_for_android_run_as_file(
        args,
        MAKEPAD_ANDROID_PACKAGE,
        MAKEPAD_RENDER_SIDECAR_RELATIVE,
        args.wait_seconds,
    )
    wait_for_makepad_render_sidecar(
        args,
        MAKEPAD_ANDROID_PACKAGE,
        MAKEPAD_RENDER_SIDECAR_RELATIVE,
        args.wait_seconds,
        target="headset" if args.target == "quest" else "mobile",
        min_events=args.min_events,
    )
    pull_android_run_as_file(args, MAKEPAD_ANDROID_PACKAGE, MAKEPAD_RENDER_RELATIVE, out)
    sidecar = render_sidecar_path(out)
    pull_android_run_as_file(
        args,
        MAKEPAD_ANDROID_PACKAGE,
        MAKEPAD_RENDER_SIDECAR_RELATIVE,
        sidecar,
    )
    validate_render_output(
        out,
        sidecar,
        expected_page="watcher",
        source_evidence_path="",
        target="headset" if args.target == "quest" else "mobile",
    )
    return 0


def launch_makepad_shell_contract(args: argparse.Namespace) -> int:
    return makepad_shell_contract_launcher.launch_makepad_shell_contract(
        args,
        adb_prefix=adb_prefix,
        host_app_for=host_app_for,
        run=run,
        wait_for_android_run_as_file=wait_for_android_run_as_file,
        pull_android_run_as_file=pull_android_run_as_file,
        write_android_run_as_file=write_android_run_as_file,
    )

def snapshot_telemetry(args: argparse.Namespace) -> int:
    evidence_path = Path(args.input)
    snapshot = build_snapshot(
        evidence_path,
        graph_report_path=Path(args.graph_report) if args.graph_report else None,
        runtime_input_path=Path(args.runtime_input) if args.runtime_input else None,
    )
    write_snapshot(snapshot, Path(args.out))
    return 0


def render_desktop_telemetry(args: argparse.Namespace) -> int:
    if not args.input:
        raise SystemExit("--input is required for desktop telemetry rendering")
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("desktop telemetry rendering requires Pillow") from exc

    evidence_path = Path(args.input)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    capture = evidence.get("capture", {})
    runtime_name = capture.get("runtime_input")
    graph_name = capture.get("graph_execution_report")
    runtime_path = evidence_path.with_name(runtime_name) if runtime_name else None
    graph_path = evidence_path.with_name(graph_name) if graph_name else None
    runtime_input = json.loads(runtime_path.read_text(encoding="utf-8")) if runtime_path and runtime_path.exists() else {}
    graph_report = json.loads(graph_path.read_text(encoding="utf-8")) if graph_path and graph_path.exists() else {}

    image = Image.new("RGB", (1080, 760), (248, 248, 246))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw_header(draw, font, evidence, graph_report, args.page)
    if args.page == "raw":
        draw_desktop_raw_page(draw, font, runtime_input, evidence)
    else:
        draw_desktop_module_page(draw, font, graph_report)
    image.save(out)
    sidecar = render_sidecar_path(out)
    write_render_sidecar(
        out,
        sidecar,
        page=args.page,
        target="desktop",
        source_evidence_path=str(evidence_path),
    )
    validate_render_output(
        out,
        sidecar,
        expected_page=args.page,
        source_evidence_path=str(evidence_path),
        target="desktop",
    )
    return 0


def render_sidecar_path(image_path: Path) -> Path:
    return Path(f"{image_path}.json")


def write_render_sidecar(
    image_path: Path,
    sidecar_path: Path,
    *,
    page: str,
    target: str,
    source_evidence_path: str,
) -> None:
    metrics = measure_render_image(image_path)
    sidecar = {
        "$schema": "rusty.hostess.telemetry.render_evidence.v1",
        "status": "pass",
        "rendered_at_utc": datetime.now(UTC).isoformat(),
        "target": target,
        "render_page": page,
        "image_path": str(image_path),
        "source_evidence_path": source_evidence_path,
        "width": metrics["width"],
        "height": metrics["height"],
        "content_pixel_count": metrics["content_pixel_count"],
        "validation": {
            "min_width": MIN_RENDER_WIDTH,
            "min_height": MIN_RENDER_HEIGHT,
            "min_content_pixels": MIN_RENDER_CONTENT_PIXELS,
        },
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True), encoding="utf-8")


def validate_render_output(
    image_path: Path,
    sidecar_path: Path,
    *,
    expected_page: str,
    source_evidence_path: str,
    target: str,
) -> None:
    if not image_path.exists():
        raise SystemExit(f"render output missing: {image_path}")
    if not sidecar_path.exists():
        raise SystemExit(f"render sidecar missing: {sidecar_path}")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    metrics = measure_render_image(image_path)
    errors: list[str] = []
    if sidecar.get("status") != "pass":
        errors.append(f"render sidecar status is {sidecar.get('status')}")
    if sidecar.get("target") != target:
        errors.append(f"render sidecar target is {sidecar.get('target')}, expected {target}")
    if sidecar.get("render_page") != expected_page:
        errors.append(f"render sidecar page is {sidecar.get('render_page')}, expected {expected_page}")
    sidecar_source = str(sidecar.get("source_evidence_path", ""))
    if (
        source_evidence_path
        and sidecar_source not in {source_evidence_path, str(source_evidence_path)}
        and not str(source_evidence_path).endswith(sidecar_source)
    ):
        errors.append("render sidecar source evidence path does not match request")
    for key in ["width", "height", "content_pixel_count"]:
        if int(sidecar.get(key, -1)) != int(metrics[key]):
            errors.append(f"render sidecar {key} does not match PNG")
    if metrics["width"] < MIN_RENDER_WIDTH or metrics["height"] < MIN_RENDER_HEIGHT:
        errors.append(
            f"render is too small: {metrics['width']}x{metrics['height']} "
            f"(minimum {MIN_RENDER_WIDTH}x{MIN_RENDER_HEIGHT})"
        )
    if metrics["content_pixel_count"] < MIN_RENDER_CONTENT_PIXELS:
        errors.append(f"render appears blank: {metrics['content_pixel_count']} content pixels")
    if errors:
        raise SystemExit("; ".join(errors))


def measure_render_image(image_path: Path) -> dict[str, int]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("telemetry render validation requires Pillow") from exc
    import warnings

    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            pixels = list(rgb.getdata())
    if not pixels:
        return {"width": width, "height": height, "content_pixel_count": 0}
    background = pixels[0]
    content_pixels = sum(1 for pixel in pixels if pixel != background)
    return {"width": width, "height": height, "content_pixel_count": content_pixels}


def draw_header(draw: Any, font: Any, evidence: dict[str, Any], graph_report: dict[str, Any], page: str) -> None:
    draw_panel(draw, 24, 18, 1032, 92)
    selected = evidence.get("capture", {}).get("selected_module_ids", [])
    status = evidence.get("status", "unknown")
    graph_status = graph_report.get("status", "waiting")
    draw.text((42, 36), "Rusty Hostess T", fill=(29, 29, 27), font=font)
    draw.text((42, 58), f"{status} / {evidence.get('host_profile', 'desktop')}", fill=(92, 88, 82), font=font)
    draw.text(
        (42, 80),
        f"{page} / {len(selected)} modules / graph {graph_status} / streams {len(evidence.get('streams', []))}",
        fill=(92, 88, 82),
        font=font,
    )


def draw_desktop_raw_page(draw: Any, font: Any, runtime_input: dict[str, Any], evidence: dict[str, Any]) -> None:
    rr_values = [float(value) for value in runtime_input.get("hr_rr", {}).get("rr_intervals_ms", []) if value is not None]
    acc_values: list[float] = []
    for frame in runtime_input.get("raw_acc", {}).get("frames", []):
        for sample in frame.get("samples_mg", frame.get("samples", [])):
            if isinstance(sample, dict):
                acc_values.append(float(sample.get("z_mg", 0.0)))
    draw_plot(draw, font, "RR", f"{len(rr_values)} intervals", rr_values, (15, 118, 110), 24, 132, 1032, 260)
    acc_rate = runtime_input.get("raw_acc", {}).get("sample_rate_hz", "n/a")
    draw_plot(draw, font, "ACC Z", f"{len(acc_values)} samples / {acc_rate} Hz", acc_values, (79, 76, 71), 24, 418, 1032, 260)
    draw.text((42, 706), f"evidence streams: {', '.join(stream.get('stream_id', '') for stream in evidence.get('streams', [])[:4])}", fill=(92, 88, 82), font=font)


def draw_desktop_module_page(draw: Any, font: Any, graph_report: dict[str, Any]) -> None:
    metrics = [
        ("HRV lnRMSSD", "stream.polar_h10.hrv_window", "ln_rmssd", 5.0, (37, 99, 235)),
        ("RMSSD gain", "stream.polar_h10.rmssd_gain", "ln_rmssd_gain", 2.0, (126, 34, 206)),
        ("Coherence", "stream.polar_h10.coherence", "normalized_score", 1.0, (15, 118, 110)),
        ("Breath vol", "stream.polar_h10.breath_volume", "breath_volume_01", 1.0, (185, 60, 20)),
        ("Breath rate", "stream.polar_h10.breath_dynamics", "breathing_rate_bpm", 30.0, (79, 76, 71)),
        ("HRVB amp", "stream.polar_h10.hrvb_resonance_amplitude", "amplitude_bpm", 10.0, (159, 18, 57)),
    ]
    for index, (label, stream_id, field, scale, color) in enumerate(metrics):
        col = index % 2
        row = index // 2
        left = 24 + col * 522
        top = 132 + row * 170
        stream = find_stream(graph_report, stream_id)
        value = float_value(stream.get(field)) if stream else 0.0
        status = stream.get("status", "missing") if stream else "missing"
        draw_metric_panel(draw, font, label, f"{value:.3f} / {status}", value / scale if scale else 0.0, color, left, top, 510, 142)


def draw_panel(draw: Any, left: int, top: int, width: int, height: int) -> None:
    draw.rounded_rectangle(
        (left, top, left + width, top + height),
        radius=8,
        fill=(255, 255, 255),
        outline=(214, 211, 205),
        width=1,
    )


def draw_plot(
    draw: Any,
    font: Any,
    label: str,
    count: str,
    values: list[float],
    color: tuple[int, int, int],
    left: int,
    top: int,
    width: int,
    height: int,
) -> None:
    draw_panel(draw, left, top, width, height)
    draw.text((left + 16, top + 16), label, fill=(29, 29, 27), font=font)
    draw.text((left + 16, top + 38), count, fill=(92, 88, 82), font=font)
    plot_left = left + 110
    plot_top = top + 24
    plot_width = width - 140
    plot_height = height - 54
    draw.line((plot_left, plot_top + plot_height // 2, plot_left + plot_width, plot_top + plot_height // 2), fill=(231, 229, 224), width=1)
    if not values:
        draw.text((plot_left + 8, plot_top + plot_height // 2), "waiting", fill=(92, 88, 82), font=font)
        return
    sampled = downsample(values, 800)
    low = min(sampled)
    high = max(sampled)
    if abs(high - low) < 0.0001:
        high += 1.0
        low -= 1.0
    points = []
    for index, value in enumerate(sampled):
        x = plot_left + (index * plot_width / max(len(sampled) - 1, 1))
        y = plot_top + plot_height - ((value - low) / (high - low) * plot_height)
        points.append((x, y))
    if len(points) == 1:
        x, y = points[0]
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
    else:
        draw.line(points, fill=color, width=2)


def draw_metric_panel(
    draw: Any,
    font: Any,
    label: str,
    value: str,
    fraction: float,
    color: tuple[int, int, int],
    left: int,
    top: int,
    width: int,
    height: int,
) -> None:
    draw_panel(draw, left, top, width, height)
    draw.text((left + 16, top + 18), label, fill=(29, 29, 27), font=font)
    draw.text((left + 16, top + 42), value, fill=(92, 88, 82), font=font)
    bar_left = left + 16
    bar_top = top + 88
    bar_width = width - 32
    draw.rounded_rectangle((bar_left, bar_top, bar_left + bar_width, bar_top + 18), radius=4, fill=(231, 229, 224))
    filled = max(0.0, min(1.0, fraction)) * bar_width
    draw.rounded_rectangle((bar_left, bar_top, bar_left + filled, bar_top + 18), radius=4, fill=color)


def downsample(values: list[float], max_points: int) -> list[float]:
    if len(values) <= max_points:
        return values
    step = len(values) / max_points
    return [values[int(index * step)] for index in range(max_points)]


def find_stream(graph_report: dict[str, Any], stream_id: str) -> dict[str, Any] | None:
    for stream in graph_report.get("streams", []):
        if stream.get("stream_id") == stream_id:
            return stream
    return None


def float_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def sanitize_remote_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "._-" else "_" for character in value)


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def append_rmssd_baseline_extras(command: list[str], args: argparse.Namespace) -> None:
    for source_arg, extra_name in [
        ("rmssd_baseline_ln_rmssd", "rmssd_baseline_ln_rmssd"),
        ("rmssd_baseline_mean_ln_rmssd", "rmssd_baseline_mean_ln_rmssd"),
        ("rmssd_baseline_sd_ln_rmssd", "rmssd_baseline_sd_ln_rmssd"),
        ("rmssd_baseline_window_count", "rmssd_baseline_window_count"),
    ]:
        value = getattr(args, source_arg, None)
        if value is not None:
            command.extend(["--es", extra_name, str(value)])
    if getattr(args, "rmssd_baseline_source", None):
        command.extend(["--es", "rmssd_baseline_source", args.rmssd_baseline_source])


def clear_android_live_artifacts(args: argparse.Namespace) -> None:
    for remote in [ANDROID_REMOTE_EVIDENCE, ANDROID_REMOTE_RUNTIME_INPUT, ANDROID_REMOTE_GRAPH_REPORT]:
        run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)


def clear_android_pmb_artifacts(args: argparse.Namespace) -> None:
    for remote in [ANDROID_REMOTE_PMB_EVIDENCE, ANDROID_REMOTE_PMB_CORE_REPORT]:
        run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)


def clear_android_pmb_controller_preflight_artifacts(args: argparse.Namespace) -> None:
    for remote in [
        ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE,
        ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_REPORT,
    ]:
        run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)


def clear_android_pmb_simulated_live_artifacts(args: argparse.Namespace) -> None:
    for remote in [
        ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE,
        ANDROID_REMOTE_PMB_SIMULATED_LIVE_ROUTE_REPORT,
        ANDROID_REMOTE_PMB_SIMULATED_LIVE_BROKER_REPORT,
    ]:
        run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)


def clear_android_pmb_physical_live_artifacts(args: argparse.Namespace) -> None:
    for remote in [
        ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE,
        ANDROID_REMOTE_PMB_PHYSICAL_LIVE_CAPTURE_REPORT,
        ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVENTS_JSONL,
        ANDROID_REMOTE_PMB_PHYSICAL_LIVE_ROUTE_REPORT,
        ANDROID_REMOTE_PMB_PHYSICAL_LIVE_BROKER_REPORT,
    ]:
        run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)


def clear_android_broker_telemetry_artifacts(args: argparse.Namespace) -> None:
    for remote in [
        ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE,
        ANDROID_REMOTE_BROKER_TELEMETRY_REPORT,
    ]:
        run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)


def wait_for_android_evidence(args: argparse.Namespace, timeout_seconds: float) -> None:
    wait_for_android_file(args, ANDROID_REMOTE_EVIDENCE, timeout_seconds)


def wait_for_android_file(args: argparse.Namespace, remote_path: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + max(timeout_seconds, 1.0)
    while time.monotonic() < deadline:
        result = run(
            [args.adb, "-s", args.serial, "shell", "test", "-f", remote_path],
            allow_failure=True,
        )
        if result.returncode == 0:
            return
        time.sleep(1.0)
    raise SystemExit(f"timed out waiting for Android file: {remote_path}")


def wait_for_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + max(timeout_seconds, 1.0)
    while time.monotonic() < deadline:
        result = run(
            [
                args.adb,
                "-s",
                args.serial,
                "shell",
                "run-as",
                package,
                "test",
                "-f",
                relative_path,
            ],
            allow_failure=True,
        )
        if result.returncode == 0:
            return
        time.sleep(1.0)
    raise SystemExit(f"timed out waiting for app file: {package}:{relative_path}")


def pull_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    out: Path,
) -> None:
    out.write_bytes(read_android_run_as_file(args, package, relative_path))


def write_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    payload: bytes,
) -> None:
    result = subprocess.run(
        [
            args.adb,
            "-s",
            args.serial,
            "exec-in",
            "run-as",
            package,
            "sh",
            "-c",
            f"cat > {android_shell_quote(relative_path)}",
        ],
        check=False,
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"could not write app file {package}:{relative_path}: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )


def android_shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def read_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
) -> bytes:
    result = subprocess.run(
        [
            args.adb,
            "-s",
            args.serial,
            "exec-out",
            "run-as",
            package,
            "cat",
            relative_path,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"could not pull app file {package}:{relative_path}: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout


def wait_for_makepad_render_sidecar(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    timeout_seconds: float,
    *,
    target: str,
    min_events: int,
) -> None:
    deadline = time.monotonic() + max(timeout_seconds, 1.0)
    last_reason = "sidecar not readable"
    while time.monotonic() < deadline:
        try:
            payload = read_android_run_as_file(args, package, relative_path)
            sidecar = json.loads(payload.decode("utf-8"))
        except (SystemExit, UnicodeDecodeError, json.JSONDecodeError) as exc:
            last_reason = str(exc)
            time.sleep(1.0)
            continue

        event_count = int(sidecar.get("event_count") or 0)
        if (
            sidecar.get("status") == "pass"
            and sidecar.get("render_page") == "watcher"
            and sidecar.get("target") == target
            and event_count >= min_events
        ):
            return
        last_reason = (
            f"status={sidecar.get('status')} page={sidecar.get('render_page')} "
            f"target={sidecar.get('target')} events={event_count}"
        )
        time.sleep(1.0)
    raise SystemExit(
        f"timed out waiting for Makepad render sidecar: "
        f"{package}:{relative_path} ({last_reason})"
    )


def pull_android_runtime_artifacts(args: argparse.Namespace, out: Path) -> None:
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "pull",
            ANDROID_REMOTE_RUNTIME_INPUT,
            str(out.with_name(f"{out.stem}.runtime-input.json")),
        ],
        allow_failure=True,
    )
    run(
        [
            args.adb,
            "-s",
            args.serial,
            "pull",
            ANDROID_REMOTE_GRAPH_REPORT,
            str(out.with_name(f"{out.stem}.graph-execution-report.json")),
        ],
        allow_failure=True,
    )


def validate_evidence(args: argparse.Namespace, out: Path, host_profile: str) -> int:
    report_out = out.with_name(f"{out.stem}.validation-report.json")
    command = [
        sys.executable,
        str(REPO_ROOT / "tools" / "check_live_capture_evidence.py"),
        "--input",
        str(out),
        "--packages-root",
        args.packages_root,
        "--expect-host",
        host_profile,
    ]
    if getattr(args, "stream", None):
        command.extend(["--expect-stream", args.stream])
    for module_id in args.module:
        command.extend(["--expect-module", module_id])
    command.extend(["--report-out", str(report_out)])
    result = run(command, allow_failure=True)
    if result.returncode == 0:
        write_contract_evidence(out, report_out, host_profile)
    return result.returncode


def graph_report_streams(graph_report: dict[str, Any]) -> list[dict[str, Any]]:
    streams: list[dict[str, Any]] = []
    for raw_stream in graph_report.get("streams", []):
        if not isinstance(raw_stream, dict):
            continue
        stream = dict(raw_stream)
        stream.setdefault("malformed_frame_count", 0)
        streams.append(stream)
    return streams


def polar_package_root(packages_root: Path) -> Path:
    package_root = packages_root / "packages" / "polar-h10"
    return package_root if package_root.exists() else packages_root


def projected_motion_breath_package_root(packages_root: Path) -> Path:
    package_root = packages_root / "packages" / "projected-motion-breath"
    return package_root if package_root.exists() else packages_root


def default_pmb_shell_handoff_path(package_root: Path) -> Path:
    return package_root / "fixtures" / "valid" / "shell-handoff-loopback.json"


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON file did not contain an object: {path}")
    return value


def load_json_manifest_dir(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    return [
        load_json_object(path)
        for path in sorted(directory.glob("*.json"))
    ]


def collect_manifest_ids(manifests: list[dict[str, Any]], key: str) -> list[str]:
    return sorted(
        str(manifest[key])
        for manifest in manifests
        if manifest.get(key)
    )


def parse_pmb_core_report(stdout: str) -> tuple[dict[str, Any] | None, str | None]:
    for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
        try:
            report = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(report, dict):
            return report, None
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as error:
        return None, str(error)
    if not isinstance(report, dict):
        return None, "core stdout did not contain a JSON object"
    return report, None


def build_pmb_desktop_replay_execution_evidence(
    *,
    packages_root: Path,
    package_root: Path,
    command: list[str],
    core_run: subprocess.CompletedProcess[str],
    core_report: dict[str, Any] | None,
    core_report_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    started_utc: datetime,
    ended_utc: datetime,
    parse_error: str | None,
) -> dict[str, Any]:
    checked_counts = pmb_checked_counts(core_report)
    core_status = core_report.get("status") if core_report else "missing"
    status = "pass" if core_run.returncode == 0 and core_status == "pass" and parse_error is None else "fail"
    package = projected_motion_package_snapshot(package_root)
    issues = []
    if parse_error:
        issues.append(
            {
                "code": "hostess.issue.pmb_core_report_parse_failed",
                "severity": "error",
                "message": parse_error,
            }
        )
    if core_report:
        for issue in core_report.get("issues", []):
            if isinstance(issue, dict):
                issues.append(issue)
            else:
                issues.append(
                    {
                        "code": "hostess.issue.pmb_core_report_issue",
                        "severity": "error",
                        "message": str(issue),
                    }
                )
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_core_process_exit",
            core_run.returncode == 0,
            f"projected-motion-breath-core exited with {core_run.returncode}",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_core_report_parse",
            core_report is not None and parse_error is None,
            "projected-motion-breath-core emitted a parseable validation report",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_core_report_status",
            core_status == "pass",
            f"projected-motion-breath core report status was {core_status}",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_core_goldens_executed",
            checked_counts.get("checked_cases", 0) >= 2
            and checked_counts.get("checked_damaged_cases", 0) >= 2,
            "projected-motion breath pose/vector golden and damaged cases executed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_core_adapter_normalization_executed",
            checked_counts.get("checked_adapter_normalization_cases", 0) >= 3
            and checked_counts.get("checked_damaged_adapter_normalization_cases", 0) >= 2,
            "projected-motion breath adapter-normalization valid and damaged cases executed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_no_platform_execution",
            True,
            "desktop replay used no Android, Quest, APK, OpenXR, ADB, or live sensor path",
        ),
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.desktop_replay_execution_evidence.v1",
        "status": status,
        "target": "desktop",
        "host_profile": "desktop",
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "duration_ms": int((ended_utc - started_utc).total_seconds() * 1000),
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.desktop",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "package_root_name": package_root.name,
        "packages_workspace_name": packages_root.name,
        "execution": {
            "mode": "projected_motion_breath_desktop_replay",
            "command": command,
            "returncode": core_run.returncode,
            "runtime_path": "rust.projected_motion_breath_core.v1",
            "core_report_artifact": core_report_path.name if core_report is not None else None,
            "stdout_artifact": stdout_path.name,
            "stderr_artifact": stderr_path.name,
            "processor_core_executed": True,
            "execution_performed": True,
            "runtime_execution_performed": True,
            "desktop_execution_performed": True,
            "platform_execution_performed": False,
            "device_required": False,
            "android_execution_performed": False,
            "quest_execution_performed": False,
            "apk_build_performed": False,
            "openxr_runtime_used": False,
            "adb_used": False,
            "live_sensor_used": False,
        },
        "core_report_summary": {
            "schema": core_report.get("schema") if core_report else None,
            "status": core_status,
            **checked_counts,
        },
        "commands": [
            {
                "command": "run_projected_motion_breath_core_validate_goldens",
                "status": "acknowledged" if core_run.returncode == 0 else "rejected",
                "runtime_path": "rust.projected_motion_breath_core.v1",
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.desktop_replay",
            "target_id": "hostess.projected_motion_breath.desktop_replay",
            "target_revision": 1,
            "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
            "checks": checks,
            "issues": issues,
        },
    }


def validate_pmb_desktop_replay_execution_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    core_summary = evidence.get("core_report_summary", {})
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.desktop_replay_execution_evidence.v1",
            "PMB desktop replay evidence schema is supported",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.status",
            evidence.get("status") == "pass",
            "PMB desktop replay evidence status passed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.target",
            evidence.get("target") == "desktop" and evidence.get("host_profile") == "desktop",
            "PMB desktop replay targeted the desktop host profile",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.runtime_executed",
            execution.get("execution_performed") is True
            and execution.get("runtime_execution_performed") is True
            and execution.get("processor_core_executed") is True,
            "PMB processor core execution was performed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.no_platform_execution",
            execution.get("platform_execution_performed") is False
            and execution.get("device_required") is False
            and execution.get("android_execution_performed") is False
            and execution.get("quest_execution_performed") is False
            and execution.get("apk_build_performed") is False
            and execution.get("openxr_runtime_used") is False
            and execution.get("adb_used") is False
            and execution.get("live_sensor_used") is False,
            "PMB desktop replay avoided Android, Quest, APK, OpenXR, ADB, and live sensors",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_desktop_replay.core_counts",
            core_summary.get("checked_cases", 0) >= 2
            and core_summary.get("checked_damaged_cases", 0) >= 2
            and core_summary.get("checked_adapter_normalization_cases", 0) >= 3
            and core_summary.get("checked_damaged_adapter_normalization_cases", 0) >= 2,
            "PMB core replay executed golden and adapter-normalization fixture sets",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.desktop_replay_execution_validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def build_pmb_live_route_self_test_evidence(
    *,
    packages_root: Path,
    package_root: Path,
    command: list[str],
    core_run: subprocess.CompletedProcess[str],
    route_report: dict[str, Any] | None,
    route_report_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    started_utc: datetime,
    ended_utc: datetime,
    parse_error: str | None,
) -> dict[str, Any]:
    route_status = route_report.get("status") if route_report else "missing"
    status = "pass" if core_run.returncode == 0 and route_status == "pass" and parse_error is None else "fail"
    package = projected_motion_package_snapshot(package_root)
    issues = []
    if parse_error:
        issues.append(
            {
                "code": "hostess.issue.pmb_live_route_report_parse_failed",
                "severity": "error",
                "message": parse_error,
            }
        )
    if route_report:
        for issue in route_report.get("issues", []):
            issues.append(
                {
                    "code": "hostess.issue.pmb_live_route_report_issue",
                    "severity": "error",
                    "message": str(issue),
                }
            )
    input_stream_ids = route_report.get("input_stream_ids", []) if route_report else []
    normalized_stream_ids = route_report.get("normalized_stream_ids", []) if route_report else []
    output_stream_ids = route_report.get("output_stream_ids", []) if route_report else []
    source_routes = route_report.get("source_routes", []) if route_report else []
    feedback_samples = route_report.get("feedback_samples", []) if route_report else []
    receipts = (
        route_report.get("receiver_receipts")
        or route_report.get("makepad_receipts")
        or []
        if route_report
        else []
    )
    subscription = (
        route_report.get("receiver_subscription")
        or route_report.get("makepad_subscription")
        or {}
        if route_report
        else {}
    )
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_live_route_core_exit",
            core_run.returncode == 0,
            f"projected-motion-breath-core exited with {core_run.returncode}",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_report_parse",
            route_report is not None and parse_error is None,
            "projected-motion-breath-core emitted a parseable live broker route report",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_report_status",
            route_status == "pass",
            f"live broker route report status was {route_status}",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_inputs",
            {"bio:polar_acc", "stream.motion.object_pose"}.issubset(set(input_stream_ids))
            and {"stream.motion.vector3", "stream.motion.object_pose"}.issubset(set(normalized_stream_ids)),
            "self-test route consumes Polar ACC plus Makepad controller pose and normalizes them",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_outputs",
            {"stream.breath.volume", "stream.breath.feedback_state"}.issubset(set(output_stream_ids)),
            "self-test route emits breath volume and breath feedback state",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_makepad_subscription",
            subscription.get("command") == "subscribe"
            and subscription.get("stream") == "stream.breath.feedback_state",
            "Makepad subscription contract targets stream.breath.feedback_state",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_makepad_receipts",
            bool(receipts)
            and all(
                receipt.get("command") == "breath_feedback.received"
                and receipt.get("schema") == "rusty.manifold.breath.feedback_receipt.v1"
                and receipt.get("received_stream") == "stream.breath.feedback_state"
                and receipt.get("acknowledged") is True
                for receipt in receipts
                if isinstance(receipt, dict)
            ),
            "Makepad receipt contract acknowledges every feedback sample",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_non_live",
            bool(route_report)
            and route_report.get("plan_only") is True
            and route_report.get("broker_transport_used", route_report.get("external_transport_used")) is False
            and route_report.get("live_sensor_used") is False
            and route_report.get("quest_execution_performed", route_report.get("headset_execution_performed")) is False,
            "self-test avoided broker transport, live sensors, and headset execution",
            "validation.pmb_live_route_self_test_failed",
        ),
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.live_broker_route_self_test_evidence.v1",
        "status": status,
        "target": "desktop",
        "host_profile": "desktop",
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "duration_ms": int((ended_utc - started_utc).total_seconds() * 1000),
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.desktop",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "package_root_name": package_root.name,
        "packages_workspace_name": packages_root.name,
        "execution": {
            "mode": "projected_motion_breath_live_broker_route_self_test",
            "command": command,
            "returncode": core_run.returncode,
            "runtime_path": "rust.projected_motion_breath_core.v1",
            "route_report_artifact": route_report_path.name if route_report is not None else None,
            "stdout_artifact": stdout_path.name,
            "stderr_artifact": stderr_path.name,
            "processor_core_executed": bool(route_report and route_report.get("processor_core_executed") is True),
            "execution_performed": True,
            "runtime_execution_performed": bool(route_report and route_report.get("runtime_execution_performed") is True),
            "desktop_execution_performed": True,
            "platform_execution_performed": False,
            "device_required": False,
            "android_execution_performed": False,
            "quest_execution_performed": False,
            "apk_build_performed": False,
            "openxr_runtime_used": False,
            "adb_used": False,
            "broker_transport_used": bool(
                route_report
                and (
                    route_report.get("broker_transport_used") is True
                    or route_report.get("external_transport_used") is True
                )
            ),
            "live_sensor_used": bool(route_report and route_report.get("live_sensor_used") is True),
            "plan_only": bool(route_report and route_report.get("plan_only") is True),
        },
        "route_report_summary": {
            "schema": route_report.get("schema") if route_report else None,
            "status": route_status,
            "route_id": route_report.get("route_id") if route_report else None,
            "input_stream_ids": input_stream_ids,
            "normalized_stream_ids": normalized_stream_ids,
            "output_stream_ids": output_stream_ids,
            "source_route_count": len(source_routes),
            "breath_sample_count": len(route_report.get("breath_samples", [])) if route_report else 0,
            "feedback_sample_count": len(feedback_samples),
            "receipt_count": len(receipts),
            "makepad_subscription": subscription,
        },
        "commands": [
            {
                "command": "run_projected_motion_breath_live_broker_route_self_test",
                "status": "acknowledged" if core_run.returncode == 0 else "rejected",
                "runtime_path": "rust.projected_motion_breath_core.v1",
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.live_broker_route_self_test",
            "target_id": "hostess.projected_motion_breath.live_broker_route_self_test",
            "target_revision": 1,
            "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
            "checks": checks,
            "issues": issues,
        },
    }


def validate_pmb_live_route_self_test_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    summary = evidence.get("route_report_summary", {})
    subscription = summary.get("makepad_subscription", {})
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.live_broker_route_self_test_evidence.v1",
            "PMB live broker route self-test evidence schema is supported",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.status",
            evidence.get("status") == "pass",
            "PMB live broker route self-test evidence status passed",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.runtime_executed",
            execution.get("execution_performed") is True
            and execution.get("runtime_execution_performed") is True
            and execution.get("processor_core_executed") is True,
            "PMB processor core execution was performed",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.non_live",
            execution.get("plan_only") is True
            and execution.get("platform_execution_performed") is False
            and execution.get("device_required") is False
            and execution.get("android_execution_performed") is False
            and execution.get("quest_execution_performed") is False
            and execution.get("apk_build_performed") is False
            and execution.get("openxr_runtime_used") is False
            and execution.get("adb_used") is False
            and execution.get("broker_transport_used") is False
            and execution.get("live_sensor_used") is False,
            "PMB live broker route self-test avoided devices and live transports",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.stream_contract",
            {"bio:polar_acc", "stream.motion.object_pose"}.issubset(
                set(summary.get("input_stream_ids", []))
            )
            and {"stream.breath.volume", "stream.breath.feedback_state"}.issubset(
                set(summary.get("output_stream_ids", []))
            )
            and int(summary.get("source_route_count", 0)) >= 2,
            "PMB live route stream contract includes the required inputs and outputs",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.feedback_ack",
            subscription.get("stream") == "stream.breath.feedback_state"
            and int(summary.get("feedback_sample_count", 0)) > 0
            and int(summary.get("receipt_count", 0)) == int(summary.get("feedback_sample_count", -1)),
            "PMB live route has a Makepad feedback subscription and one receipt per feedback sample",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_live_route.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB live route self-test scorecard passed",
            "validation.pmb_live_route_self_test_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.live_broker_route_self_test_validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def build_pmb_shell_handoff_validation_evidence(
    *,
    packages_root: Path,
    package_root: Path,
    handoff_path: Path,
    started_utc: datetime,
    ended_utc: datetime,
) -> dict[str, Any]:
    package_manifest = load_json_object(package_root / "manifests" / "package.manifold.json")
    stream_manifests = load_json_manifest_dir(package_root / "manifests" / "streams")
    command_manifests = load_json_manifest_dir(package_root / "manifests" / "commands")
    module_manifests = load_json_manifest_dir(package_root / "manifests" / "modules")
    handoff = load_json_object(handoff_path)
    exports = package_manifest.get("exports", {}) if isinstance(package_manifest.get("exports"), dict) else {}
    exported_stream_ids = sorted(str(value) for value in exports.get("streams", []) if value)
    exported_command_ids = sorted(str(value) for value in exports.get("commands", []) if value)
    exported_module_ids = sorted(str(value) for value in exports.get("modules", []) if value)
    manifest_stream_ids = collect_manifest_ids(stream_manifests, "stream_id")
    manifest_command_ids = collect_manifest_ids(command_manifests, "command_id")
    manifest_module_ids = collect_manifest_ids(module_manifests, "module_id")
    feedback_sink = next(
        (
            manifest
            for manifest in module_manifests
            if manifest.get("module_id") == "module.breath.feedback_sink"
        ),
        {},
    )
    stream_bindings = [
        binding
        for binding in handoff.get("stream_bindings", [])
        if isinstance(binding, dict)
    ]
    binding_pairs = sorted(
        {
            (str(binding.get("stream_id")), str(binding.get("direction")))
            for binding in stream_bindings
            if binding.get("stream_id") and binding.get("direction")
        }
    )
    bound_stream_ids = sorted({stream_id for stream_id, _direction in binding_pairs})
    command_ids = sorted(str(command_id) for command_id in handoff.get("command_ids", []) if command_id)
    transport_offers = [
        offer
        for offer in handoff.get("transport_offers", [])
        if isinstance(offer, dict)
    ]
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.schema",
            handoff.get("$schema") == "rusty.manifold.shell.handoff.v1",
            "shell handoff manifest uses the Manifold shell handoff schema",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.required_bindings",
            PMB_SHELL_HANDOFF_REQUIRED_BINDINGS.issubset(set(binding_pairs)),
            "shell handoff binds controller pose input, breath feedback subscription, and feedback receipt publication",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.stream_manifest_ids",
            set(bound_stream_ids).issubset(set(manifest_stream_ids)),
            "all shell handoff stream bindings are declared by PMB stream manifests",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.command_manifest_ids",
            bool(command_ids) and set(command_ids).issubset(set(manifest_command_ids)),
            "all shell handoff commands are declared by PMB command manifests",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.feedback_receipt_export",
            "stream.breath.feedback_receipt" in exported_stream_ids,
            "PMB package exports stream.breath.feedback_receipt for downstream shell acknowledgements",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.feedback_sink_provider",
            "stream.breath.feedback_receipt" in feedback_sink.get("provides_streams", []),
            "PMB feedback sink module provides stream.breath.feedback_receipt",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.transport_offer",
            bool(transport_offers)
            and all(
                offer.get("transport_id")
                and offer.get("transport")
                and offer.get("endpoint_id")
                for offer in transport_offers
            ),
            "shell handoff exposes named transport offers without requiring a live transport",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff.clean_boundary",
            True,
            "validation used package manifests and handoff fixture only, with no legacy app, device, or runtime shell dependency",
            "validation.pmb_shell_handoff_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    issues = [
        {
            "code": check["issue_codes"][0],
            "severity": "error",
            "message": check["evidence"],
            "related_id": check["check_id"],
        }
        for check in checks
        if check["status"] != "pass" and check.get("issue_codes")
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.shell_handoff_validation_evidence.v1",
        "status": status,
        "target": "desktop",
        "host_profile": "desktop",
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "duration_ms": int((ended_utc - started_utc).total_seconds() * 1000),
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.desktop",
            "host_app_version": "0.1.0",
        },
        "package": projected_motion_package_snapshot(package_root),
        "package_root_name": package_root.name,
        "packages_workspace_name": packages_root.name,
        "execution": {
            "mode": "projected_motion_breath_shell_handoff_validation",
            "handoff_validation_performed": True,
            "execution_performed": True,
            "runtime_execution_performed": False,
            "processor_core_executed": False,
            "desktop_execution_performed": True,
            "platform_execution_performed": False,
            "device_required": False,
            "android_execution_performed": False,
            "quest_execution_performed": False,
            "apk_build_performed": False,
            "openxr_runtime_used": False,
            "adb_used": False,
            "external_transport_used": False,
            "broker_transport_used": False,
            "live_sensor_used": False,
            "downstream_shell_runtime_used": False,
            "legacy_app_dependency_used": False,
            "legacy_rusty_xr_repo_used": False,
        },
        "shell_handoff": {
            "handoff_artifact": handoff_path.name,
            "handoff_id": handoff.get("handoff_id"),
            "handoff_revision": handoff.get("handoff_revision"),
            "target_host_profile": handoff.get("target_host_profile"),
            "shell_app_id": handoff.get("shell_app_id"),
            "validation_slot_id": handoff.get("validation_slot_id"),
            "expected_scorecard_id": handoff.get("expected_scorecard_id"),
            "stream_bindings": [
                {
                    "stream_id": binding.get("stream_id"),
                    "direction": binding.get("direction"),
                    "role": binding.get("role"),
                    "required": binding.get("required", False),
                }
                for binding in stream_bindings
            ],
            "binding_pairs": [
                {"stream_id": stream_id, "direction": direction}
                for stream_id, direction in binding_pairs
            ],
            "command_ids": command_ids,
            "transport_offers": transport_offers,
        },
        "package_contract": {
            "package_id": package_manifest.get("package_id"),
            "exported_stream_ids": exported_stream_ids,
            "exported_command_ids": exported_command_ids,
            "exported_module_ids": exported_module_ids,
            "manifest_stream_ids": manifest_stream_ids,
            "manifest_command_ids": manifest_command_ids,
            "manifest_module_ids": manifest_module_ids,
            "feedback_sink_provides_streams": sorted(
                str(stream_id)
                for stream_id in feedback_sink.get("provides_streams", [])
                if stream_id
            ),
        },
        "commands": [
            {
                "command": "validate_projected_motion_breath_shell_handoff",
                "status": "acknowledged" if status == "pass" else "rejected",
                "runtime_path": "python.hostessctl.v1",
            }
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess.projected_motion_breath.shell_handoff",
            "target_id": "hostess.projected_motion_breath.shell_handoff",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": issues,
        },
    }


def validate_pmb_shell_handoff_validation_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    shell_handoff = evidence.get("shell_handoff", {})
    package_contract = evidence.get("package_contract", {})
    binding_pairs = {
        (str(binding.get("stream_id")), str(binding.get("direction")))
        for binding in shell_handoff.get("binding_pairs", [])
        if isinstance(binding, dict) and binding.get("stream_id") and binding.get("direction")
    }
    bound_stream_ids = {stream_id for stream_id, _direction in binding_pairs}
    command_ids = set(shell_handoff.get("command_ids", []))
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.shell_handoff_validation_evidence.v1",
            "PMB shell handoff validation evidence schema is supported",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.status",
            evidence.get("status") == "pass",
            "PMB shell handoff validation evidence status passed",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.required_bindings",
            PMB_SHELL_HANDOFF_REQUIRED_BINDINGS.issubset(binding_pairs),
            "PMB shell handoff includes the required stream directions",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.stream_manifests",
            bound_stream_ids.issubset(set(package_contract.get("manifest_stream_ids", []))),
            "PMB shell handoff streams resolve to package stream manifests",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.commands",
            bool(command_ids)
            and command_ids.issubset(set(package_contract.get("manifest_command_ids", []))),
            "PMB shell handoff commands resolve to package command manifests",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.feedback_receipt_export",
            "stream.breath.feedback_receipt" in package_contract.get("exported_stream_ids", []),
            "PMB package exports stream.breath.feedback_receipt",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.feedback_sink",
            "stream.breath.feedback_receipt" in package_contract.get("feedback_sink_provides_streams", []),
            "PMB feedback sink provides stream.breath.feedback_receipt",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.transport_offer",
            bool(shell_handoff.get("transport_offers")),
            "PMB shell handoff declares at least one named transport offer",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.clean_boundary",
            execution.get("runtime_execution_performed") is False
            and execution.get("platform_execution_performed") is False
            and execution.get("device_required") is False
            and execution.get("external_transport_used") is False
            and execution.get("broker_transport_used") is False
            and execution.get("downstream_shell_runtime_used") is False
            and execution.get("legacy_app_dependency_used") is False
            and execution.get("legacy_rusty_xr_repo_used") is False,
            "PMB shell handoff validation avoided runtime shell, device, transport, and legacy repo dependencies",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_shell_handoff.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB shell handoff validation scorecard passed",
            "validation.pmb_shell_handoff_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.shell_handoff_validation.v1",
        "status": "pass" if not errors else "fail",
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def validate_pmb_android_replay_execution_evidence(
    evidence: dict[str, Any],
    *,
    package_root: Path,
    target: str,
    host_profile: str,
) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    core_summary = evidence.get("core_report_summary", {})
    package = evidence.get("package", {})
    local_package = projected_motion_package_snapshot(package_root)
    expected_manifest_hash = local_package.get("package_manifest_sha256")
    actual_manifest_hash = package.get("package_manifest_sha256")
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.android_replay_execution_evidence.v1",
            "PMB Android replay evidence schema is supported",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.status",
            evidence.get("status") == "pass",
            "PMB Android replay evidence status passed",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.target",
            evidence.get("target") == target and evidence.get("host_profile") == host_profile,
            f"PMB Android replay targeted {target}/{host_profile}",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.runtime_executed",
            execution.get("execution_performed") is True
            and execution.get("runtime_execution_performed") is True
            and execution.get("processor_core_executed") is True
            and execution.get("android_execution_performed") is True
            and execution.get("platform_execution_performed") is True,
            "PMB processor core execution was performed on Android",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.quest_flag",
            execution.get("quest_execution_performed") == (target == "quest"),
            f"PMB replay quest flag matched target={target}",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.synthetic_only",
            execution.get("synthetic_replay") is True
            and execution.get("openxr_runtime_used") is False
            and execution.get("live_sensor_used") is False
            and execution.get("controller_input_used") is False,
            "PMB Android replay avoided OpenXR, live sensors, and controller input",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.core_counts",
            core_summary.get("checked_cases", 0) >= 2
            and core_summary.get("checked_damaged_cases", 0) >= 2
            and core_summary.get("checked_adapter_normalization_cases", 0) >= 3
            and core_summary.get("checked_damaged_adapter_normalization_cases", 0) >= 2,
            "PMB core replay executed golden and adapter-normalization fixture sets on Android",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.package_manifest_hash",
            bool(expected_manifest_hash)
            and expected_manifest_hash != "unavailable"
            and actual_manifest_hash == expected_manifest_hash,
            "PMB Android packaged manifest hash matched the supplied package root",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_android_replay.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB Android app-side scorecard passed",
            "validation.pmb_android_replay_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_replay_execution_validation.v1",
        "status": "pass" if not errors else "fail",
        "target": target,
        "host_profile": host_profile,
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def validate_pmb_controller_preflight_evidence(
    evidence: dict[str, Any],
    *,
    package_root: Path,
    target: str,
    host_profile: str,
) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    report = evidence.get("controller_preflight_report_summary", {})
    package = evidence.get("package", {})
    local_package = projected_motion_package_snapshot(package_root)
    expected_manifest_hash = local_package.get("package_manifest_sha256")
    actual_manifest_hash = package.get("package_manifest_sha256")
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.android_controller_preflight_evidence.v1",
            "PMB controller preflight evidence schema is supported",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.status",
            evidence.get("status") == "pass",
            "PMB controller preflight evidence status passed",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.target",
            evidence.get("target") == target and evidence.get("host_profile") == host_profile,
            f"PMB controller preflight targeted {target}/{host_profile}",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.quest_execution",
            execution.get("quest_execution_performed") == (target == "quest")
            and execution.get("android_execution_performed") is True
            and execution.get("platform_execution_performed") is True
            and execution.get("device_required") is True,
            "PMB controller preflight was executed on the requested Android/Quest target",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.processor_executed",
            execution.get("processor_core_executed") is True
            and execution.get("runtime_execution_performed") is True
            and report.get("processor_core_executed") is True
            and report.get("runtime_execution_performed") is True,
            "PMB processor core executed through the controller preflight route",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.provider_route",
            execution.get("pmb_controller_path_preflight_passed") is True
            and execution.get("controller_provider_route_ready") is True
            and execution.get("provider_boundary_exercised") is True
            and report.get("controller_provider_route_ready") is True
            and report.get("provider_boundary_exercised") is True
            and report.get("output_stream_id") == "stream.motion.object_pose",
            "controller-shaped provider route emitted stream.motion.object_pose into PMB",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.non_human_gate",
            execution.get("synthetic_replay") is True
            and execution.get("preflight_fixture_packaged") is True
            and execution.get("openxr_runtime_used") is False
            and execution.get("live_sensor_used") is False
            and execution.get("physical_controller_input_used") is False
            and execution.get("controller_input_used") is False
            and execution.get("human_controller_trial_performed") is False
            and execution.get("manual_controller_trial_required") is True
            and report.get("physical_controller_input_used") is False
            and report.get("controller_input_used") is False
            and report.get("manual_controller_trial_required") is True,
            "preflight used packaged controller-shaped samples and left the human controller trial pending",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.report_counts",
            report.get("sample_count", 0) >= 3
            and report.get("normalized_sample_count", 0) >= 3
            and report.get("estimate_count", 0) >= 3,
            "controller preflight report contains normalized samples and PMB estimates",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.package_manifest_hash",
            bool(expected_manifest_hash)
            and expected_manifest_hash != "unavailable"
            and actual_manifest_hash == expected_manifest_hash,
            "PMB Android packaged manifest hash matched the supplied package root",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_controller_preflight.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB Android app-side controller preflight scorecard passed",
            "validation.pmb_controller_preflight_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_controller_preflight_validation.v1",
        "status": "pass" if not errors else "fail",
        "target": target,
        "host_profile": host_profile,
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def validate_pmb_quest_simulated_live_evidence(
    evidence: dict[str, Any],
    *,
    package_root: Path,
    target: str,
    host_profile: str,
) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    route = evidence.get("route_report_summary", {})
    broker = evidence.get("broker_publish_summary", {})
    package = evidence.get("package", {})
    local_package = projected_motion_package_snapshot(package_root)
    expected_manifest_hash = local_package.get("package_manifest_sha256")
    actual_manifest_hash = package.get("package_manifest_sha256")
    input_stream_ids = set(route.get("input_stream_ids", []))
    output_stream_ids = set(route.get("output_stream_ids", []))
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.android_simulated_live_execution_evidence.v1",
            "PMB Quest simulated live evidence schema is supported",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.status",
            evidence.get("status") == "pass",
            "PMB Quest simulated live evidence status passed",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.target",
            evidence.get("target") == target and evidence.get("host_profile") == host_profile,
            f"PMB simulated live targeted {target}/{host_profile}",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.quest_authority",
            execution.get("quest_execution_performed") is True
            and execution.get("android_execution_performed") is True
            and execution.get("platform_execution_performed") is True
            and execution.get("pmd_computed_on_quest") is True
            and execution.get("pmd_computed_on_pc") is False
            and execution.get("pc_processor_core_executed") is False
            and execution.get("processor_authority") == "quest_hostess_android_app",
            "PMD processing authority was the Quest Android app, not the PC",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.sources",
            {"bio:polar_acc", "stream.motion.object_pose"}.issubset(input_stream_ids)
            and {"stream.breath.volume", "stream.breath.feedback_state"}.issubset(output_stream_ids)
            and int(route.get("source_route_count", 0)) >= 2
            and int(route.get("breath_sample_count", 0)) >= 6
            and int(route.get("feedback_sample_count", 0)) >= 6,
            "simulated Polar ACC and controller object-pose routes produced PMB outputs",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.non_physical_gate",
            execution.get("simulated_polar_provider_used") is True
            and execution.get("simulated_controller_provider_used") is True
            and execution.get("physical_polar_ble_used") is False
            and execution.get("physical_controller_input_used") is False
            and execution.get("controller_input_used") is False
            and execution.get("manual_polar_trial_required") is True
            and execution.get("manual_controller_trial_required") is True,
            "run used simulated providers and did not claim physical Polar/controller input",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.broker_feedback",
            execution.get("broker_transport_used") is True
            and execution.get("feedback_published_to_broker") is True
            and broker.get("broker_transport_used") is True
            and int(broker.get("feedback_published_count", 0)) > 0,
            "Quest app published PMB feedback to the broker",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.makepad_receipts",
            int(broker.get("feedback_published_count", 0)) > 0
            and int(broker.get("feedback_receipt_count", 0)) == int(broker.get("feedback_published_count", -1))
            and int(execution.get("makepad_feedback_receipt_count", 0))
            == int(broker.get("feedback_published_count", -1)),
            "Makepad acknowledged every broker feedback sample",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.package_manifest_hash",
            bool(expected_manifest_hash)
            and expected_manifest_hash != "unavailable"
            and actual_manifest_hash == expected_manifest_hash,
            "PMB Android packaged manifest hash matched the supplied package root",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_simulated_live.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB Quest simulated live app-side scorecard passed",
            "validation.pmb_quest_simulated_live_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_simulated_live_validation.v1",
        "status": "pass" if not errors else "fail",
        "target": target,
        "host_profile": host_profile,
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def validate_pmb_quest_physical_live_evidence(
    evidence: dict[str, Any],
    *,
    package_root: Path,
    target: str,
    host_profile: str,
) -> dict[str, Any]:
    execution = evidence.get("execution", {})
    capture = evidence.get("input_capture_summary", {})
    route = evidence.get("route_report_summary", {})
    broker = evidence.get("broker_publish_summary", {})
    package = evidence.get("package", {})
    local_package = projected_motion_package_snapshot(package_root)
    expected_manifest_hash = local_package.get("package_manifest_sha256")
    actual_manifest_hash = package.get("package_manifest_sha256")
    input_stream_ids = set(route.get("input_stream_ids", []))
    output_stream_ids = set(route.get("output_stream_ids", []))
    checks = [
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.schema",
            evidence.get("$schema")
            == "rusty.hostess.projected_motion_breath.android_physical_live_execution_evidence.v1",
            "PMB Quest physical live evidence schema is supported",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.status",
            evidence.get("status") == "pass",
            "PMB Quest physical live evidence status passed",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.target",
            evidence.get("target") == target and evidence.get("host_profile") == host_profile,
            f"PMB physical live targeted {target}/{host_profile}",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.physical_inputs",
            capture.get("physical_polar_ble_used") is True
            and capture.get("physical_controller_input_used") is True
            and int(capture.get("polar_event_count", 0)) > 0
            and int(capture.get("active_tracked_connected_object_pose_count", 0)) > 0
            and execution.get("physical_polar_ble_used") is True
            and execution.get("physical_controller_input_used") is True
            and execution.get("controller_input_used") is True,
            "Quest broker captured physical Polar ACC and active/tracked/connected controller pose events",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.quest_authority",
            execution.get("quest_execution_performed") is True
            and execution.get("android_execution_performed") is True
            and execution.get("platform_execution_performed") is True
            and execution.get("pmd_computed_on_quest") is True
            and execution.get("pmd_computed_on_pc") is False
            and execution.get("pc_processor_core_executed") is False
            and execution.get("processor_authority") == "quest_hostess_android_app",
            "PMD processing authority was the Quest Android app, not the PC",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.not_simulated",
            execution.get("simulated_polar_provider_used") is False
            and execution.get("simulated_controller_provider_used") is False
            and execution.get("synthetic_live_route") is False
            and capture.get("physical_polar_ble_used") is True
            and capture.get("physical_controller_input_used") is True,
            "physical PMB route did not claim simulated providers",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.route",
            {"bio:polar_acc", "stream.motion.object_pose"}.issubset(input_stream_ids)
            and {"stream.breath.volume", "stream.breath.feedback_state"}.issubset(output_stream_ids)
            and route.get("status") == "pass"
            and route.get("external_transport_used") is True
            and route.get("live_sensor_used") is True
            and route.get("plan_only_fixture") is False
            and int(route.get("breath_sample_count", 0)) > 0
            and int(route.get("feedback_sample_count", 0)) > 0,
            "PMB live route consumed physical broker transport events and produced breath feedback",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.makepad_receipts",
            int(broker.get("feedback_published_count", 0)) > 0
            and int(broker.get("feedback_receipt_count", 0)) == int(broker.get("feedback_published_count", -1))
            and int(execution.get("makepad_feedback_receipt_count", 0))
            == int(broker.get("feedback_published_count", -1)),
            "Makepad acknowledged every broker feedback sample",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.package_manifest_hash",
            bool(expected_manifest_hash)
            and expected_manifest_hash != "unavailable"
            and actual_manifest_hash == expected_manifest_hash,
            "PMB Android packaged manifest hash matched the supplied package root",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "hostess.check.pmb_quest_physical_live.app_scorecard",
            evidence.get("scorecard", {}).get("status") == "pass",
            "PMB Quest physical live app-side scorecard passed",
            "validation.pmb_quest_physical_live_failed",
        ),
    ]
    errors = [
        check["evidence"]
        for check in checks
        if check["status"] != "pass"
    ]
    return {
        "$schema": "rusty.hostess.projected_motion_breath.android_physical_live_validation.v1",
        "status": "pass" if not errors else "fail",
        "target": target,
        "host_profile": host_profile,
        "evidence_status": evidence.get("status"),
        "checks": checks,
        "errors": errors,
    }


def write_pmb_host_run_evidence(raw_evidence_path: Path, validation_report_path: Path, raw: dict[str, Any]) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_desktop_replay_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB desktop replay evidence and validation report passed",
        ),
        pmb_scorecard_check(
            "validation.check.package_manifest_hash",
            bool(raw.get("package", {}).get("package_manifest_sha256")),
            "PMB package manifest hash was recorded",
        ),
        pmb_scorecard_check(
            "validation.check.processor_core_execution",
            raw.get("execution", {}).get("processor_core_executed") is True,
            "PMB processor core executed through Hostess",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.desktop_replay.{started_ms}",
        "bundle_id": "host_run.bundle.projected_motion_breath.desktop_replay",
        "validation_slot_id": "host_run.slot.projected_motion_breath.desktop_replay",
        "host_profile": "host.desktop",
        "app_id": "app.rusty_hostess_t.desktop",
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.breath.projected_motion",
            "module.breath.dynamics",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_desktop_replay_evidence",
            "artifact.projected_motion_breath_core_validation_report",
            "artifact.projected_motion_breath_desktop_replay_validation_report",
            "artifact.host_run_evidence",
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.projected_motion_breath.desktop_replay",
            "target_id": f"host_run.run.projected_motion_breath.desktop_replay.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_live_route_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    summary = raw.get("route_report_summary", {})
    execution = raw.get("execution", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_live_route_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB live broker route self-test evidence and validation report passed",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_processor_core",
            execution.get("processor_core_executed") is True
            and execution.get("runtime_execution_performed") is True,
            "PMB processor core executed through Hostess",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_non_live_gate",
            execution.get("plan_only") is True
            and execution.get("broker_transport_used") is False
            and execution.get("live_sensor_used") is False
            and execution.get("quest_execution_performed") is False,
            "PMB route self-test did not use live broker/device resources",
            "validation.pmb_live_route_self_test_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_live_route_feedback_ack",
            int(summary.get("receipt_count", 0)) == int(summary.get("feedback_sample_count", -1))
            and int(summary.get("receipt_count", 0)) > 0,
            "PMB route self-test included one Makepad receipt plan per feedback sample",
            "validation.pmb_live_route_self_test_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.live_broker_route_self_test.{started_ms}",
        "bundle_id": "host_run.bundle.projected_motion_breath.live_broker_route_self_test",
        "validation_slot_id": "host_run.slot.projected_motion_breath.live_broker_route_self_test",
        "host_profile": "host.desktop",
        "app_id": "app.rusty_hostess_t.desktop",
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.breath.projected_motion",
            "module.breath.feedback_sink",
            "module.hostess.manifold_value_recorder",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_live_broker_route_self_test_evidence",
            "artifact.projected_motion_breath_live_broker_route_report",
            "artifact.projected_motion_breath_live_broker_route_self_test_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "input_stream_ids": summary.get("input_stream_ids", []),
            "normalized_stream_ids": summary.get("normalized_stream_ids", []),
            "output_stream_ids": summary.get("output_stream_ids", []),
            "source_route_count": summary.get("source_route_count"),
            "breath_sample_count": summary.get("breath_sample_count"),
            "feedback_sample_count": summary.get("feedback_sample_count"),
            "receipt_count": summary.get("receipt_count"),
            "plan_only": execution.get("plan_only"),
            "broker_transport_used": execution.get("broker_transport_used"),
            "live_sensor_used": execution.get("live_sensor_used"),
            "quest_execution_performed": execution.get("quest_execution_performed"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.projected_motion_breath.live_broker_route_self_test",
            "target_id": f"host_run.run.projected_motion_breath.live_broker_route_self_test.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_shell_handoff_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    shell_handoff = raw.get("shell_handoff", {})
    package_contract = raw.get("package_contract", {})
    execution = raw.get("execution", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB shell handoff evidence and validation report passed",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff_receipt_export",
            "stream.breath.feedback_receipt" in package_contract.get("exported_stream_ids", [])
            and "stream.breath.feedback_receipt" in package_contract.get("feedback_sink_provides_streams", []),
            "PMB package exports feedback receipts and the feedback sink provides them",
            "validation.pmb_shell_handoff_failed",
        ),
        pmb_scorecard_check(
            "validation.check.pmb_shell_handoff_clean_boundary",
            execution.get("runtime_execution_performed") is False
            and execution.get("legacy_app_dependency_used") is False
            and execution.get("legacy_rusty_xr_repo_used") is False
            and execution.get("downstream_shell_runtime_used") is False,
            "PMB shell handoff host-run evidence records a package-only validation boundary",
            "validation.pmb_shell_handoff_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.shell_handoff.{started_ms}",
        "bundle_id": "host_run.bundle.projected_motion_breath.shell_handoff",
        "validation_slot_id": "host_run.slot.projected_motion_breath.shell_handoff",
        "host_profile": "host.desktop",
        "app_id": "app.rusty_hostess_t.desktop",
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.motion.object_pose_provider",
            "module.breath.projected_motion",
            "module.breath.feedback_sink",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_shell_handoff_evidence",
            "artifact.projected_motion_breath_shell_handoff_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "handoff_id": shell_handoff.get("handoff_id"),
            "target_host_profile": shell_handoff.get("target_host_profile"),
            "shell_app_id": shell_handoff.get("shell_app_id"),
            "stream_bindings": shell_handoff.get("binding_pairs", []),
            "command_ids": shell_handoff.get("command_ids", []),
            "transport_ids": [
                offer.get("transport_id")
                for offer in shell_handoff.get("transport_offers", [])
                if isinstance(offer, dict)
            ],
            "runtime_execution_performed": execution.get("runtime_execution_performed"),
            "broker_transport_used": execution.get("broker_transport_used"),
            "legacy_app_dependency_used": execution.get("legacy_app_dependency_used"),
            "legacy_rusty_xr_repo_used": execution.get("legacy_rusty_xr_repo_used"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.projected_motion_breath.shell_handoff",
            "target_id": f"host_run.run.projected_motion_breath.shell_handoff.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_android_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
    target: str,
    host_profile: str,
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_android_replay_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB Android replay evidence and validation report passed",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "validation.check.package_manifest_hash",
            bool(raw.get("package", {}).get("package_manifest_sha256")),
            "PMB package manifest hash was recorded",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "validation.check.processor_core_execution",
            raw.get("execution", {}).get("processor_core_executed") is True
            and raw.get("execution", {}).get("android_execution_performed") is True,
            "PMB processor core executed through Hostess Android app",
            "validation.pmb_android_replay_failed",
        ),
        pmb_scorecard_check(
            "validation.check.synthetic_quest_replay",
            target != "quest" or raw.get("execution", {}).get("quest_execution_performed") is True,
            "PMB synthetic replay executed on Quest target" if target == "quest" else "PMB synthetic replay executed on mobile target",
            "validation.pmb_android_replay_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.{target}_synthetic_replay.{started_ms}",
        "bundle_id": f"host_run.bundle.projected_motion_breath.{target}_synthetic_replay",
        "validation_slot_id": f"host_run.slot.projected_motion_breath.{target}_synthetic_replay",
        "host_profile": f"host.{host_profile}",
        "app_id": host_app_for(host_profile),
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.breath.projected_motion",
            "module.breath.dynamics",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_android_replay_evidence",
            "artifact.projected_motion_breath_core_validation_report",
            "artifact.projected_motion_breath_android_replay_validation_report",
            "artifact.host_run_evidence",
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": f"scorecard.host_run.projected_motion_breath.{target}_synthetic_replay",
            "target_id": f"host_run.run.projected_motion_breath.{target}_synthetic_replay.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_controller_preflight_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
    target: str,
    host_profile: str,
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    execution = raw.get("execution", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_controller_preflight_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB controller preflight evidence and validation report passed",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "validation.check.processor_core_execution",
            execution.get("processor_core_executed") is True
            and execution.get("runtime_execution_performed") is True
            and execution.get("android_execution_performed") is True,
            "PMB processor core executed through Hostess Android controller preflight",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "validation.check.controller_provider_route_ready",
            execution.get("controller_provider_route_ready") is True
            and execution.get("provider_boundary_exercised") is True
            and execution.get("pmb_controller_path_preflight_passed") is True,
            "controller provider route is ready at the PMB provider boundary",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "validation.check.non_human_gate",
            execution.get("controller_input_used") is False
            and execution.get("physical_controller_input_used") is False
            and execution.get("manual_controller_trial_required") is True
            and execution.get("human_controller_trial_performed") is False,
            "physical controller input was not used and the manual human controller trial remains pending",
            "validation.pmb_controller_preflight_failed",
        ),
        pmb_scorecard_check(
            "validation.check.quest_target",
            target != "quest" or execution.get("quest_execution_performed") is True,
            "PMB controller preflight executed on Quest target" if target == "quest" else "PMB controller preflight executed on mobile target",
            "validation.pmb_controller_preflight_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.{target}_controller_preflight.{started_ms}",
        "bundle_id": f"host_run.bundle.projected_motion_breath.{target}_controller_preflight",
        "validation_slot_id": f"host_run.slot.projected_motion_breath.{target}_controller_preflight",
        "host_profile": f"host.{host_profile}",
        "app_id": host_app_for(host_profile),
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.motion.object_pose_provider",
            "module.breath.projected_motion",
            "module.breath.dynamics",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_controller_preflight_evidence",
            "artifact.projected_motion_breath_controller_preflight_report",
            "artifact.projected_motion_breath_controller_preflight_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "pmb_controller_path_preflight_passed": execution.get("pmb_controller_path_preflight_passed"),
            "quest_execution_performed": execution.get("quest_execution_performed"),
            "processor_core_executed": execution.get("processor_core_executed"),
            "controller_provider_route_ready": execution.get("controller_provider_route_ready"),
            "physical_controller_input_used": execution.get("physical_controller_input_used"),
            "controller_input_used": execution.get("controller_input_used"),
            "manual_controller_trial_required": execution.get("manual_controller_trial_required"),
            "human_controller_trial_performed": execution.get("human_controller_trial_performed"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": f"scorecard.host_run.projected_motion_breath.{target}_controller_preflight",
            "target_id": f"host_run.run.projected_motion_breath.{target}_controller_preflight.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_quest_simulated_live_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
    target: str,
    host_profile: str,
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    execution = raw.get("execution", {})
    route = raw.get("route_report_summary", {})
    broker = raw.get("broker_publish_summary", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_quest_simulated_live_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB Quest simulated live evidence and validation report passed",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.quest_processor_authority",
            execution.get("pmd_computed_on_quest") is True
            and execution.get("pmd_computed_on_pc") is False
            and execution.get("processor_authority") == "quest_hostess_android_app",
            "PMD processing authority stayed on the Quest Android app",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.simulated_polar_controller_sources",
            {"bio:polar_acc", "stream.motion.object_pose"}.issubset(set(route.get("input_stream_ids", [])))
            and int(route.get("source_route_count", 0)) >= 2,
            "simulated Polar ACC and controller object-pose routes ran in the PMB processor",
            "validation.pmb_quest_simulated_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.makepad_feedback_receipts",
            int(broker.get("feedback_published_count", 0)) > 0
            and int(broker.get("feedback_receipt_count", 0)) == int(broker.get("feedback_published_count", -1)),
            "Makepad acknowledged every Quest-published feedback sample",
            "validation.pmb_quest_simulated_live_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.{target}_simulated_live.{started_ms}",
        "bundle_id": f"host_run.bundle.projected_motion_breath.{target}_simulated_live",
        "validation_slot_id": f"host_run.slot.projected_motion_breath.{target}_simulated_live",
        "host_profile": f"host.{host_profile}",
        "app_id": host_app_for(host_profile),
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "module.motion.object_pose_provider",
            "module.breath.projected_motion",
            "module.breath.feedback_sink",
            "app.makepad_camera_shell.breath_feedback",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_quest_simulated_live_evidence",
            "artifact.projected_motion_breath_live_route_report",
            "artifact.projected_motion_breath_broker_publish_report",
            "artifact.projected_motion_breath_quest_simulated_live_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "pmd_computed_on_quest": execution.get("pmd_computed_on_quest"),
            "pmd_computed_on_pc": execution.get("pmd_computed_on_pc"),
            "processor_authority": execution.get("processor_authority"),
            "simulated_polar_provider_used": execution.get("simulated_polar_provider_used"),
            "simulated_controller_provider_used": execution.get("simulated_controller_provider_used"),
            "physical_polar_ble_used": execution.get("physical_polar_ble_used"),
            "physical_controller_input_used": execution.get("physical_controller_input_used"),
            "controller_input_used": execution.get("controller_input_used"),
            "manual_controller_trial_required": execution.get("manual_controller_trial_required"),
            "input_stream_ids": route.get("input_stream_ids", []),
            "feedback_published_count": broker.get("feedback_published_count"),
            "feedback_receipt_count": broker.get("feedback_receipt_count"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": f"scorecard.host_run.projected_motion_breath.{target}_simulated_live",
            "target_id": f"host_run.run.projected_motion_breath.{target}_simulated_live.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def write_pmb_quest_physical_live_host_run_evidence(
    raw_evidence_path: Path,
    validation_report_path: Path,
    raw: dict[str, Any],
    target: str,
    host_profile: str,
) -> None:
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    execution = raw.get("execution", {})
    capture = raw.get("input_capture_summary", {})
    route = raw.get("route_report_summary", {})
    broker = raw.get("broker_publish_summary", {})
    checks = [
        pmb_scorecard_check(
            "validation.check.pmb_quest_physical_live_status",
            validation_report.get("status") == "pass" and raw.get("status") == "pass",
            "PMB Quest physical live evidence and validation report passed",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.physical_polar_controller_inputs",
            execution.get("physical_polar_ble_used") is True
            and execution.get("physical_controller_input_used") is True
            and int(capture.get("polar_event_count", 0)) > 0
            and int(capture.get("active_tracked_connected_object_pose_count", 0)) > 0,
            "physical Polar ACC and active/tracked/connected controller pose events were captured on Quest",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.quest_processor_authority",
            execution.get("pmd_computed_on_quest") is True
            and execution.get("pmd_computed_on_pc") is False
            and execution.get("processor_authority") == "quest_hostess_android_app",
            "PMD processing authority stayed on the Quest Android app",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.real_transport_route",
            route.get("external_transport_used") is True
            and route.get("live_sensor_used") is True
            and route.get("plan_only_fixture") is False
            and {"bio:polar_acc", "stream.motion.object_pose"}.issubset(set(route.get("input_stream_ids", []))),
            "PMB route consumed real broker transport events",
            "validation.pmb_quest_physical_live_failed",
        ),
        pmb_scorecard_check(
            "validation.check.makepad_feedback_receipts",
            int(broker.get("feedback_published_count", 0)) > 0
            and int(broker.get("feedback_receipt_count", 0)) == int(broker.get("feedback_published_count", -1)),
            "Makepad acknowledged every Quest-published feedback sample",
            "validation.pmb_quest_physical_live_failed",
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.projected_motion_breath.{target}_physical_live.{started_ms}",
        "bundle_id": f"host_run.bundle.projected_motion_breath.{target}_physical_live",
        "validation_slot_id": f"host_run.slot.projected_motion_breath.{target}_physical_live",
        "host_profile": f"host.{host_profile}",
        "app_id": host_app_for(host_profile),
        "package_ids": ["package.projected_motion_breath"],
        "module_ids": [
            "provider.polar_h10.ble",
            "module.motion.object_pose_provider",
            "module.breath.projected_motion",
            "module.breath.feedback_sink",
            "app.makepad_camera_shell.breath_feedback",
        ],
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.projected_motion_breath_quest_physical_live_evidence",
            "artifact.projected_motion_breath_physical_input_capture_report",
            "artifact.projected_motion_breath_transport_events_jsonl",
            "artifact.projected_motion_breath_live_route_report",
            "artifact.projected_motion_breath_broker_publish_report",
            "artifact.projected_motion_breath_quest_physical_live_validation_report",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "pmd_computed_on_quest": execution.get("pmd_computed_on_quest"),
            "pmd_computed_on_pc": execution.get("pmd_computed_on_pc"),
            "processor_authority": execution.get("processor_authority"),
            "physical_polar_ble_used": execution.get("physical_polar_ble_used"),
            "physical_controller_input_used": execution.get("physical_controller_input_used"),
            "simulated_polar_provider_used": execution.get("simulated_polar_provider_used"),
            "simulated_controller_provider_used": execution.get("simulated_controller_provider_used"),
            "input_stream_ids": route.get("input_stream_ids", []),
            "polar_event_count": capture.get("polar_event_count"),
            "object_pose_event_count": capture.get("object_pose_event_count"),
            "active_tracked_connected_object_pose_count": capture.get("active_tracked_connected_object_pose_count"),
            "feedback_published_count": broker.get("feedback_published_count"),
            "feedback_receipt_count": broker.get("feedback_receipt_count"),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": f"scorecard.host_run.projected_motion_breath.{target}_physical_live",
            "target_id": f"host_run.run.projected_motion_breath.{target}_physical_live.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def projected_motion_package_snapshot(package_root: Path) -> dict[str, Any]:
    manifest = package_root / "manifests" / "package.manifold.json"
    return {
        "package_id": "package.projected_motion_breath",
        "package_manifest_sha256": sha256_file(manifest),
        "stream_manifest_sha256": sha256_manifest_children(package_root / "manifests" / "streams"),
        "module_manifest_sha256": sha256_manifest_children(package_root / "manifests" / "modules"),
        "command_manifest_sha256": sha256_manifest_children(package_root / "manifests" / "commands"),
    }


def sha256_manifest_children(directory: Path) -> dict[str, str]:
    if not directory.exists():
        return {}
    return {
        path.stem: sha256_file(path)
        for path in sorted(directory.glob("*.json"))
    }


def pmb_checked_counts(core_report: dict[str, Any] | None) -> dict[str, int]:
    names = [
        "checked_profiles",
        "checked_command_payloads",
        "checked_damaged_command_payloads",
        "checked_source_bindings",
        "checked_damaged_source_bindings",
        "checked_adapter_normalization_cases",
        "checked_damaged_adapter_normalization_cases",
        "checked_cases",
        "checked_damaged_cases",
    ]
    return {name: int(core_report.get(name, 0)) if core_report else 0 for name in names}


def pmb_scorecard_check(
    check_id: str,
    passed: bool,
    evidence: str,
    issue_code: str = "validation.pmb_desktop_replay_failed",
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
        "issue_codes": [] if passed else [issue_code],
    }


def write_contract_evidence(raw_evidence_path: Path, validation_report_path: Path, host_profile: str) -> None:
    raw = json.loads(raw_evidence_path.read_text(encoding="utf-8"))
    report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    started_ms = iso_to_epoch_ms(raw.get("started_at_utc"))
    ended_ms = iso_to_epoch_ms(raw.get("ended_at_utc"))
    stream_ids = [stream.get("stream_id") for stream in raw.get("streams", []) if stream.get("stream_id")]
    module_ids = [stream.get("module_id") for stream in raw.get("streams", []) if stream.get("module_id")]
    run_segment = module_segment(module_ids) if module_ids else stream_segment(stream_ids)
    checks = [
        scorecard_check(
            "validation.check.live_capture_status",
            report.get("status") == "pass" and raw.get("status") == "pass",
            "live capture evidence and validation report passed",
        ),
        scorecard_check(
            "validation.check.package_manifest_hash",
            bool(raw.get("package", {}).get("package_manifest_sha256")),
            "package manifest hash matched the supplied package root",
        ),
        scorecard_check(
            "validation.check.stream_samples",
            any(stream.get("status") == "pass" for stream in raw.get("streams", [])),
            "expected stream produced decoded samples or HR/RR events",
        ),
    ]
    status = "fail" if report.get("status") != "pass" or raw.get("status") != "pass" else "pass"
    contract = {
        "$schema": "rusty.manifold.host_run.run_evidence.v1",
        "run_id": f"host_run.run.live_capture.{host_profile}.{run_segment}.{started_ms}",
        "bundle_id": "host_run.bundle.polar_h10.live_smoke",
        "validation_slot_id": "host_run.slot.live_smoke",
        "host_profile": f"host.{host_profile}",
        "app_id": str(raw.get("software", {}).get("host_app", host_app_for(host_profile))),
        "package_ids": [str(raw.get("package", {}).get("package_id", "package.polar_h10"))],
        "module_ids": module_ids,
        "status": status,
        "started_at_ms": started_ms,
        "ended_at_ms": ended_ms,
        "evidence_artifacts": [
            "artifact.live_capture_evidence",
            "artifact.live_capture_validation_report",
            "artifact.host_run_evidence",
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.live_capture",
            "target_id": f"host_run.run.live_capture.{host_profile}.{run_segment}.{started_ms}",
            "target_revision": 1,
            "status": status,
            "checks": checks,
            "issues": [
                {
                    "code": "validation.live_capture_failed",
                    "severity": "error",
                    "message": "; ".join(report.get("errors", [])),
                    "related_id": f"host.{host_profile}",
                }
            ]
            if report.get("errors")
            else [],
        },
    }
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.host-run-evidence.json")
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def scorecard_check(check_id: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
        "issue_codes": [] if passed else ["validation.live_capture_failed"],
    }


def stream_segment(stream_ids: list[str]) -> str:
    if not stream_ids:
        return "unknown"
    return stream_ids[0].split(".")[-1].replace("-", "_")


def module_segment(module_ids: list[str]) -> str:
    if not module_ids:
        return "unknown"
    pieces = [module_id.split(".")[-1].replace("-", "_") for module_id in module_ids]
    joined = "_".join(pieces)
    return joined[:80]


def host_app_for(host_profile: str) -> str:
    if host_profile == "desktop":
        return "app.rusty_hostess_t.desktop"
    if host_profile == "headset":
        return "app.rusty_hostess_t.quest"
    return "app.rusty_hostess_t.android"


def iso_to_epoch_ms(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.replace("Z", "+00:00")
    return int(datetime.fromisoformat(normalized).timestamp() * 1000)


def run(
    command: list[str], *, allow_failure: bool = False, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, cwd=cwd)
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result


def run_captured(
    command: list[str], *, allow_failure: bool = False, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
