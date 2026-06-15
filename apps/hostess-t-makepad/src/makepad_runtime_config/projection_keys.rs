//! Projection runtime key registry.
//!
//! This module keeps the canonical projection setting keys and ownership
//! metadata separate from resolver behavior and compatibility aliases.

use super::{ProjectionRuntimeKeyOwner, RuntimeKeyDefinition, RuntimeKeyDomain, RuntimeValueKind};

pub const KEY_CAMERA_PROJECTION_MODE: &str = "camera_projection_mode";
pub const KEY_PROJECTION_GEOMETRY_PROFILE: &str = "projection_geometry_profile";
pub const KEY_SYNTHETIC_PROJECTION_PROFILE: &str = "synthetic_projection_profile";
pub const KEY_PROJECTION_SCALE: &str = "projection_scale";
pub const KEY_PROJECTION_DEPTH_METERS: &str = "projection_depth_meters";
pub const KEY_CAMERA_PROJECTION_FOV_Y_DEGREES: &str = "camera_projection_fov_y_degrees";
pub const KEY_CAMERA_PREVIEW_FOV_Y_DEGREES: &str = "camera_preview_fov_y_degrees";
pub const KEY_CAMERA_PREVIEW_OFFSET_Y_METERS: &str = "camera_preview_offset_y_meters";
pub const KEY_CAMERA_RAW_OVERLAY_OVERSCAN: &str = "camera_raw_overlay_overscan";
pub const KEY_PROJECTION_AREA_SCALE_UV: &str = "projection_area_scale_uv";
pub const KEY_PROJECTION_AREA_SCALE_X: &str = "projection_area_scale_x";
pub const KEY_PROJECTION_AREA_SCALE_Y: &str = "projection_area_scale_y";
pub const KEY_PROJECTION_AREA_OFFSET_X_UV: &str = "projection_area_offset_x_uv";
pub const KEY_PROJECTION_AREA_OFFSET_Y_UV: &str = "projection_area_offset_y_uv";
pub const KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV: &str = "projection_area_left_offset_x_uv";
pub const KEY_PROJECTION_AREA_LEFT_OFFSET_Y_UV: &str = "projection_area_left_offset_y_uv";
pub const KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV: &str = "projection_area_right_offset_x_uv";
pub const KEY_PROJECTION_AREA_RIGHT_OFFSET_Y_UV: &str = "projection_area_right_offset_y_uv";
pub const KEY_PROJECTION_AREA_RADIUS_X_UV: &str = "projection_area_radius_x_uv";
pub const KEY_PROJECTION_AREA_RADIUS_Y_UV: &str = "projection_area_radius_y_uv";
pub const KEY_PROJECTION_AREA_CORNER_RADIUS_UV: &str = "projection_area_corner_radius_uv";
pub const KEY_PROJECTION_AREA_OPACITY: &str = "projection_area_opacity";
pub const KEY_PROJECTION_BORDER_OPACITY: &str = "projection_border_opacity";
pub const KEY_PROJECTION_BORDER_POLICY: &str = "projection_border_policy";
pub const KEY_PROJECTION_TARGET_OFFSET_X_UV: &str = "projection_target_offset_x_uv";
pub const KEY_PROJECTION_TARGET_OFFSET_Y_UV: &str = "projection_target_offset_y_uv";
pub const KEY_PROJECTION_TARGET_SCALE: &str = "projection_target_scale";
pub const KEY_PROJECTION_TARGET_JOYSTICK_CONTROLS: &str = "projection_target_joystick_controls";
pub const KEY_PROJECTION_TARGET_BREATH_CONTROLS: &str = "projection_target_breath_controls";
pub const KEY_PROJECTION_TARGET_BREATH_STREAM: &str = "projection_target_breath_stream";
pub const KEY_PROJECTION_TARGET_BREATH_SCALE_MODE: &str = "projection_target_breath_scale_mode";
pub const KEY_PROJECTION_TARGET_BREATH_MIN_SCALE: &str = "projection_target_breath_min_scale";
pub const KEY_PROJECTION_TARGET_BREATH_MAX_SCALE: &str = "projection_target_breath_max_scale";
pub const KEY_PROJECTION_TARGET_BREATH_INHALE_SECONDS_MIN_TO_MAX: &str =
    "projection_target_breath_inhale_seconds_min_to_max";
pub const KEY_PROJECTION_TARGET_BREATH_EXHALE_SECONDS_MAX_TO_MIN: &str =
    "projection_target_breath_exhale_seconds_max_to_min";
pub const KEY_PROJECTION_TARGET_BREATH_SMOOTHING_ALPHA: &str =
    "projection_target_breath_smoothing_alpha";
pub const KEY_PROJECTION_TARGET_BREATH_INVERT: &str = "projection_target_breath_invert";
pub const KEY_PROJECTION_TARGET_BREATH_MIN_QUALITY: &str = "projection_target_breath_min_quality";
pub const KEY_PROCESSING_LAYER: &str = "processing_layer";
pub const KEY_CAMERA_BLUR_RADIUS_PX: &str = "camera_blur_radius_px";
pub const KEY_PERIPHERAL_STRETCH_MODE: &str = "peripheral_stretch_mode";
pub const KEY_PERIPHERAL_STRETCH_CORE_SCALE: &str = "peripheral_stretch_core_scale";
pub const KEY_PERIPHERAL_STRETCH_EDGE_INSET_UV: &str = "peripheral_stretch_edge_inset_uv";
pub const KEY_PERIPHERAL_STRETCH_MAX_INSET_UV: &str = "peripheral_stretch_max_inset_uv";
pub const KEY_PERIPHERAL_STRETCH_CURVE: &str = "peripheral_stretch_curve";
pub const KEY_PERIPHERAL_STRETCH_INNER_BLEND_UV: &str = "peripheral_stretch_inner_blend_uv";
pub const KEY_PERIPHERAL_STRETCH_BLEND_CURVE: &str = "peripheral_stretch_blend_curve";
pub const KEY_PERIPHERAL_STRETCH_BLEND_MODE: &str = "peripheral_stretch_blend_mode";
pub const KEY_PERIPHERAL_STRETCH_CORNER_MODE: &str = "peripheral_stretch_corner_mode";
pub const KEY_PERIPHERAL_STRETCH_DEBUG: &str = "peripheral_stretch_debug";
pub const KEY_PROJECTION_ALPHA_MODE: &str = "projection_alpha_mode";
pub const KEY_PROJECTION_ALPHA_SCALE: &str = "projection_alpha_scale";
pub const KEY_PROJECTION_ALPHA_BIAS: &str = "projection_alpha_bias";
pub const KEY_SOURCE_EYE_MAPPING: &str = "source_eye_mapping";
pub const KEY_SOURCE_TEXTURE_ROTATION: &str = "source_texture_rotation";
pub const KEY_SOURCE_TEXTURE_FLIP_X: &str = "source_texture_flip_x";
pub const KEY_SOURCE_TEXTURE_FLIP_Y: &str = "source_texture_flip_y";
pub const KEY_SOURCE_TEXTURE_MIRROR: &str = "source_texture_mirror";
pub const KEY_SOURCE_TEXTURE_TRANSFORM_SOURCE: &str = "source_texture_transform_source";
pub const KEY_SOURCE_TEXTURE_TRANSFORM_REASON: &str = "source_texture_transform_reason";
pub const KEY_LEFT_SOURCE_TEXTURE_TRANSFORM_SOURCE: &str = "left_source_texture_transform_source";
pub const KEY_RIGHT_SOURCE_TEXTURE_TRANSFORM_SOURCE: &str = "right_source_texture_transform_source";
pub const KEY_SOURCE_VISIBLE_RECT_X_UV: &str = "source_visible_rect_x_uv";
pub const KEY_SOURCE_VISIBLE_RECT_Y_UV: &str = "source_visible_rect_y_uv";
pub const KEY_SOURCE_VISIBLE_RECT_WIDTH_UV: &str = "source_visible_rect_width_uv";
pub const KEY_SOURCE_VISIBLE_RECT_HEIGHT_UV: &str = "source_visible_rect_height_uv";

/// Canonical projection runtime keys.
pub const PROJECTION_RUNTIME_KEY_DEFINITIONS: &[RuntimeKeyDefinition] = &[
    projection_key(
        KEY_CAMERA_PROJECTION_MODE,
        ProjectionRuntimeKeyOwner::Geometry,
        RuntimeValueKind::Text,
        "Projection placement mode selected by the runtime profile.",
    ),
    projection_key(
        KEY_PROJECTION_GEOMETRY_PROFILE,
        ProjectionRuntimeKeyOwner::Geometry,
        RuntimeValueKind::Text,
        "Named projection geometry profile used for renderer and analyzer parity.",
    ),
    projection_key(
        KEY_SYNTHETIC_PROJECTION_PROFILE,
        ProjectionRuntimeKeyOwner::Geometry,
        RuntimeValueKind::Text,
        "Named projection profile embedded in synthetic source metadata.",
    ),
    projection_key(
        KEY_PROJECTION_SCALE,
        ProjectionRuntimeKeyOwner::Geometry,
        RuntimeValueKind::Float,
        "Legacy projection scale retained as an explicit non-depth tuning key.",
    ),
    projection_key(
        KEY_PROJECTION_DEPTH_METERS,
        ProjectionRuntimeKeyOwner::Geometry,
        RuntimeValueKind::Float,
        "Head-anchored projection surface depth in meters.",
    ),
    projection_key(
        KEY_CAMERA_PROJECTION_FOV_Y_DEGREES,
        ProjectionRuntimeKeyOwner::Geometry,
        RuntimeValueKind::Float,
        "Projection camera vertical field of view in degrees.",
    ),
    projection_key(
        KEY_CAMERA_PREVIEW_FOV_Y_DEGREES,
        ProjectionRuntimeKeyOwner::Geometry,
        RuntimeValueKind::Float,
        "Preview camera vertical field of view in degrees.",
    ),
    projection_key(
        KEY_CAMERA_PREVIEW_OFFSET_Y_METERS,
        ProjectionRuntimeKeyOwner::Geometry,
        RuntimeValueKind::Float,
        "Preview camera vertical offset in meters.",
    ),
    projection_key(
        KEY_CAMERA_RAW_OVERLAY_OVERSCAN,
        ProjectionRuntimeKeyOwner::Geometry,
        RuntimeValueKind::Float,
        "Raw camera overlay overscan factor.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_SCALE_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Uniform projection-area scale in display-eye screen UV.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_SCALE_X,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Horizontal projection-area scale in display-eye screen UV.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_SCALE_Y,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Vertical projection-area scale in display-eye screen UV.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_OFFSET_X_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Global projection-area horizontal offset; positive X moves right.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_OFFSET_Y_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Global projection-area vertical offset; positive Y moves down.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Left-eye projection-area horizontal offset; positive X moves right.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_LEFT_OFFSET_Y_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Left-eye projection-area vertical offset; positive Y moves down.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Right-eye projection-area horizontal offset; positive X moves right.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_RIGHT_OFFSET_Y_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Right-eye projection-area vertical offset; positive Y moves down.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_RADIUS_X_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Projection-area horizontal radius in display-eye screen UV.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_RADIUS_Y_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Projection-area vertical radius in display-eye screen UV.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_CORNER_RADIUS_UV,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Projection-area corner radius in display-eye screen UV.",
    ),
    projection_key(
        KEY_PROJECTION_AREA_OPACITY,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Projection-area source opacity.",
    ),
    projection_key(
        KEY_PROJECTION_BORDER_OPACITY,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Float,
        "Projection-area border opacity.",
    ),
    projection_key(
        KEY_PROJECTION_BORDER_POLICY,
        ProjectionRuntimeKeyOwner::ProjectionArea,
        RuntimeValueKind::Text,
        "Projection-area border fill policy.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_OFFSET_X_UV,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Float,
        "Runtime horizontal offset applied to the metadata or fallback target footprint.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_OFFSET_Y_UV,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Float,
        "Runtime vertical offset applied to the metadata or fallback target footprint.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_SCALE,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Float,
        "Runtime uniform scale applied around the target-footprint center.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_JOYSTICK_CONTROLS,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Text,
        "OpenXR controller target-footprint control mode: off, offset-scale, or horizontal-offset.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_CONTROLS,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Text,
        "Broker breath target-footprint control mode.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_STREAM,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Text,
        "Broker stream id that provides normalized breath volume for target-footprint scale control.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_SCALE_MODE,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Text,
        "Projection-target breath scale processing mode: volume or state-ramp.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_MIN_SCALE,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Float,
        "Projection-target scale mapped from breath volume 0.0 before optional inversion.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_MAX_SCALE,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Float,
        "Projection-target scale mapped from breath volume 1.0 before optional inversion.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_INHALE_SECONDS_MIN_TO_MAX,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Float,
        "Seconds a constant inhale state takes to ramp projection-target scale from min to max.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_EXHALE_SECONDS_MAX_TO_MIN,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Float,
        "Seconds a constant exhale state takes to ramp projection-target scale from max to min.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_SMOOTHING_ALPHA,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Float,
        "Exponential smoothing alpha applied to broker breath target-scale updates.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_INVERT,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Bool,
        "Whether breath volume is inverted before mapping it to projection-target scale.",
    ),
    projection_key(
        KEY_PROJECTION_TARGET_BREATH_MIN_QUALITY,
        ProjectionRuntimeKeyOwner::TargetFootprint,
        RuntimeValueKind::Float,
        "Minimum broker breath quality01 accepted for projection-target scale updates.",
    ),
    projection_key(
        KEY_PROCESSING_LAYER,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Text,
        "Source-agnostic processing layer applied after target-footprint placement.",
    ),
    projection_key(
        KEY_CAMERA_BLUR_RADIUS_PX,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Float,
        "Diagnostic blur radius in source pixels for the blur processing layer.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_MODE,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Text,
        "Peripheral-stretch exterior fill mode.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_CORE_SCALE,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Float,
        "Scale of the coherent target-footprint core used by peripheral stretch.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_EDGE_INSET_UV,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Float,
        "Optional source sample inset from the target-footprint edge for peripheral stretch.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_MAX_INSET_UV,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Float,
        "Maximum permitted target-edge inset for peripheral stretch.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_CURVE,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Float,
        "Curve parameter reserved for non-linear peripheral stretch falloff.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_INNER_BLEND_UV,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Float,
        "Width of the target-footprint inner transition band for peripheral stretch.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_BLEND_CURVE,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Float,
        "Curve parameter for peripheral-stretch target inner-band blending.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_BLEND_MODE,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Text,
        "Peripheral-stretch target-footprint blend mode.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_CORNER_MODE,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Text,
        "Corner handling mode for target-footprint peripheral stretch.",
    ),
    projection_key(
        KEY_PERIPHERAL_STRETCH_DEBUG,
        ProjectionRuntimeKeyOwner::RendererPolicy,
        RuntimeValueKind::Text,
        "Debug overlay mode for peripheral-stretch exterior samples.",
    ),
    projection_key(
        KEY_PROJECTION_ALPHA_MODE,
        ProjectionRuntimeKeyOwner::Alpha,
        RuntimeValueKind::Text,
        "Projection alpha interpretation mode.",
    ),
    projection_key(
        KEY_PROJECTION_ALPHA_SCALE,
        ProjectionRuntimeKeyOwner::Alpha,
        RuntimeValueKind::Float,
        "Projection alpha scale.",
    ),
    projection_key(
        KEY_PROJECTION_ALPHA_BIAS,
        ProjectionRuntimeKeyOwner::Alpha,
        RuntimeValueKind::Float,
        "Projection alpha bias.",
    ),
    projection_key(
        KEY_SOURCE_EYE_MAPPING,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Text,
        "Mapping from display eye to sampled source eye.",
    ),
    projection_key(
        KEY_SOURCE_TEXTURE_ROTATION,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Text,
        "Source texture rotation before projection sampling.",
    ),
    projection_key(
        KEY_SOURCE_TEXTURE_FLIP_X,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Bool,
        "Source texture horizontal flip before projection sampling.",
    ),
    projection_key(
        KEY_SOURCE_TEXTURE_FLIP_Y,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Bool,
        "Source texture vertical flip before projection sampling.",
    ),
    projection_key(
        KEY_SOURCE_TEXTURE_MIRROR,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Bool,
        "Source texture mirror operation before projection sampling.",
    ),
    projection_key(
        KEY_SOURCE_TEXTURE_TRANSFORM_SOURCE,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Text,
        "Owner that supplied the source texture transform.",
    ),
    projection_key(
        KEY_SOURCE_TEXTURE_TRANSFORM_REASON,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Text,
        "Reason for the selected source texture transform.",
    ),
    projection_key(
        KEY_LEFT_SOURCE_TEXTURE_TRANSFORM_SOURCE,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Text,
        "Owner that supplied the left-eye source texture transform.",
    ),
    projection_key(
        KEY_RIGHT_SOURCE_TEXTURE_TRANSFORM_SOURCE,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Text,
        "Owner that supplied the right-eye source texture transform.",
    ),
    projection_key(
        KEY_SOURCE_VISIBLE_RECT_X_UV,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Float,
        "Source-visible rectangle X coordinate in normalized source UV.",
    ),
    projection_key(
        KEY_SOURCE_VISIBLE_RECT_Y_UV,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Float,
        "Source-visible rectangle Y coordinate in normalized source UV.",
    ),
    projection_key(
        KEY_SOURCE_VISIBLE_RECT_WIDTH_UV,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Float,
        "Source-visible rectangle width in normalized source UV.",
    ),
    projection_key(
        KEY_SOURCE_VISIBLE_RECT_HEIGHT_UV,
        ProjectionRuntimeKeyOwner::SourceSampling,
        RuntimeValueKind::Float,
        "Source-visible rectangle height in normalized source UV.",
    ),
];

const fn projection_key(
    key: &'static str,
    owner: ProjectionRuntimeKeyOwner,
    value_kind: RuntimeValueKind,
    description: &'static str,
) -> RuntimeKeyDefinition {
    RuntimeKeyDefinition {
        key,
        domain: RuntimeKeyDomain::Projection,
        owner,
        value_kind,
        description,
    }
}

pub fn projection_runtime_key_definition(key: &str) -> Option<&'static RuntimeKeyDefinition> {
    PROJECTION_RUNTIME_KEY_DEFINITIONS
        .iter()
        .find(|definition| definition.key == key)
}
