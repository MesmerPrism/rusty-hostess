"""Run a bidirectional QCL-081 LSL echo pass over a promoted Wi-Fi Direct group."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
from pathlib import Path
from typing import Any


REPORT_SCHEMA = "rusty.hostess.qcl081_wifi_direct_lsl_echo_roundtrip.v1"
ECHO_INLET_MAX_BUFLEN_SECONDS = 60


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_echo_roundtrip(args)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report.get("status") == "pass" else 2


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--command-stream-name", default="RustyQCL081WifiDirectCommand")
    parser.add_argument("--command-stream-type", default="rusty.quest.qcl081.wifi_direct.command")
    parser.add_argument("--command-source-id", required=True)
    parser.add_argument("--echo-stream-name", default="RustyQCL081WifiDirectEcho")
    parser.add_argument("--echo-stream-type", default="rusty.quest.qcl081.wifi_direct.echo")
    parser.add_argument("--echo-source-id", required=True)
    parser.add_argument("--sample-count", type=int, default=300)
    parser.add_argument("--interval-ms", type=float, default=100.0)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--pre-send-delay-ms", type=float, default=3000.0)
    parser.add_argument("--command-mode", choices=("pylsl_outlet", "external"), default="pylsl_outlet")
    parser.add_argument("--topology-report", default="")
    return parser.parse_args(argv)


def run_echo_roundtrip(args: argparse.Namespace) -> dict[str, Any]:
    sample_count = max(1, int(args.sample_count or 300))
    interval_seconds = max(0.001, float(args.interval_ms or 100.0) / 1000.0)
    timeout_seconds = max(1.0, float(args.timeout_seconds or 60.0))
    topology = read_json(Path(args.topology_report)) if args.topology_report else {}

    try:
        import pylsl
        from pylsl import StreamInfo, StreamInlet, StreamOutlet, local_clock, resolve_byprop
    except Exception as exc:
        return base_report(
            args,
            status="blocked",
            issue_codes=["hostess.issue.connectivity_probe.pylsl_unavailable"],
            notes=f"pylsl/liblsl unavailable on Windows echo probe: {exc}",
            topology=topology,
            samples_sent=0,
            samples_received=0,
        )

    library_version = safe_library_version(pylsl)
    command_outlet = None
    if args.command_mode == "pylsl_outlet":
        command_info = StreamInfo(
            str(args.command_stream_name),
            str(args.command_stream_type),
            2,
            0.0,
            "double64",
            str(args.command_source_id),
        )
        command_outlet = StreamOutlet(command_info, 1, 60)

    pre_send_delay = max(0.0, float(args.pre_send_delay_ms or 0.0) / 1000.0)
    sent_by_sequence: dict[int, float] = {}
    send_monotonic_by_sequence: dict[int, float] = {}
    raw_rows: list[dict[str, Any]] = []
    sent_count = 0
    first_send_lsl: float | None = None
    last_send_lsl: float | None = None
    deadline = time.monotonic() + timeout_seconds
    next_send = time.monotonic() + pre_send_delay
    max_send_count = 0 if args.command_mode == "external" else max(sample_count, int(timeout_seconds / interval_seconds))

    def send_command_sample() -> None:
        nonlocal sent_count, first_send_lsl, last_send_lsl, next_send
        if command_outlet is None:
            return
        sequence = sent_count
        host_send_lsl = float(local_clock())
        command_sample = [float(sequence), host_send_lsl]
        push_sample(command_outlet, command_sample, host_send_lsl)
        sent_by_sequence[sequence] = host_send_lsl
        send_monotonic_by_sequence[sequence] = time.monotonic()
        if first_send_lsl is None:
            first_send_lsl = host_send_lsl
        last_send_lsl = host_send_lsl
        sent_count += 1
        next_send += interval_seconds

    discovery_started = time.monotonic()
    streams = []
    while time.monotonic() < deadline and not streams:
        now = time.monotonic()
        while command_outlet is not None and sent_count < max_send_count and now >= next_send:
            send_command_sample()
            now = time.monotonic()
        streams = list(
            resolve_byprop(
                "source_id",
                str(args.echo_source_id),
                minimum=1,
                timeout=0.05,
            )
            or []
        )
    discovery_ms = int(round((time.monotonic() - discovery_started) * 1000.0))
    if not streams:
        report = base_report(
            args,
            status="fail",
            issue_codes=["hostess.issue.connectivity_probe.lsl_echo_discovery_failed"],
            notes="No Quest QCL-081 LSL echo outlet was discovered by source_id.",
            topology=topology,
            library_version=library_version,
            samples_sent=sent_count,
            samples_received=0,
        )
        report["discovery_ms"] = discovery_ms
        return report

    echo_inlet = StreamInlet(
        streams[0],
        max_buflen=ECHO_INLET_MAX_BUFLEN_SECONDS,
        max_chunklen=1,
        recover=True,
    )
    try:
        echo_inlet.open_stream(timeout=min(5.0, timeout_seconds))
    except Exception:
        pass

    time_correction_before = safe_time_correction(echo_inlet, timeout=2.0)
    seen_sequences: set[int] = set()
    receive_loop_started = time.monotonic()
    first_receive_monotonic: float | None = None
    last_receive_monotonic: float | None = None
    pull_timeout_count = 0
    pull_timeouts_after_first_echo = 0
    consecutive_pull_timeouts_after_last_echo = 0
    max_consecutive_pull_timeouts_after_last_echo = 0

    while time.monotonic() < deadline and len(seen_sequences) < sample_count:
        now = time.monotonic()
        while command_outlet is not None and sent_count < max_send_count and now >= next_send:
            send_command_sample()
            now = time.monotonic()

        pull_timeout = min(0.025, max(0.0, next_send - now)) if sent_count < max_send_count else 0.025
        sample, timestamp = echo_inlet.pull_sample(timeout=pull_timeout)
        if not sample:
            pull_timeout_count += 1
            if first_receive_monotonic is not None:
                pull_timeouts_after_first_echo += 1
                consecutive_pull_timeouts_after_last_echo += 1
                max_consecutive_pull_timeouts_after_last_echo = max(
                    max_consecutive_pull_timeouts_after_last_echo,
                    consecutive_pull_timeouts_after_last_echo,
                )
            continue
        receive_monotonic = time.monotonic()
        if first_receive_monotonic is None:
            first_receive_monotonic = receive_monotonic
        last_receive_monotonic = receive_monotonic
        consecutive_pull_timeouts_after_last_echo = 0
        host_receive_lsl = float(local_clock())
        parsed = parse_echo_sample(sample)
        if parsed is None:
            continue
        sequence = parsed["sequence"]
        host_send_lsl = sent_by_sequence.get(sequence, parsed["host_send_lsl_clock_seconds"])
        parsed["host_send_lsl_clock_seconds"] = host_send_lsl
        parsed["host_receive_lsl_clock_seconds"] = host_receive_lsl
        parsed["echo_lsl_timestamp_seconds"] = float(timestamp)
        parsed["host_send_monotonic_seconds"] = send_monotonic_by_sequence.get(sequence)
        raw_rows.append(parsed)
        seen_sequences.add(sequence)

    time_correction_after = safe_time_correction(echo_inlet, timeout=1.0)
    receive_loop_ended = time.monotonic()
    clock_correction = median_available([time_correction_before, time_correction_after])
    rows = apply_clock_alignment(raw_rows, clock_correction)
    unique_sequences = sorted({int(row["sequence"]) for row in rows})
    sequence_gaps = sequence_gap_ranges(unique_sequences)
    sequence_missing_between_first_last = sum((gap["end"] - gap["start"] + 1) for gap in sequence_gaps)
    duplicate_count = len(rows) - len(unique_sequences)
    matched_count = len(unique_sequences)
    loss_percent = round(((sample_count - matched_count) / sample_count) * 100.0, 3)
    send_duration_seconds = (
        (last_send_lsl - first_send_lsl)
        if first_send_lsl is not None and last_send_lsl is not None
        else None
    )

    issue_codes: list[str] = []
    if matched_count != sample_count:
        issue_codes.append("hostess.issue.connectivity_probe.lsl_echo_sample_loss")
    if duplicate_count > 0:
        issue_codes.append("hostess.issue.connectivity_probe.lsl_echo_duplicate_sequences")
    if clock_correction is None:
        issue_codes.append("hostess.issue.connectivity_probe.lsl_echo_clock_alignment_unavailable")
    elif has_large_negative_segment(rows):
        issue_codes.append("hostess.issue.connectivity_probe.lsl_echo_clock_alignment_segment_negative")

    if matched_count == sample_count and clock_correction is not None and not issue_codes:
        status = "pass"
    elif matched_count > 0:
        status = "warn"
    else:
        status = "fail"

    report = base_report(
        args,
        status=status,
        issue_codes=issue_codes,
        notes=(
            "Windows pylsl command outlet and inlet measured Quest LSL echo timing with "
            "LSL clock correction applied to Quest receive/send timestamps."
        ),
        topology=topology,
        library_version=library_version,
        samples_sent=sent_count,
        samples_received=len(rows),
    )
    report.update(
        {
            "discovery_ms": discovery_ms,
            "command_mode": str(args.command_mode),
            "lsl_api_config": current_lsl_api_config(),
            "samples_requested": sample_count,
            "samples_matched": matched_count,
            "duplicate_echo_samples": duplicate_count,
            "loss_percent": loss_percent,
            "send_interval_ms": round(interval_seconds * 1000.0, 3),
            "send_duration_seconds": round(send_duration_seconds, 6)
            if send_duration_seconds is not None
            else None,
            "streaming_target_seconds": round((sample_count - 1) * interval_seconds, 6),
            "echo_inlet_max_buflen_seconds": ECHO_INLET_MAX_BUFLEN_SECONDS,
            "receive_loop_elapsed_ms": round((receive_loop_ended - receive_loop_started) * 1000.0, 3),
            "first_echo_receive_offset_ms": (
                round((first_receive_monotonic - receive_loop_started) * 1000.0, 3)
                if first_receive_monotonic is not None
                else None
            ),
            "last_echo_receive_offset_ms": (
                round((last_receive_monotonic - receive_loop_started) * 1000.0, 3)
                if last_receive_monotonic is not None
                else None
            ),
            "last_echo_age_at_loop_exit_ms": (
                round((receive_loop_ended - last_receive_monotonic) * 1000.0, 3)
                if last_receive_monotonic is not None
                else None
            ),
            "pull_timeout_count": pull_timeout_count,
            "pull_timeouts_after_first_echo": pull_timeouts_after_first_echo,
            "max_consecutive_pull_timeouts_after_last_echo": max_consecutive_pull_timeouts_after_last_echo,
            "clock_alignment": {
                "status": "pass" if clock_correction is not None else "unavailable",
                "method": "pylsl.StreamInlet.time_correction",
                "formula": "windows_clock_seconds = quest_lsl_local_clock_seconds + correction_seconds",
                "time_correction_seconds_before": time_correction_before,
                "time_correction_seconds_after": time_correction_after,
                "time_correction_seconds_used": clock_correction,
            },
            "latency_ms_summary": {
                "windows_send_to_quest_receive": summarize_ms(
                    values(rows, "windows_send_to_quest_receive_ms")
                ),
                "quest_processing": summarize_ms(values(rows, "quest_processing_ms")),
                "quest_send_to_windows_receive": summarize_ms(
                    values(rows, "quest_send_to_windows_receive_ms")
                ),
                "round_trip": summarize_ms(values(rows, "round_trip_ms")),
                "accounting_error": summarize_ms(values(rows, "accounting_error_ms")),
            },
            "sequence_first": unique_sequences[0] if unique_sequences else None,
            "sequence_last": unique_sequences[-1] if unique_sequences else None,
            "sequence_gap_count": len(sequence_gaps),
            "sequence_missing_between_first_last": sequence_missing_between_first_last,
            "sequence_gap_ranges": sequence_gaps[:20],
            "timing_samples": rows,
            "timing_samples_tail": rows[-10:],
        }
    )
    return report


def base_report(
    args: argparse.Namespace,
    *,
    status: str,
    issue_codes: list[str],
    notes: str,
    topology: dict[str, Any],
    samples_sent: int,
    samples_received: int,
    library_version: Any = None,
) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "status": status,
        "run_id": str(args.run_id),
        "source": "windows-host-plus-quest-runtime",
        "evidence_tier": "quest_runtime",
        "command_stream_name": str(args.command_stream_name),
        "command_stream_type": str(args.command_stream_type),
        "command_source_id": str(args.command_source_id),
        "echo_stream_name": str(args.echo_stream_name),
        "echo_stream_type": str(args.echo_stream_type),
        "echo_source_id": str(args.echo_source_id),
        "samples_requested": max(1, int(args.sample_count or 300)),
        "samples_sent": samples_sent,
        "samples_received": samples_received,
        "library_version": library_version,
        "lsl_api_config": current_lsl_api_config(),
        "topology": {
            "owner": "wifi_direct",
            "network_provider": "wifi_direct",
            "endpoint_direction": "lsl_multicast_discovery_plus_bidirectional_lsl_samples",
            "topology_report_path": str(args.topology_report or ""),
            "paired_topology_status": topology.get("status"),
            "paired_topology_promotion_allowed": (topology.get("promotion") or {}).get("allowed"),
        },
        "issue_codes": issue_codes,
        "notes": notes,
    }


def current_lsl_api_config() -> dict[str, str]:
    path_text = os.environ.get("LSLAPICFG") or ""
    if not path_text:
        return {"path": "", "content": ""}
    return {"path": path_text, "content": read_text(Path(path_text))}


def push_sample(outlet: Any, sample: list[float], timestamp: float) -> None:
    try:
        outlet.push_sample(sample, timestamp=timestamp, pushthrough=True)
    except TypeError:
        outlet.push_sample(sample, timestamp, True)


def parse_echo_sample(sample: list[Any]) -> dict[str, Any] | None:
    if len(sample) < 4:
        return None
    try:
        sequence = int(round(float(sample[0])))
        return {
            "sequence": sequence,
            "host_send_lsl_clock_seconds": float(sample[1]),
            "quest_receive_lsl_clock_seconds": float(sample[2]),
            "quest_echo_send_lsl_clock_seconds": float(sample[3]),
            "command_capture_timestamp_seconds": float(sample[4]) if len(sample) > 4 else None,
        }
    except (TypeError, ValueError):
        return None


def apply_clock_alignment(
    rows: list[dict[str, Any]],
    correction_seconds: float | None,
) -> list[dict[str, Any]]:
    aligned: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in rows:
        sequence = int(row["sequence"])
        duplicate = sequence in seen
        seen.add(sequence)
        aligned_row = dict(row)
        aligned_row["duplicate_sequence"] = duplicate
        if correction_seconds is not None:
            quest_receive_host = row["quest_receive_lsl_clock_seconds"] + correction_seconds
            quest_echo_send_host = row["quest_echo_send_lsl_clock_seconds"] + correction_seconds
            host_send = row["host_send_lsl_clock_seconds"]
            host_receive = row["host_receive_lsl_clock_seconds"]
            host_to_quest = (quest_receive_host - host_send) * 1000.0
            quest_processing = (
                row["quest_echo_send_lsl_clock_seconds"] - row["quest_receive_lsl_clock_seconds"]
            ) * 1000.0
            quest_to_host = (host_receive - quest_echo_send_host) * 1000.0
            round_trip = (host_receive - host_send) * 1000.0
            accounted = host_to_quest + quest_processing + quest_to_host
            aligned_row.update(
                {
                    "quest_receive_windows_clock_seconds": quest_receive_host,
                    "quest_echo_send_windows_clock_seconds": quest_echo_send_host,
                    "windows_send_to_quest_receive_ms": host_to_quest,
                    "quest_processing_ms": quest_processing,
                    "quest_send_to_windows_receive_ms": quest_to_host,
                    "round_trip_ms": round_trip,
                    "accounting_error_ms": round_trip - accounted,
                }
            )
        else:
            aligned_row.update(
                {
                    "quest_receive_windows_clock_seconds": None,
                    "quest_echo_send_windows_clock_seconds": None,
                    "windows_send_to_quest_receive_ms": None,
                    "quest_processing_ms": (
                        row["quest_echo_send_lsl_clock_seconds"]
                        - row["quest_receive_lsl_clock_seconds"]
                    )
                    * 1000.0,
                    "quest_send_to_windows_receive_ms": None,
                    "round_trip_ms": (
                        row["host_receive_lsl_clock_seconds"]
                        - row["host_send_lsl_clock_seconds"]
                    )
                    * 1000.0,
                    "accounting_error_ms": None,
                }
            )
        aligned.append(round_row(aligned_row))
    return aligned


def values(rows: list[dict[str, Any]], key: str) -> list[float]:
    result: list[float] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            result.append(float(value))
    return result


def summarize_ms(items: list[float]) -> dict[str, Any] | None:
    if not items:
        return None
    ordered = sorted(float(item) for item in items)
    return {
        "count": len(ordered),
        "min": round(ordered[0], 3),
        "median": round(float(statistics.median(ordered)), 3),
        "p95": round(percentile(ordered, 95.0), 3),
        "max": round(ordered[-1], 3),
    }


def percentile(ordered: list[float], percentile_value: float) -> float:
    if not ordered:
        return math.nan
    if len(ordered) == 1:
        return ordered[0]
    position = (max(0.0, min(100.0, percentile_value)) / 100.0) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def has_large_negative_segment(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        for key in ("windows_send_to_quest_receive_ms", "quest_send_to_windows_receive_ms"):
            value = row.get(key)
            if isinstance(value, (int, float)) and float(value) < -25.0:
                return True
    return False


def sequence_gap_ranges(sequences: list[int]) -> list[dict[str, int]]:
    gaps: list[dict[str, int]] = []
    if len(sequences) < 2:
        return gaps
    previous = sequences[0]
    for sequence in sequences[1:]:
        if sequence > previous + 1:
            gaps.append({"start": previous + 1, "end": sequence - 1})
        previous = sequence
    return gaps


def round_row(row: dict[str, Any]) -> dict[str, Any]:
    rounded: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, float):
            rounded[key] = round(value, 9)
        else:
            rounded[key] = value
    return rounded


def median_available(values_: list[float | None]) -> float | None:
    available = [float(value) for value in values_ if value is not None and math.isfinite(float(value))]
    if not available:
        return None
    return float(statistics.median(available))


def safe_library_version(pylsl_module: Any) -> Any:
    for name in ("library_version", "lsl_library_version"):
        func = getattr(pylsl_module, name, None)
        if callable(func):
            try:
                return func()
            except Exception:
                pass
    return getattr(pylsl_module, "__version__", None)


def safe_time_correction(inlet: Any, *, timeout: float) -> float | None:
    try:
        return float(inlet.time_correction(timeout=timeout))
    except Exception:
        return None


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
