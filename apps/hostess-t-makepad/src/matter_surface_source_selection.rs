//! Hostess-local low-rate source selection for Matter surface worker input.
//!
//! This selects which already-available provider feeds the Matter worker. It
//! never carries hand joints, meshes, fields, particles, or GPU buffers.

const SOURCE_ARG: &str = "--matter-surface-source";
const SOURCE_ENV: &str = "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_SOURCE";
#[cfg(target_os = "android")]
const SOURCE_ANDROID_PROPERTY: &str = "debug.rustyhostess.makepad.matter.surface.source";

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub(crate) enum MatterSurfaceSourceMode {
    #[default]
    RecordedOrPositionsReplay,
    LiveOpenXrHandAny,
    LiveOpenXrHandLeft,
    LiveOpenXrHandRight,
}

impl MatterSurfaceSourceMode {
    pub(crate) const fn marker_value(self) -> &'static str {
        match self {
            Self::RecordedOrPositionsReplay => "recorded-or-positions-replay",
            Self::LiveOpenXrHandAny => "live-openxr-hand-any",
            Self::LiveOpenXrHandLeft => "live-openxr-hand-left",
            Self::LiveOpenXrHandRight => "live-openxr-hand-right",
        }
    }

    pub(crate) const fn uses_live_openxr_hand(self) -> bool {
        !matches!(self, Self::RecordedOrPositionsReplay)
    }

    pub(crate) const fn live_is_left(self) -> Option<bool> {
        match self {
            Self::RecordedOrPositionsReplay | Self::LiveOpenXrHandAny => None,
            Self::LiveOpenXrHandLeft => Some(true),
            Self::LiveOpenXrHandRight => Some(false),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct MatterSurfaceSourceSelection {
    mode: MatterSurfaceSourceMode,
    selection_source: &'static str,
    requested_value: Option<String>,
    issue: Option<String>,
}

impl Default for MatterSurfaceSourceSelection {
    fn default() -> Self {
        Self {
            mode: MatterSurfaceSourceMode::RecordedOrPositionsReplay,
            selection_source: "default",
            requested_value: None,
            issue: None,
        }
    }
}

impl MatterSurfaceSourceSelection {
    pub(crate) fn from_runtime() -> Self {
        if let Some(value) = arg_value(SOURCE_ARG) {
            return Self::from_value(value, "launch-arg");
        }
        if let Ok(value) = std::env::var(SOURCE_ENV) {
            return Self::from_value(value, "environment");
        }
        #[cfg(target_os = "android")]
        if let Some(value) =
            crate::runtime_settings::android_system_property_value(SOURCE_ANDROID_PROPERTY)
        {
            return Self::from_value(value, "android-property");
        }
        Self::default()
    }

    pub(crate) fn from_value(value: impl Into<String>, selection_source: &'static str) -> Self {
        let raw_value = value.into();
        let trimmed_value = raw_value.trim();
        let requested_value = (!trimmed_value.is_empty()).then(|| trimmed_value.to_string());
        let normalized = trimmed_value.to_ascii_lowercase();
        let mode = match normalized.as_str() {
            ""
            | "default"
            | "replay"
            | "recorded-or-replay"
            | "recorded-or-positions"
            | "recorded-or-positions-replay"
            | "positions-only"
            | "positions-only-surface" => MatterSurfaceSourceMode::RecordedOrPositionsReplay,
            "live"
            | "live-openxr-hand"
            | "live-openxr-hand-any"
            | "live-meta-quest-hand"
            | "live-meta-quest-hand-any" => MatterSurfaceSourceMode::LiveOpenXrHandAny,
            "left" | "live-left" | "live-openxr-hand-left" | "live-meta-quest-hand-left" => {
                MatterSurfaceSourceMode::LiveOpenXrHandLeft
            }
            "right" | "live-right" | "live-openxr-hand-right" | "live-meta-quest-hand-right" => {
                MatterSurfaceSourceMode::LiveOpenXrHandRight
            }
            _ => MatterSurfaceSourceMode::RecordedOrPositionsReplay,
        };
        let issue = if normalized.is_empty()
            || mode != MatterSurfaceSourceMode::RecordedOrPositionsReplay
        {
            None
        } else if matches!(
            normalized.as_str(),
            "default"
                | "replay"
                | "recorded-or-replay"
                | "recorded-or-positions"
                | "recorded-or-positions-replay"
                | "positions-only"
                | "positions-only-surface"
        ) {
            None
        } else {
            Some("invalid_source_selection".to_string())
        };
        Self {
            mode,
            selection_source,
            requested_value,
            issue,
        }
    }

    pub(crate) const fn mode(&self) -> MatterSurfaceSourceMode {
        self.mode
    }

    pub(crate) fn marker_line(&self, phase: &str) -> String {
        let status = if self.issue.is_some() {
            "warning"
        } else {
            "ready"
        };
        format!(
            "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_SOURCE_SELECTION schema=rusty.hostess.makepad.matter_surface_source_selection.v1 phase={} status={} mode={} selectionSource={} requestedValue={} issue={} selectionPlane=low-rate-hostess-runtime-selection liveOpenXrHandProviderSelected={} recordedReplayDefaultPreserved=true positionsOnlySmokePreserved=true gpuAdapterBoundaryUnchanged=true highRateJsonPayload=false",
            crate::runtime_settings::marker_token(phase),
            status,
            self.mode.marker_value(),
            self.selection_source,
            marker_option(self.requested_value.as_deref()),
            marker_option(self.issue.as_deref()),
            self.mode.uses_live_openxr_hand(),
        )
    }
}

fn arg_value(name: &str) -> Option<String> {
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == name {
            return args.next();
        }
        if let Some((key, value)) = arg.split_once('=') {
            if key == name {
                return Some(value.to_string());
            }
        }
    }
    None
}

fn marker_option(value: Option<&str>) -> String {
    value
        .map(crate::runtime_settings::marker_token)
        .unwrap_or_else(|| "none".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_to_recorded_or_positions_replay() {
        let selection = MatterSurfaceSourceSelection::default();
        assert_eq!(
            selection.mode(),
            MatterSurfaceSourceMode::RecordedOrPositionsReplay
        );
        assert!(selection
            .marker_line("unit-test")
            .contains("highRateJsonPayload=false"));
    }

    #[test]
    fn parses_live_openxr_hand_sides() {
        assert_eq!(
            MatterSurfaceSourceSelection::from_value("live-openxr-hand-left", "test").mode(),
            MatterSurfaceSourceMode::LiveOpenXrHandLeft
        );
        assert_eq!(
            MatterSurfaceSourceSelection::from_value("right", "test")
                .mode()
                .live_is_left(),
            Some(false)
        );
    }

    #[test]
    fn invalid_values_fall_back_without_hiding_issue() {
        let selection = MatterSurfaceSourceSelection::from_value("mesh-distance", "test");
        assert_eq!(
            selection.mode(),
            MatterSurfaceSourceMode::RecordedOrPositionsReplay
        );
        let marker = selection.marker_line("unit-test");
        assert!(marker.contains("status=warning"));
        assert!(marker.contains("issue=invalid_source_selection"));
    }
}
