"""Telemetry render, Makepad render, and snapshot routes for hostessctl."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from tools.hostessctl import makepad_shell_contract as makepad_shell_contract_launcher
from tools.hostessctl.manifold_recording import adb_prefix
from tools.hostessctl.platform_defaults import (
    ANDROID_PACKAGE,
    ANDROID_REMOTE_EVIDENCE,
    ANDROID_REMOTE_RENDER_ROOT,
    ANDROID_RENDER_ACTION,
    MAKEPAD_ANDROID_ACTIVITY,
    MAKEPAD_ANDROID_PACKAGE,
    MAKEPAD_RENDER_RELATIVE,
    MAKEPAD_RENDER_SIDECAR_RELATIVE,
)
from tools.hostessctl.telemetry_render import (
    render_desktop_telemetry,
    render_sidecar_path,
    sanitize_remote_name,
    validate_render_output,
)
from tools.telemetry_snapshot import build_snapshot, write_snapshot


RunFunc = Callable[..., Any]


def render_telemetry(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    wait_for_android_file_func: Callable[[argparse.Namespace, str, float], None],
) -> int:
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
    run_func([args.adb, "-s", args.serial, "shell", "rm", "-f", remote], allow_failure=True)
    run_func([args.adb, "-s", args.serial, "shell", "rm", "-f", remote_sidecar], allow_failure=True)
    run_func(
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
            "--es",
            "render_source_evidence_path",
            args.source_evidence_path or "hostess-t/evidence/live-capture/latest.json",
        ]
    )
    wait_for_android_file_func(args, remote_sidecar, 10.0)
    run_func([args.adb, "-s", args.serial, "pull", remote, str(out)])
    sidecar = render_sidecar_path(out)
    run_func([args.adb, "-s", args.serial, "pull", remote_sidecar, str(sidecar)])
    validate_render_output(
        out,
        sidecar,
        expected_page=args.page,
        source_evidence_path=args.source_evidence_path or ANDROID_REMOTE_EVIDENCE,
        target=args.target,
    )
    return 0


def pull_makepad_render(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    wait_for_android_run_as_file_func: Callable[[argparse.Namespace, str, str, float], None],
    wait_for_makepad_render_sidecar_func: Callable[..., None],
    pull_android_run_as_file_func: Callable[[argparse.Namespace, str, str, Path], None],
) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not args.no_launch:
        run_func(
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
        run_func(
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
        run_func(
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
    wait_for_android_run_as_file_func(
        args,
        MAKEPAD_ANDROID_PACKAGE,
        MAKEPAD_RENDER_SIDECAR_RELATIVE,
        args.wait_seconds,
    )
    wait_for_makepad_render_sidecar_func(
        args,
        MAKEPAD_ANDROID_PACKAGE,
        MAKEPAD_RENDER_SIDECAR_RELATIVE,
        args.wait_seconds,
        target="headset" if args.target == "quest" else "mobile",
        min_events=args.min_events,
    )
    pull_android_run_as_file_func(args, MAKEPAD_ANDROID_PACKAGE, MAKEPAD_RENDER_RELATIVE, out)
    sidecar = render_sidecar_path(out)
    pull_android_run_as_file_func(
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


def launch_makepad_shell_contract(
    args: argparse.Namespace,
    *,
    host_app_for_func: Callable[[str], str],
    run_func: RunFunc,
    wait_for_android_run_as_file_func: Callable[[argparse.Namespace, str, str, float], None],
    pull_android_run_as_file_func: Callable[[argparse.Namespace, str, str, Path], None],
    write_android_run_as_file_func: Callable[[argparse.Namespace, str, str, bytes], None],
) -> int:
    return makepad_shell_contract_launcher.launch_makepad_shell_contract(
        args,
        adb_prefix=adb_prefix,
        host_app_for=host_app_for_func,
        run=run_func,
        wait_for_android_run_as_file=wait_for_android_run_as_file_func,
        pull_android_run_as_file=pull_android_run_as_file_func,
        write_android_run_as_file=write_android_run_as_file_func,
    )


def snapshot_telemetry(args: argparse.Namespace) -> int:
    evidence_path = Path(args.input)
    snapshot = build_snapshot(
        evidence_path,
        graph_report_path=Path(args.graph_report) if args.graph_report else None,
        runtime_input_path=Path(args.runtime_input) if args.runtime_input else None,
    )
    write_snapshot(snapshot, Path(args.out))
    return 0
