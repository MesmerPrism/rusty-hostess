"""Live dependency preflight and blocked-result helpers for media receiver routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_probe_common import object_value, read_json_file
from tools.hostessctl.connectivity_media_receiver_common import (
    LIVE_CAPTURE_KINDS,
    RECEIVER_CAPTURE_RESULT_SCHEMA,
    RECEIVER_CAPTURE_SIDECAR_SCHEMA,
    RECEIVER_CAPTURE_STATS_SCHEMA,
    endpoint_source_for_capture_kind,
)
from tools.hostessctl.connectivity_media_receiver_lease import quest_lease_summary_from_args
from tools.hostessctl.connectivity_media_receiver_product import (
    media_product_listener_firewall_summary,
    media_product_topology_summary,
)


def blocked_receiver_capture_result(
    args: Any,
    *,
    capture_kind: str,
    quest_lease: dict[str, Any],
    close_reason: str = "blocked_missing_quest_lease",
    extra_issue_codes: list[str] | None = None,
    dependency_preflight: dict[str, Any] | None = None,
    live_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    capture_path = str(getattr(args, "capture_out", "") or "")
    sidecar_path = str(getattr(args, "sidecar_out", "") or "")
    issue_codes = sorted(
        set(
            str(code)
            for code in [
                *(quest_lease.get("issue_codes", []) or []),
                *(extra_issue_codes or []),
            ]
            if str(code)
        )
    )
    return {
        "schema": RECEIVER_CAPTURE_RESULT_SCHEMA,
        "status": "fail",
        "capture_kind": capture_kind,
        "live_capture": capture_kind in LIVE_CAPTURE_KINDS,
        "capture_path": capture_path,
        "sidecar_path": sidecar_path,
        "runtime_status_path": str(getattr(args, "runtime_status", "") or getattr(args, "execution_out", "") or ""),
        "topology_report_path": str(getattr(args, "topology_report", "") or ""),
        "firewall_report_path": str(getattr(args, "firewall_report", "") or ""),
        "local_endpoint": "",
        "remote_endpoint": "",
        "accepted_connection": False,
        "close_reason": close_reason,
        "elapsed_ms": 0.0,
        "bytes_written": 0,
        "issue_codes": issue_codes,
        "socket_error": "",
        "capture_stats": {
            "schema": RECEIVER_CAPTURE_STATS_SCHEMA,
            "status": "fail",
            "capture_path": capture_path,
            "packet_count": 0,
            "issue_codes": issue_codes,
        },
        "receiver_sidecar": {
            "schema": RECEIVER_CAPTURE_SIDECAR_SCHEMA,
            "capture_kind": capture_kind,
            "live_capture": capture_kind in LIVE_CAPTURE_KINDS,
            "receiver": {
                "local_endpoint": "",
                "close_reason": close_reason,
                "queue_capacity_packets": None,
                "max_queue_depth_observed": None,
                "dropped_frames": None,
                "backpressure_events": None,
            },
            "source": {
                "endpoint_source": endpoint_source_for_capture_kind(capture_kind),
                "runtime_status_path": str(getattr(args, "execution_out", "") or ""),
                "topology_report_path": str(getattr(args, "topology_report", "") or ""),
                "firewall_report_path": str(getattr(args, "firewall_report", "") or ""),
            },
            "lease": quest_lease,
        },
        "quest_lease": quest_lease,
        "dependency_preflight": object_value(dependency_preflight),
        "live_session": live_session or {},
    }

def media_live_dependency_preflight_from_args(args: Any) -> dict[str, Any]:
    """Check product-media live dependencies without running live steps."""

    topology_path = str(getattr(args, "topology_report", "") or "").strip()
    firewall_path = str(getattr(args, "firewall_report", "") or "").strip()
    capture_kind = str(getattr(args, "capture_kind", "live_broker_stream") or "live_broker_stream")
    quest_lease = quest_lease_summary_from_args(args)
    topology_report = read_json_file(Path(topology_path)) if topology_path else {}
    firewall_report = read_json_file(Path(firewall_path)) if firewall_path else {}
    topology = media_product_topology_summary(
        topology_report,
        topology_report_path=topology_path,
        media_promotion_allowed=True,
        media_transport_ok=True,
        runtime_ok=True,
        capture_kind=capture_kind,
        quest_lease=quest_lease,
    )
    firewall = media_product_listener_firewall_summary(
        firewall_report,
        firewall_report_path=firewall_path,
        media_promotion_allowed=True,
        capture_kind=capture_kind,
    )
    issue_codes: list[str] = []
    if not topology["topology_report_present"]:
        issue_codes.append(
            "hostess.issue.connectivity_probe.media_live_session_topology_report_missing"
        )
    elif not topology["ready"]:
        issue_codes.append(
            "hostess.issue.connectivity_probe.media_live_session_direct_wifi_topology_not_ready"
        )
    if not firewall["firewall_report_present"]:
        issue_codes.append(
            "hostess.issue.connectivity_probe.media_live_session_firewall_report_missing"
        )
    elif not firewall["ready"]:
        issue_codes.append(
            "hostess.issue.connectivity_probe.media_live_session_listener_firewall_not_ready"
        )
    issue_codes.extend(str(code) for code in topology.get("issue_codes", []) or [])
    issue_codes.extend(str(code) for code in firewall.get("issue_codes", []) or [])
    ready = topology["ready"] and firewall["ready"]
    return {
        "ready": ready,
        "requires_promoted_direct_wifi_topology": True,
        "requires_product_listener_firewall": True,
        "topology": topology,
        "firewall": firewall,
        "issue_codes": sorted(set(code for code in issue_codes if code)),
    }

__all__ = [
    "blocked_receiver_capture_result",
    "media_live_dependency_preflight_from_args",
]
