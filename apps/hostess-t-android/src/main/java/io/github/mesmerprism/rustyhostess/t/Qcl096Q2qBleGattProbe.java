package io.github.mesmerprism.rustyhostess.t;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattServer;
import android.bluetooth.BluetoothGattServerCallback;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.bluetooth.le.AdvertiseCallback;
import android.bluetooth.le.AdvertiseData;
import android.bluetooth.le.AdvertiseSettings;
import android.bluetooth.le.BluetoothLeAdvertiser;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanFilter;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Handler;
import android.os.ParcelUuid;
import android.os.SystemClock;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

final class Qcl096Q2qBleGattProbe {
    static final UUID SERVICE_UUID = UUID.fromString("7b2a0096-7c4d-4f4c-9b16-515100515100");
    static final UUID CONTROL_UUID = UUID.fromString("7b2a0097-7c4d-4f4c-9b16-515100515100");
    static final UUID STATUS_UUID = UUID.fromString("7b2a0098-7c4d-4f4c-9b16-515100515100");
    private static final UUID CCCD_UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");
    private static final String SCHEMA = "rusty.hostess.android.qcl096_q2q_ble_gatt_probe.v1";

    private Qcl096Q2qBleGattProbe() {
    }

    static void start(
            Activity activity,
            Intent intent,
            Handler handler,
            PlatformDebugTelemetryView telemetryView) {
        String role = stringExtra(intent, "role", "server").toLowerCase(Locale.ROOT);
        if ("client".equals(role)) {
            new ClientRunner(activity, intent, handler, telemetryView).start();
            return;
        }
        new ServerRunner(activity, intent, handler, telemetryView).start();
    }

    private static final class ServerRunner {
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
        private AdvertiseCallback advertiseCallback;
        private BluetoothGattServer gattServer;
        private BluetoothGattCharacteristic statusCharacteristic;
        private boolean adapterAvailable = false;
        private boolean bluetoothEnabled = false;
        private boolean multipleAdvertisementSupported = false;
        private boolean advertisingStarted = false;
        private boolean advertisingStopped = false;
        private boolean gattServerOpened = false;
        private boolean gattServerClosed = false;
        private boolean serviceAdded = false;
        private int serviceAddStatus = Integer.MIN_VALUE;
        private int advertisingErrorCode = 0;
        private int connections = 0;
        private int disconnections = 0;
        private int writeRequests = 0;
        private int readRequests = 0;
        private int bytesReceived = 0;
        private int bytesRead = 0;
        private String lastAck = "ready";
        private boolean completed = false;

        ServerRunner(
                Activity activity,
                Intent intent,
                Handler handler,
                PlatformDebugTelemetryView telemetryView) {
            this.activity = activity;
            this.intent = intent;
            this.handler = handler;
            this.telemetryView = telemetryView;
            this.runId = stringExtra(intent, "run_id", "qcl096-q2q-ble-gatt-server");
            this.expectedMessages = Math.max(1, intExtra(intent, "message_count", 10));
            this.timeoutMs = Math.max(3000L, longExtra(intent, "timeout_ms", 30000L));
        }

        void start() {
            recordEvent("probe.start", "pass", "QCL-096 Quest-to-Quest BLE/GATT server starting");
            String[] missing = missingPermissions("server", activity);
            if (missing.length > 0) {
                fail("hostess.issue.connectivity_probe.qcl096_permission_missing", "Missing permission: " + missing[0]);
                return;
            }

            BluetoothManager manager = (BluetoothManager) activity.getSystemService(Activity.BLUETOOTH_SERVICE);
            BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
            adapterAvailable = adapter != null;
            bluetoothEnabled = adapter != null && adapter.isEnabled();
            multipleAdvertisementSupported = adapter != null && adapter.isMultipleAdvertisementSupported();
            if (adapter == null || !adapter.isEnabled()) {
                fail("hostess.issue.connectivity_probe.qcl096_backend_missing", "Bluetooth adapter unavailable or disabled");
                return;
            }

            advertiser = adapter.getBluetoothLeAdvertiser();
            if (advertiser == null || !multipleAdvertisementSupported) {
                fail("hostess.issue.connectivity_probe.qcl096_advertiser_missing", "BLE advertising is not available on this device");
                return;
            }

            gattServer = manager.openGattServer(activity, gattServerCallback);
            if (gattServer == null) {
                fail("hostess.issue.connectivity_probe.qcl096_gatt_server_failed", "Could not open GATT server");
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
            statusCharacteristic.setValue(statusPayload("ready", 0, ""));
            service.addCharacteristic(control);
            service.addCharacteristic(statusCharacteristic);

            if (!gattServer.addService(service)) {
                fail("hostess.issue.connectivity_probe.qcl096_gatt_server_failed", "Could not add GATT service");
                return;
            }
            handler.postDelayed(() -> {
                if (!completed) {
                    fail("hostess.issue.connectivity_probe.qcl096_timeout", "Timed out waiting for Quest BLE/GATT client payloads");
                }
            }, timeoutMs);
        }

        private final BluetoothGattServerCallback gattServerCallback = new BluetoothGattServerCallback() {
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
                    fail("hostess.issue.connectivity_probe.qcl096_service_add_failed", "GATT service add failed: " + status);
                }
            }

            @Override
            public void onConnectionStateChange(BluetoothDevice device, int status, int newState) {
                if (newState == BluetoothProfile.STATE_CONNECTED) {
                    connections += 1;
                    recordEvent("gatt_server.connection", "pass", "client connected; address redacted");
                } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                    disconnections += 1;
                    recordEvent("gatt_server.disconnection", "pass", "client disconnected; address redacted");
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
                String text = new String(payload, StandardCharsets.UTF_8);
                writeRequests += 1;
                bytesReceived += payload.length;
                receivedPayloads.add(text);
                int sequence = sequenceFromPayload(text, writeRequests);
                lastAck = statusPayload("ack", sequence, text);
                if (statusCharacteristic != null) {
                    statusCharacteristic.setValue(lastAck.getBytes(StandardCharsets.UTF_8));
                }
                if (responseNeeded && gattServer != null) {
                    gattServer.sendResponse(device, requestId, BluetoothGatt.GATT_SUCCESS, offset, lastAck.getBytes(StandardCharsets.UTF_8));
                }
                if (gattServer != null && statusCharacteristic != null) {
                    gattServer.notifyCharacteristicChanged(device, statusCharacteristic, false);
                }
                recordEvent("gatt.write", "pass", "received Quest BLE/GATT control payload " + writeRequests);
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
            advertiseCallback = new AdvertiseCallback() {
                @Override
                public void onStartSuccess(AdvertiseSettings settingsInEffect) {
                    advertisingStarted = true;
                    recordEvent("ble_advertise.start", "pass", "BLE advertising started");
                }

                @Override
                public void onStartFailure(int errorCode) {
                    advertisingErrorCode = errorCode;
                    fail("hostess.issue.connectivity_probe.qcl096_advertise_failed", "BLE advertising failed: " + errorCode);
                }
            };
            advertiser.startAdvertising(settings, data, advertiseCallback);
        }

        private String statusPayload(String status, int sequence, String requestPayload) {
            if ("ack".equals(status)) {
                return String.format(Locale.ROOT, "a:%04d:%04d", sequence, writeRequests);
            }
            return String.format(Locale.ROOT, "r:%04d", writeRequests);
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

        private void complete(String status) {
            if (completed) {
                return;
            }
            completed = true;
            cleanup();
            writeEvidence(status);
            handler.post(() -> telemetryView.setRunState(status, "qcl096_q2q_ble_gatt", new ArrayList<>()));
        }

        private void cleanup() {
            if (advertiser != null && advertiseCallback != null && advertisingStarted && !advertisingStopped) {
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
                JSONObject evidence = baseEvidence(runId, "quest_ble_gatt_server", status, startedAt, endedAt);
                evidence.put("messages_expected", expectedMessages);
                evidence.put("messages_received", writeRequests);
                evidence.put("read_requests", readRequests);
                evidence.put("bytes_received", bytesReceived);
                evidence.put("bytes_read", bytesRead);
                evidence.put("permissions", permissionStatus("server", activity));
                evidence.put("bluetooth", new JSONObject()
                        .put("adapter_available", adapterAvailable)
                        .put("enabled", bluetoothEnabled)
                        .put("multiple_advertisement_supported", multipleAdvertisementSupported));
                evidence.put("advertising", new JSONObject()
                        .put("started", advertisingStarted)
                        .put("stopped", advertisingStopped)
                        .put("error_code", advertisingErrorCode));
                evidence.put("gatt_server", new JSONObject()
                        .put("opened", gattServerOpened)
                        .put("closed", gattServerClosed)
                        .put("service_added", serviceAdded)
                        .put("service_add_status", serviceAddStatus == Integer.MIN_VALUE ? JSONObject.NULL : serviceAddStatus)
                        .put("connections", connections)
                        .put("disconnections", disconnections));
                evidence.put("payloads", redactedPayloads(receivedPayloads));
                evidence.put("events", new JSONArray(events));
                evidence.put("errors", new JSONArray(errors));
                evidence.put("issue_codes", new JSONArray(issueCodes));
                writeEvidenceFile(activity, evidence);
            } catch (IOException | JSONException ignored) {
                // UI state remains the fallback when app-private evidence cannot be written.
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
    }

    private static final class ClientRunner implements Runnable {
        private final Activity activity;
        private final Intent intent;
        private final Handler handler;
        private final PlatformDebugTelemetryView telemetryView;
        private final String runId;
        private final String directionLabel;
        private final int messageCount;
        private final long intervalMs;
        private final long timeoutMs;
        private final Instant startedAt = Instant.now();
        private final List<JSONObject> events = new ArrayList<>();
        private final List<String> errors = new ArrayList<>();
        private final List<String> issueCodes = new ArrayList<>();
        private final List<Long> rttMs = new ArrayList<>();

        private BluetoothGatt gatt;
        private BluetoothLeScanner scanner;
        private boolean adapterAvailable = false;
        private boolean bluetoothEnabled = false;
        private boolean scanStarted = false;
        private boolean scanStopped = false;
        private int scanFoundCount = 0;
        private int scanErrorCode = 0;
        private boolean connectStarted = false;
        private boolean connected = false;
        private boolean disconnected = false;
        private int serviceDiscoveryStatus = Integer.MIN_VALUE;
        private boolean disconnectRequested = false;
        private boolean gattClosed = false;
        private int messagesSent = 0;
        private int acknowledgements = 0;
        private int sequenceEchoes = 0;
        private int writeFailures = 0;
        private int readFailures = 0;
        private int bytesWritten = 0;
        private int bytesRead = 0;
        private boolean completed = false;

        ClientRunner(
                Activity activity,
                Intent intent,
                Handler handler,
                PlatformDebugTelemetryView telemetryView) {
            this.activity = activity;
            this.intent = intent;
            this.handler = handler;
            this.telemetryView = telemetryView;
            this.runId = stringExtra(intent, "run_id", "qcl096-q2q-ble-gatt-client");
            this.directionLabel = stringExtra(intent, "direction", "quest-to-quest");
            this.messageCount = Math.max(1, intExtra(intent, "message_count", 10));
            this.intervalMs = Math.max(0L, longExtra(intent, "interval_ms", 500L));
            this.timeoutMs = Math.max(3000L, longExtra(intent, "timeout_ms", 30000L));
        }

        void start() {
            recordEvent("probe.start", "pass", "QCL-096 Quest-to-Quest BLE/GATT client starting");
            String[] missing = missingPermissions("client", activity);
            if (missing.length > 0) {
                fail("hostess.issue.connectivity_probe.qcl096_permission_missing", "Missing permission: " + missing[0]);
                return;
            }
            Thread thread = new Thread(this, "qcl096-q2q-ble-gatt-client");
            thread.start();
        }

        @Override
        public void run() {
            try {
                runClient();
            } catch (RuntimeException ex) {
                fail("hostess.issue.connectivity_probe.qcl096_client_failed", ex.getMessage() == null ? ex.toString() : ex.getMessage());
            }
        }

        private void runClient() {
            BluetoothManager manager = (BluetoothManager) activity.getSystemService(Activity.BLUETOOTH_SERVICE);
            BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
            adapterAvailable = adapter != null;
            bluetoothEnabled = adapter != null && adapter.isEnabled();
            if (adapter == null || !adapter.isEnabled()) {
                fail("hostess.issue.connectivity_probe.qcl096_backend_missing", "Bluetooth adapter unavailable or disabled");
                return;
            }
            scanner = adapter.getBluetoothLeScanner();
            if (scanner == null) {
                fail("hostess.issue.connectivity_probe.qcl096_scanner_missing", "BLE scanner is not available on this device");
                return;
            }

            BluetoothDevice device = scanForPeer();
            if (device == null) {
                String issue = scanErrorCode == 0
                        ? "hostess.issue.connectivity_probe.qcl096_scan_timeout"
                        : "hostess.issue.connectivity_probe.qcl096_scan_failed";
                fail(issue, scanErrorCode == 0 ? "Timed out scanning for peer Quest BLE/GATT service" : "BLE scan failed: " + scanErrorCode);
                return;
            }

            runGattExchange(device);
            String status = messagesSent == messageCount && acknowledgements == messageCount ? "pass" : "fail";
            if (!completed) {
                complete(status);
            }
        }

        private BluetoothDevice scanForPeer() {
            CountDownLatch foundLatch = new CountDownLatch(1);
            final BluetoothDevice[] found = new BluetoothDevice[1];
            ScanCallback callback = new ScanCallback() {
                @Override
                public void onScanResult(int callbackType, ScanResult result) {
                    if (result != null && result.getDevice() != null) {
                        found[0] = result.getDevice();
                        scanFoundCount += 1;
                        foundLatch.countDown();
                    }
                }

                @Override
                public void onScanFailed(int errorCode) {
                    scanErrorCode = errorCode;
                    foundLatch.countDown();
                }
            };
            ScanFilter filter = new ScanFilter.Builder()
                    .setServiceUuid(new ParcelUuid(SERVICE_UUID))
                    .build();
            ScanSettings settings = new ScanSettings.Builder()
                    .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                    .build();
            scanner.startScan(Collections.singletonList(filter), settings, callback);
            scanStarted = true;
            recordEvent("ble_scan.start", "pass", "BLE scan started for QCL-096 service UUID");
            try {
                foundLatch.await(timeoutMs, TimeUnit.MILLISECONDS);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                errors.add("Interrupted while scanning");
            } finally {
                try {
                    scanner.stopScan(callback);
                    scanStopped = true;
                } catch (RuntimeException ex) {
                    errors.add("stopScan failed: " + ex.getMessage());
                }
            }
            if (found[0] != null) {
                recordEvent("ble_scan.result", "pass", "peer service found; address redacted");
            }
            return found[0];
        }

        private void runGattExchange(BluetoothDevice device) {
            CountDownLatch readyLatch = new CountDownLatch(1);
            final BluetoothGattCharacteristic[] controlRef = new BluetoothGattCharacteristic[1];
            final BluetoothGattCharacteristic[] statusRef = new BluetoothGattCharacteristic[1];
            final CountDownLatch[] writeLatch = new CountDownLatch[1];
            final CountDownLatch[] readLatch = new CountDownLatch[1];
            final int[] lastWriteStatus = new int[]{Integer.MIN_VALUE};
            final int[] lastReadStatus = new int[]{Integer.MIN_VALUE};
            final String[] lastReadValue = new String[]{""};

            BluetoothGattCallback callback = new BluetoothGattCallback() {
                @Override
                public void onConnectionStateChange(BluetoothGatt callbackGatt, int status, int newState) {
                    if (newState == BluetoothProfile.STATE_CONNECTED) {
                        connected = true;
                        recordEvent("gatt_client.connection", "pass", "connected to peer; address redacted");
                        callbackGatt.discoverServices();
                    } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                        disconnected = true;
                    }
                }

                @Override
                public void onServicesDiscovered(BluetoothGatt callbackGatt, int status) {
                    serviceDiscoveryStatus = status;
                    BluetoothGattService service = callbackGatt.getService(SERVICE_UUID);
                    if (status == BluetoothGatt.GATT_SUCCESS && service != null) {
                        controlRef[0] = service.getCharacteristic(CONTROL_UUID);
                        statusRef[0] = service.getCharacteristic(STATUS_UUID);
                    }
                    readyLatch.countDown();
                }

                @Override
                public void onCharacteristicWrite(
                        BluetoothGatt callbackGatt,
                        BluetoothGattCharacteristic characteristic,
                        int status) {
                    lastWriteStatus[0] = status;
                    if (writeLatch[0] != null) {
                        writeLatch[0].countDown();
                    }
                }

                @Override
                public void onCharacteristicRead(
                        BluetoothGatt callbackGatt,
                        BluetoothGattCharacteristic characteristic,
                        int status) {
                    lastReadStatus[0] = status;
                    byte[] value = characteristic == null ? null : characteristic.getValue();
                    lastReadValue[0] = value == null ? "" : new String(value, StandardCharsets.UTF_8);
                    if (readLatch[0] != null) {
                        readLatch[0].countDown();
                    }
                }

                @Override
                public void onCharacteristicRead(
                        BluetoothGatt callbackGatt,
                        BluetoothGattCharacteristic characteristic,
                        byte[] value,
                        int status) {
                    lastReadStatus[0] = status;
                    lastReadValue[0] = value == null ? "" : new String(value, StandardCharsets.UTF_8);
                    if (readLatch[0] != null) {
                        readLatch[0].countDown();
                    }
                }
            };

            gatt = device.connectGatt(activity, false, callback, BluetoothDevice.TRANSPORT_LE);
            connectStarted = gatt != null;
            if (gatt == null) {
                fail("hostess.issue.connectivity_probe.qcl096_connect_failed", "connectGatt returned null");
                return;
            }
            try {
                if (!readyLatch.await(timeoutMs, TimeUnit.MILLISECONDS)) {
                    fail("hostess.issue.connectivity_probe.qcl096_service_discovery_timeout", "Timed out waiting for GATT service discovery");
                    return;
                }
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                fail("hostess.issue.connectivity_probe.qcl096_interrupted", "Interrupted during service discovery");
                return;
            }
            if (controlRef[0] == null || statusRef[0] == null) {
                fail("hostess.issue.connectivity_probe.qcl096_characteristic_missing", "QCL-096 control/status characteristic missing");
                return;
            }

            for (int sequence = 1; sequence <= messageCount; sequence += 1) {
                long txNs = SystemClock.elapsedRealtimeNanos();
                String payload = String.format(Locale.ROOT, "q:%04d", sequence);
                CountDownLatch currentWrite = new CountDownLatch(1);
                writeLatch[0] = currentWrite;
                lastWriteStatus[0] = Integer.MIN_VALUE;
                controlRef[0].setWriteType(BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT);
                byte[] payloadBytes = payload.getBytes(StandardCharsets.UTF_8);
                controlRef[0].setValue(payloadBytes);
                boolean writeStarted = gatt.writeCharacteristic(controlRef[0]);
                if (!writeStarted || !await(currentWrite) || lastWriteStatus[0] != BluetoothGatt.GATT_SUCCESS) {
                    writeFailures += 1;
                    continue;
                }
                bytesWritten += payloadBytes.length;
                messagesSent += 1;

                CountDownLatch currentRead = new CountDownLatch(1);
                readLatch[0] = currentRead;
                lastReadStatus[0] = Integer.MIN_VALUE;
                boolean readStarted = gatt.readCharacteristic(statusRef[0]);
                if (!readStarted || !await(currentRead) || lastReadStatus[0] != BluetoothGatt.GATT_SUCCESS) {
                    readFailures += 1;
                    continue;
                }
                long rxNs = SystemClock.elapsedRealtimeNanos();
                String readValue = lastReadValue[0] == null ? "" : lastReadValue[0];
                bytesRead += readValue.getBytes(StandardCharsets.UTF_8).length;
                acknowledgements += 1;
                rttMs.add((rxNs - txNs) / 1_000_000L);
                if (readValue.contains(String.format(Locale.ROOT, "a:%04d", sequence))) {
                    sequenceEchoes += 1;
                }
                recordEvent("gatt_client.exchange", "pass", "message " + sequence + " write/read completed");
                sleepQuietly(intervalMs);
            }
        }

        private boolean await(CountDownLatch latch) {
            try {
                return latch.await(timeoutMs, TimeUnit.MILLISECONDS);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                return false;
            }
        }

        private void fail(String issueCode, String message) {
            errors.add(message);
            issueCodes.add(issueCode);
            recordEvent("probe.failure", "fail", message);
            complete("fail");
        }

        private void complete(String status) {
            if (completed) {
                return;
            }
            completed = true;
            cleanup();
            writeEvidence(status);
            handler.post(() -> telemetryView.setRunState(status, "qcl096_q2q_ble_gatt", new ArrayList<>()));
        }

        private void cleanup() {
            if (gatt != null) {
                try {
                    gatt.disconnect();
                    disconnectRequested = true;
                } catch (RuntimeException ignored) {
                }
                try {
                    gatt.close();
                    gattClosed = true;
                } catch (RuntimeException ignored) {
                }
            }
            recordEvent("probe.cleanup", "pass", "BLE GATT client cleanup attempted");
        }

        private void writeEvidence(String status) {
            Instant endedAt = Instant.now();
            try {
                JSONObject evidence = baseEvidence(runId, "quest_ble_gatt_client", status, startedAt, endedAt);
                evidence.put("direction", directionLabel);
                evidence.put("messages_expected", messageCount);
                evidence.put("messages_sent", messagesSent);
                evidence.put("messages_acknowledged", acknowledgements);
                evidence.put("sequence_echoes", sequenceEchoes);
                evidence.put("write_failures", writeFailures);
                evidence.put("read_failures", readFailures);
                evidence.put("bytes_written", bytesWritten);
                evidence.put("bytes_read", bytesRead);
                evidence.put("permissions", permissionStatus("client", activity));
                evidence.put("bluetooth", new JSONObject()
                        .put("adapter_available", adapterAvailable)
                        .put("enabled", bluetoothEnabled));
                evidence.put("scan", new JSONObject()
                        .put("started", scanStarted)
                        .put("stopped", scanStopped)
                        .put("found_count", scanFoundCount)
                        .put("error_code", scanErrorCode));
                evidence.put("gatt_client", new JSONObject()
                        .put("connect_started", connectStarted)
                        .put("connected", connected)
                        .put("disconnected", disconnected)
                        .put("service_discovery_status", serviceDiscoveryStatus == Integer.MIN_VALUE ? JSONObject.NULL : serviceDiscoveryStatus)
                        .put("disconnect_requested", disconnectRequested)
                        .put("gatt_closed", gattClosed));
                evidence.put("latency", new JSONObject()
                        .put("rtt_ms_min", min(rttMs))
                        .put("rtt_ms_median", percentile(rttMs, 50))
                        .put("rtt_ms_p95", percentile(rttMs, 95))
                        .put("rtt_ms_max", max(rttMs)));
                evidence.put("events", new JSONArray(events));
                evidence.put("errors", new JSONArray(errors));
                evidence.put("issue_codes", new JSONArray(issueCodes));
                writeEvidenceFile(activity, evidence);
            } catch (IOException | JSONException ignored) {
                // UI state remains the fallback when app-private evidence cannot be written.
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
    }

    private static JSONObject baseEvidence(String runId, String role, String status, Instant startedAt, Instant endedAt) throws JSONException {
        JSONObject evidence = new JSONObject();
        evidence.put("schema", SCHEMA);
        evidence.put("schema_version", 1);
        evidence.put("run_id", runId);
        evidence.put("status", status);
        evidence.put("started_at_utc", startedAt.toString());
        evidence.put("ended_at_utc", endedAt.toString());
        evidence.put("role", role);
        evidence.put("authority", "app_owned_runtime_q2q_ble_gatt");
        evidence.put("service_uuid", SERVICE_UUID.toString());
        evidence.put("control_characteristic_uuid", CONTROL_UUID.toString());
        evidence.put("status_characteristic_uuid", STATUS_UUID.toString());
        evidence.put("raw_bluetooth_addresses_redacted", true);
        return evidence;
    }

    private static void writeEvidenceFile(Activity activity, JSONObject evidence) throws IOException, JSONException {
        File root = new File(activity.getExternalFilesDir(null), "hostess-t/evidence/qcl096-q2q-ble-gatt");
        if (!root.exists() && !root.mkdirs()) {
            throw new IOException("could not create QCL-096 evidence folder");
        }
        writeText(new File(root, "latest.json"), evidence.toString(2));
    }

    private static JSONObject permissionStatus(String role, Activity activity) throws JSONException {
        JSONObject permissions = new JSONObject();
        permissions.put("bluetooth_connect", permissionGranted(activity, Manifest.permission.BLUETOOTH_CONNECT));
        permissions.put("bluetooth_advertise", permissionGranted(activity, Manifest.permission.BLUETOOTH_ADVERTISE));
        permissions.put("bluetooth_scan", permissionGranted(activity, Manifest.permission.BLUETOOTH_SCAN));
        permissions.put("access_fine_location", permissionGranted(activity, Manifest.permission.ACCESS_FINE_LOCATION));
        permissions.put("role", role);
        permissions.put("address_redacted", true);
        return permissions;
    }

    private static String[] missingPermissions(String role, Activity activity) {
        List<String> missing = new ArrayList<>();
        if (android.os.Build.VERSION.SDK_INT >= 31) {
            if (!permissionGranted(activity, Manifest.permission.BLUETOOTH_CONNECT)) {
                missing.add(Manifest.permission.BLUETOOTH_CONNECT);
            }
            if ("server".equals(role) && !permissionGranted(activity, Manifest.permission.BLUETOOTH_ADVERTISE)) {
                missing.add(Manifest.permission.BLUETOOTH_ADVERTISE);
            }
            if ("client".equals(role) && !permissionGranted(activity, Manifest.permission.BLUETOOTH_SCAN)) {
                missing.add(Manifest.permission.BLUETOOTH_SCAN);
            }
        }
        if ("client".equals(role) && !permissionGranted(activity, Manifest.permission.ACCESS_FINE_LOCATION)) {
            missing.add(Manifest.permission.ACCESS_FINE_LOCATION);
        }
        return missing.toArray(new String[0]);
    }

    private static boolean permissionGranted(Activity activity, String permission) {
        if (android.os.Build.VERSION.SDK_INT < 31
                && (Manifest.permission.BLUETOOTH_CONNECT.equals(permission)
                || Manifest.permission.BLUETOOTH_ADVERTISE.equals(permission)
                || Manifest.permission.BLUETOOTH_SCAN.equals(permission))) {
            return true;
        }
        return activity.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
    }

    private static JSONArray redactedPayloads(List<String> receivedPayloads) {
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

    private static int sequenceFromPayload(String payload, int fallback) {
        String marker = "sequence=";
        int start = payload.indexOf(marker);
        if (payload.startsWith("q:") && payload.length() >= 6) {
            try {
                return Integer.parseInt(payload.substring(2, 6));
            } catch (NumberFormatException ex) {
                return fallback;
            }
        }
        if (start < 0) {
            return fallback;
        }
        start += marker.length();
        int end = start;
        while (end < payload.length() && Character.isDigit(payload.charAt(end))) {
            end += 1;
        }
        try {
            return Integer.parseInt(payload.substring(start, end));
        } catch (NumberFormatException ex) {
            return fallback;
        }
    }

    private static long min(List<Long> values) {
        if (values.isEmpty()) {
            return -1L;
        }
        long best = Long.MAX_VALUE;
        for (Long value : values) {
            if (value != null && value < best) {
                best = value;
            }
        }
        return best;
    }

    private static long max(List<Long> values) {
        if (values.isEmpty()) {
            return -1L;
        }
        long best = Long.MIN_VALUE;
        for (Long value : values) {
            if (value != null && value > best) {
                best = value;
            }
        }
        return best;
    }

    private static long percentile(List<Long> values, int percentile) {
        if (values.isEmpty()) {
            return -1L;
        }
        List<Long> sorted = new ArrayList<>(values);
        Collections.sort(sorted);
        int index = (int) Math.ceil((percentile / 100.0) * sorted.size()) - 1;
        if (index < 0) {
            index = 0;
        }
        if (index >= sorted.size()) {
            index = sorted.size() - 1;
        }
        return sorted.get(index);
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

    private static void sleepQuietly(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
        }
    }
}
