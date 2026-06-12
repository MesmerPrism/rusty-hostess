//! Hostess-local Makepad preview renderer for staged Optics stimulus profiles.
//!
//! This is a headset visibility bridge, not the final compute renderer. Optics
//! owns the profile schema and layer graph; this widget proves that the staged
//! browser profile can drive a full-viewport stereo Makepad draw path.

use crate::makepad_widgets::*;
use makepad_xr::scene::XrNode;
use rusty_quest_makepad_camera_shell::StimulusProfilePayload;
use serde_json::Value;
use std::sync::atomic::{AtomicUsize, Ordering};

pub(crate) const STIMULUS_STEREO_FIELD_MARKER_PREFIX: &str = "RUSTY_HOSTESS_MAKEPAD_STIMULUS_DRAW";
pub(crate) const STIMULUS_STEREO_FIELD_MARKER_SCHEMA: &str =
    "rusty.hostess.makepad.stimulus_draw.v1";
const STIMULUS_STEREO_FIELD_DRAW_MARKER_LIMIT: usize = 8;
static STIMULUS_STEREO_FIELD_DRAW_MARKERS_EMITTED: AtomicUsize = AtomicUsize::new(0);

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
        })
    }

    pub(crate) fn disabled() -> Self {
        Self::default()
    }

    pub(crate) fn marker_line(&self, phase: &str, time_seconds: f32, panel_bound: bool) -> String {
        format!(
            "{} schema={} phase={} status={} panelBound={} profileId={} profileSchema={} profileSha256={} tuningSha256={} presentationMode={} stereoBinding={} fullscreen=true renderPath=makepad-xr-fragment-preview computeKernel=false targetCycleHz={:.3} spatialFrequency={:.3} geometryMix={:.3} edgeFade={:.3} timeSeconds={:.3}",
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
            self.temporal_frequency_hz,
            self.spatial_frequency,
            self.geometry_mix,
            self.edge_fade,
            time_seconds,
        )
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
    ) -> bool {
        let changed = self.state != state;
        self.state = state;
        self.draw_field.apply_state(&self.state, time_seconds);
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
                    "{} schema={} phase=xr-draw status={} panelBound=true canInstance={} profileId={} profileSha256={} fullscreen=true renderPath=makepad-xr-fragment-preview computeKernel=false",
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
