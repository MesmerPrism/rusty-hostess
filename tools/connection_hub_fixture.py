#!/usr/bin/env python3
"""Deterministic loopback-only Rusty Connection Hub fixture.

This is a Hostess conformance oracle, not a product server or reusable
admission/command authority.  It binds only to 127.0.0.1 on an ephemeral port.
"""

from __future__ import annotations

import base64
import hashlib
import json
import socket
import struct
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

try:
    from tools.connection_hub_cli import (
        AUTHENTICATE_SCHEMA,
        AUTHENTICATION_RECEIPT_SCHEMA,
        COMMAND_SCHEMA,
        EVENT_SCHEMAS,
        PAIR_RECEIPT_SCHEMA,
        PAIR_REQUEST_SCHEMA,
        REVOKE_RECEIPT_SCHEMA,
        REVOKE_REQUEST_SCHEMA,
        STATUS_SCHEMA,
        canonical_json,
        validate_args,
    )
except ModuleNotFoundError:
    from connection_hub_cli import (
        AUTHENTICATE_SCHEMA,
        AUTHENTICATION_RECEIPT_SCHEMA,
        COMMAND_SCHEMA,
        EVENT_SCHEMAS,
        PAIR_RECEIPT_SCHEMA,
        PAIR_REQUEST_SCHEMA,
        REVOKE_RECEIPT_SCHEMA,
        REVOKE_REQUEST_SCHEMA,
        STATUS_SCHEMA,
        canonical_json,
        validate_args,
    )


def media_surface() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "surface_id": "media.control",
        "display_label": "Media control",
        "description": "Low-rate playback control only.",
        "provider_package": "fixture.media",
        "provider_signer_sha256": "1" * 64,
        "commands": [
            {"command": "play", "display_label": "Play"},
            {"command": "pause", "display_label": "Pause"},
        ],
        "state": {"playing": False},
        "state_revision": 1,
        "_fixture_provider_id": "media.provider",
    }


def diagnostic_surface() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "surface_id": "diagnostics.capture",
        "display_label": "Diagnostics",
        "description": "Bounded low-rate diagnostic requests.",
        "provider_package": "fixture.diagnostics",
        "provider_signer_sha256": "2" * 64,
        "commands": [{"command": "snapshot", "display_label": "Capture snapshot"}],
        "state": {"ready": True},
        "state_revision": 1,
        "_fixture_provider_id": "diagnostics.provider",
    }


def _public_surface(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if not key.startswith("_fixture_")}


def _frame(opcode: int, payload: bytes) -> bytes:
    if len(payload) < 126:
        return bytes((0x80 | opcode, len(payload))) + payload
    return bytes((0x80 | opcode, 126)) + struct.pack("!H", len(payload)) + payload


def _read_exact(sock: socket.socket, length: int) -> bytes:
    value = bytearray()
    while len(value) < length:
        chunk = sock.recv(length - len(value))
        if not chunk:
            raise EOFError
        value.extend(chunk)
    return bytes(value)


def _read_client_frame(sock: socket.socket) -> tuple[int, bytes]:
    first, second = _read_exact(sock, 2)
    opcode = first & 0x0F
    if not second & 0x80:
        raise ValueError("fixture_requires_masked_client_frames")
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", _read_exact(sock, 2))[0]
    elif length == 127 or length > 4096:
        raise ValueError("fixture_client_frame_out_of_bounds")
    mask = _read_exact(sock, 4)
    payload = _read_exact(sock, length)
    return opcode, bytes(value ^ mask[index % 4] for index, value in enumerate(payload))


@dataclass(eq=False)
class _FixtureSocket:
    sock: socket.socket
    epoch: int
    write_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, value: dict[str, Any]) -> None:
        with self.write_lock:
            self.sock.sendall(_frame(0x1, canonical_json(value)))

    def close(self, code: int = 4001, reason: str = "session_revoked") -> None:
        with self.write_lock:
            try:
                self.sock.sendall(_frame(0x8, struct.pack("!H", code) + reason.encode("utf-8")))
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


class _FixtureState:
    pairing_code = "246810"
    controller_identity_sha256 = "a" * 64
    session = "fixture-session-token-000000000001"

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.session_active = False
        self.pair_count = 0
        self.transport_counter = 0
        self.surface_revision = 0
        self.surfaces: dict[str, dict[str, Any]] = {}
        self.connections: set[_FixtureSocket] = set()
        self.request_ids: set[str] = set()
        self.dispatch_log: list[tuple[str, str, str]] = []
        self.high_rate_payload_count = 0
        self.upgrade_paths: list[str] = []

    def transport_fields(self) -> dict[str, Any]:
        return {
            "transport_classification": "loopback_fixture",
            "confidentiality": "none",
            "production_eligible": False,
        }

    def status(self) -> dict[str, Any]:
        with self.lock:
            return {
                "$schema": STATUS_SCHEMA,
                "listener_enabled": True,
                "desired_connection_state": "running",
                "transport_epoch": self.transport_counter,
                "surface_revision": self.surface_revision,
                "active_session_count": 1 if self.session_active else 0,
                "pairing_required": True,
                "surfaces": [_public_surface(self.surfaces[key]) for key in sorted(self.surfaces)],
                **self.transport_fields(),
            }

    def pair(self, request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        expected_keys = {"$schema", "pairing_code", "controller_identity_sha256"}
        accepted = (
            set(request) == expected_keys
            and request.get("$schema") == PAIR_REQUEST_SCHEMA
            and request.get("pairing_code") == self.pairing_code
            and request.get("controller_identity_sha256") == self.controller_identity_sha256
        )
        with self.lock:
            if accepted:
                self.session_active = True
                self.pair_count += 1
            receipt = {
                "$schema": PAIR_RECEIPT_SCHEMA,
                "accepted": accepted,
                "status": "paired" if accepted else "pairing_rejected",
                "expires_at_utc": "2099-01-01T00:00:00Z",
                "transport_epoch": self.transport_counter,
                **self.transport_fields(),
            }
            if accepted:
                receipt["session"] = self.session
            return (200 if accepted else 403), receipt

    def authenticate(
        self, sock: socket.socket, request: dict[str, Any]
    ) -> tuple[_FixtureSocket | None, dict[str, Any], list[_FixtureSocket]]:
        expected = {
            "$schema": AUTHENTICATE_SCHEMA,
            "type": "authenticate",
            "session": self.session,
        }
        with self.lock:
            accepted = self.session_active and request == expected
            if not accepted:
                return (
                    None,
                    {
                        "$schema": AUTHENTICATION_RECEIPT_SCHEMA,
                        "type": "authentication_receipt",
                        "accepted": False,
                        "status": "authentication_rejected",
                        "transport_epoch": self.transport_counter,
                        "confidentiality": "none",
                        "production_eligible": False,
                    },
                    [],
                )
            replaced = list(self.connections)
            self.transport_counter += 1
            connection = _FixtureSocket(sock, self.transport_counter)
            self.connections.add(connection)
            receipt = {
                "$schema": AUTHENTICATION_RECEIPT_SCHEMA,
                "type": "authentication_receipt",
                "accepted": True,
                "status": "authenticated",
                "transport_epoch": connection.epoch,
                "confidentiality": "none",
                "production_eligible": False,
            }
        return connection, receipt, replaced

    def snapshot(self, connection: _FixtureSocket) -> dict[str, Any]:
        with self.lock:
            return self.event(
                "surface_snapshot",
                connection.epoch,
                surfaces=[_public_surface(self.surfaces[key]) for key in sorted(self.surfaces)],
            )

    def unregister(self, connection: _FixtureSocket) -> None:
        with self.lock:
            self.connections.discard(connection)

    def event(self, event_type: str, epoch: int, **fields: Any) -> dict[str, Any]:
        return {
            "$schema": EVENT_SCHEMAS[event_type],
            "type": event_type,
            "transport_epoch": epoch,
            "surface_revision": self.surface_revision,
            **fields,
        }

    def broadcast(self, event_type: str, **fields: Any) -> None:
        with self.lock:
            connections = list(self.connections)
            events = [(item, self.event(event_type, item.epoch, **fields)) for item in connections]
        for connection, event in events:
            connection.send(event)

    def add_surface(self, descriptor: dict[str, Any]) -> None:
        surface_id = descriptor["surface_id"]
        with self.lock:
            self.surface_revision += 1
            self.surfaces[surface_id] = descriptor
        self.broadcast("surface_available", surface=_public_surface(descriptor))

    def remove_surface(self, surface_id: str) -> None:
        with self.lock:
            if surface_id not in self.surfaces:
                raise ValueError("fixture_surface_missing")
            del self.surfaces[surface_id]
            self.surface_revision += 1
        self.broadcast("surface_removed", surface_id=surface_id, reason="provider_unregistered")

    def command(self, connection: _FixtureSocket, request: dict[str, Any]) -> dict[str, Any]:
        exact_keys = {"$schema", "type", "request_id", "surface_id", "command", "args"}
        request_id = request.get("request_id")
        surface_id = request.get("surface_id")
        command = request.get("command")
        reason: str | None = None
        with self.lock:
            if (
                set(request) != exact_keys
                or request.get("$schema") != COMMAND_SCHEMA
                or request.get("type") != "surface.command"
                or not isinstance(request_id, str)
            ):
                reason = "request_invalid"
            elif request_id in self.request_ids:
                reason = "request_replay"
            else:
                self.request_ids.add(request_id)
                try:
                    validate_args(request.get("args"))
                except (ValueError, TypeError):
                    reason = "args_invalid"
                descriptor = self.surfaces.get(str(surface_id))
                if reason is None and descriptor is None:
                    reason = "unknown_surface"
                registered = (
                    {item["command"] for item in descriptor["commands"]}
                    if descriptor is not None
                    else set()
                )
                if reason is None and command not in registered:
                    reason = "unknown_command"
                if reason is None:
                    self.dispatch_log.append(
                        (descriptor["_fixture_provider_id"], str(surface_id), str(command))
                    )
            return self.event(
                "command_receipt",
                connection.epoch,
                request_id=request_id,
                surface_id=surface_id,
                command=command,
                accepted=reason is None,
                status="accepted" if reason is None else reason,
                proves_application_effect=False,
            )

    def revoke(self, request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        expected = {
            "$schema": REVOKE_REQUEST_SCHEMA,
            "session": self.session,
            "reason": "user_request",
        }
        with self.lock:
            applied = self.session_active and request == expected
            if applied:
                self.session_active = False
            connections = list(self.connections) if applied else []
            receipt = {
                "$schema": REVOKE_RECEIPT_SCHEMA,
                "applied": applied,
                "status": "revoked" if applied else "revoke_rejected",
                "transport_epoch": self.transport_counter,
                **self.transport_fields(),
            }
        if applied:
            threading.Thread(
                target=self._close_after_reply,
                args=(connections,),
                daemon=True,
            ).start()
        return (200 if applied else 403), receipt

    @staticmethod
    def _close_after_reply(connections: list[_FixtureSocket]) -> None:
        threading.Event().wait(0.05)
        for connection in connections:
            connection.close()


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, state: _FixtureState) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.state = state


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: _Server

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = canonical_json(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _request_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("content_length_invalid") from error
        if length <= 0 or length > 4096:
            raise ValueError("request_body_out_of_bounds")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("request_body_must_be_object")
        return value

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/v1/status" and not parsed.query:
            self._json(200, self.server.state.status())
            return
        if parsed.path != "/v1/socket" or parsed.query:
            self._json(404, {"status": "not_found"})
            return
        if self.headers.get("Upgrade", "").lower() != "websocket":
            self._json(400, {"status": "upgrade_required"})
            return
        with self.server.state.lock:
            self.server.state.upgrade_paths.append(self.path)
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self._json(400, {"status": "websocket_key_missing"})
            return
        accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.wfile.flush()
        connection: _FixtureSocket | None = None
        try:
            opcode, payload = _read_client_frame(self.connection)
            auth_request = json.loads(payload.decode("utf-8")) if opcode == 0x1 else {}
            if not isinstance(auth_request, dict):
                auth_request = {}
            connection, auth_receipt, replaced = self.server.state.authenticate(
                self.connection, auth_request
            )
            if connection is None:
                self.connection.sendall(_frame(0x1, canonical_json(auth_receipt)))
                self.connection.sendall(
                    _frame(0x8, struct.pack("!H", 4003) + b"authentication_rejected")
                )
                return
            connection.send(auth_receipt)
            connection.send(self.server.state.snapshot(connection))
            for previous in replaced:
                previous.close(4002, "transport_replaced")
            while self.server.state.session_active:
                opcode, payload = _read_client_frame(self.connection)
                if opcode == 0x8:
                    break
                if opcode == 0x9:
                    with connection.write_lock:
                        self.connection.sendall(_frame(0xA, payload))
                    continue
                if opcode != 0x1:
                    continue
                request = json.loads(payload.decode("utf-8"))
                if not isinstance(request, dict):
                    raise ValueError("command_must_be_object")
                connection.send(self.server.state.command(connection, request))
        except (EOFError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            pass
        finally:
            if connection is not None:
                self.server.state.unregister(connection)
            self.close_connection = True

    def do_POST(self) -> None:
        try:
            request = self._request_json()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"status": "request_invalid"})
            return
        if self.path == "/v1/pair":
            status, payload = self.server.state.pair(request)
        elif self.path == "/v1/revoke":
            status, payload = self.server.state.revoke(request)
        else:
            status, payload = 404, {"status": "not_found"}
        self._json(status, payload)


class ConnectionHubFixture:
    """Context-managed deterministic loopback fixture."""

    def __init__(self) -> None:
        self._state = _FixtureState()
        self._server: _Server | None = None
        self._thread: threading.Thread | None = None

    @property
    def origin(self) -> str:
        if self._server is None:
            raise RuntimeError("fixture_not_started")
        return f"http://127.0.0.1:{self._server.server_port}"

    @property
    def pairing_code(self) -> str:
        return self._state.pairing_code

    @property
    def controller_identity_sha256(self) -> str:
        return self._state.controller_identity_sha256

    @property
    def pair_count(self) -> int:
        return self._state.pair_count

    @property
    def dispatch_log(self) -> list[tuple[str, str, str]]:
        return list(self._state.dispatch_log)

    @property
    def high_rate_payload_count(self) -> int:
        return self._state.high_rate_payload_count

    @property
    def upgrade_paths(self) -> list[str]:
        return list(self._state.upgrade_paths)

    def add_surface(self, descriptor: dict[str, Any]) -> None:
        self._state.add_surface(descriptor)

    def remove_surface(self, surface_id: str) -> None:
        self._state.remove_surface(surface_id)

    def __enter__(self) -> "ConnectionHubFixture":
        self._server = _Server(self._state)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
