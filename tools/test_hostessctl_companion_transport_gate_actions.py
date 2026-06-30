from __future__ import annotations

import unittest
from typing import Any

from tools.hostessctl.companion_transport_gate_actions import (
    operator_next_actions_for_gate,
    operator_next_actions_summary,
    validate_next_actions_for_gate,
)


class HostessCtlCompanionTransportGateActionTests(unittest.TestCase):
    def test_direct_wifi_actions_keep_serial_scoped_lease_policy(self) -> None:
        actions = actions_by_id("transport.direct_wifi_live_topology")

        self.assert_valid_actions("transport.direct_wifi_live_topology", actions)
        self.assertIn("reserve_quest_lease_for_direct_wifi", actions)
        reserve = actions["reserve_quest_lease_for_direct_wifi"]
        self.assertFalse(reserve["requires_quest_lease"])
        self.assertFalse(reserve["requires_adb_server_lifecycle_lease"])
        self.assertIn("agent-board.ps1", command_text(reserve))
        self.assertEqual(reserve["lease"]["resource"], "quest:<quest-serial>")
        self.assertIn("reserve 'quest:<quest-serial>'", reserve["lease"]["reserve_command"])
        self.assertIn("release '<quest-lease-id>'", reserve["lease"]["release_command"])

        for action in actions.values():
            self.assertFalse(
                action["requires_adb_server_lifecycle_lease"],
                f"{action['action_id']} must stay serial-scoped unless it owns ADB daemon recovery",
            )
            self.assert_allowed_command_shape(action)
            if action["requires_quest_lease"]:
                self.assert_quest_lease_metadata(action)
                self.assertIn("--serial '<quest-serial>'", command_text(action))

        normalizer = actions["normalize_qcl041_wifi_direct_lifecycle_report"]
        self.assertFalse(normalizer["requires_quest_lease"])
        self.assertTrue(normalizer["clears_gate_when_accepted"])
        self.assertIn("--wifi-direct-lifecycle-report '<wifi-direct-lifecycle-report>'", command_text(normalizer))
        self.assertIn("leased Quest run", normalizer["note"])

    def test_product_media_actions_preserve_dependency_and_lease_flags(self) -> None:
        actions = actions_by_id("transport.product_tcp_media_over_direct_wifi")

        self.assert_valid_actions("transport.product_tcp_media_over_direct_wifi", actions)
        plan = actions["write_qcl082_product_media_direct_wifi_plan"]
        self.assertFalse(plan["requires_quest_lease"])
        self.assertIn("--promoted-topology-report '<promoted-qcl040-or-qcl041-topology-report>'", command_text(plan))
        self.assertIn("--quest-lease-id '<quest-lease-id>'", command_text(plan))
        self.assertIn("--quest-lease-resource 'quest:<quest-serial>'", command_text(plan))

        live_session = actions["run_qcl082_product_media_live_session"]
        self.assertTrue(live_session["requires_quest_lease"])
        self.assertFalse(live_session["requires_elevation"])
        self.assertFalse(live_session["requires_adb_server_lifecycle_lease"])
        self.assertFalse(live_session["mutates_host"])
        self.assertTrue(live_session["mutates_device"])
        self.assertEqual(
            live_session["depends_on"],
            [
                "transport.direct_wifi_live_topology",
                "transport.product_tcp_media_listener_firewall",
            ],
        )
        self.assert_quest_lease_metadata(live_session)
        live_command = command_text(live_session)
        self.assertIn("qcl082-product-media-live-session", live_command)
        self.assertIn("--topology-report '<promoted-qcl040-or-qcl041-topology-report>'", live_command)
        self.assertIn("--firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json", live_command)
        self.assertIn("--quest-lease-id '<quest-lease-id>'", live_command)
        self.assertIn("--quest-lease-resource 'quest:<quest-serial>'", live_command)
        self.assertIn("--quest-lease-reserved-before-live-steps", live_command)
        self.assertIn("--out target\\connectivity-probe\\media-stream-receiver-result.json", live_command)
        self.assertIn("--fail-on-error", live_command)

        capture = actions["capture_rmanvid1_over_promoted_direct_wifi"]
        self.assertTrue(capture["requires_quest_lease"])
        self.assertFalse(capture["requires_adb_server_lifecycle_lease"])
        self.assert_quest_lease_metadata(capture)
        self.assertIn("--quest-lease-reserved-before-live-steps", command_text(capture))
        self.assertIn("--media-stream-receiver-result", command_text(actions["promote_qcl082_rmanvid1_capture"]))

    def test_product_firewall_actions_separate_handoff_from_verify(self) -> None:
        actions = actions_by_id("transport.product_tcp_media_listener_firewall")

        self.assert_valid_actions("transport.product_tcp_media_listener_firewall", actions)
        generate = actions["generate_qcl082_firewall_admin_handoff"]
        self.assertFalse(generate["requires_elevation"])
        self.assertFalse(generate["mutates_host"])
        self.assertIn("--handoff-script-out", command_text(generate))

        run = actions["run_qcl082_firewall_admin_handoff"]
        self.assertTrue(run["requires_elevation"])
        self.assertTrue(run["mutates_host"])
        self.assertIn("-File target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-apply.ps1", command_text(run))

        verify = actions["verify_qcl082_product_firewall_rule"]
        self.assertFalse(verify["requires_elevation"])
        self.assertFalse(verify["mutates_host"])
        self.assertTrue(verify["clears_gate_when_accepted"])
        verify_command = command_text(verify)
        self.assertIn("--action verify", verify_command)
        self.assertIn("--rule-profile qcl-082-rmanvid1-media", verify_command)
        self.assertIn("--out target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json", verify_command)
        self.assertIn("--fail-on-error", verify_command)

    def test_general_websocket_actions_preserve_candidate_and_promotion_boundary(self) -> None:
        actions = actions_by_id("transport.general_websocket_capability")

        self.assert_valid_actions("transport.general_websocket_capability", actions)
        self.assertEqual(
            set(actions),
            {
                "run_qcl079_host_loopback_websocket",
                "run_qcl079_broker_owned_websocket",
            },
        )
        host_loopback = actions["run_qcl079_host_loopback_websocket"]
        self.assertFalse(host_loopback["requires_elevation"])
        self.assertFalse(host_loopback["requires_quest_lease"])
        self.assertFalse(host_loopback["requires_adb_server_lifecycle_lease"])
        self.assertFalse(host_loopback["mutates_host"])
        self.assertFalse(host_loopback["mutates_device"])
        self.assertFalse(host_loopback["clears_gate_when_accepted"])
        self.assertIn("--probe-id QCL-079", command_text(host_loopback))
        self.assertIn("--websocket-source host-loopback", command_text(host_loopback))
        self.assertIn("--out target\\connectivity-probe\\qcl079-live-host-loopback.json", command_text(host_loopback))

        broker_owned = actions["run_qcl079_broker_owned_websocket"]
        self.assertFalse(broker_owned["requires_elevation"])
        self.assertFalse(broker_owned["requires_quest_lease"])
        self.assertFalse(broker_owned["requires_adb_server_lifecycle_lease"])
        self.assertFalse(broker_owned["mutates_host"])
        self.assertFalse(broker_owned["mutates_device"])
        self.assertTrue(broker_owned["clears_gate_when_accepted"])
        broker_command = command_text(broker_owned)
        self.assertIn("--websocket-source broker-owned-websocket", broker_command)
        self.assertIn("--websocket-route-descriptor '<manifold-stream-websocket-route>'", broker_command)
        self.assertIn("--websocket-route-evidence '<manifold-stream-websocket-evidence>'", broker_command)
        self.assertIn("--out target\\connectivity-probe\\qcl079-live-broker-owned-websocket.json", broker_command)
        self.assertIn("--fail-on-error", broker_command)

    def test_operator_next_actions_summary_lists_source_owned_action_ids(self) -> None:
        remaining = [
            {
                "gate_id": "transport.general_websocket_capability",
                "next_actions": operator_next_actions_for_gate("transport.general_websocket_capability"),
            },
            {
                "gate_id": "transport.direct_wifi_live_topology",
                "next_actions": operator_next_actions_for_gate("transport.direct_wifi_live_topology"),
            },
            {
                "gate_id": "transport.product_tcp_media_over_direct_wifi",
                "next_actions": operator_next_actions_for_gate("transport.product_tcp_media_over_direct_wifi"),
            },
        ]
        summary = operator_next_actions_summary(remaining)

        self.assertEqual(summary["shell"], "powershell")
        self.assertEqual(summary["cwd"], "<rusty-hostess-root>")
        self.assertEqual(summary["gate_count"], 3)
        websocket = next(
            gate for gate in summary["gates"]
            if gate["gate_id"] == "transport.general_websocket_capability"
        )
        self.assertIn("run_qcl079_broker_owned_websocket", websocket["next_action_ids"])
        direct_wifi = next(
            gate for gate in summary["gates"]
            if gate["gate_id"] == "transport.direct_wifi_live_topology"
        )
        self.assertIn("normalize_qcl041_wifi_direct_lifecycle_report", direct_wifi["next_action_ids"])
        product_media = next(
            gate for gate in summary["gates"]
            if gate["gate_id"] == "transport.product_tcp_media_over_direct_wifi"
        )
        self.assertIn("run_qcl082_product_media_live_session", product_media["next_action_ids"])

    def assert_valid_actions(self, gate_id: str, actions: dict[str, dict[str, Any]]) -> None:
        self.assertFalse(validate_next_actions_for_gate(gate_id, list(actions.values())))

    def assert_allowed_command_shape(self, action: dict[str, Any]) -> None:
        text = command_text(action)
        if not text:
            return
        if action["authority_owner"] == "Agent Board":
            self.assertIn("agent-board.ps1", text)
            return
        if action["action_id"] == "run_qcl082_firewall_admin_handoff":
            self.assertTrue(text.startswith("powershell -NoProfile -ExecutionPolicy Bypass"))
            return
        self.assertIn("python tools\\hostessctl\\hostessctl.py", text)

    def assert_quest_lease_metadata(self, action: dict[str, Any]) -> None:
        lease = action["lease"]
        self.assertEqual(lease["manager"], "Agent Board")
        self.assertEqual(lease["resource"], "quest:<quest-serial>")
        self.assertEqual(lease["duration"], "45m")
        self.assertIn("reserve 'quest:<quest-serial>'", lease["reserve_command"])
        self.assertIn("release '<quest-lease-id>'", lease["release_command"])
        self.assertIn("Use adb-server:lifecycle only for disruptive daemon lifecycle", lease["adb_server_lifecycle_policy"])


def actions_by_id(gate_id: str) -> dict[str, dict[str, Any]]:
    return {
        action["action_id"]: action
        for action in operator_next_actions_for_gate(gate_id)
    }


def command_text(action: dict[str, Any]) -> str:
    command = action.get("command")
    if not isinstance(command, dict):
        return ""
    return str(command.get("command") or "")


if __name__ == "__main__":
    unittest.main()
