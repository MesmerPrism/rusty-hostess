"""Bounded Hostess lifecycle wrapper for Meta Quest Developer Hub Casting.

Casting.exe remains an opaque, third-party presentation sink.  This adapter
does not decode, intercept, or claim access to its media transport.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, BinaryIO, Callable

from tools.hostessctl.json_schema_validation import (
    CheckedSchemaError,
    load_and_validate_checked_schema,
)
REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT_SCHEMA_PATH = REPO_ROOT / "schemas" / "meta-quest-casting-receipt.schema.json"
DESCRIPTOR_SCHEMA_PATH = (
    REPO_ROOT / "schemas" / "meta-quest-casting-capability-descriptor.schema.json"
)
RECEIPT_SCHEMA = "rusty.hostess.meta_quest_casting.receipt.v1"
DESCRIPTOR_SCHEMA = "rusty.hostess.meta_quest_casting.capability_descriptor.v1"
STATE_SCHEMA = "rusty.hostess.meta_quest_casting.private_state.v1"
COMPANION_PACKAGE = "com.oculus.magicislandcastingservice"
SERIAL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
REJECTED_SERIALS = {"*", "any", "auto", "default", "first"}
STATE_PHASES = {
    "starting",
    "active",
    "launched_unconfirmed",
    "failed",
    "stopping",
    "failed_pending_cleanup",
}

HIGH_POV_FEATURES = (
    "image_stabilization",
    "force_reapply_fov",
    "update_device_fov_via_openxr_api",
    "panel_streaming",
    "system_monitor",
)
COMPATIBILITY_PROFILES: dict[str, dict[str, Any]] = {
    "6.4.1": {
        "profile_id": "mqdh-6.4.1-high-pov-v1",
        "mqdh_sha256": (
            "A64EC9300B411074AEAB01A7A99F68ED193226B166B6C678B2FE872D1A01284F"
        ),
        "mqdh_signer_thumbprint": "4FB8B255A20FDE3C8C7123EFA02970DFC7459877",
        "casting_sha256": (
            "C8ECD63A7BD17A9822FF1A39340BB5443BB3F5923682826CFA19D559D4AFE77F"
        ),
        "signer_thumbprint": "4FB8B255A20FDE3C8C7123EFA02970DFC7459877",
        "adb_sha256": (
            "0E606318957BAAC81B997CCD8EE4BCDFF79964A9921DA07C716AEA3E8D856AF7"
        ),
        "adb_api_sha256": (
            "DB92F418F6C384FAEEBCCADBC592FB339AF3D51ECFEC3EC04BD3572080247BAE"
        ),
        "adb_usb_api_sha256": (
            "3BA13420D47C60D958E0D5B333440F9895704879BB7C983B55F195717F621A3E"
        ),
        "adb_signer_thumbprint": "607A3EDAA64933E94422FC8F0C80388E0590986C",
        "companion_version_name": "2.0.0.0.7440",
        "companion_version_code": "839205053",
        "features": HIGH_POV_FEATURES,
    }
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_state_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is required for private casting state")
    return (
        Path(local_app_data)
        / "Rusty Hostess"
        / "meta-quest-casting"
        / "state.json"
    )


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class PrivateStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _default_state_path()

    def load(self) -> dict[str, Any] | None:
        _validate_private_storage_path(self.path)
        if not self.path.is_file():
            return None
        value = json.loads(self.path.read_text(encoding="utf-8"))
        _validate_private_state(value)
        return value

    def write(self, value: dict[str, Any]) -> None:
        _validate_private_state(value)
        _validate_private_storage_path(self.path)
        _atomic_write_json(self.path, value)

    def clear(self) -> None:
        _validate_private_storage_path(self.path)
        if self.path.exists():
            self.path.unlink()

    def try_acquire_operation_lock(self) -> BinaryIO | None:
        lock_path = self.path.with_name(f"{self.path.name}.lock")
        _validate_private_storage_path(lock_path)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        _validate_private_storage_path(lock_path)
        handle = lock_path.open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return None
        return handle

    @staticmethod
    def release_operation_lock(handle: BinaryIO) -> None:
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _validate_private_storage_path(path: Path) -> None:
    absolute = path.absolute()
    if not absolute.is_absolute():
        raise ValueError("private casting state path must be absolute")
    current = absolute
    while True:
        if current.exists() or current.is_symlink():
            attributes = int(getattr(os.lstat(current), "st_file_attributes", 0))
            if current.is_symlink() or attributes & 0x400:
                raise ValueError(
                    "private casting state path has a reparse component"
                )
        parent = current.parent
        if parent == current:
            break
        current = parent
    if os.name == "nt":
        import ctypes

        drive_root = PureWindowsPath(str(absolute)).anchor
        if not drive_root:
            raise ValueError("private casting state path has no local drive")
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_root)
        if drive_type != 3:
            raise ValueError("private casting state must be on a fixed local drive")


def _validate_uuid(value: Any, *, label: str, allow_empty: bool = False) -> None:
    text = str(value)
    if allow_empty and text == "":
        return
    try:
        parsed = uuid.UUID(text)
    except (AttributeError, ValueError) as error:
        raise ValueError(f"private casting state {label} is not a UUID") from error
    if str(parsed) != text.casefold():
        raise ValueError(f"private casting state {label} is not canonical")


def _validate_utc_timestamp(
    value: Any,
    *,
    label: str,
    allow_empty: bool = False,
) -> None:
    text = str(value)
    if allow_empty and text == "":
        return
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"private casting state {label} is not an ISO-8601 timestamp"
        ) from error
    if parsed.tzinfo is None:
        raise ValueError(f"private casting state {label} is not UTC-qualified")


def _validate_private_state(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("private casting state must be one object")
    required = {
        "$schema",
        "session_id",
        "phase",
        "serial",
        "coordination_mode",
        "quest_lease_id",
        "casting_exe",
        "adb_exe",
        "cache_dir",
        "casting_sha256",
        "profile_id",
        "feature_profile_sha256",
        "features",
        "launch_arguments_sha256",
        "pid",
        "process_creation_time_utc",
        "stdout_log",
        "stderr_log",
        "updated_at_utc",
    }
    if set(value) != required:
        raise ValueError("private casting state fields do not match the closed schema")
    if value["$schema"] != STATE_SCHEMA:
        raise ValueError("private casting state has an unsupported schema")
    _validate_uuid(value["session_id"], label="session_id")
    phase = str(value["phase"])
    if phase not in STATE_PHASES:
        raise ValueError("private casting state phase is unsupported")
    validate_serial(str(value["serial"]))
    coordination_mode = str(value["coordination_mode"])
    if coordination_mode not in {"agent-board", "user-supervised"}:
        raise ValueError("private casting state coordination_mode is unsupported")
    if coordination_mode == "agent-board":
        _validate_uuid(value["quest_lease_id"], label="quest_lease_id")
    elif value["quest_lease_id"] != "":
        raise ValueError("user-supervised private state must not contain a lease id")

    casting_path = PureWindowsPath(str(value["casting_exe"]))
    if not casting_path.is_absolute() or casting_path.name.casefold() != "casting.exe":
        raise ValueError("private casting state casting_exe is not an absolute Casting.exe path")
    adb_path = PureWindowsPath(str(value["adb_exe"]))
    expected_adb_path = casting_path.parent.parent / "adb.exe"
    if adb_path != expected_adb_path:
        raise ValueError("private casting state adb_exe is outside the reviewed install layout")
    cache_path = PureWindowsPath(str(value["cache_dir"]))
    if (
        not cache_path.is_absolute()
        or tuple(part.casefold() for part in cache_path.parts[-2:])
        != ("odh", "casting")
    ):
        raise ValueError("private casting state cache_dir is not an ODH casting cache")
    profiles = {
        str(profile["profile_id"]): profile
        for profile in COMPATIBILITY_PROFILES.values()
    }
    profile = profiles.get(str(value["profile_id"]))
    if profile is None:
        raise ValueError("private casting state profile_id is unsupported")
    if str(value["casting_sha256"]) != str(profile["casting_sha256"]):
        raise ValueError("private casting state Casting hash does not match its profile")
    expected_feature_hash = _sha256_json(list(profile["features"]))
    if str(value["feature_profile_sha256"]) != expected_feature_hash:
        raise ValueError("private casting state feature hash does not match its profile")
    if value["features"] != list(profile["features"]):
        raise ValueError("private casting state features do not match their profile")
    expected_arguments = _launch_arguments(
        {
            "adb_exe": str(adb_path),
            "cache_dir": str(cache_path),
        },
        serial=str(value["serial"]),
        session_id=str(value["session_id"]),
        features=list(value["features"]),
    )
    if str(value["launch_arguments_sha256"]) != _sha256_json(expected_arguments):
        raise ValueError("private casting state launch arguments do not match their profile")

    pid = value["pid"]
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 0:
        raise ValueError("private casting state pid is invalid")
    creation_time = str(value["process_creation_time_utc"])
    if phase != "starting" and (pid <= 0 or not creation_time):
        raise ValueError("active private casting state lacks exact process identity")
    _validate_utc_timestamp(
        creation_time,
        label="process_creation_time_utc",
        allow_empty=phase == "starting",
    )
    _validate_utc_timestamp(value["updated_at_utc"], label="updated_at_utc")
    for field in ("stdout_log", "stderr_log"):
        log_path = PureWindowsPath(str(value[field]))
        if not log_path.is_absolute() or str(value["session_id"]) not in log_path.parts:
            raise ValueError(f"private casting state {field} is not session-scoped")


def _base_receipt(action: str, operation_id: str) -> dict[str, Any]:
    return {
        "$schema": RECEIPT_SCHEMA,
        "schema_version": 1,
        "action": action,
        "operation_id": operation_id,
        "observed_at_utc": _utc_now(),
        "outcome": "blocked",
        "reason_code": "not_evaluated",
        "authority": {
            "lifecycle_owner": "Rusty Hostess",
            "casting_runtime_owner": "Meta Platforms",
            "device_service_owner": "Meta Platforms",
        },
        "transport": {
            "owner": "Meta Platforms",
            "observability": "opaque",
            "frame_access": False,
            "hostess_media_route": False,
        },
        "compatibility": None,
        "device": None,
        "session": None,
        "presentation": None,
        "recording": None,
        "cleanup": None,
        "issues": [],
    }


def _issue(code: str, detail: str) -> dict[str, str]:
    return {"code": code[:96], "detail": detail[:512]}


def _presentation_observation(
    *,
    window_observed: bool,
    readiness: str = "unconfirmed",
    cinematic_mode: str = "unconfirmed",
) -> dict[str, Any]:
    return {
        "window_observed": window_observed,
        "presentation_ready": readiness,
        "cinematic_mode": cinematic_mode,
    }


def _recording_observation() -> dict[str, Any]:
    return {
        "requested": False,
        "active": "unconfirmed",
        "finalized": "unconfirmed",
        "artifact": None,
    }


def validate_meta_quest_casting_receipt_semantics(
    receipt: dict[str, Any],
) -> None:
    presentation = receipt.get("presentation")
    if isinstance(presentation, dict):
        if (
            presentation.get("presentation_ready") == "observed_ready"
            and not presentation.get("window_observed")
        ):
            raise CheckedSchemaError(
                "Meta Quest casting receipt: readiness requires an observed window"
            )
        if (
            presentation.get("cinematic_mode")
            == "observed_cinematic_16_9"
            and presentation.get("presentation_ready") != "observed_ready"
        ):
            raise CheckedSchemaError(
                "Meta Quest casting receipt: Cinematic mode requires presentation readiness"
            )

    recording = receipt.get("recording")
    if isinstance(recording, dict):
        requested = recording.get("requested") is True
        finalized = recording.get("finalized") == "observed_finalized"
        artifact = recording.get("artifact")
        if recording.get("active") == "observed_active" and not requested:
            raise CheckedSchemaError(
                "Meta Quest casting receipt: active recording must be requested"
            )
        if finalized and (not requested or artifact is None):
            raise CheckedSchemaError(
                "Meta Quest casting receipt: finalized recording requires its request and artifact"
            )
        if artifact is not None and not finalized:
            raise CheckedSchemaError(
                "Meta Quest casting receipt: artifact requires observed finalization"
            )

    cleanup = receipt.get("cleanup")
    if isinstance(cleanup, dict):
        if (
            cleanup.get("host_process_exited") is True
            and cleanup.get("identity_confirmed") is not True
        ):
            raise CheckedSchemaError(
                "Meta Quest casting receipt: host-process exit requires confirmed ownership"
            )
        if cleanup.get("cleanup_complete") is True and not (
            cleanup.get("host_process_exited") is True
            and cleanup.get("device_session_stopped") == "observed_stopped"
            and cleanup.get("fov_restored") == "observed_restored"
        ):
            raise CheckedSchemaError(
                "Meta Quest casting receipt: complete cleanup requires all owner effects"
            )


def capability_descriptor() -> dict[str, Any]:
    profiles = []
    for mqdh_version, profile in sorted(COMPATIBILITY_PROFILES.items()):
        profiles.append(
            {
                "mqdh_version": mqdh_version,
                "mqdh_sha256": profile["mqdh_sha256"],
                "mqdh_signer_thumbprint": profile["mqdh_signer_thumbprint"],
                "casting_sha256": profile["casting_sha256"],
                "signer_thumbprint": profile["signer_thumbprint"],
                "adb_sha256": profile["adb_sha256"],
                "adb_api_sha256": profile["adb_api_sha256"],
                "adb_usb_api_sha256": profile["adb_usb_api_sha256"],
                "adb_signer_thumbprint": profile["adb_signer_thumbprint"],
                "companion_version_name": profile["companion_version_name"],
                "companion_version_code": profile["companion_version_code"],
                "feature_profile_id": profile["profile_id"],
                "feature_profile_sha256": _sha256_json(list(profile["features"])),
            }
        )
    return {
        "$schema": DESCRIPTOR_SCHEMA,
        "schema_version": 1,
        "provider_id": "rusty-hostess-meta-quest-casting",
        "owner": "Rusty Hostess",
        "provider_runtime_owner": "Meta Platforms",
        "host_platform": "windows",
        "hostess_contract_version": "1.0.0-experimental.1",
        "authorizes_execution": False,
        "actions": [
            {
                "id": "describe",
                "mutation": False,
                "target_required": False,
                "receipt_schema": DESCRIPTOR_SCHEMA,
            },
            {
                "id": "doctor",
                "mutation": False,
                "target_required": True,
                "receipt_schema": RECEIPT_SCHEMA,
            },
            {
                "id": "start",
                "mutation": True,
                "target_required": True,
                "receipt_schema": RECEIPT_SCHEMA,
            },
            {
                "id": "status",
                "mutation": False,
                "target_required": False,
                "receipt_schema": RECEIPT_SCHEMA,
            },
            {
                "id": "stop",
                "mutation": True,
                "target_required": False,
                "receipt_schema": RECEIPT_SCHEMA,
            },
        ],
        "compatibility_profiles": profiles,
        "exclusions": [
            "no_meta_binary_redistribution",
            "no_arbitrary_argument_passthrough",
            "no_adb_daemon_lifecycle",
            "no_transport_or_frame_access",
            "no_process_or_window_effectiveness_claim",
            "no_recording_claim_without_finalized_artifact",
        ],
    }


def validate_serial(serial: str) -> None:
    if (
        not SERIAL_PATTERN.fullmatch(serial)
        or serial.casefold() in REJECTED_SERIALS
        or serial.strip() != serial
    ):
        raise ValueError("serial must be one exact non-placeholder ADB identity")


def parse_adb_devices(output: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices attached") or line.startswith("*"):
            continue
        fields = line.split()
        if len(fields) < 2:
            continue
        properties: dict[str, str] = {}
        for field in fields[2:]:
            if ":" in field:
                key, value = field.split(":", 1)
                properties[key] = value
        devices.append(
            {
                "serial": fields[0],
                "state": fields[1],
                "product": properties.get("product", ""),
                "model": properties.get("model", ""),
                "device": properties.get("device", ""),
                "transport_id": properties.get("transport_id", ""),
            }
        )
    return devices


def parse_companion_package(output: str) -> dict[str, str]:
    version_name = re.search(r"^\s*versionName=(\S+)", output, re.MULTILINE)
    version_code = re.search(r"^\s*versionCode=(\d+)", output, re.MULTILINE)
    return {
        "package": COMPANION_PACKAGE,
        "installed": bool(version_name and version_code),
        "version_name": version_name.group(1) if version_name else "",
        "version_code": version_code.group(1) if version_code else "",
    }


def _compatibility_observation(installation: dict[str, Any]) -> dict[str, Any]:
    version = str(installation.get("mqdh_version", "")).strip()
    profile = COMPATIBILITY_PROFILES.get(version)
    signature_status = str(installation.get("signature_status", ""))
    observed_mqdh_hash = str(installation.get("mqdh_sha256", "")).upper()
    observed_mqdh_thumbprint = str(
        installation.get("mqdh_signer_thumbprint", "")
    ).upper()
    observed_hash = str(installation.get("casting_sha256", "")).upper()
    observed_thumbprint = str(installation.get("signer_thumbprint", "")).upper()
    observed_adb_hash = str(installation.get("adb_sha256", "")).upper()
    observed_adb_api_hash = str(installation.get("adb_api_sha256", "")).upper()
    observed_adb_usb_api_hash = str(
        installation.get("adb_usb_api_sha256", "")
    ).upper()
    observed_adb_thumbprint = str(
        installation.get("adb_signer_thumbprint", "")
    ).upper()
    observed_adb_api_thumbprint = str(
        installation.get("adb_api_signer_thumbprint", "")
    ).upper()
    observed_adb_usb_api_thumbprint = str(
        installation.get("adb_usb_api_signer_thumbprint", "")
    ).upper()
    supported = bool(
        installation.get("files_present")
        and installation.get("canonical_install_root")
        and not installation.get("install_path_has_reparse_component")
        and not installation.get("casting_is_reparse_point")
        and not installation.get("adb_is_reparse_point")
        and not installation.get("adb_dependency_is_reparse_point")
        and profile
        and str(installation.get("mqdh_signature_status", "")) == "Valid"
        and observed_mqdh_hash == profile["mqdh_sha256"]
        and observed_mqdh_thumbprint == profile["mqdh_signer_thumbprint"]
        and signature_status == "Valid"
        and observed_hash == profile["casting_sha256"]
        and observed_thumbprint == profile["signer_thumbprint"]
        and str(installation.get("adb_signature_status", "")) == "Valid"
        and observed_adb_hash == profile["adb_sha256"]
        and observed_adb_api_hash == profile["adb_api_sha256"]
        and observed_adb_usb_api_hash == profile["adb_usb_api_sha256"]
        and observed_adb_thumbprint == profile["adb_signer_thumbprint"]
        and str(installation.get("adb_api_signature_status", "")) == "Valid"
        and str(installation.get("adb_usb_api_signature_status", "")) == "Valid"
        and observed_adb_api_thumbprint == profile["adb_signer_thumbprint"]
        and observed_adb_usb_api_thumbprint == profile["adb_signer_thumbprint"]
    )
    return {
        "mqdh_version": version,
        "mqdh_signature_status": str(
            installation.get("mqdh_signature_status", "")
        ),
        "mqdh_signer_thumbprint": observed_mqdh_thumbprint,
        "mqdh_sha256": observed_mqdh_hash,
        "files_present": bool(installation.get("files_present")),
        "canonical_install_root": bool(installation.get("canonical_install_root")),
        "install_path_has_reparse_component": bool(
            installation.get("install_path_has_reparse_component")
        ),
        "casting_is_reparse_point": bool(
            installation.get("casting_is_reparse_point")
        ),
        "adb_is_reparse_point": bool(installation.get("adb_is_reparse_point")),
        "adb_dependency_is_reparse_point": bool(
            installation.get("adb_dependency_is_reparse_point")
        ),
        "signature_status": signature_status,
        "signer_subject": str(installation.get("signer_subject", "")),
        "signer_thumbprint": observed_thumbprint,
        "casting_sha256": observed_hash,
        "adb_signature_status": str(
            installation.get("adb_signature_status", "")
        ),
        "adb_signer_thumbprint": observed_adb_thumbprint,
        "adb_sha256": observed_adb_hash,
        "adb_api_signature_status": str(
            installation.get("adb_api_signature_status", "")
        ),
        "adb_api_signer_thumbprint": observed_adb_api_thumbprint,
        "adb_api_sha256": observed_adb_api_hash,
        "adb_usb_api_signature_status": str(
            installation.get("adb_usb_api_signature_status", "")
        ),
        "adb_usb_api_signer_thumbprint": observed_adb_usb_api_thumbprint,
        "adb_usb_api_sha256": observed_adb_usb_api_hash,
        "supported": supported,
        "profile_id": str(profile["profile_id"]) if profile else "",
        "feature_profile_sha256": (
            _sha256_json(list(profile["features"])) if profile else ""
        ),
        "features": list(profile["features"]) if profile else [],
    }


def _collect_doctor(
    adapter: Any,
    serial: str,
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, str]], dict[str, Any]]:
    validate_serial(serial)
    installation = adapter.discover_installation()
    compatibility = _compatibility_observation(installation)
    issues: list[dict[str, str]] = []
    device: dict[str, Any] | None = None

    if not compatibility["files_present"]:
        issues.append(_issue("mqdh_installation_incomplete", "Required Meta files are missing."))
    elif not compatibility["canonical_install_root"]:
        issues.append(
            _issue(
                "noncanonical_mqdh_installation_rejected",
                "The closed profile accepts only the standard protected MQDH install root.",
            )
        )
    elif compatibility["install_path_has_reparse_component"]:
        issues.append(
            _issue(
                "mqdh_reparse_ancestry_rejected",
                "The MQDH runtime path contains a reparse component.",
            )
        )
    elif compatibility["casting_is_reparse_point"]:
        issues.append(
            _issue(
                "casting_reparse_point_rejected",
                "Casting.exe is a reparse point; the closed profile requires a regular file.",
            )
        )
    elif compatibility["adb_is_reparse_point"]:
        issues.append(
            _issue(
                "adb_reparse_point_rejected",
                "The bundled adb.exe is a reparse point; the closed profile requires a regular file.",
            )
        )
    elif compatibility["adb_dependency_is_reparse_point"]:
        issues.append(
            _issue(
                "adb_dependency_reparse_point_rejected",
                "An adjacent ADB runtime DLL is a reparse point; regular files are required.",
            )
        )
    elif not compatibility["supported"]:
        issues.append(
            _issue(
                "unsupported_meta_build",
                "Meta signature, version, or Casting hash is outside the closed profile.",
            )
        )
    if issues:
        return compatibility, device, issues, installation

    if not adapter.adb_server_running():
        issues.append(
            _issue(
                "adb_server_not_running",
                "The wrapper will not start or restart the shared ADB daemon.",
            )
        )
        return compatibility, device, issues, installation

    adb_result = adapter.run_adb(
        installation["adb_exe"],
        ["devices", "-l"],
    )
    if adb_result.returncode != 0:
        issues.append(_issue("adb_devices_failed", "ADB device discovery failed."))
        return compatibility, device, issues, installation

    devices = parse_adb_devices(adb_result.stdout)
    matches = [candidate for candidate in devices if candidate["serial"] == serial]
    if len(matches) != 1:
        issues.append(
            _issue(
                "exact_device_not_found",
                "The requested serial was not present exactly once.",
            )
        )
        return compatibility, device, issues, installation
    selected = matches[0]
    device = {
        **selected,
        "transport": "usb" if ":" not in serial else "network",
        "companion": {
            "package": COMPANION_PACKAGE,
            "installed": False,
            "version_name": "",
            "version_code": "",
        },
    }
    if selected["state"] != "device":
        issues.append(
            _issue(
                f"device_{selected['state']}",
                "The exact Quest is not in the authorized device state.",
            )
        )
        return compatibility, device, issues, installation
    if device["transport"] != "usb":
        issues.append(
            _issue(
                "usb_transport_required",
                "The first compatibility profile accepts USB ADB only.",
            )
        )
        return compatibility, device, issues, installation

    package_result = adapter.run_adb(
        installation["adb_exe"],
        ["-s", serial, "shell", "dumpsys", "package", COMPANION_PACKAGE],
    )
    if package_result.returncode == 0:
        device["companion"] = parse_companion_package(package_result.stdout)
    if not device["companion"]["installed"]:
        issues.append(
            _issue(
                "meta_companion_missing",
                "The Meta Magic Island casting service is not installed.",
            )
        )
    else:
        profile = COMPATIBILITY_PROFILES.get(compatibility["mqdh_version"])
        if profile and (
            device["companion"]["version_name"]
            != profile["companion_version_name"]
            or device["companion"]["version_code"]
            != profile["companion_version_code"]
        ):
            issues.append(
                _issue(
                    "unsupported_meta_companion_build",
                    "The installed Meta casting companion is outside the closed profile.",
                )
            )
    return compatibility, device, issues, installation


def _paths_match(left: str, right: str) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
        os.path.abspath(right)
    )


def _installation_identity_matches(
    earlier: dict[str, Any],
    current: dict[str, Any],
) -> bool:
    path_fields = ("root", "mqdh_exe", "casting_exe", "adb_exe", "cache_dir")
    if not all(
        _paths_match(str(earlier.get(field, "")), str(current.get(field, "")))
        for field in path_fields
    ):
        return False
    return _compatibility_observation(earlier) == _compatibility_observation(current)


def _wait_seconds_are_valid(value: Any) -> bool:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return False
    return seconds >= 0.0 and seconds <= 120.0


def _process_matches_state(process: dict[str, Any] | None, state: dict[str, Any]) -> bool:
    if process is None:
        return False
    return bool(
        int(process.get("pid", -1)) == int(state["pid"])
        and _paths_match(
            str(process.get("executable_path", "")),
            str(state["casting_exe"]),
        )
        and str(process.get("creation_time_utc", ""))
        == str(state["process_creation_time_utc"])
        and _process_command_matches_state(process, state)
    )


def _split_windows_command_line(command_line: str) -> list[str]:
    if os.name != "nt":
        raise ValueError("Windows command-line parsing is unavailable")
    import ctypes

    argc = ctypes.c_int()
    command_line_to_argv = ctypes.windll.shell32.CommandLineToArgvW
    command_line_to_argv.argtypes = [
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    command_line_to_argv.restype = ctypes.POINTER(ctypes.c_wchar_p)
    argv_pointer = command_line_to_argv(command_line, ctypes.byref(argc))
    if not argv_pointer:
        raise ValueError("process command line could not be parsed")
    try:
        return [argv_pointer[index] for index in range(argc.value)]
    finally:
        local_free = ctypes.windll.kernel32.LocalFree
        local_free.argtypes = [ctypes.c_void_p]
        local_free.restype = ctypes.c_void_p
        local_free(argv_pointer)


def _process_command_matches_state(
    process: dict[str, Any],
    state: dict[str, Any],
) -> bool:
    try:
        arguments = _split_windows_command_line(
            str(process.get("command_line", ""))
        )
    except ValueError:
        return False
    return bool(
        len(arguments) >= 2
        and _sha256_json(arguments[1:])
        == str(state["launch_arguments_sha256"])
    )


def _process_is_recovery_candidate(
    process: dict[str, Any],
    state: dict[str, Any],
) -> bool:
    return bool(
        _paths_match(
            str(process.get("executable_path", "")),
            str(state["casting_exe"]),
        )
        and _process_command_matches_state(process, state)
        and int(process.get("pid", 0)) > 0
        and str(process.get("creation_time_utc", ""))
    )


def _observe_owned_process(
    adapter: Any,
    state: dict[str, Any],
    state_store: PrivateStateStore,
) -> dict[str, Any] | None:
    pid = int(state["pid"])
    if pid > 0:
        return adapter.inspect_process(pid)
    if state["phase"] != "starting":
        return None
    candidates = [
        process
        for process in adapter.list_casting_processes()
        if _process_is_recovery_candidate(process, state)
    ]
    if len(candidates) != 1:
        return None
    recovered = candidates[0]
    state["pid"] = int(recovered["pid"])
    state["process_creation_time_utc"] = str(
        recovered["creation_time_utc"]
    )
    state["phase"] = "launched_unconfirmed"
    state["updated_at_utc"] = _utc_now()
    state_store.write(state)
    return recovered


def _launch_arguments(
    installation: dict[str, Any],
    *,
    serial: str,
    session_id: str,
    features: list[str],
) -> list[str]:
    return [
        "--adb",
        str(installation["adb_exe"]),
        "--application-caches-dir",
        str(installation["cache_dir"]),
        "--exit-on-close",
        "--launch-surface",
        "MQDH",
        "--target-device",
        json.dumps({"id": serial}, separators=(",", ":")),
        "--features",
        *features,
        "--launch-surface-session-uuid",
        session_id,
    ]


def _write_checked_document(
    args: argparse.Namespace,
    document: dict[str, Any],
    schema_path: Path,
    *,
    label: str,
) -> None:
    load_and_validate_checked_schema(
        document,
        schema_path,
        label=label,
    )
    _atomic_write_json(Path(args.out), document)


def _write_receipt(args: argparse.Namespace, receipt: dict[str, Any]) -> None:
    validate_meta_quest_casting_receipt_semantics(receipt)
    _write_checked_document(
        args,
        receipt,
        RECEIPT_SCHEMA_PATH,
        label="Meta Quest casting receipt",
    )


def run_meta_quest_casting(
    args: argparse.Namespace,
    *,
    adapter: Any | None = None,
    state_store: PrivateStateStore | None = None,
    sleep_func: Callable[[float], None] = time.sleep,
) -> int:
    operation_id = str(uuid.uuid4())
    if args.meta_quest_casting_command == "describe":
        _write_checked_document(
            args,
            capability_descriptor(),
            DESCRIPTOR_SCHEMA_PATH,
            label="Meta Quest casting capability descriptor",
        )
        return 0
    receipt = _base_receipt(args.meta_quest_casting_command, operation_id)
    if adapter is None:
        if os.name != "nt":
            receipt["issues"] = [
                _issue(
                    "host_platform_unsupported",
                    "Meta Quest Developer Hub Casting is supported only on Windows.",
                )
            ]
            receipt["reason_code"] = "host_platform_unsupported"
            _write_receipt(args, receipt)
            return 3
        from tools.hostessctl.meta_quest_casting_windows import (
            WindowsMetaQuestCastingAdapter,
        )

        adapter = WindowsMetaQuestCastingAdapter()
    state_store = state_store or PrivateStateStore()
    operation_lock: BinaryIO | None = None
    launched_identity: dict[str, Any] | None = None

    try:
        if args.meta_quest_casting_command == "start" and not _wait_seconds_are_valid(
            args.startup_wait_seconds
        ):
            receipt["issues"] = [
                _issue(
                    "invalid_wait_seconds",
                    "Startup wait seconds must be finite and between 0 and 120.",
                )
            ]
            receipt["reason_code"] = "invalid_wait_seconds"
            _write_receipt(args, receipt)
            return 3
        if args.meta_quest_casting_command == "start":
            coordination_issue: dict[str, str] | None = None
            if args.coordination_mode == "agent-board":
                if not args.quest_lease_id:
                    coordination_issue = _issue(
                        "quest_lease_id_required",
                        "Agent Board coordination requires its exact lease id.",
                    )
                else:
                    try:
                        _validate_uuid(
                            args.quest_lease_id,
                            label="quest_lease_id",
                        )
                    except ValueError:
                        coordination_issue = _issue(
                            "invalid_quest_lease_id",
                            "Agent Board coordination requires a canonical lease UUID.",
                        )
            elif args.quest_lease_id:
                coordination_issue = _issue(
                    "unexpected_quest_lease_id",
                    "User-supervised coordination must not include a lease id.",
                )
            if coordination_issue is not None:
                receipt["issues"] = [coordination_issue]
                receipt["reason_code"] = coordination_issue["code"]
                _write_receipt(args, receipt)
                return 3
        if args.meta_quest_casting_command == "stop" and not _wait_seconds_are_valid(
            args.shutdown_wait_seconds
        ):
            receipt["issues"] = [
                _issue(
                    "invalid_wait_seconds",
                    "Shutdown wait seconds must be finite and between 0 and 120.",
                )
            ]
            receipt["reason_code"] = "invalid_wait_seconds"
            _write_receipt(args, receipt)
            return 3

        if args.meta_quest_casting_command in {"start", "status", "stop"}:
            operation_lock = state_store.try_acquire_operation_lock()
            if operation_lock is None:
                receipt["issues"] = [
                    _issue(
                        "operation_in_progress",
                        "Another Hostess casting lifecycle operation holds the private state lock.",
                    )
                ]
                receipt["reason_code"] = "operation_in_progress"
                _write_receipt(args, receipt)
                return 3

        if args.meta_quest_casting_command == "doctor":
            compatibility, device, issues, _ = _collect_doctor(adapter, args.serial)
            receipt["compatibility"] = compatibility
            receipt["device"] = device
            receipt["issues"] = issues
            receipt["outcome"] = "pass" if not issues else "blocked"
            receipt["reason_code"] = "ready" if not issues else issues[0]["code"]
            _write_receipt(args, receipt)
            return 0 if not issues else 3

        if args.meta_quest_casting_command == "start":
            compatibility, device, issues, installation = _collect_doctor(
                adapter, args.serial
            )
            receipt["compatibility"] = compatibility
            receipt["device"] = device
            if issues:
                receipt["issues"] = issues
                receipt["reason_code"] = issues[0]["code"]
                _write_receipt(args, receipt)
                return 3

            prior_state = state_store.load()
            if prior_state is not None:
                prior_process = _observe_owned_process(
                    adapter,
                    prior_state,
                    state_store,
                )
                if _process_matches_state(prior_process, prior_state):
                    receipt["issues"] = [
                        _issue(
                            "owned_session_already_active",
                            "A matching Hostess-owned Casting process is already active.",
                        )
                    ]
                    receipt["reason_code"] = "owned_session_already_active"
                    receipt["session"] = {
                        "session_id": prior_state["session_id"],
                        "phase": prior_state["phase"],
                        "pid": prior_state["pid"],
                        "process_creation_time_utc": prior_state[
                            "process_creation_time_utc"
                        ],
                        "main_window_observed": bool(
                            prior_process.get("main_window_handle")
                        ),
                    }
                    receipt["presentation"] = _presentation_observation(
                        window_observed=bool(prior_process.get("main_window_handle"))
                    )
                    receipt["recording"] = _recording_observation()
                    _write_receipt(args, receipt)
                    return 3
                state_store.clear()

            casting_path = str(installation["casting_exe"])
            external = [
                process
                for process in adapter.list_casting_processes()
                if _paths_match(
                    str(process.get("executable_path", "")),
                    casting_path,
                )
            ]
            if external:
                receipt["issues"] = [
                    _issue(
                        "external_casting_process_present",
                        "Hostess will not adopt or close a pre-existing Casting process.",
                    )
                ]
                receipt["reason_code"] = "external_casting_process_present"
                _write_receipt(args, receipt)
                return 3

            (
                current_compatibility,
                current_device,
                current_issues,
                current_installation,
            ) = _collect_doctor(adapter, args.serial)
            if not _installation_identity_matches(
                installation,
                current_installation,
            ):
                receipt["issues"] = [
                    _issue(
                        "meta_installation_changed_before_launch",
                        "The Meta executable identity changed after doctor checks; launch was refused.",
                    )
                ]
                receipt["reason_code"] = "meta_installation_changed_before_launch"
                receipt["compatibility"] = _compatibility_observation(
                    current_installation
                )
                _write_receipt(args, receipt)
                return 3
            if current_issues or current_device != device:
                receipt["issues"] = [
                    _issue(
                        "meta_device_changed_before_launch",
                        "The exact device or companion identity changed after preflight; launch was refused.",
                    )
                ]
                receipt["reason_code"] = "meta_device_changed_before_launch"
                receipt["compatibility"] = current_compatibility
                receipt["device"] = current_device
                _write_receipt(args, receipt)
                return 3
            installation = current_installation
            compatibility = current_compatibility
            device = current_device

            session_id = str(uuid.uuid4())
            arguments = _launch_arguments(
                installation,
                serial=args.serial,
                session_id=session_id,
                features=compatibility["features"],
            )
            state = {
                "$schema": STATE_SCHEMA,
                "session_id": session_id,
                "phase": "starting",
                "serial": args.serial,
                "coordination_mode": args.coordination_mode,
                "quest_lease_id": args.quest_lease_id or "",
                "casting_exe": casting_path,
                "adb_exe": str(installation["adb_exe"]),
                "cache_dir": str(installation["cache_dir"]),
                "casting_sha256": compatibility["casting_sha256"],
                "profile_id": compatibility["profile_id"],
                "feature_profile_sha256": compatibility["feature_profile_sha256"],
                "features": compatibility["features"],
                "launch_arguments_sha256": _sha256_json(arguments),
                "pid": 0,
                "process_creation_time_utc": "",
                "updated_at_utc": _utc_now(),
            }
            session_log_dir = state_store.path.parent / "sessions" / session_id
            state["stdout_log"] = str(session_log_dir / "casting.stdout.log")
            state["stderr_log"] = str(session_log_dir / "casting.stderr.log")
            state_store.write(state)
            launched_identity = adapter.launch_casting(
                casting_path,
                arguments,
                working_directory=str(Path(casting_path).parent),
                stdout_path=state["stdout_log"],
                stderr_path=state["stderr_log"],
            )
            pid = int(launched_identity["pid"])
            state["pid"] = pid
            state["process_creation_time_utc"] = str(
                launched_identity["creation_time_utc"]
            )
            state["updated_at_utc"] = _utc_now()
            state_store.write(state)

            sleep_func(float(args.startup_wait_seconds))
            process = adapter.inspect_process(pid)
            if not _process_matches_state(process, state):
                close_result = adapter.close_main_window_if_matches(
                    int(launched_identity["pid"]),
                    executable_path=str(launched_identity["executable_path"]),
                    creation_time_utc=str(
                        launched_identity["creation_time_utc"]
                    ),
                )
                state["phase"] = "failed"
                state["updated_at_utc"] = _utc_now()
                state_store.write(state)
                receipt["issues"] = [
                    _issue(
                        "casting_exited_during_startup",
                        "Casting.exe identity was missing or changed during startup.",
                    )
                ]
                receipt["reason_code"] = "casting_exited_during_startup"
                receipt["session"] = {
                    "session_id": session_id,
                    "phase": "failed",
                    "pid": pid,
                    "process_creation_time_utc": state[
                        "process_creation_time_utc"
                    ],
                    "main_window_observed": False,
                }
                receipt["presentation"] = _presentation_observation(
                    window_observed=False
                )
                receipt["recording"] = _recording_observation()
                receipt["cleanup"] = {
                    "identity_confirmed": bool(
                        close_result["identity_matched"]
                    ),
                    "graceful_close_requested": bool(
                        close_result["close_requested"]
                    ),
                    "host_process_exited": bool(
                        close_result["identity_matched"] and process is None
                    ),
                    "forced_termination": False,
                    "device_session_stopped": "unconfirmed",
                    "fov_restored": "unconfirmed",
                    "cleanup_complete": False,
                }
                _write_receipt(args, receipt)
                return 3

            state["phase"] = (
                "active"
                if int(process.get("main_window_handle", 0)) != 0
                else "launched_unconfirmed"
            )
            state["updated_at_utc"] = _utc_now()
            state_store.write(state)
            receipt["session"] = {
                "session_id": session_id,
                "phase": state["phase"],
                "pid": pid,
                "process_creation_time_utc": process["creation_time_utc"],
                "main_window_observed": bool(process.get("main_window_handle")),
            }
            receipt["presentation"] = _presentation_observation(
                window_observed=bool(process.get("main_window_handle"))
            )
            receipt["recording"] = _recording_observation()
            receipt["outcome"] = state["phase"]
            receipt["reason_code"] = (
                "casting_window_observed"
                if state["phase"] == "active"
                else "casting_window_not_observed"
            )
            _write_receipt(args, receipt)
            return 0 if state["phase"] == "active" else 3

        state = state_store.load()
        if state is None:
            receipt["outcome"] = "inactive"
            receipt["reason_code"] = "no_owned_session"
            _write_receipt(args, receipt)
            return 0
        process = _observe_owned_process(adapter, state, state_store)
        matches = _process_matches_state(process, state)
        receipt["session"] = {
            "session_id": state["session_id"],
            "phase": state["phase"] if matches else "stale",
            "pid": state["pid"],
            "process_creation_time_utc": state["process_creation_time_utc"],
            "main_window_observed": bool(
                matches and process and process.get("main_window_handle")
            ),
        }
        receipt["presentation"] = _presentation_observation(
            window_observed=bool(
                matches and process and process.get("main_window_handle")
            )
        )
        receipt["recording"] = _recording_observation()

        if args.meta_quest_casting_command == "status":
            if matches:
                if state["phase"] in {
                    "failed",
                    "stopping",
                    "failed_pending_cleanup",
                }:
                    receipt["outcome"] = "cleanup_incomplete"
                    receipt["reason_code"] = (
                        f"owned_process_{state['phase']}"
                    )
                    receipt["issues"] = [
                        _issue(
                            "owned_process_requires_cleanup",
                            "The exact process is alive but its persisted lifecycle is not active.",
                        )
                    ]
                    _write_receipt(args, receipt)
                    return 3
                receipt["outcome"] = "active"
                receipt["reason_code"] = "owned_process_identity_confirmed"
                _write_receipt(args, receipt)
                return 0
            receipt["outcome"] = "inactive"
            receipt["reason_code"] = "owned_process_missing_or_changed"
            receipt["issues"] = [
                _issue(
                    "owned_process_missing_or_changed",
                    "PID, executable path, or creation time no longer matches state.",
                )
            ]
            _write_receipt(args, receipt)
            return 3

        if args.meta_quest_casting_command == "stop":
            if not matches:
                state_store.clear()
                receipt["outcome"] = "inactive"
                receipt["reason_code"] = "stale_state_cleared"
                receipt["cleanup"] = {
                    "identity_confirmed": False,
                    "graceful_close_requested": False,
                    "host_process_exited": False,
                    "forced_termination": False,
                    "device_session_stopped": "unconfirmed",
                    "fov_restored": "unconfirmed",
                    "cleanup_complete": False,
                }
                _write_receipt(args, receipt)
                return 0

            state["phase"] = "stopping"
            state["updated_at_utc"] = _utc_now()
            state_store.write(state)
            close_result = adapter.close_main_window_if_matches(
                int(state["pid"]),
                executable_path=str(state["casting_exe"]),
                creation_time_utc=str(state["process_creation_time_utc"]),
            )
            if not close_result["identity_matched"]:
                state["phase"] = "failed_pending_cleanup"
                state["updated_at_utc"] = _utc_now()
                state_store.write(state)
                receipt["cleanup"] = {
                    "identity_confirmed": False,
                    "graceful_close_requested": False,
                    "host_process_exited": False,
                    "forced_termination": False,
                    "device_session_stopped": "unconfirmed",
                    "fov_restored": "unconfirmed",
                    "cleanup_complete": False,
                }
                receipt["outcome"] = "cleanup_incomplete"
                receipt["reason_code"] = "process_identity_changed_before_close"
                receipt["issues"] = [
                    _issue(
                        "process_identity_changed_before_close",
                        "The exact process identity changed before close; no window input was sent.",
                    )
                ]
                receipt["session"]["phase"] = "failed_pending_cleanup"
                _write_receipt(args, receipt)
                return 3
            close_requested = close_result["close_requested"]
            deadline = time.monotonic() + float(args.shutdown_wait_seconds)
            current = adapter.inspect_process(int(state["pid"]))
            owned_process_remains = _process_matches_state(current, state)
            while owned_process_remains and time.monotonic() < deadline:
                sleep_func(0.25)
                current = adapter.inspect_process(int(state["pid"]))
                owned_process_remains = _process_matches_state(current, state)
            exited = not owned_process_remains
            receipt["cleanup"] = {
                "identity_confirmed": True,
                "graceful_close_requested": close_requested,
                "host_process_exited": exited,
                "forced_termination": False,
                "device_session_stopped": "unconfirmed",
                "fov_restored": "unconfirmed",
                "cleanup_complete": False,
            }
            if exited:
                state_store.clear()
                receipt["outcome"] = "stopped"
                receipt["reason_code"] = (
                    "host_process_stopped_device_cleanup_unconfirmed"
                )
                receipt["session"]["phase"] = "stopped"
                _write_receipt(args, receipt)
                return 0
            state["phase"] = "failed_pending_cleanup"
            state["updated_at_utc"] = _utc_now()
            state_store.write(state)
            receipt["outcome"] = "cleanup_incomplete"
            receipt["reason_code"] = "graceful_close_failed"
            receipt["issues"] = [
                _issue(
                    "graceful_close_failed",
                    "The exact owned process remains alive; no forced kill was attempted.",
                )
            ]
            receipt["session"]["phase"] = "failed_pending_cleanup"
            _write_receipt(args, receipt)
            return 3
    except (CheckedSchemaError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        if launched_identity is not None:
            try:
                close_result = adapter.close_main_window_if_matches(
                    int(launched_identity["pid"]),
                    executable_path=str(launched_identity["executable_path"]),
                    creation_time_utc=str(
                        launched_identity["creation_time_utc"]
                    ),
                )
                receipt["cleanup"] = {
                    "identity_confirmed": bool(
                        close_result["identity_matched"]
                    ),
                    "graceful_close_requested": bool(
                        close_result["close_requested"]
                    ),
                    "host_process_exited": False,
                    "forced_termination": False,
                    "device_session_stopped": "unconfirmed",
                    "fov_restored": "unconfirmed",
                    "cleanup_complete": False,
                }
            except (OSError, RuntimeError, ValueError):
                pass
        receipt["issues"] = [_issue("adapter_error", str(error))]
        receipt["reason_code"] = "adapter_error"
        _write_receipt(args, receipt)
        return 3
    finally:
        if operation_lock is not None:
            state_store.release_operation_lock(operation_lock)
    return 2
