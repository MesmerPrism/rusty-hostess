#[cfg(target_os = "android")]
use crate::hostess_camera_model::{
    camera2_lens_pose_to_extrinsics, camera_basis_from_camera2_reference_pose_relative_to_center,
    head_anchored_preview_surface_corners, invert_homography, scale_intrinsics_to_image,
    screen_to_camera_uv_homography, surface_to_camera_uv_homography,
    surface_to_eye_screen_uv_homography, CameraBasis, CameraIntrinsics, ImageSize, Quat,
    TrackingBasis, Vec2, Vec3,
};
#[cfg(target_os = "android")]
use std::ffi::CString;

#[cfg(target_os = "android")]
use crate::acamera_sys::ACAMERA_LENS_FACING_BACK;

#[cfg(target_os = "android")]
use super::android_camera_probe::{CameraSource, NativeIntrinsics};

mod markers;

// Keep marker/reporting names available through projection_geometry while the
// implementation lives in a focused child module.
#[allow(unused_imports)]
pub(crate) use markers::{
    makepad_draw_vars_bound_marker_fields, makepad_horizontal_alignment_hotload_marker_fields,
    makepad_native_video_widget_reset_error_marker_fields,
    makepad_native_video_widget_reset_waiting_marker_fields,
    makepad_native_video_widget_surface_marker_fields,
    makepad_paired_projection_progress_marker_fields,
    makepad_projection_complete_error_marker_fields, makepad_projection_complete_marker_fields,
    makepad_projection_enumerated_marker_fields, makepad_projection_start_marker_fields,
    makepad_projection_target_marker_fields, makepad_single_stream_proof_wait_marker_fields,
    makepad_stereo_comparison_marker_line, makepad_stereo_projection_marker_line,
    makepad_synthetic_stereo_comparison_marker_line, makepad_visible_panel_bound_marker_fields,
    makepad_visible_panel_draw_marker_line, projection_homography_marker_fields,
    MakepadStereoComparisonMarkerInputs,
};

#[cfg(target_os = "android")]
pub(crate) use markers::broker_projection_plan_marker_fields;

#[cfg(target_os = "android")]
const DEFAULT_PROJECTION_TARGET_DEPTH_METERS: f32 = 1.0;
#[cfg(target_os = "android")]
const PROJECTION_PREVIEW_FOV_Y_DEGREES: f32 = 60.0;
#[cfg(target_os = "android")]
const PROJECTION_RAW_OVERSCAN: f32 = 1.06;
#[cfg(target_os = "android")]
const PROJECTION_SOURCE_ASPECT: f32 = 1.0;
#[cfg(target_os = "android")]
const DISPLAY_EYE_OFFSET_METERS: f32 = 0.032;
#[cfg(target_os = "android")]
const DISPLAY_FOV_Y_DEGREES: f32 = 92.0;
#[cfg(target_os = "android")]
const DISPLAY_ASPECT: f32 = 1.0;
#[cfg(target_os = "android")]
const DEFAULT_DISPLAY_SOURCE_EYE_MAPPING: &str = "display-left-from-left-source";
#[cfg(target_os = "android")]
const IDENTITY_HOMOGRAPHY: [[f32; 3]; 3] = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]];

#[cfg(target_os = "android")]
#[derive(Clone, Copy, Debug)]
pub struct XrDisplayEyeView {
    pub position: [f32; 3],
    pub orientation: [f32; 4],
    pub angle_left: f32,
    pub angle_right: f32,
    pub angle_up: f32,
    pub angle_down: f32,
    pub valid: bool,
}

#[cfg(target_os = "android")]
#[derive(Clone, Copy, Debug)]
pub struct XrDisplayViews {
    pub left: XrDisplayEyeView,
    pub right: XrDisplayEyeView,
    pub predicted_display_time_ns: i64,
    pub reference_space: &'static str,
    pub projection_depth_meters: f32,
    pub projection_preview_fov_y_degrees: f32,
    pub projection_preview_offset_y_meters: f32,
    pub projection_raw_overscan: f32,
}

#[cfg(target_os = "android")]
#[derive(Clone, Copy, Debug)]
pub struct XrProjectionContract {
    pub reference_space: &'static str,
    pub openxr_reference_space: &'static str,
    pub display_time_source: &'static str,
    pub predicted_display_time_ns: Option<i64>,
    pub view_pose_fov_source: &'static str,
    pub projection_depth_meters: Option<f32>,
    pub projection_preview_fov_y_degrees: Option<f32>,
    pub projection_preview_offset_y_meters: Option<f32>,
    pub projection_raw_overscan: Option<f32>,
    pub left_render_fov_tangents: Option<[f32; 4]>,
    pub right_render_fov_tangents: Option<[f32; 4]>,
    pub left_render_position: Option<[f32; 4]>,
    pub right_render_position: Option<[f32; 4]>,
    pub left_render_orientation: Option<[f32; 4]>,
    pub right_render_orientation: Option<[f32; 4]>,
}

#[cfg(target_os = "android")]
impl XrProjectionContract {
    fn missing() -> Self {
        Self {
            reference_space: "not-logged",
            openxr_reference_space: "not-logged",
            display_time_source: "not-logged",
            predicted_display_time_ns: None,
            view_pose_fov_source: "not-logged",
            projection_depth_meters: None,
            projection_preview_fov_y_degrees: None,
            projection_preview_offset_y_meters: None,
            projection_raw_overscan: None,
            left_render_fov_tangents: None,
            right_render_fov_tangents: None,
            left_render_position: None,
            right_render_position: None,
            left_render_orientation: None,
            right_render_orientation: None,
        }
    }

    fn from_views(views: XrDisplayViews) -> Self {
        Self {
            reference_space: "app-reference-space",
            openxr_reference_space: views.reference_space,
            display_time_source: "predicted-display-time",
            predicted_display_time_ns: Some(views.predicted_display_time_ns),
            view_pose_fov_source: "makepad-xr-XrUpdateEvent",
            projection_depth_meters: Some(views.projection_depth_meters),
            projection_preview_fov_y_degrees: Some(views.projection_preview_fov_y_degrees),
            projection_preview_offset_y_meters: Some(views.projection_preview_offset_y_meters),
            projection_raw_overscan: Some(views.projection_raw_overscan),
            left_render_fov_tangents: Some(fov_tangents(views.left)),
            right_render_fov_tangents: Some(fov_tangents(views.right)),
            left_render_position: Some(position_vec4(views.left)),
            right_render_position: Some(position_vec4(views.right)),
            left_render_orientation: Some(orientation_vec4(views.left)),
            right_render_orientation: Some(orientation_vec4(views.right)),
        }
    }
}

#[cfg(target_os = "android")]
#[derive(Clone, Debug)]
struct ProjectionHomographies {
    left_surface_to_camera_h: [[f32; 3]; 3],
    right_surface_to_camera_h: [[f32; 3]; 3],
    left_surface_to_screen_h: [[f32; 3]; 3],
    right_surface_to_screen_h: [[f32; 3]; 3],
    left_screen_to_camera_h: [[f32; 3]; 3],
    right_screen_to_camera_h: [[f32; 3]; 3],
    left_screen_to_surface_h: [[f32; 3]; 3],
    right_screen_to_surface_h: [[f32; 3]; 3],
}

#[cfg(target_os = "android")]
impl ProjectionHomographies {
    fn identity() -> Self {
        Self {
            left_surface_to_camera_h: IDENTITY_HOMOGRAPHY,
            right_surface_to_camera_h: IDENTITY_HOMOGRAPHY,
            left_surface_to_screen_h: IDENTITY_HOMOGRAPHY,
            right_surface_to_screen_h: IDENTITY_HOMOGRAPHY,
            left_screen_to_camera_h: IDENTITY_HOMOGRAPHY,
            right_screen_to_camera_h: IDENTITY_HOMOGRAPHY,
            left_screen_to_surface_h: IDENTITY_HOMOGRAPHY,
            right_screen_to_surface_h: IDENTITY_HOMOGRAPHY,
        }
    }
}

#[cfg(target_os = "android")]
#[derive(Clone)]
pub(super) struct StereoProjectionSources {
    pub(super) left_source_index: usize,
    pub(super) left: CameraSource,
    pub(super) right_source_index: usize,
    pub(super) right: CameraSource,
    pub(super) width: u32,
    pub(super) height: u32,
}

#[cfg(target_os = "android")]
#[derive(Clone, Debug)]
pub struct StereoProjectionPlan {
    pub left_source_index: usize,
    pub right_source_index: usize,
    pub left_camera_id: String,
    pub right_camera_id: String,
    pub left_facing: &'static str,
    pub right_facing: &'static str,
    pub width: u32,
    pub height: u32,
    pub projection_metadata_ready: bool,
    pub pose_source: &'static str,
    pub source_eye_mapping: &'static str,
    pub coordinate_chain: &'static str,
    pub fallback_reason: &'static str,
    pub left_surface_to_camera_h: [[f32; 3]; 3],
    pub right_surface_to_camera_h: [[f32; 3]; 3],
    pub left_surface_to_screen_h: [[f32; 3]; 3],
    pub right_surface_to_screen_h: [[f32; 3]; 3],
    pub left_screen_to_camera_h: [[f32; 3]; 3],
    pub right_screen_to_camera_h: [[f32; 3]; 3],
    pub left_screen_to_surface_h: [[f32; 3]; 3],
    pub right_screen_to_surface_h: [[f32; 3]; 3],
    pub projection_homography_ready: bool,
    pub runtime_xr_view_state_ready: bool,
    pub openxr_contract: XrProjectionContract,
}

#[cfg(target_os = "android")]
#[derive(Clone, Debug)]
pub struct BrokerProjectionSource {
    pub camera_id: String,
    pub intrinsics_fx: f32,
    pub intrinsics_fy: f32,
    pub intrinsics_cx: f32,
    pub intrinsics_cy: f32,
    pub intrinsics_skew: f32,
    pub intrinsics_domain_width: u32,
    pub intrinsics_domain_height: u32,
    pub pose_translation: [f32; 3],
    pub pose_rotation: [f32; 4],
}

#[cfg(target_os = "android")]
impl BrokerProjectionSource {
    fn camera_source(&self) -> Option<CameraSource> {
        let camera_id_c = CString::new(self.camera_id.clone()).ok()?;
        let intrinsics_width = self.intrinsics_domain_width.max(1);
        let intrinsics_height = self.intrinsics_domain_height.max(1);
        Some(CameraSource {
            camera_id_c,
            lens_facing: ACAMERA_LENS_FACING_BACK,
            logical_multi_camera: false,
            physical_camera_ids: Vec::new(),
            sensor_sync_type: None,
            private_sizes: Vec::new(),
            intrinsics: Some(NativeIntrinsics {
                fx: self.intrinsics_fx,
                fy: self.intrinsics_fy,
                cx: self.intrinsics_cx,
                cy: self.intrinsics_cy,
                skew: self.intrinsics_skew,
            }),
            active_array_size: Some((intrinsics_width, intrinsics_height)),
            pose_translation: Some(self.pose_translation),
            pose_rotation: Some(self.pose_rotation),
        })
    }
}

#[cfg(target_os = "android")]
impl StereoProjectionPlan {
    pub(super) fn from_sources(sources: &StereoProjectionSources) -> Self {
        let left = &sources.left;
        let right = &sources.right;
        let width = sources.width;
        let height = sources.height;
        let projection_metadata_ready = left.has_projection_metadata()
            && right.has_projection_metadata()
            && width > 0
            && height > 0;
        let (homographies, projection_homography_ready) =
            stereo_projection_homographies(left, right, width, height)
                .map(|homographies| (homographies, true))
                .unwrap_or_else(|| (ProjectionHomographies::identity(), false));

        Self {
            left_source_index: sources.left_source_index,
            right_source_index: sources.right_source_index,
            left_camera_id: left.camera_id_label(),
            right_camera_id: right.camera_id_label(),
            left_facing: left.lens_facing_label(),
            right_facing: right.lens_facing_label(),
            width,
            height,
            projection_metadata_ready,
            pose_source: if projection_metadata_ready {
                "platform"
            } else {
                "missing"
            },
            source_eye_mapping: display_source_eye_mapping(),
            coordinate_chain: "camera2-sensor-reference-to-openxr-head-basis",
            fallback_reason: if projection_metadata_ready {
                "none"
            } else {
                "selected stereo pair is missing intrinsics or pose metadata"
            },
            left_surface_to_camera_h: homographies.left_surface_to_camera_h,
            right_surface_to_camera_h: homographies.right_surface_to_camera_h,
            left_surface_to_screen_h: homographies.left_surface_to_screen_h,
            right_surface_to_screen_h: homographies.right_surface_to_screen_h,
            left_screen_to_camera_h: homographies.left_screen_to_camera_h,
            right_screen_to_camera_h: homographies.right_screen_to_camera_h,
            left_screen_to_surface_h: homographies.left_screen_to_surface_h,
            right_screen_to_surface_h: homographies.right_screen_to_surface_h,
            projection_homography_ready,
            runtime_xr_view_state_ready: false,
            openxr_contract: XrProjectionContract::missing(),
        }
    }

    pub(super) fn from_sources_and_xr_views(
        sources: &StereoProjectionSources,
        views: XrDisplayViews,
    ) -> Option<Self> {
        let left = &sources.left;
        let right = &sources.right;
        let projection_metadata_ready = left.has_projection_metadata()
            && right.has_projection_metadata()
            && sources.width > 0
            && sources.height > 0
            && views.left.valid
            && views.right.valid;
        let homographies = stereo_projection_homographies_from_xr_views(
            left,
            right,
            sources.width,
            sources.height,
            views,
        )?;

        Some(Self {
            left_source_index: sources.left_source_index,
            right_source_index: sources.right_source_index,
            left_camera_id: left.camera_id_label(),
            right_camera_id: right.camera_id_label(),
            left_facing: left.lens_facing_label(),
            right_facing: right.lens_facing_label(),
            width: sources.width,
            height: sources.height,
            projection_metadata_ready,
            pose_source: "platform-openxr-view",
            source_eye_mapping: display_source_eye_mapping(),
            coordinate_chain: "camera2-sensor-reference-to-openxr-head-basis",
            fallback_reason: "none",
            left_surface_to_camera_h: homographies.left_surface_to_camera_h,
            right_surface_to_camera_h: homographies.right_surface_to_camera_h,
            left_surface_to_screen_h: homographies.left_surface_to_screen_h,
            right_surface_to_screen_h: homographies.right_surface_to_screen_h,
            left_screen_to_camera_h: homographies.left_screen_to_camera_h,
            right_screen_to_camera_h: homographies.right_screen_to_camera_h,
            left_screen_to_surface_h: homographies.left_screen_to_surface_h,
            right_screen_to_surface_h: homographies.right_screen_to_surface_h,
            projection_homography_ready: projection_metadata_ready,
            runtime_xr_view_state_ready: true,
            openxr_contract: XrProjectionContract::from_views(views),
        })
    }
}

#[cfg(target_os = "android")]
pub fn broker_physical_projection_plan_from_xr_views(
    left_source: BrokerProjectionSource,
    right_source: BrokerProjectionSource,
    width: u32,
    height: u32,
    views: XrDisplayViews,
) -> Option<StereoProjectionPlan> {
    if width == 0 || height == 0 {
        return None;
    }
    let left_camera_id = left_source.camera_id.clone();
    let right_camera_id = right_source.camera_id.clone();
    let left = left_source.camera_source()?;
    let right = right_source.camera_source()?;
    let homographies =
        stereo_projection_homographies_from_xr_views(&left, &right, width, height, views)?;

    Some(StereoProjectionPlan {
        left_source_index: 0,
        right_source_index: 1,
        left_camera_id,
        right_camera_id,
        left_facing: "back",
        right_facing: "back",
        width,
        height,
        projection_metadata_ready: true,
        pose_source: "broker-stream-header-platform-openxr-view",
        source_eye_mapping: display_source_eye_mapping(),
        coordinate_chain: "broker-h264-physical-camera-stream-header-to-openxr-view",
        fallback_reason: "none",
        left_surface_to_camera_h: homographies.left_surface_to_camera_h,
        right_surface_to_camera_h: homographies.right_surface_to_camera_h,
        left_surface_to_screen_h: homographies.left_surface_to_screen_h,
        right_surface_to_screen_h: homographies.right_surface_to_screen_h,
        left_screen_to_camera_h: homographies.left_screen_to_camera_h,
        right_screen_to_camera_h: homographies.right_screen_to_camera_h,
        left_screen_to_surface_h: homographies.left_screen_to_surface_h,
        right_screen_to_surface_h: homographies.right_screen_to_surface_h,
        projection_homography_ready: true,
        runtime_xr_view_state_ready: true,
        openxr_contract: XrProjectionContract::from_views(views),
    })
}

#[cfg(target_os = "android")]
fn preview_surface_corners(
    tracking: TrackingBasis,
    views: XrDisplayViews,
    aspect: f32,
) -> Option<[Vec3; 4]> {
    let mut surface = head_anchored_preview_surface_corners(
        tracking,
        views.projection_preview_fov_y_degrees,
        views.projection_depth_meters,
        aspect,
        views.projection_raw_overscan,
    )
    .ok()?;
    let offset = tracking.up * views.projection_preview_offset_y_meters.clamp(-2.0, 2.0);
    for corner in &mut surface {
        *corner = *corner + offset;
    }
    Some(surface)
}

#[cfg(target_os = "android")]
pub fn broker_synthetic_projection_plan_from_xr_views(
    left_camera_id: &str,
    right_camera_id: &str,
    width: u32,
    height: u32,
    views: XrDisplayViews,
) -> Option<StereoProjectionPlan> {
    if width == 0 || height == 0 {
        return None;
    }
    let tracking = tracking_basis_from_xr_views(views)?;
    let aspect = projection_surface_aspect(width, height);
    let surface = preview_surface_corners(tracking, views, aspect)?;
    let intrinsics =
        synthetic_broker_intrinsics(width, height, views.projection_preview_fov_y_degrees)?;
    let camera_basis = CameraBasis::new(
        tracking.origin,
        tracking.right,
        tracking.up,
        tracking.forward,
    )?;
    let surface_to_camera =
        surface_to_camera_uv_homography(surface, camera_basis, intrinsics).ok()?;
    let left_eye_basis = eye_basis_from_xr_view(views.left)?;
    let right_eye_basis = eye_basis_from_xr_view(views.right)?;
    let left_surface_to_screen = surface_to_eye_screen_uv_homography(
        surface,
        left_eye_basis,
        views.left.angle_left.tan(),
        views.left.angle_right.tan(),
        views.left.angle_down.tan(),
        views.left.angle_up.tan(),
    )
    .ok()?;
    let right_surface_to_screen = surface_to_eye_screen_uv_homography(
        surface,
        right_eye_basis,
        views.right.angle_left.tan(),
        views.right.angle_right.tan(),
        views.right.angle_down.tan(),
        views.right.angle_up.tan(),
    )
    .ok()?;
    let left_screen_to_surface_h = invert_homography(left_surface_to_screen)?;
    let right_screen_to_surface_h = invert_homography(right_surface_to_screen)?;
    let left_screen_to_camera_h =
        screen_to_camera_uv_homography(left_surface_to_screen, surface_to_camera).ok()?;
    let right_screen_to_camera_h =
        screen_to_camera_uv_homography(right_surface_to_screen, surface_to_camera).ok()?;

    Some(StereoProjectionPlan {
        left_source_index: 0,
        right_source_index: 1,
        left_camera_id: left_camera_id.to_string(),
        right_camera_id: right_camera_id.to_string(),
        left_facing: "synthetic",
        right_facing: "synthetic",
        width,
        height,
        projection_metadata_ready: true,
        pose_source: "estimated-profile",
        source_eye_mapping: "left-right",
        coordinate_chain: "broker-synthetic-head-anchored-preview-to-openxr-view",
        fallback_reason: "none",
        left_surface_to_camera_h: surface_to_camera,
        right_surface_to_camera_h: surface_to_camera,
        left_surface_to_screen_h: left_surface_to_screen,
        right_surface_to_screen_h: right_surface_to_screen,
        left_screen_to_camera_h,
        right_screen_to_camera_h,
        left_screen_to_surface_h,
        right_screen_to_surface_h,
        projection_homography_ready: true,
        runtime_xr_view_state_ready: true,
        openxr_contract: XrProjectionContract::from_views(views),
    })
}

#[cfg(target_os = "android")]
pub fn broker_full_frame_projection_plan_from_xr_views(
    left_camera_id: &str,
    right_camera_id: &str,
    width: u32,
    height: u32,
    views: XrDisplayViews,
) -> Option<StereoProjectionPlan> {
    if width == 0 || height == 0 {
        return None;
    }
    let tracking = tracking_basis_from_xr_views(views)?;
    let aspect = projection_surface_aspect(width, height);
    let surface = preview_surface_corners(tracking, views, aspect)?;
    let left_eye_basis = eye_basis_from_xr_view(views.left)?;
    let right_eye_basis = eye_basis_from_xr_view(views.right)?;
    let left_surface_to_screen = surface_to_eye_screen_uv_homography(
        surface,
        left_eye_basis,
        views.left.angle_left.tan(),
        views.left.angle_right.tan(),
        views.left.angle_down.tan(),
        views.left.angle_up.tan(),
    )
    .ok()?;
    let right_surface_to_screen = surface_to_eye_screen_uv_homography(
        surface,
        right_eye_basis,
        views.right.angle_left.tan(),
        views.right.angle_right.tan(),
        views.right.angle_down.tan(),
        views.right.angle_up.tan(),
    )
    .ok()?;
    let left_screen_to_surface_h = invert_homography(left_surface_to_screen)?;
    let right_screen_to_surface_h = invert_homography(right_surface_to_screen)?;

    Some(StereoProjectionPlan {
        left_source_index: 0,
        right_source_index: 1,
        left_camera_id: left_camera_id.to_string(),
        right_camera_id: right_camera_id.to_string(),
        left_facing: "synthetic",
        right_facing: "synthetic",
        width,
        height,
        projection_metadata_ready: true,
        pose_source: "projection-surface",
        source_eye_mapping: "left-right",
        coordinate_chain: "broker-synthetic-full-frame-projection-surface-to-openxr-view",
        fallback_reason: "none",
        left_surface_to_camera_h: IDENTITY_HOMOGRAPHY,
        right_surface_to_camera_h: IDENTITY_HOMOGRAPHY,
        left_surface_to_screen_h: left_surface_to_screen,
        right_surface_to_screen_h: right_surface_to_screen,
        left_screen_to_camera_h: left_screen_to_surface_h,
        right_screen_to_camera_h: right_screen_to_surface_h,
        left_screen_to_surface_h,
        right_screen_to_surface_h,
        projection_homography_ready: true,
        runtime_xr_view_state_ready: true,
        openxr_contract: XrProjectionContract::from_views(views),
    })
}

#[cfg(target_os = "android")]
fn synthetic_broker_intrinsics(
    width: u32,
    height: u32,
    preview_fov_y_degrees: f32,
) -> Option<CameraIntrinsics> {
    let width_f = width as f32;
    let height_f = height as f32;
    if width_f <= 0.0 || height_f <= 0.0 {
        return None;
    }
    let focal = height_f / (2.0 * (preview_fov_y_degrees.to_radians() * 0.5).tan());
    let intrinsics = CameraIntrinsics::new(
        Vec2::new(focal, focal),
        Vec2::new(width_f * 0.5, height_f * 0.5),
        ImageSize::new(width, height),
    );
    intrinsics.is_valid().then_some(intrinsics)
}

#[cfg(target_os = "android")]
fn stereo_projection_homographies(
    left: &CameraSource,
    right: &CameraSource,
    delivered_width: u32,
    delivered_height: u32,
) -> Option<ProjectionHomographies> {
    let left_extrinsics =
        camera2_lens_pose_to_extrinsics(left.pose_translation?, left.pose_rotation?).ok()?;
    let right_extrinsics =
        camera2_lens_pose_to_extrinsics(right.pose_translation?, right.pose_rotation?).ok()?;
    let reference_center = (left_extrinsics.world_from_camera.position
        + right_extrinsics.world_from_camera.position)
        * 0.5;
    let tracking = TrackingBasis::new(Vec3::ZERO, Vec3::RIGHT, Vec3::UP, Vec3::FORWARD_NEG_Z)?;
    let surface = head_anchored_preview_surface_corners(
        tracking,
        PROJECTION_PREVIEW_FOV_Y_DEGREES,
        DEFAULT_PROJECTION_TARGET_DEPTH_METERS,
        PROJECTION_SOURCE_ASPECT,
        PROJECTION_RAW_OVERSCAN,
    )
    .ok()?;
    let left_intrinsics = scaled_intrinsics(left, delivered_width, delivered_height)?;
    let right_intrinsics = scaled_intrinsics(right, delivered_width, delivered_height)?;
    let left_basis = camera_basis_from_camera2_reference_pose_relative_to_center(
        tracking,
        left_extrinsics,
        reference_center,
    )
    .ok()?;
    let right_basis = camera_basis_from_camera2_reference_pose_relative_to_center(
        tracking,
        right_extrinsics,
        reference_center,
    )
    .ok()?;
    let left_h = surface_to_camera_uv_homography(surface, left_basis, left_intrinsics).ok()?;
    let right_h = surface_to_camera_uv_homography(surface, right_basis, right_intrinsics).ok()?;
    let (display_left_surface_to_camera_h, display_right_surface_to_camera_h) =
        display_mapped_surface_to_camera_homographies(left_h, right_h);
    let left_eye_basis = display_eye_basis(-DISPLAY_EYE_OFFSET_METERS)?;
    let right_eye_basis = display_eye_basis(DISPLAY_EYE_OFFSET_METERS)?;
    let tan_y = (DISPLAY_FOV_Y_DEGREES * 0.5).to_radians().tan();
    let tan_x = tan_y * DISPLAY_ASPECT.max(0.1);
    let left_surface_to_screen =
        surface_to_eye_screen_uv_homography(surface, left_eye_basis, -tan_x, tan_x, -tan_y, tan_y)
            .ok()?;
    let right_surface_to_screen =
        surface_to_eye_screen_uv_homography(surface, right_eye_basis, -tan_x, tan_x, -tan_y, tan_y)
            .ok()?;
    let left_screen_to_surface_h = invert_homography(left_surface_to_screen)?;
    let right_screen_to_surface_h = invert_homography(right_surface_to_screen)?;
    let left_screen_to_camera_h =
        screen_to_camera_uv_homography(left_surface_to_screen, display_left_surface_to_camera_h)
            .ok()?;
    let right_screen_to_camera_h =
        screen_to_camera_uv_homography(right_surface_to_screen, display_right_surface_to_camera_h)
            .ok()?;
    Some(ProjectionHomographies {
        left_surface_to_camera_h: display_left_surface_to_camera_h,
        right_surface_to_camera_h: display_right_surface_to_camera_h,
        left_surface_to_screen_h: left_surface_to_screen,
        right_surface_to_screen_h: right_surface_to_screen,
        left_screen_to_camera_h,
        right_screen_to_camera_h,
        left_screen_to_surface_h,
        right_screen_to_surface_h,
    })
}

#[cfg(target_os = "android")]
fn stereo_projection_homographies_from_xr_views(
    left: &CameraSource,
    right: &CameraSource,
    delivered_width: u32,
    delivered_height: u32,
    views: XrDisplayViews,
) -> Option<ProjectionHomographies> {
    let left_extrinsics =
        camera2_lens_pose_to_extrinsics(left.pose_translation?, left.pose_rotation?).ok()?;
    let right_extrinsics =
        camera2_lens_pose_to_extrinsics(right.pose_translation?, right.pose_rotation?).ok()?;
    let reference_center = (left_extrinsics.world_from_camera.position
        + right_extrinsics.world_from_camera.position)
        * 0.5;
    let tracking = tracking_basis_from_xr_views(views)?;
    let aspect = projection_surface_aspect(delivered_width, delivered_height);
    let surface = preview_surface_corners(tracking, views, aspect)?;
    let left_intrinsics = scaled_intrinsics(left, delivered_width, delivered_height)?;
    let right_intrinsics = scaled_intrinsics(right, delivered_width, delivered_height)?;
    let left_basis = camera_basis_from_camera2_reference_pose_relative_to_center(
        tracking,
        left_extrinsics,
        reference_center,
    )
    .ok()?;
    let right_basis = camera_basis_from_camera2_reference_pose_relative_to_center(
        tracking,
        right_extrinsics,
        reference_center,
    )
    .ok()?;
    let left_h = surface_to_camera_uv_homography(surface, left_basis, left_intrinsics).ok()?;
    let right_h = surface_to_camera_uv_homography(surface, right_basis, right_intrinsics).ok()?;
    let (display_left_surface_to_camera_h, display_right_surface_to_camera_h) =
        display_mapped_surface_to_camera_homographies(left_h, right_h);
    let left_eye_basis = eye_basis_from_xr_view(views.left)?;
    let right_eye_basis = eye_basis_from_xr_view(views.right)?;
    let left_surface_to_screen = surface_to_eye_screen_uv_homography(
        surface,
        left_eye_basis,
        views.left.angle_left.tan(),
        views.left.angle_right.tan(),
        views.left.angle_down.tan(),
        views.left.angle_up.tan(),
    )
    .ok()?;
    let right_surface_to_screen = surface_to_eye_screen_uv_homography(
        surface,
        right_eye_basis,
        views.right.angle_left.tan(),
        views.right.angle_right.tan(),
        views.right.angle_down.tan(),
        views.right.angle_up.tan(),
    )
    .ok()?;
    let left_screen_to_surface_h = invert_homography(left_surface_to_screen)?;
    let right_screen_to_surface_h = invert_homography(right_surface_to_screen)?;
    let left_screen_to_camera_h =
        screen_to_camera_uv_homography(left_surface_to_screen, display_left_surface_to_camera_h)
            .ok()?;
    let right_screen_to_camera_h =
        screen_to_camera_uv_homography(right_surface_to_screen, display_right_surface_to_camera_h)
            .ok()?;
    Some(ProjectionHomographies {
        left_surface_to_camera_h: display_left_surface_to_camera_h,
        right_surface_to_camera_h: display_right_surface_to_camera_h,
        left_surface_to_screen_h: left_surface_to_screen,
        right_surface_to_screen_h: right_surface_to_screen,
        left_screen_to_camera_h,
        right_screen_to_camera_h,
        left_screen_to_surface_h,
        right_screen_to_surface_h,
    })
}

#[cfg(target_os = "android")]
fn display_mapped_surface_to_camera_homographies(
    physical_left_h: [[f32; 3]; 3],
    physical_right_h: [[f32; 3]; 3],
) -> ([[f32; 3]; 3], [[f32; 3]; 3]) {
    // Homography rows are display-indexed. The display/source eye mapping is
    // applied only when selecting the source texture; remapping homographies
    // here double-swaps the cameras for the diagnostic inverted-source lane.
    (physical_left_h, physical_right_h)
}

#[cfg(target_os = "android")]
fn display_source_eye_mapping() -> &'static str {
    match option_env!("RUSTY_MAKEPAD_DISPLAY_SOURCE_EYE_MAPPING") {
        Some("display-left-from-left-source") => "display-left-from-left-source",
        Some("display-left-from-right-source") => "display-left-from-right-source",
        _ => DEFAULT_DISPLAY_SOURCE_EYE_MAPPING,
    }
}

#[cfg(target_os = "android")]
fn eye_basis_from_xr_view(view: XrDisplayEyeView) -> Option<CameraBasis> {
    if !view.valid {
        return None;
    }
    let orientation = Quat::new(
        view.orientation[0],
        view.orientation[1],
        view.orientation[2],
        view.orientation[3],
    )
    .normalized_or(Quat::IDENTITY);
    CameraBasis::new(
        Vec3::new(view.position[0], view.position[1], view.position[2]),
        orientation.rotate_vec3(Vec3::RIGHT),
        orientation.rotate_vec3(Vec3::UP),
        orientation.rotate_vec3(Vec3::FORWARD_NEG_Z),
    )
}

#[cfg(target_os = "android")]
fn tracking_basis_from_xr_views(views: XrDisplayViews) -> Option<TrackingBasis> {
    if !views.left.valid || !views.right.valid {
        return None;
    }
    let position = Vec3::new(
        (views.left.position[0] + views.right.position[0]) * 0.5,
        (views.left.position[1] + views.right.position[1]) * 0.5,
        (views.left.position[2] + views.right.position[2]) * 0.5,
    );
    let orientation = Quat::new(
        views.left.orientation[0],
        views.left.orientation[1],
        views.left.orientation[2],
        views.left.orientation[3],
    )
    .normalized_or(Quat::IDENTITY);
    TrackingBasis::new(
        position,
        orientation.rotate_vec3(Vec3::RIGHT),
        orientation.rotate_vec3(Vec3::UP),
        orientation.rotate_vec3(Vec3::FORWARD_NEG_Z),
    )
}

#[cfg(target_os = "android")]
fn projection_surface_aspect(width: u32, height: u32) -> f32 {
    if width == 0 || height == 0 {
        return PROJECTION_SOURCE_ASPECT;
    }
    ((width as f32) / (height as f32)).clamp(0.25, 4.0)
}

#[cfg(target_os = "android")]
fn fov_tangents(view: XrDisplayEyeView) -> [f32; 4] {
    [
        view.angle_left.tan(),
        view.angle_right.tan(),
        view.angle_up.tan(),
        view.angle_down.tan(),
    ]
}

#[cfg(target_os = "android")]
fn position_vec4(view: XrDisplayEyeView) -> [f32; 4] {
    [view.position[0], view.position[1], view.position[2], 1.0]
}

#[cfg(target_os = "android")]
fn orientation_vec4(view: XrDisplayEyeView) -> [f32; 4] {
    [
        view.orientation[0],
        view.orientation[1],
        view.orientation[2],
        view.orientation[3],
    ]
}

#[cfg(target_os = "android")]
fn display_eye_basis(x_offset_meters: f32) -> Option<CameraBasis> {
    CameraBasis::new(
        Vec3::new(x_offset_meters, 0.0, 0.0),
        Vec3::RIGHT,
        Vec3::UP,
        Vec3::FORWARD_NEG_Z,
    )
}

#[cfg(target_os = "android")]
fn scaled_intrinsics(
    source: &CameraSource,
    delivered_width: u32,
    delivered_height: u32,
) -> Option<CameraIntrinsics> {
    let intrinsics = source.intrinsics?;
    let source_size = source
        .active_array_size
        .unwrap_or((delivered_width, delivered_height));
    let source_intrinsics = CameraIntrinsics::new(
        Vec2::new(intrinsics.fx, intrinsics.fy),
        Vec2::new(intrinsics.cx, intrinsics.cy),
        ImageSize::new(source_size.0, source_size.1),
    )
    .with_skew_px(intrinsics.skew);
    scale_intrinsics_to_image(
        source_intrinsics,
        ImageSize::new(source_size.0, source_size.1),
        ImageSize::new(delivered_width, delivered_height),
    )
    .ok()
}

#[derive(Clone)]
pub(crate) struct MakepadOpenXrProjectionContract {
    reference_space: String,
    openxr_reference_space: String,
    display_time_source: String,
    predicted_display_time_ns: Option<i64>,
    view_pose_fov_source: String,
    projection_depth_meters: Option<f32>,
    projection_preview_fov_y_degrees: Option<f32>,
    projection_preview_offset_y_meters: Option<f32>,
    projection_raw_overscan: Option<f32>,
    left_render_fov_tangents: Option<[f32; 4]>,
    right_render_fov_tangents: Option<[f32; 4]>,
    left_render_position: Option<[f32; 4]>,
    right_render_position: Option<[f32; 4]>,
    left_render_orientation: Option<[f32; 4]>,
    right_render_orientation: Option<[f32; 4]>,
}

impl MakepadOpenXrProjectionContract {
    pub(crate) fn missing() -> Self {
        Self {
            reference_space: "not-logged".to_string(),
            openxr_reference_space: "not-logged".to_string(),
            display_time_source: "not-logged".to_string(),
            predicted_display_time_ns: None,
            view_pose_fov_source: "not-logged".to_string(),
            projection_depth_meters: None,
            projection_preview_fov_y_degrees: None,
            projection_preview_offset_y_meters: None,
            projection_raw_overscan: None,
            left_render_fov_tangents: None,
            right_render_fov_tangents: None,
            left_render_position: None,
            right_render_position: None,
            left_render_orientation: None,
            right_render_orientation: None,
        }
    }

    #[cfg(target_os = "android")]
    pub(crate) fn from_android(contract: XrProjectionContract) -> Self {
        Self {
            reference_space: contract.reference_space.to_string(),
            openxr_reference_space: contract.openxr_reference_space.to_string(),
            display_time_source: contract.display_time_source.to_string(),
            predicted_display_time_ns: contract.predicted_display_time_ns,
            view_pose_fov_source: contract.view_pose_fov_source.to_string(),
            projection_depth_meters: contract.projection_depth_meters,
            projection_preview_fov_y_degrees: contract.projection_preview_fov_y_degrees,
            projection_preview_offset_y_meters: contract.projection_preview_offset_y_meters,
            projection_raw_overscan: contract.projection_raw_overscan,
            left_render_fov_tangents: contract.left_render_fov_tangents,
            right_render_fov_tangents: contract.right_render_fov_tangents,
            left_render_position: contract.left_render_position,
            right_render_position: contract.right_render_position,
            left_render_orientation: contract.left_render_orientation,
            right_render_orientation: contract.right_render_orientation,
        }
    }
}
