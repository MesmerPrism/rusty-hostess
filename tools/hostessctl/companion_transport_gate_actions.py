"""Operator next-action catalog for companion transport gates."""

from __future__ import annotations

from typing import Any


POWERSHELL_SHELL = "powershell"
HOSTESS_REPO_CWD = "<rusty-hostess-root>"
AGENT_BOARD_SCRIPT = r"S:\Work\agent-bureau\scripts\agent-board.ps1"
QUEST_LEASE_RESOURCE = "quest:<quest-serial>"
QUEST_LEASE_ID = "<quest-lease-id>"
QUEST_LEASE_DURATION = "45m"
WPF_COMPANION_EXE = (
    r"apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe"
)
QCL082_FIREWALL_VERIFY = (
    r"target\connectivity-probe\qcl082-tcp-firewall-admin-handoff-verify.json"
)
DIRECT_WIFI_LIFECYCLE_INPUT = r"<wifi-direct-lifecycle-report>"
DIRECT_WIFI_QCL040_LIFECYCLE_OUTPUT = (
    r"target\connectivity-probe\qcl040-live-wifi-direct-lifecycle.json"
)
DIRECT_WIFI_QCL041_LIFECYCLE_OUTPUT = (
    r"target\connectivity-probe\qcl041-live-wifi-direct-lifecycle.json"
)


def operator_next_actions_summary(
    remaining_live_gates: list[dict[str, Any]]
) -> dict[str, Any]:
    gate_actions = []
    for gate in remaining_live_gates:
        gate_id = str(gate.get("gate_id") or "")
        next_actions = list_objects(gate.get("next_actions"))
        if gate_id and next_actions:
            gate_actions.append(
                {
                    "gate_id": gate_id,
                    "next_action_ids": [
                        str(action.get("action_id") or "")
                        for action in next_actions
                        if str(action.get("action_id") or "")
                    ],
                }
            )
    return {
        "policy": (
            "These are CLI-equivalent operator actions for WPF-visible pending "
            "transport gates. They point to Hostess-owned routes and do not "
            "mutate host or headset state unless the action explicitly marks "
            "that requirement."
        ),
        "shell": POWERSHELL_SHELL,
        "cwd": HOSTESS_REPO_CWD,
        "gate_count": len(gate_actions),
        "gates": gate_actions,
    }


def operator_next_actions_for_gate(gate_id: str) -> list[dict[str, Any]]:
    if gate_id == "transport.product_tcp_media_listener_firewall":
        return product_tcp_media_listener_firewall_actions()
    if gate_id == "transport.direct_wifi_live_topology":
        return direct_wifi_live_topology_actions()
    if gate_id == "transport.product_tcp_media_over_direct_wifi":
        return product_tcp_media_over_direct_wifi_actions()
    if gate_id == "transport.general_websocket_capability":
        return general_websocket_capability_actions()
    return []


def validate_next_actions_for_gate(
    gate_id: str,
    next_actions: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if not next_actions:
        return [f"pending transport gate missing next_actions: {gate_id}"]
    for next_action in next_actions:
        action_id = str(next_action.get("action_id") or "")
        if not action_id:
            errors.append(f"pending transport gate next action missing action_id: {gate_id}")
        command = object_value(next_action.get("command"))
        available_now = next_action.get("available_now") is not False
        if available_now and not command:
            errors.append(f"available next action missing command: {gate_id}/{action_id}")
        if command:
            if command.get("shell") != POWERSHELL_SHELL:
                errors.append(f"next action command must be powershell: {gate_id}/{action_id}")
            if not str(command.get("command") or "").strip():
                errors.append(f"next action command missing command text: {gate_id}/{action_id}")
        if next_action.get("requires_quest_lease"):
            lease = object_value(next_action.get("lease"))
            if lease.get("manager") != "Agent Board":
                errors.append(f"quest-bound next action missing Agent Board lease metadata: {gate_id}/{action_id}")
            if str(lease.get("resource") or "") != QUEST_LEASE_RESOURCE:
                errors.append(f"quest-bound next action missing quest:<quest-serial> resource: {gate_id}/{action_id}")
            if "adb-server:lifecycle" not in str(lease.get("adb_server_lifecycle_policy") or ""):
                errors.append(f"quest-bound next action missing adb-server lifecycle policy: {gate_id}/{action_id}")
            if not str(lease.get("release_command") or "").strip():
                errors.append(f"quest-bound next action missing lease release command: {gate_id}/{action_id}")
    return errors


def product_tcp_media_listener_firewall_actions() -> list[dict[str, Any]]:
    return [
        next_action(
            "generate_qcl082_firewall_admin_handoff",
            "Generate the product-owned QCL-082 firewall apply handoff.",
            authority_owner="tools.hostessctl.connectivity_firewall",
            requires_elevation=False,
            requires_quest_lease=False,
            mutates_host=False,
            mutates_device=False,
            command=powershell_command(
                "Generate admin handoff",
                (
                    "python tools\\hostessctl\\hostessctl.py "
                    "connectivity-probe windows-firewall-rule "
                    "--action apply "
                    "--rule-profile qcl-082-rmanvid1-media "
                    f"--program {WPF_COMPANION_EXE} "
                    "--out target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-apply.json "
                    "--handoff-script-out target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-apply.ps1 "
                    f"--handoff-verify-out {QCL082_FIREWALL_VERIFY}"
                ),
            ),
            acceptance_artifacts=[
                r"target\connectivity-probe\qcl082-tcp-firewall-admin-handoff-apply.json",
                r"target\connectivity-probe\qcl082-tcp-firewall-admin-handoff-apply.ps1",
            ],
            clears_gate=False,
        ),
        next_action(
            "run_qcl082_firewall_admin_handoff",
            "Run the generated Hostess firewall handoff from elevated PowerShell.",
            authority_owner="tools.hostessctl.connectivity_firewall",
            requires_elevation=True,
            requires_quest_lease=False,
            mutates_host=True,
            mutates_device=False,
            command=powershell_command(
                "Run elevated handoff",
                (
                    "powershell -NoProfile -ExecutionPolicy Bypass "
                    "-File target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-apply.ps1"
                ),
            ),
            acceptance_artifacts=[QCL082_FIREWALL_VERIFY],
            clears_gate=False,
        ),
        next_action(
            "verify_qcl082_product_firewall_rule",
            "Verify the scoped Hostess/WPF TCP listener rule report.",
            authority_owner="tools.hostessctl.connectivity_firewall",
            requires_elevation=False,
            requires_quest_lease=False,
            mutates_host=False,
            mutates_device=False,
            command=powershell_command(
                "Verify product listener rule",
                (
                    "python tools\\hostessctl\\hostessctl.py "
                    "connectivity-probe windows-firewall-rule "
                    "--action verify "
                    "--rule-profile qcl-082-rmanvid1-media "
                    f"--program {WPF_COMPANION_EXE} "
                    f"--out {QCL082_FIREWALL_VERIFY} "
                    "--fail-on-error"
                ),
            ),
            acceptance_artifacts=[QCL082_FIREWALL_VERIFY],
            clears_gate=True,
        ),
    ]


def direct_wifi_live_topology_actions() -> list[dict[str, Any]]:
    return [
        next_action(
            "reserve_quest_lease_for_direct_wifi",
            "Reserve the target Quest before headset-bound Wi-Fi Direct evidence.",
            authority_owner="Agent Board",
            requires_elevation=False,
            requires_quest_lease=False,
            mutates_host=False,
            mutates_device=False,
            command=powershell_command(
                "Reserve Quest lease",
                agent_board_reserve_command("QCL-040/QCL-041 direct Wi-Fi validation"),
            ),
            acceptance_artifacts=["Agent Board quest:<quest-serial> lease id"],
            clears_gate=False,
            lease=quest_lease_metadata("QCL-040/QCL-041 direct Wi-Fi validation"),
            note=(
                "Use the local Agent Board lease flow before running the ADB-backed "
                "commands below. Ordinary ADB commands stay serial-scoped; reserve "
                "adb-server:lifecycle only for disruptive daemon lifecycle work."
            ),
        ),
        next_action(
            "run_qcl040_live_wifi_direct_preflight",
            "Refresh the Android-phone Wi-Fi Direct live preflight evidence.",
            authority_owner="tools.hostessctl.connectivity_topology_live",
            requires_elevation=False,
            requires_quest_lease=True,
            mutates_host=False,
            mutates_device=False,
            command=powershell_command(
                "Run QCL-040 live preflight",
                (
                    "python tools\\hostessctl\\hostessctl.py "
                    "connectivity-probe run "
                    "--mode live "
                    "--probe-id QCL-040 "
                    "--adb S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe "
                    "--serial '<quest-serial>' "
                    "--out target\\connectivity-probe\\qcl040-live-wifi-direct-preflight.json"
                ),
            ),
            acceptance_artifacts=[
                r"target\connectivity-probe\qcl040-live-wifi-direct-preflight.json",
            ],
            clears_gate=False,
            lease=quest_lease_metadata("QCL-040 live Wi-Fi Direct preflight"),
            note=(
                "The current preflight is read-only and does not clear the promotion "
                "gate by itself."
            ),
        ),
        next_action(
            "run_qcl041_live_wifi_direct_preflight",
            "Refresh the Windows-peer Wi-Fi Direct live preflight evidence.",
            authority_owner="tools.hostessctl.connectivity_topology_live",
            requires_elevation=False,
            requires_quest_lease=True,
            mutates_host=False,
            mutates_device=False,
            command=powershell_command(
                "Run QCL-041 live preflight",
                (
                    "python tools\\hostessctl\\hostessctl.py "
                    "connectivity-probe run "
                    "--mode live "
                    "--probe-id QCL-041 "
                    "--adb S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe "
                    "--serial '<quest-serial>' "
                    "--out target\\connectivity-probe\\qcl041-live-wifi-direct-preflight.json"
                ),
            ),
            acceptance_artifacts=[
                r"target\connectivity-probe\qcl041-live-wifi-direct-preflight.json",
            ],
            clears_gate=False,
            lease=quest_lease_metadata("QCL-041 live Wi-Fi Direct preflight"),
            note=(
                "The clearing evidence still needs peer discovery, group formation, "
                "bounded socket exchange, and cleanup evidence."
            ),
        ),
        wifi_direct_lifecycle_template_action(
            action_id="template_qcl040_wifi_direct_lifecycle_source",
            probe_id="QCL-040",
            output=r"target\connectivity-probe\qcl040-wifi-direct-lifecycle-template.json",
            label="Write the QCL-040 Wi-Fi Direct lifecycle source-artifact template.",
        ),
        wifi_direct_lifecycle_template_action(
            action_id="template_qcl041_wifi_direct_lifecycle_source",
            probe_id="QCL-041",
            output=r"target\connectivity-probe\qcl041-wifi-direct-lifecycle-template.json",
            label="Write the QCL-041 Wi-Fi Direct lifecycle source-artifact template.",
        ),
        wifi_direct_lifecycle_action(
            action_id="normalize_qcl040_wifi_direct_lifecycle_report",
            probe_id="QCL-040",
            output=DIRECT_WIFI_QCL040_LIFECYCLE_OUTPUT,
            label=(
                "Normalize leased Android-phone Wi-Fi Direct lifecycle evidence "
                "into a promoted topology report."
            ),
        ),
        wifi_direct_lifecycle_action(
            action_id="normalize_qcl041_wifi_direct_lifecycle_report",
            probe_id="QCL-041",
            output=DIRECT_WIFI_QCL041_LIFECYCLE_OUTPUT,
            label=(
                "Normalize leased Windows-peer Wi-Fi Direct lifecycle evidence "
                "into a promoted topology report."
            ),
        ),
    ]


def wifi_direct_lifecycle_template_action(
    *,
    action_id: str,
    probe_id: str,
    output: str,
    label: str,
) -> dict[str, Any]:
    return next_action(
        action_id,
        label,
        authority_owner="tools.hostessctl.connectivity_topology_lifecycle",
        requires_elevation=False,
        requires_quest_lease=False,
        mutates_host=False,
        mutates_device=False,
        command=powershell_command(
            f"Write {probe_id} lifecycle source template",
            (
                "python tools\\hostessctl\\hostessctl.py "
                "connectivity-probe wifi-direct-lifecycle-template "
                f"--probe-id {probe_id} "
                f"--out {output}"
            ),
        ),
        acceptance_artifacts=[output],
        clears_gate=False,
        note=(
            "This only writes the expected source-artifact shape for a future "
            "leased lifecycle harness. The template is non-promoting and must "
            "be replaced by live evidence before normalization can clear the gate."
        ),
    )


def wifi_direct_lifecycle_action(
    *,
    action_id: str,
    probe_id: str,
    output: str,
    label: str,
) -> dict[str, Any]:
    return next_action(
        action_id,
        label,
        authority_owner="tools.hostessctl.connectivity_topology_lifecycle",
        requires_elevation=False,
        requires_quest_lease=False,
        mutates_host=False,
        mutates_device=False,
        command=powershell_command(
            f"Build {probe_id} lifecycle topology report",
            (
                "python tools\\hostessctl\\hostessctl.py "
                "connectivity-probe run "
                "--mode fixture "
                f"--probe-id {probe_id} "
                f"--wifi-direct-lifecycle-report '{DIRECT_WIFI_LIFECYCLE_INPUT}' "
                f"--out {output} "
                "--fail-on-error"
            ),
        ),
        acceptance_artifacts=[output],
        clears_gate=True,
        note=(
            "The input lifecycle report must come from a leased Quest run and "
            "prove peer discovery, group formation, bounded TCP socket exchange, "
            "and cleanup. This route only normalizes evidence."
        ),
    )


def product_tcp_media_over_direct_wifi_actions() -> list[dict[str, Any]]:
    return [
        next_action(
            "capture_rmanvid1_over_promoted_direct_wifi",
            "Capture bounded RMANVID1 TCP media with topology and firewall evidence attached.",
            authority_owner="tools.hostessctl.connectivity_media_receiver",
            requires_elevation=False,
            requires_quest_lease=True,
            mutates_host=False,
            mutates_device=True,
            depends_on=[
                "transport.direct_wifi_live_topology",
                "transport.product_tcp_media_listener_firewall",
            ],
            command=powershell_command(
                "Capture RMANVID1 receiver counters",
                (
                    "python tools\\hostessctl\\hostessctl.py "
                    "connectivity-probe rmanvid1-receiver-capture "
                    "--bind-host 0.0.0.0 "
                    "--port 9079 "
                    "--capture-out target\\connectivity-probe\\media-stream.rmanvid1 "
                    "--sidecar-out target\\connectivity-probe\\media-stream-receiver-sidecar.json "
                    "--runtime-status target\\connectivity-probe\\media-stream-runtime-status.json "
                    "--topology-report '<promoted-qcl040-or-qcl041-topology-report>' "
                    f"--firewall-report {QCL082_FIREWALL_VERIFY} "
                    "--capture-kind live_broker_stream "
                    "--max-packets 240 "
                    "--out target\\connectivity-probe\\media-stream-receiver-result.json "
                    "--fail-on-error"
                ),
            ),
            acceptance_artifacts=[
                r"target\connectivity-probe\media-stream.rmanvid1",
                r"target\connectivity-probe\media-stream-receiver-sidecar.json",
                r"target\connectivity-probe\media-stream-receiver-result.json",
            ],
            clears_gate=False,
            lease=quest_lease_metadata("QCL-082 RMANVID1 product media capture"),
        ),
        next_action(
            "promote_qcl082_rmanvid1_capture",
            "Fold the RMANVID1 capture back into the QCL-082 report.",
            authority_owner="tools.hostessctl.connectivity_probe",
            requires_elevation=False,
            requires_quest_lease=False,
            mutates_host=False,
            mutates_device=False,
            command=powershell_command(
                "Build QCL-082 product media report",
                (
                    "python tools\\hostessctl\\hostessctl.py "
                    "connectivity-probe run "
                    "--mode fixture "
                    "--probe-id QCL-082 "
                    "--media-stream-rmanvid1-capture target\\connectivity-probe\\media-stream.rmanvid1 "
                    "--media-stream-receiver-sidecar target\\connectivity-probe\\media-stream-receiver-sidecar.json "
                    "--media-stream-runtime-status target\\connectivity-probe\\media-stream-runtime-status.json "
                    "--media-stream-topology-report '<promoted-qcl040-or-qcl041-topology-report>' "
                    f"--media-stream-firewall-report {QCL082_FIREWALL_VERIFY} "
                    "--out target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json "
                    "--fail-on-error"
                ),
            ),
            acceptance_artifacts=[
                r"target\connectivity-probe\qcl082-rmanvid1-receiver-capture.json",
            ],
            clears_gate=True,
        ),
    ]


def general_websocket_capability_actions() -> list[dict[str, Any]]:
    return [
        next_action(
            "run_qcl079_host_loopback_websocket",
            "Keep generic WebSocket protocol-fit evidence visible as candidate evidence.",
            authority_owner="tools.hostessctl.connectivity_websocket",
            requires_elevation=False,
            requires_quest_lease=False,
            mutates_host=False,
            mutates_device=False,
            command=powershell_command(
                "Run QCL-079 host loopback",
                (
                    "python tools\\hostessctl\\hostessctl.py "
                    "connectivity-probe run "
                    "--mode live "
                    "--probe-id QCL-079 "
                    "--websocket-source host-loopback "
                    "--out target\\connectivity-probe\\qcl079-live-host-loopback.json"
                ),
            ),
            acceptance_artifacts=[
                r"target\connectivity-probe\qcl079-live-host-loopback.json",
            ],
            clears_gate=False,
        ),
        next_action(
            "run_qcl079_broker_owned_websocket",
            "Promote generic WebSocket only with broker-owned stream endpoint evidence.",
            authority_owner="tools.hostessctl.connectivity_websocket",
            requires_elevation=False,
            requires_quest_lease=False,
            mutates_host=False,
            mutates_device=False,
            command=powershell_command(
                "Run QCL-079 broker-owned WebSocket",
                (
                    "python tools\\hostessctl\\hostessctl.py "
                    "connectivity-probe run "
                    "--mode live "
                    "--probe-id QCL-079 "
                    "--websocket-source broker-owned-websocket "
                    "--websocket-route-descriptor '<manifold-stream-websocket-route>' "
                    "--websocket-route-evidence '<manifold-stream-websocket-evidence>' "
                    "--out target\\connectivity-probe\\qcl079-live-broker-owned-websocket.json "
                    "--fail-on-error"
                ),
            ),
            acceptance_artifacts=[
                r"target\connectivity-probe\qcl079-live-broker-owned-websocket.json",
            ],
            clears_gate=True,
        ),
    ]


def next_action(
    action_id: str,
    label: str,
    *,
    authority_owner: str,
    requires_elevation: bool,
    requires_quest_lease: bool,
    mutates_host: bool,
    mutates_device: bool,
    command: dict[str, Any] | None,
    acceptance_artifacts: list[str],
    clears_gate: bool,
    available_now: bool = True,
    depends_on: list[str] | None = None,
    lease: dict[str, Any] | None = None,
    note: str = "",
) -> dict[str, Any]:
    action = {
        "action_id": action_id,
        "label": label,
        "authority_owner": authority_owner,
        "available_now": available_now,
        "requires_elevation": requires_elevation,
        "requires_quest_lease": requires_quest_lease,
        "requires_adb_server_lifecycle_lease": False,
        "mutates_host": mutates_host,
        "mutates_device": mutates_device,
        "clears_gate_when_accepted": clears_gate,
        "acceptance_artifacts": acceptance_artifacts,
    }
    if depends_on:
        action["depends_on"] = depends_on
    if lease:
        action["lease"] = lease
    if command:
        action["command"] = command
    if note:
        action["note"] = note
    return action


def powershell_command(label: str, command: str) -> dict[str, Any]:
    return {
        "label": label,
        "shell": POWERSHELL_SHELL,
        "cwd": HOSTESS_REPO_CWD,
        "command": command,
    }


def quest_lease_metadata(task: str) -> dict[str, Any]:
    return {
        "manager": "Agent Board",
        "resource": QUEST_LEASE_RESOURCE,
        "duration": QUEST_LEASE_DURATION,
        "task": task,
        "lease_id_placeholder": QUEST_LEASE_ID,
        "reserve_command": agent_board_reserve_command(task),
        "release_command": agent_board_release_command(),
        "adb_server_lifecycle_policy": (
            "Use adb-server:lifecycle only for disruptive daemon lifecycle "
            "or Wi-Fi ADB setup/recovery. Ordinary ADB commands stay serial-scoped."
        ),
    }


def agent_board_reserve_command(task: str) -> str:
    return (
        f"& '{AGENT_BOARD_SCRIPT}' reserve '{QUEST_LEASE_RESOURCE}' "
        f"--duration {QUEST_LEASE_DURATION} --task '{task}'"
    )


def agent_board_release_command() -> str:
    return f"& '{AGENT_BOARD_SCRIPT}' release '{QUEST_LEASE_ID}' --result done"


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_objects(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


__all__ = [
    "operator_next_actions_for_gate",
    "operator_next_actions_summary",
    "validate_next_actions_for_gate",
]
