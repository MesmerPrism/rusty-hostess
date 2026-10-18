"""Closed shader lifecycle handler; effect ownership stays with its executor.

No ADB, socket, generic command execution, watcher or production device backend.
The same API is used by the CLI's neutral consumer. Unknown effects block all
further mutation; observation may reconcile them without replaying a request.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Protocol
import uuid

from tools.hostessctl.sdk_graphics_batch import NAMES, load_batch

ACTIONS = ("prepare", "transfer", "reload", "observe", "revert")


class EffectNotDispatched(ValueError):
    """Executor refused before its first effect; no uncertain operation exists."""


class Executor(Protocol):
    evidence_scope: str
    def status(self) -> dict: ...
    def upload(self, request_id: str, name: str, data: bytes) -> None: ...
    def hashes(self, names: tuple[str, ...]) -> dict: ...
    def reload(self, request_id: str, batch_digest: str) -> None: ...
    def observe(self) -> dict: ...
    def retirement(self, request_id: str) -> dict: ...


class ShaderIteration:
    def __init__(self, catalog: Path, executor: Executor, *, checkpoint=None, batch_loader=None):
        self.catalog = Path(catalog)
        self.executor = executor
        self.actor = None
        self.batch = None
        self.phase = "idle"
        self.events = []
        self.pending = None
        self.last_frame = None
        self.reload_request = None
        self.reporting_errors = []
        self.checkpoint = checkpoint or (lambda report: None)
        self.batch_loader = batch_loader or (lambda path: load_batch(path, self.catalog))

    def _status(self) -> dict:
        status = self.executor.status()
        if (type(status.get("actor")) is not dict or not status["actor"]
                or status.get("eligible") is not True or
                type(status.get("frame")) is not int or status["frame"] < 0):
            raise ValueError("eligible_actor_and_frame_required")
        if self.actor is not None and status["actor"] != self.actor:
            raise ValueError("actor_or_scene_or_settings_changed")
        if self.last_frame is not None and status["frame"] < self.last_frame:
            raise ValueError("frame_counter_regressed")
        self.last_frame = status["frame"]
        return status

    def _advancement(self):
        first = self._status()
        second = self._status()
        if first["actor"] != second["actor"] or second["frame"] <= first["frame"]:
            raise ValueError("same_actor_advancing_frames_required")
        if "end_frame" in first or "end_frame" in second:
            if (type(first.get("end_frame")) is not int or type(second.get("end_frame")) is not int or
                    first["end_frame"] < 0 or second["end_frame"] <= first["end_frame"]):
                raise ValueError("same_actor_advancing_end_frames_required")
        if self.actor is None:
            self.actor = deepcopy(second["actor"])

    def _hashes(self):
        return self.executor.hashes(NAMES) == {
            name: self.batch["files"][name]["sha256"] for name in NAMES}

    def handle(self, action: str, *, batch: Path | None = None) -> dict:
        if action not in ACTIONS:
            raise ValueError("closed_action_required")
        if action == "observe":
            return self._observe()
        if self.pending is not None:
            raise ValueError("original_unknown_requires_read_only_reconciliation")
        if action in ("prepare", "revert"):
            allowed = ("idle", "observed") if action == "prepare" else ("observed",)
            if self.phase not in allowed or batch is None:
                raise ValueError("observe_current_batch_before_next_preparation")
            prepared = self.batch_loader(Path(batch))
            if action == "revert" and prepared["mode"] != "exact-baseline-revert":
                raise ValueError("exact_baseline_revert_required")
            self._advancement()
            self.batch = prepared
            self.phase = "prepared"
            self.events.append({"action": action, "status": "prepared", "batch": prepared["digest"]})
        elif action == "transfer":
            if self.phase != "prepared":
                raise ValueError("prepared_batch_required")
            self._advancement()
            self._mutate("transfer", self._transfer)
            self.phase = "uploaded"
        elif action == "reload":
            if self.phase != "uploaded":
                raise ValueError("complete_upload_required")
            self._advancement()
            if not self._hashes():
                raise ValueError("complete_remote_hashes_required")
            self._mutate("reload", lambda request: self.executor.reload(request, self.batch["digest"]))
            self.phase = "adoption-pending"
        return self.report()

    def _transfer(self, request):
        for name in NAMES:
            self._status()
            self.executor.upload(request, name, self.batch["files"][name]["bytes"])
        if not self._hashes():
            raise ValueError("complete_remote_hashes_required")

    def _mutate(self, action, effect):
        request = uuid.uuid4().hex
        intent = {"action": action, "request_id": request, "batch": self.batch["digest"],
                  "status": "sent", "actor": deepcopy(self.actor), "pre_frame": self.last_frame}
        if action == "reload":
            self.reload_request = intent
        self.events.append(intent)
        self.pending = intent
        try:
            self._persist("before-dispatch", required=True)  # Durable intent before effects.
        except Exception:
            intent["status"] = "not-dispatched"
            self.pending = None
            if action == "reload":
                self.reload_request = None
            raise
        try:
            effect(request)
            if not self._retired(request):
                raise ValueError("original_executor_operation_not_retired")
        except EffectNotDispatched:
            intent["status"] = "not-dispatched"
            self.pending = None
            self.reload_request = None if action == "reload" else self.reload_request
            self._persist("not-dispatched")
            raise
        except BaseException:
            intent["status"] = "unknown"
            self.phase = "unknown"
            try:
                self._persist("unknown-operation")
            except Exception:
                pass  # Preserve the original operation exception and identity.
            # Preserve the exact request/effect owner; no rollback in finally.
            raise
        intent["status"] = "dispatched"
        self.phase = "uploaded" if action == "transfer" else "adoption-pending"
        self.pending = None
        # Persistence failure cannot turn confirmed retirement into uncertainty.
        self._persist("after-retirement")

    def _persist(self, stage, *, required=False):
        try:
            self.checkpoint(self.report())
        except Exception as error:
            self.reporting_errors.append({"stage": stage, "error_type": type(error).__name__})
            if required:
                raise

    def _retired(self, request):
        result = self.executor.retirement(request)
        return result.get("request_id") == request and result.get("retired") is True

    def _observe(self):
        if self.batch is None:
            raise ValueError("batch_required")
        self._status()
        observation = self.executor.observe()
        if (observation.get("actor") != self.actor or
                type(observation.get("frame")) is not int or
                observation["frame"] < self.last_frame):
            raise ValueError("observation_actor_or_frame_mismatch")
        self.last_frame = observation["frame"]
        hashes_match = self._hashes()
        reload = self.reload_request
        witness = observation.get("witness_sha256", "")
        adopted = bool(hashes_match and reload and
                       observation.get("batch_digest") == self.batch["digest"] and
                       observation.get("request_id") == reload["request_id"] and
                       type(observation.get("effect_frame")) is int and
                       reload["pre_frame"] < observation["effect_frame"] <= observation["frame"] and
                       isinstance(witness, str) and len(witness) == 64 and
                       all(c in "0123456789abcdef" for c in witness) and
                       self._retired(reload["request_id"]))
        # A transfer is reconciled only by the complete original batch readback.
        # A trigger requires the executor's own observed output witness as well.
        if self.pending is not None:
            retired = self._retired(self.pending["request_id"])
            resolved = retired and (hashes_match if self.pending["action"] == "transfer" else adopted)
            if resolved:
                self.pending["status"] = "reconciled-read-only"
                self.phase = "uploaded" if self.pending["action"] == "transfer" else "observed"
                self.pending = None
        elif self.phase == "adoption-pending" and adopted:
            self.phase = "observed"
        self.events.append({"action": "observe", "status": self.phase,
                            "observation": deepcopy(observation), "hashes_match": hashes_match})
        self._persist("observation")  # Include terminal reconciliation/pending-clear.
        return self.report()

    def report(self):
        reporting_errors = self.reporting_errors + getattr(self.executor, "reporting_errors", [])
        return {"schema": "rusty.hostess.sdk_graphics.iteration.v1", "phase": self.phase,
                "status": "pass" if self.phase == "observed" and not reporting_errors else "warn",
                "evidence_scope": self.executor.evidence_scope, "actor": deepcopy(self.actor),
                "events": deepcopy(self.events), "pending": deepcopy(self.pending),
                "reporting_errors": deepcopy(reporting_errors),
                "live_device_acceptance": False, "gpu_completion": False,
                "cleanup": "executor_owned_not_inferred_from_host_state"}
