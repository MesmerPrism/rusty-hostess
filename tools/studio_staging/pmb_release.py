"""Projected-motion breath and operator-release staging receipts.

Compatibility facade for the PMB release receipt families. Keep imports from
``tools.studio_staging.pmb_release`` stable while the implementation lives in
focused modules.
"""

from __future__ import annotations

from tools.studio_staging.pmb_validation_handoff import *  # re-exported facade symbols
from tools.studio_staging.pmb_replay_validation import *  # re-exported facade symbols
from tools.studio_staging.operator_release import *  # re-exported facade symbols
from tools.studio_staging.staging_handoff import *  # re-exported facade symbols

__all__ = [
    "build_projected_motion_breath_validation_handoff",
    "validate_projected_motion_breath_validation_handoff",
    "pmb_required_package_checks",
    "int_or_zero",
    "pmb_required_package_checks_ready",
    "pmb_package_evidence_intake_matches_required_checks",
    "pmb_source_authority_preserved",
    "pmb_authority_fields_match",
    "pmb_source_adapter_selection_targets_authoring",
    "pmb_source_adapter_selection_stream_binding_supported",
    "pmb_source_adapter_selection_handoff_fields_match",
    "pmb_sources_did_not_execute",
    "pmb_validation_slots",
    "pmb_validation_slot_contracts",
    "pmb_validation_slot_dicts",
    "pmb_embedded_check_dicts",
    "pmb_validation_slots_match_contracts",
    "pmb_validation_slot_unstarted",
    "pmb_validation_handoff_unstarted",
    "build_projected_motion_breath_replay_validation_receipt",
    "validate_projected_motion_breath_replay_validation_receipt",
    "pmb_replay_receipt_id",
    "pmb_replay_descriptor_source_matches_contracts",
    "pmb_replay_descriptor_rows",
    "pmb_replay_source_descriptor_by_id",
    "pmb_replay_descriptor_dicts",
    "pmb_replay_descriptors_match_contracts",
    "pmb_replay_descriptor_unstarted",
    "pmb_replay_validation_receipt_unstarted",
    "build_operator_release_readiness_bundle",
    "validate_operator_release_readiness_bundle",
    "operator_release_readiness_bundle_checks",
    "operator_release_artifact_rows",
    "operator_release_host_shell_targets",
    "operator_release_artifact_dicts",
    "operator_release_host_shell_target_dicts",
    "operator_release_source_by_role",
    "operator_release_artifacts_match_contracts",
    "operator_release_host_shell_targets_match_contracts",
    "platform_smoke_evidence_review_source_ready",
    "pmb_replay_validation_receipt_source_ready",
    "platform_smoke_evidence_review_unstarted",
    "operator_release_artifact_row_unstarted",
    "operator_release_host_shell_target_unstarted",
]
