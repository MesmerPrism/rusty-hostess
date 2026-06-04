from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable

from tools.hostessctl.makepad_visual_profile import (
    MAKEPAD_VISUAL_PROFILE_ID,
    makepad_visual_profile_property_records,
    makepad_visual_profile_runtime_properties,
)


MAKEPAD_ANDROID_PACKAGE = "io.github.mesmerprism.rustyhostess.makepad"
MAKEPAD_ANDROID_ACTIVITY = f"{MAKEPAD_ANDROID_PACKAGE}/.MakepadApp"
MAKEPAD_ANDROID_XR_ACTIVITY = f"{MAKEPAD_ANDROID_PACKAGE}/.MakepadAppXr"
MAKEPAD_SHELL_REMOTE_SUBDIR = "files/hostess-t/shell"
MAKEPAD_SHELL_LAUNCH_HANDOFF_REMOTE_NAME = "makepad-shell-launch-handoff.json"
MAKEPAD_SHELL_CONTRACT_REMOTE_NAME = "makepad-shell-contract-receipt.json"
MAKEPAD_SHELL_CONTRACT_READ_RECEIPT_REMOTE_NAME = "makepad-shell-contract-read-receipt.json"
MAKEPAD_SHELL_RUNTIME_CAPABILITY_RECEIPT_REMOTE_NAME = (
    "makepad-shell-runtime-capability-receipt.json"
)
MAKEPAD_SHELL_CONTRACT_READ_RECEIPT_RELATIVE = (
    f"{MAKEPAD_SHELL_REMOTE_SUBDIR}/{MAKEPAD_SHELL_CONTRACT_READ_RECEIPT_REMOTE_NAME}"
)
MAKEPAD_SHELL_RUNTIME_CAPABILITY_RECEIPT_RELATIVE = (
    f"{MAKEPAD_SHELL_REMOTE_SUBDIR}/{MAKEPAD_SHELL_RUNTIME_CAPABILITY_RECEIPT_REMOTE_NAME}"
)
MAKEPAD_SHELL_LAUNCH_HANDOFF_SCHEMA = "rusty.hostess.makepad_shell_launch_handoff_receipt.v1"
MAKEPAD_SHELL_CONTRACT_SCHEMA = "rusty.hostess.makepad_shell_contract_receipt.v1"
MAKEPAD_SHELL_CONTRACT_LAUNCH_EVIDENCE_SCHEMA = (
    "rusty.hostess.makepad_shell_contract_launch_evidence.v1"
)
MAKEPAD_SHELL_CONTRACT_LAUNCH_VALIDATION_SCHEMA = (
    "rusty.hostess.makepad_shell_contract_launch_validation.v1"
)
MAKEPAD_QUEST_REFERENCE_PREGRANT_PERMISSIONS = [
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
    "com.oculus.permission.USE_SCENE",
    "horizonos.permission.USE_SCENE",
    "horizonos.permission.HEADSET_CAMERA",
    "horizonos.permission.AVATAR_CAMERA",
]


def launch_makepad_shell_contract(
    args: argparse.Namespace,
    *,
    adb_prefix: Callable[[argparse.Namespace], list[str]],
    host_app_for: Callable[[str], str],
    run: Callable[..., Any],
    wait_for_android_run_as_file: Callable[
        [argparse.Namespace, str, str, float],
        None,
    ],
    pull_android_run_as_file: Callable[[argparse.Namespace, str, str, Path], None],
    write_android_run_as_file: Callable[
        [argparse.Namespace, str, str, bytes],
        None,
    ],
) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    launch_handoff_path = Path(args.launch_handoff)
    launch_handoff = load_labeled_json_object(launch_handoff_path, "Makepad shell launch handoff")
    contract_path_text = (
        launch_handoff.get("makepad_contract_reader_input_path")
        or launch_handoff.get("source_makepad_shell_contract_receipt_path")
    )
    contract_path = Path(contract_path_text) if isinstance(contract_path_text, str) else None
    contract_receipt = (
        load_labeled_json_object(contract_path, "Makepad shell contract receipt")
        if contract_path is not None and contract_path.is_file()
        else {}
    )
    checks = validate_makepad_shell_contract_launch_inputs(
        launch_handoff,
        contract_receipt,
        contract_path,
    )
    descriptor_fallback_used = (
        launch_handoff.get("descriptor_fallback_used") is True
        or contract_receipt.get("descriptor_fallback_used") is True
    )
    legacy_rusty_xr_dependency_used = (
        launch_handoff.get("legacy_rusty_xr_dependency_used") is True
        or contract_receipt.get("legacy_rusty_xr_dependency_used") is True
    )
    failed = [entry for entry in checks if entry["status"] == "fail"]

    remote_dir = args.remote_dir or makepad_shell_remote_dir(args.makepad_package)
    remote_contract_path = makepad_shell_remote_path(remote_dir, MAKEPAD_SHELL_CONTRACT_REMOTE_NAME)
    remote_launch_path = makepad_shell_remote_path(
        remote_dir,
        MAKEPAD_SHELL_LAUNCH_HANDOFF_REMOTE_NAME,
    )
    device_contract_path = out.with_name(f"{out.stem}.device-contract.json")
    device_launch_path = out.with_name(f"{out.stem}.device-launch-handoff.json")
    read_receipt_path = out.with_name(f"{out.stem}.makepad-contract-read-receipt.json")
    runtime_capability_receipt_path = out.with_name(
        f"{out.stem}.makepad-runtime-capability-receipt.json"
    )

    if contract_receipt:
        device_contract_path.write_text(
            json.dumps(contract_receipt, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    device_launch_handoff = build_device_makepad_shell_launch_handoff(
        launch_handoff=launch_handoff,
        host_launch_handoff_path=launch_handoff_path,
        host_contract_path=contract_path,
        remote_launch_path=remote_launch_path,
        remote_contract_path=remote_contract_path,
    )
    device_launch_path.write_text(
        json.dumps(device_launch_handoff, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    status = "ready" if not failed else "rejected"
    issue_code = failed[0]["issue_code"] if failed else None
    pulled_read_receipt: dict[str, Any] | None = None
    pulled_runtime_capability_receipt: dict[str, Any] | None = None
    adb_execution_performed = False
    push_performed = False
    app_private_write_performed = False
    launch_started = False
    makepad_contract_read_receipt_pulled = False
    makepad_runtime_capability_receipt_pulled = False
    permission_pregrant_performed = False
    permission_grant_records: list[dict[str, Any]] = []
    visual_profile_setprops_performed = False
    visual_profile_property_records: list[dict[str, str]] = []
    runtime_observation_poll_performed = False
    runtime_observation_pull_count = 0

    if status == "ready" and not args.plan_only:
        if not args.adb or not args.serial:
            raise SystemExit("launch-makepad-shell-contract requires --adb and --serial without --plan-only")
        adb_execution_performed = True
        activity = makepad_shell_activity(
            args.makepad_package,
            getattr(args, "makepad_activity", None),
            getattr(args, "target", None),
        )
        if makepad_shell_uses_run_as(remote_dir, args.makepad_package):
            run(
                adb_prefix(args)
                + ["shell", "run-as", args.makepad_package, "mkdir", "-p", MAKEPAD_SHELL_REMOTE_SUBDIR]
            )
            run(
                adb_prefix(args)
                + [
                    "shell",
                    "run-as",
                    args.makepad_package,
                    "rm",
                    "-f",
                    makepad_shell_relative_path(MAKEPAD_SHELL_LAUNCH_HANDOFF_REMOTE_NAME),
                    makepad_shell_relative_path(MAKEPAD_SHELL_CONTRACT_REMOTE_NAME),
                    MAKEPAD_SHELL_CONTRACT_READ_RECEIPT_RELATIVE,
                    MAKEPAD_SHELL_RUNTIME_CAPABILITY_RECEIPT_RELATIVE,
                ],
                allow_failure=True,
            )
            write_android_run_as_file(
                args,
                args.makepad_package,
                makepad_shell_relative_path(MAKEPAD_SHELL_CONTRACT_REMOTE_NAME),
                device_contract_path.read_bytes(),
            )
            write_android_run_as_file(
                args,
                args.makepad_package,
                makepad_shell_relative_path(MAKEPAD_SHELL_LAUNCH_HANDOFF_REMOTE_NAME),
                device_launch_path.read_bytes(),
            )
            app_private_write_performed = True
        else:
            run(adb_prefix(args) + ["shell", "mkdir", "-p", remote_dir])
            run(adb_prefix(args) + ["push", str(device_contract_path), remote_contract_path])
            run(adb_prefix(args) + ["push", str(device_launch_path), remote_launch_path])
            push_performed = True
            run(
                adb_prefix(args)
                + [
                    "shell",
                    "run-as",
                    args.makepad_package,
                    "rm",
                    "-f",
                    MAKEPAD_SHELL_CONTRACT_READ_RECEIPT_RELATIVE,
                    MAKEPAD_SHELL_RUNTIME_CAPABILITY_RECEIPT_RELATIVE,
                ],
                allow_failure=True,
            )
        if not getattr(args, "skip_pregrant_permissions", False):
            permission_pregrant_performed = True
            permission_grant_records = pregrant_makepad_shell_permissions(
                args,
                adb_prefix=adb_prefix,
                run=run,
            )
        visual_profile_property_records = apply_makepad_visual_profile_runtime_properties(
            args,
            adb_prefix=adb_prefix,
            run=run,
        )
        visual_profile_setprops_performed = True
        run(
            adb_prefix(args) + ["shell", "am", "force-stop", args.makepad_package],
            allow_failure=True,
        )
        run(adb_prefix(args) + ["shell", "am", "start", "-n", activity])
        launch_started = True
        wait_for_android_run_as_file(
            args,
            args.makepad_package,
            MAKEPAD_SHELL_CONTRACT_READ_RECEIPT_RELATIVE,
            args.wait_seconds,
        )
        pull_android_run_as_file(
            args,
            args.makepad_package,
            MAKEPAD_SHELL_CONTRACT_READ_RECEIPT_RELATIVE,
            read_receipt_path,
        )
        makepad_contract_read_receipt_pulled = True
        pulled_read_receipt = json.loads(read_receipt_path.read_text(encoding="utf-8"))
        if pulled_read_receipt.get("status") != "read":
            status = "fail"
            issue_code = (
                pulled_read_receipt.get("issue_code")
                or "hostess.issue.makepad_shell_contract_launch_read_receipt"
            )
        else:
            wait_for_android_run_as_file(
                args,
                args.makepad_package,
                MAKEPAD_SHELL_RUNTIME_CAPABILITY_RECEIPT_RELATIVE,
                args.wait_seconds,
            )
            (
                pulled_runtime_capability_receipt,
                runtime_observation_poll_performed,
                runtime_observation_pull_count,
            ) = pull_runtime_capability_receipt_until_observed(
                args,
                pull_android_run_as_file=pull_android_run_as_file,
                runtime_capability_receipt_path=runtime_capability_receipt_path,
            )
            makepad_runtime_capability_receipt_pulled = (
                pulled_runtime_capability_receipt is not None
            )
            if pulled_runtime_capability_receipt is None:
                status = "fail"
                issue_code = "hostess.issue.makepad_shell_runtime_capability_receipt_missing"
            elif pulled_runtime_capability_receipt.get("status") not in {
                "incomplete",
                "ready",
                "completed",
            }:
                status = "fail"
                issue_code = (
                    pulled_runtime_capability_receipt.get("issue_code")
                    or "hostess.issue.makepad_shell_runtime_capability_receipt"
                )
            else:
                status = "completed"

    evidence = build_makepad_shell_contract_launch_evidence(
        args=args,
        status=status,
        issue_code=issue_code,
        checks=checks,
        launch_handoff_path=launch_handoff_path,
        contract_path=contract_path,
        device_launch_path=device_launch_path,
        device_contract_path=device_contract_path,
        read_receipt_path=read_receipt_path,
        runtime_capability_receipt_path=runtime_capability_receipt_path,
        remote_dir=remote_dir,
        remote_launch_path=remote_launch_path,
        remote_contract_path=remote_contract_path,
        adb_execution_performed=adb_execution_performed,
        push_performed=push_performed,
        app_private_write_performed=app_private_write_performed,
        launch_started=launch_started,
        makepad_contract_read_receipt_pulled=makepad_contract_read_receipt_pulled,
        pulled_read_receipt=pulled_read_receipt,
        makepad_runtime_capability_receipt_pulled=makepad_runtime_capability_receipt_pulled,
        pulled_runtime_capability_receipt=pulled_runtime_capability_receipt,
        descriptor_fallback_used=descriptor_fallback_used,
        legacy_rusty_xr_dependency_used=legacy_rusty_xr_dependency_used,
        permission_pregrant_performed=permission_pregrant_performed,
        permission_grant_records=permission_grant_records,
        visual_profile_setprops_performed=visual_profile_setprops_performed,
        visual_profile_property_records=visual_profile_property_records,
        runtime_observation_poll_performed=runtime_observation_poll_performed,
        runtime_observation_pull_count=runtime_observation_pull_count,
    )
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    validation = validate_makepad_shell_contract_launch_evidence(evidence)
    out.with_name(f"{out.stem}.validation-report.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_makepad_shell_contract_launch_host_run_evidence(
        out,
        validation,
        evidence,
        host_app_for=host_app_for,
    )
    return 0 if evidence["status"] in {"ready", "completed"} else 2


def pregrant_makepad_shell_permissions(
    args: argparse.Namespace,
    *,
    adb_prefix: Callable[[argparse.Namespace], list[str]],
    run: Callable[..., Any],
) -> list[dict[str, Any]]:
    records = []
    for permission in MAKEPAD_QUEST_REFERENCE_PREGRANT_PERMISSIONS:
        command = adb_prefix(args) + [
            "shell",
            "pm",
            "grant",
            args.makepad_package,
            permission,
        ]
        result = run(command, allow_failure=True)
        records.append(
            {
                "permission": permission,
                "command": " ".join(command),
                "return_code": getattr(result, "returncode", None),
            }
        )
    return records


def apply_makepad_visual_profile_runtime_properties(
    args: argparse.Namespace,
    *,
    adb_prefix: Callable[[argparse.Namespace], list[str]],
    run: Callable[..., Any],
) -> list[dict[str, str]]:
    records = []
    for key, value in makepad_visual_profile_runtime_properties().items():
        run(
            adb_prefix(args) + ["shell", "setprop", key, value],
            allow_failure=False,
        )
        records.append({"key": key, "value": value})
    return records


def pull_runtime_capability_receipt_until_observed(
    args: argparse.Namespace,
    *,
    pull_android_run_as_file: Callable[[argparse.Namespace, str, str, Path], None],
    runtime_capability_receipt_path: Path,
) -> tuple[dict[str, Any] | None, bool, int]:
    observation_seconds = max(0.0, float(getattr(args, "runtime_observation_seconds", 0.0)))
    poll_seconds = max(
        0.1,
        float(getattr(args, "runtime_observation_poll_ms", 750.0)) / 1000.0,
    )
    deadline = time.monotonic() + observation_seconds
    pull_count = 0
    poll_performed = observation_seconds > 0.0
    last_receipt: dict[str, Any] | None = None

    while True:
        pull_android_run_as_file(
            args,
            args.makepad_package,
            MAKEPAD_SHELL_RUNTIME_CAPABILITY_RECEIPT_RELATIVE,
            runtime_capability_receipt_path,
        )
        pull_count += 1
        try:
            last_receipt = json.loads(runtime_capability_receipt_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            last_receipt = None
            if time.monotonic() >= deadline:
                return last_receipt, poll_performed, pull_count
            time.sleep(poll_seconds)
            continue
        if runtime_receipt_observed_enough(last_receipt):
            return last_receipt, poll_performed, pull_count
        if time.monotonic() >= deadline:
            return last_receipt, poll_performed, pull_count
        time.sleep(poll_seconds)


def runtime_receipt_observed_enough(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("xr_update_observed") is True
        or receipt.get("controller_pose_provider_observed") is True
        or receipt.get("status") in {"ready", "completed"}
    )


def load_labeled_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"{label} not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a JSON object: {path}")
    return payload


def makepad_shell_remote_dir(package: str) -> str:
    return f"/data/user/0/{package}/{MAKEPAD_SHELL_REMOTE_SUBDIR}"


def makepad_shell_remote_path(remote_dir: str, name: str) -> str:
    return f"{remote_dir.rstrip('/')}/{name}"


def makepad_shell_relative_path(name: str) -> str:
    return f"{MAKEPAD_SHELL_REMOTE_SUBDIR}/{name}"


def makepad_shell_uses_run_as(remote_dir: str, package: str) -> bool:
    return remote_dir.rstrip("/").startswith(f"/data/user/0/{package}/")


def makepad_shell_activity(package: str, activity: str | None, target: str | None) -> str:
    if activity == MAKEPAD_ANDROID_ACTIVITY and package != MAKEPAD_ANDROID_PACKAGE:
        return f"{package}/.MakepadApp"
    if activity == MAKEPAD_ANDROID_XR_ACTIVITY and package != MAKEPAD_ANDROID_PACKAGE:
        return f"{package}/.MakepadAppXr"
    if activity:
        return activity
    if target == "quest":
        return f"{package}/.MakepadAppXr"
    return f"{package}/.MakepadApp"


def build_device_makepad_shell_launch_handoff(
    *,
    launch_handoff: dict[str, Any],
    host_launch_handoff_path: Path,
    host_contract_path: Path | None,
    remote_launch_path: str,
    remote_contract_path: str,
) -> dict[str, Any]:
    device_launch_handoff = dict(launch_handoff)
    device_launch_handoff["makepad_contract_reader_input_path"] = remote_contract_path
    device_launch_handoff["source_makepad_shell_contract_receipt_path"] = remote_contract_path
    device_launch_handoff["host_local_makepad_shell_launch_handoff_receipt_path"] = str(
        host_launch_handoff_path
    )
    device_launch_handoff["host_local_makepad_shell_contract_receipt_path"] = (
        str(host_contract_path) if host_contract_path is not None else None
    )
    device_launch_handoff["device_makepad_shell_launch_handoff_receipt_path"] = remote_launch_path
    device_launch_handoff["device_makepad_shell_contract_receipt_path"] = remote_contract_path
    device_launch_handoff["device_path_rewrite_performed"] = True
    return device_launch_handoff


def validate_makepad_shell_contract_launch_inputs(
    launch_handoff: dict[str, Any],
    contract_receipt: dict[str, Any],
    contract_path: Path | None,
) -> list[dict[str, Any]]:
    descriptor_fallback_used = (
        launch_handoff.get("descriptor_fallback_used") is True
        or contract_receipt.get("descriptor_fallback_used") is True
    )
    legacy_rusty_xr_dependency_used = (
        launch_handoff.get("legacy_rusty_xr_dependency_used") is True
        or contract_receipt.get("legacy_rusty_xr_dependency_used") is True
    )
    return [
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch.launch_schema",
            launch_handoff.get("$schema") == MAKEPAD_SHELL_LAUNCH_HANDOFF_SCHEMA,
            "Makepad shell launch handoff schema is supported",
            "Makepad shell launch handoff schema is unsupported",
            "hostess.issue.makepad_shell_contract_launch_schema",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch.launch_ready",
            launch_handoff.get("status") == "ready"
            and launch_handoff.get("makepad_contract_reader_ready") is True
            and launch_handoff.get("makepad_launch_handoff_ready") is True,
            "Makepad shell launch handoff is ready for clean Makepad intake",
            "Makepad shell launch handoff is not ready for clean Makepad intake",
            "hostess.issue.makepad_shell_contract_launch_not_ready",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch.contract_path",
            contract_path is not None and contract_path.is_file(),
            "Makepad shell contract receipt exists on the host",
            "Makepad shell contract receipt is missing on the host",
            "hostess.issue.makepad_shell_contract_launch_contract_path",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch.contract_schema",
            contract_receipt.get("$schema") == MAKEPAD_SHELL_CONTRACT_SCHEMA,
            "Makepad shell contract receipt schema is supported",
            "Makepad shell contract receipt schema is unsupported",
            "hostess.issue.makepad_shell_contract_launch_contract_schema",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch.contract_ready",
            contract_receipt.get("status") == "accepted"
            and contract_receipt.get("makepad_shell_contract_ready") is True,
            "Makepad shell contract receipt is accepted and ready",
            "Makepad shell contract receipt is not accepted and ready",
            "hostess.issue.makepad_shell_contract_launch_contract_not_ready",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch.linkage",
            contract_receipt
            and launch_handoff.get("selected_handoff_id")
            == contract_receipt.get("selected_handoff_id")
            and launch_handoff.get("selected_shell_app_id")
            == contract_receipt.get("selected_shell_app_id")
            and launch_handoff.get("expected_reader_contract_schema")
            == MAKEPAD_SHELL_CONTRACT_SCHEMA,
            "Makepad shell launch handoff links to the accepted contract receipt",
            "Makepad shell launch handoff does not link to the accepted contract receipt",
            "hostess.issue.makepad_shell_contract_launch_linkage",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch.clean_route",
            not descriptor_fallback_used and not legacy_rusty_xr_dependency_used,
            "Makepad shell launch uses the clean Hostess/Manifold route",
            "Makepad shell launch uses descriptor fallback or legacy Rusty-XR",
            "hostess.issue.makepad_shell_contract_launch_legacy_or_fallback",
        ),
    ]


def makepad_shell_launch_check(
    check_id: str,
    passed: bool,
    pass_evidence: str,
    fail_evidence: str,
    issue_code: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": pass_evidence if passed else fail_evidence,
        "issue_code": None if passed else issue_code,
    }


def build_makepad_shell_contract_launch_evidence(
    *,
    args: argparse.Namespace,
    status: str,
    issue_code: str | None,
    checks: list[dict[str, Any]],
    launch_handoff_path: Path,
    contract_path: Path | None,
    device_launch_path: Path,
    device_contract_path: Path,
    read_receipt_path: Path,
    runtime_capability_receipt_path: Path,
    remote_dir: str,
    remote_launch_path: str,
    remote_contract_path: str,
    adb_execution_performed: bool,
    push_performed: bool,
    app_private_write_performed: bool,
    launch_started: bool,
    makepad_contract_read_receipt_pulled: bool,
    pulled_read_receipt: dict[str, Any] | None,
    makepad_runtime_capability_receipt_pulled: bool,
    pulled_runtime_capability_receipt: dict[str, Any] | None,
    descriptor_fallback_used: bool,
    legacy_rusty_xr_dependency_used: bool,
    permission_pregrant_performed: bool,
    permission_grant_records: list[dict[str, Any]],
    visual_profile_setprops_performed: bool,
    visual_profile_property_records: list[dict[str, str]],
    runtime_observation_poll_performed: bool,
    runtime_observation_pull_count: int,
) -> dict[str, Any]:
    runtime_status = (
        pulled_runtime_capability_receipt.get("status")
        if pulled_runtime_capability_receipt
        else None
    )
    runtime_missing = (
        pulled_runtime_capability_receipt.get("missing_capabilities")
        if pulled_runtime_capability_receipt
        else []
    )
    if not isinstance(runtime_missing, list):
        runtime_missing = []
    runtime_implemented = (
        pulled_runtime_capability_receipt.get("implemented_capabilities")
        if pulled_runtime_capability_receipt
        else []
    )
    if not isinstance(runtime_implemented, list):
        runtime_implemented = []
    return {
        "$schema": MAKEPAD_SHELL_CONTRACT_LAUNCH_EVIDENCE_SCHEMA,
        "status": status,
        "issue_code": issue_code,
        "target": args.target,
        "plan_only": args.plan_only,
        "device_required": True,
        "adb_execution_performed": adb_execution_performed,
        "push_performed": push_performed,
        "app_private_write_performed": app_private_write_performed,
        "launch_started": launch_started,
        "permission_pregrant_performed": permission_pregrant_performed,
        "permission_grant_records": permission_grant_records,
        "permission_grants_attempted": [
            record.get("permission")
            for record in permission_grant_records
            if isinstance(record, dict) and isinstance(record.get("permission"), str)
        ],
        "visual_profile_runtime_profile": MAKEPAD_VISUAL_PROFILE_ID,
        "visual_profile_setprops_performed": visual_profile_setprops_performed,
        "visual_profile_properties": (
            visual_profile_property_records or makepad_visual_profile_property_records()
        ),
        "visual_profile_processing_layer": (
            makepad_visual_profile_runtime_properties()["debug.rustyxr.processing.layer"]
        ),
        "visual_profile_source_sampling_mode": (
            makepad_visual_profile_runtime_properties()[
                "debug.rustyxr.camera.source.sampling.mode"
            ]
        ),
        "visual_profile_projection_border_policy": (
            makepad_visual_profile_runtime_properties()[
                "debug.rustyxr.projection.border.policy"
            ]
        ),
        "visual_profile_makepad_projection_border_policy": (
            makepad_visual_profile_runtime_properties()[
                "debug.rustyxr.makepad.projection.border.policy"
            ]
        ),
        "runtime_observation_poll_performed": runtime_observation_poll_performed,
        "runtime_observation_pull_count": runtime_observation_pull_count,
        "makepad_contract_read_receipt_pulled": makepad_contract_read_receipt_pulled,
        "makepad_contract_read_receipt_status": (
            pulled_read_receipt.get("status") if pulled_read_receipt else None
        ),
        "makepad_runtime_capability_receipt_pulled": (
            makepad_runtime_capability_receipt_pulled
        ),
        "makepad_runtime_capability_receipt_status": runtime_status,
        "makepad_runtime_capability_issue_code": (
            pulled_runtime_capability_receipt.get("issue_code")
            if pulled_runtime_capability_receipt
            else None
        ),
        "makepad_runtime_implemented_capabilities": runtime_implemented,
        "makepad_runtime_missing_capabilities": runtime_missing,
        "makepad_xr_root_registered": (
            pulled_runtime_capability_receipt.get("makepad_xr_root_registered")
            if pulled_runtime_capability_receipt
            else False
        ),
        "makepad_xr_update_observed": (
            pulled_runtime_capability_receipt.get("xr_update_observed")
            if pulled_runtime_capability_receipt
            else False
        ),
        "makepad_xr_update_count": (
            pulled_runtime_capability_receipt.get("xr_update_count")
            if pulled_runtime_capability_receipt
            else 0
        ),
        "makepad_in_xr_mode_observed": (
            pulled_runtime_capability_receipt.get("in_xr_mode_observed")
            if pulled_runtime_capability_receipt
            else False
        ),
        "makepad_controller_pose_provider_observed": (
            pulled_runtime_capability_receipt.get("controller_pose_provider_observed")
            if pulled_runtime_capability_receipt
            else False
        ),
        "makepad_left_controller_active": (
            pulled_runtime_capability_receipt.get("left_controller_active")
            if pulled_runtime_capability_receipt
            else False
        ),
        "makepad_right_controller_active": (
            pulled_runtime_capability_receipt.get("right_controller_active")
            if pulled_runtime_capability_receipt
            else False
        ),
        "final_clean_makepad_app_requires_xr": (
            pulled_runtime_capability_receipt.get("final_clean_makepad_app_requires_xr")
            if pulled_runtime_capability_receipt
            else True
        ),
        "makepad_xr_session_required": (
            pulled_runtime_capability_receipt.get("xr_session_required")
            if pulled_runtime_capability_receipt
            else True
        ),
        "makepad_controller_pose_required": (
            pulled_runtime_capability_receipt.get("controller_pose_required")
            if pulled_runtime_capability_receipt
            else True
        ),
        "makepad_camera_hwb_projection_required": (
            pulled_runtime_capability_receipt.get("camera_hardware_buffer_projection_required")
            if pulled_runtime_capability_receipt
            else True
        ),
        "makepad_custom_camera_projection_required": (
            pulled_runtime_capability_receipt.get("custom_camera_projection_required")
            if pulled_runtime_capability_receipt
            else True
        ),
        "makepad_breath_feedback_required": (
            pulled_runtime_capability_receipt.get("breath_feedback_required")
            if pulled_runtime_capability_receipt
            else True
        ),
        "makepad_broker_transport_required": (
            pulled_runtime_capability_receipt.get("broker_transport_required")
            if pulled_runtime_capability_receipt
            else True
        ),
        "makepad_package": args.makepad_package,
        "makepad_activity": makepad_shell_activity(
            args.makepad_package,
            getattr(args, "makepad_activity", None),
            getattr(args, "target", None),
        ),
        "source_makepad_shell_launch_handoff_receipt_path": str(launch_handoff_path),
        "source_makepad_shell_contract_receipt_path": (
            str(contract_path) if contract_path is not None else None
        ),
        "local_device_makepad_shell_launch_handoff_receipt_path": str(device_launch_path),
        "local_device_makepad_shell_contract_receipt_path": str(device_contract_path),
        "local_makepad_shell_contract_read_receipt_path": str(read_receipt_path),
        "local_makepad_shell_runtime_capability_receipt_path": str(
            runtime_capability_receipt_path
        ),
        "device_makepad_shell_remote_dir": remote_dir,
        "device_makepad_shell_launch_handoff_receipt_path": remote_launch_path,
        "device_makepad_shell_contract_receipt_path": remote_contract_path,
        "device_makepad_shell_contract_read_receipt_relative_path": (
            MAKEPAD_SHELL_CONTRACT_READ_RECEIPT_RELATIVE
        ),
        "device_makepad_shell_runtime_capability_receipt_relative_path": (
            MAKEPAD_SHELL_RUNTIME_CAPABILITY_RECEIPT_RELATIVE
        ),
        "device_makepad_shell_staging_mode": (
            "run_as_app_private" if app_private_write_performed or makepad_shell_uses_run_as(remote_dir, args.makepad_package) else "adb_push"
        ),
        "descriptor_fallback_used": descriptor_fallback_used,
        "legacy_rusty_xr_dependency_used": legacy_rusty_xr_dependency_used,
        "old_makepad_provider_route_changed": False,
        "record_values_provider_route_changed": False,
        "next_required_action": (
            "run_device_launch_makepad_shell_contract"
            if status == "ready"
            else "implement_clean_makepad_xr_controller_hwb_runtime"
            if status == "completed" and runtime_status == "incomplete"
            else "run_polar_controller_pmb_makepad_closed_loop_device_test"
            if status == "completed"
            else "repair_makepad_shell_contract_launch_input"
        ),
        "checks": checks,
    }


def validate_makepad_shell_contract_launch_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    checks = [
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch_evidence.schema",
            evidence.get("$schema") == MAKEPAD_SHELL_CONTRACT_LAUNCH_EVIDENCE_SCHEMA,
            "Makepad shell contract launch evidence schema is supported",
            "Makepad shell contract launch evidence schema is unsupported",
            "hostess.issue.makepad_shell_contract_launch_evidence_schema",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch_evidence.status",
            evidence.get("status") in {"ready", "completed", "rejected", "fail"},
            "Makepad shell contract launch evidence status is supported",
            "Makepad shell contract launch evidence status is unsupported",
            "hostess.issue.makepad_shell_contract_launch_evidence_status",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch_evidence.device_paths",
            isinstance(evidence.get("device_makepad_shell_launch_handoff_receipt_path"), str)
            and isinstance(evidence.get("device_makepad_shell_contract_receipt_path"), str)
            and isinstance(evidence.get("device_makepad_shell_contract_read_receipt_relative_path"), str)
            and isinstance(
                evidence.get("device_makepad_shell_runtime_capability_receipt_relative_path"),
                str,
            ),
            "Makepad shell contract launch evidence includes device paths",
            "Makepad shell contract launch evidence is missing device paths",
            "hostess.issue.makepad_shell_contract_launch_evidence_device_paths",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch_evidence.plan_or_receipt",
            (
                evidence.get("status") == "ready"
                and evidence.get("plan_only") is True
                and evidence.get("adb_execution_performed") is False
            )
            or (
                evidence.get("status") == "completed"
                and evidence.get("makepad_contract_read_receipt_pulled") is True
                and evidence.get("makepad_contract_read_receipt_status") == "read"
                and evidence.get("makepad_runtime_capability_receipt_pulled") is True
                and evidence.get("makepad_runtime_capability_receipt_status")
                in {"incomplete", "ready", "completed"}
            )
            or evidence.get("status") in {"rejected", "fail"},
            "Makepad shell contract launch evidence matches plan or receipt mode",
            "Makepad shell contract launch evidence does not match plan or receipt mode",
            "hostess.issue.makepad_shell_contract_launch_evidence_mode",
        ),
        makepad_shell_launch_check(
            "hostess.check.makepad_shell_contract_launch_evidence.visual_profile",
            (
                evidence.get("status") in {"rejected", "fail"}
                or (
                    evidence.get("plan_only") is True
                    and evidence.get("visual_profile_setprops_performed") is False
                )
                or (
                    evidence.get("status") == "completed"
                    and evidence.get("visual_profile_setprops_performed") is True
                    and evidence.get("visual_profile_runtime_profile") == MAKEPAD_VISUAL_PROFILE_ID
                    and evidence.get("visual_profile_processing_layer")
                    == "peripheral-stretch"
                    and evidence.get("visual_profile_source_sampling_mode")
                    == "target-local-raster"
                    and evidence.get("visual_profile_projection_border_policy")
                    == "passthrough-underlay"
                    and evidence.get("visual_profile_makepad_projection_border_policy")
                    == "passthrough-underlay"
                )
            ),
            "Makepad shell launch applies the stretch visual runtime profile when executed",
            "Makepad shell launch is missing the stretch visual runtime profile",
            "hostess.issue.makepad_shell_contract_launch_visual_profile",
        ),
    ]
    embedded = [entry for entry in evidence.get("checks", []) if isinstance(entry, dict)]
    failed = [
        entry
        for entry in checks + embedded
        if entry.get("status") == "fail"
    ]
    return {
        "$schema": MAKEPAD_SHELL_CONTRACT_LAUNCH_VALIDATION_SCHEMA,
        "status": "pass" if not failed else "fail",
        "issue_code": failed[0].get("issue_code") if failed else None,
        "launch_started": evidence.get("launch_started") is True,
        "makepad_contract_read_receipt_pulled": (
            evidence.get("makepad_contract_read_receipt_pulled") is True
        ),
        "makepad_runtime_capability_receipt_pulled": (
            evidence.get("makepad_runtime_capability_receipt_pulled") is True
        ),
        "makepad_runtime_capability_receipt_status": evidence.get(
            "makepad_runtime_capability_receipt_status"
        ),
        "checks": checks + embedded,
    }


def write_makepad_shell_contract_launch_host_run_evidence(
    out: Path,
    validation: dict[str, Any],
    evidence: dict[str, Any],
    *,
    host_app_for: Callable[[str], str],
) -> None:
    contract = {
        "$schema": "rusty.hostess.host_run_evidence.v1",
        "run_id": f"host_run.makepad_shell_contract_launch.{out.stem}",
        "app_id": host_app_for("headset" if evidence.get("target") == "quest" else "mobile"),
        "package_ids": ["package.rusty_manifold.shell_contract"],
        "module_ids": ["module.hostess.makepad_shell_contract_launch"],
        "status": evidence.get("status"),
        "evidence_artifacts": [
            "artifact.makepad_shell_contract_launch_evidence",
            "artifact.makepad_shell_contract_launch_validation_report",
            "artifact.makepad_shell_runtime_capability_receipt",
            "artifact.host_run_evidence",
        ],
        "result_fields": {
            "plan_only": evidence.get("plan_only"),
            "launch_started": evidence.get("launch_started"),
            "makepad_contract_read_receipt_pulled": evidence.get(
                "makepad_contract_read_receipt_pulled"
            ),
            "makepad_runtime_capability_receipt_pulled": evidence.get(
                "makepad_runtime_capability_receipt_pulled"
            ),
            "makepad_runtime_capability_receipt_status": evidence.get(
                "makepad_runtime_capability_receipt_status"
            ),
            "makepad_runtime_missing_capabilities": evidence.get(
                "makepad_runtime_missing_capabilities"
            ),
            "final_clean_makepad_app_requires_xr": evidence.get(
                "final_clean_makepad_app_requires_xr"
            ),
            "makepad_controller_pose_required": evidence.get(
                "makepad_controller_pose_required"
            ),
            "makepad_camera_hwb_projection_required": evidence.get(
                "makepad_camera_hwb_projection_required"
            ),
            "old_makepad_provider_route_changed": evidence.get(
                "old_makepad_provider_route_changed"
            ),
            "record_values_provider_route_changed": evidence.get(
                "record_values_provider_route_changed"
            ),
        },
        "scorecard": {
            "$schema": "rusty.manifold.validation.scorecard.v1",
            "scorecard_id": "scorecard.host_run.makepad_shell_contract_launch",
            "target_id": f"host_run.makepad_shell_contract_launch.{out.stem}",
            "target_revision": 1,
            "status": validation.get("status"),
            "checks": validation.get("checks", []),
            "issues": [],
        },
    }
    out.with_name(f"{out.stem}.host-run-evidence.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True),
        encoding="utf-8",
    )
