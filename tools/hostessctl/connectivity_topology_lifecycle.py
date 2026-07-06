"""Wi-Fi Direct lifecycle evidence ingestion for QCL-040/QCL-041."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    append_issue_once,
    base_report,
    check_row,
    empty_measurements,
    list_value,
    object_value,
    read_json_file,
)
from tools.hostessctl.connectivity_topology import topology_issues
from tools.hostessctl.connectivity_topology_live import LIVE_DIRECT_WIFI_PROBE_IDS


WIFI_DIRECT_LIFECYCLE_SCHEMA = "rusty.quest.connectivity_wifi_direct_lifecycle.v1"
WINDOWS_LEGACY_AP_SCHEMA = "rusty.quest.qcl041.windows_legacy_ap_probe.v1"
WINDOWS_LEGACY_AP_HELPER_SCHEMA = "rusty.hostess.windows.qcl041_wifi_direct_legacy_ap.v1"
QUEST_ACTIVE_WIFI_CLIENT_SCHEMA = "rusty.quest.qcl030.local_only_hotspot_probe.v1"
LIVE_EVIDENCE_TIERS = {
    "quest_runtime",
    "hostess_harness",
    "product_harness",
    "product_owned",
}
AGENT_BOARD_MANAGER = "Agent Board"
QUEST_LEASE_RESOURCE_PREFIX = "quest:"
PLACEHOLDER_TOKENS = {
    "",
    "<quest-lease-id>",
    "LEASE_ID_FROM_RESERVE_OUTPUT",
}
PLACEHOLDER_SERIAL_TOKENS = {
    "",
    "<quest-serial>",
    "QUEST_SERIAL_FROM_ADB_DEVICES",
}
PLACEHOLDER_ID_TOKENS = {
    "",
    "<wifi-direct-lifecycle-run-id>",
    "<wifi-direct-peer-harness-id>",
}


def wifi_direct_lifecycle_probe_report(
    args: argparse.Namespace,
    *,
    observed_at: datetime,
) -> dict[str, Any]:
    """Build a QCL-040/QCL-041 topology report from a lifecycle evidence artifact."""

    probe_id = str(getattr(args, "probe_id", "") or "QCL-040").upper()
    if probe_id not in LIVE_DIRECT_WIFI_PROBE_IDS:
        raise SystemExit("Wi-Fi Direct lifecycle evidence supports QCL-040 or QCL-041")
    artifact_path = Path(str(getattr(args, "wifi_direct_lifecycle_report", "") or ""))
    windows_legacy_ap_path = str(getattr(args, "wifi_direct_windows_legacy_ap_report", "") or "")
    if windows_legacy_ap_path:
        if probe_id != "QCL-041":
            raise SystemExit("Windows legacy AP normalization supports QCL-041 only")
        report = base_report(args, observed_at=observed_at, probe_id=probe_id)
        report.update(
            windows_legacy_ap_body(
                read_json_file(Path(windows_legacy_ap_path)),
                artifact_path=windows_legacy_ap_path,
            )
        )
        return report
    artifact = read_json_file(artifact_path)
    windows_join_report_path = str(getattr(args, "wifi_direct_windows_join_report", "") or "")
    windows_join_report = read_optional_windows_join_report(windows_join_report_path)
    report = base_report(args, observed_at=observed_at, probe_id=probe_id)
    report.update(
        wifi_direct_lifecycle_body(
            artifact,
            artifact_path=str(artifact_path),
            probe_id=probe_id,
            windows_join_report=windows_join_report,
            windows_join_report_path=windows_join_report_path,
        )
    )
    return report


def run_wifi_direct_lifecycle_template(
    args: argparse.Namespace,
    *,
    clock_func: Any | None = None,
) -> int:
    """Write a non-promoting source artifact template for future lifecycle harnesses."""

    clock = clock_func or (lambda: datetime.now(UTC))
    probe_id = str(getattr(args, "probe_id", "") or "QCL-041").upper()
    if probe_id not in LIVE_DIRECT_WIFI_PROBE_IDS:
        raise SystemExit("Wi-Fi Direct lifecycle templates support QCL-040 or QCL-041")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    artifact = wifi_direct_lifecycle_template_artifact(
        probe_id=probe_id,
        observed_at=clock(),
    )
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def wifi_direct_lifecycle_template_artifact(
    *,
    probe_id: str,
    observed_at: datetime,
) -> dict[str, Any]:
    """Return the source-artifact shape expected from a real Wi-Fi Direct harness."""

    windows_peer = probe_id == "QCL-041"
    peer_class = "windows" if windows_peer else "android_phone"
    peer_phase = "windows_wifi_direct_api" if windows_peer else "android_phone_peer"
    required_phases = [
        "feature",
        peer_phase,
        "permission_state",
        "peer_discovery",
        "group_formation",
        "socket_exchange",
        "cleanup",
    ]
    return {
        "$schema": WIFI_DIRECT_LIFECYCLE_SCHEMA,
        "schema_version": 1,
        "probe_id": probe_id,
        "peer_class": peer_class,
        "evidence_tier": "template",
        "capture_kind": "template_wifi_direct_lifecycle",
        "live_evidence": False,
        "observed_at_utc": isoformat_utc(observed_at),
        "contract": {
            "required_phases": required_phases,
            "required_fields": [
                "run_id",
                "harness.harness_id",
                "harness.owner",
                "device.serial",
                "lease.resource",
                "lease.lease_id",
            ],
            "promotes_when": (
                "live_evidence is true, evidence_tier is a live tier, peer class "
                "matches the probe, the source run and harness are identified, "
                "the leased Quest serial matches device.serial, and all lifecycle "
                "phases pass"
            ),
            "non_promoting_template": True,
        },
        "run_id": "<wifi-direct-lifecycle-run-id>",
        "harness": {
            "harness_id": "<wifi-direct-peer-harness-id>",
            "owner": "external leased Wi-Fi Direct peer harness",
            "route": "external_peer_harness",
            "hostess_runs_harness": False,
            "writes_live_source_artifact": True,
        },
        "topology": {
            "owner": "wifi_direct",
            "network_provider": "wifi_direct",
            "endpoint_direction": "peer_to_peer_group",
            "peer_class": peer_class,
        },
        "device": {
            "model": "Quest",
            "serial": "<quest-serial>",
            "wifi_direct_role": "group_owner_or_client",
        },
        "host": {
            "os": "windows" if windows_peer else "android_phone_peer",
            "toolchain_profile": "hostessctl.connectivity_probe.wifi_direct_lifecycle_template",
        },
        "lease": {
            "manager": AGENT_BOARD_MANAGER,
            "resource": "quest:<quest-serial>",
            "lease_id": "<quest-lease-id>",
            "reserved_before_live_steps": False,
            "released_after_live_steps": False,
            "adb_server_lifecycle_lease_used": False,
            "reserve_command": (
                "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' "
                "reserve 'quest:<quest-serial>' --duration 45m "
                f"--task '{probe_id} direct Wi-Fi lifecycle evidence'"
            ),
            "release_command": (
                "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' "
                "release '<quest-lease-id>' --result done"
            ),
            "adb_server_lifecycle_policy": (
                "Use adb-server:lifecycle only for disruptive daemon lifecycle "
                "or Wi-Fi ADB setup/recovery. Ordinary ADB commands stay serial-scoped."
            ),
        },
        "lifecycle": {
            "feature": lifecycle_template_phase(
                "Quest Wi-Fi Direct feature observed by the leased harness"
            ),
            peer_phase: lifecycle_template_phase(
                (
                    "Windows Wi-Fi Direct API/adapter observed by the leased harness"
                    if windows_peer
                    else "Android-phone Wi-Fi Direct peer observed by the leased harness"
                )
            ),
            "permission_state": lifecycle_template_phase(
                "Wi-Fi Direct runtime permissions accepted"
            ),
            "peer_discovery": lifecycle_template_phase(
                "Wi-Fi Direct peer discovery completed with at least one peer",
                peer_count=0,
            ),
            "group_formation": lifecycle_template_phase(
                "Wi-Fi Direct group formation completed with recorded roles",
                local_role=None,
                peer_role=None,
            ),
            "socket_exchange": lifecycle_template_phase(
                "Bounded TCP probe exchanged across the Wi-Fi Direct group",
                protocol="tcp",
                payload_class="bounded_tcp_probe",
                bounded=True,
                messages_sent=0,
                messages_received=0,
            ),
            "cleanup": lifecycle_template_phase(
                "Wi-Fi Direct group cleanup completed",
                completed=False,
            ),
        },
        "measurements": {
            "tcp_connect_ms": None,
            "wifi_direct_peer_count": 0,
            "group_formation_ms": None,
        },
    }


def lifecycle_template_phase(summary: str, **extra: Any) -> dict[str, Any]:
    phase = {
        "status": "blocked",
        "evidence": f"pending live harness evidence: {summary}",
        "required": True,
    }
    phase.update(extra)
    return phase


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def wifi_direct_lifecycle_body(
    artifact: dict[str, Any],
    *,
    artifact_path: str,
    probe_id: str,
    windows_join_report: dict[str, Any] | None = None,
    windows_join_report_path: str = "",
) -> dict[str, Any]:
    windows_peer = probe_id == "QCL-041"
    artifact_peer_class = str(artifact.get("peer_class") or "").strip()
    windows_join_summary = windows_join_summary_validation(
        windows_join_report or {},
        windows_join_report_path,
        artifact,
    )
    quest_hosted_windows_join = (
        windows_peer
        and artifact_peer_class == "quest"
        and windows_join_summary["valid"]
    )
    expected_peer_class = (
        "quest"
        if quest_hosted_windows_join
        else ("windows" if windows_peer else "android_phone")
    )
    source_summary = lifecycle_source_summary(artifact, probe_id, expected_peer_class)
    lease_summary = lifecycle_lease_summary(artifact)
    lifecycle = object_value(artifact.get("lifecycle"))

    checks = [
        check_row(
            "wifi_direct.lifecycle_source",
            "pass" if source_summary["valid"] else "blocked",
            source_summary["evidence"],
            observed=source_summary,
            issue_codes=source_summary["issue_codes"],
        ),
        lifecycle_lease_check(lease_summary),
        lifecycle_check(
            lifecycle,
            "feature",
            "wifi_direct.feature",
            "Quest Wi-Fi Direct feature observed by lifecycle harness",
            "hostess.issue.connectivity_probe.wifi_direct_feature_missing",
        ),
        lifecycle_check(
            lifecycle,
            "windows_wifi_direct_api" if windows_peer else "android_phone_peer",
            "windows.wifi_direct_api" if windows_peer else "android_phone.wifi_direct_peer",
            (
                "Windows Wi-Fi Direct API/adapter observed by lifecycle harness"
                if windows_peer
                else "Android-phone Wi-Fi Direct peer observed by lifecycle harness"
            ),
            (
                "hostess.issue.connectivity_probe.wifi_direct_windows_driver_unavailable"
                if windows_peer
                else "hostess.issue.connectivity_probe.wifi_direct_phone_peer_missing"
            ),
        ),
        lifecycle_check(
            lifecycle,
            "permission_state",
            "wifi_direct.permission_state",
            "Wi-Fi Direct runtime permissions accepted",
            "hostess.issue.connectivity_probe.wifi_direct_permission_denied",
        ),
        (
            quest_hosted_windows_peer_discovery_check(windows_join_summary, lifecycle)
            if quest_hosted_windows_join
            else peer_discovery_check(lifecycle)
        ),
        group_formation_check(lifecycle),
        socket_exchange_check(lifecycle),
        cleanup_check(lifecycle),
    ]
    if windows_peer and (artifact_peer_class == "quest" or windows_join_report_path):
        checks.append(windows_join_summary_check(windows_join_summary))
    phase_pass = all(check.get("status") == "pass" for check in checks)
    issues = topology_issues(checks)
    if not phase_pass:
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.wifi_direct_live_topology_not_promoted",
            "warning",
            "QCL-040/QCL-041 lifecycle evidence is incomplete or not live/promotable",
        )

    artifact_measurements = object_value(artifact.get("measurements"))
    measurements = empty_measurements()
    measurements.update(
        {
            "tcp_connect_ms": artifact_measurements.get("tcp_connect_ms"),
            "wifi_direct_peer_count": artifact_measurements.get("wifi_direct_peer_count"),
            "group_formation_ms": artifact_measurements.get("group_formation_ms"),
            "cleanup_completed": cleanup_completed(lifecycle),
        }
    )
    for key, value in artifact_measurements.items():
        measurements.setdefault(key, value)

    topology = {
        "owner": "wifi_direct",
        "network_provider": "wifi_direct",
        "endpoint_direction": "peer_to_peer_group",
        "requires_existing_wifi": False,
        "requires_adb": True,
        "requires_pairing": True,
        "requires_termux": False,
        "experimental": True,
        "peer_class": expected_peer_class,
    }
    topology.update(object_value(artifact.get("topology")))
    topology["owner"] = "wifi_direct"
    topology["network_provider"] = "wifi_direct"
    if quest_hosted_windows_join:
        topology["peer_class"] = "windows"
        topology["peer_class_source"] = artifact_peer_class
        topology["endpoint_direction"] = "quest_hosted_windows_client_join"
        topology["windows_join_summary_report"] = windows_join_report_path
        topology["quest_group_owner_host"] = windows_join_summary["quest_group_owner_host"]
        topology["windows_client_ipv4"] = windows_join_summary["windows_client_ipv4"]
    else:
        topology["peer_class"] = expected_peer_class

    source_artifact_host = object_value(artifact.get("host"))
    host = {
        "os": "windows" if windows_peer else "android_phone_peer",
        "toolchain_profile": f"hostessctl.connectivity_probe.{probe_id.lower()}.wifi_direct_lifecycle",
    }
    if quest_hosted_windows_join:
        host["wifi_direct_role"] = "client"
        host["source_artifact_host"] = source_artifact_host
    else:
        host.update(source_artifact_host)

    device = object_value(artifact.get("device")) or {"model": "Quest", "wifi_direct_role": "group_owner_or_client"}

    return {
        "status": "pass" if phase_pass else "blocked",
        "classification": "experimental",
        "topology": topology,
        "transport": {
            "family": "wifi_direct",
            "route": "wifi_direct_lifecycle_artifact",
            "protocol_role": "experimental_topology",
            "payload_class": "bounded_tcp_probe",
            "product_data_plane": False,
        },
        "device": device,
        "host": host,
        "checks": checks,
        "measurements": measurements,
        "issues": issues,
        "artifacts": [
            {
                "kind": "wifi_direct_lifecycle_report",
                "path": artifact_path,
                "schema": source_summary["schema"],
                "evidence_tier": source_summary["evidence_tier"],
                "capture_kind": source_summary["capture_kind"],
                "source_run_id": source_summary["run_id"],
                "harness_id": source_summary["harness_id"],
                "harness_owner": source_summary["harness_owner"],
                "quest_lease_valid": lease_summary["valid"],
            }
        ]
        + (
            [
                {
                    "kind": "wifi_direct_windows_join_report",
                    "path": windows_join_report_path,
                    "schema": windows_join_summary["schema"],
                    "source_run_id": windows_join_summary["run_id"],
                }
            ]
            if windows_join_report_path
            else []
        ),
        "promotion": {
            "allowed": phase_pass,
            "target": "experimental topology descriptor",
            "reason": (
                "Live Wi-Fi Direct topology lifecycle is complete"
                if phase_pass
                else (
                    "Live Wi-Fi Direct topology requires peer discovery, group "
                    "formation, bounded socket exchange, and cleanup evidence."
                )
            ),
        },
    }


def windows_legacy_ap_body(summary: dict[str, Any], *, artifact_path: str) -> dict[str, Any]:
    helper_report_path = str(object_value(summary.get("artifacts")).get("helper_report") or "")
    client_report_path = str(object_value(summary.get("artifacts")).get("client_artifact") or "")
    helper_report = read_optional_json_report(helper_report_path)
    client_report = read_optional_json_report(client_report_path)
    summary_validation = windows_legacy_ap_summary_validation(summary)
    helper_validation = windows_legacy_ap_helper_validation(helper_report, summary)
    client_validation = windows_legacy_ap_client_validation(client_report, summary)
    cleanup_validation = windows_legacy_ap_cleanup_validation(summary, helper_report)
    socket_validation = windows_legacy_ap_socket_validation(
        summary,
        helper_report,
        client_report,
        summary_validation,
        helper_validation,
        client_validation,
    )
    phase_pass = all(
        validation["valid"]
        for validation in [
            summary_validation,
            helper_validation,
            client_validation,
            socket_validation,
            cleanup_validation,
        ]
    )
    checks = [
        check_row(
            "wifi_direct.legacy_ap_source",
            "pass" if summary_validation["valid"] else "blocked",
            summary_validation["evidence"],
            observed=summary_validation,
            issue_codes=summary_validation["issue_codes"],
        ),
        check_row(
            "wifi_direct.feature",
            "pass" if helper_validation["valid"] else "blocked",
            helper_validation["feature_evidence"],
            observed=helper_validation,
            issue_codes=helper_validation["issue_codes"],
        ),
        check_row(
            "windows.wifi_direct_api",
            "pass" if helper_validation["valid"] else "blocked",
            helper_validation["evidence"],
            observed=helper_validation,
            issue_codes=helper_validation["issue_codes"],
        ),
        check_row(
            "wifi_direct.permission_state",
            "pass" if summary_validation["permission_grants_ok"] else "blocked",
            summary_validation["permission_evidence"],
            observed={"permission_grants_ok": summary_validation["permission_grants_ok"]},
            issue_codes=[] if summary_validation["permission_grants_ok"] else [
                "hostess.issue.connectivity_probe.wifi_direct_permission_denied"
            ],
        ),
        check_row(
            "wifi_direct.peer_discovery",
            "pass" if client_validation["valid"] else "blocked",
            client_validation["peer_evidence"],
            observed=client_validation,
            issue_codes=client_validation["issue_codes"],
        ),
        check_row(
            "wifi_direct.group_formation",
            "pass" if client_validation["valid"] else "blocked",
            client_validation["join_evidence"],
            observed=client_validation,
            issue_codes=client_validation["issue_codes"],
        ),
        check_row(
            "topology.socket_exchange",
            "pass" if socket_validation["valid"] else "blocked",
            socket_validation["evidence"],
            observed=socket_validation,
            issue_codes=socket_validation["issue_codes"],
        ),
        check_row(
            "wifi_direct.cleanup",
            "pass" if cleanup_validation["valid"] else "blocked",
            cleanup_validation["evidence"],
            observed=cleanup_validation,
            issue_codes=cleanup_validation["issue_codes"],
        ),
        check_row(
            "windows.wifi_direct_legacy_ap",
            "pass" if phase_pass else "blocked",
            "Windows-owned Wi-Fi Direct LegacySettings AP is normalized as a QCL-041 topology input"
            if phase_pass
            else "Windows legacy AP report is incomplete for product topology routing",
            observed={
                "summary": summary_validation,
                "helper": helper_validation,
                "client": client_validation,
                "socket": socket_validation,
                "cleanup": cleanup_validation,
            },
            issue_codes=list(
                dict.fromkeys(
                    summary_validation["issue_codes"]
                    + helper_validation["issue_codes"]
                    + client_validation["issue_codes"]
                    + socket_validation["issue_codes"]
                    + cleanup_validation["issue_codes"]
                )
            ),
        ),
    ]
    issues = topology_issues(checks)
    if not phase_pass:
        append_issue_once(
            issues,
            "hostess.issue.connectivity_probe.wifi_direct_legacy_ap_not_promoted",
            "warning",
            "Windows legacy AP evidence is incomplete for QCL-041 product topology promotion",
        )

    measurements = empty_measurements()
    measurements.update(
        {
            "wifi_direct_peer_count": 1 if client_validation["quest_joined"] else 0,
            "udp_bytes_received": socket_validation["helper_udp_bytes"],
            "tcp_bytes_received": socket_validation["helper_tcp_bytes"],
            "tcp_ack_bytes": socket_validation["tcp_ack_bytes"],
            "cleanup_completed": cleanup_validation["valid"],
        }
    )
    owner_host = summary_validation["owner_host"] or helper_validation["owner_host"]
    quest_ipv4 = client_validation["quest_active_wifi_ipv4"]
    topology = {
        "owner": "wifi_direct",
        "network_provider": "windows_wifi_direct_legacy_ap",
        "endpoint_direction": "windows_legacy_ap_quest_client_join",
        "requires_existing_wifi": False,
        "requires_adb": True,
        "requires_pairing": True,
        "requires_termux": False,
        "experimental": True,
        "peer_class": "windows",
        "peer_class_source": "windows_legacy_ap",
        "windows_owner_host": owner_host,
        "quest_active_wifi_ipv4": quest_ipv4,
        "credential_sensitive_redacted": summary_validation["credential_sensitive_redacted"],
    }
    return {
        "status": "pass" if phase_pass else "blocked",
        "classification": "experimental",
        "topology": topology,
        "transport": {
            "family": "wifi_direct",
            "route": "windows_wifi_direct_legacy_ap",
            "protocol_role": "experimental_topology",
            "payload_class": "bounded_udp_tcp_probe",
            "product_data_plane": False,
        },
        "device": {
            "model": "Quest",
            "serial": summary_validation["serial"] or str(object_value(client_report.get("device")).get("serial") or ""),
            "wifi_direct_role": "legacy_ap_station",
            "wifi_ipv4": quest_ipv4,
        },
        "host": {
            "os": "windows",
            "wifi_direct_role": "legacy_ap_owner",
            "selected_owner_host": owner_host,
            "toolchain_profile": "hostessctl.connectivity_probe.qcl041.windows_wifi_direct_legacy_ap",
        },
        "checks": checks,
        "measurements": measurements,
        "issues": issues,
        "artifacts": [
            {
                "kind": "wifi_direct_windows_legacy_ap_report",
                "path": artifact_path,
                "schema": summary_validation["schema"],
                "source_run_id": summary_validation["run_id"],
                "credential_sensitive_redacted": summary_validation["credential_sensitive_redacted"],
            },
            {
                "kind": "wifi_direct_windows_legacy_ap_helper_report",
                "path": helper_report_path,
                "schema": helper_validation["schema"],
                "source_run_id": helper_validation["run_id"],
            },
            {
                "kind": "wifi_direct_windows_legacy_ap_client_report",
                "path": client_report_path,
                "schema": client_validation["schema"],
                "source_run_id": client_validation["run_id"],
            },
        ],
        "product_routing": {
            "qcl041_topology_input_ready": phase_pass,
            "qcl082_product_media_topology_input_ready": phase_pass,
            "endpoint_direction": "windows_legacy_ap_quest_client_join",
            "requires_product_media_fold_in": phase_pass,
            "credential_fields_preserved": False,
        },
        "promotion": {
            "allowed": phase_pass,
            "target": "experimental topology descriptor",
            "reason": (
                "Windows legacy AP topology is complete and ready as a QCL-082 product-media topology input"
                if phase_pass
                else (
                    "Windows legacy AP topology requires redacted credentials, Quest active-Wi-Fi join, "
                    "bounded UDP/TCP/ACK counters, transient profile cleanup, and previous WLAN restore."
                )
            ),
        },
    }


def lifecycle_lease_check(summary: dict[str, Any]) -> dict[str, Any]:
    if summary["valid"] and summary.get("coordination_mode") == "manual_supervised_no_agent_board":
        evidence = (
            "manual supervised QCL run recorded no Agent Board lease because Agent Board "
            "coordination was not requested; quest serial matched"
        )
    elif summary["valid"]:
        evidence = "Agent Board quest lease was reserved before live Wi-Fi Direct steps and released after cleanup"
    else:
        evidence = "live Wi-Fi Direct lifecycle evidence is missing an accepted Quest coordination receipt"
    return check_row(
        "wifi_direct.quest_lease",
        "pass" if summary["valid"] else "blocked",
        evidence,
        observed=summary,
        issue_codes=summary["issue_codes"],
    )


def lifecycle_lease_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    lease = object_value(artifact.get("lease") or artifact.get("agent_board_lease"))
    device = object_value(artifact.get("device"))
    manager = str(lease.get("manager") or lease.get("provider") or "").strip()
    resource = str(lease.get("resource") or "").strip()
    resource_serial = quest_serial_from_resource(resource)
    device_serial = quest_device_serial(device)
    lease_id = str(lease.get("lease_id") or lease.get("id") or "").strip()
    reserved_before = (
        lease.get("reserved_before_live_steps") is True
        or lease.get("reserved") is True
        or str(lease.get("reserve_status") or "").lower() == "pass"
    )
    released_after = (
        lease.get("released_after_live_steps") is True
        or str(lease.get("release_result") or "").lower() in {"done", "pass", "released"}
        or str(lease.get("release_status") or "").lower() == "pass"
    )
    adb_server_lifecycle_used = lease.get("adb_server_lifecycle_lease_used") is True
    serial_matches = bool(resource_serial and device_serial and resource_serial == device_serial)
    manual_supervised_no_agent_board = (
        manager == AGENT_BOARD_MANAGER
        and serial_matches
        and lease_id == "manual-no-lease"
        and not reserved_before
        and not released_after
    )

    issue_codes: list[str] = []
    if manager != AGENT_BOARD_MANAGER:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_quest_lease_missing")
    if not resource.startswith(QUEST_LEASE_RESOURCE_PREFIX) or "<" in resource:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_quest_lease_resource_invalid")
    if not device_serial:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_quest_device_serial_missing")
    if resource_serial and device_serial and resource_serial != device_serial:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_quest_lease_serial_mismatch")
    if lease_id in PLACEHOLDER_TOKENS or "<" in lease_id:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_quest_lease_id_missing")
    if not reserved_before and not manual_supervised_no_agent_board:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_quest_lease_not_reserved")
    if not released_after and not manual_supervised_no_agent_board:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_quest_lease_not_released")

    return {
        "manager": manager,
        "resource": resource,
        "quest_serial": resource_serial,
        "device_serial": device_serial,
        "serial_matches": serial_matches,
        "coordination_mode": (
            "manual_supervised_no_agent_board"
            if manual_supervised_no_agent_board
            else "agent_board_lease"
        ),
        "lease_id": lease_id,
        "reserved_before_live_steps": reserved_before,
        "released_after_live_steps": released_after,
        "adb_server_lifecycle_lease_used": adb_server_lifecycle_used,
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "reserve_command": str(lease.get("reserve_command") or ""),
        "release_command": str(lease.get("release_command") or ""),
        "adb_server_lifecycle_policy": str(lease.get("adb_server_lifecycle_policy") or ""),
    }


def quest_serial_from_resource(resource: str) -> str:
    if not resource.startswith(QUEST_LEASE_RESOURCE_PREFIX):
        return ""
    serial = resource[len(QUEST_LEASE_RESOURCE_PREFIX) :].strip()
    return "" if serial in PLACEHOLDER_SERIAL_TOKENS or "<" in serial else serial


def quest_device_serial(device: dict[str, Any]) -> str:
    for key in ("serial", "adb_serial"):
        serial = str(device.get(key) or "").strip()
        if serial and serial not in PLACEHOLDER_SERIAL_TOKENS and "<" not in serial:
            return serial
    return ""


def lifecycle_source_summary(
    artifact: dict[str, Any],
    probe_id: str,
    expected_peer_class: str,
) -> dict[str, Any]:
    schema = str(artifact.get("$schema") or artifact.get("schema") or "")
    evidence_tier = str(artifact.get("evidence_tier") or "").strip().lower()
    capture_kind = str(artifact.get("capture_kind") or "").strip()
    capture_kind_lower = capture_kind.lower()
    artifact_probe_id = str(artifact.get("probe_id") or "").upper()
    peer_class = str(
        artifact.get("peer_class")
        or object_value(artifact.get("topology")).get("peer_class")
        or ""
    ).strip()
    harness = object_value(artifact.get("harness") or artifact.get("source_harness"))
    run_id = str(
        artifact.get("run_id")
        or object_value(artifact.get("source")).get("run_id")
        or ""
    ).strip()
    harness_id = str(
        artifact.get("harness_id")
        or harness.get("harness_id")
        or harness.get("id")
        or ""
    ).strip()
    harness_owner = str(
        artifact.get("harness_owner")
        or harness.get("owner")
        or harness.get("authority_owner")
        or ""
    ).strip()
    declares_live = artifact.get("live_evidence") is True or capture_kind_lower.startswith("live")
    live_evidence = declares_live and evidence_tier in LIVE_EVIDENCE_TIERS

    issue_codes: list[str] = []
    if schema != WIFI_DIRECT_LIFECYCLE_SCHEMA:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_lifecycle_schema_invalid")
    if artifact_probe_id != probe_id:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_lifecycle_probe_mismatch")
    if peer_class != expected_peer_class:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_lifecycle_peer_mismatch")
    if not live_evidence:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_lifecycle_not_live")
    if run_id in PLACEHOLDER_ID_TOKENS or "<" in run_id:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_lifecycle_run_id_missing")
    if harness_id in PLACEHOLDER_ID_TOKENS or "<" in harness_id:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_lifecycle_harness_id_missing")
    if not harness_owner or "<" in harness_owner:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_lifecycle_harness_owner_missing")

    evidence = (
        f"schema={schema or 'missing'}; probe_id={artifact_probe_id or 'missing'}; "
        f"peer_class={peer_class or 'missing'}; evidence_tier={evidence_tier or 'missing'}; "
        f"capture_kind={capture_kind or 'missing'}; run_id={run_id or 'missing'}; "
        f"harness_id={harness_id or 'missing'}; harness_owner={harness_owner or 'missing'}"
    )
    return {
        "schema": schema,
        "probe_id": artifact_probe_id,
        "peer_class": peer_class,
        "evidence_tier": evidence_tier,
        "capture_kind": capture_kind,
        "run_id": run_id,
        "harness_id": harness_id,
        "harness_owner": harness_owner,
        "live_evidence": live_evidence,
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "evidence": evidence,
    }


def read_optional_windows_join_report(path_text: str) -> dict[str, Any]:
    if not path_text:
        return {}
    return read_optional_json_report(path_text)


def read_optional_json_report(path_text: str) -> dict[str, Any]:
    path = Path(str(path_text or ""))
    if not path_text:
        return {}
    try:
        return read_json_file(path)
    except Exception as ex:
        return {
            "schema": "",
            "status": "invalid",
            "issue": str(ex),
        }


def windows_legacy_ap_summary_validation(summary: dict[str, Any]) -> dict[str, Any]:
    artifacts = object_value(summary.get("artifacts"))
    results = object_value(summary.get("results"))
    schema = str(summary.get("schema") or summary.get("$schema") or "")
    run_id = str(summary.get("run_id") or "").strip()
    status = str(summary.get("status") or "").strip()
    serial = str(summary.get("serial") or object_value(summary.get("device")).get("serial") or "").strip()
    owner_host = str(summary.get("owner_host") or results.get("helper_ready_selected_owner_host") or "").strip()
    helper_report_path = str(artifacts.get("helper_report") or "")
    client_report_path = str(artifacts.get("client_artifact") or "")
    socket_bytes = int_value(summary.get("socket_bytes"))
    credential_sensitive_redacted = summary.get("credential_sensitive_redacted") is True
    permission_grants_ok = step_status(summary, "permission_grants") == "pass"
    issue_codes: list[str] = []
    if schema != WINDOWS_LEGACY_AP_SCHEMA:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_schema_invalid")
    if status != "pass":
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_not_pass")
    if not run_id:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_run_id_missing")
    if not serial:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_serial_missing")
    if not owner_host:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_owner_host_missing")
    if socket_bytes is None or socket_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_bounded_bytes_missing")
    if not credential_sensitive_redacted:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_credentials_not_redacted")
    if not permission_grants_ok:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_permission_denied")
    if not helper_report_path:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_helper_report_missing")
    if not client_report_path:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_client_report_missing")

    evidence = (
        f"schema={schema or 'missing'}; status={status or 'missing'}; run_id={run_id or 'missing'}; "
        f"serial={'present' if serial else 'missing'}; owner_host={owner_host or 'missing'}; "
        f"bounded_bytes={socket_bytes or 0}; credential_redacted={credential_sensitive_redacted}; "
        f"helper_report={'present' if helper_report_path else 'missing'}; "
        f"client_report={'present' if client_report_path else 'missing'}"
    )
    permission_evidence = (
        "runtime permission grant step passed for active-Wi-Fi client evidence"
        if permission_grants_ok
        else "runtime permission grant step is missing or blocked"
    )
    return {
        "schema": schema,
        "run_id": run_id,
        "status": status,
        "serial": serial,
        "owner_host": owner_host,
        "socket_bytes": socket_bytes,
        "credential_sensitive_redacted": credential_sensitive_redacted,
        "permission_grants_ok": permission_grants_ok,
        "permission_evidence": permission_evidence,
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "evidence": evidence,
    }


def windows_legacy_ap_helper_validation(
    helper: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    measurements = object_value(helper.get("measurements"))
    summary_run_id = str(summary.get("run_id") or "").strip()
    summary_owner_host = str(summary.get("owner_host") or object_value(summary.get("results")).get("helper_ready_selected_owner_host") or "").strip()
    schema = str(helper.get("schema") or helper.get("$schema") or "")
    run_id = str(helper.get("run_id") or "").strip()
    status = str(helper.get("status") or "").strip()
    role = str(helper.get("role") or "").strip()
    mode = str(helper.get("windows_wifidirect_mode") or "").strip()
    owner_host = str(helper.get("selected_owner_host") or "").strip()
    advertisement_started = measurements.get("advertisement_started") is True
    legacy_settings_enabled = helper.get("legacy_settings_enabled") is True
    autonomous_go = helper.get("autonomous_group_owner") is True
    credential_sensitive_redacted = helper.get("credential_sensitive_redacted") is True
    cleanup_completed = measurements.get("cleanup_completed") is True
    udp_bytes = int_value(measurements.get("udp_bytes")) or 0
    tcp_bytes = int_value(measurements.get("tcp_bytes")) or 0
    tcp_ack_bytes = int_value(measurements.get("tcp_ack_bytes")) or 0
    issues_present = bool(helper.get("issues") or helper.get("errors"))
    issue_codes: list[str] = []
    if schema != WINDOWS_LEGACY_AP_HELPER_SCHEMA:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_helper_schema_invalid")
    if status != "pass":
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_helper_not_pass")
    if summary_run_id and run_id != summary_run_id:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_run_mismatch")
    if role != "windows_wifi_direct_legacy_ap_owner":
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_helper_role_invalid")
    if mode != "autonomous_legacy_ap":
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_mode_invalid")
    if not legacy_settings_enabled:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_legacy_settings_disabled")
    if not autonomous_go:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_autonomous_go_missing")
    if not advertisement_started:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_advertisement_missing")
    if not owner_host:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_owner_host_missing")
    if summary_owner_host and owner_host and owner_host != summary_owner_host:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_owner_host_mismatch")
    if not credential_sensitive_redacted:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_credentials_not_redacted")
    if udp_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_udp_bytes_missing")
    if tcp_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_tcp_bytes_missing")
    if tcp_ack_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_tcp_ack_missing")
    if not cleanup_completed:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_helper_cleanup_missing")
    if issues_present:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_helper_report_has_issues")

    evidence = (
        f"schema={schema or 'missing'}; status={status or 'missing'}; role={role or 'missing'}; "
        f"mode={mode or 'missing'}; legacy_settings={legacy_settings_enabled}; "
        f"autonomous_go={autonomous_go}; owner_host={owner_host or 'missing'}; "
        f"udp_bytes={udp_bytes}; tcp_bytes={tcp_bytes}; tcp_ack_bytes={tcp_ack_bytes}; "
        f"cleanup={cleanup_completed}"
    )
    return {
        "schema": schema,
        "run_id": run_id,
        "owner_host": owner_host,
        "udp_bytes": udp_bytes,
        "tcp_bytes": tcp_bytes,
        "tcp_ack_bytes": tcp_ack_bytes,
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "evidence": evidence,
        "feature_evidence": (
            "Windows Wi-Fi Direct LegacySettings AP advertised with redacted credentials"
            if not issue_codes
            else "Windows Wi-Fi Direct LegacySettings AP helper evidence is incomplete"
        ),
    }


def windows_legacy_ap_client_validation(
    client: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    results = object_value(summary.get("results"))
    socket_matrix = object_value(client.get("socket_matrix"))
    schema = str(client.get("schema") or client.get("$schema") or "")
    run_id = str(client.get("run_id") or "").strip()
    summary_run_id = str(summary.get("run_id") or "").strip()
    status = str(client.get("status") or "").strip()
    join_mode = str(socket_matrix.get("client_join_mode") or "").strip()
    ssid_match = str(socket_matrix.get("client_active_wifi_ssid_match_status") or "").strip()
    client_network_bound = socket_matrix.get("client_network_bound") is True
    client_udp_bytes = int_value(socket_matrix.get("client_udp_sent_bytes")) or 0
    client_tcp_bytes = int_value(socket_matrix.get("client_tcp_sent_bytes")) or 0
    client_tcp_ack_bytes = int_value(socket_matrix.get("client_tcp_ack_bytes")) or 0
    quest_joined = results.get("quest_connected_to_windows_legacy_ap") is True
    quest_active_wifi_ipv4 = (
        str(results.get("quest_wifi_ipv4") or summary.get("quest_wifi_ipv4") or "").strip()
        or first_ipv4_from_text(str(socket_matrix.get("client_link_properties") or ""))
        or first_ipv4_from_text(str(results.get("quest_wifi_status_after_connect") or ""))
    )
    issue_codes: list[str] = []
    if schema != QUEST_ACTIVE_WIFI_CLIENT_SCHEMA:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_client_schema_invalid")
    if status != "pass":
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_client_not_pass")
    if summary_run_id and run_id != summary_run_id:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_run_mismatch")
    if not quest_joined:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_quest_join_missing")
    if join_mode != "active_wifi":
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_client_join_mode_invalid")
    if ssid_match != "matched":
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_client_ssid_mismatch")
    if not client_network_bound:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_client_network_not_bound")
    if not quest_active_wifi_ipv4:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_quest_ipv4_missing")
    if client_udp_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_client_udp_bytes_missing")
    if client_tcp_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_client_tcp_bytes_missing")
    if client_tcp_ack_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_client_tcp_ack_missing")

    peer_evidence = (
        f"Quest joined Windows legacy AP as active Wi-Fi client with IPv4 {quest_active_wifi_ipv4}"
        if quest_joined and quest_active_wifi_ipv4
        else "Quest active-Wi-Fi join evidence is missing or incomplete"
    )
    join_evidence = (
        "Quest active-Wi-Fi network was selected and bound for client socket traffic"
        if client_network_bound and join_mode == "active_wifi" and ssid_match == "matched"
        else "Quest active-Wi-Fi client did not prove matched network binding"
    )
    evidence = (
        f"schema={schema or 'missing'}; status={status or 'missing'}; run_id={run_id or 'missing'}; "
        f"join_mode={join_mode or 'missing'}; ssid_match={ssid_match or 'missing'}; "
        f"network_bound={client_network_bound}; quest_ipv4={quest_active_wifi_ipv4 or 'missing'}; "
        f"udp_sent={client_udp_bytes}; tcp_sent={client_tcp_bytes}; tcp_ack={client_tcp_ack_bytes}"
    )
    return {
        "schema": schema,
        "run_id": run_id,
        "quest_joined": quest_joined,
        "quest_active_wifi_ipv4": quest_active_wifi_ipv4,
        "client_udp_bytes": client_udp_bytes,
        "client_tcp_bytes": client_tcp_bytes,
        "client_tcp_ack_bytes": client_tcp_ack_bytes,
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "evidence": evidence,
        "peer_evidence": peer_evidence,
        "join_evidence": join_evidence,
    }


def windows_legacy_ap_socket_validation(
    summary: dict[str, Any],
    helper: dict[str, Any],
    client: dict[str, Any],
    summary_validation: dict[str, Any],
    helper_validation: dict[str, Any],
    client_validation: dict[str, Any],
) -> dict[str, Any]:
    expected_bytes = summary_validation["socket_bytes"] or int_value(helper.get("expected_bytes")) or 0
    helper_udp_bytes = helper_validation["udp_bytes"]
    helper_tcp_bytes = helper_validation["tcp_bytes"]
    tcp_ack_bytes = min_nonzero(
        helper_validation["tcp_ack_bytes"],
        client_validation["client_tcp_ack_bytes"],
    )
    client_udp_bytes = client_validation["client_udp_bytes"]
    client_tcp_bytes = client_validation["client_tcp_bytes"]
    issue_codes: list[str] = []
    if expected_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_bounded_bytes_missing")
    if helper_udp_bytes < expected_bytes or client_udp_bytes < expected_bytes:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_udp_bytes_missing")
    if helper_tcp_bytes < expected_bytes or client_tcp_bytes < expected_bytes:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_tcp_bytes_missing")
    if tcp_ack_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_tcp_ack_missing")
    evidence = (
        f"bounded_bytes={expected_bytes}; helper_udp={helper_udp_bytes}; client_udp={client_udp_bytes}; "
        f"helper_tcp={helper_tcp_bytes}; client_tcp={client_tcp_bytes}; tcp_ack={tcp_ack_bytes}"
    )
    return {
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "evidence": evidence,
        "bounded": expected_bytes > 0,
        "protocol": "udp_tcp",
        "payload_class": "bounded_udp_tcp_probe",
        "messages_sent": 2 if not issue_codes else 0,
        "messages_received": 2 if not issue_codes else 0,
        "expected_bytes": expected_bytes,
        "helper_udp_bytes": helper_udp_bytes,
        "helper_tcp_bytes": helper_tcp_bytes,
        "client_udp_bytes": client_udp_bytes,
        "client_tcp_bytes": client_tcp_bytes,
        "tcp_ack_bytes": tcp_ack_bytes,
    }


def windows_legacy_ap_cleanup_validation(
    summary: dict[str, Any],
    helper: dict[str, Any],
) -> dict[str, Any]:
    helper_cleanup = object_value(helper.get("measurements")).get("cleanup_completed") is True
    cleanup = object_value(summary.get("cleanup"))
    quest_wifi_forget = object_value(cleanup.get("quest_wifi_forget"))
    profile_removed = any(
        int_value(item.get("exit_code")) == 0 and "Forget successful" in str(item.get("output") or "")
        for item in list_value(quest_wifi_forget.get("removed"))
    )
    wifi_status_after_cleanup = str(cleanup.get("wifi_status_after_cleanup") or "")
    previous_wlan_restored = previous_wlan_restore_observed(wifi_status_after_cleanup)
    direct_profile_absent = "[target-ssid]" not in wifi_status_after_cleanup and "DIRECT-" not in wifi_status_after_cleanup
    issue_codes: list[str] = []
    if not helper_cleanup:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_helper_cleanup_missing")
    if not profile_removed:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_transient_profile_cleanup_missing")
    if not previous_wlan_restored:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_previous_wlan_restore_missing")
    if not direct_profile_absent:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_legacy_ap_direct_profile_still_active")
    evidence = (
        f"helper_cleanup={helper_cleanup}; transient_profile_removed={profile_removed}; "
        f"previous_wlan_restored={previous_wlan_restored}; direct_profile_absent={direct_profile_absent}"
    )
    return {
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "evidence": evidence,
        "helper_cleanup_completed": helper_cleanup,
        "transient_profile_removed": profile_removed,
        "previous_wlan_restored": previous_wlan_restored,
        "direct_profile_absent": direct_profile_absent,
    }


def step_status(summary: dict[str, Any], name: str) -> str:
    for step in list_value(summary.get("steps")):
        if step.get("name") == name:
            return str(step.get("status") or "")
    return ""


def first_ipv4_from_text(text: str) -> str:
    for match in re.finditer(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)", text or ""):
        value = match.group(0)
        if valid_ipv4(value) and not value.startswith("169.254."):
            return value
    return ""


def valid_ipv4(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def previous_wlan_restore_observed(wifi_status: str) -> bool:
    if "Wifi is connected" not in wifi_status:
        return False
    return "[target-ssid]" not in wifi_status and "DIRECT-" not in wifi_status


def min_nonzero(*values: int) -> int:
    positive = [value for value in values if value > 0]
    return min(positive) if positive else 0


def windows_join_summary_validation(
    summary: dict[str, Any],
    path_text: str,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    expected_schema = "rusty.quest.qcl041.quest_hosted_windows_join_probe.v1"
    results = object_value(summary.get("results"))
    cleanup = object_value(summary.get("cleanup"))
    artifact_run_id = str(artifact.get("run_id") or "").strip()
    run_id = str(summary.get("run_id") or "").strip()
    quest_group_owner_host = str(results.get("quest_group_owner_host") or "192.168.49.1").strip()
    windows_client_ipv4 = str(results.get("windows_wifi_direct_ipv4") or "").strip()
    try:
        tcp_response_bytes = int(results.get("tcp_response_bytes") or 0)
    except (TypeError, ValueError):
        tcp_response_bytes = 0
    issue_codes: list[str] = []
    if not path_text:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_report_missing")
    if str(summary.get("schema") or "") != expected_schema:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_report_schema_invalid")
    if str(summary.get("status") or "") != "pass":
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_report_not_pass")
    if artifact_run_id and run_id != artifact_run_id:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_run_mismatch")
    if results.get("windows_connected_to_quest_go") is not True:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_missing")
    if results.get("final_socket_exchange_pass") is not True:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_socket_missing")
    if results.get("final_cleanup_pass") is not True:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_cleanup_missing")
    if not windows_client_ipv4:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_ipv4_missing")
    if tcp_response_bytes <= 0:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_tcp_response_missing")
    if summary.get("credential_sensitive_redacted") is not True:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_not_redacted")
    if cleanup.get("windows_profile_deleted") is not True:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_windows_join_profile_cleanup_missing")

    evidence = (
        f"schema={summary.get('schema') or 'missing'}; status={summary.get('status') or 'missing'}; "
        f"run_id={run_id or 'missing'}; windows_connected={results.get('windows_connected_to_quest_go')}; "
        f"quest_go={quest_group_owner_host or 'missing'}; "
        f"windows_ipv4={windows_client_ipv4 or 'missing'}; tcp_response_bytes={tcp_response_bytes}; "
        f"socket={results.get('final_socket_exchange_pass')}; cleanup={results.get('final_cleanup_pass')}; "
        f"profile_deleted={cleanup.get('windows_profile_deleted')}"
    )
    return {
        "schema": str(summary.get("schema") or ""),
        "run_id": run_id,
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "evidence": evidence,
        "windows_client_ipv4": windows_client_ipv4,
        "quest_group_owner_host": quest_group_owner_host,
    }


def windows_join_summary_check(summary: dict[str, Any]) -> dict[str, Any]:
    return check_row(
        "windows.wifi_direct_join",
        "pass" if summary["valid"] else "blocked",
        summary["evidence"],
        observed=summary,
        issue_codes=summary["issue_codes"],
    )


def lifecycle_check(
    lifecycle: dict[str, Any],
    phase_key: str,
    check_name: str,
    pass_evidence: str,
    issue_code: str,
) -> dict[str, Any]:
    phase = object_value(lifecycle.get(phase_key))
    passed = phase_passed(phase)
    if passed:
        evidence = str(phase.get("evidence") or phase.get("summary") or pass_evidence)
    else:
        evidence = str(phase.get("evidence") or f"{phase_key} evidence missing or not passing")
    return check_row(
        check_name,
        "pass" if passed else "blocked",
        evidence,
        observed=phase,
        issue_codes=[] if passed else [issue_code],
    )


def socket_exchange_check(lifecycle: dict[str, Any]) -> dict[str, Any]:
    phase = object_value(lifecycle.get("socket_exchange"))
    bounded = phase.get("bounded") is True or str(phase.get("payload_class") or "") == "bounded_tcp_probe"
    tcp = str(phase.get("protocol") or "").lower() in {"tcp", "tcp_echo", "bounded_tcp_probe"}
    sent = int_value(phase.get("messages_sent"))
    received = int_value(phase.get("messages_received"))
    counters_proven = sent is not None and sent > 0 and received is not None and received > 0
    passed = phase_passed(phase) and bounded and tcp and counters_proven
    issue_codes: list[str] = []
    if not phase_passed(phase):
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_socket_exchange_missing")
    if phase and not bounded:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_socket_exchange_not_bounded")
    if phase and not tcp:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_socket_exchange_not_tcp")
    if phase and not counters_proven:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_socket_exchange_counters_missing")
    return check_row(
        "topology.socket_exchange",
        "pass" if passed else "blocked",
        (
            str(phase.get("evidence") or "bounded TCP socket exchange completed")
            if passed
            else str(phase.get("evidence") or "bounded TCP socket exchange evidence missing")
        ),
        observed=phase,
        issue_codes=issue_codes,
    )


def peer_discovery_check(lifecycle: dict[str, Any]) -> dict[str, Any]:
    phase = object_value(lifecycle.get("peer_discovery"))
    peer_count = int_value(phase.get("peer_count"))
    peer_observed = peer_count is not None and peer_count > 0
    passed = phase_passed(phase) and peer_observed
    issue_codes: list[str] = []
    if not phase_passed(phase):
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_live_peer_discovery_missing")
    if phase and not peer_observed:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_peer_count_missing")
    return check_row(
        "wifi_direct.peer_discovery",
        "pass" if passed else "blocked",
        (
            str(phase.get("evidence") or "Wi-Fi Direct peer discovery completed")
            if passed
            else str(phase.get("evidence") or "Wi-Fi Direct peer discovery evidence missing")
        ),
        observed=phase,
        issue_codes=issue_codes,
    )


def quest_hosted_windows_peer_discovery_check(
    windows_join_summary: dict[str, Any],
    lifecycle: dict[str, Any],
) -> dict[str, Any]:
    source_phase = object_value(lifecycle.get("peer_discovery"))
    return check_row(
        "wifi_direct.peer_discovery",
        "pass",
        (
            "Windows joined the Quest-hosted Wi-Fi Direct group and received "
            f"{windows_join_summary['windows_client_ipv4']}"
        ),
        observed={
            "mode": "quest_hosted_windows_client_join",
            "source_peer_discovery": source_phase,
            "windows_join_summary": windows_join_summary,
        },
        issue_codes=[],
    )


def group_formation_check(lifecycle: dict[str, Any]) -> dict[str, Any]:
    phase = object_value(lifecycle.get("group_formation"))
    local_role = str(phase.get("local_role") or "").strip()
    peer_role = str(phase.get("peer_role") or "").strip()
    roles_recorded = bool(local_role and peer_role)
    passed = phase_passed(phase) and roles_recorded
    issue_codes: list[str] = []
    if not phase_passed(phase):
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_group_formation_missing")
    if phase and not roles_recorded:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_group_roles_missing")
    return check_row(
        "wifi_direct.group_formation",
        "pass" if passed else "blocked",
        (
            str(phase.get("evidence") or "Wi-Fi Direct group formation completed")
            if passed
            else str(phase.get("evidence") or "Wi-Fi Direct group formation evidence incomplete")
        ),
        observed=phase,
        issue_codes=issue_codes,
    )


def cleanup_check(lifecycle: dict[str, Any]) -> dict[str, Any]:
    phase = object_value(lifecycle.get("cleanup"))
    completed = phase.get("completed") is True
    passed = phase_passed(phase) and completed
    issue_codes: list[str] = []
    if not phase_passed(phase):
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_cleanup_missing")
    if phase and not completed:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_cleanup_not_completed")
    return check_row(
        "wifi_direct.cleanup",
        "pass" if passed else "blocked",
        (
            str(phase.get("evidence") or "Wi-Fi Direct group cleanup completed")
            if passed
            else str(phase.get("evidence") or "Wi-Fi Direct cleanup evidence incomplete")
        ),
        observed=phase,
        issue_codes=issue_codes,
    )


def phase_passed(phase: dict[str, Any]) -> bool:
    return phase.get("status") == "pass" or phase.get("passed") is True


def cleanup_completed(lifecycle: dict[str, Any]) -> bool:
    cleanup = object_value(lifecycle.get("cleanup"))
    return phase_passed(cleanup) and cleanup.get("completed") is True


def int_value(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


__all__ = [
    "WIFI_DIRECT_LIFECYCLE_SCHEMA",
    "run_wifi_direct_lifecycle_template",
    "lifecycle_lease_summary",
    "wifi_direct_lifecycle_body",
    "wifi_direct_lifecycle_probe_report",
    "wifi_direct_lifecycle_template_artifact",
]
