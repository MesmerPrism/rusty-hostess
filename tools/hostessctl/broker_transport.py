"""Broker WebSocket transport helpers for Hostess CLI flows."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


MANIFOLD_COMMAND_SCHEMA = "rusty.manifold.command.envelope.v1"
MANIFOLD_BROKER_EVENTS_PATH = "/manifold/v1/events"


class BrokerWebSocketClient:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        path: str = MANIFOLD_BROKER_EVENTS_PATH,
        timeout: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.path = path
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {self.key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self._read_http_response()
        status_line = response.split(b"\r\n", 1)[0]
        if b" 101 " not in status_line:
            raise RuntimeError(f"broker websocket handshake failed: {status_line.decode('ascii', 'replace')}")
        expected_accept = base64.b64encode(
            hashlib.sha1((self.key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        headers = {}
        for line in response.split(b"\r\n")[1:]:
            if b":" not in line:
                continue
            name, value = line.split(b":", 1)
            headers[name.decode("ascii", "ignore").strip().lower()] = value.decode("ascii", "ignore").strip()
        if headers.get("sec-websocket-accept") != expected_accept:
            raise RuntimeError("broker websocket handshake accept header did not match")

    def close(self) -> None:
        try:
            self._send_frame(b"", opcode=0x8)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    def send_json(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        self._send_frame(data, opcode=0x1)

    def recv_json(self, *, timeout: float) -> dict[str, Any] | None:
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(timeout)
        try:
            while True:
                opcode, payload = self._recv_frame()
                if opcode == 0x1:
                    return json.loads(payload.decode("utf-8"))
                if opcode == 0x8:
                    return None
                if opcode == 0x9:
                    self._send_frame(payload, opcode=0xA)
        except socket.timeout:
            return None
        finally:
            self.sock.settimeout(old_timeout)

    def _read_http_response(self) -> bytes:
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > 65536:
                raise RuntimeError("broker websocket handshake response exceeded 64 KiB")
        return bytes(data)

    def _send_frame(self, payload: bytes, *, opcode: int) -> None:
        header = bytearray()
        header.append(0x80 | (opcode & 0x0F))
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length <= 0xFFFF:
            header.append(0x80 | 126)
            header.extend(length.to_bytes(2, "big"))
        else:
            header.append(0x80 | 127)
            header.extend(length.to_bytes(8, "big"))
        mask = os.urandom(4)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def _recv_frame(self) -> tuple[int, bytes]:
        first = self._read_exact(2)
        opcode = first[0] & 0x0F
        masked = bool(first[1] & 0x80)
        length = first[1] & 0x7F
        if length == 126:
            length = int.from_bytes(self._read_exact(2), "big")
        elif length == 127:
            length = int.from_bytes(self._read_exact(8), "big")
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length) if length else b""
        if masked:
            payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        return opcode, payload

    def _read_exact(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise RuntimeError("broker websocket closed while reading")
            data.extend(chunk)
        return bytes(data)


def broker_command_message(
    command: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
    client_id: str = "hostessctl.record_values",
    app_package: str = "rusty-hostess",
) -> dict[str, Any]:
    return {
        "type": "command",
        "schema": MANIFOLD_COMMAND_SCHEMA,
        "request_id": request_id or f"hostess-record-values-{command.replace('.', '-')}",
        "command": command,
        "params": params or {},
        "client_id": client_id,
        "app_package": app_package,
    }


def broker_ack_accepted(reply: dict[str, Any]) -> bool:
    if "accepted" in reply:
        return bool(reply.get("accepted"))
    return bool(reply.get("ok", reply.get("success", True)))


def connect_broker_websocket_with_retry(
    host: str,
    port: int,
    provider_actions: list[dict[str, Any]],
    errors: list[str],
) -> BrokerWebSocketClient:
    deadline = time.monotonic() + 15.0
    attempt = 0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        attempt += 1
        try:
            client = BrokerWebSocketClient(host, port, timeout=2.0)
            provider_actions.append(
                {
                    "action": "connect-broker-websocket",
                    "attempt": attempt,
                    "status": "pass",
                    "host": host,
                    "port": port,
                }
            )
            return client
        except OSError as ex:
            last_error = ex
            time.sleep(0.25)
        except RuntimeError as ex:
            last_error = ex
            time.sleep(0.25)
    message = f"broker websocket connection failed: {last_error}"
    errors.append(message)
    raise RuntimeError(message)


def accept_broker_stream_event(
    event: dict[str, Any],
    stream_rows: dict[str, dict[str, Any]],
    events_jsonl: Path,
    *,
    events_file: Any | None = None,
) -> None:
    event = with_transport_event_aliases(event)
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    stream = str(event.get("stream") or event.get("stream_id") or payload.get("stream_id") or "")
    if stream not in stream_rows:
        return
    now = datetime.now(UTC).isoformat()
    row = stream_rows[stream]
    row["event_count"] = int(row["event_count"]) + 1
    row["sample_count"] = int(row["sample_count"]) + 1
    if row["first_event_at_utc"] is None:
        row["first_event_at_utc"] = now
    row["last_event_at_utc"] = now
    line = json.dumps(event, separators=(",", ":"), sort_keys=True)
    if events_file is not None:
        events_file.write(line + "\n")
    else:
        with events_jsonl.open("a", encoding="utf-8") as file:
            file.write(line + "\n")


def with_transport_event_aliases(event: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(event)
    payload = normalized.get("payload")
    if isinstance(payload, dict):
        payload = dict(payload)
        normalized["payload"] = payload
    else:
        payload = {}

    for old_key, new_key in (
        ("broker_time_unix_ns", "transport_time_unix_ns"),
        ("broker_receive_time_unix_ns", "transport_receive_time_unix_ns"),
    ):
        if new_key not in normalized and old_key in normalized:
            normalized[new_key] = normalized[old_key]
        if new_key not in payload and old_key in payload:
            payload[new_key] = payload[old_key]

    return normalized
