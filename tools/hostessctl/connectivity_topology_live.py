"""Live topology preflight reports for experimental QCL rows."""

from __future__ import annotations

import argparse
import json
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

    checks.extend(
        [
            check_row(
                "wifi_direct.permission_state",
                "skipped",
                "runtime Wi-Fi Direct permission state must come from the Quest-side topology harness",
                issue_codes=["hostess.issue.connectivity_probe.wifi_direct_runtime_harness_missing"],
            ),
            check_row(
                "wifi_direct.peer_discovery",
                "blocked",
                "live Wi-Fi Direct peer discovery has not produced Hostess evidence",
                issue_codes=["hostess.issue.connectivity_probe.wifi_direct_live_peer_discovery_missing"],
            ),
            check_row(
                "wifi_direct.group_formation",
                "skipped",
                "group formation waits for live peer discovery evidence",
            ),
            check_row(
                "topology.socket_exchange",
                "skipped",
                "bounded socket exchange waits for live Wi-Fi Direct group evidence",
            ),
            check_row(
                "wifi_direct.cleanup",
                "skipped",
                "cleanup/restart safety waits for live Wi-Fi Direct group evidence",
            ),
        ]
    )
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
        "$adapters = @(Get-NetAdapter | Where-Object { "
        "$_.Name -match 'Wi-Fi Direct' -or $_.InterfaceDescription -match 'Wi-Fi Direct' }); "
        "[pscustomobject]@{"
        "available=($adapters.Count -gt 0); "
        "adapter_count=$adapters.Count; "
        "adapter_names=@($adapters | Select-Object -ExpandProperty Name); "
        "source='get_netadapter'"
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
            "source": "get_netadapter",
            "error": str(result.stderr or "").strip(),
        }
    try:
        parsed = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        return {
            "available": False,
            "adapter_count": 0,
            "adapter_names": [],
            "source": "get_netadapter",
            "error": str(exc),
        }
    return parsed if isinstance(parsed, dict) else {}


__all__ = [
    "LIVE_DIRECT_WIFI_PROBE_IDS",
    "collect_quest_wifi_direct_feature",
    "collect_windows_wifi_direct_status",
    "live_direct_wifi_topology_report",
]
