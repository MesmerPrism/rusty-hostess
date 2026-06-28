use crate::makepad_diagnostics::{emit_marker_line, marker_value};
use crate::runtime_settings::marker_token;
use serde_json::{json, Value};
use std::{
    fs,
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

pub(crate) const BRIDGE_COMMAND_REQUEST_SCHEMA: &str = "rusty.hostess.bridge_command.request.v1";
pub(crate) const BRIDGE_COMMAND_RECEIPT_SCHEMA: &str =
    "rusty.hostess.makepad.bridge_command_runtime_receipt.v1";
pub(crate) const BRIDGE_COMMAND_RECEIPT_MARKER: &str =
    "RUSTY_HOSTESS_MAKEPAD_BRIDGE_COMMAND_RECEIPT";
pub(crate) const BRIDGE_PROBE_SET_MARKER_COMMAND: &str = "hostess.makepad.bridge_probe.set_marker";
#[cfg(target_os = "android")]
const DEFAULT_BRIDGE_COMMAND_REQUEST_FILE: &str = "bridge-command-request.json";
#[cfg(target_os = "android")]
const DEFAULT_BRIDGE_COMMAND_RECEIPT_FILE: &str = "bridge-command-receipt.json";

#[cfg(target_os = "android")]
const ANDROID_INTERNAL_SETTINGS_ROOT: &str =
    "/data/user/0/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/settings";

#[derive(Clone, Debug, Default)]
pub(crate) struct BridgeCommandInboxState {
    last_request_id: Option<String>,
    last_rejected_identity: Option<String>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct BridgeCommandApplication {
    pub(crate) request_id: String,
    pub(crate) command: String,
    pub(crate) probe_token: String,
    pub(crate) receipt_json: Value,
    pub(crate) receipt_path: Option<PathBuf>,
}

#[derive(Clone, Debug)]
pub(crate) struct BridgeCommandRequest {
    pub(crate) request_id: String,
    pub(crate) command: String,
    pub(crate) probe_token: String,
    pub(crate) source: String,
    pub(crate) command_transport: String,
}

impl BridgeCommandInboxState {
    pub(crate) fn poll(&mut self, phase: &str) -> Option<BridgeCommandApplication> {
        let path = selected_bridge_command_request_path()?;
        if !path.is_file() {
            return None;
        }
        let identity = request_identity(&path);
        let text = match fs::read_to_string(&path) {
            Ok(text) => text,
            Err(error) => {
                self.emit_changed_rejection(
                    phase,
                    identity,
                    "unknown",
                    "unknown",
                    "hostess.issue.bridge_command_request_read",
                    &format!("read failed: {error}"),
                    Some(path.as_path()),
                );
                return None;
            }
        };
        let request = match parse_bridge_command_request(&text) {
            Ok(request) => request,
            Err(error) => {
                self.emit_changed_rejection(
                    phase,
                    identity,
                    "unknown",
                    "unknown",
                    "hostess.issue.bridge_command_request_parse",
                    &error,
                    Some(path.as_path()),
                );
                return None;
            }
        };
        self.apply_request(phase, request, Some(path.as_path()))
    }

    pub(crate) fn apply_request(
        &mut self,
        phase: &str,
        request: BridgeCommandRequest,
        source_path: Option<&Path>,
    ) -> Option<BridgeCommandApplication> {
        if self.last_request_id.as_deref() == Some(request.request_id.as_str()) {
            return None;
        }
        self.last_request_id = Some(request.request_id.clone());
        self.last_rejected_identity = None;

        if request.command != BRIDGE_PROBE_SET_MARKER_COMMAND {
            let receipt = build_receipt_json(
                phase,
                &request,
                "rejected",
                false,
                false,
                Some("hostess.issue.bridge_command_unsupported"),
                Some("unsupported bridge command"),
                source_path,
            );
            let receipt_path = write_selected_receipt(&receipt).ok();
            emit_receipt_marker(
                phase,
                &request,
                "rejected",
                "fail",
                false,
                false,
                Some("hostess.issue.bridge_command_unsupported"),
                source_path,
                receipt_path.as_deref(),
            );
            return None;
        }

        emit_receipt_marker(
            phase,
            &request,
            "runtime_accepted",
            "pass",
            true,
            false,
            None,
            source_path,
            None,
        );
        let receipt = build_receipt_json(
            phase,
            &request,
            "applied",
            true,
            true,
            None,
            None,
            source_path,
        );
        let receipt_path = write_selected_receipt(&receipt).ok();
        emit_receipt_marker(
            phase,
            &request,
            "applied",
            "pass",
            true,
            true,
            None,
            source_path,
            receipt_path.as_deref(),
        );
        Some(BridgeCommandApplication {
            request_id: request.request_id,
            command: request.command,
            probe_token: request.probe_token,
            receipt_json: receipt,
            receipt_path,
        })
    }

    fn emit_changed_rejection(
        &mut self,
        phase: &str,
        identity: String,
        request_id: &str,
        command: &str,
        issue: &str,
        issue_detail: &str,
        source_path: Option<&Path>,
    ) {
        if self.last_rejected_identity.as_deref() == Some(identity.as_str()) {
            return;
        }
        self.last_rejected_identity = Some(identity);
        let request = BridgeCommandRequest {
            request_id: request_id.to_string(),
            command: command.to_string(),
            probe_token: "none".to_string(),
            source: "app-private-json".to_string(),
            command_transport: "android-app-private-json".to_string(),
        };
        let receipt = build_receipt_json(
            phase,
            &request,
            "rejected",
            false,
            false,
            Some(issue),
            Some(issue_detail),
            source_path,
        );
        let receipt_path = write_selected_receipt(&receipt).ok();
        emit_receipt_marker(
            phase,
            &request,
            "rejected",
            "fail",
            false,
            false,
            Some(issue),
            source_path,
            receipt_path.as_deref(),
        );
    }
}

pub(crate) fn parse_bridge_command_request(text: &str) -> Result<BridgeCommandRequest, String> {
    let value: Value =
        serde_json::from_str(text).map_err(|error| format!("invalid json: {error}"))?;
    parse_bridge_command_request_value(&value)
}

pub(crate) fn parse_bridge_command_request_value(
    value: &Value,
) -> Result<BridgeCommandRequest, String> {
    if value.get("$schema").and_then(Value::as_str) != Some(BRIDGE_COMMAND_REQUEST_SCHEMA) {
        return Err(format!(
            "unsupported schema: {}",
            value
                .get("$schema")
                .and_then(Value::as_str)
                .unwrap_or("missing")
        ));
    }
    let request_id = required_string(&value, "request_id")?;
    let command = required_string(&value, "command")?;
    let params = value.get("params").filter(|params| params.is_object());
    let probe_token = params
        .and_then(|params| params.get("probe_token"))
        .and_then(Value::as_str)
        .or_else(|| {
            params
                .and_then(|params| params.get("marker"))
                .and_then(Value::as_str)
        })
        .unwrap_or(request_id.as_str())
        .to_string();
    let source = params
        .and_then(|params| params.get("source"))
        .and_then(Value::as_str)
        .unwrap_or("app-private-json")
        .to_string();
    let command_transport = params
        .and_then(|params| params.get("command_transport"))
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .map(|value| value.trim().to_string())
        .unwrap_or_else(|| command_transport_for_source(&source).to_string());
    Ok(BridgeCommandRequest {
        request_id,
        command,
        probe_token,
        source,
        command_transport,
    })
}

fn required_string(value: &Value, field: &str) -> Result<String, String> {
    value
        .get(field)
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .map(ToString::to_string)
        .ok_or_else(|| format!("missing required string field: {field}"))
}

fn emit_receipt_marker(
    phase: &str,
    request: &BridgeCommandRequest,
    stage: &str,
    status: &str,
    runtime_accepted: bool,
    applied: bool,
    issue: Option<&str>,
    source_path: Option<&Path>,
    receipt_path: Option<&Path>,
) {
    emit_marker_line(&format!(
        "{} schema={} phase={} status={} requestId={} command={} bridgeRouteStage={} runtimeAccepted={} applied={} probeToken={} source={} sourcePath={} receiptPath={} evidenceRef={} issue={} highRateJsonPayload=false",
        BRIDGE_COMMAND_RECEIPT_MARKER,
        BRIDGE_COMMAND_RECEIPT_SCHEMA,
        marker_token(phase),
        marker_token(status),
        marker_value(&request.request_id),
        marker_value(&request.command),
        marker_token(stage),
        runtime_accepted,
        applied,
        marker_value(&request.probe_token),
        marker_value(&request.source),
        marker_path(source_path),
        marker_path(receipt_path),
        marker_value(evidence_ref_for_stage(stage)),
        issue.map(marker_token).unwrap_or_else(|| "none".to_string()),
    ));
}

fn build_receipt_json(
    phase: &str,
    request: &BridgeCommandRequest,
    status: &str,
    runtime_accepted: bool,
    applied: bool,
    issue: Option<&str>,
    issue_detail: Option<&str>,
    source_path: Option<&Path>,
) -> Value {
    json!({
        "$schema": BRIDGE_COMMAND_RECEIPT_SCHEMA,
        "phase": phase,
        "status": status,
        "request_id": request.request_id,
        "command": request.command,
        "probe_token": request.probe_token,
        "source": request.source,
        "source_path": source_path.map(|path| path.display().to_string()),
        "runtime_accepted": runtime_accepted,
        "applied": applied,
        "issue_code": issue,
        "issue_detail": issue_detail,
        "runtime_authority": "hostess-makepad-app",
        "command_transport": request.command_transport.as_str(),
        "high_rate_json_payload": false,
        "written_at_unix_ns": now_unix_ns(),
        "stage_receipts": stage_receipts(runtime_accepted, applied, issue),
    })
}

fn command_transport_for_source(source: &str) -> &'static str {
    if source.contains("broker") {
        "manifold-broker-stream"
    } else {
        "android-app-private-json"
    }
}

fn stage_receipts(runtime_accepted: bool, applied: bool, issue: Option<&str>) -> Vec<Value> {
    let mut receipts = Vec::new();
    if runtime_accepted {
        receipts.push(json!({
            "stage": "runtime_accepted",
            "status": "pass",
            "evidence_refs": ["evidence.quest.runtime_receipt"],
        }));
    }
    if applied {
        receipts.push(json!({
            "stage": "applied",
            "status": "pass",
            "evidence_refs": ["evidence.quest.effective_state_marker"],
        }));
    }
    if let Some(issue) = issue {
        receipts.push(json!({
            "stage": "rejected",
            "status": "fail",
            "issue_codes": [issue],
            "evidence_refs": ["evidence.quest.runtime_receipt"],
        }));
    }
    receipts
}

fn selected_bridge_command_request_path() -> Option<PathBuf> {
    if let Some(path) = arg_value("--bridge-command-request") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("HOSTESS_MAKEPAD_BRIDGE_COMMAND_REQUEST") {
        return Some(PathBuf::from(path));
    }
    default_bridge_command_request_path()
}

fn selected_bridge_command_receipt_path() -> Option<PathBuf> {
    if let Some(path) = arg_value("--bridge-command-receipt-out") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("HOSTESS_MAKEPAD_BRIDGE_COMMAND_RECEIPT_OUT") {
        return Some(PathBuf::from(path));
    }
    default_bridge_command_receipt_path()
}

fn write_selected_receipt(receipt: &Value) -> Result<PathBuf, String> {
    let path = selected_bridge_command_receipt_path()
        .ok_or_else(|| "bridge command receipt path is not configured".to_string())?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|error| format!("create {}: {error}", parent.display()))?;
    }
    let text = serde_json::to_string_pretty(receipt)
        .map_err(|error| format!("serialize bridge command receipt: {error}"))?;
    fs::write(&path, format!("{text}\n"))
        .map_err(|error| format!("write {}: {error}", path.display()))?;
    Ok(path)
}

#[cfg(target_os = "android")]
fn default_bridge_command_request_path() -> Option<PathBuf> {
    Some(PathBuf::from(format!(
        "{ANDROID_INTERNAL_SETTINGS_ROOT}/{DEFAULT_BRIDGE_COMMAND_REQUEST_FILE}"
    )))
}

#[cfg(not(target_os = "android"))]
fn default_bridge_command_request_path() -> Option<PathBuf> {
    None
}

#[cfg(target_os = "android")]
fn default_bridge_command_receipt_path() -> Option<PathBuf> {
    Some(PathBuf::from(format!(
        "{ANDROID_INTERNAL_SETTINGS_ROOT}/{DEFAULT_BRIDGE_COMMAND_RECEIPT_FILE}"
    )))
}

#[cfg(not(target_os = "android"))]
fn default_bridge_command_receipt_path() -> Option<PathBuf> {
    None
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

fn request_identity(path: &Path) -> String {
    let modified_ns = fs::metadata(path)
        .and_then(|metadata| metadata.modified())
        .ok()
        .and_then(|modified| modified.duration_since(UNIX_EPOCH).ok())
        .map(|duration| duration.as_nanos())
        .unwrap_or_default();
    format!("{}:{modified_ns}", path.display())
}

fn marker_path(path: Option<&Path>) -> String {
    path.map(|path| marker_value(&path.display().to_string()))
        .unwrap_or_else(|| "none".to_string())
}

fn evidence_ref_for_stage(stage: &str) -> &'static str {
    if stage == "applied" {
        "evidence.quest.effective_state_marker"
    } else {
        "evidence.quest.runtime_receipt"
    }
}

fn now_unix_ns() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos())
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn parses_bridge_probe_command_request() {
        let request = parse_bridge_command_request(
            r#"{
              "$schema": "rusty.hostess.bridge_command.request.v1",
              "request_id": "request.test",
              "command": "hostess.makepad.bridge_probe.set_marker",
              "params": {
                "probe_token": "probe-a",
                "source": "unit-test"
              }
            }"#,
        )
        .expect("parse request");

        assert_eq!(request.request_id, "request.test");
        assert_eq!(request.command, BRIDGE_PROBE_SET_MARKER_COMMAND);
        assert_eq!(request.probe_token, "probe-a");
        assert_eq!(request.source, "unit-test");
        assert_eq!(request.command_transport, "android-app-private-json");
    }

    #[test]
    fn applied_receipt_contains_runtime_and_applied_stages() {
        let request = BridgeCommandRequest {
            request_id: "request.test".to_string(),
            command: BRIDGE_PROBE_SET_MARKER_COMMAND.to_string(),
            probe_token: "probe-a".to_string(),
            source: "unit-test".to_string(),
            command_transport: "android-app-private-json".to_string(),
        };

        let receipt = build_receipt_json("unit", &request, "applied", true, true, None, None, None);
        let stages = receipt["stage_receipts"]
            .as_array()
            .expect("stage receipts");

        assert_eq!(receipt["runtime_accepted"], true);
        assert_eq!(receipt["applied"], true);
        assert_eq!(stages[0]["stage"], "runtime_accepted");
        assert_eq!(stages[1]["stage"], "applied");
    }

    #[test]
    fn unsupported_receipt_keeps_rejection_explicit() {
        let request = BridgeCommandRequest {
            request_id: "request.bad".to_string(),
            command: "hostess.makepad.unsupported".to_string(),
            probe_token: "probe-b".to_string(),
            source: "unit-test".to_string(),
            command_transport: "android-app-private-json".to_string(),
        };

        let receipt = build_receipt_json(
            "unit",
            &request,
            "rejected",
            false,
            false,
            Some("hostess.issue.bridge_command_unsupported"),
            Some("unsupported"),
            None,
        );

        assert_eq!(receipt["status"], "rejected");
        assert_eq!(receipt["runtime_accepted"], false);
        assert_eq!(receipt["applied"], false);
        assert_eq!(receipt["stage_receipts"][0]["stage"], "rejected");
    }

    #[test]
    fn request_identity_is_stable_for_missing_file() {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let path = PathBuf::from(format!("missing-bridge-command-{unique}.json"));

        assert!(request_identity(&path).contains("missing-bridge-command-"));
    }
}
