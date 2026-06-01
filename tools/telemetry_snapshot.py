from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SNAPSHOT_SCHEMA = "rusty.hostess.telemetry.snapshot.v1"
MAX_PREVIEW_VALUES = 24
MAX_SERIES_VALUES = 256

DIRECT_STREAM_IDS = {
    "stream.polar_h10.hr_rr",
    "stream.polar_h10.acc",
    "stream.polar_h10.ecg",
}

MODULE_METRIC_FIELDS = [
    "ln_rmssd",
    "ln_rmssd_gain",
    "normalized_score",
    "breath_volume_01",
    "breathing_rate_bpm",
    "amplitude_bpm",
    "quality",
]


def build_snapshot(
    evidence_path: Path,
    *,
    graph_report_path: Path | None = None,
    runtime_input_path: Path | None = None,
) -> dict[str, Any]:
    evidence = load_json(evidence_path)
    capture = dict_value(evidence.get("capture"))
    graph_report = load_optional_json(resolve_artifact(evidence_path, graph_report_path, capture.get("graph_execution_report")))
    runtime_input = load_optional_json(resolve_artifact(evidence_path, runtime_input_path, capture.get("runtime_input")))

    streams = [stream for stream in evidence.get("streams", []) if isinstance(stream, dict)]
    graph_streams = [stream for stream in graph_report.get("streams", []) if isinstance(stream, dict)]
    if graph_streams:
        streams = merge_streams(streams, graph_streams)

    issues = collect_issues(evidence, graph_report, streams)
    selected_modules = [str(value) for value in capture.get("selected_module_ids", [])]

    return {
        "$schema": SNAPSHOT_SCHEMA,
        "snapshot_id": f"snapshot.{evidence_path.stem}",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_evidence_path": str(evidence_path),
        "run": {
            "status": str(evidence.get("status", "unknown")),
            "host_profile": str(evidence.get("host_profile", "unknown")),
            "mode": str(capture.get("mode", "unknown")),
            "runtime_path": str(capture.get("runtime_path", "")),
            "graph_id": str(capture.get("graph_id", graph_report.get("graph_id", ""))),
            "graph_status": str(graph_report.get("status", "waiting")),
            "selected_module_ids": selected_modules,
        },
        "raw_streams": [raw_stream_summary(stream, runtime_input) for stream in streams if is_direct_stream(stream)],
        "module_outputs": [module_output_summary(stream) for stream in streams if is_module_stream(stream)],
        "time_series": time_series(runtime_input),
        "issues": issues[:16],
        "evidence": {
            "capture": str(evidence_path),
            "runtime_input": str(resolve_artifact(evidence_path, runtime_input_path, capture.get("runtime_input")) or ""),
            "graph_execution_report": str(resolve_artifact(evidence_path, graph_report_path, capture.get("graph_execution_report")) or ""),
        },
        "commands": telemetry_commands(),
    }


def write_snapshot(snapshot: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object in {path}")
    return value


def load_optional_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return load_json(path)


def resolve_artifact(evidence_path: Path, explicit: Path | None, relative_name: Any) -> Path | None:
    if explicit is not None:
        return explicit
    if isinstance(relative_name, str) and relative_name:
        candidate = evidence_path.with_name(relative_name)
        if candidate.exists():
            return candidate
        for suffix in [".runtime-input.json", ".graph-execution-report.json"]:
            if relative_name.endswith(suffix):
                sibling = evidence_path.with_name(f"{evidence_path.stem}{suffix}")
                if sibling.exists():
                    return sibling
        return candidate
    return None


def merge_streams(primary: list[dict[str, Any]], graph_streams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for stream in primary:
        stream_id = str(stream.get("stream_id", ""))
        if stream_id:
            by_id[stream_id] = dict(stream)
    for stream in graph_streams:
        stream_id = str(stream.get("stream_id", ""))
        if stream_id:
            merged = dict(by_id.get(stream_id, {}))
            merged.update(stream)
            by_id[stream_id] = merged
    return list(by_id.values())


def is_direct_stream(stream: dict[str, Any]) -> bool:
    return str(stream.get("stream_id", "")) in DIRECT_STREAM_IDS


def is_module_stream(stream: dict[str, Any]) -> bool:
    stream_id = str(stream.get("stream_id", ""))
    return bool(stream.get("module_id")) or (stream_id and stream_id not in DIRECT_STREAM_IDS)


def raw_stream_summary(stream: dict[str, Any], runtime_input: dict[str, Any]) -> dict[str, Any]:
    stream_id = str(stream.get("stream_id", ""))
    counters = {
        key: value
        for key, value in stream.items()
        if key.endswith("_count") or key.endswith("_hz") or key in {"status", "quality", "issue_code"}
    }
    return {
        "stream_id": stream_id,
        "status": str(stream.get("status", "unknown")),
        "summary": raw_stream_text(stream),
        "counters": counters,
        "preview": preview_for_stream(stream_id, runtime_input),
    }


def module_output_summary(stream: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        key: stream[key]
        for key in MODULE_METRIC_FIELDS
        if key in stream and is_scalar(stream[key])
    }
    return {
        "stream_id": str(stream.get("stream_id", "")),
        "module_id": str(stream.get("module_id", "")),
        "status": str(stream.get("status", "unknown")),
        "input_stream_id": str(stream.get("input_stream_id", "")),
        "summary": module_output_text(stream),
        "metrics": metrics,
        "issue_code": stream.get("issue_code"),
    }


def raw_stream_text(stream: dict[str, Any]) -> str:
    stream_id = str(stream.get("stream_id", "stream"))
    if stream_id.endswith(".hr_rr"):
        return f"{stream.get('heart_rate_event_count', 0)} HR / {stream.get('rr_interval_count', 0)} RR"
    if stream_id.endswith(".acc"):
        return f"{stream.get('frame_count', stream.get('acc_frame_count', 0))} frames / {stream.get('sample_count', stream.get('acc_sample_count', 0))} samples"
    if stream_id.endswith(".ecg"):
        return f"{stream.get('frame_count', stream.get('ecg_frame_count', 0))} frames / {stream.get('sample_count', stream.get('ecg_sample_count', 0))} samples"
    return str(stream.get("status", "unknown"))


def module_output_text(stream: dict[str, Any]) -> str:
    for key, suffix in [
        ("ln_rmssd", "lnRMSSD"),
        ("ln_rmssd_gain", "gain"),
        ("normalized_score", "coherence"),
        ("breath_volume_01", "volume"),
        ("breathing_rate_bpm", "bpm"),
        ("amplitude_bpm", "bpm"),
    ]:
        if key in stream:
            return f"{float_or_zero(stream.get(key)):.3f} {suffix}"
    return str(stream.get("status", "unknown"))


def preview_for_stream(stream_id: str, runtime_input: dict[str, Any]) -> list[float]:
    if stream_id == "stream.polar_h10.hr_rr":
        return numeric_preview(dict_value(runtime_input.get("hr_rr")).get("rr_intervals_ms", []))
    if stream_id == "stream.polar_h10.acc":
        values: list[float] = []
        for frame in dict_value(runtime_input.get("raw_acc")).get("frames", []):
            if not isinstance(frame, dict):
                continue
            samples = frame.get("samples_mg", frame.get("samples", []))
            for sample in samples if isinstance(samples, list) else []:
                if isinstance(sample, dict):
                    values.append(float_or_zero(sample.get("z_mg", sample.get("z", 0.0))))
        return numeric_preview(values)
    return []


def time_series(runtime_input: dict[str, Any]) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    rr_intervals = numeric_series(dict_value(runtime_input.get("hr_rr")).get("rr_intervals_ms", []))
    if rr_intervals:
        series.append(series_doc(
            "series.polar_h10.hr_bpm",
            "stream.polar_h10.hr_rr",
            "HR",
            "bpm",
            "runtime_input.hr_rr.rr_intervals_ms",
            [60000.0 / value for value in rr_intervals if value > 0.0],
            sample_rate_hz=1.0,
        ))
        series.append(series_doc(
            "series.polar_h10.rr_interval_ms",
            "stream.polar_h10.hr_rr",
            "RR",
            "ms",
            "runtime_input.hr_rr.rr_intervals_ms",
            rr_intervals,
            sample_rate_hz=1.0,
        ))

    acc_values = acc_magnitude_values(runtime_input)
    if acc_values:
        series.append(series_doc(
            "series.polar_h10.acc_magnitude_mg",
            "stream.polar_h10.acc",
            "ACC magnitude",
            "mg",
            "runtime_input.raw_acc.frames.samples_mg",
            acc_values,
            sample_rate_hz=optional_float(dict_value(runtime_input.get("raw_acc")).get("sample_rate_hz")),
        ))

    ecg_values = ecg_sample_values(runtime_input)
    if ecg_values:
        series.append(series_doc(
            "series.polar_h10.ecg_uv",
            "stream.polar_h10.ecg",
            "ECG",
            "uV",
            "runtime_input.raw_ecg.frames.samples_uv",
            ecg_values,
            sample_rate_hz=optional_float(dict_value(runtime_input.get("raw_ecg")).get("sample_rate_hz")),
        ))

    breath_volume = breath_volume_values(runtime_input)
    if breath_volume:
        series.append(series_doc(
            "series.polar_h10.breath_volume_01",
            "stream.polar_h10.breath_volume",
            "Breath volume",
            "01",
            "runtime_input.breath_volume",
            breath_volume,
            sample_rate_hz=1.0,
        ))

    breath = dict_value(runtime_input.get("breath_dynamics"))
    breath_amplitudes = numeric_series(breath.get("breath_amplitudes_01", []))
    if breath_amplitudes:
        series.append(series_doc(
            "series.polar_h10.breath_amplitude_01",
            "stream.polar_h10.breath_dynamics",
            "Breath amplitude",
            "01",
            "runtime_input.breath_dynamics.breath_amplitudes_01",
            breath_amplitudes,
            sample_rate_hz=1.0,
        ))

    coherence_values = coherence_uniform_values(runtime_input)
    if coherence_values:
        series.append(series_doc(
            "series.polar_h10.coherence_uniform_rr_ms",
            "stream.polar_h10.coherence",
            "Coherence input",
            "ms",
            "runtime_input.coherence_uniform",
            coherence_values,
            sample_rate_hz=2.0,
        ))

    hrvb_values = hrvb_values_from_generator(runtime_input)
    if hrvb_values:
        series.append(series_doc(
            "series.polar_h10.hrvb_hr_bpm",
            "stream.polar_h10.hrvb_resonance_amplitude",
            "HRVB",
            "bpm",
            "runtime_input.hrvb_resonance_amplitude.generator",
            hrvb_values,
            sample_rate_hz=1.0,
        ))

    breath_intervals = numeric_series(breath.get("breath_intervals_s", []))
    if breath_intervals:
        series.append(series_doc(
            "series.polar_h10.breath_interval_s",
            "stream.polar_h10.breath_dynamics",
            "Breath interval",
            "s",
            "runtime_input.breath_dynamics.breath_intervals_s",
            breath_intervals,
            sample_rate_hz=1.0,
        ))

    return [doc for doc in series if doc["values"]]


def series_doc(
    series_id: str,
    stream_id: str,
    label: str,
    unit: str,
    source: str,
    values: list[float],
    *,
    sample_rate_hz: float | None,
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "series_id": series_id,
        "stream_id": stream_id,
        "label": label,
        "unit": unit,
        "source": source,
        "values": bounded_values(values),
    }
    if sample_rate_hz is not None:
        doc["sample_rate_hz"] = sample_rate_hz
    return doc


def acc_magnitude_values(runtime_input: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for frame in dict_value(runtime_input.get("raw_acc")).get("frames", []):
        if not isinstance(frame, dict):
            continue
        samples = frame.get("samples_mg", frame.get("samples", []))
        for sample in samples if isinstance(samples, list) else []:
            if not isinstance(sample, dict):
                continue
            x = float_or_zero(sample.get("x_mg", sample.get("x", 0.0)))
            y = float_or_zero(sample.get("y_mg", sample.get("y", 0.0)))
            z = float_or_zero(sample.get("z_mg", sample.get("z", 0.0)))
            values.append(math.sqrt(x * x + y * y + z * z))
    return bounded_values(values)


def ecg_sample_values(runtime_input: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for frame in dict_value(runtime_input.get("raw_ecg")).get("frames", []):
        if not isinstance(frame, dict):
            continue
        samples = frame.get("samples_uv", frame.get("samples", []))
        values.extend(numeric_series(samples))
    return bounded_values(values)


def breath_volume_values(runtime_input: dict[str, Any]) -> list[float]:
    breath = dict_value(runtime_input.get("breath_volume"))
    values = numeric_series(breath.get("calibration_projection", []))
    for key in ["previous_projection", "live_projection"]:
        if key in breath:
            values.append(float_or_zero(breath.get(key)))
    return bounded_values(values)


def coherence_uniform_values(runtime_input: dict[str, Any]) -> list[float]:
    coherence = dict_value(runtime_input.get("coherence_uniform"))
    components = [component for component in coherence.get("components", []) if isinstance(component, dict)]
    if not components:
        return []
    base_rr = float_or_zero(coherence.get("base_rr_ms", 1000.0))
    sample_count = min(MAX_SERIES_VALUES, max(64, max(int(float_or_zero(component.get("bin", 0))) for component in components) * 4))
    values: list[float] = []
    for index in range(sample_count):
        value = base_rr
        for component in components:
            bin_index = float_or_zero(component.get("bin", 0.0))
            amplitude = float_or_zero(component.get("amplitude_ms", 0.0))
            phase = float_or_zero(component.get("phase_rad", 0.0))
            value += amplitude * math.sin((2.0 * math.pi * bin_index * index / sample_count) + phase)
        values.append(value)
    return bounded_values(values)


def hrvb_values_from_generator(runtime_input: dict[str, Any]) -> list[float]:
    generator = dict_value(dict_value(runtime_input.get("hrvb_resonance_amplitude")).get("generator"))
    if not generator:
        return []
    sample_count = int(float_or_zero(generator.get("sample_count", 0)))
    if sample_count <= 0:
        return []
    sample_count = min(MAX_SERIES_VALUES, sample_count)
    mean_hr = float_or_zero(generator.get("mean_hr_bpm", 0.0))
    amplitude = float_or_zero(generator.get("amplitude_bpm", 0.0))
    frequency_hz = float_or_zero(generator.get("frequency_hz", 0.0))
    phase = float_or_zero(generator.get("phase_rad", 0.0))
    return [
        mean_hr + amplitude * math.sin((2.0 * math.pi * frequency_hz * index) + phase)
        for index in range(sample_count)
    ]


def numeric_series(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    return bounded_values([float_or_zero(value) for value in values])


def bounded_values(values: list[float]) -> list[float]:
    return [round(value, 4) for value in values[:MAX_SERIES_VALUES]]


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def numeric_preview(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    parsed = [float_or_zero(value) for value in values[:MAX_PREVIEW_VALUES]]
    return [round(value, 4) for value in parsed]


def collect_issues(
    evidence: dict[str, Any],
    graph_report: dict[str, Any],
    streams: list[dict[str, Any]],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for index, message in enumerate(evidence.get("errors", [])):
        if message:
            issues.append({"code": f"evidence.error.{index}", "message": str(message)})
    for issue in graph_report.get("issues", []):
        if isinstance(issue, dict):
            issues.append({
                "code": str(issue.get("code", "graph.issue")),
                "message": str(issue.get("message", issue.get("code", "graph issue"))),
            })
    for stream in streams:
        issue_code = stream.get("issue_code")
        if issue_code:
            issues.append({"code": str(issue_code), "message": str(stream.get("stream_id", "stream issue"))})
    return issues


def telemetry_commands() -> list[dict[str, Any]]:
    return [
        {
            "command": "run-live",
            "route": "hostessctl run-live",
            "state_changing": True,
            "authority": "Manifold command route through Hostess",
        },
        {
            "command": "run-replay",
            "route": "hostessctl run-replay",
            "state_changing": True,
            "authority": "package Rust runtime through Hostess",
        },
        {
            "command": "render-telemetry",
            "route": "hostessctl render-telemetry",
            "state_changing": False,
            "authority": "Hostess evidence export",
        },
    ]


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
