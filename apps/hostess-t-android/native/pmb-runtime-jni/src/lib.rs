use jni::objects::{JClass, JString};
use jni::sys::{jlong, jstring};
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

#[no_mangle]
pub extern "system" fn Java_io_github_mesmerprism_rustyhostess_t_PMBRuntime_nativeOpenLiveTransportProcessor(
    mut env: JNIEnv,
    _class: JClass,
    package_root: JString,
) -> jstring {
    let result = jni_open_live_transport_processor(&mut env, package_root).unwrap_or_else(|error| {
        json!({
            "schema": "rusty.manifold.projected_motion_breath.live_transport_processor_open.v1",
            "status": "fail",
            "handle": 0,
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
pub extern "system" fn Java_io_github_mesmerprism_rustyhostess_t_PMBRuntime_nativePushLiveTransportEvent(
    mut env: JNIEnv,
    _class: JClass,
    handle: jlong,
    event_json: JString,
    selected_source_preference: JString,
) -> jstring {
    let result = jni_push_live_transport_event(
        &mut env,
        handle,
        event_json,
        selected_source_preference,
    )
    .unwrap_or_else(|error| {
        json!({
            "schema": "rusty.manifold.projected_motion_breath.live_transport_update.v1",
            "status": "fail",
            "route_id": "",
            "package_root": "",
            "input_stream_id": "",
            "selected_source_preference": "auto",
            "selected_source_effective": "unknown",
            "event_sample_count": 0,
            "normalized_sample_count": 0,
            "output_sample_count": 0,
            "source_updates": [],
            "breath_samples": [],
            "feedback_samples": [],
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
pub extern "system" fn Java_io_github_mesmerprism_rustyhostess_t_PMBRuntime_nativeCloseLiveTransportProcessor(
    env: JNIEnv,
    _class: JClass,
    handle: jlong,
) -> jstring {
    let result = jni_close_live_transport_processor(handle).unwrap_or_else(|error| {
        json!({
            "schema": "rusty.manifold.projected_motion_breath.live_transport_update.v1",
            "status": "fail",
            "route_id": "",
            "package_root": "",
            "input_stream_id": "",
            "selected_source_preference": "auto",
            "selected_source_effective": "unknown",
            "event_sample_count": 0,
            "normalized_sample_count": 0,
            "output_sample_count": 0,
            "source_updates": [],
            "breath_samples": [],
            "feedback_samples": [],
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

fn jni_open_live_transport_processor(
    env: &mut JNIEnv,
    package_root: JString,
) -> Result<String, String> {
    let package_root: String = env
        .get_string(&package_root)
        .map_err(|error| format!("package_root_jni:{error}"))?
        .into();
    let processor = projected_motion_breath_core::LiveTransportProcessor::open(PathBuf::from(package_root))?;
    let handle = Box::into_raw(Box::new(processor)) as jlong;
    Ok(json!({
        "schema": "rusty.manifold.projected_motion_breath.live_transport_processor_open.v1",
        "status": "pass",
        "handle": handle,
        "issues": []
    })
    .to_string())
}

fn jni_push_live_transport_event(
    env: &mut JNIEnv,
    handle: jlong,
    event_json: JString,
    selected_source_preference: JString,
) -> Result<String, String> {
    if handle == 0 {
        return Err("live_transport_processor_handle_invalid".to_string());
    }
    let event_json: String = env
        .get_string(&event_json)
        .map_err(|error| format!("event_json_jni:{error}"))?
        .into();
    let selected_source_preference: String = env
        .get_string(&selected_source_preference)
        .map_err(|error| format!("selected_source_preference_jni:{error}"))?
        .into();
    let processor = unsafe {
        &mut *(handle as *mut projected_motion_breath_core::LiveTransportProcessor)
    };
    let update = processor.push_transport_event_json(&event_json, &selected_source_preference);
    serde_json::to_string(&update).map_err(|error| error.to_string())
}

fn jni_close_live_transport_processor(handle: jlong) -> Result<String, String> {
    if handle == 0 {
        return Err("live_transport_processor_handle_invalid".to_string());
    }
    let processor = unsafe {
        Box::from_raw(handle as *mut projected_motion_breath_core::LiveTransportProcessor)
    };
    let update = processor.close_report();
    serde_json::to_string(&update).map_err(|error| error.to_string())
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
