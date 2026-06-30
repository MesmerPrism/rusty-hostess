from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.connectivity_firewall import (
    CONNECTIVITY_FIREWALL_RULE_SCHEMA,
    run_windows_firewall_rule,
    windows_firewall_rule_report,
)
from tools.hostessctl.connectivity_media_receiver import (
    run_qcl082_product_media_live_session,
    run_rmanvid1_receiver_capture,
)
from tools.hostessctl.connectivity_probe import (
    CONNECTIVITY_PROBE_SCHEMA,
    DEFAULT_QCL080_UDP_PORT,
    device_to_host_tcp_echo,
    device_to_host_udp_freshness,
    fixture_report,
    latest_qcl080_app_marker,
    live_bluetooth_report,
    live_lsl_report,
    live_osc_report,
    live_same_wifi_report,
    live_udp_freshness_report,
    live_websocket_report,
    live_zeromq_report,
    qcl080_makepad_runtime_properties,
    run_connectivity_probe,
    strip_powershell_clixml_noise,
    udp_listener_from_result,
    validate_connectivity_probe_report,
    windows_firewall_rule_report as facade_windows_firewall_rule_report,
)
from tools.hostessctl.connectivity_topology_live import live_direct_wifi_topology_report
from tools.hostessctl.connectivity_topology_lifecycle import (
    WIFI_DIRECT_LIFECYCLE_SCHEMA,
    run_wifi_direct_lifecycle_template,
    wifi_direct_lifecycle_template_artifact,
)
from tools.hostessctl.connectivity_topology_lifecycle_plan import (
    WIFI_DIRECT_LIFECYCLE_PLAN_SCHEMA,
    run_wifi_direct_lifecycle_plan,
    wifi_direct_lifecycle_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[2]

def fake_tcp_echo_pass(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    return {
        "name": "device_to_host.tcp_echo",
        "status": "pass",
        "evidence": "rusty-qcl-tcp-echo",
        "observed": {"host_ip": host_ip, "port": 49152, "elapsed_ms": 8},
        "notes": "",
        "issue_codes": [],
    }


def fake_tcp_echo_fail(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    return {
        "name": "device_to_host.tcp_echo",
        "status": "fail",
        "evidence": "timed out",
        "observed": {"host_ip": host_ip, "port": 49152, "elapsed_ms": 6000},
        "notes": "",
        "issue_codes": ["hostess.issue.connectivity_probe.tcp_echo_failed"],
    }


def fake_udp_freshness_pass(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    return {
        "name": "protocol.udp_freshness",
        "status": "pass",
        "evidence": "12/12 packets, loss=0.0%, p95_gap=50ms",
        "observed": {
            "host_ip": host_ip,
            "port": DEFAULT_QCL080_UDP_PORT,
            "marker": "rusty-qcl-udp",
            "packets_requested": 12,
            "packets_received": 12,
            "datagrams_received": 12,
            "unique_sequences": list(range(12)),
            "duplicates": 0,
            "loss_percent": 0.0,
            "elapsed_ms": 700,
            "interarrival_ms_p95": 50,
            "generator": "adb_shell_udp_generator",
        },
        "notes": "fixture UDP pass",
        "issue_codes": [],
    }


def fake_udp_freshness_app_owned_pass(args: argparse.Namespace, host_ip: str, run_timeout_func: Any) -> dict[str, Any]:
    return {
        "name": "protocol.udp_freshness",
        "status": "pass",
        "evidence": "12/12 packets, loss=0.0%, p95_gap=50ms",
        "observed": {
            "host_ip": host_ip,
            "port": DEFAULT_QCL080_UDP_PORT,
            "marker": "rusty-qcl-udp",
            "packets_requested": 12,
            "packets_received": 12,
            "datagrams_received": 12,
            "unique_sequences": list(range(12)),
            "duplicates": 0,
            "loss_percent": 0.0,
            "elapsed_ms": 700,
            "interarrival_ms_p95": 50,
            "generator": "app_owned_runtime_udp_sender",
            "runtime_marker": {
                "line": "RUSTY_HOSTESS_MAKEPAD_QCL080_UDP_SENDER schema=rusty.hostess.makepad.qcl080_udp_sender.v1 status=sent marker=rusty-qcl-udp packetsRequested=12 packetsSent=12 runId=qcl080-app senderSource=makepad-runtime socketOwner=app-owned",
                "fields": {
                    "schema": "rusty.hostess.makepad.qcl080_udp_sender.v1",
                    "status": "sent",
                    "marker": "rusty-qcl-udp",
                    "packetsRequested": "12",
                    "packetsSent": "12",
                    "runId": "qcl080-app",
                    "senderSource": "makepad-runtime",
                    "socketOwner": "app-owned",
                },
                "matched": True,
            },
        },
        "notes": "fixture app-owned UDP pass",
        "issue_codes": [],
    }


def fake_lsl_loopback_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "host-loopback",
        "stream_name": "RustyQCL081",
        "stream_type": "Markers",
        "samples_requested": 16,
        "samples_received": 16,
        "loss_percent": 0.0,
        "discovery_ms": 42,
        "monotonic_sequences": True,
        "received_sequences": list(range(16)),
        "issue_codes": [],
        "notes": "host-local LSL loopback",
    }


def fake_manifold_lsl_broker_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "manifold-lsl-broker",
        "stream_name": "RustyQCL081",
        "stream_type": "Markers",
        "source_id": "rusty-manifold-qcl081-fixture",
        "samples_requested": 16,
        "samples_received": 16,
        "loss_percent": 0.0,
        "discovery_ms": 42,
        "monotonic_sequences": True,
        "received_sequences": list(range(16)),
        "evidence_tier": "broker_owned",
        "authority_owner": "rusty.manifold.transport",
        "route_id": "bridge_route.clock.lsl.roundtrip_echo",
        "bridge_route_evidence": {
            "$schema": "rusty.manifold.bridge.route_evidence.v1",
            "route_id": "bridge_route.clock.lsl.roundtrip_echo",
            "status": "pass",
            "stage_reports": [
                {"stage": "sent", "status": "pass", "issue_codes": []},
                {"stage": "transport_ok", "status": "pass", "issue_codes": []},
                {"stage": "observed", "status": "pass", "issue_codes": []},
            ],
            "issues": [],
        },
        "issue_codes": [],
        "notes": "Manifold-owned LSL route evidence",
    }


def fake_external_lsl_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "external",
        "stream_name": "RustyQCL081",
        "stream_type": "Markers",
        "samples_requested": 16,
        "samples_received": 16,
        "loss_percent": 0.0,
        "discovery_ms": 42,
        "monotonic_sequences": True,
        "received_sequences": list(range(16)),
        "issue_codes": [],
        "notes": "External LSL stream without Quest-runtime or broker-owned authority",
    }


def fake_osc_loopback_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "host-loopback",
        "address": "/rusty/qcl083",
        "messages_requested": 16,
        "messages_received": 16,
        "messages_acknowledged": 16,
        "loss_percent": 0.0,
        "round_trip_ms_p95": 8,
        "monotonic_sequences": True,
        "received_sequences": list(range(16)),
        "issue_codes": [],
        "notes": "host-local OSC loopback",
    }


def fake_zeromq_loopback_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "host-loopback",
        "pattern": "req-rep",
        "messages_requested": 16,
        "messages_received": 16,
        "messages_acknowledged": 16,
        "round_trip_ms_p95": 5,
        "received_sequences": list(range(16)),
        "issue_codes": [],
        "notes": "host-local ZeroMQ loopback",
    }


def fake_native_rust_broker_zeromq_pass(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "pass",
        "source": "native-rust-broker",
        "pattern": "pub-sub",
        "messages_requested": 16,
        "messages_received": 16,
        "messages_acknowledged": 16,
        "round_trip_ms_p95": None,
        "received_sequences": list(range(16)),
        "dropped_count": 0,
        "decode_error_count": 0,
        "evidence_tier": "broker_owned",
        "authority_owner": "rusty.manifold.transport",
        "bridge_route_evidence": {
            "$schema": "rusty.manifold.bridge.route_evidence.v1",
            "route_id": "bridge_route.stream.zeromq.pub_sub",
            "status": "pass",
            "stage_reports": [
                {"stage": "sent", "status": "pass", "issue_codes": []},
                {"stage": "transport_ok", "status": "pass", "issue_codes": []},
                {"stage": "observed", "status": "pass", "issue_codes": []},
            ],
            "issues": [],
        },
        "issue_codes": [],
        "notes": "native Rust Manifold-owned ZeroMQ route evidence",
    }


def fake_zeromq_dependency_missing(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "status": "blocked",
        "source": "host-loopback",
        "pattern": "req-rep",
        "messages_requested": 16,
        "messages_received": 0,
        "messages_acknowledged": 0,
        "round_trip_ms_p95": None,
        "received_sequences": [],
        "issue_codes": ["hostess.issue.connectivity_probe.pyzmq_unavailable"],
        "notes": "pyzmq unavailable",
    }


class FakeRunner:
    def __init__(
        self,
        *,
        protocol: str = "TCP",
        listener_port: int = 49152,
        quest_activity_locked: bool = False,
    ) -> None:
        self.protocol = protocol
        self.listener_port = listener_port
        self.quest_activity_locked = quest_activity_locked

    def __call__(
        self,
        command: list[str],
        *,
        allow_failure: bool = False,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        text = " ".join(command)
        if "get-state" in text:
            return subprocess.CompletedProcess(command, 0, "device\n", "")
        if "ro.product.model" in text:
            return subprocess.CompletedProcess(command, 0, "Quest 3S\n", "")
        if "ro.build.version.sdk" in text:
            return subprocess.CompletedProcess(command, 0, "35\n", "")
        if "ro.build.version.incremental" in text:
            return subprocess.CompletedProcess(command, 0, "2.5.fixture\n", "")
        if "pm list features" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                "feature:android.hardware.wifi\nfeature:android.hardware.wifi.direct\n",
                "",
            )
        if "ip -o -4 addr show wlan0" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                "21: wlan0 inet 192.0.2.42/24 brd 192.0.2.255 scope global wlan0\n",
                "",
            )
        if "NetworkOperatorTetheringManager" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "available": True,
                        "state": "On",
                        "source_profile": "fixture-upstream",
                        "client_count": 1,
                        "max_client_count": 8,
                        "ssid": "RustyHostess-QCL011",
                        "passphrase_set": True,
                        "band": "Auto",
                    }
                ),
                "",
            )
        if "Get-NetAdapter" in text and "Wi-Fi Direct" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "available": True,
                        "adapter_count": 1,
                        "adapter_names": ["Local Area Connection* 12"],
                        "source": "fixture_get_netadapter",
                    }
                ),
                "",
            )
        if "Get-PnpDevice -Class Bluetooth" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "available": True,
                        "adapter_status": "OK",
                        "adapter_name": "fixture Bluetooth Adapter",
                        "bthserv_status": "Running",
                        "user_service_running": True,
                        "service_count": 2,
                        "address_redacted": True,
                    }
                ),
                "",
            )
        if "dumpsys bluetooth_manager" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                "\n".join(
                    [
                        "Bluetooth Status",
                        "  enabled: true",
                        "  state: ON",
                        "  address: 12:34:56:78:9A:BC",
                        "  name: Quest fixture",
                        "AdapterProperties",
                        "  Name: Quest fixture",
                        "  Address: 12:34:56:78:9A:BC",
                        "  ConnectionState: STATE_DISCONNECTED",
                        "  State: ON",
                        "  Bonded devices:",
                        "    XX:XX:XX:XX:A5:A5 last_active_time=0",
                    ]
                ),
                "",
            )
        if "cmd bluetooth_manager" in text:
            return subprocess.CompletedProcess(
                command,
                1,
                "Bluetooth Manager Commands:\n  enable\n  disable\n  wait-for-state:<STATE>\n",
                "",
            )
        if "dumpsys activity activities" in text:
            if self.quest_activity_locked:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    "topResumedActivity=ActivityRecord{fixture com.oculus.os.vrlockscreen/.SensorLockActivity}\n",
                    "",
                )
            return subprocess.CompletedProcess(
                command,
                0,
                "topResumedActivity=ActivityRecord{fixture io.github.mesmerprism.rustyhostess.t/.MainActivity}\n",
                "",
            )
        if " shell pm grant " in text and "android.permission.BLUETOOTH_" in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell rm -f " in text and "qcl050-rfcomm/latest.json" in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell rm -f " in text and "qcl051-ble-gatt/latest.json" in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell am force-stop " in text and "io.github.mesmerprism.rustyhostess.t" in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell am start " in text and "RUN_QCL050_RFCOMM" in text:
            return subprocess.CompletedProcess(command, 0, "Starting: Intent\n", "")
        if " shell am start " in text and "RUN_QCL051_BLE_GATT" in text:
            return subprocess.CompletedProcess(command, 0, "Starting: Intent\n", "")
        if "fixture-qcl050-helper.exe" in text:
            helper_out = Path(command[command.index("--out") + 1])
            run_id = command[command.index("--run-id") + 1]
            helper_out.parent.mkdir(parents=True, exist_ok=True)
            helper_out.write_text(json.dumps(qcl050_windows_helper_report(run_id=run_id)) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")
        if "fixture-qcl051-helper.exe" in text:
            helper_out = Path(command[command.index("--out") + 1])
            run_id = command[command.index("--run-id") + 1]
            helper_out.parent.mkdir(parents=True, exist_ok=True)
            helper_out.write_text(json.dumps(qcl051_windows_helper_report(run_id=run_id)) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell cat " in text and "qcl050-rfcomm/latest.json" in text:
            return subprocess.CompletedProcess(command, 0, json.dumps(qcl050_android_probe_report()) + "\n", "")
        if " shell cat " in text and "qcl051-ble-gatt/latest.json" in text:
            return subprocess.CompletedProcess(command, 0, json.dumps(qcl051_android_probe_report()) + "\n", "")
        if "Get-NetConnectionProfile" in text:
            return subprocess.CompletedProcess(
                command,
                0,
                firewall_profile_json(protocol=self.protocol, listener_port=self.listener_port),
                "",
            )
        return subprocess.CompletedProcess(command, 1, "", f"unexpected command: {text}")


class FakeTimeoutRunner:
    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        text = " ".join(command)
        if "ping" in text:
            return subprocess.CompletedProcess(command, 0, "2 packets transmitted, 2 received, 0% packet loss\n", "")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected timeout command: {text}")


class OneWayPingTimeoutRunner:
    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        text = " ".join(command)
        if text.startswith("ping "):
            return subprocess.CompletedProcess(command, 0, "Packets: Sent = 2, Received = 2, Lost = 0 (0% loss),\n", "")
        if " shell ping " in text:
            return subprocess.CompletedProcess(command, 1, "2 packets transmitted, 0 received, 100% packet loss\n", "")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected timeout command: {text}")


class TcpEchoCommandRunner:
    def __init__(self) -> None:
        self.command: list[str] = []

    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        self.command = command
        command_text = command[-1]
        parts = command_text.split()
        host_index = parts.index("127.0.0.1")
        port = int(parts[host_index + 1])
        with socket.create_connection(("127.0.0.1", port), timeout=timeout_seconds) as client:
            client.sendall(b"rusty-qcl-tcp-echo")
        return subprocess.CompletedProcess(command, 0, "", "")


class UdpFreshnessCommandRunner:
    def __init__(self) -> None:
        self.command: list[str] = []

    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        self.command = command
        command_text = command[-1]
        parts = command_text.split()
        host_index = parts.index("127.0.0.1")
        port = int(parts[host_index + 1])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.settimeout(timeout_seconds)
            for sequence in range(4):
                client.sendto(f"rusty-qcl-udp|{sequence:04d}\n".encode("utf-8"), ("127.0.0.1", port))
        return subprocess.CompletedProcess(command, 0, "", "")


class MakepadRuntimeUdpCommandRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.properties: dict[str, str] = {}

    def __call__(
        self,
        command: list[str],
        *,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        text = " ".join(command)
        if " shell setprop " in text:
            key = command[-2]
            value = command[-1]
            self.properties[key] = value
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell am force-stop " in text:
            return subprocess.CompletedProcess(command, 0, "", "")
        if " shell am start " in text:
            self.send_configured_packets(timeout_seconds)
            return subprocess.CompletedProcess(command, 0, "Starting: Intent\n", "")
        if " shell logcat " in text:
            return subprocess.CompletedProcess(command, 0, self.logcat_text(), "")
        return subprocess.CompletedProcess(command, 1, "", f"unexpected command: {text}")

    def send_configured_packets(self, timeout_seconds: float) -> None:
        host = self.properties["debug.rustyquest.makepad.qcl080.udp.host"]
        port = int(self.properties["debug.rustyquest.makepad.qcl080.udp.port"])
        marker = self.properties["debug.rustyquest.makepad.qcl080.udp.marker"]
        count = int(self.properties["debug.rustyquest.makepad.qcl080.udp.packet.count"])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.settimeout(timeout_seconds)
            for sequence in range(count):
                client.sendto(f"{marker}|{sequence:04d}\n".encode("utf-8"), (host, port))

    def logcat_text(self) -> str:
        marker = self.properties["debug.rustyquest.makepad.qcl080.udp.marker"]
        run_id = self.properties["debug.rustyquest.makepad.qcl080.udp.run.id"]
        count = self.properties["debug.rustyquest.makepad.qcl080.udp.packet.count"]
        host = self.properties["debug.rustyquest.makepad.qcl080.udp.host"]
        port = self.properties["debug.rustyquest.makepad.qcl080.udp.port"]
        return (
            "06-28 13:00:00.000 I/HostessMakepad: "
            "RUSTY_HOSTESS_MAKEPAD_QCL080_UDP_SENDER "
            "schema=rusty.hostess.makepad.qcl080_udp_sender.v1 "
            f"phase=startup status=sent enabled=true host={host} port={port} "
            f"marker={marker} packetsRequested={count} packetsSent={count} "
            f"intervalMs=1 elapsedMs=4 runId={run_id} issue=none "
            "senderSource=makepad-runtime socketOwner=app-owned "
            "highRateJsonPayload=false settingsControlPayload=false\n"
        )


def check(report: dict[str, Any], name: str) -> dict[str, Any]:
    for row in report["checks"]:
        if row["name"] == name:
            return row
    raise AssertionError(f"missing check {name}")


def free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def send_rmanvid1_loopback_payload(port: int, payload: bytes) -> None:
    deadline = time.monotonic() + 2.0
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25) as client:
                for offset in range(0, len(payload), 23):
                    client.sendall(payload[offset : offset + 23])
                    time.sleep(0.001)
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.025)
    raise AssertionError(f"receiver did not accept loopback connection: {last_error}")


def probe_args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "command": "connectivity-probe",
        "connectivity_probe_command": "run",
        "out": "target/connectivity-probe/report.json",
        "validation_out": None,
        "probe_id": "QCL-010",
        "run_id": "",
        "mode": "fixture",
        "fixture_profile": "",
        "media_stream_session_plan": "",
        "media_stream_runtime_status": "",
        "media_stream_rmanvid1_capture": "",
        "media_stream_receiver_sidecar": "",
        "media_stream_receiver_result": "",
        "media_stream_topology_report": "",
        "media_stream_firewall_report": "",
        "wifi_direct_lifecycle_report": "",
        "capture_out": "target/connectivity-probe/media-stream.rmanvid1",
        "sidecar_out": "target/connectivity-probe/media-stream-receiver-sidecar.json",
        "bind_host": "0.0.0.0",
        "port": 9079,
        "timeout_seconds": 10.0,
        "max_packets": 240,
        "max_bytes": 67108864,
        "max_packet_bytes": 4194304,
        "max_metadata_bytes": 262144,
        "queue_capacity_packets": 48,
        "capture_kind": "fixture_loopback_receiver",
        "source_endpoint_source": "",
        "source_remote_endpoint": "",
        "command_id": "command.media_stream.start_source",
        "session_id": "",
        "runtime_status": "",
        "topology_report": "",
        "firewall_report": "",
        "start_source_request_out": "target/connectivity-probe/media-stream-start-source.request.json",
        "bridge_evidence_out": "target/connectivity-probe/media-stream-start-source.bridge-evidence.json",
        "execution_out": "target/connectivity-probe/media-stream-start-source.live-android-execution.json",
        "bridge_command": "command.media_stream.start_source",
        "request_id": "",
        "evidence_id": "",
        "route_id": "bridge_route.command.websocket.applied",
        "required_stage": [],
        "params_json": None,
        "params_json_file": None,
        "route_descriptor": "",
        "logcat_out": "",
        "broker_package": "io.github.mesmerprism.rustymanifold.broker",
        "broker_activity": "",
        "broker_host": "127.0.0.1",
        "broker_port": 8765,
        "broker_local_port": 18765,
        "broker_path": "/manifold/v1/events",
        "connect_timeout_seconds": 5.0,
        "wait_seconds": 15.0,
        "runtime_receipt_stream": "stream.hostess.makepad.bridge_command.receipt",
        "no_runtime_receipt_subscribe": False,
        "makepad_package": "io.github.mesmerprism.rustyhostess.makepad",
        "makepad_activity": "io.github.mesmerprism.rustyhostess.makepad/.MakepadAppXr",
        "broker_process_wait_seconds": 8.0,
        "makepad_process_wait_seconds": 8.0,
        "socket_wait_seconds": 8.0,
        "launch_settle_seconds": 8.0,
        "runtime_subscriber_retry_count": 1,
        "runtime_subscriber_retry_wait_seconds": 5.0,
        "live_command_join_timeout_seconds": 30.0,
        "no_launch_broker": False,
        "no_launch_makepad": False,
        "no_wait_broker_process": False,
        "no_wait_makepad_process": False,
        "no_adb_forward_broker": False,
        "adb": "adb.exe",
        "serial": "serial-1",
        "wifi_interface": "wlan0",
        "host_ip": "",
        "topology_owner": "",
        "network_provider": "",
        "skip_host_ping": False,
        "skip_device_ping": False,
        "skip_tcp_echo": False,
        "tcp_echo_bind_host": "0.0.0.0",
        "tcp_echo_port": 0,
        "tcp_echo_marker": "rusty-qcl-tcp-echo",
        "tcp_timeout_seconds": 1.0,
        "skip_udp_freshness": False,
        "udp_bind_host": "0.0.0.0",
        "udp_port": 0,
        "udp_marker": "rusty-qcl-udp",
        "udp_packet_count": 12,
        "udp_interval_ms": 50.0,
        "udp_timeout_seconds": 1.0,
        "udp_max_loss_percent": 10.0,
        "udp_max_jitter_ms": 250.0,
        "udp_listener_helper": "",
        "udp_sender_source": "auto",
        "udp_sender_host_path": "",
        "udp_sender_device_path": "/data/local/tmp/rusty-qcl080-udp-sender",
        "makepad_package": "io.github.mesmerprism.rustyhostess.makepad",
        "makepad_activity": "io.github.mesmerprism.rustyhostess.makepad/.MakepadAppXr",
        "skip_makepad_force_stop": False,
        "makepad_launch_timeout_seconds": 10.0,
        "lsl_source": "host-loopback",
        "lsl_stream_name": "RustyQCL081",
        "lsl_stream_type": "Markers",
        "lsl_sample_count": 16,
        "lsl_timeout_seconds": 1.0,
        "lsl_manifold_root": "",
        "osc_source": "host-loopback",
        "osc_address": "/rusty/qcl083",
        "osc_port": 0,
        "osc_message_count": 16,
        "osc_timeout_seconds": 1.0,
        "osc_max_loss_percent": 0.0,
        "zeromq_source": "host-loopback",
        "zeromq_pattern": "req-rep",
        "zeromq_message_count": 16,
        "zeromq_timeout_seconds": 1.0,
        "zeromq_port": 18784,
        "zeromq_android_binary_host_path": "",
        "zeromq_android_binary_device_path": "/data/local/tmp/rusty-qcl084-req-rep-probe",
        "zeromq_manifold_root": "",
        "zeromq_rusty_xr_root": "",
        "zeromq_goofi_bridge_root": "",
        "zeromq_cargo_timeout_seconds": 120.0,
        "websocket_source": "host-loopback",
        "websocket_bind_host": "127.0.0.1",
        "websocket_port": 0,
        "websocket_path": "/qcl079",
        "websocket_message_count": 16,
        "websocket_payload_bytes": 96,
        "websocket_timeout_seconds": 1.0,
        "websocket_route_descriptor": "",
        "websocket_route_evidence": "",
        "ping_count": 2,
        "ping_timeout_seconds": 1.0,
        "fail_on_error": False,
        "handoff_script_out": "",
        "handoff_verify_out": "",
        "bluetooth_payload_source": "passive",
        "bluetooth_helper": "",
        "bluetooth_message_count": 3,
        "bluetooth_reconnect_count": 0,
        "bluetooth_timeout_seconds": 20.0,
        "hostess_android_package": "io.github.mesmerprism.rustyhostess.t",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_websocket_route_files(root: Path, *, command_route: bool = False) -> tuple[Path, Path]:
    descriptor = {
        "$schema": "rusty.manifold.bridge.route_descriptor.v1",
        "route_id": (
            "bridge_route.command.websocket.applied"
            if command_route
            else "bridge_route.stream.websocket.ordered"
        ),
        "route_kind": "command" if command_route else "stream_bridge",
        "plane": "control" if command_route else "data",
        "transport_family": "web_socket",
        "delivery": "applied_receipt_required" if command_route else "ordered",
        "payload_class": "command_envelope" if command_route else "stream_packet",
        "rate_class": "event" if command_route else "periodic",
        "authority_role": "authority" if command_route else "adapter",
        "required_evidence_stages": (
            ["sent", "transport_ok", "authority_accepted", "runtime_accepted", "applied"]
            if command_route
            else ["sent", "transport_ok", "observed"]
        ),
        "required_conditions": [
            {
                "condition_id": "condition.host.websocket_firewall_inbound",
                "scope": "security",
                "kind": "host_firewall_inbound_allowed",
                "required_state": "allowed",
                "check_ref": "check.host.firewall.websocket_inbound",
                "issue_codes": ["issue.host.firewall_blocked"],
            }
        ],
        "timing": {
            "rtt_strategy": "applied_receipt_echo" if command_route else "transport_echo",
            "clock_domain": "clock.host_monotonic",
            "min_round_trips": 1 if command_route else 8,
            "timeout_ms": 5000,
            "warmup_ms": 0 if command_route else 250,
            "reported_metrics": ["rtt_ms", "jitter_ms"],
        },
    }
    evidence = {
        "$schema": "rusty.manifold.bridge.route_evidence.v1",
        "evidence_id": (
            "evidence.bridge_route.command.websocket.applied"
            if command_route
            else "evidence.bridge_route.stream.websocket.ordered.loopback"
        ),
        "route_id": descriptor["route_id"],
        "status": "pass",
        "started_at_ms": 1765000003000,
        "ended_at_ms": 1765000003280,
        "stage_reports": [
            {
                "stage": "sent",
                "status": "pass",
                "observed_at_ms": 1765000003010,
                "evidence_refs": ["evidence.websocket.stream.producer.sent"],
                "issue_codes": [],
            },
            {
                "stage": "transport_ok",
                "status": "pass",
                "observed_at_ms": 1765000003050,
                "evidence_refs": [
                    "evidence.websocket.http_upgrade.accepted",
                    "evidence.websocket.sec_websocket_accept.valid",
                ],
                "issue_codes": [],
            },
        ],
        "artifact_refs": ["artifact.websocket.stream.loopback.report"],
        "issues": [],
    }
    if command_route:
        evidence["stage_reports"].extend(
            [
                {
                    "stage": "authority_accepted",
                    "status": "pass",
                    "observed_at_ms": 1765000003060,
                    "evidence_refs": ["evidence.manifold.command_ack"],
                    "issue_codes": [],
                },
                {
                    "stage": "runtime_accepted",
                    "status": "pass",
                    "observed_at_ms": 1765000003180,
                    "evidence_refs": ["evidence.runtime.receipt"],
                    "issue_codes": [],
                },
                {
                    "stage": "applied",
                    "status": "pass",
                    "observed_at_ms": 1765000003270,
                    "evidence_refs": ["evidence.runtime.effective_state"],
                    "issue_codes": [],
                },
            ]
        )
    else:
        evidence["stage_reports"].append(
            {
                "stage": "observed",
                "status": "pass",
                "observed_at_ms": 1765000003270,
                "evidence_refs": ["evidence.websocket.stream.consumer.received"],
                "issue_codes": [],
            }
        )

    descriptor_path = root / "websocket-route.json"
    evidence_path = root / "websocket-evidence.json"
    descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    return descriptor_path, evidence_path


def qcl050_windows_helper_report(*, run_id: str = "qcl050-unit-rfcomm") -> dict[str, Any]:
    return {
        "schema": "rusty.hostess.windows.qcl050_rfcomm_client.v1",
        "schema_version": 1,
        "run_id": run_id,
        "status": "pass",
        "role": "windows_rfcomm_client",
        "messages_requested": 3,
        "messages_completed": 3,
        "bytes_written": 99,
        "bytes_read": 183,
        "selected_device": {
            "id_redacted": True,
            "name": "Quest",
            "is_paired": True,
            "can_pair": False,
        },
        "measurements": {
            "round_trip_ms_p95": 22.0,
            "round_trip_ms_max": 22.0,
        },
        "messages": [
            {"sequence": 1, "payload_bytes": 33, "status_bytes": 61, "round_trip_ms": 18.0},
            {"sequence": 2, "payload_bytes": 33, "status_bytes": 61, "round_trip_ms": 20.0},
            {"sequence": 3, "payload_bytes": 33, "status_bytes": 61, "round_trip_ms": 22.0},
        ],
        "issues": [],
        "errors": [],
    }


def qcl050_android_probe_report() -> dict[str, Any]:
    return {
        "schema": "rusty.hostess.android.qcl050_rfcomm_probe.v1",
        "schema_version": 1,
        "run_id": "qcl050-unit-rfcomm",
        "status": "pass",
        "role": "quest_rfcomm_server",
        "authority": "app_owned_runtime_rfcomm_server",
        "messages_expected": 3,
        "messages_received": 3,
        "bytes_received": 99,
        "bytes_written": 183,
        "client_addresses_redacted": True,
        "permissions": {
            "bluetooth_connect": True,
            "address_redacted": True,
        },
        "rfcomm_server": {
            "server_socket_opened": True,
            "server_socket_closed": True,
            "client_socket_accepted": True,
            "client_socket_closed": True,
        },
        "payloads": [
            {"sequence": 1, "byte_count": 33, "redacted": False},
            {"sequence": 2, "byte_count": 33, "redacted": False},
            {"sequence": 3, "byte_count": 33, "redacted": False},
        ],
        "errors": [],
        "issue_codes": [],
    }


def qcl051_windows_helper_report(*, run_id: str = "qcl051-unit-ble-gatt") -> dict[str, Any]:
    return {
        "schema": "rusty.hostess.windows.qcl051_ble_gatt_client.v1",
        "schema_version": 1,
        "run_id": run_id,
        "status": "pass",
        "role": "windows_ble_gatt_client",
        "messages_requested": 3,
        "messages_completed": 3,
        "bytes_written": 96,
        "bytes_read": 180,
        "selected_device": {
            "address_redacted": True,
            "local_name": "",
            "is_paired": False,
            "can_pair": True,
        },
        "measurements": {
            "round_trip_ms_p95": 15.0,
            "round_trip_ms_max": 15.0,
        },
        "messages": [
            {"sequence": 1, "payload_bytes": 32, "status_bytes": 60, "round_trip_ms": 10.0},
            {"sequence": 2, "payload_bytes": 32, "status_bytes": 60, "round_trip_ms": 12.0},
            {"sequence": 3, "payload_bytes": 32, "status_bytes": 60, "round_trip_ms": 15.0},
        ],
        "issues": [],
        "errors": [],
    }


def qcl051_android_probe_report() -> dict[str, Any]:
    return {
        "schema": "rusty.hostess.android.qcl051_ble_gatt_probe.v1",
        "schema_version": 1,
        "run_id": "qcl051-unit-ble-gatt",
        "status": "pass",
        "role": "quest_ble_gatt_server",
        "authority": "app_owned_runtime_ble_gatt_server",
        "messages_expected": 3,
        "messages_received": 3,
        "read_requests": 3,
        "bytes_received": 96,
        "bytes_read": 180,
        "client_addresses_redacted": True,
        "permissions": {
            "bluetooth_connect": True,
            "bluetooth_advertise": True,
            "address_redacted": True,
        },
        "advertising": {
            "started": True,
            "stopped": True,
        },
        "gatt_server": {
            "opened": True,
            "closed": True,
            "service_added": True,
            "service_add_status": 0,
        },
        "payloads": [
            {"sequence": 1, "byte_count": 32, "redacted": False},
            {"sequence": 2, "byte_count": 32, "redacted": False},
            {"sequence": 3, "byte_count": 32, "redacted": False},
        ],
        "errors": [],
        "issue_codes": [],
    }


def media_stream_session_plan(
    *,
    high_rate_payload_plane: str = "binary-media",
    shell_display: bool = False,
    shell_display_production: bool = False,
) -> dict[str, Any]:
    source_kind = (
        "shell_display_mirror_mediacodec_surface"
        if shell_display
        else "display_composite_mediaprojection_mediacodec_surface"
    )
    source_family = "quest-shell-display-mirror" if shell_display else "quest-display-composite-mediaprojection"
    source_id = "quest-a-shell-display-mirror" if shell_display else "quest-a-display-composite"
    return {
        "schema": "rusty.quest.media_stream_session.v1",
        "session_id": "session.media_stream.test",
        "topology_id": "quest_display_to_pc",
        "privacy_tier": "local_lan_diagnostic",
        "devices": [
            {"device_id": "quest-a", "device_kind": "quest", "role": "sender"},
            {"device_id": "pc-host", "device_kind": "windows_pc", "role": "receiver"},
        ],
        "sources": [
            {
                "source_id": source_id,
                "device_id": "quest-a",
                "source_family": source_family,
                "source_kind": source_kind,
                "capture_route": "shell-hidden-display-mirror" if shell_display else "display-composite",
                "capture_authority": (
                    "adb_shell_hidden_api_developer_only"
                    if shell_display
                    else "android_mediaprojection_consent"
                ),
                "deployment_classification": (
                    "production_candidate"
                    if shell_display_production
                    else "lab_developer_only"
                    if shell_display
                    else "production_candidate"
                ),
                "track_role": "display",
                "developer_shell_required": shell_display and not shell_display_production,
                "consent_required": not shell_display,
                "display": {
                    "display_id": "default",
                    "rotation": "runtime-reported",
                    "density_dpi": 320,
                    "content_crop": {
                        "left": 0,
                        "top": 0,
                        "width": 1920,
                        "height": 1080,
                    },
                    "protected_content_policy": "omit-protected-content",
                    "consent_state": "android-mediaprojection-consent-required",
                    "privacy_indicator": "system-capture-indicator-required",
                    "foreground_package_reporting": "not-collected",
                },
            }
        ],
        "lanes": [
            {
                "lane_id": "quest-a-display-to-pc-host",
                "direction": "outgoing",
                "source_id": source_id,
                "source_device_id": "quest-a",
                "sink_device_id": "pc-host",
                "media": {
                    "track_id": "quest-a.display.h264",
                    "track_role": "display",
                    "track_kind": "video",
                    "codec": "h264",
                    "stream_framing": "diagnostic-h264-packet-stream",
                    "width": 1920,
                    "height": 1080,
                    "frame_rate_hz": 60,
                    "bitrate_bps": 8000000,
                    "max_packet_bytes": 4194304,
                    "metadata_transport": "stream-header-sidecar-status",
                    "timestamp_domain": "android-display-frame-time",
                    "high_rate_payload_plane": high_rate_payload_plane,
                },
                "transport": {
                    "transport_kind": "lan_tcp",
                    "relay_required": False,
                    "encryption_required": False,
                },
                "queue": {
                    "max_buffered_packets": 48,
                    "max_buffered_bytes": 16777216,
                    "drop_policy": "drop-oldest-complete-frame",
                    "slow_peer_close": True,
                },
                "receiver_first_required": True,
            }
        ],
        "runtime_endpoints": [
            {
                "device_id": "quest-a",
                "adapter_kind": "quest_manifold_broker_android",
                "source_bindings": [
                    {
                        "source_id": source_id,
                        "track_role": "display",
                        "source_host": "127.0.0.1",
                        "source_port": 8879,
                    }
                ],
                "receiver_bind_host": "127.0.0.1",
                "receiver_ports": [],
                "transport_bind_host": "0.0.0.0",
                "transport_receive_ports": [],
            },
            {
                "device_id": "pc-host",
                "adapter_kind": "windows_hostess",
                "source_bindings": [],
                "receiver_bind_host": "127.0.0.1",
                "receiver_ports": [{"track_role": "display", "port": 8979}],
                "transport_bind_host": "0.0.0.0",
                "transport_receive_ports": [{"track_role": "display", "port": 9079}],
            },
        ],
        "transport_routes": [
            {
                "lane_id": "quest-a-display-to-pc-host",
                "source_device_id": "quest-a",
                "sink_device_id": "pc-host",
                "track_role": "display",
                "route_kind": "direct_tcp_connect",
                "connect_host": "pc-host.local",
                "connect_port": 9079,
            }
        ],
        "security": {
            "visible_streaming_indicator": True,
            "explicit_pairing_required": True,
            "immediate_stop_command": "media_stream.stop",
            "raw_media_logging": False,
        },
        "observability": {
            "required_markers": [
                "media-stream-session-started",
                "receiver-armed",
                "display-source-bound",
                "sender-started",
                "frame-painted",
                "lane-closed",
            ],
            "required_counters": [
                "bytes_sent",
                "bytes_received",
                "media_packets",
                "codec_config_packets",
                "keyframes",
                "queue_drops",
                "close_reason",
                "capture_to_encode_ms",
                "encode_to_receive_ms",
            ],
        },
    }


def media_stream_runtime_ack(*, high_rate_json_payload: bool = False) -> dict[str, Any]:
    runtime_status = {
        "schema": "rusty.quest.media_stream.android_runtime_status.v1",
        "runtime_family": "media_stream",
        "compatibility_runtime": "remote_camera",
        "session_id": "session.media_stream.test",
        "active_count": 0,
        "matched_count": 0,
        "created_count": 0,
        "stopped_count": 0,
        "failed_count": 0,
        "lanes": [],
        "high_rate_json_payload": high_rate_json_payload,
        "media_payload_plane": "json-event" if high_rate_json_payload else "binary-media",
        "sender_source_runtime": {
            "session_id": "session.media_stream.test",
            "source_count": 0,
            "sources": [],
            "high_rate_json_payload": high_rate_json_payload,
        },
    }
    media_stream_runtime = {
        "schema": "rusty.quest.media_stream.android_runtime_status.v1",
        "command_id": "command.media_stream.start_source",
        "runtime_family": "media_stream",
        "compatibility_runtime": "remote_camera",
        "session_id": "session.media_stream.test",
        "status": "sender_source_unavailable",
        "high_rate_json_payload": high_rate_json_payload,
        "media_socket_runtime_started": False,
        "sender_source_runtime": {
            "schema": "rusty.quest.media_stream.android_display_source_adapter.v1",
            "session_id": "session.media_stream.test",
            "source_kind": "display_composite_mediaprojection_mediacodec_surface",
            "state": "source_unavailable",
            "source_available": False,
            "runtime_started": False,
            "media_payload_plane": "json-event" if high_rate_json_payload else "binary-media",
            "high_rate_json_payload": high_rate_json_payload,
            "reason": "mediaprojection_consent_route_not_implemented_in_broker_apk",
            "source_family": "display",
            "display_frame_source": "display_composite_mediaprojection_mediacodec_surface",
            "capture_authority": "android_mediaprojection_user_consent",
            "adapter_surface_only": True,
            "lab_only": False,
            "production_allowed": True,
        },
        "runtime_status": runtime_status,
    }
    return {
        "type": "command_ack",
        "schema": "rusty.manifold.command.ack.v1",
        "request_id": "request.media-stream.test",
        "command": "command.media_stream.start_source",
        "accepted": True,
        "status": "sender_source_unavailable",
        "authority": "rusty.manifold",
        "live_stream_events_synthesized": False,
        "high_rate_json_payload": high_rate_json_payload,
        "media_socket_runtime_started": False,
        "media_stream_runtime": media_stream_runtime,
    }


def media_stream_receiver_sidecar(*, capture_kind: str = "fixture_rmanvid1_capture") -> dict[str, Any]:
    return {
        "schema": "rusty.hostess.media_stream.receiver_capture_sidecar.v1",
        "capture_kind": capture_kind,
        "receiver": {
            "local_endpoint": "0.0.0.0:9079",
            "queue_capacity_packets": 48,
            "max_queue_depth_observed": 2,
            "drop_policy": "drop-oldest-complete-frame",
            "close_policy": "close_after_sustained_overrun",
            "close_reason": "eof_after_test_window",
            "dropped_frames": 0,
            "backpressure_events": 0,
            "arrival_timestamped_packet_count": 4,
            "receiver_arrival_timestamps": True,
            "timestamp_gap_ms_p95": 33,
            "decode_error_count": 0,
        },
        "source": {
            "endpoint_source": "rusty-quest-manifold-broker-media-stream-runtime",
            "remote_endpoint": "127.0.0.1:8879",
            "command_id": "command.media_stream.start_source",
            "session_id": "session.media_stream.test",
        },
    }


def wifi_direct_lifecycle_artifact(
    *,
    probe_id: str = "QCL-041",
    cleanup: bool = True,
    socket_bounded: bool = True,
    live_evidence: bool = True,
) -> dict[str, Any]:
    windows_peer = probe_id == "QCL-041"
    peer_class = "windows" if windows_peer else "android_phone"
    peer_phase = "windows_wifi_direct_api" if windows_peer else "android_phone_peer"
    lifecycle = {
        "feature": {"status": "pass", "evidence": "android.hardware.wifi.direct"},
        peer_phase: {"status": "pass", "evidence": f"{peer_class} peer available"},
        "permission_state": {"status": "pass", "evidence": "permissions granted"},
        "peer_discovery": {"status": "pass", "evidence": "peer discovered", "peer_count": 1},
        "group_formation": {
            "status": "pass",
            "evidence": "group owner/client roles recorded",
            "local_role": "group_owner",
            "peer_role": "client",
        },
        "socket_exchange": {
            "status": "pass",
            "evidence": "bounded TCP probe exchanged",
            "protocol": "tcp",
            "payload_class": "bounded_tcp_probe" if socket_bounded else "unbounded_stream",
            "bounded": socket_bounded,
            "messages_sent": 3,
            "messages_received": 3,
        },
        "cleanup": {
            "status": "pass" if cleanup else "blocked",
            "evidence": "group removed and restart gate clean" if cleanup else "cleanup did not complete",
            "completed": cleanup,
        },
    }
    return {
        "$schema": WIFI_DIRECT_LIFECYCLE_SCHEMA,
        "schema_version": 1,
        "probe_id": probe_id,
        "peer_class": peer_class,
        "evidence_tier": "quest_runtime" if live_evidence else "fixture",
        "capture_kind": "live_wifi_direct_lifecycle" if live_evidence else "fixture_wifi_direct_lifecycle",
        "live_evidence": live_evidence,
        "observed_at_utc": "2026-06-28T13:00:00Z",
        "topology": {
            "owner": "wifi_direct",
            "network_provider": "wifi_direct",
            "endpoint_direction": "peer_to_peer_group",
            "peer_class": peer_class,
        },
        "device": {"model": "Quest 3S", "wifi_direct_role": "group_owner_or_client"},
        "host": {
            "os": "windows" if windows_peer else "android_phone_peer",
            "toolchain_profile": "fixture.wifi_direct_lifecycle",
        },
        "lease": {
            "manager": "Agent Board",
            "resource": "quest:TESTQUESTSERIAL",
            "lease_id": "unit-test-quest-lease",
            "reserved_before_live_steps": live_evidence,
            "released_after_live_steps": live_evidence,
            "adb_server_lifecycle_lease_used": False,
            "reserve_command": (
                "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' "
                "reserve 'quest:TESTQUESTSERIAL' --duration 45m "
                f"--task '{probe_id} direct Wi-Fi lifecycle evidence'"
            ),
            "release_command": (
                "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' "
                "release 'unit-test-quest-lease' --result done"
            ),
            "adb_server_lifecycle_policy": (
                "Use adb-server:lifecycle only for disruptive daemon lifecycle "
                "or Wi-Fi ADB setup/recovery. Ordinary ADB commands stay serial-scoped."
            ),
        },
        "lifecycle": lifecycle,
        "measurements": {
            "tcp_connect_ms": 91,
            "wifi_direct_peer_count": 1,
            "group_formation_ms": 320,
        },
    }


def media_stream_firewall_report(
    *,
    program: str = "S:\\Work\\repos\\active\\rusty-hostess\\apps\\hostess-companion-wpf\\bin\\Debug\\net9.0-windows\\HostessCompanion.Wpf.exe",
    port: int = 9079,
    protocol: str = "TCP",
    product_rule_verified: bool = True,
    allowed_on_active_profile: bool = True,
) -> dict[str, Any]:
    listener_firewall = {
        "program": program,
        "protocol": protocol,
        "port": port,
        "bind_host": "0.0.0.0",
        "expected_rule_name": f"Rusty Hostess WPF QCL-082 TCP RMANVID1 Media {port}",
        "expected_remote_address": "LocalSubnet",
        "active_profiles": ["Private"],
        "matching_rule_count": 1 if allowed_on_active_profile else 0,
        "product_matching_rule_count": 1 if product_rule_verified else 0,
        "product_rule_verified": product_rule_verified,
        "allowed_on_active_profile": allowed_on_active_profile,
    }
    return {
        "schema": CONNECTIVITY_FIREWALL_RULE_SCHEMA,
        "schema_version": 1,
        "observed_at_utc": "2026-06-28T13:00:00Z",
        "status": "pass" if product_rule_verified and allowed_on_active_profile else "warn",
        "action": "verify",
        "rule": {
            "name": f"Rusty Hostess WPF QCL-082 TCP RMANVID1 Media {port}",
            "direction": "Inbound",
            "action": "Allow",
            "enabled": True,
            "program": program,
            "protocol": protocol,
            "local_port": port,
            "profiles": ["Private"],
            "remote_address": "LocalSubnet",
        },
        "verification": {
            "status": "pass" if product_rule_verified else "warn",
            "product_rule_verified": product_rule_verified,
            "allowed_on_active_profile": allowed_on_active_profile,
            "listener_firewall": listener_firewall,
            "network_profile": {
                "connections": [{"InterfaceAlias": "Wi-Fi", "NetworkCategory": "Private"}],
                "listener_firewall": listener_firewall,
            },
            "issue_codes": [],
        },
    }


def rmanvid1_capture_bytes(*, invalid_magic: bool = False) -> bytes:
    metadata = json.dumps(
        {
            "schema": "rusty.quest.media_stream.rmanvid1.header_metadata.v1",
            "session_id": "session.media_stream.test",
            "source_kind": "display_composite_mediaprojection_mediacodec_surface",
        },
        separators=(",", ":"),
    ).encode("utf-8")
    packets = [
        (1000, 2, b"\x00\x00\x00\x01sps", 1_000_000, 10_000_000),
        (16666, 1, b"\x00\x00\x00\x01keyframe", 17_000_000, 26_000_000),
        (33333, 0, b"\x00\x00\x00\x01delta-a", 34_000_000, 43_000_000),
        (50000, 0, b"\x00\x00\x00\x01delta-b", 51_000_000, 60_000_000),
    ]
    data = bytearray()
    data.extend((b"BROKEN01" if invalid_magic else b"RMANVID1"))
    for value in [1, 1, 1920, 1080, 0, len(metadata)]:
        data.extend(int(value).to_bytes(4, "big"))
    data.extend(metadata)
    for presentation_time_us, flags, payload, source_elapsed_ns, source_unix_ns in packets:
        data.extend(int(presentation_time_us).to_bytes(8, "big"))
        data.extend(int(flags).to_bytes(4, "big"))
        data.extend(len(payload).to_bytes(4, "big"))
        data.extend(int(source_elapsed_ns).to_bytes(8, "big"))
        data.extend(int(source_unix_ns).to_bytes(8, "big"))
        data.extend(payload)
    return bytes(data)


def fixed_datetime() -> datetime:
    return datetime(2026, 6, 28, 13, 0, 0, tzinfo=UTC)


def firewall_profile_json(
    *,
    active_category: str = "Private",
    allowed: bool = True,
    protocol: str = "TCP",
    listener_port: int = 49152,
) -> str:
    protocol_number = 17 if protocol == "UDP" else 6
    return json.dumps(
        {
            "connections": [
                {
                    "Name": "fixture-wifi",
                    "InterfaceAlias": "Wi-Fi",
                    "InterfaceIndex": 16,
                    "NetworkCategory": active_category,
                    "IPv4Connectivity": "Internet",
                    "IPv6Connectivity": "Internet",
                }
            ],
            "firewall": [
                {
                    "Name": name,
                    "Enabled": True,
                    "DefaultInboundAction": "NotConfigured",
                    "DefaultOutboundAction": "NotConfigured",
                    "AllowInboundRules": "NotConfigured",
                    "NotifyOnListen": True,
                    "LogFileName": "%systemroot%\\system32\\LogFiles\\Firewall\\pfirewall.log",
                    "LogBlocked": False,
                    "LogAllowed": False,
                }
                for name in ["Domain", "Private", "Public"]
            ],
            "listener_firewall": {
                "program": "python.exe",
                "protocol": protocol,
                "port": listener_port,
                "bind_host": "0.0.0.0",
                "expected_rule_name": (
                    f"Rusty Hostess WPF QCL-080 UDP Freshness {listener_port}"
                    if protocol == "UDP"
                    else f"Rusty Hostess WPF QCL-010 TCP Echo {listener_port}"
                ),
                "expected_remote_address": "LocalSubnet",
                "active_profiles": [active_category],
                "matching_rule_count": 1 if allowed else 0,
                "product_matching_rule_count": 0,
                "product_rule_verified": False,
                "matching_rules": [
                    {
                        "name": "Rusty Hostess connectivity probe fixture",
                        "profiles": [active_category],
                        "profile_mask": 2 if active_category == "Private" else 4,
                        "protocol": protocol_number,
                        "local_ports": str(listener_port),
                        "remote_addresses": "LocalSubnet",
                        "application_name": "python.exe",
                        "profiles_apply_to_active": True,
                        "program_matches": True,
                        "name_matches": False,
                        "remote_address_matches": True,
                        "product_scope_matches": False,
                    }
                ]
                if allowed
                else [],
                "allowed_on_active_profile": allowed,
                "probe": "windows_firewall_com_policy",
            },
        }
    )
