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

from tools.check_live_capture_evidence import package_snapshot  # noqa: E402
from tools.hostessctl import android_files  # noqa: E402
from tools.hostessctl import makepad_shell_contract as makepad_shell_contract_launcher  # noqa: E402
from tools.hostessctl.makepad_visual_profile import (  # noqa: E402
    makepad_visual_profile_runtime_properties,
)
from tools.hostessctl.pmb_evidence import (  # noqa: E402
    PMB_BREATH_FEEDBACK_RECEIPT_STREAM,
    PMB_BREATH_FEEDBACK_STATE_STREAM,
    PMB_BREATH_SCALE_SMOOTHING_ALPHA,
    PMB_BREATH_SCALE_VOLUME0,
    PMB_BREATH_SCALE_VOLUME1,
    PMB_BREATH_SELECTION_STATE_STREAM,
    PMB_BREATH_VOLUME_CONTROLLER_STREAM,
    PMB_BREATH_VOLUME_POLAR_STREAM,
    PMB_BREATH_VOLUME_SELECTED_STREAM,
    PMB_BREATH_VOLUME_STREAM,
    build_pmb_desktop_replay_execution_evidence,
    build_pmb_live_route_self_test_evidence,
    build_pmb_shell_handoff_validation_evidence,
    default_pmb_shell_handoff_path,
    graph_report_streams,
    host_app_for,
    iso_to_epoch_ms,
    parse_pmb_core_report,
    projected_motion_breath_package_root,
    projected_motion_package_snapshot,
    validate_pmb_android_replay_execution_evidence,
    validate_pmb_controller_preflight_evidence,
    validate_pmb_desktop_replay_execution_evidence,
    validate_pmb_live_route_self_test_evidence,
    validate_pmb_quest_physical_live_evidence,
    validate_pmb_quest_simulated_live_evidence,
    validate_pmb_shell_handoff_validation_evidence,
    write_contract_evidence,
    write_pmb_android_host_run_evidence,
    write_pmb_controller_preflight_host_run_evidence,
    write_pmb_host_run_evidence,
    write_pmb_live_route_host_run_evidence,
    write_pmb_quest_physical_live_host_run_evidence,
    write_pmb_quest_simulated_live_host_run_evidence,
    write_pmb_shell_handoff_host_run_evidence,
)
from tools.hostessctl.recording_evidence import (  # noqa: E402
    build_manifold_value_recording_evidence,
    recording_segment,
    validate_broker_telemetry_observer_evidence,
    validate_broker_websocket_stream_recording_evidence,
    validate_manifold_value_recording_evidence,
    write_manifold_value_recording_host_run_evidence,
)
from tools.hostessctl.telemetry_render import (  # noqa: E402
    render_desktop_telemetry,
    render_sidecar_path,
    sanitize_remote_name,
    validate_render_output,
)
from tools.telemetry_snapshot import build_snapshot, write_snapshot  # noqa: E402

ANDROID_PACKAGE = "io.github.mesmerprism.rustyhostess.t"
MANIFOLD_BROKER_PACKAGE = "io.github.mesmerprism.rustymanifold.broker"
MANIFOLD_BROKER_ACTIVITY = f"{MANIFOLD_BROKER_PACKAGE}/.BrokerStartActivity"
LEGACY_REFERENCE_BROKER_PACKAGE = "com.example.rustyxr.broker"
LEGACY_REFERENCE_BROKER_ACTIVITY = f"{LEGACY_REFERENCE_BROKER_PACKAGE}/.BrokerStartActivity"
BROKER_PACKAGE = MANIFOLD_BROKER_PACKAGE
BROKER_ACTIVITY = MANIFOLD_BROKER_ACTIVITY
BROKER_PORT = 8765
BROKER_LOCAL_FORWARD_PORT = 18765
MANIFOLD_COMMAND_SCHEMA = "rusty.manifold.command.envelope.v1"
MANIFOLD_BROKER_EVENTS_PATH = "/manifold/v1/events"
MAKEPAD_ANDROID_PACKAGE = "io.github.mesmerprism.rustyhostess.makepad"
MAKEPAD_ANDROID_ACTIVITY = f"{MAKEPAD_ANDROID_PACKAGE}/.MakepadApp"
MAKEPAD_ANDROID_XR_ACTIVITY = f"{MAKEPAD_ANDROID_PACKAGE}/.MakepadAppXr"
MAKEPAD_PROVIDER_PACKAGE = MAKEPAD_ANDROID_PACKAGE
MAKEPAD_PROVIDER_ACTIVITY = MAKEPAD_ANDROID_XR_ACTIVITY
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

MANIFOLD_VALUE_ALIASES = {
    "polar.hr_rr": "stream.polar_h10.hr_rr",
    "polar.ecg": "stream.polar_h10.ecg",
    "polar.acc": "stream.polar_h10.acc",
    "polar.coherence": "stream.polar_h10.coherence",
    "motion.object_pose": "stream.motion.object_pose",
    "motion.vector3": "stream.motion.vector3",
    "breath.volume": "stream.breath.volume",
    "breath.volume.selected": "stream.breath.volume.selected",
    "breath.volume.polar": "stream.breath.volume.polar",
    "breath.volume.controller": "stream.breath.volume.controller",
    "breath.dynamics": "stream.breath.dynamics",
    "breath.feedback_state": "stream.breath.feedback_state",
}

def broker_activity_for_package(package_name: str) -> str:
    return f"{package_name}/.BrokerStartActivity"


def selected_broker_package(args: argparse.Namespace) -> str:
    return str(getattr(args, "broker_package", None) or BROKER_PACKAGE)


def selected_broker_activity(args: argparse.Namespace) -> str:
    activity = getattr(args, "broker_activity", None)
    if activity:
        return str(activity)
    return broker_activity_for_package(selected_broker_package(args))


def broker_identity(args: argparse.Namespace) -> dict[str, Any]:
    package_name = selected_broker_package(args)
    activity = selected_broker_activity(args)
    legacy_reference = package_name == LEGACY_REFERENCE_BROKER_PACKAGE
    return {
        "$schema": "rusty.hostess.manifold_broker_identity.v1",
        "authority": "rusty.manifold",
        "profile_id": (
            "broker.profile.legacy_reference"
            if legacy_reference
            else "broker.profile.rusty_manifold_android"
        ),
        "package_name": package_name,
        "activity": activity,
        "default_selected": package_name == BROKER_PACKAGE and activity == BROKER_ACTIVITY,
        "legacy_reference_package": legacy_reference,
        "legacy_reference_allowed": legacy_reference,
    }


def attach_broker_identity(evidence: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    annotated = dict(evidence)
    annotated["broker_identity"] = broker_identity(args)
    return annotated


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
    "stream.breath.volume.selected": {
        "value_id": "value.breath.volume.selected",
        "stream_id": "stream.breath.volume.selected",
        "provider_id": "processor.projected_motion_breath.selector",
        "provider_kind": "processor_output",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "breath_volume",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": True,
        "blocked_reason": "selected breath output recording requires a bound PMB source selection route",
    },
    "stream.breath.volume.polar": {
        "value_id": "value.breath.volume.polar",
        "stream_id": "stream.breath.volume.polar",
        "provider_id": "processor.projected_motion_breath.polar",
        "provider_kind": "processor_output",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "breath_volume",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": True,
        "blocked_reason": "Polar breath output recording requires a bound Polar PMD route",
    },
    "stream.breath.volume.controller": {
        "value_id": "value.breath.volume.controller",
        "stream_id": "stream.breath.volume.controller",
        "provider_id": "processor.projected_motion_breath.controller",
        "provider_kind": "processor_output",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "breath_volume",
        "supported_targets": ["quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": True,
        "blocked_reason": "Controller breath output recording requires a bound XR controller pose route",
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
    run_pmb_simulated_live_parser.add_argument("--broker-activity")
    run_pmb_simulated_live_parser.add_argument("--broker-port", type=int, default=BROKER_PORT)
    run_pmb_simulated_live_parser.add_argument("--makepad-package", default=MAKEPAD_ANDROID_PACKAGE)
    run_pmb_simulated_live_parser.add_argument("--makepad-activity", default=MAKEPAD_ANDROID_XR_ACTIVITY)
    run_pmb_simulated_live_parser.add_argument("--makepad-settle-seconds", type=float, default=8.0)
    run_pmb_simulated_live_parser.add_argument("--feedback-publish-limit", type=int, default=12)
    run_pmb_simulated_live_parser.add_argument("--breath-selected-source", choices=["auto", "polar", "controller"], default="auto")
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
    run_pmb_physical_live_parser.add_argument("--broker-activity")
    run_pmb_physical_live_parser.add_argument("--broker-port", type=int, default=BROKER_PORT)
    run_pmb_physical_live_parser.add_argument("--makepad-package", default=MAKEPAD_ANDROID_PACKAGE)
    run_pmb_physical_live_parser.add_argument("--makepad-activity", default=MAKEPAD_ANDROID_XR_ACTIVITY)
    run_pmb_physical_live_parser.add_argument("--makepad-settle-seconds", type=float, default=10.0)
    run_pmb_physical_live_parser.add_argument("--makepad-pose-controller", choices=["left", "right"], default="right")
    run_pmb_physical_live_parser.add_argument("--makepad-pose-kind", choices=["grip", "aim"], default="grip")
    run_pmb_physical_live_parser.add_argument("--makepad-pose-sample-hz", type=float, default=20.0)
    run_pmb_physical_live_parser.add_argument("--feedback-publish-limit", type=int, default=24)
    run_pmb_physical_live_parser.add_argument("--breath-selected-source", choices=["auto", "polar", "controller"], default="auto")
    run_pmb_physical_live_parser.add_argument("--receipt-listen-seconds", type=float, default=6.0)
    run_pmb_physical_live_parser.add_argument("--run-until-stopped", action="store_true")
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
    observe_broker_telemetry.add_argument("--broker-activity")
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
    record_values.add_argument("--broker-activity")
    record_values.add_argument("--broker-port", type=int, default=BROKER_PORT)
    record_values.add_argument("--broker-local-port", type=int, default=BROKER_LOCAL_FORWARD_PORT)
    record_values.add_argument("--makepad-provider-package", default=MAKEPAD_PROVIDER_PACKAGE)
    record_values.add_argument("--makepad-provider-activity", default=MAKEPAD_PROVIDER_ACTIVITY)
    record_values.add_argument("--makepad-pose-controller", choices=["left", "right"], default="right")
    record_values.add_argument("--makepad-pose-kind", choices=["grip", "aim"], default="grip")
    record_values.add_argument("--makepad-pose-sample-hz", type=float, default=20.0)
    record_values.add_argument("--makepad-pose-ready-timeout-seconds", type=float, default=20.0)
    record_values.add_argument("--cargo", default="cargo")
    record_values.add_argument("--pmb-live-processor", action="store_true")
    record_values.add_argument("--pmb-feedback-publish-limit", type=int, default=24)
    record_values.add_argument("--pmb-breath-selected-source", choices=["auto", "polar", "controller"], default="auto")
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
        run([args.adb, "-s", args.serial, "shell", "am", "start", "-n", selected_broker_activity(args)])
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
            "breath_selected_source",
            str(getattr(args, "breath_selected_source", "auto") or "auto"),
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
    evidence = attach_broker_identity(json.loads(out.read_text(encoding="utf-8")), args)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
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
    if args.duration_seconds <= 0 and not getattr(args, "run_until_stopped", False):
        raise SystemExit("--duration-seconds must be greater than zero")
    if getattr(args, "run_until_stopped", False) and getattr(args, "foreground_hostess", False):
        raise SystemExit("--run-until-stopped requires the background Hostess service")
    host_profile = "headset"
    if not getattr(args, "no_launch_broker", False):
        grant_broker_runtime_permissions(args)
        run([args.adb, "-s", args.serial, "shell", "am", "start", "-n", selected_broker_activity(args)])
    if not getattr(args, "no_launch_makepad", False):
        configure_makepad_physical_pmb_provider(args)
    clear_android_pmb_physical_live_artifacts(args)
    run([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    command = pmb_physical_live_start_command(args, host_profile)
    run(command)
    if getattr(args, "run_until_stopped", False):
        started = {
            "$schema": "rusty.hostess.projected_motion_breath.physical_live_service_start.v1",
            "status": "running",
            "target": args.target,
            "host_profile": host_profile,
            "run_until_stopped": True,
            "pmd_computed_on_quest": True,
            "pmd_computed_on_pc": False,
            "publish_mode": "event_driven_live_processor",
            "selected_breath_stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
            "breath_selected_source": str(getattr(args, "breath_selected_source", "auto") or "auto"),
            "broker_identity": broker_identity(args),
            "command": command,
        }
        out.write_text(json.dumps(started, indent=2, sort_keys=True), encoding="utf-8")
        return 0
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
    evidence = attach_broker_identity(json.loads(out.read_text(encoding="utf-8")), args)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
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
        "0" if getattr(args, "run_until_stopped", False) else str(int(max(0.0, args.duration_seconds) * 1000.0)),
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
        "breath_selected_source",
        str(getattr(args, "breath_selected_source", "auto") or "auto"),
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
        run([args.adb, "-s", args.serial, "shell", "am", "start", "-n", selected_broker_activity(args)])
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
    evidence = attach_broker_identity(json.loads(out.read_text(encoding="utf-8")), args)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
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
        broker_identity_record=broker_identity(args),
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
            (PMB_BREATH_VOLUME_STREAM, "breath_volume"),
            (PMB_BREATH_VOLUME_SELECTED_STREAM, "breath_volume_selected"),
            (PMB_BREATH_VOLUME_POLAR_STREAM, "breath_volume_polar"),
            (PMB_BREATH_VOLUME_CONTROLLER_STREAM, "breath_volume_controller"),
            (PMB_BREATH_SELECTION_STATE_STREAM, "breath_selection_state"),
            (PMB_BREATH_FEEDBACK_STATE_STREAM, "breath_feedback_state"),
            (PMB_BREATH_FEEDBACK_RECEIPT_STREAM, "breath_feedback_receipt"),
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
                adb_prefix(args) + ["shell", "am", "start", "-n", selected_broker_activity(args)],
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
            for stream_id in [
                PMB_BREATH_VOLUME_STREAM,
                PMB_BREATH_VOLUME_SELECTED_STREAM,
                PMB_BREATH_VOLUME_POLAR_STREAM,
                PMB_BREATH_VOLUME_CONTROLLER_STREAM,
                PMB_BREATH_SELECTION_STATE_STREAM,
                PMB_BREATH_FEEDBACK_STATE_STREAM,
                PMB_BREATH_FEEDBACK_RECEIPT_STREAM,
            ]:
                send_broker_command("subscribe", {"stream": stream_id})
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
            key = "debug.rusty.manifold.pose.publish.enabled"
            run_adb(
                f"disable-makepad-pose-publish-{key}",
                adb_prefix(args) + ["shell", "setprop", key, "false"],
                allow_failure=True,
            )
        if makepad_breath_feedback_enabled:
            for key in [
                "debug.rusty.manifold.breath.feedback.enabled",
                "debug.rustyquest.makepad.projection.target.breath.controls",
            ]:
                run_adb(
                    f"disable-makepad-breath-feedback-subscriber-{key}",
                    adb_prefix(args) + ["shell", "setprop", key, "off" if key.endswith(".controls") else "false"],
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
    pmb_selected_breath_publish_count = int(pmb_publish.get("selected_breath_published_count") or 0)
    pmb_feedback_publish_count = int(pmb_publish.get("feedback_published_count") or 0)
    pmb_receipt_count = int(
        stream_rows.get(PMB_BREATH_FEEDBACK_RECEIPT_STREAM, {}).get("event_count") or 0
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
            "broker_identity": broker_identity(args),
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
        "pmb_selected_breath_published": pmb_selected_breath_publish_count > 0,
        "pmb_selected_breath_publish_count": pmb_selected_breath_publish_count,
        "pmb_breath_selected_source_preference": pmb_publish.get("selected_source_preference"),
        "pmb_breath_selected_source_effective": pmb_publish.get("selected_source_effective"),
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
    setprops = {
        **makepad_visual_profile_runtime_properties(),
        "debug.rusty.manifold.pose.publish.enabled": "true",
        "debug.rusty.manifold.pose.stream": "stream.motion.object_pose",
        "debug.rusty.manifold.pose.source": "provider.makepad.controller_pose",
        "debug.rusty.manifold.pose.controller": args.makepad_pose_controller,
        "debug.rusty.manifold.pose.kind": args.makepad_pose_kind,
        "debug.rusty.manifold.pose.sample.hz": str(args.makepad_pose_sample_hz),
        "debug.rusty.manifold.broker.host": "127.0.0.1",
        "debug.rusty.manifold.broker.port": str(args.broker_port),
        "debug.rustyquest.makepad.projection.target.joystick.controls": "offset-scale",
    }
    if enable_breath_feedback:
        setprops.update({
            "debug.rusty.manifold.breath.feedback.enabled": "true",
            "debug.rusty.manifold.breath.feedback.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
            "debug.rusty.manifold.breath.feedback.receiver": "app.makepad_camera_shell.breath_feedback",
            "debug.rusty.manifold.breath.feedback.connect.timeout.ms": "5000",
            "debug.rustyquest.makepad.projection.target.breath.controls": "scale",
            "debug.rustyquest.makepad.projection.target.breath.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
            "debug.rustyquest.makepad.projection.target.breath.min.scale": PMB_BREATH_SCALE_VOLUME0,
            "debug.rustyquest.makepad.projection.target.breath.max.scale": PMB_BREATH_SCALE_VOLUME1,
            "debug.rustyquest.makepad.projection.target.breath.smoothing.alpha": PMB_BREATH_SCALE_SMOOTHING_ALPHA,
            "debug.rustyquest.makepad.projection.target.breath.invert": "false",
            "debug.rustyquest.makepad.projection.target.breath.min.quality": "0.0",
        })
    else:
        setprops.update({
            "debug.rusty.manifold.breath.feedback.enabled": "false",
            "debug.rustyquest.makepad.projection.target.breath.controls": "off",
        })
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
    setprops = {
        **makepad_visual_profile_runtime_properties(),
        "debug.rusty.manifold.pose.publish.enabled": "false",
        "debug.rusty.manifold.broker.host": "127.0.0.1",
        "debug.rusty.manifold.broker.port": str(args.broker_port),
        "debug.rusty.manifold.breath.feedback.enabled": "true",
        "debug.rusty.manifold.breath.feedback.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
        "debug.rusty.manifold.breath.feedback.receiver": "app.makepad_camera_shell.breath_feedback",
        "debug.rusty.manifold.breath.feedback.connect.timeout.ms": "5000",
        "debug.rustyquest.makepad.projection.target.breath.controls": "scale",
        "debug.rustyquest.makepad.projection.target.breath.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
        "debug.rustyquest.makepad.projection.target.breath.min.scale": PMB_BREATH_SCALE_VOLUME0,
        "debug.rustyquest.makepad.projection.target.breath.max.scale": PMB_BREATH_SCALE_VOLUME1,
        "debug.rustyquest.makepad.projection.target.breath.smoothing.alpha": PMB_BREATH_SCALE_SMOOTHING_ALPHA,
        "debug.rustyquest.makepad.projection.target.breath.invert": "false",
        "debug.rustyquest.makepad.projection.target.breath.min.quality": "0.0",
        "debug.rustyquest.makepad.projection.target.joystick.controls": "offset-scale",
    }
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
    setprops = {
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
        "debug.rusty.manifold.breath.feedback.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
        "debug.rusty.manifold.breath.feedback.receiver": "app.makepad_camera_shell.breath_feedback",
        "debug.rusty.manifold.breath.feedback.connect.timeout.ms": "5000",
        "debug.rustyquest.makepad.projection.target.breath.controls": "scale",
        "debug.rustyquest.makepad.projection.target.breath.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
        "debug.rustyquest.makepad.projection.target.breath.min.scale": PMB_BREATH_SCALE_VOLUME0,
        "debug.rustyquest.makepad.projection.target.breath.max.scale": PMB_BREATH_SCALE_VOLUME1,
        "debug.rustyquest.makepad.projection.target.breath.smoothing.alpha": PMB_BREATH_SCALE_SMOOTHING_ALPHA,
        "debug.rustyquest.makepad.projection.target.breath.invert": "false",
        "debug.rustyquest.makepad.projection.target.breath.min.quality": "0.0",
        "debug.rustyquest.makepad.projection.target.joystick.controls": "offset-scale",
    }
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
            [args.adb, "-s", args.serial, "shell", "pm", "grant", selected_broker_package(args), permission],
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
    selected_source_preference = str(getattr(args, "pmb_breath_selected_source", "auto") or "auto")
    selected_breath_samples, selected_source_effective = select_pmb_selected_breath_samples(
        breath_samples,
        selected_source_preference,
        limit,
    )
    feedback_samples = select_pmb_output_samples(route_report.get("feedback_samples", []), limit)
    breath_results: list[dict[str, Any]] = []
    for index, sample in enumerate(breath_samples):
        sequence_id = int(sample.get("sequence_id") or index + 1)
        breath_results.append(
            publish_pmb_stream_sample(
                send_broker_command,
                stream_id=PMB_BREATH_VOLUME_STREAM,
                sequence_id=sequence_id,
                payload=pmb_breath_payload(sample, sequence_id, PMB_BREATH_VOLUME_STREAM),
            )
        )
        source_stream_id = pmb_breath_source_stream_id(sample)
        if source_stream_id is not None:
            breath_results.append(
                publish_pmb_stream_sample(
                    send_broker_command,
                    stream_id=source_stream_id,
                    sequence_id=sequence_id,
                    payload=pmb_breath_payload(sample, sequence_id, source_stream_id),
                )
            )
    selected_breath_results = [
        publish_pmb_stream_sample(
            send_broker_command,
            stream_id=PMB_BREATH_VOLUME_SELECTED_STREAM,
            sequence_id=int(sample.get("sequence_id") or index + 1),
            payload=pmb_breath_payload(
                sample,
                int(sample.get("sequence_id") or index + 1),
                PMB_BREATH_VOLUME_SELECTED_STREAM,
                selected=True,
                selected_source_preference=selected_source_preference,
                selected_source_effective=selected_source_effective,
            ),
        )
        for index, sample in enumerate(selected_breath_samples)
    ]
    breath_results.extend(selected_breath_results)
    selection_state_results: list[dict[str, Any]] = []
    if limit > 0:
        selection_state_results.append(
            publish_pmb_stream_sample(
                send_broker_command,
                stream_id=PMB_BREATH_SELECTION_STATE_STREAM,
                sequence_id=1,
                payload={
                    "schema": "rusty.manifold.breath.selection_state.v1",
                    "stream_id": PMB_BREATH_SELECTION_STATE_STREAM,
                    "sequence_id": 1,
                    "selected_stream_id": PMB_BREATH_VOLUME_SELECTED_STREAM,
                    "selected_source_preference": selected_source_preference,
                    "selected_source_effective": selected_source_effective,
                    "source_stream_ids": [
                        PMB_BREATH_VOLUME_POLAR_STREAM,
                        PMB_BREATH_VOLUME_CONTROLLER_STREAM,
                    ],
                    "selected_sample_count": len(selected_breath_samples),
                    "publisher": "hostessctl.record_values",
                },
            )
        )
    breath_results.extend(selection_state_results)
    feedback_results = [
        publish_pmb_stream_sample(
            send_broker_command,
            stream_id=PMB_BREATH_FEEDBACK_STATE_STREAM,
            sequence_id=int(sample.get("sequence_id") or index + 1),
            payload={
                "schema": "rusty.manifold.breath.feedback_state.v1",
                "stream_id": PMB_BREATH_FEEDBACK_STATE_STREAM,
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
        "selected_source_preference": selected_source_preference,
        "selected_source_effective": selected_source_effective,
        "breath_requested_count": len(route_report.get("breath_samples", [])),
        "feedback_requested_count": len(route_report.get("feedback_samples", [])),
        "breath_published_count": sum(
            1
            for result in breath_results
            if result.get("stream_id") == PMB_BREATH_VOLUME_STREAM and result.get("status") == "pass"
        ),
        "selected_breath_published_count": sum(
            1
            for result in selected_breath_results
            if result.get("status") == "pass"
        ),
        "selection_state_published_count": sum(
            1
            for result in selection_state_results
            if result.get("status") == "pass"
        ),
        "feedback_published_count": sum(1 for result in feedback_results if result.get("status") == "pass"),
        "published_count": sum(1 for result in breath_results + feedback_results if result.get("status") == "pass"),
        "published": any(result.get("status") == "pass" for result in breath_results + feedback_results),
        "breath_results": breath_results,
        "selected_breath_results": selected_breath_results,
        "feedback_results": feedback_results,
    }


def pmb_breath_payload(
    sample: dict[str, Any],
    sequence_id: int,
    stream_id: str,
    *,
    selected: bool = False,
    selected_source_preference: str = "auto",
    selected_source_effective: str = "auto",
) -> dict[str, Any]:
    payload = {
        "schema": "rusty.manifold.breath.volume.v1",
        "stream_id": stream_id,
        "sequence_id": sequence_id,
        "source_id": sample.get("source_id"),
        "source_kind": pmb_breath_source_kind(sample),
        "input_stream_id": sample.get("input_stream_id"),
        "normalized_stream_id": sample.get("normalized_stream_id"),
        "sample_time_unix_ns": sample_time_unix_ns_from_sample(sample),
        "volume01": sample.get("volume01"),
        "phase": sample.get("phase"),
        "quality": sample.get("quality"),
        "quality01": sample.get("quality01", sample.get("tracking01", 1.0)),
        "tracking01": sample.get("tracking01"),
        "processor_id": "processor.projected_motion_breath.live_bridge",
        "publisher": "hostessctl.record_values",
    }
    if selected:
        payload.update(
            {
                "selected": True,
                "selected_source_preference": selected_source_preference,
                "selected_source_effective": selected_source_effective,
            }
        )
    return payload


def pmb_breath_source_kind(sample: dict[str, Any]) -> str:
    text = " ".join(
        str(sample.get(key) or "")
        for key in ("source_id", "input_stream_id", "normalized_stream_id")
    ).lower()
    if "polar" in text or "bio:polar" in text:
        return "polar"
    if "controller" in text or "object_pose" in text or "motion.object" in text:
        return "controller"
    return "unknown"


def pmb_breath_source_stream_id(sample: dict[str, Any]) -> str | None:
    source_kind = pmb_breath_source_kind(sample)
    if source_kind == "polar":
        return PMB_BREATH_VOLUME_POLAR_STREAM
    if source_kind == "controller":
        return PMB_BREATH_VOLUME_CONTROLLER_STREAM
    return None


def select_pmb_selected_breath_samples(
    breath_samples: list[dict[str, Any]],
    selected_source_preference: str,
    limit: int,
) -> tuple[list[dict[str, Any]], str]:
    if limit <= 0:
        return [], selected_source_preference
    source_kinds = [pmb_breath_source_kind(sample) for sample in breath_samples]
    effective = selected_source_preference
    if selected_source_preference == "auto":
        if "polar" in source_kinds:
            effective = "polar"
        elif "controller" in source_kinds:
            effective = "controller"
        else:
            effective = "unknown"
    selected = [
        sample
        for sample in breath_samples
        if effective == "unknown" or pmb_breath_source_kind(sample) == effective
    ]
    return selected[:limit], effective


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




def redact_command(command: list[str]) -> list[str]:
    redacted = list(command)
    for index, token in enumerate(redacted[:-1]):
        if token in {"--device-address"}:
            redacted[index + 1] = "<redacted>"
    return redacted












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
    clear_android_files(args, [ANDROID_REMOTE_EVIDENCE, ANDROID_REMOTE_RUNTIME_INPUT, ANDROID_REMOTE_GRAPH_REPORT])


def clear_android_pmb_artifacts(args: argparse.Namespace) -> None:
    clear_android_files(args, [ANDROID_REMOTE_PMB_EVIDENCE, ANDROID_REMOTE_PMB_CORE_REPORT])


def clear_android_pmb_controller_preflight_artifacts(args: argparse.Namespace) -> None:
    clear_android_files(
        args,
        [
            ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE,
            ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_REPORT,
        ],
    )


def clear_android_pmb_simulated_live_artifacts(args: argparse.Namespace) -> None:
    clear_android_files(
        args,
        [
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE,
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_ROUTE_REPORT,
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_BROKER_REPORT,
        ],
    )


def clear_android_pmb_physical_live_artifacts(args: argparse.Namespace) -> None:
    clear_android_files(
        args,
        [
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE,
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_CAPTURE_REPORT,
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVENTS_JSONL,
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_ROUTE_REPORT,
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_BROKER_REPORT,
        ],
    )


def clear_android_broker_telemetry_artifacts(args: argparse.Namespace) -> None:
    clear_android_files(
        args,
        [
            ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE,
            ANDROID_REMOTE_BROKER_TELEMETRY_REPORT,
        ],
    )


def clear_android_files(args: argparse.Namespace, remote_paths: list[str]) -> None:
    android_files.clear_android_files(args, remote_paths, run=run)


def wait_for_android_evidence(args: argparse.Namespace, timeout_seconds: float) -> None:
    wait_for_android_file(args, ANDROID_REMOTE_EVIDENCE, timeout_seconds)


def wait_for_android_file(args: argparse.Namespace, remote_path: str, timeout_seconds: float) -> None:
    android_files.wait_for_android_file(args, remote_path, timeout_seconds, run=run)


def wait_for_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    timeout_seconds: float,
) -> None:
    android_files.wait_for_android_run_as_file(
        args,
        package,
        relative_path,
        timeout_seconds,
        run=run,
    )


def pull_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    out: Path,
) -> None:
    android_files.pull_android_run_as_file(args, package, relative_path, out)


def write_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    payload: bytes,
) -> None:
    android_files.write_android_run_as_file(args, package, relative_path, payload)


def android_shell_quote(value: str) -> str:
    return android_files.android_shell_quote(value)


def read_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
) -> bytes:
    return android_files.read_android_run_as_file(args, package, relative_path)


def wait_for_makepad_render_sidecar(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    timeout_seconds: float,
    *,
    target: str,
    min_events: int,
) -> None:
    android_files.wait_for_makepad_render_sidecar(
        args,
        package,
        relative_path,
        timeout_seconds,
        target=target,
        min_events=min_events,
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
