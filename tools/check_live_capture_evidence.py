"""Validate live-capture evidence emitted by Rusty Hostess T."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VALID_HOSTS = {"desktop", "mobile", "headset"}
VALID_STREAMS = {"stream.polar_h10.hr_rr", "stream.polar_h10.ecg", "stream.polar_h10.acc"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--expect-host", choices=sorted(VALID_HOSTS))
    parser.add_argument("--expect-stream", choices=["hr_rr", "ecg", "acc"])
    args = parser.parse_args()

    doc = json.loads(args.input.read_text(encoding="utf-8"))
    errors = validate(doc)
    if args.expect_host and doc.get("host_profile") != args.expect_host:
        errors.append(f"expected host {args.expect_host}, got {doc.get('host_profile')}")
    if args.expect_stream:
        expected = {
            "hr_rr": "stream.polar_h10.hr_rr",
            "ecg": "stream.polar_h10.ecg",
            "acc": "stream.polar_h10.acc",
        }[args.expect_stream]
        if expected not in {stream.get("stream_id") for stream in doc.get("streams", [])}:
            errors.append(f"expected stream {expected}")

    report = {
        "$schema": "rusty.manifold.live_capture_validation_report.v1",
        "status": "fail" if errors else "pass",
        "input": str(args.input),
        "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if errors else 0


def validate(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("$schema") != "rusty.manifold.live_capture_evidence.v1":
        errors.append("missing or unknown schema")
    if doc.get("host_profile") not in VALID_HOSTS:
        errors.append("host_profile must be desktop, mobile, or headset")
    if doc.get("software", {}).get("origin") != "rusty-hostess":
        errors.append("software.origin must be rusty-hostess")

    package = doc.get("package", {})
    if package.get("package_id") != "package.polar_h10":
        errors.append("package_id must be package.polar_h10")
    if not package.get("package_manifest_sha256"):
        errors.append("package manifest hash is required")

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
        if stream_id == "stream.polar_h10.hr_rr":
            if int(stream.get("heart_rate_event_count", 0)) <= 0:
                errors.append("HR/RR stream has no heart-rate events")
            if int(stream.get("rr_interval_count", 0)) <= 0:
                errors.append("HR/RR stream has no RR intervals")
        else:
            if int(stream.get("frame_count", 0)) <= 0:
                errors.append(f"{stream_id} has no frames")
            if int(stream.get("decoded_sample_count", 0)) <= 0:
                errors.append(f"{stream_id} has no decoded samples")

    return errors


if __name__ == "__main__":
    raise SystemExit(main())
