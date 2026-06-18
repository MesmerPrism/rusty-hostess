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
pub(crate) const STIMULUS_CONTROLLER_RANDOMIZE_MARKER_PREFIX: &str =
    "RUSTY_HOSTESS_MAKEPAD_STIMULUS_RANDOMIZE";
pub(crate) const STIMULUS_CONTROLLER_RANDOMIZE_MARKER_SCHEMA: &str =
    "rusty.hostess.makepad.stimulus_randomize.v1";
pub(crate) const STIMULUS_VOLUME_ADOPTION_MARKER_SCHEMA: &str =
    "rusty.hostess.makepad.stimulus_volume_adoption.v1";
const STIMULUS_STEREO_FIELD_DRAW_MARKER_LIMIT: usize = 8;
static STIMULUS_STEREO_FIELD_DRAW_MARKERS_EMITTED: AtomicUsize = AtomicUsize::new(0);
pub(crate) const STIMULUS_VOLUME_TEXTURE_SLOT: usize = 0;
pub(crate) const STIMULUS_VOLUME_FRAGMENT_RENDER_PATH: &str =
    "makepad-xr-fragment-volume-raymarch-v2";
pub(crate) const STIMULUS_VOLUME_FRAGMENT_RAYMARCH_SAMPLES: u64 = 6;
pub(crate) const STIMULUS_VOLUME_NOISE_MODEL: &str = "value-fbm-mobile-2oct-v1";
pub(crate) const STIMULUS_VOLUME_OSCILLATOR_MODEL: &str = "radial-axial-cross-v1";

pub(crate) const STIMULUS_IDENTITY_SURFACE_HOMOGRAPHY: [[f32; 3]; 3] =
    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum StimulusVolumeColorMode {
    Spectral,
    DepthRamp,
}

impl StimulusVolumeColorMode {
    fn from_hint(value: &str) -> Self {
        if value.eq_ignore_ascii_case("depth_ramp")
            || value.eq_ignore_ascii_case("depthramp")
            || value.eq_ignore_ascii_case("depth")
        {
            Self::DepthRamp
        } else {
            Self::Spectral
        }
    }

    fn marker_token(self) -> &'static str {
        match self {
            Self::Spectral => "Spectral",
            Self::DepthRamp => "DepthRamp",
        }
    }
}

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
    pub(crate) post_contrast: f32,
    pub(crate) post_brightness: f32,
    pub(crate) intensity_gain: f32,
    pub(crate) background_grid_mix: f32,
    pub(crate) texture_flow_strength: f32,
    pub(crate) fiducial_intensity: f32,
    pub(crate) binocular_color_separation: f32,
    pub(crate) binocular_phase_offset_radians: f32,
    pub(crate) volume_only: bool,
    pub(crate) volume_base_layer_mix: f32,
    pub(crate) volume_texture_mix: f32,
    pub(crate) volume_emission_gain: f32,
    pub(crate) volume_black_threshold: f32,
    pub(crate) volume_color_saturation: f32,
    pub(crate) volume_color_mode: StimulusVolumeColorMode,
    pub(crate) volume_depth_color_mix: f32,
    pub(crate) volume_depth_contrast: f32,
    pub(crate) volume_depth_color_near: [f32; 4],
    pub(crate) volume_depth_color_mid: [f32; 4],
    pub(crate) volume_depth_color_far: [f32; 4],
    pub(crate) randomize_min_hz: f32,
    pub(crate) randomize_max_hz: f32,
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
    pub(crate) volume_density_scale: f32,
    pub(crate) volume_opacity_scale: f32,
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
            post_contrast: 1.0,
            post_brightness: 0.0,
            intensity_gain: 1.0,
            background_grid_mix: 0.35,
            texture_flow_strength: 0.0,
            fiducial_intensity: 0.0,
            binocular_color_separation: 0.0,
            binocular_phase_offset_radians: 0.0,
            volume_only: false,
            volume_base_layer_mix: 1.0,
            volume_texture_mix: 0.55,
            volume_emission_gain: 1.0,
            volume_black_threshold: 0.0,
            volume_color_saturation: 0.0,
            volume_color_mode: StimulusVolumeColorMode::Spectral,
            volume_depth_color_mix: 0.0,
            volume_depth_contrast: 1.0,
            volume_depth_color_near: [1.0, 0.85, 0.05, 1.0],
            volume_depth_color_mid: [0.0, 1.0, 0.85, 1.0],
            volume_depth_color_far: [0.30, 0.15, 1.0, 1.0],
            randomize_min_hz: 0.15,
            randomize_max_hz: 2.85,
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
            volume_density_scale: 1.0,
            volume_opacity_scale: 1.0,
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
        let post_contrast = json_f32(post, &["contrast"]).unwrap_or(1.0).clamp(0.0, 4.0);
        let post_brightness = json_f32(post, &["brightness"])
            .unwrap_or(0.0)
            .clamp(-1.0, 1.0);
        let intensity_gain = json_f32(post, &["intensity_gain"])
            .unwrap_or(1.0)
            .clamp(0.0, 4.0);
        let background_grid_mix = json_f32(post, &["background_grid_mix"])
            .unwrap_or(0.35)
            .clamp(0.0, 1.0);
        let texture_flow_strength = json_f32(post, &["texture_flow_strength"])
            .unwrap_or(0.0)
            .clamp(0.0, 0.12);
        let fiducial_intensity = json_f32(presentation, &["fiducial_intensity"])
            .or_else(|| {
                json_bool(presentation, &["debug_fiducials_enabled"]).map(|enabled| {
                    if enabled {
                        0.85
                    } else {
                        0.0
                    }
                })
            })
            .unwrap_or(0.0)
            .clamp(0.0, 1.0);
        let binocular_color_separation = json_f32(presentation, &["binocular_color_separation"])
            .or_else(|| json_f32(presentation, &["stereo_color_separation"]))
            .unwrap_or(0.0)
            .clamp(0.0, 1.0);
        let binocular_phase_offset_radians =
            json_f32(presentation, &["binocular_phase_offset_radians"])
                .or_else(|| json_f32(presentation, &["stereo_phase_offset_radians"]))
                .unwrap_or(0.0)
                .clamp(-std::f32::consts::PI, std::f32::consts::PI);
        let adapter_hints = value.get("adapter_hints").unwrap_or(&Value::Null);
        let makepad_volume_hints = adapter_hints
            .get("makepad_fragment_volume")
            .unwrap_or(&Value::Null);
        let volume_render_mode =
            json_string(makepad_volume_hints, &["render_mode"]).or_else(|| {
                json_string(
                    value.get("volume").unwrap_or(&Value::Null),
                    &["render_mode"],
                )
            });
        let volume_only_by_mode = volume_render_mode
            .map(|mode| {
                mode.eq_ignore_ascii_case("volume_only")
                    || mode.eq_ignore_ascii_case("volumeonly")
                    || mode.eq_ignore_ascii_case("pure_volume")
                    || mode.eq_ignore_ascii_case("purevolume")
            })
            .unwrap_or(false);
        let volume_only = json_bool(makepad_volume_hints, &["volume_only"])
            .or_else(|| json_bool(presentation, &["volume_only"]))
            .unwrap_or(volume_only_by_mode);
        let volume_base_layer_mix = json_f32(makepad_volume_hints, &["base_layer_mix"])
            .or_else(|| json_f32(makepad_volume_hints, &["volume_base_layer_mix"]))
            .or_else(|| json_f32(presentation, &["base_layer_mix"]))
            .unwrap_or(if volume_only { 0.0 } else { 1.0 })
            .clamp(0.0, 1.0);
        let volume_texture_mix = json_f32(makepad_volume_hints, &["texture_mix"])
            .or_else(|| json_f32(makepad_volume_hints, &["volume_texture_mix"]))
            .unwrap_or(if volume_only { 0.0 } else { 0.55 })
            .clamp(0.0, 1.0);
        let volume_emission_gain = json_f32(makepad_volume_hints, &["emission_gain"])
            .or_else(|| json_f32(makepad_volume_hints, &["volume_emission_gain"]))
            .unwrap_or(if volume_only { 3.2 } else { 1.0 })
            .clamp(0.0, 8.0);
        let volume_black_threshold = json_f32(makepad_volume_hints, &["black_threshold"])
            .or_else(|| json_f32(makepad_volume_hints, &["volume_black_threshold"]))
            .unwrap_or(if volume_only { 0.30 } else { 0.0 })
            .clamp(0.0, 0.95);
        let volume_color_saturation = json_f32(makepad_volume_hints, &["color_saturation"])
            .or_else(|| json_f32(makepad_volume_hints, &["volume_color_saturation"]))
            .unwrap_or(if volume_only { 1.0 } else { 0.0 })
            .clamp(0.0, 1.0);
        let volume_color_mode = json_string(makepad_volume_hints, &["color_mode"])
            .or_else(|| json_string(makepad_volume_hints, &["volume_color_mode"]))
            .map(StimulusVolumeColorMode::from_hint)
            .unwrap_or(StimulusVolumeColorMode::Spectral);
        let volume_depth_color_mix_default =
            if volume_color_mode == StimulusVolumeColorMode::DepthRamp {
                0.85
            } else {
                0.0
            };
        let volume_depth_color_mix = json_f32(makepad_volume_hints, &["depth_color_mix"])
            .or_else(|| json_f32(makepad_volume_hints, &["volume_depth_color_mix"]))
            .unwrap_or(volume_depth_color_mix_default)
            .clamp(0.0, 1.0);
        let volume_depth_contrast = json_f32(makepad_volume_hints, &["depth_contrast"])
            .or_else(|| json_f32(makepad_volume_hints, &["volume_depth_contrast"]))
            .unwrap_or(if volume_color_mode == StimulusVolumeColorMode::DepthRamp {
                1.25
            } else {
                1.0
            })
            .clamp(0.10, 4.0);
        let volume_depth_color_near =
            json_color_rgba_path(makepad_volume_hints, &["depth_color_near"])
                .or_else(|| json_color_rgba_path(makepad_volume_hints, &["depth_colors", "near"]))
                .unwrap_or([1.0, 0.85, 0.05, 1.0]);
        let volume_depth_color_mid =
            json_color_rgba_path(makepad_volume_hints, &["depth_color_mid"])
                .or_else(|| json_color_rgba_path(makepad_volume_hints, &["depth_colors", "mid"]))
                .unwrap_or([0.0, 1.0, 0.85, 1.0]);
        let volume_depth_color_far =
            json_color_rgba_path(makepad_volume_hints, &["depth_color_far"])
                .or_else(|| json_color_rgba_path(makepad_volume_hints, &["depth_colors", "far"]))
                .unwrap_or([0.30, 0.15, 1.0, 1.0]);
        let default_randomize_min_hz = if volume_only { 8.0 } else { 0.15 };
        let default_randomize_max_hz = if volume_only { 15.0 } else { 2.85 };
        let randomize_min_hz = json_f32(makepad_volume_hints, &["randomize_min_hz"])
            .or_else(|| json_f32(makepad_volume_hints, &["randomize_hz_min"]))
            .or_else(|| json_f32(makepad_volume_hints, &["randomize_frequency_min_hz"]))
            .unwrap_or(default_randomize_min_hz)
            .clamp(0.01, 120.0);
        let randomize_max_hz = json_f32(makepad_volume_hints, &["randomize_max_hz"])
            .or_else(|| json_f32(makepad_volume_hints, &["randomize_hz_max"]))
            .or_else(|| json_f32(makepad_volume_hints, &["randomize_frequency_max_hz"]))
            .unwrap_or(default_randomize_max_hz)
            .clamp(randomize_min_hz, 120.0);
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
        let volume = value.get("volume").unwrap_or(&Value::Null);
        let volume_density_scale = json_f32(volume, &["density_scale"])
            .unwrap_or(1.0)
            .clamp(0.05, 4.0);
        let volume_opacity_scale = json_f32(volume, &["opacity_scale"])
            .unwrap_or(1.0)
            .clamp(0.05, 4.0);
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
            post_contrast,
            post_brightness,
            intensity_gain,
            background_grid_mix,
            texture_flow_strength,
            fiducial_intensity,
            binocular_color_separation,
            binocular_phase_offset_radians,
            volume_only,
            volume_base_layer_mix,
            volume_texture_mix,
            volume_emission_gain,
            volume_black_threshold,
            volume_color_saturation,
            volume_color_mode,
            volume_depth_color_mix,
            volume_depth_contrast,
            volume_depth_color_near,
            volume_depth_color_mid,
            volume_depth_color_far,
            randomize_min_hz,
            randomize_max_hz,
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
            volume_density_scale,
            volume_opacity_scale,
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

    pub(crate) fn apply_controller_randomize(&mut self, seed: u64) {
        let mut rng = StimulusControllerRandomizer::new(seed);
        let tau = std::f32::consts::PI * 2.0;

        self.temporal_frequency_hz = rng.range(self.randomize_min_hz, self.randomize_max_hz);
        self.spatial_frequency = rng.range(3.0, 22.0);
        self.rotation_radians = rng.range(-std::f32::consts::PI, std::f32::consts::PI);
        self.phase_offset = rng.range(0.0, tau);
        self.wave_modulation = rng.range(0.04, 0.95);
        self.radial_decay = rng.range(0.05, 2.40);
        self.geometry_mix = if rng.next_unit() > 0.25 {
            rng.range(0.48, 1.0)
        } else {
            rng.range(0.12, 0.45)
        };
        self.edge_fade = rng.range(0.02, 0.42);
        self.post_contrast = rng.range(0.90, 2.40);
        self.post_brightness = rng.range(-0.12, 0.16);
        self.intensity_gain = rng.range(0.70, 2.20);
        self.background_grid_mix = rng.range(0.10, 0.82);
        self.texture_flow_strength = rng.range(0.0, 0.10);
        self.fiducial_intensity = if self.fiducial_intensity > 0.0 {
            rng.range(0.20, 0.85)
        } else {
            0.0
        };
        self.binocular_color_separation = rng.range(0.0, 0.32);
        self.binocular_phase_offset_radians = rng.range(-0.42, 0.42);
        self.source_a = [rng.range(-0.42, -0.08), rng.range(-0.26, 0.26)];
        self.source_b = [rng.range(0.08, 0.42), rng.range(-0.26, 0.26)];
        self.source_b_weight = rng.range(0.50, 1.35);
        self.color_low = rng.color(0.03, 0.24);
        self.color_high = rng.color(0.62, 1.0);
        if self.volume_present {
            if self.volume_only {
                self.geometry_mix = 1.0;
                self.volume_base_layer_mix = 0.0;
                self.volume_texture_mix = 0.0;
                self.volume_emission_gain = rng.range(2.10, 3.15);
                self.volume_black_threshold = rng.range(0.18, 0.32);
                self.volume_color_saturation = rng.range(0.86, 1.0);
                if self.volume_color_mode == StimulusVolumeColorMode::DepthRamp {
                    self.volume_depth_color_mix = rng.range(0.92, 1.0);
                    self.volume_depth_contrast = rng.range(0.65, 1.20);
                }
                self.volume_density_scale = rng.range(1.35, 3.40);
                self.volume_opacity_scale = rng.range(1.15, 3.20);
                self.post_contrast = rng.range(1.45, 2.20);
                self.post_brightness = rng.range(-0.08, 0.05);
                self.intensity_gain = rng.range(1.45, 2.40);
                self.background_grid_mix = 0.0;
                self.texture_flow_strength = 0.0;
                self.color_low = rng.color(0.0, 0.035);
                self.color_high = rng.bright_color();
            } else {
                self.volume_density_scale = rng.range(0.55, 1.85);
                self.volume_opacity_scale = rng.range(0.24, 1.25);
            }
        }
    }

    pub(crate) fn controller_randomize_marker_line(
        &self,
        phase: &str,
        randomize_count: u64,
        xr_update_count: u64,
        time_seconds: f32,
        panel_bound: bool,
        projection_rows_ready: bool,
    ) -> String {
        format!(
            "{} schema={} phase={} status=applied source=makepad-xr-actions controller=right primaryButton=rightA action=randomizeStimulusVolume runtimeMutation=true settingsMutated=false profilePayloadMutated=false androidPropertiesMutated=false highRateJsonPayload=false randomizeCount={} xrUpdateCount={} panelBound={} projectionSurfaceRowsReady={} profileId={} profileSha256={} tuningSha256={} renderPath={} fragmentVolumeRenderer={} runtimeVolumeRenderer={} volumePresent={} volumeId={} volumeOnly={} randomizeHzRange={:.3}-{:.3} targetCycleHz={:.3} spatialFrequency={:.3} rotationRadians={:.3} phaseOffset={:.3} waveModulation={:.3} radialDecay={:.3} geometryMix={:.3} edgeFade={:.3} postContrast={:.3} postBrightness={:.3} intensityGain={:.3} backgroundGridMix={:.3} textureFlowStrength={:.3} binocularColorSeparation={:.3} binocularPhaseOffsetRadians={:.3} sourceA={} sourceB={} sourceBWeight={:.3} colorLow={} colorHigh={} volumeBaseLayerMix={:.3} volumeTextureMix={:.3} volumeEmissionGain={:.3} volumeBlackThreshold={:.3} volumeColorSaturation={:.3} volumeColorMode={} volumeDepthColorMix={:.3} volumeDepthContrast={:.3} volumeDepthColorNear={} volumeDepthColorMid={} volumeDepthColorFar={} volumeDensityScale={:.3} volumeOpacityScale={:.3} timeSeconds={:.3}",
            STIMULUS_CONTROLLER_RANDOMIZE_MARKER_PREFIX,
            STIMULUS_CONTROLLER_RANDOMIZE_MARKER_SCHEMA,
            marker_token(phase),
            randomize_count,
            xr_update_count,
            panel_bound,
            projection_rows_ready,
            marker_token(&self.profile_id),
            marker_token(&self.profile_sha256),
            marker_token(&self.tuning_sha256),
            self.volume_render_path(),
            self.volume_fragment_renderer_ready(),
            self.volume_fragment_renderer_ready(),
            self.volume_present,
            marker_token(&self.volume_id),
            self.volume_only,
            self.randomize_min_hz,
            self.randomize_max_hz,
            self.temporal_frequency_hz,
            self.spatial_frequency,
            self.rotation_radians,
            self.phase_offset,
            self.wave_modulation,
            self.radial_decay,
            self.geometry_mix,
            self.edge_fade,
            self.post_contrast,
            self.post_brightness,
            self.intensity_gain,
            self.background_grid_mix,
            self.texture_flow_strength,
            self.binocular_color_separation,
            self.binocular_phase_offset_radians,
            marker_vec2(self.source_a),
            marker_vec2(self.source_b),
            self.source_b_weight,
            marker_color(self.color_low),
            marker_color(self.color_high),
            self.volume_base_layer_mix,
            self.volume_texture_mix,
            self.volume_emission_gain,
            self.volume_black_threshold,
            self.volume_color_saturation,
            self.volume_color_mode_marker(),
            self.volume_depth_color_mix,
            self.volume_depth_contrast,
            marker_color(self.volume_depth_color_near),
            marker_color(self.volume_depth_color_mid),
            marker_color(self.volume_depth_color_far),
            self.volume_density_scale,
            self.volume_opacity_scale,
            time_seconds,
        )
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
        (0.10 + self.temporal_frequency_hz * 0.04 + self.wave_modulation * 0.08).clamp(0.04, 1.45)
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

    pub(crate) fn volume_color_mode_marker(&self) -> &'static str {
        self.volume_color_mode.marker_token()
    }

    pub(crate) fn volume_depth_color_enabled(&self) -> bool {
        self.volume_fragment_renderer_ready()
            && self.volume_color_mode == StimulusVolumeColorMode::DepthRamp
            && self.volume_depth_color_mix > 0.0
    }

    pub(crate) fn marker_line(
        &self,
        phase: &str,
        time_seconds: f32,
        panel_bound: bool,
        projection_rows_ready: bool,
    ) -> String {
        format!(
            "{} schema={} phase={} status={} panelBound={} profileId={} profileSchema={} profileSha256={} tuningSha256={} presentationMode={} stereoBinding={} fullscreen=true renderPath={} fragmentVolumeRenderer={} runtimeVolumeRenderer={} gpuRenderReady={} gpuComputeReady=false computeKernel=false volumeNoiseModel={} volumeOscillatorModel={} volumeNoiseScale={:.3} volumeNoiseStrength={:.3} volumeNoiseMotion={:.3} volumeOscillatorMix={:.3} volumeShellMix={:.3} volumeOnly={} volumeBaseLayerMix={:.3} volumeTextureMix={:.3} volumeEmissionGain={:.3} volumeBlackThreshold={:.3} volumeColorSaturation={:.3} volumeColorMode={} volumeDepthColorMix={:.3} volumeDepthContrast={:.3} volumeDepthColorNear={} volumeDepthColorMid={} volumeDepthColorFar={} randomizeHzRange={:.3}-{:.3} targetCycleHz={:.3} spatialFrequency={:.3} geometryMix={:.3} edgeFade={:.3} postContrast={:.3} postBrightness={:.3} intensityGain={:.3} backgroundGridMix={:.3} textureFlowStrength={:.3} fiducialIntensity={:.3} binocularColorSeparation={:.3} binocularPhaseOffsetRadians={:.3} volumeDensityScale={:.3} volumeOpacityScale={:.3} volumePresent={} volumeSchema={} volumeFieldKind={} volumeStorageHint={} volumeGridDimensions={} volumeStepCount={} shaderRaymarchSamples={} kernelAbiId={} computePassCount={} volumeReadbackProbeSamples={} stereoFieldOutputLayers={} timeSeconds={:.3}",
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
            self.volume_only,
            self.volume_base_layer_mix,
            self.volume_texture_mix,
            self.volume_emission_gain,
            self.volume_black_threshold,
            self.volume_color_saturation,
            self.volume_color_mode_marker(),
            self.volume_depth_color_mix,
            self.volume_depth_contrast,
            marker_color(self.volume_depth_color_near),
            marker_color(self.volume_depth_color_mid),
            marker_color(self.volume_depth_color_far),
            self.randomize_min_hz,
            self.randomize_max_hz,
            self.temporal_frequency_hz,
            self.spatial_frequency,
            self.geometry_mix,
            self.edge_fade,
            self.post_contrast,
            self.post_brightness,
            self.intensity_gain,
            self.background_grid_mix,
            self.texture_flow_strength,
            self.fiducial_intensity,
            self.binocular_color_separation,
            self.binocular_phase_offset_radians,
            self.volume_density_scale,
            self.volume_opacity_scale,
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
            "{} schema={} phase={} status=profile-adopted panelBound={} profileId={} profileSha256={} volumeSchema={} volumeId={} volumeFieldKind={} volumeStorageHint={} volumeGridDimensions={} volumeStepCount={} shaderRaymarchSamples={} volumeNoiseModel={} volumeOscillatorModel={} volumeNoiseScale={:.3} volumeNoiseStrength={:.3} volumeNoiseMotion={:.3} volumeOscillatorMix={:.3} volumeShellMix={:.3} volumeOnly={} volumeBaseLayerMix={:.3} volumeTextureMix={:.3} volumeEmissionGain={:.3} volumeBlackThreshold={:.3} volumeColorSaturation={:.3} volumeColorMode={} volumeDepthColorMix={:.3} volumeDepthContrast={:.3} volumeDepthColorNear={} volumeDepthColorMid={} volumeDepthColorFar={} randomizeHzRange={:.3}-{:.3} kernelAbiId={} computePassCount={} volumeReadbackProbeSamples={} stereoFieldOutputLayers={} renderPath={} resourcePlane=staged-optics-json-profile fragmentVolumeRenderer=true runtimeVolumeRenderer=true gpuRenderReady=true gpuComputeReady=false computeKernel=false highRateJsonPayload=false",
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
            self.volume_only,
            self.volume_base_layer_mix,
            self.volume_texture_mix,
            self.volume_emission_gain,
            self.volume_black_threshold,
            self.volume_color_saturation,
            self.volume_color_mode_marker(),
            self.volume_depth_color_mix,
            self.volume_depth_contrast,
            marker_color(self.volume_depth_color_near),
            marker_color(self.volume_depth_color_mid),
            marker_color(self.volume_depth_color_far),
            self.randomize_min_hz,
            self.randomize_max_hz,
            marker_token(&self.kernel_abi_id),
            self.compute_pass_count,
            self.volume_readback_probe_samples,
            self.stereo_field_output_layers,
            self.volume_render_path(),
        ))
    }
}

struct StimulusControllerRandomizer {
    state: u64,
}

impl StimulusControllerRandomizer {
    fn new(seed: u64) -> Self {
        Self {
            state: seed.wrapping_add(0x9e37_79b9_7f4a_7c15).max(1),
        }
    }

    fn next_unit(&mut self) -> f32 {
        let mut x = self.state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.state = x;
        let value = x.wrapping_mul(0x2545_f491_4f6c_dd1d) >> 40;
        (value as f32) / ((1_u64 << 24) as f32)
    }

    fn range(&mut self, min: f32, max: f32) -> f32 {
        min + (max - min) * self.next_unit().clamp(0.0, 1.0)
    }

    fn color(&mut self, min: f32, max: f32) -> [f32; 4] {
        [
            self.range(min, max).clamp(0.0, 1.0),
            self.range(min, max).clamp(0.0, 1.0),
            self.range(min, max).clamp(0.0, 1.0),
            1.0,
        ]
    }

    fn bright_color(&mut self) -> [f32; 4] {
        let base = match (self.next_unit() * 6.0).floor() as u32 {
            0 => [1.0, 0.08, 0.88],
            1 => [0.00, 0.95, 1.00],
            2 => [1.0, 0.86, 0.04],
            3 => [0.16, 1.00, 0.14],
            4 => [0.58, 0.12, 1.00],
            _ => [1.0, 0.20, 0.03],
        };
        [
            (base[0] + self.range(-0.04, 0.04)).clamp(0.0, 1.0),
            (base[1] + self.range(-0.04, 0.04)).clamp(0.0, 1.0),
            (base[2] + self.range(-0.04, 0.04)).clamp(0.0, 1.0),
            1.0,
        ]
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
    #[live(1.0_f32)]
    pub post_contrast: f32,
    #[live(0.0_f32)]
    pub post_brightness: f32,
    #[live(1.0_f32)]
    pub intensity_gain: f32,
    #[live(0.35_f32)]
    pub background_grid_mix: f32,
    #[live(0.0_f32)]
    pub texture_flow_strength: f32,
    #[live(0.0_f32)]
    pub fiducial_intensity: f32,
    #[live(0.0_f32)]
    pub binocular_color_separation: f32,
    #[live(0.0_f32)]
    pub binocular_phase_offset_radians: f32,
    #[live(0.0_f32)]
    pub volume_only: f32,
    #[live(1.0_f32)]
    pub volume_base_layer_mix: f32,
    #[live(0.55_f32)]
    pub volume_texture_mix: f32,
    #[live(1.0_f32)]
    pub volume_emission_gain: f32,
    #[live(0.0_f32)]
    pub volume_black_threshold: f32,
    #[live(0.0_f32)]
    pub volume_color_saturation: f32,
    #[live(0.0_f32)]
    pub volume_depth_color_enabled: f32,
    #[live(0.0_f32)]
    pub volume_depth_color_mix: f32,
    #[live(1.0_f32)]
    pub volume_depth_contrast: f32,
    #[live(vec4(1.0, 0.85, 0.05, 1.0))]
    pub volume_depth_color_near: Vec4f,
    #[live(vec4(0.0, 1.0, 0.85, 1.0))]
    pub volume_depth_color_mid: Vec4f,
    #[live(vec4(0.30, 0.15, 1.0, 1.0))]
    pub volume_depth_color_far: Vec4f,
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
        self.post_contrast = state.post_contrast;
        self.post_brightness = state.post_brightness;
        self.intensity_gain = state.intensity_gain;
        self.background_grid_mix = state.background_grid_mix;
        self.texture_flow_strength = state.texture_flow_strength;
        self.fiducial_intensity = state.fiducial_intensity;
        self.binocular_color_separation = state.binocular_color_separation;
        self.binocular_phase_offset_radians = state.binocular_phase_offset_radians;
        self.volume_only = if state.volume_only { 1.0 } else { 0.0 };
        self.volume_base_layer_mix = state.volume_base_layer_mix;
        self.volume_texture_mix = state.volume_texture_mix;
        self.volume_emission_gain = state.volume_emission_gain;
        self.volume_black_threshold = state.volume_black_threshold;
        self.volume_color_saturation = state.volume_color_saturation;
        self.volume_depth_color_enabled = if state.volume_depth_color_enabled() {
            1.0
        } else {
            0.0
        };
        self.volume_depth_color_mix = state.volume_depth_color_mix;
        self.volume_depth_contrast = state.volume_depth_contrast;
        self.volume_depth_color_near = vec4f(
            state.volume_depth_color_near[0],
            state.volume_depth_color_near[1],
            state.volume_depth_color_near[2],
            state.volume_depth_color_near[3],
        );
        self.volume_depth_color_mid = vec4f(
            state.volume_depth_color_mid[0],
            state.volume_depth_color_mid[1],
            state.volume_depth_color_mid[2],
            state.volume_depth_color_mid[3],
        );
        self.volume_depth_color_far = vec4f(
            state.volume_depth_color_far[0],
            state.volume_depth_color_far[1],
            state.volume_depth_color_far[2],
            state.volume_depth_color_far[3],
        );
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
            if state.volume_only {
                1.0
            } else {
                state.geometry_mix.clamp(0.0, 1.0)
            }
        } else {
            0.0
        };
        self.volume_raymarch_steps = state.volume_shader_raymarch_steps();
        self.volume_grid_frequency = state.volume_grid_frequency();
        let density_gain_base = if state.volume_only { 1.05 } else { 0.72 };
        let density_gain_max = if state.volume_only { 5.0 } else { 2.40 };
        self.volume_density_gain =
            (density_gain_base * state.volume_density_scale * state.volume_opacity_scale)
                .clamp(0.10, density_gain_max);
        self.volume_absorption = (1.10 + state.volume_opacity_scale * 0.35).clamp(0.40, 2.20);
        self.volume_phase = 0.37
            + state.volume_step_count as f32 * 0.003
            + time_seconds * state.temporal_frequency_hz.max(0.01);
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
            if state.volume_texture_mix <= 0.0 {
                0.0
            } else if state.volume_only {
                1.0
            } else {
                state.geometry_mix.clamp(0.0, 1.0)
            }
        } else {
            0.0
        };
        let effective_volume_texture =
            if state.enabled && state.volume_present && state.volume_texture_mix > 0.0 {
                volume_preview_texture
            } else {
                None
            };
        let changed = self.state != state
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
                    "{} schema={} phase=xr-draw status={} panelBound=true canInstance={} profileId={} profileSha256={} fullscreen=true renderPath={} fragmentVolumeRenderer={} runtimeVolumeRenderer={} gpuRenderReady={} gpuComputeReady=false computeKernel=false volumeNoiseModel={} volumeOscillatorModel={} volumeNoiseScale={:.3} volumeNoiseStrength={:.3} volumeNoiseMotion={:.3} volumeOscillatorMix={:.3} volumeShellMix={:.3} volumeOnly={} volumeBaseLayerMix={:.3} volumeTextureMix={:.3} volumeEmissionGain={:.3} volumeBlackThreshold={:.3} volumeColorSaturation={:.3} volumeColorMode={} volumeDepthColorMix={:.3} volumeDepthContrast={:.3} volumeDepthColorNear={} volumeDepthColorMid={} volumeDepthColorFar={} postContrast={:.3} postBrightness={:.3} intensityGain={:.3} backgroundGridMix={:.3} textureFlowStrength={:.3} binocularColorSeparation={:.3} binocularPhaseOffsetRadians={:.3} projectionSurfaceRowsReady={} stereoAlignment=per-eye-openxr-homography runtimeTextureBound={} volumeTextureBlend={:.3} volumeRendererBlend={:.3} shaderRaymarchSamples={:.0} stereoFiducialsEnabled={} stereoFiducialIntensity={:.3} stereoFiducialAnchors={}",
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
                    self.state.volume_only,
                    self.draw_field.volume_base_layer_mix,
                    self.draw_field.volume_texture_mix,
                    self.draw_field.volume_emission_gain,
                    self.draw_field.volume_black_threshold,
                    self.draw_field.volume_color_saturation,
                    self.state.volume_color_mode_marker(),
                    self.draw_field.volume_depth_color_mix,
                    self.draw_field.volume_depth_contrast,
                    marker_color(self.state.volume_depth_color_near),
                    marker_color(self.state.volume_depth_color_mid),
                    marker_color(self.state.volume_depth_color_far),
                    self.draw_field.post_contrast,
                    self.draw_field.post_brightness,
                    self.draw_field.intensity_gain,
                    self.draw_field.background_grid_mix,
                    self.draw_field.texture_flow_strength,
                    self.draw_field.binocular_color_separation,
                    self.draw_field.binocular_phase_offset_radians,
                    self.projection_rows.ready,
                    self.volume_texture_bound,
                    self.volume_texture_blend,
                    self.draw_field.volume_renderer_blend,
                    self.draw_field.volume_raymarch_steps,
                    self.draw_field.fiducial_intensity > 0.0,
                    self.draw_field.fiducial_intensity,
                    if self.draw_field.fiducial_intensity > 0.0 {
                        "center-and-four-corners"
                    } else {
                        "disabled"
                    },
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

fn json_bool(value: &Value, keys: &[&str]) -> Option<bool> {
    let mut current = value;
    for key in keys {
        current = current.get(*key)?;
    }
    current.as_bool()
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

fn json_color_rgba_path(value: &Value, keys: &[&str]) -> Option<[f32; 4]> {
    let mut current = value;
    for key in keys {
        current = current.get(*key)?;
    }
    json_color_rgba(current)
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

fn marker_vec2(value: [f32; 2]) -> String {
    format!("{:.3},{:.3}", value[0], value[1])
}

fn marker_color(value: [f32; 4]) -> String {
    format!(
        "{:.3},{:.3},{:.3},{:.3}",
        value[0], value[1], value[2], value[3]
    )
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
            profile_json: r#"{"profile_id":"stimulus.profile.volume.test","schema_id":"rusty.optics.stimulus.profile.v1","presentation":{"mode":"StereoEyeField","coverage":"FullViewport","eye_count":2,"fiducial_intensity":0.4},"layer_graph":{"post":{"contrast":2.4,"brightness":0.12,"intensity_gain":1.8,"background_grid_mix":0.7,"texture_flow_strength":0.05}},"volume":{"density_scale":1.6,"opacity_scale":1.5}}"#.to_string(),
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
        assert!((state.post_contrast - 2.4).abs() < 0.0001);
        assert!((state.post_brightness - 0.12).abs() < 0.0001);
        assert!((state.intensity_gain - 1.8).abs() < 0.0001);
        assert!((state.background_grid_mix - 0.7).abs() < 0.0001);
        assert!((state.texture_flow_strength - 0.05).abs() < 0.0001);
        assert!((state.fiducial_intensity - 0.4).abs() < 0.0001);
        assert!((state.binocular_color_separation - 0.0).abs() < 0.0001);
        assert!((state.binocular_phase_offset_radians - 0.0).abs() < 0.0001);
        assert!((state.volume_density_scale - 1.6).abs() < 0.0001);
        assert!((state.volume_opacity_scale - 1.5).abs() < 0.0001);

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
        assert!(draw_marker.contains("postContrast=2.400"));
        assert!(draw_marker.contains("postBrightness=0.120"));
        assert!(draw_marker.contains("intensityGain=1.800"));
        assert!(draw_marker.contains("backgroundGridMix=0.700"));
        assert!(draw_marker.contains("textureFlowStrength=0.050"));
        assert!(draw_marker.contains("fiducialIntensity=0.400"));
        assert!(draw_marker.contains("binocularColorSeparation=0.000"));
        assert!(draw_marker.contains("binocularPhaseOffsetRadians=0.000"));
        assert!(draw_marker.contains("volumeDensityScale=1.600"));
        assert!(draw_marker.contains("volumeOpacityScale=1.500"));
        assert!(draw_marker.contains(&format!(
            "shaderRaymarchSamples={STIMULUS_VOLUME_FRAGMENT_RAYMARCH_SAMPLES}"
        )));
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

    #[test]
    fn controller_randomize_marker_keeps_profile_and_volume_authority_stable() {
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
            profile_json: r#"{"profile_id":"stimulus.profile.volume.test","schema_id":"rusty.optics.stimulus.profile.v1","temporal":{"target_cycle_hz":2.0},"presentation":{"mode":"StereoEyeField","coverage":"FullViewport","eye_count":2},"layer_graph":{"layers":[{"spatial_frequency":12.0,"rotation_radians":0.38,"phase_offset":0.0,"interference":{"source_a":{"x":-0.24,"y":0.0},"source_b":{"x":0.24,"y":0.0},"source_b_weight":1.0,"radial_decay":0.0,"wave_modulation":0.0},"colors":[{"color":{"r":0.0,"g":0.0,"b":0.0,"a":1.0}},{"color":{"r":1.0,"g":1.0,"b":1.0,"a":1.0}}]}],"post":{"contrast":1.0,"brightness":0.0,"intensity_gain":1.0}},"volume":{"density_scale":1.0,"opacity_scale":0.35}}"#.to_string(),
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

        let mut state = StimulusStereoFieldState::from_profile_payload(&payload).unwrap();
        let original = state.clone();
        state.apply_controller_randomize(0xfeed_cafe_1234_5678);

        assert_eq!(state.profile_id, original.profile_id);
        assert_eq!(state.profile_sha256, original.profile_sha256);
        assert_eq!(state.volume_id, original.volume_id);
        assert_eq!(
            state.volume_grid_dimensions,
            original.volume_grid_dimensions
        );
        assert_ne!(state.spatial_frequency, original.spatial_frequency);
        assert!((0.15..=2.85).contains(&state.temporal_frequency_hz));
        assert!((0.55..=1.85).contains(&state.volume_density_scale));
        assert!((0.24..=1.25).contains(&state.volume_opacity_scale));

        let marker =
            state.controller_randomize_marker_line("xr-controller", 3, 44, 8.5, true, true);
        assert!(marker.starts_with(STIMULUS_CONTROLLER_RANDOMIZE_MARKER_PREFIX));
        assert!(marker.contains("controller=right"));
        assert!(marker.contains("primaryButton=rightA"));
        assert!(marker.contains("action=randomizeStimulusVolume"));
        assert!(marker.contains("runtimeMutation=true"));
        assert!(marker.contains("settingsMutated=false"));
        assert!(marker.contains("profilePayloadMutated=false"));
        assert!(marker.contains("androidPropertiesMutated=false"));
        assert!(marker.contains("highRateJsonPayload=false"));
        assert!(marker.contains("volumePresent=true"));
        assert!(marker.contains("randomizeCount=3"));
    }

    #[test]
    fn bright_volume_profile_uses_pure_volume_randomize_contract() {
        let payload = StimulusProfilePayload {
            config: StimulusEffectiveConfig {
                enabled: true,
                profile_path: "stimulus/volume-bright-profile.json".to_string(),
                profile_sha256:
                    "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
                        .to_string(),
                profile_schema: "rusty.optics.stimulus.profile.v1".to_string(),
                tuning_path: "none".to_string(),
                tuning_sha256: "none".to_string(),
                presentation_mode: StimulusPresentationMode::StereoEyeField,
            },
            profile_path: PathBuf::from("stimulus/volume-bright-profile.json"),
            profile_id: "stimulus.profile.volume_bright.test".to_string(),
            profile_schema: "rusty.optics.stimulus.profile.v1".to_string(),
            profile_json: r#"{"profile_id":"stimulus.profile.volume_bright.test","schema_id":"rusty.optics.stimulus.profile.v1","temporal":{"target_cycle_hz":12.0},"safety":{"max_cycle_hz":15.0},"presentation":{"mode":"StereoEyeField","coverage":"FullViewport","eye_count":2},"adapter_hints":{"makepad_fragment_volume":{"render_mode":"VolumeOnly","volume_only":true,"base_layer_mix":0.0,"texture_mix":0.0,"emission_gain":2.65,"black_threshold":0.24,"color_saturation":1.0,"color_mode":"DepthRamp","depth_color_near":{"r":1.0,"g":0.82,"b":0.10,"a":1.0},"depth_color_mid":{"r":0.0,"g":1.0,"b":0.82,"a":1.0},"depth_color_far":{"r":0.46,"g":0.18,"b":1.0,"a":1.0},"depth_color_mix":1.0,"depth_contrast":0.9,"randomize_min_hz":8.0,"randomize_max_hz":15.0}},"layer_graph":{"layers":[{"pattern":"Interference","spatial_frequency":11.5,"rotation_radians":0.16,"phase_offset":0.0,"temporal":{"speed_hz":12.0},"interference":{"source_a":{"x":-0.30,"y":-0.06},"source_b":{"x":0.30,"y":0.06},"source_b_weight":0.96,"radial_decay":0.42,"wave_modulation":0.72},"colors":[{"color":{"r":0.0,"g":0.0,"b":0.0,"a":1.0}},{"color":{"r":0.0,"g":1.0,"b":0.92,"a":1.0}}]}],"post":{"contrast":1.85,"brightness":-0.03,"intensity_gain":1.9,"background_grid_mix":0.0,"texture_flow_strength":0.0}},"volume":{"density_scale":2.2,"opacity_scale":2.4}}"#.to_string(),
            profile_sha256:
                "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
                    .to_string(),
            volume_summary: StimulusVolumeProfileSummary {
                volume_present: true,
                volume_schema: Some("rusty.optics.stimulus.volume.v1".to_string()),
                volume_id: Some("stimulus.volume.bright.test".to_string()),
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

        let mut state = StimulusStereoFieldState::from_profile_payload(&payload).unwrap();
        assert!(state.volume_only);
        assert!((state.temporal_frequency_hz - 12.0).abs() < 0.0001);
        assert!((state.volume_base_layer_mix - 0.0).abs() < 0.0001);
        assert!((state.volume_texture_mix - 0.0).abs() < 0.0001);
        assert!((state.volume_emission_gain - 2.65).abs() < 0.0001);
        assert!((state.volume_black_threshold - 0.24).abs() < 0.0001);
        assert!((state.volume_color_saturation - 1.0).abs() < 0.0001);
        assert_eq!(state.volume_color_mode, StimulusVolumeColorMode::DepthRamp);
        assert!((state.volume_depth_color_mix - 1.0).abs() < 0.0001);
        assert!((state.volume_depth_contrast - 0.9).abs() < 0.0001);
        assert_eq!(state.volume_depth_color_near, [1.0, 0.82, 0.10, 1.0]);
        assert_eq!(state.volume_depth_color_mid, [0.0, 1.0, 0.82, 1.0]);
        assert_eq!(state.volume_depth_color_far, [0.46, 0.18, 1.0, 1.0]);
        assert!(state.volume_depth_color_enabled());
        assert!((state.randomize_min_hz - 8.0).abs() < 0.0001);
        assert!((state.randomize_max_hz - 15.0).abs() < 0.0001);

        let marker = state.marker_line("test", 0.25, true, true);
        assert!(marker.contains("volumeOnly=true"));
        assert!(marker.contains("volumeBaseLayerMix=0.000"));
        assert!(marker.contains("volumeTextureMix=0.000"));
        assert!(marker.contains("volumeEmissionGain=2.650"));
        assert!(marker.contains("volumeBlackThreshold=0.240"));
        assert!(marker.contains("volumeColorSaturation=1.000"));
        assert!(marker.contains("volumeColorMode=DepthRamp"));
        assert!(marker.contains("volumeDepthColorMix=1.000"));
        assert!(marker.contains("volumeDepthContrast=0.900"));
        assert!(marker.contains("volumeDepthColorNear=1.000,0.820,0.100,1.000"));
        assert!(marker.contains("volumeDepthColorMid=0.000,1.000,0.820,1.000"));
        assert!(marker.contains("volumeDepthColorFar=0.460,0.180,1.000,1.000"));
        assert!(marker.contains("randomizeHzRange=8.000-15.000"));

        state.apply_controller_randomize(0x9f9e_7d7c_5b5a_3938);
        assert!((8.0..=15.0).contains(&state.temporal_frequency_hz));
        assert_eq!(state.volume_base_layer_mix, 0.0);
        assert_eq!(state.volume_texture_mix, 0.0);
        assert!((2.10..=3.15).contains(&state.volume_emission_gain));
        assert!(state.volume_color_saturation >= 0.86);
        assert_eq!(state.volume_color_mode, StimulusVolumeColorMode::DepthRamp);
        assert!((0.92..=1.0).contains(&state.volume_depth_color_mix));
        assert!((0.65..=1.20).contains(&state.volume_depth_contrast));

        let randomize_marker =
            state.controller_randomize_marker_line("xr-controller", 7, 88, 2.0, true, true);
        assert!(randomize_marker.contains("primaryButton=rightA"));
        assert!(randomize_marker.contains("volumeOnly=true"));
        assert!(randomize_marker.contains("volumeColorMode=DepthRamp"));
        assert!(randomize_marker.contains("randomizeHzRange=8.000-15.000"));
    }
}
