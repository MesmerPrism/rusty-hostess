"""Broker telemetry observer route implementation for hostessctl."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from tools.hostessctl.platform_defaults import (
    ANDROID_BROKER_TELEMETRY_ACTION,
    ANDROID_PACKAGE,
    ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE,
    ANDROID_REMOTE_BROKER_TELEMETRY_REPORT,
)
from tools.hostessctl.recording_evidence import validate_broker_telemetry_observer_evidence


RunFunc = Callable[..., Any]


def observe_broker_telemetry_ui(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    grant_broker_runtime_permissions_func: Callable[[argparse.Namespace], None],
    clear_android_broker_telemetry_artifacts_func: Callable[[argparse.Namespace], None],
    wait_for_android_file_func: Callable[[argparse.Namespace, str, float], None],
    selected_broker_activity_func: Callable[[argparse.Namespace], str],
    attach_broker_identity_func: Callable[[dict[str, Any], argparse.Namespace], dict[str, Any]],
    render_telemetry_func: Callable[[argparse.Namespace], int],
) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.duration_seconds <= 0:
        raise SystemExit("--duration-seconds must be greater than zero")
    if not getattr(args, "no_launch_broker", False):
        grant_broker_runtime_permissions_func(args)
        run_func([args.adb, "-s", args.serial, "shell", "am", "start", "-n", selected_broker_activity_func(args)])
    clear_android_broker_telemetry_artifacts_func(args)
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
    run_func(command)
    wait_seconds = (
        max(0.0, float(args.duration_seconds))
        + (0.0 if args.no_request_provider_start else max(0.0, float(args.scan_timeout_seconds)))
        + 20.0
    )
    wait_for_android_file_func(args, ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE, wait_seconds)
    run_func([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE, str(out)])
    report_path = out.with_name(f"{out.stem}.broker-telemetry-report.json")
    run_func([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_BROKER_TELEMETRY_REPORT, str(report_path)])
    evidence = attach_broker_identity_func(json.loads(out.read_text(encoding="utf-8")), args)
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
        render_telemetry_func(render_args)
    return 0 if validation_report["status"] == "pass" else 2
