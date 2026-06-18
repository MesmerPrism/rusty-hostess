"""Quest questionnaire bridge routes for hostessctl."""

from __future__ import annotations

import argparse
import json
import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import error, request
from urllib.parse import urljoin


OPERATOR_PROTOCOL_VERSION = "quest.questionnaire.operator.v1"
PANEL_PROTOCOL_VERSION = "quest.questionnaire.v1"
STUDY_ID = "maia-spatial"
SCHEMA_ID = "maia2-spatial-frame-questionnaire-v1"
DEFAULT_BRIDGE_ENDPOINT = "http://127.0.0.1:8787"
STATUS_PATH = "/v1/status"
COMMAND_PATH = "/v1/command"

BLOCK_SPECS: dict[str, dict[str, Any]] = {
    "1": {
        "command_name": "maia_spatial.block1",
        "label": "Block 1",
        "open_stage": "maia_spatial:language_selection",
        "screen_sequence": [
            "maia_spatial:language_selection",
            "maia_spatial:demographics",
            "maia_spatial:maia2",
        ],
    },
    "2": {
        "command_name": "maia_spatial.block2",
        "label": "Block 2",
        "open_stage": "maia_spatial:spatial_frame_reference_1",
        "screen_sequence": ["maia_spatial:spatial_frame_reference_1"],
    },
    "3": {
        "command_name": "maia_spatial.block3",
        "label": "Block 3",
        "open_stage": "maia_spatial:spatial_frame_reference_2",
        "screen_sequence": ["maia_spatial:spatial_frame_reference_2"],
    },
}


@dataclass
class QuestionnaireBridgeState:
    """Mutable low-rate bridge state for development and smoke tests."""

    bridge_app: str = "rusty-hostess-questionnaire-bridge"
    bridge_version: str = "0.1.0"
    device_label: str = "local-dev"
    xr_package: str = "rusty-morphospace.xr"
    xr_activity: str = ".MainActivity"
    panel_package: str = "io.github.mesmerprism.questquestionnaire"
    panel_activity: str = ".QuestionnairePanelActivity"
    protocol_version: str = OPERATOR_PROTOCOL_VERSION
    request_count: int = 0
    panel_foreground: bool = False
    last_open_stage: str | None = None
    last_questionnaire_id: str | None = None
    last_command: dict[str, Any] | None = None
    last_result: dict[str, Any] | None = None
    command_log: list[dict[str, Any]] = field(default_factory=list)

    def status_response(self, message: str = "Questionnaire bridge ready.") -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "bridge": {
                "app": self.bridge_app,
                "version": self.bridge_version,
                "device_label": self.device_label,
            },
            "foreground": {
                "xr_app_foreground": not self.panel_foreground,
                "panel_foreground": self.panel_foreground,
                "foreground_package": self.panel_package if self.panel_foreground else self.xr_package,
                "foreground_activity": (
                    self.panel_activity if self.panel_foreground else self.xr_activity
                ),
                "questionnaire_id": self.last_questionnaire_id,
                "open_stage": self.last_open_stage,
            },
            "last_command": self.last_command,
            "last_result": self.last_result,
            "message": message,
        }

    def apply_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = payload.get("action")
        command_id = str(payload.get("command_id") or "")
        command_name = str(payload.get("command_name") or "")
        panel_request = payload.get("panel_request") if isinstance(payload, dict) else None
        if payload.get("protocol_version") != OPERATOR_PROTOCOL_VERSION:
            return self.command_response(
                accepted=False,
                command_id=command_id,
                command_name=command_name,
                message="Unsupported operator protocol version.",
            )
        if action == "open_questionnaire":
            if not isinstance(panel_request, dict):
                return self.command_response(
                    accepted=False,
                    command_id=command_id,
                    command_name=command_name,
                    message="Open command is missing panel_request.",
                )
            open_stage = panel_request.get("open_stage")
            if not isinstance(open_stage, str) or not open_stage:
                return self.command_response(
                    accepted=False,
                    command_id=command_id,
                    command_name=command_name,
                    message="Open command is missing open_stage.",
                )
            self.panel_foreground = True
            self.last_open_stage = open_stage
            self.last_questionnaire_id = str(panel_request.get("schema_id") or SCHEMA_ID)
            self.last_result = {
                "request_id": command_id,
                "session_id": panel_request.get("session_id"),
                "status": "foreground",
                "open_stage": open_stage,
            }
            return self.command_response(
                accepted=True,
                command_id=command_id,
                command_name=command_name,
                message=f"Foreground request accepted for {open_stage}.",
            )
        if action == "dismiss_questionnaire":
            session_id = panel_request.get("session_id") if isinstance(panel_request, dict) else None
            self.panel_foreground = False
            self.last_result = {
                "request_id": command_id,
                "session_id": session_id,
                "status": "dismissed",
                "open_stage": self.last_open_stage,
            }
            return self.command_response(
                accepted=True,
                command_id=command_id,
                command_name=command_name,
                message="Dismiss request accepted.",
            )
        return self.command_response(
            accepted=False,
            command_id=command_id,
            command_name=command_name,
            message=f"Unsupported questionnaire action: {action!r}.",
        )

    def command_response(
        self,
        *,
        accepted: bool,
        command_id: str,
        command_name: str,
        message: str,
    ) -> dict[str, Any]:
        self.last_command = {
            "command_id": command_id or None,
            "command_name": command_name or None,
            "accepted": accepted,
            "message": message,
        }
        self.command_log.append(dict(self.last_command))
        foreground = self.status_response(message=message)["foreground"]
        return {
            "protocol_version": self.protocol_version,
            "accepted": accepted,
            "message": message,
            "foreground": foreground,
            "last_result": self.last_result,
        }


class QuestionnaireBridgeServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        state: QuestionnaireBridgeState,
        max_requests: int | None = None,
    ) -> None:
        super().__init__(server_address, QuestionnaireBridgeHandler)
        self.state = state
        self.max_requests = max_requests
        self._served_requests = 0

    def mark_request_served(self) -> None:
        self._served_requests += 1
        if self.max_requests is not None and self._served_requests >= self.max_requests:
            threading.Thread(target=self.shutdown, daemon=True).start()


class QuestionnaireBridgeHandler(BaseHTTPRequestHandler):
    server: QuestionnaireBridgeServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path != STATUS_PATH:
            self.write_json(HTTPStatus.NOT_FOUND, {"message": "Unknown bridge route."})
            return
        self.write_json(HTTPStatus.OK, self.server.state.status_response())

    def do_POST(self) -> None:
        if self.path != COMMAND_PATH:
            self.write_json(HTTPStatus.NOT_FOUND, {"message": "Unknown bridge route."})
            return
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.write_json(HTTPStatus.BAD_REQUEST, {"message": str(exc)})
            return
        response = self.server.state.apply_command(payload)
        status = HTTPStatus.OK if response.get("accepted") else HTTPStatus.BAD_REQUEST
        self.write_json(status, response)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Request body is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.server.mark_request_served()


def build_open_block_command(
    *,
    block: str,
    command_id: str,
    session_id: str,
    participant_ref: str,
    language_code: str,
) -> dict[str, Any]:
    spec = block_spec(block)
    language = language_code.strip() or "en"
    return {
        "protocol_version": OPERATOR_PROTOCOL_VERSION,
        "command_id": command_id,
        "action": "open_questionnaire",
        "command_name": spec["command_name"],
        "panel_request": {
            "protocol_version": PANEL_PROTOCOL_VERSION,
            "session_id": session_id,
            "study_id": STUDY_ID,
            "schema_id": SCHEMA_ID,
            "open_stage": spec["open_stage"],
            "screen_sequence": list(spec["screen_sequence"]),
            "participant_ref": participant_ref,
            "questionnaire_state": {"language_code": language},
            "caller_hint": {
                "engine": "rusty-morphospace",
                "transport": "hostessctl-questionnaire-bridge",
            },
        },
    }


def build_dismiss_command(*, command_id: str, session_id: str) -> dict[str, Any]:
    return {
        "protocol_version": OPERATOR_PROTOCOL_VERSION,
        "command_id": command_id,
        "action": "dismiss_questionnaire",
        "command_name": "questionnaire.dismiss",
        "panel_request": {
            "protocol_version": PANEL_PROTOCOL_VERSION,
            "session_id": session_id,
            "study_id": STUDY_ID,
            "schema_id": SCHEMA_ID,
            "open_stage": "",
            "screen_sequence": [],
            "participant_ref": "",
            "questionnaire_state": {"language_code": "en"},
            "caller_hint": {
                "engine": "rusty-morphospace",
                "transport": "hostessctl-questionnaire-bridge",
            },
        },
    }


def block_spec(block: str) -> dict[str, Any]:
    normalized = str(block).strip().lower().removeprefix("block")
    try:
        return BLOCK_SPECS[normalized]
    except KeyError:
        raise SystemExit(f"Unknown questionnaire block: {block}") from None


def get_json(endpoint: str, path: str) -> dict[str, Any]:
    url = endpoint_url(endpoint, path)
    with request.urlopen(url, timeout=10.0) as response:
        return read_json_response(response.read())


def post_json(endpoint: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = endpoint_url(endpoint, path)
    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(http_request, timeout=10.0) as response:
            return read_json_response(response.read())
    except error.HTTPError as exc:
        payload = read_json_response(exc.read())
        raise SystemExit(json.dumps(payload, indent=2, sort_keys=True)) from exc


def read_json_response(body: bytes) -> dict[str, Any]:
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Bridge response must be a JSON object.")
    return payload


def endpoint_url(endpoint: str, path: str) -> str:
    base = endpoint.strip().rstrip("/") + "/"
    if not base.startswith(("http://", "https://")):
        raise SystemExit("Bridge endpoint must start with http:// or https://")
    return urljoin(base, path.lstrip("/"))


def questionnaire_status(args: argparse.Namespace) -> int:
    print_json(get_json(args.endpoint, STATUS_PATH))
    return 0


def questionnaire_open_block(args: argparse.Namespace) -> int:
    payload = build_open_block_command(
        block=args.block,
        command_id=args.command_id,
        session_id=args.session_id,
        participant_ref=args.participant_ref,
        language_code=args.language_code,
    )
    print_json(post_json(args.endpoint, COMMAND_PATH, payload))
    return 0


def questionnaire_dismiss(args: argparse.Namespace) -> int:
    payload = build_dismiss_command(
        command_id=args.command_id,
        session_id=args.session_id,
    )
    print_json(post_json(args.endpoint, COMMAND_PATH, payload))
    return 0


def questionnaire_serve(args: argparse.Namespace) -> int:
    state = QuestionnaireBridgeState(
        device_label=args.device_label,
        xr_package=args.xr_package,
        xr_activity=args.xr_activity,
        panel_package=args.panel_package,
        panel_activity=args.panel_activity,
    )
    server = QuestionnaireBridgeServer((args.host, args.port), state, args.max_requests)
    bound_host, bound_port = server.server_address
    print_json(
        {
            "protocol_version": OPERATOR_PROTOCOL_VERSION,
            "bridge": {
                "app": state.bridge_app,
                "version": state.bridge_version,
                "endpoint": f"http://{bound_host}:{bound_port}",
            },
            "message": "Questionnaire bridge listening.",
        }
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))

