"""Offline conformance report construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contract import (
    COMMANDS,
    build_descriptor,
    validate_descriptor,
    validate_quest_registry,
    validate_web_assets,
)
from .fake_runtime import FakeClock, FixtureManifoldPort, TrustedLocalControlFixture


def find_quest_web_root(quest_root: Path) -> Path | None:
    """Resolve the exact packaged controller source directory in the bound app."""

    web_root = (
        quest_root
        / "apps"
        / "spatial-video-control-example-android"
        / "app"
        / "src"
        / "main"
        / "assets"
        / "control"
    )
    if all((web_root / name).is_file() for name in ("index.html", "app.js", "styles.css")):
        return web_root
    return None


def asset_receipt(web_root: Path, *, role: str) -> dict[str, Any]:
    files = []
    for name in ("index.html", "app.js", "styles.css"):
        path = web_root / name
        files.append(
            {
                "name": name,
                "path": str(path.resolve()),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
            }
        )
    return {
        "role": role,
        "web_root": str(web_root.resolve()),
        "files": files,
    }


def _envelope(
    fixture: TrustedLocalControlFixture,
    command: str,
    request_id: str,
    payload: dict[str, Any] | None = None,
    *,
    expected_authority_revision: int | None = None,
    expected_player_revision: int | None = None,
) -> dict[str, Any]:
    return {
        "command": command,
        "expected_authority_revision": (
            fixture.authority.authority_revision
            if expected_authority_revision is None
            else expected_authority_revision
        ),
        "expected_player_revision": (
            fixture.state_revision
            if expected_player_revision is None
            else expected_player_revision
        ),
        "payload": payload or {},
        "request_id": request_id,
    }


def exercise_fixture() -> dict[str, bool]:
    """Exercise the deterministic boundary without opening a socket."""

    checks: dict[str, bool] = {}
    clock = FakeClock()
    fixture = TrustedLocalControlFixture(clock=clock)
    checks["disabled_default"] = fixture.authority.enabled is False
    denied = fixture.wearer_enable(foreground=False, wearer_confirmed=True)
    checks["foreground_wearer_opt_in"] = denied.get("decision") == "rejected"
    enabled = fixture.wearer_enable()
    checks["bounded_explicit_enable"] = (
        enabled.get("decision") == "accepted"
        and fixture.authority.enabled_until is not None
    )

    invalid_pair = fixture.pair(
        pairing_code="000000",
        request_id="pair-invalid-0001",
    )
    checks["manual_pairing_code"] = invalid_pair.get("reason") == "pairing_code_invalid"
    pair = fixture.pair(
        pairing_code=fixture.pairing_code,
        request_id="pair-accepted-001",
    )
    token = fixture.session_token or ""
    checks["single_use_pairing"] = (
        pair.get("decision") == "accepted"
        and fixture.pair(
            pairing_code=fixture.pairing_code,
            request_id="pair-second-00001",
        ).get("reason")
        == "controller_lease_occupied"
    )
    checks["visible_controller_and_revoke"] = (
        fixture.authority.controller_state()["controller_id"] == "windows-browser"
        and fixture.authority.controller_state()["wearer_revoke_available"] is True
    )

    query_results: dict[str, dict[str, Any]] = {}
    for sequence, command in enumerate(("describe", "get_state", "list_videos"), start=1):
        request_id = f"query-{command.replace('_', '-')}-{sequence:08d}"
        query_results[command] = fixture.handle_command(
            session_token=token,
            envelope=_envelope(fixture, command, request_id),
        )
    checks["closed_query_commands"] = (
        all(result.get("accepted") for result in query_results.values())
        and query_results["describe"]["result"]["commands"] == list(COMMANDS)
        and len(query_results["list_videos"]["result"]["videos"]) == 2
    )

    select_id = "effect-select-0001"
    select = fixture.handle_command(
        session_token=token,
        envelope=_envelope(
            fixture,
            "select_video",
            select_id,
            {"video_id": "synthetic-grid"},
        ),
    )
    accepted_index = next(
        index
        for index, event in enumerate(fixture.event_history)
        if event.get("event") == "command_accepted" and event.get("request_id") == select_id
    )
    checks["acceptance_not_effect"] = (
        select.get("accepted") is True
        and fixture.player.selected_video_id == "synthetic-blue"
        and fixture.state_revision == 0
    )
    applied = fixture.apply_next_player_callback()
    applied_index = next(
        index
        for index, event in enumerate(fixture.event_history)
        if event.get("event") == "command_applied" and event.get("request_id") == select_id
    )
    checks["callback_applied_causality"] = (
        applied is not None
        and accepted_index < applied_index
        and applied["application_source"] == "fake_player_effect_callback"
        and applied["expected_player_revision"] == 0
        and applied["state"]["revision"] == 1
    )
    checks["select_does_not_play"] = (
        fixture.player.selected_video_id == "synthetic-grid"
        and fixture.player.playing is False
    )

    play = fixture.handle_command(
        session_token=token,
        envelope=_envelope(fixture, "play", "effect-play-000001"),
    )
    fixture.apply_next_player_callback()
    checks["play_is_separate"] = play.get("accepted") is True and fixture.player.playing is True
    pause = fixture.handle_command(
        session_token=token,
        envelope=_envelope(fixture, "pause", "effect-pause-00001"),
    )
    fixture.apply_next_player_callback()
    checks["pause_command"] = pause.get("accepted") is True and fixture.player.playing is False

    replay = fixture.handle_command(
        session_token=token,
        envelope=_envelope(fixture, "play", "effect-play-000001"),
    )
    checks["request_replay_rejected"] = replay.get("reason") == "request_replay"
    stale = fixture.handle_command(
        session_token=token,
        envelope=_envelope(
            fixture,
            "play",
            "effect-stale-000001",
            expected_player_revision=0,
        ),
    )
    checks["stale_revision_rejected"] = stale.get("reason") == "stale_expected_player_revision"
    unknown = fixture.handle_command(
        session_token=token,
        envelope=_envelope(fixture, "open_url", "unknown-surface-001"),
    )
    checks["generic_surfaces_rejected"] = unknown.get("reason") == "unknown_command"
    unknown_video = fixture.handle_command(
        session_token=token,
        envelope=_envelope(
            fixture,
            "select_video",
            "unknown-video-00001",
            {"video_id": "https://example.invalid/video.mp4"},
        ),
    )
    checks["arbitrary_url_rejected"] = unknown_video.get("reason") == "unknown_video_id"

    fixture.wearer_revoke()
    revoked = fixture.handle_command(
        session_token=token,
        envelope=_envelope(fixture, "get_state", "post-revoke-000001"),
    )
    checks["wearer_revoke_effective"] = revoked.get("reason") == "session_invalid"

    expiry_clock = FakeClock()
    expiry_fixture = TrustedLocalControlFixture(clock=expiry_clock)
    expiry_fixture.wearer_enable()
    expiry_fixture.pair(
        pairing_code=expiry_fixture.pairing_code,
        request_id="pair-expiry-00001",
    )
    expiry_token = expiry_fixture.session_token or ""
    expiry_clock.advance(expiry_fixture.authority.idle_window_seconds)
    expired = expiry_fixture.handle_command(
        session_token=expiry_token,
        envelope=_envelope(expiry_fixture, "get_state", "idle-expired-0001"),
    )
    checks["bounded_idle_expiry"] = expired.get("reason") == "idle_expired"

    rate_clock = FakeClock()
    rate_authority = FixtureManifoldPort(rate_clock, rate_limit_count=1)
    rate_fixture = TrustedLocalControlFixture(clock=rate_clock, authority=rate_authority)
    rate_fixture.wearer_enable()
    rate_fixture.pair(
        pairing_code=rate_fixture.pairing_code,
        request_id="pair-rate-limit-01",
    )
    rate_token = rate_fixture.session_token or ""
    rate_fixture.handle_command(
        session_token=rate_token,
        envelope=_envelope(rate_fixture, "get_state", "rate-first-000001"),
    )
    limited = rate_fixture.handle_command(
        session_token=rate_token,
        envelope=_envelope(rate_fixture, "get_state", "rate-second-00001"),
    )
    checks["strict_rate_limit"] = limited.get("reason") == "rate_limited"
    return checks


def build_report(
    *,
    descriptor: dict[str, Any] | None = None,
    web_root: Path,
    quest_root: Path | None = None,
) -> dict[str, Any]:
    descriptor = descriptor or build_descriptor()
    descriptor_issues = validate_descriptor(descriptor)
    asset_issues = validate_web_assets(web_root)
    fixture_checks = exercise_fixture()
    quest_issues = validate_quest_registry(quest_root) if quest_root is not None else []
    report = {
        "schema": "rusty.hostess.trusted_local_control.conformance_report.v1",
        "profile": "trusted_local_http_v1",
        "authority_claim": "none_fixture_only",
        "descriptor_issues": descriptor_issues,
        "asset_issues": asset_issues,
        "fixture_checks": fixture_checks,
        "asset_receipt": asset_receipt(
            web_root,
            role="quest_packaged_assets" if quest_root is not None else "hostess_fixture_assets",
        ),
        "quest_registry": {
            "checked": quest_root is not None,
            "issues": quest_issues,
            "path": (
                str(
                    (
                        quest_root
                        / "apps"
                        / "spatial-video-control-example-android"
                        / "contracts"
                        / "trusted_local_http_v1.commands.registry.json"
                    ).resolve()
                )
                if quest_root is not None
                else None
            ),
        },
        "network_actions": {
            "lan_listener": False,
            "mdns": False,
            "fixed_port": False,
            "device_contact": False,
        },
    }
    report["status"] = (
        "pass"
        if not descriptor_issues
        and not asset_issues
        and not quest_issues
        and all(fixture_checks.values())
        else "fail"
    )
    return report


def read_descriptor(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("descriptor must be one JSON object")
    return value
