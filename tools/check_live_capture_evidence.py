"""Validate live-capture evidence emitted by Rusty Hostess T."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


VALID_HOSTS = {"desktop", "mobile", "headset"}
VALID_STREAMS = {
    "stream.polar_h10.hr_rr",
    "stream.polar_h10.ecg",
    "stream.polar_h10.acc",
    "stream.polar_h10.coherence",
    "stream.polar_h10.hrv_window",
    "stream.polar_h10.rmssd_gain",
    "stream.polar_h10.breath_volume",
    "stream.polar_h10.breath_dynamics",
    "stream.polar_h10.hrvb_resonance_amplitude",
}
VALID_MODULES = {
    "module.polar_h10.hrv_window": "stream.polar_h10.hrv_window",
    "module.polar_h10.rmssd_gain": "stream.polar_h10.rmssd_gain",
    "module.polar_h10.coherence": "stream.polar_h10.coherence",
    "module.polar_h10.breath_volume_from_acc": "stream.polar_h10.breath_volume",
    "module.polar_h10.breath_dynamics": "stream.polar_h10.breath_dynamics",
    "module.polar_h10.hrvb_resonance_amplitude": "stream.polar_h10.hrvb_resonance_amplitude",
}
MODULE_ALIASES = {
    "hrv_window": "module.polar_h10.hrv_window",
    "rmssd_gain": "module.polar_h10.rmssd_gain",
    "coherence": "module.polar_h10.coherence",
    "breath_volume": "module.polar_h10.breath_volume_from_acc",
    "breath_volume_from_acc": "module.polar_h10.breath_volume_from_acc",
    "breath_dynamics": "module.polar_h10.breath_dynamics",
    "hrvb_resonance_amplitude": "module.polar_h10.hrvb_resonance_amplitude",
}
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--packages-root", type=Path, required=True)
    parser.add_argument("--expect-host", choices=sorted(VALID_HOSTS))
    parser.add_argument("--expect-stream", choices=["hr_rr", "ecg", "acc", "coherence"])
    parser.add_argument("--expect-module", action="append", default=[])
    parser.add_argument("--report-out", type=Path)
    args = parser.parse_args()

    doc = json.loads(args.input.read_text(encoding="utf-8"))
    package = package_snapshot(args.packages_root)
    errors = validate(doc, package)
    if args.expect_host and doc.get("host_profile") != args.expect_host:
        errors.append(f"expected host {args.expect_host}, got {doc.get('host_profile')}")
    if args.expect_stream:
        expected = {
            "hr_rr": "stream.polar_h10.hr_rr",
            "ecg": "stream.polar_h10.ecg",
            "acc": "stream.polar_h10.acc",
            "coherence": "stream.polar_h10.coherence",
        }[args.expect_stream]
        if expected not in {stream.get("stream_id") for stream in doc.get("streams", [])}:
            errors.append(f"expected stream {expected}")
    expected_modules = normalize_modules(args.expect_module)
    if expected_modules:
        actual_modules = {stream.get("module_id") for stream in doc.get("streams", [])}
        actual_streams = {stream.get("stream_id") for stream in doc.get("streams", [])}
        for module_id in expected_modules:
            if module_id not in actual_modules:
                errors.append(f"expected module {module_id}")
            expected_stream = VALID_MODULES[module_id]
            if expected_stream not in actual_streams:
                errors.append(f"expected module stream {expected_stream}")

    report = {
        "$schema": "rusty.manifold.live_capture_validation_report.v1",
        "status": "fail" if errors else "pass",
        "input": str(args.input),
        "errors": errors,
    }
    if args.report_out:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if errors else 0


def validate(doc: dict[str, Any], package_snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("$schema") != "rusty.manifold.live_capture_evidence.v1":
        errors.append("missing or unknown schema")
    if doc.get("status") != "pass":
        errors.append(f"top-level status must be pass, got {doc.get('status')}")
    if doc.get("host_profile") not in VALID_HOSTS:
        errors.append("host_profile must be desktop, mobile, or headset")
    if doc.get("software", {}).get("origin") != "rusty-hostess":
        errors.append("software.origin must be rusty-hostess")
    if doc.get("errors"):
        errors.append(f"evidence errors must be empty: {doc.get('errors')}")

    package = doc.get("package", {})
    if package.get("package_id") != "package.polar_h10":
        errors.append("package_id must be package.polar_h10")
    package_hash = package.get("package_manifest_sha256")
    if not valid_sha256(package_hash):
        errors.append("package manifest hash must be a SHA-256 hex digest")
    elif package_hash != package_snapshot["package_manifest_sha256"]:
        errors.append("package manifest hash does not match packages root")

    stream_hashes = package.get("stream_manifest_sha256", {})
    if stream_hashes is not None and not isinstance(stream_hashes, dict):
        errors.append("stream manifest hashes must be an object")
        stream_hashes = {}
    for key, value in stream_hashes.items():
        if key not in package_snapshot["stream_manifest_sha256"]:
            errors.append(f"unknown stream manifest hash key {key}")
        elif not valid_sha256(value):
            errors.append(f"stream manifest hash {key} must be a SHA-256 hex digest")
        elif value != package_snapshot["stream_manifest_sha256"][key]:
            errors.append(f"stream manifest hash {key} does not match packages root")

    module_hashes = package.get("module_manifest_sha256", {})
    if module_hashes is not None and not isinstance(module_hashes, dict):
        errors.append("module manifest hashes must be an object")
        module_hashes = {}
    for key, value in module_hashes.items():
        if key not in package_snapshot["module_manifest_sha256"]:
            errors.append(f"unknown module manifest hash key {key}")
        elif not valid_sha256(value):
            errors.append(f"module manifest hash {key} must be a SHA-256 hex digest")
        elif value != package_snapshot["module_manifest_sha256"][key]:
            errors.append(f"module manifest hash {key} does not match packages root")

    streams = doc.get("streams")
    if not isinstance(streams, list) or not streams:
        errors.append("at least one stream result is required")
        return errors

    for stream in streams:
        stream_id = stream.get("stream_id")
        if stream_id not in VALID_STREAMS:
            errors.append(f"unknown stream id {stream_id}")
            continue
        if stream.get("status") != "pass":
            errors.append(f"{stream_id} did not pass")
        if int_value(stream.get("malformed_frame_count", 0)) != 0:
            errors.append(f"{stream_id} has malformed frames")
        if stream_id == "stream.polar_h10.hr_rr":
            if int_value(stream.get("heart_rate_event_count", 0)) <= 0:
                errors.append("HR/RR stream has no heart-rate events")
            if int_value(stream.get("rr_interval_count", 0)) <= 0:
                errors.append("HR/RR stream has no RR intervals")
        elif stream_id == "stream.polar_h10.coherence":
            validate_coherence_stream(stream, errors)
        elif stream_id == "stream.polar_h10.hrv_window":
            validate_hrv_window_stream(stream, errors)
        elif stream_id == "stream.polar_h10.rmssd_gain":
            validate_rmssd_gain_stream(stream, errors)
        elif stream_id == "stream.polar_h10.breath_volume":
            validate_breath_volume_stream(stream, errors)
        elif stream_id == "stream.polar_h10.breath_dynamics":
            validate_breath_dynamics_stream(stream, errors)
        elif stream_id == "stream.polar_h10.hrvb_resonance_amplitude":
            validate_hrvb_stream(stream, errors)
        else:
            if int_value(stream.get("frame_count", 0)) <= 0:
                errors.append(f"{stream_id} has no frames")
            if int_value(stream.get("decoded_sample_count", 0)) <= 0:
                errors.append(f"{stream_id} has no decoded samples")

    return errors


def package_snapshot(packages_root: Path) -> dict[str, Any]:
    package_dir = packages_root / "packages" / "polar-h10"
    if not package_dir.exists() and packages_root.name == "polar-h10":
        package_dir = packages_root
    manifest = package_dir / "manifests" / "package.manifold.json"
    stream_files = {
        "hr-rr": package_dir / "manifests" / "streams" / "hr-rr.json",
        "ecg": package_dir / "manifests" / "streams" / "ecg.json",
        "acc": package_dir / "manifests" / "streams" / "acc.json",
        "coherence": package_dir / "manifests" / "streams" / "coherence.json",
        "hrv-window": package_dir / "manifests" / "streams" / "hrv-window.json",
        "rmssd-gain": package_dir / "manifests" / "streams" / "rmssd-gain.json",
        "breath-volume": package_dir / "manifests" / "streams" / "breath-volume.json",
        "breath-dynamics": package_dir / "manifests" / "streams" / "breath-dynamics.json",
        "hrvb-resonance-amplitude": package_dir / "manifests" / "streams" / "hrvb-resonance-amplitude.json",
    }
    module_files = {
        "provider": package_dir / "manifests" / "modules" / "provider.json",
        "coherence": package_dir / "manifests" / "modules" / "coherence.json",
        "hrv-window": package_dir / "manifests" / "modules" / "hrv-window.json",
        "rmssd-gain": package_dir / "manifests" / "modules" / "rmssd-gain.json",
        "breath-volume-from-acc": package_dir / "manifests" / "modules" / "breath-volume-from-acc.json",
        "breath-dynamics": package_dir / "manifests" / "modules" / "breath-dynamics.json",
        "hrvb-resonance-amplitude": package_dir / "manifests" / "modules" / "hrvb-resonance-amplitude.json",
    }
    return {
        "package_manifest_sha256": sha256_file(manifest),
        "stream_manifest_sha256": {
            key: sha256_file(path)
            for key, path in stream_files.items()
            if path.exists()
        },
        "module_manifest_sha256": {
            key: sha256_file(path)
            for key, path in module_files.items()
            if path.exists()
        },
    }


def validate_coherence_stream(stream: dict[str, Any], errors: list[str]) -> None:
    if stream.get("input_stream_id") != "stream.polar_h10.hr_rr":
        errors.append("coherence input stream must be HR/RR")
    if stream.get("method") != "spectral_ratio_v1":
        errors.append("coherence method must be spectral_ratio_v1")
    if int_value(stream.get("heart_rate_event_count", 0)) <= 0:
        errors.append("coherence has no heart-rate events")
    if int_value(stream.get("input_rr_interval_count", 0)) <= 0:
        errors.append("coherence has no RR input intervals")
    if int_value(stream.get("uniform_sample_count", 0)) < 128:
        errors.append("coherence has fewer than 128 uniform samples")
    if float_value(stream.get("window_seconds")) < 64.0:
        errors.append("coherence window is shorter than 64 seconds")
    if float_value(stream.get("sample_rate_hz")) != 2.0:
        errors.append("coherence sample rate must be 2 Hz")
    peak_frequency = float_value(stream.get("peak_frequency_hz"))
    if not 0.04 <= peak_frequency <= 0.26:
        errors.append("coherence peak frequency is outside the peak-search band")
    total_band_power = float_value(stream.get("total_band_power"))
    peak_band_power = float_value(stream.get("peak_band_power"))
    remaining_power = float_value(stream.get("remaining_power"))
    if total_band_power <= 0.0:
        errors.append("coherence total band power is not positive")
    if peak_band_power <= 0.0 or peak_band_power > total_band_power:
        errors.append("coherence peak band power is invalid")
    if remaining_power < 0.0:
        errors.append("coherence remaining power is negative")
    paper_ratio = float_value(stream.get("paper_ratio"))
    coherence_ratio = float_value(stream.get("coherence_ratio"))
    coherence_ratio_squared = float_value(stream.get("coherence_ratio_squared"))
    normalized_peak_power = float_value(stream.get("normalized_peak_power"))
    normalized_score = float_value(stream.get("normalized_score"))
    if paper_ratio < 0.0:
        errors.append("coherence paper ratio is negative")
    if coherence_ratio < 0.0:
        errors.append("coherence ratio is negative")
    if coherence_ratio_squared < 0.0:
        errors.append("coherence squared ratio is negative")
    if not approx_equal(remaining_power, total_band_power - peak_band_power):
        errors.append("coherence remaining power does not match total - peak power")
    if remaining_power > 0.0 and not approx_equal(coherence_ratio, peak_band_power / remaining_power):
        errors.append("coherence ratio does not match peak / remaining power")
    if not approx_equal(paper_ratio, coherence_ratio):
        errors.append("coherence paper ratio does not match coherence ratio")
    if not approx_equal(coherence_ratio_squared, coherence_ratio * coherence_ratio):
        errors.append("coherence squared ratio does not match coherence_ratio * coherence_ratio")
    if total_band_power > 0.0 and not approx_equal(normalized_peak_power, peak_band_power / total_band_power):
        errors.append("coherence normalized peak power does not match peak / total power")
    if paper_ratio >= 0.0 and not approx_equal(normalized_score, paper_ratio / (paper_ratio + 1.0)):
        errors.append("coherence normalized score does not match ratio / (ratio + 1)")
    if not 0.0 <= normalized_peak_power <= 1.0:
        errors.append("coherence normalized peak power is outside 0..1")
    if not 0.0 <= normalized_score <= 1.0:
        errors.append("coherence normalized score is outside 0..1")
    if stream.get("quality") not in {"stable", "distributed"}:
        errors.append("coherence quality label is invalid")
    if stream.get("issue_code") not in {None, ""}:
        errors.append(f"coherence issue code must be empty on pass: {stream.get('issue_code')}")


def validate_hrv_window_stream(stream: dict[str, Any], errors: list[str]) -> None:
    if stream.get("module_id") != "module.polar_h10.hrv_window":
        errors.append("HRV window module id is invalid")
    if stream.get("input_stream_id") != "stream.polar_h10.hr_rr":
        errors.append("HRV window input stream must be HR/RR")
    if stream.get("method") != "rr_window_v1":
        errors.append("HRV window method must be rr_window_v1")
    if int_value(stream.get("heart_rate_event_count", 0)) <= 0:
        errors.append("HRV window has no heart-rate events")
    if int_value(stream.get("accepted_count", 0)) < 2:
        errors.append("HRV window has fewer than two accepted intervals")
    if int_value(stream.get("successive_difference_count", 0)) < 1:
        errors.append("HRV window has no successive differences")
    for field in ["mean_nn_ms", "mean_hr_bpm", "sdnn_ms", "rmssd_ms", "pnn50", "sd1_ms"]:
        if float_value(stream.get(field)) < 0.0:
            errors.append(f"HRV window {field} is invalid")
    if stream.get("quality") not in {"stable", "low_motion"}:
        errors.append("HRV window quality label is invalid")
    if stream.get("issue_code") not in {None, ""}:
        errors.append(f"HRV window issue code must be empty on pass: {stream.get('issue_code')}")


def validate_rmssd_gain_stream(stream: dict[str, Any], errors: list[str]) -> None:
    if stream.get("module_id") != "module.polar_h10.rmssd_gain":
        errors.append("RMSSD gain module id is invalid")
    if stream.get("input_stream_id") != "stream.polar_h10.hrv_window":
        errors.append("RMSSD gain input stream must be HRV window")
    if stream.get("method") != "log_rmssd_gain_v1":
        errors.append("RMSSD gain method must be log_rmssd_gain_v1")
    if stream.get("baseline_source") not in {"explicit_baseline", "run_config_baseline", "manifest_baseline"}:
        errors.append("RMSSD gain baseline source must be an explicit package/runtime baseline")
    if int_value(stream.get("baseline_window_count", 0)) < 2:
        errors.append("RMSSD gain baseline window is underfilled")
    if int_value(stream.get("current_window_count", 0)) < 2:
        errors.append("RMSSD gain current window is underfilled")
    if float_value(stream.get("baseline_rmssd_ms")) <= 0.0:
        errors.append("RMSSD gain baseline RMSSD is not positive")
    if float_value(stream.get("current_rmssd_ms")) < 0.0:
        errors.append("RMSSD gain current RMSSD is invalid")
    if float_value(stream.get("rmssd_ratio")) <= 0.0:
        errors.append("RMSSD gain ratio is not positive")
    if stream.get("issue_code") not in {None, ""}:
        errors.append(f"RMSSD gain issue code must be empty on pass: {stream.get('issue_code')}")


def validate_breath_volume_stream(stream: dict[str, Any], errors: list[str]) -> None:
    if stream.get("module_id") != "module.polar_h10.breath_volume_from_acc":
        errors.append("breath volume module id is invalid")
    if stream.get("input_stream_id") != "stream.polar_h10.acc":
        errors.append("breath volume input stream must be ACC")
    if stream.get("method") != "acc_projection_proxy_v1":
        errors.append("breath volume method must be acc_projection_proxy_v1")
    if int_value(stream.get("input_acc_sample_count", 0)) <= 0:
        errors.append("breath volume has no ACC samples")
    if int_value(stream.get("calibration_sample_count", 0)) <= 0:
        errors.append("breath volume calibration is empty")
    lower = float_value(stream.get("lower_bound"))
    upper = float_value(stream.get("upper_bound"))
    if upper <= lower:
        errors.append("breath volume calibration bounds are invalid")
    volume = float_value(stream.get("breath_volume_01"))
    if not 0.0 <= volume <= 1.0:
        errors.append("breath volume is outside 0..1")
    if float_value(stream.get("confidence")) < 0.0:
        errors.append("breath volume confidence is invalid")
    if stream.get("phase") not in {"inhale", "exhale"}:
        errors.append("breath volume phase is invalid")
    if stream.get("issue_code") not in {None, ""}:
        errors.append(f"breath volume issue code must be empty on pass: {stream.get('issue_code')}")


def validate_breath_dynamics_stream(stream: dict[str, Any], errors: list[str]) -> None:
    if stream.get("module_id") != "module.polar_h10.breath_dynamics":
        errors.append("breath dynamics module id is invalid")
    if stream.get("input_stream_id") != "stream.polar_h10.breath_volume":
        errors.append("breath dynamics input stream must be breath volume")
    if stream.get("method") != "cycle_stats_v1":
        errors.append("breath dynamics method must be cycle_stats_v1")
    if int_value(stream.get("input_breath_sample_count", 0)) <= 0:
        errors.append("breath dynamics has no breath samples")
    if int_value(stream.get("cycle_count", 0)) < 2:
        errors.append("breath dynamics has fewer than two cycles")
    if float_value(stream.get("mean_interval_s")) <= 0.0:
        errors.append("breath dynamics mean interval is invalid")
    if float_value(stream.get("breathing_rate_bpm")) <= 0.0:
        errors.append("breath dynamics breathing rate is invalid")
    if float_value(stream.get("mean_amplitude_01")) < 0.0:
        errors.append("breath dynamics mean amplitude is invalid")
    if stream.get("complexity_status") not in {"underfilled", "computed"}:
        errors.append("breath dynamics complexity status is invalid")
    if stream.get("issue_code") not in {None, ""}:
        errors.append(f"breath dynamics issue code must be empty on pass: {stream.get('issue_code')}")


def validate_hrvb_stream(stream: dict[str, Any], errors: list[str]) -> None:
    if stream.get("module_id") != "module.polar_h10.hrvb_resonance_amplitude":
        errors.append("HRVB resonance amplitude module id is invalid")
    if stream.get("input_stream_id") != "stream.polar_h10.hr_rr":
        errors.append("HRVB resonance amplitude input stream must be HR/RR")
    if stream.get("method") != "rolling_sine_fit_v1":
        errors.append("HRVB resonance amplitude method must be rolling_sine_fit_v1")
    if int_value(stream.get("input_rr_interval_count", 0)) < 20:
        errors.append("HRVB resonance amplitude RR input is underfilled")
    if float_value(stream.get("window_seconds")) < 30.0:
        errors.append("HRVB resonance amplitude window is shorter than 30 seconds")
    frequency = float_value(stream.get("frequency_hz"))
    if not 0.08 <= frequency <= 0.12:
        errors.append("HRVB resonance amplitude frequency is outside 0.08..0.12 Hz")
    if float_value(stream.get("amplitude_bpm")) < 0.0:
        errors.append("HRVB resonance amplitude is invalid")
    if stream.get("threshold_status") not in {"above_source_threshold", "below_source_threshold"}:
        errors.append("HRVB resonance amplitude threshold status is invalid")
    if stream.get("issue_code") not in {None, ""}:
        errors.append(f"HRVB resonance amplitude issue code must be empty on pass: {stream.get('issue_code')}")


def normalize_modules(values: list[str]) -> list[str]:
    modules: list[str] = []
    for value in values:
        for item in value.split(","):
            key = item.strip()
            if not key:
                continue
            module_id = MODULE_ALIASES.get(key, key)
            if module_id not in VALID_MODULES:
                raise SystemExit(f"unknown expected module: {key}")
            if module_id not in modules:
                modules.append(module_id)
    return modules


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and HEX_SHA256.fullmatch(value) is not None


def int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def float_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def approx_equal(left: float, right: float, *, relative: float = 0.000001, absolute: float = 0.000001) -> bool:
    return math.isclose(left, right, rel_tol=relative, abs_tol=absolute)


if __name__ == "__main__":
    raise SystemExit(main())
