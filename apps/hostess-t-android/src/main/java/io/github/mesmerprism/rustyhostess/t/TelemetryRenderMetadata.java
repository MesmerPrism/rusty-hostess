package io.github.mesmerprism.rustyhostess.t;

import java.time.Instant;

final class TelemetryRenderMetadata {
    final int width;
    final int height;
    final int contentPixelCount;
    final String page;

    TelemetryRenderMetadata(int width, int height, int contentPixelCount, String page) {
        this.width = width;
        this.height = height;
        this.contentPixelCount = contentPixelCount;
        this.page = page;
    }

    static String toJson(
            String status,
            String target,
            String imageName,
            String sourceEvidencePath,
            TelemetryRenderMetadata metadata,
            String error) {
        StringBuilder builder = new StringBuilder();
        builder.append("{\n");
        builder.append("  \"").append("$schema").append("\": \"rusty.hostess.telemetry.render_evidence.v1\",\n");
        builder.append("  \"status\": ").append(jsonQuote(status)).append(",\n");
        builder.append("  \"rendered_at_utc\": ").append(jsonQuote(Instant.now().toString())).append(",\n");
        builder.append("  \"target\": ").append(jsonQuote(target)).append(",\n");
        builder.append("  \"render_page\": ").append(jsonQuote(metadata == null ? "unknown" : metadata.page)).append(",\n");
        builder.append("  \"image_path\": ").append(jsonQuote(imageName)).append(",\n");
        builder.append("  \"source_evidence_path\": ").append(jsonQuote(sourceEvidencePath)).append(",\n");
        builder.append("  \"width\": ").append(metadata == null ? 0 : metadata.width).append(",\n");
        builder.append("  \"height\": ").append(metadata == null ? 0 : metadata.height).append(",\n");
        builder.append("  \"content_pixel_count\": ").append(metadata == null ? 0 : metadata.contentPixelCount).append(",\n");
        builder.append("  \"validation\": {\n");
        builder.append("    \"min_width\": ").append(PlatformDebugTelemetryView.MIN_RENDER_WIDTH).append(",\n");
        builder.append("    \"min_height\": ").append(PlatformDebugTelemetryView.MIN_RENDER_HEIGHT).append(",\n");
        builder.append("    \"min_content_pixels\": ").append(PlatformDebugTelemetryView.MIN_RENDER_CONTENT_PIXELS).append("\n");
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
}
