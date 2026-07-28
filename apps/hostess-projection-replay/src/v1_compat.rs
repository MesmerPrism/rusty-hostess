use std::{collections::BTreeMap, path::PathBuf};

use crate::{
    capsule::{ReplayCapsule, CAPSULE_SCHEMA},
    execution_plan::{
        DescriptorType, PlanDescriptorBinding, PlanExport, PlanPass, PlanResource, PlanShader,
        PushRange, ReplayExecutionPlan, ShaderStage, EXECUTION_PLAN_SCHEMA,
    },
};

const GUIDE_TARGETS: [&str; 5] = [
    "guide-raw-brightness",
    "guide-blur-temp",
    "guide-preblur-brightness",
    "guide-raw-strength",
    "guide-blurred-strength",
];
const GUIDE_TARGET_SCHEDULE: [usize; 6] = [0, 1, 2, 3, 1, 4];

pub fn normalize(capsule: &ReplayCapsule) -> ReplayExecutionPlan {
    let mut resources = vec![
        image("camera-left", true, "rgba8-unorm"),
        image("camera-right", true, "rgba8-unorm"),
        image("depth", true, "r32-sfloat"),
        image("video", true, "rgba8-unorm"),
        buffer("rgb-uniform", 96),
        buffer("displacement-uniform", 64),
        buffer("zone-uniform", 368),
    ];
    resources.extend(
        GUIDE_TARGETS
            .iter()
            .map(|id| image(id, false, "rgba8-unorm")),
    );
    resources.push(image("projection-output", false, "rgba8-unorm"));

    let mut passes = capsule
        .shaders
        .guide_fragment_spirv
        .iter()
        .enumerate()
        .map(|(index, fragment)| {
            let target = GUIDE_TARGETS[GUIDE_TARGET_SCHEDULE[index]];
            let dependencies = match index {
                0 | 3 => Vec::new(),
                1 => vec!["guide-0".to_string()],
                2 => vec!["guide-1".to_string()],
                4 => vec!["guide-3".to_string()],
                5 => vec!["guide-4".to_string()],
                _ => unreachable!(),
            };
            PlanPass {
                id: format!("guide-{index}"),
                provider_label: None,
                dependencies,
                shaders: vec![
                    shader(
                        ShaderStage::Vertex,
                        &capsule.shaders.fullscreen_vertex_spirv,
                    ),
                    shader(ShaderStage::Fragment, fragment),
                ],
                descriptor_bindings: guide_bindings(index),
                push_ranges: vec![push(
                    112,
                    &capsule.guide.push_left,
                    &capsule.guide.push_right,
                )],
                scissors: BTreeMap::new(),
                render_targets: vec![target.to_string()],
            }
        })
        .collect::<Vec<_>>();
    passes.push(PlanPass {
        id: "projection".to_string(),
        provider_label: None,
        dependencies: vec!["guide-2".to_string(), "guide-5".to_string()],
        shaders: vec![
            shader(
                ShaderStage::Vertex,
                if capsule.projection.displacement_enabled {
                    capsule
                        .shaders
                        .displacement_vertex_spirv
                        .as_ref()
                        .expect("validated v1 displacement shader")
                } else {
                    &capsule.shaders.fullscreen_vertex_spirv
                },
            ),
            shader(
                ShaderStage::Fragment,
                &capsule.shaders.projection_fragment_spirv,
            ),
        ],
        descriptor_bindings: projection_bindings(),
        push_ranges: vec![PushRange {
            offset: 0,
            byte_size: 128,
            stages: vec![ShaderStage::Vertex, ShaderStage::Fragment],
            values: capsule.projection.push_left.clone(),
            view_values: BTreeMap::from([(
                "right".to_string(),
                capsule.projection.push_right.clone(),
            )]),
        }],
        scissors: BTreeMap::from([
            ("left".to_string(), capsule.projection.scissor_left.clone()),
            (
                "right".to_string(),
                capsule.projection.scissor_right.clone(),
            ),
        ]),
        render_targets: vec!["projection-output".to_string()],
    });

    ReplayExecutionPlan {
        schema: EXECUTION_PLAN_SCHEMA,
        source_schema: CAPSULE_SCHEMA.to_string(),
        name: capsule.name.clone(),
        extent: capsule.extent,
        provider_labels: BTreeMap::new(),
        resources,
        passes,
        exports: GUIDE_TARGETS
            .iter()
            .map(|name| PlanExport {
                name: (*name).to_string(),
                resource: (*name).to_string(),
                provider_label: None,
                output_override: None,
            })
            .chain(capsule.outputs.iter().map(|output| PlanExport {
                name: output.name.clone(),
                resource: "projection-output".to_string(),
                provider_label: None,
                output_override: Some(output.override_value),
            }))
            .collect(),
    }
}

fn image(id: &str, external: bool, format: &str) -> PlanResource {
    PlanResource {
        id: id.to_string(),
        kind: "image".to_string(),
        format: Some(format.to_string()),
        byte_size: None,
        external,
    }
}

fn buffer(id: &str, byte_size: u64) -> PlanResource {
    PlanResource {
        id: id.to_string(),
        kind: "buffer".to_string(),
        format: None,
        byte_size: Some(byte_size),
        external: true,
    }
}

fn shader(stage: ShaderStage, path: &std::path::Path) -> PlanShader {
    PlanShader {
        stage,
        path: PathBuf::from(path),
    }
}

fn push(byte_size: u32, left: &[f32], right: &[f32]) -> PushRange {
    PushRange {
        offset: 0,
        byte_size,
        stages: vec![ShaderStage::Fragment],
        values: left.to_vec(),
        view_values: BTreeMap::from([("right".to_string(), right.to_vec())]),
    }
}

fn guide_bindings(_index: usize) -> Vec<PlanDescriptorBinding> {
    let mut bindings = vec![
        sampled(0, 0, "camera-left", vec![ShaderStage::Fragment]),
        sampled(0, 1, "camera-right", vec![ShaderStage::Fragment]),
    ];
    bindings.extend(GUIDE_TARGETS.iter().enumerate().map(|(index, resource)| {
        sampled(
            1,
            4 + index as u32,
            resource,
            vec![ShaderStage::Vertex, ShaderStage::Fragment],
        )
    }));
    bindings
}

fn projection_bindings() -> Vec<PlanDescriptorBinding> {
    let mut bindings = vec![
        sampled(0, 0, "camera-left", vec![ShaderStage::Fragment]),
        sampled(0, 1, "camera-right", vec![ShaderStage::Fragment]),
    ];
    bindings.extend(GUIDE_TARGETS.iter().enumerate().map(|(index, resource)| {
        sampled(
            1,
            4 + index as u32,
            resource,
            vec![ShaderStage::Vertex, ShaderStage::Fragment],
        )
    }));
    bindings.extend([
        sampled(2, 0, "depth", vec![ShaderStage::Fragment]),
        uniform(3, 0, "rgb-uniform", 96, vec![ShaderStage::Fragment]),
        uniform(3, 1, "displacement-uniform", 64, vec![ShaderStage::Vertex]),
        sampled(4, 0, "video", vec![ShaderStage::Fragment]),
        uniform(5, 0, "zone-uniform", 368, vec![ShaderStage::Fragment]),
    ]);
    bindings
}

fn sampled(
    set: u32,
    binding: u32,
    resource: &str,
    stages: Vec<ShaderStage>,
) -> PlanDescriptorBinding {
    PlanDescriptorBinding {
        set,
        binding,
        descriptor_type: DescriptorType::CombinedImageSampler,
        stages,
        resource: resource.to_string(),
        byte_size: None,
    }
}

fn uniform(
    set: u32,
    binding: u32,
    resource: &str,
    byte_size: u64,
    stages: Vec<ShaderStage>,
) -> PlanDescriptorBinding {
    PlanDescriptorBinding {
        set,
        binding,
        descriptor_type: DescriptorType::UniformBuffer,
        stages,
        resource: resource.to_string(),
        byte_size: Some(byte_size),
    }
}

#[cfg(test)]
mod tests {
    use crate::capsule::{
        ColorInput, DepthInput, Extent, GuideConfiguration, OutputLayer, ProjectionConfiguration,
        ReplayInputs, ShaderBundle, SyntheticPattern,
    };

    use super::*;

    fn capsule() -> ReplayCapsule {
        ReplayCapsule {
            schema: CAPSULE_SCHEMA.to_string(),
            name: "v1-compatibility".to_string(),
            extent: Extent {
                width: 64,
                height: 32,
            },
            shaders: ShaderBundle {
                fullscreen_vertex_spirv: PathBuf::from("fullscreen.spv"),
                guide_fragment_spirv: (0..6)
                    .map(|index| PathBuf::from(format!("guide-{index}.spv")))
                    .collect(),
                projection_fragment_spirv: PathBuf::from("projection.spv"),
                displacement_vertex_spirv: None,
            },
            inputs: ReplayInputs {
                camera_left: ColorInput::Synthetic {
                    pattern: SyntheticPattern::UvGradient,
                    variant: 0,
                },
                camera_right: ColorInput::Transparent,
                video: ColorInput::Transparent,
                depth: DepthInput::Constant { meters: 1.0 },
            },
            guide: GuideConfiguration {
                push_left: vec![0.0; 28],
                push_right: vec![1.0; 28],
            },
            projection: ProjectionConfiguration {
                push_left: vec![0.0; 32],
                push_right: vec![1.0; 32],
                scissor_left: vec![0.0; 4],
                scissor_right: vec![0.0; 4],
                rgb_uniform: vec![0.0; 24],
                displacement_uniform: vec![0.0; 16],
                zone_uniform: vec![0.0; 92],
                displacement_enabled: false,
            },
            outputs: vec![
                OutputLayer {
                    name: "final".to_string(),
                    override_value: -1.0,
                },
                OutputLayer {
                    name: "diagnostic".to_string(),
                    override_value: 3.0,
                },
            ],
        }
    }

    #[test]
    fn v1_normalization_preserves_exact_schedule_abi_and_exports() {
        let plan = normalize(&capsule());
        assert_eq!(plan.source_schema, CAPSULE_SCHEMA);
        assert_eq!(
            plan.passes
                .iter()
                .take(6)
                .map(|pass| pass.render_targets[0].as_str())
                .collect::<Vec<_>>(),
            vec![
                "guide-raw-brightness",
                "guide-blur-temp",
                "guide-preblur-brightness",
                "guide-raw-strength",
                "guide-blur-temp",
                "guide-blurred-strength",
            ]
        );
        assert!(plan
            .passes
            .iter()
            .take(6)
            .all(|pass| { pass.push_ranges.len() == 1 && pass.push_ranges[0].byte_size == 112 }));
        assert_eq!(plan.passes[6].push_ranges[0].byte_size, 128);
        assert_eq!(
            plan.passes[0].push_ranges[0].view_values["right"],
            vec![1.0; 28]
        );
        assert_eq!(plan.passes[6].scissors["left"], vec![0.0; 4]);
        assert_eq!(plan.passes[6].scissors["right"], vec![0.0; 4]);
        assert_eq!(
            plan.resources
                .iter()
                .filter_map(|resource| resource.byte_size)
                .collect::<Vec<_>>(),
            vec![96, 64, 368]
        );
        assert_eq!(plan.exports.len(), 7);
        assert_eq!(plan.exports[5].name, "final");
        assert_eq!(plan.exports[5].output_override, Some(-1.0));
        assert_eq!(plan.exports[6].name, "diagnostic");
        assert_eq!(plan.exports[6].output_override, Some(3.0));
        assert!(plan.exports[5..]
            .iter()
            .all(|export| export.resource == "projection-output"));
    }
}
