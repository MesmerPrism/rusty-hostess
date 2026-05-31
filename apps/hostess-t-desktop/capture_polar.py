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
    parser.add_argument("--mode", choices=["hr_rr", "ecg", "acc", "coherence", "module"], required=True)
    parser.add_argument("--module", action="append", default=[])
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
    try:
        selected_modules = polar.normalize_module_selection(args.module)
    except ValueError as error:
        return failure_evidence(args, package, started_utc, [str(error)])
    if args.mode == "module" and not selected_modules:
        return failure_evidence(args, package, started_utc, ["module mode requires at least one module selection"])
    dependency_streams = polar.dependency_streams_for_modules(selected_modules)
    requires_hr = args.mode in {"hr_rr", "coherence"} or polar.STREAM_HR_RR in dependency_streams
    requires_acc = args.mode == "acc" or polar.STREAM_ACC in dependency_streams
    requires_ecg = args.mode == "ecg"
    if requires_ecg and requires_acc:
        return failure_evidence(args, package, started_utc, ["ECG and ACC cannot share one PMD live capture"])
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
                elif args.mode == "acc" or polar.STREAM_ACC in dependency_streams:
                    acc_frames.append((time.time_ns(), polar.decode_acc_frame(data)))
            except ValueError:
                malformed_frames += 1

        if requires_hr:
            await client.start_notify(polar.HEART_RATE_MEASUREMENT_UUID, on_hr)
        if requires_ecg or requires_acc:
            await client.start_notify(polar.PMD_CONTROL_POINT_UUID, on_control)
            await client.start_notify(polar.PMD_DATA_UUID, on_pmd_data)
            kind = "ecg" if requires_ecg else "acc"
            await write_command(client, command_status, "get_settings", polar.build_get_settings_request(kind))
            await asyncio.sleep(0.4)
            await write_command(
                client,
                command_status,
                "start_stream",
                polar.build_start_request(kind, acc_rate_hz=args.acc_rate),
            )

        await asyncio.sleep(args.duration_seconds)

        if requires_ecg or requires_acc:
            kind = "ecg" if requires_ecg else "acc"
            await write_command(client, command_status, "stop_stream", polar.build_stop_request(kind))
            await asyncio.sleep(0.3)
            await client.stop_notify(polar.PMD_DATA_UUID)
            await client.stop_notify(polar.PMD_CONTROL_POINT_UUID)
        if requires_hr:
            await client.stop_notify(polar.HEART_RATE_MEASUREMENT_UUID)

    ended_utc = datetime.now(UTC)
    streams = stream_results(
        args.mode,
        selected_modules,
        dependency_streams,
        hr_events,
        ecg_frames,
        acc_frames,
        malformed_frames,
        args.acc_rate,
    )
    status = "pass" if streams and all(stream["status"] == "pass" for stream in streams) and not errors else "fail"
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
            "selected_module_ids": selected_modules,
            "dependency_stream_ids": sorted(dependency_streams),
            "duration_seconds": args.duration_seconds,
            "device_selector": sanitize_selector(args.device_address, args.device_name_prefix),
        },
        "commands": command_status,
        "control_responses": control_responses,
        "streams": streams,
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


def stream_results(
    mode: str,
    selected_modules: list[str],
    dependency_streams: set[str],
    hr_events: list[tuple[int, polar.HeartRateReading]],
    ecg_frames: list[tuple[int, polar.EcgFrame]],
    acc_frames: list[tuple[int, polar.AccFrame]],
    malformed_frames: int,
    acc_rate_hz: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if mode in {"hr_rr", "coherence"} or polar.STREAM_HR_RR in dependency_streams:
        result = stream_result("hr_rr", hr_events, ecg_frames, acc_frames, malformed_frames)
        if mode == "module":
            result["role"] = "module_input"
        results.append(result)
    if mode == "ecg":
        results.append(stream_result("ecg", hr_events, ecg_frames, acc_frames, malformed_frames))
    if mode == "acc" or polar.STREAM_ACC in dependency_streams:
        result = stream_result("acc", hr_events, ecg_frames, acc_frames, malformed_frames)
        if mode == "module":
            result["role"] = "module_input"
        results.append(result)
    if mode == "coherence" and not selected_modules:
        results.append(module_stream_result(polar.MODULE_COHERENCE, hr_events, acc_frames, malformed_frames, acc_rate_hz))
    for module_id in selected_modules:
        results.append(module_stream_result(module_id, hr_events, acc_frames, malformed_frames, acc_rate_hz))
    return results


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
        return module_stream_result(polar.MODULE_COHERENCE, hr_events, acc_frames, malformed_frames, 200)
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


def module_stream_result(
    module_id: str,
    hr_events: list[tuple[int, polar.HeartRateReading]],
    acc_frames: list[tuple[int, polar.AccFrame]],
    malformed_frames: int,
    acc_rate_hz: int,
) -> dict[str, Any]:
    rr_intervals = [rr_ms for _, reading in hr_events for rr_ms in reading.rr_intervals_ms]
    if module_id == polar.MODULE_HRV_WINDOW:
        result = polar.compute_hrv_window(rr_intervals)
        return {
            "stream_id": polar.STREAM_HRV_WINDOW,
            "module_id": module_id,
            "status": result.status,
            "input_stream_id": polar.STREAM_HR_RR,
            "method": "rr_window_v1",
            "heart_rate_event_count": len(hr_events),
            "input_rr_interval_count": result.input_rr_interval_count,
            "accepted_count": result.accepted_count,
            "rejected_count": result.rejected_count,
            "successive_difference_count": result.successive_difference_count,
            "mean_nn_ms": result.mean_nn_ms,
            "mean_hr_bpm": result.mean_hr_bpm,
            "sdnn_ms": result.sdnn_ms,
            "rmssd_ms": result.rmssd_ms,
            "ln_rmssd": result.ln_rmssd,
            "pnn50": result.pnn50,
            "sd1_ms": result.sd1_ms,
            "quality": result.quality,
            "issue_code": result.issue_code,
            "malformed_frame_count": malformed_frames,
        }
    if module_id == polar.MODULE_RMSSD_GAIN:
        result = polar.compute_rmssd_gain(rr_intervals)
        return {
            "stream_id": polar.STREAM_RMSSD_GAIN,
            "module_id": module_id,
            "status": result.status,
            "input_stream_id": polar.STREAM_HRV_WINDOW,
            "method": "log_rmssd_gain_v1",
            "baseline_source": result.baseline_source,
            "baseline_window_count": result.baseline_window_count,
            "current_window_count": result.current_window_count,
            "baseline_rmssd_ms": result.baseline_rmssd_ms,
            "current_rmssd_ms": result.current_rmssd_ms,
            "rmssd_ratio": result.rmssd_ratio,
            "ln_rmssd_gain": result.ln_rmssd_gain,
            "quality": result.quality,
            "issue_code": result.issue_code,
            "malformed_frame_count": malformed_frames,
        }
    if module_id == polar.MODULE_COHERENCE:
        result = polar.compute_coherence(rr_intervals)
        return {
            "stream_id": polar.STREAM_COHERENCE,
            "module_id": module_id,
            "status": result.status,
            "input_stream_id": polar.STREAM_HR_RR,
            "method": "spectral_ratio_v1",
            "heart_rate_event_count": len(hr_events),
            "input_rr_interval_count": result.input_rr_interval_count,
            "uniform_sample_count": result.uniform_sample_count,
            "window_seconds": result.window_seconds,
            "sample_rate_hz": result.sample_rate_hz,
            "peak_frequency_hz": result.peak_frequency_hz,
            "peak_band_power": result.peak_band_power,
            "total_band_power": result.total_band_power,
            "remaining_power": result.remaining_power,
            "coherence_ratio": result.coherence_ratio,
            "coherence_ratio_squared": result.coherence_ratio_squared,
            "normalized_peak_power": result.normalized_peak_power,
            "paper_ratio": result.paper_ratio,
            "normalized_score": result.normalized_score,
            "quality": result.quality,
            "issue_code": result.issue_code,
            "host_notification_rate_hz": host_rate([timestamp for timestamp, _ in hr_events]),
            "malformed_frame_count": malformed_frames,
        }
    if module_id == polar.MODULE_BREATH_VOLUME_FROM_ACC:
        result = polar.compute_breath_volume([frame for _, frame in acc_frames], acc_rate_hz=acc_rate_hz)
        return {
            "stream_id": polar.STREAM_BREATH_VOLUME,
            "module_id": module_id,
            "status": result.status,
            "input_stream_id": polar.STREAM_ACC,
            "method": "acc_projection_proxy_v1",
            "input_acc_sample_count": result.input_acc_sample_count,
            "source_sample_rate_hz": result.source_sample_rate_hz,
            "calibration_sample_count": result.calibration_sample_count,
            "projection_axis": result.projection_axis,
            "lower_bound": result.lower_bound,
            "upper_bound": result.upper_bound,
            "breath_volume_01": result.breath_volume_01,
            "phase": result.phase,
            "confidence": result.confidence,
            "quality": result.quality,
            "issue_code": result.issue_code,
            "malformed_frame_count": malformed_frames,
        }
    if module_id == polar.MODULE_BREATH_DYNAMICS:
        result = polar.compute_breath_dynamics([frame for _, frame in acc_frames], acc_rate_hz=acc_rate_hz)
        return {
            "stream_id": polar.STREAM_BREATH_DYNAMICS,
            "module_id": module_id,
            "status": result.status,
            "input_stream_id": polar.STREAM_BREATH_VOLUME,
            "method": "cycle_stats_v1",
            "input_breath_sample_count": result.input_breath_sample_count,
            "cycle_count": result.cycle_count,
            "mean_interval_s": result.mean_interval_s,
            "breathing_rate_bpm": result.breathing_rate_bpm,
            "interval_sd_s": result.interval_sd_s,
            "interval_cv": result.interval_cv,
            "mean_amplitude_01": result.mean_amplitude_01,
            "amplitude_sd_01": result.amplitude_sd_01,
            "amplitude_cv": result.amplitude_cv,
            "complexity_status": result.complexity_status,
            "quality": result.quality,
            "issue_code": result.issue_code,
            "malformed_frame_count": malformed_frames,
        }
    if module_id == polar.MODULE_HRVB_RESONANCE_AMPLITUDE:
        result = polar.compute_hrvb_resonance_amplitude(rr_intervals)
        return {
            "stream_id": polar.STREAM_HRVB_RESONANCE_AMPLITUDE,
            "module_id": module_id,
            "status": result.status,
            "input_stream_id": polar.STREAM_HR_RR,
            "method": "rolling_sine_fit_v1",
            "input_rr_interval_count": result.input_rr_interval_count,
            "window_seconds": result.window_seconds,
            "sample_rate_hz": result.sample_rate_hz,
            "amplitude_bpm": result.amplitude_bpm,
            "mean_hr_bpm": result.mean_hr_bpm,
            "frequency_hz": result.frequency_hz,
            "omega_rad_s": result.omega_rad_s,
            "phase_rad": result.phase_rad,
            "median_session_amplitude_bpm": result.median_session_amplitude_bpm,
            "threshold_status": result.threshold_status,
            "quality": result.quality,
            "issue_code": result.issue_code,
            "malformed_frame_count": malformed_frames,
        }
    raise ValueError(f"unknown module id: {module_id}")


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
        package_dir / "manifests" / "streams" / "hrv-window.json",
        package_dir / "manifests" / "streams" / "rmssd-gain.json",
        package_dir / "manifests" / "streams" / "breath-volume.json",
        package_dir / "manifests" / "streams" / "breath-dynamics.json",
        package_dir / "manifests" / "streams" / "hrvb-resonance-amplitude.json",
    ]
    module_files = [
        package_dir / "manifests" / "modules" / "provider.json",
        package_dir / "manifests" / "modules" / "coherence.json",
        package_dir / "manifests" / "modules" / "hrv-window.json",
        package_dir / "manifests" / "modules" / "rmssd-gain.json",
        package_dir / "manifests" / "modules" / "breath-volume-from-acc.json",
        package_dir / "manifests" / "modules" / "breath-dynamics.json",
        package_dir / "manifests" / "modules" / "hrvb-resonance-amplitude.json",
    ]
    return {
        "package_id": "package.polar_h10",
        "package_manifest_sha256": sha256_file(manifest),
        "stream_manifest_sha256": {path.stem: sha256_file(path) for path in stream_files},
        "module_manifest_sha256": {path.stem: sha256_file(path) for path in module_files},
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
    selected_modules: list[str] = []
    try:
        selected_modules = polar.normalize_module_selection(getattr(args, "module", []))
    except ValueError:
        pass
    stream_id = polar.stream_id_for_mode(args.mode) if args.mode != "module" else "stream.polar_h10.module_selection"
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
        "capture": {
            "mode": args.mode,
            "selected_module_ids": selected_modules,
            "duration_seconds": args.duration_seconds,
        },
        "commands": [],
        "control_responses": [],
        "streams": [
            {
                "stream_id": stream_id,
                "status": "fail",
            }
        ],
        "errors": errors,
    }


if __name__ == "__main__":
    raise SystemExit(main())
