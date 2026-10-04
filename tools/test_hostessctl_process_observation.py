"""Real neutral subprocess regressions. Artifacts remain outside source."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools.hostessctl.process_observation import ObservationFailure, observe_process
from tools.observe_process import main as cli_main

FIXTURE = Path(__file__).with_name("process_observation_fixture.py")


class ProcessObservationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="hostess-process-observation-"))
        print("retained fixture artifacts:", self.root)

    def observe(self, mode, **kwargs):
        return observe_process([sys.executable, str(FIXTURE), mode, "--root", str(self.root)],
                               self.root / "stdout", self.root / "stderr", **kwargs)

    def assert_closed(self, receipt):
        self.assertTrue(receipt["exit_known"])
        self.assertTrue(receipt["process_reaped"])
        for stream in receipt["streams"].values():
            self.assertTrue(stream["eof"])
            self.assertTrue(stream["raw_file_closed"])
            descriptor = stream["descriptor"]
            raw = Path(descriptor["path"]).read_bytes()
            self.assertEqual(descriptor["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(descriptor["bytes"], len(raw))

    def test_admission_denies_after_diagnostic_callback_failure(self):
        phases = []
        def progress(event):
            phases.append(event["phase"])
            if event["phase"] == "dispatch_before":
                raise RuntimeError("diagnostic source-bank change")
        def admit():
            self.assertEqual(phases, ["dispatch_before"])
            raise ValueError("caller admission denied")
        with patch("tools.hostessctl.process_observation.subprocess.Popen") as popen:
            with self.assertRaises(ObservationFailure) as caught:
                self.observe("nonzero", progress=progress, admit=admit)
            popen.assert_not_called()
        receipt = caught.exception.receipt
        self.assertFalse(receipt["child_started"])
        self.assertFalse(receipt["exit_known"])
        self.assertFalse(receipt["process_reaped"])
        self.assertFalse(receipt["observation_complete"])
        self.assertFalse((self.root / "ready-nonzero").exists())
        self.assertEqual({row["phase"] for row in receipt["observer_errors"]},
                         {"progress", "admission", "launch_or_observation"})
        types = {row["phase"]: row["type"] for row in receipt["observer_errors"]}
        self.assertEqual(types["admission"], "ValueError")
        self.assertEqual(types["progress"], "RuntimeError")
        for row in receipt["streams"].values():
            self.assertTrue(row["raw_file_closed"])
            self.assertFalse(row["eof"])
            self.assertEqual(row["descriptor"]["bytes"], 0)
            self.assertEqual(row["descriptor"]["sha256"], hashlib.sha256(b"").hexdigest())

    def test_normal_admission_runs_once_before_child(self):
        admitted = []
        def admit():
            self.assertFalse((self.root / "ready-nonzero").exists())
            admitted.append(True)
        receipt = self.observe("nonzero", admit=admit)
        self.assertEqual(admitted, [True])
        self.assert_closed(receipt)
        self.assertTrue(receipt["observation_complete"])
        self.assertEqual(receipt["exit_code"], 7)

    def test_concurrent_volume(self):
        receipt = self.observe("volume")
        self.assert_closed(receipt)
        self.assertTrue(receipt["observation_complete"])
        self.assertEqual([row["observed_bytes"] for row in receipt["streams"].values()], [262144] * 2)

    def test_short_flushed_output_visible_before_release(self):
        live = []
        def progress(event):
            if event["phase"] == "pending" and event["streams"]["stdout"]["retained_bytes"]:
                raw = (self.root / "stdout").read_bytes()
                self.assertIn(b"short live diagnostic", raw)
                self.assertFalse(event["exit_observed"])
                live.append(True)
                (self.root / "RELEASE").touch(exist_ok=True)
        receipt = self.observe("short", progress=progress)
        self.assertTrue(live)
        self.assert_closed(receipt)

    def test_raw_sink_failure_does_not_stop_pipe_drain(self):
        original_open = Path.open
        class FailedSink:
            def __init__(self, file):
                self.file = file
            @property
            def closed(self):
                return self.file.closed
            def write(self, data):
                raise OSError("injected raw sink failure")
            def flush(self):
                return self.file.flush()
            def fileno(self):
                return self.file.fileno()
            def close(self):
                return self.file.close()
        def open_file(path, *args, **kwargs):
            file = original_open(path, *args, **kwargs)
            return FailedSink(file) if path == self.root / "stdout" and args == ("xb",) else file
        with patch.object(Path, "open", open_file):
            with self.assertRaises(ObservationFailure) as caught:
                self.observe("volume")
        receipt = caught.exception.receipt
        self.assert_closed(receipt)
        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual(receipt["streams"]["stdout"]["observed_bytes"], 262144)
        self.assertTrue(any(row["phase"] == "stdout_sink" for row in receipt["observer_errors"]))

    def test_prefix_budget_keeps_draining(self):
        with self.assertRaises(ObservationFailure) as caught:
            self.observe("volume", stdout_budget=17, stderr_budget=19)
        receipt = caught.exception.receipt
        self.assert_closed(receipt)
        self.assertFalse(receipt["observation_complete"])
        self.assertEqual(receipt["streams"]["stdout"]["observed_bytes"], 262144)
        self.assertEqual(receipt["streams"]["stdout"]["descriptor"]["bytes"], 17)

    def test_nonzero_is_complete_observation(self):
        receipt = self.observe("nonzero")
        self.assert_closed(receipt)
        self.assertTrue(receipt["observation_complete"])
        self.assertEqual(receipt["exit_code"], 7)

    def test_parent_exit_does_not_claim_eof(self):
        events = []
        def progress(event):
            events.append(event)
            if event["exit_observed"] and event["phase"] == "pending":
                self.assertFalse(all(row["eof"] for row in event["streams"].values()))
                (self.root / "RELEASE").touch(exist_ok=True)
        receipt = self.observe("parent", progress=progress)
        self.assert_closed(receipt)
        self.assertTrue(any(row["exit_observed"] and row["phase"] == "pending" for row in events))
        self.assertIn(b"actual parent boundary", (self.root / "stdout").read_bytes())

    def test_callback_error_preserves_exit(self):
        def progress(event):
            raise RuntimeError("test observer failure")
        with self.assertRaises(ObservationFailure) as caught:
            self.observe("nonzero", progress=progress)
        self.assert_closed(caught.exception.receipt)
        self.assertEqual(caught.exception.receipt["exit_code"], 7)
        self.assertTrue(any(row["phase"] == "progress" for row in caught.exception.receipt["observer_errors"]))

    def test_cooperative_exit(self):
        def cooperate(process):
            self.assertIsNone(process.poll())
            (self.root / "RELEASE").touch()
        receipt = self.observe("wait", cancelled=lambda: (self.root / "ready-wait").exists(),
                               cooperative_cancel=cooperate)
        self.assert_closed(receipt)
        self.assertTrue(receipt["cooperative_notification_returned"])
        self.assertFalse(receipt["owned_kill_attempted"])
        self.assertEqual(receipt["termination_reason"], "cooperative_cancel_exit")

    def test_distinct_force_owned_object(self):
        latest = {}
        notice = []
        def progress(event):
            latest.update(event)
        def cooperate(process):
            notice.append(process)
        def force(process):
            self.assertIs(notice[0], process)
            return {"action": "force_cancel_exact_owned_host_child", "owned_process": process,
                    "session_id": latest["session_id"], "pid": process.pid,
                    "birth_identity": latest["birth_identity"], "request_id": "second-request"}
        original_force = force
        def joined_force(process):
            return dict(original_force(process), cooperative_notice_id=latest["cooperative_notice_id"])
        receipt = self.observe("wait", progress=progress,
            cancelled=lambda: (self.root / "ready-wait").exists(),
            cooperative_cancel=cooperate, force_requested=joined_force)
        self.assert_closed(receipt)
        self.assertTrue(receipt["owned_kill_attempted"])
        self.assertEqual(receipt["termination_reason"], "explicit_owned_force")

    def test_source_drift_is_diagnostic(self):
        watched = self.root / "watched"
        watched.write_bytes(b"before")
        changed = []
        def progress(event):
            if event["phase"] == "child_started":
                watched.write_bytes(b"after")
                changed.append(True)
        receipt = self.observe("nonzero", source_paths=(watched,), progress=progress)
        self.assertTrue(changed)
        self.assertTrue(receipt["source_changed"])
        self.assert_closed(receipt)

    def test_source_read_error_preserves_known_child_exit(self):
        watched = self.root / "watched"
        watched.write_bytes(b"before")
        def progress(event):
            if event["phase"] == "child_started":
                watched.unlink()
        with self.assertRaises(ObservationFailure) as caught:
            self.observe("nonzero", source_paths=(watched,), progress=progress)
        self.assert_closed(caught.exception.receipt)
        self.assertEqual(caught.exception.receipt["exit_code"], 7)
        self.assertTrue(any(row["phase"] == "source_observation"
                            for row in caught.exception.receipt["observer_errors"]))

    def test_cancel_callback_failure_does_not_force(self):
        def cooperate(process):
            (self.root / "RELEASE").touch()
            raise RuntimeError("notification uncertainty")
        with self.assertRaises(ObservationFailure) as caught:
            self.observe("wait", cancelled=lambda: (self.root / "ready-wait").exists(),
                         cooperative_cancel=cooperate)
        self.assert_closed(caught.exception.receipt)
        self.assertFalse(caught.exception.receipt["cooperative_notification_returned"])
        self.assertFalse(caught.exception.receipt["owned_kill_attempted"])

    def test_each_reader_initialization_failure_settles_unknown(self):
        original_start = threading.Thread.start
        for failed_position in (1, 2):
            with self.subTest(failed_position=failed_position):
                self.root = Path(tempfile.mkdtemp(prefix="hostess-reader-initialization-"))
                calls = []
                def start(thread):
                    calls.append(thread)
                    if len(calls) == failed_position:
                        raise RuntimeError("injected reader initialization failure")
                    return original_start(thread)
                # A small genuinely exiting child avoids an artificial blocked
                # writer; only thread initialization is injected, not exit/EOF.
                with patch.object(threading.Thread, "start", start):
                    with self.assertRaises(ObservationFailure) as caught:
                        self.observe("nonzero")
                receipt = caught.exception.receipt
                self.assertTrue(receipt["exit_known"])
                self.assertTrue(receipt["process_reaped"])
                name = "stdout" if failed_position == 1 else "stderr"
                self.assertEqual(receipt["streams"][name]["initialization"], "failed")
                self.assertFalse(receipt["streams"][name]["eof"])
                self.assertFalse(receipt["observation_complete"])

    def test_wrong_force_object_denied_without_kill(self):
        latest = {}
        calls = []
        def progress(event):
            latest.update(event)
            if calls and event["phase"] == "pending":
                (self.root / "RELEASE").touch(exist_ok=True)
        def force(process):
            calls.append(True)
            return {"action": "force_cancel_exact_owned_host_child", "owned_process": object(),
                    "session_id": latest["session_id"], "pid": process.pid,
                    "birth_identity": latest["birth_identity"], "request_id": "wrong-object"}
        original_force = force
        def joined_force(process):
            return dict(original_force(process), cooperative_notice_id=latest["cooperative_notice_id"])
        with self.assertRaises(ObservationFailure) as caught:
            self.observe("wait", progress=progress,
                cancelled=lambda: (self.root / "ready-wait").exists(),
                cooperative_cancel=lambda process: None, force_requested=joined_force)
        self.assert_closed(caught.exception.receipt)
        self.assertFalse(caught.exception.receipt["owned_kill_attempted"])
        self.assertTrue(any(row["phase"] == "explicit_force" for row in caught.exception.receipt["observer_errors"]))

    def test_real_cli_same_api(self):
        out = self.root / "cli"
        result = cli_main(["--out", str(out), "--", sys.executable, str(FIXTURE),
                           "nonzero", "--root", str(self.root)])
        receipt = json.loads((out / "receipt.json").read_text())
        self.assertEqual(result, 1)
        self.assertEqual(receipt["exit_code"], 7)
        self.assert_closed(receipt)

    def test_real_cli_source_drift_rejects_complete_capture(self):
        watched = self.root / "watched"
        watched.write_bytes(b"initial source")
        out = self.root / "cli"
        result = cli_main(["--out", str(out), "--source", str(watched), "--",
            sys.executable, str(FIXTURE), "source-drift", "--root", str(self.root),
            "--source", str(watched)])
        receipt = json.loads((out / "receipt.json").read_text())
        self.assertEqual(result, 1)
        self.assertEqual(receipt["exit_code"], 0)
        self.assertTrue(receipt["source_changed"])
        self.assertTrue(receipt["observation_complete"])
        self.assert_closed(receipt)

    @unittest.skipUnless(os.environ.get("HOSTESS_OBSERVATION_LONG_TEST") == "1", "opt-in 35s stimulus")
    def test_completion_beyond_old_cutoffs(self):
        receipt = self.observe("delay")
        self.assert_closed(receipt)
        self.assertGreater(receipt["elapsed_ns"], 30_000_000_000)
        self.assertTrue(receipt["observation_complete"])


if __name__ == "__main__":
    unittest.main()
