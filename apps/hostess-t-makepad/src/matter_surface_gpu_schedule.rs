//! Hostess-local scheduling policy for Matter GPU proof evidence.
//!
//! This module only decides when Hostess asks the existing Makepad GPU proof
//! adapters to run. It does not own Matter semantics, GPU kernels, or high-rate
//! hand/mesh/field payloads.

use crate::matter_surface_source_selection::MatterSurfaceSourceSelection;
use crate::runtime_settings::marker_token;
use rusty_quest_makepad_camera_shell::{
    QuestMakepadGpuForceAuthorityRuntimeReadiness,
    QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY_REQUIRED_PROOFS,
};

pub(crate) const MATTER_SURFACE_LIVE_GPU_PROBE_MIN_CADENCE_FRAMES: u64 = 24;
pub(crate) const MATTER_SURFACE_LIVE_OBSERVE_INTERVAL_SECONDS: f64 = 1.0 / 15.0;
pub(crate) const MATTER_SURFACE_LIVE_SOURCE_STEP_INTERVAL_SECONDS: f64 = 1.0 / 45.0;
pub(crate) const MATTER_SURFACE_DEFAULT_MESH_SDF_PROBE_TARGET_MARKERS: usize = 1;
pub(crate) const MATTER_SURFACE_STEADY_STATE_MESH_SDF_PROBE_TARGET_MARKERS: usize =
    QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY_REQUIRED_PROOFS + 1;
pub(crate) const MATTER_SURFACE_RECORDED_MESH_SDF_PROBE_TARGET_MARKERS: usize =
    MATTER_SURFACE_STEADY_STATE_MESH_SDF_PROBE_TARGET_MARKERS;
pub(crate) const MATTER_SURFACE_LIVE_MESH_SDF_PROBE_TARGET_MARKERS: usize =
    MATTER_SURFACE_STEADY_STATE_MESH_SDF_PROBE_TARGET_MARKERS;
pub(crate) const MATTER_SURFACE_GPU_FORCE_FRESHNESS_MAX_SOURCE_FRAME_LAG: usize = 4;

pub(crate) fn matter_surface_step_interval_seconds(
    selection: &MatterSurfaceSourceSelection,
    default_step_interval_seconds: f64,
) -> f64 {
    if selection.mode().uses_live_openxr_hand() {
        MATTER_SURFACE_LIVE_SOURCE_STEP_INTERVAL_SECONDS
    } else {
        default_step_interval_seconds
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MatterSurfaceGpuProofSchedule {
    pub(crate) min_cadence_frames: u64,
    pub(crate) source_aware_live_first_proof: bool,
    pub(crate) blocking_gpu_diagnostics: bool,
    pub(crate) mesh_sdf_probe_target_markers: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct MatterSurfaceGpuForceFreshnessEvidence {
    candidate_source_id: String,
    adopted_source_id: String,
    candidate_source_frame_index: usize,
    adopted_source_frame_index: Option<usize>,
    max_source_frame_lag: usize,
}

impl MatterSurfaceGpuForceFreshnessEvidence {
    pub(crate) fn from_source_frame_adoption(
        candidate_source_id: &str,
        candidate_source_frame_index: usize,
        adopted_source_id: &str,
        adopted_source_frame_index: Option<usize>,
        max_source_frame_lag: usize,
    ) -> Self {
        Self {
            candidate_source_id: candidate_source_id.to_owned(),
            adopted_source_id: adopted_source_id.to_owned(),
            candidate_source_frame_index,
            adopted_source_frame_index,
            max_source_frame_lag,
        }
    }

    pub(crate) fn source_id_matched(&self) -> bool {
        self.candidate_source_id == self.adopted_source_id
    }

    pub(crate) fn candidate_not_future(&self) -> bool {
        self.adopted_source_frame_index
            .is_some_and(|adopted| adopted >= self.candidate_source_frame_index)
    }

    pub(crate) fn source_frame_lag(&self) -> Option<usize> {
        self.adopted_source_frame_index
            .filter(|adopted| *adopted >= self.candidate_source_frame_index)
            .map(|adopted| adopted - self.candidate_source_frame_index)
    }

    pub(crate) fn freshness_ready(&self) -> bool {
        self.source_id_matched()
            && self
                .source_frame_lag()
                .is_some_and(|lag| lag <= self.max_source_frame_lag)
    }

    pub(crate) fn marker_line(
        &self,
        phase: &str,
        cadence_ready: bool,
        selection: &MatterSurfaceSourceSelection,
    ) -> String {
        let source_frame_lag = self
            .source_frame_lag()
            .map_or_else(|| "none".to_string(), |lag| lag.to_string());
        let adopted_source_frame_index = self
            .adopted_source_frame_index
            .map_or_else(|| "none".to_string(), |index| index.to_string());
        format!(
            "RUSTY_HOSTESS_MAKEPAD_GPU_FORCE_FRESHNESS schema=rusty.hostess.makepad.gpu_force_freshness.v1 phase={} status={} selectedMode={} candidateSourceId={} adoptedSourceId={} candidateSourceFrameIndex={} adoptedSourceFrameIndex={} sourceFrameLag={} maxSourceFrameLag={} sourceIdMatched={} candidateNotFuture={} cadenceReady={} freshnessReady={} evidenceSource=hostess-adopted-matter-source-frame gpuAdapterBoundaryUnchanged=true runtimeForceAuthority=false gpuComputeReady=false highRateJsonPayload=false settingsControlPayload=false",
            marker_token(phase),
            if self.freshness_ready() {
                "ready"
            } else {
                "not-ready"
            },
            marker_token(selection.mode().marker_value()),
            marker_token(&self.candidate_source_id),
            marker_token(&self.adopted_source_id),
            self.candidate_source_frame_index,
            adopted_source_frame_index,
            source_frame_lag,
            self.max_source_frame_lag,
            self.source_id_matched(),
            self.candidate_not_future(),
            cadence_ready,
            self.freshness_ready(),
        )
    }
}

impl MatterSurfaceGpuProofSchedule {
    pub(crate) fn for_source_selection(
        selection: &MatterSurfaceSourceSelection,
        default_min_cadence_frames: u64,
    ) -> Self {
        if selection.mode().uses_live_openxr_hand() {
            Self {
                min_cadence_frames: MATTER_SURFACE_LIVE_GPU_PROBE_MIN_CADENCE_FRAMES,
                source_aware_live_first_proof: true,
                blocking_gpu_diagnostics: false,
                mesh_sdf_probe_target_markers: MATTER_SURFACE_LIVE_MESH_SDF_PROBE_TARGET_MARKERS,
            }
        } else if selection.mode().uses_recorded_hand_replay() {
            Self {
                min_cadence_frames: default_min_cadence_frames,
                source_aware_live_first_proof: false,
                blocking_gpu_diagnostics: false,
                mesh_sdf_probe_target_markers:
                    MATTER_SURFACE_RECORDED_MESH_SDF_PROBE_TARGET_MARKERS,
            }
        } else {
            Self {
                min_cadence_frames: default_min_cadence_frames,
                source_aware_live_first_proof: false,
                blocking_gpu_diagnostics: true,
                mesh_sdf_probe_target_markers: MATTER_SURFACE_DEFAULT_MESH_SDF_PROBE_TARGET_MARKERS,
            }
        }
    }

    pub(crate) fn cadence_ready(
        self,
        cadence_started: bool,
        frame_count: u64,
        xr_update_count: u64,
        draw_event_count: u64,
    ) -> bool {
        cadence_started
            && frame_count >= self.min_cadence_frames
            && xr_update_count >= self.min_cadence_frames
            && draw_event_count >= self.min_cadence_frames
    }

    pub(crate) fn marker_line(
        self,
        phase: &str,
        selection: &MatterSurfaceSourceSelection,
        default_min_cadence_frames: u64,
        default_step_interval_seconds: f64,
        frame_count: u64,
        xr_update_count: u64,
        draw_event_count: u64,
    ) -> String {
        format!(
            "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_SCHEDULE schema=rusty.hostess.makepad.matter_surface_gpu_proof_schedule.v1 phase={} status=ready selectedMode={} minCadenceFrames={} defaultMinCadenceFrames={} liveMinCadenceFrames={} liveObserveIntervalSeconds={:.6} liveSourceStepIntervalSeconds={:.3} defaultStepIntervalSeconds={:.6} frameCount={} xrUpdateCount={} drawEventCount={} liveOpenXrHandProviderSelected={} recordedHandReplaySelected={} liveEquivalentHandInputSelected={} sourceAwareLiveFirstProof={} blockingGpuDiagnostics={} meshSdfProbeTargetMarkers={} cadenceGate=source-aware-first-proof liveSourceObserveCadence=bounded-evidence liveSourceSubmitCadence=authority-freshness-cadence gpuAdapterBoundaryUnchanged=true highRateJsonPayload=false",
            marker_token(phase),
            marker_token(selection.mode().marker_value()),
            self.min_cadence_frames,
            default_min_cadence_frames,
            MATTER_SURFACE_LIVE_GPU_PROBE_MIN_CADENCE_FRAMES,
            MATTER_SURFACE_LIVE_OBSERVE_INTERVAL_SECONDS,
            matter_surface_step_interval_seconds(selection, default_step_interval_seconds),
            default_step_interval_seconds,
            frame_count,
            xr_update_count,
            draw_event_count,
            selection.mode().uses_live_openxr_hand(),
            selection.mode().uses_recorded_hand_replay(),
            selection.mode().uses_live_equivalent_hand_input(),
            self.source_aware_live_first_proof,
            self.blocking_gpu_diagnostics,
            self.mesh_sdf_probe_target_markers,
        )
    }

    pub(crate) fn force_authority_runtime_readiness(
        self,
        cadence_ready: bool,
        freshness_ready: bool,
    ) -> QuestMakepadGpuForceAuthorityRuntimeReadiness {
        QuestMakepadGpuForceAuthorityRuntimeReadiness {
            freshness_ready: freshness_ready && !self.blocking_gpu_diagnostics,
            cadence_ready: cadence_ready && !self.blocking_gpu_diagnostics,
            expanded_oracle_comparison_ready: false,
            live_recorded_provider_ab_ready: false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::matter_surface_source_selection::MatterSurfaceSourceSelection;

    #[test]
    fn recorded_replay_keeps_default_gate() {
        let selection = MatterSurfaceSourceSelection::default();
        let schedule = MatterSurfaceGpuProofSchedule::for_source_selection(&selection, 900);

        assert_eq!(schedule.min_cadence_frames, 900);
        assert!(!schedule.source_aware_live_first_proof);
        assert!(schedule.blocking_gpu_diagnostics);
        assert_eq!(
            schedule.mesh_sdf_probe_target_markers,
            MATTER_SURFACE_DEFAULT_MESH_SDF_PROBE_TARGET_MARKERS
        );
        assert!(!schedule.cadence_ready(true, 899, 900, 900));
        assert!(schedule.cadence_ready(true, 900, 900, 900));
    }

    #[test]
    fn live_openxr_hand_uses_short_source_aware_gate() {
        let selection = MatterSurfaceSourceSelection::from_value("live-openxr-hand-any", "test");
        let schedule = MatterSurfaceGpuProofSchedule::for_source_selection(&selection, 900);

        assert_eq!(
            schedule.min_cadence_frames,
            MATTER_SURFACE_LIVE_GPU_PROBE_MIN_CADENCE_FRAMES
        );
        assert!(schedule.source_aware_live_first_proof);
        assert!(!schedule.blocking_gpu_diagnostics);
        assert_eq!(
            schedule.mesh_sdf_probe_target_markers,
            MATTER_SURFACE_LIVE_MESH_SDF_PROBE_TARGET_MARKERS
        );
        assert!(!schedule.cadence_ready(true, 23, 24, 24));
        assert!(schedule.cadence_ready(true, 24, 24, 24));
        assert_eq!(
            matter_surface_step_interval_seconds(&selection, 1.0 / 12.0),
            MATTER_SURFACE_LIVE_SOURCE_STEP_INTERVAL_SECONDS
        );
        assert!(MATTER_SURFACE_LIVE_OBSERVE_INTERVAL_SECONDS > 0.0);
        assert!(MATTER_SURFACE_LIVE_OBSERVE_INTERVAL_SECONDS < 1.0);
        assert!(MATTER_SURFACE_LIVE_SOURCE_STEP_INTERVAL_SECONDS > 0.0);
        assert!(
            MATTER_SURFACE_LIVE_SOURCE_STEP_INTERVAL_SECONDS
                < MATTER_SURFACE_LIVE_OBSERVE_INTERVAL_SECONDS
        );
    }

    #[test]
    fn explicit_recorded_hand_replay_requests_mesh_sdf_reuse_marker() {
        let selection = MatterSurfaceSourceSelection::from_value("recorded-hand-replay", "test");
        let schedule = MatterSurfaceGpuProofSchedule::for_source_selection(&selection, 900);

        assert_eq!(schedule.min_cadence_frames, 900);
        assert!(!schedule.source_aware_live_first_proof);
        assert!(!schedule.blocking_gpu_diagnostics);
        assert_eq!(
            schedule.mesh_sdf_probe_target_markers,
            MATTER_SURFACE_RECORDED_MESH_SDF_PROBE_TARGET_MARKERS
        );
        assert!(!schedule.cadence_ready(true, 899, 900, 900));
        assert!(schedule.cadence_ready(true, 900, 900, 900));

        let marker = schedule.marker_line("unit-test", &selection, 900, 1.0 / 12.0, 900, 900, 900);
        assert!(marker.contains("selectedMode=recorded-hand-replay"));
        assert!(marker.contains("recordedHandReplaySelected=true"));
        assert!(marker.contains("liveEquivalentHandInputSelected=true"));
        assert!(marker.contains("blockingGpuDiagnostics=false"));
        assert!(marker.contains("meshSdfProbeTargetMarkers=5"));
    }

    #[test]
    fn marker_records_boundary_and_gate_policy() {
        let selection = MatterSurfaceSourceSelection::from_value("right", "test");
        let schedule = MatterSurfaceGpuProofSchedule::for_source_selection(&selection, 900);
        let marker = schedule.marker_line("unit-test", &selection, 900, 1.0 / 12.0, 24, 24, 24);

        assert!(marker.contains("selectedMode=live-openxr-hand-right"));
        assert!(marker.contains("minCadenceFrames=24"));
        assert!(marker.contains("defaultMinCadenceFrames=900"));
        assert!(marker.contains("liveObserveIntervalSeconds=0.066667"));
        assert!(marker.contains("liveSourceStepIntervalSeconds=0.022"));
        assert!(marker.contains("liveSourceObserveCadence=bounded-evidence"));
        assert!(marker.contains("liveSourceSubmitCadence=authority-freshness-cadence"));
        assert!(marker.contains("sourceAwareLiveFirstProof=true"));
        assert!(marker.contains("blockingGpuDiagnostics=false"));
        assert!(marker.contains("meshSdfProbeTargetMarkers=5"));
        assert!(marker.contains("gpuAdapterBoundaryUnchanged=true"));
        assert!(marker.contains("highRateJsonPayload=false"));
    }

    #[test]
    fn steady_state_runtime_readiness_exposes_cadence_but_keeps_future_gates_closed() {
        let selection = MatterSurfaceSourceSelection::from_value("recorded-hand-replay", "test");
        let schedule = MatterSurfaceGpuProofSchedule::for_source_selection(&selection, 900);

        assert_eq!(
            schedule.mesh_sdf_probe_target_markers,
            QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY_REQUIRED_PROOFS + 1
        );

        let readiness = schedule.force_authority_runtime_readiness(true, false);
        assert!(!readiness.freshness_ready);
        assert!(readiness.cadence_ready);
        assert!(!readiness.expanded_oracle_comparison_ready);
        assert!(!readiness.live_recorded_provider_ab_ready);

        let freshness = MatterSurfaceGpuForceFreshnessEvidence::from_source_frame_adoption(
            "recorded-left",
            10,
            "recorded-left",
            Some(13),
            MATTER_SURFACE_GPU_FORCE_FRESHNESS_MAX_SOURCE_FRAME_LAG,
        );
        assert!(freshness.source_id_matched());
        assert!(freshness.candidate_not_future());
        assert_eq!(freshness.source_frame_lag(), Some(3));
        assert!(freshness.freshness_ready());
        let readiness =
            schedule.force_authority_runtime_readiness(true, freshness.freshness_ready());
        assert!(readiness.freshness_ready);
        assert!(readiness.cadence_ready);
        assert!(!readiness.expanded_oracle_comparison_ready);
        assert!(!readiness.live_recorded_provider_ab_ready);
        let marker = freshness.marker_line("unit-test", true, &selection);
        assert!(marker.contains("RUSTY_HOSTESS_MAKEPAD_GPU_FORCE_FRESHNESS"));
        assert!(marker.contains("status=ready"));
        assert!(marker.contains("selectedMode=recorded-hand-replay"));
        assert!(marker.contains("candidateSourceFrameIndex=10"));
        assert!(marker.contains("adoptedSourceFrameIndex=13"));
        assert!(marker.contains("sourceFrameLag=3"));
        assert!(marker.contains("maxSourceFrameLag=4"));
        assert!(marker.contains("sourceIdMatched=true"));
        assert!(marker.contains("candidateNotFuture=true"));
        assert!(marker.contains("freshnessReady=true"));
        assert!(marker.contains("runtimeForceAuthority=false"));
        assert!(marker.contains("gpuComputeReady=false"));

        let stale_freshness = MatterSurfaceGpuForceFreshnessEvidence::from_source_frame_adoption(
            "recorded-left",
            10,
            "recorded-left",
            Some(15),
            4,
        );
        assert_eq!(stale_freshness.source_frame_lag(), Some(5));
        assert!(!stale_freshness.freshness_ready());
        let marker = stale_freshness.marker_line("unit-test", true, &selection);
        assert!(marker.contains("status=not-ready"));
        assert!(marker.contains("sourceFrameLag=5"));
        assert!(marker.contains("freshnessReady=false"));

        let mismatched_source = MatterSurfaceGpuForceFreshnessEvidence::from_source_frame_adoption(
            "recorded-left",
            10,
            "recorded-right",
            Some(10),
            4,
        );
        assert!(!mismatched_source.source_id_matched());
        assert!(!mismatched_source.freshness_ready());
        let marker = mismatched_source.marker_line("unit-test", true, &selection);
        assert!(marker.contains("sourceIdMatched=false"));
        assert!(marker.contains("freshnessReady=false"));
    }
}
