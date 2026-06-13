use crate::camera_texture_path::MakepadCameraTexturePath;
use crate::hostess_camera_model::SourceSamplingMode;
use crate::runtime_settings::*;
use crate::source_metadata::{
    makepad_runtime_camera_source_sampling_mode, makepad_runtime_target_screen_footprint_pair,
    normalize_direct_camera_projection_geometry_profile, target_screen_uv_rect_token,
};
use crate::stereo_frame::StereoEye;
use makepad_widgets::makepad_platform::event::video_playback::ExternalH264VideoSource;
use rusty_quest_makepad_camera_shell::RemoteCameraEffectiveConfig;

pub(crate) fn broker_h264_enabled(remote_receiver: Option<&RemoteCameraEffectiveConfig>) -> bool {
    if remote_receiver.is_some() {
        return true;
    }
    let transport_requests_broker = std::env::var("RUSTY_MAKEPAD_TRANSPORT_PROFILE")
        .map(|value| value.to_ascii_lowercase().contains("broker-h264"))
        .unwrap_or(false);
    hotload_bool(
        KEY_MAKEPAD_BROKER_H264_ENABLED,
        DEFAULT_BROKER_H264_ENABLED || transport_requests_broker,
    )
}

pub(crate) fn broker_h264_decode_output_mode() -> String {
    hotload_text(
        KEY_MAKEPAD_BROKER_H264_DECODE_OUTPUT_MODE,
        DEFAULT_BROKER_H264_DECODE_OUTPUT_MODE,
    )
}

pub(crate) fn broker_h264_requested_texture_path() -> MakepadCameraTexturePath {
    match broker_h264_decode_output_mode()
        .trim()
        .to_ascii_lowercase()
        .replace('_', "-")
        .as_str()
    {
        "hardware-buffer" | "hwb" | "image-reader" | "imagereader" => {
            MakepadCameraTexturePath::BrokerH264HardwareBuffer
        }
        "surface-texture" | "surfacetexture" | "external-oes" | "oes" | "surface" => {
            MakepadCameraTexturePath::BrokerH264SurfaceTexture
        }
        _ => MakepadCameraTexturePath::BrokerH264CpuYuv,
    }
}

pub(crate) fn broker_h264_source_sampling_mode() -> SourceSamplingMode {
    let default_mode = makepad_runtime_camera_source_sampling_mode();
    SourceSamplingMode::parse(&hotload_text(
        KEY_MAKEPAD_BROKER_H264_SOURCE_SAMPLING_MODE,
        default_mode.stable_id(),
    ))
    .unwrap_or(default_mode)
}

pub(crate) fn direct_camera_projection_geometry_profile() -> String {
    normalize_direct_camera_projection_geometry_profile(&hotload_text_any(
        &[
            KEY_CAMERA_PROJECTION_GEOMETRY_PROFILE,
            KEY_MAKEPAD_CAMERA_PROJECTION_GEOMETRY_PROFILE,
        ],
        DEFAULT_CAMERA_PROJECTION_GEOMETRY_PROFILE,
    ))
}

pub(crate) fn broker_h264_stream_port(
    eye: StereoEye,
    remote_receiver: Option<&RemoteCameraEffectiveConfig>,
) -> u16 {
    let default_left = if remote_receiver.is_some() {
        DEFAULT_REMOTE_CAMERA_RECEIVER_LEFT_STREAM_PORT
    } else {
        DEFAULT_BROKER_H264_STREAM_PORT
    };
    let default_right = if remote_receiver.is_some() {
        DEFAULT_REMOTE_CAMERA_RECEIVER_RIGHT_STREAM_PORT
    } else {
        DEFAULT_BROKER_H264_RIGHT_STREAM_PORT
    };
    match eye {
        StereoEye::Left => hotload_u16(
            KEY_MAKEPAD_BROKER_H264_STREAM_PORT,
            default_left,
            1,
            u16::MAX,
        ),
        StereoEye::Right => hotload_u16(
            KEY_MAKEPAD_BROKER_H264_RIGHT_STREAM_PORT,
            default_right,
            1,
            u16::MAX,
        ),
    }
}

pub(crate) fn broker_h264_target_screen_uv_rect_for_eye(eye: StereoEye) -> String {
    let target = makepad_runtime_target_screen_footprint_pair();
    let fallback = match eye {
        StereoEye::Left => target_screen_uv_rect_token(target.left_rect),
        StereoEye::Right => target_screen_uv_rect_token(target.right_rect),
    };
    let shared = hotload_text(KEY_MAKEPAD_BROKER_H264_TARGET_SCREEN_UV_RECT, "");
    if !shared.trim().is_empty() {
        return shared;
    }
    match eye {
        StereoEye::Left => hotload_text(
            KEY_MAKEPAD_BROKER_H264_LEFT_TARGET_SCREEN_UV_RECT,
            &fallback,
        ),
        StereoEye::Right => hotload_text(
            KEY_MAKEPAD_BROKER_H264_RIGHT_TARGET_SCREEN_UV_RECT,
            &fallback,
        ),
    }
}

pub(crate) fn broker_h264_source_for_eye(
    eye: StereoEye,
    remote_receiver: Option<&RemoteCameraEffectiveConfig>,
) -> ExternalH264VideoSource {
    let synthetic_projection_profile = hotload_text(
        KEY_MAKEPAD_BROKER_H264_SYNTHETIC_PROJECTION_PROFILE,
        DEFAULT_BROKER_H264_SYNTHETIC_PROJECTION_PROFILE,
    );
    let projection_geometry_profile = hotload_text(
        KEY_MAKEPAD_BROKER_H264_PROJECTION_GEOMETRY_PROFILE,
        &synthetic_projection_profile,
    );
    let source_sampling_mode = broker_h264_source_sampling_mode();
    let decode_output_mode = broker_h264_decode_output_mode();
    ExternalH264VideoSource {
        broker_host: hotload_text(KEY_MAKEPAD_BROKER_H264_HOST, DEFAULT_BROKER_H264_HOST),
        broker_port: hotload_u16(
            KEY_MAKEPAD_BROKER_H264_BROKER_PORT,
            DEFAULT_BROKER_H264_BROKER_PORT,
            1,
            u16::MAX,
        ),
        stream_port: broker_h264_stream_port(eye, remote_receiver),
        source_mode: hotload_text(
            KEY_MAKEPAD_BROKER_H264_SOURCE_MODE,
            if remote_receiver.is_some() {
                DEFAULT_REMOTE_CAMERA_RECEIVER_SOURCE_MODE
            } else {
                DEFAULT_BROKER_H264_SOURCE_MODE
            },
        ),
        decode_output_mode,
        synthetic_pattern: hotload_text(
            KEY_MAKEPAD_BROKER_H264_SYNTHETIC_PATTERN,
            DEFAULT_BROKER_H264_SYNTHETIC_PATTERN,
        ),
        synthetic_projection_profile: projection_geometry_profile,
        source_sampling_mode: source_sampling_mode.stable_id().to_string(),
        target_screen_uv_rect: broker_h264_target_screen_uv_rect_for_eye(eye),
        camera_id: match eye {
            StereoEye::Left => hotload_text(
                KEY_MAKEPAD_BROKER_H264_LEFT_CAMERA_ID,
                DEFAULT_BROKER_H264_LEFT_CAMERA_ID,
            ),
            StereoEye::Right => hotload_text(
                KEY_MAKEPAD_BROKER_H264_RIGHT_CAMERA_ID,
                DEFAULT_BROKER_H264_RIGHT_CAMERA_ID,
            ),
        },
        stereo_pair_id: hotload_text(
            KEY_MAKEPAD_BROKER_H264_STEREO_PAIR_ID,
            remote_receiver
                .map(|config| config.session_id.as_str())
                .unwrap_or(DEFAULT_BROKER_H264_STEREO_PAIR_ID),
        ),
        stereo_pair_role: match eye {
            StereoEye::Left => "left".to_string(),
            StereoEye::Right => "right".to_string(),
        },
        stereo_pair_max_delta_ns: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_STEREO_PAIR_MAX_DELTA_NS,
            DEFAULT_BROKER_H264_STEREO_PAIR_MAX_DELTA_NS,
            0,
            250_000_000,
        ),
        preferred_width: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_WIDTH,
            DEFAULT_BROKER_H264_WIDTH,
            16,
            4096,
        ),
        preferred_height: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_HEIGHT,
            DEFAULT_BROKER_H264_HEIGHT,
            16,
            4096,
        ),
        capture_ms: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_CAPTURE_MS,
            if remote_receiver.is_some() {
                0
            } else {
                DEFAULT_BROKER_H264_CAPTURE_MS
            },
            0,
            120_000,
        ),
        max_packets: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_MAX_PACKETS,
            if remote_receiver.is_some() {
                0
            } else {
                DEFAULT_BROKER_H264_MAX_PACKETS
            },
            0,
            2400,
        ),
        bitrate_bps: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_BITRATE_BPS,
            DEFAULT_BROKER_H264_BITRATE_BPS,
            100_000,
            20_000_000,
        ),
        frame_rate_hz: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_FRAME_RATE_HZ,
            DEFAULT_BROKER_H264_FRAME_RATE_HZ,
            1,
            120,
        ),
        command_timeout_ms: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_COMMAND_TIMEOUT_MS,
            DEFAULT_BROKER_H264_COMMAND_TIMEOUT_MS,
            500,
            60_000,
        ),
        stream_timeout_ms: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_STREAM_TIMEOUT_MS,
            DEFAULT_BROKER_H264_STREAM_TIMEOUT_MS,
            500,
            120_000,
        ),
        decode_timeout_ms: hotload_u32(
            KEY_MAKEPAD_BROKER_H264_DECODE_TIMEOUT_MS,
            DEFAULT_BROKER_H264_DECODE_TIMEOUT_MS,
            500,
            60_000,
        ),
        live_stream: hotload_bool(
            KEY_MAKEPAD_BROKER_H264_LIVE_STREAM,
            DEFAULT_BROKER_H264_LIVE_STREAM || remote_receiver.is_some(),
        ),
    }
}

pub(crate) fn broker_h264_source(
    remote_receiver: Option<&RemoteCameraEffectiveConfig>,
) -> ExternalH264VideoSource {
    broker_h264_source_for_eye(StereoEye::Left, remote_receiver)
}
