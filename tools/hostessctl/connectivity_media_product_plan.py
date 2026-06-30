"""QCL-082 product media over direct-Wi-Fi plan artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_firewall import (
    DEFAULT_QCL082_RMANVID1_MEDIA_PORT,
    DEFAULT_WPF_FIREWALL_PROGRAM,
    diagnostic_python_program_path,
)
from tools.hostessctl.connectivity_probe_common import (
    check_row,
    issue_row,
    object_value,
    read_json_file,
)


PRODUCT_MEDIA_DIRECT_WIFI_PLAN_SCHEMA = (
    "rusty.hostess.qcl082_product_media_direct_wifi_plan.v1"
)
AGENT_BOARD_SCRIPT = r"S:\Work\agent-bureau\scripts\agent-board.ps1"
QUEST_LEASE_RESOURCE = "quest:<quest-serial>"
QUEST_LEASE_DURATION = "45m"
HOSTESS_REPO_CWD = "<rusty-hostess-root>"
DEFAULT_ADB = r"S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe"
DEFAULT_START_SOURCE_REQUEST = (
    r"target\connectivity-probe\media-stream-start-source.request.json"
)
DEFAULT_START_SOURCE_BRIDGE_EVIDENCE = (
    r"target\connectivity-probe\media-stream-start-source.bridge-evidence.json"
)
DEFAULT_START_SOURCE_EXECUTION = (
    r"target\connectivity-probe\media-stream-start-source.live-android-execution.json"
)
DEFAULT_START_SOURCE_VALIDATION = (
    r"target\connectivity-probe\media-stream-start-source.validation-report.json"
)
DEFAULT_START_SOURCE_LOGCAT = (
    r"target\connectivity-probe\media-stream-start-source.logcat.txt"
)
DEFAULT_RUNTIME_STATUS_REPORT = (
    r"target\connectivity-probe\qcl082-media-stream-runtime-status.json"
)
DEFAULT_FIREWALL_REPORT = (
    r"target\connectivity-probe\qcl082-tcp-firewall-admin-handoff-verify.json"
)
DEFAULT_RMANVID1_CAPTURE = r"target\connectivity-probe\media-stream.rmanvid1"
DEFAULT_RMANVID1_SIDECAR = (
    r"target\connectivity-probe\media-stream-receiver-sidecar.json"
)
DEFAULT_RMANVID1_RECEIVER_RESULT = (
    r"target\connectivity-probe\media-stream-receiver-result.json"
)
DEFAULT_QCL082_PRODUCT_REPORT = (
    r"target\connectivity-probe\qcl082-rmanvid1-receiver-capture.json"
)
DEFAULT_PROTOCOL_MATRIX = (
    r"target\connectivity-probe\qcl082-rmanvid1-receiver-capture.protocol-matrix.json"
)
DEFAULT_PROMOTED_TOPOLOGY_REPORT = "<promoted-qcl040-or-qcl041-topology-report>"


def run_qcl082_product_media_direct_wifi_plan(
    args: argparse.Namespace,
    *,
    clock_func: Any | None = None,
) -> int:
    """Write a read-only plan artifact for the QCL-082 product media gate."""

    clock = clock_func or (lambda: datetime.now(UTC))
    report = qcl082_product_media_direct_wifi_plan(args, observed_at=clock())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if getattr(args, "fail_on_error", False) and report["status"] not in {"planned", "pass"}:
        return 2
    return 0


def qcl082_product_media_direct_wifi_plan(
    args: argparse.Namespace,
    *,
    observed_at: datetime,
) -> dict[str, Any]:
    """Return the CLI/WPF-equivalent product-media-over-direct-Wi-Fi plan."""

    paths = product_media_plan_paths(args)
    topology = topology_dependency(paths["promoted_topology_report"])
    firewall = firewall_dependency(paths["firewall_report"])
    commands = product_media_plan_commands(args, paths)
    checks = [
        check_row(
            "qcl082.product_media_plan_authority",
            "pass",
            "Hostess owns the product-media plan artifact; WPF renders it only",
            observed={
                "plan_owner": "tools.hostessctl.connectivity_media_product_plan",
                "runtime_authority": "rusty.manifold command/session plus Quest runtime status",
                "receiver_owner": "tools.hostessctl.connectivity_media_receiver",
            },
        ),
        check_row(
            "qcl082.product_media_direct_wifi_dependency",
            "pass" if topology["ready"] else "planned",
            topology["evidence"],
            observed=topology,
            issue_codes=topology["issue_codes"],
        ),
        check_row(
            "qcl082.product_media_listener_firewall_dependency",
            "pass" if firewall["ready"] else "planned",
            firewall["evidence"],
            observed=firewall,
            issue_codes=firewall["issue_codes"],
        ),
        check_row(
            "qcl082.product_media_receiver_contract",
            "pass",
            "RMANVID1 receiver stays on the binary TCP media plane and writes capture, sidecar, and result artifacts",
            observed={
                "bind_host": value(args, "bind_host", "0.0.0.0"),
                "port": int_value(value(args, "port", DEFAULT_QCL082_RMANVID1_MEDIA_PORT)),
                "capture_kind": value(args, "capture_kind", "live_broker_stream"),
                "capture_out": paths["capture_out"],
                "sidecar_out": paths["sidecar_out"],
                "receiver_result_out": paths["receiver_result_out"],
            },
        ),
        check_row(
            "qcl082.product_media_command_chain",
            "pass",
            "Plan lists the ordered Hostess CLI routes needed before product-media promotion",
            observed={
                "action_ids": [command["action_id"] for command in commands],
                "live_action_count": sum(1 for command in commands if command["requires_quest_lease"]),
            },
        ),
    ]
    issues = [
        issue_row(code, "warning", "QCL-082 product media plan dependency is not ready")
        for dependency in (topology, firewall)
        for code in dependency["issue_codes"]
    ]
    ready_for_receiver_capture = topology["ready"] and firewall["ready"]
    return {
        "schema": PRODUCT_MEDIA_DIRECT_WIFI_PLAN_SCHEMA,
        "schema_version": 1,
        "plan_id": value(args, "plan_id", "qcl082-product-media-direct-wifi"),
        "observed_at_utc": isoformat_utc(observed_at),
        "status": "planned",
        "product_gate": "product_tcp_media_over_direct_wifi",
        "authority": {
            "plan_owner": "tools.hostessctl.connectivity_media_product_plan",
            "command_request_owner": "tools.hostessctl.bridge_command_routes",
            "live_command_owner": "tools.hostessctl.bridge_command_live_android_routes",
            "runtime_status_owner": "tools.hostessctl.connectivity_media",
            "receiver_owner": "tools.hostessctl.connectivity_media_receiver",
            "firewall_owner": "tools.hostessctl.connectivity_firewall",
            "topology_owner": "tools.hostessctl.connectivity_topology_lifecycle",
            "promotion_owner": "tools.hostessctl.protocol_evidence_matrix",
            "frontend_role": "requester_inspector",
        },
        "policy": {
            "high_rate_media_payload_plane": "binary_tcp_rmanvid1",
            "json_allowed_for_media_payload": False,
            "requires_promoted_direct_wifi_topology": True,
            "requires_product_listener_firewall": True,
            "requires_quest_lease_for_live_steps": True,
            "adb_server_lifecycle_policy": (
                "Use adb-server:lifecycle only for disruptive daemon lifecycle "
                "or Wi-Fi ADB setup/recovery. Ordinary ADB commands stay serial-scoped."
            ),
        },
        "lease": quest_lease_metadata("QCL-082 product TCP media over direct Wi-Fi"),
        "dependencies": [
            {
                "gate_id": "transport.direct_wifi_live_topology",
                "ready": topology["ready"],
                "artifact": paths["promoted_topology_report"],
                "authority_owner": "tools.hostessctl.connectivity_topology_lifecycle",
                "summary": topology,
            },
            {
                "gate_id": "transport.product_tcp_media_listener_firewall",
                "ready": firewall["ready"],
                "artifact": paths["firewall_report"],
                "authority_owner": "tools.hostessctl.connectivity_firewall",
                "summary": firewall,
            },
        ],
        "readiness": {
            "ready_for_receiver_capture": ready_for_receiver_capture,
            "ready_for_qcl082_product_gate": ready_for_receiver_capture,
            "live_steps_require_quest_lease": True,
            "firewall_mutation_required_by_plan": False,
            "headset_mutation_required_by_plan": True,
            "host_mutation_required_by_plan": False,
        },
        "artifacts": paths,
        "commands": commands,
        "checks": checks,
        "issues": issues,
        "next_step": (
            "Reserve quest:<quest-serial>, run the live start_source and receiver-capture steps, "
            "then fold the capture into QCL-082 and the protocol matrix."
            if ready_for_receiver_capture
            else (
                "Produce a promoted QCL-040/QCL-041 direct-Wi-Fi lifecycle report and "
                "a verified qcl-082-rmanvid1-media firewall report before the live receiver capture."
            )
        ),
    }


def product_media_plan_paths(args: argparse.Namespace) -> dict[str, str]:
    return {
        "start_source_request_out": value(args, "start_source_request_out", DEFAULT_START_SOURCE_REQUEST),
        "start_source_bridge_evidence_out": value(
            args,
            "start_source_bridge_evidence_out",
            DEFAULT_START_SOURCE_BRIDGE_EVIDENCE,
        ),
        "start_source_execution_out": value(
            args,
            "start_source_execution_out",
            DEFAULT_START_SOURCE_EXECUTION,
        ),
        "start_source_validation_out": value(
            args,
            "start_source_validation_out",
            DEFAULT_START_SOURCE_VALIDATION,
        ),
        "start_source_logcat_out": value(
            args,
            "start_source_logcat_out",
            DEFAULT_START_SOURCE_LOGCAT,
        ),
        "runtime_status_report_out": value(
            args,
            "runtime_status_report_out",
            DEFAULT_RUNTIME_STATUS_REPORT,
        ),
        "promoted_topology_report": value(
            args,
            "promoted_topology_report",
            DEFAULT_PROMOTED_TOPOLOGY_REPORT,
        ),
        "firewall_report": value(args, "firewall_report", DEFAULT_FIREWALL_REPORT),
        "capture_out": value(args, "capture_out", DEFAULT_RMANVID1_CAPTURE),
        "sidecar_out": value(args, "sidecar_out", DEFAULT_RMANVID1_SIDECAR),
        "receiver_result_out": value(args, "receiver_result_out", DEFAULT_RMANVID1_RECEIVER_RESULT),
        "qcl082_report_out": value(args, "qcl082_report_out", DEFAULT_QCL082_PRODUCT_REPORT),
        "protocol_matrix_out": value(args, "protocol_matrix_out", DEFAULT_PROTOCOL_MATRIX),
    }


def product_media_plan_commands(args: argparse.Namespace, paths: dict[str, str]) -> list[dict[str, Any]]:
    adb = value(args, "adb", DEFAULT_ADB)
    serial = value(args, "serial", "<quest-serial>")
    program = value(args, "program", str(DEFAULT_WPF_FIREWALL_PROGRAM))
    bind_host = value(args, "bind_host", "0.0.0.0")
    port = str(int_value(value(args, "port", DEFAULT_QCL082_RMANVID1_MEDIA_PORT)) or DEFAULT_QCL082_RMANVID1_MEDIA_PORT)
    max_packets = str(int_value(value(args, "max_packets", 240)) or 240)
    capture_kind = value(args, "capture_kind", "live_broker_stream")
    return [
        plan_command(
            "write_qcl082_media_stream_start_source_request",
            "tools.hostessctl.bridge_command_routes",
            "Write QCL-082 start_source request",
            (
                "python tools\\hostessctl\\hostessctl.py emit-bridge-command-request "
                "--bridge-command command.media_stream.start_source "
                "--request-id request.hostess.qcl082.media_stream.start_source "
                "--evidence-id evidence.hostess.qcl082.media_stream.start_source "
                "--route-id bridge_route.command.websocket.applied "
                "--required-stage sent --required-stage transport_ok --required-stage authority_accepted "
                f"--out {ps_quote(paths['start_source_request_out'])}"
            ),
            [paths["start_source_request_out"]],
        ),
        plan_command(
            "run_qcl082_media_stream_start_source",
            "tools.hostessctl.bridge_command_live_android_routes",
            "Run QCL-082 start_source on Quest",
            (
                "python tools\\hostessctl\\hostessctl.py run-bridge-command-live-android "
                f"--input {ps_quote(paths['start_source_request_out'])} "
                f"--out {ps_quote(paths['start_source_bridge_evidence_out'])} "
                f"--execution-out {ps_quote(paths['start_source_execution_out'])} "
                f"--validation-out {ps_quote(paths['start_source_validation_out'])} "
                f"--adb {ps_quote(adb)} --serial {ps_quote(serial)}"
            ),
            [
                paths["start_source_bridge_evidence_out"],
                paths["start_source_execution_out"],
                paths["start_source_validation_out"],
            ],
            requires_quest_lease=True,
            mutates_host=True,
            mutates_device=True,
        ),
        plan_command(
            "validate_qcl082_media_stream_runtime_status",
            "tools.hostessctl.connectivity_media",
            "Build QCL-082 runtime-status report",
            (
                "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
                "--mode fixture --probe-id QCL-082 "
                f"--media-stream-runtime-status {ps_quote(paths['start_source_execution_out'])} "
                f"--out {ps_quote(paths['runtime_status_report_out'])} --fail-on-error"
            ),
            [paths["runtime_status_report_out"]],
        ),
        plan_command(
            "verify_qcl082_product_firewall_rule",
            "tools.hostessctl.connectivity_firewall",
            "Verify product TCP listener firewall",
            (
                "python tools\\hostessctl\\hostessctl.py connectivity-probe windows-firewall-rule "
                "--action verify --rule-profile qcl-082-rmanvid1-media "
                f"--program {ps_quote(program)} "
                f"--out {ps_quote(paths['firewall_report'])} --fail-on-error"
            ),
            [paths["firewall_report"]],
        ),
        plan_command(
            "run_qcl082_product_media_live_session",
            "tools.hostessctl.connectivity_media_receiver",
            "Run orchestrated QCL-082 product media session",
            (
                "python tools\\hostessctl\\hostessctl.py "
                "connectivity-probe qcl082-product-media-live-session "
                "--bridge-command command.media_stream.start_source "
                f"--start-source-request-out {ps_quote(paths['start_source_request_out'])} "
                f"--bridge-evidence-out {ps_quote(paths['start_source_bridge_evidence_out'])} "
                f"--execution-out {ps_quote(paths['start_source_execution_out'])} "
                f"--validation-out {ps_quote(paths['start_source_validation_out'])} "
                f"--logcat-out {ps_quote(paths['start_source_logcat_out'])} "
                f"--bind-host {ps_quote(bind_host)} --port {port} "
                f"--capture-out {ps_quote(paths['capture_out'])} "
                f"--sidecar-out {ps_quote(paths['sidecar_out'])} "
                f"--topology-report {ps_quote(paths['promoted_topology_report'])} "
                f"--firewall-report {ps_quote(paths['firewall_report'])} "
                f"--capture-kind {capture_kind} --max-packets {max_packets} "
                f"--adb {ps_quote(adb)} --serial {ps_quote(serial)} "
                f"--out {ps_quote(paths['receiver_result_out'])} --fail-on-error"
            ),
            [
                paths["start_source_request_out"],
                paths["start_source_bridge_evidence_out"],
                paths["start_source_execution_out"],
                paths["start_source_validation_out"],
                paths["capture_out"],
                paths["sidecar_out"],
                paths["receiver_result_out"],
            ],
            requires_quest_lease=True,
            mutates_device=True,
            depends_on=[
                "transport.direct_wifi_live_topology",
                "transport.product_tcp_media_listener_firewall",
            ],
        ),
        plan_command(
            "capture_rmanvid1_over_promoted_direct_wifi",
            "tools.hostessctl.connectivity_media_receiver",
            "Capture RMANVID1 receiver counters",
            (
                "python tools\\hostessctl\\hostessctl.py connectivity-probe rmanvid1-receiver-capture "
                f"--bind-host {ps_quote(bind_host)} --port {port} "
                f"--capture-out {ps_quote(paths['capture_out'])} "
                f"--sidecar-out {ps_quote(paths['sidecar_out'])} "
                f"--runtime-status {ps_quote(paths['start_source_execution_out'])} "
                f"--topology-report {ps_quote(paths['promoted_topology_report'])} "
                f"--firewall-report {ps_quote(paths['firewall_report'])} "
                f"--capture-kind {capture_kind} --max-packets {max_packets} "
                f"--out {ps_quote(paths['receiver_result_out'])} --fail-on-error"
            ),
            [
                paths["capture_out"],
                paths["sidecar_out"],
                paths["receiver_result_out"],
            ],
            requires_quest_lease=True,
            mutates_device=True,
            depends_on=[
                "transport.direct_wifi_live_topology",
                "transport.product_tcp_media_listener_firewall",
            ],
        ),
        plan_command(
            "promote_qcl082_rmanvid1_capture",
            "tools.hostessctl.connectivity_probe",
            "Build QCL-082 product media report",
            (
                "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
                "--mode fixture --probe-id QCL-082 "
                f"--media-stream-rmanvid1-capture {ps_quote(paths['capture_out'])} "
                f"--media-stream-receiver-sidecar {ps_quote(paths['sidecar_out'])} "
                f"--media-stream-runtime-status {ps_quote(paths['start_source_execution_out'])} "
                f"--media-stream-topology-report {ps_quote(paths['promoted_topology_report'])} "
                f"--media-stream-firewall-report {ps_quote(paths['firewall_report'])} "
                f"--out {ps_quote(paths['qcl082_report_out'])} --fail-on-error"
            ),
            [paths["qcl082_report_out"]],
            depends_on=[
                "transport.direct_wifi_live_topology",
                "transport.product_tcp_media_listener_firewall",
            ],
            clears_gate=True,
        ),
        plan_command(
            "build_protocol_matrix_with_qcl082_product_media",
            "tools.hostessctl.protocol_evidence_matrix",
            "Build protocol matrix with product-media evidence",
            (
                "python tools\\hostessctl\\hostessctl.py connectivity-probe protocol-matrix "
                f"--input {ps_quote(paths['qcl082_report_out'])} "
                f"--out {ps_quote(paths['protocol_matrix_out'])} --fail-on-error"
            ),
            [paths["protocol_matrix_out"]],
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
    mutates_host: bool = False,
    mutates_device: bool = False,
    depends_on: list[str] | None = None,
    clears_gate: bool = False,
) -> dict[str, Any]:
    item = {
        "action_id": action_id,
        "label": label,
        "authority_owner": authority_owner,
        "shell": "powershell",
        "cwd": HOSTESS_REPO_CWD,
        "command": command,
        "acceptance_artifacts": acceptance_artifacts,
        "requires_quest_lease": requires_quest_lease,
        "requires_elevation": False,
        "requires_adb_server_lifecycle_lease": False,
        "mutates_host": mutates_host,
        "mutates_device": mutates_device,
        "clears_gate_when_accepted": clears_gate,
    }
    if depends_on:
        item["depends_on"] = depends_on
    return item


def topology_dependency(path_text: str) -> dict[str, Any]:
    report = report_if_path_exists(path_text)
    topology = object_value(report.get("topology"))
    transport = object_value(report.get("transport"))
    promotion = object_value(report.get("promotion"))
    tokens = [
        topology.get("owner"),
        topology.get("network_provider"),
        topology.get("endpoint_direction"),
        transport.get("family"),
        transport.get("route"),
    ]
    direct_wifi = any("wifi_direct" in normalize_token(token) for token in tokens)
    report_status = str(report.get("status") or "")
    promotion_allowed = promotion.get("allowed") is True
    ready = bool(report) and report_status == "pass" and direct_wifi and promotion_allowed
    if ready:
        evidence = "promoted direct-Wi-Fi topology report is ready for QCL-082 product media"
        issue_codes: list[str] = []
    elif not report:
        evidence = "promoted direct-Wi-Fi topology report is not supplied yet"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_direct_wifi_topology_missing"]
    elif not direct_wifi:
        evidence = "topology report does not describe Wi-Fi Direct"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_direct_wifi_topology_mismatch"]
    elif not promotion_allowed:
        evidence = "direct-Wi-Fi topology report is present but not promoted"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_direct_wifi_topology_not_promoted"]
    else:
        evidence = "direct-Wi-Fi topology report is not pass status"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_direct_wifi_topology_not_pass"]
    return {
        "ready": ready,
        "evidence": evidence,
        "issue_codes": issue_codes,
        "report_path": path_text,
        "report_present": bool(report),
        "report_status": report_status,
        "probe_id": str(report.get("probe_id") or ""),
        "promotion_allowed": promotion_allowed,
        "direct_wifi_topology": direct_wifi,
        "topology_owner": str(topology.get("owner") or ""),
        "topology_network_provider": str(topology.get("network_provider") or ""),
        "transport_family": str(transport.get("family") or ""),
        "transport_route": str(transport.get("route") or ""),
    }


def firewall_dependency(path_text: str) -> dict[str, Any]:
    report = report_if_path_exists(path_text)
    rule = object_value(report.get("rule"))
    verification = object_value(report.get("verification"))
    listener_firewall = object_value(verification.get("listener_firewall"))
    if not listener_firewall:
        listener_firewall = object_value(object_value(verification.get("network_profile")).get("listener_firewall"))
    report_status = str(report.get("status") or "")
    protocol = str(listener_firewall.get("protocol") or rule.get("protocol") or "").upper()
    port = int_value(listener_firewall.get("port")) or int_value(rule.get("local_port")) or 0
    program = str(listener_firewall.get("program") or rule.get("program") or "")
    product_rule_verified = (
        verification.get("product_rule_verified") is True
        or listener_firewall.get("product_rule_verified") is True
    )
    allowed_on_active_profile = (
        verification.get("allowed_on_active_profile") is True
        or listener_firewall.get("allowed_on_active_profile") is True
    )
    diagnostic_program = diagnostic_python_program_path(program)
    ready = (
        bool(report)
        and report_status == "pass"
        and protocol == "TCP"
        and port == DEFAULT_QCL082_RMANVID1_MEDIA_PORT
        and product_rule_verified
        and allowed_on_active_profile
        and not diagnostic_program
    )
    if ready:
        evidence = "verified product Hostess/WPF TCP listener firewall report is ready"
        issue_codes: list[str] = []
    elif not report:
        evidence = "QCL-082 product TCP listener firewall report is not supplied yet"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_firewall_missing"]
    elif protocol != "TCP" or port != DEFAULT_QCL082_RMANVID1_MEDIA_PORT:
        evidence = "firewall report does not verify TCP/9079 for RMANVID1 media"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_firewall_wrong_port"]
    elif diagnostic_program:
        evidence = "firewall report is scoped to a diagnostic program instead of Hostess/WPF"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_firewall_diagnostic_program"]
    elif not product_rule_verified:
        evidence = "firewall report does not verify the product-scoped Hostess/WPF rule"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_firewall_product_rule_missing"]
    elif not allowed_on_active_profile:
        evidence = "firewall report is not allowed on the active Windows profile"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_firewall_profile_blocked"]
    else:
        evidence = "firewall report is present but not pass status"
        issue_codes = ["hostess.issue.connectivity_probe.product_media_firewall_not_pass"]
    return {
        "ready": ready,
        "evidence": evidence,
        "issue_codes": issue_codes,
        "report_path": path_text,
        "report_present": bool(report),
        "report_status": report_status,
        "protocol": protocol,
        "port": port,
        "program": program,
        "product_rule_verified": product_rule_verified,
        "allowed_on_active_profile": allowed_on_active_profile,
        "diagnostic_program": diagnostic_program,
    }


def report_if_path_exists(path_text: str) -> dict[str, Any]:
    if not path_text or path_text.startswith("<"):
        return {}
    return read_json_file(Path(path_text))


def quest_lease_metadata(task: str) -> dict[str, Any]:
    return {
        "manager": "Agent Board",
        "resource": QUEST_LEASE_RESOURCE,
        "duration": QUEST_LEASE_DURATION,
        "task": task,
        "reserve_command": (
            f"& '{AGENT_BOARD_SCRIPT}' reserve '{QUEST_LEASE_RESOURCE}' "
            f"--duration {QUEST_LEASE_DURATION} --task '{task}'"
        ),
        "release_command": f"& '{AGENT_BOARD_SCRIPT}' release '<quest-lease-id>' --result done",
        "adb_server_lifecycle_policy": (
            "Use adb-server:lifecycle only for disruptive daemon lifecycle "
            "or Wi-Fi ADB setup/recovery. Ordinary ADB commands stay serial-scoped."
        ),
    }


def value(args: argparse.Namespace, name: str, default: Any) -> str:
    return str(getattr(args, name, default) or default)


def int_value(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def normalize_token(raw: Any) -> str:
    return str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")


def ps_quote(raw: str) -> str:
    return "'" + str(raw).replace("'", "''") + "'"


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "PRODUCT_MEDIA_DIRECT_WIFI_PLAN_SCHEMA",
    "qcl082_product_media_direct_wifi_plan",
    "run_qcl082_product_media_direct_wifi_plan",
]
