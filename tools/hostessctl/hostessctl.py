"""Small Hostess T command bridge for the first live-capture slot."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.check_live_capture_evidence import package_snapshot, sha256_file  # noqa: E402
from tools.telemetry_snapshot import build_snapshot, write_snapshot  # noqa: E402

ANDROID_PACKAGE = "io.github.mesmerprism.rustyhostess.t"
MAKEPAD_ANDROID_PACKAGE = "io.github.mesmerprism.rustyhostess.makepad"
MAKEPAD_ANDROID_ACTIVITY = f"{MAKEPAD_ANDROID_PACKAGE}/.MakepadApp"
ANDROID_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_CAPTURE"
ANDROID_REPLAY_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_REPLAY"
ANDROID_PMB_REPLAY_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_PMB_REPLAY"
ANDROID_PMB_CONTROLLER_PREFLIGHT_ACTION = (
    "io.github.mesmerprism.rustyhostess.t.RUN_PMB_CONTROLLER_PREFLIGHT"
)
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
        "provider_id": "provider.polar_h10.ble",
        "provider_kind": "ble_polar_h10",
        "package_id": "package.polar_h10",
        "live_stream_mode": "acc",
        "sample_kind": "motion_vector3",
        "supported_targets": ["desktop", "phone", "quest"],
        "single_value_live_route_supported": True,
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
        "provider_id": "provider.headset.controller_pose",
        "provider_kind": "xr_controller_pose",
        "package_id": "package.projected_motion_breath",
        "sample_kind": "object_pose",
        "supported_targets": ["quest"],
        "single_value_live_route_supported": False,
        "preflight_supported": True,
        "preflight_route": "hostessctl.run-pmb-controller-preflight",
        "blocked_reason": "live OpenXR/controller pose provider is not attached to Hostess record-values yet",
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

    makepad_render = subcommands.add_parser("pull-makepad-render")
    makepad_render.add_argument("--target", choices=["phone", "quest"], required=True)
    makepad_render.add_argument("--adb", required=True)
    makepad_render.add_argument("--serial", required=True)
    makepad_render.add_argument("--out", required=True)
    makepad_render.add_argument("--wait-seconds", type=float, default=45.0)
    makepad_render.add_argument("--min-events", type=int, default=0)
    makepad_render.add_argument("--no-launch", action="store_true")

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
    if args.command == "record-values":
        return run_manifold_value_recording(args)
    if args.command == "render-telemetry":
        return render_telemetry(args)
    if args.command == "pull-makepad-render":
        return pull_makepad_render(args)
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
    started_utc = datetime.now(UTC)
    capture_status: int | None = None
    capture_evidence: dict[str, Any] | None = None
    capture_evidence_path: Path | None = None

    if not args.plan_only and route_status == "ready":
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
    status = "ready" if single_live else "requires_provider"
    blocked_reason = provider.get("blocked_reason")
    if not target_supported:
        status = "unavailable_on_target"
        blocked_reason = f"value is not available on target {target}"
    return {
        "value_id": provider["value_id"],
        "requested_value_id": value_id,
        "stream_id": provider["stream_id"],
        "provider_id": provider["provider_id"],
        "provider_kind": provider["provider_kind"],
        "package_id": provider.get("package_id"),
        "sample_kind": provider.get("sample_kind"),
        "target": target,
        "supported_targets": supported_targets,
        "status": status,
        "live_supported": single_live,
        "preflight_supported": bool(provider.get("preflight_supported")),
        "single_value_live_route_supported": single_live,
        "combined_recording_supported": False,
        "recording_route": "hostessctl.run-live" if single_live else None,
        "live_stream_mode": provider.get("live_stream_mode"),
        "preflight_route": provider.get("preflight_route"),
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
    if len(provider_plans) > 1:
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
    captured_streams = []
    if capture_evidence:
        captured_streams = [
            {
                "stream_id": stream.get("stream_id"),
                "status": stream.get("status"),
                "sample_count": stream.get("sample_count"),
                "event_count": stream.get("event_count"),
            }
            for stream in capture_evidence.get("streams", [])
            if isinstance(stream, dict)
        ]
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
            "physical_controller_input_used": False,
            "controller_input_used": False,
            "simultaneous_multi_value_recording_supported": len(provider_plans) == 1,
            "manual_controller_trial_required": any(
                plan.get("stream_id") == "stream.motion.object_pose"
                for plan in provider_plans
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
    status = evidence.get("status")
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
            recording.get("physical_controller_input_used") is False
            and recording.get("controller_input_used") is False,
            "evidence does not claim live physical controller input",
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
        source_evidence_path=ANDROID_REMOTE_EVIDENCE,
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
