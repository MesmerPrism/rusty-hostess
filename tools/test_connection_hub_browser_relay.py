"""Target-free relay tests using the actual strict client and owner fixture."""
import base64
import hashlib
import http.client
import json
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path

from tools import connection_hub_browser_relay as relay
from tools import connection_hub_cli as hub
from tools.connection_hub_fixture import ConnectionHubFixture, media_surface


class RelayTests(unittest.TestCase):
    def test_client_frames_actual_owner_canonical_bytes(self):
        left, right = socket.socketpair()
        try:
            client = hub.WebSocketClient(right)
            message = {"$schema": hub.AUTHENTICATE_SCHEMA_V2, "type": "authenticate", "session": "A" * 43}
            client.send_json(message)
            self.assertEqual(relay.validate_request(relay.read_browser(left), True), message)
        finally:
            left.close(); right.close()

    def test_unmasked_fragment_binary_and_overflow_deny_before_payload(self):
        for frame in [b"\x81\x01x", b"\x01\x81", b"\x82\x81", b"\x81\xff", b"\x81\xfe\x10\x01"]:
            with self.subTest(frame=frame):
                left, right = socket.socketpair()
                try:
                    right.sendall(frame)
                    with self.assertRaises(relay.RelayError): relay.read_browser(left)
                finally:
                    left.close(); right.close()

    def test_noncanonical_and_unknown_auth_fields_deny(self):
        left, right = socket.socketpair()
        try:
            hub.WebSocketClient(right).send_text_bytes(b'{ "type":"authenticate"}')
            with self.assertRaises(relay.RelayError): relay.read_browser(left)
        finally:
            left.close(); right.close()
        with self.assertRaises(hub.HubError): relay.validate_request({"$schema": hub.AUTHENTICATE_SCHEMA_V2, "type": "authenticate", "session": "A" * 43, "hidden": True}, True)

    def test_closed_requests_and_positive_sequence(self):
        valid = {"$schema": hub.COMMAND_SCHEMA_V2, "type": "surface.command", "request_id": "test.request", "request_sequence": 1, "surface_id": "media.control", "command": "play", "args": {}}
        self.assertEqual(relay.validate_request(valid), valid)
        for change in [{"type": "create_group"}, {"request_sequence": True}, {"request_sequence": 0}, {"request_id": "bad/"}, {"args": {"high_rate": [1, 2]}}]:
            with self.subTest(change=change), self.assertRaises((relay.RelayError, hub.HubError, ValueError)):
                relay.validate_request({**valid, **change})

    def test_upgrade_exact_origin_route_key_and_no_duplicate_headers(self):
        key = base64.b64encode(b"0123456789abcdef").decode()
        original = f"GET /v1/socket HTTP/1.1\r\nHost: localhost\r\nOrigin: {relay.PAGE_ORIGIN}\r\nUpgrade: websocket\r\nConnection: keep-alive, Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: {key}\r\n\r\n"
        for request, accepted in [(original, True), (original.replace(relay.PAGE_ORIGIN, "https://foreign.test"), False), (original.replace("/v1/socket", "/arbitrary"), False), (original.replace("Host: localhost", "Host: localhost\r\nOrigin: foreign"), False)]:
            left, right = socket.socketpair()
            try:
                right.sendall(request.encode())
                if accepted:
                    relay.upgrade(left)
                    self.assertIn(b"101 Switching Protocols", right.recv(1024))
                else:
                    with self.assertRaises(relay.RelayError): relay.upgrade(left)
            finally:
                left.close(); right.close()

    def test_tls_pins_damage_and_size_deny(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "test.pem"; file.write_bytes(b"test-only-certificate")
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            self.assertEqual(relay.pinned_bytes(file, digest), b"test-only-certificate")
            file.write_bytes(b"damaged")
            with self.assertRaises(relay.RelayError): relay.pinned_bytes(file, digest)
            file.write_bytes(b"x" * 65537)
            with self.assertRaises(relay.RelayError): relay.pinned_bytes(file, digest)

    def test_exact_65536_server_frame_uses_rfc_64bit_length(self):
        class Sink:
            def sendall(self, data): self.data = data
        sink = Sink()
        relay.send_browser(sink, {"x": "x" * 65528})
        self.assertEqual(sink.data[:2], b"\x81\x7f")
        self.assertEqual(int.from_bytes(sink.data[2:10], "big"), 65536)
        self.assertEqual(len(sink.data[10:]), 65536)
        with self.assertRaises(relay.RelayError): relay.send_browser(sink, {"x": "x" * 65529})

    def test_actual_slow_trickle_upgrade_cannot_refresh_global_budget(self):
        left, right = socket.socketpair()
        def trickle():
            try:
                for byte in b"GET /v1/socket HTTP/1.1\r\n":
                    right.sendall(bytes((byte,))); time.sleep(.01)
            except OSError:
                pass
        thread = threading.Thread(target=trickle); thread.start()
        start = time.monotonic()
        try:
            with self.assertRaises((relay.RelayError, TimeoutError)):
                relay.upgrade(left, deadline=start+.06)
            self.assertLess(time.monotonic()-start, .3)
        finally:
            left.close(); right.close(); thread.join(1)

    def test_expired_pre_auth_reads_never_open_downstream(self):
        left, right = socket.socketpair()
        try:
            hub.WebSocketClient(right).send_json({"$schema": hub.AUTHENTICATE_SCHEMA_V2, "type": "authenticate", "session": "A" * 43})
            factory = mock.Mock()
            with self.assertRaises(relay.RelayError):
                relay.relay_session(left, hub.transport_policy("http://127.0.0.1:1", "loopback_fixture"), connection_factory=factory, absolute_deadline=time.monotonic()-1)
            factory.assert_not_called()
        finally:
            left.close(); right.close()

    def test_owner_upgrade_expiry_denies_before_authentication_write(self):
        clock = [0.0]
        class Socket:
            def __init__(self): self.sent = []; self.closed = False
            def settimeout(self, timeout): self.timeout = timeout
            def sendall(self, payload): self.sent.append(payload)
            def close(self): self.closed = True
        raw = Socket(); key = base64.b64encode(b"0" * 16).decode()
        accept = base64.b64encode(hashlib.sha1((key+relay.GUID).encode()).digest()).decode()
        def header(*args, **kwargs):
            clock[0] = 3.0
            return "HTTP/1.1 101 Switching Protocols\r\nSec-WebSocket-Accept: "+accept
        with mock.patch.object(hub.time, "monotonic", side_effect=lambda: clock[0]), mock.patch.object(hub.socket, "create_connection", return_value=raw), mock.patch.object(hub.os, "urandom", return_value=b"0"*16), mock.patch.object(hub.WebSocketClient, "_read_http_head", side_effect=header):
            with self.assertRaisesRegex(hub.HubError, "transport_deadline_expired"):
                hub.WebSocketClient.connect(hub.transport_policy("http://127.0.0.1:1", "loopback_fixture"), "A"*43, hub.PROTOCOL_ID_V2, transport_deadline=2.0)
        self.assertEqual(len(raw.sent), 1)
        self.assertTrue(raw.sent[0].startswith(b"GET /v1/socket"))
        self.assertTrue(raw.closed)

    def test_owner_post_connect_expiry_and_tls_failure_close_owned_socket(self):
        for expire in (True, False):
            clock = [0.0]
            raw = mock.Mock()
            def connect(*args, **kwargs):
                if expire: clock[0] = 3.0
                return raw
            context = mock.Mock()
            context.wrap_socket.side_effect = OSError("modeled TLS failure")
            with mock.patch.object(hub.time, "monotonic", side_effect=lambda: clock[0]), mock.patch.object(hub.socket, "create_connection", side_effect=connect), mock.patch.object(hub.ssl, "create_default_context", return_value=context):
                with self.assertRaises((hub.HubError, OSError)):
                    hub.WebSocketClient.connect(hub.transport_policy("https://example.test:443", "tls"), "A"*43, hub.PROTOCOL_ID_V2, transport_deadline=2.0)
            raw.close.assert_called_once()
            raw.sendall.assert_not_called()
            if expire: context.wrap_socket.assert_not_called()

    def test_owner_actual_slow_trickle_read_deadline(self):
        left, right = socket.socketpair()
        client = hub.WebSocketClient(left); client._transport_deadline = time.monotonic()+.05
        def trickle():
            try:
                for byte in b"\x81\x05hello":
                    right.sendall(bytes((byte,))); time.sleep(.02)
            except OSError:
                pass
        thread = threading.Thread(target=trickle); thread.start()
        try:
            with self.assertRaises((hub.HubError, TimeoutError)): client.read_json()
        finally:
            left.close(); right.close(); thread.join(1)

    def test_actual_owner_fixture_auth_command_receipt_and_no_extra_dispatch(self):
        with ConnectionHubFixture() as fixture:
            fixture.add_surface(media_surface())
            policy = hub.transport_policy(fixture.origin, "loopback_fixture")
            endpoint = fixture.origin.removeprefix("http://").split(":")
            connection = http.client.HTTPConnection(endpoint[0], int(endpoint[1]))
            connection.request("POST", "/v1/pair", body=json.dumps({"$schema": hub.PAIR_REQUEST_SCHEMA, "pairing_code": fixture.pairing_code, "controller_identity_sha256": "a" * 64}), headers={"Content-Type": "application/json"})
            receipt = json.loads(connection.getresponse().read()); connection.close()
            left, right = socket.socketpair(); results = []; failures = []
            def run():
                try: results.append(relay.relay_session(left, policy, 1))
                except BaseException as error: failures.append(type(error).__name__)
                finally: left.close()
            thread = threading.Thread(target=run); thread.start()
            browser = hub.WebSocketClient(right)
            try:
                browser.send_json({"$schema": hub.AUTHENTICATE_SCHEMA_V2, "type": "authenticate", "session": receipt["session"]})
                auth = browser.read_json(); snapshot = browser.read_json()
                self.assertTrue(auth["accepted"])
                self.assertEqual(snapshot["type"], "surface_snapshot")
                browser.send_json({"$schema": hub.COMMAND_SCHEMA_V2, "type": "surface.command", "request_sequence": auth["next_external_request_sequence"], "request_id": "relay.fixture.play", "surface_id": "media.control", "command": "play", "args": {}})
                while True:
                    event = browser.read_json()
                    if event["type"] == "command_receipt": break
                self.assertEqual(event["request_id"], "relay.fixture.play")
                self.assertTrue(event["provider_applied"])
                self.assertEqual(event["confidentiality"], "none")
                thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertEqual(failures, [])
                self.assertEqual(results[0]["browser_commands"], 1)
                self.assertEqual(len(fixture.dispatch_log), 1)
                self.assertNotIn("session", results[0])
            finally:
                right.close(); thread.join(3)


if __name__ == "__main__": unittest.main()
