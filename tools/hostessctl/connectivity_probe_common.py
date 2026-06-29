"""Shared helpers for Hostess connectivity probe reports."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

def percentile(values: list[int | float], percentile_value: int) -> int | float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(round(((percentile_value / 100.0) * (len(ordered) - 1))))
    return ordered[max(0, min(index, len(ordered) - 1))]

def median(values: list[int | float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[midpoint])
    return float((ordered[midpoint - 1] + ordered[midpoint]) / 2.0)

def round_float(value: int | float | None, digits: int = 3) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)

def parse_json_string(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}

def int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def float_value(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def dedupe_issue_codes(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

def adb_command(args: argparse.Namespace, *parts: str) -> list[str]:
    return [str(getattr(args, "adb", "adb")), "-s", str(getattr(args, "serial", "")), *parts]

def completed_observed(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {"returncode": result.returncode, "stdout": trim_text(result.stdout), "stderr": trim_text(result.stderr)}

def trim_text(text: str, limit: int = 800) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "...<truncated>"

def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

def list_value(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]

def shell_word(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9._:-]+", value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"

def powershell_executable() -> str:
    windows_powershell = Path(
        "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    return str(windows_powershell) if windows_powershell.exists() else "powershell"

def strip_powershell_clixml_noise(text: str) -> str:
    marker = text.find("#< CLIXML")
    if marker >= 0:
        text = text[:marker]
    lines = [line for line in text.splitlines() if not line.startswith("#< CLIXML")]
    return "\n".join(lines).strip()

def collect_android_activity_launch_precondition(args: argparse.Namespace, run_captured_func: Any) -> dict[str, Any]:
    result = run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "dumpsys", "activity", "activities"],
        allow_failure=True,
    )
    summary = trim_text(result.stdout, limit=1200)
    blocked = (
        "com.oculus.os.vrlockscreen/.SensorLockActivity" in result.stdout
        or "com.oculus.os.clearactivity/.ClearActivity" in result.stdout
    )
    return {
        "status": "blocked" if blocked else "pass",
        "blocked": blocked,
        "returncode": result.returncode,
        "summary": summary,
        "issue_code": "hostess.issue.connectivity_probe.ble_gatt_runtime_not_launchable" if blocked else "",
    }

def read_android_json_with_retry(
    args: argparse.Namespace,
    remote_path: str,
    run_captured_func: Any,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_stdout = ""
    while time.time() < deadline:
        result = run_captured_func(
            [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "cat", remote_path],
            allow_failure=True,
        )
        last_stdout = result.stdout
        if result.returncode == 0 and result.stdout.strip():
            try:
                return json.loads(strip_powershell_clixml_noise(result.stdout).strip())
            except json.JSONDecodeError:
                pass
        time.sleep(0.25)
    if last_stdout.strip():
        try:
            return json.loads(strip_powershell_clixml_noise(last_stdout).strip())
        except json.JSONDecodeError:
            return {}
    return {}

def sanitize_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "qcl051"

def redact_command_for_report(command: list[str]) -> list[str]:
    return list(command)

def wait_for_json_file(path: Path, *, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        data = read_json_file(path)
        if data:
            return data
        time.sleep(0.05)
    return {}

def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}

def empty_measurements() -> dict[str, Any]:
    return {
        "tcp_connect_ms": None,
        "websocket_echo_ms": None,
        "udp_packets_sent": None,
        "udp_packets_received": None,
        "udp_loss_percent": None,
        "lsl_discovery_ms": None,
        "lsl_samples_requested": None,
        "lsl_samples_received": None,
        "lsl_sample_loss_percent": None,
        "osc_messages_requested": None,
        "osc_messages_received": None,
        "osc_loss_percent": None,
        "osc_rtt_ms_p95": None,
        "osc_quest_processing_ms_p95": None,
        "osc_estimated_one_way_ms_p95": None,
        "osc_clock_offset_estimate_ms_median": None,
        "osc_clock_offset_jitter_ms_p95": None,
        "zeromq_messages_requested": None,
        "zeromq_messages_received": None,
        "zeromq_rtt_ms_p95": None,
        "zeromq_server_processing_ms_p95": None,
        "zeromq_estimated_one_way_ms_p95": None,
        "zeromq_clock_offset_estimate_ms_median": None,
        "zeromq_clock_offset_jitter_ms_p95": None,
        "throughput_mbps": None,
        "jitter_ms_p95": None,
        "reconnect_attempts": None,
    }

def check_row(
    name: str,
    status: str,
    evidence: str,
    *,
    observed: dict[str, Any] | None = None,
    notes: str = "",
    issue_codes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "evidence": evidence,
        "observed": observed or {},
        "notes": notes,
        "issue_codes": issue_codes or [],
    }

def issue_row(issue_code: str, severity: str, message: str) -> dict[str, str]:
    return {"issue_code": issue_code, "severity": severity, "message": message}

def check_status(checks: list[dict[str, Any]], name: str) -> str:
    for check in checks:
        if check.get("name") == name:
            return str(check.get("status") or "")
    return ""

def check_passed(report: dict[str, Any], name: str) -> bool:
    return check_status(list_value(report.get("checks")), name) == "pass"

def check_skipped(report: dict[str, Any], name: str) -> bool:
    return check_status(list_value(report.get("checks")), name) == "skipped"
