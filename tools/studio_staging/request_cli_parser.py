"""Argument parser for the Studio staging request CLI."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_staging_request_parser() -> argparse.ArgumentParser:
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
    return parser
