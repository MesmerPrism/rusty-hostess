"""Small Hostess T command bridge for the first live-capture slot."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
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
    run_live.add_argument("--stream", choices=["hr_rr", "ecg", "acc"], required=True)
    run_live.add_argument("--out", required=True)
    run_live.add_argument("--packages-root", required=True)
    run_live.add_argument("--duration-seconds", type=float, default=12.0)
    run_live.add_argument("--device-address")
    run_live.add_argument("--adb")
    run_live.add_argument("--serial")
    run_live.add_argument("--acc-rate", type=int, default=200)

    args = parser.parse_args()
    if args.command == "install-android":
        return install_android(args)
    if args.command == "run-live":
        return run_live_capture(args)
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
        args.stream,
        "--duration-seconds",
        str(args.duration_seconds),
        "--acc-rate",
        str(args.acc_rate),
        "--out",
        str(out),
    ]
    if args.device_address:
        command.extend(["--device-address", args.device_address])
    return run(command).returncode


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
        args.stream,
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
    run(command)
    time.sleep(args.duration_seconds + 20.0)
    run([args.adb, "-s", args.serial, "pull", ANDROID_REMOTE_EVIDENCE, str(out)])
    validator_stream = args.stream
    validator_host = "headset" if args.target == "quest" else "mobile"
    return run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "check_live_capture_evidence.py"),
            "--input",
            str(out),
            "--expect-host",
            validator_host,
            "--expect-stream",
            validator_stream,
        ]
    ).returncode


def run(command: list[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True)
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
