package io.github.mesmerprism.rustyhostess.t;

import android.content.Context;
import android.content.Intent;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.FileInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

final class PmbPhysicalLiveRunner {
    private static final String PMB_PACKAGE_ID = "package.projected_motion_breath";
    private static final String PMB_ASSET_ROOT = "manifold/packages/projected-motion-breath";
    // PMB fixed-controller state mirrors the legacy Unity 24/180-sample spans
    // against the current 72 Hz headset profile, then transports them as seconds.
    private static final double CONTROLLER_STATE_SAMPLE_RATE_HZ = 72.0d;
    private static final double CONTROLLER_STATE_SHORT_WINDOW_SAMPLES = 24.0d;
    private static final double CONTROLLER_STATE_LONG_WINDOW_SAMPLES = 180.0d;
    private static final double DEFAULT_CONTROLLER_STATE_SHORT_WINDOW_S =
            CONTROLLER_STATE_SHORT_WINDOW_SAMPLES / CONTROLLER_STATE_SAMPLE_RATE_HZ;
    private static final double DEFAULT_CONTROLLER_STATE_LONG_WINDOW_S =
            CONTROLLER_STATE_LONG_WINDOW_SAMPLES / CONTROLLER_STATE_SAMPLE_RATE_HZ;
    private static final double DEFAULT_CONTROLLER_STATE_INHALE_THRESHOLD = 0.001d;
    private static final double DEFAULT_CONTROLLER_STATE_EXHALE_THRESHOLD = -0.00057d;
    private static final double DEFAULT_CONTROLLER_STATE_ROTATION_GUARD_DEGREES = 0.5d;
    private static final double DEFAULT_CONTROLLER_STATE_MOVING_AVERAGE_GUARD = 0.025d;

    private PmbPhysicalLiveRunner() {
    }

    static String run(Context context, Intent intent) {
        Instant startedAt = Instant.now();
        String hostProfile = stringExtra(intent, "host_profile", "headset");
        String brokerHost = stringExtra(intent, "broker_host", "127.0.0.1");
        int brokerPort = intExtra(intent, "broker_port", 8765);
        String deviceAddress = stringExtra(intent, "device_address", "");
        int durationMs = intExtra(intent, "duration_ms", 30000);
        int accRateHz = intExtra(intent, "acc_rate_hz", 200);
        int scanTimeoutMs = intExtra(intent, "scan_timeout_ms", 30000);
        int controllerWaitMs = intExtra(intent, "controller_wait_ms", 15000);
        int feedbackLimit = intExtra(intent, "feedback_publish_limit", 24);
        String breathSelectedSource = stringExtra(intent, "breath_selected_source", "auto");
        String controllerStateMode = normalizePmbControllerStateMode(
                stringExtra(intent, "pmb_controller_state_mode", "projected-volume-delta"));
        double controllerStateShortWindowS = doubleExtra(
                intent,
                "pmb_controller_state_short_window_s",
                DEFAULT_CONTROLLER_STATE_SHORT_WINDOW_S);
        double controllerStateLongWindowS = doubleExtra(
                intent,
                "pmb_controller_state_long_window_s",
                DEFAULT_CONTROLLER_STATE_LONG_WINDOW_S);
        double controllerStateInhaleThreshold = doubleExtra(
                intent,
                "pmb_controller_state_inhale_threshold",
                DEFAULT_CONTROLLER_STATE_INHALE_THRESHOLD);
        double controllerStateExhaleThreshold = doubleExtra(
                intent,
                "pmb_controller_state_exhale_threshold",
                DEFAULT_CONTROLLER_STATE_EXHALE_THRESHOLD);
        double controllerStateRotationGuardDegrees = doubleExtra(
                intent,
                "pmb_controller_state_rotation_guard_degrees",
                DEFAULT_CONTROLLER_STATE_ROTATION_GUARD_DEGREES);
        double controllerStateMovingAverageGuard = doubleExtra(
                intent,
                "pmb_controller_state_moving_average_guard",
                DEFAULT_CONTROLLER_STATE_MOVING_AVERAGE_GUARD);
        int receiptListenMs = intExtra(intent, "receipt_listen_ms", 6000);
        int livePublishIntervalMs = intExtra(intent, "live_publish_interval_ms", 1000);
        File evidenceRoot = new File(context.getExternalFilesDir(null), "hostess-t/evidence/pmb-physical-live");
        File packageRoot = new File(context.getExternalFilesDir(null), "hostess-t/packages/projected-motion-breath");
        String status = "fail";
        try {
            resetDirectory(packageRoot);
            copyPmbPackageAssets(context, packageRoot);
            applyPmbControllerStateMode(packageRoot, controllerStateMode);
            applyPmbControllerStateTuning(
                    packageRoot,
                    controllerStateMode,
                    controllerStateShortWindowS,
                    controllerStateLongWindowS,
                    controllerStateInhaleThreshold,
                    controllerStateExhaleThreshold,
                    controllerStateRotationGuardDegrees,
                    controllerStateMovingAverageGuard);
            if (!evidenceRoot.exists() && !evidenceRoot.mkdirs()) {
                throw new IOException("could not create PMB physical live evidence folder");
            }
            File eventsJsonl = new File(evidenceRoot, "latest.transport-events.jsonl");
            PmbBrokerBridge.PhysicalLiveResult liveResult = PmbBrokerBridge.capturePhysicalInputsAndPublishLive(
                    brokerHost,
                    brokerPort,
                    deviceAddress,
                    accRateHz,
                    scanTimeoutMs,
                    durationMs,
                    controllerWaitMs,
                    eventsJsonl,
                    packageRoot.getAbsolutePath(),
                    feedbackLimit,
                    receiptListenMs,
                    breathSelectedSource,
                    livePublishIntervalMs);
            JSONObject captureReport = liveResult.captureResult.toJson();
            JSONObject brokerReport = liveResult.brokerResult.toJson();
            List<String> errors = jsonArrayStrings(captureReport.optJSONArray("errors"));
            JSONObject routeReport = "pass".equals(captureReport.optString("status"))
                    ? PMBRuntime.runLiveRouteFromEvents(
                            packageRoot.getAbsolutePath(),
                            eventsJsonl.getAbsolutePath(),
                            breathSelectedSource)
                    : pmbFailureLiveRouteReport(packageRoot.getAbsolutePath(), "physical input capture failed");
            errors.addAll(pmbCoreErrors(routeReport));
            if (!"pass".equals(brokerReport.optString("status"))) {
                errors.addAll(jsonArrayStrings(brokerReport.optJSONArray("errors")));
            }
            Instant endedAt = Instant.now();
            status = errors.isEmpty()
                    && "pass".equals(captureReport.optString("status"))
                    && "pass".equals(routeReport.optString("status"))
                    && "pass".equals(brokerReport.optString("status"))
                    ? "pass"
                    : "fail";
            writeText(new File(evidenceRoot, "latest.input-capture-report.json"), captureReport.toString(2));
            writeText(new File(evidenceRoot, "latest.live-route-report.json"), routeReport.toString(2));
            writeText(new File(evidenceRoot, "latest.broker-publish-report.json"), brokerReport.toString(2));
            JSONObject evidence = PmbPhysicalLiveEvidence.build(
                    hostProfile,
                    startedAt,
                    endedAt,
                    pmbPackageSnapshot(context),
                    captureReport,
                    routeReport,
                    brokerReport,
                    errors,
                    null);
            writeText(new File(evidenceRoot, "latest.json"), evidence.toString(2));
        } catch (IOException | JSONException | RuntimeException ex) {
            Instant endedAt = Instant.now();
            try {
                if (!evidenceRoot.exists()) {
                    evidenceRoot.mkdirs();
                }
                JSONObject captureReport = pmbFailurePhysicalInputCaptureReport(
                        brokerHost,
                        brokerPort,
                        deviceAddress,
                        accRateHz,
                        scanTimeoutMs,
                        durationMs,
                        controllerWaitMs,
                        ex.getMessage());
                JSONObject routeReport = pmbFailureLiveRouteReport(packageRoot.getAbsolutePath(), ex.getMessage());
                JSONObject brokerReport = pmbFailureBrokerPublishReport(brokerHost, brokerPort, ex.getMessage());
                writeText(new File(evidenceRoot, "latest.input-capture-report.json"), captureReport.toString(2));
                writeText(new File(evidenceRoot, "latest.live-route-report.json"), routeReport.toString(2));
                writeText(new File(evidenceRoot, "latest.broker-publish-report.json"), brokerReport.toString(2));
                List<String> errors = new ArrayList<>();
                errors.add(ex.getMessage() == null ? ex.toString() : ex.getMessage());
                JSONObject evidence = PmbPhysicalLiveEvidence.build(
                        hostProfile,
                        startedAt,
                        endedAt,
                        pmbPackageSnapshot(context),
                        captureReport,
                        routeReport,
                        brokerReport,
                        errors,
                        ex.toString());
                writeText(new File(evidenceRoot, "latest.json"), evidence.toString(2));
            } catch (IOException | JSONException ignored) {
                // App-private evidence is the host-visible completion signal.
            }
            status = "fail";
        }
        return status;
    }

    static JSONObject pmbPackageSnapshot(Context context) throws JSONException {
        return new JSONObject()
                .put("package_id", PMB_PACKAGE_ID)
                .put("package_manifest_sha256", assetSha256(context, PMB_ASSET_ROOT + "/manifests/package.manifold.json"))
                .put("stream_manifest_sha256", pmbManifestHashes(context, "streams"))
                .put("module_manifest_sha256", pmbManifestHashes(context, "modules"))
                .put("command_manifest_sha256", pmbManifestHashes(context, "commands"));
    }

    private static JSONObject pmbManifestHashes(Context context, String manifestFolder) throws JSONException {
        JSONObject hashes = new JSONObject();
        String folder = PMB_ASSET_ROOT + "/manifests/" + manifestFolder;
        try {
            String prefix = "manifests/" + manifestFolder + "/";
            for (String relative : pmbPackageAssetFiles(context)) {
                if (relative.startsWith(prefix) && relative.endsWith(".json")) {
                    String file = relative.substring(prefix.length());
                    hashes.put(file.substring(0, file.length() - 5), assetSha256(context, PMB_ASSET_ROOT + "/" + relative));
                }
            }
            if (hashes.length() > 0) {
                return hashes;
            }
            String[] files = listAssets(context, folder);
            if (files == null) {
                return hashes;
            }
            Arrays.sort(files);
            for (String file : files) {
                if (file.endsWith(".json")) {
                    hashes.put(file.substring(0, file.length() - 5), assetSha256(context, folder + "/" + file));
                }
            }
        } catch (IOException ignored) {
        }
        return hashes;
    }

    private static void copyPmbPackageAssets(Context context, File targetRoot) throws IOException {
        for (String relative : pmbPackageAssetFiles(context)) {
            copyAssetFile(context, PMB_ASSET_ROOT + "/" + relative, new File(targetRoot, relative.replace('/', File.separatorChar)));
        }
    }

    private static void applyPmbControllerStateMode(File packageRoot, String mode) throws IOException, JSONException {
        if (!"fixed-controller-orientation".equals(mode)) {
            return;
        }
        File bindingPath = new File(packageRoot, "fixtures/valid/source-binding-headset-controller-pose.json");
        JSONObject binding = new JSONObject(readText(bindingPath));
        binding.put("profile_id", "profile.projected_motion_breath.headset_controller_fixed_orientation_state");
        binding.put("profile_path", "fixtures/valid/profile-headset-controller-fixed-orientation-state.json");
        writeText(bindingPath, binding.toString(2));
    }

    private static void applyPmbControllerStateTuning(
            File packageRoot,
            String mode,
            double shortWindowS,
            double longWindowS,
            double inhaleThreshold,
            double exhaleThreshold,
            double rotationGuardDegrees,
            double movingAverageGuard) throws IOException, JSONException {
        if (!"fixed-controller-orientation".equals(mode)) {
            return;
        }
        File profilePath = new File(packageRoot, "fixtures/valid/profile-headset-controller-fixed-orientation-state.json");
        JSONObject profile = new JSONObject(readText(profilePath));
        JSONObject controllerState = profile.optJSONObject("controller_state");
        if (controllerState == null) {
            controllerState = new JSONObject();
            profile.put("controller_state", controllerState);
        }
        controllerState.put(
                "short_window_s",
                positiveFiniteOr(shortWindowS, DEFAULT_CONTROLLER_STATE_SHORT_WINDOW_S));
        controllerState.put(
                "long_window_s",
                positiveFiniteOr(longWindowS, DEFAULT_CONTROLLER_STATE_LONG_WINDOW_S));
        controllerState.put(
                "inhale_threshold",
                finiteOr(inhaleThreshold, DEFAULT_CONTROLLER_STATE_INHALE_THRESHOLD));
        controllerState.put(
                "exhale_threshold",
                finiteOr(exhaleThreshold, DEFAULT_CONTROLLER_STATE_EXHALE_THRESHOLD));
        controllerState.put(
                "rotation_guard_degrees",
                positiveFiniteOr(
                        rotationGuardDegrees,
                        DEFAULT_CONTROLLER_STATE_ROTATION_GUARD_DEGREES));
        controllerState.put(
                "moving_average_guard",
                positiveFiniteOr(
                        movingAverageGuard,
                        DEFAULT_CONTROLLER_STATE_MOVING_AVERAGE_GUARD));
        writeText(profilePath, profile.toString(2));
    }

    private static String normalizePmbControllerStateMode(String value) {
        String normalized = value == null ? "" : value.trim().toLowerCase(Locale.US).replace('_', '-');
        if ("fixed-controller-orientation".equals(normalized)
                || "fixed-orientation".equals(normalized)
                || "fixed-orientation-state".equals(normalized)) {
            return "fixed-controller-orientation";
        }
        return "projected-volume-delta";
    }

    private static List<String> pmbPackageAssetFiles(Context context) throws IOException {
        List<String> files = new ArrayList<>();
        String manifest = readAssetText(context, PMB_ASSET_ROOT + "/package-files.txt");
        for (String rawFile : manifest.split("\\r?\\n")) {
            String relative = rawFile.trim();
            if (!relative.isEmpty() && !relative.contains("..")) {
                files.add(relative);
            }
        }
        return files;
    }

    private static JSONObject pmbFailureLiveRouteReport(String packageRoot, String message) throws JSONException {
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
                .put("state_samples", new JSONArray())
                .put("state_value_samples", new JSONArray())
                .put("feedback_samples", new JSONArray())
                .put("receiver_subscription", new JSONObject()
                        .put("command", "")
                        .put("stream", "")
                        .put("receiver_id", ""))
                .put("receiver_receipts", new JSONArray())
                .put("issues", new JSONArray().put(message == null ? "issue.android_physical_live_failed" : message));
    }

    private static JSONObject pmbFailurePhysicalInputCaptureReport(
            String brokerHost,
            int brokerPort,
            String deviceAddress,
            int accRateHz,
            int scanTimeoutMs,
            int durationMs,
            int controllerWaitMs,
            String message) throws JSONException {
        return new JSONObject()
                .put("schema", "rusty.hostess.projected_motion_breath.quest_physical_input_capture_report.v1")
                .put("status", "fail")
                .put("broker_host", brokerHost)
                .put("broker_port", brokerPort)
                .put("broker_connected", false)
                .put("broker_transport_used", false)
                .put("events_jsonl", "")
                .put("device_address_supplied", deviceAddress != null && !deviceAddress.isEmpty())
                .put("acc_rate_hz", accRateHz)
                .put("scan_timeout_ms", scanTimeoutMs)
                .put("duration_ms", durationMs)
                .put("controller_wait_ms", controllerWaitMs)
                .put("polar_start_status", "fail")
                .put("polar_stop_status", "not_started")
                .put("polar_event_count", 0)
                .put("object_pose_event_count", 0)
                .put("active_object_pose_count", 0)
                .put("tracked_object_pose_count", 0)
                .put("connected_object_pose_count", 0)
                .put("active_tracked_connected_object_pose_count", 0)
                .put("physical_polar_ble_used", false)
                .put("physical_controller_input_used", false)
                .put("controller_input_used", false)
                .put("simulated_polar_provider_used", false)
                .put("simulated_controller_provider_used", false)
                .put("command_replies", new JSONArray())
                .put("observed_events", new JSONArray())
                .put("errors", new JSONArray().put(message == null ? "issue.android_physical_live_capture_failed" : message));
    }

    private static JSONObject pmbFailureBrokerPublishReport(String brokerHost, int brokerPort, String message) throws JSONException {
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
                .put("publish_mode", "failed")
                .put("live_publish_during_capture", false)
                .put("incremental_processor_used", false)
                .put("snapshot_replay_used", false)
                .put("live_publish_interval_ms", 0)
                .put("input_event_processed_count", 0)
                .put("live_processor_update_count", 0)
                .put("live_processor_output_update_count", 0)
                .put("live_publish_attempt_count", 0)
                .put("live_route_pass_count", 0)
                .put("live_route_fail_count", 0)
                .put("first_selected_publish_elapsed_ms", -1)
                .put("last_selected_publish_elapsed_ms", -1)
                .put("last_route_status", "missing")
                .put("breath_requested_count", 0)
                .put("state_requested_count", 0)
                .put("state_value_requested_count", 0)
                .put("feedback_requested_count", 0)
                .put("breath_published_count", 0)
                .put("selected_breath_published_count", 0)
                .put("selection_state_published_count", 0)
                .put("state_published_count", 0)
                .put("state_value_published_count", 0)
                .put("feedback_published_count", 0)
                .put("feedback_receipt_count", 0)
                .put("receipt_stream_id", PmbBrokerBridge.STREAM_BREATH_FEEDBACK_RECEIPT)
                .put("breath_results", new JSONArray())
                .put("state_results", new JSONArray())
                .put("state_value_results", new JSONArray())
                .put("feedback_results", new JSONArray())
                .put("command_replies", new JSONArray())
                .put("receipt_events", new JSONArray())
                .put("errors", new JSONArray().put(message == null ? "issue.android_broker_publish_failed" : message));
    }

    private static List<String> pmbCoreErrors(JSONObject report) {
        List<String> errors = new ArrayList<>();
        if (report == null) {
            errors.add("pmb_report_missing");
            return errors;
        }
        JSONArray issues = report.optJSONArray("issues");
        if (issues == null || issues.length() == 0) {
            return errors;
        }
        for (int index = 0; index < issues.length(); index++) {
            errors.add(issues.optString(index));
        }
        return errors;
    }

    private static List<String> jsonArrayStrings(JSONArray values) {
        List<String> strings = new ArrayList<>();
        if (values == null) {
            return strings;
        }
        for (int index = 0; index < values.length(); index++) {
            strings.add(values.optString(index));
        }
        return strings;
    }

    private static String stringExtra(Intent intent, String name, String fallback) {
        String value = intent.getStringExtra(name);
        if (value == null || value.trim().isEmpty()) {
            return fallback;
        }
        return value.trim();
    }

    private static int intExtra(Intent intent, String name, int fallback) {
        if (!intent.hasExtra(name) || intent.getExtras() == null) {
            return fallback;
        }
        try {
            return Integer.parseInt(String.valueOf(intent.getExtras().get(name)).trim());
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static double doubleExtra(Intent intent, String name, double fallback) {
        if (!intent.hasExtra(name) || intent.getExtras() == null) {
            return fallback;
        }
        try {
            return Double.parseDouble(String.valueOf(intent.getExtras().get(name)).trim());
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static double finiteOr(double value, double fallback) {
        return Double.isFinite(value) ? value : fallback;
    }

    private static double positiveFiniteOr(double value, double fallback) {
        return Double.isFinite(value) && value > 0.0d ? value : fallback;
    }

    private static void resetDirectory(File root) throws IOException {
        deleteRecursively(root);
        if (!root.exists() && !root.mkdirs()) {
            throw new IOException("could not create folder: " + root.getAbsolutePath());
        }
    }

    private static void deleteRecursively(File path) throws IOException {
        if (!path.exists()) {
            return;
        }
        File[] children = path.listFiles();
        if (children != null) {
            for (File child : children) {
                deleteRecursively(child);
            }
        }
        if (!path.delete()) {
            throw new IOException("could not delete: " + path.getAbsolutePath());
        }
    }

    private static void copyAssetFile(Context context, String assetPath, File target) throws IOException {
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("could not create folder: " + parent.getAbsolutePath());
        }
        try (InputStream input = openAsset(context, assetPath); FileOutputStream output = new FileOutputStream(target)) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) >= 0) {
                output.write(buffer, 0, read);
            }
        }
    }

    private static void writeText(File path, String text) throws IOException {
        try (FileOutputStream stream = new FileOutputStream(path)) {
            stream.write(text.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static String readText(File path) throws IOException {
        try (FileInputStream input = new FileInputStream(path)) {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            byte[] bytes = new byte[8192];
            int read;
            while ((read = input.read(bytes)) >= 0) {
                buffer.write(bytes, 0, read);
            }
            return buffer.toString(StandardCharsets.UTF_8.name());
        }
    }

    private static String readAssetText(Context context, String assetPath) throws IOException {
        try (InputStream input = openAsset(context, assetPath)) {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            byte[] bytes = new byte[8192];
            int read;
            while ((read = input.read(bytes)) >= 0) {
                buffer.write(bytes, 0, read);
            }
            return buffer.toString(StandardCharsets.UTF_8.name());
        }
    }

    private static String[] listAssets(Context context, String path) throws IOException {
        String[] children = context.getAssets().list(path);
        if (children != null && children.length > 0) {
            return children;
        }
        String fallback = path.replace('/', '\\');
        if (!fallback.equals(path)) {
            String[] fallbackChildren = context.getAssets().list(fallback);
            if (fallbackChildren != null && fallbackChildren.length > 0) {
                return fallbackChildren;
            }
        }
        return children;
    }

    private static String assetSha256(Context context, String path) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream stream = openAsset(context, path)) {
                byte[] buffer = new byte[8192];
                int read;
                while ((read = stream.read(buffer)) >= 0) {
                    digest.update(buffer, 0, read);
                }
            }
            return hex(digest.digest());
        } catch (IOException | NoSuchAlgorithmException ex) {
            return "unavailable";
        }
    }

    private static InputStream openAsset(Context context, String path) throws IOException {
        try {
            return context.getAssets().open(path);
        } catch (IOException first) {
            return context.getAssets().open(path.replace('/', '\\'));
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder builder = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) {
            builder.append(String.format(Locale.US, "%02x", value & 0xff));
        }
        return builder.toString();
    }
}
