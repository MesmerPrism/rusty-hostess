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
    static final String EXTERNAL_STREAM_POLAR_ACC = "bio:polar_acc";
    static final String STREAM_OBJECT_POSE = "stream.motion.object_pose";
    static final String STREAM_BREATH_VOLUME = "stream.breath.volume";
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
        Result result = new Result(host, port, limit, receiptListenMs);
        List<JSONObject> breathSamples = selectSamples(routeReport.optJSONArray("breath_samples"), limit);
        List<JSONObject> feedbackSamples = selectSamples(routeReport.optJSONArray("feedback_samples"), limit);
        result.breathRequestedCount = routeReport.optJSONArray("breath_samples") == null
                ? 0
                : routeReport.optJSONArray("breath_samples").length();
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
                PublishResult publish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_VOLUME,
                        sample.optLong("sequence_id", index + 1),
                        breathPayload(sample, index + 1),
                        sequence++);
                result.breathPublishResults.put(publish.toJson());
                if ("pass".equals(publish.status)) {
                    result.breathPublishedCount += 1;
                }
            }
            for (int index = 0; index < feedbackSamples.size(); index++) {
                JSONObject sample = feedbackSamples.get(index);
                PublishResult publish = publishStreamSample(
                        client,
                        result,
                        STREAM_BREATH_FEEDBACK_STATE,
                        sample.optLong("sequence_id", index + 1),
                        feedbackPayload(sample, index + 1),
                        sequence++);
                result.feedbackPublishResults.put(publish.toJson());
                if ("pass".equals(publish.status)) {
                    result.feedbackPublishedCount += 1;
                }
            }

            long deadline = System.currentTimeMillis() + Math.max(0, receiptListenMs);
            while (System.currentTimeMillis() < deadline
                    && result.feedbackReceiptCount < result.feedbackPublishedCount) {
                int timeout = (int) Math.max(50, Math.min(250, deadline - System.currentTimeMillis()));
                client.readJson(timeout, result);
            }
        }
        result.status = result.feedbackPublishedCount > 0
                && result.feedbackReceiptCount == result.feedbackPublishedCount
                ? "pass"
                : "fail";
        if (!"pass".equals(result.status) && result.feedbackReceiptCount < result.feedbackPublishedCount) {
            result.errors.put("issue.makepad_feedback_receipts_missing");
        }
        return result;
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
                .put("schema", "rusty.xr.broker.command.v1")
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
        String requestId = "quest-pmb-simulated-live-" + command.replace('.', '-') + "-" + sequence;
        client.sendJson(new JSONObject()
                .put("type", "command")
                .put("schema", "rusty.xr.broker.command.v1")
                .put("request_id", requestId)
                .put("command", command)
                .put("params", params)
                .put("client_id", "app.rusty_hostess_t.quest.pmb_simulated_live")
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

    private static JSONObject breathPayload(JSONObject sample, int fallbackSequence) throws JSONException {
        int sequence = (int) sample.optLong("sequence_id", fallbackSequence);
        return new JSONObject()
                .put("schema", "rusty.manifold.breath.volume.v1")
                .put("stream_id", STREAM_BREATH_VOLUME)
                .put("sequence_id", sequence)
                .put("source_id", sample.optString("source_id", "source.unknown"))
                .put("input_stream_id", sample.optString("input_stream_id", ""))
                .put("normalized_stream_id", sample.optString("normalized_stream_id", ""))
                .put("sample_time_unix_ns", sampleTimeUnixNs(sample))
                .put("volume01", sample.optDouble("volume01", 0.0))
                .put("phase", sample.optString("phase", "unknown"))
                .put("quality", sample.optString("quality", "unknown"))
                .put("tracking01", sample.optDouble("tracking01", 0.0))
                .put("processor_id", "processor.projected_motion_breath.quest_simulated_live")
                .put("publisher", "app.rusty_hostess_t.quest")
                .put("computation_authority", "quest_hostess_android_app");
    }

    private static JSONObject feedbackPayload(JSONObject sample, int fallbackSequence) throws JSONException {
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
                .put("processor_id", "processor.projected_motion_breath.quest_simulated_live")
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

        JSONObject toJson() throws JSONException {
            return new JSONObject()
                    .put("schema", "rusty.hostess.projected_motion_breath.quest_physical_input_capture_report.v1")
                    .put("status", status)
                    .put("broker_host", brokerHost)
                    .put("broker_port", brokerPort)
                    .put("broker_connected", brokerConnected)
                    .put("broker_transport_used", brokerConnected)
                    .put("events_jsonl", eventsJsonl)
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

        void acceptCaptureMessage(JSONObject message, BufferedWriter writer) throws IOException, JSONException {
            if (!"stream_event".equals(message.optString("type"))) {
                return;
            }
            String stream = streamId(message);
            if (!EXTERNAL_STREAM_POLAR_ACC.equals(stream) && !STREAM_OBJECT_POSE.equals(stream)) {
                return;
            }
            acceptObservedMessage(message);
            if (STREAM_OBJECT_POSE.equals(stream) && !isUsableObjectPose(message)) {
                return;
            }
            writer.write(message.toString());
            writer.newLine();
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
        final JSONArray feedbackPublishResults = new JSONArray();
        final JSONArray commandReplies = new JSONArray();
        final JSONArray receiptEvents = new JSONArray();
        final JSONArray errors = new JSONArray();
        String status = "pending";
        boolean brokerConnected = false;
        int breathRequestedCount = 0;
        int feedbackRequestedCount = 0;
        int breathPublishedCount = 0;
        int feedbackPublishedCount = 0;
        int feedbackReceiptCount = 0;

        Result(String brokerHost, int brokerPort, int publishLimit, int receiptListenMs) {
            this.brokerHost = brokerHost;
            this.brokerPort = brokerPort;
            this.publishLimit = publishLimit;
            this.receiptListenMs = receiptListenMs;
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
                    .put("breath_requested_count", breathRequestedCount)
                    .put("feedback_requested_count", feedbackRequestedCount)
                    .put("breath_published_count", breathPublishedCount)
                    .put("feedback_published_count", feedbackPublishedCount)
                    .put("feedback_receipt_count", feedbackReceiptCount)
                    .put("receipt_stream_id", STREAM_BREATH_FEEDBACK_RECEIPT)
                    .put("breath_results", breathPublishResults)
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
            receiptEvents.put(message);
        }
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
            String request = "GET /rustyxr/v1/events HTTP/1.1\r\n"
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
