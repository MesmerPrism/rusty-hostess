"""Receive Quest-owned QCL-081 LSL samples over a promoted Wi-Fi Direct group."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any


REPORT_SCHEMA = "rusty.hostess.qcl081_wifi_direct_lsl_receiver.v1"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_receiver(args)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report.get("status") == "pass" else 2


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--stream-name", default="RustyQCL081WifiDirect")
    parser.add_argument("--stream-type", default="rusty.quest.qcl081.wifi_direct")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--sample-count", type=int, default=16)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--topology-report", default="")
    return parser.parse_args(argv)


def run_receiver(args: argparse.Namespace) -> dict[str, Any]:
    run_id = str(args.run_id)
    stream_name = str(args.stream_name or "RustyQCL081WifiDirect")
    stream_type = str(args.stream_type or "rusty.quest.qcl081.wifi_direct")
    source_id = str(args.source_id)
    sample_count = max(1, int(args.sample_count or 16))
    timeout = max(1.0, float(args.timeout_seconds or 20.0))
    topology = read_json(Path(args.topology_report)) if args.topology_report else {}

    try:
        import pylsl
        from pylsl import StreamInlet, local_clock, resolve_byprop
    except Exception as exc:
        return base_report(
            args,
            status="blocked",
            samples_received=0,
            loss_percent=100.0,
            discovery_ms=None,
            monotonic=False,
            issue_codes=["hostess.issue.connectivity_probe.pylsl_unavailable"],
            notes=f"pylsl/liblsl unavailable on Windows receiver: {exc}",
            topology=topology,
        )

    library_version = safe_library_version(pylsl)
    discovery_started = time.monotonic()
    streams = list(resolve_byprop("source_id", source_id, minimum=1, timeout=timeout) or [])
    discovery_ms = int(round((time.monotonic() - discovery_started) * 1000.0))
    if not streams:
        return base_report(
            args,
            status="fail",
            samples_received=0,
            loss_percent=100.0,
            discovery_ms=discovery_ms,
            monotonic=False,
            issue_codes=["hostess.issue.connectivity_probe.lsl_discovery_failed"],
            notes="No Quest QCL-081 LSL outlet was discovered by source_id.",
            topology=topology,
            library_version=library_version,
        )

    inlet = StreamInlet(streams[0], max_buflen=4, max_chunklen=1, recover=True)
    try:
        inlet.open_stream(timeout=timeout)
    except Exception:
        pass

    time_correction_before = safe_time_correction(inlet)
    received_sequences: list[int] = []
    lsl_timestamps: list[float] = []
    host_pull_clock: list[float] = []
    deadline = time.monotonic() + timeout
    while len(received_sequences) < sample_count and time.monotonic() < deadline:
        sample, timestamp = inlet.pull_sample(timeout=0.25)
        if not sample:
            continue
        try:
            received_sequences.append(int(round(float(sample[0]))))
            lsl_timestamps.append(float(timestamp))
            host_pull_clock.append(float(local_clock()))
        except (TypeError, ValueError, IndexError):
            continue
    time_correction_after = safe_time_correction(inlet)

    received_count = len(received_sequences)
    loss_percent = round(((sample_count - received_count) / sample_count) * 100.0, 2)
    monotonic_sequences = received_sequences == list(range(received_count))
    monotonic_timestamps = all(
        right > left for left, right in zip(lsl_timestamps, lsl_timestamps[1:])
    )
    if received_count == sample_count and monotonic_sequences and monotonic_timestamps:
        status = "pass"
        issue_codes: list[str] = []
    elif received_count > 0:
        status = "warn"
        issue_codes = ["hostess.issue.connectivity_probe.lsl_sample_continuity_degraded"]
    else:
        status = "fail"
        issue_codes = ["hostess.issue.connectivity_probe.lsl_sample_continuity_failed"]

    report = base_report(
        args,
        status=status,
        samples_received=received_count,
        loss_percent=loss_percent,
        discovery_ms=discovery_ms,
        monotonic=monotonic_sequences and monotonic_timestamps,
        issue_codes=issue_codes,
        notes="Windows pylsl inlet received Quest-owned source-timestamped LSL samples over Wi-Fi Direct.",
        topology=topology,
        library_version=library_version,
    )
    report["received_sequences"] = received_sequences[:50]
    report["lsl_timestamps_seconds"] = lsl_timestamps[:50]
    report["source_timestamp_domain"] = "quest_lsl_local_clock"
    report["source_timestamps_monotonic"] = monotonic_timestamps
    report["host_pull_clock_seconds"] = host_pull_clock[:50]
    report["time_correction_seconds_before"] = time_correction_before
    report["time_correction_seconds_after"] = time_correction_after
    report["inter_sample_ms_median"] = median_delta_ms(lsl_timestamps)
    return report


def base_report(
    args: argparse.Namespace,
    *,
    status: str,
    samples_received: int,
    loss_percent: float,
    discovery_ms: int | None,
    monotonic: bool,
    issue_codes: list[str],
    notes: str,
    topology: dict[str, Any],
    library_version: Any = None,
) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "status": status,
        "run_id": str(args.run_id),
        "source": "quest-runtime",
        "evidence_tier": "quest_runtime",
        "stream_name": str(args.stream_name or "RustyQCL081WifiDirect"),
        "stream_type": str(args.stream_type or "rusty.quest.qcl081.wifi_direct"),
        "source_id": str(args.source_id),
        "samples_requested": max(1, int(args.sample_count or 16)),
        "samples_received": samples_received,
        "loss_percent": loss_percent,
        "discovery_ms": discovery_ms,
        "monotonic_sequences": monotonic,
        "library_version": library_version,
        "topology": {
            "owner": "wifi_direct",
            "network_provider": "wifi_direct",
            "endpoint_direction": "lsl_multicast_discovery_plus_tcp_samples",
            "topology_report_path": str(args.topology_report or ""),
            "paired_topology_status": topology.get("status"),
            "paired_topology_promotion_allowed": (topology.get("promotion") or {}).get("allowed"),
        },
        "issue_codes": issue_codes,
        "notes": notes,
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def safe_library_version(pylsl_module: Any) -> Any:
    for name in ("library_version", "lsl_library_version"):
        func = getattr(pylsl_module, name, None)
        if callable(func):
            try:
                return func()
            except Exception:
                pass
    return getattr(pylsl_module, "__version__", None)


def safe_time_correction(inlet: Any) -> float | None:
    try:
        return float(inlet.time_correction(timeout=1.0))
    except Exception:
        return None


def median_delta_ms(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    deltas = [(right - left) * 1000.0 for left, right in zip(values, values[1:])]
    return round(float(statistics.median(deltas)), 3)


if __name__ == "__main__":
    raise SystemExit(main())
