"""Live topology preflight reports for experimental QCL rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_lan import (
    collect_device_identity,
    collect_host_ipv4_candidates,
)
from tools.hostessctl.connectivity_probe_common import (
    adb_command,
    base_report,
    check_row,
    empty_measurements,
    ensure_probe_run_id,
    issue_row,
    powershell_executable,
    strip_powershell_clixml_noise,
)
from tools.hostessctl.connectivity_topology import topology_issues


LIVE_DIRECT_WIFI_PROBE_IDS = {"QCL-040", "QCL-041"}


def live_direct_wifi_topology_report(
    args: argparse.Namespace,
    *,
    run_captured_func: Any,
    clock_func: Any,
    host_ipv4_func: Any | None = None,
) -> dict[str, Any]:
    """Build a read-only live Wi-Fi Direct preflight report."""

    probe_id = str(getattr(args, "probe_id", "QCL-040") or "QCL-040").upper()
    if probe_id not in LIVE_DIRECT_WIFI_PROBE_IDS:
        raise SystemExit("live Wi-Fi Direct topology preflight supports QCL-040 or QCL-041")
    if not getattr(args, "adb", None) or not getattr(args, "serial", None):
        raise SystemExit("connectivity-probe live Wi-Fi Direct topology preflight requires --adb and --serial")

    observed_at = clock_func()
    ensure_probe_run_id(args, observed_at, probe_id)
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    windows_peer = probe_id == "QCL-041"

    device = collect_device_identity(args, run_captured_func, checks, issues)
    host_candidates = host_ipv4_func() if host_ipv4_func is not None else collect_host_ipv4_candidates(run_captured_func)
    quest_wifi_direct = collect_quest_wifi_direct_feature(args, run_captured_func)
    windows_wifi_direct = collect_windows_wifi_direct_status(run_captured_func) if windows_peer else {}
    windows_helper = (
        windows_wifi_direct_helper_summary(getattr(args, "windows_wifi_direct_helper_report", ""))
        if windows_peer
        else {}
    )

    feature_status = "pass" if quest_wifi_direct.get("feature_present") is True else "blocked"
    checks.append(
        check_row(
            "wifi_direct.feature",
            feature_status,
            (
                "Quest reports android.hardware.wifi.direct"
                if quest_wifi_direct.get("feature_present") is True
                else "Quest Wi-Fi Direct feature was not observed"
            ),
            observed=quest_wifi_direct,
            issue_codes=[] if feature_status == "pass" else ["hostess.issue.connectivity_probe.wifi_direct_feature_missing"],
        )
    )

    if windows_peer:
        windows_status = "pass" if windows_wifi_direct.get("available") is True else "blocked"
        checks.append(
            check_row(
                "windows.wifi_direct_api",
                windows_status,
                (
                    f"Wi-Fi Direct adapter count={windows_wifi_direct.get('adapter_count', 0)}"
                    if windows_status == "pass"
                    else "Windows Wi-Fi Direct adapter/API was not observed"
                ),
                observed=windows_wifi_direct,
                issue_codes=(
                    []
                    if windows_status == "pass"
                    else ["hostess.issue.connectivity_probe.wifi_direct_windows_driver_unavailable"]
                ),
            )
        )
        helper_status = str(windows_helper.get("check_status") or "skipped")
        checks.append(
            check_row(
                "windows.wifi_direct_peer_helper",
                helper_status,
                str(windows_helper.get("evidence") or "Windows Wi-Fi Direct peer helper report was not supplied"),
                observed=windows_helper,
                issue_codes=list(windows_helper.get("issue_codes") or []),
            )
        )
    else:
        checks.append(
            check_row(
                "android_phone.wifi_direct_peer",
                "blocked",
                "phone-peer Wi-Fi Direct harness is not configured for this Hostess run",
                observed={"configured": False, "source": "operator_required"},
                issue_codes=["hostess.issue.connectivity_probe.wifi_direct_phone_peer_missing"],
            )
        )

    checks.extend(wifi_direct_lifecycle_preflight_checks(windows_helper if windows_peer else {}))
    issues.extend(topology_issues(checks))
    if not any(issue.get("issue_code") == "hostess.issue.connectivity_probe.wifi_direct_live_topology_not_promoted" for issue in issues):
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.wifi_direct_live_topology_not_promoted",
                "warning",
                "QCL-040/QCL-041 live topology remains unpromoted until peer lifecycle and cleanup evidence exists",
            )
        )

    measurements = empty_measurements()
    measurements.update(
        {
            "wifi_direct_peer_count": 0,
            "group_formation_ms": None,
            "tcp_connect_ms": None,
            "cleanup_completed": False,
            "windows_helper_peer_requested": windows_helper.get("peer_connection_requested"),
            "windows_helper_group_formed": windows_helper.get("group_formed"),
            "windows_helper_socket_exchange_completed": windows_helper.get("socket_exchange_completed"),
        }
    )

    peer_class = "windows" if windows_peer else "android_phone"
    report = base_report(args, observed_at=observed_at)
    report.update(
        {
            "status": "blocked",
            "classification": "experimental",
            "topology": {
                "owner": "wifi_direct",
                "network_provider": "wifi_direct",
                "endpoint_direction": "peer_to_peer_group",
                "requires_existing_wifi": False,
                "requires_adb": True,
                "requires_pairing": True,
                "requires_termux": False,
                "experimental": True,
                "peer_class": peer_class,
            },
            "transport": {
                "family": "wifi_direct",
                "route": "wifi_direct_live_preflight",
                "protocol_role": "experimental_topology",
                "payload_class": "bounded_tcp_probe",
                "product_data_plane": False,
            },
            "device": device,
            "host": {
                "os": "windows",
                "ipv4_candidates": host_candidates,
                "windows_wifi_direct": windows_wifi_direct,
                "adb_provider": str(getattr(args, "adb", "")),
                "toolchain_profile": f"hostessctl.connectivity_probe.{probe_id.lower()}.live_preflight",
            },
            "checks": checks,
            "measurements": measurements,
            "issues": issues,
            "promotion": {
                "allowed": False,
                "target": "experimental topology descriptor",
                "reason": (
                    "Live Wi-Fi Direct topology requires peer discovery, group "
                    "formation, bounded socket exchange, and cleanup evidence."
                ),
            },
        }
    )
    return report


def collect_quest_wifi_direct_feature(args: argparse.Namespace, run_captured_func: Any) -> dict[str, Any]:
    command = adb_command(args, "shell", "pm", "list", "features")
    result = run_captured_func(command, allow_failure=True)
    stdout = str(result.stdout or "")
    stderr = str(result.stderr or "")
    feature_present = "android.hardware.wifi.direct" in stdout
    return {
        "feature_present": feature_present,
        "returncode": result.returncode,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "source": "adb_pm_list_features",
    }


def collect_windows_wifi_direct_status(run_captured_func: Any) -> dict[str, Any]:
    script = (
        "$ErrorActionPreference = 'SilentlyContinue'; "
        "$adapters = @(Get-NetAdapter -IncludeHidden | Where-Object { "
        "$_.Name -match 'Wi-Fi Direct' -or $_.InterfaceDescription -match 'Wi-Fi Direct' }); "
        "[pscustomobject]@{"
        "available=($adapters.Count -gt 0); "
        "adapter_count=$adapters.Count; "
        "adapter_names=@($adapters | Select-Object -ExpandProperty Name); "
        "source='get_netadapter_include_hidden'"
        "} | ConvertTo-Json -Compress -Depth 4"
    )
    command = [powershell_executable(), "-NoProfile", "-Command", script]
    result = run_captured_func(command, allow_failure=True)
    stdout = strip_powershell_clixml_noise(str(result.stdout or "")).strip()
    if result.returncode != 0:
        return {
            "available": False,
            "adapter_count": 0,
            "adapter_names": [],
            "source": "get_netadapter_include_hidden",
            "error": str(result.stderr or "").strip(),
        }
    try:
        parsed = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        return {
            "available": False,
            "adapter_count": 0,
            "adapter_names": [],
            "source": "get_netadapter_include_hidden",
            "error": str(exc),
        }
    return parsed if isinstance(parsed, dict) else {}


def windows_wifi_direct_helper_summary(path_text: str) -> dict[str, Any]:
    if not str(path_text or "").strip():
        return {
            "report_present": False,
            "check_status": "skipped",
            "issue_codes": [],
        }

    report_path = Path(path_text)
    if not report_path.exists():
        return {
            "report_present": False,
            "report_path": str(report_path),
            "check_status": "blocked",
            "evidence": "Windows Wi-Fi Direct peer helper report path does not exist",
            "issue_codes": ["hostess.issue.connectivity_probe.wifi_direct_windows_peer_helper_report_missing"],
        }

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "report_present": True,
            "report_path": str(report_path),
            "check_status": "blocked",
            "evidence": f"Windows Wi-Fi Direct peer helper report could not be read: {exc}",
            "issue_codes": ["hostess.issue.connectivity_probe.wifi_direct_windows_peer_helper_report_invalid"],
        }

    measurements = report.get("measurements") if isinstance(report.get("measurements"), dict) else {}
    events = report.get("events") if isinstance(report.get("events"), list) else []
    issues = report.get("issues") if isinstance(report.get("issues"), list) else []
    issue_codes = [
        str(issue.get("issue_code"))
        for issue in issues
        if isinstance(issue, dict) and str(issue.get("issue_code") or "")
    ]
    listener_ready = bool(measurements.get("connection_listener_ready"))
    advertisement_started = bool(measurements.get("advertisement_started"))
    peer_requested = bool(measurements.get("peer_connection_requested"))
    group_formed = bool(measurements.get("group_formed"))
    socket_exchange_completed = bool(measurements.get("socket_exchange_completed"))
    cleanup_completed = bool(measurements.get("cleanup_completed"))
    report_status = str(report.get("status") or "")
    helper_ready = listener_ready and advertisement_started and report_status in {"pass", "blocked"}
    if helper_ready:
        check_status = "pass"
        evidence = (
            "Windows Wi-Fi Direct helper advertised and accepted a peer request"
            if peer_requested
            else "Windows Wi-Fi Direct helper advertised/listened; no Quest peer connected before timeout"
        )
        helper_issue_codes: list[str] = []
    else:
        check_status = "blocked"
        evidence = "Windows Wi-Fi Direct helper did not prove listener readiness"
        helper_issue_codes = issue_codes or ["hostess.issue.connectivity_probe.wifi_direct_windows_peer_helper_failed"]

    return {
        "report_present": True,
        "report_path": str(report_path),
        "schema": str(report.get("schema") or ""),
        "report_status": report_status,
        "check_status": check_status,
        "evidence": evidence,
        "issue_codes": helper_issue_codes,
        "listener_ready": listener_ready,
        "advertisement_started": advertisement_started,
        "peer_connection_requested": peer_requested,
        "group_formed": group_formed,
        "endpoint_pair_count": measurements.get("endpoint_pair_count"),
        "socket_exchange_completed": socket_exchange_completed,
        "messages_sent": measurements.get("messages_sent"),
        "messages_received": measurements.get("messages_received"),
        "cleanup_completed": cleanup_completed,
        "event_count": len(events),
    }


def wifi_direct_lifecycle_preflight_checks(helper: dict[str, Any]) -> list[dict[str, Any]]:
    peer_requested = helper.get("peer_connection_requested") is True
    group_formed = helper.get("group_formed") is True
    socket_exchange_completed = helper.get("socket_exchange_completed") is True
    cleanup_completed = helper.get("cleanup_completed") is True
    group_cleanup_completed = cleanup_completed and group_formed
    helper_present = helper.get("report_present") is True

    permission_evidence = (
        "Windows helper is ready; Quest-side Wi-Fi Direct permission/group state is still required"
        if helper_present
        else "runtime Wi-Fi Direct permission state must come from the Quest-side topology harness"
    )
    peer_evidence = (
        "Windows helper observed a peer connection request"
        if peer_requested
        else (
            "Windows helper advertised/listened, but no Quest peer connected"
            if helper_present
            else "live Wi-Fi Direct peer discovery has not produced Hostess evidence"
        )
    )
    group_evidence = (
        "Windows helper observed Wi-Fi Direct endpoint pairs"
        if group_formed
        else (
            "group formation still waits for a Quest peer connection"
            if helper_present
            else "group formation waits for live peer discovery evidence"
        )
    )
    socket_evidence = (
        "bounded TCP probe exchanged across the Wi-Fi Direct group"
        if socket_exchange_completed
        else (
            "bounded TCP exchange still waits for a formed Wi-Fi Direct group"
            if helper_present
            else "bounded socket exchange waits for live Wi-Fi Direct group evidence"
        )
    )
    cleanup_evidence = (
        "Windows helper Wi-Fi Direct group cleanup completed"
        if group_cleanup_completed
        else (
            "Windows helper disposed resources; Wi-Fi Direct group cleanup still waits for group formation"
            if helper_present and cleanup_completed
            else (
                "cleanup still waits for live Wi-Fi Direct group evidence"
                if helper_present
                else "cleanup/restart safety waits for live Wi-Fi Direct group evidence"
            )
        )
    )

    cleanup_status = (
        "pass"
        if group_cleanup_completed
        else (
            "blocked"
            if group_formed
            else "skipped"
        )
    )

    return [
        check_row(
            "wifi_direct.permission_state",
            "skipped",
            permission_evidence,
            observed=helper,
            issue_codes=["hostess.issue.connectivity_probe.wifi_direct_runtime_harness_missing"],
        ),
        check_row(
            "wifi_direct.peer_discovery",
            "pass" if peer_requested else "blocked",
            peer_evidence,
            observed=helper,
            issue_codes=[] if peer_requested else ["hostess.issue.connectivity_probe.wifi_direct_live_peer_discovery_missing"],
        ),
        check_row(
            "wifi_direct.group_formation",
            "pass" if group_formed else ("blocked" if peer_requested else "skipped"),
            group_evidence,
            observed=helper,
            issue_codes=[] if group_formed else (
                ["hostess.issue.connectivity_probe.wifi_direct_group_formation_missing"] if peer_requested else []
            ),
        ),
        check_row(
            "topology.socket_exchange",
            "pass" if socket_exchange_completed else ("blocked" if group_formed else "skipped"),
            socket_evidence,
            observed=helper,
            issue_codes=[] if socket_exchange_completed else (
                ["hostess.issue.connectivity_probe.wifi_direct_socket_exchange_missing"] if group_formed else []
            ),
        ),
        check_row(
            "wifi_direct.cleanup",
            cleanup_status,
            cleanup_evidence,
            observed=helper,
            issue_codes=[] if group_cleanup_completed else (
                ["hostess.issue.connectivity_probe.wifi_direct_cleanup_missing"] if group_formed else []
            ),
        ),
    ]


__all__ = [
    "LIVE_DIRECT_WIFI_PROBE_IDS",
    "collect_quest_wifi_direct_feature",
    "collect_windows_wifi_direct_status",
    "live_direct_wifi_topology_report",
    "windows_wifi_direct_helper_summary",
]
