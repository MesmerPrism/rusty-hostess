//! Hostess-local camera metadata and projection helpers.
//!
//! This module is the compatibility facade for public, app-neutral camera
//! math. Child modules own source selection, projection footprint/layout,
//! camera basis/projection, homography smoothing, and timestamp matching.
//! Existing `rusty.xr.*` schema identifiers below are explicit
//! `LEGACY_RUSTY_XR_*` serialized compatibility values; the active module name
//! is Hostess-local until the contracts move to their Morphospace owner crates.
//!
//! Enable the `serde` feature to serialize helper result types; camera metadata
//! serialization is forwarded through `hostess-contracts/serde`.
//!
//! ```
//! use crate::hostess_camera_model::{project_camera_point, CameraIntrinsics, ImageSize, Vec2, Vec3};
//!
//! let intrinsics = CameraIntrinsics::new(
//!     Vec2::new(500.0, 500.0),
//!     Vec2::new(320.0, 240.0),
//!     ImageSize::new(640, 480),
//! );
//! let pixel = project_camera_point(intrinsics, Vec3::new(0.0, 0.0, 1.0)).unwrap();
//! assert_eq!(pixel, Vec2::new(320.0, 240.0));
//! ```

use core::fmt;

pub use crate::hostess_contracts::{
    CameraCompositeTier, CameraExtrinsics, CameraFrameAdoptionMode, CameraFrameMetadata,
    CameraFrameMetadataFlags, CameraFrameTiming, CameraGpuBufferDescriptor, CameraImageRotation,
    CameraIntrinsics, CameraPixelDomain, CameraPixelDomainKind, CameraProjectionState,
    CameraProjectionStatus, CameraSourceId, CameraTextureTransform, ColorRgba, Eye, ImageSize,
    Pose, ProjectionTargetState, Quat, Rect2, StereoCameraFrameMetadata, StereoCameraFramePair,
    StereoMediaLayout, TemporalProjectionEdgeMode, TemporalProjectionMetrics,
    TemporalProjectionMode, TemporalProjectionPolicy, Vec2, Vec3, VisualProjectionState,
};

/// Crate version exposed for lightweight smoke checks.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Legacy schema id for metadata-authored screen target footprints.
pub const LEGACY_RUSTY_XR_TARGET_SCREEN_FOOTPRINT_SCHEMA: &str =
    "rusty.xr.target_screen_footprint.v1";

/// Legacy schema id for diagnostic region colors used by projection lanes.
pub const LEGACY_RUSTY_XR_TARGET_FOOTPRINT_DEBUG_REGION_COLORS_SCHEMA: &str =
    "rusty.xr.target_footprint_debug_region_colors.v1";

/// Legacy schema id for source-to-target sampling mode carried by stream metadata.
pub const LEGACY_RUSTY_XR_SOURCE_SAMPLING_MODE_SCHEMA: &str = "rusty.xr.source_sampling_mode.v1";

/// Source raster is placed in the metadata-authored target footprint as local 0..1 UV.
pub const SOURCE_SAMPLING_MODE_TARGET_LOCAL_RASTER: &str = "target-local-raster";

/// Display-eye screen UV is mapped to source UV through calibrated camera homography.
pub const SOURCE_SAMPLING_MODE_SCREEN_TO_CAMERA_HOMOGRAPHY: &str = "screen-to-camera-homography";

/// Public source-sampling modes understood by renderer lanes.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum SourceSamplingMode {
    #[default]
    TargetLocalRaster,
    ScreenToCameraHomography,
}

impl SourceSamplingMode {
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().replace('_', "-").as_str() {
            "target-local-raster"
            | "target-local"
            | "target-raster"
            | "local-raster"
            | "raster"
            | "default" => Some(Self::TargetLocalRaster),
            "screen-to-camera-homography"
            | "screen-camera-homography"
            | "screen-to-source-homography"
            | "camera-homography"
            | "camera-projection"
            | "homography" => Some(Self::ScreenToCameraHomography),
            _ => None,
        }
    }

    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::TargetLocalRaster => SOURCE_SAMPLING_MODE_TARGET_LOCAL_RASTER,
            Self::ScreenToCameraHomography => SOURCE_SAMPLING_MODE_SCREEN_TO_CAMERA_HOMOGRAPHY,
        }
    }

    pub const fn uses_target_local_raster(self) -> bool {
        matches!(self, Self::TargetLocalRaster)
    }

    pub const fn uses_screen_to_camera_homography(self) -> bool {
        matches!(self, Self::ScreenToCameraHomography)
    }
}

/// Camera model helper error.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CameraModelError {
    InvalidSourceIntrinsics,
    InvalidSourceSize,
    InvalidTargetSize,
    InvalidPoseTranslation,
    InvalidPoseRotation,
    InvalidTrackingBasis,
    InvalidProjectionSurface,
    PointBehindCamera,
    ZeroDepth,
}

impl fmt::Display for CameraModelError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidSourceIntrinsics => f.write_str("invalid source intrinsics"),
            Self::InvalidSourceSize => f.write_str("invalid source image size"),
            Self::InvalidTargetSize => f.write_str("invalid target image size"),
            Self::InvalidPoseTranslation => f.write_str("invalid pose translation"),
            Self::InvalidPoseRotation => f.write_str("invalid pose rotation"),
            Self::InvalidTrackingBasis => f.write_str("invalid tracking basis"),
            Self::InvalidProjectionSurface => f.write_str("invalid projection surface"),
            Self::PointBehindCamera => f.write_str("point is behind the camera"),
            Self::ZeroDepth => f.write_str("depth must be non-zero"),
        }
    }
}

impl std::error::Error for CameraModelError {}

mod camera_basis;
mod homography;
mod projection_footprint;
mod source_selection;
mod timestamp_matching;

pub use camera_basis::*;
pub use homography::*;
pub use projection_footprint::*;
pub use source_selection::*;
pub use timestamp_matching::*;
#[cfg(test)]
mod tests {
    use super::*;

    fn test_intrinsics() -> CameraIntrinsics {
        CameraIntrinsics::new(
            Vec2::new(1000.0, 900.0),
            Vec2::new(500.0, 400.0),
            ImageSize::new(1000, 800),
        )
    }

    fn centered_square_intrinsics() -> CameraIntrinsics {
        CameraIntrinsics::new(
            Vec2::new(900.0, 900.0),
            Vec2::new(640.0, 640.0),
            ImageSize::new(1280, 1280),
        )
    }

    fn fov_matched_square_intrinsics() -> CameraIntrinsics {
        CameraIntrinsics::new(
            Vec2::new(640.0, 640.0),
            Vec2::new(640.0, 640.0),
            ImageSize::new(1280, 1280),
        )
    }

    fn tracking_basis() -> TrackingBasis {
        TrackingBasis::new(Vec3::ZERO, Vec3::RIGHT, Vec3::UP, Vec3::FORWARD_NEG_Z)
            .expect("test tracking basis is valid")
    }

    fn camera_for_tracking_basis(tracking: TrackingBasis, right_offset: f32) -> CameraBasis {
        CameraBasis::new(
            tracking.origin + tracking.right * right_offset,
            tracking.right,
            tracking.up,
            tracking.forward,
        )
        .expect("test camera basis is valid")
    }

    fn apply_homography(rows: [[f32; 3]; 3], uv: Vec2) -> Vec2 {
        let w = rows[2][0] * uv.x + rows[2][1] * uv.y + rows[2][2];
        Vec2::new(
            (rows[0][0] * uv.x + rows[0][1] * uv.y + rows[0][2]) / w,
            (rows[1][0] * uv.x + rows[1][1] * uv.y + rows[1][2]) / w,
        )
    }

    fn translated_uv_homography(dx: f32, dy: f32) -> [[f32; 3]; 3] {
        [[1.0, 0.0, dx], [0.0, 1.0, dy], [0.0, 0.0, 1.0]]
    }

    #[test]
    fn exposes_workspace_version() {
        assert_eq!(VERSION, "0.1.0");
    }

    #[test]
    fn applies_uv_homography_and_rejects_singular_rows() {
        let translated = translated_uv_homography(0.125, -0.25);
        let projected =
            apply_uv_homography(translated, Vec2::new(0.5, 0.75)).expect("uv should project");
        assert_eq!(projected, Vec2::new(0.625, 0.5));

        assert_eq!(
            apply_uv_homography(
                [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]],
                Vec2::ONE
            ),
            None
        );
    }

    #[test]
    fn stereo_homography_metrics_reports_motion_and_invalid_uvs() {
        let previous = StereoHomographyProjection::new(
            translated_uv_homography(0.0, 0.0),
            translated_uv_homography(0.0, 0.0),
        );
        let current = StereoHomographyProjection::new(
            translated_uv_homography(0.01, 0.0),
            translated_uv_homography(0.01, 0.0),
        );
        let metrics = stereo_homography_projection_metrics(
            Some(previous),
            current,
            ImageSize::new(1000, 500),
        );

        assert_eq!(metrics.sample_count, 50);
        assert_eq!(metrics.invalid_uv_sample_count, 0);
        assert!((metrics.average_motion_px - 10.0).abs() < 0.001);
        assert!((metrics.p95_motion_px - 10.0).abs() < 0.001);

        let edge_shifted = StereoHomographyProjection::new(
            translated_uv_homography(0.2, 0.0),
            translated_uv_homography(0.2, 0.0),
        );
        let first_frame_metrics =
            stereo_homography_projection_metrics(None, edge_shifted, ImageSize::new(1000, 500));
        assert_eq!(first_frame_metrics.average_motion_px, 0.0);
        assert_eq!(first_frame_metrics.p95_motion_px, 0.0);
        assert_eq!(first_frame_metrics.invalid_uv_sample_count, 10);
        assert!((first_frame_metrics.invalid_uv_percent - 20.0).abs() < 0.001);
    }

    #[test]
    fn screen_motion_clamp_limits_applied_projection_motion() {
        let previous = StereoHomographyProjection::new(
            translated_uv_homography(0.0, 0.0),
            translated_uv_homography(0.0, 0.0),
        );
        let target = StereoHomographyProjection::new(
            translated_uv_homography(0.20, 0.0),
            translated_uv_homography(0.20, 0.0),
        );

        let clamped = clamp_stereo_homography_screen_motion(
            Some(previous),
            target,
            ImageSize::new(1000, 500),
            25.0,
        );

        assert!(clamped.clamped);
        assert!((clamped.target_motion.p95_motion_px - 200.0).abs() < 0.001);
        assert!(clamped.applied_motion.p95_motion_px <= 25.001);
        assert!((clamped.projection.left_screen_to_camera[0][2] - 0.025).abs() < 0.001);
        assert!((clamped.projection.right_screen_to_camera[0][2] - 0.025).abs() < 0.001);
        assert!(clamped.residual_motion.p95_motion_px > 170.0);

        let unclamped = clamp_stereo_homography_screen_motion(
            Some(previous),
            target,
            ImageSize::new(1000, 500),
            250.0,
        );

        assert!(!unclamped.clamped);
        assert_eq!(unclamped.projection, target);
        assert_eq!(unclamped.residual_motion.p95_motion_px, 0.0);
    }

    #[test]
    fn pose_delta_clamp_uses_shared_stereo_coefficient() {
        let previous = StereoHomographyProjection::new(
            translated_uv_homography(0.0, 0.0),
            translated_uv_homography(0.0, 0.0),
        );
        let target = StereoHomographyProjection::new(
            translated_uv_homography(0.20, 0.0),
            translated_uv_homography(0.10, 0.0),
        );
        let previous_pose = Pose::IDENTITY;
        let target_pose = Pose::new(
            Vec3::new(0.0, 0.0, 0.20),
            Quat::from_axis_angle(Vec3::UP, 10.0_f32.to_radians()),
        );

        let clamped = clamp_stereo_homography_pose_delta(
            Some(previous),
            target,
            Some(previous_pose),
            target_pose,
            ImageSize::new(1000, 500),
            2.5,
            0.20,
        );

        assert!(clamped.clamped);
        assert!((clamped.alpha - 0.25).abs() < 0.001);
        assert!((clamped.angular_delta_deg - 10.0).abs() < 0.001);
        assert!((clamped.projection.left_screen_to_camera[0][2] - 0.05).abs() < 0.001);
        assert!((clamped.projection.right_screen_to_camera[0][2] - 0.025).abs() < 0.001);
        assert!(clamped.residual_motion.p95_motion_px > 70.0);

        let unclamped = clamp_stereo_homography_pose_delta(
            Some(previous),
            target,
            Some(previous_pose),
            target_pose,
            ImageSize::new(1000, 500),
            12.0,
            0.30,
        );

        assert!(!unclamped.clamped);
        assert_eq!(unclamped.projection, target);
        assert_eq!(unclamped.residual_motion.p95_motion_px, 0.0);
    }

    #[test]
    fn scales_intrinsics_between_pixel_domains() {
        let scaled = scale_intrinsics_to_image(
            test_intrinsics(),
            ImageSize::new(1000, 800),
            ImageSize::new(500, 400),
        )
        .expect("intrinsics should scale");

        assert_eq!(scaled.focal_length_px, Vec2::new(500.0, 450.0));
        assert_eq!(scaled.principal_point_px, Vec2::new(250.0, 200.0));
        assert_eq!(scaled.image_size, ImageSize::new(500, 400));
    }

    #[test]
    fn scales_intrinsics_from_active_array_to_delivered_image() {
        let source = CameraIntrinsics::new(
            Vec2::new(2200.0, 2000.0),
            Vec2::new(1100.0, 1000.0),
            ImageSize::new(2200, 2000),
        )
        .with_skew_px(4.0);

        let scaled = scale_intrinsics_to_image(
            source,
            ImageSize::new(2200, 2000),
            ImageSize::new(1100, 1000),
        )
        .expect("active-array intrinsics should scale to delivered image");

        assert_eq!(scaled.focal_length_px, Vec2::new(1100.0, 1000.0));
        assert_eq!(scaled.principal_point_px, Vec2::new(550.0, 500.0));
        assert_eq!(scaled.skew_px, 2.0);
        assert_eq!(scaled.image_size, ImageSize::new(1100, 1000));
    }

    #[test]
    fn scores_preferred_quest_camera_candidate() {
        let policy = CameraSourceSelectionPolicy::default();
        let preferred = CameraSourceCandidate::new(ImageSize::new(1280, 1280))
            .with_stereo(true)
            .with_preferred_device_rank(2)
            .with_frame_rate_millihz(60_000);
        let off_square = CameraSourceCandidate::new(ImageSize::new(1920, 1080))
            .with_preferred_device_rank(2)
            .with_frame_rate_millihz(90_000);

        assert!(
            score_camera_source_candidate(preferred, policy)
                > score_camera_source_candidate(off_square, policy)
        );
        assert_eq!(
            score_camera_source_candidate(
                CameraSourceCandidate::new(ImageSize::new(0, 1280)),
                policy
            ),
            None
        );
    }

    #[test]
    fn computes_delivered_eye_stream_size() {
        assert_eq!(
            delivered_eye_stream_size(ImageSize::new(1280, 720), StereoMediaLayout::Mono),
            Some(ImageSize::new(1280, 720))
        );
        assert_eq!(
            delivered_eye_stream_size(ImageSize::new(1280, 720), StereoMediaLayout::Separate),
            Some(ImageSize::new(1280, 720))
        );
        assert_eq!(
            delivered_eye_stream_size(
                ImageSize::new(2560, 1280),
                StereoMediaLayout::SIDE_BY_SIDE_LEFT_FIRST
            ),
            Some(ImageSize::new(1280, 1280))
        );
        assert_eq!(
            delivered_eye_stream_size(
                ImageSize::new(1280, 960),
                StereoMediaLayout::TOP_BOTTOM_LEFT_FIRST
            ),
            Some(ImageSize::new(1280, 480))
        );
        assert_eq!(
            delivered_eye_stream_size(
                ImageSize::new(1, 1280),
                StereoMediaLayout::SideBySide { left_first: true }
            ),
            None
        );
    }

    #[test]
    fn centered_fill_window_preserves_target_aspect_and_overscan() {
        let window =
            centered_fill_source_window(ImageSize::new(1280, 1280), ImageSize::new(16, 9), 1.0)
                .expect("window should fit");

        assert_eq!(window.origin_px, Vec2::new(0.0, 280.0));
        assert_eq!(window.size_px, Vec2::new(1280.0, 720.0));

        let overscanned =
            centered_fill_source_window(ImageSize::new(1280, 1280), ImageSize::new(16, 9), 2.0)
                .expect("overscanned window should fit");

        assert_eq!(overscanned.origin_px, Vec2::new(320.0, 460.0));
        assert_eq!(overscanned.size_px, Vec2::new(640.0, 360.0));
    }

    #[test]
    fn video_projection_behavior_is_explicit_not_provenance_driven() {
        let behavior = VideoProjectionBehavior::full_source(
            VideoProjectionMapping::ScreenToSourceHomography,
            1.0,
        );
        let direct = VideoFeedDescriptor::new(
            "left",
            ImageSize::new(1280, 1280),
            ImageSize::new(1280, 1280),
            VideoSourceProvenance::new("live-camera", "direct-api", "platform-adapter"),
            behavior,
        );
        let broker = VideoFeedDescriptor::new(
            "left",
            ImageSize::new(1280, 1280),
            ImageSize::new(1280, 1280),
            VideoSourceProvenance::new("live-camera", "broker-stream", "remote-adapter"),
            behavior,
        );

        assert!(direct.is_valid());
        assert!(broker.is_valid());
        assert_eq!(direct.behavior, broker.behavior);
        assert_ne!(
            direct.provenance.transport_kind,
            broker.provenance.transport_kind
        );
    }

    #[test]
    fn source_valid_footprint_uses_explicit_source_rect() {
        let identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]];
        let full = source_valid_screen_uv_footprint(identity, Rect2::UNIT, 8);
        let inset = source_valid_screen_uv_footprint(
            identity,
            Rect2::new(Vec2::new(0.25, 0.25), Vec2::new(0.5, 0.5)),
            8,
        );

        assert_eq!(full.bbox_xywh(), [0.0, 0.0, 1.0, 1.0]);
        assert_eq!(inset.bbox_xywh(), [0.25, 0.25, 0.5, 0.5]);
        assert!(full.active_fraction > inset.active_fraction);
    }

    #[test]
    fn projection_border_layout_is_surface_minus_feed() {
        let layout = projection_border_layout(
            Rect2::UNIT,
            Rect2::new(Vec2::new(0.2, 0.3), Vec2::new(0.6, 0.4)),
            ProjectionBorderDescriptor::new(
                ProjectionBorderFillPolicy::PassthroughUnderlay,
                ColorRgba::new(0.0, 0.0, 0.0, 0.0),
                0.0,
            ),
        )
        .expect("border should layout");

        assert!(layout.is_valid());
        assert_eq!(layout.top.size.y, 0.3);
        assert!((layout.bottom.origin.y - 0.7).abs() < 1.0e-6);
        assert_eq!(layout.left.size.x, 0.2);
        assert_eq!(layout.right.origin.x, 0.8);
        assert_eq!(
            layout.descriptor.fill_policy,
            ProjectionBorderFillPolicy::PassthroughUnderlay
        );
    }

    #[test]
    fn edge_fade_reaches_full_alpha_after_configured_width() {
        assert_eq!(edge_fade_alpha(Vec2::new(0.0, 0.5), 0.06), 0.0);
        assert_eq!(edge_fade_alpha(Vec2::new(0.06, 0.5), 0.06), 1.0);
        assert_eq!(edge_fade_alpha(Vec2::new(0.5, 0.5), 0.0), 1.0);
    }

    #[test]
    fn projection_round_trips_camera_point() {
        let intrinsics = test_intrinsics();
        let camera_point = Vec3::new(0.1, -0.2, 2.0);
        let pixel = project_camera_point(intrinsics, camera_point).expect("point should project");
        let round_trip =
            back_project_pixel(intrinsics, pixel, camera_point.z).expect("pixel should unproject");

        assert!((round_trip.x - camera_point.x).abs() < 1.0e-5);
        assert!((round_trip.y - camera_point.y).abs() < 1.0e-5);
        assert!((round_trip.z - camera_point.z).abs() < 1.0e-5);
    }

    #[test]
    fn camera2_lens_pose_conversion_normalizes_quaternion() {
        let extrinsics = camera2_lens_pose_to_extrinsics([0.03, -0.01, 0.02], [0.0, 0.0, 0.0, 2.0])
            .expect("finite Camera2 pose should convert");

        assert_eq!(
            extrinsics.world_from_camera.position,
            Vec3::new(0.03, -0.01, 0.02)
        );
        assert!((extrinsics.world_from_camera.orientation.w - 1.0).abs() < 1.0e-6);
        assert!(extrinsics.is_valid());
    }

    #[test]
    fn camera2_lens_pose_conversion_stores_world_from_camera_orientation() {
        let s = core::f32::consts::FRAC_1_SQRT_2;
        let extrinsics = camera2_lens_pose_to_extrinsics([0.0, 0.0, 0.0], [0.0, 0.0, s, s])
            .expect("finite Camera2 pose should convert");

        assert!((extrinsics.world_from_camera.orientation.z + s).abs() < 1.0e-6);
        assert!((extrinsics.world_from_camera.orientation.w - s).abs() < 1.0e-6);
    }

    #[test]
    fn camera2_lens_pose_conversion_rejects_missing_or_invalid_pose_values() {
        assert_eq!(
            camera2_lens_pose_to_extrinsics([f32::NAN, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]),
            Err(CameraModelError::InvalidPoseTranslation)
        );
        assert_eq!(
            camera2_lens_pose_to_extrinsics([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]),
            Err(CameraModelError::InvalidPoseRotation)
        );
    }

    #[test]
    fn android_sensor_vectors_resolve_through_head_basis() {
        let tracking = tracking_basis();

        assert_eq!(
            android_sensor_vector_to_tracking(tracking, Vec3::RIGHT),
            Vec3::RIGHT
        );
        assert_eq!(
            android_sensor_vector_to_tracking(tracking, Vec3::UP),
            Vec3::UP
        );
        assert_eq!(
            android_sensor_vector_to_tracking(tracking, Vec3::new(0.0, 0.0, 1.0)),
            Vec3::new(0.0, 0.0, 1.0)
        );
    }

    #[test]
    fn camera2_reference_pose_builds_tracking_camera_basis() {
        let tracking = tracking_basis();
        let extrinsics = camera2_lens_pose_to_extrinsics([0.03, 0.01, -0.02], [0.0, 0.0, 0.0, 1.0])
            .expect("pose should convert");
        let basis = camera_basis_from_camera2_reference_pose(tracking, extrinsics)
            .expect("basis should resolve");

        assert!((basis.position.x - 0.03).abs() < 1.0e-6);
        assert!((basis.position.y - 0.01).abs() < 1.0e-6);
        assert!((basis.position.z + 0.02).abs() < 1.0e-6);
        assert_eq!(basis.right, Vec3::RIGHT);
        assert_eq!(basis.up, Vec3::UP);
        assert_eq!(basis.forward, Vec3::new(0.0, 0.0, 1.0));
    }

    #[test]
    fn camera2_reference_pose_can_be_centered_on_stereo_rig() {
        let tracking = tracking_basis();
        let left = camera2_lens_pose_to_extrinsics([-0.03, -0.01, -0.07], [0.0, 0.0, 0.0, 1.0])
            .expect("left pose should convert");
        let right = camera2_lens_pose_to_extrinsics([0.03, -0.01, -0.07], [0.0, 0.0, 0.0, 1.0])
            .expect("right pose should convert");
        let center = (left.world_from_camera.position + right.world_from_camera.position) * 0.5;

        let left_basis =
            camera_basis_from_camera2_reference_pose_relative_to_center(tracking, left, center)
                .expect("left centered basis should resolve");
        let right_basis =
            camera_basis_from_camera2_reference_pose_relative_to_center(tracking, right, center)
                .expect("right centered basis should resolve");

        assert!((left_basis.position.x + 0.03).abs() < 1.0e-6);
        assert!((right_basis.position.x - 0.03).abs() < 1.0e-6);
        assert!(left_basis.position.y.abs() < 1.0e-6);
        assert!(right_basis.position.y.abs() < 1.0e-6);
        assert!(left_basis.position.z.abs() < 1.0e-6);
        assert!(right_basis.position.z.abs() < 1.0e-6);
    }

    #[test]
    fn stereo_baseline_shifts_projected_uv_in_expected_direction() {
        let tracking = tracking_basis();
        let intrinsics = centered_square_intrinsics();
        let surface = head_anchored_preview_surface_corners(tracking, 60.0, 1.0, 1.0, 1.0)
            .expect("surface should resolve");
        let left_camera = camera_for_tracking_basis(tracking, -0.03);
        let right_camera = camera_for_tracking_basis(tracking, 0.03);
        let left_rows = surface_to_camera_uv_homography(surface, left_camera, intrinsics)
            .expect("left projection should resolve");
        let right_rows = surface_to_camera_uv_homography(surface, right_camera, intrinsics)
            .expect("right projection should resolve");

        let left_center = apply_homography(left_rows, Vec2::new(0.5, 0.5));
        let right_center = apply_homography(right_rows, Vec2::new(0.5, 0.5));

        assert!(left_center.x > 0.5);
        assert!(right_center.x < 0.5);
        assert!(left_center.x > right_center.x);
    }

    #[test]
    fn horizontal_mirror_reverses_stereo_baseline_signal() {
        let tracking = tracking_basis();
        let intrinsics = centered_square_intrinsics();
        let surface = head_anchored_preview_surface_corners(tracking, 60.0, 1.0, 1.0, 1.0)
            .expect("surface should resolve");
        let left_rows = surface_to_camera_uv_homography(
            surface,
            camera_for_tracking_basis(tracking, -0.03),
            intrinsics,
        )
        .expect("left projection should resolve");
        let right_rows = surface_to_camera_uv_homography(
            surface,
            camera_for_tracking_basis(tracking, 0.03),
            intrinsics,
        )
        .expect("right projection should resolve");
        let mirror = CameraTextureTransform::new("test", "mirror check").with_flip_x(true);

        let mirrored_left = mirror.apply_uv(apply_homography(left_rows, Vec2::new(0.5, 0.5)));
        let mirrored_right = mirror.apply_uv(apply_homography(right_rows, Vec2::new(0.5, 0.5)));

        assert!(mirrored_left.x < mirrored_right.x);
    }

    #[test]
    fn rotate_180_does_not_preserve_source_eye_mapping_signal() {
        let tracking = tracking_basis();
        let intrinsics = centered_square_intrinsics();
        let surface = head_anchored_preview_surface_corners(tracking, 60.0, 1.0, 1.0, 1.0)
            .expect("surface should resolve");
        let rows = surface_to_camera_uv_homography(
            surface,
            camera_for_tracking_basis(tracking, -0.03),
            intrinsics,
        )
        .expect("projection should resolve");
        let rotate180 = CameraTextureTransform::new("test", "rotation check")
            .with_rotation(CameraImageRotation::Rotate180);

        let unrotated = apply_homography(rows, Vec2::new(0.25, 0.4));
        let rotated = rotate180.apply_uv(unrotated);

        assert!((rotated.x - (1.0 - unrotated.x)).abs() < 1.0e-6);
        assert!((rotated.y - (1.0 - unrotated.y)).abs() < 1.0e-6);
        assert_ne!(rotated.x > 0.5, unrotated.x > 0.5);
    }

    #[test]
    fn vertical_texture_flip_preserves_stereo_baseline_signal() {
        let tracking = tracking_basis();
        let intrinsics = centered_square_intrinsics();
        let surface = head_anchored_preview_surface_corners(tracking, 60.0, 1.0, 1.0, 1.0)
            .expect("surface should resolve");
        let left_rows = surface_to_camera_uv_homography(
            surface,
            camera_for_tracking_basis(tracking, -0.03),
            intrinsics,
        )
        .expect("left projection should resolve");
        let right_rows = surface_to_camera_uv_homography(
            surface,
            camera_for_tracking_basis(tracking, 0.03),
            intrinsics,
        )
        .expect("right projection should resolve");
        let flip_y =
            CameraTextureTransform::new("test", "display-origin correction").with_flip_y(true);

        let left = flip_y.apply_uv(apply_homography(left_rows, Vec2::new(0.5, 0.5)));
        let right = flip_y.apply_uv(apply_homography(right_rows, Vec2::new(0.5, 0.5)));

        assert!(left.x > 0.5);
        assert!(right.x < 0.5);
        assert!(left.x > right.x);
    }

    #[test]
    fn head_basis_rotation_keeps_relative_projection_stable() {
        let base_tracking = tracking_basis();
        let yaw = Quat::from_axis_angle(Vec3::UP, 0.35);
        let rotated_tracking = TrackingBasis::new(
            Vec3::new(0.2, 1.0, -0.4),
            yaw.rotate_vec3(Vec3::RIGHT),
            yaw.rotate_vec3(Vec3::UP),
            yaw.rotate_vec3(Vec3::FORWARD_NEG_Z),
        )
        .expect("rotated tracking basis should be valid");
        let intrinsics = centered_square_intrinsics();

        let base_surface =
            head_anchored_preview_surface_corners(base_tracking, 60.0, 1.0, 1.0, 1.0)
                .expect("base surface should resolve");
        let rotated_surface =
            head_anchored_preview_surface_corners(rotated_tracking, 60.0, 1.0, 1.0, 1.0)
                .expect("rotated surface should resolve");
        let base_rows = surface_to_camera_uv_homography(
            base_surface,
            camera_for_tracking_basis(base_tracking, -0.03),
            intrinsics,
        )
        .expect("base projection should resolve");
        let rotated_rows = surface_to_camera_uv_homography(
            rotated_surface,
            camera_for_tracking_basis(rotated_tracking, -0.03),
            intrinsics,
        )
        .expect("rotated projection should resolve");

        let uv = Vec2::new(0.62, 0.37);
        let base = apply_homography(base_rows, uv);
        let rotated = apply_homography(rotated_rows, uv);

        assert!((base.x - rotated.x).abs() < 1.0e-5);
        assert!((base.y - rotated.y).abs() < 1.0e-5);
    }

    #[test]
    fn full_view_uv_scale_maps_visible_surface_back_to_content_surface() {
        let scale = full_view_content_uv_scale(2.10, 1.06).expect("valid overscans");
        assert!((scale - 1.9811321).abs() < 0.0001);

        let visible_edge_uv = Vec2::new(0.0, 0.5);
        let content_uv = (visible_edge_uv - Vec2::new(0.5, 0.5)) * scale + Vec2::new(0.5, 0.5);
        let visible_local_x = (content_uv.x - 0.5) / scale;

        assert!((visible_local_x + 0.5).abs() < 0.0001);
    }

    #[test]
    fn openxr_eye_projection_uses_fullscreen_shader_uv_origin() {
        let tracking = tracking_basis();
        let eye = camera_for_tracking_basis(tracking, 0.0);
        let center = project_tracking_point_to_eye_screen_uv(
            eye,
            -1.0,
            1.0,
            -1.0,
            1.0,
            tracking.origin + tracking.forward,
        )
        .expect("center point should project");
        let top = project_tracking_point_to_eye_screen_uv(
            eye,
            -1.0,
            1.0,
            -1.0,
            1.0,
            tracking.origin + tracking.forward + tracking.up,
        )
        .expect("top point should project");

        assert!((center.x - 0.5).abs() < 1.0e-6);
        assert!((center.y - 0.5).abs() < 1.0e-6);
        assert!((top.x - 0.5).abs() < 1.0e-6);
        assert!(top.y.abs() < 1.0e-6);
    }

    #[test]
    fn screen_to_camera_homography_matches_eye_projection_for_centered_camera() {
        let tracking = tracking_basis();
        let eye = camera_for_tracking_basis(tracking, 0.0);
        let surface = head_anchored_preview_surface_corners(tracking, 90.0, 1.0, 1.0, 1.0)
            .expect("surface should resolve");
        let surface_to_screen =
            surface_to_eye_screen_uv_homography(surface, eye, -1.0, 1.0, -1.0, 1.0)
                .expect("screen homography should resolve");
        let surface_to_camera =
            surface_to_camera_uv_homography(surface, eye, fov_matched_square_intrinsics())
                .expect("camera homography should resolve");
        let screen_to_camera = screen_to_camera_uv_homography(surface_to_screen, surface_to_camera)
            .expect("screen-to-camera homography should resolve");

        for uv in [
            Vec2::new(0.25, 0.25),
            Vec2::new(0.5, 0.5),
            Vec2::new(0.75, 0.8),
        ] {
            let projected = apply_homography(screen_to_camera, uv);
            assert!((projected.x - uv.x).abs() < 1.0e-5);
            assert!((projected.y - (1.0 - uv.y)).abs() < 1.0e-5);
        }
    }

    #[test]
    fn scaled_projection_round_trips_camera_point() {
        let active_array_intrinsics = test_intrinsics();
        let delivered = scale_intrinsics_to_image(
            active_array_intrinsics,
            ImageSize::new(1000, 800),
            ImageSize::new(500, 400),
        )
        .expect("intrinsics should scale");
        let camera_point = Vec3::new(-0.15, 0.25, 3.0);

        let pixel = project_camera_point(delivered, camera_point).expect("point should project");
        let round_trip =
            back_project_pixel(delivered, pixel, camera_point.z).expect("pixel should unproject");

        assert!((round_trip.x - camera_point.x).abs() < 1.0e-5);
        assert!((round_trip.y - camera_point.y).abs() < 1.0e-5);
        assert!((round_trip.z - camera_point.z).abs() < 1.0e-5);
    }

    #[test]
    fn timestamp_matching_respects_max_delta() {
        let timestamps = [100, 150, 210];
        let matched = match_nearest_timestamp(160, &timestamps, Some(20))
            .expect("nearest timestamp should match");

        assert_eq!(
            matched,
            TimestampMatch {
                candidate_index: 1,
                delta_ns: -10,
            }
        );
        assert_eq!(match_nearest_timestamp(160, &timestamps, Some(5)), None);
    }

    #[test]
    fn stereo_timestamp_pairing_uses_closest_within_delta() {
        let left = [1_000_u64, 2_000, 3_000];
        let right = [980_u64, 2_040, 3_400];

        let pair =
            match_stereo_timestamps(&left, &right, 50).expect("nearest stereo pair should match");

        assert_eq!(pair.left_index, 0);
        assert_eq!(pair.right_index, 0);
        assert_eq!(pair.delta_ns, 20);
        assert_eq!(pair.midpoint_timestamp_ns, 990);
        assert_eq!(match_stereo_timestamps(&left, &right, 10), None);
    }

    #[cfg(feature = "serde")]
    #[test]
    fn timestamp_match_round_trips_with_serde() {
        let value = TimestampMatch {
            candidate_index: 1,
            delta_ns: -10,
        };

        let encoded = serde_json::to_string(&value).expect("match should serialize");
        let decoded: TimestampMatch =
            serde_json::from_str(&encoded).expect("match should deserialize");

        assert_eq!(decoded, value);
    }
}
