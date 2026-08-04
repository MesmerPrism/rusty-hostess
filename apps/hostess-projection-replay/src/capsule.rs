use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::{Path, PathBuf},
};

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const CAPSULE_SCHEMA: &str = "rusty.hostess.projection_replay_capsule.v1";
pub const REPORT_SCHEMA: &str = "rusty.hostess.projection_replay_report.v1";
pub const COMPARISON_SCHEMA: &str = "rusty.hostess.projection_replay_comparison.v1";
pub const MAX_PNG_SEQUENCE_FRAMES: usize = 120;
pub const SURFACE_UNIFORM_V1_FLOATS: usize = 16;
pub const SURFACE_UNIFORM_V2_FLOATS: usize = 32;
pub const SURFACE_UNIFORM_V1_BYTES: usize = SURFACE_UNIFORM_V1_FLOATS * 4;
pub const SURFACE_UNIFORM_V2_BYTES: usize = SURFACE_UNIFORM_V2_FLOATS * 4;
pub const SURFACE_UNIFORM_V2_ABI_VERSION: u32 = 2;
pub const SURFACE_TILING_CONTRACT_ID: &str = "rusty.quest.projection-surface-tiling.v1";
pub const INNER_ALPHA_CONTRACT_ID: &str = "rusty.quest.projection-inner-alpha.v1";
const MAX_CAPSULE_BYTES: u64 = 1024 * 1024;
const RESERVED_GUIDE_OUTPUT_NAMES: [&str; 5] = [
    "guide-raw-brightness",
    "guide-blur-temp",
    "guide-preblur-brightness",
    "guide-raw-strength",
    "guide-blurred-strength",
];

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReplayCapsule {
    pub schema: String,
    pub name: String,
    pub extent: Extent,
    pub shaders: ShaderBundle,
    pub inputs: ReplayInputs,
    pub guide: GuideConfiguration,
    pub projection: ProjectionConfiguration,
    pub outputs: Vec<OutputLayer>,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Extent {
    pub width: u32,
    pub height: u32,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ShaderBundle {
    pub fullscreen_vertex_spirv: PathBuf,
    pub guide_fragment_spirv: Vec<PathBuf>,
    pub projection_fragment_spirv: PathBuf,
    pub displacement_vertex_spirv: Option<PathBuf>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReplayInputs {
    pub camera_left: ColorInput,
    pub camera_right: ColorInput,
    pub video: ColorInput,
    pub depth: DepthInput,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "kebab-case", deny_unknown_fields)]
pub enum ColorInput {
    Png {
        path: PathBuf,
    },
    PngSequence {
        paths: Vec<PathBuf>,
    },
    Synthetic {
        pattern: SyntheticPattern,
        #[serde(default)]
        variant: u32,
    },
    Transparent,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum SyntheticPattern {
    RgbQuadrants,
    RgbBands,
    RadialRings,
    UvGradient,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "kebab-case", deny_unknown_fields)]
pub enum DepthInput {
    Constant {
        meters: f32,
    },
    HorizontalRamp {
        near_m: f32,
        far_m: f32,
    },
    Png16 {
        path: PathBuf,
        near_m: f32,
        far_m: f32,
    },
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct GuideConfiguration {
    pub push_left: Vec<f32>,
    pub push_right: Vec<f32>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProjectionConfiguration {
    pub push_left: Vec<f32>,
    pub push_right: Vec<f32>,
    pub scissor_left: Vec<f32>,
    pub scissor_right: Vec<f32>,
    pub rgb_uniform: Vec<f32>,
    pub displacement_uniform: Vec<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub surface_feature_uniform: Option<Vec<f32>>,
    pub zone_uniform: Vec<f32>,
    #[serde(default)]
    pub displacement_enabled: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct OutputLayer {
    pub name: String,
    pub override_value: f32,
}

#[derive(Clone, Debug, Serialize)]
pub struct ReplayReport {
    pub schema: &'static str,
    pub capsule_schema: String,
    pub capsule_name: String,
    pub capsule_path: String,
    pub capsule_sha256: String,
    pub extent: Extent,
    pub adapter: AdapterReport,
    pub shaders: Vec<ArtifactHash>,
    pub outputs: Vec<OutputReport>,
    pub validation: ValidationReport,
}

#[derive(Clone, Debug, Serialize)]
pub struct AdapterReport {
    pub name: String,
    pub vendor_id: u32,
    pub device_id: u32,
    pub api_version: String,
    pub driver_version: u32,
    pub device_type: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct ArtifactHash {
    pub role: String,
    pub path: String,
    pub sha256: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct OutputReport {
    pub layer: String,
    pub path: String,
    pub sha256: String,
    pub alpha_min: u8,
    pub alpha_max: u8,
}

#[derive(Clone, Debug, Serialize)]
pub struct ValidationReport {
    pub exact_spirv_loaded: bool,
    pub descriptor_contract: String,
    pub guide_push_bytes: usize,
    pub projection_push_bytes: usize,
    pub rgb_uniform_bytes: usize,
    pub displacement_uniform_bytes: usize,
    pub projection_surface_uniform_bytes: usize,
    pub projection_surface_uniform_abi_version: u32,
    pub projection_surface_uniform_prefix_bytes: usize,
    pub projection_surface_uniform_suffix_bytes: usize,
    pub projection_surface_uniform_stages: Vec<&'static str>,
    pub zone_uniform_bytes: usize,
    pub surface_features: SurfaceFeatureEvidence,
}

#[derive(Clone, Debug, Serialize)]
pub struct SurfaceFeatureEvidence {
    pub accepted_uniform_bytes: [usize; 2],
    pub actual_uniform_bytes: usize,
    pub descriptor_set: u32,
    pub descriptor_binding: u32,
    pub tiling: FeatureActivationEvidence,
    pub inner_alpha: FeatureActivationEvidence,
    pub marker_fields: BTreeMap<String, String>,
}

#[derive(Clone, Debug, Serialize)]
pub struct FeatureActivationEvidence {
    pub contract: &'static str,
    pub requested: bool,
    pub supported: bool,
    pub effective: bool,
}

pub struct LoadedReplayCapsule {
    pub capsule: ReplayCapsule,
    pub sha256: String,
}

impl ReplayCapsule {
    pub fn read(path: &Path) -> Result<Self> {
        Ok(Self::read_bound(path)?.capsule)
    }

    pub fn read_bound(path: &Path) -> Result<LoadedReplayCapsule> {
        let metadata = fs::metadata(path)
            .with_context(|| format!("replay capsule does not exist: {}", path.display()))?;
        if metadata.len() > MAX_CAPSULE_BYTES {
            bail!("replay capsule exceeds the 1 MiB limit");
        }
        let bytes = fs::read(path)
            .with_context(|| format!("failed to read replay capsule {}", path.display()))?;
        if bytes.len() as u64 > MAX_CAPSULE_BYTES {
            bail!("replay capsule exceeds the 1 MiB limit");
        }
        Self::parse_bound_bytes(path, &bytes)
    }

    fn parse_bound_bytes(path: &Path, bytes: &[u8]) -> Result<LoadedReplayCapsule> {
        let capsule: Self = serde_json::from_slice(bytes)
            .with_context(|| format!("invalid replay capsule JSON {}", path.display()))?;
        capsule.validate(path)?;
        let sha256 = format!("{:x}", Sha256::digest(bytes));
        Ok(LoadedReplayCapsule { capsule, sha256 })
    }

    pub fn validate(&self, capsule_path: &Path) -> Result<()> {
        if self.schema != CAPSULE_SCHEMA {
            bail!(
                "unsupported capsule schema {}; expected {}",
                self.schema,
                CAPSULE_SCHEMA
            );
        }
        if self.name.trim().is_empty() {
            bail!("capsule name must not be empty");
        }
        if self.extent.width < 2
            || self.extent.height < 2
            || self.extent.width > 8192
            || self.extent.height > 8192
        {
            bail!(
                "extent {}x{} is outside the supported 2..8192 range",
                self.extent.width,
                self.extent.height
            );
        }
        if !self.extent.width.is_multiple_of(2) {
            bail!("packed-stereo output width must be even");
        }
        exact_len("guide.push_left", &self.guide.push_left, 28)?;
        exact_len("guide.push_right", &self.guide.push_right, 28)?;
        exact_len("projection.push_left", &self.projection.push_left, 32)?;
        exact_len("projection.push_right", &self.projection.push_right, 32)?;
        exact_len("projection.scissor_left", &self.projection.scissor_left, 4)?;
        exact_len(
            "projection.scissor_right",
            &self.projection.scissor_right,
            4,
        )?;
        exact_len("projection.rgb_uniform", &self.projection.rgb_uniform, 24)?;
        exact_len(
            "projection.displacement_uniform",
            &self.projection.displacement_uniform,
            SURFACE_UNIFORM_V1_FLOATS,
        )?;
        if let Some(surface) = &self.projection.surface_feature_uniform {
            validate_surface_feature_uniform(surface, &self.projection.displacement_uniform)?;
        }
        exact_len("projection.zone_uniform", &self.projection.zone_uniform, 92)?;
        if self.shaders.guide_fragment_spirv.len() != 6 {
            bail!(
                "exactly six guide fragment passes are required, got {}",
                self.shaders.guide_fragment_spirv.len()
            );
        }
        if self.tessellated_projection_requested()
            && self.shaders.displacement_vertex_spirv.is_none()
        {
            bail!("displacement or surface tiling requires displacement_vertex_spirv");
        }
        validate_outputs(&self.outputs)?;
        for (label, values) in [
            ("guide.push_left", self.guide.push_left.as_slice()),
            ("guide.push_right", self.guide.push_right.as_slice()),
            ("projection.push_left", self.projection.push_left.as_slice()),
            (
                "projection.push_right",
                self.projection.push_right.as_slice(),
            ),
            (
                "projection.scissor_left",
                self.projection.scissor_left.as_slice(),
            ),
            (
                "projection.scissor_right",
                self.projection.scissor_right.as_slice(),
            ),
            (
                "projection.rgb_uniform",
                self.projection.rgb_uniform.as_slice(),
            ),
            (
                "projection.displacement_uniform",
                self.projection.displacement_uniform.as_slice(),
            ),
            (
                "projection.zone_uniform",
                self.projection.zone_uniform.as_slice(),
            ),
        ] {
            if values.iter().any(|value| !value.is_finite()) {
                bail!("{label} contains a non-finite value");
            }
        }
        if self
            .projection
            .surface_feature_uniform
            .as_ref()
            .is_some_and(|values| values.iter().any(|value| !value.is_finite()))
        {
            bail!("projection.surface_feature_uniform contains a non-finite value");
        }
        let base = capsule_path.parent().unwrap_or_else(|| Path::new("."));
        for (role, path) in self.shader_paths() {
            let resolved = resolve_path(base, path);
            let metadata = fs::metadata(&resolved).with_context(|| {
                format!("missing {role} shader artifact {}", resolved.display())
            })?;
            if metadata.len() < 20 || metadata.len() % 4 != 0 {
                bail!(
                    "{role} shader artifact {} is not valid-sized SPIR-V",
                    resolved.display()
                );
            }
        }
        validate_color_input("camera_left", &self.inputs.camera_left, base)?;
        validate_color_input("camera_right", &self.inputs.camera_right, base)?;
        validate_color_input("video", &self.inputs.video, base)?;
        Ok(())
    }

    pub fn projection_surface_uniform(&self) -> &[f32] {
        self.projection
            .surface_feature_uniform
            .as_deref()
            .unwrap_or(&self.projection.displacement_uniform)
    }

    pub fn tessellated_projection_requested(&self) -> bool {
        self.projection.displacement_enabled
            || self
                .projection
                .surface_feature_uniform
                .as_ref()
                .is_some_and(|values| values[16] >= 0.5)
    }

    pub fn surface_feature_evidence(&self, rendered: bool) -> SurfaceFeatureEvidence {
        let surface = self.projection.surface_feature_uniform.as_deref();
        let supported = surface.is_some();
        let tiling_requested = surface.is_some_and(|values| values[16] >= 0.5);
        let inner_alpha_requested = surface.is_some_and(|values| values[21] >= 0.5);
        let mut marker_fields = BTreeMap::new();
        marker_fields.insert(
            "projectionSurfaceTilingContract".to_string(),
            SURFACE_TILING_CONTRACT_ID.to_string(),
        );
        marker_fields.insert(
            "projectionSurfaceTilingRequested".to_string(),
            tiling_requested.to_string(),
        );
        marker_fields.insert(
            "projectionSurfaceTilingSupported".to_string(),
            supported.to_string(),
        );
        marker_fields.insert(
            "projectionSurfaceTilingEffective".to_string(),
            (tiling_requested && supported && rendered).to_string(),
        );
        marker_fields.insert(
            "projectionSurfaceTopology".to_string(),
            surface
                .map_or("continuous", |values| {
                    token_name(values[17], &["continuous", "tiled"])
                })
                .to_string(),
        );
        marker_fields.insert(
            "projectionSurfaceTileGapNormalized".to_string(),
            surface.map_or(0.0, |values| values[18]).to_string(),
        );
        marker_fields.insert(
            "projectionSurfaceDepthFlexibility".to_string(),
            surface.map_or(1.0, |values| values[19]).to_string(),
        );
        marker_fields.insert(
            "projectionSurfaceTilingScope".to_string(),
            surface
                .map_or("core-and-stretch", |values| {
                    token_name(values[20], &["core-and-stretch", "core-only"])
                })
                .to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaContract".to_string(),
            INNER_ALPHA_CONTRACT_ID.to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaInput".to_string(),
            "processed-core".to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaRequested".to_string(),
            inner_alpha_requested.to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaSupported".to_string(),
            supported.to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaEffective".to_string(),
            (inner_alpha_requested && supported && rendered).to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaDriver".to_string(),
            surface
                .map_or("luma", |values| {
                    token_name(values[22], &["red", "green", "blue", "luma", "max"])
                })
                .to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaThreshold".to_string(),
            surface.map_or(0.5, |values| values[24]).to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaSoftness".to_string(),
            surface.map_or(0.1, |values| values[25]).to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaAmount".to_string(),
            surface.map_or(0.0, |values| values[26]).to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaInvert".to_string(),
            surface.is_some_and(|values| values[27] >= 0.5).to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaStretchPolicy".to_string(),
            surface
                .map_or("follow-projection", |values| {
                    token_name(values[23], &["follow-projection", "opaque-independent"])
                })
                .to_string(),
        );
        marker_fields.insert(
            "projectionInnerAlphaStretchObeysExactProjectionMask".to_string(),
            surface.is_some_and(|values| values[28] >= 0.5).to_string(),
        );
        marker_fields.insert(
            "projectionSurfaceFeatureUniformAbiRequested".to_string(),
            if supported { "2" } else { "1" }.to_string(),
        );
        marker_fields.insert(
            "projectionSurfaceFeatureUniformAbiProvided".to_string(),
            if supported { "2" } else { "1" }.to_string(),
        );
        SurfaceFeatureEvidence {
            accepted_uniform_bytes: [SURFACE_UNIFORM_V1_BYTES, SURFACE_UNIFORM_V2_BYTES],
            actual_uniform_bytes: self.projection_surface_uniform().len() * 4,
            descriptor_set: 3,
            descriptor_binding: 1,
            tiling: FeatureActivationEvidence {
                contract: SURFACE_TILING_CONTRACT_ID,
                requested: tiling_requested,
                supported,
                effective: tiling_requested && supported && rendered,
            },
            inner_alpha: FeatureActivationEvidence {
                contract: INNER_ALPHA_CONTRACT_ID,
                requested: inner_alpha_requested,
                supported,
                effective: inner_alpha_requested && supported && rendered,
            },
            marker_fields,
        }
    }

    pub fn shader_paths(&self) -> Vec<(&'static str, &Path)> {
        let mut paths = vec![(
            "fullscreen-vertex",
            self.shaders.fullscreen_vertex_spirv.as_path(),
        )];
        const GUIDE_ROLES: [&str; 6] = [
            "guide-raw-brightness",
            "guide-preblur-horizontal",
            "guide-preblur-vertical",
            "guide-raw-strength",
            "guide-strength-horizontal",
            "guide-strength-vertical",
        ];
        paths.extend(
            self.shaders
                .guide_fragment_spirv
                .iter()
                .zip(GUIDE_ROLES)
                .map(|(path, role)| (role, path.as_path())),
        );
        paths.push((
            "projection-fragment",
            self.shaders.projection_fragment_spirv.as_path(),
        ));
        if let Some(path) = &self.shaders.displacement_vertex_spirv {
            paths.push(("projection-displacement-vertex", path.as_path()));
        }
        paths
    }

    pub fn make_paths_absolute(&mut self, base: &Path) -> Result<()> {
        self.shaders.fullscreen_vertex_spirv =
            absolute_existing_path(base, &self.shaders.fullscreen_vertex_spirv)?;
        for path in &mut self.shaders.guide_fragment_spirv {
            *path = absolute_existing_path(base, path)?;
        }
        self.shaders.projection_fragment_spirv =
            absolute_existing_path(base, &self.shaders.projection_fragment_spirv)?;
        if let Some(path) = &mut self.shaders.displacement_vertex_spirv {
            *path = absolute_existing_path(base, path)?;
        }
        for input in [
            &mut self.inputs.camera_left,
            &mut self.inputs.camera_right,
            &mut self.inputs.video,
        ] {
            match input {
                ColorInput::Png { path } => {
                    *path = absolute_existing_path(base, path)?;
                }
                ColorInput::PngSequence { paths } => {
                    for path in paths {
                        *path = absolute_existing_path(base, path)?;
                    }
                }
                ColorInput::Synthetic { .. } | ColorInput::Transparent => {}
            }
        }
        if let DepthInput::Png16 { path, .. } = &mut self.inputs.depth {
            *path = absolute_existing_path(base, path)?;
        }
        Ok(())
    }
}

pub fn resolve_path(base: &Path, path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        base.join(path)
    }
}

fn exact_len(label: &str, values: &[f32], expected: usize) -> Result<()> {
    if values.len() != expected {
        bail!(
            "{label} must contain {expected} f32 values ({} bytes), got {}",
            expected * 4,
            values.len()
        );
    }
    Ok(())
}

pub fn disabled_surface_feature_uniform(displacement: &[f32], revision: u32) -> Result<Vec<f32>> {
    exact_len(
        "projection.displacement_uniform",
        displacement,
        SURFACE_UNIFORM_V1_FLOATS,
    )?;
    let mut values = displacement.to_vec();
    values.extend_from_slice(&[
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        3.0,
        0.0,
        0.5,
        0.1,
        0.0,
        0.0,
        0.0,
        revision as f32,
        SURFACE_UNIFORM_V2_ABI_VERSION as f32,
        0.0,
    ]);
    Ok(values)
}

pub fn validate_surface_feature_uniform(surface: &[f32], displacement: &[f32]) -> Result<()> {
    exact_len(
        "projection.surface_feature_uniform",
        surface,
        SURFACE_UNIFORM_V2_FLOATS,
    )?;
    exact_len(
        "projection.displacement_uniform",
        displacement,
        SURFACE_UNIFORM_V1_FLOATS,
    )?;
    if surface.iter().any(|value| !value.is_finite()) {
        bail!("projection.surface_feature_uniform contains a non-finite value");
    }
    if surface[..SURFACE_UNIFORM_V1_FLOATS] != displacement[..] {
        bail!("projection.surface_feature_uniform prefix must exactly match displacement_uniform");
    }
    exact_token("projection.surface_feature_uniform[16]", surface[16], 1)?;
    exact_token("projection.surface_feature_uniform[17]", surface[17], 1)?;
    finite_range(
        "projection.surface_feature_uniform[18]",
        surface[18],
        0.0,
        0.45,
    )?;
    finite_range(
        "projection.surface_feature_uniform[19]",
        surface[19],
        0.0,
        1.0,
    )?;
    exact_token("projection.surface_feature_uniform[20]", surface[20], 1)?;
    exact_token("projection.surface_feature_uniform[21]", surface[21], 1)?;
    exact_token("projection.surface_feature_uniform[22]", surface[22], 4)?;
    exact_token("projection.surface_feature_uniform[23]", surface[23], 1)?;
    finite_range(
        "projection.surface_feature_uniform[24]",
        surface[24],
        0.0,
        1.0,
    )?;
    finite_range(
        "projection.surface_feature_uniform[25]",
        surface[25],
        0.001,
        0.5,
    )?;
    finite_range(
        "projection.surface_feature_uniform[26]",
        surface[26],
        0.0,
        1.0,
    )?;
    exact_token("projection.surface_feature_uniform[27]", surface[27], 1)?;
    exact_token("projection.surface_feature_uniform[28]", surface[28], 1)?;
    if surface[29].fract() != 0.0 || surface[29] < 0.0 || surface[29] > 16_777_216.0 {
        bail!("projection.surface_feature_uniform[29] must be an exact nonnegative revision");
    }
    if surface[30] != SURFACE_UNIFORM_V2_ABI_VERSION as f32 {
        bail!("projection.surface_feature_uniform[30] must declare ABI version 2");
    }
    if surface[31] != 0.0 {
        bail!("projection.surface_feature_uniform[31] is reserved and must be zero");
    }
    Ok(())
}

fn exact_token(label: &str, value: f32, maximum: u32) -> Result<()> {
    if value.fract() != 0.0 || value < 0.0 || value > maximum as f32 {
        bail!("{label} must be an exact token in 0..={maximum}");
    }
    Ok(())
}

fn finite_range(label: &str, value: f32, minimum: f32, maximum: f32) -> Result<()> {
    if !value.is_finite() || value < minimum || value > maximum {
        bail!("{label}={value} is outside {minimum}..={maximum}");
    }
    Ok(())
}

fn token_name<'a>(value: f32, names: &'a [&'a str]) -> &'a str {
    names.get(value as usize).copied().unwrap_or(names[0])
}

fn validate_outputs(outputs: &[OutputLayer]) -> Result<()> {
    if outputs.is_empty() {
        bail!("at least one output layer is required");
    }
    let mut names = RESERVED_GUIDE_OUTPUT_NAMES
        .into_iter()
        .collect::<BTreeSet<_>>();
    for output in outputs {
        if output.name.trim().is_empty() {
            bail!("output layer name must not be empty");
        }
        if !names.insert(output.name.as_str()) {
            bail!(
                "output layer {} collides with another or reserved guide output",
                output.name
            );
        }
        if !output.override_value.is_finite() {
            bail!("output layer {} has a non-finite override", output.name);
        }
    }
    Ok(())
}

fn absolute_existing_path(base: &Path, path: &Path) -> Result<PathBuf> {
    resolve_path(base, path)
        .canonicalize()
        .with_context(|| format!("failed to resolve replay artifact {}", path.display()))
}

fn validate_color_input(role: &str, input: &ColorInput, base: &Path) -> Result<()> {
    match input {
        ColorInput::Png { path } => validate_png_path(role, path, base),
        ColorInput::PngSequence { paths } => {
            if role != "video" {
                bail!("PNG sequences are supported only for the video input");
            }
            if paths.is_empty() || paths.len() > MAX_PNG_SEQUENCE_FRAMES {
                bail!(
                    "video PNG sequence frame count must be within 1..={MAX_PNG_SEQUENCE_FRAMES}"
                );
            }
            for path in paths {
                validate_png_path("video sequence", path, base)?;
            }
            Ok(())
        }
        ColorInput::Synthetic { .. } | ColorInput::Transparent => Ok(()),
    }
}

fn validate_png_path(role: &str, path: &Path, base: &Path) -> Result<()> {
    if path
        .extension()
        .and_then(|value| value.to_str())
        .is_none_or(|value| !value.eq_ignore_ascii_case("png"))
    {
        bail!("{role} input must be a PNG: {}", path.display());
    }
    let resolved = resolve_path(base, path);
    if !resolved.is_file() {
        bail!("{role} input does not exist: {}", resolved.display());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    #[test]
    fn public_capsule_contract_uses_exact_current_buffer_sizes() {
        assert_eq!(28 * 4, 112);
        assert_eq!(32 * 4, 128);
        assert_eq!(24 * 4, 96);
        assert_eq!(16 * 4, 64);
        assert_eq!(92 * 4, 368);
    }

    #[test]
    fn relative_paths_resolve_beside_capsule() {
        assert_eq!(
            resolve_path(Path::new("C:/capsules/run"), Path::new("shader.spv")),
            PathBuf::from("C:/capsules/run/shader.spv")
        );
    }

    #[test]
    fn png_sequence_is_bounded_and_video_only() {
        let one = ColorInput::PngSequence {
            paths: vec![PathBuf::from("frame.png")],
        };
        assert!(validate_color_input("camera_left", &one, Path::new(".")).is_err());

        let empty = ColorInput::PngSequence { paths: Vec::new() };
        assert!(validate_color_input("video", &empty, Path::new(".")).is_err());

        let too_many = ColorInput::PngSequence {
            paths: (0..=MAX_PNG_SEQUENCE_FRAMES)
                .map(|index| PathBuf::from(format!("frame-{index}.png")))
                .collect(),
        };
        assert!(validate_color_input("video", &too_many, Path::new(".")).is_err());
    }

    #[test]
    fn png_sequence_serializes_with_explicit_kind() {
        let value = serde_json::to_value(ColorInput::PngSequence {
            paths: vec![PathBuf::from("frame.png")],
        })
        .expect("serialize PNG sequence");
        assert_eq!(value["kind"], "png-sequence");
        assert_eq!(value["paths"][0], "frame.png");
    }

    #[test]
    fn requested_outputs_cannot_shadow_reserved_guide_exports() {
        let outputs = [OutputLayer {
            name: "guide-raw-brightness".to_string(),
            override_value: -1.0,
        }];
        assert!(validate_outputs(&outputs).is_err());
    }

    #[test]
    fn parsed_capsule_and_binding_digest_are_derived_from_the_same_injected_bytes() {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let dir = std::env::temp_dir().join(format!("hostess-bound-capsule-{nonce}"));
        fs::create_dir_all(&dir).expect("test directory");
        let shader_bytes = [
            3_u8, 2, 35, 7, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0,
        ];
        let shader_paths = (0..8)
            .map(|index| {
                let path = dir.join(format!("shader-{index}.spv"));
                fs::write(&path, shader_bytes).expect("shader");
                path
            })
            .collect::<Vec<_>>();
        let path = dir.join("capsule.json");
        let mut original = ReplayCapsule {
            schema: CAPSULE_SCHEMA.to_string(),
            name: "original-bytes".to_string(),
            extent: Extent {
                width: 4,
                height: 2,
            },
            shaders: ShaderBundle {
                fullscreen_vertex_spirv: shader_paths[0].clone(),
                guide_fragment_spirv: shader_paths[1..7].to_vec(),
                projection_fragment_spirv: shader_paths[7].clone(),
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
        };
        let original_bytes = serde_json::to_vec(&original).expect("original bytes");
        original.name = "replacement-bytes".to_string();
        fs::write(&path, serde_json::to_vec(&original).expect("replacement")).expect("replace");

        let loaded = ReplayCapsule::parse_bound_bytes(&path, &original_bytes).expect("bound load");
        assert_eq!(loaded.capsule.name, "original-bytes");
        assert_eq!(
            loaded.sha256,
            format!("{:x}", Sha256::digest(&original_bytes))
        );
        assert_ne!(
            loaded.sha256,
            format!(
                "{:x}",
                Sha256::digest(fs::read(&path).expect("replacement bytes"))
            )
        );
        let mut evidence_capsule = loaded.capsule;
        let legacy_evidence = evidence_capsule.surface_feature_evidence(true);
        assert!(!legacy_evidence.tiling.supported);
        assert_eq!(legacy_evidence.actual_uniform_bytes, 64);
        let mut surface =
            disabled_surface_feature_uniform(&evidence_capsule.projection.displacement_uniform, 2)
                .expect("surface");
        surface[16] = 1.0;
        surface[17] = 1.0;
        surface[21] = 1.0;
        surface[23] = 1.0;
        surface[26] = 0.5;
        surface[28] = 1.0;
        evidence_capsule.projection.surface_feature_uniform = Some(surface);
        let requested = evidence_capsule.surface_feature_evidence(false);
        assert!(requested.tiling.requested);
        assert!(requested.tiling.supported);
        assert!(!requested.tiling.effective);
        assert!(requested.inner_alpha.requested);
        let rendered = evidence_capsule.surface_feature_evidence(true);
        assert!(rendered.tiling.effective);
        assert!(rendered.inner_alpha.effective);
        assert_eq!(
            rendered.marker_fields["projectionInnerAlphaStretchPolicy"],
            "opaque-independent"
        );
        assert_eq!(
            rendered.marker_fields["projectionInnerAlphaStretchObeysExactProjectionMask"],
            "true"
        );
        assert_eq!(
            rendered.marker_fields["projectionSurfaceFeatureUniformAbiProvided"],
            "2"
        );
        fs::remove_dir_all(dir).expect("cleanup");
    }

    #[test]
    fn additive_surface_uniform_preserves_the_prefix_and_exact_disabled_identity() {
        let displacement = vec![0.0; SURFACE_UNIFORM_V1_FLOATS];
        let surface = disabled_surface_feature_uniform(&displacement, 7).expect("uniform");
        validate_surface_feature_uniform(&surface, &displacement).expect("valid v2");
        assert_eq!(&surface[..16], displacement.as_slice());
        assert_eq!(&surface[16..20], &[0.0, 0.0, 0.0, 1.0]);
        assert_eq!(&surface[20..24], &[0.0, 0.0, 3.0, 0.0]);
        assert_eq!(&surface[24..29], &[0.5, 0.1, 0.0, 0.0, 0.0]);
        assert_eq!(&surface[29..], &[7.0, 2.0, 0.0]);
    }

    #[test]
    fn additive_surface_uniform_rejects_prefix_abi_and_reserved_damage() {
        let displacement = vec![0.0; SURFACE_UNIFORM_V1_FLOATS];
        let baseline = disabled_surface_feature_uniform(&displacement, 0).expect("uniform");
        for (index, value) in [(0, 1.0), (30, 1.0), (31, 1.0)] {
            let mut damaged = baseline.clone();
            damaged[index] = value;
            assert!(
                validate_surface_feature_uniform(&damaged, &displacement).is_err(),
                "index {index}"
            );
        }
    }
}
