//! Camera intrinsics, pose-basis, and tracking-space projection helpers.

use super::homography::{homography_from_unit_square, invert_homography, multiply_homographies};
use super::{
    CameraExtrinsics, CameraIntrinsics, CameraModelError, ImageSize, Pose, Quat, Vec2, Vec3,
};

/// Scale camera intrinsics from one pixel domain to another.
///
/// This is the core active-array-to-preview-stream operation used by camera
/// adapters before handing projection data to app-neutral consumers.
pub fn scale_intrinsics_to_image(
    intrinsics: CameraIntrinsics,
    source_size: ImageSize,
    target_size: ImageSize,
) -> Result<CameraIntrinsics, CameraModelError> {
    if !intrinsics.is_valid() {
        return Err(CameraModelError::InvalidSourceIntrinsics);
    }
    if !source_size.is_non_empty() {
        return Err(CameraModelError::InvalidSourceSize);
    }
    if !target_size.is_non_empty() {
        return Err(CameraModelError::InvalidTargetSize);
    }

    let scale = Vec2::new(
        target_size.width as f32 / source_size.width as f32,
        target_size.height as f32 / source_size.height as f32,
    );

    Ok(CameraIntrinsics::new(
        Vec2::new(
            intrinsics.focal_length_px.x * scale.x,
            intrinsics.focal_length_px.y * scale.y,
        ),
        Vec2::new(
            intrinsics.principal_point_px.x * scale.x,
            intrinsics.principal_point_px.y * scale.y,
        ),
        target_size,
    )
    .with_skew_px(intrinsics.skew_px * scale.x))
}

/// Convert Android Camera2 lens pose arrays into public extrinsics.
///
/// Camera2 stores `LENS_POSE_TRANSLATION` as meters in the
/// `LENS_POSE_REFERENCE` coordinate frame and `LENS_POSE_ROTATION` as an
/// `[x, y, z, w]` quaternion that maps the Android sensor/reference frame into
/// the camera-aligned frame. The returned pose preserves that public reference
/// frame as `world_from_camera`, so the quaternion is normalized and inverted
/// before it is stored.
pub fn camera2_lens_pose_to_extrinsics(
    translation_m: [f32; 3],
    rotation_xyzw: [f32; 4],
) -> Result<CameraExtrinsics, CameraModelError> {
    if !translation_m.iter().all(|value| value.is_finite()) {
        return Err(CameraModelError::InvalidPoseTranslation);
    }
    if !rotation_xyzw.iter().all(|value| value.is_finite()) {
        return Err(CameraModelError::InvalidPoseRotation);
    }

    let rotation = Quat::new(
        rotation_xyzw[0],
        rotation_xyzw[1],
        rotation_xyzw[2],
        rotation_xyzw[3],
    );
    let norm_sq = rotation.length_squared();
    if norm_sq <= 1.0e-12 || !norm_sq.is_finite() {
        return Err(CameraModelError::InvalidPoseRotation);
    }

    let reference_from_camera = rotation.normalized_or(Quat::IDENTITY).conjugate();
    let extrinsics = CameraExtrinsics::new(Pose::new(
        Vec3::new(translation_m[0], translation_m[1], translation_m[2]),
        reference_from_camera,
    ));
    if extrinsics.is_valid() {
        Ok(extrinsics)
    } else {
        Err(CameraModelError::InvalidPoseRotation)
    }
}

/// A head/tracking basis used to resolve Android Camera2 pose-reference data
/// into the same space as the OpenXR preview surface.
///
/// `forward` is the current head-forward vector in the renderer's tracking
/// space. For OpenXR view poses this is commonly the view orientation applied
/// to negative Z.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct TrackingBasis {
    pub origin: Vec3,
    pub right: Vec3,
    pub up: Vec3,
    pub forward: Vec3,
}

impl TrackingBasis {
    pub fn new(origin: Vec3, right: Vec3, up: Vec3, forward: Vec3) -> Option<Self> {
        let basis = Self {
            origin,
            right: right.normalized_or(Vec3::ZERO),
            up: up.normalized_or(Vec3::ZERO),
            forward: forward.normalized_or(Vec3::ZERO),
        };
        basis.is_valid().then_some(basis)
    }

    pub fn is_valid(self) -> bool {
        self.origin.is_finite()
            && basis_axis_is_valid(self.right)
            && basis_axis_is_valid(self.up)
            && basis_axis_is_valid(self.forward)
            && self.right.dot(self.up).abs() < 0.05
            && self.right.dot(self.forward).abs() < 0.05
            && self.up.dot(self.forward).abs() < 0.05
    }
}

/// Camera basis in the renderer's tracking space.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct CameraBasis {
    pub position: Vec3,
    pub right: Vec3,
    pub up: Vec3,
    pub forward: Vec3,
}

impl CameraBasis {
    pub fn new(position: Vec3, right: Vec3, up: Vec3, forward: Vec3) -> Option<Self> {
        let basis = Self {
            position,
            right: right.normalized_or(Vec3::ZERO),
            up: up.normalized_or(Vec3::ZERO),
            forward: forward.normalized_or(Vec3::ZERO),
        };
        basis.is_valid().then_some(basis)
    }

    pub fn is_valid(self) -> bool {
        self.position.is_finite()
            && basis_axis_is_valid(self.right)
            && basis_axis_is_valid(self.up)
            && basis_axis_is_valid(self.forward)
            && self.right.dot(self.up).abs() < 0.05
            && self.right.dot(self.forward).abs() < 0.05
            && self.up.dot(self.forward).abs() < 0.05
    }
}

fn basis_axis_is_valid(axis: Vec3) -> bool {
    axis.is_finite() && (axis.length() - 1.0).abs() < 0.05
}

/// Convert a vector expressed in Android Camera2 sensor/reference coordinates
/// into the current renderer tracking basis.
///
/// Android Camera2 pose data is not automatically OpenXR view/world space. The
/// public renderer resolves it by assigning sensor +X to current head right,
/// sensor +Y to current head up, and sensor +Z opposite current head forward.
pub fn android_sensor_vector_to_tracking(basis: TrackingBasis, sensor_vector: Vec3) -> Vec3 {
    (basis.right * sensor_vector.x) + (basis.up * sensor_vector.y)
        - (basis.forward * sensor_vector.z)
}

/// Resolve Camera2 `LENS_POSE_*` extrinsics into a camera basis in the current
/// tracking frame.
///
/// The input extrinsics must be produced by `camera2_lens_pose_to_extrinsics`.
/// Its pose orientation is the Camera2 reference-from-camera rotation. The
/// returned basis can be used directly with a head-anchored preview surface.
pub fn camera_basis_from_camera2_reference_pose(
    tracking: TrackingBasis,
    extrinsics: CameraExtrinsics,
) -> Result<CameraBasis, CameraModelError> {
    camera_basis_from_camera2_reference_pose_relative_to_center(tracking, extrinsics, Vec3::ZERO)
}

/// Resolve Camera2 `LENS_POSE_*` extrinsics after subtracting a shared rig
/// center in the Camera2 reference frame.
///
/// Stereo headset camera poses are often reported relative to a gyroscope or
/// primary-camera reference rather than the head origin used by the renderer.
/// Subtracting the average left/right pose before mapping into tracking space
/// preserves the stereo baseline without making the whole projection surface
/// orbit around an unrelated platform pose origin.
pub fn camera_basis_from_camera2_reference_pose_relative_to_center(
    tracking: TrackingBasis,
    extrinsics: CameraExtrinsics,
    reference_center: Vec3,
) -> Result<CameraBasis, CameraModelError> {
    if !tracking.is_valid() {
        return Err(CameraModelError::InvalidTrackingBasis);
    }
    if !extrinsics.is_valid() || !extrinsics.world_from_camera.position.is_finite() {
        return Err(CameraModelError::InvalidPoseTranslation);
    }
    if !reference_center.is_finite() {
        return Err(CameraModelError::InvalidPoseTranslation);
    }

    let reference_from_camera = extrinsics
        .world_from_camera
        .orientation
        .normalized_or(Quat::IDENTITY);
    if !reference_from_camera.is_finite() {
        return Err(CameraModelError::InvalidPoseRotation);
    }

    let centered_position = extrinsics.world_from_camera.position - reference_center;
    let position = tracking.origin + android_sensor_vector_to_tracking(tracking, centered_position);
    let right =
        android_sensor_vector_to_tracking(tracking, reference_from_camera.rotate_vec3(Vec3::RIGHT));
    let up =
        android_sensor_vector_to_tracking(tracking, reference_from_camera.rotate_vec3(Vec3::UP));
    let forward = android_sensor_vector_to_tracking(
        tracking,
        reference_from_camera.rotate_vec3(Vec3::new(0.0, 0.0, 1.0)),
    );

    CameraBasis::new(position, right, up, forward).ok_or(CameraModelError::InvalidPoseRotation)
}

/// Return the four corners of a head-anchored preview-FOV camera surface in
/// tracking space. The order is top-left, top-right, bottom-right, bottom-left.
pub fn head_anchored_preview_surface_corners(
    tracking: TrackingBasis,
    preview_fov_y_degrees: f32,
    depth_meters: f32,
    aspect: f32,
    overscan: f32,
) -> Result<[Vec3; 4], CameraModelError> {
    if !tracking.is_valid() {
        return Err(CameraModelError::InvalidTrackingBasis);
    }
    if !preview_fov_y_degrees.is_finite()
        || !depth_meters.is_finite()
        || !aspect.is_finite()
        || !overscan.is_finite()
        || depth_meters <= 0.0
        || aspect <= 0.0
    {
        return Err(CameraModelError::InvalidProjectionSurface);
    }

    let half_height = (preview_fov_y_degrees.clamp(1.0, 175.0).to_radians() * 0.5).tan()
        * depth_meters
        * overscan.max(1.0);
    let half_width = half_height * aspect.clamp(0.1, 10.0);
    let center = tracking.origin + tracking.forward * depth_meters;
    Ok([
        center - tracking.right * half_width + tracking.up * half_height,
        center + tracking.right * half_width + tracking.up * half_height,
        center + tracking.right * half_width - tracking.up * half_height,
        center - tracking.right * half_width - tracking.up * half_height,
    ])
}

/// Return the UV scale from the visible full-view surface into the projected
/// camera-content surface.
///
/// Full-lens overlays often render a larger surface than the camera-content
/// projection itself. Public renderers can use this value in the fragment
/// shader as:
///
/// `content_uv = (surface_uv - 0.5) * scale + 0.5`
///
/// and build the camera homography over the smaller raw-overlay/content
/// surface. This mirrors the geometry contract without depending on any
/// downstream effect stack.
pub fn full_view_content_uv_scale(
    full_view_overlay_overscan: f32,
    raw_overlay_overscan: f32,
) -> Result<f32, CameraModelError> {
    if !full_view_overlay_overscan.is_finite()
        || !raw_overlay_overscan.is_finite()
        || full_view_overlay_overscan <= 0.0
        || raw_overlay_overscan <= 0.0
    {
        return Err(CameraModelError::InvalidProjectionSurface);
    }

    Ok((full_view_overlay_overscan.max(1.0) / raw_overlay_overscan.max(1.0)).max(1.0))
}

/// Project a tracking-space point through a source camera basis into normalized
/// camera UV.
pub fn project_tracking_point_to_camera_uv(
    camera: CameraBasis,
    intrinsics: CameraIntrinsics,
    tracking_point: Vec3,
) -> Result<Vec2, CameraModelError> {
    if !camera.is_valid() {
        return Err(CameraModelError::InvalidPoseRotation);
    }
    if !intrinsics.is_valid() {
        return Err(CameraModelError::InvalidSourceIntrinsics);
    }

    let local = tracking_point - camera.position;
    let camera_point = Vec3::new(
        local.dot(camera.right),
        local.dot(camera.up),
        local.dot(camera.forward),
    );
    let pixel = project_camera_point(intrinsics, camera_point)?;
    Ok(Vec2::new(
        pixel.x / intrinsics.image_size.width as f32,
        pixel.y / intrinsics.image_size.height as f32,
    ))
}

/// Project a tracking-space point through an OpenXR display-eye view into
/// fullscreen shader UV.
///
/// The returned UV matches the Quest composite example's fullscreen triangle:
/// `x=0` is screen left and `y=0` is screen top. This is distinct from raw
/// OpenXR tangent space, where positive Y is up.
pub fn project_tracking_point_to_eye_screen_uv(
    eye: CameraBasis,
    tan_left: f32,
    tan_right: f32,
    tan_down: f32,
    tan_up: f32,
    tracking_point: Vec3,
) -> Result<Vec2, CameraModelError> {
    if !eye.is_valid() {
        return Err(CameraModelError::InvalidPoseRotation);
    }
    if !tan_left.is_finite()
        || !tan_right.is_finite()
        || !tan_down.is_finite()
        || !tan_up.is_finite()
        || tan_right <= tan_left
        || tan_up <= tan_down
    {
        return Err(CameraModelError::InvalidProjectionSurface);
    }

    let local = tracking_point - eye.position;
    let z = local.dot(eye.forward);
    if z <= 0.0 {
        return Err(CameraModelError::PointBehindCamera);
    }

    let tan_x = local.dot(eye.right) / z;
    let tan_y = local.dot(eye.up) / z;
    Ok(Vec2::new(
        (tan_x - tan_left) / (tan_right - tan_left),
        (tan_up - tan_y) / (tan_up - tan_down),
    ))
}

/// Compute homography rows from a unit preview surface to source-camera UV.
pub fn surface_to_camera_uv_homography(
    surface_corners: [Vec3; 4],
    camera: CameraBasis,
    intrinsics: CameraIntrinsics,
) -> Result<[[f32; 3]; 3], CameraModelError> {
    if !surface_corners.iter().all(|corner| corner.is_finite()) {
        return Err(CameraModelError::InvalidProjectionSurface);
    }

    let mut projected = [Vec2::ZERO; 4];
    for (index, corner) in surface_corners.iter().copied().enumerate() {
        projected[index] = project_tracking_point_to_camera_uv(camera, intrinsics, corner)?;
    }

    homography_from_unit_square(projected).ok_or(CameraModelError::InvalidProjectionSurface)
}

/// Compute homography rows from a unit preview surface to fullscreen display
/// UV for one OpenXR display eye.
pub fn surface_to_eye_screen_uv_homography(
    surface_corners: [Vec3; 4],
    eye: CameraBasis,
    tan_left: f32,
    tan_right: f32,
    tan_down: f32,
    tan_up: f32,
) -> Result<[[f32; 3]; 3], CameraModelError> {
    if !surface_corners.iter().all(|corner| corner.is_finite()) {
        return Err(CameraModelError::InvalidProjectionSurface);
    }

    let mut projected = [Vec2::ZERO; 4];
    for (index, corner) in surface_corners.iter().copied().enumerate() {
        projected[index] = project_tracking_point_to_eye_screen_uv(
            eye, tan_left, tan_right, tan_down, tan_up, corner,
        )?;
    }

    homography_from_unit_square(projected).ok_or(CameraModelError::InvalidProjectionSurface)
}

/// Compose a display-screen UV to source-camera UV homography from the shared
/// head-anchored content surface mappings.
pub fn screen_to_camera_uv_homography(
    surface_to_screen_uv: [[f32; 3]; 3],
    surface_to_camera_uv: [[f32; 3]; 3],
) -> Result<[[f32; 3]; 3], CameraModelError> {
    let screen_to_surface_uv = invert_homography(surface_to_screen_uv)
        .ok_or(CameraModelError::InvalidProjectionSurface)?;
    multiply_homographies(surface_to_camera_uv, screen_to_surface_uv)
        .ok_or(CameraModelError::InvalidProjectionSurface)
}

/// Project a camera-space point into pixel coordinates.
pub fn project_camera_point(
    intrinsics: CameraIntrinsics,
    camera_point: Vec3,
) -> Result<Vec2, CameraModelError> {
    if !intrinsics.is_valid() {
        return Err(CameraModelError::InvalidSourceIntrinsics);
    }
    if camera_point.z <= 0.0 {
        return Err(CameraModelError::PointBehindCamera);
    }

    Ok(Vec2::new(
        (camera_point.x * intrinsics.focal_length_px.x / camera_point.z)
            + intrinsics.principal_point_px.x,
        (camera_point.y * intrinsics.focal_length_px.y / camera_point.z)
            + intrinsics.principal_point_px.y,
    ))
}

/// Back-project a pixel and metric depth into camera-space coordinates.
pub fn back_project_pixel(
    intrinsics: CameraIntrinsics,
    pixel: Vec2,
    depth_meters: f32,
) -> Result<Vec3, CameraModelError> {
    if !intrinsics.is_valid() {
        return Err(CameraModelError::InvalidSourceIntrinsics);
    }
    if !depth_meters.is_finite() || depth_meters.abs() <= f32::EPSILON {
        return Err(CameraModelError::ZeroDepth);
    }

    Ok(Vec3::new(
        (pixel.x - intrinsics.principal_point_px.x) * depth_meters / intrinsics.focal_length_px.x,
        (pixel.y - intrinsics.principal_point_px.y) * depth_meters / intrinsics.focal_length_px.y,
        depth_meters,
    ))
}
