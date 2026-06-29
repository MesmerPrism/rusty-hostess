"""Windows firewall and network-profile helpers for connectivity probes."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    completed_observed,
    issue_row,
    object_value,
)
from tools.hostessctl.runtime import run_captured as default_run_captured


CONNECTIVITY_FIREWALL_RULE_SCHEMA = "rusty.quest.connectivity_windows_firewall_rule.v1"
DEFAULT_QCL010_TCP_ECHO_PORT = 18766
DEFAULT_WPF_FIREWALL_PROGRAM = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "hostess-companion-wpf"
    / "bin"
    / "Debug"
    / "net9.0-windows"
    / "HostessCompanion.Wpf.exe"
)


def run_windows_firewall_rule(
    args: argparse.Namespace,
    *,
    run_captured_func: Any | None = None,
    clock_func: Any | None = None,
) -> int:
    """Plan, apply, verify, or remove a scoped Windows Firewall listener rule."""

    run_captured = run_captured_func or default_run_captured
    clock = clock_func or utc_now
    report = windows_firewall_rule_report(args, observed_at=clock())
    action = str(report.get("action") or "plan")

    if action in {"apply", "remove"}:
        if report["status"] == "blocked":
            result_key = "apply_result" if action == "apply" else "remove_result"
            report[result_key] = {
                "attempted": False,
                "returncode": None,
                "stdout": "",
                "stderr": "firewall rule plan was blocked",
            }
        else:
            result = run_captured(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    report["powershell"]["script"],
                ],
                allow_failure=True,
            )
            action_result = {
                "attempted": True,
                **completed_observed(result),
            }
            report["action_result"] = action_result
            if action == "apply":
                report["apply_result"] = action_result
            else:
                report["remove_result"] = action_result
            report["status"] = "pass" if result.returncode == 0 else "fail"

    if action in {"apply", "verify", "remove"} and report["status"] != "blocked":
        verification = verify_windows_firewall_rule_report(report, run_captured)
        report["verification"] = verification
        if action == "verify":
            report["status"] = verification["status"]
        elif action == "apply" and report["status"] == "pass":
            report["status"] = "pass" if verification["product_rule_verified"] is True else "warn"
        elif action == "remove" and report["status"] == "pass":
            report["status"] = "warn" if verification["product_rule_verified"] is True else "pass"

    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    out = str(getattr(args, "out", "") or "").strip()
    if out:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")

    if getattr(args, "fail_on_error", False) and report["status"] not in {"pass", "planned"}:
        return 2
    return 0


def windows_firewall_rule_report(args: argparse.Namespace, *, observed_at: datetime) -> dict[str, Any]:
    port = int(getattr(args, "port", DEFAULT_QCL010_TCP_ECHO_PORT) or DEFAULT_QCL010_TCP_ECHO_PORT)
    protocol = normalize_firewall_protocol(str(getattr(args, "protocol", "") or "TCP"))
    program = normalize_firewall_program_path(
        str(getattr(args, "program", "") or default_firewall_program(protocol)).strip()
    )
    profiles = normalize_firewall_profiles(str(getattr(args, "profile", "") or "Public"))
    remote_address = str(getattr(args, "remote_address", "") or "LocalSubnet").strip()
    rule_name = str(getattr(args, "rule_name", "") or "").strip()
    if not rule_name:
        rule_name = default_firewall_rule_name(port, protocol)
    action = firewall_rule_action(args)

    issues: list[dict[str, Any]] = []
    status = "planned"
    if not program:
        status = "blocked"
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.firewall_rule_program_missing",
                "error",
                "firewall rule plan requires a program path",
            )
        )
    if port <= 0 or port > 65535:
        status = "blocked"
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.firewall_rule_port_invalid",
                "error",
                "firewall rule plan requires a TCP port from 1 to 65535",
            )
        )
    if program and diagnostic_python_program_path(program):
        issues.append(
            issue_row(
                "hostess.issue.connectivity_probe.firewall_rule_program_diagnostic",
                "warning",
                "diagnostic Python listener rules are not product Hostess/WPF listener rules",
            )
        )

    if action == "remove":
        script = build_windows_firewall_rule_remove_script(rule_name=rule_name)
    elif action == "verify":
        script = build_windows_firewall_rule_verify_script(rule_name=rule_name)
    else:
        script = build_windows_firewall_rule_script(
            rule_name=rule_name,
            program=program,
            port=port,
            protocol=protocol,
            profiles=profiles,
            remote_address=remote_address,
        )
    probe_id = "QCL-010" if protocol == "TCP" else "QCL-080"
    connectivity_probe_args = [
        "connectivity-probe",
        "run",
        "--mode",
        "live",
        "--probe-id",
        probe_id,
    ]
    if protocol == "TCP":
        connectivity_probe_args.extend(["--tcp-echo-port", str(port)])
    else:
        connectivity_probe_args.extend(
            [
                "--udp-port",
                str(port),
                "--udp-listener-helper",
                program,
                "--udp-sender-source",
                "makepad-runtime",
            ]
        )

    return {
        "schema": CONNECTIVITY_FIREWALL_RULE_SCHEMA,
        "schema_version": 1,
        "observed_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "status": status,
        "action": action,
        "rule": {
            "name": rule_name,
            "direction": "Inbound",
            "action": "Allow",
            "enabled": True,
            "program": program,
            "protocol": protocol,
            "local_port": port,
            "profiles": profiles,
            "remote_address": remote_address,
            "replace_same_display_name": True,
            "scope_note": (
                "Allows only the selected program, selected protocol/port, "
                "profile set, and remote address scope."
            ),
        },
        "probe_usage": {
            "probe_id": probe_id,
            "connectivity_probe_args": connectivity_probe_args,
        },
        "powershell": {
            "requires_admin": True,
            "script": script,
            "command": (
                "powershell -NoProfile -ExecutionPolicy Bypass -Command "
                + ps_string_literal(script)
            ),
        },
        "issues": issues,
    }


def firewall_rule_action(args: argparse.Namespace) -> str:
    action = str(getattr(args, "action", "") or "").strip().lower()
    if action in {"plan", "apply", "verify", "remove"}:
        return action
    if getattr(args, "remove", False):
        return "remove"
    if getattr(args, "verify", False):
        return "verify"
    if getattr(args, "apply", False):
        return "apply"
    return "plan"


def default_firewall_program(protocol: str) -> str:
    return str(DEFAULT_WPF_FIREWALL_PROGRAM)


def default_firewall_rule_name(port: int, protocol: str) -> str:
    return (
        f"Rusty Hostess WPF QCL-010 TCP Echo {port}"
        if normalize_firewall_protocol(protocol) == "TCP"
        else f"Rusty Hostess WPF QCL-080 UDP Freshness {port}"
    )


def normalize_firewall_program_path(program: str) -> str:
    if not program:
        return ""
    candidate = Path(program)
    if candidate.is_absolute():
        return str(candidate)
    try:
        return str(candidate.resolve(strict=False))
    except OSError:
        return program


def normalize_firewall_profiles(raw_profiles: str) -> list[str]:
    allowed = {"Domain", "Private", "Public", "Any"}
    profiles: list[str] = []
    for part in raw_profiles.replace(";", ",").split(","):
        candidate = part.strip()
        if not candidate:
            continue
        normalized = candidate[:1].upper() + candidate[1:].lower()
        if normalized == "All":
            normalized = "Any"
        if normalized in allowed and normalized not in profiles:
            profiles.append(normalized)
    return profiles or ["Public"]


def normalize_firewall_protocol(raw_protocol: str) -> str:
    protocol = raw_protocol.strip().upper()
    if protocol not in {"TCP", "UDP"}:
        return "TCP"
    return protocol


def build_windows_firewall_rule_script(
    *,
    rule_name: str,
    program: str,
    port: int,
    protocol: str,
    profiles: list[str],
    remote_address: str,
) -> str:
    profile_text = ",".join(profiles)
    protocol_text = normalize_firewall_protocol(protocol)
    return " ".join(
        [
            "$ErrorActionPreference = 'Stop';",
            f"$ruleName = {ps_string_literal(rule_name)};",
            f"$program = {ps_string_literal(program)};",
            f"$port = {port};",
            f"$protocol = {ps_string_literal(protocol_text)};",
            f"$profile = {ps_string_literal(profile_text)};",
            f"$remoteAddress = {ps_string_literal(remote_address)};",
            "Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule;",
            "New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Enabled True -Program $program -Protocol $protocol -LocalPort $port -Profile $profile -RemoteAddress $remoteAddress | Out-Null;",
            "Get-NetFirewallRule -DisplayName $ruleName | Select-Object DisplayName,Enabled,Direction,Action,Profile | ConvertTo-Json -Compress;",
        ]
    )


def build_windows_firewall_rule_remove_script(*, rule_name: str) -> str:
    return " ".join(
        [
            "$ErrorActionPreference = 'Stop';",
            f"$ruleName = {ps_string_literal(rule_name)};",
            "$rules = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue;",
            "if ($rules) { $rules | Remove-NetFirewallRule; }",
            "[pscustomobject]@{DisplayName=$ruleName;Removed=($null -ne $rules)} | ConvertTo-Json -Compress;",
        ]
    )


def build_windows_firewall_rule_verify_script(*, rule_name: str) -> str:
    return " ".join(
        [
            "$ErrorActionPreference = 'Stop';",
            f"$ruleName = {ps_string_literal(rule_name)};",
            "Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | "
            "Select-Object DisplayName,Enabled,Direction,Action,Profile | ConvertTo-Json -Compress;",
        ]
    )


def verify_windows_firewall_rule_report(
    report: dict[str, Any],
    run_captured_func: Any,
) -> dict[str, Any]:
    rule = object_value(report.get("rule"))
    listener = {
        "program": str(rule.get("program") or ""),
        "protocol": str(rule.get("protocol") or "UDP"),
        "port": int(rule.get("local_port") or 0),
        "bind_host": "0.0.0.0",
        "rule_name": str(rule.get("name") or ""),
        "remote_address": str(rule.get("remote_address") or "LocalSubnet"),
    }
    network_profile = collect_windows_network_profile(run_captured_func, listener=listener)
    listener_firewall = object_value(network_profile.get("listener_firewall"))
    product_rule_verified = listener_firewall.get("product_rule_verified") is True
    allowed_on_active_profile = listener_firewall.get("allowed_on_active_profile") is True
    issue_codes: list[str] = []
    if not allowed_on_active_profile:
        issue_codes.append(
            "hostess.issue.connectivity_probe.no_udp_listener_firewall_allow_rule"
            if normalize_firewall_protocol(str(rule.get("protocol") or "UDP")) == "UDP"
            else "hostess.issue.connectivity_probe.no_tcp_listener_firewall_allow_rule"
        )
    if allowed_on_active_profile and not product_rule_verified:
        issue_codes.append(
            "hostess.issue.connectivity_probe.product_firewall_rule_not_verified"
        )
    return {
        "status": "pass" if product_rule_verified else "warn" if allowed_on_active_profile else "fail",
        "product_rule_verified": product_rule_verified,
        "allowed_on_active_profile": allowed_on_active_profile,
        "network_profile": network_profile,
        "listener_firewall": listener_firewall,
        "issue_codes": issue_codes,
    }


def collect_windows_network_profile(run_captured_func: Any, *, listener: dict[str, Any] | None = None) -> dict[str, Any]:
    listener = listener or {}
    listener_program = normalize_firewall_program_path(str(listener.get("program") or ""))
    listener_port = int(listener.get("port") or 0)
    listener_bind_host = str(listener.get("bind_host") or "")
    listener_protocol = normalize_firewall_protocol(str(listener.get("protocol") or "TCP"))
    listener_rule_name = str(listener.get("rule_name") or default_firewall_rule_name(listener_port, listener_protocol))
    listener_remote_address = str(listener.get("remote_address") or "LocalSubnet")
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"$listenerProgram = {ps_string_literal(listener_program)}; "
            f"$listenerPort = {listener_port}; "
            f"$listenerBindHost = {ps_string_literal(listener_bind_host)}; "
            f"$listenerProtocol = {ps_string_literal(listener_protocol)}; "
            f"$listenerRuleName = {ps_string_literal(listener_rule_name)}; "
            f"$listenerRemoteAddress = {ps_string_literal(listener_remote_address)}; "
            "$listenerProtocolNumber = if ($listenerProtocol -eq 'UDP') { 17 } else { 6 }; "
            "function Convert-Profiles($mask) { "
            "  if ($mask -eq 2147483647) { return @('Domain','Private','Public') } "
            "  $names = @(); "
            "  if (($mask -band 1) -ne 0) { $names += 'Domain' } "
            "  if (($mask -band 2) -ne 0) { $names += 'Private' } "
            "  if (($mask -band 4) -ne 0) { $names += 'Public' } "
            "  if ($names.Count -eq 0) { $names += 'All' } "
            "  return $names "
            "} "
            "function Test-PortMatch($ports, $port) { "
            "  if ($port -le 0) { return $false } "
            "  $text = [string]$ports; "
            "  if ([string]::IsNullOrWhiteSpace($text) -or $text -eq '*' -or $text -eq 'Any') { return $true } "
            "  foreach ($part in $text -split ',') { "
            "    $part = $part.Trim(); "
            "    if ($part -eq [string]$port) { return $true } "
            "    if ($part -match '^(\\d+)-(\\d+)$') { "
            "      $left = [int]$Matches[1]; $right = [int]$Matches[2]; "
            "      if ($port -ge $left -and $port -le $right) { return $true } "
            "    } "
            "  } "
            "  return $false "
            "} "
            "function Test-RemoteAddressMatch($remoteAddresses, $expectedRemoteAddress) { "
            "  $expected = [string]$expectedRemoteAddress; "
            "  if ([string]::IsNullOrWhiteSpace($expected)) { return $true } "
            "  $text = [string]$remoteAddresses; "
            "  if ([string]::IsNullOrWhiteSpace($text)) { return $false } "
            "  foreach ($part in $text -split ',') { "
            "    $candidate = $part.Trim(); "
            "    if ($candidate.Equals($expected, [System.StringComparison]::OrdinalIgnoreCase)) { return $true } "
            "  } "
            "  return $false "
            "} "
            "$connections = Get-NetConnectionProfile | "
            "Select-Object InterfaceAlias,"
            "Name,InterfaceIndex,"
            "@{Name='NetworkCategory';Expression={$_.NetworkCategory.ToString()}},"
            "@{Name='IPv4Connectivity';Expression={$_.IPv4Connectivity.ToString()}},"
            "@{Name='IPv6Connectivity';Expression={$_.IPv6Connectivity.ToString()}}; "
            "$firewall = Get-NetFirewallProfile | "
            "Select-Object Name,Enabled,"
            "@{Name='DefaultInboundAction';Expression={$_.DefaultInboundAction.ToString()}},"
            "@{Name='DefaultOutboundAction';Expression={$_.DefaultOutboundAction.ToString()}},"
            "@{Name='AllowInboundRules';Expression={$_.AllowInboundRules.ToString()}},"
            "NotifyOnListen,LogFileName,LogBlocked,LogAllowed; "
            "$listenerFirewall = $null; "
            "if ($listenerPort -gt 0) { "
            "  $activeProfiles = @($connections | ForEach-Object { $_.NetworkCategory } | "
            "    Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique); "
            "  $matches = @(); "
            "  try { "
            "    $policy = New-Object -ComObject HNetCfg.FwPolicy2; "
            "    foreach ($rule in $policy.Rules) { "
            "      try { "
            "        if (-not $rule.Enabled -or $rule.Direction -ne 1 -or $rule.Action -ne 1) { continue } "
            "        $app = [string]$rule.ApplicationName; "
            "        $programMatches = (-not [string]::IsNullOrWhiteSpace($app)) -and "
            "          $app.Equals($listenerProgram, [System.StringComparison]::OrdinalIgnoreCase); "
            "        $displayName = [string]$rule.Name; "
            "        $nameMatches = [string]::IsNullOrWhiteSpace($listenerRuleName) -or "
            "          $displayName.Equals($listenerRuleName, [System.StringComparison]::OrdinalIgnoreCase); "
            "        $ports = [string]$rule.LocalPorts; "
            "        $portScoped = (-not [string]::IsNullOrWhiteSpace($ports)) -and $ports -ne '*' -and $ports -ne 'Any'; "
            "        $portOnlyMatches = ([string]::IsNullOrWhiteSpace($app) -or $app -eq '*') -and $portScoped; "
            "        if (-not ($programMatches -or $portOnlyMatches)) { continue } "
            "        if (-not (($rule.Protocol -eq $listenerProtocolNumber) -or ($rule.Protocol -eq 256))) { continue } "
            "        if (-not (Test-PortMatch $ports $listenerPort)) { continue } "
            "        $remoteAddresses = [string]$rule.RemoteAddresses; "
            "        $remoteAddressMatches = Test-RemoteAddressMatch $remoteAddresses $listenerRemoteAddress; "
            "        $profiles = @(Convert-Profiles $rule.Profiles); "
            "        $profilesApply = $false; "
            "        foreach ($profile in $activeProfiles) { "
            "          if ($profiles -contains $profile -or $profiles -contains 'All') { $profilesApply = $true } "
            "        } "
            "        $productScopeMatches = $programMatches -and $nameMatches -and $remoteAddressMatches -and $profilesApply; "
            "        $matches += [pscustomobject]@{ "
            "          name=$displayName; profiles=$profiles; profile_mask=$rule.Profiles; "
            "          protocol=$rule.Protocol; local_ports=$ports; remote_addresses=$remoteAddresses; "
            "          application_name=$app; profiles_apply_to_active=$profilesApply; "
            "          program_matches=$programMatches; name_matches=$nameMatches; "
            "          remote_address_matches=$remoteAddressMatches; product_scope_matches=$productScopeMatches "
            "        }; "
            "      } catch {} "
            "    } "
            "    $productMatches = @($matches | Where-Object { $_.product_scope_matches }); "
            "    $listenerFirewall = [pscustomobject]@{ "
            "      program=$listenerProgram; protocol=$listenerProtocol; port=$listenerPort; bind_host=$listenerBindHost; "
            "      expected_rule_name=$listenerRuleName; expected_remote_address=$listenerRemoteAddress; "
            "      active_profiles=$activeProfiles; matching_rule_count=$matches.Count; "
            "      product_matching_rule_count=$productMatches.Count; product_rule_verified=($productMatches.Count -gt 0); "
            "      matching_rules=@($matches | Select-Object -First 20); "
            "      allowed_on_active_profile=[bool](@($matches | Where-Object { $_.profiles_apply_to_active }).Count -gt 0); "
            "      probe='windows_firewall_com_policy' "
            "    }; "
            "  } catch { "
            "    $listenerFirewall = [pscustomobject]@{ "
            "      program=$listenerProgram; protocol=$listenerProtocol; port=$listenerPort; bind_host=$listenerBindHost; "
            "      expected_rule_name=$listenerRuleName; expected_remote_address=$listenerRemoteAddress; "
            "      active_profiles=$activeProfiles; matching_rule_count=0; matching_rules=@(); "
            "      product_matching_rule_count=0; product_rule_verified=$false; "
            "      allowed_on_active_profile=$false; probe='windows_firewall_com_policy'; error=$_.Exception.Message "
            "    }; "
            "  } "
            "} "
            "[pscustomobject]@{connections=$connections; firewall=$firewall; listener_firewall=$listenerFirewall} | ConvertTo-Json -Compress -Depth 7"
        ),
    ]
    result = run_captured_func(command, allow_failure=True)
    if result.returncode != 0:
        return {}
    try:
        parsed = json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def network_profile_summary(profile: dict[str, Any]) -> str:
    connections = profile.get("connections")
    if isinstance(connections, dict):
        connection_rows = [connections]
    elif isinstance(connections, list):
        connection_rows = [row for row in connections if isinstance(row, dict)]
    else:
        connection_rows = []
    firewall = profile.get("firewall")
    if isinstance(firewall, dict):
        firewall_rows = [firewall]
    elif isinstance(firewall, list):
        firewall_rows = [row for row in firewall if isinstance(row, dict)]
    else:
        firewall_rows = []
    connection_text = ", ".join(
        f"{row.get('InterfaceAlias', 'unknown')}:{row.get('NetworkCategory', 'unknown')}"
        for row in connection_rows
    )
    firewall_text = ", ".join(
        f"{row.get('Name', 'unknown')} enabled={row.get('Enabled', 'unknown')} inbound={row.get('DefaultInboundAction', 'unknown')}"
        for row in firewall_rows
    )
    return "; ".join(part for part in [connection_text, firewall_text] if part) or "not_checked"


def windows_network_profile_status(profile: dict[str, Any]) -> tuple[str, list[str]]:
    if not profile:
        return "skipped", []
    active_profiles = active_windows_network_categories(profile)
    issue_codes: list[str] = []
    if "Public" in active_profiles:
        issue_codes.append("hostess.issue.connectivity_probe.windows_network_profile_public")
    return ("warn" if issue_codes else "pass"), issue_codes


def active_windows_network_categories(profile: dict[str, Any]) -> list[str]:
    connections = profile.get("connections")
    if isinstance(connections, dict):
        rows = [connections]
    elif isinstance(connections, list):
        rows = [row for row in connections if isinstance(row, dict)]
    else:
        rows = []
    categories: list[str] = []
    for row in rows:
        category = str(row.get("NetworkCategory") or "").strip()
        if category and category not in categories:
            categories.append(category)
    return categories


def windows_firewall_listener_status(
    listener_firewall: dict[str, Any],
    probe_result: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    if not listener_firewall or not listener_firewall.get("port"):
        return "skipped", []
    if listener_firewall.get("allowed_on_active_profile") is True:
        return "pass", []
    protocol = normalize_firewall_protocol(str(listener_firewall.get("protocol") or "TCP"))
    issue_codes = [
        "hostess.issue.connectivity_probe.no_udp_listener_firewall_allow_rule"
        if protocol == "UDP"
        else "hostess.issue.connectivity_probe.no_tcp_listener_firewall_allow_rule"
    ]
    probe_status = str((probe_result or {}).get("status") or "")
    if probe_status == "fail":
        return "fail", issue_codes
    return "warn", issue_codes


def windows_firewall_listener_summary(listener_firewall: dict[str, Any]) -> str:
    if not listener_firewall or not listener_firewall.get("port"):
        return "Windows listener firewall coverage not available"
    program = str(listener_firewall.get("program") or "unknown")
    protocol = normalize_firewall_protocol(str(listener_firewall.get("protocol") or "TCP"))
    port = listener_firewall.get("port")
    profiles = listener_firewall.get("active_profiles")
    profile_text = ",".join(str(profile) for profile in profiles) if isinstance(profiles, list) else "unknown"
    allowed = listener_firewall.get("allowed_on_active_profile")
    match_count = listener_firewall.get("matching_rule_count", 0)
    allowed_text = "allowed" if allowed is True else "no active-profile allow rule"
    return f"{program} {protocol}/{port} on {profile_text}: {allowed_text} ({match_count} matching rule(s))"


def diagnostic_python_program_path(program: Any) -> bool:
    value = str(program or "").replace("\\", "/").lower()
    return value.endswith("/python.exe") or value.endswith("/python") or value.endswith("python.exe")


def ps_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def utc_now() -> datetime:
    return datetime.now().astimezone()


__all__ = [
    "CONNECTIVITY_FIREWALL_RULE_SCHEMA",
    "DEFAULT_QCL010_TCP_ECHO_PORT",
    "DEFAULT_WPF_FIREWALL_PROGRAM",
    "active_windows_network_categories",
    "build_windows_firewall_rule_remove_script",
    "build_windows_firewall_rule_script",
    "build_windows_firewall_rule_verify_script",
    "collect_windows_network_profile",
    "default_firewall_program",
    "default_firewall_rule_name",
    "diagnostic_python_program_path",
    "firewall_rule_action",
    "network_profile_summary",
    "normalize_firewall_program_path",
    "normalize_firewall_profiles",
    "normalize_firewall_protocol",
    "ps_string_literal",
    "run_windows_firewall_rule",
    "verify_windows_firewall_rule_report",
    "windows_firewall_listener_status",
    "windows_firewall_listener_summary",
    "windows_firewall_rule_report",
    "windows_network_profile_status",
]
