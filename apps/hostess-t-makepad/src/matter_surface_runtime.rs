//! Hostess-local Matter surface worker and evidence plumbing.
//!
//! Matter owns source-frame semantics and CPU truth. Quest-Makepad owns the
//! adapter payloads. This module keeps Hostess as the app-shell evidence
//! consumer without growing the Makepad app root with GPU/worker details.

use crate::live_hand_surface::LiveHandSurfaceWorkerSourceSummary;
use crate::makepad_widgets::makepad_platform::{
    XrGpuF32ForceProbeSample, XR_GPU_F32_FORCE_PROBE_SAMPLES,
};
use crate::makepad_widgets::*;
use crate::matter_particle_texture::MatterParticleTextureFrame;
use crate::matter_surface_gpu::{
    gpu_mesh_sdf_probe_poll_marker_lines, gpu_mesh_sdf_probe_submit,
    gpu_skinning_mesh_probe_poll_marker_line, gpu_skinning_mesh_probe_submit,
    gpu_skinning_probe_poll_marker_line, gpu_skinning_probe_submit,
};
use crate::matter_surface_gpu_schedule::{
    matter_surface_step_interval_seconds, MatterSurfaceGpuForceFreshnessEvidence,
    MatterSurfaceGpuProofSchedule, MATTER_SURFACE_GPU_FORCE_FRESHNESS_MAX_SOURCE_FRAME_LAG,
};
use crate::matter_surface_uniforms::MakepadMatterSurfaceUniforms;
use crate::matter_world_adf_debug::{
    MatterWorldAdfDebugCells, HOSTESS_WORLD_ADF_DEBUG_RENDERER_ID,
};
use crate::matter_world_particle_billboard::MatterWorldParticleBillboardCloud;
use crate::{
    emit_marker_line, marker_f32_token, marker_token, App,
    MATTER_SURFACE_GPU_FORCE_PROBE_TOLERANCE, MATTER_SURFACE_GPU_PROBE_MIN_CADENCE_FRAMES,
    MATTER_SURFACE_GPU_SYNC_PROBE_FRAME_GAP, MATTER_SURFACE_MARKER_LIMIT,
    MATTER_SURFACE_STEP_INTERVAL_SECONDS, MATTER_WORLD_ADF_DEBUG_DRAW_LIMIT_MAX,
    MATTER_WORLD_ADF_DEBUG_DRAW_MARKER_LIMIT, MATTER_WORLD_PARTICLE_CONTENT_LOCAL_CENTER,
    MATTER_WORLD_PARTICLE_DRAW_MARKER_LIMIT, MATTER_WORLD_PARTICLE_START_HEAD_DISTANCE_METERS,
};
use rusty_quest_makepad_camera_shell::{
    MatterSurfaceContactProbe, QuestMakepadGpuComputePreflight, QuestMakepadGpuFieldForceProbe,
    QuestMakepadGpuFieldForceProbeReadback, QuestMakepadGpuOracleComputeProbe,
    QuestMakepadGpuOracleComputeProbeReadback, QuestMakepadGpuResidencyProof,
    QuestMakepadGpuStorageProbe, QuestMakepadGpuStorageProbeReadback,
    QuestMakepadMatterSurfaceWorkerFrame, QuestMakepadMatterSurfaceWorkerOutput,
    QuestMakepadWorldAdfDebugPlacement, QuestMakepadWorldParticlePlacement,
    DEFAULT_WORLD_CONTENT_TARGET_RADIUS, QUEST_MAKEPAD_GPU_COMPUTE_DEFAULT_READBACK_PROBE_COUNT,
    QUEST_MAKEPAD_GPU_STORAGE_PROBE_DEFAULT_BYTES, QUEST_MAKEPAD_GPU_STORAGE_PROBE_DEFAULT_PATTERN,
    QUEST_MAKEPAD_WORLD_ADF_DEBUG_RENDER_MODE,
    QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_ANIMATION_SOURCE,
    QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_REFERENCE,
    QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_RENDERER_ID,
};

#[derive(Clone, Debug, Default)]
pub(crate) struct MatterSurfacePanelOverlayFrame {
    pub(crate) uniforms: MakepadMatterSurfaceUniforms,
    pub(crate) particle_texture: MatterParticleTextureFrame,
}

impl App {
    pub(crate) fn emit_matter_surface_gpu_proof_epoch_marker(
        &self,
        phase: &str,
        source_path: Option<&str>,
        gpu_proof_revision_key: Option<&str>,
    ) {
        emit_marker_line(&format!(
            "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_EPOCH schema=rusty.hostess.makepad.matter_surface_gpu_proof_epoch.v1 phase={} status=applied sourcePath={} gpuProofRevisionKey={} proofCountersReset=true runtimeSettingsReloaded=false replayRuntimeRebuilt=false matterWorkerRestarted=false highRateJsonPayload=false",
            marker_token(phase),
            marker_token(source_path.unwrap_or("none")),
            marker_token(gpu_proof_revision_key.unwrap_or("none")),
        ));
    }

    pub(crate) fn matter_world_particle_placement() -> QuestMakepadWorldParticlePlacement {
        QuestMakepadWorldParticlePlacement::content_local(
            MATTER_WORLD_PARTICLE_CONTENT_LOCAL_CENTER,
            DEFAULT_WORLD_CONTENT_TARGET_RADIUS,
        )
    }

    pub(crate) fn matter_world_adf_debug_placement() -> QuestMakepadWorldAdfDebugPlacement {
        QuestMakepadWorldAdfDebugPlacement::content_local(
            MATTER_WORLD_PARTICLE_CONTENT_LOCAL_CENTER,
            DEFAULT_WORLD_CONTENT_TARGET_RADIUS,
        )
    }

    pub(crate) fn refresh_matter_surface_gpu_proof_epoch_from_selected_settings(
        &mut self,
        phase: &str,
    ) -> bool {
        let identity =
            crate::makepad_effective_settings::selected_makepad_effective_settings_identity();
        if !identity.gpu_proof_settings_changed_from(
            self.mesh_replay_effective_settings_path.as_deref(),
            self.mesh_replay_effective_settings_gpu_proof_revision_key
                .as_deref(),
        ) {
            return false;
        }

        let gpu_proof_revision_key = identity.gpu_proof_settings_revision_key();
        self.mesh_replay_effective_settings_gpu_proof_revision_key = gpu_proof_revision_key.clone();
        self.reset_matter_surface_gpu_proof_markers();
        self.emit_matter_surface_gpu_proof_epoch_marker(
            phase,
            identity.source_effective_settings_path.as_deref(),
            gpu_proof_revision_key.as_deref(),
        );
        true
    }

    pub(crate) fn reset_matter_surface_gpu_proof_markers(&mut self) {
        self.matter_surface_gpu_compute_preflight_markers_emitted = 0;
        self.matter_surface_gpu_storage_probe_markers_emitted = 0;
        self.matter_surface_gpu_oracle_compute_probe_markers_emitted = 0;
        self.matter_surface_gpu_field_force_probe_markers_emitted = 0;
        self.matter_surface_gpu_skinning_probe_markers_emitted = 0;
        self.matter_surface_gpu_skinning_probe_pending = None;
        self.matter_surface_gpu_skinning_mesh_probe_markers_emitted = 0;
        self.matter_surface_gpu_skinning_mesh_probe_pending = None;
        self.matter_surface_gpu_mesh_sdf_probe_markers_emitted = 0;
        self.matter_surface_gpu_mesh_sdf_probe_pending = None;
        self.matter_surface_gpu_force_authority_residency_tracker
            .reset();
        self.matter_surface_gpu_sync_probe_last_frame = 0;
        self.matter_surface_gpu_schedule_markers_emitted = 0;
    }

    pub(crate) fn update_matter_surface_runtime_for_evidence(
        &mut self,
        cx: &mut Cx,
        now_seconds: f64,
        phase: &str,
        update_panel_overlay: bool,
    ) -> MatterSurfacePanelOverlayFrame {
        let step_interval_seconds = matter_surface_step_interval_seconds(
            &self.matter_surface_source_selection,
            MATTER_SURFACE_STEP_INTERVAL_SECONDS,
        );
        let should_submit = !(now_seconds.is_finite()
            && self.matter_surface_last_step_seconds.is_finite()
            && now_seconds - self.matter_surface_last_step_seconds < step_interval_seconds);

        if should_submit {
            let delta_seconds =
                if now_seconds.is_finite() && self.matter_surface_last_step_seconds.is_finite() {
                    (now_seconds - self.matter_surface_last_step_seconds).clamp(0.0, 0.25) as f32
                } else {
                    1.0 / 60.0
                };
            if self.submit_matter_surface_worker_for_evidence(phase, delta_seconds) {
                self.matter_surface_last_step_seconds = now_seconds;
            }
        }

        if let Some(frame) =
            self.consume_matter_surface_worker_output(cx, phase, update_panel_overlay)
        {
            self.matter_surface_cached_panel_overlay_frame = frame.clone();
            return frame;
        }

        self.matter_surface_cached_panel_overlay_frame.clone()
    }

    fn submit_matter_surface_worker_for_evidence(
        &mut self,
        phase: &str,
        delta_seconds: f32,
    ) -> bool {
        if self.matter_surface_worker.is_none() {
            self.matter_surface_cached_world_particle_batch = None;
            self.matter_surface_cached_world_adf_debug_batch = None;
            return false;
        }
        if self
            .matter_surface_source_selection
            .mode()
            .uses_live_openxr_hand()
        {
            let selected_mode = self.matter_surface_source_selection.mode();
            let include_gpu_oracle_payloads = self.hand_gpu_oracle_payloads_due();
            let Some(worker) = self.matter_surface_worker.as_ref() else {
                return false;
            };
            let summary = self
                .live_hand_surface_source
                .submit_worker_frame_for_latest_matching(
                    worker,
                    phase,
                    selected_mode.live_is_left(),
                    delta_seconds,
                    include_gpu_oracle_payloads,
                );
            if let Some(summary) = summary.as_ref() {
                self.emit_live_hand_surface_worker_source_marker(
                    phase,
                    "ready",
                    selected_mode.marker_value(),
                    Some(summary),
                    None,
                );
                return true;
            }
            self.emit_live_hand_surface_worker_source_marker(
                phase,
                "waiting",
                selected_mode.marker_value(),
                None,
                Some("live_openxr_hand_not_ready"),
            );
            return false;
        }

        let Some(worker) = self.matter_surface_worker.as_ref() else {
            self.matter_surface_cached_world_particle_batch = None;
            self.matter_surface_cached_world_adf_debug_batch = None;
            return false;
        };
        let Some(replay_runtime) = self.mesh_replay_runtime.as_ref() else {
            self.matter_surface_cached_world_particle_batch = None;
            self.matter_surface_cached_world_adf_debug_batch = None;
            return false;
        };
        let selected_mode = self.matter_surface_source_selection.mode();
        let include_gpu_oracle_payloads = if selected_mode.allows_recorded_hand_replay() {
            self.hand_gpu_oracle_payloads_due()
        } else {
            false
        };
        if selected_mode.allows_recorded_hand_replay() {
            if let Some(recorded_source) = self.recorded_hand_surface_source.as_mut() {
                let summary = recorded_source.submit_worker_frame_for_replay(
                    worker,
                    phase,
                    replay_runtime,
                    delta_seconds,
                    include_gpu_oracle_payloads,
                );
                if let Some(marker_line) = recorded_source.worker_marker_line_if_due(
                    phase,
                    selected_mode.marker_value(),
                    &summary,
                    MATTER_SURFACE_MARKER_LIMIT,
                ) {
                    emit_marker_line(&marker_line);
                }
                return true;
            }
        }
        if selected_mode.uses_recorded_hand_replay() {
            self.matter_surface_cached_world_particle_batch = None;
            self.matter_surface_cached_world_adf_debug_batch = None;
            if self.matter_surface_worker_markers_emitted < MATTER_SURFACE_MARKER_LIMIT {
                emit_marker_line(&format!(
                    "RUSTY_QUEST_MAKEPAD_MATTER_SURFACE_WORKER schema=rusty.quest.makepad.matter_surface_worker.v1 phase={} status=waiting mode=latest-wins workerThread=true renderThreadBlocking=false sourceMode={} issue=recorded_hand_replay_not_ready",
                    marker_token(phase),
                    marker_token(selected_mode.marker_value()),
                ));
                self.matter_surface_worker_markers_emitted += 1;
            }
            return false;
        }
        let probe = MatterSurfaceContactProbe::sphere(
            "hostess.camera_shell.center_probe",
            replay_runtime.sequence().bounds_center(),
            replay_runtime.sequence().bounds_radius() * 0.5,
        );
        match worker.submit_replay_frame(phase, replay_runtime, delta_seconds, &[probe]) {
            Ok(_) => true,
            Err(error) => {
                self.matter_surface_cached_world_particle_batch = None;
                self.matter_surface_cached_world_adf_debug_batch = None;
                if self.matter_surface_worker_markers_emitted < MATTER_SURFACE_MARKER_LIMIT {
                    emit_marker_line(&format!(
                        "RUSTY_QUEST_MAKEPAD_MATTER_SURFACE_WORKER schema=rusty.quest.makepad.matter_surface_worker.v1 phase={} status=error mode=latest-wins workerThread=true renderThreadBlocking=false issue={}",
                        marker_token(phase),
                        marker_token(&error.to_string()),
                    ));
                    self.matter_surface_worker_markers_emitted += 1;
                }
                false
            }
        }
    }

    fn hand_gpu_oracle_payloads_due(&self) -> bool {
        let gpu_probe_schedule = MatterSurfaceGpuProofSchedule::for_source_selection(
            &self.matter_surface_source_selection,
            MATTER_SURFACE_GPU_PROBE_MIN_CADENCE_FRAMES,
        );
        if !gpu_probe_schedule.cadence_ready(
            self.cadence_started,
            self.cadence_frame_count,
            self.cadence_xr_update_count,
            self.cadence_draw_event_count,
        ) {
            return false;
        }
        if self.matter_surface_gpu_sync_probe_last_frame != 0
            && self
                .cadence_frame_count
                .saturating_sub(self.matter_surface_gpu_sync_probe_last_frame)
                < MATTER_SURFACE_GPU_SYNC_PROBE_FRAME_GAP
        {
            return false;
        }
        (self.matter_surface_gpu_skinning_probe_markers_emitted == 0
            && self.matter_surface_gpu_skinning_probe_pending.is_none())
            || (self.matter_surface_gpu_skinning_mesh_probe_markers_emitted == 0
                && self
                    .matter_surface_gpu_skinning_mesh_probe_pending
                    .is_none())
            || (self.matter_surface_gpu_mesh_sdf_probe_markers_emitted
                < gpu_probe_schedule.mesh_sdf_probe_target_markers
                && self.matter_surface_gpu_mesh_sdf_probe_pending.is_none())
    }

    fn emit_live_hand_surface_worker_source_marker(
        &mut self,
        phase: &str,
        status: &str,
        selected_mode: &str,
        source_frame: Option<&LiveHandSurfaceWorkerSourceSummary>,
        issue: Option<&str>,
    ) {
        let ready_source_frame = status == "ready" && source_frame.is_some();
        let marker_limit = if ready_source_frame {
            MATTER_SURFACE_MARKER_LIMIT
        } else {
            MATTER_SURFACE_MARKER_LIMIT.saturating_sub(1)
        };
        if self.matter_surface_live_source_worker_markers_emitted >= marker_limit {
            return;
        }
        let source_id = source_frame.map(|frame| frame.source_id).unwrap_or("none");
        let provider_shape = source_frame
            .map(|_| "bind-mesh-plus-compact-joint-frame")
            .unwrap_or("none");
        let frame_index = source_frame.map_or(0, |frame| frame.frame_index);
        let vertex_count = source_frame.map_or(0, |frame| frame.vertex_count);
        let triangle_count = source_frame.map_or(0, |frame| frame.triangle_count);
        let gpu_oracle_payloads_requested =
            source_frame.map_or(false, |frame| frame.gpu_oracle_payloads_requested);
        emit_marker_line(&format!(
            "RUSTY_HOSTESS_MAKEPAD_LIVE_HAND_SURFACE_WORKER_SOURCE schema=rusty.hostess.makepad.live_hand_surface_worker_source.v1 phase={} status={} selectedMode={} sourceId={} providerShape={} frameIndex={} vertexCount={} triangleCount={} issue={} liveOpenXrHandProvider=true workerSourceSelected={} compactFrameWorkerSubmit={} sourceFrameExpansionThread=matter-worker gpuOraclePayloadsRequested={} recordedInputEquivalent={} gpuAdapterBoundaryUnchanged=true highRateJsonPayload=false",
            marker_token(phase),
            marker_token(status),
            marker_token(selected_mode),
            marker_token(source_id),
            marker_token(provider_shape),
            frame_index,
            vertex_count,
            triangle_count,
            issue
                .map(marker_token)
                .unwrap_or_else(|| "none".to_string()),
            source_frame.is_some() && status == "ready",
            source_frame.is_some() && status == "ready",
            gpu_oracle_payloads_requested,
            source_frame.is_some(),
        ));
        self.matter_surface_live_source_worker_markers_emitted += 1;
    }

    fn consume_matter_surface_worker_output(
        &mut self,
        cx: &mut Cx,
        phase: &str,
        update_panel_overlay: bool,
    ) -> Option<MatterSurfacePanelOverlayFrame> {
        let output = self
            .matter_surface_worker
            .as_ref()
            .and_then(|worker| worker.take_latest_output())?;

        if self.matter_surface_worker_markers_emitted < MATTER_SURFACE_MARKER_LIMIT {
            emit_marker_line(&output.marker_line(phase));
            self.matter_surface_worker_markers_emitted += 1;
        }

        match output {
            QuestMakepadMatterSurfaceWorkerOutput::Frame(worker_frame) => {
                Some(self.apply_matter_surface_worker_frame(
                    cx,
                    phase,
                    worker_frame,
                    update_panel_overlay,
                ))
            }
            QuestMakepadMatterSurfaceWorkerOutput::Error(_error) => {
                self.matter_surface_cached_world_particle_batch = None;
                self.matter_surface_cached_world_adf_debug_batch = None;
                None
            }
        }
    }

    fn apply_matter_surface_worker_frame(
        &mut self,
        cx: &mut Cx,
        phase: &str,
        worker_frame: QuestMakepadMatterSurfaceWorkerFrame,
        update_panel_overlay: bool,
    ) -> MatterSurfacePanelOverlayFrame {
        let frame = worker_frame.frame;
        if self.matter_surface_frame_markers_emitted < MATTER_SURFACE_MARKER_LIMIT {
            emit_marker_line(&worker_frame.runtime_marker_line);
            self.matter_surface_frame_markers_emitted += 1;
        }
        let gpu_compute_preflight = QuestMakepadGpuComputePreflight::from_frame(
            &frame,
            QUEST_MAKEPAD_GPU_COMPUTE_DEFAULT_READBACK_PROBE_COUNT,
        );
        if self.matter_surface_gpu_compute_preflight_markers_emitted < MATTER_SURFACE_MARKER_LIMIT {
            if let Some(preflight) = gpu_compute_preflight.as_ref() {
                emit_marker_line(&preflight.marker_line(phase));
                self.matter_surface_gpu_compute_preflight_markers_emitted += 1;
            }
        }
        let gpu_probe_schedule = MatterSurfaceGpuProofSchedule::for_source_selection(
            &self.matter_surface_source_selection,
            MATTER_SURFACE_GPU_PROBE_MIN_CADENCE_FRAMES,
        );
        let gpu_probe_steady_state_ready = gpu_probe_schedule.cadence_ready(
            self.cadence_started,
            self.cadence_frame_count,
            self.cadence_xr_update_count,
            self.cadence_draw_event_count,
        );
        if gpu_probe_steady_state_ready && self.matter_surface_gpu_schedule_markers_emitted == 0 {
            self.reset_matter_surface_gpu_proof_markers();
            let identity =
                crate::makepad_effective_settings::selected_makepad_effective_settings_identity();
            self.emit_matter_surface_gpu_proof_epoch_marker(
                phase,
                identity.source_effective_settings_path.as_deref(),
                identity.gpu_proof_settings_revision_key().as_deref(),
            );
            emit_marker_line(&gpu_probe_schedule.marker_line(
                phase,
                &self.matter_surface_source_selection,
                MATTER_SURFACE_GPU_PROBE_MIN_CADENCE_FRAMES,
                MATTER_SURFACE_STEP_INTERVAL_SECONDS,
                self.cadence_frame_count,
                self.cadence_xr_update_count,
                self.cadence_draw_event_count,
            ));
            self.matter_surface_gpu_schedule_markers_emitted += 1;
        }
        let gpu_probe_due = gpu_probe_steady_state_ready
            && (self.matter_surface_gpu_sync_probe_last_frame == 0
                || self
                    .cadence_frame_count
                    .saturating_sub(self.matter_surface_gpu_sync_probe_last_frame)
                    >= MATTER_SURFACE_GPU_SYNC_PROBE_FRAME_GAP);
        let gpu_sync_probe_due = gpu_probe_due && gpu_probe_schedule.blocking_gpu_diagnostics;
        let mut gpu_async_probe_completed_this_frame = false;
        if self.matter_surface_gpu_skinning_probe_markers_emitted == 0 {
            let completed_skinning_marker = self
                .matter_surface_gpu_skinning_probe_pending
                .as_ref()
                .and_then(|pending| gpu_skinning_probe_poll_marker_line(cx, pending, phase));
            if let Some(marker) = completed_skinning_marker {
                emit_marker_line(&marker);
                self.matter_surface_gpu_skinning_probe_markers_emitted += 1;
                self.matter_surface_gpu_skinning_probe_pending = None;
                gpu_async_probe_completed_this_frame = true;
            }
        }
        if self.matter_surface_gpu_mesh_sdf_probe_markers_emitted
            < gpu_probe_schedule.mesh_sdf_probe_target_markers
        {
            let mesh_sdf_phase = gpu_mesh_sdf_probe_evidence_phase(
                phase,
                self.matter_surface_gpu_mesh_sdf_probe_markers_emitted,
            );
            let pending_mesh_sdf_probe = self.matter_surface_gpu_mesh_sdf_probe_pending.clone();
            let completed_mesh_sdf_markers = pending_mesh_sdf_probe.as_ref().and_then(|pending| {
                let freshness = MatterSurfaceGpuForceFreshnessEvidence::from_source_frame_adoption(
                    pending.source_id(),
                    pending.source_frame_index(),
                    &frame.source_id,
                    frame.matter_update.frame_index,
                    MATTER_SURFACE_GPU_FORCE_FRESHNESS_MAX_SOURCE_FRAME_LAG,
                );
                let gpu_force_authority_runtime_readiness = gpu_probe_schedule
                    .force_authority_runtime_readiness(
                        gpu_probe_steady_state_ready,
                        freshness.freshness_ready(),
                    );
                gpu_mesh_sdf_probe_poll_marker_lines(
                    cx,
                    pending,
                    &mesh_sdf_phase,
                    &mut self.matter_surface_gpu_force_authority_residency_tracker,
                    gpu_force_authority_runtime_readiness,
                )
                .map(|markers| (freshness, markers))
            });
            if let Some((freshness, markers)) = completed_mesh_sdf_markers {
                emit_marker_line(&freshness.marker_line(
                    &mesh_sdf_phase,
                    gpu_probe_steady_state_ready,
                    &self.matter_surface_source_selection,
                ));
                for marker in markers {
                    emit_marker_line(&marker);
                }
                self.matter_surface_gpu_mesh_sdf_probe_markers_emitted += 1;
                self.matter_surface_gpu_mesh_sdf_probe_pending = None;
                gpu_async_probe_completed_this_frame = true;
            }
        }
        if self.matter_surface_gpu_skinning_mesh_probe_markers_emitted == 0 {
            let completed_skinning_mesh_marker = self
                .matter_surface_gpu_skinning_mesh_probe_pending
                .as_ref()
                .and_then(|pending| gpu_skinning_mesh_probe_poll_marker_line(cx, pending, phase));
            if let Some(marker) = completed_skinning_mesh_marker {
                emit_marker_line(&marker);
                self.matter_surface_gpu_skinning_mesh_probe_markers_emitted += 1;
                self.matter_surface_gpu_skinning_mesh_probe_pending = None;
                gpu_async_probe_completed_this_frame = true;
            }
        }
        let mut gpu_sync_probe_emitted_this_frame = gpu_async_probe_completed_this_frame;
        if gpu_sync_probe_due && self.matter_surface_gpu_storage_probe_markers_emitted == 0 {
            if let Some(preflight) = gpu_compute_preflight.as_ref() {
                if let Some(readback) = cx.xr_gpu_storage_buffer_probe(
                    QUEST_MAKEPAD_GPU_STORAGE_PROBE_DEFAULT_BYTES,
                    QUEST_MAKEPAD_GPU_STORAGE_PROBE_DEFAULT_PATTERN,
                ) {
                    let probe = QuestMakepadGpuStorageProbe::from_preflight(
                        preflight,
                        QuestMakepadGpuStorageProbeReadback {
                            requested_bytes: readback.requested_bytes,
                            storage_buffer_bytes: readback.storage_buffer_bytes,
                            readback_bytes: readback.readback_bytes,
                            pattern: readback.pattern,
                            first_word: readback.first_word,
                            word_count: readback.word_count,
                            mismatched_words: readback.mismatched_words,
                            elapsed_ms: readback.elapsed_ms,
                        },
                    );
                    emit_marker_line(&probe.marker_line(phase));
                    self.matter_surface_gpu_storage_probe_markers_emitted += 1;
                    self.matter_surface_gpu_sync_probe_last_frame = self.cadence_frame_count;
                    gpu_sync_probe_emitted_this_frame = true;
                }
            }
        }
        if gpu_sync_probe_due
            && !gpu_sync_probe_emitted_this_frame
            && self.matter_surface_gpu_oracle_compute_probe_markers_emitted == 0
        {
            if let Some(preflight) = gpu_compute_preflight.as_ref() {
                let input_words = preflight.oracle_compute_probe_words();
                if let Some(readback) = cx.xr_gpu_u32_compute_probe(input_words) {
                    let probe = QuestMakepadGpuOracleComputeProbe::from_preflight(
                        preflight,
                        QuestMakepadGpuOracleComputeProbeReadback {
                            input_words: readback.input_words,
                            output_words: readback.output_words,
                            expected_words: readback.expected_words,
                            word_count: readback.word_count,
                            mismatched_words: readback.mismatched_words,
                            queue_submit_serial: readback.queue_submit_serial,
                            fence_serial: readback.fence_serial,
                            resource_generation: readback.resource_generation,
                            pending_retire_count: readback.pending_retire_count,
                            retained_resource_count: readback.retained_resource_count,
                            retired_after_fence_count: readback.retired_after_fence_count,
                            queue_wait_idle_performed: readback.queue_wait_idle_performed,
                            elapsed_ms: readback.elapsed_ms,
                        },
                    );
                    emit_marker_line(&probe.marker_line(phase));
                    self.matter_surface_gpu_oracle_compute_probe_markers_emitted += 1;
                    self.matter_surface_gpu_sync_probe_last_frame = self.cadence_frame_count;
                    gpu_sync_probe_emitted_this_frame = true;
                }
            }
        }
        if gpu_sync_probe_due
            && !gpu_sync_probe_emitted_this_frame
            && self.matter_surface_gpu_field_force_probe_markers_emitted == 0
        {
            if let Some(preflight) = gpu_compute_preflight.as_ref() {
                if let Some(force_probe) = frame
                    .particle_step
                    .as_ref()
                    .and_then(|diagnostics| diagnostics.particle_force_probe.as_ref())
                {
                    let mut samples =
                        [XrGpuF32ForceProbeSample::default(); XR_GPU_F32_FORCE_PROBE_SAMPLES];
                    let sample_count = force_probe
                        .samples
                        .len()
                        .min(XR_GPU_F32_FORCE_PROBE_SAMPLES);
                    for (target, source) in samples
                        .iter_mut()
                        .zip(force_probe.samples.iter())
                        .take(sample_count)
                    {
                        *target = XrGpuF32ForceProbeSample {
                            position_radius: [
                                source.position.x,
                                source.position.y,
                                source.position.z,
                                source.radius,
                            ],
                            distance_target_strength: [
                                source.distance,
                                source.target_distance,
                                force_probe.attraction_strength,
                                0.0,
                            ],
                            outward: [source.outward.x, source.outward.y, source.outward.z, 0.0],
                            expected_acceleration: [
                                source.expected_acceleration.x,
                                source.expected_acceleration.y,
                                source.expected_acceleration.z,
                                0.0,
                            ],
                        };
                    }
                    if sample_count > 0 {
                        if let Some(readback) = cx.xr_gpu_f32_force_probe(
                            samples,
                            sample_count,
                            MATTER_SURFACE_GPU_FORCE_PROBE_TOLERANCE,
                        ) {
                            let probe = QuestMakepadGpuFieldForceProbe::from_preflight(
                                preflight,
                                QuestMakepadGpuFieldForceProbeReadback {
                                    sample_count: readback.sample_count,
                                    component_count: readback.component_count,
                                    mismatched_components: readback.mismatched_components,
                                    max_abs_error: readback.max_abs_error,
                                    tolerance: readback.tolerance,
                                    queue_submit_serial: readback.queue_submit_serial,
                                    fence_serial: readback.fence_serial,
                                    resource_generation: readback.resource_generation,
                                    pending_retire_count: readback.pending_retire_count,
                                    retained_resource_count: readback.retained_resource_count,
                                    retired_after_fence_count: readback.retired_after_fence_count,
                                    queue_wait_idle_performed: readback.queue_wait_idle_performed,
                                    elapsed_ms: readback.elapsed_ms,
                                },
                            );
                            emit_marker_line(&probe.marker_line(phase));
                            self.matter_surface_gpu_field_force_probe_markers_emitted += 1;
                            self.matter_surface_gpu_sync_probe_last_frame =
                                self.cadence_frame_count;
                            gpu_sync_probe_emitted_this_frame = true;
                        }
                    }
                }
            }
        }
        if gpu_probe_due
            && !gpu_sync_probe_emitted_this_frame
            && self.matter_surface_gpu_skinning_probe_markers_emitted == 0
            && self.matter_surface_gpu_skinning_probe_pending.is_none()
        {
            if let Some(input) = frame.gpu_skinning_probe.as_ref() {
                if let Some(pending) = gpu_skinning_probe_submit(cx, input) {
                    self.matter_surface_gpu_skinning_probe_pending = Some(pending);
                    self.matter_surface_gpu_sync_probe_last_frame = self.cadence_frame_count;
                    gpu_sync_probe_emitted_this_frame = true;
                }
            }
        }
        if gpu_probe_due
            && !gpu_sync_probe_emitted_this_frame
            && self.matter_surface_gpu_skinning_mesh_probe_markers_emitted == 0
            && self
                .matter_surface_gpu_skinning_mesh_probe_pending
                .is_none()
        {
            if let Some(input) = frame.gpu_skinning_mesh_probe.as_ref() {
                if let Some(pending) = gpu_skinning_mesh_probe_submit(cx, input) {
                    self.matter_surface_gpu_skinning_mesh_probe_pending = Some(pending);
                    self.matter_surface_gpu_sync_probe_last_frame = self.cadence_frame_count;
                    gpu_sync_probe_emitted_this_frame = true;
                }
            }
        }
        if gpu_probe_due
            && !gpu_sync_probe_emitted_this_frame
            && self.matter_surface_gpu_mesh_sdf_probe_markers_emitted
                < gpu_probe_schedule.mesh_sdf_probe_target_markers
            && self.matter_surface_gpu_mesh_sdf_probe_pending.is_none()
        {
            if frame.gpu_mesh_sdf_probe.is_some() {
                if let Some(pending) =
                    gpu_mesh_sdf_probe_submit(cx, &frame, self.matter_surface_force_authority)
                {
                    self.matter_surface_gpu_mesh_sdf_probe_pending = Some(pending);
                    self.matter_surface_gpu_sync_probe_last_frame = self.cadence_frame_count;
                }
            }
        }
        let bounds_min = frame.source_bounds_min;
        let bounds_max = frame.source_bounds_max;
        let draw_limit = self.current_matter_world_particle_draw_limit();
        let world_batch = frame.world_particle_batch(
            bounds_min,
            bounds_max,
            Self::matter_world_particle_placement(),
            draw_limit,
        );
        if self.matter_surface_world_particle_markers_emitted < MATTER_SURFACE_MARKER_LIMIT {
            if let Some(world_batch) = world_batch.as_ref() {
                emit_marker_line(&world_batch.marker_line(phase));
                self.matter_surface_world_particle_markers_emitted += 1;
            }
        }
        self.matter_surface_cached_world_particle_batch = world_batch;
        let world_adf_debug = frame.world_adf_debug_batch(
            Self::matter_world_adf_debug_placement(),
            MATTER_WORLD_ADF_DEBUG_DRAW_LIMIT_MAX,
        );
        if self.matter_surface_world_adf_debug_markers_emitted < MATTER_SURFACE_MARKER_LIMIT {
            if let Some(world_adf_debug) = world_adf_debug.as_ref() {
                emit_marker_line(&world_adf_debug.marker_line(phase));
                self.matter_surface_world_adf_debug_markers_emitted += 1;
            }
        }
        self.matter_surface_cached_world_adf_debug_batch = world_adf_debug;
        if !update_panel_overlay {
            return MatterSurfacePanelOverlayFrame::default();
        }
        let uniforms = MakepadMatterSurfaceUniforms::from_frame(&frame, bounds_min, bounds_max);
        let particle_texture = self
            .matter_particle_texture
            .update_from_frame(cx, &frame, bounds_min, bounds_max, phase);
        MatterSurfacePanelOverlayFrame {
            uniforms,
            particle_texture,
        }
    }

    pub(crate) fn apply_matter_world_particles_to_cloud(&mut self, cx: &mut Cx, phase: &str) {
        let batch = self.matter_surface_cached_world_particle_batch.clone();
        let draw_limit = self.current_matter_world_particle_draw_limit();
        let draw_limit_source = self.matter_world_particle_draw_limit_source();
        let animation_mode = self.current_matter_world_particle_animation_mode();
        let size_scale = self.current_matter_world_particle_size_scale();
        let cloud_ref = self.ui.widget(cx, ids!(matter_particle_cloud));
        let Some(mut cloud) = cloud_ref.borrow_mut::<MatterWorldParticleBillboardCloud>() else {
            if self.matter_surface_world_particle_draw_markers_emitted
                < MATTER_WORLD_PARTICLE_DRAW_MARKER_LIMIT
            {
                emit_marker_line(&format!(
                    "RUSTY_QUEST_MAKEPAD_WORLD_PARTICLE_DRAW schema=rusty.hostess.makepad.world_particle_draw.v1 phase={} status=error renderer={} issue=matter_world_particle_billboard_cloud_widget_missing configuredDrawLimit={} drawLimitSource={} billboardRenderer=true finalTextureAtlasRenderer=false",
                    marker_token(phase),
                    marker_token(QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_RENDERER_ID),
                    draw_limit,
                    draw_limit_source,
                ));
                self.matter_surface_world_particle_draw_markers_emitted += 1;
            }
            return;
        };
        cloud.set_world_particle_batch(cx, batch.clone(), draw_limit, size_scale, animation_mode);

        if self.matter_surface_world_particle_draw_markers_emitted
            >= MATTER_WORLD_PARTICLE_DRAW_MARKER_LIMIT
        {
            return;
        }
        let Some(batch) = batch else {
            if !self.matter_surface_world_particle_draw_waiting_marker_emitted {
                emit_marker_line(&format!(
                    "RUSTY_QUEST_MAKEPAD_WORLD_PARTICLE_DRAW schema=rusty.hostess.makepad.world_particle_draw.v1 phase={} status=waiting renderer={} sourceSchema=none configuredDrawLimit={} drawLimitSource={} drawnInstances=0 billboardRenderer=true finalTextureAtlasRenderer=false",
                    marker_token(phase),
                    marker_token(QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_RENDERER_ID),
                    draw_limit,
                    draw_limit_source,
                ));
                self.matter_surface_world_particle_draw_waiting_marker_emitted = true;
            }
            return;
        };
        let drawn_instances = batch.instances.len().min(draw_limit);
        let content_center_distance = (batch.content_center[0] * batch.content_center[0]
            + batch.content_center[1] * batch.content_center[1]
            + batch.content_center[2] * batch.content_center[2])
            .sqrt();
        emit_marker_line(&format!(
            "RUSTY_QUEST_MAKEPAD_WORLD_PARTICLE_DRAW schema=rusty.hostess.makepad.world_particle_draw.v1 phase={} status=ready renderer={} renderMode={} animationMode={} animationSource={} borrowedVisualReference={} particleSizeScale={} particleSizeScaleSource={} sourceSchema={} coordinateSpace={} sourceRows={} instanceRows={} configuredDrawLimit={} drawLimitSource={} drawnInstances={} droppedRows={} contentCenter={:.6},{:.6},{:.6} contentRadius={:.6} contentCenterLocalDistanceMeters={:.3} expectedStartHeadDistanceMeters={:.3} billboardRenderer=true finalTextureAtlasRenderer=false",
            marker_token(phase),
            marker_token(QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_RENDERER_ID),
            marker_token(&batch.render_mode),
            marker_token(animation_mode.as_str()),
            marker_token(QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_ANIMATION_SOURCE),
            marker_token(QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_REFERENCE),
            marker_f32_token(Some(size_scale)),
            self.matter_world_particle_size_scale_source(),
            marker_token(&batch.source_schema_id),
            marker_token(&batch.coordinate_space),
            batch.source_rows,
            batch.instances.len(),
            draw_limit,
            draw_limit_source,
            drawn_instances,
            batch.dropped_rows,
            batch.content_center[0],
            batch.content_center[1],
            batch.content_center[2],
            batch.content_radius,
            content_center_distance,
            MATTER_WORLD_PARTICLE_START_HEAD_DISTANCE_METERS,
        ));
        emit_marker_line(
            &QuestMakepadGpuResidencyProof::from_world_particle_batch(
                &batch,
                drawn_instances,
                QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_RENDERER_ID,
            )
            .marker_line(phase),
        );
        self.matter_surface_world_particle_draw_markers_emitted += 1;
    }

    pub(crate) fn apply_matter_world_adf_debug_to_cells(&mut self, cx: &mut Cx, phase: &str) {
        let batch = self.matter_surface_cached_world_adf_debug_batch.clone();
        let draw_limit = MATTER_WORLD_ADF_DEBUG_DRAW_LIMIT_MAX;
        let cells_ref = self.ui.widget(cx, ids!(matter_adf_debug_cells));
        let Some(mut cells) = cells_ref.borrow_mut::<MatterWorldAdfDebugCells>() else {
            if self.matter_surface_world_adf_debug_draw_markers_emitted
                < MATTER_WORLD_ADF_DEBUG_DRAW_MARKER_LIMIT
            {
                emit_marker_line(&format!(
                    "RUSTY_QUEST_MAKEPAD_WORLD_ADF_DEBUG_DRAW schema=rusty.hostess.makepad.world_adf_debug_draw.v1 phase={} status=error renderer={} issue=matter_world_adf_debug_cells_widget_missing configuredDrawLimit={}",
                    marker_token(phase),
                    marker_token(HOSTESS_WORLD_ADF_DEBUG_RENDERER_ID),
                    draw_limit,
                ));
                self.matter_surface_world_adf_debug_draw_markers_emitted += 1;
            }
            return;
        };
        cells.set_world_adf_debug_batch(cx, batch.clone(), draw_limit);

        if self.matter_surface_world_adf_debug_draw_markers_emitted
            >= MATTER_WORLD_ADF_DEBUG_DRAW_MARKER_LIMIT
        {
            return;
        }
        let Some(batch) = batch else {
            if !self.matter_surface_world_adf_debug_draw_waiting_marker_emitted {
                emit_marker_line(&format!(
                    "RUSTY_QUEST_MAKEPAD_WORLD_ADF_DEBUG_DRAW schema=rusty.hostess.makepad.world_adf_debug_draw.v1 phase={} status=waiting renderer={} sourceSchema=none configuredDrawLimit={} drawnCells=0",
                    marker_token(phase),
                    marker_token(HOSTESS_WORLD_ADF_DEBUG_RENDERER_ID),
                    draw_limit,
                ));
                self.matter_surface_world_adf_debug_draw_waiting_marker_emitted = true;
            }
            return;
        };
        let drawn_cells = batch.cells.len().min(draw_limit);
        let content_center_distance = (batch.content_center[0] * batch.content_center[0]
            + batch.content_center[1] * batch.content_center[1]
            + batch.content_center[2] * batch.content_center[2])
            .sqrt();
        emit_marker_line(&format!(
            "RUSTY_QUEST_MAKEPAD_WORLD_ADF_DEBUG_DRAW schema=rusty.hostess.makepad.world_adf_debug_draw.v1 phase={} status=ready renderer={} renderMode={} sourceSchema={} sourceVisualSchema={} coordinateSpace={} sourceCells={} cellRows={} configuredDrawLimit={} drawnCells={} droppedCells={} contentCenter={:.6},{:.6},{:.6} contentRadius={:.6} contentCenterLocalDistanceMeters={:.3} expectedStartHeadDistanceMeters={:.3} dataPlane=makepad-world-adf-debug-cells",
            marker_token(phase),
            marker_token(HOSTESS_WORLD_ADF_DEBUG_RENDERER_ID),
            marker_token(if batch.render_mode.is_empty() {
                QUEST_MAKEPAD_WORLD_ADF_DEBUG_RENDER_MODE
            } else {
                &batch.render_mode
            }),
            marker_token(&batch.source_schema_id),
            marker_token(&batch.source_visual_schema_id),
            marker_token(&batch.coordinate_space),
            batch.source_cells,
            batch.cells.len(),
            draw_limit,
            drawn_cells,
            batch.dropped_cells,
            batch.content_center[0],
            batch.content_center[1],
            batch.content_center[2],
            batch.content_radius,
            content_center_distance,
            MATTER_WORLD_PARTICLE_START_HEAD_DISTANCE_METERS,
        ));
        emit_marker_line(
            &QuestMakepadGpuResidencyProof::from_world_adf_debug_batch(
                &batch,
                drawn_cells,
                HOSTESS_WORLD_ADF_DEBUG_RENDERER_ID,
            )
            .marker_line(phase),
        );
        self.matter_surface_world_adf_debug_draw_markers_emitted += 1;
    }
}

fn gpu_mesh_sdf_probe_evidence_phase(base_phase: &str, markers_emitted: usize) -> String {
    let suffix = if markers_emitted == 0 {
        "gpu-mesh-sdf-setup"
    } else {
        "gpu-mesh-sdf-reuse"
    };
    format!("{base_phase}-{suffix}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mesh_sdf_probe_evidence_phase_separates_setup_and_reuse() {
        assert_eq!(
            gpu_mesh_sdf_probe_evidence_phase("unit", 0),
            "unit-gpu-mesh-sdf-setup"
        );
        assert_eq!(
            gpu_mesh_sdf_probe_evidence_phase("unit", 1),
            "unit-gpu-mesh-sdf-reuse"
        );
        assert_eq!(
            gpu_mesh_sdf_probe_evidence_phase("unit", 2),
            "unit-gpu-mesh-sdf-reuse"
        );
    }
}
