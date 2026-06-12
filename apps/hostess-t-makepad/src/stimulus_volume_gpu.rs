//! Hostess adapter for bounded stimulus-volume GPU proof markers.
//!
//! Quest-Makepad owns the marker contract and CPU oracle. Makepad owns the
//! generic Vulkan compute/readback API. Hostess only prepares, submits, polls,
//! and emits the resulting evidence line.

use crate::stimulus_stereo_field::StimulusStereoFieldState;
use makepad_widgets::makepad_platform::{
    XrGpuF32VolumeImagePreviewOutput, XrGpuF32VolumeImagePreviewPixel,
    XrGpuF32VolumeImagePreviewResult, XrGpuF32VolumeImagePreviewTicket, XrGpuF32VolumeProbeOutput,
    XrGpuF32VolumeProbeResult, XrGpuF32VolumeProbeSample, XrGpuF32VolumeProbeTicket,
    XrGpuF32VolumeRaymarchPreviewOutput, XrGpuF32VolumeRaymarchPreviewPixel,
    XrGpuF32VolumeRaymarchPreviewResult, XrGpuF32VolumeRaymarchPreviewTicket,
    XR_GPU_F32_VOLUME_IMAGE_PREVIEW_PIXELS, XR_GPU_F32_VOLUME_PROBE_SAMPLES,
    XR_GPU_F32_VOLUME_RAYMARCH_PREVIEW_PIXELS,
};
use makepad_widgets::*;
use rusty_quest_makepad_camera_shell::{
    QuestMakepadStimulusVolumeImagePreview, QuestMakepadStimulusVolumeImagePreviewInput,
    QuestMakepadStimulusVolumeImagePreviewOutput, QuestMakepadStimulusVolumeImagePreviewPixel,
    QuestMakepadStimulusVolumeImagePreviewReadback, QuestMakepadStimulusVolumeProbe,
    QuestMakepadStimulusVolumeProbeInput, QuestMakepadStimulusVolumeProbeOutput,
    QuestMakepadStimulusVolumeProbeReadback, QuestMakepadStimulusVolumeProbeSample,
    QuestMakepadStimulusVolumeRaymarchPreview, QuestMakepadStimulusVolumeRaymarchPreviewInput,
    QuestMakepadStimulusVolumeRaymarchPreviewOutput,
    QuestMakepadStimulusVolumeRaymarchPreviewPixel,
    QuestMakepadStimulusVolumeRaymarchPreviewReadback, StimulusVolumeProfileSummary,
    QUEST_MAKEPAD_STIMULUS_VOLUME_GPU_PROBE_DEFAULT_TOLERANCE,
    QUEST_MAKEPAD_STIMULUS_VOLUME_GPU_PROBE_SAMPLES,
    QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW_DEFAULT_TOLERANCE,
    QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW_PIXELS,
    QUEST_MAKEPAD_STIMULUS_VOLUME_RAYMARCH_PREVIEW_DEFAULT_TOLERANCE,
    QUEST_MAKEPAD_STIMULUS_VOLUME_RAYMARCH_PREVIEW_PIXELS,
};

#[derive(Clone, Debug)]
pub(crate) struct PendingStimulusVolumeGpuProbe {
    input: QuestMakepadStimulusVolumeProbeInput,
    ticket: XrGpuF32VolumeProbeTicket,
}

#[derive(Clone, Debug)]
pub(crate) struct PendingStimulusVolumeRaymarchPreview {
    input: QuestMakepadStimulusVolumeRaymarchPreviewInput,
    ticket: XrGpuF32VolumeRaymarchPreviewTicket,
}

#[derive(Clone, Debug)]
pub(crate) struct PendingStimulusVolumeImagePreview {
    input: QuestMakepadStimulusVolumeImagePreviewInput,
    ticket: XrGpuF32VolumeImagePreviewTicket,
}

struct PreparedStimulusVolumeGpuProbe {
    samples: [XrGpuF32VolumeProbeSample; XR_GPU_F32_VOLUME_PROBE_SAMPLES],
    sample_count: usize,
}

struct PreparedStimulusVolumeRaymarchPreview {
    pixels: [XrGpuF32VolumeRaymarchPreviewPixel; XR_GPU_F32_VOLUME_RAYMARCH_PREVIEW_PIXELS],
    pixel_count: usize,
}

struct PreparedStimulusVolumeImagePreview {
    pixels: [XrGpuF32VolumeImagePreviewPixel; XR_GPU_F32_VOLUME_IMAGE_PREVIEW_PIXELS],
    pixel_count: usize,
}

pub(crate) fn stimulus_volume_probe_input_from_state(
    state: &StimulusStereoFieldState,
) -> Option<QuestMakepadStimulusVolumeProbeInput> {
    if !state.enabled || !state.volume_present {
        return None;
    }
    let summary = StimulusVolumeProfileSummary {
        volume_present: state.volume_present,
        volume_schema: Some(state.volume_schema.clone()),
        volume_id: Some(state.volume_id.clone()),
        field_kind: Some(state.volume_field_kind.clone()),
        storage_hint: Some(state.volume_storage_hint.clone()),
        grid_dimensions: Some(state.volume_grid_dimensions),
        step_count: Some(state.volume_step_count),
        kernel_abi_id: Some(state.kernel_abi_id.clone()),
        compute_pass_count: state.compute_pass_count,
        volume_readback_probe_samples: Some(state.volume_readback_probe_samples),
        stereo_field_output_layers: Some(state.stereo_field_output_layers),
    };
    QuestMakepadStimulusVolumeProbeInput::from_profile_summary(
        state.profile_id.clone(),
        state.profile_sha256.clone(),
        &summary,
    )
}

pub(crate) fn stimulus_volume_raymarch_preview_input_from_state(
    state: &StimulusStereoFieldState,
) -> Option<QuestMakepadStimulusVolumeRaymarchPreviewInput> {
    let probe_input = stimulus_volume_probe_input_from_state(state)?;
    Some(QuestMakepadStimulusVolumeRaymarchPreviewInput::from_volume_probe_input(&probe_input))
}

pub(crate) fn stimulus_volume_image_preview_input_from_state(
    state: &StimulusStereoFieldState,
) -> Option<QuestMakepadStimulusVolumeImagePreviewInput> {
    let raymarch_input = stimulus_volume_raymarch_preview_input_from_state(state)?;
    Some(QuestMakepadStimulusVolumeImagePreviewInput::from_raymarch_preview_input(&raymarch_input))
}

pub(crate) fn stimulus_volume_gpu_probe_submit(
    cx: &mut Cx,
    input: &QuestMakepadStimulusVolumeProbeInput,
) -> Option<PendingStimulusVolumeGpuProbe> {
    let prepared = prepare_stimulus_volume_gpu_probe(input)?;
    let ticket = cx.xr_gpu_f32_volume_probe_submit(
        prepared.samples,
        prepared.sample_count,
        QUEST_MAKEPAD_STIMULUS_VOLUME_GPU_PROBE_DEFAULT_TOLERANCE,
    )?;
    Some(PendingStimulusVolumeGpuProbe {
        input: input.clone(),
        ticket,
    })
}

pub(crate) fn stimulus_volume_gpu_probe_poll_marker_line(
    cx: &mut Cx,
    pending: &PendingStimulusVolumeGpuProbe,
    phase: &str,
) -> Option<String> {
    let readback = cx.xr_gpu_f32_volume_probe_poll(pending.ticket.request_id)?;
    stimulus_volume_gpu_probe_marker_line_from_readback(&pending.input, readback, phase)
}

pub(crate) fn stimulus_volume_raymarch_preview_submit(
    cx: &mut Cx,
    input: &QuestMakepadStimulusVolumeRaymarchPreviewInput,
) -> Option<PendingStimulusVolumeRaymarchPreview> {
    let prepared = prepare_stimulus_volume_raymarch_preview(input)?;
    let ticket = cx.xr_gpu_f32_volume_raymarch_preview_submit(
        prepared.pixels,
        input.preview_width,
        input.preview_height,
        input.eye_count,
        prepared.pixel_count,
        QUEST_MAKEPAD_STIMULUS_VOLUME_RAYMARCH_PREVIEW_DEFAULT_TOLERANCE,
    )?;
    Some(PendingStimulusVolumeRaymarchPreview {
        input: input.clone(),
        ticket,
    })
}

pub(crate) fn stimulus_volume_raymarch_preview_poll_marker_line(
    cx: &mut Cx,
    pending: &PendingStimulusVolumeRaymarchPreview,
    phase: &str,
) -> Option<String> {
    let readback = cx.xr_gpu_f32_volume_raymarch_preview_poll(pending.ticket.request_id)?;
    stimulus_volume_raymarch_preview_marker_line_from_readback(&pending.input, readback, phase)
}

pub(crate) fn stimulus_volume_image_preview_submit(
    cx: &mut Cx,
    input: &QuestMakepadStimulusVolumeImagePreviewInput,
) -> Option<PendingStimulusVolumeImagePreview> {
    let prepared = prepare_stimulus_volume_image_preview(input)?;
    let ticket = cx.xr_gpu_f32_volume_image_preview_submit(
        prepared.pixels,
        input.eye_tile_width,
        input.eye_tile_height,
        input.eye_count,
        prepared.pixel_count,
        QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW_DEFAULT_TOLERANCE,
    )?;
    Some(PendingStimulusVolumeImagePreview {
        input: input.clone(),
        ticket,
    })
}

pub(crate) fn stimulus_volume_image_preview_poll_marker_line(
    cx: &mut Cx,
    pending: &PendingStimulusVolumeImagePreview,
    phase: &str,
) -> Option<String> {
    let readback = cx.xr_gpu_f32_volume_image_preview_poll(pending.ticket.request_id)?;
    stimulus_volume_image_preview_marker_line_from_readback(&pending.input, readback, phase)
}

fn prepare_stimulus_volume_gpu_probe(
    input: &QuestMakepadStimulusVolumeProbeInput,
) -> Option<PreparedStimulusVolumeGpuProbe> {
    let sample_count = input
        .sample_count
        .min(QUEST_MAKEPAD_STIMULUS_VOLUME_GPU_PROBE_SAMPLES)
        .min(XR_GPU_F32_VOLUME_PROBE_SAMPLES);
    if sample_count == 0 {
        return None;
    }

    let mut samples = [XrGpuF32VolumeProbeSample::default(); XR_GPU_F32_VOLUME_PROBE_SAMPLES];
    for (target, source) in samples
        .iter_mut()
        .zip(input.samples.iter().copied())
        .take(sample_count)
    {
        *target = makepad_volume_probe_sample(source);
    }

    Some(PreparedStimulusVolumeGpuProbe {
        samples,
        sample_count,
    })
}

fn prepare_stimulus_volume_raymarch_preview(
    input: &QuestMakepadStimulusVolumeRaymarchPreviewInput,
) -> Option<PreparedStimulusVolumeRaymarchPreview> {
    let pixel_count = input
        .pixel_count
        .min(QUEST_MAKEPAD_STIMULUS_VOLUME_RAYMARCH_PREVIEW_PIXELS)
        .min(XR_GPU_F32_VOLUME_RAYMARCH_PREVIEW_PIXELS);
    if pixel_count == 0 {
        return None;
    }

    let mut pixels =
        [XrGpuF32VolumeRaymarchPreviewPixel::default(); XR_GPU_F32_VOLUME_RAYMARCH_PREVIEW_PIXELS];
    for (target, source) in pixels
        .iter_mut()
        .zip(input.pixels.iter().copied())
        .take(pixel_count)
    {
        *target = makepad_volume_raymarch_preview_pixel(source);
    }

    Some(PreparedStimulusVolumeRaymarchPreview {
        pixels,
        pixel_count,
    })
}

fn prepare_stimulus_volume_image_preview(
    input: &QuestMakepadStimulusVolumeImagePreviewInput,
) -> Option<PreparedStimulusVolumeImagePreview> {
    let pixel_count = input
        .pixel_count
        .min(QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW_PIXELS)
        .min(XR_GPU_F32_VOLUME_IMAGE_PREVIEW_PIXELS);
    if pixel_count == 0 {
        return None;
    }

    let mut pixels =
        [XrGpuF32VolumeImagePreviewPixel::default(); XR_GPU_F32_VOLUME_IMAGE_PREVIEW_PIXELS];
    for (target, source) in pixels
        .iter_mut()
        .zip(input.pixels().iter().copied())
        .take(pixel_count)
    {
        *target = makepad_volume_image_preview_pixel(source);
    }

    Some(PreparedStimulusVolumeImagePreview {
        pixels,
        pixel_count,
    })
}

fn stimulus_volume_gpu_probe_marker_line_from_readback(
    input: &QuestMakepadStimulusVolumeProbeInput,
    readback: XrGpuF32VolumeProbeResult,
    phase: &str,
) -> Option<String> {
    let mut outputs = [QuestMakepadStimulusVolumeProbeOutput::default();
        QUEST_MAKEPAD_STIMULUS_VOLUME_GPU_PROBE_SAMPLES];
    let mut expected_outputs = [QuestMakepadStimulusVolumeProbeOutput::default();
        QUEST_MAKEPAD_STIMULUS_VOLUME_GPU_PROBE_SAMPLES];
    for (target, source) in outputs
        .iter_mut()
        .zip(readback.outputs.iter().copied())
        .take(
            readback
                .sample_count
                .min(QUEST_MAKEPAD_STIMULUS_VOLUME_GPU_PROBE_SAMPLES),
        )
    {
        *target = quest_volume_probe_output(source);
    }
    for (target, source) in expected_outputs
        .iter_mut()
        .zip(readback.expected_outputs.iter().copied())
        .take(
            readback
                .sample_count
                .min(QUEST_MAKEPAD_STIMULUS_VOLUME_GPU_PROBE_SAMPLES),
        )
    {
        *target = quest_volume_probe_output(source);
    }

    let probe = QuestMakepadStimulusVolumeProbe::from_input(
        input,
        QuestMakepadStimulusVolumeProbeReadback {
            sample_count: readback.sample_count,
            component_count: readback.component_count,
            mismatched_components: readback.mismatched_components,
            max_abs_error: readback.max_abs_error,
            tolerance: readback.tolerance,
            outputs,
            expected_outputs,
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

fn stimulus_volume_raymarch_preview_marker_line_from_readback(
    input: &QuestMakepadStimulusVolumeRaymarchPreviewInput,
    readback: XrGpuF32VolumeRaymarchPreviewResult,
    phase: &str,
) -> Option<String> {
    let mut outputs = [QuestMakepadStimulusVolumeRaymarchPreviewOutput::default();
        QUEST_MAKEPAD_STIMULUS_VOLUME_RAYMARCH_PREVIEW_PIXELS];
    let mut expected_outputs = [QuestMakepadStimulusVolumeRaymarchPreviewOutput::default();
        QUEST_MAKEPAD_STIMULUS_VOLUME_RAYMARCH_PREVIEW_PIXELS];
    for (target, source) in outputs
        .iter_mut()
        .zip(readback.outputs.iter().copied())
        .take(
            readback
                .pixel_count
                .min(QUEST_MAKEPAD_STIMULUS_VOLUME_RAYMARCH_PREVIEW_PIXELS),
        )
    {
        *target = quest_volume_raymarch_preview_output(source);
    }
    for (target, source) in expected_outputs
        .iter_mut()
        .zip(readback.expected_outputs.iter().copied())
        .take(
            readback
                .pixel_count
                .min(QUEST_MAKEPAD_STIMULUS_VOLUME_RAYMARCH_PREVIEW_PIXELS),
        )
    {
        *target = quest_volume_raymarch_preview_output(source);
    }

    let proof = QuestMakepadStimulusVolumeRaymarchPreview::from_input(
        input,
        QuestMakepadStimulusVolumeRaymarchPreviewReadback {
            preview_width: readback.preview_width,
            preview_height: readback.preview_height,
            eye_count: readback.eye_count,
            pixel_count: readback.pixel_count,
            component_count: readback.component_count,
            mismatched_components: readback.mismatched_components,
            max_abs_error: readback.max_abs_error,
            tolerance: readback.tolerance,
            outputs,
            expected_outputs,
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
    Some(proof.marker_line(phase))
}

fn stimulus_volume_image_preview_marker_line_from_readback(
    input: &QuestMakepadStimulusVolumeImagePreviewInput,
    readback: XrGpuF32VolumeImagePreviewResult,
    phase: &str,
) -> Option<String> {
    let mut outputs = [QuestMakepadStimulusVolumeImagePreviewOutput::default();
        QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW_PIXELS];
    let mut expected_outputs = [QuestMakepadStimulusVolumeImagePreviewOutput::default();
        QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW_PIXELS];
    for (target, source) in outputs
        .iter_mut()
        .zip(readback.outputs.iter().copied())
        .take(
            readback
                .pixel_count
                .min(QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW_PIXELS),
        )
    {
        *target = quest_volume_image_preview_output(source);
    }
    for (target, source) in expected_outputs
        .iter_mut()
        .zip(readback.expected_outputs.iter().copied())
        .take(
            readback
                .pixel_count
                .min(QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW_PIXELS),
        )
    {
        *target = quest_volume_image_preview_output(source);
    }

    let proof = QuestMakepadStimulusVolumeImagePreview::from_input(
        input,
        QuestMakepadStimulusVolumeImagePreviewReadback {
            image_width: readback.image_width,
            image_height: readback.image_height,
            image_layers: readback.image_layers,
            eye_tile_width: readback.eye_tile_width,
            eye_tile_height: readback.eye_tile_height,
            eye_count: readback.eye_count,
            pixel_count: readback.pixel_count,
            component_count: readback.component_count,
            mismatched_components: readback.mismatched_components,
            max_abs_error: readback.max_abs_error,
            tolerance: readback.tolerance,
            outputs,
            expected_outputs,
            queue_submit_serial: readback.queue_submit_serial,
            fence_serial: readback.fence_serial,
            resource_generation: readback.resource_generation,
            pending_retire_count: readback.pending_retire_count,
            retained_resource_count: readback.retained_resource_count,
            retired_after_fence_count: readback.retired_after_fence_count,
            storage_image_written: readback.storage_image_written,
            transfer_readback_performed: readback.transfer_readback_performed,
            sampled_image_usage: readback.sampled_image_usage,
            sampled_texture_bound: readback.sampled_texture_bound,
            queue_wait_idle_performed: readback.queue_wait_idle_performed,
            elapsed_ms: readback.elapsed_ms,
        },
    );
    Some(proof.marker_line(phase))
}

fn makepad_volume_probe_sample(
    sample: QuestMakepadStimulusVolumeProbeSample,
) -> XrGpuF32VolumeProbeSample {
    XrGpuF32VolumeProbeSample {
        uv_eye_time: sample.uv_eye_time,
        ray_origin_depth: sample.ray_origin_depth,
        ray_direction_step: sample.ray_direction_step,
        volume_params: sample.volume_params,
        expected_rgba: sample.expected_rgba,
        expected_density_depth_status: sample.expected_density_depth_status,
    }
}

fn makepad_volume_raymarch_preview_pixel(
    pixel: QuestMakepadStimulusVolumeRaymarchPreviewPixel,
) -> XrGpuF32VolumeRaymarchPreviewPixel {
    XrGpuF32VolumeRaymarchPreviewPixel {
        uv_eye_time: pixel.uv_eye_time,
        ray_origin: pixel.ray_origin,
        ray_direction_step: pixel.ray_direction_step,
        volume_params: pixel.volume_params,
        expected_rgba: pixel.expected_rgba,
        expected_density_depth_status: pixel.expected_density_depth_status,
    }
}

fn makepad_volume_image_preview_pixel(
    pixel: QuestMakepadStimulusVolumeImagePreviewPixel,
) -> XrGpuF32VolumeImagePreviewPixel {
    XrGpuF32VolumeImagePreviewPixel {
        uv_eye_time: pixel.uv_eye_time,
        ray_origin: pixel.ray_origin,
        ray_direction_step: pixel.ray_direction_step,
        volume_params: pixel.volume_params,
        expected_rgba: pixel.expected_rgba,
        expected_density_depth_status: pixel.expected_density_depth_status,
    }
}

fn quest_volume_probe_output(
    output: XrGpuF32VolumeProbeOutput,
) -> QuestMakepadStimulusVolumeProbeOutput {
    QuestMakepadStimulusVolumeProbeOutput {
        rgba: output.rgba,
        density_depth_status: output.density_depth_status,
    }
}

fn quest_volume_raymarch_preview_output(
    output: XrGpuF32VolumeRaymarchPreviewOutput,
) -> QuestMakepadStimulusVolumeRaymarchPreviewOutput {
    QuestMakepadStimulusVolumeRaymarchPreviewOutput {
        rgba: output.rgba,
        density_depth_status: output.density_depth_status,
    }
}

fn quest_volume_image_preview_output(
    output: XrGpuF32VolumeImagePreviewOutput,
) -> QuestMakepadStimulusVolumeImagePreviewOutput {
    QuestMakepadStimulusVolumeImagePreviewOutput { rgba: output.rgba }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_volume_probe_input_from_stimulus_state() {
        let state = StimulusStereoFieldState {
            enabled: true,
            profile_id: "stimulus.profile.volume.test".to_owned(),
            profile_sha256: "0123456789abcdef".to_owned(),
            volume_present: true,
            volume_schema: "rusty.optics.stimulus.volume.v1".to_owned(),
            volume_id: "stimulus.volume.test".to_owned(),
            volume_field_kind: "ProceduralLayerStack3d".to_owned(),
            volume_storage_hint: "StorageBuffer".to_owned(),
            volume_grid_dimensions: [32, 32, 32],
            volume_step_count: 32,
            kernel_abi_id: "stimulus.kernel.volume_compute_v1".to_owned(),
            compute_pass_count: 3,
            volume_readback_probe_samples: 512,
            stereo_field_output_layers: 2,
            ..StimulusStereoFieldState::default()
        };

        let input = stimulus_volume_probe_input_from_state(&state).expect("volume input");

        assert_eq!(input.profile_id, state.profile_id);
        assert_eq!(
            input.sample_count,
            QUEST_MAKEPAD_STIMULUS_VOLUME_GPU_PROBE_SAMPLES
        );
        assert_eq!(input.declared_readback_samples, 512);
    }
}
