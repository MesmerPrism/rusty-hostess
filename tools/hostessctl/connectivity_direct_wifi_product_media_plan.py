"""Direct-Wi-Fi plus product-media acceptance plan artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl import connectivity_media_product_plan as product_plan
from tools.hostessctl import connectivity_topology_lifecycle_plan as lifecycle_plan
from tools.hostessctl.connectivity_probe_common import (
    check_row,
    issue_row,
    object_value,
    read_json_file,
)


DIRECT_WIFI_PRODUCT_MEDIA_PLAN_SCHEMA = (
    "rusty.hostess.direct_wifi_product_media_acceptance_plan.v1"
)
DEFAULT_ACCEPTANCE_PLAN = (
    r"target\connectivity-probe\direct-wifi-product-media-acceptance-plan.json"
)
DEFAULT_TRANSPORT_GATES = (
    r"target\companion-report\direct-wifi-product-media-transport-gates.json"
)
DEFAULT_COMPANION_PROJECTION = (
    r"target\companion-report\direct-wifi-product-media-projection.json"
)


def run_direct_wifi_product_media_plan(
    args: argparse.Namespace,
    *,
    clock_func: Any | None = None,
) -> int:
    """Write the read-only acceptance plan for the remaining direct-Wi-Fi gates."""

    clock = clock_func or (lambda: datetime.now(UTC))
    report = direct_wifi_product_media_plan(args, observed_at=clock())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if getattr(args, "fail_on_error", False) and report["status"] not in {"planned", "pass"}:
        return 2
    return 0


def direct_wifi_product_media_plan(
    args: argparse.Namespace,
    *,
    observed_at: datetime,
) -> dict[str, Any]:
    """Return a CLI/WPF-equivalent plan that composes the existing owners."""

    paths = acceptance_plan_paths(args)
    qcl040_lifecycle = lifecycle_plan.lifecycle_dependency(
        paths["qcl040_lifecycle_report"],
        "QCL-040",
    )
    qcl041_lifecycle = lifecycle_plan.lifecycle_dependency(
        paths["qcl041_lifecycle_report"],
        "QCL-041",
    )
    topology_candidates = [
        {
            "candidate_id": "explicit_promoted_topology",
            "summary": product_plan.topology_dependency(paths["promoted_topology_report"]),
        },
        {
            "candidate_id": "qcl041_lifecycle_topology",
            "summary": product_plan.topology_dependency(paths["qcl041_topology_report"]),
        },
        {
            "candidate_id": "qcl040_lifecycle_topology",
            "summary": product_plan.topology_dependency(paths["qcl040_topology_report"]),
        },
    ]
    selected_topology = select_topology_dependency(topology_candidates)
    firewall = product_plan.firewall_dependency(paths["firewall_report"])
    qcl082_media = qcl082_product_media_dependency(paths["qcl082_report"])

    qcl040_plan = lifecycle_plan.wifi_direct_lifecycle_plan(
        lifecycle_args(args, "QCL-040", paths),
        observed_at=observed_at,
    )
    qcl041_plan = lifecycle_plan.wifi_direct_lifecycle_plan(
        lifecycle_args(args, "QCL-041", paths),
        observed_at=observed_at,
    )
    qcl082_plan = product_plan.qcl082_product_media_direct_wifi_plan(
        product_args(args, paths, selected_topology),
        observed_at=observed_at,
    )
    preflight = direct_wifi_preflight_summary(
        qcl040_plan,
        qcl041_plan,
        direct_wifi_topology_ready=selected_topology["ready"],
    )

    commands = (
        subplan_writer_commands(args, paths)
        + prefixed_commands("qcl040", qcl040_plan)
        + prefixed_commands("qcl041", qcl041_plan)
        + prefixed_commands("qcl082", qcl082_plan)
        + follow_on_projection_commands(paths)
    )
    lifecycle_source_ready = qcl040_lifecycle["ready"] or qcl041_lifecycle["ready"]
    direct_wifi_topology_ready = selected_topology["ready"]
    ready_for_receiver_capture = direct_wifi_topology_ready and firewall["ready"]
    product_media_ready = qcl082_media["ready"]
    all_remaining_gates_ready = direct_wifi_topology_ready and product_media_ready
    checks = [
        check_row(
            "direct_wifi_product_media.acceptance_plan_authority",
            "pass",
            "Hostess composes existing plan/evidence owners; WPF renders the result only",
            observed={
                "plan_owner": "tools.hostessctl.connectivity_direct_wifi_product_media_plan",
                "lifecycle_plan_owner": "tools.hostessctl.connectivity_topology_lifecycle_plan",
                "lifecycle_normalizer_owner": "tools.hostessctl.connectivity_topology_lifecycle",
                "product_media_plan_owner": "tools.hostessctl.connectivity_media_product_plan",
                "receiver_owner": "tools.hostessctl.connectivity_media_receiver",
                "firewall_owner": "tools.hostessctl.connectivity_firewall",
                "promotion_owner": "tools.hostessctl.protocol_evidence_matrix",
                "frontend_role": "requester_inspector",
            },
        ),
        check_row(
            "direct_wifi_product_media.protocol_plane_separation",
            "pass",
            (
                "Manifold/WebSocket carries low-rate start_source command/control; "
                "RMANVID1 binary TCP carries high-rate media; promoted direct Wi-Fi "
                "proves the product topology"
            ),
            observed={
                "command_control_plane": "manifold_websocket_command_ack",
                "media_payload_plane": "binary_tcp_rmanvid1",
                "topology_plane": "promoted_qcl040_or_qcl041_direct_wifi",
                "json_allowed_for_media_payload": False,
            },
        ),
        check_row(
            "direct_wifi_product_media.lifecycle_source_dependency",
            "pass" if lifecycle_source_ready else "planned",
            (
                "a live lifecycle source artifact is ready for topology normalization"
                if lifecycle_source_ready
                else "no live direct-Wi-Fi lifecycle source artifact is ready yet"
            ),
            observed={
                "qcl040": qcl040_lifecycle,
                "qcl041": qcl041_lifecycle,
            },
            issue_codes=sorted(
                set(qcl040_lifecycle["issue_codes"] + qcl041_lifecycle["issue_codes"])
            ),
        ),
        check_row(
            "direct_wifi_product_media.direct_wifi_topology_dependency",
            "pass" if direct_wifi_topology_ready else "planned",
            selected_topology["evidence"],
            observed=selected_topology,
            issue_codes=selected_topology["issue_codes"],
        ),
        check_row(
            "direct_wifi_product_media.direct_wifi_preflight_observation",
            preflight["status"],
            preflight["evidence"],
            observed=preflight,
            issue_codes=preflight["issue_codes"],
        ),
        check_row(
            "direct_wifi_product_media.product_listener_firewall_dependency",
            "pass" if firewall["ready"] else "planned",
            firewall["evidence"],
            observed=firewall,
            issue_codes=firewall["issue_codes"],
        ),
        check_row(
            "direct_wifi_product_media.qcl082_product_media_dependency",
            "pass" if product_media_ready else "planned",
            qcl082_media["evidence"],
            observed=qcl082_media,
            issue_codes=qcl082_media["issue_codes"],
        ),
        check_row(
            "direct_wifi_product_media.command_chain",
            "pass",
            "acceptance plan lists the lifecycle, product-media, matrix, projection, and gate commands",
            observed={
                "action_ids": [str(command.get("action_id") or "") for command in commands],
                "live_action_count": sum(1 for command in commands if command.get("requires_quest_lease")),
                "elevated_action_count": sum(1 for command in commands if command.get("requires_elevation")),
            },
        ),
    ]

    return {
        "schema": DIRECT_WIFI_PRODUCT_MEDIA_PLAN_SCHEMA,
        "schema_version": 1,
        "plan_id": value(args, "plan_id", "direct-wifi-product-media-acceptance"),
        "observed_at_utc": isoformat_utc(observed_at),
        "status": "pass" if all_remaining_gates_ready else "planned",
        "product_gates": [
            "transport.direct_wifi_live_topology",
            "transport.product_tcp_media_listener_firewall",
            "transport.product_tcp_media_over_direct_wifi",
        ],
        "authority": {
            "plan_owner": "tools.hostessctl.connectivity_direct_wifi_product_media_plan",
            "lifecycle_plan_owner": "tools.hostessctl.connectivity_topology_lifecycle_plan",
            "lifecycle_normalizer_owner": "tools.hostessctl.connectivity_topology_lifecycle",
            "product_media_plan_owner": "tools.hostessctl.connectivity_media_product_plan",
            "command_request_owner": "tools.hostessctl.bridge_command_routes",
            "live_command_owner": "tools.hostessctl.bridge_command_live_android_routes",
            "runtime_status_owner": "tools.hostessctl.connectivity_media",
            "receiver_owner": "tools.hostessctl.connectivity_media_receiver",
            "firewall_owner": "tools.hostessctl.connectivity_firewall",
            "promotion_owner": "tools.hostessctl.protocol_evidence_matrix",
            "frontend_role": "requester_inspector",
        },
        "policy": {
            "read_only_plan": True,
            "runs_adb": False,
            "runs_lifecycle_harness": False,
            "runs_firewall_mutation": False,
            "parses_media_payload": False,
            "requires_quest_lease_for_live_steps": True,
            "requires_adb_server_lifecycle_lease": False,
            "adb_server_lifecycle_policy": (
                "Use adb-server:lifecycle only for disruptive daemon lifecycle "
                "or Wi-Fi ADB setup/recovery. Ordinary ADB commands stay serial-scoped."
            ),
            "elevated_firewall_policy": (
                "Firewall apply/remove work stays in connectivity_firewall and should be "
                "run through its generated UAC handoff when elevation is needed."
            ),
        },
        "lease": product_plan.quest_lease_metadata(
            "direct-Wi-Fi product media validation",
            serial=value(args, "serial", "<quest-serial>"),
        ),
        "dependencies": [
            {
                "gate_id": "transport.direct_wifi_live_topology",
                "ready": direct_wifi_topology_ready,
                "authority_owner": "tools.hostessctl.connectivity_topology_lifecycle",
                "selected": selected_topology,
                "candidates": topology_candidates,
            },
            {
                "gate_id": "transport.product_tcp_media_listener_firewall",
                "ready": firewall["ready"],
                "artifact": paths["firewall_report"],
                "authority_owner": "tools.hostessctl.connectivity_firewall",
                "summary": firewall,
            },
            {
                "gate_id": "transport.product_tcp_media_over_direct_wifi",
                "ready": product_media_ready,
                "artifact": paths["qcl082_report"],
                "authority_owner": "tools.hostessctl.connectivity_media_receiver",
                "summary": qcl082_media,
            },
        ],
        "readiness": {
            "lifecycle_source_ready_for_normalization": lifecycle_source_ready,
            "direct_wifi_preflight_observed": preflight["observed"],
            "direct_wifi_preflight_blocked": preflight["blocked"],
            "direct_wifi_topology_ready": direct_wifi_topology_ready,
            "product_listener_firewall_ready": firewall["ready"],
            "ready_for_qcl082_receiver_capture": ready_for_receiver_capture,
            "product_tcp_media_over_direct_wifi_ready": product_media_ready,
            "all_remaining_transport_gates_ready": all_remaining_gates_ready,
            "live_steps_require_quest_lease": True,
            "firewall_mutation_required_by_plan": False,
            "headset_mutation_required_by_plan": False,
            "host_mutation_required_by_plan": False,
        },
        "artifacts": paths,
        "subplans": {
            "qcl040_wifi_direct_lifecycle_plan": qcl040_plan,
            "qcl041_wifi_direct_lifecycle_plan": qcl041_plan,
            "qcl082_product_media_direct_wifi_plan": qcl082_plan,
        },
        "commands": commands,
        "checks": checks,
        "issues": plan_issues(
            qcl040_lifecycle,
            qcl041_lifecycle,
            selected_topology,
            firewall,
            qcl082_media,
            preflight if not direct_wifi_topology_ready else {},
        ),
        "next_step": next_step(
            lifecycle_source_ready=lifecycle_source_ready,
            preflight_observed=preflight["observed"],
            direct_wifi_topology_ready=direct_wifi_topology_ready,
            firewall_ready=firewall["ready"],
            qcl082_ready=product_media_ready,
        ),
    }


def direct_wifi_preflight_summary(
    qcl040_plan: dict[str, Any],
    qcl041_plan: dict[str, Any],
    *,
    direct_wifi_topology_ready: bool,
) -> dict[str, Any]:
    observations = {
        "qcl040": object_value(object_value(qcl040_plan.get("observations")).get("preflight")),
        "qcl041": object_value(object_value(qcl041_plan.get("observations")).get("preflight")),
    }
    observed = any(item.get("report_present") is True for item in observations.values())
    issue_codes = {
        str(code)
        for item in observations.values()
        for code in item.get("issue_codes", [])
        if str(code)
    }
    if observed:
        issue_codes.discard("hostess.issue.connectivity_probe.wifi_direct_live_preflight_missing")
    issue_codes = sorted(issue_codes)
    blocked = any(item.get("blocked") is True for item in observations.values())
    if direct_wifi_topology_ready:
        status = "skipped"
        evidence = "promoted direct-Wi-Fi topology is already supplied; live preflight blockers do not gate this plan"
        issue_codes = []
        blocked = False
    elif blocked:
        status = "blocked"
        evidence = "live Wi-Fi Direct preflight exists and records blockers"
    elif observed:
        status = "planned"
        evidence = "live Wi-Fi Direct preflight exists, but lifecycle source evidence is still required for promotion"
    else:
        status = "planned"
        evidence = "live Wi-Fi Direct preflight has not been supplied for QCL-040 or QCL-041"
    return {
        "status": status,
        "observed": observed,
        "blocked": blocked,
        "issue_codes": issue_codes,
        "evidence": evidence,
        "qcl040": observations["qcl040"],
        "qcl041": observations["qcl041"],
    }


def acceptance_plan_paths(args: argparse.Namespace) -> dict[str, str]:
    return {
        "acceptance_plan_out": value(args, "out", DEFAULT_ACCEPTANCE_PLAN),
        "qcl040_lifecycle_plan_out": value(
            args,
            "qcl040_lifecycle_plan_out",
            lifecycle_plan.DEFAULT_QCL040_TOPOLOGY.replace(
                "live-wifi-direct-lifecycle.json",
                "wifi-direct-lifecycle-plan.json",
            ),
        ),
        "qcl041_lifecycle_plan_out": value(
            args,
            "qcl041_lifecycle_plan_out",
            lifecycle_plan.DEFAULT_QCL041_TOPOLOGY.replace(
                "live-wifi-direct-lifecycle.json",
                "wifi-direct-lifecycle-plan.json",
            ),
        ),
        "qcl082_product_plan_out": value(
            args,
            "qcl082_product_plan_out",
            r"target\connectivity-probe\qcl082-product-media-direct-wifi-plan.json",
        ),
        "qcl040_preflight_report": value(
            args,
            "qcl040_preflight_report",
            lifecycle_plan.DEFAULT_QCL040_PREFLIGHT,
        ),
        "qcl041_preflight_report": value(
            args,
            "qcl041_preflight_report",
            lifecycle_plan.DEFAULT_QCL041_PREFLIGHT,
        ),
        "qcl040_lifecycle_report": value(
            args,
            "qcl040_lifecycle_report",
            lifecycle_plan.DEFAULT_QCL040_SOURCE,
        ),
        "qcl041_lifecycle_report": value(
            args,
            "qcl041_lifecycle_report",
            lifecycle_plan.DEFAULT_QCL041_SOURCE,
        ),
        "qcl040_topology_report": value(
            args,
            "qcl040_topology_report",
            lifecycle_plan.DEFAULT_QCL040_TOPOLOGY,
        ),
        "qcl041_topology_report": value(
            args,
            "qcl041_topology_report",
            lifecycle_plan.DEFAULT_QCL041_TOPOLOGY,
        ),
        "promoted_topology_report": value(
            args,
            "promoted_topology_report",
            product_plan.DEFAULT_PROMOTED_TOPOLOGY_REPORT,
        ),
        "firewall_report": value(args, "firewall_report", product_plan.DEFAULT_FIREWALL_REPORT),
        "qcl082_report": value(args, "qcl082_report", product_plan.DEFAULT_QCL082_PRODUCT_REPORT),
        "protocol_matrix_out": value(args, "protocol_matrix_out", product_plan.DEFAULT_PROTOCOL_MATRIX),
        "projection_out": value(args, "projection_out", DEFAULT_COMPANION_PROJECTION),
        "transport_gates_out": value(args, "transport_gates_out", DEFAULT_TRANSPORT_GATES),
    }


def lifecycle_args(args: argparse.Namespace, probe_id: str, paths: dict[str, str]) -> argparse.Namespace:
    qcl040 = probe_id == "QCL-040"
    return argparse.Namespace(
        out=paths["qcl040_lifecycle_plan_out"] if qcl040 else paths["qcl041_lifecycle_plan_out"],
        probe_id=probe_id,
        plan_id=f"{probe_id.lower()}-wifi-direct-lifecycle",
        adb=value(args, "adb", lifecycle_plan.DEFAULT_ADB),
        serial=value(args, "serial", "<quest-serial>"),
        preflight_report_out=paths["qcl040_preflight_report"] if qcl040 else paths["qcl041_preflight_report"],
        template_out="",
        lifecycle_report=paths["qcl040_lifecycle_report"] if qcl040 else paths["qcl041_lifecycle_report"],
        topology_report_out=paths["qcl040_topology_report"] if qcl040 else paths["qcl041_topology_report"],
        fail_on_error=False,
    )


def product_args(
    args: argparse.Namespace,
    paths: dict[str, str],
    selected_topology: dict[str, Any],
) -> argparse.Namespace:
    topology_path = str(selected_topology.get("report_path") or "") or paths["promoted_topology_report"]
    return argparse.Namespace(
        out=paths["qcl082_product_plan_out"],
        plan_id="qcl082-product-media-direct-wifi",
        adb=value(args, "adb", product_plan.DEFAULT_ADB),
        serial=value(args, "serial", "<quest-serial>"),
        program=value(args, "program", ""),
        bind_host=value(args, "bind_host", "0.0.0.0"),
        port=int_value(value(args, "port", product_plan.DEFAULT_QCL082_RMANVID1_MEDIA_PORT))
        or product_plan.DEFAULT_QCL082_RMANVID1_MEDIA_PORT,
        max_packets=int_value(value(args, "max_packets", 240)) or 240,
        capture_kind=product_capture_kind(args),
        start_source_request_out="",
        start_source_bridge_evidence_out="",
        start_source_execution_out="",
        start_source_validation_out="",
        runtime_status_report_out="",
        promoted_topology_report=topology_path,
        firewall_report=paths["firewall_report"],
        capture_out="",
        sidecar_out="",
        receiver_result_out="",
        qcl082_report_out=paths["qcl082_report"],
        protocol_matrix_out=paths["protocol_matrix_out"],
        quest_lease_id=value(args, "quest_lease_id", product_plan.DEFAULT_QUEST_LEASE_ID),
        quest_lease_resource=product_plan.quest_lease_resource_value(
            value(args, "serial", "<quest-serial>"),
            value(args, "quest_lease_resource", product_plan.DEFAULT_QUEST_LEASE_RESOURCE),
        ),
        fail_on_error=False,
    )


def select_topology_dependency(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    for candidate in candidates:
        summary = dict(object_value(candidate.get("summary")))
        if summary.get("ready") is True:
            summary["selected_candidate_id"] = str(candidate.get("candidate_id") or "")
            return summary
    issue_codes = sorted(
        {
            str(code)
            for candidate in candidates
            for code in object_value(candidate.get("summary")).get("issue_codes", [])
            if str(code)
        }
    )
    present = [
        candidate
        for candidate in candidates
        if object_value(candidate.get("summary")).get("report_present") is True
    ]
    return {
        "ready": False,
        "evidence": (
            "no promoted direct-Wi-Fi topology report is ready"
            if not present
            else "direct-Wi-Fi topology candidate reports are present but not promotable"
        ),
        "issue_codes": issue_codes
        or ["hostess.issue.connectivity_probe.product_media_direct_wifi_topology_missing"],
        "report_path": "",
        "report_present": bool(present),
        "selected_candidate_id": "",
        "candidate_count": len(candidates),
    }


def qcl082_product_media_dependency(path_text: str) -> dict[str, Any]:
    report = report_if_path_exists(path_text)
    measurements = object_value(report.get("measurements"))
    capture = object_value(report.get("media_stream_receiver_capture"))
    source = object_value(capture.get("source"))
    product_topology = object_value(capture.get("product_topology"))
    product_firewall = object_value(capture.get("product_listener_firewall"))
    promotion = object_value(report.get("promotion"))
    report_status = str(report.get("status") or "")
    probe_id = str(report.get("probe_id") or "")
    capture_kind = str(capture.get("capture_kind") or "")
    live_capture = capture.get("live_capture") is True or capture_kind in {
        "live_broker_stream",
        "live_quest_runtime_stream",
    }
    topology_ready = (
        measurements.get("media_product_topology_ready") is True
        or product_topology.get("ready") is True
    )
    firewall_ready = (
        measurements.get("media_product_listener_firewall_verified") is True
        or product_firewall.get("ready") is True
    )
    promotion_allowed = promotion.get("allowed") is True
    broker_or_quest_source = source.get("broker_or_quest_source") is True
    ready = (
        bool(report)
        and report_status == "pass"
        and probe_id == "QCL-082"
        and promotion_allowed
        and live_capture
        and broker_or_quest_source
        and topology_ready
        and firewall_ready
    )
    if ready:
        evidence = "QCL-082 RMANVID1 product media report proves TCP media over promoted direct-Wi-Fi"
        issue_codes: list[str] = []
    elif not report:
        evidence = "QCL-082 RMANVID1 product media report is not supplied yet"
        issue_codes = ["hostess.issue.connectivity_probe.qcl082_product_media_report_missing"]
    elif probe_id != "QCL-082":
        evidence = "supplied product media report is not QCL-082"
        issue_codes = ["hostess.issue.connectivity_probe.qcl082_product_media_probe_mismatch"]
    elif report_status != "pass":
        evidence = "QCL-082 product media report is present but not pass status"
        issue_codes = ["hostess.issue.connectivity_probe.qcl082_product_media_not_pass"]
    elif not promotion_allowed:
        evidence = "QCL-082 product media report is not promotion-allowed"
        issue_codes = ["hostess.issue.connectivity_probe.qcl082_product_media_not_promoted"]
    elif not live_capture or not broker_or_quest_source:
        evidence = "QCL-082 receiver capture is not live broker/Quest runtime media"
        issue_codes = ["hostess.issue.connectivity_probe.qcl082_product_media_not_live_runtime"]
    elif not topology_ready:
        evidence = "QCL-082 report is not paired with promoted direct-Wi-Fi topology"
        issue_codes = ["hostess.issue.connectivity_probe.qcl082_product_media_topology_missing"]
    elif not firewall_ready:
        evidence = "QCL-082 report is not paired with verified product TCP listener firewall"
        issue_codes = ["hostess.issue.connectivity_probe.qcl082_product_media_firewall_missing"]
    else:
        evidence = "QCL-082 product media report is present but incomplete"
        issue_codes = ["hostess.issue.connectivity_probe.qcl082_product_media_incomplete"]
    return {
        "ready": ready,
        "evidence": evidence,
        "issue_codes": issue_codes,
        "report_path": path_text,
        "report_present": bool(report),
        "report_status": report_status,
        "probe_id": probe_id,
        "promotion_allowed": promotion_allowed,
        "capture_kind": capture_kind,
        "live_capture": live_capture,
        "broker_or_quest_source": broker_or_quest_source,
        "direct_wifi_product_topology_ready": topology_ready,
        "product_listener_firewall_verified": firewall_ready,
        "media_frames_received": measurements.get("media_frames_received"),
        "media_bytes_received": measurements.get("media_bytes_received"),
    }


def plan_issues(*dependencies: dict[str, Any]) -> list[dict[str, Any]]:
    issue_codes = sorted(
        {
            str(code)
            for dependency in dependencies
            for code in dependency.get("issue_codes", [])
            if str(code)
        }
    )
    return [
        issue_row(code, "warning", "direct-Wi-Fi product-media acceptance dependency is not ready")
        for code in issue_codes
    ]


def subplan_writer_commands(args: argparse.Namespace, paths: dict[str, str]) -> list[dict[str, Any]]:
    adb = value(args, "adb", lifecycle_plan.DEFAULT_ADB)
    serial = value(args, "serial", "<quest-serial>")
    quest_lease_id = value(args, "quest_lease_id", product_plan.DEFAULT_QUEST_LEASE_ID)
    quest_lease_resource = product_plan.quest_lease_resource_value(
        serial,
        value(args, "quest_lease_resource", product_plan.DEFAULT_QUEST_LEASE_RESOURCE),
    )
    return [
        plan_command(
            "write_qcl040_wifi_direct_lifecycle_plan",
            "tools.hostessctl.connectivity_topology_lifecycle_plan",
            "Write QCL-040 Wi-Fi Direct lifecycle plan",
            (
                "python tools\\hostessctl\\hostessctl.py "
                "connectivity-probe wifi-direct-lifecycle-plan "
                "--probe-id QCL-040 "
                f"--out {ps_quote(paths['qcl040_lifecycle_plan_out'])} "
                f"--preflight-report-out {ps_quote(paths['qcl040_preflight_report'])} "
                f"--adb {ps_quote(adb)} --serial {ps_quote(serial)}"
            ),
            [paths["qcl040_lifecycle_plan_out"]],
        ),
        plan_command(
            "write_qcl041_wifi_direct_lifecycle_plan",
            "tools.hostessctl.connectivity_topology_lifecycle_plan",
            "Write QCL-041 Wi-Fi Direct lifecycle plan",
            (
                "python tools\\hostessctl\\hostessctl.py "
                "connectivity-probe wifi-direct-lifecycle-plan "
                "--probe-id QCL-041 "
                f"--out {ps_quote(paths['qcl041_lifecycle_plan_out'])} "
                f"--preflight-report-out {ps_quote(paths['qcl041_preflight_report'])} "
                f"--adb {ps_quote(adb)} --serial {ps_quote(serial)}"
            ),
            [paths["qcl041_lifecycle_plan_out"]],
        ),
        plan_command(
            "write_qcl082_product_media_direct_wifi_plan",
            "tools.hostessctl.connectivity_media_product_plan",
            "Write QCL-082 product-media direct-Wi-Fi plan",
            (
                "python tools\\hostessctl\\hostessctl.py "
                "connectivity-probe qcl082-product-media-plan "
                f"--out {ps_quote(paths['qcl082_product_plan_out'])} "
                f"--promoted-topology-report {ps_quote(paths['promoted_topology_report'])} "
                f"--firewall-report {ps_quote(paths['firewall_report'])} "
                f"--adb {ps_quote(adb)} --serial {ps_quote(serial)} "
                f"--quest-lease-id {ps_quote(quest_lease_id)} "
                f"--quest-lease-resource {ps_quote(quest_lease_resource)}"
            ),
            [paths["qcl082_product_plan_out"]],
        ),
    ]


def prefixed_commands(prefix: str, plan: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for command in plan.get("commands", []):
        if not isinstance(command, dict):
            continue
        item = dict(command)
        action_id = str(item.get("action_id") or "")
        item["action_id"] = f"{prefix}_{action_id}" if action_id else prefix
        result.append(item)
    return result


def follow_on_projection_commands(paths: dict[str, str]) -> list[dict[str, Any]]:
    return [
        plan_command(
            "build_protocol_matrix_after_qcl082_product_media",
            "tools.hostessctl.protocol_evidence_matrix",
            "Build protocol matrix after QCL-082 product media",
            (
                "python tools\\hostessctl\\hostessctl.py connectivity-probe protocol-matrix "
                f"--input {ps_quote(paths['qcl082_report'])} "
                f"--out {ps_quote(paths['protocol_matrix_out'])} --fail-on-error"
            ),
            [paths["protocol_matrix_out"]],
        ),
        plan_command(
            "project_companion_report_after_product_media",
            "tools.hostessctl.companion_report_projection",
            "Project companion report after product media",
            (
                "python tools\\hostessctl\\hostessctl.py companion-report projection "
                f"--protocol-matrix {ps_quote(paths['protocol_matrix_out'])} "
                f"--firewall-rule {ps_quote(paths['firewall_report'])} "
                f"--direct-wifi-product-media-plan {ps_quote(paths['acceptance_plan_out'])} "
                f"--out {ps_quote(paths['projection_out'])} "
                "--include-protocol-matrix-inputs"
            ),
            [paths["projection_out"]],
        ),
        plan_command(
            "build_transport_gates_after_product_media",
            "tools.hostessctl.companion_transport_gates",
            "Build transport gate report after product media",
            (
                "python tools\\hostessctl\\hostessctl.py companion-report transport-gates "
                f"--projection {ps_quote(paths['projection_out'])} "
                f"--out {ps_quote(paths['transport_gates_out'])} --fail-on-pending"
            ),
            [paths["transport_gates_out"]],
        ),
    ]


def plan_command(
    action_id: str,
    authority_owner: str,
    label: str,
    command: str,
    acceptance_artifacts: list[str],
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "label": label,
        "authority_owner": authority_owner,
        "available_now": True,
        "shell": "powershell",
        "cwd": product_plan.HOSTESS_REPO_CWD,
        "command": command,
        "acceptance_artifacts": acceptance_artifacts,
        "requires_quest_lease": False,
        "requires_elevation": False,
        "requires_adb_server_lifecycle_lease": False,
        "mutates_host": False,
        "mutates_device": False,
        "clears_gate_when_accepted": False,
    }


def next_step(
    *,
    lifecycle_source_ready: bool,
    preflight_observed: bool,
    direct_wifi_topology_ready: bool,
    firewall_ready: bool,
    qcl082_ready: bool,
) -> str:
    if qcl082_ready:
        return "Build the protocol matrix/projection/transport gates and confirm no product transport gates remain."
    if direct_wifi_topology_ready and firewall_ready:
        return (
            "Reserve quest:<quest-serial>, run the QCL-082 start_source and "
            "RMANVID1 receiver capture, then fold the capture into QCL-082."
        )
    if direct_wifi_topology_ready:
        return "Verify or apply the product Hostess/WPF TCP listener firewall rule for QCL-082."
    if lifecycle_source_ready:
        return "Normalize the ready lifecycle source into a promoted QCL-040/QCL-041 topology report."
    if preflight_observed:
        return (
            "Use the preflight blockers to finish the external Wi-Fi Direct peer "
            "harness, then collect leased lifecycle source evidence with peer "
            "discovery, group roles, bounded TCP exchange, and cleanup."
        )
    return (
        "Refresh live QCL-040/QCL-041 Wi-Fi Direct preflight under a "
        "quest:<quest-serial> lease, then collect lifecycle evidence with peer "
        "discovery, group roles, bounded TCP exchange, and cleanup."
    )


def report_if_path_exists(path_text: str) -> dict[str, Any]:
    if not path_text or path_text.startswith("<"):
        return {}
    return read_json_file(Path(path_text))


def value(args: argparse.Namespace, name: str, default: Any) -> str:
    return str(getattr(args, name, default) or default)


def int_value(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def product_capture_kind(args: argparse.Namespace) -> str:
    raw = value(args, "capture_kind", "live_broker_stream")
    if raw in {"live_broker_stream", "live_quest_runtime_stream"}:
        return raw
    return "live_broker_stream"


def ps_quote(raw: str) -> str:
    return "'" + str(raw).replace("'", "''") + "'"


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "DIRECT_WIFI_PRODUCT_MEDIA_PLAN_SCHEMA",
    "direct_wifi_product_media_plan",
    "run_direct_wifi_product_media_plan",
]
