from __future__ import annotations

import base64
import http.client
import json
import os
import socket
import unittest

import _app_path  # noqa: F401 - repo-root unittest discovery bootstrap

from trusted_local_control_conformance.contract import canonical_json_bytes
from trusted_local_control_conformance.loopback_server import LoopbackTestServer


def http_request(
    server: LoopbackTestServer,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    host: str | None = None,
    origin: str | None = None,
    cookie: str | None = None,
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=2)
    connection.putrequest(method, path, skip_host=True)
    connection.putheader("Host", host or server.host_header)
    if origin is not None:
        connection.putheader("Origin", origin)
    if cookie is not None:
        connection.putheader("Cookie", cookie)
    if body is not None:
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(len(body)))
    connection.endheaders(body)
    response = connection.getresponse()
    response_body = response.read()
    headers = {name.lower(): value for name, value in response.getheaders()}
    connection.close()
    return response.status, headers, response_body


def pair(server: LoopbackTestServer) -> tuple[dict[str, object], str]:
    body = canonical_json_bytes(
        {
            "pairing_code": server.fixture.pairing_code,
            "request_id": "pair-loopback-0001",
        }
    )
    status, headers, response_body = http_request(
        server,
        "POST",
        "/v1/pair",
        body=body,
        origin=server.origin,
    )
    if status != 200:
        raise AssertionError(response_body)
    cookie = headers["set-cookie"].split(";", 1)[0]
    return json.loads(response_body), cookie


def open_websocket(server: LoopbackTestServer, cookie: str) -> socket.socket:
    client = socket.create_connection(("127.0.0.1", server.port), timeout=2)
    client.settimeout(2)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        "GET /v1/events HTTP/1.1\r\n"
        f"Host: {server.host_header}\r\n"
        f"Origin: {server.origin}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        f"Cookie: {cookie}\r\n"
        "\r\n"
    )
    client.sendall(request.encode("ascii"))
    response = bytearray()
    while b"\r\n\r\n" not in response:
        response.extend(client.recv(4096))
    if b" 101 " not in response.split(b"\r\n", 1)[0]:
        raise AssertionError(response.decode("ascii", "replace"))
    return client


def send_client_text(client: socket.socket, value: dict[str, object]) -> None:
    payload = canonical_json_bytes(value)
    mask = b"\x11\x22\x33\x44"
    if len(payload) < 126:
        header = bytes((0x81, 0x80 | len(payload)))
    else:
        header = bytes((0x81, 0x80 | 126)) + len(payload).to_bytes(2, "big")
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    client.sendall(header + mask + masked)


def read_server_event(client: socket.socket) -> dict[str, object]:
    header = read_exact(client, 2)
    length = header[1] & 0x7F
    if length == 126:
        length = int.from_bytes(read_exact(client, 2), "big")
    payload = read_exact(client, length)
    return json.loads(payload.decode("utf-8"))


def read_exact(client: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        data.extend(client.recv(size - len(data)))
    return bytes(data)


class LoopbackServerTests(unittest.TestCase):
    def test_disabled_default_and_bind_guards(self) -> None:
        server = LoopbackTestServer()
        self.assertFalse(server.started)
        with self.assertRaisesRegex(RuntimeError, "explicit wearer opt-in"):
            server.start()
        with self.assertRaisesRegex(ValueError, "127.0.0.1"):
            LoopbackTestServer(explicitly_enabled=True, bind_host="0.0.0.0")
        with self.assertRaisesRegex(ValueError, "port 0"):
            LoopbackTestServer(explicitly_enabled=True, bind_port=18785)

    def test_same_origin_assets_have_security_headers_and_no_cors(self) -> None:
        with LoopbackTestServer(explicitly_enabled=True) as server:
            status, headers, body = http_request(server, "GET", "/")
            self.assertEqual(status, 200)
            self.assertIn(b"Quest local video control", body)
            self.assertIn("content-security-policy", headers)
            self.assertNotIn("access-control-allow-origin", headers)

            status, _, _ = http_request(
                server,
                "GET",
                "/app.js",
                origin="http://attacker.invalid",
            )
            self.assertEqual(status, 403)
            status, _, _ = http_request(
                server,
                "GET",
                "/",
                host="attacker.invalid",
            )
            self.assertEqual(status, 421)

            status, headers, _ = http_request(
                server,
                "OPTIONS",
                "/v1/pair",
                origin=server.origin,
            )
            self.assertEqual(status, 405)
            self.assertNotIn("access-control-allow-origin", headers)

    def test_pairing_is_canonical_single_use_and_has_http_only_cookie(self) -> None:
        with LoopbackTestServer(explicitly_enabled=True) as server:
            noncanonical = json.dumps(
                {
                    "request_id": "pair-loopback-0000",
                    "pairing_code": server.fixture.pairing_code,
                },
                indent=2,
            ).encode("utf-8")
            status, _, _ = http_request(
                server,
                "POST",
                "/v1/pair",
                body=noncanonical,
                origin=server.origin,
            )
            self.assertEqual(status, 400)

            response, cookie = pair(server)
            self.assertTrue(response["paired"])
            self.assertTrue(cookie.startswith("rq_session="))

            second_body = canonical_json_bytes(
                {
                    "pairing_code": server.fixture.pairing_code,
                    "request_id": "pair-loopback-0002",
                }
            )
            status, _, body = http_request(
                server,
                "POST",
                "/v1/pair",
                body=second_body,
                origin=server.origin,
            )
            self.assertEqual(status, 409)
            self.assertEqual(json.loads(body)["reason"], "controller_lease_occupied")

            status, _, _ = http_request(
                server,
                "POST",
                "/v1/pair",
                body=second_body,
                origin="http://attacker.invalid",
            )
            self.assertEqual(status, 403)

    def test_websocket_acceptance_precedes_callback_applied_state(self) -> None:
        with LoopbackTestServer(explicitly_enabled=True) as server:
            pair_response, cookie = pair(server)
            client = open_websocket(server, cookie)
            try:
                select = {
                    "command": "select_video",
                    "expected_authority_revision": pair_response["authority_revision"],
                    "expected_player_revision": 0,
                    "payload": {"video_id": "synthetic-grid"},
                    "request_id": "select-loopback-001",
                }
                send_client_text(client, select)
                accepted = read_server_event(client)

                self.assertEqual(accepted["event"], "command_accepted")
                self.assertEqual(accepted["request_id"], select["request_id"])
                self.assertEqual(server.fixture.player.selected_video_id, "synthetic-blue")
                self.assertEqual(server.fixture.state_revision, 0)

                applied = server.fixture.apply_next_player_callback()
                self.assertIsNotNone(applied)
                observed = read_server_event(client)

                self.assertEqual(observed["event"], "command_applied")
                self.assertEqual(observed["request_id"], select["request_id"])
                self.assertEqual(observed["state"]["selected_video_id"], "synthetic-grid")
                self.assertFalse(observed["state"]["playing"])
                self.assertEqual(observed["state"]["revision"], 1)
            finally:
                client.close()

    def test_websocket_requires_exact_origin_session_and_closed_command(self) -> None:
        with LoopbackTestServer(explicitly_enabled=True) as server:
            pair_response, cookie = pair(server)
            client = open_websocket(server, cookie)
            try:
                command = {
                    "command": "shell",
                    "expected_authority_revision": pair_response["authority_revision"],
                    "expected_player_revision": 0,
                    "payload": {},
                    "request_id": "shell-loopback-0001",
                }
                send_client_text(client, command)
                rejected = read_server_event(client)
                self.assertEqual(rejected["event"], "command_rejected")
                self.assertEqual(rejected["reason"], "unknown_command")
            finally:
                client.close()

            raw = socket.create_connection(("127.0.0.1", server.port), timeout=2)
            try:
                request = (
                    "GET /v1/events HTTP/1.1\r\n"
                    f"Host: {server.host_header}\r\n"
                    "Origin: http://attacker.invalid\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                    "Sec-WebSocket-Version: 13\r\n"
                    f"Cookie: {cookie}\r\n\r\n"
                )
                raw.sendall(request.encode("ascii"))
                self.assertIn(b" 403 ", raw.recv(4096).split(b"\r\n", 1)[0])
            finally:
                raw.close()

    def test_no_remote_revoke_or_generic_http_command_route(self) -> None:
        with LoopbackTestServer(explicitly_enabled=True) as server:
            for path in ("/control/command", "/control/revoke", "/upload", "/execute"):
                with self.subTest(path=path):
                    status, _, _ = http_request(
                        server,
                        "POST",
                        path,
                        body=canonical_json_bytes({"request": "closed"}),
                        origin=server.origin,
                    )
                    self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
