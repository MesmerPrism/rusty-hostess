use std::{
    collections::BTreeMap,
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
};

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};

use crate::capsule::{validate_surface_feature_uniform, ReplayCapsule};

pub(crate) const LEGACY_CONTROL_PROFILE_SCHEMA: &str =
    "rusty.quest.spatial_camera_panel.control_profile.v1";
pub(crate) const LEGACY_CONTROL_PROFILE_SUFFIX: &str = ".profile.json";
pub(crate) const REPLAY_CONTROL_STATE_SCHEMA: &str =
    "rusty.hostess.projection_replay_control_state.v2";
pub(crate) const REPLAY_CONTROL_STATE_V1_SCHEMA: &str =
    "rusty.hostess.projection_replay_control_state.v1";
pub(crate) const REPLAY_CONTROL_STATE_SUFFIX: &str = ".replay-control-state.json";
const MAX_CONTROL_PROFILE_BYTES: u64 = 64 * 1024;

#[derive(Clone, Debug, PartialEq, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct LegacyControlProfile {
    pub(crate) schema: String,
    pub(crate) profile_id: String,
    pub(crate) revision: u64,
    pub(crate) created_unix_ms: u64,
    pub(crate) quest_controls: QuestControlProfile,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) desktop_preview: Option<DesktopPreviewProfile>,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct QuestControlProfile {
    pub(crate) layer_override: f32,
    pub(crate) projection_scale: f32,
    pub(crate) zone_compositor: ZoneCompositorProfile,
    pub(crate) rgb_channel_transform: RgbTransformProfile,
    pub(crate) projection_surface_displacement: SurfaceDisplacementProfile,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct DesktopPreviewProfile {
    pub(crate) layer_token: String,
    pub(crate) effect_clock_speed: f32,
    pub(crate) preview_target_hz: f32,
    pub(crate) preview_mode: String,
    pub(crate) preview_eye: String,
    pub(crate) color_effect_phase_offset_turns: f32,
    pub(crate) color_effect_rate_hz: f32,
    pub(crate) buffer_footprint_scale: f32,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ZoneCompositorProfile {
    pub(crate) coverage_mode: String,
    pub(crate) stretch_source: String,
    pub(crate) debug_mode: String,
    pub(crate) outer_target_mode: String,
    pub(crate) stretch_mapping: String,
    pub(crate) projection_effect_edge_guard_enabled: bool,
    pub(crate) edge_inset_uv: f32,
    pub(crate) max_inset_uv: f32,
    pub(crate) stretch_curve: f32,
    pub(crate) processed_mix: f32,
    pub(crate) inner: ZoneBandProfile,
    pub(crate) outer: ZoneBandProfile,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ZoneBandProfile {
    pub(crate) signal: String,
    pub(crate) width_uv: f32,
    pub(crate) curve: f32,
    pub(crate) threshold_rgb: [f32; 3],
    pub(crate) softness: f32,
    pub(crate) strength: f32,
    pub(crate) cycle_amplitude: f32,
    pub(crate) cycle_hz: f32,
    pub(crate) motion_gain: f32,
    pub(crate) channel_dynamics: ZoneChannelDynamicsProfile,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ZoneChannelDynamicsProfile {
    pub(crate) application_mode: String,
    pub(crate) source_choice: String,
    pub(crate) region_driver: String,
    pub(crate) strength_rgb: [f32; 3],
    pub(crate) cycle_amplitude_rgb: [f32; 3],
    pub(crate) cycle_hz_rgb: [f32; 3],
    pub(crate) cycle_phase_turns_rgb: [f32; 3],
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RgbTransformProfile {
    pub(crate) mode: String,
    pub(crate) edge_mode: String,
    pub(crate) red: RgbChannelProfile,
    pub(crate) green: RgbChannelProfile,
    pub(crate) blue: RgbChannelProfile,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RgbChannelProfile {
    pub(crate) direction_turns: f32,
    pub(crate) direction_rate_hz: f32,
    pub(crate) displacement_strength_uv: f32,
    pub(crate) image_scale: f32,
    pub(crate) coverage_scale: f32,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct SurfaceDisplacementProfile {
    pub(crate) enabled: bool,
    pub(crate) max_displacement_meters: f32,
    pub(crate) reference_surface_distance_meters: f32,
    pub(crate) polarity: f32,
    pub(crate) edge_taper: f32,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ReplayControlState {
    pub(crate) schema: String,
    pub(crate) state_id: String,
    pub(crate) revision: u64,
    pub(crate) created_unix_ms: u64,
    pub(crate) replay_layer: ReplayLayerState,
    pub(crate) projection: ProjectionControlState,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) control_transport: Option<ControlTransportState>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) preview: Option<DesktopPreviewProfile>,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ControlTransportState {
    pub(crate) transport_id: String,
    pub(crate) capsule_sha256: String,
    pub(crate) values: BTreeMap<String, f32>,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ReplayLayerState {
    pub(crate) layer_token: String,
    pub(crate) override_value: f32,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ProjectionControlState {
    pub(crate) scale: f32,
    pub(crate) rgb_uniform_f32: Vec<f32>,
    pub(crate) displacement_uniform_f32: Vec<f32>,
    pub(crate) displacement_enabled: bool,
    pub(crate) zone_uniform_f32: Vec<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) surface_feature_uniform_f32: Option<Vec<f32>>,
}

impl LegacyControlProfile {
    pub(crate) fn validate(&self) -> Result<()> {
        if self.schema != LEGACY_CONTROL_PROFILE_SCHEMA {
            bail!(
                "unsupported profile schema {}; expected {}",
                self.schema,
                LEGACY_CONTROL_PROFILE_SCHEMA
            );
        }
        validate_profile_id(&self.profile_id)?;
        finite_range(
            "quest_controls.layer_override",
            self.quest_controls.layer_override,
            -1.0,
            8.0,
        )?;
        finite_range(
            "quest_controls.projection_scale",
            self.quest_controls.projection_scale,
            0.25,
            1.8,
        )?;
        self.quest_controls.zone_compositor.validate()?;
        self.quest_controls.rgb_channel_transform.validate()?;
        self.quest_controls
            .projection_surface_displacement
            .validate()?;
        if let Some(desktop) = &self.desktop_preview {
            if desktop.layer_token.trim().is_empty() || desktop.layer_token.len() > 128 {
                bail!("desktop_preview.layer_token must contain 1..128 characters");
            }
            finite_range(
                "desktop_preview.effect_clock_speed",
                desktop.effect_clock_speed,
                0.05,
                4.0,
            )?;
            finite_range(
                "desktop_preview.preview_target_hz",
                desktop.preview_target_hz,
                30.0,
                120.0,
            )?;
            finite_range(
                "desktop_preview.color_effect_phase_offset_turns",
                desktop.color_effect_phase_offset_turns,
                0.0,
                1.0,
            )?;
            finite_range(
                "desktop_preview.color_effect_rate_hz",
                desktop.color_effect_rate_hz,
                -2.0,
                2.0,
            )?;
            finite_range(
                "desktop_preview.buffer_footprint_scale",
                desktop.buffer_footprint_scale,
                0.5,
                1.5,
            )?;
            token(
                "desktop_preview.preview_mode",
                &desktop.preview_mode,
                &["stereo", "mono"],
            )?;
            token(
                "desktop_preview.preview_eye",
                &desktop.preview_eye,
                &["left", "right"],
            )?;
        }
        Ok(())
    }
}

impl ReplayControlState {
    pub(crate) fn write(&self, directory: &Path) -> Result<PathBuf> {
        self.validate()?;
        fs::create_dir_all(directory)
            .with_context(|| format!("failed to create {}", directory.display()))?;
        let path = directory.join(format!(
            "{}{}",
            profile_file_stem(&self.state_id),
            REPLAY_CONTROL_STATE_SUFFIX
        ));
        let bytes = serde_json::to_vec_pretty(self)?;
        if bytes.len() as u64 > MAX_CONTROL_PROFILE_BYTES {
            bail!("generated control state exceeds the 64 KiB limit");
        }
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)
            .with_context(|| format!("refusing to overwrite control state {}", path.display()))?;
        if let Err(error) = file.write_all(&bytes).and_then(|_| file.sync_all()) {
            drop(file);
            let _ = fs::remove_file(&path);
            return Err(error)
                .with_context(|| format!("failed to write control state {}", path.display()));
        }
        Ok(path)
    }

    pub(crate) fn validate(&self) -> Result<()> {
        if self.schema != REPLAY_CONTROL_STATE_SCHEMA
            && self.schema != REPLAY_CONTROL_STATE_V1_SCHEMA
        {
            bail!(
                "unsupported control state schema {}; expected {}",
                self.schema,
                REPLAY_CONTROL_STATE_SCHEMA
            );
        }
        if self.schema == REPLAY_CONTROL_STATE_SCHEMA {
            if let Some(transport) = &self.control_transport {
                validate_profile_id(&transport.transport_id)?;
                if transport.capsule_sha256.len() != 64
                    || !transport
                        .capsule_sha256
                        .bytes()
                        .all(|byte| byte.is_ascii_hexdigit())
                {
                    bail!("control_transport.capsule_sha256 must be 64 hexadecimal characters");
                }
                for (key, value) in &transport.values {
                    validate_profile_id(key)?;
                    if !value.is_finite() {
                        bail!("control transport value must be finite");
                    }
                }
            }
        } else if self.control_transport.is_some()
            || self.projection.surface_feature_uniform_f32.is_some()
        {
            bail!(
                "v1 control state must not contain v2 control_transport or surface feature values"
            );
        }
        validate_profile_id(&self.state_id)?;
        if self.replay_layer.layer_token.trim().is_empty()
            || self.replay_layer.layer_token.len() > 128
        {
            bail!("replay_layer.layer_token must contain 1..128 characters");
        }
        finite_range(
            "replay_layer.override_value",
            self.replay_layer.override_value,
            -1.0,
            8.0,
        )?;
        finite_range("projection.scale", self.projection.scale, 0.25, 1.8)?;
        exact_finite_block(
            "projection.rgb_uniform_f32",
            &self.projection.rgb_uniform_f32,
            24,
        )?;
        exact_finite_block(
            "projection.displacement_uniform_f32",
            &self.projection.displacement_uniform_f32,
            16,
        )?;
        exact_finite_block(
            "projection.zone_uniform_f32",
            &self.projection.zone_uniform_f32,
            92,
        )?;
        if let Some(surface) = &self.projection.surface_feature_uniform_f32 {
            validate_surface_feature_uniform(surface, &self.projection.displacement_uniform_f32)?;
        }
        // Reuse the bounds already enforced by the Hostess editor without assigning
        // provider semantics to the opaque ABI blocks.
        RgbTransformProfile::from_uniform(&self.projection.rgb_uniform_f32)?.validate()?;
        ZoneCompositorProfile::from_uniform(&self.projection.zone_uniform_f32)?.validate()?;
        let displacement = SurfaceDisplacementProfile {
            enabled: self.projection.displacement_enabled
                && self.projection.displacement_uniform_f32[0] >= 0.5,
            max_displacement_meters: self.projection.displacement_uniform_f32[4],
            reference_surface_distance_meters: self.projection.displacement_uniform_f32[5],
            polarity: self.projection.displacement_uniform_f32[1],
            edge_taper: self.projection.displacement_uniform_f32[6],
        };
        displacement.validate()?;
        if let Some(preview) = &self.preview {
            validate_desktop_preview(preview)?;
        }
        Ok(())
    }

    pub(crate) fn import_legacy(
        legacy: &LegacyControlProfile,
        baseline: &ReplayCapsule,
    ) -> Result<Self> {
        legacy.validate()?;
        let mut rgb = baseline.projection.rgb_uniform.clone();
        legacy
            .quest_controls
            .rgb_channel_transform
            .apply_to_uniform(&mut rgb)?;
        let mut zone = baseline.projection.zone_uniform.clone();
        legacy
            .quest_controls
            .zone_compositor
            .apply_to_uniform(&mut zone)?;
        let mut displacement = baseline.projection.displacement_uniform.clone();
        legacy
            .quest_controls
            .projection_surface_displacement
            .apply_to_uniform(&mut displacement)?;
        let layer_token = legacy
            .desktop_preview
            .as_ref()
            .map(|preview| preview.layer_token.clone())
            .or_else(|| {
                baseline
                    .outputs
                    .iter()
                    .find(|output| {
                        (output.override_value - legacy.quest_controls.layer_override).abs() < 0.001
                    })
                    .map(|output| output.name.clone())
            })
            .context("legacy layer override is not available in this replay capsule")?;
        let state = Self {
            schema: REPLAY_CONTROL_STATE_SCHEMA.to_string(),
            state_id: legacy.profile_id.clone(),
            revision: legacy.revision,
            created_unix_ms: legacy.created_unix_ms,
            replay_layer: ReplayLayerState {
                layer_token,
                override_value: legacy.quest_controls.layer_override,
            },
            projection: ProjectionControlState {
                scale: legacy.quest_controls.projection_scale,
                rgb_uniform_f32: rgb,
                displacement_uniform_f32: displacement,
                displacement_enabled: legacy
                    .quest_controls
                    .projection_surface_displacement
                    .enabled,
                zone_uniform_f32: zone,
                surface_feature_uniform_f32: None,
            },
            control_transport: None,
            preview: legacy.desktop_preview.clone(),
        };
        state.validate()?;
        Ok(state)
    }
}

pub(crate) fn read_stored_control(
    path: &Path,
    baseline: &ReplayCapsule,
) -> Result<ReplayControlState> {
    read_stored_control_with(path, baseline, |selected| fs::read(selected))
}

fn read_stored_control_with<F>(
    path: &Path,
    baseline: &ReplayCapsule,
    reader: F,
) -> Result<ReplayControlState>
where
    F: FnOnce(&Path) -> std::io::Result<Vec<u8>>,
{
    let bytes = read_bounded_control_bytes(path, reader)?;
    let value = parse_control_json(&bytes)?;
    let schema = value
        .get("schema")
        .and_then(serde_json::Value::as_str)
        .context("stored control schema must be a string")?;
    match schema {
        REPLAY_CONTROL_STATE_SCHEMA | REPLAY_CONTROL_STATE_V1_SCHEMA => {
            let state: ReplayControlState = serde_json::from_value(value)
                .context("stored replay control state does not match its schema")?;
            state.validate()?;
            Ok(state)
        }
        LEGACY_CONTROL_PROFILE_SCHEMA => {
            let legacy: LegacyControlProfile = serde_json::from_value(value)
                .context("legacy Quest profile does not match its schema")?;
            legacy.validate()?;
            ReplayControlState::import_legacy(&legacy, baseline)
        }
        _ => bail!("unsupported stored control schema {schema}"),
    }
}

fn read_bounded_control_bytes<F>(path: &Path, reader: F) -> Result<Vec<u8>>
where
    F: FnOnce(&Path) -> std::io::Result<Vec<u8>>,
{
    let metadata = fs::metadata(path)
        .with_context(|| format!("stored control file does not exist: {}", path.display()))?;
    if metadata.len() > MAX_CONTROL_PROFILE_BYTES {
        bail!("stored control file exceeds the 64 KiB limit");
    }
    let bytes = reader(path).with_context(|| format!("failed to read {}", path.display()))?;
    if bytes.len() as u64 > MAX_CONTROL_PROFILE_BYTES {
        bail!("stored control file exceeds the 64 KiB limit after read");
    }
    Ok(bytes)
}

fn parse_control_json(bytes: &[u8]) -> Result<serde_json::Value> {
    let text = std::str::from_utf8(bytes).context("stored control file is not strict UTF-8")?;
    serde_json::from_str(text).context("stored control file is not valid JSON")
}

impl ZoneCompositorProfile {
    fn validate(&self) -> Result<()> {
        token(
            "zone_compositor.coverage_mode",
            &self.coverage_mode,
            &["off", "buffer", "full"],
        )?;
        token(
            "zone_compositor.stretch_source",
            &self.stretch_source,
            &["raw", "processed", "mix"],
        )?;
        token(
            "zone_compositor.debug_mode",
            &self.debug_mode,
            &["normal", "regions", "sample-uv"],
        )?;
        token(
            "zone_compositor.outer_target_mode",
            &self.outer_target_mode,
            &["readable-color", "transparent-spatial-video"],
        )?;
        token(
            "zone_compositor.stretch_mapping",
            &self.stretch_mapping,
            &["graded-edge-trail-native"],
        )?;
        finite_range(
            "zone_compositor.edge_inset_uv",
            self.edge_inset_uv,
            0.0,
            0.49,
        )?;
        finite_range(
            "zone_compositor.max_inset_uv",
            self.max_inset_uv,
            self.edge_inset_uv,
            0.49,
        )?;
        finite_range(
            "zone_compositor.stretch_curve",
            self.stretch_curve,
            0.25,
            6.0,
        )?;
        finite_range(
            "zone_compositor.processed_mix",
            self.processed_mix,
            0.0,
            1.0,
        )?;
        self.inner.validate("zone_compositor.inner")?;
        self.outer.validate("zone_compositor.outer")
    }

    pub(crate) fn from_uniform(zone: &[f32]) -> Result<Self> {
        if zone.len() != 92 {
            bail!("projection zone uniform must contain exactly 92 floats");
        }
        Ok(Self {
            coverage_mode: coverage_token(zone[24])?.to_string(),
            stretch_source: stretch_source_token(zone[25])?.to_string(),
            debug_mode: debug_token(zone[26])?.to_string(),
            outer_target_mode: outer_target_token(zone[59])?.to_string(),
            stretch_mapping: "graded-edge-trail-native".to_string(),
            projection_effect_edge_guard_enabled: !float_flag(zone[31], 1 << 1),
            edge_inset_uv: zone[28],
            max_inset_uv: zone[29],
            stretch_curve: zone[30],
            processed_mix: zone[27],
            inner: ZoneBandProfile::from_uniform(zone, true)?,
            outer: ZoneBandProfile::from_uniform(zone, false)?,
        })
    }

    pub(crate) fn apply_to_uniform(&self, zone: &mut [f32]) -> Result<()> {
        self.validate()?;
        if zone.len() != 92 {
            bail!("projection zone uniform must contain exactly 92 floats");
        }
        zone[24] = coverage_value(&self.coverage_mode);
        zone[25] = stretch_source_value(&self.stretch_source);
        zone[26] = debug_value(&self.debug_mode);
        zone[27] = self.processed_mix;
        zone[28] = self.edge_inset_uv;
        zone[29] = self.max_inset_uv;
        zone[30] = self.stretch_curve;
        zone[31] = set_float_flag(zone[31], 1 << 1, !self.projection_effect_edge_guard_enabled);
        self.inner.apply_to_uniform(zone, true);
        self.outer.apply_to_uniform(zone, false);
        zone[59] = outer_target_value(&self.outer_target_mode);
        Ok(())
    }
}

impl ZoneBandProfile {
    fn validate(&self, label: &str) -> Result<()> {
        token(
            &format!("{label}.signal"),
            &self.signal,
            &["flat", "rgb", "luma", "chroma", "difference"],
        )?;
        finite_range(&format!("{label}.width_uv"), self.width_uv, 0.0, 0.25)?;
        finite_range(&format!("{label}.curve"), self.curve, 0.25, 6.0)?;
        vector_range(
            &format!("{label}.threshold_rgb"),
            self.threshold_rgb,
            0.0,
            1.0,
        )?;
        finite_range(&format!("{label}.softness"), self.softness, 0.001, 0.5)?;
        finite_range(&format!("{label}.strength"), self.strength, 0.0, 1.0)?;
        finite_range(
            &format!("{label}.cycle_amplitude"),
            self.cycle_amplitude,
            0.0,
            0.5,
        )?;
        finite_range(&format!("{label}.cycle_hz"), self.cycle_hz, 0.0, 4.0)?;
        finite_range(&format!("{label}.motion_gain"), self.motion_gain, -0.5, 0.5)?;
        self.channel_dynamics
            .validate(&format!("{label}.channel_dynamics"))
    }

    fn from_uniform(zone: &[f32], inner: bool) -> Result<Self> {
        let (threshold, dynamics, shape, strength, amplitude, hz, phase) = if inner {
            (36, 40, 44, 60, 64, 68, 72)
        } else {
            (48, 52, 56, 76, 80, 84, 88)
        };
        Ok(Self {
            signal: signal_token(zone[shape])?.to_string(),
            width_uv: zone[shape + 1],
            curve: zone[shape + 2],
            threshold_rgb: [zone[threshold], zone[threshold + 1], zone[threshold + 2]],
            softness: zone[threshold + 3],
            strength: zone[dynamics],
            cycle_amplitude: zone[dynamics + 1],
            cycle_hz: zone[dynamics + 2],
            motion_gain: zone[dynamics + 3],
            channel_dynamics: ZoneChannelDynamicsProfile {
                application_mode: application_token(zone[strength + 3])?.to_string(),
                source_choice: source_choice_token(zone[amplitude + 3])?.to_string(),
                region_driver: region_driver_token(zone[hz + 3])?.to_string(),
                strength_rgb: [zone[strength], zone[strength + 1], zone[strength + 2]],
                cycle_amplitude_rgb: [zone[amplitude], zone[amplitude + 1], zone[amplitude + 2]],
                cycle_hz_rgb: [zone[hz], zone[hz + 1], zone[hz + 2]],
                cycle_phase_turns_rgb: [zone[phase], zone[phase + 1], zone[phase + 2]],
            },
        })
    }

    fn apply_to_uniform(&self, zone: &mut [f32], inner: bool) {
        let (threshold, dynamics, shape, strength, amplitude, hz, phase) = if inner {
            (36, 40, 44, 60, 64, 68, 72)
        } else {
            (48, 52, 56, 76, 80, 84, 88)
        };
        zone[shape] = signal_value(&self.signal);
        zone[shape + 1] = self.width_uv;
        zone[shape + 2] = self.curve;
        zone[threshold..threshold + 3].copy_from_slice(&self.threshold_rgb);
        zone[threshold + 3] = self.softness;
        zone[dynamics] = self.strength;
        zone[dynamics + 1] = self.cycle_amplitude;
        zone[dynamics + 2] = self.cycle_hz;
        zone[dynamics + 3] = self.motion_gain;
        zone[strength..strength + 3].copy_from_slice(&self.channel_dynamics.strength_rgb);
        zone[strength + 3] = application_value(&self.channel_dynamics.application_mode);
        zone[amplitude..amplitude + 3].copy_from_slice(&self.channel_dynamics.cycle_amplitude_rgb);
        zone[amplitude + 3] = source_choice_value(&self.channel_dynamics.source_choice);
        zone[hz..hz + 3].copy_from_slice(&self.channel_dynamics.cycle_hz_rgb);
        zone[hz + 3] = region_driver_value(&self.channel_dynamics.region_driver);
        zone[phase..phase + 3].copy_from_slice(&self.channel_dynamics.cycle_phase_turns_rgb);
        zone[phase + 3] = 1.0;
    }
}

impl ZoneChannelDynamicsProfile {
    fn validate(&self, label: &str) -> Result<()> {
        token(
            &format!("{label}.application_mode"),
            &self.application_mode,
            &["legacy", "component", "region"],
        )?;
        token(
            &format!("{label}.source_choice"),
            &self.source_choice,
            &["outgoing", "midpoint", "incoming"],
        )?;
        token(
            &format!("{label}.region_driver"),
            &self.region_driver,
            &["red", "green", "blue", "luma", "max"],
        )?;
        vector_range(
            &format!("{label}.strength_rgb"),
            self.strength_rgb,
            0.0,
            1.0,
        )?;
        vector_range(
            &format!("{label}.cycle_amplitude_rgb"),
            self.cycle_amplitude_rgb,
            0.0,
            0.5,
        )?;
        vector_range(
            &format!("{label}.cycle_hz_rgb"),
            self.cycle_hz_rgb,
            0.0,
            4.0,
        )?;
        vector_range(
            &format!("{label}.cycle_phase_turns_rgb"),
            self.cycle_phase_turns_rgb,
            -4.0,
            4.0,
        )
    }
}

impl RgbTransformProfile {
    fn validate(&self) -> Result<()> {
        token(
            "rgb_channel_transform.mode",
            &self.mode,
            &["off", "independent", "linked"],
        )?;
        token(
            "rgb_channel_transform.edge_mode",
            &self.edge_mode,
            &["clamp", "mirror", "fade"],
        )?;
        self.red.validate("rgb_channel_transform.red")?;
        self.green.validate("rgb_channel_transform.green")?;
        self.blue.validate("rgb_channel_transform.blue")
    }

    pub(crate) fn from_uniform(rgb: &[f32]) -> Result<Self> {
        if rgb.len() != 24 {
            bail!("RGB uniform must contain exactly 24 floats");
        }
        Ok(Self {
            mode: rgb_mode_token(rgb[0])?.to_string(),
            edge_mode: rgb_edge_token(rgb[1])?.to_string(),
            red: RgbChannelProfile::from_uniform(rgb, 0),
            green: RgbChannelProfile::from_uniform(rgb, 1),
            blue: RgbChannelProfile::from_uniform(rgb, 2),
        })
    }

    pub(crate) fn apply_to_uniform(&self, rgb: &mut [f32]) -> Result<()> {
        self.validate()?;
        if rgb.len() != 24 {
            bail!("RGB uniform must contain exactly 24 floats");
        }
        rgb[0] = rgb_mode_value(&self.mode);
        rgb[1] = rgb_edge_value(&self.edge_mode);
        for (channel, value) in [&self.red, &self.green, &self.blue].into_iter().enumerate() {
            rgb[4 + channel] = value.direction_turns;
            rgb[8 + channel] = value.direction_rate_hz;
            rgb[12 + channel] = value.displacement_strength_uv;
            rgb[16 + channel] = value.image_scale;
            rgb[20 + channel] = value.coverage_scale;
        }
        Ok(())
    }
}

impl RgbChannelProfile {
    fn validate(&self, label: &str) -> Result<()> {
        finite_range(
            &format!("{label}.direction_turns"),
            self.direction_turns,
            0.0,
            1.0,
        )?;
        finite_range(
            &format!("{label}.direction_rate_hz"),
            self.direction_rate_hz,
            -2.0,
            2.0,
        )?;
        finite_range(
            &format!("{label}.displacement_strength_uv"),
            self.displacement_strength_uv,
            0.0,
            0.08,
        )?;
        finite_range(&format!("{label}.image_scale"), self.image_scale, 0.5, 2.0)?;
        finite_range(
            &format!("{label}.coverage_scale"),
            self.coverage_scale,
            0.5,
            1.0,
        )
    }

    fn from_uniform(rgb: &[f32], channel: usize) -> Self {
        Self {
            direction_turns: rgb[4 + channel].rem_euclid(1.0),
            direction_rate_hz: rgb[8 + channel],
            displacement_strength_uv: rgb[12 + channel],
            image_scale: rgb[16 + channel],
            coverage_scale: rgb[20 + channel],
        }
    }
}

impl SurfaceDisplacementProfile {
    fn validate(&self) -> Result<()> {
        finite_range(
            "projection_surface_displacement.max_displacement_meters",
            self.max_displacement_meters,
            0.0,
            0.35,
        )?;
        finite_range(
            "projection_surface_displacement.reference_surface_distance_meters",
            self.reference_surface_distance_meters,
            1.0,
            4.0,
        )?;
        finite_range(
            "projection_surface_displacement.polarity",
            self.polarity,
            -1.0,
            1.0,
        )?;
        finite_range(
            "projection_surface_displacement.edge_taper",
            self.edge_taper,
            0.02,
            0.45,
        )
    }

    pub(crate) fn from_capsule(capsule: &ReplayCapsule) -> Result<Self> {
        let uniform = &capsule.projection.displacement_uniform;
        if uniform.len() != 16 {
            bail!("surface-displacement uniform must contain exactly 16 floats");
        }
        Ok(Self {
            enabled: capsule.projection.displacement_enabled && uniform[0] >= 0.5,
            max_displacement_meters: uniform[4],
            reference_surface_distance_meters: uniform[5],
            polarity: if uniform[1].abs() < 0.001 {
                1.0
            } else {
                uniform[1]
            },
            edge_taper: uniform[6],
        })
    }

    pub(crate) fn apply_to_uniform(&self, uniform: &mut [f32]) -> Result<()> {
        self.validate()?;
        if uniform.len() != 16 {
            bail!("surface-displacement uniform must contain exactly 16 floats");
        }
        uniform[0] = if self.enabled { 1.0 } else { 0.0 };
        uniform[1] = self.polarity;
        uniform[4] = self.max_displacement_meters;
        uniform[5] = self.reference_surface_distance_meters;
        uniform[6] = self.edge_taper;
        Ok(())
    }
}

pub(crate) fn profile_files(directory: &Path) -> Result<Vec<PathBuf>> {
    if !directory.exists() {
        return Ok(Vec::new());
    }
    let mut files = fs::read_dir(directory)
        .with_context(|| format!("failed to list {}", directory.display()))?
        .filter_map(|entry| entry.ok().map(|entry| entry.path()))
        .filter(|path| {
            path.is_file()
                && path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| {
                        name.ends_with(REPLAY_CONTROL_STATE_SUFFIX)
                            || name.ends_with(LEGACY_CONTROL_PROFILE_SUFFIX)
                    })
        })
        .collect::<Vec<_>>();
    files.sort();
    Ok(files)
}

fn exact_finite_block(label: &str, values: &[f32], expected: usize) -> Result<()> {
    if values.len() != expected {
        bail!("{label} must contain exactly {expected} floats");
    }
    if let Some(index) = values.iter().position(|value| !value.is_finite()) {
        bail!("{label}[{index}] must be finite");
    }
    Ok(())
}

fn validate_desktop_preview(desktop: &DesktopPreviewProfile) -> Result<()> {
    if desktop.layer_token.trim().is_empty() || desktop.layer_token.len() > 128 {
        bail!("preview.layer_token must contain 1..128 characters");
    }
    finite_range(
        "preview.effect_clock_speed",
        desktop.effect_clock_speed,
        0.05,
        4.0,
    )?;
    finite_range(
        "preview.preview_target_hz",
        desktop.preview_target_hz,
        30.0,
        120.0,
    )?;
    finite_range(
        "preview.color_effect_phase_offset_turns",
        desktop.color_effect_phase_offset_turns,
        0.0,
        1.0,
    )?;
    finite_range(
        "preview.color_effect_rate_hz",
        desktop.color_effect_rate_hz,
        -2.0,
        2.0,
    )?;
    finite_range(
        "preview.buffer_footprint_scale",
        desktop.buffer_footprint_scale,
        0.5,
        1.5,
    )?;
    token(
        "preview.preview_mode",
        &desktop.preview_mode,
        &["stereo", "mono"],
    )?;
    token(
        "preview.preview_eye",
        &desktop.preview_eye,
        &["left", "right"],
    )
}

pub(crate) fn profile_file_stem(profile_id: &str) -> String {
    let stem = profile_id
        .trim()
        .to_ascii_lowercase()
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || matches!(character, '-' | '_' | '.') {
                character
            } else {
                '-'
            }
        })
        .collect::<String>();
    stem.trim_matches(['-', '_', '.']).to_string()
}

fn validate_profile_id(profile_id: &str) -> Result<()> {
    let stem = profile_file_stem(profile_id);
    if stem.len() < 2 || stem.len() > 64 || stem != profile_id {
        bail!(
            "profile_id must be a normalized 2..64 character lowercase id using letters, digits, '.', '_' or '-'"
        );
    }
    Ok(())
}

fn finite_range(label: &str, value: f32, minimum: f32, maximum: f32) -> Result<()> {
    if !value.is_finite() || value < minimum || value > maximum {
        bail!("{label}={value} is outside {minimum}..{maximum}");
    }
    Ok(())
}

fn vector_range(label: &str, values: [f32; 3], minimum: f32, maximum: f32) -> Result<()> {
    for (index, value) in values.into_iter().enumerate() {
        finite_range(&format!("{label}[{index}]"), value, minimum, maximum)?;
    }
    Ok(())
}

fn token(label: &str, value: &str, allowed: &[&str]) -> Result<()> {
    if !allowed.contains(&value) {
        bail!("{label} has unsupported token {value}");
    }
    Ok(())
}

fn exact_token<'a>(label: &str, value: f32, tokens: &'a [&'a str]) -> Result<&'a str> {
    if !value.is_finite() || value.fract() != 0.0 || value < 0.0 || value >= tokens.len() as f32 {
        bail!(
            "{label} must be an exact finite token in 0..{}",
            tokens.len() - 1
        );
    }
    Ok(tokens[value as usize])
}

fn coverage_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection.zone_uniform_f32[24]",
        value,
        &["off", "buffer", "full"],
    )
}

fn coverage_value(value: &str) -> f32 {
    match value {
        "buffer" => 1.0,
        "full" => 2.0,
        _ => 0.0,
    }
}

fn stretch_source_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection.zone_uniform_f32[25]",
        value,
        &["raw", "processed", "mix"],
    )
}

fn stretch_source_value(value: &str) -> f32 {
    match value {
        "processed" => 1.0,
        "mix" => 2.0,
        _ => 0.0,
    }
}

fn debug_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection.zone_uniform_f32[26]",
        value,
        &["normal", "regions", "sample-uv"],
    )
}

fn debug_value(value: &str) -> f32 {
    match value {
        "regions" => 1.0,
        "sample-uv" => 2.0,
        _ => 0.0,
    }
}

fn outer_target_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection.zone_uniform_f32[59]",
        value,
        &["readable-color", "transparent-spatial-video"],
    )
}

fn outer_target_value(value: &str) -> f32 {
    if value == "transparent-spatial-video" {
        1.0
    } else {
        0.0
    }
}

fn signal_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection zone signal token",
        value,
        &["flat", "rgb", "luma", "chroma", "difference"],
    )
}

fn signal_value(value: &str) -> f32 {
    match value {
        "rgb" => 1.0,
        "luma" => 2.0,
        "chroma" => 3.0,
        "difference" => 4.0,
        _ => 0.0,
    }
}

fn application_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection zone application token",
        value,
        &["legacy", "component", "region"],
    )
}

fn application_value(value: &str) -> f32 {
    match value {
        "component" => 1.0,
        "region" => 2.0,
        _ => 0.0,
    }
}

fn source_choice_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection zone source token",
        value,
        &["outgoing", "midpoint", "incoming"],
    )
}

fn source_choice_value(value: &str) -> f32 {
    match value {
        "outgoing" => 0.0,
        "incoming" => 2.0,
        _ => 1.0,
    }
}

fn region_driver_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection zone region token",
        value,
        &["red", "green", "blue", "luma", "max"],
    )
}

fn region_driver_value(value: &str) -> f32 {
    match value {
        "red" => 0.0,
        "green" => 1.0,
        "blue" => 2.0,
        "max" => 4.0,
        _ => 3.0,
    }
}

fn rgb_mode_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection.rgb_uniform_f32[0]",
        value,
        &["off", "independent", "linked"],
    )
}

fn rgb_mode_value(value: &str) -> f32 {
    match value {
        "independent" => 1.0,
        "linked" => 2.0,
        _ => 0.0,
    }
}

fn rgb_edge_token(value: f32) -> Result<&'static str> {
    exact_token(
        "projection.rgb_uniform_f32[1]",
        value,
        &["clamp", "mirror", "fade"],
    )
}

fn rgb_edge_value(value: &str) -> f32 {
    match value {
        "mirror" => 1.0,
        "fade" => 2.0,
        _ => 0.0,
    }
}

fn float_flag(value: f32, flag: u32) -> bool {
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capsule::{
        ColorInput, DepthInput, Extent, GuideConfiguration, ProjectionConfiguration, ReplayInputs,
        ShaderBundle,
    };

    fn capsule() -> ReplayCapsule {
        let mut zone = vec![0.0; 92];
        zone[24] = 1.0;
        zone[25] = 1.0;
        zone[27] = 0.7;
        zone[28] = 0.015;
        zone[29] = 0.14;
        zone[30] = 1.6;
        zone[31] = 2.0;
        zone[36..39].copy_from_slice(&[0.2, 0.4, 0.6]);
        zone[39] = 0.12;
        zone[44] = 1.0;
        zone[45] = 0.08;
        zone[46] = 2.0;
        zone[48..51].copy_from_slice(&[0.3, 0.5, 0.7]);
        zone[51] = 0.11;
        zone[56] = 2.0;
        zone[57] = 0.09;
        zone[58] = 1.8;
        zone[60..63].copy_from_slice(&[0.1, 0.2, 0.3]);
        zone[63] = 2.0;
        zone[64..67].copy_from_slice(&[0.01, 0.02, 0.03]);
        zone[67] = 0.0;
        zone[68..71].copy_from_slice(&[0.1, 0.2, 0.3]);
        zone[71] = 3.0;
        zone[72..75].copy_from_slice(&[0.0, 0.33, 0.66]);
        zone[75] = 1.0;
        zone[76..79].copy_from_slice(&[0.3, 0.2, 0.1]);
        zone[79] = 1.0;
        zone[80..83].copy_from_slice(&[0.03, 0.02, 0.01]);
        zone[83] = 2.0;
        zone[84..87].copy_from_slice(&[0.3, 0.2, 0.1]);
        zone[87] = 4.0;
        zone[88..91].copy_from_slice(&[0.66, 0.33, 0.0]);
        zone[91] = 1.0;

        let mut rgb = vec![0.0; 24];
        rgb[0] = 1.0;
        rgb[1] = 1.0;
        rgb[4..7].copy_from_slice(&[0.0, 0.33, 0.66]);
        rgb[8..11].copy_from_slice(&[0.11, 0.17, -0.13]);
        rgb[12..15].copy_from_slice(&[0.018, 0.014, 0.022]);
        rgb[16..19].copy_from_slice(&[1.0, 1.05, 0.95]);
        rgb[20..23].copy_from_slice(&[1.0, 0.92, 0.84]);

        let mut displacement = vec![0.0; 16];
        displacement[0] = 1.0;
        displacement[1] = 1.0;
        displacement[4] = 0.06;
        displacement[5] = 2.0;
        displacement[6] = 0.14;

        ReplayCapsule {
            schema: crate::capsule::CAPSULE_SCHEMA.to_string(),
            name: "profile-test".to_string(),
            extent: Extent {
                width: 64,
                height: 32,
            },
            shaders: ShaderBundle {
                fullscreen_vertex_spirv: PathBuf::from("fullscreen.spv"),
                guide_fragment_spirv: vec![PathBuf::from("guide.spv"); 6],
                projection_fragment_spirv: PathBuf::from("projection.spv"),
                displacement_vertex_spirv: Some(PathBuf::from("displacement.spv")),
            },
            inputs: ReplayInputs {
                camera_left: ColorInput::Transparent,
                camera_right: ColorInput::Transparent,
                video: ColorInput::Transparent,
                depth: DepthInput::Constant { meters: 2.0 },
            },
            guide: GuideConfiguration {
                push_left: vec![0.0; 28],
                push_right: vec![0.0; 28],
            },
            projection: ProjectionConfiguration {
                push_left: vec![0.0; 32],
                push_right: vec![0.0; 32],
                scissor_left: vec![0.0; 4],
                scissor_right: vec![0.0; 4],
                rgb_uniform: rgb,
                displacement_uniform: displacement,
                surface_feature_uniform: None,
                zone_uniform: zone,
                displacement_enabled: true,
            },
            outputs: Vec::new(),
        }
    }

    #[test]
    fn structured_profile_round_trips_every_public_transport_field() {
        let source = capsule();
        let zone = ZoneCompositorProfile::from_uniform(&source.projection.zone_uniform)
            .expect("zone profile");
        let mut target = vec![0.0; 92];
        zone.apply_to_uniform(&mut target).expect("apply zone");
        assert_eq!(&target[24..32], &source.projection.zone_uniform[24..32]);
        assert_eq!(&target[36..92], &source.projection.zone_uniform[36..92]);
        assert!(!zone.projection_effect_edge_guard_enabled);

        let rgb =
            RgbTransformProfile::from_uniform(&source.projection.rgb_uniform).expect("RGB profile");
        assert_eq!(rgb.mode, "independent");
        assert_eq!(rgb.blue.direction_rate_hz, -0.13);

        let displacement =
            SurfaceDisplacementProfile::from_capsule(&source).expect("displacement profile");
        assert!(displacement.enabled);
        assert_eq!(displacement.max_displacement_meters, 0.06);
    }

    #[test]
    fn profile_id_is_safe_for_a_portable_file_name() {
        assert_eq!(profile_file_stem("Evening flow!"), "evening-flow");
        assert!(validate_profile_id("a0").is_ok());
        assert!(validate_profile_id(&format!("a{}", "0".repeat(63))).is_ok());
        assert!(validate_profile_id("a").is_err());
        assert!(validate_profile_id(&format!("a{}", "0".repeat(64))).is_err());
        assert!(validate_profile_id("evening-flow").is_ok());
        assert!(validate_profile_id("../escape").is_err());
        assert!(validate_profile_id("A Profile").is_err());
    }

    fn replay_state() -> ReplayControlState {
        let source = capsule();
        ReplayControlState {
            schema: REPLAY_CONTROL_STATE_SCHEMA.to_string(),
            state_id: "round-trip".to_string(),
            revision: 7,
            created_unix_ms: 12,
            replay_layer: ReplayLayerState {
                layer_token: "final".to_string(),
                override_value: 0.0,
            },
            projection: ProjectionControlState {
                scale: 1.15,
                rgb_uniform_f32: source.projection.rgb_uniform,
                displacement_uniform_f32: source.projection.displacement_uniform,
                displacement_enabled: true,
                zone_uniform_f32: source.projection.zone_uniform,
                surface_feature_uniform_f32: None,
            },
            control_transport: None,
            preview: Some(DesktopPreviewProfile {
                layer_token: "final".to_string(),
                effect_clock_speed: 1.0,
                preview_target_hz: 60.0,
                preview_mode: "stereo".to_string(),
                preview_eye: "left".to_string(),
                color_effect_phase_offset_turns: 0.0,
                color_effect_rate_hz: 0.0,
                buffer_footprint_scale: 1.0,
            }),
        }
    }

    #[test]
    fn replay_control_state_round_trips_with_distinct_suffix_and_hostess_schema() {
        let state = replay_state();
        state.validate().expect("valid state");
        let directory =
            std::env::temp_dir().join(format!("hostess-replay-state-{}", std::process::id()));
        let path = state.write(&directory).expect("write state");
        assert!(path
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.ends_with(REPLAY_CONTROL_STATE_SUFFIX)));
        assert!(!path
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.ends_with(LEGACY_CONTROL_PROFILE_SUFFIX)));
        let bytes = fs::read(&path).expect("read emitted state");
        assert!(!String::from_utf8_lossy(&bytes).contains("rusty.quest."));
        assert_eq!(
            read_stored_control(&path, &capsule()).expect("read state"),
            state
        );
        let _ = fs::remove_file(path);
        let _ = fs::remove_dir(directory);
    }

    #[test]
    fn replay_control_state_rejects_unknown_non_finite_and_wrong_lengths() {
        let state = replay_state();
        let mut json = serde_json::to_value(&state).expect("serialize");
        json.as_object_mut()
            .expect("object")
            .insert("android_path".to_string(), serde_json::Value::Null);
        assert!(serde_json::from_value::<ReplayControlState>(json).is_err());

        let mut damaged = state.clone();
        damaged.projection.rgb_uniform_f32[3] = f32::NAN;
        assert!(damaged.validate().is_err());
        let mut short = state;
        short.projection.zone_uniform_f32.pop();
        assert!(short.validate().is_err());
    }

    #[test]
    fn replay_v2_accepts_exact_surface_suffix_and_v1_rejects_it() {
        let mut state = replay_state();
        let surface = crate::capsule::disabled_surface_feature_uniform(
            &state.projection.displacement_uniform_f32,
            9,
        )
        .expect("surface");
        state.projection.surface_feature_uniform_f32 = Some(surface);
        state.validate().expect("v2 state");

        let mut v1 = state.clone();
        v1.schema = REPLAY_CONTROL_STATE_V1_SCHEMA.to_string();
        assert!(v1.validate().is_err());
    }

    #[test]
    fn replay_v2_rejects_surface_prefix_abi_and_reserved_damage() {
        let state = replay_state();
        let baseline = crate::capsule::disabled_surface_feature_uniform(
            &state.projection.displacement_uniform_f32,
            0,
        )
        .expect("surface");
        for (index, value) in [(0, baseline[0] + 0.25), (30, 1.0), (31, 1.0)] {
            let mut damaged = state.clone();
            let mut surface = baseline.clone();
            surface[index] = value;
            damaged.projection.surface_feature_uniform_f32 = Some(surface);
            assert!(damaged.validate().is_err(), "index {index}");
        }
    }

    #[test]
    fn replay_control_state_rejects_damaged_exact_tokens() {
        for (block, index, value) in [
            ("zone", 24, 9.0),
            ("zone", 25, 0.5),
            ("zone", 44, -1.0),
            ("zone", 63, 3.0),
            ("zone", 67, 3.5),
            ("zone", 71, 5.0),
            ("rgb", 0, 0.5),
            ("rgb", 1, 3.0),
        ] {
            let mut state = replay_state();
            if block == "zone" {
                state.projection.zone_uniform_f32[index] = value;
            } else {
                state.projection.rgb_uniform_f32[index] = value;
            }
            assert!(state.validate().is_err(), "{block}[{index}]={value}");
        }
    }

    #[test]
    fn replay_control_state_write_refuses_overwrite_without_changing_target() {
        let state = replay_state();
        let directory = std::env::temp_dir().join(format!(
            "hostess-replay-state-create-new-{}",
            std::process::id()
        ));
        fs::create_dir_all(&directory).expect("directory");
        let path = directory.join(format!(
            "{}{}",
            profile_file_stem(&state.state_id),
            REPLAY_CONTROL_STATE_SUFFIX
        ));
        fs::write(&path, b"sentinel").expect("sentinel");
        assert!(state.write(&directory).is_err());
        assert_eq!(fs::read(&path).expect("read sentinel"), b"sentinel");
        let _ = fs::remove_file(path);
        let _ = fs::remove_dir(directory);
    }

    #[test]
    fn stored_control_reader_is_bounded_strict_and_uses_one_immutable_buffer() {
        let directory = std::env::temp_dir().join(format!(
            "hostess-stored-control-reader-{}",
            std::process::id()
        ));
        fs::create_dir_all(&directory).expect("directory");
        let path = directory.join("selected.json");
        fs::write(&path, br#"{"schema":"damaged-on-disk"}"#).expect("path metadata");
        let state = replay_state();
        let state_bytes = serde_json::to_vec(&state).expect("state bytes");
        let baseline = capsule();

        let loaded = read_stored_control_with(&path, &baseline, |_| Ok(state_bytes.clone()))
            .expect("injected immutable buffer");
        assert_eq!(loaded, state);

        let oversize = vec![b' '; MAX_CONTROL_PROFILE_BYTES as usize + 1];
        assert!(read_stored_control_with(&path, &baseline, |_| Ok(oversize)).is_err());

        let malformed_schema = br#"{"schema":42}"#.to_vec();
        assert!(read_stored_control_with(&path, &baseline, |_| Ok(malformed_schema)).is_err());

        let invalid_utf8 = vec![0xff, 0xfe, 0xfd];
        assert!(read_stored_control_with(&path, &baseline, |_| Ok(invalid_utf8)).is_err());

        fs::remove_file(path).expect("file cleanup");
        fs::remove_dir(directory).expect("directory cleanup");
    }

    #[test]
    fn legacy_quest_profile_imports_losslessly_into_capsule_native_blocks() {
        let mut baseline = capsule();
        baseline.outputs.push(crate::capsule::OutputLayer {
            name: "final".to_string(),
            override_value: 0.0,
        });
        let legacy = LegacyControlProfile {
            schema: LEGACY_CONTROL_PROFILE_SCHEMA.to_string(),
            profile_id: "golden-import".to_string(),
            revision: 7,
            created_unix_ms: 12,
            quest_controls: QuestControlProfile {
                layer_override: 0.0,
                projection_scale: 1.15,
                zone_compositor: ZoneCompositorProfile::from_uniform(
                    &baseline.projection.zone_uniform,
                )
                .expect("zone"),
                rgb_channel_transform: RgbTransformProfile::from_uniform(
                    &baseline.projection.rgb_uniform,
                )
                .expect("rgb"),
                projection_surface_displacement: SurfaceDisplacementProfile::from_capsule(
                    &baseline,
                )
                .expect("displacement"),
            },
            desktop_preview: None,
        };
        let state = ReplayControlState::import_legacy(&legacy, &baseline).expect("legacy import");
        assert_eq!(
            state.projection.rgb_uniform_f32,
            baseline.projection.rgb_uniform
        );
        assert_eq!(
            state.projection.displacement_uniform_f32,
            baseline.projection.displacement_uniform
        );
        assert_eq!(
            state.projection.zone_uniform_f32,
            baseline.projection.zone_uniform
        );
        assert_eq!(state.replay_layer.layer_token, "final");
        assert_eq!(state.replay_layer.override_value, 0.0);
        assert_eq!(state.projection.scale, 1.15);
    }
}
