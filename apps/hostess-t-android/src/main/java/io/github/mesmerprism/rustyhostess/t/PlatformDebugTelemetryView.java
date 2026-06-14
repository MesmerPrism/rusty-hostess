package io.github.mesmerprism.rustyhostess.t;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayDeque;
import java.util.List;
import java.util.Locale;

// Fallback/debug-only platform renderer. Makepad is the intended Hostess GUI surface.
final class PlatformDebugTelemetryView extends View {
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
    static final int MIN_RENDER_WIDTH = 320;
    static final int MIN_RENDER_HEIGHT = 240;
    static final int MIN_RENDER_CONTENT_PIXELS = 64;

    private static final String STREAM_COHERENCE = "stream.polar_h10.coherence";
    private static final String STREAM_HRV_WINDOW = "stream.polar_h10.hrv_window";
    private static final String STREAM_RMSSD_GAIN = "stream.polar_h10.rmssd_gain";
    private static final String STREAM_BREATH_VOLUME = "stream.polar_h10.breath_volume";
    private static final String STREAM_BREATH_DYNAMICS = "stream.polar_h10.breath_dynamics";
    private static final String STREAM_HRVB_RESONANCE_AMPLITUDE = "stream.polar_h10.hrvb_resonance_amplitude";

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

    void addAccFrame(MainActivity.PmdFrameMetric frame, int malformed) {
        accFrameCount += 1;
        accSampleCount += frame.sampleCount;
        for (MainActivity.AccSample sample : frame.accSamples) {
            double magnitude = Math.sqrt(
                    (sample.xMg * sample.xMg)
                            + (sample.yMg * sample.yMg)
                            + (sample.zMg * sample.zMg));
            append(accMagnitude, (float) magnitude);
        }
        malformedFrameCount = malformed;
        invalidate();
    }

    void addEcgFrame(MainActivity.PmdFrameMetric frame, int malformed) {
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

    TelemetryRenderMetadata writePng(File out) throws IOException {
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
            return new TelemetryRenderMetadata(width, height, contentPixels, page);
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
