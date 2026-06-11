use makepad_widgets::makepad_platform::{
    XrGpuF32SkinningProbeSample, XR_GPU_F32_SKINNING_PROBE_SAMPLES,
};
use makepad_widgets::*;
use rusty_quest_makepad_camera_shell::{
    QuestMakepadGpuSkinningProbe, QuestMakepadGpuSkinningProbeInput,
    QuestMakepadGpuSkinningProbeReadback, QuestMakepadGpuSkinningProbeSample,
    QUEST_MAKEPAD_GPU_SKINNING_PROBE_DEFAULT_TOLERANCE, QUEST_MAKEPAD_GPU_SKINNING_PROBE_SAMPLES,
};

pub(crate) fn gpu_skinning_probe_marker_line(
    cx: &mut Cx,
    input: &QuestMakepadGpuSkinningProbeInput,
    phase: &str,
) -> Option<String> {
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

    let readback = cx.xr_gpu_f32_skinning_probe(
        samples,
        sample_count,
        QUEST_MAKEPAD_GPU_SKINNING_PROBE_DEFAULT_TOLERANCE,
    )?;
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
