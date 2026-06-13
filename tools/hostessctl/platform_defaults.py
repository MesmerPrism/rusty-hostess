"""Platform package names, routes, and broker identity helpers."""

from __future__ import annotations

import argparse
from typing import Any


ANDROID_PACKAGE = "io.github.mesmerprism.rustyhostess.t"
MANIFOLD_BROKER_PACKAGE = "io.github.mesmerprism.rustymanifold.broker"
MANIFOLD_BROKER_ACTIVITY = f"{MANIFOLD_BROKER_PACKAGE}/.BrokerStartActivity"
LEGACY_REFERENCE_BROKER_PACKAGE = "com.example.rustyxr.broker"
LEGACY_REFERENCE_BROKER_ACTIVITY = f"{LEGACY_REFERENCE_BROKER_PACKAGE}/.BrokerStartActivity"
BROKER_PACKAGE = MANIFOLD_BROKER_PACKAGE
BROKER_ACTIVITY = MANIFOLD_BROKER_ACTIVITY
BROKER_PORT = 8765
BROKER_LOCAL_FORWARD_PORT = 18765
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
