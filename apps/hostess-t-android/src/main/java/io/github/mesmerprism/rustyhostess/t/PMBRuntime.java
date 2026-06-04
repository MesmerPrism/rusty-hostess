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

    private static native String nativeValidatePackage(String packageRoot);

    private static native String nativeRunControllerPreflight(String packageRoot);

    private static native String nativeRunLiveRouteSelfTest(String packageRoot);
}
