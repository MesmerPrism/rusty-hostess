package io.github.mesmerprism.rustyhostess.t;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

final class PmbAndroidEvidence {
    private static final String SOFTWARE_ORIGIN = "rusty-hostess";

    private final HostessAssetStore assets;

    PmbAndroidEvidence(HostessAssetStore assets) {
        this.assets = assets;
    }

    JSONObject pmbReplayEvidence(
            String hostProfile,
            Instant startedAt,
            Instant endedAt,
            String status,
            JSONObject coreReport,
            List<String> errors,
            String failureMessage) throws JSONException {
        boolean quest = "headset".equals(hostProfile);
        boolean coreExecuted = failureMessage == null;
        JSONObject evidence = new JSONObject();
        evidence.put("$schema", "rusty.hostess.projected_motion_breath.android_replay_execution_evidence.v1");
        evidence.put("status", errors.isEmpty() && "pass".equals(status) ? "pass" : "fail");
        evidence.put("target", quest ? "quest" : "phone");
        evidence.put("host_profile", hostProfile);
        evidence.put("started_at_utc", startedAt.toString());
        evidence.put("ended_at_utc", endedAt.toString());
        evidence.put("duration_ms", Math.max(0L, endedAt.toEpochMilli() - startedAt.toEpochMilli()));
        evidence.put("software", new JSONObject()
                .put("origin", SOFTWARE_ORIGIN)
                .put("host_app", quest ? "app.rusty_hostess_t.quest" : "app.rusty_hostess_t.android")
                .put("host_app_version", "0.1.0"));
        evidence.put("package", PmbPackageAssets.snapshot(assets));
        evidence.put("execution", new JSONObject()
                .put("mode", "projected_motion_breath_android_synthetic_replay")
                .put("runtime_path", PMBRuntime.RUNTIME_PATH)
                .put("core_report_artifact", "latest.core-validation-report.json")
                .put("processor_core_executed", coreExecuted)
                .put("execution_performed", true)
                .put("runtime_execution_performed", coreExecuted)
                .put("desktop_execution_performed", false)
                .put("platform_execution_performed", true)
                .put("android_execution_performed", true)
                .put("quest_execution_performed", quest)
                .put("device_required", true)
                .put("apk_build_performed", false)
                .put("openxr_runtime_used", false)
                .put("live_sensor_used", false)
                .put("controller_input_used", false)
                .put("synthetic_replay", true)
                .put("app_private_evidence", true));
        evidence.put("core_report_summary", pmbCoreReportSummary(coreReport));
        evidence.put("commands", new JSONArray()
                .put(new JSONObject()
                        .put("command", "run_projected_motion_breath_core_validate_goldens_android")
                        .put("status", "pass".equals(coreReport.optString("status")) ? "acknowledged" : "rejected")
                        .put("runtime_path", PMBRuntime.RUNTIME_PATH)));
        evidence.put("scorecard", pmbReplayScorecard(evidence, coreReport, errors, failureMessage));
        return evidence;
    }

    JSONObject pmbControllerPreflightEvidence(
            String hostProfile,
            Instant startedAt,
            Instant endedAt,
            String status,
            JSONObject preflightReport,
            List<String> errors,
            String failureMessage) throws JSONException {
        boolean quest = "headset".equals(hostProfile);
        boolean coreExecuted = failureMessage == null && preflightReport.optBoolean("processor_core_executed", false);
        boolean routeReady = "pass".equals(preflightReport.optString("status"))
                && preflightReport.optBoolean("controller_provider_route_ready", false);
        boolean controllerShapeUsed = preflightReport.optBoolean("headset_controller_shape_used", false);
        boolean physicalControllerInputUsed = preflightReport.optBoolean("physical_controller_input_used", false);
        boolean controllerInputUsed = preflightReport.optBoolean("controller_input_used", false);
        boolean manualTrialRequired = preflightReport.optBoolean("manual_controller_trial_required", true);
        JSONObject evidence = new JSONObject();
        evidence.put("$schema", "rusty.hostess.projected_motion_breath.android_controller_preflight_evidence.v1");
        evidence.put("status", errors.isEmpty() && "pass".equals(status) && routeReady ? "pass" : "fail");
        evidence.put("target", quest ? "quest" : "phone");
        evidence.put("host_profile", hostProfile);
        evidence.put("started_at_utc", startedAt.toString());
        evidence.put("ended_at_utc", endedAt.toString());
        evidence.put("duration_ms", Math.max(0L, endedAt.toEpochMilli() - startedAt.toEpochMilli()));
        evidence.put("software", new JSONObject()
                .put("origin", SOFTWARE_ORIGIN)
                .put("host_app", quest ? "app.rusty_hostess_t.quest" : "app.rusty_hostess_t.android")
                .put("host_app_version", "0.1.0"));
        evidence.put("package", PmbPackageAssets.snapshot(assets));
        evidence.put("execution", new JSONObject()
                .put("mode", "projected_motion_breath_android_controller_preflight")
                .put("runtime_path", PMBRuntime.RUNTIME_PATH)
                .put("controller_preflight_report_artifact", "latest.controller-preflight-report.json")
                .put("pmb_controller_path_preflight_passed", routeReady)
                .put("processor_core_executed", coreExecuted)
                .put("controller_provider_route_ready", routeReady)
                .put("provider_boundary_exercised", preflightReport.optBoolean("provider_boundary_exercised", false))
                .put("controller_shape_used", controllerShapeUsed)
                .put("quest_controller_shape_used", quest && controllerShapeUsed)
                .put("execution_performed", true)
                .put("runtime_execution_performed", preflightReport.optBoolean("runtime_execution_performed", false) && failureMessage == null)
                .put("desktop_execution_performed", false)
                .put("platform_execution_performed", true)
                .put("android_execution_performed", true)
                .put("quest_execution_performed", quest)
                .put("device_required", true)
                .put("apk_build_performed", false)
                .put("openxr_runtime_used", false)
                .put("live_sensor_used", false)
                .put("physical_controller_input_used", physicalControllerInputUsed)
                .put("controller_input_used", controllerInputUsed)
                .put("human_controller_trial_performed", false)
                .put("manual_controller_trial_required", manualTrialRequired)
                .put("synthetic_replay", true)
                .put("preflight_fixture_packaged", true)
                .put("app_private_evidence", true));
        evidence.put("controller_preflight_report_summary", pmbControllerPreflightReportSummary(preflightReport));
        evidence.put("commands", new JSONArray()
                .put(new JSONObject()
                        .put("command", "run_projected_motion_breath_controller_preflight_android")
                        .put("status", routeReady ? "acknowledged" : "rejected")
                        .put("runtime_path", PMBRuntime.RUNTIME_PATH)));
        evidence.put("scorecard", pmbControllerPreflightScorecard(evidence, preflightReport, errors, failureMessage));
        return evidence;
    }

    private JSONObject pmbReplayScorecard(
            JSONObject evidence,
            JSONObject coreReport,
            List<String> errors,
            String failureMessage) throws JSONException {
        JSONObject execution = evidence.optJSONObject("execution");
        JSONObject summary = evidence.optJSONObject("core_report_summary");
        JSONArray checks = new JSONArray();
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_android_core_loaded",
                PMBRuntime.isAvailable(),
                PMBRuntime.isAvailable() ? "PMB JNI runtime loaded" : PMBRuntime.loadError()));
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_android_core_report_status",
                "pass".equals(coreReport.optString("status")),
                "projected-motion-breath core report status was " + coreReport.optString("status", "missing")));
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_android_core_goldens_executed",
                summary.optInt("checked_cases", 0) >= 2 && summary.optInt("checked_damaged_cases", 0) >= 2,
                "projected-motion breath pose/vector golden and damaged cases executed on Android"));
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_android_adapter_normalization_executed",
                summary.optInt("checked_adapter_normalization_cases", 0) >= 3
                        && summary.optInt("checked_damaged_adapter_normalization_cases", 0) >= 2,
                "projected-motion breath adapter-normalization valid and damaged cases executed on Android"));
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_android_synthetic_only",
                execution != null
                        && execution.optBoolean("synthetic_replay")
                        && !execution.optBoolean("openxr_runtime_used")
                        && !execution.optBoolean("live_sensor_used")
                        && !execution.optBoolean("controller_input_used"),
                "PMB Android replay used synthetic packaged fixtures, not OpenXR, live sensors, or controller input"));
        JSONArray issueObjects = new JSONArray();
        for (String error : errors) {
            issueObjects.put(new JSONObject()
                    .put("code", "hostess.issue.pmb_android_replay_failed")
                    .put("severity", "error")
                    .put("message", error));
        }
        if (failureMessage != null) {
            issueObjects.put(new JSONObject()
                    .put("code", "hostess.issue.pmb_android_runtime_exception")
                    .put("severity", "error")
                    .put("message", failureMessage));
        }
        String scoreStatus = "pass";
        for (int index = 0; index < checks.length(); index++) {
            if (!"pass".equals(checks.getJSONObject(index).optString("status"))) {
                scoreStatus = "fail";
            }
        }
        return new JSONObject()
                .put("$schema", "rusty.manifold.validation.scorecard.v1")
                .put("scorecard_id", "scorecard.hostess.projected_motion_breath.android_replay")
                .put("target_id", "hostess.projected_motion_breath.android_replay")
                .put("target_revision", 1)
                .put("status", scoreStatus)
                .put("checks", checks)
                .put("issues", issueObjects);
    }

    private JSONObject pmbControllerPreflightScorecard(
            JSONObject evidence,
            JSONObject preflightReport,
            List<String> errors,
            String failureMessage) throws JSONException {
        JSONObject execution = evidence.optJSONObject("execution");
        JSONObject summary = evidence.optJSONObject("controller_preflight_report_summary");
        JSONArray checks = new JSONArray();
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_controller_preflight_core_loaded",
                PMBRuntime.isAvailable(),
                PMBRuntime.isAvailable() ? "PMB JNI runtime loaded" : PMBRuntime.loadError(),
                "validation.pmb_controller_preflight_failed"));
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_controller_preflight_report_status",
                "pass".equals(preflightReport.optString("status")),
                "projected-motion-breath controller preflight report status was " + preflightReport.optString("status", "missing"),
                "validation.pmb_controller_preflight_failed"));
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_controller_provider_boundary",
                summary != null
                        && summary.optBoolean("provider_boundary_exercised")
                        && summary.optBoolean("controller_provider_route_ready")
                        && "stream.motion.object_pose".equals(summary.optString("output_stream_id")),
                "controller-shaped provider emitted stream.motion.object_pose into PMB",
                "validation.pmb_controller_preflight_failed"));
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_controller_preflight_on_device_flags",
                execution != null
                        && execution.optBoolean("android_execution_performed")
                        && execution.optBoolean("platform_execution_performed")
                        && execution.optBoolean("processor_core_executed"),
                "PMB controller preflight executed through the Android app and PMB core",
                "validation.pmb_controller_preflight_failed"));
        checks.put(pmbScorecardCheck(
                "validation.check.pmb_controller_preflight_non_human_gate",
                execution != null
                        && execution.optBoolean("synthetic_replay")
                        && execution.optBoolean("preflight_fixture_packaged")
                        && !execution.optBoolean("openxr_runtime_used")
                        && !execution.optBoolean("live_sensor_used")
                        && !execution.optBoolean("physical_controller_input_used")
                        && !execution.optBoolean("controller_input_used")
                        && !execution.optBoolean("human_controller_trial_performed")
                        && execution.optBoolean("manual_controller_trial_required"),
                "PMB controller preflight used packaged samples and left the human controller trial pending",
                "validation.pmb_controller_preflight_failed"));
        JSONArray issueObjects = new JSONArray();
        for (String error : errors) {
            issueObjects.put(new JSONObject()
                    .put("code", "hostess.issue.pmb_controller_preflight_failed")
                    .put("severity", "error")
                    .put("message", error));
        }
        if (failureMessage != null) {
            issueObjects.put(new JSONObject()
                    .put("code", "hostess.issue.pmb_controller_preflight_runtime_exception")
                    .put("severity", "error")
                    .put("message", failureMessage));
        }
        String scoreStatus = "pass";
        for (int index = 0; index < checks.length(); index++) {
            if (!"pass".equals(checks.getJSONObject(index).optString("status"))) {
                scoreStatus = "fail";
            }
        }
        return new JSONObject()
                .put("$schema", "rusty.manifold.validation.scorecard.v1")
                .put("scorecard_id", "scorecard.hostess.projected_motion_breath.controller_preflight")
                .put("target_id", "hostess.projected_motion_breath.controller_preflight")
                .put("target_revision", 1)
                .put("status", scoreStatus)
                .put("checks", checks)
                .put("issues", issueObjects);
    }

    private static JSONObject pmbCoreReportSummary(JSONObject coreReport) throws JSONException {
        JSONObject summary = new JSONObject();
        summary.put("schema", coreReport.has("schema") ? coreReport.optString("schema") : JSONObject.NULL);
        summary.put("status", coreReport.optString("status", "missing"));
        for (String field : new String[] {
                "checked_profiles",
                "checked_command_payloads",
                "checked_damaged_command_payloads",
                "checked_source_bindings",
                "checked_damaged_source_bindings",
                "checked_adapter_normalization_cases",
                "checked_damaged_adapter_normalization_cases",
                "checked_cases",
                "checked_damaged_cases" }) {
            summary.put(field, coreReport.optInt(field, 0));
        }
        return summary;
    }

    private static JSONObject pmbControllerPreflightReportSummary(JSONObject report) throws JSONException {
        JSONObject summary = new JSONObject();
        summary.put("schema", report.has("schema") ? report.optString("schema") : JSONObject.NULL);
        summary.put("status", report.optString("status", "missing"));
        summary.put("preflight_id", report.optString("preflight_id", ""));
        summary.put("provider_id", report.optString("provider_id", ""));
        summary.put("provider_kind", report.optString("provider_kind", ""));
        summary.put("binding_id", report.optString("binding_id", ""));
        summary.put("selected_adapter_id", report.optString("selected_adapter_id", ""));
        summary.put("selected_source_kind", report.optString("selected_source_kind", ""));
        summary.put("source_payload_kind", report.optString("source_payload_kind", ""));
        summary.put("input_stream_id", report.optString("input_stream_id", ""));
        summary.put("output_stream_id", report.optString("output_stream_id", ""));
        summary.put("source_id", report.optString("source_id", ""));
        summary.put("frame_id", report.optString("frame_id", ""));
        summary.put("sample_count", report.optInt("sample_count", 0));
        summary.put("normalized_sample_count", report.optInt("normalized_sample_count", 0));
        summary.put("estimate_count", report.optInt("estimate_count", 0));
        summary.put("processor_core_executed", report.optBoolean("processor_core_executed", false));
        summary.put("runtime_execution_performed", report.optBoolean("runtime_execution_performed", false));
        summary.put("provider_boundary_exercised", report.optBoolean("provider_boundary_exercised", false));
        summary.put("controller_provider_route_ready", report.optBoolean("controller_provider_route_ready", false));
        summary.put("headset_controller_shape_used", report.optBoolean("headset_controller_shape_used", false));
        summary.put("physical_controller_input_used", report.optBoolean("physical_controller_input_used", false));
        summary.put("controller_input_used", report.optBoolean("controller_input_used", false));
        summary.put("manual_controller_trial_required", report.optBoolean("manual_controller_trial_required", true));
        summary.put("estimates", report.optJSONArray("estimates") == null ? new JSONArray() : report.optJSONArray("estimates"));
        return summary;
    }

    static List<String> pmbCoreErrors(JSONObject coreReport) {
        List<String> errors = new ArrayList<>();
        JSONArray issues = coreReport.optJSONArray("issues");
        if (issues == null) {
            return errors;
        }
        for (int index = 0; index < issues.length(); index++) {
            Object item = issues.opt(index);
            if (item instanceof JSONObject) {
                JSONObject issue = (JSONObject) item;
                errors.add(issue.optString("message", issue.toString()));
            } else if (item != null) {
                errors.add(item.toString());
            }
        }
        return errors;
    }

    static JSONObject pmbFailureCoreReport(String packageRoot, String message) throws JSONException {
        return new JSONObject()
                .put("schema", "rusty.manifold.projected_motion_breath.core_validation_report.v1")
                .put("package_root", packageRoot)
                .put("status", "fail")
                .put("checked_profiles", 0)
                .put("checked_command_payloads", 0)
                .put("checked_damaged_command_payloads", 0)
                .put("checked_source_bindings", 0)
                .put("checked_damaged_source_bindings", 0)
                .put("checked_adapter_normalization_cases", 0)
                .put("checked_damaged_adapter_normalization_cases", 0)
                .put("checked_cases", 0)
                .put("checked_damaged_cases", 0)
                .put("issues", new JSONArray().put(message == null ? "issue.android_replay_failed" : message));
    }

    static JSONObject pmbFailureControllerPreflightReport(String packageRoot, String message) throws JSONException {
        return new JSONObject()
                .put("schema", "rusty.manifold.projected_motion_breath.controller_preflight_report.v1")
                .put("package_root", packageRoot)
                .put("status", "fail")
                .put("preflight_id", "")
                .put("provider_id", "")
                .put("provider_kind", "")
                .put("binding_id", "")
                .put("selected_adapter_id", "")
                .put("selected_source_kind", "")
                .put("source_payload_kind", "")
                .put("input_stream_id", "")
                .put("output_stream_id", "")
                .put("source_id", "")
                .put("frame_id", "")
                .put("sample_count", 0)
                .put("normalized_sample_count", 0)
                .put("estimate_count", 0)
                .put("processor_core_executed", false)
                .put("runtime_execution_performed", false)
                .put("provider_boundary_exercised", false)
                .put("controller_provider_route_ready", false)
                .put("headset_controller_shape_used", false)
                .put("physical_controller_input_used", false)
                .put("controller_input_used", false)
                .put("manual_controller_trial_required", true)
                .put("estimates", new JSONArray())
                .put("issues", new JSONArray().put(message == null ? "issue.android_controller_preflight_failed" : message));
    }

    static JSONObject pmbFailureLiveRouteReport(String packageRoot, String message) throws JSONException {
        return new JSONObject()
                .put("schema", "rusty.manifold.projected_motion_breath.live_route_report.v1")
                .put("package_root", packageRoot)
                .put("status", "fail")
                .put("route_id", "")
                .put("input_stream_ids", new JSONArray())
                .put("normalized_stream_ids", new JSONArray())
                .put("output_stream_ids", new JSONArray())
                .put("processor_core_executed", false)
                .put("runtime_execution_performed", false)
                .put("external_transport_used", false)
                .put("live_sensor_used", false)
                .put("headset_execution_performed", false)
                .put("plan_only", true)
                .put("source_routes", new JSONArray())
                .put("breath_samples", new JSONArray())
                .put("feedback_samples", new JSONArray())
                .put("receiver_subscription", new JSONObject()
                        .put("command", "")
                        .put("stream", "")
                        .put("receiver_id", ""))
                .put("receiver_receipts", new JSONArray())
                .put("issues", new JSONArray().put(message == null ? "issue.android_simulated_live_failed" : message));
    }

    static JSONObject pmbFailureBrokerPublishReport(String brokerHost, int brokerPort, String message) throws JSONException {
        return new JSONObject()
                .put("schema", "rusty.hostess.projected_motion_breath.quest_broker_publish_report.v1")
                .put("status", "fail")
                .put("broker_host", brokerHost)
                .put("broker_port", brokerPort)
                .put("broker_connected", false)
                .put("broker_transport_used", false)
                .put("publish_limit", 0)
                .put("receipt_listen_ms", 0)
                .put("selected_source_preference", "auto")
                .put("selected_source_effective", "unknown")
                .put("breath_requested_count", 0)
                .put("feedback_requested_count", 0)
                .put("breath_published_count", 0)
                .put("selected_breath_published_count", 0)
                .put("selection_state_published_count", 0)
                .put("feedback_published_count", 0)
                .put("feedback_receipt_count", 0)
                .put("receipt_stream_id", PmbBrokerBridge.STREAM_BREATH_FEEDBACK_RECEIPT)
                .put("breath_results", new JSONArray())
                .put("feedback_results", new JSONArray())
                .put("command_replies", new JSONArray())
                .put("receipt_events", new JSONArray())
                .put("errors", new JSONArray().put(message == null ? "issue.android_broker_publish_failed" : message));
    }

    private static JSONObject pmbScorecardCheck(String checkId, boolean passed, String evidence) throws JSONException {
        return pmbScorecardCheck(checkId, passed, evidence, "validation.pmb_android_replay_failed");
    }

    private static JSONObject pmbScorecardCheck(String checkId, boolean passed, String evidence, String issueCode) throws JSONException {
        return new JSONObject()
                .put("check_id", checkId)
                .put("status", passed ? "pass" : "fail")
                .put("evidence", evidence)
                .put("issue_codes", passed ? new JSONArray() : new JSONArray().put(issueCode));
    }
}
