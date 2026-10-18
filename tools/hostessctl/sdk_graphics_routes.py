"""CLI projection over the shader preparation and finite lifecycle APIs."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from tools.hostessctl import sdk_graphics_batch as batches
from tools.hostessctl.sdk_graphics_iteration import ACTIONS, ShaderIteration


def add_arguments(subcommands):
    parser = subcommands.add_parser("sdk-graphics")
    actions = parser.add_subparsers(dest="sdk_graphics_action", required=True)
    describe = actions.add_parser("describe")
    describe.add_argument("--out", required=True)
    prepare = actions.add_parser("prepare")
    for name in ("owner-app", "preparer-sha256", "reflector-sha256", "baseline-catalog",
                 "batch-output", "process-evidence", "glslc", "spirv-val", "spirv-dis",
                 "headers", "shader-config", "out"):
        prepare.add_argument("--" + name, required=True)
    mode = prepare.add_mutually_exclusive_group(required=True)
    mode.add_argument("--source-directory")
    mode.add_argument("--baseline-revert", action="store_true")
    fixture = actions.add_parser("fixture")
    for name in ("catalog", "baseline-batch", "candidate-batch", "consumer-root", "out"):
        fixture.add_argument("--" + name, required=True)
    return parser


def describe():
    # No source reads, executors, child processes, target discovery or backend.
    return {"schema": "rusty.hostess.sdk_graphics.capability.v1",
            "actions": list(ACTIONS), "host_preparation": True,
            "live_backend": "unavailable-not-qualified",
            "selected_consumer_contract": "optimized-sdk014-ten-vec4-160-byte-v1",
            "fixture_backend": "neutral-file-consumer-no-gpu",
            "availability_is_execution_grant": False,
            "report_schema": "rusty.hostess.sdk_graphics.iteration.v1"}


def run_fixture(args):
    from tools.hostessctl.sdk_graphics_fixture import FileConsumer
    # Validate both closures before creating any consumer or transferring bytes.
    baseline = batches.load_batch(Path(args.baseline_batch), Path(args.catalog))
    candidate = batches.load_batch(Path(args.candidate_batch), Path(args.catalog))
    if baseline["mode"] != "exact-baseline-revert" or candidate["mode"] != "fresh-source":
        raise ValueError("baseline_and_candidate_modes_required")
    consumer = FileConsumer(Path(args.consumer_root))
    def checkpoint(report):
        number = len(list(consumer.root.glob("checkpoint-*.json")))
        with (consumer.root / f"checkpoint-{number:04}.json").open("x") as stream:
            stream.write(json.dumps(report, indent=2) + "\n")
    session = ShaderIteration(Path(args.catalog), consumer, checkpoint=checkpoint)
    try:
        for action, batch in (("prepare", args.baseline_batch), ("transfer", None),
                              ("reload", None), ("observe", None)):
            session.handle(action, batch=Path(batch) if batch else None)
        before = consumer.observe()["witness_sha256"]
        for action, batch in (("prepare", args.candidate_batch), ("transfer", None),
                              ("reload", None), ("observe", None),
                              ("revert", args.baseline_batch), ("transfer", None),
                              ("reload", None), ("observe", None)):
            session.handle(action, batch=Path(batch) if batch else None)
        report = session.report()
        report["baseline_witness_restored"] = consumer.observe()["witness_sha256"] == before
        if not report["baseline_witness_restored"]:
            report["status"] = "fail"
        return report
    except BaseException:
        # Preserve original pending/unknown evidence. No automatic revert or kill.
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.exists():
            out.write_text(json.dumps(session.report(), indent=2) + "\n")
        raise


def run(args):
    out = Path(args.out)
    if out.exists():
        print("sdk-graphics: existing_report_refused", file=sys.stderr)
        return 2
    try:
        if args.sdk_graphics_action == "describe":
            report = describe()
        elif args.sdk_graphics_action == "prepare":
            report = batches.prepare(args)
        elif args.sdk_graphics_action == "fixture":
            report = run_fixture(args)
        else:
            raise ValueError("unsupported_sdk_graphics_action")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2) + "\n")
        return 0 if report.get("status") != "fail" else 2
    except (ValueError, OSError, KeyError, TypeError) as error:
        print("sdk-graphics: " + str(error), file=sys.stderr)
        return 2
