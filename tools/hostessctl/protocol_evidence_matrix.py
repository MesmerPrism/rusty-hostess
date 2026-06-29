"""Protocol promotion evidence matrix for Quest device-link capabilities."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl import device_link_report
from tools.hostessctl.connectivity_suite import CONNECTIVITY_SUITE_RUN_SCHEMA


PROTOCOL_EVIDENCE_MATRIX_SCHEMA = "rusty.quest.device_link.protocol_evidence_matrix.v1"
PROTOCOL_EVIDENCE_MATRIX_VALIDATION_SCHEMA = (
    "rusty.quest.device_link.protocol_evidence_matrix.validation.v1"
)
PROMOTABLE_TIERS = {"quest_runtime", "broker_owned"}
VALID_MATRIX_STATUSES = {"pass", "warn", "fail"}
VALID_ROW_STATUSES = {
    "usable",
    "usable_with_warnings",
    "candidate",
    "blocked",
    "missing",
    "rejected",
}


CAPABILITY_PROFILES: list[dict[str, Any]] = [
    {
        "capability_id": "capability.command.hostess_makepad_bridge",
        "probe_id": "QCL-000",
        "transport_kind": "manifold_websocket",
        "semantic_family": "command",
        "authority_owner": "rusty.manifold.command",
        "required_for_fold_in": True,
        "allowed_tiers": ["quest_runtime"],
        "next_cli": (
            "python tools\\hostessctl\\hostessctl.py companion-session run "
            "--out target\\companion-session\\session.json"
        ),
        "promotion_gate": (
            "Manifold command route must show sent, transport_ok, authority_accepted, "
            "runtime_accepted, and applied stages through a Quest runtime subscriber."
        ),
    },
    {
        "capability_id": "capability.telemetry.pose_udp",
        "probe_id": "QCL-080",
        "transport_kind": "udp",
        "semantic_family": "pose_or_low_rate_telemetry",
        "authority_owner": "rusty.quest.device_link",
        "required_for_fold_in": True,
        "allowed_tiers": ["quest_runtime"],
        "next_cli": (
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
            "--mode live --probe-id QCL-080 --udp-sender-source makepad-runtime "
            "--udp-listener-helper apps\\hostess-companion-wpf\\bin\\Debug\\net9.0-windows\\HostessCompanion.Wpf.exe "
            "--out target\\connectivity-probe\\qcl080-live.json"
        ),
        "promotion_gate": (
            "QCL-080 must be an app-owned Quest runtime sender with measured packet "
            "receipt and a product-scoped Hostess/WPF listener firewall rule."
        ),
    },
    {
        "capability_id": "capability.biosignal.lsl_clocked_samples",
        "probe_id": "QCL-081",
        "transport_kind": "lsl",
        "semantic_family": "biosignal_or_clocked_samples",
        "authority_owner": "rusty.quest.device_link",
        "required_for_fold_in": True,
        "allowed_tiers": ["quest_runtime", "broker_owned"],
        "next_cli": (
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
            "--mode live --probe-id QCL-081 --lsl-source manifold-lsl-broker "
            "--lsl-manifold-root S:\\Work\\repos\\active\\rusty-manifold "
            "--out target\\connectivity-probe\\qcl081-live-manifold-lsl-broker.json"
        ),
        "promotion_gate": (
            "QCL-081 host-loopback proves only dependency/protocol fit; promotion "
            "requires Quest-runtime or broker-owned live QCL evidence."
        ),
    },
    {
        "capability_id": "capability.control.osc_round_trip",
        "probe_id": "QCL-083",
        "transport_kind": "osc_udp",
        "semantic_family": "control_or_low_rate_telemetry",
        "authority_owner": "rusty.quest.device_link",
        "required_for_fold_in": True,
        "allowed_tiers": ["quest_runtime", "broker_owned"],
        "next_cli": (
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
            "--mode live --probe-id QCL-083 --osc-source quest-runtime "
            "--out target\\connectivity-probe\\qcl083-live-quest-runtime.json"
        ),
        "promotion_gate": (
            "QCL-083 host-loopback proves OSC shape/exchange only; promotion "
            "requires Quest-runtime or broker-owned live QCL evidence."
        ),
    },
    {
        "capability_id": "capability.protocol.zeromq_native_rust",
        "probe_id": "QCL-084",
        "transport_kind": "zeromq",
        "semantic_family": "generic_data_protocol",
        "authority_owner": "rusty.manifold.transport",
        "required_for_fold_in": True,
        "allowed_tiers": ["quest_runtime", "broker_owned"],
        "next_cli": (
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
            "--mode live --probe-id QCL-084 --zeromq-source native-rust-broker "
            "--zeromq-pattern pub-sub --out target\\connectivity-probe\\qcl084-live-broker-owned.json"
        ),
        "promotion_gate": (
            "QCL-084 Manifold adapter loopback is dependency/protocol evidence; "
            "promotion requires broker-owned or Quest-runtime live QCL evidence."
        ),
    },
    {
        "capability_id": "capability.bluetooth.rfcomm_control",
        "probe_id": "QCL-050",
        "transport_kind": "bluetooth_rfcomm",
        "semantic_family": "short_range_control",
        "authority_owner": "rusty.quest.device_link",
        "required_for_fold_in": False,
        "allowed_tiers": ["quest_runtime"],
        "next_cli": (
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
            "--mode live --probe-id QCL-050 --bluetooth-payload-source android-rfcomm "
            "--out target\\connectivity-probe\\qcl050-live-rfcomm.json"
        ),
        "promotion_gate": (
            "RFCOMM needs Windows service discovery, pairing/prompt handling, "
            "payload exchange, reconnect, and cleanup evidence."
        ),
    },
    {
        "capability_id": "capability.bluetooth.ble_gatt_status",
        "probe_id": "QCL-051",
        "transport_kind": "bluetooth_gatt",
        "semantic_family": "short_range_status_or_control",
        "authority_owner": "rusty.quest.device_link",
        "required_for_fold_in": False,
        "allowed_tiers": ["quest_runtime"],
        "next_cli": (
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
            "--mode live --probe-id QCL-051 --bluetooth-payload-source android-ble-gatt "
            "--out target\\connectivity-probe\\qcl051-live-ble-gatt.json"
        ),
        "promotion_gate": (
            "BLE/GATT needs app-owned Quest server payload exchange plus cleanup "
            "and reconnect evidence for reusable promotion."
        ),
    },
    {
        "capability_id": "capability.media.h264_tcp_binary",
        "probe_id": "QCL-082",
        "transport_kind": "tcp_binary",
        "semantic_family": "media",
        "authority_owner": "rusty.quest.device_link",
        "required_for_fold_in": False,
        "allowed_tiers": ["quest_runtime", "broker_owned"],
        "next_cli": (
            "python tools\\hostessctl\\hostessctl.py connectivity-probe run "
            "--mode fixture --probe-id QCL-082 --fixture-profile qcl-082-media-binary-plane-pass "
            "--out target\\connectivity-probe\\qcl082-media-binary-plane-pass.json --fail-on-error"
        ),
        "promotion_gate": (
            "Media stays planned until a binary transport/codec path declares "
            "queue, drop, timestamp, and backpressure policy."
        ),
    },
]


def run_protocol_evidence_matrix(args: argparse.Namespace) -> int:
    report = build_protocol_evidence_matrix(args)
    validation = validate_protocol_evidence_matrix(report)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    validation_out = (
        Path(args.validation_out)
        if getattr(args, "validation_out", None)
        else out.with_name(f"{out.stem}.validation-report.json")
    )
    validation_out.parent.mkdir(parents=True, exist_ok=True)
    validation_out.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if getattr(args, "fail_on_error", False) and validation["status"] != "pass":
        return 2
    return 0


def build_protocol_evidence_matrix(args: argparse.Namespace) -> dict[str, Any]:
    observed_at = utc_now()
    matrix_id = str(getattr(args, "matrix_id", "") or "").strip()
    if not matrix_id:
        matrix_id = f"protocol-evidence-{observed_at.strftime('%Y%m%d-%H%M%S')}"
    artifacts = collect_input_artifacts(args)
    rows = [
        build_matrix_row(profile, artifacts)
        for profile in CAPABILITY_PROFILES
    ]
    summary = matrix_summary(rows)
    status = matrix_status(rows)
    return {
        "$schema": PROTOCOL_EVIDENCE_MATRIX_SCHEMA,
        "schema_version": 1,
        "matrix_id": matrix_id,
        "observed_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "status": status,
        "authority": {
            "descriptor_owner": "rusty.quest.device_link",
            "execution_owner": "rusty.hostess.connectivity_probe",
            "command_authority": "rusty.manifold.command",
            "ui_role": "requester_and_inspector",
            "promotion_policy": (
                "Reusable data-protocol promotion requires Quest-runtime or "
                "broker-owned QCL evidence; host-loopback and fixture reports are "
                "dependency/protocol evidence only."
            ),
        },
        "inputs": artifacts["inputs"],
        "rows": rows,
        "summary": summary,
        "issues": matrix_issues(rows),
    }


def collect_input_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    inputs: list[dict[str, Any]] = []
    probe_reports: dict[str, list[dict[str, Any]]] = {}
    stream_descriptors: dict[str, dict[str, Any]] = {}
    device_link_reports: list[dict[str, Any]] = []

    pending_paths: list[Path] = []
    for raw in argument_values(getattr(args, "input", None)):
        pending_paths.append(Path(str(raw)))
    for raw in argument_values(getattr(args, "suite_run", None)):
        suite_path = Path(str(raw))
        suite = read_json(suite_path)
        inputs.append(input_ref(suite_path, suite, role="suite_run"))
        for artifact in list_value(suite.get("artifacts")):
            path = resolve_artifact_path(
                str(object_value(artifact).get("path") or ""),
                suite_path=suite_path,
            )
            if path:
                pending_paths.append(path)
    pending_paths.extend(latest_artifact_paths(args))

    seen_paths: set[str] = set()
    for path in pending_paths:
        resolved_key = str(path.resolve(strict=False)).lower()
        if resolved_key in seen_paths:
            continue
        seen_paths.add(resolved_key)
        payload = read_json(path)
        if not payload:
            inputs.append(input_ref(path, payload, role="unreadable"))
            continue
        role = classify_payload(payload)
        inputs.append(input_ref(path, payload, role=role))
        if role == "connectivity_probe_report":
            probe_reports.setdefault(str(payload.get("probe_id") or ""), []).append(
                {"path": path, "payload": payload}
            )
        elif role == "stream_capability_descriptor":
            source_probe = object_value(payload.get("source_probe"))
            probe_id = str(source_probe.get("probe_id") or "")
            if probe_id:
                stream_descriptors[probe_id] = {"path": path, "payload": payload}
        elif role == "device_link_report":
            device_link_reports.append({"path": path, "payload": payload})

    return {
        "inputs": inputs,
        "probe_reports": probe_reports,
        "stream_descriptors": stream_descriptors,
        "device_link_reports": device_link_reports,
    }


def latest_artifact_paths(args: argparse.Namespace) -> list[Path]:
    artifact_dirs = [
        Path(raw)
        for raw in argument_values(getattr(args, "latest_artifact_dir", None))
        if raw.strip()
    ]
    probe_ids = [
        raw.strip()
        for raw in argument_values(getattr(args, "latest_probe_id", None))
        if raw.strip()
    ]
    if not probe_ids:
        probe_ids = [str(profile["probe_id"]) for profile in CAPABILITY_PROFILES]

    selected: list[Path] = []
    for artifact_dir in artifact_dirs:
        selected.extend(latest_probe_reports_in_dir(artifact_dir, probe_ids))
    selected.extend(latest_device_link_paths(args))
    selected.extend(latest_stream_capability_paths(args))
    return selected


def latest_probe_reports_in_dir(artifact_dir: Path, probe_ids: list[str]) -> list[Path]:
    if not artifact_dir.exists() or not artifact_dir.is_dir():
        return []

    requested = set(probe_ids)
    latest: dict[str, tuple[int, int, int, str, Path]] = {}
    for path in artifact_dir.rglob("*.json"):
        payload = read_json(path)
        if classify_payload(payload) != "connectivity_probe_report":
            continue
        probe_id = str(payload.get("probe_id") or "")
        if probe_id not in requested:
            continue
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            mtime_ns = 0
        candidate = (
            probe_report_quality_score({"path": path, "payload": payload}),
            probe_report_search_rank(artifact_dir, path),
            mtime_ns,
            str(path),
            path,
        )
        if probe_id not in latest or candidate > latest[probe_id]:
            latest[probe_id] = candidate

    return [latest[probe_id][4] for probe_id in probe_ids if probe_id in latest]


def probe_report_search_rank(artifact_dir: Path, path: Path) -> int:
    """Prefer independent run reports over generated suite artifact copies."""
    try:
        relative = path.relative_to(artifact_dir)
    except ValueError:
        relative = path
    parent_parts = relative.parts[:-1]
    if any(part.endswith("-artifacts") for part in parent_parts):
        return 0
    return 1


def latest_device_link_paths(args: argparse.Namespace) -> list[Path]:
    selected: list[Path] = []
    for raw in argument_values(getattr(args, "latest_device_link_dir", None)):
        if raw.strip():
            selected.extend(latest_payloads_in_dir(Path(raw), "device_link_report"))
    return selected


def latest_stream_capability_paths(args: argparse.Namespace) -> list[Path]:
    artifact_dirs = [
        Path(raw)
        for raw in argument_values(getattr(args, "latest_stream_capability_dir", None))
        if raw.strip()
    ]
    if not artifact_dirs:
        return []

    probe_ids = [
        raw.strip()
        for raw in argument_values(getattr(args, "latest_stream_probe_id", None))
        if raw.strip()
    ]
    if not probe_ids:
        probe_ids = [str(profile["probe_id"]) for profile in CAPABILITY_PROFILES]

    selected: list[Path] = []
    for artifact_dir in artifact_dirs:
        selected.extend(latest_stream_capabilities_in_dir(artifact_dir, probe_ids))
    return selected


def latest_payloads_in_dir(artifact_dir: Path, role: str) -> list[Path]:
    if not artifact_dir.exists() or not artifact_dir.is_dir():
        return []
    latest: tuple[int, str, Path] | None = None
    for path in artifact_dir.rglob("*.json"):
        payload = read_json(path)
        if classify_payload(payload) != role:
            continue
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            mtime_ns = 0
        candidate = (mtime_ns, str(path), path)
        if latest is None or candidate > latest:
            latest = candidate
    return [latest[2]] if latest else []


def latest_stream_capabilities_in_dir(artifact_dir: Path, probe_ids: list[str]) -> list[Path]:
    if not artifact_dir.exists() or not artifact_dir.is_dir():
        return []

    requested = set(probe_ids)
    latest: dict[str, tuple[int, str, Path]] = {}
    for path in artifact_dir.rglob("*.json"):
        payload = read_json(path)
        if classify_payload(payload) != "stream_capability_descriptor":
            continue
        source_probe = object_value(payload.get("source_probe"))
        probe_id = str(source_probe.get("probe_id") or "")
        if probe_id not in requested:
            continue
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            mtime_ns = 0
        candidate = (mtime_ns, str(path), path)
        if probe_id not in latest or candidate > latest[probe_id]:
            latest[probe_id] = candidate

    selected: list[Path] = []
    for probe_id in probe_ids:
        if probe_id not in latest:
            continue
        descriptor_path = latest[probe_id][2]
        descriptor = read_json(descriptor_path)
        source_path = descriptor_source_probe_path(descriptor_path, descriptor)
        if source_path:
            selected.append(source_path)
        selected.append(descriptor_path)
    return selected


def descriptor_source_probe_path(descriptor_path: Path, descriptor: dict[str, Any]) -> Path | None:
    source_probe = object_value(descriptor.get("source_probe"))
    raw_path = str(source_probe.get("artifact_path") or "")
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.exists() or path.is_absolute():
        return path
    candidate = descriptor_path.parent / path.name
    if candidate.exists():
        return candidate
    return path


def build_matrix_row(profile: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    probe_id = str(profile["probe_id"])
    if probe_id == "QCL-000":
        return build_command_row(profile, artifacts)

    reports = object_value(artifacts.get("probe_reports")).get(probe_id, [])
    selected = select_best_probe_report(reports)
    report = object_value(selected.get("payload"))
    report_path = selected.get("path")
    descriptor_entry = object_value(object_value(artifacts.get("stream_descriptors")).get(probe_id))
    descriptor = object_value(descriptor_entry.get("payload"))
    descriptor_path = descriptor_entry.get("path")
    tier = evidence_tier(report)
    promotion = object_value(report.get("promotion"))
    raw_promotion_allowed = promotion.get("allowed") is True
    promotion_allowed = raw_promotion_allowed and tier in set(string_list(profile.get("allowed_tiers")))
    requirements = promotion_requirements(
        profile,
        report=report,
        descriptor=descriptor,
        evidence_tier=tier,
        promotion_allowed=promotion_allowed,
    )
    row_status = protocol_row_status(
        report,
        descriptor=descriptor,
        evidence_tier=tier,
        requirements=requirements,
        promotion_allowed=promotion_allowed,
    )
    promotion_state = protocol_promotion_state(row_status, promotion_allowed)
    return {
        "capability_id": profile["capability_id"],
        "probe_id": probe_id,
        "transport_kind": profile["transport_kind"],
        "semantic_family": profile["semantic_family"],
        "authority_owner": profile["authority_owner"],
        "required_for_fold_in": bool(profile["required_for_fold_in"]),
        "status": row_status,
        "promotion_state": promotion_state,
        "promotion_allowed": promotion_allowed,
        "source_promotion_allowed": raw_promotion_allowed,
        "evidence_tier": tier,
        "allowed_promotion_tiers": profile["allowed_tiers"],
        "promotion_gate": profile["promotion_gate"],
        "missing_gates": [
            row["gate_id"] for row in requirements if row.get("status") != "satisfied"
        ],
        "gate_results": requirements,
        "source": source_summary(report, report_path=report_path),
        "descriptor": descriptor_summary(descriptor, descriptor_path=descriptor_path),
        "measurements": object_value(report.get("measurements")),
        "next_cli": profile["next_cli"],
    }


def build_command_row(profile: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    selected = select_best_device_link_report(list_value(artifacts.get("device_link_reports")))
    report = object_value(selected.get("payload"))
    report_path = selected.get("path")
    if not report:
        return build_command_probe_row(profile, artifacts)
    command = selected_command_result(report)
    command_ok = bool(command) and command.get("status") == "pass" and command.get("applied") is True
    runtime_subscriber = selected_runtime_subscriber(report)
    subscriber_ok = runtime_subscriber.get("status") == "connected"
    requirements = [
        gate_result(
            "gate.qcl000.device_link_report",
            "satisfied" if report else "missing",
            "device-link report loaded" if report else "companion-session device-link report not loaded",
        ),
        gate_result(
            "gate.qcl000.runtime_subscriber",
            "satisfied" if subscriber_ok else "missing",
            "runtime subscriber connected" if subscriber_ok else "runtime subscriber evidence missing",
        ),
        gate_result(
            "gate.qcl000.applied_command_receipt",
            "satisfied" if command_ok else "missing",
            "command result applied through Manifold" if command_ok else "applied command receipt missing",
        ),
    ]
    status = "usable" if all(row["status"] == "satisfied" for row in requirements) else "missing"
    return {
        "capability_id": profile["capability_id"],
        "probe_id": profile["probe_id"],
        "transport_kind": profile["transport_kind"],
        "semantic_family": profile["semantic_family"],
        "authority_owner": profile["authority_owner"],
        "required_for_fold_in": bool(profile["required_for_fold_in"]),
        "status": status,
        "promotion_state": "promoted" if status == "usable" else "not_evaluated",
        "promotion_allowed": status == "usable",
        "evidence_tier": "quest_runtime" if status == "usable" else "none",
        "allowed_promotion_tiers": profile["allowed_tiers"],
        "promotion_gate": profile["promotion_gate"],
        "missing_gates": [
            row["gate_id"] for row in requirements if row.get("status") != "satisfied"
        ],
        "gate_results": requirements,
        "source": {
            "artifact_path": str(report_path) if report_path else "",
            "schema": report.get("schema"),
            "status": report.get("status"),
            "probe_id": profile["probe_id"],
            "run_id": report.get("link_id"),
            "promotion_reason": "device-link command route evidence",
        },
        "descriptor": {},
        "measurements": {
            "runtime_dispatch_delivered_count": command.get("runtime_dispatch_delivered_count"),
            "applied": command.get("applied"),
        },
        "next_cli": profile["next_cli"],
    }


def build_command_probe_row(profile: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    reports = object_value(artifacts.get("probe_reports")).get("QCL-000", [])
    selected = select_best_probe_report(reports)
    report = object_value(selected.get("payload"))
    report_path = selected.get("path")
    stages = object_value(report.get("command_stages"))
    required_stages = ["sent", "transport_ok", "authority_accepted", "runtime_accepted", "applied"]
    stages_ok = bool(stages) and all(stages.get(stage) == "pass" for stage in required_stages)
    tier = evidence_tier(report)
    raw_promotion_allowed = object_value(report.get("promotion")).get("allowed") is True
    promotion_allowed = raw_promotion_allowed and tier in set(string_list(profile.get("allowed_tiers")))
    requirements = [
        gate_result(
            "gate.qcl000.command_probe_report",
            "satisfied" if report else "missing",
            "QCL-000 command probe report loaded" if report else "QCL-000 command probe report not loaded",
        ),
        gate_result(
            "gate.qcl000.command_stages",
            "satisfied" if stages_ok else "missing",
            "sent, transport_ok, authority_accepted, runtime_accepted, applied"
            if stages_ok
            else "required command stages are missing or incomplete",
        ),
        gate_result(
            "gate.qcl000.quest_runtime",
            "satisfied" if tier == "quest_runtime" else "missing",
            f"evidence_tier={tier}; live Quest/device-link evidence required",
        ),
        gate_result(
            "gate.qcl000.promotion_allowed",
            "satisfied" if promotion_allowed else "missing",
            f"promotion.allowed={promotion_allowed}",
        ),
    ]
    missing_gates = [row["gate_id"] for row in requirements if row["status"] != "satisfied"]
    status = "usable" if not missing_gates else "candidate" if report else "missing"
    return {
        "capability_id": profile["capability_id"],
        "probe_id": profile["probe_id"],
        "transport_kind": profile["transport_kind"],
        "semantic_family": profile["semantic_family"],
        "authority_owner": profile["authority_owner"],
        "required_for_fold_in": bool(profile["required_for_fold_in"]),
        "status": status,
        "promotion_state": "promoted" if status == "usable" else "candidate",
        "promotion_allowed": promotion_allowed,
        "source_promotion_allowed": raw_promotion_allowed,
        "evidence_tier": tier,
        "allowed_promotion_tiers": profile["allowed_tiers"],
        "promotion_gate": profile["promotion_gate"],
        "missing_gates": missing_gates,
        "gate_results": requirements,
        "source": source_summary(report, report_path=report_path),
        "descriptor": {},
        "measurements": {"command_stages": stages},
        "next_cli": profile["next_cli"],
    }


def promotion_requirements(
    profile: dict[str, Any],
    *,
    report: dict[str, Any],
    descriptor: dict[str, Any],
    evidence_tier: str,
    promotion_allowed: bool,
) -> list[dict[str, Any]]:
    probe_id = str(profile["probe_id"])
    probe_token = gate_probe_token(probe_id)
    requirements = [
        gate_result(
            f"gate.{probe_token}.report_present",
            "satisfied" if report else "missing",
            f"{probe_id} report loaded" if report else f"{probe_id} report not loaded",
        ),
        gate_result(
            f"gate.{probe_token}.report_passed",
            "satisfied" if report.get("status") in {"pass", "warn"} else "missing",
            f"report status={report.get('status') or 'missing'}",
        ),
    ]
    if bool(profile.get("required_for_fold_in")):
        allowed_tiers = set(string_list(profile.get("allowed_tiers")))
        tier_gate = (
            "quest_runtime_or_broker_owned"
            if "broker_owned" in allowed_tiers
            else "quest_runtime"
        )
        requirements.append(
            gate_result(
                f"gate.{probe_token}.{tier_gate}",
                "satisfied" if evidence_tier in allowed_tiers else "missing",
                f"evidence_tier={evidence_tier}; allowed={','.join(sorted(allowed_tiers))}",
            )
        )
        requirements.append(
            gate_result(
                f"gate.{probe_token}.promotion_allowed",
                "satisfied" if promotion_allowed else "missing",
                f"promotion.allowed={promotion_allowed}",
            )
        )
    if probe_id == "QCL-080":
        requirements.extend(qcl080_product_requirements(report, descriptor))
    if probe_id == "QCL-082":
        requirements.extend(qcl082_media_requirements(report))
    return requirements


def qcl080_product_requirements(
    report: dict[str, Any],
    descriptor: dict[str, Any],
) -> list[dict[str, Any]]:
    host = object_value(report.get("host"))
    firewall = object_value(host.get("firewall_listener"))
    product_rule = firewall.get("product_rule_verified") is True
    if not product_rule:
        for requirement in list_value(descriptor.get("requirements")):
            row = object_value(requirement)
            if str(row.get("requirement_id") or "").endswith("product_host_firewall_rule"):
                product_rule = row.get("status") == "satisfied"
    return [
        gate_result(
            "gate.qcl080.product_host_firewall_rule",
            "satisfied" if product_rule else "missing",
            (
                "product Hostess/WPF firewall rule verified"
                if product_rule
                else "product Hostess/WPF firewall rule is not verified"
            ),
        )
    ]


def qcl082_media_requirements(report: dict[str, Any]) -> list[dict[str, Any]]:
    transport = object_value(report.get("transport"))
    measurements = object_value(report.get("measurements"))
    media_plane_defined = (
        transport.get("family") == "tcp_binary"
        and transport.get("payload_class") == "h264_annex_b_binary_frames"
        and qcl082_check_passed(report, "protocol.media_binary_transport")
    )
    packet_policy = qcl082_check_passed(report, "protocol.media_packet_boundaries")
    timestamp_policy = qcl082_check_passed(report, "protocol.media_timestamp_policy")
    backpressure_policy = qcl082_check_passed(report, "protocol.media_backpressure_policy")
    json_guard = qcl082_check_passed(report, "protocol.media_high_rate_json_guard")
    broker_runtime_status = qcl082_check_passed(report, "protocol.media_stream_runtime_status")
    measurement_keys = [
        "media_frames_received",
        "media_bytes_received",
        "media_dropped_frames",
        "media_receiver_queue_depth_max",
    ]
    measurements_present = all(measurements.get(key) is not None for key in measurement_keys)
    return [
        gate_result(
            "gate.qcl082.media_binary_probe_defined",
            "satisfied" if media_plane_defined else "missing",
            (
                "QCL-082 TCP binary media report loaded"
                if media_plane_defined
                else "QCL-082 TCP binary media report is missing or not binary"
            ),
        ),
        gate_result(
            "gate.qcl082.media_packet_boundaries",
            "satisfied" if packet_policy else "missing",
            (
                "packet magic, sequence, timestamp, flags, and payload length declared"
                if packet_policy
                else "packet boundary policy missing"
            ),
        ),
        gate_result(
            "gate.qcl082.media_timestamp_policy",
            "satisfied" if timestamp_policy else "missing",
            (
                "capture and receiver-arrival timestamps declared"
                if timestamp_policy
                else "media timestamp policy missing"
            ),
        ),
        gate_result(
            "gate.qcl082.media_backpressure_policy",
            "satisfied" if backpressure_policy else "missing",
            (
                "bounded queue, drop, and close policy declared"
                if backpressure_policy
                else "media queue/drop/backpressure policy missing"
            ),
        ),
        gate_result(
            "gate.qcl082.media_high_rate_json_guard",
            "satisfied" if json_guard else "missing",
            (
                "high-rate media payloads rejected from JSON streams"
                if json_guard
                else "high-rate JSON payload rejection missing"
            ),
        ),
        gate_result(
            "gate.qcl082.broker_runtime_status",
            "satisfied" if broker_runtime_status else "missing",
            (
                "broker media-stream runtime status loaded"
                if broker_runtime_status
                else "broker media-stream runtime status missing"
            ),
        ),
        gate_result(
            "gate.qcl082.media_measurements_declared",
            "satisfied" if measurements_present else "missing",
            (
                "frame, byte, drop, and queue measurements declared"
                if measurements_present
                else "frame, byte, drop, or queue measurements missing"
            ),
        ),
    ]


def qcl082_check_passed(report: dict[str, Any], name: str) -> bool:
    for check in list_value(report.get("checks")):
        row = object_value(check)
        if row.get("name") == name:
            return row.get("status") == "pass"
    return False


def protocol_row_status(
    report: dict[str, Any],
    *,
    descriptor: dict[str, Any],
    evidence_tier: str,
    requirements: list[dict[str, Any]],
    promotion_allowed: bool,
) -> str:
    if not report:
        return "missing"
    report_status = str(report.get("status") or "")
    if report_status in {"blocked", "fail"}:
        return "blocked" if report_status == "blocked" else "rejected"
    if any(row.get("status") != "satisfied" for row in requirements):
        return "candidate"
    descriptor_status = str(descriptor.get("status") or "")
    if descriptor_status in {"usable", "usable_with_warnings"}:
        return descriptor_status
    if promotion_allowed and evidence_tier in PROMOTABLE_TIERS:
        return "usable_with_warnings" if report_status == "warn" else "usable"
    return "candidate"


def protocol_promotion_state(row_status: str, promotion_allowed: bool) -> str:
    if row_status == "usable":
        return "promoted"
    if row_status == "usable_with_warnings":
        return "promoted_with_warnings"
    if row_status in {"blocked", "rejected"}:
        return row_status
    if promotion_allowed:
        return "promotion_incomplete"
    return "candidate"


def evidence_tier(report: dict[str, Any]) -> str:
    if not report:
        return "none"
    probe_id = str(report.get("probe_id") or "")
    transport = object_value(report.get("transport"))
    endpoint_source = str(transport.get("endpoint_source") or "")
    promotion_allowed = object_value(report.get("promotion")).get("allowed") is True
    if probe_id == "QCL-000" and report.get("status") == "pass":
        return "quest_runtime"
    if probe_id == "QCL-080" and endpoint_source == "app_owned_runtime_udp_sender":
        return "quest_runtime"
    if endpoint_source == "quest-runtime":
        return "quest_runtime"
    if endpoint_source in {
        "native-rust-broker",
        "manifold-lsl-broker",
        "rusty-quest-manifold-broker-media-stream-runtime",
    }:
        return "broker_owned"
    if is_fixture_report(report):
        return "fixture"
    if probe_id in {"QCL-050", "QCL-051"} and promotion_allowed:
        return "quest_runtime"
    if endpoint_source in {"host-loopback", "manifold-zmq-loopback", "rusty-xr-zmq-loopback"}:
        return "host_loopback"
    if endpoint_source == "goofi-sidecar":
        return "sidecar_loopback"
    if not endpoint_source:
        return "none"
    return "dependency_check"


def is_fixture_report(report: dict[str, Any]) -> bool:
    host = object_value(report.get("host"))
    if str(host.get("adb_provider") or "") == "fixture":
        return True
    if ".fixture" in str(host.get("toolchain_profile") or ""):
        return True
    if str(report.get("run_id") or "").startswith("fixture"):
        return True
    return False


def source_summary(report: dict[str, Any], *, report_path: Any) -> dict[str, Any]:
    promotion = object_value(report.get("promotion"))
    transport = object_value(report.get("transport"))
    return {
        "artifact_path": str(report_path) if report_path else "",
        "schema": report.get("schema"),
        "probe_id": report.get("probe_id"),
        "run_id": report.get("run_id"),
        "status": report.get("status"),
        "classification": report.get("classification"),
        "endpoint_source": transport.get("endpoint_source"),
        "promotion_target": promotion.get("target"),
        "promotion_reason": promotion.get("reason"),
    }


def descriptor_summary(descriptor: dict[str, Any], *, descriptor_path: Any) -> dict[str, Any]:
    if not descriptor:
        return {}
    return {
        "artifact_path": str(descriptor_path) if descriptor_path else "",
        "schema": descriptor.get("$schema") or descriptor.get("schema"),
        "status": descriptor.get("status"),
        "capability_id": descriptor.get("capability_id"),
        "stream_id": descriptor.get("stream_id"),
        "transport_kind": descriptor.get("transport_kind"),
    }


def select_best_probe_report(entries: list[Any]) -> dict[str, Any]:
    rows = [object_value(row) for row in entries if isinstance(row, dict)]
    if not rows:
        return {}
    return max(rows, key=probe_report_score)


def probe_report_score(entry: dict[str, Any]) -> tuple[int, int, str]:
    return (
        probe_report_quality_score(entry),
        len(str(object_value(entry.get("payload")).get("observed_at_utc") or "")),
        str(entry.get("path") or ""),
    )


def probe_report_quality_score(entry: dict[str, Any]) -> int:
    report = object_value(entry.get("payload"))
    promotion_score = 100 if object_value(report.get("promotion")).get("allowed") is True else 0
    status_score = {
        "pass": 60,
        "warn": 50,
        "blocked": 20,
        "planned": 10,
        "skipped": 10,
        "fail": 0,
    }.get(str(report.get("status") or ""), 0)
    tier_score = {
        "quest_runtime": 50,
        "broker_owned": 50,
        "host_loopback": 30,
        "sidecar_loopback": 20,
        "dependency_check": 10,
        "fixture": 5,
        "none": 0,
    }.get(evidence_tier(report), 0)
    return promotion_score + status_score + tier_score


def select_best_device_link_report(entries: list[Any]) -> dict[str, Any]:
    rows = [object_value(row) for row in entries if isinstance(row, dict)]
    if not rows:
        return {}
    return max(rows, key=device_link_score)


def device_link_score(entry: dict[str, Any]) -> int:
    report = object_value(entry.get("payload"))
    command = selected_command_result(report)
    subscriber = selected_runtime_subscriber(report)
    return (
        (100 if report.get("status") == "pass" else 0)
        + (100 if command.get("applied") is True else 0)
        + (50 if subscriber.get("status") == "connected" else 0)
    )


def selected_command_result(report: dict[str, Any]) -> dict[str, Any]:
    rows = [object_value(row) for row in list_value(report.get("command_results"))]
    for row in rows:
        if row.get("transport_kind") == "manifold_websocket" and row.get("applied") is True:
            return row
    return rows[0] if rows else {}


def selected_runtime_subscriber(report: dict[str, Any]) -> dict[str, Any]:
    rows = [object_value(row) for row in list_value(report.get("runtime_subscribers"))]
    for row in rows:
        if row.get("status") == "connected":
            return row
    return rows[0] if rows else {}


def matrix_status(rows: list[dict[str, Any]]) -> str:
    required_rows = [row for row in rows if row.get("required_for_fold_in") is True]
    if any(row.get("status") in {"blocked", "rejected"} for row in required_rows):
        return "fail"
    if any(row.get("status") not in {"usable", "usable_with_warnings"} for row in required_rows):
        return "warn"
    if any(row.get("status") == "usable_with_warnings" for row in required_rows):
        return "warn"
    return "pass"


def matrix_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    required_rows = [row for row in rows if row.get("required_for_fold_in") is True]
    promoted_rows = [
        row for row in rows if row.get("status") in {"usable", "usable_with_warnings"}
    ]
    pending_required = [
        str(row.get("probe_id") or row.get("capability_id") or "")
        for row in required_rows
        if row.get("status") not in {"usable", "usable_with_warnings"}
    ]
    missing_gates = sum(len(list_value(row.get("missing_gates"))) for row in rows)
    return {
        "row_count": len(rows),
        "required_row_count": len(required_rows),
        "promoted_count": len(promoted_rows),
        "required_promoted_count": len(required_rows) - len(pending_required),
        "candidate_count": sum(1 for row in rows if row.get("status") == "candidate"),
        "blocked_count": sum(1 for row in rows if row.get("status") in {"blocked", "rejected"}),
        "missing_count": sum(1 for row in rows if row.get("status") == "missing"),
        "missing_gate_count": missing_gates,
        "pending_required_probe_ids": pending_required,
        "all_required_data_protocols_promoted": not pending_required,
    }


def matrix_issues(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in rows:
        if row.get("required_for_fold_in") is not True:
            continue
        if row.get("status") in {"usable", "usable_with_warnings"}:
            continue
        issues.append(
            {
                "issue_code": "hostess.issue.protocol_evidence_matrix.required_protocol_not_promoted",
                "severity": "warning",
                "message": (
                    f"{row.get('probe_id')} {row.get('transport_kind')} remains "
                    f"{row.get('status')}; missing {', '.join(string_list(row.get('missing_gates')))}"
                ),
            }
        )
    return issues


def validate_protocol_evidence_matrix(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if report.get("$schema") != PROTOCOL_EVIDENCE_MATRIX_SCHEMA:
        errors.append("unsupported protocol evidence matrix schema")
    if report.get("status") not in VALID_MATRIX_STATUSES:
        errors.append("status must be pass, warn, or fail")
    rows = [object_value(row) for row in list_value(report.get("rows"))]
    if not rows:
        errors.append("rows must not be empty")
    seen_probe_ids = {str(row.get("probe_id") or "") for row in rows}
    for required in ["QCL-000", "QCL-080", "QCL-081", "QCL-083", "QCL-084"]:
        if required not in seen_probe_ids:
            errors.append(f"missing required protocol row {required}")
    for row in rows:
        row_id = str(row.get("capability_id") or "<unknown>")
        if not str(row.get("capability_id") or "").strip():
            errors.append("row capability_id must not be empty")
        if row.get("status") not in VALID_ROW_STATUSES:
            errors.append(f"row {row_id} has invalid status")
        if not str(row.get("evidence_tier") or "").strip():
            errors.append(f"row {row_id} requires evidence_tier")
        gates = [object_value(gate) for gate in list_value(row.get("gate_results"))]
        if not gates:
            errors.append(f"row {row_id} requires gate_results")
        if row.get("required_for_fold_in") is True and row.get("status") not in {
            "usable",
            "usable_with_warnings",
        }:
            warnings.append(f"{row.get('probe_id')} remains {row.get('status')}")
        if row.get("promotion_allowed") is True:
            allowed_tiers = set(string_list(row.get("allowed_promotion_tiers")))
            if row.get("evidence_tier") not in allowed_tiers:
                errors.append(
                    f"row {row_id} has promotion_allowed without an allowed evidence tier"
                )
    return {
        "$schema": PROTOCOL_EVIDENCE_MATRIX_VALIDATION_SCHEMA,
        "status": "pass" if not errors else "fail",
        "matrix_id": report.get("matrix_id"),
        "report_status": report.get("status"),
        "row_count": len(rows),
        "errors": errors,
        "warnings": warnings,
    }


def gate_result(gate_id: str, status: str, evidence: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "status": status,
        "evidence": evidence,
    }


def gate_probe_token(probe_id: str) -> str:
    return probe_id.lower().replace("-", "")


def classify_payload(payload: dict[str, Any]) -> str:
    schema = str(payload.get("$schema") or payload.get("schema") or "")
    if schema == "rusty.quest.connectivity_topology_probe.v1":
        return "connectivity_probe_report"
    if schema == device_link_report.QUEST_DEVICE_LINK_STREAM_CAPABILITY_SCHEMA:
        return "stream_capability_descriptor"
    if schema == device_link_report.QUEST_DEVICE_LINK_SCHEMA:
        return "device_link_report"
    if schema == CONNECTIVITY_SUITE_RUN_SCHEMA:
        return "suite_run"
    if schema == device_link_report.QUEST_DEVICE_LINK_INSTALL_TEST_SUITE_SCHEMA:
        return "suite_descriptor"
    return "unknown"


def input_ref(path: Path, payload: dict[str, Any], *, role: str) -> dict[str, Any]:
    schema = str(payload.get("$schema") or payload.get("schema") or "")
    return {
        "role": role,
        "path": str(path),
        "schema": schema,
        "probe_id": payload.get("probe_id"),
        "status": payload.get("status"),
        "sha256": sha256_file(path) if path.exists() else "",
    }


def resolve_artifact_path(raw_path: str, *, suite_path: Path) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.exists() or path.is_absolute():
        return path
    candidate = suite_path.parent / path
    if candidate.exists():
        return candidate
    return path


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def argument_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def utc_now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "PROTOCOL_EVIDENCE_MATRIX_SCHEMA",
    "PROTOCOL_EVIDENCE_MATRIX_VALIDATION_SCHEMA",
    "build_protocol_evidence_matrix",
    "run_protocol_evidence_matrix",
    "validate_protocol_evidence_matrix",
]
