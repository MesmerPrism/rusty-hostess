"""Wi-Fi Direct lifecycle plan artifacts for QCL-040/QCL-041."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    check_row,
    issue_row,
    object_value,
    read_json_file,
)
from tools.hostessctl.connectivity_topology_lifecycle import (
    LIVE_DIRECT_WIFI_PROBE_IDS,
    WIFI_DIRECT_LIFECYCLE_SCHEMA,
    lifecycle_source_summary,
    wifi_direct_lifecycle_body,
)


WIFI_DIRECT_LIFECYCLE_PLAN_SCHEMA = (
    "rusty.hostess.qcl040_qcl041_wifi_direct_lifecycle_plan.v1"
)
AGENT_BOARD_SCRIPT = r"S:\Work\agent-bureau\scripts\agent-board.ps1"
QUEST_LEASE_RESOURCE = "quest:<quest-serial>"
QUEST_LEASE_DURATION = "45m"
HOSTESS_REPO_CWD = "<rusty-hostess-root>"
DEFAULT_ADB = r"S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe"
DEFAULT_QCL040_PREFLIGHT = (
    r"target\connectivity-probe\qcl040-live-wifi-direct-preflight.json"
)
DEFAULT_QCL041_PREFLIGHT = (
    r"target\connectivity-probe\qcl041-live-wifi-direct-preflight.json"
)
DEFAULT_QCL040_TEMPLATE = (
    r"target\connectivity-probe\qcl040-wifi-direct-lifecycle-template.json"
)
DEFAULT_QCL041_TEMPLATE = (
    r"target\connectivity-probe\qcl041-wifi-direct-lifecycle-template.json"
)
DEFAULT_QCL040_SOURCE = r"<qcl040-live-wifi-direct-lifecycle-source>"
DEFAULT_QCL041_SOURCE = r"<qcl041-live-wifi-direct-lifecycle-source>"
DEFAULT_QCL040_TOPOLOGY = (
    r"target\connectivity-probe\qcl040-live-wifi-direct-lifecycle.json"
)
DEFAULT_QCL041_TOPOLOGY = (
    r"target\connectivity-probe\qcl041-live-wifi-direct-lifecycle.json"
)


def run_wifi_direct_lifecycle_plan(
    args: argparse.Namespace,
    *,
    clock_func: Any | None = None,
) -> int:
    """Write a read-only plan artifact for the direct-Wi-Fi topology gate."""

    clock = clock_func or (lambda: datetime.now(UTC))
    report = wifi_direct_lifecycle_plan(args, observed_at=clock())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if getattr(args, "fail_on_error", False) and report["status"] not in {"planned", "pass"}:
        return 2
    return 0


def wifi_direct_lifecycle_plan(
    args: argparse.Namespace,
    *,
    observed_at: datetime,
) -> dict[str, Any]:
    """Return the CLI/WPF-equivalent direct-Wi-Fi lifecycle plan."""

    probe_id = str(getattr(args, "probe_id", "") or "QCL-041").upper()
    if probe_id not in LIVE_DIRECT_WIFI_PROBE_IDS:
        raise SystemExit("Wi-Fi Direct lifecycle plans support QCL-040 or QCL-041")
    serial = value(args, "serial", "<quest-serial>")
    paths = wifi_direct_lifecycle_plan_paths(args, probe_id)
    lifecycle = lifecycle_dependency(paths["lifecycle_report"], probe_id)
    preflight = preflight_observation(paths["preflight_report"], probe_id)
    commands = wifi_direct_lifecycle_plan_commands(args, paths, probe_id)
    preflight_check_status = lifecycle_preflight_check_status(
        preflight,
        lifecycle_ready=lifecycle["ready"],
    )
    preflight_issue_codes = (
        []
        if lifecycle["ready"] or preflight_check_status == "pass"
        else preflight["issue_codes"]
    )
    checks = [
        check_row(
            "wifi_direct.lifecycle_plan_authority",
            "pass",
            "Hostess owns the lifecycle plan artifact; WPF renders it only",
            observed={
                "plan_owner": "tools.hostessctl.connectivity_topology_lifecycle_plan",
                "normalizer_owner": "tools.hostessctl.connectivity_topology_lifecycle",
                "preflight_owner": "tools.hostessctl.connectivity_topology_live",
                "frontend_role": "requester_inspector",
            },
        ),
        check_row(
            "wifi_direct.lifecycle_preflight_observation",
            preflight_check_status,
            preflight["evidence"],
            observed=preflight,
            issue_codes=preflight_issue_codes,
        ),
        check_row(
            "wifi_direct.lifecycle_source_dependency",
            "pass" if lifecycle["ready"] else "planned",
            lifecycle["evidence"],
            observed=lifecycle,
            issue_codes=lifecycle["issue_codes"],
        ),
        check_row(
            "wifi_direct.lifecycle_command_chain",
            "pass",
            "Plan lists the Hostess CLI routes and external source artifact needed before topology promotion",
            observed={
                "action_ids": [command["action_id"] for command in commands],
                "live_action_count": sum(1 for command in commands if command["requires_quest_lease"]),
                "external_source_action_count": sum(1 for command in commands if not command["available_now"]),
            },
        ),
    ]
    issue_codes = sorted(set(lifecycle["issue_codes"] + preflight_issue_codes))
    issues = [
        issue_row(code, "warning", "Wi-Fi Direct lifecycle plan dependency is not ready")
        for code in issue_codes
    ]
    return {
        "schema": WIFI_DIRECT_LIFECYCLE_PLAN_SCHEMA,
        "schema_version": 1,
        "plan_id": value(args, "plan_id", f"{probe_id.lower()}-wifi-direct-lifecycle"),
        "observed_at_utc": isoformat_utc(observed_at),
        "status": "planned",
        "probe_id": probe_id,
        "product_gate": "transport.direct_wifi_live_topology",
        "authority": {
            "plan_owner": "tools.hostessctl.connectivity_topology_lifecycle_plan",
            "preflight_owner": "tools.hostessctl.connectivity_topology_live",
            "template_owner": "tools.hostessctl.connectivity_topology_lifecycle",
            "normalizer_owner": "tools.hostessctl.connectivity_topology_lifecycle",
            "frontend_role": "requester_inspector",
        },
        "policy": {
            "requires_quest_lease_for_live_steps": True,
            "requires_adb_server_lifecycle_lease": False,
            "requires_device_serial_matches_quest_lease": True,
            "mutates_wifi_direct_state": False,
            "plan_runs_lifecycle_harness": False,
            "promotes_only_after_live_source_artifact": True,
            "adb_server_lifecycle_policy": (
                "Use adb-server:lifecycle only for disruptive daemon lifecycle "
                "or Wi-Fi ADB setup/recovery. Ordinary ADB commands stay serial-scoped."
            ),
        },
        "lease": quest_lease_metadata(f"{probe_id} direct Wi-Fi lifecycle evidence", serial=serial),
        "dependencies": [
            {
                "gate_id": "transport.direct_wifi_live_topology",
                "ready": lifecycle["ready"],
                "artifact": paths["lifecycle_report"],
                "authority_owner": "tools.hostessctl.connectivity_topology_lifecycle",
                "summary": lifecycle,
            }
        ],
        "observations": {
            "preflight": preflight,
        },
        "readiness": {
            "preflight_report_present": preflight["report_present"],
            "preflight_probe_matches": preflight["probe_id_matches"],
            "preflight_blocked": preflight["blocked"],
            "ready_for_normalization": lifecycle["ready"],
            "ready_for_topology_promotion": lifecycle["ready"],
            "live_steps_require_quest_lease": True,
            "headset_mutation_required_by_plan": False,
            "host_mutation_required_by_plan": False,
        },
        "artifacts": paths,
        "commands": commands,
        "checks": checks,
        "issues": issues,
        "next_step": (
            "Normalize the supplied live lifecycle artifact into a promoted topology report."
            if lifecycle["ready"]
            else (
                "Refresh the live Wi-Fi Direct preflight if needed, then under "
                "a quest:<quest-serial> lease collect a live "
                f"{WIFI_DIRECT_LIFECYCLE_SCHEMA} source artifact with peer discovery, "
                "group formation, bounded TCP socket exchange, cleanup evidence, "
                "and device.serial matching the Agent Board quest lease resource."
            )
        ),
    }


def preflight_observation(path_text: str, probe_id: str) -> dict[str, Any]:
    report = report_if_path_exists(path_text)
    report_probe_id = str(report.get("probe_id") or "").upper()
    report_status = str(report.get("status") or "")
    checks = list_objects(report.get("checks"))
    issues = list_objects(report.get("issues"))
    topology = object_value(report.get("topology"))
    transport = object_value(report.get("transport"))
    check_summaries = [
        {
            "name": str(check.get("name") or ""),
            "status": str(check.get("status") or ""),
            "evidence": str(check.get("evidence") or ""),
            "issue_codes": [
                str(code)
                for code in check.get("issue_codes", [])
                if str(code)
            ]
            if isinstance(check.get("issue_codes"), list)
            else [],
        }
        for check in checks
    ]
    blocker_checks = [
        item
        for item in check_summaries
        if item["status"] in {"blocked", "fail"}
    ]
    issue_codes = sorted(
        {
            str(code)
            for item in check_summaries
            for code in item["issue_codes"]
            if str(code)
        }
        | {
            str(issue.get("issue_code") or "")
            for issue in issues
            if str(issue.get("issue_code") or "")
        }
    )

    if not report:
        return {
            "report_present": False,
            "report_path": path_text,
            "probe_id": "",
            "probe_id_matches": False,
            "report_status": "",
            "blocked": False,
            "blocker_checks": [],
            "issue_codes": [
                "hostess.issue.connectivity_probe.wifi_direct_live_preflight_missing"
            ],
            "evidence": "live Wi-Fi Direct preflight report is not supplied yet",
            "topology_owner": "",
            "transport_route": "",
            "peer_class": "windows" if probe_id == "QCL-041" else "android_phone",
        }

    if report_probe_id != probe_id:
        issue_codes.append(
            "hostess.issue.connectivity_probe.wifi_direct_live_preflight_probe_mismatch"
        )

    blocked = report_status in {"blocked", "fail"} or bool(blocker_checks)
    if blocked:
        blocker_names = ", ".join(
            item["name"] for item in blocker_checks if item["name"]
        )
        evidence = (
            "live Wi-Fi Direct preflight report records blockers"
            + (f": {blocker_names}" if blocker_names else "")
        )
    elif report_status:
        evidence = f"live Wi-Fi Direct preflight report status={report_status}"
    else:
        evidence = "live Wi-Fi Direct preflight report is present"

    return {
        "report_present": True,
        "report_path": path_text,
        "probe_id": report_probe_id,
        "probe_id_matches": report_probe_id == probe_id,
        "report_status": report_status,
        "blocked": blocked,
        "blocker_checks": blocker_checks,
        "issue_codes": sorted(set(issue_codes)),
        "evidence": evidence,
        "topology_owner": str(topology.get("owner") or ""),
        "transport_route": str(transport.get("route") or ""),
        "peer_class": str(topology.get("peer_class") or ""),
    }


def lifecycle_preflight_check_status(
    preflight: dict[str, Any],
    *,
    lifecycle_ready: bool,
) -> str:
    if lifecycle_ready:
        return "skipped"
    if not preflight["report_present"]:
        return "planned"
    if preflight["blocked"] or preflight["issue_codes"]:
        return "blocked"
    return "pass"


def wifi_direct_lifecycle_plan_paths(args: argparse.Namespace, probe_id: str) -> dict[str, str]:
    qcl040 = probe_id == "QCL-040"
    return {
        "preflight_report": value(
            args,
            "preflight_report_out",
            DEFAULT_QCL040_PREFLIGHT if qcl040 else DEFAULT_QCL041_PREFLIGHT,
        ),
        "template_out": value(
            args,
            "template_out",
            DEFAULT_QCL040_TEMPLATE if qcl040 else DEFAULT_QCL041_TEMPLATE,
        ),
        "lifecycle_report": value(
            args,
            "lifecycle_report",
            DEFAULT_QCL040_SOURCE if qcl040 else DEFAULT_QCL041_SOURCE,
        ),
        "topology_report_out": value(
            args,
            "topology_report_out",
            DEFAULT_QCL040_TOPOLOGY if qcl040 else DEFAULT_QCL041_TOPOLOGY,
        ),
    }


def wifi_direct_lifecycle_plan_commands(
    args: argparse.Namespace,
    paths: dict[str, str],
    probe_id: str,
) -> list[dict[str, Any]]:
    adb = value(args, "adb", DEFAULT_ADB)
    serial = value(args, "serial", "<quest-serial>")
    probe_token = probe_id.lower().replace("-", "")
    return [
        plan_command(
            "reserve_quest_lease_for_wifi_direct_lifecycle",
            "Agent Board",
            f"Reserve Quest lease for {probe_id} lifecycle evidence",
            agent_board_reserve_command(f"{probe_id} direct Wi-Fi lifecycle evidence", serial),
            [f"Agent Board {quest_lease_resource(serial)} lease id"],
        ),
        plan_command(
            f"run_{probe_token}_live_wifi_direct_preflight",
            "tools.hostessctl.connectivity_topology_live",
            f"Run {probe_id} live Wi-Fi Direct preflight",
            (
                "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
                f"--mode live --probe-id {probe_id} "
                f"--adb {ps_quote(adb)} --serial {ps_quote(serial)} "
                f"--out {ps_quote(paths['preflight_report'])}"
            ),
            [paths["preflight_report"]],
            requires_quest_lease=True,
        ),
        plan_command(
            f"write_{probe_token}_wifi_direct_lifecycle_template",
            "tools.hostessctl.connectivity_topology_lifecycle",
            f"Write {probe_id} lifecycle source template",
            (
                "python tools\\hostessctl\\hostessctl.py "
                "connectivity-probe wifi-direct-lifecycle-template "
                f"--probe-id {probe_id} --out {ps_quote(paths['template_out'])}"
            ),
            [paths["template_out"]],
        ),
        plan_command(
            f"collect_{probe_token}_wifi_direct_lifecycle_source",
            "external leased Wi-Fi Direct peer harness",
            f"Collect live {probe_id} lifecycle source artifact",
            (
                "external leased peer harness writes "
                f"{ps_quote(paths['lifecycle_report'])} with schema {WIFI_DIRECT_LIFECYCLE_SCHEMA} "
                f"and device.serial matching quest resource {ps_quote(quest_lease_resource(serial))}"
            ),
            [paths["lifecycle_report"]],
            requires_quest_lease=True,
            lease_serial=serial,
            available_now=False,
            note=(
                "Hostess does not own Wi-Fi Direct peer discovery/group mechanics yet; "
                "it accepts the resulting structured source artifact only when the "
                "device serial matches the reserved Agent Board quest resource."
            ),
        ),
        plan_command(
            f"normalize_{probe_token}_wifi_direct_lifecycle_report",
            "tools.hostessctl.connectivity_topology_lifecycle",
            f"Normalize live {probe_id} lifecycle evidence",
            (
                "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
                f"--mode fixture --probe-id {probe_id} "
                f"--wifi-direct-lifecycle-report {ps_quote(paths['lifecycle_report'])} "
                f"--out {ps_quote(paths['topology_report_out'])} --fail-on-error"
            ),
            [paths["topology_report_out"]],
            clears_gate=True,
        ),
    ]


def plan_command(
    action_id: str,
    authority_owner: str,
    label: str,
    command: str,
    acceptance_artifacts: list[str],
    *,
    requires_quest_lease: bool = False,
    lease_serial: str = "<quest-serial>",
    available_now: bool = True,
    clears_gate: bool = False,
    note: str = "",
) -> dict[str, Any]:
    item = {
        "action_id": action_id,
        "label": label,
        "authority_owner": authority_owner,
        "available_now": available_now,
        "shell": "powershell",
        "cwd": HOSTESS_REPO_CWD,
        "command": command,
        "acceptance_artifacts": acceptance_artifacts,
        "requires_quest_lease": requires_quest_lease,
        "requires_elevation": False,
        "requires_adb_server_lifecycle_lease": False,
        "mutates_host": False,
        "mutates_device": False,
        "clears_gate_when_accepted": clears_gate,
    }
    if requires_quest_lease:
        item["lease"] = quest_lease_metadata(label, serial=lease_serial)
    if note:
        item["note"] = note
    return item


def lifecycle_dependency(path_text: str, probe_id: str) -> dict[str, Any]:
    artifact = report_if_path_exists(path_text)
    expected_peer_class = "windows" if probe_id == "QCL-041" else "android_phone"
    source = lifecycle_source_summary(artifact, probe_id, expected_peer_class)
    topology_body = wifi_direct_lifecycle_body(artifact, artifact_path=path_text, probe_id=probe_id)
    ready = bool(artifact) and source["valid"] and topology_body.get("status") == "pass"
    if ready:
        evidence = "live Wi-Fi Direct lifecycle source artifact is ready for topology normalization"
        issue_codes: list[str] = []
    elif not artifact:
        evidence = "live Wi-Fi Direct lifecycle source artifact is not supplied yet"
        issue_codes = ["hostess.issue.connectivity_probe.wifi_direct_lifecycle_source_missing"]
    else:
        evidence = "Wi-Fi Direct lifecycle source artifact is present but not promotable"
        issue_codes = sorted(
            {
                code
                for code in source["issue_codes"]
                + [
                    code
                    for issue in list_objects(topology_body.get("issues"))
                    for code in [str(issue.get("issue_code") or "")]
                    if code
                ]
            }
        )
    return {
        "ready": ready,
        "evidence": evidence,
        "issue_codes": issue_codes,
        "report_path": path_text,
        "report_present": bool(artifact),
        "schema": source["schema"],
        "probe_id": source["probe_id"],
        "peer_class": source["peer_class"],
        "evidence_tier": source["evidence_tier"],
        "capture_kind": source["capture_kind"],
        "run_id": source["run_id"],
        "harness_id": source["harness_id"],
        "harness_owner": source["harness_owner"],
        "live_evidence": source["live_evidence"],
        "topology_status": str(topology_body.get("status") or ""),
        "promotion_allowed": object_value(topology_body.get("promotion")).get("allowed") is True,
    }


def report_if_path_exists(path_text: str) -> dict[str, Any]:
    if not path_text or path_text.startswith("<"):
        return {}
    return read_json_file(Path(path_text))


def quest_lease_metadata(task: str, *, serial: str = "<quest-serial>") -> dict[str, Any]:
    return {
        "manager": "Agent Board",
        "resource": quest_lease_resource(serial),
        "duration": QUEST_LEASE_DURATION,
        "task": task,
        "lease_id_placeholder": "<quest-lease-id>",
        "reserve_command": agent_board_reserve_command(task, serial),
        "release_command": f"& '{AGENT_BOARD_SCRIPT}' release '<quest-lease-id>' --result done",
        "adb_server_lifecycle_policy": (
            "Use adb-server:lifecycle only for disruptive daemon lifecycle "
            "or Wi-Fi ADB setup/recovery. Ordinary ADB commands stay serial-scoped."
        ),
    }


def agent_board_reserve_command(task: str, serial: str = "<quest-serial>") -> str:
    return (
        f"& '{AGENT_BOARD_SCRIPT}' reserve '{quest_lease_resource(serial)}' "
        f"--duration {QUEST_LEASE_DURATION} --task '{task}'"
    )


def quest_lease_resource(serial: str) -> str:
    serial_text = str(serial or "<quest-serial>").strip()
    if serial_text.startswith("quest:"):
        return serial_text
    return f"quest:{serial_text}"


def value(args: argparse.Namespace, name: str, default: Any) -> str:
    return str(getattr(args, name, default) or default)


def ps_quote(raw: str) -> str:
    return "'" + str(raw).replace("'", "''") + "'"


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def list_objects(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


__all__ = [
    "WIFI_DIRECT_LIFECYCLE_PLAN_SCHEMA",
    "run_wifi_direct_lifecycle_plan",
    "wifi_direct_lifecycle_plan",
]
