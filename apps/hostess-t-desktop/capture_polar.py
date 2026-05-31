"""Desktop live capture for Rusty Hostess T and the Manifold Polar package."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools import polar_protocol as polar  # noqa: E402


try:
    from bleak import BleakClient, BleakScanner
except ImportError as error:  # pragma: no cover - exercised by operator preflight
    raise SystemExit(
        "Install desktop requirements first: python -m pip install -r apps/hostess-t-desktop/requirements.txt"
    ) from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=["hr_rr", "ecg", "acc", "coherence"], required=True)
    parser.add_argument("--device-address")
    parser.add_argument("--device-name-prefix", default="Polar H10")
    parser.add_argument("--duration-seconds", type=float, default=10.0)
    parser.add_argument("--acc-rate", type=int, default=200)
    args = parser.parse_args()

    evidence = asyncio.run(capture(args))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["status"] == "pass" else 2


async def capture(args: argparse.Namespace) -> dict[str, Any]:
    package = package_snapshot(args.packages_root)
    started_utc = datetime.now(UTC)
    errors: list[str] = []
    control_responses: list[dict[str, Any]] = []
    hr_events: list[tuple[int, polar.HeartRateReading]] = []
    ecg_frames: list[tuple[int, polar.EcgFrame]] = []
    acc_frames: list[tuple[int, polar.AccFrame]] = []
    malformed_frames = 0
    command_status: list[dict[str, Any]] = []

    device = await find_device(args.device_address, args.device_name_prefix)
    if device is None:
        return failure_evidence(args, package, started_utc, ["device not found"])

    async with BleakClient(device, timeout=20.0) as client:
        if not client.is_connected:
            return failure_evidence(args, package, started_utc, ["connection failed"])

        def on_hr(_: Any, data: bytearray) -> None:
            nonlocal malformed_frames
            try:
                hr_events.append((time.time_ns(), polar.decode_heart_rate_measurement(data)))
            except ValueError:
                malformed_frames += 1

        def on_control(_: Any, data: bytearray) -> None:
            try:
                response = polar.parse_control_response(data)
                control_responses.append(
                    {
                        "op_code": response.op_code,
                        "measurement_type": response.measurement_type,
                        "error_code": response.error_code,
                        "success": response.success,
                    }
                )
            except ValueError as error:
                errors.append(f"bad control response: {error}")

        def on_pmd_data(_: Any, data: bytearray) -> None:
            nonlocal malformed_frames
            try:
                if args.mode == "ecg":
                    ecg_frames.append((time.time_ns(), polar.decode_ecg_frame(data)))
                elif args.mode == "acc":
                    acc_frames.append((time.time_ns(), polar.decode_acc_frame(data)))
            except ValueError:
                malformed_frames += 1

        if args.mode in {"hr_rr", "coherence"}:
            await client.start_notify(polar.HEART_RATE_MEASUREMENT_UUID, on_hr)
        else:
            await client.start_notify(polar.PMD_CONTROL_POINT_UUID, on_control)
            await client.start_notify(polar.PMD_DATA_UUID, on_pmd_data)
            kind = "ecg" if args.mode == "ecg" else "acc"
            await write_command(client, command_status, "get_settings", polar.build_get_settings_request(kind))
            await asyncio.sleep(0.4)
            await write_command(
                client,
                command_status,
                "start_stream",
                polar.build_start_request(kind, acc_rate_hz=args.acc_rate),
            )

        await asyncio.sleep(args.duration_seconds)

        if args.mode in {"hr_rr", "coherence"}:
            await client.stop_notify(polar.HEART_RATE_MEASUREMENT_UUID)
        else:
            kind = "ecg" if args.mode == "ecg" else "acc"
            await write_command(client, command_status, "stop_stream", polar.build_stop_request(kind))
            await asyncio.sleep(0.3)
            await client.stop_notify(polar.PMD_DATA_UUID)
            await client.stop_notify(polar.PMD_CONTROL_POINT_UUID)

    ended_utc = datetime.now(UTC)
    stream = stream_result(args.mode, hr_events, ecg_frames, acc_frames, malformed_frames)
    status = "pass" if stream["status"] == "pass" and not errors else "fail"
    return {
        "$schema": "rusty.manifold.live_capture_evidence.v1",
        "status": status,
        "host_profile": "desktop",
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": ended_utc.isoformat(),
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.desktop",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "capture": {
            "mode": args.mode,
            "duration_seconds": args.duration_seconds,
            "device_selector": sanitize_selector(args.device_address, args.device_name_prefix),
        },
        "commands": command_status,
        "control_responses": control_responses,
        "streams": [stream],
        "errors": errors,
    }


async def write_command(client: Any, command_status: list[dict[str, Any]], label: str, payload: bytes) -> None:
    started_ns = time.time_ns()
    await client.write_gatt_char(polar.PMD_CONTROL_POINT_UUID, payload, response=True)
    command_status.append(
        {
            "command": label,
            "status": "acknowledged",
            "host_time_unix_ns": started_ns,
            "payload_length": len(payload),
        }
    )


async def find_device(address: str | None, name_prefix: str) -> Any | None:
    if address:
        device = await BleakScanner.find_device_by_address(address, timeout=15.0)
        if device is not None:
            return device
    devices = await BleakScanner.discover(timeout=15.0)
    for device in devices:
        name = getattr(device, "name", None) or ""
        if name.startswith(name_prefix):
            return device
    return None


def stream_result(
    mode: str,
    hr_events: list[tuple[int, polar.HeartRateReading]],
    ecg_frames: list[tuple[int, polar.EcgFrame]],
    acc_frames: list[tuple[int, polar.AccFrame]],
    malformed_frames: int,
) -> dict[str, Any]:
    if mode == "hr_rr":
        rr_count = sum(len(reading.rr_intervals_ms) for _, reading in hr_events)
        return {
            "stream_id": polar.STREAM_HR_RR,
            "status": "pass" if hr_events and rr_count > 0 else "fail",
            "heart_rate_event_count": len(hr_events),
            "rr_interval_count": rr_count,
            "latest_bpm": hr_events[-1][1].bpm if hr_events else None,
            "latest_rr_ms": hr_events[-1][1].rr_intervals_ms[-3:] if hr_events and hr_events[-1][1].rr_intervals_ms else [],
            "host_notification_rate_hz": host_rate([timestamp for timestamp, _ in hr_events]),
            "malformed_frame_count": malformed_frames,
        }
    if mode == "coherence":
        rr_intervals = [
            rr_ms
            for _, reading in hr_events
            for rr_ms in reading.rr_intervals_ms
        ]
        coherence = polar.compute_coherence(rr_intervals)
        return {
            "stream_id": polar.STREAM_COHERENCE,
            "status": coherence.status,
            "input_stream_id": polar.STREAM_HR_RR,
            "method": "spectral_ratio_v1",
            "heart_rate_event_count": len(hr_events),
            "input_rr_interval_count": coherence.input_rr_interval_count,
            "uniform_sample_count": coherence.uniform_sample_count,
            "window_seconds": coherence.window_seconds,
            "sample_rate_hz": coherence.sample_rate_hz,
            "peak_frequency_hz": coherence.peak_frequency_hz,
            "peak_band_power": coherence.peak_band_power,
            "total_band_power": coherence.total_band_power,
            "paper_ratio": coherence.paper_ratio,
            "normalized_score": coherence.normalized_score,
            "quality": coherence.quality,
            "issue_code": coherence.issue_code,
            "host_notification_rate_hz": host_rate([timestamp for timestamp, _ in hr_events]),
            "malformed_frame_count": malformed_frames,
        }
    if mode == "ecg":
        sample_count = sum(len(frame.samples_microvolts) for _, frame in ecg_frames)
        return {
            "stream_id": polar.STREAM_ECG,
            "status": "pass" if sample_count > 0 else "fail",
            "frame_count": len(ecg_frames),
            "decoded_sample_count": sample_count,
            "sensor_sample_rate_hz": sensor_rate([(frame.sensor_timestamp_ns, len(frame.samples_microvolts)) for _, frame in ecg_frames]),
            "host_notification_rate_hz": host_rate([timestamp for timestamp, _ in ecg_frames]),
            "malformed_frame_count": malformed_frames,
        }
    sample_count = sum(len(frame.samples_mg) for _, frame in acc_frames)
    return {
        "stream_id": polar.STREAM_ACC,
        "status": "pass" if sample_count > 0 else "fail",
        "frame_count": len(acc_frames),
        "decoded_sample_count": sample_count,
        "sensor_sample_rate_hz": sensor_rate([(frame.sensor_timestamp_ns, len(frame.samples_mg)) for _, frame in acc_frames]),
        "host_notification_rate_hz": host_rate([timestamp for timestamp, _ in acc_frames]),
        "malformed_frame_count": malformed_frames,
    }


def host_rate(timestamps_ns: list[int]) -> float | None:
    if len(timestamps_ns) < 2:
        return None
    span_seconds = (timestamps_ns[-1] - timestamps_ns[0]) / 1_000_000_000.0
    return round((len(timestamps_ns) - 1) / span_seconds, 3) if span_seconds > 0 else None


def sensor_rate(frames: list[tuple[int, int]]) -> float | None:
    if len(frames) < 2:
        return None
    span_seconds = (frames[-1][0] - frames[0][0]) / 1_000_000_000.0
    samples_after_first = sum(sample_count for _, sample_count in frames[1:])
    return round(samples_after_first / span_seconds, 3) if span_seconds > 0 else None


def package_snapshot(packages_root: Path) -> dict[str, Any]:
    package_dir = packages_root / "packages" / "polar-h10"
    if not package_dir.exists() and packages_root.name == "polar-h10":
        package_dir = packages_root
    manifest = package_dir / "manifests" / "package.manifold.json"
    stream_files = [
        package_dir / "manifests" / "streams" / "hr-rr.json",
        package_dir / "manifests" / "streams" / "ecg.json",
        package_dir / "manifests" / "streams" / "acc.json",
        package_dir / "manifests" / "streams" / "coherence.json",
    ]
    return {
        "package_id": "package.polar_h10",
        "package_manifest_sha256": sha256_file(manifest),
        "stream_manifest_sha256": {path.stem: sha256_file(path) for path in stream_files},
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def sanitize_selector(address: str | None, name_prefix: str) -> dict[str, Any]:
    return {
        "address_supplied": bool(address),
        "name_prefix_supplied": bool(name_prefix),
    }


def failure_evidence(args: argparse.Namespace, package: dict[str, Any], started_utc: datetime, errors: list[str]) -> dict[str, Any]:
    return {
        "$schema": "rusty.manifold.live_capture_evidence.v1",
        "status": "fail",
        "host_profile": "desktop",
        "started_at_utc": started_utc.isoformat(),
        "ended_at_utc": datetime.now(UTC).isoformat(),
        "software": {
            "origin": "rusty-hostess",
            "host_app": "app.rusty_hostess_t.desktop",
            "host_app_version": "0.1.0",
        },
        "package": package,
        "capture": {"mode": args.mode, "duration_seconds": args.duration_seconds},
        "commands": [],
        "control_responses": [],
        "streams": [
            {
                "stream_id": polar.stream_id_for_mode(args.mode),
                "status": "fail",
            }
        ],
        "errors": errors,
    }


if __name__ == "__main__":
    raise SystemExit(main())
