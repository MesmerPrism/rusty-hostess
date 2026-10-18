"""Actual live-backend command paths against a real local executable peer."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.hostessctl.process_observation import observe_process
from tools.hostessctl.sdk_graphics_batch import NAMES, digest
from tools.hostessctl.sdk_graphics_iteration import ShaderIteration, EffectNotDispatched
from tools.hostessctl.sdk_graphics_live import LiveExecutor
from tools.hostessctl.sdk_graphics_live_contract import load_config, project_status, sha_file
from tools.hostessctl.sdk_graphics_live_routes import plan_live
from tools.hostessctl.sdk_graphics_pixels import check_pixels
from tools.sdk_graphics_fixture_inputs import create_inputs


def snapshot():
    return {"identity": {"packageName": "example.sdk.consumer", "pid": 41}, "controls": {"revision": 1},
            "topology": {"generation": 1}, "consumerBindings": [], "originalProductStartup": {"phase": "running"},
            "producerHandle": 9, "restoreSrgb": True, "flipRows": False,
            "native": {"generation": 1, "sourceStateGeneration": 1},
            "submissionObserver": {"binding": "bound_exact_context", "instanceGeneration": 1, "sessionGeneration": 1,
                "activityOwnerEpoch": 1, "appAttachmentEpoch": 1,
                "frame": {"focused": True, "eligibleAtRead": True, "acceptedSequence": "1", "endSequence": "1"},
                "graphicsBinding": {"available": True, "backend": "vulkan", "instanceGeneration": 1,
                    "sessionGeneration": 1, "lifetimeRevision": 1, "creationHostNs": 1, "creationResult": 0}}}


def settings():
    return {"schema": "rusty.quest.product_panel.receipt.v1", "status": "current", "owner_token": "a"*32,
            "observation": {"particles": {"submitted_owner_current": True, "submitted_parameters": {"fixture": 1},
                            "submitted_revision": 1, "runtime_epoch": 1, "sdk_epoch": 1, "service_generation": 1}}}


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = create_inputs(self.root/"inputs")
        self.catalog = self.inputs/"catalog/catalog.json"
        self.base = self.inputs/"baseline-batch"
        self.candidate = self.inputs/"candidate-batch"
        self.peer = self.root/"peer"
        self.peer.mkdir()
        def pin(name, data):
            path = self.root/name
            path.write_bytes(data)
            return {"path": str(path), "sha256": sha_file(path)}
        apk = pin("test.apk", b"synthetic-fixture-apk-not-installable")
        provider = self.root/"provider"
        provider.mkdir()
        scripts = {}
        for name in ("Prepare-FreshSdkHotload.py", "Prepare-SdkHotloadCatalog.py", "Qualify-SdkGraphicsApk.py"):
            (provider/name).write_text("synthetic provider peer")
            scripts[name] = sha_file(provider/name)
        predicates = {}
        for folder, rgb in ((self.base, [0, 255, 0]), (self.candidate, [255, 0, 0])):
            predicates[digest((folder/"MANIFEST.json").read_bytes())] = {
                "rect": [0, 0, 8, 8], "rgb": rgb, "tolerance": 0, "minimum_matches": 64}
        self.config = {"schema": "rusty.hostess.sdk_graphics.live_inputs.v1", "serial": "FIXTURE", "canonical_serial": "FIXTURE",
            "boot_id": "00000000-0000-0000-0000-000000000001", "package": "example.sdk.consumer", "pid": 41,
            "uid": 10041, "start_ticks": 1234, "apk": apk,
            "adb": pin("adb.provider", b"synthetic adb peer"), "qfm": pin("qfm.provider", b"synthetic qfm peer"),
            "quest_provider": {"root": str(provider), "scripts": scripts},
            "enabling_receipt": pin("enabled.json", json.dumps({"passed": True, "apk_sha256": apk["sha256"],
                                        "sdk_graphics_hot_reload_selected": True}).encode()),
            "app_status_reference": pin("reference.json", json.dumps(snapshot()).encode()),
            "settings_reference": pin("settings-reference.json", json.dumps(settings()).encode()),
            "settings_provider": {"script": pin("settings.ps1", b"synthetic status-only wrapper"),
                                  "pwsh": pin("pwsh.provider", b"synthetic pwsh peer")},
            "catalog_sha256": sha_file(self.catalog), "pixel_predicates": predicates,
            "operator_authorized_sdk_debug_fallback": True}
        self.config_path = self.root/"live.json"
        self.config_path.write_text(json.dumps(self.config))
        self.state_path = self.peer/"state.json"
        self.state_path.write_text(json.dumps({"apk_sha": apk["sha256"], "catalog_sha": sha_file(self.catalog),
            "boot": self.config["boot_id"], "snapshot": snapshot(), "settings": settings(),
            "frame": 1, "reloads": 0, "candidate": False}))
        self.calls = []

    def observer(self, argv, stdout, stderr, **kwargs):
        self.calls.append(argv)
        script = Path(__file__).with_name("sdk_graphics_live_fixture.py")
        return observe_process([sys.executable, str(script), str(self.peer), json.dumps(argv)], stdout, stderr, **kwargs)

    def session(self):
        executor = LiveExecutor(self.config_path, self.catalog, self.root/"evidence", observer=self.observer)
        return ShaderIteration(self.catalog, executor), executor

    def edit_state(self, **values):
        state = json.loads(self.state_path.read_text())
        state.update(values)
        self.state_path.write_text(json.dumps(state))

    def test_real_process_peer_candidate_and_exact_baseline_observation(self):
        session, executor = self.session()
        for action, batch in (("prepare", self.candidate), ("revert", self.base)):
            session.handle(action, batch=batch)
            session.handle("transfer")
            session.handle("reload")
            report = session.handle("observe")
            self.assertEqual(report["phase"], "observed")
            self.assertFalse(report["gpu_completion"])
            self.assertFalse(report["live_device_acceptance"])
        self.assertEqual(json.loads(self.state_path.read_text())["reloads"], 2)
        for path in executor.root.glob("*/process.json"):
            receipt = json.loads(path.read_text())
            self.assertTrue(receipt["observation_complete"])
            self.assertTrue(receipt["process_reaped"])
        self.assertFalse(any("install" in a or "force-stop" in a for a in self.calls))

    def test_unknown_trigger_reconciles_original_terminal_transport_without_replay(self):
        session, executor = self.session()
        session.handle("prepare", batch=self.candidate)
        session.handle("transfer")
        self.edit_state(unknown_trigger=True)
        with self.assertRaisesRegex(ValueError, "transport_failed"):
            session.handle("reload")
        original = session.pending["request_id"]
        self.assertTrue(executor.retirement(original)["retired"])
        self.assertEqual(session.handle("observe")["phase"], "observed")
        self.assertEqual(json.loads(self.state_path.read_text())["reloads"], 1)

    def test_qfm_unknown_response_matching_bytes_never_proves_its_original_retired(self):
        session, executor = self.session()
        session.handle("prepare", batch=self.candidate)
        self.edit_state(bad_push=NAMES[-1])
        with self.assertRaises(ValueError):
            session.handle("transfer")
        self.assertTrue(session._hashes())
        self.assertFalse(executor.retirement(session.pending["request_id"])["retired"])
        self.assertEqual(session.handle("observe")["phase"], "unknown")
        with self.assertRaises(ValueError):
            session.handle("reload")

    def test_predispatch_pixel_match_keeps_known_upload_without_trigger(self):
        session, executor = self.session()
        session.handle("prepare", batch=self.candidate)
        session.handle("transfer")
        self.edit_state(candidate=True)
        with self.assertRaises(EffectNotDispatched):
            session.handle("reload")
        self.assertEqual(session.phase, "uploaded")
        self.assertIsNone(session.pending)
        self.assertEqual(json.loads(self.state_path.read_text())["reloads"], 0)

    def test_source_only_plan_is_inert_and_pin_drift_refuses(self):
        args = argparse.Namespace(config=self.config_path, catalog=self.catalog, baseline_batch=self.base,
                                  candidate_batch=self.candidate)
        with patch("tools.hostessctl.sdk_graphics_live.observe_process", side_effect=AssertionError):
            self.assertEqual(plan_live(args)["device_calls"], 0)
        out = self.root/"plan.json"
        cli = Path(__file__).parent/"hostessctl/hostessctl.py"
        result = subprocess.run([sys.executable, str(cli), "sdk-graphics", "plan-live", "--config", str(self.config_path),
                  "--catalog", str(self.catalog), "--baseline-batch", str(self.base), "--candidate-batch", str(self.candidate),
                  "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(out.read_text())["device_calls"], 0)
        Path(self.config["qfm"]["path"]).write_bytes(b"drift")
        with self.assertRaises(ValueError):
            plan_live(args)

    def test_original_settings_drift_refuses_before_first_remote_write(self):
        session, executor = self.session()
        session.handle("prepare", batch=self.candidate)
        changed = settings()
        changed["observation"]["particles"]["submitted_parameters"]["fixture"] = 2
        self.edit_state(settings=changed)
        with self.assertRaises(EffectNotDispatched):
            session.handle("transfer")
        self.assertEqual(session.phase, "prepared")
        self.assertIsNone(session.pending)
        self.assertEqual(list((self.peer/"remote").iterdir()), [])

    def test_stalled_end_sequence_rejects_before_transfer(self):
        session, executor = self.session()
        with patch.object(executor, "status", side_effect=[
                {"actor": {"scene": 1}, "eligible": True, "frame": 1, "end_frame": 7},
                {"actor": {"scene": 1}, "eligible": True, "frame": 2, "end_frame": 7}]):
            with self.assertRaisesRegex(ValueError, "advancing_end_frames"):
                session.handle("prepare", batch=self.candidate)
        self.assertEqual(self.calls, [])

    def test_process_journal_error_preserves_known_transport_retirement(self):
        session, executor = self.session()
        original_open = Path.open
        def open_path(path, *args, **kwargs):
            if path.name == "process.json":
                raise OSError("journal write")
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", open_path):
            executor._adb("fixed-directory", ["shell", "mkdir", "-p", executor.remote], request="a"*32)
        self.assertTrue(executor.retirement("a"*32)["retired"])
        self.assertEqual(session.report()["reporting_errors"][0]["stage"], "process-receipt")

    def test_observed_timestamp_is_not_actor_and_pixel_predicate_rejects_broad_or_bad_layout(self):
        first, second = snapshot(), snapshot()
        second["submissionObserver"]["graphicsBinding"]["observedHostNs"] = 99
        self.assertEqual(project_status(first, self.config)["actor"], project_status(second, self.config)["actor"])
        predicate = {"rect": [0, 0, 8, 8], "rgb": [255, 0, 0], "tolerance": 0, "minimum_matches": 64}
        raw = struct.pack("<III", 8, 8, 1)+bytes((255, 0, 0, 255))*64
        self.assertTrue(check_pixels(raw, predicate)["matched"])
        with self.assertRaises(ValueError):
            check_pixels(raw[:-1], predicate)
        predicate["tolerance"] = 255
        with self.assertRaises(ValueError):
            check_pixels(raw, predicate)


if __name__ == "__main__":
    unittest.main()
