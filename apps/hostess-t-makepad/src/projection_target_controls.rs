use crate::makepad_runtime_config as makepad_config;
use crate::runtime_settings::{
    hotload_f32, PROJECTION_TARGET_JOYSTICK_DEADZONE, PROJECTION_TARGET_MAX_SCALE,
    PROJECTION_TARGET_MIN_SCALE, PROJECTION_TARGET_OFFSET_RATE_UV_PER_SECOND,
    PROJECTION_TARGET_SCALE_RATE_PER_SECOND, TARGET_PROJECTION_TARGET_OFFSET_X_UV,
    TARGET_PROJECTION_TARGET_OFFSET_Y_UV, TARGET_PROJECTION_TARGET_SCALE,
};

pub(crate) const PROJECTION_TARGET_BREATH_DEFAULT_SMOOTHING_ALPHA: f32 = 0.30;

pub(crate) fn makepad_projection_target_joystick_controls_enabled_from_value(value: &str) -> bool {
    matches!(
        value.trim().to_ascii_lowercase().replace('_', "-").as_str(),
        "offset-scale"
            | "target-offset-scale"
            | "projection-target"
            | "target-footprint"
            | "joystick-offset-scale"
            | "on"
            | "true"
            | "1"
            | "enabled"
    )
}

pub(crate) fn makepad_projection_target_breath_controls_enabled_from_value(value: &str) -> bool {
    matches!(
        value.trim().to_ascii_lowercase().replace('_', "-").as_str(),
        "scale"
            | "breath-scale"
            | "selected-scale"
            | "target-scale"
            | "on"
            | "true"
            | "1"
            | "enabled"
    )
}

pub(crate) fn makepad_projection_target_scale() -> f32 {
    hotload_f32(
        makepad_config::KEY_PROJECTION_TARGET_SCALE,
        TARGET_PROJECTION_TARGET_SCALE,
        PROJECTION_TARGET_MIN_SCALE,
        PROJECTION_TARGET_MAX_SCALE,
    )
}

pub(crate) fn makepad_projection_target_breath_scale(
    volume01: f32,
    min_scale: f32,
    max_scale: f32,
    invert: bool,
) -> f32 {
    let volume01 = if invert { 1.0 - volume01 } else { volume01 }.clamp(0.0, 1.0);
    let lower = min_scale.min(max_scale);
    let upper = min_scale.max(max_scale);
    (min_scale + (max_scale - min_scale) * volume01)
        .clamp(lower, upper)
        .clamp(PROJECTION_TARGET_MIN_SCALE, PROJECTION_TARGET_MAX_SCALE)
}

pub(crate) fn makepad_projection_target_breath_smoothing_alpha(value: f32) -> f32 {
    value.clamp(0.0, 1.0)
}

pub(crate) fn makepad_projection_target_breath_lerp(
    current: f32,
    target: f32,
    smoothing_alpha: f32,
) -> f32 {
    current + (target - current) * makepad_projection_target_breath_smoothing_alpha(smoothing_alpha)
}

pub(crate) fn makepad_projection_target_breath_sample_is_new(
    scale_ready: bool,
    previous_sequence_id: u64,
    sequence_id: u64,
) -> bool {
    !scale_ready || sequence_id != previous_sequence_id
}

pub(crate) fn makepad_projection_target_offset_x_uv() -> f32 {
    hotload_f32(
        makepad_config::KEY_PROJECTION_TARGET_OFFSET_X_UV,
        TARGET_PROJECTION_TARGET_OFFSET_X_UV,
        -0.5,
        0.5,
    )
}

pub(crate) fn makepad_projection_target_offset_y_uv() -> f32 {
    hotload_f32(
        makepad_config::KEY_PROJECTION_TARGET_OFFSET_Y_UV,
        TARGET_PROJECTION_TARGET_OFFSET_Y_UV,
        -0.5,
        0.5,
    )
}

fn makepad_projection_target_deadzone_axis(value: f32) -> f32 {
    if value.abs() <= PROJECTION_TARGET_JOYSTICK_DEADZONE {
        0.0
    } else {
        value.clamp(-1.0, 1.0)
    }
}

pub(crate) fn makepad_projection_target_offset_step(
    current_offset: f32,
    axis: f32,
    dt_seconds: f32,
    y_axis: bool,
) -> Option<f32> {
    let axis = makepad_projection_target_deadzone_axis(axis);
    if axis == 0.0 {
        return None;
    }
    let direction = if y_axis { -axis } else { axis };
    Some(
        (current_offset + direction * PROJECTION_TARGET_OFFSET_RATE_UV_PER_SECOND * dt_seconds)
            .clamp(-0.5, 0.5),
    )
}

pub(crate) fn makepad_projection_target_scale_step(
    current_scale: f32,
    makepad_right_stick_y: f32,
    dt_seconds: f32,
) -> Option<f32> {
    let scale_axis = makepad_projection_target_deadzone_axis(-makepad_right_stick_y);
    if scale_axis == 0.0 {
        return None;
    }
    Some(
        (current_scale + scale_axis * PROJECTION_TARGET_SCALE_RATE_PER_SECOND * dt_seconds)
            .clamp(PROJECTION_TARGET_MIN_SCALE, PROJECTION_TARGET_MAX_SCALE),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn joystick_controls_parse_hwb_offset_scale_aliases() {
        assert!(makepad_projection_target_joystick_controls_enabled_from_value("offset-scale"));
        assert!(
            makepad_projection_target_joystick_controls_enabled_from_value("joystick_offset_scale")
        );
        assert!(!makepad_projection_target_joystick_controls_enabled_from_value("off"));
    }

    #[test]
    fn breath_controls_parse_selected_scale_aliases() {
        assert!(makepad_projection_target_breath_controls_enabled_from_value("scale"));
        assert!(makepad_projection_target_breath_controls_enabled_from_value("selected_scale"));
        assert!(!makepad_projection_target_breath_controls_enabled_from_value("offset-scale"));
    }

    #[test]
    fn breath_volume_maps_default_scale_to_expanded_scale() {
        assert_eq!(
            makepad_projection_target_breath_scale(0.0, TARGET_PROJECTION_TARGET_SCALE, 5.0, false),
            TARGET_PROJECTION_TARGET_SCALE
        );
        assert_eq!(
            makepad_projection_target_breath_scale(1.0, TARGET_PROJECTION_TARGET_SCALE, 5.0, false),
            5.0
        );
        assert_eq!(
            makepad_projection_target_breath_scale(1.0, TARGET_PROJECTION_TARGET_SCALE, 5.0, true),
            TARGET_PROJECTION_TARGET_SCALE
        );
    }

    #[test]
    fn breath_volume_maps_calibrated_scale_to_smaller_endpoint() {
        assert_eq!(
            makepad_projection_target_breath_scale(0.0, 1.0, 0.1796, false),
            1.0
        );
        assert_eq!(
            makepad_projection_target_breath_scale(1.0, 1.0, 0.1796, false),
            0.1796
        );
        assert!(
            (makepad_projection_target_breath_scale(0.5, 1.0, 0.1796, false) - 0.5898).abs()
                < 0.000_01
        );
    }

    #[test]
    fn breath_lerp_smooths_toward_target_without_overshoot() {
        assert!((makepad_projection_target_breath_lerp(1.0, 5.0, 0.30) - 2.2).abs() < 0.000_01);
        assert!((makepad_projection_target_breath_lerp(5.0, 1.0, 0.30) - 3.8).abs() < 0.000_01);
        assert_eq!(makepad_projection_target_breath_lerp(1.0, 5.0, 0.0), 1.0);
        assert_eq!(makepad_projection_target_breath_lerp(1.0, 5.0, 1.0), 5.0);
    }

    #[test]
    fn breath_smoothing_alpha_clamps_to_lerp_domain() {
        assert_eq!(makepad_projection_target_breath_smoothing_alpha(-0.25), 0.0);
        assert_eq!(makepad_projection_target_breath_smoothing_alpha(0.30), 0.30);
        assert_eq!(makepad_projection_target_breath_smoothing_alpha(1.25), 1.0);
    }

    #[test]
    fn breath_marker_sample_identity_tracks_new_sequences() {
        assert!(makepad_projection_target_breath_sample_is_new(false, 0, 12));
        assert!(!makepad_projection_target_breath_sample_is_new(
            true, 12, 12
        ));
        assert!(makepad_projection_target_breath_sample_is_new(true, 12, 13));
    }

    #[test]
    fn left_stick_x_offsets_projection_target() {
        let next = makepad_projection_target_offset_step(0.0, 1.0, 0.1, false)
            .expect("rightward stick should produce an offset step");
        assert!(next > 0.0);
    }

    #[test]
    fn left_stick_up_offsets_projection_target_up_in_display_uv() {
        let next = makepad_projection_target_offset_step(0.0, 1.0, 0.1, true)
            .expect("upward reference stick should produce an offset step");
        assert!(next < 0.0);
    }

    #[test]
    fn right_stick_up_grows_projection_target_scale() {
        let next = makepad_projection_target_scale_step(1.0, -1.0, 0.1)
            .expect("upward stick should produce a scale step");
        assert!(next > 1.0);
    }

    #[test]
    fn right_stick_down_shrinks_projection_target_scale() {
        let next = makepad_projection_target_scale_step(1.0, 1.0, 0.1)
            .expect("downward stick should produce a scale step");
        assert!(next < 1.0);
    }

    #[test]
    fn right_stick_down_allows_minimal_projection_target_scale() {
        let next = makepad_projection_target_scale_step(PROJECTION_TARGET_MIN_SCALE, 1.0, 1.0)
            .expect("downward stick at the floor should still produce a clamped scale");
        assert_eq!(next, PROJECTION_TARGET_MIN_SCALE);
    }

    #[test]
    fn right_stick_up_allows_expanded_projection_target_scale_for_reference_zoom() {
        let next = makepad_projection_target_scale_step(PROJECTION_TARGET_MAX_SCALE, -1.0, 1.0)
            .expect("upward stick at the ceiling should still produce a clamped scale");
        assert_eq!(next, PROJECTION_TARGET_MAX_SCALE);
    }
}
