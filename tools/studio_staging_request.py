"""Schema-only Hostess intake for Studio staging execution requests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.studio_staging.manifold_handoff_intake import (
    build_hostess_manifold_shell_handoff_review_intake_receipt,
    hostess_manifold_shell_handoff_review_intake_receipt_checks,
    hostess_manifold_shell_handoff_review_intake_receipt_no_runtime_started,
    hostess_manifold_shell_handoff_review_intake_source_ready,
    manifold_shell_handoff_endpoint_ids,
    manifold_shell_handoff_review_receipt_no_runtime_started,
    manifold_shell_handoff_stream_ids,
    manifold_shell_handoff_transport_ids,
    selected_manifold_shell_handoff_from_selection,
    validate_hostess_manifold_shell_handoff_review_intake_receipt,
)
from tools.studio_staging.makepad_shell_contract import (
    HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_SCHEMA,
    HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_VALIDATION_SCHEMA,
    HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA,
    HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_VALIDATION_SCHEMA,
    build_hostess_makepad_shell_launch_handoff_receipt,
    build_hostess_makepad_shell_contract_receipt,
    hostess_makepad_shell_launch_handoff_receipt_no_runtime_started,
    hostess_makepad_shell_launch_handoff_source_ready,
    hostess_makepad_shell_contract_intake_no_runtime_started,
    hostess_makepad_shell_contract_receipt_checks,
    hostess_makepad_shell_contract_receipt_no_runtime_started,
    hostess_makepad_shell_contract_source_ready,
    validate_hostess_makepad_shell_launch_handoff_receipt,
    validate_hostess_makepad_shell_contract_receipt,
)


from tools.studio_staging.request_shared import *  # re-exported facade symbols

from tools.studio_staging.request_intake import *  # re-exported facade symbols

from tools.studio_staging.smoke_workflow import *  # re-exported facade symbols

from tools.studio_staging.platform_smoke import *  # re-exported facade symbols

from tools.studio_staging.pmb_release import *  # re-exported facade symbols

from tools.studio_staging.staging_handoff import *  # re-exported facade symbols

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="studio-staging-request",
        description="Validate Studio staging execution requests without executing Hostess runtime actions.",
    )
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--report-out", type=Path)
    parser.add_argument("--ack-out", type=Path)
    parser.add_argument("--reject-out", type=Path)
    parser.add_argument("--smoke-handoff-in", type=Path)
    parser.add_argument("--smoke-handoff-out", type=Path)
    parser.add_argument("--smoke-dry-run-request-in", type=Path)
    parser.add_argument("--smoke-dry-run-request-out", type=Path)
    parser.add_argument("--smoke-dry-run-receipt-in", type=Path)
    parser.add_argument("--smoke-dry-run-receipt-out", type=Path)
    parser.add_argument("--smoke-preflight-in", type=Path)
    parser.add_argument("--smoke-preflight-out", type=Path)
    parser.add_argument("--smoke-host-shell-execution-in", type=Path)
    parser.add_argument("--smoke-host-shell-execution-out", type=Path)
    parser.add_argument("--smoke-review-bundle-in", type=Path)
    parser.add_argument("--smoke-review-bundle-out", type=Path)
    parser.add_argument("--platform-smoke-plan-in", type=Path)
    parser.add_argument("--platform-smoke-plan-out", type=Path)
    parser.add_argument("--platform-smoke-approval-in", type=Path)
    parser.add_argument("--platform-smoke-approval-out", type=Path)
    parser.add_argument("--platform-smoke-rejection-out", type=Path)
    parser.add_argument("--platform-smoke-execution-request-in", type=Path)
    parser.add_argument("--platform-smoke-execution-request-out", type=Path)
    parser.add_argument("--platform-smoke-execution-receipt-in", type=Path)
    parser.add_argument("--platform-smoke-execution-receipt-out", type=Path)
    parser.add_argument("--platform-smoke-operator-start-gate-in", type=Path)
    parser.add_argument("--platform-smoke-operator-start-gate-out", type=Path)
    parser.add_argument("--platform-smoke-operator-start-preflight-in", type=Path)
    parser.add_argument("--platform-smoke-operator-start-preflight-out", type=Path)
    parser.add_argument("--platform-smoke-operator-start-preflight-rejection-out", type=Path)
    parser.add_argument("--platform-smoke-execution-report-in", type=Path)
    parser.add_argument("--platform-smoke-execution-report-out", type=Path)
    parser.add_argument("--platform-smoke-execution-report-rejection-out", type=Path)
    parser.add_argument("--platform-smoke-evidence-attachment-in", type=Path)
    parser.add_argument("--platform-smoke-evidence-attachment-out", type=Path)
    parser.add_argument("--platform-smoke-evidence-attachment-rejection-out", type=Path)
    parser.add_argument("--platform-smoke-evidence-review-in", type=Path)
    parser.add_argument("--platform-smoke-evidence-review-out", type=Path)
    parser.add_argument("--platform-smoke-evidence-review-rejection-out", type=Path)
    parser.add_argument("--pmb-authoring-review-in", type=Path)
    parser.add_argument("--pmb-package-evidence-intake-in", type=Path)
    parser.add_argument("--pmb-source-adapter-selection-in", type=Path)
    parser.add_argument("--pmb-shell-handoff-review-in", type=Path)
    parser.add_argument("--require-pmb-shell-handoff-review", action="store_true")
    parser.add_argument("--pmb-validation-handoff-in", type=Path)
    parser.add_argument("--pmb-validation-handoff-out", type=Path)
    parser.add_argument("--pmb-replay-descriptors-in", type=Path)
    parser.add_argument("--pmb-replay-validation-receipt-in", type=Path)
    parser.add_argument("--pmb-replay-validation-receipt-out", type=Path)
    parser.add_argument("--operator-release-readiness-bundle-in", type=Path)
    parser.add_argument("--operator-release-readiness-bundle-out", type=Path)
    parser.add_argument("--operator-release-readiness-bundle-rejection-out", type=Path)
    parser.add_argument("--hostess-staging-file-plan-in", type=Path)
    parser.add_argument("--hostess-staging-handoff-in", type=Path)
    parser.add_argument("--hostess-staging-acceptance-manifest-in", type=Path)
    parser.add_argument("--hostess-staging-handoff-acceptance-receipt-in", type=Path)
    parser.add_argument("--hostess-staging-handoff-acceptance-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-staging-handoff-acceptance-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-staging-file-plan-receipt-in", type=Path)
    parser.add_argument("--hostess-staging-file-plan-receipt-out", type=Path)
    parser.add_argument("--hostess-staging-file-plan-receipt-rejection-out", type=Path)
    parser.add_argument("--hostess-staging-file-copy-receipt-in", type=Path)
    parser.add_argument("--hostess-staging-file-copy-receipt-out", type=Path)
    parser.add_argument("--hostess-staging-file-copy-receipt-rejection-out", type=Path)
    parser.add_argument("--hostess-staged-payload-manifest-receipt-in", type=Path)
    parser.add_argument("--hostess-staged-payload-manifest-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-staged-payload-manifest-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-downstream-shell-selection-receipt-in", type=Path)
    parser.add_argument("--hostess-downstream-shell-selection-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-downstream-shell-selection-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--manifold-shell-handoff-review-receipt-in", type=Path)
    parser.add_argument(
        "--hostess-manifold-shell-handoff-review-intake-receipt-in",
        type=Path,
    )
    parser.add_argument(
        "--hostess-manifold-shell-handoff-review-intake-receipt-out",
        type=Path,
    )
    parser.add_argument(
        "--hostess-manifold-shell-handoff-review-intake-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-makepad-shell-contract-receipt-in", type=Path)
    parser.add_argument("--hostess-makepad-shell-contract-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-makepad-shell-contract-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-makepad-shell-launch-handoff-receipt-in", type=Path)
    parser.add_argument("--hostess-makepad-shell-launch-handoff-receipt-out", type=Path)
    parser.add_argument(
        "--hostess-makepad-shell-launch-handoff-receipt-rejection-out",
        type=Path,
    )
    parser.add_argument("--hostess-downstream-shell-selection-target-kind")
    parser.add_argument("--hostess-downstream-shell-selection-graph-id")
    parser.add_argument("--hostess-downstream-shell-selection-consumer-id")
    parser.add_argument("--hostess-staging-root", default="hostess-staging")
    parser.add_argument("--target-profile", default="hostess.t.schema_smoke")
    parser.add_argument("--target-platform", default="hostess.platform_smoke.operator_controlled")
    parser.add_argument("--host-shell-kind", default="hostess.t_or_dedicated_quest_host_shell")
    parser.add_argument("--validate-ack", type=Path)
    parser.add_argument("--validate-reject", type=Path)
    parser.add_argument("--validate-smoke-handoff", type=Path)
    parser.add_argument("--validate-smoke-dry-run-request", type=Path)
    parser.add_argument("--validate-smoke-dry-run-receipt", type=Path)
    parser.add_argument("--validate-smoke-preflight", type=Path)
    parser.add_argument("--validate-smoke-host-shell-execution", type=Path)
    parser.add_argument("--validate-smoke-review-bundle", type=Path)
    parser.add_argument("--validate-platform-smoke-plan", type=Path)
    parser.add_argument("--validate-platform-smoke-approval", type=Path)
    parser.add_argument("--validate-platform-smoke-execution-request", type=Path)
    parser.add_argument("--validate-platform-smoke-execution-receipt", type=Path)
    parser.add_argument("--validate-platform-smoke-operator-start-gate", type=Path)
    parser.add_argument("--validate-platform-smoke-operator-start-preflight", type=Path)
    parser.add_argument("--validate-platform-smoke-execution-report", type=Path)
    parser.add_argument("--validate-platform-smoke-evidence-attachment", type=Path)
    parser.add_argument("--validate-platform-smoke-evidence-review", type=Path)
    parser.add_argument("--validate-pmb-validation-handoff", type=Path)
    parser.add_argument("--validate-pmb-replay-validation-receipt", type=Path)
    parser.add_argument("--validate-operator-release-readiness-bundle", type=Path)
    parser.add_argument("--validate-hostess-staging-handoff-acceptance-receipt", type=Path)
    parser.add_argument("--validate-hostess-staging-file-plan-receipt", type=Path)
    parser.add_argument("--validate-hostess-staging-file-copy-receipt", type=Path)
    parser.add_argument("--validate-hostess-staged-payload-manifest-receipt", type=Path)
    parser.add_argument("--validate-hostess-downstream-shell-selection-receipt", type=Path)
    parser.add_argument(
        "--validate-hostess-manifold-shell-handoff-review-intake-receipt",
        type=Path,
    )
    parser.add_argument("--validate-hostess-makepad-shell-contract-receipt", type=Path)
    parser.add_argument("--validate-hostess-makepad-shell-launch-handoff-receipt", type=Path)
    args = parser.parse_args()

    request = load_json(args.request)
    report = build_intake_report(request, args.request)
    ack_fixture = build_ack_fixture(request) if report["status"] == ACCEPTED_STATUS else None
    smoke_handoff = load_json(args.smoke_handoff_in) if args.smoke_handoff_in else None
    dry_run_request = load_json(args.smoke_dry_run_request_in) if args.smoke_dry_run_request_in else None
    dry_run_receipt = load_json(args.smoke_dry_run_receipt_in) if args.smoke_dry_run_receipt_in else None
    smoke_preflight = load_json(args.smoke_preflight_in) if args.smoke_preflight_in else None
    host_shell_execution = (
        load_json(args.smoke_host_shell_execution_in) if args.smoke_host_shell_execution_in else None
    )
    smoke_review_bundle = load_json(args.smoke_review_bundle_in) if args.smoke_review_bundle_in else None
    platform_smoke_plan = load_json(args.platform_smoke_plan_in) if args.platform_smoke_plan_in else None
    platform_smoke_approval = (
        load_json(args.platform_smoke_approval_in) if args.platform_smoke_approval_in else None
    )
    platform_smoke_execution_request = (
        load_json(args.platform_smoke_execution_request_in)
        if args.platform_smoke_execution_request_in
        else None
    )
    platform_smoke_execution_receipt = (
        load_json(args.platform_smoke_execution_receipt_in)
        if args.platform_smoke_execution_receipt_in
        else None
    )
    platform_smoke_operator_start_gate = (
        load_json(args.platform_smoke_operator_start_gate_in)
        if args.platform_smoke_operator_start_gate_in
        else None
    )
    platform_smoke_operator_start_preflight = (
        load_json(args.platform_smoke_operator_start_preflight_in)
        if args.platform_smoke_operator_start_preflight_in
        else None
    )
    platform_smoke_execution_report = (
        load_json(args.platform_smoke_execution_report_in)
        if args.platform_smoke_execution_report_in
        else None
    )
    platform_smoke_evidence_attachment = (
        load_json(args.platform_smoke_evidence_attachment_in)
        if args.platform_smoke_evidence_attachment_in
        else None
    )
    platform_smoke_evidence_review = (
        load_json(args.platform_smoke_evidence_review_in)
        if args.platform_smoke_evidence_review_in
        else None
    )
    pmb_authoring_review = (
        load_json(args.pmb_authoring_review_in)
        if args.pmb_authoring_review_in
        else None
    )
    pmb_package_evidence_intake = (
        load_json(args.pmb_package_evidence_intake_in)
        if args.pmb_package_evidence_intake_in
        else None
    )
    pmb_source_adapter_selection = (
        load_json(args.pmb_source_adapter_selection_in)
        if args.pmb_source_adapter_selection_in
        else None
    )
    request_pmb_shell_handoff_review_path = request_relative_path(
        args.request,
        request.get("pmb_shell_handoff_review_path"),
    )
    pmb_shell_handoff_review_path = (
        args.pmb_shell_handoff_review_in
        if args.pmb_shell_handoff_review_in
        else request_pmb_shell_handoff_review_path
    )
    pmb_shell_handoff_review_required = (
        args.require_pmb_shell_handoff_review
        or request.get("pmb_shell_handoff_review_required") is True
    )
    pmb_shell_handoff_review = (
        load_json(pmb_shell_handoff_review_path)
        if pmb_shell_handoff_review_path
        else None
    )
    pmb_validation_handoff = (
        load_json(args.pmb_validation_handoff_in)
        if args.pmb_validation_handoff_in
        else None
    )
    pmb_replay_descriptors = (
        load_json(args.pmb_replay_descriptors_in)
        if args.pmb_replay_descriptors_in
        else None
    )
    pmb_replay_validation_receipt = (
        load_json(args.pmb_replay_validation_receipt_in)
        if args.pmb_replay_validation_receipt_in
        else None
    )
    operator_release_readiness_bundle = (
        load_json(args.operator_release_readiness_bundle_in)
        if args.operator_release_readiness_bundle_in
        else None
    )
    request_staging_handoff_path = request_relative_path(
        args.request,
        request.get("handoff_path"),
    )
    request_staging_file_plan_path = request_relative_path(
        args.request,
        request.get("file_plan_path"),
    )
    request_staging_acceptance_manifest_path = request_relative_path(
        args.request,
        request.get("acceptance_manifest_path"),
    )
    staging_file_plan_path = (
        args.hostess_staging_file_plan_in
        if args.hostess_staging_file_plan_in
        else request_staging_file_plan_path
    )
    staging_handoff_path = (
        args.hostess_staging_handoff_in
        if args.hostess_staging_handoff_in
        else request_staging_handoff_path
    )
    staging_acceptance_manifest_path = (
        args.hostess_staging_acceptance_manifest_in
        if args.hostess_staging_acceptance_manifest_in
        else request_staging_acceptance_manifest_path
    )
    staging_file_plan = (
        load_json(staging_file_plan_path) if staging_file_plan_path else None
    )
    staging_handoff = load_json(staging_handoff_path) if staging_handoff_path else None
    staging_acceptance_manifest = (
        load_json(staging_acceptance_manifest_path)
        if staging_acceptance_manifest_path
        else None
    )
    staging_handoff_acceptance_receipt = (
        load_json(args.hostess_staging_handoff_acceptance_receipt_in)
        if args.hostess_staging_handoff_acceptance_receipt_in
        else None
    )
    staging_file_plan_receipt = (
        load_json(args.hostess_staging_file_plan_receipt_in)
        if args.hostess_staging_file_plan_receipt_in
        else None
    )
    staging_file_copy_receipt = (
        load_json(args.hostess_staging_file_copy_receipt_in)
        if args.hostess_staging_file_copy_receipt_in
        else None
    )
    staged_payload_manifest_receipt = (
        load_json(args.hostess_staged_payload_manifest_receipt_in)
        if args.hostess_staged_payload_manifest_receipt_in
        else None
    )
    downstream_shell_selection_receipt = (
        load_json(args.hostess_downstream_shell_selection_receipt_in)
        if args.hostess_downstream_shell_selection_receipt_in
        else None
    )
    manifold_shell_handoff_review_receipt = (
        load_json(args.manifold_shell_handoff_review_receipt_in)
        if args.manifold_shell_handoff_review_receipt_in
        else None
    )
    manifold_shell_handoff_review_intake_receipt = (
        load_json(args.hostess_manifold_shell_handoff_review_intake_receipt_in)
        if args.hostess_manifold_shell_handoff_review_intake_receipt_in
        else None
    )
    makepad_shell_contract_receipt = (
        load_json(args.hostess_makepad_shell_contract_receipt_in)
        if args.hostess_makepad_shell_contract_receipt_in
        else None
    )
    makepad_shell_launch_handoff_receipt = (
        load_json(args.hostess_makepad_shell_launch_handoff_receipt_in)
        if args.hostess_makepad_shell_launch_handoff_receipt_in
        else None
    )
    if args.report_out:
        write_json(args.report_out, report)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    if args.ack_out and ack_fixture is not None:
        write_json(args.ack_out, ack_fixture)
    if args.reject_out:
        write_json(args.reject_out, build_reject_fixture(request))
    if args.pmb_validation_handoff_out:
        if pmb_validation_handoff is None:
            if pmb_authoring_review is None:
                raise ValueError(
                    "--pmb-authoring-review-in is required when building a PMB validation handoff"
                )
            pmb_validation_handoff = build_projected_motion_breath_validation_handoff(
                pmb_authoring_review,
                pmb_package_evidence_intake,
                args.pmb_authoring_review_in,
                args.pmb_package_evidence_intake_in,
                pmb_source_adapter_selection,
                args.pmb_source_adapter_selection_in,
            )
        write_json(args.pmb_validation_handoff_out, pmb_validation_handoff)
    if args.pmb_replay_validation_receipt_out:
        if pmb_replay_validation_receipt is None:
            if pmb_validation_handoff is None:
                if pmb_authoring_review is None:
                    raise ValueError(
                        "--pmb-validation-handoff-in or --pmb-authoring-review-in "
                        "is required when building a PMB replay validation receipt"
                    )
                pmb_validation_handoff = build_projected_motion_breath_validation_handoff(
                    pmb_authoring_review,
                    pmb_package_evidence_intake,
                    args.pmb_authoring_review_in,
                    args.pmb_package_evidence_intake_in,
                    pmb_source_adapter_selection,
                    args.pmb_source_adapter_selection_in,
                )
            pmb_replay_validation_receipt = (
                build_projected_motion_breath_replay_validation_receipt(
                    pmb_validation_handoff,
                    pmb_replay_descriptors,
                    args.pmb_replay_descriptors_in,
                )
            )
        write_json(args.pmb_replay_validation_receipt_out, pmb_replay_validation_receipt)
    if args.smoke_handoff_out:
        if smoke_handoff is None:
            smoke_handoff = build_smoke_handoff_checklist(
                request,
                report,
                ack_fixture,
                target_profile=args.target_profile,
            )
        write_json(
            args.smoke_handoff_out,
            smoke_handoff,
        )
    if (
        args.smoke_dry_run_request_out
        or args.smoke_dry_run_receipt_out
        or args.smoke_preflight_out
        or args.smoke_host_shell_execution_out
        or args.smoke_review_bundle_out
        or args.platform_smoke_plan_out
        or args.platform_smoke_approval_out
        or args.platform_smoke_rejection_out
        or args.platform_smoke_execution_request_out
        or args.platform_smoke_execution_receipt_out
        or args.platform_smoke_operator_start_gate_out
        or args.platform_smoke_operator_start_preflight_out
        or args.platform_smoke_operator_start_preflight_rejection_out
        or args.platform_smoke_execution_report_out
        or args.platform_smoke_execution_report_rejection_out
        or args.platform_smoke_evidence_attachment_out
        or args.platform_smoke_evidence_attachment_rejection_out
        or args.platform_smoke_evidence_review_out
        or args.platform_smoke_evidence_review_rejection_out
        or args.operator_release_readiness_bundle_out
        or args.operator_release_readiness_bundle_rejection_out
        or args.hostess_staging_handoff_acceptance_receipt_out
        or args.hostess_staging_handoff_acceptance_receipt_rejection_out
        or args.hostess_staging_file_plan_receipt_out
        or args.hostess_staging_file_plan_receipt_rejection_out
        or args.hostess_staging_file_copy_receipt_out
        or args.hostess_staging_file_copy_receipt_rejection_out
        or args.hostess_staged_payload_manifest_receipt_out
        or args.hostess_staged_payload_manifest_receipt_rejection_out
        or args.hostess_staged_payload_manifest_receipt_out
        or args.hostess_staged_payload_manifest_receipt_rejection_out
    ):
        if smoke_handoff is None:
            smoke_handoff = build_smoke_handoff_checklist(
                request,
                report,
                ack_fixture,
                target_profile=args.target_profile,
            )
        if dry_run_request is None:
            dry_run_request = build_smoke_dry_run_request(
                smoke_handoff,
                target_profile=args.target_profile,
            )
        if args.smoke_dry_run_request_out:
            write_json(args.smoke_dry_run_request_out, dry_run_request)
        if args.smoke_dry_run_receipt_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            write_json(args.smoke_dry_run_receipt_out, dry_run_receipt)
        if args.smoke_preflight_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            write_json(
                args.smoke_preflight_out,
                smoke_preflight,
            )
        if args.smoke_host_shell_execution_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            write_json(
                args.smoke_host_shell_execution_out,
                host_shell_execution,
            )
        if args.smoke_review_bundle_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            write_json(
                args.smoke_review_bundle_out,
                smoke_review_bundle,
            )
        if args.platform_smoke_plan_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            write_json(
                args.platform_smoke_plan_out,
                platform_smoke_plan,
            )
        if args.platform_smoke_approval_out or args.platform_smoke_rejection_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if args.platform_smoke_approval_out:
                if platform_smoke_approval is None:
                    platform_smoke_approval = build_platform_smoke_approval_receipt(
                        platform_smoke_plan,
                        decision=APPROVED_STATUS,
                    )
                write_json(
                    args.platform_smoke_approval_out,
                    platform_smoke_approval,
                )
            if args.platform_smoke_rejection_out:
                write_json(
                    args.platform_smoke_rejection_out,
                    build_platform_smoke_approval_receipt(
                        platform_smoke_plan,
                        decision=REJECTED_STATUS,
                        reason_code="hostess.issue.operator_rejected_platform_smoke_plan",
                    ),
                )
        if args.platform_smoke_execution_request_out or args.platform_smoke_execution_receipt_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if platform_smoke_approval is None:
                platform_smoke_approval = build_platform_smoke_approval_receipt(
                    platform_smoke_plan,
                    decision=APPROVED_STATUS,
                )
            if platform_smoke_execution_request is None:
                platform_smoke_execution_request = build_platform_smoke_execution_request(
                    platform_smoke_plan,
                    platform_smoke_approval,
                )
            if args.platform_smoke_execution_request_out:
                write_json(
                    args.platform_smoke_execution_request_out,
                    platform_smoke_execution_request,
                )
            if args.platform_smoke_execution_receipt_out:
                if platform_smoke_execution_receipt is None:
                    platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                        platform_smoke_plan,
                        platform_smoke_approval,
                        platform_smoke_execution_request,
                    )
                write_json(
                    args.platform_smoke_execution_receipt_out,
                    platform_smoke_execution_receipt,
                )
        if args.platform_smoke_operator_start_gate_out:
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if platform_smoke_approval is None:
                platform_smoke_approval = build_platform_smoke_approval_receipt(
                    platform_smoke_plan,
                    decision=APPROVED_STATUS,
                )
            if platform_smoke_execution_request is None:
                platform_smoke_execution_request = build_platform_smoke_execution_request(
                    platform_smoke_plan,
                    platform_smoke_approval,
                )
            if platform_smoke_execution_receipt is None:
                platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                )
            if platform_smoke_operator_start_gate is None:
                platform_smoke_operator_start_gate = build_platform_smoke_operator_start_gate(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    host_shell_kind=args.host_shell_kind,
                )
            write_json(
                args.platform_smoke_operator_start_gate_out,
                platform_smoke_operator_start_gate,
            )
        if (
            args.platform_smoke_operator_start_preflight_out
            or args.platform_smoke_operator_start_preflight_rejection_out
            or args.platform_smoke_execution_report_out
            or args.platform_smoke_execution_report_rejection_out
            or args.platform_smoke_evidence_attachment_out
            or args.platform_smoke_evidence_attachment_rejection_out
            or args.platform_smoke_evidence_review_out
            or args.platform_smoke_evidence_review_rejection_out
            or args.operator_release_readiness_bundle_out
            or args.operator_release_readiness_bundle_rejection_out
        ):
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            if platform_smoke_plan is None:
                platform_smoke_plan = build_platform_smoke_plan(
                    smoke_review_bundle,
                    target_platform=args.target_platform,
                )
            if platform_smoke_approval is None:
                platform_smoke_approval = build_platform_smoke_approval_receipt(
                    platform_smoke_plan,
                    decision=APPROVED_STATUS,
                )
            if platform_smoke_execution_request is None:
                platform_smoke_execution_request = build_platform_smoke_execution_request(
                    platform_smoke_plan,
                    platform_smoke_approval,
                )
            if platform_smoke_execution_receipt is None:
                platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                )
            if platform_smoke_operator_start_gate is None:
                platform_smoke_operator_start_gate = build_platform_smoke_operator_start_gate(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    host_shell_kind=args.host_shell_kind,
                )
            if args.platform_smoke_operator_start_preflight_out:
                if platform_smoke_operator_start_preflight is None:
                    platform_smoke_operator_start_preflight = (
                        build_platform_smoke_operator_start_preflight_receipt(
                            platform_smoke_plan,
                            platform_smoke_approval,
                            platform_smoke_execution_request,
                            platform_smoke_execution_receipt,
                            platform_smoke_operator_start_gate,
                            decision=APPROVED_STATUS,
                            pmb_shell_handoff_review=pmb_shell_handoff_review,
                            pmb_shell_handoff_review_path=pmb_shell_handoff_review_path,
                            require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
                        )
                    )
                write_json(
                    args.platform_smoke_operator_start_preflight_out,
                    platform_smoke_operator_start_preflight,
                )
            if args.platform_smoke_operator_start_preflight_rejection_out:
                write_json(
                    args.platform_smoke_operator_start_preflight_rejection_out,
                    build_platform_smoke_operator_start_preflight_receipt(
                        platform_smoke_plan,
                        platform_smoke_approval,
                        platform_smoke_execution_request,
                        platform_smoke_execution_receipt,
                        platform_smoke_operator_start_gate,
                        decision=REJECTED_STATUS,
                        reason_code="hostess.issue.operator_rejected_platform_smoke_operator_start_preflight",
                        pmb_shell_handoff_review=pmb_shell_handoff_review,
                        pmb_shell_handoff_review_path=pmb_shell_handoff_review_path,
                        require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
                    ),
                )
            if (
                args.platform_smoke_execution_report_out
                or args.platform_smoke_execution_report_rejection_out
                or args.platform_smoke_evidence_attachment_out
                or args.platform_smoke_evidence_attachment_rejection_out
                or args.platform_smoke_evidence_review_out
                or args.platform_smoke_evidence_review_rejection_out
                or args.operator_release_readiness_bundle_out
                or args.operator_release_readiness_bundle_rejection_out
            ):
                if platform_smoke_operator_start_preflight is None:
                    platform_smoke_operator_start_preflight = (
                        build_platform_smoke_operator_start_preflight_receipt(
                            platform_smoke_plan,
                            platform_smoke_approval,
                            platform_smoke_execution_request,
                            platform_smoke_execution_receipt,
                            platform_smoke_operator_start_gate,
                            decision=APPROVED_STATUS,
                            pmb_shell_handoff_review=pmb_shell_handoff_review,
                            pmb_shell_handoff_review_path=pmb_shell_handoff_review_path,
                            require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
                        )
                    )
                if args.platform_smoke_execution_report_out:
                    if platform_smoke_execution_report is None:
                        platform_smoke_execution_report = (
                            build_platform_smoke_execution_report(
                                platform_smoke_plan,
                                platform_smoke_approval,
                                platform_smoke_execution_request,
                                platform_smoke_execution_receipt,
                                platform_smoke_operator_start_gate,
                                platform_smoke_operator_start_preflight,
                            )
                        )
                    write_json(
                        args.platform_smoke_execution_report_out,
                        platform_smoke_execution_report,
                    )
                if args.platform_smoke_execution_report_rejection_out:
                    write_json(
                        args.platform_smoke_execution_report_rejection_out,
                        build_platform_smoke_execution_report(
                            platform_smoke_plan,
                            platform_smoke_approval,
                            platform_smoke_execution_request,
                            platform_smoke_execution_receipt,
                            platform_smoke_operator_start_gate,
                            platform_smoke_operator_start_preflight,
                            outcome=REJECTED_STATUS,
                            reason_code="hostess.issue.operator_rejected_platform_smoke_execution_report",
                        ),
                    )
                if (
                    args.platform_smoke_evidence_attachment_out
                    or args.platform_smoke_evidence_attachment_rejection_out
                    or args.platform_smoke_evidence_review_out
                    or args.platform_smoke_evidence_review_rejection_out
                    or args.operator_release_readiness_bundle_out
                    or args.operator_release_readiness_bundle_rejection_out
                ):
                    if platform_smoke_execution_report is None:
                        platform_smoke_execution_report = (
                            build_platform_smoke_execution_report(
                                platform_smoke_plan,
                                platform_smoke_approval,
                                platform_smoke_execution_request,
                                platform_smoke_execution_receipt,
                                platform_smoke_operator_start_gate,
                                platform_smoke_operator_start_preflight,
                            )
                        )
                    if args.platform_smoke_evidence_attachment_out:
                        if platform_smoke_evidence_attachment is None:
                            platform_smoke_evidence_attachment = (
                                build_platform_smoke_evidence_attachment_receipt(
                                    platform_smoke_plan,
                                    platform_smoke_approval,
                                    platform_smoke_execution_request,
                                    platform_smoke_execution_receipt,
                                    platform_smoke_operator_start_gate,
                                    platform_smoke_operator_start_preflight,
                                    platform_smoke_execution_report,
                                )
                            )
                        write_json(
                            args.platform_smoke_evidence_attachment_out,
                            platform_smoke_evidence_attachment,
                        )
                    if args.platform_smoke_evidence_attachment_rejection_out:
                        write_json(
                            args.platform_smoke_evidence_attachment_rejection_out,
                            build_platform_smoke_evidence_attachment_receipt(
                                platform_smoke_plan,
                                platform_smoke_approval,
                                platform_smoke_execution_request,
                                platform_smoke_execution_receipt,
                                platform_smoke_operator_start_gate,
                                platform_smoke_operator_start_preflight,
                                platform_smoke_execution_report,
                                decision=REJECTED_STATUS,
                                reason_code="hostess.issue.operator_rejected_platform_smoke_evidence_attachment",
                            ),
                        )
                    if (
                        args.platform_smoke_evidence_review_out
                        or args.platform_smoke_evidence_review_rejection_out
                        or args.operator_release_readiness_bundle_out
                        or args.operator_release_readiness_bundle_rejection_out
                    ):
                        if platform_smoke_evidence_attachment is None:
                            platform_smoke_evidence_attachment = (
                                build_platform_smoke_evidence_attachment_receipt(
                                    platform_smoke_plan,
                                    platform_smoke_approval,
                                    platform_smoke_execution_request,
                                    platform_smoke_execution_receipt,
                                    platform_smoke_operator_start_gate,
                                    platform_smoke_operator_start_preflight,
                                    platform_smoke_execution_report,
                                )
                            )
                        if args.platform_smoke_evidence_review_out:
                            if platform_smoke_evidence_review is None:
                                platform_smoke_evidence_review = (
                                    build_platform_smoke_evidence_review(
                                        platform_smoke_plan,
                                        platform_smoke_approval,
                                        platform_smoke_execution_request,
                                        platform_smoke_execution_receipt,
                                        platform_smoke_operator_start_gate,
                                        platform_smoke_operator_start_preflight,
                                        platform_smoke_execution_report,
                                        platform_smoke_evidence_attachment,
                                    )
                                )
                            write_json(
                                args.platform_smoke_evidence_review_out,
                                platform_smoke_evidence_review,
                            )
                        if args.platform_smoke_evidence_review_rejection_out:
                            write_json(
                                args.platform_smoke_evidence_review_rejection_out,
                                build_platform_smoke_evidence_review(
                                    platform_smoke_plan,
                                    platform_smoke_approval,
                                    platform_smoke_execution_request,
                                    platform_smoke_execution_receipt,
                                    platform_smoke_operator_start_gate,
                                    platform_smoke_operator_start_preflight,
                                    platform_smoke_execution_report,
                                    platform_smoke_evidence_attachment,
                                    decision=REJECTED_STATUS,
                                    reason_code="hostess.issue.operator_rejected_platform_smoke_evidence_review",
                                ),
                            )
                        if (
                            args.operator_release_readiness_bundle_out
                            or args.operator_release_readiness_bundle_rejection_out
                            or args.hostess_staging_handoff_acceptance_receipt_out
                            or args.hostess_staging_handoff_acceptance_receipt_rejection_out
                            or args.hostess_staging_file_plan_receipt_out
                            or args.hostess_staging_file_plan_receipt_rejection_out
                            or args.hostess_staging_file_copy_receipt_out
                            or args.hostess_staging_file_copy_receipt_rejection_out
                            or args.hostess_staged_payload_manifest_receipt_out
                            or args.hostess_staged_payload_manifest_receipt_rejection_out
                        ):
                            if platform_smoke_evidence_review is None:
                                platform_smoke_evidence_review = (
                                    build_platform_smoke_evidence_review(
                                        platform_smoke_plan,
                                        platform_smoke_approval,
                                        platform_smoke_execution_request,
                                        platform_smoke_execution_receipt,
                                        platform_smoke_operator_start_gate,
                                        platform_smoke_operator_start_preflight,
                                        platform_smoke_execution_report,
                                        platform_smoke_evidence_attachment,
                                    )
                                )
                            if pmb_replay_validation_receipt is None:
                                if pmb_validation_handoff is None:
                                    if pmb_authoring_review is None:
                                        raise ValueError(
                                            "--pmb-replay-validation-receipt-in or "
                                            "--pmb-authoring-review-in is required when "
                                            "building an operator release readiness bundle"
                                        )
                                    pmb_validation_handoff = (
                                        build_projected_motion_breath_validation_handoff(
                                            pmb_authoring_review,
                                            pmb_package_evidence_intake,
                                            args.pmb_authoring_review_in,
                                            args.pmb_package_evidence_intake_in,
                                            pmb_source_adapter_selection,
                                            args.pmb_source_adapter_selection_in,
                                        )
                                    )
                                pmb_replay_validation_receipt = (
                                    build_projected_motion_breath_replay_validation_receipt(
                                        pmb_validation_handoff,
                                        pmb_replay_descriptors,
                                        args.pmb_replay_descriptors_in,
                                    )
                                )
                            if args.operator_release_readiness_bundle_out:
                                if operator_release_readiness_bundle is None:
                                    operator_release_readiness_bundle = (
                                        build_operator_release_readiness_bundle(
                                            platform_smoke_evidence_review,
                                            pmb_replay_validation_receipt,
                                        )
                                    )
                                write_json(
                                    args.operator_release_readiness_bundle_out,
                                    operator_release_readiness_bundle,
                                )
                            if args.operator_release_readiness_bundle_rejection_out:
                                write_json(
                                    args.operator_release_readiness_bundle_rejection_out,
                                    build_operator_release_readiness_bundle(
                                        platform_smoke_evidence_review,
                                        pmb_replay_validation_receipt,
                                        decision=REJECTED_STATUS,
                                        reason_code=(
                                            "hostess.issue.operator_rejected_operator_release_readiness_bundle"
                                        ),
                                    ),
                                )
                            if (
                                args.hostess_staging_handoff_acceptance_receipt_out
                                or args.hostess_staging_handoff_acceptance_receipt_rejection_out
                                or args.hostess_staging_file_plan_receipt_out
                                or args.hostess_staging_file_plan_receipt_rejection_out
                                or args.hostess_staging_file_copy_receipt_out
                                or args.hostess_staging_file_copy_receipt_rejection_out
                                or args.hostess_staged_payload_manifest_receipt_out
                                or args.hostess_staged_payload_manifest_receipt_rejection_out
                            ):
                                if operator_release_readiness_bundle is None:
                                    operator_release_readiness_bundle = (
                                        build_operator_release_readiness_bundle(
                                            platform_smoke_evidence_review,
                                            pmb_replay_validation_receipt,
                                        )
                                    )
                                if staging_handoff is None:
                                    raise ValueError(
                                        "--hostess-staging-handoff-in or request handoff_path "
                                        "is required when accepting a Hostess staging handoff"
                                    )
                                if staging_acceptance_manifest is None:
                                    raise ValueError(
                                        "--hostess-staging-acceptance-manifest-in or request "
                                        "acceptance_manifest_path is required when accepting a "
                                        "Hostess staging handoff"
                                    )
                                if args.hostess_staging_handoff_acceptance_receipt_out:
                                    if staging_handoff_acceptance_receipt is None:
                                        staging_handoff_acceptance_receipt = (
                                            build_hostess_staging_handoff_acceptance_receipt(
                                                operator_release_readiness_bundle,
                                                staging_handoff,
                                                staging_acceptance_manifest,
                                            )
                                        )
                                    write_json(
                                        args.hostess_staging_handoff_acceptance_receipt_out,
                                        staging_handoff_acceptance_receipt,
                                    )
                                if (
                                    args.hostess_staging_handoff_acceptance_receipt_rejection_out
                                ):
                                    write_json(
                                        args.hostess_staging_handoff_acceptance_receipt_rejection_out,
                                        build_hostess_staging_handoff_acceptance_receipt(
                                            operator_release_readiness_bundle,
                                            staging_handoff,
                                            staging_acceptance_manifest,
                                            decision=REJECTED_STATUS,
                                            reason_code=(
                                                "hostess.issue.operator_rejected_hostess_staging_handoff_acceptance"
                                            ),
                                        ),
                                    )
                                if (
                                    args.hostess_staging_file_plan_receipt_out
                                    or args.hostess_staging_file_plan_receipt_rejection_out
                                    or args.hostess_staging_file_copy_receipt_out
                                    or args.hostess_staging_file_copy_receipt_rejection_out
                                    or args.hostess_staged_payload_manifest_receipt_out
                                    or args.hostess_staged_payload_manifest_receipt_rejection_out
                                ):
                                    if staging_file_plan is None:
                                        raise ValueError(
                                            "--hostess-staging-file-plan-in or request file_plan_path "
                                            "is required when building a Hostess staging file plan receipt"
                                        )
                                    if staging_handoff_acceptance_receipt is None:
                                        staging_handoff_acceptance_receipt = (
                                            build_hostess_staging_handoff_acceptance_receipt(
                                                operator_release_readiness_bundle,
                                                staging_handoff,
                                                staging_acceptance_manifest,
                                            )
                                        )
                                    if args.hostess_staging_file_plan_receipt_out:
                                        if staging_file_plan_receipt is None:
                                            staging_file_plan_receipt = (
                                                build_hostess_staging_file_plan_receipt(
                                                    staging_handoff_acceptance_receipt,
                                                    staging_file_plan,
                                                    staging_root=args.hostess_staging_root,
                                                    source_file_plan_path=staging_file_plan_path,
                                                )
                                            )
                                        write_json(
                                            args.hostess_staging_file_plan_receipt_out,
                                            staging_file_plan_receipt,
                                        )
                                    if args.hostess_staging_file_plan_receipt_rejection_out:
                                        write_json(
                                            args.hostess_staging_file_plan_receipt_rejection_out,
                                            build_hostess_staging_file_plan_receipt(
                                                staging_handoff_acceptance_receipt,
                                                staging_file_plan,
                                                staging_root=args.hostess_staging_root,
                                                source_file_plan_path=staging_file_plan_path,
                                                decision=REJECTED_STATUS,
                                                reason_code=(
                                                    "hostess.issue.operator_rejected_hostess_staging_file_plan"
                                                ),
                                            ),
                                        )
                                    if (
                                        args.hostess_staging_file_copy_receipt_out
                                        or args.hostess_staging_file_copy_receipt_rejection_out
                                        or args.hostess_staged_payload_manifest_receipt_out
                                        or args.hostess_staged_payload_manifest_receipt_rejection_out
                                    ):
                                        if staging_file_plan_receipt is None:
                                            staging_file_plan_receipt = (
                                                build_hostess_staging_file_plan_receipt(
                                                    staging_handoff_acceptance_receipt,
                                                    staging_file_plan,
                                                    staging_root=args.hostess_staging_root,
                                                    source_file_plan_path=staging_file_plan_path,
                                                )
                                            )
                                        if args.hostess_staging_file_copy_receipt_out:
                                            if staging_file_copy_receipt is None:
                                                staging_file_copy_receipt = (
                                                    build_hostess_staging_file_copy_receipt(
                                                        staging_file_plan_receipt,
                                                        staging_file_plan,
                                                    )
                                                )
                                            write_json(
                                                args.hostess_staging_file_copy_receipt_out,
                                                staging_file_copy_receipt,
                                            )
                                        if args.hostess_staging_file_copy_receipt_rejection_out:
                                            write_json(
                                                args.hostess_staging_file_copy_receipt_rejection_out,
                                                build_hostess_staging_file_copy_receipt(
                                                    staging_file_plan_receipt,
                                                    staging_file_plan,
                                                    decision=REJECTED_STATUS,
                                                    reason_code=(
                                                        "hostess.issue.operator_rejected_hostess_staging_file_copy"
                                                    ),
                                                ),
                                            )
                                        if (
                                            args.hostess_staged_payload_manifest_receipt_out
                                            or args.hostess_staged_payload_manifest_receipt_rejection_out
                                        ):
                                            if staging_file_copy_receipt is None:
                                                staging_file_copy_receipt = (
                                                    build_hostess_staging_file_copy_receipt(
                                                        staging_file_plan_receipt,
                                                        staging_file_plan,
                                                    )
                                                )
                                            if args.hostess_staged_payload_manifest_receipt_out:
                                                if staged_payload_manifest_receipt is None:
                                                    staged_payload_manifest_receipt = (
                                                        build_hostess_staged_payload_manifest_receipt(
                                                            staging_file_copy_receipt,
                                                        )
                                                    )
                                                write_json(
                                                    args.hostess_staged_payload_manifest_receipt_out,
                                                    staged_payload_manifest_receipt,
                                                )
                                            if args.hostess_staged_payload_manifest_receipt_rejection_out:
                                                write_json(
                                                    args.hostess_staged_payload_manifest_receipt_rejection_out,
                                                    build_hostess_staged_payload_manifest_receipt(
                                                        staging_file_copy_receipt,
                                                        decision=REJECTED_STATUS,
                                                        reason_code=(
                                                            "hostess.issue.operator_rejected_hostess_staged_payload_manifest"
                                                        ),
                                                    ),
                                                )
    if (
        args.hostess_staging_handoff_acceptance_receipt_out
        or args.hostess_staging_handoff_acceptance_receipt_rejection_out
        or args.hostess_staging_file_plan_receipt_out
        or args.hostess_staging_file_plan_receipt_rejection_out
        or args.hostess_staging_file_copy_receipt_out
        or args.hostess_staging_file_copy_receipt_rejection_out
        or args.hostess_staged_payload_manifest_receipt_out
        or args.hostess_staged_payload_manifest_receipt_rejection_out
    ):
        if operator_release_readiness_bundle is None:
            if (
                staging_handoff_acceptance_receipt is None
                and staging_file_plan_receipt is None
                and staging_file_copy_receipt is None
            ):
                raise ValueError(
                    "--operator-release-readiness-bundle-in, "
                    "--operator-release-readiness-bundle-out, or "
                    "--hostess-staging-handoff-acceptance-receipt-in is required "
                    "when building Hostess staging receipts"
                )
        if staging_handoff is None:
            if (
                staging_handoff_acceptance_receipt is None
                and staging_file_plan_receipt is None
                and staging_file_copy_receipt is None
            ):
                raise ValueError(
                    "--hostess-staging-handoff-in or request handoff_path is required "
                    "when accepting a Hostess staging handoff"
                )
        if staging_acceptance_manifest is None:
            if (
                staging_handoff_acceptance_receipt is None
                and staging_file_plan_receipt is None
                and staging_file_copy_receipt is None
            ):
                raise ValueError(
                    "--hostess-staging-acceptance-manifest-in or request "
                    "acceptance_manifest_path is required when accepting a Hostess "
                    "staging handoff"
                )
        if args.hostess_staging_handoff_acceptance_receipt_out:
            if staging_handoff_acceptance_receipt is None:
                staging_handoff_acceptance_receipt = (
                    build_hostess_staging_handoff_acceptance_receipt(
                        operator_release_readiness_bundle,
                        staging_handoff,
                        staging_acceptance_manifest,
                    )
                )
            write_json(
                args.hostess_staging_handoff_acceptance_receipt_out,
                staging_handoff_acceptance_receipt,
            )
        if args.hostess_staging_handoff_acceptance_receipt_rejection_out:
            write_json(
                args.hostess_staging_handoff_acceptance_receipt_rejection_out,
                build_hostess_staging_handoff_acceptance_receipt(
                    operator_release_readiness_bundle,
                    staging_handoff,
                    staging_acceptance_manifest,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_staging_handoff_acceptance"
                    ),
                ),
            )
        if (
            args.hostess_staging_file_plan_receipt_out
            or args.hostess_staging_file_plan_receipt_rejection_out
            or args.hostess_staging_file_copy_receipt_out
            or args.hostess_staging_file_copy_receipt_rejection_out
        ):
            if staging_file_plan is None:
                raise ValueError(
                    "--hostess-staging-file-plan-in or request file_plan_path is required "
                    "when building a Hostess staging file plan receipt"
                )
            if (
                staging_handoff_acceptance_receipt is None
                and staging_file_plan_receipt is None
            ):
                if operator_release_readiness_bundle is None:
                    raise ValueError(
                        "--hostess-staging-handoff-acceptance-receipt-in or "
                        "operator release and handoff inputs are required when "
                        "building a Hostess staging file plan receipt"
                    )
                staging_handoff_acceptance_receipt = (
                    build_hostess_staging_handoff_acceptance_receipt(
                        operator_release_readiness_bundle,
                        staging_handoff,
                        staging_acceptance_manifest,
                    )
                )
            if args.hostess_staging_file_plan_receipt_out:
                if staging_file_plan_receipt is None:
                    staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                    )
                write_json(
                    args.hostess_staging_file_plan_receipt_out,
                    staging_file_plan_receipt,
                )
            if args.hostess_staging_file_plan_receipt_rejection_out:
                write_json(
                    args.hostess_staging_file_plan_receipt_rejection_out,
                    build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                        decision=REJECTED_STATUS,
                        reason_code=(
                            "hostess.issue.operator_rejected_hostess_staging_file_plan"
                        ),
                    ),
                )
            if (
                args.hostess_staging_file_copy_receipt_out
                or args.hostess_staging_file_copy_receipt_rejection_out
            ):
                if staging_file_plan_receipt is None:
                    staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                    )
                if args.hostess_staging_file_copy_receipt_out:
                    if staging_file_copy_receipt is None:
                        staging_file_copy_receipt = (
                            build_hostess_staging_file_copy_receipt(
                                staging_file_plan_receipt,
                                staging_file_plan,
                            )
                        )
                    write_json(
                        args.hostess_staging_file_copy_receipt_out,
                        staging_file_copy_receipt,
                    )
                if args.hostess_staging_file_copy_receipt_rejection_out:
                    write_json(
                        args.hostess_staging_file_copy_receipt_rejection_out,
                        build_hostess_staging_file_copy_receipt(
                            staging_file_plan_receipt,
                            staging_file_plan,
                            decision=REJECTED_STATUS,
                            reason_code=(
                                "hostess.issue.operator_rejected_hostess_staging_file_copy"
                            ),
                        ),
                    )
                if (
                    args.hostess_staged_payload_manifest_receipt_out
                    or args.hostess_staged_payload_manifest_receipt_rejection_out
                ):
                    if staging_file_copy_receipt is None:
                        staging_file_copy_receipt = (
                            build_hostess_staging_file_copy_receipt(
                                staging_file_plan_receipt,
                                staging_file_plan,
                            )
                        )
                    if args.hostess_staged_payload_manifest_receipt_out:
                        if staged_payload_manifest_receipt is None:
                            staged_payload_manifest_receipt = (
                                build_hostess_staged_payload_manifest_receipt(
                                    staging_file_copy_receipt,
                                )
                            )
                        write_json(
                            args.hostess_staged_payload_manifest_receipt_out,
                            staged_payload_manifest_receipt,
                        )
                    if args.hostess_staged_payload_manifest_receipt_rejection_out:
                        write_json(
                            args.hostess_staged_payload_manifest_receipt_rejection_out,
                            build_hostess_staged_payload_manifest_receipt(
                                staging_file_copy_receipt,
                                decision=REJECTED_STATUS,
                                reason_code=(
                                    "hostess.issue.operator_rejected_hostess_staged_payload_manifest"
                            ),
                        ),
                    )
        if (
            args.hostess_staged_payload_manifest_receipt_out
            or args.hostess_staged_payload_manifest_receipt_rejection_out
        ):
            if staging_file_copy_receipt is None:
                if staging_file_plan is None:
                    raise ValueError(
                        "--hostess-staging-file-copy-receipt-in or "
                        "--hostess-staging-file-plan-in is required when building "
                        "a Hostess staged payload manifest receipt"
                    )
                if staging_file_plan_receipt is None:
                    staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                    )
                staging_file_copy_receipt = build_hostess_staging_file_copy_receipt(
                    staging_file_plan_receipt,
                    staging_file_plan,
                )
            if args.hostess_staged_payload_manifest_receipt_out:
                if staged_payload_manifest_receipt is None:
                    staged_payload_manifest_receipt = (
                        build_hostess_staged_payload_manifest_receipt(
                            staging_file_copy_receipt,
                        )
                    )
                write_json(
                    args.hostess_staged_payload_manifest_receipt_out,
                    staged_payload_manifest_receipt,
                )
            if args.hostess_staged_payload_manifest_receipt_rejection_out:
                write_json(
                    args.hostess_staged_payload_manifest_receipt_rejection_out,
                    build_hostess_staged_payload_manifest_receipt(
                        staging_file_copy_receipt,
                        decision=REJECTED_STATUS,
                        reason_code=(
                            "hostess.issue.operator_rejected_hostess_staged_payload_manifest"
                        ),
                    ),
                )
    if (
        args.hostess_downstream_shell_selection_receipt_out
        or args.hostess_downstream_shell_selection_receipt_rejection_out
    ):
        if staged_payload_manifest_receipt is None:
            if staging_file_copy_receipt is None:
                if staging_file_plan is None:
                    raise ValueError(
                        "--hostess-staged-payload-manifest-receipt-in, "
                        "--hostess-staging-file-copy-receipt-in, or "
                        "--hostess-staging-file-plan-in is required when building "
                        "a Hostess downstream shell selection receipt"
                    )
                if staging_file_plan_receipt is None:
                    if staging_handoff_acceptance_receipt is None:
                        raise ValueError(
                            "--hostess-staged-payload-manifest-receipt-in, "
                            "--hostess-staging-file-copy-receipt-in, "
                            "--hostess-staging-file-plan-receipt-in, or "
                            "handoff acceptance inputs are required when building "
                            "a Hostess downstream shell selection receipt"
                        )
                    staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                        staging_handoff_acceptance_receipt,
                        staging_file_plan,
                        staging_root=args.hostess_staging_root,
                        source_file_plan_path=staging_file_plan_path,
                    )
                staging_file_copy_receipt = build_hostess_staging_file_copy_receipt(
                    staging_file_plan_receipt,
                    staging_file_plan,
                )
            staged_payload_manifest_receipt = (
                build_hostess_staged_payload_manifest_receipt(
                    staging_file_copy_receipt,
                )
            )
        if args.hostess_downstream_shell_selection_receipt_out:
            if downstream_shell_selection_receipt is None:
                downstream_shell_selection_receipt = (
                    build_hostess_downstream_shell_selection_receipt(
                        staged_payload_manifest_receipt,
                        target_kind=args.hostess_downstream_shell_selection_target_kind,
                        graph_id=args.hostess_downstream_shell_selection_graph_id,
                        consumer_id=args.hostess_downstream_shell_selection_consumer_id,
                    )
                )
            write_json(
                args.hostess_downstream_shell_selection_receipt_out,
                downstream_shell_selection_receipt,
            )
        if args.hostess_downstream_shell_selection_receipt_rejection_out:
            write_json(
                args.hostess_downstream_shell_selection_receipt_rejection_out,
                build_hostess_downstream_shell_selection_receipt(
                    staged_payload_manifest_receipt,
                    target_kind=args.hostess_downstream_shell_selection_target_kind,
                    graph_id=args.hostess_downstream_shell_selection_graph_id,
                    consumer_id=args.hostess_downstream_shell_selection_consumer_id,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_downstream_shell_selection"
                    ),
                ),
            )
    if (
        args.hostess_manifold_shell_handoff_review_intake_receipt_out
        or args.hostess_manifold_shell_handoff_review_intake_receipt_rejection_out
    ):
        if downstream_shell_selection_receipt is None:
            if staged_payload_manifest_receipt is None:
                if staging_file_copy_receipt is None:
                    raise ValueError(
                        "--hostess-downstream-shell-selection-receipt-in, "
                        "--hostess-staged-payload-manifest-receipt-in, or "
                        "--hostess-staging-file-copy-receipt-in is required when "
                        "building a Hostess Manifold shell handoff review intake receipt"
                    )
                staged_payload_manifest_receipt = (
                    build_hostess_staged_payload_manifest_receipt(
                        staging_file_copy_receipt,
                    )
                )
            downstream_shell_selection_receipt = (
                build_hostess_downstream_shell_selection_receipt(
                    staged_payload_manifest_receipt,
                    target_kind=args.hostess_downstream_shell_selection_target_kind,
                    graph_id=args.hostess_downstream_shell_selection_graph_id,
                    consumer_id=args.hostess_downstream_shell_selection_consumer_id,
                )
            )
        selected_handoff = selected_manifold_shell_handoff_from_selection(
            downstream_shell_selection_receipt
        )
        if args.hostess_manifold_shell_handoff_review_intake_receipt_out:
            if manifold_shell_handoff_review_receipt is None:
                raise ValueError(
                    "--manifold-shell-handoff-review-receipt-in is required when "
                    "building a Hostess Manifold shell handoff review intake receipt"
                )
            manifold_shell_handoff_review_intake_receipt = (
                build_hostess_manifold_shell_handoff_review_intake_receipt(
                    downstream_shell_selection_receipt,
                    selected_handoff,
                    manifold_shell_handoff_review_receipt,
                    args.manifold_shell_handoff_review_receipt_in,
                )
            )
            write_json(
                args.hostess_manifold_shell_handoff_review_intake_receipt_out,
                manifold_shell_handoff_review_intake_receipt,
            )
        if args.hostess_manifold_shell_handoff_review_intake_receipt_rejection_out:
            write_json(
                args.hostess_manifold_shell_handoff_review_intake_receipt_rejection_out,
                build_hostess_manifold_shell_handoff_review_intake_receipt(
                    downstream_shell_selection_receipt,
                    selected_handoff,
                    manifold_shell_handoff_review_receipt or {},
                    args.manifold_shell_handoff_review_receipt_in,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_manifold_shell_handoff_review_intake"
                    ),
                ),
            )
    if (
        args.hostess_makepad_shell_contract_receipt_out
        or args.hostess_makepad_shell_contract_receipt_rejection_out
    ):
        if manifold_shell_handoff_review_intake_receipt is None:
            raise ValueError(
                "--hostess-manifold-shell-handoff-review-intake-receipt-in or "
                "--hostess-manifold-shell-handoff-review-intake-receipt-out is "
                "required when building a Hostess Makepad shell contract receipt"
            )
        if args.hostess_makepad_shell_contract_receipt_out:
            makepad_shell_contract_receipt = (
                build_hostess_makepad_shell_contract_receipt(
                    manifold_shell_handoff_review_intake_receipt,
                    args.hostess_manifold_shell_handoff_review_intake_receipt_in
                    or args.hostess_manifold_shell_handoff_review_intake_receipt_out,
                )
            )
            write_json(
                args.hostess_makepad_shell_contract_receipt_out,
                makepad_shell_contract_receipt,
            )
        if args.hostess_makepad_shell_contract_receipt_rejection_out:
            write_json(
                args.hostess_makepad_shell_contract_receipt_rejection_out,
                build_hostess_makepad_shell_contract_receipt(
                    manifold_shell_handoff_review_intake_receipt,
                    args.hostess_manifold_shell_handoff_review_intake_receipt_in
                    or args.hostess_manifold_shell_handoff_review_intake_receipt_out,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_makepad_shell_contract"
                    ),
                ),
            )
    if (
        args.hostess_makepad_shell_launch_handoff_receipt_out
        or args.hostess_makepad_shell_launch_handoff_receipt_rejection_out
    ):
        if makepad_shell_contract_receipt is None:
            raise ValueError(
                "--hostess-makepad-shell-contract-receipt-in or "
                "--hostess-makepad-shell-contract-receipt-out is required when "
                "building a Hostess Makepad shell launch handoff receipt"
            )
        makepad_shell_contract_receipt_path = (
            args.hostess_makepad_shell_contract_receipt_in
            or args.hostess_makepad_shell_contract_receipt_out
        )
        if args.hostess_makepad_shell_launch_handoff_receipt_out:
            makepad_shell_launch_handoff_receipt = (
                build_hostess_makepad_shell_launch_handoff_receipt(
                    makepad_shell_contract_receipt,
                    makepad_shell_contract_receipt_path,
                )
            )
            write_json(
                args.hostess_makepad_shell_launch_handoff_receipt_out,
                makepad_shell_launch_handoff_receipt,
            )
        if args.hostess_makepad_shell_launch_handoff_receipt_rejection_out:
            write_json(
                args.hostess_makepad_shell_launch_handoff_receipt_rejection_out,
                build_hostess_makepad_shell_launch_handoff_receipt(
                    makepad_shell_contract_receipt,
                    makepad_shell_contract_receipt_path,
                    decision=REJECTED_STATUS,
                    reason_code=(
                        "hostess.issue.operator_rejected_hostess_makepad_shell_launch_handoff"
                    ),
                ),
            )
    if (
        args.validate_platform_smoke_approval
        or args.validate_platform_smoke_execution_request
        or args.validate_platform_smoke_execution_receipt
        or args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_plan is None:
        if args.validate_platform_smoke_plan:
            platform_smoke_plan = load_json(args.validate_platform_smoke_plan)
        else:
            if dry_run_request is None:
                if smoke_handoff is None:
                    smoke_handoff = build_smoke_handoff_checklist(
                        request,
                        report,
                        ack_fixture,
                        target_profile=args.target_profile,
                    )
                dry_run_request = build_smoke_dry_run_request(
                    smoke_handoff,
                    target_profile=args.target_profile,
                )
            if dry_run_receipt is None:
                dry_run_receipt = build_smoke_dry_run_receipt(dry_run_request)
            if smoke_preflight is None:
                smoke_preflight = build_smoke_execution_preflight(
                    dry_run_request,
                    dry_run_receipt,
                    target_profile=args.target_profile,
                )
            if host_shell_execution is None:
                host_shell_execution = build_smoke_host_shell_execution(smoke_preflight)
            if smoke_review_bundle is None:
                smoke_review_bundle = build_smoke_review_bundle(host_shell_execution)
            platform_smoke_plan = build_platform_smoke_plan(
                smoke_review_bundle,
                target_platform=args.target_platform,
            )
    if (
        args.validate_platform_smoke_execution_request
        or args.validate_platform_smoke_execution_receipt
        or args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_approval is None:
        if args.validate_platform_smoke_approval:
            platform_smoke_approval = load_json(args.validate_platform_smoke_approval)
        else:
            platform_smoke_approval = build_platform_smoke_approval_receipt(
                platform_smoke_plan,
                decision=APPROVED_STATUS,
            )
    if (
        args.validate_platform_smoke_execution_receipt
        or args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_execution_request is None:
        if args.validate_platform_smoke_execution_request:
            platform_smoke_execution_request = load_json(args.validate_platform_smoke_execution_request)
        else:
            platform_smoke_execution_request = build_platform_smoke_execution_request(
                platform_smoke_plan,
                platform_smoke_approval,
            )
    if (
        args.validate_platform_smoke_operator_start_gate
        or args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_execution_receipt is None:
        if args.validate_platform_smoke_execution_receipt:
            platform_smoke_execution_receipt = load_json(args.validate_platform_smoke_execution_receipt)
        else:
            platform_smoke_execution_receipt = build_platform_smoke_execution_receipt(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
            )
    if (
        args.validate_platform_smoke_operator_start_preflight
        or args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_operator_start_gate is None:
        if args.validate_platform_smoke_operator_start_gate:
            platform_smoke_operator_start_gate = load_json(args.validate_platform_smoke_operator_start_gate)
        else:
            platform_smoke_operator_start_gate = build_platform_smoke_operator_start_gate(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
                platform_smoke_execution_receipt,
                host_shell_kind=args.host_shell_kind,
            )
    if (
        args.validate_platform_smoke_execution_report
        or args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_operator_start_preflight is None:
        if args.validate_platform_smoke_operator_start_preflight:
            platform_smoke_operator_start_preflight = load_json(
                args.validate_platform_smoke_operator_start_preflight
            )
        else:
            platform_smoke_operator_start_preflight = (
                build_platform_smoke_operator_start_preflight_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    platform_smoke_operator_start_gate,
                    decision=APPROVED_STATUS,
                    pmb_shell_handoff_review=pmb_shell_handoff_review,
                    pmb_shell_handoff_review_path=pmb_shell_handoff_review_path,
                    require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
                )
            )
    if (
        args.validate_platform_smoke_evidence_attachment
        or args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_execution_report is None:
        if args.validate_platform_smoke_execution_report:
            platform_smoke_execution_report = load_json(args.validate_platform_smoke_execution_report)
        else:
            platform_smoke_execution_report = build_platform_smoke_execution_report(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
                platform_smoke_execution_receipt,
                platform_smoke_operator_start_gate,
                platform_smoke_operator_start_preflight,
            )
    if (
        args.validate_platform_smoke_evidence_review
        or args.validate_operator_release_readiness_bundle
    ) and platform_smoke_evidence_attachment is None:
        if args.validate_platform_smoke_evidence_attachment:
            platform_smoke_evidence_attachment = load_json(
                args.validate_platform_smoke_evidence_attachment
            )
        else:
            platform_smoke_evidence_attachment = (
                build_platform_smoke_evidence_attachment_receipt(
                    platform_smoke_plan,
                    platform_smoke_approval,
                    platform_smoke_execution_request,
                    platform_smoke_execution_receipt,
                    platform_smoke_operator_start_gate,
                    platform_smoke_operator_start_preflight,
                    platform_smoke_execution_report,
                )
            )
    if args.validate_operator_release_readiness_bundle and platform_smoke_evidence_review is None:
        if args.validate_platform_smoke_evidence_review:
            platform_smoke_evidence_review = load_json(
                args.validate_platform_smoke_evidence_review
            )
        else:
            platform_smoke_evidence_review = build_platform_smoke_evidence_review(
                platform_smoke_plan,
                platform_smoke_approval,
                platform_smoke_execution_request,
                platform_smoke_execution_receipt,
                platform_smoke_operator_start_gate,
                platform_smoke_operator_start_preflight,
                platform_smoke_execution_report,
                platform_smoke_evidence_attachment,
            )
    if args.validate_operator_release_readiness_bundle and pmb_replay_validation_receipt is None:
        if args.validate_pmb_replay_validation_receipt:
            pmb_replay_validation_receipt = load_json(
                args.validate_pmb_replay_validation_receipt
            )
        else:
            if pmb_validation_handoff is None:
                if pmb_authoring_review is None:
                    raise ValueError(
                        "--pmb-replay-validation-receipt-in or --pmb-authoring-review-in "
                        "is required when validating an operator release readiness bundle"
                    )
                pmb_validation_handoff = build_projected_motion_breath_validation_handoff(
                    pmb_authoring_review,
                    pmb_package_evidence_intake,
                    args.pmb_authoring_review_in,
                    args.pmb_package_evidence_intake_in,
                    pmb_source_adapter_selection,
                    args.pmb_source_adapter_selection_in,
                )
            pmb_replay_validation_receipt = (
                build_projected_motion_breath_replay_validation_receipt(
                    pmb_validation_handoff,
                    pmb_replay_descriptors,
                    args.pmb_replay_descriptors_in,
                )
            )
    if args.validate_ack:
        ack_report = validate_ack_fixture(request, load_json(args.validate_ack))
        write_json(args.validate_ack.with_suffix(args.validate_ack.suffix + ".validation.json"), ack_report)
    if args.validate_reject:
        reject_report = validate_reject_fixture(request, load_json(args.validate_reject))
        write_json(
            args.validate_reject.with_suffix(args.validate_reject.suffix + ".validation.json"),
            reject_report,
        )
    if args.validate_smoke_handoff:
        smoke_report = validate_smoke_handoff_checklist(load_json(args.validate_smoke_handoff))
        write_json(
            args.validate_smoke_handoff.with_suffix(args.validate_smoke_handoff.suffix + ".validation.json"),
            smoke_report,
        )
    if args.validate_smoke_dry_run_request:
        request_report = validate_smoke_dry_run_request(load_json(args.validate_smoke_dry_run_request))
        write_json(
            args.validate_smoke_dry_run_request.with_suffix(
                args.validate_smoke_dry_run_request.suffix + ".validation.json"
            ),
            request_report,
        )
    if args.validate_smoke_dry_run_receipt:
        if dry_run_request is None:
            if args.validate_smoke_dry_run_request:
                dry_run_request = load_json(args.validate_smoke_dry_run_request)
            else:
                if smoke_handoff is None:
                    smoke_handoff = build_smoke_handoff_checklist(
                        request,
                        report,
                        ack_fixture,
                        target_profile=args.target_profile,
                    )
                dry_run_request = build_smoke_dry_run_request(
                    smoke_handoff,
                    target_profile=args.target_profile,
                )
        receipt_report = validate_smoke_dry_run_receipt(
            dry_run_request,
            load_json(args.validate_smoke_dry_run_receipt),
        )
        write_json(
            args.validate_smoke_dry_run_receipt.with_suffix(
                args.validate_smoke_dry_run_receipt.suffix + ".validation.json"
            ),
            receipt_report,
        )
    if args.validate_smoke_preflight:
        preflight_report = validate_smoke_execution_preflight(load_json(args.validate_smoke_preflight))
        write_json(
            args.validate_smoke_preflight.with_suffix(
                args.validate_smoke_preflight.suffix + ".validation.json"
            ),
            preflight_report,
        )
    if args.validate_smoke_host_shell_execution:
        execution_report = validate_smoke_host_shell_execution(load_json(args.validate_smoke_host_shell_execution))
        write_json(
            args.validate_smoke_host_shell_execution.with_suffix(
                args.validate_smoke_host_shell_execution.suffix + ".validation.json"
            ),
            execution_report,
        )
    if args.validate_smoke_review_bundle:
        bundle_report = validate_smoke_review_bundle(load_json(args.validate_smoke_review_bundle))
        write_json(
            args.validate_smoke_review_bundle.with_suffix(
                args.validate_smoke_review_bundle.suffix + ".validation.json"
            ),
            bundle_report,
        )
    if args.validate_platform_smoke_plan:
        plan_report = validate_platform_smoke_plan(load_json(args.validate_platform_smoke_plan))
        write_json(
            args.validate_platform_smoke_plan.with_suffix(
                args.validate_platform_smoke_plan.suffix + ".validation.json"
            ),
            plan_report,
        )
    if args.validate_platform_smoke_approval:
        approval_report = validate_platform_smoke_approval_receipt(
            platform_smoke_plan,
            load_json(args.validate_platform_smoke_approval),
        )
        write_json(
            args.validate_platform_smoke_approval.with_suffix(
                args.validate_platform_smoke_approval.suffix + ".validation.json"
            ),
            approval_report,
        )
    if args.validate_platform_smoke_execution_request:
        execution_request_report = validate_platform_smoke_execution_request(
            platform_smoke_plan,
            platform_smoke_approval,
            load_json(args.validate_platform_smoke_execution_request),
        )
        write_json(
            args.validate_platform_smoke_execution_request.with_suffix(
                args.validate_platform_smoke_execution_request.suffix + ".validation.json"
            ),
            execution_request_report,
        )
    if args.validate_platform_smoke_execution_receipt:
        execution_receipt_report = validate_platform_smoke_execution_receipt(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            load_json(args.validate_platform_smoke_execution_receipt),
        )
        write_json(
            args.validate_platform_smoke_execution_receipt.with_suffix(
                args.validate_platform_smoke_execution_receipt.suffix + ".validation.json"
            ),
            execution_receipt_report,
        )
    if args.validate_platform_smoke_operator_start_gate:
        operator_start_report = validate_platform_smoke_operator_start_gate(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            load_json(args.validate_platform_smoke_operator_start_gate),
        )
        write_json(
            args.validate_platform_smoke_operator_start_gate.with_suffix(
                args.validate_platform_smoke_operator_start_gate.suffix + ".validation.json"
            ),
            operator_start_report,
        )
    if args.validate_platform_smoke_operator_start_preflight:
        operator_start_preflight_report = validate_platform_smoke_operator_start_preflight_receipt(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            platform_smoke_operator_start_gate,
            load_json(args.validate_platform_smoke_operator_start_preflight),
            require_pmb_shell_handoff_review=pmb_shell_handoff_review_required,
        )
        write_json(
            args.validate_platform_smoke_operator_start_preflight.with_suffix(
                args.validate_platform_smoke_operator_start_preflight.suffix + ".validation.json"
            ),
            operator_start_preflight_report,
        )
    if args.validate_platform_smoke_execution_report:
        execution_report_report = validate_platform_smoke_execution_report(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            platform_smoke_operator_start_gate,
            platform_smoke_operator_start_preflight,
            load_json(args.validate_platform_smoke_execution_report),
        )
        write_json(
            args.validate_platform_smoke_execution_report.with_suffix(
                args.validate_platform_smoke_execution_report.suffix + ".validation.json"
            ),
            execution_report_report,
        )
    if args.validate_platform_smoke_evidence_attachment:
        evidence_attachment_report = validate_platform_smoke_evidence_attachment_receipt(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            platform_smoke_operator_start_gate,
            platform_smoke_operator_start_preflight,
            platform_smoke_execution_report,
            load_json(args.validate_platform_smoke_evidence_attachment),
        )
        write_json(
            args.validate_platform_smoke_evidence_attachment.with_suffix(
                args.validate_platform_smoke_evidence_attachment.suffix + ".validation.json"
            ),
            evidence_attachment_report,
        )
    if args.validate_platform_smoke_evidence_review:
        evidence_review_report = validate_platform_smoke_evidence_review(
            platform_smoke_plan,
            platform_smoke_approval,
            platform_smoke_execution_request,
            platform_smoke_execution_receipt,
            platform_smoke_operator_start_gate,
            platform_smoke_operator_start_preflight,
            platform_smoke_execution_report,
            platform_smoke_evidence_attachment,
            load_json(args.validate_platform_smoke_evidence_review),
        )
        write_json(
            args.validate_platform_smoke_evidence_review.with_suffix(
                args.validate_platform_smoke_evidence_review.suffix + ".validation.json"
            ),
            evidence_review_report,
        )
    if args.validate_pmb_validation_handoff:
        pmb_validation_report = validate_projected_motion_breath_validation_handoff(
            load_json(args.validate_pmb_validation_handoff)
        )
        write_json(
            args.validate_pmb_validation_handoff.with_suffix(
                args.validate_pmb_validation_handoff.suffix + ".validation.json"
            ),
            pmb_validation_report,
        )
    if args.validate_pmb_replay_validation_receipt:
        pmb_replay_validation_report = (
            validate_projected_motion_breath_replay_validation_receipt(
                load_json(args.validate_pmb_replay_validation_receipt)
            )
        )
        write_json(
            args.validate_pmb_replay_validation_receipt.with_suffix(
                args.validate_pmb_replay_validation_receipt.suffix + ".validation.json"
            ),
            pmb_replay_validation_report,
        )
    if args.validate_operator_release_readiness_bundle:
        operator_release_report = validate_operator_release_readiness_bundle(
            platform_smoke_evidence_review,
            pmb_replay_validation_receipt,
            load_json(args.validate_operator_release_readiness_bundle),
        )
        write_json(
            args.validate_operator_release_readiness_bundle.with_suffix(
                args.validate_operator_release_readiness_bundle.suffix
                + ".validation.json"
            ),
            operator_release_report,
        )
    if args.validate_hostess_staging_handoff_acceptance_receipt:
        if operator_release_readiness_bundle is None:
            if args.validate_operator_release_readiness_bundle:
                operator_release_readiness_bundle = load_json(
                    args.validate_operator_release_readiness_bundle
                )
            else:
                operator_release_readiness_bundle = build_operator_release_readiness_bundle(
                    platform_smoke_evidence_review,
                    pmb_replay_validation_receipt,
                )
        if staging_handoff is None:
            raise ValueError(
                "--hostess-staging-handoff-in or request handoff_path is required "
                "when validating a Hostess staging handoff acceptance receipt"
            )
        if staging_acceptance_manifest is None:
            raise ValueError(
                "--hostess-staging-acceptance-manifest-in or request "
                "acceptance_manifest_path is required when validating a Hostess "
                "staging handoff acceptance receipt"
            )
        handoff_acceptance_report = validate_hostess_staging_handoff_acceptance_receipt(
            operator_release_readiness_bundle,
            staging_handoff,
            staging_acceptance_manifest,
            load_json(args.validate_hostess_staging_handoff_acceptance_receipt),
        )
        write_json(
            args.validate_hostess_staging_handoff_acceptance_receipt.with_suffix(
                args.validate_hostess_staging_handoff_acceptance_receipt.suffix
                + ".validation.json"
            ),
            handoff_acceptance_report,
        )
    if args.validate_hostess_staging_file_plan_receipt:
        if staging_handoff_acceptance_receipt is None:
            if args.validate_hostess_staging_handoff_acceptance_receipt:
                staging_handoff_acceptance_receipt = load_json(
                    args.validate_hostess_staging_handoff_acceptance_receipt
                )
            else:
                if operator_release_readiness_bundle is None:
                    raise ValueError(
                        "--hostess-staging-handoff-acceptance-receipt-in or "
                        "operator release inputs are required when validating a "
                        "Hostess staging file plan receipt"
                    )
                if staging_handoff is None:
                    raise ValueError(
                        "--hostess-staging-handoff-in or request handoff_path is required "
                        "when validating a Hostess staging file plan receipt"
                    )
                if staging_acceptance_manifest is None:
                    raise ValueError(
                        "--hostess-staging-acceptance-manifest-in or request "
                        "acceptance_manifest_path is required when validating a "
                        "Hostess staging file plan receipt"
                    )
                staging_handoff_acceptance_receipt = (
                    build_hostess_staging_handoff_acceptance_receipt(
                        operator_release_readiness_bundle,
                        staging_handoff,
                        staging_acceptance_manifest,
                    )
                )
        if staging_file_plan is None:
            raise ValueError(
                "--hostess-staging-file-plan-in or request file_plan_path is required "
                "when validating a Hostess staging file plan receipt"
            )
        file_plan_report = validate_hostess_staging_file_plan_receipt(
            staging_handoff_acceptance_receipt,
            staging_file_plan,
            load_json(args.validate_hostess_staging_file_plan_receipt),
        )
        write_json(
            args.validate_hostess_staging_file_plan_receipt.with_suffix(
                args.validate_hostess_staging_file_plan_receipt.suffix
                + ".validation.json"
            ),
            file_plan_report,
        )
    if args.validate_hostess_staging_file_copy_receipt:
        if staging_file_plan_receipt is None:
            if args.validate_hostess_staging_file_plan_receipt:
                staging_file_plan_receipt = load_json(
                    args.validate_hostess_staging_file_plan_receipt
                )
            else:
                if staging_handoff_acceptance_receipt is None:
                    raise ValueError(
                        "--hostess-staging-file-plan-receipt-in, "
                        "--validate-hostess-staging-file-plan-receipt, or "
                        "handoff acceptance inputs are required when validating a "
                        "Hostess staging file copy receipt"
                    )
                if staging_file_plan is None:
                    raise ValueError(
                        "--hostess-staging-file-plan-in or request file_plan_path is required "
                        "when validating a Hostess staging file copy receipt"
                    )
                staging_file_plan_receipt = build_hostess_staging_file_plan_receipt(
                    staging_handoff_acceptance_receipt,
                    staging_file_plan,
                    staging_root=args.hostess_staging_root,
                    source_file_plan_path=staging_file_plan_path,
                )
        if staging_file_plan is None:
            raise ValueError(
                "--hostess-staging-file-plan-in or request file_plan_path is required "
                "when validating a Hostess staging file copy receipt"
            )
        file_copy_report = validate_hostess_staging_file_copy_receipt(
            staging_file_plan_receipt,
            staging_file_plan,
            load_json(args.validate_hostess_staging_file_copy_receipt),
        )
        write_json(
            args.validate_hostess_staging_file_copy_receipt.with_suffix(
                args.validate_hostess_staging_file_copy_receipt.suffix
                + ".validation.json"
            ),
            file_copy_report,
        )
    if args.validate_hostess_staged_payload_manifest_receipt:
        if staging_file_copy_receipt is None:
            if args.validate_hostess_staging_file_copy_receipt:
                staging_file_copy_receipt = load_json(
                    args.validate_hostess_staging_file_copy_receipt
                )
            else:
                if staging_file_plan_receipt is None:
                    raise ValueError(
                        "--hostess-staging-file-copy-receipt-in, "
                        "--validate-hostess-staging-file-copy-receipt, or "
                        "file-plan receipt inputs are required when validating a "
                        "Hostess staged payload manifest receipt"
                    )
                if staging_file_plan is None:
                    raise ValueError(
                        "--hostess-staging-file-plan-in or request file_plan_path is required "
                        "when validating a Hostess staged payload manifest receipt"
                    )
                staging_file_copy_receipt = build_hostess_staging_file_copy_receipt(
                    staging_file_plan_receipt,
                    staging_file_plan,
                )
        staged_payload_report = validate_hostess_staged_payload_manifest_receipt(
            staging_file_copy_receipt,
            load_json(args.validate_hostess_staged_payload_manifest_receipt),
        )
        write_json(
            args.validate_hostess_staged_payload_manifest_receipt.with_suffix(
                args.validate_hostess_staged_payload_manifest_receipt.suffix
                + ".validation.json"
            ),
            staged_payload_report,
        )
    if args.validate_hostess_downstream_shell_selection_receipt:
        if staged_payload_manifest_receipt is None:
            if args.validate_hostess_staged_payload_manifest_receipt:
                staged_payload_manifest_receipt = load_json(
                    args.validate_hostess_staged_payload_manifest_receipt
                )
            elif staging_file_copy_receipt is not None:
                staged_payload_manifest_receipt = (
                    build_hostess_staged_payload_manifest_receipt(
                        staging_file_copy_receipt,
                    )
                )
            else:
                raise ValueError(
                    "--hostess-staged-payload-manifest-receipt-in, "
                    "--validate-hostess-staged-payload-manifest-receipt, or "
                    "--hostess-staging-file-copy-receipt-in is required when "
                    "validating a Hostess downstream shell selection receipt"
                )
        downstream_shell_selection_report = (
            validate_hostess_downstream_shell_selection_receipt(
                staged_payload_manifest_receipt,
                load_json(args.validate_hostess_downstream_shell_selection_receipt),
            )
        )
        write_json(
            args.validate_hostess_downstream_shell_selection_receipt.with_suffix(
                args.validate_hostess_downstream_shell_selection_receipt.suffix
                + ".validation.json"
            ),
            downstream_shell_selection_report,
        )
    if args.validate_hostess_manifold_shell_handoff_review_intake_receipt:
        intake_receipt = load_json(
            args.validate_hostess_manifold_shell_handoff_review_intake_receipt
        )
        manifold_shell_handoff_review_intake_receipt = intake_receipt
        if downstream_shell_selection_receipt is None:
            if args.validate_hostess_downstream_shell_selection_receipt:
                downstream_shell_selection_receipt = load_json(
                    args.validate_hostess_downstream_shell_selection_receipt
                )
            else:
                raise ValueError(
                    "--hostess-downstream-shell-selection-receipt-in or "
                    "--validate-hostess-downstream-shell-selection-receipt is "
                    "required when validating a Hostess Manifold shell handoff "
                    "review intake receipt"
                )
        selected_handoff = selected_manifold_shell_handoff_from_selection(
            downstream_shell_selection_receipt
        )
        if manifold_shell_handoff_review_receipt is None:
            review_path = intake_receipt.get(
                "source_manifold_shell_handoff_review_receipt_path"
            )
            if isinstance(review_path, str) and review_path:
                manifold_shell_handoff_review_receipt = load_json(Path(review_path))
            else:
                raise ValueError(
                    "--manifold-shell-handoff-review-receipt-in is required when "
                    "validating a Hostess Manifold shell handoff review intake receipt"
                )
        intake_report = validate_hostess_manifold_shell_handoff_review_intake_receipt(
            downstream_shell_selection_receipt,
            selected_handoff,
            manifold_shell_handoff_review_receipt,
            intake_receipt,
        )
        write_json(
            args.validate_hostess_manifold_shell_handoff_review_intake_receipt.with_suffix(
                args.validate_hostess_manifold_shell_handoff_review_intake_receipt.suffix
                + ".validation.json"
            ),
            intake_report,
        )
    if args.validate_hostess_makepad_shell_contract_receipt:
        makepad_shell_contract_receipt = load_json(
            args.validate_hostess_makepad_shell_contract_receipt
        )
        if manifold_shell_handoff_review_intake_receipt is None:
            if args.validate_hostess_manifold_shell_handoff_review_intake_receipt:
                manifold_shell_handoff_review_intake_receipt = load_json(
                    args.validate_hostess_manifold_shell_handoff_review_intake_receipt
                )
            else:
                intake_path = makepad_shell_contract_receipt.get(
                    "source_manifold_shell_handoff_review_intake_receipt_path"
                )
                if isinstance(intake_path, str) and intake_path:
                    manifold_shell_handoff_review_intake_receipt = load_json(
                        Path(intake_path)
                    )
                else:
                    raise ValueError(
                        "--hostess-manifold-shell-handoff-review-intake-receipt-in "
                        "or --validate-hostess-manifold-shell-handoff-review-intake-receipt "
                        "is required when validating a Hostess Makepad shell contract receipt"
                    )
        makepad_shell_contract_report = (
            validate_hostess_makepad_shell_contract_receipt(
                manifold_shell_handoff_review_intake_receipt,
                makepad_shell_contract_receipt,
            )
        )
        write_json(
            args.validate_hostess_makepad_shell_contract_receipt.with_suffix(
                args.validate_hostess_makepad_shell_contract_receipt.suffix
                + ".validation.json"
            ),
            makepad_shell_contract_report,
        )
    if args.validate_hostess_makepad_shell_launch_handoff_receipt:
        makepad_shell_launch_handoff_receipt = load_json(
            args.validate_hostess_makepad_shell_launch_handoff_receipt
        )
        if makepad_shell_contract_receipt is None:
            if args.validate_hostess_makepad_shell_contract_receipt:
                makepad_shell_contract_receipt = load_json(
                    args.validate_hostess_makepad_shell_contract_receipt
                )
            else:
                contract_receipt_path = makepad_shell_launch_handoff_receipt.get(
                    "source_makepad_shell_contract_receipt_path"
                )
                if isinstance(contract_receipt_path, str) and contract_receipt_path:
                    makepad_shell_contract_receipt = load_json(
                        Path(contract_receipt_path)
                    )
                else:
                    raise ValueError(
                        "--hostess-makepad-shell-contract-receipt-in or "
                        "--validate-hostess-makepad-shell-contract-receipt is "
                        "required when validating a Hostess Makepad shell launch "
                        "handoff receipt"
                    )
        makepad_shell_launch_handoff_report = (
            validate_hostess_makepad_shell_launch_handoff_receipt(
                makepad_shell_contract_receipt,
                makepad_shell_launch_handoff_receipt,
            )
        )
        write_json(
            args.validate_hostess_makepad_shell_launch_handoff_receipt.with_suffix(
                args.validate_hostess_makepad_shell_launch_handoff_receipt.suffix
                + ".validation.json"
            ),
            makepad_shell_launch_handoff_report,
        )
    return 0 if report["status"] == ACCEPTED_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
