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
ANDROID_REMOTE_EVIDENCE = (
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/hostess-t/evidence/live-capture/latest.json"
)


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

    run_replay = subcommands.add_parser("run-replay")
    run_replay.add_argument("--target", choices=["desktop"], default="desktop")
    run_replay.add_argument("--module", action="append", required=True)
    run_replay.add_argument("--out", required=True)
    run_replay.add_argument("--packages-root", required=True)
    run_replay.add_argument("--input")

    args = parser.parse_args()
    if args.command == "install-android":
        return install_android(args)
    if args.command == "run-live":
        return run_live_capture(args)
    if args.command == "run-replay":
        return run_replay_capture(args)
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
    run([args.adb, "-s", args.serial, "shell", "rm", "-f", ANDROID_REMOTE_EVIDENCE], allow_failure=True)
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
    ]
    if args.device_address:
        command.extend(["--es", "device_address", args.device_address])
    if args.module:
        command.extend(["--es", "modules", ",".join(args.module)])
    run(command)
    time.sleep(args.duration_seconds + 20.0)
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_EVIDENCE, str(out)])
    return validate_evidence(args, out, "headset" if args.target == "quest" else "mobile")


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
