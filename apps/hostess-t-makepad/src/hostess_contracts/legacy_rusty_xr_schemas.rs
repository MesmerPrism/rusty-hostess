//! Frozen `rusty.xr.*` schema identifiers kept for serialized compatibility.
//!
//! New Hostess, Manifold, Quest, Lattice, Matter, Optics, or GUI contracts
//! should not add default schema IDs here. This module is the compatibility
//! ledger for old serialized Hostess contract DTOs until each contract moves to
//! its owning Rusty Morphospace lane.

/// Audit entry for one frozen legacy schema identifier.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LegacyRustyXrSchema {
    pub constant: &'static str,
    pub schema: &'static str,
    pub owner_module: &'static str,
}

impl LegacyRustyXrSchema {
    pub const fn new(
        constant: &'static str,
        schema: &'static str,
        owner_module: &'static str,
    ) -> Self {
        Self {
            constant,
            schema,
            owner_module,
        }
    }
}

/// Legacy schema id for source-sampling contracts kept for serialized compatibility.
pub const LEGACY_RUSTY_XR_SOURCE_SAMPLING_CONTRACT_SCHEMA: &str =
    "rusty.xr.source-sampling-contract.v1";

/// Legacy schema id for camera texture lane contracts kept for serialized compatibility.
pub const LEGACY_RUSTY_XR_CAMERA_TEXTURE_LANE_CONTRACT_SCHEMA: &str =
    "rusty.xr.camera-texture-lane-contract.v1";

/// Legacy schema id for camera-source diagnostics kept for serialized compatibility.
pub const LEGACY_RUSTY_XR_CAMERA_SOURCE_DIAGNOSTICS_SCHEMA: &str =
    "rusty.xr.camera-source-diagnostics.v1";

/// Legacy serialized schema id for depth/world-space contract packets.
pub const LEGACY_RUSTY_XR_DEPTH_WORLD_SPACE_CONTRACT_SCHEMA: &str =
    "rusty.xr.depth_world_space_contract.v1";

/// Legacy serialized schema id for generic effect-stack descriptors.
pub const LEGACY_RUSTY_XR_EFFECT_STACK_DESCRIPTOR_SCHEMA: &str =
    "rusty.xr.effect_stack.descriptor.v1";

/// Legacy serialized schema id for generic effect-stack comparison reports.
pub const LEGACY_RUSTY_XR_EFFECT_STACK_COMPARISON_REPORT_SCHEMA: &str =
    "rusty.xr.effect_stack.comparison_report.v1";

/// Legacy serialized schema id for home panel descriptors.
pub const LEGACY_RUSTY_XR_HOME_PANEL_DESCRIPTOR_SCHEMA: &str = "rusty.xr.home.panel.v1";

/// Legacy serialized schema id for home session state.
pub const LEGACY_RUSTY_XR_HOME_SESSION_STATE_SCHEMA: &str = "rusty.xr.home.state.v1";

/// Legacy serialized schema id for launcher entries.
pub const LEGACY_RUSTY_XR_HOME_LAUNCHER_ENTRY_SCHEMA: &str = "rusty.xr.home.launcher_entry.v1";

/// Legacy serialized schema id for settings shortcut descriptors.
pub const LEGACY_RUSTY_XR_HOME_SETTINGS_SHORTCUT_SCHEMA: &str =
    "rusty.xr.home.settings_shortcut.v1";

/// Legacy serialized schema id for focus recovery events.
pub const LEGACY_RUSTY_XR_HOME_FOCUS_RECOVERY_EVENT_SCHEMA: &str =
    "rusty.xr.home.focus_recovery_event.v1";

/// Legacy serialized schema id for Rusty Kiosk control-plane snapshots.
pub const LEGACY_RUSTY_XR_KIOSK_CONTROL_PLANE_STATUS_SCHEMA: &str =
    "rusty.xr.kiosk.control_plane.v1";

/// Legacy serialized schema id for command evidence embedded in control-plane snapshots.
pub const LEGACY_RUSTY_XR_KIOSK_COMMAND_EVIDENCE_SCHEMA: &str =
    "rusty.xr.kiosk.command_evidence.v1";

/// Legacy serialized schema id for run records that tie API, CLI, MCP, and fallback
/// command paths to before/after kiosk state.
pub const LEGACY_RUSTY_XR_KIOSK_COMMAND_RUN_RECORD_SCHEMA: &str =
    "rusty.xr.kiosk.command_run_record.v1";

/// Legacy serialized schema id for renderer-neutral projection/performance matrix packets.
pub const LEGACY_RUSTY_XR_PROJECTION_PERFORMANCE_MATRIX_SCHEMA: &str =
    "rusty.xr.projection_performance_matrix.v1";

/// Current frozen Hostess-local compatibility registry for old Rusty-XR schema IDs.
pub const LEGACY_RUSTY_XR_SCHEMAS: &[LegacyRustyXrSchema] = &[
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_SOURCE_SAMPLING_CONTRACT_SCHEMA",
        LEGACY_RUSTY_XR_SOURCE_SAMPLING_CONTRACT_SCHEMA,
        "camera",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_CAMERA_TEXTURE_LANE_CONTRACT_SCHEMA",
        LEGACY_RUSTY_XR_CAMERA_TEXTURE_LANE_CONTRACT_SCHEMA,
        "camera",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_CAMERA_SOURCE_DIAGNOSTICS_SCHEMA",
        LEGACY_RUSTY_XR_CAMERA_SOURCE_DIAGNOSTICS_SCHEMA,
        "camera",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_DEPTH_WORLD_SPACE_CONTRACT_SCHEMA",
        LEGACY_RUSTY_XR_DEPTH_WORLD_SPACE_CONTRACT_SCHEMA,
        "depth",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_EFFECT_STACK_DESCRIPTOR_SCHEMA",
        LEGACY_RUSTY_XR_EFFECT_STACK_DESCRIPTOR_SCHEMA,
        "effect_stack",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_EFFECT_STACK_COMPARISON_REPORT_SCHEMA",
        LEGACY_RUSTY_XR_EFFECT_STACK_COMPARISON_REPORT_SCHEMA,
        "effect_stack",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_HOME_PANEL_DESCRIPTOR_SCHEMA",
        LEGACY_RUSTY_XR_HOME_PANEL_DESCRIPTOR_SCHEMA,
        "home",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_HOME_SESSION_STATE_SCHEMA",
        LEGACY_RUSTY_XR_HOME_SESSION_STATE_SCHEMA,
        "home",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_HOME_LAUNCHER_ENTRY_SCHEMA",
        LEGACY_RUSTY_XR_HOME_LAUNCHER_ENTRY_SCHEMA,
        "home",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_HOME_SETTINGS_SHORTCUT_SCHEMA",
        LEGACY_RUSTY_XR_HOME_SETTINGS_SHORTCUT_SCHEMA,
        "home",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_HOME_FOCUS_RECOVERY_EVENT_SCHEMA",
        LEGACY_RUSTY_XR_HOME_FOCUS_RECOVERY_EVENT_SCHEMA,
        "home",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_KIOSK_CONTROL_PLANE_STATUS_SCHEMA",
        LEGACY_RUSTY_XR_KIOSK_CONTROL_PLANE_STATUS_SCHEMA,
        "home",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_KIOSK_COMMAND_EVIDENCE_SCHEMA",
        LEGACY_RUSTY_XR_KIOSK_COMMAND_EVIDENCE_SCHEMA,
        "home",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_KIOSK_COMMAND_RUN_RECORD_SCHEMA",
        LEGACY_RUSTY_XR_KIOSK_COMMAND_RUN_RECORD_SCHEMA,
        "home",
    ),
    LegacyRustyXrSchema::new(
        "LEGACY_RUSTY_XR_PROJECTION_PERFORMANCE_MATRIX_SCHEMA",
        LEGACY_RUSTY_XR_PROJECTION_PERFORMANCE_MATRIX_SCHEMA,
        "projection_matrix",
    ),
];

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    #[test]
    fn legacy_schema_registry_is_unique_and_frozen_to_old_prefix() {
        let mut constants = BTreeSet::new();
        let mut schemas = BTreeSet::new();

        for entry in LEGACY_RUSTY_XR_SCHEMAS {
            assert!(
                constants.insert(entry.constant),
                "duplicate legacy schema constant {}",
                entry.constant
            );
            assert!(
                schemas.insert(entry.schema),
                "duplicate legacy schema value {}",
                entry.schema
            );
            assert!(
                entry.schema.starts_with("rusty.xr."),
                "legacy schema {} must remain an explicit old-lane value",
                entry.constant
            );
        }

        assert_eq!(LEGACY_RUSTY_XR_SCHEMAS.len(), 15);
    }
}
