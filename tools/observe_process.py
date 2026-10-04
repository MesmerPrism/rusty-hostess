#!/usr/bin/env python3
"""Typed CLI for the Hostess completion-driven host process API."""
import argparse
import json
import os
from pathlib import Path

if __package__:
    from .hostessctl.process_observation import (
        ObservationFailure, ObservationInterrupted, observe_process,
    )
else:
    from hostessctl.process_observation import (
        ObservationFailure, ObservationInterrupted, observe_process,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new evidence directory")
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--cancel-request", type=Path)
    parser.add_argument("--force-request", type=Path)
    parser.add_argument("--stdout-budget", type=int)
    parser.add_argument("--stderr-budget", type=int)
    parser.add_argument("--source", type=Path, action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("command required after --")
    args.out.mkdir(parents=True, exist_ok=False)
    notice = args.out / "COOPERATIVE_CANCEL.json"
    environment = dict(os.environ, HOSTESS_COOPERATIVE_CANCEL_PATH=str(notice.resolve()))

    def cancelled():
        return args.cancel_request is not None and args.cancel_request.is_file()

    def cooperate(process):
        with notice.open("x", encoding="utf-8") as file:
            json.dump({"schema": "rusty.hostess.process_cancel_notice.v1", "pid": process.pid}, file)

    def force(process):
        if args.force_request is None or not args.force_request.is_file():
            return None
        # Fixed closed caller document; no PID lookup or reopened process.
        data = json.loads(args.force_request.read_text(encoding="utf-8"))
        if type(data) is not dict or set(data) != {
                "action", "session_id", "pid", "birth_identity", "request_id",
                "cooperative_notice_id"}:
            raise ValueError("closed_force_request_required")
        return dict(data, owned_process=process)

    with (args.out / "progress.jsonl").open("x", encoding="utf-8") as progress_file:
        def progress(event):
            progress_file.write(json.dumps(event) + "\n")
            progress_file.flush()

        try:
            receipt = observe_process(command, args.out / "stdout.raw", args.out / "stderr.raw",
                cwd=args.cwd, env=environment, progress=progress, cancelled=cancelled,
                cooperative_cancel=cooperate, force_requested=force,
                stdout_budget=args.stdout_budget, stderr_budget=args.stderr_budget,
                source_paths=tuple(args.source))
        except (ObservationFailure, ObservationInterrupted) as error:
            receipt = error.receipt
    with (args.out / "receipt.json").open("x", encoding="utf-8") as file:
        json.dump(receipt, file, indent=2)
    print(json.dumps(receipt))
    if (not receipt["observation_complete"] or receipt["cancel_requested"]
            or receipt["source_changed"]):
        return 1
    return 0 if receipt["exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
