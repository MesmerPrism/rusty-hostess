//! Projection runtime compatibility aliases.
//!
//! Keep canonical runtime keys and parsing behavior in the parent module. This
//! child module contains only accepted external spellings so compatibility
//! pruning can be audited without expanding the primary runtime config file.

use super::*;

/// Current external spellings for projection runtime keys.
///
/// These are accepted entry-point names for launch profiles, Android
/// properties, and environment variables. Legacy `rustyxr`/`RUSTY_XR` spellings
/// are intentionally not registered in this active Makepad settings surface.
pub const PROJECTION_RUNTIME_KEY_ALIASES: &[RuntimeKeyAlias] = &[
    launch_alias("makepad.cameraProjectionMode", KEY_CAMERA_PROJECTION_MODE),
    launch_alias(
        "makepad.cameraProjectionGeometryProfile",
        KEY_PROJECTION_GEOMETRY_PROFILE,
    ),
    launch_alias(
        "makepad.brokerH264ProjectionGeometryProfile",
        KEY_PROJECTION_GEOMETRY_PROFILE,
    ),
    launch_alias(
        "makepad.brokerH264SyntheticProjectionProfile",
        KEY_SYNTHETIC_PROJECTION_PROFILE,
    ),
    launch_alias("makepad.cameraProjectionScale", KEY_PROJECTION_SCALE),
    launch_alias("makepad.projectionDepthMeters", KEY_PROJECTION_DEPTH_METERS),
    launch_alias(
        "makepad.cameraProjectionFovYDegrees",
        KEY_CAMERA_PROJECTION_FOV_Y_DEGREES,
    ),
    launch_alias(
        "makepad.cameraPreviewFovYDegrees",
        KEY_CAMERA_PREVIEW_FOV_Y_DEGREES,
    ),
    launch_alias(
        "makepad.cameraPreviewOffsetYMeters",
        KEY_CAMERA_PREVIEW_OFFSET_Y_METERS,
    ),
    launch_alias(
        "makepad.cameraRawOverlayOverscan",
        KEY_CAMERA_RAW_OVERLAY_OVERSCAN,
    ),
    launch_alias(
        "makepad.projectionAreaScaleUv",
        KEY_PROJECTION_AREA_SCALE_UV,
    ),
    launch_alias("makepad.projectionAreaScaleX", KEY_PROJECTION_AREA_SCALE_X),
    launch_alias("makepad.projectionAreaScaleY", KEY_PROJECTION_AREA_SCALE_Y),
    launch_alias(
        "makepad.projectionAreaOffsetXUv",
        KEY_PROJECTION_AREA_OFFSET_X_UV,
    ),
    launch_alias(
        "makepad.projectionAreaOffsetYUv",
        KEY_PROJECTION_AREA_OFFSET_Y_UV,
    ),
    launch_alias(
        "makepad.projectionAreaLeftOffsetXUv",
        KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV,
    ),
    launch_alias(
        "makepad.projectionAreaLeftOffsetYUv",
        KEY_PROJECTION_AREA_LEFT_OFFSET_Y_UV,
    ),
    launch_alias(
        "makepad.projectionAreaRightOffsetXUv",
        KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV,
    ),
    launch_alias(
        "makepad.projectionAreaRightOffsetYUv",
        KEY_PROJECTION_AREA_RIGHT_OFFSET_Y_UV,
    ),
    launch_alias(
        "makepad.projectionAreaRadiusXUv",
        KEY_PROJECTION_AREA_RADIUS_X_UV,
    ),
    launch_alias(
        "makepad.projectionAreaRadiusYUv",
        KEY_PROJECTION_AREA_RADIUS_Y_UV,
    ),
    launch_alias(
        "makepad.projectionAreaCornerRadiusUv",
        KEY_PROJECTION_AREA_CORNER_RADIUS_UV,
    ),
    launch_alias("makepad.projectionAreaOpacity", KEY_PROJECTION_AREA_OPACITY),
    launch_alias(
        "makepad.projectionBorderOpacity",
        KEY_PROJECTION_BORDER_OPACITY,
    ),
    launch_alias(
        "makepad.projectionBorderPolicy",
        KEY_PROJECTION_BORDER_POLICY,
    ),
    launch_alias(
        "makepad.projectionTargetOffsetXUv",
        KEY_PROJECTION_TARGET_OFFSET_X_UV,
    ),
    launch_alias(
        "makepad.projectionTargetOffsetYUv",
        KEY_PROJECTION_TARGET_OFFSET_Y_UV,
    ),
    launch_alias("makepad.projectionTargetScale", KEY_PROJECTION_TARGET_SCALE),
    launch_alias(
        "makepad.projectionTargetJoystickControls",
        KEY_PROJECTION_TARGET_JOYSTICK_CONTROLS,
    ),
    launch_alias(
        "makepad.projectionTargetBreathControls",
        KEY_PROJECTION_TARGET_BREATH_CONTROLS,
    ),
    launch_alias(
        "makepad.projectionTargetBreathStream",
        KEY_PROJECTION_TARGET_BREATH_STREAM,
    ),
    launch_alias(
        "makepad.projectionTargetBreathMinScale",
        KEY_PROJECTION_TARGET_BREATH_MIN_SCALE,
    ),
    launch_alias(
        "makepad.projectionTargetBreathMaxScale",
        KEY_PROJECTION_TARGET_BREATH_MAX_SCALE,
    ),
    launch_alias(
        "makepad.projectionTargetBreathSmoothingAlpha",
        KEY_PROJECTION_TARGET_BREATH_SMOOTHING_ALPHA,
    ),
    launch_alias(
        "makepad.projectionTargetBreathInvert",
        KEY_PROJECTION_TARGET_BREATH_INVERT,
    ),
    launch_alias(
        "makepad.projectionTargetBreathMinQuality",
        KEY_PROJECTION_TARGET_BREATH_MIN_QUALITY,
    ),
    launch_alias("makepad.processingLayer", KEY_PROCESSING_LAYER),
    launch_alias("makepad.cameraBlurRadiusPx", KEY_CAMERA_BLUR_RADIUS_PX),
    launch_alias("makepad.peripheralStretchMode", KEY_PERIPHERAL_STRETCH_MODE),
    launch_alias(
        "makepad.peripheralStretchCoreScale",
        KEY_PERIPHERAL_STRETCH_CORE_SCALE,
    ),
    launch_alias(
        "makepad.peripheralStretchEdgeInsetUv",
        KEY_PERIPHERAL_STRETCH_EDGE_INSET_UV,
    ),
    launch_alias(
        "makepad.peripheralStretchMaxInsetUv",
        KEY_PERIPHERAL_STRETCH_MAX_INSET_UV,
    ),
    launch_alias(
        "makepad.peripheralStretchCurve",
        KEY_PERIPHERAL_STRETCH_CURVE,
    ),
    launch_alias(
        "makepad.peripheralStretchInnerBlendUv",
        KEY_PERIPHERAL_STRETCH_INNER_BLEND_UV,
    ),
    launch_alias(
        "makepad.peripheralStretchBlendCurve",
        KEY_PERIPHERAL_STRETCH_BLEND_CURVE,
    ),
    launch_alias(
        "makepad.peripheralStretchBlendMode",
        KEY_PERIPHERAL_STRETCH_BLEND_MODE,
    ),
    launch_alias(
        "makepad.peripheralStretchCornerMode",
        KEY_PERIPHERAL_STRETCH_CORNER_MODE,
    ),
    launch_alias(
        "makepad.peripheralStretchDebug",
        KEY_PERIPHERAL_STRETCH_DEBUG,
    ),
    launch_alias("makepad.projectionAlphaMode", KEY_PROJECTION_ALPHA_MODE),
    launch_alias("makepad.projectionAlphaScale", KEY_PROJECTION_ALPHA_SCALE),
    launch_alias("makepad.projectionAlphaBias", KEY_PROJECTION_ALPHA_BIAS),
    launch_alias("makepad.cameraSourceEyeMapping", KEY_SOURCE_EYE_MAPPING),
    launch_alias("makepad.cameraTextureRotation", KEY_SOURCE_TEXTURE_ROTATION),
    launch_alias("makepad.cameraTextureFlipX", KEY_SOURCE_TEXTURE_FLIP_X),
    launch_alias("makepad.cameraTextureFlipY", KEY_SOURCE_TEXTURE_FLIP_Y),
    launch_alias("makepad.cameraTextureMirror", KEY_SOURCE_TEXTURE_MIRROR),
    launch_alias(
        "makepad.cameraTextureTransformSource",
        KEY_SOURCE_TEXTURE_TRANSFORM_SOURCE,
    ),
    launch_alias(
        "makepad.cameraTextureTransformReason",
        KEY_SOURCE_TEXTURE_TRANSFORM_REASON,
    ),
    launch_alias(
        "makepad.leftCameraTextureTransformSource",
        KEY_LEFT_SOURCE_TEXTURE_TRANSFORM_SOURCE,
    ),
    launch_alias(
        "makepad.rightCameraTextureTransformSource",
        KEY_RIGHT_SOURCE_TEXTURE_TRANSFORM_SOURCE,
    ),
    property_alias(
        "debug.rustyquest.makepad.camera.projection.mode",
        KEY_CAMERA_PROJECTION_MODE,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.geometry.profile",
        KEY_PROJECTION_GEOMETRY_PROFILE,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.scale",
        KEY_PROJECTION_SCALE,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.depth.meters",
        KEY_PROJECTION_DEPTH_METERS,
    ),
    property_alias(
        "debug.rustyquest.makepad.camera.projection.fov.y.degrees",
        KEY_CAMERA_PROJECTION_FOV_Y_DEGREES,
    ),
    property_alias(
        "debug.rustyquest.makepad.camera.preview.fov.y.degrees",
        KEY_CAMERA_PREVIEW_FOV_Y_DEGREES,
    ),
    property_alias(
        "debug.rustyquest.makepad.camera.preview.offset.y.meters",
        KEY_CAMERA_PREVIEW_OFFSET_Y_METERS,
    ),
    property_alias(
        "debug.rustyquest.makepad.camera.raw.overlay.overscan",
        KEY_CAMERA_RAW_OVERLAY_OVERSCAN,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.scale.uv",
        KEY_PROJECTION_AREA_SCALE_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.scale.x",
        KEY_PROJECTION_AREA_SCALE_X,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.scale.y",
        KEY_PROJECTION_AREA_SCALE_Y,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.offset.x.uv",
        KEY_PROJECTION_AREA_OFFSET_X_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.offset.y.uv",
        KEY_PROJECTION_AREA_OFFSET_Y_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.left.offset.x.uv",
        KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.left.offset.y.uv",
        KEY_PROJECTION_AREA_LEFT_OFFSET_Y_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.right.offset.x.uv",
        KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.right.offset.y.uv",
        KEY_PROJECTION_AREA_RIGHT_OFFSET_Y_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.radius.x.uv",
        KEY_PROJECTION_AREA_RADIUS_X_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.radius.y.uv",
        KEY_PROJECTION_AREA_RADIUS_Y_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.corner.radius.uv",
        KEY_PROJECTION_AREA_CORNER_RADIUS_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.area.opacity",
        KEY_PROJECTION_AREA_OPACITY,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.border.opacity",
        KEY_PROJECTION_BORDER_OPACITY,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.border.policy",
        KEY_PROJECTION_BORDER_POLICY,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.offset.x.uv",
        KEY_PROJECTION_TARGET_OFFSET_X_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.offset.y.uv",
        KEY_PROJECTION_TARGET_OFFSET_Y_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.scale",
        KEY_PROJECTION_TARGET_SCALE,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.joystick.controls",
        KEY_PROJECTION_TARGET_JOYSTICK_CONTROLS,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.breath.controls",
        KEY_PROJECTION_TARGET_BREATH_CONTROLS,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.breath.stream",
        KEY_PROJECTION_TARGET_BREATH_STREAM,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.breath.min.scale",
        KEY_PROJECTION_TARGET_BREATH_MIN_SCALE,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.breath.max.scale",
        KEY_PROJECTION_TARGET_BREATH_MAX_SCALE,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.breath.smoothing.alpha",
        KEY_PROJECTION_TARGET_BREATH_SMOOTHING_ALPHA,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.breath.invert",
        KEY_PROJECTION_TARGET_BREATH_INVERT,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.target.breath.min.quality",
        KEY_PROJECTION_TARGET_BREATH_MIN_QUALITY,
    ),
    property_alias(
        "debug.rustyquest.makepad.processing.layer",
        KEY_PROCESSING_LAYER,
    ),
    property_alias(
        "debug.rustyquest.makepad.camera.blur.radius.px",
        KEY_CAMERA_BLUR_RADIUS_PX,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.mode",
        KEY_PERIPHERAL_STRETCH_MODE,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.core.scale",
        KEY_PERIPHERAL_STRETCH_CORE_SCALE,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.edge.inset.uv",
        KEY_PERIPHERAL_STRETCH_EDGE_INSET_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.max.inset.uv",
        KEY_PERIPHERAL_STRETCH_MAX_INSET_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.curve",
        KEY_PERIPHERAL_STRETCH_CURVE,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.inner.blend.uv",
        KEY_PERIPHERAL_STRETCH_INNER_BLEND_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.blend.curve",
        KEY_PERIPHERAL_STRETCH_BLEND_CURVE,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.blend.mode",
        KEY_PERIPHERAL_STRETCH_BLEND_MODE,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.corner.mode",
        KEY_PERIPHERAL_STRETCH_CORNER_MODE,
    ),
    property_alias(
        "debug.rustyquest.makepad.peripheral.stretch.debug",
        KEY_PERIPHERAL_STRETCH_DEBUG,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.alpha.mode",
        KEY_PROJECTION_ALPHA_MODE,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.alpha.scale",
        KEY_PROJECTION_ALPHA_SCALE,
    ),
    property_alias(
        "debug.rustyquest.makepad.projection.alpha.bias",
        KEY_PROJECTION_ALPHA_BIAS,
    ),
    property_alias(
        "debug.rustyquest.makepad.source.eye.mapping",
        KEY_SOURCE_EYE_MAPPING,
    ),
    property_alias(
        "debug.rustyquest.makepad.source.texture.transform.source",
        KEY_SOURCE_TEXTURE_TRANSFORM_SOURCE,
    ),
    property_alias(
        "debug.rustyquest.makepad.source.visible.rect.x.uv",
        KEY_SOURCE_VISIBLE_RECT_X_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.source.visible.rect.y.uv",
        KEY_SOURCE_VISIBLE_RECT_Y_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.source.visible.rect.width.uv",
        KEY_SOURCE_VISIBLE_RECT_WIDTH_UV,
    ),
    property_alias(
        "debug.rustyquest.makepad.source.visible.rect.height.uv",
        KEY_SOURCE_VISIBLE_RECT_HEIGHT_UV,
    ),
    env_alias(
        "RUSTY_MAKEPAD_PROJECTION_DEPTH_METERS",
        KEY_PROJECTION_DEPTH_METERS,
    ),
    env_alias(
        "RUSTY_MAKEPAD_CAMERA_PREVIEW_FOV_Y_DEGREES",
        KEY_CAMERA_PREVIEW_FOV_Y_DEGREES,
    ),
    env_alias(
        "RUSTY_MAKEPAD_CAMERA_PREVIEW_OFFSET_Y_METERS",
        KEY_CAMERA_PREVIEW_OFFSET_Y_METERS,
    ),
    env_alias(
        "RUSTY_MAKEPAD_CAMERA_RAW_OVERLAY_OVERSCAN",
        KEY_CAMERA_RAW_OVERLAY_OVERSCAN,
    ),
];

pub fn projection_runtime_key_alias(alias: &str) -> Option<&'static RuntimeKeyAlias> {
    PROJECTION_RUNTIME_KEY_ALIASES
        .iter()
        .find(|definition| definition.alias == alias)
}

const fn launch_alias(alias: &'static str, canonical_key: &'static str) -> RuntimeKeyAlias {
    RuntimeKeyAlias {
        alias,
        canonical_key,
        source: RuntimeKeyAliasSource::LaunchExtra,
        status: RuntimeKeyAliasStatus::Current,
        value_transform: RuntimeKeyAliasValueTransform::Identity,
    }
}

const fn property_alias(alias: &'static str, canonical_key: &'static str) -> RuntimeKeyAlias {
    RuntimeKeyAlias {
        alias,
        canonical_key,
        source: RuntimeKeyAliasSource::AndroidProperty,
        status: RuntimeKeyAliasStatus::Current,
        value_transform: RuntimeKeyAliasValueTransform::Identity,
    }
}

const fn env_alias(alias: &'static str, canonical_key: &'static str) -> RuntimeKeyAlias {
    RuntimeKeyAlias {
        alias,
        canonical_key,
        source: RuntimeKeyAliasSource::EnvironmentVariable,
        status: RuntimeKeyAliasStatus::Current,
        value_transform: RuntimeKeyAliasValueTransform::Identity,
    }
}
