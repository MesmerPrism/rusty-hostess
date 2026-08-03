import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

from tools import connection_hub_cli as cli
from tools.connection_hub_fixture import (
    ConnectionHubFixture,
    diagnostic_surface,
    media_surface,
)


class ConnectionHubTransportTests(unittest.TestCase):
    def test_endpoint_requires_explicit_transport_classification(self):
        with self.assertRaisesRegex(ValueError, "transport_classification_required"):
            cli.transport_policy("http://127.0.0.1:10000", None)

    def test_plaintext_trusted_lan_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, "explicit_opt_in"):
            cli.transport_policy(
                "http://192.168.50.10:43210", "trusted_lan_experimental"
            )
        policy = cli.transport_policy(
            "http://192.168.50.10:43210",
            "trusted_lan_experimental",
            allow_insecure_trusted_lan=True,
        )
        self.assertEqual(policy.confidentiality, "none")
        self.assertTrue(policy.production_ineligible)
        self.assertTrue(policy.explicit_insecure_opt_in)

    def test_loopback_adb_and_tls_are_distinct(self):
        loopback = cli.transport_policy(
            "http://127.0.0.1:43210", "loopback_fixture"
        )
        forwarded = cli.transport_policy("http://localhost:43210", "adb_forward")
        tls = cli.transport_policy("https://hub.example.test:443", "tls")
        self.assertNotEqual(loopback.classification, forwarded.classification)
        self.assertTrue(loopback.production_ineligible)
        self.assertTrue(forwarded.production_ineligible)
        self.assertEqual(tls.confidentiality, "tls")
        self.assertFalse(tls.production_ineligible)
        with self.assertRaisesRegex(ValueError, "requires_loopback"):
            cli.transport_policy("http://192.168.1.4:43210", "adb_forward")

    def test_server_transport_metadata_is_mandatory(self):
        policy = cli.transport_policy(
            "http://127.0.0.1:43210", "loopback_fixture"
        )
        with self.assertRaisesRegex(cli.HubError, "classification_missing"):
            cli._validated_server_transport({}, policy)


class ConnectionHubValidationTests(unittest.TestCase):
    def test_checked_in_real_protocol_vectors_match_client_lock(self):
        vector_path = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "connection-hub"
            / "connection-hub-protocol-v1.json"
        )
        raw = vector_path.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "fa00d34511b2ee5576eebdd815e58ae032e37b10c209e41289cfd876c78c9c78",
        )
        document = json.loads(raw)
        self.assertEqual(
            document["$schema"], "rusty.quest.connection_hub.protocol_vectors.v1"
        )
        self.assertEqual(document["owner"], "rusty-quest")
        self.assertEqual(document["protocol_id"], cli.PROTOCOL_ID)
        self.assertEqual(document["routes"]["socket"], "/v1/socket")
        self.assertEqual(document["browser_projection"]["routes"], {
            "pair": "/v1/pair",
            "revoke": "/v1/revoke",
            "socket": "/v1/socket",
        })
        for name, owner_contract in document["messages"].items():
            schema, message_type, required, optional = cli.MESSAGE_CONTRACTS[name]
            self.assertEqual(schema, owner_contract["schema"], name)
            self.assertEqual(message_type, owner_contract.get("type"), name)
            self.assertEqual(required, frozenset(owner_contract["required_fields"]), name)
            self.assertEqual(optional, frozenset(owner_contract["optional_fields"]), name)
            cli.validate_protocol_message(owner_contract["example"], name)
        surface = document["messages"]["surface_available"]["example"]["surface"]
        cli.validate_surface(surface)
        cli.validate_args(document["messages"]["surface_command"]["example"]["args"])

    def test_owner_protocol_examples_reject_missing_unknown_wrong_schema_and_type(self):
        vector_path = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "connection-hub"
            / "connection-hub-protocol-v1.json"
        )
        messages = json.loads(vector_path.read_text(encoding="utf-8"))["messages"]
        for name, owner_contract in messages.items():
            example = owner_contract["example"]
            missing = json.loads(json.dumps(example))
            removable = next(
                field
                for field in owner_contract["required_fields"]
                if field not in {"$schema", "type"}
            )
            missing.pop(removable)
            with self.subTest(message=name, damage="missing"), self.assertRaises(
                cli.HubError
            ):
                cli.validate_protocol_message(missing, name)

            unknown = json.loads(json.dumps(example))
            unknown["unknown_field"] = True
            with self.subTest(message=name, damage="unknown"), self.assertRaises(
                cli.HubError
            ):
                cli.validate_protocol_message(unknown, name)

            wrong_schema = json.loads(json.dumps(example))
            wrong_schema["$schema"] = "rusty.quest.connection_hub.wrong.v1"
            with self.subTest(message=name, damage="wrong_schema"), self.assertRaises(
                cli.HubError
            ):
                cli.validate_protocol_message(wrong_schema, name)

            if "type" in owner_contract:
                wrong_type = json.loads(json.dumps(example))
                wrong_type["type"] = "wrong_type"
                with self.subTest(message=name, damage="wrong_type"), self.assertRaises(
                    cli.HubError
                ):
                    cli.validate_protocol_message(wrong_type, name)

    def test_pairing_code_never_has_an_argv_option(self):
        arguments = [
            "pair",
            "--origin",
            "http://127.0.0.1:43210",
            "--transport-classification",
            "loopback_fixture",
            "--controller-identity-sha256",
            "a" * 64,
            "--session-file",
            "session.json",
            "--pairing-code",
            "123456",
        ]
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.parser().parse_args(arguments)

    def test_pairing_code_stdin_and_fd_inputs_are_not_argv_values(self):
        stdin_args = Namespace(pairing_code_stdin=True, pairing_code_fd=None)
        with mock.patch.object(cli.sys, "stdin", io.StringIO("123456\n")):
            self.assertEqual(cli._read_pairing_code(stdin_args), "123456")
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b"654321\n")
            os.close(write_fd)
            write_fd = -1
            fd_args = Namespace(pairing_code_stdin=False, pairing_code_fd=read_fd)
            self.assertEqual(cli._read_pairing_code(fd_args), "654321")
        finally:
            if write_fd >= 0:
                os.close(write_fd)
            os.close(read_fd)

    def test_command_cli_exit_uses_operation_status_not_provider_status(self):
        receipt = {
            "$schema": "rusty.hostess.connection_hub.command_receipt.v1",
            "operation_status": "passed",
            "status": "provider_declined",
            "authority_accepted": True,
            "provider_applied": False,
        }
        stdout = io.StringIO()
        with mock.patch.object(
            cli, "invoke_surface_command", return_value=receipt
        ), contextlib.redirect_stdout(stdout):
            result = cli.main(
                [
                    "invoke-surface-command",
                    "--session-file",
                    "unused-session.json",
                    "--surface-id",
                    "media.control",
                    "--command",
                    "play",
                ]
            )
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "provider_declined")

    def test_command_args_are_flat_and_bounded(self):
        self.assertEqual(cli.validate_args({"enabled": True, "count": 4}), {"enabled": True, "count": 4})
        with self.assertRaisesRegex(ValueError, "flat_scalars"):
            cli.validate_args({"nested": {"not": "allowed"}})
        with self.assertRaisesRegex(ValueError, "flat_scalars"):
            cli.validate_args({"items": [1]})
        with self.assertRaisesRegex(ValueError, "at_most_16"):
            cli.validate_args({f"key{index}": index for index in range(17)})
        with self.assertRaisesRegex(ValueError, "string_too_long"):
            cli.validate_args({"text": "x" * 257})

    def test_surface_descriptor_registry_is_closed(self):
        surface = media_surface()
        surface.pop("_fixture_provider_id")
        validated = cli.validate_surface(surface)
        self.assertEqual(
            [item["command"] for item in validated["commands"]], ["play", "pause"]
        )
        damaged = dict(surface)
        damaged["commands"] = [{"command_id": "play", "display_label": "Play"}]
        with self.assertRaisesRegex(cli.HubError, "command_descriptor_invalid"):
            cli.validate_surface(damaged)

    def test_tampered_session_file_fails_closed(self):
        with ConnectionHubFixture() as fixture, tempfile.TemporaryDirectory() as directory:
            store = cli.MemoryCredentialStore()
            policy = cli.transport_policy(fixture.origin, "loopback_fixture")
            path = Path(directory) / "session.json"
            cli.pair(
                policy,
                fixture.pairing_code,
                fixture.controller_identity_sha256,
                path,
                store,
            )
            document = json.loads(path.read_text(encoding="utf-8"))
            document["security_binding"]["controller_identity_sha256"] = "b" * 64
            binding = cli.canonical_json(document["security_binding"])
            document["security_binding_sha256"] = hashlib.sha256(binding).hexdigest()
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(cli.HubError, "credential_binding_mismatch"):
                cli.load_session(path, store)

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI only")
    def test_dpapi_current_user_roundtrip_is_bound_and_not_plaintext(self):
        store = cli.WindowsDpapiCredentialStore()
        bearer = "fixture-session-token-000000000001"
        binding = b"exact-origin-protocol-and-posture"
        reference = store.store(bearer, binding)
        self.assertEqual(reference["provider"], "windows_dpapi_current_user")
        self.assertNotIn(bearer, json.dumps(reference))
        self.assertEqual(store.load(reference, binding), bearer)
        with self.assertRaisesRegex(cli.HubError, "dpapi_unprotect_failed"):
            store.load(reference, b"wrong-binding")


class ConnectionHubFixtureTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ConnectionHubFixture()
        self.fixture.__enter__()
        self.directory = tempfile.TemporaryDirectory()
        self.session_path = Path(self.directory.name) / "hub-session.json"
        self.policy = cli.transport_policy(self.fixture.origin, "loopback_fixture")
        self.store = cli.MemoryCredentialStore()

    def tearDown(self):
        self.fixture.__exit__(None, None, None)
        self.directory.cleanup()

    def pair(self):
        return cli.pair(
            self.policy,
            self.fixture.pairing_code,
            self.fixture.controller_identity_sha256,
            self.session_path,
            self.store,
        )

    @unittest.skipUnless(os.name == "nt", "CLI credential persistence uses Windows DPAPI")
    def test_cli_pair_reads_stdin_uses_dpapi_and_revoke_deletes_metadata(self):
        arguments = [
            "pair",
            "--origin",
            self.fixture.origin,
            "--transport-classification",
            "loopback_fixture",
            "--pairing-code-stdin",
            "--controller-identity-sha256",
            self.fixture.controller_identity_sha256,
            "--session-file",
            str(self.session_path),
        ]
        stdout = io.StringIO()
        with mock.patch.object(
            cli.sys, "stdin", io.StringIO(self.fixture.pairing_code + "\n")
        ), contextlib.redirect_stdout(stdout):
            self.assertEqual(cli.main(arguments), 0)
        self.assertNotIn(self.fixture.pairing_code, stdout.getvalue())
        metadata = self.session_path.read_text(encoding="utf-8")
        self.assertIn("windows_dpapi_current_user", metadata)
        self.assertNotIn("fixture-session-token", metadata)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                cli.main(["revoke", "--session-file", str(self.session_path)]), 0
            )
        self.assertFalse(self.session_path.exists())

    def test_status_pair_and_session_file_are_secret_redacted(self):
        observed = cli.status(self.policy)
        self.assertEqual(observed["hub"]["$schema"], cli.STATUS_SCHEMA)
        self.assertEqual(observed["transport"]["classification"], "loopback_fixture")
        paired = self.pair()
        rendered = json.dumps(paired)
        self.assertNotIn(self.fixture.pairing_code, rendered)
        document, _, session = cli.load_session(self.session_path, self.store)
        persisted = self.session_path.read_text(encoding="utf-8")
        self.assertNotIn(session, persisted)
        self.assertNotIn(self.fixture.pairing_code, persisted)
        self.assertNotIn(session, rendered)
        self.assertEqual(
            document["security_binding"]["controller_identity_sha256"],
            self.fixture.controller_identity_sha256,
        )
        self.assertEqual(document["credential"]["provider"], "test_in_memory")

    def test_existing_session_destination_prevents_remote_pair(self):
        self.session_path.write_text("reserved by operator\n", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.pair()
        self.assertEqual(self.fixture.pair_count, 0)
        self.assertFalse(self.fixture.session_active)
        self.assertEqual(
            self.session_path.read_text(encoding="utf-8"), "reserved by operator\n"
        )

    def test_credential_preflight_failure_prevents_remote_pair(self):
        class PreflightFailureStore(cli.MemoryCredentialStore):
            def store(self, bearer, binding):
                raise cli.HubError("injected_preflight_store_failure")

        with self.assertRaisesRegex(cli.HubError, "injected_preflight"):
            cli.pair(
                self.policy,
                self.fixture.pairing_code,
                self.fixture.controller_identity_sha256,
                self.session_path,
                PreflightFailureStore(),
            )
        self.assertEqual(self.fixture.pair_count, 0)
        self.assertFalse(self.fixture.session_active)
        self.assertFalse(self.session_path.exists())

    def test_post_pair_credential_failure_compensates_remote_session(self):
        class SecondStoreFailure(cli.MemoryCredentialStore):
            def __init__(self):
                super().__init__()
                self.store_count = 0

            def store(self, bearer, binding):
                self.store_count += 1
                if self.store_count == 2:
                    raise cli.HubError("injected_session_store_failure")
                return super().store(bearer, binding)

        store = SecondStoreFailure()
        with self.assertRaisesRegex(cli.HubError, "injected_session_store_failure"):
            cli.pair(
                self.policy,
                self.fixture.pairing_code,
                self.fixture.controller_identity_sha256,
                self.session_path,
                store,
            )
        self.assertEqual(self.fixture.pair_count, 1)
        self.assertFalse(self.fixture.session_active)
        self.assertFalse(self.session_path.exists())
        self.assertEqual(store._values, {})

    def test_post_pair_metadata_failure_compensates_and_deletes_credential(self):
        store = cli.MemoryCredentialStore()
        with mock.patch.object(
            cli, "_atomic_write_json", side_effect=OSError("injected metadata failure")
        ), self.assertRaisesRegex(OSError, "injected metadata failure"):
            cli.pair(
                self.policy,
                self.fixture.pairing_code,
                self.fixture.controller_identity_sha256,
                self.session_path,
                store,
            )
        self.assertEqual(self.fixture.pair_count, 1)
        self.assertFalse(self.fixture.session_active)
        self.assertFalse(self.session_path.exists())
        self.assertEqual(store._values, {})

    def test_damaged_accepted_pair_receipt_is_rejected_and_compensated(self):
        original_http_json = cli.http_json

        def damage_pair_receipt(policy, method, path, body=None):
            code, payload = original_http_json(policy, method, path, body)
            if path == "/v1/pair" and code == 200:
                payload = dict(payload)
                payload["unknown_field"] = "must-reject"
            return code, payload

        with mock.patch.object(cli, "http_json", side_effect=damage_pair_receipt):
            with self.assertRaisesRegex(cli.HubError, "pair_receipt_fields_invalid"):
                self.pair()
        self.assertEqual(self.fixture.pair_count, 1)
        self.assertFalse(self.fixture.session_active)
        self.assertFalse(self.session_path.exists())
        self.assertEqual(self.store._values, {})

    def test_list_watch_and_invoke_use_one_logical_session(self):
        self.pair()
        self.fixture.add_surface(media_surface())
        listed = cli.list_surfaces(self.session_path, self.store)
        self.assertEqual(
            [item["surface_id"] for item in listed["surfaces"]], ["media.control"]
        )
        watched = cli.watch(self.session_path, 0.1, 4, self.store)
        self.assertGreaterEqual(watched["event_count"], 1)
        invoked = cli.invoke_surface_command(
            self.session_path, "media.control", "play", {}, self.store
        )
        self.assertTrue(invoked["authority_accepted"])
        self.assertTrue(invoked["provider_applied"])
        self.assertTrue(invoked["request_binding_exact"])
        self.assertEqual(invoked["surface_id"], "media.control")
        self.assertEqual(invoked["command"], "play")
        self.assertTrue(invoked["request_id"])
        self.assertEqual(invoked["status"], "provider_applied")
        self.assertEqual(
            self.fixture.dispatch_log,
            [("media.provider", "media.control", "play")],
        )
        self.assertEqual(self.fixture.pair_count, 1)
        self.assertTrue(listed["transport_epoch_changed"])
        self.assertTrue(watched["transport_epoch_changed"])
        self.assertTrue(invoked["transport_epoch_changed"])

    def test_authority_accepted_provider_not_applied_remains_distinct(self):
        self.pair()
        self.fixture.add_surface(media_surface())
        self.fixture.set_provider_result(
            "media.control", "play", applied=False, status="provider_declined"
        )
        invoked = cli.invoke_surface_command(
            self.session_path, "media.control", "play", {}, self.store
        )
        self.assertEqual(invoked["operation_status"], "passed")
        self.assertTrue(invoked["authority_accepted"])
        self.assertFalse(invoked["provider_applied"])
        self.assertEqual(invoked["status"], "provider_declined")
        self.assertTrue(invoked["request_binding_exact"])
        self.assertEqual(
            self.fixture.dispatch_log,
            [("media.provider", "media.control", "play")],
        )

    def test_local_unknown_command_is_not_dispatched(self):
        self.pair()
        self.fixture.add_surface(media_surface())
        with self.assertRaisesRegex(cli.HubError, "command_not_advertised"):
            cli.invoke_surface_command(
                self.session_path, "media.control", "format_disk", {}, self.store
            )
        self.assertEqual(self.fixture.dispatch_log, [])

    def test_replay_unknown_surface_and_unknown_command_fail_closed_at_server(self):
        self.pair()
        self.fixture.add_surface(media_surface())
        _, _, session = cli.load_session(self.session_path, self.store)
        connection = cli.HubConnection(self.policy, session)
        try:
            use_id = "fixed-request-00000000001"
            _, accepted = connection.send_command(
                "media.control", "play", {}, explicit_request_id=use_id
            )
            _, replay = connection.send_command(
                "media.control",
                "play",
                {},
                explicit_request_id=use_id,
                preflight=False,
            )
            _, missing = connection.send_command(
                "missing.surface", "play", {}, preflight=False
            )
            _, unknown = connection.send_command(
                "media.control", "unknown", {}, preflight=False
            )
        finally:
            connection.close()
        self.assertTrue(accepted["accepted"])
        self.assertEqual(replay["status"], "request_replay")
        self.assertEqual(missing["status"], "unknown_surface")
        self.assertEqual(unknown["status"], "unknown_command")
        self.assertEqual(len(self.fixture.dispatch_log), 1)

    def test_provider_lifecycle_reconnect_epoch_and_revoke(self):
        self.pair()
        _, _, session = cli.load_session(self.session_path, self.store)
        first = cli.HubConnection(self.policy, session)
        first_epoch = first.transport_epoch
        self.fixture.add_surface(media_surface())
        first.await_type("surface_available")
        self.fixture.add_surface(diagnostic_surface())
        first.await_type("surface_available")
        self.fixture.remove_surface("media.control")
        first.await_type("surface_removed")
        first.close()
        second = cli.HubConnection(self.policy, session)
        self.assertNotEqual(first_epoch, second.transport_epoch)
        self.assertEqual(set(second.surfaces), {"diagnostics.capture"})
        receipt = cli.revoke(self.session_path, self.store)
        self.assertEqual(receipt["status"], "passed")
        self.assertTrue(receipt["authenticated_socket_open_before_revoke"])
        self.assertTrue(receipt["http_revoke_applied"])
        self.assertTrue(receipt["authenticated_socket_closed_within_deadline"])
        self.assertTrue(receipt["stale_bearer_auth_rejected"])
        self.assertTrue(receipt["credentials_deleted_after_negative_proof"])
        self.assertNotIn(session, json.dumps(receipt))
        self.assertFalse(self.session_path.exists())
        with self.assertRaises(cli.WebSocketClosed):
            second.read_event(2)
        second.close()
        with self.assertRaisesRegex(cli.HubError, "socket_authentication_rejected"):
            cli.HubConnection(self.policy, session)

    def test_revoke_keeps_credentials_when_socket_close_proof_fails(self):
        self.pair()
        with mock.patch.object(
            cli,
            "_require_server_closed_socket",
            side_effect=cli.HubError("injected_close_proof_failure"),
        ), self.assertRaisesRegex(cli.HubError, "injected_close_proof_failure"):
            cli.revoke(self.session_path, self.store)
        self.assertTrue(self.session_path.exists())
        self.assertNotEqual(self.store._values, {})

    def test_revoke_accepts_live_shaped_auth_phase_close_as_rejection(self):
        self.pair()
        self.fixture.set_silent_auth_rejection(True)
        receipt = cli.revoke(self.session_path, self.store)
        self.assertTrue(receipt["stale_bearer_auth_rejected"])
        self.assertTrue(receipt["credentials_deleted_after_negative_proof"])
        self.assertFalse(self.session_path.exists())
        self.assertEqual(self.store._values, {})

    def test_revoke_keeps_credentials_when_stale_auth_proof_fails(self):
        self.pair()
        with mock.patch.object(
            cli,
            "_require_post_revoke_authentication_rejected",
            side_effect=cli.HubError("injected_stale_auth_proof_failure"),
        ), self.assertRaisesRegex(cli.HubError, "injected_stale_auth_proof_failure"):
            cli.revoke(self.session_path, self.store)
        self.assertTrue(self.session_path.exists())
        self.assertNotEqual(self.store._values, {})

    def test_new_authenticated_transport_replaces_old_socket(self):
        self.pair()
        _, _, session = cli.load_session(self.session_path, self.store)
        first = cli.HubConnection(self.policy, session)
        second = cli.HubConnection(self.policy, session)
        try:
            self.assertGreater(second.transport_epoch, first.transport_epoch)
            with self.assertRaises(cli.WebSocketClosed) as closed:
                first.read_event(2)
            self.assertEqual(closed.exception.code, 4002)
        finally:
            first.close()
            second.close()

    def test_pair_rejects_wrong_controller_identity(self):
        with self.assertRaisesRegex(cli.HubError, "pair_rejected"):
            cli.pair(
                self.policy,
                self.fixture.pairing_code,
                "b" * 64,
                self.session_path,
                self.store,
            )
        self.assertFalse(self.session_path.exists())


class ConnectionHubE2ETests(unittest.TestCase):
    def test_deterministic_simulated_e2e(self):
        receipt = cli.simulated_e2e()
        self.assertEqual(receipt["status"], "passed")
        self.assertTrue(all(receipt["checks"].values()))
        self.assertTrue(receipt["transport"]["production_ineligible"])
        self.assertFalse(receipt["session_bearer_in_receipt"])
        self.assertFalse(receipt["pairing_code_in_receipt"])

    def test_cli_simulation_prints_structured_secret_free_receipt(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(["simulate-e2e"])
        self.assertEqual(code, 0, stderr.getvalue())
        receipt = json.loads(stdout.getvalue())
        self.assertEqual(
            receipt["$schema"],
            "rusty.hostess.connection_hub.simulated_e2e_receipt.v1",
        )
        self.assertNotIn("fixture-session-token", stdout.getvalue())
        self.assertNotIn("246810", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
