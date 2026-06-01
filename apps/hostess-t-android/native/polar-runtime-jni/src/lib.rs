use jni::objects::{JClass, JString};
use jni::sys::jstring;
use jni::JNIEnv;
use serde_json::json;

#[no_mangle]
pub extern "system" fn Java_io_github_mesmerprism_rustyhostess_t_PolarRuntime_nativeRunGraph(
    mut env: JNIEnv,
    _class: JClass,
    graph_json: JString,
    input_json: JString,
    selected_modules_json: JString,
) -> jstring {
    let result = jni_run_graph(&mut env, graph_json, input_json, selected_modules_json)
        .unwrap_or_else(|error| {
            json!({
                "$schema": "rusty.manifold.graph.execution_report.v1",
                "graph_id": "graph.polar_h10_processing",
                "graph_revision": 0,
                "runtime_path": "rust.polar_h10_core.v1",
                "selected_module_ids": [],
                "resolved_node_ids": [],
                "status": "fail",
                "node_reports": [],
                "output_stream_ids": [],
                "issues": [{
                    "issue_code": "issue.jni_bridge_failed",
                    "severity": "error",
                    "message": error
                }],
                "streams": []
            })
            .to_string()
        });
    match env.new_string(result) {
        Ok(output) => output.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

fn jni_run_graph(
    env: &mut JNIEnv,
    graph_json: JString,
    input_json: JString,
    selected_modules_json: JString,
) -> Result<String, String> {
    let graph_json: String = env
        .get_string(&graph_json)
        .map_err(|error| format!("graph_json_jni:{error}"))?
        .into();
    let input_json: String = env
        .get_string(&input_json)
        .map_err(|error| format!("input_json_jni:{error}"))?
        .into();
    let selected_modules_json: String = env
        .get_string(&selected_modules_json)
        .map_err(|error| format!("selected_modules_json_jni:{error}"))?
        .into();
    polar_h10_core::run_graph_json(&graph_json, &input_json, &selected_modules_json)
}
