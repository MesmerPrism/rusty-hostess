package io.github.mesmerprism.rustyhostess.t;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattServer;
import android.bluetooth.BluetoothGattServerCallback;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.AdvertiseCallback;
import android.bluetooth.le.AdvertiseData;
import android.bluetooth.le.AdvertiseSettings;
import android.bluetooth.le.BluetoothLeAdvertiser;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Handler;
import android.os.ParcelUuid;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

final class Qcl051BleGattProbe {
    static final UUID SERVICE_UUID = UUID.fromString("7b2a0001-7c4d-4f4c-9b16-515100515100");
    static final UUID CONTROL_UUID = UUID.fromString("7b2a0002-7c4d-4f4c-9b16-515100515100");
    static final UUID STATUS_UUID = UUID.fromString("7b2a0003-7c4d-4f4c-9b16-515100515100");
    private static final UUID CCCD_UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");
    private static final String SCHEMA = "rusty.hostess.android.qcl051_ble_gatt_probe.v1";

    private Qcl051BleGattProbe() {
    }

    static void start(
            Activity activity,
            Intent intent,
            Handler handler,
            PlatformDebugTelemetryView telemetryView) {
        Runner runner = new Runner(activity, intent, handler, telemetryView);
        runner.start();
    }

    private static final class Runner {
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

        private BluetoothLeAdvertiser advertiser;
        private BluetoothGattServer gattServer;
        private BluetoothGattCharacteristic statusCharacteristic;
        private boolean advertisingStarted = false;
        private boolean advertisingStopped = false;
        private boolean gattServerOpened = false;
        private boolean gattServerClosed = false;
        private boolean serviceAdded = false;
        private int serviceAddStatus = Integer.MIN_VALUE;
        private int bytesReceived = 0;
        private int bytesRead = 0;
        private int writeRequests = 0;
        private int readRequests = 0;
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
            this.runId = stringExtra(intent, "run_id", "qcl051-android-ble-gatt");
            this.expectedMessages = Math.max(1, intExtra(intent, "message_count", 3));
            this.timeoutMs = Math.max(3000L, longExtra(intent, "timeout_ms", 20000L));
        }

        void start() {
            recordEvent("probe.start", "pass", "QCL-051 BLE/GATT app-owned server starting");
            String[] missing = missingPermissions();
            if (missing.length > 0) {
                fail("rejection.permission_missing", "Missing permission: " + missing[0]);
                return;
            }

            BluetoothManager manager = (BluetoothManager) activity.getSystemService(Activity.BLUETOOTH_SERVICE);
            BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
            if (adapter == null || !adapter.isEnabled()) {
                fail("rejection.backend_missing", "Bluetooth adapter unavailable or disabled");
                return;
            }
            advertiser = adapter.getBluetoothLeAdvertiser();
            if (advertiser == null || !adapter.isMultipleAdvertisementSupported()) {
                fail("rejection.service_discovery_failed", "BLE advertising is not available on this device");
                return;
            }

            gattServer = manager.openGattServer(activity, callback);
            if (gattServer == null) {
                fail("rejection.service_cache_failed", "Could not open GATT server");
                return;
            }
            gattServerOpened = true;
            recordEvent("gatt_server.open", "pass", "GATT server opened");

            BluetoothGattService service = new BluetoothGattService(
                    SERVICE_UUID,
                    BluetoothGattService.SERVICE_TYPE_PRIMARY);
            BluetoothGattCharacteristic control = new BluetoothGattCharacteristic(
                    CONTROL_UUID,
                    BluetoothGattCharacteristic.PROPERTY_WRITE | BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE,
                    BluetoothGattCharacteristic.PERMISSION_WRITE);
            statusCharacteristic = new BluetoothGattCharacteristic(
                    STATUS_UUID,
                    BluetoothGattCharacteristic.PROPERTY_READ | BluetoothGattCharacteristic.PROPERTY_NOTIFY,
                    BluetoothGattCharacteristic.PERMISSION_READ);
            statusCharacteristic.addDescriptor(new BluetoothGattDescriptor(
                    CCCD_UUID,
                    BluetoothGattDescriptor.PERMISSION_READ | BluetoothGattDescriptor.PERMISSION_WRITE));
            statusCharacteristic.setValue(statusPayload("ready", 0));
            service.addCharacteristic(control);
            service.addCharacteristic(statusCharacteristic);

            if (!gattServer.addService(service)) {
                fail("rejection.service_cache_failed", "Could not add GATT service");
                return;
            }
            handler.postDelayed(() -> {
                if (!completed) {
                    fail("rejection.handoff_first_frame_timeout", "Timed out waiting for Windows GATT payload writes");
                }
            }, timeoutMs);
        }

        private final BluetoothGattServerCallback callback = new BluetoothGattServerCallback() {
            @Override
            public void onServiceAdded(int status, BluetoothGattService service) {
                serviceAddStatus = status;
                serviceAdded = status == BluetoothGatt.GATT_SUCCESS;
                recordEvent(
                        "gatt_server.service_added",
                        serviceAdded ? "pass" : "fail",
                        "service_add_status=" + status);
                if (serviceAdded) {
                    startAdvertising();
                } else {
                    fail("rejection.service_cache_failed", "GATT service add failed: " + status);
                }
            }

            @Override
            public void onCharacteristicWriteRequest(
                    BluetoothDevice device,
                    int requestId,
                    BluetoothGattCharacteristic characteristic,
                    boolean preparedWrite,
                    boolean responseNeeded,
                    int offset,
                    byte[] value) {
                if (!CONTROL_UUID.equals(characteristic.getUuid())) {
                    if (responseNeeded && gattServer != null) {
                        gattServer.sendResponse(device, requestId, BluetoothGatt.GATT_FAILURE, offset, null);
                    }
                    return;
                }
                byte[] payload = value == null ? new byte[0] : value;
                writeRequests += 1;
                bytesReceived += payload.length;
                String text = new String(payload, StandardCharsets.UTF_8);
                receivedPayloads.add(text);
                recordEvent("gatt.write", "pass", "received bounded control payload " + writeRequests);
                if (statusCharacteristic != null) {
                    statusCharacteristic.setValue(statusPayload("echo", writeRequests));
                }
                if (responseNeeded && gattServer != null) {
                    gattServer.sendResponse(device, requestId, BluetoothGatt.GATT_SUCCESS, offset, null);
                }
                if (gattServer != null && statusCharacteristic != null) {
                    gattServer.notifyCharacteristicChanged(device, statusCharacteristic, false);
                }
                if (writeRequests >= expectedMessages) {
                    scheduleCompletionGrace();
                }
            }

            @Override
            public void onCharacteristicReadRequest(
                    BluetoothDevice device,
                    int requestId,
                    int offset,
                    BluetoothGattCharacteristic characteristic) {
                if (!STATUS_UUID.equals(characteristic.getUuid()) || statusCharacteristic == null) {
                    if (gattServer != null) {
                        gattServer.sendResponse(device, requestId, BluetoothGatt.GATT_FAILURE, offset, null);
                    }
                    return;
                }
                byte[] payload = statusCharacteristic.getValue();
                bytesRead += payload == null ? 0 : payload.length;
                readRequests += 1;
                if (gattServer != null) {
                    gattServer.sendResponse(device, requestId, BluetoothGatt.GATT_SUCCESS, offset, payload);
                }
                recordEvent("gatt.read", "pass", "status characteristic read " + readRequests);
                if (writeRequests >= expectedMessages && readRequests >= expectedMessages) {
                    complete("pass");
                }
            }
        };

        private final AdvertiseCallback advertiseCallback = new AdvertiseCallback() {
            @Override
            public void onStartSuccess(AdvertiseSettings settingsInEffect) {
                advertisingStarted = true;
                recordEvent("ble_advertise.start", "pass", "BLE advertising started");
            }

            @Override
            public void onStartFailure(int errorCode) {
                fail("rejection.service_discovery_failed", "BLE advertising failed: " + errorCode);
            }
        };

        private void startAdvertising() {
            AdvertiseSettings settings = new AdvertiseSettings.Builder()
                    .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
                    .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
                    .setConnectable(true)
                    .setTimeout(0)
                    .build();
            AdvertiseData data = new AdvertiseData.Builder()
                    .addServiceUuid(new ParcelUuid(SERVICE_UUID))
                    .setIncludeTxPowerLevel(false)
                    .setIncludeDeviceName(false)
                    .build();
            advertiser.startAdvertising(settings, data, advertiseCallback);
        }

        private byte[] statusPayload(String status, int sequence) {
            String text = "schema=" + SCHEMA
                    + ";runId=" + runId
                    + ";status=" + status
                    + ";sequence=" + sequence
                    + ";received=" + writeRequests;
            return text.getBytes(StandardCharsets.UTF_8);
        }

        private String[] missingPermissions() {
            List<String> missing = new ArrayList<>();
            if (android.os.Build.VERSION.SDK_INT >= 31) {
                if (activity.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                        != PackageManager.PERMISSION_GRANTED) {
                    missing.add(Manifest.permission.BLUETOOTH_CONNECT);
                }
                if (activity.checkSelfPermission(Manifest.permission.BLUETOOTH_ADVERTISE)
                        != PackageManager.PERMISSION_GRANTED) {
                    missing.add(Manifest.permission.BLUETOOTH_ADVERTISE);
                }
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
            handler.post(() -> telemetryView.setRunState(status, "qcl051_ble_gatt", new ArrayList<>()));
        }

        private void scheduleCompletionGrace() {
            if (readRequests >= expectedMessages) {
                complete("pass");
                return;
            }
            handler.postDelayed(() -> {
                if (!completed && writeRequests >= expectedMessages) {
                    complete("pass");
                }
            }, 1500L);
        }

        private void fail(String issueCode, String message) {
            errors.add(message);
            issueCodes.add(issueCode);
            recordEvent("probe.failure", "fail", message);
            complete("fail");
        }

        private void cleanup() {
            if (advertiser != null && advertisingStarted && !advertisingStopped) {
                try {
                    advertiser.stopAdvertising(advertiseCallback);
                } catch (RuntimeException ignored) {
                }
                advertisingStopped = true;
            }
            if (gattServer != null && !gattServerClosed) {
                try {
                    gattServer.close();
                } catch (RuntimeException ignored) {
                }
                gattServerClosed = true;
            }
            recordEvent("probe.cleanup", "pass", "BLE advertiser and GATT server cleanup attempted");
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
                evidence.put("role", "quest_ble_gatt_server");
                evidence.put("authority", "app_owned_runtime_ble_gatt_server");
                evidence.put("service_uuid", SERVICE_UUID.toString());
                evidence.put("control_characteristic_uuid", CONTROL_UUID.toString());
                evidence.put("status_characteristic_uuid", STATUS_UUID.toString());
                evidence.put("messages_expected", expectedMessages);
                evidence.put("messages_received", writeRequests);
                evidence.put("read_requests", readRequests);
                evidence.put("bytes_received", bytesReceived);
                evidence.put("bytes_read", bytesRead);
                evidence.put("client_addresses_redacted", true);
                evidence.put("permissions", permissionStatus());
                evidence.put("advertising", new JSONObject()
                        .put("started", advertisingStarted)
                        .put("stopped", advertisingStopped));
                evidence.put("gatt_server", new JSONObject()
                        .put("opened", gattServerOpened)
                        .put("closed", gattServerClosed)
                        .put("service_added", serviceAdded)
                        .put("service_add_status", serviceAddStatus == Integer.MIN_VALUE ? JSONObject.NULL : serviceAddStatus));
                evidence.put("payloads", redactedPayloads());
                evidence.put("events", new JSONArray(events));
                evidence.put("errors", new JSONArray(errors));
                evidence.put("issue_codes", new JSONArray(issueCodes));
                File root = new File(activity.getExternalFilesDir(null), "hostess-t/evidence/qcl051-ble-gatt");
                if (!root.exists() && !root.mkdirs()) {
                    throw new IOException("could not create QCL-051 evidence folder");
                }
                writeText(new File(root, "latest.json"), evidence.toString(2));
            } catch (IOException | JSONException ignored) {
                // UI state remains the fallback when evidence cannot be written.
            }
        }

        private JSONObject permissionStatus() throws JSONException {
            JSONObject permissions = new JSONObject();
            permissions.put("bluetooth_connect", permissionGranted(Manifest.permission.BLUETOOTH_CONNECT));
            permissions.put("bluetooth_advertise", permissionGranted(Manifest.permission.BLUETOOTH_ADVERTISE));
            permissions.put("address_redacted", true);
            return permissions;
        }

        private boolean permissionGranted(String permission) {
            if (android.os.Build.VERSION.SDK_INT < 31
                    && (Manifest.permission.BLUETOOTH_CONNECT.equals(permission)
                    || Manifest.permission.BLUETOOTH_ADVERTISE.equals(permission))) {
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
