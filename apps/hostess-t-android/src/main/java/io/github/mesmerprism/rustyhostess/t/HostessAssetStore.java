package io.github.mesmerprism.rustyhostess.t;

import android.content.Context;
import android.content.res.AssetManager;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

final class HostessAssetStore {
    private final AssetManager assets;

    HostessAssetStore(Context context) {
        this.assets = context.getAssets();
    }

    void copyFile(String assetPath, File target) throws IOException {
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("could not create " + parent);
        }
        try (InputStream input = open(assetPath); FileOutputStream output = new FileOutputStream(target)) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) >= 0) {
                output.write(buffer, 0, read);
            }
        }
    }

    String readText(String assetPath) throws IOException {
        try (InputStream input = open(assetPath)) {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            byte[] bytes = new byte[8192];
            int read;
            while ((read = input.read(bytes)) >= 0) {
                buffer.write(bytes, 0, read);
            }
            return buffer.toString(StandardCharsets.UTF_8.name());
        }
    }

    String[] list(String path) throws IOException {
        String[] children = assets.list(path);
        if (children != null && children.length > 0) {
            return children;
        }
        String fallback = path.replace('/', '\\');
        if (!fallback.equals(path)) {
            String[] fallbackChildren = assets.list(fallback);
            if (fallbackChildren != null && fallbackChildren.length > 0) {
                return fallbackChildren;
            }
        }
        return children == null ? new String[0] : children;
    }

    String sha256(String path) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream stream = open(path)) {
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

    InputStream open(String path) throws IOException {
        try {
            return assets.open(path);
        } catch (IOException first) {
            return assets.open(path.replace('/', '\\'));
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder builder = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) {
            builder.append(String.format(Locale.US, "%02x", value & 0xff));
        }
        return builder.toString();
    }
}
