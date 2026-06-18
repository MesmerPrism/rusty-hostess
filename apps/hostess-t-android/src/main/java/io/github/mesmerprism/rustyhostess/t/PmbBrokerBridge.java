package io.github.mesmerprism.rustyhostess.t;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedWriter;
import java.io.ByteArrayOutputStream;
import java.io.Closeable;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

final class PmbBrokerBridge {
    static final String MANIFOLD_COMMAND_SCHEMA = "rusty.manifold.command.envelope.v1";
    static final String MANIFOLD_BROKER_EVENTS_PATH = "/manifold/v1/events";
    static final String EXTERNAL_STREAM_POLAR_ACC = "bio:polar_acc";
    static final String STREAM_OBJECT_POSE = "stream.motion.object_pose";
    static final String STREAM_BREATH_VOLUME = "stream.breath.volume";
    static final String STREAM_BREATH_VOLUME_SELECTED = "stream.breath.volume.selected";
    static final String STREAM_BREATH_VOLUME_POLAR = "stream.breath.volume.polar";
    static final String STREAM_BREATH_VOLUME_CONTROLLER = "stream.breath.volume.controller";
    static final String STREAM_BREATH_SELECTION_STATE = "stream.breath.selection_state";
    static final String STREAM_BREATH_STATE = "stream.breath.state";
    static final String STREAM_BREATH_STATE_VALUE = "stream.breath.state.value";
    static final String STREAM_BREATH_FEEDBACK_STATE = "stream.breath.feedback_state";
    static final String STREAM_BREATH_FEEDBACK_RECEIPT = "stream.breath.feedback_receipt";

    private PmbBrokerBridge() {
    }

    static PhysicalCaptureResult capturePhysicalInputs(
            String host,
            int port,
            String deviceAddress,
            int accRateHz,
            int scanTimeoutMs,
            int durationMs,
            int controllerWaitMs,
            File eventsJsonl) throws IOException, JSONException {
        PhysicalCaptureResult result = new PhysicalCaptureResult(
                host,
                port,
                deviceAddress,
                accRateHz,
                scanTimeoutMs,
                durationMs,
                controllerWaitMs,
                eventsJsonl.getAbsolutePath());
        File parent = eventsJsonl.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("could not create PMB physical live event folder");
        }

        try (BrokerWebSocketClient client = BrokerWebSocketClient.open(host, port, 2500);
                BufferedWriter writer = new BufferedWriter(new FileWriter(eventsJsonl, false))) {
            result.brokerConnected = true;
            client.sendJson(new JSONObject()
                    .put("type", "hello")
                    .put("client_id", "app.rusty_hostess_t.quest.pmb_physical_live")
                    .put("app_package", "io.github.mesmerprism.rustyhostess.t")
                    .put("role", "quest_pmb_physical_live_processor"), 1);
            client.readJson(500);
            physicalCommandAndWait(client, result, "subscribe", new JSONObject()
                    .put("stream", EXTERNAL_STREAM_POLAR_ACC)
                    .put("receiver", "app.rusty_hostess_t.quest.pmb_physical_live"), 2);
            physicalCommandAndWait(client, result, "subscribe", new JSONObject()
                    .put("stream", STREAM_BREATH_FEEDBACK_RECEIPT)
                    .put("receiver", "app.rusty_hostess_t.quest.pmb_physical_live"), 3);
            physicalCommandAndWait(client, result, "subscribe", new JSONObject()
                    .put("stream", STREAM_OBJECT_POSE)
                    .put("receiver", "app.rusty_hostess_t.quest.pmb_physical_live"), 4);
            result.polarStartStatus = physicalCommandAndWait(client, result, "polar_pmd.start", new JSONObject()
                    .put("device_address", deviceAddress == null ? "" : deviceAddress)
                    .put("scan_timeout_ms", scanTimeoutMs)
                    .put("pmd_stream", "acc")
                    .put("acc_sample_rate_hz", accRateHz)
                    .put("high_connection_priority", true), 5);

            long deadline = System.currentTimeMillis() + Math.max(0, durationMs);
            while (System.currentTimeMillis() < deadline) {
                int timeout = (int) Math.max(50, Math.min(250, deadline - System.currentTimeMillis()));
                JSONObject message = client.readJson(timeout);
                if (message == null) {
                    continue;
                }
                result.acceptCaptureMessage(message, writer);
            }
            writer.flush();
            result.polarStopStatus = physicalCommandAndWait(client, result, "polar_pmd.stop", new JSONObject(), 6);
        } catch (IOException | JSONException | RuntimeException ex) {
            result.errors.put(ex.getMessage() == null ? ex.toString() : ex.getMessage());
            throw ex;
        }

        result.status = result.polarEventCount > 0
                && result.activeTrackedConnectedObjectPoseCount > 0
                && result.errors.length() == 0
                ? "pass"
                : "fail";
        if (result.polarEventCount <= 0) {
            result.errors.put("issue.polar_acc_events_missing");
        }
        if (result.activeTrackedConnectedObjectPoseCount <= 0) {
            result.errors.put("issue.controller_pose_active_tracked_connected_missing");
        }
        return result;
    }

    static Result publishRoute(JSONObject routeReport, String host, int port, int limit, int receiptListenMs)
            throws IOException, JSONException {
        return publishRoute(routeReport, host, port, limit, receiptListenMs, "auto");
    }

    static PhysicalLiveResult capturePhysicalInputsAndPublishLive(
            String host,
            int port,
            String deviceAddress,
            int accRateHz,
            int scanTimeoutMs,
            int durationMs,
            int controllerWaitMs,
            File eventsJsonl,
            String packageRoot,
            int feedbackLimit,
            int receiptListenMs,
            String selectedSourcePreference,
            int livePublishIntervalMs) throws IOException, JSONException {
        PhysicalCaptureResult captureResult = new PhysicalCaptureResult(
                host,
                port,
                deviceAddress,
                accRateHz,
                scanTimeoutMs,
                durationMs,
                controllerWaitMs,
                eventsJsonl.getAbsolutePath());
        Result brokerResult = new Result(host, port, feedbackLimit, receiptListenMs);
        brokerResult.selectedSourcePreference = normalizeSelectedSourcePreference(selectedSourcePreference);
        captureResult.configureSourcePreference(brokerResult.selectedSourcePreference);
        brokerResult.publishMode = "event_driven_live_processor";
        brokerResult.livePublishDuringCapture = true;
        brokerResult.incrementalProcessorUsed = true;
        brokerResult.snapshotReplayUsed = false;
        brokerResult.livePublishIntervalMs = 0;
        brokerResult.clientId = "app.rusty_hostess_t.quest.pmb_physical_live";
        brokerResult.requestIdPrefix = "quest-pmb-physical-live";
        brokerResult.processorId = "processor.projected_motion_breath.quest_live_transport";
        LivePublishState publishState = new LivePublishState();
        File parent = eventsJsonl.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("could not create PMB physical live event folder");
        }

        try (BrokerWebSocketClient captureClient = BrokerWebSocketClient.open(host, port, 2500);
                BrokerWebSocketClient publishClient = BrokerWebSocketClient.open(host, port, 2500);
                BufferedWriter writer = new BufferedWriter(new FileWriter(eventsJsonl, false))) {
            captureResult.brokerConnected = true;
            brokerResult.brokerConnected = true;
            captureClient.sendJson(new JSONObject()
                    .put("type", "hello")
                    .put("client_id", "app.rusty_hostess_t.quest.pmb_physical_live")
                    .put("app_package", "io.github.mesmerprism.rustyhostess.t")
                    .put("role", "quest_pmb_physical_live_processor"), 1);
            captureClient.readJson(500);
            physicalCommandAndWait(captureClient, captureResult, "subscribe", new JSONObject()
                    .put("stream", EXTERNAL_STREAM_POLAR_ACC)
                    .put("receiver", "app.rusty_hostess_t.quest.pmb_physical_live"), 2);
            physicalCommandAndWait(captureClient, captureResult, "subscribe", new JSONObject()
                    .put("stream", STREAM_BREATH_FEEDBACK_RECEIPT)
                    .put("receiver", "app.rusty_hostess_t.quest.pmb_physical_live"), 3);
            physicalCommandAndWait(captureClient, captureResult, "subscribe", new JSONObject()
                    .put("stream", STREAM_OBJECT_POSE)
                    .put("receiver", "app.rusty_hostess_t.quest.pmb_physical_live"), 4);

            publishClient.sendJson(new JSONObject()
                    .put("type", "hello")
                    .put("client_id", brokerResult.clientId)
                    .put("app_package", "io.github.mesmerprism.rustyhostess.t")
                    .put("role", "quest_pmb_physical_live_publisher"), 5);
            publishClient.readJson(500, brokerResult);
            sendCommandAndWait(publishClient, brokerResult, "subscribe", new JSONObject()
                    .put("stream", STREAM_BREATH_FEEDBACK_RECEIPT)
                    .put("receiver", brokerResult.clientId), publishState.nextCommandSequence());
            long processorHandle = PMBRuntime.openLiveTransportProcessor(packageRoot);

            boolean polarRequested = captureResult.polarProviderRequested();
            if (polarRequested) {
                captureResult.polarStartStatus = physicalCommandAndWait(captureClient, captureResult, "polar_pmd.start", new JSONObject()
                        .put("device_address", deviceAddress == null ? "" : deviceAddress)
                        .put("scan_timeout_ms", scanTimeoutMs)
                        .put("pmd_stream", "acc")
                        .put("acc_sample_rate_hz", accRateHz)
                        .put("high_connection_priority", true), 6);
            } else {
                captureResult.polarStartStatus = "not_requested";
            }

            long startedMs = System.currentTimeMillis();
            boolean runUntilStopped = durationMs <= 0;
            long deadline = runUntilStopped ? Long.MAX_VALUE : startedMs + Math.max(0, durationMs);
            while ((runUntilStopped || System.currentTimeMillis() < deadline)
                    && !Thread.currentThread().isInterrupted()) {
                long now = System.currentTimeMillis();
                int timeout = runUntilStopped
                        ? 250
                        : (int) Math.max(50, Math.min(250, deadline - now));
                JSONObject message = captureClient.readJson(timeout);
                if (message != null && captureResult.acceptCaptureMessage(message, writer)) {
                    brokerResult.inputEventProcessedCount += 1;
                    JSONObject update = PMBRuntime.pushLiveTransportEvent(
                            processorHandle,
                            message.toString(),
                            brokerResult.selectedSourcePreference);
                    publishLiveTransportUpdate(
                            publishClient,
                            brokerResult,
                            update,
                            publishState,
                            startedMs);
                    drainFeedbackReceipts(publishClient, brokerResult, 50);
                }
            }
            writer.flush();
            JSONObject closeUpdate = PMBRuntime.closeLiveTransportProcessor(processorHandle);
            brokerResult.closeReport = closeUpdate;
            if (polarRequested) {
                captureResult.polarStopStatus = physicalCommandAndWait(captureClient, captureResult, "polar_pmd.stop", new JSONObject(), 7);
            } else {
                captureResult.polarStopStatus = "not_requested";
            }

            long receiptDeadline = System.currentTimeMillis() + Math.max(0, receiptListenMs);
            while (System.currentTimeMillis() < receiptDeadline
                    && brokerResult.feedbackReceiptCount < brokerResult.selectedBreathPublishedCount) {
                int timeout = (int) Math.max(50, Math.min(250, receiptDeadline - System.currentTimeMillis()));
                publishClient.readJson(timeout, brokerResult);
            }
        } catch (IOException | JSONException | RuntimeException ex) {
            captureResult.errors.put(ex.getMessage() == null ? ex.toString() : ex.getMessage());
            brokerResult.errors.put(ex.getMessage() == null ? ex.toString() : ex.getMessage());
            throw ex;
        }

        captureResult.status = captureResult.requiredInputsCaptured()
                && captureResult.errors.length() == 0
                ? "pass"
                : "fail";
        if (captureResult.polarRequired && captureResult.polarEventCount <= 0) {
            captureResult.errors.put("issue.polar_acc_events_missing");
        }
        if (captureResult.controllerRequired && captureResult.activeTrackedConnectedObjectPoseCount <= 0) {
            captureResult.errors.put("issue.controller_pose_active_tracked_connected_missing");
        }
        if (!captureResult.polarRequired
                && !captureResult.controllerRequired
                && captureResult.polarEventCount <= 0
                && captureResult.activeTrackedConnectedObjectPoseCount <= 0) {
            captureResult.errors.put("issue.physical_pmb_input_events_missing");
        }
        brokerResult.status = brokerResult.liveRoutePassCount > 0
                && brokerResult.firstSelectedPublishElapsedMs >= 0
                && brokerResult.selectedBreathPublishedCount > 0
                && brokerResult.statePublishedCount > 0
                && brokerResult.stateValuePublishedCount > 0
                && brokerResult.feedbackPublishedCount > 0
                && brokerResult.feedbackReceiptCount == brokerResult.selectedBreathPublishedCount
                ? "pass"
                : "fail";
        if (brokerResult.liveRoutePassCount <= 0) {
            brokerResult.errors.put("issue.pmb_live_processor_did_not_emit_during_capture");
        }
        if (brokerResult.firstSelectedPublishElapsedMs < 0 || brokerResult.selectedBreathPublishedCount <= 0) {
            brokerResult.errors.put("issue.selected_breath_volume_stream_missing_during_capture");
        }
        if (brokerResult.statePublishedCount <= 0) {
            brokerResult.errors.put("issue.breath_state_stream_missing_during_capture");
        }
        if (brokerResult.stateValuePublishedCount <= 0) {
            brokerResult.errors.put("issue.breath_state_value_stream_missing_during_capture");
        }
        if (!"pass".equals(brokerResult.status)
                && brokerResult.feedbackReceiptCount < brokerResult.selectedBreathPublishedCount) {
            brokerResult.errors.put("issue.makepad_selected_breath_receipts_missing");
        }
        return new PhysicalLiveResult(captureResult, brokerResult);
    }

    static Result publishRoute(
            JSONObject routeReport,
            String host,
            int port,
            int limit,
            int receiptListenMs,
            String selectedSourcePreference)
            throws IOException, JSONException {
        Result result = new Result(host, port, limit, receiptListenMs);
        result.selectedSourcePreference = normalizeSelectedSourcePreference(selectedSourcePreference);
        result.publishMode = "post_capture_replay";
        result.livePublishDuringCapture = false;
        List<JSONObject> breathSamples = selectSamples(routeReport.optJSONArray("breath_samples"), limit);
        List<JSONObject> selectedBreathSamples = selectSelectedBreathSamples(
                breathSamples,
                result.selectedSourcePreference,
                limit);
        result.selectedSourceEffective = effectiveSelectedSource(breathSamples, result.selectedSourcePreference);
        List<JSONObject> stateSamples = selectSamples(routeReport.optJSONArray("state_samples"), limit);
        List<JSONObject> stateValueSamples = selectSamples(routeReport.optJSONArray("state_value_samples"), limit);
        List<JSONObject> feedbackSamples = selectSamples(routeReport.optJSONArray("feedback_samples"), limit);
        result.breathRequestedCount = routeReport.optJSONArray("breath_samples") == null
                ? 0
                : routeReport.optJSONArray("breath_samples").length();
        result.stateRequestedCount = routeReport.optJSONArray("state_samples") == null
                ? 0
                : routeReport.optJSONArray("state_samples").length();
        result.stateValueRequestedCount = routeReport.optJSONArray("state_value_samples") == null
                ? 0
                : routeReport.optJSONArray("state_value_samples").length();
        result.feedbackRequestedCount = routeReport.optJSONArray("feedback_samples") == null
                ? 0
                : routeReport.optJSONArray("feedback_samples").length();

        try (BrokerWebSocketClient client = BrokerWebSocketClient.open(host, port, 2500)) {
            result.brokerConnected = true;
            client.sendJson(new JSONObject()
                    .put("type", "hello")
                    .put("client_id", "app.rusty_hostess_t.quest.pmb_simulated_live")
                    .put("app_package", "io.github.mesmerprism.rustyhostess.t")
                    .put("role", "quest_pmb_simulated_live_publisher"), 1);
            client.readJson(500, result);
            sendCommandAndWait(client, result, "subscribe", new JSONObject()
                    .put("stream", STREAM_BREATH_FEEDBACK_RECEIPT)
                    .put("receiver", "app.rusty_hostess_t.quest.pmb_simulated_live"), 2);

            int sequence = 3;
            for (int index = 0; index < breathSamples.size(); index++) {
                JSONObject sample = breathSamples.get(index);
                long sampleSequence = sample.optLong("sequence_id", index + 1);
                PublishResult publish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_VOLUME,
                        sampleSequence,
                        breathPayload(sample, index + 1, STREAM_BREATH_VOLUME, false, result),
                        sequence++);
                result.breathPublishResults.put(publish.toJson());
                if ("pass".equals(publish.status)) {
                    result.breathPublishedCount += 1;
                }
                String sourceStream = breathSourceStreamId(sample);
                if (!sourceStream.isEmpty()) {
                    PublishResult sourcePublish = publishStreamSample(
                            client,
                            result,
                            sourceStream,
                            sampleSequence,
                            breathPayload(sample, index + 1, sourceStream, false, result),
                            sequence++);
                    result.breathPublishResults.put(sourcePublish.toJson());
                }
            }
            for (int index = 0; index < selectedBreathSamples.size(); index++) {
                JSONObject sample = selectedBreathSamples.get(index);
                PublishResult publish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_VOLUME_SELECTED,
                        sample.optLong("sequence_id", index + 1),
                        breathPayload(sample, index + 1, STREAM_BREATH_VOLUME_SELECTED, true, result),
                        sequence++);
                result.breathPublishResults.put(publish.toJson());
                if ("pass".equals(publish.status)) {
                    result.selectedBreathPublishedCount += 1;
                }
            }
            if (limit > 0) {
                PublishResult selectionPublish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_SELECTION_STATE,
                        1,
                        selectionStatePayload(result, selectedBreathSamples.size()),
                        sequence++);
                result.breathPublishResults.put(selectionPublish.toJson());
                if ("pass".equals(selectionPublish.status)) {
                    result.selectionStatePublishedCount += 1;
                }
            }
            for (int index = 0; index < stateSamples.size(); index++) {
                JSONObject sample = stateSamples.get(index);
                PublishResult publish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_STATE,
                        sample.optLong("sequence_id", index + 1),
                        statePayload(sample, index + 1, result),
                        sequence++);
                result.statePublishResults.put(publish.toJson());
                if ("pass".equals(publish.status)) {
                    result.statePublishedCount += 1;
                }
            }
            for (int index = 0; index < stateValueSamples.size(); index++) {
                JSONObject sample = stateValueSamples.get(index);
                PublishResult publish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_STATE_VALUE,
                        sample.optLong("sequence_id", index + 1),
                        stateValuePayload(sample, index + 1, result),
                        sequence++);
                result.stateValuePublishResults.put(publish.toJson());
                if ("pass".equals(publish.status)) {
                    result.stateValuePublishedCount += 1;
                }
            }
            for (int index = 0; index < feedbackSamples.size(); index++) {
                JSONObject sample = feedbackSamples.get(index);
                PublishResult publish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_FEEDBACK_STATE,
                        sample.optLong("sequence_id", index + 1),
                        feedbackPayload(sample, index + 1, result),
                        sequence++);
                result.feedbackPublishResults.put(publish.toJson());
                if ("pass".equals(publish.status)) {
                    result.feedbackPublishedCount += 1;
                }
            }

            long deadline = System.currentTimeMillis() + Math.max(0, receiptListenMs);
            while (System.currentTimeMillis() < deadline
                    && result.feedbackReceiptCount < result.selectedBreathPublishedCount) {
                int timeout = (int) Math.max(50, Math.min(250, deadline - System.currentTimeMillis()));
                client.readJson(timeout, result);
            }
        }
        result.status = result.selectedBreathPublishedCount > 0
                && result.statePublishedCount > 0
                && result.stateValuePublishedCount > 0
                && result.feedbackPublishedCount > 0
                && result.feedbackReceiptCount == result.selectedBreathPublishedCount
                ? "pass"
                : "fail";
        if (result.selectedBreathPublishedCount <= 0) {
            result.errors.put("issue.selected_breath_volume_stream_missing");
        }
        if (result.statePublishedCount <= 0) {
            result.errors.put("issue.breath_state_stream_missing");
        }
        if (result.stateValuePublishedCount <= 0) {
            result.errors.put("issue.breath_state_value_stream_missing");
        }
        if (!"pass".equals(result.status) && result.feedbackReceiptCount < result.selectedBreathPublishedCount) {
            result.errors.put("issue.makepad_selected_breath_receipts_missing");
        }
        return result;
    }

    private static void publishLiveTransportUpdate(
            BrokerWebSocketClient client,
            Result result,
            JSONObject update,
            LivePublishState state,
            long startedMs) throws IOException, JSONException {
        result.liveProcessorUpdateCount += 1;
        result.lastRouteStatus = update.optString("status", "missing");
        result.selectedSourceEffective = update.optString("selected_source_effective", result.selectedSourceEffective);
        JSONArray issues = update.optJSONArray("issues");
        if (issues != null) {
            for (int index = 0; index < issues.length(); index++) {
                String issue = issues.optString(index);
                if (issue.contains("json_invalid") || issue.contains("jni_bridge_failed")) {
                    result.errors.put(issue);
                }
            }
        }
        JSONArray breathSamples = update.optJSONArray("breath_samples");
        if (breathSamples == null || breathSamples.length() == 0) {
            return;
        }
        result.liveProcessorOutputUpdateCount += 1;
        result.liveRoutePassCount = result.liveProcessorOutputUpdateCount;
        maybePublishSelectionState(client, result, state);
        JSONArray stateSamples = update.optJSONArray("state_samples");
        if (stateSamples != null) {
            for (int index = 0; index < stateSamples.length(); index++) {
                JSONObject sample = stateSamples.optJSONObject(index);
                if (sample == null) {
                    continue;
                }
                result.stateRequestedCount += 1;
                PublishResult statePublish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_STATE,
                        sample.optLong("sequence_id", result.stateRequestedCount),
                        statePayload(sample, result.stateRequestedCount, result),
                        state.nextCommandSequence());
                putLimited(result.statePublishResults, statePublish.toJson(), result.retainedResultLimit());
                if ("pass".equals(statePublish.status)) {
                    result.statePublishedCount += 1;
                }
            }
        }
        JSONArray stateValueSamples = update.optJSONArray("state_value_samples");
        if (stateValueSamples != null) {
            for (int index = 0; index < stateValueSamples.length(); index++) {
                JSONObject sample = stateValueSamples.optJSONObject(index);
                if (sample == null) {
                    continue;
                }
                result.stateValueRequestedCount += 1;
                PublishResult stateValuePublish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_STATE_VALUE,
                        sample.optLong("sequence_id", result.stateValueRequestedCount),
                        stateValuePayload(sample, result.stateValueRequestedCount, result),
                        state.nextCommandSequence());
                putLimited(result.stateValuePublishResults, stateValuePublish.toJson(), result.retainedResultLimit());
                if ("pass".equals(stateValuePublish.status)) {
                    result.stateValuePublishedCount += 1;
                }
            }
        }

        for (int index = 0; index < breathSamples.length(); index++) {
            JSONObject sample = breathSamples.optJSONObject(index);
            if (sample == null) {
                continue;
            }
            result.breathRequestedCount += 1;
            long sampleSequence = sample.optLong("sequence_id", result.breathRequestedCount);
            PublishResult aggregatePublish = publishStreamSample(
                    client,
                    result,
                    STREAM_BREATH_VOLUME,
                    sampleSequence,
                    breathPayload(sample, result.breathRequestedCount, STREAM_BREATH_VOLUME, false, result),
                    state.nextCommandSequence());
            putLimited(result.breathPublishResults, aggregatePublish.toJson(), result.retainedResultLimit());
            if ("pass".equals(aggregatePublish.status)) {
                result.breathPublishedCount += 1;
            }
            String sourceStream = breathSourceStreamId(sample);
            if (!sourceStream.isEmpty()) {
                PublishResult sourcePublish = publishStreamSample(
                        client,
                        result,
                        sourceStream,
                        sampleSequence,
                        breathPayload(sample, result.breathRequestedCount, sourceStream, false, result),
                        state.nextCommandSequence());
                putLimited(result.breathPublishResults, sourcePublish.toJson(), result.retainedResultLimit());
            }
            if (!sampleMatchesSelectedSource(sample, result.selectedSourceEffective)) {
                continue;
            }
            PublishResult selectedPublish = publishStreamSample(
                    client,
                    result,
                    STREAM_BREATH_VOLUME_SELECTED,
                    sampleSequence,
                    breathPayload(sample, result.selectedBreathPublishedCount + 1, STREAM_BREATH_VOLUME_SELECTED, true, result),
                    state.nextCommandSequence());
            putLimited(result.breathPublishResults, selectedPublish.toJson(), result.retainedResultLimit());
            if ("pass".equals(selectedPublish.status)) {
                result.selectedBreathPublishedCount += 1;
                long elapsedMs = Math.max(0L, System.currentTimeMillis() - startedMs);
                if (result.firstSelectedPublishElapsedMs < 0L) {
                    result.firstSelectedPublishElapsedMs = elapsedMs;
                }
                result.lastSelectedPublishElapsedMs = elapsedMs;
            }
            result.feedbackRequestedCount += 1;
            PublishResult feedbackPublish = publishStreamSample(
                    client,
                    result,
                    STREAM_BREATH_FEEDBACK_STATE,
                    sampleSequence,
                    feedbackPayload(sample, result.feedbackRequestedCount, result),
                    state.nextCommandSequence());
            putLimited(result.feedbackPublishResults, feedbackPublish.toJson(), result.retainedResultLimit());
            if ("pass".equals(feedbackPublish.status)) {
                result.feedbackPublishedCount += 1;
            }
        }
    }

    private static void maybePublishSelectionState(
            BrokerWebSocketClient client,
            Result result,
            LivePublishState state) throws IOException, JSONException {
        if (result.selectedSourceEffective == null || result.selectedSourceEffective.isEmpty()) {
            result.selectedSourceEffective = "unknown";
        }
        if (state.selectionStatePublished
                && result.selectedSourceEffective.equals(state.lastSelectedSourceEffective)) {
            return;
        }
        PublishResult selectionPublish = publishStreamSample(
                client,
                result,
                STREAM_BREATH_SELECTION_STATE,
                result.selectionStatePublishedCount + 1L,
                selectionStatePayload(result, result.selectedBreathPublishedCount),
                state.nextCommandSequence());
        putLimited(result.breathPublishResults, selectionPublish.toJson(), result.retainedResultLimit());
        if ("pass".equals(selectionPublish.status)) {
            result.selectionStatePublishedCount += 1;
            state.selectionStatePublished = true;
            state.lastSelectedSourceEffective = result.selectedSourceEffective;
        }
    }

    private static void drainFeedbackReceipts(
            BrokerWebSocketClient client,
            Result result,
            int maxWaitMs) throws IOException, JSONException {
        long deadline = System.currentTimeMillis() + Math.max(0, maxWaitMs);
        while (System.currentTimeMillis() < deadline) {
            int timeout = (int) Math.max(25, Math.min(50, deadline - System.currentTimeMillis()));
            if (client.readJson(timeout, result) == null) {
                return;
            }
        }
    }

    private static boolean sampleMatchesSelectedSource(JSONObject sample, String selectedSourceEffective) {
        return "polar".equals(selectedSourceEffective) && "polar".equals(breathSourceKind(sample))
                || "controller".equals(selectedSourceEffective) && "controller".equals(breathSourceKind(sample));
    }

    private static void putLimited(JSONArray array, JSONObject value, int limit) {
        if (limit <= 0 || array.length() < limit) {
            array.put(value);
        }
    }

    static BrokerTelemetryResult observePolarAccTelemetry(
            String host,
            int port,
            String deviceAddress,
            int accRateHz,
            int scanTimeoutMs,
            int durationMs,
            boolean requestProviderStart,
            boolean stopProviderOnFinish,
            AccFrameConsumer consumer) throws IOException, JSONException {
        BrokerTelemetryResult result = new BrokerTelemetryResult(
                host,
                port,
                deviceAddress,
                accRateHz,
                scanTimeoutMs,
                durationMs,
                requestProviderStart,
                stopProviderOnFinish);
        try (BrokerWebSocketClient client = BrokerWebSocketClient.open(host, port, 2500)) {
            result.brokerConnected = true;
            client.sendJson(new JSONObject()
                    .put("type", "hello")
                    .put("client_id", "app.rusty_hostess_t.quest.telemetry_observer")
                    .put("app_package", "io.github.mesmerprism.rustyhostess.t")
                    .put("role", "quest_broker_telemetry_ui_observer"), 1);
            client.readJson(500);
            telemetryCommandAndWait(client, result, "subscribe", new JSONObject()
                    .put("stream", EXTERNAL_STREAM_POLAR_ACC)
                    .put("receiver", "app.rusty_hostess_t.quest.telemetry_observer"), 2, consumer);
            if (requestProviderStart) {
                result.polarStartStatus = telemetryCommandAndWait(client, result, "polar_pmd.start", new JSONObject()
                        .put("device_address", deviceAddress == null ? "" : deviceAddress)
                        .put("scan_timeout_ms", scanTimeoutMs)
                        .put("pmd_stream", "acc")
                        .put("acc_sample_rate_hz", accRateHz)
                        .put("high_connection_priority", true), 3, consumer);
            }

            long acquisitionDeadline = System.currentTimeMillis()
                    + (requestProviderStart ? Math.max(0, scanTimeoutMs) : 0);
            boolean captureWindowStarted = !requestProviderStart;
            long captureDeadline = System.currentTimeMillis() + Math.max(0, durationMs);
            while (true) {
                long now = System.currentTimeMillis();
                if (!captureWindowStarted && result.frameCount > 0) {
                    captureWindowStarted = true;
                    captureDeadline = now + Math.max(0, durationMs);
                }
                long activeDeadline = captureWindowStarted ? captureDeadline : acquisitionDeadline;
                if (now >= activeDeadline) {
                    break;
                }
                int timeout = (int) Math.max(50, Math.min(250, activeDeadline - now));
                JSONObject message = client.readJson(timeout);
                if (message == null) {
                    continue;
                }
                result.acceptMessage(message, consumer);
            }
            if (requestProviderStart && stopProviderOnFinish) {
                result.polarStopStatus = telemetryCommandAndWait(
                        client,
                        result,
                        "polar_pmd.stop",
                        new JSONObject(),
                        4,
                        consumer);
            }
        } catch (IOException | JSONException | RuntimeException ex) {
            result.errors.put(ex.getMessage() == null ? ex.toString() : ex.getMessage());
            throw ex;
        }
        result.status = result.frameCount > 0 && result.sampleCount > 0 && result.errors.length() == 0
                ? "pass"
                : "fail";
        if (result.frameCount <= 0 || result.sampleCount <= 0) {
            result.errors.put("issue.broker_polar_acc_events_missing");
        }
        return result;
    }

    private static String telemetryCommandAndWait(
            BrokerWebSocketClient client,
            BrokerTelemetryResult result,
            String command,
            JSONObject params,
            int sequence,
            AccFrameConsumer consumer) throws IOException, JSONException {
        String requestId = "quest-broker-telemetry-" + command.replace('.', '-') + "-" + sequence;
        client.sendJson(new JSONObject()
                .put("type", "command")
                .put("schema", MANIFOLD_COMMAND_SCHEMA)
                .put("request_id", requestId)
                .put("command", command)
                .put("params", params)
                .put("client_id", "app.rusty_hostess_t.quest.telemetry_observer")
                .put("app_package", "io.github.mesmerprism.rustyhostess.t"), sequence);
        long deadline = System.currentTimeMillis() + 1500L;
        while (System.currentTimeMillis() < deadline) {
            int timeout = (int) Math.max(50, Math.min(250, deadline - System.currentTimeMillis()));
            JSONObject reply = client.readJson(timeout);
            if (reply == null) {
                continue;
            }
            if ("stream_event".equals(reply.optString("type"))) {
                result.acceptMessage(reply, consumer);
                continue;
            }
            if (requestId.equals(reply.optString("request_id"))
                    || command.equals(reply.optString("command"))) {
                boolean accepted = reply.has("accepted")
                        ? reply.optBoolean("accepted")
                        : reply.optBoolean("ok", reply.optBoolean("success", true));
                result.commandReplies.put(reply);
                return accepted ? "pass" : "fail";
            }
        }
        result.errors.put("issue.broker_command_ack_timeout:" + command);
        return "unknown";
    }

    private static String physicalCommandAndWait(
            BrokerWebSocketClient client,
            PhysicalCaptureResult result,
            String command,
            JSONObject params,
            int sequence) throws IOException, JSONException {
        String requestId = "quest-pmb-physical-live-" + command.replace('.', '-') + "-" + sequence;
        client.sendJson(new JSONObject()
                .put("type", "command")
                .put("schema", MANIFOLD_COMMAND_SCHEMA)
                .put("request_id", requestId)
                .put("command", command)
                .put("params", params)
                .put("client_id", "app.rusty_hostess_t.quest.pmb_physical_live")
                .put("app_package", "io.github.mesmerprism.rustyhostess.t"), sequence);
        long deadline = System.currentTimeMillis() + 1500L;
        while (System.currentTimeMillis() < deadline) {
            int timeout = (int) Math.max(50, Math.min(250, deadline - System.currentTimeMillis()));
            JSONObject reply = client.readJson(timeout);
            if (reply == null) {
                continue;
            }
            if ("stream_event".equals(reply.optString("type"))) {
                result.acceptObservedMessage(reply);
                continue;
            }
            if (requestId.equals(reply.optString("request_id"))
                    || command.equals(reply.optString("command"))) {
                boolean accepted = reply.has("accepted")
                        ? reply.optBoolean("accepted")
                        : reply.optBoolean("ok", reply.optBoolean("success", true));
                result.commandReplies.put(reply);
                return accepted ? "pass" : "fail";
            }
        }
        result.errors.put("issue.broker_command_ack_timeout:" + command);
        return "unknown";
    }

    private static PublishResult publishStreamSample(
            BrokerWebSocketClient client,
            Result result,
            String streamId,
            long sequenceId,
            JSONObject payload,
            int commandSequence) throws IOException, JSONException {
        JSONObject params = new JSONObject()
                .put("stream", streamId)
                .put("sequence_id", sequenceId)
                .put("payload", payload);
        String status = sendCommandAndWait(client, result, "publish_stream_event", params, commandSequence);
        return new PublishResult(streamId, sequenceId, status);
    }

    private static String sendCommandAndWait(
            BrokerWebSocketClient client,
            Result result,
            String command,
            JSONObject params,
            int sequence) throws IOException, JSONException {
        String requestId = result.requestIdPrefix + "-" + command.replace('.', '-') + "-" + sequence;
        client.sendJson(new JSONObject()
                .put("type", "command")
                .put("schema", MANIFOLD_COMMAND_SCHEMA)
                .put("request_id", requestId)
                .put("command", command)
                .put("params", params)
                .put("client_id", result.clientId)
                .put("app_package", "io.github.mesmerprism.rustyhostess.t"), sequence);
        long deadline = System.currentTimeMillis() + 1500L;
        while (System.currentTimeMillis() < deadline) {
            int timeout = (int) Math.max(50, Math.min(250, deadline - System.currentTimeMillis()));
            JSONObject reply = client.readJson(timeout, result);
            if (reply == null) {
                continue;
            }
            if (requestId.equals(reply.optString("request_id"))
                    || command.equals(reply.optString("command"))) {
                boolean accepted = reply.has("accepted")
                        ? reply.optBoolean("accepted")
                        : reply.optBoolean("ok", reply.optBoolean("success", true));
                result.commandReplies.put(reply);
                return accepted ? "pass" : "fail";
            }
        }
        result.errors.put("issue.broker_command_ack_timeout:" + command);
        return "unknown";
    }

    private static JSONObject breathPayload(
            JSONObject sample,
            int fallbackSequence,
            String streamId,
            boolean selected,
            Result result) throws JSONException {
        int sequence = (int) sample.optLong("sequence_id", fallbackSequence);
        JSONObject payload = new JSONObject()
                .put("schema", "rusty.manifold.breath.volume.v1")
                .put("stream_id", streamId)
                .put("sequence_id", sequence)
                .put("source_id", sample.optString("source_id", "source.unknown"))
                .put("source_kind", breathSourceKind(sample))
                .put("input_stream_id", sample.optString("input_stream_id", ""))
                .put("normalized_stream_id", sample.optString("normalized_stream_id", ""))
                .put("sample_time_unix_ns", sampleTimeUnixNs(sample))
                .put("volume01", sample.optDouble("volume01", 0.0))
                .put("phase", sample.optString("phase", "unknown"))
                .put("quality", sample.optString("quality", "unknown"))
                .put("quality01", sample.optDouble("quality01", sample.optDouble("tracking01", 1.0)))
                .put("tracking01", sample.optDouble("tracking01", 0.0))
                .put("processor_id", result.processorId)
                .put("publisher", "app.rusty_hostess_t.quest")
                .put("computation_authority", "quest_hostess_android_app");
        if (selected) {
            payload.put("selected", true)
                    .put("selected_source_preference", result.selectedSourcePreference)
                    .put("selected_source_effective", result.selectedSourceEffective);
        }
        return payload;
    }

    private static JSONObject selectionStatePayload(Result result, int selectedSampleCount) throws JSONException {
        return new JSONObject()
                .put("schema", "rusty.manifold.breath.selection_state.v1")
                .put("stream_id", STREAM_BREATH_SELECTION_STATE)
                .put("sequence_id", 1)
                .put("selected_stream_id", STREAM_BREATH_VOLUME_SELECTED)
                .put("selected_source_preference", result.selectedSourcePreference)
                .put("selected_source_effective", result.selectedSourceEffective)
                .put("source_stream_ids", new JSONArray()
                        .put(STREAM_BREATH_VOLUME_POLAR)
                        .put(STREAM_BREATH_VOLUME_CONTROLLER))
                .put("selected_sample_count", selectedSampleCount)
                .put("publisher", "app.rusty_hostess_t.quest")
                .put("computation_authority", "quest_hostess_android_app");
    }

    private static JSONObject feedbackPayload(JSONObject sample, int fallbackSequence, Result result) throws JSONException {
        int sequence = (int) sample.optLong("sequence_id", fallbackSequence);
        return new JSONObject()
                .put("schema", "rusty.manifold.breath.feedback_state.v1")
                .put("stream_id", STREAM_BREATH_FEEDBACK_STATE)
                .put("sequence_id", sequence)
                .put("source_breath_sequence_id", sample.optLong("source_breath_sequence_id", sequence))
                .put("source_id", sample.optString("source_id", "source.unknown"))
                .put("sample_time_unix_ns", sample.optLong("sample_time_unix_ns", sampleTimeUnixNs(sample)))
                .put("volume01", sample.optDouble("volume01", 0.0))
                .put("phase", sample.optString("phase", "unknown"))
                .put("quality", sample.optString("quality", "unknown"))
                .put("processor_id", result.processorId)
                .put("publisher", "app.rusty_hostess_t.quest")
                .put("computation_authority", "quest_hostess_android_app");
    }

    private static JSONObject statePayload(JSONObject sample, int fallbackSequence, Result result) throws JSONException {
        int sequence = (int) sample.optLong("sequence_id", fallbackSequence);
        String state = sample.optString("state", sample.optString("phase", "pause"));
        return new JSONObject()
                .put("schema", "rusty.manifold.breath.state.v1")
                .put("stream_id", STREAM_BREATH_STATE)
                .put("sequence_id", sequence)
                .put("source_breath_sequence_id", sample.optLong("source_breath_sequence_id", sequence))
                .put("source_id", sample.optString("source_id", "source.unknown"))
                .put("sample_time_unix_ns", sample.optLong("sample_time_unix_ns", sampleTimeUnixNs(sample)))
                .put("state", state)
                .put("phase", state)
                .put("state01", sample.optDouble("state01", 0.5))
                .put("tracking01", sample.optDouble("tracking01", 0.0))
                .put("quality", sample.optString("quality", "unknown"))
                .put("processor_id", result.processorId)
                .put("publisher", "app.rusty_hostess_t.quest")
                .put("computation_authority", "quest_hostess_android_app");
    }

    private static JSONObject stateValuePayload(JSONObject sample, int fallbackSequence, Result result) throws JSONException {
        int sequence = (int) sample.optLong("sequence_id", fallbackSequence);
        String state = sample.optString("state", sample.optString("phase", "pause"));
        Object value01 = sample.has("value01") ? sample.get("value01") : JSONObject.NULL;
        return new JSONObject()
                .put("schema", "rusty.manifold.breath.state_value.v1")
                .put("stream_id", STREAM_BREATH_STATE_VALUE)
                .put("sequence_id", sequence)
                .put("source_breath_sequence_id", sample.optLong("source_breath_sequence_id", sequence))
                .put("source_state_sequence_id", sample.optLong("source_state_sequence_id", sequence))
                .put("source_id", sample.optString("source_id", "source.unknown"))
                .put("sample_time_unix_ns", sample.optLong("sample_time_unix_ns", sampleTimeUnixNs(sample)))
                .put("state", state)
                .put("phase", state)
                .put("state01", sample.optDouble("state01", 0.5))
                .put("target01", sample.optDouble("target01", 0.5))
                .put("value01", value01)
                .put("volume01", value01)
                .put("delta_seconds", sample.optDouble("delta_seconds", 0.0))
                .put("stale_gap", sample.optBoolean("stale_gap", false))
                .put("tracking01", sample.optDouble("tracking01", 0.0))
                .put("quality", sample.optString("quality", "unknown"))
                .put("processor_id", "processor.projected_motion_breath.state_value")
                .put("publisher", "app.rusty_hostess_t.quest")
                .put("computation_authority", "quest_hostess_android_app");
    }

    private static long sampleTimeUnixNs(JSONObject sample) {
        if (sample.has("sample_time_unix_ns")) {
            return sample.optLong("sample_time_unix_ns", 0L);
        }
        double seconds = sample.optDouble("sample_time_s", 0.0);
        return (long) Math.max(0.0, seconds * 1_000_000_000.0);
    }

    private static String normalizeSelectedSourcePreference(String value) {
        if ("polar".equals(value) || "controller".equals(value)) {
            return value;
        }
        return "auto";
    }

    private static String effectiveSelectedSource(List<JSONObject> breathSamples, String preference) {
        if (!"auto".equals(preference)) {
            return preference;
        }
        boolean hasController = false;
        for (JSONObject sample : breathSamples) {
            String kind = breathSourceKind(sample);
            if ("polar".equals(kind)) {
                return "polar";
            }
            if ("controller".equals(kind)) {
                hasController = true;
            }
        }
        return hasController ? "controller" : "unknown";
    }

    private static List<JSONObject> selectSelectedBreathSamples(
            List<JSONObject> breathSamples,
            String preference,
            int limit) {
        List<JSONObject> selected = new ArrayList<>();
        if (limit <= 0) {
            return selected;
        }
        String effective = effectiveSelectedSource(breathSamples, preference);
        for (JSONObject sample : breathSamples) {
            if ("unknown".equals(effective) || effective.equals(breathSourceKind(sample))) {
                selected.add(sample);
                if (selected.size() >= limit) {
                    break;
                }
            }
        }
        return selected;
    }

    private static String breathSourceKind(JSONObject sample) {
        String text = (sample.optString("source_id", "") + " "
                + sample.optString("input_stream_id", "") + " "
                + sample.optString("normalized_stream_id", "")).toLowerCase();
        if (text.contains("polar") || text.contains("bio:polar")) {
            return "polar";
        }
        if (text.contains("controller") || text.contains("object_pose") || text.contains("motion.object")) {
            return "controller";
        }
        return "unknown";
    }

    private static String breathSourceStreamId(JSONObject sample) {
        String kind = breathSourceKind(sample);
        if ("polar".equals(kind)) {
            return STREAM_BREATH_VOLUME_POLAR;
        }
        if ("controller".equals(kind)) {
            return STREAM_BREATH_VOLUME_CONTROLLER;
        }
        return "";
    }

    private static List<JSONObject> selectSamples(JSONArray samples, int limit) throws JSONException {
        List<JSONObject> selected = new ArrayList<>();
        if (samples == null || limit <= 0) {
            return selected;
        }
        Map<String, List<JSONObject>> bySource = new LinkedHashMap<>();
        for (int index = 0; index < samples.length(); index++) {
            JSONObject sample = samples.optJSONObject(index);
            if (sample == null) {
                continue;
            }
            String source = sample.optString("source_id", "source.unknown");
            List<JSONObject> sourceSamples = bySource.get(source);
            if (sourceSamples == null) {
                sourceSamples = new ArrayList<>();
                bySource.put(source, sourceSamples);
            }
            sourceSamples.add(sample);
        }
        int cursor = 0;
        while (selected.size() < limit && !bySource.isEmpty()) {
            boolean progressed = false;
            for (List<JSONObject> sourceSamples : bySource.values()) {
                if (cursor < sourceSamples.size()) {
                    selected.add(sourceSamples.get(cursor));
                    progressed = true;
                    if (selected.size() >= limit) {
                        break;
                    }
                }
            }
            if (!progressed) {
                break;
            }
            cursor += 1;
        }
        return selected;
    }

    static final class PhysicalCaptureResult {
        final String brokerHost;
        final int brokerPort;
        final String deviceAddress;
        final int accRateHz;
        final int scanTimeoutMs;
        final int durationMs;
        final int controllerWaitMs;
        final String eventsJsonl;
        final JSONArray commandReplies = new JSONArray();
        final JSONArray observedEvents = new JSONArray();
        final JSONArray errors = new JSONArray();
        String status = "pending";
        boolean brokerConnected = false;
        String selectedSourcePreference = "auto";
        boolean polarRequired = true;
        boolean controllerRequired = true;
        String polarStartStatus = "not_started";
        String polarStopStatus = "not_started";
        int polarEventCount = 0;
        int objectPoseEventCount = 0;
        int activeObjectPoseCount = 0;
        int trackedObjectPoseCount = 0;
        int connectedObjectPoseCount = 0;
        int activeTrackedConnectedObjectPoseCount = 0;

        PhysicalCaptureResult(
                String brokerHost,
                int brokerPort,
                String deviceAddress,
                int accRateHz,
                int scanTimeoutMs,
                int durationMs,
                int controllerWaitMs,
                String eventsJsonl) {
            this.brokerHost = brokerHost;
            this.brokerPort = brokerPort;
            this.deviceAddress = deviceAddress == null ? "" : deviceAddress;
            this.accRateHz = accRateHz;
            this.scanTimeoutMs = scanTimeoutMs;
            this.durationMs = durationMs;
            this.controllerWaitMs = controllerWaitMs;
            this.eventsJsonl = eventsJsonl;
        }

        void configureSourcePreference(String preference) {
            selectedSourcePreference = normalizeSelectedSourcePreference(preference);
            polarRequired = "polar".equals(selectedSourcePreference);
            controllerRequired = "controller".equals(selectedSourcePreference);
        }

        boolean polarProviderRequested() {
            return !"controller".equals(selectedSourcePreference);
        }

        boolean requiredInputsCaptured() {
            if (polarRequired) {
                return polarEventCount > 0;
            }
            if (controllerRequired) {
                return activeTrackedConnectedObjectPoseCount > 0;
            }
            return polarEventCount > 0 || activeTrackedConnectedObjectPoseCount > 0;
        }

        JSONObject toJson() throws JSONException {
            return new JSONObject()
                    .put("schema", "rusty.hostess.projected_motion_breath.quest_physical_input_capture_report.v1")
                    .put("status", status)
                    .put("broker_host", brokerHost)
                    .put("broker_port", brokerPort)
                    .put("broker_connected", brokerConnected)
                    .put("broker_transport_used", brokerConnected)
                    .put("events_jsonl", eventsJsonl)
                    .put("selected_source_preference", selectedSourcePreference)
                    .put("polar_required", polarRequired)
                    .put("controller_required", controllerRequired)
                    .put("polar_provider_requested", polarProviderRequested())
                    .put("device_address_supplied", !deviceAddress.isEmpty())
                    .put("acc_rate_hz", accRateHz)
                    .put("scan_timeout_ms", scanTimeoutMs)
                    .put("duration_ms", durationMs)
                    .put("controller_wait_ms", controllerWaitMs)
                    .put("polar_start_status", polarStartStatus)
                    .put("polar_stop_status", polarStopStatus)
                    .put("polar_event_count", polarEventCount)
                    .put("object_pose_event_count", objectPoseEventCount)
                    .put("active_object_pose_count", activeObjectPoseCount)
                    .put("tracked_object_pose_count", trackedObjectPoseCount)
                    .put("connected_object_pose_count", connectedObjectPoseCount)
                    .put("active_tracked_connected_object_pose_count", activeTrackedConnectedObjectPoseCount)
                    .put("physical_polar_ble_used", polarEventCount > 0)
                    .put("physical_controller_input_used", activeTrackedConnectedObjectPoseCount > 0)
                    .put("controller_input_used", activeTrackedConnectedObjectPoseCount > 0)
                    .put("simulated_polar_provider_used", false)
                    .put("simulated_controller_provider_used", false)
                    .put("command_replies", commandReplies)
                    .put("observed_events", observedEvents)
                    .put("errors", errors);
        }

        void acceptObservedMessage(JSONObject message) throws JSONException {
            if (!"stream_event".equals(message.optString("type"))) {
                return;
            }
            String stream = streamId(message);
            if (EXTERNAL_STREAM_POLAR_ACC.equals(stream)) {
                polarEventCount += 1;
            } else if (STREAM_OBJECT_POSE.equals(stream)) {
                objectPoseEventCount += 1;
                JSONObject payload = message.optJSONObject("payload");
                boolean active = payload != null && payload.optBoolean("active", false);
                boolean tracked = payload != null && payload.optBoolean("tracked", false);
                boolean connected = payload != null && payload.optBoolean("connected", false);
                if (active) {
                    activeObjectPoseCount += 1;
                }
                if (tracked) {
                    trackedObjectPoseCount += 1;
                }
                if (connected) {
                    connectedObjectPoseCount += 1;
                }
                if (active && tracked && connected) {
                    activeTrackedConnectedObjectPoseCount += 1;
                }
            }
            if (observedEvents.length() < 24) {
                observedEvents.put(message);
            }
        }

        boolean acceptCaptureMessage(JSONObject message, BufferedWriter writer) throws IOException, JSONException {
            if (!"stream_event".equals(message.optString("type"))) {
                return false;
            }
            String stream = streamId(message);
            if (!EXTERNAL_STREAM_POLAR_ACC.equals(stream) && !STREAM_OBJECT_POSE.equals(stream)) {
                return false;
            }
            acceptObservedMessage(message);
            if (STREAM_OBJECT_POSE.equals(stream) && !isUsableObjectPose(message)) {
                return false;
            }
            writer.write(message.toString());
            writer.newLine();
            return true;
        }

        private boolean isUsableObjectPose(JSONObject message) {
            JSONObject payload = message.optJSONObject("payload");
            return payload != null
                    && payload.optBoolean("active", false)
                    && payload.optBoolean("tracked", false)
                    && payload.optBoolean("connected", false);
        }
    }

    private static String streamId(JSONObject message) {
        JSONObject payload = message.optJSONObject("payload");
        return message.optString("stream",
                message.optString("stream_id", payload == null ? "" : payload.optString("stream_id", "")));
    }

    static final class Result {
        final String brokerHost;
        final int brokerPort;
        final int publishLimit;
        final int receiptListenMs;
        final JSONArray breathPublishResults = new JSONArray();
        final JSONArray statePublishResults = new JSONArray();
        final JSONArray stateValuePublishResults = new JSONArray();
        final JSONArray feedbackPublishResults = new JSONArray();
        final JSONArray commandReplies = new JSONArray();
        final JSONArray receiptEvents = new JSONArray();
        final JSONArray errors = new JSONArray();
        String status = "pending";
        boolean brokerConnected = false;
        int breathRequestedCount = 0;
        int stateRequestedCount = 0;
        int stateValueRequestedCount = 0;
        int feedbackRequestedCount = 0;
        int breathPublishedCount = 0;
        int selectedBreathPublishedCount = 0;
        int selectionStatePublishedCount = 0;
        int statePublishedCount = 0;
        int stateValuePublishedCount = 0;
        int feedbackPublishedCount = 0;
        int feedbackReceiptCount = 0;
        String selectedSourcePreference = "auto";
        String selectedSourceEffective = "auto";
        String publishMode = "unknown";
        boolean livePublishDuringCapture = false;
        boolean incrementalProcessorUsed = false;
        boolean snapshotReplayUsed = false;
        int livePublishIntervalMs = 0;
        int inputEventProcessedCount = 0;
        int liveProcessorUpdateCount = 0;
        int liveProcessorOutputUpdateCount = 0;
        int liveRoutePassCount = 0;
        int liveRouteFailCount = 0;
        long firstSelectedPublishElapsedMs = -1L;
        long lastSelectedPublishElapsedMs = -1L;
        String lastRouteStatus = "missing";
        String clientId = "app.rusty_hostess_t.quest.pmb_simulated_live";
        String requestIdPrefix = "quest-pmb-simulated-live";
        String processorId = "processor.projected_motion_breath.quest_simulated_live";
        JSONObject closeReport = new JSONObject();

        Result(String brokerHost, int brokerPort, int publishLimit, int receiptListenMs) {
            this.brokerHost = brokerHost;
            this.brokerPort = brokerPort;
            this.publishLimit = publishLimit;
            this.receiptListenMs = receiptListenMs;
        }

        int retainedResultLimit() {
            return Math.max(64, Math.max(1, publishLimit) * 8);
        }

        JSONObject toJson() throws JSONException {
            return new JSONObject()
                    .put("schema", "rusty.hostess.projected_motion_breath.quest_broker_publish_report.v1")
                    .put("status", status)
                    .put("broker_host", brokerHost)
                    .put("broker_port", brokerPort)
                    .put("broker_connected", brokerConnected)
                    .put("broker_transport_used", brokerConnected)
                    .put("publish_limit", publishLimit)
                    .put("receipt_listen_ms", receiptListenMs)
                    .put("selected_source_preference", selectedSourcePreference)
                    .put("selected_source_effective", selectedSourceEffective)
                    .put("publish_mode", publishMode)
                    .put("live_publish_during_capture", livePublishDuringCapture)
                    .put("incremental_processor_used", incrementalProcessorUsed)
                    .put("snapshot_replay_used", snapshotReplayUsed)
                    .put("live_publish_interval_ms", livePublishIntervalMs)
                    .put("input_event_processed_count", inputEventProcessedCount)
                    .put("live_processor_update_count", liveProcessorUpdateCount)
                    .put("live_processor_output_update_count", liveProcessorOutputUpdateCount)
                    .put("live_route_pass_count", liveRoutePassCount)
                    .put("live_route_fail_count", liveRouteFailCount)
                    .put("first_selected_publish_elapsed_ms", firstSelectedPublishElapsedMs)
                    .put("last_selected_publish_elapsed_ms", lastSelectedPublishElapsedMs)
                    .put("last_route_status", lastRouteStatus)
                    .put("close_report", closeReport)
                    .put("breath_requested_count", breathRequestedCount)
                    .put("state_requested_count", stateRequestedCount)
                    .put("state_value_requested_count", stateValueRequestedCount)
                    .put("feedback_requested_count", feedbackRequestedCount)
                    .put("breath_published_count", breathPublishedCount)
                    .put("selected_breath_published_count", selectedBreathPublishedCount)
                    .put("selection_state_published_count", selectionStatePublishedCount)
                    .put("state_published_count", statePublishedCount)
                    .put("state_value_published_count", stateValuePublishedCount)
                    .put("feedback_published_count", feedbackPublishedCount)
                    .put("feedback_receipt_count", feedbackReceiptCount)
                    .put("receipt_stream_id", STREAM_BREATH_FEEDBACK_RECEIPT)
                    .put("breath_results", breathPublishResults)
                    .put("state_results", statePublishResults)
                    .put("state_value_results", stateValuePublishResults)
                    .put("feedback_results", feedbackPublishResults)
                    .put("command_replies", commandReplies)
                    .put("receipt_events", receiptEvents)
                    .put("errors", errors);
        }

        void acceptMessage(JSONObject message) throws JSONException {
            if (!"stream_event".equals(message.optString("type"))) {
                return;
            }
            JSONObject payload = message.optJSONObject("payload");
            String stream = message.optString("stream",
                    message.optString("stream_id", payload == null ? "" : payload.optString("stream_id", "")));
            if (!STREAM_BREATH_FEEDBACK_RECEIPT.equals(stream)) {
                return;
            }
            feedbackReceiptCount += 1;
            if (receiptEvents.length() < retainedResultLimit()) {
                receiptEvents.put(message);
            }
        }
    }

    static final class PhysicalLiveResult {
        final PhysicalCaptureResult captureResult;
        final Result brokerResult;

        PhysicalLiveResult(PhysicalCaptureResult captureResult, Result brokerResult) {
            this.captureResult = captureResult;
            this.brokerResult = brokerResult;
        }
    }

    private static final class LivePublishState {
        boolean selectionStatePublished = false;
        String lastSelectedSourceEffective = "";
        int commandSequence = 20;

        int nextCommandSequence() {
            commandSequence += 1;
            return commandSequence;
        }
    }

    interface AccFrameConsumer {
        void accept(ObservedAccFrame frame);
    }

    static final class ObservedAccFrame {
        final long hostTimeNs;
        final long sensorTimestampNs;
        final List<int[]> samplesMg;

        ObservedAccFrame(long hostTimeNs, long sensorTimestampNs, List<int[]> samplesMg) {
            this.hostTimeNs = hostTimeNs;
            this.sensorTimestampNs = sensorTimestampNs;
            this.samplesMg = samplesMg;
        }
    }

    static final class BrokerTelemetryResult {
        final String brokerHost;
        final int brokerPort;
        final String deviceAddress;
        final int accRateHz;
        final int scanTimeoutMs;
        final int durationMs;
        final boolean providerStartRequested;
        final boolean providerStopRequested;
        final JSONArray commandReplies = new JSONArray();
        final JSONArray observedEvents = new JSONArray();
        final JSONArray errors = new JSONArray();
        String status = "pending";
        boolean brokerConnected = false;
        String polarStartStatus = "not_requested";
        String polarStopStatus = "not_requested";
        int frameCount = 0;
        int sampleCount = 0;
        int malformedFrameCount = 0;

        BrokerTelemetryResult(
                String brokerHost,
                int brokerPort,
                String deviceAddress,
                int accRateHz,
                int scanTimeoutMs,
                int durationMs,
                boolean providerStartRequested,
                boolean providerStopRequested) {
            this.brokerHost = brokerHost;
            this.brokerPort = brokerPort;
            this.deviceAddress = deviceAddress == null ? "" : deviceAddress;
            this.accRateHz = accRateHz;
            this.scanTimeoutMs = scanTimeoutMs;
            this.durationMs = durationMs;
            this.providerStartRequested = providerStartRequested;
            this.providerStopRequested = providerStopRequested;
        }

        JSONObject toJson() throws JSONException {
            return new JSONObject()
                    .put("schema", "rusty.hostess.broker_telemetry_observer.report.v1")
                    .put("status", status)
                    .put("broker_host", brokerHost)
                    .put("broker_port", brokerPort)
                    .put("broker_connected", brokerConnected)
                    .put("broker_transport_used", brokerConnected)
                    .put("broker_transport_authority", "quest_broker_polar_pmd_provider")
                    .put("hostess_role", "foreground_telemetry_ui_observer")
                    .put("stream_id", EXTERNAL_STREAM_POLAR_ACC)
                    .put("device_address_supplied", !deviceAddress.isEmpty())
                    .put("acc_rate_hz", accRateHz)
                    .put("scan_timeout_ms", scanTimeoutMs)
                    .put("duration_ms", durationMs)
                    .put("provider_start_requested", providerStartRequested)
                    .put("provider_stop_requested", providerStopRequested)
                    .put("polar_start_status", polarStartStatus)
                    .put("polar_stop_status", polarStopStatus)
                    .put("frame_count", frameCount)
                    .put("sample_count", sampleCount)
                    .put("malformed_frame_count", malformedFrameCount)
                    .put("direct_ble_used", false)
                    .put("physical_polar_ble_used", frameCount > 0)
                    .put("simulated_polar_provider_used", false)
                    .put("telemetry_ui_visualized", frameCount > 0 && sampleCount > 0)
                    .put("command_replies", commandReplies)
                    .put("observed_events", observedEvents)
                    .put("errors", errors);
        }

        void acceptMessage(JSONObject message, AccFrameConsumer consumer) throws JSONException {
            if (!"stream_event".equals(message.optString("type"))) {
                return;
            }
            if (!EXTERNAL_STREAM_POLAR_ACC.equals(streamId(message))) {
                return;
            }
            ObservedAccFrame frame = decodeObservedAccFrame(message);
            if (observedEvents.length() < 24) {
                observedEvents.put(message);
            }
            if (frame == null || frame.samplesMg.isEmpty()) {
                malformedFrameCount += 1;
                return;
            }
            frameCount += 1;
            sampleCount += frame.samplesMg.size();
            if (consumer != null) {
                consumer.accept(frame);
            }
        }
    }

    private static ObservedAccFrame decodeObservedAccFrame(JSONObject message) {
        JSONObject payload = message.optJSONObject("payload");
        if (payload == null) {
            payload = message;
        }
        List<int[]> samples = new ArrayList<>();
        JSONArray samplesMg = payload.optJSONArray("samples_mg");
        if (samplesMg != null) {
            for (int index = 0; index < samplesMg.length(); index++) {
                Object rawSample = samplesMg.opt(index);
                int[] sample = decodeObservedAccSample(rawSample);
                if (sample != null) {
                    samples.add(sample);
                }
            }
        }
        if (samples.isEmpty()) {
            int[] topLevel = decodeObservedAccSample(payload);
            if (topLevel != null) {
                samples.add(topLevel);
            }
        }
        if (samples.isEmpty()) {
            JSONObject decoded = payload.optJSONObject("decoded");
            if (decoded != null && decoded.has("first_x_mg")) {
                samples.add(new int[] {
                        decoded.optInt("first_x_mg", 0),
                        decoded.optInt("first_y_mg", 0),
                        decoded.optInt("first_z_mg", 0)
                });
            }
        }
        if (samples.isEmpty()) {
            return null;
        }
        long sensorTimestampNs = payload.optLong(
                "sensor_timestamp_ns",
                message.optLong("sensor_timestamp_ns", 0L));
        return new ObservedAccFrame(System.nanoTime(), sensorTimestampNs, samples);
    }

    private static int[] decodeObservedAccSample(Object rawSample) {
        if (rawSample instanceof JSONArray) {
            JSONArray row = (JSONArray) rawSample;
            if (row.length() < 3) {
                return null;
            }
            return new int[] {row.optInt(0, 0), row.optInt(1, 0), row.optInt(2, 0)};
        }
        if (rawSample instanceof JSONObject) {
            JSONObject row = (JSONObject) rawSample;
            if (row.has("x_mg") || row.has("y_mg") || row.has("z_mg")) {
                return new int[] {
                        row.optInt("x_mg", 0),
                        row.optInt("y_mg", 0),
                        row.optInt("z_mg", 0)
                };
            }
            if (row.has("x") || row.has("y") || row.has("z")) {
                return new int[] {
                        row.optInt("x", 0),
                        row.optInt("y", 0),
                        row.optInt("z", 0)
                };
            }
        }
        return null;
    }

    private static final class PublishResult {
        final String streamId;
        final long sequenceId;
        final String status;

        PublishResult(String streamId, long sequenceId, String status) {
            this.streamId = streamId;
            this.sequenceId = sequenceId;
            this.status = status;
        }

        JSONObject toJson() throws JSONException {
            return new JSONObject()
                    .put("stream_id", streamId)
                    .put("sequence_id", sequenceId)
                    .put("status", status);
        }
    }

    private static final class BrokerWebSocketClient implements Closeable {
        private final Socket socket;
        private final InputStream input;
        private final OutputStream output;

        private BrokerWebSocketClient(Socket socket) throws IOException {
            this.socket = socket;
            this.input = socket.getInputStream();
            this.output = socket.getOutputStream();
        }

        static BrokerWebSocketClient open(String host, int port, int timeoutMs) throws IOException {
            Socket socket = new Socket();
            socket.connect(new InetSocketAddress(host, port), timeoutMs);
            socket.setSoTimeout(timeoutMs);
            BrokerWebSocketClient client = new BrokerWebSocketClient(socket);
            String request = "GET " + MANIFOLD_BROKER_EVENTS_PATH + " HTTP/1.1\r\n"
                    + "Host: " + host + ":" + port + "\r\n"
                    + "Upgrade: websocket\r\n"
                    + "Connection: Upgrade\r\n"
                    + "Sec-WebSocket-Key: cnVzdHkteHItaG9zdGVzcy1wbWI=\r\n"
                    + "Sec-WebSocket-Version: 13\r\n"
                    + "\r\n";
            client.output.write(request.getBytes(StandardCharsets.US_ASCII));
            client.output.flush();
            String response = client.readHttpResponse();
            if (!response.startsWith("HTTP/1.1 101")) {
                throw new IOException("websocket handshake rejected: " + response.split("\\r?\\n", 2)[0]);
            }
            return client;
        }

        void sendJson(JSONObject value, int sequence) throws IOException {
            byte[] payload = value.toString().getBytes(StandardCharsets.UTF_8);
            byte[] frame = maskedTextFrame(payload, sequence);
            output.write(frame);
            output.flush();
        }

        JSONObject readJson(int timeoutMs) throws IOException, JSONException {
            int oldTimeout = socket.getSoTimeout();
            socket.setSoTimeout(Math.max(50, timeoutMs));
            try {
                while (true) {
                    Frame frame = readFrame();
                    if (frame.opcode == 0x1) {
                        return new JSONObject(new String(frame.payload, StandardCharsets.UTF_8));
                    }
                    if (frame.opcode == 0x8) {
                        return null;
                    }
                    if (frame.opcode == 0x9) {
                        sendFrame(frame.payload, 0xA);
                    }
                }
            } catch (SocketTimeoutException timeout) {
                return null;
            } finally {
                socket.setSoTimeout(oldTimeout);
            }
        }

        JSONObject readJson(int timeoutMs, Result result) throws IOException, JSONException {
            JSONObject message = readJson(timeoutMs);
            if (message != null) {
                result.acceptMessage(message);
            }
            return message;
        }

        private String readHttpResponse() throws IOException {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            int previous = -1;
            int current;
            while ((current = input.read()) >= 0 && buffer.size() < 4096) {
                buffer.write(current);
                byte[] bytes = buffer.toByteArray();
                if (previous == '\r' && current == '\n' && bytes.length >= 4
                        && bytes[bytes.length - 4] == '\r'
                        && bytes[bytes.length - 3] == '\n'
                        && bytes[bytes.length - 2] == '\r'
                        && bytes[bytes.length - 1] == '\n') {
                    break;
                }
                previous = current;
            }
            return buffer.toString(StandardCharsets.US_ASCII.name());
        }

        private Frame readFrame() throws IOException {
            int first = input.read();
            int second = input.read();
            if (first < 0 || second < 0) {
                throw new IOException("websocket closed");
            }
            int opcode = first & 0x0F;
            boolean masked = (second & 0x80) != 0;
            long len = second & 0x7F;
            if (len == 126) {
                len = ((long) input.read() << 8) | input.read();
            } else if (len == 127) {
                len = 0;
                for (int index = 0; index < 8; index++) {
                    len = (len << 8) | input.read();
                }
            }
            if (len > 1024 * 1024) {
                throw new IOException("websocket frame too large");
            }
            byte[] mask = new byte[4];
            if (masked) {
                readFully(mask);
            }
            byte[] payload = new byte[(int) len];
            readFully(payload);
            if (masked) {
                for (int index = 0; index < payload.length; index++) {
                    payload[index] = (byte) (payload[index] ^ mask[index % 4]);
                }
            }
            return new Frame(opcode, payload);
        }

        private void sendFrame(byte[] payload, int opcode) throws IOException {
            output.write(0x80 | (opcode & 0x0F));
            byte[] mask = mask(opcode + payload.length + 97);
            if (payload.length <= 125) {
                output.write(0x80 | payload.length);
            } else if (payload.length <= 65535) {
                output.write(0x80 | 126);
                output.write((payload.length >> 8) & 0xFF);
                output.write(payload.length & 0xFF);
            } else {
                output.write(0x80 | 127);
                long length = payload.length;
                for (int shift = 56; shift >= 0; shift -= 8) {
                    output.write((int) ((length >> shift) & 0xFF));
                }
            }
            output.write(mask);
            for (int index = 0; index < payload.length; index++) {
                output.write(payload[index] ^ mask[index % 4]);
            }
            output.flush();
        }

        private void readFully(byte[] target) throws IOException {
            int offset = 0;
            while (offset < target.length) {
                int read = input.read(target, offset, target.length - offset);
                if (read < 0) {
                    throw new IOException("websocket closed while reading payload");
                }
                offset += read;
            }
        }

        @Override
        public void close() throws IOException {
            try {
                sendFrame(new byte[0], 0x8);
            } catch (IOException ignored) {
            }
            socket.close();
        }
    }

    private static byte[] maskedTextFrame(byte[] payload, int sequence) {
        ByteArrayOutputStream frame = new ByteArrayOutputStream(payload.length + 16);
        frame.write(0x81);
        if (payload.length <= 125) {
            frame.write(0x80 | payload.length);
        } else if (payload.length <= 65535) {
            frame.write(0x80 | 126);
            frame.write((payload.length >> 8) & 0xFF);
            frame.write(payload.length & 0xFF);
        } else {
            frame.write(0x80 | 127);
            long length = payload.length;
            for (int shift = 56; shift >= 0; shift -= 8) {
                frame.write((int) ((length >> shift) & 0xFF));
            }
        }
        byte[] mask = mask(sequence);
        frame.write(mask, 0, mask.length);
        for (int index = 0; index < payload.length; index++) {
            frame.write(payload[index] ^ mask[index % 4]);
        }
        return frame.toByteArray();
    }

    private static byte[] mask(int sequence) {
        long value = 0xC2B2AE3D27D4EB4FL * Math.max(1, sequence);
        return new byte[] {
                (byte) value,
                (byte) (value >> 17),
                (byte) (value >> 33),
                (byte) (value >> 49)
        };
    }

    private static final class Frame {
        final int opcode;
        final byte[] payload;

        Frame(int opcode, byte[] payload) {
            this.opcode = opcode;
            this.payload = payload;
        }
    }
}
