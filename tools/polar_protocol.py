"""Small Polar H10 protocol helpers used by Rusty Hostess T.

The helpers are intentionally platform-neutral: host apps own scanning,
permissions, pairing, connection lifecycle, storage, and evidence files.
"""

from __future__ import annotations

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


def stream_id_for_mode(mode: str) -> str:
    if mode == "hr_rr":
        return STREAM_HR_RR
    if mode == "ecg":
        return STREAM_ECG
    if mode == "acc":
        return STREAM_ACC
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


if __name__ == "__main__":
    unittest.main()
