package io.github.mesmerprism.rustyhostess.t;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

final class PmbPackageAssets {
    private static final String PACKAGE_ID = "package.projected_motion_breath";
    private static final String ASSET_ROOT = "manifold/packages/projected-motion-breath";

    private PmbPackageAssets() {
    }

    static void copyTo(HostessAssetStore assets, File targetRoot) throws IOException {
        for (String relative : assetFiles(assets)) {
            assets.copyFile(ASSET_ROOT + "/" + relative, new File(targetRoot, relative.replace('/', File.separatorChar)));
        }
    }

    static JSONObject snapshot(HostessAssetStore assets) throws JSONException {
        return new JSONObject()
                .put("package_id", PACKAGE_ID)
                .put("package_manifest_sha256", assets.sha256(ASSET_ROOT + "/manifests/package.manifold.json"))
                .put("stream_manifest_sha256", manifestHashes(assets, "streams"))
                .put("module_manifest_sha256", manifestHashes(assets, "modules"))
                .put("command_manifest_sha256", manifestHashes(assets, "commands"));
    }

    static JSONObject manifestHashes(HostessAssetStore assets, String manifestFolder) throws JSONException {
        JSONObject hashes = new JSONObject();
        String folder = ASSET_ROOT + "/manifests/" + manifestFolder;
        try {
            String prefix = "manifests/" + manifestFolder + "/";
            for (String relative : assetFiles(assets)) {
                if (relative.startsWith(prefix) && relative.endsWith(".json")) {
                    String file = relative.substring(prefix.length());
                    hashes.put(file.substring(0, file.length() - 5), assets.sha256(ASSET_ROOT + "/" + relative));
                }
            }
            if (hashes.length() > 0) {
                return hashes;
            }
            String[] files = assets.list(folder);
            Arrays.sort(files);
            for (String file : files) {
                if (file.endsWith(".json")) {
                    hashes.put(file.substring(0, file.length() - 5), assets.sha256(folder + "/" + file));
                }
            }
        } catch (IOException ignored) {
        }
        return hashes;
    }

    private static List<String> assetFiles(HostessAssetStore assets) throws IOException {
        List<String> files = new ArrayList<>();
        String manifest = assets.readText(ASSET_ROOT + "/package-files.txt");
        for (String line : manifest.split("\\r?\\n")) {
            String trimmed = line.trim();
            if (!trimmed.isEmpty() && !trimmed.contains("..")) {
                files.add(trimmed);
            }
        }
        return files;
    }
}
