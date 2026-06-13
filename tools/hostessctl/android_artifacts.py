"""Android artifact cleanup and app-private file facades for hostessctl routes."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from tools.hostessctl import android_files
from tools.hostessctl.platform_defaults import (
    ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE,
    ANDROID_REMOTE_BROKER_TELEMETRY_REPORT,
    ANDROID_REMOTE_EVIDENCE,
    ANDROID_REMOTE_GRAPH_REPORT,
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
    ANDROID_REMOTE_RUNTIME_INPUT,
)


RunFunc = Callable[..., Any]


def clear_android_live_artifacts(args: argparse.Namespace, *, run_func: RunFunc) -> None:
    clear_android_files(
        args,
        [ANDROID_REMOTE_EVIDENCE, ANDROID_REMOTE_RUNTIME_INPUT, ANDROID_REMOTE_GRAPH_REPORT],
        run_func=run_func,
    )


def clear_android_pmb_artifacts(args: argparse.Namespace, *, run_func: RunFunc) -> None:
    clear_android_files(args, [ANDROID_REMOTE_PMB_EVIDENCE, ANDROID_REMOTE_PMB_CORE_REPORT], run_func=run_func)


def clear_android_pmb_controller_preflight_artifacts(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
) -> None:
    clear_android_files(
        args,
        [
            ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_EVIDENCE,
            ANDROID_REMOTE_PMB_CONTROLLER_PREFLIGHT_REPORT,
        ],
        run_func=run_func,
    )


def clear_android_pmb_simulated_live_artifacts(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
) -> None:
    clear_android_files(
        args,
        [
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_EVIDENCE,
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_ROUTE_REPORT,
            ANDROID_REMOTE_PMB_SIMULATED_LIVE_BROKER_REPORT,
        ],
        run_func=run_func,
    )


def clear_android_pmb_physical_live_artifacts(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
) -> None:
    clear_android_files(
        args,
        [
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVIDENCE,
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_CAPTURE_REPORT,
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_EVENTS_JSONL,
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_ROUTE_REPORT,
            ANDROID_REMOTE_PMB_PHYSICAL_LIVE_BROKER_REPORT,
        ],
        run_func=run_func,
    )


def clear_android_broker_telemetry_artifacts(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
) -> None:
    clear_android_files(
        args,
        [
            ANDROID_REMOTE_BROKER_TELEMETRY_EVIDENCE,
            ANDROID_REMOTE_BROKER_TELEMETRY_REPORT,
        ],
        run_func=run_func,
    )


def clear_android_files(
    args: argparse.Namespace,
    remote_paths: list[str],
    *,
    run_func: RunFunc,
) -> None:
    android_files.clear_android_files(args, remote_paths, run=run_func)


def wait_for_android_evidence(
    args: argparse.Namespace,
    timeout_seconds: float,
    *,
    wait_for_android_file_func: Callable[[argparse.Namespace, str, float], None],
) -> None:
    wait_for_android_file_func(args, ANDROID_REMOTE_EVIDENCE, timeout_seconds)


def wait_for_android_file(
    args: argparse.Namespace,
    remote_path: str,
    timeout_seconds: float,
    *,
    run_func: RunFunc,
) -> None:
    android_files.wait_for_android_file(args, remote_path, timeout_seconds, run=run_func)


def wait_for_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    timeout_seconds: float,
    *,
    run_func: RunFunc,
) -> None:
    android_files.wait_for_android_run_as_file(
        args,
        package,
        relative_path,
        timeout_seconds,
        run=run_func,
    )


def pull_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    out: Path,
) -> None:
    android_files.pull_android_run_as_file(args, package, relative_path, out)


def write_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    payload: bytes,
) -> None:
    android_files.write_android_run_as_file(args, package, relative_path, payload)


def android_shell_quote(value: str) -> str:
    return android_files.android_shell_quote(value)


def read_android_run_as_file(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
) -> bytes:
    return android_files.read_android_run_as_file(args, package, relative_path)


def wait_for_makepad_render_sidecar(
    args: argparse.Namespace,
    package: str,
    relative_path: str,
    timeout_seconds: float,
    *,
    target: str,
    min_events: int,
) -> None:
    android_files.wait_for_makepad_render_sidecar(
        args,
        package,
        relative_path,
        timeout_seconds,
        target=target,
        min_events=min_events,
    )
