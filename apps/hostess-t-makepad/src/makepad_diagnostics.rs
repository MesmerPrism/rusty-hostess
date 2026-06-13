use crate::hostess_camera_model::{Rect2, Vec2};
use crate::projection_geometry::makepad_projection_target_marker_fields;
use crate::runtime_settings::{
    RAW_VIDEO_EVENT_MARKER_LIMIT, TEXTURE_UPDATE_MARKER_LIMIT, TEXTURE_UPDATE_MARKER_PERIOD,
};
use crate::source_metadata::makepad_hardware_buffer_import_raw_video_event_marker_line;
use crate::stereo_frame::StereoEye;
use makepad_widgets::makepad_platform::{
    event::video_playback::VideoTextureUpdateMetadata, LiveId,
};
use makepad_widgets::*;
use std::{
    sync::atomic::{AtomicUsize, Ordering},
    time::{SystemTime, UNIX_EPOCH},
};

static VIDEO_EVENT_RAW_MARKERS_EMITTED: AtomicUsize = AtomicUsize::new(0);

pub(crate) fn emit_raw_video_event_marker(event_name: &str, video_id: LiveId) {
    let marker_index = VIDEO_EVENT_RAW_MARKERS_EMITTED.fetch_add(1, Ordering::AcqRel);
    if marker_index >= RAW_VIDEO_EVENT_MARKER_LIMIT {
        return;
    }
    let side = StereoEye::from_video_id(video_id)
        .map(StereoEye::label)
        .unwrap_or("unknown");
    emit_marker_line(&makepad_hardware_buffer_import_raw_video_event_marker_line(
        event_name,
        side,
        video_id.0,
        StereoEye::Left.video_id().0,
        StereoEye::Right.video_id().0,
    ));
}

pub(crate) fn should_emit_texture_update_marker(marker_index: usize) -> bool {
    marker_index < TEXTURE_UPDATE_MARKER_LIMIT || marker_index % TEXTURE_UPDATE_MARKER_PERIOD == 0
}

pub(crate) fn marker_value(value: &str) -> String {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return "empty".to_string();
    }
    trimmed
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.' | ':' | '/') {
                ch
            } else {
                '_'
            }
        })
        .collect()
}

pub(crate) fn optional_u64_token(value: Option<u64>) -> String {
    value
        .map(|value| value.to_string())
        .unwrap_or_else(|| "missing".to_string())
}

pub(crate) fn optional_i64_token(value: Option<i64>) -> String {
    value
        .map(|value| value.to_string())
        .unwrap_or_else(|| "missing".to_string())
}

pub(crate) fn vec3_marker_token(value: [f32; 3]) -> String {
    format!("{:.6},{:.6},{:.6}", value[0], value[1], value[2])
}

pub(crate) fn vec4_marker_token(value: [f32; 4]) -> String {
    format!(
        "{:.6},{:.6},{:.6},{:.6}",
        value[0], value[1], value[2], value[3]
    )
}

#[derive(Clone)]
pub(crate) struct MakepadCameraYuvTextures {
    pub(crate) y: Texture,
    pub(crate) u: Texture,
    pub(crate) v: Texture,
}

impl MakepadCameraYuvTextures {
    pub(crate) fn new(y: Texture, u: Texture, v: Texture) -> Self {
        Self { y, u, v }
    }
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct MakepadTargetFootprintPush {
    pub(crate) from_metadata: f32,
    pub(crate) left_offset_x_uv: f32,
    pub(crate) left_offset_y_uv: f32,
    pub(crate) right_offset_x_uv: f32,
    pub(crate) right_offset_y_uv: f32,
    pub(crate) left_radius_x_uv: f32,
    pub(crate) left_radius_y_uv: f32,
    pub(crate) right_radius_x_uv: f32,
    pub(crate) right_radius_y_uv: f32,
}

impl MakepadTargetFootprintPush {
    pub(crate) fn from_pair(
        pair: crate::source_metadata::MakepadTargetScreenFootprintPair,
    ) -> Self {
        let (left_offset, left_radius) = target_footprint_rect_push(pair.left_rect);
        let (right_offset, right_radius) = target_footprint_rect_push(pair.right_rect);
        Self {
            from_metadata: if pair.from_metadata { 1.0 } else { 0.0 },
            left_offset_x_uv: left_offset.x,
            left_offset_y_uv: left_offset.y,
            right_offset_x_uv: right_offset.x,
            right_offset_y_uv: right_offset.y,
            left_radius_x_uv: left_radius.x,
            left_radius_y_uv: left_radius.y,
            right_radius_x_uv: right_radius.x,
            right_radius_y_uv: right_radius.y,
        }
    }
}

fn target_footprint_rect_push(rect: Rect2) -> (Vec2, Vec2) {
    let center = Vec2::new(
        rect.origin.x + rect.size.x * 0.5,
        rect.origin.y + rect.size.y * 0.5,
    );
    let offset = Vec2::new(
        (center.x - 0.5).clamp(-0.5, 0.5),
        (center.y - 0.5).clamp(-0.5, 0.5),
    );
    let radius = Vec2::new(
        (rect.size.x * 0.5).clamp(0.001, 0.5),
        (rect.size.y * 0.5).clamp(0.001, 0.5),
    );
    (offset, radius)
}

fn marker_line_with_runtime_projection_target_fields(line: &str) -> std::borrow::Cow<'_, str> {
    const LEGACY_TARGET_FIELDS: &str =
        "panelTargetPreviewFovYDegrees=60 panelTargetRawOverscan=1.06";
    if line.contains(LEGACY_TARGET_FIELDS) {
        std::borrow::Cow::Owned(line.replace(
            LEGACY_TARGET_FIELDS,
            &makepad_projection_target_marker_fields(),
        ))
    } else {
        std::borrow::Cow::Borrowed(line)
    }
}

#[cfg(target_os = "android")]
pub(crate) fn emit_marker_line(line: &str) {
    use std::ffi::CString;
    use std::os::raw::{c_char, c_int};

    const ANDROID_LOG_INFO: c_int = 4;

    #[link(name = "log")]
    unsafe extern "C" {
        fn __android_log_write(prio: c_int, tag: *const c_char, text: *const c_char) -> c_int;
    }

    let line = marker_line_with_runtime_projection_target_fields(line);
    let tag = CString::new("HostessMakepad");
    let msg = CString::new(line.as_ref());
    if let (Ok(tag), Ok(msg)) = (tag, msg) {
        unsafe {
            __android_log_write(ANDROID_LOG_INFO, tag.as_ptr(), msg.as_ptr());
        }
    }
}

#[cfg(not(target_os = "android"))]
pub(crate) fn emit_marker_line(line: &str) {
    let line = marker_line_with_runtime_projection_target_fields(line);
    log!("{}", line.as_ref());
}

pub(crate) fn rate_hz(count: u64, seconds: f64) -> f64 {
    if seconds <= 0.0 {
        0.0
    } else {
        count as f64 / seconds
    }
}

pub(crate) fn diagnostic_now_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos().min(u64::MAX as u128) as u64)
        .unwrap_or(0)
}

pub(crate) fn camera_frame_age_ms(
    metadata: Option<&VideoTextureUpdateMetadata>,
    now_ns: u64,
) -> Option<f64> {
    metadata
        .and_then(|metadata| metadata.acquire_time_ns.or(metadata.import_time_ns))
        .and_then(|timestamp_ns| now_ns.checked_sub(timestamp_ns))
        .map(|age_ns| age_ns as f64 / 1_000_000.0)
}

pub(crate) fn camera_import_lag_ms(metadata: Option<&VideoTextureUpdateMetadata>) -> Option<f64> {
    metadata
        .and_then(|metadata| metadata.acquire_time_ns.zip(metadata.import_time_ns))
        .and_then(|(acquire_time_ns, import_time_ns)| import_time_ns.checked_sub(acquire_time_ns))
        .map(|lag_ns| lag_ns as f64 / 1_000_000.0)
}

pub(crate) fn optional_max_f64(left: Option<f64>, right: Option<f64>) -> Option<f64> {
    match (left, right) {
        (Some(left), Some(right)) => Some(left.max(right)),
        (Some(value), None) | (None, Some(value)) => Some(value),
        (None, None) => None,
    }
}

pub(crate) fn mesh_replay_segment_vec4(segment: [f32; 4]) -> Vec4f {
    Vec4f {
        x: segment[0],
        y: segment[1],
        z: segment[2],
        w: segment[3],
    }
}

pub(crate) fn camera_shell_sdf_adf_mode_token(mode: f32) -> &'static str {
    if mode >= 2.5 {
        "combined"
    } else if mode >= 1.5 {
        "adf"
    } else if mode >= 0.5 {
        "sdf"
    } else {
        "off"
    }
}

pub(crate) fn marker_f32_token(value: Option<f32>) -> String {
    match value {
        Some(value) if value.is_finite() => format!("{value:.3}"),
        _ => "none".to_string(),
    }
}
