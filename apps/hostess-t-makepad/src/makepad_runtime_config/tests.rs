//! Makepad runtime config tests.

use super::*;
use std::collections::BTreeMap;

#[test]
fn exposes_workspace_version() {
    assert_eq!(VERSION, "0.1.0");
}

#[test]
fn parses_typed_runtime_values() {
    assert_eq!(RuntimeValue::parse_typed("on"), RuntimeValue::Bool(true));
    assert_eq!(RuntimeValue::parse_typed("42"), RuntimeValue::Integer(42));
    assert_eq!(RuntimeValue::parse_typed("0.25"), RuntimeValue::Float(0.25));
    assert_eq!(
        RuntimeValue::parse_typed("balanced"),
        RuntimeValue::Text("balanced".to_string())
    );
}

#[test]
fn rejects_private_or_invalid_key_shapes() {
    assert!(RuntimeKey::new("render_scale").is_ok());
    assert!(RuntimeKey::new("debug.example.render_scale").is_err());
    assert!(RuntimeKey::new("RenderScale").is_err());
}

#[test]
fn builds_generic_android_property_name() {
    let key = RuntimeKey::new("render_scale").expect("key should be valid");
    let prefix = AndroidPropertyPrefix::default();

    assert_eq!(key.android_property(&prefix), "debug.rusty.render.scale");
}

#[test]
fn android_property_normalizes_public_key_separators() {
    let key = RuntimeKey::new("render-scale").expect("key should be valid");
    let prefix = AndroidPropertyPrefix::default();

    assert_eq!(key.android_property(&prefix), "debug.rusty.render.scale");
}

#[test]
fn stores_ordered_runtime_settings() {
    let config = RuntimeConfig::parse_pairs(
        RuntimeConfigSource::Synthetic,
        [("z_value", "9"), ("a_value", "true")],
    )
    .expect("pairs should parse");

    let keys = config
        .iter()
        .map(|setting| setting.key.as_str())
        .collect::<Vec<_>>();

    assert_eq!(keys, ["a_value", "z_value"]);
    assert_eq!(config.get("a_value"), Some(&RuntimeValue::Bool(true)));
}

#[test]
fn projection_runtime_registry_keys_are_valid_and_unique() {
    let mut seen = BTreeMap::new();
    for definition in PROJECTION_RUNTIME_KEY_DEFINITIONS {
        assert_eq!(definition.runtime_key().as_str(), definition.key);
        assert!(
            seen.insert(definition.key, definition.owner).is_none(),
            "duplicate projection key {}",
            definition.key
        );
    }
}

#[test]
fn projection_runtime_aliases_resolve_to_registered_keys() {
    let mut seen = BTreeMap::new();
    for alias in PROJECTION_RUNTIME_KEY_ALIASES {
        assert!(
            projection_runtime_key_definition(alias.canonical_key).is_some(),
            "alias {} targets unregistered key {}",
            alias.alias,
            alias.canonical_key
        );
        assert!(
            seen.insert(alias.alias, alias.canonical_key).is_none(),
            "duplicate alias {}",
            alias.alias
        );
    }

    let launch = resolve_projection_runtime_key("makepad.projectionDepthMeters")
        .expect("launch extra alias should resolve");
    assert_eq!(launch.canonical_key.as_str(), KEY_PROJECTION_DEPTH_METERS);
    assert_eq!(launch.source, RuntimeKeyAliasSource::LaunchExtra);

    let property =
        resolve_projection_runtime_key("debug.rustyquest.makepad.projection.depth.meters")
            .expect("Android property alias should resolve");
    assert_eq!(property.canonical_key.as_str(), KEY_PROJECTION_DEPTH_METERS);
    assert_eq!(property.source, RuntimeKeyAliasSource::AndroidProperty);
}

#[test]
fn projection_runtime_keeps_source_kind_out_of_projection_math() {
    let source_sampling_keys = PROJECTION_RUNTIME_KEY_DEFINITIONS
        .iter()
        .filter(|definition| definition.owner == ProjectionRuntimeKeyOwner::SourceSampling)
        .map(|definition| definition.key)
        .collect::<Vec<_>>();

    assert_eq!(
        source_sampling_keys,
        [
            KEY_SOURCE_EYE_MAPPING,
            KEY_SOURCE_TEXTURE_ROTATION,
            KEY_SOURCE_TEXTURE_FLIP_X,
            KEY_SOURCE_TEXTURE_FLIP_Y,
            KEY_SOURCE_TEXTURE_MIRROR,
            KEY_SOURCE_TEXTURE_TRANSFORM_SOURCE,
            KEY_SOURCE_TEXTURE_TRANSFORM_REASON,
            KEY_LEFT_SOURCE_TEXTURE_TRANSFORM_SOURCE,
            KEY_RIGHT_SOURCE_TEXTURE_TRANSFORM_SOURCE,
            KEY_SOURCE_VISIBLE_RECT_X_UV,
            KEY_SOURCE_VISIBLE_RECT_Y_UV,
            KEY_SOURCE_VISIBLE_RECT_WIDTH_UV,
            KEY_SOURCE_VISIBLE_RECT_HEIGHT_UV,
        ]
    );
    assert!(projection_runtime_key_definition("source_kind").is_none());
    assert!(projection_runtime_key_definition("camera_source_kind").is_none());
    assert!(projection_runtime_key_definition("synthetic_source_kind").is_none());
}

#[test]
fn parses_projection_runtime_pairs_with_alias_evidence() {
    let parsed = parse_projection_runtime_pairs(
        RuntimeConfigSource::CommandLine,
        [
            ("makepad.projectionDepthMeters", "1.25"),
            ("source_eye_mapping", "right-left"),
            (
                "debug.rustyquest.makepad.source.visible.rect.width.uv",
                "0.875",
            ),
        ],
    )
    .expect("projection pairs should parse");

    assert_eq!(
        parsed.config.get(KEY_PROJECTION_DEPTH_METERS),
        Some(&RuntimeValue::Float(1.25))
    );
    assert_eq!(
        parsed.config.get(KEY_SOURCE_EYE_MAPPING),
        Some(&RuntimeValue::Text("right-left".to_string()))
    );
    assert_eq!(
        parsed.config.get(KEY_SOURCE_VISIBLE_RECT_WIDTH_UV),
        Some(&RuntimeValue::Float(0.875))
    );
    assert_eq!(parsed.aliases.len(), 3);
    assert_eq!(parsed.aliases[0].source, RuntimeKeyAliasSource::LaunchExtra);
    assert_eq!(parsed.aliases[1].source, RuntimeKeyAliasSource::Canonical);
    assert_eq!(
        parsed.aliases[2].source,
        RuntimeKeyAliasSource::AndroidProperty
    );
}

#[test]
fn parses_projection_alias_values_using_registered_value_kind() {
    let parsed = parse_projection_runtime_pairs(
        RuntimeConfigSource::AndroidProperty,
        [
            ("debug.rustyquest.makepad.projection.depth.meters", "1"),
            (
                "debug.rustyquest.makepad.camera.preview.offset.y.meters",
                "0",
            ),
            ("makepad.cameraTextureFlipX", "true"),
            (
                "debug.rustyquest.makepad.projection.alpha.mode",
                "source-alpha",
            ),
        ],
    )
    .expect("registered projection value kinds should parse");

    assert_eq!(
        parsed.config.get(KEY_PROJECTION_DEPTH_METERS),
        Some(&RuntimeValue::Float(1.0))
    );
    assert_eq!(
        parsed.config.get(KEY_CAMERA_PREVIEW_OFFSET_Y_METERS),
        Some(&RuntimeValue::Float(0.0))
    );
    assert_eq!(
        parsed.config.get(KEY_SOURCE_TEXTURE_FLIP_X),
        Some(&RuntimeValue::Bool(true))
    );
    assert_eq!(
        parsed.config.get(KEY_PROJECTION_ALPHA_MODE),
        Some(&RuntimeValue::Text("source-alpha".to_string()))
    );
}

#[test]
fn rejects_unregistered_makepad_scoped_projection_aliases() {
    let retired_alias =
        retired_projection_runtime_key_alias("debug.rusty.makepad.projection.area.offset.left.uv")
            .expect("retired mis-scoped property should be documented");
    assert_eq!(
        retired_alias.replacement,
        "debug.rustyquest.makepad.projection.area.left.offset.x.uv"
    );

    let error = parse_projection_runtime_pairs(
        RuntimeConfigSource::AndroidProperty,
        [(
            "debug.rusty.makepad.projection.area.offset.left.uv",
            "0.125",
        )],
    )
    .unwrap_err();

    assert_eq!(
        error,
        RuntimeConfigError::UnknownRuntimeKeyAlias(
            "debug.rusty.makepad.projection.area.offset.left.uv".to_string()
        )
    );
}

#[test]
fn retired_projection_aliases_are_documented_but_not_accepted() {
    let mut seen = BTreeMap::new();
    for retired_alias in RETIRED_PROJECTION_RUNTIME_KEY_ALIASES {
        assert!(
            seen.insert(retired_alias.alias, retired_alias.replacement)
                .is_none(),
            "duplicate retired alias {}",
            retired_alias.alias
        );
        assert!(
            projection_runtime_key_alias(retired_alias.alias).is_none(),
            "retired alias {} must not be accepted",
            retired_alias.alias
        );
        assert_eq!(
            retired_projection_runtime_key_alias(retired_alias.alias),
            Some(retired_alias)
        );
        assert!(
            projection_runtime_key_definition(retired_alias.replacement).is_some()
                || projection_runtime_key_alias(retired_alias.replacement).is_some(),
            "retired alias {} points to unknown replacement {}",
            retired_alias.alias,
            retired_alias.replacement
        );
        assert_eq!(
            resolve_projection_runtime_key(retired_alias.alias).unwrap_err(),
            RuntimeConfigError::UnknownRuntimeKeyAlias(retired_alias.alias.to_string())
        );
    }
}

#[test]
fn rejects_unknown_projection_runtime_aliases() {
    assert_eq!(
        resolve_projection_runtime_key("makepad.privateEffectStrength").unwrap_err(),
        RuntimeConfigError::UnknownRuntimeKeyAlias("makepad.privateEffectStrength".to_string())
    );
}

#[test]
fn projection_manifest_marker_lines_include_resolution_trace() {
    let defaults = parse_projection_runtime_pairs(
        RuntimeConfigSource::Default,
        [("projection_depth_meters", "1.0")],
    )
    .expect("defaults should parse");
    let requested = parse_projection_runtime_pairs(
        RuntimeConfigSource::AndroidProperty,
        [("debug.rustyquest.makepad.projection.depth.meters", "1.5")],
    )
    .expect("properties should parse");
    let resolution = RuntimeConfigResolver::new()
        .with_layer(RuntimeConfigLayer::new("backend-defaults", 0, defaults.config).unwrap())
        .with_layer(RuntimeConfigLayer::new("android-properties", 20, requested.config).unwrap())
        .resolve();
    let lines =
        projection_runtime_manifest_marker_lines("oes", "startup", &resolution, &requested.aliases);

    assert_eq!(lines.len(), 2);
    let joined = lines.join("\n");
    assert!(joined.contains("schema=rusty.gui.makepad.projection_runtime_manifest.v1"));
    assert!(joined.contains("backend=oes"));
    assert!(joined.contains("section=aliases"));
    assert!(joined.contains("section=fields"));
    assert!(joined.contains("projection_depth_meters"));
    assert!(joined.contains("resolved=float:1.500000"));
    assert!(joined.contains("default=float:1.000000"));
    assert!(
        joined.contains("debug.rustyquest.makepad.projection.depth.meters>projection_depth_meters")
    );
}

#[test]
fn projection_runtime_builder_collects_layers_and_aliases() {
    let defaults = parse_projection_runtime_pairs(
        RuntimeConfigSource::Default,
        [("projection_depth_meters", "1.0")],
    )
    .expect("defaults should parse");
    let requested = parse_projection_runtime_pairs(
        RuntimeConfigSource::AndroidProperty,
        [("debug.rustyquest.makepad.projection.depth.meters", "1.25")],
    )
    .expect("properties should parse");
    let runtime = ProjectionRuntimeConfigBuilder::new()
        .with_layer("backend-defaults", 0, defaults.config)
        .expect("default layer should be valid")
        .with_layer("android-properties", 20, requested.config)
        .expect("property layer should be valid")
        .with_aliases(requested.aliases)
        .resolve();

    assert_eq!(
        runtime
            .resolution
            .resolved()
            .get(KEY_PROJECTION_DEPTH_METERS),
        Some(&RuntimeValue::Float(1.25))
    );
    assert_eq!(runtime.aliases.len(), 1);
    let lines = runtime.manifest_marker_lines("oes", "startup");
    let joined = lines.join("\n");
    assert!(joined.contains("backend=oes"));
    assert!(joined.contains("owner=android-properties"));
    assert!(joined.contains("resolved=float:1.250000"));
}

fn projection_runtime_golden_snapshot(
    backend: &str,
    launch_pairs: &[(&'static str, &'static str)],
    property_pairs: &[(&'static str, &'static str)],
) -> Vec<(&'static str, RuntimeValue)> {
    let defaults = parse_projection_runtime_pairs(
        RuntimeConfigSource::Default,
        [
            (KEY_CAMERA_PROJECTION_MODE, "display-screen-homography"),
            (KEY_PROJECTION_DEPTH_METERS, "1.0"),
            (KEY_CAMERA_PREVIEW_FOV_Y_DEGREES, "60.0"),
            (KEY_CAMERA_PREVIEW_OFFSET_Y_METERS, "0.0"),
            (KEY_CAMERA_RAW_OVERLAY_OVERSCAN, "1.06"),
            (KEY_PROJECTION_AREA_SCALE_X, "1.0"),
            (KEY_PROJECTION_AREA_SCALE_Y, "1.0"),
            (KEY_PROJECTION_AREA_OFFSET_X_UV, "0.0"),
            (KEY_PROJECTION_AREA_OFFSET_Y_UV, "0.0"),
            (KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV, "0.0"),
            (KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV, "0.0"),
            (KEY_PROJECTION_AREA_RADIUS_X_UV, "0.47"),
            (KEY_PROJECTION_AREA_RADIUS_Y_UV, "0.36"),
            (KEY_PROJECTION_AREA_OPACITY, "1.0"),
            (KEY_PROJECTION_BORDER_OPACITY, "1.0"),
            (KEY_PROJECTION_BORDER_POLICY, "solid-red"),
            (KEY_PROJECTION_TARGET_OFFSET_X_UV, "0.0"),
            (KEY_PROJECTION_TARGET_OFFSET_Y_UV, "0.0"),
            (KEY_PROJECTION_TARGET_SCALE, "1.0"),
            (KEY_PROJECTION_TARGET_JOYSTICK_CONTROLS, "off"),
            (KEY_PROJECTION_TARGET_BREATH_CONTROLS, "off"),
            (
                KEY_PROJECTION_TARGET_BREATH_STREAM,
                "stream.breath.volume.selected",
            ),
            (KEY_PROJECTION_TARGET_BREATH_SCALE_MODE, "volume"),
            (KEY_PROJECTION_TARGET_BREATH_MIN_SCALE, "1.0"),
            (KEY_PROJECTION_TARGET_BREATH_MAX_SCALE, "5.0"),
            (
                KEY_PROJECTION_TARGET_BREATH_INHALE_SECONDS_MIN_TO_MAX,
                "4.0",
            ),
            (
                KEY_PROJECTION_TARGET_BREATH_EXHALE_SECONDS_MAX_TO_MIN,
                "4.0",
            ),
            (KEY_PROJECTION_TARGET_BREATH_SMOOTHING_ALPHA, "0.30"),
            (KEY_PROJECTION_TARGET_BREATH_INVERT, "false"),
            (KEY_PROJECTION_TARGET_BREATH_MIN_QUALITY, "0.0"),
            (KEY_PROJECTION_ALPHA_MODE, "fixed"),
            (KEY_PROJECTION_ALPHA_SCALE, "1.0"),
            (KEY_PROJECTION_ALPHA_BIAS, "0.0"),
            (KEY_SOURCE_EYE_MAPPING, "left-right"),
            (KEY_SOURCE_TEXTURE_TRANSFORM_SOURCE, "metadata"),
            (KEY_SOURCE_VISIBLE_RECT_X_UV, "0.0"),
            (KEY_SOURCE_VISIBLE_RECT_Y_UV, "0.0"),
            (KEY_SOURCE_VISIBLE_RECT_WIDTH_UV, "1.0"),
            (KEY_SOURCE_VISIBLE_RECT_HEIGHT_UV, "1.0"),
        ],
    )
    .expect("golden defaults should parse");
    let launch = parse_projection_runtime_pairs(
        RuntimeConfigSource::CommandLine,
        launch_pairs.iter().copied(),
    )
    .expect("golden launch pairs should parse");
    let properties = parse_projection_runtime_pairs(
        RuntimeConfigSource::AndroidProperty,
        property_pairs.iter().copied(),
    )
    .expect("golden property pairs should parse");
    let runtime = ProjectionRuntimeConfigBuilder::new()
        .with_layer(format!("{backend}-defaults"), 0, defaults.config)
        .expect("default layer should be valid")
        .with_layer(format!("{backend}-launch"), 10, launch.config)
        .expect("launch layer should be valid")
        .with_layer(format!("{backend}-properties"), 20, properties.config)
        .expect("property layer should be valid")
        .with_aliases(launch.aliases)
        .with_aliases(properties.aliases)
        .resolve();
    [
        KEY_CAMERA_PROJECTION_MODE,
        KEY_PROJECTION_DEPTH_METERS,
        KEY_CAMERA_PREVIEW_FOV_Y_DEGREES,
        KEY_CAMERA_PREVIEW_OFFSET_Y_METERS,
        KEY_CAMERA_RAW_OVERLAY_OVERSCAN,
        KEY_PROJECTION_AREA_SCALE_X,
        KEY_PROJECTION_AREA_SCALE_Y,
        KEY_PROJECTION_AREA_OFFSET_X_UV,
        KEY_PROJECTION_AREA_OFFSET_Y_UV,
        KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV,
        KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV,
        KEY_PROJECTION_AREA_RADIUS_X_UV,
        KEY_PROJECTION_AREA_RADIUS_Y_UV,
        KEY_PROJECTION_AREA_OPACITY,
        KEY_PROJECTION_BORDER_OPACITY,
        KEY_PROJECTION_BORDER_POLICY,
        KEY_PROJECTION_TARGET_OFFSET_X_UV,
        KEY_PROJECTION_TARGET_OFFSET_Y_UV,
        KEY_PROJECTION_TARGET_SCALE,
        KEY_PROJECTION_TARGET_JOYSTICK_CONTROLS,
        KEY_PROJECTION_TARGET_BREATH_CONTROLS,
        KEY_PROJECTION_TARGET_BREATH_STREAM,
        KEY_PROJECTION_TARGET_BREATH_SCALE_MODE,
        KEY_PROJECTION_TARGET_BREATH_MIN_SCALE,
        KEY_PROJECTION_TARGET_BREATH_MAX_SCALE,
        KEY_PROJECTION_TARGET_BREATH_INHALE_SECONDS_MIN_TO_MAX,
        KEY_PROJECTION_TARGET_BREATH_EXHALE_SECONDS_MAX_TO_MIN,
        KEY_PROJECTION_TARGET_BREATH_SMOOTHING_ALPHA,
        KEY_PROJECTION_TARGET_BREATH_INVERT,
        KEY_PROJECTION_TARGET_BREATH_MIN_QUALITY,
        KEY_PROJECTION_ALPHA_MODE,
        KEY_PROJECTION_ALPHA_SCALE,
        KEY_PROJECTION_ALPHA_BIAS,
        KEY_SOURCE_EYE_MAPPING,
        KEY_SOURCE_TEXTURE_TRANSFORM_SOURCE,
        KEY_SOURCE_VISIBLE_RECT_X_UV,
        KEY_SOURCE_VISIBLE_RECT_Y_UV,
        KEY_SOURCE_VISIBLE_RECT_WIDTH_UV,
        KEY_SOURCE_VISIBLE_RECT_HEIGHT_UV,
    ]
    .into_iter()
    .map(|key| {
        (
            key,
            runtime
                .resolution
                .resolved()
                .get(key)
                .unwrap_or_else(|| panic!("{key} should resolve"))
                .clone(),
        )
    })
    .collect()
}

#[test]
fn projection_runtime_golden_matrix_is_backend_neutral_for_equivalent_metadata() {
    let launch_alias_snapshot = projection_runtime_golden_snapshot(
        "hwb",
        &[
            ("makepad.cameraProjectionMode", "display-screen-homography"),
            ("makepad.projectionDepthMeters", "1.25"),
            ("makepad.cameraPreviewFovYDegrees", "63.0"),
            ("makepad.cameraPreviewOffsetYMeters", "0.08"),
            ("makepad.cameraRawOverlayOverscan", "1.12"),
            ("makepad.projectionAreaScaleX", "0.82"),
            ("makepad.projectionAreaScaleY", "0.74"),
            ("makepad.projectionAreaOffsetXUv", "0.03"),
            ("makepad.projectionAreaOffsetYUv", "-0.02"),
            ("makepad.projectionAreaLeftOffsetXUv", "-0.04"),
            ("makepad.projectionAreaRightOffsetXUv", "0.04"),
            ("makepad.projectionAreaRadiusXUv", "0.44"),
            ("makepad.projectionAreaRadiusYUv", "0.31"),
            ("makepad.projectionAreaOpacity", "0.90"),
            ("makepad.projectionBorderOpacity", "0.80"),
            ("makepad.projectionBorderPolicy", "solid-red"),
            ("makepad.projectionTargetOffsetXUv", "0.05"),
            ("makepad.projectionTargetOffsetYUv", "-0.03"),
            ("makepad.projectionTargetScale", "0.80"),
            ("makepad.projectionTargetJoystickControls", "offset-scale"),
            ("makepad.projectionTargetBreathControls", "scale"),
            (
                "makepad.projectionTargetBreathStream",
                "stream.breath.volume.selected",
            ),
            ("makepad.projectionTargetBreathScaleMode", "state-ramp"),
            ("makepad.projectionTargetBreathMinScale", "1.0"),
            ("makepad.projectionTargetBreathMaxScale", "5.0"),
            ("makepad.projectionTargetBreathInhaleSecondsMinToMax", "4.0"),
            ("makepad.projectionTargetBreathExhaleSecondsMaxToMin", "4.0"),
            ("makepad.projectionTargetBreathSmoothingAlpha", "0.30"),
            ("makepad.projectionTargetBreathInvert", "true"),
            ("makepad.projectionTargetBreathMinQuality", "0.20"),
            ("makepad.projectionAlphaMode", "fixed"),
            ("makepad.projectionAlphaScale", "1.10"),
            ("makepad.projectionAlphaBias", "-0.05"),
            ("makepad.cameraSourceEyeMapping", "left-right"),
            ("makepad.cameraTextureTransformSource", "metadata"),
            (KEY_SOURCE_VISIBLE_RECT_X_UV, "0.10"),
            (KEY_SOURCE_VISIBLE_RECT_Y_UV, "0.20"),
            (KEY_SOURCE_VISIBLE_RECT_WIDTH_UV, "0.80"),
            (KEY_SOURCE_VISIBLE_RECT_HEIGHT_UV, "0.60"),
        ],
        &[],
    );
    let canonical_snapshot = projection_runtime_golden_snapshot(
        "oes",
        &[
            (KEY_CAMERA_PROJECTION_MODE, "display-screen-homography"),
            (KEY_PROJECTION_DEPTH_METERS, "1.25"),
            (KEY_CAMERA_PREVIEW_FOV_Y_DEGREES, "63.0"),
            (KEY_CAMERA_PREVIEW_OFFSET_Y_METERS, "0.08"),
            (KEY_CAMERA_RAW_OVERLAY_OVERSCAN, "1.12"),
            (KEY_PROJECTION_AREA_SCALE_X, "0.82"),
            (KEY_PROJECTION_AREA_SCALE_Y, "0.74"),
            (KEY_PROJECTION_AREA_OFFSET_X_UV, "0.03"),
            (KEY_PROJECTION_AREA_OFFSET_Y_UV, "-0.02"),
            (KEY_PROJECTION_AREA_LEFT_OFFSET_X_UV, "-0.04"),
            (KEY_PROJECTION_AREA_RIGHT_OFFSET_X_UV, "0.04"),
            (KEY_PROJECTION_AREA_RADIUS_X_UV, "0.44"),
            (KEY_PROJECTION_AREA_RADIUS_Y_UV, "0.31"),
            (KEY_PROJECTION_AREA_OPACITY, "0.90"),
            (KEY_PROJECTION_BORDER_OPACITY, "0.80"),
            (KEY_PROJECTION_BORDER_POLICY, "solid-red"),
            (KEY_PROJECTION_TARGET_OFFSET_X_UV, "0.05"),
            (KEY_PROJECTION_TARGET_OFFSET_Y_UV, "-0.03"),
            (KEY_PROJECTION_TARGET_SCALE, "0.80"),
            (KEY_PROJECTION_TARGET_JOYSTICK_CONTROLS, "offset-scale"),
            (KEY_PROJECTION_TARGET_BREATH_CONTROLS, "scale"),
            (
                KEY_PROJECTION_TARGET_BREATH_STREAM,
                "stream.breath.volume.selected",
            ),
            (KEY_PROJECTION_TARGET_BREATH_SCALE_MODE, "state-ramp"),
            (KEY_PROJECTION_TARGET_BREATH_MIN_SCALE, "1.0"),
            (KEY_PROJECTION_TARGET_BREATH_MAX_SCALE, "5.0"),
            (
                KEY_PROJECTION_TARGET_BREATH_INHALE_SECONDS_MIN_TO_MAX,
                "4.0",
            ),
            (
                KEY_PROJECTION_TARGET_BREATH_EXHALE_SECONDS_MAX_TO_MIN,
                "4.0",
            ),
            (KEY_PROJECTION_TARGET_BREATH_SMOOTHING_ALPHA, "0.30"),
            (KEY_PROJECTION_TARGET_BREATH_INVERT, "true"),
            (KEY_PROJECTION_TARGET_BREATH_MIN_QUALITY, "0.20"),
            (KEY_PROJECTION_ALPHA_MODE, "fixed"),
            (KEY_PROJECTION_ALPHA_SCALE, "1.10"),
            (KEY_PROJECTION_ALPHA_BIAS, "-0.05"),
            (KEY_SOURCE_EYE_MAPPING, "left-right"),
            (KEY_SOURCE_TEXTURE_TRANSFORM_SOURCE, "metadata"),
            (KEY_SOURCE_VISIBLE_RECT_X_UV, "0.10"),
            (KEY_SOURCE_VISIBLE_RECT_Y_UV, "0.20"),
            (KEY_SOURCE_VISIBLE_RECT_WIDTH_UV, "0.80"),
            (KEY_SOURCE_VISIBLE_RECT_HEIGHT_UV, "0.60"),
        ],
        &[],
    );
    let property_snapshot = projection_runtime_golden_snapshot(
        "makepad",
        &[],
        &[
            (
                "debug.rustyquest.makepad.camera.projection.mode",
                "display-screen-homography",
            ),
            ("debug.rustyquest.makepad.projection.depth.meters", "1.25"),
            (
                "debug.rustyquest.makepad.camera.preview.fov.y.degrees",
                "63.0",
            ),
            (
                "debug.rustyquest.makepad.camera.preview.offset.y.meters",
                "0.08",
            ),
            (
                "debug.rustyquest.makepad.camera.raw.overlay.overscan",
                "1.12",
            ),
            ("debug.rustyquest.makepad.projection.area.scale.x", "0.82"),
            ("debug.rustyquest.makepad.projection.area.scale.y", "0.74"),
            (
                "debug.rustyquest.makepad.projection.area.offset.x.uv",
                "0.03",
            ),
            (
                "debug.rustyquest.makepad.projection.area.offset.y.uv",
                "-0.02",
            ),
            (
                "debug.rustyquest.makepad.projection.area.left.offset.x.uv",
                "-0.04",
            ),
            (
                "debug.rustyquest.makepad.projection.area.right.offset.x.uv",
                "0.04",
            ),
            (
                "debug.rustyquest.makepad.projection.area.radius.x.uv",
                "0.44",
            ),
            (
                "debug.rustyquest.makepad.projection.area.radius.y.uv",
                "0.31",
            ),
            ("debug.rustyquest.makepad.projection.area.opacity", "0.90"),
            ("debug.rustyquest.makepad.projection.border.opacity", "0.80"),
            (
                "debug.rustyquest.makepad.projection.border.policy",
                "solid-red",
            ),
            (
                "debug.rustyquest.makepad.projection.target.offset.x.uv",
                "0.05",
            ),
            (
                "debug.rustyquest.makepad.projection.target.offset.y.uv",
                "-0.03",
            ),
            ("debug.rustyquest.makepad.projection.target.scale", "0.80"),
            (
                "debug.rustyquest.makepad.projection.target.joystick.controls",
                "offset-scale",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.controls",
                "scale",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.stream",
                "stream.breath.volume.selected",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.scale.mode",
                "state-ramp",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.min.scale",
                "1.0",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.max.scale",
                "5.0",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.inhale.seconds.min.to.max",
                "4.0",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.exhale.seconds.max.to.min",
                "4.0",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.smoothing.alpha",
                "0.30",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.invert",
                "true",
            ),
            (
                "debug.rustyquest.makepad.projection.target.breath.min.quality",
                "0.20",
            ),
            ("debug.rustyquest.makepad.projection.alpha.mode", "fixed"),
            ("debug.rustyquest.makepad.projection.alpha.scale", "1.10"),
            ("debug.rustyquest.makepad.projection.alpha.bias", "-0.05"),
            ("debug.rustyquest.makepad.source.eye.mapping", "left-right"),
            (
                "debug.rustyquest.makepad.source.texture.transform.source",
                "metadata",
            ),
            ("debug.rustyquest.makepad.source.visible.rect.x.uv", "0.10"),
            ("debug.rustyquest.makepad.source.visible.rect.y.uv", "0.20"),
            (
                "debug.rustyquest.makepad.source.visible.rect.width.uv",
                "0.80",
            ),
            (
                "debug.rustyquest.makepad.source.visible.rect.height.uv",
                "0.60",
            ),
        ],
    );

    assert_eq!(launch_alias_snapshot, canonical_snapshot);
    assert_eq!(canonical_snapshot, property_snapshot);
    assert!(
        parse_projection_runtime_pairs(
            RuntimeConfigSource::CommandLine,
            [("source_kind", "synthetic")]
        )
        .is_err(),
        "source kind must not become a projection-runtime key"
    );
}

#[test]
fn projection_runtime_golden_matrix_covers_canvas_and_underlay_profiles() {
    let canvas = projection_runtime_golden_snapshot(
        "hwb",
        &[
            ("makepad.cameraProjectionMode", "world-canvas"),
            ("makepad.projectionAreaScaleX", "0.70"),
            ("makepad.projectionAreaScaleY", "0.55"),
            ("makepad.projectionBorderPolicy", "solid-red"),
        ],
        &[],
    );
    assert!(canvas.contains(&(
        KEY_CAMERA_PROJECTION_MODE,
        RuntimeValue::Text("world-canvas".to_string())
    )));
    assert!(canvas.contains(&(
        KEY_PROJECTION_BORDER_POLICY,
        RuntimeValue::Text("solid-red".to_string())
    )));

    let underlay = projection_runtime_golden_snapshot(
        "oes",
        &[
            ("makepad.projectionBorderPolicy", "passthrough-underlay"),
            ("makepad.projectionAreaOpacity", "0.65"),
            ("makepad.projectionBorderOpacity", "0.0"),
            ("makepad.projectionAlphaMode", "luma"),
        ],
        &[],
    );
    assert!(underlay.contains(&(
        KEY_PROJECTION_BORDER_POLICY,
        RuntimeValue::Text("passthrough-underlay".to_string())
    )));
    assert!(underlay.contains(&(KEY_PROJECTION_AREA_OPACITY, RuntimeValue::Float(0.65))));
    assert!(underlay.contains(&(KEY_PROJECTION_BORDER_OPACITY, RuntimeValue::Float(0.0))));
    assert!(underlay.contains(&(
        KEY_PROJECTION_ALPHA_MODE,
        RuntimeValue::Text("luma".to_string())
    )));
}

#[test]
fn resolves_layered_runtime_config_with_trace() {
    let defaults = RuntimeConfig::parse_pairs(
        RuntimeConfigSource::Default,
        [
            ("projection_depth_meters", "1.0"),
            ("projection_area_scale_x", "1.0"),
        ],
    )
    .expect("defaults should parse");
    let launch = RuntimeConfig::parse_pairs(
        RuntimeConfigSource::CommandLine,
        [("projection_depth_meters", "1.25")],
    )
    .expect("launch values should parse");
    let properties = RuntimeConfig::parse_pairs(
        RuntimeConfigSource::AndroidProperty,
        [("projection_depth_meters", "1.5")],
    )
    .expect("property values should parse");

    let resolution = RuntimeConfigResolver::new()
        .with_layer(RuntimeConfigLayer::new("backend-defaults", 0, defaults).unwrap())
        .with_layer(RuntimeConfigLayer::new("launch-profile", 10, launch).unwrap())
        .with_layer(RuntimeConfigLayer::new("android-properties", 20, properties).unwrap())
        .resolve();

    assert_eq!(
        resolution.resolved().get("projection_depth_meters"),
        Some(&RuntimeValue::Float(1.5))
    );

    let setting = resolution
        .get("projection_depth_meters")
        .expect("depth should be resolved");
    assert_eq!(setting.source, RuntimeConfigSource::AndroidProperty);
    assert_eq!(setting.owner.as_str(), "android-properties");
    assert_eq!(setting.default_value, Some(RuntimeValue::Float(1.0)));
    assert_eq!(setting.candidates.len(), 3);
    assert_eq!(
        setting
            .overridden_candidates()
            .map(|candidate| candidate.owner.as_str())
            .collect::<Vec<_>>(),
        ["launch-profile", "backend-defaults"]
    );
}

#[test]
fn later_layer_wins_equal_precedence() {
    let first = RuntimeConfig::parse_pairs(
        RuntimeConfigSource::File,
        [("projection_depth_meters", "1.1")],
    )
    .expect("file values should parse");
    let second = RuntimeConfig::parse_pairs(
        RuntimeConfigSource::Environment,
        [("projection_depth_meters", "1.2")],
    )
    .expect("env values should parse");

    let resolution = RuntimeConfigResolver::new()
        .with_layer(RuntimeConfigLayer::new("file-profile", 10, first).unwrap())
        .with_layer(RuntimeConfigLayer::new("env-profile", 10, second).unwrap())
        .resolve();

    let setting = resolution
        .get("projection_depth_meters")
        .expect("depth should be resolved");
    assert_eq!(setting.value, RuntimeValue::Float(1.2));
    assert_eq!(setting.owner.as_str(), "env-profile");
}

#[test]
fn rejects_invalid_owner_labels() {
    let config = RuntimeConfig::new();

    assert_eq!(
        RuntimeConfigLayer::new("Launch Profile", 0, config).unwrap_err(),
        RuntimeConfigError::InvalidOwner("Launch Profile".to_string())
    );
}

#[cfg(feature = "serde")]
#[test]
fn runtime_config_round_trips_with_serde() {
    let config = RuntimeConfig::parse_pairs(
        RuntimeConfigSource::Synthetic,
        [("render_scale", "0.8"), ("capture_enabled", "true")],
    )
    .expect("pairs should parse");

    let encoded = serde_json::to_string(&config).expect("config should serialize");
    let decoded: RuntimeConfig = serde_json::from_str(&encoded).expect("config should deserialize");

    assert_eq!(decoded, config);
}
