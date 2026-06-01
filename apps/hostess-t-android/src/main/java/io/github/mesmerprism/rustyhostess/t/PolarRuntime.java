package io.github.mesmerprism.rustyhostess.t;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

final class PolarRuntime {
    static final String RUNTIME_PATH = "rust.polar_h10_core.v1";

    private static boolean loadAttempted = false;
    private static boolean loaded = false;
    private static String loadError = "";

    private PolarRuntime() {
    }

    static synchronized boolean isAvailable() {
        if (!loadAttempted) {
            loadAttempted = true;
            try {
                System.loadLibrary("hostess_polar_runtime_jni");
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

    static JSONObject runGraph(Context context, JSONObject runtimeInput, List<String> selectedModules)
            throws JSONException, IOException {
        if (!isAvailable()) {
            throw new IOException("native runtime unavailable: " + loadError());
        }
        String graphJson = readAsset(context, "manifold/packages/polar-h10/fixtures/valid/graph.json");
        JSONArray modules = new JSONArray();
        for (String moduleId : selectedModules) {
            modules.put(moduleId);
        }
        return new JSONObject(nativeRunGraph(graphJson, runtimeInput.toString(), modules.toString()));
    }

    static JSONObject syntheticReplay(Context context, List<String> selectedModules)
            throws JSONException, IOException {
        return runGraph(context, syntheticRuntimeInput(context), selectedModules);
    }

    static JSONObject syntheticRuntimeInput(Context context) throws JSONException, IOException {
        JSONObject input = new JSONObject(readAsset(
                context,
                "manifold/packages/polar-h10/fixtures/valid/processor-runtime-input-synthetic.json"));
        return input;
    }

    private static String readAsset(Context context, String path) throws IOException {
        InputStream input;
        try {
            input = context.getAssets().open(path);
        } catch (IOException first) {
            input = context.getAssets().open(path.replace('/', '\\'));
        }
        try (InputStream stream = input) {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            byte[] bytes = new byte[8192];
            int read;
            while ((read = stream.read(bytes)) >= 0) {
                buffer.write(bytes, 0, read);
            }
            return buffer.toString(StandardCharsets.UTF_8.name());
        }
    }

    private static native String nativeRunGraph(
            String graphJson,
            String inputJson,
            String selectedModulesJson);
}
