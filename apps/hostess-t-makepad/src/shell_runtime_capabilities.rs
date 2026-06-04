use crate::shell_contract::MakepadShellContractReadReceipt;
use crate::shell_xr_runtime::ShellXrRuntimeState;
use std::path::PathBuf;

pub(crate) const RUNTIME_CAPABILITY_RECEIPT_SCHEMA: &str =
    "rusty.hostess.makepad_shell_runtime_capability_receipt.v1";

#[cfg(target_os = "android")]
const ANDROID_INTERNAL_SHELL_ROOT: &str =
    "/data/user/0/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/shell";

const TARGET_SHELL_KIND: &str = "clean_makepad_xr_shell";
const RUNTIME_MISSING_ISSUE: &str =
    "hostess.issue.makepad_shell_runtime_capability_xr_controller_hwb_missing";
const CONTRACT_UNREAD_ISSUE: &str =
    "hostess.issue.makepad_shell_runtime_capability_contract_unread";
const LEGACY_OR_FALLBACK_ISSUE: &str =
    "hostess.issue.makepad_shell_runtime_capability_legacy_or_fallback";

const REQUIRED_CAPABILITIES: &[&str] = &[
    "xr_session",
    "xr_controller_pose_provider",
    "controller_pose_manifold_publisher",
    "manifold_broker_transport",
    "breath_feedback_subscriber",
    "breath_feedback_receipt_publisher",
    "camera_hardware_buffer_import",
    "custom_camera_projection_from_hwb",
];

const STATIC_IMPLEMENTED_CAPABILITIES: &[&str] = &[
    "shell_contract_reader",
    "app_private_contract_receipt_writer",
    "host_telemetry_snapshot_viewer",
    "render_export_writer",
    "makepad_xr_root",
];

#[derive(Clone, Debug, Default)]
pub(crate) struct MakepadShellRuntimeCapabilityReceipt {
    status: String,
    issue_code: Option<String>,
    target_shell_kind: String,
    shell_contract_read_status: String,
    shell_contract_issue_code: Option<String>,
    selected_handoff_id: Option<String>,
    selected_shell_app_id: Option<String>,
    final_clean_makepad_app_requires_xr: bool,
    xr_session_required: bool,
    controller_pose_required: bool,
    camera_hardware_buffer_projection_required: bool,
    custom_camera_projection_required: bool,
    breath_feedback_required: bool,
    broker_transport_required: bool,
    descriptor_fallback_used: bool,
    makepad_xr_dependency_used: bool,
    makepad_xr_root_registered: bool,
    xr_update_observed: bool,
    xr_update_count: u64,
    in_xr_mode_observed: bool,
    controller_pose_provider_observed: bool,
    left_controller_active: bool,
    right_controller_active: bool,
    last_xr_time_s: Option<f64>,
    legacy_rusty_xr_dependency_used: bool,
    legacy_rusty_xr_reference_only: bool,
    runtime_capability_receipt_written: bool,
    required_capabilities: Vec<String>,
    implemented_capabilities: Vec<String>,
    missing_capabilities: Vec<String>,
    next_required_action: String,
    checks: Vec<RuntimeCapabilityCheck>,
}

#[derive(Clone, Debug)]
struct RuntimeCapabilityCheck {
    check_id: String,
    status: String,
    evidence: String,
    issue_code: Option<String>,
}

impl MakepadShellRuntimeCapabilityReceipt {
    pub(crate) fn status_line(&self) -> String {
        if self.status == "incomplete" {
            let first = self
                .missing_capabilities
                .first()
                .map(String::as_str)
                .unwrap_or("unknown_capability");
            return format!(
                "runtime incomplete / missing {} +{}",
                first,
                self.missing_capabilities.len().saturating_sub(1)
            );
        }
        if self.status.is_empty() {
            return "runtime not evaluated".to_string();
        }
        let issue = self.issue_code.as_deref().unwrap_or("ok");
        format!("runtime {} / {issue}", self.status)
    }

    fn to_json(&self) -> String {
        let checks = self
            .checks
            .iter()
            .map(RuntimeCapabilityCheck::to_json)
            .collect::<Vec<_>>()
            .join(",");
        format!(
            concat!(
                "{{",
                "\"$schema\":{},",
                "\"status\":{},",
                "\"issue_code\":{},",
                "\"target_shell_kind\":{},",
                "\"shell_contract_read_status\":{},",
                "\"shell_contract_issue_code\":{},",
                "\"selected_handoff_id\":{},",
                "\"selected_shell_app_id\":{},",
                "\"final_clean_makepad_app_requires_xr\":{},",
                "\"xr_session_required\":{},",
                "\"controller_pose_required\":{},",
                "\"camera_hardware_buffer_projection_required\":{},",
                "\"custom_camera_projection_required\":{},",
                "\"breath_feedback_required\":{},",
                "\"broker_transport_required\":{},",
                "\"descriptor_fallback_used\":{},",
                "\"makepad_xr_dependency_used\":{},",
                "\"makepad_xr_root_registered\":{},",
                "\"xr_update_observed\":{},",
                "\"xr_update_count\":{},",
                "\"in_xr_mode_observed\":{},",
                "\"controller_pose_provider_observed\":{},",
                "\"left_controller_active\":{},",
                "\"right_controller_active\":{},",
                "\"last_xr_time_s\":{},",
                "\"legacy_rusty_xr_dependency_used\":{},",
                "\"legacy_rusty_xr_reference_only\":{},",
                "\"runtime_capability_receipt_written\":{},",
                "\"required_capabilities\":{},",
                "\"implemented_capabilities\":{},",
                "\"missing_capabilities\":{},",
                "\"next_required_action\":{},",
                "\"checks\":[{}]",
                "}}\n"
            ),
            json_string(RUNTIME_CAPABILITY_RECEIPT_SCHEMA),
            json_string(&self.status),
            json_option_string(self.issue_code.as_deref()),
            json_string(&self.target_shell_kind),
            json_string(&self.shell_contract_read_status),
            json_option_string(self.shell_contract_issue_code.as_deref()),
            json_option_string(self.selected_handoff_id.as_deref()),
            json_option_string(self.selected_shell_app_id.as_deref()),
            json_bool(self.final_clean_makepad_app_requires_xr),
            json_bool(self.xr_session_required),
            json_bool(self.controller_pose_required),
            json_bool(self.camera_hardware_buffer_projection_required),
            json_bool(self.custom_camera_projection_required),
            json_bool(self.breath_feedback_required),
            json_bool(self.broker_transport_required),
            json_bool(self.descriptor_fallback_used),
            json_bool(self.makepad_xr_dependency_used),
            json_bool(self.makepad_xr_root_registered),
            json_bool(self.xr_update_observed),
            self.xr_update_count,
            json_bool(self.in_xr_mode_observed),
            json_bool(self.controller_pose_provider_observed),
            json_bool(self.left_controller_active),
            json_bool(self.right_controller_active),
            json_option_f64(self.last_xr_time_s),
            json_bool(self.legacy_rusty_xr_dependency_used),
            json_bool(self.legacy_rusty_xr_reference_only),
            json_bool(self.runtime_capability_receipt_written),
            json_string_array(&self.required_capabilities),
            json_string_array(&self.implemented_capabilities),
            json_string_array(&self.missing_capabilities),
            json_string(&self.next_required_action),
            checks
        )
    }
}

pub(crate) fn evaluate(
    contract_read: &MakepadShellContractReadReceipt,
    xr_runtime: &ShellXrRuntimeState,
) -> MakepadShellRuntimeCapabilityReceipt {
    let required = REQUIRED_CAPABILITIES
        .iter()
        .map(|capability| (*capability).to_string())
        .collect::<Vec<_>>();
    let mut implemented = STATIC_IMPLEMENTED_CAPABILITIES
        .iter()
        .map(|capability| (*capability).to_string())
        .collect::<Vec<_>>();
    if xr_runtime.xr_update_observed() {
        implemented.push("xr_session".to_string());
    }
    if xr_runtime.controller_pose_provider_observed() {
        implemented.push("xr_controller_pose_provider".to_string());
    }
    let missing = required
        .iter()
        .filter(|capability| !implemented.iter().any(|value| value == *capability))
        .cloned()
        .collect::<Vec<_>>();
    let contract_read_ok = contract_read.status() == "read";
    let clean_route = !contract_read.descriptor_fallback_used()
        && !contract_read.legacy_rusty_xr_dependency_used();

    let (status, issue_code, next_required_action) = if !contract_read_ok {
        (
            "rejected",
            Some(CONTRACT_UNREAD_ISSUE),
            "repair_makepad_shell_contract_read_before_runtime_capability_gate",
        )
    } else if !clean_route {
        (
            "rejected",
            Some(LEGACY_OR_FALLBACK_ISSUE),
            "repair_makepad_shell_contract_clean_route_before_runtime_capability_gate",
        )
    } else if missing.is_empty() {
        (
            "ready",
            None,
            "run_polar_controller_pmb_makepad_closed_loop_device_test",
        )
    } else {
        (
            "incomplete",
            Some(RUNTIME_MISSING_ISSUE),
            "implement_clean_makepad_xr_controller_hwb_runtime",
        )
    };

    let mut checks = Vec::new();
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_runtime_capability.contract_read",
        contract_read_ok,
        "Makepad shell contract was read before runtime capability evaluation",
        "Makepad shell contract was not read before runtime capability evaluation",
        CONTRACT_UNREAD_ISSUE,
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_runtime_capability.clean_route",
        clean_route,
        "Runtime capability gate is using the clean Hostess/Manifold route",
        "Runtime capability gate saw descriptor fallback or legacy Rusty-XR dependency",
        LEGACY_OR_FALLBACK_ISSUE,
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_runtime_capability.xr_controller_hwb_required",
        true,
        "Final clean Makepad shell requires XR, controller pose, and custom HWB camera projection",
        "Final clean Makepad shell did not declare XR/controller/HWB projection requirements",
        "hostess.issue.makepad_shell_runtime_capability_missing_final_requirements",
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_runtime_capability.makepad_xr_root",
        xr_runtime.xr_root_registered(),
        "Clean Makepad app registered its XR root through the local Makepad XR fork",
        "Clean Makepad app did not register an XR root",
        "hostess.issue.makepad_shell_runtime_capability_xr_root_missing",
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_runtime_capability.xr_update_observed",
        xr_runtime.xr_update_observed(),
        "Clean Makepad app observed an XR update",
        "Clean Makepad app has not observed an XR update yet",
        RUNTIME_MISSING_ISSUE,
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_runtime_capability.controller_pose_observed",
        xr_runtime.controller_pose_provider_observed(),
        "Clean Makepad app observed an active controller pose provider",
        "Clean Makepad app has not observed an active controller pose provider yet",
        RUNTIME_MISSING_ISSUE,
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_runtime_capability.required_runtime_implemented",
        missing.is_empty(),
        "All required clean XR Makepad runtime capabilities are implemented",
        "Clean XR Makepad runtime capabilities are still missing",
        RUNTIME_MISSING_ISSUE,
    );

    MakepadShellRuntimeCapabilityReceipt {
        status: status.to_string(),
        issue_code: issue_code.map(str::to_string),
        target_shell_kind: TARGET_SHELL_KIND.to_string(),
        shell_contract_read_status: contract_read.status().to_string(),
        shell_contract_issue_code: contract_read.issue_code().map(str::to_string),
        selected_handoff_id: contract_read.selected_handoff_id().map(str::to_string),
        selected_shell_app_id: contract_read.selected_shell_app_id().map(str::to_string),
        final_clean_makepad_app_requires_xr: true,
        xr_session_required: true,
        controller_pose_required: true,
        camera_hardware_buffer_projection_required: true,
        custom_camera_projection_required: true,
        breath_feedback_required: true,
        broker_transport_required: true,
        descriptor_fallback_used: contract_read.descriptor_fallback_used(),
        makepad_xr_dependency_used: true,
        makepad_xr_root_registered: xr_runtime.xr_root_registered(),
        xr_update_observed: xr_runtime.xr_update_observed(),
        xr_update_count: xr_runtime.xr_update_count(),
        in_xr_mode_observed: xr_runtime.in_xr_mode_observed(),
        controller_pose_provider_observed: xr_runtime.controller_pose_provider_observed(),
        left_controller_active: xr_runtime.left_controller_active(),
        right_controller_active: xr_runtime.right_controller_active(),
        last_xr_time_s: xr_runtime.last_xr_time_s(),
        legacy_rusty_xr_dependency_used: contract_read.legacy_rusty_xr_dependency_used(),
        legacy_rusty_xr_reference_only: true,
        runtime_capability_receipt_written: false,
        required_capabilities: required,
        implemented_capabilities: implemented,
        missing_capabilities: missing,
        next_required_action: next_required_action.to_string(),
        checks,
    }
}

pub(crate) fn write_selected_makepad_shell_runtime_capability_receipt(
    receipt: &MakepadShellRuntimeCapabilityReceipt,
) -> Result<Option<PathBuf>, String> {
    let Some(path) = selected_runtime_capability_receipt_output_path() else {
        return Ok(None);
    };
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|error| format!("create {}: {error}", parent.display()))?;
    }
    let mut writable = receipt.clone();
    writable.runtime_capability_receipt_written = true;
    std::fs::write(&path, writable.to_json())
        .map_err(|error| format!("write {}: {error}", path.display()))?;
    Ok(Some(path))
}

fn selected_runtime_capability_receipt_output_path() -> Option<PathBuf> {
    if let Some(path) = arg_value("--makepad-shell-runtime-capability-receipt-out") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("HOSTESS_MAKEPAD_SHELL_RUNTIME_CAPABILITY_RECEIPT_OUT") {
        return Some(PathBuf::from(path));
    }
    default_runtime_capability_receipt_output_path()
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
fn default_runtime_capability_receipt_output_path() -> Option<PathBuf> {
    Some(PathBuf::from(format!(
        "{ANDROID_INTERNAL_SHELL_ROOT}/makepad-shell-runtime-capability-receipt.json"
    )))
}

#[cfg(not(target_os = "android"))]
fn default_runtime_capability_receipt_output_path() -> Option<PathBuf> {
    None
}

fn add_check(
    checks: &mut Vec<RuntimeCapabilityCheck>,
    check_id: &str,
    condition: bool,
    pass_evidence: &str,
    fail_evidence: &str,
    issue_code: &str,
) {
    checks.push(RuntimeCapabilityCheck {
        check_id: check_id.to_string(),
        status: if condition {
            "pass".to_string()
        } else {
            "fail".to_string()
        },
        evidence: if condition {
            pass_evidence.to_string()
        } else {
            fail_evidence.to_string()
        },
        issue_code: if condition {
            None
        } else {
            Some(issue_code.to_string())
        },
    });
}

impl RuntimeCapabilityCheck {
    fn to_json(&self) -> String {
        format!(
            concat!(
                "{{",
                "\"check_id\":{},",
                "\"status\":{},",
                "\"evidence\":{},",
                "\"issue_code\":{}",
                "}}"
            ),
            json_string(&self.check_id),
            json_string(&self.status),
            json_string(&self.evidence),
            json_option_string(self.issue_code.as_deref())
        )
    }
}

fn json_string_array(values: &[String]) -> String {
    let joined = values
        .iter()
        .map(|value| json_string(value))
        .collect::<Vec<_>>()
        .join(",");
    format!("[{joined}]")
}

fn json_option_string(value: Option<&str>) -> String {
    value.map(json_string).unwrap_or_else(|| "null".to_string())
}

fn json_bool(value: bool) -> &'static str {
    if value {
        "true"
    } else {
        "false"
    }
}

fn json_option_f64(value: Option<f64>) -> String {
    match value {
        Some(value) if value.is_finite() => format!("{value:.6}"),
        _ => "null".to_string(),
    }
}

fn json_string(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            ch if ch.is_control() => {
                out.push_str(&format!("\\u{:04x}", ch as u32));
            }
            ch => out.push(ch),
        }
    }
    out.push('"');
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use makepad_widgets::makepad_platform::makepad_micro_serde::*;

    #[test]
    fn marks_xr_controller_and_hwb_projection_as_required() {
        let contract_read = MakepadShellContractReadReceipt::test_read_receipt();

        let receipt = evaluate(&contract_read, &ShellXrRuntimeState::registered_xr_shell());

        assert_eq!(receipt.status, "incomplete");
        assert_eq!(receipt.issue_code.as_deref(), Some(RUNTIME_MISSING_ISSUE));
        assert!(receipt.final_clean_makepad_app_requires_xr);
        assert!(receipt.xr_session_required);
        assert!(receipt.controller_pose_required);
        assert!(receipt.camera_hardware_buffer_projection_required);
        assert!(receipt.custom_camera_projection_required);
        assert!(receipt.breath_feedback_required);
        assert!(receipt.broker_transport_required);
        assert!(receipt.makepad_xr_dependency_used);
        assert!(receipt.makepad_xr_root_registered);
        assert!(!receipt.xr_update_observed);
        assert!(!receipt.controller_pose_provider_observed);
        assert!(receipt.legacy_rusty_xr_reference_only);
        assert!(receipt
            .missing_capabilities
            .iter()
            .any(|capability| capability == "xr_session"));
        assert!(receipt
            .missing_capabilities
            .iter()
            .any(|capability| capability == "xr_controller_pose_provider"));
        assert!(receipt
            .missing_capabilities
            .iter()
            .any(|capability| capability == "custom_camera_projection_from_hwb"));
    }

    #[test]
    fn rejects_capability_gate_when_contract_was_not_read() {
        let receipt = evaluate(
            &MakepadShellContractReadReceipt::default(),
            &ShellXrRuntimeState::registered_xr_shell(),
        );

        assert_eq!(receipt.status, "rejected");
        assert_eq!(receipt.issue_code.as_deref(), Some(CONTRACT_UNREAD_ISSUE));
        assert!(receipt
            .missing_capabilities
            .iter()
            .any(|capability| capability == "camera_hardware_buffer_import"));
    }

    #[test]
    fn serializes_runtime_capability_receipt() {
        let contract_read = MakepadShellContractReadReceipt::test_read_receipt();
        let receipt = evaluate(
            &contract_read,
            &ShellXrRuntimeState::test_observed_xr_controller(),
        );
        let json = receipt.to_json();
        let parsed = JsonValue::deserialize_json_lenient(&json).expect("valid JSON");

        let JsonValue::Object(object) = parsed else {
            panic!("receipt JSON must be an object");
        };
        assert!(matches!(
            object.get("$schema"),
            Some(JsonValue::String(value)) if value == RUNTIME_CAPABILITY_RECEIPT_SCHEMA
        ));
        assert!(matches!(
            object.get("status"),
            Some(JsonValue::String(value)) if value == "incomplete"
        ));
        assert!(matches!(
            object.get("target_shell_kind"),
            Some(JsonValue::String(value)) if value == TARGET_SHELL_KIND
        ));
        assert!(matches!(
            object.get("xr_update_observed"),
            Some(JsonValue::Bool(true))
        ));
        assert!(matches!(
            object.get("controller_pose_provider_observed"),
            Some(JsonValue::Bool(true))
        ));
        assert!(matches!(
            object.get("missing_capabilities"),
            Some(JsonValue::Array(values))
                if !values.iter().any(|value| matches!(value, JsonValue::String(text) if text == "xr_session"))
        ));
    }
}
