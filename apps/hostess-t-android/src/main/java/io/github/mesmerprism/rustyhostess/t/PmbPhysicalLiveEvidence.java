package io.github.mesmerprism.rustyhostess.t;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.Instant;
import java.util.List;

final class PmbPhysicalLiveEvidence {
    static final String SCHEMA = "rusty.hostess.projected_motion_breath.android_physical_live_execution_evidence.v1";

    private PmbPhysicalLiveEvidence() {
    }

    static JSONObject build(
            String hostProfile,
            Instant startedAt,
            Instant endedAt,
            JSONObject packageSnapshot,
            JSONObject captureReport,
            JSONObject routeReport,
            JSONObject brokerReport,
            List<String> errors,
            String failureMessage) throws JSONException {
        boolean quest = "headset".equals(hostProfile);
        boolean routePass = "pass".equals(routeReport.optString("status"));
        boolean brokerPass = "pass".equals(brokerReport.optString("status"));
        boolean capturePass = "pass".equals(captureReport.optString("status"));
        JSONObject evidence = new JSONObject();
        evidence.put("$schema", SCHEMA);
        evidence.put("status", errors.isEmpty() && capturePass && routePass && brokerPass ? "pass" : "fail");
        evidence.put("target", quest ? "quest" : "phone");
        evidence.put("host_profile", hostProfile);
        evidence.put("started_at_utc", startedAt.toString());
        evidence.put("ended_at_utc", endedAt.toString());
        evidence.put("duration_ms", Math.max(0L, endedAt.toEpochMilli() - startedAt.toEpochMilli()));
        evidence.put("software", new JSONObject()
                .put("origin", "rusty-hostess")
                .put("host_app", quest ? "app.rusty_hostess_t.quest" : "app.rusty_hostess_t.android")
                .put("host_app_version", "0.1.0"));
        evidence.put("package", packageSnapshot);
        evidence.put("execution", execution(hostProfile, captureReport, routeReport, brokerReport, failureMessage));
        evidence.put("input_capture_summary", captureSummary(captureReport));
        evidence.put("route_report_summary", routeSummary(routeReport));
        evidence.put("broker_publish_summary", brokerSummary(brokerReport));
        evidence.put("commands", new JSONArray()
                .put(new JSONObject()
                        .put("command", "capture_physical_polar_controller_events_from_quest_broker")
                        .put("status", capturePass ? "acknowledged" : "rejected"))
                .put(new JSONObject()
                        .put("command", "run_projected_motion_breath_live_route_from_events_android")
                        .put("status", routePass ? "acknowledged" : "rejected")
                        .put("runtime_path", PMBRuntime.RUNTIME_PATH))
                .put(new JSONObject()
                        .put("command", "publish_projected_motion_breath_feedback_to_quest_broker")
                        .put("status", brokerPass ? "acknowledged" : "rejected")
                        .put("stream", PmbBrokerBridge.STREAM_BREATH_FEEDBACK_STATE)));
        evidence.put("scorecard", scorecard(evidence, errors, failureMessage));
        return evidence;
    }

    private static JSONObject execution(
            String hostProfile,
            JSONObject captureReport,
            JSONObject routeReport,
            JSONObject brokerReport,
            String failureMessage) throws JSONException {
        boolean quest = "headset".equals(hostProfile);
        boolean coreExecuted = failureMessage == null
                && routeReport.optBoolean("processor_core_executed", false)
                && routeReport.optBoolean("runtime_execution_performed", false);
        boolean physicalPolar = captureReport.optBoolean("physical_polar_ble_used", false);
        boolean physicalController = captureReport.optBoolean("physical_controller_input_used", false);
        return new JSONObject()
                .put("mode", "projected_motion_breath_android_quest_physical_live")
                .put("runtime_path", PMBRuntime.RUNTIME_PATH)
                .put("input_capture_report_artifact", "latest.input-capture-report.json")
                .put("events_jsonl_artifact", "latest.transport-events.jsonl")
                .put("route_report_artifact", "latest.live-route-report.json")
                .put("broker_publish_report_artifact", "latest.broker-publish-report.json")
                .put("processor_core_executed", coreExecuted)
                .put("runtime_execution_performed", coreExecuted)
                .put("desktop_execution_performed", false)
                .put("pc_processor_core_executed", false)
                .put("platform_execution_performed", true)
                .put("android_execution_performed", true)
                .put("quest_execution_performed", quest)
                .put("device_required", true)
                .put("apk_build_performed", false)
                .put("openxr_runtime_used", true)
                .put("live_sensor_used", physicalPolar || physicalController)
                .put("physical_polar_ble_used", physicalPolar)
                .put("simulated_polar_provider_used", false)
                .put("polar_transport_authority", "quest_broker_polar_pmd_provider")
                .put("physical_controller_input_used", physicalController)
                .put("controller_input_used", physicalController)
                .put("simulated_controller_provider_used", false)
                .put("controller_transport_authority", "quest_makepad_xr_controller_pose_provider")
                .put("manual_polar_trial_required", !physicalPolar)
                .put("manual_controller_trial_required", !physicalController)
                .put("synthetic_live_route", false)
                .put("pmd_computed_on_quest", coreExecuted && quest)
                .put("pmd_computed_on_pc", false)
                .put("processor_authority", "quest_hostess_android_app")
                .put("broker_transport_used", brokerReport.optBoolean("broker_transport_used", false))
                .put("publish_mode", brokerReport.optString("publish_mode", "missing"))
                .put("live_publish_during_capture", brokerReport.optBoolean("live_publish_during_capture", false))
                .put("incremental_processor_used", brokerReport.optBoolean("incremental_processor_used", false))
                .put("snapshot_replay_used", brokerReport.optBoolean("snapshot_replay_used", true))
                .put("first_selected_publish_elapsed_ms", brokerReport.optLong("first_selected_publish_elapsed_ms", -1L))
                .put("last_selected_publish_elapsed_ms", brokerReport.optLong("last_selected_publish_elapsed_ms", -1L))
                .put("selected_breath_published_to_broker", brokerReport.optInt("selected_breath_published_count", 0) > 0)
                .put("breath_state_published_to_broker", brokerReport.optInt("state_published_count", 0) > 0)
                .put("breath_state_value_published_to_broker", brokerReport.optInt("state_value_published_count", 0) > 0)
                .put("breath_selected_source_preference", brokerReport.optString("selected_source_preference", "auto"))
                .put("breath_selected_source_effective", brokerReport.optString("selected_source_effective", "unknown"))
                .put("feedback_published_to_broker", brokerReport.optInt("feedback_published_count", 0) > 0)
                .put("makepad_feedback_receipt_count", brokerReport.optInt("feedback_receipt_count", 0))
                .put("app_private_evidence", true);
    }

    private static JSONObject captureSummary(JSONObject captureReport) throws JSONException {
        return new JSONObject()
                .put("schema", captureReport.optString("schema", ""))
                .put("status", captureReport.optString("status", "missing"))
                .put("broker_connected", captureReport.optBoolean("broker_connected", false))
                .put("polar_start_status", captureReport.optString("polar_start_status", "missing"))
                .put("polar_stop_status", captureReport.optString("polar_stop_status", "missing"))
                .put("polar_event_count", captureReport.optInt("polar_event_count", 0))
                .put("object_pose_event_count", captureReport.optInt("object_pose_event_count", 0))
                .put("active_tracked_connected_object_pose_count", captureReport.optInt("active_tracked_connected_object_pose_count", 0))
                .put("physical_polar_ble_used", captureReport.optBoolean("physical_polar_ble_used", false))
                .put("physical_controller_input_used", captureReport.optBoolean("physical_controller_input_used", false));
    }

    private static JSONObject routeSummary(JSONObject routeReport) throws JSONException {
        JSONArray sourceRoutes = routeReport.optJSONArray("source_routes");
        JSONArray feedbackSamples = routeReport.optJSONArray("feedback_samples");
        JSONArray breathSamples = routeReport.optJSONArray("breath_samples");
        JSONArray stateSamples = routeReport.optJSONArray("state_samples");
        JSONArray stateValueSamples = routeReport.optJSONArray("state_value_samples");
        return new JSONObject()
                .put("schema", routeReport.optString("schema", ""))
                .put("status", routeReport.optString("status", "missing"))
                .put("route_id", routeReport.optString("route_id", ""))
                .put("input_stream_ids", routeReport.optJSONArray("input_stream_ids"))
                .put("normalized_stream_ids", routeReport.optJSONArray("normalized_stream_ids"))
                .put("output_stream_ids", routeReport.optJSONArray("output_stream_ids"))
                .put("source_route_count", sourceRoutes == null ? 0 : sourceRoutes.length())
                .put("breath_sample_count", breathSamples == null ? 0 : breathSamples.length())
                .put("state_sample_count", stateSamples == null ? 0 : stateSamples.length())
                .put("state_value_sample_count", stateValueSamples == null ? 0 : stateValueSamples.length())
                .put("feedback_sample_count", feedbackSamples == null ? 0 : feedbackSamples.length())
                .put("processor_core_executed", routeReport.optBoolean("processor_core_executed", false))
                .put("runtime_execution_performed", routeReport.optBoolean("runtime_execution_performed", false))
                .put("plan_only_fixture", routeReport.optBoolean("plan_only", true))
                .put("external_transport_used", routeReport.optBoolean("external_transport_used", false))
                .put("live_sensor_used", routeReport.optBoolean("live_sensor_used", false))
                .put("source_routes", sourceRoutes == null ? new JSONArray() : sourceRoutes);
    }

    private static JSONObject brokerSummary(JSONObject brokerReport) throws JSONException {
        return new JSONObject()
                .put("schema", brokerReport.optString("schema", ""))
                .put("status", brokerReport.optString("status", "missing"))
                .put("broker_transport_used", brokerReport.optBoolean("broker_transport_used", false))
                .put("broker_connected", brokerReport.optBoolean("broker_connected", false))
                .put("publish_mode", brokerReport.optString("publish_mode", "missing"))
                .put("live_publish_during_capture", brokerReport.optBoolean("live_publish_during_capture", false))
                .put("incremental_processor_used", brokerReport.optBoolean("incremental_processor_used", false))
                .put("snapshot_replay_used", brokerReport.optBoolean("snapshot_replay_used", true))
                .put("input_event_processed_count", brokerReport.optInt("input_event_processed_count", 0))
                .put("live_processor_update_count", brokerReport.optInt("live_processor_update_count", 0))
                .put("live_processor_output_update_count", brokerReport.optInt("live_processor_output_update_count", 0))
                .put("first_selected_publish_elapsed_ms", brokerReport.optLong("first_selected_publish_elapsed_ms", -1L))
                .put("last_selected_publish_elapsed_ms", brokerReport.optLong("last_selected_publish_elapsed_ms", -1L))
                .put("breath_published_count", brokerReport.optInt("breath_published_count", 0))
                .put("selected_breath_published_count", brokerReport.optInt("selected_breath_published_count", 0))
                .put("selection_state_published_count", brokerReport.optInt("selection_state_published_count", 0))
                .put("state_published_count", brokerReport.optInt("state_published_count", 0))
                .put("state_value_published_count", brokerReport.optInt("state_value_published_count", 0))
                .put("selected_source_preference", brokerReport.optString("selected_source_preference", "auto"))
                .put("selected_source_effective", brokerReport.optString("selected_source_effective", "unknown"))
                .put("feedback_published_count", brokerReport.optInt("feedback_published_count", 0))
                .put("feedback_receipt_count", brokerReport.optInt("feedback_receipt_count", 0))
                .put("receipt_stream_id", brokerReport.optString("receipt_stream_id", ""));
    }

    private static JSONObject scorecard(
            JSONObject evidence,
            List<String> errors,
            String failureMessage) throws JSONException {
        JSONObject execution = evidence.optJSONObject("execution");
        JSONObject capture = evidence.optJSONObject("input_capture_summary");
        JSONObject route = evidence.optJSONObject("route_report_summary");
        JSONObject broker = evidence.optJSONObject("broker_publish_summary");
        JSONArray checks = new JSONArray();
        checks.put(check("validation.check.pmb_physical_live_core_loaded",
                PMBRuntime.isAvailable(),
                PMBRuntime.isAvailable() ? "PMB JNI runtime loaded" : PMBRuntime.loadError()));
        checks.put(check("validation.check.pmb_physical_live_inputs",
                capture != null
                        && capture.optBoolean("physical_polar_ble_used")
                        && capture.optBoolean("physical_controller_input_used")
                        && capture.optInt("polar_event_count", 0) > 0
                        && capture.optInt("active_tracked_connected_object_pose_count", 0) > 0,
                "Quest broker provided physical Polar ACC and active/tracked/connected controller pose events"));
        checks.put(check("validation.check.pmb_physical_live_quest_authority",
                execution != null
                        && execution.optBoolean("android_execution_performed")
                        && execution.optBoolean("pmd_computed_on_quest")
                        && !execution.optBoolean("pmd_computed_on_pc")
                        && !execution.optBoolean("simulated_polar_provider_used")
                        && !execution.optBoolean("simulated_controller_provider_used"),
                "PMB processing ran through the Quest Android app without PC or simulated providers"));
        checks.put(check("validation.check.pmb_physical_live_route_status",
                route != null
                        && "pass".equals(route.optString("status"))
                        && !route.optBoolean("plan_only_fixture", true)
                        && route.optBoolean("external_transport_used")
                        && route.optBoolean("live_sensor_used")
                        && route.optInt("state_sample_count", 0) > 0
                        && route.optInt("state_value_sample_count", 0) > 0
                        && contains(route.optJSONArray("input_stream_ids"), "bio:polar_acc")
                        && contains(route.optJSONArray("input_stream_ids"), "stream.motion.object_pose"),
                "PMB live route consumed broker transport events and produced raw plus processed state samples"));
        checks.put(check("validation.check.pmb_physical_live_makepad_receipts",
                broker != null
                        && "event_driven_live_processor".equals(broker.optString("publish_mode"))
                        && broker.optBoolean("live_publish_during_capture")
                        && broker.optBoolean("incremental_processor_used")
                        && !broker.optBoolean("snapshot_replay_used")
                        && broker.optInt("input_event_processed_count", 0) > 0
                        && broker.optInt("live_processor_output_update_count", 0) > 0
                        && broker.optLong("first_selected_publish_elapsed_ms", -1L) >= 0L
                        && broker.optInt("selected_breath_published_count", 0) > 0
                        && broker.optInt("state_published_count", 0) > 0
                        && broker.optInt("state_value_published_count", 0) > 0
                        && broker.optInt("feedback_published_count", 0) > 0
                        && broker.optInt("feedback_receipt_count", 0) == broker.optInt("selected_breath_published_count", -1),
                "Makepad acknowledged selected breath samples while raw state, processed state-value, and PMB feedback were published"));

        JSONArray issueObjects = new JSONArray();
        for (String error : errors) {
            issueObjects.put(new JSONObject()
                    .put("code", "hostess.issue.pmb_physical_live_failed")
                    .put("severity", "error")
                    .put("message", error));
        }
        if (failureMessage != null) {
            issueObjects.put(new JSONObject()
                    .put("code", "hostess.issue.pmb_physical_live_runtime_exception")
                    .put("severity", "error")
                    .put("message", failureMessage));
        }
        String status = "pass";
        for (int index = 0; index < checks.length(); index++) {
            if (!"pass".equals(checks.getJSONObject(index).optString("status"))) {
                status = "fail";
            }
        }
        return new JSONObject()
                .put("$schema", "rusty.manifold.validation.scorecard.v1")
                .put("scorecard_id", "scorecard.hostess.projected_motion_breath.android_physical_live")
                .put("target_id", "hostess.projected_motion_breath.android_physical_live")
                .put("target_revision", 1)
                .put("status", status)
                .put("checks", checks)
                .put("issues", issueObjects);
    }

    private static JSONObject check(String checkId, boolean passed, String evidence) throws JSONException {
        return new JSONObject()
                .put("check_id", checkId)
                .put("status", passed ? "pass" : "fail")
                .put("evidence", evidence);
    }

    private static boolean contains(JSONArray values, String expected) {
        if (values == null) {
            return false;
        }
        for (int index = 0; index < values.length(); index++) {
            if (expected.equals(values.optString(index))) {
                return true;
            }
        }
        return false;
    }
}
