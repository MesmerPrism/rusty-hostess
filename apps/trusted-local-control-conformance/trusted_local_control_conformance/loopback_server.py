"""Ephemeral loopback-only HTTP/WebSocket shell for offline conformance."""

from __future__ import annotations

import base64
import hashlib
import json
import queue
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .contract import canonical_json_bytes
from .fake_runtime import TrustedLocalControlFixture


WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_REQUEST_BYTES = 4096
SESSION_COOKIE = "rq_session"


class LoopbackTestServer:
    """Test server that rejects LAN hosts, fixed ports, and implicit startup."""

    def __init__(
        self,
        fixture: TrustedLocalControlFixture | None = None,
        *,
        explicitly_enabled: bool = False,
        bind_host: str = "127.0.0.1",
        bind_port: int = 0,
        auto_apply_callbacks: bool = False,
        web_root: Path | None = None,
    ) -> None:
        if bind_host != "127.0.0.1":
            raise ValueError("conformance server permits only 127.0.0.1")
        if bind_port != 0:
            raise ValueError("conformance server permits only ephemeral port 0")
        self.fixture = fixture or TrustedLocalControlFixture()
        self.explicitly_enabled = explicitly_enabled
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.auto_apply_callbacks = auto_apply_callbacks
        self.web_root = web_root or Path(__file__).resolve().parents[1] / "web"
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()

    @property
    def started(self) -> bool:
        return self._httpd is not None

    @property
    def port(self) -> int:
        if self._httpd is None:
            raise RuntimeError("server has not started")
        return int(self._httpd.server_address[1])

    @property
    def host_header(self) -> str:
        return f"127.0.0.1:{self.port}"

    @property
    def origin(self) -> str:
        return f"http://{self.host_header}"

    @property
    def url(self) -> str:
        return f"{self.origin}/"

    def start(self) -> "LoopbackTestServer":
        if self.started:
            return self
        if not self.explicitly_enabled:
            raise RuntimeError("listener disabled: explicit wearer opt-in required")
        enable_receipt = self.fixture.wearer_enable(
            foreground=True,
            wearer_confirmed=True,
        )
        if enable_receipt.get("decision") != "accepted":
            raise RuntimeError("synthetic wearer activation was rejected")

        owner = self

        class Handler(_ControlHandler):
            server_owner = owner

        httpd = ThreadingHTTPServer((self.bind_host, self.bind_port), Handler)
        httpd.daemon_threads = True
        self._httpd = httpd
        self._stopping.clear()
        self._thread = threading.Thread(
            target=httpd.serve_forever,
            name="trusted-local-control-loopback",
            daemon=True,
        )
        self._thread.start()
        return self

    def close(self) -> None:
        if self._httpd is None:
            return
        self._stopping.set()
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._httpd = None

    def __enter__(self) -> "LoopbackTestServer":
        return self.start()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


class _ControlHandler(BaseHTTPRequestHandler):
    server_owner: LoopbackTestServer
    protocol_version = "HTTP/1.1"
    server_version = "HostessConformance/1"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        return

    @property
    def owner(self) -> LoopbackTestServer:
        return self.server_owner

    def do_OPTIONS(self) -> None:
        if not self._host_allowed():
            self._send_json(421, {"error": "host_rejected"})
            return
        if not self._origin_allowed():
            self._send_json(403, {"error": "origin_rejected"})
            return
        self._send_json(405, {"error": "cors_not_supported"})

    def do_GET(self) -> None:
        if not self._host_allowed():
            self._send_json(421, {"error": "host_rejected"})
            return
        origin = self.headers.get("Origin")
        if origin is not None and not self._origin_allowed():
            self._send_json(403, {"error": "origin_rejected"})
            return
        path = urlsplit(self.path).path
        if path == "/v1/events":
            self._serve_websocket()
            return
        asset = {
            "/": "index.html",
            "/app.js": "app.js",
            "/styles.css": "styles.css",
        }.get(path)
        if asset is None:
            self._send_json(404, {"error": "route_not_found"})
            return
        content_type = {
            "index.html": "text/html; charset=utf-8",
            "app.js": "text/javascript; charset=utf-8",
            "styles.css": "text/css; charset=utf-8",
        }[asset]
        body = (self.owner.web_root / asset).read_bytes()
        self._send_bytes(200, body, content_type=content_type)

    def do_POST(self) -> None:
        if not self._host_allowed():
            self._send_json(421, {"error": "host_rejected"})
            return
        if not self._origin_allowed():
            self._send_json(403, {"error": "origin_rejected"})
            return
        if self.headers.get("Content-Type") != "application/json":
            self._send_json(415, {"error": "content_type_rejected"})
            return
        parsed = self._read_canonical_json()
        if parsed is None:
            return
        payload, canonical = parsed
        if not canonical:
            self._send_json(400, {"error": "non_canonical_json"})
            return
        if urlsplit(self.path).path != "/v1/pair":
            self._send_json(404, {"error": "route_not_found"})
            return
        self._pair(payload)

    def _pair(self, payload: Any) -> None:
        if not isinstance(payload, dict) or set(payload) != {"pairing_code", "request_id"}:
            self._send_json(400, {"error": "non_canonical_pair_request"})
            return
        pairing_code = payload.get("pairing_code")
        request_id = payload.get("request_id")
        if not isinstance(pairing_code, str) or not isinstance(request_id, str):
            self._send_json(400, {"error": "invalid_pair_request"})
            return
        result = self.owner.fixture.pair(
            pairing_code=pairing_code,
            request_id=request_id,
        )
        if result.get("decision") != "accepted":
            status = 409 if result.get("reason") == "controller_lease_occupied" else 401
            self._send_json(status, {"paired": False, "reason": result.get("reason")})
            return
        token = self.owner.fixture.session_token
        if token is None:
            self._send_json(500, {"error": "fixture_session_missing"})
            return
        response = {
            "authority_revision": result["authority_revision"],
            "controller_label": "windows-browser",
            "paired": True,
            "session_expires_at": result["session_expires_at"],
        }
        self._send_json(
            200,
            response,
            extra_headers=(
                (
                    "Set-Cookie",
                    f"{SESSION_COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=90",
                ),
            ),
        )

    def _serve_websocket(self) -> None:
        if not self._origin_allowed():
            self._send_json(403, {"error": "origin_rejected"})
            return
        if self.headers.get("Upgrade", "").lower() != "websocket":
            self._send_json(426, {"error": "websocket_upgrade_required"})
            return
        if "upgrade" not in self.headers.get("Connection", "").lower():
            self._send_json(400, {"error": "connection_upgrade_required"})
            return
        key = self.headers.get("Sec-WebSocket-Key", "")
        if not key or self.headers.get("Sec-WebSocket-Version") != "13":
            self._send_json(400, {"error": "websocket_key_rejected"})
            return
        token = self._session_cookie()
        self.owner.fixture.sweep_expiry()
        if token is None or token != self.owner.fixture.session_token:
            self._send_json(401, {"error": "session_invalid"})
            return

        accept = base64.b64encode(
            hashlib.sha1((key + WEBSOCKET_GUID).encode("ascii")).digest()
        ).decode("ascii")
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'")
        self.end_headers()
        self.close_connection = True

        subscriber = self.owner.fixture.subscribe()
        writer_stop = threading.Event()
        write_lock = threading.Lock()

        def writer() -> None:
            try:
                while not writer_stop.is_set() and not self.owner._stopping.is_set():
                    try:
                        event = subscriber.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    with write_lock:
                        _write_server_websocket_frame(
                            self.connection,
                            canonical_json_bytes(event),
                            opcode=1,
                        )
            except (ConnectionError, OSError):
                writer_stop.set()

        writer_thread = threading.Thread(target=writer, daemon=True)
        writer_thread.start()
        self.connection.settimeout(0.2)
        try:
            while not writer_stop.is_set() and not self.owner._stopping.is_set():
                try:
                    opcode, payload = _read_client_websocket_frame(self.connection)
                except socket.timeout:
                    continue
                if opcode == 8:
                    with write_lock:
                        _write_server_websocket_frame(self.connection, b"", opcode=8)
                    break
                if opcode == 9:
                    with write_lock:
                        _write_server_websocket_frame(self.connection, payload, opcode=10)
                    continue
                if opcode != 1:
                    with write_lock:
                        _write_server_websocket_frame(
                            self.connection,
                            canonical_json_bytes({"error": "unsupported_websocket_opcode"}),
                            opcode=1,
                        )
                    continue
                self._handle_websocket_command(token, payload)
        except (ConnectionError, OSError, ValueError):
            pass
        finally:
            writer_stop.set()
            self.owner.fixture.unsubscribe(subscriber)
            writer_thread.join(timeout=1.0)

    def _handle_websocket_command(self, token: str, payload: bytes) -> None:
        try:
            if len(payload) > MAX_REQUEST_BYTES:
                raise ValueError("request_too_large")
            text = payload.decode("utf-8")
            envelope = json.loads(text)
            if canonical_json_bytes(envelope) != payload:
                raise ValueError("non_canonical_command")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self.owner.fixture._emit(
                {
                    "event": "command_rejected",
                    "reason": str(error) or "invalid_canonical_command",
                }
            )
            return
        result = self.owner.fixture.handle_command(
            session_token=token,
            envelope=envelope,
        )
        if self.owner.auto_apply_callbacks and result.get("application_pending"):
            self.owner.fixture.apply_next_player_callback()

    def _host_allowed(self) -> bool:
        return self.headers.get("Host") == self.owner.host_header

    def _origin_allowed(self) -> bool:
        return self.headers.get("Origin") == self.owner.origin

    def _session_cookie(self) -> str | None:
        cookies = self.headers.get("Cookie", "")
        for part in cookies.split(";"):
            name, separator, value = part.strip().partition("=")
            if separator and name == SESSION_COOKIE and value:
                return value
        return None

    def _read_canonical_json(self) -> tuple[Any, bool] | None:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None or not raw_length.isdigit():
            self._send_json(411, {"error": "content_length_required"})
            return None
        length = int(raw_length)
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "request_size_rejected"})
            return None
        body = self.rfile.read(length)
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "invalid_json"})
            return None
        return parsed, canonical_json_bytes(parsed) == body

    def _send_json(
        self,
        status: int,
        payload: dict[str, Any],
        *,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self._send_bytes(
            status,
            canonical_json_bytes(payload),
            content_type="application/json; charset=utf-8",
            extra_headers=extra_headers,
        )

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'")
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


def _write_server_websocket_frame(connection: Any, payload: bytes, *, opcode: int) -> None:
    if len(payload) > MAX_REQUEST_BYTES:
        raise ValueError("event exceeds bounded WebSocket frame size")
    if len(payload) < 126:
        header = bytes((0x80 | opcode, len(payload)))
    else:
        header = bytes((0x80 | opcode, 126)) + len(payload).to_bytes(2, "big")
    connection.sendall(header + payload)


def _read_client_websocket_frame(connection: socket.socket) -> tuple[int, bytes]:
    header = _read_exact(connection, 2)
    if len(header) != 2:
        raise ConnectionError("websocket closed")
    if header[0] & 0x70:
        raise ValueError("websocket extension bits are forbidden")
    if not header[0] & 0x80:
        raise ValueError("fragmented frames are forbidden")
    opcode = header[0] & 0x0F
    if not header[1] & 0x80:
        raise ValueError("client frames must be masked")
    length = header[1] & 0x7F
    if length == 126:
        length = int.from_bytes(_read_exact(connection, 2), "big")
    elif length == 127:
        raise ValueError("64-bit WebSocket frame length is forbidden")
    if length > MAX_REQUEST_BYTES:
        raise ValueError("WebSocket frame exceeds bound")
    mask = _read_exact(connection, 4)
    payload = _read_exact(connection, length)
    return opcode, bytes(value ^ mask[index % 4] for index, value in enumerate(payload))


def _read_exact(connection: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = connection.recv(size - len(data))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)
