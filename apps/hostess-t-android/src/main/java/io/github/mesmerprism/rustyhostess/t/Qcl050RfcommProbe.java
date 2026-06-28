package io.github.mesmerprism.rustyhostess.t;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothServerSocket;
import android.bluetooth.BluetoothSocket;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Handler;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

final class Qcl050RfcommProbe {
    static final UUID SERVICE_UUID = UUID.fromString("7b2a0050-7c4d-4f4c-9b16-515100515100");
    private static final String SERVICE_NAME = "Rusty Hostess QCL-050 RFCOMM";
    private static final String SCHEMA = "rusty.hostess.android.qcl050_rfcomm_probe.v1";

    private Qcl050RfcommProbe() {
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
        private final int expectedMessages;
        private final long timeoutMs;
        private final Instant startedAt = Instant.now();
        private final List<JSONObject> events = new ArrayList<>();
        private final List<String> errors = new ArrayList<>();
        private final List<String> issueCodes = new ArrayList<>();
        private final List<String> receivedPayloads = new ArrayList<>();

        private BluetoothServerSocket serverSocket;
        private BluetoothSocket clientSocket;
        private boolean serverSocketOpened = false;
        private boolean serverSocketClosed = false;
        private boolean clientSocketAccepted = false;
        private boolean clientSocketClosed = false;
        private int messagesReceived = 0;
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
            this.runId = stringExtra(intent, "run_id", "qcl050-android-rfcomm");
            this.expectedMessages = Math.max(1, intExtra(intent, "message_count", 3));
            this.timeoutMs = Math.max(3000L, longExtra(intent, "timeout_ms", 20000L));
        }

        void start() {
            recordEvent("probe.start", "pass", "QCL-050 RFCOMM app-owned server starting");
            String[] missing = missingPermissions();
            if (missing.length > 0) {
                fail("rejection.permission_missing", "Missing permission: " + missing[0]);
                return;
            }
            Thread thread = new Thread(this, "qcl050-rfcomm-probe");
            thread.start();
        }

        @Override
        public void run() {
            BluetoothManager manager = (BluetoothManager) activity.getSystemService(Activity.BLUETOOTH_SERVICE);
            BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
            if (adapter == null || !adapter.isEnabled()) {
                fail("rejection.backend_missing", "Bluetooth adapter unavailable or disabled");
                return;
            }
            try {
                serverSocket = adapter.listenUsingRfcommWithServiceRecord(SERVICE_NAME, SERVICE_UUID);
                serverSocketOpened = true;
                recordEvent("rfcomm.server_socket.open", "pass", "RFCOMM server socket opened");
                clientSocket = serverSocket.accept((int) timeoutMs);
                if (clientSocket == null) {
                    fail("rejection.service_discovery_failed", "RFCOMM accept returned no client socket");
                    return;
                }
                clientSocketAccepted = true;
                recordEvent("rfcomm.client.accept", "pass", "RFCOMM client socket accepted; address redacted");
                exchangeMessages(clientSocket.getInputStream(), clientSocket.getOutputStream());
                complete(messagesReceived >= expectedMessages ? "pass" : "fail");
            } catch (IOException ex) {
                fail("rejection.service_discovery_failed", ex.getMessage() == null ? "RFCOMM socket failed" : ex.getMessage());
            }
        }

        private void exchangeMessages(InputStream input, OutputStream output) throws IOException {
            long deadline = System.currentTimeMillis() + timeoutMs;
            StringBuilder line = new StringBuilder();
            while (!completed && messagesReceived < expectedMessages && System.currentTimeMillis() < deadline) {
                int available = input.available();
                if (available <= 0) {
                    sleepQuietly(20L);
                    continue;
                }
                int next = input.read();
                if (next < 0) {
                    break;
                }
                if (next == '\n') {
                    handleLine(line.toString(), output);
                    line.setLength(0);
                } else if (next != '\r') {
                    line.append((char) next);
                }
            }
            if (messagesReceived < expectedMessages) {
                issueCodes.add("rejection.handoff_first_frame_timeout");
                errors.add("Timed out waiting for RFCOMM payload messages");
                recordEvent("rfcomm.payload_exchange", "fail", "message timeout");
            }
        }

        private void handleLine(String line, OutputStream output) throws IOException {
            byte[] payload = line.getBytes(StandardCharsets.UTF_8);
            messagesReceived += 1;
            bytesReceived += payload.length;
            receivedPayloads.add(line);
            String reply = "schema=" + SCHEMA
                    + ";runId=" + runId
                    + ";status=echo"
                    + ";sequence=" + messagesReceived
                    + ";received=" + messagesReceived
                    + "\n";
            byte[] replyBytes = reply.getBytes(StandardCharsets.UTF_8);
            output.write(replyBytes);
            output.flush();
            bytesWritten += replyBytes.length;
            recordEvent("rfcomm.payload_exchange", "pass", "message " + messagesReceived + " read/write completed");
        }

        private String[] missingPermissions() {
            List<String> missing = new ArrayList<>();
            if (android.os.Build.VERSION.SDK_INT >= 31
                    && activity.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                    != PackageManager.PERMISSION_GRANTED) {
                missing.add(Manifest.permission.BLUETOOTH_CONNECT);
            }
            return missing.toArray(new String[0]);
        }

        private void complete(String status) {
            if (completed) {
                return;
            }
            completed = true;
            cleanup();
            writeEvidence(status);
            handler.post(() -> telemetryView.setRunState(status, "qcl050_rfcomm", new ArrayList<>()));
        }

        private void fail(String issueCode, String message) {
            errors.add(message);
            issueCodes.add(issueCode);
            recordEvent("probe.failure", "fail", message);
            complete("fail");
        }

        private void cleanup() {
            if (clientSocket != null && !clientSocketClosed) {
                try {
                    clientSocket.close();
                } catch (IOException ignored) {
                }
                clientSocketClosed = true;
            }
            if (serverSocket != null && !serverSocketClosed) {
                try {
                    serverSocket.close();
                } catch (IOException ignored) {
                }
                serverSocketClosed = true;
            }
            recordEvent("probe.cleanup", "pass", "RFCOMM sockets cleanup attempted");
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
                evidence.put("role", "quest_rfcomm_server");
                evidence.put("authority", "app_owned_runtime_rfcomm_server");
                evidence.put("service_uuid", SERVICE_UUID.toString());
                evidence.put("messages_expected", expectedMessages);
                evidence.put("messages_received", messagesReceived);
                evidence.put("bytes_received", bytesReceived);
                evidence.put("bytes_written", bytesWritten);
                evidence.put("client_addresses_redacted", true);
                evidence.put("permissions", permissionStatus());
                evidence.put("rfcomm_server", new JSONObject()
                        .put("server_socket_opened", serverSocketOpened)
                        .put("server_socket_closed", serverSocketClosed)
                        .put("client_socket_accepted", clientSocketAccepted)
                        .put("client_socket_closed", clientSocketClosed));
                evidence.put("payloads", redactedPayloads());
                evidence.put("events", new JSONArray(events));
                evidence.put("errors", new JSONArray(errors));
                evidence.put("issue_codes", new JSONArray(issueCodes));
                File root = new File(activity.getExternalFilesDir(null), "hostess-t/evidence/qcl050-rfcomm");
                if (!root.exists() && !root.mkdirs()) {
                    throw new IOException("could not create QCL-050 evidence folder");
                }
                writeText(new File(root, "latest.json"), evidence.toString(2));
            } catch (IOException | JSONException ignored) {
                // UI state remains the fallback when evidence cannot be written.
            }
        }

        private JSONObject permissionStatus() throws JSONException {
            JSONObject permissions = new JSONObject();
            permissions.put("bluetooth_connect", permissionGranted(Manifest.permission.BLUETOOTH_CONNECT));
            permissions.put("address_redacted", true);
            return permissions;
        }

        private boolean permissionGranted(String permission) {
            if (android.os.Build.VERSION.SDK_INT < 31
                    && Manifest.permission.BLUETOOTH_CONNECT.equals(permission)) {
                return true;
            }
            return activity.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
        }

        private JSONArray redactedPayloads() {
            JSONArray payloads = new JSONArray();
            for (int index = 0; index < receivedPayloads.size(); index += 1) {
                JSONObject payload = new JSONObject();
                try {
                    payload.put("sequence", index + 1);
                    payload.put("byte_count", receivedPayloads.get(index).getBytes(StandardCharsets.UTF_8).length);
                    payload.put("redacted", false);
                    payload.put("text", receivedPayloads.get(index));
                } catch (JSONException ignored) {
                }
                payloads.put(payload);
            }
            return payloads;
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

        private static void sleepQuietly(long millis) {
            try {
                Thread.sleep(millis);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
            }
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
}
