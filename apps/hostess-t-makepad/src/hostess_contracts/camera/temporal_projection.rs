//! Camera temporal projection and projection-state contract family.

use super::{Eye, Pose};

/// Temporal smoothing mode for an app-owned custom camera projection.
///
/// This is only a policy label. Platform adapters still own OpenXR frame
/// timing, camera acquisition, shader uniforms, depth acquire, and optional
/// `XR_FB_space_warp` submission.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum TemporalProjectionMode {
    /// Submit the target projection directly.
    #[default]
    Off,
    /// Clamp pose-space angular and linear changes before submission.
    PoseDeltaClamp,
    /// Clamp the estimated screen-space motion in pixels per display frame.
    ScreenMotionClamp,
    /// Use a depth witness when available, falling back to planar clamping.
    DepthAwareClamp,
    /// Generate planar motion vectors for an optional space-warp experiment.
    AswPlanar,
    /// Generate depth-aware motion vectors for an optional space-warp experiment.
    AswDepthAware,
}

impl TemporalProjectionMode {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::Off => "off",
            Self::PoseDeltaClamp => "pose-delta-clamp",
            Self::ScreenMotionClamp => "screen-motion-clamp",
            Self::DepthAwareClamp => "depth-aware-clamp",
            Self::AswPlanar => "asw-planar",
            Self::AswDepthAware => "asw-depth-aware",
        }
    }

    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "off" | "none" => Some(Self::Off),
            "pose-delta-clamp" | "poseDeltaClamp" => Some(Self::PoseDeltaClamp),
            "screen-motion-clamp" | "screenMotionClamp" => Some(Self::ScreenMotionClamp),
            "depth-aware-clamp" | "depthAwareClamp" => Some(Self::DepthAwareClamp),
            "asw-planar" | "spacewarp-planar" => Some(Self::AswPlanar),
            "asw-depth-aware" | "spacewarp-depth-aware" => Some(Self::AswDepthAware),
            _ => None,
        }
    }
}

/// Policy for when a newer camera frame pair becomes the visible source pair.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum CameraFrameAdoptionMode {
    /// Adopt the newest accepted pair immediately.
    #[default]
    Immediate,
    /// Hold the previous visible pair until the projection residual is small.
    HoldUntilSmooth,
    /// Blend the previous and next camera pair for a short fixed window.
    ShortCrossfade,
    /// Hold while screen-space head motion is high, adopt when it settles.
    VelocityAware,
}

impl CameraFrameAdoptionMode {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::Immediate => "immediate",
            Self::HoldUntilSmooth => "hold-until-smooth",
            Self::ShortCrossfade => "short-crossfade",
            Self::VelocityAware => "velocity-aware",
        }
    }

    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "immediate" => Some(Self::Immediate),
            "hold-until-smooth" | "holdUntilSmooth" => Some(Self::HoldUntilSmooth),
            "short-crossfade" | "shortCrossfade" => Some(Self::ShortCrossfade),
            "velocity-aware" | "velocityAware" => Some(Self::VelocityAware),
            _ => None,
        }
    }
}

/// Edge handling for camera UVs exposed by temporal lingering.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum TemporalProjectionEdgeMode {
    /// Leave invalid samples to the adapter's existing behavior.
    #[default]
    None,
    /// Clamp invalid UVs to the nearest valid source edge.
    Clamp,
    /// Clamp and feather invalid regions into a soft edge.
    ClampSoft,
    /// Fade invalid samples toward the adapter's configured fallback color.
    FadeInvalid,
}

impl TemporalProjectionEdgeMode {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Clamp => "clamp",
            Self::ClampSoft => "clamp-soft",
            Self::FadeInvalid => "fade-invalid",
        }
    }

    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "none" | "off" => Some(Self::None),
            "clamp" => Some(Self::Clamp),
            "clamp-soft" | "clampSoft" => Some(Self::ClampSoft),
            "fade-invalid" | "fadeInvalid" => Some(Self::FadeInvalid),
            _ => None,
        }
    }
}

/// Timing stamps for one camera frame as it moves through a projection path.
///
/// Different adapters may not share a single clock domain for every field, so
/// this contract records raw stamps without implying they are directly
/// subtractable unless the adapter documents that clock mapping.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CameraFrameTiming {
    pub source_eye: Eye,
    pub frame_sequence: u64,
    pub camera_capture_time_ns: Option<i64>,
    pub camera_frame_number: Option<i64>,
    pub receive_time_ns: Option<i64>,
    pub decode_output_time_ns: Option<i64>,
    pub import_time_ns: Option<i64>,
}

impl CameraFrameTiming {
    pub const fn new(source_eye: Eye, frame_sequence: u64) -> Self {
        Self {
            source_eye,
            frame_sequence,
            camera_capture_time_ns: None,
            camera_frame_number: None,
            receive_time_ns: None,
            decode_output_time_ns: None,
            import_time_ns: None,
        }
    }

    pub const fn with_camera_capture_time_ns(mut self, value: i64) -> Self {
        self.camera_capture_time_ns = Some(value);
        self
    }

    pub const fn with_camera_frame_number(mut self, value: i64) -> Self {
        self.camera_frame_number = Some(value);
        self
    }

    pub const fn with_receive_time_ns(mut self, value: i64) -> Self {
        self.receive_time_ns = Some(value);
        self
    }

    pub const fn with_decode_output_time_ns(mut self, value: i64) -> Self {
        self.decode_output_time_ns = Some(value);
        self
    }

    pub const fn with_import_time_ns(mut self, value: i64) -> Self {
        self.import_time_ns = Some(value);
        self
    }
}

/// Left/right camera frame timing pair used by temporal adoption policy.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct StereoCameraFramePair {
    pub pair_sequence: u64,
    pub left: CameraFrameTiming,
    pub right: CameraFrameTiming,
    pub pair_delta_ns: Option<i64>,
    pub accepted_pair: bool,
}

impl StereoCameraFramePair {
    pub fn new(pair_sequence: u64, left: CameraFrameTiming, right: CameraFrameTiming) -> Self {
        let pair_delta_ns = match (left.camera_capture_time_ns, right.camera_capture_time_ns) {
            (Some(left_ns), Some(right_ns)) => {
                Some(left_ns.saturating_sub(right_ns).saturating_abs())
            }
            _ => None,
        };
        Self {
            pair_sequence,
            left,
            right,
            pair_delta_ns,
            accepted_pair: false,
        }
    }

    pub const fn with_accepted_pair(mut self, accepted_pair: bool) -> Self {
        self.accepted_pair = accepted_pair;
        self
    }

    pub const fn with_pair_delta_ns(mut self, pair_delta_ns: i64) -> Self {
        self.pair_delta_ns = Some(pair_delta_ns);
        self
    }

    pub fn is_valid(&self) -> bool {
        self.left.source_eye == Eye::Left
            && self.right.source_eye == Eye::Right
            && self.pair_delta_ns.map(|value| value >= 0).unwrap_or(true)
    }
}

/// One eye's screen-to-camera projection state.
///
/// The required matrix is a generic 3x3 homography from display-eye screen UV
/// into camera UV. Adapters can also report the intermediate
/// screen-to-surface and surface-to-camera rows so Vulkan, OpenGL, and
/// framework comparison lanes can separate projection-footprint differences
/// from texture-transform or effect-stack differences.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct CameraProjectionState {
    pub eye: Eye,
    pub projection_sequence: u64,
    #[cfg_attr(feature = "serde", serde(default))]
    pub screen_to_surface_uv: Option<[[f32; 3]; 3]>,
    #[cfg_attr(feature = "serde", serde(default))]
    pub surface_to_camera_uv: Option<[[f32; 3]; 3]>,
    pub screen_to_camera_uv: [[f32; 3]; 3],
    pub source_frame_sequence: Option<u64>,
    pub projection_surface_label: String,
    pub texture_transform_label: String,
}

impl CameraProjectionState {
    pub fn new(eye: Eye, projection_sequence: u64, screen_to_camera_uv: [[f32; 3]; 3]) -> Self {
        Self {
            eye,
            projection_sequence,
            screen_to_surface_uv: None,
            surface_to_camera_uv: None,
            screen_to_camera_uv,
            source_frame_sequence: None,
            projection_surface_label: String::new(),
            texture_transform_label: String::new(),
        }
    }

    pub fn with_source_frame_sequence(mut self, source_frame_sequence: u64) -> Self {
        self.source_frame_sequence = Some(source_frame_sequence);
        self
    }

    pub const fn with_screen_to_surface_uv(mut self, rows: [[f32; 3]; 3]) -> Self {
        self.screen_to_surface_uv = Some(rows);
        self
    }

    pub const fn with_surface_to_camera_uv(mut self, rows: [[f32; 3]; 3]) -> Self {
        self.surface_to_camera_uv = Some(rows);
        self
    }

    pub fn with_projection_surface_label(mut self, label: impl Into<String>) -> Self {
        self.projection_surface_label = label.into();
        self
    }

    pub fn with_texture_transform_label(mut self, label: impl Into<String>) -> Self {
        self.texture_transform_label = label.into();
        self
    }

    pub const fn has_projection_stage_rows(&self) -> bool {
        self.screen_to_surface_uv.is_some() && self.surface_to_camera_uv.is_some()
    }

    pub fn is_valid(&self) -> bool {
        self.eye != Eye::Mono
            && homography_rows_are_valid(self.screen_to_camera_uv)
            && self
                .screen_to_surface_uv
                .map(homography_rows_are_valid)
                .unwrap_or(true)
            && self
                .surface_to_camera_uv
                .map(homography_rows_are_valid)
                .unwrap_or(true)
    }
}

/// Physically current projection target for a camera pair and display pose.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct ProjectionTargetState {
    pub predicted_display_time_ns: i64,
    pub head_pose_at_display: Pose,
    pub camera_pose_at_capture: Option<Pose>,
    pub source_pair_sequence: Option<u64>,
    pub left_projection: CameraProjectionState,
    pub right_projection: CameraProjectionState,
}

impl ProjectionTargetState {
    pub fn new(
        predicted_display_time_ns: i64,
        head_pose_at_display: Pose,
        left_projection: CameraProjectionState,
        right_projection: CameraProjectionState,
    ) -> Self {
        Self {
            predicted_display_time_ns,
            head_pose_at_display,
            camera_pose_at_capture: None,
            source_pair_sequence: None,
            left_projection,
            right_projection,
        }
    }

    pub fn with_camera_pose_at_capture(mut self, camera_pose_at_capture: Pose) -> Self {
        self.camera_pose_at_capture = Some(camera_pose_at_capture);
        self
    }

    pub fn with_source_pair_sequence(mut self, source_pair_sequence: u64) -> Self {
        self.source_pair_sequence = Some(source_pair_sequence);
        self
    }

    pub fn is_valid(&self) -> bool {
        self.head_pose_at_display.is_finite()
            && self
                .camera_pose_at_capture
                .map(Pose::is_finite)
                .unwrap_or(true)
            && self.left_projection.eye == Eye::Left
            && self.right_projection.eye == Eye::Right
            && self.left_projection.is_valid()
            && self.right_projection.is_valid()
    }
}

/// Projection state actually submitted after temporal smoothing.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct VisualProjectionState {
    pub visual_sequence: u64,
    pub predicted_display_time_ns: i64,
    pub source_pair_sequence: Option<u64>,
    pub left_projection: CameraProjectionState,
    pub right_projection: CameraProjectionState,
    pub visual_lag_ms: f32,
    pub residual_motion_px: f32,
}

impl VisualProjectionState {
    pub fn new(
        visual_sequence: u64,
        predicted_display_time_ns: i64,
        left_projection: CameraProjectionState,
        right_projection: CameraProjectionState,
    ) -> Self {
        Self {
            visual_sequence,
            predicted_display_time_ns,
            source_pair_sequence: None,
            left_projection,
            right_projection,
            visual_lag_ms: 0.0,
            residual_motion_px: 0.0,
        }
    }

    pub fn with_source_pair_sequence(mut self, source_pair_sequence: u64) -> Self {
        self.source_pair_sequence = Some(source_pair_sequence);
        self
    }

    pub const fn with_visual_lag_ms(mut self, visual_lag_ms: f32) -> Self {
        self.visual_lag_ms = visual_lag_ms;
        self
    }

    pub const fn with_residual_motion_px(mut self, residual_motion_px: f32) -> Self {
        self.residual_motion_px = residual_motion_px;
        self
    }

    pub fn is_valid(&self) -> bool {
        self.left_projection.eye == Eye::Left
            && self.right_projection.eye == Eye::Right
            && self.left_projection.is_valid()
            && self.right_projection.is_valid()
            && finite_non_negative(self.visual_lag_ms)
            && finite_non_negative(self.residual_motion_px)
    }
}

/// Runtime policy for app-owned temporal camera projection.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct TemporalProjectionPolicy {
    pub enabled: bool,
    pub mode: TemporalProjectionMode,
    pub max_screen_motion_px_per_frame: f32,
    pub max_angular_deg_per_frame: f32,
    pub max_linear_m_per_frame: f32,
    pub catchup_half_life_ms: f32,
    pub max_visual_lag_ms: f32,
    pub max_camera_frame_age_ms: f32,
    pub stereo_lockstep: bool,
    pub frame_adoption_mode: CameraFrameAdoptionMode,
    pub frame_adoption_max_jump_px: f32,
    pub frame_adoption_max_hold_ms: f32,
    pub crossfade_frames: u32,
    pub edge_mode: TemporalProjectionEdgeMode,
    pub edge_feather_px: f32,
}

impl TemporalProjectionPolicy {
    /// Conservative starting point for a screen-motion clamp experiment.
    pub const CONSERVATIVE_SCREEN_CLAMP: Self = Self {
        enabled: true,
        mode: TemporalProjectionMode::ScreenMotionClamp,
        max_screen_motion_px_per_frame: 18.0,
        max_angular_deg_per_frame: 1.25,
        max_linear_m_per_frame: 0.012,
        catchup_half_life_ms: 50.0,
        max_visual_lag_ms: 120.0,
        max_camera_frame_age_ms: 120.0,
        stereo_lockstep: true,
        frame_adoption_mode: CameraFrameAdoptionMode::HoldUntilSmooth,
        frame_adoption_max_jump_px: 24.0,
        frame_adoption_max_hold_ms: 80.0,
        crossfade_frames: 3,
        edge_mode: TemporalProjectionEdgeMode::ClampSoft,
        edge_feather_px: 32.0,
    };

    pub const OFF: Self = Self {
        enabled: false,
        mode: TemporalProjectionMode::Off,
        max_screen_motion_px_per_frame: 0.0,
        max_angular_deg_per_frame: 0.0,
        max_linear_m_per_frame: 0.0,
        catchup_half_life_ms: 0.0,
        max_visual_lag_ms: 0.0,
        max_camera_frame_age_ms: 0.0,
        stereo_lockstep: true,
        frame_adoption_mode: CameraFrameAdoptionMode::Immediate,
        frame_adoption_max_jump_px: 0.0,
        frame_adoption_max_hold_ms: 0.0,
        crossfade_frames: 0,
        edge_mode: TemporalProjectionEdgeMode::None,
        edge_feather_px: 0.0,
    };

    pub fn is_valid(self) -> bool {
        finite_non_negative(self.max_screen_motion_px_per_frame)
            && finite_non_negative(self.max_angular_deg_per_frame)
            && finite_non_negative(self.max_linear_m_per_frame)
            && finite_non_negative(self.catchup_half_life_ms)
            && finite_non_negative(self.max_visual_lag_ms)
            && finite_non_negative(self.max_camera_frame_age_ms)
            && finite_non_negative(self.frame_adoption_max_jump_px)
            && finite_non_negative(self.frame_adoption_max_hold_ms)
            && finite_non_negative(self.edge_feather_px)
    }
}

impl Default for TemporalProjectionPolicy {
    fn default() -> Self {
        Self::OFF
    }
}

/// Scorecard-facing metrics for temporal camera projection.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct TemporalProjectionMetrics {
    pub camera_frame_age_ms_avg: f32,
    pub camera_frame_age_ms_p95: f32,
    pub depth_frame_age_ms_avg: f32,
    pub stereo_pair_delta_ms_avg: f32,
    pub target_projection_motion_px_avg: f32,
    pub target_projection_motion_px_p95: f32,
    pub applied_projection_motion_px_avg: f32,
    pub applied_projection_motion_px_p95: f32,
    pub projection_residual_px_avg: f32,
    pub projection_residual_px_p95: f32,
    pub visual_lag_ms_avg: f32,
    pub visual_lag_ms_p95: f32,
    pub held_frame_count: u64,
    pub held_frame_duration_ms_max: f32,
    pub frame_crossfade_count: u64,
    pub invalid_uv_px_percent: f32,
    pub edge_fill_px_percent: f32,
    pub asw_enabled_frame_count: u64,
    pub asw_skipped_frame_count: u64,
    pub motion_vector_max_px: f32,
    pub motion_vector_clamped_count: u64,
}

impl TemporalProjectionMetrics {
    pub fn is_valid(self) -> bool {
        [
            self.camera_frame_age_ms_avg,
            self.camera_frame_age_ms_p95,
            self.depth_frame_age_ms_avg,
            self.stereo_pair_delta_ms_avg,
            self.target_projection_motion_px_avg,
            self.target_projection_motion_px_p95,
            self.applied_projection_motion_px_avg,
            self.applied_projection_motion_px_p95,
            self.projection_residual_px_avg,
            self.projection_residual_px_p95,
            self.visual_lag_ms_avg,
            self.visual_lag_ms_p95,
            self.held_frame_duration_ms_max,
            self.motion_vector_max_px,
        ]
        .into_iter()
        .all(finite_non_negative)
            && percent_is_valid(self.invalid_uv_px_percent)
            && percent_is_valid(self.edge_fill_px_percent)
    }
}

fn finite_non_negative(value: f32) -> bool {
    value.is_finite() && value >= 0.0
}

fn homography_rows_are_valid(rows: [[f32; 3]; 3]) -> bool {
    rows.iter().flatten().all(|value| value.is_finite())
        && rows[2].iter().any(|value| value.abs() > f32::EPSILON)
}

fn percent_is_valid(value: f32) -> bool {
    value.is_finite() && (0.0..=100.0).contains(&value)
}
