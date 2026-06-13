use makepad_widgets::makepad_platform::{
    XrGpuF32FieldForceSampleProbeResult, XrGpuF32FieldSampleProbeResult, XrGpuF32ForceProbeSample,
    XrGpuF32MeshSdfProbeGrid, XrGpuF32MeshSdfProbeResult, XrGpuF32MeshSdfProbeTicket,
    XrGpuF32SkinningMeshProbeResult, XrGpuF32SkinningMeshProbeTicket, XrGpuF32SkinningMeshVertex,
    XrGpuF32SkinningProbeResult, XrGpuF32SkinningProbeSample, XrGpuF32SkinningProbeTicket,
    XrGpuSkinningMeshTriangle, XR_GPU_F32_FIELD_FORCE_SAMPLE_PROBE_SAMPLES,
    XR_GPU_F32_FIELD_SAMPLE_PROBE_SAMPLES, XR_GPU_F32_MESH_SDF_PROBE_SAMPLES,
    XR_GPU_F32_SKINNING_MESH_PROBE_SAMPLES, XR_GPU_F32_SKINNING_PROBE_SAMPLES,
};
use makepad_widgets::*;
use rusty_quest_makepad_camera_shell::{
    MatterSurfaceParticleForceSource, QuestMakepadForceAuthorityMode,
    QuestMakepadGpuFieldConstructionReceipt, QuestMakepadGpuFieldForceSamplingProbe,
    QuestMakepadGpuFieldForceSamplingProbeReadback, QuestMakepadGpuFieldParticleForceProbe,
    QuestMakepadGpuFieldParticleForceProbeInput, QuestMakepadGpuFieldSamplingProbe,
    QuestMakepadGpuFieldSamplingProbeReadback, QuestMakepadGpuForceAuthorityCandidate,
    QuestMakepadGpuForceAuthorityGate, QuestMakepadGpuForceAuthorityResidencyHealth,
    QuestMakepadGpuMeshSdfProbe, QuestMakepadGpuMeshSdfProbeInput,
    QuestMakepadGpuMeshSdfProbeReadback, QuestMakepadGpuSkinningMeshProbe,
    QuestMakepadGpuSkinningMeshProbeInput, QuestMakepadGpuSkinningMeshProbeReadback,
    QuestMakepadGpuSkinningMeshVertex, QuestMakepadGpuSkinningProbe,
    QuestMakepadGpuSkinningProbeInput, QuestMakepadGpuSkinningProbeReadback,
    QuestMakepadGpuSkinningProbeSample, QuestMakepadMatterSurfaceFrame,
    QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE_DEFAULT_TOLERANCE,
    QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE_SAMPLES,
    QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE_DEFAULT_TOLERANCE,
    QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE_SAMPLES,
    QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE_DEFAULT_TOLERANCE,
    QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE_SAMPLES,
    QUEST_MAKEPAD_GPU_MESH_SDF_PROBE_DEFAULT_TOLERANCE, QUEST_MAKEPAD_GPU_MESH_SDF_PROBE_SAMPLES,
    QUEST_MAKEPAD_GPU_SKINNING_MESH_PROBE_DEFAULT_TOLERANCE,
    QUEST_MAKEPAD_GPU_SKINNING_MESH_PROBE_SAMPLES,
    QUEST_MAKEPAD_GPU_SKINNING_PROBE_DEFAULT_TOLERANCE, QUEST_MAKEPAD_GPU_SKINNING_PROBE_SAMPLES,
};

#[derive(Clone, Debug)]
pub(crate) struct PendingGpuMeshSdfProbe {
    input: QuestMakepadGpuMeshSdfProbeInput,
    particle_force_input: Option<QuestMakepadGpuFieldParticleForceProbeInput>,
    active_force_source: MatterSurfaceParticleForceSource,
    requested_force_authority: QuestMakepadForceAuthorityMode,
    ticket: XrGpuF32MeshSdfProbeTicket,
}

#[derive(Clone, Debug)]
pub(crate) struct PendingGpuSkinningMeshProbe {
    input: QuestMakepadGpuSkinningMeshProbeInput,
    ticket: XrGpuF32SkinningMeshProbeTicket,
}

#[derive(Clone, Debug)]
pub(crate) struct PendingGpuSkinningProbe {
    input: QuestMakepadGpuSkinningProbeInput,
    ticket: XrGpuF32SkinningProbeTicket,
}

struct PreparedGpuSkinningProbe {
    samples: [XrGpuF32SkinningProbeSample; XR_GPU_F32_SKINNING_PROBE_SAMPLES],
    sample_count: usize,
}

struct PreparedGpuSkinningMeshProbe {
    vertices: Vec<XrGpuF32SkinningMeshVertex>,
    triangles: Vec<XrGpuSkinningMeshTriangle>,
    sample_vertex_indices: [u32; XR_GPU_F32_SKINNING_MESH_PROBE_SAMPLES],
    sample_count: usize,
}

struct PreparedGpuMeshSdfProbe {
    vertices: Vec<XrGpuF32SkinningMeshVertex>,
    triangles: Vec<XrGpuSkinningMeshTriangle>,
    grid: XrGpuF32MeshSdfProbeGrid,
    sample_linear_indices: [u32; XR_GPU_F32_MESH_SDF_PROBE_SAMPLES],
    expected_distances: [f32; XR_GPU_F32_MESH_SDF_PROBE_SAMPLES],
    sample_count: usize,
}

pub(crate) fn gpu_skinning_probe_submit(
    cx: &mut Cx,
    input: &QuestMakepadGpuSkinningProbeInput,
) -> Option<PendingGpuSkinningProbe> {
    let prepared = prepare_gpu_skinning_probe(input)?;
    let ticket = cx.xr_gpu_f32_skinning_probe_submit(
        prepared.samples,
        prepared.sample_count,
        QUEST_MAKEPAD_GPU_SKINNING_PROBE_DEFAULT_TOLERANCE,
    )?;
    Some(PendingGpuSkinningProbe {
        input: input.clone(),
        ticket,
    })
}

pub(crate) fn gpu_skinning_probe_poll_marker_line(
    cx: &mut Cx,
    pending: &PendingGpuSkinningProbe,
    phase: &str,
) -> Option<String> {
    let readback = cx.xr_gpu_f32_skinning_probe_poll(pending.ticket.request_id)?;
    gpu_skinning_probe_marker_line_from_readback(&pending.input, readback, phase)
}

fn prepare_gpu_skinning_probe(
    input: &QuestMakepadGpuSkinningProbeInput,
) -> Option<PreparedGpuSkinningProbe> {
    let sample_count = input
        .sample_count
        .min(QUEST_MAKEPAD_GPU_SKINNING_PROBE_SAMPLES)
        .min(XR_GPU_F32_SKINNING_PROBE_SAMPLES);
    if sample_count == 0 {
        return None;
    }

    let mut samples = [XrGpuF32SkinningProbeSample::default(); XR_GPU_F32_SKINNING_PROBE_SAMPLES];
    for (target, source) in samples
        .iter_mut()
        .zip(input.samples.iter())
        .take(sample_count)
    {
        *target = makepad_skinning_sample(*source);
    }

    Some(PreparedGpuSkinningProbe {
        samples,
        sample_count,
    })
}

fn gpu_skinning_probe_marker_line_from_readback(
    input: &QuestMakepadGpuSkinningProbeInput,
    readback: XrGpuF32SkinningProbeResult,
    phase: &str,
) -> Option<String> {
    let probe = QuestMakepadGpuSkinningProbe::from_input(
        input,
        QuestMakepadGpuSkinningProbeReadback {
            sample_count: readback.sample_count,
            component_count: readback.component_count,
            mismatched_components: readback.mismatched_components,
            max_abs_error: readback.max_abs_error,
            tolerance: readback.tolerance,
            queue_submit_serial: readback.queue_submit_serial,
            fence_serial: readback.fence_serial,
            resource_generation: readback.resource_generation,
            pending_retire_count: readback.pending_retire_count,
            retained_resource_count: readback.retained_resource_count,
            retired_after_fence_count: readback.retired_after_fence_count,
            queue_wait_idle_performed: readback.queue_wait_idle_performed,
            elapsed_ms: readback.elapsed_ms,
        },
    );
    Some(probe.marker_line(phase))
}

pub(crate) fn gpu_mesh_sdf_probe_submit(
    cx: &mut Cx,
    frame: &QuestMakepadMatterSurfaceFrame,
    requested_force_authority: QuestMakepadForceAuthorityMode,
) -> Option<PendingGpuMeshSdfProbe> {
    let input = frame.gpu_mesh_sdf_probe.as_ref()?;
    let prepared = prepare_gpu_mesh_sdf_probe(input)?;
    let ticket = cx.xr_gpu_f32_mesh_sdf_probe_submit(
        &prepared.vertices,
        &prepared.triangles,
        prepared.grid,
        prepared.sample_linear_indices,
        prepared.expected_distances,
        prepared.sample_count,
        QUEST_MAKEPAD_GPU_MESH_SDF_PROBE_DEFAULT_TOLERANCE,
    )?;
    let particle_force_input =
        QuestMakepadGpuFieldParticleForceProbeInput::from_mesh_sdf_input_and_particle_snapshot(
            input,
            &frame.particle_snapshot,
            frame.particle_force_oracle_config,
        );
    Some(PendingGpuMeshSdfProbe {
        input: input.clone(),
        particle_force_input,
        active_force_source: frame.stats.particle_force_source,
        requested_force_authority,
        ticket,
    })
}

pub(crate) fn gpu_mesh_sdf_probe_poll_marker_lines(
    cx: &mut Cx,
    pending: &PendingGpuMeshSdfProbe,
    phase: &str,
) -> Option<Vec<String>> {
    let readback = cx.xr_gpu_f32_mesh_sdf_probe_poll(pending.ticket.request_id)?;
    gpu_mesh_sdf_probe_marker_lines_from_readback(
        cx,
        &pending.input,
        pending.particle_force_input.as_ref(),
        pending.active_force_source,
        pending.requested_force_authority,
        readback,
        phase,
    )
}

fn prepare_gpu_mesh_sdf_probe(
    input: &QuestMakepadGpuMeshSdfProbeInput,
) -> Option<PreparedGpuMeshSdfProbe> {
    let sample_count = input
        .sample_count
        .min(QUEST_MAKEPAD_GPU_MESH_SDF_PROBE_SAMPLES)
        .min(XR_GPU_F32_MESH_SDF_PROBE_SAMPLES);
    if sample_count == 0 || input.vertices.is_empty() || input.triangles.is_empty() {
        return None;
    }

    let vertices = input
        .vertices
        .iter()
        .copied()
        .map(makepad_skinning_mesh_vertex)
        .collect::<Vec<_>>();
    let triangles = input
        .triangles
        .iter()
        .copied()
        .map(makepad_skinning_mesh_triangle)
        .collect::<Vec<_>>();
    let mut sample_linear_indices = [0_u32; XR_GPU_F32_MESH_SDF_PROBE_SAMPLES];
    let mut expected_distances = [0.0_f32; XR_GPU_F32_MESH_SDF_PROBE_SAMPLES];
    for index in 0..sample_count {
        sample_linear_indices[index] = u32::try_from(input.samples[index].linear_index).ok()?;
        expected_distances[index] = input.samples[index].expected_distance;
    }
    let grid = XrGpuF32MeshSdfProbeGrid {
        origin_voxel_size: [
            input.grid.origin[0],
            input.grid.origin[1],
            input.grid.origin[2],
            input.grid.voxel_size,
        ],
        dimensions: [
            input.grid.dimensions[0],
            input.grid.dimensions[1],
            input.grid.dimensions[2],
            0,
        ],
    };

    Some(PreparedGpuMeshSdfProbe {
        vertices,
        triangles,
        grid,
        sample_linear_indices,
        expected_distances,
        sample_count,
    })
}

fn gpu_mesh_sdf_probe_marker_lines_from_readback(
    cx: &mut Cx,
    input: &QuestMakepadGpuMeshSdfProbeInput,
    particle_force_input: Option<&QuestMakepadGpuFieldParticleForceProbeInput>,
    active_force_source: MatterSurfaceParticleForceSource,
    requested_force_authority: QuestMakepadForceAuthorityMode,
    readback: XrGpuF32MeshSdfProbeResult,
    phase: &str,
) -> Option<Vec<String>> {
    let mut readback_sample_indices = [0_usize; QUEST_MAKEPAD_GPU_MESH_SDF_PROBE_SAMPLES];
    for (target, source) in readback_sample_indices
        .iter_mut()
        .zip(readback.sample_linear_indices.iter())
        .take(
            readback
                .sample_count
                .min(QUEST_MAKEPAD_GPU_MESH_SDF_PROBE_SAMPLES),
        )
    {
        *target = *source as usize;
    }
    let probe = QuestMakepadGpuMeshSdfProbe::from_input(
        input,
        QuestMakepadGpuMeshSdfProbeReadback {
            vertex_count: readback.vertex_count,
            triangle_count: readback.triangle_count,
            index_count: readback.index_count,
            voxel_count: readback.voxel_count,
            sample_count: readback.sample_count,
            checked_sample_count: readback.checked_sample_count,
            mismatched_samples: readback.mismatched_samples,
            max_abs_error: readback.max_abs_error,
            tolerance: readback.tolerance,
            sample_linear_indices: readback_sample_indices,
            output_distances: readback.output_distances,
            expected_distances: readback.expected_distances,
            queue_submit_serial: readback.queue_submit_serial,
            fence_serial: readback.fence_serial,
            resource_generation: readback.resource_generation,
            program_generation: readback.program_generation,
            program_reused: readback.program_reused,
            shader_compiled_this_submit: readback.shader_compiled_this_submit,
            pipeline_created_this_submit: readback.pipeline_created_this_submit,
            source_mesh_buffer_generation: readback.source_mesh_buffer_generation,
            source_mesh_buffers_resident: readback.source_mesh_buffers_resident,
            source_mesh_buffers_reused: readback.source_mesh_buffers_reused,
            source_vertex_buffer_bytes: readback.source_vertex_buffer_bytes,
            source_triangle_buffer_bytes: readback.source_triangle_buffer_bytes,
            derived_buffer_generation: readback.derived_buffer_generation,
            derived_buffers_resident: readback.derived_buffers_resident,
            derived_buffers_reused: readback.derived_buffers_reused,
            skinned_position_buffer_bytes: readback.skinned_position_buffer_bytes,
            sdf_distance_buffer_bytes: readback.sdf_distance_buffer_bytes,
            pending_retire_count: readback.pending_retire_count,
            retained_resource_count: readback.retained_resource_count,
            retired_after_fence_count: readback.retired_after_fence_count,
            queue_wait_idle_performed: readback.queue_wait_idle_performed,
            elapsed_ms: readback.elapsed_ms,
        },
    );
    let receipt = QuestMakepadGpuFieldConstructionReceipt::from_mesh_sdf_probe(&probe);
    let mut markers = vec![probe.marker_line(phase), receipt.marker_line(phase)];
    if let Some(marker) = gpu_field_sampling_probe_marker_line(cx, input, &receipt, phase) {
        markers.push(marker);
    }
    if let Some(marker) = gpu_field_force_sampling_probe_marker_line(cx, input, &receipt, phase) {
        markers.push(marker);
    }
    if let Some(particle_force_input) = particle_force_input {
        if let Some(particle_markers) = gpu_field_particle_force_probe_marker_lines(
            cx,
            particle_force_input,
            &receipt,
            active_force_source,
            requested_force_authority,
            phase,
        ) {
            markers.extend(particle_markers);
        }
    }
    Some(markers)
}

fn gpu_field_sampling_probe_marker_line(
    cx: &mut Cx,
    input: &QuestMakepadGpuMeshSdfProbeInput,
    receipt: &QuestMakepadGpuFieldConstructionReceipt,
    phase: &str,
) -> Option<String> {
    if !receipt.runtime_field_boundary_ready() {
        return None;
    }
    let sample_count = input
        .sample_count
        .min(QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE_SAMPLES)
        .min(XR_GPU_F32_FIELD_SAMPLE_PROBE_SAMPLES);
    if sample_count == 0 {
        return None;
    }

    let mut sample_linear_indices = [0_u32; XR_GPU_F32_FIELD_SAMPLE_PROBE_SAMPLES];
    let mut expected_distances = [0.0_f32; XR_GPU_F32_FIELD_SAMPLE_PROBE_SAMPLES];
    for index in 0..sample_count {
        sample_linear_indices[index] = u32::try_from(input.samples[index].linear_index).ok()?;
        expected_distances[index] = input.samples[index].expected_distance;
    }

    let readback = cx.xr_gpu_f32_field_sample_probe(
        sample_linear_indices,
        expected_distances,
        sample_count,
        QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE_DEFAULT_TOLERANCE,
    )?;
    gpu_field_sampling_probe_marker_line_from_readback(input, receipt, readback, phase)
}

fn gpu_field_sampling_probe_marker_line_from_readback(
    input: &QuestMakepadGpuMeshSdfProbeInput,
    receipt: &QuestMakepadGpuFieldConstructionReceipt,
    readback: XrGpuF32FieldSampleProbeResult,
    phase: &str,
) -> Option<String> {
    let mut sample_linear_indices = [0_usize; QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE_SAMPLES];
    let mut output_distances = [0.0_f32; QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE_SAMPLES];
    let mut expected_distances = [0.0_f32; QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE_SAMPLES];
    let sample_count = readback
        .sample_count
        .min(QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE_SAMPLES);
    for index in 0..sample_count {
        sample_linear_indices[index] = readback.sample_linear_indices[index] as usize;
        output_distances[index] = readback.output_distances[index];
        expected_distances[index] = readback.expected_distances[index];
    }
    let probe = QuestMakepadGpuFieldSamplingProbe::from_receipt_and_input(
        receipt,
        input,
        QuestMakepadGpuFieldSamplingProbeReadback {
            sample_count: readback.sample_count,
            checked_sample_count: readback.checked_sample_count,
            sample_linear_indices,
            output_distances,
            expected_distances,
            mismatched_samples: readback.mismatched_samples,
            max_abs_error: readback.max_abs_error,
            tolerance: readback.tolerance,
            queue_submit_serial: readback.queue_submit_serial,
            fence_serial: readback.fence_serial,
            resource_generation: readback.resource_generation,
            program_generation: readback.program_generation,
            program_reused: readback.program_reused,
            shader_compiled_this_submit: readback.shader_compiled_this_submit,
            pipeline_created_this_submit: readback.pipeline_created_this_submit,
            source_field_generation: readback.source_field_generation,
            source_field_buffer_resident: readback.source_field_buffer_resident,
            source_field_buffer_bytes: readback.source_field_buffer_bytes,
            sample_index_buffer_bytes: readback.sample_index_buffer_bytes,
            sample_output_buffer_bytes: readback.sample_output_buffer_bytes,
            pending_retire_count: readback.pending_retire_count,
            retained_resource_count: readback.retained_resource_count,
            retired_after_fence_count: readback.retired_after_fence_count,
            queue_wait_idle_performed: readback.queue_wait_idle_performed,
            elapsed_ms: readback.elapsed_ms,
        },
    );
    Some(probe.marker_line(phase))
}

fn gpu_field_force_sampling_probe_marker_line(
    cx: &mut Cx,
    input: &QuestMakepadGpuMeshSdfProbeInput,
    receipt: &QuestMakepadGpuFieldConstructionReceipt,
    phase: &str,
) -> Option<String> {
    if !receipt.runtime_field_boundary_ready() {
        return None;
    }
    let sample_count = input
        .force_sample_count
        .min(QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE_SAMPLES)
        .min(XR_GPU_F32_FIELD_FORCE_SAMPLE_PROBE_SAMPLES);
    if sample_count == 0 {
        return None;
    }

    let mut samples =
        [XrGpuF32ForceProbeSample::default(); XR_GPU_F32_FIELD_FORCE_SAMPLE_PROBE_SAMPLES];
    for (target, source) in samples
        .iter_mut()
        .zip(input.force_samples.iter())
        .take(sample_count)
    {
        *target = XrGpuF32ForceProbeSample {
            position_radius: [
                source.position[0],
                source.position[1],
                source.position[2],
                source.radius,
            ],
            distance_target_strength: [
                source.distance,
                source.target_distance,
                source.attraction_strength,
                0.0,
            ],
            outward: source.outward,
            expected_acceleration: source.expected_acceleration,
        };
    }

    let readback = cx.xr_gpu_f32_field_force_sample_probe(
        samples,
        sample_count,
        QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE_DEFAULT_TOLERANCE,
    )?;
    gpu_field_force_sampling_probe_marker_line_from_readback(input, receipt, readback, phase)
}

fn gpu_field_force_sampling_probe_marker_line_from_readback(
    input: &QuestMakepadGpuMeshSdfProbeInput,
    receipt: &QuestMakepadGpuFieldConstructionReceipt,
    readback: XrGpuF32FieldForceSampleProbeResult,
    phase: &str,
) -> Option<String> {
    let probe = QuestMakepadGpuFieldForceSamplingProbe::from_receipt_and_input(
        receipt,
        input,
        QuestMakepadGpuFieldForceSamplingProbeReadback {
            sample_count: readback.sample_count,
            component_count: readback.component_count,
            mismatched_components: readback.mismatched_components,
            max_abs_error: readback.max_abs_error,
            tolerance: readback.tolerance,
            queue_submit_serial: readback.queue_submit_serial,
            fence_serial: readback.fence_serial,
            resource_generation: readback.resource_generation,
            program_generation: readback.program_generation,
            program_reused: readback.program_reused,
            shader_compiled_this_submit: readback.shader_compiled_this_submit,
            pipeline_created_this_submit: readback.pipeline_created_this_submit,
            source_field_generation: readback.source_field_generation,
            source_field_buffer_resident: readback.source_field_buffer_resident,
            source_field_buffer_bytes: readback.source_field_buffer_bytes,
            sample_input_buffer_bytes: readback.sample_input_buffer_bytes,
            sample_output_buffer_bytes: readback.sample_output_buffer_bytes,
            pending_retire_count: readback.pending_retire_count,
            retained_resource_count: readback.retained_resource_count,
            retired_after_fence_count: readback.retired_after_fence_count,
            queue_wait_idle_performed: readback.queue_wait_idle_performed,
            elapsed_ms: readback.elapsed_ms,
        },
    );
    Some(probe.marker_line(phase))
}

fn gpu_field_particle_force_probe_marker_lines(
    cx: &mut Cx,
    input: &QuestMakepadGpuFieldParticleForceProbeInput,
    receipt: &QuestMakepadGpuFieldConstructionReceipt,
    active_force_source: MatterSurfaceParticleForceSource,
    requested_force_authority: QuestMakepadForceAuthorityMode,
    phase: &str,
) -> Option<Vec<String>> {
    if !receipt.runtime_field_boundary_ready() {
        return None;
    }
    let sample_count = input
        .sample_count
        .min(QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE_SAMPLES)
        .min(XR_GPU_F32_FIELD_FORCE_SAMPLE_PROBE_SAMPLES);
    if sample_count == 0 {
        return None;
    }

    let mut samples =
        [XrGpuF32ForceProbeSample::default(); XR_GPU_F32_FIELD_FORCE_SAMPLE_PROBE_SAMPLES];
    for (target, source) in samples
        .iter_mut()
        .zip(input.samples.iter())
        .take(sample_count)
    {
        *target = XrGpuF32ForceProbeSample {
            position_radius: [
                source.position[0],
                source.position[1],
                source.position[2],
                source.radius,
            ],
            distance_target_strength: [
                source.distance,
                source.target_distance,
                source.attraction_strength,
                0.0,
            ],
            outward: source.outward,
            expected_acceleration: source.expected_acceleration,
        };
    }

    let readback = cx.xr_gpu_f32_field_force_sample_probe(
        samples,
        sample_count,
        QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE_DEFAULT_TOLERANCE,
    )?;
    gpu_field_particle_force_probe_marker_lines_from_readback(
        input,
        receipt,
        active_force_source,
        requested_force_authority,
        readback,
        phase,
    )
}

fn gpu_field_particle_force_probe_marker_lines_from_readback(
    input: &QuestMakepadGpuFieldParticleForceProbeInput,
    receipt: &QuestMakepadGpuFieldConstructionReceipt,
    active_force_source: MatterSurfaceParticleForceSource,
    requested_force_authority: QuestMakepadForceAuthorityMode,
    readback: XrGpuF32FieldForceSampleProbeResult,
    phase: &str,
) -> Option<Vec<String>> {
    let probe = QuestMakepadGpuFieldParticleForceProbe::from_receipt_and_input(
        receipt,
        input,
        QuestMakepadGpuFieldForceSamplingProbeReadback {
            sample_count: readback.sample_count,
            component_count: readback.component_count,
            mismatched_components: readback.mismatched_components,
            max_abs_error: readback.max_abs_error,
            tolerance: readback.tolerance,
            queue_submit_serial: readback.queue_submit_serial,
            fence_serial: readback.fence_serial,
            resource_generation: readback.resource_generation,
            program_generation: readback.program_generation,
            program_reused: readback.program_reused,
            shader_compiled_this_submit: readback.shader_compiled_this_submit,
            pipeline_created_this_submit: readback.pipeline_created_this_submit,
            source_field_generation: readback.source_field_generation,
            source_field_buffer_resident: readback.source_field_buffer_resident,
            source_field_buffer_bytes: readback.source_field_buffer_bytes,
            sample_input_buffer_bytes: readback.sample_input_buffer_bytes,
            sample_output_buffer_bytes: readback.sample_output_buffer_bytes,
            pending_retire_count: readback.pending_retire_count,
            retained_resource_count: readback.retained_resource_count,
            retired_after_fence_count: readback.retired_after_fence_count,
            queue_wait_idle_performed: readback.queue_wait_idle_performed,
            elapsed_ms: readback.elapsed_ms,
        },
    );
    let mut markers = vec![probe.marker_line(phase)];
    if let Some(candidate) =
        QuestMakepadGpuForceAuthorityCandidate::from_particle_force_probe(&probe)
    {
        markers.push(candidate.marker_line(phase));
        if let Some(gate) = QuestMakepadGpuForceAuthorityGate::from_candidate(
            &candidate,
            active_force_source,
            requested_force_authority,
        ) {
            markers.push(gate.marker_line(phase));
            let residency_health = QuestMakepadGpuForceAuthorityResidencyHealth::from_gate(&gate);
            markers.push(residency_health.marker_line(phase));
        }
    }
    Some(markers)
}

pub(crate) fn gpu_skinning_mesh_probe_submit(
    cx: &mut Cx,
    input: &QuestMakepadGpuSkinningMeshProbeInput,
) -> Option<PendingGpuSkinningMeshProbe> {
    let prepared = prepare_gpu_skinning_mesh_probe(input)?;
    let ticket = cx.xr_gpu_f32_skinning_mesh_probe_submit(
        &prepared.vertices,
        &prepared.triangles,
        prepared.sample_vertex_indices,
        prepared.sample_count,
        QUEST_MAKEPAD_GPU_SKINNING_MESH_PROBE_DEFAULT_TOLERANCE,
    )?;
    Some(PendingGpuSkinningMeshProbe {
        input: input.clone(),
        ticket,
    })
}

pub(crate) fn gpu_skinning_mesh_probe_poll_marker_line(
    cx: &mut Cx,
    pending: &PendingGpuSkinningMeshProbe,
    phase: &str,
) -> Option<String> {
    let readback = cx.xr_gpu_f32_skinning_mesh_probe_poll(pending.ticket.request_id)?;
    gpu_skinning_mesh_probe_marker_line_from_readback(&pending.input, readback, phase)
}

fn prepare_gpu_skinning_mesh_probe(
    input: &QuestMakepadGpuSkinningMeshProbeInput,
) -> Option<PreparedGpuSkinningMeshProbe> {
    let sample_count = input
        .sample_count
        .min(QUEST_MAKEPAD_GPU_SKINNING_MESH_PROBE_SAMPLES)
        .min(XR_GPU_F32_SKINNING_MESH_PROBE_SAMPLES);
    if sample_count == 0 || input.vertices.is_empty() || input.triangles.is_empty() {
        return None;
    }

    let vertices = input
        .vertices
        .iter()
        .copied()
        .map(makepad_skinning_mesh_vertex)
        .collect::<Vec<_>>();
    let triangles = input
        .triangles
        .iter()
        .copied()
        .map(makepad_skinning_mesh_triangle)
        .collect::<Vec<_>>();
    let mut sample_vertex_indices = [0_u32; XR_GPU_F32_SKINNING_MESH_PROBE_SAMPLES];
    for (target, source) in sample_vertex_indices
        .iter_mut()
        .zip(input.sample_vertex_indices.iter())
        .take(sample_count)
    {
        *target = u32::try_from(*source).ok()?;
    }

    Some(PreparedGpuSkinningMeshProbe {
        vertices,
        triangles,
        sample_vertex_indices,
        sample_count,
    })
}

fn gpu_skinning_mesh_probe_marker_line_from_readback(
    input: &QuestMakepadGpuSkinningMeshProbeInput,
    readback: XrGpuF32SkinningMeshProbeResult,
    phase: &str,
) -> Option<String> {
    let mut readback_sample_indices = [0_usize; QUEST_MAKEPAD_GPU_SKINNING_MESH_PROBE_SAMPLES];
    for (target, source) in readback_sample_indices
        .iter_mut()
        .zip(readback.sample_vertex_indices.iter())
        .take(
            readback
                .sample_count
                .min(QUEST_MAKEPAD_GPU_SKINNING_MESH_PROBE_SAMPLES),
        )
    {
        *target = *source as usize;
    }
    let probe = QuestMakepadGpuSkinningMeshProbe::from_input(
        input,
        QuestMakepadGpuSkinningMeshProbeReadback {
            vertex_count: readback.vertex_count,
            triangle_count: readback.triangle_count,
            index_count: readback.index_count,
            checked_position_components: readback.checked_position_components,
            mismatched_position_components: readback.mismatched_position_components,
            mismatched_triangle_indices: readback.mismatched_triangle_indices,
            max_abs_error: readback.max_abs_error,
            tolerance: readback.tolerance,
            sample_count: readback.sample_count,
            sample_vertex_indices: readback_sample_indices,
            queue_submit_serial: readback.queue_submit_serial,
            fence_serial: readback.fence_serial,
            resource_generation: readback.resource_generation,
            pending_retire_count: readback.pending_retire_count,
            retained_resource_count: readback.retained_resource_count,
            retired_after_fence_count: readback.retired_after_fence_count,
            queue_wait_idle_performed: readback.queue_wait_idle_performed,
            elapsed_ms: readback.elapsed_ms,
        },
    );
    Some(probe.marker_line(phase))
}

fn makepad_skinning_sample(
    sample: QuestMakepadGpuSkinningProbeSample,
) -> XrGpuF32SkinningProbeSample {
    let matrices = sample.joint_matrices;
    XrGpuF32SkinningProbeSample {
        bind_position: sample.bind_position,
        joint_weights: sample.joint_weights,
        matrix0_row0: matrices[0][0],
        matrix0_row1: matrices[0][1],
        matrix0_row2: matrices[0][2],
        matrix0_row3: matrices[0][3],
        matrix1_row0: matrices[1][0],
        matrix1_row1: matrices[1][1],
        matrix1_row2: matrices[1][2],
        matrix1_row3: matrices[1][3],
        matrix2_row0: matrices[2][0],
        matrix2_row1: matrices[2][1],
        matrix2_row2: matrices[2][2],
        matrix2_row3: matrices[2][3],
        matrix3_row0: matrices[3][0],
        matrix3_row1: matrices[3][1],
        matrix3_row2: matrices[3][2],
        matrix3_row3: matrices[3][3],
        expected_position: sample.expected_position,
    }
}

fn makepad_skinning_mesh_vertex(
    vertex: QuestMakepadGpuSkinningMeshVertex,
) -> XrGpuF32SkinningMeshVertex {
    let matrices = vertex.joint_matrices;
    XrGpuF32SkinningMeshVertex {
        bind_position: vertex.bind_position,
        joint_weights: vertex.joint_weights,
        matrix0_row0: matrices[0][0],
        matrix0_row1: matrices[0][1],
        matrix0_row2: matrices[0][2],
        matrix0_row3: matrices[0][3],
        matrix1_row0: matrices[1][0],
        matrix1_row1: matrices[1][1],
        matrix1_row2: matrices[1][2],
        matrix1_row3: matrices[1][3],
        matrix2_row0: matrices[2][0],
        matrix2_row1: matrices[2][1],
        matrix2_row2: matrices[2][2],
        matrix2_row3: matrices[2][3],
        matrix3_row0: matrices[3][0],
        matrix3_row1: matrices[3][1],
        matrix3_row2: matrices[3][2],
        matrix3_row3: matrices[3][3],
        expected_position: vertex.expected_position,
    }
}

fn makepad_skinning_mesh_triangle(indices: [u32; 3]) -> XrGpuSkinningMeshTriangle {
    XrGpuSkinningMeshTriangle {
        indices: [
            indices[0],
            indices[1],
            indices[2],
            indices[0] ^ indices[1] ^ indices[2],
        ],
    }
}
