use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    io::Read,
    path::{Component, Path, PathBuf},
};

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};

use crate::capsule::Extent;

pub const CAPSULE_V2_SCHEMA: &str = "rusty.hostess.projection_replay_capsule.v2";
pub const EXECUTION_PLAN_SCHEMA: &str = "rusty.hostess.projection_replay_execution_plan.v1";

const MAX_RESOURCES: usize = 64;
const MAX_PASSES: usize = 64;
const MAX_BINDINGS_PER_PASS: usize = 32;
const MAX_PUSH_RANGES_PER_PASS: usize = 8;
const MAX_EXPORTS: usize = 32;
const MAX_BUFFER_BYTES: u64 = 64 * 1024 * 1024;
const MAX_PUSH_BYTES: u32 = 256;
const MAX_SHADER_BYTES: u64 = 16 * 1024 * 1024;
const MAX_DESCRIPTOR_SET: u32 = 5;
const MAX_DESCRIPTOR_BINDING: u32 = 8;
const MAX_PROVIDER_LABEL_BYTES: usize = 256;
const SPIRV_MAGIC: u32 = 0x0723_0203;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReplayCapsuleV2 {
    pub schema: String,
    pub name: String,
    pub extent: Extent,
    #[serde(default)]
    pub provider_labels: BTreeMap<String, String>,
    pub resources: Vec<DeclaredResource>,
    pub passes: Vec<DeclaredPass>,
    pub exports: Vec<DeclaredExport>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DeclaredResource {
    pub id: String,
    #[serde(flatten)]
    pub resource: ResourceDeclaration,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "kebab-case", deny_unknown_fields)]
pub enum ResourceDeclaration {
    Image {
        format: ImageFormat,
        #[serde(default)]
        external: bool,
    },
    Buffer {
        byte_size: u64,
        #[serde(default)]
        external: bool,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum ImageFormat {
    Rgba8Unorm,
    R32Sfloat,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DeclaredPass {
    pub id: String,
    #[serde(default)]
    pub provider_label: Option<String>,
    #[serde(default)]
    pub dependencies: Vec<String>,
    pub shaders: Vec<ShaderArtifact>,
    #[serde(default)]
    pub descriptor_bindings: Vec<DescriptorBinding>,
    #[serde(default)]
    pub push_ranges: Vec<PushRange>,
    #[serde(default)]
    pub scissors: BTreeMap<String, Vec<f32>>,
    pub render_targets: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ShaderArtifact {
    pub stage: ShaderStage,
    pub path: PathBuf,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum ShaderStage {
    Vertex,
    Fragment,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DescriptorBinding {
    pub set: u32,
    pub binding: u32,
    pub descriptor_type: DescriptorType,
    pub stages: Vec<ShaderStage>,
    pub resource: String,
    #[serde(default)]
    pub byte_size: Option<u64>,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum DescriptorType {
    CombinedImageSampler,
    UniformBuffer,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PushRange {
    pub offset: u32,
    pub byte_size: u32,
    pub stages: Vec<ShaderStage>,
    pub values: Vec<f32>,
    #[serde(default)]
    pub view_values: BTreeMap<String, Vec<f32>>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DeclaredExport {
    pub name: String,
    pub resource: String,
    #[serde(default)]
    pub provider_label: Option<String>,
    #[serde(default)]
    pub output_override: Option<f32>,
}

#[derive(Clone, Debug, Serialize, PartialEq)]
pub struct ReplayExecutionPlan {
    pub schema: &'static str,
    pub source_schema: String,
    pub name: String,
    pub extent: Extent,
    pub provider_labels: BTreeMap<String, String>,
    pub resources: Vec<PlanResource>,
    pub passes: Vec<PlanPass>,
    pub exports: Vec<PlanExport>,
}

#[derive(Clone, Debug, Serialize, PartialEq)]
pub struct PlanResource {
    pub id: String,
    pub kind: String,
    pub format: Option<String>,
    pub byte_size: Option<u64>,
    pub external: bool,
}

#[derive(Clone, Debug, Serialize, PartialEq)]
pub struct PlanPass {
    pub id: String,
    pub provider_label: Option<String>,
    pub dependencies: Vec<String>,
    pub shaders: Vec<PlanShader>,
    pub descriptor_bindings: Vec<PlanDescriptorBinding>,
    pub push_ranges: Vec<PushRange>,
    pub scissors: BTreeMap<String, Vec<f32>>,
    pub render_targets: Vec<String>,
}

#[derive(Clone, Debug, Serialize, PartialEq)]
pub struct PlanShader {
    pub stage: ShaderStage,
    pub path: PathBuf,
}

#[derive(Clone, Debug, Serialize, PartialEq)]
pub struct PlanDescriptorBinding {
    pub set: u32,
    pub binding: u32,
    pub descriptor_type: DescriptorType,
    pub stages: Vec<ShaderStage>,
    pub resource: String,
    pub byte_size: Option<u64>,
}

#[derive(Clone, Debug, Serialize, PartialEq)]
pub struct PlanExport {
    pub name: String,
    pub resource: String,
    pub provider_label: Option<String>,
    pub output_override: Option<f32>,
}

impl ReplayCapsuleV2 {
    pub fn read(path: &Path) -> Result<Self> {
        let bytes = fs::read(path)
            .with_context(|| format!("failed to read replay capsule {}", path.display()))?;
        let capsule: Self = serde_json::from_slice(&bytes)
            .with_context(|| format!("invalid v2 replay capsule JSON {}", path.display()))?;
        capsule.validate(path)?;
        Ok(capsule)
    }

    pub fn validate(&self, capsule_path: &Path) -> Result<()> {
        self.normalize(capsule_path).map(|_| ())
    }

    pub fn normalize(&self, capsule_path: &Path) -> Result<ReplayExecutionPlan> {
        if self.schema != CAPSULE_V2_SCHEMA {
            bail!(
                "unsupported capsule schema {}; expected {}",
                self.schema,
                CAPSULE_V2_SCHEMA
            );
        }
        validate_identity("capsule name", &self.name)?;
        validate_extent(self.extent)?;
        if self.resources.is_empty() || self.resources.len() > MAX_RESOURCES {
            bail!("resource count must be within 1..={MAX_RESOURCES}");
        }
        if self.passes.is_empty() || self.passes.len() > MAX_PASSES {
            bail!("pass count must be within 1..={MAX_PASSES}");
        }
        if self.exports.is_empty() || self.exports.len() > MAX_EXPORTS {
            bail!("export count must be within 1..={MAX_EXPORTS}");
        }
        for (key, value) in &self.provider_labels {
            validate_identity("provider label key", key)?;
            validate_provider_label("provider label", value)?;
        }

        let mut resources = BTreeMap::new();
        for resource in &self.resources {
            validate_identity("resource id", &resource.id)?;
            if resources.insert(resource.id.as_str(), resource).is_some() {
                bail!("duplicate resource id {}", resource.id);
            }
            if let ResourceDeclaration::Buffer { byte_size, .. } = resource.resource {
                if byte_size == 0 || byte_size > MAX_BUFFER_BYTES || byte_size % 4 != 0 {
                    bail!(
                        "buffer {} byte_size must be aligned and within 4..={MAX_BUFFER_BYTES}",
                        resource.id
                    );
                }
            }
        }

        let base = capsule_path.parent().unwrap_or_else(|| Path::new("."));
        let mut passes = BTreeMap::new();
        for pass in &self.passes {
            validate_identity("pass id", &pass.id)?;
            if passes.insert(pass.id.as_str(), pass).is_some() {
                bail!("duplicate pass id {}", pass.id);
            }
            validate_pass(pass, &resources, base)?;
        }
        for pass in &self.passes {
            let mut dependencies = BTreeSet::new();
            for dependency in &pass.dependencies {
                if dependency == &pass.id {
                    bail!("pass {} depends on itself", pass.id);
                }
                if !passes.contains_key(dependency.as_str()) {
                    bail!("pass {} has missing dependency {}", pass.id, dependency);
                }
                if !dependencies.insert(dependency) {
                    bail!("pass {} repeats dependency {}", pass.id, dependency);
                }
            }
        }

        let ordered_ids = topological_order(&passes)?;
        validate_resource_flow(&ordered_ids, &passes, &resources)?;
        let mut export_names = BTreeSet::new();
        for export in &self.exports {
            validate_identity("export name", &export.name)?;
            if let Some(label) = &export.provider_label {
                validate_provider_label("export provider label", label)?;
            }
            if !export_names.insert(export.name.as_str()) {
                bail!("duplicate export name {}", export.name);
            }
            if !resources.contains_key(export.resource.as_str()) {
                bail!(
                    "export {} references missing resource {}",
                    export.name,
                    export.resource
                );
            }
            if export
                .output_override
                .is_some_and(|value| !value.is_finite())
            {
                bail!("export {} has a non-finite output_override", export.name);
            }
        }

        Ok(ReplayExecutionPlan {
            schema: EXECUTION_PLAN_SCHEMA,
            source_schema: self.schema.clone(),
            name: self.name.clone(),
            extent: self.extent,
            provider_labels: self.provider_labels.clone(),
            resources: resources
                .values()
                .map(|resource| match &resource.resource {
                    ResourceDeclaration::Image {
                        format, external, ..
                    } => PlanResource {
                        id: resource.id.clone(),
                        kind: "image".to_string(),
                        format: Some(format_name(*format).to_string()),
                        byte_size: None,
                        external: *external,
                    },
                    ResourceDeclaration::Buffer {
                        byte_size,
                        external,
                    } => PlanResource {
                        id: resource.id.clone(),
                        kind: "buffer".to_string(),
                        format: None,
                        byte_size: Some(*byte_size),
                        external: *external,
                    },
                })
                .collect(),
            passes: ordered_ids
                .iter()
                .map(|id| normalize_pass(passes[id.as_str()]))
                .collect(),
            exports: {
                let mut exports = self
                    .exports
                    .iter()
                    .map(|export| PlanExport {
                        name: export.name.clone(),
                        resource: export.resource.clone(),
                        provider_label: export.provider_label.clone(),
                        output_override: export.output_override,
                    })
                    .collect::<Vec<_>>();
                exports.sort_by(|left, right| left.name.cmp(&right.name));
                exports
            },
        })
    }
}

fn validate_pass(
    pass: &DeclaredPass,
    resources: &BTreeMap<&str, &DeclaredResource>,
    base: &Path,
) -> Result<()> {
    if let Some(label) = &pass.provider_label {
        validate_provider_label("pass provider label", label)?;
    }
    if pass.shaders.len() != 2 {
        bail!(
            "pass {} must declare exactly one vertex and one fragment shader",
            pass.id
        );
    }
    let mut shader_stages = BTreeSet::new();
    for shader in &pass.shaders {
        if !shader_stages.insert(stage_rank(shader.stage)) {
            bail!("pass {} repeats a shader stage", pass.id);
        }
        validate_relative_artifact_path(&pass.id, &shader.path, base)?;
    }
    if !shader_stages.contains(&stage_rank(ShaderStage::Vertex))
        || !shader_stages.contains(&stage_rank(ShaderStage::Fragment))
    {
        bail!(
            "pass {} must declare exactly one vertex and one fragment shader",
            pass.id
        );
    }
    if pass.descriptor_bindings.len() > MAX_BINDINGS_PER_PASS {
        bail!("pass {} has excessive descriptor bindings", pass.id);
    }
    let mut binding_keys = BTreeSet::new();
    for binding in &pass.descriptor_bindings {
        if binding.set > MAX_DESCRIPTOR_SET || binding.binding > MAX_DESCRIPTOR_BINDING {
            bail!(
                "pass {} descriptor binding {}:{} exceeds supported maxima {}:{}",
                pass.id,
                binding.set,
                binding.binding,
                MAX_DESCRIPTOR_SET,
                MAX_DESCRIPTOR_BINDING
            );
        }
        if !binding_keys.insert((binding.set, binding.binding)) {
            bail!(
                "pass {} has duplicate descriptor binding {}:{}",
                pass.id,
                binding.set,
                binding.binding
            );
        }
        let resource = resources.get(binding.resource.as_str()).ok_or_else(|| {
            anyhow::anyhow!(
                "pass {} binding {}:{} references missing resource {}",
                pass.id,
                binding.set,
                binding.binding,
                binding.resource
            )
        })?;
        validate_stages(&pass.id, &binding.stages)?;
        validate_stage_subset(&pass.id, &binding.stages, &shader_stages)?;
        match (&binding.descriptor_type, &resource.resource) {
            (DescriptorType::CombinedImageSampler, ResourceDeclaration::Image { .. }) => {
                if binding.byte_size.is_some() {
                    bail!(
                        "image binding in pass {} must not declare byte_size",
                        pass.id
                    );
                }
            }
            (DescriptorType::UniformBuffer, ResourceDeclaration::Buffer { byte_size, .. }) => {
                if binding.byte_size != Some(*byte_size) {
                    bail!(
                        "pass {} buffer binding byte-size mismatch for {}",
                        pass.id,
                        binding.resource
                    );
                }
            }
            _ => bail!(
                "pass {} descriptor type does not match resource {}",
                pass.id,
                binding.resource
            ),
        }
    }
    if pass.push_ranges.len() > MAX_PUSH_RANGES_PER_PASS {
        bail!("pass {} has excessive push ranges", pass.id);
    }
    let mut occupied = Vec::new();
    for range in &pass.push_ranges {
        if range.byte_size == 0
            || range.offset % 4 != 0
            || range.byte_size % 4 != 0
            || range.offset.saturating_add(range.byte_size) > MAX_PUSH_BYTES
        {
            bail!(
                "pass {} has a misaligned or out-of-range push range",
                pass.id
            );
        }
        if range.values.len() * 4 != range.byte_size as usize {
            bail!("pass {} has a push-range byte-size mismatch", pass.id);
        }
        if range.values.iter().any(|value| !value.is_finite()) {
            bail!("pass {} push range contains a non-finite value", pass.id);
        }
        for (view, values) in &range.view_values {
            validate_identity("push-range view", view)?;
            if values.len() * 4 != range.byte_size as usize {
                bail!("pass {} has a view push-range byte-size mismatch", pass.id);
            }
            if values.iter().any(|value| !value.is_finite()) {
                bail!(
                    "pass {} view push range contains a non-finite value",
                    pass.id
                );
            }
        }
        validate_stages(&pass.id, &range.stages)?;
        validate_stage_subset(&pass.id, &range.stages, &shader_stages)?;
        let end = range.offset + range.byte_size;
        if occupied
            .iter()
            .any(|(start, previous_end)| range.offset < *previous_end && end > *start)
        {
            bail!("pass {} has overlapping push ranges", pass.id);
        }
        occupied.push((range.offset, end));
    }
    for (view, scissor) in &pass.scissors {
        validate_identity("scissor view", view)?;
        if scissor.len() != 4 || scissor.iter().any(|value| !value.is_finite()) {
            bail!("pass {} has an invalid scissor for view {view}", pass.id);
        }
    }
    if pass.render_targets.is_empty() || pass.render_targets.len() > 8 {
        bail!("pass {} render target count must be within 1..=8", pass.id);
    }
    let mut targets = BTreeSet::new();
    for target in &pass.render_targets {
        if !targets.insert(target) {
            bail!("pass {} repeats render target {}", pass.id, target);
        }
        match resources.get(target.as_str()).map(|value| &value.resource) {
            Some(ResourceDeclaration::Image {
                format: ImageFormat::Rgba8Unorm,
                external: false,
            }) => {}
            Some(_) => bail!("pass {} has unsupported render target {}", pass.id, target),
            None => bail!("pass {} has missing render target {}", pass.id, target),
        }
    }
    Ok(())
}

fn topological_order(passes: &BTreeMap<&str, &DeclaredPass>) -> Result<Vec<String>> {
    let mut remaining = passes.keys().copied().collect::<BTreeSet<_>>();
    let mut completed = BTreeSet::new();
    let mut ordered = Vec::with_capacity(passes.len());
    while !remaining.is_empty() {
        let ready = remaining
            .iter()
            .copied()
            .filter(|id| {
                passes[id]
                    .dependencies
                    .iter()
                    .all(|dependency| completed.contains(dependency.as_str()))
            })
            .collect::<Vec<_>>();
        if ready.is_empty() {
            bail!("pass dependency graph contains a cycle");
        }
        for id in ready {
            remaining.remove(id);
            completed.insert(id);
            ordered.push(id.to_string());
        }
    }
    Ok(ordered)
}

fn validate_resource_flow(
    ordered_ids: &[String],
    passes: &BTreeMap<&str, &DeclaredPass>,
    resources: &BTreeMap<&str, &DeclaredResource>,
) -> Result<()> {
    let mut writers: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for pass in passes.values() {
        for target in &pass.render_targets {
            writers
                .entry(target.as_str())
                .or_default()
                .push(pass.id.as_str());
        }
    }
    for (resource, resource_writers) in &writers {
        if resource_writers.len() > 1 {
            bail!(
                "resource {resource} has multiple writers; ordered multiple writes are unsupported"
            );
        }
    }
    let mut initialized = resources
        .iter()
        .filter_map(|(id, resource)| match resource.resource {
            ResourceDeclaration::Image { external: true, .. }
            | ResourceDeclaration::Buffer { external: true, .. } => Some(*id),
            _ => None,
        })
        .collect::<BTreeSet<_>>();
    for id in ordered_ids {
        let pass = passes[id.as_str()];
        for binding in &pass.descriptor_bindings {
            if !initialized.contains(binding.resource.as_str()) {
                bail!(
                    "pass {} reads resource {} before it is written",
                    pass.id,
                    binding.resource
                );
            }
            let resource = resources[binding.resource.as_str()];
            let external = match resource.resource {
                ResourceDeclaration::Image { external, .. }
                | ResourceDeclaration::Buffer { external, .. } => external,
            };
            if !external {
                let producers = &writers[binding.resource.as_str()];
                if !producers
                    .iter()
                    .any(|producer| depends_transitively(pass.id.as_str(), producer, passes))
                {
                    bail!(
                        "pass {} reads internal resource {} without a transitive dependency on its producer",
                        pass.id,
                        binding.resource
                    );
                }
            }
        }
        initialized.extend(pass.render_targets.iter().map(String::as_str));
    }
    for (id, resource) in resources {
        let external = match resource.resource {
            ResourceDeclaration::Image { external, .. }
            | ResourceDeclaration::Buffer { external, .. } => external,
        };
        if !external && !writers.contains_key(id) {
            bail!("resource {id} has no producer");
        }
    }
    Ok(())
}

fn depends_transitively(start: &str, target: &str, passes: &BTreeMap<&str, &DeclaredPass>) -> bool {
    let mut pending = vec![start];
    let mut visited = BTreeSet::new();
    while let Some(id) = pending.pop() {
        if !visited.insert(id) {
            continue;
        }
        for dependency in &passes[id].dependencies {
            if dependency == target {
                return true;
            }
            pending.push(dependency);
        }
    }
    false
}

fn normalize_pass(pass: &DeclaredPass) -> PlanPass {
    let mut dependencies = pass.dependencies.clone();
    dependencies.sort();
    let mut shaders = pass
        .shaders
        .iter()
        .map(|shader| PlanShader {
            stage: shader.stage,
            path: shader.path.clone(),
        })
        .collect::<Vec<_>>();
    shaders.sort_by_key(|shader| stage_rank(shader.stage));
    let mut descriptor_bindings = pass
        .descriptor_bindings
        .iter()
        .map(|binding| {
            let mut stages = binding.stages.clone();
            stages.sort_by_key(|stage| stage_rank(*stage));
            PlanDescriptorBinding {
                set: binding.set,
                binding: binding.binding,
                descriptor_type: binding.descriptor_type,
                stages,
                resource: binding.resource.clone(),
                byte_size: binding.byte_size,
            }
        })
        .collect::<Vec<_>>();
    descriptor_bindings.sort_by_key(|binding| (binding.set, binding.binding));
    let mut push_ranges = pass.push_ranges.clone();
    for range in &mut push_ranges {
        range.stages.sort_by_key(|stage| stage_rank(*stage));
    }
    push_ranges.sort_by_key(|range| range.offset);
    PlanPass {
        id: pass.id.clone(),
        provider_label: pass.provider_label.clone(),
        dependencies,
        shaders,
        descriptor_bindings,
        push_ranges,
        scissors: pass.scissors.clone(),
        render_targets: pass.render_targets.clone(),
    }
}

fn validate_relative_artifact_path(pass: &str, path: &Path, base: &Path) -> Result<()> {
    if path.is_absolute()
        || path.components().any(|component| {
            matches!(
                component,
                Component::ParentDir | Component::RootDir | Component::Prefix(_)
            )
        })
    {
        bail!("pass {pass} shader path must be relative and traversal-free");
    }
    if path
        .extension()
        .and_then(|value| value.to_str())
        .is_none_or(|value| !value.eq_ignore_ascii_case("spv"))
    {
        bail!("pass {pass} shader path must reference .spv");
    }
    let resolved = base.join(path);
    let metadata = fs::metadata(&resolved)
        .with_context(|| format!("missing pass {pass} shader artifact {}", resolved.display()))?;
    if metadata.len() < 20 || metadata.len() > MAX_SHADER_BYTES || metadata.len() % 4 != 0 {
        bail!("pass {pass} shader artifact is not valid-sized SPIR-V");
    }
    let mut header = [0_u8; 20];
    fs::File::open(&resolved)
        .with_context(|| {
            format!(
                "failed to open pass {pass} shader artifact {}",
                resolved.display()
            )
        })?
        .read_exact(&mut header)
        .with_context(|| {
            format!(
                "failed to read pass {pass} shader header {}",
                resolved.display()
            )
        })?;
    let words = header
        .chunks_exact(4)
        .map(|bytes| u32::from_le_bytes(bytes.try_into().expect("four-byte SPIR-V word")))
        .collect::<Vec<_>>();
    let version = words[1];
    if words[0] != SPIRV_MAGIC
        || !(0x0001_0000..=0x0001_0600).contains(&version)
        || version & 0xff != 0
        || words[3] == 0
        || words[4] != 0
    {
        bail!("pass {pass} shader artifact has an invalid SPIR-V header");
    }
    Ok(())
}

fn validate_stages(pass: &str, stages: &[ShaderStage]) -> Result<()> {
    if stages.is_empty() {
        bail!("pass {pass} has an empty stage list");
    }
    let mut seen = BTreeSet::new();
    if stages.iter().any(|stage| !seen.insert(stage_rank(*stage))) {
        bail!("pass {pass} repeats a stage");
    }
    Ok(())
}

fn validate_stage_subset(
    pass: &str,
    stages: &[ShaderStage],
    shader_stages: &BTreeSet<u8>,
) -> Result<()> {
    if stages
        .iter()
        .any(|stage| !shader_stages.contains(&stage_rank(*stage)))
    {
        bail!("pass {pass} declares visibility for an undeclared shader stage");
    }
    Ok(())
}

fn validate_provider_label(label: &str, value: &str) -> Result<()> {
    if value.len() > MAX_PROVIDER_LABEL_BYTES {
        bail!("{label} exceeds {MAX_PROVIDER_LABEL_BYTES} bytes");
    }
    Ok(())
}

fn validate_identity(label: &str, value: &str) -> Result<()> {
    if value.is_empty()
        || value.len() > 128
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.'))
    {
        bail!("{label} must be a bounded portable identifier");
    }
    Ok(())
}

fn validate_extent(extent: Extent) -> Result<()> {
    if extent.width < 2
        || extent.height < 2
        || extent.width > 8192
        || extent.height > 8192
        || !extent.width.is_multiple_of(2)
    {
        bail!("extent must be even-width and within 2..=8192");
    }
    Ok(())
}

fn stage_rank(stage: ShaderStage) -> u8 {
    match stage {
        ShaderStage::Vertex => 0,
        ShaderStage::Fragment => 1,
    }
}

fn format_name(format: ImageFormat) -> &'static str {
    match format {
        ImageFormat::Rgba8Unorm => "rgba8-unorm",
        ImageFormat::R32Sfloat => "r32-sfloat",
    }
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    fn test_dir() -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let path = std::env::temp_dir().join(format!("hostess-replay-plan-{nonce}"));
        fs::create_dir_all(&path).expect("create test directory");
        write_spirv(
            &path.join("vertex.spv"),
            [SPIRV_MAGIC, 0x0001_0000, 0, 1, 0],
        );
        write_spirv(
            &path.join("fragment.spv"),
            [SPIRV_MAGIC, 0x0001_0600, 0, 1, 0],
        );
        path
    }

    fn write_spirv(path: &Path, header: [u32; 5]) {
        let bytes = header
            .into_iter()
            .flat_map(u32::to_le_bytes)
            .collect::<Vec<_>>();
        fs::write(path, bytes).expect("write SPIR-V");
    }

    fn shader(stage: ShaderStage, name: &str) -> ShaderArtifact {
        ShaderArtifact {
            stage,
            path: PathBuf::from(name),
        }
    }

    fn neutral_capsule() -> ReplayCapsuleV2 {
        ReplayCapsuleV2 {
            schema: CAPSULE_V2_SCHEMA.to_string(),
            name: "neutral-conformance".to_string(),
            extent: Extent {
                width: 64,
                height: 32,
            },
            provider_labels: BTreeMap::from([(
                "suite".to_string(),
                "independent-neutral-provider".to_string(),
            )]),
            resources: vec![
                DeclaredResource {
                    id: "source".to_string(),
                    resource: ResourceDeclaration::Image {
                        format: ImageFormat::Rgba8Unorm,
                        external: true,
                    },
                },
                DeclaredResource {
                    id: "middle".to_string(),
                    resource: ResourceDeclaration::Image {
                        format: ImageFormat::Rgba8Unorm,
                        external: false,
                    },
                },
                DeclaredResource {
                    id: "result".to_string(),
                    resource: ResourceDeclaration::Image {
                        format: ImageFormat::Rgba8Unorm,
                        external: false,
                    },
                },
            ],
            passes: vec![
                DeclaredPass {
                    id: "z-producer".to_string(),
                    provider_label: Some("first".to_string()),
                    dependencies: Vec::new(),
                    shaders: vec![
                        shader(ShaderStage::Fragment, "fragment.spv"),
                        shader(ShaderStage::Vertex, "vertex.spv"),
                    ],
                    descriptor_bindings: vec![DescriptorBinding {
                        set: 0,
                        binding: 0,
                        descriptor_type: DescriptorType::CombinedImageSampler,
                        stages: vec![ShaderStage::Fragment],
                        resource: "source".to_string(),
                        byte_size: None,
                    }],
                    push_ranges: vec![PushRange {
                        offset: 0,
                        byte_size: 4,
                        stages: vec![ShaderStage::Fragment],
                        values: vec![1.0],
                        view_values: BTreeMap::new(),
                    }],
                    scissors: BTreeMap::new(),
                    render_targets: vec!["middle".to_string()],
                },
                DeclaredPass {
                    id: "a-consumer".to_string(),
                    provider_label: Some("second".to_string()),
                    dependencies: vec!["z-producer".to_string()],
                    shaders: vec![
                        shader(ShaderStage::Fragment, "fragment.spv"),
                        shader(ShaderStage::Vertex, "vertex.spv"),
                    ],
                    descriptor_bindings: vec![DescriptorBinding {
                        set: 0,
                        binding: 0,
                        descriptor_type: DescriptorType::CombinedImageSampler,
                        stages: vec![ShaderStage::Fragment],
                        resource: "middle".to_string(),
                        byte_size: None,
                    }],
                    push_ranges: Vec::new(),
                    scissors: BTreeMap::new(),
                    render_targets: vec!["result".to_string()],
                },
            ],
            exports: vec![DeclaredExport {
                name: "neutral-result".to_string(),
                resource: "result".to_string(),
                provider_label: Some("opaque-output".to_string()),
                output_override: None,
            }],
        }
    }

    #[test]
    fn neutral_v2_graph_normalizes_deterministically() {
        let dir = test_dir();
        let path = dir.join("capsule.json");
        let capsule = neutral_capsule();
        let first = capsule.normalize(&path).expect("normalize neutral graph");
        let second = capsule
            .normalize(&path)
            .expect("normalize neutral graph again");
        assert_eq!(first, second);
        assert_eq!(
            first
                .passes
                .iter()
                .map(|pass| pass.id.as_str())
                .collect::<Vec<_>>(),
            vec!["z-producer", "a-consumer"]
        );
        assert_eq!(
            first.provider_labels["suite"],
            "independent-neutral-provider"
        );
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn independent_passes_use_lexical_dependency_order() {
        let dir = test_dir();
        let path = dir.join("capsule.json");
        let mut capsule = neutral_capsule();
        capsule.passes[1].dependencies.clear();
        capsule.passes[1].descriptor_bindings[0].resource = "source".to_string();
        let plan = capsule
            .normalize(&path)
            .expect("normalize independent passes");
        assert_eq!(plan.passes[0].id, "a-consumer");
        assert_eq!(plan.passes[1].id, "z-producer");
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn damaged_graphs_fail_closed() {
        let dir = test_dir();
        let path = dir.join("capsule.json");

        let mut missing = neutral_capsule();
        missing.passes[1].descriptor_bindings[0].resource = "absent".to_string();
        assert!(missing.normalize(&path).is_err());

        let mut cycle = neutral_capsule();
        cycle.passes[0].dependencies.push("a-consumer".to_string());
        assert!(cycle.normalize(&path).is_err());

        let mut read_before_write = neutral_capsule();
        read_before_write.passes[1].dependencies.clear();
        assert!(read_before_write.normalize(&path).is_err());

        let mut duplicate_binding = neutral_capsule();
        let repeated_binding = duplicate_binding.passes[0].descriptor_bindings[0].clone();
        duplicate_binding.passes[0]
            .descriptor_bindings
            .push(repeated_binding);
        assert!(duplicate_binding.normalize(&path).is_err());

        let mut traversal = neutral_capsule();
        traversal.passes[0].shaders[0].path = PathBuf::from("../private.spv");
        assert!(traversal.normalize(&path).is_err());

        let mut non_finite = neutral_capsule();
        non_finite.passes[0].push_ranges[0].values[0] = f32::NAN;
        assert!(non_finite.normalize(&path).is_err());

        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn internal_read_requires_explicit_transitive_producer_dependency() {
        let dir = test_dir();
        let path = dir.join("capsule.json");
        let mut capsule = neutral_capsule();
        capsule.passes[0].id = "a-producer".to_string();
        capsule.passes[1].id = "z-consumer".to_string();
        capsule.passes[1].dependencies.clear();
        let error = capsule
            .normalize(&path)
            .expect_err("lexical producer order must not imply a dependency");
        assert!(error
            .to_string()
            .contains("without a transitive dependency"));

        capsule.passes[1].dependencies = vec!["a-producer".to_string()];
        capsule
            .normalize(&path)
            .expect("explicit producer dependency is accepted");
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn ordered_multiple_writes_remain_rejected() {
        let dir = test_dir();
        let path = dir.join("capsule.json");
        let mut capsule = neutral_capsule();
        capsule.passes[1].render_targets = vec!["middle".to_string()];
        let error = capsule
            .normalize(&path)
            .expect_err("multiple writers must fail even when ordered");
        assert!(error.to_string().contains("multiple writers"));
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn visibility_must_be_declared_by_pass_shaders() {
        let dir = test_dir();
        let path = dir.join("capsule.json");
        let fragment_only = BTreeSet::from([stage_rank(ShaderStage::Fragment)]);
        assert!(validate_stage_subset("pass", &[ShaderStage::Vertex], &fragment_only).is_err());
        assert!(validate_stage_subset("pass", &[ShaderStage::Fragment], &fragment_only).is_ok());

        let mut capsule = neutral_capsule();
        capsule.passes[0].descriptor_bindings[0].stages = vec![ShaderStage::Vertex];
        capsule.passes[0].push_ranges[0].stages = vec![ShaderStage::Vertex];
        capsule
            .normalize(&path)
            .expect("declared vertex visibility is accepted");
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn v2_pass_requires_exactly_one_vertex_and_fragment_shader() {
        let dir = test_dir();
        let path = dir.join("capsule.json");

        let mut missing_vertex = neutral_capsule();
        missing_vertex.passes[0]
            .shaders
            .retain(|shader| shader.stage == ShaderStage::Fragment);
        assert!(missing_vertex.normalize(&path).is_err());

        let mut duplicate_vertex = neutral_capsule();
        duplicate_vertex.passes[0].shaders[0].stage = ShaderStage::Vertex;
        assert!(duplicate_vertex.normalize(&path).is_err());

        neutral_capsule()
            .normalize(&path)
            .expect("one vertex and one fragment shader");
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn descriptor_indices_are_bounded_to_supported_vocabulary() {
        let dir = test_dir();
        let path = dir.join("capsule.json");
        let mut maximum = neutral_capsule();
        maximum.passes[0].descriptor_bindings[0].set = MAX_DESCRIPTOR_SET;
        maximum.passes[0].descriptor_bindings[0].binding = MAX_DESCRIPTOR_BINDING;
        maximum.normalize(&path).expect("supported maxima");

        let mut excessive_set = neutral_capsule();
        excessive_set.passes[0].descriptor_bindings[0].set = MAX_DESCRIPTOR_SET + 1;
        assert!(excessive_set.normalize(&path).is_err());

        let mut excessive_binding = neutral_capsule();
        excessive_binding.passes[0].descriptor_bindings[0].binding = MAX_DESCRIPTOR_BINDING + 1;
        assert!(excessive_binding.normalize(&path).is_err());
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn spirv_five_word_header_is_validated() {
        let dir = test_dir();
        let path = dir.join("capsule.json");
        neutral_capsule()
            .normalize(&path)
            .expect("supported 1.0 and 1.6 headers");

        for (name, header) in [
            ("magic", [0, 0x0001_0000, 0, 1, 0]),
            ("version", [SPIRV_MAGIC, 0x0001_0700, 0, 1, 0]),
            ("bound", [SPIRV_MAGIC, 0x0001_0000, 0, 0, 0]),
            ("reserved", [SPIRV_MAGIC, 0x0001_0000, 0, 1, 1]),
        ] {
            write_spirv(&dir.join("vertex.spv"), header);
            assert!(
                neutral_capsule().normalize(&path).is_err(),
                "damaged {name} header must fail"
            );
        }

        write_spirv(&dir.join("vertex.spv"), [SPIRV_MAGIC, 0x0001_0000, 0, 1, 0]);
        write_spirv(
            &dir.join("fragment.spv"),
            [SPIRV_MAGIC, 0x0001_0600, 0, 1, 0],
        );
        fs::OpenOptions::new()
            .write(true)
            .open(dir.join("fragment.spv"))
            .expect("open oversized shader")
            .set_len(MAX_SHADER_BYTES + 4)
            .expect("extend oversized shader");
        let error = neutral_capsule()
            .normalize(&path)
            .expect_err("oversized SPIR-V must fail");
        assert!(error.to_string().contains("valid-sized SPIR-V"));
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn v2_normalization_is_stable_under_declaration_reordering() {
        let dir = test_dir();
        let path = dir.join("capsule.json");
        let mut first = neutral_capsule();
        first.exports.push(DeclaredExport {
            name: "alpha-export".to_string(),
            resource: "result".to_string(),
            provider_label: None,
            output_override: Some(1.0),
        });
        let mut reordered = first.clone();
        reordered.resources.reverse();
        reordered.passes.reverse();
        reordered.exports.reverse();
        assert_eq!(
            first.normalize(&path).expect("first plan"),
            reordered.normalize(&path).expect("reordered plan")
        );
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn optional_provider_labels_are_bounded() {
        let dir = test_dir();
        let path = dir.join("capsule.json");
        let maximum = "x".repeat(MAX_PROVIDER_LABEL_BYTES);
        let oversized = "x".repeat(MAX_PROVIDER_LABEL_BYTES + 1);

        let mut accepted = neutral_capsule();
        accepted.passes[0].provider_label = Some(maximum.clone());
        accepted.exports[0].provider_label = Some(maximum);
        accepted.normalize(&path).expect("bounded provider labels");

        let mut pass = neutral_capsule();
        pass.passes[0].provider_label = Some(oversized.clone());
        assert!(pass.normalize(&path).is_err());

        let mut export = neutral_capsule();
        export.exports[0].provider_label = Some(oversized);
        assert!(export.normalize(&path).is_err());
        fs::remove_dir_all(dir).expect("remove test directory");
    }
}
