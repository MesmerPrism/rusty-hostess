"""Native Rusty Quest Breathing Room setup receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from tools.hostessctl.runtime import REPO_ROOT
from tools.hostessctl.pmb_support import (
    PMB_BREATH_STATE_STREAM,
    PMB_BREATH_STATE_VALUE_STREAM,
    PMB_CONTROLLER_STATE_EXHALE_THRESHOLD,
    PMB_CONTROLLER_STATE_INHALE_THRESHOLD,
    PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS,
    PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD,
    PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES,
    PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS,
    PMB_STREAM_CONTRACT_AUTHORITY,
)

NATIVE_RENDERER_PREFIX = "debug.rustyquest.native_renderer."
BREATH_STATE_STREAM = PMB_BREATH_STATE_STREAM
BREATH_STATE_VALUE_STREAM = PMB_BREATH_STATE_VALUE_STREAM
NATIVE_BREATHING_ROOM_PROFILE_ID = "profile.quest.native_renderer.breathing_room_pmb_scale"
NATIVE_BREATHING_ROOM_PROFILE_FILE = "quest-native-renderer-breathing-room-pmb-scale.profile.json"
NATIVE_BREATHING_ROOM_PROFILE_ENV = "RUSTY_QUEST_NATIVE_BREATHING_ROOM_PROFILE"
NATIVE_BREATHING_ROOM_PARAMETERIZED_PROPERTIES = (
    "debug.rustyquest.native_renderer.projection.target.controls",
    "debug.rustyquest.native_renderer.projection.target.scale",
    "debug.rustyquest.native_renderer.projection.target.tuned.max.scale",
    "debug.rustyquest.native_renderer.projection.target.min.scale",
    "debug.rustyquest.native_renderer.projection.target.max.scale",
    "debug.rustyquest.native_renderer.projection.target.offset.x.uv",
    "debug.rustyquest.native_renderer.projection.target.offset.y.uv",
    "debug.rustyquest.native_renderer.projection.target.joystick.controls",
    "debug.rustyquest.native_renderer.projection.target.joystick.scale.rate_per_second",
    "debug.rustyquest.native_renderer.projection.target.breath.bridge.mode",
    "debug.rustyquest.native_renderer.projection.target.breath.state.stream",
    "debug.rustyquest.native_renderer.projection.target.breath.value.stream",
    "debug.rustyquest.native_renderer.projection.target.breath.inhale.seconds.min_to_max",
    "debug.rustyquest.native_renderer.projection.target.breath.exhale.seconds.max_to_min",
    "debug.rustyquest.native_renderer.projection.target.breath.synthetic.period.seconds",
    "debug.rustyquest.native_renderer.projection.target.breath.high_rate_json_payload",
    "debug.rustyquest.native_renderer.manifold.broker.host",
    "debug.rustyquest.native_renderer.manifold.broker.port",
    "debug.rustyquest.native_renderer.manifold.broker.path",
)


def default_native_breathing_room_profile_path() -> Path:
    return (
        REPO_ROOT.parent
        / "rusty-quest"
        / "fixtures"
        / "runtime-profiles"
        / NATIVE_BREATHING_ROOM_PROFILE_FILE
    )


def resolve_native_breathing_room_profile_path(args: argparse.Namespace) -> Path:
    explicit = getattr(args, "runtime_profile", None)
    if explicit:
        return Path(explicit)
    env_path = os.environ.get(NATIVE_BREATHING_ROOM_PROFILE_ENV)
    if env_path:
        return Path(env_path)
    return default_native_breathing_room_profile_path()


def load_native_breathing_room_profile_property_records(profile_path: Path) -> list[dict[str, str]]:
    if not profile_path.exists():
        raise FileNotFoundError(
            f"Native Breathing Room setup requires the Rusty Quest runtime profile: {profile_path}"
        )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("schema") != "rusty.quest.runtime_profile.v1":
        raise ValueError("native Breathing Room setup requires a rusty.quest.runtime_profile.v1 profile")
    if profile.get("profile_id") != NATIVE_BREATHING_ROOM_PROFILE_ID:
        raise ValueError(
            f"native Breathing Room setup expected {NATIVE_BREATHING_ROOM_PROFILE_ID}"
        )
    owned_properties = [str(name) for name in profile.get("owned_android_properties", [])]
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in profile.get("set_properties", []):
        name = str(item.get("name", ""))
        if not name:
            raise ValueError("native Breathing Room profile contains a property with no name")
        if name in seen:
            raise ValueError(f"native Breathing Room profile repeats property {name}")
        seen.add(name)
        record = {"name": name, "value": str(item.get("value", ""))}
        source_setting_id = item.get("source_setting_id")
        if source_setting_id is not None:
            record["source_setting_id"] = str(source_setting_id)
        records.append(record)
    owned_set = set(owned_properties)
    record_set = {record["name"] for record in records}
    missing_owned_properties = sorted(owned_set - record_set)
    extra_set_properties = sorted(record_set - owned_set)
    if missing_owned_properties:
        raise ValueError(
            "native Breathing Room profile does not set all owned properties: "
            + ", ".join(missing_owned_properties)
        )
    if extra_set_properties:
        raise ValueError(
            "native Breathing Room profile sets properties it does not own: "
            + ", ".join(extra_set_properties)
        )
    if any(not record["name"].startswith(NATIVE_RENDERER_PREFIX) for record in records):
        raise ValueError("native Breathing Room profile may only emit native_renderer properties")
    return records


def native_breathing_room_profile_sha256(profile_path: Path) -> str:
    if not profile_path.exists():
        raise FileNotFoundError(
            f"Native Breathing Room setup requires the Rusty Quest runtime profile: {profile_path}"
        )
    return hashlib.sha256(profile_path.read_bytes()).hexdigest()


def validate_native_breathing_room_stream_contract(args: argparse.Namespace) -> None:
    state_stream = str(args.state_stream)
    value_stream = str(args.value_stream)
    if state_stream != PMB_BREATH_STATE_STREAM or value_stream != PMB_BREATH_STATE_VALUE_STREAM:
        raise ValueError(
            "native Breathing Room setup currently requires the canonical PMB stream "
            f"contract {PMB_BREATH_STATE_STREAM} / {PMB_BREATH_STATE_VALUE_STREAM}; "
            "custom stream ids would also need coordinated publisher and native "
            "receipt-policy support"
        )


def native_breathing_room_runtime_properties(args: argparse.Namespace) -> dict[str, str]:
    return {
        record["name"]: record["value"]
        for record in native_breathing_room_runtime_property_records(args)
    }


def native_breathing_room_runtime_property_records(
    args: argparse.Namespace,
) -> list[dict[str, str]]:
    validate_native_breathing_room_stream_contract(args)
    mode = str(args.mode)
    bridge_mode = {
        "pmb-controller-state": "manifold-state",
        "pmb-state": "manifold-state",
        "pmb-state-value": "manifold-state-value",
        "synthetic": "synthetic",
    }[mode]
    profile_path = resolve_native_breathing_room_profile_path(args)
    records = load_native_breathing_room_profile_property_records(profile_path)
    by_name = {record["name"]: dict(record) for record in records}
    overrides = {
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
    if set(overrides) != set(NATIVE_BREATHING_ROOM_PARAMETERIZED_PROPERTIES):
        raise ValueError("native Breathing Room parameterized property list is out of sync")
    missing_overrides = sorted(set(overrides) - set(by_name))
    if missing_overrides:
        raise ValueError(
            "native Breathing Room profile is missing parameterized properties: "
            + ", ".join(missing_overrides)
        )
    for name, value in overrides.items():
        by_name[name]["value"] = value
    return [by_name[record["name"]] for record in records]


def build_native_breathing_room_setup_receipt(args: argparse.Namespace) -> dict[str, Any]:
    profile_path = resolve_native_breathing_room_profile_path(args)
    property_records = native_breathing_room_runtime_property_records(args)
    setprops = {record["name"]: record["value"] for record in property_records}
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
        "profile_id": NATIVE_BREATHING_ROOM_PROFILE_ID,
        "runtime_profile_file": profile_path.name,
        "runtime_profile_sha256": native_breathing_room_profile_sha256(profile_path),
        "runtime_profile_authority": "rusty-quest-runtime-profile",
        "runtime_profile_property_count": len(property_records),
        "runtime_profile_parameterized_properties": list(
            NATIVE_BREATHING_ROOM_PARAMETERIZED_PROPERTIES
        ),
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
        "pmb_stream_contract_authority": PMB_STREAM_CONTRACT_AUTHORITY,
        "native_app_receipt_policy_streams": {
            "app_receipt_policy": "native-renderer-projection-target",
            "state_stream": PMB_BREATH_STATE_STREAM,
            "state_value_stream": PMB_BREATH_STATE_VALUE_STREAM,
            "publisher": "hostess-pmb-broker-bridge",
            "consumer": "rusty-quest-native-renderer",
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
        "set_properties": property_records,
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
