//! Hostess-local Makepad GPU renderer for staged Optics stimulus profiles.
//!
//! Optics owns the profile schema and layer graph. This widget is the
//! Quest-visible presentation bridge: it renders a full-viewport per-eye
//! fragment volume path and keeps the small compute texture path as validation
//! evidence/fallback while the renderer-neutral backend is split into Optics and
//! Makepad adapters.

use crate::makepad_widgets::*;
use crate::projection_settings::{
    makepad_projection_depth_meters, makepad_projection_preview_fov_y_degrees,
    makepad_projection_preview_offset_y_meters, makepad_projection_raw_overscan,
};
use crate::runtime_settings::{TARGET_DISPLAY_ASPECT, TARGET_DISPLAY_EYE_OFFSET_METERS};
use makepad_xr::scene::XrNode;
use rusty_quest_makepad_camera_shell::{StimulusProfilePayload, STIMULUS_VOLUME_ADOPTION_MARKER};
use serde_json::Value;
use std::sync::atomic::{AtomicUsize, Ordering};

pub(crate) const STIMULUS_STEREO_FIELD_MARKER_PREFIX: &str = "RUSTY_HOSTESS_MAKEPAD_STIMULUS_DRAW";
pub(crate) const STIMULUS_STEREO_FIELD_MARKER_SCHEMA: &str =
    "rusty.hostess.makepad.stimulus_draw.v1";
pub(crate) const STIMULUS_VOLUME_ADOPTION_MARKER_SCHEMA: &str =
    "rusty.hostess.makepad.stimulus_volume_adoption.v1";
const STIMULUS_STEREO_FIELD_DRAW_MARKER_LIMIT: usize = 8;
static STIMULUS_STEREO_FIELD_DRAW_MARKERS_EMITTED: AtomicUsize = AtomicUsize::new(0);
pub(crate) const STIMULUS_VOLUME_TEXTURE_SLOT: usize = 0;
pub(crate) const STIMULUS_VOLUME_FRAGMENT_RENDER_PATH: &str =
    "makepad-xr-fragment-volume-raymarch-v2";
pub(crate) const STIMULUS_VOLUME_FRAGMENT_RAYMARCH_SAMPLES: u64 = 16;
pub(crate) const STIMULUS_VOLUME_NOISE_MODEL: &str = "value-fbm-3oct-v1";
pub(crate) const STIMULUS_VOLUME_OSCILLATOR_MODEL: &str = "radial-axial-cross-v1";

pub(crate) const STIMULUS_IDENTITY_SURFACE_HOMOGRAPHY: [[f32; 3]; 3] =
    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]];

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct StimulusSurfaceProjectionRows {
    pub(crate) left_screen_to_surface_h: [[f32; 3]; 3],
    pub(crate) right_screen_to_surface_h: [[f32; 3]; 3],
    pub(crate) ready: bool,
}

impl StimulusSurfaceProjectionRows {
    #[cfg_attr(not(target_os = "android"), allow(dead_code))]
    pub(crate) fn from_homographies(
        left_screen_to_surface_h: [[f32; 3]; 3],
        right_screen_to_surface_h: [[f32; 3]; 3],
    ) -> Self {
        Self {
            left_screen_to_surface_h,
            right_screen_to_surface_h,
            ready: true,
        }
    }
}

impl Default for StimulusSurfaceProjectionRows {
    fn default() -> Self {
        Self {
            left_screen_to_surface_h: STIMULUS_IDENTITY_SURFACE_HOMOGRAPHY,
            right_screen_to_surface_h: STIMULUS_IDENTITY_SURFACE_HOMOGRAPHY,
            ready: false,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct StimulusStereoFieldState {
    pub(crate) enabled: bool,
    pub(crate) profile_id: String,
    pub(crate) profile_schema: String,
    pub(crate) profile_sha256: String,
    pub(crate) tuning_sha256: String,
    pub(crate) presentation_mode: String,
    pub(crate) stereo_binding: String,
    pub(crate) temporal_frequency_hz: f32,
    pub(crate) spatial_frequency: f32,
    pub(crate) rotation_radians: f32,
    pub(crate) phase_offset: f32,
    pub(crate) wave_modulation: f32,
    pub(crate) radial_decay: f32,
    pub(crate) geometry_mix: f32,
    pub(crate) edge_fade: f32,
    pub(crate) source_a: [f32; 2],
    pub(crate) source_b: [f32; 2],
    pub(crate) source_b_weight: f32,
    pub(crate) color_low: [f32; 4],
    pub(crate) color_high: [f32; 4],
    pub(crate) volume_present: bool,
    pub(crate) volume_schema: String,
    pub(crate) volume_id: String,
    pub(crate) volume_field_kind: String,
    pub(crate) volume_storage_hint: String,
    pub(crate) volume_grid_dimensions: [u64; 3],
    pub(crate) volume_step_count: u64,
    pub(crate) kernel_abi_id: String,
    pub(crate) compute_pass_count: usize,
    pub(crate) volume_readback_probe_samples: u64,
    pub(crate) stereo_field_output_layers: u64,
}

impl Default for StimulusStereoFieldState {
    fn default() -> Self {
        Self {
            enabled: false,
            profile_id: "none".to_string(),
            profile_schema: "none".to_string(),
            profile_sha256: "none".to_string(),
            tuning_sha256: "none".to_string(),
            presentation_mode: "none".to_string(),
            stereo_binding: "none".to_string(),
            temporal_frequency_hz: 0.0,
            spatial_frequency: 0.0,
            rotation_radians: 0.0,
            phase_offset: 0.0,
            wave_modulation: 0.0,
            radial_decay: 0.0,
            geometry_mix: 0.0,
            edge_fade: 0.0,
            source_a: [-0.24, 0.0],
            source_b: [0.24, 0.0],
            source_b_weight: 1.0,
            color_low: [0.0, 0.0, 0.0, 1.0],
            color_high: [1.0, 1.0, 1.0, 1.0],
            volume_present: false,
            volume_schema: "none".to_string(),
            volume_id: "none".to_string(),
            volume_field_kind: "none".to_string(),
            volume_storage_hint: "none".to_string(),
            volume_grid_dimensions: [0, 0, 0],
            volume_step_count: 0,
            kernel_abi_id: "none".to_string(),
            compute_pass_count: 0,
            volume_readback_probe_samples: 0,
            stereo_field_output_layers: 0,
        }
    }
}

impl StimulusStereoFieldState {
    pub(crate) fn from_profile_payload(payload: &StimulusProfilePayload) -> Result<Self, String> {
        let value: Value = serde_json::from_str(&payload.profile_json)
            .map_err(|error| format!("stimulus profile parse failed: {error}"))?;
        let profile_id = json_string(&value, &["profile_id"]).unwrap_or(&payload.profile_id);
        let profile_schema = json_string(&value, &["schema_id"]).unwrap_or(&payload.profile_schema);
        let presentation = value.get("presentation").unwrap_or(&Value::Null);
        let presentation_mode = json_string(presentation, &["mode"])
            .unwrap_or(payload.config.presentation_mode.as_str());
        let stereo_binding =
            json_string(presentation, &["stereo_binding"]).unwrap_or("SharedFieldBothEyes");
        let temporal = value.get("temporal").unwrap_or(&Value::Null);
        let safety = value.get("safety").unwrap_or(&Value::Null);
        let requested_hz = json_f32(temporal, &["target_cycle_hz"]).unwrap_or(1.0);
        let max_hz = json_f32(safety, &["max_cycle_hz"])
            .unwrap_or(12.0)
            .max(0.01);
        let temporal_frequency_hz = requested_hz.clamp(0.01, max_hz);
        let global_phase = json_f32(temporal, &["phase_offset"]).unwrap_or(0.0);

        let layer_graph = value.get("layer_graph").unwrap_or(&Value::Null);
        let post = layer_graph.get("post").unwrap_or(&Value::Null);
        let geometry_mix = json_f32(post, &["geometry_mix"])
            .unwrap_or(1.0)
            .clamp(0.0, 1.0);
        let edge_fade = json_f32(post, &["edge_fade"])
            .unwrap_or(0.0)
            .clamp(0.0, 1.0);
        let layer = selected_layer(layer_graph).unwrap_or(Value::Null);
        let interference = layer.get("interference").unwrap_or(&Value::Null);
        let source_a = json_vec2(interference, "source_a").unwrap_or([-0.24, 0.0]);
        let source_b = json_vec2(interference, "source_b").unwrap_or([0.24, 0.0]);
        let source_b_weight = json_f32(interference, &["source_b_weight"])
            .unwrap_or(1.0)
            .clamp(0.0, 2.0);
        let wave_modulation = json_f32(interference, &["wave_modulation"])
            .unwrap_or(0.0)
            .clamp(0.0, 2.0);
        let radial_decay = json_f32(interference, &["radial_decay"])
            .unwrap_or(0.0)
            .clamp(0.0, 4.0);
        let layer_temporal = layer.get("temporal").unwrap_or(&Value::Null);
        let layer_speed = json_f32(layer_temporal, &["speed_hz"]).unwrap_or(0.0);
        let layer_phase = json_f32(&layer, &["phase_offset"]).unwrap_or(0.0);
        let colors = layer.get("colors").and_then(Value::as_array);
        let color_low = colors
            .and_then(|colors| colors.first())
            .and_then(|stop| stop.get("color"))
            .and_then(json_color_rgba)
            .unwrap_or([0.0, 0.0, 0.0, 1.0]);
        let color_high = colors
            .and_then(|colors| colors.get(1))
            .and_then(|stop| stop.get("color"))
            .and_then(json_color_rgba)
            .unwrap_or([1.0, 1.0, 1.0, 1.0]);
        let volume_summary = &payload.volume_summary;

        Ok(Self {
            enabled: payload.config.enabled,
            profile_id: profile_id.to_string(),
            profile_schema: profile_schema.to_string(),
            profile_sha256: payload.profile_sha256.clone(),
            tuning_sha256: payload.config.tuning_sha256.clone(),
            presentation_mode: presentation_mode.to_string(),
            stereo_binding: stereo_binding.to_string(),
            temporal_frequency_hz,
            spatial_frequency: json_f32(&layer, &["spatial_frequency"])
                .unwrap_or(8.0)
                .clamp(0.1, 80.0),
            rotation_radians: json_f32(&layer, &["rotation_radians"]).unwrap_or(0.0),
            phase_offset: global_phase + layer_phase + layer_speed,
            wave_modulation,
            radial_decay,
            geometry_mix,
            edge_fade,
            source_a,
            source_b,
            source_b_weight,
            color_low,
            color_high,
            volume_present: volume_summary.volume_present,
            volume_schema: volume_summary
                .volume_schema
                .clone()
                .unwrap_or_else(|| "none".to_string()),
            volume_id: volume_summary
                .volume_id
                .clone()
                .unwrap_or_else(|| "none".to_string()),
            volume_field_kind: volume_summary
                .field_kind
                .clone()
                .unwrap_or_else(|| "none".to_string()),
            volume_storage_hint: volume_summary
                .storage_hint
                .clone()
                .unwrap_or_else(|| "none".to_string()),
            volume_grid_dimensions: volume_summary.grid_dimensions.unwrap_or([0, 0, 0]),
            volume_step_count: volume_summary.step_count.unwrap_or(0),
            kernel_abi_id: volume_summary
                .kernel_abi_id
                .clone()
                .unwrap_or_else(|| "none".to_string()),
            compute_pass_count: volume_summary.compute_pass_count,
            volume_readback_probe_samples: volume_summary
                .volume_readback_probe_samples
                .unwrap_or(0),
            stereo_field_output_layers: volume_summary.stereo_field_output_layers.unwrap_or(0),
        })
    }

    pub(crate) fn disabled() -> Self {
        Self::default()
    }

    pub(crate) fn volume_fragment_renderer_ready(&self) -> bool {
        self.enabled && self.volume_present
    }

    pub(crate) fn volume_render_path(&self) -> &'static str {
        if self.volume_fragment_renderer_ready() {
            STIMULUS_VOLUME_FRAGMENT_RENDER_PATH
        } else {
            "makepad-xr-fragment-preview"
        }
    }

    pub(crate) fn volume_shader_raymarch_steps(&self) -> f32 {
        if !self.volume_fragment_renderer_ready() {
            return 0.0;
        }
        self.volume_step_count
            .max(1)
            .min(STIMULUS_VOLUME_FRAGMENT_RAYMARCH_SAMPLES) as f32
    }

    pub(crate) fn volume_grid_frequency(&self) -> f32 {
        let max_axis = self
            .volume_grid_dimensions
            .iter()
            .copied()
            .max()
            .unwrap_or(1)
            .max(1) as f32;
        (max_axis / 8.0).clamp(1.0, 64.0)
    }

    pub(crate) fn volume_eccentricity(&self) -> f32 {
        let x = self.volume_grid_dimensions[0].max(1) as f32;
        let y = self.volume_grid_dimensions[1].max(1) as f32;
        (x / y).clamp(0.35, 2.75)
    }

    pub(crate) fn volume_noise_model(&self) -> &'static str {
        if self.volume_fragment_renderer_ready() {
            STIMULUS_VOLUME_NOISE_MODEL
        } else {
            "none"
        }
    }

    pub(crate) fn volume_oscillator_model(&self) -> &'static str {
        if self.volume_fragment_renderer_ready() {
            STIMULUS_VOLUME_OSCILLATOR_MODEL
        } else {
            "none"
        }
    }

    pub(crate) fn volume_noise_scale(&self) -> f32 {
        if !self.volume_fragment_renderer_ready() {
            return 0.0;
        }
        (self.volume_grid_frequency() * 0.75).clamp(1.0, 48.0)
    }

    pub(crate) fn volume_noise_strength(&self) -> f32 {
        if !self.volume_fragment_renderer_ready() {
            return 0.0;
        }
        (0.24 + self.wave_modulation * 0.16 + self.geometry_mix * 0.22).clamp(0.12, 0.86)
    }

    pub(crate) fn volume_noise_motion(&self) -> f32 {
        if !self.volume_fragment_renderer_ready() {
            return 0.0;
        }
        (0.10 + self.temporal_frequency_hz * 0.04 + self.wave_modulation * 0.08).clamp(0.04, 1.25)
    }

    pub(crate) fn volume_oscillator_mix(&self) -> f32 {
        if !self.volume_fragment_renderer_ready() {
            return 0.0;
        }
        (0.28 + self.wave_modulation * 0.26 + self.geometry_mix * 0.18).clamp(0.0, 1.0)
    }

    pub(crate) fn volume_shell_mix(&self) -> f32 {
        if !self.volume_fragment_renderer_ready() {
            return 0.0;
        }
        (0.12 + self.radial_decay * 0.05 + self.edge_fade * 0.18).clamp(0.0, 0.72)
    }

    pub(crate) fn marker_line(
        &self,
        phase: &str,
        time_seconds: f32,
        panel_bound: bool,
        projection_rows_ready: bool,
    ) -> String {
        format!(
            "{} schema={} phase={} status={} panelBound={} profileId={} profileSchema={} profileSha256={} tuningSha256={} presentationMode={} stereoBinding={} fullscreen=true renderPath={} fragmentVolumeRenderer={} runtimeVolumeRenderer={} gpuRenderReady={} gpuComputeReady=false computeKernel=false volumeNoiseModel={} volumeOscillatorModel={} volumeNoiseScale={:.3} volumeNoiseStrength={:.3} volumeNoiseMotion={:.3} volumeOscillatorMix={:.3} volumeShellMix={:.3} targetCycleHz={:.3} spatialFrequency={:.3} geometryMix={:.3} edgeFade={:.3} volumePresent={} volumeSchema={} volumeFieldKind={} volumeStorageHint={} volumeGridDimensions={} volumeStepCount={} shaderRaymarchSamples={} kernelAbiId={} computePassCount={} volumeReadbackProbeSamples={} stereoFieldOutputLayers={} timeSeconds={:.3}",
            STIMULUS_STEREO_FIELD_MARKER_PREFIX,
            STIMULUS_STEREO_FIELD_MARKER_SCHEMA,
            marker_token(phase),
            if self.enabled {
                "state-applied"
            } else {
                "disabled"
            },
            panel_bound,
            marker_token(&self.profile_id),
            marker_token(&self.profile_schema),
            marker_token(&self.profile_sha256),
            marker_token(&self.tuning_sha256),
            marker_token(&self.presentation_mode),
            marker_token(&self.stereo_binding),
            self.volume_render_path(),
            self.volume_fragment_renderer_ready(),
            self.volume_fragment_renderer_ready(),
            self.volume_fragment_renderer_ready(),
            self.volume_noise_model(),
            self.volume_oscillator_model(),
            self.volume_noise_scale(),
            self.volume_noise_strength(),
            self.volume_noise_motion(),
            self.volume_oscillator_mix(),
            self.volume_shell_mix(),
            self.temporal_frequency_hz,
            self.spatial_frequency,
            self.geometry_mix,
            self.edge_fade,
            self.volume_present,
            marker_token(&self.volume_schema),
            marker_token(&self.volume_field_kind),
            marker_token(&self.volume_storage_hint),
            marker_grid_dimensions(self.volume_grid_dimensions),
            self.volume_step_count,
            self.volume_shader_raymarch_steps(),
            marker_token(&self.kernel_abi_id),
            self.compute_pass_count,
            self.volume_readback_probe_samples,
            self.stereo_field_output_layers,
            time_seconds,
        )
        + &format!(
            " projectionSurface=head-anchored-openxr-view-plane projectionSurfaceRowsReady={} projectionSurfaceCoordinateChain=display-eye-screen-uv-to-shared-head-surface-uv activeEyeSelector=xr_view_id stereoAlignment=per-eye-openxr-homography",
            projection_rows_ready
        )
    }

    pub(crate) fn volume_adoption_marker_line(
        &self,
        phase: &str,
        panel_bound: bool,
    ) -> Option<String> {
        if !self.enabled || !self.volume_present {
            return None;
        }
        Some(format!(
            "{} schema={} phase={} status=profile-adopted panelBound={} profileId={} profileSha256={} volumeSchema={} volumeId={} volumeFieldKind={} volumeStorageHint={} volumeGridDimensions={} volumeStepCount={} shaderRaymarchSamples={} volumeNoiseModel={} volumeOscillatorModel={} volumeNoiseScale={:.3} volumeNoiseStrength={:.3} volumeNoiseMotion={:.3} volumeOscillatorMix={:.3} volumeShellMix={:.3} kernelAbiId={} computePassCount={} volumeReadbackProbeSamples={} stereoFieldOutputLayers={} renderPath={} resourcePlane=staged-optics-json-profile fragmentVolumeRenderer=true runtimeVolumeRenderer=true gpuRenderReady=true gpuComputeReady=false computeKernel=false highRateJsonPayload=false",
            STIMULUS_VOLUME_ADOPTION_MARKER,
            STIMULUS_VOLUME_ADOPTION_MARKER_SCHEMA,
            marker_token(phase),
            panel_bound,
            marker_token(&self.profile_id),
            marker_token(&self.profile_sha256),
            marker_token(&self.volume_schema),
            marker_token(&self.volume_id),
            marker_token(&self.volume_field_kind),
            marker_token(&self.volume_storage_hint),
            marker_grid_dimensions(self.volume_grid_dimensions),
            self.volume_step_count,
            self.volume_shader_raymarch_steps(),
            self.volume_noise_model(),
            self.volume_oscillator_model(),
            self.volume_noise_scale(),
            self.volume_noise_strength(),
            self.volume_noise_motion(),
            self.volume_oscillator_mix(),
            self.volume_shell_mix(),
            marker_token(&self.kernel_abi_id),
            self.compute_pass_count,
            self.volume_readback_probe_samples,
            self.stereo_field_output_layers,
            self.volume_render_path(),
        ))
    }
}

#[derive(Script, ScriptHook, Debug)]
#[repr(C)]
pub struct DrawStimulusStereoField {
    #[deref]
    pub draw_super: DrawQuad,
    #[live(0.0_f32)]
    pub enabled: f32,
    #[live(0.0_f32)]
    pub time_seconds: f32,
    #[live(0.0_f32)]
    pub temporal_frequency_hz: f32,
    #[live(0.0_f32)]
    pub spatial_frequency: f32,
    #[live(0.0_f32)]
    pub rotation_radians: f32,
    #[live(0.0_f32)]
    pub phase_offset: f32,
    #[live(0.0_f32)]
    pub wave_modulation: f32,
    #[live(0.0_f32)]
    pub radial_decay: f32,
    #[live(0.0_f32)]
    pub geometry_mix: f32,
    #[live(0.0_f32)]
    pub edge_fade: f32,
    #[live(vec4(0.0, 0.0, 0.0, 0.0))]
    pub source_a_b: Vec4f,
    #[live(1.0_f32)]
    pub source_b_weight: f32,
    #[live(vec4(0.0, 0.0, 0.0, 1.0))]
    pub color_low: Vec4f,
    #[live(vec4(1.0, 1.0, 1.0, 1.0))]
    pub color_high: Vec4f,
    #[live(0.032_f32)]
    pub display_eye_offset_meters: f32,
    #[live(1.0_f32)]
    pub display_aspect: f32,
    #[live(1.0_f32)]
    pub projection_depth_meters: f32,
    #[live(69.763084_f32)]
    pub projection_preview_fov_y_degrees: f32,
    #[live(-0.168832_f32)]
    pub projection_preview_offset_y_meters: f32,
    #[live(1.0_f32)]
    pub projection_raw_overscan: f32,
    #[live(0.0_f32)]
    pub projection_rows_ready: f32,
    #[live(1.0_f32)]
    pub left_screen_to_surface_h00: f32,
    #[live(0.0_f32)]
    pub left_screen_to_surface_h01: f32,
    #[live(0.0_f32)]
    pub left_screen_to_surface_h02: f32,
    #[live(0.0_f32)]
    pub left_screen_to_surface_h10: f32,
    #[live(1.0_f32)]
    pub left_screen_to_surface_h11: f32,
    #[live(0.0_f32)]
    pub left_screen_to_surface_h12: f32,
    #[live(0.0_f32)]
    pub left_screen_to_surface_h20: f32,
    #[live(0.0_f32)]
    pub left_screen_to_surface_h21: f32,
    #[live(1.0_f32)]
    pub left_screen_to_surface_h22: f32,
    #[live(1.0_f32)]
    pub right_screen_to_surface_h00: f32,
    #[live(0.0_f32)]
    pub right_screen_to_surface_h01: f32,
    #[live(0.0_f32)]
    pub right_screen_to_surface_h02: f32,
    #[live(0.0_f32)]
    pub right_screen_to_surface_h10: f32,
    #[live(1.0_f32)]
    pub right_screen_to_surface_h11: f32,
    #[live(0.0_f32)]
    pub right_screen_to_surface_h12: f32,
    #[live(0.0_f32)]
    pub right_screen_to_surface_h20: f32,
    #[live(0.0_f32)]
    pub right_screen_to_surface_h21: f32,
    #[live(1.0_f32)]
    pub right_screen_to_surface_h22: f32,
    #[live(0.0_f32)]
    pub volume_texture_ready: f32,
    #[live(0.0_f32)]
    pub volume_texture_blend: f32,
    #[live(0.0_f32)]
    pub volume_renderer_ready: f32,
    #[live(0.0_f32)]
    pub volume_renderer_blend: f32,
    #[live(0.0_f32)]
    pub volume_raymarch_steps: f32,
    #[live(1.0_f32)]
    pub volume_grid_frequency: f32,
    #[live(0.72_f32)]
    pub volume_density_gain: f32,
    #[live(1.25_f32)]
    pub volume_absorption: f32,
    #[live(0.0_f32)]
    pub volume_phase: f32,
    #[live(1.0_f32)]
    pub volume_eccentricity: f32,
    #[live(3.0_f32)]
    pub volume_noise_scale: f32,
    #[live(0.42_f32)]
    pub volume_noise_strength: f32,
    #[live(0.18_f32)]
    pub volume_noise_motion: f32,
    #[live(0.44_f32)]
    pub volume_oscillator_mix: f32,
    #[live(0.24_f32)]
    pub volume_shell_mix: f32,
}

impl DrawStimulusStereoField {
    fn apply_state(&mut self, state: &StimulusStereoFieldState, time_seconds: f32) {
        self.enabled = if state.enabled { 1.0 } else { 0.0 };
        self.time_seconds = time_seconds;
        self.temporal_frequency_hz = state.temporal_frequency_hz;
        self.spatial_frequency = state.spatial_frequency;
        self.rotation_radians = state.rotation_radians;
        self.phase_offset = state.phase_offset;
        self.wave_modulation = state.wave_modulation;
        self.radial_decay = state.radial_decay;
        self.geometry_mix = state.geometry_mix;
        self.edge_fade = state.edge_fade;
        self.source_a_b = vec4f(
            state.source_a[0],
            state.source_a[1],
            state.source_b[0],
            state.source_b[1],
        );
        self.source_b_weight = state.source_b_weight;
        self.color_low = vec4f(
            state.color_low[0],
            state.color_low[1],
            state.color_low[2],
            state.color_low[3],
        );
        self.color_high = vec4f(
            state.color_high[0],
            state.color_high[1],
            state.color_high[2],
            state.color_high[3],
        );
        self.display_eye_offset_meters = TARGET_DISPLAY_EYE_OFFSET_METERS;
        self.display_aspect = TARGET_DISPLAY_ASPECT;
        self.projection_depth_meters = makepad_projection_depth_meters();
        self.projection_preview_fov_y_degrees = makepad_projection_preview_fov_y_degrees();
        self.projection_preview_offset_y_meters = makepad_projection_preview_offset_y_meters();
        self.projection_raw_overscan = makepad_projection_raw_overscan();
        let volume_renderer_ready = state.volume_fragment_renderer_ready();
        self.volume_renderer_ready = if volume_renderer_ready { 1.0 } else { 0.0 };
        self.volume_renderer_blend = if volume_renderer_ready {
            state.geometry_mix.clamp(0.0, 1.0)
        } else {
            0.0
        };
        self.volume_raymarch_steps = state.volume_shader_raymarch_steps();
        self.volume_grid_frequency = state.volume_grid_frequency();
        self.volume_density_gain = 0.72;
        self.volume_absorption = 1.25;
        self.volume_phase = 0.37
            + state.volume_step_count as f32 * 0.003
            + time_seconds * state.temporal_frequency_hz.max(0.01) * 0.35;
        self.volume_eccentricity = state.volume_eccentricity();
        self.volume_noise_scale = state.volume_noise_scale();
        self.volume_noise_strength = state.volume_noise_strength();
        self.volume_noise_motion = state.volume_noise_motion();
        self.volume_oscillator_mix = state.volume_oscillator_mix();
        self.volume_shell_mix = state.volume_shell_mix();
    }

    fn apply_projection_rows(&mut self, projection_rows: StimulusSurfaceProjectionRows) {
        self.projection_rows_ready = if projection_rows.ready { 1.0 } else { 0.0 };
        let left = projection_rows.left_screen_to_surface_h;
        let right = projection_rows.right_screen_to_surface_h;
        self.left_screen_to_surface_h00 = left[0][0];
        self.left_screen_to_surface_h01 = left[0][1];
        self.left_screen_to_surface_h02 = left[0][2];
        self.left_screen_to_surface_h10 = left[1][0];
        self.left_screen_to_surface_h11 = left[1][1];
        self.left_screen_to_surface_h12 = left[1][2];
        self.left_screen_to_surface_h20 = left[2][0];
        self.left_screen_to_surface_h21 = left[2][1];
        self.left_screen_to_surface_h22 = left[2][2];
        self.right_screen_to_surface_h00 = right[0][0];
        self.right_screen_to_surface_h01 = right[0][1];
        self.right_screen_to_surface_h02 = right[0][2];
        self.right_screen_to_surface_h10 = right[1][0];
        self.right_screen_to_surface_h11 = right[1][1];
        self.right_screen_to_surface_h12 = right[1][2];
        self.right_screen_to_surface_h20 = right[2][0];
        self.right_screen_to_surface_h21 = right[2][1];
        self.right_screen_to_surface_h22 = right[2][2];
    }

    fn apply_volume_preview_texture(&mut self, texture: Option<Texture>, blend: f32) -> bool {
        let texture_ready = texture.is_some();
        match texture {
            Some(texture) => self
                .draw_super
                .draw_vars
                .set_texture(STIMULUS_VOLUME_TEXTURE_SLOT, &texture),
            None => self
                .draw_super
                .draw_vars
                .empty_texture(STIMULUS_VOLUME_TEXTURE_SLOT),
        }
        self.volume_texture_ready = if texture_ready { 1.0 } else { 0.0 };
        self.volume_texture_blend = if texture_ready {
            blend.clamp(0.0, 1.0)
        } else {
            0.0
        };
        texture_ready
    }

    fn draw(&mut self, cx: &mut CxDraw) -> bool {
        if self.draw_super.draw_vars.can_instance() {
            let new_area = cx.add_instance(&self.draw_super.draw_vars);
            self.draw_super.draw_vars.area =
                cx.update_area_refs(self.draw_super.draw_vars.area, new_area);
            true
        } else {
            false
        }
    }
}

#[derive(Script, Widget)]
pub struct StimulusStereoFieldPanel {
    #[redraw]
    #[live]
    draw_field: DrawStimulusStereoField,
    #[rust]
    state: StimulusStereoFieldState,
    #[rust]
    projection_rows: StimulusSurfaceProjectionRows,
    #[rust]
    volume_texture_bound: bool,
    #[rust]
    volume_texture_blend: f32,
    #[cast]
    #[deref]
    node: XrNode,
}

impl StimulusStereoFieldPanel {
    pub(crate) fn set_stimulus_state(
        &mut self,
        cx: &mut Cx,
        state: StimulusStereoFieldState,
        time_seconds: f32,
        projection_rows: StimulusSurfaceProjectionRows,
        volume_preview_texture: Option<Texture>,
    ) -> bool {
        let requested_volume_blend = if state.enabled && state.volume_present {
            state.geometry_mix.clamp(0.0, 1.0)
        } else {
            0.0
        };
        let effective_volume_texture = if state.enabled && state.volume_present {
            volume_preview_texture
        } else {
            None
        };
        let changed = self.state != state
            || self.projection_rows != projection_rows
            || self.volume_texture_bound != effective_volume_texture.is_some()
            || (self.volume_texture_blend - requested_volume_blend).abs() > 0.0001;
        self.state = state;
        self.projection_rows = projection_rows;
        self.draw_field.apply_state(&self.state, time_seconds);
        self.draw_field.apply_projection_rows(self.projection_rows);
        self.volume_texture_bound = self
            .draw_field
            .apply_volume_preview_texture(effective_volume_texture, requested_volume_blend);
        self.volume_texture_blend = requested_volume_blend;
        self.draw_field.draw_super.draw_vars.redraw(cx);
        self.node.redraw(cx);
        changed
    }
}

impl ScriptHook for StimulusStereoFieldPanel {}

impl Widget for StimulusStereoFieldPanel {
    fn draw_3d(&mut self, cx: &mut Cx3d, scope: &mut Scope) -> DrawStep {
        if cx.scene_state_3d().is_none() {
            return self.node.draw_3d(cx, scope);
        }
        if self.state.enabled {
            let submitted = self.draw_field.draw(cx);
            let marker_index =
                STIMULUS_STEREO_FIELD_DRAW_MARKERS_EMITTED.fetch_add(1, Ordering::AcqRel);
            if marker_index < STIMULUS_STEREO_FIELD_DRAW_MARKER_LIMIT {
                crate::emit_marker_line(&format!(
                    "{} schema={} phase=xr-draw status={} panelBound=true canInstance={} profileId={} profileSha256={} fullscreen=true renderPath={} fragmentVolumeRenderer={} runtimeVolumeRenderer={} gpuRenderReady={} gpuComputeReady=false computeKernel=false volumeNoiseModel={} volumeOscillatorModel={} volumeNoiseScale={:.3} volumeNoiseStrength={:.3} volumeNoiseMotion={:.3} volumeOscillatorMix={:.3} volumeShellMix={:.3} projectionSurfaceRowsReady={} stereoAlignment=per-eye-openxr-homography runtimeTextureBound={} volumeTextureBlend={:.3} volumeRendererBlend={:.3} shaderRaymarchSamples={:.0} stereoFiducialAnchors=center-and-four-corners",
                    STIMULUS_STEREO_FIELD_MARKER_PREFIX,
                    STIMULUS_STEREO_FIELD_MARKER_SCHEMA,
                    if submitted {
                        "xr-draw-submitted"
                    } else {
                        "xr-draw-no-instance"
                    },
                    submitted,
                    marker_token(&self.state.profile_id),
                    marker_token(&self.state.profile_sha256),
                    self.state.volume_render_path(),
                    self.state.volume_fragment_renderer_ready(),
                    self.state.volume_fragment_renderer_ready(),
                    self.state.volume_fragment_renderer_ready(),
                    self.state.volume_noise_model(),
                    self.state.volume_oscillator_model(),
                    self.draw_field.volume_noise_scale,
                    self.draw_field.volume_noise_strength,
                    self.draw_field.volume_noise_motion,
                    self.draw_field.volume_oscillator_mix,
                    self.draw_field.volume_shell_mix,
                    self.projection_rows.ready,
                    self.volume_texture_bound,
                    self.volume_texture_blend,
                    self.draw_field.volume_renderer_blend,
                    self.draw_field.volume_raymarch_steps,
                ));
            }
        }
        self.node.draw_3d(cx, scope)
    }

    fn draw_walk(&mut self, _cx: &mut Cx2d, _scope: &mut Scope, _walk: Walk) -> DrawStep {
        DrawStep::done()
    }
}

fn selected_layer(layer_graph: &Value) -> Option<Value> {
    let layers = layer_graph.get("layers")?.as_array()?;
    layers
        .iter()
        .find(|layer| json_string(layer, &["pattern"]) == Some("Interference"))
        .or_else(|| {
            layers
                .iter()
                .find(|layer| json_string(layer, &["pattern"]) == Some("Ripple"))
        })
        .or_else(|| layers.first())
        .cloned()
}

fn json_string<'a>(value: &'a Value, keys: &[&str]) -> Option<&'a str> {
    let mut current = value;
    for key in keys {
        current = current.get(*key)?;
    }
    current.as_str()
}

fn json_f32(value: &Value, keys: &[&str]) -> Option<f32> {
    let mut current = value;
    for key in keys {
        current = current.get(*key)?;
    }
    current.as_f64().map(|value| value as f32)
}

fn json_vec2(value: &Value, key: &str) -> Option<[f32; 2]> {
    let point = value.get(key)?;
    Some([
        json_f32(point, &["x"]).unwrap_or(0.0),
        json_f32(point, &["y"]).unwrap_or(0.0),
    ])
}

fn json_color_rgba(value: &Value) -> Option<[f32; 4]> {
    Some([
        json_f32(value, &["r"])?.clamp(0.0, 1.0),
        json_f32(value, &["g"])?.clamp(0.0, 1.0),
        json_f32(value, &["b"])?.clamp(0.0, 1.0),
        json_f32(value, &["a"]).unwrap_or(1.0).clamp(0.0, 1.0),
    ])
}

fn marker_token(value: &str) -> String {
    let mut out = String::with_capacity(value.len().max(4));
    for ch in value.chars() {
        if ch.is_ascii_alphanumeric() || ch == '-' || ch == '_' || ch == '.' {
            out.push(ch);
        } else {
            out.push('_');
        }
    }
    if out.is_empty() {
        "none".to_string()
    } else {
        out
    }
}

fn marker_grid_dimensions(dimensions: [u64; 3]) -> String {
    format!("{}x{}x{}", dimensions[0], dimensions[1], dimensions[2])
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusty_quest_makepad_camera_shell::{
        StimulusEffectiveConfig, StimulusPresentationMode, StimulusVolumeProfileSummary,
    };
    use std::path::PathBuf;

    #[test]
    fn volume_adoption_marker_claims_fragment_gpu_renderer_not_compute_kernel() {
        let payload = StimulusProfilePayload {
            config: StimulusEffectiveConfig {
                enabled: true,
                profile_path: "stimulus/volume-profile.json".to_string(),
                profile_sha256:
                    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                        .to_string(),
                profile_schema: "rusty.optics.stimulus.profile.v1".to_string(),
                tuning_path: "none".to_string(),
                tuning_sha256: "none".to_string(),
                presentation_mode: StimulusPresentationMode::StereoEyeField,
            },
            profile_path: PathBuf::from("stimulus/volume-profile.json"),
            profile_id: "stimulus.profile.volume.test".to_string(),
            profile_schema: "rusty.optics.stimulus.profile.v1".to_string(),
            profile_json: r#"{"profile_id":"stimulus.profile.volume.test","schema_id":"rusty.optics.stimulus.profile.v1","presentation":{"mode":"StereoEyeField","coverage":"FullViewport","eye_count":2}}"#.to_string(),
            profile_sha256:
                "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                    .to_string(),
            volume_summary: StimulusVolumeProfileSummary {
                volume_present: true,
                volume_schema: Some("rusty.optics.stimulus.volume.v1".to_string()),
                volume_id: Some("stimulus.volume.test".to_string()),
                field_kind: Some("ProceduralLayerStack3d".to_string()),
                storage_hint: Some("StorageBuffer".to_string()),
                grid_dimensions: Some([32, 32, 32]),
                step_count: Some(32),
                kernel_abi_id: Some("stimulus.kernel.volume_compute_v1".to_string()),
                compute_pass_count: 3,
                volume_readback_probe_samples: Some(512),
                stereo_field_output_layers: Some(2),
            },
        };

        let state = StimulusStereoFieldState::from_profile_payload(&payload).unwrap();
        assert!(state.volume_fragment_renderer_ready());
        assert_eq!(
            state.volume_render_path(),
            STIMULUS_VOLUME_FRAGMENT_RENDER_PATH
        );
        assert_eq!(
            state.volume_shader_raymarch_steps(),
            STIMULUS_VOLUME_FRAGMENT_RAYMARCH_SAMPLES as f32
        );
        assert_eq!(state.volume_noise_model(), STIMULUS_VOLUME_NOISE_MODEL);
        assert_eq!(
            state.volume_oscillator_model(),
            STIMULUS_VOLUME_OSCILLATOR_MODEL
        );
        assert!((state.volume_noise_scale() - 3.0).abs() < 0.0001);
        assert!(state.volume_noise_strength() > 0.0);
        assert!(state.volume_oscillator_mix() > 0.0);

        let draw_marker = state.marker_line("test", 1.25, true, true);
        assert!(draw_marker.contains(&format!(
            "renderPath={STIMULUS_VOLUME_FRAGMENT_RENDER_PATH}"
        )));
        assert!(draw_marker.contains(&format!("volumeNoiseModel={STIMULUS_VOLUME_NOISE_MODEL}")));
        assert!(draw_marker.contains(&format!(
            "volumeOscillatorModel={STIMULUS_VOLUME_OSCILLATOR_MODEL}"
        )));
        assert!(draw_marker.contains("volumeNoiseScale=3.000"));
        assert!(draw_marker.contains("fragmentVolumeRenderer=true"));
        assert!(draw_marker.contains("runtimeVolumeRenderer=true"));
        assert!(draw_marker.contains("gpuRenderReady=true"));
        assert!(draw_marker.contains("gpuComputeReady=false"));
        assert!(draw_marker.contains("volumePresent=true"));
        assert!(draw_marker.contains("volumeGridDimensions=32x32x32"));
        assert!(draw_marker.contains("shaderRaymarchSamples=16"));
        assert!(draw_marker.contains("computeKernel=false"));
        assert!(draw_marker.contains("projectionSurfaceRowsReady=true"));

        let volume_marker = state
            .volume_adoption_marker_line("test", true)
            .expect("volume adoption marker");
        assert!(volume_marker.starts_with(STIMULUS_VOLUME_ADOPTION_MARKER));
        assert!(volume_marker.contains("status=profile-adopted"));
        assert!(volume_marker.contains("volumeReadbackProbeSamples=512"));
        assert!(volume_marker.contains("stereoFieldOutputLayers=2"));
        assert!(volume_marker.contains(&format!(
            "renderPath={STIMULUS_VOLUME_FRAGMENT_RENDER_PATH}"
        )));
        assert!(volume_marker.contains(&format!("volumeNoiseModel={STIMULUS_VOLUME_NOISE_MODEL}")));
        assert!(volume_marker.contains(&format!(
            "volumeOscillatorModel={STIMULUS_VOLUME_OSCILLATOR_MODEL}"
        )));
        assert!(volume_marker.contains("fragmentVolumeRenderer=true"));
        assert!(volume_marker.contains("runtimeVolumeRenderer=true"));
        assert!(volume_marker.contains("gpuRenderReady=true"));
        assert!(volume_marker.contains("gpuComputeReady=false"));
        assert!(volume_marker.contains("computeKernel=false"));
        assert!(volume_marker.contains("highRateJsonPayload=false"));
    }
}
