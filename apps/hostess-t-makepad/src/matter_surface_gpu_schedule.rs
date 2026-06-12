//! Hostess-local scheduling policy for Matter GPU proof evidence.
//!
//! This module only decides when Hostess asks the existing Makepad GPU proof
//! adapters to run. It does not own Matter semantics, GPU kernels, or high-rate
//! hand/mesh/field payloads.

use crate::matter_surface_source_selection::MatterSurfaceSourceSelection;
use crate::runtime_settings::marker_token;

pub(crate) const MATTER_SURFACE_LIVE_GPU_PROBE_MIN_CADENCE_FRAMES: u64 = 24;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MatterSurfaceGpuProofSchedule {
    pub(crate) min_cadence_frames: u64,
    pub(crate) source_aware_live_first_proof: bool,
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
            }
        } else {
            Self {
                min_cadence_frames: default_min_cadence_frames,
                source_aware_live_first_proof: false,
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
        frame_count: u64,
        xr_update_count: u64,
        draw_event_count: u64,
    ) -> String {
        format!(
            "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_SCHEDULE schema=rusty.hostess.makepad.matter_surface_gpu_proof_schedule.v1 phase={} status=ready selectedMode={} minCadenceFrames={} defaultMinCadenceFrames={} liveMinCadenceFrames={} frameCount={} xrUpdateCount={} drawEventCount={} liveOpenXrHandProviderSelected={} sourceAwareLiveFirstProof={} cadenceGate=source-aware-first-proof gpuAdapterBoundaryUnchanged=true highRateJsonPayload=false",
            marker_token(phase),
            marker_token(selection.mode().marker_value()),
            self.min_cadence_frames,
            default_min_cadence_frames,
            MATTER_SURFACE_LIVE_GPU_PROBE_MIN_CADENCE_FRAMES,
            frame_count,
            xr_update_count,
            draw_event_count,
            selection.mode().uses_live_openxr_hand(),
            self.source_aware_live_first_proof,
        )
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
        assert!(!schedule.cadence_ready(true, 23, 24, 24));
        assert!(schedule.cadence_ready(true, 24, 24, 24));
    }

    #[test]
    fn marker_records_boundary_and_gate_policy() {
        let selection = MatterSurfaceSourceSelection::from_value("right", "test");
        let schedule = MatterSurfaceGpuProofSchedule::for_source_selection(&selection, 900);
        let marker = schedule.marker_line("unit-test", &selection, 900, 24, 24, 24);

        assert!(marker.contains("selectedMode=live-openxr-hand-right"));
        assert!(marker.contains("minCadenceFrames=24"));
        assert!(marker.contains("defaultMinCadenceFrames=900"));
        assert!(marker.contains("sourceAwareLiveFirstProof=true"));
        assert!(marker.contains("gpuAdapterBoundaryUnchanged=true"));
        assert!(marker.contains("highRateJsonPayload=false"));
    }
}
