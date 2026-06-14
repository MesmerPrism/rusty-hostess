//! Homography math and temporal stereo projection smoothing helpers.

use super::{ImageSize, Pose, Quat, Rect2, Vec2};

/// Apply a homography to a normalized UV coordinate.
pub fn apply_homography_uv(rows: [[f32; 3]; 3], uv: Vec2) -> Option<Vec2> {
    let w = rows[2][0] * uv.x + rows[2][1] * uv.y + rows[2][2];
    if !w.is_finite() || w.abs() <= 1.0e-6 {
        return None;
    }
    let u = (rows[0][0] * uv.x + rows[0][1] * uv.y + rows[0][2]) / w;
    let v = (rows[1][0] * uv.x + rows[1][1] * uv.y + rows[1][2]) / w;
    (u.is_finite() && v.is_finite()).then_some(Vec2::new(u, v))
}

/// Return the screen-space bounding rect of a homography-projected unit square.
pub fn homography_unit_square_bounding_rect(rows: [[f32; 3]; 3]) -> Option<Rect2> {
    let points = [
        apply_homography_uv(rows, Vec2::new(0.0, 0.0))?,
        apply_homography_uv(rows, Vec2::new(1.0, 0.0))?,
        apply_homography_uv(rows, Vec2::new(1.0, 1.0))?,
        apply_homography_uv(rows, Vec2::new(0.0, 1.0))?,
    ];
    let mut min_x = f32::INFINITY;
    let mut min_y = f32::INFINITY;
    let mut max_x = f32::NEG_INFINITY;
    let mut max_y = f32::NEG_INFINITY;
    for point in points {
        min_x = min_x.min(point.x);
        min_y = min_y.min(point.y);
        max_x = max_x.max(point.x);
        max_y = max_y.max(point.y);
    }
    let rect = Rect2::new(
        Vec2::new(min_x, min_y),
        Vec2::new((max_x - min_x).max(0.0), (max_y - min_y).max(0.0)),
    );
    (rect.is_valid() && rect.size.x > 0.0 && rect.size.y > 0.0).then_some(rect)
}

/// Build a 3x3 homography from unit-square UV to a projected quadrilateral.
pub fn homography_from_unit_square(points: [Vec2; 4]) -> Option<[[f32; 3]; 3]> {
    if !points.iter().all(|point| point.is_finite()) {
        return None;
    }

    let p0 = points[0];
    let p1 = points[1];
    let p2 = points[2];
    let p3 = points[3];
    let sx = p0.x - p1.x + p2.x - p3.x;
    let sy = p0.y - p1.y + p2.y - p3.y;
    let (g, h) = if sx.abs() <= 1.0e-6 && sy.abs() <= 1.0e-6 {
        (0.0, 0.0)
    } else {
        let dx1 = p1.x - p2.x;
        let dy1 = p1.y - p2.y;
        let dx2 = p3.x - p2.x;
        let dy2 = p3.y - p2.y;
        let denominator = dx1 * dy2 - dx2 * dy1;
        if denominator.abs() <= 1.0e-6 || !denominator.is_finite() {
            return None;
        }
        (
            (sx * dy2 - dx2 * sy) / denominator,
            (dx1 * sy - sx * dy1) / denominator,
        )
    };

    let rows = [
        [p1.x - p0.x + g * p1.x, p3.x - p0.x + h * p3.x, p0.x],
        [p1.y - p0.y + g * p1.y, p3.y - p0.y + h * p3.y, p0.y],
        [g, h, 1.0],
    ];
    rows.iter()
        .flatten()
        .all(|value| value.is_finite())
        .then_some(rows)
}

/// Invert a 3x3 homography matrix.
pub fn invert_homography(rows: [[f32; 3]; 3]) -> Option<[[f32; 3]; 3]> {
    if !rows.iter().flatten().all(|value| value.is_finite()) {
        return None;
    }

    let a = rows[0][0];
    let b = rows[0][1];
    let c = rows[0][2];
    let d = rows[1][0];
    let e = rows[1][1];
    let f = rows[1][2];
    let g = rows[2][0];
    let h = rows[2][1];
    let i = rows[2][2];
    let det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
    if det.abs() <= 1.0e-7 || !det.is_finite() {
        return None;
    }
    let inv_det = 1.0 / det;
    let inverse = [
        [
            (e * i - f * h) * inv_det,
            (c * h - b * i) * inv_det,
            (b * f - c * e) * inv_det,
        ],
        [
            (f * g - d * i) * inv_det,
            (a * i - c * g) * inv_det,
            (c * d - a * f) * inv_det,
        ],
        [
            (d * h - e * g) * inv_det,
            (b * g - a * h) * inv_det,
            (a * e - b * d) * inv_det,
        ],
    ];
    inverse
        .iter()
        .flatten()
        .all(|value| value.is_finite())
        .then_some(inverse)
}

/// Multiply two 3x3 homographies as `left * right`.
pub fn multiply_homographies(left: [[f32; 3]; 3], right: [[f32; 3]; 3]) -> Option<[[f32; 3]; 3]> {
    if !left.iter().flatten().all(|value| value.is_finite())
        || !right.iter().flatten().all(|value| value.is_finite())
    {
        return None;
    }

    let mut out = [[0.0; 3]; 3];
    for row in 0..3 {
        for col in 0..3 {
            out[row][col] = left[row][0] * right[0][col]
                + left[row][1] * right[1][col]
                + left[row][2] * right[2][col];
        }
    }
    out.iter()
        .flatten()
        .all(|value| value.is_finite())
        .then_some(out)
}

/// Screen-to-camera homographies for a stereo custom camera projection.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct StereoHomographyProjection {
    pub left_screen_to_camera: [[f32; 3]; 3],
    pub right_screen_to_camera: [[f32; 3]; 3],
}

impl StereoHomographyProjection {
    pub const fn new(
        left_screen_to_camera: [[f32; 3]; 3],
        right_screen_to_camera: [[f32; 3]; 3],
    ) -> Self {
        Self {
            left_screen_to_camera,
            right_screen_to_camera,
        }
    }

    pub fn is_valid(self) -> bool {
        homography_rows_are_finite(self.left_screen_to_camera)
            && homography_rows_are_finite(self.right_screen_to_camera)
    }
}

/// Motion and coverage metrics derived from stereo projection homographies.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct StereoHomographyProjectionMetrics {
    pub average_motion_px: f32,
    pub p95_motion_px: f32,
    pub sample_count: u32,
    pub invalid_uv_sample_count: u32,
    pub invalid_uv_percent: f32,
}

/// Result of clamping a target stereo homography toward a previous visible
/// homography by screen-space p95 motion.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ScreenMotionClampResult {
    pub projection: StereoHomographyProjection,
    pub alpha: f32,
    pub clamped: bool,
    pub target_motion: StereoHomographyProjectionMetrics,
    pub applied_motion: StereoHomographyProjectionMetrics,
    pub residual_motion: StereoHomographyProjectionMetrics,
}

/// Result of clamping a target stereo homography using a shared pose-delta
/// coefficient before measuring the resulting screen-space motion.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PoseDeltaClampResult {
    pub projection: StereoHomographyProjection,
    pub visual_pose: Pose,
    pub alpha: f32,
    pub clamped: bool,
    pub angular_delta_deg: f32,
    pub linear_delta_m: f32,
    pub target_motion: StereoHomographyProjectionMetrics,
    pub applied_motion: StereoHomographyProjectionMetrics,
    pub residual_motion: StereoHomographyProjectionMetrics,
}

/// Default sample grid for temporal projection motion estimates.
pub const TEMPORAL_PROJECTION_SAMPLE_GRID_5X5: [Vec2; 25] = [
    Vec2::new(0.1, 0.1),
    Vec2::new(0.3, 0.1),
    Vec2::new(0.5, 0.1),
    Vec2::new(0.7, 0.1),
    Vec2::new(0.9, 0.1),
    Vec2::new(0.1, 0.3),
    Vec2::new(0.3, 0.3),
    Vec2::new(0.5, 0.3),
    Vec2::new(0.7, 0.3),
    Vec2::new(0.9, 0.3),
    Vec2::new(0.1, 0.5),
    Vec2::new(0.3, 0.5),
    Vec2::new(0.5, 0.5),
    Vec2::new(0.7, 0.5),
    Vec2::new(0.9, 0.5),
    Vec2::new(0.1, 0.7),
    Vec2::new(0.3, 0.7),
    Vec2::new(0.5, 0.7),
    Vec2::new(0.7, 0.7),
    Vec2::new(0.9, 0.7),
    Vec2::new(0.1, 0.9),
    Vec2::new(0.3, 0.9),
    Vec2::new(0.5, 0.9),
    Vec2::new(0.7, 0.9),
    Vec2::new(0.9, 0.9),
];

/// Apply a 3x3 UV homography to a normalized UV coordinate.
pub fn apply_uv_homography(rows: [[f32; 3]; 3], uv: Vec2) -> Option<Vec2> {
    if !homography_rows_are_finite(rows) || !uv.is_finite() {
        return None;
    }

    let w = rows[2][0] * uv.x + rows[2][1] * uv.y + rows[2][2];
    if !w.is_finite() || w.abs() < 1.0e-6 {
        return None;
    }
    let projected = Vec2::new(
        (rows[0][0] * uv.x + rows[0][1] * uv.y + rows[0][2]) / w,
        (rows[1][0] * uv.x + rows[1][1] * uv.y + rows[1][2]) / w,
    );
    projected.is_finite().then_some(projected)
}

/// Estimate temporal projection motion from consecutive stereo homographies.
///
/// When `previous` is `None`, motion is reported as zero but invalid current
/// UV coverage is still measured. This matches the first-frame behavior needed
/// by metrics-only renderers.
pub fn stereo_homography_projection_metrics(
    previous: Option<StereoHomographyProjection>,
    current: StereoHomographyProjection,
    resolution: ImageSize,
) -> StereoHomographyProjectionMetrics {
    stereo_homography_projection_metrics_with_samples(
        previous,
        current,
        resolution,
        &TEMPORAL_PROJECTION_SAMPLE_GRID_5X5,
    )
}

/// Clamp target stereo homography motion to a p95 pixel budget.
///
/// The blend factor is shared between eyes so stereo lockstep is preserved.
/// Invalid previous projections fall back to the target projection, matching
/// first-frame behavior where there is nothing to smooth against.
pub fn clamp_stereo_homography_screen_motion(
    previous_visible: Option<StereoHomographyProjection>,
    target: StereoHomographyProjection,
    resolution: ImageSize,
    max_motion_px_per_frame: f32,
) -> ScreenMotionClampResult {
    let visual_start = previous_visible
        .filter(|projection| projection.is_valid())
        .unwrap_or(target);
    let target_motion =
        stereo_homography_projection_metrics(Some(visual_start), target, resolution);
    let max_motion_px = if max_motion_px_per_frame.is_finite() {
        max_motion_px_per_frame.max(1.0)
    } else {
        1.0
    };
    let target_motion_px = target_motion.p95_motion_px.max(0.0);
    let alpha = if target_motion_px > max_motion_px {
        (max_motion_px / target_motion_px).clamp(0.0, 1.0)
    } else {
        1.0
    };
    let projection = blend_stereo_homography_projection(visual_start, target, alpha);
    let applied_motion =
        stereo_homography_projection_metrics(Some(visual_start), projection, resolution);
    let residual_motion =
        stereo_homography_projection_metrics(Some(projection), target, resolution);

    ScreenMotionClampResult {
        projection,
        alpha,
        clamped: alpha < 0.999,
        target_motion,
        applied_motion,
        residual_motion,
    }
}

/// Clamp target stereo homography advancement according to angular and linear
/// pose deltas.
///
/// The pose-derived blend factor is shared between eyes. Screen-space motion
/// metrics are still reported so scorecards can prove residual projection lag
/// without needing renderer-private pose state.
pub fn clamp_stereo_homography_pose_delta(
    previous_visible: Option<StereoHomographyProjection>,
    target: StereoHomographyProjection,
    previous_visual_pose: Option<Pose>,
    target_pose: Pose,
    resolution: ImageSize,
    max_angular_deg_per_frame: f32,
    max_linear_m_per_frame: f32,
) -> PoseDeltaClampResult {
    let visual_start = previous_visible
        .filter(|projection| projection.is_valid())
        .unwrap_or(target);
    let pose_start = previous_visual_pose
        .filter(|pose| pose.is_finite())
        .unwrap_or(target_pose);

    let angular_delta_deg = pose_angular_delta_degrees(pose_start, target_pose);
    let linear_delta_m = pose_linear_delta_meters(pose_start, target_pose);
    let angular_alpha =
        clamp_alpha_for_delta(angular_delta_deg, max_angular_deg_per_frame.max(0.0));
    let linear_alpha = clamp_alpha_for_delta(linear_delta_m, max_linear_m_per_frame.max(0.0));
    let alpha = angular_alpha.min(linear_alpha).clamp(0.0, 1.0);

    let projection = blend_stereo_homography_projection(visual_start, target, alpha);
    let visual_pose = blend_pose(pose_start, target_pose, alpha);
    let target_motion =
        stereo_homography_projection_metrics(Some(visual_start), target, resolution);
    let applied_motion =
        stereo_homography_projection_metrics(Some(visual_start), projection, resolution);
    let residual_motion =
        stereo_homography_projection_metrics(Some(projection), target, resolution);

    PoseDeltaClampResult {
        projection,
        visual_pose,
        alpha,
        clamped: alpha < 0.999,
        angular_delta_deg,
        linear_delta_m,
        target_motion,
        applied_motion,
        residual_motion,
    }
}

/// Linearly blend screen-to-camera homography rows, preserving the target when
/// interpolation produces non-finite rows.
pub fn blend_stereo_homography_projection(
    from: StereoHomographyProjection,
    to: StereoHomographyProjection,
    alpha: f32,
) -> StereoHomographyProjection {
    let alpha = alpha.clamp(0.0, 1.0);
    StereoHomographyProjection::new(
        blend_homography_rows(from.left_screen_to_camera, to.left_screen_to_camera, alpha),
        blend_homography_rows(
            from.right_screen_to_camera,
            to.right_screen_to_camera,
            alpha,
        ),
    )
}

fn clamp_alpha_for_delta(delta: f32, max_delta: f32) -> f32 {
    if !delta.is_finite() || delta <= 0.0 || !max_delta.is_finite() || max_delta <= 0.0 {
        return 1.0;
    }
    if delta > max_delta {
        (max_delta / delta).clamp(0.0, 1.0)
    } else {
        1.0
    }
}

fn blend_pose(from: Pose, to: Pose, alpha: f32) -> Pose {
    let alpha = alpha.clamp(0.0, 1.0);
    Pose::new(
        from.position + ((to.position - from.position) * alpha),
        blend_quaternion(from.orientation, to.orientation, alpha),
    )
}

fn blend_quaternion(from: Quat, to: Quat, alpha: f32) -> Quat {
    let from = from.normalized_or(Quat::IDENTITY);
    let mut to = to.normalized_or(Quat::IDENTITY);
    if quat_dot(from, to) < 0.0 {
        to = Quat::new(-to.x, -to.y, -to.z, -to.w);
    }
    Quat::new(
        from.x + ((to.x - from.x) * alpha),
        from.y + ((to.y - from.y) * alpha),
        from.z + ((to.z - from.z) * alpha),
        from.w + ((to.w - from.w) * alpha),
    )
    .normalized_or(Quat::IDENTITY)
}

fn pose_angular_delta_degrees(from: Pose, to: Pose) -> f32 {
    let dot = quat_dot(
        from.orientation.normalized_or(Quat::IDENTITY),
        to.orientation.normalized_or(Quat::IDENTITY),
    )
    .abs()
    .clamp(0.0, 1.0);
    (2.0 * dot.acos()).to_degrees()
}

fn pose_linear_delta_meters(from: Pose, to: Pose) -> f32 {
    let delta = to.position - from.position;
    ((delta.x * delta.x) + (delta.y * delta.y) + (delta.z * delta.z)).sqrt()
}

fn quat_dot(left: Quat, right: Quat) -> f32 {
    (left.x * right.x) + (left.y * right.y) + (left.z * right.z) + (left.w * right.w)
}

fn blend_homography_rows(from: [[f32; 3]; 3], to: [[f32; 3]; 3], alpha: f32) -> [[f32; 3]; 3] {
    let mut out = [[0.0; 3]; 3];
    for row in 0..3 {
        for column in 0..3 {
            out[row][column] = from[row][column] + (to[row][column] - from[row][column]) * alpha;
        }
    }
    if homography_rows_are_finite(out) {
        out
    } else {
        to
    }
}

/// Estimate temporal projection motion with a caller-supplied sample grid.
pub fn stereo_homography_projection_metrics_with_samples(
    previous: Option<StereoHomographyProjection>,
    current: StereoHomographyProjection,
    resolution: ImageSize,
    samples: &[Vec2],
) -> StereoHomographyProjectionMetrics {
    let sample_count = (samples.len() * 2) as u32;
    if !current.is_valid() || !resolution.is_non_empty() || samples.is_empty() {
        return StereoHomographyProjectionMetrics {
            sample_count,
            invalid_uv_sample_count: sample_count,
            invalid_uv_percent: if sample_count == 0 { 0.0 } else { 100.0 },
            ..StereoHomographyProjectionMetrics::default()
        };
    }

    let invalid_uv_sample_count = count_invalid_uv_samples(current, samples);
    let invalid_uv_percent = if sample_count == 0 {
        0.0
    } else {
        invalid_uv_sample_count as f32 * 100.0 / sample_count as f32
    };
    let Some(previous) = previous.filter(|previous| previous.is_valid()) else {
        return StereoHomographyProjectionMetrics {
            sample_count,
            invalid_uv_sample_count,
            invalid_uv_percent,
            ..StereoHomographyProjectionMetrics::default()
        };
    };

    let mut deltas = Vec::with_capacity(sample_count as usize);
    for (previous_rows, current_rows) in [
        (
            previous.left_screen_to_camera,
            current.left_screen_to_camera,
        ),
        (
            previous.right_screen_to_camera,
            current.right_screen_to_camera,
        ),
    ] {
        for &sample in samples {
            let Some(previous_uv) = apply_uv_homography(previous_rows, sample) else {
                continue;
            };
            let Some(current_uv) = apply_uv_homography(current_rows, sample) else {
                continue;
            };
            let dx = (current_uv.x - previous_uv.x) * resolution.width as f32;
            let dy = (current_uv.y - previous_uv.y) * resolution.height as f32;
            let delta = (dx * dx + dy * dy).sqrt();
            if delta.is_finite() {
                deltas.push(delta);
            }
        }
    }

    StereoHomographyProjectionMetrics {
        average_motion_px: finite_average(&deltas),
        p95_motion_px: percentile_95(deltas),
        sample_count,
        invalid_uv_sample_count,
        invalid_uv_percent,
    }
}

fn homography_rows_are_finite(rows: [[f32; 3]; 3]) -> bool {
    rows.iter().flatten().all(|value| value.is_finite())
}

fn count_invalid_uv_samples(projection: StereoHomographyProjection, samples: &[Vec2]) -> u32 {
    let mut invalid = 0_u32;
    for rows in [
        projection.left_screen_to_camera,
        projection.right_screen_to_camera,
    ] {
        for &sample in samples {
            match apply_uv_homography(rows, sample) {
                Some(uv) if (0.0..=1.0).contains(&uv.x) && (0.0..=1.0).contains(&uv.y) => {}
                _ => invalid += 1,
            }
        }
    }
    invalid
}

fn finite_average(values: &[f32]) -> f32 {
    if values.is_empty() {
        return 0.0;
    }
    values.iter().sum::<f32>() / values.len() as f32
}

fn percentile_95(mut values: Vec<f32>) -> f32 {
    if values.is_empty() {
        return 0.0;
    }
    values.sort_by(f32::total_cmp);
    let index = ((values.len() as f32 * 0.95).ceil() as usize).saturating_sub(1);
    values[index.min(values.len() - 1)]
}
