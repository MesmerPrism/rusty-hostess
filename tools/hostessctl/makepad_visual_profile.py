from __future__ import annotations


MAKEPAD_VISUAL_PROFILE_ID = "makepad-direct-hwb-target-inner-band-stretch"

VISUAL_PROFILE_PROCESSING_LAYER_PROPERTY = "debug.rustyquest.makepad.processing.layer"
VISUAL_PROFILE_SOURCE_SAMPLING_MODE_PROPERTY = (
    "debug.rustyquest.makepad.camera.source.sampling.mode"
)
VISUAL_PROFILE_PROJECTION_BORDER_POLICY_PROPERTY = (
    "debug.rustyquest.makepad.projection.border.policy"
)
VISUAL_PROFILE_PROJECTION_BORDER_OPACITY_PROPERTY = (
    "debug.rustyquest.makepad.projection.border.opacity"
)
VISUAL_PROFILE_PERIPHERAL_STRETCH_MODE_PROPERTY = (
    "debug.rustyquest.makepad.peripheral.stretch.mode"
)
VISUAL_PROFILE_PERIPHERAL_STRETCH_BLEND_MODE_PROPERTY = (
    "debug.rustyquest.makepad.peripheral.stretch.blend.mode"
)
VISUAL_PROFILE_PERIPHERAL_STRETCH_DEBUG_PROPERTY = (
    "debug.rustyquest.makepad.peripheral.stretch.debug"
)

MAKEPAD_VISUAL_PROFILE_RUNTIME_PROPERTIES = {
    VISUAL_PROFILE_PROCESSING_LAYER_PROPERTY: "peripheral-stretch",
    VISUAL_PROFILE_SOURCE_SAMPLING_MODE_PROPERTY: "target-local-raster",
    VISUAL_PROFILE_PROJECTION_BORDER_POLICY_PROPERTY: "passthrough-underlay",
    VISUAL_PROFILE_PROJECTION_BORDER_OPACITY_PROPERTY: "0.0",
    VISUAL_PROFILE_PERIPHERAL_STRETCH_MODE_PROPERTY: "edge-stretch",
    VISUAL_PROFILE_PERIPHERAL_STRETCH_BLEND_MODE_PROPERTY: "target-inner-band",
    VISUAL_PROFILE_PERIPHERAL_STRETCH_DEBUG_PROPERTY: "off",
}

MAKEPAD_VISUAL_PROFILE_SOURCE_SETTINGS = {
    VISUAL_PROFILE_PROCESSING_LAYER_PROPERTY: "makepad.processing.layer",
    VISUAL_PROFILE_SOURCE_SAMPLING_MODE_PROPERTY: "makepad.camera.source_sampling.mode",
    VISUAL_PROFILE_PROJECTION_BORDER_POLICY_PROPERTY: "makepad.projection.border.policy",
    VISUAL_PROFILE_PROJECTION_BORDER_OPACITY_PROPERTY: "makepad.projection.border.opacity",
    VISUAL_PROFILE_PERIPHERAL_STRETCH_MODE_PROPERTY: "makepad.peripheral_stretch.mode",
    VISUAL_PROFILE_PERIPHERAL_STRETCH_BLEND_MODE_PROPERTY: (
        "makepad.peripheral_stretch.blend_mode"
    ),
    VISUAL_PROFILE_PERIPHERAL_STRETCH_DEBUG_PROPERTY: "makepad.peripheral_stretch.debug",
}

def makepad_visual_profile_runtime_properties() -> dict[str, str]:
    return dict(MAKEPAD_VISUAL_PROFILE_RUNTIME_PROPERTIES)


def makepad_visual_profile_property_records() -> list[dict[str, str]]:
    properties = makepad_visual_profile_runtime_properties()
    return [
        {
            "key": key,
            "value": value,
            "source_setting_id": MAKEPAD_VISUAL_PROFILE_SOURCE_SETTINGS[key],
            "profile_id": MAKEPAD_VISUAL_PROFILE_ID,
        }
        for key, value in properties.items()
    ]
