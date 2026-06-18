pub use makepad_xr::makepad_widgets;

#[cfg(target_os = "android")]
mod acamera_sys;
#[cfg(target_os = "android")]
mod android_camera_probe;
mod app_horizontal_alignment;
mod app_mesh_replay_runtime;
mod app_projection_target;
mod app_stimulus_runtime;
mod broker_h264_runtime;
mod camera_pair;
mod camera_projection_flow;
mod camera_texture_path;
mod frame_orientation;
#[allow(dead_code, unused_imports)]
mod hostess_camera_model;
#[allow(dead_code, unused_imports)]
mod hostess_contracts;
mod live_hand_surface;
#[cfg(test)]
mod main_tests;
mod makepad_app_live_design;
mod makepad_diagnostics;
mod makepad_effective_settings;
#[allow(dead_code, unused_imports)]
mod makepad_runtime_config;
mod makepad_stereo_camera_panel;
mod manifold_breath_feedback;
mod manifold_pose_publisher;
mod matter_particle_texture;
mod matter_surface_gpu;
mod matter_surface_gpu_promotion;
mod matter_surface_gpu_schedule;
mod matter_surface_runtime;
mod matter_surface_source_selection;
mod matter_surface_uniforms;
mod matter_world_adf_debug;
mod matter_world_particle_billboard;
mod projection_geometry;
mod projection_runtime;
mod projection_settings;
mod projection_target_controls;
mod recorded_hand_surface;
mod runtime_settings;
mod shell_contract;
mod shell_runtime_capabilities;
mod shell_xr_runtime;
mod source_metadata;
mod source_sampling;
mod stereo_frame;
mod stimulus_stereo_field;
mod stimulus_stereo_field_live;
mod stimulus_volume_gpu;
mod texture_probe_stats;
use crate::makepad_runtime_config as makepad_config;
use camera_pair::{
    collect_makepad_camera_choices, frame_rate_token, makepad_display_source_eye_mapping,
    pixel_format_label, Camera2StereoPlan, MakepadCameraPair,
};
use camera_texture_path::MakepadCameraTexturePath;
use frame_orientation::{broker_pair_pose_source, FrameOrientationDecision};
use live_hand_surface::LiveHandSurfaceSource;
use makepad_diagnostics::{
    camera_frame_age_ms, camera_import_lag_ms, camera_shell_sdf_adf_mode_token, diagnostic_now_ns,
    emit_marker_line, emit_raw_video_event_marker, marker_f32_token, marker_value,
    optional_i64_token, optional_max_f64, optional_u64_token, rate_hz,
    should_emit_texture_update_marker, vec3_marker_token, vec4_marker_token,
    MakepadCameraYuvTextures,
};
use makepad_effective_settings::MakepadCameraShellFeatureUniforms;
pub(crate) use makepad_stereo_camera_panel::{HorizontalAlignmentTuning, MakepadStereoCameraPanel};
use matter_particle_texture::{MatterParticleTextureFrame, MatterParticleTextureRenderer};
use matter_surface_gpu::{
    PendingGpuMeshSdfProbe, PendingGpuSkinningMeshProbe, PendingGpuSkinningProbe,
};
use matter_surface_gpu_promotion::MatterSurfaceGpuForcePromotionReadiness;
use matter_surface_gpu_schedule::MATTER_SURFACE_LIVE_OBSERVE_INTERVAL_SECONDS;
use matter_surface_runtime::MatterSurfacePanelOverlayFrame;
use matter_surface_source_selection::MatterSurfaceSourceSelection;
use matter_surface_uniforms::MakepadMatterSurfaceUniforms;
use matter_world_adf_debug::HOSTESS_WORLD_ADF_DEBUG_DRAW_LIMIT_MAX;
use matter_world_particle_billboard::HOSTESS_WORLD_PARTICLE_BILLBOARD_DRAW_LIMIT_MAX;
#[cfg(target_os = "android")]
use projection_geometry::broker_projection_plan_marker_fields;
use projection_geometry::{
    makepad_draw_vars_bound_marker_fields, makepad_horizontal_alignment_hotload_marker_fields,
    makepad_native_video_widget_reset_error_marker_fields,
    makepad_native_video_widget_reset_waiting_marker_fields,
    makepad_native_video_widget_surface_marker_fields,
    makepad_paired_projection_progress_marker_fields,
    makepad_projection_complete_error_marker_fields, makepad_projection_complete_marker_fields,
    makepad_projection_enumerated_marker_fields, makepad_projection_start_marker_fields,
    makepad_single_stream_proof_wait_marker_fields, makepad_stereo_comparison_marker_line,
    makepad_stereo_projection_marker_line, makepad_synthetic_stereo_comparison_marker_line,
    makepad_visible_panel_bound_marker_fields, MakepadStereoComparisonMarkerInputs,
};
use projection_runtime::{
    makepad_current_projection_runtime_float, makepad_horizontal_alignment_tuning_from_resolution,
    makepad_projection_runtime_manifest_lines, makepad_projection_runtime_resolution,
    makepad_projection_runtime_resolution_enabled,
};
use projection_settings::*;
use recorded_hand_surface::RecordedHandSurfaceSource;
use runtime_settings::*;
#[cfg(target_os = "android")]
use source_metadata::{broker_projection_plan_decision, BrokerProjectionPlanKind};
use source_metadata::{
    makepad_camera2_acquisition_broker_h264_skipped_marker_line,
    makepad_camera2_acquisition_streaming_disabled_marker_line, makepad_camera_status_marker_line,
    makepad_content_geometry_marker_fields,
    makepad_hardware_buffer_import_broker_h264_prepare_request_marker_fields,
    makepad_hardware_buffer_import_broker_h264_startup_marker_fields,
    makepad_hardware_buffer_import_complete_error_marker_fields,
    makepad_hardware_buffer_import_enumerated_error_marker_fields,
    makepad_hardware_buffer_import_enumerated_marker_fields,
    makepad_hardware_buffer_import_marker_line,
    makepad_hardware_buffer_import_prepared_marker_fields,
    makepad_hardware_buffer_import_start_error_marker_fields,
    makepad_hardware_buffer_import_start_marker_fields,
    makepad_hardware_buffer_import_start_waiting_marker_fields,
    makepad_hardware_buffer_import_texture_handle_ready_marker_fields,
    makepad_hardware_buffer_import_texture_updated_marker_fields,
    makepad_hardware_buffer_import_timer_armed_marker_fields,
    makepad_hardware_buffer_import_timer_fired_marker_fields,
    makepad_hardware_buffer_import_yuv_textures_ready_broker_marker_fields,
    makepad_hardware_buffer_import_yuv_textures_ready_single_stream_marker_fields,
    makepad_runtime_camera_source_sampling_mode,
    makepad_stream_header_metadata_error_marker_fields,
    makepad_stream_header_metadata_ignored_marker_fields, stream_header_metadata_marker_fields,
    BrokerH264ProjectionMetadata, MakepadContentGeometrySource,
};

use crate::hostess_camera_model::SourceSamplingMode;
use crate::makepad_runtime_config::RuntimeConfig;
use makepad_widgets::makepad_platform::{
    event::video_playback::{
        CameraPreviewMode, ExternalH264VideoSource, TextureHandleReadyEvent, VideoSource,
        VideoTextureResourcePath, VideoTextureUpdateMetadata, VideoYuvMetadata,
    },
    permission::Permission,
    script::vm::ScriptVmCx,
    thread::SignalToUI,
    video::VideoInputsEvent,
    CxMediaApi, TextureFormat, TextureId, TextureUpdated,
};
use makepad_widgets::*;
use manifold_breath_feedback::{
    BreathFeedbackSample, ManifoldBreathFeedbackConfig, ManifoldBreathFeedbackSubscriber,
};
use manifold_pose_publisher::{
    ManifoldPosePublisher, ManifoldPosePublisherConfig, ManifoldPoseSample,
};
use projection_target_controls::{
    makepad_projection_target_breath_controls_enabled_from_value,
    makepad_projection_target_breath_lerp, makepad_projection_target_breath_sample_is_new,
    makepad_projection_target_breath_scale, makepad_projection_target_breath_scale_mode_from_value,
    makepad_projection_target_breath_smoothing_alpha,
    makepad_projection_target_breath_state_scale_step,
    makepad_projection_target_joystick_controls_enabled_from_value,
    makepad_projection_target_offset_step, makepad_projection_target_offset_x_uv,
    makepad_projection_target_offset_y_uv, makepad_projection_target_scale,
    makepad_projection_target_scale_step, ProjectionTargetBreathScaleMode,
    PROJECTION_TARGET_BREATH_DEFAULT_EXHALE_SECONDS_MAX_TO_MIN,
    PROJECTION_TARGET_BREATH_DEFAULT_INHALE_SECONDS_MIN_TO_MAX,
    PROJECTION_TARGET_BREATH_DEFAULT_SMOOTHING_ALPHA,
};
use rusty_quest_makepad_camera_shell::{
    MeshReplayRuntime, MeshReplayUniforms, ParticleRenderAnimationMode,
    QuestMakepadForceAuthorityMode, QuestMakepadGpuForceAuthorityResidencyTracker,
    QuestMakepadMatterSurfaceWorker, QuestMakepadWorldAdfDebugBatch,
    QuestMakepadWorldParticleBatch, RemoteCameraEffectiveConfig,
    DEFAULT_PARTICLE_RENDER_ANIMATION_MODE, DEFAULT_PARTICLE_RENDER_DRAW_LIMIT,
    DEFAULT_PARTICLE_RENDER_SIZE_SCALE,
};
use shell_contract::MakepadShellContractReadReceipt;
use shell_runtime_capabilities::MakepadShellRuntimeCapabilityReceipt;
use shell_xr_runtime::ShellXrRuntimeState;
use source_sampling::{
    makepad_cadence_compact_sample_marker_line, makepad_cadence_sample_marker_line,
    makepad_cadence_start_marker_line, makepad_texture_content_probe_missing_marker_fields,
    makepad_texture_content_probe_ok_marker_fields, MakepadCadenceSampleMarker,
    MakepadSourceSamplingHandoff,
};
use std::{
    sync::{
        atomic::{AtomicBool, AtomicUsize, Ordering},
        Mutex,
    },
    thread,
    time::Duration,
};
use stereo_frame::{AdoptedStereoCameraFrame, CameraTextureFrameSample, StereoEye, XrPoseSnapshot};
use stimulus_stereo_field::{
    StimulusStereoFieldPanel, StimulusStereoFieldState, StimulusSurfaceProjectionRows,
    STIMULUS_VOLUME_TEXTURE_SLOT,
};
use stimulus_volume_gpu::{
    stimulus_volume_gpu_probe_poll_marker_line, stimulus_volume_gpu_probe_submit,
    stimulus_volume_image_preview_input_from_state, stimulus_volume_image_preview_poll_ready,
    stimulus_volume_image_preview_submit, stimulus_volume_probe_input_from_state,
    stimulus_volume_raymarch_preview_input_from_state,
    stimulus_volume_raymarch_preview_poll_marker_line, stimulus_volume_raymarch_preview_submit,
    PendingStimulusVolumeGpuProbe, PendingStimulusVolumeImagePreview,
    PendingStimulusVolumeRaymarchPreview, StimulusVolumeImagePreviewReady,
    StimulusVolumeTextureBindingEvidence,
};
use texture_probe_stats::texture_plane_content_stats;

app_main!(App);

#[cfg(target_os = "android")]
#[allow(dead_code)]
fn main() {
    // Makepad Android launches through the JNI entrypoint emitted by app_main!.
    // Plain Cargo target checks still compile this source as a binary crate.
}

static STARTUP_MARKERS_EMITTED: AtomicBool = AtomicBool::new(false);
static PAIRED_IMPORT_SIGNAL_READY: AtomicBool = AtomicBool::new(false);
static TEXTURE_UPDATE_MARKERS_EMITTED: AtomicUsize = AtomicUsize::new(0);
static TEXTURE_CONTENT_PROBE_MARKERS_EMITTED: AtomicUsize = AtomicUsize::new(0);
static FRAME_ADOPTION_MARKERS_EMITTED: AtomicUsize = AtomicUsize::new(0);
static EFFECTIVE_REMOTE_CAMERA: Mutex<Option<RemoteCameraEffectiveConfig>> = Mutex::new(None);
#[cfg(target_os = "android")]
static ANDROID_XR_START_FALLBACK_REQUESTED: AtomicBool = AtomicBool::new(false);

const CAMERA_FRAME_STALE_THRESHOLD_MS: f64 = 100.0;
const FRAME_ADOPTION_MARKER_LIMIT: usize = 24;
const FRAME_ADOPTION_MARKER_PERIOD: usize = 120;
const MATTER_SURFACE_STEP_INTERVAL_SECONDS: f64 = 1.0 / 12.0;
const MATTER_SURFACE_MARKER_LIMIT: usize = 8;
const MATTER_SURFACE_GPU_PROBE_MIN_CADENCE_FRAMES: u64 = 900;
const MATTER_SURFACE_GPU_SYNC_PROBE_FRAME_GAP: u64 = 90;
const MATTER_SURFACE_GPU_FORCE_PROBE_TOLERANCE: f32 = 0.0001;
const MATTER_WORLD_PARTICLE_DRAW_LIMIT_MAX: usize = HOSTESS_WORLD_PARTICLE_BILLBOARD_DRAW_LIMIT_MAX;
const MATTER_WORLD_PARTICLE_DRAW_MARKER_LIMIT: usize = 8;
const MATTER_WORLD_ADF_DEBUG_DRAW_LIMIT_MAX: usize = HOSTESS_WORLD_ADF_DEBUG_DRAW_LIMIT_MAX;
const MATTER_WORLD_ADF_DEBUG_DRAW_MARKER_LIMIT: usize = 8;
const STIMULUS_STEREO_FIELD_MARKER_LIMIT: usize = 8;
const STIMULUS_VOLUME_GPU_PROBE_MARKER_LIMIT: usize = 1;
const STIMULUS_VOLUME_RAYMARCH_PREVIEW_MARKER_LIMIT: usize = 1;
const STIMULUS_VOLUME_IMAGE_PREVIEW_MARKER_LIMIT: usize = 1;
const MAKEPAD_XR_INITIAL_CONTENT_FORWARD_OFFSET_METERS: f32 = 0.28;
const MAKEPAD_XR_INITIAL_CONTENT_VERTICAL_OFFSET_METERS: f32 = -0.58;
const MATTER_WORLD_PARTICLE_START_HEAD_DISTANCE_METERS: f32 = 0.50;
const MATTER_WORLD_PARTICLE_CONTENT_LOCAL_CENTER: [f32; 3] = [
    0.0,
    -MAKEPAD_XR_INITIAL_CONTENT_VERTICAL_OFFSET_METERS,
    -(MATTER_WORLD_PARTICLE_START_HEAD_DISTANCE_METERS
        - MAKEPAD_XR_INITIAL_CONTENT_FORWARD_OFFSET_METERS),
];

#[derive(Script, ScriptHook)]
pub struct App {
    #[live]
    ui: WidgetRef,
    #[rust]
    shell_contract_read: MakepadShellContractReadReceipt,
    #[rust]
    shell_runtime_capabilities: MakepadShellRuntimeCapabilityReceipt,
    #[rust]
    shell_xr_runtime: ShellXrRuntimeState,
    #[rust]
    mesh_replay_runtime: Option<MeshReplayRuntime>,
    #[rust]
    recorded_hand_surface_source: Option<RecordedHandSurfaceSource>,
    #[rust]
    live_hand_surface_source: LiveHandSurfaceSource,
    #[rust]
    matter_surface_source_selection: MatterSurfaceSourceSelection,
    #[rust]
    matter_surface_worker: Option<QuestMakepadMatterSurfaceWorker>,
    #[rust]
    matter_surface_frame_markers_emitted: usize,
    #[rust]
    matter_surface_worker_markers_emitted: usize,
    #[rust]
    matter_surface_live_source_worker_markers_emitted: usize,
    #[rust]
    matter_surface_gpu_compute_preflight_markers_emitted: usize,
    #[rust]
    matter_surface_gpu_storage_probe_markers_emitted: usize,
    #[rust]
    matter_surface_gpu_oracle_compute_probe_markers_emitted: usize,
    #[rust]
    matter_surface_gpu_field_force_probe_markers_emitted: usize,
    #[rust]
    matter_surface_gpu_skinning_probe_markers_emitted: usize,
    #[rust]
    matter_surface_gpu_skinning_probe_pending: Option<PendingGpuSkinningProbe>,
    #[rust]
    matter_surface_gpu_skinning_mesh_probe_markers_emitted: usize,
    #[rust]
    matter_surface_gpu_skinning_mesh_probe_pending: Option<PendingGpuSkinningMeshProbe>,
    #[rust]
    matter_surface_gpu_mesh_sdf_probe_markers_emitted: usize,
    #[rust]
    matter_surface_gpu_mesh_sdf_probe_pending: Option<PendingGpuMeshSdfProbe>,
    #[rust]
    matter_surface_gpu_force_authority_residency_tracker:
        QuestMakepadGpuForceAuthorityResidencyTracker,
    #[rust]
    matter_surface_gpu_sync_probe_last_frame: u64,
    #[rust]
    matter_surface_gpu_schedule_markers_emitted: usize,
    #[rust]
    matter_surface_world_particle_markers_emitted: usize,
    #[rust]
    matter_surface_world_particle_draw_markers_emitted: usize,
    #[rust]
    matter_surface_world_particle_draw_waiting_marker_emitted: bool,
    #[rust]
    matter_surface_world_adf_debug_markers_emitted: usize,
    #[rust]
    matter_surface_world_adf_debug_draw_markers_emitted: usize,
    #[rust]
    matter_surface_world_adf_debug_draw_waiting_marker_emitted: bool,
    #[rust]
    matter_surface_last_step_seconds: f64,
    #[rust]
    matter_surface_cached_panel_overlay_frame: MatterSurfacePanelOverlayFrame,
    #[rust]
    matter_surface_cached_world_particle_batch: Option<QuestMakepadWorldParticleBatch>,
    #[rust]
    matter_surface_cached_world_adf_debug_batch: Option<QuestMakepadWorldAdfDebugBatch>,
    #[rust]
    matter_particle_texture: MatterParticleTextureRenderer,
    #[rust]
    matter_world_particle_draw_limit: usize,
    #[rust]
    matter_world_particle_draw_limit_configured: bool,
    #[rust]
    matter_world_particle_animation_mode: ParticleRenderAnimationMode,
    #[rust]
    matter_world_particle_size_scale: f32,
    #[rust]
    matter_world_particle_size_scale_configured: bool,
    #[rust]
    camera_shell_feature_uniforms: MakepadCameraShellFeatureUniforms,
    #[rust]
    matter_surface_force_authority: QuestMakepadForceAuthorityMode,
    #[rust]
    matter_surface_gpu_force_promotion_readiness: MatterSurfaceGpuForcePromotionReadiness,
    #[rust]
    camera_shell_effective_render_scale: f32,
    #[rust]
    camera_shell_effective_render_scale_present: bool,
    #[rust]
    camera_shell_effective_camera_streaming_enabled: bool,
    #[rust]
    stimulus_stereo_field_state: StimulusStereoFieldState,
    #[rust]
    stimulus_surface_projection_rows: StimulusSurfaceProjectionRows,
    #[rust]
    stimulus_stereo_field_markers_emitted: usize,
    #[rust]
    stimulus_controller_randomize_count: u64,
    #[rust]
    stimulus_volume_gpu_probe_markers_emitted: usize,
    #[rust]
    stimulus_volume_gpu_probe_pending: Option<PendingStimulusVolumeGpuProbe>,
    #[rust]
    stimulus_volume_raymarch_preview_markers_emitted: usize,
    #[rust]
    stimulus_volume_raymarch_preview_pending: Option<PendingStimulusVolumeRaymarchPreview>,
    #[rust]
    stimulus_volume_image_preview_markers_emitted: usize,
    #[rust]
    stimulus_volume_image_preview_pending: Option<PendingStimulusVolumeImagePreview>,
    #[rust]
    stimulus_volume_image_preview_texture: Option<Texture>,
    #[rust]
    stimulus_volume_texture_adoption_markers_emitted: usize,
    #[rust]
    makepad_video_input_discovery_enabled: Option<bool>,
    #[rust]
    mesh_replay_effective_settings_path: Option<String>,
    #[rust]
    mesh_replay_effective_settings_revision_key: Option<String>,
    #[rust]
    mesh_replay_effective_settings_gpu_proof_revision_key: Option<String>,
    #[rust]
    mesh_replay_effective_settings_modified_ns: u128,
    #[rust]
    mesh_replay_effective_settings_has_modified_ns: bool,
    #[rust]
    mesh_replay_settings_check_frame: u64,
    #[rust]
    paired_import_timer: Timer,
    #[rust]
    paired_import_wait_count: usize,
    #[rust]
    paired_import_choice: Option<MakepadCameraPair>,
    #[rust]
    paired_import_selection_logged: bool,
    #[rust]
    camera_streaming_disabled_logged: bool,
    #[rust]
    paired_import_started: bool,
    #[rust]
    broker_h264_left_playback_requested: bool,
    #[rust]
    broker_h264_right_playback_requested: bool,
    #[rust]
    broker_h264_left_projection_metadata: Option<BrokerH264ProjectionMetadata>,
    #[rust]
    broker_h264_right_projection_metadata: Option<BrokerH264ProjectionMetadata>,
    #[rust]
    #[cfg_attr(not(target_os = "android"), allow(dead_code))]
    broker_h264_projection_plan_logged: bool,
    #[rust]
    native_video_widget_started: bool,
    #[rust]
    native_video_widget_retry_timer: Timer,
    #[rust]
    native_video_widget_retry_pair: Option<MakepadCameraPair>,
    #[rust]
    native_video_widget_retry_count: usize,
    #[rust]
    paired_import_finished: bool,
    #[rust]
    paired_import_left_texture: Option<Texture>,
    #[rust]
    paired_import_right_texture: Option<Texture>,
    #[rust]
    paired_import_left_yuv_textures: Option<MakepadCameraYuvTextures>,
    #[rust]
    paired_import_right_yuv_textures: Option<MakepadCameraYuvTextures>,
    #[rust]
    paired_import_left_yuv_metadata: Option<VideoYuvMetadata>,
    #[rust]
    paired_import_right_yuv_metadata: Option<VideoYuvMetadata>,
    #[rust]
    paired_import_left_update_metadata: Option<VideoTextureUpdateMetadata>,
    #[rust]
    paired_import_right_update_metadata: Option<VideoTextureUpdateMetadata>,
    #[rust]
    pending_left_camera_frame: Option<CameraTextureFrameSample>,
    #[rust]
    pending_right_camera_frame: Option<CameraTextureFrameSample>,
    #[rust]
    adopted_stereo_camera_frame: Option<AdoptedStereoCameraFrame>,
    #[rust]
    next_adopted_stereo_frame_id: u64,
    #[rust]
    camera_projection_bound_adopted_frame_id: u64,
    #[rust]
    last_xr_pose_snapshot: Option<XrPoseSnapshot>,
    #[rust]
    paired_import_left_prepared: bool,
    #[rust]
    paired_import_right_prepared: bool,
    #[rust]
    paired_import_left_updated: bool,
    #[rust]
    paired_import_right_updated: bool,
    #[rust]
    paired_import_left_rotation_steps: f32,
    #[rust]
    paired_import_right_rotation_steps: f32,
    #[rust]
    camera_projection_textures_bound: bool,
    #[rust]
    camera_projection_paired_textures_bound: bool,
    #[rust]
    camera_projection_single_stream_logged: bool,
    #[rust]
    camera_projection_bind_error_logged: bool,
    #[rust]
    synthetic_scene_hidden_for_camera: bool,
    #[rust]
    horizontal_alignment_tuning_ready: bool,
    #[rust]
    horizontal_alignment_strength: f32,
    #[rust]
    manual_horizontal_offset_left_uv: f32,
    #[rust]
    manual_horizontal_offset_right_uv: f32,
    #[rust]
    manual_vertical_offset_uv: f32,
    #[rust]
    content_uv_scale: f32,
    #[rust]
    projection_border_opacity: f32,
    #[rust]
    projection_border_policy: f32,
    #[rust]
    processing_layer: f32,
    #[rust]
    projection_sample_mode: f32,
    #[rust]
    blur_radius_px: f32,
    #[rust]
    peripheral_stretch_core_scale: f32,
    #[rust]
    peripheral_stretch_edge_inset_uv: f32,
    #[rust]
    peripheral_stretch_max_inset_uv: f32,
    #[rust]
    peripheral_stretch_curve: f32,
    #[rust]
    peripheral_stretch_inner_blend_uv: f32,
    #[rust]
    peripheral_stretch_blend_curve: f32,
    #[rust]
    peripheral_stretch_blend_mode: f32,
    #[rust]
    peripheral_stretch_debug: f32,
    #[rust]
    projection_area_diagnostic: f32,
    #[rust]
    projection_area_offset_left_uv: f32,
    #[rust]
    projection_area_offset_right_uv: f32,
    #[rust]
    projection_area_offset_vertical_uv: f32,
    #[rust]
    projection_area_scale_x: f32,
    #[rust]
    projection_area_scale_y: f32,
    #[rust]
    projection_target_offset_x_uv: f32,
    #[rust]
    projection_target_offset_y_uv: f32,
    #[rust]
    projection_target_scale: f32,
    #[rust]
    projection_area_radius_x_uv: f32,
    #[rust]
    projection_area_radius_y_uv: f32,
    #[rust]
    projection_area_corner_radius_uv: f32,
    #[rust]
    projection_area_keystone_x: f32,
    #[rust]
    projection_area_bow_x: f32,
    #[rust]
    projection_area_opacity: f32,
    #[rust]
    projection_alpha_mode: f32,
    #[rust]
    projection_alpha_scale: f32,
    #[rust]
    projection_alpha_bias: f32,
    #[rust]
    #[allow(dead_code)]
    projection_content_mapping_mode: f32,
    #[rust]
    manifold_pose_publisher: Option<ManifoldPosePublisher>,
    #[rust]
    manifold_pose_last_publish_time: f64,
    #[rust]
    manifold_pose_next_sequence_id: u64,
    #[rust]
    manifold_pose_published_count: u64,
    #[rust]
    manifold_pose_dropped_count: u64,
    #[rust]
    manifold_breath_feedback_subscriber: Option<ManifoldBreathFeedbackSubscriber>,
    #[rust]
    manifold_breath_feedback_config_marker: Option<String>,
    #[rust]
    projection_target_breath_scale_ready: bool,
    #[rust]
    projection_target_breath_last_sequence_id: u64,
    #[rust]
    projection_target_breath_last_sample_time_ns: i64,
    #[rust]
    projection_target_breath_last_log_frame: u64,
    #[rust]
    projection_target_joystick_scale_ready: bool,
    #[rust]
    projection_target_joystick_offset_x_uv: f32,
    #[rust]
    projection_target_joystick_offset_y_uv: f32,
    #[rust]
    projection_target_joystick_scale: f32,
    #[rust]
    projection_target_joystick_last_time: f64,
    #[rust]
    projection_target_joystick_last_log_frame: u64,
    #[rust]
    cadence_next_frame: Option<NextFrame>,
    #[rust]
    cadence_started: bool,
    #[rust]
    cadence_start_time: f64,
    #[rust]
    cadence_last_sample_time: f64,
    #[rust]
    cadence_frame_count: u64,
    #[rust]
    cadence_frame_count_at_last_sample: u64,
    #[rust]
    cadence_xr_update_count: u64,
    #[rust]
    cadence_xr_update_count_at_last_sample: u64,
    #[rust]
    cadence_draw_event_count: u64,
    #[rust]
    cadence_draw_event_count_at_last_sample: u64,
    #[rust]
    cadence_left_texture_update_count: u64,
    #[rust]
    cadence_right_texture_update_count: u64,
    #[rust]
    cadence_left_texture_update_count_at_last_sample: u64,
    #[rust]
    cadence_right_texture_update_count_at_last_sample: u64,
    #[rust]
    cadence_left_last_position_ms: u128,
    #[rust]
    cadence_right_last_position_ms: u128,
}

impl App {
    fn emit_startup_markers_once(phase: &str) {
        if STARTUP_MARKERS_EMITTED
            .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
            .is_err()
        {
            return;
        }

        Self::emit_status_marker(phase);
        Self::emit_stereo_comparison_marker(phase);
        if !Self::startup_camera_streaming_enabled() {
            emit_marker_line(makepad_camera2_acquisition_streaming_disabled_marker_line());
        } else if Self::broker_h264_enabled() {
            emit_marker_line(makepad_camera2_acquisition_broker_h264_skipped_marker_line());
        } else {
            Self::start_camera_probe_once();
        }
    }

    fn emit_status_marker(phase: &str) {
        let config = Self::runtime_config();

        emit_marker_line(&makepad_camera_status_marker_line(
            phase,
            &runtime_text(&config, KEY_RUNTIME_PROFILE),
            &runtime_text(&config, KEY_TRANSPORT_PROFILE),
            &runtime_text(&config, KEY_MAKEPAD_REVISION),
            &runtime_text(&config, KEY_STUDIO_HOST),
        ));
    }

    fn emit_stereo_comparison_marker(phase: &str) {
        let config = Self::runtime_config();
        let tuning = Self::horizontal_alignment_tuning();

        emit_marker_line(&makepad_synthetic_stereo_comparison_marker_line(
            MakepadStereoComparisonMarkerInputs {
                phase,
                runtime_profile: &runtime_text(&config, KEY_RUNTIME_PROFILE),
                comparison_baseline: &runtime_text(&config, KEY_COMPARISON_BASELINE),
                camera_tier: &runtime_text(&config, KEY_CAMERA_TIER),
                acquisition_profile: &runtime_text(&config, KEY_ACQUISITION_PROFILE),
                transport_profile: &runtime_text(&config, KEY_TRANSPORT_PROFILE),
                projection_mode: &runtime_text(&config, KEY_CAMERA_PROJECTION_MODE),
                synthetic_scene: &runtime_text(&config, KEY_SYNTHETIC_SCENE),
                projection_scale: runtime_float(&config, KEY_PROJECTION_SCALE),
                xr_render_scale: runtime_float(&config, KEY_XR_RENDER_SCALE),
                texture_path: MakepadCameraTexturePath::direct_default(),
                aligned_projection: false,
                visible_projection_ready: false,
                makepad_fork_branch: &runtime_text(&config, KEY_MAKEPAD_BRANCH),
                makepad_fork_commit: &runtime_text(&config, KEY_MAKEPAD_REVISION),
            },
            tuning,
        ));
        Self::emit_projection_runtime_manifest_marker(phase, &config, tuning);
    }

    fn emit_projection_runtime_manifest_marker(
        phase: &str,
        config: &RuntimeConfig,
        tuning: HorizontalAlignmentTuning,
    ) {
        for line in makepad_projection_runtime_manifest_lines(phase, config, tuning) {
            emit_marker_line(&line);
        }
    }

    fn runtime_config() -> RuntimeConfig {
        makepad_runtime_config()
    }

    fn startup_camera_streaming_enabled() -> bool {
        let config = Self::runtime_config();
        hotload_bool(
            KEY_MAKEPAD_CAMERA_STREAMING_ENABLED,
            runtime_bool(&config, KEY_MAKEPAD_CAMERA_STREAMING_ENABLED),
        )
    }

    fn current_camera_streaming_enabled(&self) -> bool {
        hotload_bool(
            KEY_MAKEPAD_CAMERA_STREAMING_ENABLED,
            self.camera_shell_effective_camera_streaming_enabled,
        )
    }

    fn set_effective_remote_camera(remote_camera: Option<RemoteCameraEffectiveConfig>) {
        if let Ok(mut slot) = EFFECTIVE_REMOTE_CAMERA.lock() {
            *slot = remote_camera;
        }
    }

    fn effective_remote_camera_receiver() -> Option<RemoteCameraEffectiveConfig> {
        EFFECTIVE_REMOTE_CAMERA
            .lock()
            .ok()
            .and_then(|slot| slot.clone())
            .filter(|config| {
                config.enabled
                    && config.incoming_lane_count > 0
                    && matches!(
                        config.endpoint_role.as_str(),
                        "receiver" | "sender_receiver"
                    )
            })
    }

    fn apply_makepad_video_input_discovery_enabled(
        &mut self,
        cx: &mut Cx,
        phase: &str,
        enabled: bool,
    ) {
        if self.makepad_video_input_discovery_enabled == Some(enabled) {
            return;
        }
        self.makepad_video_input_discovery_enabled = Some(enabled);
        cx.set_video_input_discovery_enabled(enabled);
        emit_marker_line(&format!(
            "RUSTY_HOSTESS_MAKEPAD_CAMERA_DISCOVERY schema=rusty.gui.makepad.camera_discovery.v1 phase={} status=applied videoInputDiscoveryEnabled={} cameraStreamingEnabled={} settingId=makepad.camera.streaming.enabled",
            marker_token(phase),
            enabled,
            enabled,
        ));
    }

    fn initialize_hostess_shell_contract(&mut self) {
        self.shell_contract_read = shell_contract::read_selected_makepad_shell_contract();
        let _ = shell_contract::write_selected_makepad_shell_contract_read_receipt(
            &self.shell_contract_read,
        );
        let effective_settings =
            makepad_effective_settings::read_selected_makepad_effective_settings();
        emit_marker_line(&effective_settings.marker_line("startup"));
        let _ = makepad_effective_settings::write_selected_makepad_effective_settings_receipt(
            &effective_settings,
        );
        self.refresh_mesh_replay_runtime_from_selected_settings("startup", true);
        self.shell_xr_runtime = ShellXrRuntimeState::registered_xr_shell();
        self.refresh_hostess_shell_runtime_capability_receipt();
    }

    fn refresh_hostess_shell_runtime_capability_receipt(&mut self) {
        self.shell_runtime_capabilities =
            shell_runtime_capabilities::evaluate(&self.shell_contract_read, &self.shell_xr_runtime);
        let _ = shell_runtime_capabilities::write_selected_makepad_shell_runtime_capability_receipt(
            &self.shell_runtime_capabilities,
        );
    }

    fn broker_h264_enabled() -> bool {
        let remote_receiver = Self::effective_remote_camera_receiver();
        broker_h264_runtime::broker_h264_enabled(remote_receiver.as_ref())
    }

    fn broker_h264_requested_texture_path() -> MakepadCameraTexturePath {
        broker_h264_runtime::broker_h264_requested_texture_path()
    }

    fn broker_h264_source_sampling_mode() -> SourceSamplingMode {
        broker_h264_runtime::broker_h264_source_sampling_mode()
    }

    fn direct_camera_projection_geometry_profile() -> String {
        broker_h264_runtime::direct_camera_projection_geometry_profile()
    }

    fn broker_h264_stream_port(eye: StereoEye) -> u16 {
        let remote_receiver = Self::effective_remote_camera_receiver();
        broker_h264_runtime::broker_h264_stream_port(eye, remote_receiver.as_ref())
    }

    fn broker_h264_source_for_eye(eye: StereoEye) -> ExternalH264VideoSource {
        let remote_receiver = Self::effective_remote_camera_receiver();
        broker_h264_runtime::broker_h264_source_for_eye(eye, remote_receiver.as_ref())
    }

    fn broker_h264_source() -> ExternalH264VideoSource {
        let remote_receiver = Self::effective_remote_camera_receiver();
        broker_h264_runtime::broker_h264_source(remote_receiver.as_ref())
    }

    fn emit_hardware_buffer_import_marker(body: &str) {
        emit_marker_line(&makepad_hardware_buffer_import_marker_line(body));
    }

    fn emit_stereo_projection_marker(body: &str) {
        emit_marker_line(&makepad_stereo_projection_marker_line(body));
    }

    fn arm_cadence_probe(&mut self, cx: &mut Cx) {
        self.cadence_next_frame = Some(cx.new_next_frame());
        emit_marker_line(&makepad_cadence_start_marker_line(CADENCE_SAMPLE_SECONDS));
    }

    fn manifold_pose_publisher_config() -> ManifoldPosePublisherConfig {
        ManifoldPosePublisherConfig {
            enabled: hotload_bool(
                KEY_MANIFOLD_POSE_PUBLISH_ENABLED,
                DEFAULT_MANIFOLD_POSE_PUBLISH_ENABLED,
            ),
            broker_host: hotload_text(KEY_MANIFOLD_BROKER_HOST, DEFAULT_MANIFOLD_BROKER_HOST),
            broker_port: hotload_u16(
                KEY_MANIFOLD_BROKER_PORT,
                DEFAULT_MANIFOLD_BROKER_PORT,
                1,
                u16::MAX,
            ),
            stream_id: hotload_text(KEY_MANIFOLD_POSE_STREAM, DEFAULT_MANIFOLD_POSE_STREAM),
            source_id: hotload_text(KEY_MANIFOLD_POSE_SOURCE, DEFAULT_MANIFOLD_POSE_SOURCE),
            controller: Self::normalized_manifold_pose_controller(&hotload_text(
                KEY_MANIFOLD_POSE_CONTROLLER,
                DEFAULT_MANIFOLD_POSE_CONTROLLER,
            )),
            pose_kind: Self::normalized_manifold_pose_kind(&hotload_text(
                KEY_MANIFOLD_POSE_KIND,
                DEFAULT_MANIFOLD_POSE_KIND,
            )),
            sample_hz: hotload_f32(
                KEY_MANIFOLD_POSE_SAMPLE_HZ,
                DEFAULT_MANIFOLD_POSE_SAMPLE_HZ,
                1.0,
                120.0,
            ),
            connect_timeout_ms: hotload_u32(
                KEY_MANIFOLD_POSE_CONNECT_TIMEOUT_MS,
                DEFAULT_MANIFOLD_POSE_CONNECT_TIMEOUT_MS,
                50,
                5_000,
            ) as u64,
        }
    }

    fn normalized_manifold_pose_controller(value: &str) -> String {
        match value.trim().to_ascii_lowercase().as_str() {
            "left" => "left".to_string(),
            _ => "right".to_string(),
        }
    }

    fn normalized_manifold_pose_kind(value: &str) -> String {
        match value.trim().to_ascii_lowercase().as_str() {
            "aim" => "aim".to_string(),
            _ => "grip".to_string(),
        }
    }

    fn handle_manifold_pose_publish(&mut self, update: &XrUpdateEvent) {
        let config = Self::manifold_pose_publisher_config();
        if !config.enabled {
            self.manifold_pose_publisher = None;
            return;
        }

        let state = update.state.as_ref();
        let now_seconds = state.time.max(0.0);
        if self.manifold_pose_last_publish_time > 0.0
            && now_seconds - self.manifold_pose_last_publish_time < config.interval_seconds()
        {
            return;
        }
        self.manifold_pose_last_publish_time = now_seconds;

        if self
            .manifold_pose_publisher
            .as_ref()
            .is_none_or(|publisher| publisher.config() != &config)
        {
            emit_marker_line(&format!(
                "RUSTY_MAKEPAD_CONTROLLER_POSE_PROVIDER schema=rusty.gui.makepad.controller_pose_provider.v1 phase=configure status=ready stream={} source={} controller={} poseKind={} brokerHost={} brokerPort={} sampleHz={:.3} providerBoundary=stream.motion.object_pose sourceAgnostic=true controllerSpecificEstimator=false",
                marker_token(&config.stream_id),
                marker_token(&config.source_id),
                marker_token(&config.controller),
                marker_token(&config.pose_kind),
                marker_token(&config.broker_host),
                config.broker_port,
                config.sample_hz,
            ));
            self.manifold_pose_publisher = Some(ManifoldPosePublisher::new(config.clone()));
        }

        let controller = if config.controller == "left" {
            &state.left_controller
        } else {
            &state.right_controller
        };
        let (pose, pose_tracked) = if config.pose_kind == "aim" {
            (controller.aim_pose, controller.aim_tracked())
        } else {
            (controller.grip_pose, controller.grip_tracked())
        };
        let position = [pose.position.x, pose.position.y, pose.position.z];
        let orientation = [
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        ];
        let pose_is_finite = position.iter().all(|value| value.is_finite())
            && orientation.iter().all(|value| value.is_finite());
        let active = controller.active();
        let tracked = active && pose_tracked && pose_is_finite;

        self.manifold_pose_next_sequence_id = self.manifold_pose_next_sequence_id.saturating_add(1);
        let sequence_id = self.manifold_pose_next_sequence_id;
        let sample = ManifoldPoseSample {
            sequence_id,
            sample_time_unix_ns: ManifoldPoseSample::now_unix_ns(),
            xr_predicted_display_time_ns: (state.time * 1_000_000_000.0).round() as i64,
            controller: config.controller.clone(),
            pose_kind: config.pose_kind.clone(),
            active,
            tracked,
            position_m: position,
            orientation_xyzw: orientation,
        };
        let queued = self
            .manifold_pose_publisher
            .as_ref()
            .is_some_and(|publisher| publisher.publish(sample));
        if queued {
            self.manifold_pose_published_count =
                self.manifold_pose_published_count.saturating_add(1);
        } else {
            self.manifold_pose_dropped_count = self.manifold_pose_dropped_count.saturating_add(1);
        }
        if !queued
            || self.manifold_pose_published_count == 1
            || self.manifold_pose_published_count % 120 == 0
        {
            emit_marker_line(&format!(
                "RUSTY_MAKEPAD_CONTROLLER_POSE_PROVIDER schema=rusty.gui.makepad.controller_pose_provider.v1 phase=sample status={} stream={} sequenceId={} controller={} poseKind={} active={} tracked={} queued={} published={} dropped={} positionM={:.5},{:.5},{:.5}",
                if queued { "queued" } else { "dropped" },
                marker_token(&config.stream_id),
                sequence_id,
                marker_token(&config.controller),
                marker_token(&config.pose_kind),
                active,
                tracked,
                queued,
                self.manifold_pose_published_count,
                self.manifold_pose_dropped_count,
                position[0],
                position[1],
                position[2],
            ));
        }
    }

    #[cfg(target_os = "android")]
    fn xr_display_views_from_update(
        update: &XrUpdateEvent,
    ) -> android_camera_probe::XrDisplayViews {
        let state = update.state.as_ref();
        let left = state.left_eye_view;
        let right = state.right_eye_view;
        let predicted_display_time_ns = (state.time * 1_000_000_000.0).round() as i64;
        android_camera_probe::XrDisplayViews {
            left: android_camera_probe::XrDisplayEyeView {
                position: [
                    left.pose.position.x,
                    left.pose.position.y,
                    left.pose.position.z,
                ],
                orientation: [
                    left.pose.orientation.x,
                    left.pose.orientation.y,
                    left.pose.orientation.z,
                    left.pose.orientation.w,
                ],
                angle_left: left.fov.angle_left,
                angle_right: left.fov.angle_right,
                angle_up: left.fov.angle_up,
                angle_down: left.fov.angle_down,
                valid: left.valid,
            },
            right: android_camera_probe::XrDisplayEyeView {
                position: [
                    right.pose.position.x,
                    right.pose.position.y,
                    right.pose.position.z,
                ],
                orientation: [
                    right.pose.orientation.x,
                    right.pose.orientation.y,
                    right.pose.orientation.z,
                    right.pose.orientation.w,
                ],
                angle_left: right.fov.angle_left,
                angle_right: right.fov.angle_right,
                angle_up: right.fov.angle_up,
                angle_down: right.fov.angle_down,
                valid: right.valid,
            },
            predicted_display_time_ns,
            reference_space: "makepad-platform-local-space",
            projection_depth_meters: makepad_projection_depth_meters(),
            projection_preview_fov_y_degrees: makepad_projection_preview_fov_y_degrees(),
            projection_preview_offset_y_meters: makepad_projection_preview_offset_y_meters(),
            projection_raw_overscan: makepad_projection_raw_overscan(),
        }
    }

    #[cfg(target_os = "android")]
    fn update_runtime_xr_projection(&mut self, update: &XrUpdateEvent) {
        let views = Self::xr_display_views_from_update(update);
        let updated = if Self::broker_h264_enabled() {
            self.refresh_broker_h264_projection_plan(views)
        } else {
            android_camera_probe::update_stereo_projection_from_xr_views(views)
        };
        if updated {
            self.refresh_paired_import_projection_plan();
        }
    }

    #[cfg(target_os = "android")]
    fn refresh_broker_h264_projection_plan(
        &mut self,
        views: android_camera_probe::XrDisplayViews,
    ) -> bool {
        let (Some(left_metadata), Some(right_metadata)) = (
            self.broker_h264_left_projection_metadata.as_ref(),
            self.broker_h264_right_projection_metadata.as_ref(),
        ) else {
            return false;
        };
        let Some(pair) = self.paired_import_choice.as_mut() else {
            return false;
        };
        let Some((left_width, left_height)) =
            left_metadata.ready_size(pair.left.width, pair.left.height)
        else {
            return false;
        };
        let Some((right_width, right_height)) =
            right_metadata.ready_size(pair.right.width, pair.right.height)
        else {
            return false;
        };
        if left_width != right_width || left_height != right_height {
            return false;
        }
        let Some(decision) = broker_projection_plan_decision(left_metadata, right_metadata) else {
            return false;
        };
        let Some(plan) = (match decision.kind {
            BrokerProjectionPlanKind::FullFrameContent => {
                android_camera_probe::broker_full_frame_projection_plan_from_xr_views(
                    &left_metadata.camera_id,
                    &right_metadata.camera_id,
                    left_width,
                    left_height,
                    views,
                )
                .map(Camera2StereoPlan::from)
            }
            BrokerProjectionPlanKind::CameraProjection => left_metadata
                .android_projection_source()
                .zip(right_metadata.android_projection_source())
                .and_then(|(left_source, right_source)| {
                    android_camera_probe::broker_physical_projection_plan_from_xr_views(
                        left_source,
                        right_source,
                        left_width,
                        left_height,
                        views,
                    )
                    .map(Camera2StereoPlan::from)
                })
                .map(|mut plan| {
                    plan.left_camera_id = left_metadata.camera_id.clone();
                    plan.right_camera_id = right_metadata.camera_id.clone();
                    plan.width = left_width;
                    plan.height = left_height;
                    plan.coordinate_chain = format!(
                        "broker-h264-camera-projection-stream-header/{}",
                        plan.coordinate_chain
                    );
                    plan
                })
                .or_else(|| {
                    decision
                        .camera_matched_live_fallback_allowed
                        .then_some(())?;
                    Self::camera2_stereo_plan().map(|mut plan| {
                        plan.left_camera_id = left_metadata.camera_id.clone();
                        plan.right_camera_id = right_metadata.camera_id.clone();
                        plan.width = left_width;
                        plan.height = left_height;
                        plan.coordinate_chain = format!(
                            "broker-h264-camera-matched-live-camera2-fallback/{}",
                            plan.coordinate_chain
                        );
                        plan.fallback_reason =
                            "camera_matched_stream_header_missing_camera_projection_metadata"
                                .to_string();
                        plan
                    })
                }),
            BrokerProjectionPlanKind::HeadAnchoredProjectionArea => {
                android_camera_probe::broker_synthetic_projection_plan_from_xr_views(
                    &left_metadata.camera_id,
                    &right_metadata.camera_id,
                    left_width,
                    left_height,
                    views,
                )
                .map(Camera2StereoPlan::from)
            }
        }) else {
            return false;
        };

        pair.apply_broker_projection_plan(&plan, &decision, left_metadata, right_metadata);
        if !self.broker_h264_projection_plan_logged {
            self.broker_h264_projection_plan_logged = true;
            let config = Self::runtime_config();
            Self::emit_projection_runtime_manifest_marker(
                "broker-h264-projection-plan",
                &config,
                Self::horizontal_alignment_tuning(),
            );
            Self::emit_stereo_projection_marker(&broker_projection_plan_marker_fields(
                pair,
                &plan,
                left_metadata,
                right_metadata,
            ));
        }
        true
    }

    #[cfg(target_os = "android")]
    fn refresh_paired_import_projection_plan(&mut self) {
        let Some(plan) = Self::camera2_stereo_plan() else {
            return;
        };
        let Some(pair) = self.paired_import_choice.as_mut() else {
            return;
        };
        if !pair.matches_camera2_plan(&plan)
            || pair.left.width != plan.width as usize
            || pair.left.height != plan.height as usize
            || pair.right.width != plan.width as usize
            || pair.right.height != plan.height as usize
        {
            return;
        }

        pair.projection_metadata_ready = plan.projection_metadata_ready;
        pair.pose_source = plan.pose_source;
        pair.source_eye_mapping = makepad_display_source_eye_mapping().to_string();
        pair.coordinate_chain = plan.coordinate_chain;
        pair.fallback_reason = plan.fallback_reason;
        pair.left_surface_to_camera_h = plan.left_surface_to_camera_h;
        pair.right_surface_to_camera_h = plan.right_surface_to_camera_h;
        pair.left_surface_to_screen_h = plan.left_surface_to_screen_h;
        pair.right_surface_to_screen_h = plan.right_surface_to_screen_h;
        pair.left_screen_to_camera_h = plan.left_screen_to_camera_h;
        pair.right_screen_to_camera_h = plan.right_screen_to_camera_h;
        pair.left_screen_to_surface_h = plan.left_screen_to_surface_h;
        pair.right_screen_to_surface_h = plan.right_screen_to_surface_h;
        pair.projection_homography_ready = plan.projection_homography_ready;
        pair.runtime_xr_view_state_ready = plan.runtime_xr_view_state_ready;
        pair.openxr_contract = plan.openxr_contract.clone();
    }

    fn update_camera_projection_panel_streaming_enabled(&mut self, cx: &mut Cx) {
        let enabled = self.current_camera_streaming_enabled();
        self.apply_makepad_video_input_discovery_enabled(cx, "event", enabled);
        let panel_ref = self.ui.widget(cx, ids!(camera_projection_panel));
        let Some(mut panel) = panel_ref.borrow_mut::<MakepadStereoCameraPanel>() else {
            return;
        };
        panel.set_camera_streaming_enabled(cx, enabled);
    }

    fn handle_cadence_event(&mut self, cx: &mut Cx, event: &Event) {
        if matches!(event, Event::Startup)
            || (matches!(event, Event::XrUpdate(_)) && self.current_camera_streaming_enabled())
        {
            self.refresh_horizontal_alignment_tuning(cx);
        }

        if matches!(event, Event::Startup) && self.cadence_next_frame.is_none() {
            self.arm_cadence_probe(cx);
            return;
        }

        match event {
            Event::XrUpdate(_update) => {
                self.cadence_xr_update_count = self.cadence_xr_update_count.saturating_add(1);
                let camera_streaming_enabled = self.current_camera_streaming_enabled();
                if self
                    .shell_xr_runtime
                    .observe_update(cx.in_xr_mode(), _update)
                {
                    self.refresh_hostess_shell_runtime_capability_receipt();
                }
                if self
                    .matter_surface_source_selection
                    .mode()
                    .uses_live_openxr_hand()
                {
                    if let Some(marker) = self.live_hand_surface_source.observe_update(
                        cx,
                        _update,
                        self.shell_xr_runtime.xr_update_count(),
                        "xr-update",
                        Some(MATTER_SURFACE_LIVE_OBSERVE_INTERVAL_SECONDS),
                    ) {
                        emit_marker_line(&marker);
                    }
                }
                self.record_xr_pose_snapshot(_update);
                self.handle_manifold_breath_feedback_subscription();
                self.handle_manifold_pose_publish(_update);
                #[cfg(target_os = "android")]
                self.update_stimulus_runtime_xr_projection(_update);
                self.handle_stimulus_controller_randomize(cx, _update, camera_streaming_enabled);
                if camera_streaming_enabled {
                    self.handle_projection_target_joystick(cx, _update);
                    self.handle_projection_target_breath_feedback(cx);
                    #[cfg(target_os = "android")]
                    self.update_runtime_xr_projection(_update);
                    let adopted = self.try_adopt_pending_stereo_camera_frame("xr-update");
                    if (adopted || self.adopted_stereo_camera_frame.is_some())
                        && !self.paired_import_finished
                    {
                        self.complete_paired_import_if_ready(cx);
                    } else if adopted {
                        self.bind_camera_projection_panel(cx);
                    }
                }
            }
            Event::Draw(_) => {
                self.cadence_draw_event_count = self.cadence_draw_event_count.saturating_add(1);
            }
            _ => {}
        }

        let Some(next_frame) = self.cadence_next_frame else {
            return;
        };
        let Some(next_frame_event) = next_frame.is_event(event) else {
            return;
        };

        if !self.cadence_started {
            self.cadence_started = true;
            self.cadence_start_time = next_frame_event.time;
            self.cadence_last_sample_time = next_frame_event.time;
        }

        self.cadence_frame_count = self.cadence_frame_count.saturating_add(1);
        self.handle_mesh_replay_runtime_cadence(cx, next_frame_event.time);
        let interval_seconds = (next_frame_event.time - self.cadence_last_sample_time).max(0.0);
        if interval_seconds >= CADENCE_SAMPLE_SECONDS {
            self.emit_cadence_sample(cx, next_frame_event.time, interval_seconds);
        }

        self.cadence_next_frame = Some(cx.new_next_frame());
    }

    #[cfg(target_os = "android")]
    fn request_android_xr_start_fallback_once(&mut self, cx: &mut Cx, phase: &str) {
        if ANDROID_XR_START_FALLBACK_REQUESTED.swap(true, Ordering::SeqCst) {
            return;
        }
        if cx.in_xr_mode() {
            emit_marker_line(&format!(
                "RUSTY_MAKEPAD_XR_START_FALLBACK schema=rusty.gui.makepad.xr_start_fallback.v1 phase={} status=already_presenting directXrActivity=true",
                phase
            ));
            return;
        }
        cx.xr_start_presenting();
        emit_marker_line(&format!(
            "RUSTY_MAKEPAD_XR_START_FALLBACK schema=rusty.gui.makepad.xr_start_fallback.v1 phase={} status=requested directXrActivity=true permissionFlowFallback=true",
            phase
        ));
    }
}

impl MatchEvent for App {
    fn handle_startup(&mut self, cx: &mut Cx) {
        Self::emit_startup_markers_once("startup");
        let config = Self::runtime_config();
        cx.xr_set_native_passthrough(makepad_native_passthrough_enabled());
        cx.xr_set_render_scale(runtime_float(&config, KEY_XR_RENDER_SCALE) as f32);
        #[cfg(target_os = "android")]
        self.request_android_xr_start_fallback_once(cx, "match_startup");
    }

    fn handle_actions(&mut self, cx: &mut Cx, actions: &Actions) {
        if self
            .ui
            .button(cx, ids!(emit_marker_button))
            .clicked(actions)
        {
            Self::emit_status_marker("button");
        }
    }
}

impl AppMain for App {
    fn script_mod(vm: &mut ScriptVm) -> ScriptValue {
        crate::makepad_widgets::script_mod(vm);
        makepad_xr::script_mod(vm);
        crate::makepad_stereo_camera_panel::script_mod(vm);
        crate::matter_world_particle_billboard::script_mod(vm);
        crate::matter_world_adf_debug::script_mod(vm);
        crate::stimulus_stereo_field_live::script_mod(vm);
        crate::makepad_app_live_design::script_mod(vm)
    }

    fn after_new_from_script(vm: &mut ScriptVm, app: &mut Self) {
        Self::emit_startup_markers_once("startup");
        app.initialize_hostess_shell_contract();
        let camera_streaming_enabled = app.current_camera_streaming_enabled();
        app.apply_makepad_video_input_discovery_enabled(
            vm.cx_mut(),
            "startup",
            camera_streaming_enabled,
        );
    }

    fn handle_event(&mut self, cx: &mut Cx, event: &Event) {
        #[cfg(target_os = "android")]
        self.request_android_xr_start_fallback_once(cx, "first_event");
        self.match_event(cx, event);
        self.handle_cadence_event(cx, event);
        self.update_camera_projection_panel_streaming_enabled(cx);
        self.handle_paired_import_event(cx, event);
        self.ui.handle_event(cx, event, &mut Scope::empty());
    }
}
