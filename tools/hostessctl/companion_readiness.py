"""Companion readiness report helpers for hostessctl."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from tools.hostessctl.platform_defaults import (
    BROKER_LOCAL_FORWARD_PORT,
    BROKER_PORT,
    MAKEPAD_ANDROID_PACKAGE,
    MAKEPAD_ANDROID_XR_ACTIVITY,
    MANIFOLD_BROKER_ACTIVITY,
    MANIFOLD_BROKER_PACKAGE,
)


HOSTESS_COMPANION_READINESS_SCHEMA = "rusty.hostess.companion.readiness_report.v1"
HOSTESS_COMPANION_READINESS_VALIDATION_SCHEMA = (
    "rusty.hostess.companion.readiness_validation.v1"
)
GUI_COMPANION_MODULE_DESCRIPTOR_SCHEMA = "rusty.gui.companion.module_descriptor.v1"
READINESS_DESCRIPTOR_MODULE_ID = "companion.readiness.preconditions"
VALID_READINESS_STATUSES = {"pass", "warn", "fail", "skipped"}


def run_companion_readiness(
    args: argparse.Namespace,
    *,
    run_captured_func: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    clock_ms_func: Callable[[], int] | None = None,
    which_func: Callable[[str], str | None] | None = None,
    broker_probe_func: Callable[[str, int, float], bool] | None = None,
) -> int:
    """Write a companion readiness report and validation sidecar."""

    report = build_companion_readiness_report(
        args,
        run_captured_func=run_captured_func or default_run_captured,
        clock_ms_func=clock_ms_func or epoch_ms,
        which_func=which_func or shutil.which,
        broker_probe_func=broker_probe_func or broker_port_open,
    )
    validation = validate_companion_readiness_report(report)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation_out = (
        Path(args.validation_out)
        if getattr(args, "validation_out", None)
        else out.with_name(f"{out.stem}.validation-report.json")
    )
    validation_out.parent.mkdir(parents=True, exist_ok=True)
    validation_out.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if getattr(args, "fail_on_blocking", False) and validation["status"] != "pass":
        return 2
    return 0


def build_companion_readiness_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Callable[..., subprocess.CompletedProcess[str]],
    clock_ms_func: Callable[[], int],
    which_func: Callable[[str], str | None],
    broker_probe_func: Callable[[str, int, float], bool],
) -> dict[str, Any]:
    started_at_ms = int(clock_ms_func())
    checks: list[dict[str, Any]] = []
    profile = str(getattr(args, "profile", None) or "basic")

    descriptor_path = getattr(args, "descriptor", None)
    if descriptor_path:
        checks.append(check_companion_descriptor(Path(descriptor_path)))

    report_out = Path(args.out)
    checks.append(
        readiness_check(
            "check.host.os",
            "host",
            "Host OS",
            "pass",
            True,
            f"{platform.system()} {platform.release()}",
            observed={"system": platform.system(), "release": platform.release()},
        )
    )
    checks.append(
        readiness_check(
            "check.host.python",
            "host",
            "Python",
            "pass" if Path(sys.executable).exists() else "fail",
            True,
            sys.executable,
            observed={"executable": sys.executable},
        )
    )
    checks.append(check_output_directory(report_out.parent))

    android_toolchain_required = profile == "hostess-makepad-quest"
    cargo_required = profile == "hostess-makepad-quest"
    adb_required = bool(getattr(args, "require_adb", False)) or android_toolchain_required
    android_sdk_required = (
        bool(getattr(args, "require_android_sdk", False)) or android_toolchain_required
    )
    jdk_required = bool(getattr(args, "require_jdk", False)) or android_toolchain_required
    cargo_makepad_required = (
        bool(getattr(args, "require_cargo_makepad", False)) or cargo_required
    )
    device_required = bool(getattr(args, "require_device", False)) or profile == (
        "hostess-makepad-quest"
    )
    package_required = (
        bool(getattr(args, "require_makepad_package", False))
        or profile == "hostess-makepad-quest"
    )

    adb_path, adb_check = check_executable(
        "check.tool.adb",
        "toolchain",
        "ADB",
        str(getattr(args, "adb", None) or ""),
        adb_required,
        which_func,
        fallback_candidates=default_adb_candidates(args),
    )
    checks.append(adb_check)
    checks.append(
        check_directory(
            "check.tool.android_sdk",
            "toolchain",
            "Android SDK",
            str(getattr(args, "android_sdk", None) or default_android_sdk()),
            android_sdk_required,
        )
    )
    checks.append(
        check_jdk(
            str(getattr(args, "jdk_home", None) or default_jdk_home()),
            jdk_required,
        )
    )
    _, cargo_check = check_executable(
        "check.tool.cargo",
        "toolchain",
        "Cargo",
        str(getattr(args, "cargo", None) or "cargo"),
        cargo_required,
        which_func,
    )
    checks.append(cargo_check)
    _, cargo_makepad_check = check_executable(
        "check.tool.cargo_makepad",
        "toolchain",
        "cargo-makepad",
        str(getattr(args, "cargo_makepad", None) or "cargo-makepad"),
        cargo_makepad_required,
        which_func,
    )
    checks.append(cargo_makepad_check)

    serial = str(getattr(args, "serial", None) or "")
    if serial and adb_path:
        checks.extend(
            android_device_checks(
                args,
                adb_path,
                serial,
                run_captured_func,
                device_required=device_required,
                package_required=package_required,
            )
        )
    else:
        checks.append(
            readiness_check(
                "check.device.serial",
                "device",
                "Connected device serial",
                "fail" if device_required else "warn",
                device_required,
                "no device serial provided" if not serial else "ADB unavailable",
                issue_codes=["hostess.issue.companion.no_device_serial"],
            )
        )

    check_broker = bool(getattr(args, "check_broker", False)) or bool(
        getattr(args, "require_broker", False)
    )
    if check_broker:
        broker_host = str(getattr(args, "broker_host", None) or "127.0.0.1")
        broker_port = int(getattr(args, "broker_port", None) or BROKER_PORT)
        broker_local_port = int(
            getattr(args, "broker_local_port", None) or BROKER_LOCAL_FORWARD_PORT
        )
        require_broker = bool(getattr(args, "require_broker", False))
        if serial and adb_path:
            checks.extend(
                android_broker_checks(
                    args,
                    adb_path,
                    serial,
                    run_captured_func,
                    required=require_broker,
                )
            )
            if broker_local_port != broker_port:
                checks.append(
                    check_broker_forwarded_port(
                        broker_host,
                        broker_local_port,
                        broker_port,
                        require_broker,
                        broker_probe_func,
                    )
                )
        checks.append(
            check_broker_port(
                broker_host,
                broker_port,
                require_broker,
                broker_probe_func,
            )
        )
    else:
        checks.append(
            readiness_check(
                "check.network.broker_port",
                "network",
                "Broker port",
                "skipped",
                False,
                "broker port probe not requested",
            )
        )

    ended_at_ms = max(started_at_ms, int(clock_ms_func()))
    summary = summarize_checks(checks)
    status = status_from_summary(summary)
    return {
        "$schema": HOSTESS_COMPANION_READINESS_SCHEMA,
        "status": status,
        "profile": profile,
        "started_at_ms": started_at_ms,
        "ended_at_ms": ended_at_ms,
        "scope": {
            "adb": adb_path or str(getattr(args, "adb", None) or ""),
            "serial": serial,
            "broker_host": str(getattr(args, "broker_host", None) or "127.0.0.1"),
            "broker_port": int(getattr(args, "broker_port", None) or BROKER_PORT),
            "broker_local_port": int(
                getattr(args, "broker_local_port", None) or BROKER_LOCAL_FORWARD_PORT
            ),
            "broker_package": str(
                getattr(args, "broker_package", None) or MANIFOLD_BROKER_PACKAGE
            ),
            "broker_activity": str(
                getattr(args, "broker_activity", None) or MANIFOLD_BROKER_ACTIVITY
            ),
            "makepad_package": str(
                getattr(args, "makepad_package", None) or MAKEPAD_ANDROID_PACKAGE
            ),
            "makepad_activity": str(
                getattr(args, "makepad_activity", None) or MAKEPAD_ANDROID_XR_ACTIVITY
            ),
            "descriptor": str(descriptor_path or ""),
        },
        "summary": summary,
        "checks": checks,
    }


def validate_companion_readiness_report(report: dict[str, Any]) -> dict[str, Any]:
    checks = [row for row in report.get("checks", []) if isinstance(row, dict)]
    failures: list[str] = []
    if report.get("$schema") != HOSTESS_COMPANION_READINESS_SCHEMA:
        failures.append("unsupported readiness report schema")
    if not checks:
        failures.append("readiness report must contain checks")
    invalid_status = [
        str(row.get("check_id") or "<unknown>")
        for row in checks
        if row.get("status") not in VALID_READINESS_STATUSES
    ]
    if invalid_status:
        failures.append(f"checks with unsupported status: {', '.join(invalid_status)}")
    blocking_failures = [
        str(row.get("check_id") or "<unknown>")
        for row in checks
        if row.get("required") is True and row.get("status") == "fail"
    ]
    if blocking_failures:
        failures.append(f"blocking checks failed: {', '.join(blocking_failures)}")
    expected_status = "fail" if blocking_failures else ("warn" if any_warn(checks) else "pass")
    if report.get("status") != expected_status:
        failures.append(
            f"report status {report.get('status')!r} did not match expected {expected_status!r}"
        )
    return {
        "$schema": HOSTESS_COMPANION_READINESS_VALIDATION_SCHEMA,
        "status": "pass" if not failures else "fail",
        "report_status": report.get("status"),
        "blocking_failures": blocking_failures,
        "check_count": len(checks),
        "errors": failures,
    }


def check_companion_descriptor(path: Path) -> dict[str, Any]:
    try:
        descriptor = load_json_object(path)
    except Exception as exc:
        return readiness_check(
            "check.descriptor.companion_module",
            "module_descriptor",
            "Companion module descriptor",
            "fail",
            True,
            str(exc),
            issue_codes=["hostess.issue.companion.descriptor_unreadable"],
        )
    schema = descriptor.get("schema")
    module_id = descriptor.get("module_id")
    family = descriptor.get("family")
    status = (
        "pass"
        if schema == GUI_COMPANION_MODULE_DESCRIPTOR_SCHEMA
        and module_id == READINESS_DESCRIPTOR_MODULE_ID
        and family == "readiness_preconditions"
        else "fail"
    )
    return readiness_check(
        "check.descriptor.companion_module",
        "module_descriptor",
        "Companion module descriptor",
        status,
        True,
        "readiness module descriptor accepted" if status == "pass" else "descriptor mismatch",
        observed={
            "path": str(path),
            "schema": schema,
            "module_id": module_id,
            "family": family,
        },
        issue_codes=[] if status == "pass" else ["hostess.issue.companion.descriptor_mismatch"],
    )


def check_output_directory(path: Path) -> dict[str, Any]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        writable = path.exists() and path.is_dir()
    except OSError:
        writable = False
    return readiness_check(
        "check.host.output_directory",
        "host",
        "Output directory",
        "pass" if writable else "fail",
        True,
        str(path),
        observed={"path": str(path)},
        issue_codes=[] if writable else ["hostess.issue.companion.output_directory"],
    )


def check_executable(
    check_id: str,
    group: str,
    title: str,
    candidate: str,
    required: bool,
    which_func: Callable[[str], str | None],
    *,
    fallback_candidates: list[Path] | None = None,
) -> tuple[str | None, dict[str, Any]]:
    resolved = resolve_executable(candidate, which_func, fallback_candidates or [])
    status = "pass" if resolved else ("fail" if required else "warn")
    return resolved, readiness_check(
        check_id,
        group,
        title,
        status,
        required,
        resolved or f"{title} not found",
        observed={"requested": candidate, "resolved": resolved or ""},
        issue_codes=[] if resolved else [f"hostess.issue.companion.missing_{check_id.rsplit('.', 1)[-1]}"],
    )


def check_directory(
    check_id: str,
    group: str,
    title: str,
    candidate: str,
    required: bool,
) -> dict[str, Any]:
    resolved = Path(candidate) if candidate else None
    exists = bool(resolved and resolved.exists() and resolved.is_dir())
    status = "pass" if exists else ("fail" if required else "warn")
    return readiness_check(
        check_id,
        group,
        title,
        status,
        required,
        str(resolved) if resolved else f"{title} not configured",
        observed={"path": str(resolved or "")},
        issue_codes=[] if exists else [f"hostess.issue.companion.missing_{check_id.rsplit('.', 1)[-1]}"],
    )


def check_jdk(candidate: str, required: bool) -> dict[str, Any]:
    root = Path(candidate) if candidate else None
    java = root / "bin" / "java.exe" if root else None
    exists = bool(root and root.exists() and java and java.exists())
    status = "pass" if exists else ("fail" if required else "warn")
    return readiness_check(
        "check.tool.jdk",
        "toolchain",
        "JDK",
        status,
        required,
        str(root) if root else "JDK not configured",
        observed={"path": str(root or ""), "java": str(java or "")},
        issue_codes=[] if exists else ["hostess.issue.companion.missing_jdk"],
    )


def android_device_checks(
    args: argparse.Namespace,
    adb_path: str,
    serial: str,
    run_captured_func: Callable[..., subprocess.CompletedProcess[str]],
    *,
    device_required: bool,
    package_required: bool,
) -> list[dict[str, Any]]:
    package = str(getattr(args, "makepad_package", None) or MAKEPAD_ANDROID_PACKAGE)
    activity = str(getattr(args, "makepad_activity", None) or MAKEPAD_ANDROID_XR_ACTIVITY)
    checks = [
        command_check(
            "check.device.adb_state",
            "device",
            "ADB device state",
            [adb_path, "-s", serial, "get-state"],
            run_captured_func,
            required=device_required,
            stdout_contains="device",
        ),
        command_check(
            "check.device.model",
            "device",
            "Device model",
            [adb_path, "-s", serial, "shell", "getprop", "ro.product.model"],
            run_captured_func,
            required=False,
            stdout_required=True,
        ),
        command_check(
            "check.runtime.makepad_package",
            "runtime",
            "Makepad package installed",
            [adb_path, "-s", serial, "shell", "pm", "path", package],
            run_captured_func,
            required=package_required,
            stdout_contains="package:",
        ),
        command_check(
            "check.runtime.makepad_run_as",
            "runtime",
            "Makepad app-private access",
            [adb_path, "-s", serial, "shell", "run-as", package, "pwd"],
            run_captured_func,
            required=package_required,
            stdout_required=True,
        ),
        command_check(
            "check.runtime.makepad_activity",
            "runtime",
            "Makepad activity resolvable",
            [adb_path, "-s", serial, "shell", "cmd", "package", "resolve-activity", "--brief", "-n", activity],
            run_captured_func,
            required=package_required,
            stdout_required=True,
        ),
    ]
    return checks


def android_broker_checks(
    args: argparse.Namespace,
    adb_path: str,
    serial: str,
    run_captured_func: Callable[..., subprocess.CompletedProcess[str]],
    *,
    required: bool,
) -> list[dict[str, Any]]:
    package = str(getattr(args, "broker_package", None) or MANIFOLD_BROKER_PACKAGE)
    activity = str(getattr(args, "broker_activity", None) or MANIFOLD_BROKER_ACTIVITY)
    local_port = int(getattr(args, "broker_local_port", None) or BROKER_LOCAL_FORWARD_PORT)
    remote_port = int(getattr(args, "broker_port", None) or BROKER_PORT)
    return [
        command_check(
            "check.runtime.manifold_broker_package",
            "runtime",
            "Manifold broker package installed",
            [adb_path, "-s", serial, "shell", "pm", "path", package],
            run_captured_func,
            required=required,
            stdout_contains="package:",
        ),
        command_check(
            "check.runtime.manifold_broker_activity",
            "runtime",
            "Manifold broker activity resolvable",
            [
                adb_path,
                "-s",
                serial,
                "shell",
                "cmd",
                "package",
                "resolve-activity",
                "--brief",
                "-n",
                activity,
            ],
            run_captured_func,
            required=required,
            stdout_required=True,
        ),
        command_check(
            "check.runtime.manifold_broker_process",
            "runtime",
            "Manifold broker process",
            [adb_path, "-s", serial, "shell", "pidof", package],
            run_captured_func,
            required=required,
            stdout_required=True,
        ),
        broker_forward_check(
            adb_path,
            serial,
            local_port,
            remote_port,
            run_captured_func,
            required=required,
        ),
    ]


def broker_forward_check(
    adb_path: str,
    serial: str,
    local_port: int,
    remote_port: int,
    run_captured_func: Callable[..., subprocess.CompletedProcess[str]],
    *,
    required: bool,
) -> dict[str, Any]:
    command = [adb_path, "-s", serial, "forward", "--list"]
    result = run_captured_func(command, allow_failure=True)
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    expected = f"tcp:{local_port} tcp:{remote_port}"
    passed = result.returncode == 0 and expected in stdout
    return readiness_check(
        "check.network.broker_adb_forward",
        "network",
        "Broker ADB forward",
        "pass" if passed else ("fail" if required else "warn"),
        required,
        expected if passed else f"missing ADB forward {expected}",
        observed={
            "command": redact_command(command),
            "returncode": result.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "local_port": local_port,
            "remote_port": remote_port,
        },
        issue_codes=[] if passed else ["hostess.issue.companion.broker_adb_forward_missing"],
    )


def command_check(
    check_id: str,
    group: str,
    title: str,
    command: list[str],
    run_captured_func: Callable[..., subprocess.CompletedProcess[str]],
    *,
    required: bool,
    stdout_contains: str | None = None,
    stdout_required: bool = False,
) -> dict[str, Any]:
    try:
        result = run_captured_func(command, allow_failure=True)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        passed = result.returncode == 0
        if stdout_contains is not None:
            passed = passed and stdout_contains in stdout
        if stdout_required:
            passed = passed and bool(stdout.strip())
        status = "pass" if passed else ("fail" if required else "warn")
        evidence = stdout.strip() or stderr.strip() or f"returncode={result.returncode}"
        issue_codes = [] if passed else [f"hostess.issue.companion.{check_id.rsplit('.', 1)[-1]}"]
        return readiness_check(
            check_id,
            group,
            title,
            status,
            required,
            evidence,
            observed={
                "command": redact_command(command),
                "returncode": result.returncode,
                "stdout": stdout.strip(),
                "stderr": stderr.strip(),
            },
            issue_codes=issue_codes,
        )
    except Exception as exc:
        return readiness_check(
            check_id,
            group,
            title,
            "fail" if required else "warn",
            required,
            str(exc),
            observed={"command": redact_command(command)},
            issue_codes=[f"hostess.issue.companion.{check_id.rsplit('.', 1)[-1]}"],
        )


def check_broker_port(
    host: str,
    port: int,
    required: bool,
    broker_probe_func: Callable[[str, int, float], bool],
) -> dict[str, Any]:
    open_port = broker_probe_func(host, port, 0.25)
    status = "pass" if open_port else ("fail" if required else "warn")
    return readiness_check(
        "check.network.broker_port",
        "network",
        "Broker port",
        status,
        required,
        f"{host}:{port} is {'open' if open_port else 'not reachable'}",
        observed={"host": host, "port": port},
        issue_codes=[] if open_port else ["hostess.issue.companion.broker_port_closed"],
    )


def check_broker_forwarded_port(
    host: str,
    local_port: int,
    remote_port: int,
    required: bool,
    broker_probe_func: Callable[[str, int, float], bool],
) -> dict[str, Any]:
    open_port = broker_probe_func(host, local_port, 0.25)
    status = "pass" if open_port else ("fail" if required else "warn")
    return readiness_check(
        "check.network.broker_forwarded_port",
        "network",
        "Broker forwarded port",
        status,
        required,
        f"{host}:{local_port} -> tcp:{remote_port} is "
        f"{'open' if open_port else 'not reachable'}",
        observed={"host": host, "local_port": local_port, "remote_port": remote_port},
        issue_codes=[]
        if open_port
        else ["hostess.issue.companion.broker_forwarded_port_closed"],
    )


def readiness_check(
    check_id: str,
    group: str,
    title: str,
    status: str,
    required: bool,
    evidence: str,
    *,
    observed: dict[str, Any] | None = None,
    issue_codes: list[str] | None = None,
    remediation_action_ids: list[str] | None = None,
) -> dict[str, Any]:
    if status not in VALID_READINESS_STATUSES:
        raise ValueError(f"unsupported readiness status: {status}")
    severity = "info"
    if status == "fail" and required:
        severity = "error"
    elif status in {"fail", "warn"}:
        severity = "warning"
    return {
        "check_id": check_id,
        "group": group,
        "title": title,
        "status": status,
        "required": required,
        "severity": severity,
        "evidence": evidence,
        "observed": observed or {},
        "issue_codes": issue_codes or [],
        "remediation_action_ids": remediation_action_ids or [],
    }


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "pass": sum(1 for check in checks if check.get("status") == "pass"),
        "warn": sum(1 for check in checks if check.get("status") == "warn"),
        "fail": sum(1 for check in checks if check.get("status") == "fail"),
        "skipped": sum(1 for check in checks if check.get("status") == "skipped"),
        "blocking": sum(
            1
            for check in checks
            if check.get("required") is True and check.get("status") == "fail"
        ),
    }


def status_from_summary(summary: dict[str, int]) -> str:
    if summary.get("blocking", 0) > 0:
        return "fail"
    if summary.get("fail", 0) > 0 or summary.get("warn", 0) > 0:
        return "warn"
    return "pass"


def any_warn(checks: list[dict[str, Any]]) -> bool:
    return any(check.get("status") in {"warn", "fail"} for check in checks)


def resolve_executable(
    candidate: str,
    which_func: Callable[[str], str | None],
    fallback_candidates: list[Path],
) -> str | None:
    if candidate:
        path = Path(candidate)
        if path.exists():
            return str(path)
        found = which_func(candidate)
        if found:
            return found
    for fallback in fallback_candidates:
        if fallback.exists():
            return str(fallback)
    return None


def default_adb_candidates(args: argparse.Namespace) -> list[Path]:
    android_sdk = str(getattr(args, "android_sdk", None) or default_android_sdk())
    candidates = []
    if android_sdk:
        candidates.append(Path(android_sdk) / "platform-tools" / "adb.exe")
    return candidates


def default_android_sdk() -> str:
    import os

    return os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or ""


def default_jdk_home() -> str:
    import os

    return os.environ.get("JAVA_HOME") or ""


def broker_port_open(host: str, port: int, timeout_seconds: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON file did not contain an object: {path}")
    return value


def redact_command(command: list[str]) -> list[str]:
    return [str(part) for part in command]


def default_run_captured(
    command: list[str], *, allow_failure: bool = False
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result


def epoch_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


__all__ = [
    "GUI_COMPANION_MODULE_DESCRIPTOR_SCHEMA",
    "HOSTESS_COMPANION_READINESS_SCHEMA",
    "HOSTESS_COMPANION_READINESS_VALIDATION_SCHEMA",
    "build_companion_readiness_report",
    "run_companion_readiness",
    "validate_companion_readiness_report",
]
