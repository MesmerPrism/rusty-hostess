#!/usr/bin/env python3
"""Closed ADB-gated operator CLI for the Rusty Quest video-control example."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import ipaddress
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

PACKAGE = "io.github.mesmerprism.rustyquest.spatial_video_control_example"
AUTHORITY = f"{PACKAGE}.debug-local-control"
PROVIDER_METHODS = frozenset({"status", "enable_paired", "enable_open_lan", "revoke"})
SERIAL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{3,63}$")
REQUEST_ID = re.compile(r"^[a-z0-9][a-z0-9-]{15,63}$")
RECEIPT_B64 = re.compile(r"receipt_b64=([A-Za-z0-9+/=]+)")
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
DISCOVERY_SERVICE = "_rustyquest-control._tcp.local."
MAX_MEDIA_PROFILES_PER_SESSION = 5


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def new_request_id(prefix: str) -> str:
    value = f"{prefix}-{uuid.uuid4()}"
    if not REQUEST_ID.fullmatch(value):
        raise RuntimeError("generated_request_id_invalid")
    return value


def invoke_provider(serial: str, method: str) -> dict[str, Any]:
    if not SERIAL.fullmatch(serial):
        raise ValueError("serial_must_be_an_explicit_usb_identifier")
    if method not in PROVIDER_METHODS:
        raise ValueError("provider_method_not_registered")
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError("adb_not_found")
    command = [
        adb,
        "-s",
        serial,
        "shell",
        "content",
        "call",
        "--uri",
        f"content://{AUTHORITY}",
        "--method",
        method,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=12, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"adb_provider_failed:{completed.returncode}")
    match = RECEIPT_B64.search(completed.stdout)
    if not match:
        raise RuntimeError("adb_provider_receipt_missing")
    try:
        receipt = json.loads(base64.b64decode(match.group(1), validate=True).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("adb_provider_receipt_invalid") from error
    if receipt.get("schema") != "rusty.quest.debug_local_control_receipt.v1":
        raise RuntimeError("adb_provider_schema_mismatch")
    return receipt


def redact(receipt: dict[str, Any], reveal_pairing_code: bool) -> dict[str, Any]:
    result = dict(receipt)
    if result.get("pairing_code") and not reveal_pairing_code:
        result["pairing_code"] = "<redacted>"
        result["pairing_code_redacted"] = True
    return result


def _dns_name(value: str) -> bytes:
    labels = value.rstrip(".").split(".")
    encoded = bytearray()
    for label in labels:
        item = label.encode("ascii")
        if not item or len(item) > 63:
            raise RuntimeError("discovery_service_name_invalid")
        encoded.append(len(item))
        encoded.extend(item)
    encoded.append(0)
    return bytes(encoded)


def _read_dns_name(packet: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    next_offset = offset
    jumped = False
    visited: set[int] = set()
    while True:
        if offset >= len(packet) or offset in visited:
            raise RuntimeError("discovery_dns_name_invalid")
        visited.add(offset)
        length = packet[offset]
        if length == 0:
            if not jumped:
                next_offset = offset + 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(packet):
                raise RuntimeError("discovery_dns_pointer_truncated")
            pointer = ((length & 0x3F) << 8) | packet[offset + 1]
            if not jumped:
                next_offset = offset + 2
                jumped = True
            offset = pointer
            continue
        if length & 0xC0 or length > 63 or offset + 1 + length > len(packet):
            raise RuntimeError("discovery_dns_label_invalid")
        labels.append(packet[offset + 1 : offset + 1 + length].decode("utf-8"))
        offset += 1 + length
        if not jumped:
            next_offset = offset
    return ".".join(labels).lower() + ".", next_offset


def _parse_dns_records(packet: bytes) -> list[tuple[str, int, bytes, int]]:
    if len(packet) < 12:
        raise RuntimeError("discovery_dns_packet_truncated")
    _, _, questions, answers, authorities, additional = struct.unpack("!6H", packet[:12])
    offset = 12
    for _ in range(questions):
        _, offset = _read_dns_name(packet, offset)
        if offset + 4 > len(packet):
            raise RuntimeError("discovery_dns_question_truncated")
        offset += 4
    records: list[tuple[str, int, bytes, int]] = []
    for _ in range(answers + authorities + additional):
        name, offset = _read_dns_name(packet, offset)
        if offset + 10 > len(packet):
            raise RuntimeError("discovery_dns_record_truncated")
        record_type, _, _, length = struct.unpack("!HHIH", packet[offset : offset + 10])
        offset += 10
        end = offset + length
        if end > len(packet):
            raise RuntimeError("discovery_dns_rdata_truncated")
        records.append((name, record_type, packet[offset:end], offset))
        offset = end
    return records


def discover_services(timeout_seconds: float = 3.0) -> dict[str, Any]:
    if timeout_seconds < 1 or timeout_seconds > 10:
        raise ValueError("discovery_timeout_out_of_bounds")
    query = (
        struct.pack("!6H", 0, 0, 1, 0, 0, 0)
        + _dns_name(DISCOVERY_SERVICE)
        + struct.pack("!HH", 12, 1)
    )
    instances: set[str] = set()
    services: dict[str, tuple[str, int]] = {}
    attributes: dict[str, dict[str, str]] = {}
    addresses: dict[str, set[str]] = {}
    deadline = time.monotonic() + timeout_seconds
    next_query = 0.0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as discovery:
        discovery.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        discovery.bind(("", 5353))
        discovery.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            socket.inet_aton("224.0.0.251") + socket.inet_aton("0.0.0.0"),
        )
        discovery.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        discovery.settimeout(0.25)
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_query:
                discovery.sendto(query, ("224.0.0.251", 5353))
                next_query = now + 0.75
            try:
                packet, _ = discovery.recvfrom(9000)
            except socket.timeout:
                continue
            try:
                records = _parse_dns_records(packet)
                for name, record_type, data, data_offset in records:
                    if record_type == 12:
                        target, _ = _read_dns_name(packet, data_offset)
                        if name == DISCOVERY_SERVICE:
                            instances.add(target)
                    elif record_type == 33 and len(data) >= 6:
                        _, _, port = struct.unpack("!HHH", data[:6])
                        target, _ = _read_dns_name(packet, data_offset + 6)
                        services[name] = (target, port)
                    elif record_type == 16:
                        fields: dict[str, str] = {}
                        cursor = 0
                        while cursor < len(data):
                            size = data[cursor]
                            cursor += 1
                            if cursor + size > len(data):
                                raise RuntimeError("discovery_txt_truncated")
                            item = data[cursor : cursor + size].decode("utf-8")
                            cursor += size
                            key, separator, value = item.partition("=")
                            if separator and key not in fields:
                                fields[key] = value
                        attributes[name] = fields
                    elif record_type in (1, 28):
                        family = socket.AF_INET if record_type == 1 else socket.AF_INET6
                        address = socket.inet_ntop(family, data)
                        parsed_address = ipaddress.ip_address(address)
                        if (
                            parsed_address.is_private
                            or parsed_address.is_link_local
                            or parsed_address.is_loopback
                        ):
                            addresses.setdefault(name, set()).add(address)
            except (RuntimeError, UnicodeDecodeError, OSError, ValueError):
                continue
    discovered: list[dict[str, Any]] = []
    for instance in sorted(instances):
        target_port = services.get(instance)
        txt = attributes.get(instance, {})
        if (
            not target_port
            or txt.get("protocol") != "trusted_local_http_v1"
            or txt.get("access") not in {"paired", "open_lan_insecure"}
            or txt.get("confidentiality") != "none"
            or txt.get("path") != "/"
        ):
            continue
        target, port = target_port
        candidates = sorted(addresses.get(target, set()), key=lambda item: ":" in item)
        host = candidates[0] if candidates else target.rstrip(".")
        host_literal = f"[{host}]" if ":" in host else host
        discovered.append(
            {
                "service_name": instance,
                "origin": f"http://{host_literal}:{port}",
                "access_mode": txt["access"],
                "confidentiality": "none",
                "path": "/",
            }
        )
    return {
        "schema": "rusty.hostess.trusted_local_control_discovery.v1",
        "status": "passed" if discovered else "not_found",
        "service_type": DISCOVERY_SERVICE,
        "services": discovered,
    }


def request_session(origin: str, mode: str, pairing_code: str | None) -> dict[str, Any]:
    parsed = urlsplit(origin)
    if parsed.scheme != "http" or parsed.path not in ("", "/") or parsed.username or parsed.password:
        raise RuntimeError("origin_not_plain_http_root")
    if not parsed.hostname or not parsed.port:
        raise RuntimeError("origin_missing_host_or_port")
    if mode == "paired":
        if not pairing_code or not re.fullmatch(r"[0-9]{6}", pairing_code):
            raise RuntimeError("paired_mode_code_missing")
        path = "/v1/pair"
        body = canonical_json(
            {"pairing_code": pairing_code, "request_id": new_request_id("hostess-pair")}
        )
    elif mode == "open_lan_insecure":
        path = "/v1/open-session"
        body = canonical_json({"request_id": new_request_id("hostess-open")})
    else:
        raise RuntimeError("access_mode_not_supported")
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
    connection.request(
        "POST",
        path,
        body=body.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Origin": origin,
            "Host": parsed.netloc,
        },
    )
    response = connection.getresponse()
    payload = response.read(4097)
    cookie = response.getheader("Set-Cookie")
    connection.close()
    if len(payload) > 4096:
        raise RuntimeError("session_response_too_large")
    try:
        result = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("session_response_invalid") from error
    if response.status != 200 or result.get("session_admitted") is not True:
        raise RuntimeError(f"session_rejected:{result.get('error', response.status)}")
    if not cookie or not cookie.startswith("rq_session="):
        raise RuntimeError("session_cookie_missing")
    return {"body": result, "cookie": cookie.split(";", 1)[0]}


@dataclass
class WebSocketClient:
    sock: socket.socket

    @classmethod
    def connect(cls, origin: str, cookie: str) -> "WebSocketClient":
        parsed = urlsplit(origin)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        sock = socket.create_connection((parsed.hostname, parsed.port), timeout=5)
        request = (
            "GET /v1/events HTTP/1.1\r\n"
            f"Host: {parsed.netloc}\r\n"
            f"Origin: {origin}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Cookie: {cookie}\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = cls._read_http_head(sock)
        lines = response.split("\r\n")
        if lines[0] != "HTTP/1.1 101 Switching Protocols":
            sock.close()
            raise RuntimeError(f"websocket_upgrade_rejected:{lines[0]}")
        headers = {
            name.strip().lower(): value.strip()
            for name, value in (line.split(":", 1) for line in lines[1:] if ":" in line)
        }
        expected = base64.b64encode(hashlib.sha1((key + WS_GUID).encode("ascii")).digest()).decode(
            "ascii"
        )
        if headers.get("sec-websocket-accept") != expected:
            sock.close()
            raise RuntimeError("websocket_accept_mismatch")
        return cls(sock)

    @staticmethod
    def _read_http_head(sock: socket.socket) -> str:
        data = bytearray()
        while not data.endswith(b"\r\n\r\n"):
            chunk = sock.recv(1)
            if not chunk:
                raise RuntimeError("websocket_upgrade_eof")
            data.extend(chunk)
            if len(data) > 8192:
                raise RuntimeError("websocket_upgrade_too_large")
        return data[:-4].decode("ascii")

    def send_json(self, value: dict[str, Any]) -> None:
        payload = canonical_json(value).encode("utf-8")
        if len(payload) > 4096:
            raise RuntimeError("websocket_command_too_large")
        mask = os.urandom(4)
        if len(payload) < 126:
            head = bytes((0x81, 0x80 | len(payload)))
        else:
            head = bytes((0x81, 0x80 | 126)) + struct.pack("!H", len(payload))
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.sock.sendall(head + mask + masked)

    def read_json(self, timeout: float = 6.0) -> dict[str, Any]:
        self.sock.settimeout(timeout)
        while True:
            first, second = self._read_exact(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if second & 0x80:
                raise RuntimeError("masked_server_frame_rejected")
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                raise RuntimeError("large_server_frame_rejected")
            if length > 4096:
                raise RuntimeError("server_frame_too_large")
            payload = self._read_exact(length)
            if opcode == 0x8:
                raise RuntimeError("websocket_closed")
            if opcode == 0x9:
                self._send_control(0xA, payload)
                continue
            if opcode != 0x1:
                continue
            return json.loads(payload.decode("utf-8"))

    def _send_control(self, opcode: int, payload: bytes) -> None:
        mask = os.urandom(4)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.sock.sendall(bytes((0x80 | opcode, 0x80 | len(payload))) + mask + masked)

    def _read_exact(self, length: int) -> bytes:
        data = bytearray()
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                raise RuntimeError("websocket_eof")
            data.extend(chunk)
        return bytes(data)

    def close(self) -> None:
        try:
            self._send_control(0x8, struct.pack("!H", 1000))
        except OSError:
            pass
        self.sock.close()


class MediaSequence:
    def __init__(self, socket_client: WebSocketClient, admission: dict[str, Any]) -> None:
        self.socket = socket_client
        self.authority_revision = int(admission["authority_revision"])
        self.player_revision = 0
        self.events: list[dict[str, Any]] = []

    def _observe(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        authority = event.get("authority_revision")
        if isinstance(authority, int):
            self.authority_revision = authority
        candidates = [
            event.get("player_revision"),
            (event.get("state") or {}).get("revision"),
            ((event.get("state") or {}).get("player") or {}).get("revision"),
        ]
        for candidate in candidates:
            if isinstance(candidate, int):
                self.player_revision = candidate

    def command(self, command: str, video_id: str | None = None) -> list[dict[str, Any]]:
        request_id = new_request_id(f"hostess-{command.replace('_', '-')}")
        payload: dict[str, Any] = {} if video_id is None else {"video_id": video_id}
        self.socket.send_json(
            {
                "command": command,
                "expected_authority_revision": self.authority_revision,
                "expected_player_revision": self.player_revision,
                "payload": payload,
                "request_id": request_id,
            }
        )
        terminal = {"command_result"} if command in {"describe", "get_state", "list_videos"} else {
            "command_applied",
            "command_failed",
            "command_not_submitted",
            "command_rejected",
        }
        observed: list[dict[str, Any]] = []
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            event = self.socket.read_json(max(0.2, deadline - time.monotonic()))
            self._observe(event)
            observed.append(event)
            if event.get("request_id") == request_id and event.get("event") in terminal:
                if event.get("event") not in {"command_result", "command_applied"}:
                    reason = event.get("reason", "unspecified")
                    raise RuntimeError(
                        f"command_failed:{command}:{event.get('event')}:{reason}"
                    )
                return observed
        raise RuntimeError(f"command_timeout:{command}")


def select_video_descriptor(
    videos: list[dict[str, Any]], initial_video_id: str | None, requested_video_id: str | None
) -> dict[str, Any]:
    if requested_video_id is not None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,47}", requested_video_id):
            raise ValueError("video_id_invalid")
        selected = next(
            (video for video in videos if video.get("video_id") == requested_video_id), None
        )
        if selected is None:
            raise RuntimeError("video_id_not_advertised")
        if requested_video_id == initial_video_id:
            raise RuntimeError("video_id_already_selected")
        return selected
    return next(
        video for video in videos if video.get("video_id") != initial_video_id
    )


def run_media_sequence(
    serial: str, mode: str, requested_video_ids: list[str] | None = None
) -> dict[str, Any]:
    requests: list[str | None] = list(requested_video_ids or [None])
    if not requests or len(requests) > MAX_MEDIA_PROFILES_PER_SESSION:
        raise ValueError("video_test_batch_out_of_bounds")
    provider_method = "enable_paired" if mode == "paired" else "enable_open_lan"
    enabled = invoke_provider(serial, provider_method)
    if enabled.get("confirmed") is not True:
        raise RuntimeError(f"enable_not_confirmed:{enabled.get('reason', enabled.get('phase'))}")
    origin = enabled.get("origin")
    if not isinstance(origin, str):
        raise RuntimeError("listener_origin_missing")
    try:
        session = request_session(origin, mode, enabled.get("pairing_code"))
        websocket = WebSocketClient.connect(origin, session["cookie"])
        sequence = MediaSequence(websocket, session["body"])
        try:
            sequence.command("describe")
            state_events = sequence.command("get_state")
            state_result = next(
                event
                for event in reversed(state_events)
                if event.get("event") == "command_result" and event.get("command") == "get_state"
            )
            initial_player = (state_result.get("state") or {}).get("player") or {}
            initial_selected_id = initial_player.get("selected_video_id")
            if initial_player.get("playing"):
                sequence.command("pause")
            video_events = sequence.command("list_videos")
            listing = next(
                event
                for event in reversed(video_events)
                if event.get("event") == "command_result" and event.get("command") == "list_videos"
            )
            videos = listing.get("videos") or []
            if len(videos) < 2:
                raise RuntimeError("bundled_video_catalog_incomplete")
            tested_videos: list[dict[str, Any]] = []
            final: dict[str, Any] = initial_player
            current_selected_id = initial_selected_id
            for requested_video_id in requests:
                selected_video = select_video_descriptor(
                    videos, current_selected_id, requested_video_id
                )
                selected_id = selected_video["video_id"]
                select_events = sequence.command("select_video", selected_id)
                select_applied = select_events[-1]
                if (select_applied.get("state") or {}).get("selected_video_id") != selected_id:
                    raise RuntimeError("select_video_effect_not_observed")
                play_events = sequence.command("play")
                if not (play_events[-1].get("state") or {}).get("playing"):
                    raise RuntimeError("play_effect_not_observed")
                time.sleep(0.25)
                pause_events = sequence.command("pause")
                final = pause_events[-1].get("state") or {}
                if final.get("playing"):
                    raise RuntimeError("pause_effect_not_observed")
                tested_videos.append(
                    {
                        key: selected_video.get(key)
                        for key in (
                            "video_id",
                            "title",
                            "projection_shape",
                            "stereo_layout",
                            "width_px",
                            "height_px",
                            "source_kind",
                            "license",
                        )
                    }
                )
                current_selected_id = selected_id
            return {
                "schema": "rusty.hostess.trusted_local_control_device_run.v1",
                "status": "passed",
                "access_mode": mode,
                "admission_receipt_id": session["body"].get("admission_receipt_id"),
                "controller_lease_id": session["body"].get("controller_lease_id"),
                "selected_video_id": final.get("selected_video_id", current_selected_id),
                "tested_videos": tested_videos,
                "playing": final.get("playing", False),
                "position_ms": final.get("position_ms"),
                "authority_revision": sequence.authority_revision,
                "player_revision": sequence.player_revision,
                "command_accepted_events": sum(
                    event.get("event") == "command_accepted" for event in sequence.events
                ),
                "command_applied_events": sum(
                    event.get("event") == "command_applied" for event in sequence.events
                ),
                "pairing_code_retained": False,
            }
        finally:
            websocket.close()
    finally:
        failure_in_flight = sys.exc_info()[0] is not None
        try:
            revoked = invoke_provider(serial, "revoke")
            if revoked.get("confirmed") is not True and not failure_in_flight:
                raise RuntimeError("post_test_revoke_not_confirmed")
        except (OSError, ValueError, RuntimeError, socket.timeout):
            if not failure_in_flight:
                raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--serial", help="Exact ADB-authorized USB serial")
    result.add_argument(
        "--show-pairing-code",
        action="store_true",
        help="Print the debug-only pairing code instead of redacting it",
    )
    sub = result.add_subparsers(dest="action", required=True)
    for action in ("status", "enable-paired", "enable-open-lan", "revoke"):
        sub.add_parser(action)
    media = sub.add_parser("test-media")
    media.add_argument("--mode", choices=("paired", "open_lan_insecure"), default="paired")
    media.add_argument(
        "--video-id",
        action="append",
        help="Select an exact advertised video id; repeat at most five times",
    )
    discovery = sub.add_parser("discover")
    discovery.add_argument("--timeout-seconds", type=float, default=3.0)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action == "discover":
            result = discover_services(args.timeout_seconds)
        elif not args.serial:
            raise ValueError("serial_is_required_for_adb_actions")
        elif args.action == "test-media":
            result = run_media_sequence(args.serial, args.mode, args.video_id)
        else:
            method = args.action.replace("-", "_")
            result = redact(invoke_provider(args.serial, method), args.show_pairing_code)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("confirmed", True) else 2
    except (OSError, ValueError, RuntimeError, socket.timeout) as error:
        print(
            json.dumps(
                {
                    "schema": "rusty.hostess.trusted_local_control_cli_error.v1",
                    "status": "failed",
                    "reason": str(error),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
