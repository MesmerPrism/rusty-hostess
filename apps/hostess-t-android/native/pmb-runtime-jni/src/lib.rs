use jni::objects::{JClass, JString};
use jni::sys::jstring;
use jni::JNIEnv;
use serde_json::json;
use std::path::PathBuf;

#[no_mangle]
pub extern "system" fn Java_io_github_mesmerprism_rustyhostess_t_PMBRuntime_nativeValidatePackage(
    mut env: JNIEnv,
    _class: JClass,
    package_root: JString,
) -> jstring {
    let result = jni_validate_package(&mut env, package_root).unwrap_or_else(|error| {
        json!({
            "schema": "rusty.manifold.projected_motion_breath.core_validation_report.v1",
            "package_root": "",
            "status": "fail",
            "checked_profiles": 0,
            "checked_command_payloads": 0,
            "checked_damaged_command_payloads": 0,
            "checked_source_bindings": 0,
            "checked_damaged_source_bindings": 0,
            "checked_adapter_normalization_cases": 0,
            "checked_damaged_adapter_normalization_cases": 0,
            "checked_cases": 0,
            "checked_damaged_cases": 0,
            "issues": [format!("issue.jni_bridge_failed:{error}")]
        })
        .to_string()
    });
    match env.new_string(result) {
        Ok(output) => output.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

#[no_mangle]
pub extern "system" fn Java_io_github_mesmerprism_rustyhostess_t_PMBRuntime_nativeRunControllerPreflight(
    mut env: JNIEnv,
    _class: JClass,
    package_root: JString,
) -> jstring {
    let result = jni_run_controller_preflight(&mut env, package_root).unwrap_or_else(|error| {
        json!({
            "schema": "rusty.manifold.projected_motion_breath.controller_preflight_report.v1",
            "package_root": "",
            "status": "fail",
            "preflight_id": "",
            "provider_id": "",
            "provider_kind": "",
            "binding_id": "",
            "selected_adapter_id": "",
            "selected_source_kind": "",
            "source_payload_kind": "",
            "input_stream_id": "",
            "output_stream_id": "",
            "source_id": "",
            "frame_id": "",
            "sample_count": 0,
            "normalized_sample_count": 0,
            "estimate_count": 0,
            "processor_core_executed": false,
            "runtime_execution_performed": false,
            "provider_boundary_exercised": false,
            "controller_provider_route_ready": false,
            "headset_controller_shape_used": false,
            "physical_controller_input_used": false,
            "controller_input_used": false,
            "manual_controller_trial_required": true,
            "estimates": [],
            "issues": [format!("issue.jni_bridge_failed:{error}")]
        })
        .to_string()
    });
    match env.new_string(result) {
        Ok(output) => output.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

#[no_mangle]
pub extern "system" fn Java_io_github_mesmerprism_rustyhostess_t_PMBRuntime_nativeRunLiveRouteSelfTest(
    mut env: JNIEnv,
    _class: JClass,
    package_root: JString,
) -> jstring {
    let result = jni_run_live_route_self_test(&mut env, package_root).unwrap_or_else(|error| {
        json!({
            "schema": "rusty.manifold.projected_motion_breath.live_route_report.v1",
            "package_root": "",
            "status": "fail",
            "route_id": "",
            "input_stream_ids": [],
            "normalized_stream_ids": [],
            "output_stream_ids": [],
            "processor_core_executed": false,
            "runtime_execution_performed": false,
            "external_transport_used": false,
            "live_sensor_used": false,
            "headset_execution_performed": false,
            "plan_only": true,
            "source_routes": [],
            "breath_samples": [],
            "feedback_samples": [],
            "receiver_subscription": {
                "command": "",
                "stream": "",
                "receiver_id": ""
            },
            "receiver_receipts": [],
            "issues": [format!("issue.jni_bridge_failed:{error}")]
        })
        .to_string()
    });
    match env.new_string(result) {
        Ok(output) => output.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

#[no_mangle]
pub extern "system" fn Java_io_github_mesmerprism_rustyhostess_t_PMBRuntime_nativeRunLiveRouteFromEvents(
    mut env: JNIEnv,
    _class: JClass,
    package_root: JString,
    events_jsonl: JString,
) -> jstring {
    let result = jni_run_live_route_from_transport_events(&mut env, package_root, events_jsonl)
        .unwrap_or_else(|error| {
            json!({
                "schema": "rusty.manifold.projected_motion_breath.live_route_report.v1",
                "package_root": "",
                "status": "fail",
                "route_id": "",
                "input_stream_ids": [],
                "normalized_stream_ids": [],
                "output_stream_ids": [],
                "processor_core_executed": false,
                "runtime_execution_performed": false,
                "external_transport_used": true,
                "live_sensor_used": true,
                "headset_execution_performed": true,
                "plan_only": false,
                "source_routes": [],
                "breath_samples": [],
                "feedback_samples": [],
                "receiver_subscription": {
                    "command": "",
                    "stream": "",
                    "receiver_id": ""
                },
                "receiver_receipts": [],
                "issues": [format!("issue.jni_bridge_failed:{error}")]
            })
            .to_string()
        });
    match env.new_string(result) {
        Ok(output) => output.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

fn jni_validate_package(env: &mut JNIEnv, package_root: JString) -> Result<String, String> {
    let package_root: String = env
        .get_string(&package_root)
        .map_err(|error| format!("package_root_jni:{error}"))?
        .into();
    let report =
        projected_motion_breath_core::validate_package_goldens(PathBuf::from(package_root))
            .map_err(|error| error.to_string())?;
    serde_json::to_string(&report).map_err(|error| error.to_string())
}

fn jni_run_live_route_self_test(env: &mut JNIEnv, package_root: JString) -> Result<String, String> {
    let package_root: String = env
        .get_string(&package_root)
        .map_err(|error| format!("package_root_jni:{error}"))?
        .into();
    let report =
        projected_motion_breath_core::run_live_route_self_test(PathBuf::from(package_root))
            .map_err(|error| error.to_string())?;
    serde_json::to_string(&report).map_err(|error| error.to_string())
}

fn jni_run_live_route_from_transport_events(
    env: &mut JNIEnv,
    package_root: JString,
    events_jsonl: JString,
) -> Result<String, String> {
    let package_root: String = env
        .get_string(&package_root)
        .map_err(|error| format!("package_root_jni:{error}"))?
        .into();
    let events_jsonl: String = env
        .get_string(&events_jsonl)
        .map_err(|error| format!("events_jsonl_jni:{error}"))?
        .into();
    let report = projected_motion_breath_core::run_live_route_from_transport_events(
        PathBuf::from(package_root),
        PathBuf::from(events_jsonl),
    )
    .map_err(|error| error.to_string())?;
    serde_json::to_string(&report).map_err(|error| error.to_string())
}

fn jni_run_controller_preflight(env: &mut JNIEnv, package_root: JString) -> Result<String, String> {
    let package_root: String = env
        .get_string(&package_root)
        .map_err(|error| format!("package_root_jni:{error}"))?
        .into();
    let report =
        projected_motion_breath_core::run_controller_preflight(PathBuf::from(package_root))
            .map_err(|error| error.to_string())?;
    serde_json::to_string(&report).map_err(|error| error.to_string())
}
