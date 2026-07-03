"""Focused helpers split from connectivity_data_protocols.py."""

from __future__ import annotations

import argparse
import json
import re
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    adb_command,
    append_issue_once,
    base_report,
    check_row,
    collect_android_activity_launch_precondition,
    completed_observed,
    dedupe_issue_codes,
    ensure_probe_run_id,
    float_value,
    int_value,
    median,
    object_value,
    parse_json_string,
    percentile,
    read_android_json_with_retry,
    redact_command_for_report,
    round_float,
    sanitize_filename,
    trim_text,
)
from tools.hostessctl.connectivity_lan import (
    choose_host_ip,
    collect_device_identity,
    collect_host_ipv4_candidates,
    same_subnet_check,
)
from tools.hostessctl.connectivity_probe_live_reports import (
    live_qcl081_status,
    live_qcl083_status,
    live_qcl084_status,
    measurements_from_lsl_probe,
    measurements_from_osc_probe,
    measurements_from_zeromq_probe,
    protocol_topology_for_report,
)
from tools.hostessctl.platform_defaults import (
    ANDROID_PACKAGE,
    ANDROID_QCL083_OSC_ACTION,
    ANDROID_REMOTE_QCL083_OSC_EVIDENCE,
)
def parse_probe_json_stdout(stdout: str) -> dict[str, Any]:
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}

def protocol_topology_checks(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    host_ipv4_func: Any | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    device: dict[str, Any] = {
        "serial_redacted": True,
        "foreground_package": "not_checked",
        "adb_state": "not_provided",
        "wifi_interface": str(getattr(args, "wifi_interface", "wlan0") or "wlan0"),
        "wifi_ipv4": "",
        "wifi_prefix_length": None,
    }
    host_candidates: list[dict[str, Any]] = []
    host_ip = str(getattr(args, "host_ip", "") or "").strip()
    if getattr(args, "adb", None) and getattr(args, "serial", None):
        device = collect_device_identity(args, run_captured_func, checks, issues)
        host_candidates = (
            host_ipv4_func()
            if host_ipv4_func is not None
            else collect_host_ipv4_candidates(run_captured_func)
        )
        host_ip = host_ip or choose_host_ip(
            host_candidates,
            device.get("wifi_ipv4"),
            device.get("wifi_prefix_length"),
        )
        checks.append(
            check_row(
                "host.ipv4_candidate",
                "pass" if host_ip else "blocked",
                f"selected={host_ip or 'none'}",
                observed={"selected_ip": host_ip, "candidates": host_candidates},
                issue_codes=[] if host_ip else ["hostess.issue.connectivity_probe.host_ip_missing"],
            )
        )
        checks.append(same_subnet_check(host_ip, device.get("wifi_ipv4"), device.get("wifi_prefix_length")))
    else:
        checks.append(
            check_row(
                "device.adb_state",
                "skipped",
                "ADB serial not provided; protocol probe will not prove Quest topology",
            )
        )
    return checks, issues, device, host_candidates, host_ip

def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"

