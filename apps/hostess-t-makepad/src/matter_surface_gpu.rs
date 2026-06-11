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
    XrGpuF32SkinningProbeSample {
        bind_position: sample.bind_position,
        delta0_weight: sample.delta0_weight,
        delta1_weight: sample.delta1_weight,
        delta2_weight: sample.delta2_weight,
        delta3_weight: sample.delta3_weight,
        expected_position: sample.expected_position,
    }
}
