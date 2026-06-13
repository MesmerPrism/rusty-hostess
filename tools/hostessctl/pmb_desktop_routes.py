"""Desktop Projected Motion Breath route implementations for hostessctl."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from tools.hostessctl.pmb_evidence import (
    build_pmb_desktop_replay_execution_evidence,
    build_pmb_live_route_self_test_evidence,
    build_pmb_shell_handoff_validation_evidence,
    default_pmb_shell_handoff_path,
    parse_pmb_core_report,
    projected_motion_breath_package_root,
    validate_pmb_desktop_replay_execution_evidence,
    validate_pmb_live_route_self_test_evidence,
    validate_pmb_shell_handoff_validation_evidence,
    write_pmb_host_run_evidence,
    write_pmb_live_route_host_run_evidence,
    write_pmb_shell_handoff_host_run_evidence,
)


RunCapturedFunc = Callable[..., Any]


def run_pmb_replay_capture(
    args: argparse.Namespace,
    *,
    run_captured_func: RunCapturedFunc,
    run_android_pmb_replay_func: Callable[[argparse.Namespace], int],
) -> int:
    if args.target in {"phone", "quest"}:
        return run_android_pmb_replay_func(args)
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
    core_run = run_captured_func(command, allow_failure=True, cwd=packages_root)
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


def run_pmb_live_route_self_test(
    args: argparse.Namespace,
    *,
    run_captured_func: RunCapturedFunc,
) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    route_report_path = out.with_name(f"{out.stem}.live-broker-route-report.json")
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
        "live-route-self-test",
        "--package-root",
        str(package_root),
    ]
    core_run = run_captured_func(command, allow_failure=True, cwd=packages_root)
    ended_utc = datetime.now(UTC)
    stdout_path.write_text(core_run.stdout, encoding="utf-8")
    stderr_path.write_text(core_run.stderr, encoding="utf-8")
    route_report, parse_error = parse_pmb_core_report(core_run.stdout)
    if route_report is not None:
        route_report_path.write_text(
            json.dumps(route_report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    evidence = build_pmb_live_route_self_test_evidence(
        packages_root=packages_root,
        package_root=package_root,
        command=command,
        core_run=core_run,
        route_report=route_report,
        route_report_path=route_report_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        started_utc=started_utc,
        ended_utc=ended_utc,
        parse_error=parse_error,
    )
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    validation_report = validate_pmb_live_route_self_test_evidence(evidence)
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_pmb_live_route_host_run_evidence(out, validation_path, evidence)
    return 0 if validation_report["status"] == "pass" else core_run.returncode or 2


def run_pmb_shell_handoff(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packages_root = Path(args.packages_root)
    package_root = projected_motion_breath_package_root(packages_root)
    if not package_root.exists():
        raise SystemExit(f"projected-motion-breath package root not found: {package_root}")
    handoff_path = Path(args.handoff) if getattr(args, "handoff", None) else default_pmb_shell_handoff_path(package_root)
    if not handoff_path.exists():
        raise SystemExit(f"PMB shell handoff manifest not found: {handoff_path}")
    started_utc = datetime.now(UTC)
    evidence = build_pmb_shell_handoff_validation_evidence(
        packages_root=packages_root,
        package_root=package_root,
        handoff_path=handoff_path,
        started_utc=started_utc,
        ended_utc=datetime.now(UTC),
    )
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    validation_report = validate_pmb_shell_handoff_validation_evidence(evidence)
    validation_path = out.with_name(f"{out.stem}.validation-report.json")
    validation_path.write_text(
        json.dumps(validation_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if validation_report["status"] == "pass":
        write_pmb_shell_handoff_host_run_evidence(out, validation_path, evidence)
    return 0 if validation_report["status"] == "pass" else 2
