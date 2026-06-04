from __future__ import annotations


MAKEPAD_VISUAL_PROFILE_ID = "makepad-direct-hwb-target-inner-band-stretch"

MAKEPAD_VISUAL_PROFILE_RUNTIME_PROPERTIES = {
    "debug.rustyxr.processing.layer": "peripheral-stretch",
    "debug.rustyxr.makepad.processing.layer": "peripheral-stretch",
    "debug.rustyxr.camera.source.sampling.mode": "target-local-raster",
    "debug.rustyxr.makepad.camera.source.sampling.mode": "target-local-raster",
    "debug.rustyxr.projection.border.policy": "passthrough-underlay",
    "debug.rustyxr.projection.border.opacity": "0.0",
    "debug.rustyxr.makepad.projection.border.policy": "passthrough-underlay",
    "debug.rustyxr.makepad.projection.border.opacity": "0.0",
    "debug.rustyxr.peripheral.stretch.mode": "edge-stretch",
    "debug.rustyxr.peripheral.stretch.blend.mode": "target-inner-band",
    "debug.rustyxr.peripheral.stretch.debug": "off",
}


def makepad_visual_profile_runtime_properties() -> dict[str, str]:
    return dict(MAKEPAD_VISUAL_PROFILE_RUNTIME_PROPERTIES)


def makepad_visual_profile_property_records() -> list[dict[str, str]]:
    return [
        {"key": key, "value": value}
        for key, value in MAKEPAD_VISUAL_PROFILE_RUNTIME_PROPERTIES.items()
    ]
