use super::*;
use crate::makepad_runtime_config as makepad_config;

pub(super) fn makepad_projection_runtime_resolution_enabled() -> bool {
    hotload_bool(KEY_MAKEPAD_PROJECTION_RUNTIME_RESOLUTION_ENABLED, false)
}

pub(super) fn makepad_projection_runtime_mode_token() -> &'static str {
    if makepad_projection_runtime_resolution_enabled() {
        "resolved-manifest"
    } else {
        "legacy"
    }
}

pub(super) fn makepad_projection_runtime_manifest_lines(
    phase: &str,
    config: &makepad_config::RuntimeConfig,
    tuning: HorizontalAlignmentTuning,
) -> Vec<String> {
    let runtime = makepad_projection_runtime_resolution(config, tuning);
    let mut lines = runtime.manifest_marker_lines("makepad", phase);
    lines.push(format!(
        "RUSTY_MAKEPAD_PROJECTION_RUNTIME schema=rusty.gui.makepad.projection_runtime.v1 phase={} mode={} resolvedManifestConsumptionEnabled={}",
        marker_token(phase),
        makepad_projection_runtime_mode_token(),
        makepad_projection_runtime_resolution_enabled()
    ));
    lines
}

pub(super) fn makepad_projection_runtime_resolution(
    config: &makepad_config::RuntimeConfig,
    tuning: HorizontalAlignmentTuning,
) -> makepad_config::ProjectionRuntimeConfigResolution {
    let mut builder = makepad_config::ProjectionRuntimeConfigBuilder::new();
    builder
        .push_layer(
            "makepad-defaults",
            0,
            makepad_projection_runtime_config_defaults(),
        )
        .expect("manifest owner should be valid");
    builder
        .push_layer(
            "makepad-effective",
            10,
            makepad_projection_runtime_config_effective(config, tuning),
        )
        .expect("manifest owner should be valid");

    let env_config = makepad_projection_runtime_env_config();
    builder
        .push_layer("makepad-env", 20, env_config)
        .expect("manifest owner should be valid");

    let current_property_config = makepad_projection_runtime_android_property_config(
        makepad_config::RuntimeKeyAliasStatus::Current,
    );
    builder
        .push_layer("makepad-android-properties", 30, current_property_config)
        .expect("manifest owner should be valid");

    builder
        .with_aliases(makepad_projection_alias_records())
        .resolve()
}

fn makepad_projection_runtime_env_config() -> makepad_config::RuntimeConfig {
    let values = makepad_config::PROJECTION_RUNTIME_KEY_ALIASES
        .iter()
        .filter(|alias| alias.source == makepad_config::RuntimeKeyAliasSource::EnvironmentVariable)
        .filter_map(|alias| {
            std::env::var(alias.alias)
                .ok()
                .map(|value| (alias.alias, value))
        })
        .collect::<Vec<_>>();
    makepad_projection_runtime_alias_config(
        makepad_config::RuntimeConfigSource::Environment,
        values,
    )
}

fn makepad_projection_runtime_android_property_config(
    status: makepad_config::RuntimeKeyAliasStatus,
) -> makepad_config::RuntimeConfig {
    let values = makepad_config::PROJECTION_RUNTIME_KEY_ALIASES
        .iter()
        .filter(|alias| {
            alias.source == makepad_config::RuntimeKeyAliasSource::AndroidProperty
                && alias.status == status
        })
        .filter_map(|alias| {
            android_system_property_value(alias.alias).map(|value| (alias.alias, value))
        })
        .collect::<Vec<_>>();
    makepad_projection_runtime_alias_config(
        makepad_config::RuntimeConfigSource::AndroidProperty,
        values,
    )
}

fn makepad_projection_runtime_alias_config(
    source: makepad_config::RuntimeConfigSource,
    values: Vec<(&'static str, String)>,
) -> makepad_config::RuntimeConfig {
    let mut config = makepad_config::RuntimeConfig::new();
    for (key, value) in values {
        let Ok(parsed) =
            makepad_config::parse_projection_runtime_pairs(source.clone(), [(key, value.as_str())])
        else {
            continue;
        };
        for setting in parsed.config.iter() {
            config.insert(setting.clone());
        }
    }
    config
}

pub(super) fn makepad_current_projection_runtime_float(
    key: &str,
    fallback: f32,
    min: f32,
    max: f32,
) -> f32 {
    let config = App::runtime_config();
    let legacy = App::legacy_horizontal_alignment_tuning();
    let runtime = makepad_projection_runtime_resolution(&config, legacy);
    makepad_projection_runtime_float(&runtime.resolution, key, fallback, min, max)
}

fn makepad_projection_runtime_float(
    resolution: &makepad_config::RuntimeConfigResolution,
    key: &str,
    fallback: f32,
    min: f32,
    max: f32,
) -> f32 {
    makepad_projection_runtime_optional_float(resolution, key, min, max).unwrap_or(fallback)
}

fn makepad_projection_runtime_optional_float(
    resolution: &makepad_config::RuntimeConfigResolution,
    key: &str,
    min: f32,
    max: f32,
) -> Option<f32> {
    resolution
        .resolved()
        .get(key)
        .and_then(makepad_config::RuntimeValue::as_float)
        .filter(|value| value.is_finite())
        .map(|value| value.clamp(f64::from(min), f64::from(max)) as f32)
}

fn makepad_projection_runtime_text<'a>(
    resolution: &'a makepad_config::RuntimeConfigResolution,
    key: &str,
) -> Option<&'a str> {
    resolution
        .resolved()
        .get(key)
        .and_then(makepad_config::RuntimeValue::as_text)
}

pub(super) fn makepad_horizontal_alignment_tuning_from_resolution(
    mut tuning: HorizontalAlignmentTuning,
    resolution: &makepad_config::RuntimeConfigResolution,
) -> HorizontalAlignmentTuning {
    let global_offset_x_uv = makepad_projection_runtime_optional_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_OFFSET_X_UV,
        -0.5,
        0.5,
    );
    let left_offset_x_uv = makepad_projection_runtime_optional_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV,
        -0.5,
        0.5,
    )
    .or(global_offset_x_uv)
    .unwrap_or(-tuning.projection_area_offset_left_uv);
    let right_offset_x_uv = makepad_projection_runtime_optional_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV,
        -0.5,
        0.5,
    )
    .or(global_offset_x_uv)
    .unwrap_or(-tuning.projection_area_offset_right_uv);
    tuning.projection_area_offset_left_uv = (-left_offset_x_uv).clamp(-0.5, 0.5);
    tuning.projection_area_offset_right_uv = (-right_offset_x_uv).clamp(-0.5, 0.5);
    tuning.projection_area_offset_vertical_uv = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_OFFSET_Y_UV,
        tuning.projection_area_offset_vertical_uv,
        -0.5,
        0.5,
    );
    let uniform_scale = makepad_projection_runtime_optional_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_SCALE_UV,
        PROJECTION_AREA_MIN_SCALE,
        PROJECTION_AREA_MAX_SCALE,
    );
    tuning.projection_area_scale_x = makepad_projection_runtime_optional_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_SCALE_X,
        PROJECTION_AREA_MIN_SCALE,
        PROJECTION_AREA_MAX_SCALE,
    )
    .or(uniform_scale)
    .unwrap_or(tuning.projection_area_scale_x);
    tuning.projection_area_scale_y = makepad_projection_runtime_optional_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_SCALE_Y,
        PROJECTION_AREA_MIN_SCALE,
        PROJECTION_AREA_MAX_SCALE,
    )
    .or(uniform_scale)
    .unwrap_or(tuning.projection_area_scale_y);
    tuning.projection_target_offset_x_uv = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_TARGET_OFFSET_X_UV,
        tuning.projection_target_offset_x_uv,
        -0.5,
        0.5,
    );
    tuning.projection_target_offset_y_uv = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_TARGET_OFFSET_Y_UV,
        tuning.projection_target_offset_y_uv,
        -0.5,
        0.5,
    );
    tuning.projection_target_scale = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_TARGET_SCALE,
        tuning.projection_target_scale,
        PROJECTION_TARGET_MIN_SCALE,
        PROJECTION_TARGET_MAX_SCALE,
    );
    tuning.projection_area_radius_x_uv = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_RADIUS_X_UV,
        tuning.projection_area_radius_x_uv,
        0.05,
        0.5,
    );
    tuning.projection_area_radius_y_uv = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_RADIUS_Y_UV,
        tuning.projection_area_radius_y_uv,
        0.05,
        0.5,
    );
    tuning.projection_area_corner_radius_uv = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_CORNER_RADIUS_UV,
        tuning.projection_area_corner_radius_uv,
        0.0,
        0.5,
    );
    tuning.projection_area_opacity = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_AREA_OPACITY,
        tuning.projection_area_opacity,
        0.0,
        1.0,
    );
    tuning.projection_border_opacity = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_BORDER_OPACITY,
        tuning.projection_border_opacity,
        0.0,
        1.0,
    );
    if let Some(policy) =
        makepad_projection_runtime_text(resolution, makepad_config::KEY_PROJECTION_BORDER_POLICY)
    {
        tuning.projection_border_policy =
            MakepadProjectionBorderPolicy::from_stable_id(policy).shader_code();
    }
    if let Some(processing_layer) =
        makepad_projection_runtime_text(resolution, makepad_config::KEY_PROCESSING_LAYER)
    {
        tuning.processing_layer =
            MakepadProcessingLayer::from_stable_id(processing_layer).shader_code();
    }
    tuning.blur_radius_px = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_CAMERA_BLUR_RADIUS_PX,
        tuning.blur_radius_px,
        0.0,
        16.0,
    );
    tuning.peripheral_stretch_core_scale = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PERIPHERAL_STRETCH_CORE_SCALE,
        tuning.peripheral_stretch_core_scale,
        0.05,
        1.0,
    );
    tuning.peripheral_stretch_edge_inset_uv = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PERIPHERAL_STRETCH_EDGE_INSET_UV,
        tuning.peripheral_stretch_edge_inset_uv,
        0.0,
        0.49,
    );
    tuning.peripheral_stretch_max_inset_uv = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PERIPHERAL_STRETCH_MAX_INSET_UV,
        tuning.peripheral_stretch_max_inset_uv,
        tuning.peripheral_stretch_edge_inset_uv,
        0.49,
    );
    tuning.peripheral_stretch_curve = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PERIPHERAL_STRETCH_CURVE,
        tuning.peripheral_stretch_curve,
        0.25,
        6.0,
    );
    tuning.peripheral_stretch_inner_blend_uv = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PERIPHERAL_STRETCH_INNER_BLEND_UV,
        tuning.peripheral_stretch_inner_blend_uv,
        0.0,
        0.25,
    );
    tuning.peripheral_stretch_blend_curve = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PERIPHERAL_STRETCH_BLEND_CURVE,
        tuning.peripheral_stretch_blend_curve,
        0.25,
        6.0,
    );
    if let Some(blend_mode) = makepad_projection_runtime_text(
        resolution,
        makepad_config::KEY_PERIPHERAL_STRETCH_BLEND_MODE,
    ) {
        tuning.peripheral_stretch_blend_mode =
            MakepadPeripheralStretchBlendMode::from_stable_id(blend_mode).shader_code();
    }
    if let Some(debug) =
        makepad_projection_runtime_text(resolution, makepad_config::KEY_PERIPHERAL_STRETCH_DEBUG)
    {
        tuning.peripheral_stretch_debug =
            MakepadPeripheralStretchDebug::from_stable_id(debug).shader_code();
    }
    if let Some(alpha_mode) =
        makepad_projection_runtime_text(resolution, makepad_config::KEY_PROJECTION_ALPHA_MODE)
    {
        tuning.projection_alpha_mode =
            MakepadProjectionAlphaMode::from_stable_id(alpha_mode).shader_code();
    }
    tuning.projection_alpha_scale = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_ALPHA_SCALE,
        tuning.projection_alpha_scale,
        0.0,
        4.0,
    );
    tuning.projection_alpha_bias = makepad_projection_runtime_float(
        resolution,
        makepad_config::KEY_PROJECTION_ALPHA_BIAS,
        tuning.projection_alpha_bias,
        -1.0,
        1.0,
    );
    tuning
}

fn makepad_projection_runtime_config_defaults() -> makepad_config::RuntimeConfig {
    let mut config = makepad_config::RuntimeConfig::new();
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_CAMERA_PROJECTION_MODE,
        DEFAULT_CAMERA_PROJECTION_MODE,
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_PROJECTION_GEOMETRY_PROFILE,
        DEFAULT_CAMERA_PROJECTION_GEOMETRY_PROFILE,
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_SCALE,
        DEFAULT_PROJECTION_SCALE,
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_DEPTH_METERS,
        DEFAULT_PROJECTION_DEPTH_METERS,
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_CAMERA_PREVIEW_FOV_Y_DEGREES,
        f64::from(TARGET_PROJECTION_PREVIEW_FOV_Y_DEGREES),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_CAMERA_PREVIEW_OFFSET_Y_METERS,
        f64::from(TARGET_PROJECTION_PREVIEW_OFFSET_Y_METERS),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_CAMERA_RAW_OVERLAY_OVERSCAN,
        f64::from(TARGET_PROJECTION_RAW_OVERSCAN),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV,
        f64::from(-TARGET_PROJECTION_AREA_OFFSET_LEFT_UV),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV,
        f64::from(-TARGET_PROJECTION_AREA_OFFSET_RIGHT_UV),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_AREA_OFFSET_Y_UV,
        f64::from(TARGET_PROJECTION_AREA_OFFSET_VERTICAL_UV),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_AREA_SCALE_X,
        f64::from(TARGET_PROJECTION_AREA_SCALE_X),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_AREA_SCALE_Y,
        f64::from(TARGET_PROJECTION_AREA_SCALE_Y),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_TARGET_OFFSET_X_UV,
        f64::from(TARGET_PROJECTION_TARGET_OFFSET_X_UV),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_TARGET_OFFSET_Y_UV,
        f64::from(TARGET_PROJECTION_TARGET_OFFSET_Y_UV),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_TARGET_SCALE,
        f64::from(TARGET_PROJECTION_TARGET_SCALE),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_AREA_RADIUS_X_UV,
        f64::from(TARGET_PROJECTION_AREA_RADIUS_X_UV),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_AREA_RADIUS_Y_UV,
        f64::from(TARGET_PROJECTION_AREA_RADIUS_Y_UV),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_AREA_CORNER_RADIUS_UV,
        f64::from(TARGET_PROJECTION_AREA_CORNER_RADIUS_UV),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_AREA_OPACITY,
        f64::from(TARGET_PROJECTION_AREA_OPACITY),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_BORDER_OPACITY,
        f64::from(TARGET_PROJECTION_BORDER_OPACITY),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_PROJECTION_BORDER_POLICY,
        MakepadProjectionBorderPolicy::SolidRed.stable_id(),
        makepad_config::RuntimeConfigSource::Default,
    );
    let default_processing_layer = MakepadProcessingLayer::Raw;
    let default_peripheral_stretch = MakepadPeripheralStretchConfig::default();
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_PROCESSING_LAYER,
        default_processing_layer.stable_id(),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_CAMERA_BLUR_RADIUS_PX,
        2.0,
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_MODE,
        default_peripheral_stretch.mode.stable_id(),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_CORE_SCALE,
        f64::from(default_peripheral_stretch.core_scale),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_EDGE_INSET_UV,
        f64::from(default_peripheral_stretch.edge_inset_uv),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_MAX_INSET_UV,
        f64::from(default_peripheral_stretch.max_inset_uv),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_CURVE,
        f64::from(default_peripheral_stretch.curve),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_INNER_BLEND_UV,
        f64::from(default_peripheral_stretch.inner_blend_uv),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_BLEND_CURVE,
        f64::from(default_peripheral_stretch.blend_curve),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_BLEND_MODE,
        default_peripheral_stretch.blend_mode.stable_id(),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_CORNER_MODE,
        default_peripheral_stretch.corner_mode.stable_id(),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_PERIPHERAL_STRETCH_DEBUG,
        default_peripheral_stretch.debug.stable_id(),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_PROJECTION_ALPHA_MODE,
        MakepadProjectionAlphaMode::Fixed.stable_id(),
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_ALPHA_SCALE,
        1.0,
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_float(
        &mut config,
        makepad_config::KEY_PROJECTION_ALPHA_BIAS,
        0.0,
        makepad_config::RuntimeConfigSource::Default,
    );
    set_projection_manifest_text(
        &mut config,
        makepad_config::KEY_SOURCE_EYE_MAPPING,
        DEFAULT_MAKEPAD_DISPLAY_SOURCE_EYE_MAPPING,
        makepad_config::RuntimeConfigSource::Default,
    );
    config
}

fn makepad_projection_runtime_config_effective(
    config: &makepad_config::RuntimeConfig,
    tuning: HorizontalAlignmentTuning,
) -> makepad_config::RuntimeConfig {
    let mut manifest = makepad_config::RuntimeConfig::new();
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_CAMERA_PROJECTION_MODE,
        &runtime_text(config, KEY_CAMERA_PROJECTION_MODE),
        makepad_config::RuntimeConfigSource::Environment,
    );
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_PROJECTION_GEOMETRY_PROFILE,
        &App::direct_camera_projection_geometry_profile(),
        makepad_config::RuntimeConfigSource::Environment,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_SCALE,
        runtime_float(config, KEY_PROJECTION_SCALE),
        makepad_config::RuntimeConfigSource::Environment,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_DEPTH_METERS,
        runtime_float(config, KEY_PROJECTION_DEPTH_METERS),
        makepad_config::RuntimeConfigSource::Environment,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_CAMERA_PREVIEW_FOV_Y_DEGREES,
        runtime_float(config, KEY_CAMERA_PREVIEW_FOV_Y_DEGREES),
        makepad_config::RuntimeConfigSource::Environment,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_CAMERA_PREVIEW_OFFSET_Y_METERS,
        runtime_float(config, KEY_CAMERA_PREVIEW_OFFSET_Y_METERS),
        makepad_config::RuntimeConfigSource::Environment,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_CAMERA_RAW_OVERLAY_OVERSCAN,
        runtime_float(config, KEY_CAMERA_RAW_OVERLAY_OVERSCAN),
        makepad_config::RuntimeConfigSource::Environment,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV,
        f64::from(-tuning.projection_area_offset_left_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV,
        f64::from(-tuning.projection_area_offset_right_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_AREA_OFFSET_Y_UV,
        f64::from(tuning.projection_area_offset_vertical_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_AREA_SCALE_X,
        f64::from(tuning.projection_area_scale_x),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_AREA_SCALE_Y,
        f64::from(tuning.projection_area_scale_y),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_TARGET_OFFSET_X_UV,
        f64::from(tuning.projection_target_offset_x_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_TARGET_OFFSET_Y_UV,
        f64::from(tuning.projection_target_offset_y_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_TARGET_SCALE,
        f64::from(tuning.projection_target_scale),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_AREA_RADIUS_X_UV,
        f64::from(tuning.projection_area_radius_x_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_AREA_RADIUS_Y_UV,
        f64::from(tuning.projection_area_radius_y_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_AREA_CORNER_RADIUS_UV,
        f64::from(tuning.projection_area_corner_radius_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_AREA_OPACITY,
        f64::from(tuning.projection_area_opacity),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_BORDER_OPACITY,
        f64::from(tuning.projection_border_opacity),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_PROJECTION_BORDER_POLICY,
        MakepadProjectionBorderPolicy::current().stable_id(),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    let processing_layer = MakepadProcessingLayer::from_shader_code(tuning.processing_layer);
    let stretch_blend_mode =
        MakepadPeripheralStretchBlendMode::from_shader_code(tuning.peripheral_stretch_blend_mode);
    let stretch_debug =
        MakepadPeripheralStretchDebug::from_shader_code(tuning.peripheral_stretch_debug);
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_PROCESSING_LAYER,
        processing_layer.stable_id(),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_CAMERA_BLUR_RADIUS_PX,
        f64::from(tuning.blur_radius_px),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_MODE,
        MakepadPeripheralStretchMode::EdgeStretch.stable_id(),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_CORE_SCALE,
        f64::from(tuning.peripheral_stretch_core_scale),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_EDGE_INSET_UV,
        f64::from(tuning.peripheral_stretch_edge_inset_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_MAX_INSET_UV,
        f64::from(tuning.peripheral_stretch_max_inset_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_CURVE,
        f64::from(tuning.peripheral_stretch_curve),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_INNER_BLEND_UV,
        f64::from(tuning.peripheral_stretch_inner_blend_uv),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_BLEND_CURVE,
        f64::from(tuning.peripheral_stretch_blend_curve),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_BLEND_MODE,
        stretch_blend_mode.stable_id(),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_CORNER_MODE,
        MakepadPeripheralStretchCornerMode::TargetFootprint.stable_id(),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_PERIPHERAL_STRETCH_DEBUG,
        stretch_debug.stable_id(),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_PROJECTION_ALPHA_MODE,
        MakepadProjectionAlphaMode::current().stable_id(),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_ALPHA_SCALE,
        f64::from(tuning.projection_alpha_scale),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_float(
        &mut manifest,
        makepad_config::KEY_PROJECTION_ALPHA_BIAS,
        f64::from(tuning.projection_alpha_bias),
        makepad_config::RuntimeConfigSource::AndroidProperty,
    );
    set_projection_manifest_text(
        &mut manifest,
        makepad_config::KEY_SOURCE_EYE_MAPPING,
        makepad_display_source_eye_mapping(),
        makepad_config::RuntimeConfigSource::Synthetic,
    );
    manifest
}

fn makepad_projection_alias_records() -> Vec<makepad_config::RuntimeKeyAliasRecord> {
    [
        "debug.rusty.projection.depth.meters",
        "debug.rusty.camera.preview.fov.y.degrees",
        "debug.rusty.camera.preview.offset.y.meters",
        "debug.rusty.camera.raw.overlay.overscan",
        "debug.rusty.projection.area.scale.uv",
        "debug.rusty.projection.area.offset.x.uv",
        "debug.rusty.projection.area.left.offset.x.uv",
        "debug.rusty.projection.area.right.offset.x.uv",
        "debug.rusty.projection.area.offset.y.uv",
        "debug.rusty.projection.area.scale.x",
        "debug.rusty.projection.area.scale.y",
        "debug.rusty.projection.target.offset.x.uv",
        "debug.rusty.projection.target.offset.y.uv",
        "debug.rusty.projection.target.scale",
        "debug.rusty.projection.target.joystick.controls",
        "debug.rusty.projection.area.radius.x.uv",
        "debug.rusty.projection.area.radius.y.uv",
        "debug.rusty.projection.area.corner.radius.uv",
        "debug.rusty.projection.area.opacity",
        "debug.rusty.projection.border.opacity",
        "debug.rusty.projection.border.policy",
        "debug.rusty.processing.layer",
        "debug.rusty.camera.blur.radius.px",
        "debug.rusty.peripheral.stretch.mode",
        "debug.rusty.peripheral.stretch.core.scale",
        "debug.rusty.peripheral.stretch.edge.inset.uv",
        "debug.rusty.peripheral.stretch.max.inset.uv",
        "debug.rusty.peripheral.stretch.curve",
        "debug.rusty.peripheral.stretch.inner.blend.uv",
        "debug.rusty.peripheral.stretch.blend.curve",
        "debug.rusty.peripheral.stretch.blend.mode",
        "debug.rusty.peripheral.stretch.corner.mode",
        "debug.rusty.peripheral.stretch.debug",
        "debug.rusty.projection.alpha.mode",
        "debug.rusty.projection.alpha.scale",
        "debug.rusty.projection.alpha.bias",
    ]
    .into_iter()
    .filter_map(|key| makepad_config::resolve_projection_runtime_key(key).ok())
    .collect()
}

fn set_projection_manifest_text(
    config: &mut makepad_config::RuntimeConfig,
    key: &'static str,
    value: &str,
    source: makepad_config::RuntimeConfigSource,
) {
    config
        .set(
            key,
            makepad_config::RuntimeValue::Text(value.to_string()),
            source,
        )
        .expect("projection manifest keys should be public-safe");
}

fn set_projection_manifest_float(
    config: &mut makepad_config::RuntimeConfig,
    key: &'static str,
    value: f64,
    source: makepad_config::RuntimeConfigSource,
) {
    config
        .set(key, makepad_config::RuntimeValue::Float(value), source)
        .expect("projection manifest keys should be public-safe");
}
