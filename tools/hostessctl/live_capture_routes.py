"""Live capture and Polar replay route implementations for hostessctl."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from tools.check_live_capture_evidence import package_snapshot
from tools.hostessctl.platform_defaults import (
    ANDROID_ACTION,
    ANDROID_PACKAGE,
    ANDROID_REMOTE_EVIDENCE,
    ANDROID_REMOTE_GRAPH_REPORT,
    ANDROID_REMOTE_RUNTIME_INPUT,
    ANDROID_REPLAY_ACTION,
)
from tools.hostessctl.runtime import REPO_ROOT
from tools.hostessctl.pmb_evidence import graph_report_streams, write_contract_evidence


RunFunc = Callable[..., Any]


def polar_package_root(packages_root: Path) -> Path:
    package_root = packages_root / "packages" / "polar-h10"
    if not package_root.exists() and packages_root.name == "polar-h10":
        return packages_root
    return package_root


def install_android(args: argparse.Namespace, *, run_func: RunFunc) -> int:
    run_func([args.adb, "-s", args.serial, "uninstall", ANDROID_PACKAGE], allow_failure=True)
    run_func([args.adb, "-s", args.serial, "install", args.apk])
    for permission in [
        "android.permission.BLUETOOTH_SCAN",
        "android.permission.BLUETOOTH_CONNECT",
        "android.permission.ACCESS_FINE_LOCATION",
    ]:
        run_func(
            [args.adb, "-s", args.serial, "shell", "pm", "grant", ANDROID_PACKAGE, permission],
            allow_failure=True,
        )
    return 0


def run_desktop_capture(
    args: argparse.Namespace,
    out: Path,
    *,
    run_func: RunFunc,
    validate_evidence_func: Callable[[argparse.Namespace, Path, str], int],
) -> int:
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
    capture = run_func(command, allow_failure=True)
    validation = validate_evidence_func(args, out, "desktop")
    return validation if validation != 0 else capture.returncode


def run_replay_capture(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    run_android_replay_func: Callable[[argparse.Namespace], int],
    validate_evidence_func: Callable[[argparse.Namespace, Path, str], int],
) -> int:
    if args.target in {"phone", "quest"}:
        return run_android_replay_func(args)
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
    graph_run = run_func(command, allow_failure=True, cwd=packages_root)
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
    validation = validate_evidence_func(args, out, "desktop")
    return validation if validation != 0 else graph_run.returncode


def run_android_capture(
    args: argparse.Namespace,
    out: Path,
    *,
    run_func: RunFunc,
    clear_android_live_artifacts_func: Callable[[argparse.Namespace], None],
    wait_for_android_evidence_func: Callable[[argparse.Namespace, float], None],
    pull_android_runtime_artifacts_func: Callable[[argparse.Namespace, Path], None],
    append_rmssd_baseline_extras_func: Callable[[list[str], argparse.Namespace], None],
    validate_evidence_func: Callable[[argparse.Namespace, Path, str], int],
) -> int:
    if not args.adb or not args.serial:
        raise SystemExit("--adb and --serial are required for phone and quest targets")
    host_profile = "headset" if args.target == "quest" else "mobile"
    run_func([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    clear_android_live_artifacts_func(args)
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
    append_rmssd_baseline_extras_func(command, args)
    run_func(command)
    wait_for_android_evidence_func(args, args.duration_seconds + 90.0)
    run_func([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_EVIDENCE, str(out)])
    pull_android_runtime_artifacts_func(args, out)
    return validate_evidence_func(args, out, "headset" if args.target == "quest" else "mobile")


def run_android_replay(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    clear_android_live_artifacts_func: Callable[[argparse.Namespace], None],
    wait_for_android_evidence_func: Callable[[argparse.Namespace, float], None],
    pull_android_runtime_artifacts_func: Callable[[argparse.Namespace, Path], None],
    validate_evidence_func: Callable[[argparse.Namespace, Path, str], int],
) -> int:
    if not args.adb or not args.serial:
        raise SystemExit("--adb and --serial are required for phone and quest replay targets")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    host_profile = "headset" if args.target == "quest" else "mobile"
    run_func([args.adb, "-s", args.serial, "shell", "am", "force-stop", ANDROID_PACKAGE], allow_failure=True)
    clear_android_live_artifacts_func(args)
    run_func(
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
    wait_for_android_evidence_func(args, 15.0)
    run_func([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_EVIDENCE, str(out)])
    pull_android_runtime_artifacts_func(args, out)
    return validate_evidence_func(args, out, host_profile)


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


def pull_android_runtime_artifacts(
    args: argparse.Namespace,
    out: Path,
    *,
    run_func: RunFunc,
) -> None:
    run_func(
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
    run_func(
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


def validate_evidence(
    args: argparse.Namespace,
    out: Path,
    host_profile: str,
    *,
    run_func: RunFunc,
) -> int:
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
    result = run_func(command, allow_failure=True)
    if result.returncode == 0:
        write_contract_evidence(out, report_out, host_profile)
    return result.returncode
