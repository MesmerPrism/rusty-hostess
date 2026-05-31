package io.github.mesmerprism.rustyhostess.t;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.TextView;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Queue;
import java.util.UUID;

public final class MainActivity extends Activity {
    private static final String ACTION_RUN = "io.github.mesmerprism.rustyhostess.t.RUN_CAPTURE";
    private static final String PACKAGE_ID = "package.polar_h10";
    private static final String SOFTWARE_ORIGIN = "rusty-hostess";

    private static final UUID HEART_RATE_SERVICE = UUID.fromString("0000180d-0000-1000-8000-00805f9b34fb");
    private static final UUID HEART_RATE_MEASUREMENT = UUID.fromString("00002a37-0000-1000-8000-00805f9b34fb");
    private static final UUID PMD_SERVICE = UUID.fromString("fb005c80-02e7-f387-1cad-8acd2d8df0c8");
    private static final UUID PMD_CONTROL_POINT = UUID.fromString("fb005c81-02e7-f387-1cad-8acd2d8df0c8");
    private static final UUID PMD_DATA = UUID.fromString("fb005c82-02e7-f387-1cad-8acd2d8df0c8");
    private static final UUID CCCD = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");

    private static final String STREAM_HR_RR = "stream.polar_h10.hr_rr";
    private static final String STREAM_ECG = "stream.polar_h10.ecg";
    private static final String STREAM_ACC = "stream.polar_h10.acc";

    private final Handler handler = new Handler(Looper.getMainLooper());
    private TextView statusView;
    private CaptureRun run;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        statusView = new TextView(this);
        statusView.setText("Manifold capture test");
        setContentView(statusView);
        startCapture(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        startCapture(intent);
    }

    private void startCapture(Intent intent) {
        if (!ACTION_RUN.equals(intent.getAction())) {
            writeImmediateFailure("unknown_intent", "Start with " + ACTION_RUN);
            return;
        }
        String[] missing = missingPermissions();
        if (missing.length > 0) {
            writeImmediateFailure("permission_missing", "Missing permission: " + missing[0]);
            return;
        }
        if (run != null) {
            run.close();
        }
        run = new CaptureRun(this, intent);
        statusView.setText("Capture running: " + run.mode);
        run.start();
    }

    private String[] missingPermissions() {
        List<String> missing = new ArrayList<>();
        if (android.os.Build.VERSION.SDK_INT >= 31) {
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED) {
                missing.add(Manifest.permission.BLUETOOTH_SCAN);
            }
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
                missing.add(Manifest.permission.BLUETOOTH_CONNECT);
            }
        } else if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            missing.add(Manifest.permission.ACCESS_FINE_LOCATION);
        }
        return missing.toArray(new String[0]);
    }

    private void writeImmediateFailure(String code, String message) {
        CaptureRun failure = new CaptureRun(this, new Intent(ACTION_RUN).putExtra("mode", "hr_rr"));
        failure.errors.add(code + ": " + message);
        failure.complete("fail");
    }

    private final class CaptureRun {
        final Context context;
        final String mode;
        final String hostProfile;
        final String deviceAddress;
        final String deviceNamePrefix;
        final long durationMs;
        final int accRateHz;
        final Instant startedAt = Instant.now();
        final List<String> errors = new ArrayList<>();
        final List<CommandRecord> commands = new ArrayList<>();
        final List<ControlRecord> controlRecords = new ArrayList<>();
        final List<Long> hrHostTimes = new ArrayList<>();
        final List<Integer> heartRates = new ArrayList<>();
        final List<Float> rrIntervalsMs = new ArrayList<>();
        final List<PmdFrameMetric> ecgFrames = new ArrayList<>();
        final List<PmdFrameMetric> accFrames = new ArrayList<>();
        int malformedFrameCount = 0;

        BluetoothLeScanner scanner;
        BluetoothGatt gatt;
        BluetoothGattCharacteristic hrCharacteristic;
        BluetoothGattCharacteristic pmdControlCharacteristic;
        BluetoothGattCharacteristic pmdDataCharacteristic;
        boolean scanFinished = false;
        boolean descriptorsStarted = false;
        boolean commandInFlight = false;
        String pendingCommand = "";
        boolean getSettingsWritten = false;
        boolean startWritten = false;
        boolean stopWritten = false;
        final Queue<DescriptorTask> descriptorTasks = new ArrayDeque<>();

        CaptureRun(Context context, Intent intent) {
            this.context = context;
            this.mode = normalizeMode(intent.getStringExtra("mode"));
            this.hostProfile = normalizeHostProfile(intent.getStringExtra("host_profile"));
            this.deviceAddress = emptyToNull(intent.getStringExtra("device_address"));
            this.deviceNamePrefix = intent.getStringExtra("device_name_prefix") == null
                    ? "Polar H10"
                    : intent.getStringExtra("device_name_prefix");
            this.durationMs = Math.max(1000L, intent.getLongExtra("duration_ms", 10000L));
            this.accRateHz = Math.max(25, intent.getIntExtra("acc_rate_hz", 200));
        }

        void start() {
            BluetoothManager manager = (BluetoothManager) context.getSystemService(Context.BLUETOOTH_SERVICE);
            BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
            if (adapter == null || !adapter.isEnabled()) {
                errors.add("bluetooth_unavailable");
                complete("fail");
                return;
            }
            scanner = adapter.getBluetoothLeScanner();
            if (scanner == null) {
                errors.add("scanner_unavailable");
                complete("fail");
                return;
            }
            scanner.startScan(scanCallback);
            handler.postDelayed(() -> {
                if (!scanFinished) {
                    stopScan();
                    errors.add("scan_timeout");
                    complete("fail");
                }
            }, 15000L);
        }

        void close() {
            stopScan();
            if (gatt != null) {
                gatt.disconnect();
                gatt.close();
                gatt = null;
            }
        }

        private final ScanCallback scanCallback = new ScanCallback() {
            @Override
            public void onScanResult(int callbackType, ScanResult result) {
                BluetoothDevice device = result.getDevice();
                if (device == null || !matches(device)) {
                    return;
                }
                stopScan();
                gatt = device.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE);
            }

            @Override
            public void onScanFailed(int errorCode) {
                errors.add("scan_failed:" + errorCode);
                complete("fail");
            }
        };

        private final BluetoothGattCallback gattCallback = new BluetoothGattCallback() {
            @Override
            public void onConnectionStateChange(BluetoothGatt gatt, int status, int newState) {
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    errors.add("connection_status:" + status);
                    complete("fail");
                    return;
                }
                if (newState == BluetoothProfile.STATE_CONNECTED) {
                    gatt.requestConnectionPriority(BluetoothGatt.CONNECTION_PRIORITY_HIGH);
                    gatt.discoverServices();
                } else if (newState == BluetoothProfile.STATE_DISCONNECTED && !stopWritten) {
                    errors.add("disconnected_before_stop");
                    complete("fail");
                }
            }

            @Override
            public void onServicesDiscovered(BluetoothGatt gatt, int status) {
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    errors.add("service_discovery_status:" + status);
                    complete("fail");
                    return;
                }
                boolean mtuRequested = gatt.requestMtu(232);
                if (!mtuRequested) {
                    setupAfterMtu(gatt);
                } else {
                    handler.postDelayed(() -> setupAfterMtu(gatt), 1500L);
                }
            }

            @Override
            public void onMtuChanged(BluetoothGatt gatt, int mtu, int status) {
                setupAfterMtu(gatt);
            }

            @Override
            public void onDescriptorWrite(BluetoothGatt gatt, BluetoothGattDescriptor descriptor, int status) {
                commandInFlight = false;
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    errors.add("descriptor_write_status:" + status);
                }
                writeNextDescriptorOrBegin(gatt);
            }

            @Override
            public void onCharacteristicWrite(BluetoothGatt gatt, BluetoothGattCharacteristic characteristic, int status) {
                commandInFlight = false;
                commands.add(new CommandRecord(pendingCommand, status == BluetoothGatt.GATT_SUCCESS ? "acknowledged" : "rejected", status, System.nanoTime()));
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    errors.add("command_write_status:" + pendingCommand + ":" + status);
                    complete("fail");
                    return;
                }
                if ("get_settings".equals(pendingCommand)) {
                    getSettingsWritten = true;
                    writePmdCommand(gatt, "start_stream", buildStartCommand());
                } else if ("start_stream".equals(pendingCommand)) {
                    startWritten = true;
                    scheduleStop();
                } else if ("stop_stream".equals(pendingCommand)) {
                    stopWritten = true;
                    complete(computePass() ? "pass" : "fail");
                }
            }

            @Override
            public void onCharacteristicChanged(BluetoothGatt gatt, BluetoothGattCharacteristic characteristic) {
                handleCharacteristic(characteristic, characteristic.getValue());
            }

            @Override
            public void onCharacteristicChanged(BluetoothGatt gatt, BluetoothGattCharacteristic characteristic, byte[] value) {
                handleCharacteristic(characteristic, value);
            }
        };

        private boolean matches(BluetoothDevice device) {
            String address = device.getAddress();
            String name = device.getName();
            if (deviceAddress != null && address != null && deviceAddress.equalsIgnoreCase(address)) {
                return true;
            }
            return name != null && name.startsWith(deviceNamePrefix);
        }

        private void stopScan() {
            if (scanner != null && !scanFinished) {
                try {
                    scanner.stopScan(scanCallback);
                } catch (RuntimeException ignored) {
                }
            }
            scanFinished = true;
        }

        private void setupAfterMtu(BluetoothGatt gatt) {
            if (descriptorsStarted) {
                return;
            }
            descriptorsStarted = true;
            BluetoothGattService hrService = gatt.getService(HEART_RATE_SERVICE);
            BluetoothGattService pmdService = gatt.getService(PMD_SERVICE);
            if ("hr_rr".equals(mode)) {
                hrCharacteristic = hrService == null ? null : hrService.getCharacteristic(HEART_RATE_MEASUREMENT);
                if (hrCharacteristic == null) {
                    errors.add("heart_rate_characteristic_missing");
                    complete("fail");
                    return;
                }
                descriptorTasks.add(new DescriptorTask(hrCharacteristic, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE));
            } else {
                if (pmdService == null) {
                    errors.add("pmd_service_missing");
                    complete("fail");
                    return;
                }
                pmdControlCharacteristic = pmdService.getCharacteristic(PMD_CONTROL_POINT);
                pmdDataCharacteristic = pmdService.getCharacteristic(PMD_DATA);
                if (pmdControlCharacteristic == null || pmdDataCharacteristic == null) {
                    errors.add("pmd_characteristic_missing");
                    complete("fail");
                    return;
                }
                descriptorTasks.add(new DescriptorTask(pmdControlCharacteristic, BluetoothGattDescriptor.ENABLE_INDICATION_VALUE));
                descriptorTasks.add(new DescriptorTask(pmdDataCharacteristic, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE));
            }
            writeNextDescriptorOrBegin(gatt);
        }

        private void writeNextDescriptorOrBegin(BluetoothGatt gatt) {
            if (commandInFlight) {
                return;
            }
            DescriptorTask task = descriptorTasks.poll();
            if (task == null) {
                beginCapture(gatt);
                return;
            }
            BluetoothGattDescriptor descriptor = task.characteristic.getDescriptor(CCCD);
            if (descriptor == null) {
                errors.add("cccd_missing");
                complete("fail");
                return;
            }
            gatt.setCharacteristicNotification(task.characteristic, true);
            descriptor.setValue(task.value);
            commandInFlight = true;
            if (!gatt.writeDescriptor(descriptor)) {
                commandInFlight = false;
                errors.add("descriptor_write_not_started");
                complete("fail");
            }
        }

        private void beginCapture(BluetoothGatt gatt) {
            if ("hr_rr".equals(mode)) {
                scheduleStop();
            } else if (!getSettingsWritten && !startWritten) {
                writePmdCommand(gatt, "get_settings", buildGetSettingsCommand());
            }
        }

        private void writePmdCommand(BluetoothGatt gatt, String label, byte[] payload) {
            if (pmdControlCharacteristic == null) {
                errors.add("pmd_control_missing");
                complete("fail");
                return;
            }
            pendingCommand = label;
            pmdControlCharacteristic.setValue(payload);
            commandInFlight = true;
            if (!gatt.writeCharacteristic(pmdControlCharacteristic)) {
                commandInFlight = false;
                errors.add("command_write_not_started:" + label);
                complete("fail");
            }
        }

        private void scheduleStop() {
            handler.postDelayed(() -> {
                if ("hr_rr".equals(mode)) {
                    complete(computePass() ? "pass" : "fail");
                } else if (gatt != null && !stopWritten) {
                    writePmdCommand(gatt, "stop_stream", buildStopCommand());
                }
            }, durationMs);
        }

        private void handleCharacteristic(BluetoothGattCharacteristic characteristic, byte[] value) {
            if (value == null) {
                malformedFrameCount += 1;
                return;
            }
            UUID uuid = characteristic.getUuid();
            try {
                if (HEART_RATE_MEASUREMENT.equals(uuid)) {
                    HeartRateReading reading = PolarProtocol.decodeHeartRateMeasurement(value);
                    hrHostTimes.add(System.nanoTime());
                    heartRates.add(reading.bpm);
                    rrIntervalsMs.addAll(reading.rrIntervalsMs);
                } else if (PMD_CONTROL_POINT.equals(uuid)) {
                    ControlRecord record = PolarProtocol.parseControl(value);
                    controlRecords.add(record);
                } else if (PMD_DATA.equals(uuid)) {
                    if ("ecg".equals(mode)) {
                        ecgFrames.add(PolarProtocol.decodeEcg(value));
                    } else if ("acc".equals(mode)) {
                        accFrames.add(PolarProtocol.decodeAcc(value));
                    }
                }
            } catch (RuntimeException ex) {
                malformedFrameCount += 1;
            }
        }

        private byte[] buildGetSettingsCommand() {
            return new byte[] {0x01, measurementType()};
        }

        private byte[] buildStartCommand() {
            if ("ecg".equals(mode)) {
                return new byte[] {0x02, 0x00, 0x00, 0x01, (byte) 0x82, 0x00, 0x01, 0x01, 0x0e, 0x00};
            }
            return new byte[] {
                    0x02, 0x02,
                    0x02, 0x01, 0x08, 0x00,
                    0x00, 0x01, (byte) (accRateHz & 0xff), (byte) ((accRateHz >> 8) & 0xff),
                    0x01, 0x01, 0x10, 0x00
            };
        }

        private byte[] buildStopCommand() {
            return new byte[] {0x03, measurementType()};
        }

        private byte measurementType() {
            return "ecg".equals(mode) ? (byte) 0x00 : (byte) 0x02;
        }

        private boolean computePass() {
            if (!errors.isEmpty()) {
                return false;
            }
            if ("hr_rr".equals(mode)) {
                return !heartRates.isEmpty() && !rrIntervalsMs.isEmpty();
            }
            if ("ecg".equals(mode)) {
                return decodedSampleCount(ecgFrames) > 0;
            }
            return decodedSampleCount(accFrames) > 0;
        }

        private int decodedSampleCount(List<PmdFrameMetric> frames) {
            int count = 0;
            for (PmdFrameMetric frame : frames) {
                count += frame.sampleCount;
            }
            return count;
        }

        private void complete(String status) {
            close();
            Instant endedAt = Instant.now();
            String json = new EvidenceWriter().write(this, status, endedAt);
            try {
                File root = new File(getExternalFilesDir(null), "hostess-t/evidence/live-capture");
                if (!root.exists() && !root.mkdirs()) {
                    throw new IOException("could not create output folder");
                }
                writeText(new File(root, "latest.json"), json);
                writeText(new File(root, sanitizeFileName(hostProfile + "-" + mode + "-" + endedAt.toString()) + ".json"), json);
                statusView.setText("Capture " + status + ": " + mode);
            } catch (IOException ex) {
                statusView.setText("Capture finished but write failed: " + ex.getMessage());
            }
        }
    }

    private static void writeText(File path, String text) throws IOException {
        try (FileOutputStream stream = new FileOutputStream(path)) {
            stream.write(text.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static String normalizeMode(String mode) {
        if ("ecg".equals(mode) || "acc".equals(mode) || "hr_rr".equals(mode)) {
            return mode;
        }
        return "hr_rr";
    }

    private static String normalizeHostProfile(String hostProfile) {
        if ("headset".equals(hostProfile) || "mobile".equals(hostProfile)) {
            return hostProfile;
        }
        return "mobile";
    }

    private static String emptyToNull(String value) {
        return value == null || value.trim().isEmpty() ? null : value.trim();
    }

    private static String sanitizeFileName(String value) {
        return value.replaceAll("[^a-zA-Z0-9._-]", "_");
    }

    private static final class DescriptorTask {
        final BluetoothGattCharacteristic characteristic;
        final byte[] value;

        DescriptorTask(BluetoothGattCharacteristic characteristic, byte[] value) {
            this.characteristic = characteristic;
            this.value = value;
        }
    }

    private static final class HeartRateReading {
        final int bpm;
        final List<Float> rrIntervalsMs;

        HeartRateReading(int bpm, List<Float> rrIntervalsMs) {
            this.bpm = bpm;
            this.rrIntervalsMs = rrIntervalsMs;
        }
    }

    private static final class PmdFrameMetric {
        final long hostTimeNs;
        final long sensorTimestampNs;
        final int sampleCount;

        PmdFrameMetric(long hostTimeNs, long sensorTimestampNs, int sampleCount) {
            this.hostTimeNs = hostTimeNs;
            this.sensorTimestampNs = sensorTimestampNs;
            this.sampleCount = sampleCount;
        }
    }

    private static final class CommandRecord {
        final String command;
        final String status;
        final int nativeStatus;
        final long hostTimeNs;

        CommandRecord(String command, String status, int nativeStatus, long hostTimeNs) {
            this.command = command;
            this.status = status;
            this.nativeStatus = nativeStatus;
            this.hostTimeNs = hostTimeNs;
        }
    }

    private static final class ControlRecord {
        final int opCode;
        final int measurementType;
        final int errorCode;

        ControlRecord(int opCode, int measurementType, int errorCode) {
            this.opCode = opCode;
            this.measurementType = measurementType;
            this.errorCode = errorCode;
        }
    }

    private static final class PolarProtocol {
        static HeartRateReading decodeHeartRateMeasurement(byte[] data) {
            if (data.length < 2) {
                throw new IllegalArgumentException("short heart-rate payload");
            }
            int flags = unsigned(data[0]);
            int offset = 1;
            int bpm;
            if ((flags & 0x01) != 0) {
                bpm = readUInt16(data, offset);
                offset += 2;
            } else {
                bpm = unsigned(data[offset]);
                offset += 1;
            }
            if ((flags & 0x08) != 0) {
                offset += 2;
            }
            List<Float> rr = new ArrayList<>();
            if ((flags & 0x10) != 0) {
                while (offset + 1 < data.length) {
                    rr.add(readUInt16(data, offset) * 1000.0f / 1024.0f);
                    offset += 2;
                }
            }
            return new HeartRateReading(bpm, rr);
        }

        static ControlRecord parseControl(byte[] data) {
            if (data.length < 4 || unsigned(data[0]) != 0xf0) {
                throw new IllegalArgumentException("bad control response");
            }
            return new ControlRecord(unsigned(data[1]), unsigned(data[2]), unsigned(data[3]));
        }

        static PmdFrameMetric decodeEcg(byte[] data) {
            validatePmd(data, 0x00, 0x00);
            int body = data.length - 10;
            if (body <= 0 || body % 3 != 0) {
                throw new IllegalArgumentException("bad ECG length");
            }
            return new PmdFrameMetric(System.nanoTime(), readUInt64(data, 1), body / 3);
        }

        static PmdFrameMetric decodeAcc(byte[] data) {
            validatePmd(data, 0x02, 0x01);
            int body = data.length - 10;
            if (body <= 0 || body % 6 != 0) {
                throw new IllegalArgumentException("bad ACC length");
            }
            return new PmdFrameMetric(System.nanoTime(), readUInt64(data, 1), body / 6);
        }

        static void validatePmd(byte[] data, int expectedType, int expectedFrameType) {
            if (data.length < 10 || unsigned(data[0]) != expectedType || unsigned(data[9]) != expectedFrameType) {
                throw new IllegalArgumentException("bad PMD frame");
            }
        }

        static int readUInt16(byte[] data, int offset) {
            if (offset + 1 >= data.length) {
                throw new IllegalArgumentException("short u16");
            }
            return unsigned(data[offset]) | (unsigned(data[offset + 1]) << 8);
        }

        static long readUInt64(byte[] data, int offset) {
            if (offset + 7 >= data.length) {
                throw new IllegalArgumentException("short u64");
            }
            long value = 0L;
            for (int index = 0; index < 8; index++) {
                value |= ((long) unsigned(data[offset + index])) << (index * 8);
            }
            return value;
        }

        static int unsigned(byte value) {
            return value & 0xff;
        }
    }

    private final class EvidenceWriter {
        String write(CaptureRun run, String status, Instant endedAt) {
            StringBuilder builder = new StringBuilder();
            builder.append("{\n");
            field(builder, "$schema", "rusty.manifold.live_capture_evidence.v1", true, 1);
            field(builder, "status", status, true, 1);
            field(builder, "host_profile", run.hostProfile, true, 1);
            field(builder, "started_at_utc", run.startedAt.toString(), true, 1);
            field(builder, "ended_at_utc", endedAt.toString(), true, 1);
            indent(builder, 1).append("\"software\": {\n");
            field(builder, "origin", SOFTWARE_ORIGIN, true, 2);
            field(builder, "host_app", hostAppId(run.hostProfile), true, 2);
            field(builder, "host_app_version", "0.1.0", false, 2);
            indent(builder, 1).append("},\n");
            indent(builder, 1).append("\"package\": {\n");
            field(builder, "package_id", PACKAGE_ID, true, 2);
            field(builder, "package_manifest_sha256", assetSha256("manifold/packages/polar-h10/manifests/package.manifold.json"), false, 2);
            indent(builder, 1).append("},\n");
            indent(builder, 1).append("\"capture\": {\n");
            field(builder, "mode", run.mode, true, 2);
            numberField(builder, "duration_ms", run.durationMs, true, 2);
            boolField(builder, "address_supplied", run.deviceAddress != null, false, 2);
            indent(builder, 1).append("},\n");
            appendCommands(builder, run);
            appendControl(builder, run);
            appendStreams(builder, run);
            appendErrors(builder, run);
            builder.append("}\n");
            return builder.toString();
        }

        private void appendCommands(StringBuilder builder, CaptureRun run) {
            indent(builder, 1).append("\"commands\": [\n");
            for (int index = 0; index < run.commands.size(); index++) {
                CommandRecord command = run.commands.get(index);
                indent(builder, 2).append("{");
                jsonPair(builder, "command", command.command).append(", ");
                jsonPair(builder, "status", command.status).append(", ");
                builder.append("\"native_status\": ").append(command.nativeStatus).append(", ");
                builder.append("\"host_time_ns\": ").append(command.hostTimeNs);
                builder.append(index + 1 == run.commands.size() ? "}\n" : "},\n");
            }
            indent(builder, 1).append("],\n");
        }

        private void appendControl(StringBuilder builder, CaptureRun run) {
            indent(builder, 1).append("\"control_responses\": [\n");
            for (int index = 0; index < run.controlRecords.size(); index++) {
                ControlRecord record = run.controlRecords.get(index);
                indent(builder, 2).append("{");
                builder.append("\"op_code\": ").append(record.opCode).append(", ");
                builder.append("\"measurement_type\": ").append(record.measurementType).append(", ");
                builder.append("\"error_code\": ").append(record.errorCode).append(", ");
                builder.append("\"success\": ").append(record.errorCode == 0 ? "true" : "false");
                builder.append(index + 1 == run.controlRecords.size() ? "}\n" : "},\n");
            }
            indent(builder, 1).append("],\n");
        }

        private void appendStreams(StringBuilder builder, CaptureRun run) {
            indent(builder, 1).append("\"streams\": [\n");
            indent(builder, 2).append("{\n");
            String streamId = streamId(run.mode);
            field(builder, "stream_id", streamId, true, 3);
            field(builder, "status", run.computePass() ? "pass" : "fail", true, 3);
            if ("hr_rr".equals(run.mode)) {
                numberField(builder, "heart_rate_event_count", run.heartRates.size(), true, 3);
                numberField(builder, "rr_interval_count", run.rrIntervalsMs.size(), true, 3);
                numberField(builder, "latest_bpm", run.heartRates.isEmpty() ? 0 : run.heartRates.get(run.heartRates.size() - 1), true, 3);
                doubleField(builder, "host_notification_rate_hz", hostRate(run.hrHostTimes), true, 3);
                numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            } else {
                List<PmdFrameMetric> frames = "ecg".equals(run.mode) ? run.ecgFrames : run.accFrames;
                numberField(builder, "frame_count", frames.size(), true, 3);
                numberField(builder, "decoded_sample_count", run.decodedSampleCount(frames), true, 3);
                doubleField(builder, "sensor_sample_rate_hz", sensorRate(frames), true, 3);
                doubleField(builder, "host_notification_rate_hz", pmdHostRate(frames), true, 3);
                numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            }
            indent(builder, 2).append("}\n");
            indent(builder, 1).append("],\n");
        }

        private void appendErrors(StringBuilder builder, CaptureRun run) {
            indent(builder, 1).append("\"errors\": [");
            for (int index = 0; index < run.errors.size(); index++) {
                builder.append(quote(run.errors.get(index)));
                if (index + 1 < run.errors.size()) {
                    builder.append(", ");
                }
            }
            builder.append("]\n");
        }

        private String assetSha256(String path) {
            try {
                MessageDigest digest = MessageDigest.getInstance("SHA-256");
                try (InputStream stream = openAsset(path)) {
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

        private InputStream openAsset(String path) throws IOException {
            try {
                return MainActivity.this.getAssets().open(path);
            } catch (IOException first) {
                return MainActivity.this.getAssets().open(path.replace('/', '\\'));
            }
        }

        private String streamId(String mode) {
            if ("ecg".equals(mode)) {
                return STREAM_ECG;
            }
            if ("acc".equals(mode)) {
                return STREAM_ACC;
            }
            return STREAM_HR_RR;
        }

        private String hostAppId(String hostProfile) {
            if ("headset".equals(hostProfile)) {
                return "app.rusty_hostess_t.quest";
            }
            return "app.rusty_hostess_t.android";
        }

        private double hostRate(List<Long> timestamps) {
            if (timestamps.size() < 2) {
                return 0.0;
            }
            double spanSeconds = (timestamps.get(timestamps.size() - 1) - timestamps.get(0)) / 1_000_000_000.0;
            return spanSeconds <= 0.0 ? 0.0 : round3((timestamps.size() - 1) / spanSeconds);
        }

        private double pmdHostRate(List<PmdFrameMetric> frames) {
            if (frames.size() < 2) {
                return 0.0;
            }
            double spanSeconds = (frames.get(frames.size() - 1).hostTimeNs - frames.get(0).hostTimeNs) / 1_000_000_000.0;
            return spanSeconds <= 0.0 ? 0.0 : round3((frames.size() - 1) / spanSeconds);
        }

        private double sensorRate(List<PmdFrameMetric> frames) {
            if (frames.size() < 2) {
                return 0.0;
            }
            double spanSeconds = (frames.get(frames.size() - 1).sensorTimestampNs - frames.get(0).sensorTimestampNs) / 1_000_000_000.0;
            int samples = 0;
            for (int index = 1; index < frames.size(); index++) {
                samples += frames.get(index).sampleCount;
            }
            return spanSeconds <= 0.0 ? 0.0 : round3(samples / spanSeconds);
        }

        private double round3(double value) {
            return Math.round(value * 1000.0) / 1000.0;
        }

        private StringBuilder field(StringBuilder builder, String name, String value, boolean comma, int level) {
            indent(builder, level);
            jsonPair(builder, name, value);
            builder.append(comma ? ",\n" : "\n");
            return builder;
        }

        private StringBuilder numberField(StringBuilder builder, String name, long value, boolean comma, int level) {
            indent(builder, level).append(quote(name)).append(": ").append(value).append(comma ? ",\n" : "\n");
            return builder;
        }

        private StringBuilder boolField(StringBuilder builder, String name, boolean value, boolean comma, int level) {
            indent(builder, level).append(quote(name)).append(": ").append(value ? "true" : "false").append(comma ? ",\n" : "\n");
            return builder;
        }

        private StringBuilder doubleField(StringBuilder builder, String name, double value, boolean comma, int level) {
            indent(builder, level).append(quote(name)).append(": ");
            builder.append(String.format(Locale.US, "%.3f", value)).append(comma ? ",\n" : "\n");
            return builder;
        }

        private StringBuilder jsonPair(StringBuilder builder, String name, String value) {
            return builder.append(quote(name)).append(": ").append(quote(value));
        }

        private StringBuilder indent(StringBuilder builder, int level) {
            for (int index = 0; index < level; index++) {
                builder.append("  ");
            }
            return builder;
        }

        private String quote(String value) {
            StringBuilder builder = new StringBuilder("\"");
            for (int index = 0; index < value.length(); index++) {
                char ch = value.charAt(index);
                if (ch == '\\' || ch == '"') {
                    builder.append('\\').append(ch);
                } else if (ch == '\n') {
                    builder.append("\\n");
                } else if (ch == '\r') {
                    builder.append("\\r");
                } else if (ch == '\t') {
                    builder.append("\\t");
                } else {
                    builder.append(ch);
                }
            }
            return builder.append('"').toString();
        }

        private String hex(byte[] bytes) {
            StringBuilder builder = new StringBuilder(bytes.length * 2);
            for (byte value : bytes) {
                builder.append(String.format(Locale.US, "%02x", value & 0xff));
            }
            return builder.toString();
        }
    }
}
