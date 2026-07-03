"""Quest lease and serial-binding helpers for live media receiver routes."""

from __future__ import annotations

from typing import Any

from tools.hostessctl.connectivity_probe_common import object_value
from tools.hostessctl.connectivity_media_receiver_common import (
    AGENT_BOARD_MANAGER,
    QUEST_LEASE_PLACEHOLDERS,
    QUEST_LEASE_RESOURCE_PREFIX,
    QUEST_SERIAL_PLACEHOLDERS,
)


def adb_server_lifecycle_policy() -> str:
    return (
        "Use adb-server:lifecycle only for disruptive daemon lifecycle/recovery "
        "or Wi-Fi ADB setup. This route uses serial-scoped ADB."
    )

def quest_lease_summary_from_args(args: Any) -> dict[str, Any]:
    serial = str(getattr(args, "serial", "") or "").strip()
    resource = str(getattr(args, "quest_lease_resource", "") or "").strip()
    if not resource and serial and "<" not in serial:
        resource = f"{QUEST_LEASE_RESOURCE_PREFIX}{serial}"
    resource_serial = quest_serial_from_resource(resource)
    command_serial = concrete_quest_serial(serial)
    lease_id = str(getattr(args, "quest_lease_id", "") or "").strip()
    reserved_before = bool(getattr(args, "quest_lease_reserved_before_live_steps", False))
    issue_codes: list[str] = []
    if not resource.startswith(QUEST_LEASE_RESOURCE_PREFIX) or "<" in resource:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_quest_lease_resource_invalid")
    if command_serial and resource_serial and command_serial != resource_serial:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_quest_lease_serial_mismatch")
    if lease_id in QUEST_LEASE_PLACEHOLDERS or "<" in lease_id:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_quest_lease_id_missing")
    if not reserved_before:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_quest_lease_not_reserved")
    return {
        "manager": AGENT_BOARD_MANAGER,
        "resource": resource,
        "quest_serial": resource_serial,
        "command_serial": command_serial,
        "command_serial_matches_resource": bool(
            not command_serial or (resource_serial and command_serial == resource_serial)
        ),
        "lease_id": lease_id,
        "reserved_before_live_steps": reserved_before,
        "released_after_live_steps": False,
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "adb_server_lifecycle_lease_used": False,
        "adb_server_lifecycle_policy": adb_server_lifecycle_policy(),
    }

def media_receiver_quest_lease_summary(sidecar: dict[str, Any]) -> dict[str, Any]:
    lease = object_value(sidecar.get("lease") or sidecar.get("quest_lease"))
    manager = str(lease.get("manager") or "").strip()
    resource = str(lease.get("resource") or "").strip()
    resource_serial = quest_serial_from_resource(resource)
    lease_id = str(lease.get("lease_id") or lease.get("id") or "").strip()
    reserved_before = lease.get("reserved_before_live_steps") is True
    issue_codes: list[str] = []
    if manager != AGENT_BOARD_MANAGER:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_quest_lease_missing")
    if not resource.startswith(QUEST_LEASE_RESOURCE_PREFIX) or "<" in resource:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_quest_lease_resource_invalid")
    if lease_id in QUEST_LEASE_PLACEHOLDERS or "<" in lease_id:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_quest_lease_id_missing")
    if not reserved_before:
        issue_codes.append("hostess.issue.connectivity_probe.media_receiver_quest_lease_not_reserved")
    return {
        "manager": manager,
        "resource": resource,
        "quest_serial": resource_serial,
        "lease_id": lease_id,
        "reserved_before_live_steps": reserved_before,
        "released_after_live_steps": lease.get("released_after_live_steps") is True,
        "valid": not issue_codes,
        "issue_codes": issue_codes,
        "adb_server_lifecycle_lease_used": lease.get("adb_server_lifecycle_lease_used") is True,
        "adb_server_lifecycle_policy": str(
            lease.get("adb_server_lifecycle_policy") or adb_server_lifecycle_policy()
        ),
    }

def quest_serial_from_resource(resource: str) -> str:
    if not resource.startswith(QUEST_LEASE_RESOURCE_PREFIX):
        return ""
    return concrete_quest_serial(resource[len(QUEST_LEASE_RESOURCE_PREFIX) :])

def concrete_quest_serial(raw: str) -> str:
    serial = str(raw or "").strip()
    return "" if serial in QUEST_SERIAL_PLACEHOLDERS or "<" in serial else serial

def topology_device_serial(report: dict[str, Any]) -> str:
    device = object_value(report.get("device"))
    for key in ("serial", "adb_serial"):
        serial = concrete_quest_serial(str(device.get(key) or ""))
        if serial:
            return serial
    return ""

__all__ = [
    "adb_server_lifecycle_policy",
    "quest_lease_summary_from_args",
    "media_receiver_quest_lease_summary",
    "quest_serial_from_resource",
    "concrete_quest_serial",
    "topology_device_serial",
]
