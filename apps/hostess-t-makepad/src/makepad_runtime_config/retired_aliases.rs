//! Retired projection runtime spellings.
//!
//! These entries are intentionally not part of `PROJECTION_RUNTIME_KEY_ALIASES`.
//! They document old names that should be rejected by active runtime parsing
//! while remaining discoverable for property/env cleanup and migration notes.

use super::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RetiredRuntimeKeyAlias {
    pub alias: &'static str,
    pub former_source: RuntimeKeyAliasSource,
    pub retired_status: RuntimeKeyAliasStatus,
    pub replacement: &'static str,
    pub reason: &'static str,
    pub hygiene_action: &'static str,
}

pub const RETIRED_PROJECTION_RUNTIME_KEY_ALIASES: &[RetiredRuntimeKeyAlias] = &[
    RetiredRuntimeKeyAlias {
        alias: "rustyxr.projectionDepthMeters",
        former_source: RuntimeKeyAliasSource::LegacyRuntimeKey,
        retired_status: RuntimeKeyAliasStatus::Legacy,
        replacement: "makepad.projectionDepthMeters",
        reason: "old public/reference Rusty-XR launch/runtime key",
        hygiene_action: "reject active parsing and remove from launch profiles",
    },
    RetiredRuntimeKeyAlias {
        alias: "debug.rustyxr.projection.depth.meters",
        former_source: RuntimeKeyAliasSource::AndroidProperty,
        retired_status: RuntimeKeyAliasStatus::Legacy,
        replacement: "debug.rustyquest.makepad.projection.depth.meters",
        reason: "old public/reference Rusty-XR Android property namespace",
        hygiene_action: "clear before controlled runs and use the Rusty Quest Makepad property",
    },
    RetiredRuntimeKeyAlias {
        alias: "debug.rusty.projection.depth.meters",
        former_source: RuntimeKeyAliasSource::AndroidProperty,
        retired_status: RuntimeKeyAliasStatus::Deprecated,
        replacement: "debug.rustyquest.makepad.projection.depth.meters",
        reason: "generic debug.rusty projection property was too broad for the Quest Makepad app",
        hygiene_action: "clear before controlled runs and use the Rusty Quest Makepad property",
    },
    RetiredRuntimeKeyAlias {
        alias: "debug.rusty.makepad.projection.area.offset.left.uv",
        former_source: RuntimeKeyAliasSource::AndroidProperty,
        retired_status: RuntimeKeyAliasStatus::Deprecated,
        replacement: "debug.rustyquest.makepad.projection.area.left.offset.x.uv",
        reason:
            "mis-scoped Makepad property shape predated the current left/right axis-specific key",
        hygiene_action:
            "clear before controlled runs and use the axis-specific Rusty Quest Makepad property",
    },
    RetiredRuntimeKeyAlias {
        alias: "RUSTY_XR_PROJECTION_DEPTH_METERS",
        former_source: RuntimeKeyAliasSource::EnvironmentVariable,
        retired_status: RuntimeKeyAliasStatus::Legacy,
        replacement: "RUSTY_MAKEPAD_PROJECTION_DEPTH_METERS",
        reason: "old public/reference Rusty-XR environment variable namespace",
        hygiene_action: "unset in shell profiles and use the Rusty Makepad environment variable",
    },
];

pub fn retired_projection_runtime_key_alias(
    alias: &str,
) -> Option<&'static RetiredRuntimeKeyAlias> {
    RETIRED_PROJECTION_RUNTIME_KEY_ALIASES
        .iter()
        .find(|definition| definition.alias == alias)
}
