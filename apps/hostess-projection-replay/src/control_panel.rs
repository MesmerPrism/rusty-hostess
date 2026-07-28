use std::{
    fs,
    path::{Path, PathBuf},
    sync::mpsc::{self, Receiver, Sender},
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

use anyhow::{bail, Context, Result};
use eframe::egui::{self, Color32, RichText, TextureHandle};
use serde::Serialize;

use crate::{
    capsule::{ColorInput, ReplayCapsule},
    control_profile::{
        profile_file_stem, profile_files, read_stored_control, ControlTransportState,
        DesktopPreviewProfile, ProjectionControlState,
        ReplayControlState as StoredReplayControlState, ReplayLayerState, RgbChannelProfile,
        RgbTransformProfile, SurfaceDisplacementProfile, ZoneCompositorProfile,
        REPLAY_CONTROL_STATE_SCHEMA,
    },
    control_transport::ControlTransport,
    sequence::{PreparedFrameInputs, PreparedSequence},
    sha256_file, vulkan,
};

const CONTROL_RECEIPT_SCHEMA: &str = "rusty.hostess.projection_replay_control_update.v2";
const LIVE_RENDER_SLOT_COUNT: u64 = 8;
const EVIDENCE_INTERVAL: Duration = Duration::from_secs(1);
const STRETCH_FLAGS_INDEX: usize = 31;
const DISABLE_PROJECTION_EDGE_GUARD_FLAG: u32 = 1 << 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum CoverageMode {
    Off,
    Buffer,
    Full,
}

impl CoverageMode {
    fn from_uniform(value: f32) -> Self {
        match value.round() as i32 {
            1 => Self::Buffer,
            2 => Self::Full,
            _ => Self::Off,
        }
    }

    fn uniform(self) -> f32 {
        match self {
            Self::Off => 0.0,
            Self::Buffer => 1.0,
            Self::Full => 2.0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum StretchSource {
    Raw,
    Processed,
    Mix,
}

impl StretchSource {
    fn from_uniform(value: f32) -> Self {
        match value.round() as i32 {
            1 => Self::Processed,
            2 => Self::Mix,
            _ => Self::Raw,
        }
    }

    fn uniform(self) -> f32 {
        match self {
            Self::Raw => 0.0,
            Self::Processed => 1.0,
            Self::Mix => 2.0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum DebugView {
    Normal,
    Regions,
    SampleUv,
}

impl DebugView {
    fn from_uniform(value: f32) -> Self {
        match value.round() as i32 {
            1 => Self::Regions,
            2 => Self::SampleUv,
            _ => Self::Normal,
        }
    }

    fn uniform(self) -> f32 {
        match self {
            Self::Normal => 0.0,
            Self::Regions => 1.0,
            Self::SampleUv => 2.0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum RgbMode {
    Off,
    Independent,
    Linked,
}

impl RgbMode {
    fn from_uniform(value: f32) -> Self {
        match value.round() as i32 {
            1 => Self::Independent,
            2 => Self::Linked,
            _ => Self::Off,
        }
    }

    fn uniform(self) -> f32 {
        match self {
            Self::Off => 0.0,
            Self::Independent => 1.0,
            Self::Linked => 2.0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum RgbEdgeMode {
    Clamp,
    Mirror,
    Fade,
}

impl RgbEdgeMode {
    fn from_uniform(value: f32) -> Self {
        match value.round() as i32 {
            1 => Self::Mirror,
            2 => Self::Fade,
            _ => Self::Clamp,
        }
    }

    fn uniform(self) -> f32 {
        match self {
            Self::Clamp => 0.0,
            Self::Mirror => 1.0,
            Self::Fade => 2.0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum PreviewMode {
    Stereo,
    Mono,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum PreviewEye {
    Left,
    Right,
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
struct RgbChannelControl {
    phase_turns: f32,
    rate_hz: f32,
    strength_uv: f32,
    image_scale: f32,
    coverage_scale: f32,
}

impl RgbChannelControl {
    fn from_uniform(uniform: &[f32], channel: usize) -> Self {
        Self {
            phase_turns: wrap_turns(uniform[4 + channel]),
            rate_hz: uniform[8 + channel].clamp(-2.0, 2.0),
            strength_uv: uniform[12 + channel].clamp(0.0, 0.08),
            image_scale: uniform[16 + channel].clamp(0.5, 2.0),
            coverage_scale: uniform[20 + channel].clamp(0.5, 1.0),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum SurfaceDisplacementPreset {
    Off,
    Gentle,
    Deep,
}

impl SurfaceDisplacementPreset {
    fn from_capsule(capsule: &ReplayCapsule) -> Self {
        if !capsule.projection.displacement_enabled
            || capsule.projection.displacement_uniform[0] < 0.5
        {
            return Self::Off;
        }
        if capsule.projection.displacement_uniform[4] >= 0.12 {
            Self::Deep
        } else {
            Self::Gentle
        }
    }

    fn parameters(self) -> (bool, f32, f32) {
        match self {
            Self::Off => (false, 0.0, 0.12),
            Self::Gentle => (true, 0.06, 0.14),
            Self::Deep => (true, 0.18, 0.18),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
struct ReplayControlState {
    layer: String,
    effect_clock_running: bool,
    effect_elapsed_seconds: f32,
    effect_clock_speed: f32,
    preview_target_hz: f32,
    preview_mode: PreviewMode,
    preview_eye: PreviewEye,
    phase_values: Vec<f32>,
    control_transport: Option<ControlTransport>,
    rgb_mode: RgbMode,
    rgb_edge_mode: RgbEdgeMode,
    rgb_channels: [RgbChannelControl; 3],
    projection_edge_guard_enabled: bool,
    surface_displacement: SurfaceDisplacementPreset,
    coverage: CoverageMode,
    stretch_source: StretchSource,
    debug_view: DebugView,
    processed_mix: f32,
    edge_inset_uv: f32,
    max_inset_uv: f32,
    stretch_curve: f32,
    projection_scale: f32,
    buffer_footprint_scale: f32,
    inner_blend_width_uv: f32,
    inner_blend_curve: f32,
    outer_blend_width_uv: f32,
    outer_blend_curve: f32,
    #[serde(skip)]
    loaded_zone_profile: Option<ZoneCompositorProfile>,
}

impl ReplayControlState {
    fn from_capsule(
        capsule: &ReplayCapsule,
        layer: &str,
        control_transport: Option<ControlTransport>,
    ) -> Result<Self> {
        if !capsule.outputs.iter().any(|output| output.name == layer) {
            bail!("capsule has no output layer named {layer}");
        }
        let zone = &capsule.projection.zone_uniform;
        let elapsed_seconds = control_transport
            .as_ref()
            .and_then(|transport| transport.clock.as_ref())
            .map_or(0.0, |clock| clock.initial_seconds);
        let phase_values = control_transport
            .as_ref()
            .map_or_else(Vec::new, |transport| {
                transport
                    .phase_controls
                    .iter()
                    .map(|control| control.initial_phase)
                    .collect()
            });
        Ok(Self {
            layer: layer.to_string(),
            effect_clock_running: true,
            effect_elapsed_seconds: elapsed_seconds,
            effect_clock_speed: 1.0,
            preview_target_hz: 90.0,
            preview_mode: PreviewMode::Stereo,
            preview_eye: PreviewEye::Left,
            phase_values,
            control_transport,
            rgb_mode: RgbMode::from_uniform(capsule.projection.rgb_uniform[0]),
            rgb_edge_mode: RgbEdgeMode::from_uniform(capsule.projection.rgb_uniform[1]),
            rgb_channels: [
                RgbChannelControl::from_uniform(&capsule.projection.rgb_uniform, 0),
                RgbChannelControl::from_uniform(&capsule.projection.rgb_uniform, 1),
                RgbChannelControl::from_uniform(&capsule.projection.rgb_uniform, 2),
            ],
            projection_edge_guard_enabled: !float_flag_enabled(
                zone[STRETCH_FLAGS_INDEX],
                DISABLE_PROJECTION_EDGE_GUARD_FLAG,
            ),
            surface_displacement: SurfaceDisplacementPreset::from_capsule(capsule),
            coverage: CoverageMode::from_uniform(zone[24]),
            stretch_source: StretchSource::from_uniform(zone[25]),
            debug_view: DebugView::from_uniform(zone[26]),
            processed_mix: zone[27].clamp(0.0, 1.0),
            edge_inset_uv: zone[28].clamp(0.0, 0.35),
            max_inset_uv: zone[29].clamp(0.0, 0.35),
            stretch_curve: zone[30].clamp(0.5, 4.0),
            projection_scale: 1.0,
            buffer_footprint_scale: 1.0,
            inner_blend_width_uv: zone[45].clamp(0.0, 0.25),
            inner_blend_curve: zone[46].clamp(0.5, 4.0),
            outer_blend_width_uv: zone[57].clamp(0.0, 0.25),
            outer_blend_curve: zone[58].clamp(0.5, 4.0),
            loaded_zone_profile: None,
        })
    }

    fn apply_to_capsule(
        &self,
        capsule: &mut ReplayCapsule,
        baseline: &ReplayCapsule,
    ) -> Result<()> {
        let selected_output = baseline
            .outputs
            .iter()
            .find(|output| output.name == self.layer)
            .cloned()
            .with_context(|| format!("capsule has no output layer named {}", self.layer))?;
        capsule.outputs = vec![selected_output];

        if let Some(profile) = &self.loaded_zone_profile {
            profile.apply_to_uniform(&mut capsule.projection.zone_uniform)?;
        }
        let elapsed_seconds = self.effect_elapsed_seconds.max(0.0);
        if let Some(transport) = &self.control_transport {
            transport.apply(capsule, elapsed_seconds, &self.phase_values)?;
        }
        apply_rgb_controls(&mut capsule.projection.rgb_uniform, self);

        capsule.projection.zone_uniform[24] = self.coverage.uniform();
        capsule.projection.zone_uniform[25] = self.stretch_source.uniform();
        capsule.projection.zone_uniform[26] = self.debug_view.uniform();
        capsule.projection.zone_uniform[27] = self.processed_mix.clamp(0.0, 1.0);
        capsule.projection.zone_uniform[28] =
            self.edge_inset_uv.clamp(0.0, self.max_inset_uv.max(0.0));
        capsule.projection.zone_uniform[29] = self.max_inset_uv.clamp(0.0, 0.35);
        capsule.projection.zone_uniform[30] = self.stretch_curve.clamp(0.5, 4.0);
        capsule.projection.zone_uniform[STRETCH_FLAGS_INDEX] = set_float_flag(
            capsule.projection.zone_uniform[STRETCH_FLAGS_INDEX],
            DISABLE_PROJECTION_EDGE_GUARD_FLAG,
            !self.projection_edge_guard_enabled,
        );
        capsule.projection.zone_uniform[45] = self.inner_blend_width_uv.clamp(0.0, 0.25);
        capsule.projection.zone_uniform[46] = self.inner_blend_curve.clamp(0.5, 4.0);
        capsule.projection.zone_uniform[57] = self.outer_blend_width_uv.clamp(0.0, 0.25);
        capsule.projection.zone_uniform[58] = self.outer_blend_curve.clamp(0.5, 4.0);

        scale_packed_rect(
            &mut capsule.projection.push_left,
            &baseline.projection.push_left,
            self.projection_scale,
            0.0,
            0.5,
        );
        scale_packed_rect(
            &mut capsule.projection.push_right,
            &baseline.projection.push_right,
            self.projection_scale,
            0.5,
            1.0,
        );
        scale_packed_rect_at(
            &mut capsule.projection.zone_uniform,
            &baseline.projection.zone_uniform,
            0,
            self.buffer_footprint_scale,
            0.0,
            0.5,
        );
        scale_packed_rect_at(
            &mut capsule.projection.zone_uniform,
            &baseline.projection.zone_uniform,
            4,
            self.buffer_footprint_scale,
            0.5,
            1.0,
        );
        apply_surface_displacement(capsule, baseline, self)?;
        Ok(())
    }

    fn apply_control_profile(
        &mut self,
        profile: &StoredReplayControlState,
        baseline: &ReplayCapsule,
    ) -> Result<()> {
        let mut candidate = self.clone();
        candidate.apply_control_profile_in_place(profile, baseline)?;
        *self = candidate;
        Ok(())
    }

    fn apply_control_profile_in_place(
        &mut self,
        profile: &StoredReplayControlState,
        baseline: &ReplayCapsule,
    ) -> Result<()> {
        profile.validate()?;
        let zone_compositor =
            ZoneCompositorProfile::from_uniform(&profile.projection.zone_uniform_f32)?;
        let rgb_channel_transform =
            RgbTransformProfile::from_uniform(&profile.projection.rgb_uniform_f32)?;
        let projection_surface_displacement =
            SurfaceDisplacementProfile::from_capsule(&ReplayCapsule {
                projection: crate::capsule::ProjectionConfiguration {
                    displacement_uniform: profile.projection.displacement_uniform_f32.clone(),
                    displacement_enabled: profile.projection.displacement_enabled,
                    ..baseline.projection.clone()
                },
                ..baseline.clone()
            })?;
        let requested_output = baseline
            .outputs
            .iter()
            .find(|output| output.name == profile.replay_layer.layer_token)
            .with_context(|| {
                format!(
                    "replay layer token {} is not available in this replay capsule",
                    profile.replay_layer.layer_token
                )
            })?;
        if (requested_output.override_value - profile.replay_layer.override_value).abs() >= 0.001 {
            bail!(
                "replay layer override {} disagrees with capsule layer {} override {}",
                profile.replay_layer.override_value,
                requested_output.name,
                requested_output.override_value
            );
        }
        let requested_layer = requested_output.name.clone();
        if let Some(preview) = &profile.preview {
            if preview.layer_token != requested_layer {
                bail!(
                    "preview layer token {} disagrees with replay layer token {}",
                    preview.layer_token,
                    requested_layer
                );
            }
        }
        self.layer = requested_layer;
        self.projection_scale = profile.projection.scale;
        self.loaded_zone_profile = Some(zone_compositor.clone());
        self.coverage = match zone_compositor.coverage_mode.as_str() {
            "buffer" => CoverageMode::Buffer,
            "full" => CoverageMode::Full,
            _ => CoverageMode::Off,
        };
        self.stretch_source = match zone_compositor.stretch_source.as_str() {
            "processed" => StretchSource::Processed,
            "mix" => StretchSource::Mix,
            _ => StretchSource::Raw,
        };
        self.debug_view = match zone_compositor.debug_mode.as_str() {
            "regions" => DebugView::Regions,
            "sample-uv" => DebugView::SampleUv,
            _ => DebugView::Normal,
        };
        self.projection_edge_guard_enabled = zone_compositor.projection_effect_edge_guard_enabled;
        self.processed_mix = zone_compositor.processed_mix;
        self.edge_inset_uv = zone_compositor.edge_inset_uv;
        self.max_inset_uv = zone_compositor.max_inset_uv;
        self.stretch_curve = zone_compositor.stretch_curve;
        self.inner_blend_width_uv = zone_compositor.inner.width_uv;
        self.inner_blend_curve = zone_compositor.inner.curve;
        self.outer_blend_width_uv = zone_compositor.outer.width_uv;
        self.outer_blend_curve = zone_compositor.outer.curve;

        self.rgb_mode = match rgb_channel_transform.mode.as_str() {
            "independent" => RgbMode::Independent,
            "linked" => RgbMode::Linked,
            _ => RgbMode::Off,
        };
        self.rgb_edge_mode = match rgb_channel_transform.edge_mode.as_str() {
            "mirror" => RgbEdgeMode::Mirror,
            "fade" => RgbEdgeMode::Fade,
            _ => RgbEdgeMode::Clamp,
        };
        self.rgb_channels = [
            rgb_control_from_profile(&rgb_channel_transform.red),
            rgb_control_from_profile(&rgb_channel_transform.green),
            rgb_control_from_profile(&rgb_channel_transform.blue),
        ];
        self.surface_displacement = surface_preset_from_profile(&projection_surface_displacement);

        if let Some(desktop) = &profile.preview {
            self.effect_clock_speed = desktop.effect_clock_speed;
            self.preview_target_hz = desktop.preview_target_hz;
            self.preview_mode = if desktop.preview_mode == "mono" {
                PreviewMode::Mono
            } else {
                PreviewMode::Stereo
            };
            self.preview_eye = if desktop.preview_eye == "right" {
                PreviewEye::Right
            } else {
                PreviewEye::Left
            };
            self.buffer_footprint_scale = desktop.buffer_footprint_scale;
        }
        match (&self.control_transport, &profile.control_transport) {
            (Some(descriptor), Some(values))
                if descriptor.transport_id == values.transport_id
                    && descriptor.capsule.sha256 == values.capsule_sha256 =>
            {
                descriptor.validate(baseline, &descriptor.capsule.sha256)?;
                if values.values.len() != descriptor.phase_controls.len()
                    || descriptor
                        .phase_controls
                        .iter()
                        .any(|control| !values.values.contains_key(&control.control_id))
                {
                    bail!("control state phase keys must exactly match the sidecar descriptor");
                }
                let mut phases = Vec::with_capacity(descriptor.phase_controls.len());
                for control in &descriptor.phase_controls {
                    let phase = values.values[&control.control_id];
                    if !phase.is_finite()
                        || phase < control.minimum_phase
                        || phase > control.maximum_phase
                    {
                        bail!(
                            "control state phase {} is outside the sidecar-declared range",
                            control.control_id
                        );
                    }
                    phases.push(phase);
                }
                self.phase_values = phases;
            }
            (Some(descriptor), None)
                if profile.schema == crate::control_profile::REPLAY_CONTROL_STATE_V1_SCHEMA
                    && descriptor.phase_controls.len() == 1 =>
            {
                let preview = profile
                    .preview
                    .as_ref()
                    .context("v1 compatibility requires preview phase values")?;
                let descriptor_rate = descriptor.phase_controls[0].rate_hz;
                if !preview.color_effect_rate_hz.is_finite()
                    || preview.color_effect_rate_hz.to_bits() != descriptor_rate.to_bits()
                {
                    bail!(
                        "v1 control state is incompatible: saved phase rate must exactly match the single sidecar phase-control rate"
                    );
                }
                let phase = preview.color_effect_phase_offset_turns;
                let control = &descriptor.phase_controls[0];
                if !phase.is_finite()
                    || phase < control.minimum_phase
                    || phase > control.maximum_phase
                {
                    bail!("v1 control state phase is outside the sidecar-declared range");
                }
                self.phase_values = vec![preview.color_effect_phase_offset_turns];
            }
            (None, None) => {}
            _ => bail!("control state and transport descriptor binding mismatch"),
        }
        Ok(())
    }
}

fn rgb_control_from_profile(profile: &RgbChannelProfile) -> RgbChannelControl {
    RgbChannelControl {
        phase_turns: profile.direction_turns,
        rate_hz: profile.direction_rate_hz,
        strength_uv: profile.displacement_strength_uv,
        image_scale: profile.image_scale,
        coverage_scale: profile.coverage_scale,
    }
}

fn surface_preset_from_profile(profile: &SurfaceDisplacementProfile) -> SurfaceDisplacementPreset {
    if !profile.enabled || profile.max_displacement_meters <= 0.0001 {
        SurfaceDisplacementPreset::Off
    } else if profile.max_displacement_meters >= 0.12 {
        SurfaceDisplacementPreset::Deep
    } else {
        SurfaceDisplacementPreset::Gentle
    }
}

fn wrap_turns(value: f32) -> f32 {
    value.rem_euclid(1.0)
}

fn float_flag_enabled(value: f32, flag: u32) -> bool {
    (value.max(0.0).floor() as u32) & flag != 0
}

fn set_float_flag(value: f32, flag: u32, enabled: bool) -> f32 {
    let current = value.max(0.0).floor() as u32;
    if enabled {
        (current | flag) as f32
    } else {
        (current & !flag) as f32
    }
}

fn advance_effect_elapsed(elapsed: f32, running: bool, speed: f32, delta: f32) -> f32 {
    if !running || delta <= 0.0 {
        return elapsed;
    }
    elapsed + delta * speed.clamp(0.05, 4.0)
}

fn preview_interval(target_hz: f32) -> Duration {
    Duration::from_secs_f64(1.0 / target_hz.clamp(30.0, 120.0) as f64)
}

fn apply_rgb_controls(uniform: &mut [f32], controls: &ReplayControlState) {
    uniform[0] = controls.rgb_mode.uniform();
    uniform[1] = controls.rgb_edge_mode.uniform();
    uniform[2] = uniform[2].max(1.0);

    let red = controls.rgb_channels[0];
    for channel in 0..3 {
        let settings = if controls.rgb_mode == RgbMode::Linked {
            red
        } else {
            controls.rgb_channels[channel]
        };
        uniform[4 + channel] = wrap_turns(settings.phase_turns);
        uniform[8 + channel] = settings.rate_hz.clamp(-2.0, 2.0);
        uniform[12 + channel] = settings.strength_uv.clamp(0.0, 0.08);
        uniform[16 + channel] = settings.image_scale.clamp(0.5, 2.0);
        uniform[20 + channel] = settings.coverage_scale.clamp(0.5, 1.0);
    }
}

fn apply_surface_displacement(
    capsule: &mut ReplayCapsule,
    baseline: &ReplayCapsule,
    controls: &ReplayControlState,
) -> Result<()> {
    let (enabled, max_displacement_m, edge_taper) = controls.surface_displacement.parameters();
    if enabled && baseline.shaders.displacement_vertex_spirv.is_none() {
        bail!("capsule has no projection-surface displacement vertex shader");
    }

    capsule.projection.displacement_enabled = enabled;
    let uniform = &mut capsule.projection.displacement_uniform;
    uniform[0] = if enabled { 1.0 } else { 0.0 };
    uniform[1] = 1.0;
    uniform[2] = uniform[2].max(1.0);
    uniform[3] = 32.0;
    uniform[4] = max_displacement_m;
    uniform[5] = 2.0;
    uniform[6] = edge_taper;
    uniform[7] = 0.0;

    let (left, right) = match controls.coverage {
        CoverageMode::Off => (
            &capsule.projection.push_left[0..4],
            &capsule.projection.push_right[0..4],
        ),
        CoverageMode::Buffer => (
            &capsule.projection.zone_uniform[0..4],
            &capsule.projection.zone_uniform[4..8],
        ),
        CoverageMode::Full => (
            &baseline.projection.zone_uniform[8..12],
            &baseline.projection.zone_uniform[12..16],
        ),
    };
    let left = [left[0], left[1], left[2], left[3]];
    let right = [right[0], right[1], right[2], right[3]];
    uniform[8..12].copy_from_slice(&left);
    uniform[12..16].copy_from_slice(&right);
    Ok(())
}

fn scale_packed_rect(target: &mut [f32], baseline: &[f32], scale: f32, x_min: f32, x_max: f32) {
    let rect = scaled_rect(&baseline[0..4], scale, x_min, x_max);
    target[0..4].copy_from_slice(&rect);
}

fn scale_packed_rect_at(
    target: &mut [f32],
    baseline: &[f32],
    offset: usize,
    scale: f32,
    x_min: f32,
    x_max: f32,
) {
    let rect = scaled_rect(&baseline[offset..offset + 4], scale, x_min, x_max);
    target[offset..offset + 4].copy_from_slice(&rect);
}

fn scaled_rect(baseline: &[f32], scale: f32, x_min: f32, x_max: f32) -> [f32; 4] {
    let scale = scale.clamp(0.35, 1.8);
    let center_x = baseline[0] + baseline[2] * 0.5;
    let center_y = baseline[1] + baseline[3] * 0.5;
    let width = (baseline[2] * scale).clamp(0.01, x_max - x_min);
    let height = (baseline[3] * scale).clamp(0.01, 1.0);
    let x = (center_x - width * 0.5).clamp(x_min, x_max - width);
    let y = (center_y - height * 0.5).clamp(0.0, 1.0 - height);
    [x, y, width, height]
}

#[derive(Serialize)]
struct ControlReceipt<'a> {
    schema: &'static str,
    status: &'static str,
    revision: u64,
    frame_index: usize,
    state: &'a ReplayControlState,
    effective_capsule_path: String,
    effective_capsule_sha256: String,
    rendered_png: String,
    rendered_sha256: String,
    preview_target_hz: f32,
    preview_observed_fps: f64,
    gpu_round_trip_ms: f64,
    evidence_interval_seconds: f64,
    render_mode: &'static str,
    confidence_boundary: &'static str,
}

struct PreviewSuccess {
    frame_index: usize,
    state: ReplayControlState,
    capsule: ReplayCapsule,
    rgba: Vec<u8>,
    width: u32,
    height: u32,
    gpu_round_trip_ms: f64,
}

struct PreviewResponse {
    revision: u64,
    result: std::result::Result<PreviewSuccess, String>,
}

struct PreviewRequest {
    revision: u64,
    frame_index: usize,
    state: ReplayControlState,
    frame: PreparedFrameInputs,
}

struct EvidenceTask {
    revision: u64,
    frame_index: usize,
    state: ReplayControlState,
    capsule: ReplayCapsule,
    rgba: Vec<u8>,
    width: u32,
    height: u32,
    preview_observed_fps: f64,
    gpu_round_trip_ms: f64,
    output_dir: PathBuf,
}

struct EvidenceResponse {
    result: std::result::Result<PathBuf, String>,
}

struct ControlApp {
    sequence: PreparedSequence,
    baseline_capsule: ReplayCapsule,
    baseline_state: ReplayControlState,
    controls: ReplayControlState,
    layer_names: Vec<String>,
    output_dir: PathBuf,
    profile_dir: PathBuf,
    profile_name: String,
    profile_files: Vec<PathBuf>,
    selected_profile: Option<usize>,
    profile_status: String,
    texture: Option<TextureHandle>,
    frame_index: usize,
    playing: bool,
    last_frame_advance: Instant,
    last_effect_tick: Instant,
    dirty_since: Option<Instant>,
    render_busy: bool,
    revision: u64,
    request_tx: Sender<PreviewRequest>,
    response_rx: Receiver<PreviewResponse>,
    evidence_tx: Sender<EvidenceResponse>,
    evidence_rx: Receiver<EvidenceResponse>,
    evidence_busy: bool,
    evidence_due: bool,
    last_evidence_write: Instant,
    last_preview_complete: Option<Instant>,
    last_preview_submit: Option<Instant>,
    preview_fps: f64,
    gpu_round_trip_ms: f64,
    status: String,
    last_effective_capsule: Option<PathBuf>,
}

impl ControlApp {
    fn new(
        creation_context: &eframe::CreationContext<'_>,
        sequence: PreparedSequence,
        baseline_capsule: ReplayCapsule,
        capsule_path: PathBuf,
        controls: ReplayControlState,
        adapter: Option<String>,
        output_dir: PathBuf,
        profile_dir: PathBuf,
        initial_image: egui::ColorImage,
    ) -> Self {
        configure_style(&creation_context.egui_ctx);
        let texture = creation_context.egui_ctx.load_texture(
            "projection-replay-preview",
            initial_image,
            egui::TextureOptions::LINEAR,
        );
        let layer_names = baseline_capsule
            .outputs
            .iter()
            .map(|output| output.name.clone())
            .collect();
        let (request_tx, request_rx) = mpsc::channel();
        let (response_tx, response_rx) = mpsc::channel();
        let (evidence_tx, evidence_rx) = mpsc::channel();
        let worker_baseline = baseline_capsule.clone();
        let available_profiles = profile_files(&profile_dir).unwrap_or_default();
        let selected_profile = (!available_profiles.is_empty()).then_some(0);
        thread::spawn(move || {
            preview_worker(
                worker_baseline,
                capsule_path,
                adapter,
                request_rx,
                response_tx,
            )
        });
        Self {
            sequence,
            baseline_capsule,
            baseline_state: controls.clone(),
            controls,
            layer_names,
            output_dir,
            profile_dir,
            profile_name: "my-profile".to_string(),
            profile_files: available_profiles,
            selected_profile,
            profile_status:
                "Replay control states are Hostess JSON; legacy Quest profiles are import-only."
                    .to_string(),
            texture: Some(texture),
            frame_index: 0,
            playing: false,
            last_frame_advance: Instant::now(),
            last_effect_tick: Instant::now(),
            dirty_since: None,
            render_busy: false,
            revision: 0,
            request_tx,
            response_rx,
            evidence_tx,
            evidence_rx,
            evidence_busy: false,
            evidence_due: true,
            last_evidence_write: Instant::now()
                .checked_sub(EVIDENCE_INTERVAL)
                .unwrap_or_else(Instant::now),
            last_preview_complete: None,
            last_preview_submit: None,
            preview_fps: 0.0,
            gpu_round_trip_ms: 0.0,
            status: "Initializing persistent Vulkan preview…".to_string(),
            last_effective_capsule: None,
        }
    }

    fn save_current_profile(&mut self) {
        let result = (|| -> Result<PathBuf> {
            let profile_id = profile_file_stem(&self.profile_name);
            let mut capsule = self.baseline_capsule.clone();
            self.controls
                .apply_to_capsule(&mut capsule, &self.baseline_capsule)?;
            let layer_override = capsule
                .outputs
                .first()
                .context("effective capsule has no selected output layer")?
                .override_value;
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .context("system clock is before the Unix epoch")?
                .as_millis() as u64;
            let profile = StoredReplayControlState {
                schema: REPLAY_CONTROL_STATE_SCHEMA.to_string(),
                state_id: profile_id,
                revision: now,
                created_unix_ms: now,
                replay_layer: ReplayLayerState {
                    layer_token: self.controls.layer.clone(),
                    override_value: layer_override,
                },
                projection: ProjectionControlState {
                    scale: self.controls.projection_scale,
                    rgb_uniform_f32: capsule.projection.rgb_uniform.clone(),
                    displacement_uniform_f32: capsule.projection.displacement_uniform.clone(),
                    displacement_enabled: capsule.projection.displacement_enabled,
                    zone_uniform_f32: capsule.projection.zone_uniform.clone(),
                },
                control_transport: self.controls.control_transport.as_ref().map(|transport| {
                    ControlTransportState {
                        transport_id: transport.transport_id.clone(),
                        capsule_sha256: transport.capsule.sha256.clone(),
                        values: transport
                            .phase_controls
                            .iter()
                            .zip(&self.controls.phase_values)
                            .map(|(control, value)| (control.control_id.clone(), *value))
                            .collect(),
                    }
                }),
                preview: Some(DesktopPreviewProfile {
                    layer_token: self.controls.layer.clone(),
                    effect_clock_speed: self.controls.effect_clock_speed,
                    preview_target_hz: self.controls.preview_target_hz,
                    preview_mode: match self.controls.preview_mode {
                        PreviewMode::Stereo => "stereo",
                        PreviewMode::Mono => "mono",
                    }
                    .to_string(),
                    preview_eye: match self.controls.preview_eye {
                        PreviewEye::Left => "left",
                        PreviewEye::Right => "right",
                    }
                    .to_string(),
                    color_effect_phase_offset_turns: 0.0,
                    color_effect_rate_hz: 0.0,
                    buffer_footprint_scale: self.controls.buffer_footprint_scale,
                }),
            };
            profile.write(&self.profile_dir)
        })();
        match result {
            Ok(path) => {
                self.profile_status = format!("Saved {}", path.display());
                self.profile_files = profile_files(&self.profile_dir).unwrap_or_default();
                self.selected_profile = self.profile_files.iter().position(|item| item == &path);
            }
            Err(error) => {
                self.profile_status = format!("Profile save failed: {error:#}");
            }
        }
    }

    fn load_selected_profile(&mut self) {
        let result = (|| -> Result<(StoredReplayControlState, PathBuf)> {
            let index = self.selected_profile.context("choose a profile first")?;
            let path = self
                .profile_files
                .get(index)
                .cloned()
                .context("selected profile is no longer available")?;
            let profile = read_stored_control(&path, &self.baseline_capsule)?;
            self.controls
                .apply_control_profile(&profile, &self.baseline_capsule)?;
            Ok((profile, path))
        })();
        match result {
            Ok((profile, path)) => {
                self.profile_name = profile.state_id;
                self.profile_status = format!("Loaded {}", path.display());
                self.evidence_due = true;
                self.mark_dirty();
            }
            Err(error) => {
                self.profile_status = format!("Profile load failed: {error:#}");
            }
        }
    }

    fn refresh_profiles(&mut self) {
        match profile_files(&self.profile_dir) {
            Ok(files) => {
                self.profile_files = files;
                self.selected_profile = if self.profile_files.is_empty() {
                    None
                } else {
                    Some(
                        self.selected_profile
                            .unwrap_or(0)
                            .min(self.profile_files.len() - 1),
                    )
                };
                self.profile_status =
                    format!("Found {} stored profile(s).", self.profile_files.len());
            }
            Err(error) => {
                self.profile_status = format!("Profile refresh failed: {error:#}");
            }
        }
    }

    fn mark_dirty(&mut self) {
        if self.dirty_since.is_none() {
            self.dirty_since = Some(Instant::now());
        }
    }

    fn tick_effect_clock(&mut self) {
        let now = Instant::now();
        let delta = now
            .saturating_duration_since(self.last_effect_tick)
            .as_secs_f32()
            .min(0.25);
        self.last_effect_tick = now;
        if !self.controls.effect_clock_running || delta <= 0.0 {
            return;
        }
        self.controls.effect_elapsed_seconds = advance_effect_elapsed(
            self.controls.effect_elapsed_seconds,
            self.controls.effect_clock_running,
            self.controls.effect_clock_speed,
            delta,
        );
        self.mark_dirty();
    }

    fn step_frame(&mut self, amount: isize) {
        let frame_count = self.sequence.input_frames.len();
        if frame_count == 0 {
            return;
        }
        self.frame_index =
            (self.frame_index as isize + amount).rem_euclid(frame_count as isize) as usize;
        self.last_frame_advance = Instant::now();
        self.evidence_due = true;
        self.mark_dirty();
    }

    fn poll_render(&mut self, context: &egui::Context) {
        while let Ok(response) = self.response_rx.try_recv() {
            if response.revision != self.revision {
                continue;
            }
            self.render_busy = false;
            match response.result {
                Ok(success) => {
                    let now = Instant::now();
                    if let Some(previous) = self.last_preview_complete.replace(now) {
                        let sample_fps =
                            1.0 / now.duration_since(previous).as_secs_f64().max(0.001);
                        self.preview_fps = if self.preview_fps <= 0.0 {
                            sample_fps
                        } else {
                            self.preview_fps * 0.85 + sample_fps * 0.15
                        };
                    }
                    self.gpu_round_trip_ms = success.gpu_round_trip_ms;
                    let image = color_image_from_rgba(success.width, success.height, &success.rgba);
                    if let Some(texture) = &mut self.texture {
                        texture.set(image, egui::TextureOptions::LINEAR);
                    } else {
                        self.texture = Some(context.load_texture(
                            "projection-replay-preview",
                            image,
                            egui::TextureOptions::LINEAR,
                        ));
                    }
                    self.status = format!(
                        "Live — frame {} · {} · {:.0} fps · {:.1} ms GPU",
                        success.frame_index + 1,
                        friendly_layer_name(&self.controls.layer),
                        self.preview_fps,
                        self.gpu_round_trip_ms
                    );
                    if !self.evidence_busy
                        && (self.evidence_due
                            || self.last_evidence_write.elapsed() >= EVIDENCE_INTERVAL)
                    {
                        self.evidence_busy = true;
                        self.evidence_due = false;
                        self.last_evidence_write = Instant::now();
                        let task = EvidenceTask {
                            revision: response.revision,
                            frame_index: success.frame_index,
                            state: success.state,
                            capsule: success.capsule,
                            rgba: success.rgba,
                            width: success.width,
                            height: success.height,
                            preview_observed_fps: self.preview_fps,
                            gpu_round_trip_ms: success.gpu_round_trip_ms,
                            output_dir: self.output_dir.clone(),
                        };
                        let evidence_tx = self.evidence_tx.clone();
                        thread::spawn(move || {
                            let result =
                                write_preview_evidence(task).map_err(|error| format!("{error:#}"));
                            let _ = evidence_tx.send(EvidenceResponse { result });
                        });
                    }
                }
                Err(error) => {
                    self.status = format!("Preview failed: {error}");
                }
            }
        }
        while let Ok(response) = self.evidence_rx.try_recv() {
            self.evidence_busy = false;
            match response.result {
                Ok(path) => self.last_effective_capsule = Some(path),
                Err(error) => self.status = format!("Evidence write failed: {error}"),
            }
        }
    }

    fn maybe_advance_playback(&mut self) {
        if !self.playing || self.render_busy {
            return;
        }
        if self.last_frame_advance.elapsed() >= self.sequence.frame_interval {
            self.step_frame(1);
        }
    }

    fn maybe_start_render(&mut self) {
        if self.dirty_since.is_none() {
            return;
        }
        if self.render_busy {
            return;
        }
        let target_interval = preview_interval(self.controls.preview_target_hz);
        if self
            .last_preview_submit
            .is_some_and(|last| last.elapsed() < target_interval)
        {
            return;
        }
        let Some(frame) = self.sequence.input_frames.get(self.frame_index).cloned() else {
            self.status = "No replay frame is available".to_string();
            self.dirty_since = None;
            return;
        };

        self.dirty_since = None;
        self.render_busy = true;
        self.revision = self.revision.saturating_add(1);
        let revision = self.revision;
        self.status = format!(
            "Rendering frame {} · {}…",
            self.frame_index + 1,
            friendly_layer_name(&self.controls.layer)
        );
        let request = PreviewRequest {
            revision,
            frame_index: self.frame_index,
            state: self.controls.clone(),
            frame,
        };
        if self.request_tx.send(request).is_err() {
            self.render_busy = false;
            self.status = "Preview worker stopped unexpectedly".to_string();
        } else {
            self.last_preview_submit = Some(Instant::now());
        }
    }

    fn show_controls(&mut self, ui: &mut egui::Ui) {
        ui.heading("Projection replay controls");
        ui.label(
            RichText::new("Quest-camera replay · desktop shader preview")
                .color(Color32::from_rgb(170, 179, 194)),
        );
        ui.add_space(8.0);

        ui.label(RichText::new("Profiles").strong());
        ui.label(
            RichText::new("Save a Hostess replay state; legacy Quest profiles remain load-only.")
                .small()
                .color(Color32::from_rgb(170, 179, 194)),
        );
        ui.horizontal(|ui| {
            ui.label("Name");
            ui.text_edit_singleline(&mut self.profile_name);
        });
        ui.horizontal(|ui| {
            if ui.button("Save current").clicked() {
                self.save_current_profile();
            }
            if ui.button("Refresh").clicked() {
                self.refresh_profiles();
            }
        });
        let selected_profile_name = self
            .selected_profile
            .and_then(|index| self.profile_files.get(index))
            .and_then(|path| path.file_name())
            .and_then(|name| name.to_str())
            .unwrap_or("No stored profile");
        egui::ComboBox::from_id_salt("stored-profile-select")
            .selected_text(selected_profile_name)
            .width(ui.available_width())
            .show_ui(ui, |ui| {
                for (index, path) in self.profile_files.iter().enumerate() {
                    let label = path
                        .file_name()
                        .and_then(|name| name.to_str())
                        .unwrap_or("profile");
                    ui.selectable_value(&mut self.selected_profile, Some(index), label);
                }
            });
        if ui
            .add_enabled(
                self.selected_profile.is_some(),
                egui::Button::new("Load selected"),
            )
            .clicked()
        {
            self.load_selected_profile();
        }
        ui.label(
            RichText::new(&self.profile_status)
                .small()
                .color(Color32::from_rgb(99, 210, 255)),
        );
        ui.label(
            RichText::new(format!("Folder: {}", self.profile_dir.display()))
                .small()
                .color(Color32::from_rgb(170, 179, 194)),
        );

        ui.separator();
        ui.label(RichText::new("Layer").strong());
        egui::ComboBox::from_id_salt("layer-select")
            .selected_text(friendly_layer_name(&self.controls.layer))
            .width(ui.available_width())
            .show_ui(ui, |ui| {
                for layer in &self.layer_names {
                    ui.selectable_value(
                        &mut self.controls.layer,
                        layer.clone(),
                        friendly_layer_name(layer),
                    );
                }
            });

        ui.separator();
        ui.label(RichText::new("Playback").strong());
        ui.horizontal(|ui| {
            if ui.button("◀").on_hover_text("Previous frame").clicked() {
                self.step_frame(-1);
            }
            if ui
                .button(if self.playing { "Pause" } else { "Play" })
                .clicked()
            {
                self.playing = !self.playing;
                self.last_frame_advance = Instant::now();
            }
            if ui.button("▶").on_hover_text("Next frame").clicked() {
                self.step_frame(1);
            }
            ui.label(format!(
                "{} / {}",
                self.frame_index + 1,
                self.sequence.input_frames.len()
            ));
        });
        if self.sequence.input_frames.len() > 1 {
            ui.add(
                egui::Slider::new(
                    &mut self.frame_index,
                    0..=self.sequence.input_frames.len() - 1,
                )
                .show_value(false),
            );
        }

        ui.separator();
        ui.label(RichText::new("Effect clock").strong());
        ui.horizontal(|ui| {
            if ui
                .button(if self.controls.effect_clock_running {
                    "Pause effects"
                } else {
                    "Run effects"
                })
                .clicked()
            {
                self.controls.effect_clock_running = !self.controls.effect_clock_running;
                self.last_effect_tick = Instant::now();
            }
            if ui.button("Reset time").clicked() {
                self.controls.effect_elapsed_seconds = 0.0;
                self.last_effect_tick = Instant::now();
            }
            ui.label(format!("{:.2} s", self.controls.effect_elapsed_seconds));
        });
        value_slider(
            ui,
            &mut self.controls.effect_clock_speed,
            0.05..=4.0,
            "Clock speed",
        );
        value_slider(
            ui,
            &mut self.controls.preview_target_hz,
            30.0..=120.0,
            "Preview Hz",
        );
        if let Some(transport) = &self.controls.control_transport {
            for (control, value) in transport
                .phase_controls
                .iter()
                .zip(&mut self.controls.phase_values)
            {
                value_slider(
                    ui,
                    value,
                    control.minimum_phase..=control.maximum_phase,
                    &control.label,
                );
            }
        }

        ui.separator();
        ui.label(RichText::new("Projection regions").strong());
        ui.label("Coverage");
        ui.horizontal_wrapped(|ui| {
            ui.selectable_value(&mut self.controls.coverage, CoverageMode::Off, "Off");
            ui.selectable_value(&mut self.controls.coverage, CoverageMode::Buffer, "Buffer");
            ui.selectable_value(&mut self.controls.coverage, CoverageMode::Full, "Full");
        });
        value_slider(
            ui,
            &mut self.controls.projection_scale,
            0.5..=1.6,
            "Projection area",
        );
        value_slider(
            ui,
            &mut self.controls.buffer_footprint_scale,
            0.5..=1.5,
            "Buffer footprint",
        );
        ui.label("Surface displacement");
        ui.horizontal_wrapped(|ui| {
            ui.selectable_value(
                &mut self.controls.surface_displacement,
                SurfaceDisplacementPreset::Off,
                "Off",
            );
            ui.selectable_value(
                &mut self.controls.surface_displacement,
                SurfaceDisplacementPreset::Gentle,
                "Gentle",
            );
            ui.selectable_value(
                &mut self.controls.surface_displacement,
                SurfaceDisplacementPreset::Deep,
                "Deep",
            );
        });
        ui.label("Projection effect edge guard");
        ui.horizontal_wrapped(|ui| {
            ui.selectable_value(&mut self.controls.projection_edge_guard_enabled, true, "On")
                .on_hover_text("Fade image displacement and final effect mixing near source edges");
            ui.selectable_value(
                &mut self.controls.projection_edge_guard_enabled,
                false,
                "Off (test)",
            )
            .on_hover_text("Keep full effect strength to the edge for artifact inspection");
        });

        ui.separator();
        ui.label(RichText::new("Border stretch").strong());
        ui.label("Source");
        ui.horizontal_wrapped(|ui| {
            ui.selectable_value(&mut self.controls.stretch_source, StretchSource::Raw, "Raw");
            ui.selectable_value(
                &mut self.controls.stretch_source,
                StretchSource::Processed,
                "Processed",
            );
            ui.selectable_value(&mut self.controls.stretch_source, StretchSource::Mix, "Mix");
        });
        value_slider(
            ui,
            &mut self.controls.edge_inset_uv,
            0.0..=0.20,
            "Edge inset",
        );
        value_slider(
            ui,
            &mut self.controls.max_inset_uv,
            0.01..=0.35,
            "Stretch depth",
        );
        value_slider(
            ui,
            &mut self.controls.stretch_curve,
            0.5..=4.0,
            "Stretch curve",
        );
        if self.controls.stretch_source == StretchSource::Mix {
            value_slider(
                ui,
                &mut self.controls.processed_mix,
                0.0..=1.0,
                "Processed mix",
            );
        }

        ui.separator();
        ui.label(RichText::new("Blend bands").strong());
        value_slider(
            ui,
            &mut self.controls.inner_blend_width_uv,
            0.0..=0.20,
            "Inner width",
        );
        value_slider(
            ui,
            &mut self.controls.inner_blend_curve,
            0.5..=4.0,
            "Inner curve",
        );
        value_slider(
            ui,
            &mut self.controls.outer_blend_width_uv,
            0.0..=0.20,
            "Outer width",
        );
        value_slider(
            ui,
            &mut self.controls.outer_blend_curve,
            0.5..=4.0,
            "Outer curve",
        );

        ui.separator();
        ui.label(RichText::new("RGB channel motion").strong());
        ui.label("Mode");
        ui.horizontal_wrapped(|ui| {
            ui.selectable_value(&mut self.controls.rgb_mode, RgbMode::Off, "Off");
            ui.selectable_value(
                &mut self.controls.rgb_mode,
                RgbMode::Independent,
                "Independent",
            );
            ui.selectable_value(&mut self.controls.rgb_mode, RgbMode::Linked, "Linked");
        });
        ui.label("Edge behavior");
        ui.horizontal_wrapped(|ui| {
            ui.selectable_value(
                &mut self.controls.rgb_edge_mode,
                RgbEdgeMode::Clamp,
                "Clamp",
            );
            ui.selectable_value(
                &mut self.controls.rgb_edge_mode,
                RgbEdgeMode::Mirror,
                "Mirror",
            );
            ui.selectable_value(&mut self.controls.rgb_edge_mode, RgbEdgeMode::Fade, "Fade");
        });
        let active_channels = match self.controls.rgb_mode {
            RgbMode::Off => 0,
            RgbMode::Independent => 3,
            RgbMode::Linked => 1,
        };
        for channel in 0..active_channels {
            let label = if self.controls.rgb_mode == RgbMode::Linked {
                "Linked RGB"
            } else {
                ["Red", "Green", "Blue"][channel]
            };
            ui.label(RichText::new(label).small().strong());
            value_slider(
                ui,
                &mut self.controls.rgb_channels[channel].phase_turns,
                0.0..=1.0,
                "Phase",
            );
            value_slider(
                ui,
                &mut self.controls.rgb_channels[channel].rate_hz,
                -2.0..=2.0,
                "Rate",
            );
            value_slider(
                ui,
                &mut self.controls.rgb_channels[channel].strength_uv,
                0.0..=0.08,
                "Strength",
            );
            value_slider(
                ui,
                &mut self.controls.rgb_channels[channel].image_scale,
                0.5..=2.0,
                "Image scale",
            );
            value_slider(
                ui,
                &mut self.controls.rgb_channels[channel].coverage_scale,
                0.5..=1.0,
                "Coverage scale",
            );
        }
        if self.controls.rgb_mode == RgbMode::Off {
            ui.label(
                RichText::new("Enable Linked or Independent to edit channel transforms.")
                    .small()
                    .color(Color32::from_rgb(170, 179, 194)),
            );
        }
        if ui.button("Independent motion preset").clicked() {
            self.controls.rgb_mode = RgbMode::Independent;
            self.controls.rgb_edge_mode = RgbEdgeMode::Mirror;
            self.controls.rgb_channels = [
                RgbChannelControl {
                    phase_turns: 0.0,
                    rate_hz: 0.11,
                    strength_uv: 0.018,
                    image_scale: 1.0,
                    coverage_scale: 1.0,
                },
                RgbChannelControl {
                    phase_turns: 0.333_333,
                    rate_hz: 0.17,
                    strength_uv: 0.014,
                    image_scale: 1.05,
                    coverage_scale: 0.92,
                },
                RgbChannelControl {
                    phase_turns: 0.666_667,
                    rate_hz: -0.13,
                    strength_uv: 0.022,
                    image_scale: 0.95,
                    coverage_scale: 0.84,
                },
            ];
        }

        ui.separator();
        ui.label(RichText::new("View").strong());
        ui.horizontal_wrapped(|ui| {
            ui.selectable_value(&mut self.controls.debug_view, DebugView::Normal, "Normal");
            ui.selectable_value(&mut self.controls.debug_view, DebugView::Regions, "Regions");
            ui.selectable_value(
                &mut self.controls.debug_view,
                DebugView::SampleUv,
                "Sample UV",
            );
        });
        ui.horizontal(|ui| {
            if ui.button("Buffer preset").clicked() {
                self.controls.coverage = CoverageMode::Buffer;
                self.controls.stretch_source = StretchSource::Raw;
                self.controls.edge_inset_uv = 0.015;
                self.controls.max_inset_uv = 0.14;
                self.controls.stretch_curve = 1.6;
            }
            if ui.button("Full stretch").clicked() {
                self.controls.coverage = CoverageMode::Full;
                self.controls.stretch_source = StretchSource::Raw;
            }
        });
        if ui.button("Reset settings").clicked() {
            let current_layer = self.controls.layer.clone();
            self.controls = self.baseline_state.clone();
            self.controls.layer = current_layer;
        }

        ui.separator();
        ui.label(RichText::new(&self.status).small().color(
            if self.status.starts_with("Preview failed")
                || self.status.starts_with("Evidence write failed")
            {
                Color32::from_rgb(255, 120, 120)
            } else {
                Color32::from_rgb(170, 179, 194)
            },
        ));
        if let Some(path) = &self.last_effective_capsule {
            ui.label(
                RichText::new(format!("Saved: {}", path.display()))
                    .small()
                    .color(Color32::from_rgb(99, 210, 255)),
            );
        }
    }

    fn show_preview_mode(&mut self, ui: &mut egui::Ui) {
        ui.horizontal_centered(|ui| {
            ui.label(RichText::new("Preview").strong());
            ui.selectable_value(
                &mut self.controls.preview_mode,
                PreviewMode::Stereo,
                "Stereo",
            )
            .on_hover_text("Show both packed stereo eyes");
            ui.selectable_value(&mut self.controls.preview_mode, PreviewMode::Mono, "Mono")
                .on_hover_text("Enlarge one eye for effect tuning");
            if self.controls.preview_mode == PreviewMode::Mono {
                ui.separator();
                ui.selectable_value(&mut self.controls.preview_eye, PreviewEye::Left, "Left eye");
                ui.selectable_value(
                    &mut self.controls.preview_eye,
                    PreviewEye::Right,
                    "Right eye",
                );
            }
        });
    }

    fn show_preview(&self, ui: &mut egui::Ui) {
        let Some(texture) = &self.texture else {
            ui.centered_and_justified(|ui| {
                ui.spinner();
            });
            return;
        };
        let available = ui.available_size();
        let (source, uv) = preview_source_and_uv(
            texture.size_vec2(),
            self.controls.preview_mode,
            self.controls.preview_eye,
        );
        let scale = (available.x / source.x)
            .min(available.y / source.y)
            .max(0.01);
        let size = source * scale;
        ui.centered_and_justified(|ui| {
            ui.add(egui::Image::new((texture.id(), size)).uv(uv));
        });
    }
}

fn preview_source_and_uv(
    stereo_source: egui::Vec2,
    mode: PreviewMode,
    eye: PreviewEye,
) -> (egui::Vec2, egui::Rect) {
    match mode {
        PreviewMode::Stereo => (
            stereo_source,
            egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(1.0, 1.0)),
        ),
        PreviewMode::Mono => {
            let (left, right) = match eye {
                PreviewEye::Left => (0.0, 0.5),
                PreviewEye::Right => (0.5, 1.0),
            };
            (
                egui::vec2(stereo_source.x * 0.5, stereo_source.y),
                egui::Rect::from_min_max(egui::pos2(left, 0.0), egui::pos2(right, 1.0)),
            )
        }
    }
}

impl eframe::App for ControlApp {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let context = ui.ctx().clone();
        self.poll_render(&context);
        self.tick_effect_clock();
        if context.input(|input| input.key_pressed(egui::Key::Space)) {
            self.playing = !self.playing;
            self.last_frame_advance = Instant::now();
        }
        if context.input(|input| input.key_pressed(egui::Key::ArrowLeft)) {
            self.step_frame(-1);
        }
        if context.input(|input| input.key_pressed(egui::Key::ArrowRight)) {
            self.step_frame(1);
        }
        if context.input(|input| input.key_pressed(egui::Key::M)) {
            self.controls.preview_mode = match self.controls.preview_mode {
                PreviewMode::Stereo => PreviewMode::Mono,
                PreviewMode::Mono => PreviewMode::Stereo,
            };
        }
        self.maybe_advance_playback();

        let before_controls = self.controls.clone();
        let before_frame = self.frame_index;
        egui::Panel::top("preview-mode")
            .resizable(false)
            .exact_size(40.0)
            .show(ui, |ui| self.show_preview_mode(ui));
        egui::Panel::right("controls")
            .resizable(false)
            .default_size(330.0)
            .min_size(330.0)
            .max_size(330.0)
            .show(ui, |ui| {
                egui::ScrollArea::vertical()
                    .auto_shrink([false, false])
                    .show(ui, |ui| self.show_controls(ui));
            });
        egui::CentralPanel::default().show(ui, |ui| self.show_preview(ui));
        if self.controls != before_controls || self.frame_index != before_frame {
            self.evidence_due = true;
            self.mark_dirty();
        }
        self.maybe_start_render();
        context.request_repaint_after(preview_interval(self.controls.preview_target_hz));
    }
}

fn preview_worker(
    baseline: ReplayCapsule,
    capsule_path: PathBuf,
    adapter: Option<String>,
    request_rx: Receiver<PreviewRequest>,
    response_tx: Sender<PreviewResponse>,
) {
    let mut renderer =
        match vulkan::PreviewRenderer::new(&baseline, &capsule_path, adapter.as_deref()) {
            Ok(renderer) => renderer,
            Err(error) => {
                if let Ok(request) = request_rx.recv() {
                    let _ = response_tx.send(PreviewResponse {
                        revision: request.revision,
                        result: Err(format!(
                            "persistent Vulkan initialization failed: {error:#}"
                        )),
                    });
                }
                return;
            }
        };
    while let Ok(request) = request_rx.recv() {
        let revision = request.revision;
        let result = render_preview_request(&mut renderer, &baseline, &capsule_path, request)
            .map_err(|error| format!("{error:#}"));
        if response_tx
            .send(PreviewResponse { revision, result })
            .is_err()
        {
            break;
        }
    }
}

fn render_preview_request(
    renderer: &mut vulkan::PreviewRenderer,
    baseline: &ReplayCapsule,
    capsule_path: &Path,
    request: PreviewRequest,
) -> Result<PreviewSuccess> {
    let mut capsule = baseline.clone();
    request.state.apply_to_capsule(&mut capsule, baseline)?;
    capsule.inputs.camera_left = ColorInput::Png {
        path: request.frame.left,
    };
    capsule.inputs.camera_right = ColorInput::Png {
        path: request.frame.right,
    };
    if let Some(video) = request.frame.video {
        capsule.inputs.video = ColorInput::Png { path: video };
    }
    capsule.validate(capsule_path)?;
    let preview = renderer.render(&capsule, request.frame_index)?;
    Ok(PreviewSuccess {
        frame_index: request.frame_index,
        state: request.state,
        capsule,
        rgba: preview.rgba,
        width: preview.width,
        height: preview.height,
        gpu_round_trip_ms: preview.gpu_round_trip_ms,
    })
}

fn write_preview_evidence(task: EvidenceTask) -> Result<PathBuf> {
    let control_dir = task.output_dir.join("interactive");
    let render_dir = live_render_dir(&control_dir, task.revision);
    fs::create_dir_all(&render_dir)
        .with_context(|| format!("failed to create {}", render_dir.display()))?;
    let effective_capsule_path = render_dir.join("effective.capsule.json");
    let capsule_bytes = serde_json::to_vec_pretty(&task.capsule)?;
    fs::write(&effective_capsule_path, &capsule_bytes)?;
    task.capsule.validate(&effective_capsule_path)?;
    let rendered_path = render_dir.join(format!("{}.png", sanitize_layer_name(&task.state.layer)));
    let image = image::RgbaImage::from_raw(task.width, task.height, task.rgba)
        .context("persistent preview returned an invalid RGBA buffer size")?;
    image
        .save(&rendered_path)
        .with_context(|| format!("failed to save {}", rendered_path.display()))?;
    let receipt = ControlReceipt {
        schema: CONTROL_RECEIPT_SCHEMA,
        status: "pass",
        revision: task.revision,
        frame_index: task.frame_index,
        state: &task.state,
        effective_capsule_path: effective_capsule_path.display().to_string(),
        effective_capsule_sha256: sha256_file(&effective_capsule_path)?,
        rendered_png: rendered_path.display().to_string(),
        rendered_sha256: sha256_file(&rendered_path)?,
        preview_target_hz: task.state.preview_target_hz,
        preview_observed_fps: task.preview_observed_fps,
        gpu_round_trip_ms: task.gpu_round_trip_ms,
        evidence_interval_seconds: EVIDENCE_INTERVAL.as_secs_f64(),
        render_mode: "persistent-vulkan-live-preview",
        confidence_boundary:
            "desktop-vulkan-effect-replay-only;quest-composition-performance-and-comfort-remain-device-gates",
    };
    let receipt_bytes = serde_json::to_vec_pretty(&receipt)?;
    fs::write(render_dir.join("control-receipt.json"), &receipt_bytes)?;
    fs::create_dir_all(&control_dir)?;
    fs::write(control_dir.join("effective.capsule.json"), &capsule_bytes)?;
    fs::write(
        control_dir.join("latest-control-receipt.json"),
        receipt_bytes,
    )?;

    Ok(effective_capsule_path)
}

fn sanitize_layer_name(name: &str) -> String {
    let sanitized = name
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || character == '-' || character == '_' {
                character.to_ascii_lowercase()
            } else {
                '-'
            }
        })
        .collect::<String>();
    sanitized.trim_matches('-').to_string()
}

fn live_render_dir(control_dir: &Path, revision: u64) -> PathBuf {
    control_dir.join(format!(
        "live-slot-{:02}",
        revision % LIVE_RENDER_SLOT_COUNT
    ))
}

fn value_slider(
    ui: &mut egui::Ui,
    value: &mut f32,
    range: std::ops::RangeInclusive<f32>,
    label: &str,
) {
    ui.add(
        egui::Slider::new(value, range)
            .text(label)
            .fixed_decimals(3),
    );
}

fn friendly_layer_name(layer: &str) -> &str {
    match layer {
        "final" => "Final composite",
        "raw-brightness" => "Raw brightness",
        "preblur-brightness" => "Blurred brightness",
        "raw-strength" => "Raw strength",
        "blurred-strength" => "Blurred strength",
        "displacement" => "Displacement",
        "depth-gradient" => "Depth",
        other => other,
    }
}

fn load_color_image(path: &Path) -> Result<egui::ColorImage> {
    let rgba = image::open(path)
        .with_context(|| format!("failed to open preview {}", path.display()))?
        .into_rgba8();
    let size = [rgba.width() as usize, rgba.height() as usize];
    Ok(egui::ColorImage::from_rgba_unmultiplied(
        size,
        rgba.as_raw(),
    ))
}

fn color_image_from_rgba(width: u32, height: u32, rgba: &[u8]) -> egui::ColorImage {
    egui::ColorImage::from_rgba_unmultiplied([width as usize, height as usize], rgba)
}

fn configure_style(context: &egui::Context) {
    context.set_theme(egui::Theme::Dark);
    let mut visuals = egui::Visuals::dark();
    visuals.panel_fill = Color32::from_rgb(32, 38, 52);
    visuals.window_fill = Color32::from_rgb(32, 38, 52);
    visuals.extreme_bg_color = Color32::from_rgb(20, 24, 32);
    visuals.faint_bg_color = Color32::from_rgb(41, 49, 66);
    visuals.widgets.inactive.bg_fill = Color32::from_rgb(41, 49, 66);
    visuals.widgets.hovered.bg_fill = Color32::from_rgb(59, 70, 90);
    visuals.widgets.active.bg_fill = Color32::from_rgb(51, 112, 138);
    visuals.selection.bg_fill = Color32::from_rgb(51, 112, 138);
    visuals.selection.stroke.color = Color32::from_rgb(244, 247, 250);
    context.set_visuals(visuals);
    context.style_mut_of(egui::Theme::Dark, |style| {
        style.spacing.item_spacing = egui::vec2(8.0, 7.0);
        style.spacing.button_padding = egui::vec2(10.0, 5.0);
    });
}

pub(crate) fn run(
    sequence: PreparedSequence,
    capsule_path: &Path,
    output_dir: &Path,
    adapter: Option<String>,
    initial_layer: &str,
    camera_only: bool,
    requested_profile_dir: Option<&Path>,
    requested_control_transport: Option<&Path>,
) -> Result<()> {
    let capsule_path = capsule_path
        .canonicalize()
        .with_context(|| format!("capsule does not exist: {}", capsule_path.display()))?;
    let loaded_capsule = ReplayCapsule::read_bound(&capsule_path)?;
    let capsule_sha256 = loaded_capsule.sha256;
    let mut baseline_capsule = loaded_capsule.capsule;
    baseline_capsule
        .make_paths_absolute(capsule_path.parent().unwrap_or_else(|| Path::new(".")))?;
    if camera_only {
        baseline_capsule.inputs.video = ColorInput::Transparent;
        baseline_capsule.projection.displacement_enabled = false;
        baseline_capsule.projection.zone_uniform[24] = 0.0;
        baseline_capsule.projection.zone_uniform[26] = 0.0;
    }
    let control_transport = requested_control_transport
        .map(|path| ControlTransport::read(path, &baseline_capsule, &capsule_sha256))
        .transpose()?;
    let controls =
        ReplayControlState::from_capsule(&baseline_capsule, initial_layer, control_transport)?;
    let first_frame = sequence
        .frame_paths
        .first()
        .context("prepared sequence contains no rendered frames")?;
    let initial_image = load_color_image(first_frame)?;
    fs::create_dir_all(output_dir)?;
    let output_dir = output_dir
        .canonicalize()
        .with_context(|| format!("failed to resolve {}", output_dir.display()))?;
    let profile_dir = requested_profile_dir
        .map(Path::to_path_buf)
        .unwrap_or_else(|| output_dir.join("profiles"));
    fs::create_dir_all(&profile_dir).with_context(|| {
        format!(
            "failed to create profile directory {}",
            profile_dir.display()
        )
    })?;
    let profile_dir = profile_dir.canonicalize().with_context(|| {
        format!(
            "failed to resolve profile directory {}",
            profile_dir.display()
        )
    })?;

    let mut native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1240.0, 760.0])
            .with_min_inner_size([900.0, 600.0]),
        ..Default::default()
    };
    native_options.glow_options.vsync = false;
    eframe::run_native(
        "Rusty Hostess — Projection replay controls",
        native_options,
        Box::new(move |creation_context| {
            Ok(Box::new(ControlApp::new(
                creation_context,
                sequence,
                baseline_capsule,
                capsule_path,
                controls,
                adapter,
                output_dir,
                profile_dir,
                initial_image,
            )))
        }),
    )
    .map_err(|error| anyhow::anyhow!("failed to run projection controls: {error}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capsule::{
        DepthInput, Extent, GuideConfiguration, OutputLayer, ProjectionConfiguration, ReplayInputs,
        ShaderBundle,
    };

    fn test_capsule() -> ReplayCapsule {
        let mut push_left = vec![0.0; 32];
        push_left[0..4].copy_from_slice(&[0.14, 0.26, 0.22, 0.50]);
        let mut push_right = vec![0.0; 32];
        push_right[0..4].copy_from_slice(&[0.64, 0.26, 0.22, 0.50]);
        let mut zone_uniform = vec![0.0; 92];
        let mut rgb_uniform = vec![0.0; 24];
        rgb_uniform[16..19].fill(1.0);
        rgb_uniform[20..23].fill(1.0);
        zone_uniform[0..4].copy_from_slice(&[0.08, 0.15, 0.34, 0.72]);
        zone_uniform[4..8].copy_from_slice(&[0.58, 0.15, 0.34, 0.72]);
        zone_uniform[24] = 1.0;
        zone_uniform[25] = 0.0;
        zone_uniform[28] = 0.015;
        zone_uniform[29] = 0.14;
        zone_uniform[30] = 1.6;
        zone_uniform[45] = 0.04;
        zone_uniform[46] = 1.6;
        zone_uniform[57] = 0.04;
        zone_uniform[58] = 1.6;
        ReplayCapsule {
            schema: "rusty.hostess.projection_replay_capsule.v1".to_string(),
            name: "test".to_string(),
            extent: Extent {
                width: 100,
                height: 100,
            },
            shaders: ShaderBundle {
                fullscreen_vertex_spirv: PathBuf::from("full.spv"),
                guide_fragment_spirv: vec![PathBuf::from("guide.spv"); 6],
                projection_fragment_spirv: PathBuf::from("projection.spv"),
                displacement_vertex_spirv: None,
            },
            inputs: ReplayInputs {
                camera_left: ColorInput::Transparent,
                camera_right: ColorInput::Transparent,
                video: ColorInput::Transparent,
                depth: DepthInput::Constant { meters: 1.0 },
            },
            guide: GuideConfiguration {
                push_left: vec![0.0; 28],
                push_right: vec![0.0; 28],
            },
            projection: ProjectionConfiguration {
                push_left,
                push_right,
                scissor_left: vec![0.0; 4],
                scissor_right: vec![0.0; 4],
                rgb_uniform,
                displacement_uniform: vec![0.0; 16],
                zone_uniform,
                displacement_enabled: false,
            },
            outputs: vec![
                OutputLayer {
                    name: "final".to_string(),
                    override_value: 0.0,
                },
                OutputLayer {
                    name: "raw-brightness".to_string(),
                    override_value: 1.0,
                },
            ],
        }
    }

    #[test]
    fn controls_write_documented_projection_zone_slots() {
        let baseline = test_capsule();
        let mut capsule = baseline.clone();
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "raw-brightness", None).expect("state");
        controls.coverage = CoverageMode::Full;
        controls.stretch_source = StretchSource::Mix;
        controls.debug_view = DebugView::Regions;
        controls.edge_inset_uv = 0.03;
        controls.max_inset_uv = 0.2;
        controls.inner_blend_width_uv = 0.08;
        controls.outer_blend_curve = 2.5;
        controls.projection_edge_guard_enabled = false;
        controls
            .apply_to_capsule(&mut capsule, &baseline)
            .expect("apply controls");

        assert_eq!(capsule.outputs[0].name, "raw-brightness");
        assert_eq!(capsule.projection.zone_uniform[24], 2.0);
        assert_eq!(capsule.projection.zone_uniform[25], 2.0);
        assert_eq!(capsule.projection.zone_uniform[26], 1.0);
        assert_eq!(capsule.projection.zone_uniform[28], 0.03);
        assert_eq!(capsule.projection.zone_uniform[29], 0.2);
        assert_eq!(
            capsule.projection.zone_uniform[STRETCH_FLAGS_INDEX],
            DISABLE_PROJECTION_EDGE_GUARD_FLAG as f32
        );
        assert_eq!(capsule.projection.zone_uniform[45], 0.08);
        assert_eq!(capsule.projection.zone_uniform[58], 2.5);
    }

    #[test]
    fn projection_edge_guard_toggle_preserves_other_stretch_flags() {
        let mut baseline = test_capsule();
        baseline.projection.zone_uniform[STRETCH_FLAGS_INDEX] = 1.0;
        let mut capsule = baseline.clone();
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "final", None).expect("state");
        assert!(controls.projection_edge_guard_enabled);

        controls.projection_edge_guard_enabled = false;
        controls
            .apply_to_capsule(&mut capsule, &baseline)
            .expect("apply unguarded controls");
        assert_eq!(capsule.projection.zone_uniform[STRETCH_FLAGS_INDEX], 3.0);

        controls.projection_edge_guard_enabled = true;
        controls
            .apply_to_capsule(&mut capsule, &baseline)
            .expect("restore guarded controls");
        assert_eq!(capsule.projection.zone_uniform[STRETCH_FLAGS_INDEX], 1.0);
    }

    #[test]
    fn projection_and_buffer_scaling_preserve_unclamped_centers() {
        let baseline = test_capsule();
        let mut capsule = baseline.clone();
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "final", None).expect("state");
        controls.projection_scale = 1.2;
        controls.buffer_footprint_scale = 0.8;
        controls
            .apply_to_capsule(&mut capsule, &baseline)
            .expect("apply controls");

        let base_projection_center =
            baseline.projection.push_left[0] + baseline.projection.push_left[2] * 0.5;
        let scaled_projection_center =
            capsule.projection.push_left[0] + capsule.projection.push_left[2] * 0.5;
        let base_buffer_center =
            baseline.projection.zone_uniform[0] + baseline.projection.zone_uniform[2] * 0.5;
        let scaled_buffer_center =
            capsule.projection.zone_uniform[0] + capsule.projection.zone_uniform[2] * 0.5;
        assert!((base_projection_center - scaled_projection_center).abs() < 0.0001);
        assert!((base_buffer_center - scaled_buffer_center).abs() < 0.0001);
        assert!((capsule.projection.push_left[2] - 0.264).abs() < 0.0001);
        assert!((capsule.projection.zone_uniform[2] - 0.272).abs() < 0.0001);
    }

    #[test]
    fn unknown_layer_is_rejected_instead_of_silently_substituted() {
        let baseline = test_capsule();
        assert!(ReplayControlState::from_capsule(&baseline, "missing", None).is_err());
        let mut capsule = baseline.clone();
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "final", None).expect("state");
        controls.layer = "missing".to_string();
        assert!(controls.apply_to_capsule(&mut capsule, &baseline).is_err());
    }

    fn stored_state_for_layer(
        baseline: &ReplayCapsule,
        layer_token: &str,
        override_value: f32,
        preview_layer: Option<&str>,
    ) -> StoredReplayControlState {
        let mut displacement = baseline.projection.displacement_uniform.clone();
        displacement[1] = 1.0;
        displacement[5] = 2.0;
        displacement[6] = 0.18;
        let mut zone = baseline.projection.zone_uniform.clone();
        zone[39] = 0.12;
        zone[51] = 0.12;
        StoredReplayControlState {
            schema: REPLAY_CONTROL_STATE_SCHEMA.to_string(),
            state_id: "stored-state".to_string(),
            revision: 1,
            created_unix_ms: 1,
            replay_layer: ReplayLayerState {
                layer_token: layer_token.to_string(),
                override_value,
            },
            projection: ProjectionControlState {
                scale: 1.0,
                rgb_uniform_f32: baseline.projection.rgb_uniform.clone(),
                displacement_uniform_f32: displacement,
                displacement_enabled: false,
                zone_uniform_f32: zone,
            },
            control_transport: None,
            preview: preview_layer.map(|token| DesktopPreviewProfile {
                layer_token: token.to_string(),
                effect_clock_speed: 1.0,
                preview_target_hz: 90.0,
                preview_mode: "stereo".to_string(),
                preview_eye: "left".to_string(),
                color_effect_phase_offset_turns: 0.0,
                color_effect_rate_hz: 0.0,
                buffer_footprint_scale: 1.0,
            }),
        }
    }

    #[test]
    fn stored_replay_layer_token_disambiguates_duplicate_override_without_preview() {
        let mut baseline = test_capsule();
        baseline.outputs.push(OutputLayer {
            name: "duplicate-override".to_string(),
            override_value: 0.0,
        });
        let profile = stored_state_for_layer(&baseline, "duplicate-override", 0.0, None);
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "final", None).expect("controls");
        controls
            .apply_control_profile(&profile, &baseline)
            .expect("token-selected state");
        assert_eq!(controls.layer, "duplicate-override");
    }

    #[test]
    fn stored_preview_layer_must_agree_with_replay_layer() {
        let baseline = test_capsule();
        let profile = stored_state_for_layer(&baseline, "final", 0.0, Some("raw-brightness"));
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "final", None).expect("controls");
        assert!(controls.apply_control_profile(&profile, &baseline).is_err());
        assert_eq!(controls.layer, "final");
    }

    fn single_phase_transport(rate_hz: f32) -> ControlTransport {
        use crate::control_transport::{
            CapsuleBinding, PhaseControl, Target, TargetMapping, View, CONTROL_TRANSPORT_SCHEMA,
        };
        ControlTransport {
            schema: CONTROL_TRANSPORT_SCHEMA.to_string(),
            transport_id: "v1-migration-test".to_string(),
            capsule: CapsuleBinding {
                schema: crate::capsule::CAPSULE_SCHEMA.to_string(),
                sha256: "a".repeat(64),
            },
            clock: None,
            phase_controls: vec![PhaseControl {
                control_id: "opaque-phase".to_string(),
                label: "Opaque phase".to_string(),
                initial_phase: 0.0,
                default_phase: 0.0,
                minimum_phase: 0.0,
                maximum_phase: 1.0,
                rate_hz,
                targets: vec![TargetMapping {
                    target: Target::ProjectionPush {
                        view: View::Both,
                        index: 1,
                    },
                    scale: 1.0,
                    offset: 0.0,
                }],
            }],
        }
    }

    #[test]
    fn v1_phase_migration_requires_exact_single_descriptor_rate() {
        let baseline = test_capsule();
        let mut profile = stored_state_for_layer(&baseline, "final", 0.0, Some("final"));
        profile.schema = crate::control_profile::REPLAY_CONTROL_STATE_V1_SCHEMA.to_string();
        profile
            .preview
            .as_mut()
            .expect("preview")
            .color_effect_phase_offset_turns = 0.25;
        profile
            .preview
            .as_mut()
            .expect("preview")
            .color_effect_rate_hz = 0.375;

        let mut matching = ReplayControlState::from_capsule(
            &baseline,
            "final",
            Some(single_phase_transport(0.375)),
        )
        .expect("matching controls");
        matching
            .apply_control_profile(&profile, &baseline)
            .expect("exact rate match");
        assert_eq!(matching.phase_values, vec![0.25]);

        let mut differing = ReplayControlState::from_capsule(
            &baseline,
            "final",
            Some(single_phase_transport(f32::from_bits(
                0.375_f32.to_bits() + 1,
            ))),
        )
        .expect("differing controls");
        let error = differing
            .apply_control_profile(&profile, &baseline)
            .expect_err("one-bit rate drift must fail");
        assert!(error
            .to_string()
            .contains("saved phase rate must exactly match"));
    }

    #[test]
    fn control_profile_rejections_are_transactional_and_require_exact_phase_values() {
        use std::collections::BTreeMap;

        let baseline = test_capsule();
        let descriptor = single_phase_transport(0.375);
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "final", Some(descriptor.clone()))
                .expect("controls");
        controls.effect_elapsed_seconds = 3.25;
        controls.rgb_channels[0].strength_uv = 0.031;
        let original = controls.clone();

        let base_profile = || {
            let mut profile = stored_state_for_layer(&baseline, "final", 0.0, Some("final"));
            profile.control_transport = Some(ControlTransportState {
                transport_id: descriptor.transport_id.clone(),
                capsule_sha256: descriptor.capsule.sha256.clone(),
                values: BTreeMap::from([("opaque-phase".to_string(), 0.25)]),
            });
            profile
        };

        let mut missing = base_profile();
        missing
            .control_transport
            .as_mut()
            .expect("transport")
            .values
            .clear();
        assert!(controls.apply_control_profile(&missing, &baseline).is_err());
        assert_eq!(controls, original);

        let mut extra = base_profile();
        extra
            .control_transport
            .as_mut()
            .expect("transport")
            .values
            .insert("extra-phase".to_string(), 0.5);
        assert!(controls.apply_control_profile(&extra, &baseline).is_err());
        assert_eq!(controls, original);

        let mut out_of_range = base_profile();
        out_of_range
            .control_transport
            .as_mut()
            .expect("transport")
            .values
            .insert("opaque-phase".to_string(), 1.5);
        assert!(controls
            .apply_control_profile(&out_of_range, &baseline)
            .is_err());
        assert_eq!(controls, original);

        let mut tampered = base_profile();
        tampered
            .control_transport
            .as_mut()
            .expect("transport")
            .capsule_sha256 = "b".repeat(64);
        assert!(controls
            .apply_control_profile(&tampered, &baseline)
            .is_err());
        assert_eq!(controls, original);

        let mut tampered_transport = base_profile();
        tampered_transport
            .control_transport
            .as_mut()
            .expect("transport")
            .transport_id = "tampered-transport".to_string();
        assert!(controls
            .apply_control_profile(&tampered_transport, &baseline)
            .is_err());
        assert_eq!(controls, original);
    }

    #[test]
    fn no_transport_leaves_provider_phase_destinations_unchanged() {
        let baseline = test_capsule();
        let mut capsule = baseline.clone();
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "final", None).expect("state");
        controls.effect_elapsed_seconds = 4.0;
        controls.rgb_mode = RgbMode::Linked;
        controls.rgb_channels[0] = RgbChannelControl {
            phase_turns: 0.25,
            rate_hz: 0.75,
            strength_uv: 0.02,
            image_scale: 1.25,
            coverage_scale: 0.8,
        };
        controls
            .apply_to_capsule(&mut capsule, &baseline)
            .expect("apply controls");

        assert_eq!(
            capsule.projection.push_left[6],
            baseline.projection.push_left[6]
        );
        assert_eq!(
            capsule.projection.push_right[6],
            baseline.projection.push_right[6]
        );
        assert_eq!(
            capsule.projection.push_left[12],
            baseline.projection.push_left[12]
        );
        assert_eq!(
            capsule.projection.push_right[12],
            baseline.projection.push_right[12]
        );
        assert_eq!(capsule.guide.push_left[8], baseline.guide.push_left[8]);
        assert_eq!(capsule.guide.push_right[8], baseline.guide.push_right[8]);
        assert_eq!(
            capsule.projection.zone_uniform[35],
            baseline.projection.zone_uniform[35]
        );
        assert_eq!(capsule.projection.rgb_uniform[0], 2.0);
        assert_eq!(&capsule.projection.rgb_uniform[4..7], &[0.25; 3]);
        assert_eq!(&capsule.projection.rgb_uniform[8..11], &[0.75; 3]);
        assert_eq!(&capsule.projection.rgb_uniform[12..15], &[0.02; 3]);
        assert_eq!(&capsule.projection.rgb_uniform[16..19], &[1.25; 3]);
        assert_eq!(&capsule.projection.rgb_uniform[20..23], &[0.8; 3]);
    }

    #[test]
    fn independent_rgb_controls_write_all_five_channel_fields() {
        let baseline = test_capsule();
        let mut capsule = baseline.clone();
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "final", None).expect("state");
        controls.rgb_mode = RgbMode::Independent;
        controls.rgb_channels = [
            RgbChannelControl {
                phase_turns: 0.1,
                rate_hz: 0.2,
                strength_uv: 0.01,
                image_scale: 0.8,
                coverage_scale: 0.6,
            },
            RgbChannelControl {
                phase_turns: 0.3,
                rate_hz: 0.4,
                strength_uv: 0.02,
                image_scale: 1.1,
                coverage_scale: 0.7,
            },
            RgbChannelControl {
                phase_turns: 0.5,
                rate_hz: 0.6,
                strength_uv: 0.03,
                image_scale: 1.4,
                coverage_scale: 0.9,
            },
        ];
        controls
            .apply_to_capsule(&mut capsule, &baseline)
            .expect("apply controls");

        assert_eq!(&capsule.projection.rgb_uniform[4..7], &[0.1, 0.3, 0.5]);
        assert_eq!(&capsule.projection.rgb_uniform[8..11], &[0.2, 0.4, 0.6]);
        assert_eq!(&capsule.projection.rgb_uniform[12..15], &[0.01, 0.02, 0.03]);
        assert_eq!(&capsule.projection.rgb_uniform[16..19], &[0.8, 1.1, 1.4]);
        assert_eq!(&capsule.projection.rgb_uniform[20..23], &[0.6, 0.7, 0.9]);
    }

    #[test]
    fn mono_preview_crops_one_eye_without_changing_its_aspect_ratio() {
        let stereo_source = egui::vec2(1600.0, 900.0);
        let (stereo_size, stereo_uv) =
            preview_source_and_uv(stereo_source, PreviewMode::Stereo, PreviewEye::Left);
        assert_eq!(stereo_size, stereo_source);
        assert_eq!(stereo_uv.min, egui::pos2(0.0, 0.0));
        assert_eq!(stereo_uv.max, egui::pos2(1.0, 1.0));

        let (left_size, left_uv) =
            preview_source_and_uv(stereo_source, PreviewMode::Mono, PreviewEye::Left);
        assert_eq!(left_size, egui::vec2(800.0, 900.0));
        assert_eq!(left_uv.min, egui::pos2(0.0, 0.0));
        assert_eq!(left_uv.max, egui::pos2(0.5, 1.0));

        let (right_size, right_uv) =
            preview_source_and_uv(stereo_source, PreviewMode::Mono, PreviewEye::Right);
        assert_eq!(right_size, egui::vec2(800.0, 900.0));
        assert_eq!(right_uv.min, egui::pos2(0.5, 0.0));
        assert_eq!(right_uv.max, egui::pos2(1.0, 1.0));
    }

    #[test]
    fn surface_displacement_presets_drive_the_vertex_path_and_draw_rects() {
        let mut baseline = test_capsule();
        baseline.shaders.displacement_vertex_spirv = Some(PathBuf::from("displacement.spv"));
        let mut capsule = baseline.clone();
        let mut controls =
            ReplayControlState::from_capsule(&baseline, "final", None).expect("state");
        controls.coverage = CoverageMode::Buffer;
        controls.surface_displacement = SurfaceDisplacementPreset::Gentle;
        controls
            .apply_to_capsule(&mut capsule, &baseline)
            .expect("apply gentle controls");

        assert!(capsule.projection.displacement_enabled);
        assert_eq!(capsule.projection.displacement_uniform[0], 1.0);
        assert_eq!(capsule.projection.displacement_uniform[4], 0.06);
        assert_eq!(capsule.projection.displacement_uniform[6], 0.14);
        assert_eq!(
            &capsule.projection.displacement_uniform[8..12],
            &capsule.projection.zone_uniform[0..4]
        );

        controls.surface_displacement = SurfaceDisplacementPreset::Deep;
        controls
            .apply_to_capsule(&mut capsule, &baseline)
            .expect("apply deep controls");
        assert_eq!(capsule.projection.displacement_uniform[4], 0.18);
        assert_eq!(capsule.projection.displacement_uniform[6], 0.18);

        controls.surface_displacement = SurfaceDisplacementPreset::Off;
        controls
            .apply_to_capsule(&mut capsule, &baseline)
            .expect("apply off controls");
        assert!(!capsule.projection.displacement_enabled);
        assert_eq!(capsule.projection.displacement_uniform[0], 0.0);
    }

    #[test]
    fn live_render_slots_are_bounded_and_reused() {
        let root = Path::new("interactive");
        assert_eq!(live_render_dir(root, 1), root.join("live-slot-01"));
        assert_eq!(
            live_render_dir(root, 1 + LIVE_RENDER_SLOT_COUNT),
            root.join("live-slot-01")
        );
    }

    #[test]
    fn effect_clock_can_pause_and_scales_one_shared_elapsed_value() {
        assert_eq!(advance_effect_elapsed(3.0, false, 2.0, 0.5), 3.0);
        assert_eq!(advance_effect_elapsed(3.0, true, 2.0, 0.5), 4.0);
        assert_eq!(advance_effect_elapsed(3.0, true, 9.0, 0.5), 5.0);
    }

    #[test]
    fn preview_cadence_defaults_to_quest_like_ninety_hz_and_is_bounded() {
        assert!((preview_interval(90.0).as_secs_f64() - 1.0 / 90.0).abs() < 0.000_001);
        assert_eq!(preview_interval(1.0), preview_interval(30.0));
        assert_eq!(preview_interval(500.0), preview_interval(120.0));
    }
}
