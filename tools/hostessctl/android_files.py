"""Android file and app-private run-as helpers for hostessctl."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Protocol


class RunCommand(Protocol):
    def __call__(
        self,
        command: list[str],
        *,
        allow_failure: bool = False,
    ) -> subprocess.CompletedProcess[Any]:
        ...


def clear_android_files(
    args: argparse.Namespace,
    remote_paths: list[str],
    *,
    run: RunCommand,
) -> None:
    for remote in remote_paths:
        run([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)


def wait_for_android_file(
    args: argparse.Namespace,
    remote_path: str,
    timeout_seconds: float,
    *,
    run: RunCommand,
) -> None:
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
    *,
    run: RunCommand,
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


def write_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    payload: bytes,
) -> None:
    result = subprocess.run(
        [
            args.adb,
            "-s",
            args.serial,
            "exec-in",
            "run-as",
            package,
            "sh",
            "-c",
            f"cat > {android_shell_quote(relative_path)}",
        ],
        check=False,
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"could not write app file {package}:{relative_path}: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )


def android_shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


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
