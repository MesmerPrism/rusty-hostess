"""Deterministic, non-production authority/effect fixtures.

``FixtureManifoldPort`` supplies synthetic receipts with Manifold ownership
labels. It is deliberately app-local and non-persistent; product code must
adapt to the real Manifold authority instead of importing this oracle.
"""

from __future__ import annotations

import json
import queue
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract import COMMANDS, build_descriptor, canonical_json_bytes


_REQUEST_ID = re.compile(r"^[a-z0-9][a-z0-9-]{15,63}$")
_CONTROLLER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,39}$")
_MUTATING_COMMANDS = frozenset(("select_video", "play", "pause"))
_QUERY_COMMANDS = frozenset(("describe", "get_state", "list_videos"))


class FakeClock:
    def __init__(self, initial: float = 1_000.0) -> None:
        self._now = float(initial)

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("clock cannot move backwards")
        self._now += float(seconds)


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    provenance: str

    def as_dict(self) -> dict[str, str]:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "provenance": self.provenance,
        }


class FakePlayer:
    """Callback-driven stand-in for the Quest-owned Media3 player."""

    def __init__(self) -> None:
        self.videos = (
            Video("synthetic-blue", "Synthetic blue field", "generated-test-media"),
            Video("synthetic-grid", "Synthetic calibration grid", "generated-test-media"),
        )
        self.selected_video_id = self.videos[0].video_id
        self.playing = False
        self._pending: deque[dict[str, Any]] = deque()

    def prepare(self, *, command: str, params: dict[str, Any], causality: dict[str, Any]) -> None:
        if command not in _MUTATING_COMMANDS:
            raise ValueError("fake player only accepts effect commands")
        self._pending.append(
            {
                "command": command,
                "params": dict(params),
                "causality": dict(causality),
            }
        )

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def apply_next(self) -> dict[str, Any] | None:
        if not self._pending:
            return None
        action = self._pending.popleft()
        command = action["command"]
        if command == "select_video":
            self.selected_video_id = action["params"]["video_id"]
        elif command == "play":
            self.playing = True
        elif command == "pause":
            self.playing = False
        return {
            "callback_source": "fake_player_effect_callback",
            "command": command,
            "causality": action["causality"],
        }


class FixtureManifoldPort:
    """Synthetic receipt supplier for the Manifold boundary.

    The state machine is only a deterministic conformance oracle. It does not
    persist, listen on a socket, or provide a product authority implementation.
    """

    def __init__(
        self,
        clock: FakeClock,
        *,
        pairing_code: str = "731905",
        listener_window_seconds: float = 120.0,
        session_window_seconds: float = 90.0,
        idle_window_seconds: float = 30.0,
        rate_limit_count: int = 8,
        rate_window_seconds: float = 10.0,
        receipt_fixture_path: Path | None = None,
    ) -> None:
        if not pairing_code.isdigit() or len(pairing_code) != 6:
            raise ValueError("synthetic pairing code must be exactly six digits")
        self.clock = clock
        self.pairing_code = pairing_code
        self.listener_window_seconds = listener_window_seconds
        self.session_window_seconds = session_window_seconds
        self.idle_window_seconds = idle_window_seconds
        self.rate_limit_count = rate_limit_count
        self.rate_window_seconds = rate_window_seconds
        self.templates = self._load_templates(receipt_fixture_path)
        self.enabled_until: float | None = None
        self.pairing_code_used = False
        self.controller_id: str | None = None
        self.session_token: str | None = None
        self.session_expires_at: float | None = None
        self.idle_expires_at: float | None = None
        self.authority_revision = 0
        self.request_ids: set[str] = set()
        self.pair_request_ids: set[str] = set()
        self._request_times: deque[float] = deque()

    @staticmethod
    def _load_templates(path: Path | None) -> dict[str, dict[str, str]]:
        if path is None:
            path = (
                Path(__file__).resolve().parents[1]
                / "fixtures"
                / "manifold-fixture-receipts.json"
            )
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if (
            fixture.get("schema")
            != "rusty.hostess.trusted_local_control.manifold_fixture_receipts.v1"
            or fixture.get("synthetic") is not True
            or fixture.get("source_authority") != "rusty.manifold"
        ):
            raise ValueError("invalid synthetic Manifold receipt fixture")
        templates = fixture.get("templates")
        if not isinstance(templates, dict):
            raise ValueError("fixture templates missing")
        return templates

    @property
    def enabled(self) -> bool:
        return self.enabled_until is not None and self.clock() < self.enabled_until

    def _receipt(self, template: str, **fields: Any) -> dict[str, Any]:
        self.authority_revision += 1
        return {
            **self.templates[template],
            "source_authority": "rusty.manifold",
            "synthetic_fixture": True,
            "authority_revision": self.authority_revision,
            **fields,
        }

    def wearer_enable(self, *, foreground: bool, wearer_confirmed: bool) -> dict[str, Any]:
        if not foreground or not wearer_confirmed:
            return self._receipt("pair_rejected", reason="wearer_opt_in_required")
        now = self.clock()
        self.enabled_until = now + self.listener_window_seconds
        self.pairing_code_used = False
        self.controller_id = None
        self.session_token = None
        self.session_expires_at = None
        self.idle_expires_at = None
        self.request_ids.clear()
        self.pair_request_ids.clear()
        self._request_times.clear()
        return self._receipt(
            "listener_enabled",
            enabled_until=self.enabled_until,
            foreground=True,
            pairing_code_delivery="on_headset_only",
        )

    def pair(
        self,
        pairing_code: str,
        request_id: str,
        controller_id: str = "windows-browser",
    ) -> dict[str, Any]:
        expiry = self.sweep_expiry()
        if expiry is not None:
            return self._receipt("pair_rejected", reason="listener_expired")
        if not self.enabled:
            return self._receipt("pair_rejected", reason="listener_disabled")
        if not _CONTROLLER_ID.fullmatch(controller_id):
            return self._receipt("pair_rejected", reason="invalid_controller_id")
        if not _REQUEST_ID.fullmatch(request_id):
            return self._receipt("pair_rejected", reason="invalid_request_id")
        if request_id in self.pair_request_ids:
            return self._receipt("pair_rejected", reason="request_replay")
        self.pair_request_ids.add(request_id)
        if self.controller_id is not None:
            return self._receipt("pair_rejected", reason="controller_lease_occupied")
        if self.pairing_code_used:
            return self._receipt("pair_rejected", reason="pairing_code_consumed")
        if pairing_code != self.pairing_code:
            return self._receipt("pair_rejected", reason="pairing_code_invalid")

        now = self.clock()
        self.pairing_code_used = True
        self.controller_id = controller_id
        self.session_token = f"synthetic-session-token-{self.authority_revision + 1:016d}"
        self.session_expires_at = min(
            now + self.session_window_seconds,
            self.enabled_until if self.enabled_until is not None else now,
        )
        self.idle_expires_at = min(
            now + self.idle_window_seconds,
            self.session_expires_at,
        )
        return self._receipt(
            "pair_accepted",
            controller_id=controller_id,
            session_expires_at=self.session_expires_at,
            idle_expires_at=self.idle_expires_at,
            controller_limit=1,
        )

    def review_command(
        self,
        *,
        session_token: str,
        request_id: str,
        command: str,
        expected_authority_revision: int,
        expected_player_revision: int,
        current_effect_revision: int,
    ) -> dict[str, Any]:
        expiry = self.sweep_expiry()
        if expiry is not None:
            return self._receipt(
                "command_rejected",
                request_id=request_id,
                command=command,
                reason=expiry["reason"],
            )
        if not self.enabled:
            return self._receipt(
                "command_rejected",
                request_id=request_id,
                command=command,
                reason="listener_disabled",
            )
        if self.session_token is None or session_token != self.session_token:
            return self._receipt(
                "command_rejected",
                request_id=request_id,
                command=command,
                reason="session_invalid",
            )
        if request_id in self.request_ids:
            return self._receipt(
                "command_rejected",
                request_id=request_id,
                command=command,
                reason="request_replay",
            )

        self.request_ids.add(request_id)
        now = self.clock()
        while self._request_times and self._request_times[0] <= now - self.rate_window_seconds:
            self._request_times.popleft()
        if len(self._request_times) >= self.rate_limit_count:
            return self._receipt(
                "command_rejected",
                request_id=request_id,
                command=command,
                reason="rate_limited",
            )
        self._request_times.append(now)

        if expected_authority_revision != self.authority_revision:
            return self._receipt(
                "command_rejected",
                request_id=request_id,
                command=command,
                reason="stale_expected_authority_revision",
                expected_authority_revision=expected_authority_revision,
            )
        if expected_player_revision != current_effect_revision:
            return self._receipt(
                "command_rejected",
                request_id=request_id,
                command=command,
                reason="stale_expected_player_revision",
                expected_player_revision=expected_player_revision,
                current_effect_revision=current_effect_revision,
            )

        self.idle_expires_at = min(
            now + self.idle_window_seconds,
            self.session_expires_at if self.session_expires_at is not None else now,
        )
        return self._receipt(
            "command_accepted",
            request_id=request_id,
            command=command,
            expected_authority_revision=expected_authority_revision,
            expected_player_revision=expected_player_revision,
            controller_id=self.controller_id,
            lease="single_controller",
        )

    def wearer_revoke(self) -> dict[str, Any]:
        controller_id = self.controller_id
        self._clear_controller()
        return self._receipt(
            "controller_revoked",
            controller_id=controller_id,
            reason="wearer_revoke",
        )

    def sweep_expiry(self) -> dict[str, Any] | None:
        now = self.clock()
        reason: str | None = None
        if self.enabled_until is not None and now >= self.enabled_until:
            reason = "listener_expired"
            self.enabled_until = None
        elif self.session_expires_at is not None and now >= self.session_expires_at:
            reason = "session_expired"
        elif self.idle_expires_at is not None and now >= self.idle_expires_at:
            reason = "idle_expired"
        if reason is None:
            return None
        controller_id = self.controller_id
        self._clear_controller()
        return self._receipt(
            "session_expired",
            controller_id=controller_id,
            reason=reason,
        )

    def _clear_controller(self) -> None:
        self.controller_id = None
        self.session_token = None
        self.session_expires_at = None
        self.idle_expires_at = None
        self._request_times.clear()

    def controller_state(self) -> dict[str, Any]:
        return {
            "listener_enabled": self.enabled,
            "controller_id": self.controller_id,
            "one_controller_limit": True,
            "session_expires_at": self.session_expires_at,
            "idle_expires_at": self.idle_expires_at,
            "wearer_revoke_available": self.controller_id is not None,
            "authority_revision": self.authority_revision,
        }


class TrustedLocalControlFixture:
    """Protocol-compatible fake adapter with explicit authority/effect ports."""

    def __init__(
        self,
        *,
        clock: FakeClock | None = None,
        authority: FixtureManifoldPort | None = None,
        player: FakePlayer | None = None,
    ) -> None:
        self.clock = clock or FakeClock()
        self.authority = authority or FixtureManifoldPort(self.clock)
        self.player = player or FakePlayer()
        self.state_revision = 0
        self._subscribers: list[queue.Queue[dict[str, Any]]] = []
        self.event_history: list[dict[str, Any]] = []

    @property
    def pairing_code(self) -> str:
        return self.authority.pairing_code

    @property
    def session_token(self) -> str | None:
        return self.authority.session_token

    def wearer_enable(self, *, foreground: bool = True, wearer_confirmed: bool = True) -> dict[str, Any]:
        receipt = self.authority.wearer_enable(
            foreground=foreground,
            wearer_confirmed=wearer_confirmed,
        )
        self._emit({"event": "listener_enabled", **receipt})
        return receipt

    def pair(
        self,
        *,
        pairing_code: str,
        request_id: str,
        controller_id: str = "windows-browser",
    ) -> dict[str, Any]:
        receipt = self.authority.pair(pairing_code, request_id, controller_id)
        event = dict(receipt)
        event["event"] = (
            "controller_paired"
            if receipt.get("decision") == "accepted"
            else "pairing_rejected"
        )
        self._emit(event)
        return {
            **receipt,
            "state": self.state(),
            "controller_state": self.authority.controller_state(),
        }

    def wearer_revoke(self) -> dict[str, Any]:
        receipt = self.authority.wearer_revoke()
        self._emit({"event": "controller_revoked", **receipt})
        return receipt

    def sweep_expiry(self) -> dict[str, Any] | None:
        receipt = self.authority.sweep_expiry()
        if receipt is not None:
            self._emit({"event": "session_expired", **receipt})
        return receipt

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        subscriber: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=64)
        self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[dict[str, Any]]) -> None:
        try:
            self._subscribers.remove(subscriber)
        except ValueError:
            pass

    def _emit(self, event: dict[str, Any]) -> None:
        self.event_history.append(event)
        for subscriber in tuple(self._subscribers):
            try:
                subscriber.put_nowait(event)
            except queue.Full:
                self.unsubscribe(subscriber)

    def state(self) -> dict[str, Any]:
        return {
            "playback_state": "playing" if self.player.playing else "paused",
            "playing": self.player.playing,
            "position_ms": 0,
            "revision": self.state_revision,
            "selected_video_id": self.player.selected_video_id,
        }

    def list_videos(self) -> list[dict[str, str]]:
        return [video.as_dict() for video in self.player.videos]

    def handle_command(self, *, session_token: str, envelope: Any) -> dict[str, Any]:
        issue = self._validate_command_envelope(envelope)
        if issue is not None:
            event = {
                "accepted": False,
                "event": "command_rejected",
                "reason": issue,
            }
            if isinstance(envelope, dict) and isinstance(envelope.get("request_id"), str):
                event["request_id"] = envelope["request_id"]
            if isinstance(envelope, dict) and isinstance(envelope.get("command"), str):
                event["command"] = envelope["command"]
            self._emit(dict(event))
            return event

        request_id = envelope["request_id"]
        command = envelope["command"]
        expected_authority_revision = envelope["expected_authority_revision"]
        expected_player_revision = envelope["expected_player_revision"]
        receipt = self.authority.review_command(
            session_token=session_token,
            request_id=request_id,
            command=command,
            expected_authority_revision=expected_authority_revision,
            expected_player_revision=expected_player_revision,
            current_effect_revision=self.state_revision,
        )
        if receipt.get("decision") != "accepted":
            event = {"event": "command_rejected", **receipt}
            self._emit(event)
            return {"accepted": False, **event}

        accepted_event = {
            "event": "command_accepted",
            **receipt,
            "payload": dict(envelope["payload"]),
        }
        self._emit(accepted_event)

        if command in _QUERY_COMMANDS:
            result = self._query_result(command)
            result_event = {
                "event": "command_result",
                "request_id": request_id,
                "command": command,
                "authority_revision": receipt["authority_revision"],
                "state_revision": self.state_revision,
                **result,
            }
            self._emit(result_event)
            return {
                "accepted": True,
                "event": accepted_event,
                "result": result,
                "state_revision": self.state_revision,
            }

        self.player.prepare(
            command=command,
            params=envelope["payload"],
            causality={
                "request_id": request_id,
                "command": command,
                "expected_authority_revision": expected_authority_revision,
                "expected_player_revision": expected_player_revision,
                "accepted_authority_revision": receipt["authority_revision"],
            },
        )
        return {
            "accepted": True,
            "event": accepted_event,
            "application_pending": True,
            "state_revision": self.state_revision,
        }

    def apply_next_player_callback(self) -> dict[str, Any] | None:
        callback = self.player.apply_next()
        if callback is None:
            return None
        self.state_revision += 1
        causality = callback["causality"]
        event = {
            "event": "command_applied",
            "request_id": causality["request_id"],
            "command": callback["command"],
            "expected_authority_revision": causality["expected_authority_revision"],
            "expected_player_revision": causality["expected_player_revision"],
            "accepted_authority_revision": causality["accepted_authority_revision"],
            "state_revision": self.state_revision,
            "application_source": callback["callback_source"],
            "state": self.state(),
        }
        self._emit(event)
        return event

    def _query_result(self, command: str) -> dict[str, Any]:
        if command == "describe":
            return {
                "commands": list(COMMANDS),
                "confidentiality": False,
                "protocol": build_descriptor()["profile"],
            }
        if command == "get_state":
            return {"state": self.state(), "controller": self.authority.controller_state()}
        if command == "list_videos":
            return {"videos": self.list_videos()}
        raise AssertionError(f"unhandled query command {command}")

    def _validate_command_envelope(self, envelope: Any) -> str | None:
        if not isinstance(envelope, dict):
            return "invalid_envelope"
        if set(envelope) != {
            "command",
            "expected_authority_revision",
            "expected_player_revision",
            "payload",
            "request_id",
        }:
            return "non_canonical_envelope"
        if len(canonical_json_bytes(envelope)) > 4096:
            return "request_too_large"
        request_id = envelope.get("request_id")
        if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
            return "invalid_request_id"
        command = envelope.get("command")
        if command not in COMMANDS:
            return "unknown_command"
        for revision_name in ("expected_authority_revision", "expected_player_revision"):
            revision = envelope.get(revision_name)
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
                return f"invalid_{revision_name}"
        params = envelope.get("payload")
        if not isinstance(params, dict):
            return "invalid_payload"
        if command == "select_video":
            if set(params) != {"video_id"}:
                return "invalid_select_video_params"
            allowed_ids = {video.video_id for video in self.player.videos}
            if params.get("video_id") not in allowed_ids:
                return "unknown_video_id"
        elif params:
            return "params_not_allowed"
        return None
