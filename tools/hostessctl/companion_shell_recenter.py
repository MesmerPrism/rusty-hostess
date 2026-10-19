"""Typed shell-only Quest recenter caller and evidence projection.

Quest owns the fixed AppFunction implementation, fresh privilege/firmware
checks, and original process retirement. This caller never sends ADB commands.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import uuid
from typing import Any

from tools.hostessctl.immutable_input_binding import WindowsInputBinding
from tools.hostessctl.process_observation import observe_process

PROFILE_SCHEMA = "rusty.hostess.companion.shell_recenter.profile.v1"
REPORT_SCHEMA = "rusty.hostess.companion.shell_recenter.v1"
INTENT_SCHEMA = "rusty.hostess.companion.shell_recenter.intent.v1"
RESULT_SCHEMA = "rusty.quest.shell_recenter.result.v1"
REQUEST_SCHEMA = "rusty.quest.shell_recenter.request.v1"
ACTION = "shell_recenter"
MODES = ("readiness", "recenter", "reconcile")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes(), object_pairs_hook=object_pairs)
    if type(value) is not dict:
        raise ValueError("JSON object required")
    return value


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON property")
        result[key] = value
    return result


def write_new(path: Path, data: bytes) -> None:
    # Exclusive creation plus flush before dispatch provides a durable replay
    # barrier. A crash after this point requires passive reconciliation.
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def load_profile(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if len(raw) > 262144:
        raise ValueError("bounded private profile required")
    profile = json.loads(raw, object_pairs_hook=object_pairs)
    if (type(profile) is not dict or set(profile) != {"$schema", "provider", "request"}
            or profile["$schema"] != PROFILE_SCHEMA):
        raise ValueError("closed shell recenter profile required")
    provider = profile["provider"]
    if (type(provider) is not dict or set(provider) != {"path", "sha256"}
            or type(provider["path"]) is not str
            or not Path(provider["path"]).is_absolute()
            or Path(provider["path"]).name != "quest_shell_recenter.py"
            or not re.fullmatch("[0-9a-f]{64}", str(provider["sha256"]))):
        raise ValueError("exact named Quest provider path and SHA-256 required")
    request = profile["request"]
    # The provider validates its complete closed contract. The caller checks
    # identity and paths it uses before creating its own host files.
    if (type(request) is not dict or request.get("schema") != REQUEST_SCHEMA
            or not re.fullmatch("[0-9a-f]{32}", str(request.get("request_id")))
            or not re.fullmatch("[0-9a-f]{32}", str(request.get("nonce")))
            or type(request.get("output_dir")) is not str
            or not Path(request["output_dir"]).is_absolute()
            or not str(request.get("boot_id") or "")
            or type(request.get("source")) is not dict
            or not re.fullmatch("[0-9a-f]{64}", str(request["source"].get("source_id")))
            or type(request.get("artifact")) is not dict):
        raise ValueError("Quest request identity and absolute output directory required")
    if digest(Path(provider["path"]).read_bytes()) != provider["sha256"]:
        raise ValueError("Quest provider SHA-256 changed")
    return profile, raw


def validate_result(result: dict[str, Any], request: dict[str, Any], request_sha256: str | None = None) -> None:
    if (result.get("schema") != RESULT_SCHEMA
            or any(result.get(key) != request[key] for key in ("request_id", "nonce", "boot_id"))
            or result.get("source_id") != request["source"].get("source_id")
            or result.get("request_sha256") != (request_sha256 or digest(canonical(request)))
            or result.get("artifact") != request["artifact"]):
        raise ValueError("Quest result identity or source/artifact pin mismatch")
    choices = {
        "availability": ("status", {"ready", "unavailable", "unknown"}),
        "dispatch": ("state", {"not_sent", "intent_recorded", "sent", "unknown"}),
        "callback": ("state", {"not_received", "success", "error", "unknown"}),
        "effect": ("state", {"unverified"}),
        "original": ("state", {"active", "retired", "unknown"}),
        "cleanup": ("state", {"held", "complete", "not_started"}),
    }
    for key, (field, values) in choices.items():
        if type(result.get(key)) is not dict or result[key].get(field) not in values:
            raise ValueError(f"invalid Quest {key} result")
    if result["availability"].get("privilege") != "android_shell_uid_2000":
        raise ValueError("explicit genuine Android shell privilege required")
    original = result["original"]
    if type(original.get("retired")) is not bool or original["retired"] != (original["state"] == "retired"):
        raise ValueError("inconsistent original retirement")
    if result["cleanup"]["state"] == "complete" and not original["retired"]:
        raise ValueError("cleanup cannot complete before original retirement")


def unknown_result(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        **{key: request[key] for key in ("request_id", "nonce", "boot_id", "artifact")},
        "source_id": request["source"]["source_id"],
        "request_sha256": digest(canonical(request)),
        "availability": {"status": "unknown", "reason": "inspect original provider evidence", "privilege": "android_shell_uid_2000"},
        "dispatch": {"state": "unknown"}, "callback": {"state": "unknown"},
        "effect": {"state": "unverified"},
        "original": {"state": "unknown", "retired": False}, "cleanup": {"state": "held"},
    }


def read_provider_result(request: dict[str, Any]) -> tuple[dict[str, Any], str]:
    root = Path(request["output_dir"])
    for name in ("RESULT.json", "STATUS.json"):
        path = root / name
        if path.exists():
            result = read_object(path)
            validate_result(result, request)
            return result, str(path)
    return unknown_result(request), ""


def invoke_provider(provider: Path, mode: str, request_path: Path) -> subprocess.CompletedProcess[bytes]:
    # No observer deadline, cancellation, kill, or timeout. communicate drains
    # both pipes and reaps this original child. Quest retains its own originals
    # through callback, final, EOF, and reap even if the callback is late.
    argv = [sys.executable, "-I", str(provider), mode, "--request", str(request_path)]
    stem = request_path.with_name(request_path.name + ".observation-" + uuid.uuid4().hex)
    # Reuse the binary, completion-driven observer: no decoding can abandon
    # a live child, and failed raw sinks keep draining both original pipes.
    previous = None
    if threading.current_thread() is threading.main_thread():
        previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        receipt = observe_process(argv, Path(str(stem) + ".stdout"), Path(str(stem) + ".stderr"))
        write_new(Path(str(stem) + ".json"), canonical(receipt))
        result = subprocess.CompletedProcess(argv, receipt["exit_code"], b"", b"")
        result.observation = receipt
        return result
    finally:
        if previous is not None:
            signal.signal(signal.SIGINT, previous)


def result_status(result: dict[str, Any], initial_mode: str, errors: list[str]) -> str:
    if result["availability"]["status"] == "unavailable" or result["callback"]["state"] == "error" or errors:
        return "fail"
    if result["original"]["retired"] and result["cleanup"]["state"] == "complete":
        if result["callback"]["state"] == "success" or (initial_mode == "readiness" and result["availability"]["status"] == "ready"):
            return "pass"
    return "warn"


def execute(profile_path: Path, mode: str) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError("unsupported shell recenter lifecycle mode")
    profile, profile_raw = load_profile(profile_path)
    request = profile["request"]
    output = Path(request["output_dir"])
    output.parent.mkdir(parents=True, exist_ok=True)
    intent_path = output.with_name(output.name + ".hostess-intent.json")
    request_path = output.with_name(output.name + ".hostess-request.json")
    request_bytes = canonical(request)
    identity = {
        "$schema": INTENT_SCHEMA, "action": ACTION,
        "profile_sha256": digest(profile_raw), "request_sha256": digest(request_bytes),
        "provider": profile["provider"], "request_id": request["request_id"], "nonce": request["nonce"],
        "initial_mode": mode,
    }
    duplicate = False
    errors: list[str] = []
    child = None
    with ExitStack() as stack:
        if os.name == "nt":
            binding = WindowsInputBinding.from_pins([
                {"path": str(profile_path.resolve()), "sha256": digest(profile_raw)},
                profile["provider"],
            ])
            stack.callback(binding.close)
        if mode == "reconcile":
            if not intent_path.exists():
                raise ValueError("no owned Hostess intent to reconcile")
            duplicate = True
        else:
            try:
                write_new(intent_path, canonical(identity))
            except FileExistsError:
                duplicate = True
        stored = read_object(intent_path)
        if (set(stored) != set(identity) or stored.get("initial_mode") not in {"readiness", "recenter"}
                or any(stored.get(key) != identity[key] for key in identity if key != "initial_mode")):
            raise ValueError("output directory belongs to a different exact request")
        if mode == "recenter" and stored.get("initial_mode") != "recenter":
            raise ValueError("readiness request cannot become a recenter request; use fresh identity/output")
        if not duplicate or mode == "reconcile":
            try:
                if not request_path.exists():
                    write_new(request_path, request_bytes)
                if request_path.read_bytes() != request_bytes:
                    raise ValueError("captured Quest request changed")
                if os.name == "nt":
                    request_binding = WindowsInputBinding.from_pins([
                        {"path": str(request_path.resolve()), "sha256": digest(request_bytes)},
                    ])
                    stack.callback(request_binding.close)
                child = invoke_provider(Path(profile["provider"]["path"]), mode, request_path)
            except Exception as exc:
                # The write-ahead barrier remains even when launch/result
                # observation is uncertain. A caller must never auto-retrigger.
                errors.append(f"provider observation failed: {exc}")
        try:
            result, result_path = read_provider_result(request)
        except (OSError, ValueError, KeyError) as exc:
            result, result_path = unknown_result(request), ""
            errors.append(f"provider result rejected: {exc}")
        if child is not None and child.returncode != 0:
            errors.append(f"provider exited {child.returncode}; inspect original result")
    status = result_status(result, stored["initial_mode"], errors)
    return {
        "$schema": REPORT_SCHEMA, "action": ACTION, "mode": mode, "status": status,
        "initial_mode": stored["initial_mode"],
        "request_id": request["request_id"], "nonce": request["nonce"],
        "target": {key: request.get(key) for key in ("canonical_serial", "selector", "boot_id", "operator_id")},
        "source": request["source"], "artifact": request["artifact"],
        "firmware": request.get("firmware"), "request_path": str(request_path),
        "profile_sha256": digest(profile_raw), "request_sha256": digest(request_bytes),
        "provider": profile["provider"], "intent_path": str(intent_path),
        "provider_result_path": result_path, "duplicate_suppressed": duplicate,
        "provider_exit_code": child.returncode if child is not None else None,
        "provider_observation": getattr(child, "observation", None),
        **{key: result[key] for key in ("availability", "dispatch", "callback", "effect", "original", "cleanup")},
        "provider_result": result, "errors": errors,
        "policy": "Developer/operator shell UID 2000 only; callback success does not prove a reference-space or wearer-visible effect. No timeout replay or ordinary APK fallback.",
    }


def run_shell_recenter(args: argparse.Namespace) -> int:
    report = execute(Path(args.profile).resolve(), args.mode)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical(report))
    return 2 if report["status"] == "fail" else 0


def project_rows(report: dict[str, Any], source: dict[str, Any], row) -> list[dict[str, Any]]:
    if not valid_report(report):
        return [row("shell_recenter.invalid", "command", "shell_recenter", "Invalid shell recenter evidence", "fail", source,
                    authority_owner="rusty.hostess", notes="No callback, effect, or cleanup success can be inferred.")]
    stages = [row(
        f"shell_recenter.{key}", "command", "shell_recenter", label,
        ({"ready": "pass", "unavailable": "fail", "unknown": "warn"}[report[key]["status"]] if key == "availability" else
         "pass" if report[key].get("state") in {"success", "retired", "complete"} else
         "fail" if report[key].get("state") == "error" else "warn"),
        source, authority_owner="rusty.quest", evidence=str(report[key].get("state", report[key].get("status", "unknown"))),
        notes=report.get("policy", ""), details={**report[key], "request_id": report.get("request_id"), "target": report.get("target"),
            "source": report.get("source"), "artifact": report.get("artifact"), "firmware": report.get("firmware"),
            "provider_result_path": report.get("provider_result_path"), "request_path": report.get("request_path")},
    ) for key, label in (
        ("availability", "Recenter availability: genuine Android shell UID 2000 required"),
        ("dispatch", "Recenter dispatch"), ("callback", "Original AppFunction callback"),
        ("effect", "Recenter effect: independent observation required"),
        ("original", "Original process retirement"), ("cleanup", "Owned cleanup"),
    )]
    return [row("shell_recenter.action", "command", "shell_recenter", "Shell recenter action result", report["status"], source,
                authority_owner="rusty.hostess", evidence=report["status"], notes=report.get("policy", ""),
                issue_count=len(report["errors"]),
                details={"errors": report["errors"], "provider_exit_code": report.get("provider_exit_code"),
                         "provider_observation": report.get("provider_observation"), "target": report.get("target"),
                         "duplicate_suppressed": report.get("duplicate_suppressed")})] + stages


def valid_report(report: dict[str, Any]) -> bool:
    try:
        if (report.get("$schema") != REPORT_SCHEMA or report.get("action") != ACTION
                or report.get("mode") not in MODES or report.get("status") not in {"pass", "warn", "fail"}
                or report.get("initial_mode") not in {"readiness", "recenter"}
                or type(report.get("errors")) is not list):
            return False
        request = {"request_id": report["request_id"], "nonce": report["nonce"],
                   "boot_id": report["target"]["boot_id"], "source": report["source"], "artifact": report["artifact"]}
        result = report["provider_result"]
        validate_result(result, request, report["request_sha256"])
        return (report["status"] == result_status(result, report["initial_mode"], report["errors"])
                and all(report[key] == result[key] for key in ("availability", "dispatch", "callback", "effect", "original", "cleanup")))
    except (ValueError, TypeError, KeyError):
        return False
