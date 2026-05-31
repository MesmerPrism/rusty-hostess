"""Small Polar H10 protocol helpers used by Rusty Hostess T.

The helpers are intentionally platform-neutral: host apps own scanning,
permissions, pairing, connection lifecycle, storage, and evidence files.
"""

from __future__ import annotations

import math
import unittest
from dataclasses import dataclass


HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
CCCD_DESCRIPTOR_UUID = "00002902-0000-1000-8000-00805f9b34fb"

PMD_SERVICE_UUID = "fb005c80-02e7-f387-1cad-8acd2d8df0c8"
PMD_CONTROL_POINT_UUID = "fb005c81-02e7-f387-1cad-8acd2d8df0c8"
PMD_DATA_UUID = "fb005c82-02e7-f387-1cad-8acd2d8df0c8"

STREAM_HR_RR = "stream.polar_h10.hr_rr"
STREAM_ECG = "stream.polar_h10.ecg"
STREAM_ACC = "stream.polar_h10.acc"
STREAM_COHERENCE = "stream.polar_h10.coherence"
STREAM_HRV_WINDOW = "stream.polar_h10.hrv_window"
STREAM_RMSSD_GAIN = "stream.polar_h10.rmssd_gain"
STREAM_BREATH_VOLUME = "stream.polar_h10.breath_volume"
STREAM_BREATH_DYNAMICS = "stream.polar_h10.breath_dynamics"
STREAM_HRVB_RESONANCE_AMPLITUDE = "stream.polar_h10.hrvb_resonance_amplitude"

MODULE_HRV_WINDOW = "module.polar_h10.hrv_window"
MODULE_RMSSD_GAIN = "module.polar_h10.rmssd_gain"
MODULE_COHERENCE = "module.polar_h10.coherence"
MODULE_BREATH_VOLUME_FROM_ACC = "module.polar_h10.breath_volume_from_acc"
MODULE_BREATH_DYNAMICS = "module.polar_h10.breath_dynamics"
MODULE_HRVB_RESONANCE_AMPLITUDE = "module.polar_h10.hrvb_resonance_amplitude"

MODULE_OUTPUT_STREAMS = {
    MODULE_HRV_WINDOW: STREAM_HRV_WINDOW,
    MODULE_RMSSD_GAIN: STREAM_RMSSD_GAIN,
    MODULE_COHERENCE: STREAM_COHERENCE,
    MODULE_BREATH_VOLUME_FROM_ACC: STREAM_BREATH_VOLUME,
    MODULE_BREATH_DYNAMICS: STREAM_BREATH_DYNAMICS,
    MODULE_HRVB_RESONANCE_AMPLITUDE: STREAM_HRVB_RESONANCE_AMPLITUDE,
}

MODULE_ALIASES = {
    "hrv_window": MODULE_HRV_WINDOW,
    "rmssd_gain": MODULE_RMSSD_GAIN,
    "coherence": MODULE_COHERENCE,
    "breath_volume": MODULE_BREATH_VOLUME_FROM_ACC,
    "breath_volume_from_acc": MODULE_BREATH_VOLUME_FROM_ACC,
    "breath_dynamics": MODULE_BREATH_DYNAMICS,
    "hrvb_resonance_amplitude": MODULE_HRVB_RESONANCE_AMPLITUDE,
    MODULE_HRV_WINDOW: MODULE_HRV_WINDOW,
    MODULE_RMSSD_GAIN: MODULE_RMSSD_GAIN,
    MODULE_COHERENCE: MODULE_COHERENCE,
    MODULE_BREATH_VOLUME_FROM_ACC: MODULE_BREATH_VOLUME_FROM_ACC,
    MODULE_BREATH_DYNAMICS: MODULE_BREATH_DYNAMICS,
    MODULE_HRVB_RESONANCE_AMPLITUDE: MODULE_HRVB_RESONANCE_AMPLITUDE,
}

HR_DEPENDENT_MODULES = {
    MODULE_HRV_WINDOW,
    MODULE_RMSSD_GAIN,
    MODULE_COHERENCE,
    MODULE_HRVB_RESONANCE_AMPLITUDE,
}
ACC_DEPENDENT_MODULES = {
    MODULE_BREATH_VOLUME_FROM_ACC,
    MODULE_BREATH_DYNAMICS,
}

COHERENCE_SAMPLE_RATE_HZ = 2.0
COHERENCE_WINDOW_SECONDS = 64.0
COHERENCE_FFT_LENGTH = 128
COHERENCE_TOTAL_BAND_HZ = (0.0033, 0.4)
COHERENCE_PEAK_SEARCH_HZ = (0.04, 0.26)
COHERENCE_PEAK_HALF_WIDTH_HZ = 0.03

PMD_OPCODE_GET_SETTINGS = 0x01
PMD_OPCODE_START_STREAM = 0x02
PMD_OPCODE_STOP_STREAM = 0x03
PMD_RESPONSE_MARKER = 0xF0

PMD_MEASUREMENT_TYPE_ECG = 0x00
PMD_MEASUREMENT_TYPE_ACC = 0x02

PMD_SETTING_TYPE_SAMPLE_RATE = 0x00
PMD_SETTING_TYPE_RESOLUTION = 0x01
PMD_SETTING_TYPE_RANGE = 0x02

PMD_HEADER_SIZE = 10


@dataclass(frozen=True)
class HeartRateReading:
    bpm: int
    rr_intervals_ms: list[float]
    energy_expended: int | None


@dataclass(frozen=True)
class PmdControlResponse:
    op_code: int
    measurement_type: int
    error_code: int
    payload: bytes

    @property
    def success(self) -> bool:
        return self.error_code == 0


@dataclass(frozen=True)
class EcgFrame:
    sensor_timestamp_ns: int
    samples_microvolts: list[int]


@dataclass(frozen=True)
class AccSample:
    x_mg: int
    y_mg: int
    z_mg: int


@dataclass(frozen=True)
class AccFrame:
    sensor_timestamp_ns: int
    samples_mg: list[AccSample]


@dataclass(frozen=True)
class CoherenceResult:
    status: str
    issue_code: str | None
    input_rr_interval_count: int
    uniform_sample_count: int
    window_seconds: float
    sample_rate_hz: float
    peak_frequency_hz: float | None
    peak_band_power: float | None
    total_band_power: float | None
    remaining_power: float | None
    coherence_ratio: float | None
    coherence_ratio_squared: float | None
    normalized_peak_power: float | None
    paper_ratio: float | None
    normalized_score: float | None
    quality: str | None


@dataclass(frozen=True)
class HrvWindowResult:
    status: str
    issue_code: str | None
    input_rr_interval_count: int
    accepted_count: int
    rejected_count: int
    successive_difference_count: int
    mean_nn_ms: float | None
    mean_hr_bpm: float | None
    sdnn_ms: float | None
    rmssd_ms: float | None
    ln_rmssd: float | None
    pnn50: float | None
    sd1_ms: float | None
    quality: str | None


@dataclass(frozen=True)
class RmssdGainResult:
    status: str
    issue_code: str | None
    baseline_source: str
    baseline_window_count: int
    current_window_count: int
    baseline_rmssd_ms: float | None
    current_rmssd_ms: float | None
    rmssd_ratio: float | None
    ln_rmssd_gain: float | None
    quality: str | None


@dataclass(frozen=True)
class BreathProxySeries:
    status: str
    issue_code: str | None
    sample_count: int
    source_sample_rate_hz: float
    calibration_sample_count: int
    projection_axis: str | None
    lower_bound: float | None
    upper_bound: float | None
    times_seconds: list[float]
    values_01: list[float]
    confidence: float | None
    quality: str | None


@dataclass(frozen=True)
class BreathVolumeResult:
    status: str
    issue_code: str | None
    input_acc_sample_count: int
    source_sample_rate_hz: float
    calibration_sample_count: int
    projection_axis: str | None
    lower_bound: float | None
    upper_bound: float | None
    breath_volume_01: float | None
    phase: str | None
    confidence: float | None
    quality: str | None


@dataclass(frozen=True)
class BreathDynamicsResult:
    status: str
    issue_code: str | None
    input_breath_sample_count: int
    cycle_count: int
    mean_interval_s: float | None
    breathing_rate_bpm: float | None
    interval_sd_s: float | None
    interval_cv: float | None
    mean_amplitude_01: float | None
    amplitude_sd_01: float | None
    amplitude_cv: float | None
    complexity_status: str | None
    quality: str | None


@dataclass(frozen=True)
class HrvbResonanceAmplitudeResult:
    status: str
    issue_code: str | None
    input_rr_interval_count: int
    window_seconds: float
    sample_rate_hz: float
    amplitude_bpm: float | None
    mean_hr_bpm: float | None
    frequency_hz: float | None
    omega_rad_s: float | None
    phase_rad: float | None
    median_session_amplitude_bpm: float | None
    threshold_status: str | None
    quality: str | None


def decode_heart_rate_measurement(payload: bytes | bytearray) -> HeartRateReading:
    data = bytes(payload)
    if len(data) < 2:
        raise ValueError("Heart Rate Measurement payload is too short")

    flags = data[0]
    offset = 1
    if flags & 0x01:
        bpm = _read_u16_le(data, offset)
        offset += 2
    else:
        bpm = data[offset]
        offset += 1

    energy = None
    if flags & 0x08:
        energy = _read_u16_le(data, offset)
        offset += 2

    rr_intervals_ms: list[float] = []
    if flags & 0x10:
        while offset + 1 < len(data):
            rr_intervals_ms.append(_read_u16_le(data, offset) * 1000.0 / 1024.0)
            offset += 2

    return HeartRateReading(bpm=bpm, rr_intervals_ms=rr_intervals_ms, energy_expended=energy)


def build_get_settings_request(kind: str) -> bytes:
    return bytes([PMD_OPCODE_GET_SETTINGS, _measurement_type(kind)])


def build_stop_request(kind: str) -> bytes:
    return bytes([PMD_OPCODE_STOP_STREAM, _measurement_type(kind)])


def build_start_request(kind: str, *, acc_rate_hz: int = 200) -> bytes:
    if kind == "ecg":
        return bytes(
            [
                PMD_OPCODE_START_STREAM,
                PMD_MEASUREMENT_TYPE_ECG,
                PMD_SETTING_TYPE_SAMPLE_RATE,
                0x01,
                0x82,
                0x00,
                PMD_SETTING_TYPE_RESOLUTION,
                0x01,
                0x0E,
                0x00,
            ]
        )
    if kind == "acc":
        return bytes(
            [
                PMD_OPCODE_START_STREAM,
                PMD_MEASUREMENT_TYPE_ACC,
                PMD_SETTING_TYPE_RANGE,
                0x01,
                0x08,
                0x00,
                PMD_SETTING_TYPE_SAMPLE_RATE,
                0x01,
                acc_rate_hz & 0xFF,
                (acc_rate_hz >> 8) & 0xFF,
                PMD_SETTING_TYPE_RESOLUTION,
                0x01,
                0x10,
                0x00,
            ]
        )
    raise ValueError(f"unsupported PMD stream kind: {kind}")


def parse_control_response(payload: bytes | bytearray) -> PmdControlResponse:
    data = bytes(payload)
    if len(data) < 4 or data[0] != PMD_RESPONSE_MARKER:
        raise ValueError("bad PMD control response")
    return PmdControlResponse(
        op_code=data[1],
        measurement_type=data[2],
        error_code=data[3],
        payload=data[4:],
    )


def decode_ecg_frame(payload: bytes | bytearray) -> EcgFrame:
    data = bytes(payload)
    _validate_pmd_header(data, PMD_MEASUREMENT_TYPE_ECG)
    if data[9] != 0x00:
        raise ValueError(f"unsupported ECG frame type: {data[9]}")
    body = data[PMD_HEADER_SIZE:]
    if len(body) == 0 or len(body) % 3:
        raise ValueError("bad ECG PMD frame length")
    return EcgFrame(
        sensor_timestamp_ns=_read_u64_le(data, 1),
        samples_microvolts=[_read_i24_le(body[index : index + 3]) for index in range(0, len(body), 3)],
    )


def decode_acc_frame(payload: bytes | bytearray) -> AccFrame:
    data = bytes(payload)
    _validate_pmd_header(data, PMD_MEASUREMENT_TYPE_ACC)
    if data[9] != 0x01:
        raise ValueError(f"unsupported ACC frame type: {data[9]}")
    body = data[PMD_HEADER_SIZE:]
    if len(body) == 0 or len(body) % 6:
        raise ValueError("bad ACC PMD frame length")
    samples = []
    for index in range(0, len(body), 6):
        samples.append(
            AccSample(
                x_mg=_read_i16_le(body, index),
                y_mg=_read_i16_le(body, index + 2),
                z_mg=_read_i16_le(body, index + 4),
            )
        )
    return AccFrame(sensor_timestamp_ns=_read_u64_le(data, 1), samples_mg=samples)


def normalize_module_selection(values: list[str] | None) -> list[str]:
    modules: list[str] = []
    for value in values or []:
        for item in value.split(","):
            key = item.strip()
            if not key:
                continue
            module_id = MODULE_ALIASES.get(key)
            if module_id is None:
                raise ValueError(f"unknown module selection: {key}")
            if module_id not in modules:
                modules.append(module_id)
    if MODULE_RMSSD_GAIN in modules and MODULE_HRV_WINDOW not in modules:
        raise ValueError("module.polar_h10.rmssd_gain requires module.polar_h10.hrv_window")
    if MODULE_BREATH_DYNAMICS in modules and MODULE_BREATH_VOLUME_FROM_ACC not in modules:
        raise ValueError("module.polar_h10.breath_dynamics requires module.polar_h10.breath_volume_from_acc")
    return modules


def dependency_streams_for_modules(module_ids: list[str]) -> set[str]:
    streams: set[str] = set()
    if any(module_id in HR_DEPENDENT_MODULES for module_id in module_ids):
        streams.add(STREAM_HR_RR)
    if any(module_id in ACC_DEPENDENT_MODULES for module_id in module_ids):
        streams.add(STREAM_ACC)
    return streams


def compute_hrv_window(rr_intervals_ms: list[float]) -> HrvWindowResult:
    usable = _usable_rr(rr_intervals_ms)
    rejected = len(rr_intervals_ms) - len(usable)
    if len(usable) < 2:
        return _hrv_failure("issue.window_underfilled", len(rr_intervals_ms), len(usable), rejected)
    if rejected > 0:
        return _hrv_failure("issue.quality_low", len(rr_intervals_ms), len(usable), rejected)

    diffs = [usable[index] - usable[index - 1] for index in range(1, len(usable))]
    rmssd = math.sqrt(sum(diff * diff for diff in diffs) / len(diffs))
    mean_nn = sum(usable) / len(usable)
    sdnn = _sample_sd(usable)
    pnn50 = 100.0 * sum(1 for diff in diffs if abs(diff) > 50.0) / len(diffs)
    ln_rmssd = math.log(rmssd) if rmssd > 0.0 else None
    return HrvWindowResult(
        status="pass",
        issue_code=None,
        input_rr_interval_count=len(rr_intervals_ms),
        accepted_count=len(usable),
        rejected_count=rejected,
        successive_difference_count=len(diffs),
        mean_nn_ms=round(mean_nn, 6),
        mean_hr_bpm=round(60000.0 / mean_nn, 6) if mean_nn > 0.0 else None,
        sdnn_ms=round(sdnn, 6),
        rmssd_ms=round(rmssd, 6),
        ln_rmssd=round(ln_rmssd, 6) if ln_rmssd is not None else None,
        pnn50=round(pnn50, 6),
        sd1_ms=round(rmssd / math.sqrt(2.0), 6),
        quality="stable",
    )


def compute_rmssd_gain(rr_intervals_ms: list[float]) -> RmssdGainResult:
    usable = _usable_rr(rr_intervals_ms)
    if len(usable) < 12:
        return _rmssd_gain_failure("issue.baseline_underfilled", 0, 0)
    window_count = min(30, max(6, len(usable) // 3))
    if len(usable) < window_count * 2:
        return _rmssd_gain_failure("issue.baseline_underfilled", window_count, len(usable) - window_count)
    baseline = usable[:window_count]
    current = usable[-window_count:]
    baseline_rmssd = _rmssd(baseline)
    current_rmssd = _rmssd(current)
    if baseline_rmssd is None or current_rmssd is None:
        return _rmssd_gain_failure("issue.baseline_underfilled", len(baseline), len(current))
    if baseline_rmssd <= 0.0:
        return _rmssd_gain_failure("issue.baseline_invalid", len(baseline), len(current))
    ratio = current_rmssd / baseline_rmssd
    return RmssdGainResult(
        status="pass",
        issue_code=None,
        baseline_source="same_run_initial_segment",
        baseline_window_count=len(baseline),
        current_window_count=len(current),
        baseline_rmssd_ms=round(baseline_rmssd, 6),
        current_rmssd_ms=round(current_rmssd, 6),
        rmssd_ratio=round(ratio, 6),
        ln_rmssd_gain=round(math.log(ratio), 6) if ratio > 0.0 else None,
        quality="stable",
    )


def compute_breath_volume(acc_frames: list[AccFrame], *, acc_rate_hz: int = 200) -> BreathVolumeResult:
    series = _breath_proxy_series(acc_frames, acc_rate_hz=acc_rate_hz)
    if series.status != "pass":
        return BreathVolumeResult(
            status="fail",
            issue_code=series.issue_code,
            input_acc_sample_count=series.sample_count,
            source_sample_rate_hz=series.source_sample_rate_hz,
            calibration_sample_count=series.calibration_sample_count,
            projection_axis=series.projection_axis,
            lower_bound=series.lower_bound,
            upper_bound=series.upper_bound,
            breath_volume_01=None,
            phase=None,
            confidence=series.confidence,
            quality=series.quality,
        )
    latest = series.values_01[-1]
    previous = series.values_01[-2] if len(series.values_01) >= 2 else latest
    return BreathVolumeResult(
        status="pass",
        issue_code=None,
        input_acc_sample_count=series.sample_count,
        source_sample_rate_hz=series.source_sample_rate_hz,
        calibration_sample_count=series.calibration_sample_count,
        projection_axis=series.projection_axis,
        lower_bound=series.lower_bound,
        upper_bound=series.upper_bound,
        breath_volume_01=round(latest, 6),
        phase="inhale" if latest >= previous else "exhale",
        confidence=series.confidence,
        quality=series.quality,
    )


def compute_breath_dynamics(acc_frames: list[AccFrame], *, acc_rate_hz: int = 200) -> BreathDynamicsResult:
    series = _breath_proxy_series(acc_frames, acc_rate_hz=acc_rate_hz)
    if series.status != "pass":
        return _breath_dynamics_failure(series.issue_code or "issue.input_stream_missing", series.sample_count)
    downsampled = _downsample_series(series.times_seconds, series.values_01, 10.0)
    if len(downsampled) < 30:
        return _breath_dynamics_failure("issue.window_underfilled", series.sample_count)
    times = [item[0] for item in downsampled]
    values = _moving_average([item[1] for item in downsampled], 5)
    midpoint = _median(values)
    crossings: list[float] = []
    for index in range(1, len(values)):
        left = values[index - 1] - midpoint
        right = values[index] - midpoint
        if left < 0.0 <= right:
            span = right - left
            fraction = 0.0 if span == 0.0 else -left / span
            crossings.append(times[index - 1] + (times[index] - times[index - 1]) * fraction)
    intervals = [
        crossings[index] - crossings[index - 1]
        for index in range(1, len(crossings))
        if 1.5 <= crossings[index] - crossings[index - 1] <= 12.0
    ]
    amplitudes: list[float] = []
    for start, end in zip(crossings, crossings[1:]):
        window = [value for time_s, value in zip(times, values) if start <= time_s <= end]
        if window:
            amplitudes.append(max(window) - min(window))
    if len(intervals) < 2 or len(amplitudes) < 2:
        return _breath_dynamics_failure("issue.window_underfilled", series.sample_count)

    mean_interval = sum(intervals) / len(intervals)
    interval_sd = _sample_sd(intervals)
    mean_amplitude = sum(amplitudes) / len(amplitudes)
    amplitude_sd = _sample_sd(amplitudes)
    return BreathDynamicsResult(
        status="pass",
        issue_code=None,
        input_breath_sample_count=series.sample_count,
        cycle_count=len(intervals),
        mean_interval_s=round(mean_interval, 6),
        breathing_rate_bpm=round(60.0 / mean_interval, 6) if mean_interval > 0.0 else None,
        interval_sd_s=round(interval_sd, 6),
        interval_cv=round(interval_sd / mean_interval, 6) if mean_interval > 0.0 else None,
        mean_amplitude_01=round(mean_amplitude, 6),
        amplitude_sd_01=round(amplitude_sd, 6),
        amplitude_cv=round(amplitude_sd / mean_amplitude, 6) if mean_amplitude > 0.0 else None,
        complexity_status="underfilled",
        quality="stable",
    )


def compute_hrvb_resonance_amplitude(rr_intervals_ms: list[float]) -> HrvbResonanceAmplitudeResult:
    usable = _usable_rr(rr_intervals_ms)
    if len(usable) < 30:
        return _hrvb_failure("issue.window_underfilled", len(usable))
    elapsed = 0.0
    samples: list[tuple[float, float]] = []
    for rr_ms in usable:
        elapsed += rr_ms / 1000.0
        samples.append((elapsed, 60000.0 / rr_ms))
    if elapsed < 30.0:
        return _hrvb_failure("issue.window_underfilled", len(usable))
    window_start = elapsed - 30.0
    window = [(time_s - window_start, hr) for time_s, hr in samples if time_s >= window_start]
    if len(window) < 20:
        return _hrvb_failure("issue.window_underfilled", len(usable))
    best_frequency = None
    best_amplitude = -1.0
    best_phase = None
    for step in range(0, 41):
        frequency = 0.08 + step * 0.001
        omega = 2.0 * math.pi * frequency
        sin_projection = 0.0
        cos_projection = 0.0
        mean_hr = sum(hr for _, hr in window) / len(window)
        for time_s, hr in window:
            centered = hr - mean_hr
            sin_projection += centered * math.sin(omega * time_s)
            cos_projection += centered * math.cos(omega * time_s)
        sin_projection *= 2.0 / len(window)
        cos_projection *= 2.0 / len(window)
        amplitude = math.sqrt((sin_projection * sin_projection) + (cos_projection * cos_projection))
        if amplitude > best_amplitude:
            best_amplitude = amplitude
            best_frequency = frequency
            best_phase = math.atan2(cos_projection, sin_projection)
    if best_frequency is None or best_phase is None:
        return _hrvb_failure("issue.fit_not_converged", len(usable))
    mean_hr = sum(hr for _, hr in window) / len(window)
    threshold_status = "above_source_threshold" if best_amplitude >= 2.0 else "below_source_threshold"
    return HrvbResonanceAmplitudeResult(
        status="pass",
        issue_code=None,
        input_rr_interval_count=len(usable),
        window_seconds=30.0,
        sample_rate_hz=1.0,
        amplitude_bpm=round(best_amplitude, 6),
        mean_hr_bpm=round(mean_hr, 6),
        frequency_hz=round(best_frequency, 6),
        omega_rad_s=round(2.0 * math.pi * best_frequency, 6),
        phase_rad=round(best_phase, 6),
        median_session_amplitude_bpm=round(best_amplitude, 6),
        threshold_status=threshold_status,
        quality="stable",
    )


def compute_coherence(rr_intervals_ms: list[float]) -> CoherenceResult:
    usable_rr = [value for value in rr_intervals_ms if 300.0 <= value <= 2000.0]
    if len(usable_rr) < 12:
        return _coherence_failure("issue.window_underfilled", len(usable_rr), 0)

    beat_times: list[float] = []
    elapsed = 0.0
    for rr_ms in usable_rr:
        elapsed += rr_ms / 1000.0
        beat_times.append(elapsed)

    if elapsed < COHERENCE_WINDOW_SECONDS:
        return _coherence_failure("issue.window_underfilled", len(usable_rr), 0)

    window_start = elapsed - COHERENCE_WINDOW_SECONDS
    if beat_times[0] > window_start:
        return _coherence_failure("issue.window_underfilled", len(usable_rr), 0)

    samples: list[float] = []
    beat_index = 0
    for sample_index in range(COHERENCE_FFT_LENGTH):
        sample_time = window_start + (sample_index / COHERENCE_SAMPLE_RATE_HZ)
        while beat_index + 1 < len(beat_times) and beat_times[beat_index + 1] < sample_time:
            beat_index += 1
        if beat_index + 1 >= len(beat_times):
            break
        left_time = beat_times[beat_index]
        right_time = beat_times[beat_index + 1]
        left_rr = usable_rr[beat_index]
        right_rr = usable_rr[beat_index + 1]
        if right_time <= left_time:
            samples.append(left_rr)
        else:
            fraction = (sample_time - left_time) / (right_time - left_time)
            samples.append(left_rr + (right_rr - left_rr) * fraction)

    if len(samples) < COHERENCE_FFT_LENGTH:
        return _coherence_failure("issue.window_underfilled", len(usable_rr), len(samples))

    return compute_coherence_uniform(samples, input_rr_interval_count=len(usable_rr))


def compute_coherence_uniform(
    samples_ms: list[float], *, input_rr_interval_count: int | None = None
) -> CoherenceResult:
    if len(samples_ms) < COHERENCE_FFT_LENGTH:
        return _coherence_failure(
            "issue.window_underfilled",
            len(samples_ms) if input_rr_interval_count is None else input_rr_interval_count,
            len(samples_ms),
        )
    samples = samples_ms[-COHERENCE_FFT_LENGTH:]
    mean = sum(samples) / COHERENCE_FFT_LENGTH
    detrended = [value - mean for value in samples]
    powers = _dft_powers(detrended)
    total_band_power = sum(
        power for _, frequency, power in powers if _in_band(frequency, COHERENCE_TOTAL_BAND_HZ)
    )
    peak_candidates = [
        (bin_index, frequency, power)
        for bin_index, frequency, power in powers
        if _in_band(frequency, COHERENCE_PEAK_SEARCH_HZ)
    ]
    if total_band_power <= 0.0 or not peak_candidates:
        return _coherence_failure(
            "issue.quality_low",
            len(samples) if input_rr_interval_count is None else input_rr_interval_count,
            len(samples),
        )

    max_peak_power = max(power for _, _, power in peak_candidates)
    peak_bin, peak_frequency_hz, _ = min(
        (
            (bin_index, frequency, power)
            for bin_index, frequency, power in peak_candidates
            if abs(power - max_peak_power) <= 0.000000000001
        ),
        key=lambda item: item[0],
    )
    if peak_bin <= 0:
        return _coherence_failure("issue.quality_low", len(samples), len(samples))

    peak_band_power = sum(
        power
        for _, frequency, power in powers
        if _in_band(frequency, COHERENCE_TOTAL_BAND_HZ)
        and abs(frequency - peak_frequency_hz) <= COHERENCE_PEAK_HALF_WIDTH_HZ + 0.000000000001
    )
    remaining_power = total_band_power - peak_band_power
    if remaining_power <= 0.0:
        paper_ratio = 1000000.0
        normalized_score = 1.0
    else:
        paper_ratio = peak_band_power / remaining_power
        normalized_score = paper_ratio / (paper_ratio + 1.0)
    coherence_ratio_squared = paper_ratio * paper_ratio
    normalized_peak_power = peak_band_power / total_band_power if total_band_power > 0.0 else 0.0

    return CoherenceResult(
        status="pass",
        issue_code=None,
        input_rr_interval_count=len(samples) if input_rr_interval_count is None else input_rr_interval_count,
        uniform_sample_count=len(samples),
        window_seconds=COHERENCE_WINDOW_SECONDS,
        sample_rate_hz=COHERENCE_SAMPLE_RATE_HZ,
        peak_frequency_hz=round(peak_frequency_hz, 6),
        peak_band_power=round(peak_band_power, 6),
        total_band_power=round(total_band_power, 6),
        remaining_power=round(remaining_power, 6),
        coherence_ratio=round(paper_ratio, 6) if math.isfinite(paper_ratio) else paper_ratio,
        coherence_ratio_squared=round(coherence_ratio_squared, 6)
        if math.isfinite(coherence_ratio_squared)
        else coherence_ratio_squared,
        normalized_peak_power=round(normalized_peak_power, 6),
        paper_ratio=round(paper_ratio, 6) if math.isfinite(paper_ratio) else paper_ratio,
        normalized_score=round(normalized_score, 6),
        quality="stable" if paper_ratio >= 2.0 else "distributed",
    )


def stream_id_for_mode(mode: str) -> str:
    if mode == "hr_rr":
        return STREAM_HR_RR
    if mode == "ecg":
        return STREAM_ECG
    if mode == "acc":
        return STREAM_ACC
    if mode == "coherence":
        return STREAM_COHERENCE
    raise ValueError(f"unknown capture mode: {mode}")


def _measurement_type(kind: str) -> int:
    if kind == "ecg":
        return PMD_MEASUREMENT_TYPE_ECG
    if kind == "acc":
        return PMD_MEASUREMENT_TYPE_ACC
    raise ValueError(f"unsupported PMD stream kind: {kind}")


def _usable_rr(rr_intervals_ms: list[float]) -> list[float]:
    return [value for value in rr_intervals_ms if 300.0 <= value <= 2000.0]


def _rmssd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    diffs = [values[index] - values[index - 1] for index in range(1, len(values))]
    return math.sqrt(sum(diff * diff for diff in diffs) / len(diffs))


def _sample_sd(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) * (value - mean) for value in values) / (len(values) - 1)
    return math.sqrt(max(0.0, variance))


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, fraction)) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _breath_proxy_series(acc_frames: list[AccFrame], *, acc_rate_hz: int) -> BreathProxySeries:
    samples: list[tuple[float, float, float, float]] = []
    sample_period = 1.0 / max(1, acc_rate_hz)
    for frame in acc_frames:
        frame_start = frame.sensor_timestamp_ns / 1_000_000_000.0
        for index, sample in enumerate(frame.samples_mg):
            samples.append(
                (
                    frame_start + index * sample_period,
                    float(sample.x_mg),
                    float(sample.y_mg),
                    float(sample.z_mg),
                )
            )
    if len(samples) < max(20, acc_rate_hz // 2):
        return _breath_series_failure("issue.calibration_underfilled", len(samples), float(acc_rate_hz))

    first_time = samples[0][0]
    times = [sample[0] - first_time for sample in samples]
    axes = {
        "x": [sample[1] for sample in samples],
        "y": [sample[2] for sample in samples],
        "z": [sample[3] for sample in samples],
    }
    best_axis = None
    best_values: list[float] = []
    best_span = -1.0
    for axis, values in axes.items():
        span = _quantile(values, 0.95) - _quantile(values, 0.05)
        if span > best_span:
            best_axis = axis
            best_values = values
            best_span = span
    lower = _quantile(best_values, 0.05)
    upper = _quantile(best_values, 0.95)
    if upper - lower <= 0.000001:
        return _breath_series_failure("issue.calibration_invalid", len(samples), float(acc_rate_hz))
    normalized = [_clamp((value - lower) / (upper - lower), 0.0, 1.0) for value in best_values]
    confidence = _clamp((upper - lower) / 80.0, 0.0, 1.0)
    return BreathProxySeries(
        status="pass",
        issue_code=None,
        sample_count=len(samples),
        source_sample_rate_hz=float(acc_rate_hz),
        calibration_sample_count=len(samples),
        projection_axis=best_axis,
        lower_bound=round(lower, 6),
        upper_bound=round(upper, 6),
        times_seconds=times,
        values_01=normalized,
        confidence=round(confidence, 6),
        quality="stable" if confidence >= 0.2 else "low_motion",
    )


def _downsample_series(times: list[float], values: list[float], rate_hz: float) -> list[tuple[float, float]]:
    if not times or not values:
        return []
    buckets: dict[int, list[float]] = {}
    for time_s, value in zip(times, values):
        buckets.setdefault(int(time_s * rate_hz), []).append(value)
    return [
        (bucket / rate_hz, sum(bucket_values) / len(bucket_values))
        for bucket, bucket_values in sorted(buckets.items())
        if bucket_values
    ]


def _moving_average(values: list[float], radius: int) -> list[float]:
    smoothed: list[float] = []
    for index in range(len(values)):
        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        window = values[start:end]
        smoothed.append(sum(window) / len(window))
    return smoothed


def _hrv_failure(
    issue_code: str, input_count: int, accepted_count: int, rejected_count: int
) -> HrvWindowResult:
    return HrvWindowResult(
        status="fail",
        issue_code=issue_code,
        input_rr_interval_count=input_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        successive_difference_count=max(0, accepted_count - 1),
        mean_nn_ms=None,
        mean_hr_bpm=None,
        sdnn_ms=None,
        rmssd_ms=None,
        ln_rmssd=None,
        pnn50=None,
        sd1_ms=None,
        quality=None,
    )


def _rmssd_gain_failure(issue_code: str, baseline_count: int, current_count: int) -> RmssdGainResult:
    return RmssdGainResult(
        status="fail",
        issue_code=issue_code,
        baseline_source="same_run_initial_segment",
        baseline_window_count=baseline_count,
        current_window_count=current_count,
        baseline_rmssd_ms=None,
        current_rmssd_ms=None,
        rmssd_ratio=None,
        ln_rmssd_gain=None,
        quality=None,
    )


def _breath_series_failure(issue_code: str, sample_count: int, sample_rate: float) -> BreathProxySeries:
    return BreathProxySeries(
        status="fail",
        issue_code=issue_code,
        sample_count=sample_count,
        source_sample_rate_hz=sample_rate,
        calibration_sample_count=sample_count,
        projection_axis=None,
        lower_bound=None,
        upper_bound=None,
        times_seconds=[],
        values_01=[],
        confidence=None,
        quality=None,
    )


def _breath_dynamics_failure(issue_code: str, input_count: int) -> BreathDynamicsResult:
    return BreathDynamicsResult(
        status="fail",
        issue_code=issue_code,
        input_breath_sample_count=input_count,
        cycle_count=0,
        mean_interval_s=None,
        breathing_rate_bpm=None,
        interval_sd_s=None,
        interval_cv=None,
        mean_amplitude_01=None,
        amplitude_sd_01=None,
        amplitude_cv=None,
        complexity_status=None,
        quality=None,
    )


def _hrvb_failure(issue_code: str, input_count: int) -> HrvbResonanceAmplitudeResult:
    return HrvbResonanceAmplitudeResult(
        status="fail",
        issue_code=issue_code,
        input_rr_interval_count=input_count,
        window_seconds=30.0,
        sample_rate_hz=1.0,
        amplitude_bpm=None,
        mean_hr_bpm=None,
        frequency_hz=None,
        omega_rad_s=None,
        phase_rad=None,
        median_session_amplitude_bpm=None,
        threshold_status=None,
        quality=None,
    )


def _validate_pmd_header(data: bytes, expected_type: int) -> None:
    if len(data) < PMD_HEADER_SIZE:
        raise ValueError("PMD frame is too short")
    if data[0] != expected_type:
        raise ValueError(f"unexpected PMD measurement type: {data[0]}")


def _read_u16_le(data: bytes, offset: int) -> int:
    if offset + 1 >= len(data):
        raise ValueError("payload is too short for u16")
    return data[offset] | (data[offset + 1] << 8)


def _read_i16_le(data: bytes, offset: int) -> int:
    value = _read_u16_le(data, offset)
    return value - 0x10000 if value & 0x8000 else value


def _read_u64_le(data: bytes, offset: int) -> int:
    if offset + 7 >= len(data):
        raise ValueError("payload is too short for u64")
    value = 0
    for shift, byte in enumerate(data[offset : offset + 8]):
        value |= byte << (shift * 8)
    return value


def _read_i24_le(data: bytes) -> int:
    if len(data) != 3:
        raise ValueError("i24 expects exactly 3 bytes")
    value = data[0] | (data[1] << 8) | (data[2] << 16)
    return value | ~0xFFFFFF if value & 0x800000 else value


def _coherence_failure(
    issue_code: str, input_rr_interval_count: int, uniform_sample_count: int
) -> CoherenceResult:
    return CoherenceResult(
        status="fail",
        issue_code=issue_code,
        input_rr_interval_count=input_rr_interval_count,
        uniform_sample_count=uniform_sample_count,
        window_seconds=COHERENCE_WINDOW_SECONDS,
        sample_rate_hz=COHERENCE_SAMPLE_RATE_HZ,
        peak_frequency_hz=None,
        peak_band_power=None,
        total_band_power=None,
        remaining_power=None,
        coherence_ratio=None,
        coherence_ratio_squared=None,
        normalized_peak_power=None,
        paper_ratio=None,
        normalized_score=None,
        quality=None,
    )


def _dft_powers(samples: list[float]) -> list[tuple[int, float, float]]:
    powers: list[tuple[int, float, float]] = []
    sample_count = len(samples)
    for bin_index in range(1, (sample_count // 2) + 1):
        real = 0.0
        imaginary = 0.0
        for sample_index, sample in enumerate(samples):
            angle = -2.0 * math.pi * bin_index * sample_index / sample_count
            real += sample * math.cos(angle)
            imaginary += sample * math.sin(angle)
        frequency = bin_index * COHERENCE_SAMPLE_RATE_HZ / sample_count
        power = ((real * real) + (imaginary * imaginary)) / (sample_count * sample_count)
        powers.append((bin_index, frequency, power))
    return powers


def _in_band(frequency: float, band: tuple[float, float]) -> bool:
    return band[0] <= frequency <= band[1]


class ProtocolTests(unittest.TestCase):
    def test_decodes_heart_rate_and_rr(self) -> None:
        reading = decode_heart_rate_measurement(bytes([0x10, 60, 0x20, 0x03, 0x00, 0x04]))
        self.assertEqual(reading.bpm, 60)
        self.assertEqual(reading.rr_intervals_ms, [781.25, 1000.0])

    def test_builds_pmd_commands(self) -> None:
        self.assertEqual(build_get_settings_request("ecg"), bytes([0x01, 0x00]))
        self.assertEqual(build_get_settings_request("acc"), bytes([0x01, 0x02]))
        self.assertEqual(
            build_start_request("ecg"),
            bytes([0x02, 0x00, 0x00, 0x01, 0x82, 0x00, 0x01, 0x01, 0x0E, 0x00]),
        )
        self.assertEqual(
            build_start_request("acc"),
            bytes([0x02, 0x02, 0x02, 0x01, 0x08, 0x00, 0x00, 0x01, 0xC8, 0x00, 0x01, 0x01, 0x10, 0x00]),
        )

    def test_decodes_ecg(self) -> None:
        frame = decode_ecg_frame(bytes([0x00, 1, 0, 0, 0, 0, 0, 0, 0, 0x00, 1, 0, 0, 0xFF, 0xFF, 0xFF]))
        self.assertEqual(frame.sensor_timestamp_ns, 1)
        self.assertEqual(frame.samples_microvolts, [1, -1])

    def test_decodes_acc(self) -> None:
        frame = decode_acc_frame(bytes([0x02, 2, 0, 0, 0, 0, 0, 0, 0, 0x01, 1, 0, 0xFE, 0xFF, 0x10, 0x27]))
        self.assertEqual(frame.sensor_timestamp_ns, 2)
        self.assertEqual(frame.samples_mg, [AccSample(1, -2, 10000)])

    def test_computes_coherence_uniform_golden(self) -> None:
        samples = [
            1000.0
            + 50.0 * math.sin(2.0 * math.pi * 6.0 * index / 128.0)
            + 10.0 * math.sin(2.0 * math.pi * 18.0 * index / 128.0)
            + 5.0 * math.sin(2.0 * math.pi * 22.0 * index / 128.0)
            for index in range(128)
        ]
        result = compute_coherence_uniform(samples, input_rr_interval_count=72)
        self.assertEqual(result.status, "pass")
        self.assertAlmostEqual(result.peak_frequency_hz or 0.0, 0.09375, places=6)
        self.assertAlmostEqual(result.paper_ratio or 0.0, 20.0, places=6)
        self.assertAlmostEqual(result.normalized_score or 0.0, 0.952381, places=6)
        self.assertEqual(result.quality, "stable")

    def test_rejects_underfilled_coherence_window(self) -> None:
        result = compute_coherence([1000.0] * 20)
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.issue_code, "issue.window_underfilled")


if __name__ == "__main__":
    unittest.main()
