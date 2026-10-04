"""Completion-driven host process observation; no automatic duration kill.

The caller owns command admission and cancellation policy. This module owns one
retained Popen object, its two pipes, and CreateNew raw files, never a process tree.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid
from typing import Callable

SCHEMA = "rusty.hostess.process_observation.v1"


class ObservationFailure(Exception):
    """Observation is incomplete; receipt preserves known facts."""

    def __init__(self, receipt: dict, owned_process: subprocess.Popen | None = None):
        super().__init__("process_observation_incomplete")
        self.receipt = receipt
        self.owned_process = owned_process


class ObservationInterrupted(BaseException):
    """Unexpected interruption retains the owned child and partial evidence."""

    def __init__(self, receipt: dict, owned_process: subprocess.Popen | None):
        super().__init__("process_observation_interrupted")
        self.receipt = receipt
        self.owned_process = owned_process


def _digest(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while chunk := source.read(65536):
            digest.update(chunk)
            size += len(chunk)
    return {"path": str(path), "bytes": size, "sha256": digest.hexdigest()}


def _birth(process: subprocess.Popen) -> dict | None:
    if os.name != "nt":
        return None
    # Read the retained Popen handle, never OpenProcess(numeric PID).
    import ctypes
    from ctypes import wintypes
    created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
    get_times = ctypes.WinDLL("kernel32", use_last_error=True).GetProcessTimes
    get_times.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    get_times.restype = wintypes.BOOL
    if not get_times(wintypes.HANDLE(int(process._handle)), ctypes.byref(created),
                     ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
        raise OSError(ctypes.get_last_error(), "GetProcessTimes")
    return {"kind": "windows_retained_handle_creation_filetime",
            "value": (created.dwHighDateTime << 32) | created.dwLowDateTime}


def observe_process(
    argv: list[str], stdout_path: Path, stderr_path: Path, *,
    cwd: Path | None = None, env: dict[str, str] | None = None,
    progress: Callable[[dict], None] | None = None,
    admit: Callable[[], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    cooperative_cancel: Callable[[subprocess.Popen], None] | None = None,
    force_requested: Callable[[subprocess.Popen], dict | None] | None = None,
    stdout_budget: int | None = None, stderr_budget: int | None = None,
    source_paths: tuple[Path, ...] = (),
) -> dict:
    """Observe until actual child exit/reap and every started reader settles.

    Budgets limit retained bytes, never process lifetime or pipe draining. A
    truncated prefix is incomplete. Cooperative notification does not prove
    cleanup. Force requires a distinct grant referencing this exact Popen object:
    {action: 'force_cancel_exact_owned_host_child', owned_process: process,
     session_id: progress session_id, pid: process.pid, birth_identity: birth,
     cooperative_notice_id: progress cooperative_notice_id,
     request_id: a distinct caller-authenticated second request identifier}.
    The caller must authenticate that grant; object equality is not authorization.
    Callback exceptions become diagnostic errors, not implicit cancellation.
    The separate admit callback runs once immediately before Popen and may
    reject dispatch. It is caller admission, not a progress/cleanup callback.
    """
    if (type(argv) is not list or not argv
            or any(type(arg) is not str or not arg or "\0" in arg for arg in argv)):
        raise ValueError("nonempty_argv_strings_required")
    for budget in (stdout_budget, stderr_budget):
        if budget is not None and (type(budget) is not int or budget < 0):
            raise ValueError("retained_budget_nonnegative_integer_required")
    paths = (Path(stdout_path), Path(stderr_path))
    if paths[0].resolve() == paths[1].resolve():
        raise ValueError("distinct_raw_paths_required")
    started = time.monotonic_ns()
    lock = threading.Lock()
    errors: list[dict] = []
    streams: dict[str, dict] = {}
    process = None
    files = []
    readers = []
    receipt = {"schema": SCHEMA, "session_id": uuid.uuid4().hex,
               "argv": list(argv), "child_started": False,
               "pid": None, "birth_identity": None, "exit_known": False,
               "exit_code": None, "process_reaped": False, "streams": streams,
               "observer_errors": errors, "cancel_requested": False,
               "cooperative_notification_returned": False,
               "cooperative_notice_id": None,
               "explicit_force_requested": False, "owned_kill_attempted": False,
               "owned_kill_returned": False, "observation_complete": False,
               "termination_reason": None, "source_changed": False}

    def error(phase, exception):
        with lock:
            row = next((row for row in errors if row["phase"] == phase), None)
            if row is None:
                errors.append({"phase": phase, "type": type(exception).__name__, "count": 1})
            else:
                row["count"] += 1

    def emit(phase):
        if progress is not None:
            with lock:
                event = {"schema": "rusty.hostess.process_progress.v1", "phase": phase,
                         "pid": receipt["pid"], "session_id": receipt["session_id"],
                         "birth_identity": receipt["birth_identity"],
                         "cooperative_notice_id": receipt["cooperative_notice_id"],
                         "elapsed_ns": time.monotonic_ns() - started,
                         "exit_observed": process is not None and process.returncode is not None,
                         "streams": {name: dict(row) for name, row in streams.items()}}
            try:
                progress(event)
            except Exception as exception:
                error("progress", exception)

    def close_prelaunch_raw():
        # No pipe/EOF exists before dispatch. Preserve empty raw files as closed
        # evidence without claiming a launched child's capture completed.
        for name, file, path in zip(("stdout", "stderr"), files, paths):
            row = {"observed_bytes": 0, "retained_bytes": 0, "eof": False,
                   "budget_exceeded": False, "error": None,
                   "raw_file_closed": False, "settled": True,
                   "initialization": "not_started"}
            streams[name] = row
            try:
                file.close()
                row["raw_file_closed"] = file.closed
                if row["raw_file_closed"]:
                    row["descriptor"] = _digest(path)
            except Exception as exception:
                row["error"] = type(exception).__name__
                error(name + "_prelaunch_close", exception)

    def read_pipe(name, pipe, file, budget):
        row = streams[name]
        sink_failed = False
        try:
            # Buffered read() can wait for a full block. read1 exposes a short
            # flushed diagnostic while its child is still alive.
            while chunk := pipe.read1(65536):
                with lock:
                    row["observed_bytes"] += len(chunk)
                    retained = chunk if budget is None else chunk[:max(0, budget - row["retained_bytes"])]
                if not sink_failed:
                    try:
                        file.write(retained)
                        file.flush()  # Make short live diagnostics observable.
                        with lock:
                            row["retained_bytes"] += len(retained)
                            row["budget_exceeded"] |= len(retained) != len(chunk)
                    except Exception as exception:
                        sink_failed = True
                        with lock:
                            row["error"] = type(exception).__name__
                        error(name + "_sink", exception)
                # A failed raw sink never closes the pipe early. Keep draining
                # without retaining, preserving unknown rather than SIGPIPE.
            with lock:
                row["eof"] = True
        except Exception as exception:
            with lock:
                row["error"] = type(exception).__name__
            error(name + "_read", exception)
        finally:
            try:
                file.flush()
                os.fsync(file.fileno())
            except Exception as exception:
                error(name + "_flush", exception)
            try:
                file.close()
                with lock:
                    row["raw_file_closed"] = file.closed
            except Exception as exception:
                error(name + "_close", exception)
            try:
                pipe.close()
            except Exception as exception:
                error(name + "_pipe_close", exception)
            with lock:
                row["settled"] = True

    try:
        # Source hashes are diagnostics, never authority or atomic snapshots.
        baseline = {str(path): _digest(Path(path)) for path in source_paths}
        receipt["source_before"] = baseline
        if cancelled is not None:
            before = cancelled()
            if type(before) is not bool:
                raise ValueError("cancel_boolean_required")
            if before:
                receipt["cancel_requested"] = True
                receipt["termination_reason"] = "cancelled_before_dispatch"
                return receipt
        for path in paths:
            files.append(path.open("xb"))
        emit("dispatch_before")
        if admit is not None:
            try:
                admit()
            except Exception as exception:
                error("admission", exception)
                raise
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        receipt.update(child_started=True, pid=process.pid)
        try:
            receipt["birth_identity"] = _birth(process)
        except Exception as exception:
            error("birth_identity", exception)
        # POSIX exposes retained object/session identity, no invented OS birth.
        emit("child_started")
        for name, pipe, file, budget in (
                ("stdout", process.stdout, files[0], stdout_budget),
                ("stderr", process.stderr, files[1], stderr_budget)):
            streams[name] = {"observed_bytes": 0, "retained_bytes": 0, "eof": False,
                             "budget_exceeded": False, "error": None,
                             "raw_file_closed": False, "settled": False,
                             "initialization": "not_started"}
            try:
                thread = threading.Thread(target=read_pipe, args=(name, pipe, file, budget),
                                          name="hostess-" + name, daemon=True)
                thread.start()
                readers.append(thread)
                streams[name]["initialization"] = "started"
            except Exception as exception:
                streams[name].update(initialization="failed", error=type(exception).__name__, settled=True)
                error(name + "_initialization", exception)
        while True:
            try:
                request = False if cancelled is None else cancelled()
                if type(request) is not bool:
                    raise ValueError("cancel_boolean_required")
                if request and not receipt["cancel_requested"]:
                    receipt["cancel_requested"] = True
                    receipt["cooperative_notice_id"] = uuid.uuid4().hex
                    if cooperative_cancel is None:
                        raise ValueError("cooperative_callback_required")
                    cooperative_cancel(process)
                    receipt["cooperative_notification_returned"] = True
                    emit("cooperative_notification_returned")
            except Exception as exception:
                error("cooperative_cancel", exception)
            if receipt["cancel_requested"] and not receipt["explicit_force_requested"]:
                try:
                    grant = None if force_requested is None else force_requested(process)
                    if grant is not None:
                        receipt["explicit_force_requested"] = True
                        if (type(grant) is not dict or set(grant) != {
                                "action", "owned_process", "session_id", "pid",
                                "birth_identity", "request_id", "cooperative_notice_id"}
                                or grant["action"] != "force_cancel_exact_owned_host_child"
                                or grant["owned_process"] is not process
                                or grant["session_id"] != receipt["session_id"]
                                or type(grant["pid"]) is not int or grant["pid"] != process.pid
                                or grant["birth_identity"] != receipt["birth_identity"]
                                or type(grant["request_id"]) is not str or not grant["request_id"]
                                or grant["request_id"] == receipt["cooperative_notice_id"]
                                or grant["cooperative_notice_id"] != receipt["cooperative_notice_id"]
                                or not receipt["cooperative_notification_returned"]
                                or (os.name == "nt" and receipt["birth_identity"] is None)):
                            raise ValueError("exact_owned_force_grant_required")
                        if process.poll() is None:
                            if _birth(process) != receipt["birth_identity"]:
                                raise ValueError("retained_birth_changed")
                            receipt["force_request_id"] = grant["request_id"]
                            receipt["owned_kill_attempted"] = True
                            process.kill()
                            receipt["owned_kill_returned"] = True
                except Exception as exception:
                    error("explicit_force", exception)
            for path in source_paths:
                try:
                    if _digest(Path(path)) != baseline[str(path)]:
                        receipt["source_changed"] = True
                except Exception as exception:
                    error("source_observation", exception)
            try:
                exited = process.poll() is not None
            except Exception as exception:
                error("child_observation", exception)
                exited = False
            with lock:
                settled = all(row["settled"] for row in streams.values())
            if exited and settled:
                break
            emit("pending")
            time.sleep(.05)  # Observation cadence, never a lifetime limit.
        receipt.update(exit_code=process.wait(), exit_known=True, process_reaped=True)
        for thread in readers:
            thread.join()  # Already settled; no timeout or kill.
        for pipe in (process.stdout, process.stderr):
            if not pipe.closed:
                try:
                    pipe.close()  # Also release any reader that failed initialization.
                except Exception as exception:
                    error("pipe_close_after_exit", exception)
        for name, file, path in zip(("stdout", "stderr"), files, paths):
            if not file.closed:
                try:
                    file.flush()
                    file.close()
                    streams[name]["raw_file_closed"] = file.closed
                except Exception as exception:
                    error(name + "_close", exception)
            try:
                if not streams[name]["raw_file_closed"]:
                    raise RuntimeError("raw_hash_requires_closed_file")
                streams[name]["descriptor"] = _digest(path)
            except Exception as exception:
                error(name + "_descriptor", exception)
        receipt["termination_reason"] = ("explicit_owned_force" if receipt["owned_kill_attempted"]
            else "cooperative_cancel_exit" if receipt["cancel_requested"] else "genuine_child_exit")
        emit("complete")
        receipt["elapsed_ns"] = time.monotonic_ns() - started
        receipt["observation_complete"] = not errors and all(
            row["eof"] and row["raw_file_closed"] and not row["budget_exceeded"]
            for row in streams.values())
        if not receipt["observation_complete"]:
            raise ObservationFailure(receipt, process)
        return receipt
    except ObservationFailure:
        raise
    except Exception as exception:
        error("launch_or_observation", exception)
        if process is None:
            close_prelaunch_raw()
        receipt["elapsed_ns"] = time.monotonic_ns() - started
        raise ObservationFailure(receipt, process) from exception
    except BaseException as exception:
        error("interrupted", exception)
        if process is None:
            close_prelaunch_raw()
        receipt["elapsed_ns"] = time.monotonic_ns() - started
        raise ObservationInterrupted(receipt, process) from exception
    finally:
        # Never kill or wait implicitly. Live-child interruptions retain its
        # object in ObservationInterrupted; daemon readers remain diagnostics.
        if process is None:
            for file in files:
                if not file.closed:
                    try:
                        file.close()
                    except Exception as exception:
                        error("prelaunch_final_close", exception)
