#!/usr/bin/env python3
"""Strict external operator and conformance client for Rusty Connection Hub.

Hostess owns the controller, test, and evidence projection only.  The Hub and
Manifold remain responsible for transport, admission, sessions, surfaces,
leases, replay, command acceptance, and revocation.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import getpass
import hashlib
import http.client
import ipaddress
import json
import math
import os
import re
import socket
import ssl
import struct
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SESSION_SCHEMA = "rusty.hostess.connection_hub_session.v1"
PAIR_REQUEST_SCHEMA = "rusty.quest.connection_hub.pair_request.v1"
PAIR_RECEIPT_SCHEMA = "rusty.quest.connection_hub.pair_receipt.v1"
REVOKE_REQUEST_SCHEMA = "rusty.quest.connection_hub.revoke_request.v1"
REVOKE_RECEIPT_SCHEMA = "rusty.quest.connection_hub.revoke_receipt.v1"
STATUS_SCHEMA = "rusty.quest.connection_hub.status.v1"
COMMAND_SCHEMA = "rusty.quest.connection_hub.surface_command.v1"
AUTHENTICATE_SCHEMA = "rusty.quest.connection_hub.socket_authenticate.v1"
AUTHENTICATION_RECEIPT_SCHEMA = (
    "rusty.quest.connection_hub.socket_authentication_receipt.v1"
)
COMMAND_SCHEMA_V2 = "rusty.quest.connection_hub.surface_command.v2"
AUTHENTICATE_SCHEMA_V2 = "rusty.quest.connection_hub.socket_authenticate.v2"
AUTHENTICATION_RECEIPT_SCHEMA_V2 = (
    "rusty.quest.connection_hub.socket_authentication_receipt.v2"
)
KEEPALIVE_SCHEMA_V2 = "rusty.quest.connection_hub.keepalive.v2"
KEEPALIVE_RECEIPT_SCHEMA_V2 = "rusty.quest.connection_hub.keepalive_receipt.v2"
COMMAND_RECEIPT_SCHEMA_V2 = "rusty.quest.connection_hub.command_receipt.v2"
PROTOCOL_ERROR_SCHEMA_V2 = "rusty.quest.connection_hub.protocol_error.v2"
PROTOCOL_ID_V1 = "rusty.quest.connection_hub.v1"
PROTOCOL_ID_V2 = "rusty.quest.connection_hub.v2"
PROTOCOL_ID = PROTOCOL_ID_V2
SUPPORTED_PROTOCOLS = frozenset({PROTOCOL_ID_V1, PROTOCOL_ID_V2})
CANONICAL_JSON_ID = "rusty.quest.connection_hub.canonical_json_ascii.v1"
EVENT_SCHEMAS = {
    "surface_snapshot": "rusty.quest.connection_hub.surface_snapshot.v1",
    "surface_available": "rusty.quest.connection_hub.surface_available.v1",
    "surface_removed": "rusty.quest.connection_hub.surface_removed.v1",
    "surface_state": "rusty.quest.connection_hub.surface_state.v1",
    "command_receipt": "rusty.quest.connection_hub.command_receipt.v1",
}
V2_EVENT_SCHEMAS = {
    "command_receipt": COMMAND_RECEIPT_SCHEMA_V2,
    "keepalive_receipt": KEEPALIVE_RECEIPT_SCHEMA_V2,
    "protocol_error": PROTOCOL_ERROR_SCHEMA_V2,
}
TRANSPORT_CLASSES = (
    "loopback_fixture",
    "adb_forward",
    "trusted_lan_experimental",
    "tls",
)
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
OPAQUE_SESSION = re.compile(r"^[A-Za-z0-9_-]{16,512}$")
PAIRING_CODE = re.compile(r"^[0-9]{6}$")
SIGNER_SHA256 = re.compile(r"^[a-f0-9]{64}$")
CONTRACT_SHA256 = re.compile(r"^sha256:[a-f0-9]{64}$")
PACKAGE_NAME = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
LISTENER_INSTANCE_ID = re.compile(r"^[a-f0-9]{32}$")
MAX_HTTP_BODY = 65536
MAX_SERVER_FRAME = 65536
MAX_COMMAND_BODY = 4096
MAX_SURFACES = 32
MAX_COMMANDS = 32
REVOKE_SOCKET_CLOSE_TIMEOUT_SECONDS = 3.0

EVENT_BASE_FIELDS = frozenset(
    {
        "$schema",
        "type",
        "transport_epoch",
        "listener_instance_id",
        "surface_revision",
        "transport_classification",
        "confidentiality",
        "production_eligible",
    }
)
MESSAGE_CONTRACTS: dict[
    str, tuple[str, str | None, frozenset[str], frozenset[str]]
] = {
    "status": (
        STATUS_SCHEMA,
        None,
        frozenset(
            {
                "$schema",
                "listener_enabled",
                "desired_connection_state",
                "pairing_available",
                "status",
                "transport_classification",
                "confidentiality",
                "production_eligible",
            }
        ),
        frozenset(),
    ),
    "pair_request": (
        PAIR_REQUEST_SCHEMA,
        None,
        frozenset({"$schema", "pairing_code", "controller_identity_sha256"}),
        frozenset(),
    ),
    "pair_receipt": (
        PAIR_RECEIPT_SCHEMA,
        "pair_receipt",
        EVENT_BASE_FIELDS | {"accepted", "status"},
        frozenset({"session", "expires_at_utc", "authority_receipt"}),
    ),
    "socket_authenticate": (
        AUTHENTICATE_SCHEMA,
        "authenticate",
        frozenset({"$schema", "type", "session"}),
        frozenset(),
    ),
    "socket_authentication_receipt": (
        AUTHENTICATION_RECEIPT_SCHEMA,
        "authentication_receipt",
        frozenset(
            {
                "$schema",
                "type",
                "accepted",
                "status",
                "transport_epoch",
                "confidentiality",
                "production_eligible",
            }
        ),
        frozenset(),
    ),
    "socket_authenticate_v2": (
        AUTHENTICATE_SCHEMA_V2,
        "authenticate",
        frozenset({"$schema", "type", "session"}),
        frozenset(),
    ),
    "socket_authentication_receipt_v2": (
        AUTHENTICATION_RECEIPT_SCHEMA_V2,
        "authentication_receipt",
        frozenset(
            {
                "$schema",
                "type",
                "accepted",
                "status",
                "transport_epoch",
                "next_external_request_sequence",
                "expires_at_utc",
                "confidentiality",
                "production_eligible",
            }
        ),
        frozenset(),
    ),
    "surface_snapshot": (
        EVENT_SCHEMAS["surface_snapshot"],
        "surface_snapshot",
        EVENT_BASE_FIELDS | {"surfaces"},
        frozenset(),
    ),
    "surface_available": (
        EVENT_SCHEMAS["surface_available"],
        "surface_available",
        EVENT_BASE_FIELDS | {"surface"},
        frozenset(),
    ),
    "surface_removed": (
        EVENT_SCHEMAS["surface_removed"],
        "surface_removed",
        EVENT_BASE_FIELDS | {"surface_id", "reason"},
        frozenset(),
    ),
    "surface_state": (
        EVENT_SCHEMAS["surface_state"],
        "surface_state",
        EVENT_BASE_FIELDS | {"surface_id", "state_revision", "state"},
        frozenset(),
    ),
    "surface_command": (
        COMMAND_SCHEMA,
        "surface.command",
        frozenset({"$schema", "type", "request_id", "surface_id", "command", "args"}),
        frozenset(),
    ),
    "surface_command_v2": (
        COMMAND_SCHEMA_V2,
        "surface.command",
        frozenset(
            {
                "$schema",
                "type",
                "request_sequence",
                "request_id",
                "surface_id",
                "command",
                "args",
            }
        ),
        frozenset(),
    ),
    "command_receipt": (
        EVENT_SCHEMAS["command_receipt"],
        "command_receipt",
        EVENT_BASE_FIELDS
        | {
            "request_id",
            "surface_id",
            "command",
            "accepted",
            "provider_applied",
            "status",
            "authority_receipt",
        },
        frozenset(),
    ),
    "command_receipt_v2": (
        COMMAND_RECEIPT_SCHEMA_V2,
        "command_receipt",
        EVENT_BASE_FIELDS
        | {
            "request_sequence",
            "next_external_request_sequence",
            "request_id",
            "surface_id",
            "command",
            "accepted",
            "provider_applied",
            "status",
            "authority_receipt",
        },
        frozenset(),
    ),
    "keepalive_v2": (
        KEEPALIVE_SCHEMA_V2,
        "keepalive",
        frozenset({"$schema", "type", "request_sequence"}),
        frozenset(),
    ),
    "keepalive_receipt_v2": (
        KEEPALIVE_RECEIPT_SCHEMA_V2,
        "keepalive_receipt",
        EVENT_BASE_FIELDS
        | {
            "request_sequence",
            "next_external_request_sequence",
            "accepted",
            "status",
            "authority_receipt",
        },
        frozenset(),
    ),
    "protocol_error_v2": (
        PROTOCOL_ERROR_SCHEMA_V2,
        "protocol_error",
        EVENT_BASE_FIELDS | {"next_external_request_sequence", "status"},
        frozenset(),
    ),
    "revoke_request": (
        REVOKE_REQUEST_SCHEMA,
        None,
        frozenset({"$schema", "session"}),
        frozenset({"reason"}),
    ),
    "revoke_receipt": (
        REVOKE_RECEIPT_SCHEMA,
        "revoke_receipt",
        EVENT_BASE_FIELDS | {"applied", "status"},
        frozenset({"authority_receipt"}),
    ),
}


class HubError(RuntimeError):
    """Fail-closed protocol or operator-input error."""


class WebSocketClosed(HubError):
    def __init__(self, code: int, reason: str) -> None:
        super().__init__(f"websocket_closed:{code}:{reason}")
        self.code = code
        self.reason = reason


class AuthenticationRejected(HubError):
    """The Hub rejected the bearer during the mandatory first-frame exchange."""


class CredentialStore:
    """Abstract bearer protection; product callers must use an OS store."""

    provider = "abstract"

    def store(self, bearer: str, binding: bytes) -> dict[str, Any]:
        raise HubError("secure_credential_store_unavailable")

    def load(self, reference: dict[str, Any], binding: bytes) -> str:
        raise HubError("secure_credential_store_unavailable")

    def delete(self, reference: dict[str, Any]) -> None:
        raise HubError("secure_credential_store_unavailable")


class WindowsDpapiCredentialStore(CredentialStore):
    """Current-user DPAPI bearer protection with bound optional entropy."""

    provider = "windows_dpapi_current_user"

    class _DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.c_ulong),
            ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    def __init__(self) -> None:
        if os.name != "nt":
            raise HubError("windows_dpapi_unavailable")
        self._crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(self._DataBlob),
            ctypes.c_wchar_p,
            ctypes.POINTER(self._DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(self._DataBlob),
        ]
        self._crypt32.CryptProtectData.restype = ctypes.c_int
        self._crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(self._DataBlob),
            ctypes.POINTER(ctypes.c_wchar_p),
            ctypes.POINTER(self._DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(self._DataBlob),
        ]
        self._crypt32.CryptUnprotectData.restype = ctypes.c_int
        self._kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel32.LocalFree.restype = ctypes.c_void_p

    @classmethod
    def _blob(cls, value: bytes) -> tuple["WindowsDpapiCredentialStore._DataBlob", Any]:
        buffer = ctypes.create_string_buffer(value)
        blob = cls._DataBlob(
            len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        )
        return blob, buffer

    def store(self, bearer: str, binding: bytes) -> dict[str, Any]:
        source, source_buffer = self._blob(bearer.encode("ascii"))
        entropy, entropy_buffer = self._blob(binding)
        protected = self._DataBlob()
        if not self._crypt32.CryptProtectData(
            ctypes.byref(source),
            "Rusty Connection Hub session",
            ctypes.byref(entropy),
            None,
            None,
            0x1,
            ctypes.byref(protected),
        ):
            raise HubError(f"dpapi_protect_failed:{ctypes.get_last_error()}")
        del source_buffer, entropy_buffer
        try:
            payload = ctypes.string_at(protected.pbData, protected.cbData)
        finally:
            self._kernel32.LocalFree(protected.pbData)
        return {
            "provider": self.provider,
            "protected_blob_b64": base64.b64encode(payload).decode("ascii"),
        }

    def load(self, reference: dict[str, Any], binding: bytes) -> str:
        if set(reference) != {"provider", "protected_blob_b64"} or reference.get(
            "provider"
        ) != self.provider:
            raise HubError("credential_reference_invalid")
        try:
            payload = base64.b64decode(reference["protected_blob_b64"], validate=True)
        except (TypeError, ValueError) as error:
            raise HubError("dpapi_blob_invalid") from error
        source, source_buffer = self._blob(payload)
        entropy, entropy_buffer = self._blob(binding)
        clear = self._DataBlob()
        description = ctypes.c_wchar_p()
        if not self._crypt32.CryptUnprotectData(
            ctypes.byref(source),
            ctypes.byref(description),
            ctypes.byref(entropy),
            None,
            None,
            0x1,
            ctypes.byref(clear),
        ):
            raise HubError(f"dpapi_unprotect_failed:{ctypes.get_last_error()}")
        del source_buffer, entropy_buffer
        try:
            bearer = ctypes.string_at(clear.pbData, clear.cbData).decode("ascii")
        except UnicodeDecodeError as error:
            raise HubError("dpapi_bearer_not_ascii") from error
        finally:
            self._kernel32.LocalFree(clear.pbData)
            if description:
                self._kernel32.LocalFree(description)
        return bearer

    def delete(self, reference: dict[str, Any]) -> None:
        if reference.get("provider") != self.provider:
            raise HubError("credential_reference_provider_mismatch")


class MemoryCredentialStore(CredentialStore):
    """Process-local test double; never selected by the CLI."""

    provider = "test_in_memory"

    def __init__(self) -> None:
        self._values: dict[str, tuple[str, str]] = {}

    def store(self, bearer: str, binding: bytes) -> dict[str, Any]:
        reference = f"test-credential-{uuid.uuid4()}"
        self._values[reference] = (bearer, hashlib.sha256(binding).hexdigest())
        return {"provider": self.provider, "reference_id": reference}

    def load(self, reference: dict[str, Any], binding: bytes) -> str:
        if set(reference) != {"provider", "reference_id"} or reference.get(
            "provider"
        ) != self.provider:
            raise HubError("credential_reference_invalid")
        stored = self._values.get(str(reference["reference_id"]))
        if stored is None or stored[1] != hashlib.sha256(binding).hexdigest():
            raise HubError("credential_binding_mismatch")
        return stored[0]

    def delete(self, reference: dict[str, Any]) -> None:
        key = str(reference.get("reference_id", ""))
        if self._values.pop(key, None) is None:
            raise HubError("credential_reference_missing")


def default_credential_store() -> CredentialStore:
    if os.name != "nt":
        raise HubError("secure_credential_store_unavailable")
    return WindowsDpapiCredentialStore()


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def validate_protocol_message(value: Any, message_name: str) -> dict[str, Any]:
    """Apply an exact vendored Quest v1/v2 required/optional field registry."""

    if message_name not in MESSAGE_CONTRACTS:
        raise ValueError("protocol_message_name_unknown")
    if not isinstance(value, dict):
        raise HubError(f"{message_name}_must_be_object")
    schema, expected_type, required, optional = MESSAGE_CONTRACTS[message_name]
    if value.get("$schema") != schema:
        raise HubError(f"{message_name}_schema_mismatch")
    if expected_type is not None and value.get("type") != expected_type:
        raise HubError(f"{message_name}_type_mismatch")
    fields = set(value)
    if not required.issubset(fields) or not fields.issubset(required | optional):
        raise HubError(f"{message_name}_fields_invalid")
    return value


def request_id(prefix: str) -> str:
    value = f"{prefix}-{uuid.uuid4()}"
    if not TOKEN.fullmatch(value):
        raise HubError("generated_request_id_invalid")
    return value


def session_fingerprint(session: str) -> str:
    return hashlib.sha256(session.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class TransportPolicy:
    origin: str
    classification: str
    confidentiality: str
    production_ineligible: bool
    explicit_insecure_opt_in: bool

    def receipt(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "confidentiality": self.confidentiality,
            "explicit_insecure_opt_in": self.explicit_insecure_opt_in,
            "production_ineligible": self.production_ineligible,
        }


def transport_policy(
    origin: str,
    classification: str | None,
    allow_insecure_trusted_lan: bool = False,
) -> TransportPolicy:
    if classification not in TRANSPORT_CLASSES:
        raise ValueError("transport_classification_required")
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.port is None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("origin_must_be_an_explicit_http_root")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    is_loopback = parsed.hostname.lower() == "localhost" or bool(address and address.is_loopback)
    if classification in {"loopback_fixture", "adb_forward"}:
        if not is_loopback:
            raise ValueError(f"{classification}_requires_loopback_origin")
        if parsed.scheme != "http":
            raise ValueError(f"{classification}_expects_plain_loopback_http")
        return TransportPolicy(origin, classification, "none", True, False)
    if classification == "trusted_lan_experimental":
        if parsed.scheme != "http":
            raise ValueError("trusted_lan_experimental_requires_plain_http")
        if not allow_insecure_trusted_lan:
            raise ValueError("insecure_trusted_lan_requires_explicit_opt_in")
        if (
            address is None
            or is_loopback
            or not (address.is_private or address.is_link_local)
        ):
            raise ValueError("trusted_lan_origin_must_be_private_or_link_local")
        return TransportPolicy(origin, classification, "none", True, True)
    if parsed.scheme != "https":
        raise ValueError("tls_transport_requires_https")
    return TransportPolicy(origin, classification, "tls", False, False)


def _validated_server_transport(payload: dict[str, Any], policy: TransportPolicy) -> dict[str, Any]:
    observed_class = payload.get("transport_classification")
    confidentiality = payload.get("confidentiality")
    production_eligible = payload.get("production_eligible")
    if not isinstance(observed_class, str) or not observed_class:
        raise HubError("server_transport_classification_missing")
    if confidentiality not in {"none", "tls"} or not isinstance(production_eligible, bool):
        raise HubError("server_transport_posture_invalid")
    if policy.classification == "trusted_lan_experimental":
        if observed_class != "trusted_lan_experimental" or confidentiality != "none":
            raise HubError("trusted_lan_server_posture_mismatch")
        if production_eligible:
            raise HubError("plaintext_server_must_be_production_ineligible")
    if policy.classification == "loopback_fixture" and observed_class != "loopback_fixture":
        raise HubError("loopback_fixture_server_posture_mismatch")
    if policy.classification == "tls" and confidentiality != "tls":
        raise HubError("tls_server_posture_mismatch")
    return {
        "transport_classification": observed_class,
        "confidentiality": confidentiality,
        "production_eligible": production_eligible,
    }


def _validate_event_base(
    payload: dict[str, Any], policy: TransportPolicy, *, require_active_epoch: bool
) -> dict[str, Any]:
    epoch = payload.get("transport_epoch")
    revision = payload.get("surface_revision")
    listener = payload.get("listener_instance_id")
    if (
        not isinstance(epoch, int)
        or isinstance(epoch, bool)
        or epoch < (1 if require_active_epoch else 0)
    ):
        raise HubError("transport_epoch_invalid")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise HubError("surface_revision_invalid")
    if not isinstance(listener, str) or not LISTENER_INSTANCE_ID.fullmatch(listener):
        raise HubError("listener_instance_id_invalid")
    if payload.get("confidentiality") != policy.confidentiality:
        raise HubError("server_confidentiality_mismatch")
    return _validated_server_transport(payload, policy)


def _connection(parsed: Any, timeout: float = 5.0) -> http.client.HTTPConnection:
    if parsed.scheme == "https":
        return http.client.HTTPSConnection(
            parsed.hostname,
            parsed.port,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
    return http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=timeout)


def http_json(
    policy: TransportPolicy,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    if method not in {"GET", "POST"} or path not in {"/v1/status", "/v1/pair", "/v1/revoke"}:
        raise ValueError("http_route_not_registered")
    parsed = urlsplit(policy.origin)
    encoded = None if body is None else canonical_json(body)
    connection = _connection(parsed)
    try:
        connection.request(
            method,
            path,
            body=encoded,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": policy.origin,
            },
        )
        response = connection.getresponse()
        raw = response.read(MAX_HTTP_BODY + 1)
    finally:
        connection.close()
    if len(raw) > MAX_HTTP_BODY:
        raise HubError("http_response_too_large")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HubError("http_response_not_json") from error
    if not isinstance(payload, dict):
        raise HubError("http_response_must_be_object")
    return response.status, payload


def status(policy: TransportPolicy) -> dict[str, Any]:
    code, payload = http_json(policy, "GET", "/v1/status")
    if code != 200:
        raise HubError(f"status_rejected:{code}")
    validate_protocol_message(payload, "status")
    if not isinstance(payload.get("listener_enabled"), bool):
        raise HubError("status_listener_state_invalid")
    if payload.get("desired_connection_state") not in {"stopped", "running"}:
        raise HubError("status_desired_connection_state_invalid")
    if not isinstance(payload.get("pairing_available"), bool):
        raise HubError("status_pairing_state_invalid")
    if not isinstance(payload.get("status"), str) or not payload["status"]:
        raise HubError("status_value_invalid")
    observed = _validated_server_transport(payload, policy)
    return {
        "$schema": "rusty.hostess.connection_hub.status_receipt.v1",
        "status": "passed",
        "transport": policy.receipt(),
        "server_transport": observed,
        "hub": payload,
    }


def _security_binding(
    policy: TransportPolicy,
    payload: dict[str, Any],
    session_digest: str,
    controller_identity_sha256: str,
    socket_protocol: str,
) -> dict[str, Any]:
    if socket_protocol not in SUPPORTED_PROTOCOLS:
        raise ValueError("socket_protocol_not_supported")
    return {
        "origin": policy.origin,
        "protocol": socket_protocol,
        "transport": policy.receipt(),
        "server_transport": _validated_server_transport(payload, policy),
        "session_fingerprint_sha256": session_digest,
        "controller_identity_sha256": controller_identity_sha256,
    }


def _session_document(
    payload: dict[str, Any],
    binding: dict[str, Any],
    credential: dict[str, Any],
) -> dict[str, Any]:
    binding_bytes = canonical_json(binding)
    return {
        "$schema": SESSION_SCHEMA,
        "security_binding": binding,
        "security_binding_sha256": hashlib.sha256(binding_bytes).hexdigest(),
        "credential": credential,
        "expires_at_utc": payload.get("expires_at_utc"),
        "last_transport_epoch": payload.get("transport_epoch"),
    }


def _atomic_write_json(path: Path, value: dict[str, Any], *, create: bool) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if create:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        return
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _reserve_session_file(path: Path) -> Path:
    """Reserve the metadata destination before creating a remote session."""

    reserved = path.resolve()
    reserved.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(reserved, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    return reserved


def _remove_reserved_session_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError as error:
        raise HubError("reserved_session_metadata_cleanup_failed") from error


def _preflight_credential_store(
    store: CredentialStore,
    policy: TransportPolicy,
    controller_identity_sha256: str,
    socket_protocol: str,
) -> None:
    """Prove protect/load/delete before the irreversible remote pair call."""

    probe = "credential-preflight-" + uuid.uuid4().hex
    binding = canonical_json(
        {
            "controller_identity_sha256": controller_identity_sha256,
            "origin": policy.origin,
            "protocol": socket_protocol,
            "purpose": "credential_store_preflight",
        }
    )
    reference: dict[str, Any] | None = None
    try:
        reference = store.store(probe, binding)
        if store.load(reference, binding) != probe:
            raise HubError("credential_store_preflight_roundtrip_mismatch")
    finally:
        if reference is not None:
            store.delete(reference)


def _compensating_revoke(policy: TransportPolicy, session: str) -> dict[str, Any]:
    """Close a remotely accepted session when local persistence cannot commit."""

    request = {
        "$schema": REVOKE_REQUEST_SCHEMA,
        "session": session,
        "reason": "user_request",
    }
    validate_protocol_message(request, "revoke_request")
    code, payload = http_json(policy, "POST", "/v1/revoke", request)
    if payload.get("$schema") != REVOKE_RECEIPT_SCHEMA:
        raise HubError(
            f"pair_compensating_revoke_rejected:{code}:{payload.get('status', 'unknown')}"
        )
    validate_protocol_message(payload, "revoke_receipt")
    if code != 200:
        raise HubError(
            f"pair_compensating_revoke_rejected:{code}:{payload.get('status', 'unknown')}"
        )
    _validate_event_base(payload, policy, require_active_epoch=True)
    if payload.get("applied") is not True:
        raise HubError(
            f"pair_compensating_revoke_rejected:{code}:{payload.get('status', 'unknown')}"
        )
    return payload


def pair(
    policy: TransportPolicy,
    pairing_code: str,
    controller_identity_sha256: str,
    session_file: Path,
    credential_store: CredentialStore | None = None,
    socket_protocol: str = PROTOCOL_ID_V2,
) -> dict[str, Any]:
    if not PAIRING_CODE.fullmatch(pairing_code):
        raise ValueError("pairing_code_must_be_six_digits")
    if not SIGNER_SHA256.fullmatch(controller_identity_sha256):
        raise ValueError("controller_identity_sha256_invalid")
    if socket_protocol not in SUPPORTED_PROTOCOLS:
        raise ValueError("socket_protocol_not_supported")
    store = credential_store or default_credential_store()
    reserved = _reserve_session_file(session_file)
    remote_session: str | None = None
    credential: dict[str, Any] | None = None
    committed = False
    try:
        _preflight_credential_store(
            store, policy, controller_identity_sha256, socket_protocol
        )
        request = {
            "$schema": PAIR_REQUEST_SCHEMA,
            "pairing_code": pairing_code,
            "controller_identity_sha256": controller_identity_sha256,
        }
        validate_protocol_message(request, "pair_request")
        code, payload = http_json(policy, "POST", "/v1/pair", request)
        candidate_session = payload.get("session")
        if (
            payload.get("$schema") == PAIR_RECEIPT_SCHEMA
            and payload.get("accepted") is True
            and isinstance(candidate_session, str)
            and OPAQUE_SESSION.fullmatch(candidate_session)
        ):
            remote_session = candidate_session
        if payload.get("$schema") != PAIR_RECEIPT_SCHEMA:
            raise HubError(
                f"pair_rejected:{code}:{payload.get('status', 'unknown')}"
            )
        validate_protocol_message(payload, "pair_receipt")
        if code != 200:
            raise HubError(
                f"pair_rejected:{code}:{payload.get('status', 'unknown')}"
            )
        if payload.get("accepted") is not True:
            raise HubError(f"pair_not_accepted:{payload.get('status', 'unknown')}")
        if remote_session is None:
            raise HubError("pair_session_invalid")
        if not isinstance(payload.get("expires_at_utc"), str):
            raise HubError("pair_expiry_invalid")
        if "authority_receipt" in payload and not isinstance(
            payload["authority_receipt"], dict
        ):
            raise HubError("pair_authority_receipt_invalid")
        _validate_event_base(payload, policy, require_active_epoch=True)
        session_digest = session_fingerprint(remote_session)
        binding = _security_binding(
            policy,
            payload,
            session_digest,
            controller_identity_sha256,
            socket_protocol,
        )
        binding_bytes = canonical_json(binding)
        credential = store.store(remote_session, binding_bytes)
        document = _session_document(payload, binding, credential)
        _atomic_write_json(reserved, document, create=False)
        committed = True
    except BaseException as original_error:
        rollback_error: BaseException | None = None
        if remote_session is not None:
            try:
                _compensating_revoke(policy, remote_session)
            except BaseException as error:
                rollback_error = error
        if credential is not None:
            try:
                store.delete(credential)
            except BaseException as error:
                rollback_error = rollback_error or error
        try:
            _remove_reserved_session_file(reserved)
        except BaseException as error:
            rollback_error = rollback_error or error
        if rollback_error is not None:
            raise HubError("pair_transaction_rollback_unconfirmed") from rollback_error
        raise original_error
    finally:
        if not committed and reserved.exists():
            _remove_reserved_session_file(reserved)
    redacted = {key: value for key, value in payload.items() if key != "session"}
    return {
        "$schema": "rusty.hostess.connection_hub.pair_receipt.v2",
        "status": "passed",
        "session_redacted": True,
        "session_fingerprint_sha256": session_digest,
        "session_file": str(session_file.resolve()),
        "transport": policy.receipt(),
        "socket_protocol": socket_protocol,
        "rollover_safe": socket_protocol == PROTOCOL_ID_V2,
        "server_receipt": redacted,
    }


def load_session(
    path: Path, credential_store: CredentialStore | None = None
) -> tuple[dict[str, Any], TransportPolicy, str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HubError("session_file_unreadable") from error
    if not isinstance(document, dict) or document.get("$schema") != SESSION_SCHEMA:
        raise HubError("session_file_schema_mismatch")
    if set(document) - {
        "$schema",
        "security_binding",
        "security_binding_sha256",
        "credential",
        "expires_at_utc",
        "last_transport_epoch",
        "last_surface_revision",
    }:
        raise HubError("session_file_fields_invalid")
    binding = document.get("security_binding")
    if not isinstance(binding, dict) or set(binding) != {
        "origin",
        "protocol",
        "transport",
        "server_transport",
        "session_fingerprint_sha256",
        "controller_identity_sha256",
    }:
        raise HubError("session_file_security_binding_invalid")
    binding_bytes = canonical_json(binding)
    if document.get("security_binding_sha256") != hashlib.sha256(binding_bytes).hexdigest():
        raise HubError("session_file_security_binding_mismatch")
    if binding.get("protocol") not in SUPPORTED_PROTOCOLS:
        raise HubError("session_file_protocol_mismatch")
    if not SIGNER_SHA256.fullmatch(str(binding.get("controller_identity_sha256", ""))):
        raise HubError("session_file_controller_identity_invalid")
    if not SIGNER_SHA256.fullmatch(str(binding.get("session_fingerprint_sha256", ""))):
        raise HubError("session_file_token_digest_invalid")
    transport = binding.get("transport")
    if not isinstance(transport, dict):
        raise HubError("session_file_transport_missing")
    policy = transport_policy(
        binding.get("origin", ""),
        transport.get("classification"),
        bool(transport.get("explicit_insecure_opt_in")),
    )
    if policy.receipt() != transport:
        raise HubError("session_file_transport_mismatch")
    server_transport = binding.get("server_transport")
    if not isinstance(server_transport, dict):
        raise HubError("session_file_server_transport_missing")
    _validated_server_transport(server_transport, policy)
    credential = document.get("credential")
    if not isinstance(credential, dict):
        raise HubError("session_file_credential_missing")
    store = credential_store or default_credential_store()
    if credential.get("provider") != store.provider:
        raise HubError("credential_store_provider_mismatch")
    session = store.load(credential, binding_bytes)
    if not OPAQUE_SESSION.fullmatch(session):
        raise HubError("credential_session_invalid")
    if binding["session_fingerprint_sha256"] != session_fingerprint(session):
        raise HubError("session_file_fingerprint_mismatch")
    return document, policy, session


def validate_args(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or len(value) > 16:
        raise ValueError("command_args_must_be_an_object_with_at_most_16_keys")
    for key, item in value.items():
        if not isinstance(key, str) or not TOKEN.fullmatch(key):
            raise ValueError("command_arg_key_invalid")
        if isinstance(item, str):
            if len(item) > 256:
                raise ValueError("command_arg_string_too_long")
        elif item is not None and not isinstance(item, (bool, int)):
            raise ValueError("command_args_must_be_flat_scalars")
    if len(canonical_json(value)) > MAX_COMMAND_BODY:
        raise ValueError("command_args_too_large")
    return value


def validate_surface(descriptor: Any) -> dict[str, Any]:
    if not isinstance(descriptor, dict) or descriptor.get("schema_version") != 1:
        raise HubError("surface_descriptor_schema_invalid")
    if set(descriptor) != {
        "schema_version",
        "surface_id",
        "display_label",
        "description",
        "surface_contract_sha256",
        "provider_package",
        "provider_signer_sha256",
        "commands",
        "state",
        "state_revision",
    }:
        raise HubError("surface_descriptor_fields_invalid")
    required_strings = ("surface_id", "display_label", "description", "provider_package")
    if any(not isinstance(descriptor.get(key), str) for key in required_strings):
        raise HubError("surface_descriptor_string_missing")
    if not TOKEN.fullmatch(descriptor["surface_id"]):
        raise HubError("surface_id_invalid")
    if not PACKAGE_NAME.fullmatch(descriptor["provider_package"]):
        raise HubError("surface_provider_package_invalid")
    if len(descriptor["display_label"]) > 96 or len(descriptor["description"]) > 160:
        raise HubError("surface_text_out_of_bounds")
    if not SIGNER_SHA256.fullmatch(str(descriptor.get("provider_signer_sha256", ""))):
        raise HubError("surface_provider_signer_invalid")
    if not CONTRACT_SHA256.fullmatch(str(descriptor.get("surface_contract_sha256", ""))):
        raise HubError("surface_contract_sha256_invalid")
    commands = descriptor.get("commands")
    if not isinstance(commands, list) or len(commands) > MAX_COMMANDS:
        raise HubError("surface_commands_invalid")
    seen: set[str] = set()
    for item in commands:
        if not isinstance(item, dict) or set(item) != {
            "command",
            "display_label",
            "required_controller_capability",
        }:
            raise HubError("surface_command_descriptor_invalid")
        command = item["command"]
        label = item["display_label"]
        capability = item["required_controller_capability"]
        if not isinstance(command, str) or not TOKEN.fullmatch(command) or command in seen:
            raise HubError("surface_command_invalid")
        if not isinstance(label, str) or len(label) > 96:
            raise HubError("surface_command_label_invalid")
        if not isinstance(capability, str) or not TOKEN.fullmatch(capability):
            raise HubError("surface_command_capability_invalid")
        seen.add(command)
    validate_args(descriptor.get("state"))
    if not isinstance(descriptor.get("state_revision"), int) or isinstance(
        descriptor.get("state_revision"), bool
    ):
        raise HubError("surface_state_revision_invalid")
    return descriptor


@dataclass
class WebSocketClient:
    sock: socket.socket
    _receive_buffer: bytearray = field(default_factory=bytearray, init=False, repr=False)

    @classmethod
    def connect(
        cls, policy: TransportPolicy, session: str, protocol_id: str
    ) -> "WebSocketClient":
        if protocol_id not in SUPPORTED_PROTOCOLS:
            raise ValueError("socket_protocol_not_supported")
        parsed = urlsplit(policy.origin)
        raw = socket.create_connection((parsed.hostname, parsed.port), timeout=5)
        if parsed.scheme == "https":
            raw = ssl.create_default_context().wrap_socket(raw, server_hostname=parsed.hostname)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET /v1/socket HTTP/1.1\r\n"
            f"Host: {parsed.netloc}\r\n"
            f"Origin: {policy.origin}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Key: {key}\r\n\r\n"
        )
        raw.sendall(request.encode("ascii"))
        head = cls._read_http_head(raw)
        lines = head.split("\r\n")
        if lines[0] != "HTTP/1.1 101 Switching Protocols":
            raw.close()
            raise HubError(f"websocket_upgrade_rejected:{lines[0]}")
        headers = {
            name.strip().lower(): value.strip()
            for name, value in (line.split(":", 1) for line in lines[1:] if ":" in line)
        }
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        if headers.get("sec-websocket-accept") != expected:
            raw.close()
            raise HubError("websocket_accept_mismatch")
        result = cls(raw)
        authentication = {
            "$schema": (
                AUTHENTICATE_SCHEMA_V2
                if protocol_id == PROTOCOL_ID_V2
                else AUTHENTICATE_SCHEMA
            ),
            "type": "authenticate",
            "session": session,
        }
        validate_protocol_message(
            authentication,
            "socket_authenticate_v2"
            if protocol_id == PROTOCOL_ID_V2
            else "socket_authenticate",
        )
        result.send_json(authentication)
        return result

    @staticmethod
    def _read_http_head(sock: socket.socket) -> str:
        data = bytearray()
        while not data.endswith(b"\r\n\r\n"):
            chunk = sock.recv(1)
            if not chunk:
                raise HubError("websocket_upgrade_eof")
            data.extend(chunk)
            if len(data) > 8192:
                raise HubError("websocket_upgrade_too_large")
        return data[:-4].decode("ascii")

    def _read_exact(self, length: int) -> bytes:
        if length < 0:
            raise ValueError("websocket_read_length_invalid")
        while len(self._receive_buffer) < length:
            chunk = self.sock.recv(length - len(self._receive_buffer))
            if not chunk:
                raise WebSocketClosed(1006, "eof")
            self._receive_buffer.extend(chunk)
        value = bytes(self._receive_buffer[:length])
        del self._receive_buffer[:length]
        return value

    def send_json(self, value: dict[str, Any]) -> None:
        payload = canonical_json(value)
        self.send_text_bytes(payload)

    def send_text_bytes(self, payload: bytes) -> None:
        if len(payload) > MAX_COMMAND_BODY:
            raise ValueError("websocket_command_too_large")
        try:
            payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("websocket_text_payload_not_utf8") from error
        self._send_frame(0x1, payload)

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        if len(payload) > 65535:
            raise ValueError("websocket_client_frame_too_large")
        mask = os.urandom(4)
        if len(payload) < 126:
            header = bytes((0x80 | opcode, 0x80 | len(payload)))
        else:
            header = bytes((0x80 | opcode, 0x80 | 126)) + struct.pack("!H", len(payload))
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def read_json(self, timeout: float = 6.0) -> dict[str, Any]:
        self.sock.settimeout(timeout)
        while True:
            first, second = self._read_exact(2)
            if not first & 0x80:
                raise HubError("fragmented_server_frame_rejected")
            opcode = first & 0x0F
            if second & 0x80:
                raise HubError("masked_server_frame_rejected")
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                raise HubError("large_server_frame_rejected")
            if length > MAX_SERVER_FRAME:
                raise HubError("server_frame_too_large")
            payload = self._read_exact(length)
            if opcode == 0x8:
                code = struct.unpack("!H", payload[:2])[0] if len(payload) >= 2 else 1005
                reason = payload[2:].decode("utf-8", errors="replace")
                raise WebSocketClosed(code, reason)
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode != 0x1:
                continue
            try:
                value = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise HubError("server_frame_not_json") from error
            if not isinstance(value, dict):
                raise HubError("server_event_must_be_object")
            return value

    def close(self) -> None:
        try:
            self._send_frame(0x8, struct.pack("!H", 1000))
        except OSError:
            pass
        self.sock.close()


class HubConnection:
    def __init__(
        self,
        policy: TransportPolicy,
        session: str,
        protocol_id: str = PROTOCOL_ID_V2,
    ) -> None:
        if protocol_id not in SUPPORTED_PROTOCOLS:
            raise ValueError("socket_protocol_not_supported")
        self.policy = policy
        self.session = session
        self.protocol_id = protocol_id
        self.socket = WebSocketClient.connect(policy, session, protocol_id)
        self.transport_epoch: Any = None
        self.next_external_request_sequence: int | None = None
        self.expires_at_utc: str | None = None
        self.listener_instance_id: str | None = None
        self.surface_revision: Any = None
        self.surfaces: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        try:
            self.authentication_receipt = self.socket.read_json()
        except (WebSocketClosed, OSError) as error:
            self.close()
            raise AuthenticationRejected("socket_authentication_rejected") from error
        try:
            validate_protocol_message(
                self.authentication_receipt,
                "socket_authentication_receipt_v2"
                if protocol_id == PROTOCOL_ID_V2
                else "socket_authentication_receipt",
            )
        except BaseException:
            self.close()
            raise
        accepted = self.authentication_receipt.get("accepted")
        if (
            not isinstance(accepted, bool)
            or self.authentication_receipt.get("confidentiality") != "none"
            or self.authentication_receipt.get("production_eligible") is not False
        ):
            self.close()
            raise HubError("socket_authentication_receipt_invalid")
        auth_epoch = self.authentication_receipt.get("transport_epoch")
        if not isinstance(auth_epoch, int) or isinstance(auth_epoch, bool) or auth_epoch < 1:
            self.close()
            raise HubError("socket_authentication_epoch_invalid")
        self.transport_epoch = auth_epoch
        if protocol_id == PROTOCOL_ID_V2:
            next_sequence = self.authentication_receipt.get(
                "next_external_request_sequence"
            )
            expires_at_utc = self.authentication_receipt.get("expires_at_utc")
            if (
                not isinstance(next_sequence, int)
                or isinstance(next_sequence, bool)
                or next_sequence < 1
            ):
                self.close()
                raise HubError("socket_authentication_next_sequence_invalid")
            if not isinstance(expires_at_utc, str) or not expires_at_utc:
                self.close()
                raise HubError("socket_authentication_expiry_invalid")
            self.next_external_request_sequence = next_sequence
            self.expires_at_utc = expires_at_utc
        if accepted is False:
            if self.authentication_receipt.get("status") != "authentication_rejected":
                self.close()
                raise HubError("socket_authentication_rejection_status_invalid")
            self.close()
            raise AuthenticationRejected("socket_authentication_rejected")
        if self.authentication_receipt.get("status") != "authenticated":
            self.close()
            raise HubError("socket_authentication_receipt_invalid")
        first = self.read_event()
        if first.get("type") != "surface_snapshot":
            self.close()
            raise HubError("first_event_must_be_surface_snapshot")

    def _validate_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if self.protocol_id == PROTOCOL_ID_V2 and event_type in V2_EVENT_SCHEMAS:
            contract_name = f"{event_type}_v2"
        elif event_type in EVENT_SCHEMAS:
            contract_name = str(event_type)
        elif event_type in V2_EVENT_SCHEMAS:
            raise HubError("v2_event_on_legacy_socket")
        else:
            raise HubError("server_event_schema_mismatch")
        validate_protocol_message(event, contract_name)
        _validate_event_base(event, self.policy, require_active_epoch=True)
        epoch = event.get("transport_epoch")
        if self.transport_epoch is None:
            self.transport_epoch = epoch
        elif epoch != self.transport_epoch:
            raise HubError("transport_epoch_changed_within_socket")
        listener_instance_id = event.get("listener_instance_id")
        if self.listener_instance_id is None:
            self.listener_instance_id = listener_instance_id
        elif listener_instance_id != self.listener_instance_id:
            raise HubError("listener_instance_id_changed_within_socket")
        revision = event.get("surface_revision")
        if self.surface_revision is not None and revision < self.surface_revision:
            raise HubError("surface_revision_regressed")
        if event_type in {"command_receipt", "keepalive_receipt"}:
            if not isinstance(event.get("accepted"), bool) or not isinstance(
                event.get("provider_applied", False), bool
            ):
                raise HubError("sequenced_receipt_boolean_invalid")
            if not isinstance(event.get("authority_receipt"), dict):
                raise HubError("sequenced_authority_receipt_invalid")
            if not isinstance(event.get("status"), str) or not event["status"]:
                raise HubError("sequenced_status_invalid")
            if self.protocol_id == PROTOCOL_ID_V2:
                for field in (
                    "request_sequence",
                    "next_external_request_sequence",
                ):
                    value = event.get(field)
                    if (
                        not isinstance(value, int)
                        or isinstance(value, bool)
                        or value < 1
                    ):
                        raise HubError(f"sequenced_receipt_{field}_invalid")
        if event_type == "protocol_error" and (
            not isinstance(event.get("status"), str) or not event["status"]
        ):
            raise HubError("protocol_error_status_invalid")
        if event_type == "protocol_error":
            next_sequence = event.get("next_external_request_sequence")
            if (
                not isinstance(next_sequence, int)
                or isinstance(next_sequence, bool)
                or next_sequence < 1
            ):
                raise HubError("protocol_error_next_sequence_invalid")
        self.surface_revision = revision

    def _project(self, event: dict[str, Any]) -> None:
        event_type = event["type"]
        if event_type == "surface_snapshot":
            surfaces = event.get("surfaces")
            if not isinstance(surfaces, list) or len(surfaces) > MAX_SURFACES:
                raise HubError("surface_snapshot_out_of_bounds")
            projected = [validate_surface(item) for item in surfaces]
            if len({item["surface_id"] for item in projected}) != len(projected):
                raise HubError("surface_snapshot_duplicate_id")
            self.surfaces = {item["surface_id"]: item for item in projected}
        elif event_type == "surface_available":
            descriptor = validate_surface(event.get("surface"))
            self.surfaces[descriptor["surface_id"]] = descriptor
        elif event_type == "surface_removed":
            surface_id = event.get("surface_id")
            if not isinstance(surface_id, str) or not TOKEN.fullmatch(surface_id):
                raise HubError("removed_surface_id_invalid")
            self.surfaces.pop(surface_id, None)
        elif event_type == "surface_state":
            surface_id = event.get("surface_id")
            state = validate_args(event.get("state"))
            state_revision = event.get("state_revision")
            if surface_id not in self.surfaces or not isinstance(state_revision, int):
                raise HubError("surface_state_target_invalid")
            updated = dict(self.surfaces[surface_id])
            updated["state"] = state
            updated["state_revision"] = state_revision
            self.surfaces[surface_id] = updated

    def read_event(self, timeout: float = 6.0) -> dict[str, Any]:
        event = self.socket.read_json(timeout)
        self._validate_event(event)
        self._project(event)
        self.events.append(event)
        return event

    def await_type(self, event_type: str, timeout: float = 6.0) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            event = self.read_event(max(0.05, deadline - time.monotonic()))
            if event.get("type") == event_type:
                return event
        raise HubError(f"event_timeout:{event_type}")

    def _require_v2_next_sequence(self) -> int:
        sequence = self.next_external_request_sequence
        if (
            self.protocol_id != PROTOCOL_ID_V2
            or not isinstance(sequence, int)
            or isinstance(sequence, bool)
            or sequence < 1
        ):
            raise HubError("sequenced_v2_socket_required")
        return sequence

    def _accept_sequenced_receipt(
        self,
        receipt: dict[str, Any],
        requested_sequence: int,
        expected_before: int,
    ) -> None:
        receipt_sequence = receipt.get("request_sequence")
        next_sequence = receipt.get("next_external_request_sequence")
        if receipt_sequence != requested_sequence:
            raise HubError("sequenced_receipt_request_sequence_mismatch")
        if (
            not isinstance(next_sequence, int)
            or isinstance(next_sequence, bool)
            or next_sequence < 1
        ):
            raise HubError("sequenced_receipt_next_sequence_invalid")
        if receipt.get("accepted") is True and requested_sequence != expected_before:
            raise HubError("sequenced_receipt_accepted_wrong_sequence")
        expected_next = expected_before + 1 if receipt.get("accepted") is True else expected_before
        if next_sequence != expected_next:
            raise HubError("sequenced_receipt_next_sequence_mismatch")
        self.next_external_request_sequence = next_sequence

    def send_keepalive(
        self,
        *,
        explicit_request_sequence: int | None = None,
        receipt_timeout_seconds: float = 6.0,
        max_events_to_read: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if (
            isinstance(receipt_timeout_seconds, bool)
            or not isinstance(receipt_timeout_seconds, (int, float))
            or not math.isfinite(float(receipt_timeout_seconds))
            or receipt_timeout_seconds <= 0
            or receipt_timeout_seconds > 6
        ):
            raise ValueError("keepalive_receipt_timeout_out_of_bounds")
        if max_events_to_read is not None and (
            isinstance(max_events_to_read, bool)
            or not isinstance(max_events_to_read, int)
            or max_events_to_read < 1
            or max_events_to_read > 512
        ):
            raise ValueError("keepalive_event_limit_out_of_bounds")
        expected_before = self._require_v2_next_sequence()
        sequence = (
            expected_before
            if explicit_request_sequence is None
            else explicit_request_sequence
        )
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise ValueError("request_sequence_must_be_positive")
        request = {
            "$schema": KEEPALIVE_SCHEMA_V2,
            "type": "keepalive",
            "request_sequence": sequence,
        }
        validate_protocol_message(request, "keepalive_v2")
        payload = canonical_json(request)
        self.socket.send_text_bytes(payload)
        deadline = time.monotonic() + float(receipt_timeout_seconds)
        events_read = 0
        while time.monotonic() < deadline:
            if max_events_to_read is not None and events_read >= max_events_to_read:
                raise HubError("keepalive_event_limit_reached")
            event = self.read_event(max(0.001, deadline - time.monotonic()))
            events_read += 1
            if event.get("type") == "protocol_error":
                raise HubError(f"protocol_error:{event.get('status', 'unknown')}")
            if event.get("type") == "keepalive_receipt":
                self._accept_sequenced_receipt(event, sequence, expected_before)
                return request, event
        raise HubError("keepalive_receipt_timeout")

    def send_command(
        self,
        surface_id: str,
        command: str,
        args: dict[str, Any],
        *,
        explicit_request_id: str | None = None,
        explicit_request_sequence: int | None = None,
        preflight: bool = True,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not TOKEN.fullmatch(surface_id) or not TOKEN.fullmatch(command):
            raise ValueError("surface_or_command_token_invalid")
        args = validate_args(args)
        if preflight:
            descriptor = self.surfaces.get(surface_id)
            if descriptor is None:
                raise HubError("surface_not_advertised")
            registered = {item["command"] for item in descriptor["commands"]}
            if command not in registered:
                raise HubError("command_not_advertised")
        use_request_id = explicit_request_id or request_id("hostess-command")
        if not TOKEN.fullmatch(use_request_id):
            raise ValueError("request_id_invalid")
        if self.protocol_id == PROTOCOL_ID_V2:
            expected_before = self._require_v2_next_sequence()
            sequence = (
                expected_before
                if explicit_request_sequence is None
                else explicit_request_sequence
            )
            if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
                raise ValueError("request_sequence_must_be_positive")
            request = {
                "$schema": COMMAND_SCHEMA_V2,
                "type": "surface.command",
                "request_sequence": sequence,
                "request_id": use_request_id,
                "surface_id": surface_id,
                "command": command,
                "args": args,
            }
            contract_name = "surface_command_v2"
        else:
            sequence = None
            expected_before = None
            if explicit_request_sequence is not None:
                raise ValueError("request_sequence_not_supported_by_legacy_v1")
            request = {
                "$schema": COMMAND_SCHEMA,
                "type": "surface.command",
                "request_id": use_request_id,
                "surface_id": surface_id,
                "command": command,
                "args": args,
            }
            contract_name = "surface_command"
        validate_protocol_message(request, contract_name)
        payload = canonical_json(request)
        self.socket.send_text_bytes(payload)
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            event = self.read_event(max(0.05, deadline - time.monotonic()))
            if event.get("type") == "protocol_error":
                raise HubError(f"protocol_error:{event.get('status', 'unknown')}")
            if event.get("type") == "command_receipt" and event.get("request_id") == use_request_id:
                if event.get("surface_id") != surface_id or event.get("command") != command:
                    raise HubError("command_receipt_causality_mismatch")
                if not isinstance(event.get("accepted"), bool):
                    raise HubError("command_receipt_acceptance_invalid")
                if sequence is not None:
                    assert expected_before is not None
                    self._accept_sequenced_receipt(
                        event, sequence, expected_before
                    )
                return request, event
        raise HubError("command_receipt_timeout")

    def close(self) -> None:
        self.socket.close()


def _document_session_fingerprint(document: dict[str, Any]) -> str:
    return document["security_binding"]["session_fingerprint_sha256"]


def connect_session(
    path: Path, credential_store: CredentialStore | None = None
) -> tuple[dict[str, Any], TransportPolicy, HubConnection, bool]:
    document, policy, session = load_session(path, credential_store)
    protocol_id = str(document["security_binding"]["protocol"])
    connection = HubConnection(policy, session, protocol_id)
    changed = document.get("last_transport_epoch") not in {None, connection.transport_epoch}
    document["last_transport_epoch"] = connection.transport_epoch
    document["last_surface_revision"] = connection.surface_revision
    if connection.expires_at_utc is not None:
        document["expires_at_utc"] = connection.expires_at_utc
    _atomic_write_json(path, document, create=False)
    return document, policy, connection, changed


def list_surfaces(
    path: Path, credential_store: CredentialStore | None = None
) -> dict[str, Any]:
    document, policy, connection, changed = connect_session(path, credential_store)
    try:
        surfaces = [connection.surfaces[key] for key in sorted(connection.surfaces)]
        return {
            "$schema": "rusty.hostess.connection_hub.surface_list_receipt.v2",
            "status": "passed",
            "session_fingerprint_sha256": _document_session_fingerprint(document),
            "transport": policy.receipt(),
            "transport_epoch": connection.transport_epoch,
            "transport_epoch_changed": changed,
            "socket_protocol": connection.protocol_id,
            "rollover_safe": connection.protocol_id == PROTOCOL_ID_V2,
            "next_external_request_sequence": connection.next_external_request_sequence,
            "expires_at_utc": connection.expires_at_utc,
            "surface_revision": connection.surface_revision,
            "surfaces": surfaces,
        }
    finally:
        connection.close()


def _advance_periodic_deadline(previous: float, interval: float, now: float) -> float:
    next_deadline = previous + interval
    while next_deadline <= now:
        next_deadline += interval
    return next_deadline


def wait_surface(
    path: Path,
    surface_id: str,
    expected_present: bool,
    seconds: float,
    credential_store: CredentialStore | None = None,
    keepalive_interval_seconds: float = 5.0,
    max_events: int = 128,
) -> dict[str, Any]:
    if not isinstance(surface_id, str) or not TOKEN.fullmatch(surface_id):
        raise ValueError("wait_surface_id_invalid")
    if not isinstance(expected_present, bool):
        raise ValueError("wait_surface_presence_invalid")
    if (
        isinstance(seconds, bool)
        or not isinstance(seconds, (int, float))
        or not math.isfinite(float(seconds))
        or seconds < 0.1
        or seconds > 60
    ):
        raise ValueError("wait_surface_seconds_out_of_bounds")
    if (
        isinstance(keepalive_interval_seconds, bool)
        or not isinstance(keepalive_interval_seconds, (int, float))
        or not math.isfinite(float(keepalive_interval_seconds))
        or keepalive_interval_seconds < 0.1
        or keepalive_interval_seconds > 10
    ):
        raise ValueError("wait_surface_keepalive_interval_out_of_bounds")
    if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 1 or max_events > 128:
        raise ValueError("wait_surface_event_limit_out_of_bounds")
    authentication_retry_count = 0
    try:
        document, policy, connection, changed = connect_session(path, credential_store)
    except AuthenticationRejected:
        authentication_retry_count = 1
        time.sleep(0.25)
        document, policy, connection, changed = connect_session(path, credential_store)
    started = time.monotonic()
    deadline = time.monotonic() + seconds
    next_keepalive = (
        time.monotonic() + keepalive_interval_seconds
        if connection.protocol_id == PROTOCOL_ID_V2
        else deadline
    )
    keepalive_count = 0
    try:
        while (surface_id in connection.surfaces) is not expected_present:
            if time.monotonic() >= deadline:
                raise HubError("wait_surface_timeout")
            if len(connection.events) >= max_events:
                raise HubError("wait_surface_event_limit_reached")
            if (
                connection.protocol_id == PROTOCOL_ID_V2
                and time.monotonic() >= next_keepalive
            ):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise HubError("wait_surface_timeout")
                _, keepalive_receipt = connection.send_keepalive(
                    receipt_timeout_seconds=min(6.0, remaining),
                    max_events_to_read=max_events - len(connection.events),
                )
                if keepalive_receipt.get("accepted") is not True:
                    raise HubError(
                        f"keepalive_rejected:{keepalive_receipt.get('status', 'unknown')}"
                    )
                keepalive_count += 1
                # Keep a fixed cadence instead of adding every receipt's
                # round-trip time to all later keepalives. If one receipt
                # crosses a cadence boundary, skip that missed slot rather
                # than emitting a catch-up burst.
                next_keepalive = _advance_periodic_deadline(
                    next_keepalive,
                    keepalive_interval_seconds,
                    time.monotonic(),
                )
                continue
            try:
                wait_until = min(deadline, next_keepalive)
                remaining = wait_until - time.monotonic()
                if remaining <= 0:
                    continue
                connection.read_event(min(0.25, remaining))
            except socket.timeout:
                continue
        return {
            "$schema": "rusty.hostess.connection_hub.wait_surface_receipt.v1",
            "status": "passed",
            "session_fingerprint_sha256": _document_session_fingerprint(document),
            "transport": policy.receipt(),
            "transport_epoch": connection.transport_epoch,
            "transport_epoch_changed": changed,
            "socket_protocol": connection.protocol_id,
            "rollover_safe": connection.protocol_id == PROTOCOL_ID_V2,
            "authentication_retry_count": authentication_retry_count,
            "surface_id": surface_id,
            "expected_present": expected_present,
            "observed_present": surface_id in connection.surfaces,
            "condition_satisfied": True,
            "surface": connection.surfaces.get(surface_id),
            "elapsed_milliseconds": int((time.monotonic() - started) * 1000),
            "timeout_seconds": seconds,
            "max_events": max_events,
            "keepalive_interval_seconds": (
                keepalive_interval_seconds
                if connection.protocol_id == PROTOCOL_ID_V2
                else None
            ),
            "keepalive_count": keepalive_count,
            "next_external_request_sequence": connection.next_external_request_sequence,
            "expires_at_utc": connection.expires_at_utc,
            "surface_revision": connection.surface_revision,
            "event_count": len(connection.events),
        }
    finally:
        connection.close()


def invoke_surface_command(
    path: Path,
    surface_id: str,
    command: str,
    args: dict[str, Any],
    credential_store: CredentialStore | None = None,
) -> dict[str, Any]:
    document, policy, connection, changed = connect_session(path, credential_store)
    try:
        request, receipt = connection.send_command(surface_id, command, args)
        if receipt.get("accepted") is not True:
            raise HubError(f"command_rejected:{receipt.get('status', 'unknown')}")
        return {
            "$schema": "rusty.hostess.connection_hub.command_receipt.v2",
            "operation_status": "passed",
            "status": receipt["status"],
            "surface_id": receipt["surface_id"],
            "command": receipt["command"],
            "request_id": receipt["request_id"],
            "request_binding_exact": receipt["request_id"] == request["request_id"]
            and receipt["surface_id"] == request["surface_id"]
            and receipt["command"] == request["command"]
            and (
                connection.protocol_id == PROTOCOL_ID_V1
                or receipt["request_sequence"] == request["request_sequence"]
            ),
            "authority_accepted": receipt["accepted"],
            "provider_applied": receipt["provider_applied"],
            "session_fingerprint_sha256": _document_session_fingerprint(document),
            "transport": policy.receipt(),
            "transport_epoch": connection.transport_epoch,
            "transport_epoch_changed": changed,
            "socket_protocol": connection.protocol_id,
            "rollover_safe": connection.protocol_id == PROTOCOL_ID_V2,
            "request_sequence": request.get("request_sequence"),
            "next_external_request_sequence": connection.next_external_request_sequence,
            "server_receipt": receipt,
        }
    finally:
        connection.close()


def watch(
    path: Path,
    seconds: float,
    max_events: int,
    credential_store: CredentialStore | None = None,
    keepalive_interval_seconds: float = 15.0,
) -> dict[str, Any]:
    if seconds < 0.1 or seconds > 300:
        raise ValueError("watch_seconds_out_of_bounds")
    if max_events < 1 or max_events > 512:
        raise ValueError("watch_event_limit_out_of_bounds")
    if keepalive_interval_seconds < 0.1 or keepalive_interval_seconds > 60:
        raise ValueError("watch_keepalive_interval_out_of_bounds")
    document, policy, connection, changed = connect_session(path, credential_store)
    deadline = time.monotonic() + seconds
    next_keepalive = (
        time.monotonic() + keepalive_interval_seconds
        if connection.protocol_id == PROTOCOL_ID_V2
        else deadline
    )
    keepalive_count = 0
    try:
        while time.monotonic() < deadline and len(connection.events) < max_events:
            if (
                connection.protocol_id == PROTOCOL_ID_V2
                and time.monotonic() >= next_keepalive
            ):
                _, keepalive_receipt = connection.send_keepalive()
                if keepalive_receipt.get("accepted") is not True:
                    raise HubError(
                        f"keepalive_rejected:{keepalive_receipt.get('status', 'unknown')}"
                    )
                keepalive_count += 1
                next_keepalive = _advance_periodic_deadline(
                    next_keepalive,
                    keepalive_interval_seconds,
                    time.monotonic(),
                )
                continue
            try:
                wait_until = min(deadline, next_keepalive)
                connection.read_event(
                    min(0.25, max(0.05, wait_until - time.monotonic()))
                )
            except socket.timeout:
                continue
        return {
            "$schema": "rusty.hostess.connection_hub.watch_receipt.v2",
            "status": "passed",
            "session_fingerprint_sha256": _document_session_fingerprint(document),
            "transport": policy.receipt(),
            "transport_epoch": connection.transport_epoch,
            "transport_epoch_changed": changed,
            "socket_protocol": connection.protocol_id,
            "rollover_safe": connection.protocol_id == PROTOCOL_ID_V2,
            "keepalive_interval_seconds": (
                keepalive_interval_seconds
                if connection.protocol_id == PROTOCOL_ID_V2
                else None
            ),
            "keepalive_count": keepalive_count,
            "next_external_request_sequence": connection.next_external_request_sequence,
            "surface_revision": connection.surface_revision,
            "event_count": len(connection.events),
            "events": connection.events,
        }
    finally:
        connection.close()


def _require_server_closed_socket(
    connection: HubConnection,
    timeout: float = REVOKE_SOCKET_CLOSE_TIMEOUT_SECONDS,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            connection.read_event(max(0.05, deadline - time.monotonic()))
        except socket.timeout:
            continue
        except (WebSocketClosed, OSError):
            return
    raise HubError("revoke_active_socket_not_closed")


def _require_post_revoke_authentication_rejected(
    policy: TransportPolicy, stale_session: str, protocol_id: str
) -> None:
    connection: HubConnection | None = None
    try:
        connection = HubConnection(policy, stale_session, protocol_id)
    except AuthenticationRejected:
        return
    except BaseException as error:
        raise HubError("post_revoke_reconnect_rejection_unproven") from error
    finally:
        if connection is not None:
            connection.close()
    raise HubError("post_revoke_reconnect_accepted")


def revoke(
    path: Path, credential_store: CredentialStore | None = None
) -> dict[str, Any]:
    store = credential_store or default_credential_store()
    document, policy, session = load_session(path, store)
    protocol_id = str(document["security_binding"]["protocol"])
    active_connection = HubConnection(policy, session, protocol_id)
    try:
        request = {
            "$schema": REVOKE_REQUEST_SCHEMA,
            "session": session,
            "reason": "user_request",
        }
        validate_protocol_message(request, "revoke_request")
        code, payload = http_json(policy, "POST", "/v1/revoke", request)
        if payload.get("$schema") != REVOKE_RECEIPT_SCHEMA:
            raise HubError(f"revoke_rejected:{code}")
        validate_protocol_message(payload, "revoke_receipt")
        if code != 200:
            raise HubError(f"revoke_rejected:{code}")
        _validate_event_base(payload, policy, require_active_epoch=True)
        if "authority_receipt" in payload and not isinstance(
            payload["authority_receipt"], dict
        ):
            raise HubError("revoke_authority_receipt_invalid")
        if payload.get("applied") is not True:
            raise HubError(f"revoke_not_applied:{payload.get('status', 'unknown')}")
        observed = _validated_server_transport(payload, policy)
        _require_server_closed_socket(active_connection)
        _require_post_revoke_authentication_rejected(policy, session, protocol_id)
    finally:
        active_connection.close()
    request["session"] = ""
    session = ""
    store.delete(document["credential"])
    try:
        path.resolve().unlink()
    except OSError as error:
        raise HubError("revoke_applied_but_session_metadata_cleanup_failed") from error
    return {
        "$schema": "rusty.hostess.connection_hub.revoke_receipt.v2",
        "status": "passed",
        "authenticated_socket_open_before_revoke": True,
        "http_revoke_applied": True,
        "authenticated_socket_closed_within_deadline": True,
        "stale_bearer_auth_rejected": True,
        "credentials_deleted_after_negative_proof": True,
        "session_fingerprint_sha256": _document_session_fingerprint(document),
        "session_redacted": True,
        "local_credential_deleted": True,
        "session_metadata_deleted": True,
        "transport": policy.receipt(),
        "server_transport": observed,
        "socket_protocol": protocol_id,
        "rollover_safe": protocol_id == PROTOCOL_ID_V2,
        "server_receipt": payload,
    }


def simulated_e2e() -> dict[str, Any]:
    try:
        from tools.connection_hub_fixture import (
            ConnectionHubFixture,
            diagnostic_surface,
            media_surface,
        )
    except ModuleNotFoundError:
        from connection_hub_fixture import ConnectionHubFixture, diagnostic_surface, media_surface

    with ConnectionHubFixture() as fixture, tempfile.TemporaryDirectory() as directory:
        credential_store = MemoryCredentialStore()
        policy = transport_policy(fixture.origin, "loopback_fixture")
        status_receipt = status(policy)
        session_path = Path(directory) / "session.json"
        pair_receipt = pair(
            policy,
            fixture.pairing_code,
            fixture.controller_identity_sha256,
            session_path,
            credential_store,
        )
        document, _, session = load_session(session_path, credential_store)
        connection = HubConnection(policy, session)
        try:
            first_epoch = connection.transport_epoch
            fixture.add_surface(media_surface())
            media_event = connection.await_type("surface_available")
            media_request_id = "media-request-0000000001"
            _, media_receipt = connection.send_command(
                "media.control", "play", {}, explicit_request_id=media_request_id
            )
            _, replay_receipt = connection.send_command(
                "media.control",
                "play",
                {},
                explicit_request_id=media_request_id,
                preflight=False,
            )
            _, unknown_surface = connection.send_command(
                "missing.surface", "play", {}, preflight=False
            )
            _, unknown_command = connection.send_command(
                "media.control", "delete_everything", {}, preflight=False
            )
            fixture.add_surface(diagnostic_surface())
            diagnostic_event = connection.await_type("surface_available")
            _, diagnostic_receipt = connection.send_command(
                "diagnostics.capture", "snapshot", {"detail": "bounded"}
            )
            _, keepalive_receipt = connection.send_keepalive()
            next_before_restart = connection.next_external_request_sequence
            fixture.remove_surface("media.control")
            removed_event = connection.await_type("surface_removed")
        finally:
            connection.close()
        fixture.restart_authority()
        reconnected = HubConnection(policy, session)
        try:
            second_epoch = reconnected.transport_epoch
            reconnect_resynced_sequence = reconnected.next_external_request_sequence
            captured_command = fixture.accepted_external_request_bytes[0]
            fixture.rollover_authority()
            dispatches_before_rollover_replay = len(fixture.dispatch_log)
            reconnected.socket.send_text_bytes(captured_command)
            rollover_replay_receipt = reconnected.read_event()
            rollover_replay_not_redispatched = (
                len(fixture.dispatch_log) == dispatches_before_rollover_replay
            )
            _, post_reconnect = reconnected.send_command(
                "diagnostics.capture", "snapshot", {"detail": "bounded"}
            )
            revoke_receipt = revoke(session_path, credential_store)
            revoked_close = False
            try:
                reconnected.read_event(2)
            except WebSocketClosed:
                revoked_close = True
        finally:
            reconnected.close()
        reconnect_rejected = False
        try:
            HubConnection(policy, session)
        except HubError:
            reconnect_rejected = True
        checks = {
            "status_safe_and_labelled": status_receipt["hub"].get("listener_enabled") is True,
            "pair_secret_redacted": pair_receipt.get("session_redacted") is True
            and "session" not in pair_receipt.get("server_receipt", {}),
            "bearer_absent_from_websocket_url": bool(fixture.upgrade_paths)
            and set(fixture.upgrade_paths) == {"/v1/socket"},
            "media_surface_appeared": media_event.get("surface", {}).get("surface_id")
            == "media.control",
            "media_command_scoped": media_receipt.get("accepted") is True,
            "media_provider_applied": media_receipt.get("provider_applied") is True,
            "replay_failed_closed": replay_receipt.get("accepted") is False
            and replay_receipt.get("status") == "request_replay",
            "unknown_surface_failed_closed": unknown_surface.get("accepted") is False
            and unknown_surface.get("status") == "unknown_surface",
            "unknown_command_failed_closed": unknown_command.get("accepted") is False
            and unknown_command.get("status") == "unknown_command",
            "second_surface_appeared": diagnostic_event.get("surface", {}).get("surface_id")
            == "diagnostics.capture",
            "second_provider_command_scoped": diagnostic_receipt.get("accepted") is True,
            "keepalive_slid_session": keepalive_receipt.get("accepted") is True
            and keepalive_receipt.get("next_external_request_sequence")
            == next_before_restart,
            "media_surface_removed": removed_event.get("surface_id") == "media.control",
            "logical_session_preserved": fixture.pair_count == 1,
            "transport_epoch_advanced": first_epoch != second_epoch,
            "reconnect_resynced_next_sequence": reconnect_resynced_sequence
            == next_before_restart,
            "restart_preserved_sequence_fence": next_before_restart == 4,
            "rollover_replay_failed_closed": rollover_replay_receipt.get("accepted")
            is False
            and rollover_replay_receipt.get("status")
            == "request_sequence_mismatch"
            and rollover_replay_receipt.get("next_external_request_sequence")
            == next_before_restart,
            "rollover_replay_not_redispatched": rollover_replay_not_redispatched,
            "reconnect_snapshot_preserved_surfaces": set(reconnected.surfaces)
            == {"diagnostics.capture"},
            "post_reconnect_command_accepted": post_reconnect.get("accepted") is True,
            "explicit_revoke_applied": revoke_receipt.get("status") == "passed",
            "revoke_active_socket_closed": revoke_receipt.get(
                "authenticated_socket_closed_within_deadline"
            )
            is True,
            "revoke_stale_bearer_rejected": revoke_receipt.get(
                "stale_bearer_auth_rejected"
            )
            is True,
            "local_credentials_deleted": not session_path.exists()
            and revoke_receipt.get("local_credential_deleted") is True,
            "revoke_terminated_socket": revoked_close,
            "post_revoke_reconnect_rejected": reconnect_rejected,
            "high_rate_data_plane_absent": fixture.high_rate_payload_count == 0,
            "dispatch_never_crossed_provider": fixture.dispatch_log
            == [
                ("media.provider", "media.control", "play"),
                ("diagnostics.provider", "diagnostics.capture", "snapshot"),
                ("diagnostics.provider", "diagnostics.capture", "snapshot"),
            ],
        }
        passed = all(checks.values())
        return {
            "$schema": "rusty.hostess.connection_hub.simulated_e2e_receipt.v2",
            "status": "passed" if passed else "failed",
            "transport": policy.receipt(),
            "session_fingerprint_sha256": _document_session_fingerprint(document),
            "session_bearer_in_receipt": False,
            "pairing_code_in_receipt": False,
            "first_transport_epoch": first_epoch,
            "second_transport_epoch": second_epoch,
            "next_external_request_sequence_after_reconnect": reconnect_resynced_sequence,
            "authority_epoch_after_rollover": fixture.authority_epoch,
            "surface_lifecycle": [
                "snapshot-empty",
                "media-available",
                "diagnostics-available",
                "media-removed",
                "reconnect-diagnostics-preserved",
                "revoked",
            ],
            "checks": checks,
        }


def _add_endpoint_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--origin", required=True, help="Exact Hub HTTP(S) root origin")
    parser.add_argument(
        "--transport-classification",
        required=True,
        choices=TRANSPORT_CLASSES,
        help="Explicit transport posture; unlabelled endpoints are rejected",
    )
    parser.add_argument(
        "--allow-insecure-trusted-lan",
        action="store_true",
        help="Explicitly allow paired plaintext on a private trusted LAN; evidence remains production-ineligible",
    )


def _read_pairing_code(args: argparse.Namespace) -> str:
    if args.pairing_code_stdin:
        value = sys.stdin.readline(8)
    elif args.pairing_code_fd is not None:
        if args.pairing_code_fd < 0 or args.pairing_code_fd in {1, 2}:
            raise ValueError("pairing_code_fd_invalid")
        with os.fdopen(os.dup(args.pairing_code_fd), "r", encoding="utf-8") as stream:
            value = stream.readline(8)
    else:
        try:
            value = getpass.getpass("Pairing code: ")
        except EOFError as error:
            raise HubError("hidden_pairing_code_input_unavailable") from error
    return value.rstrip("\r\n")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="action", required=True)
    status_parser = sub.add_parser("status")
    _add_endpoint_options(status_parser)
    pair_parser = sub.add_parser("pair")
    _add_endpoint_options(pair_parser)
    pairing_input = pair_parser.add_mutually_exclusive_group()
    pairing_input.add_argument(
        "--pairing-code-stdin",
        action="store_true",
        help="Read the one-use code from stdin without placing it in argv",
    )
    pairing_input.add_argument(
        "--pairing-code-fd",
        type=int,
        help="Read the one-use code from an inherited file descriptor",
    )
    pair_parser.add_argument("--controller-identity-sha256", required=True)
    pair_parser.add_argument("--session-file", required=True, type=Path)
    pair_parser.add_argument(
        "--legacy-v1",
        action="store_true",
        help="Bind the session to legacy socket v1; this is not rollover-safe and receives no sliding keepalives",
    )
    for name in ("list-surfaces", "revoke"):
        command = sub.add_parser(name)
        command.add_argument("--session-file", required=True, type=Path)
    watch_parser = sub.add_parser("connect-watch")
    watch_parser.add_argument("--session-file", required=True, type=Path)
    watch_parser.add_argument("--seconds", type=float, default=5.0)
    watch_parser.add_argument("--max-events", type=int, default=128)
    watch_parser.add_argument("--keepalive-interval-seconds", type=float, default=15.0)
    wait_parser = sub.add_parser("wait-surface")
    wait_parser.add_argument("--session-file", required=True, type=Path)
    wait_parser.add_argument("--surface-id", required=True)
    wait_parser.add_argument(
        "--presence", required=True, choices=("present", "absent")
    )
    wait_parser.add_argument("--seconds", type=float, default=20.0)
    wait_parser.add_argument("--max-events", type=int, default=128)
    wait_parser.add_argument("--keepalive-interval-seconds", type=float, default=5.0)
    invoke_parser = sub.add_parser("invoke-surface-command")
    invoke_parser.add_argument("--session-file", required=True, type=Path)
    invoke_parser.add_argument("--surface-id", required=True)
    invoke_parser.add_argument("--command", required=True)
    invoke_parser.add_argument("--args-json", default="{}")
    sub.add_parser("simulate-e2e")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action in {"status", "pair"}:
            policy = transport_policy(
                args.origin,
                args.transport_classification,
                args.allow_insecure_trusted_lan,
            )
            if args.action == "status":
                receipt = status(policy)
            else:
                receipt = pair(
                    policy,
                    _read_pairing_code(args),
                    args.controller_identity_sha256,
                    args.session_file,
                    socket_protocol=(
                        PROTOCOL_ID_V1 if args.legacy_v1 else PROTOCOL_ID_V2
                    ),
                )
        elif args.action == "list-surfaces":
            receipt = list_surfaces(args.session_file)
        elif args.action == "connect-watch":
            receipt = watch(
                args.session_file,
                args.seconds,
                args.max_events,
                keepalive_interval_seconds=args.keepalive_interval_seconds,
            )
        elif args.action == "wait-surface":
            receipt = wait_surface(
                args.session_file,
                args.surface_id,
                args.presence == "present",
                args.seconds,
                keepalive_interval_seconds=args.keepalive_interval_seconds,
                max_events=args.max_events,
            )
        elif args.action == "invoke-surface-command":
            try:
                command_args = json.loads(args.args_json)
            except json.JSONDecodeError as error:
                raise ValueError("args_json_invalid") from error
            receipt = invoke_surface_command(
                args.session_file, args.surface_id, args.command, validate_args(command_args)
            )
        elif args.action == "revoke":
            receipt = revoke(args.session_file)
        else:
            receipt = simulated_e2e()
        print(json.dumps(receipt, indent=2, sort_keys=True))
        operation_status = receipt.get("operation_status", receipt.get("status"))
        return 0 if operation_status == "passed" else 2
    except (HubError, OSError, ValueError, socket.timeout) as error:
        print(
            json.dumps(
                {
                    "$schema": "rusty.hostess.connection_hub.cli_error.v1",
                    "status": "failed",
                    "reason": str(error),
                    "secrets_in_receipt": False,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
