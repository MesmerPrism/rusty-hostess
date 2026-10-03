#!/usr/bin/env python3
"""Bounded foreground TLS adapter for the existing Connection Hub controller.

AGPL-3.0-or-later. No device APIs, enrollment, listener management, authority,
secret persistence or automatic retries. The downstream Hub remains authority.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import select
import socket
import ssl
import struct
import time
from pathlib import Path

try:
    from tools import connection_hub_cli as hub
except ModuleNotFoundError:
    import connection_hub_cli as hub

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
PAGE_ORIGIN = "https://mesmerprism.com"


class RelayError(ValueError):
    """Closed local transport failure; messages never include credentials."""


def pinned_bytes(path: Path, digest: str) -> bytes:
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise RelayError("tls_pin_shape_invalid")
    size = path.stat().st_size
    if not 0 < size <= 65536:
        raise RelayError("tls_material_size_invalid")
    value = path.read_bytes()
    if len(value) != size or hashlib.sha256(value).hexdigest() != digest:
        raise RelayError("tls_material_pin_differs")
    return value


def tls_context(cert: Path, key: Path, cert_sha: str, key_sha: str) -> ssl.SSLContext:
    pinned_bytes(cert, cert_sha)
    pinned_bytes(key, key_sha)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(cert), str(key))
    # Reobserve both files after the platform loader; no stale pin success.
    pinned_bytes(cert, cert_sha)
    pinned_bytes(key, key_sha)
    return context


def remaining(deadline: float) -> float:
    value = deadline - time.monotonic()
    if value <= 0:
        raise RelayError("foreground_budget_expired")
    return value


def read_exact(sock: socket.socket, length: int, deadline: float | None = None) -> bytes:
    result = bytearray()
    while len(result) < length:
        if deadline is not None:
            sock.settimeout(min(6, remaining(deadline)))
        part = sock.recv(length - len(result))
        if not part:
            raise RelayError("browser_connection_closed")
        result.extend(part)
    return bytes(result)


def upgrade(sock: socket.socket, allowed_origin: str = PAGE_ORIGIN, deadline: float | None = None) -> None:
    data = bytearray()
    while not data.endswith(b"\r\n\r\n"):
        if len(data) >= 8192:
            raise RelayError("upgrade_too_large")
        data.extend(read_exact(sock, 1, deadline))
    try:
        lines = data[:-4].decode("ascii").split("\r\n")
        if lines[0] != "GET /v1/socket HTTP/1.1":
            raise RelayError("upgrade_route_invalid")
        headers = {}
        for line in lines[1:]:
            name, value = line.split(":", 1)
            name = name.strip().lower()
            if name in headers:
                raise RelayError("upgrade_duplicate_header")
            headers[name] = value.strip()
        if (headers.get("origin") != allowed_origin
                or headers.get("upgrade", "").lower() != "websocket"
                or "upgrade" not in [part.strip() for part in headers.get("connection", "").lower().split(",")]
                or headers.get("sec-websocket-version") != "13"
                or "sec-websocket-protocol" in headers):
            raise RelayError("upgrade_origin_or_protocol_invalid")
        key = headers["sec-websocket-key"]
        if len(base64.b64decode(key, validate=True)) != 16:
            raise RelayError("upgrade_key_invalid")
    except (UnicodeError, KeyError, ValueError) as error:
        if isinstance(error, RelayError):
            raise
        raise RelayError("upgrade_shape_invalid") from None
    accepted = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
    if deadline is not None:
        sock.settimeout(min(6, remaining(deadline)))
    sock.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                  "Connection: Upgrade\r\nSec-WebSocket-Accept: " + accepted + "\r\n\r\n").encode("ascii"))


def read_browser(sock: socket.socket, deadline: float | None = None) -> dict:
    first, second = read_exact(sock, 2, deadline)
    if first != 0x81 or not second & 0x80:
        raise RelayError("browser_frame_must_be_masked_final_text")
    size = second & 127
    if size == 126:
        size = struct.unpack("!H", read_exact(sock, 2, deadline))[0]
    elif size == 127:
        raise RelayError("browser_frame_too_large")
    if not 0 < size <= hub.MAX_COMMAND_BODY:
        raise RelayError("browser_frame_too_large")
    mask = read_exact(sock, 4, deadline)
    encoded = read_exact(sock, size, deadline)
    raw = bytes(byte ^ mask[i % 4] for i, byte in enumerate(encoded))
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise RelayError("browser_frame_not_json") from None
    if not isinstance(value, dict) or hub.canonical_json(value) != raw:
        raise RelayError("browser_frame_not_canonical")
    return value


def send_browser(sock: socket.socket, event: dict, deadline: float | None = None) -> None:
    payload = hub.canonical_json(event)
    if len(payload) > hub.MAX_SERVER_FRAME:
        raise RelayError("hub_event_too_large")
    header = (bytes((0x81, len(payload))) if len(payload) < 126
              else bytes((0x81, 126)) + struct.pack("!H", len(payload)) if len(payload) < 65536
              else bytes((0x81, 127)) + struct.pack("!Q", len(payload)))
    if deadline is not None:
        sock.settimeout(min(6, remaining(deadline)))
    sock.sendall(header + payload)


def validate_request(message: dict, authenticate: bool = False) -> dict:
    if authenticate:
        hub.validate_protocol_message(message, "socket_authenticate_v2")
        if not isinstance(message["session"], str) or not hub.OPAQUE_SESSION.fullmatch(message["session"]):
            raise RelayError("browser_session_shape_invalid")
        return message
    kind = message.get("type")
    if kind not in {"surface.command", "keepalive"}:
        raise RelayError("browser_request_type_unavailable")
    hub.validate_protocol_message(message, "surface_command_v2" if kind == "surface.command" else "keepalive_v2")
    sequence = message["request_sequence"]
    if type(sequence) is not int or not 1 <= sequence <= 9007199254740991:
        raise RelayError("browser_sequence_invalid")
    if kind == "surface.command":
        if any(not isinstance(message[k], str) or not hub.TOKEN.fullmatch(message[k])
               for k in ("surface_id", "command", "request_id")):
            raise RelayError("browser_command_identity_invalid")
        hub.validate_args(message["args"])
    return message


def relay_session(browser: socket.socket, policy: hub.TransportPolicy,
                  duration: float = 900, connection_factory=hub.HubConnection,
                  absolute_deadline: float | None = None) -> dict:
    """Forward through the actual owner controller, preserving its receipts.

    No local acceptance boolean or authority lease is generated. The injected
    factory exists for portable tests; the CLI always uses HubConnection.
    """
    deadline = min(time.monotonic() + duration, absolute_deadline) if absolute_deadline is not None else time.monotonic() + duration
    browser.settimeout(min(10, duration))
    auth = validate_request(read_browser(browser, deadline), authenticate=True)
    remaining(deadline)
    downstream = connection_factory(policy, auth["session"], hub.PROTOCOL_ID_V2,
                                    transport_deadline=deadline)
    auth.clear()  # No clear bearer retained in the request object or a receipt.
    counts = {"browser_commands": 0, "hub_events": 0}
    try:
        send_browser(browser, downstream.authentication_receipt, deadline)
        for event in downstream.events:
            send_browser(browser, event, deadline)
            counts["hub_events"] += 1
        downstream.events.clear()
        while time.monotonic() < deadline:
            buffered = isinstance(browser, ssl.SSLSocket) and browser.pending() > 0
            ready, _, _ = select.select([browser, downstream.socket.sock], [], [], 0 if buffered else min(1, deadline - time.monotonic()))
            if buffered and browser not in ready:
                ready.append(browser)
            if downstream.socket.sock in ready:
                event = downstream.read_event(timeout=min(6, max(.001, deadline-time.monotonic())))
                send_browser(browser, event, deadline)
                counts["hub_events"] += 1
                downstream.events.clear()
            if browser not in ready:
                continue
            browser.settimeout(min(6, max(.001, deadline-time.monotonic())))
            message = validate_request(read_browser(browser, deadline))
            if time.monotonic() >= deadline:
                raise RelayError("foreground_budget_expired_before_dispatch")
            if message["request_sequence"] != downstream.next_external_request_sequence:
                raise RelayError("browser_sequence_not_current")
            if message["type"] == "surface.command":
                downstream.send_command(message["surface_id"], message["command"], message["args"],
                                        explicit_request_id=message["request_id"],
                                        explicit_request_sequence=message["request_sequence"])
                counts["browser_commands"] += 1
            else:
                downstream.send_keepalive(explicit_request_sequence=message["request_sequence"])
            for event in downstream.events:
                send_browser(browser, event, deadline)
                counts["hub_events"] += 1
            downstream.events.clear()
        return {"status": "duration_complete", "authority_accepted": "not_claimed", **counts}
    finally:
        downstream.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="Explicit existing Hub HTTP(S) root with port")
    parser.add_argument("--classification", choices=["trusted_lan_experimental", "tls"], required=True)
    parser.add_argument("--allow-insecure-trusted-lan", action="store_true")
    parser.add_argument("--serve", action="store_true", help="Explicitly start bounded foreground relay")
    parser.add_argument("--port", type=int, default=18786)
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--certificate", type=Path)
    parser.add_argument("--private-key", type=Path)
    parser.add_argument("--certificate-sha256")
    parser.add_argument("--private-key-sha256")
    options = parser.parse_args()
    try:
        policy = hub.transport_policy(options.origin, options.classification, options.allow_insecure_trusted_lan)
        if not 1024 <= options.port <= 65535 or not 1 <= options.seconds <= 900:
            raise RelayError("listener_budget_invalid")
        if not options.serve:
            print(json.dumps({"status": "planned", "listener_started": False,
                              "bind": "127.0.0.1", "browser_origin": PAGE_ORIGIN,
                              "downstream_classification": policy.classification,
                              "downstream_confidentiality": policy.confidentiality,
                              "command_authority": "downstream_hub_only"}))
            return 0
        if not all((options.certificate, options.private_key, options.certificate_sha256, options.private_key_sha256)):
            raise RelayError("pinned_tls_material_required")
        context = tls_context(options.certificate, options.private_key, options.certificate_sha256, options.private_key_sha256)
        deadline = time.monotonic() + options.seconds
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", options.port))
            listener.listen(1)
            listener.settimeout(min(30, options.seconds))
            raw, _ = listener.accept()  # One foreground browser session per invocation.
            with raw:
                raw.settimeout(min(10, remaining(deadline)))
                with context.wrap_socket(raw, server_side=True) as browser:
                    remaining(deadline)
                    upgrade(browser, deadline=deadline)
                    result = relay_session(browser, policy, remaining(deadline), absolute_deadline=deadline)
                    print(json.dumps(result))
        return 0
    except (OSError, ValueError, hub.HubError):
        # Never print raw exceptions, request bodies, session bearers or key data.
        print(json.dumps({"status": "failed_or_disconnected", "command_outcome": "not_inferred",
                          "automatic_retry": False, "authority_accepted": "not_claimed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
