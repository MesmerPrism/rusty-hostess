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
import os
import re
import socket
import ssl
import struct
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
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
PROTOCOL_ID = "rusty.quest.connection_hub.v1"
EVENT_SCHEMAS = {
    "surface_snapshot": "rusty.quest.connection_hub.surface_snapshot.v1",
    "surface_available": "rusty.quest.connection_hub.surface_available.v1",
    "surface_removed": "rusty.quest.connection_hub.surface_removed.v1",
    "surface_state": "rusty.quest.connection_hub.surface_state.v1",
    "command_receipt": "rusty.quest.connection_hub.command_receipt.v1",
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
PACKAGE_NAME = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
MAX_HTTP_BODY = 65536
MAX_SERVER_FRAME = 65536
MAX_COMMAND_BODY = 4096
MAX_SURFACES = 32
MAX_COMMANDS = 32


class HubError(RuntimeError):
    """Fail-closed protocol or operator-input error."""


class WebSocketClosed(HubError):
    def __init__(self, code: int, reason: str) -> None:
        super().__init__(f"websocket_closed:{code}:{reason}")
        self.code = code
        self.reason = reason


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
    if code != 200 or payload.get("$schema") != STATUS_SCHEMA:
        raise HubError(f"status_rejected:{code}")
    allowed = {
        "$schema",
        "listener_enabled",
        "desired_connection_state",
        "transport_epoch",
        "surface_revision",
        "active_session_count",
        "pairing_required",
        "surfaces",
        "transport_classification",
        "confidentiality",
        "production_eligible",
    }
    if set(payload) != allowed:
        raise HubError("status_fields_invalid")
    if not isinstance(payload.get("listener_enabled"), bool):
        raise HubError("status_listener_state_invalid")
    if payload.get("desired_connection_state") not in {"stopped", "running"}:
        raise HubError("status_desired_connection_state_invalid")
    if not isinstance(payload.get("pairing_required"), bool):
        raise HubError("status_pairing_state_invalid")
    active_count = payload.get("active_session_count")
    surface_revision = payload.get("surface_revision")
    if (
        not isinstance(active_count, int)
        or isinstance(active_count, bool)
        or active_count < 0
        or not isinstance(surface_revision, int)
        or isinstance(surface_revision, bool)
        or surface_revision < 0
    ):
        raise HubError("status_revision_or_count_invalid")
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list) or len(surfaces) > MAX_SURFACES:
        raise HubError("status_surfaces_invalid")
    for surface in surfaces:
        validate_surface(surface)
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
) -> dict[str, Any]:
    return {
        "origin": policy.origin,
        "protocol": PROTOCOL_ID,
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


def pair(
    policy: TransportPolicy,
    pairing_code: str,
    controller_identity_sha256: str,
    session_file: Path,
    credential_store: CredentialStore | None = None,
) -> dict[str, Any]:
    if not PAIRING_CODE.fullmatch(pairing_code):
        raise ValueError("pairing_code_must_be_six_digits")
    if not SIGNER_SHA256.fullmatch(controller_identity_sha256):
        raise ValueError("controller_identity_sha256_invalid")
    request = {
        "$schema": PAIR_REQUEST_SCHEMA,
        "pairing_code": pairing_code,
        "controller_identity_sha256": controller_identity_sha256,
    }
    code, payload = http_json(policy, "POST", "/v1/pair", request)
    if code != 200 or payload.get("$schema") != PAIR_RECEIPT_SCHEMA:
        raise HubError(f"pair_rejected:{code}:{payload.get('status', 'unknown')}")
    if set(payload) != {
        "$schema",
        "accepted",
        "status",
        "session",
        "expires_at_utc",
        "transport_epoch",
        "transport_classification",
        "confidentiality",
        "production_eligible",
    }:
        raise HubError("pair_receipt_fields_invalid")
    if payload.get("accepted") is not True:
        raise HubError(f"pair_not_accepted:{payload.get('status', 'unknown')}")
    session = payload.get("session")
    if not isinstance(session, str) or not OPAQUE_SESSION.fullmatch(session):
        raise HubError("pair_session_invalid")
    session_digest = session_fingerprint(session)
    binding = _security_binding(
        policy, payload, session_digest, controller_identity_sha256
    )
    binding_bytes = canonical_json(binding)
    store = credential_store or default_credential_store()
    credential = store.store(session, binding_bytes)
    document = _session_document(payload, binding, credential)
    try:
        _atomic_write_json(session_file, document, create=True)
    except BaseException:
        store.delete(credential)
        raise
    redacted = {key: value for key, value in payload.items() if key != "session"}
    return {
        "$schema": "rusty.hostess.connection_hub.pair_receipt.v1",
        "status": "passed",
        "session_redacted": True,
        "session_fingerprint_sha256": session_digest,
        "session_file": str(session_file.resolve()),
        "transport": policy.receipt(),
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
    if binding.get("protocol") != PROTOCOL_ID:
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
    commands = descriptor.get("commands")
    if not isinstance(commands, list) or len(commands) > MAX_COMMANDS:
        raise HubError("surface_commands_invalid")
    seen: set[str] = set()
    for item in commands:
        if not isinstance(item, dict) or set(item) != {"command", "display_label"}:
            raise HubError("surface_command_descriptor_invalid")
        command = item["command"]
        label = item["display_label"]
        if not isinstance(command, str) or not TOKEN.fullmatch(command) or command in seen:
            raise HubError("surface_command_invalid")
        if not isinstance(label, str) or len(label) > 96:
            raise HubError("surface_command_label_invalid")
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

    @classmethod
    def connect(cls, policy: TransportPolicy, session: str) -> "WebSocketClient":
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
        result.send_json(
            {
                "$schema": AUTHENTICATE_SCHEMA,
                "type": "authenticate",
                "session": session,
            }
        )
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
        value = bytearray()
        while len(value) < length:
            chunk = self.sock.recv(length - len(value))
            if not chunk:
                raise WebSocketClosed(1006, "eof")
            value.extend(chunk)
        return bytes(value)

    def send_json(self, value: dict[str, Any]) -> None:
        payload = canonical_json(value)
        if len(payload) > MAX_COMMAND_BODY:
            raise ValueError("websocket_command_too_large")
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
    def __init__(self, policy: TransportPolicy, session: str) -> None:
        self.socket = WebSocketClient.connect(policy, session)
        self.transport_epoch: Any = None
        self.surface_revision: Any = None
        self.surfaces: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.authentication_receipt = self.socket.read_json()
        expected_auth_fields = {
            "$schema",
            "type",
            "accepted",
            "status",
            "transport_epoch",
            "confidentiality",
            "production_eligible",
        }
        if (
            set(self.authentication_receipt) != expected_auth_fields
            or self.authentication_receipt.get("$schema")
            != AUTHENTICATION_RECEIPT_SCHEMA
            or self.authentication_receipt.get("type") != "authentication_receipt"
            or self.authentication_receipt.get("accepted") is not True
            or self.authentication_receipt.get("status") != "authenticated"
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
        first = self.read_event()
        if first.get("type") != "surface_snapshot":
            self.close()
            raise HubError("first_event_must_be_surface_snapshot")

    def _validate_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type not in EVENT_SCHEMAS or event.get("$schema") != EVENT_SCHEMAS[event_type]:
            raise HubError("server_event_schema_mismatch")
        required_fields = {
            "surface_snapshot": {"surfaces"},
            "surface_available": {"surface"},
            "surface_removed": {"surface_id", "reason"},
            "surface_state": {"surface_id", "state_revision", "state"},
            "command_receipt": {
                "request_id",
                "surface_id",
                "command",
                "accepted",
                "status",
            },
        }[event_type]
        common = {"$schema", "type", "transport_epoch", "surface_revision"}
        allowed_fields = common | required_fields
        if event_type == "command_receipt":
            allowed_fields.add("proves_application_effect")
        if not (common | required_fields).issubset(event) or not set(event).issubset(
            allowed_fields
        ):
            raise HubError("server_event_fields_invalid")
        if "proves_application_effect" in event and not isinstance(
            event["proves_application_effect"], bool
        ):
            raise HubError("command_effect_proof_flag_invalid")
        epoch = event.get("transport_epoch")
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
            raise HubError("transport_epoch_invalid")
        if self.transport_epoch is None:
            self.transport_epoch = epoch
        elif epoch != self.transport_epoch:
            raise HubError("transport_epoch_changed_within_socket")
        revision = event.get("surface_revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            raise HubError("surface_revision_invalid")
        if self.surface_revision is not None and revision < self.surface_revision:
            raise HubError("surface_revision_regressed")
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

    def send_command(
        self,
        surface_id: str,
        command: str,
        args: dict[str, Any],
        *,
        explicit_request_id: str | None = None,
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
        request = {
            "$schema": COMMAND_SCHEMA,
            "type": "surface.command",
            "request_id": use_request_id,
            "surface_id": surface_id,
            "command": command,
            "args": args,
        }
        self.socket.send_json(request)
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            event = self.read_event(max(0.05, deadline - time.monotonic()))
            if event.get("type") == "command_receipt" and event.get("request_id") == use_request_id:
                if event.get("surface_id") != surface_id or event.get("command") != command:
                    raise HubError("command_receipt_causality_mismatch")
                if not isinstance(event.get("accepted"), bool):
                    raise HubError("command_receipt_acceptance_invalid")
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
    connection = HubConnection(policy, session)
    changed = document.get("last_transport_epoch") not in {None, connection.transport_epoch}
    document["last_transport_epoch"] = connection.transport_epoch
    document["last_surface_revision"] = connection.surface_revision
    _atomic_write_json(path, document, create=False)
    return document, policy, connection, changed


def list_surfaces(
    path: Path, credential_store: CredentialStore | None = None
) -> dict[str, Any]:
    document, policy, connection, changed = connect_session(path, credential_store)
    try:
        surfaces = [connection.surfaces[key] for key in sorted(connection.surfaces)]
        return {
            "$schema": "rusty.hostess.connection_hub.surface_list_receipt.v1",
            "status": "passed",
            "session_fingerprint_sha256": _document_session_fingerprint(document),
            "transport": policy.receipt(),
            "transport_epoch": connection.transport_epoch,
            "transport_epoch_changed": changed,
            "surface_revision": connection.surface_revision,
            "surfaces": surfaces,
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
        _, receipt = connection.send_command(surface_id, command, args)
        if receipt.get("accepted") is not True:
            raise HubError(f"command_rejected:{receipt.get('status', 'unknown')}")
        return {
            "$schema": "rusty.hostess.connection_hub.command_receipt.v1",
            "status": "passed",
            "session_fingerprint_sha256": _document_session_fingerprint(document),
            "transport": policy.receipt(),
            "transport_epoch": connection.transport_epoch,
            "transport_epoch_changed": changed,
            "server_receipt": receipt,
        }
    finally:
        connection.close()


def watch(
    path: Path,
    seconds: float,
    max_events: int,
    credential_store: CredentialStore | None = None,
) -> dict[str, Any]:
    if seconds < 0.1 or seconds > 300:
        raise ValueError("watch_seconds_out_of_bounds")
    if max_events < 1 or max_events > 512:
        raise ValueError("watch_event_limit_out_of_bounds")
    document, policy, connection, changed = connect_session(path, credential_store)
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline and len(connection.events) < max_events:
            try:
                connection.read_event(min(0.25, max(0.05, deadline - time.monotonic())))
            except socket.timeout:
                continue
        return {
            "$schema": "rusty.hostess.connection_hub.watch_receipt.v1",
            "status": "passed",
            "session_fingerprint_sha256": _document_session_fingerprint(document),
            "transport": policy.receipt(),
            "transport_epoch": connection.transport_epoch,
            "transport_epoch_changed": changed,
            "surface_revision": connection.surface_revision,
            "event_count": len(connection.events),
            "events": connection.events,
        }
    finally:
        connection.close()


def revoke(
    path: Path, credential_store: CredentialStore | None = None
) -> dict[str, Any]:
    store = credential_store or default_credential_store()
    document, policy, session = load_session(path, store)
    request = {
        "$schema": REVOKE_REQUEST_SCHEMA,
        "session": session,
        "reason": "user_request",
    }
    code, payload = http_json(policy, "POST", "/v1/revoke", request)
    if code != 200 or payload.get("$schema") != REVOKE_RECEIPT_SCHEMA:
        raise HubError(f"revoke_rejected:{code}")
    if set(payload) != {
        "$schema",
        "applied",
        "status",
        "transport_epoch",
        "transport_classification",
        "confidentiality",
        "production_eligible",
    }:
        raise HubError("revoke_receipt_fields_invalid")
    if payload.get("applied") is not True:
        raise HubError(f"revoke_not_applied:{payload.get('status', 'unknown')}")
    observed = _validated_server_transport(payload, policy)
    receipt = {
        "$schema": "rusty.hostess.connection_hub.revoke_receipt.v1",
        "status": "passed",
        "session_fingerprint_sha256": _document_session_fingerprint(document),
        "session_redacted": True,
        "local_credential_deleted": True,
        "session_metadata_deleted": True,
        "transport": policy.receipt(),
        "server_transport": observed,
        "server_receipt": payload,
    }
    store.delete(document["credential"])
    try:
        path.resolve().unlink()
    except OSError as error:
        raise HubError("revoke_applied_but_session_metadata_cleanup_failed") from error
    return receipt


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
            fixture.remove_surface("media.control")
            removed_event = connection.await_type("surface_removed")
        finally:
            connection.close()
        reconnected = HubConnection(policy, session)
        try:
            second_epoch = reconnected.transport_epoch
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
            "replay_failed_closed": replay_receipt.get("accepted") is False
            and replay_receipt.get("status") == "request_replay",
            "unknown_surface_failed_closed": unknown_surface.get("accepted") is False
            and unknown_surface.get("status") == "unknown_surface",
            "unknown_command_failed_closed": unknown_command.get("accepted") is False
            and unknown_command.get("status") == "unknown_command",
            "second_surface_appeared": diagnostic_event.get("surface", {}).get("surface_id")
            == "diagnostics.capture",
            "second_provider_command_scoped": diagnostic_receipt.get("accepted") is True,
            "media_surface_removed": removed_event.get("surface_id") == "media.control",
            "logical_session_preserved": fixture.pair_count == 1,
            "transport_epoch_advanced": first_epoch != second_epoch,
            "reconnect_snapshot_preserved_surfaces": set(reconnected.surfaces)
            == {"diagnostics.capture"},
            "post_reconnect_command_accepted": post_reconnect.get("accepted") is True,
            "explicit_revoke_applied": revoke_receipt.get("status") == "passed",
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
            "$schema": "rusty.hostess.connection_hub.simulated_e2e_receipt.v1",
            "status": "passed" if passed else "failed",
            "transport": policy.receipt(),
            "session_fingerprint_sha256": _document_session_fingerprint(document),
            "session_bearer_in_receipt": False,
            "pairing_code_in_receipt": False,
            "first_transport_epoch": first_epoch,
            "second_transport_epoch": second_epoch,
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
    for name in ("list-surfaces", "revoke"):
        command = sub.add_parser(name)
        command.add_argument("--session-file", required=True, type=Path)
    watch_parser = sub.add_parser("connect-watch")
    watch_parser.add_argument("--session-file", required=True, type=Path)
    watch_parser.add_argument("--seconds", type=float, default=5.0)
    watch_parser.add_argument("--max-events", type=int, default=128)
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
                )
        elif args.action == "list-surfaces":
            receipt = list_surfaces(args.session_file)
        elif args.action == "connect-watch":
            receipt = watch(args.session_file, args.seconds, args.max_events)
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
        return 0 if receipt.get("status") == "passed" else 2
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
