use crate::runtime_settings::marker_token;
use rusty_makepad_settings::{EffectiveSettingsReport, EFFECTIVE_SETTINGS_SCHEMA};
use rusty_quest_makepad_camera_shell::CameraShellReplayConfig;
use serde_json::Value;
use std::path::{Path, PathBuf};

pub(crate) const EFFECTIVE_SETTINGS_RECEIPT_SCHEMA: &str =
    "rusty.hostess.makepad_effective_settings_receipt.v1";
const MARKER_PREFIX: &str = "RUSTY_HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS";
const NOT_CONFIGURED_ISSUE: &str = "hostess.issue.makepad_effective_settings_not_configured";
const READ_ISSUE: &str = "hostess.issue.makepad_effective_settings_read";
const PARSE_ISSUE: &str = "hostess.issue.makepad_effective_settings_parse";
const SCHEMA_ISSUE: &str = "hostess.issue.makepad_effective_settings_schema";
const MESH_REPLAY_ADAPTER: &str = "rusty-quest-makepad-camera-shell";
const RENDER_SCALE_SETTING: &str = "makepad.render.scale";

#[cfg(target_os = "android")]
const ANDROID_INTERNAL_SETTINGS_ROOT: &str =
    "/data/user/0/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/settings";
#[cfg(target_os = "android")]
const ANDROID_EXTERNAL_SETTINGS_ROOT: &str =
    "/sdcard/Android/data/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/settings";

#[derive(Clone, Debug, Default)]
pub(crate) struct MakepadEffectiveSettingsReceipt {
    status: String,
    issue_code: Option<String>,
    issue_evidence: Option<String>,
    source_effective_settings_path: Option<String>,
    source_effective_settings_schema: Option<String>,
    source_app_id: Option<String>,
    source_surface_schema: Option<String>,
    source_surface_version: Option<u32>,
    source_revision: Option<u64>,
    source_generated_at: Option<String>,
    setting_count: usize,
    canonical_effective_settings_consumed: bool,
    mesh_replay_settings_present: bool,
    mesh_replay_adapter: Option<String>,
    mesh_replay_adapter_status: Option<String>,
    mesh_replay_adapter_error: Option<String>,
    mesh_replay_enabled: Option<bool>,
    mesh_replay_source: Option<String>,
    mesh_replay_speed: Option<f64>,
    mesh_replay_opacity: Option<f64>,
    render_scale: Option<f64>,
    legacy_settings_fallback_used: bool,
    receipt_written: bool,
}

impl MakepadEffectiveSettingsReceipt {
    pub(crate) fn marker_line(&self, phase: &str) -> String {
        format!(
            "{} schema={} phase={} status={} issue={} sourcePath={} app={} revision={} settingCount={} canonicalEffectiveSettingsConsumed={} meshReplaySettingsPresent={} meshReplayAdapter={} meshReplayAdapterStatus={} meshReplayAdapterError={} meshReplayEnabled={} meshReplaySource={} meshReplaySpeed={} meshReplayOpacity={} renderScale={} legacySettingsFallbackUsed={}",
            MARKER_PREFIX,
            EFFECTIVE_SETTINGS_RECEIPT_SCHEMA,
            marker_token(phase),
            marker_token(&self.status),
            marker_option(self.issue_code.as_deref()),
            marker_option(self.source_effective_settings_path.as_deref()),
            marker_option(self.source_app_id.as_deref()),
            self.source_revision
                .map(|value| value.to_string())
                .unwrap_or_else(|| "none".to_string()),
            self.setting_count,
            self.canonical_effective_settings_consumed,
            self.mesh_replay_settings_present,
            marker_option(self.mesh_replay_adapter.as_deref()),
            marker_option(self.mesh_replay_adapter_status.as_deref()),
            marker_option(self.mesh_replay_adapter_error.as_deref()),
            self.mesh_replay_enabled
                .map(|value| value.to_string())
                .unwrap_or_else(|| "none".to_string()),
            marker_option(self.mesh_replay_source.as_deref()),
            marker_f64(self.mesh_replay_speed),
            marker_f64(self.mesh_replay_opacity),
            marker_f64(self.render_scale),
            self.legacy_settings_fallback_used,
        )
    }

    pub(crate) fn render_scale(&self) -> Option<f64> {
        self.render_scale
    }

    fn to_json_value(&self) -> Value {
        serde_json::json!({
            "$schema": EFFECTIVE_SETTINGS_RECEIPT_SCHEMA,
            "status": self.status,
            "issue_code": self.issue_code,
            "issue_evidence": self.issue_evidence,
            "source_effective_settings_path": self.source_effective_settings_path,
            "source_effective_settings_schema": self.source_effective_settings_schema,
            "source_app_id": self.source_app_id,
            "source_surface_schema": self.source_surface_schema,
            "source_surface_version": self.source_surface_version,
            "source_revision": self.source_revision,
            "source_generated_at": self.source_generated_at,
            "setting_count": self.setting_count,
            "canonical_effective_settings_consumed": self.canonical_effective_settings_consumed,
            "mesh_replay_settings_present": self.mesh_replay_settings_present,
            "mesh_replay_adapter": self.mesh_replay_adapter,
            "mesh_replay_adapter_status": self.mesh_replay_adapter_status,
            "mesh_replay_adapter_error": self.mesh_replay_adapter_error,
            "mesh_replay_enabled": self.mesh_replay_enabled,
            "mesh_replay_source": self.mesh_replay_source,
            "mesh_replay_speed": self.mesh_replay_speed,
            "mesh_replay_opacity": self.mesh_replay_opacity,
            "render_scale": self.render_scale,
            "legacy_settings_fallback_used": self.legacy_settings_fallback_used,
            "receipt_written": self.receipt_written,
        })
    }
}

pub(crate) fn read_selected_makepad_effective_settings() -> MakepadEffectiveSettingsReceipt {
    let Some(path) = selected_effective_settings_path() else {
        return not_configured_receipt();
    };
    read_makepad_effective_settings_from_path(&path)
}

pub(crate) fn read_makepad_effective_settings_from_path(
    path: &Path,
) -> MakepadEffectiveSettingsReceipt {
    let text = match std::fs::read_to_string(path) {
        Ok(text) => text,
        Err(error) => {
            return rejected_receipt(Some(path), READ_ISSUE, &format!("read failed: {error}"))
        }
    };
    let report = match serde_json::from_str::<EffectiveSettingsReport>(&text) {
        Ok(report) => report,
        Err(error) => {
            return rejected_receipt(Some(path), PARSE_ISSUE, &format!("parse failed: {error}"))
        }
    };
    if report.schema != EFFECTIVE_SETTINGS_SCHEMA {
        return rejected_receipt(
            Some(path),
            SCHEMA_ISSUE,
            &format!("unsupported schema {}", report.schema),
        );
    }
    ready_receipt(path, report, &text)
}

pub(crate) fn write_selected_makepad_effective_settings_receipt(
    receipt: &MakepadEffectiveSettingsReceipt,
) -> Result<Option<PathBuf>, String> {
    let Some(path) = selected_effective_settings_receipt_output_path() else {
        return Ok(None);
    };
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|error| format!("create {}: {error}", parent.display()))?;
    }
    let mut writable = receipt.clone();
    writable.receipt_written = true;
    let json = serde_json::to_string_pretty(&writable.to_json_value())
        .map_err(|error| format!("encode Makepad effective-settings receipt: {error}"))?;
    std::fs::write(&path, format!("{json}\n"))
        .map_err(|error| format!("write {}: {error}", path.display()))?;
    Ok(Some(path))
}

fn ready_receipt(
    path: &Path,
    report: EffectiveSettingsReport,
    raw_json: &str,
) -> MakepadEffectiveSettingsReceipt {
    let mesh_replay_adapter = Some(MESH_REPLAY_ADAPTER.to_string());
    let (
        mesh_replay_adapter_status,
        mesh_replay_adapter_error,
        mesh_replay_settings_present,
        mesh_replay_enabled,
        mesh_replay_source,
        mesh_replay_speed,
        mesh_replay_opacity,
    ) = match CameraShellReplayConfig::from_effective_settings_json(raw_json) {
        Ok(config) => (
            Some("ready".to_string()),
            None,
            true,
            Some(config.enabled),
            Some(config.source),
            Some(f64::from(config.speed)),
            Some(f64::from(config.opacity)),
        ),
        Err(error) => (
            Some("rejected".to_string()),
            Some(error.to_string()),
            false,
            None,
            None,
            None,
            None,
        ),
    };
    let render_scale = number_setting(&report, RENDER_SCALE_SETTING);

    MakepadEffectiveSettingsReceipt {
        status: "ready".to_string(),
        issue_code: None,
        issue_evidence: None,
        source_effective_settings_path: Some(path.display().to_string()),
        source_effective_settings_schema: Some(report.schema),
        source_app_id: Some(report.app_id),
        source_surface_schema: Some(report.surface_schema),
        source_surface_version: Some(report.surface_version),
        source_revision: Some(report.revision),
        source_generated_at: Some(report.generated_at),
        setting_count: report.settings.len(),
        canonical_effective_settings_consumed: true,
        mesh_replay_settings_present,
        mesh_replay_adapter,
        mesh_replay_adapter_status,
        mesh_replay_adapter_error,
        mesh_replay_enabled,
        mesh_replay_source,
        mesh_replay_speed,
        mesh_replay_opacity,
        render_scale,
        legacy_settings_fallback_used: false,
        receipt_written: false,
    }
}

fn not_configured_receipt() -> MakepadEffectiveSettingsReceipt {
    MakepadEffectiveSettingsReceipt {
        status: "not_configured".to_string(),
        issue_code: Some(NOT_CONFIGURED_ISSUE.to_string()),
        issue_evidence: Some("No Makepad effective-settings path was configured".to_string()),
        legacy_settings_fallback_used: false,
        ..Default::default()
    }
}

fn rejected_receipt(
    path: Option<&Path>,
    issue_code: &str,
    evidence: &str,
) -> MakepadEffectiveSettingsReceipt {
    MakepadEffectiveSettingsReceipt {
        status: "rejected".to_string(),
        issue_code: Some(issue_code.to_string()),
        issue_evidence: Some(evidence.to_string()),
        source_effective_settings_path: path.map(|path| path.display().to_string()),
        legacy_settings_fallback_used: false,
        ..Default::default()
    }
}

fn selected_effective_settings_path() -> Option<PathBuf> {
    if let Some(path) = arg_value("--makepad-effective-settings") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("RUSTY_MAKEPAD_EFFECTIVE_SETTINGS") {
        return Some(PathBuf::from(path));
    }
    default_effective_settings_candidates()
        .into_iter()
        .find(|path| path.is_file())
}

fn selected_effective_settings_receipt_output_path() -> Option<PathBuf> {
    if let Some(path) = arg_value("--makepad-effective-settings-receipt-out") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS_RECEIPT_OUT") {
        return Some(PathBuf::from(path));
    }
    default_effective_settings_receipt_output_path()
}

fn arg_value(flag: &str) -> Option<String> {
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == flag {
            return args.next();
        }
    }
    None
}

#[cfg(target_os = "android")]
fn default_effective_settings_candidates() -> Vec<PathBuf> {
    vec![
        PathBuf::from(format!(
            "{ANDROID_INTERNAL_SETTINGS_ROOT}/makepad-effective-settings.json"
        )),
        PathBuf::from(format!(
            "{ANDROID_EXTERNAL_SETTINGS_ROOT}/makepad-effective-settings.json"
        )),
    ]
}

#[cfg(not(target_os = "android"))]
fn default_effective_settings_candidates() -> Vec<PathBuf> {
    Vec::new()
}

#[cfg(target_os = "android")]
fn default_effective_settings_receipt_output_path() -> Option<PathBuf> {
    Some(PathBuf::from(format!(
        "{ANDROID_INTERNAL_SETTINGS_ROOT}/makepad-effective-settings-receipt.json"
    )))
}

#[cfg(not(target_os = "android"))]
fn default_effective_settings_receipt_output_path() -> Option<PathBuf> {
    None
}

fn marker_option(value: Option<&str>) -> String {
    value
        .map(marker_token)
        .unwrap_or_else(|| "none".to_string())
}

fn marker_f64(value: Option<f64>) -> String {
    match value {
        Some(value) if value.is_finite() => format!("{value:.3}"),
        _ => "none".to_string(),
    }
}

fn number_setting(report: &EffectiveSettingsReport, setting_id: &str) -> Option<f64> {
    setting_value(report, setting_id)
        .and_then(Value::as_f64)
        .filter(|value| value.is_finite())
}

fn setting_value<'a>(report: &'a EffectiveSettingsReport, setting_id: &str) -> Option<&'a Value> {
    report
        .settings
        .iter()
        .find(|setting| setting.setting_id == setting_id)
        .map(|setting| &setting.value)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusty_quest_makepad_camera_shell::CAMERA_SHELL_APP_ID;
    use std::time::{SystemTime, UNIX_EPOCH};

    const EFFECTIVE_SETTINGS_FIXTURE: &str = include_str!(
        "../../../../rusty-quest-makepad/fixtures/effective-settings/mesh-replay.effective-settings.json"
    );

    #[test]
    fn reads_canonical_effective_settings_with_mesh_replay_values() {
        let path = write_temp_json("effective-settings", EFFECTIVE_SETTINGS_FIXTURE);

        let receipt = read_makepad_effective_settings_from_path(&path);

        assert_eq!(receipt.status, "ready");
        assert!(receipt.canonical_effective_settings_consumed);
        assert!(receipt.mesh_replay_settings_present);
        assert_eq!(
            receipt.mesh_replay_adapter.as_deref(),
            Some(MESH_REPLAY_ADAPTER)
        );
        assert_eq!(receipt.mesh_replay_adapter_status.as_deref(), Some("ready"));
        assert_eq!(receipt.source_app_id.as_deref(), Some(CAMERA_SHELL_APP_ID));
        assert_eq!(receipt.mesh_replay_enabled, Some(true));
        assert_eq!(
            receipt.mesh_replay_source.as_deref(),
            Some("public-synthetic-hand-sequence")
        );
        assert_eq!(receipt.mesh_replay_speed, Some(1.5));
        assert_eq!(receipt.mesh_replay_opacity, Some(0.75));
        assert_eq!(receipt.render_scale, Some(0.9));
        assert!(!receipt.legacy_settings_fallback_used);

        let marker = receipt.marker_line("test");
        assert!(marker.contains("schema=rusty.hostess.makepad_effective_settings_receipt.v1"));
        assert!(marker.contains("canonicalEffectiveSettingsConsumed=true"));
        assert!(marker.contains("meshReplaySettingsPresent=true"));
        assert!(marker.contains("meshReplayAdapter=rusty-quest-makepad-camera-shell"));
        assert!(marker.contains("meshReplayAdapterStatus=ready"));
        assert!(marker.contains("renderScale=0.900"));
        assert!(!marker.contains("rustyxr"));
        assert!(!marker.contains("rusty.xr"));
    }

    #[test]
    fn records_mesh_replay_adapter_rejection_without_legacy_fallback() {
        let different_app = EFFECTIVE_SETTINGS_FIXTURE
            .replace(CAMERA_SHELL_APP_ID, "rusty-quest-makepad.other-shell");
        let path = write_temp_json("wrong-effective-settings-app", &different_app);

        let receipt = read_makepad_effective_settings_from_path(&path);

        assert_eq!(receipt.status, "ready");
        assert!(receipt.canonical_effective_settings_consumed);
        assert!(!receipt.mesh_replay_settings_present);
        assert_eq!(
            receipt.mesh_replay_adapter_status.as_deref(),
            Some("rejected")
        );
        assert!(receipt
            .mesh_replay_adapter_error
            .as_deref()
            .is_some_and(|error| error.contains("unexpected effective-settings app id")));
        assert!(!receipt.legacy_settings_fallback_used);
    }

    #[test]
    fn rejects_wrong_effective_settings_schema() {
        let damaged = EFFECTIVE_SETTINGS_FIXTURE.replace(
            EFFECTIVE_SETTINGS_SCHEMA,
            "rusty.gui.makepad.old_settings.v1",
        );
        let path = write_temp_json("wrong-effective-settings-schema", &damaged);

        let receipt = read_makepad_effective_settings_from_path(&path);

        assert_eq!(receipt.status, "rejected");
        assert_eq!(receipt.issue_code.as_deref(), Some(SCHEMA_ISSUE));
        assert!(!receipt.canonical_effective_settings_consumed);
        assert!(!receipt.legacy_settings_fallback_used);
    }

    #[test]
    fn not_configured_receipt_does_not_use_legacy_fallback() {
        let receipt = not_configured_receipt();

        assert_eq!(receipt.status, "not_configured");
        assert_eq!(receipt.issue_code.as_deref(), Some(NOT_CONFIGURED_ISSUE));
        assert!(!receipt.legacy_settings_fallback_used);
    }

    fn write_temp_json(name: &str, text: &str) -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock before Unix epoch")
            .as_nanos();
        let root = std::env::temp_dir().join(format!("{name}-{stamp}"));
        std::fs::create_dir_all(&root).expect("create temp root");
        let path = root.join("settings.json");
        std::fs::write(&path, text).expect("write effective settings fixture");
        path
    }
}
