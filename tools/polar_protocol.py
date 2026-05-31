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
    paper_ratio: float | None
    normalized_score: float | None
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
