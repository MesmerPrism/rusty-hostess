"""QCL-079 generic WebSocket protocol-fit helpers."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.hostessctl.connectivity_probe_common import (
    base_report,
    check_row,
    empty_measurements,
    ensure_probe_run_id,
    issue_row,
    list_value,
    object_value,
    percentile,
    round_float,
)


DEFAULT_QCL079_WEBSOCKET_PORT = 18785
WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
WEBSOCKET_ENDPOINT_SOURCE_HOST_LOOPBACK = "host-loopback"
WEBSOCKET_ENDPOINT_SOURCE_BROKER = "broker-owned-websocket"
WEBSOCKET_ENDPOINT_SOURCE_QUEST_RUNTIME = "quest-runtime"


class WebSocketProtocolError(Exception):
    """Raised when the bounded WebSocket probe observes invalid framing."""


def live_websocket_report(
    args: argparse.Namespace,
    *,
    clock_func: Any,
) -> dict[str, Any]:
    """Run the generic WebSocket probe and wrap it as a QCL-079 report."""

    observed_at = clock_func()
    if getattr(args, "probe_id", "QCL-079") != "QCL-079":
        raise SystemExit("live WebSocket currently supports --probe-id QCL-079")
    ensure_probe_run_id(args, observed_at, "QCL-079")
    source = str(getattr(args, "websocket_source", "host-loopback") or "host-loopback")
    route_descriptor = str(getattr(args, "websocket_route_descriptor", "") or "")
    route_evidence = str(getattr(args, "websocket_route_evidence", "") or "")
    if (
        source in {WEBSOCKET_ENDPOINT_SOURCE_BROKER, WEBSOCKET_ENDPOINT_SOURCE_QUEST_RUNTIME}
        and route_descriptor
        and route_evidence
    ):
        probe = websocket_bridge_route_probe(
            route_descriptor_path=route_descriptor,
            route_evidence_path=route_evidence,
            source=source,
            message_count=int(getattr(args, "websocket_message_count", 16) or 16),
            payload_bytes=int(getattr(args, "websocket_payload_bytes", 96) or 96),
        )
    elif source != "host-loopback":
        probe = {
            "status": "blocked",
            "source": source,
            "endpoint_source": source,
            "messages_requested": int(getattr(args, "websocket_message_count", 16) or 16),
            "messages_received": 0,
            "messages_acknowledged": 0,
            "round_trip_ms_p95": None,
            "payload_bytes_max": int(getattr(args, "websocket_payload_bytes", 96) or 96),
            "bounded_messages": False,
            "high_rate_json_payload": False,
            "not_command_authority": source != WEBSOCKET_ENDPOINT_SOURCE_BROKER,
            "handshake_complete": False,
            "issue_codes": ["hostess.issue.connectivity_probe.websocket_source_not_implemented"],
            "notes": (
                "QCL-079 broker/Quest-runtime evidence requires "
                "--websocket-route-descriptor and --websocket-route-evidence"
            ),
        }
    else:
        probe = websocket_loopback_probe(
            run_id=str(getattr(args, "run_id", "") or "qcl079-websocket"),
            bind_host=str(getattr(args, "websocket_bind_host", "127.0.0.1") or "127.0.0.1"),
            bind_port=int(getattr(args, "websocket_port", 0) or 0),
            path=str(getattr(args, "websocket_path", "/qcl079") or "/qcl079"),
            message_count=int(getattr(args, "websocket_message_count", 16) or 16),
            payload_bytes=int(getattr(args, "websocket_payload_bytes", 96) or 96),
            timeout_seconds=float(getattr(args, "websocket_timeout_seconds", 5.0) or 5.0),
        )
    report = base_report(args, observed_at=observed_at, probe_id="QCL-079")
    report.update(qcl079_body_from_probe(probe, source=source))
    return report


def websocket_bridge_route_probe(
    *,
    route_descriptor_path: str,
    route_evidence_path: str,
    source: str,
    message_count: int,
    payload_bytes: int,
) -> dict[str, Any]:
    """Build QCL-079 evidence from a Manifold WebSocket stream route."""

    issue_codes: list[str] = []
    try:
        descriptor = read_json_object(route_descriptor_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        descriptor = {}
        issue_codes.append("hostess.issue.connectivity_probe.websocket_route_descriptor_unreadable")
        descriptor_error = f"{type(exc).__name__}: {exc}"
    else:
        descriptor_error = ""

    try:
        evidence = read_json_object(route_evidence_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        evidence = {}
        issue_codes.append("hostess.issue.connectivity_probe.websocket_route_evidence_unreadable")
        evidence_error = f"{type(exc).__name__}: {exc}"
    else:
        evidence_error = ""

    route_id = str(descriptor.get("route_id") or "")
    evidence_route_id = str(evidence.get("route_id") or "")
    required_stages = {str(stage) for stage in descriptor.get("required_evidence_stages", [])}
    stage_reports = list_value(evidence.get("stage_reports"))
    passed_stages = {
        str(stage.get("stage") or "")
        for stage in stage_reports
        if str(stage.get("status") or "") in {"pass", "warn"}
    }
    transport_stage = next(
        (stage for stage in stage_reports if str(stage.get("stage") or "") == "transport_ok"),
        {},
    )
    transport_refs = {str(ref) for ref in transport_stage.get("evidence_refs", []) or []}
    timing = object_value(descriptor.get("timing"))
    min_round_trips = int_value(timing.get("min_round_trips")) or 0
    messages_requested = max(1, int(message_count or 16), min_round_trips)
    payload_bytes = max(8, min(int(payload_bytes or 96), 4096))

    descriptor_ok = (
        descriptor.get("$schema") == "rusty.manifold.bridge.route_descriptor.v1"
        and route_id
        and str(descriptor.get("transport_family") or "") == "web_socket"
        and str(descriptor.get("route_kind") or "") == "stream_bridge"
        and str(descriptor.get("plane") or "") == "data"
        and str(descriptor.get("payload_class") or "") == "stream_packet"
        and str(descriptor.get("authority_role") or "") == "adapter"
        and {"sent", "transport_ok", "observed"}.issubset(required_stages)
    )
    if not descriptor_ok:
        issue_codes.append("hostess.issue.connectivity_probe.websocket_route_descriptor_not_generic")

    evidence_ok = (
        evidence.get("$schema") == "rusty.manifold.bridge.route_evidence.v1"
        and str(evidence.get("status") or "") in {"pass", "warn"}
        and evidence_route_id == route_id
        and {"sent", "transport_ok", "observed"}.issubset(passed_stages)
    )
    if not evidence_ok:
        issue_codes.append("hostess.issue.connectivity_probe.websocket_route_evidence_incomplete")

    command_route = (
        str(descriptor.get("route_kind") or "") == "command"
        or str(descriptor.get("plane") or "") == "control"
        or str(descriptor.get("payload_class") or "") == "command_envelope"
        or str(descriptor.get("delivery") or "") == "applied_receipt_required"
    )
    if command_route:
        issue_codes.append("hostess.issue.connectivity_probe.websocket_command_route_not_generic")

    handshake_complete = (
        "transport_ok" in passed_stages
        and any("websocket" in ref or "sec_websocket_accept" in ref for ref in transport_refs)
    )
    if not handshake_complete:
        issue_codes.append("hostess.issue.connectivity_probe.websocket_handshake_evidence_missing")

    status = "pass" if not issue_codes else "fail"
    return {
        "status": status,
        "source": source,
        "endpoint_source": source,
        "run_id": str(evidence.get("evidence_id") or route_id or "qcl079-websocket-route"),
        "path": route_id or "bridge_route.stream.websocket.ordered",
        "endpoint": route_id or "manifold-bridge-route",
        "messages_requested": messages_requested,
        "messages_received": messages_requested if status == "pass" else 0,
        "messages_acknowledged": messages_requested if status == "pass" else 0,
        "loss_percent": 0.0 if status == "pass" else 100.0,
        "round_trip_ms_p95": None,
        "payload_bytes_max": payload_bytes,
        "bounded_messages": status == "pass",
        "high_rate_json_payload": False,
        "not_command_authority": not command_route,
        "handshake_complete": handshake_complete and status == "pass",
        "issue_codes": list(dict.fromkeys(issue_codes)),
        "notes": (
            "Manifold-owned generic WebSocket stream bridge route evidence"
            if status == "pass"
            else "; ".join(value for value in [descriptor_error, evidence_error] if value)
            or "Manifold WebSocket route/evidence did not satisfy QCL-079"
        ),
        "bridge_route": {
            "descriptor_path": route_descriptor_path,
            "evidence_path": route_evidence_path,
            "route_id": route_id,
            "evidence_id": str(evidence.get("evidence_id") or ""),
            "required_stages": sorted(required_stages),
            "passed_stages": sorted(passed_stages),
            "transport_refs": sorted(transport_refs),
            "authority_owner": "rusty.manifold.transport",
        },
    }


def websocket_loopback_probe(
    *,
    run_id: str,
    bind_host: str,
    bind_port: int,
    path: str,
    message_count: int,
    payload_bytes: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Run a bounded local WebSocket server/client echo probe."""

    message_count = max(1, message_count)
    payload_bytes = max(8, min(payload_bytes, 4096))
    timeout_seconds = max(0.5, timeout_seconds)
    issue_codes: list[str] = []
    server_errors: list[str] = []
    server_received = 0
    server_echoed = 0
    server_ready = threading.Event()
    server_done = threading.Event()
    server_state: dict[str, Any] = {
        "endpoint": "",
        "handshake_complete": False,
    }

    def server() -> None:
        nonlocal server_received, server_echoed
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((bind_host, bind_port))
                listener.listen(1)
                listener.settimeout(timeout_seconds)
                host, port = listener.getsockname()[:2]
                server_state["endpoint"] = f"{host}:{port}"
                server_ready.set()
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(timeout_seconds)
                    headers = read_http_headers(connection)
                    key = websocket_request_key(headers)
                    if not key:
                        raise WebSocketProtocolError("missing Sec-WebSocket-Key")
                    response = websocket_accept_response(key)
                    connection.sendall(response)
                    server_state["handshake_complete"] = True
                    for _ in range(message_count):
                        opcode, payload = read_websocket_frame(connection, expect_masked=True)
                        if opcode == 8:
                            break
                        if opcode not in {1, 2}:
                            raise WebSocketProtocolError(f"unsupported opcode {opcode}")
                        if len(payload) > payload_bytes:
                            raise WebSocketProtocolError("payload exceeded configured bound")
                        server_received += 1
                        write_websocket_frame(connection, payload, opcode=opcode, mask=False)
                        server_echoed += 1
        except Exception as exc:  # keep probe evidence inspectable
            server_errors.append(f"{type(exc).__name__}: {exc}")
        finally:
            server_done.set()

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    if not server_ready.wait(timeout_seconds):
        return websocket_probe_result(
            status="blocked",
            run_id=run_id,
            path=path,
            endpoint="",
            messages_requested=message_count,
            messages_received=0,
            messages_acknowledged=0,
            payload_bytes_max=payload_bytes,
            round_trips_ms=[],
            handshake_complete=False,
            issue_codes=["hostess.issue.connectivity_probe.websocket_listener_not_ready"],
            notes="host-loopback WebSocket listener did not become ready",
        )

    endpoint = str(server_state.get("endpoint") or "")
    port = int(endpoint.rsplit(":", 1)[-1])
    connect_host = "127.0.0.1" if bind_host in {"", "0.0.0.0"} else bind_host
    acknowledged = 0
    round_trips_ms: list[float] = []
    client_issue_codes: list[str] = []
    try:
        with socket.create_connection((connect_host, port), timeout=timeout_seconds) as client:
            client.settimeout(timeout_seconds)
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            request = websocket_handshake_request(path, f"{connect_host}:{port}", key)
            client.sendall(request)
            response = read_http_headers(client)
            if " 101 " not in response.split("\r\n", 1)[0]:
                raise WebSocketProtocolError("server did not return HTTP 101")
            expected_accept = websocket_accept_key(key)
            if expected_accept not in response:
                raise WebSocketProtocolError("server returned invalid Sec-WebSocket-Accept")
            for sequence in range(message_count):
                payload = bounded_payload(run_id, sequence, payload_bytes)
                started = time.perf_counter()
                write_websocket_frame(client, payload, opcode=1, mask=True)
                opcode, echoed = read_websocket_frame(client, expect_masked=False)
                if opcode != 1 or echoed != payload:
                    raise WebSocketProtocolError("echo payload mismatch")
                round_trips_ms.append((time.perf_counter() - started) * 1000.0)
                acknowledged += 1
            try:
                write_websocket_frame(client, b"", opcode=8, mask=True)
            except OSError:
                pass
    except Exception as exc:
        client_issue_codes.append("hostess.issue.connectivity_probe.websocket_exchange_failed")
        server_errors.append(f"{type(exc).__name__}: {exc}")

    server_done.wait(timeout_seconds)
    all_issue_codes = list(dict.fromkeys(client_issue_codes + websocket_issue_codes(server_errors)))
    status = "pass" if acknowledged == message_count and not all_issue_codes else "fail"
    return websocket_probe_result(
        status=status,
        run_id=run_id,
        path=path,
        endpoint=endpoint,
        messages_requested=message_count,
        messages_received=server_received,
        messages_acknowledged=acknowledged,
        payload_bytes_max=payload_bytes,
        round_trips_ms=round_trips_ms,
        handshake_complete=bool(server_state.get("handshake_complete")),
        issue_codes=all_issue_codes,
        notes="host-loopback bounded WebSocket handshake and echo probe",
    )


def websocket_probe_result(
    *,
    status: str,
    run_id: str,
    path: str,
    endpoint: str,
    messages_requested: int,
    messages_received: int,
    messages_acknowledged: int,
    payload_bytes_max: int,
    round_trips_ms: list[float],
    handshake_complete: bool,
    issue_codes: list[str],
    notes: str,
) -> dict[str, Any]:
    loss_percent = 100.0
    if messages_requested > 0:
        loss_percent = round_float(
            ((messages_requested - messages_acknowledged) / messages_requested) * 100.0,
            3,
        ) or 0.0
    return {
        "status": status,
        "source": "host-loopback",
        "endpoint_source": WEBSOCKET_ENDPOINT_SOURCE_HOST_LOOPBACK,
        "run_id": run_id,
        "path": path,
        "endpoint": endpoint,
        "messages_requested": messages_requested,
        "messages_received": messages_received,
        "messages_acknowledged": messages_acknowledged,
        "loss_percent": loss_percent,
        "round_trip_ms_p95": round_float(percentile(round_trips_ms, 95)),
        "payload_bytes_max": payload_bytes_max,
        "bounded_messages": messages_acknowledged == messages_requested,
        "high_rate_json_payload": False,
        "handshake_complete": handshake_complete,
        "issue_codes": issue_codes,
        "notes": notes,
    }


def qcl079_fixture_body(*, status: str, handshake_blocked: bool = False) -> dict[str, Any]:
    blocked = status == "blocked" or handshake_blocked
    probe = {
        "status": "blocked" if blocked else "pass",
        "source": "host-loopback",
        "endpoint_source": WEBSOCKET_ENDPOINT_SOURCE_HOST_LOOPBACK,
        "run_id": "fixture-qcl079-websocket",
        "path": "/qcl079",
        "endpoint": "127.0.0.1:18785",
        "messages_requested": 16,
        "messages_received": 0 if blocked else 16,
        "messages_acknowledged": 0 if blocked else 16,
        "loss_percent": 100.0 if blocked else 0.0,
        "round_trip_ms_p95": None if blocked else 4,
        "payload_bytes_max": 96,
        "bounded_messages": not blocked,
        "high_rate_json_payload": False,
        "handshake_complete": not blocked,
        "issue_codes": (
            ["hostess.issue.connectivity_probe.websocket_handshake_failed"]
            if blocked
            else []
        ),
        "notes": "fixture generic WebSocket loopback",
    }
    return qcl079_body_from_probe(probe, source="host-loopback")


def qcl079_body_from_probe(probe: dict[str, Any], *, source: str) -> dict[str, Any]:
    issue_codes = [str(code) for code in probe.get("issue_codes", []) or []]
    source = str(source or probe.get("source") or "host-loopback")
    endpoint_source = str(probe.get("endpoint_source") or source)
    handshake_ok = probe.get("handshake_complete") is True and not issue_codes
    exchange_ok = int_value(probe.get("messages_acknowledged")) == int_value(probe.get("messages_requested"))
    bounds_ok = probe.get("bounded_messages") is True and int_value(probe.get("payload_bytes_max")) is not None
    command_guard_ok = probe.get("not_command_authority", True) is True
    media_guard_ok = probe.get("high_rate_json_payload") is not True
    checks = [
        check_row(
            "protocol.websocket_handshake",
            "pass" if handshake_ok else "blocked",
            "WebSocket HTTP upgrade and Sec-WebSocket-Accept validated"
            if handshake_ok
            else "WebSocket handshake did not complete",
            observed={
                "endpoint": probe.get("endpoint"),
                "path": probe.get("path"),
                "endpoint_source": endpoint_source,
            },
            issue_codes=issue_codes if not handshake_ok else [],
        ),
        check_row(
            "protocol.websocket_payload_exchange",
            "pass" if exchange_ok else "fail",
            "bounded WebSocket text messages echoed"
            if exchange_ok
            else "WebSocket payload exchange did not complete",
            observed={
                "messages_requested": probe.get("messages_requested"),
                "messages_received": probe.get("messages_received"),
                "messages_acknowledged": probe.get("messages_acknowledged"),
                "loss_percent": probe.get("loss_percent"),
                "round_trip_ms_p95": probe.get("round_trip_ms_p95"),
            },
            issue_codes=issue_codes if not exchange_ok else [],
        ),
        check_row(
            "protocol.websocket_message_bounds",
            "pass" if bounds_ok else "blocked",
            "WebSocket probe used bounded message count and payload size"
            if bounds_ok
            else "WebSocket message bounds were not proven",
            observed={
                "messages_requested": probe.get("messages_requested"),
                "payload_bytes_max": probe.get("payload_bytes_max"),
            },
        ),
        check_row(
            "protocol.websocket_not_command_authority",
            "pass" if command_guard_ok else "fail",
            "generic WebSocket evidence is separate from Manifold command acceptance"
            if command_guard_ok
            else "QCL-079 rejected a command/control WebSocket route",
            observed={
                "qcl000_command_authority": "not_claimed",
                "qcl079_generic_protocol_fit": command_guard_ok,
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.websocket_command_route_not_generic"]
                if not command_guard_ok
                else []
            ),
        ),
        check_row(
            "protocol.websocket_high_rate_media_guard",
            "pass" if media_guard_ok else "fail",
            "generic WebSocket probe does not carry high-rate media payloads"
            if media_guard_ok
            else "WebSocket probe attempted high-rate media payloads",
            observed={
                "high_rate_media_payload_allowed": False,
                "high_rate_json_payload": probe.get("high_rate_json_payload"),
            },
            issue_codes=(
                ["hostess.issue.connectivity_probe.websocket_high_rate_media_payload"]
                if not media_guard_ok
                else []
            ),
        ),
    ]
    status = qcl079_status(checks)
    promotion_allowed = (
        status == "pass"
        and endpoint_source
        in {WEBSOCKET_ENDPOINT_SOURCE_BROKER, WEBSOCKET_ENDPOINT_SOURCE_QUEST_RUNTIME}
    )
    return {
        "status": status,
        "classification": "protocol_fit_candidate",
        "topology": {
            "owner": "host_local" if endpoint_source == "host-loopback" else "runtime_or_broker",
            "network_provider": "loopback" if endpoint_source == "host-loopback" else "declared_by_source",
            "endpoint_direction": "generic_websocket_message_exchange",
            "requires_existing_wifi": False,
            "requires_adb": False,
            "requires_pairing": False,
            "requires_termux": False,
            "experimental": endpoint_source != "host-loopback",
        },
        "transport": {
            "family": "websocket",
            "route": "qcl079_generic_websocket_echo",
            "local_endpoint": probe.get("endpoint") or "host-loopback",
            "remote_endpoint": probe.get("endpoint") or "host-loopback",
            "protocol_role": "generic_websocket_protocol_fit",
            "payload_class": "bounded_text_messages",
            "endpoint_source": endpoint_source,
            "product_data_plane": endpoint_source != "host-loopback",
            "bridge_route": object_value(probe.get("bridge_route")),
        },
        "device": {
            "serial_redacted": True,
            "model": "fixture" if endpoint_source == "host-loopback" else "not_checked",
            "wifi_ipv4": "",
            "foreground_package": "not_checked",
            "adb_state": "not_applicable",
        },
        "host": {
            "os": "windows",
            "toolchain_profile": "hostessctl.connectivity_probe.qcl079.websocket",
        },
        "checks": checks,
        "measurements": {
            **empty_measurements(),
            "websocket_messages_requested": probe.get("messages_requested"),
            "websocket_messages_received": probe.get("messages_acknowledged"),
            "websocket_loss_percent": probe.get("loss_percent"),
            "websocket_echo_ms": probe.get("round_trip_ms_p95"),
            "websocket_payload_bytes_max": probe.get("payload_bytes_max"),
        },
        "issues": [
            issue_row(
                str(code),
                "error" if status in {"fail", "blocked"} else "warning",
                "generic WebSocket probe reported invalid handshake or payload exchange",
            )
            for code in issue_codes
        ],
        "promotion": {
            "allowed": promotion_allowed,
            "target": "quest.device_link generic WebSocket capability descriptor",
            "reason": (
                "generic WebSocket evidence is broker-owned or Quest-runtime owned"
                if promotion_allowed
                else (
                    "host-loopback WebSocket proves protocol fit only; generic "
                    "WebSocket promotion needs broker-owned or Quest-runtime evidence"
                )
            ),
        },
        "websocket_bridge_route": object_value(probe.get("bridge_route")),
    }


def qcl079_status(checks: list[dict[str, Any]]) -> str:
    statuses = {str(check.get("status") or "") for check in checks}
    hard_fail_checks = {
        "protocol.websocket_not_command_authority",
        "protocol.websocket_high_rate_media_guard",
    }
    if any(
        str(check.get("name") or "") in hard_fail_checks
        and str(check.get("status") or "") == "fail"
        for check in checks
    ):
        return "fail"
    if "blocked" in statuses:
        return "blocked"
    if "fail" in statuses:
        return "fail"
    return "pass"


def websocket_handshake_request(path: str, host: str, key: str) -> bytes:
    request_path = path if path.startswith("/") else f"/{path}"
    return (
        f"GET {request_path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    ).encode("ascii")


def read_http_headers(sock: socket.socket) -> str:
    chunks: list[bytes] = []
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
        data = b"".join(chunks)
        if len(data) > 16384:
            raise WebSocketProtocolError("HTTP header too large")
    return data.decode("iso-8859-1", errors="replace")


def websocket_request_key(headers: str) -> str:
    for line in headers.splitlines():
        if line.lower().startswith("sec-websocket-key:"):
            return line.split(":", 1)[1].strip()
    return ""


def websocket_accept_response(key: str) -> bytes:
    accept = websocket_accept_key(key)
    return (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "\r\n"
    ).encode("ascii")


def websocket_accept_key(key: str) -> str:
    digest = hashlib.sha1((key + WEBSOCKET_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def write_websocket_frame(sock: socket.socket, payload: bytes, *, opcode: int, mask: bool) -> None:
    if len(payload) > 65535:
        raise WebSocketProtocolError("payload too large for bounded probe")
    first = 0x80 | (opcode & 0x0F)
    if len(payload) <= 125:
        header = bytes([first, (0x80 if mask else 0) | len(payload)])
    else:
        header = bytes([first, (0x80 if mask else 0) | 126]) + len(payload).to_bytes(2, "big")
    if mask:
        key = os.urandom(4)
        masked = bytes(byte ^ key[index % 4] for index, byte in enumerate(payload))
        sock.sendall(header + key + masked)
    else:
        sock.sendall(header + payload)


def read_websocket_frame(sock: socket.socket, *, expect_masked: bool) -> tuple[int, bytes]:
    header = recv_exact(sock, 2)
    if len(header) != 2:
        raise WebSocketProtocolError("frame header truncated")
    opcode = header[0] & 0x0F
    masked = (header[1] & 0x80) != 0
    if masked != expect_masked:
        raise WebSocketProtocolError("unexpected frame mask state")
    length = header[1] & 0x7F
    if length == 126:
        length = int.from_bytes(recv_exact(sock, 2), "big")
    elif length == 127:
        raise WebSocketProtocolError("64-bit payload length not allowed in bounded probe")
    mask_key = recv_exact(sock, 4) if masked else b""
    payload = recv_exact(sock, length)
    if len(payload) != length:
        raise WebSocketProtocolError("frame payload truncated")
    if masked:
        payload = bytes(byte ^ mask_key[index % 4] for index, byte in enumerate(payload))
    return opcode, payload


def recv_exact(sock: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def bounded_payload(run_id: str, sequence: int, payload_bytes: int) -> bytes:
    prefix = f"qcl079:{run_id}:{sequence}:".encode("utf-8")
    if len(prefix) >= payload_bytes:
        return prefix[:payload_bytes]
    return prefix + (b"x" * (payload_bytes - len(prefix)))


def websocket_issue_codes(errors: list[str]) -> list[str]:
    if not errors:
        return []
    return ["hostess.issue.connectivity_probe.websocket_exchange_failed"]


def int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def read_json_object(path: str) -> dict[str, Any]:
    parsed = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError("JSON root must be an object")
    return parsed


__all__ = [
    "DEFAULT_QCL079_WEBSOCKET_PORT",
    "live_websocket_report",
    "qcl079_fixture_body",
    "websocket_loopback_probe",
]

