use std::{collections::BTreeSet, fs, path::Path};

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};

use crate::capsule::{ReplayCapsule, CAPSULE_SCHEMA};

pub(crate) const CONTROL_TRANSPORT_SCHEMA: &str =
    "rusty.hostess.projection_replay_control_transport.v1";
const MAX_BYTES: u64 = 64 * 1024;
const MAX_LABEL_BYTES: usize = 256;
const MAX_PHASE_CONTROLS: usize = 8;

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ControlTransport {
    pub(crate) schema: String,
    pub(crate) transport_id: String,
    pub(crate) capsule: CapsuleBinding,
    #[serde(default)]
    pub(crate) clock: Option<ClockControl>,
    #[serde(default)]
    pub(crate) phase_controls: Vec<PhaseControl>,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CapsuleBinding {
    pub(crate) schema: String,
    pub(crate) sha256: String,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ClockControl {
    pub(crate) initial_seconds: f32,
    pub(crate) default_seconds: f32,
    pub(crate) minimum_seconds: f32,
    pub(crate) maximum_seconds: f32,
    #[serde(default)]
    pub(crate) targets: Vec<TargetMapping>,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PhaseControl {
    pub(crate) control_id: String,
    pub(crate) label: String,
    pub(crate) initial_phase: f32,
    pub(crate) default_phase: f32,
    pub(crate) minimum_phase: f32,
    pub(crate) maximum_phase: f32,
    pub(crate) rate_hz: f32,
    pub(crate) targets: Vec<TargetMapping>,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
pub(crate) struct TargetMapping {
    #[serde(flatten)]
    pub(crate) target: Target,
    pub(crate) scale: f32,
    pub(crate) offset: f32,
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
#[serde(tag = "target", rename_all = "kebab-case")]
pub(crate) enum Target {
    ProjectionPush { view: View, index: usize },
    GuidePush { view: View, index: usize },
    ProjectionZoneUniform { index: usize },
    ProjectionSurfaceUniform { index: usize },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "kebab-case")]
pub(crate) enum View {
    Left,
    Right,
    Both,
}

impl ControlTransport {
    pub(crate) fn read(path: &Path, capsule: &ReplayCapsule, capsule_sha256: &str) -> Result<Self> {
        let metadata = fs::metadata(path)
            .with_context(|| format!("control transport does not exist: {}", path.display()))?;
        if metadata.len() > MAX_BYTES {
            bail!("control transport exceeds the 64 KiB limit");
        }
        let bytes = fs::read(path).with_context(|| format!("failed to read {}", path.display()))?;
        let value = Self::parse_bytes(&bytes)
            .with_context(|| format!("invalid control transport {}", path.display()))?;
        value.validate(capsule, capsule_sha256)?;
        Ok(value)
    }

    fn parse_bytes(bytes: &[u8]) -> Result<Self> {
        if bytes.len() as u64 > MAX_BYTES {
            bail!("control transport exceeds the 64 KiB limit");
        }
        let json: serde_json::Value =
            serde_json::from_slice(bytes).context("control transport JSON is invalid")?;
        validate_target_object_fields(&json)?;
        serde_json::from_value(json).context("control transport JSON is invalid")
    }

    pub(crate) fn validate(&self, capsule: &ReplayCapsule, capsule_sha256: &str) -> Result<()> {
        if self.schema != CONTROL_TRANSPORT_SCHEMA
            || self.capsule.schema != CAPSULE_SCHEMA
            || self.capsule.sha256 != capsule_sha256
        {
            bail!("control transport schema or capsule binding mismatch");
        }
        identity("transport_id", &self.transport_id)?;
        if self.phase_controls.len() > MAX_PHASE_CONTROLS {
            bail!("phase_controls exceeds the maximum count of 8");
        }
        let mut ids = BTreeSet::new();
        let mut owned = BTreeSet::new();
        if let Some(clock) = &self.clock {
            bounds(
                "clock",
                clock.initial_seconds,
                clock.default_seconds,
                clock.minimum_seconds,
                clock.maximum_seconds,
            )?;
            validate_targets(&clock.targets, capsule, &mut owned)?;
        }
        for control in &self.phase_controls {
            identity("control_id", &control.control_id)?;
            if !ids.insert(&control.control_id) {
                bail!("duplicate phase control id");
            }
            if control.label.len() > MAX_LABEL_BYTES {
                bail!("phase label exceeds 256 UTF-8 bytes");
            }
            bounds(
                &control.control_id,
                control.initial_phase,
                control.default_phase,
                control.minimum_phase,
                control.maximum_phase,
            )?;
            finite("rate_hz", control.rate_hz)?;
            if control.rate_hz.abs() > 1000.0 {
                bail!("rate_hz is outside -1000..=1000");
            }
            validate_targets(&control.targets, capsule, &mut owned)?;
        }
        Ok(())
    }

    pub(crate) fn apply(
        &self,
        capsule: &mut ReplayCapsule,
        elapsed_seconds: f32,
        selected_phases: &[f32],
    ) -> Result<()> {
        if selected_phases.len() != self.phase_controls.len() {
            bail!("phase value count mismatch");
        }
        // Revalidate against actual vectors immediately before mutation.
        self.validate(capsule, &self.capsule.sha256)?;
        if !elapsed_seconds.is_finite() {
            bail!("elapsed time must be finite");
        }
        if let Some(clock) = &self.clock {
            let elapsed = elapsed_seconds.clamp(clock.minimum_seconds, clock.maximum_seconds);
            for target in &clock.targets {
                write_target(capsule, target, elapsed)?;
            }
        }
        for (control, selected) in self.phase_controls.iter().zip(selected_phases) {
            if !selected.is_finite()
                || *selected < control.minimum_phase
                || *selected > control.maximum_phase
            {
                bail!("selected phase is outside its provider range");
            }
            let phase = (*selected + elapsed_seconds * control.rate_hz).rem_euclid(1.0);
            for target in &control.targets {
                write_target(capsule, target, phase)?;
            }
        }
        Ok(())
    }
}

fn validate_target_object_fields(root: &serde_json::Value) -> Result<()> {
    let mut targets = Vec::new();
    if let Some(clock_targets) = root
        .get("clock")
        .and_then(|clock| clock.get("targets"))
        .and_then(serde_json::Value::as_array)
    {
        targets.extend(clock_targets);
    }
    if let Some(controls) = root
        .get("phase_controls")
        .and_then(serde_json::Value::as_array)
    {
        for control in controls {
            if let Some(control_targets) =
                control.get("targets").and_then(serde_json::Value::as_array)
            {
                targets.extend(control_targets);
            }
        }
    }
    for target in targets {
        let object = target
            .as_object()
            .context("control target must be an object")?;
        let kind = object
            .get("target")
            .and_then(serde_json::Value::as_str)
            .context("control target discriminator must be a string")?;
        let allowed: &[&str] = match kind {
            "projection-push" | "guide-push" => &["target", "view", "index", "scale", "offset"],
            "projection-zone-uniform" | "projection-surface-uniform" => {
                &["target", "index", "scale", "offset"]
            }
            _ => bail!("unsupported control target {kind}"),
        };
        if object.keys().any(|key| !allowed.contains(&key.as_str())) {
            bail!("control target contains an unknown field");
        }
    }
    Ok(())
}

fn validate_targets(
    targets: &[TargetMapping],
    capsule: &ReplayCapsule,
    owned: &mut BTreeSet<String>,
) -> Result<()> {
    if targets.is_empty() {
        bail!("a control must own at least one target");
    }
    for mapping in targets {
        finite("target.scale", mapping.scale)?;
        finite("target.offset", mapping.offset)?;
        for key in expanded_keys(&mapping.target, capsule)? {
            if !owned.insert(key) {
                bail!("duplicate or overlapping expanded control destination");
            }
        }
    }
    Ok(())
}

fn expanded_keys(target: &Target, capsule: &ReplayCapsule) -> Result<Vec<String>> {
    let (stem, view, index, left_len, right_len) = match target {
        Target::ProjectionPush { view, index } => (
            "projection-push",
            Some(*view),
            *index,
            capsule.projection.push_left.len(),
            capsule.projection.push_right.len(),
        ),
        Target::GuidePush { view, index } => (
            "guide-push",
            Some(*view),
            *index,
            capsule.guide.push_left.len(),
            capsule.guide.push_right.len(),
        ),
        Target::ProjectionZoneUniform { index } => {
            if *index >= capsule.projection.zone_uniform.len() {
                bail!("projection-zone-uniform index is out of bounds");
            }
            return Ok(vec![format!("projection-zone-uniform:{index}")]);
        }
        Target::ProjectionSurfaceUniform { index } => {
            let surface = capsule
                .projection
                .surface_feature_uniform
                .as_ref()
                .context("projection-surface-uniform requires surface uniform ABI v2")?;
            if !(16..=29).contains(index) || *index >= surface.len() {
                bail!(
                    "projection-surface-uniform may target only the neutral v2 suffix indices 16..=29"
                );
            }
            return Ok(vec![format!("projection-surface-uniform:{index}")]);
        }
    };
    let view = view.expect("push targets have a view");
    if matches!(view, View::Left | View::Both) && index >= left_len {
        bail!("{stem} left index is out of bounds");
    }
    if matches!(view, View::Right | View::Both) && index >= right_len {
        bail!("{stem} right index is out of bounds");
    }
    Ok(match view {
        View::Left => vec![format!("{stem}:left:{index}")],
        View::Right => vec![format!("{stem}:right:{index}")],
        View::Both => vec![
            format!("{stem}:left:{index}"),
            format!("{stem}:right:{index}"),
        ],
    })
}

fn write_target(capsule: &mut ReplayCapsule, mapping: &TargetMapping, value: f32) -> Result<()> {
    let written = value * mapping.scale + mapping.offset;
    if !written.is_finite() {
        bail!("mapped control value is non-finite");
    }
    match mapping.target {
        Target::ProjectionPush { view, index } => write_views(
            &mut capsule.projection.push_left,
            &mut capsule.projection.push_right,
            view,
            index,
            written,
        ),
        Target::GuidePush { view, index } => write_views(
            &mut capsule.guide.push_left,
            &mut capsule.guide.push_right,
            view,
            index,
            written,
        ),
        Target::ProjectionZoneUniform { index } => {
            *capsule
                .projection
                .zone_uniform
                .get_mut(index)
                .context("projection-zone-uniform index changed after validation")? = written
        }
        Target::ProjectionSurfaceUniform { index } => {
            *capsule
                .projection
                .surface_feature_uniform
                .as_mut()
                .context("projection-surface-uniform ABI changed after validation")?
                .get_mut(index)
                .context("projection-surface-uniform index changed after validation")? = written
        }
    }
    Ok(())
}

fn write_views(left: &mut [f32], right: &mut [f32], view: View, index: usize, value: f32) {
    if matches!(view, View::Left | View::Both) {
        left[index] = value;
    }
    if matches!(view, View::Right | View::Both) {
        right[index] = value;
    }
}

fn bounds(label: &str, initial: f32, default: f32, minimum: f32, maximum: f32) -> Result<()> {
    for (field, value) in [
        ("initial", initial),
        ("default", default),
        ("minimum", minimum),
        ("maximum", maximum),
    ] {
        finite(&format!("{label}.{field}"), value)?;
    }
    if minimum > maximum
        || initial < minimum
        || initial > maximum
        || default < minimum
        || default > maximum
    {
        bail!("{label} has inconsistent bounds");
    }
    Ok(())
}
fn finite(label: &str, value: f32) -> Result<()> {
    if !value.is_finite() {
        bail!("{label} must be finite");
    }
    Ok(())
}
fn identity(label: &str, value: &str) -> Result<()> {
    if value.len() < 2
        || value.len() > 64
        || !value.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'-' | b'_' | b'.')
        })
        || !value
            .as_bytes()
            .first()
            .is_some_and(|b| b.is_ascii_lowercase() || b.is_ascii_digit())
    {
        bail!("{label} must be a normalized 2..64 character lowercase id");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use super::*;
    use crate::capsule::{
        ColorInput, DepthInput, Extent, GuideConfiguration, OutputLayer, ProjectionConfiguration,
        ReplayInputs, ShaderBundle,
    };

    fn capsule() -> ReplayCapsule {
        ReplayCapsule {
            schema: CAPSULE_SCHEMA.to_string(),
            name: "sanitized-provider-fixture".to_string(),
            extent: Extent {
                width: 4,
                height: 2,
            },
            shaders: ShaderBundle {
                fullscreen_vertex_spirv: PathBuf::from("v.spv"),
                guide_fragment_spirv: Vec::new(),
                projection_fragment_spirv: PathBuf::from("f.spv"),
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
                push_left: vec![0.0; 32],
                push_right: vec![0.0; 32],
                scissor_left: vec![0.0; 4],
                scissor_right: vec![0.0; 4],
                rgb_uniform: vec![0.0; 24],
                displacement_uniform: vec![0.0; 16],
                surface_feature_uniform: None,
                zone_uniform: vec![0.0; 92],
                displacement_enabled: false,
            },
            outputs: vec![OutputLayer {
                name: "final".to_string(),
                override_value: 0.0,
            }],
        }
    }

    fn mapping(target: Target) -> TargetMapping {
        TargetMapping {
            target,
            scale: 1.0,
            offset: 0.0,
        }
    }

    fn descriptor() -> ControlTransport {
        ControlTransport {
            schema: CONTROL_TRANSPORT_SCHEMA.to_string(),
            transport_id: "sanitized-transport".to_string(),
            capsule: CapsuleBinding {
                schema: CAPSULE_SCHEMA.to_string(),
                sha256: "a".repeat(64),
            },
            clock: Some(ClockControl {
                initial_seconds: 0.0,
                default_seconds: 0.0,
                minimum_seconds: 0.0,
                maximum_seconds: 10.0,
                targets: vec![
                    mapping(Target::ProjectionPush {
                        view: View::Both,
                        index: 6,
                    }),
                    mapping(Target::ProjectionZoneUniform { index: 35 }),
                ],
            }),
            phase_controls: vec![PhaseControl {
                control_id: "opaque-phase".to_string(),
                label: "Provider phase".to_string(),
                initial_phase: 0.125,
                default_phase: 0.125,
                minimum_phase: 0.0,
                maximum_phase: 1.0,
                rate_hz: 0.25,
                targets: vec![
                    mapping(Target::ProjectionPush {
                        view: View::Both,
                        index: 12,
                    }),
                    mapping(Target::GuidePush {
                        view: View::Both,
                        index: 8,
                    }),
                ],
            }],
        }
    }

    #[test]
    fn sanitized_descriptor_expands_both_and_matches_formula_at_boundaries() {
        let mut capsule = capsule();
        let transport = descriptor();
        transport
            .validate(&capsule, &"a".repeat(64))
            .expect("descriptor");
        for (elapsed, expected) in [(0.0, 0.125), (3.5, 0.0), (4.0, 0.125)] {
            let mut effective = capsule.clone();
            transport
                .apply(&mut effective, elapsed, &[0.125])
                .expect("apply");
            assert_eq!(effective.projection.push_left[6], elapsed);
            assert_eq!(effective.projection.push_right[6], elapsed);
            assert_eq!(effective.projection.zone_uniform[35], elapsed);
            assert!((effective.projection.push_left[12] - expected).abs() < 0.0001);
            assert_eq!(
                effective.projection.push_left[12],
                effective.projection.push_right[12]
            );
            assert_eq!(effective.guide.push_left[8], effective.guide.push_right[8]);
        }
        transport
            .apply(&mut capsule, 1.0, &[0.125])
            .expect("deterministic apply");
    }

    #[test]
    fn left_right_bounds_duplicates_overlap_and_binding_fail_closed() {
        let capsule = capsule();
        let mut transport = descriptor();
        transport.phase_controls[0].targets = vec![
            mapping(Target::ProjectionPush {
                view: View::Left,
                index: 1,
            }),
            mapping(Target::ProjectionPush {
                view: View::Right,
                index: 1,
            }),
        ];
        transport
            .validate(&capsule, &"a".repeat(64))
            .expect("separate views");
        transport.phase_controls[0]
            .targets
            .push(mapping(Target::ProjectionPush {
                view: View::Both,
                index: 1,
            }));
        assert!(transport.validate(&capsule, &"a".repeat(64)).is_err());
        let mut out_of_bounds = descriptor();
        out_of_bounds.phase_controls[0].targets[0].target = Target::ProjectionPush {
            view: View::Left,
            index: 32,
        };
        assert!(out_of_bounds.validate(&capsule, &"a".repeat(64)).is_err());
        assert!(descriptor().validate(&capsule, &"b".repeat(64)).is_err());
    }

    #[test]
    fn non_finite_ranges_counts_and_unknown_fields_fail_closed() {
        let capsule = capsule();
        let mut damaged = descriptor();
        damaged.phase_controls[0].rate_hz = f32::INFINITY;
        assert!(damaged.validate(&capsule, &"a".repeat(64)).is_err());
        let mut count = descriptor();
        count.phase_controls = vec![count.phase_controls[0].clone(); 9];
        assert!(count.validate(&capsule, &"a".repeat(64)).is_err());
        let json = serde_json::to_vec(&descriptor()).expect("json");
        let mut value: serde_json::Value = serde_json::from_slice(&json).expect("value");
        value["unknown"] = serde_json::json!(true);
        assert!(serde_json::from_value::<ControlTransport>(value).is_err());
        let mut value = serde_json::to_value(descriptor()).expect("value");
        value["phase_controls"][0]["targets"][0]["unknown"] = serde_json::json!(true);
        assert!(ControlTransport::parse_bytes(
            &serde_json::to_vec(&value).expect("damaged target")
        )
        .is_err());
        assert!(ControlTransport::parse_bytes(&vec![b' '; MAX_BYTES as usize + 1]).is_err());
    }

    #[test]
    fn transport_and_control_ids_share_portable_profile_domain() {
        for accepted in ["a0".to_string(), format!("a{}", "0".repeat(63))] {
            let mut transport = descriptor();
            transport.transport_id = accepted.clone();
            transport.phase_controls[0].control_id = accepted;
            transport
                .validate(&capsule(), &"a".repeat(64))
                .expect("portable boundary id");
        }
        for rejected in [
            "a".to_string(),
            "Mixed-case".to_string(),
            format!("a{}", "0".repeat(64)),
        ] {
            let mut transport = descriptor();
            transport.transport_id = rejected.clone();
            assert!(transport.validate(&capsule(), &"a".repeat(64)).is_err());
            let mut transport = descriptor();
            transport.phase_controls[0].control_id = rejected;
            assert!(transport.validate(&capsule(), &"a".repeat(64)).is_err());
        }
    }

    #[test]
    fn v2_transport_can_address_exact_mask_and_stretch_policy_without_prefix_writes() {
        let mut capsule = capsule();
        capsule.projection.surface_feature_uniform = Some(
            crate::capsule::disabled_surface_feature_uniform(
                &capsule.projection.displacement_uniform,
                0,
            )
            .expect("surface"),
        );
        let mut transport = descriptor();
        transport.clock = None;
        transport.phase_controls[0].initial_phase = 0.0;
        transport.phase_controls[0].default_phase = 0.0;
        transport.phase_controls[0].rate_hz = 0.0;
        transport.phase_controls[0].targets = vec![
            TargetMapping {
                target: Target::ProjectionSurfaceUniform { index: 23 },
                scale: 0.0,
                offset: 1.0,
            },
            TargetMapping {
                target: Target::ProjectionSurfaceUniform { index: 28 },
                scale: 0.0,
                offset: 1.0,
            },
        ];
        transport
            .validate(&capsule, &"a".repeat(64))
            .expect("v2 targets");
        transport.apply(&mut capsule, 0.0, &[0.0]).expect("apply");
        let surface = capsule
            .projection
            .surface_feature_uniform
            .as_ref()
            .expect("surface");
        assert_eq!(surface[23], 1.0);
        assert_eq!(surface[28], 1.0);

        transport.phase_controls[0].targets =
            vec![mapping(Target::ProjectionSurfaceUniform { index: 15 })];
        assert!(transport.validate(&capsule, &"a".repeat(64)).is_err());
        transport.phase_controls[0].targets =
            vec![mapping(Target::ProjectionSurfaceUniform { index: 30 })];
        assert!(transport.validate(&capsule, &"a".repeat(64)).is_err());
    }
}
