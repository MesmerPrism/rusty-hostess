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

from tools.check_live_capture_evidence import package_snapshot  # noqa: E402

ANDROID_PACKAGE = "io.github.mesmerprism.rustyhostess.t"
ANDROID_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_CAPTURE"
ANDROID_REPLAY_ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_REPLAY"
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
ANDROID_REMOTE_RENDER_ROOT = f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/render"


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

    render = subcommands.add_parser("render-telemetry")
    render.add_argument("--target", choices=["desktop", "phone", "quest"], required=True)
    render.add_argument("--adb")
    render.add_argument("--serial")
    render.add_argument("--out", required=True)
    render.add_argument("--input")
    render.add_argument("--name")
    render.add_argument("--page", choices=["raw", "modules"], default="raw")

    args = parser.parse_args()
    if args.command == "install-android":
        return install_android(args)
    if args.command == "run-live":
        return run_live_capture(args)
    if args.command == "run-replay":
        return run_replay_capture(args)
    if args.command == "render-telemetry":
        return render_telemetry(args)
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
    run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)
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
        ]
    )
    time.sleep(1.0)
    run([args.adb, "-s", args.serial, "pull", remote, str(out)])
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
    runtime_path = evidence_path.with_name(capture.get("runtime_input", ""))
    graph_path = evidence_path.with_name(capture.get("graph_execution_report", ""))
    runtime_input = json.loads(runtime_path.read_text(encoding="utf-8")) if runtime_path.exists() else {}
    graph_report = json.loads(graph_path.read_text(encoding="utf-8")) if graph_path.exists() else {}

    image = Image.new("RGB", (1080, 760), (248, 248, 246))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw_header(draw, font, evidence, graph_report, args.page)
    if args.page == "raw":
        draw_desktop_raw_page(draw, font, runtime_input, evidence)
    else:
        draw_desktop_module_page(draw, font, graph_report)
    image.save(out)
    return 0


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


def wait_for_android_evidence(args: argparse.Namespace, timeout_seconds: float) -> None:
    deadline = time.monotonic() + max(timeout_seconds, 1.0)
    while time.monotonic() < deadline:
        result = run(
            [args.adb, "-s", args.serial, "shell", "test", "-f", ANDROID_REMOTE_EVIDENCE],
            allow_failure=True,
        )
        if result.returncode == 0:
            return
        time.sleep(1.0)
    raise SystemExit(f"timed out waiting for Android evidence: {ANDROID_REMOTE_EVIDENCE}")


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
        "$schema": "rusty.manifold.hostess.run_evidence.v1",
        "run_id": f"hostess.run.live_capture.{host_profile}.{run_segment}.{started_ms}",
        "bundle_id": "hostess.bundle.polar_h10.live_smoke",
        "validation_slot_id": "hostess.slot.live_smoke",
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
            "artifact.hostess_run_evidence",
        ],
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.hostess_t.live_capture",
            "target_id": f"hostess.run.live_capture.{host_profile}.{run_segment}.{started_ms}",
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
    contract_path = raw_evidence_path.with_name(f"{raw_evidence_path.stem}.hostess-run-evidence.json")
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


if __name__ == "__main__":
    raise SystemExit(main())
