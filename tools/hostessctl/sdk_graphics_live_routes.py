"""Single finite live test using the existing shader lifecycle handler."""
import json
from pathlib import Path

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


def run_live(args):
    from tools.hostessctl.sdk_graphics_live import LiveExecutor
    if not args.confirm_live_sdk_debug:
        raise ValueError("explicit_live_sdk_developer_dispatch_required")
    plan = plan_live(args)  # All local admission before any device contact.
    root = Path(args.evidence_root)
    executor = LiveExecutor(args.config, args.catalog, root)
    with (root/"plan.json").open("x") as stream:
        stream.write(json.dumps(plan, indent=2)+"\n")
    def checkpoint(report):
        number = len(list(root.glob("checkpoint-*.json")))
        with (root/f"checkpoint-{number:04}.json").open("x") as stream:
            stream.write(json.dumps(report, indent=2)+"\n")
    session = ShaderIteration(Path(args.catalog), executor, checkpoint=checkpoint)
    def cycle(action, batch):
        session.handle(action, batch=Path(batch))
        session.handle("transfer")
        session.handle("reload")
        for _ in range(3):
            report = session.handle("observe")
            if report["phase"] == "observed":
                return True
        return False  # Keep original trigger; no replay or automatic revert.
    operation_error = None
    try:
        adopted = cycle("prepare", args.candidate_batch)
        restored = cycle("revert", args.baseline_batch) if adopted else False
        report = session.report()
        report.update(candidate_pixel_predicate_observed=adopted, baseline_pixel_predicate_observed=restored,
                      runtime_backend=executor.evidence_scope, sdk_completion_callback=False)
        return report
    except BaseException as error:
        operation_error = error
        raise
    finally:
        # Preserve known or unknown lifecycle even if host/report observation fails.
        # This is a report write, never cleanup, replay or an operation verdict.
        try:
            with (root/"terminal-report.json").open("x") as stream:
                stream.write(json.dumps(session.report(), indent=2)+"\n")
        except OSError as error:
            session.reporting_errors.append({"stage": "terminal-report", "error_type": type(error).__name__})
            if operation_error is not None:
                operation_error.sdk_graphics_report = session.report()
            else:
                report.update(session.report())  # Reporting warning, known lifecycle unchanged.
