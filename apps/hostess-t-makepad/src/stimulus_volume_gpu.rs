//! Hostess adapter for bounded stimulus-volume GPU proof markers.
//!
//! Quest-Makepad owns the marker contract and CPU oracle. Makepad owns the
//! generic Vulkan compute/readback API. Hostess only prepares, submits, polls,
//! and emits the resulting evidence line.

use crate::runtime_settings::marker_token;
use crate::stimulus_stereo_field::{
    StimulusStereoFieldState, STIMULUS_VOLUME_FRAGMENT_RENDER_PATH,
};
use makepad_widgets::makepad_platform::{
    XrGpuF32VolumeImagePreviewOutput, XrGpuF32VolumeImagePreviewPixel,
    XrGpuF32VolumeImagePreviewResult, XrGpuF32VolumeImagePreviewTextureAdoption,
    XrGpuF32VolumeImagePreviewTicket, XrGpuF32VolumeProbeOutput, XrGpuF32VolumeProbeResult,
    XrGpuF32VolumeProbeSample, XrGpuF32VolumeProbeTicket, XrGpuF32VolumeRaymarchPreviewOutput,
    XrGpuF32VolumeRaymarchPreviewPixel, XrGpuF32VolumeRaymarchPreviewResult,
    XrGpuF32VolumeRaymarchPreviewTicket, XR_GPU_F32_VOLUME_IMAGE_PREVIEW_PIXELS,
    XR_GPU_F32_VOLUME_PROBE_SAMPLES, XR_GPU_F32_VOLUME_RAYMARCH_PREVIEW_PIXELS,
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

#[derive(Clone, Debug)]
pub(crate) struct StimulusVolumeImagePreviewReady {
    pub(crate) request_id: u64,
    pub(crate) marker_line: String,
    pub(crate) texture_rgba: Vec<f32>,
    pub(crate) readback: QuestMakepadStimulusVolumeImagePreviewReadback,
    pub(crate) profile_id: String,
    pub(crate) profile_sha256: String,
}

#[derive(Clone, Debug)]
pub(crate) struct StimulusVolumeTextureBindingEvidence {
    pub(crate) texture_source: &'static str,
    pub(crate) resource_plane: &'static str,
    pub(crate) texture_format: &'static str,
    pub(crate) texture_upload_bytes: usize,
    pub(crate) platform_texture_adopted: bool,
    pub(crate) cpu_texture_upload_performed: bool,
    pub(crate) zero_copy_vulkan_image: bool,
    pub(crate) image_ownership_transferred: bool,
    pub(crate) texture_resource_generation: u64,
    pub(crate) replaced_existing_texture_resource: bool,
}

impl StimulusVolumeTextureBindingEvidence {
    pub(crate) fn cpu_upload(texture_upload_bytes: usize) -> Self {
        Self {
            texture_source: "volume-image-preview-readback-cpu-upload",
            resource_plane: "hostess-cpu-uploaded-makepad-texture",
            texture_format: "VecRGBAf32",
            texture_upload_bytes,
            platform_texture_adopted: false,
            cpu_texture_upload_performed: true,
            zero_copy_vulkan_image: false,
            image_ownership_transferred: false,
            texture_resource_generation: 0,
            replaced_existing_texture_resource: false,
        }
    }

    pub(crate) fn gpu_adoption(adoption: XrGpuF32VolumeImagePreviewTextureAdoption) -> Self {
        Self {
            texture_source: "volume-image-preview-retained-vulkan-image",
            resource_plane: "makepad-vulkan-retained-image-texture",
            texture_format: "PlatformRGBAf32",
            texture_upload_bytes: 0,
            platform_texture_adopted: true,
            cpu_texture_upload_performed: adoption.cpu_texture_upload_performed,
            zero_copy_vulkan_image: adoption.zero_copy_vulkan_image,
            image_ownership_transferred: adoption.image_ownership_transferred,
            texture_resource_generation: adoption.texture_resource_generation,
            replaced_existing_texture_resource: adoption.replaced_existing_texture_resource,
        }
    }
}

impl StimulusVolumeImagePreviewReady {
    pub(crate) fn readback_matched(&self) -> bool {
        self.readback.readback_matched()
    }

    pub(crate) fn texture_upload_bytes(&self) -> usize {
        self.texture_rgba.len() * std::mem::size_of::<f32>()
    }

    pub(crate) fn texture_adoption_marker_line(
        &self,
        phase: &str,
        panel_bound: bool,
        shader_texture_slot: usize,
        binding: &StimulusVolumeTextureBindingEvidence,
    ) -> String {
        format!(
            "RUSTY_HOSTESS_MAKEPAD_STIMULUS_VOLUME_TEXTURE_ADOPTION schema=rusty.hostess.makepad.stimulus_volume_texture_adoption.v1 phase={} status={} panelBound={} profileId={} profileSha256={} renderPath={} validationTexturePath=makepad-xr-fragment-preview sourceProof=RUSTY_QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW textureSource={} resourcePlane={} sourceRequestId={} imageWidth={} imageHeight={} imageLayers={} eyeTileWidth={} eyeTileHeight={} eyeCount={} pixelCount={} textureFormat={} textureUploadBytes={} cpuTextureUploadPerformed={} platformTextureAdopted={} shaderTextureSlot={} stereoAtlasMapping=left-right-eye-tiles stereoFiducialAnchors=center-and-four-corners runtimeTextureBound={} sampledTextureBound={} sourceReadbackMatched={} zeroCopyVulkanImage={} imageOwnershipTransferred={} storageImageResident={} storageImageWritten={} transferReadbackPerformed={} sampledImageUsage={} highRateJsonPayload=false fragmentVolumeRenderer=true runtimeVolumeRenderer=true gpuRenderReady=true gpuComputeReady=false computeKernel=false queueSubmitSerial={} fenceSerial={} resourceGeneration={} textureResourceGeneration={} replacedExistingTextureResource={} queueWaitIdlePerformed={} elapsedMs={}",
            marker_token(phase),
            if !self.readback_matched() {
                "rejected-source-mismatch"
            } else if binding.platform_texture_adopted {
                "runtime-gpu-texture-bound"
            } else {
                "runtime-cpu-upload-texture-bound"
            },
            panel_bound,
            marker_token(&self.profile_id),
            marker_token(&self.profile_sha256),
            STIMULUS_VOLUME_FRAGMENT_RENDER_PATH,
            binding.texture_source,
            binding.resource_plane,
            self.request_id,
            self.readback.image_width,
            self.readback.image_height,
            self.readback.image_layers,
            self.readback.eye_tile_width,
            self.readback.eye_tile_height,
            self.readback.eye_count,
            self.readback.pixel_count,
            binding.texture_format,
            binding.texture_upload_bytes,
            binding.cpu_texture_upload_performed,
            binding.platform_texture_adopted,
            shader_texture_slot,
            panel_bound && self.readback_matched(),
            self.readback.sampled_texture_bound,
            self.readback_matched(),
            binding.zero_copy_vulkan_image,
            binding.image_ownership_transferred,
            self.readback.sampled_image_usage,
            self.readback.storage_image_written,
            self.readback.transfer_readback_performed,
            self.readback.sampled_image_usage,
            self.readback.queue_submit_serial,
            self.readback.fence_serial,
            self.readback.resource_generation,
            binding.texture_resource_generation,
            binding.replaced_existing_texture_resource,
            self.readback.queue_wait_idle_performed,
            finite_f64_marker_token(self.readback.elapsed_ms),
        )
    }
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

pub(crate) fn stimulus_volume_image_preview_poll_ready(
    cx: &mut Cx,
    pending: &PendingStimulusVolumeImagePreview,
    phase: &str,
) -> Option<StimulusVolumeImagePreviewReady> {
    let readback = cx.xr_gpu_f32_volume_image_preview_poll(pending.ticket.request_id)?;
    stimulus_volume_image_preview_ready_from_readback(
        &pending.input,
        pending.ticket.request_id,
        readback,
        phase,
    )
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

fn stimulus_volume_image_preview_ready_from_readback(
    input: &QuestMakepadStimulusVolumeImagePreviewInput,
    request_id: u64,
    readback: XrGpuF32VolumeImagePreviewResult,
    phase: &str,
) -> Option<StimulusVolumeImagePreviewReady> {
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

    let readback = QuestMakepadStimulusVolumeImagePreviewReadback {
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
    };

    let proof = QuestMakepadStimulusVolumeImagePreview::from_input(input, readback);
    Some(StimulusVolumeImagePreviewReady {
        request_id,
        marker_line: proof.marker_line(phase),
        texture_rgba: stimulus_volume_image_preview_texture_rgba(&proof.readback),
        readback: proof.readback,
        profile_id: input.raymarch_input.profile_id.clone(),
        profile_sha256: input.raymarch_input.profile_sha256.clone(),
    })
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

fn stimulus_volume_image_preview_texture_rgba(
    readback: &QuestMakepadStimulusVolumeImagePreviewReadback,
) -> Vec<f32> {
    let image_pixel_count = readback.image_width.saturating_mul(readback.image_height);
    let mut texture_rgba = vec![0.0; image_pixel_count.saturating_mul(4)];
    for pixel in texture_rgba.chunks_exact_mut(4) {
        pixel[3] = 1.0;
    }

    for (index, output) in readback
        .outputs
        .iter()
        .copied()
        .take(readback.pixel_count.min(image_pixel_count))
        .enumerate()
    {
        let start = index * 4;
        texture_rgba[start..start + 4].copy_from_slice(&output.rgba);
    }
    texture_rgba
}

fn finite_f64_marker_token(value: f64) -> String {
    if value.is_finite() {
        format!("{value:.3}")
    } else {
        "nonfinite".to_string()
    }
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

    #[test]
    fn image_preview_ready_builds_texture_payload_and_adoption_marker() {
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
        let input = stimulus_volume_image_preview_input_from_state(&state).expect("image input");
        let mut result = XrGpuF32VolumeImagePreviewResult {
            image_width: input.image_width,
            image_height: input.image_height,
            image_layers: input.image_layers,
            eye_tile_width: input.eye_tile_width,
            eye_tile_height: input.eye_tile_height,
            eye_count: input.eye_count,
            pixel_count: input.pixel_count,
            component_count: input.pixel_count * 4,
            tolerance: QUEST_MAKEPAD_STIMULUS_VOLUME_IMAGE_PREVIEW_DEFAULT_TOLERANCE,
            storage_image_written: true,
            transfer_readback_performed: true,
            sampled_image_usage: true,
            sampled_texture_bound: true,
            queue_submit_serial: 12,
            fence_serial: 12,
            resource_generation: 1,
            ..XrGpuF32VolumeImagePreviewResult::default()
        };
        for (index, output) in result
            .outputs
            .iter_mut()
            .enumerate()
            .take(input.pixel_count)
        {
            let value = index as f32 / input.pixel_count as f32;
            output.rgba = [value, 1.0 - value, 0.25, 0.75];
        }
        result.expected_outputs = result.outputs;

        let ready = stimulus_volume_image_preview_ready_from_readback(&input, 12, result, "unit")
            .expect("ready image preview");

        assert!(ready.readback_matched());
        assert_eq!(
            ready.texture_rgba.len(),
            input.image_width * input.image_height * 4
        );
        assert_eq!(&ready.texture_rgba[0..4], &[0.0, 1.0, 0.25, 0.75]);
        let marker = ready.texture_adoption_marker_line(
            "unit",
            true,
            0,
            &StimulusVolumeTextureBindingEvidence::cpu_upload(ready.texture_upload_bytes()),
        );
        assert!(marker.contains("status=runtime-cpu-upload-texture-bound"));
        assert!(marker.contains("runtimeTextureBound=true"));
        assert!(marker.contains("textureSource=volume-image-preview-readback-cpu-upload"));
        assert!(marker.contains("zeroCopyVulkanImage=false"));
        assert!(marker.contains("gpuComputeReady=false"));
        assert!(marker.contains("textureUploadBytes=512"));
    }

    #[test]
    fn image_preview_gpu_binding_marker_preserves_compute_boundary() {
        let ready = StimulusVolumeImagePreviewReady {
            request_id: 44,
            marker_line: "source".to_owned(),
            texture_rgba: vec![0.0; 128],
            readback: QuestMakepadStimulusVolumeImagePreviewReadback {
                image_width: 8,
                image_height: 4,
                image_layers: 1,
                eye_tile_width: 4,
                eye_tile_height: 4,
                eye_count: 2,
                pixel_count: 32,
                component_count: 128,
                storage_image_written: true,
                transfer_readback_performed: true,
                sampled_image_usage: true,
                sampled_texture_bound: true,
                ..QuestMakepadStimulusVolumeImagePreviewReadback::default()
            },
            profile_id: "stimulus.profile.volume.test".to_owned(),
            profile_sha256: "0123456789abcdef".to_owned(),
        };
        let binding = StimulusVolumeTextureBindingEvidence::gpu_adoption(
            XrGpuF32VolumeImagePreviewTextureAdoption {
                request_id: 44,
                image_width: 8,
                image_height: 4,
                image_layers: 1,
                queue_submit_serial: 44,
                resource_generation: 1,
                texture_resource_generation: 2,
                runtime_texture_bound: true,
                zero_copy_vulkan_image: true,
                image_ownership_transferred: true,
                ..XrGpuF32VolumeImagePreviewTextureAdoption::default()
            },
        );
        let marker = ready.texture_adoption_marker_line("unit", true, 0, &binding);
        assert!(marker.contains("status=runtime-gpu-texture-bound"));
        assert!(marker.contains("textureSource=volume-image-preview-retained-vulkan-image"));
        assert!(marker.contains("resourcePlane=makepad-vulkan-retained-image-texture"));
        assert!(marker.contains("textureFormat=PlatformRGBAf32"));
        assert!(marker.contains("textureUploadBytes=0"));
        assert!(marker.contains("cpuTextureUploadPerformed=false"));
        assert!(marker.contains("platformTextureAdopted=true"));
        assert!(marker.contains("zeroCopyVulkanImage=true"));
        assert!(marker.contains("imageOwnershipTransferred=true"));
        assert!(marker.contains("gpuComputeReady=false"));
    }
}
