package io.github.mesmerprism.rustyhostess.t;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;

final class PMBRuntime {
    static final String RUNTIME_PATH = "rust.projected_motion_breath_core.v1";

    private static boolean loadAttempted = false;
    private static boolean loaded = false;
    private static String loadError = "";

    private PMBRuntime() {
    }

    static synchronized boolean isAvailable() {
        if (!loadAttempted) {
            loadAttempted = true;
            try {
                System.loadLibrary("hostess_pmb_runtime_jni");
                loaded = true;
            } catch (UnsatisfiedLinkError error) {
                loadError = error.toString();
                loaded = false;
            }
        }
        return loaded;
    }

    static String loadError() {
        isAvailable();
        return loadError;
    }

    static JSONObject validatePackage(String packageRoot) throws JSONException, IOException {
        if (!isAvailable()) {
            throw new IOException("native runtime unavailable: " + loadError());
        }
        return new JSONObject(nativeValidatePackage(packageRoot));
    }

    static JSONObject runControllerPreflight(String packageRoot) throws JSONException, IOException {
        if (!isAvailable()) {
            throw new IOException("native runtime unavailable: " + loadError());
        }
        return new JSONObject(nativeRunControllerPreflight(packageRoot));
    }

    static JSONObject runLiveRouteSelfTest(String packageRoot) throws JSONException, IOException {
        if (!isAvailable()) {
            throw new IOException("native runtime unavailable: " + loadError());
        }
        return new JSONObject(nativeRunLiveRouteSelfTest(packageRoot));
    }

    static JSONObject runLiveRouteFromEvents(String packageRoot, String eventsJsonl) throws JSONException, IOException {
        if (!isAvailable()) {
            throw new IOException("native runtime unavailable: " + loadError());
        }
        return new JSONObject(nativeRunLiveRouteFromEvents(packageRoot, eventsJsonl));
    }

    static long openLiveTransportProcessor(String packageRoot) throws JSONException, IOException {
        if (!isAvailable()) {
            throw new IOException("native runtime unavailable: " + loadError());
        }
        JSONObject report = new JSONObject(nativeOpenLiveTransportProcessor(packageRoot));
        long handle = report.optLong("handle", 0L);
        if (!"pass".equals(report.optString("status")) || handle == 0L) {
            throw new IOException(report.optJSONArray("issues") == null
                    ? "live transport processor open failed"
                    : report.optJSONArray("issues").toString());
        }
        return handle;
    }

    static JSONObject pushLiveTransportEvent(
            long handle,
            String eventJson,
            String selectedSourcePreference) throws JSONException, IOException {
        if (!isAvailable()) {
            throw new IOException("native runtime unavailable: " + loadError());
        }
        return new JSONObject(nativePushLiveTransportEvent(handle, eventJson, selectedSourcePreference));
    }

    static JSONObject closeLiveTransportProcessor(long handle) throws JSONException, IOException {
        if (!isAvailable()) {
            throw new IOException("native runtime unavailable: " + loadError());
        }
        return new JSONObject(nativeCloseLiveTransportProcessor(handle));
    }

    private static native String nativeValidatePackage(String packageRoot);

    private static native String nativeRunControllerPreflight(String packageRoot);

    private static native String nativeRunLiveRouteSelfTest(String packageRoot);

    private static native String nativeRunLiveRouteFromEvents(String packageRoot, String eventsJsonl);

    private static native String nativeOpenLiveTransportProcessor(String packageRoot);

    private static native String nativePushLiveTransportEvent(
            long handle,
            String eventJson,
            String selectedSourcePreference);

    private static native String nativeCloseLiveTransportProcessor(long handle);
}
