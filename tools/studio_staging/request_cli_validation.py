"""Validation output pipeline for the Studio staging request CLI."""

from __future__ import annotations

from pathlib import Path

from tools.studio_staging.manifold_handoff_intake import (
    selected_manifold_shell_handoff_from_selection,
    validate_hostess_manifold_shell_handoff_review_intake_receipt,
)
from tools.studio_staging.makepad_shell_contract import (
    validate_hostess_makepad_shell_contract_receipt,
    validate_hostess_makepad_shell_launch_handoff_receipt,
)
from tools.studio_staging.request_shared import *  # shared schema constants and JSON helpers
from tools.studio_staging.request_intake import *  # request intake validators
from tools.studio_staging.smoke_workflow import *  # smoke workflow validators/builders
from tools.studio_staging.platform_smoke import *  # platform smoke validators/builders
from tools.studio_staging.pmb_release import *  # PMB/operator release validators/builders
from tools.studio_staging.staging_handoff import *  # staging handoff validators/builders


def run_validation_outputs(
    *,
    args,
    request,
    ack_fixture,
    smoke_handoff,
    dry_run_request,
    dry_run_receipt,
    smoke_preflight,
    host_shell_execution,
    smoke_review_bundle,
    platform_smoke_plan,
    platform_smoke_approval,
    platform_smoke_execution_request,
    platform_smoke_execution_receipt,
    platform_smoke_operator_start_gate,
    platform_smoke_operator_start_preflight,
    platform_smoke_execution_report,
    platform_smoke_evidence_attachment,
    platform_smoke_evidence_review,
    pmb_authoring_review,
    pmb_package_evidence_intake,
    pmb_source_adapter_selection,
    pmb_shell_handoff_review,
    pmb_shell_handoff_review_path,
    pmb_shell_handoff_review_required,
    pmb_validation_handoff,
    pmb_replay_descriptors,
    pmb_replay_validation_receipt,
    operator_release_readiness_bundle,
    staging_file_plan,
    staging_file_plan_path,
    staging_handoff,
    staging_acceptance_manifest,
    staging_handoff_acceptance_receipt,
    staging_file_plan_receipt,
    staging_file_copy_receipt,
    staged_payload_manifest_receipt,
    downstream_shell_selection_receipt,
    manifold_shell_handoff_review_receipt,
    manifold_shell_handoff_review_intake_receipt,
    makepad_shell_contract_receipt,
    makepad_shell_launch_handoff_receipt,
) -> None:
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
