from __future__ import annotations

import unittest

import _app_path  # noqa: F401 - repo-root unittest discovery bootstrap

from trusted_local_control_conformance.fake_runtime import (
    FakeClock,
    FixtureManifoldPort,
    TrustedLocalControlFixture,
)


def envelope(
    fixture: TrustedLocalControlFixture,
    command: str,
    request_id: str,
    payload: dict[str, object] | None = None,
    *,
    authority_revision: int | None = None,
    player_revision: int | None = None,
) -> dict[str, object]:
    return {
        "command": command,
        "expected_authority_revision": (
            fixture.authority.authority_revision
            if authority_revision is None
            else authority_revision
        ),
        "expected_player_revision": (
            fixture.state_revision if player_revision is None else player_revision
        ),
        "payload": payload or {},
        "request_id": request_id,
    }


def paired_fixture(
    *,
    clock: FakeClock | None = None,
    authority: FixtureManifoldPort | None = None,
) -> tuple[TrustedLocalControlFixture, str]:
    fixture = TrustedLocalControlFixture(clock=clock, authority=authority)
    fixture.wearer_enable()
    pair = fixture.pair(
        pairing_code=fixture.pairing_code,
        request_id="pair-runtime-0001",
    )
    if pair["decision"] != "accepted" or fixture.session_token is None:
        raise AssertionError("fixture failed to pair")
    return fixture, fixture.session_token


class RuntimeBoundaryTests(unittest.TestCase):
    def test_listener_requires_foreground_wearer_enable(self) -> None:
        fixture = TrustedLocalControlFixture()

        self.assertFalse(fixture.authority.enabled)
        rejected = fixture.wearer_enable(foreground=False, wearer_confirmed=True)
        self.assertEqual(rejected["decision"], "rejected")
        self.assertFalse(fixture.authority.enabled)

    def test_one_controller_and_single_use_pairing_code(self) -> None:
        fixture, _ = paired_fixture()

        second = fixture.pair(
            pairing_code=fixture.pairing_code,
            request_id="pair-runtime-0002",
        )

        self.assertEqual(second["reason"], "controller_lease_occupied")
        self.assertTrue(fixture.authority.pairing_code_used)
        self.assertEqual(
            fixture.authority.controller_state()["controller_id"],
            "windows-browser",
        )

    def test_select_is_pending_until_callback_and_does_not_play(self) -> None:
        fixture, token = paired_fixture()
        request_id = "select-runtime-0001"

        response = fixture.handle_command(
            session_token=token,
            envelope=envelope(
                fixture,
                "select_video",
                request_id,
                {"video_id": "synthetic-blue-2s"},
            ),
        )

        self.assertTrue(response["accepted"])
        self.assertTrue(response["application_pending"])
        self.assertEqual(fixture.player.selected_video_id, "synthetic-grid-1s")
        self.assertFalse(fixture.player.playing)
        self.assertEqual(fixture.state_revision, 0)
        self.assertEqual(
            [event["event"] for event in fixture.event_history if event.get("request_id") == request_id],
            ["command_accepted"],
        )

        applied = fixture.apply_next_player_callback()

        self.assertIsNotNone(applied)
        self.assertEqual(fixture.player.selected_video_id, "synthetic-blue-2s")
        self.assertFalse(fixture.player.playing)
        self.assertEqual(applied["state"]["revision"], 1)
        self.assertEqual(applied["request_id"], request_id)
        self.assertEqual(applied["application_source"], "fake_player_effect_callback")

    def test_play_and_pause_are_separate_callback_effects(self) -> None:
        fixture, token = paired_fixture()

        fixture.handle_command(
            session_token=token,
            envelope=envelope(fixture, "play", "play-runtime-00001"),
        )
        self.assertFalse(fixture.player.playing)
        fixture.apply_next_player_callback()
        self.assertTrue(fixture.player.playing)

        fixture.handle_command(
            session_token=token,
            envelope=envelope(fixture, "pause", "pause-runtime-0001"),
        )
        self.assertTrue(fixture.player.playing)
        fixture.apply_next_player_callback()
        self.assertFalse(fixture.player.playing)

    def test_query_results_match_the_quest_ui_projection(self) -> None:
        fixture, token = paired_fixture()
        state_result = fixture.handle_command(
            session_token=token,
            envelope=envelope(fixture, "get_state", "state-runtime-0001"),
        )
        projected_state = state_result["result"]["state"]

        self.assertEqual(
            set(projected_state),
            {
                "authority_revision",
                "controller_connected",
                "controller_label",
                "enabled",
                "player",
            },
        )
        self.assertEqual(projected_state["player"], fixture.state())

        videos_result = fixture.handle_command(
            session_token=token,
            envelope=envelope(fixture, "list_videos", "videos-runtime-001"),
        )
        self.assertEqual(
            videos_result["result"]["videos"],
            [
                {
                    "duration_ms": 1_000,
                    "title": "Synthetic grid",
                    "video_id": "synthetic-grid-1s",
                },
                {
                    "duration_ms": 2_000,
                    "title": "Synthetic blue",
                    "video_id": "synthetic-blue-2s",
                },
            ],
        )

    def test_replay_and_stale_revisions_fail_closed(self) -> None:
        fixture, token = paired_fixture()
        first = envelope(fixture, "get_state", "replay-runtime-001")
        accepted = fixture.handle_command(session_token=token, envelope=first)
        self.assertTrue(accepted["accepted"])

        replay = fixture.handle_command(session_token=token, envelope=first)
        self.assertEqual(replay["reason"], "request_replay")

        stale_authority = fixture.handle_command(
            session_token=token,
            envelope=envelope(
                fixture,
                "get_state",
                "stale-authority-01",
                authority_revision=0,
            ),
        )
        self.assertEqual(stale_authority["reason"], "stale_expected_authority_revision")

        stale_player = fixture.handle_command(
            session_token=token,
            envelope=envelope(
                fixture,
                "get_state",
                "stale-player-0001",
                player_revision=99,
            ),
        )
        self.assertEqual(stale_player["reason"], "stale_expected_player_revision")

    def test_rate_expiry_and_revoke_are_manifold_fixture_receipts(self) -> None:
        clock = FakeClock()
        authority = FixtureManifoldPort(clock, rate_limit_count=1)
        fixture, token = paired_fixture(clock=clock, authority=authority)

        first = fixture.handle_command(
            session_token=token,
            envelope=envelope(fixture, "get_state", "rate-runtime-0001"),
        )
        self.assertTrue(first["accepted"])
        limited = fixture.handle_command(
            session_token=token,
            envelope=envelope(fixture, "get_state", "rate-runtime-0002"),
        )
        self.assertEqual(limited["reason"], "rate_limited")
        self.assertEqual(limited["source_authority"], "rusty.manifold")
        self.assertTrue(limited["synthetic_fixture"])

        clock.advance(authority.idle_window_seconds)
        expired = fixture.handle_command(
            session_token=token,
            envelope=envelope(fixture, "get_state", "expiry-runtime-001"),
        )
        self.assertEqual(expired["reason"], "idle_expired")

        fixture, token = paired_fixture()
        fixture.wearer_revoke()
        revoked = fixture.handle_command(
            session_token=token,
            envelope=envelope(fixture, "get_state", "revoke-runtime-001"),
        )
        self.assertEqual(revoked["reason"], "session_invalid")

    def test_envelope_and_registry_reject_generic_surfaces(self) -> None:
        fixture, token = paired_fixture()
        base = envelope(fixture, "get_state", "surface-runtime-01")

        cases = (
            ({**base, "shell": "whoami"}, "non_canonical_envelope"),
            ({**base, "command": "execute"}, "unknown_command"),
            ({**base, "payload": {"url": "https://example.invalid"}}, "params_not_allowed"),
            (
                envelope(
                    fixture,
                    "select_video",
                    "surface-video-0001",
                    {"video_id": "../private.mp4"},
                ),
                "unknown_video_id",
            ),
        )
        for damaged, reason in cases:
            with self.subTest(reason=reason):
                result = fixture.handle_command(session_token=token, envelope=damaged)
                self.assertEqual(result["reason"], reason)


if __name__ == "__main__":
    unittest.main()
