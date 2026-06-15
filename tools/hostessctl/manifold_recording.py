"""Manifold value recording routes and broker stream capture helpers."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.broker_transport import (
    MANIFOLD_BROKER_EVENTS_PATH,
    BrokerWebSocketClient,
    accept_broker_stream_event,
    broker_ack_accepted,
    broker_command_message,
    connect_broker_websocket_with_retry,
)
from tools.hostessctl.makepad_visual_profile import (
    makepad_visual_profile_runtime_properties,
)
from tools.hostessctl.makepad_pmb_setup import makepad_breath_scale_runtime_properties
from tools.hostessctl.pmb_broker_bridge import (
    listen_for_pmb_receipts,
    publish_pmb_feedback_samples,
)
from tools.hostessctl.pmb_evidence import (
    PMB_BREATH_FEEDBACK_RECEIPT_STREAM,
    PMB_BREATH_FEEDBACK_STATE_STREAM,
    PMB_BREATH_SELECTION_STATE_STREAM,
    PMB_BREATH_STATE_STREAM,
    PMB_BREATH_STATE_VALUE_STREAM,
    PMB_BREATH_VOLUME_CONTROLLER_STREAM,
    PMB_BREATH_VOLUME_POLAR_STREAM,
    PMB_BREATH_VOLUME_SELECTED_STREAM,
    PMB_BREATH_VOLUME_STREAM,
    parse_pmb_core_report,
    projected_motion_breath_package_root,
)
from tools.hostessctl.recording_evidence import (
    build_manifold_value_recording_evidence,
    recording_segment,
    validate_broker_websocket_stream_recording_evidence,
    validate_manifold_value_recording_evidence,
    write_manifold_value_recording_host_run_evidence,
)

RunCaptured = Callable[..., subprocess.CompletedProcess[str]]
RunLiveCapture = Callable[[argparse.Namespace], int]
RecordBrokerStreams = Callable[[argparse.Namespace, list[dict[str, Any]], Path], int]
SelectedBrokerActivity = Callable[[argparse.Namespace], str]
BrokerIdentity = Callable[[argparse.Namespace], dict[str, Any]]


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
    "breath.state": "stream.breath.state",
    "breath.state.value": "stream.breath.state.value",
    "breath.dynamics": "stream.breath.dynamics",
    "breath.feedback_state": "stream.breath.feedback_state",
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
    "stream.breath.state": {
        "value_id": "value.breath.state",
        "stream_id": "stream.breath.state",
        "provider_id": "processor.projected_motion_breath.state_classifier",
        "provider_kind": "processor_output",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "breath_state",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": True,
        "blocked_reason": "raw breath-state recording requires a bound PMB input provider",
    },
    "stream.breath.state.value": {
        "value_id": "value.breath.state.value",
        "stream_id": "stream.breath.state.value",
        "provider_id": "processor.projected_motion_breath.state_value",
        "provider_kind": "processor_output",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "breath_state_value",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": True,
        "blocked_reason": "processed breath-state value recording requires a bound PMB input provider",
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


def run_manifold_value_recording(
    args: argparse.Namespace,
    *,
    run_live_capture_func: RunLiveCapture,
    record_broker_streams_func: RecordBrokerStreams,
    broker_identity_func: BrokerIdentity,
) -> int:
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
            capture_status = record_broker_streams_func(args, provider_plans, capture_evidence_path)
        else:
            plan = provider_plans[0]
            capture_evidence_path = out.with_name(
                f"{out.stem}.{recording_segment([plan['stream_id']])}.live-capture.json"
            )
            capture_status = run_live_capture_func(
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
        broker_identity_record=broker_identity_func(args),
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


def pmb_live_processor_inputs_ready(provider_plans: list[dict[str, Any]]) -> bool:
    stream_ids = {str(plan.get("stream_id")) for plan in provider_plans}
    return {
        "stream.polar_h10.acc",
        "stream.motion.object_pose",
    }.issubset(stream_ids)


def record_broker_websocket_streams(
    args: argparse.Namespace,
    provider_plans: list[dict[str, Any]],
    out: Path,
    *,
    run_captured_func: RunCaptured,
    selected_broker_activity_func: SelectedBrokerActivity,
    broker_identity_func: BrokerIdentity,
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
    pmb_bridge_enabled = bool(getattr(args, "pmb_live_processor", False)) and pmb_live_processor_inputs_ready(
        provider_plans
    )
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
            (PMB_BREATH_STATE_STREAM, "breath_state"),
            (PMB_BREATH_STATE_VALUE_STREAM, "breath_state_value"),
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
        result = run_captured_func(command, allow_failure=True)
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
                adb_prefix(args) + ["shell", "am", "start", "-n", selected_broker_activity_func(args)],
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
                PMB_BREATH_STATE_STREAM,
                PMB_BREATH_STATE_VALUE_STREAM,
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
            pmb_bridge = run_pmb_live_processor_bridge(
                args,
                events_jsonl,
                out,
                run_captured_func=run_captured_func,
            )
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
        run_adb(
            "adb-forward-remove-broker-websocket",
            adb_prefix(args) + ["forward", "--remove", forward_spec],
            allow_failure=True,
        )

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
    pmb_state_publish_count = int(pmb_publish.get("state_published_count") or 0)
    pmb_state_value_publish_count = int(pmb_publish.get("state_value_published_count") or 0)
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
            "broker_identity": broker_identity_func(args),
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
        "pmb_breath_state_published": pmb_state_publish_count > 0,
        "pmb_breath_state_publish_count": pmb_state_publish_count,
        "pmb_breath_state_value_published": pmb_state_value_publish_count > 0,
        "pmb_breath_state_value_publish_count": pmb_state_value_publish_count,
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
            **makepad_breath_scale_runtime_properties(args),
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
    *,
    run_captured_func: RunCaptured,
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
    core_run = run_captured_func(command, allow_failure=True, cwd=packages_root)
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


def redact_command(command: list[str]) -> list[str]:
    redacted = list(command)
    for index, token in enumerate(redacted[:-1]):
        if token in {"--device-address"}:
            redacted[index + 1] = "<redacted>"
    return redacted
