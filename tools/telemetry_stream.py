from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


STREAM_EVENT_SCHEMA = "rusty.hostess.telemetry.stream_event.v1"


def main() -> int:
    parser = argparse.ArgumentParser(prog="telemetry-stream")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--delay-seconds", type=float, default=0.12)
    parser.add_argument("--cycles", type=int, default=8)
    parser.add_argument(
        "--drop-after",
        action="append",
        default=[],
        help="series_id=count; stop emitting that series after count batches",
    )
    args = parser.parse_args()
    snapshot = load_json(Path(args.snapshot))
    series = [item for item in snapshot.get("time_series", []) if isinstance(item, dict)]
    if not series:
        raise SystemExit("snapshot has no time_series entries")
    drops = parse_drop_after(args.drop_after)
    stream_to_jsonl(
        series,
        Path(args.out),
        batch_size=max(1, args.batch_size),
        delay_seconds=max(0.0, args.delay_seconds),
        cycles=max(1, args.cycles),
        drops=drops,
    )
    return 0


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object in {path}")
    return value


def parse_drop_after(values: list[str]) -> dict[str, int]:
    drops: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"bad --drop-after value {value!r}; expected series_id=count")
        series_id, count = value.split("=", 1)
        drops[series_id] = int(count)
    return drops


def stream_to_jsonl(
    series: list[dict[str, Any]],
    out: Path,
    *,
    batch_size: int,
    delay_seconds: float,
    cycles: int,
    drops: dict[str, int],
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("", encoding="utf-8")
    emitted_batches: dict[str, int] = {}
    sequence = 0
    with out.open("a", encoding="utf-8") as handle:
        for cycle in range(cycles):
            for item in series:
                series_id = str(item.get("series_id", ""))
                values = numeric_values(item.get("values", []))
                if not series_id or not values:
                    continue
                emitted = emitted_batches.get(series_id, 0)
                if series_id in drops and emitted >= drops[series_id]:
                    continue
                offset = (cycle * batch_size) % len(values)
                batch = cyclic_batch(values, offset, batch_size)
                event = {
                    "$schema": STREAM_EVENT_SCHEMA,
                    "event_id": f"event.{sequence:06d}",
                    "sequence": sequence,
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "series_id": series_id,
                    "stream_id": str(item.get("stream_id", "")),
                    "label": str(item.get("label", series_id)),
                    "unit": str(item.get("unit", "value")),
                    "source": str(item.get("source", "replay-stream")),
                    "sample_rate_hz": item.get("sample_rate_hz"),
                    "values": batch,
                }
                handle.write(json.dumps(event, sort_keys=True) + "\n")
                handle.flush()
                emitted_batches[series_id] = emitted + 1
                sequence += 1
                if delay_seconds:
                    time.sleep(delay_seconds)


def cyclic_batch(values: list[float], offset: int, count: int) -> list[float]:
    return [round(values[(offset + index) % len(values)], 4) for index in range(count)]


def numeric_values(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    parsed: list[float] = []
    for value in values:
        try:
            parsed.append(float(value))
        except (TypeError, ValueError):
            continue
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
