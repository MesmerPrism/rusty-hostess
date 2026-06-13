pub use makepad_xr::makepad_widgets;

#[cfg(target_os = "android")]
mod acamera_sys;
#[cfg(target_os = "android")]
mod android_camera_probe;
mod broker_h264_runtime;
mod camera_pair;
mod camera_texture_path;
#[allow(dead_code, unused_imports)]
mod hostess_camera_model;
#[allow(dead_code, unused_imports)]
mod hostess_contracts;
mod live_hand_surface;
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
use matter_world_adf_debug::{MatterWorldAdfDebugCells, HOSTESS_WORLD_ADF_DEBUG_DRAW_LIMIT_MAX};
use matter_world_particle_billboard::{
    MatterWorldParticleBillboardCloud, HOSTESS_WORLD_PARTICLE_BILLBOARD_DRAW_LIMIT_MAX,
};
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
    makepad_projection_target_breath_scale, makepad_projection_target_breath_smoothing_alpha,
    makepad_projection_target_joystick_controls_enabled_from_value,
    makepad_projection_target_offset_step, makepad_projection_target_offset_x_uv,
    makepad_projection_target_offset_y_uv, makepad_projection_target_scale,
    makepad_projection_target_scale_step, PROJECTION_TARGET_BREATH_DEFAULT_SMOOTHING_ALPHA,
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

script_mod! {
    use mod.pod.*
    use mod.math.*
    use mod.shader.*
    use mod.draw
    use mod.geom
    use mod.prelude.widgets.*
    use mod.widgets.*

    mod.widgets.MatterWorldParticleBillboardCloudBase = #(MatterWorldParticleBillboardCloud::register_widget(vm))
    mod.widgets.MatterWorldParticleBillboardCloud = set_type_default() do mod.widgets.MatterWorldParticleBillboardCloudBase{
        body: mod.widgets.XrBodyKind.Fixed
        shared_object_policy: mod.widgets.XrSharedObjectPolicy.None
        draw_cube +: {
            alpha_blend: true
            backface_culling: false
            light_dir: vec3(0.0, 0.0, 1.0)
            billboard_uv: varying(vec2f)
            billboard_state: varying(vec4f)

            vertex: fn() {
                let model_view = self.draw_list.view_transform * self.transform
                let center_world = model_view * vec4(self.cube_pos.x, self.cube_pos.y, self.cube_pos.z, 1.0)
                self.world = center_world

                let face_live = step(0.5, self.geom.geom_normal.z)
                let center_view = self.draw_pass.camera_view * center_world
                if face_live < 0.5 || center_view.z >= -0.000001 {
                    self.billboard_uv = vec2(0.0, 0.0)
                    self.billboard_state = vec4(0.0, 0.0, 1.0, 0.0)
                    self.lit_color = vec4(0.0, 0.0, 0.0, 0.0)
                    self.vertex_pos = vec4(2.0, 2.0, 2.0, 1.0)
                    return
                }

                let frame = clamp(self.cube_size.y, 0.0, 0.999985)
                let rotation = self.cube_size.z + frame * 6.2831853
                let cs = cos(rotation)
                let sn = sin(rotation)
                let raw_corner = self.geom.geom_pos.xy * 2.0
                let corner = vec2(
                    raw_corner.x * cs - raw_corner.y * sn,
                    raw_corner.x * sn + raw_corner.y * cs
                )

                let eye_origin = (self.draw_pass.camera_inv * vec4(0.0, 0.0, 0.0, 1.0)).xyz
                let normal_world = normalize((model_view * vec4(self.light_dir.x, self.light_dir.y, self.light_dir.z, 0.0)).xyz)
                let eye_dir = normalize(eye_origin - center_world.xyz)
                let facing = clamp(dot(normal_world, eye_dir), 0.0, 1.0)
                let frame_scale = 0.92 + 0.20 * frame
                let facing_scale = mix(0.86, 1.08, facing)
                let diameter = max(self.cube_size.x, 0.002) * frame_scale * facing_scale
                let view_pos = center_view + vec4(corner.x * diameter * 0.5, corner.y * diameter * 0.5, 0.0, 0.0)
                let projected = self.draw_pass.camera_projection * view_pos
                self.billboard_uv = corner * 0.5 + vec2(0.5, 0.5)
                self.billboard_state = vec4(frame, facing, clamp((-center_view.z - 0.05) / 12.0, 0.0, 1.0), 1.0)
                self.lit_color = self.color
                self.vertex_pos = projected
            }

            pixel: fn() {
                if self.billboard_state.w < 0.5 {
                    discard()
                }
                let p = self.billboard_uv * 2.0 - vec2(1.0, 1.0)
                let radius = length(p)
                if radius > 1.02 {
                    discard()
                }
                let frame = self.billboard_state.x
                let animated_ring = 0.60 + 0.08 * sin(frame * 6.2831853 + p.x * 3.1 - p.y * 2.2)
                let ring = 1.0 - smoothstep(0.050, 0.165, abs(radius - animated_ring))
                let core = (1.0 - smoothstep(0.12, 0.42, radius)) * 0.28
                let ripple = 0.72 + 0.28 * sin((p.x + p.y) * 7.0 + frame * 12.566371)
                let edge = 1.0 - smoothstep(0.92, 1.02, radius)
                let mask = clamp(max(core, ring * ripple) * edge, 0.0, 1.0)
                if mask < 0.002 {
                    discard()
                }
                let facing_tint = 0.80 + 0.20 * self.billboard_state.y
                let depth_atten = pow(2.0, -1.5 * self.billboard_state.z)
                let alpha = clamp(mask * self.color.w * 0.92, 0.0, 0.58)
                let rgb = min(self.color.xyz * facing_tint * depth_atten, vec3(1.0, 1.0, 1.0))
                return vec4(rgb.x * alpha, rgb.y * alpha, rgb.z * alpha, alpha)
            }

            fragment: fn() {
                self.fb0 = depth_clip(self.world, self.pixel(), self.depth_clip)
            }
        }
    }

    mod.widgets.MatterWorldAdfDebugCellsBase = #(MatterWorldAdfDebugCells::register_widget(vm))
    mod.widgets.MatterWorldAdfDebugCells = set_type_default() do mod.widgets.MatterWorldAdfDebugCellsBase{
        body: mod.widgets.XrBodyKind.Fixed
        shared_object_policy: mod.widgets.XrSharedObjectPolicy.None
        draw_cube +: {
            alpha_blend: true
            backface_culling: false
            light_dir: vec3(0.35, 0.55, 1.0)
        }
    }

    startup() do #(App::script_component(vm)){
        ui: XrRoot{
            window.inner_size: vec2(760, 480)
            pass.clear_color: #x203040
            camera.fov_y: 36.0
            camera.desktop_target: vec3(0.0, -0.05, -0.72)
            camera.distance: 1.65
            env.gravity: 0.0
            env.env_cube: false
            env.depth_mesh: false

            camera_projection_scene := XrNode{
                pos: vec3(0.0, 0.0, 0.0)

                stimulus_stereo_field := mod.widgets.StimulusStereoFieldPanel{
                    body: mod.widgets.XrBodyKind.Fixed
                    pos: vec3(0.0, 0.0, -1.0)
                }

                camera_projection_panel := mod.widgets.MakepadStereoCameraPanel{
                    body: mod.widgets.XrBodyKind.Fixed
                    size: vec3(1.0, 1.0, 0.010)
                    pos: vec3(0.0, 0.0, -1.0)
                }

                matter_particle_cloud := mod.widgets.MatterWorldParticleBillboardCloud{
                    body: mod.widgets.XrBodyKind.Fixed
                    pos: vec3(0.0, 0.0, 0.0)
                }

                matter_adf_debug_cells := mod.widgets.MatterWorldAdfDebugCells{
                    body: mod.widgets.XrBodyKind.Fixed
                    pos: vec3(0.0, 0.0, 0.0)
                }
            }

            camera_video_view := XrView{
                visible: false
                pos: vec3(0.0, -0.04, -0.764)
                logical_size: vec2(960, 540)
                pixel_scale: 0.00096
                dpi_factor: 1.0

                SolidView{
                    width: Fill
                    height: Fill
                    flow: Right
                    spacing: 0
                    draw_bg.color: #x05090dff

                    left_camera_video := Video{
                        width: 480
                        height: Fill
                        autoplay: false
                        show_controls: false
                    }

                    right_camera_video := Video{
                        width: 480
                        height: Fill
                        autoplay: false
                        show_controls: false
                    }
                }
            }

            xr_permissions := XrPermissionsFlow{}
        }
    }
}

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

    fn refresh_mesh_replay_runtime_from_selected_settings(
        &mut self,
        phase: &str,
        force: bool,
    ) -> bool {
        let identity = makepad_effective_settings::selected_makepad_effective_settings_identity();
        if !force {
            if !identity.runtime_settings_changed_from(
                self.mesh_replay_effective_settings_path.as_deref(),
                self.current_mesh_replay_effective_settings_modified_ns(),
                self.mesh_replay_effective_settings_revision_key.as_deref(),
            ) {
                return false;
            }
        }

        let runtime_revision_key = identity.runtime_settings_revision_key();
        let gpu_proof_revision_key = identity.gpu_proof_settings_revision_key();
        let selection = makepad_effective_settings::read_selected_mesh_replay_runtime();
        let runtime_ready = selection.runtime.is_some();
        let marker_line = if selection.runtime.is_none() {
            Some(selection.marker_line(phase))
        } else {
            None
        };
        let adoption_marker_line =
            selection.adoption_marker_line(phase, &identity, runtime_revision_key.as_deref());
        self.mesh_replay_effective_settings_path = selection.source_effective_settings_path.clone();
        self.mesh_replay_effective_settings_revision_key = runtime_revision_key.clone();
        self.mesh_replay_effective_settings_gpu_proof_revision_key = gpu_proof_revision_key.clone();
        self.mesh_replay_effective_settings_modified_ns =
            selection.source_modified_ns.unwrap_or_default();
        self.mesh_replay_effective_settings_has_modified_ns =
            selection.source_modified_ns.is_some();
        self.camera_shell_effective_render_scale = selection.render_scale.unwrap_or_default();
        self.camera_shell_effective_render_scale_present = selection.render_scale.is_some();
        self.camera_shell_effective_camera_streaming_enabled = selection
            .camera_streaming_enabled
            .unwrap_or(DEFAULT_MAKEPAD_CAMERA_STREAMING_ENABLED);
        Self::set_effective_remote_camera(selection.remote_camera.clone());
        self.matter_world_particle_draw_limit = selection
            .particle_render_draw_limit
            .unwrap_or(DEFAULT_PARTICLE_RENDER_DRAW_LIMIT)
            .min(MATTER_WORLD_PARTICLE_DRAW_LIMIT_MAX);
        self.matter_world_particle_draw_limit_configured =
            selection.particle_render_draw_limit.is_some();
        self.matter_world_particle_animation_mode = selection
            .particle_render_animation_mode
            .unwrap_or(DEFAULT_PARTICLE_RENDER_ANIMATION_MODE);
        self.matter_world_particle_size_scale = selection
            .particle_render_size_scale
            .unwrap_or(DEFAULT_PARTICLE_RENDER_SIZE_SCALE);
        self.matter_world_particle_size_scale_configured =
            selection.particle_render_size_scale.is_some();
        self.camera_shell_feature_uniforms = selection.feature_uniforms;
        self.matter_surface_force_authority =
            selection.particle_force_authority.unwrap_or_default();
        self.matter_surface_gpu_force_promotion_readiness =
            MatterSurfaceGpuForcePromotionReadiness::from_provider_ab_receipt(
                selection.gpu_force_provider_ab_receipt.unwrap_or_default(),
            );
        self.matter_surface_worker = selection
            .matter_surface_runtime
            .map(QuestMakepadMatterSurfaceWorker::from_runtime);
        self.matter_surface_frame_markers_emitted = 0;
        self.matter_surface_worker_markers_emitted = 0;
        self.matter_surface_live_source_worker_markers_emitted = 0;
        self.reset_matter_surface_gpu_proof_markers();
        self.emit_matter_surface_gpu_proof_epoch_marker(
            phase,
            selection.source_effective_settings_path.as_deref(),
            gpu_proof_revision_key.as_deref(),
        );
        self.matter_surface_world_particle_markers_emitted = 0;
        self.matter_surface_world_particle_draw_markers_emitted = 0;
        self.matter_surface_world_particle_draw_waiting_marker_emitted = false;
        self.matter_surface_world_adf_debug_markers_emitted = 0;
        self.matter_surface_world_adf_debug_draw_markers_emitted = 0;
        self.matter_surface_world_adf_debug_draw_waiting_marker_emitted = false;
        self.matter_surface_last_step_seconds = f64::NEG_INFINITY;
        self.matter_surface_cached_panel_overlay_frame = MatterSurfacePanelOverlayFrame::default();
        self.matter_surface_cached_world_particle_batch = None;
        self.matter_surface_cached_world_adf_debug_batch = None;
        self.matter_particle_texture.reset_markers();
        self.live_hand_surface_source.reset_markers();
        self.matter_surface_source_selection = MatterSurfaceSourceSelection::from_runtime();
        self.stimulus_stereo_field_state = if let Some(payload) =
            selection.stimulus_profile.as_ref()
        {
            match StimulusStereoFieldState::from_profile_payload(payload) {
                Ok(state) => state,
                Err(error) => {
                    emit_marker_line(&format!(
                            "RUSTY_HOSTESS_MAKEPAD_STIMULUS_DRAW schema=rusty.hostess.makepad.stimulus_draw.v1 phase={} status=rejected issue={} profileSelected=true renderPath=makepad-xr-fragment-preview",
                            marker_token(phase),
                            marker_token(&error),
                        ));
                    StimulusStereoFieldState::disabled()
                }
            }
        } else {
            if let Some(issue) = selection.stimulus_issue.as_deref() {
                emit_marker_line(&format!(
                        "RUSTY_HOSTESS_MAKEPAD_STIMULUS_DRAW schema=rusty.hostess.makepad.stimulus_draw.v1 phase={} status=rejected issue={} profileSelected=false renderPath=makepad-xr-fragment-preview",
                        marker_token(phase),
                        marker_token(issue),
                    ));
            }
            StimulusStereoFieldState::disabled()
        };
        self.stimulus_surface_projection_rows = StimulusSurfaceProjectionRows::default();
        self.stimulus_stereo_field_markers_emitted = 0;
        self.stimulus_volume_gpu_probe_markers_emitted = 0;
        self.stimulus_volume_gpu_probe_pending = None;
        self.stimulus_volume_raymarch_preview_markers_emitted = 0;
        self.stimulus_volume_raymarch_preview_pending = None;
        self.stimulus_volume_image_preview_markers_emitted = 0;
        self.stimulus_volume_image_preview_pending = None;
        self.stimulus_volume_image_preview_texture = None;
        self.stimulus_volume_texture_adoption_markers_emitted = 0;
        emit_marker_line(&self.matter_surface_source_selection.marker_line(phase));
        emit_marker_line(&adoption_marker_line);
        self.mesh_replay_runtime = selection.runtime;
        self.recorded_hand_surface_source = self
            .mesh_replay_runtime
            .as_ref()
            .and_then(|runtime| {
                match RecordedHandSurfaceSource::from_replay_runtime(
                    selection.source_effective_settings_path.as_deref(),
                    runtime,
                ) {
                    Ok(source) => source,
                    Err(error) => {
                        emit_marker_line(&format!(
                            "RUSTY_HOSTESS_MAKEPAD_RECORDED_HAND_SURFACE_SOURCE schema=rusty.hostess.makepad.recorded_hand_surface_source.v1 phase={} status=error issue={}",
                            marker_token(phase),
                            marker_token(&error),
                        ));
                        None
                    }
                }
            });

        if let Some(marker_line) = marker_line {
            emit_marker_line(&marker_line);
        }
        if runtime_ready {
            emit_marker_line(&self.camera_shell_feature_uniform_marker_line(phase));
        }
        if let Some(source) = self.recorded_hand_surface_source.as_ref() {
            emit_marker_line(&source.marker_line(phase));
        }
        if let Some(runtime) = self.mesh_replay_runtime.as_mut() {
            runtime.step(0.0);
            if runtime.should_emit_config_marker() {
                emit_marker_line(&runtime.config_marker_line(phase));
            }
        }
        true
    }

    fn camera_shell_feature_uniform_marker_line(&self, phase: &str) -> String {
        format!(
            "RUSTY_QUEST_MAKEPAD_CAMERA_SHELL_FEATURES schema=rusty.quest.makepad.camera_shell_feature_uniforms.v1 phase={} status=ready collisionEnabled={} sdfAdfOverlayMode={} particlesEnabled={} particleForceAuthority={} particleRenderDrawLimit={} particleRenderDrawLimitSource={} particleRenderAnimationMode={} particleRenderSizeScale={} particleRenderSizeScaleSource={} renderScale={} sourcePath={}",
            marker_token(phase),
            self.camera_shell_feature_uniforms.collision_enabled >= 0.5,
            marker_token(camera_shell_sdf_adf_mode_token(
                self.camera_shell_feature_uniforms.sdf_adf_overlay_mode,
            )),
            self.camera_shell_feature_uniforms.particles_enabled >= 0.5,
            marker_token(self.matter_surface_force_authority.as_str()),
            self.current_matter_world_particle_draw_limit(),
            self.matter_world_particle_draw_limit_source(),
            marker_token(self.current_matter_world_particle_animation_mode().as_str()),
            marker_f32_token(Some(self.current_matter_world_particle_size_scale())),
            self.matter_world_particle_size_scale_source(),
            marker_f32_token(self.current_camera_shell_effective_render_scale()),
            marker_token(
                self.mesh_replay_effective_settings_path
                    .as_deref()
                    .unwrap_or("none")
            ),
        )
    }

    fn current_camera_shell_effective_render_scale(&self) -> Option<f32> {
        if self.camera_shell_effective_render_scale_present {
            Some(self.camera_shell_effective_render_scale)
        } else {
            None
        }
    }

    fn current_matter_world_particle_draw_limit(&self) -> usize {
        if self.matter_world_particle_draw_limit_configured {
            self.matter_world_particle_draw_limit
                .min(MATTER_WORLD_PARTICLE_DRAW_LIMIT_MAX)
        } else {
            DEFAULT_PARTICLE_RENDER_DRAW_LIMIT.min(MATTER_WORLD_PARTICLE_DRAW_LIMIT_MAX)
        }
    }

    fn current_matter_world_particle_animation_mode(&self) -> ParticleRenderAnimationMode {
        self.matter_world_particle_animation_mode
    }

    fn current_matter_world_particle_size_scale(&self) -> f32 {
        if self.matter_world_particle_size_scale.is_finite()
            && self.matter_world_particle_size_scale > 0.0
        {
            self.matter_world_particle_size_scale
        } else {
            DEFAULT_PARTICLE_RENDER_SIZE_SCALE
        }
    }

    fn matter_world_particle_size_scale_source(&self) -> &'static str {
        if self.matter_world_particle_size_scale_configured {
            "effective-settings"
        } else {
            "default"
        }
    }

    fn matter_world_particle_draw_limit_source(&self) -> &'static str {
        if self.matter_world_particle_draw_limit_configured {
            "effective-settings"
        } else {
            "default"
        }
    }

    fn current_mesh_replay_effective_settings_modified_ns(&self) -> Option<u128> {
        if self.mesh_replay_effective_settings_has_modified_ns {
            Some(self.mesh_replay_effective_settings_modified_ns)
        } else {
            None
        }
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

    fn manifold_breath_feedback_config() -> ManifoldBreathFeedbackConfig {
        ManifoldBreathFeedbackConfig {
            enabled: hotload_bool(
                KEY_MANIFOLD_BREATH_FEEDBACK_ENABLED,
                DEFAULT_MANIFOLD_BREATH_FEEDBACK_ENABLED,
            ),
            broker_host: hotload_text(KEY_MANIFOLD_BROKER_HOST, DEFAULT_MANIFOLD_BROKER_HOST),
            broker_port: hotload_u16(
                KEY_MANIFOLD_BROKER_PORT,
                DEFAULT_MANIFOLD_BROKER_PORT,
                1,
                u16::MAX,
            ),
            stream_id: hotload_text_any(
                &[
                    KEY_MANIFOLD_BREATH_FEEDBACK_STREAM,
                    makepad_config::KEY_PROJECTION_TARGET_BREATH_STREAM,
                ],
                DEFAULT_MANIFOLD_BREATH_FEEDBACK_STREAM,
            ),
            receiver_id: hotload_text(
                KEY_MANIFOLD_BREATH_FEEDBACK_RECEIVER,
                DEFAULT_MANIFOLD_BREATH_FEEDBACK_RECEIVER,
            ),
            connect_timeout_ms: hotload_u32(
                KEY_MANIFOLD_BREATH_FEEDBACK_CONNECT_TIMEOUT_MS,
                DEFAULT_MANIFOLD_BREATH_FEEDBACK_CONNECT_TIMEOUT_MS,
                50,
                5_000,
            ) as u64,
        }
    }

    fn manifold_breath_feedback_config_marker_line(
        config: &ManifoldBreathFeedbackConfig,
    ) -> String {
        let status = if config.enabled {
            "enabled"
        } else {
            "disabled"
        };
        format!(
            "RUSTY_MAKEPAD_BREATH_FEEDBACK_CONFIG schema=rusty.gui.makepad.breath_feedback_config.v1 phase=hotload status={} enabled={} enabledRaw={} stream={} streamRaw={} receiver={} receiverRaw={} brokerHost={} brokerHostRaw={} brokerPort={} brokerPortRaw={} connectTimeoutMs={} connectTimeoutRaw={} flagsOwner=hostessctl.record_values",
            status,
            config.enabled,
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BREATH_FEEDBACK_ENABLED)),
            marker_token(&config.stream_id),
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BREATH_FEEDBACK_STREAM)),
            marker_token(&config.receiver_id),
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BREATH_FEEDBACK_RECEIVER)),
            marker_token(&config.broker_host),
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BROKER_HOST)),
            config.broker_port,
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BROKER_PORT)),
            config.connect_timeout_ms,
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BREATH_FEEDBACK_CONNECT_TIMEOUT_MS)),
        )
    }

    fn runtime_marker_value(key: &'static str) -> String {
        runtime_property_value(key).unwrap_or_else(|| "default".to_string())
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

    fn projection_target_scale() -> f32 {
        makepad_projection_target_scale()
    }

    fn projection_target_joystick_controls_enabled() -> bool {
        makepad_projection_target_joystick_controls_enabled_from_value(&hotload_text_any(
            &[
                makepad_config::KEY_PROJECTION_TARGET_JOYSTICK_CONTROLS,
                KEY_MAKEPAD_PROJECTION_TARGET_JOYSTICK_CONTROLS,
            ],
            DEFAULT_MAKEPAD_PROJECTION_TARGET_JOYSTICK_CONTROLS,
        ))
    }

    fn projection_target_breath_controls_enabled() -> bool {
        makepad_projection_target_breath_controls_enabled_from_value(&hotload_text(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_CONTROLS,
            "off",
        ))
    }

    fn handle_projection_target_joystick(&mut self, cx: &mut Cx, update: &XrUpdateEvent) {
        if !Self::projection_target_joystick_controls_enabled() {
            self.projection_target_joystick_scale_ready = false;
            self.projection_target_joystick_last_time = 0.0;
            return;
        }

        let breath_controls_scale = Self::projection_target_breath_controls_enabled();
        let state = update.state.as_ref();
        let now_seconds = state.time.max(0.0);
        if !self.projection_target_joystick_scale_ready {
            let tuning = self.current_horizontal_alignment_tuning();
            self.projection_target_joystick_offset_x_uv =
                tuning.projection_target_offset_x_uv.clamp(-0.5, 0.5);
            self.projection_target_joystick_offset_y_uv =
                tuning.projection_target_offset_y_uv.clamp(-0.5, 0.5);
            self.projection_target_joystick_scale = tuning
                .projection_target_scale
                .clamp(PROJECTION_TARGET_MIN_SCALE, PROJECTION_TARGET_MAX_SCALE);
            self.projection_target_joystick_scale_ready = true;
            self.projection_target_joystick_last_time = now_seconds;
            Self::emit_stereo_projection_marker(&format!(
                "phase=projection-target-controller status=active source=makepad-xr-actions referenceSource=quest-composite-layer-apk projectionTargetJoystickControls=offset-scale controls=leftStick:projectionTargetOffsetUv,rightStickY:projectionTargetScale,rightA:resetOffsetAndProjectionTargetScale coordinateSpace=display-eye-screen-uv yConvention=stickUpMovesTargetUp projectionAreaScaleControlRole=diagnostic-canvas-scale-runtime-property projectionAreaScaleMin={:.4} projectionAreaScaleMax={:.4} projectionTargetScaleControlRole=reference-target-footprint-runtime-adjustment projectionTargetScaleMin={:.4} projectionTargetScaleMax={:.4} projectionTargetOffsetXUv={:.4} projectionTargetOffsetYUv={:.4} projectionTargetScale={:.4} projectionAreaScaleX={:.4} projectionAreaScaleY={:.4}",
                PROJECTION_AREA_MIN_SCALE,
                PROJECTION_AREA_MAX_SCALE,
                PROJECTION_TARGET_MIN_SCALE,
                PROJECTION_TARGET_MAX_SCALE,
                self.projection_target_joystick_offset_x_uv,
                self.projection_target_joystick_offset_y_uv,
                tuning.projection_target_scale,
                tuning.projection_area_scale_x,
                tuning.projection_area_scale_y,
            ));
        }

        let dt_seconds = if self.projection_target_joystick_last_time > 0.0 {
            (now_seconds - self.projection_target_joystick_last_time).clamp(0.0, 0.1) as f32
        } else {
            0.0
        };
        self.projection_target_joystick_last_time = now_seconds;

        let mut changed = false;
        let mut reset = false;
        if update.clicked_a() {
            self.projection_target_joystick_offset_x_uv = 0.0;
            self.projection_target_joystick_offset_y_uv = 0.0;
            self.projection_target_joystick_scale = 1.0;
            changed = true;
            reset = true;
        }
        if state.left_controller.active() {
            if let Some(next_offset_x) = makepad_projection_target_offset_step(
                self.projection_target_joystick_offset_x_uv,
                state.left_controller.stick.x,
                dt_seconds,
                false,
            ) {
                if (next_offset_x - self.projection_target_joystick_offset_x_uv).abs() > 0.0001 {
                    self.projection_target_joystick_offset_x_uv = next_offset_x;
                    changed = true;
                }
            }
            if let Some(next_offset_y) = makepad_projection_target_offset_step(
                self.projection_target_joystick_offset_y_uv,
                state.left_controller.stick.y,
                dt_seconds,
                true,
            ) {
                if (next_offset_y - self.projection_target_joystick_offset_y_uv).abs() > 0.0001 {
                    self.projection_target_joystick_offset_y_uv = next_offset_y;
                    changed = true;
                }
            }
        }
        if state.right_controller.active() && !breath_controls_scale {
            if let Some(next_scale) = makepad_projection_target_scale_step(
                self.projection_target_joystick_scale,
                state.right_controller.stick.y,
                dt_seconds,
            ) {
                if (next_scale - self.projection_target_joystick_scale).abs() > 0.0001 {
                    self.projection_target_joystick_scale = next_scale;
                    changed = true;
                }
            }
        }
        let frame = self.cadence_xr_update_count;
        let should_sample_log = self.projection_target_joystick_last_log_frame == 0
            || frame.saturating_sub(self.projection_target_joystick_last_log_frame) >= 60;
        if !changed {
            if should_sample_log {
                let tuning = self.current_horizontal_alignment_tuning();
                Self::emit_stereo_projection_marker(&format!(
                    "phase=projection-target-input status=sampled source=controller referenceSource=quest-composite-layer-apk changed=false projectionAreaScaleControlRole=diagnostic-canvas-scale-runtime-property projectionAreaScaleMin={:.4} projectionAreaScaleMax={:.4} projectionTargetScaleControlRole=reference-target-footprint-runtime-adjustment projectionTargetScaleMin={:.4} projectionTargetScaleMax={:.4} leftActive={} rightActive={} leftStickX={:.4} leftStickY={:.4} rightStickY={:.4} projectionTargetOffsetXUv={:.4} projectionTargetOffsetYUv={:.4} projectionTargetScale={:.4} projectionAreaScaleX={:.4} projectionAreaScaleY={:.4}",
                    PROJECTION_AREA_MIN_SCALE,
                    PROJECTION_AREA_MAX_SCALE,
                    PROJECTION_TARGET_MIN_SCALE,
                    PROJECTION_TARGET_MAX_SCALE,
                    state.left_controller.active(),
                    state.right_controller.active(),
                    state.left_controller.stick.x,
                    state.left_controller.stick.y,
                    state.right_controller.stick.y,
                    self.projection_target_joystick_offset_x_uv,
                    self.projection_target_joystick_offset_y_uv,
                    tuning.projection_target_scale,
                    tuning.projection_area_scale_x,
                    tuning.projection_area_scale_y,
                ));
                self.projection_target_joystick_last_log_frame = frame;
            }
            return;
        }

        let mut tuning = self.current_horizontal_alignment_tuning();
        tuning.projection_target_offset_x_uv = self.projection_target_joystick_offset_x_uv;
        tuning.projection_target_offset_y_uv = self.projection_target_joystick_offset_y_uv;
        if !breath_controls_scale {
            tuning.projection_target_scale = self.projection_target_joystick_scale;
        }
        self.projection_target_offset_x_uv = tuning.projection_target_offset_x_uv;
        self.projection_target_offset_y_uv = tuning.projection_target_offset_y_uv;
        self.projection_target_scale = tuning.projection_target_scale;
        let panel_bound = self.apply_horizontal_alignment_tuning_to_panel(cx, tuning);
        if changed
            || reset
            || self.projection_target_joystick_last_log_frame == 0
            || frame.saturating_sub(self.projection_target_joystick_last_log_frame) >= 30
        {
            Self::emit_stereo_projection_marker(&format!(
                "phase=projection-target-tuning status=ok source=controller referenceSource=quest-composite-layer-apk changed={} reset={} projectionTargetJoystickControls=offset-scale projectionAreaScaleControlRole=diagnostic-canvas-scale-runtime-property projectionAreaScaleMin={:.4} projectionAreaScaleMax={:.4} projectionTargetScaleControlRole=reference-target-footprint-runtime-adjustment projectionTargetScaleMin={:.4} projectionTargetScaleMax={:.4} projectionTargetOffsetXUv={:.4} projectionTargetOffsetYUv={:.4} projectionTargetScale={:.4} projectionAreaScaleX={:.4} projectionAreaScaleY={:.4} leftStickX={:.4} leftStickY={:.4} rightStickY={:.4} panelBound={}",
                changed,
                reset,
                PROJECTION_AREA_MIN_SCALE,
                PROJECTION_AREA_MAX_SCALE,
                PROJECTION_TARGET_MIN_SCALE,
                PROJECTION_TARGET_MAX_SCALE,
                self.projection_target_joystick_offset_x_uv,
                self.projection_target_joystick_offset_y_uv,
                tuning.projection_target_scale,
                tuning.projection_area_scale_x,
                tuning.projection_area_scale_y,
                state.left_controller.stick.x,
                state.left_controller.stick.y,
                state.right_controller.stick.y,
                panel_bound,
            ));
            self.projection_target_joystick_last_log_frame = frame;
        }
    }

    fn handle_manifold_breath_feedback_subscription(&mut self) {
        let config = Self::manifold_breath_feedback_config();
        let config_marker = Self::manifold_breath_feedback_config_marker_line(&config);
        if self
            .manifold_breath_feedback_config_marker
            .as_ref()
            .is_none_or(|previous| previous != &config_marker)
        {
            emit_marker_line(&config_marker);
            self.manifold_breath_feedback_config_marker = Some(config_marker);
        }
        if !config.enabled {
            self.manifold_breath_feedback_subscriber = None;
            return;
        }
        if self
            .manifold_breath_feedback_subscriber
            .as_ref()
            .is_none_or(|subscriber| subscriber.config() != &config)
        {
            emit_marker_line(&format!(
                "RUSTY_MAKEPAD_BREATH_FEEDBACK_SUBSCRIBER schema=rusty.gui.makepad.breath_feedback_subscriber.v1 phase=subscribe status=ready stream={} receiver={} brokerHost={} brokerPort={} subscribeCommand=subscribe receiptCommand=breath_feedback.received receiptSchema=rusty.manifold.breath.feedback_receipt.v1",
                marker_token(&config.stream_id),
                marker_token(&config.receiver_id),
                marker_token(&config.broker_host),
                config.broker_port,
            ));
            self.manifold_breath_feedback_subscriber =
                Some(ManifoldBreathFeedbackSubscriber::new(config));
        }
    }

    fn handle_projection_target_breath_feedback(&mut self, cx: &mut Cx) {
        if !Self::projection_target_breath_controls_enabled() {
            self.projection_target_breath_scale_ready = false;
            self.projection_target_breath_last_sequence_id = 0;
            return;
        }
        let Some(sample) = self
            .manifold_breath_feedback_subscriber
            .as_ref()
            .and_then(ManifoldBreathFeedbackSubscriber::latest_sample)
        else {
            return;
        };
        let min_quality = hotload_f32(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_MIN_QUALITY,
            0.0,
            0.0,
            1.0,
        );
        if sample.quality01 < min_quality as f64 {
            return;
        }
        let min_scale = hotload_f32(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_MIN_SCALE,
            TARGET_PROJECTION_TARGET_SCALE,
            PROJECTION_TARGET_MIN_SCALE,
            PROJECTION_TARGET_MAX_SCALE,
        );
        let max_scale = hotload_f32(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_MAX_SCALE,
            PROJECTION_TARGET_MAX_SCALE,
            PROJECTION_TARGET_MIN_SCALE,
            PROJECTION_TARGET_MAX_SCALE,
        );
        let smoothing_alpha = hotload_f32(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_SMOOTHING_ALPHA,
            PROJECTION_TARGET_BREATH_DEFAULT_SMOOTHING_ALPHA,
            0.0,
            1.0,
        );
        let invert = hotload_bool(makepad_config::KEY_PROJECTION_TARGET_BREATH_INVERT, false);
        self.apply_projection_target_breath_sample(
            cx,
            sample,
            min_scale,
            max_scale,
            smoothing_alpha,
            invert,
        );
    }

    fn apply_projection_target_breath_sample(
        &mut self,
        cx: &mut Cx,
        sample: BreathFeedbackSample,
        min_scale: f32,
        max_scale: f32,
        smoothing_alpha: f32,
        invert: bool,
    ) {
        let was_ready = self.projection_target_breath_scale_ready;
        let previous_sequence_id = self.projection_target_breath_last_sequence_id;
        let is_new_sample = makepad_projection_target_breath_sample_is_new(
            was_ready,
            previous_sequence_id,
            sample.sequence_id,
        );
        let target_scale = makepad_projection_target_breath_scale(
            sample.volume01 as f32,
            min_scale,
            max_scale,
            invert,
        );
        let smoothing_alpha = makepad_projection_target_breath_smoothing_alpha(smoothing_alpha);
        let next_scale = if self.projection_target_breath_scale_ready {
            makepad_projection_target_breath_lerp(
                self.projection_target_scale,
                target_scale,
                smoothing_alpha,
            )
        } else {
            target_scale
        }
        .clamp(PROJECTION_TARGET_MIN_SCALE, PROJECTION_TARGET_MAX_SCALE);
        let changed = !was_ready || (next_scale - self.projection_target_scale).abs() > 0.0001;
        self.projection_target_breath_scale_ready = true;
        self.projection_target_breath_last_sequence_id = sample.sequence_id;
        self.projection_target_joystick_scale = next_scale;

        let mut tuning = self.current_horizontal_alignment_tuning();
        if Self::projection_target_joystick_controls_enabled()
            && self.projection_target_joystick_scale_ready
        {
            tuning.projection_target_offset_x_uv = self.projection_target_joystick_offset_x_uv;
            tuning.projection_target_offset_y_uv = self.projection_target_joystick_offset_y_uv;
        }
        tuning.projection_target_scale = next_scale;
        self.projection_target_offset_x_uv = tuning.projection_target_offset_x_uv;
        self.projection_target_offset_y_uv = tuning.projection_target_offset_y_uv;
        self.projection_target_scale = tuning.projection_target_scale;
        let panel_bound = self.apply_horizontal_alignment_tuning_to_panel(cx, tuning);

        if is_new_sample {
            Self::emit_stereo_projection_marker(&format!(
                "phase=projection-target-tuning status=ok source=manifold-breath-volume-selected stream={} sequenceId={} previousSequenceId={} newSample=true scaleChanged={} sourceId={} inputStreamId={} volume01={:.4} quality01={:.4} minScale={:.4} maxScale={:.4} smoothingAlpha={:.4} invert={} targetScale={:.4} projectionTargetScale={:.4} panelBound={}",
                marker_token(&sample.stream_id),
                sample.sequence_id,
                previous_sequence_id,
                changed,
                marker_token(&sample.source_id),
                marker_token(&sample.input_stream_id),
                sample.volume01,
                sample.quality01,
                min_scale,
                max_scale,
                smoothing_alpha,
                invert,
                target_scale,
                tuning.projection_target_scale,
                panel_bound,
            ));
            self.projection_target_breath_last_log_frame = self.cadence_xr_update_count;
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
    fn update_stimulus_runtime_xr_projection(&mut self, update: &XrUpdateEvent) {
        if !self.stimulus_stereo_field_state.enabled {
            return;
        }
        let views = Self::xr_display_views_from_update(update);
        if let Some(plan) = android_camera_probe::broker_full_frame_projection_plan_from_xr_views(
            "stimulus-left",
            "stimulus-right",
            1024,
            1024,
            views,
        ) {
            self.stimulus_surface_projection_rows =
                StimulusSurfaceProjectionRows::from_homographies(
                    plan.left_screen_to_surface_h,
                    plan.right_screen_to_surface_h,
                );
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

    fn horizontal_alignment_tuning() -> HorizontalAlignmentTuning {
        let legacy = Self::legacy_horizontal_alignment_tuning();
        if !makepad_projection_runtime_resolution_enabled() {
            return legacy;
        }

        let config = Self::runtime_config();
        let runtime = makepad_projection_runtime_resolution(&config, legacy);
        makepad_horizontal_alignment_tuning_from_resolution(legacy, &runtime.resolution)
    }

    fn legacy_horizontal_alignment_tuning() -> HorizontalAlignmentTuning {
        let strength = hotload_f32(
            KEY_MAKEPAD_HORIZONTAL_ALIGNMENT_STRENGTH,
            TARGET_HORIZONTAL_ALIGNMENT_STRENGTH,
            -4.0,
            4.0,
        );
        let global_offset = hotload_f32(KEY_MAKEPAD_HORIZONTAL_OFFSET_UV, 0.0, -0.5, 0.5);
        let left_offset = global_offset
            + hotload_f32(
                KEY_MAKEPAD_HORIZONTAL_OFFSET_LEFT_UV,
                TARGET_MANUAL_HORIZONTAL_OFFSET_LEFT_UV,
                -0.5,
                0.5,
            );
        let right_offset = global_offset
            + hotload_f32(
                KEY_MAKEPAD_HORIZONTAL_OFFSET_RIGHT_UV,
                TARGET_MANUAL_HORIZONTAL_OFFSET_RIGHT_UV,
                -0.5,
                0.5,
            );
        let vertical_offset = hotload_f32(
            KEY_MAKEPAD_VERTICAL_OFFSET_UV,
            TARGET_MANUAL_VERTICAL_OFFSET_UV,
            -0.5,
            0.5,
        );
        let content_uv_scale = hotload_f32(
            KEY_MAKEPAD_CONTENT_UV_SCALE,
            TARGET_FULL_VIEW_CONTENT_UV_SCALE,
            1.0,
            2.4,
        );
        let projection_border_opacity = makepad_projection_border_opacity();
        let projection_border_policy = MakepadProjectionBorderPolicy::current().shader_code();
        let processing_layer = MakepadProcessingLayer::current().shader_code();
        let projection_sample_mode = MakepadProjectionSampleMode::current().shader_code();
        let blur_radius_px = makepad_blur_radius_px();
        let peripheral_stretch = MakepadPeripheralStretchConfig::current();
        let projection_area_diagnostic = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_DIAGNOSTIC,
            TARGET_PROJECTION_AREA_DIAGNOSTIC,
            0.0,
            2.0,
        );
        let projection_area_offset_left_uv = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_OFFSET_LEFT_UV,
            TARGET_PROJECTION_AREA_OFFSET_LEFT_UV,
            -0.5,
            0.5,
        );
        let projection_area_offset_right_uv = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_OFFSET_RIGHT_UV,
            TARGET_PROJECTION_AREA_OFFSET_RIGHT_UV,
            -0.5,
            0.5,
        );
        let projection_area_offset_vertical_uv = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_OFFSET_VERTICAL_UV,
            TARGET_PROJECTION_AREA_OFFSET_VERTICAL_UV,
            -0.5,
            0.5,
        );
        let projection_area_scale_x = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_SCALE_X,
            TARGET_PROJECTION_AREA_SCALE_X,
            PROJECTION_AREA_MIN_SCALE,
            PROJECTION_AREA_MAX_SCALE,
        );
        let projection_area_scale_y = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_SCALE_Y,
            TARGET_PROJECTION_AREA_SCALE_Y,
            PROJECTION_AREA_MIN_SCALE,
            PROJECTION_AREA_MAX_SCALE,
        );
        let projection_target_offset_x_uv = makepad_projection_target_offset_x_uv();
        let projection_target_offset_y_uv = makepad_projection_target_offset_y_uv();
        let projection_target_scale = Self::projection_target_scale();
        let projection_area_radius_x_uv = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_RADIUS_X_UV,
            TARGET_PROJECTION_AREA_RADIUS_X_UV,
            0.05,
            0.5,
        );
        let projection_area_radius_y_uv = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_RADIUS_Y_UV,
            TARGET_PROJECTION_AREA_RADIUS_Y_UV,
            0.05,
            0.5,
        );
        let projection_area_corner_radius_uv = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_CORNER_RADIUS_UV,
            TARGET_PROJECTION_AREA_CORNER_RADIUS_UV,
            0.0,
            0.5,
        );
        let projection_area_keystone_x = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_KEYSTONE_X,
            TARGET_PROJECTION_AREA_KEYSTONE_X,
            -0.45,
            0.45,
        );
        let projection_area_bow_x = hotload_f32(
            KEY_MAKEPAD_PROJECTION_AREA_BOW_X,
            TARGET_PROJECTION_AREA_BOW_X,
            -0.25,
            0.25,
        );
        let projection_area_opacity = makepad_projection_area_opacity();
        let projection_alpha_mode = MakepadProjectionAlphaMode::current().shader_code();
        let projection_alpha_scale = makepad_projection_alpha_scale();
        let projection_alpha_bias = makepad_projection_alpha_bias();
        HorizontalAlignmentTuning {
            strength,
            left_offset_uv: left_offset.clamp(-0.5, 0.5),
            right_offset_uv: right_offset.clamp(-0.5, 0.5),
            vertical_offset_uv: vertical_offset,
            content_uv_scale,
            projection_border_opacity,
            projection_border_policy,
            processing_layer,
            projection_sample_mode,
            blur_radius_px,
            peripheral_stretch_core_scale: peripheral_stretch.core_scale,
            peripheral_stretch_edge_inset_uv: peripheral_stretch.edge_inset_uv,
            peripheral_stretch_max_inset_uv: peripheral_stretch.max_inset_uv,
            peripheral_stretch_curve: peripheral_stretch.curve,
            peripheral_stretch_inner_blend_uv: peripheral_stretch.inner_blend_uv,
            peripheral_stretch_blend_curve: peripheral_stretch.blend_curve,
            peripheral_stretch_blend_mode: peripheral_stretch.blend_mode.shader_code(),
            peripheral_stretch_debug: peripheral_stretch.debug.shader_code(),
            projection_area_diagnostic,
            projection_area_offset_left_uv,
            projection_area_offset_right_uv,
            projection_area_offset_vertical_uv,
            projection_area_scale_x,
            projection_area_scale_y,
            projection_target_offset_x_uv,
            projection_target_offset_y_uv,
            projection_target_scale,
            projection_area_radius_x_uv,
            projection_area_radius_y_uv,
            projection_area_corner_radius_uv,
            projection_area_keystone_x,
            projection_area_bow_x,
            projection_area_opacity,
            projection_alpha_mode,
            projection_alpha_scale,
            projection_alpha_bias,
        }
    }

    fn current_horizontal_alignment_tuning(&self) -> HorizontalAlignmentTuning {
        if self.horizontal_alignment_tuning_ready {
            HorizontalAlignmentTuning {
                strength: self.horizontal_alignment_strength,
                left_offset_uv: self.manual_horizontal_offset_left_uv,
                right_offset_uv: self.manual_horizontal_offset_right_uv,
                vertical_offset_uv: self.manual_vertical_offset_uv,
                content_uv_scale: self.content_uv_scale,
                projection_border_opacity: self.projection_border_opacity,
                projection_border_policy: self.projection_border_policy,
                processing_layer: self.processing_layer,
                projection_sample_mode: self.projection_sample_mode,
                blur_radius_px: self.blur_radius_px,
                peripheral_stretch_core_scale: self.peripheral_stretch_core_scale,
                peripheral_stretch_edge_inset_uv: self.peripheral_stretch_edge_inset_uv,
                peripheral_stretch_max_inset_uv: self.peripheral_stretch_max_inset_uv,
                peripheral_stretch_curve: self.peripheral_stretch_curve,
                peripheral_stretch_inner_blend_uv: self.peripheral_stretch_inner_blend_uv,
                peripheral_stretch_blend_curve: self.peripheral_stretch_blend_curve,
                peripheral_stretch_blend_mode: self.peripheral_stretch_blend_mode,
                peripheral_stretch_debug: self.peripheral_stretch_debug,
                projection_area_diagnostic: self.projection_area_diagnostic,
                projection_area_offset_left_uv: self.projection_area_offset_left_uv,
                projection_area_offset_right_uv: self.projection_area_offset_right_uv,
                projection_area_offset_vertical_uv: self.projection_area_offset_vertical_uv,
                projection_area_scale_x: self.projection_area_scale_x,
                projection_area_scale_y: self.projection_area_scale_y,
                projection_target_offset_x_uv: self.projection_target_offset_x_uv,
                projection_target_offset_y_uv: self.projection_target_offset_y_uv,
                projection_target_scale: self.projection_target_scale,
                projection_area_radius_x_uv: self.projection_area_radius_x_uv,
                projection_area_radius_y_uv: self.projection_area_radius_y_uv,
                projection_area_corner_radius_uv: self.projection_area_corner_radius_uv,
                projection_area_keystone_x: self.projection_area_keystone_x,
                projection_area_bow_x: self.projection_area_bow_x,
                projection_area_opacity: self.projection_area_opacity,
                projection_alpha_mode: self.projection_alpha_mode,
                projection_alpha_scale: self.projection_alpha_scale,
                projection_alpha_bias: self.projection_alpha_bias,
            }
        } else {
            HorizontalAlignmentTuning::default()
        }
    }

    fn refresh_horizontal_alignment_tuning(&mut self, cx: &mut Cx) {
        let mut tuning = Self::horizontal_alignment_tuning();
        if Self::projection_target_joystick_controls_enabled()
            && self.projection_target_joystick_scale_ready
        {
            tuning.projection_target_offset_x_uv = self.projection_target_joystick_offset_x_uv;
            tuning.projection_target_offset_y_uv = self.projection_target_joystick_offset_y_uv;
            if !Self::projection_target_breath_controls_enabled() {
                tuning.projection_target_scale = self.projection_target_joystick_scale;
            }
        }
        if Self::projection_target_breath_controls_enabled()
            && self.projection_target_breath_scale_ready
        {
            tuning.projection_target_scale = self.projection_target_scale;
        }
        let changed = !self.horizontal_alignment_tuning_ready
            || (self.horizontal_alignment_strength - tuning.strength).abs() > 0.0001
            || (self.manual_horizontal_offset_left_uv - tuning.left_offset_uv).abs() > 0.0001
            || (self.manual_horizontal_offset_right_uv - tuning.right_offset_uv).abs() > 0.0001
            || (self.manual_vertical_offset_uv - tuning.vertical_offset_uv).abs() > 0.0001
            || (self.content_uv_scale - tuning.content_uv_scale).abs() > 0.0001
            || (self.projection_border_opacity - tuning.projection_border_opacity).abs() > 0.0001
            || (self.projection_border_policy - tuning.projection_border_policy).abs() > 0.0001
            || (self.processing_layer - tuning.processing_layer).abs() > 0.0001
            || (self.projection_sample_mode - tuning.projection_sample_mode).abs() > 0.0001
            || (self.blur_radius_px - tuning.blur_radius_px).abs() > 0.0001
            || (self.peripheral_stretch_core_scale - tuning.peripheral_stretch_core_scale).abs()
                > 0.0001
            || (self.peripheral_stretch_edge_inset_uv - tuning.peripheral_stretch_edge_inset_uv)
                .abs()
                > 0.0001
            || (self.peripheral_stretch_max_inset_uv - tuning.peripheral_stretch_max_inset_uv)
                .abs()
                > 0.0001
            || (self.peripheral_stretch_curve - tuning.peripheral_stretch_curve).abs() > 0.0001
            || (self.peripheral_stretch_inner_blend_uv - tuning.peripheral_stretch_inner_blend_uv)
                .abs()
                > 0.0001
            || (self.peripheral_stretch_blend_curve - tuning.peripheral_stretch_blend_curve).abs()
                > 0.0001
            || (self.peripheral_stretch_blend_mode - tuning.peripheral_stretch_blend_mode).abs()
                > 0.0001
            || (self.peripheral_stretch_debug - tuning.peripheral_stretch_debug).abs() > 0.0001
            || (self.projection_area_diagnostic - tuning.projection_area_diagnostic).abs() > 0.0001
            || (self.projection_area_offset_left_uv - tuning.projection_area_offset_left_uv).abs()
                > 0.0001
            || (self.projection_area_offset_right_uv - tuning.projection_area_offset_right_uv)
                .abs()
                > 0.0001
            || (self.projection_area_offset_vertical_uv
                - tuning.projection_area_offset_vertical_uv)
                .abs()
                > 0.0001
            || (self.projection_area_scale_x - tuning.projection_area_scale_x).abs() > 0.0001
            || (self.projection_area_scale_y - tuning.projection_area_scale_y).abs() > 0.0001
            || (self.projection_target_offset_x_uv - tuning.projection_target_offset_x_uv).abs()
                > 0.0001
            || (self.projection_target_offset_y_uv - tuning.projection_target_offset_y_uv).abs()
                > 0.0001
            || (self.projection_target_scale - tuning.projection_target_scale).abs() > 0.0001
            || (self.projection_area_radius_x_uv - tuning.projection_area_radius_x_uv).abs()
                > 0.0001
            || (self.projection_area_radius_y_uv - tuning.projection_area_radius_y_uv).abs()
                > 0.0001
            || (self.projection_area_corner_radius_uv - tuning.projection_area_corner_radius_uv)
                .abs()
                > 0.0001
            || (self.projection_area_keystone_x - tuning.projection_area_keystone_x).abs() > 0.0001
            || (self.projection_area_bow_x - tuning.projection_area_bow_x).abs() > 0.0001
            || (self.projection_area_opacity - tuning.projection_area_opacity).abs() > 0.0001
            || (self.projection_alpha_mode - tuning.projection_alpha_mode).abs() > 0.0001
            || (self.projection_alpha_scale - tuning.projection_alpha_scale).abs() > 0.0001
            || (self.projection_alpha_bias - tuning.projection_alpha_bias).abs() > 0.0001;
        if !changed {
            return;
        }

        self.horizontal_alignment_tuning_ready = true;
        self.horizontal_alignment_strength = tuning.strength;
        self.manual_horizontal_offset_left_uv = tuning.left_offset_uv;
        self.manual_horizontal_offset_right_uv = tuning.right_offset_uv;
        self.manual_vertical_offset_uv = tuning.vertical_offset_uv;
        self.content_uv_scale = tuning.content_uv_scale;
        self.projection_border_opacity = tuning.projection_border_opacity;
        self.projection_border_policy = tuning.projection_border_policy;
        self.processing_layer = tuning.processing_layer;
        self.projection_sample_mode = tuning.projection_sample_mode;
        self.blur_radius_px = tuning.blur_radius_px;
        self.peripheral_stretch_core_scale = tuning.peripheral_stretch_core_scale;
        self.peripheral_stretch_edge_inset_uv = tuning.peripheral_stretch_edge_inset_uv;
        self.peripheral_stretch_max_inset_uv = tuning.peripheral_stretch_max_inset_uv;
        self.peripheral_stretch_curve = tuning.peripheral_stretch_curve;
        self.peripheral_stretch_inner_blend_uv = tuning.peripheral_stretch_inner_blend_uv;
        self.peripheral_stretch_blend_curve = tuning.peripheral_stretch_blend_curve;
        self.peripheral_stretch_blend_mode = tuning.peripheral_stretch_blend_mode;
        self.peripheral_stretch_debug = tuning.peripheral_stretch_debug;
        self.projection_area_diagnostic = tuning.projection_area_diagnostic;
        self.projection_area_offset_left_uv = tuning.projection_area_offset_left_uv;
        self.projection_area_offset_right_uv = tuning.projection_area_offset_right_uv;
        self.projection_area_offset_vertical_uv = tuning.projection_area_offset_vertical_uv;
        self.projection_area_scale_x = tuning.projection_area_scale_x;
        self.projection_area_scale_y = tuning.projection_area_scale_y;
        self.projection_target_offset_x_uv = tuning.projection_target_offset_x_uv;
        self.projection_target_offset_y_uv = tuning.projection_target_offset_y_uv;
        self.projection_target_scale = tuning.projection_target_scale;
        self.projection_area_radius_x_uv = tuning.projection_area_radius_x_uv;
        self.projection_area_radius_y_uv = tuning.projection_area_radius_y_uv;
        self.projection_area_corner_radius_uv = tuning.projection_area_corner_radius_uv;
        self.projection_area_keystone_x = tuning.projection_area_keystone_x;
        self.projection_area_bow_x = tuning.projection_area_bow_x;
        self.projection_area_opacity = tuning.projection_area_opacity;
        self.projection_alpha_mode = tuning.projection_alpha_mode;
        self.projection_alpha_scale = tuning.projection_alpha_scale;
        self.projection_alpha_bias = tuning.projection_alpha_bias;
        let panel_bound = self.apply_horizontal_alignment_tuning_to_panel(cx, tuning);
        Self::emit_stereo_projection_marker(&makepad_horizontal_alignment_hotload_marker_fields(
            tuning,
            panel_bound,
        ));
    }

    fn apply_horizontal_alignment_tuning_to_panel(
        &mut self,
        cx: &mut Cx,
        tuning: HorizontalAlignmentTuning,
    ) -> bool {
        let panel_ref = self.ui.widget(cx, ids!(camera_projection_panel));
        let Some(mut panel) = panel_ref.borrow_mut::<MakepadStereoCameraPanel>() else {
            return false;
        };
        panel.set_horizontal_alignment_tuning(cx, tuning);
        true
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

    fn handle_mesh_replay_runtime_cadence(&mut self, cx: &mut Cx, now_seconds: f64) {
        const SETTINGS_HOTLOAD_CHECK_PERIOD_FRAMES: u64 = 30;
        if self.cadence_frame_count == 1
            || self
                .cadence_frame_count
                .saturating_sub(self.mesh_replay_settings_check_frame)
                >= SETTINGS_HOTLOAD_CHECK_PERIOD_FRAMES
        {
            self.mesh_replay_settings_check_frame = self.cadence_frame_count;
            self.refresh_matter_surface_gpu_proof_epoch_from_selected_settings("hotload");
            if self.refresh_mesh_replay_runtime_from_selected_settings("hotload", false) {
                self.apply_camera_shell_render_scale(cx, "hotload");
            }
        }

        let mut marker_lines = Vec::new();
        let uniforms = if let Some(runtime) = self.mesh_replay_runtime.as_mut() {
            runtime.step(now_seconds);
            if runtime.should_emit_config_marker() {
                marker_lines.push(runtime.config_marker_line("cadence"));
            }
            if runtime.should_emit_frame_marker() {
                marker_lines.push(runtime.frame_marker_line("cadence"));
            }
            runtime.uniforms()
        } else {
            MeshReplayUniforms::disabled()
        };

        for line in marker_lines {
            emit_marker_line(&line);
        }
        let camera_streaming_enabled = self.current_camera_streaming_enabled();
        let matter_frame = self.update_matter_surface_runtime_for_evidence(
            cx,
            now_seconds,
            "cadence",
            camera_streaming_enabled,
        );
        if camera_streaming_enabled {
            self.apply_mesh_replay_uniforms_to_panel(
                cx,
                uniforms,
                self.camera_shell_feature_uniforms,
                matter_frame.uniforms,
                matter_frame.particle_texture,
            );
        }
        self.apply_matter_world_particles_to_cloud(cx, "cadence");
        self.apply_matter_world_adf_debug_to_cells(cx, "cadence");
        self.apply_stimulus_stereo_field_to_panel(cx, "cadence", now_seconds);
    }

    fn apply_stimulus_stereo_field_to_panel(
        &mut self,
        cx: &mut Cx,
        phase: &str,
        now_seconds: f64,
    ) -> bool {
        let field_ref = self.ui.widget(cx, ids!(stimulus_stereo_field));
        let Some(mut field) = field_ref.borrow_mut::<StimulusStereoFieldPanel>() else {
            if self.stimulus_stereo_field_state.enabled
                && self.stimulus_stereo_field_markers_emitted < STIMULUS_STEREO_FIELD_MARKER_LIMIT
            {
                emit_marker_line(&format!(
                    "RUSTY_HOSTESS_MAKEPAD_STIMULUS_DRAW schema=rusty.hostess.makepad.stimulus_draw.v1 phase={} status=error issue=stimulus_stereo_field_widget_missing panelBound=false profileId={} renderPath=makepad-xr-fragment-preview",
                    marker_token(phase),
                    marker_token(&self.stimulus_stereo_field_state.profile_id),
                ));
                self.stimulus_stereo_field_markers_emitted += 1;
            }
            return false;
        };
        let time_seconds = now_seconds.max(0.0).min(f32::MAX as f64) as f32;
        let changed = field.set_stimulus_state(
            cx,
            self.stimulus_stereo_field_state.clone(),
            time_seconds,
            self.stimulus_surface_projection_rows,
            self.stimulus_volume_image_preview_texture.clone(),
        );
        if self.stimulus_stereo_field_state.enabled
            && (changed
                || self.stimulus_stereo_field_markers_emitted < STIMULUS_STEREO_FIELD_MARKER_LIMIT)
        {
            emit_marker_line(&self.stimulus_stereo_field_state.marker_line(
                phase,
                time_seconds,
                true,
                self.stimulus_surface_projection_rows.ready,
            ));
            if let Some(marker_line) = self
                .stimulus_stereo_field_state
                .volume_adoption_marker_line(phase, true)
            {
                emit_marker_line(&marker_line);
            }
            self.stimulus_stereo_field_markers_emitted += 1;
        }
        drop(field);
        self.update_stimulus_volume_gpu_probe(cx, phase);
        self.update_stimulus_volume_raymarch_preview(cx, phase);
        self.update_stimulus_volume_image_preview(cx, phase, time_seconds);
        true
    }

    fn update_stimulus_volume_gpu_probe(&mut self, cx: &mut Cx, phase: &str) {
        if !self.stimulus_stereo_field_state.enabled
            || !self.stimulus_stereo_field_state.volume_present
        {
            self.stimulus_volume_gpu_probe_pending = None;
            return;
        }

        if let Some(marker_line) = self
            .stimulus_volume_gpu_probe_pending
            .as_ref()
            .and_then(|pending| stimulus_volume_gpu_probe_poll_marker_line(cx, pending, phase))
        {
            emit_marker_line(&marker_line);
            self.stimulus_volume_gpu_probe_markers_emitted += 1;
            self.stimulus_volume_gpu_probe_pending = None;
            return;
        }

        if self.stimulus_volume_gpu_probe_markers_emitted >= STIMULUS_VOLUME_GPU_PROBE_MARKER_LIMIT
            || self.stimulus_volume_gpu_probe_pending.is_some()
        {
            return;
        }

        let Some(input) = stimulus_volume_probe_input_from_state(&self.stimulus_stereo_field_state)
        else {
            return;
        };
        if let Some(pending) = stimulus_volume_gpu_probe_submit(cx, &input) {
            self.stimulus_volume_gpu_probe_pending = Some(pending);
        }
    }

    fn update_stimulus_volume_raymarch_preview(&mut self, cx: &mut Cx, phase: &str) {
        if !self.stimulus_stereo_field_state.enabled
            || !self.stimulus_stereo_field_state.volume_present
        {
            self.stimulus_volume_raymarch_preview_pending = None;
            return;
        }

        if let Some(marker_line) = self
            .stimulus_volume_raymarch_preview_pending
            .as_ref()
            .and_then(|pending| {
                stimulus_volume_raymarch_preview_poll_marker_line(cx, pending, phase)
            })
        {
            emit_marker_line(&marker_line);
            self.stimulus_volume_raymarch_preview_markers_emitted += 1;
            self.stimulus_volume_raymarch_preview_pending = None;
            return;
        }

        if self.stimulus_volume_gpu_probe_markers_emitted == 0
            || self.stimulus_volume_raymarch_preview_markers_emitted
                >= STIMULUS_VOLUME_RAYMARCH_PREVIEW_MARKER_LIMIT
            || self.stimulus_volume_raymarch_preview_pending.is_some()
        {
            return;
        }

        let Some(input) =
            stimulus_volume_raymarch_preview_input_from_state(&self.stimulus_stereo_field_state)
        else {
            return;
        };
        if let Some(pending) = stimulus_volume_raymarch_preview_submit(cx, &input) {
            self.stimulus_volume_raymarch_preview_pending = Some(pending);
        }
    }

    fn update_stimulus_volume_image_preview(
        &mut self,
        cx: &mut Cx,
        phase: &str,
        time_seconds: f32,
    ) {
        if !self.stimulus_stereo_field_state.enabled
            || !self.stimulus_stereo_field_state.volume_present
        {
            self.stimulus_volume_image_preview_pending = None;
            self.stimulus_volume_image_preview_texture = None;
            return;
        }

        if let Some(ready) = self
            .stimulus_volume_image_preview_pending
            .as_ref()
            .and_then(|pending| stimulus_volume_image_preview_poll_ready(cx, pending, phase))
        {
            emit_marker_line(&ready.marker_line);
            self.stimulus_volume_image_preview_markers_emitted += 1;
            self.stimulus_volume_image_preview_pending = None;
            self.adopt_stimulus_volume_image_preview_texture(cx, phase, time_seconds, ready);
            return;
        }

        if self.stimulus_volume_raymarch_preview_markers_emitted == 0
            || self.stimulus_volume_image_preview_markers_emitted
                >= STIMULUS_VOLUME_IMAGE_PREVIEW_MARKER_LIMIT
            || self.stimulus_volume_image_preview_pending.is_some()
        {
            return;
        }

        let Some(input) =
            stimulus_volume_image_preview_input_from_state(&self.stimulus_stereo_field_state)
        else {
            return;
        };
        if let Some(pending) = stimulus_volume_image_preview_submit(cx, &input) {
            self.stimulus_volume_image_preview_pending = Some(pending);
        }
    }

    fn adopt_stimulus_volume_image_preview_texture(
        &mut self,
        cx: &mut Cx,
        phase: &str,
        time_seconds: f32,
        ready: StimulusVolumeImagePreviewReady,
    ) {
        let binding = if ready.readback_matched() {
            let gpu_texture = Texture::new_with_format(
                cx,
                TextureFormat::PlatformRGBAf32 {
                    width: ready.readback.image_width,
                    height: ready.readback.image_height,
                },
            );
            if let Some(adoption) = cx.xr_gpu_f32_volume_image_preview_adopt_texture(
                ready.request_id,
                gpu_texture.texture_id(),
            ) {
                self.stimulus_volume_image_preview_texture = Some(gpu_texture);
                StimulusVolumeTextureBindingEvidence::gpu_adoption(adoption)
            } else {
                let texture = Texture::new_with_format(
                    cx,
                    TextureFormat::VecRGBAf32 {
                        width: ready.readback.image_width,
                        height: ready.readback.image_height,
                        data: Some(ready.texture_rgba.clone()),
                        updated: TextureUpdated::Full,
                    },
                );
                self.stimulus_volume_image_preview_texture = Some(texture);
                StimulusVolumeTextureBindingEvidence::cpu_upload(ready.texture_upload_bytes())
            }
        } else {
            self.stimulus_volume_image_preview_texture = None;
            StimulusVolumeTextureBindingEvidence::cpu_upload(0)
        };

        let panel_bound =
            self.bind_stimulus_stereo_field_panel(cx, time_seconds, "volume-texture-adopted");
        if self.stimulus_volume_texture_adoption_markers_emitted < 1 {
            emit_marker_line(&ready.texture_adoption_marker_line(
                phase,
                panel_bound,
                STIMULUS_VOLUME_TEXTURE_SLOT,
                &binding,
            ));
            self.stimulus_volume_texture_adoption_markers_emitted += 1;
        }
    }

    fn bind_stimulus_stereo_field_panel(
        &mut self,
        cx: &mut Cx,
        time_seconds: f32,
        _phase: &str,
    ) -> bool {
        let field_ref = self.ui.widget(cx, ids!(stimulus_stereo_field));
        let Some(mut field) = field_ref.borrow_mut::<StimulusStereoFieldPanel>() else {
            return false;
        };
        field.set_stimulus_state(
            cx,
            self.stimulus_stereo_field_state.clone(),
            time_seconds,
            self.stimulus_surface_projection_rows,
            self.stimulus_volume_image_preview_texture.clone(),
        );
        true
    }

    fn apply_mesh_replay_uniforms_to_panel(
        &mut self,
        cx: &mut Cx,
        uniforms: MeshReplayUniforms,
        feature_uniforms: MakepadCameraShellFeatureUniforms,
        matter_uniforms: MakepadMatterSurfaceUniforms,
        particle_texture_frame: MatterParticleTextureFrame,
    ) -> bool {
        let panel_ref = self.ui.widget(cx, ids!(camera_projection_panel));
        let Some(mut panel) = panel_ref.borrow_mut::<MakepadStereoCameraPanel>() else {
            return false;
        };
        panel.set_mesh_replay_uniforms(
            cx,
            uniforms,
            feature_uniforms,
            matter_uniforms,
            particle_texture_frame,
        );
        true
    }

    fn apply_camera_shell_render_scale(&self, cx: &mut Cx, phase: &str) {
        let (render_scale, source) =
            if let Some(render_scale) = self.current_camera_shell_effective_render_scale() {
                (render_scale, "effective-settings")
            } else {
                let config = Self::runtime_config();
                (
                    runtime_float(&config, KEY_XR_RENDER_SCALE) as f32,
                    "runtime-config",
                )
            };
        cx.xr_set_render_scale(render_scale);
        emit_marker_line(&format!(
            "RUSTY_QUEST_MAKEPAD_CAMERA_SHELL_RENDER_SCALE schema=rusty.quest.makepad.camera_shell_render_scale.v1 phase={} status=applied renderScale={} source={}",
            marker_token(phase),
            marker_f32_token(Some(render_scale)),
            marker_token(source),
        ));
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

    fn record_camera_texture_update(&mut self, side: StereoEye, position_ms: u128) -> u64 {
        match side {
            StereoEye::Left => {
                self.cadence_left_texture_update_count =
                    self.cadence_left_texture_update_count.saturating_add(1);
                self.cadence_left_last_position_ms = position_ms;
                self.cadence_left_texture_update_count
            }
            StereoEye::Right => {
                self.cadence_right_texture_update_count =
                    self.cadence_right_texture_update_count.saturating_add(1);
                self.cadence_right_last_position_ms = position_ms;
                self.cadence_right_texture_update_count
            }
        }
    }

    fn record_camera_texture_metadata(
        &mut self,
        side: StereoEye,
        yuv: VideoYuvMetadata,
        metadata: VideoTextureUpdateMetadata,
    ) {
        match side {
            StereoEye::Left => {
                self.paired_import_left_yuv_metadata = Some(yuv);
                self.paired_import_left_update_metadata = Some(metadata);
            }
            StereoEye::Right => {
                self.paired_import_right_yuv_metadata = Some(yuv);
                self.paired_import_right_update_metadata = Some(metadata);
            }
        }
    }

    fn record_pending_camera_frame(
        &mut self,
        side: StereoEye,
        yuv: VideoYuvMetadata,
        metadata: VideoTextureUpdateMetadata,
        position_ms: u128,
        texture_update_count: u64,
    ) {
        let texture_path = Self::makepad_camera_texture_path_from_update_metadata(
            Self::broker_h264_enabled(),
            Self::direct_camera_hardware_buffer_external_enabled(),
            yuv.enabled,
            &metadata,
        );
        let sample = CameraTextureFrameSample::new(
            side,
            yuv,
            metadata,
            position_ms,
            texture_update_count,
            texture_path,
        );
        match side {
            StereoEye::Left => self.pending_left_camera_frame = Some(sample),
            StereoEye::Right => self.pending_right_camera_frame = Some(sample),
        }
    }

    fn record_xr_pose_snapshot(&mut self, update: &XrUpdateEvent) {
        self.last_xr_pose_snapshot = Some(XrPoseSnapshot::from_update(
            update,
            self.cadence_xr_update_count,
        ));
    }

    fn try_adopt_pending_stereo_camera_frame(&mut self, reason: &str) -> bool {
        let (Some(left), Some(right)) = (
            self.pending_left_camera_frame.clone(),
            self.pending_right_camera_frame.clone(),
        ) else {
            return false;
        };
        let Some(pose) = self.last_xr_pose_snapshot else {
            return false;
        };

        if let Some(adopted) = self.adopted_stereo_camera_frame.as_ref() {
            let left_advanced = left.texture_update_count > adopted.left.texture_update_count;
            let right_advanced = right.texture_update_count > adopted.right.texture_update_count;
            if !left_advanced || !right_advanced {
                return false;
            }
        }

        self.next_adopted_stereo_frame_id = self.next_adopted_stereo_frame_id.saturating_add(1);
        let adopted = AdoptedStereoCameraFrame::new(
            self.next_adopted_stereo_frame_id,
            left,
            right,
            Some(pose),
        );
        self.paired_import_left_updated = true;
        self.paired_import_right_updated = true;
        self.paired_import_left_rotation_steps = adopted.left.rotation_steps;
        self.paired_import_right_rotation_steps = adopted.right.rotation_steps;
        self.camera_projection_paired_textures_bound = false;
        self.emit_stereo_frame_adoption_marker(reason, &adopted);
        self.adopted_stereo_camera_frame = Some(adopted);
        true
    }

    fn emit_stereo_frame_adoption_marker(&self, reason: &str, adopted: &AdoptedStereoCameraFrame) {
        let marker_index = FRAME_ADOPTION_MARKERS_EMITTED.fetch_add(1, Ordering::AcqRel);
        if marker_index >= FRAME_ADOPTION_MARKER_LIMIT
            && marker_index % FRAME_ADOPTION_MARKER_PERIOD != 0
        {
            return;
        }
        let pose_update_count = adopted
            .pose
            .map(|pose| pose.update_count.to_string())
            .unwrap_or_else(|| "missing".to_string());
        let predicted_display_time_ns = adopted
            .pose
            .map(|pose| pose.predicted_display_time_ns.to_string())
            .unwrap_or_else(|| "missing".to_string());
        let left_pose_valid = adopted
            .pose
            .map(|pose| pose.left_valid.to_string())
            .unwrap_or_else(|| "false".to_string());
        let right_pose_valid = adopted
            .pose
            .map(|pose| pose.right_valid.to_string())
            .unwrap_or_else(|| "false".to_string());
        let pose_source = if adopted.pose.is_some() {
            "makepad-xr-update-predicted-display-pose"
        } else {
            "missing-xr-update-pose"
        };
        emit_marker_line(&format!(
            "RUSTY_MAKEPAD_FRAME_ADOPTION schema=rusty.gui.makepad.stereo_frame_adoption.v1 phase=adopt status=ok reason={} adoptionId={} leftSide={} rightSide={} leftTextureUpdateCount={} rightTextureUpdateCount={} leftPositionMs={} rightPositionMs={} leftCameraFrameSeq={} rightCameraFrameSeq={} frameSequenceDelta={} leftCameraTimestampNs={} rightCameraTimestampNs={} timestampDeltaNs={} closeTimestampMatch={} pairingStatus={} texturePath={} poseSource={} poseUpdateCount={} predictedDisplayTimeNs={} leftPoseValid={} rightPoseValid={} leftPosePosition={} rightPosePosition={} leftPoseOrientation={} rightPoseOrientation={} adoptionPolicy=latest-complete-stereo-pair panelUpdatePolicy=adopted-pair-xr-update-only",
            marker_value(reason),
            adopted.adoption_id,
            adopted.left.side.label(),
            adopted.right.side.label(),
            adopted.left.texture_update_count,
            adopted.right.texture_update_count,
            adopted.left.position_ms,
            adopted.right.position_ms,
            optional_u64_token(adopted.left.metadata.camera_frame_sequence),
            optional_u64_token(adopted.right.metadata.camera_frame_sequence),
            optional_i64_token(adopted.pairing.sequence_delta),
            optional_u64_token(adopted.left.metadata.camera_timestamp_ns),
            optional_u64_token(adopted.right.metadata.camera_timestamp_ns),
            optional_u64_token(adopted.pairing.timestamp_delta_ns),
            adopted.pairing.close_timestamp_match,
            adopted.pairing.status,
            adopted.left.texture_path.stable_id(),
            pose_source,
            pose_update_count,
            predicted_display_time_ns,
            left_pose_valid,
            right_pose_valid,
            adopted
                .pose
                .map(|pose| vec3_marker_token(pose.left_position))
                .unwrap_or_else(|| "missing".to_string()),
            adopted
                .pose
                .map(|pose| vec3_marker_token(pose.right_position))
                .unwrap_or_else(|| "missing".to_string()),
            adopted
                .pose
                .map(|pose| vec4_marker_token(pose.left_orientation))
                .unwrap_or_else(|| "missing".to_string()),
            adopted
                .pose
                .map(|pose| vec4_marker_token(pose.right_orientation))
                .unwrap_or_else(|| "missing".to_string()),
        ));
    }

    fn makepad_camera_texture_path_from_update_metadata(
        broker_h264_enabled: bool,
        direct_hardware_buffer_requested: bool,
        yuv_enabled: bool,
        metadata: &VideoTextureUpdateMetadata,
    ) -> MakepadCameraTexturePath {
        match metadata.resource_path {
            VideoTextureResourcePath::CpuYuvPlanes
            | VideoTextureResourcePath::SoftwareYuvPlanes => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::BrokerH264CpuYuv
                } else {
                    MakepadCameraTexturePath::DirectCpuYuvPlane
                }
            }
            VideoTextureResourcePath::HardwareBufferExternal => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::BrokerH264HardwareBuffer
                } else {
                    MakepadCameraTexturePath::DirectHardwareBufferExternal
                }
            }
            VideoTextureResourcePath::HardwareBufferYuvPlanes => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::BrokerH264HardwareBuffer
                } else {
                    MakepadCameraTexturePath::DirectHardwareBufferYuvPlane
                }
            }
            VideoTextureResourcePath::SurfaceTextureExternal => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::BrokerH264SurfaceTexture
                } else {
                    MakepadCameraTexturePath::from_direct_video_update(
                        direct_hardware_buffer_requested,
                        yuv_enabled,
                    )
                }
            }
            VideoTextureResourcePath::Unspecified => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::from_video_update(true, yuv_enabled)
                } else {
                    MakepadCameraTexturePath::from_direct_video_update(
                        direct_hardware_buffer_requested,
                        yuv_enabled,
                    )
                }
            }
        }
    }

    fn direct_camera_texture_path(&self) -> MakepadCameraTexturePath {
        let yuv_enabled = self
            .paired_import_left_yuv_metadata
            .as_ref()
            .is_some_and(|metadata| metadata.enabled)
            || self
                .paired_import_right_yuv_metadata
                .as_ref()
                .is_some_and(|metadata| metadata.enabled);
        if let Some(metadata) = self
            .paired_import_left_update_metadata
            .as_ref()
            .or(self.paired_import_right_update_metadata.as_ref())
        {
            return Self::makepad_camera_texture_path_from_update_metadata(
                false,
                Self::direct_camera_hardware_buffer_external_enabled(),
                yuv_enabled,
                metadata,
            );
        }
        MakepadCameraTexturePath::from_direct_video_update(
            Self::direct_camera_hardware_buffer_external_enabled(),
            yuv_enabled,
        )
    }

    fn direct_camera_hardware_buffer_external_enabled() -> bool {
        hotload_bool(
            KEY_MAKEPAD_DIRECT_CAMERA_HARDWARE_BUFFER_EXTERNAL,
            DEFAULT_MAKEPAD_DIRECT_CAMERA_HARDWARE_BUFFER_EXTERNAL,
        )
    }

    fn direct_camera_requested_texture_path() -> MakepadCameraTexturePath {
        MakepadCameraTexturePath::from_direct_hardware_buffer_external_enabled(
            Self::direct_camera_hardware_buffer_external_enabled(),
        )
    }

    fn cadence_camera_texture_path(&self) -> MakepadCameraTexturePath {
        if Self::broker_h264_enabled() {
            if let Some(metadata) = self
                .paired_import_left_update_metadata
                .as_ref()
                .or(self.paired_import_right_update_metadata.as_ref())
            {
                return Self::makepad_camera_texture_path_from_update_metadata(
                    true,
                    false,
                    self.paired_import_left_yuv_metadata
                        .as_ref()
                        .is_some_and(|metadata| metadata.enabled)
                        || self
                            .paired_import_right_yuv_metadata
                            .as_ref()
                            .is_some_and(|metadata| metadata.enabled),
                    metadata,
                );
            }
            if self.paired_import_left_yuv_metadata.is_some()
                || self.paired_import_right_yuv_metadata.is_some()
                || self.paired_import_left_yuv_textures.is_some()
                || self.paired_import_right_yuv_textures.is_some()
            {
                MakepadCameraTexturePath::BrokerH264CpuYuv
            } else {
                Self::broker_h264_requested_texture_path()
            }
        } else {
            self.direct_camera_texture_path()
        }
    }

    fn use_compact_cadence_marker(&self) -> bool {
        !self.current_camera_streaming_enabled()
    }

    fn emit_cadence_sample(&mut self, cx: &mut Cx, now_seconds: f64, interval_seconds: f64) {
        let elapsed_seconds = (now_seconds - self.cadence_start_time).max(0.0);
        let frame_delta = self
            .cadence_frame_count
            .saturating_sub(self.cadence_frame_count_at_last_sample);
        let left_delta = self
            .cadence_left_texture_update_count
            .saturating_sub(self.cadence_left_texture_update_count_at_last_sample);
        let right_delta = self
            .cadence_right_texture_update_count
            .saturating_sub(self.cadence_right_texture_update_count_at_last_sample);
        let xr_update_delta = self
            .cadence_xr_update_count
            .saturating_sub(self.cadence_xr_update_count_at_last_sample);
        let draw_event_delta = self
            .cadence_draw_event_count
            .saturating_sub(self.cadence_draw_event_count_at_last_sample);
        let paired_delta = left_delta.min(right_delta);
        let app_frame_rate_hz = rate_hz(frame_delta, interval_seconds);
        let xr_update_rate_hz = rate_hz(xr_update_delta, interval_seconds);
        let draw_event_rate_hz = rate_hz(draw_event_delta, interval_seconds);
        let left_texture_rate_hz = rate_hz(left_delta, interval_seconds);
        let right_texture_rate_hz = rate_hz(right_delta, interval_seconds);
        let paired_texture_rate_hz = rate_hz(paired_delta, interval_seconds);
        let paired_buffers_ready = self.adopted_stereo_camera_frame.is_some();
        let projection_ready = self
            .paired_import_choice
            .as_ref()
            .map(|pair| pair.projection_homography_ready)
            .unwrap_or(false);
        let (projection_mapping_ready, aligned_projection) = if paired_buffers_ready {
            (projection_ready, projection_ready)
        } else {
            (false, false)
        };
        let xr_cpu = cx.xr_frame_cpu_breakdown();
        let now_ns = diagnostic_now_ns();
        let left_camera_frame_age_ms =
            camera_frame_age_ms(self.paired_import_left_update_metadata.as_ref(), now_ns);
        let right_camera_frame_age_ms =
            camera_frame_age_ms(self.paired_import_right_update_metadata.as_ref(), now_ns);
        let paired_camera_frame_age_ms =
            optional_max_f64(left_camera_frame_age_ms, right_camera_frame_age_ms);
        let left_camera_import_lag_ms =
            camera_import_lag_ms(self.paired_import_left_update_metadata.as_ref());
        let right_camera_import_lag_ms =
            camera_import_lag_ms(self.paired_import_right_update_metadata.as_ref());
        let paired_camera_stale =
            paired_camera_frame_age_ms.map(|age_ms| age_ms > CAMERA_FRAME_STALE_THRESHOLD_MS);

        let cadence_sample = MakepadCadenceSampleMarker {
            elapsed_seconds,
            interval_seconds,
            app_frame_count: self.cadence_frame_count,
            app_frame_delta: frame_delta,
            app_frame_rate_hz,
            xr_update_count: self.cadence_xr_update_count,
            xr_update_delta,
            xr_update_rate_hz,
            draw_event_count: self.cadence_draw_event_count,
            draw_event_delta,
            draw_event_rate_hz,
            left_texture_update_count: self.cadence_left_texture_update_count,
            right_texture_update_count: self.cadence_right_texture_update_count,
            paired_texture_update_count: self
                .cadence_left_texture_update_count
                .min(self.cadence_right_texture_update_count),
            left_texture_update_delta: left_delta,
            right_texture_update_delta: right_delta,
            paired_texture_update_delta: paired_delta,
            left_texture_update_rate_hz: left_texture_rate_hz,
            right_texture_update_rate_hz: right_texture_rate_hz,
            paired_texture_update_rate_hz: paired_texture_rate_hz,
            left_last_position_ms: self.cadence_left_last_position_ms,
            right_last_position_ms: self.cadence_right_last_position_ms,
            left_camera_frame_age_ms,
            right_camera_frame_age_ms,
            paired_camera_frame_age_ms,
            left_camera_import_lag_ms,
            right_camera_import_lag_ms,
            camera_stale_threshold_ms: CAMERA_FRAME_STALE_THRESHOLD_MS,
            paired_camera_stale,
            paired_left_right_camera_frames: paired_buffers_ready,
            projection_mapping_ready,
            aligned_projection,
            visible_camera_projection_ready: self.camera_projection_textures_bound,
            xr_display_refresh_rate_hz: cx.xr_display_refresh_rate_hz(),
            xr_effective_frame_rate_hz: cx.xr_effective_frame_rate_hz(),
            xr_frame_cpu_ms: cx.xr_frame_cpu_time_ms(),
            xr_should_render: xr_cpu.map(|breakdown| breakdown.should_render),
            xr_skipped_should_render_count: xr_cpu
                .map(|breakdown| breakdown.skipped_should_render_count),
            xr_pre_frame_events_ms: xr_cpu.map(|breakdown| breakdown.pre_frame_events_ms),
            xr_post_frame_media_events_ms: xr_cpu
                .map(|breakdown| breakdown.post_frame_media_events_ms),
            xr_wait_frame_ms: xr_cpu.map(|breakdown| breakdown.wait_frame_ms),
            xr_begin_frame_ms: xr_cpu.map(|breakdown| breakdown.begin_frame_ms),
            xr_locate_space_ms: xr_cpu.map(|breakdown| breakdown.locate_space_ms),
            xr_locate_views_ms: xr_cpu.map(|breakdown| breakdown.locate_views_ms),
            xr_acquire_swapchain_ms: xr_cpu.map(|breakdown| breakdown.acquire_swapchain_ms),
            xr_wait_swapchain_ms: xr_cpu.map(|breakdown| breakdown.wait_swapchain_ms),
            xr_acquire_depth_ms: xr_cpu.map(|breakdown| breakdown.acquire_depth_ms),
            xr_update_prepare_ms: xr_cpu.map(|breakdown| breakdown.update_prepare_ms),
            xr_update_dispatch_ms: xr_cpu.map(|breakdown| breakdown.update_dispatch_ms),
            xr_next_frame_ms: xr_cpu.map(|breakdown| breakdown.next_frame_ms),
            xr_draw_event_ms: xr_cpu.map(|breakdown| breakdown.draw_event_ms),
            xr_compile_shaders_ms: xr_cpu.map(|breakdown| breakdown.compile_shaders_ms),
            xr_repaint_ms: xr_cpu.map(|breakdown| breakdown.repaint_ms),
            xr_repaint_gpu_ms: xr_cpu.and_then(|breakdown| breakdown.repaint_gpu_ms),
            xr_repaint_wait_inflight_ms: xr_cpu.map(|breakdown| breakdown.repaint_wait_inflight_ms),
            xr_repaint_prepare_textures_ms: xr_cpu
                .map(|breakdown| breakdown.repaint_prepare_textures_ms),
            xr_repaint_record_draw_ms: xr_cpu.map(|breakdown| breakdown.repaint_record_draw_ms),
            xr_repaint_submit_ms: xr_cpu.map(|breakdown| breakdown.repaint_submit_ms),
            xr_repaint_texture_upload_count: xr_cpu
                .map(|breakdown| breakdown.repaint_texture_upload_count),
            xr_repaint_texture_upload_bytes: xr_cpu
                .map(|breakdown| breakdown.repaint_texture_upload_bytes),
            xr_repaint_packet_buffer_count: xr_cpu
                .map(|breakdown| breakdown.repaint_packet_buffer_count),
            xr_repaint_packet_buffer_bytes: xr_cpu
                .map(|breakdown| breakdown.repaint_packet_buffer_bytes),
            xr_repaint_geometry_upload_bytes: xr_cpu
                .map(|breakdown| breakdown.repaint_geometry_upload_bytes),
            xr_repaint_descriptor_set_count: xr_cpu
                .map(|breakdown| breakdown.repaint_descriptor_set_count),
            xr_repaint_draw_items: xr_cpu.map(|breakdown| breakdown.repaint_draw_items),
            xr_repaint_draw_calls: xr_cpu.map(|breakdown| breakdown.repaint_draw_calls),
            xr_repaint_packets: xr_cpu.map(|breakdown| breakdown.repaint_packets),
            xr_repaint_instances: xr_cpu.map(|breakdown| breakdown.repaint_instances),
            xr_repaint_indices: xr_cpu.map(|breakdown| breakdown.repaint_indices),
            xr_depth_readback_ms: xr_cpu.map(|breakdown| breakdown.depth_readback_ms),
            xr_end_frame_ms: xr_cpu.map(|breakdown| breakdown.end_frame_ms),
            xr_resize_projection_ms: xr_cpu.map(|breakdown| breakdown.resize_projection_ms),
            texture_path: self.cadence_camera_texture_path(),
        };
        let cadence_marker = if self.use_compact_cadence_marker() {
            makepad_cadence_compact_sample_marker_line(cadence_sample)
        } else {
            makepad_cadence_sample_marker_line(cadence_sample)
        };
        emit_marker_line(&cadence_marker);

        self.cadence_last_sample_time = now_seconds;
        self.cadence_frame_count_at_last_sample = self.cadence_frame_count;
        self.cadence_xr_update_count_at_last_sample = self.cadence_xr_update_count;
        self.cadence_draw_event_count_at_last_sample = self.cadence_draw_event_count;
        self.cadence_left_texture_update_count_at_last_sample =
            self.cadence_left_texture_update_count;
        self.cadence_right_texture_update_count_at_last_sample =
            self.cadence_right_texture_update_count;
    }

    fn arm_paired_import_timer(&mut self, cx: &mut Cx, delay_seconds: f64, reason: &str) {
        if self.paired_import_finished {
            return;
        }
        self.paired_import_timer = cx.start_timeout(delay_seconds);
        PAIRED_IMPORT_SIGNAL_READY.store(false, Ordering::Release);
        thread::spawn(move || {
            thread::sleep(Duration::from_secs_f64(delay_seconds.max(0.0)));
            PAIRED_IMPORT_SIGNAL_READY.store(true, Ordering::Release);
            SignalToUI::set_ui_signal();
        });
        Self::emit_hardware_buffer_import_marker(
            &makepad_hardware_buffer_import_timer_armed_marker_fields(reason, delay_seconds),
        );
    }

    fn handle_broker_h264_projection_metadata(&mut self, video_id: LiveId, metadata_json: &str) {
        emit_raw_video_event_marker("metadata", video_id);
        if !self.current_camera_streaming_enabled() || !Self::broker_h264_enabled() {
            return;
        }
        let texture_path = Self::broker_h264_requested_texture_path();
        let Some(side) = StereoEye::from_video_id(video_id) else {
            Self::emit_hardware_buffer_import_marker(
                &makepad_stream_header_metadata_ignored_marker_fields(video_id.0, texture_path),
            );
            return;
        };
        match BrokerH264ProjectionMetadata::parse(metadata_json) {
            Ok(metadata) => {
                match side {
                    StereoEye::Left => {
                        self.broker_h264_left_projection_metadata = Some(metadata.clone())
                    }
                    StereoEye::Right => {
                        self.broker_h264_right_projection_metadata = Some(metadata.clone())
                    }
                }
                if let Some(pair) = self.paired_import_choice.as_mut() {
                    match side {
                        StereoEye::Left => {
                            pair.left.camera_id = Some(metadata.camera_id.clone());
                            if metadata.delivered_width > 0 {
                                pair.left.width = metadata.delivered_width as usize;
                            }
                            if metadata.delivered_height > 0 {
                                pair.left.height = metadata.delivered_height as usize;
                            }
                        }
                        StereoEye::Right => {
                            pair.right.camera_id = Some(metadata.camera_id.clone());
                            if metadata.delivered_width > 0 {
                                pair.right.width = metadata.delivered_width as usize;
                            }
                            if metadata.delivered_height > 0 {
                                pair.right.height = metadata.delivered_height as usize;
                            }
                        }
                    }
                    pair.projection_metadata_ready = self
                        .broker_h264_left_projection_metadata
                        .as_ref()
                        .is_some_and(|metadata| metadata.projection_metadata_ready)
                        && self
                            .broker_h264_right_projection_metadata
                            .as_ref()
                            .is_some_and(|metadata| metadata.projection_metadata_ready);
                    pair.pose_source = match (
                        self.broker_h264_left_projection_metadata.as_ref(),
                        self.broker_h264_right_projection_metadata.as_ref(),
                    ) {
                        (Some(left), Some(right)) => broker_pair_pose_source(left, right),
                        _ => metadata.pose_source.clone(),
                    };
                    pair.source_binding_mode = "broker-h264-stream-header".to_string();
                    pair.coordinate_chain =
                        "broker-h264-stream-header-to-runtime-openxr-view".to_string();
                    pair.fallback_reason = if pair.projection_metadata_ready {
                        "waiting_for_runtime_xr_view_projection".to_string()
                    } else {
                        "broker_stream_metadata_not_projection_ready".to_string()
                    };
                }
                Self::emit_hardware_buffer_import_marker(&stream_header_metadata_marker_fields(
                    side.label(),
                    &metadata,
                    texture_path,
                ));
            }
            Err(error) => {
                Self::emit_hardware_buffer_import_marker(
                    &makepad_stream_header_metadata_error_marker_fields(
                        side.label(),
                        metadata_json.len(),
                        &error,
                        texture_path,
                    ),
                );
            }
        }
    }

    fn begin_camera_streaming_startup(&mut self, cx: &mut Cx) {
        if !self.current_camera_streaming_enabled() {
            if !self.camera_streaming_disabled_logged {
                self.camera_streaming_disabled_logged = true;
                emit_marker_line(makepad_camera2_acquisition_streaming_disabled_marker_line());
            }
            return;
        }
        if self.paired_import_started || self.paired_import_finished {
            return;
        }
        if !self.paired_import_timer.is_empty() {
            return;
        }
        if Self::broker_h264_enabled() {
            let source = Self::broker_h264_source();
            self.paired_import_choice = Some(MakepadCameraPair::from_broker_h264_source(&source));
            Self::emit_hardware_buffer_import_marker(
                &makepad_hardware_buffer_import_broker_h264_startup_marker_fields(
                    &source.broker_host,
                    source.broker_port,
                    source.stream_port,
                    Self::broker_h264_stream_port(StereoEye::Right),
                    &source.source_mode,
                    &source.decode_output_mode,
                    &source.synthetic_pattern,
                    source.preferred_width,
                    source.preferred_height,
                    source.live_stream,
                    Self::broker_h264_requested_texture_path(),
                ),
            );
        } else {
            cx.request_permission(Permission::Camera);
            cx.request_permission(Permission::HeadsetCamera);
        }
        self.arm_paired_import_timer(cx, PAIRED_IMPORT_DELAY_SECONDS, "startup");
    }

    fn handle_paired_import_event(&mut self, cx: &mut Cx, event: &Event) {
        if !self.current_camera_streaming_enabled() {
            self.paired_import_timer = Timer::empty();
            if !self.camera_streaming_disabled_logged {
                self.camera_streaming_disabled_logged = true;
                emit_marker_line(makepad_camera2_acquisition_streaming_disabled_marker_line());
            }
            return;
        }
        if self.camera_streaming_disabled_logged {
            self.camera_streaming_disabled_logged = false;
            self.begin_camera_streaming_startup(cx);
        }
        match event {
            Event::Startup => {
                self.begin_camera_streaming_startup(cx);
            }
            Event::VideoInputs(inputs) => {
                if Self::broker_h264_enabled() {
                    return;
                }
                self.paired_import_choice = Self::pick_makepad_camera_pair(inputs);
                if !self.paired_import_selection_logged {
                    self.paired_import_selection_logged = true;
                    self.emit_makepad_camera_selection_marker(inputs);
                }
                if self.paired_import_timer.is_empty()
                    && !self.paired_import_started
                    && !self.paired_import_finished
                {
                    self.arm_paired_import_timer(cx, PAIRED_IMPORT_DELAY_SECONDS, "video-inputs");
                }
            }
            Event::TextureHandleReady(ready) => {
                self.maybe_prepare_broker_h264_import(cx, ready);
            }
            Event::VideoYuvTexturesReady(ready) => {
                emit_raw_video_event_marker("yuv-textures-ready", ready.video_id);
                if let Some(side) = StereoEye::from_video_id(ready.video_id) {
                    if Self::broker_h264_enabled() {
                        if Self::broker_h264_requested_texture_path()
                            != MakepadCameraTexturePath::BrokerH264CpuYuv
                        {
                            return;
                        }
                        let textures = MakepadCameraYuvTextures::new(
                            ready.tex_y.clone(),
                            ready.tex_u.clone(),
                            ready.tex_v.clone(),
                        );
                        match side {
                            StereoEye::Left => {
                                self.paired_import_left_yuv_textures = Some(textures)
                            }
                            StereoEye::Right => {
                                self.paired_import_right_yuv_textures = Some(textures)
                            }
                        }
                        self.camera_projection_textures_bound = false;
                        self.camera_projection_paired_textures_bound = false;
                        Self::emit_hardware_buffer_import_marker(
                            &makepad_hardware_buffer_import_yuv_textures_ready_broker_marker_fields(
                                side.label(),
                            ),
                        );
                        return;
                    }
                    let textures = MakepadCameraYuvTextures::new(
                        ready.tex_y.clone(),
                        ready.tex_u.clone(),
                        ready.tex_v.clone(),
                    );
                    match side {
                        StereoEye::Left => self.paired_import_left_yuv_textures = Some(textures),
                        StereoEye::Right => self.paired_import_right_yuv_textures = Some(textures),
                    }
                    Self::emit_hardware_buffer_import_marker(
                        &makepad_hardware_buffer_import_yuv_textures_ready_single_stream_marker_fields(
                            side.label(),
                            Self::direct_camera_requested_texture_path(),
                        ),
                    );
                }
            }
            Event::VideoPlaybackMetadata(metadata) => {
                self.handle_broker_h264_projection_metadata(
                    metadata.video_id,
                    &metadata.metadata_json,
                );
                self.emit_paired_projection_progress("stream-header-metadata");
            }
            Event::VideoPlaybackPrepared(prepared) => {
                emit_raw_video_event_marker("prepared", prepared.video_id);
                if let Some(side) = StereoEye::from_video_id(prepared.video_id) {
                    match side {
                        StereoEye::Left => self.paired_import_left_prepared = true,
                        StereoEye::Right => self.paired_import_right_prepared = true,
                    }
                    Self::emit_hardware_buffer_import_marker(
                        &makepad_hardware_buffer_import_prepared_marker_fields(
                            side.label(),
                            prepared.video_width,
                            prepared.video_height,
                            if Self::broker_h264_enabled() {
                                Self::broker_h264_requested_texture_path()
                            } else {
                                Self::direct_camera_requested_texture_path()
                            },
                        ),
                    );
                    self.emit_paired_projection_progress("prepared");
                }
            }
            Event::VideoTextureUpdated(updated) => {
                emit_raw_video_event_marker("texture-updated", updated.video_id);
                if let Some(side) = StereoEye::from_video_id(updated.video_id) {
                    let texture_update_count =
                        self.record_camera_texture_update(side, updated.current_position_ms);
                    self.record_camera_texture_metadata(
                        side,
                        updated.yuv,
                        updated.metadata.clone(),
                    );
                    self.record_pending_camera_frame(
                        side,
                        updated.yuv,
                        updated.metadata.clone(),
                        updated.current_position_ms,
                        texture_update_count,
                    );
                    if !Self::broker_h264_enabled() {
                        self.emit_yuv_texture_content_probe(cx, side, updated.yuv);
                    }
                    let marker_index =
                        TEXTURE_UPDATE_MARKERS_EMITTED.fetch_add(1, Ordering::AcqRel);
                    if should_emit_texture_update_marker(marker_index) {
                        let texture_path = Self::makepad_camera_texture_path_from_update_metadata(
                            Self::broker_h264_enabled(),
                            Self::direct_camera_hardware_buffer_external_enabled(),
                            updated.yuv.enabled,
                            &updated.metadata,
                        );
                        Self::emit_hardware_buffer_import_marker(
                            &makepad_hardware_buffer_import_texture_updated_marker_fields(
                                side.label(),
                                updated.yuv.enabled,
                                updated.yuv.biplanar,
                                updated.yuv.rotation_steps,
                                texture_path,
                                &updated.metadata,
                                MakepadProjectionBorderPolicy::current().stable_id(),
                                MakepadProcessingLayer::current().stable_id(),
                            ),
                        );
                    }
                    if self.paired_import_finished {
                        return;
                    }
                    match side {
                        StereoEye::Left => {
                            self.paired_import_left_updated = true;
                            self.paired_import_left_rotation_steps = updated.yuv.rotation_steps;
                        }
                        StereoEye::Right => {
                            self.paired_import_right_updated = true;
                            self.paired_import_right_rotation_steps = updated.yuv.rotation_steps;
                        }
                    }
                    self.complete_paired_import_if_ready(cx);
                }
            }
            Event::VideoDecodingError(error) => {
                emit_raw_video_event_marker("decode-error", error.video_id);
                if let Some(side) = StereoEye::from_video_id(error.video_id) {
                    self.paired_import_finished = true;
                    Self::emit_hardware_buffer_import_marker(
                        &makepad_hardware_buffer_import_complete_error_marker_fields(
                            side.label(),
                            &error.error,
                        ),
                    );
                    Self::emit_stereo_projection_marker(
                        &makepad_projection_complete_error_marker_fields(side.label()),
                    );
                }
            }
            _ => {}
        }

        if !self.paired_import_timer.is_empty()
            && self.paired_import_timer.is_event(event).is_some()
        {
            self.paired_import_timer = Timer::empty();
            Self::emit_hardware_buffer_import_marker(
                &makepad_hardware_buffer_import_timer_fired_marker_fields(
                    "makepad-timer",
                    self.paired_import_choice.is_some(),
                    self.paired_import_started,
                    self.paired_import_finished,
                ),
            );
            self.try_start_paired_import(cx);
        }

        if !self.paired_import_timer.is_empty()
            && matches!(event, Event::Signal)
            && PAIRED_IMPORT_SIGNAL_READY.swap(false, Ordering::AcqRel)
        {
            self.paired_import_timer = Timer::empty();
            Self::emit_hardware_buffer_import_marker(
                &makepad_hardware_buffer_import_timer_fired_marker_fields(
                    "signal-fallback",
                    self.paired_import_choice.is_some(),
                    self.paired_import_started,
                    self.paired_import_finished,
                ),
            );
            self.try_start_paired_import(cx);
        }

        if !self.native_video_widget_retry_timer.is_empty()
            && self
                .native_video_widget_retry_timer
                .is_event(event)
                .is_some()
        {
            self.native_video_widget_retry_timer = Timer::empty();
            if let Some(pair) = self.native_video_widget_retry_pair.clone() {
                if self.start_native_video_widget_surface(cx, &pair) {
                    self.paired_import_finished = true;
                    self.native_video_widget_retry_pair = None;
                }
            }
        }
    }

    fn maybe_prepare_broker_h264_import(&mut self, cx: &mut Cx, ready: &TextureHandleReadyEvent) {
        if !self.current_camera_streaming_enabled() || !Self::broker_h264_enabled() {
            return;
        }

        let left_texture_id = self
            .paired_import_left_texture
            .as_ref()
            .map(Texture::texture_id);
        let right_texture_id = self
            .paired_import_right_texture
            .as_ref()
            .map(Texture::texture_id);
        let side = if Some(ready.texture_id) == left_texture_id {
            StereoEye::Left
        } else if Some(ready.texture_id) == right_texture_id {
            StereoEye::Right
        } else {
            return;
        };

        let already_requested = match side {
            StereoEye::Left => self.broker_h264_left_playback_requested,
            StereoEye::Right => self.broker_h264_right_playback_requested,
        };
        if already_requested {
            return;
        }

        let source = Self::broker_h264_source_for_eye(side);
        match side {
            StereoEye::Left => self.broker_h264_left_playback_requested = true,
            StereoEye::Right => self.broker_h264_right_playback_requested = true,
        }
        Self::emit_hardware_buffer_import_marker(
            &makepad_hardware_buffer_import_texture_handle_ready_marker_fields(
                side.label(),
                ready.handle,
                &source.broker_host,
                source.broker_port,
                source.stream_port,
                &source.source_mode,
                &source.synthetic_pattern,
                source.live_stream,
            ),
        );
        cx.prepare_video_playback(
            side.video_id(),
            VideoSource::ExternalH264(source),
            CameraPreviewMode::Texture,
            ready.handle,
            ready.texture_id,
            true,
            false,
        );
    }

    fn request_broker_h264_import(&mut self, cx: &mut Cx, side: StereoEye, texture_id: TextureId) {
        if !self.current_camera_streaming_enabled() || !Self::broker_h264_enabled() {
            return;
        }
        let already_requested = match side {
            StereoEye::Left => self.broker_h264_left_playback_requested,
            StereoEye::Right => self.broker_h264_right_playback_requested,
        };
        if already_requested {
            return;
        }

        let source = Self::broker_h264_source_for_eye(side);
        match side {
            StereoEye::Left => self.broker_h264_left_playback_requested = true,
            StereoEye::Right => self.broker_h264_right_playback_requested = true,
        }
        Self::emit_hardware_buffer_import_marker(
            &makepad_hardware_buffer_import_broker_h264_prepare_request_marker_fields(
                side.label(),
                &source.broker_host,
                source.broker_port,
                source.stream_port,
                &source.source_mode,
                &source.decode_output_mode,
                &source.synthetic_pattern,
                source.live_stream,
                Self::broker_h264_requested_texture_path(),
            ),
        );
        cx.prepare_video_playback(
            side.video_id(),
            VideoSource::ExternalH264(source),
            CameraPreviewMode::Texture,
            0,
            texture_id,
            true,
            false,
        );
    }

    fn try_start_paired_import(&mut self, cx: &mut Cx) {
        if !self.current_camera_streaming_enabled() {
            return;
        }
        if self.paired_import_started || self.paired_import_finished {
            return;
        }

        if Self::broker_h264_enabled() && self.paired_import_choice.is_none() {
            let source = Self::broker_h264_source();
            self.paired_import_choice = Some(MakepadCameraPair::from_broker_h264_source(&source));
        }

        let Some(pair) = self.paired_import_choice.clone() else {
            self.paired_import_wait_count = self.paired_import_wait_count.saturating_add(1);
            if self.paired_import_wait_count > PAIRED_IMPORT_MAX_WAITS {
                self.paired_import_finished = true;
                Self::emit_hardware_buffer_import_marker(
                    makepad_hardware_buffer_import_start_error_marker_fields(),
                );
                Self::emit_stereo_projection_marker(
                    "phase=start status=error pairedLeftRightGpuBuffers=false projectionMappingReady=false alignedProjection=false fallbackReason=no_makepad_camera_stereo_pair",
                );
            } else {
                Self::emit_hardware_buffer_import_marker(
                    &makepad_hardware_buffer_import_start_waiting_marker_fields(
                        self.paired_import_wait_count,
                    ),
                );
                self.arm_paired_import_timer(cx, PAIRED_IMPORT_RETRY_SECONDS, "stereo-pair-retry");
            }
            return;
        };

        let left_texture = Texture::new_with_format(cx, TextureFormat::VideoExternal);
        let right_texture = Texture::new_with_format(cx, TextureFormat::VideoExternal);
        let left_texture_id = left_texture.texture_id();
        let right_texture_id = right_texture.texture_id();
        self.paired_import_left_texture = Some(left_texture);
        self.paired_import_right_texture = Some(right_texture);
        self.paired_import_started = true;

        let broker_h264_enabled = Self::broker_h264_enabled();
        let left_stream_port = if broker_h264_enabled {
            Self::broker_h264_stream_port(StereoEye::Left).to_string()
        } else {
            "none".to_string()
        };
        let right_stream_port = if broker_h264_enabled {
            Self::broker_h264_stream_port(StereoEye::Right).to_string()
        } else {
            "none".to_string()
        };
        Self::emit_hardware_buffer_import_marker(
            &makepad_hardware_buffer_import_start_marker_fields(
                &pair,
                broker_h264_enabled,
                &frame_rate_token(pair.left.frame_rate),
                &frame_rate_token(pair.right.frame_rate),
                pixel_format_label(pair.left.pixel_format),
                &left_stream_port,
                &right_stream_port,
                PAIRED_IMPORT_DELAY_SECONDS,
                if broker_h264_enabled {
                    Self::broker_h264_requested_texture_path()
                } else {
                    Self::direct_camera_requested_texture_path()
                },
            ),
        );
        Self::emit_stereo_projection_marker(&makepad_projection_start_marker_fields(
            &pair,
            &runtime_text(&Self::runtime_config(), KEY_CAMERA_PROJECTION_MODE),
            runtime_float(&Self::runtime_config(), KEY_PROJECTION_SCALE),
            runtime_float(&Self::runtime_config(), KEY_XR_RENDER_SCALE),
        ));

        if NATIVE_VIDEO_WIDGET_SURFACE_DIAGNOSTIC {
            if self.start_native_video_widget_surface(cx, &pair) {
                self.paired_import_finished = true;
            }
            return;
        }

        if broker_h264_enabled {
            if let Some(texture) = self.paired_import_left_texture.as_ref() {
                self.request_broker_h264_import(cx, StereoEye::Left, texture.texture_id());
            }
            if let Some(texture) = self.paired_import_right_texture.as_ref() {
                self.request_broker_h264_import(cx, StereoEye::Right, texture.texture_id());
            }
            return;
        }

        let direct_camera_texture_path = Self::direct_camera_requested_texture_path();
        let left_import_texture_id = if direct_camera_texture_path.makepad_vulkan_import() {
            left_texture_id
        } else {
            TextureId::default()
        };
        let right_import_texture_id = if direct_camera_texture_path.makepad_vulkan_import() {
            right_texture_id
        } else {
            TextureId::default()
        };

        cx.prepare_headset_camera_playback(
            StereoEye::Left.video_id(),
            VideoSource::Camera(pair.left.input_id, pair.left.format_id),
            CameraPreviewMode::Texture,
            0,
            left_import_texture_id,
            true,
            false,
        );
        cx.prepare_headset_camera_playback(
            StereoEye::Right.video_id(),
            VideoSource::Camera(pair.right.input_id, pair.right.format_id),
            CameraPreviewMode::Texture,
            0,
            right_import_texture_id,
            true,
            false,
        );
    }

    fn start_native_video_widget_surface(&mut self, cx: &mut Cx, pair: &MakepadCameraPair) -> bool {
        if self.native_video_widget_started {
            return true;
        }

        let left_video = self.ui.video(cx, &[live_id!(left_camera_video)]);
        let right_video = self.ui.video(cx, &[live_id!(right_camera_video)]);
        let left_unprepared = left_video.is_unprepared();
        let right_unprepared = right_video.is_unprepared();
        if !left_unprepared || !right_unprepared {
            if self.native_video_widget_retry_count >= NATIVE_VIDEO_WIDGET_MAX_RESETS {
                Self::emit_stereo_projection_marker(
                    &makepad_native_video_widget_reset_error_marker_fields(
                        left_unprepared,
                        right_unprepared,
                        left_video.is_playing(),
                        right_video.is_playing(),
                        left_video.is_cleaning_up(),
                        right_video.is_cleaning_up(),
                        self.native_video_widget_retry_count,
                    ),
                );
                return true;
            }

            if !left_unprepared && !left_video.is_cleaning_up() {
                left_video.stop_and_cleanup_resources(cx);
            }
            if !right_unprepared && !right_video.is_cleaning_up() {
                right_video.stop_and_cleanup_resources(cx);
            }
            self.native_video_widget_retry_count =
                self.native_video_widget_retry_count.saturating_add(1);
            self.native_video_widget_retry_pair = Some(pair.clone());
            self.native_video_widget_retry_timer =
                cx.start_timeout(NATIVE_VIDEO_WIDGET_RETRY_SECONDS);
            Self::emit_stereo_projection_marker(
                &makepad_native_video_widget_reset_waiting_marker_fields(
                    left_unprepared,
                    right_unprepared,
                    left_video.is_playing(),
                    right_video.is_playing(),
                    left_video.is_cleaning_up(),
                    right_video.is_cleaning_up(),
                    self.native_video_widget_retry_count,
                    NATIVE_VIDEO_WIDGET_RETRY_SECONDS,
                ),
            );
            return false;
        }

        left_video.set_camera_preview_mode(cx, VideoCameraPreviewMode::Texture);
        right_video.set_camera_preview_mode(cx, VideoCameraPreviewMode::Texture);
        left_video.set_camera_permission(VideoCameraPermission::HeadsetCamera);
        right_video.set_camera_permission(VideoCameraPermission::HeadsetCamera);
        left_video.set_source_camera(cx, pair.left.input_id, pair.left.format_id);
        right_video.set_source_camera(cx, pair.right.input_id, pair.right.format_id);
        left_video.should_dispatch_texture_updates(true);
        right_video.should_dispatch_texture_updates(true);
        left_video.begin_playback(cx);
        right_video.begin_playback(cx);
        self.native_video_widget_started = true;

        Self::emit_stereo_projection_marker(&makepad_native_video_widget_surface_marker_fields(
            pair,
            self.native_video_widget_retry_count,
        ));
        true
    }

    fn emit_makepad_camera_selection_marker(&self, inputs: &VideoInputsEvent) {
        let source_count = inputs.descs.len();
        let format_count: usize = inputs.descs.iter().map(|desc| desc.formats.len()).sum();
        match &self.paired_import_choice {
            Some(pair) => {
                Self::emit_hardware_buffer_import_marker(
                    &makepad_hardware_buffer_import_enumerated_marker_fields(
                        pair,
                        source_count,
                        format_count,
                        &frame_rate_token(pair.left.frame_rate),
                        &frame_rate_token(pair.right.frame_rate),
                        pixel_format_label(pair.left.pixel_format),
                    ),
                );
                Self::emit_stereo_projection_marker(&makepad_projection_enumerated_marker_fields(
                    pair,
                    source_count,
                    format_count,
                ));
            }
            None => Self::emit_hardware_buffer_import_marker(
                &makepad_hardware_buffer_import_enumerated_error_marker_fields(
                    source_count,
                    format_count,
                ),
            ),
        }
    }

    fn pick_makepad_camera_pair(inputs: &VideoInputsEvent) -> Option<MakepadCameraPair> {
        if Self::broker_h264_enabled() {
            let source = Self::broker_h264_source();
            return Some(MakepadCameraPair::from_broker_h264_source(&source));
        }
        let choices = collect_makepad_camera_choices(inputs);
        let camera2_plan = Self::latest_camera2_stereo_plan();
        camera2_plan
            .as_ref()
            .and_then(|plan| MakepadCameraPair::from_camera2_plan(&choices, plan))
            .or_else(|| MakepadCameraPair::from_best_available_pair(&choices))
    }

    fn emit_paired_projection_progress(&self, phase: &str) {
        let Some(pair) = &self.paired_import_choice else {
            return;
        };
        Self::emit_stereo_projection_marker(&makepad_paired_projection_progress_marker_fields(
            pair,
            phase,
            self.paired_import_left_prepared,
            self.paired_import_right_prepared,
            self.paired_import_left_updated,
            self.paired_import_right_updated,
        ));
    }

    fn emit_yuv_texture_content_probe(&self, cx: &mut Cx, side: StereoEye, yuv: VideoYuvMetadata) {
        if TEXTURE_CONTENT_PROBE_MARKERS_EMITTED.fetch_add(1, Ordering::AcqRel)
            >= TEXTURE_CONTENT_PROBE_MARKER_LIMIT
        {
            return;
        }

        let textures = match side {
            StereoEye::Left => self.paired_import_left_yuv_textures.clone(),
            StereoEye::Right => self.paired_import_right_yuv_textures.clone(),
        };

        let Some(textures) = textures else {
            Self::emit_stereo_projection_marker(
                &makepad_texture_content_probe_missing_marker_fields(
                    side.label(),
                    yuv.enabled,
                    yuv.biplanar,
                    yuv.matrix,
                    yuv.rotation_steps,
                ),
            );
            return;
        };

        let y_stats = texture_plane_content_stats(cx, &textures.y);
        let u_stats = texture_plane_content_stats(cx, &textures.u);
        let v_stats = texture_plane_content_stats(cx, &textures.v);
        let cpu_content_present =
            y_stats.readable && y_stats.data_present && y_stats.sample_count > 0 && y_stats.max > 0;

        Self::emit_stereo_projection_marker(&makepad_texture_content_probe_ok_marker_fields(
            side.label(),
            yuv.enabled,
            yuv.biplanar,
            yuv.matrix,
            yuv.rotation_steps,
            cpu_content_present,
            &y_stats.marker_fields("y"),
            &u_stats.marker_fields("u"),
            &v_stats.marker_fields("v"),
        ));
    }

    fn bind_camera_projection_panel(&mut self, cx: &mut Cx) -> bool {
        if !self.current_camera_streaming_enabled() {
            self.camera_projection_textures_bound = false;
            self.camera_projection_paired_textures_bound = false;
            return false;
        }
        let broker_h264_enabled = Self::broker_h264_enabled();
        let projection_sample_mode = MakepadProjectionSampleMode::current();
        let camera_texture_binding_enabled = projection_sample_mode.binds_camera_textures();
        let projection_panel_draw_enabled = projection_sample_mode.draws_projection_panel();
        let adopted_frame = self.adopted_stereo_camera_frame.clone();
        let adopted_frame_id = adopted_frame
            .as_ref()
            .map(|frame| frame.adoption_id)
            .unwrap_or(0);
        let paired_streams_available = adopted_frame.is_some();
        if self.camera_projection_textures_bound
            && (!paired_streams_available || self.camera_projection_paired_textures_bound)
            && self.camera_projection_bound_adopted_frame_id == adopted_frame_id
        {
            return true;
        }
        let emit_binding_markers = !self.camera_projection_textures_bound
            || self.camera_projection_bound_adopted_frame_id != adopted_frame_id;

        let (Some(left_texture), Some(right_texture), Some(pair)) = (
            self.paired_import_left_texture.clone(),
            self.paired_import_right_texture.clone(),
            self.paired_import_choice.clone(),
        ) else {
            return false;
        };
        let left_updated_yuv = if adopted_frame
            .as_ref()
            .is_some_and(|frame| frame.left.yuv.enabled)
            || (adopted_frame.is_none() && self.paired_import_left_updated)
        {
            self.paired_import_left_yuv_textures.clone()
        } else {
            None
        };
        let right_updated_yuv = if adopted_frame
            .as_ref()
            .is_some_and(|frame| frame.right.yuv.enabled)
            || (adopted_frame.is_none() && self.paired_import_right_updated)
        {
            self.paired_import_right_yuv_textures.clone()
        } else {
            None
        };
        let proof_source_side = match (left_updated_yuv.is_some(), right_updated_yuv.is_some()) {
            (true, true) => "paired",
            (true, false) => "left",
            (false, true) => "right",
            (false, false) => "ready-only",
        };
        let (left_yuv_source, right_yuv_source) =
            match (left_updated_yuv.clone(), right_updated_yuv.clone()) {
                (Some(left), Some(right)) => (Some(left), Some(right)),
                (Some(left), None) => (Some(left.clone()), Some(left)),
                (None, Some(right)) => (Some(right.clone()), Some(right)),
                (None, None) => {
                    let left_ready = self
                        .paired_import_left_yuv_textures
                        .clone()
                        .or_else(|| self.paired_import_right_yuv_textures.clone());
                    let right_ready = self
                        .paired_import_right_yuv_textures
                        .clone()
                        .or_else(|| left_ready.clone());
                    (left_ready, right_ready)
                }
            };
        let single_stream_visual_proof = adopted_frame.is_none()
            && !(self.paired_import_left_updated && self.paired_import_right_updated);
        let broker_h264_cpu_yuv_decode = broker_h264_enabled
            && (left_yuv_source.is_some()
                || right_yuv_source.is_some()
                || self.paired_import_left_yuv_textures.is_some()
                || self.paired_import_right_yuv_textures.is_some());
        let texture_path = adopted_frame
            .as_ref()
            .map(|frame| frame.left.texture_path)
            .unwrap_or_else(|| {
                if broker_h264_enabled {
                    if broker_h264_cpu_yuv_decode {
                        MakepadCameraTexturePath::BrokerH264CpuYuv
                    } else {
                        Self::broker_h264_requested_texture_path()
                    }
                } else {
                    self.direct_camera_texture_path()
                }
            });
        let explicit_top_left_broker_stimulus = broker_h264_enabled
            && self
                .broker_h264_left_projection_metadata
                .as_ref()
                .is_some_and(
                    BrokerH264ProjectionMetadata::has_explicit_top_left_stimulus_orientation,
                )
            && self
                .broker_h264_right_projection_metadata
                .as_ref()
                .is_some_and(
                    BrokerH264ProjectionMetadata::has_explicit_top_left_stimulus_orientation,
                );
        let orientation_decision = if broker_h264_enabled {
            match (
                self.broker_h264_left_projection_metadata.as_ref(),
                self.broker_h264_right_projection_metadata.as_ref(),
            ) {
                (Some(left), Some(right)) => {
                    FrameOrientationDecision::from_broker_pair(left, right)
                }
                _ => FrameOrientationDecision::fallback("broker-h264-orientation-metadata-missing"),
            }
        } else {
            FrameOrientationDecision::direct_camera2()
        };
        let source_sample_y_flip = orientation_decision.source_sample_y_flip;
        let source_sampling_mode = if broker_h264_enabled {
            Self::broker_h264_source_sampling_mode()
        } else {
            makepad_runtime_camera_source_sampling_mode()
        };
        let full_frame_diagnostic = source_sampling_mode.uses_target_local_raster();
        let projection_content_mapping_mode = if source_sampling_mode.uses_target_local_raster() {
            1.0
        } else {
            0.0
        };
        let source_sample_transform = if source_sample_y_flip >= 0.5 {
            "stimulus-raster-y-flip"
        } else if orientation_decision.raster_orientation == FRAME_RASTER_TOP_LEFT_Y_DOWN {
            "identity-top-left-stimulus-raster"
        } else {
            "identity-y-to-match-raster-metadata"
        };
        let (left_yuv, right_yuv) = if !camera_texture_binding_enabled {
            (None, None)
        } else if texture_path.yuv_sampling_enabled() {
            if broker_h264_enabled {
                let left_yuv = left_yuv_source
                    .clone()
                    .or_else(|| right_yuv_source.clone())
                    .or_else(|| self.paired_import_left_yuv_textures.clone())
                    .or_else(|| self.paired_import_right_yuv_textures.clone());
                let right_yuv = right_yuv_source
                    .clone()
                    .or_else(|| left_yuv_source.clone())
                    .or_else(|| self.paired_import_right_yuv_textures.clone())
                    .or_else(|| left_yuv.clone());
                (left_yuv, right_yuv)
            } else {
                let (Some(left_yuv), Some(right_yuv)) = (left_yuv_source, right_yuv_source) else {
                    if !self.camera_projection_bind_error_logged {
                        Self::emit_stereo_projection_marker(
                            "phase=visible-panel-bound status=waiting visibleCameraProjectionReady=false fallbackReason=makepad_camera_yuv_plane_textures_missing",
                        );
                        self.camera_projection_bind_error_logged = true;
                    }
                    return false;
                };
                (Some(left_yuv), Some(right_yuv))
            }
        } else {
            (None, None)
        };

        let panel_ref = self.ui.widget(cx, ids!(camera_projection_panel));
        let Some(mut panel) = panel_ref.borrow_mut::<MakepadStereoCameraPanel>() else {
            if !self.camera_projection_bind_error_logged {
                Self::emit_stereo_projection_marker(
                    "phase=visible-panel-bound status=error visibleCameraProjectionReady=false fallbackReason=makepad_camera_projection_panel_missing",
                );
                self.camera_projection_bind_error_logged = true;
            }
            return false;
        };

        panel.apply_projection_panel_geometry(cx);
        let left_panel_texture = if camera_texture_binding_enabled {
            Some(left_texture)
        } else {
            None
        };
        let right_panel_texture = if camera_texture_binding_enabled {
            Some(right_texture)
        } else {
            None
        };
        panel.set_camera_textures(
            cx,
            left_panel_texture,
            right_panel_texture,
            left_yuv,
            right_yuv,
            texture_path,
            adopted_frame
                .as_ref()
                .map(|frame| frame.left.rotation_steps)
                .unwrap_or(self.paired_import_left_rotation_steps),
            adopted_frame
                .as_ref()
                .map(|frame| frame.right.rotation_steps)
                .unwrap_or(self.paired_import_right_rotation_steps),
            pair.left_surface_to_camera_h,
            pair.right_surface_to_camera_h,
            pair.left_screen_to_camera_h,
            pair.right_screen_to_camera_h,
            pair.left_screen_to_surface_h,
            pair.right_screen_to_surface_h,
            source_sample_y_flip,
            projection_content_mapping_mode,
            Self::horizontal_alignment_tuning(),
        );
        panel.set_target_footprint(cx, pair.target_footprint);
        panel.set_horizontal_alignment_tuning(cx, self.current_horizontal_alignment_tuning());
        self.camera_projection_textures_bound = true;
        self.camera_projection_paired_textures_bound = !single_stream_visual_proof;
        self.camera_projection_bound_adopted_frame_id = adopted_frame_id;
        if !emit_binding_markers {
            return true;
        }
        let content_geometry_fields = if broker_h264_enabled {
            makepad_content_geometry_marker_fields(MakepadContentGeometrySource::BrokerH264 {
                left: self.broker_h264_left_projection_metadata.as_ref(),
                right: self.broker_h264_right_projection_metadata.as_ref(),
            })
        } else {
            makepad_content_geometry_marker_fields(MakepadContentGeometrySource::DirectCamera2 {
                width: pair.left.width,
                height: pair.left.height,
                projection_geometry_profile: &pair.projection_geometry_profile,
            })
        };
        let source_color_contract = makepad_current_source_color_contract_fields();
        let source_sampling_fields = MakepadSourceSamplingHandoff::new(
            broker_h264_enabled,
            explicit_top_left_broker_stimulus,
            &orientation_decision,
            source_sampling_mode,
            projection_content_mapping_mode,
            full_frame_diagnostic,
            &pair.source_eye_mapping,
            source_sample_transform,
            &content_geometry_fields,
            &source_color_contract,
            texture_path,
        )
        .marker_fields();
        Self::emit_stereo_projection_marker(&source_sampling_fields);
        Self::emit_stereo_projection_marker(&makepad_draw_vars_bound_marker_fields(
            &pair,
            texture_path,
            broker_h264_enabled && !broker_h264_cpu_yuv_decode,
            single_stream_visual_proof,
            proof_source_side,
            camera_texture_binding_enabled,
            projection_panel_draw_enabled,
        ));
        if !self.synthetic_scene_hidden_for_camera {
            self.synthetic_scene_hidden_for_camera = true;
            Self::emit_stereo_projection_marker(
                "phase=synthetic-scene-hidden status=ok visibleCameraProjectionReady=true fallbackSceneVisible=false fallbackReason=makepad_synthetic_scene_removed_for_visual_gate",
            );
        }
        Self::emit_stereo_projection_marker(&makepad_visible_panel_bound_marker_fields(
            &pair,
            texture_path,
            self.paired_import_left_rotation_steps,
            self.paired_import_right_rotation_steps,
            single_stream_visual_proof,
            proof_source_side,
            camera_texture_binding_enabled,
            projection_panel_draw_enabled,
        ));
        true
    }

    fn complete_paired_import_if_ready(&mut self, cx: &mut Cx) {
        if self.paired_import_finished {
            return;
        }

        let broker_h264_enabled = Self::broker_h264_enabled();
        let paired_streams_ready = self.adopted_stereo_camera_frame.is_some();
        let updated_stream_visual_proof_side = match (
            self.paired_import_left_updated,
            self.paired_import_right_updated,
        ) {
            (true, true) => "paired",
            (true, false) => "left",
            (false, true) => "right",
            (false, false) => "none",
        };
        let single_stream_ready = if broker_h264_enabled {
            false
        } else {
            let one_stream_updated =
                self.paired_import_left_updated || self.paired_import_right_updated;
            let direct_yuv_ready = self.paired_import_left_yuv_textures.is_some()
                || self.paired_import_right_yuv_textures.is_some();
            one_stream_updated
                && (!self.direct_camera_texture_path().yuv_sampling_enabled() || direct_yuv_ready)
        };
        if !paired_streams_ready && !single_stream_ready {
            self.emit_paired_projection_progress("texture-updated");
            return;
        }

        let Some(pair) = self.paired_import_choice.clone() else {
            return;
        };
        if !paired_streams_ready && !broker_h264_enabled {
            let visible_projection_ready = self.bind_camera_projection_panel(cx);
            if !self.camera_projection_single_stream_logged {
                self.camera_projection_single_stream_logged = true;
                Self::emit_stereo_projection_marker(
                    &makepad_single_stream_proof_wait_marker_fields(
                        self.paired_import_left_updated,
                        self.paired_import_right_updated,
                        self.paired_import_left_yuv_textures.is_some(),
                        self.paired_import_right_yuv_textures.is_some(),
                        self.cadence_camera_texture_path(),
                        pair.projection_homography_ready,
                        visible_projection_ready,
                        updated_stream_visual_proof_side,
                    ),
                );
            }
            return;
        }
        self.paired_import_finished = true;
        let aligned_projection = pair.projection_homography_ready && paired_streams_ready;
        let visible_projection_ready = self.bind_camera_projection_panel(cx);
        let texture_path = self.cadence_camera_texture_path();
        Self::emit_stereo_projection_marker(&makepad_projection_complete_marker_fields(
            &pair,
            paired_streams_ready,
            broker_h264_enabled,
            texture_path,
            aligned_projection,
            visible_projection_ready,
            &runtime_text(&Self::runtime_config(), KEY_CAMERA_PROJECTION_MODE),
            self.paired_import_left_rotation_steps,
            self.paired_import_right_rotation_steps,
            runtime_float(&Self::runtime_config(), KEY_PROJECTION_SCALE),
            runtime_float(&Self::runtime_config(), KEY_XR_RENDER_SCALE),
        ));
        Self::emit_stereo_comparison_parity_marker(
            "paired-projection-ready",
            &pair,
            texture_path,
            aligned_projection,
            visible_projection_ready,
        );
    }

    fn emit_stereo_comparison_parity_marker(
        phase: &str,
        pair: &MakepadCameraPair,
        texture_path: MakepadCameraTexturePath,
        aligned_projection: bool,
        visible_projection_ready: bool,
    ) {
        let config = Self::runtime_config();
        Self::emit_projection_runtime_manifest_marker(
            phase,
            &config,
            Self::horizontal_alignment_tuning(),
        );
        emit_marker_line(&makepad_stereo_comparison_marker_line(
            pair,
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
                texture_path,
                aligned_projection,
                visible_projection_ready,
                makepad_fork_branch: &runtime_text(&config, KEY_MAKEPAD_BRANCH),
                makepad_fork_commit: &runtime_text(&config, KEY_MAKEPAD_REVISION),
            },
        ));
    }

    #[cfg(target_os = "android")]
    fn camera2_stereo_plan() -> Option<Camera2StereoPlan> {
        android_camera_probe::latest_stereo_projection_plan().map(Camera2StereoPlan::from)
    }

    #[cfg(not(target_os = "android"))]
    fn camera2_stereo_plan() -> Option<Camera2StereoPlan> {
        None
    }

    fn latest_camera2_stereo_plan() -> Option<Camera2StereoPlan> {
        let profile = Self::direct_camera_projection_geometry_profile();
        Self::camera2_stereo_plan().map(|mut plan| {
            plan.apply_projection_geometry_profile(&profile);
            plan
        })
    }

    #[cfg(target_os = "android")]
    fn start_camera_probe_once() {
        android_camera_probe::start_camera_probe_once();
    }

    #[cfg(not(target_os = "android"))]
    fn start_camera_probe_once() {}
}

#[derive(Clone, Debug)]
struct FrameOrientationDecision {
    source_sample_y_flip: f32,
    source_sample_y_flip_reason: String,
    orientation_kind: String,
    raster_orientation: String,
    upright_marker: String,
    metadata_source: String,
    orientation_default: bool,
    fallback_reason: String,
}

impl FrameOrientationDecision {
    fn direct_camera2() -> Self {
        Self {
            source_sample_y_flip: 0.0,
            source_sample_y_flip_reason:
                "direct-camera2-generated-stimulus-top-left-raster-matches-makepad-video-sampler-origin".to_string(),
            orientation_kind: "camera-frame".to_string(),
            raster_orientation: FRAME_RASTER_TOP_LEFT_Y_DOWN.to_string(),
            upright_marker: "camera-native-upright".to_string(),
            metadata_source: "generated-direct-camera2-stimulus-metadata".to_string(),
            orientation_default: false,
            fallback_reason: "none".to_string(),
        }
    }

    fn fallback(reason: &str) -> Self {
        Self {
            source_sample_y_flip: 0.0,
            source_sample_y_flip_reason:
                "standard-stimulus-default-top-left-raster-matches-makepad-video-sampler-origin"
                    .to_string(),
            orientation_kind: "standard-stimulus-default".to_string(),
            raster_orientation: FRAME_RASTER_TOP_LEFT_Y_DOWN.to_string(),
            upright_marker: "unspecified".to_string(),
            metadata_source: "standard-stimulus-orientation-default".to_string(),
            orientation_default: true,
            fallback_reason: reason.to_string(),
        }
    }

    fn from_broker_pair(
        left: &BrokerH264ProjectionMetadata,
        right: &BrokerH264ProjectionMetadata,
    ) -> Self {
        if !left.has_explicit_stimulus_orientation() || !right.has_explicit_stimulus_orientation() {
            return Self::fallback("broker-h264-explicit-stimulus-orientation-missing");
        }
        if left.stimulus_raster_orientation != right.stimulus_raster_orientation {
            return Self::fallback("broker-h264-left-right-stimulus-orientation-mismatch");
        }
        let source_sample_y_flip = match left.stimulus_raster_orientation.as_str() {
            FRAME_RASTER_TOP_LEFT_Y_DOWN => 0.0,
            FRAME_RASTER_BOTTOM_LEFT_Y_UP => 1.0,
            _ => return Self::fallback("broker-h264-unsupported-stimulus-orientation"),
        };
        let source_sample_y_flip_reason = match left.stimulus_raster_orientation.as_str() {
            FRAME_RASTER_TOP_LEFT_Y_DOWN => {
                "broker-stimulus-top-left-raster-matches-makepad-video-sampler-origin"
            }
            FRAME_RASTER_BOTTOM_LEFT_Y_UP => {
                "broker-stimulus-bottom-left-raster-to-makepad-video-sampler-origin"
            }
            _ => "broker-stimulus-raster-unsupported",
        };
        Self {
            source_sample_y_flip,
            source_sample_y_flip_reason: source_sample_y_flip_reason.to_string(),
            orientation_kind: if left.orientation_kind == right.orientation_kind {
                left.orientation_kind.clone()
            } else {
                format!("{}+{}", left.orientation_kind, right.orientation_kind)
            },
            raster_orientation: left.stimulus_raster_orientation.clone(),
            upright_marker: if left.stimulus_upright_marker == right.stimulus_upright_marker {
                left.stimulus_upright_marker.clone()
            } else {
                format!(
                    "{}+{}",
                    left.stimulus_upright_marker, right.stimulus_upright_marker
                )
            },
            metadata_source: if left.stimulus_orientation_metadata_source
                == right.stimulus_orientation_metadata_source
            {
                left.stimulus_orientation_metadata_source.clone()
            } else {
                format!(
                    "{}+{}",
                    left.stimulus_orientation_metadata_source,
                    right.stimulus_orientation_metadata_source
                )
            },
            orientation_default: false,
            fallback_reason: "none".to_string(),
        }
    }
}

fn broker_pair_pose_source(
    left: &BrokerH264ProjectionMetadata,
    right: &BrokerH264ProjectionMetadata,
) -> String {
    if left.pose_source == right.pose_source {
        left.pose_source.clone()
    } else {
        format!("{}+{}", left.pose_source, right.pose_source)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn breath_feedback_config_marker_exposes_resolved_subscriber_config() {
        let mut config = ManifoldBreathFeedbackConfig::default();
        config.enabled = true;
        config.broker_port = 18765;

        let marker = App::manifold_breath_feedback_config_marker_line(&config);

        assert!(marker.contains("RUSTY_MAKEPAD_BREATH_FEEDBACK_CONFIG"));
        assert!(marker.contains("status=enabled"));
        assert!(marker.contains("enabled=true"));
        assert!(marker.contains("enabledRaw=default"));
        assert!(marker.contains("stream=stream.breath.volume.selected"));
        assert!(marker.contains("receiver=app.makepad_camera_shell.breath_feedback"));
        assert!(marker.contains("brokerPort=18765"));
        assert!(marker.contains("flagsOwner=hostessctl.record_values"));
    }

    #[test]
    fn broker_camera_metadata_maps_legacy_physical_profile_to_camera_projection() {
        let metadata = BrokerH264ProjectionMetadata::parse(
            r#"{
                "source": "broker_app.camera2_h264_stream",
                "cameraId": "50",
                "deliveredWidth": 1280,
                "deliveredHeight": 1280,
                "projectionGeometryProfile": "physical-camera",
                "projectionMetadataReady": true,
                "poseSource": "platform",
                "poseCoordinateConvention": "android-camera2-lens-pose-reference-from-camera",
                "intrinsics": {
                    "fx": 1024.0,
                    "fy": 1025.0,
                    "cx": 640.0,
                    "cy": 641.0,
                    "skew": 0.5
                },
                "intrinsicsDomain": {
                    "kind": "activeArray",
                    "width": 4096,
                    "height": 3072
                },
                "extrinsics": {
                    "px": 0.01,
                    "py": 0.02,
                    "pz": 0.03,
                    "qx": 0.0,
                    "qy": 0.0,
                    "qz": 0.0,
                    "qw": 1.0
                }
            }"#,
        )
        .unwrap();

        assert!(metadata.has_camera_projection_metadata());
        assert!(metadata.requests_camera_projection_mapping());
        assert_eq!(
            metadata.projection_mapping_profile_id(),
            "camera-projection"
        );
        assert_eq!(metadata.camera_id, "50");
        assert_eq!(metadata.intrinsics.unwrap().fx, 1024.0);
        assert_eq!(metadata.intrinsics_domain.unwrap().width, 4096);
        assert_eq!(metadata.extrinsics.unwrap().rotation[3], 1.0);
    }

    #[test]
    fn broker_full_frame_camera_metadata_keeps_projection_metadata_authoritative() {
        let metadata = BrokerH264ProjectionMetadata::parse(
            r#"{
                "source": "broker_app.camera2_h264_stream",
                "cameraId": "50",
                "deliveredWidth": 1280,
                "deliveredHeight": 1280,
                "projectionGeometryProfile": "full-frame-diagnostic",
                "sourceSamplingMode": "screen-to-camera-homography",
                "contentMappingIntent": "map-camera-frame-to-full-frame-projection-area",
                "projectionMetadataReady": true,
                "poseSource": "platform",
                "poseCoordinateConvention": "android-camera2-lens-pose-reference-from-camera",
                "intrinsics": {
                    "fx": 1024.0,
                    "fy": 1024.0,
                    "cx": 640.0,
                    "cy": 640.0
                },
                "extrinsics": {
                    "px": 0.01,
                    "py": 0.02,
                    "pz": 0.03,
                    "qx": 0.0,
                    "qy": 0.0,
                    "qz": 0.0,
                    "qw": 1.0
                }
            }"#,
        )
        .unwrap();

        assert!(metadata.is_full_frame_diagnostic_projection());
        assert!(metadata.has_camera_projection_metadata());
        assert!(!metadata.requests_explicit_full_frame_content_mapping());
    }

    #[test]
    fn broker_explicit_full_frame_content_intent_is_distinct_from_profile_label() {
        let metadata = BrokerH264ProjectionMetadata::parse(
            r#"{
                "source": "broker_app.synthetic_h264_stream",
                "cameraId": "synthetic-left",
                "deliveredWidth": 1280,
                "deliveredHeight": 1280,
                "projectionGeometryProfile": "full-frame-diagnostic",
                "contentMappingIntent": "map-full-frame-stimulus-to-projection-surface",
                "projectionMetadataReady": true
            }"#,
        )
        .unwrap();

        assert!(metadata.is_full_frame_diagnostic_projection());
        assert!(metadata.requests_explicit_full_frame_content_mapping());
        assert!(!metadata.has_camera_projection_metadata());
    }

    #[test]
    fn broker_orientation_sampling_uses_stimulus_metadata_only() {
        let metadata = BrokerH264ProjectionMetadata::parse(
            r#"{
                "source": "broker_app.camera2_h264_stream",
                "cameraId": "50",
                "deliveredWidth": 1280,
                "deliveredHeight": 1280,
                "orientationKind": "camera-frame",
                "rasterOrientation": "top-left-origin-y-down",
                "orientationMetadataSource": "legacy-stream-field",
                "orientationDefault": false,
                "stimulusRasterOrientation": "bottom-left-origin-y-up",
                "stimulusUprightMarker": "camera-native-upright",
                "stimulusOrientationMetadataSource": "stream-stimulus-contract",
                "stimulusOrientationDefault": false
            }"#,
        )
        .unwrap();

        let decision = FrameOrientationDecision::from_broker_pair(&metadata, &metadata);

        assert_eq!(decision.source_sample_y_flip, 1.0);
        assert_eq!(decision.raster_orientation, FRAME_RASTER_BOTTOM_LEFT_Y_UP);
        assert_eq!(decision.metadata_source, "stream-stimulus-contract");
    }

    #[test]
    fn direct_camera_orientation_sampling_keeps_top_left_stimulus_unflipped() {
        let decision = FrameOrientationDecision::direct_camera2();

        assert_eq!(decision.source_sample_y_flip, 0.0);
        assert_eq!(decision.raster_orientation, FRAME_RASTER_TOP_LEFT_Y_DOWN);
        assert_eq!(
            decision.metadata_source,
            "generated-direct-camera2-stimulus-metadata"
        );
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
        crate::stimulus_stereo_field_live::script_mod(vm);
        self::script_mod(vm)
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
