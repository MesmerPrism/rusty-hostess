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
        AUTHENTICATE_SCHEMA_V2,
        AUTHENTICATION_RECEIPT_SCHEMA_V2,
        COMMAND_SCHEMA,
        COMMAND_SCHEMA_V2,
        COMMAND_RECEIPT_SCHEMA_V2,
        EVENT_SCHEMAS,
        KEEPALIVE_RECEIPT_SCHEMA_V2,
        KEEPALIVE_SCHEMA_V2,
        PAIR_RECEIPT_SCHEMA,
        PAIR_REQUEST_SCHEMA,
        REVOKE_RECEIPT_SCHEMA,
        REVOKE_REQUEST_SCHEMA,
        STATUS_SCHEMA,
        PROTOCOL_ERROR_SCHEMA_V2,
        PROTOCOL_ID_V1,
        PROTOCOL_ID_V2,
        canonical_json,
        validate_args,
    )
except ModuleNotFoundError:
    from connection_hub_cli import (
        AUTHENTICATE_SCHEMA,
        AUTHENTICATION_RECEIPT_SCHEMA,
        AUTHENTICATE_SCHEMA_V2,
        AUTHENTICATION_RECEIPT_SCHEMA_V2,
        COMMAND_SCHEMA,
        COMMAND_SCHEMA_V2,
        COMMAND_RECEIPT_SCHEMA_V2,
        EVENT_SCHEMAS,
        KEEPALIVE_RECEIPT_SCHEMA_V2,
        KEEPALIVE_SCHEMA_V2,
        PAIR_RECEIPT_SCHEMA,
        PAIR_REQUEST_SCHEMA,
        REVOKE_RECEIPT_SCHEMA,
        REVOKE_REQUEST_SCHEMA,
        STATUS_SCHEMA,
        PROTOCOL_ERROR_SCHEMA_V2,
        PROTOCOL_ID_V1,
        PROTOCOL_ID_V2,
        canonical_json,
        validate_args,
    )


def media_surface() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "surface_id": "media.control",
        "display_label": "Media control",
        "description": "Low-rate playback control only.",
        "surface_contract_sha256": "sha256:" + "1" * 64,
        "provider_package": "fixture.media",
        "provider_signer_sha256": "1" * 64,
        "commands": [
            {
                "command": "play",
                "display_label": "Play",
                "required_controller_capability": "capability.media.play",
            },
            {
                "command": "pause",
                "display_label": "Pause",
                "required_controller_capability": "capability.media.pause",
            },
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
        "surface_contract_sha256": "sha256:" + "2" * 64,
        "provider_package": "fixture.diagnostics",
        "provider_signer_sha256": "2" * 64,
        "commands": [
            {
                "command": "snapshot",
                "display_label": "Capture snapshot",
                "required_controller_capability": "capability.diagnostics.snapshot",
            }
        ],
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
    protocol_id: str
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
    listener_instance_id = "00112233445566778899aabbccddeeff"

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.session_active = False
        self.pair_count = 0
        self.transport_counter = 0
        self.surface_revision = 0
        self.surfaces: dict[str, dict[str, Any]] = {}
        self.connections: set[_FixtureSocket] = set()
        self.request_ids: set[str] = set()
        self.next_external_request_sequence = 1
        self.latest_external_request_sha256: str | None = None
        self.authority_epoch = 1
        self.restart_count = 0
        self.rollover_count = 0
        self.accepted_external_request_bytes: list[bytes] = []
        self.keepalive_count = 0
        self.authenticated_snapshot_count = 0
        self.pre_keepalive_snapshot_count = 0
        self.drop_next_sequenced_receipt = False
        self.dispatch_log: list[tuple[str, str, str]] = []
        self.provider_results: dict[tuple[str, str], tuple[bool, str]] = {}
        self.silent_auth_rejection = False
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
                "pairing_available": not self.session_active,
                "status": "controller_paired" if self.session_active else "awaiting_pairing",
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
                if self.transport_counter < 1:
                    self.transport_counter = 1
            receipt = {
                "$schema": PAIR_RECEIPT_SCHEMA,
                "type": "pair_receipt",
                "accepted": accepted,
                "status": "paired" if accepted else "pairing_rejected",
                "transport_epoch": self.transport_counter,
                "listener_instance_id": self.listener_instance_id,
                "surface_revision": self.surface_revision,
                **self.transport_fields(),
            }
            if accepted:
                receipt["session"] = self.session
                receipt["expires_at_utc"] = "2099-01-01T00:00:00Z"
                receipt["authority_receipt"] = {}
            return (200 if accepted else 403), receipt

    def authenticate(
        self, sock: socket.socket, request: dict[str, Any], raw_request: bytes
    ) -> tuple[_FixtureSocket | None, dict[str, Any], list[_FixtureSocket]]:
        protocol_id = (
            PROTOCOL_ID_V2
            if request.get("$schema") == AUTHENTICATE_SCHEMA_V2
            else PROTOCOL_ID_V1
        )
        expected = {
            "$schema": (
                AUTHENTICATE_SCHEMA_V2
                if protocol_id == PROTOCOL_ID_V2
                else AUTHENTICATE_SCHEMA
            ),
            "type": "authenticate",
            "session": self.session,
        }
        with self.lock:
            accepted = (
                self.session_active
                and request == expected
                and (
                    protocol_id == PROTOCOL_ID_V1
                    or raw_request == canonical_json(request)
                )
            )
            if not accepted:
                return (
                    None,
                    {
                        "$schema": (
                            AUTHENTICATION_RECEIPT_SCHEMA_V2
                            if protocol_id == PROTOCOL_ID_V2
                            else AUTHENTICATION_RECEIPT_SCHEMA
                        ),
                        "type": "authentication_receipt",
                        "accepted": False,
                        "status": "authentication_rejected",
                        "transport_epoch": self.transport_counter,
                        **(
                            {
                                "next_external_request_sequence": self.next_external_request_sequence,
                                "expires_at_utc": "2099-01-01T00:00:00Z",
                            }
                            if protocol_id == PROTOCOL_ID_V2
                            else {}
                        ),
                        "confidentiality": "none",
                        "production_eligible": False,
                    },
                    [],
                )
            replaced = list(self.connections)
            self.transport_counter += 1
            connection = _FixtureSocket(sock, self.transport_counter, protocol_id)
            self.connections.add(connection)
            receipt = {
                "$schema": (
                    AUTHENTICATION_RECEIPT_SCHEMA_V2
                    if protocol_id == PROTOCOL_ID_V2
                    else AUTHENTICATION_RECEIPT_SCHEMA
                ),
                "type": "authentication_receipt",
                "accepted": True,
                "status": "authenticated",
                "transport_epoch": connection.epoch,
                **(
                    {
                        "next_external_request_sequence": self.next_external_request_sequence,
                        "expires_at_utc": "2099-01-01T00:00:00Z",
                    }
                    if protocol_id == PROTOCOL_ID_V2
                    else {}
                ),
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

    def event(
        self,
        event_type: str,
        epoch: int,
        *,
        protocol_id: str = PROTOCOL_ID_V1,
        **fields: Any,
    ) -> dict[str, Any]:
        schema = EVENT_SCHEMAS.get(event_type)
        if protocol_id == PROTOCOL_ID_V2:
            schema = {
                "command_receipt": COMMAND_RECEIPT_SCHEMA_V2,
                "keepalive_receipt": KEEPALIVE_RECEIPT_SCHEMA_V2,
                "protocol_error": PROTOCOL_ERROR_SCHEMA_V2,
            }.get(event_type, schema)
        if schema is None:
            raise ValueError("fixture_event_schema_missing")
        return {
            "$schema": schema,
            "type": event_type,
            "transport_epoch": epoch,
            "listener_instance_id": self.listener_instance_id,
            "surface_revision": self.surface_revision,
            **self.transport_fields(),
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

    def protocol_error(
        self, connection: _FixtureSocket, status: str
    ) -> dict[str, Any]:
        return self.event(
            "protocol_error",
            connection.epoch,
            protocol_id=PROTOCOL_ID_V2,
            next_external_request_sequence=self.next_external_request_sequence,
            status=status,
        )

    def command(
        self,
        connection: _FixtureSocket,
        request: dict[str, Any],
        raw_request: bytes,
    ) -> tuple[dict[str, Any], bool]:
        v2 = connection.protocol_id == PROTOCOL_ID_V2
        exact_keys = {
            "$schema",
            "type",
            "request_id",
            "surface_id",
            "command",
            "args",
            *({"request_sequence"} if v2 else set()),
        }
        request_id = request.get("request_id")
        surface_id = request.get("surface_id")
        command = request.get("command")
        request_sequence = request.get("request_sequence") if v2 else None
        reason: str | None = None
        with self.lock:
            if (
                set(request) != exact_keys
                or request.get("$schema")
                != (COMMAND_SCHEMA_V2 if v2 else COMMAND_SCHEMA)
                or request.get("type") != "surface.command"
                or not isinstance(request_id, str)
            ):
                if v2:
                    return self.protocol_error(connection, "request_invalid"), True
                reason = "request_invalid"
            elif v2 and raw_request != canonical_json(request):
                return self.protocol_error(connection, "request_noncanonical"), True
            elif v2 and (
                not isinstance(request_sequence, int)
                or isinstance(request_sequence, bool)
                or request_sequence < 1
            ):
                return self.protocol_error(connection, "request_sequence_invalid"), True
            elif v2 and request_sequence != self.next_external_request_sequence:
                reason = "request_sequence_mismatch"
            elif request_id in self.request_ids:
                reason = "request_replay"
            else:
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
                    self.request_ids.add(request_id)
                    if v2:
                        self.latest_external_request_sha256 = hashlib.sha256(
                            raw_request
                        ).hexdigest()
                        self.accepted_external_request_bytes.append(raw_request)
                        self.next_external_request_sequence += 1
                    self.dispatch_log.append(
                        (descriptor["_fixture_provider_id"], str(surface_id), str(command))
                    )
            provider_applied, provider_status = self.provider_results.get(
                (str(surface_id), str(command)),
                (True, "provider_applied"),
            )
            return self.event(
                "command_receipt",
                connection.epoch,
                protocol_id=connection.protocol_id,
                **(
                    {
                        "request_sequence": request_sequence,
                        "next_external_request_sequence": self.next_external_request_sequence,
                    }
                    if v2
                    else {}
                ),
                request_id=request_id,
                surface_id=surface_id,
                command=command,
                accepted=reason is None,
                provider_applied=reason is None and provider_applied,
                status=provider_status if reason is None else reason,
                authority_receipt={"authority_epoch": self.authority_epoch},
            ), False

    def keepalive(
        self,
        connection: _FixtureSocket,
        request: dict[str, Any],
        raw_request: bytes,
    ) -> tuple[dict[str, Any], bool]:
        if connection.protocol_id != PROTOCOL_ID_V2:
            return self.protocol_error(connection, "keepalive_requires_v2"), True
        if (
            set(request) != {"$schema", "type", "request_sequence"}
            or request.get("$schema") != KEEPALIVE_SCHEMA_V2
            or request.get("type") != "keepalive"
        ):
            return self.protocol_error(connection, "request_invalid"), True
        if raw_request != canonical_json(request):
            return self.protocol_error(connection, "request_noncanonical"), True
        request_sequence = request.get("request_sequence")
        if (
            not isinstance(request_sequence, int)
            or isinstance(request_sequence, bool)
            or request_sequence < 1
        ):
            return self.protocol_error(connection, "request_sequence_invalid"), True
        with self.lock:
            accepted = request_sequence == self.next_external_request_sequence
            if accepted:
                self.latest_external_request_sha256 = hashlib.sha256(
                    raw_request
                ).hexdigest()
                self.accepted_external_request_bytes.append(raw_request)
                self.next_external_request_sequence += 1
                self.keepalive_count += 1
            return self.event(
                "keepalive_receipt",
                connection.epoch,
                protocol_id=PROTOCOL_ID_V2,
                request_sequence=request_sequence,
                next_external_request_sequence=self.next_external_request_sequence,
                accepted=accepted,
                status="accepted" if accepted else "request_sequence_mismatch",
                authority_receipt={"authority_epoch": self.authority_epoch},
            ), False

    def take_pre_keepalive_snapshot_count(self) -> int:
        with self.lock:
            count = self.pre_keepalive_snapshot_count
            self.pre_keepalive_snapshot_count = 0
            return count

    def restart_authority(self) -> None:
        with self.lock:
            self.restart_count += 1
            self.request_ids.clear()

    def rollover_authority(self) -> None:
        with self.lock:
            self.rollover_count += 1
            self.authority_epoch += 1
            self.request_ids.clear()

    def consume_drop_next_sequenced_receipt(self, receipt: dict[str, Any]) -> bool:
        with self.lock:
            if (
                self.drop_next_sequenced_receipt
                and receipt.get("accepted") is True
                and receipt.get("type")
                in {"command_receipt", "keepalive_receipt"}
            ):
                self.drop_next_sequenced_receipt = False
                return True
            return False

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
                "type": "revoke_receipt",
                "applied": applied,
                "status": "applied" if applied else "revoke_rejected",
                "transport_epoch": self.transport_counter,
                "listener_instance_id": self.listener_instance_id,
                "surface_revision": self.surface_revision,
                **self.transport_fields(),
            }
            if applied:
                receipt["authority_receipt"] = {}
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
                self.connection, auth_request, payload
            )
            if connection is None:
                if self.server.state.silent_auth_rejection:
                    return
                self.connection.sendall(_frame(0x1, canonical_json(auth_receipt)))
                self.connection.sendall(
                    _frame(0x8, struct.pack("!H", 4003) + b"authentication_rejected")
                )
                return
            connection.send(auth_receipt)
            connection.send(self.server.state.snapshot(connection))
            with self.server.state.lock:
                self.server.state.authenticated_snapshot_count += 1
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
                try:
                    request = json.loads(payload.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    if connection.protocol_id == PROTOCOL_ID_V2:
                        connection.send(
                            self.server.state.protocol_error(
                                connection, "request_not_json"
                            )
                        )
                    break
                if not isinstance(request, dict):
                    if connection.protocol_id == PROTOCOL_ID_V2:
                        connection.send(
                            self.server.state.protocol_error(
                                connection, "request_must_be_object"
                            )
                        )
                    break
                if request.get("type") == "surface.command":
                    receipt, close_after = self.server.state.command(
                        connection, request, payload
                    )
                elif request.get("type") == "keepalive":
                    receipt, close_after = self.server.state.keepalive(
                        connection, request, payload
                    )
                    for _ in range(
                        self.server.state.take_pre_keepalive_snapshot_count()
                    ):
                        connection.send(self.server.state.snapshot(connection))
                elif connection.protocol_id == PROTOCOL_ID_V2:
                    receipt = self.server.state.protocol_error(
                        connection, "request_type_unknown"
                    )
                    close_after = True
                else:
                    raise ValueError("command_type_unknown")
                if self.server.state.consume_drop_next_sequenced_receipt(receipt):
                    connection.close(4004, "receipt_lost_after_acceptance")
                    break
                connection.send(receipt)
                if close_after:
                    break
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
    def session_active(self) -> bool:
        with self._state.lock:
            return self._state.session_active

    @property
    def dispatch_log(self) -> list[tuple[str, str, str]]:
        return list(self._state.dispatch_log)

    @property
    def high_rate_payload_count(self) -> int:
        return self._state.high_rate_payload_count

    @property
    def upgrade_paths(self) -> list[str]:
        return list(self._state.upgrade_paths)

    @property
    def next_external_request_sequence(self) -> int:
        with self._state.lock:
            return self._state.next_external_request_sequence

    @property
    def accepted_external_request_bytes(self) -> list[bytes]:
        with self._state.lock:
            return list(self._state.accepted_external_request_bytes)

    @property
    def keepalive_count(self) -> int:
        with self._state.lock:
            return self._state.keepalive_count

    @property
    def active_connection_count(self) -> int:
        with self._state.lock:
            return len(self._state.connections)

    @property
    def authenticated_snapshot_count(self) -> int:
        with self._state.lock:
            return self._state.authenticated_snapshot_count

    def queue_pre_keepalive_snapshots(self, count: int) -> None:
        if isinstance(count, bool) or not isinstance(count, int) or count < 1 or count > 16:
            raise ValueError("pre_keepalive_snapshot_count_out_of_bounds")
        with self._state.lock:
            self._state.pre_keepalive_snapshot_count += count

    @property
    def authority_epoch(self) -> int:
        with self._state.lock:
            return self._state.authority_epoch

    def restart_authority(self) -> None:
        self._state.restart_authority()

    def rollover_authority(self) -> None:
        self._state.rollover_authority()

    def drop_next_sequenced_receipt_after_acceptance(self) -> None:
        with self._state.lock:
            self._state.drop_next_sequenced_receipt = True

    def add_surface(self, descriptor: dict[str, Any]) -> None:
        self._state.add_surface(descriptor)

    def remove_surface(self, surface_id: str) -> None:
        self._state.remove_surface(surface_id)

    def set_provider_result(
        self, surface_id: str, command: str, *, applied: bool, status: str
    ) -> None:
        with self._state.lock:
            self._state.provider_results[(surface_id, command)] = (applied, status)

    def set_silent_auth_rejection(self, enabled: bool) -> None:
        with self._state.lock:
            self._state.silent_auth_rejection = enabled

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
