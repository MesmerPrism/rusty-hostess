"""Validate live-capture evidence emitted by Rusty Hostess T."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


VALID_HOSTS = {"desktop", "mobile", "headset"}
VALID_STREAMS = {
    "stream.polar_h10.hr_rr",
    "stream.polar_h10.ecg",
    "stream.polar_h10.acc",
    "stream.polar_h10.coherence",
}
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--packages-root", type=Path, required=True)
    parser.add_argument("--expect-host", choices=sorted(VALID_HOSTS))
    parser.add_argument("--expect-stream", choices=["hr_rr", "ecg", "acc", "coherence"])
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
    }
    return {
        "package_manifest_sha256": sha256_file(manifest),
        "stream_manifest_sha256": {
            key: sha256_file(path)
            for key, path in stream_files.items()
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
    if total_band_power <= 0.0:
        errors.append("coherence total band power is not positive")
    if peak_band_power <= 0.0 or peak_band_power > total_band_power:
        errors.append("coherence peak band power is invalid")
    paper_ratio = float_value(stream.get("paper_ratio"))
    normalized_score = float_value(stream.get("normalized_score"))
    if paper_ratio < 0.0:
        errors.append("coherence paper ratio is negative")
    if not 0.0 <= normalized_score <= 1.0:
        errors.append("coherence normalized score is outside 0..1")
    if stream.get("quality") not in {"stable", "distributed"}:
        errors.append("coherence quality label is invalid")
    if stream.get("issue_code") not in {None, ""}:
        errors.append(f"coherence issue code must be empty on pass: {stream.get('issue_code')}")


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


if __name__ == "__main__":
    raise SystemExit(main())
