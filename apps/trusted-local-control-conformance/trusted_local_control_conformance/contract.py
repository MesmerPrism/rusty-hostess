"""Closed, static contract checks for ``trusted_local_http_v1``."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROFILE = "trusted_local_http_v1"
DESCRIPTOR_SCHEMA = "rusty.hostess.trusted_local_control.conformance_descriptor.v1"
COMMANDS = (
    "describe",
    "get_state",
    "list_videos",
    "select_video",
    "play",
    "pause",
)

_REQUIRED_ASSETS = ("index.html", "app.js", "styles.css")
_FORBIDDEN_DESCRIPTOR_WORDS = (
    "shell",
    "adb",
    "intent",
    "component",
    "upload",
    "plugin",
    "mcp",
    "execute",
    "arbitrary_url",
    "arbitrary_path",
)
_EXTERNAL_REFERENCE = re.compile(
    r"""(?:src|href)\s*=\s*["'](?:https?:)?//|https?://|<script(?![^>]*\bsrc="/app\.js")""",
    re.IGNORECASE,
)


def build_descriptor() -> dict[str, Any]:
    """Return the deterministic Hostess conformance descriptor."""

    return {
        "schema": DESCRIPTOR_SCHEMA,
        "profile": PROFILE,
        "default_enabled": False,
        "authority": {
            "admission_session_lease_replay_expiry_revocation": "rusty.manifold",
            "application_effect": "rusty.quest.player",
            "hostess_role": "non_authoritative_fixture_and_conformance",
        },
        "transport": {
            "http": True,
            "websocket_events": True,
            "same_origin_only": True,
            "cors": False,
            "confidentiality": False,
            "test_bind_host": "127.0.0.1",
            "test_bind_port": 0,
        },
        "activation": {
            "wearer_opt_in": True,
            "foreground_only": True,
            "bounded_window": True,
            "wearer_visible_controller": True,
            "wearer_revoke": True,
        },
        "pairing": {
            "manual_ip_required": True,
            "single_use_code_required": True,
            "qr_optional": True,
            "mdns_optional": True,
            "qr_in_slice": False,
            "mdns_in_slice": False,
        },
        "limits": {
            "one_controller": True,
            "bounded_idle_expiry": True,
            "bounded_session_expiry": True,
            "strict_rate_limit": True,
            "max_request_bytes": 4096,
        },
        "commands": list(COMMANDS),
        "effects": {
            "acceptance_event": "command_accepted",
            "application_event": "command_applied",
            "application_source": "player_callback",
            "expected_revision": True,
            "request_causality": True,
            "select_and_play_separate": True,
        },
        "assets": {
            "packaged": list(_REQUIRED_ASSETS),
            "same_origin": True,
            "external_scripts": False,
            "runtime_or_uploaded_ui": False,
        },
        "forbidden_surfaces": list(_FORBIDDEN_DESCRIPTOR_WORDS),
        "sensitive_data": {
            "passwords": False,
            "private_evidence": False,
            "fleet_credentials": False,
            "device_management_credentials": False,
        },
    }


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def validate_descriptor(descriptor: dict[str, Any]) -> list[str]:
    """Return stable issue codes; an empty list means conformance."""

    issues: list[str] = []
    expected = build_descriptor()
    if descriptor.get("schema") != DESCRIPTOR_SCHEMA:
        issues.append("descriptor.schema")
    if descriptor.get("profile") != PROFILE:
        issues.append("descriptor.profile")
    if descriptor.get("default_enabled") is not False:
        issues.append("descriptor.default_enabled")
    if descriptor.get("commands") != list(COMMANDS):
        issues.append("descriptor.closed_command_registry")

    for section, keys in (
        ("authority", expected["authority"].keys()),
        ("transport", expected["transport"].keys()),
        ("activation", expected["activation"].keys()),
        ("pairing", expected["pairing"].keys()),
        ("limits", expected["limits"].keys()),
        ("effects", expected["effects"].keys()),
        ("assets", expected["assets"].keys()),
        ("sensitive_data", expected["sensitive_data"].keys()),
    ):
        actual = descriptor.get(section)
        if not isinstance(actual, dict) or set(actual) != set(keys):
            issues.append(f"descriptor.{section}.shape")

    for dotted, required in (
        ("transport.same_origin_only", True),
        ("transport.cors", False),
        ("transport.confidentiality", False),
        ("transport.test_bind_host", "127.0.0.1"),
        ("transport.test_bind_port", 0),
        ("activation.wearer_opt_in", True),
        ("activation.foreground_only", True),
        ("activation.bounded_window", True),
        ("activation.wearer_visible_controller", True),
        ("activation.wearer_revoke", True),
        ("pairing.manual_ip_required", True),
        ("pairing.single_use_code_required", True),
        ("pairing.qr_in_slice", False),
        ("pairing.mdns_in_slice", False),
        ("limits.one_controller", True),
        ("limits.bounded_idle_expiry", True),
        ("limits.bounded_session_expiry", True),
        ("limits.strict_rate_limit", True),
        ("effects.select_and_play_separate", True),
        ("effects.application_source", "player_callback"),
        ("assets.same_origin", True),
        ("assets.external_scripts", False),
        ("assets.runtime_or_uploaded_ui", False),
    ):
        section, key = dotted.split(".", 1)
        actual_section = descriptor.get(section)
        if not isinstance(actual_section, dict) or actual_section.get(key) != required:
            issues.append(f"descriptor.{dotted}")

    forbidden = descriptor.get("forbidden_surfaces")
    if forbidden != list(_FORBIDDEN_DESCRIPTOR_WORDS):
        issues.append("descriptor.forbidden_surfaces")

    if len(canonical_json_bytes(descriptor)) > 4096:
        issues.append("descriptor.size")
    return sorted(set(issues))


def validate_web_assets(web_root: Path) -> list[str]:
    """Check the packaged UI without executing JavaScript or using a network."""

    issues: list[str] = []
    for name in _REQUIRED_ASSETS:
        path = web_root / name
        if not path.is_file():
            issues.append(f"assets.missing.{name}")

    if issues:
        return sorted(issues)

    html = (web_root / "index.html").read_text(encoding="utf-8")
    javascript = (web_root / "app.js").read_text(encoding="utf-8")
    stylesheet = (web_root / "styles.css").read_text(encoding="utf-8")
    combined = "\n".join((html, javascript, stylesheet))

    if _EXTERNAL_REFERENCE.search(combined):
        issues.append("assets.external_reference")
    if '<script src="/app.js" defer></script>' not in html:
        issues.append("assets.script_not_packaged")
    if '<link rel="stylesheet" href="/styles.css">' not in html:
        issues.append("assets.style_not_packaged")
    if "<script>" in html.lower() or "style=" in html.lower():
        issues.append("assets.inline_code")
    for forbidden in ("eval(", "new Function(", "import(", "innerHTML", "document.write"):
        if forbidden in javascript:
            issues.append("assets.dynamic_code")
    for forbidden_surface in _FORBIDDEN_DESCRIPTOR_WORDS:
        if forbidden_surface in javascript.lower():
            issues.append(f"assets.forbidden.{forbidden_surface}")
    return sorted(set(issues))


def validate_quest_registry(quest_root: Path) -> list[str]:
    """Validate the exact public Quest command-registry binding."""

    registry_path = (
        quest_root
        / "apps"
        / "spatial-video-control-example-android"
        / "contracts"
        / "trusted_local_http_v1.commands.registry.json"
    )
    if not registry_path.is_file():
        return ["quest_registry.missing"]
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ["quest_registry.invalid_json"]
    issues: list[str] = []
    if registry.get("schema") != "rusty.quest.trusted_local_http.command_registry.v1":
        issues.append("quest_registry.schema")
    if registry.get("protocol") != PROFILE:
        issues.append("quest_registry.protocol")
    if registry.get("payload_max_bytes") != 4096:
        issues.append("quest_registry.payload_max_bytes")
    if registry.get("request_id_pattern") != "^[a-z0-9][a-z0-9-]{15,63}$":
        issues.append("quest_registry.request_id_pattern")
    commands = registry.get("commands")
    if not isinstance(commands, list):
        return sorted(set(issues + ["quest_registry.commands.shape"]))
    if [command.get("id") for command in commands if isinstance(command, dict)] != list(COMMANDS):
        issues.append("quest_registry.commands.closed_order")
    expected_kinds = {
        "describe": "query",
        "get_state": "query",
        "list_videos": "query",
        "select_video": "effect",
        "play": "effect",
        "pause": "effect",
    }
    for command in commands:
        if not isinstance(command, dict):
            issues.append("quest_registry.command.shape")
            continue
        command_id = command.get("id")
        if command.get("kind") != expected_kinds.get(command_id):
            issues.append(f"quest_registry.command.{command_id}.kind")
        payload = command.get("payload")
        if not isinstance(payload, dict) or payload.get("additionalProperties") is not False:
            issues.append(f"quest_registry.command.{command_id}.payload_closed")
            continue
        if command_id == "select_video":
            if payload.get("required") != ["video_id"]:
                issues.append("quest_registry.command.select_video.video_required")
            properties = payload.get("properties")
            video = properties.get("video_id") if isinstance(properties, dict) else None
            if not isinstance(video, dict) or video.get("type") != "string":
                issues.append("quest_registry.command.select_video.video_shape")
        elif payload.get("required") != []:
            issues.append(f"quest_registry.command.{command_id}.payload_empty")
    return sorted(set(issues))
