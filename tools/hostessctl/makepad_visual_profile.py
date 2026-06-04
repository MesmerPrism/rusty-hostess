from __future__ import annotations


MAKEPAD_VISUAL_PROFILE_ID = "makepad-direct-hwb-target-inner-band-stretch"

MAKEPAD_VISUAL_PROFILE_PRIMARY_RUNTIME_PROPERTIES = {
    "debug.rusty.processing.layer": "peripheral-stretch",
    "debug.rusty.makepad.processing.layer": "peripheral-stretch",
    "debug.rusty.camera.source.sampling.mode": "target-local-raster",
    "debug.rusty.makepad.camera.source.sampling.mode": "target-local-raster",
    "debug.rusty.projection.border.policy": "passthrough-underlay",
    "debug.rusty.projection.border.opacity": "0.0",
    "debug.rusty.makepad.projection.border.policy": "passthrough-underlay",
    "debug.rusty.makepad.projection.border.opacity": "0.0",
    "debug.rusty.peripheral.stretch.mode": "edge-stretch",
    "debug.rusty.peripheral.stretch.blend.mode": "target-inner-band",
    "debug.rusty.peripheral.stretch.debug": "off",
}


def with_legacy_rustyxr_property_aliases(properties: dict[str, str]) -> dict[str, str]:
    aliased = dict(properties)
    for key, value in properties.items():
        if key.startswith("debug.rusty."):
            legacy_key = "debug.rustyxr." + key[len("debug.rusty.") :]
            aliased.setdefault(legacy_key, value)
    return aliased


MAKEPAD_VISUAL_PROFILE_RUNTIME_PROPERTIES = with_legacy_rustyxr_property_aliases(
    MAKEPAD_VISUAL_PROFILE_PRIMARY_RUNTIME_PROPERTIES
)


def makepad_visual_profile_runtime_properties() -> dict[str, str]:
    return dict(MAKEPAD_VISUAL_PROFILE_RUNTIME_PROPERTIES)


def makepad_visual_profile_property_records() -> list[dict[str, str]]:
    return [
        {"key": key, "value": value}
        for key, value in MAKEPAD_VISUAL_PROFILE_RUNTIME_PROPERTIES.items()
    ]
