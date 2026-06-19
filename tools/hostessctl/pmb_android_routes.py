"""Android and Quest Projected Motion Breath route implementations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from tools.hostessctl.platform_defaults import (
    ANDROID_PACKAGE,
    ANDROID_PMB_CONTROLLER_PREFLIGHT_ACTION,
    ANDROID_PMB_PHYSICAL_LIVE_ACTION,
    ANDROID_PMB_PHYSICAL_LIVE_BACKGROUND_ACTION,
    ANDROID_PMB_PHYSICAL_LIVE_SERVICE,
    ANDROID_PMB_REPLAY_ACTION,
    ANDROID_PMB_SIMULATED_LIVE_ACTION,
    ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE,
    ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_REPORT,
    ANDROID_REMOTE_PMB_CORE_REPORT,
    ANDROID_REMOTE_PMB_EVIDENCE,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_BROKER_REPORT,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_CAPTURE_REPORT,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVENTS_JSONL,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE,
    ANDROID_REMOTE_PMB_PHYSICAL_LIVE_ROUTE_REPORT,
    ANDROID_REMOTE_PMB_SIMULATED_LIVE_BROKER_REPORT,
    ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE,
    ANDROID_REMOTE_PMB_SIMULATED_LIVE_ROUTE_REPORT,
)
from tools.hostessctl.pmb_evidence import (
    PMB_BREATH_VOLUME_SELECTED_STREAM,
    projected_motion_breath_package_root,
    validate_pmb_android_replay_execution_evidence,
    validate_pmb_controller_preflight_evidence,
    validate_pmb_quest_physical_live_evidence,
    validate_pmb_quest_simulated_live_evidence,
    write_pmb_android_host_run_evidence,
    write_pmb_controller_preflight_host_run_evidence,
    write_pmb_quest_physical_live_host_run_evidence,
    write_pmb_quest_simulated_live_host_run_evidence,
)
from tools.hostessctl.pmb_native_receipts import (
    NATIVE_RENDERER_LOGCAT_FILTER,
    PMB_APP_RECEIPT_POLICY_MAKEPAD,
    PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER,
    native_renderer_receipt_summary_from_logcat,
    pmb_app_receipt_policy_from_args,
    pmb_effective_receipt_listen_seconds,
)
from tools.hostessctl.pmb_support import (
    PMB_CONTROLLER_STATE_EXHALE_THRESHOLD,
    PMB_CONTROLLER_STATE_INHALE_THRESHOLD,
    PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS,
    PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD,
    PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES,
    PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS,
)


RunFunc = Callable[..., Any]


def run_android_pmb_replay(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    clear_android_pmb_artifacts_func: Callable[[argparse.Namespace], None],
    wait_for_android_file_func: Callable[[argparse.Namespace, str, float], None],
) -> int:
    if not args.adb or not args.serial:
        raise SystemExit("--adb and --serial are required for phone and quest PMB replay targets")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    host_profile = "headset" if args.target == "quest" else "mobile"
    run_func([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    clear_android_pmb_artifacts_func(args)
    run_func(
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
    wait_for_android_file_func(args, ANDROID_REMOTE_PMB_EVIDENCE, 30.0)
    run_func([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_EVIDENCE, str(out)])
    core_report_path = out.with_name(f"{out.stem}.core-validation-report.json")
    run_func([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_CORE_REPORT, str(core_report_path)])
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


def run_pmb_controller_preflight(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    clear_android_pmb_controller_preflight_artifacts_func: Callable[[argparse.Namespace], None],
    wait_for_android_file_func: Callable[[argparse.Namespace, str, float], None],
) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    host_profile = "headset" if args.target == "quest" else "mobile"
    run_func([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    clear_android_pmb_controller_preflight_artifacts_func(args)
    run_func(
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
    wait_for_android_file_func(args, ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE, 30.0)
    run_func([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE, str(out)])
    report_path = out.with_name(f"{out.stem}.controller-preflight-report.json")
    run_func(
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


def run_pmb_quest_simulated_live(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    configure_makepad_breath_feedback_receiver_func: Callable[[argparse.Namespace], None],
    clear_android_pmb_simulated_live_artifacts_func: Callable[[argparse.Namespace], None],
    wait_for_android_file_func: Callable[[argparse.Namespace, str, float], None],
    selected_broker_activity_func: Callable[[argparse.Namespace], str],
    attach_broker_identity_func: Callable[[dict[str, Any], argparse.Namespace], dict[str, Any]],
) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    host_profile = "headset"
    if not getattr(args, "no_launch_broker", False):
        run_func([args.adb, "-s", args.serial, "shell", "am", "start", "-n", selected_broker_activity_func(args)])
    if not getattr(args, "no_launch_makepad", False):
        configure_makepad_breath_feedback_receiver_func(args)
    clear_android_pmb_simulated_live_artifacts_func(args)
    run_func([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    run_func(
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
    wait_for_android_file_func(args, ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE, 45.0)
    run_func([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE, str(out)])
    route_report_path = out.with_name(f"{out.stem}.live-route-report.json")
    broker_report_path = out.with_name(f"{out.stem}.broker-publish-report.json")
    run_func(
        [
            args.adb,
            "-s",
            args.serial,
            "pull",
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_ROUTE_REPORT,
            str(route_report_path),
        ]
    )
    run_func(
        [
            args.adb,
            "-s",
            args.serial,
            "pull",
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_BROKER_REPORT,
            str(broker_report_path),
        ]
    )
    evidence = attach_broker_identity_func(json.loads(out.read_text(encoding="utf-8")), args)
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


def run_pmb_quest_physical_live(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    run_captured_func: RunFunc,
    grant_broker_runtime_permissions_func: Callable[[argparse.Namespace], None],
    configure_makepad_physical_pmb_provider_func: Callable[[argparse.Namespace], None],
    clear_android_pmb_physical_live_artifacts_func: Callable[[argparse.Namespace], None],
    wait_for_android_file_func: Callable[[argparse.Namespace, str, float], None],
    selected_broker_activity_func: Callable[[argparse.Namespace], str],
    broker_identity_func: Callable[[argparse.Namespace], dict[str, Any]],
    attach_broker_identity_func: Callable[[dict[str, Any], argparse.Namespace], dict[str, Any]],
) -> int:
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
    app_receipt_policy = pmb_app_receipt_policy_from_args(args)
    if not getattr(args, "no_launch_broker", False):
        grant_broker_runtime_permissions_func(args)
        run_func([args.adb, "-s", args.serial, "shell", "am", "start", "-n", selected_broker_activity_func(args)])
    if (
        app_receipt_policy == PMB_APP_RECEIPT_POLICY_MAKEPAD
        and not getattr(args, "no_launch_makepad", False)
    ):
        configure_makepad_physical_pmb_provider_func(args)
    clear_android_pmb_physical_live_artifacts_func(args)
    run_func([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    command = pmb_physical_live_start_command(args, host_profile)
    run_func(command)
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
            "app_receipt_policy": app_receipt_policy,
            "broker_identity": broker_identity_func(args),
            "command": command,
        }
        out.write_text(json.dumps(started, indent=2, sort_keys=True), encoding="utf-8")
        return 0
    wait_seconds = (
        max(0.0, float(args.scan_timeout_seconds))
        + max(0.0, float(args.duration_seconds))
        + pmb_effective_receipt_listen_seconds(args)
        + 30.0
    )
    wait_for_android_file_func(args, ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE, wait_seconds)
    run_func([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE, str(out)])
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
        run_func([args.adb, "-s", args.serial, "pull", remote, str(local)])
    evidence = attach_broker_identity_func(json.loads(out.read_text(encoding="utf-8")), args)
    evidence.setdefault("execution", {})["app_receipt_policy"] = app_receipt_policy
    if app_receipt_policy == PMB_APP_RECEIPT_POLICY_NATIVE_RENDERER:
        attach_native_renderer_receipt_summary(
            args,
            out,
            evidence,
            run_captured_func=run_captured_func,
        )
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
        "pmb_controller_state_mode",
        str(getattr(args, "pmb_controller_state_mode", "projected-volume-delta") or "projected-volume-delta"),
        "--es",
        "pmb_controller_state_short_window_s",
        str(
            getattr(
                args,
                "pmb_controller_state_short_window_seconds",
                PMB_CONTROLLER_STATE_SHORT_WINDOW_SECONDS,
            )
        ),
        "--es",
        "pmb_controller_state_long_window_s",
        str(
            getattr(
                args,
                "pmb_controller_state_long_window_seconds",
                PMB_CONTROLLER_STATE_LONG_WINDOW_SECONDS,
            )
        ),
        "--es",
        "pmb_controller_state_inhale_threshold",
        str(
            getattr(
                args,
                "pmb_controller_state_inhale_threshold",
                PMB_CONTROLLER_STATE_INHALE_THRESHOLD,
            )
        ),
        "--es",
        "pmb_controller_state_exhale_threshold",
        str(
            getattr(
                args,
                "pmb_controller_state_exhale_threshold",
                PMB_CONTROLLER_STATE_EXHALE_THRESHOLD,
            )
        ),
        "--es",
        "pmb_controller_state_rotation_guard_degrees",
        str(
            getattr(
                args,
                "pmb_controller_state_rotation_guard_degrees",
                PMB_CONTROLLER_STATE_ROTATION_GUARD_DEGREES,
            )
        ),
        "--es",
        "pmb_controller_state_moving_average_guard",
        str(
            getattr(
                args,
                "pmb_controller_state_moving_average_guard",
                PMB_CONTROLLER_STATE_MOVING_AVERAGE_GUARD,
            )
        ),
        "--es",
        "feedback_publish_limit",
        str(args.feedback_publish_limit),
        "--es",
        "breath_selected_source",
        str(getattr(args, "breath_selected_source", "auto") or "auto"),
        "--es",
        "receipt_listen_ms",
        str(int(pmb_effective_receipt_listen_seconds(args) * 1000.0)),
    ])
    if args.device_address:
        command.extend(["--es", "device_address", args.device_address])
    return command


def attach_native_renderer_receipt_summary(
    args: argparse.Namespace,
    out: Path,
    evidence: dict[str, Any],
    *,
    run_captured_func: RunFunc,
) -> None:
    logcat_path = out.with_name(f"{out.stem}.native-renderer-logcat.txt")
    result = run_captured_func(
        [
            args.adb,
            "-s",
            args.serial,
            "logcat",
            "-d",
            "-s",
            "RQNativeRenderer:I",
            "*:S",
        ],
        allow_failure=True,
    )
    logcat_text = result.stdout or ""
    logcat_path.write_text(logcat_text, encoding="utf-8")
    summary = native_renderer_receipt_summary_from_logcat(
        logcat_text,
        broker_summary=evidence.get("broker_publish_summary", {}),
        route_summary=evidence.get("route_report_summary", {}),
    )
    summary["logcat_artifact"] = logcat_path.name
    summary["logcat_filter"] = NATIVE_RENDERER_LOGCAT_FILTER
    summary["logcat_returncode"] = result.returncode
    if result.stderr:
        summary["logcat_stderr_tail"] = result.stderr[-2048:]
    evidence["native_app_receipt_summary"] = summary
