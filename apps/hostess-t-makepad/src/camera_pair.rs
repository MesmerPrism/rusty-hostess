#[cfg(target_os = "android")]
use crate::android_camera_probe;
use crate::projection_geometry::MakepadOpenXrProjectionContract;
use crate::runtime_settings::{
    marker_token, DEFAULT_CAMERA_PROJECTION_GEOMETRY_PROFILE,
    DEFAULT_MAKEPAD_DISPLAY_SOURCE_EYE_MAPPING, IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
};
use crate::rusty_xr_camera_model::Rect2;
use crate::source_metadata::{
    makepad_runtime_target_screen_footprint_pair,
    normalize_direct_camera_projection_geometry_profile, MakepadTargetScreenFootprintPair,
};
#[cfg(target_os = "android")]
use crate::source_metadata::{BrokerH264ProjectionMetadata, BrokerProjectionPlanDecision};
use makepad_widgets::makepad_platform::{
    event::video_playback::ExternalH264VideoSource,
    video::{VideoFormat, VideoFormatId, VideoInputId, VideoInputsEvent, VideoPixelFormat},
};

pub(crate) fn collect_makepad_camera_choices(
    inputs: &VideoInputsEvent,
) -> Vec<MakepadCameraChoice> {
    inputs
        .descs
        .iter()
        .enumerate()
        .flat_map(|(source_index, desc)| {
            desc.formats
                .iter()
                .filter(|format| format.pixel_format == VideoPixelFormat::YUV420)
                .map(move |format| {
                    MakepadCameraChoice::new(
                        source_index,
                        desc.input_id,
                        *format,
                        camera_source_class(&desc.name),
                        camera_id_from_makepad_desc_name(&desc.name),
                    )
                })
        })
        .collect()
}

#[derive(Clone)]
pub(crate) struct MakepadCameraChoice {
    pub(crate) source_index: usize,
    pub(crate) input_id: VideoInputId,
    pub(crate) format_id: VideoFormatId,
    pub(crate) camera_id: Option<String>,
    pub(crate) source_class: &'static str,
    pub(crate) width: usize,
    pub(crate) height: usize,
    pub(crate) frame_rate: Option<f64>,
    pub(crate) pixel_format: VideoPixelFormat,
}

type MakepadCameraPairScore = (i32, i64, i64, i64, i64);
type MakepadCameraPairCandidate = (
    MakepadCameraChoice,
    MakepadCameraChoice,
    MakepadCameraPairScore,
);

impl MakepadCameraChoice {
    pub(crate) fn new(
        source_index: usize,
        input_id: VideoInputId,
        format: VideoFormat,
        source_class: &'static str,
        camera_id: Option<String>,
    ) -> Self {
        Self {
            source_index,
            input_id,
            format_id: format.format_id,
            camera_id,
            source_class,
            width: format.width,
            height: format.height,
            frame_rate: format.frame_rate,
            pixel_format: format.pixel_format,
        }
    }

    fn score(&self) -> (i32, i64, i64, i64) {
        let source_rank = match self.source_class {
            "back" => 3,
            "external" => 2,
            "front" => 1,
            _ => 0,
        };
        let frame_rate_milli = self
            .frame_rate
            .filter(|rate| rate.is_finite() && *rate > 0.0)
            .map(|rate| (rate * 1000.0).round() as i64)
            .unwrap_or(0);
        let target_penalty = self.width.abs_diff(1280) + self.height.abs_diff(1280);
        let square_penalty = self.width.abs_diff(self.height);
        let area = (self.width as i64) * (self.height as i64);
        (
            source_rank,
            frame_rate_milli,
            area - (target_penalty as i64) * 2048 - (square_penalty as i64) * 4096,
            area,
        )
    }

    fn broker_h264(label: &'static str, width: u32, height: u32) -> Self {
        let source_index = if label == "right" { 1 } else { 0 };
        Self {
            source_index,
            input_id: Default::default(),
            format_id: Default::default(),
            camera_id: Some(format!("broker-h264-{label}")),
            source_class: "synthetic",
            width: width as usize,
            height: height as usize,
            frame_rate: None,
            pixel_format: VideoPixelFormat::Unsupported(0x6832_3634),
        }
    }
}

#[derive(Clone)]
pub(crate) struct MakepadCameraPair {
    pub(crate) left: MakepadCameraChoice,
    pub(crate) right: MakepadCameraChoice,
    pub(crate) projection_metadata_ready: bool,
    pub(crate) projection_geometry_profile: String,
    pub(crate) pose_source: String,
    pub(crate) source_eye_mapping: String,
    pub(crate) source_binding_mode: String,
    pub(crate) coordinate_chain: String,
    pub(crate) fallback_reason: String,
    pub(crate) left_surface_to_camera_h: [[f32; 3]; 3],
    pub(crate) right_surface_to_camera_h: [[f32; 3]; 3],
    pub(crate) left_surface_to_screen_h: [[f32; 3]; 3],
    pub(crate) right_surface_to_screen_h: [[f32; 3]; 3],
    pub(crate) left_screen_to_camera_h: [[f32; 3]; 3],
    pub(crate) right_screen_to_camera_h: [[f32; 3]; 3],
    pub(crate) left_screen_to_surface_h: [[f32; 3]; 3],
    pub(crate) right_screen_to_surface_h: [[f32; 3]; 3],
    pub(crate) left_source_valid_uv_rect: Rect2,
    pub(crate) right_source_valid_uv_rect: Rect2,
    pub(crate) target_footprint: MakepadTargetScreenFootprintPair,
    pub(crate) projection_homography_ready: bool,
    pub(crate) runtime_xr_view_state_ready: bool,
    pub(crate) openxr_contract: MakepadOpenXrProjectionContract,
}

impl MakepadCameraPair {
    pub(crate) fn from_broker_h264_source(source: &ExternalH264VideoSource) -> Self {
        let width = source.preferred_width.max(1);
        let height = source.preferred_height.max(1);
        let left = MakepadCameraChoice::broker_h264("left", width, height);
        let right = MakepadCameraChoice::broker_h264("right", width, height);
        let source_mode = source
            .source_mode
            .trim()
            .to_ascii_lowercase()
            .replace('_', "-");
        let source_binding_mode = match source_mode.as_str() {
            "broker-camera" | "camera" | "camera2" => "broker-h264-camera-stereo-stream",
            "existing-stream" | "existing" | "remote" | "proxied" | "proxy" | "proxy-stream"
            | "incoming" | "incoming-stream" => "broker-h264-existing-stereo-stream",
            _ => "broker-h264-synthetic-stereo-stream",
        };
        let pose_source = match source_binding_mode {
            "broker-h264-camera-stereo-stream" => "broker-camera-h264-stream-header-pending",
            "broker-h264-existing-stereo-stream" => "broker-existing-h264-stream-header-pending",
            _ => "broker-synthetic-h264-stream-header-pending",
        };
        Self {
            left,
            right,
            projection_metadata_ready: false,
            projection_geometry_profile: source.synthetic_projection_profile.clone(),
            pose_source: pose_source.to_string(),
            source_eye_mapping: "left-right".to_string(),
            source_binding_mode: source_binding_mode.to_string(),
            coordinate_chain: "broker-h264-delivered-stereo-images-to-shader-surface".to_string(),
            fallback_reason: "waiting_for_broker_h264_stream_header".to_string(),
            left_surface_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_surface_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_surface_to_screen_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_surface_to_screen_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_screen_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_screen_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_screen_to_surface_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_screen_to_surface_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_source_valid_uv_rect: Rect2::UNIT,
            right_source_valid_uv_rect: Rect2::UNIT,
            target_footprint: makepad_runtime_target_screen_footprint_pair(),
            projection_homography_ready: false,
            runtime_xr_view_state_ready: false,
            openxr_contract: MakepadOpenXrProjectionContract::missing(),
        }
    }

    pub(crate) fn from_camera2_plan(
        choices: &[MakepadCameraChoice],
        plan: &Camera2StereoPlan,
    ) -> Option<Self> {
        let left = best_choice_for_camera_id(choices, &plan.left_camera_id, plan.size()).or_else(
            || best_choice_for_source_index(choices, plan.left_source_index, plan.size()),
        )?;
        let right = best_choice_for_camera_id(choices, &plan.right_camera_id, plan.size())
            .or_else(|| {
                best_choice_for_source_index(choices, plan.right_source_index, plan.size())
            })?;
        if left.source_index == right.source_index {
            return None;
        }
        let source_binding_mode = if left.camera_id.as_deref() == Some(plan.left_camera_id.as_str())
            && right.camera_id.as_deref() == Some(plan.right_camera_id.as_str())
        {
            "camera-id"
        } else {
            "source-index-fallback"
        };
        let source_binding_mode = if plan.projection_geometry_profile == "full-frame-diagnostic" {
            format!("direct-camera2-full-frame-diagnostic-{source_binding_mode}")
        } else {
            source_binding_mode.to_string()
        };

        let _input_source_eye_mapping = &plan.source_eye_mapping;
        Some(Self {
            left,
            right,
            projection_metadata_ready: plan.projection_metadata_ready,
            projection_geometry_profile: plan.projection_geometry_profile.clone(),
            pose_source: plan.pose_source.clone(),
            source_eye_mapping: makepad_display_source_eye_mapping().to_string(),
            source_binding_mode,
            coordinate_chain: plan.coordinate_chain.clone(),
            fallback_reason: plan.fallback_reason.clone(),
            left_surface_to_camera_h: plan.left_surface_to_camera_h,
            right_surface_to_camera_h: plan.right_surface_to_camera_h,
            left_surface_to_screen_h: plan.left_surface_to_screen_h,
            right_surface_to_screen_h: plan.right_surface_to_screen_h,
            left_screen_to_camera_h: plan.left_screen_to_camera_h,
            right_screen_to_camera_h: plan.right_screen_to_camera_h,
            left_screen_to_surface_h: plan.left_screen_to_surface_h,
            right_screen_to_surface_h: plan.right_screen_to_surface_h,
            left_source_valid_uv_rect: Rect2::UNIT,
            right_source_valid_uv_rect: Rect2::UNIT,
            target_footprint: makepad_runtime_target_screen_footprint_pair(),
            projection_homography_ready: plan.projection_homography_ready,
            runtime_xr_view_state_ready: plan.runtime_xr_view_state_ready,
            openxr_contract: plan.openxr_contract.clone(),
        })
    }

    pub(crate) fn from_best_available_pair(choices: &[MakepadCameraChoice]) -> Option<Self> {
        let mut best: Option<MakepadCameraPairCandidate> = None;

        for left in choices {
            for right in choices {
                if left.source_index == right.source_index
                    || left.pixel_format != right.pixel_format
                    || left.width != right.width
                    || left.height != right.height
                {
                    continue;
                }

                let source_rank =
                    source_class_rank(left.source_class) + source_class_rank(right.source_class);
                let frame_rate_milli = left
                    .frame_rate
                    .zip(right.frame_rate)
                    .filter(|(left_rate, right_rate)| {
                        left_rate.is_finite()
                            && right_rate.is_finite()
                            && *left_rate > 0.0
                            && *right_rate > 0.0
                    })
                    .map(|(left_rate, right_rate)| left_rate.min(right_rate))
                    .map(|rate| (rate * 1000.0).round() as i64)
                    .unwrap_or(0);
                let area = (left.width as i64) * (left.height as i64);
                let target_penalty = left.width.abs_diff(1280) + left.height.abs_diff(1280);
                let square_penalty = left.width.abs_diff(left.height);
                let index_spacing = left.source_index.abs_diff(right.source_index) as i64;
                let score = (
                    source_rank,
                    frame_rate_milli,
                    area - (target_penalty as i64) * 2048 - (square_penalty as i64) * 4096,
                    area,
                    -index_spacing,
                );

                if best
                    .as_ref()
                    .map(|(_, _, best_score)| score > *best_score)
                    .unwrap_or(true)
                {
                    best = Some((left.clone(), right.clone(), score));
                }
            }
        }

        let (left, right, _) = best?;
        Some(Self {
            left,
            right,
            projection_metadata_ready: false,
            projection_geometry_profile: DEFAULT_CAMERA_PROJECTION_GEOMETRY_PROFILE.to_string(),
            pose_source: "missing".to_string(),
            source_eye_mapping: makepad_display_source_eye_mapping().to_string(),
            source_binding_mode: "best-available-fallback".to_string(),
            coordinate_chain: "unresolved".to_string(),
            fallback_reason: "camera2 stereo projection metadata was not correlated".to_string(),
            left_surface_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_surface_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_surface_to_screen_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_surface_to_screen_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_screen_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_screen_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_screen_to_surface_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_screen_to_surface_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_source_valid_uv_rect: Rect2::UNIT,
            right_source_valid_uv_rect: Rect2::UNIT,
            target_footprint: makepad_runtime_target_screen_footprint_pair(),
            projection_homography_ready: false,
            runtime_xr_view_state_ready: false,
            openxr_contract: MakepadOpenXrProjectionContract::missing(),
        })
    }

    #[cfg(target_os = "android")]
    pub(crate) fn apply_broker_projection_plan(
        &mut self,
        plan: &Camera2StereoPlan,
        decision: &BrokerProjectionPlanDecision,
        left_metadata: &BrokerH264ProjectionMetadata,
        right_metadata: &BrokerH264ProjectionMetadata,
    ) {
        self.left.camera_id = Some(plan.left_camera_id.clone());
        self.right.camera_id = Some(plan.right_camera_id.clone());
        self.left.width = plan.width as usize;
        self.left.height = plan.height as usize;
        self.right.width = plan.width as usize;
        self.right.height = plan.height as usize;
        self.projection_metadata_ready =
            left_metadata.projection_metadata_ready && right_metadata.projection_metadata_ready;
        self.projection_geometry_profile = decision.projection_geometry_profile.clone();
        self.pose_source = broker_pair_pose_source(left_metadata, right_metadata);
        self.source_eye_mapping = plan.source_eye_mapping.clone();
        self.source_binding_mode = decision.source_binding_mode.to_string();
        self.coordinate_chain = plan.coordinate_chain.clone();
        self.fallback_reason = plan.fallback_reason.clone();
        self.left_surface_to_camera_h = plan.left_surface_to_camera_h;
        self.right_surface_to_camera_h = plan.right_surface_to_camera_h;
        self.left_surface_to_screen_h = plan.left_surface_to_screen_h;
        self.right_surface_to_screen_h = plan.right_surface_to_screen_h;
        self.left_screen_to_camera_h = plan.left_screen_to_camera_h;
        self.right_screen_to_camera_h = plan.right_screen_to_camera_h;
        self.left_screen_to_surface_h = plan.left_screen_to_surface_h;
        self.right_screen_to_surface_h = plan.right_screen_to_surface_h;
        self.left_source_valid_uv_rect = left_metadata.source_valid_uv_rect;
        self.right_source_valid_uv_rect = right_metadata.source_valid_uv_rect;
        self.target_footprint = match (
            left_metadata.target_screen_uv_rect,
            right_metadata.target_screen_uv_rect,
        ) {
            (Some(left_rect), Some(right_rect)) => MakepadTargetScreenFootprintPair {
                left_rect,
                right_rect,
                from_metadata: true,
                defaulted: left_metadata.target_footprint_default
                    && right_metadata.target_footprint_default,
            },
            _ => makepad_runtime_target_screen_footprint_pair(),
        };
        self.projection_homography_ready = plan.projection_homography_ready;
        self.runtime_xr_view_state_ready = plan.runtime_xr_view_state_ready;
        self.openxr_contract = plan.openxr_contract.clone();
    }

    #[cfg_attr(not(target_os = "android"), allow(dead_code))]
    pub(crate) fn matches_camera2_plan(&self, plan: &Camera2StereoPlan) -> bool {
        let camera_id_match = self.left.camera_id.as_deref() == Some(plan.left_camera_id.as_str())
            && self.right.camera_id.as_deref() == Some(plan.right_camera_id.as_str());
        let source_index_match = self.left.source_index == plan.left_source_index
            && self.right.source_index == plan.right_source_index;
        camera_id_match || source_index_match
    }
}

#[derive(Clone)]
pub(crate) struct Camera2StereoPlan {
    pub(crate) left_source_index: usize,
    pub(crate) right_source_index: usize,
    pub(crate) left_camera_id: String,
    pub(crate) right_camera_id: String,
    pub(crate) width: u32,
    pub(crate) height: u32,
    pub(crate) projection_metadata_ready: bool,
    pub(crate) projection_geometry_profile: String,
    pub(crate) pose_source: String,
    pub(crate) source_eye_mapping: String,
    pub(crate) coordinate_chain: String,
    pub(crate) fallback_reason: String,
    pub(crate) left_surface_to_camera_h: [[f32; 3]; 3],
    pub(crate) right_surface_to_camera_h: [[f32; 3]; 3],
    pub(crate) left_surface_to_screen_h: [[f32; 3]; 3],
    pub(crate) right_surface_to_screen_h: [[f32; 3]; 3],
    pub(crate) left_screen_to_camera_h: [[f32; 3]; 3],
    pub(crate) right_screen_to_camera_h: [[f32; 3]; 3],
    pub(crate) left_screen_to_surface_h: [[f32; 3]; 3],
    pub(crate) right_screen_to_surface_h: [[f32; 3]; 3],
    pub(crate) projection_homography_ready: bool,
    pub(crate) runtime_xr_view_state_ready: bool,
    pub(crate) openxr_contract: MakepadOpenXrProjectionContract,
}

impl Camera2StereoPlan {
    pub(crate) fn size(&self) -> (usize, usize) {
        (self.width as usize, self.height as usize)
    }

    pub(crate) fn apply_projection_geometry_profile(&mut self, profile: &str) {
        let profile = normalize_direct_camera_projection_geometry_profile(profile);
        self.projection_geometry_profile = profile.clone();
        if profile == "camera-projection" {
            if !self
                .coordinate_chain
                .contains("direct-camera2-screen-to-camera-homography")
            {
                self.coordinate_chain = format!(
                    "direct-camera2-screen-to-camera-homography/{}",
                    self.coordinate_chain
                );
            }
            if self.fallback_reason == "unsupported_direct_camera_projection_geometry_profile" {
                self.fallback_reason = if self.projection_homography_ready {
                    "none".to_string()
                } else {
                    "waiting_for_camera2_projection_homography".to_string()
                };
            }
            return;
        }
        if profile != "full-frame-diagnostic" {
            self.projection_metadata_ready = false;
            self.projection_homography_ready = false;
            self.fallback_reason = format!(
                "unsupported_direct_camera_projection_geometry_profile:{}",
                marker_token(&profile)
            );
            if !self
                .coordinate_chain
                .contains("unsupported-direct-camera-projection-geometry-profile")
            {
                self.coordinate_chain = format!(
                    "unsupported-direct-camera-projection-geometry-profile:{}/{}",
                    marker_token(&profile),
                    self.coordinate_chain
                );
            }
            return;
        }

        self.projection_metadata_ready = self.runtime_xr_view_state_ready;
        self.pose_source = "projection-surface".to_string();
        self.fallback_reason = if self.runtime_xr_view_state_ready {
            "none".to_string()
        } else {
            "waiting_for_runtime_openxr_view_state".to_string()
        };
        self.left_surface_to_camera_h = IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY;
        self.right_surface_to_camera_h = IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY;
        self.left_screen_to_camera_h = self.left_screen_to_surface_h;
        self.right_screen_to_camera_h = self.right_screen_to_surface_h;
        self.projection_homography_ready = self.runtime_xr_view_state_ready;
        if !self
            .coordinate_chain
            .contains("direct-camera2-full-frame-diagnostic-projection-surface")
        {
            self.coordinate_chain = format!(
                "direct-camera2-full-frame-diagnostic-projection-surface/{}",
                self.coordinate_chain
            );
        }
    }
}

#[cfg(target_os = "android")]
impl From<android_camera_probe::StereoProjectionPlan> for Camera2StereoPlan {
    fn from(plan: android_camera_probe::StereoProjectionPlan) -> Self {
        Self {
            left_source_index: plan.left_source_index,
            right_source_index: plan.right_source_index,
            left_camera_id: plan.left_camera_id,
            right_camera_id: plan.right_camera_id,
            width: plan.width,
            height: plan.height,
            projection_metadata_ready: plan.projection_metadata_ready,
            projection_geometry_profile: "camera2-platform-unprofiled".to_string(),
            pose_source: plan.pose_source.to_string(),
            source_eye_mapping: plan.source_eye_mapping.to_string(),
            coordinate_chain: plan.coordinate_chain.to_string(),
            fallback_reason: plan.fallback_reason.to_string(),
            left_surface_to_camera_h: plan.left_surface_to_camera_h,
            right_surface_to_camera_h: plan.right_surface_to_camera_h,
            left_surface_to_screen_h: plan.left_surface_to_screen_h,
            right_surface_to_screen_h: plan.right_surface_to_screen_h,
            left_screen_to_camera_h: plan.left_screen_to_camera_h,
            right_screen_to_camera_h: plan.right_screen_to_camera_h,
            left_screen_to_surface_h: plan.left_screen_to_surface_h,
            right_screen_to_surface_h: plan.right_screen_to_surface_h,
            projection_homography_ready: plan.projection_homography_ready,
            runtime_xr_view_state_ready: plan.runtime_xr_view_state_ready,
            openxr_contract: MakepadOpenXrProjectionContract::from_android(plan.openxr_contract),
        }
    }
}

fn best_choice_for_source_index(
    choices: &[MakepadCameraChoice],
    source_index: usize,
    preferred_size: (usize, usize),
) -> Option<MakepadCameraChoice> {
    choices
        .iter()
        .filter(|choice| choice.source_index == source_index)
        .max_by_key(|choice| {
            let preferred_match =
                (choice.width == preferred_size.0 && choice.height == preferred_size.1) as i32;
            (preferred_match, choice.score())
        })
        .cloned()
}

fn best_choice_for_camera_id(
    choices: &[MakepadCameraChoice],
    camera_id: &str,
    preferred_size: (usize, usize),
) -> Option<MakepadCameraChoice> {
    if camera_id.is_empty() {
        return None;
    }
    choices
        .iter()
        .filter(|choice| choice.camera_id.as_deref() == Some(camera_id))
        .max_by_key(|choice| {
            let preferred_match =
                (choice.width == preferred_size.0 && choice.height == preferred_size.1) as i32;
            (preferred_match, choice.score())
        })
        .cloned()
}

fn source_class_rank(source_class: &str) -> i32 {
    match source_class {
        "back" => 3,
        "external" => 2,
        "front" => 1,
        _ => 0,
    }
}

fn camera_id_from_makepad_desc_name(name: &str) -> Option<String> {
    let marker = "cameraId=";
    let start = name.find(marker)? + marker.len();
    let value = name[start..]
        .chars()
        .take_while(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '_' | '-' | '.')
        })
        .collect::<String>();
    (!value.is_empty()).then_some(value)
}

fn camera_source_class(name: &str) -> &'static str {
    let lower = name.to_ascii_lowercase();
    if lower.contains("back") {
        "back"
    } else if lower.contains("external") {
        "external"
    } else if lower.contains("front") {
        "front"
    } else {
        "unknown"
    }
}

pub(crate) fn pixel_format_label(format: VideoPixelFormat) -> &'static str {
    match format {
        VideoPixelFormat::RGB24 => "rgb24",
        VideoPixelFormat::YUY2 => "yuy2",
        VideoPixelFormat::NV12 => "nv12",
        VideoPixelFormat::YUV420 => "yuv420",
        VideoPixelFormat::GRAY => "gray",
        VideoPixelFormat::MJPEG => "mjpeg",
        VideoPixelFormat::Unsupported(_) => "unsupported",
    }
}

pub(crate) fn frame_rate_token(frame_rate: Option<f64>) -> String {
    frame_rate
        .filter(|rate| rate.is_finite() && *rate > 0.0)
        .map(|rate| format!("{rate:.2}"))
        .unwrap_or_else(|| "unknown".to_string())
}

pub(crate) fn makepad_display_source_eye_mapping() -> &'static str {
    match option_env!("RUSTY_MAKEPAD_DISPLAY_SOURCE_EYE_MAPPING") {
        Some("display-left-from-left-source") => "display-left-from-left-source",
        Some("display-left-from-right-source") => "display-left-from-right-source",
        _ => DEFAULT_MAKEPAD_DISPLAY_SOURCE_EYE_MAPPING,
    }
}

pub(crate) fn makepad_display_left_from_right_source() -> bool {
    makepad_display_source_eye_mapping() == "display-left-from-right-source"
}

#[cfg(target_os = "android")]
fn broker_pair_pose_source(
    left: &BrokerH264ProjectionMetadata,
    right: &BrokerH264ProjectionMetadata,
) -> String {
    if left.pose_source == right.pose_source {
        left.pose_source.clone()
    } else {
        format!("{}+{}", left.pose_source, right.pose_source)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn yuv_choice(
        source_index: usize,
        camera_id: Option<&str>,
        width: usize,
        height: usize,
    ) -> MakepadCameraChoice {
        MakepadCameraChoice::new(
            source_index,
            Default::default(),
            VideoFormat {
                format_id: Default::default(),
                width,
                height,
                frame_rate: Some(72.0),
                pixel_format: VideoPixelFormat::YUV420,
            },
            "back",
            camera_id.map(str::to_string),
        )
    }

    fn test_plan() -> Camera2StereoPlan {
        Camera2StereoPlan {
            left_source_index: 0,
            right_source_index: 1,
            left_camera_id: "50".to_string(),
            right_camera_id: "51".to_string(),
            width: 1280,
            height: 1280,
            projection_metadata_ready: true,
            projection_geometry_profile: "camera2-platform-unprofiled".to_string(),
            pose_source: "platform-openxr-view".to_string(),
            source_eye_mapping: DEFAULT_MAKEPAD_DISPLAY_SOURCE_EYE_MAPPING.to_string(),
            coordinate_chain: "camera2-sensor-reference-to-openxr-head-basis".to_string(),
            fallback_reason: "none".to_string(),
            left_surface_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_surface_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_surface_to_screen_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_surface_to_screen_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_screen_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_screen_to_camera_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            left_screen_to_surface_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            right_screen_to_surface_h: IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY,
            projection_homography_ready: true,
            runtime_xr_view_state_ready: true,
            openxr_contract: MakepadOpenXrProjectionContract::missing(),
        }
    }

    #[test]
    fn parses_makepad_descriptor_camera_id_token() {
        assert_eq!(
            camera_id_from_makepad_desc_name("Back Camera cameraId=50").as_deref(),
            Some("50")
        );
        assert_eq!(
            camera_id_from_makepad_desc_name("External cameraId=cam_12-3.4 fps=72").as_deref(),
            Some("cam_12-3.4")
        );
        assert_eq!(camera_id_from_makepad_desc_name("Back Camera"), None);
    }

    #[test]
    fn camera_id_choice_prefers_requested_size() {
        let choices = vec![
            yuv_choice(0, Some("50"), 640, 640),
            yuv_choice(1, Some("51"), 1280, 1280),
            yuv_choice(2, Some("50"), 1280, 1280),
        ];

        let choice = best_choice_for_camera_id(&choices, "50", (1280, 1280)).unwrap();

        assert_eq!(choice.source_index, 2);
        assert_eq!(choice.camera_id.as_deref(), Some("50"));
        assert_eq!((choice.width, choice.height), (1280, 1280));
    }

    #[test]
    fn camera_id_pair_binding_overrides_misleading_source_index() {
        let choices = vec![
            yuv_choice(0, Some("51"), 1280, 1280),
            yuv_choice(1, Some("50"), 1280, 1280),
        ];
        let plan = test_plan();

        let pair = MakepadCameraPair::from_camera2_plan(&choices, &plan).unwrap();

        assert_eq!(pair.source_binding_mode, "camera-id");
        assert_eq!(pair.left.camera_id.as_deref(), Some("50"));
        assert_eq!(pair.right.camera_id.as_deref(), Some("51"));
        assert_eq!(pair.left.source_index, 1);
        assert_eq!(pair.right.source_index, 0);
        assert!(pair.matches_camera2_plan(&plan));
    }

    #[test]
    fn direct_full_frame_profile_marks_source_binding_and_homography() {
        let choices = vec![
            yuv_choice(0, Some("51"), 1280, 1280),
            yuv_choice(1, Some("50"), 1280, 1280),
        ];
        let mut plan = test_plan();

        plan.apply_projection_geometry_profile("full-frame-diagnostic");
        let pair = MakepadCameraPair::from_camera2_plan(&choices, &plan).unwrap();

        assert_eq!(
            pair.source_binding_mode,
            "direct-camera2-full-frame-diagnostic-camera-id"
        );
        assert_eq!(
            pair.left_surface_to_camera_h,
            IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY
        );
        assert_eq!(
            pair.left_screen_to_camera_h,
            IDENTITY_SURFACE_TO_CAMERA_HOMOGRAPHY
        );
        assert!(pair
            .coordinate_chain
            .contains("direct-camera2-full-frame-diagnostic-projection-surface"));
    }

    #[test]
    fn compile_time_source_eye_mapping_is_sanitized() {
        let expected = match option_env!("RUSTY_MAKEPAD_DISPLAY_SOURCE_EYE_MAPPING") {
            Some("display-left-from-left-source") => "display-left-from-left-source",
            Some("display-left-from-right-source") => "display-left-from-right-source",
            _ => DEFAULT_MAKEPAD_DISPLAY_SOURCE_EYE_MAPPING,
        };
        assert_eq!(makepad_display_source_eye_mapping(), expected);
    }

    #[test]
    fn default_source_eye_mapping_matches_hwb_and_oes() {
        assert_eq!(
            DEFAULT_MAKEPAD_DISPLAY_SOURCE_EYE_MAPPING,
            "display-left-from-left-source"
        );
    }
}
