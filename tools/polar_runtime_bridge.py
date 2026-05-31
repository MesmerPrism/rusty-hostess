"""Bridge Hostess captures into the package Rust runtime input shape."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from tools import polar_protocol as polar


def runtime_input_from_capture(
    *,
    input_id: str,
    hr_events: list[tuple[int, polar.HeartRateReading]],
    acc_frames: list[tuple[int, polar.AccFrame]],
    acc_rate_hz: int,
    rmssd_gain_baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "$schema": "rusty.manifold.polar_h10.processor_runtime_input.v1",
        "input_id": input_id,
        "hr_rr": {
            "heart_rate_event_count": len(hr_events),
            "rr_intervals_ms": [rr_ms for _, reading in hr_events for rr_ms in reading.rr_intervals_ms],
        },
    }
    if acc_frames:
        doc["raw_acc"] = {
            "sample_rate_hz": float(acc_rate_hz),
            "frames": [
                {
                    "sensor_timestamp_ns": frame.sensor_timestamp_ns,
                    "samples_mg": [
                        {"x_mg": sample.x_mg, "y_mg": sample.y_mg, "z_mg": sample.z_mg}
                        for sample in frame.samples_mg
                    ],
                }
                for _, frame in acc_frames
            ],
        }
    if rmssd_gain_baseline is not None:
        doc["rmssd_gain_baseline"] = rmssd_gain_baseline
    return doc


def graph_report_streams(
    graph_report: dict[str, Any], *, include_input_streams: bool = False
) -> list[dict[str, Any]]:
    skipped = set() if include_input_streams else {polar.STREAM_HR_RR, polar.STREAM_ACC}
    streams: list[dict[str, Any]] = []
    for raw_stream in graph_report.get("streams", []):
        if not isinstance(raw_stream, dict):
            continue
        if raw_stream.get("stream_id") in skipped:
            continue
        stream = dict(raw_stream)
        stream.setdefault("malformed_frame_count", 0)
        streams.append(stream)
    return streams


def run_graph_fixture(
    *,
    packages_root: Path,
    input_path: Path,
    selected_modules: list[str],
    out_path: Path,
) -> subprocess.CompletedProcess[str]:
    package_root = polar_package_root(packages_root)
    graph_path = package_root / "fixtures" / "valid" / "graph.json"
    command = [
        "cargo",
        "run",
        "-p",
        "polar-h10-core",
        "--",
        "run-fixture",
        "--graph",
        str(graph_path),
        "--input",
        str(input_path),
        "--select",
        ",".join(selected_modules),
        "--out",
        str(out_path),
    ]
    return subprocess.run(command, cwd=cargo_workspace_root(packages_root), text=True)


def polar_package_root(packages_root: Path) -> Path:
    package_root = packages_root / "packages" / "polar-h10"
    return package_root if package_root.exists() else packages_root


def cargo_workspace_root(packages_root: Path) -> Path:
    for candidate in [packages_root, packages_root.parent, packages_root.parent.parent]:
        if (candidate / "Cargo.toml").exists():
            return candidate
    return packages_root


def write_runtime_input(path: Path, runtime_input: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(runtime_input, indent=2, sort_keys=True), encoding="utf-8")
