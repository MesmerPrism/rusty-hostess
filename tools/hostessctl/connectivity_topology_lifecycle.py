"""Wi-Fi Direct lifecycle evidence ingestion for QCL-040/QCL-041."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    append_issue_once,
    base_report,
    check_row,
    empty_measurements,
    object_value,
    read_json_file,
)
from tools.hostessctl.connectivity_topology import topology_issues
from tools.hostessctl.connectivity_topology_live import LIVE_DIRECT_WIFI_PROBE_IDS


WIFI_DIRECT_LIFECYCLE_SCHEMA = "rusty.quest.connectivity_wifi_direct_lifecycle.v1"
LIVE_EVIDENCE_TIERS = {
    "quest_runtime",
    "hostess_harness",
    "product_harness",
    "product_owned",
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
    artifact = read_json_file(artifact_path)
    report = base_report(args, observed_at=observed_at, probe_id=probe_id)
    report.update(wifi_direct_lifecycle_body(artifact, artifact_path=str(artifact_path), probe_id=probe_id))
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
            "promotes_when": (
                "live_evidence is true, evidence_tier is a live tier, peer class "
                "matches the probe, and all lifecycle phases pass"
            ),
            "non_promoting_template": True,
        },
        "topology": {
            "owner": "wifi_direct",
            "network_provider": "wifi_direct",
            "endpoint_direction": "peer_to_peer_group",
            "peer_class": peer_class,
        },
        "device": {
            "model": "Quest",
            "wifi_direct_role": "group_owner_or_client",
        },
        "host": {
            "os": "windows" if windows_peer else "android_phone_peer",
            "toolchain_profile": "hostessctl.connectivity_probe.wifi_direct_lifecycle_template",
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
                "Wi-Fi Direct peer discovery completed with at least one peer"
            ),
            "group_formation": lifecycle_template_phase(
                "Wi-Fi Direct group formation completed with recorded roles"
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
) -> dict[str, Any]:
    windows_peer = probe_id == "QCL-041"
    expected_peer_class = "windows" if windows_peer else "android_phone"
    source_summary = lifecycle_source_summary(artifact, probe_id, expected_peer_class)
    lifecycle = object_value(artifact.get("lifecycle"))

    checks = [
        check_row(
            "wifi_direct.lifecycle_source",
            "pass" if source_summary["valid"] else "blocked",
            source_summary["evidence"],
            observed=source_summary,
            issue_codes=source_summary["issue_codes"],
        ),
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
        lifecycle_check(
            lifecycle,
            "peer_discovery",
            "wifi_direct.peer_discovery",
            "Wi-Fi Direct peer discovery completed",
            "hostess.issue.connectivity_probe.wifi_direct_live_peer_discovery_missing",
        ),
        lifecycle_check(
            lifecycle,
            "group_formation",
            "wifi_direct.group_formation",
            "Wi-Fi Direct group formation completed",
            "hostess.issue.connectivity_probe.wifi_direct_group_formation_missing",
        ),
        socket_exchange_check(lifecycle),
        lifecycle_check(
            lifecycle,
            "cleanup",
            "wifi_direct.cleanup",
            "Wi-Fi Direct group cleanup completed",
            "hostess.issue.connectivity_probe.wifi_direct_cleanup_missing",
        ),
    ]
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
    topology["peer_class"] = expected_peer_class

    host = {
        "os": "windows" if windows_peer else "android_phone_peer",
        "toolchain_profile": f"hostessctl.connectivity_probe.{probe_id.lower()}.wifi_direct_lifecycle",
    }
    host.update(object_value(artifact.get("host")))

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
            }
        ],
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

    evidence = (
        f"schema={schema or 'missing'}; probe_id={artifact_probe_id or 'missing'}; "
        f"peer_class={peer_class or 'missing'}; evidence_tier={evidence_tier or 'missing'}; "
        f"capture_kind={capture_kind or 'missing'}"
    )
    return {
        "schema": schema,
        "probe_id": artifact_probe_id,
        "peer_class": peer_class,
        "evidence_tier": evidence_tier,
        "capture_kind": capture_kind,
        "live_evidence": live_evidence,
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "evidence": evidence,
    }


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
    passed = phase_passed(phase) and bounded and tcp
    issue_codes: list[str] = []
    if not phase_passed(phase):
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_socket_exchange_missing")
    if phase and not bounded:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_socket_exchange_not_bounded")
    if phase and not tcp:
        issue_codes.append("hostess.issue.connectivity_probe.wifi_direct_socket_exchange_not_tcp")
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


def phase_passed(phase: dict[str, Any]) -> bool:
    return phase.get("status") == "pass" or phase.get("passed") is True


def cleanup_completed(lifecycle: dict[str, Any]) -> bool:
    cleanup = object_value(lifecycle.get("cleanup"))
    return phase_passed(cleanup) and cleanup.get("completed") is not False


__all__ = [
    "WIFI_DIRECT_LIFECYCLE_SCHEMA",
    "run_wifi_direct_lifecycle_template",
    "wifi_direct_lifecycle_body",
    "wifi_direct_lifecycle_probe_report",
    "wifi_direct_lifecycle_template_artifact",
]
