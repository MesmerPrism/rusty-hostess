from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.meta_quest_casting import (
    COMPATIBILITY_PROFILES,
    PrivateStateStore,
    _default_state_path,
    _sha256_json,
    _launch_arguments,
    parse_adb_devices,
    run_meta_quest_casting,
    validate_meta_quest_casting_receipt_semantics,
    validate_serial,
)


TEST_SERIAL = "TESTSERIAL001"
TEST_SESSION_ID = "11111111-1111-4111-8111-111111111111"
TEST_LEASE_ID = "22222222-2222-4222-8222-222222222222"
TEST_CASTING_PATH = r"C:\Program Files\Meta Quest Developer Hub\resources\bin\Casting\Casting.exe"
TEST_ADB_PATH = r"C:\Program Files\Meta Quest Developer Hub\resources\bin\adb.exe"
TEST_CACHE_DIR = r"C:\Users\Test\AppData\Roaming\odh\casting"


def closed_arguments(session_id: str = TEST_SESSION_ID) -> list[str]:
    profile = COMPATIBILITY_PROFILES["6.4.1"]
    return _launch_arguments(
        {
            "adb_exe": TEST_ADB_PATH,
            "cache_dir": TEST_CACHE_DIR,
        },
        serial=TEST_SERIAL,
        session_id=session_id,
        features=list(profile["features"]),
    )


def closed_command_line(session_id: str = TEST_SESSION_ID) -> str:
    return subprocess.list2cmdline(
        [TEST_CASTING_PATH, *closed_arguments(session_id)]
    )


def private_state(
    root: Path,
    *,
    pid: int,
    creation_time_utc: str,
    phase: str = "active",
    coordination_mode: str = "user-supervised",
) -> dict[str, object]:
    profile = COMPATIBILITY_PROFILES["6.4.1"]
    log_root = root / TEST_SESSION_ID
    arguments = closed_arguments()
    return {
        "$schema": "rusty.hostess.meta_quest_casting.private_state.v1",
        "session_id": TEST_SESSION_ID,
        "phase": phase,
        "serial": TEST_SERIAL,
        "coordination_mode": coordination_mode,
        "quest_lease_id": (
            TEST_LEASE_ID if coordination_mode == "agent-board" else ""
        ),
        "casting_exe": TEST_CASTING_PATH,
        "adb_exe": TEST_ADB_PATH,
        "cache_dir": TEST_CACHE_DIR,
        "casting_sha256": profile["casting_sha256"],
        "profile_id": profile["profile_id"],
        "feature_profile_sha256": _sha256_json(list(profile["features"])),
        "features": list(profile["features"]),
        "launch_arguments_sha256": _sha256_json(arguments),
        "pid": pid,
        "process_creation_time_utc": creation_time_utc,
        "stdout_log": str(log_root / "casting.stdout.log"),
        "stderr_log": str(log_root / "casting.stderr.log"),
        "updated_at_utc": "2026-07-30T20:00:01Z",
    }


class FakeAdapter:
    def __init__(self) -> None:
        profile = COMPATIBILITY_PROFILES["6.4.1"]
        self.installation = {
            "root": r"C:\Program Files\Meta Quest Developer Hub",
            "mqdh_exe": (
                r"C:\Program Files\Meta Quest Developer Hub"
                r"\Meta Quest Developer Hub.exe"
            ),
            "casting_exe": TEST_CASTING_PATH,
            "adb_exe": (
                r"C:\Program Files\Meta Quest Developer Hub\resources\bin\adb.exe"
            ),
            "cache_dir": r"C:\Users\Test\AppData\Roaming\odh\casting",
            "files_present": True,
            "canonical_install_root": True,
            "install_path_has_reparse_component": False,
            "casting_is_reparse_point": False,
            "adb_is_reparse_point": False,
            "adb_dependency_is_reparse_point": False,
            "mqdh_version": "6.4.1",
            "mqdh_sha256": profile["mqdh_sha256"],
            "mqdh_signature_status": "Valid",
            "mqdh_signer_subject": 'CN="Meta Platforms, Inc."',
            "mqdh_signer_thumbprint": profile["mqdh_signer_thumbprint"],
            "casting_sha256": profile["casting_sha256"],
            "signature_status": "Valid",
            "signer_subject": 'CN="Meta Platforms, Inc."',
            "signer_thumbprint": profile["signer_thumbprint"],
            "adb_sha256": profile["adb_sha256"],
            "adb_api_sha256": profile["adb_api_sha256"],
            "adb_usb_api_sha256": profile["adb_usb_api_sha256"],
            "adb_signature_status": "Valid",
            "adb_api_signature_status": "Valid",
            "adb_usb_api_signature_status": "Valid",
            "adb_signer_subject": "CN=Google LLC",
            "adb_signer_thumbprint": profile["adb_signer_thumbprint"],
            "adb_api_signer_thumbprint": profile["adb_signer_thumbprint"],
            "adb_usb_api_signer_thumbprint": profile["adb_signer_thumbprint"],
        }
        self.server_running = True
        self.processes: dict[int, dict[str, object]] = {}
        self.external_processes: list[dict[str, object]] = []
        self.launched_arguments: list[str] | None = None
        self.launch_state_path: Path | None = None
        self.closed_pids: list[int] = []
        self.close_identity_matches = True

    def discover_installation(self) -> dict[str, object]:
        return dict(self.installation)

    def adb_server_running(self) -> bool:
        return self.server_running

    def run_adb(
        self,
        _adb_exe: str,
        arguments: list[str],
        *,
        timeout_seconds: float = 15.0,
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        if arguments == ["devices", "-l"]:
            output = (
                "List of devices attached\n"
                f"{TEST_SERIAL} device product:panther model:Quest_3S "
                "device:panther transport_id:1\n"
            )
            return subprocess.CompletedProcess(arguments, 0, output, "")
        if arguments[-3:] == ["dumpsys", "package", "com.oculus.magicislandcastingservice"]:
            output = (
                "Package [com.oculus.magicislandcastingservice]\n"
                "  versionCode=839205053 minSdk=32 targetSdk=34\n"
                "  versionName=2.0.0.0.7440\n"
            )
            return subprocess.CompletedProcess(arguments, 0, output, "")
        raise AssertionError(f"Unexpected ADB invocation: {arguments!r}")

    def list_casting_processes(self) -> list[dict[str, object]]:
        return [
            *[dict(process) for process in self.external_processes],
            *[dict(process) for process in self.processes.values()],
        ]

    def inspect_process(self, pid: int) -> dict[str, object] | None:
        process = self.processes.get(pid)
        return dict(process) if process is not None else None

    def launch_casting(
        self,
        executable: str,
        arguments: list[str],
        *,
        working_directory: str,
        stdout_path: str,
        stderr_path: str,
    ) -> int:
        self.launched_arguments = list(arguments)
        self.launched_executable = executable
        self.launched_working_directory = working_directory
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        if self.launch_state_path is not None:
            persisted = json.loads(self.launch_state_path.read_text(encoding="utf-8"))
            if persisted["phase"] != "starting" or persisted["pid"] != 0:
                raise AssertionError("write-ahead starting state was not persisted")
        pid = 4242
        self.processes[pid] = {
            "pid": pid,
            "executable_path": TEST_CASTING_PATH,
            "creation_time_utc": "2026-07-30T20:00:00Z",
            "main_window_handle": 1001,
            "main_window_title": "Meta Quest Casting",
            "command_line": (
                subprocess.list2cmdline([executable, *arguments])
            ),
        }
        return dict(self.processes[pid])

    def close_main_window_if_matches(
        self,
        pid: int,
        *,
        executable_path: str,
        creation_time_utc: str,
    ) -> dict[str, bool]:
        process = self.processes.get(pid)
        identity_matches = bool(
            self.close_identity_matches
            and process
            and process["executable_path"] == executable_path
            and process["creation_time_utc"] == creation_time_utc
        )
        if not identity_matches:
            return {
                "identity_matched": False,
                "close_requested": False,
            }
        self.closed_pids.append(pid)
        self.processes.pop(pid, None)
        return {
            "identity_matched": True,
            "close_requested": True,
        }


def command_args(command: str, out: Path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "command": "meta-quest-casting",
        "meta_quest_casting_command": command,
        "out": str(out),
    }
    if command in {"doctor", "start"}:
        values["serial"] = TEST_SERIAL
    if command == "start":
        values.update(
            {
                "transport": "usb",
                "coordination_mode": "agent-board",
                "quest_lease_id": "00000000-0000-0000-0000-000000000001",
                "startup_wait_seconds": 0.0,
            }
        )
    if command == "stop":
        values["shutdown_wait_seconds"] = 0.1
    values.update(overrides)
    return argparse.Namespace(**values)


class MetaQuestCastingTests(unittest.TestCase):
    def test_descriptor_is_target_free_inert_and_metadata_only(self) -> None:
        adapter = FakeAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            descriptor_path = Path(temporary) / "descriptor.json"
            result = run_meta_quest_casting(
                command_args("describe", descriptor_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        self.assertEqual(0, result)
        self.assertFalse(descriptor["authorizes_execution"])
        self.assertEqual(
            ["describe", "doctor", "start", "status", "stop"],
            [action["id"] for action in descriptor["actions"]],
        )
        encoded = json.dumps(descriptor).casefold()
        for forbidden in (
            "c:\\",
            "serial",
            "endpoint",
            "credential",
            "--target-device",
            "healthy",
            "ready",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, encoded)

    def test_descriptor_does_not_require_private_state_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            descriptor_path = Path(temporary) / "descriptor.json"
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": ""}):
                result = run_meta_quest_casting(
                    command_args("describe", descriptor_path)
                )
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        self.assertEqual(0, result)
        self.assertFalse(descriptor["authorizes_execution"])

    def test_default_private_state_path_is_product_channel_isolated(self) -> None:
        local_app_data = r"C:\Users\Test\AppData\Local"
        with mock.patch.dict(
            os.environ,
            {"LOCALAPPDATA": local_app_data},
            clear=True,
        ):
            self.assertEqual(
                Path(local_app_data)
                / "Rusty Hostess"
                / "meta-quest-casting"
                / "state.json",
                _default_state_path(),
            )
        with mock.patch.dict(
            os.environ,
            {
                "LOCALAPPDATA": local_app_data,
                "RUSTY_HOSTESS_PRODUCT_CHANNEL": "labs",
            },
            clear=True,
        ):
            self.assertEqual(
                Path(local_app_data)
                / "RustyHostessLabs"
                / "meta-quest-casting"
                / "state.json",
                _default_state_path(),
            )
        with mock.patch.dict(
            os.environ,
            {
                "LOCALAPPDATA": local_app_data,
                "RUSTY_HOSTESS_PRODUCT_CHANNEL": "Labs",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "exactly stable or labs"):
                _default_state_path()

    def test_serial_validation_is_exact_and_closed(self) -> None:
        validate_serial(TEST_SERIAL)
        for value in ("", "*", "any", "first", " serial", "serial ", "a/b", "a\nb"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_serial(value)

    def test_parse_adb_devices_preserves_exact_identity_and_state(self) -> None:
        devices = parse_adb_devices(
            "List of devices attached\n"
            "ONE device product:panther model:Quest_3S transport_id:1\n"
            "TWO unauthorized transport_id:2\n"
        )
        self.assertEqual("ONE", devices[0]["serial"])
        self.assertEqual("device", devices[0]["state"])
        self.assertEqual("Quest_3S", devices[0]["model"])
        self.assertEqual("unauthorized", devices[1]["state"])

    def test_doctor_passes_only_closed_compatible_profile(self) -> None:
        adapter = FakeAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "doctor.json"
            result = run_meta_quest_casting(
                command_args("doctor", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(0, result)
        self.assertEqual("pass", receipt["outcome"])
        self.assertTrue(receipt["compatibility"]["supported"])
        self.assertEqual(TEST_SERIAL, receipt["device"]["serial"])
        self.assertFalse(receipt["transport"]["frame_access"])
        self.assertFalse(receipt["transport"]["hostess_media_route"])
        self.assertIsNone(receipt["presentation"])
        self.assertIsNone(receipt["recording"])

    def test_doctor_does_not_invoke_adb_when_server_is_down(self) -> None:
        class NoAdbAdapter(FakeAdapter):
            def run_adb(self, *args: object, **kwargs: object) -> None:
                raise AssertionError("ADB must not be invoked while the daemon is down")

        adapter = NoAdbAdapter()
        adapter.server_running = False
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "doctor.json"
            result = run_meta_quest_casting(
                command_args("doctor", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual("adb_server_not_running", receipt["reason_code"])

    def test_unknown_hash_fails_closed(self) -> None:
        adapter = FakeAdapter()
        adapter.installation["casting_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "doctor.json"
            result = run_meta_quest_casting(
                command_args("doctor", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual("unsupported_meta_build", receipt["reason_code"])

    def test_bad_host_compatibility_does_not_execute_adb(self) -> None:
        class NoAdbAdapter(FakeAdapter):
            def run_adb(self, *args: object, **kwargs: object) -> None:
                raise AssertionError("untrusted ADB must not execute")

        adapter = NoAdbAdapter()
        adapter.installation["adb_api_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "doctor.json"
            result = run_meta_quest_casting(
                command_args("doctor", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual("unsupported_meta_build", receipt["reason_code"])

    def test_unknown_companion_build_fails_closed(self) -> None:
        class OldCompanionAdapter(FakeAdapter):
            def run_adb(
                self,
                adb_exe: str,
                arguments: list[str],
                *,
                timeout_seconds: float = 15.0,
            ) -> subprocess.CompletedProcess[str]:
                result = super().run_adb(
                    adb_exe,
                    arguments,
                    timeout_seconds=timeout_seconds,
                )
                if arguments[-3:] == [
                    "dumpsys",
                    "package",
                    "com.oculus.magicislandcastingservice",
                ]:
                    result = subprocess.CompletedProcess(
                        arguments,
                        0,
                        "  versionCode=770486731 minSdk=32 targetSdk=34\n"
                        "  versionName=2.0.0.0.3921\n",
                        "",
                    )
                return result

        adapter = OldCompanionAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "doctor.json"
            result = run_meta_quest_casting(
                command_args("doctor", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual(
            "unsupported_meta_companion_build",
            receipt["reason_code"],
        )

    def test_reparse_point_fails_closed(self) -> None:
        adapter = FakeAdapter()
        adapter.installation["casting_is_reparse_point"] = True
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "doctor.json"
            result = run_meta_quest_casting(
                command_args("doctor", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual(
            "casting_reparse_point_rejected",
            receipt["reason_code"],
        )

    def test_start_persists_write_ahead_state_and_uses_closed_arguments(self) -> None:
        adapter = FakeAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            adapter.launch_state_path = state_path
            receipt_path = Path(temporary) / "start.json"
            result = run_meta_quest_casting(
                command_args("start", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(state_path),
                sleep_func=lambda _seconds: None,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(0, result)
        self.assertEqual("active", state["phase"])
        self.assertEqual("active", receipt["outcome"])
        self.assertTrue(receipt["presentation"]["window_observed"])
        self.assertEqual(
            "unconfirmed", receipt["presentation"]["presentation_ready"]
        )
        self.assertFalse(receipt["recording"]["requested"])
        self.assertEqual("unconfirmed", receipt["recording"]["finalized"])
        self.assertEqual(TEST_CASTING_PATH, adapter.launched_executable)
        self.assertEqual(
            [
                "--adb",
                adapter.installation["adb_exe"],
                "--application-caches-dir",
                adapter.installation["cache_dir"],
                "--exit-on-close",
                "--launch-surface",
                "MQDH",
                "--target-device",
                f'{{"id":"{TEST_SERIAL}"}}',
                "--features",
                "image_stabilization",
                "force_reapply_fov",
                "update_device_fov_via_openxr_api",
                "panel_streaming",
                "system_monitor",
                "--launch-surface-session-uuid",
                state["session_id"],
            ],
            adapter.launched_arguments,
        )
        self.assertNotIn("--args", adapter.launched_arguments)

    def test_startup_failure_does_not_claim_exit_without_owned_identity(self) -> None:
        class MissingAfterLaunchAdapter(FakeAdapter):
            def launch_casting(
                self,
                executable: str,
                arguments: list[str],
                *,
                working_directory: str,
                stdout_path: str,
                stderr_path: str,
            ) -> dict[str, object]:
                identity = super().launch_casting(
                    executable,
                    arguments,
                    working_directory=working_directory,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                )
                self.processes.clear()
                return identity

        adapter = MissingAfterLaunchAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "start.json"
            result = run_meta_quest_casting(
                command_args("start", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
                sleep_func=lambda _seconds: None,
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual(
            "casting_exited_during_startup",
            receipt["reason_code"],
        )
        self.assertFalse(receipt["cleanup"]["identity_confirmed"])
        self.assertFalse(receipt["cleanup"]["host_process_exited"])

    def test_start_rechecks_meta_identity_immediately_before_launch(self) -> None:
        class ChangingAdapter(FakeAdapter):
            def __init__(self) -> None:
                super().__init__()
                self.discovery_count = 0

            def discover_installation(self) -> dict[str, object]:
                self.discovery_count += 1
                observation = super().discover_installation()
                if self.discovery_count > 1:
                    observation["casting_sha256"] = "0" * 64
                return observation

        adapter = ChangingAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "start.json"
            result = run_meta_quest_casting(
                command_args("start", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual(
            "meta_installation_changed_before_launch",
            receipt["reason_code"],
        )
        self.assertIsNone(adapter.launched_arguments)

    def test_start_refuses_while_private_state_lock_is_held(self) -> None:
        adapter = FakeAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            store = PrivateStateStore(state_path)
            held_lock = store.try_acquire_operation_lock()
            self.assertIsNotNone(held_lock)
            try:
                receipt_path = Path(temporary) / "start.json"
                result = run_meta_quest_casting(
                    command_args("start", receipt_path),
                    adapter=adapter,
                    state_store=store,
                )
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            finally:
                store.release_operation_lock(held_lock)
        self.assertEqual(3, result)
        self.assertEqual("operation_in_progress", receipt["reason_code"])
        self.assertIsNone(adapter.launched_arguments)

    def test_start_refuses_to_adopt_external_casting_process(self) -> None:
        adapter = FakeAdapter()
        adapter.external_processes = [
            {
                "pid": 99,
                "executable_path": TEST_CASTING_PATH,
                "creation_time_utc": "2026-07-30T19:00:00Z",
                "main_window_handle": 10,
                "main_window_title": "Meta Quest Casting",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "start.json"
            result = run_meta_quest_casting(
                command_args("start", receipt_path),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual("external_casting_process_present", receipt["reason_code"])
        self.assertIsNone(adapter.launched_arguments)

    def test_status_rejects_pid_reuse(self) -> None:
        adapter = FakeAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            store = PrivateStateStore(state_path)
            store.write(
                private_state(
                    Path(temporary),
                    pid=42,
                    creation_time_utc="2026-07-30T20:00:00Z",
                )
            )
            adapter.processes[42] = {
                "pid": 42,
                "executable_path": TEST_CASTING_PATH,
                "creation_time_utc": "2026-07-30T20:00:02Z",
                "main_window_handle": 1,
                "main_window_title": "Meta Quest Casting",
                "command_line": closed_command_line(),
            }
            receipt_path = Path(temporary) / "status.json"
            result = run_meta_quest_casting(
                command_args("status", receipt_path),
                adapter=adapter,
                state_store=store,
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual("owned_process_missing_or_changed", receipt["reason_code"])

    def test_status_recovers_write_ahead_starting_state_by_session_uuid(self) -> None:
        adapter = FakeAdapter()
        process = {
            "pid": 4242,
            "executable_path": TEST_CASTING_PATH,
            "creation_time_utc": "2026-07-30T20:00:00Z",
            "main_window_handle": 1001,
            "main_window_title": "Meta Quest Casting",
            "command_line": closed_command_line(),
        }
        adapter.processes[4242] = dict(process)
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            store = PrivateStateStore(state_path)
            store.write(
                private_state(
                    Path(temporary),
                    pid=0,
                    creation_time_utc="",
                    phase="starting",
                )
            )
            receipt_path = Path(temporary) / "status.json"
            result = run_meta_quest_casting(
                command_args("status", receipt_path),
                adapter=adapter,
                state_store=store,
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            recovered = store.load()
        self.assertEqual(0, result)
        self.assertEqual("active", receipt["outcome"])
        self.assertEqual(4242, recovered["pid"])
        self.assertEqual(
            process["creation_time_utc"],
            recovered["process_creation_time_utc"],
        )

    def test_private_state_rejects_extra_or_unprofiled_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            store = PrivateStateStore(state_path)
            malformed = private_state(
                Path(temporary),
                pid=4242,
                creation_time_utc="2026-07-30T20:00:00Z",
            )
            malformed["unexpected"] = True
            with self.assertRaises(ValueError):
                store.write(malformed)

    def test_stop_closes_only_exact_owned_process_and_clears_state(self) -> None:
        adapter = FakeAdapter()
        process = {
            "pid": 4242,
            "executable_path": TEST_CASTING_PATH,
            "creation_time_utc": "2026-07-30T20:00:00Z",
            "main_window_handle": 1001,
            "main_window_title": "Meta Quest Casting",
            "command_line": closed_command_line(),
        }
        adapter.processes[4242] = dict(process)
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            store = PrivateStateStore(state_path)
            store.write(
                private_state(
                    Path(temporary),
                    pid=4242,
                    creation_time_utc=str(process["creation_time_utc"]),
                    coordination_mode="agent-board",
                )
            )
            receipt_path = Path(temporary) / "stop.json"
            result = run_meta_quest_casting(
                command_args("stop", receipt_path),
                adapter=adapter,
                state_store=store,
                sleep_func=lambda _seconds: None,
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            state_exists = state_path.exists()
        self.assertEqual(0, result)
        self.assertEqual([4242], adapter.closed_pids)
        self.assertEqual("stopped", receipt["outcome"])
        self.assertFalse(receipt["cleanup"]["forced_termination"])
        self.assertTrue(receipt["cleanup"]["host_process_exited"])
        self.assertEqual("unconfirmed", receipt["cleanup"]["device_session_stopped"])
        self.assertEqual("unconfirmed", receipt["cleanup"]["fov_restored"])
        self.assertFalse(receipt["cleanup"]["cleanup_complete"])
        self.assertFalse(state_exists)

    def test_stop_clears_stale_state_without_claiming_process_exit(self) -> None:
        adapter = FakeAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            store = PrivateStateStore(state_path)
            store.write(
                private_state(
                    Path(temporary),
                    pid=4242,
                    creation_time_utc="2026-07-30T20:00:00Z",
                )
            )
            receipt_path = Path(temporary) / "stop.json"
            result = run_meta_quest_casting(
                command_args("stop", receipt_path),
                adapter=adapter,
                state_store=store,
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            state_exists = state_path.exists()
        self.assertEqual(0, result)
        self.assertEqual([], adapter.closed_pids)
        self.assertEqual("inactive", receipt["outcome"])
        self.assertEqual("stale_state_cleared", receipt["reason_code"])
        self.assertFalse(receipt["cleanup"]["identity_confirmed"])
        self.assertFalse(receipt["cleanup"]["graceful_close_requested"])
        self.assertFalse(receipt["cleanup"]["host_process_exited"])
        self.assertFalse(receipt["cleanup"]["cleanup_complete"])
        self.assertFalse(state_exists)

    def test_stop_sends_no_window_input_if_identity_changes_at_close(self) -> None:
        adapter = FakeAdapter()
        process = {
            "pid": 4242,
            "executable_path": TEST_CASTING_PATH,
            "creation_time_utc": "2026-07-30T20:00:00Z",
            "main_window_handle": 1001,
            "main_window_title": "Meta Quest Casting",
            "command_line": closed_command_line(),
        }
        adapter.processes[4242] = dict(process)
        adapter.close_identity_matches = False
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            store = PrivateStateStore(state_path)
            store.write(
                private_state(
                    Path(temporary),
                    pid=4242,
                    creation_time_utc=str(process["creation_time_utc"]),
                )
            )
            receipt_path = Path(temporary) / "stop.json"
            result = run_meta_quest_casting(
                command_args("stop", receipt_path),
                adapter=adapter,
                state_store=store,
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual([], adapter.closed_pids)
        self.assertEqual(
            "process_identity_changed_before_close",
            receipt["reason_code"],
        )
        self.assertFalse(receipt["cleanup"]["identity_confirmed"])

    def test_stop_observes_once_even_with_zero_second_wait(self) -> None:
        adapter = FakeAdapter()
        process = {
            "pid": 4242,
            "executable_path": TEST_CASTING_PATH,
            "creation_time_utc": "2026-07-30T20:00:00Z",
            "main_window_handle": 1001,
            "main_window_title": "Meta Quest Casting",
            "command_line": closed_command_line(),
        }
        adapter.processes[4242] = dict(process)
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            store = PrivateStateStore(state_path)
            store.write(
                private_state(
                    Path(temporary),
                    pid=4242,
                    creation_time_utc=str(process["creation_time_utc"]),
                )
            )
            receipt_path = Path(temporary) / "stop.json"
            result = run_meta_quest_casting(
                command_args(
                    "stop",
                    receipt_path,
                    shutdown_wait_seconds=0.0,
                ),
                adapter=adapter,
                state_store=store,
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(0, result)
        self.assertEqual("stopped", receipt["outcome"])
        self.assertTrue(receipt["cleanup"]["host_process_exited"])

    def test_receipt_semantics_reject_stronger_synthetic_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "doctor.json"
            result = run_meta_quest_casting(
                command_args("doctor", receipt_path),
                adapter=FakeAdapter(),
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(0, result)
        contradictory_cleanup = dict(receipt)
        contradictory_cleanup["cleanup"] = {
            "identity_confirmed": True,
            "graceful_close_requested": True,
            "host_process_exited": True,
            "forced_termination": False,
            "device_session_stopped": "unconfirmed",
            "fov_restored": "unconfirmed",
            "cleanup_complete": True,
        }
        with self.assertRaises(ValueError):
            validate_meta_quest_casting_receipt_semantics(
                contradictory_cleanup
            )
        unowned_exit = dict(receipt)
        unowned_exit["cleanup"] = {
            "identity_confirmed": False,
            "graceful_close_requested": False,
            "host_process_exited": True,
            "forced_termination": False,
            "device_session_stopped": "unconfirmed",
            "fov_restored": "unconfirmed",
            "cleanup_complete": False,
        }
        with self.assertRaises(ValueError):
            validate_meta_quest_casting_receipt_semantics(unowned_exit)
        contradictory_recording = dict(receipt)
        contradictory_recording["recording"] = {
            "requested": False,
            "active": "observed_inactive",
            "finalized": "observed_finalized",
            "artifact": {
                "path": "recording.mp4",
                "size_bytes": 1,
                "sha256": "A" * 64,
            },
        }
        with self.assertRaises(ValueError):
            validate_meta_quest_casting_receipt_semantics(
                contradictory_recording
            )

    def test_parser_has_no_arbitrary_argument_passthrough(self) -> None:
        parser = build_hostessctl_parser(
            broker_package="broker",
            broker_port=1,
            broker_local_forward_port=2,
            makepad_android_package="makepad",
            makepad_android_xr_activity="xr",
            makepad_provider_package="provider",
            makepad_provider_activity="activity",
        )
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "meta-quest-casting",
                    "start",
                    "--serial",
                    TEST_SERIAL,
                    "--coordination-mode",
                    "user-supervised",
                    "--args",
                    "unexpected",
                    "--out",
                    "receipt.json",
                ]
            )
        for invalid_wait in ("-0.1", "nan", "121"):
            with self.subTest(invalid_wait=invalid_wait), self.assertRaises(
                SystemExit
            ):
                parser.parse_args(
                    [
                        "meta-quest-casting",
                        "start",
                        "--serial",
                        TEST_SERIAL,
                        "--coordination-mode",
                        "user-supervised",
                        "--startup-wait-seconds",
                        invalid_wait,
                        "--out",
                        "receipt.json",
                    ]
                )
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "meta-quest-casting",
                    "start",
                    "--serial",
                    TEST_SERIAL,
                    "--coordination-mode",
                    "agent-board",
                    "--quest-lease-id",
                    "not-a-uuid",
                    "--out",
                    "receipt.json",
                ]
            )

    def test_direct_negative_wait_is_rejected_before_device_observation(self) -> None:
        class NoObservationAdapter(FakeAdapter):
            def discover_installation(self) -> dict[str, object]:
                raise AssertionError("invalid input must fail before observation")

        adapter = NoObservationAdapter()
        with tempfile.TemporaryDirectory() as temporary:
            receipt_path = Path(temporary) / "start.json"
            result = run_meta_quest_casting(
                command_args(
                    "start",
                    receipt_path,
                    startup_wait_seconds=-1.0,
                ),
                adapter=adapter,
                state_store=PrivateStateStore(Path(temporary) / "state.json"),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(3, result)
        self.assertEqual("invalid_wait_seconds", receipt["reason_code"])

    def test_invalid_coordination_input_never_observes_or_launches(self) -> None:
        class NoObservationAdapter(FakeAdapter):
            def discover_installation(self) -> dict[str, object]:
                raise AssertionError(
                    "invalid coordination must fail before observation"
                )

        for overrides, expected_reason in (
            (
                {
                    "coordination_mode": "agent-board",
                    "quest_lease_id": "not-a-uuid",
                },
                "invalid_quest_lease_id",
            ),
            (
                {
                    "coordination_mode": "user-supervised",
                    "quest_lease_id": TEST_LEASE_ID,
                },
                "unexpected_quest_lease_id",
            ),
        ):
            with self.subTest(expected_reason=expected_reason):
                adapter = NoObservationAdapter()
                with tempfile.TemporaryDirectory() as temporary:
                    receipt_path = Path(temporary) / "start.json"
                    result = run_meta_quest_casting(
                        command_args("start", receipt_path, **overrides),
                        adapter=adapter,
                        state_store=PrivateStateStore(
                            Path(temporary) / "state.json"
                        ),
                    )
                    receipt = json.loads(
                        receipt_path.read_text(encoding="utf-8")
                    )
                self.assertEqual(3, result)
                self.assertEqual(expected_reason, receipt["reason_code"])
                self.assertIsNone(adapter.launched_arguments)


if __name__ == "__main__":
    unittest.main()
