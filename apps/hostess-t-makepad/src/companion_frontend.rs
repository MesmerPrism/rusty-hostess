//! Makepad-facing projection over shared companion reports.
//!
//! This module is deliberately source/fixture only. It parses the same Hostess
//! catalog, Quest device-link, and protocol-matrix reports that WPF renders,
//! then reduces them to compact rows a Makepad panel can display later without
//! owning validation.

use serde_json::Value;

pub(crate) const MAKEPAD_COMPANION_FRONTEND_MARKER: &str =
    "RUSTY_HOSTESS_MAKEPAD_COMPANION_FRONTEND";
pub(crate) const MAKEPAD_COMPANION_FRONTEND_SCHEMA: &str =
    "rusty.hostess.makepad.companion_frontend_projection.v1";
const HOSTESS_COMPANION_CATALOG_SCHEMA: &str = "rusty.hostess.companion.catalog.v1";
const QUEST_DEVICE_LINK_SCHEMA: &str = "rusty.quest.device_link.v1";
const PROTOCOL_EVIDENCE_MATRIX_SCHEMA: &str = "rusty.quest.device_link.protocol_evidence_matrix.v1";

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct MakepadCompanionRow {
    pub(crate) row_id: String,
    pub(crate) row_family: String,
    pub(crate) status: String,
    pub(crate) title: String,
    pub(crate) detail: String,
    pub(crate) source_schema: String,
    pub(crate) source_report: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct MakepadCompanionProjection {
    pub(crate) status: String,
    pub(crate) rows: Vec<MakepadCompanionRow>,
    pub(crate) catalog_rows: usize,
    pub(crate) device_link_rows: usize,
    pub(crate) protocol_matrix_rows: usize,
}

pub(crate) fn project_companion_catalog(text: &str) -> Result<Vec<MakepadCompanionRow>, String> {
    let value = parse_report(text, HOSTESS_COMPANION_CATALOG_SCHEMA)?;
    let mut rows = Vec::new();
    let catalog_status = string_field(&value, "status", "unknown");
    rows.push(MakepadCompanionRow {
        row_id: "catalog.summary".to_string(),
        row_family: "catalog_summary".to_string(),
        status: catalog_status,
        title: "Companion catalog".to_string(),
        detail: summary_detail(&value),
        source_schema: HOSTESS_COMPANION_CATALOG_SCHEMA.to_string(),
        source_report: "catalog".to_string(),
    });

    let issues = value
        .get("issues")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    for module in array_field(&value, "modules") {
        let module_id = string_field(module, "module_id", "unknown_module");
        rows.push(MakepadCompanionRow {
            row_id: module_id.clone(),
            row_family: "catalog_module".to_string(),
            status: issue_status(&issues, "module_id", &module_id),
            title: string_field(module, "title", &module_id),
            detail: format!(
                "family={} owner={} reports={} commands={} evidence={}",
                string_field(module, "family", "unknown"),
                string_field(module, "owner_lane", "unknown"),
                count_array(module, "readable_reports"),
                count_array(module, "command_requests"),
                count_array(module, "evidence_artifacts")
            ),
            source_schema: HOSTESS_COMPANION_CATALOG_SCHEMA.to_string(),
            source_report: "catalog".to_string(),
        });
    }
    for workspace in array_field(&value, "workspaces") {
        let workspace_id = string_field(workspace, "workspace_id", "unknown_workspace");
        rows.push(MakepadCompanionRow {
            row_id: workspace_id.clone(),
            row_family: "catalog_workspace".to_string(),
            status: issue_status(&issues, "workspace_id", &workspace_id),
            title: string_field(workspace, "title", &workspace_id),
            detail: format!(
                "modules={} sensitivity={}",
                count_array(workspace, "modules"),
                joined_strings(workspace, "sensitivity")
            ),
            source_schema: HOSTESS_COMPANION_CATALOG_SCHEMA.to_string(),
            source_report: "catalog".to_string(),
        });
    }
    for transport in array_field(&value, "transports") {
        let transport_id = string_field(transport, "transport_id", "unknown_transport");
        rows.push(MakepadCompanionRow {
            row_id: transport_id.clone(),
            row_family: "catalog_transport".to_string(),
            status: issue_status(&issues, "transport_id", &transport_id),
            title: string_field(transport, "title", &transport_id),
            detail: format!(
                "family={} plane={} delivery={} stages={}",
                string_field(transport, "family", "unknown"),
                string_field(transport, "plane", "unknown"),
                string_field(transport, "delivery", "unknown"),
                joined_strings(transport, "required_evidence_stages")
            ),
            source_schema: HOSTESS_COMPANION_CATALOG_SCHEMA.to_string(),
            source_report: "catalog".to_string(),
        });
    }
    for issue in issues {
        rows.push(MakepadCompanionRow {
            row_id: string_field(&issue, "code", "catalog.issue"),
            row_family: "catalog_issue".to_string(),
            status: string_field(&issue, "severity", "warning"),
            title: string_field(&issue, "code", "Catalog issue"),
            detail: string_field(&issue, "message", "No issue detail"),
            source_schema: HOSTESS_COMPANION_CATALOG_SCHEMA.to_string(),
            source_report: "catalog".to_string(),
        });
    }
    Ok(rows)
}

pub(crate) fn project_device_link(text: &str) -> Result<Vec<MakepadCompanionRow>, String> {
    let value = parse_report(text, QUEST_DEVICE_LINK_SCHEMA)?;
    let mut rows = Vec::new();
    rows.push(MakepadCompanionRow {
        row_id: string_field(&value, "link_id", "device_link.summary"),
        row_family: "device_link_summary".to_string(),
        status: string_field(&value, "status", "unknown"),
        title: "Quest device link".to_string(),
        detail: format!(
            "tools={} tunnels={} brokerEndpoints={} runtimeSubscribers={} commandResults={} streamCapabilities={}",
            count_array(&value, "host_tools"),
            count_array(&value, "tunnels"),
            count_array(&value, "broker_endpoints"),
            count_array(&value, "runtime_subscribers"),
            count_array(&value, "command_results"),
            count_array(&value, "stream_capabilities")
        ),
        source_schema: QUEST_DEVICE_LINK_SCHEMA.to_string(),
        source_report: "device_link".to_string(),
    });
    if let Some(identity) = value.get("device_identity").filter(|row| row.is_object()) {
        rows.push(MakepadCompanionRow {
            row_id: format!("device.{}", string_field(identity, "serial", "unknown")),
            row_family: "device_identity".to_string(),
            status: adb_state_status(&string_field(identity, "adb_state", "unknown")),
            title: string_field(identity, "model", "Quest device"),
            detail: format!(
                "serial={} transport={}",
                string_field(identity, "serial", "unknown"),
                string_field(identity, "transport_kind", "unknown")
            ),
            source_schema: QUEST_DEVICE_LINK_SCHEMA.to_string(),
            source_report: "device_link".to_string(),
        });
    }
    for tunnel in array_field(&value, "tunnels") {
        rows.push(MakepadCompanionRow {
            row_id: string_field(tunnel, "tunnel_id", "tunnel.unknown"),
            row_family: "device_link_tunnel".to_string(),
            status: string_field(tunnel, "status", "unknown"),
            title: string_field(tunnel, "tunnel_id", "ADB tunnel"),
            detail: format!(
                "{}:{} -> {}:{}{}",
                string_field(tunnel, "host", "unknown"),
                numeric_field(tunnel, "local_port", "unknown"),
                string_field(tunnel, "device_host", "unknown"),
                numeric_field(tunnel, "device_port", "unknown"),
                path_suffix(tunnel)
            ),
            source_schema: QUEST_DEVICE_LINK_SCHEMA.to_string(),
            source_report: "device_link".to_string(),
        });
    }
    for endpoint in array_field(&value, "broker_endpoints") {
        rows.push(MakepadCompanionRow {
            row_id: string_field(endpoint, "endpoint_id", "broker.unknown"),
            row_family: "broker_endpoint".to_string(),
            status: string_field(endpoint, "status", "unknown"),
            title: string_field(endpoint, "endpoint_id", "Broker endpoint"),
            detail: format!(
                "{}://{}:{}{} authority={}",
                string_field(endpoint, "protocol", "unknown"),
                string_field(endpoint, "host", "unknown"),
                numeric_field(endpoint, "port", "unknown"),
                path_suffix(endpoint),
                string_field(endpoint, "authority", "unknown")
            ),
            source_schema: QUEST_DEVICE_LINK_SCHEMA.to_string(),
            source_report: "device_link".to_string(),
        });
    }
    for subscriber in array_field(&value, "runtime_subscribers") {
        rows.push(MakepadCompanionRow {
            row_id: string_field(subscriber, "subscriber_id", "runtime.subscriber.unknown"),
            row_family: "runtime_subscriber".to_string(),
            status: string_field(subscriber, "status", "unknown"),
            title: string_field(subscriber, "subscriber_id", "Runtime subscriber"),
            detail: format!(
                "app={} requestStream={} receiptStream={} delivered={}",
                string_field(subscriber, "runtime_app_id", "unknown"),
                string_field(subscriber, "request_stream_id", "unknown"),
                string_field(subscriber, "receipt_stream_id", "unknown"),
                numeric_field(subscriber, "last_dispatch_delivered_count", "0")
            ),
            source_schema: QUEST_DEVICE_LINK_SCHEMA.to_string(),
            source_report: "device_link".to_string(),
        });
    }
    for command in array_field(&value, "command_results") {
        rows.push(MakepadCompanionRow {
            row_id: string_field(command, "result_id", "command_result.unknown"),
            row_family: "command_result".to_string(),
            status: string_field(command, "status", "unknown"),
            title: string_field(command, "command", "Command result"),
            detail: format!(
                "route={} transport={} applied={} requiredStages={}",
                string_field(command, "route_id", "unknown"),
                string_field(command, "transport_kind", "unknown"),
                bool_field(command, "applied"),
                joined_strings(command, "required_stages")
            ),
            source_schema: QUEST_DEVICE_LINK_SCHEMA.to_string(),
            source_report: "device_link".to_string(),
        });
    }
    for capability in array_field(&value, "stream_capabilities") {
        rows.push(MakepadCompanionRow {
            row_id: string_field(capability, "capability_id", "capability.unknown"),
            row_family: "stream_capability".to_string(),
            status: string_field(capability, "status", "ready"),
            title: string_field(capability, "stream_id", "Stream capability"),
            detail: format!(
                "transport={} family={} direction={} rate={} clock={}",
                string_field(capability, "transport_kind", "unknown"),
                string_field(capability, "semantic_family", "unknown"),
                string_field(capability, "direction", "unknown"),
                string_field(capability, "rate_class", "unknown"),
                string_field(capability, "clock_policy", "unknown")
            ),
            source_schema: QUEST_DEVICE_LINK_SCHEMA.to_string(),
            source_report: "device_link".to_string(),
        });
    }
    for issue in array_field(&value, "issues") {
        rows.push(MakepadCompanionRow {
            row_id: first_string(issue, &["issue_code", "code", "id"], "device_link.issue"),
            row_family: "device_link_issue".to_string(),
            status: first_string(issue, &["severity", "status"], "warning"),
            title: first_string(issue, &["issue_code", "code", "title"], "Device-link issue"),
            detail: first_string(issue, &["message", "detail", "evidence"], "No issue detail"),
            source_schema: QUEST_DEVICE_LINK_SCHEMA.to_string(),
            source_report: "device_link".to_string(),
        });
    }
    Ok(rows)
}

pub(crate) fn project_protocol_matrix(text: &str) -> Result<Vec<MakepadCompanionRow>, String> {
    let value = parse_report(text, PROTOCOL_EVIDENCE_MATRIX_SCHEMA)?;
    let mut rows = Vec::new();
    let summary = value.get("summary").filter(|row| row.is_object());
    rows.push(MakepadCompanionRow {
        row_id: string_field(&value, "matrix_id", "protocol_matrix.summary"),
        row_family: "protocol_matrix_summary".to_string(),
        status: string_field(&value, "status", "unknown"),
        title: "Protocol evidence matrix".to_string(),
        detail: match summary {
            Some(summary) => format!(
                "requiredPromoted={}/{} allPromoted={} pending={}",
                numeric_field(summary, "required_promoted_count", "0"),
                numeric_field(summary, "required_row_count", "0"),
                bool_field(summary, "all_required_data_protocols_promoted"),
                joined_strings(summary, "pending_required_probe_ids")
            ),
            None => "summary=missing".to_string(),
        },
        source_schema: PROTOCOL_EVIDENCE_MATRIX_SCHEMA.to_string(),
        source_report: "protocol_matrix".to_string(),
    });

    for protocol in array_field(&value, "rows") {
        let probe_id = string_field(protocol, "probe_id", "QCL-unknown");
        let transport_kind = string_field(protocol, "transport_kind", "unknown");
        rows.push(MakepadCompanionRow {
            row_id: format!("protocol.{probe_id}"),
            row_family: "protocol_matrix_protocol".to_string(),
            status: string_field(protocol, "status", "unknown"),
            title: format!("{probe_id} {transport_kind}"),
            detail: format!(
                "capability={} family={} tier={} promotion={} allowed={} required={} missingGates={}",
                string_field(protocol, "capability_id", "unknown"),
                string_field(protocol, "semantic_family", "unknown"),
                string_field(protocol, "evidence_tier", "unknown"),
                string_field(protocol, "promotion_state", "unknown"),
                bool_field(protocol, "promotion_allowed"),
                bool_field(protocol, "required_for_fold_in"),
                joined_strings(protocol, "missing_gates")
            ),
            source_schema: PROTOCOL_EVIDENCE_MATRIX_SCHEMA.to_string(),
            source_report: "protocol_matrix".to_string(),
        });

        for gate in array_field(protocol, "gate_results") {
            let gate_id = string_field(gate, "gate_id", "protocol_matrix.gate");
            rows.push(MakepadCompanionRow {
                row_id: gate_id.clone(),
                row_family: "protocol_matrix_gate".to_string(),
                status: protocol_gate_status(&string_field(gate, "status", "unknown")),
                title: gate_id,
                detail: string_field(gate, "evidence", "No gate evidence"),
                source_schema: PROTOCOL_EVIDENCE_MATRIX_SCHEMA.to_string(),
                source_report: "protocol_matrix".to_string(),
            });
        }
    }

    for issue in array_field(&value, "issues") {
        rows.push(MakepadCompanionRow {
            row_id: first_string(
                issue,
                &["issue_code", "code", "id"],
                "protocol_matrix.issue",
            ),
            row_family: "protocol_matrix_issue".to_string(),
            status: first_string(issue, &["severity", "status"], "warning"),
            title: first_string(
                issue,
                &["issue_code", "code", "title"],
                "Protocol matrix issue",
            ),
            detail: first_string(issue, &["message", "detail", "evidence"], "No issue detail"),
            source_schema: PROTOCOL_EVIDENCE_MATRIX_SCHEMA.to_string(),
            source_report: "protocol_matrix".to_string(),
        });
    }
    Ok(rows)
}

pub(crate) fn build_makepad_companion_rows(
    catalog_text: &str,
    device_link_text: &str,
) -> Result<MakepadCompanionProjection, String> {
    build_makepad_companion_rows_with_protocol_matrix(catalog_text, device_link_text, None)
}

pub(crate) fn build_makepad_companion_rows_with_protocol_matrix(
    catalog_text: &str,
    device_link_text: &str,
    protocol_matrix_text: Option<&str>,
) -> Result<MakepadCompanionProjection, String> {
    let mut rows = project_companion_catalog(catalog_text)?;
    let catalog_rows = rows.len();
    let device_rows = project_device_link(device_link_text)?;
    let device_link_rows = device_rows.len();
    rows.extend(device_rows);
    let protocol_matrix_rows = if let Some(protocol_matrix_text) = protocol_matrix_text {
        let protocol_rows = project_protocol_matrix(protocol_matrix_text)?;
        let protocol_matrix_rows = protocol_rows.len();
        rows.extend(protocol_rows);
        protocol_matrix_rows
    } else {
        0
    };
    let status = aggregate_status(&rows).to_string();
    Ok(MakepadCompanionProjection {
        status,
        rows,
        catalog_rows,
        device_link_rows,
        protocol_matrix_rows,
    })
}

pub(crate) fn makepad_companion_projection_marker_line(
    phase: &str,
    projection: &MakepadCompanionProjection,
) -> String {
    format!(
        "{} schema={} phase={} status={} rowCount={} catalogRows={} deviceLinkRows={} protocolMatrixRows={} issueRows={} commandRows={} streamCapabilityRows={} protocolRows={} protocolGateRows={} authority=requester_inspector backendEvidence=hostess_companion_catalog_quest_device_link_and_protocol_matrix highRateJsonPayload=false settingsControlPayload=false",
        MAKEPAD_COMPANION_FRONTEND_MARKER,
        MAKEPAD_COMPANION_FRONTEND_SCHEMA,
        marker_value(phase),
        marker_value(&projection.status),
        projection.rows.len(),
        projection.catalog_rows,
        projection.device_link_rows,
        projection.protocol_matrix_rows,
        projection
            .rows
            .iter()
            .filter(|row| row.row_family.ends_with("_issue"))
            .count(),
        projection
            .rows
            .iter()
            .filter(|row| row.row_family == "command_result")
            .count(),
        projection
            .rows
            .iter()
            .filter(|row| row.row_family == "stream_capability")
            .count(),
        projection
            .rows
            .iter()
            .filter(|row| row.row_family == "protocol_matrix_protocol")
            .count(),
        projection
            .rows
            .iter()
            .filter(|row| row.row_family == "protocol_matrix_gate")
            .count()
    )
}

fn parse_report(text: &str, expected_schema: &str) -> Result<Value, String> {
    let value: Value =
        serde_json::from_str(text).map_err(|error| format!("invalid json: {error}"))?;
    let schema = value
        .get("$schema")
        .or_else(|| value.get("schema"))
        .and_then(Value::as_str)
        .unwrap_or("missing");
    if schema != expected_schema {
        return Err(format!("unsupported schema: {schema}"));
    }
    Ok(value)
}

fn array_field<'a>(value: &'a Value, key: &str) -> &'a [Value] {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or(&[])
}

fn count_array(value: &Value, key: &str) -> usize {
    array_field(value, key).len()
}

fn string_field(value: &Value, key: &str, default: &str) -> String {
    value
        .get(key)
        .and_then(Value::as_str)
        .filter(|text| !text.trim().is_empty())
        .unwrap_or(default)
        .to_string()
}

fn first_string(value: &Value, keys: &[&str], default: &str) -> String {
    keys.iter()
        .find_map(|key| {
            value
                .get(*key)
                .and_then(Value::as_str)
                .filter(|text| !text.trim().is_empty())
        })
        .unwrap_or(default)
        .to_string()
}

fn numeric_field(value: &Value, key: &str, default: &str) -> String {
    value
        .get(key)
        .and_then(|value| {
            value
                .as_i64()
                .map(|number| number.to_string())
                .or_else(|| value.as_u64().map(|number| number.to_string()))
                .or_else(|| value.as_f64().map(|number| format!("{number:.3}")))
        })
        .unwrap_or_else(|| default.to_string())
}

fn bool_field(value: &Value, key: &str) -> &'static str {
    match value.get(key).and_then(Value::as_bool) {
        Some(true) => "true",
        Some(false) => "false",
        None => "unknown",
    }
}

fn joined_strings(value: &Value, key: &str) -> String {
    let joined = array_field(value, key)
        .iter()
        .filter_map(Value::as_str)
        .filter(|text| !text.trim().is_empty())
        .collect::<Vec<_>>()
        .join(",");
    if joined.is_empty() {
        "none".to_string()
    } else {
        joined
    }
}

fn summary_detail(value: &Value) -> String {
    let Some(summary) = value.get("summary").filter(|summary| summary.is_object()) else {
        return "summary=missing".to_string();
    };
    format!(
        "modules={} workspaces={} transports={} issues={}",
        numeric_field(summary, "modules", "0"),
        numeric_field(summary, "workspaces", "0"),
        numeric_field(summary, "transports", "0"),
        numeric_field(summary, "issues", "0")
    )
}

fn issue_status(issues: &[Value], key: &str, id: &str) -> String {
    let mut saw_warning = false;
    for issue in issues {
        if issue.get(key).and_then(Value::as_str) != Some(id) {
            continue;
        }
        match issue
            .get("severity")
            .and_then(Value::as_str)
            .unwrap_or("warning")
        {
            "error" | "fail" | "blocked" => return "fail".to_string(),
            "warning" | "warn" => saw_warning = true,
            _ => {}
        }
    }
    if saw_warning {
        "warn".to_string()
    } else {
        "ready".to_string()
    }
}

fn adb_state_status(state: &str) -> String {
    if state == "device" {
        "pass".to_string()
    } else {
        "warn".to_string()
    }
}

fn protocol_gate_status(status: &str) -> String {
    match status {
        "satisfied" => "pass".to_string(),
        "missing" => "warn".to_string(),
        "blocked" => "blocked".to_string(),
        _ => {
            if status.trim().is_empty() {
                "unknown".to_string()
            } else {
                status.to_string()
            }
        }
    }
}

fn path_suffix(value: &Value) -> String {
    let path = string_field(value, "path", "");
    if path.is_empty() {
        String::new()
    } else {
        path
    }
}

fn aggregate_status(rows: &[MakepadCompanionRow]) -> &'static str {
    if rows.iter().any(|row| is_fail_status(&row.status)) {
        "fail"
    } else if rows.iter().any(|row| is_warn_status(&row.status)) {
        "warn"
    } else {
        "pass"
    }
}

fn is_fail_status(status: &str) -> bool {
    matches!(
        status,
        "fail" | "failed" | "error" | "blocked" | "rejected" | "invalid"
    )
}

fn is_warn_status(status: &str) -> bool {
    matches!(
        status,
        "warn" | "warning" | "degraded" | "usable_with_warnings" | "missing" | "unknown"
    )
}

fn marker_value(value: &str) -> String {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return "empty".to_string();
    }
    trimmed
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.' | ':' | '/') {
                ch
            } else {
                '_'
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    const CATALOG: &str = include_str!("../../../fixtures/companion/makepad-catalog-pass.json");
    const DEVICE_LINK: &str = include_str!("../../../fixtures/companion/device-link-pass.json");
    const PROTOCOL_MATRIX: &str =
        include_str!("../../../fixtures/companion/protocol-matrix-promoted.json");

    #[test]
    fn companion_frontend_projects_catalog_fixture() {
        let rows = project_companion_catalog(CATALOG).expect("catalog projects");

        assert!(rows
            .iter()
            .any(|row| row.row_id == "companion.command.bridge_probe"));
        assert!(rows
            .iter()
            .any(|row| row.row_id == "workspace.hostess_makepad.validation"));
        assert!(rows
            .iter()
            .any(|row| row.row_id == "transport.manifold_websocket"));
        assert!(rows.iter().all(|row| row.source_report == "catalog"));
    }

    #[test]
    fn companion_frontend_projects_device_link_fixture() {
        let rows = project_device_link(DEVICE_LINK).expect("device link projects");

        assert!(rows
            .iter()
            .any(|row| row.row_family == "runtime_subscriber"));
        assert!(rows.iter().any(|row| row.row_family == "command_result"));
        assert!(rows.iter().any(|row| row.row_family == "stream_capability"));
        assert!(rows.iter().all(|row| row.source_report == "device_link"));
    }

    #[test]
    fn companion_frontend_projects_protocol_matrix_fixture() {
        let rows = project_protocol_matrix(PROTOCOL_MATRIX).expect("protocol matrix projects");

        assert!(rows
            .iter()
            .any(|row| row.row_family == "protocol_matrix_summary" && row.status == "pass"));
        assert!(rows.iter().any(|row| {
            row.row_family == "protocol_matrix_protocol"
                && row.row_id == "protocol.QCL-081"
                && row.detail.contains("tier=broker_owned")
        }));
        assert!(rows.iter().any(|row| {
            row.row_family == "protocol_matrix_protocol"
                && row.row_id == "protocol.QCL-083"
                && row.detail.contains("tier=quest_runtime")
        }));
        assert!(rows
            .iter()
            .any(|row| row.row_id == "gate.qcl084.promotion_allowed"));
        assert!(rows
            .iter()
            .all(|row| row.source_report == "protocol_matrix"));
    }

    #[test]
    fn companion_frontend_marker_reports_shared_evidence_counts() {
        let projection = build_makepad_companion_rows_with_protocol_matrix(
            CATALOG,
            DEVICE_LINK,
            Some(PROTOCOL_MATRIX),
        )
        .expect("projection builds");
        let marker = makepad_companion_projection_marker_line("fixture", &projection);

        assert_eq!(projection.status, "pass");
        assert!(projection.protocol_matrix_rows > 0);
        assert!(marker.contains(MAKEPAD_COMPANION_FRONTEND_MARKER));
        assert!(marker.contains("schema=rusty.hostess.makepad.companion_frontend_projection.v1"));
        assert!(marker.contains("status=pass"));
        assert!(marker.contains("catalogRows="));
        assert!(marker.contains("deviceLinkRows="));
        assert!(marker.contains("protocolMatrixRows="));
        assert!(marker.contains("protocolRows=5"));
        assert!(marker.contains("authority=requester_inspector"));
        assert!(marker.contains(
            "backendEvidence=hostess_companion_catalog_quest_device_link_and_protocol_matrix"
        ));
        assert!(marker.contains("highRateJsonPayload=false"));
    }
}
