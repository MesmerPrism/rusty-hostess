use crate::camera_texture_path::MakepadCameraTexturePath;
use crate::hostess_camera_model::{
    rect_xywh, target_footprint_debug_region_marker_fields, uv_rect_token, Rect2,
    SourceSamplingMode, Vec2, LEGACY_RUSTY_XR_TARGET_SCREEN_FOOTPRINT_SCHEMA,
};
use crate::makepad_widgets::makepad_platform::event::video_playback::VideoTextureUpdateMetadata;

use super::{
    hotload_text_any, marker_token, MakepadCameraPair, DEFAULT_CAMERA_LEFT_TARGET_SCREEN_UV_RECT,
    DEFAULT_CAMERA_RIGHT_TARGET_SCREEN_UV_RECT, DEFAULT_CAMERA_SOURCE_SAMPLING_MODE,
    DEFAULT_CAMERA_TARGET_SCREEN_UV_RECT, KEY_CAMERA_LEFT_TARGET_SCREEN_UV_RECT,
    KEY_CAMERA_RIGHT_TARGET_SCREEN_UV_RECT, KEY_CAMERA_SOURCE_SAMPLING_MODE,
    KEY_CAMERA_TARGET_SCREEN_UV_RECT, KEY_MAKEPAD_CAMERA_LEFT_TARGET_SCREEN_UV_RECT,
    KEY_MAKEPAD_CAMERA_RIGHT_TARGET_SCREEN_UV_RECT, KEY_MAKEPAD_CAMERA_SOURCE_SAMPLING_MODE,
    KEY_MAKEPAD_CAMERA_TARGET_SCREEN_UV_RECT,
};

mod broker_projection;

// Host builds do not touch every Android/test-only facade item, but the
// source_metadata boundary should keep these names stable for those targets.
#[allow(unused_imports)]
pub(crate) use broker_projection::{
    broker_pair_content_geometry_marker_fields, broker_projection_plan_decision,
    direct_camera2_content_geometry_marker_fields, makepad_content_geometry_marker_fields,
    missing_broker_content_geometry_marker_fields,
    normalize_direct_camera_projection_geometry_profile, stream_header_metadata_marker_fields,
    BrokerH264Extrinsics, BrokerH264Intrinsics, BrokerH264PixelDomain,
    BrokerH264ProjectionMetadata, BrokerProjectionPlanDecision, BrokerProjectionPlanKind,
    MakepadContentGeometrySource,
};

pub(crate) fn aspect_ratio_u32(width: u32, height: u32) -> f64 {
    if width > 0 && height > 0 {
        width as f64 / height as f64
    } else {
        1.0
    }
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct MakepadTargetScreenFootprintPair {
    pub(crate) left_rect: Rect2,
    pub(crate) right_rect: Rect2,
    pub(crate) from_metadata: bool,
    pub(crate) defaulted: bool,
}

impl MakepadTargetScreenFootprintPair {
    pub(crate) fn marker_fields(self) -> String {
        format!(
            "targetFootprintSchema={} targetCoordinateSpace=display-eye-screen-uv leftTargetScreenUvRect={} rightTargetScreenUvRect={} targetClipPolicy=clip-to-visible-eye targetFootprintMetadataSource={} targetFootprintDefault={} effectBoundary=target-footprint borderRegionSemantics=visible-render-surface-minus-target-footprint sourceInvalidSemantics=homography-path-only-target-local-stretch-clamps-edge-sample {}",
            LEGACY_RUSTY_XR_TARGET_SCREEN_FOOTPRINT_SCHEMA,
            target_screen_uv_rect_token(self.left_rect),
            target_screen_uv_rect_token(self.right_rect),
            if self.from_metadata {
                "makepad-direct-camera-target-screen-uv-runtime"
            } else {
                "renderer-authored-fallback"
            },
            self.defaulted,
            target_footprint_debug_region_marker_fields(),
        )
    }
}

pub(crate) fn makepad_default_target_screen_uv_rect(left: bool) -> Rect2 {
    let default = if left {
        DEFAULT_CAMERA_LEFT_TARGET_SCREEN_UV_RECT
    } else {
        DEFAULT_CAMERA_RIGHT_TARGET_SCREEN_UV_RECT
    };
    parse_uv_rect_xywh_text(default).unwrap_or(Rect2::UNIT)
}

pub(crate) fn makepad_runtime_target_screen_footprint_pair() -> MakepadTargetScreenFootprintPair {
    let shared_text = hotload_text_any(
        &[
            KEY_CAMERA_TARGET_SCREEN_UV_RECT,
            KEY_MAKEPAD_CAMERA_TARGET_SCREEN_UV_RECT,
        ],
        DEFAULT_CAMERA_TARGET_SCREEN_UV_RECT,
    );
    let left_default_text = if shared_text.is_empty() {
        DEFAULT_CAMERA_LEFT_TARGET_SCREEN_UV_RECT
    } else {
        shared_text.as_str()
    };
    let right_default_text = if shared_text.is_empty() {
        DEFAULT_CAMERA_RIGHT_TARGET_SCREEN_UV_RECT
    } else {
        shared_text.as_str()
    };
    let left_text = hotload_text_any(
        &[
            KEY_CAMERA_LEFT_TARGET_SCREEN_UV_RECT,
            KEY_MAKEPAD_CAMERA_LEFT_TARGET_SCREEN_UV_RECT,
        ],
        left_default_text,
    );
    let right_text = hotload_text_any(
        &[
            KEY_CAMERA_RIGHT_TARGET_SCREEN_UV_RECT,
            KEY_MAKEPAD_CAMERA_RIGHT_TARGET_SCREEN_UV_RECT,
        ],
        right_default_text,
    );
    let left_rect = parse_uv_rect_xywh_text(&left_text)
        .unwrap_or_else(|| makepad_default_target_screen_uv_rect(true));
    let right_rect = parse_uv_rect_xywh_text(&right_text)
        .unwrap_or_else(|| makepad_default_target_screen_uv_rect(false));
    MakepadTargetScreenFootprintPair {
        left_rect,
        right_rect,
        from_metadata: true,
        defaulted: shared_text.is_empty()
            && left_text == DEFAULT_CAMERA_LEFT_TARGET_SCREEN_UV_RECT
            && right_text == DEFAULT_CAMERA_RIGHT_TARGET_SCREEN_UV_RECT,
    }
}

pub(crate) fn makepad_runtime_camera_source_sampling_mode() -> SourceSamplingMode {
    SourceSamplingMode::parse(&hotload_text_any(
        &[
            KEY_CAMERA_SOURCE_SAMPLING_MODE,
            KEY_MAKEPAD_CAMERA_SOURCE_SAMPLING_MODE,
        ],
        DEFAULT_CAMERA_SOURCE_SAMPLING_MODE,
    ))
    .unwrap_or(SourceSamplingMode::TargetLocalRaster)
}

pub(crate) fn parse_uv_rect_xywh_text(text: &str) -> Option<Rect2> {
    let parts: Vec<f32> = text
        .split(|character| matches!(character, ',' | ';' | ' ' | '\t'))
        .filter(|part| !part.trim().is_empty())
        .filter_map(|part| part.trim().parse::<f32>().ok())
        .collect();
    if parts.len() != 4 {
        return None;
    }
    let rect = Rect2::new(Vec2::new(parts[0], parts[1]), Vec2::new(parts[2], parts[3]));
    target_screen_rect_is_valid(rect).then_some(rect)
}

pub(crate) fn target_screen_uv_rect_token(rect: Rect2) -> String {
    uv_rect_token(rect_xywh(rect))
}

pub(super) fn target_screen_rect_is_valid(rect: Rect2) -> bool {
    rect.is_valid()
        && rect.size.x > 0.0
        && rect.size.y > 0.0
        && rect.origin.x >= 0.0
        && rect.origin.y >= 0.0
        && rect.max().x <= 1.0
        && rect.max().y <= 1.0
}

pub(crate) fn makepad_camera_status_marker_line(
    phase: &str,
    runtime_profile: &str,
    transport_profile: &str,
    makepad_rev: &str,
    studio_host: &str,
) -> String {
    format!(
        "RUSTY_MAKEPAD_CAMERA_STATUS schema=rusty.gui.makepad.camera_status.v1 phase={} profile={} transport={} renderer=makepad android_packager=cargo-makepad makepad_rev={} studio_host={}",
        phase,
        runtime_profile,
        transport_profile,
        makepad_rev,
        studio_host,
    )
}

pub(crate) fn makepad_camera2_acquisition_broker_h264_skipped_marker_line() -> &'static str {
    "RUSTY_MAKEPAD_CAMERA2_ACQUISITION schema=rusty.gui.makepad.camera2_acquisition.v1 phase=start status=skipped reason=broker-h264-enabled import=broker-h264"
}

pub(crate) fn makepad_camera2_acquisition_streaming_disabled_marker_line() -> &'static str {
    "RUSTY_MAKEPAD_CAMERA2_ACQUISITION schema=rusty.gui.makepad.camera2_acquisition.v1 phase=start status=skipped reason=camera-streaming-disabled import=none cameraStreamingEnabled=false"
}

pub(crate) fn makepad_hardware_buffer_import_marker_line(body: &str) -> String {
    format!(
        "RUSTY_MAKEPAD_HARDWARE_BUFFER_IMPORT schema=rusty.gui.makepad.hardware_buffer_import.v1 {}",
        body
    )
}

pub(crate) fn makepad_hardware_buffer_import_enumerated_marker_fields(
    pair: &MakepadCameraPair,
    source_count: usize,
    format_count: usize,
    left_frame_rate: &str,
    right_frame_rate: &str,
    pixel_format: &str,
) -> String {
    hardware_buffer_import_enumerated_marker_fields(
        source_count,
        format_count,
        &pair.source_binding_mode,
        pair.left.source_index,
        pair.right.source_index,
        pair.left.camera_id.as_deref().unwrap_or("unknown"),
        pair.right.camera_id.as_deref().unwrap_or("unknown"),
        pair.left.source_class,
        pair.right.source_class,
        pair.left.width,
        pair.left.height,
        pair.right.width,
        pair.right.height,
        left_frame_rate,
        right_frame_rate,
        pixel_format,
    )
}

pub(crate) fn makepad_hardware_buffer_import_enumerated_error_marker_fields(
    source_count: usize,
    format_count: usize,
) -> String {
    format!(
        "phase=enumerated status=error makepadSourceCount={} makepadFormatCount={} selected=false errorKind=no_yuv420_makepad_camera_stereo_pair",
        source_count,
        format_count,
    )
}

pub(crate) fn makepad_hardware_buffer_import_texture_updated_marker_fields(
    side_label: &str,
    yuv_enabled: bool,
    yuv_biplanar: bool,
    rotation_steps: f32,
    texture_path: MakepadCameraTexturePath,
    metadata: &VideoTextureUpdateMetadata,
    projection_border_policy: &str,
    processing_layer: &str,
) -> String {
    format!(
        "phase=texture-updated status=ok side={} yuvEnabled={} yuvBiplanar={} rotationSteps={:.0} projectionBorderPolicy={} processingLayer={} importPlan={} {}{}",
        side_label,
        yuv_enabled,
        yuv_biplanar,
        rotation_steps,
        marker_token(projection_border_policy),
        marker_token(processing_layer),
        texture_path.import_plan(),
        texture_path.marker_fields(),
        video_texture_update_metadata_marker_fields(metadata),
    )
}

fn video_texture_update_metadata_marker_fields(metadata: &VideoTextureUpdateMetadata) -> String {
    let mut fields = vec![
        format!("eventResourcePath={}", metadata.resource_path.as_str()),
        format!("descriptorShape={}", metadata.descriptor_shape.as_str()),
    ];
    if let Some(value) = metadata.camera_input_id {
        fields.push(format!("cameraInputId={}", (value.0).0));
    }
    if let Some(value) = metadata.camera_format_id {
        fields.push(format!("cameraFormatId={}", (value.0).0));
    }
    if let Some(value) = metadata.camera_frame_sequence {
        fields.push(format!("cameraFrameSeq={value}"));
    }
    if let Some(value) = metadata.camera_timestamp_ns {
        fields.push(format!("cameraTimestampNs={value}"));
    }
    if let Some(value) = metadata.acquire_time_ns {
        fields.push(format!("acquireTimeNs={value}"));
    }
    if let Some(value) = metadata.upload_sequence {
        fields.push(format!("uploadSeq={value}"));
    }
    if let Some(value) = metadata.upload_time_ns {
        fields.push(format!("uploadTimeNs={value}"));
    }
    if let Some(value) = metadata.import_sequence {
        fields.push(format!("importSeq={value}"));
    }
    if let Some(value) = metadata.import_time_ns {
        fields.push(format!("importTimeNs={value}"));
    }
    if let Some(value) = metadata.texture_update_sequence {
        fields.push(format!("textureUpdateSeq={value}"));
    }
    if metadata.width > 0 {
        fields.push(format!("textureWidth={}", metadata.width));
    }
    if metadata.height > 0 {
        fields.push(format!("textureHeight={}", metadata.height));
    }
    if let Some(value) = metadata.vulkan_format.as_deref() {
        fields.push(format!("vulkanFormat={}", marker_token(value)));
    }
    if let Some(value) = metadata.vulkan_external_format {
        fields.push(format!("vulkanExternalFormat={value}"));
    }
    #[cfg(feature = "makepad-hwb-ycbcr-metadata")]
    if let Some(ycbcr) = metadata.ycbcr_conversion.as_ref() {
        fields.push(format!(
            "suggestedYcbcrModel={}",
            marker_token(&ycbcr.suggested_model)
        ));
        fields.push(format!(
            "suggestedYcbcrRange={}",
            marker_token(&ycbcr.suggested_range)
        ));
        fields.push(format!(
            "effectiveYcbcrModel={}",
            marker_token(&ycbcr.effective_model)
        ));
        fields.push(format!(
            "effectiveYcbcrRange={}",
            marker_token(&ycbcr.effective_range)
        ));
        fields.push(format!(
            "ycbcrComponents={}",
            marker_token(&ycbcr.components)
        ));
        fields.push(format!(
            "suggestedXChromaOffset={}",
            marker_token(&ycbcr.suggested_x_chroma_offset)
        ));
        fields.push(format!(
            "suggestedYChromaOffset={}",
            marker_token(&ycbcr.suggested_y_chroma_offset)
        ));
        fields.push(format!(
            "conversionMode={}",
            marker_token(&ycbcr.conversion_mode)
        ));
        fields.push(format!(
            "samplerBindingMode={}",
            marker_token(&ycbcr.sampler_binding_mode)
        ));
        fields.push(format!(
            "samplerBindingCompliance={}",
            marker_token(&ycbcr.sampler_binding_compliance)
        ));
        fields.push(format!(
            "shaderSampleLowering={}",
            marker_token(&ycbcr.shader_sample_lowering)
        ));
        fields.push(
            "colorFixAttempt=hwb-external-combined-immutable-v4-default-sampler-remap".to_string(),
        );
    }
    if let Some(value) = metadata.resource_reused {
        fields.push(format!("resourceReused={value}"));
    }
    if metadata.fallback_active {
        fields.push("fallbackActive=true".to_string());
    }
    if let Some(value) = metadata.fallback_reason.as_deref() {
        fields.push(format!("fallbackReason={}", marker_token(value)));
    }
    format!(" {}", fields.join(" "))
}

pub(crate) fn makepad_hardware_buffer_import_complete_error_marker_fields(
    side_label: &str,
    message: &str,
) -> String {
    format!(
        "phase=complete status=error side={} errorKind=makepad_video_import_failed message={}",
        side_label,
        marker_token(message),
    )
}

pub(crate) fn makepad_hardware_buffer_import_timer_fired_marker_fields(
    source: &str,
    has_pair: bool,
    import_started: bool,
    import_finished: bool,
) -> String {
    format!(
        "phase=timer status=fired source={} hasPair={} importStarted={} importFinished={} importPlan=paired-makepad-video-hardware-buffer",
        source,
        has_pair,
        import_started,
        import_finished,
    )
}

pub(crate) fn makepad_hardware_buffer_import_timer_armed_marker_fields(
    reason: &str,
    delay_seconds: f64,
) -> String {
    format!(
        "phase=timer status=armed reason={} delaySeconds={:.1} signalFallback=true importPlan=paired-makepad-video-hardware-buffer",
        marker_token(reason),
        delay_seconds,
    )
}

pub(crate) fn makepad_stream_header_metadata_ignored_marker_fields(
    video_id: u64,
    texture_path: MakepadCameraTexturePath,
) -> String {
    format!(
        "phase=stream-header-metadata status=ignored side=unknown videoId={} reason=unexpected_video_id textureMode={} importPlan={}",
        video_id,
        texture_path.stable_id(),
        texture_path.import_plan(),
    )
}

pub(crate) fn makepad_stream_header_metadata_error_marker_fields(
    side_label: &str,
    metadata_bytes: usize,
    error: &str,
    texture_path: MakepadCameraTexturePath,
) -> String {
    format!(
        "phase=stream-header-metadata status=error side={} metadataBytes={} error={} textureMode={} importPlan={}",
        side_label,
        metadata_bytes,
        marker_token(error),
        texture_path.stable_id(),
        texture_path.import_plan(),
    )
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn makepad_hardware_buffer_import_broker_h264_startup_marker_fields(
    broker_host: &str,
    broker_port: u16,
    left_stream_port: u16,
    right_stream_port: u16,
    source_mode: &str,
    decode_output_mode: &str,
    synthetic_pattern: &str,
    preferred_width: u32,
    preferred_height: u32,
    live_stream: bool,
    texture_path: MakepadCameraTexturePath,
) -> String {
    format!(
        "phase=startup status=broker-h264-enabled brokerHost={} brokerPort={} leftStreamPort={} rightStreamPort={} sourceMode={} decodeOutputMode={} syntheticPattern={} preferredWidth={} preferredHeight={} liveStream={} textureMode={} importPlan={}",
        marker_token(broker_host),
        broker_port,
        left_stream_port,
        right_stream_port,
        marker_token(source_mode),
        marker_token(decode_output_mode),
        marker_token(synthetic_pattern),
        preferred_width,
        preferred_height,
        live_stream,
        texture_path.stable_id(),
        texture_path.import_plan(),
    )
}

pub(crate) fn makepad_hardware_buffer_import_yuv_textures_ready_broker_marker_fields(
    side_label: &str,
) -> String {
    format!(
        "phase=yuv-textures-ready status=ok side={} textureMode=cpu-yuv-decoded-broker-h264 importPlan=broker-h264-stereo-mediacodec-yuv-texture",
        side_label,
    )
}

pub(crate) fn makepad_hardware_buffer_import_yuv_textures_ready_single_stream_marker_fields(
    side_label: &str,
    texture_path: MakepadCameraTexturePath,
) -> String {
    format!(
        "phase=yuv-textures-ready status=ok side={} textureMode=makepad-yuv-slot-allocation requestedTexturePath={} importPlan={} depthClip=false environmentDepthClip=false",
        side_label,
        texture_path.stable_id(),
        texture_path.import_plan(),
    )
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn makepad_hardware_buffer_import_texture_handle_ready_marker_fields(
    side_label: &str,
    texture_handle: u32,
    broker_host: &str,
    broker_port: u16,
    stream_port: u16,
    source_mode: &str,
    synthetic_pattern: &str,
    live_stream: bool,
) -> String {
    format!(
        "phase=texture-handle-ready status=ok side={} textureHandle={} textureMode=external-oes brokerHost={} brokerPort={} streamPort={} sourceMode={} syntheticPattern={} liveStream={} importPlan=broker-h264-stereo-surface-texture",
        side_label,
        texture_handle,
        marker_token(broker_host),
        broker_port,
        stream_port,
        marker_token(source_mode),
        marker_token(synthetic_pattern),
        live_stream,
    )
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn makepad_hardware_buffer_import_broker_h264_prepare_request_marker_fields(
    side_label: &str,
    broker_host: &str,
    broker_port: u16,
    stream_port: u16,
    source_mode: &str,
    decode_output_mode: &str,
    synthetic_pattern: &str,
    live_stream: bool,
    texture_path: MakepadCameraTexturePath,
) -> String {
    format!(
        "phase=broker-h264-prepare-request status=sent side={} textureHandle=0 textureMode={} brokerHost={} brokerPort={} streamPort={} sourceMode={} decodeOutputMode={} syntheticPattern={} liveStream={} importPlan={}",
        side_label,
        texture_path.stable_id(),
        marker_token(broker_host),
        broker_port,
        stream_port,
        marker_token(source_mode),
        marker_token(decode_output_mode),
        marker_token(synthetic_pattern),
        live_stream,
        texture_path.import_plan(),
    )
}

pub(crate) fn makepad_hardware_buffer_import_prepared_marker_fields(
    side_label: &str,
    width: u32,
    height: u32,
    texture_path: MakepadCameraTexturePath,
) -> String {
    format!(
        "phase=prepared status=ok side={} width={} height={} importPath={} textureMode={} importPlan={} {}",
        side_label,
        width,
        height,
        texture_path.texture_import_path(),
        texture_path.stable_id(),
        texture_path.import_plan(),
        texture_path.marker_fields(),
    )
}

pub(crate) fn makepad_hardware_buffer_import_start_error_marker_fields() -> &'static str {
    "phase=start status=error errorKind=no_makepad_camera_stereo_pair"
}

pub(crate) fn makepad_hardware_buffer_import_start_waiting_marker_fields(
    wait_count: usize,
) -> String {
    format!(
        "phase=start status=waiting waitCount={} reason=no_makepad_camera_stereo_pair_yet",
        wait_count,
    )
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn makepad_hardware_buffer_import_start_marker_fields(
    pair: &MakepadCameraPair,
    broker_h264_enabled: bool,
    left_frame_rate: &str,
    right_frame_rate: &str,
    pixel_format: &str,
    left_stream_port: &str,
    right_stream_port: &str,
    delayed_after_acquisition_seconds: f64,
    texture_path: MakepadCameraTexturePath,
) -> String {
    hardware_buffer_import_start_marker_fields(
        broker_h264_enabled,
        pair.left.source_index,
        pair.right.source_index,
        pair.left.source_class,
        pair.right.source_class,
        pair.left.width,
        pair.left.height,
        pair.right.width,
        pair.right.height,
        left_frame_rate,
        right_frame_rate,
        pixel_format,
        left_stream_port,
        right_stream_port,
        delayed_after_acquisition_seconds,
        texture_path,
    )
}

pub(crate) fn makepad_hardware_buffer_import_raw_video_event_marker_line(
    event_name: &str,
    side_label: &str,
    video_id: u64,
    left_video_id: u64,
    right_video_id: u64,
) -> String {
    format!(
        "RUSTY_MAKEPAD_HARDWARE_BUFFER_IMPORT schema=rusty.gui.makepad.hardware_buffer_import.v1 phase=raw-video-event status=seen event={} side={} videoId={} leftVideoId={} rightVideoId={} depthClip=false environmentDepthClip=false importPlan=makepad-video-texture-event",
        event_name,
        side_label,
        video_id,
        left_video_id,
        right_video_id,
    )
}

#[allow(clippy::too_many_arguments)]
fn hardware_buffer_import_enumerated_marker_fields(
    source_count: usize,
    format_count: usize,
    source_binding_mode: &str,
    left_source_index: usize,
    right_source_index: usize,
    left_camera_id: &str,
    right_camera_id: &str,
    left_source_class: &str,
    right_source_class: &str,
    left_width: usize,
    left_height: usize,
    right_width: usize,
    right_height: usize,
    left_frame_rate: &str,
    right_frame_rate: &str,
    pixel_format: &str,
) -> String {
    format!(
        "phase=enumerated status=ok makepadSourceCount={} makepadFormatCount={} selected=true importPlan=paired-makepad-video-hardware-buffer sourceBindingMode={} leftSourceIndex={} rightSourceIndex={} leftCameraId={} rightCameraId={} leftSourceClass={} rightSourceClass={} leftWidth={} leftHeight={} rightWidth={} rightHeight={} leftFrameRate={} rightFrameRate={} pixelFormat={}",
        source_count,
        format_count,
        source_binding_mode,
        left_source_index,
        right_source_index,
        marker_token(left_camera_id),
        marker_token(right_camera_id),
        left_source_class,
        right_source_class,
        left_width,
        left_height,
        right_width,
        right_height,
        left_frame_rate,
        right_frame_rate,
        pixel_format,
    )
}

#[allow(clippy::too_many_arguments)]
fn hardware_buffer_import_start_marker_fields(
    broker_h264_enabled: bool,
    left_source_index: usize,
    right_source_index: usize,
    left_source_class: &str,
    right_source_class: &str,
    left_width: usize,
    left_height: usize,
    right_width: usize,
    right_height: usize,
    left_frame_rate: &str,
    right_frame_rate: &str,
    pixel_format: &str,
    left_stream_port: &str,
    right_stream_port: &str,
    delayed_after_acquisition_seconds: f64,
    texture_path: MakepadCameraTexturePath,
) -> String {
    let texture_format = match texture_path {
        MakepadCameraTexturePath::BrokerH264CpuYuv => "VideoYuvPlaneStereo",
        MakepadCameraTexturePath::DirectCpuYuvPlane => "VideoYuvPlane",
        MakepadCameraTexturePath::DirectHardwareBufferExternal
        | MakepadCameraTexturePath::DirectHardwareBufferYuvPlane
        | MakepadCameraTexturePath::BrokerH264HardwareBuffer
        | MakepadCameraTexturePath::BrokerH264SurfaceTexture => "VideoExternal",
    };
    let (import_plan, import_path) = (
        texture_path.import_plan(),
        texture_path.texture_import_path(),
    );
    format!(
        "phase=start status=started importPlan={} brokerH264Enabled={} leftSourceIndex={} rightSourceIndex={} leftSourceClass={} rightSourceClass={} leftWidth={} leftHeight={} rightWidth={} rightHeight={} leftFrameRate={} rightFrameRate={} pixelFormat={} leftStreamPort={} rightStreamPort={} importPath={} textureMode={} textureFormat={} depthClip=false environmentDepthClip=false delayedAfterAcquisitionSeconds={:.0}",
        import_plan,
        broker_h264_enabled,
        left_source_index,
        right_source_index,
        left_source_class,
        right_source_class,
        left_width,
        left_height,
        right_width,
        right_height,
        left_frame_rate,
        right_frame_rate,
        pixel_format,
        left_stream_port,
        right_stream_port,
        import_path,
        texture_path.stable_id(),
        texture_format,
        delayed_after_acquisition_seconds,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn camera_status_marker_keeps_source_metadata_shape() {
        assert_eq!(
            makepad_camera_status_marker_line(
                "startup",
                "fast-visual",
                "direct-camera",
                "185020114",
                "studio.local"
            ),
            "RUSTY_MAKEPAD_CAMERA_STATUS schema=rusty.gui.makepad.camera_status.v1 phase=startup profile=fast-visual transport=direct-camera renderer=makepad android_packager=cargo-makepad makepad_rev=185020114 studio_host=studio.local"
        );
    }

    #[test]
    fn broker_h264_camera2_skip_marker_keeps_acquisition_shape() {
        assert_eq!(
            makepad_camera2_acquisition_broker_h264_skipped_marker_line(),
            "RUSTY_MAKEPAD_CAMERA2_ACQUISITION schema=rusty.gui.makepad.camera2_acquisition.v1 phase=start status=skipped reason=broker-h264-enabled import=broker-h264"
        );
    }

    #[test]
    fn disabled_camera_streaming_skip_marker_keeps_acquisition_shape() {
        assert_eq!(
            makepad_camera2_acquisition_streaming_disabled_marker_line(),
            "RUSTY_MAKEPAD_CAMERA2_ACQUISITION schema=rusty.gui.makepad.camera2_acquisition.v1 phase=start status=skipped reason=camera-streaming-disabled import=none cameraStreamingEnabled=false"
        );
    }

    #[test]
    fn hardware_buffer_import_marker_line_keeps_prefix_shape() {
        assert_eq!(
            makepad_hardware_buffer_import_marker_line("phase=complete status=ok"),
            "RUSTY_MAKEPAD_HARDWARE_BUFFER_IMPORT schema=rusty.gui.makepad.hardware_buffer_import.v1 phase=complete status=ok"
        );
    }

    #[test]
    fn direct_camera2_content_geometry_uses_stereo_record() {
        let fields =
            direct_camera2_content_geometry_marker_fields(1280, 720, "camera2-platform-unprofiled");

        assert!(fields.contains(
            "projectionGeometryProfile=camera-projection geometry_profile=camera-projection"
        ));
        assert!(fields.contains("leftContentKind=camera-frame rightContentKind=camera-frame"));
        assert!(
            fields.contains("leftContentMappingIntent=target-local-raster rightContentMappingIntent=target-local-raster")
        );
        assert!(
            fields.contains("leftSourceSamplingMode=target-local-raster rightSourceSamplingMode=target-local-raster")
        );
        assert!(fields.contains("targetFootprintSchema=rusty.xr.target_screen_footprint.v1"));
        assert!(fields.contains("leftTargetScreenUvRect=0.171875,0.218750,0.750000,0.656250"));
        assert!(fields.contains("rightTargetScreenUvRect=0.078125,0.218750,0.750000,0.671875"));
    }

    #[test]
    fn broker_camera_projection_keeps_target_local_sampling_orthogonal() {
        let metadata = BrokerH264ProjectionMetadata::parse(
            r#"{
                "source": "broker_app.camera2_h264_stream",
                "cameraId": "50",
                "deliveredWidth": 1280,
                "deliveredHeight": 1280,
                "projectionGeometryProfile": "camera-projection",
                "sourceSamplingMode": "target-local-raster",
                "contentMappingIntent": "target-local-raster",
                "projectionMetadataReady": true,
                "intrinsics": {
                    "fx": 1024.0,
                    "fy": 1024.0,
                    "cx": 640.0,
                    "cy": 640.0
                },
                "extrinsics": {
                    "px": 0.0,
                    "py": 0.0,
                    "pz": 0.0,
                    "qx": 0.0,
                    "qy": 0.0,
                    "qz": 0.0,
                    "qw": 1.0
                }
            }"#,
        )
        .unwrap();

        assert!(metadata.source_sampling_mode.uses_target_local_raster());
        assert!(metadata.requests_camera_projection_mapping());
        assert!(!metadata.requests_explicit_full_frame_content_mapping());

        let decision = broker_projection_plan_decision(&metadata, &metadata).unwrap();
        assert_eq!(decision.kind, BrokerProjectionPlanKind::CameraProjection);
        assert_eq!(decision.projection_geometry_profile, "camera-projection");

        let fields = broker_pair_content_geometry_marker_fields(&metadata, &metadata);
        assert!(fields.contains(
            "leftSourceSamplingMode=target-local-raster rightSourceSamplingMode=target-local-raster"
        ));
    }

    #[test]
    fn missing_broker_content_geometry_uses_fallback_record() {
        assert_eq!(
            missing_broker_content_geometry_marker_fields(),
            "leftContentKind=default-fallback rightContentKind=default-fallback leftContentWidth=0 leftContentHeight=0 rightContentWidth=0 rightContentHeight=0 leftContentAspectRatio=1.000000 rightContentAspectRatio=1.000000 leftDesiredDisplayAspectRatio=1.000000 rightDesiredDisplayAspectRatio=1.000000 leftDesiredProjectionAspectRatio=1.000000 rightDesiredProjectionAspectRatio=1.000000 leftContentCoordinateSpace=normalized-uv rightContentCoordinateSpace=normalized-uv leftContentOrigin=top-left rightContentOrigin=top-left leftContentXAxis=right rightContentXAxis=right leftContentYAxis=down rightContentYAxis=down leftContentMappingIntent=standard-missing-metadata-fallback rightContentMappingIntent=standard-missing-metadata-fallback leftSourceSamplingMode=target-local-raster rightSourceSamplingMode=target-local-raster leftContentGeometryMetadataSource=missing rightContentGeometryMetadataSource=missing leftContentGeometryDefault=true rightContentGeometryDefault=true contentGeometryFallbackReason=broker-h264-content-geometry-metadata-missing"
        );
    }

    #[test]
    fn makepad_content_geometry_source_selects_direct_and_missing_broker_records() {
        let direct =
            makepad_content_geometry_marker_fields(MakepadContentGeometrySource::DirectCamera2 {
                width: 1280,
                height: 720,
                projection_geometry_profile: "full-frame-diagnostic",
            });
        assert!(direct.contains("projectionGeometryProfile=full-frame-diagnostic"));
        assert!(direct.contains("leftContentKind=camera-frame"));
        assert!(direct.contains("contentGeometryFallbackReason=none"));

        let missing =
            makepad_content_geometry_marker_fields(MakepadContentGeometrySource::BrokerH264 {
                left: None,
                right: None,
            });
        assert!(missing.contains("leftContentKind=default-fallback"));
        assert!(missing.contains(
            "contentGeometryFallbackReason=broker-h264-content-geometry-metadata-missing"
        ));
    }

    #[test]
    fn broker_content_geometry_marker_fields_use_parsed_records() {
        let left = BrokerH264ProjectionMetadata::parse(
            r#"{
                "projectionMetadataReady": true,
                "contentKind": "broker synthetic",
                "contentWidth": 640,
                "contentHeight": 480,
                "contentAspectRatio": 1.333333,
                "desiredDisplayAspectRatio": 1.333333,
                "desiredProjectionAspectRatio": 1.333333,
                "contentMappingIntent": "map broker stimulus",
                "contentGeometryMetadataSource": "stream header",
                "contentGeometryDefault": false
            }"#,
        )
        .unwrap();
        let right = BrokerH264ProjectionMetadata::parse(
            r#"{
                "projectionMetadataReady": true,
                "contentKind": "broker camera",
                "contentWidth": 800,
                "contentHeight": 600,
                "contentMappingIntent": "map broker camera",
                "contentGeometryMetadataSource": "stream header",
                "contentGeometryDefault": false
            }"#,
        )
        .unwrap();

        let fields = broker_pair_content_geometry_marker_fields(&left, &right);

        assert!(fields.contains("leftContentKind=broker_synthetic"));
        assert!(fields.contains("rightContentKind=broker_camera"));
        assert!(fields.contains("leftContentWidth=640 leftContentHeight=480"));
        assert!(fields.contains("rightContentWidth=800 rightContentHeight=600"));
        assert!(fields.contains("leftContentMappingIntent=map_broker_stimulus"));
        assert!(fields.contains("rightContentMappingIntent=map_broker_camera"));
        assert!(fields.contains("contentGeometryFallbackReason=none"));
    }

    #[test]
    fn broker_projection_plan_decision_is_metadata_driven() {
        let camera = BrokerH264ProjectionMetadata::parse(
            r#"{
                "projectionMetadataReady": true,
                "projectionGeometryProfile": "full-frame-diagnostic",
                "sourceSamplingMode": "screen-to-camera-homography",
                "contentMappingIntent": "map-camera-frame-to-full-frame-projection-area",
                "intrinsics": {"fx": 1024.0, "fy": 1024.0, "cx": 640.0, "cy": 640.0},
                "extrinsics": {"px": 0.0, "py": 0.0, "pz": 0.0, "qx": 0.0, "qy": 0.0, "qz": 0.0, "qw": 1.0}
            }"#,
        )
        .unwrap();
        let camera_decision = broker_projection_plan_decision(&camera, &camera).unwrap();
        assert_eq!(
            camera_decision.kind,
            BrokerProjectionPlanKind::CameraProjection
        );
        assert_eq!(
            camera_decision.source_binding_mode,
            "broker-h264-stream-header-full-frame-diagnostic"
        );
        assert_eq!(
            camera_decision.projection_geometry_profile,
            "full-frame-diagnostic"
        );

        let synthetic = BrokerH264ProjectionMetadata::parse(
            r#"{
                "projectionMetadataReady": true,
                "projectionGeometryProfile": "full-frame-diagnostic",
                "contentMappingIntent": "map-full-frame-stimulus-to-projection-surface"
            }"#,
        )
        .unwrap();
        let synthetic_decision = broker_projection_plan_decision(&synthetic, &synthetic).unwrap();
        assert_eq!(
            synthetic_decision.kind,
            BrokerProjectionPlanKind::FullFrameContent
        );

        let camera_matched = BrokerH264ProjectionMetadata::parse(
            r#"{
                "projectionMetadataReady": true,
                "projectionGeometryProfile": "camera-matched"
            }"#,
        )
        .unwrap();
        let fallback_decision =
            broker_projection_plan_decision(&camera_matched, &camera_matched).unwrap();
        assert_eq!(
            fallback_decision.kind,
            BrokerProjectionPlanKind::CameraProjection
        );
        assert!(fallback_decision.camera_matched_live_fallback_allowed);

        let head_anchored = BrokerH264ProjectionMetadata::parse(
            r#"{
                "projectionMetadataReady": true,
                "projectionGeometryProfile": "head-anchored-virtual-camera"
            }"#,
        )
        .unwrap();
        let head_anchored_decision =
            broker_projection_plan_decision(&head_anchored, &head_anchored).unwrap();
        assert_eq!(
            head_anchored_decision.kind,
            BrokerProjectionPlanKind::HeadAnchoredProjectionArea
        );
    }

    #[test]
    fn stream_header_metadata_marker_uses_content_geometry_record() {
        let metadata = BrokerH264ProjectionMetadata::parse(
            r#"{
                "projectionMetadataReady": true,
                "cameraId": "left camera",
                "source": "broker_app.synthetic_h264_stream",
                "poseSource": "stream header",
                "poseCoordinateConvention": "camera2 lens",
                "projectionGeometryProfile": "full-frame-diagnostic",
                "syntheticPattern": "uv grid",
                "contentKind": "broker synthetic",
                "contentWidth": 640,
                "contentHeight": 480,
                "contentMappingIntent": "map full frame content",
                "contentGeometryMetadataSource": "stream header",
                "contentGeometryDefault": false,
                "sourceValidUvRect": [0.1, 0.2, 0.8, 0.6]
            }"#,
        )
        .unwrap();

        let fields = stream_header_metadata_marker_fields(
            "left",
            &metadata,
            MakepadCameraTexturePath::BrokerH264CpuYuv,
        );

        assert!(fields.starts_with("phase=stream-header-metadata status=ok side=left"));
        assert!(fields.contains("cameraId=left_camera"));
        assert!(fields.contains("source=broker_app.synthetic_h264_stream"));
        assert!(fields.contains("contentKind=broker_synthetic"));
        assert!(fields.contains("contentWidth=640 contentHeight=480"));
        assert!(fields.contains("contentMappingIntent=map_full_frame_content"));
        assert!(fields.contains("sourceValidUvRect=0.100000,0.200000,0.800000,0.600000"));
        assert!(fields.ends_with(
            "textureMode=broker-h264-mediacodec-cpu-yuv importPlan=broker-h264-stereo-mediacodec-yuv-texture"
        ));
    }

    #[test]
    fn hardware_buffer_import_enumerated_markers_keep_source_metadata_shape() {
        let fields = hardware_buffer_import_enumerated_marker_fields(
            2,
            4,
            "camera2-direct",
            0,
            1,
            "camera 0",
            "camera 1",
            "back",
            "back",
            1280,
            720,
            1280,
            720,
            "30.00",
            "30.00",
            "YUV420",
        );

        assert!(fields.starts_with(
            "phase=enumerated status=ok makepadSourceCount=2 makepadFormatCount=4 selected=true"
        ));
        assert!(fields.contains("sourceBindingMode=camera2-direct"));
        assert!(fields.contains("leftCameraId=camera_0 rightCameraId=camera_1"));
        assert!(fields.contains("leftFrameRate=30.00 rightFrameRate=30.00 pixelFormat=YUV420"));

        let error = makepad_hardware_buffer_import_enumerated_error_marker_fields(0, 0);
        assert_eq!(
            error,
            "phase=enumerated status=error makepadSourceCount=0 makepadFormatCount=0 selected=false errorKind=no_yuv420_makepad_camera_stereo_pair"
        );
    }

    #[test]
    fn hardware_buffer_import_lifecycle_markers_keep_source_metadata_shape() {
        assert_eq!(
            makepad_hardware_buffer_import_texture_updated_marker_fields(
                "left",
                true,
                false,
                2.0,
                MakepadCameraTexturePath::DirectCpuYuvPlane,
                &VideoTextureUpdateMetadata::default(),
                "solid-red",
                "raw",
            ),
            "phase=texture-updated status=ok side=left yuvEnabled=true yuvBiplanar=false rotationSteps=2 projectionBorderPolicy=solid-red processingLayer=raw importPlan=paired-camera-cpu-yuv-fallback cameraTexturePath=direct-camera-cpu-yuv-plane makepadVulkanImport=false textureImportPath=makepad-camera-cpu-yuv-plane cpuUploadPath=makepad-camera-cpu-yuv-plane visualColorStatus=accepted-cpu-yuv-reference eventResourcePath=unspecified descriptorShape=unspecified"
        );
        assert_eq!(
            makepad_hardware_buffer_import_complete_error_marker_fields(
                "right",
                "decoder failed",
            ),
            "phase=complete status=error side=right errorKind=makepad_video_import_failed message=decoder_failed"
        );
        assert_eq!(
            makepad_hardware_buffer_import_timer_fired_marker_fields(
                "signal-fallback",
                true,
                false,
                false,
            ),
            "phase=timer status=fired source=signal-fallback hasPair=true importStarted=false importFinished=false importPlan=paired-makepad-video-hardware-buffer"
        );
        assert_eq!(
            makepad_hardware_buffer_import_timer_armed_marker_fields("stereo pair retry", 0.5),
            "phase=timer status=armed reason=stereo_pair_retry delaySeconds=0.5 signalFallback=true importPlan=paired-makepad-video-hardware-buffer"
        );
        assert_eq!(
            makepad_hardware_buffer_import_start_error_marker_fields(),
            "phase=start status=error errorKind=no_makepad_camera_stereo_pair"
        );
        assert_eq!(
            makepad_hardware_buffer_import_start_waiting_marker_fields(3),
            "phase=start status=waiting waitCount=3 reason=no_makepad_camera_stereo_pair_yet"
        );
    }

    #[test]
    fn broker_h264_import_markers_keep_source_metadata_shape() {
        assert_eq!(
            makepad_hardware_buffer_import_texture_handle_ready_marker_fields(
                "left",
                42,
                "127.0.0.1",
                8765,
                8879,
                "broker camera",
                "uv grid",
                true,
            ),
            "phase=texture-handle-ready status=ok side=left textureHandle=42 textureMode=external-oes brokerHost=127.0.0.1 brokerPort=8765 streamPort=8879 sourceMode=broker_camera syntheticPattern=uv_grid liveStream=true importPlan=broker-h264-stereo-surface-texture"
        );
        assert_eq!(
            makepad_hardware_buffer_import_broker_h264_prepare_request_marker_fields(
                "right",
                "127.0.0.1",
                8765,
                8880,
                "synthetic h264",
                "hardware buffer",
                "diagnostic grid",
                false,
                MakepadCameraTexturePath::BrokerH264HardwareBuffer,
            ),
            "phase=broker-h264-prepare-request status=sent side=right textureHandle=0 textureMode=broker-h264-mediacodec-hardware-buffer brokerHost=127.0.0.1 brokerPort=8765 streamPort=8880 sourceMode=synthetic_h264 decodeOutputMode=hardware_buffer syntheticPattern=diagnostic_grid liveStream=false importPlan=broker-h264-stereo-mediacodec-hardware-buffer"
        );
        assert_eq!(
            makepad_hardware_buffer_import_broker_h264_startup_marker_fields(
                "127.0.0.1",
                8765,
                8879,
                8880,
                "broker camera",
                "cpu-yuv",
                "uv grid",
                1280,
                720,
                true,
                MakepadCameraTexturePath::BrokerH264CpuYuv,
            ),
            "phase=startup status=broker-h264-enabled brokerHost=127.0.0.1 brokerPort=8765 leftStreamPort=8879 rightStreamPort=8880 sourceMode=broker_camera decodeOutputMode=cpu-yuv syntheticPattern=uv_grid preferredWidth=1280 preferredHeight=720 liveStream=true textureMode=broker-h264-mediacodec-cpu-yuv importPlan=broker-h264-stereo-mediacodec-yuv-texture"
        );
        assert_eq!(
            makepad_stream_header_metadata_ignored_marker_fields(
                99,
                MakepadCameraTexturePath::BrokerH264HardwareBuffer,
            ),
            "phase=stream-header-metadata status=ignored side=unknown videoId=99 reason=unexpected_video_id textureMode=broker-h264-mediacodec-hardware-buffer importPlan=broker-h264-stereo-mediacodec-hardware-buffer"
        );
        assert_eq!(
            makepad_stream_header_metadata_error_marker_fields(
                "left",
                123,
                "bad json",
                MakepadCameraTexturePath::BrokerH264HardwareBuffer,
            ),
            "phase=stream-header-metadata status=error side=left metadataBytes=123 error=bad_json textureMode=broker-h264-mediacodec-hardware-buffer importPlan=broker-h264-stereo-mediacodec-hardware-buffer"
        );
        assert_eq!(
            makepad_hardware_buffer_import_yuv_textures_ready_broker_marker_fields("left"),
            "phase=yuv-textures-ready status=ok side=left textureMode=cpu-yuv-decoded-broker-h264 importPlan=broker-h264-stereo-mediacodec-yuv-texture"
        );
        assert_eq!(
            makepad_hardware_buffer_import_yuv_textures_ready_single_stream_marker_fields(
                "right",
                MakepadCameraTexturePath::DirectCpuYuvPlane,
            ),
            "phase=yuv-textures-ready status=ok side=right textureMode=makepad-yuv-slot-allocation requestedTexturePath=direct-camera-cpu-yuv-plane importPlan=paired-camera-cpu-yuv-fallback depthClip=false environmentDepthClip=false"
        );
        assert_eq!(
            makepad_hardware_buffer_import_prepared_marker_fields(
                "left",
                1280,
                720,
                MakepadCameraTexturePath::DirectCpuYuvPlane,
            ),
            "phase=prepared status=ok side=left width=1280 height=720 importPath=makepad-camera-cpu-yuv-plane textureMode=direct-camera-cpu-yuv-plane importPlan=paired-camera-cpu-yuv-fallback cameraTexturePath=direct-camera-cpu-yuv-plane makepadVulkanImport=false textureImportPath=makepad-camera-cpu-yuv-plane cpuUploadPath=makepad-camera-cpu-yuv-plane visualColorStatus=accepted-cpu-yuv-reference"
        );
        assert_eq!(
            makepad_hardware_buffer_import_texture_updated_marker_fields(
                "left",
                true,
                false,
                0.0,
                MakepadCameraTexturePath::DirectCpuYuvPlane,
                &VideoTextureUpdateMetadata::default(),
                "solid-red",
                "raw",
            ),
            "phase=texture-updated status=ok side=left yuvEnabled=true yuvBiplanar=false rotationSteps=0 projectionBorderPolicy=solid-red processingLayer=raw importPlan=paired-camera-cpu-yuv-fallback cameraTexturePath=direct-camera-cpu-yuv-plane makepadVulkanImport=false textureImportPath=makepad-camera-cpu-yuv-plane cpuUploadPath=makepad-camera-cpu-yuv-plane visualColorStatus=accepted-cpu-yuv-reference eventResourcePath=unspecified descriptorShape=unspecified"
        );
        assert_eq!(
            hardware_buffer_import_start_marker_fields(
                true,
                0,
                1,
                "broker-h264",
                "broker-h264",
                1280,
                720,
                1280,
                720,
                "30.00",
                "30.00",
                "YUV420",
                "8879",
                "8880",
                0.25,
                MakepadCameraTexturePath::BrokerH264CpuYuv,
            ),
            "phase=start status=started importPlan=broker-h264-stereo-mediacodec-yuv-texture brokerH264Enabled=true leftSourceIndex=0 rightSourceIndex=1 leftSourceClass=broker-h264 rightSourceClass=broker-h264 leftWidth=1280 leftHeight=720 rightWidth=1280 rightHeight=720 leftFrameRate=30.00 rightFrameRate=30.00 pixelFormat=YUV420 leftStreamPort=8879 rightStreamPort=8880 importPath=broker-h264-mediacodec-cpu-yuv textureMode=broker-h264-mediacodec-cpu-yuv textureFormat=VideoYuvPlaneStereo depthClip=false environmentDepthClip=false delayedAfterAcquisitionSeconds=0"
        );
        assert_eq!(
            hardware_buffer_import_start_marker_fields(
                true,
                0,
                1,
                "broker-h264",
                "broker-h264",
                1280,
                720,
                1280,
                720,
                "50.00",
                "50.00",
                "PRIVATE",
                "8879",
                "8880",
                0.25,
                MakepadCameraTexturePath::BrokerH264HardwareBuffer,
            ),
            "phase=start status=started importPlan=broker-h264-stereo-mediacodec-hardware-buffer brokerH264Enabled=true leftSourceIndex=0 rightSourceIndex=1 leftSourceClass=broker-h264 rightSourceClass=broker-h264 leftWidth=1280 leftHeight=720 rightWidth=1280 rightHeight=720 leftFrameRate=50.00 rightFrameRate=50.00 pixelFormat=PRIVATE leftStreamPort=8879 rightStreamPort=8880 importPath=broker-h264-mediacodec-hardware-buffer-vulkan-import textureMode=broker-h264-mediacodec-hardware-buffer textureFormat=VideoExternal depthClip=false environmentDepthClip=false delayedAfterAcquisitionSeconds=0"
        );
        assert_eq!(
            makepad_hardware_buffer_import_raw_video_event_marker_line(
                "texture-updated",
                "left",
                100,
                100,
                101,
            ),
            "RUSTY_MAKEPAD_HARDWARE_BUFFER_IMPORT schema=rusty.gui.makepad.hardware_buffer_import.v1 phase=raw-video-event status=seen event=texture-updated side=left videoId=100 leftVideoId=100 rightVideoId=101 depthClip=false environmentDepthClip=false importPlan=makepad-video-texture-event"
        );
    }
}
