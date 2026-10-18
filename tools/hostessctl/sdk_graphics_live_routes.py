"""One finite test and optional closed stdin turns on its retained live owner."""
import json
import os
from pathlib import Path
import sys

from tools.hostessctl.sdk_graphics_batch import load_batch
from tools.hostessctl.sdk_graphics_iteration import ShaderIteration
from tools.hostessctl.sdk_graphics_live_contract import load_config, sha_file


def plan_live(args):
    config = load_config(Path(args.config))
    catalog = Path(args.catalog)
    baseline = load_batch(Path(args.baseline_batch), catalog)
    candidate = load_batch(Path(args.candidate_batch), catalog)
    if (sha_file(catalog) != config["catalog_sha256"] or baseline["mode"] != "exact-baseline-revert" or
            candidate["mode"] != "fresh-source" or baseline["digest"] not in config["pixel_predicates"] or
            candidate["digest"] not in config["pixel_predicates"]):
        raise ValueError("exact_baseline_candidate_and_pixel_predicates_required")
    return {"schema": "rusty.hostess.sdk_graphics.live_plan.v1", "status": "host-only-validated",
            "config_sha256": sha_file(args.config), "catalog_sha256": sha_file(catalog),
            "baseline_manifest_sha256": baseline["digest"], "candidate_manifest_sha256": candidate["digest"],
            "sequence": ["prepare-candidate", "transfer", "one-reload", "up-to-three-read-only-observations",
                         "only-after-pixel-adoption-exact-baseline-revert", "transfer", "one-reload",
                         "up-to-three-read-only-observations"],
            "device_admission": False, "execution_grant": False, "device_calls": 0,
            "requirements": ["coordinated exact headset custody", "selected enabled APK already running",
                             "fresh app status/actor/settings reference", "deterministic display predicates"],
            "fallbacks": ["fixed directory", "fixed hashes", "app-owned status", "one stock SDK debug broadcast",
                          "fixed Android display readback", "exact process/boot observations"],
            "exclusions": ["install", "launch", "ports", "daemon lifecycle", "SDK completion callback",
                           "GPU retirement", "stereo or wearer acceptance", "automatic retry or cleanup"]}


class LiveRun:
    """Retained original session; callers keep this object across pending turns.

    No state/PID restoration exists. Original observer exceptions/Popen objects
    remain reachable through this owner and the executor. Every method uses the
    same ShaderIteration, pinned config, actor, request IDs and intent journal.
    """

    def __init__(self, args):
        from tools.hostessctl.sdk_graphics_live import LiveExecutor
        if not args.confirm_live_sdk_debug:
            raise ValueError("explicit_live_sdk_developer_dispatch_required")
        self.args = args
        self.plan = plan_live(args)  # Local admission before device contact.
        self.root = Path(args.evidence_root)
        self.executor = LiveExecutor(args.config, args.catalog, self.root)
        with (self.root/"plan.json").open("x") as stream:
            stream.write(json.dumps(self.plan, indent=2)+"\n")
        self.checkpoint_number = 0
        self.report_number = 0
        self.session = ShaderIteration(Path(args.catalog), self.executor, checkpoint=self._checkpoint)
        self.target = "candidate"
        self.candidate_observed = False
        self.baseline_observed = False
        self.started = False
        self.closed = False
        self.close_reason = None
        self.original_errors = []

    def _checkpoint(self, report):
        number = self.checkpoint_number
        self.checkpoint_number += 1
        with (self.root/f"checkpoint-{number:04}.json").open("x") as stream:
            stream.write(json.dumps(report, indent=2)+"\n")
            if (report.get("pending") or {}).get("status") == "sent":
                stream.flush()
                os.fsync(stream.fileno())  # Required intent before the first effect.

    def report(self):
        report = self.session.report()
        report.update(candidate_pixel_predicate_observed=self.candidate_observed,
                      baseline_pixel_predicate_observed=self.baseline_observed,
                      runtime_backend=self.executor.evidence_scope, sdk_completion_callback=False,
                      continuation={"available": not self.closed, "owner": "retained-LiveRun-object-only",
                                    "actions": ["observe-original", "revert-baseline", "status", "close"],
                                    "process_handles_restorable": False, "close_reason": self.close_reason})
        return report

    def _save_report(self):
        number = self.report_number
        self.report_number += 1
        try:
            with (self.root/f"turn-report-{number:04}.json").open("x") as stream:
                stream.write(json.dumps(self.report(), indent=2)+"\n")
        except OSError as error:
            self.session.reporting_errors.append({"stage": "turn-report", "error_type": type(error).__name__})

    def _open(self):
        if self.closed:
            raise ValueError("original_live_handle_closed")

    def _turn(self, action):
        self._open()
        try:
            return action()
        except BaseException as error:
            self.original_errors.append(error)  # Includes the original retained child exception.
            error.sdk_graphics_live_run = self
            error.sdk_graphics_report = self.report()
            raise
        finally:
            self._save_report()  # Reporting failure never aborts a known turn.

    def _observe(self):
        report = self.session.handle("observe")
        if report["phase"] == "observed":
            if self.target == "candidate":
                self.candidate_observed = True
            else:
                self.baseline_observed = True
        return self.report()

    def observe_original(self):
        """One read-only observation/reconciliation, never an upload or trigger."""
        self._turn(self._observe)
        return self.report()

    def _cycle(self, action, batch):
        self.session.handle(action, batch=Path(batch))
        expected = self.plan["baseline_manifest_sha256" if action == "revert" else "candidate_manifest_sha256"]
        if self.session.batch["digest"] != expected:
            raise ValueError("original_planned_batch_changed_before_transfer")
        self.target = "baseline" if action == "revert" else "candidate"
        self.session.handle("transfer")
        self.session.handle("reload")
        for _ in range(3):
            self._observe()
            if self.session.phase == "observed":
                break

    def revert_baseline(self):
        """Explicit compensation after actual candidate adoption; no replay."""
        if not self.candidate_observed or self.target != "candidate" or self.session.phase != "observed":
            raise ValueError("original_candidate_adoption_required")
        self._turn(lambda: self._cycle("revert", self.args.baseline_batch))
        return self.report()

    def run_initial(self):
        if self.started:
            raise ValueError("initial_live_sequence_no_replay")
        self.started = True
        def initial():
            self._cycle("prepare", self.args.candidate_batch)
            if self.candidate_observed:
                self._cycle("revert", self.args.baseline_batch)
        self._turn(initial)
        return self.report()

    def close(self, reason="caller-closed"):
        # Observation ownership ends; no process kill or device cleanup occurs.
        if self.closed:
            return self.report()
        self.closed, self.close_reason = True, reason
        self._save_report()
        try:
            with (self.root/"terminal-report.json").open("x") as stream:
                stream.write(json.dumps(self.report(), indent=2)+"\n")
        except OSError as error:
            self.session.reporting_errors.append({"stage": "terminal-report", "error_type": type(error).__name__})
        return self.report()


def run_live(args, *, input_stream=None, output_stream=None):
    owner = LiveRun(args)
    retained = getattr(args, "retain_original_stdin", False)
    if not retained:
        failure = None
        try:
            owner.run_initial()
        except BaseException as error:
            failure = error
            raise
        finally:
            owner.close("finite-route-returned-no-live-handle")
            if failure is not None:
                failure.sdk_graphics_report = owner.report()
        return owner.report()
    source, sink = input_stream or sys.stdin, output_stream or sys.stdout
    def emit(error=None):
        report = owner.report()
        if error is not None:
            report["continuation_error"] = type(error).__name__
        sink.write(json.dumps(report)+"\n")
        sink.flush()
    try:
        try:
            owner.run_initial()
        except Exception as error:
            emit(error)  # The same owner remains available for read-only reconciliation.
        else:
            emit()
        while not owner.baseline_observed:
            line = source.readline(4097)
            if not line:
                break
            try:
                command = json.loads(line)
                if len(line) > 4096 or type(command) is not dict or set(command) != {"action"}:
                    raise ValueError("closed_continuation_action_required")
                action = command["action"]
                if action == "close":
                    break
                if action == "observe-original":
                    owner.observe_original()
                elif action == "revert-baseline":
                    owner.revert_baseline()
                elif action != "status":
                    raise ValueError("closed_continuation_action_required")
                emit()
            except Exception as error:
                emit(error)
    finally:
        owner.close("stdin-continuation-ended-no-live-handle")
    return owner.report()
