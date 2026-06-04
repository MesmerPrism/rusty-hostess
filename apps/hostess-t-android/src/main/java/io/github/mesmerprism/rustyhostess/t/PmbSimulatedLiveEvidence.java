package io.github.mesmerprism.rustyhostess.t;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.Instant;
import java.util.List;

final class PmbSimulatedLiveEvidence {
    static final String SCHEMA = "rusty.hostess.projected_motion_breath.android_simulated_live_execution_evidence.v1";

    private PmbSimulatedLiveEvidence() {
    }

    static JSONObject build(
            String hostProfile,
            Instant startedAt,
            Instant endedAt,
            JSONObject packageSnapshot,
            JSONObject routeReport,
            JSONObject brokerReport,
            List<String> errors,
            String failureMessage) throws JSONException {
        boolean quest = "headset".equals(hostProfile);
        JSONObject evidence = new JSONObject();
        evidence.put("$schema", SCHEMA);
        evidence.put("status", errors.isEmpty()
                && "pass".equals(routeReport.optString("status"))
                && "pass".equals(brokerReport.optString("status"))
                ? "pass"
                : "fail");
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
        evidence.put("execution", execution(hostProfile, routeReport, brokerReport, failureMessage));
        evidence.put("route_report_summary", routeSummary(routeReport));
        evidence.put("broker_publish_summary", brokerSummary(brokerReport));
        evidence.put("commands", new JSONArray()
                .put(new JSONObject()
                        .put("command", "run_projected_motion_breath_live_route_self_test_android")
                        .put("status", "pass".equals(routeReport.optString("status")) ? "acknowledged" : "rejected")
                        .put("runtime_path", PMBRuntime.RUNTIME_PATH))
                .put(new JSONObject()
                        .put("command", "publish_projected_motion_breath_feedback_to_quest_broker")
                        .put("status", "pass".equals(brokerReport.optString("status")) ? "acknowledged" : "rejected")
                        .put("stream", PmbBrokerBridge.STREAM_BREATH_FEEDBACK_STATE)));
        evidence.put("scorecard", scorecard(evidence, routeReport, brokerReport, errors, failureMessage));
        return evidence;
    }

    private static JSONObject execution(
            String hostProfile,
            JSONObject routeReport,
            JSONObject brokerReport,
            String failureMessage) throws JSONException {
        boolean quest = "headset".equals(hostProfile);
        boolean coreExecuted = failureMessage == null
                && routeReport.optBoolean("processor_core_executed", false)
                && routeReport.optBoolean("runtime_execution_performed", false);
        return new JSONObject()
                .put("mode", "projected_motion_breath_android_quest_simulated_live")
                .put("runtime_path", PMBRuntime.RUNTIME_PATH)
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
                .put("openxr_runtime_used", false)
                .put("live_sensor_used", false)
                .put("physical_polar_ble_used", false)
                .put("simulated_polar_provider_used", true)
                .put("polar_transport_authority", "quest_app_simulated_polar_provider")
                .put("physical_controller_input_used", false)
                .put("controller_input_used", false)
                .put("simulated_controller_provider_used", true)
                .put("controller_transport_authority", "quest_app_simulated_controller_provider")
                .put("manual_polar_trial_required", true)
                .put("manual_controller_trial_required", true)
                .put("synthetic_live_route", true)
                .put("pmd_computed_on_quest", coreExecuted)
                .put("pmd_computed_on_pc", false)
                .put("processor_authority", "quest_hostess_android_app")
                .put("broker_transport_used", brokerReport.optBoolean("broker_transport_used", false))
                .put("selected_breath_published_to_broker", brokerReport.optInt("selected_breath_published_count", 0) > 0)
                .put("breath_selected_source_preference", brokerReport.optString("selected_source_preference", "auto"))
                .put("breath_selected_source_effective", brokerReport.optString("selected_source_effective", "unknown"))
                .put("feedback_published_to_broker", brokerReport.optInt("feedback_published_count", 0) > 0)
                .put("makepad_feedback_receipt_count", brokerReport.optInt("feedback_receipt_count", 0))
                .put("app_private_evidence", true);
    }

    private static JSONObject routeSummary(JSONObject routeReport) throws JSONException {
        JSONArray sourceRoutes = routeReport.optJSONArray("source_routes");
        JSONArray feedbackSamples = routeReport.optJSONArray("feedback_samples");
        JSONArray breathSamples = routeReport.optJSONArray("breath_samples");
        return new JSONObject()
                .put("schema", routeReport.optString("schema", ""))
                .put("status", routeReport.optString("status", "missing"))
                .put("route_id", routeReport.optString("route_id", ""))
                .put("input_stream_ids", routeReport.optJSONArray("input_stream_ids"))
                .put("normalized_stream_ids", routeReport.optJSONArray("normalized_stream_ids"))
                .put("output_stream_ids", routeReport.optJSONArray("output_stream_ids"))
                .put("source_route_count", sourceRoutes == null ? 0 : sourceRoutes.length())
                .put("breath_sample_count", breathSamples == null ? 0 : breathSamples.length())
                .put("feedback_sample_count", feedbackSamples == null ? 0 : feedbackSamples.length())
                .put("processor_core_executed", routeReport.optBoolean("processor_core_executed", false))
                .put("runtime_execution_performed", routeReport.optBoolean("runtime_execution_performed", false))
                .put("plan_only_fixture", routeReport.optBoolean("plan_only", false))
                .put("source_routes", sourceRoutes == null ? new JSONArray() : sourceRoutes);
    }

    private static JSONObject brokerSummary(JSONObject brokerReport) throws JSONException {
        return new JSONObject()
                .put("schema", brokerReport.optString("schema", ""))
                .put("status", brokerReport.optString("status", "missing"))
                .put("broker_transport_used", brokerReport.optBoolean("broker_transport_used", false))
                .put("broker_connected", brokerReport.optBoolean("broker_connected", false))
                .put("breath_published_count", brokerReport.optInt("breath_published_count", 0))
                .put("selected_breath_published_count", brokerReport.optInt("selected_breath_published_count", 0))
                .put("selection_state_published_count", brokerReport.optInt("selection_state_published_count", 0))
                .put("selected_source_preference", brokerReport.optString("selected_source_preference", "auto"))
                .put("selected_source_effective", brokerReport.optString("selected_source_effective", "unknown"))
                .put("feedback_published_count", brokerReport.optInt("feedback_published_count", 0))
                .put("feedback_receipt_count", brokerReport.optInt("feedback_receipt_count", 0))
                .put("receipt_stream_id", brokerReport.optString("receipt_stream_id", ""));
    }

    private static JSONObject scorecard(
            JSONObject evidence,
            JSONObject routeReport,
            JSONObject brokerReport,
            List<String> errors,
            String failureMessage) throws JSONException {
        JSONObject execution = evidence.optJSONObject("execution");
        JSONObject route = evidence.optJSONObject("route_report_summary");
        JSONObject broker = evidence.optJSONObject("broker_publish_summary");
        JSONArray checks = new JSONArray();
        checks.put(check(
                "validation.check.pmb_simulated_live_core_loaded",
                PMBRuntime.isAvailable(),
                PMBRuntime.isAvailable() ? "PMB JNI runtime loaded" : PMBRuntime.loadError()));
        checks.put(check(
                "validation.check.pmb_simulated_live_route_status",
                "pass".equals(routeReport.optString("status")),
                "PMB live route report status was " + routeReport.optString("status", "missing")));
        checks.put(check(
                "validation.check.pmb_simulated_live_sources",
                route != null
                        && route.optInt("source_route_count", 0) >= 2
                        && contains(route.optJSONArray("input_stream_ids"), "bio:polar_acc")
                        && contains(route.optJSONArray("input_stream_ids"), "stream.motion.object_pose"),
                "PMB simulated live route included Polar ACC and controller object-pose inputs"));
        checks.put(check(
                "validation.check.pmb_simulated_live_quest_authority",
                execution != null
                        && execution.optBoolean("android_execution_performed")
                        && execution.optBoolean("pmd_computed_on_quest")
                        && !execution.optBoolean("pmd_computed_on_pc")
                        && execution.optBoolean("simulated_polar_provider_used")
                        && execution.optBoolean("simulated_controller_provider_used"),
                "PMB processing ran through the Quest Android app with simulated input providers"));
        checks.put(check(
                "validation.check.pmb_simulated_live_broker_publish",
                broker != null
                        && broker.optBoolean("broker_transport_used")
                        && broker.optInt("selected_breath_published_count", 0) > 0
                        && broker.optInt("feedback_published_count", 0) > 0,
                "Quest Android app published selected breath and PMB feedback samples to the broker"));
        checks.put(check(
                "validation.check.pmb_simulated_live_makepad_receipts",
                broker != null
                        && broker.optInt("selected_breath_published_count", 0) > 0
                        && broker.optInt("feedback_receipt_count", 0) == broker.optInt("selected_breath_published_count", -1),
                "Makepad feedback subscriber acknowledged every selected breath sample"));
        checks.put(check(
                "validation.check.pmb_simulated_live_non_physical_gate",
                execution != null
                        && !execution.optBoolean("physical_polar_ble_used")
                        && !execution.optBoolean("physical_controller_input_used")
                        && !execution.optBoolean("controller_input_used")
                        && execution.optBoolean("manual_polar_trial_required")
                        && execution.optBoolean("manual_controller_trial_required"),
                "run used simulated providers and kept physical Polar/controller trials pending"));

        JSONArray issueObjects = new JSONArray();
        for (String error : errors) {
            issueObjects.put(new JSONObject()
                    .put("code", "hostess.issue.pmb_simulated_live_failed")
                    .put("severity", "error")
                    .put("message", error));
        }
        if (failureMessage != null) {
            issueObjects.put(new JSONObject()
                    .put("code", "hostess.issue.pmb_simulated_live_runtime_exception")
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
                .put("scorecard_id", "scorecard.hostess.projected_motion_breath.android_simulated_live")
                .put("target_id", "hostess.projected_motion_breath.android_simulated_live")
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
