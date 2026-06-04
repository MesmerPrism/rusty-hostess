pub use makepad_widgets;

use makepad_widgets::makepad_platform::makepad_micro_serde::*;
use makepad_widgets::*;
use shell_contract::MakepadShellContractReadReceipt;
use shell_runtime_capabilities::MakepadShellRuntimeCapabilityReceipt;
use shell_xr_runtime::ShellXrRuntimeState;
use std::collections::VecDeque;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};

mod shell_contract;
mod shell_runtime_capabilities;
mod shell_xr_runtime;

app_main!(App);

const STREAM_TICK_SECS: f64 = 0.18;
const STREAM_WINDOW_SAMPLES: usize = 96;
const MAX_BUFFER_SAMPLES: usize = 512;
const STALE_TICK_THRESHOLD: u32 = 16;
const RENDER_EXPORT_TICK_INTERVAL: u32 = 6;
const RENDER_WIDTH_HORIZONTAL: usize = 1120;
const RENDER_HEIGHT_HORIZONTAL: usize = 820;
const RENDER_WIDTH_VERTICAL: usize = 920;
const RENDER_HEIGHT_VERTICAL: usize = 1460;
const MIN_RENDER_CONTENT_PIXELS: usize = 64;
#[cfg(target_os = "android")]
const ANDROID_INTERNAL_TELEMETRY_ROOT: &str =
    "/data/user/0/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/telemetry";
#[cfg(target_os = "android")]
const ANDROID_EXTERNAL_TELEMETRY_ROOT: &str =
    "/sdcard/Android/data/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/telemetry";

script_mod! {
    use mod.prelude.widgets.*
    use mod.widgets.*

    let StreamPanel = RoundedView{
        width: Fill
        height: 184
        padding: Inset{left: 14.0 right: 14.0 top: 12.0 bottom: 12.0}
        flow: Down
        spacing: 8
        draw_bg.color: #xffffff
        draw_bg.border_radius: 12.0
        draw_bg.border_size: 1.0
        draw_bg.border_color: #xe0dcd5

        View{
            width: Fill
            height: Fit
            flow: Right
            spacing: 12

            View{
                width: Fill
                height: Fit
                flow: Down
                spacing: 3

                View{
                    width: Fill
                    height: Fit
                    flow: Right
                    spacing: 8

                    title := Label{
                        width: Fill
                        max_lines: 1
                        text_overflow: Ellipsis
                        text: ""
                        draw_text.color: #x1d1d1b
                        draw_text.text_style: theme.font_bold{font_size: 18.0}
                    }

                    status_pill := RoundedView{
                        width: Fit
                        height: Fit
                        padding: Inset{left: 7.0 right: 7.0 top: 2.0 bottom: 2.0}
                        draw_bg.color: #xeaf4ef
                        draw_bg.border_radius: 8.0

                        status_text := Label{
                            width: Fit
                            text: ""
                            draw_text.color: #x2f6b4f
                            draw_text.text_style.font_size: 10.0
                        }
                    }
                }

                detail := Label{
                    width: Fill
                    max_lines: 1
                    text_overflow: Ellipsis
                    text: ""
                    draw_text.color: #x746d64
                    draw_text.text_style.font_size: 11.0
                }
            }

            value := Label{
                width: Fit
                text: ""
                draw_text.color: #x155e75
                draw_text.text_style: theme.font_bold{font_size: 24.0}
            }
        }
        plot_box := RoundedView{
            width: Fill
            height: 112
            padding: Inset{left: 8.0 right: 8.0 top: 6.0 bottom: 6.0}
            draw_bg.color: #xf9faf7
            draw_bg.border_radius: 7.0
            draw_bg.border_size: 1.0
            draw_bg.border_color: #xe3ded6

            plot := LineChart{
                width: Fill
                height: Fill
                read_only: true
                bg_color: #xf9faf7
                grid_color: #xe6e0d766
                grid_text_color: #x8a8176
                border_color: #x00000000
                line_color: #x155e75
                line_width: 2.25
                plot_margin: Inset{left: 8.0 top: 8.0 right: 10.0 bottom: 8.0}
            }
        }
    }

    startup() do #(App::script_component(vm)){
        ui: XrRoot{
            pass.clear_color: #xf8f8f6
            window.inner_size: vec2(1120, 820)
            camera.fov_y: 38.0
            camera.desktop_target: vec3(0.0, -0.06, -0.72)
            camera.distance: 1.55
            env.gravity: 9.8
            env.env_cube: false
            env.depth_mesh: false

            shell_panel := XrView{
                show_in_non_xr: true
                pos: vec3(0.0, -0.04, -0.72)
                logical_size: vec2(1120, 820)
                pixel_scale: 0.00034
                dpi_factor: 2.0

                SolidView{
                    width: Fill
                    height: Fill
                    flow: Down
                    spacing: 0
                    draw_bg.color: #xf8f8f6

                    SolidView{
                        width: Fill
                        height: Fit
                        padding: Inset{left: 28.0 right: 28.0 top: 20.0 bottom: 16.0}
                        flow: Down
                        spacing: 7
                        draw_bg.color: #xffffff

                        Label{
                            text: "Rusty Hostess T"
                            draw_text.color: #x1d1d1b
                            draw_text.text_style: theme.font_bold{font_size: theme.font_size_3}
                        }
                        run_status := Label{
                            width: Fill
                            max_lines: 1
                            text_overflow: Ellipsis
                            text: "loading"
                            draw_text.color: #x5c5852
                            draw_text.text_style.font_size: theme.font_size_p
                        }
                        stream_state := Label{
                            width: Fill
                            max_lines: 1
                            text_overflow: Ellipsis
                            text: ""
                            draw_text.color: #x155e75
                            draw_text.text_style: theme.font_bold{font_size: theme.font_size_p}
                        }
                        snapshot_source := Label{
                            width: Fill
                            max_lines: 1
                            text_overflow: Ellipsis
                            text: ""
                            draw_text.color: #x5c5852
                            draw_text.text_style.font_size: theme.font_size_code
                        }
                    }

                    ScrollYView{
                        width: Fill
                        height: Fill
                        padding: Inset{left: 28.0 right: 28.0 top: 18.0 bottom: 18.0}
                        flow: Down
                        spacing: 12

                        View{
                            width: Fill
                            height: Fit
                            flow: Down
                            spacing: 12
                            stream_1 := StreamPanel{}
                            stream_2 := StreamPanel{}
                        }

                        View{
                            width: Fill
                            height: Fit
                            flow: Down
                            spacing: 12
                            stream_3 := StreamPanel{}
                            stream_4 := StreamPanel{}
                        }

                        View{
                            width: Fill
                            height: Fit
                            flow: Down
                            spacing: 12
                            stream_5 := StreamPanel{}
                            stream_6 := StreamPanel{}
                        }

                        SolidView{
                            width: Fill
                            height: Fit
                            padding: Inset{left: 14.0 right: 14.0 top: 12.0 bottom: 12.0}
                            flow: Down
                            spacing: 6
                            draw_bg.color: #xf1f5f2

                            issue_state := Label{
                                width: Fill
                                max_lines: 1
                                text_overflow: Ellipsis
                                text: ""
                                draw_text.color: #x3f3a35
                                draw_text.text_style.font_size: theme.font_size_p
                            }
                            debug_state := Label{
                                width: Fill
                                max_lines: 1
                                text_overflow: Ellipsis
                                text: ""
                                draw_text.color: #x5c5852
                                draw_text.text_style.font_size: theme.font_size_code
                            }
                            evidence_path := Label{
                                width: Fill
                                max_lines: 1
                                text_overflow: Ellipsis
                                text: ""
                                draw_text.color: #x5c5852
                                draw_text.text_style.font_size: theme.font_size_code
                            }
                        }
                    }
                }
            }

            xr_permissions := mod.widgets.XrPermissionsFlow{}
        }
    }
}

#[derive(Script, ScriptHook)]
pub struct App {
    #[live]
    ui: WidgetRef,
    #[rust]
    stream_timer: Timer,
    #[rust]
    telemetry: RunningTelemetry,
    #[rust]
    render_export: RenderExportState,
    #[rust]
    shell_contract_read: MakepadShellContractReadReceipt,
    #[rust]
    shell_runtime_capabilities: MakepadShellRuntimeCapabilityReceipt,
    #[rust]
    shell_xr_runtime: ShellXrRuntimeState,
}

#[derive(Clone, Debug, Default, DeJson)]
struct TelemetrySnapshot {
    snapshot_id: String,
    source_evidence_path: String,
    run: SnapshotRun,
    raw_streams: Vec<RawStream>,
    module_outputs: Vec<ModuleOutput>,
    time_series: Vec<TelemetrySeries>,
    issues: Vec<Issue>,
    evidence: EvidencePaths,
}

#[derive(Clone, Debug, Default, DeJson)]
struct SnapshotRun {
    status: String,
    host_profile: String,
    mode: String,
    runtime_path: String,
    graph_id: String,
    graph_status: String,
    selected_module_ids: Vec<String>,
}

#[derive(Clone, Debug, Default, DeJson)]
#[allow(dead_code)]
struct RawStream {
    stream_id: String,
    status: String,
    summary: String,
    preview: Vec<f64>,
}

#[derive(Clone, Debug, Default, DeJson)]
#[allow(dead_code)]
struct ModuleOutput {
    stream_id: String,
    module_id: String,
    status: String,
    input_stream_id: String,
    summary: String,
    issue_code: Option<String>,
}

#[derive(Clone, Debug, Default, DeJson)]
struct TelemetrySeries {
    series_id: String,
    stream_id: String,
    label: String,
    unit: String,
    source: String,
    sample_rate_hz: Option<f64>,
    values: Vec<f64>,
}

#[derive(Clone, Debug, Default, DeJson)]
struct Issue {
    code: String,
    message: String,
}

#[derive(Clone, Debug, Default, DeJson)]
struct EvidencePaths {
    capture: String,
    runtime_input: String,
    graph_execution_report: String,
}

#[derive(Clone, Debug, Default)]
struct LoadedSnapshot {
    snapshot: TelemetrySnapshot,
    path: Option<PathBuf>,
    stream_path: Option<PathBuf>,
}

#[derive(Clone, Debug, Default)]
struct RunningTelemetry {
    snapshot: TelemetrySnapshot,
    source_path: Option<PathBuf>,
    stream_path: Option<PathBuf>,
    stream_line_count: usize,
    stream_file_pos: u64,
    stream_pending_text: String,
    series_states: Vec<SeriesRuntime>,
    event_count: usize,
    load_error_count: usize,
}

#[derive(Clone, Debug, Default)]
struct SeriesRuntime {
    series_id: String,
    stream_id: String,
    label: String,
    unit: String,
    source: String,
    sample_rate_hz: Option<f64>,
    values: VecDeque<f64>,
    sample_times: VecDeque<Option<f64>>,
    last_delta: usize,
    ticks_since_growth: u32,
}

#[derive(Clone, Debug, Default, DeJson)]
struct TelemetryStreamEvent {
    series_id: String,
    stream_id: String,
    label: String,
    unit: String,
    source: String,
    sample_rate_hz: Option<f64>,
    values: Option<Vec<f64>>,
    samples: Option<Vec<TelemetrySample>>,
}

#[derive(Clone, Debug, Default, DeJson)]
struct TelemetrySample {
    t: Option<f64>,
    value: f64,
    quality: Option<f64>,
    artifact: Option<bool>,
    missing: Option<bool>,
}

#[derive(Clone, Copy, Debug)]
enum AxisPolicy {
    Fixed { min: f64, max: f64 },
    Soft { min: f64, max: f64 },
    Rolling { pad_fraction: f64 },
}

#[derive(Clone, Copy, Debug)]
struct MetricStyle {
    display_unit: &'static str,
    axis: AxisPolicy,
    active_color: Vec4f,
    stale_color: Vec4f,
    active_width: f32,
    stale_width: f32,
}

#[derive(Clone, Debug, Default)]
struct RenderExportState {
    path: Option<PathBuf>,
    tick_count: u32,
    write_count: usize,
    last_event_count: usize,
    last_error: Option<String>,
}

impl RunningTelemetry {
    fn from_loaded(loaded: LoadedSnapshot) -> Self {
        let mut series = loaded.snapshot.time_series.clone();
        if series.is_empty() {
            series = fallback_series(&loaded.snapshot);
        }
        let series_states = series
            .into_iter()
            .map(|series| {
                let len = series.values.len();
                SeriesRuntime::from_series(
                    series,
                    len,
                    if loaded.stream_path.is_some() {
                        STALE_TICK_THRESHOLD.saturating_add(1)
                    } else {
                        0
                    },
                )
            })
            .collect();
        Self {
            snapshot: loaded.snapshot,
            source_path: loaded.path,
            stream_path: loaded.stream_path,
            stream_line_count: 0,
            stream_file_pos: 0,
            stream_pending_text: String::new(),
            series_states,
            event_count: 0,
            load_error_count: 0,
        }
    }

    fn tick(&mut self) -> bool {
        for state in &mut self.series_states {
            state.ticks_since_growth = state.ticks_since_growth.saturating_add(1);
            state.last_delta = 0;
        }
        self.drain_stream_events()
    }

    fn points_for(&self, index: usize) -> Vec<DataPoint> {
        let Some(state) = self.series_states.get(index) else {
            return baseline_points();
        };
        if state.values.is_empty() {
            return baseline_points();
        }
        let visible_count = state.values.len().min(STREAM_WINDOW_SAMPLES);
        let start = state.values.len().saturating_sub(visible_count);
        let mut points = Vec::with_capacity(visible_count.max(2));
        let visible_values: Vec<f64> = state.values.iter().skip(start).copied().collect();
        let visible_times: Vec<Option<f64>> =
            state.sample_times.iter().skip(start).copied().collect();
        let newest_time = visible_times.iter().rev().find_map(|time| *time);
        let rate_hz = state.sample_rate_hz.unwrap_or(1.0).max(0.000_001);

        for (plot_index, value) in visible_values.iter().enumerate() {
            let x = if let (Some(newest), Some(sample_time)) = (
                newest_time,
                visible_times.get(plot_index).and_then(|time| *time),
            ) {
                sample_time - newest
            } else {
                let age_samples = visible_count.saturating_sub(1).saturating_sub(plot_index);
                -(age_samples as f64) / rate_hz
            };
            points.push(DataPoint { x, y: *value });
        }
        if points.len() == 1 {
            points.push(DataPoint {
                x: 0.0,
                y: points[0].y,
            });
        }
        points
    }

    fn display_points_for(&self, index: usize) -> Vec<DataPoint> {
        let points = self.points_for(index);
        let Some(state) = self.series_states.get(index) else {
            return points;
        };
        if is_hr_series(state) {
            smooth_points_ema(points, 0.35)
        } else {
            points
        }
    }

    fn y_axis_range_for(&self, index: usize) -> Option<(f64, f64)> {
        let state = self.series_states.get(index)?;
        let values: Vec<f64> = state
            .values
            .iter()
            .rev()
            .take(STREAM_WINDOW_SAMPLES)
            .copied()
            .filter(|value| value.is_finite())
            .collect();
        if values.is_empty() {
            return None;
        }
        Some(axis_bounds_for_state(state, &values))
    }

    fn status_line(&self) -> String {
        if self.series_states.is_empty() {
            return "waiting / 0 stream series".to_string();
        }
        format!(
            "watching incoming telemetry / active {} / stale {} / {} series / {} samples / events {} / read errors {}",
            self.active_series_count(),
            self.stale_series_count(),
            self.series_states.len(),
            self.sample_total(),
            self.event_count,
            self.load_error_count
        )
    }

    fn active_series_count(&self) -> usize {
        self.series_states
            .iter()
            .filter(|state| state.is_active())
            .count()
    }

    fn stale_series_count(&self) -> usize {
        self.series_states
            .iter()
            .filter(|state| !state.values.is_empty() && !state.is_active())
            .count()
    }

    fn sample_total(&self) -> usize {
        self.series_states
            .iter()
            .map(|state| state.values.len())
            .sum()
    }

    fn snapshot_source_line(&self) -> String {
        let snapshot = &self.snapshot;
        let source = self
            .stream_path
            .as_ref()
            .map(|path| format!("live stream {}", display_leaf(path)))
            .unwrap_or_else(|| "snapshot checkpoint".to_string());
        format!(
            "{} / {} / {} / {}",
            snapshot.snapshot_id, snapshot.run.host_profile, snapshot.run.graph_id, source
        )
    }

    fn debug_line(&self) -> String {
        let streams = self
            .series_states
            .iter()
            .take(8)
            .map(|state| {
                format!(
                    "{}:{}",
                    short_stream_id(&state.stream_id),
                    state.values.len()
                )
            })
            .collect::<Vec<_>>()
            .join(", ");
        let source = self
            .stream_path
            .as_ref()
            .map(|path| path.display().to_string())
            .or_else(|| {
                self.source_path
                    .as_ref()
                    .map(|path| path.display().to_string())
            })
            .unwrap_or_else(|| self.snapshot.source_evidence_path.clone());
        format!(
            "debug / lines {} / byte offset {} / streams [{}] / source {}",
            self.stream_line_count, self.stream_file_pos, streams, source
        )
    }

    fn render_source_path(&self) -> String {
        self.stream_path
            .as_ref()
            .map(|path| path.display().to_string())
            .or_else(|| {
                self.source_path
                    .as_ref()
                    .map(|path| path.display().to_string())
            })
            .unwrap_or_else(|| self.snapshot.source_evidence_path.clone())
    }

    fn drain_stream_events(&mut self) -> bool {
        let Some(path) = self.stream_path.clone() else {
            return false;
        };
        let Ok(metadata) = std::fs::metadata(&path) else {
            self.load_error_count = self.load_error_count.saturating_add(1);
            return false;
        };
        if metadata.len() < self.stream_file_pos {
            self.stream_file_pos = 0;
            self.stream_pending_text.clear();
            self.stream_line_count = 0;
        }
        if metadata.len() == self.stream_file_pos {
            return false;
        }
        let Ok(mut file) = File::open(&path) else {
            self.load_error_count = self.load_error_count.saturating_add(1);
            return false;
        };
        if file.seek(SeekFrom::Start(self.stream_file_pos)).is_err() {
            self.load_error_count = self.load_error_count.saturating_add(1);
            return false;
        }
        let mut appended = String::new();
        if file.read_to_string(&mut appended).is_err() {
            self.load_error_count = self.load_error_count.saturating_add(1);
            return false;
        }
        self.stream_file_pos = metadata.len();
        if appended.is_empty() {
            return false;
        }

        let mut text = String::new();
        text.push_str(&self.stream_pending_text);
        text.push_str(&appended);
        let complete = text.ends_with('\n') || text.ends_with('\r');
        let mut lines = text.lines().collect::<Vec<_>>();
        self.stream_pending_text = if complete {
            String::new()
        } else {
            lines.pop().unwrap_or("").to_string()
        };

        let mut changed = false;
        for line in lines.into_iter().filter(|line| !line.trim().is_empty()) {
            match TelemetryStreamEvent::deserialize_json_lenient(line) {
                Ok(event) => {
                    self.apply_stream_event(event);
                    self.event_count = self.event_count.saturating_add(1);
                    self.stream_line_count = self.stream_line_count.saturating_add(1);
                    changed = true;
                }
                Err(_) => {
                    self.load_error_count = self.load_error_count.saturating_add(1);
                }
            }
        }
        changed
    }

    fn apply_stream_event(&mut self, event: TelemetryStreamEvent) {
        let values_empty = event
            .values
            .as_ref()
            .map(|values| values.is_empty())
            .unwrap_or(true);
        let samples_empty = event
            .samples
            .as_ref()
            .map(|samples| samples.is_empty())
            .unwrap_or(true);
        if event.series_id.is_empty() || (values_empty && samples_empty) {
            return;
        }
        if let Some(state) = self
            .series_states
            .iter_mut()
            .find(|state| state.series_id == event.series_id)
        {
            state.update_metadata(&event);
            state.append_event_samples(&event);
            state.ticks_since_growth = 0;
        } else {
            let mut state = SeriesRuntime::from_event_metadata(&event);
            state.append_event_samples(&event);
            self.series_states.push(state);
        }
    }
}

impl SeriesRuntime {
    fn from_series(series: TelemetrySeries, last_delta: usize, ticks_since_growth: u32) -> Self {
        let times = std::iter::repeat(None)
            .take(series.values.len())
            .collect::<VecDeque<_>>();
        Self {
            series_id: series.series_id,
            stream_id: series.stream_id,
            label: series.label,
            unit: series.unit,
            source: series.source,
            sample_rate_hz: series.sample_rate_hz,
            values: series.values.into_iter().collect(),
            sample_times: times,
            last_delta,
            ticks_since_growth,
        }
    }

    fn from_event_metadata(event: &TelemetryStreamEvent) -> Self {
        Self {
            series_id: event.series_id.clone(),
            stream_id: event.stream_id.clone(),
            label: event.label.clone(),
            unit: event.unit.clone(),
            source: event.source.clone(),
            sample_rate_hz: event.sample_rate_hz,
            values: VecDeque::new(),
            sample_times: VecDeque::new(),
            last_delta: 0,
            ticks_since_growth: 0,
        }
    }

    fn update_metadata(&mut self, event: &TelemetryStreamEvent) {
        self.stream_id = event.stream_id.clone();
        self.label = event.label.clone();
        self.unit = event.unit.clone();
        self.source = event.source.clone();
        self.sample_rate_hz = event.sample_rate_hz;
    }

    fn append_event_samples(&mut self, event: &TelemetryStreamEvent) {
        let mut appended = 0usize;
        if let Some(samples) = event.samples.as_ref().filter(|samples| !samples.is_empty()) {
            for sample in samples {
                if sample.missing.unwrap_or(false)
                    || sample.artifact.unwrap_or(false)
                    || sample
                        .quality
                        .map(|quality| quality <= 0.0)
                        .unwrap_or(false)
                {
                    continue;
                }
                self.push_sample(sample.value, sample.t);
                appended = appended.saturating_add(1);
            }
        } else if let Some(values) = &event.values {
            for value in values {
                self.push_sample(*value, None);
                appended = appended.saturating_add(1);
            }
        }
        self.last_delta = appended;
    }

    fn push_sample(&mut self, value: f64, time_s: Option<f64>) {
        if !value.is_finite() {
            return;
        }
        self.values.push_back(value);
        self.sample_times.push_back(time_s);
        while self.values.len() > MAX_BUFFER_SAMPLES {
            self.values.pop_front();
            self.sample_times.pop_front();
        }
    }

    fn is_active(&self) -> bool {
        !self.values.is_empty() && self.ticks_since_growth <= STALE_TICK_THRESHOLD
    }

    fn sample_delta(&self) -> usize {
        self.last_delta
    }

    fn shown_samples(&self) -> usize {
        self.values.len().min(STREAM_WINDOW_SAMPLES)
    }

    fn last_value(&self) -> Option<f64> {
        self.values.back().copied()
    }
}

impl MatchEvent for App {
    fn handle_startup(&mut self, cx: &mut Cx) {
        let loaded = load_snapshot();
        self.telemetry = RunningTelemetry::from_loaded(loaded);
        self.render_export.path = selected_render_export_path();
        self.shell_contract_read = shell_contract::read_selected_makepad_shell_contract();
        if let Err(error) = shell_contract::write_selected_makepad_shell_contract_read_receipt(
            &self.shell_contract_read,
        ) {
            eprintln!("makepad shell contract read receipt export failed: {error}");
        }
        self.shell_xr_runtime = ShellXrRuntimeState::registered_xr_shell();
        self.update_shell_runtime_capabilities();
        self.apply_snapshot_header(cx);
        self.apply_stream_panels(cx);
        self.write_render_export(true);
        self.stream_timer = cx.start_interval(STREAM_TICK_SECS);
        self.ui.redraw(cx);
    }

    fn handle_timer(&mut self, cx: &mut Cx, event: &TimerEvent) {
        if self.stream_timer.is_timer(event).is_some() {
            if self.telemetry.tick() {
                self.apply_snapshot_header(cx);
            }
            self.apply_stream_panels(cx);
            self.maybe_write_render_export();
            self.ui.redraw(cx);
        }
    }
}

impl App {
    fn debug_line(&self) -> String {
        format!(
            "{} / shell contract {} / {} / {}",
            self.telemetry.debug_line(),
            self.shell_contract_read.status_line(),
            self.shell_runtime_capabilities.status_line(),
            self.shell_xr_runtime.status_line()
        )
    }

    fn update_shell_runtime_capabilities(&mut self) {
        self.shell_runtime_capabilities =
            shell_runtime_capabilities::evaluate(&self.shell_contract_read, &self.shell_xr_runtime);
        if let Err(error) =
            shell_runtime_capabilities::write_selected_makepad_shell_runtime_capability_receipt(
                &self.shell_runtime_capabilities,
            )
        {
            eprintln!("makepad shell runtime capability receipt export failed: {error}");
        }
    }

    fn observe_xr_update(&mut self, cx: &mut Cx, update: &XrUpdateEvent) {
        if self
            .shell_xr_runtime
            .observe_update(cx.in_xr_mode(), update)
        {
            self.update_shell_runtime_capabilities();
            self.ui
                .label(cx, ids!(debug_state))
                .set_text(cx, &self.debug_line());
        }
    }

    fn apply_snapshot_header(&mut self, cx: &mut Cx) {
        let snapshot = &self.telemetry.snapshot;
        self.ui.label(cx, ids!(run_status)).set_text(
            cx,
            &format!(
                "{} / {} / {} / {} modules / graph {}",
                snapshot.run.status,
                snapshot.run.host_profile,
                snapshot.run.mode,
                snapshot.run.selected_module_ids.len(),
                snapshot.run.graph_status
            ),
        );
        self.ui
            .label(cx, ids!(snapshot_source))
            .set_text(cx, &self.telemetry.snapshot_source_line());
        self.ui
            .label(cx, ids!(issue_state))
            .set_text(cx, &issue_text(snapshot));
        self.ui
            .label(cx, ids!(debug_state))
            .set_text(cx, &self.debug_line());
        self.ui.label(cx, ids!(evidence_path)).set_text(
            cx,
            &format!(
                "{} / {} / {}",
                snapshot.evidence.capture,
                snapshot.evidence.runtime_input,
                snapshot.evidence.graph_execution_report
            ),
        );
    }

    fn apply_stream_panels(&mut self, cx: &mut Cx) {
        self.ui
            .label(cx, ids!(stream_state))
            .set_text(cx, &self.telemetry.status_line());
        self.ui
            .label(cx, ids!(debug_state))
            .set_text(cx, &self.debug_line());
        self.set_stream_panel(cx, ids!(stream_1), 0);
        self.set_stream_panel(cx, ids!(stream_2), 1);
        self.set_stream_panel(cx, ids!(stream_3), 2);
        self.set_stream_panel(cx, ids!(stream_4), 3);
        self.set_stream_panel(cx, ids!(stream_5), 4);
        self.set_stream_panel(cx, ids!(stream_6), 5);
    }

    fn set_stream_panel(&mut self, cx: &mut Cx, path: &[LiveId], index: usize) {
        let panel = self.ui.widget(cx, path);
        if let Some(state) = self.telemetry.series_states.get(index) {
            let style = metric_style(state);
            let current = state
                .last_value()
                .map(|value| format_metric_value(value, style.display_unit))
                .unwrap_or_else(|| "--".to_string());
            let rate = state
                .sample_rate_hz
                .map(|value| format!("{:.1} Hz", value))
                .unwrap_or_else(|| "event series".to_string());
            let health = if state.is_active() { "active" } else { "stale" };
            panel.label(cx, ids!(title)).set_text(cx, &state.label);
            panel.label(cx, ids!(status_text)).set_text(cx, health);
            panel.label(cx, ids!(value)).set_text(cx, &current);
            panel.label(cx, ids!(detail)).set_text(
                cx,
                &format!(
                    "{} / {} / +{}",
                    rate,
                    window_text(state),
                    state.sample_delta()
                ),
            );
            if let Some(mut chart) = panel.widget(cx, ids!(plot)).borrow_mut::<LineChart>() {
                chart.set_data(self.telemetry.display_points_for(index));
                chart.set_y_axis_range(self.telemetry.y_axis_range_for(index));
                let color = if state.is_active() {
                    style.active_color
                } else {
                    style.stale_color
                };
                let width = if state.is_active() {
                    style.active_width
                } else {
                    style.stale_width
                };
                chart.set_line_style(color, width);
            }
            panel.widget(cx, ids!(plot)).redraw(cx);
        } else {
            panel.label(cx, ids!(title)).set_text(cx, "waiting");
            panel.label(cx, ids!(status_text)).set_text(cx, "idle");
            panel.label(cx, ids!(value)).set_text(cx, "--");
            panel
                .label(cx, ids!(detail))
                .set_text(cx, "no stream series bound");
            if let Some(mut chart) = panel.widget(cx, ids!(plot)).borrow_mut::<LineChart>() {
                chart.set_data(baseline_points());
                chart.set_y_axis_range(None);
                chart.set_line_style(vec4f(0.45, 0.45, 0.45, 1.0), 1.5);
            }
            panel.widget(cx, ids!(plot)).redraw(cx);
        }
    }

    fn maybe_write_render_export(&mut self) {
        self.render_export.tick_count = self.render_export.tick_count.saturating_add(1);
        if self.render_export.path.is_none() {
            return;
        }
        if self.render_export.tick_count >= RENDER_EXPORT_TICK_INTERVAL
            || self.render_export.last_event_count != self.telemetry.event_count
        {
            self.write_render_export(true);
        }
    }

    fn write_render_export(&mut self, force: bool) {
        let Some(path) = self.render_export.path.clone() else {
            return;
        };
        if !force && self.render_export.last_event_count == self.telemetry.event_count {
            return;
        }
        self.render_export.tick_count = 0;
        match write_makepad_render_png(&self.telemetry, &path) {
            Ok(metrics) => {
                self.render_export.last_event_count = self.telemetry.event_count;
                self.render_export.write_count = self.render_export.write_count.saturating_add(1);
                self.render_export.last_error = None;
                let sidecar = render_sidecar_path(&path);
                if let Err(error) = write_makepad_render_sidecar(
                    &self.telemetry,
                    &path,
                    &sidecar,
                    &metrics,
                    self.render_export.write_count,
                ) {
                    eprintln!("makepad render sidecar export failed: {error}");
                    self.render_export.last_error = Some(error.to_string());
                }
            }
            Err(error) => {
                eprintln!("makepad render export failed: {error}");
                self.render_export.last_error = Some(error.to_string());
            }
        }
    }
}

impl AppMain for App {
    fn script_mod(vm: &mut ScriptVm) -> ScriptValue {
        crate::makepad_widgets::script_mod(vm);
        makepad_xr::script_mod(vm);
        self::script_mod(vm)
    }

    fn handle_event(&mut self, cx: &mut Cx, event: &Event) {
        if matches!(event, Event::Shutdown) && !self.stream_timer.is_empty() {
            cx.stop_timer(self.stream_timer);
            self.stream_timer = Timer::empty();
        }
        if let Event::XrUpdate(update) = event {
            self.observe_xr_update(cx, update);
        }
        self.match_event(cx, event);
        self.ui.handle_event(cx, event, &mut Scope::empty());
    }
}

fn load_snapshot() -> LoadedSnapshot {
    let explicit_path = snapshot_arg();
    let stream_path = selected_stream_path();
    let loaded = snapshot_candidates(explicit_path.as_deref())
        .into_iter()
        .find_map(|path| read_snapshot(PathBuf::from(path)).ok());
    let mut loaded = loaded.unwrap_or_else(|| LoadedSnapshot {
        snapshot: sample_snapshot(),
        path: None,
        stream_path: None,
    });
    loaded.stream_path = stream_path;
    loaded
}

fn read_snapshot(path: PathBuf) -> Result<LoadedSnapshot, std::io::Error> {
    let text = std::fs::read_to_string(&path)?;
    if let Ok(snapshot) = TelemetrySnapshot::deserialize_json_lenient(&text) {
        Ok(LoadedSnapshot {
            snapshot,
            path: Some(path),
            stream_path: None,
        })
    } else {
        Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "snapshot JSON did not match TelemetrySnapshot",
        ))
    }
}

fn snapshot_arg() -> Option<String> {
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--snapshot" {
            return args.next();
        }
    }
    std::env::var("HOSTESS_TELEMETRY_SNAPSHOT").ok()
}

fn stream_arg() -> Option<String> {
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--stream-jsonl" {
            return args.next();
        }
    }
    std::env::var("HOSTESS_TELEMETRY_STREAM").ok()
}

fn render_export_arg() -> Option<String> {
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--render-out" {
            return args.next();
        }
    }
    std::env::var("HOSTESS_TELEMETRY_RENDER_OUT").ok()
}

#[cfg(target_os = "android")]
fn android_default_roots() -> Vec<&'static str> {
    vec![
        ANDROID_INTERNAL_TELEMETRY_ROOT,
        ANDROID_EXTERNAL_TELEMETRY_ROOT,
    ]
}

#[cfg(not(target_os = "android"))]
fn android_default_roots() -> Vec<&'static str> {
    Vec::new()
}

fn snapshot_candidates(explicit_path: Option<&str>) -> Vec<String> {
    if let Some(path) = explicit_path {
        return vec![path.to_string()];
    }
    let mut paths = android_default_roots()
        .into_iter()
        .map(|root| format!("{root}/telemetry-snapshot.json"))
        .collect::<Vec<_>>();
    paths.push("fixtures/telemetry-snapshot.sample.json".to_string());
    paths
}

fn selected_stream_path() -> Option<PathBuf> {
    if let Some(path) = stream_arg() {
        return Some(PathBuf::from(path));
    }
    let candidates = android_default_roots()
        .into_iter()
        .map(|root| PathBuf::from(format!("{root}/telemetry-stream.jsonl")))
        .collect::<Vec<_>>();
    candidates
        .iter()
        .find(|path| path.is_file())
        .cloned()
        .or_else(|| candidates.into_iter().next())
}

fn selected_render_export_path() -> Option<PathBuf> {
    if let Some(path) = render_export_arg() {
        return Some(PathBuf::from(path));
    }
    #[cfg(target_os = "android")]
    {
        return Some(PathBuf::from(format!(
            "{ANDROID_INTERNAL_TELEMETRY_ROOT}/makepad-telemetry-render.png"
        )));
    }
    #[cfg(not(target_os = "android"))]
    {
        None
    }
}

fn baseline_points() -> Vec<DataPoint> {
    vec![DataPoint { x: 0.0, y: 0.0 }, DataPoint { x: 1.0, y: 0.0 }]
}

fn display_leaf(path: &Path) -> String {
    path.file_name()
        .and_then(|name| name.to_str())
        .map(|name| name.to_string())
        .unwrap_or_else(|| path.display().to_string())
}

fn metric_style(state: &SeriesRuntime) -> MetricStyle {
    let label = state.label.to_ascii_lowercase();
    let unit = state.unit.to_ascii_lowercase();
    if unit == "bpm" || label == "hr" || label.contains("heart rate") {
        return MetricStyle {
            display_unit: "bpm",
            axis: AxisPolicy::Soft {
                min: 40.0,
                max: 180.0,
            },
            active_color: vec4f(0.08, 0.37, 0.46, 1.0),
            stale_color: vec4f(0.49, 0.58, 0.60, 1.0),
            active_width: 2.25,
            stale_width: 1.25,
        };
    }
    if unit == "ms" || label == "rr" || label.contains("rr") || label.contains("nn") {
        return MetricStyle {
            display_unit: "ms",
            axis: AxisPolicy::Soft {
                min: 400.0,
                max: 1400.0,
            },
            active_color: vec4f(0.13, 0.31, 0.62, 1.0),
            stale_color: vec4f(0.48, 0.53, 0.64, 1.0),
            active_width: 2.15,
            stale_width: 1.25,
        };
    }
    if is_normalized_unit(&unit)
        || label.contains("breath")
        || label.contains("coherence")
        || label.contains("score")
    {
        return MetricStyle {
            display_unit: "norm",
            axis: AxisPolicy::Fixed { min: 0.0, max: 1.0 },
            active_color: vec4f(0.18, 0.48, 0.31, 1.0),
            stale_color: vec4f(0.47, 0.56, 0.50, 1.0),
            active_width: 2.15,
            stale_width: 1.25,
        };
    }
    if unit == "uv" || unit == "microvolt" || unit == "microvolts" || label.contains("ecg") {
        return MetricStyle {
            display_unit: "uV",
            axis: AxisPolicy::Rolling { pad_fraction: 0.12 },
            active_color: vec4f(0.54, 0.24, 0.51, 1.0),
            stale_color: vec4f(0.58, 0.50, 0.58, 1.0),
            active_width: 1.9,
            stale_width: 1.15,
        };
    }
    if unit == "mg" || label.contains("acc") {
        return MetricStyle {
            display_unit: "mg",
            axis: AxisPolicy::Rolling { pad_fraction: 0.12 },
            active_color: vec4f(0.60, 0.38, 0.13, 1.0),
            stale_color: vec4f(0.60, 0.55, 0.48, 1.0),
            active_width: 1.9,
            stale_width: 1.15,
        };
    }
    MetricStyle {
        display_unit: "",
        axis: AxisPolicy::Rolling { pad_fraction: 0.10 },
        active_color: vec4f(0.16, 0.39, 0.44, 1.0),
        stale_color: vec4f(0.50, 0.55, 0.56, 1.0),
        active_width: 2.0,
        stale_width: 1.2,
    }
}

fn is_normalized_unit(unit: &str) -> bool {
    matches!(
        unit,
        "01" | "0-1" | "0..1" | "norm" | "normalized" | "ratio" | "score"
    )
}

fn format_metric_value(value: f64, unit: &str) -> String {
    match unit {
        "bpm" => format!("{value:.0} bpm"),
        "ms" => format!("{value:.0} ms"),
        "uV" => format!("{value:.0} uV"),
        "mg" => format!("{value:.0} mg"),
        "norm" => format!("{value:.2}"),
        "" => format!("{value:.2}"),
        _ => format!("{value:.2} {unit}"),
    }
}

fn is_hr_series(state: &SeriesRuntime) -> bool {
    let label = state.label.to_ascii_lowercase();
    let unit = state.unit.to_ascii_lowercase();
    unit == "bpm" || label == "hr" || label.contains("heart rate")
}

fn is_rr_series(state: &SeriesRuntime) -> bool {
    let label = state.label.to_ascii_lowercase();
    let unit = state.unit.to_ascii_lowercase();
    unit == "ms" || label == "rr" || label.contains("rr") || label.contains("nn")
}

fn window_text(state: &SeriesRuntime) -> String {
    let shown = state.shown_samples();
    if is_rr_series(state) {
        return format!("{shown} beats");
    }
    if let Some(rate_hz) = state.sample_rate_hz.filter(|rate| *rate > 0.0) {
        let seconds = shown as f64 / rate_hz;
        if seconds >= 60.0 {
            format!("{:.1} min window", seconds / 60.0)
        } else if seconds < 1.0 {
            format!("{seconds:.1} s window")
        } else {
            format!("{seconds:.0} s window")
        }
    } else {
        format!("{shown} samples")
    }
}

fn smooth_points_ema(mut points: Vec<DataPoint>, alpha: f64) -> Vec<DataPoint> {
    if points.len() < 3 {
        return points;
    }
    let mut y = points[0].y;
    for point in &mut points {
        y = alpha * point.y + (1.0 - alpha) * y;
        point.y = y;
    }
    points
}

fn axis_bounds_for_state(state: &SeriesRuntime, values: &[f64]) -> (f64, f64) {
    let label = state.label.to_ascii_lowercase();
    let unit = state.unit.to_ascii_lowercase();
    if unit == "bpm" || label == "hr" || label.contains("heart rate") {
        return adaptive_bounds(values, 8.0, 35.0, 220.0, 0.18);
    }
    if unit == "ms" || label == "rr" || label.contains("rr") || label.contains("nn") {
        return adaptive_bounds(values, 120.0, 300.0, 2000.0, 0.18);
    }
    if is_normalized_unit(&unit)
        || label.contains("breath")
        || label.contains("coherence")
        || label.contains("score")
    {
        return (0.0, 1.0);
    }
    axis_bounds(metric_style(state).axis, values)
}

fn adaptive_bounds(
    values: &[f64],
    min_span: f64,
    hard_min: f64,
    hard_max: f64,
    pad_fraction: f64,
) -> (f64, f64) {
    let (low, high) = quantile_extent(values, 0.05, 0.95);
    let center = (low + high) * 0.5;
    let observed_span = (high - low).abs();
    let span = (observed_span * (1.0 + 2.0 * pad_fraction)).max(min_span);
    let mut min = center - span * 0.5;
    let mut max = center + span * 0.5;

    if min < hard_min {
        let shift = hard_min - min;
        min += shift;
        max += shift;
    }
    if max > hard_max {
        let shift = max - hard_max;
        min -= shift;
        max -= shift;
    }
    (min.max(hard_min), max.min(hard_max))
}

fn axis_bounds(policy: AxisPolicy, values: &[f64]) -> (f64, f64) {
    match policy {
        AxisPolicy::Fixed { min, max } => (min, max),
        AxisPolicy::Soft { min, max } => {
            let (observed_min, observed_max) = value_extent(values);
            let range_min = observed_min.min(min);
            let range_max = observed_max.max(max);
            padded_bounds(range_min, range_max, 0.04)
        }
        AxisPolicy::Rolling { pad_fraction } => {
            let (observed_min, observed_max) = quantile_extent(values, 0.05, 0.95);
            padded_bounds(observed_min, observed_max, pad_fraction)
        }
    }
}

fn value_extent(values: &[f64]) -> (f64, f64) {
    let mut min = f64::INFINITY;
    let mut max = f64::NEG_INFINITY;
    for value in values {
        min = min.min(*value);
        max = max.max(*value);
    }
    if min < max {
        (min, max)
    } else {
        padded_bounds(min, max, 0.10)
    }
}

fn quantile_extent(values: &[f64], low: f64, high: f64) -> (f64, f64) {
    let mut sorted = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    if sorted.is_empty() {
        return (0.0, 1.0);
    }
    let last = sorted.len().saturating_sub(1);
    let low_index = ((last as f64) * low.clamp(0.0, 1.0)).round() as usize;
    let high_index = ((last as f64) * high.clamp(0.0, 1.0)).round() as usize;
    let min = sorted[low_index.min(last)];
    let max = sorted[high_index.min(last)];
    if min < max {
        (min, max)
    } else {
        value_extent(values)
    }
}

fn padded_bounds(min: f64, max: f64, pad_fraction: f64) -> (f64, f64) {
    if !min.is_finite() || !max.is_finite() {
        return (0.0, 1.0);
    }
    let span = (max - min).abs().max(1.0);
    let pad = span * pad_fraction.max(0.0);
    (min - pad, max + pad)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Rgb(u8, u8, u8);

#[derive(Clone, Copy, Debug)]
struct RenderMetrics {
    width: usize,
    height: usize,
    content_pixel_count: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum RenderTelemetryLayout {
    Vertical,
    Horizontal,
}

struct RenderCanvas {
    width: usize,
    height: usize,
    pixels: Vec<u8>,
    background: Rgb,
}

impl RenderCanvas {
    fn new(width: usize, height: usize, background: Rgb) -> Self {
        let mut pixels = Vec::with_capacity(width * height * 3);
        for _ in 0..(width * height) {
            pixels.extend_from_slice(&[background.0, background.1, background.2]);
        }
        Self {
            width,
            height,
            pixels,
            background,
        }
    }

    fn fill_rect(&mut self, left: i32, top: i32, width: i32, height: i32, color: Rgb) {
        let x0 = left.max(0) as usize;
        let y0 = top.max(0) as usize;
        let x1 = (left + width).clamp(0, self.width as i32) as usize;
        let y1 = (top + height).clamp(0, self.height as i32) as usize;
        for y in y0..y1 {
            for x in x0..x1 {
                self.set_pixel(x as i32, y as i32, color);
            }
        }
    }

    fn stroke_rect(&mut self, left: i32, top: i32, width: i32, height: i32, color: Rgb) {
        self.fill_rect(left, top, width, 1, color);
        self.fill_rect(left, top + height - 1, width, 1, color);
        self.fill_rect(left, top, 1, height, color);
        self.fill_rect(left + width - 1, top, 1, height, color);
    }

    fn draw_line(&mut self, x0: f64, y0: f64, x1: f64, y1: f64, color: Rgb, width: i32) {
        let steps = ((x1 - x0).abs().max((y1 - y0).abs()).ceil() as i32).max(1);
        let radius = (width.max(1) - 1) / 2;
        for step in 0..=steps {
            let t = step as f64 / steps as f64;
            let x = (x0 + (x1 - x0) * t).round() as i32;
            let y = (y0 + (y1 - y0) * t).round() as i32;
            self.fill_rect(x - radius, y - radius, width.max(1), width.max(1), color);
        }
    }

    fn draw_dot(&mut self, cx: f64, cy: f64, radius: i32, color: Rgb) {
        let cx = cx.round() as i32;
        let cy = cy.round() as i32;
        let r2 = radius * radius;
        for y in (cy - radius)..=(cy + radius) {
            for x in (cx - radius)..=(cx + radius) {
                let dx = x - cx;
                let dy = y - cy;
                if dx * dx + dy * dy <= r2 {
                    self.set_pixel(x, y, color);
                }
            }
        }
    }

    fn draw_text(&mut self, left: i32, top: i32, text: &str, scale: i32, color: Rgb) {
        let mut x = left;
        let scale = scale.max(1);
        for ch in text.chars() {
            if ch == '\n' {
                x = left;
                continue;
            }
            self.draw_glyph(x, top, ch.to_ascii_uppercase(), scale, color);
            x += 6 * scale;
        }
    }

    fn draw_text_clipped(
        &mut self,
        left: i32,
        top: i32,
        text: &str,
        scale: i32,
        color: Rgb,
        max_width: i32,
    ) {
        if max_width <= 0 {
            return;
        }
        let step = 6 * scale.max(1);
        let max_chars = (max_width / step).max(1) as usize;
        self.draw_text(left, top, &truncate_text(text, max_chars), scale, color);
    }

    fn draw_glyph(&mut self, left: i32, top: i32, ch: char, scale: i32, color: Rgb) {
        let rows = glyph_rows(ch);
        for (row_index, row) in rows.iter().enumerate() {
            for col in 0..5 {
                if row & (1 << (4 - col)) != 0 {
                    self.fill_rect(
                        left + col * scale,
                        top + row_index as i32 * scale,
                        scale,
                        scale,
                        color,
                    );
                }
            }
        }
    }

    fn set_pixel(&mut self, x: i32, y: i32, color: Rgb) {
        if x < 0 || y < 0 || x >= self.width as i32 || y >= self.height as i32 {
            return;
        }
        let offset = (y as usize * self.width + x as usize) * 3;
        self.pixels[offset] = color.0;
        self.pixels[offset + 1] = color.1;
        self.pixels[offset + 2] = color.2;
    }

    fn content_pixel_count(&self) -> usize {
        self.pixels
            .chunks_exact(3)
            .filter(|pixel| {
                pixel[0] != self.background.0
                    || pixel[1] != self.background.1
                    || pixel[2] != self.background.2
            })
            .count()
    }
}

fn write_makepad_render_png(
    telemetry: &RunningTelemetry,
    path: &Path,
) -> Result<RenderMetrics, String> {
    let layout = render_layout_for(telemetry);
    let (width, height) = render_dimensions(layout);
    let mut canvas = RenderCanvas::new(width, height, Rgb(248, 248, 246));
    render_makepad_telemetry(&mut canvas, telemetry, layout);
    let content_pixel_count = canvas.content_pixel_count();
    if content_pixel_count < MIN_RENDER_CONTENT_PIXELS {
        return Err(format!(
            "makepad render appears blank: {content_pixel_count} content pixels"
        ));
    }
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let options =
        makepad_widgets::makepad_zune_png::makepad_zune_core::options::EncoderOptions::default()
            .set_width(canvas.width)
            .set_height(canvas.height)
            .set_depth(
                makepad_widgets::makepad_zune_png::makepad_zune_core::bit_depth::BitDepth::Eight,
            )
            .set_colorspace(
                makepad_widgets::makepad_zune_png::makepad_zune_core::colorspace::ColorSpace::RGB,
            );
    let mut encoder = makepad_widgets::makepad_zune_png::PngEncoder::new(&canvas.pixels, options);
    let mut png = Vec::new();
    encoder
        .encode(&mut png)
        .map_err(|error| format!("could not encode makepad render PNG: {error:?}"))?;
    write_atomic(path, &png).map_err(|error| error.to_string())?;
    Ok(RenderMetrics {
        width: canvas.width,
        height: canvas.height,
        content_pixel_count,
    })
}

fn render_layout_for(telemetry: &RunningTelemetry) -> RenderTelemetryLayout {
    match telemetry
        .snapshot
        .run
        .host_profile
        .trim()
        .to_ascii_lowercase()
        .as_str()
    {
        "mobile" | "headset" | "quest" | "phone" => RenderTelemetryLayout::Vertical,
        _ => RenderTelemetryLayout::Horizontal,
    }
}

fn render_dimensions(layout: RenderTelemetryLayout) -> (usize, usize) {
    match layout {
        RenderTelemetryLayout::Vertical => (RENDER_WIDTH_VERTICAL, RENDER_HEIGHT_VERTICAL),
        RenderTelemetryLayout::Horizontal => (RENDER_WIDTH_HORIZONTAL, RENDER_HEIGHT_HORIZONTAL),
    }
}

fn write_makepad_render_sidecar(
    telemetry: &RunningTelemetry,
    image_path: &Path,
    sidecar_path: &Path,
    metrics: &RenderMetrics,
    write_count: usize,
) -> Result<(), std::io::Error> {
    let rendered_at_unix_ms = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|duration| duration.as_millis())
        .unwrap_or(0);
    let target = if telemetry.snapshot.run.host_profile.is_empty() {
        "unknown"
    } else {
        telemetry.snapshot.run.host_profile.as_str()
    };
    let layout = render_layout_for(telemetry);
    let layout_name = match layout {
        RenderTelemetryLayout::Vertical => "vertical",
        RenderTelemetryLayout::Horizontal => "horizontal",
    };
    let sidecar = format!(
        concat!(
            "{{\n",
            "  \"$schema\": \"rusty.hostess.telemetry.render_evidence.v1\",\n",
            "  \"status\": \"pass\",\n",
            "  \"render_method\": \"makepad.data_model_png.v1\",\n",
            "  \"render_page\": \"watcher\",\n",
            "  \"layout\": {},\n",
            "  \"target\": {},\n",
            "  \"image_path\": {},\n",
            "  \"source_evidence_path\": {},\n",
            "  \"snapshot_id\": {},\n",
            "  \"foreground_required\": false,\n",
            "  \"screen_occlusion_required_clear\": false,\n",
            "  \"width\": {},\n",
            "  \"height\": {},\n",
            "  \"content_pixel_count\": {},\n",
            "  \"stream_line_count\": {},\n",
            "  \"event_count\": {},\n",
            "  \"active_series_count\": {},\n",
            "  \"stale_series_count\": {},\n",
            "  \"sample_total\": {},\n",
            "  \"watcher_status_line\": {},\n",
            "  \"write_count\": {},\n",
            "  \"rendered_at_unix_ms\": {},\n",
            "  \"validation\": {{\n",
            "    \"min_width\": 320,\n",
            "    \"min_height\": 240,\n",
            "    \"min_content_pixels\": {}\n",
            "  }}\n",
            "}}\n"
        ),
        json_string(layout_name),
        json_string(target),
        json_string(&image_path.display().to_string()),
        json_string(&telemetry.render_source_path()),
        json_string(&telemetry.snapshot.snapshot_id),
        metrics.width,
        metrics.height,
        metrics.content_pixel_count,
        telemetry.stream_line_count,
        telemetry.event_count,
        telemetry.active_series_count(),
        telemetry.stale_series_count(),
        telemetry.sample_total(),
        json_string(&telemetry.status_line()),
        write_count,
        rendered_at_unix_ms,
        MIN_RENDER_CONTENT_PIXELS
    );
    write_atomic(sidecar_path, sidecar.as_bytes())
}

fn render_sidecar_path(image_path: &Path) -> PathBuf {
    PathBuf::from(format!("{}.json", image_path.display()))
}

fn write_atomic(path: &Path, bytes: &[u8]) -> Result<(), std::io::Error> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("render");
    let tmp_path = path.with_file_name(format!(".{file_name}.tmp.{}", std::process::id()));
    std::fs::write(&tmp_path, bytes)?;
    match std::fs::rename(&tmp_path, path) {
        Ok(()) => Ok(()),
        Err(first_error) => {
            if path.exists() {
                let _ = std::fs::remove_file(path);
                if std::fs::rename(&tmp_path, path).is_ok() {
                    return Ok(());
                }
            }
            let _ = std::fs::remove_file(&tmp_path);
            Err(first_error)
        }
    }
}

fn render_makepad_telemetry(
    canvas: &mut RenderCanvas,
    telemetry: &RunningTelemetry,
    layout: RenderTelemetryLayout,
) {
    let text = Rgb(29, 29, 27);
    let muted = Rgb(116, 109, 100);
    let accent = Rgb(21, 94, 117);
    let margin = 28;
    let content_width = canvas.width as i32 - margin * 2;
    draw_card(canvas, margin, 20, content_width, 110);
    canvas.draw_text(48, 40, "RUSTY HOSTESS T", 3, text);
    canvas.draw_text_clipped(
        48,
        72,
        &format!(
            "{} / {} / {} / {} MODULES / GRAPH {}",
            telemetry.snapshot.run.status,
            telemetry.snapshot.run.host_profile,
            telemetry.snapshot.run.mode,
            telemetry.snapshot.run.selected_module_ids.len(),
            telemetry.snapshot.run.graph_status
        ),
        2,
        muted,
        content_width - 40,
    );
    canvas.draw_text_clipped(
        48,
        98,
        &telemetry.status_line(),
        2,
        accent,
        content_width - 40,
    );

    match layout {
        RenderTelemetryLayout::Vertical => {
            for index in 0..6 {
                let top = 150 + index as i32 * 204;
                draw_render_stream_card(canvas, telemetry, index, margin, top, content_width, 184);
            }
        }
        RenderTelemetryLayout::Horizontal => {
            for index in 0..6 {
                let col = index % 2;
                let row = index / 2;
                let left = margin + col as i32 * 536;
                let top = 150 + row as i32 * 204;
                draw_render_stream_card(canvas, telemetry, index, left, top, 520, 184);
            }
        }
    }

    let footer_top = canvas.height as i32 - 58;
    draw_card(canvas, margin, footer_top, content_width, 38);
    canvas.draw_text_clipped(
        48,
        footer_top + 14,
        &format!(
            "SOURCE {} / LINES {} / EVENTS {}",
            display_leaf(Path::new(&telemetry.render_source_path())),
            telemetry.stream_line_count,
            telemetry.event_count
        ),
        2,
        muted,
        content_width - 40,
    );
}

fn draw_render_stream_card(
    canvas: &mut RenderCanvas,
    telemetry: &RunningTelemetry,
    index: usize,
    left: i32,
    top: i32,
    width: i32,
    height: i32,
) {
    draw_card(canvas, left, top, width, height);
    let Some(state) = telemetry.series_states.get(index) else {
        canvas.draw_text_clipped(
            left + 18,
            top + 18,
            "WAITING",
            2,
            Rgb(29, 29, 27),
            width - 36,
        );
        canvas.draw_text_clipped(
            left + 18,
            top + 46,
            "NO STREAM SERIES BOUND",
            2,
            Rgb(116, 109, 100),
            width - 36,
        );
        draw_plot_box(canvas, left + 14, top + 64, width - 28, height - 78);
        return;
    };
    let style = metric_style(state);
    let line_color = if state.is_active() {
        rgb_from_vec4(style.active_color)
    } else {
        Rgb(140, 148, 148)
    };
    let value = state
        .last_value()
        .map(|value| format_metric_value(value, style.display_unit))
        .unwrap_or_else(|| "--".to_string());
    let rate = state
        .sample_rate_hz
        .map(|value| format!("{value:.1} HZ"))
        .unwrap_or_else(|| "EVENT SERIES".to_string());
    let health = if state.is_active() { "ACTIVE" } else { "STALE" };
    let value_width = 170;
    let title_width = (width - value_width - 112).clamp(90, 280);
    let status_left = left + 18 + title_width + 8;
    canvas.draw_text_clipped(
        left + 18,
        top + 17,
        &state.label,
        2,
        Rgb(29, 29, 27),
        title_width,
    );
    canvas.fill_rect(status_left, top + 15, 58, 18, Rgb(234, 244, 239));
    canvas.draw_text(status_left + 6, top + 19, health, 1, Rgb(47, 107, 79));
    canvas.draw_text_clipped(
        left + width - value_width - 18,
        top + 14,
        &value,
        2,
        Rgb(21, 94, 117),
        value_width,
    );
    canvas.draw_text_clipped(
        left + 18,
        top + 44,
        &format!(
            "{} / {} / +{}",
            rate,
            window_text(state),
            state.sample_delta()
        ),
        1,
        Rgb(116, 109, 100),
        width - 36,
    );
    let plot = (left + 14, top + 64, width - 28, height - 78);
    draw_plot_box(canvas, plot.0, plot.1, plot.2, plot.3);
    draw_render_series(
        canvas,
        telemetry,
        index,
        plot,
        line_color,
        state.is_active(),
    );
}

fn draw_card(canvas: &mut RenderCanvas, left: i32, top: i32, width: i32, height: i32) {
    canvas.fill_rect(left, top, width, height, Rgb(255, 255, 255));
    canvas.stroke_rect(left, top, width, height, Rgb(224, 220, 213));
}

fn draw_plot_box(canvas: &mut RenderCanvas, left: i32, top: i32, width: i32, height: i32) {
    canvas.fill_rect(left, top, width, height, Rgb(249, 250, 247));
    canvas.stroke_rect(left, top, width, height, Rgb(227, 222, 214));
}

fn draw_render_series(
    canvas: &mut RenderCanvas,
    telemetry: &RunningTelemetry,
    index: usize,
    plot: (i32, i32, i32, i32),
    color: Rgb,
    active: bool,
) {
    let (left, top, width, height) = plot;
    let inner_left = left + 8;
    let inner_top = top + 8;
    let inner_width = width - 18;
    let inner_height = height - 16;
    let grid = Rgb(230, 224, 215);
    for step in 1..3 {
        let y = inner_top + inner_height * step / 3;
        canvas.fill_rect(inner_left, y, inner_width, 1, grid);
    }
    for step in 1..4 {
        let x = inner_left + inner_width * step / 4;
        canvas.fill_rect(x, inner_top, 1, inner_height, grid);
    }
    let points = telemetry.display_points_for(index);
    if points.len() < 2 {
        canvas.draw_text(
            inner_left + 8,
            inner_top + inner_height / 2 - 4,
            "WAITING",
            1,
            Rgb(116, 109, 100),
        );
        return;
    }
    let (Some((y_min, y_max)), Some((x_min, x_max))) =
        (telemetry.y_axis_range_for(index), point_x_bounds(&points))
    else {
        return;
    };
    let width_px = if active { 3 } else { 2 };
    let mut previous: Option<(f64, f64)> = None;
    for point in &points {
        let x = inner_left as f64 + ((point.x - x_min) / (x_max - x_min)) * inner_width as f64;
        let y = inner_top as f64
            + (1.0 - ((point.y - y_min) / (y_max - y_min)).clamp(0.0, 1.0)) * inner_height as f64;
        if let Some((px, py)) = previous {
            canvas.draw_line(px, py, x, y, color, width_px);
        }
        previous = Some((x, y));
    }
    if let Some((x, y)) = previous {
        canvas.draw_dot(x, y, 4, color);
    }
}

fn point_x_bounds(points: &[DataPoint]) -> Option<(f64, f64)> {
    let min = points
        .iter()
        .map(|point| point.x)
        .fold(f64::INFINITY, f64::min);
    let max = points
        .iter()
        .map(|point| point.x)
        .fold(f64::NEG_INFINITY, f64::max);
    if min.is_finite() && max.is_finite() && min < max {
        Some((min, max))
    } else {
        None
    }
}

fn rgb_from_vec4(color: Vec4f) -> Rgb {
    Rgb(
        (color.x.clamp(0.0, 1.0) * 255.0).round() as u8,
        (color.y.clamp(0.0, 1.0) * 255.0).round() as u8,
        (color.z.clamp(0.0, 1.0) * 255.0).round() as u8,
    )
}

fn truncate_text(value: &str, max_chars: usize) -> String {
    let char_count = value.chars().count();
    if char_count <= max_chars {
        return value.to_string();
    }
    if max_chars <= 1 {
        return ".".to_string();
    }
    let mut text = value
        .chars()
        .take(max_chars.saturating_sub(1))
        .collect::<String>();
    text.push('.');
    text
}

fn json_string(value: &str) -> String {
    let mut out = String::from("\"");
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            _ => out.push(ch),
        }
    }
    out.push('"');
    out
}

fn glyph_rows(ch: char) -> [u8; 7] {
    match ch {
        'A' => [
            0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001,
        ],
        'B' => [
            0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110,
        ],
        'C' => [
            0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110,
        ],
        'D' => [
            0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110,
        ],
        'E' => [
            0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111,
        ],
        'F' => [
            0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000,
        ],
        'G' => [
            0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110,
        ],
        'H' => [
            0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001,
        ],
        'I' => [
            0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b11111,
        ],
        'J' => [
            0b00111, 0b00010, 0b00010, 0b00010, 0b10010, 0b10010, 0b01100,
        ],
        'K' => [
            0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001,
        ],
        'L' => [
            0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111,
        ],
        'M' => [
            0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001,
        ],
        'N' => [
            0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001,
        ],
        'O' => [
            0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110,
        ],
        'P' => [
            0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000,
        ],
        'Q' => [
            0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101,
        ],
        'R' => [
            0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001,
        ],
        'S' => [
            0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110,
        ],
        'T' => [
            0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100,
        ],
        'U' => [
            0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110,
        ],
        'V' => [
            0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100,
        ],
        'W' => [
            0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010,
        ],
        'X' => [
            0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001,
        ],
        'Y' => [
            0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100,
        ],
        'Z' => [
            0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111,
        ],
        '0' => [
            0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110,
        ],
        '1' => [
            0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110,
        ],
        '2' => [
            0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111,
        ],
        '3' => [
            0b11110, 0b00001, 0b00001, 0b01110, 0b00001, 0b00001, 0b11110,
        ],
        '4' => [
            0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010,
        ],
        '5' => [
            0b11111, 0b10000, 0b10000, 0b11110, 0b00001, 0b00001, 0b11110,
        ],
        '6' => [
            0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110,
        ],
        '7' => [
            0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000,
        ],
        '8' => [
            0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110,
        ],
        '9' => [
            0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110,
        ],
        '-' => [0, 0, 0, 0b11111, 0, 0, 0],
        '+' => [0, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0],
        '.' => [0, 0, 0, 0, 0, 0b01100, 0b01100],
        ':' => [0, 0b01100, 0b01100, 0, 0b01100, 0b01100, 0],
        '/' => [
            0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000,
        ],
        '_' => [0, 0, 0, 0, 0, 0, 0b11111],
        ' ' => [0, 0, 0, 0, 0, 0, 0],
        _ => [0, 0, 0, 0b11111, 0, 0, 0],
    }
}

fn fallback_series(snapshot: &TelemetrySnapshot) -> Vec<TelemetrySeries> {
    let mut series = Vec::new();
    for stream in &snapshot.raw_streams {
        if !stream.preview.is_empty() {
            series.push(TelemetrySeries {
                series_id: format!("{}.preview", stream.stream_id),
                stream_id: stream.stream_id.clone(),
                label: short_stream_id(&stream.stream_id),
                unit: inferred_unit(&stream.stream_id).to_string(),
                source: "raw_stream.preview".to_string(),
                sample_rate_hz: None,
                values: stream.preview.clone(),
            });
        }
    }
    if series.is_empty() {
        series.push(TelemetrySeries {
            series_id: "series.fallback.heartbeat".to_string(),
            stream_id: "stream.fallback".to_string(),
            label: "fallback heartbeat".to_string(),
            unit: "a.u.".to_string(),
            source: "embedded sample".to_string(),
            sample_rate_hz: Some(1.0),
            values: vec![0.2, 0.4, 0.8, 0.35, 0.6, 0.5, 0.9, 0.45],
        });
    }
    series
}

fn inferred_unit(stream_id: &str) -> &'static str {
    if stream_id.ends_with(".hr_rr") {
        "ms"
    } else if stream_id.ends_with(".acc") {
        "mg"
    } else if stream_id.ends_with(".ecg") {
        "uV"
    } else {
        "value"
    }
}

fn issue_text(snapshot: &TelemetrySnapshot) -> String {
    if snapshot.issues.is_empty() {
        format!(
            "no issues / runtime {} / {} module outputs",
            snapshot.run.runtime_path,
            snapshot.module_outputs.len()
        )
    } else {
        snapshot
            .issues
            .iter()
            .take(3)
            .map(|issue| format!("{}: {}", issue.code, issue.message))
            .collect::<Vec<_>>()
            .join(" / ")
    }
}

fn short_stream_id(stream_id: &str) -> String {
    stream_id
        .rsplit('.')
        .next()
        .unwrap_or(stream_id)
        .replace('_', " ")
}

fn sample_snapshot() -> TelemetrySnapshot {
    TelemetrySnapshot {
        snapshot_id: "snapshot.fallback".to_string(),
        source_evidence_path: "embedded sample".to_string(),
        run: SnapshotRun {
            status: "pass".to_string(),
            host_profile: "desktop".to_string(),
            mode: "module".to_string(),
            runtime_path: "rust.polar_h10_core.v1".to_string(),
            graph_id: "graph.polar_h10_processing".to_string(),
            graph_status: "pass".to_string(),
            selected_module_ids: vec![
                "module.polar_h10.hrv_window".to_string(),
                "module.polar_h10.coherence".to_string(),
            ],
        },
        raw_streams: Vec::new(),
        module_outputs: vec![ModuleOutput {
            stream_id: "stream.polar_h10.coherence".to_string(),
            module_id: "module.polar_h10.coherence".to_string(),
            status: "pass".to_string(),
            input_stream_id: "stream.polar_h10.hr_rr".to_string(),
            summary: "0.952 coherence".to_string(),
            issue_code: None,
        }],
        time_series: vec![
            TelemetrySeries {
                series_id: "series.sample.hr_bpm".to_string(),
                stream_id: "stream.polar_h10.hr_rr".to_string(),
                label: "HR".to_string(),
                unit: "bpm".to_string(),
                source: "embedded".to_string(),
                sample_rate_hz: Some(1.0),
                values: vec![60.0, 59.4, 60.6, 59.7, 60.3, 60.0],
            },
            TelemetrySeries {
                series_id: "series.sample.rr_ms".to_string(),
                stream_id: "stream.polar_h10.hr_rr".to_string(),
                label: "RR".to_string(),
                unit: "ms".to_string(),
                source: "embedded".to_string(),
                sample_rate_hz: Some(1.0),
                values: vec![1000.0, 1010.0, 990.0, 1005.0, 995.0, 1000.0],
            },
            TelemetrySeries {
                series_id: "series.sample.breath_volume".to_string(),
                stream_id: "stream.polar_h10.breath_volume".to_string(),
                label: "Breath volume".to_string(),
                unit: "01".to_string(),
                source: "embedded".to_string(),
                sample_rate_hz: Some(1.0),
                values: vec![0.0, 0.25, 0.5, 0.75, 1.0, 0.75],
            },
        ],
        issues: Vec::new(),
        evidence: EvidencePaths {
            capture: "embedded".to_string(),
            runtime_input: "embedded".to_string(),
            graph_execution_report: "embedded".to_string(),
        },
    }
}
