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
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

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
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Queue;
import java.util.UUID;

public final class MainActivity extends Activity {
    private static final String ACTION_RUN = "io.github.mesmerprism.rustyhostess.t.RUN_CAPTURE";
    private static final String ACTION_REPLAY = "io.github.mesmerprism.rustyhostess.t.RUN_REPLAY";
    private static final String ACTION_PMB_REPLAY = "io.github.mesmerprism.rustyhostess.t.RUN_PMB_REPLAY";
    private static final String ACTION_PMB_CONTROLLER_PREFLIGHT = "io.github.mesmerprism.rustyhostess.t.RUN_PMB_CONTROLLER_PREFLIGHT";
    private static final String ACTION_RENDER = "io.github.mesmerprism.rustyhostess.t.RENDER_TELEMETRY";
    private static final String PACKAGE_ID = "package.polar_h10";
    private static final String PMB_PACKAGE_ID = "package.projected_motion_breath";
    private static final String PMB_ASSET_ROOT = "manifold/packages/projected-motion-breath";
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
    private static final String STREAM_COHERENCE = "stream.polar_h10.coherence";
    private static final String STREAM_HRV_WINDOW = "stream.polar_h10.hrv_window";
    private static final String STREAM_RMSSD_GAIN = "stream.polar_h10.rmssd_gain";
    private static final String STREAM_BREATH_VOLUME = "stream.polar_h10.breath_volume";
    private static final String STREAM_BREATH_DYNAMICS = "stream.polar_h10.breath_dynamics";
    private static final String STREAM_HRVB_RESONANCE_AMPLITUDE = "stream.polar_h10.hrvb_resonance_amplitude";

    private static final String MODULE_HRV_WINDOW = "module.polar_h10.hrv_window";
    private static final String MODULE_RMSSD_GAIN = "module.polar_h10.rmssd_gain";
    private static final String MODULE_COHERENCE = "module.polar_h10.coherence";
    private static final String MODULE_BREATH_VOLUME_FROM_ACC = "module.polar_h10.breath_volume_from_acc";
    private static final String MODULE_BREATH_DYNAMICS = "module.polar_h10.breath_dynamics";
    private static final String MODULE_HRVB_RESONANCE_AMPLITUDE = "module.polar_h10.hrvb_resonance_amplitude";
    private static final long RUNTIME_PREVIEW_INTERVAL_MS = 15000L;
    private static final int MIN_RENDER_WIDTH = 320;
    private static final int MIN_RENDER_HEIGHT = 240;
    private static final int MIN_RENDER_CONTENT_PIXELS = 64;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private PlatformDebugTelemetryView telemetryView;
    private CaptureRun run;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        telemetryView = new PlatformDebugTelemetryView(this);
        setContentView(telemetryView);
        startCapture(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        startCapture(intent);
    }

    private void startCapture(Intent intent) {
        if (ACTION_RENDER.equals(intent.getAction())) {
            writeTelemetryRender(intent);
            return;
        }
        if (ACTION_REPLAY.equals(intent.getAction())) {
            writeSyntheticReplay(intent);
            return;
        }
        if (ACTION_PMB_REPLAY.equals(intent.getAction())) {
            writeProjectedMotionReplay(intent);
            return;
        }
        if (ACTION_PMB_CONTROLLER_PREFLIGHT.equals(intent.getAction())) {
            writeProjectedMotionControllerPreflight(intent);
            return;
        }
        if (!ACTION_RUN.equals(intent.getAction())) {
            telemetryView.setRunState("ready", "idle", new ArrayList<>());
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
        telemetryView.resetForRun(run.mode, run.selectedModules);
        telemetryView.setPage(run.telemetryPage);
        telemetryView.setRunState("running", run.mode, run.selectedModules);
        run.start();
    }

    private void writeSyntheticReplay(Intent intent) {
        Instant startedAt = Instant.now();
        List<String> selectedModules = normalizeModules(intent.getStringExtra("modules"));
        if (selectedModules.isEmpty()) {
            selectedModules = defaultProcessorModules();
        }
        String hostProfile = normalizeHostProfile(intent.getStringExtra("host_profile"));
        telemetryView.resetForRun("replay", selectedModules);
        telemetryView.setRunState("running", "replay", selectedModules);
        try {
            JSONObject runtimeInput = PolarRuntime.syntheticRuntimeInput(this);
            JSONObject graphReport = PolarRuntime.runGraph(this, runtimeInput, selectedModules);
            telemetryView.addGraphReport(graphReport);
            Instant endedAt = Instant.now();
            List<String> errors = graphErrors(graphReport);
            String status = errors.isEmpty() && "pass".equals(graphReport.optString("status")) ? "pass" : "fail";
            File root = new File(getExternalFilesDir(null), "hostess-t/evidence/live-capture");
            if (!root.exists() && !root.mkdirs()) {
                throw new IOException("could not create output folder");
            }
            writeText(new File(root, "latest.runtime-input.json"), runtimeInput.toString(2));
            writeText(new File(root, "latest.graph-execution-report.json"), graphReport.toString(2));
            String json = new EvidenceWriter().writeReplay(
                    hostProfile,
                    selectedModules,
                    startedAt,
                    endedAt,
                    status,
                    graphReport,
                    errors);
            writeText(new File(root, "latest.json"), json);
            telemetryView.setRunState(status, "replay", selectedModules);
        } catch (IOException | JSONException ex) {
            telemetryView.setRunState("fail", "replay", selectedModules);
        }
    }

    private void writeProjectedMotionReplay(Intent intent) {
        Instant startedAt = Instant.now();
        String hostProfile = normalizeHostProfile(intent.getStringExtra("host_profile"));
        List<String> modules = new ArrayList<>();
        modules.add("module.breath.projected_motion");
        modules.add("module.breath.dynamics");
        telemetryView.resetForRun("pmb_replay", modules);
        telemetryView.setRunState("running", "pmb_replay", modules);
        File evidenceRoot = new File(getExternalFilesDir(null), "hostess-t/evidence/pmb-replay");
        File packageRoot = new File(getExternalFilesDir(null), "hostess-t/packages/projected-motion-breath");
        try {
            resetDirectory(packageRoot);
            copyPmbPackageAssets(packageRoot);
            JSONObject coreReport = PMBRuntime.validatePackage(packageRoot.getAbsolutePath());
            Instant endedAt = Instant.now();
            List<String> errors = pmbCoreErrors(coreReport);
            String status = errors.isEmpty() && "pass".equals(coreReport.optString("status")) ? "pass" : "fail";
            if (!evidenceRoot.exists() && !evidenceRoot.mkdirs()) {
                throw new IOException("could not create PMB evidence folder");
            }
            writeText(new File(evidenceRoot, "latest.core-validation-report.json"), coreReport.toString(2));
            JSONObject evidence = pmbReplayEvidence(hostProfile, startedAt, endedAt, status, coreReport, errors, null);
            writeText(new File(evidenceRoot, "latest.json"), evidence.toString(2));
            telemetryView.setRunState(status, "pmb_replay", modules);
        } catch (IOException | JSONException | RuntimeException ex) {
            Instant endedAt = Instant.now();
            try {
                if (!evidenceRoot.exists()) {
                    evidenceRoot.mkdirs();
                }
                JSONObject coreReport = pmbFailureCoreReport(packageRoot.getAbsolutePath(), ex.getMessage());
                writeText(new File(evidenceRoot, "latest.core-validation-report.json"), coreReport.toString(2));
                List<String> errors = new ArrayList<>();
                errors.add(ex.getMessage() == null ? ex.toString() : ex.getMessage());
                JSONObject evidence = pmbReplayEvidence(hostProfile, startedAt, endedAt, "fail", coreReport, errors, ex.toString());
                writeText(new File(evidenceRoot, "latest.json"), evidence.toString(2));
            } catch (IOException | JSONException ignored) {
                // The UI state is the fallback signal when app-private evidence cannot be written.
            }
            telemetryView.setRunState("fail", "pmb_replay", modules);
        }
    }

    private void writeProjectedMotionControllerPreflight(Intent intent) {
        Instant startedAt = Instant.now();
        String hostProfile = normalizeHostProfile(intent.getStringExtra("host_profile"));
        List<String> modules = new ArrayList<>();
        modules.add("module.breath.projected_motion");
        modules.add("module.breath.dynamics");
        telemetryView.resetForRun("pmb_controller_preflight", modules);
        telemetryView.setRunState("running", "pmb_controller_preflight", modules);
        File evidenceRoot = new File(getExternalFilesDir(null), "hostess-t/evidence/pmb-controller-preflight");
        File packageRoot = new File(getExternalFilesDir(null), "hostess-t/packages/projected-motion-breath");
        try {
            resetDirectory(packageRoot);
            copyPmbPackageAssets(packageRoot);
            JSONObject preflightReport = PMBRuntime.runControllerPreflight(packageRoot.getAbsolutePath());
            Instant endedAt = Instant.now();
            List<String> errors = pmbCoreErrors(preflightReport);
            String status = errors.isEmpty() && "pass".equals(preflightReport.optString("status")) ? "pass" : "fail";
            if (!evidenceRoot.exists() && !evidenceRoot.mkdirs()) {
                throw new IOException("could not create PMB controller preflight evidence folder");
            }
            writeText(new File(evidenceRoot, "latest.controller-preflight-report.json"), preflightReport.toString(2));
            JSONObject evidence = pmbControllerPreflightEvidence(hostProfile, startedAt, endedAt, status, preflightReport, errors, null);
            writeText(new File(evidenceRoot, "latest.json"), evidence.toString(2));
            telemetryView.setRunState(status, "pmb_controller_preflight", modules);
        } catch (IOException | JSONException | RuntimeException ex) {
            Instant endedAt = Instant.now();
            try {
                if (!evidenceRoot.exists()) {
                    evidenceRoot.mkdirs();
                }
                JSONObject preflightReport = pmbFailureControllerPreflightReport(packageRoot.getAbsolutePath(), ex.getMessage());
                writeText(new File(evidenceRoot, "latest.controller-preflight-report.json"), preflightReport.toString(2));
                List<String> errors = new ArrayList<>();
                errors.add(ex.getMessage() == null ? ex.toString() : ex.getMessage());
                JSONObject evidence = pmbControllerPreflightEvidence(hostProfile, startedAt, endedAt, "fail", preflightReport, errors, ex.toString());
                writeText(new File(evidenceRoot, "latest.json"), evidence.toString(2));
            } catch (IOException | JSONException ignored) {
                // The UI state is the fallback signal when app-private evidence cannot be written.
            }
            telemetryView.setRunState("fail", "pmb_controller_preflight", modules);
        }
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
        telemetryView.setRunState("fail", "hr_rr", new ArrayList<>());
        CaptureRun failure = new CaptureRun(this, new Intent(ACTION_RUN).putExtra("mode", "hr_rr"));
        failure.errors.add(code + ": " + message);
        failure.complete("fail");
    }

    private void writeTelemetryRender(Intent intent) {
        String requested = emptyToNull(intent.getStringExtra("render_name"));
        String fileName = requested == null ? "latest-render.png" : requested;
        if (!fileName.endsWith(".png")) {
            fileName = fileName + ".png";
        }
        telemetryView.setPage(normalizeTelemetryPage(intent.getStringExtra("render_page")));
        final String target = normalizeRenderTarget(intent.getStringExtra("render_target"));
        final String safeName = sanitizeFileName(fileName);
        telemetryView.post(() -> renderTelemetryToFile(safeName, target, 0));
    }

    private void renderTelemetryToFile(String safeName, String target, int attempt) {
        if ((telemetryView.getWidth() <= 0 || telemetryView.getHeight() <= 0) && attempt < 4) {
            telemetryView.postDelayed(() -> renderTelemetryToFile(safeName, target, attempt + 1), 250L);
            return;
        }
        try {
            File root = new File(getExternalFilesDir(null), "hostess-t/evidence/render");
            if (!root.exists() && !root.mkdirs()) {
                throw new IOException("could not create render folder");
            }
            File out = new File(root, safeName);
            RenderMetadata metadata = telemetryView.writePng(out);
            writeText(new File(root, safeName + ".json"), renderMetadataJson("pass", target, safeName, metadata, null));
            telemetryView.setRenderStatus("rendered");
        } catch (IOException ex) {
            File root = new File(getExternalFilesDir(null), "hostess-t/evidence/render");
            try {
                if (!root.exists()) {
                    root.mkdirs();
                }
                writeText(new File(root, safeName + ".json"), renderMetadataJson("fail", target, safeName, null, ex.getMessage()));
            } catch (IOException ignored) {
                // Keep the UI state as the fallback signal if the sidecar cannot be written.
            }
            telemetryView.setRenderStatus("render_failed");
        }
    }

    private final class CaptureRun {
        final Context context;
        final String mode;
        final List<String> selectedModules;
        final String hostProfile;
        final String deviceAddress;
        final String deviceNamePrefix;
        final long durationMs;
        final int accRateHz;
        final RmssdBaselineConfig rmssdBaseline;
        final String telemetryPage;
        final Instant startedAt = Instant.now();
        final Object captureLock = new Object();
        final List<String> errors = new ArrayList<>();
        final List<CommandRecord> commands = new ArrayList<>();
        final List<ControlRecord> controlRecords = new ArrayList<>();
        final List<Long> hrHostTimes = new ArrayList<>();
        final List<Integer> heartRates = new ArrayList<>();
        final List<Float> rrIntervalsMs = new ArrayList<>();
        final List<PmdFrameMetric> ecgFrames = new ArrayList<>();
        final List<PmdFrameMetric> accFrames = new ArrayList<>();
        JSONObject graphReport;
        JSONObject runtimeInput;
        String runtimeInputArtifact;
        String graphReportArtifact;
        int malformedFrameCount = 0;
        int stopWriteAttempts = 0;
        boolean finished = false;

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
            this.selectedModules = normalizeModules(intent.getStringExtra("modules"));
            this.hostProfile = normalizeHostProfile(intent.getStringExtra("host_profile"));
            this.deviceAddress = emptyToNull(intent.getStringExtra("device_address"));
            this.deviceNamePrefix = intent.getStringExtra("device_name_prefix") == null
                    ? "Polar H10"
                    : intent.getStringExtra("device_name_prefix");
            this.durationMs = Math.max(1000L, intent.getLongExtra("duration_ms", 10000L));
            this.accRateHz = Math.max(25, intent.getIntExtra("acc_rate_hz", 200));
            this.rmssdBaseline = RmssdBaselineConfig.fromIntent(intent);
            this.telemetryPage = normalizeTelemetryPage(intent.getStringExtra("telemetry_page"));
        }

        void start() {
            if ("module".equals(mode) && selectedModules.isEmpty()) {
                errors.add("module_selection_missing");
                complete("fail");
                return;
            }
            if (selectedModules.contains(MODULE_RMSSD_GAIN) && !selectedModules.contains(MODULE_HRV_WINDOW)) {
                errors.add("module_dependency_missing:module.polar_h10.hrv_window");
                complete("fail");
                return;
            }
            if (selectedModules.contains(MODULE_BREATH_DYNAMICS) && !selectedModules.contains(MODULE_BREATH_VOLUME_FROM_ACC)) {
                errors.add("module_dependency_missing:module.polar_h10.breath_volume_from_acc");
                complete("fail");
                return;
            }
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
            scheduleRuntimePreview();
            handler.postDelayed(() -> {
                if (!scanFinished) {
                    stopScan();
                    errors.add("scan_timeout");
                    complete("fail");
                }
            }, 15000L);
        }

        void close() {
            finished = true;
            handler.removeCallbacks(runtimePreviewRunnable);
            stopScan();
            if (gatt != null) {
                gatt.disconnect();
                gatt.close();
                gatt = null;
            }
        }

        final Runnable runtimePreviewRunnable = new Runnable() {
            @Override
            public void run() {
                if (finished || !usesRustRuntime()) {
                    return;
                }
                try {
                    JSONObject report = runGraph("preview", false);
                    handler.post(() -> telemetryView.addGraphReport(report));
                } catch (IOException | JSONException | RuntimeException ignored) {
                }
                if (!finished) {
                    handler.postDelayed(this, RUNTIME_PREVIEW_INTERVAL_MS);
                }
            }
        };

        private void scheduleRuntimePreview() {
            if (usesRustRuntime()) {
                handler.postDelayed(runtimePreviewRunnable, RUNTIME_PREVIEW_INTERVAL_MS);
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

        private boolean needsHr() {
            if ("hr_rr".equals(mode) || "coherence".equals(mode)) {
                return true;
            }
            return selectedModules.contains(MODULE_HRV_WINDOW)
                    || selectedModules.contains(MODULE_RMSSD_GAIN)
                    || selectedModules.contains(MODULE_COHERENCE)
                    || selectedModules.contains(MODULE_HRVB_RESONANCE_AMPLITUDE);
        }

        private boolean needsAcc() {
            return "acc".equals(mode)
                    || selectedModules.contains(MODULE_BREATH_VOLUME_FROM_ACC)
                    || selectedModules.contains(MODULE_BREATH_DYNAMICS);
        }

        private boolean needsEcg() {
            return "ecg".equals(mode);
        }

        private void setupAfterMtu(BluetoothGatt gatt) {
            if (descriptorsStarted) {
                return;
            }
            descriptorsStarted = true;
            BluetoothGattService hrService = gatt.getService(HEART_RATE_SERVICE);
            BluetoothGattService pmdService = gatt.getService(PMD_SERVICE);
            if (needsHr()) {
                hrCharacteristic = hrService == null ? null : hrService.getCharacteristic(HEART_RATE_MEASUREMENT);
                if (hrCharacteristic == null) {
                    errors.add("heart_rate_characteristic_missing");
                    complete("fail");
                    return;
                }
                descriptorTasks.add(new DescriptorTask(hrCharacteristic, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE));
            }
            if (needsEcg() || needsAcc()) {
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
            if (!needsEcg() && !needsAcc()) {
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
                if (!needsEcg() && !needsAcc()) {
                    complete(computePass() ? "pass" : "fail");
                } else if (gatt != null && !stopWritten) {
                    writeStopCommand(gatt);
                }
            }, durationMs);
        }

        private void writeStopCommand(BluetoothGatt gatt) {
            if (pmdControlCharacteristic == null) {
                errors.add("pmd_control_missing");
                complete("fail");
                return;
            }
            pendingCommand = "stop_stream";
            pmdControlCharacteristic.setValue(buildStopCommand());
            commandInFlight = true;
            if (!gatt.writeCharacteristic(pmdControlCharacteristic)) {
                commandInFlight = false;
                stopWriteAttempts += 1;
                if (!finished && stopWriteAttempts < 4) {
                    handler.postDelayed(() -> writeStopCommand(gatt), 250L);
                    return;
                }
                commands.add(new CommandRecord("stop_stream", "rejected", 1, System.nanoTime()));
                errors.add("command_write_not_started:stop_stream");
                complete("fail");
            }
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
                    synchronized (captureLock) {
                        hrHostTimes.add(System.nanoTime());
                        heartRates.add(reading.bpm);
                        rrIntervalsMs.addAll(reading.rrIntervalsMs);
                    }
                    handler.post(() -> telemetryView.addHeartRate(reading.bpm, reading.rrIntervalsMs, malformedFrameCount));
                } else if (PMD_CONTROL_POINT.equals(uuid)) {
                    ControlRecord record = PolarProtocol.parseControl(value);
                    synchronized (captureLock) {
                        controlRecords.add(record);
                    }
                } else if (PMD_DATA.equals(uuid)) {
                    if ("ecg".equals(mode)) {
                        PmdFrameMetric frame = PolarProtocol.decodeEcg(value);
                        synchronized (captureLock) {
                            ecgFrames.add(frame);
                        }
                        handler.post(() -> telemetryView.addEcgFrame(frame, malformedFrameCount));
                    } else if (needsAcc()) {
                        PmdFrameMetric frame = PolarProtocol.decodeAcc(value);
                        synchronized (captureLock) {
                            accFrames.add(frame);
                        }
                        handler.post(() -> telemetryView.addAccFrame(frame, malformedFrameCount));
                    }
                }
            } catch (RuntimeException ex) {
                malformedFrameCount += 1;
                handler.post(() -> telemetryView.setMalformedFrameCount(malformedFrameCount));
            }
        }

        private byte[] buildGetSettingsCommand() {
            return new byte[] {0x01, measurementType()};
        }

        private byte[] buildStartCommand() {
            if (needsEcg()) {
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
            return needsEcg() ? (byte) 0x00 : (byte) 0x02;
        }

        private boolean computePass() {
            if (!errors.isEmpty()) {
                return false;
            }
            List<Integer> heartRateSnapshot = heartRateSnapshot();
            List<Float> rrSnapshot = rrSnapshot();
            List<PmdFrameMetric> ecgSnapshot = ecgFrameSnapshot();
            List<PmdFrameMetric> accSnapshot = accFrameSnapshot();
            if ("hr_rr".equals(mode)) {
                return !heartRateSnapshot.isEmpty() && !rrSnapshot.isEmpty();
            }
            if ("coherence".equals(mode)) {
                return Coherence.compute(rrSnapshot).pass;
            }
            if ("ecg".equals(mode)) {
                return decodedSampleCount(ecgSnapshot) > 0;
            }
            if ("acc".equals(mode)) {
                return decodedSampleCount(accSnapshot) > 0;
            }
            if ("module".equals(mode)) {
                boolean hrReady = !needsHr() || (!heartRateSnapshot.isEmpty() && !rrSnapshot.isEmpty());
                boolean accReady = !needsAcc() || decodedSampleCount(accSnapshot) > 0;
                return !selectedModules.isEmpty() && hrReady && accReady;
            }
            return false;
        }

        private boolean modulePass(String moduleId) {
            if (MODULE_HRV_WINDOW.equals(moduleId)) {
                return HrvWindow.compute(rrIntervalsMs).pass;
            }
            if (MODULE_RMSSD_GAIN.equals(moduleId)) {
                return RmssdGain.compute(rrIntervalsMs).pass;
            }
            if (MODULE_COHERENCE.equals(moduleId)) {
                return Coherence.compute(rrIntervalsMs).pass;
            }
            if (MODULE_BREATH_VOLUME_FROM_ACC.equals(moduleId)) {
                return BreathVolume.compute(accFrames, accRateHz).pass;
            }
            if (MODULE_BREATH_DYNAMICS.equals(moduleId)) {
                return BreathDynamics.compute(accFrames, accRateHz).pass;
            }
            if (MODULE_HRVB_RESONANCE_AMPLITUDE.equals(moduleId)) {
                return HrvbResonance.compute(rrIntervalsMs).pass;
            }
            return false;
        }

        private int decodedSampleCount(List<PmdFrameMetric> frames) {
            int count = 0;
            for (PmdFrameMetric frame : frames) {
                count += frame.sampleCount;
            }
            return count;
        }

        private List<Integer> heartRateSnapshot() {
            synchronized (captureLock) {
                return new ArrayList<>(heartRates);
            }
        }

        private List<Float> rrSnapshot() {
            synchronized (captureLock) {
                return new ArrayList<>(rrIntervalsMs);
            }
        }

        private List<PmdFrameMetric> ecgFrameSnapshot() {
            synchronized (captureLock) {
                return new ArrayList<>(ecgFrames);
            }
        }

        private List<PmdFrameMetric> accFrameSnapshot() {
            synchronized (captureLock) {
                return new ArrayList<>(accFrames);
            }
        }

        private boolean usesRustRuntime() {
            return "module".equals(mode) || "coherence".equals(mode);
        }

        private List<String> runtimeSelectedModules() {
            if ("coherence".equals(mode) && selectedModules.isEmpty()) {
                List<String> modules = new ArrayList<>();
                modules.add(MODULE_COHERENCE);
                return modules;
            }
            return selectedModules;
        }

        private JSONObject runGraph(String inputIdSuffix, boolean persist) throws JSONException, IOException {
            List<String> modules = runtimeSelectedModules();
            JSONObject input = runtimeInput("input.polar_h10.live." + inputIdSuffix);
            JSONObject report = PolarRuntime.runGraph(context, input, modules);
            if (persist) {
                runtimeInput = input;
                graphReport = report;
                runtimeInputArtifact = "latest.runtime-input.json";
                graphReportArtifact = "latest.graph-execution-report.json";
            }
            return report;
        }

        private JSONObject runtimeInput(String inputId) throws JSONException {
            List<Integer> heartRateSnapshot = heartRateSnapshot();
            List<Float> rrSnapshot = rrSnapshot();
            List<PmdFrameMetric> accSnapshot = accFrameSnapshot();
            JSONObject input = new JSONObject();
            input.put("$schema", "rusty.manifold.polar_h10.processor_runtime_input.v1");
            input.put("input_id", inputId);
            JSONObject hrRr = new JSONObject();
            hrRr.put("heart_rate_event_count", heartRateSnapshot.size());
            JSONArray rrValues = new JSONArray();
            for (Float rr : rrSnapshot) {
                if (rr != null) {
                    rrValues.put(rr.doubleValue());
                }
            }
            hrRr.put("rr_intervals_ms", rrValues);
            input.put("hr_rr", hrRr);
            if (!accSnapshot.isEmpty()) {
                JSONObject rawAcc = new JSONObject();
                rawAcc.put("sample_rate_hz", (double) accRateHz);
                JSONArray frames = new JSONArray();
                for (PmdFrameMetric frame : accSnapshot) {
                    JSONObject frameJson = new JSONObject();
                    frameJson.put("sensor_timestamp_ns", frame.sensorTimestampNs);
                    JSONArray samples = new JSONArray();
                    for (AccSample sample : frame.accSamples) {
                        JSONObject sampleJson = new JSONObject();
                        sampleJson.put("x_mg", sample.xMg);
                        sampleJson.put("y_mg", sample.yMg);
                        sampleJson.put("z_mg", sample.zMg);
                        samples.put(sampleJson);
                    }
                    frameJson.put("samples_mg", samples);
                    frames.put(frameJson);
                }
                rawAcc.put("frames", frames);
                input.put("raw_acc", rawAcc);
            }
            if (rmssdBaseline != null) {
                input.put("rmssd_gain_baseline", rmssdBaseline.toJson());
            }
            return input;
        }

        private void complete(String status) {
            JSONObject finalGraphReport = null;
            if (usesRustRuntime()) {
                try {
                    finalGraphReport = runGraph("final", true);
                    commands.add(new CommandRecord(
                            "run_graph_live_capture",
                            "pass".equals(finalGraphReport.optString("status")) ? "acknowledged" : "rejected",
                            "pass".equals(finalGraphReport.optString("status")) ? 0 : 1,
                            System.nanoTime()));
                    if (!"pass".equals(finalGraphReport.optString("status"))) {
                        errors.addAll(graphErrors(finalGraphReport));
                        status = "fail";
                    }
                } catch (IOException | JSONException | RuntimeException ex) {
                    errors.add("runtime_bridge_failed:" + ex.getClass().getSimpleName());
                    commands.add(new CommandRecord("run_graph_live_capture", "rejected", 1, System.nanoTime()));
                    status = "fail";
                }
            }
            close();
            Instant endedAt = Instant.now();
            String json = new EvidenceWriter().write(this, status, endedAt);
            try {
                File root = new File(getExternalFilesDir(null), "hostess-t/evidence/live-capture");
                if (!root.exists() && !root.mkdirs()) {
                    throw new IOException("could not create output folder");
                }
                if (runtimeInput != null) {
                    writeText(new File(root, "latest.runtime-input.json"), runtimeInput.toString(2));
                }
                if (graphReport != null) {
                    writeText(new File(root, "latest.graph-execution-report.json"), graphReport.toString(2));
                }
                writeText(new File(root, "latest.json"), json);
                writeText(new File(root, sanitizeFileName(hostProfile + "-" + mode + "-" + endedAt.toString()) + ".json"), json);
                if (finalGraphReport != null) {
                    telemetryView.addGraphReport(finalGraphReport);
                }
                telemetryView.setRunState(status, mode, selectedModules);
            } catch (IOException | JSONException ex) {
                telemetryView.setRunState("write_failed", mode, selectedModules);
            }
        }
    }

    private static String renderMetadataJson(String status, String target, String imageName, RenderMetadata metadata, String error) {
        StringBuilder builder = new StringBuilder();
        builder.append("{\n");
        builder.append("  \"").append("$schema").append("\": \"rusty.hostess.telemetry.render_evidence.v1\",\n");
        builder.append("  \"status\": ").append(jsonQuote(status)).append(",\n");
        builder.append("  \"rendered_at_utc\": ").append(jsonQuote(Instant.now().toString())).append(",\n");
        builder.append("  \"target\": ").append(jsonQuote(target)).append(",\n");
        builder.append("  \"render_page\": ").append(jsonQuote(metadata == null ? "unknown" : metadata.page)).append(",\n");
        builder.append("  \"image_path\": ").append(jsonQuote(imageName)).append(",\n");
        builder.append("  \"source_evidence_path\": \"hostess-t/evidence/live-capture/latest.json\",\n");
        builder.append("  \"width\": ").append(metadata == null ? 0 : metadata.width).append(",\n");
        builder.append("  \"height\": ").append(metadata == null ? 0 : metadata.height).append(",\n");
        builder.append("  \"content_pixel_count\": ").append(metadata == null ? 0 : metadata.contentPixelCount).append(",\n");
        builder.append("  \"validation\": {\n");
        builder.append("    \"min_width\": ").append(MIN_RENDER_WIDTH).append(",\n");
        builder.append("    \"min_height\": ").append(MIN_RENDER_HEIGHT).append(",\n");
        builder.append("    \"min_content_pixels\": ").append(MIN_RENDER_CONTENT_PIXELS).append("\n");
        builder.append("  }");
        if (error != null) {
            builder.append(",\n  \"error\": ").append(jsonQuote(error)).append("\n");
        } else {
            builder.append("\n");
        }
        builder.append("}\n");
        return builder.toString();
    }

    private static String jsonQuote(String value) {
        StringBuilder builder = new StringBuilder("\"");
        String safe = value == null ? "" : value;
        for (int index = 0; index < safe.length(); index++) {
            char ch = safe.charAt(index);
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

    private static final class RenderMetadata {
        final int width;
        final int height;
        final int contentPixelCount;
        final String page;

        RenderMetadata(int width, int height, int contentPixelCount, String page) {
            this.width = width;
            this.height = height;
            this.contentPixelCount = contentPixelCount;
            this.page = page;
        }
    }

    // Fallback/debug-only platform renderer. Makepad is the intended Hostess GUI surface.
    private static final class PlatformDebugTelemetryView extends View {
        private static final int MAX_POINTS = 240;
        private static final int BACKGROUND = Color.rgb(248, 248, 246);
        private static final int SURFACE = Color.WHITE;
        private static final int BORDER = Color.rgb(214, 211, 205);
        private static final int GRID = Color.rgb(231, 229, 224);
        private static final int TEXT = Color.rgb(29, 29, 27);
        private static final int MUTED = Color.rgb(92, 88, 82);
        private static final int HR = Color.rgb(185, 60, 20);
        private static final int RR = Color.rgb(15, 118, 110);
        private static final int ACC = Color.rgb(79, 76, 71);
        private static final int ECG = Color.rgb(159, 18, 57);
        private static final int HRV = Color.rgb(37, 99, 235);
        private static final int MODULE = Color.rgb(126, 34, 206);

        private final Paint fillPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint strokePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint textPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint plotPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Path path = new Path();
        private final RectF rect = new RectF();
        private final ArrayDeque<Float> heartRates = new ArrayDeque<>();
        private final ArrayDeque<Float> rrIntervals = new ArrayDeque<>();
        private final ArrayDeque<Float> accMagnitude = new ArrayDeque<>();
        private final ArrayDeque<Float> ecgSamples = new ArrayDeque<>();
        private final ArrayDeque<Float> hrvLnRmssd = new ArrayDeque<>();
        private final ArrayDeque<Float> rmssdGain = new ArrayDeque<>();
        private final ArrayDeque<Float> coherenceScore = new ArrayDeque<>();
        private final ArrayDeque<Float> breathVolume = new ArrayDeque<>();
        private final ArrayDeque<Float> breathingRate = new ArrayDeque<>();
        private final ArrayDeque<Float> hrvbAmplitude = new ArrayDeque<>();

        private String status = "ready";
        private String mode = "idle";
        private String page = "raw";
        private String renderStatus = "";
        private String graphStatus = "waiting";
        private int selectedModuleCount = 0;
        private int hrEventCount = 0;
        private int rrCount = 0;
        private int accFrameCount = 0;
        private int accSampleCount = 0;
        private int ecgFrameCount = 0;
        private int ecgSampleCount = 0;
        private int malformedFrameCount = 0;

        PlatformDebugTelemetryView(Context context) {
            super(context);
            setBackgroundColor(BACKGROUND);
            plotPaint.setStyle(Paint.Style.STROKE);
            plotPaint.setStrokeCap(Paint.Cap.ROUND);
            plotPaint.setStrokeJoin(Paint.Join.ROUND);
            plotPaint.setStrokeWidth(dp(2));
            strokePaint.setStyle(Paint.Style.STROKE);
            strokePaint.setStrokeWidth(dp(1));
        }

        void resetForRun(String mode, List<String> modules) {
            this.mode = mode;
            selectedModuleCount = modules.size();
            heartRates.clear();
            rrIntervals.clear();
            accMagnitude.clear();
            ecgSamples.clear();
            hrvLnRmssd.clear();
            rmssdGain.clear();
            coherenceScore.clear();
            breathVolume.clear();
            breathingRate.clear();
            hrvbAmplitude.clear();
            hrEventCount = 0;
            rrCount = 0;
            accFrameCount = 0;
            accSampleCount = 0;
            ecgFrameCount = 0;
            ecgSampleCount = 0;
            malformedFrameCount = 0;
            renderStatus = "";
            graphStatus = modules.isEmpty() ? "direct" : "waiting";
            invalidate();
        }

        void setPage(String page) {
            this.page = page == null ? "raw" : page;
            invalidate();
        }

        void setRunState(String status, String mode, List<String> modules) {
            this.status = status;
            this.mode = mode;
            selectedModuleCount = modules.size();
            if (modules.isEmpty()) {
                graphStatus = "direct";
            }
            invalidate();
        }

        void addGraphReport(JSONObject report) {
            graphStatus = report.optString("status", "unknown");
            JSONArray streams = report.optJSONArray("streams");
            if (streams == null) {
                invalidate();
                return;
            }
            for (int index = 0; index < streams.length(); index++) {
                JSONObject stream = streams.optJSONObject(index);
                if (stream == null || !"pass".equals(stream.optString("status"))) {
                    continue;
                }
                String streamId = stream.optString("stream_id");
                if (STREAM_HRV_WINDOW.equals(streamId)) {
                    append(hrvLnRmssd, (float) stream.optDouble("ln_rmssd", 0.0));
                } else if (STREAM_RMSSD_GAIN.equals(streamId)) {
                    append(rmssdGain, (float) stream.optDouble("ln_rmssd_gain", 0.0));
                } else if (STREAM_COHERENCE.equals(streamId)) {
                    append(coherenceScore, (float) stream.optDouble("normalized_score", 0.0));
                } else if (STREAM_BREATH_VOLUME.equals(streamId)) {
                    append(breathVolume, (float) stream.optDouble("breath_volume_01", 0.0));
                } else if (STREAM_BREATH_DYNAMICS.equals(streamId)) {
                    append(breathingRate, (float) stream.optDouble("breathing_rate_bpm", 0.0));
                } else if (STREAM_HRVB_RESONANCE_AMPLITUDE.equals(streamId)) {
                    append(hrvbAmplitude, (float) stream.optDouble("amplitude_bpm", 0.0));
                }
            }
            invalidate();
        }

        void addHeartRate(int bpm, List<Float> rrIntervalsMs, int malformed) {
            hrEventCount += 1;
            append(heartRates, bpm);
            for (Float rr : rrIntervalsMs) {
                if (rr != null) {
                    rrCount += 1;
                    append(rrIntervals, rr);
                }
            }
            malformedFrameCount = malformed;
            invalidate();
        }

        void addAccFrame(PmdFrameMetric frame, int malformed) {
            accFrameCount += 1;
            accSampleCount += frame.sampleCount;
            for (AccSample sample : frame.accSamples) {
                double magnitude = Math.sqrt(
                        (sample.xMg * sample.xMg)
                                + (sample.yMg * sample.yMg)
                                + (sample.zMg * sample.zMg));
                append(accMagnitude, (float) magnitude);
            }
            malformedFrameCount = malformed;
            invalidate();
        }

        void addEcgFrame(PmdFrameMetric frame, int malformed) {
            ecgFrameCount += 1;
            ecgSampleCount += frame.sampleCount;
            for (Integer sample : frame.ecgSamplesMicrovolts) {
                append(ecgSamples, sample.floatValue());
            }
            malformedFrameCount = malformed;
            invalidate();
        }

        void setMalformedFrameCount(int count) {
            malformedFrameCount = count;
            invalidate();
        }

        void setRenderStatus(String status) {
            renderStatus = status == null ? "" : status;
            invalidate();
        }

        RenderMetadata writePng(File out) throws IOException {
            int width = Math.max(getWidth(), 1);
            int height = Math.max(getHeight(), 1);
            if (width < MIN_RENDER_WIDTH || height < MIN_RENDER_HEIGHT) {
                throw new IOException("telemetry render too small: " + width + "x" + height);
            }
            Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            try {
                Canvas canvas = new Canvas(bitmap);
                draw(canvas);
                int firstPixel = bitmap.getPixel(0, 0);
                int contentPixels = 0;
                for (int y = 0; y < height; y++) {
                    for (int x = 0; x < width; x++) {
                        if (bitmap.getPixel(x, y) != firstPixel) {
                            contentPixels += 1;
                        }
                    }
                }
                if (contentPixels < MIN_RENDER_CONTENT_PIXELS) {
                    throw new IOException("telemetry render appears blank: " + contentPixels + " content pixels");
                }
                try (FileOutputStream stream = new FileOutputStream(out)) {
                    if (!bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)) {
                        throw new IOException("could not encode telemetry render");
                    }
                }
                return new RenderMetadata(width, height, contentPixels, page);
            } finally {
                bitmap.recycle();
            }
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            canvas.drawColor(BACKGROUND);
            float width = getWidth();
            float height = getHeight();
            float margin = dp(14);
            float headerHeight = dp(82);
            drawHeader(canvas, margin, margin, width - margin * 2, headerHeight);
            float top = margin + headerHeight + dp(10);
            float gap = dp(8);
            if ("modules".equals(page)) {
                float available = Math.max(dp(336), height - top - margin - gap * 5);
                float rowHeight = Math.max(dp(46), available / 6.0f);
                drawPlot(canvas, "HRV", latestText(hrvLnRmssd, "lnRMSSD"), hrvLnRmssd.size() + " reports", hrvLnRmssd, HRV, margin, top, width - margin * 2, rowHeight);
                top += rowHeight + gap;
                drawPlot(canvas, "GAIN", latestText(rmssdGain, "ln"), rmssdGain.size() + " reports", rmssdGain, MODULE, margin, top, width - margin * 2, rowHeight);
                top += rowHeight + gap;
                drawPlot(canvas, "COH", latestText(coherenceScore, "score"), coherenceScore.size() + " reports", coherenceScore, RR, margin, top, width - margin * 2, rowHeight);
                top += rowHeight + gap;
                drawPlot(canvas, "VOL", latestText(breathVolume, "01"), breathVolume.size() + " reports", breathVolume, ACC, margin, top, width - margin * 2, rowHeight);
                top += rowHeight + gap;
                drawPlot(canvas, "BR", latestText(breathingRate, "bpm"), breathingRate.size() + " reports", breathingRate, HR, margin, top, width - margin * 2, rowHeight);
                top += rowHeight + gap;
                drawPlot(canvas, "HRVB", latestText(hrvbAmplitude, "bpm"), hrvbAmplitude.size() + " reports", hrvbAmplitude, ECG, margin, top, width - margin * 2, rowHeight);
            } else {
                float available = Math.max(dp(224), height - top - margin - gap * 3);
                float rowHeight = Math.max(dp(56), available / 4.0f);
                drawPlot(canvas, "HR", latestText(heartRates, "bpm"), hrEventCount + " events", heartRates, HR, margin, top, width - margin * 2, rowHeight);
                top += rowHeight + gap;
                drawPlot(canvas, "RR", latestText(rrIntervals, "ms"), rrCount + " intervals", rrIntervals, RR, margin, top, width - margin * 2, rowHeight);
                top += rowHeight + gap;
                drawPlot(canvas, "ACC", latestText(accMagnitude, "mg"), accFrameCount + " frames / " + accSampleCount + " samples", accMagnitude, ACC, margin, top, width - margin * 2, rowHeight);
                top += rowHeight + gap;
                drawPlot(canvas, "ECG", latestText(ecgSamples, "uV"), ecgFrameCount + " frames / " + ecgSampleCount + " samples", ecgSamples, ECG, margin, top, width - margin * 2, rowHeight);
            }
        }

        private void drawHeader(Canvas canvas, float left, float top, float width, float height) {
            drawPanel(canvas, left, top, width, height);
            textPaint.setColor(TEXT);
            textPaint.setTextSize(sp(20));
            textPaint.setFakeBoldText(true);
            canvas.drawText("Rusty Hostess T", left + dp(14), top + dp(28), textPaint);
            textPaint.setFakeBoldText(false);
            textPaint.setTextSize(sp(14));
            textPaint.setColor(MUTED);
            canvas.drawText(status + " / " + mode, left + dp(14), top + dp(52), textPaint);
            String selection = selectedModuleCount > 0 ? selectedModuleCount + " modules" : "direct stream";
            String detail = page + " / " + selection + " / " + graphStatus + " / bad " + malformedFrameCount;
            if (!renderStatus.isEmpty()) {
                detail += " / " + renderStatus;
            }
            canvas.drawText(detail, left + dp(14), top + dp(72), textPaint);
        }

        private void drawPlot(
                Canvas canvas,
                String label,
                String value,
                String count,
                ArrayDeque<Float> series,
                int color,
                float left,
                float top,
                float width,
                float height) {
            drawPanel(canvas, left, top, width, height);
            float labelLeft = left + dp(12);
            textPaint.setTextSize(sp(14));
            textPaint.setFakeBoldText(true);
            textPaint.setColor(TEXT);
            canvas.drawText(label, labelLeft, top + dp(22), textPaint);
            textPaint.setFakeBoldText(false);
            textPaint.setColor(MUTED);
            canvas.drawText(value, labelLeft, top + dp(42), textPaint);
            float plotLeft = left + dp(92);
            float plotTop = top + dp(14);
            float plotWidth = Math.max(dp(80), width - dp(106));
            float plotHeight = Math.max(dp(40), height - dp(26));
            canvas.drawText(count, plotLeft, top + height - dp(12), textPaint);
            strokePaint.setColor(GRID);
            canvas.drawLine(plotLeft, plotTop + plotHeight / 2.0f, plotLeft + plotWidth, plotTop + plotHeight / 2.0f, strokePaint);
            drawSeries(canvas, series, color, plotLeft, plotTop, plotWidth, plotHeight);
        }

        private void drawSeries(Canvas canvas, ArrayDeque<Float> series, int color, float left, float top, float width, float height) {
            if (series.isEmpty()) {
                textPaint.setTextSize(sp(13));
                textPaint.setColor(MUTED);
                canvas.drawText("waiting", left + dp(6), top + height / 2.0f, textPaint);
                return;
            }
            if (series.size() == 1) {
                plotPaint.setColor(color);
                canvas.drawCircle(left + width / 2.0f, top + height / 2.0f, dp(4), plotPaint);
                return;
            }
            float min = Float.MAX_VALUE;
            float max = -Float.MAX_VALUE;
            for (float value : series) {
                min = Math.min(min, value);
                max = Math.max(max, value);
            }
            if (Math.abs(max - min) < 0.0001f) {
                max += 1.0f;
                min -= 1.0f;
            }
            path.reset();
            int index = 0;
            int size = series.size();
            for (float value : series) {
                float x = left + (size == 1 ? 0.0f : (index * width / (size - 1)));
                float y = top + height - ((value - min) / (max - min) * height);
                if (index == 0) {
                    path.moveTo(x, y);
                } else {
                    path.lineTo(x, y);
                }
                index += 1;
            }
            plotPaint.setColor(color);
            canvas.drawPath(path, plotPaint);
        }

        private void drawPanel(Canvas canvas, float left, float top, float width, float height) {
            rect.set(left, top, left + width, top + height);
            fillPaint.setStyle(Paint.Style.FILL);
            fillPaint.setColor(SURFACE);
            canvas.drawRoundRect(rect, dp(8), dp(8), fillPaint);
            strokePaint.setColor(BORDER);
            canvas.drawRoundRect(rect, dp(8), dp(8), strokePaint);
        }

        private void append(ArrayDeque<Float> buffer, float value) {
            buffer.addLast(value);
            while (buffer.size() > MAX_POINTS) {
                buffer.removeFirst();
            }
        }

        private String latestText(ArrayDeque<Float> series, String unit) {
            if (series.isEmpty()) {
                return "-- " + unit;
            }
            return String.format(Locale.US, "%.1f %s", series.peekLast(), unit);
        }

        private float dp(float value) {
            return value * getResources().getDisplayMetrics().density;
        }

        private float sp(float value) {
            return value * getResources().getDisplayMetrics().scaledDensity;
        }
    }

    private static void writeText(File path, String text) throws IOException {
        try (FileOutputStream stream = new FileOutputStream(path)) {
            stream.write(text.getBytes(StandardCharsets.UTF_8));
        }
    }

    private void resetDirectory(File root) throws IOException {
        deleteRecursively(root);
        if (!root.exists() && !root.mkdirs()) {
            throw new IOException("could not create folder: " + root.getAbsolutePath());
        }
    }

    private void deleteRecursively(File path) throws IOException {
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

    private void copyAssetTree(String assetPath, File target) throws IOException {
        String[] children = listAssets(assetPath);
        if (children != null && children.length > 0) {
            Arrays.sort(children);
            if (!target.exists() && !target.mkdirs()) {
                throw new IOException("could not create folder: " + target.getAbsolutePath());
            }
            for (String child : children) {
                copyAssetTree(assetPath + "/" + child, new File(target, child));
            }
            return;
        }
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("could not create folder: " + parent.getAbsolutePath());
        }
        try (InputStream input = openAsset(assetPath); FileOutputStream output = new FileOutputStream(target)) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) >= 0) {
                output.write(buffer, 0, read);
            }
        }
    }

    private void copyPmbPackageAssets(File targetRoot) throws IOException {
        for (String relative : pmbPackageAssetFiles()) {
            copyAssetFile(PMB_ASSET_ROOT + "/" + relative, new File(targetRoot, relative.replace('/', File.separatorChar)));
        }
    }

    private List<String> pmbPackageAssetFiles() throws IOException {
        List<String> files = new ArrayList<>();
        String manifest = readAssetText(PMB_ASSET_ROOT + "/package-files.txt");
        for (String rawFile : manifest.split("\\r?\\n")) {
            String relative = rawFile.trim();
            if (!relative.isEmpty() && !relative.contains("..")) {
                files.add(relative);
            }
        }
        return files;
    }

    private void copyAssetFile(String assetPath, File target) throws IOException {
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("could not create folder: " + parent.getAbsolutePath());
        }
        try (InputStream input = openAsset(assetPath); FileOutputStream output = new FileOutputStream(target)) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) >= 0) {
                output.write(buffer, 0, read);
            }
        }
    }

    private String readAssetText(String assetPath) throws IOException {
        try (InputStream input = openAsset(assetPath)) {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            byte[] bytes = new byte[8192];
            int read;
            while ((read = input.read(bytes)) >= 0) {
                buffer.write(bytes, 0, read);
            }
            return buffer.toString(StandardCharsets.UTF_8.name());
        }
    }

    private JSONObject pmbReplayEvidence(
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
        evidence.put("package", pmbPackageSnapshot());
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

    private JSONObject pmbControllerPreflightEvidence(
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
        evidence.put("package", pmbPackageSnapshot());
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

    private JSONObject pmbPackageSnapshot() throws JSONException {
        return new JSONObject()
                .put("package_id", PMB_PACKAGE_ID)
                .put("package_manifest_sha256", assetSha256(PMB_ASSET_ROOT + "/manifests/package.manifold.json"))
                .put("stream_manifest_sha256", pmbManifestHashes("streams"))
                .put("module_manifest_sha256", pmbManifestHashes("modules"))
                .put("command_manifest_sha256", pmbManifestHashes("commands"));
    }

    private JSONObject pmbManifestHashes(String manifestFolder) throws JSONException {
        JSONObject hashes = new JSONObject();
        String folder = PMB_ASSET_ROOT + "/manifests/" + manifestFolder;
        try {
            String prefix = "manifests/" + manifestFolder + "/";
            for (String relative : pmbPackageAssetFiles()) {
                if (relative.startsWith(prefix) && relative.endsWith(".json")) {
                    String file = relative.substring(prefix.length());
                    hashes.put(file.substring(0, file.length() - 5), assetSha256(PMB_ASSET_ROOT + "/" + relative));
                }
            }
            if (hashes.length() > 0) {
                return hashes;
            }
            String[] files = listAssets(folder);
            if (files == null) {
                return hashes;
            }
            Arrays.sort(files);
            for (String file : files) {
                if (file.endsWith(".json")) {
                    hashes.put(file.substring(0, file.length() - 5), assetSha256(folder + "/" + file));
                }
            }
        } catch (IOException ignored) {
        }
        return hashes;
    }

    private String[] listAssets(String path) throws IOException {
        String[] children = getAssets().list(path);
        if (children != null && children.length > 0) {
            return children;
        }
        String fallback = path.replace('/', '\\');
        if (!fallback.equals(path)) {
            String[] fallbackChildren = getAssets().list(fallback);
            if (fallbackChildren != null && fallbackChildren.length > 0) {
                return fallbackChildren;
            }
        }
        return children;
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

    private static List<String> pmbCoreErrors(JSONObject coreReport) {
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

    private static JSONObject pmbFailureCoreReport(String packageRoot, String message) throws JSONException {
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

    private static JSONObject pmbFailureControllerPreflightReport(String packageRoot, String message) throws JSONException {
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
            return getAssets().open(path);
        } catch (IOException first) {
            return getAssets().open(path.replace('/', '\\'));
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder builder = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) {
            builder.append(String.format(Locale.US, "%02x", value & 0xff));
        }
        return builder.toString();
    }

    private static String normalizeMode(String mode) {
        if ("ecg".equals(mode) || "acc".equals(mode) || "hr_rr".equals(mode) || "coherence".equals(mode) || "module".equals(mode)) {
            return mode;
        }
        return "hr_rr";
    }

    private static List<String> normalizeModules(String rawModules) {
        List<String> modules = new ArrayList<>();
        if (rawModules == null || rawModules.trim().isEmpty()) {
            return modules;
        }
        String[] pieces = rawModules.split(",");
        for (String piece : pieces) {
            String module = normalizeModule(piece.trim());
            if (module != null && !modules.contains(module)) {
                modules.add(module);
            }
        }
        return modules;
    }

    private static List<String> defaultProcessorModules() {
        List<String> modules = new ArrayList<>();
        modules.add(MODULE_HRV_WINDOW);
        modules.add(MODULE_RMSSD_GAIN);
        modules.add(MODULE_COHERENCE);
        modules.add(MODULE_BREATH_VOLUME_FROM_ACC);
        modules.add(MODULE_BREATH_DYNAMICS);
        modules.add(MODULE_HRVB_RESONANCE_AMPLITUDE);
        return modules;
    }

    private static List<String> graphErrors(JSONObject graphReport) {
        List<String> errors = new ArrayList<>();
        JSONArray issues = graphReport.optJSONArray("issues");
        if (issues == null) {
            return errors;
        }
        for (int index = 0; index < issues.length(); index++) {
            JSONObject issue = issues.optJSONObject(index);
            if (issue != null) {
                errors.add(issue.optString("message", issue.optString("issue_code", "graph_issue")));
            }
        }
        return errors;
    }

    private static String normalizeModule(String value) {
        if (MODULE_HRV_WINDOW.equals(value) || "hrv_window".equals(value)) {
            return MODULE_HRV_WINDOW;
        }
        if (MODULE_RMSSD_GAIN.equals(value) || "rmssd_gain".equals(value)) {
            return MODULE_RMSSD_GAIN;
        }
        if (MODULE_COHERENCE.equals(value) || "coherence".equals(value)) {
            return MODULE_COHERENCE;
        }
        if (MODULE_BREATH_VOLUME_FROM_ACC.equals(value) || "breath_volume_from_acc".equals(value) || "breath_volume".equals(value)) {
            return MODULE_BREATH_VOLUME_FROM_ACC;
        }
        if (MODULE_BREATH_DYNAMICS.equals(value) || "breath_dynamics".equals(value)) {
            return MODULE_BREATH_DYNAMICS;
        }
        if (MODULE_HRVB_RESONANCE_AMPLITUDE.equals(value) || "hrvb_resonance_amplitude".equals(value)) {
            return MODULE_HRVB_RESONANCE_AMPLITUDE;
        }
        return null;
    }

    private static String normalizeHostProfile(String hostProfile) {
        if ("headset".equals(hostProfile) || "mobile".equals(hostProfile)) {
            return hostProfile;
        }
        return "mobile";
    }

    private static String normalizeTelemetryPage(String page) {
        if ("modules".equals(page) || "raw".equals(page)) {
            return page;
        }
        return "raw";
    }

    private static String normalizeRenderTarget(String target) {
        if ("quest".equals(target) || "phone".equals(target)) {
            return target;
        }
        return "android-class";
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
        final List<AccSample> accSamples;
        final List<Integer> ecgSamplesMicrovolts;

        PmdFrameMetric(long hostTimeNs, long sensorTimestampNs, int sampleCount) {
            this(hostTimeNs, sensorTimestampNs, sampleCount, new ArrayList<>(), new ArrayList<>());
        }

        PmdFrameMetric(long hostTimeNs, long sensorTimestampNs, int sampleCount, List<AccSample> accSamples) {
            this(hostTimeNs, sensorTimestampNs, sampleCount, accSamples, new ArrayList<>());
        }

        PmdFrameMetric(long hostTimeNs, long sensorTimestampNs, int sampleCount, List<AccSample> accSamples, List<Integer> ecgSamplesMicrovolts) {
            this.hostTimeNs = hostTimeNs;
            this.sensorTimestampNs = sensorTimestampNs;
            this.sampleCount = sampleCount;
            this.accSamples = accSamples;
            this.ecgSamplesMicrovolts = ecgSamplesMicrovolts;
        }
    }

    private static final class AccSample {
        final int xMg;
        final int yMg;
        final int zMg;

        AccSample(int xMg, int yMg, int zMg) {
            this.xMg = xMg;
            this.yMg = yMg;
            this.zMg = zMg;
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

    private static final class RmssdBaselineConfig {
        final double baselineLnRmssd;
        final double baselineMeanLnRmssd;
        final double baselineSdLnRmssd;
        final int baselineWindowCount;
        final String baselineSource;

        RmssdBaselineConfig(
                double baselineLnRmssd,
                double baselineMeanLnRmssd,
                double baselineSdLnRmssd,
                int baselineWindowCount,
                String baselineSource) {
            this.baselineLnRmssd = baselineLnRmssd;
            this.baselineMeanLnRmssd = baselineMeanLnRmssd;
            this.baselineSdLnRmssd = baselineSdLnRmssd;
            this.baselineWindowCount = baselineWindowCount;
            this.baselineSource = baselineSource;
        }

        static RmssdBaselineConfig fromIntent(Intent intent) {
            if (!intent.hasExtra("rmssd_baseline_ln_rmssd")
                    || !intent.hasExtra("rmssd_baseline_mean_ln_rmssd")
                    || !intent.hasExtra("rmssd_baseline_sd_ln_rmssd")
                    || !intent.hasExtra("rmssd_baseline_window_count")) {
                return null;
            }
            return new RmssdBaselineConfig(
                    doubleExtra(intent, "rmssd_baseline_ln_rmssd"),
                    doubleExtra(intent, "rmssd_baseline_mean_ln_rmssd"),
                    doubleExtra(intent, "rmssd_baseline_sd_ln_rmssd"),
                    (int) doubleExtra(intent, "rmssd_baseline_window_count"),
                    intent.getStringExtra("rmssd_baseline_source") == null
                            ? "run_config_baseline"
                            : intent.getStringExtra("rmssd_baseline_source"));
        }

        private static double doubleExtra(Intent intent, String name) {
            Bundle extras = intent.getExtras();
            if (extras == null || !extras.containsKey(name)) {
                return 0.0;
            }
            Object value = extras.get(name);
            if (value instanceof Number) {
                return ((Number) value).doubleValue();
            }
            if (value instanceof String) {
                try {
                    return Double.parseDouble((String) value);
                } catch (NumberFormatException ignored) {
                    return 0.0;
                }
            }
            return 0.0;
        }

        JSONObject toJson() throws JSONException {
            JSONObject json = new JSONObject();
            json.put("baseline_ln_rmssd", baselineLnRmssd);
            json.put("baseline_mean_ln_rmssd", baselineMeanLnRmssd);
            json.put("baseline_sd_ln_rmssd", baselineSdLnRmssd);
            json.put("baseline_window_count", baselineWindowCount);
            json.put("baseline_source", baselineSource);
            return json;
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
            List<Integer> samples = new ArrayList<>();
            for (int offset = 10; offset < data.length; offset += 3) {
                samples.add(readInt24(data, offset));
            }
            return new PmdFrameMetric(System.nanoTime(), readUInt64(data, 1), body / 3, new ArrayList<>(), samples);
        }

        static PmdFrameMetric decodeAcc(byte[] data) {
            validatePmd(data, 0x02, 0x01);
            int body = data.length - 10;
            if (body <= 0 || body % 6 != 0) {
                throw new IllegalArgumentException("bad ACC length");
            }
            List<AccSample> samples = new ArrayList<>();
            for (int offset = 10; offset < data.length; offset += 6) {
                samples.add(new AccSample(readInt16(data, offset), readInt16(data, offset + 2), readInt16(data, offset + 4)));
            }
            return new PmdFrameMetric(System.nanoTime(), readUInt64(data, 1), body / 6, samples);
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

        static int readInt16(byte[] data, int offset) {
            int value = readUInt16(data, offset);
            return (value & 0x8000) != 0 ? value - 0x10000 : value;
        }

        static int readInt24(byte[] data, int offset) {
            if (offset + 2 >= data.length) {
                throw new IllegalArgumentException("short i24");
            }
            int value = unsigned(data[offset]) | (unsigned(data[offset + 1]) << 8) | (unsigned(data[offset + 2]) << 16);
            return (value & 0x800000) != 0 ? value - 0x1000000 : value;
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

    private static final class CoherenceResult {
        final boolean pass;
        final String issueCode;
        final int inputRrIntervalCount;
        final int uniformSampleCount;
        final double windowSeconds;
        final double sampleRateHz;
        final Double peakFrequencyHz;
        final Double peakBandPower;
        final Double totalBandPower;
        final Double remainingPower;
        final Double coherenceRatio;
        final Double coherenceRatioSquared;
        final Double normalizedPeakPower;
        final Double paperRatio;
        final Double normalizedScore;
        final String quality;

        CoherenceResult(
                boolean pass,
                String issueCode,
                int inputRrIntervalCount,
                int uniformSampleCount,
                double windowSeconds,
                double sampleRateHz,
                Double peakFrequencyHz,
                Double peakBandPower,
                Double totalBandPower,
                Double remainingPower,
                Double coherenceRatio,
                Double coherenceRatioSquared,
                Double normalizedPeakPower,
                Double paperRatio,
                Double normalizedScore,
                String quality) {
            this.pass = pass;
            this.issueCode = issueCode;
            this.inputRrIntervalCount = inputRrIntervalCount;
            this.uniformSampleCount = uniformSampleCount;
            this.windowSeconds = windowSeconds;
            this.sampleRateHz = sampleRateHz;
            this.peakFrequencyHz = peakFrequencyHz;
            this.peakBandPower = peakBandPower;
            this.totalBandPower = totalBandPower;
            this.remainingPower = remainingPower;
            this.coherenceRatio = coherenceRatio;
            this.coherenceRatioSquared = coherenceRatioSquared;
            this.normalizedPeakPower = normalizedPeakPower;
            this.paperRatio = paperRatio;
            this.normalizedScore = normalizedScore;
            this.quality = quality;
        }
    }

    private static final class Coherence {
        static final double SAMPLE_RATE_HZ = 2.0;
        static final double WINDOW_SECONDS = 64.0;
        static final int FFT_LENGTH = 128;
        static final double TOTAL_BAND_LOW_HZ = 0.0033;
        static final double TOTAL_BAND_HIGH_HZ = 0.4;
        static final double PEAK_SEARCH_LOW_HZ = 0.04;
        static final double PEAK_SEARCH_HIGH_HZ = 0.26;
        static final double PEAK_HALF_WIDTH_HZ = 0.03;

        static CoherenceResult compute(List<Float> rrIntervalsMs) {
            List<Double> usable = new ArrayList<>();
            for (Float value : rrIntervalsMs) {
                if (value != null && value >= 300.0f && value <= 2000.0f) {
                    usable.add(value.doubleValue());
                }
            }
            if (usable.size() < 12) {
                return failure("issue.window_underfilled", usable.size(), 0);
            }

            double[] beatTimes = new double[usable.size()];
            double elapsed = 0.0;
            for (int index = 0; index < usable.size(); index++) {
                elapsed += usable.get(index) / 1000.0;
                beatTimes[index] = elapsed;
            }
            if (elapsed < WINDOW_SECONDS) {
                return failure("issue.window_underfilled", usable.size(), 0);
            }
            double windowStart = elapsed - WINDOW_SECONDS;
            if (beatTimes[0] > windowStart) {
                return failure("issue.window_underfilled", usable.size(), 0);
            }

            double[] samples = new double[FFT_LENGTH];
            int beatIndex = 0;
            int sampleCount = 0;
            for (int sampleIndex = 0; sampleIndex < FFT_LENGTH; sampleIndex++) {
                double sampleTime = windowStart + (sampleIndex / SAMPLE_RATE_HZ);
                while (beatIndex + 1 < beatTimes.length && beatTimes[beatIndex + 1] < sampleTime) {
                    beatIndex += 1;
                }
                if (beatIndex + 1 >= beatTimes.length) {
                    break;
                }
                double leftTime = beatTimes[beatIndex];
                double rightTime = beatTimes[beatIndex + 1];
                double leftRr = usable.get(beatIndex);
                double rightRr = usable.get(beatIndex + 1);
                double sample = leftRr;
                if (rightTime > leftTime) {
                    double fraction = (sampleTime - leftTime) / (rightTime - leftTime);
                    sample = leftRr + ((rightRr - leftRr) * fraction);
                }
                samples[sampleIndex] = sample;
                sampleCount += 1;
            }
            if (sampleCount < FFT_LENGTH) {
                return failure("issue.window_underfilled", usable.size(), sampleCount);
            }
            return computeUniform(samples, usable.size());
        }

        static CoherenceResult computeUniform(double[] samples, int inputRrIntervalCount) {
            double mean = 0.0;
            for (double sample : samples) {
                mean += sample;
            }
            mean /= samples.length;

            double[] detrended = new double[samples.length];
            for (int index = 0; index < samples.length; index++) {
                detrended[index] = samples[index] - mean;
            }

            double totalBandPower = 0.0;
            double peakCandidatePower = -1.0;
            int peakBin = -1;
            double peakFrequencyHz = 0.0;
            double[] powers = new double[(samples.length / 2) + 1];
            double[] frequencies = new double[(samples.length / 2) + 1];
            for (int bin = 1; bin <= samples.length / 2; bin++) {
                double real = 0.0;
                double imaginary = 0.0;
                for (int sampleIndex = 0; sampleIndex < detrended.length; sampleIndex++) {
                    double angle = -2.0 * Math.PI * bin * sampleIndex / samples.length;
                    real += detrended[sampleIndex] * Math.cos(angle);
                    imaginary += detrended[sampleIndex] * Math.sin(angle);
                }
                double frequency = bin * SAMPLE_RATE_HZ / samples.length;
                double power = ((real * real) + (imaginary * imaginary)) / (samples.length * samples.length);
                powers[bin] = power;
                frequencies[bin] = frequency;
                if (inBand(frequency, TOTAL_BAND_LOW_HZ, TOTAL_BAND_HIGH_HZ)) {
                    totalBandPower += power;
                }
                if (inBand(frequency, PEAK_SEARCH_LOW_HZ, PEAK_SEARCH_HIGH_HZ)
                        && (power > peakCandidatePower + 0.000000000001 || (Math.abs(power - peakCandidatePower) <= 0.000000000001 && bin < peakBin))) {
                    peakCandidatePower = power;
                    peakBin = bin;
                    peakFrequencyHz = frequency;
                }
            }
            if (totalBandPower <= 0.0 || peakBin <= 0) {
                return failure("issue.quality_low", inputRrIntervalCount, samples.length);
            }

            double peakBandPower = 0.0;
            for (int bin = 1; bin <= samples.length / 2; bin++) {
                if (inBand(frequencies[bin], TOTAL_BAND_LOW_HZ, TOTAL_BAND_HIGH_HZ)
                        && Math.abs(frequencies[bin] - peakFrequencyHz) <= PEAK_HALF_WIDTH_HZ + 0.000000000001) {
                    peakBandPower += powers[bin];
                }
            }
            double remainingPower = totalBandPower - peakBandPower;
            double paperRatio = remainingPower <= 0.0 ? 1000000.0 : peakBandPower / remainingPower;
            double coherenceRatioSquared = paperRatio * paperRatio;
            double normalizedPeakPower = totalBandPower <= 0.0 ? 0.0 : peakBandPower / totalBandPower;
            double normalizedScore = paperRatio / (paperRatio + 1.0);
            return new CoherenceResult(
                    true,
                    null,
                    inputRrIntervalCount,
                    samples.length,
                    WINDOW_SECONDS,
                    SAMPLE_RATE_HZ,
                    round6(peakFrequencyHz),
                    round6(peakBandPower),
                    round6(totalBandPower),
                    round6(remainingPower),
                    round6(paperRatio),
                    round6(coherenceRatioSquared),
                    round6(normalizedPeakPower),
                    round6(paperRatio),
                    round6(normalizedScore),
                    paperRatio >= 2.0 ? "stable" : "distributed");
        }

        static CoherenceResult failure(String issueCode, int inputRrIntervalCount, int uniformSampleCount) {
            return new CoherenceResult(
                    false,
                    issueCode,
                    inputRrIntervalCount,
                    uniformSampleCount,
                    WINDOW_SECONDS,
                    SAMPLE_RATE_HZ,
                    null,
                    null,
                    null,
                    null,
                    null,
                    null,
                    null,
                    null,
                    null,
                    null);
        }

        static boolean inBand(double frequency, double low, double high) {
            return frequency >= low && frequency <= high;
        }

        static double round6(double value) {
            return Math.round(value * 1000000.0) / 1000000.0;
        }
    }

    private static final class HrvWindowResult {
        final boolean pass;
        final String issueCode;
        final int inputCount;
        final int acceptedCount;
        final int rejectedCount;
        final int successiveDifferenceCount;
        final Double meanNnMs;
        final Double meanHrBpm;
        final Double sdnnMs;
        final Double rmssdMs;
        final Double lnRmssd;
        final Double pnn50;
        final Double sd1Ms;
        final String quality;

        HrvWindowResult(boolean pass, String issueCode, int inputCount, int acceptedCount, int rejectedCount,
                        int successiveDifferenceCount, Double meanNnMs, Double meanHrBpm, Double sdnnMs,
                        Double rmssdMs, Double lnRmssd, Double pnn50, Double sd1Ms, String quality) {
            this.pass = pass;
            this.issueCode = issueCode;
            this.inputCount = inputCount;
            this.acceptedCount = acceptedCount;
            this.rejectedCount = rejectedCount;
            this.successiveDifferenceCount = successiveDifferenceCount;
            this.meanNnMs = meanNnMs;
            this.meanHrBpm = meanHrBpm;
            this.sdnnMs = sdnnMs;
            this.rmssdMs = rmssdMs;
            this.lnRmssd = lnRmssd;
            this.pnn50 = pnn50;
            this.sd1Ms = sd1Ms;
            this.quality = quality;
        }
    }

    private static final class HrvWindow {
        static HrvWindowResult compute(List<Float> rrIntervalsMs) {
            List<Double> usable = usableRr(rrIntervalsMs);
            int rejected = rrIntervalsMs.size() - usable.size();
            if (usable.size() < 2) {
                return failure("issue.window_underfilled", rrIntervalsMs.size(), usable.size(), rejected);
            }
            if (rejected > 0) {
                return failure("issue.quality_low", rrIntervalsMs.size(), usable.size(), rejected);
            }
            List<Double> diffs = new ArrayList<>();
            for (int index = 1; index < usable.size(); index++) {
                diffs.add(usable.get(index) - usable.get(index - 1));
            }
            double rmssd = rmssd(usable);
            double mean = mean(usable);
            double pnn50 = 0.0;
            for (double diff : diffs) {
                if (Math.abs(diff) > 50.0) {
                    pnn50 += 1.0;
                }
            }
            pnn50 = 100.0 * pnn50 / diffs.size();
            return new HrvWindowResult(
                    true,
                    null,
                    rrIntervalsMs.size(),
                    usable.size(),
                    rejected,
                    diffs.size(),
                    round6(mean),
                    round6(60000.0 / mean),
                    round6(sampleSd(usable)),
                    round6(rmssd),
                    rmssd > 0.0 ? round6(Math.log(rmssd)) : null,
                    round6(pnn50),
                    round6(rmssd / Math.sqrt(2.0)),
                    "stable");
        }

        static HrvWindowResult failure(String issueCode, int inputCount, int acceptedCount, int rejectedCount) {
            return new HrvWindowResult(false, issueCode, inputCount, acceptedCount, rejectedCount,
                    Math.max(0, acceptedCount - 1), null, null, null, null, null, null, null, null);
        }
    }

    private static final class RmssdGainResult {
        final boolean pass;
        final String issueCode;
        final int baselineCount;
        final int currentCount;
        final Double baselineRmssdMs;
        final Double currentRmssdMs;
        final Double ratio;
        final Double lnGain;
        final String quality;

        RmssdGainResult(boolean pass, String issueCode, int baselineCount, int currentCount,
                        Double baselineRmssdMs, Double currentRmssdMs, Double ratio, Double lnGain, String quality) {
            this.pass = pass;
            this.issueCode = issueCode;
            this.baselineCount = baselineCount;
            this.currentCount = currentCount;
            this.baselineRmssdMs = baselineRmssdMs;
            this.currentRmssdMs = currentRmssdMs;
            this.ratio = ratio;
            this.lnGain = lnGain;
            this.quality = quality;
        }
    }

    private static final class RmssdGain {
        static RmssdGainResult compute(List<Float> rrIntervalsMs) {
            List<Double> usable = usableRr(rrIntervalsMs);
            if (usable.size() < 12) {
                return failure("issue.baseline_underfilled", 0, 0);
            }
            int windowCount = Math.min(30, Math.max(6, usable.size() / 3));
            if (usable.size() < windowCount * 2) {
                return failure("issue.baseline_underfilled", windowCount, usable.size() - windowCount);
            }
            List<Double> baseline = new ArrayList<>(usable.subList(0, windowCount));
            List<Double> current = new ArrayList<>(usable.subList(usable.size() - windowCount, usable.size()));
            double baselineRmssd = rmssd(baseline);
            double currentRmssd = rmssd(current);
            if (baselineRmssd <= 0.0) {
                return failure("issue.baseline_invalid", baseline.size(), current.size());
            }
            double ratio = currentRmssd / baselineRmssd;
            return new RmssdGainResult(true, null, baseline.size(), current.size(), round6(baselineRmssd),
                    round6(currentRmssd), round6(ratio), ratio > 0.0 ? round6(Math.log(ratio)) : null, "stable");
        }

        static RmssdGainResult failure(String issueCode, int baselineCount, int currentCount) {
            return new RmssdGainResult(false, issueCode, baselineCount, currentCount, null, null, null, null, null);
        }
    }

    private static final class BreathSeries {
        final boolean pass;
        final String issueCode;
        final int sampleCount;
        final String axis;
        final Double lower;
        final Double upper;
        final List<Double> times;
        final List<Double> values;
        final Double confidence;
        final String quality;

        BreathSeries(boolean pass, String issueCode, int sampleCount, String axis, Double lower, Double upper,
                     List<Double> times, List<Double> values, Double confidence, String quality) {
            this.pass = pass;
            this.issueCode = issueCode;
            this.sampleCount = sampleCount;
            this.axis = axis;
            this.lower = lower;
            this.upper = upper;
            this.times = times;
            this.values = values;
            this.confidence = confidence;
            this.quality = quality;
        }
    }

    private static final class BreathVolumeResult {
        final boolean pass;
        final String issueCode;
        final int sampleCount;
        final int calibrationCount;
        final String axis;
        final Double lower;
        final Double upper;
        final Double volume;
        final String phase;
        final Double confidence;
        final String quality;

        BreathVolumeResult(boolean pass, String issueCode, int sampleCount, int calibrationCount, String axis,
                           Double lower, Double upper, Double volume, String phase, Double confidence, String quality) {
            this.pass = pass;
            this.issueCode = issueCode;
            this.sampleCount = sampleCount;
            this.calibrationCount = calibrationCount;
            this.axis = axis;
            this.lower = lower;
            this.upper = upper;
            this.volume = volume;
            this.phase = phase;
            this.confidence = confidence;
            this.quality = quality;
        }
    }

    private static final class BreathVolume {
        static BreathVolumeResult compute(List<PmdFrameMetric> frames, int accRateHz) {
            BreathSeries series = breathSeries(frames, accRateHz);
            if (!series.pass || series.values.isEmpty()) {
                return new BreathVolumeResult(false, series.issueCode, series.sampleCount, series.sampleCount,
                        series.axis, series.lower, series.upper, null, null, series.confidence, series.quality);
            }
            double latest = series.values.get(series.values.size() - 1);
            double previous = series.values.size() > 1 ? series.values.get(series.values.size() - 2) : latest;
            return new BreathVolumeResult(true, null, series.sampleCount, series.sampleCount, series.axis,
                    series.lower, series.upper, round6(latest), latest >= previous ? "inhale" : "exhale",
                    series.confidence, series.quality);
        }
    }

    private static final class BreathDynamicsResult {
        final boolean pass;
        final String issueCode;
        final int inputCount;
        final int cycleCount;
        final Double meanInterval;
        final Double breathingRate;
        final Double intervalSd;
        final Double intervalCv;
        final Double meanAmplitude;
        final Double amplitudeSd;
        final Double amplitudeCv;
        final String complexityStatus;
        final String quality;

        BreathDynamicsResult(boolean pass, String issueCode, int inputCount, int cycleCount, Double meanInterval,
                             Double breathingRate, Double intervalSd, Double intervalCv, Double meanAmplitude,
                             Double amplitudeSd, Double amplitudeCv, String complexityStatus, String quality) {
            this.pass = pass;
            this.issueCode = issueCode;
            this.inputCount = inputCount;
            this.cycleCount = cycleCount;
            this.meanInterval = meanInterval;
            this.breathingRate = breathingRate;
            this.intervalSd = intervalSd;
            this.intervalCv = intervalCv;
            this.meanAmplitude = meanAmplitude;
            this.amplitudeSd = amplitudeSd;
            this.amplitudeCv = amplitudeCv;
            this.complexityStatus = complexityStatus;
            this.quality = quality;
        }
    }

    private static final class BreathDynamics {
        static BreathDynamicsResult compute(List<PmdFrameMetric> frames, int accRateHz) {
            BreathSeries series = breathSeries(frames, accRateHz);
            if (!series.pass) {
                return failure(series.issueCode, series.sampleCount);
            }
            List<TimeValue> downsampled = downsample(series.times, series.values, 10.0);
            if (downsampled.size() < 30) {
                return failure("issue.window_underfilled", series.sampleCount);
            }
            List<Double> times = new ArrayList<>();
            List<Double> values = new ArrayList<>();
            for (TimeValue item : downsampled) {
                times.add(item.time);
                values.add(item.value);
            }
            values = movingAverage(values, 5);
            double midpoint = median(values);
            List<Double> crossings = new ArrayList<>();
            for (int index = 1; index < values.size(); index++) {
                double left = values.get(index - 1) - midpoint;
                double right = values.get(index) - midpoint;
                if (left < 0.0 && right >= 0.0) {
                    double span = right - left;
                    double fraction = span == 0.0 ? 0.0 : -left / span;
                    crossings.add(times.get(index - 1) + (times.get(index) - times.get(index - 1)) * fraction);
                }
            }
            List<Double> intervals = new ArrayList<>();
            List<Double> amplitudes = new ArrayList<>();
            for (int index = 1; index < crossings.size(); index++) {
                double interval = crossings.get(index) - crossings.get(index - 1);
                if (interval >= 1.5 && interval <= 12.0) {
                    intervals.add(interval);
                }
                double min = Double.MAX_VALUE;
                double max = -Double.MAX_VALUE;
                for (int valueIndex = 0; valueIndex < times.size(); valueIndex++) {
                    double time = times.get(valueIndex);
                    if (time >= crossings.get(index - 1) && time <= crossings.get(index)) {
                        min = Math.min(min, values.get(valueIndex));
                        max = Math.max(max, values.get(valueIndex));
                    }
                }
                if (max > min) {
                    amplitudes.add(max - min);
                }
            }
            if (intervals.size() < 2 || amplitudes.size() < 2) {
                return failure("issue.window_underfilled", series.sampleCount);
            }
            double meanInterval = mean(intervals);
            double intervalSd = sampleSd(intervals);
            double meanAmplitude = mean(amplitudes);
            double amplitudeSd = sampleSd(amplitudes);
            return new BreathDynamicsResult(true, null, series.sampleCount, intervals.size(), round6(meanInterval),
                    round6(60.0 / meanInterval), round6(intervalSd), meanInterval > 0.0 ? round6(intervalSd / meanInterval) : null,
                    round6(meanAmplitude), round6(amplitudeSd), meanAmplitude > 0.0 ? round6(amplitudeSd / meanAmplitude) : null,
                    "underfilled", "stable");
        }

        static BreathDynamicsResult failure(String issueCode, int inputCount) {
            return new BreathDynamicsResult(false, issueCode, inputCount, 0, null, null, null, null, null, null, null, null, null);
        }
    }

    private static final class HrvbResult {
        final boolean pass;
        final String issueCode;
        final int inputCount;
        final Double amplitude;
        final Double meanHr;
        final Double frequency;
        final Double omega;
        final Double phase;
        final Double medianAmplitude;
        final String thresholdStatus;
        final String quality;

        HrvbResult(boolean pass, String issueCode, int inputCount, Double amplitude, Double meanHr,
                   Double frequency, Double omega, Double phase, Double medianAmplitude, String thresholdStatus, String quality) {
            this.pass = pass;
            this.issueCode = issueCode;
            this.inputCount = inputCount;
            this.amplitude = amplitude;
            this.meanHr = meanHr;
            this.frequency = frequency;
            this.omega = omega;
            this.phase = phase;
            this.medianAmplitude = medianAmplitude;
            this.thresholdStatus = thresholdStatus;
            this.quality = quality;
        }
    }

    private static final class HrvbResonance {
        static HrvbResult compute(List<Float> rrIntervalsMs) {
            List<Double> usable = usableRr(rrIntervalsMs);
            if (usable.size() < 30) {
                return failure("issue.window_underfilled", usable.size());
            }
            List<TimeValue> heartRates = new ArrayList<>();
            double elapsed = 0.0;
            for (double rr : usable) {
                elapsed += rr / 1000.0;
                heartRates.add(new TimeValue(elapsed, 60000.0 / rr));
            }
            if (elapsed < 30.0) {
                return failure("issue.window_underfilled", usable.size());
            }
            double windowStart = elapsed - 30.0;
            List<TimeValue> window = new ArrayList<>();
            for (TimeValue item : heartRates) {
                if (item.time >= windowStart) {
                    window.add(new TimeValue(item.time - windowStart, item.value));
                }
            }
            if (window.size() < 20) {
                return failure("issue.window_underfilled", usable.size());
            }
            List<Double> values = new ArrayList<>();
            for (TimeValue item : window) {
                values.add(item.value);
            }
            double meanHr = mean(values);
            double bestAmplitude = -1.0;
            double bestFrequency = 0.1;
            double bestPhase = 0.0;
            for (int step = 0; step <= 40; step++) {
                double frequency = 0.08 + step * 0.001;
                double omega = 2.0 * Math.PI * frequency;
                double sin = 0.0;
                double cos = 0.0;
                for (TimeValue item : window) {
                    double centered = item.value - meanHr;
                    sin += centered * Math.sin(omega * item.time);
                    cos += centered * Math.cos(omega * item.time);
                }
                sin *= 2.0 / window.size();
                cos *= 2.0 / window.size();
                double amplitude = Math.sqrt((sin * sin) + (cos * cos));
                if (amplitude > bestAmplitude) {
                    bestAmplitude = amplitude;
                    bestFrequency = frequency;
                    bestPhase = Math.atan2(cos, sin);
                }
            }
            return new HrvbResult(true, null, usable.size(), round6(bestAmplitude), round6(meanHr),
                    round6(bestFrequency), round6(2.0 * Math.PI * bestFrequency), round6(bestPhase),
                    round6(bestAmplitude), bestAmplitude >= 2.0 ? "above_source_threshold" : "below_source_threshold", "stable");
        }

        static HrvbResult failure(String issueCode, int inputCount) {
            return new HrvbResult(false, issueCode, inputCount, null, null, null, null, null, null, null, null);
        }
    }

    private static final class TimeValue {
        final double time;
        final double value;

        TimeValue(double time, double value) {
            this.time = time;
            this.value = value;
        }
    }

    private static List<Double> usableRr(List<Float> rrIntervalsMs) {
        List<Double> usable = new ArrayList<>();
        for (Float value : rrIntervalsMs) {
            if (value != null && value >= 300.0f && value <= 2000.0f) {
                usable.add(value.doubleValue());
            }
        }
        return usable;
    }

    private static double rmssd(List<Double> values) {
        if (values.size() < 2) {
            return 0.0;
        }
        double sum = 0.0;
        for (int index = 1; index < values.size(); index++) {
            double diff = values.get(index) - values.get(index - 1);
            sum += diff * diff;
        }
        return Math.sqrt(sum / (values.size() - 1));
    }

    private static double mean(List<Double> values) {
        double sum = 0.0;
        for (double value : values) {
            sum += value;
        }
        return values.isEmpty() ? 0.0 : sum / values.size();
    }

    private static double sampleSd(List<Double> values) {
        if (values.size() < 2) {
            return 0.0;
        }
        double mean = mean(values);
        double sum = 0.0;
        for (double value : values) {
            sum += (value - mean) * (value - mean);
        }
        return Math.sqrt(Math.max(0.0, sum / (values.size() - 1)));
    }

    private static double median(List<Double> values) {
        if (values.isEmpty()) {
            return 0.0;
        }
        List<Double> ordered = new ArrayList<>(values);
        ordered.sort(Double::compareTo);
        int middle = ordered.size() / 2;
        if ((ordered.size() % 2) == 1) {
            return ordered.get(middle);
        }
        return (ordered.get(middle - 1) + ordered.get(middle)) / 2.0;
    }

    private static double quantile(List<Double> values, double fraction) {
        if (values.isEmpty()) {
            return 0.0;
        }
        List<Double> ordered = new ArrayList<>(values);
        ordered.sort(Double::compareTo);
        double position = Math.max(0.0, Math.min(1.0, fraction)) * (ordered.size() - 1);
        int lower = (int) Math.floor(position);
        int upper = (int) Math.ceil(position);
        if (lower == upper) {
            return ordered.get(lower);
        }
        double weight = position - lower;
        return ordered.get(lower) + (ordered.get(upper) - ordered.get(lower)) * weight;
    }

    private static double clamp(double value, double lower, double upper) {
        return Math.max(lower, Math.min(upper, value));
    }

    private static BreathSeries breathSeries(List<PmdFrameMetric> frames, int accRateHz) {
        List<TimeValue> xValues = new ArrayList<>();
        List<TimeValue> yValues = new ArrayList<>();
        List<TimeValue> zValues = new ArrayList<>();
        double samplePeriod = 1.0 / Math.max(1, accRateHz);
        Long firstTimestamp = null;
        for (PmdFrameMetric frame : frames) {
            if (firstTimestamp == null) {
                firstTimestamp = frame.sensorTimestampNs;
            }
            double frameStart = (frame.sensorTimestampNs - firstTimestamp) / 1_000_000_000.0;
            for (int index = 0; index < frame.accSamples.size(); index++) {
                AccSample sample = frame.accSamples.get(index);
                double time = frameStart + index * samplePeriod;
                xValues.add(new TimeValue(time, sample.xMg));
                yValues.add(new TimeValue(time, sample.yMg));
                zValues.add(new TimeValue(time, sample.zMg));
            }
        }
        int sampleCount = xValues.size();
        if (sampleCount < Math.max(20, accRateHz / 2)) {
            return new BreathSeries(false, "issue.calibration_underfilled", sampleCount, null, null, null,
                    new ArrayList<>(), new ArrayList<>(), null, null);
        }
        List<TimeValue> best = xValues;
        String axis = "x";
        double bestSpan = span(xValues);
        double ySpan = span(yValues);
        if (ySpan > bestSpan) {
            best = yValues;
            axis = "y";
            bestSpan = ySpan;
        }
        double zSpan = span(zValues);
        if (zSpan > bestSpan) {
            best = zValues;
            axis = "z";
            bestSpan = zSpan;
        }
        List<Double> raw = new ArrayList<>();
        List<Double> times = new ArrayList<>();
        for (TimeValue item : best) {
            times.add(item.time);
            raw.add(item.value);
        }
        double lower = quantile(raw, 0.05);
        double upper = quantile(raw, 0.95);
        if (upper - lower <= 0.000001) {
            return new BreathSeries(false, "issue.calibration_invalid", sampleCount, axis, round6(lower), round6(upper),
                    new ArrayList<>(), new ArrayList<>(), null, null);
        }
        List<Double> normalized = new ArrayList<>();
        for (double value : raw) {
            normalized.add(clamp((value - lower) / (upper - lower), 0.0, 1.0));
        }
        double confidence = clamp((upper - lower) / 80.0, 0.0, 1.0);
        return new BreathSeries(true, null, sampleCount, axis, round6(lower), round6(upper), times, normalized,
                round6(confidence), confidence >= 0.2 ? "stable" : "low_motion");
    }

    private static double span(List<TimeValue> values) {
        List<Double> raw = new ArrayList<>();
        for (TimeValue value : values) {
            raw.add(value.value);
        }
        return quantile(raw, 0.95) - quantile(raw, 0.05);
    }

    private static List<TimeValue> downsample(List<Double> times, List<Double> values, double rateHz) {
        List<TimeValue> output = new ArrayList<>();
        if (times.isEmpty()) {
            return output;
        }
        int currentBucket = (int) Math.floor(times.get(0) * rateHz);
        double sum = 0.0;
        int count = 0;
        for (int index = 0; index < times.size(); index++) {
            int bucket = (int) Math.floor(times.get(index) * rateHz);
            if (bucket != currentBucket && count > 0) {
                output.add(new TimeValue(currentBucket / rateHz, sum / count));
                currentBucket = bucket;
                sum = 0.0;
                count = 0;
            }
            sum += values.get(index);
            count += 1;
        }
        if (count > 0) {
            output.add(new TimeValue(currentBucket / rateHz, sum / count));
        }
        return output;
    }

    private static List<Double> movingAverage(List<Double> values, int radius) {
        List<Double> output = new ArrayList<>();
        for (int index = 0; index < values.size(); index++) {
            int start = Math.max(0, index - radius);
            int end = Math.min(values.size(), index + radius + 1);
            double sum = 0.0;
            for (int item = start; item < end; item++) {
                sum += values.get(item);
            }
            output.add(sum / (end - start));
        }
        return output;
    }

    private static double round6(double value) {
        return Math.round(value * 1000000.0) / 1000000.0;
    }

    private final class EvidenceWriter {
        String write(CaptureRun run, String status, Instant endedAt) {
            PackageHashes hashes = packageHashes();
            List<String> evidenceErrors = new ArrayList<>(run.errors);
            if (!hashes.complete()) {
                evidenceErrors.add("package_manifest_hash_unavailable");
            }
            String finalStatus = evidenceErrors.isEmpty() ? status : "fail";
            StringBuilder builder = new StringBuilder();
            builder.append("{\n");
            field(builder, "$schema", "rusty.manifold.live_capture_evidence.v1", true, 1);
            field(builder, "status", finalStatus, true, 1);
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
            field(builder, "package_manifest_sha256", hashes.packageManifest, true, 2);
            indent(builder, 2).append("\"stream_manifest_sha256\": {\n");
            field(builder, "hr-rr", hashes.hrRrStream, true, 3);
            field(builder, "ecg", hashes.ecgStream, true, 3);
            field(builder, "acc", hashes.accStream, true, 3);
            field(builder, "coherence", hashes.coherenceStream, true, 3);
            field(builder, "hrv-window", hashes.hrvWindowStream, true, 3);
            field(builder, "rmssd-gain", hashes.rmssdGainStream, true, 3);
            field(builder, "breath-volume", hashes.breathVolumeStream, true, 3);
            field(builder, "breath-dynamics", hashes.breathDynamicsStream, true, 3);
            field(builder, "hrvb-resonance-amplitude", hashes.hrvbResonanceAmplitudeStream, false, 3);
            indent(builder, 2).append("},\n");
            indent(builder, 2).append("\"module_manifest_sha256\": {\n");
            field(builder, "provider", hashes.providerModule, true, 3);
            field(builder, "coherence", hashes.coherenceModule, true, 3);
            field(builder, "hrv-window", hashes.hrvWindowModule, true, 3);
            field(builder, "rmssd-gain", hashes.rmssdGainModule, true, 3);
            field(builder, "breath-volume-from-acc", hashes.breathVolumeModule, true, 3);
            field(builder, "breath-dynamics", hashes.breathDynamicsModule, true, 3);
            field(builder, "hrvb-resonance-amplitude", hashes.hrvbResonanceAmplitudeModule, false, 3);
            indent(builder, 2).append("}\n");
            indent(builder, 1).append("},\n");
            indent(builder, 1).append("\"capture\": {\n");
            field(builder, "mode", run.mode, true, 2);
            stringArrayField(builder, "selected_module_ids", run.selectedModules, true, 2);
            stringArrayField(builder, "dependency_stream_ids", dependencyStreams(run), true, 2);
            if (run.graphReport != null) {
                field(builder, "runtime_path", run.graphReport.optString("runtime_path", PolarRuntime.RUNTIME_PATH), true, 2);
                field(builder, "graph_id", run.graphReport.optString("graph_id", "graph.polar_h10_processing"), true, 2);
                numberField(builder, "graph_revision", run.graphReport.optLong("graph_revision", 0), true, 2);
                field(builder, "runtime_input", run.runtimeInputArtifact == null ? "latest.runtime-input.json" : run.runtimeInputArtifact, true, 2);
                field(builder, "graph_execution_report", run.graphReportArtifact == null ? "latest.graph-execution-report.json" : run.graphReportArtifact, true, 2);
            }
            numberField(builder, "duration_ms", run.durationMs, true, 2);
            boolField(builder, "address_supplied", run.deviceAddress != null, false, 2);
            indent(builder, 1).append("},\n");
            appendCommands(builder, run);
            appendControl(builder, run);
            appendStreams(builder, run);
            appendErrors(builder, evidenceErrors);
            builder.append("}\n");
            return builder.toString();
        }

        String writeReplay(
                String hostProfile,
                List<String> selectedModules,
                Instant startedAt,
                Instant endedAt,
                String status,
                JSONObject graphReport,
                List<String> graphErrors) {
            PackageHashes hashes = packageHashes();
            List<String> evidenceErrors = new ArrayList<>(graphErrors);
            if (!hashes.complete()) {
                evidenceErrors.add("package_manifest_hash_unavailable");
            }
            String finalStatus = evidenceErrors.isEmpty() && "pass".equals(status) ? "pass" : "fail";
            StringBuilder builder = new StringBuilder();
            builder.append("{\n");
            field(builder, "$schema", "rusty.manifold.live_capture_evidence.v1", true, 1);
            field(builder, "status", finalStatus, true, 1);
            field(builder, "host_profile", hostProfile, true, 1);
            field(builder, "started_at_utc", startedAt.toString(), true, 1);
            field(builder, "ended_at_utc", endedAt.toString(), true, 1);
            indent(builder, 1).append("\"software\": {\n");
            field(builder, "origin", SOFTWARE_ORIGIN, true, 2);
            field(builder, "host_app", hostAppId(hostProfile), true, 2);
            field(builder, "host_app_version", "0.1.0", false, 2);
            indent(builder, 1).append("},\n");
            appendPackage(builder, hashes);
            indent(builder, 1).append("\"capture\": {\n");
            field(builder, "mode", "module", true, 2);
            stringArrayField(builder, "selected_module_ids", selectedModules, true, 2);
            graphStringArrayField(builder, "dependency_stream_ids", graphReport.optJSONArray("output_stream_ids"), true, 2);
            field(builder, "runtime_path", graphReport.optString("runtime_path", PolarRuntime.RUNTIME_PATH), true, 2);
            field(builder, "graph_id", graphReport.optString("graph_id", "graph.polar_h10_processing"), true, 2);
            numberField(builder, "graph_revision", graphReport.optLong("graph_revision", 0), true, 2);
            field(builder, "runtime_input", "latest.runtime-input.json", true, 2);
            field(builder, "graph_execution_report", "latest.graph-execution-report.json", true, 2);
            numberField(builder, "duration_ms", Math.max(0L, endedAt.toEpochMilli() - startedAt.toEpochMilli()), true, 2);
            boolField(builder, "address_supplied", false, false, 2);
            indent(builder, 1).append("},\n");
            indent(builder, 1).append("\"commands\": [\n");
            indent(builder, 2).append("{");
            jsonPair(builder, "command", "run_graph_replay").append(", ");
            jsonPair(builder, "status", "pass".equals(graphReport.optString("status")) ? "acknowledged" : "rejected").append(", ");
            jsonPair(builder, "runtime_path", graphReport.optString("runtime_path", PolarRuntime.RUNTIME_PATH));
            builder.append("}\n");
            indent(builder, 1).append("],\n");
            indent(builder, 1).append("\"control_responses\": [],\n");
            appendGraphStreams(builder, graphReport, false);
            appendErrors(builder, evidenceErrors);
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

        private void appendPackage(StringBuilder builder, PackageHashes hashes) {
            indent(builder, 1).append("\"package\": {\n");
            field(builder, "package_id", PACKAGE_ID, true, 2);
            field(builder, "package_manifest_sha256", hashes.packageManifest, true, 2);
            indent(builder, 2).append("\"stream_manifest_sha256\": {\n");
            field(builder, "hr-rr", hashes.hrRrStream, true, 3);
            field(builder, "ecg", hashes.ecgStream, true, 3);
            field(builder, "acc", hashes.accStream, true, 3);
            field(builder, "coherence", hashes.coherenceStream, true, 3);
            field(builder, "hrv-window", hashes.hrvWindowStream, true, 3);
            field(builder, "rmssd-gain", hashes.rmssdGainStream, true, 3);
            field(builder, "breath-volume", hashes.breathVolumeStream, true, 3);
            field(builder, "breath-dynamics", hashes.breathDynamicsStream, true, 3);
            field(builder, "hrvb-resonance-amplitude", hashes.hrvbResonanceAmplitudeStream, false, 3);
            indent(builder, 2).append("},\n");
            indent(builder, 2).append("\"module_manifest_sha256\": {\n");
            field(builder, "provider", hashes.providerModule, true, 3);
            field(builder, "coherence", hashes.coherenceModule, true, 3);
            field(builder, "hrv-window", hashes.hrvWindowModule, true, 3);
            field(builder, "rmssd-gain", hashes.rmssdGainModule, true, 3);
            field(builder, "breath-volume-from-acc", hashes.breathVolumeModule, true, 3);
            field(builder, "breath-dynamics", hashes.breathDynamicsModule, true, 3);
            field(builder, "hrvb-resonance-amplitude", hashes.hrvbResonanceAmplitudeModule, false, 3);
            indent(builder, 2).append("}\n");
            indent(builder, 1).append("},\n");
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

        private void appendGraphStreams(StringBuilder builder, JSONObject graphReport, boolean skipInputs) {
            indent(builder, 1).append("\"streams\": [\n");
            JSONArray streams = graphReport.optJSONArray("streams");
            int emitted = 0;
            if (streams != null) {
                for (int index = 0; index < streams.length(); index++) {
                    JSONObject stream = streams.optJSONObject(index);
                    if (stream == null) {
                        continue;
                    }
                    String streamId = stream.optString("stream_id");
                    if (skipInputs && (STREAM_HR_RR.equals(streamId) || STREAM_ACC.equals(streamId))) {
                        continue;
                    }
                    if (!stream.has("malformed_frame_count")) {
                        try {
                            stream = new JSONObject(stream.toString());
                            stream.put("malformed_frame_count", 0);
                        } catch (JSONException ignored) {
                        }
                    }
                    if (emitted > 0) {
                        builder.append(",\n");
                    }
                    builder.append(indentJson(stream.toString(), 2));
                    emitted += 1;
                }
            }
            builder.append("\n");
            indent(builder, 1).append("],\n");
        }

        private void appendStreams(StringBuilder builder, CaptureRun run) {
            if (run.graphReport != null) {
                indent(builder, 1).append("\"streams\": [\n");
                List<String> streamJson = new ArrayList<>();
                if ("hr_rr".equals(run.mode) || "coherence".equals(run.mode) || run.needsHr()) {
                    streamJson.add(directHrStream(run, "module".equals(run.mode)));
                }
                if ("ecg".equals(run.mode)) {
                    streamJson.add(pmdStream(run, STREAM_ECG, run.ecgFrames, false));
                }
                if ("acc".equals(run.mode) || run.needsAcc()) {
                    streamJson.add(pmdStream(run, STREAM_ACC, run.accFrames, "module".equals(run.mode)));
                }
                JSONArray graphStreams = run.graphReport.optJSONArray("streams");
                if (graphStreams != null) {
                    for (int index = 0; index < graphStreams.length(); index++) {
                        JSONObject stream = graphStreams.optJSONObject(index);
                        if (stream == null) {
                            continue;
                        }
                        String streamId = stream.optString("stream_id");
                        if (STREAM_HR_RR.equals(streamId) || STREAM_ACC.equals(streamId)) {
                            continue;
                        }
                        if (!stream.has("malformed_frame_count")) {
                            try {
                                stream = new JSONObject(stream.toString());
                                stream.put("malformed_frame_count", run.malformedFrameCount);
                            } catch (JSONException ignored) {
                            }
                        }
                        streamJson.add(indentJson(stream.toString(), 2));
                    }
                }
                for (int index = 0; index < streamJson.size(); index++) {
                    builder.append(streamJson.get(index));
                    builder.append(index + 1 == streamJson.size() ? "\n" : ",\n");
                }
                indent(builder, 1).append("],\n");
                return;
            }
            indent(builder, 1).append("\"streams\": [\n");
            List<String> streamJson = new ArrayList<>();
            if ("hr_rr".equals(run.mode) || "coherence".equals(run.mode) || run.needsHr()) {
                streamJson.add(directHrStream(run, "module".equals(run.mode)));
            }
            if ("ecg".equals(run.mode)) {
                streamJson.add(pmdStream(run, STREAM_ECG, run.ecgFrames, false));
            }
            if ("acc".equals(run.mode) || run.needsAcc()) {
                streamJson.add(pmdStream(run, STREAM_ACC, run.accFrames, "module".equals(run.mode)));
            }
            if ("coherence".equals(run.mode) && run.selectedModules.isEmpty()) {
                streamJson.add(moduleStream(run, MODULE_COHERENCE));
            }
            for (String moduleId : run.selectedModules) {
                streamJson.add(moduleStream(run, moduleId));
            }
            for (int index = 0; index < streamJson.size(); index++) {
                builder.append(streamJson.get(index));
                builder.append(index + 1 == streamJson.size() ? "\n" : ",\n");
            }
            indent(builder, 1).append("],\n");
        }

        private String directHrStream(CaptureRun run, boolean moduleInput) {
            StringBuilder builder = new StringBuilder();
            indent(builder, 2).append("{\n");
            field(builder, "stream_id", STREAM_HR_RR, true, 3);
            field(builder, "status", (!run.heartRates.isEmpty() && !run.rrIntervalsMs.isEmpty()) ? "pass" : "fail", true, 3);
            if (moduleInput) {
                field(builder, "role", "module_input", true, 3);
            }
            numberField(builder, "heart_rate_event_count", run.heartRates.size(), true, 3);
            numberField(builder, "rr_interval_count", run.rrIntervalsMs.size(), true, 3);
            numberField(builder, "latest_bpm", run.heartRates.isEmpty() ? 0 : run.heartRates.get(run.heartRates.size() - 1), true, 3);
            doubleField(builder, "host_notification_rate_hz", hostRate(run.hrHostTimes), true, 3);
            numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            indent(builder, 2).append("}");
            return builder.toString();
        }

        private String pmdStream(CaptureRun run, String streamId, List<PmdFrameMetric> frames, boolean moduleInput) {
            StringBuilder builder = new StringBuilder();
            indent(builder, 2).append("{\n");
            field(builder, "stream_id", streamId, true, 3);
            field(builder, "status", run.decodedSampleCount(frames) > 0 ? "pass" : "fail", true, 3);
            if (moduleInput) {
                field(builder, "role", "module_input", true, 3);
            }
            numberField(builder, "frame_count", frames.size(), true, 3);
            numberField(builder, "decoded_sample_count", run.decodedSampleCount(frames), true, 3);
            doubleField(builder, "sensor_sample_rate_hz", sensorRate(frames), true, 3);
            doubleField(builder, "host_notification_rate_hz", pmdHostRate(frames), true, 3);
            numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            indent(builder, 2).append("}");
            return builder.toString();
        }

        private String moduleStream(CaptureRun run, String moduleId) {
            if (MODULE_HRV_WINDOW.equals(moduleId)) {
                return hrvWindowStream(run);
            }
            if (MODULE_RMSSD_GAIN.equals(moduleId)) {
                return rmssdGainStream(run);
            }
            if (MODULE_COHERENCE.equals(moduleId)) {
                return coherenceStream(run);
            }
            if (MODULE_BREATH_VOLUME_FROM_ACC.equals(moduleId)) {
                return breathVolumeStream(run);
            }
            if (MODULE_BREATH_DYNAMICS.equals(moduleId)) {
                return breathDynamicsStream(run);
            }
            return hrvbStream(run);
        }

        private String hrvWindowStream(CaptureRun run) {
            HrvWindowResult result = HrvWindow.compute(run.rrIntervalsMs);
            StringBuilder builder = moduleStreamHeader(STREAM_HRV_WINDOW, MODULE_HRV_WINDOW, result.pass);
            field(builder, "input_stream_id", STREAM_HR_RR, true, 3);
            field(builder, "method", "rr_window_v1", true, 3);
            numberField(builder, "heart_rate_event_count", run.heartRates.size(), true, 3);
            numberField(builder, "input_rr_interval_count", result.inputCount, true, 3);
            numberField(builder, "accepted_count", result.acceptedCount, true, 3);
            numberField(builder, "rejected_count", result.rejectedCount, true, 3);
            numberField(builder, "successive_difference_count", result.successiveDifferenceCount, true, 3);
            nullableDoubleField(builder, "mean_nn_ms", result.meanNnMs, true, 3);
            nullableDoubleField(builder, "mean_hr_bpm", result.meanHrBpm, true, 3);
            nullableDoubleField(builder, "sdnn_ms", result.sdnnMs, true, 3);
            nullableDoubleField(builder, "rmssd_ms", result.rmssdMs, true, 3);
            nullableDoubleField(builder, "ln_rmssd", result.lnRmssd, true, 3);
            nullableDoubleField(builder, "pnn50", result.pnn50, true, 3);
            nullableDoubleField(builder, "sd1_ms", result.sd1Ms, true, 3);
            nullableStringField(builder, "quality", result.quality, true, 3);
            nullableStringField(builder, "issue_code", result.issueCode, true, 3);
            numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            indent(builder, 2).append("}");
            return builder.toString();
        }

        private String rmssdGainStream(CaptureRun run) {
            RmssdGainResult result = RmssdGain.compute(run.rrIntervalsMs);
            StringBuilder builder = moduleStreamHeader(STREAM_RMSSD_GAIN, MODULE_RMSSD_GAIN, result.pass);
            field(builder, "input_stream_id", STREAM_HRV_WINDOW, true, 3);
            field(builder, "method", "log_rmssd_gain_smoke_v1", true, 3);
            field(builder, "baseline_source", "same_run_initial_segment", true, 3);
            field(builder, "contract_status", "smoke_only", true, 3);
            numberField(builder, "baseline_window_count", result.baselineCount, true, 3);
            numberField(builder, "current_window_count", result.currentCount, true, 3);
            nullableDoubleField(builder, "baseline_rmssd_ms", result.baselineRmssdMs, true, 3);
            nullableDoubleField(builder, "current_rmssd_ms", result.currentRmssdMs, true, 3);
            nullableDoubleField(builder, "rmssd_ratio", result.ratio, true, 3);
            nullableDoubleField(builder, "ln_rmssd_gain", result.lnGain, true, 3);
            nullableStringField(builder, "quality", result.quality, true, 3);
            nullableStringField(builder, "issue_code", result.issueCode, true, 3);
            numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            indent(builder, 2).append("}");
            return builder.toString();
        }

        private String coherenceStream(CaptureRun run) {
            CoherenceResult result = Coherence.compute(run.rrIntervalsMs);
            StringBuilder builder = moduleStreamHeader(STREAM_COHERENCE, MODULE_COHERENCE, result.pass);
            field(builder, "input_stream_id", STREAM_HR_RR, true, 3);
            field(builder, "method", "spectral_ratio_v1", true, 3);
            numberField(builder, "heart_rate_event_count", run.heartRates.size(), true, 3);
            numberField(builder, "input_rr_interval_count", result.inputRrIntervalCount, true, 3);
            numberField(builder, "uniform_sample_count", result.uniformSampleCount, true, 3);
            doubleField(builder, "window_seconds", result.windowSeconds, true, 3);
            doubleField(builder, "sample_rate_hz", result.sampleRateHz, true, 3);
            nullableDoubleField(builder, "peak_frequency_hz", result.peakFrequencyHz, true, 3);
            nullableDoubleField(builder, "peak_band_power", result.peakBandPower, true, 3);
            nullableDoubleField(builder, "total_band_power", result.totalBandPower, true, 3);
            nullableDoubleField(builder, "remaining_power", result.remainingPower, true, 3);
            nullableDoubleField(builder, "coherence_ratio", result.coherenceRatio, true, 3);
            nullableDoubleField(builder, "coherence_ratio_squared", result.coherenceRatioSquared, true, 3);
            nullableDoubleField(builder, "normalized_peak_power", result.normalizedPeakPower, true, 3);
            nullableDoubleField(builder, "paper_ratio", result.paperRatio, true, 3);
            nullableDoubleField(builder, "normalized_score", result.normalizedScore, true, 3);
            nullableStringField(builder, "quality", result.quality, true, 3);
            nullableStringField(builder, "issue_code", result.issueCode, true, 3);
            doubleField(builder, "host_notification_rate_hz", hostRate(run.hrHostTimes), true, 3);
            numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            indent(builder, 2).append("}");
            return builder.toString();
        }

        private String breathVolumeStream(CaptureRun run) {
            BreathVolumeResult result = BreathVolume.compute(run.accFrames, run.accRateHz);
            StringBuilder builder = moduleStreamHeader(STREAM_BREATH_VOLUME, MODULE_BREATH_VOLUME_FROM_ACC, result.pass);
            field(builder, "input_stream_id", STREAM_ACC, true, 3);
            field(builder, "method", "acc_projection_proxy_v1", true, 3);
            numberField(builder, "input_acc_sample_count", result.sampleCount, true, 3);
            doubleField(builder, "source_sample_rate_hz", run.accRateHz, true, 3);
            numberField(builder, "calibration_sample_count", result.calibrationCount, true, 3);
            nullableStringField(builder, "projection_axis", result.axis, true, 3);
            nullableDoubleField(builder, "lower_bound", result.lower, true, 3);
            nullableDoubleField(builder, "upper_bound", result.upper, true, 3);
            nullableDoubleField(builder, "breath_volume_01", result.volume, true, 3);
            nullableStringField(builder, "phase", result.phase, true, 3);
            nullableDoubleField(builder, "confidence", result.confidence, true, 3);
            nullableStringField(builder, "quality", result.quality, true, 3);
            nullableStringField(builder, "issue_code", result.issueCode, true, 3);
            numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            indent(builder, 2).append("}");
            return builder.toString();
        }

        private String breathDynamicsStream(CaptureRun run) {
            BreathDynamicsResult result = BreathDynamics.compute(run.accFrames, run.accRateHz);
            StringBuilder builder = moduleStreamHeader(STREAM_BREATH_DYNAMICS, MODULE_BREATH_DYNAMICS, result.pass);
            field(builder, "input_stream_id", STREAM_BREATH_VOLUME, true, 3);
            field(builder, "method", "cycle_stats_v1", true, 3);
            numberField(builder, "input_breath_sample_count", result.inputCount, true, 3);
            numberField(builder, "cycle_count", result.cycleCount, true, 3);
            nullableDoubleField(builder, "mean_interval_s", result.meanInterval, true, 3);
            nullableDoubleField(builder, "breathing_rate_bpm", result.breathingRate, true, 3);
            nullableDoubleField(builder, "interval_sd_s", result.intervalSd, true, 3);
            nullableDoubleField(builder, "interval_cv", result.intervalCv, true, 3);
            nullableDoubleField(builder, "mean_amplitude_01", result.meanAmplitude, true, 3);
            nullableDoubleField(builder, "amplitude_sd_01", result.amplitudeSd, true, 3);
            nullableDoubleField(builder, "amplitude_cv", result.amplitudeCv, true, 3);
            nullableStringField(builder, "complexity_status", result.complexityStatus, true, 3);
            nullableStringField(builder, "quality", result.quality, true, 3);
            nullableStringField(builder, "issue_code", result.issueCode, true, 3);
            numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            indent(builder, 2).append("}");
            return builder.toString();
        }

        private String hrvbStream(CaptureRun run) {
            HrvbResult result = HrvbResonance.compute(run.rrIntervalsMs);
            StringBuilder builder = moduleStreamHeader(STREAM_HRVB_RESONANCE_AMPLITUDE, MODULE_HRVB_RESONANCE_AMPLITUDE, result.pass);
            field(builder, "input_stream_id", STREAM_HR_RR, true, 3);
            field(builder, "method", "rolling_sine_fit_v1", true, 3);
            numberField(builder, "input_rr_interval_count", result.inputCount, true, 3);
            doubleField(builder, "window_seconds", 30.0, true, 3);
            doubleField(builder, "sample_rate_hz", 1.0, true, 3);
            nullableDoubleField(builder, "amplitude_bpm", result.amplitude, true, 3);
            nullableDoubleField(builder, "mean_hr_bpm", result.meanHr, true, 3);
            nullableDoubleField(builder, "frequency_hz", result.frequency, true, 3);
            nullableDoubleField(builder, "omega_rad_s", result.omega, true, 3);
            nullableDoubleField(builder, "phase_rad", result.phase, true, 3);
            nullableDoubleField(builder, "median_session_amplitude_bpm", result.medianAmplitude, true, 3);
            nullableStringField(builder, "threshold_status", result.thresholdStatus, true, 3);
            nullableStringField(builder, "quality", result.quality, true, 3);
            nullableStringField(builder, "issue_code", result.issueCode, true, 3);
            numberField(builder, "malformed_frame_count", run.malformedFrameCount, false, 3);
            indent(builder, 2).append("}");
            return builder.toString();
        }

        private StringBuilder moduleStreamHeader(String streamId, String moduleId, boolean pass) {
            StringBuilder builder = new StringBuilder();
            indent(builder, 2).append("{\n");
            field(builder, "stream_id", streamId, true, 3);
            field(builder, "module_id", moduleId, true, 3);
            field(builder, "status", pass ? "pass" : "fail", true, 3);
            return builder;
        }

        private void appendErrors(StringBuilder builder, List<String> errors) {
            indent(builder, 1).append("\"errors\": [");
            for (int index = 0; index < errors.size(); index++) {
                builder.append(quote(errors.get(index)));
                if (index + 1 < errors.size()) {
                    builder.append(", ");
                }
            }
            builder.append("]\n");
        }

        private PackageHashes packageHashes() {
            return new PackageHashes(
                    assetSha256("manifold/packages/polar-h10/manifests/package.manifold.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/streams/hr-rr.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/streams/ecg.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/streams/acc.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/streams/coherence.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/streams/hrv-window.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/streams/rmssd-gain.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/streams/breath-volume.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/streams/breath-dynamics.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/streams/hrvb-resonance-amplitude.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/modules/provider.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/modules/coherence.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/modules/hrv-window.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/modules/rmssd-gain.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/modules/breath-volume-from-acc.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/modules/breath-dynamics.json"),
                    assetSha256("manifold/packages/polar-h10/manifests/modules/hrvb-resonance-amplitude.json"));
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
            if ("coherence".equals(mode)) {
                return STREAM_COHERENCE;
            }
            return STREAM_HR_RR;
        }

        private String hostAppId(String hostProfile) {
            if ("headset".equals(hostProfile)) {
                return "app.rusty_hostess_t.quest";
            }
            return "app.rusty_hostess_t.android";
        }

        private List<String> dependencyStreams(CaptureRun run) {
            List<String> streams = new ArrayList<>();
            if (run.needsHr()) {
                streams.add(STREAM_HR_RR);
            }
            if (run.needsAcc()) {
                streams.add(STREAM_ACC);
            }
            if (run.needsEcg()) {
                streams.add(STREAM_ECG);
            }
            return streams;
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

        private StringBuilder stringArrayField(StringBuilder builder, String name, List<String> values, boolean comma, int level) {
            indent(builder, level).append(quote(name)).append(": [");
            for (int index = 0; index < values.size(); index++) {
                builder.append(quote(values.get(index)));
                if (index + 1 < values.size()) {
                    builder.append(", ");
                }
            }
            builder.append("]").append(comma ? ",\n" : "\n");
            return builder;
        }

        private StringBuilder graphStringArrayField(StringBuilder builder, String name, JSONArray values, boolean comma, int level) {
            indent(builder, level).append(quote(name)).append(": [");
            if (values != null) {
                for (int index = 0; index < values.length(); index++) {
                    builder.append(quote(values.optString(index)));
                    if (index + 1 < values.length()) {
                        builder.append(", ");
                    }
                }
            }
            builder.append("]").append(comma ? ",\n" : "\n");
            return builder;
        }

        private StringBuilder doubleField(StringBuilder builder, String name, double value, boolean comma, int level) {
            indent(builder, level).append(quote(name)).append(": ");
            builder.append(String.format(Locale.US, "%.3f", value)).append(comma ? ",\n" : "\n");
            return builder;
        }

        private StringBuilder nullableDoubleField(StringBuilder builder, String name, Double value, boolean comma, int level) {
            indent(builder, level).append(quote(name)).append(": ");
            if (value == null) {
                builder.append("null");
            } else {
                builder.append(String.format(Locale.US, "%.6f", value));
            }
            builder.append(comma ? ",\n" : "\n");
            return builder;
        }

        private StringBuilder nullableStringField(StringBuilder builder, String name, String value, boolean comma, int level) {
            indent(builder, level).append(quote(name)).append(": ");
            builder.append(value == null ? "null" : quote(value)).append(comma ? ",\n" : "\n");
            return builder;
        }

        private StringBuilder jsonPair(StringBuilder builder, String name, String value) {
            return builder.append(quote(name)).append(": ").append(quote(value));
        }

        private String indentJson(String json, int level) {
            String prefix = "";
            for (int index = 0; index < level; index++) {
                prefix += "  ";
            }
            return prefix + json.replace("\n", "\n" + prefix);
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

    private static final class PackageHashes {
        final String packageManifest;
        final String hrRrStream;
        final String ecgStream;
        final String accStream;
        final String coherenceStream;
        final String hrvWindowStream;
        final String rmssdGainStream;
        final String breathVolumeStream;
        final String breathDynamicsStream;
        final String hrvbResonanceAmplitudeStream;
        final String providerModule;
        final String coherenceModule;
        final String hrvWindowModule;
        final String rmssdGainModule;
        final String breathVolumeModule;
        final String breathDynamicsModule;
        final String hrvbResonanceAmplitudeModule;

        PackageHashes(String packageManifest, String hrRrStream, String ecgStream, String accStream, String coherenceStream,
                      String hrvWindowStream, String rmssdGainStream, String breathVolumeStream, String breathDynamicsStream,
                      String hrvbResonanceAmplitudeStream, String providerModule, String coherenceModule,
                      String hrvWindowModule, String rmssdGainModule, String breathVolumeModule,
                      String breathDynamicsModule, String hrvbResonanceAmplitudeModule) {
            this.packageManifest = packageManifest;
            this.hrRrStream = hrRrStream;
            this.ecgStream = ecgStream;
            this.accStream = accStream;
            this.coherenceStream = coherenceStream;
            this.hrvWindowStream = hrvWindowStream;
            this.rmssdGainStream = rmssdGainStream;
            this.breathVolumeStream = breathVolumeStream;
            this.breathDynamicsStream = breathDynamicsStream;
            this.hrvbResonanceAmplitudeStream = hrvbResonanceAmplitudeStream;
            this.providerModule = providerModule;
            this.coherenceModule = coherenceModule;
            this.hrvWindowModule = hrvWindowModule;
            this.rmssdGainModule = rmssdGainModule;
            this.breathVolumeModule = breathVolumeModule;
            this.breathDynamicsModule = breathDynamicsModule;
            this.hrvbResonanceAmplitudeModule = hrvbResonanceAmplitudeModule;
        }

        boolean complete() {
            return !"unavailable".equals(packageManifest)
                    && !"unavailable".equals(hrRrStream)
                    && !"unavailable".equals(ecgStream)
                    && !"unavailable".equals(accStream)
                    && !"unavailable".equals(coherenceStream)
                    && !"unavailable".equals(hrvWindowStream)
                    && !"unavailable".equals(rmssdGainStream)
                    && !"unavailable".equals(breathVolumeStream)
                    && !"unavailable".equals(breathDynamicsStream)
                    && !"unavailable".equals(hrvbResonanceAmplitudeStream)
                    && !"unavailable".equals(providerModule)
                    && !"unavailable".equals(coherenceModule)
                    && !"unavailable".equals(hrvWindowModule)
                    && !"unavailable".equals(rmssdGainModule)
                    && !"unavailable".equals(breathVolumeModule)
                    && !"unavailable".equals(breathDynamicsModule)
                    && !"unavailable".equals(hrvbResonanceAmplitudeModule);
        }
    }
}
