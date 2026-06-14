"""GPU force-authority evidence validation family."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .proof_lines import count_lines_containing, lines_containing, marker_int_fields


@dataclass(frozen=True)
class ForceAuthorityEvidenceResult:
    issues: list[str]
    summary: dict[str, Any]


def analyze_force_authority_evidence(
    proof_lines: list[Any],
    thresholds: Any,
    field_particle_force_lines: list[str],
    field_particle_force_max_sample_count: int,
    expanded_force_oracle_sample_count: int,
) -> ForceAuthorityEvidenceResult:
    issues: list[str] = []
    force_candidate_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_CANDIDATE"
    )
    force_candidate_ready_count = count_lines_containing(
        force_candidate_lines, "forceAuthorityCandidateReady=true"
    )
    force_candidate_gpu_ready_count = count_lines_containing(
        force_candidate_lines, "gpuComputeCandidateReady=true"
    )
    force_candidate_single_authority_count = count_lines_containing(
        force_candidate_lines, "singleActiveForceAuthorityPreserved=true"
    )
    force_candidate_not_selected_count = count_lines_containing(
        force_candidate_lines, "candidateSelected=false"
    )
    force_candidate_not_promoted_count = count_lines_containing(
        force_candidate_lines, "candidatePromoted=false"
    )
    force_candidate_active_unchanged_count = count_lines_containing(
        force_candidate_lines, "activeForceAuthorityChanged=false"
    )
    force_candidate_force_authority_false_count = count_lines_containing(
        force_candidate_lines, "forceAuthorityReady=false"
    )
    force_candidate_runtime_authority_false_count = count_lines_containing(
        force_candidate_lines, "runtimeForceAuthority=false"
    )
    force_candidate_runtime_particle_false_count = count_lines_containing(
        force_candidate_lines, "runtimeParticleIntegration=false"
    )
    force_candidate_gpu_not_ready_count = count_lines_containing(
        force_candidate_lines, "gpuComputeReady=false"
    )
    force_candidate_low_rate_count = count_lines_containing(
        force_candidate_lines, "highRateJsonPayload=false"
    )
    force_candidate_settings_payload_false_count = count_lines_containing(
        force_candidate_lines, "settingsControlPayload=false"
    )
    if force_candidate_lines:
        if force_candidate_ready_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not keep forceAuthorityCandidateReady=true"
            )
        if force_candidate_gpu_ready_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not keep gpuComputeCandidateReady=true"
            )
        if force_candidate_single_authority_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not preserve single active authority"
            )
        if force_candidate_not_selected_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate was selected")
        if force_candidate_not_promoted_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate was promoted")
        if force_candidate_active_unchanged_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate changed active force authority")
        if force_candidate_force_authority_false_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate did not keep forceAuthorityReady=false")
        if force_candidate_runtime_authority_false_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate did not keep runtimeForceAuthority=false")
        if force_candidate_runtime_particle_false_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not keep runtimeParticleIntegration=false"
            )
        if force_candidate_gpu_not_ready_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate did not keep gpuComputeReady=false")
        if force_candidate_low_rate_count != len(force_candidate_lines):
            issues.append("GPU force authority candidate did not keep highRateJsonPayload=false")
        if force_candidate_settings_payload_false_count != len(force_candidate_lines):
            issues.append(
                "GPU force authority candidate did not keep settingsControlPayload=false"
            )
    force_gate_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_GATE"
    )
    force_gate_candidate_ready_count = count_lines_containing(
        force_gate_lines, "forceAuthorityCandidateReady=true"
    )
    force_gate_gpu_candidate_ready_count = count_lines_containing(
        force_gate_lines, "gpuComputeCandidateReady=true"
    )
    force_gate_single_authority_count = count_lines_containing(
        force_gate_lines, "singleActiveForceAuthorityPreserved=true"
    )
    force_gate_slot_count = count_lines_containing(
        force_gate_lines, "forceAuthoritySlotCount=1"
    )
    force_gate_active_count = count_lines_containing(
        force_gate_lines, "activeForceAuthorityCount=1"
    )
    force_gate_profile_required_count = count_lines_containing(
        force_gate_lines, "profileGate=explicit-profile-required"
    )
    force_gate_profile_declared_count = count_lines_containing(
        force_gate_lines, "profileGateSatisfied="
    )
    force_gate_profile_satisfied_count = count_lines_containing(
        force_gate_lines, "profileGateSatisfied=true"
    )
    force_gate_profile_unsatisfied_count = count_lines_containing(
        force_gate_lines, "profileGateSatisfied=false"
    )
    force_gate_selection_blocked_count = count_lines_containing(
        force_gate_lines, "runtimeSelectionPermitted=false"
    )
    force_gate_profile_known_count = count_lines_containing(
        force_gate_lines, "gpuForceAuthorityProfileKnown=true"
    )
    force_gate_profile_state_declared_count = count_lines_containing(
        force_gate_lines, "gpuForceAuthorityProfileEnabled="
    )
    force_gate_profile_enabled_count = count_lines_containing(
        force_gate_lines, "gpuForceAuthorityProfileEnabled=true"
    )
    force_gate_profile_disabled_count = count_lines_containing(
        force_gate_lines, "gpuForceAuthorityProfileEnabled=false"
    )
    force_gate_active_kind_count = count_lines_containing(
        force_gate_lines, "activeForceAuthorityKind=matter-cpu"
    )
    force_gate_candidate_eligible_count = count_lines_containing(
        force_gate_lines, "candidateEligible=true"
    )
    force_gate_not_selected_count = count_lines_containing(
        force_gate_lines, "candidateSelected=false"
    )
    force_gate_not_promoted_count = count_lines_containing(
        force_gate_lines, "candidatePromoted=false"
    )
    force_gate_active_unchanged_count = count_lines_containing(
        force_gate_lines, "activeForceAuthorityChanged=false"
    )
    force_gate_fallback_ready_count = count_lines_containing(
        force_gate_lines, "matterCpuFallbackReady=true"
    )
    force_gate_rollback_policy_count = count_lines_containing(
        force_gate_lines,
        "rollbackPolicy=matter-cpu-oracle-on-gpu-freshness-or-cadence-failure",
    )
    force_gate_force_authority_false_count = count_lines_containing(
        force_gate_lines, "forceAuthorityReady=false"
    )
    force_gate_runtime_authority_false_count = count_lines_containing(
        force_gate_lines, "runtimeForceAuthority=false"
    )
    force_gate_runtime_particle_false_count = count_lines_containing(
        force_gate_lines, "runtimeParticleIntegration=false"
    )
    force_gate_gpu_not_ready_count = count_lines_containing(
        force_gate_lines, "gpuComputeReady=false"
    )
    force_gate_low_rate_count = count_lines_containing(
        force_gate_lines, "highRateJsonPayload=false"
    )
    force_gate_settings_payload_false_count = count_lines_containing(
        force_gate_lines, "settingsControlPayload=false"
    )
    if force_gate_lines:
        if force_gate_candidate_ready_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not keep forceAuthorityCandidateReady=true"
            )
        if force_gate_gpu_candidate_ready_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not keep gpuComputeCandidateReady=true"
            )
        if force_gate_single_authority_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not preserve single authority")
        if force_gate_slot_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not report forceAuthoritySlotCount=1")
        if force_gate_active_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not report activeForceAuthorityCount=1")
        if force_gate_profile_required_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not require explicit profile selection"
            )
        if force_gate_profile_declared_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not declare profileGateSatisfied")
        if force_gate_selection_blocked_count != len(force_gate_lines):
            issues.append("GPU force authority gate permitted runtime selection")
        if force_gate_profile_known_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not report profile knowledge")
        if force_gate_profile_state_declared_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not declare gpuForceAuthorityProfileEnabled"
            )
        if force_gate_active_kind_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep Matter CPU active kind")
        if force_gate_candidate_eligible_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep candidateEligible=true")
        if force_gate_not_selected_count != len(force_gate_lines):
            issues.append("GPU force authority gate selected the candidate")
        if force_gate_not_promoted_count != len(force_gate_lines):
            issues.append("GPU force authority gate promoted the candidate")
        if force_gate_active_unchanged_count != len(force_gate_lines):
            issues.append("GPU force authority gate changed active force authority")
        if force_gate_fallback_ready_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep Matter CPU fallback ready")
        if force_gate_rollback_policy_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not report Matter CPU rollback policy")
        if force_gate_force_authority_false_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep forceAuthorityReady=false")
        if force_gate_runtime_authority_false_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep runtimeForceAuthority=false")
        if force_gate_runtime_particle_false_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not keep runtimeParticleIntegration=false"
            )
        if force_gate_gpu_not_ready_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep gpuComputeReady=false")
        if force_gate_low_rate_count != len(force_gate_lines):
            issues.append("GPU force authority gate did not keep highRateJsonPayload=false")
        if force_gate_settings_payload_false_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not keep settingsControlPayload=false"
            )
    force_freshness_lines = lines_containing(
        proof_lines, "RUSTY_HOSTESS_MAKEPAD_GPU_FORCE_FRESHNESS"
    )
    force_freshness_ready_count = count_lines_containing(
        force_freshness_lines, "freshnessReady=true"
    )
    force_freshness_not_ready_count = count_lines_containing(
        force_freshness_lines, "freshnessReady=false"
    )
    force_freshness_source_match_count = count_lines_containing(
        force_freshness_lines, "sourceIdMatched=true"
    )
    force_freshness_candidate_not_future_count = count_lines_containing(
        force_freshness_lines, "candidateNotFuture=true"
    )
    force_freshness_cadence_ready_count = count_lines_containing(
        force_freshness_lines, "cadenceReady=true"
    )
    force_freshness_runtime_authority_false_count = count_lines_containing(
        force_freshness_lines, "runtimeForceAuthority=false"
    )
    force_freshness_gpu_not_ready_count = count_lines_containing(
        force_freshness_lines, "gpuComputeReady=false"
    )
    force_freshness_low_rate_count = count_lines_containing(
        force_freshness_lines, "highRateJsonPayload=false"
    )
    force_freshness_settings_payload_false_count = count_lines_containing(
        force_freshness_lines, "settingsControlPayload=false"
    )
    force_freshness_lag_values = marker_int_fields(force_freshness_lines, "sourceFrameLag")
    force_freshness_max_lag_values = marker_int_fields(
        force_freshness_lines, "maxSourceFrameLag"
    )
    force_freshness_max_lag_observed = max(force_freshness_lag_values, default=0)
    force_freshness_max_lag_allowed = max(force_freshness_max_lag_values, default=0)
    if force_freshness_lines:
        if force_freshness_runtime_authority_false_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep runtimeForceAuthority=false")
        if force_freshness_gpu_not_ready_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep gpuComputeReady=false")
        if force_freshness_low_rate_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep highRateJsonPayload=false")
        if force_freshness_settings_payload_false_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep settingsControlPayload=false")
        if force_freshness_source_match_count + count_lines_containing(
            force_freshness_lines, "sourceIdMatched=false"
        ) != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not declare sourceIdMatched")
        if force_freshness_candidate_not_future_count + count_lines_containing(
            force_freshness_lines, "candidateNotFuture=false"
        ) != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not declare candidateNotFuture")
        if not force_freshness_max_lag_values:
            issues.append("GPU force freshness evidence did not declare maxSourceFrameLag")
    force_residency_lines = lines_containing(
        proof_lines, "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY"
    )
    force_residency_candidate_ready_count = count_lines_containing(
        force_residency_lines, "forceAuthorityCandidateReady=true"
    )
    force_residency_gpu_candidate_ready_count = count_lines_containing(
        force_residency_lines, "gpuComputeCandidateReady=true"
    )
    force_residency_single_authority_count = count_lines_containing(
        force_residency_lines, "singleActiveForceAuthorityPreserved=true"
    )
    force_residency_slot_count = count_lines_containing(
        force_residency_lines, "forceAuthoritySlotCount=1"
    )
    force_residency_active_count = count_lines_containing(
        force_residency_lines, "activeForceAuthorityCount=1"
    )
    force_residency_profile_required_count = count_lines_containing(
        force_residency_lines, "profileGate=explicit-profile-required"
    )
    force_residency_profile_declared_count = count_lines_containing(
        force_residency_lines, "profileGateSatisfied="
    )
    force_residency_selection_blocked_count = count_lines_containing(
        force_residency_lines, "runtimeSelectionPermitted=false"
    )
    force_residency_selection_permitted_count = count_lines_containing(
        force_residency_lines, "runtimeSelectionPermitted=true"
    )
    force_residency_active_kind_count = count_lines_containing(
        force_residency_lines, "activeForceAuthorityKind=matter-cpu"
    )
    force_residency_active_gpu_kind_count = count_lines_containing(
        force_residency_lines,
        "activeForceAuthorityKind=gpu-dense-sdf-field-particle-force",
    )
    force_residency_active_kind_declared_count = count_lines_containing(
        force_residency_lines, "activeForceAuthorityKind="
    )
    force_residency_active_source_count = count_lines_containing(
        force_residency_lines, "activeForceAuthoritySource=matter-runtime-profile"
    )
    force_residency_active_gpu_source_count = count_lines_containing(
        force_residency_lines,
        "activeForceAuthoritySource=quest-makepad-gpu-runtime-selector",
    )
    force_residency_active_source_declared_count = count_lines_containing(
        force_residency_lines, "activeForceAuthoritySource="
    )
    force_residency_oracle_authority_count = count_lines_containing(
        force_residency_lines, "matterCpuOracleForceAuthority="
    )
    force_residency_active_preserved_count = count_lines_containing(
        force_residency_lines, "activeForceAuthorityPreserved=matter-cpu-runtime"
    )
    force_residency_active_gpu_preserved_count = count_lines_containing(
        force_residency_lines, "activeForceAuthorityPreserved=gpu-backed-runtime"
    )
    force_residency_active_preserved_declared_count = count_lines_containing(
        force_residency_lines, "activeForceAuthorityPreserved="
    )
    force_residency_not_selected_count = count_lines_containing(
        force_residency_lines, "candidateSelected=false"
    )
    force_residency_selected_count = count_lines_containing(
        force_residency_lines, "candidateSelected=true"
    )
    force_residency_not_promoted_count = count_lines_containing(
        force_residency_lines, "candidatePromoted=false"
    )
    force_residency_promoted_count = count_lines_containing(
        force_residency_lines, "candidatePromoted=true"
    )
    force_residency_tracker_source_count = count_lines_containing(
        force_residency_lines,
        "residencyTrackerSource=quest-makepad-gpu-force-authority-residency-tracker",
    )
    force_residency_reused_proofs_declared_count = count_lines_containing(
        force_residency_lines, "reusedResidentProofs="
    )
    force_residency_continuity_declared_count = count_lines_containing(
        force_residency_lines, "residencyContinuityReady="
    )
    force_residency_continuity_not_broken_count = count_lines_containing(
        force_residency_lines, "residencyContinuityBroken=false"
    )
    force_residency_continuity_breaks_declared_count = count_lines_containing(
        force_residency_lines, "residencyContinuityBreakCount="
    )
    force_residency_source_generation_declared_count = count_lines_containing(
        force_residency_lines, "sourceMeshBufferGeneration="
    )
    force_residency_source_generation_matched_count = count_lines_containing(
        force_residency_lines, "sourceMeshBufferGenerationMatched=true"
    )
    force_residency_derived_generation_declared_count = count_lines_containing(
        force_residency_lines, "derivedBufferGeneration="
    )
    force_residency_derived_generation_matched_count = count_lines_containing(
        force_residency_lines, "derivedBufferGenerationMatched=true"
    )
    force_residency_queue_monotonic_count = count_lines_containing(
        force_residency_lines, "queueSubmitSerialMonotonic=true"
    )
    force_residency_fence_monotonic_count = count_lines_containing(
        force_residency_lines, "fenceSerialMonotonic=true"
    )
    force_residency_fallback_ready_count = count_lines_containing(
        force_residency_lines, "matterCpuFallbackReady=true"
    )
    force_residency_fallback_authority_count = count_lines_containing(
        force_residency_lines, "fallbackForceAuthority="
    )
    force_residency_fallback_reason_count = count_lines_containing(
        force_residency_lines, "fallbackReason="
    )
    force_residency_rollback_policy_count = count_lines_containing(
        force_residency_lines,
        "rollbackPolicy=matter-cpu-oracle-on-gpu-freshness-or-cadence-failure",
    )
    force_residency_source_resident_count = count_lines_containing(
        force_residency_lines, "sourceMeshBuffersResident=true"
    )
    force_residency_source_reuse_declared_count = count_lines_containing(
        force_residency_lines, "sourceMeshBuffersReused="
    )
    force_residency_source_reuse_count = count_lines_containing(
        force_residency_lines, "sourceMeshBuffersReused=true"
    )
    force_residency_derived_resident_count = count_lines_containing(
        force_residency_lines, "derivedBuffersResident=true"
    )
    force_residency_derived_reuse_declared_count = count_lines_containing(
        force_residency_lines, "derivedBuffersReused="
    )
    force_residency_derived_reuse_count = count_lines_containing(
        force_residency_lines, "derivedBuffersReused=true"
    )
    force_residency_bounded_only_count = count_lines_containing(
        force_residency_lines, "boundedProofOnly=true"
    )
    force_residency_bounded_declared_count = count_lines_containing(
        force_residency_lines, "boundedProofOnly="
    )
    force_residency_steady_state_declared_count = count_lines_containing(
        force_residency_lines, "steadyStateResidencyReady="
    )
    force_residency_steady_state_false_count = count_lines_containing(
        force_residency_lines, "steadyStateResidencyReady=false"
    )
    force_residency_steady_state_true_count = count_lines_containing(
        force_residency_lines, "steadyStateResidencyReady=true"
    )
    force_residency_freshness_declared_count = count_lines_containing(
        force_residency_lines, "freshnessReady="
    )
    force_residency_freshness_false_count = count_lines_containing(
        force_residency_lines, "freshnessReady=false"
    )
    force_residency_freshness_true_count = count_lines_containing(
        force_residency_lines, "freshnessReady=true"
    )
    force_residency_cadence_declared_count = count_lines_containing(
        force_residency_lines, "cadenceReady="
    )
    force_residency_cadence_false_count = count_lines_containing(
        force_residency_lines, "cadenceReady=false"
    )
    force_residency_cadence_true_count = count_lines_containing(
        force_residency_lines, "cadenceReady=true"
    )
    force_residency_expanded_oracle_declared_count = count_lines_containing(
        force_residency_lines, "expandedOracleComparisonReady="
    )
    force_residency_expanded_oracle_false_count = count_lines_containing(
        force_residency_lines, "expandedOracleComparisonReady=false"
    )
    force_residency_expanded_oracle_true_count = count_lines_containing(
        force_residency_lines, "expandedOracleComparisonReady=true"
    )
    force_residency_provider_ab_declared_count = count_lines_containing(
        force_residency_lines, "liveRecordedProviderAbReady="
    )
    force_residency_provider_ab_false_count = count_lines_containing(
        force_residency_lines, "liveRecordedProviderAbReady=false"
    )
    force_residency_provider_ab_true_count = count_lines_containing(
        force_residency_lines, "liveRecordedProviderAbReady=true"
    )
    force_residency_force_authority_false_count = count_lines_containing(
        force_residency_lines, "forceAuthorityReady=false"
    )
    force_residency_force_authority_true_count = count_lines_containing(
        force_residency_lines, "forceAuthorityReady=true"
    )
    force_residency_runtime_authority_false_count = count_lines_containing(
        force_residency_lines, "runtimeForceAuthority=false"
    )
    force_residency_runtime_authority_true_count = count_lines_containing(
        force_residency_lines, "runtimeForceAuthority=true"
    )
    force_residency_runtime_particle_false_count = count_lines_containing(
        force_residency_lines, "runtimeParticleIntegration=false"
    )
    force_residency_runtime_particle_true_count = count_lines_containing(
        force_residency_lines, "runtimeParticleIntegration=true"
    )
    force_residency_gpu_not_ready_count = count_lines_containing(
        force_residency_lines, "gpuComputeReady=false"
    )
    force_residency_gpu_ready_count = count_lines_containing(
        force_residency_lines, "gpuComputeReady=true"
    )
    force_residency_low_rate_count = count_lines_containing(
        force_residency_lines, "highRateJsonPayload=false"
    )
    force_residency_settings_payload_false_count = count_lines_containing(
        force_residency_lines, "settingsControlPayload=false"
    )
    force_residency_observed_proof_values = marker_int_fields(
        force_residency_lines, "observedResidentProofs"
    )
    force_residency_reused_proof_values = marker_int_fields(
        force_residency_lines, "reusedResidentProofs"
    )
    force_residency_required_proof_values = marker_int_fields(
        force_residency_lines, "requiredResidentProofs"
    )
    force_residency_max_observed_proofs = max(
        force_residency_observed_proof_values, default=0
    )
    force_residency_max_reused_proofs = max(
        force_residency_reused_proof_values, default=0
    )
    force_residency_max_required_proofs = max(
        force_residency_required_proof_values, default=0
    )
    force_residency_freshness_fallback_count = count_lines_containing(
        force_residency_lines, "fallbackReason=gpu-freshness-not-proven"
    )
    force_residency_expanded_oracle_fallback_count = count_lines_containing(
        force_residency_lines,
        "fallbackReason=gpu-expanded-oracle-comparison-not-proven",
    )
    force_residency_provider_ab_fallback_count = count_lines_containing(
        force_residency_lines,
        "fallbackReason=gpu-live-recorded-provider-ab-not-proven",
    )
    force_residency_gpu_selected_count = count_lines_containing(
        force_residency_lines, "fallbackReason=gpu-force-authority-selected"
    )
    if force_residency_lines:
        if force_residency_candidate_ready_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not keep forceAuthorityCandidateReady=true"
            )
        if force_residency_gpu_candidate_ready_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not keep gpuComputeCandidateReady=true"
            )
        if force_residency_single_authority_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not preserve single authority")
        if force_residency_slot_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report forceAuthoritySlotCount=1"
            )
        if force_residency_active_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report activeForceAuthorityCount=1"
            )
        if force_residency_profile_required_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not require explicit profile selection"
            )
        if force_residency_profile_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare profileGateSatisfied")
        if thresholds.require_gpu_force_runtime_authority:
            if (
                force_residency_selection_blocked_count
                + force_residency_selection_permitted_count
                != len(force_residency_lines)
            ):
                issues.append(
                    "GPU force authority residency did not declare runtime selection state"
                )
            if force_residency_selection_permitted_count < 1:
                issues.append(
                    "GPU force authority residency never permitted runtime selection"
                )
            if force_residency_active_kind_declared_count != len(force_residency_lines):
                issues.append(
                    "GPU force authority residency did not declare active force authority kind"
                )
            if force_residency_active_gpu_kind_count < 1:
                issues.append(
                    "GPU force authority residency never selected the GPU-backed authority kind"
                )
            if force_residency_active_source_declared_count != len(force_residency_lines):
                issues.append(
                    "GPU force authority residency did not declare the active authority source"
                )
            if force_residency_active_gpu_source_count < 1:
                issues.append(
                    "GPU force authority residency never selected the GPU runtime selector"
                )
            if (
                force_residency_active_preserved_declared_count
                != len(force_residency_lines)
            ):
                issues.append(
                    "GPU force authority residency did not declare active authority preservation"
                )
            if force_residency_active_gpu_preserved_count < 1:
                issues.append(
                    "GPU force authority residency never preserved the GPU-backed runtime"
                )
            if (
                force_residency_not_selected_count + force_residency_selected_count
                != len(force_residency_lines)
            ):
                issues.append(
                    "GPU force authority residency did not declare candidate selection"
                )
            if force_residency_selected_count < 1:
                issues.append("GPU force authority residency never selected the candidate")
            if (
                force_residency_not_promoted_count + force_residency_promoted_count
                != len(force_residency_lines)
            ):
                issues.append(
                    "GPU force authority residency did not declare candidate promotion"
                )
            if force_residency_promoted_count < 1:
                issues.append("GPU force authority residency never promoted the candidate")
        else:
            if force_residency_selection_blocked_count != len(force_residency_lines):
                issues.append("GPU force authority residency permitted runtime selection")
            if force_residency_active_kind_count != len(force_residency_lines):
                issues.append("GPU force authority residency did not keep Matter CPU active kind")
            if force_residency_active_source_count != len(force_residency_lines):
                issues.append(
                    "GPU force authority residency did not declare the active authority source"
                )
            if force_residency_active_preserved_count != len(force_residency_lines):
                issues.append(
                    "GPU force authority residency did not preserve Matter CPU as active authority"
                )
            if force_residency_not_selected_count != len(force_residency_lines):
                issues.append("GPU force authority residency selected the candidate")
            if force_residency_not_promoted_count != len(force_residency_lines):
                issues.append("GPU force authority residency promoted the candidate")
        if force_residency_oracle_authority_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare the Matter CPU oracle authority"
            )
        if force_residency_tracker_source_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report the residency tracker source"
            )
        if force_residency_reused_proofs_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare reusedResidentProofs")
        if force_residency_continuity_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare residency continuity readiness"
            )
        if force_residency_continuity_not_broken_count != len(force_residency_lines):
            issues.append("GPU force authority residency reported a continuity break")
        if force_residency_continuity_breaks_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare continuity break count"
            )
        if force_residency_source_generation_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare source mesh buffer generation"
            )
        if force_residency_source_generation_matched_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not match source mesh buffer generation"
            )
        if force_residency_derived_generation_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare derived buffer generation"
            )
        if force_residency_derived_generation_matched_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not match derived buffer generation"
            )
        if force_residency_queue_monotonic_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep submit serials monotonic")
        if force_residency_fence_monotonic_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep fence serials monotonic")
        if force_residency_fallback_ready_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep Matter CPU fallback ready")
        if force_residency_fallback_authority_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare fallback authority")
        if force_residency_fallback_reason_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare fallback reason")
        if force_residency_rollback_policy_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not report Matter CPU rollback policy")
        if force_residency_source_resident_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report resident source mesh buffers"
            )
        if force_residency_source_reuse_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare source buffer reuse")
        if force_residency_derived_resident_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not report resident derived buffers"
            )
        if force_residency_derived_reuse_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare derived buffer reuse")
        if force_residency_bounded_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare boundedProofOnly")
        if force_residency_steady_state_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare steady-state readiness"
            )
        if force_residency_freshness_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare freshness readiness")
        if force_residency_cadence_declared_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not declare cadence readiness")
        if force_residency_expanded_oracle_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare expanded oracle comparison readiness"
            )
        if force_residency_provider_ab_declared_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not declare live/recorded A/B readiness"
            )
        if thresholds.require_gpu_force_runtime_authority:
            if (
                force_residency_force_authority_false_count
                + force_residency_force_authority_true_count
                != len(force_residency_lines)
            ):
                issues.append("GPU force authority residency did not declare forceAuthorityReady")
            if force_residency_force_authority_true_count < 1:
                issues.append("GPU force authority residency never reached forceAuthorityReady=true")
            if (
                force_residency_runtime_authority_false_count
                + force_residency_runtime_authority_true_count
                != len(force_residency_lines)
            ):
                issues.append("GPU force authority residency did not declare runtimeForceAuthority")
            if force_residency_runtime_authority_true_count < 1:
                issues.append(
                    "GPU force authority residency never reached runtimeForceAuthority=true"
                )
            if (
                force_residency_runtime_particle_false_count
                + force_residency_runtime_particle_true_count
                != len(force_residency_lines)
            ):
                issues.append(
                    "GPU force authority residency did not declare runtimeParticleIntegration"
                )
            if force_residency_runtime_particle_true_count < 1:
                issues.append(
                    "GPU force authority residency never reached runtimeParticleIntegration=true"
                )
            if (
                force_residency_gpu_not_ready_count + force_residency_gpu_ready_count
                != len(force_residency_lines)
            ):
                issues.append("GPU force authority residency did not declare gpuComputeReady")
            if force_residency_gpu_ready_count < 1:
                issues.append("GPU force authority residency never reached gpuComputeReady=true")
        else:
            if force_residency_force_authority_false_count != len(force_residency_lines):
                issues.append("GPU force authority residency did not keep forceAuthorityReady=false")
            if force_residency_runtime_authority_false_count != len(force_residency_lines):
                issues.append(
                    "GPU force authority residency did not keep runtimeForceAuthority=false"
                )
            if force_residency_runtime_particle_false_count != len(force_residency_lines):
                issues.append(
                    "GPU force authority residency did not keep runtimeParticleIntegration=false"
                )
            if force_residency_gpu_not_ready_count != len(force_residency_lines):
                issues.append("GPU force authority residency did not keep gpuComputeReady=false")
        if force_residency_low_rate_count != len(force_residency_lines):
            issues.append("GPU force authority residency did not keep highRateJsonPayload=false")
        if force_residency_settings_payload_false_count != len(force_residency_lines):
            issues.append(
                "GPU force authority residency did not keep settingsControlPayload=false"
            )
    if thresholds.require_gpu_force_profile_enabled:
        if not force_gate_lines:
            issues.append("GPU force profile was required but no force-authority gate was present")
        elif force_gate_profile_satisfied_count != len(force_gate_lines):
            issues.append(
                "GPU force authority gate did not satisfy the explicit GPU profile gate"
            )
        if not force_residency_lines:
            issues.append(
                "GPU force profile was required but no force-authority residency marker was present"
            )
        elif (
            force_residency_profile_declared_count != len(force_residency_lines)
            or count_lines_containing(force_residency_lines, "profileGateSatisfied=true")
            != len(force_residency_lines)
            or count_lines_containing(
                force_residency_lines, "gpuForceAuthorityProfileEnabled=true"
            )
            != len(force_residency_lines)
        ):
            issues.append(
                "GPU force authority residency did not satisfy the explicit GPU profile gate"
            )
    if thresholds.min_force_residency_observed_proofs > 0:
        if force_residency_max_observed_proofs < thresholds.min_force_residency_observed_proofs:
            issues.append(
                "GPU force authority residency observedResidentProofs max "
                f"{force_residency_max_observed_proofs} < "
                f"{thresholds.min_force_residency_observed_proofs}"
            )
    if thresholds.min_force_residency_reused_proofs > 0:
        if force_residency_max_reused_proofs < thresholds.min_force_residency_reused_proofs:
            issues.append(
                "GPU force authority residency reusedResidentProofs max "
                f"{force_residency_max_reused_proofs} < "
                f"{thresholds.min_force_residency_reused_proofs}"
            )
    if thresholds.require_gpu_force_steady_state_fallback:
        if not force_residency_lines:
            issues.append(
                "steady-state GPU force fallback was required but no residency marker was present"
            )
        if force_residency_steady_state_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach steadyStateResidencyReady=true"
            )
        if force_residency_cadence_true_count < 1:
            issues.append("GPU force authority residency did not reach cadenceReady=true")
        if force_residency_freshness_true_count != 0:
            issues.append("GPU force authority residency claimed freshnessReady=true too early")
        if force_residency_expanded_oracle_true_count != 0:
            issues.append(
                "GPU force authority residency claimed expandedOracleComparisonReady=true too early"
            )
        if force_residency_provider_ab_true_count != 0:
            issues.append(
                "GPU force authority residency claimed liveRecordedProviderAbReady=true too early"
            )
        if force_residency_freshness_fallback_count < 1:
            issues.append(
                "GPU force authority residency did not fall back for gpu-freshness-not-proven"
            )
        if force_residency_selection_blocked_count != len(force_residency_lines):
            issues.append("GPU force authority steady-state fallback permitted runtime selection")
        if force_residency_active_kind_count != len(force_residency_lines):
            issues.append("GPU force authority steady-state fallback did not keep Matter CPU active")
    if thresholds.require_gpu_force_freshness:
        allow_runtime_warmup_misses = thresholds.require_gpu_force_runtime_authority
        if not force_freshness_lines:
            issues.append("GPU force freshness was required but no freshness marker was present")
        if force_freshness_ready_count < 1:
            issues.append("GPU force freshness evidence did not reach freshnessReady=true")
        if force_freshness_not_ready_count != 0 and not allow_runtime_warmup_misses:
            issues.append("GPU force freshness evidence still contained freshnessReady=false")
        if force_freshness_source_match_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep sourceIdMatched=true")
        if force_freshness_candidate_not_future_count != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not keep candidateNotFuture=true")
        if force_freshness_cadence_ready_count < 1:
            issues.append("GPU force freshness evidence did not show cadenceReady=true")
        if len(force_freshness_lag_values) != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not declare numeric sourceFrameLag")
        if len(force_freshness_max_lag_values) != len(force_freshness_lines):
            issues.append("GPU force freshness evidence did not declare maxSourceFrameLag")
        if (
            force_freshness_lag_values
            and force_freshness_max_lag_values
            and force_freshness_max_lag_observed > force_freshness_max_lag_allowed
            and not allow_runtime_warmup_misses
        ):
            issues.append(
                "GPU force freshness sourceFrameLag max "
                f"{force_freshness_max_lag_observed} > allowed "
                f"{force_freshness_max_lag_allowed}"
            )
        if force_residency_freshness_true_count < 1:
            issues.append("GPU force authority residency did not consume freshnessReady=true")
    if thresholds.require_gpu_force_fresh_expanded_oracle_fallback:
        if not force_residency_lines:
            issues.append(
                "fresh GPU force fallback was required but no residency marker was present"
            )
        if force_residency_steady_state_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach steadyStateResidencyReady=true"
            )
        if force_residency_freshness_true_count < 1:
            issues.append("GPU force authority residency did not reach freshnessReady=true")
        if force_residency_cadence_true_count < 1:
            issues.append("GPU force authority residency did not reach cadenceReady=true")
        if force_residency_expanded_oracle_true_count != 0:
            issues.append(
                "GPU force authority residency claimed expandedOracleComparisonReady=true too early"
            )
        if force_residency_provider_ab_true_count != 0:
            issues.append(
                "GPU force authority residency claimed liveRecordedProviderAbReady=true too early"
            )
        if force_residency_expanded_oracle_fallback_count < 1:
            issues.append(
                "GPU force authority residency did not fall back for "
                "gpu-expanded-oracle-comparison-not-proven"
            )
        if force_residency_selection_blocked_count != len(force_residency_lines):
            issues.append("GPU force authority fresh fallback permitted runtime selection")
        if force_residency_active_kind_count != len(force_residency_lines):
            issues.append("GPU force authority fresh fallback did not keep Matter CPU active")
    if thresholds.require_gpu_force_expanded_oracle_provider_ab_fallback:
        if not field_particle_force_lines:
            issues.append(
                "expanded GPU force oracle fallback was required but no particle-force "
                "proof marker was present"
            )
        if field_particle_force_max_sample_count < expanded_force_oracle_sample_count:
            issues.append(
                "GPU field particle-force proof max sampleCount "
                f"{field_particle_force_max_sample_count} < "
                f"{expanded_force_oracle_sample_count}"
            )
        if not force_residency_lines:
            issues.append(
                "expanded GPU force oracle fallback was required but no residency marker was present"
            )
        if force_residency_steady_state_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach steadyStateResidencyReady=true"
            )
        if force_residency_freshness_true_count < 1:
            issues.append("GPU force authority residency did not reach freshnessReady=true")
        if force_residency_cadence_true_count < 1:
            issues.append("GPU force authority residency did not reach cadenceReady=true")
        if force_residency_expanded_oracle_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach expandedOracleComparisonReady=true"
            )
        if force_residency_provider_ab_true_count != 0:
            issues.append(
                "GPU force authority residency claimed liveRecordedProviderAbReady=true too early"
            )
        if force_residency_provider_ab_fallback_count < 1:
            issues.append(
                "GPU force authority residency did not fall back for "
                "gpu-live-recorded-provider-ab-not-proven"
            )
        if force_residency_selection_blocked_count != len(force_residency_lines):
            issues.append("GPU force expanded oracle fallback permitted runtime selection")
        if force_residency_active_kind_count != len(force_residency_lines):
            issues.append(
                "GPU force expanded oracle fallback did not keep Matter CPU active"
            )
    if thresholds.require_gpu_force_runtime_authority:
        if not field_particle_force_lines:
            issues.append(
                "runtime GPU force authority was required but no particle-force proof marker was present"
            )
        if field_particle_force_max_sample_count < expanded_force_oracle_sample_count:
            issues.append(
                "GPU field particle-force proof max sampleCount "
                f"{field_particle_force_max_sample_count} < "
                f"{expanded_force_oracle_sample_count}"
            )
        if not force_residency_lines:
            issues.append(
                "runtime GPU force authority was required but no residency marker was present"
            )
        if force_residency_steady_state_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach steadyStateResidencyReady=true"
            )
        if force_residency_freshness_true_count < 1:
            issues.append("GPU force authority residency did not reach freshnessReady=true")
        if force_residency_cadence_true_count < 1:
            issues.append("GPU force authority residency did not reach cadenceReady=true")
        if force_residency_expanded_oracle_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach expandedOracleComparisonReady=true"
            )
        if force_residency_provider_ab_true_count < 1:
            issues.append(
                "GPU force authority residency did not reach liveRecordedProviderAbReady=true"
            )
        if force_residency_selection_permitted_count < 1:
            issues.append(
                "GPU force authority residency did not reach runtimeSelectionPermitted=true"
            )
        if force_residency_active_gpu_kind_count < 1:
            issues.append(
                "GPU force authority residency did not select gpu-dense-sdf-field-particle-force"
            )
        if force_residency_selected_count < 1:
            issues.append("GPU force authority residency did not select the candidate")
        if force_residency_promoted_count < 1:
            issues.append("GPU force authority residency did not promote the candidate")
        if force_residency_gpu_selected_count < 1:
            issues.append(
                "GPU force authority residency did not report fallbackReason=gpu-force-authority-selected"
            )
        if force_residency_force_authority_true_count < 1:
            issues.append("GPU force authority residency did not set forceAuthorityReady=true")
        if force_residency_runtime_authority_true_count < 1:
            issues.append("GPU force authority residency did not set runtimeForceAuthority=true")
        if force_residency_runtime_particle_true_count < 1:
            issues.append(
                "GPU force authority residency did not set runtimeParticleIntegration=true"
            )
        if force_residency_gpu_ready_count < 1:
            issues.append("GPU force authority residency did not set gpuComputeReady=true")
        if force_residency_fallback_ready_count != len(force_residency_lines):
            issues.append(
                "GPU force runtime authority did not keep Matter CPU fallback ready"
            )
    summary = {
        "force_candidate_line_count": len(force_candidate_lines),
        "force_candidate_ready_count": force_candidate_ready_count,
        "force_candidate_gpu_ready_count": force_candidate_gpu_ready_count,
        "force_candidate_single_authority_count": force_candidate_single_authority_count,
        "force_candidate_not_selected_count": force_candidate_not_selected_count,
        "force_candidate_not_promoted_count": force_candidate_not_promoted_count,
        "force_candidate_active_unchanged_count": force_candidate_active_unchanged_count,
        "force_candidate_force_authority_false_count": (
            force_candidate_force_authority_false_count
        ),
        "force_candidate_runtime_authority_false_count": (
            force_candidate_runtime_authority_false_count
        ),
        "force_candidate_runtime_particle_false_count": (
            force_candidate_runtime_particle_false_count
        ),
        "force_candidate_gpu_not_ready_count": force_candidate_gpu_not_ready_count,
        "force_candidate_low_rate_count": force_candidate_low_rate_count,
        "force_candidate_settings_payload_false_count": (
            force_candidate_settings_payload_false_count
        ),
        "force_gate_line_count": len(force_gate_lines),
        "force_gate_candidate_ready_count": force_gate_candidate_ready_count,
        "force_gate_gpu_candidate_ready_count": force_gate_gpu_candidate_ready_count,
        "force_gate_single_authority_count": force_gate_single_authority_count,
        "force_gate_slot_count": force_gate_slot_count,
        "force_gate_active_count": force_gate_active_count,
        "force_gate_profile_required_count": force_gate_profile_required_count,
        "force_gate_profile_declared_count": force_gate_profile_declared_count,
        "force_gate_profile_satisfied_count": force_gate_profile_satisfied_count,
        "force_gate_profile_unsatisfied_count": force_gate_profile_unsatisfied_count,
        "force_gate_selection_blocked_count": force_gate_selection_blocked_count,
        "force_gate_profile_known_count": force_gate_profile_known_count,
        "force_gate_profile_state_declared_count": force_gate_profile_state_declared_count,
        "force_gate_profile_enabled_count": force_gate_profile_enabled_count,
        "force_gate_profile_disabled_count": force_gate_profile_disabled_count,
        "force_gate_active_kind_count": force_gate_active_kind_count,
        "force_gate_candidate_eligible_count": force_gate_candidate_eligible_count,
        "force_gate_not_selected_count": force_gate_not_selected_count,
        "force_gate_not_promoted_count": force_gate_not_promoted_count,
        "force_gate_active_unchanged_count": force_gate_active_unchanged_count,
        "force_gate_fallback_ready_count": force_gate_fallback_ready_count,
        "force_gate_rollback_policy_count": force_gate_rollback_policy_count,
        "force_gate_force_authority_false_count": force_gate_force_authority_false_count,
        "force_gate_runtime_authority_false_count": (
            force_gate_runtime_authority_false_count
        ),
        "force_gate_runtime_particle_false_count": force_gate_runtime_particle_false_count,
        "force_gate_gpu_not_ready_count": force_gate_gpu_not_ready_count,
        "force_gate_low_rate_count": force_gate_low_rate_count,
        "force_gate_settings_payload_false_count": (
            force_gate_settings_payload_false_count
        ),
        "force_freshness_line_count": len(force_freshness_lines),
        "force_freshness_ready_count": force_freshness_ready_count,
        "force_freshness_not_ready_count": force_freshness_not_ready_count,
        "force_freshness_source_match_count": force_freshness_source_match_count,
        "force_freshness_candidate_not_future_count": (
            force_freshness_candidate_not_future_count
        ),
        "force_freshness_cadence_ready_count": force_freshness_cadence_ready_count,
        "force_freshness_runtime_authority_false_count": (
            force_freshness_runtime_authority_false_count
        ),
        "force_freshness_gpu_not_ready_count": force_freshness_gpu_not_ready_count,
        "force_freshness_low_rate_count": force_freshness_low_rate_count,
        "force_freshness_settings_payload_false_count": (
            force_freshness_settings_payload_false_count
        ),
        "force_freshness_max_lag_observed": force_freshness_max_lag_observed,
        "force_freshness_max_lag_allowed": force_freshness_max_lag_allowed,
        "force_residency_line_count": len(force_residency_lines),
        "force_residency_candidate_ready_count": force_residency_candidate_ready_count,
        "force_residency_gpu_candidate_ready_count": (
            force_residency_gpu_candidate_ready_count
        ),
        "force_residency_single_authority_count": force_residency_single_authority_count,
        "force_residency_slot_count": force_residency_slot_count,
        "force_residency_active_count": force_residency_active_count,
        "force_residency_profile_required_count": force_residency_profile_required_count,
        "force_residency_profile_declared_count": force_residency_profile_declared_count,
        "force_residency_selection_blocked_count": force_residency_selection_blocked_count,
        "force_residency_selection_permitted_count": (
            force_residency_selection_permitted_count
        ),
        "force_residency_active_kind_count": force_residency_active_kind_count,
        "force_residency_active_gpu_kind_count": force_residency_active_gpu_kind_count,
        "force_residency_active_kind_declared_count": (
            force_residency_active_kind_declared_count
        ),
        "force_residency_active_source_count": force_residency_active_source_count,
        "force_residency_active_gpu_source_count": force_residency_active_gpu_source_count,
        "force_residency_active_source_declared_count": (
            force_residency_active_source_declared_count
        ),
        "force_residency_oracle_authority_count": force_residency_oracle_authority_count,
        "force_residency_active_preserved_count": force_residency_active_preserved_count,
        "force_residency_active_gpu_preserved_count": (
            force_residency_active_gpu_preserved_count
        ),
        "force_residency_active_preserved_declared_count": (
            force_residency_active_preserved_declared_count
        ),
        "force_residency_not_selected_count": force_residency_not_selected_count,
        "force_residency_selected_count": force_residency_selected_count,
        "force_residency_not_promoted_count": force_residency_not_promoted_count,
        "force_residency_promoted_count": force_residency_promoted_count,
        "force_residency_fallback_ready_count": force_residency_fallback_ready_count,
        "force_residency_fallback_authority_count": force_residency_fallback_authority_count,
        "force_residency_fallback_reason_count": force_residency_fallback_reason_count,
        "force_residency_rollback_policy_count": force_residency_rollback_policy_count,
        "force_residency_source_resident_count": force_residency_source_resident_count,
        "force_residency_source_reuse_declared_count": (
            force_residency_source_reuse_declared_count
        ),
        "force_residency_source_reuse_count": force_residency_source_reuse_count,
        "force_residency_derived_resident_count": force_residency_derived_resident_count,
        "force_residency_derived_reuse_declared_count": (
            force_residency_derived_reuse_declared_count
        ),
        "force_residency_derived_reuse_count": force_residency_derived_reuse_count,
        "force_residency_bounded_only_count": force_residency_bounded_only_count,
        "force_residency_bounded_declared_count": (
            force_residency_bounded_declared_count
        ),
        "force_residency_steady_state_declared_count": (
            force_residency_steady_state_declared_count
        ),
        "force_residency_steady_state_false_count": (
            force_residency_steady_state_false_count
        ),
        "force_residency_steady_state_true_count": force_residency_steady_state_true_count,
        "force_residency_freshness_declared_count": (
            force_residency_freshness_declared_count
        ),
        "force_residency_freshness_false_count": force_residency_freshness_false_count,
        "force_residency_freshness_true_count": force_residency_freshness_true_count,
        "force_residency_cadence_declared_count": force_residency_cadence_declared_count,
        "force_residency_cadence_false_count": force_residency_cadence_false_count,
        "force_residency_cadence_true_count": force_residency_cadence_true_count,
        "force_residency_expanded_oracle_declared_count": (
            force_residency_expanded_oracle_declared_count
        ),
        "force_residency_expanded_oracle_false_count": (
            force_residency_expanded_oracle_false_count
        ),
        "force_residency_expanded_oracle_true_count": (
            force_residency_expanded_oracle_true_count
        ),
        "force_residency_provider_ab_declared_count": (
            force_residency_provider_ab_declared_count
        ),
        "force_residency_provider_ab_false_count": force_residency_provider_ab_false_count,
        "force_residency_provider_ab_true_count": force_residency_provider_ab_true_count,
        "force_residency_force_authority_false_count": (
            force_residency_force_authority_false_count
        ),
        "force_residency_force_authority_true_count": (
            force_residency_force_authority_true_count
        ),
        "force_residency_runtime_authority_false_count": (
            force_residency_runtime_authority_false_count
        ),
        "force_residency_runtime_authority_true_count": (
            force_residency_runtime_authority_true_count
        ),
        "force_residency_runtime_particle_false_count": (
            force_residency_runtime_particle_false_count
        ),
        "force_residency_runtime_particle_true_count": (
            force_residency_runtime_particle_true_count
        ),
        "force_residency_gpu_not_ready_count": force_residency_gpu_not_ready_count,
        "force_residency_gpu_ready_count": force_residency_gpu_ready_count,
        "force_residency_low_rate_count": force_residency_low_rate_count,
        "force_residency_settings_payload_false_count": (
            force_residency_settings_payload_false_count
        ),
        "force_residency_max_observed_proofs": force_residency_max_observed_proofs,
        "force_residency_max_reused_proofs": force_residency_max_reused_proofs,
        "force_residency_max_required_proofs": force_residency_max_required_proofs,
        "force_residency_freshness_fallback_count": (
            force_residency_freshness_fallback_count
        ),
        "force_residency_expanded_oracle_fallback_count": (
            force_residency_expanded_oracle_fallback_count
        ),
        "force_residency_provider_ab_fallback_count": (
            force_residency_provider_ab_fallback_count
        ),
        "force_residency_gpu_selected_count": force_residency_gpu_selected_count,
    }
    return ForceAuthorityEvidenceResult(issues=issues, summary=summary)
