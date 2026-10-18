"""Neutral consumer and real CLI tests; no SDK compiler, ADB, ports or GPU."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.sdk_graphics_fixture_inputs import create_inputs
from tools.hostessctl import sdk_graphics_batch as batches
from tools.hostessctl import sdk_graphics_routes as routes
from tools.hostessctl.sdk_graphics_fixture import FileConsumer
from tools.hostessctl.sdk_graphics_iteration import ShaderIteration
from tools.hostessctl.companion_catalog import build_companion_catalog_report, validate_companion_catalog_report
from tools.hostessctl.companion_report_projection import build_companion_report_projection, utc_now


class ShaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = create_inputs(self.root / "inputs")
        self.catalog = self.inputs / "catalog/catalog.json"
        self.base = self.inputs / "baseline-batch"
        self.candidate = self.inputs / "candidate-batch"
        self.consumer = FileConsumer(self.root / "consumer")
        self.checkpoints = []
        self.session = ShaderIteration(self.catalog, self.consumer,
                                       checkpoint=lambda report: self.checkpoints.append(deepcopy(report)))

    def activate(self, batch=None, action="prepare"):
        self.session.handle(action, batch=batch or self.candidate)
        self.session.handle("transfer")
        self.session.handle("reload")
        return self.session.handle("observe")

    def edit_manifest(self, function):
        path = self.candidate / "MANIFEST.json"
        obj = json.loads(path.read_text())
        function(obj)
        path.write_text(json.dumps(obj))

    def test_real_child_baseline_candidate_exact_revert(self):
        self.activate(self.base)
        before = self.consumer.observe()["witness_sha256"]
        self.activate()
        self.assertNotEqual(self.consumer.observe()["witness_sha256"], before)
        report = self.activate(self.base, "revert")
        self.assertEqual(self.consumer.observe()["witness_sha256"], before)
        self.assertEqual(report["phase"], "observed")
        self.assertFalse(report["live_device_acceptance"])
        self.assertEqual(self.consumer.reloads, 3)
        for path in self.consumer.root.glob("*/process.json"):
            process = json.loads(path.read_text())
            self.assertTrue(process["observation_complete"])
            self.assertTrue(process["process_reaped"])
            self.assertEqual(process["exit_code"], 0)
        self.assertTrue(any(c["pending"] and c["pending"]["status"] == "sent" for c in self.checkpoints))

    def test_unknown_partial_transfer_blocks_all_fresh_mutations(self):
        self.session.handle("prepare", batch=self.candidate)
        self.consumer.fail_upload = batches.NAMES[1]
        with self.assertRaises(OSError):
            self.session.handle("transfer")
        request = deepcopy(self.session.pending)
        for action in ("prepare", "transfer", "reload", "revert"):
            with self.assertRaisesRegex(ValueError, "original_unknown"):
                self.session.handle(action, batch=self.base)
        self.assertEqual(self.session.handle("observe")["phase"], "unknown")
        self.assertEqual(self.session.pending, request)
        self.assertEqual(self.consumer.reloads, 0)

    def test_intent_persistence_failure_dispatches_no_effect(self):
        self.session.handle("prepare", batch=self.candidate)
        self.session.checkpoint = lambda report: (_ for _ in ()).throw(OSError("journal"))
        with self.assertRaises(OSError):
            self.session.handle("transfer")
        self.assertEqual(list(self.consumer.remote.iterdir()), [])
        self.assertIsNone(self.session.pending)
        self.assertEqual(self.session.phase, "prepared")
        self.assertEqual(self.session.events[-1]["status"], "not-dispatched")
        self.assertEqual(self.session.report()["reporting_errors"][0]["stage"], "before-dispatch")

    def test_retired_effect_survives_terminal_journal_failure_without_replay(self):
        self.session.handle("prepare", batch=self.candidate)
        self.session.handle("transfer")
        def fail_terminal(report):
            if report["pending"] is None:
                raise OSError("terminal journal")
        self.session.checkpoint = fail_terminal
        with self.assertRaises(OSError):
            self.session.handle("reload")
        self.assertEqual(self.consumer.reloads, 1)
        self.assertIsNone(self.session.pending)
        self.assertEqual(self.session.phase, "adoption-pending")
        self.assertEqual(self.session.events[-1]["status"], "dispatched")
        with self.assertRaises(ValueError):
            self.session.handle("reload")
        self.session.checkpoint = lambda report: self.checkpoints.append(deepcopy(report))
        self.assertEqual(self.session.handle("observe")["phase"], "observed")
        self.assertIsNone(self.checkpoints[-1]["pending"])
        self.assertEqual(self.consumer.reloads, 1)
        path = self.root / "degraded.json"
        path.write_text(json.dumps(self.session.report()))
        projected = build_companion_report_projection(argparse.Namespace(sdk_graphics=[str(path)]),
                                                       clock_func=utc_now)
        self.assertEqual(projected["status"], "warn")
        shader = projected["rows"][0]
        self.assertEqual(shader["status"], "warn")
        self.assertEqual(shader["details"]["reporting_errors"][0]["stage"], "after-retirement")

    def test_unknown_complete_transfer_reconciles_without_repush(self):
        self.session.handle("prepare", batch=self.candidate)
        self.consumer.fail_upload = batches.NAMES[-1]
        with self.assertRaises(OSError):
            self.session.handle("transfer")
        self.assertEqual(self.session.handle("observe")["phase"], "uploaded")
        self.session.handle("reload")
        self.assertEqual(self.session.handle("observe")["phase"], "observed")
        self.assertEqual(self.consumer.reloads, 1)

    def test_matching_hashes_cannot_reconcile_a_still_active_original(self):
        self.session.handle("prepare", batch=self.candidate)
        self.consumer.fail_upload = batches.NAMES[-1]
        self.consumer.hold_retirement = True
        with self.assertRaises(OSError):
            self.session.handle("transfer")
        request = self.session.pending["request_id"]
        self.assertTrue(self.session._hashes())
        self.assertEqual(self.session.handle("observe")["phase"], "unknown")
        with self.assertRaises(ValueError):
            self.session.handle("reload")
        self.consumer.operations[request] = True
        self.assertEqual(self.session.handle("observe")["phase"], "uploaded")

    def test_stale_same_batch_witness_cannot_acknowledge_a_new_trigger(self):
        self.activate()
        old = (self.consumer.root / "current.json").read_bytes()
        self.session.handle("prepare", batch=self.candidate)
        self.session.handle("transfer")
        self.consumer.delay_adoption = True
        self.session.handle("reload")
        self.assertEqual((self.consumer.root / "current.json").read_bytes(), old)
        self.assertEqual(self.session.handle("observe")["phase"], "adoption-pending")
        with self.assertRaises(ValueError):
            self.session.handle("revert", batch=self.base)

    def test_new_effect_witness_still_waits_for_original_reload_retirement(self):
        self.session.handle("prepare", batch=self.candidate)
        self.session.handle("transfer")
        self.consumer.hold_retirement = True
        with self.assertRaisesRegex(ValueError, "not_retired"):
            self.session.handle("reload")
        request = self.session.pending["request_id"]
        self.assertEqual(self.session.handle("observe")["phase"], "unknown")
        self.consumer.operations[request] = True
        self.assertEqual(self.session.handle("observe")["phase"], "observed")
        self.assertEqual(self.consumer.reloads, 1)

    def test_unknown_reload_is_observed_never_replayed(self):
        self.session.handle("prepare", batch=self.candidate)
        self.session.handle("transfer")
        self.consumer.unknown_reload = True
        with self.assertRaises(OSError):
            self.session.handle("reload")
        original = self.session.pending["request_id"]
        with self.assertRaises(ValueError):
            self.session.handle("reload")
        report = self.session.handle("observe")
        self.assertEqual(report["phase"], "observed")
        self.assertIsNone(report["pending"])
        self.assertEqual([e for e in report["events"] if e.get("request_id") == original][0]["status"],
                         "reconciled-read-only")
        self.assertEqual(self.consumer.reloads, 1)
        self.assertEqual(self.checkpoints[-1]["phase"], "observed")
        self.assertIsNone(self.checkpoints[-1]["pending"])

    def test_delayed_adoption_does_not_infer_effect_or_allow_revert(self):
        self.consumer.delay_adoption = True
        self.session.handle("prepare", batch=self.candidate)
        self.session.handle("transfer")
        self.session.handle("reload")
        self.assertEqual(self.session.handle("observe")["phase"], "adoption-pending")
        with self.assertRaises(ValueError):
            self.session.handle("revert", batch=self.base)
        with self.assertRaises(ValueError):
            self.session.handle("reload")

    def test_changed_actor_or_stalled_frame_refuses_before_transfer(self):
        self.session.handle("prepare", batch=self.candidate)
        self.consumer.actor["scene"] = "replacement"
        with self.assertRaises(ValueError):
            self.session.handle("transfer")
        self.assertEqual(list(self.consumer.remote.iterdir()), [])
        self.consumer.actor["scene"] = "one-fixture-scene"
        self.consumer.stalled = True
        with self.assertRaises(ValueError):
            self.session.handle("transfer")

    def test_each_profile_variant_abi_and_byte_negative_before_effect(self):
        original = (self.candidate / "MANIFEST.json").read_bytes()
        changes = [lambda m: m["files"].pop(),
                   lambda m: m["files"][0].update(relative="../escape.spv"),
                   lambda m: m["files"][0].update(abiSha256="0" * 64),
                   lambda m: m["compileProfile"].update(optimizationFlag="-g"),
                   lambda m: m["files"][0].update(sha256="0" * 64),
                   lambda m: m.update(mode="exact-baseline-revert")]
        for change in changes:
            with self.subTest(change=change):
                (self.candidate / "MANIFEST.json").write_bytes(original)
                self.edit_manifest(change)
                with self.assertRaises(ValueError):
                    self.session.handle("prepare", batch=self.candidate)
                self.assertEqual(list(self.consumer.remote.iterdir()), [])

    def test_remote_drift_refuses_reload(self):
        self.session.handle("prepare", batch=self.candidate)
        self.session.handle("transfer")
        (self.consumer.remote / batches.NAMES[0]).write_bytes(b"drift")
        with self.assertRaises(ValueError):
            self.session.handle("reload")
        self.assertEqual(self.consumer.reloads, 0)

    def test_closed_actions_and_exact_revert(self):
        with self.assertRaises(ValueError):
            self.session.handle("shell")
        self.activate()
        with self.assertRaisesRegex(ValueError, "exact_baseline"):
            self.session.handle("revert", batch=self.candidate)

    def test_inert_discovery_initializes_no_consumer_or_process(self):
        with patch("tools.hostessctl.sdk_graphics_fixture.FileConsumer", side_effect=AssertionError), \
             patch("tools.hostessctl.sdk_graphics_batch.observe_process", side_effect=AssertionError):
            report = routes.describe()
        self.assertEqual(report["live_backend"], "unavailable-not-qualified")
        self.assertFalse(report["availability_is_execution_grant"])

    def test_wrong_owner_pin_refuses_before_process_dispatch(self):
        owner = self.root / "owner"
        owner.mkdir()
        (owner / "Prepare-FreshSdkHotload.py").write_text("owner script")
        (owner / "Prepare-SdkHotloadCatalog.py").write_text("owner reflector")
        args = argparse.Namespace(owner_app=str(owner), preparer_sha256="0" * 64,
                                  reflector_sha256="0" * 64)
        with patch.object(batches, "observe_process", side_effect=AssertionError):
            with self.assertRaisesRegex(ValueError, "owner_source_pin_changed"):
                batches.prepare(args)

    def test_projection_fails_unsupported_device_claim_or_incoherent_status(self):
        report = self.activate()
        path = self.root / "unsupported.json"
        for mutation in ({"gpu_completion": True}, {"live_device_acceptance": True},
                         {"phase": "unknown"}, {"pending": {"request_id": "held"}}):
            with self.subTest(mutation=mutation):
                path.write_text(json.dumps({**report, **mutation}))
                args = argparse.Namespace(sdk_graphics=[str(path)])
                projected = build_companion_report_projection(args, clock_func=utc_now)
                self.assertEqual(projected["status"], "fail")
                self.assertEqual(projected["rows"][0]["status"], "fail")

    def test_real_cli_and_existing_catalog_consumer(self):
        repo = Path(__file__).resolve().parents[1]
        out = self.root / "report.json"
        command = [sys.executable, str(repo / "tools/hostessctl/hostessctl.py"),
                   "sdk-graphics", "fixture", "--catalog", str(self.catalog),
                   "--baseline-batch", str(self.base), "--candidate-batch", str(self.candidate),
                   "--consumer-root", str(self.root / "cli-consumer"), "--out", str(out)]
        child = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertTrue(json.loads(out.read_text())["baseline_witness_restored"])
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
        args = argparse.Namespace(frontend="cli", gui_descriptors_root=str(repo / "fixtures/sdk-graphics"),
                                  hostess_descriptor=str(repo / "fixtures/sdk-graphics/module-descriptor.json"))
        report = build_companion_catalog_report(args, clock_ms_func=lambda: 1)
        self.assertEqual(validate_companion_catalog_report(report)["status"], "pass")
        self.assertEqual(report["modules"][0]["module_id"], "companion.sdk_graphics.iteration")
        projection = self.root / "projection.json"
        child = subprocess.run([sys.executable, str(repo / "tools/hostessctl/hostessctl.py"),
                                "companion-report", "projection", "--sdk-graphics", str(out),
                                "--out", str(projection), "--fail-on-error"], capture_output=True, text=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        rows = json.loads(projection.read_text())["rows"]
        shader = next(r for r in rows if r["row_id"] == "sdk_graphics.lifecycle")
        self.assertFalse(shader["details"]["live_device_acceptance"])


if __name__ == "__main__":
    unittest.main()
