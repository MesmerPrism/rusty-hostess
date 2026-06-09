use makepad_widgets::makepad_platform::makepad_micro_serde::*;
use std::collections::HashMap;
use std::path::{Path, PathBuf};

const LAUNCH_HANDOFF_SCHEMA: &str = "rusty.hostess.makepad_shell_launch_handoff_receipt.v1";
const CONTRACT_RECEIPT_SCHEMA: &str = "rusty.hostess.makepad_shell_contract_receipt.v1";
pub(crate) const CONTRACT_READ_RECEIPT_SCHEMA: &str =
    "rusty.hostess.makepad_shell_contract_read_receipt.v1";

#[cfg(target_os = "android")]
const ANDROID_INTERNAL_SHELL_ROOT: &str =
    "/data/user/0/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/shell";
#[cfg(target_os = "android")]
const ANDROID_EXTERNAL_SHELL_ROOT: &str =
    "/sdcard/Android/data/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/shell";

type JsonObject = HashMap<String, JsonValue>;

#[derive(Clone, Debug, Default)]
pub(crate) struct MakepadShellContractReadReceipt {
    pub(crate) status: String,
    pub(crate) issue_code: Option<String>,
    source_makepad_shell_launch_handoff_receipt_path: Option<String>,
    source_makepad_shell_launch_handoff_receipt_schema: Option<String>,
    source_makepad_shell_launch_handoff_receipt_status: Option<String>,
    source_makepad_shell_contract_receipt_path: Option<String>,
    source_makepad_shell_contract_receipt_schema: Option<String>,
    source_makepad_shell_contract_receipt_status: Option<String>,
    makepad_contract_reader_required: bool,
    makepad_contract_reader_ready: bool,
    makepad_contract_read_started: bool,
    makepad_contract_read_performed: bool,
    makepad_contract_read_receipt_written: bool,
    selected_handoff_id: Option<String>,
    selected_shell_app_id: Option<String>,
    expected_reader_contract_schema: Option<String>,
    descriptor_fallback_used: bool,
    legacy_reference_dependency_used: bool,
    launch_started_by_reader: bool,
    platform_execution_performed: bool,
    runtime_execution_performed: bool,
    checks: Vec<ContractReadCheck>,
}

#[derive(Clone, Debug)]
struct ContractReadCheck {
    check_id: String,
    status: String,
    evidence: String,
    issue_code: Option<String>,
}

impl MakepadShellContractReadReceipt {
    pub(crate) fn status(&self) -> &str {
        &self.status
    }

    pub(crate) fn issue_code(&self) -> Option<&str> {
        self.issue_code.as_deref()
    }

    pub(crate) fn selected_handoff_id(&self) -> Option<&str> {
        self.selected_handoff_id.as_deref()
    }

    pub(crate) fn selected_shell_app_id(&self) -> Option<&str> {
        self.selected_shell_app_id.as_deref()
    }

    pub(crate) fn descriptor_fallback_used(&self) -> bool {
        self.descriptor_fallback_used
    }

    pub(crate) fn legacy_reference_dependency_used(&self) -> bool {
        self.legacy_reference_dependency_used
    }

    #[cfg(test)]
    pub(crate) fn test_read_receipt() -> Self {
        Self {
            status: "read".to_string(),
            makepad_contract_read_started: true,
            makepad_contract_read_performed: true,
            selected_handoff_id: Some("handoff.test".to_string()),
            selected_shell_app_id: Some("app.hostess_t_makepad".to_string()),
            ..Default::default()
        }
    }

    #[allow(dead_code)]
    pub(crate) fn status_line(&self) -> String {
        if self.status == "read" {
            let handoff = self
                .selected_handoff_id
                .as_deref()
                .unwrap_or("unknown_handoff");
            let app = self
                .selected_shell_app_id
                .as_deref()
                .unwrap_or("unknown_shell_app");
            return format!("read {handoff} / {app}");
        }
        let issue = self.issue_code.as_deref().unwrap_or("not_configured");
        format!("{} / {issue}", self.status)
    }
}

pub(crate) fn read_selected_makepad_shell_contract() -> MakepadShellContractReadReceipt {
    let Some(path) = selected_launch_handoff_path() else {
        return rejected_receipt(
            None,
            "hostess.issue.makepad_shell_contract_read_handoff_not_found",
            "No Makepad shell launch handoff path was configured",
        );
    };
    read_makepad_shell_contract_from_launch_handoff_path(&path)
}

pub(crate) fn write_selected_makepad_shell_contract_read_receipt(
    receipt: &MakepadShellContractReadReceipt,
) -> Result<Option<PathBuf>, String> {
    let Some(path) = selected_contract_read_receipt_output_path() else {
        return Ok(None);
    };
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|error| format!("create {}: {error}", parent.display()))?;
    }
    let mut writable = receipt.clone();
    writable.makepad_contract_read_receipt_written = true;
    std::fs::write(&path, writable.to_json())
        .map_err(|error| format!("write {}: {error}", path.display()))?;
    Ok(Some(path))
}

pub(crate) fn read_makepad_shell_contract_from_launch_handoff_path(
    path: &Path,
) -> MakepadShellContractReadReceipt {
    let launch = match read_json_object(path) {
        Ok(launch) => launch,
        Err(error) => {
            return rejected_receipt(
                Some(path),
                "hostess.issue.makepad_shell_contract_read_handoff_parse",
                &error,
            )
        }
    };

    let contract_path = string_field(&launch, "makepad_contract_reader_input_path")
        .or_else(|| string_field(&launch, "source_makepad_shell_contract_receipt_path"));
    let contract = contract_path
        .as_ref()
        .and_then(|path_text| read_json_object(Path::new(path_text)).ok());
    build_receipt(path, &launch, contract_path, contract.as_ref())
}

fn build_receipt(
    launch_path: &Path,
    launch: &JsonObject,
    contract_path: Option<String>,
    contract: Option<&JsonObject>,
) -> MakepadShellContractReadReceipt {
    let launch_schema = string_field(launch, "$schema");
    let launch_status = string_field(launch, "status");
    let contract_schema = contract.and_then(|payload| string_field(payload, "$schema"));
    let contract_status = contract.and_then(|payload| string_field(payload, "status"));
    let descriptor_fallback_used = bool_field(launch, "descriptor_fallback_used").unwrap_or(false)
        || contract
            .and_then(|payload| bool_field(payload, "descriptor_fallback_used"))
            .unwrap_or(false);
    let legacy_reference_dependency_used = bool_field(launch, "legacy_reference_dependency_used")
        .unwrap_or(false)
        || contract
            .and_then(|payload| bool_field(payload, "legacy_reference_dependency_used"))
            .unwrap_or(false);
    let selected_handoff_id = string_field(launch, "selected_handoff_id");
    let selected_shell_app_id = string_field(launch, "selected_shell_app_id");
    let expected_reader_contract_schema = string_field(launch, "expected_reader_contract_schema");
    let mut checks = Vec::new();

    add_check(
        &mut checks,
        "hostess.check.makepad_shell_contract_read.launch_schema",
        launch_schema.as_deref() == Some(LAUNCH_HANDOFF_SCHEMA),
        "Makepad shell launch handoff schema is supported",
        "Makepad shell launch handoff schema is unsupported",
        "hostess.issue.makepad_shell_contract_read_launch_schema",
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_contract_read.launch_ready",
        launch_status.as_deref() == Some("ready")
            && bool_field(launch, "makepad_contract_reader_ready") == Some(true)
            && bool_field(launch, "makepad_launch_handoff_ready") == Some(true),
        "Makepad shell launch handoff is ready for contract reader intake",
        "Makepad shell launch handoff is not ready for contract reader intake",
        "hostess.issue.makepad_shell_contract_read_launch_not_ready",
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_contract_read.expected_schema",
        expected_reader_contract_schema.as_deref() == Some(CONTRACT_RECEIPT_SCHEMA),
        "Makepad shell launch handoff points at the expected contract schema",
        "Makepad shell launch handoff expected contract schema drifted",
        "hostess.issue.makepad_shell_contract_read_expected_schema",
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_contract_read.clean_route",
        !descriptor_fallback_used && !legacy_reference_dependency_used,
        "Makepad shell contract reader is using the clean Hostess/Manifold route",
        "Makepad shell contract reader input used descriptor fallback or legacy reference",
        "hostess.issue.makepad_shell_contract_read_legacy_or_fallback",
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_contract_read.contract_path",
        contract_path
            .as_deref()
            .is_some_and(|path_text| Path::new(path_text).is_file()),
        "Makepad shell contract receipt path exists",
        "Makepad shell contract receipt path is missing",
        "hostess.issue.makepad_shell_contract_read_contract_path",
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_contract_read.contract_schema",
        contract_schema.as_deref() == Some(CONTRACT_RECEIPT_SCHEMA),
        "Makepad shell contract receipt schema is supported",
        "Makepad shell contract receipt schema is unsupported",
        "hostess.issue.makepad_shell_contract_read_contract_schema",
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_contract_read.contract_accepted",
        contract_status.as_deref() == Some("accepted")
            && contract.and_then(|payload| bool_field(payload, "makepad_shell_contract_ready"))
                == Some(true),
        "Makepad shell contract receipt is accepted and ready",
        "Makepad shell contract receipt is not accepted and ready",
        "hostess.issue.makepad_shell_contract_read_contract_not_ready",
    );
    add_check(
        &mut checks,
        "hostess.check.makepad_shell_contract_read.linkage",
        contract.is_some()
            && selected_handoff_id
                == contract.and_then(|payload| string_field(payload, "selected_handoff_id"))
            && selected_shell_app_id
                == contract.and_then(|payload| string_field(payload, "selected_shell_app_id")),
        "Makepad shell contract receipt is linked to the launch handoff",
        "Makepad shell contract receipt does not match the launch handoff",
        "hostess.issue.makepad_shell_contract_read_linkage",
    );

    let failed = checks
        .iter()
        .find(|check| check.status == "fail")
        .map(|check| check.issue_code.clone())
        .unwrap_or(None);
    let read = failed.is_none();
    MakepadShellContractReadReceipt {
        status: if read {
            "read".to_string()
        } else {
            "rejected".to_string()
        },
        issue_code: failed,
        source_makepad_shell_launch_handoff_receipt_path: Some(launch_path.display().to_string()),
        source_makepad_shell_launch_handoff_receipt_schema: launch_schema,
        source_makepad_shell_launch_handoff_receipt_status: launch_status,
        source_makepad_shell_contract_receipt_path: contract_path,
        source_makepad_shell_contract_receipt_schema: contract_schema,
        source_makepad_shell_contract_receipt_status: contract_status,
        makepad_contract_reader_required: bool_field(launch, "makepad_contract_reader_required")
            .unwrap_or(false),
        makepad_contract_reader_ready: bool_field(launch, "makepad_contract_reader_ready")
            .unwrap_or(false),
        makepad_contract_read_started: true,
        makepad_contract_read_performed: read,
        makepad_contract_read_receipt_written: false,
        selected_handoff_id,
        selected_shell_app_id,
        expected_reader_contract_schema,
        descriptor_fallback_used,
        legacy_reference_dependency_used,
        launch_started_by_reader: false,
        platform_execution_performed: false,
        runtime_execution_performed: false,
        checks,
    }
}

fn rejected_receipt(
    launch_path: Option<&Path>,
    issue_code: &str,
    evidence: &str,
) -> MakepadShellContractReadReceipt {
    MakepadShellContractReadReceipt {
        status: "rejected".to_string(),
        issue_code: Some(issue_code.to_string()),
        source_makepad_shell_launch_handoff_receipt_path: launch_path
            .map(|path| path.display().to_string()),
        makepad_contract_read_started: launch_path.is_some(),
        checks: vec![ContractReadCheck {
            check_id: "hostess.check.makepad_shell_contract_read.input".to_string(),
            status: "fail".to_string(),
            evidence: evidence.to_string(),
            issue_code: Some(issue_code.to_string()),
        }],
        ..Default::default()
    }
}

fn selected_launch_handoff_path() -> Option<PathBuf> {
    if let Some(path) = arg_value("--makepad-shell-launch-handoff") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF") {
        return Some(PathBuf::from(path));
    }
    default_launch_handoff_candidates()
        .into_iter()
        .find(|path| path.is_file())
}

fn selected_contract_read_receipt_output_path() -> Option<PathBuf> {
    if let Some(path) = arg_value("--makepad-shell-contract-read-receipt-out") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("HOSTESS_MAKEPAD_SHELL_CONTRACT_READ_RECEIPT_OUT") {
        return Some(PathBuf::from(path));
    }
    default_contract_read_receipt_output_path()
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
fn default_launch_handoff_candidates() -> Vec<PathBuf> {
    vec![
        PathBuf::from(format!(
            "{ANDROID_INTERNAL_SHELL_ROOT}/makepad-shell-launch-handoff.json"
        )),
        PathBuf::from(format!(
            "{ANDROID_EXTERNAL_SHELL_ROOT}/makepad-shell-launch-handoff.json"
        )),
    ]
}

#[cfg(not(target_os = "android"))]
fn default_launch_handoff_candidates() -> Vec<PathBuf> {
    Vec::new()
}

#[cfg(target_os = "android")]
fn default_contract_read_receipt_output_path() -> Option<PathBuf> {
    Some(PathBuf::from(format!(
        "{ANDROID_INTERNAL_SHELL_ROOT}/makepad-shell-contract-read-receipt.json"
    )))
}

#[cfg(not(target_os = "android"))]
fn default_contract_read_receipt_output_path() -> Option<PathBuf> {
    None
}

fn read_json_object(path: &Path) -> Result<JsonObject, String> {
    let text = std::fs::read_to_string(path).map_err(|error| {
        format!(
            "could not read Makepad shell contract JSON {}: {error}",
            path.display()
        )
    })?;
    let value = JsonValue::deserialize_json_lenient(&text).map_err(|error| {
        format!(
            "could not parse Makepad shell contract JSON {}: {error:?}",
            path.display()
        )
    })?;
    match value {
        JsonValue::Object(object) => Ok(object),
        _ => Err(format!(
            "Makepad shell contract JSON {} is not an object",
            path.display()
        )),
    }
}

fn string_field(map: &JsonObject, key: &str) -> Option<String> {
    map.get(key).and_then(|value| match value {
        JsonValue::String(text) | JsonValue::BareIdent(text) => Some(text.clone()),
        _ => None,
    })
}

fn bool_field(map: &JsonObject, key: &str) -> Option<bool> {
    map.get(key).and_then(|value| match value {
        JsonValue::Bool(value) => Some(*value),
        _ => None,
    })
}

fn add_check(
    checks: &mut Vec<ContractReadCheck>,
    check_id: &str,
    condition: bool,
    pass_evidence: &str,
    fail_evidence: &str,
    issue_code: &str,
) {
    checks.push(ContractReadCheck {
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

impl MakepadShellContractReadReceipt {
    fn to_json(&self) -> String {
        let checks = self
            .checks
            .iter()
            .map(ContractReadCheck::to_json)
            .collect::<Vec<_>>()
            .join(",");
        format!(
            concat!(
                "{{",
                "\"$schema\":{},",
                "\"status\":{},",
                "\"issue_code\":{},",
                "\"source_makepad_shell_launch_handoff_receipt_path\":{},",
                "\"source_makepad_shell_launch_handoff_receipt_schema\":{},",
                "\"source_makepad_shell_launch_handoff_receipt_status\":{},",
                "\"source_makepad_shell_contract_receipt_path\":{},",
                "\"source_makepad_shell_contract_receipt_schema\":{},",
                "\"source_makepad_shell_contract_receipt_status\":{},",
                "\"makepad_contract_reader_required\":{},",
                "\"makepad_contract_reader_ready\":{},",
                "\"makepad_contract_read_started\":{},",
                "\"makepad_contract_read_performed\":{},",
                "\"makepad_contract_read_receipt_written\":{},",
                "\"selected_handoff_id\":{},",
                "\"selected_shell_app_id\":{},",
                "\"expected_reader_contract_schema\":{},",
                "\"descriptor_fallback_used\":{},",
                "\"legacy_reference_dependency_used\":{},",
                "\"launch_started_by_reader\":{},",
                "\"platform_execution_performed\":{},",
                "\"runtime_execution_performed\":{},",
                "\"checks\":[{}]",
                "}}\n"
            ),
            json_string(CONTRACT_READ_RECEIPT_SCHEMA),
            json_string(&self.status),
            json_option_string(self.issue_code.as_deref()),
            json_option_string(
                self.source_makepad_shell_launch_handoff_receipt_path
                    .as_deref()
            ),
            json_option_string(
                self.source_makepad_shell_launch_handoff_receipt_schema
                    .as_deref()
            ),
            json_option_string(
                self.source_makepad_shell_launch_handoff_receipt_status
                    .as_deref()
            ),
            json_option_string(self.source_makepad_shell_contract_receipt_path.as_deref()),
            json_option_string(self.source_makepad_shell_contract_receipt_schema.as_deref()),
            json_option_string(self.source_makepad_shell_contract_receipt_status.as_deref()),
            json_bool(self.makepad_contract_reader_required),
            json_bool(self.makepad_contract_reader_ready),
            json_bool(self.makepad_contract_read_started),
            json_bool(self.makepad_contract_read_performed),
            json_bool(self.makepad_contract_read_receipt_written),
            json_option_string(self.selected_handoff_id.as_deref()),
            json_option_string(self.selected_shell_app_id.as_deref()),
            json_option_string(self.expected_reader_contract_schema.as_deref()),
            json_bool(self.descriptor_fallback_used),
            json_bool(self.legacy_reference_dependency_used),
            json_bool(self.launch_started_by_reader),
            json_bool(self.platform_execution_performed),
            json_bool(self.runtime_execution_performed),
            checks
        )
    }
}

impl ContractReadCheck {
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
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn reads_ready_launch_handoff_and_contract() {
        let root = temp_root("reads_ready_launch_handoff_and_contract");
        let contract_path = root.join("contract.json");
        let launch_path = root.join("launch.json");
        write_json(
            &contract_path,
            &format!(
                concat!(
                    "{{",
                    "\"$schema\":\"{}\",",
                    "\"receipt_id\":\"contract.1\",",
                    "\"status\":\"accepted\",",
                    "\"issue_code\":null,",
                    "\"makepad_shell_contract_ready\":true,",
                    "\"descriptor_fallback_used\":false,",
                    "\"legacy_reference_dependency_used\":false,",
                    "\"selected_handoff_id\":\"handoff.1\",",
                    "\"selected_shell_app_id\":\"app.makepad\"",
                    "}}"
                ),
                CONTRACT_RECEIPT_SCHEMA
            ),
        );
        write_json(
            &launch_path,
            &format!(
                concat!(
                    "{{",
                    "\"$schema\":\"{}\",",
                    "\"status\":\"ready\",",
                    "\"makepad_contract_reader_required\":true,",
                    "\"makepad_contract_reader_ready\":true,",
                    "\"makepad_contract_reader_input_path\":\"{}\",",
                    "\"makepad_launch_handoff_ready\":true,",
                    "\"expected_reader_contract_schema\":\"{}\",",
                    "\"descriptor_fallback_used\":false,",
                    "\"legacy_reference_dependency_used\":false,",
                    "\"selected_handoff_id\":\"handoff.1\",",
                    "\"selected_shell_app_id\":\"app.makepad\"",
                    "}}"
                ),
                LAUNCH_HANDOFF_SCHEMA,
                slash_path(&contract_path),
                CONTRACT_RECEIPT_SCHEMA
            ),
        );

        let receipt = read_makepad_shell_contract_from_launch_handoff_path(&launch_path);

        assert_eq!(receipt.status, "read");
        assert_eq!(receipt.issue_code, None);
        assert!(receipt.makepad_contract_read_performed);
        assert!(!receipt.descriptor_fallback_used);
        assert!(!receipt.legacy_reference_dependency_used);
    }

    #[test]
    fn rejects_descriptor_fallback_or_missing_contract() {
        let root = temp_root("rejects_descriptor_fallback_or_missing_contract");
        let launch_path = root.join("launch.json");
        let missing_contract = root.join("missing-contract.json");
        write_json(
            &launch_path,
            &format!(
                concat!(
                    "{{",
                    "\"$schema\":\"{}\",",
                    "\"status\":\"ready\",",
                    "\"makepad_contract_reader_required\":true,",
                    "\"makepad_contract_reader_ready\":true,",
                    "\"makepad_contract_reader_input_path\":\"{}\",",
                    "\"makepad_launch_handoff_ready\":true,",
                    "\"expected_reader_contract_schema\":\"{}\",",
                    "\"descriptor_fallback_used\":true,",
                    "\"legacy_reference_dependency_used\":false,",
                    "\"selected_handoff_id\":\"handoff.1\",",
                    "\"selected_shell_app_id\":\"app.makepad\"",
                    "}}"
                ),
                LAUNCH_HANDOFF_SCHEMA,
                slash_path(&missing_contract),
                CONTRACT_RECEIPT_SCHEMA
            ),
        );

        let receipt = read_makepad_shell_contract_from_launch_handoff_path(&launch_path);

        assert_eq!(receipt.status, "rejected");
        assert_eq!(
            receipt.issue_code.as_deref(),
            Some("hostess.issue.makepad_shell_contract_read_legacy_or_fallback")
        );
        assert!(!receipt.makepad_contract_read_performed);
    }

    fn temp_root(name: &str) -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock before Unix epoch")
            .as_nanos();
        let root = std::env::temp_dir().join(format!("{name}-{stamp}"));
        std::fs::create_dir_all(&root).expect("create temp root");
        root
    }

    fn write_json(path: &Path, text: &str) {
        std::fs::write(path, text).expect("write JSON fixture");
    }

    fn slash_path(path: &Path) -> String {
        path.display().to_string().replace('\\', "\\\\")
    }
}
