"""Bluetooth QCL helpers for Hostess connectivity probes."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    check_status,
    check_row,
    adb_command,
    collect_android_activity_launch_precondition,
    completed_observed,
    empty_measurements,
    powershell_executable,
    read_android_json_with_retry,
    redact_command_for_report,
    sanitize_filename,
    strip_powershell_clixml_noise,
    trim_text,
    wait_for_json_file,
)
from tools.hostessctl.platform_defaults import (
    ANDROID_PACKAGE,
    ANDROID_QCL050_RFCOMM_ACTION,
    ANDROID_QCL051_BLE_GATT_ACTION,
    ANDROID_REMOTE_QCL050_RFCOMM_EVIDENCE,
    ANDROID_REMOTE_QCL051_BLE_GATT_EVIDENCE,
)

QCL051_SERVICE_UUID = "7b2a0001-7c4d-4f4c-9b16-515100515100"

QCL051_CONTROL_UUID = "7b2a0002-7c4d-4f4c-9b16-515100515100"

QCL051_STATUS_UUID = "7b2a0003-7c4d-4f4c-9b16-515100515100"

QCL050_RFCOMM_UUID = "7b2a0050-7c4d-4f4c-9b16-515100515100"

QCL051_HELPER_PROJECT = (
    Path(__file__).resolve().parents[1]
    / "connectivity_probe"
    / "qcl051_ble_gatt_client"
    / "qcl051-ble-gatt-client.csproj"
)

QCL050_HELPER_PROJECT = (
    Path(__file__).resolve().parents[1]
    / "connectivity_probe"
    / "qcl050_rfcomm_client"
    / "qcl050-rfcomm-client.csproj"
)

def collect_windows_bluetooth_status(run_captured_func: Any) -> dict[str, Any]:
    command = [
        powershell_executable(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "try { "
            "$adapter = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
            "  Where-Object { $_.FriendlyName -match 'Bluetooth Adapter|Bluetooth Radio|Realtek|Intel|Qualcomm' } | "
            "  Select-Object -First 1 Status,FriendlyName; "
            "$services = @(Get-Service bthserv,BluetoothUserService* -ErrorAction SilentlyContinue | "
            "  Select-Object Name,Status,StartType); "
            "$bthserv = $services | Where-Object { $_.Name -eq 'bthserv' } | Select-Object -First 1; "
            "$userRunning = @($services | Where-Object { $_.Name -like 'BluetoothUserService*' -and $_.Status.ToString() -eq 'Running' }).Count -gt 0; "
            "[pscustomobject]@{ "
            "  available=($null -ne $adapter); "
            "  adapter_status=$(if ($null -ne $adapter) { $adapter.Status } else { '' }); "
            "  adapter_name=$(if ($null -ne $adapter) { $adapter.FriendlyName } else { '' }); "
            "  bthserv_status=$(if ($null -ne $bthserv) { $bthserv.Status.ToString() } else { '' }); "
            "  user_service_running=$userRunning; "
            "  service_count=$services.Count; "
            "  address_redacted=$true "
            "} | ConvertTo-Json -Compress "
            "} catch { "
            "  [pscustomobject]@{ available=$false; state='Error'; error=$_.Exception.Message; error_type=$_.Exception.GetType().FullName; address_redacted=$true } | ConvertTo-Json -Compress "
            "}"
        ),
    ]
    result = run_captured_func(command, allow_failure=True)
    if result.returncode != 0:
        return {
            "available": False,
            "state": "CommandFailed",
            "error": result.stderr.strip(),
            "returncode": result.returncode,
            "address_redacted": True,
        }
    stdout = strip_powershell_clixml_noise(result.stdout)
    try:
        parsed = json.loads(stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"available": False, "state": "ParseError", "raw_stdout": stdout, "address_redacted": True}
    if not isinstance(parsed, dict):
        return {"available": False, "state": "UnexpectedShape", "address_redacted": True}
    parsed["address_redacted"] = True
    return parsed

def collect_quest_bluetooth_status(args: argparse.Namespace, run_captured_func: Any) -> dict[str, Any]:
    dumpsys = run_captured_func(
        adb_command(args, "shell", "dumpsys", "bluetooth_manager"),
        allow_failure=True,
    )
    commands = run_captured_func(
        adb_command(args, "shell", "cmd", "bluetooth_manager"),
        allow_failure=True,
    )
    parsed = parse_quest_bluetooth_dumpsys(dumpsys.stdout)
    parsed.update(
        {
            "available": dumpsys.returncode == 0,
            "address_redacted": True,
            "dumpsys_returncode": dumpsys.returncode,
            "cmd_returncode": commands.returncode,
            "shell_commands": parse_bluetooth_manager_commands(commands.stdout + "\n" + commands.stderr),
            "raw_summary": trim_text(redact_bluetooth_addresses(dumpsys.stdout), limit=500),
        }
    )
    return parsed

def run_qcl050_android_rfcomm_probe(
    args: argparse.Namespace,
    run_captured_func: Any,
    run_timeout_func: Any | None = None,
) -> dict[str, Any]:
    run_id = str(getattr(args, "run_id", "") or "qcl050-android-rfcomm")
    package_name = str(getattr(args, "hostess_android_package", "") or ANDROID_PACKAGE)
    message_count = max(1, int(getattr(args, "bluetooth_message_count", 3) or 3))
    timeout_seconds = max(3.0, float(getattr(args, "bluetooth_timeout_seconds", 20.0) or 20.0))
    remote_path = qcl050_remote_evidence_path(package_name)
    helper_out = Path("target") / "connectivity-probe" / f"{sanitize_filename(run_id)}.windows-rfcomm-client.json"
    helper_out.parent.mkdir(parents=True, exist_ok=True)

    launch_precondition = collect_android_activity_launch_precondition(args, run_captured_func)
    if launch_precondition.get("blocked"):
        return {
            "schema": "rusty.hostess.qcl050_rfcomm_payload_probe_join.v1",
            "status": "blocked",
            "run_id": run_id,
            "endpoint_source": "app_owned_android_rfcomm_server",
            "issue_codes": ["hostess.issue.connectivity_probe.rfcomm_runtime_not_launchable"],
            "android": {
                "launch_precondition": launch_precondition,
                "remote_evidence": remote_path,
                "evidence": {},
                "evidence_available": False,
            },
            "windows": {
                "helper_command": [],
                "helper_report": str(helper_out),
                "run": {"returncode": None, "stdout": "", "stderr": ""},
                "evidence": {},
                "evidence_available": False,
            },
        }

    run_captured_func(
        [
            str(getattr(args, "adb")),
            "-s",
            str(getattr(args, "serial")),
            "shell",
            "pm",
            "grant",
            package_name,
            "android.permission.BLUETOOTH_CONNECT",
        ],
        allow_failure=True,
    )
    run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "rm", "-f", remote_path],
        allow_failure=True,
    )
    run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "am", "force-stop", package_name],
        allow_failure=True,
    )
    android_start = run_captured_func(
        [
            str(getattr(args, "adb")),
            "-s",
            str(getattr(args, "serial")),
            "shell",
            "am",
            "start",
            "-a",
            ANDROID_QCL050_RFCOMM_ACTION,
            "-n",
            f"{package_name}/.MainActivity",
            "--es",
            "run_id",
            run_id,
            "--ei",
            "message_count",
            str(message_count),
            "--el",
            "timeout_ms",
            str(int(timeout_seconds * 1000)),
        ],
        allow_failure=True,
    )
    helper_command = qcl050_helper_command(args, helper_out=helper_out, run_id=run_id)
    if run_timeout_func is not None:
        helper_run = run_timeout_func(helper_command, timeout_seconds=timeout_seconds + 15.0)
    else:
        helper_run = run_captured_func(helper_command, allow_failure=True)
    helper_report = wait_for_json_file(helper_out, timeout_seconds=2.0)
    android_report = read_android_json_with_retry(
        args,
        remote_path,
        run_captured_func,
        timeout_seconds=timeout_seconds,
    )

    helper_status = str(helper_report.get("status") or "")
    android_status = str(android_report.get("status") or "")
    if helper_status == "blocked":
        status = "blocked"
    elif helper_run.returncode == 0 and helper_status == "pass" and android_status == "pass":
        status = "pass"
    else:
        status = "fail"
    issue_codes: list[str] = []
    for source in [helper_report, android_report]:
        for issue_code in source.get("issue_codes", []) or []:
            if issue_code not in issue_codes:
                issue_codes.append(str(issue_code))
        for issue in source.get("issues", []) or []:
            if isinstance(issue, dict) and issue.get("issue_code") and issue.get("issue_code") not in issue_codes:
                issue_codes.append(str(issue.get("issue_code")))
    return {
        "schema": "rusty.hostess.qcl050_rfcomm_payload_probe_join.v1",
        "status": status,
        "run_id": run_id,
        "endpoint_source": "app_owned_android_rfcomm_server",
        "issue_codes": issue_codes,
        "android": {
            "start": completed_observed(android_start),
            "remote_evidence": remote_path,
            "evidence": android_report,
            "evidence_available": bool(android_report),
        },
        "windows": {
            "helper_command": redact_command_for_report(helper_command),
            "helper_report": str(helper_out),
            "run": completed_observed(helper_run),
            "evidence": helper_report,
            "evidence_available": bool(helper_report),
        },
    }

def run_qcl051_android_ble_gatt_probe(
    args: argparse.Namespace,
    run_captured_func: Any,
    run_timeout_func: Any | None = None,
) -> dict[str, Any]:
    run_id = str(getattr(args, "run_id", "") or "qcl051-android-ble-gatt")
    reconnect_count = max(0, int(getattr(args, "bluetooth_reconnect_count", 0) or 0))
    sessions: list[dict[str, Any]] = []
    for session_index in range(reconnect_count + 1):
        session_run_id = run_id if session_index == 0 else f"{run_id}.reconnect-{session_index}"
        session = run_qcl051_android_ble_gatt_session(
            args,
            run_captured_func,
            run_timeout_func,
            run_id=session_run_id,
        )
        session["session_index"] = session_index
        session["session_role"] = "primary" if session_index == 0 else "reconnect"
        sessions.append(session)
        if session.get("status") != "pass":
            break
        if session_index < reconnect_count:
            time.sleep(0.75)

    primary = sessions[0] if sessions else {}
    completed_reconnects = sum(1 for session in sessions[1:] if session.get("status") == "pass")
    if any(session.get("status") == "blocked" for session in sessions):
        status = "blocked"
    elif sessions and all(session.get("status") == "pass" for session in sessions) and completed_reconnects >= reconnect_count:
        status = "pass"
    else:
        status = "fail"
    issue_codes: list[str] = []
    for session in sessions:
        for issue_code in session.get("issue_codes", []) or []:
            if issue_code not in issue_codes:
                issue_codes.append(str(issue_code))
    reconnect_cleanup_pass = reconnect_count > 0 and completed_reconnects >= reconnect_count and all(
        qcl051_session_cleanup_pass(session) for session in sessions
    )
    return {
        "schema": "rusty.hostess.qcl051_ble_gatt_payload_probe_join.v1",
        "status": status,
        "run_id": run_id,
        "endpoint_source": "app_owned_android_ble_gatt_server",
        "session_count": len(sessions),
        "sessions": sessions,
        "reconnect_attempts_requested": reconnect_count,
        "reconnect_attempts_completed": completed_reconnects,
        "reconnect_cleanup_pass": reconnect_cleanup_pass,
        "issue_codes": issue_codes,
        "android": primary.get("android", {}),
        "windows": primary.get("windows", {}),
    }

def run_qcl051_android_ble_gatt_session(
    args: argparse.Namespace,
    run_captured_func: Any,
    run_timeout_func: Any | None = None,
    *,
    run_id: str,
) -> dict[str, Any]:
    package_name = str(getattr(args, "hostess_android_package", "") or ANDROID_PACKAGE)
    message_count = max(1, int(getattr(args, "bluetooth_message_count", 3) or 3))
    timeout_seconds = max(3.0, float(getattr(args, "bluetooth_timeout_seconds", 20.0) or 20.0))
    remote_path = qcl051_remote_evidence_path(package_name)
    helper_out = Path("target") / "connectivity-probe" / f"{sanitize_filename(run_id)}.windows-ble-gatt-client.json"
    helper_out.parent.mkdir(parents=True, exist_ok=True)

    launch_precondition = collect_android_activity_launch_precondition(args, run_captured_func)
    if launch_precondition.get("blocked"):
        return {
            "schema": "rusty.hostess.qcl051_ble_gatt_payload_probe_join.v1",
            "status": "blocked",
            "run_id": run_id,
            "endpoint_source": "app_owned_android_ble_gatt_server",
            "issue_codes": ["hostess.issue.connectivity_probe.ble_gatt_runtime_not_launchable"],
            "android": {
                "launch_precondition": launch_precondition,
                "remote_evidence": remote_path,
                "evidence": {},
                "evidence_available": False,
            },
            "windows": {
                "helper_command": [],
                "helper_report": str(helper_out),
                "run": {"returncode": None, "stdout": "", "stderr": ""},
                "evidence": {},
                "evidence_available": False,
            },
        }

    for permission in [
        "android.permission.BLUETOOTH_CONNECT",
        "android.permission.BLUETOOTH_ADVERTISE",
    ]:
        run_captured_func(
            [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "pm", "grant", package_name, permission],
            allow_failure=True,
        )
    run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "rm", "-f", remote_path],
        allow_failure=True,
    )
    run_captured_func(
        [str(getattr(args, "adb")), "-s", str(getattr(args, "serial")), "shell", "am", "force-stop", package_name],
        allow_failure=True,
    )
    android_start = run_captured_func(
        [
            str(getattr(args, "adb")),
            "-s",
            str(getattr(args, "serial")),
            "shell",
            "am",
            "start",
            "-a",
            ANDROID_QCL051_BLE_GATT_ACTION,
            "-n",
            f"{package_name}/.MainActivity",
            "--es",
            "run_id",
            run_id,
            "--ei",
            "message_count",
            str(message_count),
            "--el",
            "timeout_ms",
            str(int(timeout_seconds * 1000)),
        ],
        allow_failure=True,
    )
    helper_command = qcl051_helper_command(args, helper_out=helper_out, run_id=run_id)
    if run_timeout_func is not None:
        helper_run = run_timeout_func(helper_command, timeout_seconds=timeout_seconds + 15.0)
    else:
        helper_run = run_captured_func(helper_command, allow_failure=True)
    helper_report = wait_for_json_file(helper_out, timeout_seconds=2.0)
    android_report = read_android_json_with_retry(
        args,
        remote_path,
        run_captured_func,
        timeout_seconds=timeout_seconds,
    )

    status = (
        "pass"
        if helper_run.returncode == 0
        and helper_report.get("status") == "pass"
        and android_report.get("status") == "pass"
        else "fail"
    )
    return {
        "schema": "rusty.hostess.qcl051_ble_gatt_payload_probe_join.v1",
        "status": status,
        "run_id": run_id,
        "endpoint_source": "app_owned_android_ble_gatt_server",
        "android": {
            "start": completed_observed(android_start),
            "remote_evidence": remote_path,
            "evidence": android_report,
            "evidence_available": bool(android_report),
        },
        "windows": {
            "helper_command": redact_command_for_report(helper_command),
            "helper_report": str(helper_out),
            "run": completed_observed(helper_run),
            "evidence": helper_report,
            "evidence_available": bool(helper_report),
        },
    }

def qcl051_helper_command(args: argparse.Namespace, *, helper_out: Path, run_id: str) -> list[str]:
    helper = str(getattr(args, "bluetooth_helper", "") or "").strip()
    base_args = [
        "--run-id",
        run_id,
        "--service-uuid",
        QCL051_SERVICE_UUID,
        "--control-uuid",
        QCL051_CONTROL_UUID,
        "--status-uuid",
        QCL051_STATUS_UUID,
        "--message-count",
        str(max(1, int(getattr(args, "bluetooth_message_count", 3) or 3))),
        "--timeout-seconds",
        str(max(3.0, float(getattr(args, "bluetooth_timeout_seconds", 20.0) or 20.0))),
        "--out",
        str(helper_out),
    ]
    if helper:
        helper_path = Path(helper)
        if helper_path.suffix.lower() == ".csproj":
            return ["dotnet", "run", "--project", str(helper_path), "--"] + base_args
        if helper_path.suffix.lower() == ".dll":
            return ["dotnet", str(helper_path)] + base_args
        return [helper] + base_args
    return ["dotnet", "run", "--project", str(QCL051_HELPER_PROJECT), "--"] + base_args

def qcl050_helper_command(args: argparse.Namespace, *, helper_out: Path, run_id: str) -> list[str]:
    helper = str(getattr(args, "bluetooth_helper", "") or "").strip()
    base_args = [
        "--run-id",
        run_id,
        "--service-uuid",
        QCL050_RFCOMM_UUID,
        "--message-count",
        str(max(1, int(getattr(args, "bluetooth_message_count", 3) or 3))),
        "--timeout-seconds",
        str(max(3.0, float(getattr(args, "bluetooth_timeout_seconds", 20.0) or 20.0))),
        "--out",
        str(helper_out),
    ]
    if helper:
        helper_path = Path(helper)
        if helper_path.suffix.lower() == ".csproj":
            return ["dotnet", "run", "--project", str(helper_path), "--"] + base_args
        if helper_path.suffix.lower() == ".dll":
            return ["dotnet", str(helper_path)] + base_args
        return [helper] + base_args
    return ["dotnet", "run", "--project", str(QCL050_HELPER_PROJECT), "--"] + base_args

def qcl050_remote_evidence_path(package_name: str) -> str:
    if package_name == ANDROID_PACKAGE:
        return ANDROID_REMOTE_QCL050_RFCOMM_EVIDENCE
    return f"/sdcard/Android/data/{package_name}/files/hostess-t/evidence/qcl050-rfcomm/latest.json"

def qcl051_remote_evidence_path(package_name: str) -> str:
    if package_name == ANDROID_PACKAGE:
        return ANDROID_REMOTE_QCL051_BLE_GATT_EVIDENCE
    return f"/sdcard/Android/data/{package_name}/files/hostess-t/evidence/qcl051-ble-gatt/latest.json"

def qcl051_payload_sessions(payload_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload_result:
        return []
    sessions = payload_result.get("sessions")
    if isinstance(sessions, list) and sessions:
        return [session for session in sessions if isinstance(session, dict)]
    return [payload_result]

def qcl051_session_android(session: dict[str, Any]) -> dict[str, Any]:
    evidence = session.get("android", {}).get("evidence", {}) if isinstance(session.get("android", {}), dict) else {}
    return evidence if isinstance(evidence, dict) else {}

def qcl051_session_windows(session: dict[str, Any]) -> dict[str, Any]:
    evidence = session.get("windows", {}).get("evidence", {}) if isinstance(session.get("windows", {}), dict) else {}
    return evidence if isinstance(evidence, dict) else {}

def qcl051_session_protocol_pass(session: dict[str, Any]) -> bool:
    android = qcl051_session_android(session)
    windows = qcl051_session_windows(session)
    expected = int(android.get("messages_expected") or windows.get("messages_requested") or 0)
    return (
        session.get("status") == "pass"
        and android.get("status") == "pass"
        and windows.get("status") == "pass"
        and expected > 0
        and int(android.get("messages_received") or 0) >= expected
        and int(windows.get("messages_completed") or 0) >= expected
    )

def qcl051_session_cleanup_pass(session: dict[str, Any]) -> bool:
    android = qcl051_session_android(session)
    return bool(android.get("advertising", {}).get("stopped")) and bool(android.get("gatt_server", {}).get("closed"))

def bluetooth_bytes_exchanged(payload_result: dict[str, Any] | None) -> int:
    if not payload_result:
        return 0
    total = 0
    for session in qcl051_payload_sessions(payload_result):
        android = qcl051_session_android(session)
        windows = qcl051_session_windows(session)
        total += int(android.get("bytes_received") or 0) + int(windows.get("bytes_read") or 0)
    return total

def bluetooth_measurements(payload_result: dict[str, Any] | None) -> dict[str, Any]:
    measurements = empty_measurements()
    measurements["bluetooth_bytes_exchanged"] = bluetooth_bytes_exchanged(payload_result)
    measurements["bluetooth_rtt_ms_p95"] = None
    if payload_result:
        p95_values: list[float] = []
        for session in qcl051_payload_sessions(payload_result):
            windows = qcl051_session_windows(session)
            helper_measurements = windows.get("measurements", {}) if isinstance(windows, dict) else {}
            p95 = helper_measurements.get("round_trip_ms_p95")
            if p95 is not None:
                try:
                    p95_values.append(float(p95))
                except (TypeError, ValueError):
                    pass
        measurements["bluetooth_rtt_ms_p95"] = max(p95_values) if p95_values else None
        measurements["reconnect_attempts"] = int(payload_result.get("reconnect_attempts_completed") or 0)
    return measurements

def parse_quest_bluetooth_dumpsys(text: str) -> dict[str, Any]:
    enabled_match = re.search(r"(?im)^\s*enabled:\s*(true|false)\s*$", text)
    state_match = re.search(r"(?im)^\s*state:\s*([A-Z_]+)\s*$", text)
    name_match = re.search(r"(?im)^\s*name:\s*(.+?)\s*$", text)
    connection_match = re.search(r"(?im)^\s*ConnectionState:\s*([A-Z_]+)\s*$", text)
    address_present = bool(re.search(r"(?im)^\s*address:\s*[0-9A-F:]{11,}\s*$", text))
    bonded_count = len(re.findall(r"(?m)^\s+XX:XX:XX:XX:[0-9A-F]{2}:[0-9A-F]{2}\b", text))
    return {
        "enabled": enabled_match.group(1).lower() == "true" if enabled_match else None,
        "state": state_match.group(1) if state_match else "",
        "name": name_match.group(1).strip() if name_match else "",
        "connection_state": connection_match.group(1) if connection_match else "",
        "address_present": address_present,
        "bonded_device_count": bonded_count,
    }

def parse_bluetooth_manager_commands(text: str) -> list[str]:
    commands: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in {"enable", "disable"} or stripped.startswith("wait-for-state"):
            commands.append(stripped.split()[0])
    return commands

def redact_bluetooth_addresses(text: str) -> str:
    return re.sub(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b", "XX:XX:XX:XX:XX:XX", text)

def windows_bluetooth_adapter_status(bluetooth: dict[str, Any]) -> tuple[str, list[str]]:
    if not bluetooth:
        return "blocked", ["hostess.issue.connectivity_probe.host_bluetooth_state_unavailable"]
    if bluetooth.get("available") is not True:
        return "blocked", ["hostess.issue.connectivity_probe.host_bluetooth_unavailable"]
    adapter_status = str(bluetooth.get("adapter_status") or "").strip().lower()
    if adapter_status == "ok":
        return "pass", []
    return "blocked", ["hostess.issue.connectivity_probe.host_bluetooth_adapter_not_ok"]

def windows_bluetooth_service_status(bluetooth: dict[str, Any]) -> tuple[str, list[str]]:
    if not bluetooth:
        return "blocked", ["hostess.issue.connectivity_probe.host_bluetooth_service_unavailable"]
    bthserv_status = str(bluetooth.get("bthserv_status") or "").strip().lower()
    if bthserv_status == "running":
        return "pass", []
    return "blocked", ["hostess.issue.connectivity_probe.host_bluetooth_service_not_running"]

def windows_bluetooth_adapter_summary(bluetooth: dict[str, Any]) -> str:
    if not bluetooth:
        return "Windows Bluetooth adapter state not available"
    if bluetooth.get("available") is not True:
        return f"Windows Bluetooth unavailable: {bluetooth.get('state') or bluetooth.get('error') or 'unknown'}"
    return (
        f"Windows Bluetooth adapter {bluetooth.get('adapter_status') or 'unknown'}; "
        f"name={bluetooth.get('adapter_name') or 'unknown'}; address_redacted=true"
    )

def windows_bluetooth_service_summary(bluetooth: dict[str, Any]) -> str:
    if not bluetooth:
        return "Windows Bluetooth service state not available"
    return (
        f"bthserv={bluetooth.get('bthserv_status') or 'unknown'}; "
        f"user_service_running={bool(bluetooth.get('user_service_running'))}; "
        f"service_count={bluetooth.get('service_count')}"
    )

def quest_bluetooth_adapter_status(bluetooth: dict[str, Any]) -> tuple[str, list[str]]:
    if not bluetooth or bluetooth.get("available") is not True:
        return "blocked", ["hostess.issue.connectivity_probe.quest_bluetooth_state_unavailable"]
    enabled = bluetooth.get("enabled")
    state = str(bluetooth.get("state") or "").strip().upper()
    if enabled is True and state == "ON":
        return "pass", []
    if enabled is False or state == "OFF":
        return "blocked", ["hostess.issue.connectivity_probe.quest_bluetooth_off"]
    return "warn", ["hostess.issue.connectivity_probe.quest_bluetooth_state_unexpected"]

def quest_bluetooth_adapter_summary(bluetooth: dict[str, Any]) -> str:
    if not bluetooth:
        return "Quest Bluetooth state not available"
    if bluetooth.get("available") is not True:
        return f"Quest Bluetooth unavailable: returncode={bluetooth.get('dumpsys_returncode')}"
    return (
        f"Quest Bluetooth enabled={bluetooth.get('enabled')}; "
        f"state={bluetooth.get('state') or 'unknown'}; "
        f"name={bluetooth.get('name') or 'unknown'}; "
        f"bonded_count={bluetooth.get('bonded_device_count')}; address_redacted=true"
    )

def topology_for_bluetooth_probe(probe_id: str) -> dict[str, Any]:
    return {
        "owner": "bluetooth",
        "network_provider": "bluetooth_classic_rfcomm" if probe_id == "QCL-050" else "bluetooth_le_gatt",
        "endpoint_direction": "bidirectional_low_rate_control",
        "requires_existing_wifi": False,
        "requires_adb": True,
        "requires_pairing": probe_id == "QCL-050",
        "requires_termux": False,
        "experimental": True,
    }

def bluetooth_transport_for_probe(probe_id: str) -> dict[str, Any]:
    if probe_id == "QCL-050":
        return {
            "family": "bluetooth_rfcomm",
            "route": "qcl050_rfcomm_control",
            "local_endpoint": "windows-rfcomm-helper",
            "remote_endpoint": "quest-bluetooth-app",
            "protocol_role": "fallback_control_probe",
            "payload_class": "bounded_low_rate_control",
            "endpoint_source": "passive_readiness",
        }
    return {
        "family": "ble_gatt",
        "route": "qcl051_ble_gatt_status",
        "local_endpoint": "windows-ble-helper",
        "remote_endpoint": "quest-bluetooth-app",
        "protocol_role": "fallback_discovery_status_probe",
        "payload_class": "tiny_status_control",
        "endpoint_source": "app_owned_android_ble_gatt_server",
    }

def qcl050_rfcomm_payload_checks(payload_result: dict[str, Any]) -> list[dict[str, Any]]:
    if payload_result.get("status") == "blocked" and payload_result.get("android", {}).get("launch_precondition"):
        launch_precondition = payload_result.get("android", {}).get("launch_precondition", {})
        return [
            check_row(
                "bluetooth.activity_launch_state",
                "blocked",
                "Quest app launch is blocked by VR lockscreen or system UI",
                observed=launch_precondition,
                issue_codes=["hostess.issue.connectivity_probe.rfcomm_runtime_not_launchable"],
            ),
            check_row(
                "bluetooth.pairing_bond_state",
                "skipped",
                "pairing behavior not tested because the Quest app-owned RFCOMM server could not launch",
                issue_codes=["hostess.issue.connectivity_probe.bluetooth_pairing_not_tested"],
            ),
            check_row(
                "protocol.rfcomm_control",
                "blocked",
                "RFCOMM socket exchange was not attempted because the Quest app-owned server could not launch",
                observed=payload_result,
                issue_codes=["hostess.issue.connectivity_probe.rfcomm_runtime_not_launchable"],
            ),
            check_row(
                "protocol.bluetooth_payload_exchange",
                "blocked",
                "bounded Bluetooth payload exchange was not attempted because the Quest app-owned server could not launch",
                issue_codes=["hostess.issue.connectivity_probe.bluetooth_payload_not_tested"],
            ),
        ]

    android = payload_result.get("android", {}).get("evidence", {}) if payload_result else {}
    windows = payload_result.get("windows", {}).get("evidence", {}) if payload_result else {}
    android_permissions = android.get("permissions", {}) if isinstance(android, dict) else {}
    selected_device = windows.get("selected_device", {}) if isinstance(windows, dict) else {}
    android_status = str(android.get("status") or "") if isinstance(android, dict) else ""
    windows_status = str(windows.get("status") or "") if isinstance(windows, dict) else ""
    messages_received = int(android.get("messages_received") or 0) if isinstance(android, dict) else 0
    messages_completed = int(windows.get("messages_completed") or 0) if isinstance(windows, dict) else 0
    messages_expected = int(android.get("messages_expected") or windows.get("messages_requested") or 0)
    protocol_pass = (
        payload_result.get("status") == "pass"
        and android_status == "pass"
        and windows_status == "pass"
        and messages_expected > 0
        and messages_received >= messages_expected
        and messages_completed >= messages_expected
    )
    service_blocked = payload_result.get("status") == "blocked" or windows_status == "blocked"
    permission_pass = bool(android_permissions.get("bluetooth_connect"))
    rfcomm_server = android.get("rfcomm_server", {}) if isinstance(android, dict) else {}
    cleanup_pass = bool(rfcomm_server.get("server_socket_closed"))
    blocked_issue_codes = list(payload_result.get("issue_codes", []) or []) or [
        "hostess.issue.connectivity_probe.rfcomm_service_not_found_or_unpaired"
    ]
    return [
        check_row(
            "bluetooth.permission_state",
            "pass" if permission_pass else "blocked",
            "Android Bluetooth Classic permission granted" if permission_pass else "Android Bluetooth Classic permission missing or evidence unavailable",
            observed=android_permissions,
            issue_codes=[] if permission_pass else ["hostess.issue.connectivity_probe.rfcomm_permission_missing"],
        ),
        check_row(
            "bluetooth.pairing_bond_state",
            "pass" if protocol_pass else "blocked" if service_blocked else "skipped",
            (
                "RFCOMM service opened and selected-device pairing metadata was recorded"
                if protocol_pass
                else "Windows could not discover/open the RFCOMM service; pairing or SDP visibility is likely required"
                if service_blocked
                else "pairing behavior not proven"
            ),
            observed={"requires_pairing": True, "selected_device": selected_device},
            issue_codes=[] if protocol_pass else blocked_issue_codes if service_blocked else ["hostess.issue.connectivity_probe.bluetooth_pairing_not_tested"],
        ),
        check_row(
            "protocol.rfcomm_control",
            "pass" if protocol_pass else "blocked" if service_blocked else "fail",
            (
                f"RFCOMM service discovered and {messages_completed}/{messages_expected} bounded payloads exchanged"
                if protocol_pass
                else "RFCOMM service was not discoverable/openable from Windows"
                if service_blocked
                else "RFCOMM service discovery or payload exchange failed"
            ),
            observed={"android": android, "windows": windows},
            issue_codes=[] if protocol_pass else blocked_issue_codes if service_blocked else ["hostess.issue.connectivity_probe.rfcomm_payload_failed"],
        ),
        check_row(
            "protocol.bluetooth_payload_exchange",
            "pass" if protocol_pass else "blocked" if service_blocked else "fail",
            (
                f"bounded RFCOMM payload exchange completed; bytes={bluetooth_bytes_exchanged(payload_result)}"
                if protocol_pass
                else "bounded Bluetooth payload exchange did not complete"
            ),
            issue_codes=[] if protocol_pass else blocked_issue_codes if service_blocked else ["hostess.issue.connectivity_probe.bluetooth_payload_not_tested"],
        ),
        check_row(
            "bluetooth.cleanup_state",
            "pass" if cleanup_pass else "warn",
            "Android RFCOMM server socket cleanup completed" if cleanup_pass else "Android RFCOMM cleanup evidence incomplete",
            observed=rfcomm_server,
            issue_codes=[] if cleanup_pass else ["hostess.issue.connectivity_probe.rfcomm_cleanup_incomplete"],
        ),
        check_row(
            "bluetooth.reconnect_cleanup",
            "skipped",
            "disconnect/reconnect rehearsal has not been run for QCL-050 yet",
            issue_codes=["hostess.issue.connectivity_probe.bluetooth_reconnect_not_tested"],
        ),
    ]

def qcl051_ble_gatt_payload_checks(payload_result: dict[str, Any]) -> list[dict[str, Any]]:
    if payload_result.get("status") == "blocked":
        launch_precondition = payload_result.get("android", {}).get("launch_precondition", {})
        return [
            check_row(
                "bluetooth.activity_launch_state",
                "blocked",
                "Quest app launch is blocked by VR lockscreen or system UI",
                observed=launch_precondition,
                issue_codes=["hostess.issue.connectivity_probe.ble_gatt_runtime_not_launchable"],
            ),
            check_row(
                "bluetooth.pairing_bond_state",
                "skipped",
                "pairing behavior not tested because the Quest app-owned BLE server could not launch",
                issue_codes=["hostess.issue.connectivity_probe.bluetooth_pairing_not_tested"],
            ),
            check_row(
                "protocol.ble_gatt_status",
                "blocked",
                "BLE/GATT service discovery was not attempted because the Quest app-owned server could not launch",
                observed=payload_result,
                issue_codes=["hostess.issue.connectivity_probe.ble_gatt_runtime_not_launchable"],
            ),
            check_row(
                "protocol.bluetooth_payload_exchange",
                "blocked",
                "bounded Bluetooth payload exchange was not attempted because the Quest app-owned server could not launch",
                issue_codes=["hostess.issue.connectivity_probe.bluetooth_payload_not_tested"],
            ),
            check_row(
                "bluetooth.cleanup_state",
                "skipped",
                "no BLE advertiser or GATT server was started",
                issue_codes=[],
            ),
            check_row(
                "bluetooth.reconnect_cleanup",
                "skipped",
                "disconnect/reconnect rehearsal has not been run for QCL-051 yet",
                issue_codes=["hostess.issue.connectivity_probe.bluetooth_reconnect_not_tested"],
            ),
        ]
    sessions = qcl051_payload_sessions(payload_result)
    android_reports = [qcl051_session_android(session) for session in sessions]
    windows_reports = [qcl051_session_windows(session) for session in sessions]
    android_permissions = [
        report.get("permissions", {}) for report in android_reports if isinstance(report.get("permissions", {}), dict)
    ]
    messages_received = sum(int(report.get("messages_received") or 0) for report in android_reports)
    messages_completed = sum(int(report.get("messages_completed") or 0) for report in windows_reports)
    messages_expected = sum(
        int(android.get("messages_expected") or windows.get("messages_requested") or 0)
        for android, windows in zip(android_reports, windows_reports)
    )
    protocol_pass = (
        payload_result.get("status") == "pass"
        and bool(sessions)
        and all(qcl051_session_protocol_pass(session) for session in sessions)
        and messages_expected > 0
        and messages_received >= messages_expected
        and messages_completed >= messages_expected
    )
    permission_pass = bool(android_permissions) and all(
        bool(permission.get("bluetooth_connect")) and bool(permission.get("bluetooth_advertise"))
        for permission in android_permissions
    )
    cleanup_pass = bool(sessions) and all(qcl051_session_cleanup_pass(session) for session in sessions)
    reconnect_requested = int(payload_result.get("reconnect_attempts_requested") or 0)
    reconnect_completed = int(payload_result.get("reconnect_attempts_completed") or 0)
    reconnect_cleanup_pass = (
        reconnect_requested > 0
        and reconnect_completed >= reconnect_requested
        and cleanup_pass
        and bool(payload_result.get("reconnect_cleanup_pass"))
    )
    selected_devices = [
        report.get("selected_device", {}) for report in windows_reports if isinstance(report.get("selected_device", {}), dict)
    ]
    cleanup_observed: dict[str, Any] = {}
    cleanup_observed["session_count"] = len(sessions)
    cleanup_observed["reconnect_attempts_requested"] = reconnect_requested
    cleanup_observed["reconnect_attempts_completed"] = reconnect_completed
    cleanup_observed["sessions"] = [
        {
            "session_index": session.get("session_index"),
            "session_role": session.get("session_role"),
            "status": session.get("status"),
            "advertising": qcl051_session_android(session).get("advertising", {}),
            "gatt_server": qcl051_session_android(session).get("gatt_server", {}),
        }
        for session in sessions
    ]
    return [
        check_row(
            "bluetooth.permission_state",
            "pass" if permission_pass else "blocked",
            "Android BLE permissions granted" if permission_pass else "Android BLE permissions missing or evidence unavailable",
            observed={"sessions": android_permissions},
            issue_codes=[] if permission_pass else ["hostess.issue.connectivity_probe.ble_gatt_permission_missing"],
        ),
        check_row(
            "bluetooth.pairing_bond_state",
            "pass" if protocol_pass else "skipped",
            "BLE/GATT payload exchange completed without paired-device dependency" if protocol_pass else "pairing behavior not proven",
            observed={
                "requires_pairing": False,
                "selected_devices": selected_devices,
            },
            issue_codes=[] if protocol_pass else ["hostess.issue.connectivity_probe.bluetooth_pairing_not_tested"],
        ),
        check_row(
            "protocol.ble_gatt_status",
            "pass" if protocol_pass else "fail",
            (
                f"BLE/GATT service discovered and {messages_completed}/{messages_expected} bounded payloads exchanged across {len(sessions)} session(s)"
                if protocol_pass
                else "BLE/GATT service discovery or payload exchange failed"
            ),
            observed={"sessions": sessions},
            issue_codes=[] if protocol_pass else ["hostess.issue.connectivity_probe.ble_gatt_payload_failed"],
        ),
        check_row(
            "protocol.bluetooth_payload_exchange",
            "pass" if protocol_pass else "fail",
            (
                f"bounded BLE/GATT write/read payload exchange completed; bytes={bluetooth_bytes_exchanged(payload_result)}"
                if protocol_pass
                else "bounded Bluetooth payload exchange did not complete"
            ),
            issue_codes=[] if protocol_pass else ["hostess.issue.connectivity_probe.bluetooth_payload_not_tested"],
        ),
        check_row(
            "bluetooth.cleanup_state",
            "pass" if cleanup_pass else "warn",
            "Android BLE advertiser and GATT server closed" if cleanup_pass else "Android BLE cleanup evidence incomplete",
            observed=cleanup_observed,
            issue_codes=[] if cleanup_pass else ["hostess.issue.connectivity_probe.ble_gatt_cleanup_incomplete"],
        ),
        check_row(
            "bluetooth.reconnect_cleanup",
            "pass" if reconnect_cleanup_pass else "skipped",
            (
                f"disconnect, cleanup, and rediscovery passed for {reconnect_completed}/{reconnect_requested} reconnect attempt(s)"
                if reconnect_cleanup_pass
                else "disconnect/reconnect rehearsal has not been run for QCL-051 yet"
            ),
            observed=cleanup_observed,
            issue_codes=[] if reconnect_cleanup_pass else ["hostess.issue.connectivity_probe.bluetooth_reconnect_not_tested"],
        ),
    ]

def live_bluetooth_status(checks: list[dict[str, Any]]) -> str:
    required = [
        check_status(checks, "host.bluetooth_adapter"),
        check_status(checks, "host.bluetooth_service"),
        check_status(checks, "device.bluetooth_adapter"),
    ]
    if any(status in {"blocked", "fail"} for status in required):
        return "blocked"
    statuses = [str(check.get("status") or "") for check in checks]
    if any(status == "fail" for status in statuses):
        return "fail"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if any(status in {"warn", "skipped"} for status in statuses):
        return "warn"
    if all(status == "pass" for status in statuses):
        return "pass"
    return "warn"

def bluetooth_protocol_check(probe_id: str, *, status: str) -> dict[str, Any]:
    if probe_id == "QCL-050":
        return check_row(
            "protocol.rfcomm_control",
            status,
            "Bluetooth Classic RFCOMM service/socket payload exchange not implemented in passive readiness probe",
            issue_codes=["hostess.issue.connectivity_probe.rfcomm_payload_not_tested"],
        )
    return check_row(
        "protocol.ble_gatt_status",
        status,
        "BLE/GATT advertise/scan/characteristic exchange not implemented in passive readiness probe",
        issue_codes=["hostess.issue.connectivity_probe.ble_gatt_payload_not_tested"],
    )
