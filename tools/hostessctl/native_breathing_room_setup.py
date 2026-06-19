"""Native Rusty Quest Breathing Room setup receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.hostessctl.pmb_support import (
    PMB_CONTROLLER_STATE_EXHALE_THRESHOLD,
    PMB_CONTROLLER_STATE_INHALE_THRESHOLD,
    PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS,
    PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD,
    PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES,
    PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS,
)

NATIVE_RENDERER_PREFIX = "debug.rustyquest.native_renderer."
BREATH_STATE_STREAM = "stream.breath.state"
BREATH_STATE_VALUE_STREAM = "stream.breath.state.value"


def native_breathing_room_runtime_properties(args: argparse.Namespace) -> dict[str, str]:
    mode = str(args.mode)
    bridge_mode = {
        "pmb-controller-state": "manifold-state",
        "pmb-state": "manifold-state",
        "pmb-state-value": "manifold-state-value",
        "synthetic": "synthetic",
    }[mode]
    return {
        "debug.rustyquest.native_renderer.render.mode": "custom-stereo-projection",
        "debug.rustyquest.native_renderer.replay.visual_proof.enabled": "false",
        "debug.rustyquest.native_renderer.hand_mesh.input.source": "auto",
        "debug.rustyquest.native_renderer.hand_mesh.visual.diagnostic.enabled": "false",
        "debug.rustyquest.native_renderer.hand_mesh.graft_copies.enabled": "false",
        "debug.rustyquest.native_renderer.sdf.visual.enabled": "false",
        "debug.rustyquest.native_renderer.processing.layer": "peripheral-stretch",
        "debug.rustyquest.native_renderer.projection.border.policy": "passthrough-underlay",
        "debug.rustyquest.native_renderer.projection.border.opacity": "0.0",
        "debug.rustyquest.native_renderer.projection.area.opacity": "1.0",
        "debug.rustyquest.native_renderer.peripheral.stretch.core.scale": "1.0",
        "debug.rustyquest.native_renderer.peripheral.stretch.edge.inset.uv": "0.015",
        "debug.rustyquest.native_renderer.peripheral.stretch.max.inset.uv": "0.14",
        "debug.rustyquest.native_renderer.peripheral.stretch.curve": "1.6",
        "debug.rustyquest.native_renderer.peripheral.stretch.inner.blend.uv": "0.040",
        "debug.rustyquest.native_renderer.peripheral.stretch.blend.curve": "1.6",
        "debug.rustyquest.native_renderer.peripheral.stretch.blend.mode": "target-inner-band",
        "debug.rustyquest.native_renderer.peripheral.stretch.debug": "off",
        "debug.rustyquest.native_renderer.projection.target.controls": "true",
        "debug.rustyquest.native_renderer.projection.target.scale": f"{float(args.base_scale):.3f}",
        "debug.rustyquest.native_renderer.projection.target.tuned.max.scale": f"{float(args.tuned_max_scale):.3f}",
        "debug.rustyquest.native_renderer.projection.target.min.scale": "0.05",
        "debug.rustyquest.native_renderer.projection.target.max.scale": "5.0",
        "debug.rustyquest.native_renderer.projection.target.offset.x.uv": "0.0",
        "debug.rustyquest.native_renderer.projection.target.offset.y.uv": "0.0",
        "debug.rustyquest.native_renderer.projection.target.joystick.controls": "true",
        "debug.rustyquest.native_renderer.projection.target.joystick.scale.rate_per_second": f"{float(args.joystick_rate):.3f}",
        "debug.rustyquest.native_renderer.projection.target.breath.bridge.mode": bridge_mode,
        "debug.rustyquest.native_renderer.projection.target.breath.state.stream": str(args.state_stream),
        "debug.rustyquest.native_renderer.projection.target.breath.value.stream": str(args.value_stream),
        "debug.rustyquest.native_renderer.projection.target.breath.inhale.seconds.min_to_max": f"{float(args.inhale_seconds):.3f}",
        "debug.rustyquest.native_renderer.projection.target.breath.exhale.seconds.max_to_min": f"{float(args.exhale_seconds):.3f}",
        "debug.rustyquest.native_renderer.projection.target.breath.synthetic.period.seconds": f"{float(args.synthetic_period_seconds):.3f}",
        "debug.rustyquest.native_renderer.projection.target.breath.high_rate_json_payload": "false",
        "debug.rustyquest.native_renderer.manifold.broker.host": str(args.broker_host),
        "debug.rustyquest.native_renderer.manifold.broker.port": str(int(args.broker_port)),
        "debug.rustyquest.native_renderer.manifold.broker.path": str(args.broker_path),
    }


def build_native_breathing_room_setup_receipt(args: argparse.Namespace) -> dict[str, Any]:
    setprops = native_breathing_room_runtime_properties(args)
    if any(not key.startswith(NATIVE_RENDERER_PREFIX) for key in setprops):
        raise ValueError("native Breathing Room setup may only emit native_renderer properties")
    pmb_source = "controller" if args.mode == "pmb-controller-state" else str(args.breath_selected_source)
    state_subscription = {
        "command": "subscribe",
        "params": {"stream": str(args.state_stream)},
        "consumer": "rusty-quest-native-renderer",
    }
    value_subscription = {
        "command": "subscribe",
        "params": {"stream": str(args.value_stream)},
        "consumer": "rusty-quest-native-renderer",
    }
    subscriptions = []
    if args.mode in {"pmb-controller-state", "pmb-state"}:
        subscriptions.append(state_subscription)
    if args.mode == "pmb-state-value":
        subscriptions.append(value_subscription)
    return {
        "schema": "rusty.hostess.native_breathing_room.setup_receipt.v1",
        "profile_id": "profile.quest.native_renderer.breathing_room_pmb_scale",
        "mode": args.mode,
        "target": "quest-native-renderer",
        "property_namespace": NATIVE_RENDERER_PREFIX.rstrip("."),
        "makepad_property_count": 0,
        "polar_required": False,
        "controller_pmb_mode_polar_required": False,
        "runtime_authority": {
            "projection_target_state": "rusty-quest-native-renderer",
            "pmb_source_selection": "hostess-manifold",
            "pmb_calibration": "hostess-manifold",
            "startup_defaults": "rusty-quest-runtime-profile",
        },
        "high_rate_update_policy": {
            "android_properties": "startup-defaults-only",
            "pose_updates": "openxr-native-action-state",
            "breath_updates": "manifold-broker-websocket-stream-events",
        },
        "pmb": {
            "breath_selected_source": pmb_source,
            "state_stream": str(args.state_stream),
            "state_value_stream": str(args.value_stream),
            "subscriptions": subscriptions,
            "controller_state": {
                "mode": str(args.pmb_controller_state_mode),
                "short_window_seconds": float(args.pmb_controller_state_short_window_seconds),
                "long_window_seconds": float(args.pmb_controller_state_long_window_seconds),
                "inhale_threshold": float(args.pmb_controller_state_inhale_threshold),
                "exhale_threshold": float(args.pmb_controller_state_exhale_threshold),
                "rotation_guard_degrees": float(args.pmb_controller_state_rotation_guard_degrees),
                "moving_average_guard": float(args.pmb_controller_state_moving_average_guard),
            },
        },
        "set_properties": [
            {"name": key, "value": value} for key, value in sorted(setprops.items())
        ],
        "execute_requested": bool(getattr(args, "execute", False)),
    }


def run_native_breathing_room_setup(
    args: argparse.Namespace,
    *,
    run_func: Any,
) -> int:
    receipt = build_native_breathing_room_setup_receipt(args)
    if args.execute:
        if not args.adb or not args.serial:
            raise SystemExit("--execute requires --adb and --serial")
        for item in receipt["set_properties"]:
            run_func([args.adb, "-s", args.serial, "shell", "setprop", item["name"], item["value"]])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0
