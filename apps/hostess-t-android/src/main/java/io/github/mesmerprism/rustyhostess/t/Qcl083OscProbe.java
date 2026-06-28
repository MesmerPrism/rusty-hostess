package io.github.mesmerprism.rustyhostess.t;

import android.app.Activity;
import android.content.Intent;
import android.os.Handler;
import android.os.SystemClock;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.SocketException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

final class Qcl083OscProbe {
    private static final String SCHEMA = "rusty.hostess.android.qcl083_osc_probe.v1";
    private static final String DEFAULT_ADDRESS = "/rusty/qcl083";
    private static final String ACK_ADDRESS = "/rusty/qcl083/ack";
    private static final int DEFAULT_PORT = 18783;

    private Qcl083OscProbe() {
    }

    static void start(
            Activity activity,
            Intent intent,
            Handler handler,
            PlatformDebugTelemetryView telemetryView) {
        Runner runner = new Runner(activity, intent, handler, telemetryView);
        runner.start();
    }

    private static final class Runner implements Runnable {
        private final Activity activity;
        private final Intent intent;
        private final Handler handler;
        private final PlatformDebugTelemetryView telemetryView;
        private final String runId;
        private final String oscAddress;
        private final int listenPort;
        private final int expectedMessages;
        private final long timeoutMs;
        private final Instant startedAt = Instant.now();
        private final List<JSONObject> events = new ArrayList<>();
        private final List<String> errors = new ArrayList<>();
        private final List<String> issueCodes = new ArrayList<>();
        private final JSONArray packets = new JSONArray();

        private DatagramSocket socket;
        private boolean socketOpened = false;
        private boolean socketClosed = false;
        private int messagesReceived = 0;
        private int acksSent = 0;
        private int bytesReceived = 0;
        private int bytesWritten = 0;
        private boolean completed = false;

        Runner(
                Activity activity,
                Intent intent,
                Handler handler,
                PlatformDebugTelemetryView telemetryView) {
            this.activity = activity;
            this.intent = intent;
            this.handler = handler;
            this.telemetryView = telemetryView;
            this.runId = stringExtra(intent, "run_id", "qcl083-android-osc");
            this.oscAddress = stringExtra(intent, "osc_address", DEFAULT_ADDRESS);
            this.listenPort = Math.max(1, intExtra(intent, "listen_port", DEFAULT_PORT));
            this.expectedMessages = Math.max(1, intExtra(intent, "message_count", 16));
            this.timeoutMs = Math.max(3000L, longExtra(intent, "timeout_ms", 10000L));
        }

        void start() {
            recordEvent("probe.start", "pass", "QCL-083 OSC app-owned UDP server starting");
            Thread thread = new Thread(this, "qcl083-osc-probe");
            thread.start();
        }

        @Override
        public void run() {
            try {
                socket = new DatagramSocket(listenPort);
                socket.setSoTimeout(200);
                socketOpened = true;
                recordEvent("osc.server_socket.open", "pass", "OSC UDP socket bound on port " + listenPort);
                receiveMessages();
                complete(messagesReceived >= expectedMessages && acksSent >= expectedMessages ? "pass" : "fail");
            } catch (SocketException ex) {
                fail("hostess.issue.connectivity_probe.osc_android_socket_failed", messageOrFallback(ex, "OSC UDP socket failed"));
            } catch (IOException ex) {
                fail("hostess.issue.connectivity_probe.osc_android_exchange_failed", messageOrFallback(ex, "OSC UDP exchange failed"));
            }
        }

        private void receiveMessages() throws IOException {
            long deadline = System.currentTimeMillis() + timeoutMs;
            byte[] buffer = new byte[8192];
            while (!completed && messagesReceived < expectedMessages && System.currentTimeMillis() < deadline) {
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                try {
                    socket.receive(packet);
                } catch (java.net.SocketTimeoutException ignored) {
                    continue;
                }
                long questReceivedNs = SystemClock.elapsedRealtimeNanos();
                bytesReceived += packet.getLength();
                OscMessage message = parseOscMessage(packet.getData(), packet.getLength());
                if (!message.valid || !oscAddress.equals(message.address) || message.sequence < 0) {
                    issueCodes.add("hostess.issue.connectivity_probe.osc_android_packet_malformed");
                    recordEvent("osc.payload_exchange", "fail", "malformed OSC packet ignored");
                    continue;
                }
                messagesReceived += 1;
                JSONObject marker = parseMarker(message.marker);
                long questSendNs = SystemClock.elapsedRealtimeNanos();
                JSONObject ackMarker = new JSONObject();
                try {
                    ackMarker.put("run_id", runId);
                    ackMarker.put("status", "ack");
                    ackMarker.put("sequence", message.sequence);
                    ackMarker.put("host_send_monotonic_ns", marker.optLong("host_send_monotonic_ns", 0L));
                    ackMarker.put("quest_received_elapsed_ns", questReceivedNs);
                    ackMarker.put("quest_send_elapsed_ns", questSendNs);
                    ackMarker.put("quest_wall_time_ms", System.currentTimeMillis());
                } catch (JSONException ignored) {
                }
                byte[] reply = buildOscMessage(ACK_ADDRESS, message.sequence, ackMarker.toString());
                socket.send(new DatagramPacket(reply, reply.length, packet.getAddress(), packet.getPort()));
                bytesWritten += reply.length;
                acksSent += 1;
                recordPacket(message, marker, questReceivedNs, questSendNs);
                recordEvent("osc.payload_exchange", "pass", "OSC message " + message.sequence + " acknowledged");
            }
            if (messagesReceived < expectedMessages) {
                issueCodes.add("hostess.issue.connectivity_probe.osc_android_timeout");
                errors.add("Timed out waiting for OSC payload messages");
                recordEvent("osc.payload_exchange", "fail", "message timeout");
            }
        }

        private void recordPacket(
                OscMessage message,
                JSONObject marker,
                long questReceivedNs,
                long questSendNs) {
            JSONObject packet = new JSONObject();
            try {
                packet.put("sequence", message.sequence);
                packet.put("address", message.address);
                packet.put("marker_run_id", marker.optString("run_id", ""));
                packet.put("host_send_monotonic_ns", marker.optLong("host_send_monotonic_ns", 0L));
                packet.put("quest_received_elapsed_ns", questReceivedNs);
                packet.put("quest_send_elapsed_ns", questSendNs);
            } catch (JSONException ignored) {
            }
            packets.put(packet);
        }

        private void complete(String status) {
            if (completed) {
                return;
            }
            completed = true;
            cleanup();
            writeEvidence(status);
            handler.post(() -> telemetryView.setRunState(status, "qcl083_osc", new ArrayList<>()));
        }

        private void fail(String issueCode, String message) {
            errors.add(message);
            issueCodes.add(issueCode);
            recordEvent("probe.failure", "fail", message);
            complete("fail");
        }

        private void cleanup() {
            if (socket != null && !socketClosed) {
                socket.close();
                socketClosed = true;
            }
            recordEvent("probe.cleanup", "pass", "OSC UDP socket cleanup attempted");
        }

        private void writeEvidence(String status) {
            Instant endedAt = Instant.now();
            try {
                JSONObject evidence = new JSONObject();
                evidence.put("schema", SCHEMA);
                evidence.put("schema_version", 1);
                evidence.put("run_id", runId);
                evidence.put("status", status);
                evidence.put("started_at_utc", startedAt.toString());
                evidence.put("ended_at_utc", endedAt.toString());
                evidence.put("role", "quest_osc_udp_server");
                evidence.put("authority", "app_owned_runtime_osc_udp_server");
                evidence.put("listen_host", "0.0.0.0");
                evidence.put("listen_port", listenPort);
                evidence.put("osc_address", oscAddress);
                evidence.put("ack_address", ACK_ADDRESS);
                evidence.put("messages_expected", expectedMessages);
                evidence.put("messages_received", messagesReceived);
                evidence.put("messages_acknowledged", acksSent);
                evidence.put("bytes_received", bytesReceived);
                evidence.put("bytes_written", bytesWritten);
                evidence.put("osc_server", new JSONObject()
                        .put("socket_opened", socketOpened)
                        .put("socket_closed", socketClosed));
                evidence.put("packets", packets);
                evidence.put("events", new JSONArray(events));
                evidence.put("errors", new JSONArray(errors));
                evidence.put("issue_codes", new JSONArray(issueCodes));
                File root = new File(activity.getExternalFilesDir(null), "hostess-t/evidence/qcl083-osc");
                if (!root.exists() && !root.mkdirs()) {
                    throw new IOException("could not create QCL-083 evidence folder");
                }
                writeText(new File(root, "latest.json"), evidence.toString(2));
            } catch (IOException | JSONException ignored) {
                // UI state remains the fallback when evidence cannot be written.
            }
        }

        private void recordEvent(String phase, String status, String evidence) {
            JSONObject event = new JSONObject();
            try {
                event.put("phase", phase);
                event.put("status", status);
                event.put("evidence", evidence);
                event.put("observed_at_utc", Instant.now().toString());
            } catch (JSONException ignored) {
            }
            events.add(event);
        }

        private static JSONObject parseMarker(String marker) {
            try {
                return new JSONObject(marker == null ? "{}" : marker);
            } catch (JSONException ignored) {
                return new JSONObject();
            }
        }

        private static String messageOrFallback(Exception ex, String fallback) {
            return ex.getMessage() == null ? fallback : ex.getMessage();
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

        private static long longExtra(Intent intent, String name, long fallback) {
            if (!intent.hasExtra(name) || intent.getExtras() == null) {
                return fallback;
            }
            try {
                return Long.parseLong(String.valueOf(intent.getExtras().get(name)).trim());
            } catch (NumberFormatException ignored) {
                return fallback;
            }
        }

        private static void writeText(File path, String text) throws IOException {
            try (FileOutputStream out = new FileOutputStream(path)) {
                out.write(text.getBytes(StandardCharsets.UTF_8));
            }
        }
    }

    private static byte[] buildOscMessage(String address, int sequence, String marker) {
        byte[] addressBytes = oscString(address);
        byte[] typeBytes = oscString(",is");
        byte[] markerBytes = oscString(marker);
        ByteBuffer buffer = ByteBuffer.allocate(addressBytes.length + typeBytes.length + 4 + markerBytes.length)
                .order(ByteOrder.BIG_ENDIAN);
        buffer.put(addressBytes);
        buffer.put(typeBytes);
        buffer.putInt(sequence);
        buffer.put(markerBytes);
        return buffer.array();
    }

    private static byte[] oscString(String value) {
        byte[] raw = (value == null ? "" : value).getBytes(StandardCharsets.UTF_8);
        int lengthWithNull = raw.length + 1;
        int paddedLength = lengthWithNull + ((4 - (lengthWithNull % 4)) % 4);
        byte[] padded = new byte[paddedLength];
        System.arraycopy(raw, 0, padded, 0, raw.length);
        return padded;
    }

    private static OscMessage parseOscMessage(byte[] payload, int length) {
        try {
            ReadString address = readOscString(payload, length, 0);
            ReadString typeTags = readOscString(payload, length, address.nextOffset);
            if (!typeTags.value.startsWith(",i") || length < typeTags.nextOffset + 4) {
                return OscMessage.invalid(address.value);
            }
            int sequence = ByteBuffer.wrap(payload, typeTags.nextOffset, 4).order(ByteOrder.BIG_ENDIAN).getInt();
            int offset = typeTags.nextOffset + 4;
            String marker = "";
            if (typeTags.value.indexOf('s', 2) >= 0 && offset < length) {
                marker = readOscString(payload, length, offset).value;
            }
            return new OscMessage(true, address.value, typeTags.value, sequence, marker);
        } catch (RuntimeException ex) {
            return OscMessage.invalid("");
        }
    }

    private static ReadString readOscString(byte[] payload, int length, int offset) {
        int end = offset;
        while (end < length && payload[end] != 0) {
            end += 1;
        }
        if (end >= length) {
            throw new IllegalArgumentException("unterminated OSC string");
        }
        String value = new String(payload, offset, end - offset, StandardCharsets.UTF_8);
        int next = end + 1;
        while (next % 4 != 0) {
            next += 1;
        }
        if (next > length) {
            throw new IllegalArgumentException("OSC string padding exceeds packet");
        }
        return new ReadString(value, next);
    }

    private static final class ReadString {
        final String value;
        final int nextOffset;

        ReadString(String value, int nextOffset) {
            this.value = value;
            this.nextOffset = nextOffset;
        }
    }

    private static final class OscMessage {
        final boolean valid;
        final String address;
        final String typeTags;
        final int sequence;
        final String marker;

        OscMessage(boolean valid, String address, String typeTags, int sequence, String marker) {
            this.valid = valid;
            this.address = address;
            this.typeTags = typeTags;
            this.sequence = sequence;
            this.marker = marker;
        }

        static OscMessage invalid(String address) {
            return new OscMessage(false, address, "", -1, "");
        }
    }
}
